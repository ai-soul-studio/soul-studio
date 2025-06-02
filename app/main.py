import gradio as gr
import os
from dotenv import load_dotenv
from app.phase1_story_gen import generate_script
from app.phase2_tts import convert_script_to_speech_and_srt
from app import config # Import config

# Load environment variables
load_dotenv()

# --- Output Directories ---
# Use configurations from config.py
OUTPUT_SCRIPT_DIR = config.OUTPUT_SCRIPT_DIR
OUTPUT_AUDIO_DIR = config.OUTPUT_AUDIO_DIR
OUTPUT_SRT_DIR = config.OUTPUT_SRT_DIR

os.makedirs(OUTPUT_SCRIPT_DIR, exist_ok=True)
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_SRT_DIR, exist_ok=True)

# --- State Variables ---
script_path_state = gr.Textbox(label="script_path_state_hidden", visible=False, interactive=True)

# --- Helper Functions ---
def handle_generate_script(
    subject_type,
    story_length,
    complexity,
    user_prompt,
    style_primary,
    style_secondary,
    enable_web_search,
    additional_instructions,
    language # Added language parameter
):
    """Handles the story script generation."""
    try:
        script_path = generate_script(
            subject=user_prompt, # Pass user_prompt as subject
            subject_type=subject_type,
            story_length=story_length,
            complexity=complexity,
            user_prompt=user_prompt, # Keep user_prompt for internal use if needed by prompt engineering
            style_primary=style_primary,
            style_secondary=style_secondary,
            use_web_search=enable_web_search,
            additional_instructions=additional_instructions,
            language=language,
            output_dir=OUTPUT_SCRIPT_DIR
        )
        if script_path and os.path.exists(script_path):
            # Removed the third script_path output, which was for generated_script_path_display
            return script_path, f"Script generated: {os.path.basename(script_path)}", gr.update(value=None), gr.update(value=None)
        else:
            # Ensure the number of return values matches the modified outputs list
            return gr.update(value=None), "Error: Script generation failed. Path not returned or file does not exist.", gr.update(value=None), gr.update(value=None)
    except KeyError as e:
        if "GEMINI_API_KEY" in str(e):
            return gr.update(value=None), "Error: GEMINI_API_KEY not found. Please set it in your .env file or environment variables.", gr.update(value=None), gr.update(value=None)
        return gr.update(value=None), f"Error generating script: {e}", gr.update(value=None), gr.update(value=None)
    except Exception as e:
        return gr.update(value=None), f"An unexpected error occurred: {e}", gr.update(value=None), gr.update(value=None)

def handle_generate_speech_and_srt(script_file_from_state, script_file_from_upload, default_voice_selection): # Added default_voice_selection
    """Handles speech and SRT generation from either generated or uploaded script."""
    final_script_path = None
    if script_file_from_upload is not None:
        final_script_path = script_file_from_upload.name # Gradio provides a temp file path
        print(f"Processing uploaded script: {final_script_path}")
    elif script_file_from_state and os.path.exists(script_file_from_state):
        final_script_path = script_file_from_state
        print(f"Processing generated script from state: {final_script_path}")
    else:
        return "Error: No script provided or generated script path is invalid.", gr.update(value=None), gr.update(value=None), gr.update() # Keep state as is

    if not final_script_path:
        return "Error: Script path is missing.", gr.update(value=None), gr.update(value=None), gr.update() # Keep state as is

    try:
        audio_output_path, srt_output_path = convert_script_to_speech_and_srt(
            script_file_path=final_script_path,
            output_dir=config.BASE_OUTPUT_DIR, # Use BASE_OUTPUT_DIR from config
            default_voice_selection=default_voice_selection # Pass default_voice_selection
        )
        if audio_output_path and srt_output_path:
            return f"Audio and SRT generated!\nAudio: {os.path.basename(audio_output_path)}\nSRT: {os.path.basename(srt_output_path)}", audio_output_path, srt_output_path, gr.update() # Keep state as is
        elif audio_output_path:
            return f"Audio generated but SRT failed.\nAudio: {os.path.basename(audio_output_path)}", audio_output_path, gr.update(value=None), gr.update() # Keep state as is
        else:
            # convert_script_to_speech_and_srt might return None, None if an error occurred internally
            return "Error: Speech and SRT generation failed. Check logs.", gr.update(value=None), gr.update(value=None), gr.update() # Keep state as is
    except KeyError as e:
        if "GEMINI_API_KEY" in str(e):
            return "Error: GEMINI_API_KEY not found. Please set it in your .env file or environment variables.", gr.update(value=None), gr.update(value=None), gr.update()
        return f"Error generating speech/SRT: {e}", gr.update(value=None), gr.update(value=None), gr.update()
    except Exception as e:
        return f"An unexpected error occurred during speech/SRT generation: {e}", gr.update(value=None), gr.update(value=None), gr.update()

