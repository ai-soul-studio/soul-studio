Project Title: AI Storyteller with SRT and Multi-Speaker TTS (Aligned with SDK Guidelines)

Overall Goal: Create a web application using Gradio where a user can input a subject, get an AI-generated story in SRT format, and then convert that SRT into a multi-speaker audio narration, adhering to the provided SDK usage rules.

I. Project Setup & Core Configuration

1.1. Environment Setup:
[done] Create a dedicated project directory.
[done] Set up a Python virtual environment (e.g., using venv ).
[done] Activate the virtual environment.
1.2. Install Dependencies:
[ ] Install gradio: pip install gradio
[ ] Install the required Google Generative AI SDK: pip install google-genai (as per [package] rule).
[ ] Install Pillow if any image handling is anticipated for future phases (as suggested by the TOML's code example): pip install Pillow.
[ ] Install any other necessary utility libraries.
1.3. API Key Management (Strict Adherence to [api_keys] rules):
[ ] Ensure the GEMINI_API_KEY environment variable is set in your development and deployment environments.
[ ] All SDK client initializations must use api_key=os.environ["GEMINI_API_KEY"]. This will raise a KeyError if the environment variable is not set, as intended for stricter error checking.
[ ] Do not hardcode API keys or use os.environ.get().
1.4. Project Structure:
[ ] Define a clear project folder structure. Example:
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
# .env file is NOT recommended for storing the API key directly if using os.environ["GEMINI_API_KEY"]
# The environment variable should be set in the system or execution environment.
1.5. Initial Git Setup:
[ ] Initialize a Git repository: git init
[ ] Create a .gitignore file (e.g., for __pycache__, .venv, outputs/).
[ ] Make an initial commit.
II. Backend Logic Implementation (Python Modules)
* General SDK Usage Note: All interactions with the Google Generative AI SDK should use from google import genai and client initialization with genai.Client(...) as per [imports] and [migration] rules.

2.1. Module: phase1_story_gen.py (Story Generation to SRT)
[ ] Function: generate_story_srt(subject: str, output_dir: str) -> str
[ ] Initialize the Gemini client: client = genai.Client(api_key=os.environ["GEMINI_API_KEY"]).
[ ] Use the specified model for text generation (as per [models] rule, assuming it's suitable for story generation): model_name = "gemini-2.5-flash-preview-05-20".
[ ] Develop a robust prompt for the model:
Instruct it to generate a story based on the subject.
Crucially, instruct it to format the entire output directly as an SRT file content.
Specify requirements for dialogue (e.g., "Speaker 1:", "Speaker 2:").
[ ] Send the request to the Gemini API using the initialized client and model_name.
[ ] Receive the SRT formatted string response.
[ ] Save the SRT string to a unique file in output_dir/srt/.
[ ] Return the path to the saved SRT file.
2.2. Module: phase2_tts.py (TTS from SRT)
[ ] Function: parse_srt_file(srt_file_path: str) -> list[dict] (No direct SDK interaction here, but prepares data for it).
[ ] Read and parse the SRT file to extract text and speaker labels.
[ ] Function: convert_srt_to_speech(srt_file_path: str, output_dir: str) -> str
[ ] Call parse_srt_file() to get structured text.
[ ] Initialize the Gemini client: client = genai.Client(api_key=os.environ["GEMINI_API_KEY"]).
[ ] Use the specified TTS model (as per [models] rule): model_name = "gemini-2.5-flash-preview-tts".
[ ] Dynamically construct the contents payload and SpeechConfig (including MultiSpeakerVoiceConfig if applicable, as shown in your previous example) for the generate_content_stream method (or equivalent TTS method in genai.Client).
[ ] Adapt streaming/saving logic (e.g., save_binary_file, convert_to_wav) using the client and model_name.
[ ] Save audio to output_dir/audio/.
[ ] Return the path to the saved audio file.
2.3. Helper Utilities (utils.py - Optional)
[ ] Logging setup.
[ ] Functions for creating unique filenames or managing directories.
III. Gradio User Interface (UI) Development (main.py)
* (No direct changes from TOML rules here, but ensure SDK calls made via UI handlers adhere to rules implemented in backend modules.)
* [ ] 3.1. Define UI Components: (Subject input, SRT display/download, Audio output, State for SRT path, Status messages, Buttons for actions).
* [ ] 3.2. Backend Interface Functions (Wrapper Functions in main.py):
* [ ] handle_generate_srt(subject: str): Calls phase1_story_gen.generate_story_srt().
* [ ] handle_generate_speech(srt_file_path_from_state: str): Calls phase2_tts.convert_srt_to_speech().
* [ ] 3.3. Construct Gradio Interface: Use gr.Interface or gr.Blocks.
* [ ] 3.4. Input Validation and Error Handling in UI.

IV. Server and Application Entry Point (main.py)
* [ ] 4.1. Launch Gradio App: if __name__ == "__main__": app.launch().
* [ ] 4.2. Ensure Output Directories Exist.

V. Testing and Refinement
* [ ] 5.1. Backend Unit Testing:
* [ ] Test phase1_story_gen.py functions.
* [ ] Test phase2_tts.py functions.
* [ ] Crucially, as per [testing] rule (require_test_for = generate_content), ensure comprehensive tests for any functions that directly invoke content generation methods of the SDK (e.g., the parts making calls to client.generate_content or equivalent for text and TTS).
* [ ] 5.2. Integration Testing: Full flow via Gradio UI.
* [ ] 5.3. Prompt Engineering for Phase 1: Refine prompts for the gemini-2.5-flash-preview-05-20 model.
* [ ] 5.4. Voice Assignment Logic for Phase 2 (TTS Model gemini-2.5-flash-preview-tts).

VI. Documentation & Future Work Planning
* [ ] 6.1. README.md: Setup, API key environment variable (GEMINI_API_KEY), how to run.
* [ ] 6.2. Code Comments: Adhere to Python best practices and clarify SDK usage.
* [ ] 6.3. Placeholders for Future Phases (Phase 3, Phase 4):
* [ ] If image generation is considered for future phases, ensure to use the specified model models/imagen-3.0-generate-002 and follow the practices shown in the [code_example] section of your TOML file, including Pillow for image handling.

