import google.generativeai as genai
from google.generativeai import types
import os
import subprocess
import pyaudio
import wave
import tempfile
import threading
import time
import sys
import numpy as np
import logging  # Add logging module
import fcntl
import io

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configure the API key
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def list_available_models():
    """List available Gemini models and their supported methods"""
    try:
        models = genai.list_models()
        print("📋 Available Gemini Models:")
        model_names = []
        for idx, model in enumerate(models):
            print(f"{idx+1}. {model.name}")
            print(f"   Supported generation methods: {model.supported_generation_methods}")
            print()
            model_names.append(model.name)
        return model_names
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return None

def record_audio_with_enter_to_stop():
    """Record audio from microphone and stop when Enter key is pressed"""
    p = pyaudio.PyAudio()
    
    print("🎙️ Recording... Press Enter to stop recording")
    
    # Setup audio stream
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024)
    
    frames = []
    
    # Create a flag to indicate if Enter was pressed
    enter_pressed = False
    
    # Function to handle the Enter key press
    def wait_for_enter():
        nonlocal enter_pressed
        input()  # This will block until Enter is pressed
        enter_pressed = True
    
    # Start thread to wait for Enter key
    enter_thread = threading.Thread(target=wait_for_enter)
    enter_thread.daemon = True  # Make thread exit when main program exits
    enter_thread.start()
    
    try:
        while not enter_pressed:
            # Read audio chunk
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
            time.sleep(0.01)  # Short sleep to reduce CPU usage
    
    except KeyboardInterrupt:
        print("Recording interrupted.")
    finally:
        print("⏳ Processing audio...")
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    return b''.join(frames)

def get_transcription(model_name):
    """Record audio and transcribe it using the selected Gemini model"""
    try:
        # Record audio from microphone with interrupt capability
        audio_data = record_audio_with_enter_to_stop()
        
        # Create a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 2 bytes per sample
                wf.setframerate(44100)
                wf.writeframes(audio_data)
            
            # Read the temporary file
            with open(temp_file.name, 'rb') as f:
                audio_bytes = f.read()
        
        # Clean up the temporary file
        os.unlink(temp_file.name)
        
        # Create a model instance using the selected model
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(
            [
                'Transcribe this audio clip',
                {
                    'mime_type': 'audio/wav',
                    'data': audio_bytes
                }
            ]
        )
        
        print(f"📝 Transcribed Text: {response.text}")
        return response.text
    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        return None