# --- Gradio Interface Definition ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("#  Storyteller AI: Script to Speech & Subtitles")
    gr.Markdown("Generate a story script using AI, then convert it to multi-speaker audio with synchronized SRT subtitles.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## Phase 1: Generate Story Script")
            subject_type = gr.Dropdown(label="Subject Type", choices=["short story", "news report", "educational content", "dialogue", "monologue", "advertisement script", "podcast segment"], value="short story", allow_custom_value=True)
            story_length = gr.Radio(label="Story Length", choices=["short", "medium", "long"], value="short") # Revert Radio component and fix default value
            complexity = gr.Radio(label="Complexity", choices=["simple", "intermediate", "advanced"], value=config.DEFAULT_COMPLEXITY)
            user_prompt = gr.Textbox(label="User Prompt", placeholder="e.g., A cat who dreams of flying", lines=3)
            language = gr.Dropdown(label="Language", choices=["English", "Arabic"], value=config.DEFAULT_LANGUAGE, allow_custom_value=True)
            style_primary = gr.Dropdown(label="Primary Style", choices=["narrative", "informative", "conversational", "dramatic", "humorous", "formal", "informal"], value=config.DEFAULT_PRIMARY_STYLE, allow_custom_value=True)
            style_secondary = gr.Dropdown(label="Secondary Style (Optional)", choices=["none", "suspenseful", "uplifting", "factual", "technical"], value=config.DEFAULT_SECONDARY_STYLE, allow_custom_value=True)
            enable_web_search = gr.Checkbox(label="Enable Web Search for Context", value=False)
            additional_instructions = gr.Textbox(label="Additional Instructions (Optional)", placeholder="e.g., Ensure there are at least 3 characters. The story should have a surprise ending.", lines=2)

            generate_script_btn = gr.Button("Generate Script", variant="primary")
            script_output_status = gr.Textbox(label="Script Generation Status", interactive=False)
            generated_script_path_display = gr.Textbox(label="Generated Script Path", interactive=False, visible=False) # For display/debug

        with gr.Column(scale=1):
            gr.Markdown("## Phase 2: Convert Script to Speech & SRT")
            gr.Markdown("Uses the script generated in Phase 1 or an uploaded script.")
            upload_script_file = gr.File(label="Upload Script File (Optional, .txt)", type="filepath", file_types=[".txt"])
            
            # New voice selection dropdown
            voice_choices = config.AVAILABLE_VOICES # Use voices from config
            default_voice_selection = gr.Dropdown(label="Default Voice for Narration/Unassigned Speakers", choices=voice_choices, value=config.DEFAULT_VOICE_NARRATOR, allow_custom_value=True) # Use default from config

            generate_speech_srt_btn = gr.Button("Generate Speech & SRT", variant="primary")
            speech_srt_status = gr.Textbox(label="Speech & SRT Generation Status", interactive=False, lines=3)
            
            audio_output_display = gr.Audio(label="Generated Audio", type="filepath", interactive=False)
            srt_output_display = gr.File(label="Generated SRT File", type="filepath", interactive=False, file_count="single")

    # --- Event Handlers ---
    generate_script_btn.click(
        fn=handle_generate_script,
        inputs=[
            subject_type, story_length, complexity, user_prompt,
            style_primary, style_secondary, enable_web_search, additional_instructions,
            language # Added language to inputs
        ],
        outputs=[script_path_state, script_output_status, audio_output_display, srt_output_display] # Clear previous audio/SRT, removed generated_script_path_display
    )

    generate_speech_srt_btn.click(
        fn=handle_generate_speech_and_srt,
        inputs=[script_path_state, upload_script_file, default_voice_selection], # Added default_voice_selection to inputs
        outputs=[speech_srt_status, audio_output_display, srt_output_display, script_path_state]
    )

if __name__ == "__main__":
    # Validate environment variable
    if not os.getenv("GEMINI_API_KEY"):
        raise EnvironmentError("GEMINI_API_KEY environment variable not set. Please set it before running.")
    
    demo.launch(debug=True)