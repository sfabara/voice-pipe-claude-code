# Voice to Claude

A Python application that uses Gemini API for speech-to-text transcription and sends the transcribed text to the Claude CLI for processing.

## Features

- Records audio from your microphone
- Transcribes the audio using Google's Gemini API 
- Sends the transcription to Claude CLI and allows interactive conversation
- Supports choosing from available Gemini models
- Provides a menu-driven interface for multiple operations

## Requirements

- Python 3.x
- Google AI API key (set as GOOGLE_API_KEY environment variable)
- Claude CLI installed (at ~/.claude/local/claude)
- PyAudio
- NumPy
- google-generativeai Python library

## Installation

```bash
# Install required packages
pip install google-generativeai pyaudio numpy
```

## Usage

1. Run the script:
```bash
python execute.py
```

2. The script will:
   - List available Gemini models
   - Prompt you to select a model for transcription
   - Present a menu with options:
     1. Record audio and send to Claude
     2. Type text directly to Claude
     3. Change Gemini model
     4. Exit program

3. When recording audio:
   - Press Enter to start recording
   - Press Enter again to stop recording
   - Audio will be transcribed using the selected Gemini model
   - Transcription will be sent to Claude for processing

4. During a Claude session:
   - Type your responses to Claude
   - Type 'exit' to end the Claude session and return to the main menu

## Notes

- The speech recognition works best in quiet environments with clear speech
- For transcription, models that support audio (like gemini-1.5-pro) are recommended
- The Claude session is fully interactive - you can continue the conversation as needed
