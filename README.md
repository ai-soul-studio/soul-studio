# Audio Analyzer: Script to Speech & Subtitles

A comprehensive AI-powered application that generates story scripts, converts them to multi-speaker audio, and creates synchronized SRT subtitles. Now enhanced with image generation capabilities and improved error handling.

## ✨ Features

- **AI Script Generation**: Generate compelling scripts using Google's Gemini 2.5 Flash model
- **Multi-Speaker TTS**: Convert scripts to natural-sounding speech with multiple voices
- **SRT Subtitle Generation**: Create synchronized subtitle files
- **Image Generation**: Generate visual content using Google's Imagen 3.0 model
- **Web Search Integration**: Enhance scripts with real-time web search context
- **Gradio Web Interface**: User-friendly web interface for all features
- **Robust Error Handling**: Comprehensive logging and retry mechanisms
- **Configurable Settings**: Centralized configuration management

## 🚀 Recent Improvements

### Code Quality Enhancements
- ✅ Updated to use latest Google Genai SDK (`google-genai` instead of deprecated `google-generative-ai`)
- ✅ Proper import statements following best practices
- ✅ Centralized configuration management
- ✅ Comprehensive error handling and logging
- ✅ Type hints for better code maintainability
- ✅ Retry mechanisms with exponential backoff
- ✅ Rate limiting for API calls

### New Features
- 🆕 Image generation module using Imagen 3.0
- 🆕 Enhanced web search with better error handling
- 🆕 Improved audio processing utilities
- 🆕 Comprehensive test suite
- 🆕 Better voice assignment for multi-speaker content

### Security Improvements
- 🔒 Environment variable validation
- 🔒 API key security best practices
- 🔒 Input sanitization and validation

This project creates a web application using Gradio where a user can input a subject, get an AI-generated story in SRT format, and then convert that SRT into a multi-speaker audio narration using Google's Generative AI models.

## Setup Instructions

1.  **Clone the repository (if not already done):**
    ```bash
    git clone <repository_url>
    cd audio-analyzer-srt-&-vision
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv .venv
    # On Windows:
    .venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set your Google Gemini API Key:**
    The application requires your Google Gemini API key to be set as an environment variable named `GEMINI_API_KEY`.
    
    **Important:** Do NOT hardcode your API key in any files.

    *   **For Windows (Command Prompt):**
        ```bash
        set GEMINI_API_KEY=YOUR_API_KEY_HERE
        ```
    *   **For Windows (PowerShell):**
        ```powershell
        $env:GEMINI_API_KEY="YOUR_API_KEY_HERE"
        ```
    *   **For macOS/Linux:**
        ```bash
        export GEMINI_API_KEY=YOUR_API_KEY_HERE
        ```
    Replace `YOUR_API_KEY_HERE` with your actual Gemini API key. For persistent setting, you might add this to your system's environment variables or your shell's profile file (`.bashrc`, `.zshrc`, `config.fish`, etc.).

5.  **Run the application:**
    ```bash
    python app/main.py
    ```
    This will launch the Gradio web interface, typically accessible at `http://127.0.0.1:7860/` (or a similar local address).

## Project Structure

```
/project_root
|-- /app
|   |-- main.py             # Gradio app and server logic
|   |-- phase1_story_gen.py # Logic for story & SRT generation
|   |-- phase2_tts.py       # Logic for TTS from SRT
|   |-- utils.py            # Helper functions (optional)
|-- /outputs
|   |-- /srt                # To store generated SRT files
|   |-- /audio              # To store generated audio files
|-- requirements.txt        # List of dependencies (google-genai, gradio, etc.)
|-- README.md
|-- .gitignore
```

## Usage

1.  **Enter a Story Subject:** Type your desired subject into the text box.
2.  **Generate Story (SRT):** Click this button to generate an SRT formatted story. The status will be displayed.
3.  **Convert SRT to Speech:** Once the SRT is generated, click this button to convert it into an audio narration. The audio will be playable directly in the UI.

## Future Work

*   **Prompt Engineering:** Further refinement of prompts for better story and SRT generation.
*   **Voice Assignment Logic:** Implement more sophisticated logic for assigning different voices to speakers in the TTS output, if the model supports it.
*   **Error Handling & UI Improvements:** Enhance error messages and user experience.
*   **Image Generation:** Integrate image generation based on story content using `models/imagen-3.0-generate-002` as per `.clinerules`.
