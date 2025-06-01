import gradio as gr
import os
from .phase1_story_gen import generate_story_script # Changed import
from .phase2_tts import convert_script_to_speech_and_srt # To be created in phase2_tts.py

# Ensure output directories exist
OUTPUTS_DIR = os.path.join(os.getcwd(), "outputs")
SCRIPT_OUTPUT_DIR = os.path.join(OUTPUTS_DIR, "scripts") # Changed from srt to scripts
AUDIO_OUTPUT_DIR = os.path.join(OUTPUTS_DIR, "audio")
SRT_OUTPUT_DIR = os.path.join(OUTPUTS_DIR, "srt_final") # For final SRT after TTS

os.makedirs(SCRIPT_OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
os.makedirs(SRT_OUTPUT_DIR, exist_ok=True)

def handle_generate_script(subject: str) -> tuple[str, str]:
    """
    Handles the story script generation and saving, updating the UI.
    """
    if not subject:
        return "Please enter a subject for the story.", None

    try:
        script_file_path = generate_story_script(subject, OUTPUTS_DIR)
        return f"Script generated and saved to: {script_file_path}", script_file_path
    except KeyError:
        return "Error: GEMINI_API_KEY environment variable not set. Please set it before running.", None
    except Exception as e:
        return f"An error occurred during script generation: {e}", None

def handle_generate_speech_and_srt(script_file_from_state: str, script_file_from_upload: gr.File = None) -> tuple[str, str, str]:
    """
    Handles the speech generation from script and final SRT creation, updating the UI.
    Prioritizes uploaded script file if available.
    """
    script_to_process = None
    if script_file_from_upload is not None:
        script_to_process = script_file_from_upload.name # .name gives the temp path of the uploaded file
    elif script_file_from_state and os.path.exists(script_file_from_state):
        script_to_process = script_file_from_state
    
    if not script_to_process:
        return "Please generate or upload a script file first.", None, None
    
    if not os.path.exists(script_to_process):
        return f"Script file not found: {script_to_process}", None, None

    try:
        # This function will now return paths for both audio and the new SRT
        audio_file_path, final_srt_path = convert_script_to_speech_and_srt(script_to_process, OUTPUTS_DIR)
        return f"Audio generated: {audio_file_path}\nSRT generated: {final_srt_path}", audio_file_path, final_srt_path
    except KeyError:
        return "Error: GEMINI_API_KEY environment variable not set. Please set it before running.", None, None
    except Exception as e:
        return f"An error occurred during audio/SRT generation: {e}", None, None

with gr.Blocks() as demo:
    gr.Markdown("# AI Storyteller with Multi-Speaker TTS")

    with gr.Row():
        with gr.Column():
            subject_input = gr.Textbox(label="Enter Story Subject", placeholder="e.g., A brave knight on a quest")
            generate_script_btn = gr.Button("Generate Story Script") # Changed button text
            script_output_message = gr.Textbox(label="Script Generation Status", interactive=False) # Changed label
            script_file_path_state = gr.State(value=None) # To store the path of the generated script
            
            gr.Markdown("--- OR ---")
            script_file_upload = gr.File(label="Upload Script File (.txt)", file_types=[".txt"]) # Changed label and file type


        with gr.Column():
            process_output_message = gr.Textbox(label="Processing Status", interactive=False) # Combined status
            audio_output = gr.Audio(label="Generated Audio", interactive=False)
            # We might want a way to download/view the final SRT as well
            final_srt_download = gr.File(label="Download Final SRT", interactive=False)
            generate_audio_srt_btn = gr.Button("Convert Script to Speech & Generate SRT") # Changed button text

    generate_script_btn.click(
        handle_generate_script, # Changed handler
        inputs=[subject_input],
        outputs=[script_output_message, script_file_path_state] # Changed output
    )

    generate_audio_srt_btn.click(
        handle_generate_speech_and_srt, # Changed handler
        inputs=[script_file_path_state, script_file_upload],
        outputs=[process_output_message, audio_output, final_srt_download] # Changed outputs
    )

if __name__ == "__main__":
    demo.launch(debug=True)
