import google.generativeai as genai
from google.generativeai import types
import os
import subprocess
import pyaudio
import wave
import tempfile
import threading
import time
import signal
import sys
import numpy as np

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

def run_interactive_claude_session(text):
    # Start an interactive Claude session
    try:
        # Use the full path to Claude CLI
        command = [
            "/Users/sebastianfabara/.claude/local/claude",
        ]
        
        print(f"🚀 Starting Claude session with: {text}")
        
        # Start Claude as an interactive process
        claude_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Send the transcribed text to Claude
        claude_process.stdin.write(text + '\n')
        claude_process.stdin.flush()
        
        # Create threads to read from stdout and stderr
        def read_stdout():
            while True:
                line = claude_process.stdout.readline()
                if not line and claude_process.poll() is not None:
                    break
                if line:
                    print(f"🤖 {line.strip()}")
        
        def read_stderr():
            while True:
                line = claude_process.stderr.readline()
                if not line and claude_process.poll() is not None:
                    break
                if line:
                    print(f"⚠️ {line.strip()}")
        
        # Start the reading threads
        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Main loop for user interaction with Claude
        print("\n💬 You can now interact with Claude. Type your responses or 'exit' to quit this session.")
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'exit':
                break
            
            # Send user input to Claude
            claude_process.stdin.write(user_input + '\n')
            claude_process.stdin.flush()
        
        # Clean up the Claude process
        claude_process.stdin.close()
        if claude_process.poll() is None:
            claude_process.terminate()
            claude_process.wait(timeout=2)
        
        print("Claude session ended.")
        return True
    except Exception as e:
        print(f"❌ Error in Claude session: {e}")
        return False

def main():
    print("🎤 Gemini Audio Transcription to Claude 🎤")
    
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
    
    while True:
        print("\n--- New Session ---")
        print("Options:")
        print("1: Record audio and send to Claude")
        print("2: Type text directly to Claude")
        print("3: Change Gemini model")
        print("4: Exit program")
        
        try:
            option = int(input("\nSelect an option (1-4): "))
            
            if option == 1:
                # Record and transcribe audio
                print("\nPress Enter to start recording (press Enter again to stop)...")
                input()
                print("Recording started!")
                transcribed_text = get_transcription(selected_model)
                
                if transcribed_text:
                    run_interactive_claude_session(transcribed_text)
            
            elif option == 2:
                # Type text directly
                text = input("\nEnter text to send to Claude: ")
                if text:
                    run_interactive_claude_session(text)
            
            elif option == 3:
                # Change model
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
                    print("Could not list models. Using default model.")
                    selected_model = "models/gemini-1.5-pro"
            
            elif option == 4:
                # Exit program
                print("Exiting program. Goodbye!")
                break
            
            else:
                print("Invalid option. Please select 1-4.")
        
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nProgram interrupted. Exiting...")
            break

if __name__ == "__main__":
    main()