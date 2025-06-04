# AI Storyteller: Script to Video Pipeline

An end-to-end AI-powered content creation pipeline that generates stories, converts them to multi-speaker audio with subtitles, creates visual content, and compiles everything into engaging videos.

## ✨ Features

### Core Functionality
- **AI-Powered Script Generation**: Create compelling stories using Google's Gemini 2.5 Flash model
- **Multi-Speaker TTS**: Convert scripts to natural-sounding speech with 50+ distinct voices
- **SRT Subtitle Generation**: Automatically generate synchronized subtitle files
- **AI Image Generation**: Create visual content using Google's Imagen 3.0 model
- **Video Production**: Compile audio, images, and subtitles into polished videos

### Advanced Capabilities
- **Web Search Integration**: Enhance scripts with real-time web search context
- **Multi-Character Dialog**: Support for multiple speakers with distinct voices
- **Customizable Art Styles**: Choose from various art styles for generated images
- **Flexible Output Formats**: Export in multiple video resolutions and qualities

## 🏗️ Project Structure

```
app/
├── config.py           # Configuration settings and constants
├── image_generator.py   # Image generation using Imagen 3.0
├── main.py             # Gradio web interface
├── phase1_story_gen.py # Story generation logic
├── phase2_tts.py       # Text-to-speech conversion
├── phase4_video.py     # Video generation
├── utils.py            # Utility functions
└── web_search.py       # Web search functionality
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Google API key with access to:
  - Gemini 2.5 Flash
  - Gemini TTS
  - Imagen 3.0
- FFmpeg (for video processing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd audio-analyzer-srt-&-vision
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root with:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## 🎮 Usage

1. **Start the application**
   ```bash
   python -m app.main
   ```

2. **Access the web interface**
   Open your browser and navigate to `http://localhost:7860`

3. **Follow the workflow**
   - Phase 1: Generate your story script
   - Phase 2: Convert to speech and generate subtitles
   - Phase 3: Generate images for your story
   - Phase 4: Compile everything into a video

## ⚙️ Configuration

Key configuration options in `app/config.py`:

- **Output Directories**: Customize where generated files are saved
- **API Settings**: Configure API endpoints and retry logic
- **Default Voices**: Set default voices for different speaker types
- **Generation Parameters**: Adjust story length, complexity, and style defaults

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