def simple_claude_voice_interface(selected_model):
    """A simpler interface that starts Claude and allows voice input"""
    print("\n🔊 Voice-to-Text with Claude CLI")
    print("\nHow this works:")
    print("1. Type or speak to Claude")
    print("2. To speak, type '/voice' and press Enter")
    print("3. To exit, type '/exit' and press Enter")
    
    # Start Claude process
    claude_cmd = "/Users/sebastianfabara/.claude/local/claude"
    
    logger.debug(f"Starting Claude CLI process with command: {claude_cmd}")
    
    try:
        # First test if Claude is available
        if not os.path.exists(claude_cmd):
            logger.error(f"Claude executable not found at {claude_cmd}")
            print(f"❌ Error: Claude executable not found at {claude_cmd}")
            return
            
        print("\nStarting Claude CLI...\n")
        
        # Start Claude in the foreground but pipe to our own stdout/stderr
        process = subprocess.Popen(
            [claude_cmd], 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        logger.info(f"Claude process started with PID: {process.pid}")
        
        # Check if process started successfully
        if process.poll() is not None:
            logger.error(f"Claude process failed to start or terminated immediately with code {process.returncode}")
            print(f"❌ Error: Claude process failed to start or terminated immediately")
            return
            
        # Make stdout non-blocking
        stdout_fd = process.stdout.fileno()
        fl = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
        fcntl.fcntl(stdout_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
        stderr_fd = process.stderr.fileno()
        fl = fcntl.fcntl(stderr_fd, fcntl.F_GETFL)
        fcntl.fcntl(stderr_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
        # Flag to indicate if we're exiting
        is_exiting = False
        
        # Create event to indicate when initial output is received
        initial_output_received = threading.Event()
        
        # Store captured output for debugging
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        
        # Thread to continuously read from Claude's output
        def read_output(stream, prefix, is_stderr=False, capture_buffer=None):
            logger.debug(f"Starting {prefix} reader thread")
            line_count = 0
            buffer = ""
            
            while not is_exiting:
                try:
                    # Try to read from the non-blocking stream
                    chunk = stream.read(4096)
                    if chunk:
                        buffer += chunk
                        lines = buffer.splitlines(True)
                        
                        # Process complete lines
                        new_buffer = ""
                        for line in lines:
                            if line.endswith('\n'):
                                line_count += 1
                                clean_line = line.strip()
                                
                                # Store in capture buffer if provided
                                if capture_buffer is not None:
                                    capture_buffer.write(clean_line + '\n')
                                    
                                logger.debug(f"Received {prefix} line {line_count}: {clean_line[:50]}{'...' if len(clean_line) > 50 else ''}")
                                
                                # Don't print "Error: " prefix for empty lines from stderr
                                if is_stderr and not clean_line:
                                    pass
                                else:
                                    # Only print non-debug stderr messages to the user
                                    if not is_stderr or not clean_line.startswith("DEBUG:"):
                                        print(f"{prefix if not (is_stderr and clean_line.startswith('INFO:')) else ''} {clean_line}")
                                
                                # Signal that we've received some initial output
                                if not initial_output_received.is_set():
                                    logger.info(f"Initial output received from {prefix}")
                                    initial_output_received.set()
                            else:
                                # Incomplete line, put back in buffer
                                new_buffer += line
                        
                        buffer = new_buffer
                    
                    # Check if process has terminated
                    if process.poll() is not None:
                        # Try to read any remaining data
                        try:
                            remaining = stream.read()
                            if remaining:
                                if capture_buffer is not None:
                                    capture_buffer.write(remaining)
                                logger.debug(f"Read remaining data from {prefix} after process terminated")
                                print(f"{prefix} {remaining.strip()}")
                        except:
                            pass
                            
                        logger.debug(f"{prefix} stream closed, process return code: {process.poll()}")
                        break
                        
                except (IOError, OSError) as e:
                    # This is expected with non-blocking IO
                    pass
                except Exception as e:
                    logger.error(f"Error reading from {prefix}: {e}")
                    
                # Small sleep to prevent tight loop
                time.sleep(0.05)
                
            logger.debug(f"{prefix} reader thread exiting after reading {line_count} lines")
        
        # Start threads to read from stdout and stderr
        stdout_thread = threading.Thread(
            target=read_output, 
            args=(process.stdout, "Claude:", False, captured_stdout)
        )
        stderr_thread = threading.Thread(
            target=read_output, 
            args=(process.stderr, "Error:", True, captured_stderr)
        )
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        logger.debug("Starting stdout and stderr reader threads")
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for initial output with timeout
        logger.debug("Waiting for initial output from Claude...")
        # Increase timeout to give Claude more time to initialize
        if not initial_output_received.wait(timeout=10.0):
            logger.warning("No initial output received from Claude within timeout period")
            print("\n⚠️ Warning: No initial output received from Claude. The process might not be working correctly.")
            
            # Try sending a test message to see if Claude responds
            logger.debug("Sending test message to Claude to see if it responds")
            process.stdin.write("Hello Claude\n")
            process.stdin.flush()
            
            # Wait longer for response
            time.sleep(5)
            
            if not initial_output_received.is_set():
                logger.error("Claude is not responding to test input. Process health check:")
                if process.poll() is not None:
                    logger.error(f"Process has terminated with code {process.returncode}")
                else:
                    logger.error("Process is still running but not producing output")
                    
                    # Check if stdout/stderr has any content even if we didn't detect complete lines
                    try:
                        stdout_content = process.stdout.read()
                        stderr_content = process.stderr.read()
                        if stdout_content or stderr_content:
                            logger.debug(f"Found content in buffers - stdout: {stdout_content[:200]}, stderr: {stderr_content[:200]}")
                    except:
                        pass
                        
                print("\n❌ Claude is not responding. The process might be stuck or not working properly.")
            
        else:
            logger.info("Initial Claude output received successfully")
        
        # Start process monitor thread
        def monitor_process():
            while not is_exiting:
                if process.poll() is not None:
                    logger.warning(f"Claude process terminated unexpectedly with code {process.returncode}")
                    print(f"\n⚠️ Claude process terminated unexpectedly with code {process.returncode}")
                    break
                time.sleep(1)
                
        monitor_thread = threading.Thread(target=monitor_process)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Main loop for user interaction
        print("\n💬 You can now talk to Claude. Type '/voice' to use voice input, '/exit' to quit.\n")
        
        interaction_count = 0
        while process.poll() is None:  # While Claude is running
            try:
                interaction_count += 1
                logger.debug(f"Starting interaction #{interaction_count}")
                user_input = input("You: ")
                logger.debug(f"User input received: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
                
                # Special commands
                if user_input.lower() == '/exit':
                    logger.info("User requested exit")
                    print("Exiting Claude session...")
                    is_exiting = True
                    break
                
                elif user_input.lower() == '/debug':
                    logger.info("User requested debug info")
                    print("\n--- Debug Information ---")
                    print(f"Claude process running: {process.poll() is None}")
                    if process.poll() is not None:
                        print(f"Process return code: {process.returncode}")
                    print(f"Initial output received: {initial_output_received.is_set()}")
                    print(f"Interaction count: {interaction_count}")
                    print(f"Last stdout captured: {captured_stdout.getvalue()[-200:] if captured_stdout.getvalue() else 'None'}")
                    print(f"Last stderr captured: {captured_stderr.getvalue()[-200:] if captured_stderr.getvalue() else 'None'}")
                    print("------------------------\n")
                    continue
                    
                elif user_input.lower() == '/voice':
                    logger.info("Voice input mode activated")
                    print("\n🎤 Voice input mode. Press Enter to start recording...")
                    input()
                    logger.debug("Starting voice transcription")
                    transcribed_text = get_transcription(selected_model)
                    
                    if transcribed_text:
                        logger.info(f"Voice transcription successful: {transcribed_text[:50]}{'...' if len(transcribed_text) > 50 else ''}")
                        print(f"You (voice): {transcribed_text}")
                        logger.debug("Sending transcribed text to Claude")
                        try:
                            process.stdin.write(transcribed_text + '\n')
                            process.stdin.flush()
                            logger.debug("Transcribed text sent to Claude")
                        except IOError as e:
                            logger.error(f"Failed to send transcribed text to Claude: {e}")
                            print(f"❌ Error: Failed to send transcribed text to Claude: {e}")
                    else:
                        logger.warning("No voice input detected")
                        print("No voice input detected. Try again.")
                        
                else:
                    # Regular text input
                    logger.debug(f"Sending text input to Claude: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
                    try:
                        process.stdin.write(user_input + '\n')
                        process.stdin.flush()
                        logger.debug("Text input sent to Claude")
                    except IOError as e:
                        logger.error(f"Failed to send text input to Claude: {e}")
                        print(f"❌ Error: Failed to send text input to Claude: {e}")
                    
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received")
                print("\nInterrupted. Type '/exit' to quit or continue interacting.")
            except EOFError:
                logger.info("EOFError received")
                print("\nInput closed. Exiting...")
                is_exiting = True
                break
                
        # Wait for process to complete
        if process.poll() is None:
            logger.info("Terminating Claude process")
            try:
                process.stdin.close()
                logger.debug("stdin closed")
                process.terminate()
                logger.debug("Terminate signal sent to Claude process")
                process.wait(timeout=2)
                logger.info(f"Claude process terminated with return code: {process.returncode}")
            except Exception as e:
                logger.error(f"Error terminating Claude process: {e}")
                process.kill()
                logger.info("Claude process killed")
                
    except Exception as e:
        logger.error(f"Error in Claude interface: {e}")
        print(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        traceback.print_exc()
        
    logger.info("Claude session ended")
    print("\nClaude session ended.")

if __name__ == "__main__":
    print("🎤 Voice-to-Text-to-Claude Conversation 🎤")
    
    # List available models
    print("Listing available models...")
    model_names = list_available_models()
    
    if model_names:
        while True:
            try:
                choice = int(input("\nEnter the number of the model you want to use: "))
                if 1 <= choice <= len(model_names):
                    selected_model = model_names[choice-1]
                    print(f"\nYou selected: {selected_model}")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(model_names)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        # Fallback to gemini-1.5-pro if listing fails
        selected_model = "models/gemini-1.5-pro"
        print(f"\nUsing default model: {selected_model}")
    
    # Start the simpler Claude interface
    simple_claude_voice_interface(selected_model)