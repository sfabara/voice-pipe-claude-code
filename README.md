# Voice-to-Text-to-Claude Conversation

A powerful tool that allows you to speak to Claude AI using voice input. This application uses Google's Gemini models for speech transcription and connects to the Claude CLI for a seamless voice-to-text-to-AI experience.

## Features

- 🎤 **Voice Input**: Record your voice and have it transcribed to text
- 💬 **Direct Claude Interaction**: Send text or voice input directly to Claude
- 🔍 **Detailed Logging**: Comprehensive logging to track communication flow
- 🔄 **Non-blocking I/O**: Efficient handling of Claude's input/output streams
- 🛠️ **Debug Mode**: Built-in debugging capabilities with the `/debug` command

## Requirements

- Python 3.6+
- Google API key (for Gemini models)
- Claude CLI installed locally

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install google-generativeai pyaudio numpy
   ```
3. Set up your Google API key as an environment variable:
   ```
   export GOOGLE_API_KEY="your_google_api_key"
   ```
4. Make sure the Claude CLI is installed and the path in the script matches your installation path

## Usage

Run the application:
```
python execute.py
```

### Available Commands

- Type your message to interact with Claude
- `/voice` - Switch to voice input mode
- `/debug` - Display debugging information about the connection
- `/exit` - End the session

## Troubleshooting

If you experience issues with Claude's output not displaying correctly:

1. Use the `/debug` command to check process status
2. Verify Claude CLI path is correct for your system
3. Check logs for detailed error information
4. Ensure Claude CLI is installed and working independently

## Architecture

This tool works by:
1. Using Google's Gemini model to transcribe voice to text
2. Managing a subprocess that runs the Claude CLI
3. Setting up non-blocking I/O for efficient communication
4. Providing a clean, interactive interface for seamless conversations

## Advanced Debugging

The tool includes comprehensive logging at various levels:
- Process startup and connection verification
- Input/output stream monitoring
- Claude process health checking
- Input/output buffering and error handling
