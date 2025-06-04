import gradio as gr
import os
from dotenv import load_dotenv
from app.phase1_story_gen import generate_script
from app.phase2_tts import convert_script_to_speech_and_srt
# Corrected import: generate_image_from_script, generate_thumbnail_for_script, generate_scene_images_from_segments
from app.image_generator import generate_image_from_script, generate_thumbnail_for_script, generate_scene_images_from_segments
from app.phase4_video import generate_video_from_assets # Assuming phase4_video.py exists
from app import config
import logging # Added logging

load_dotenv()
logging.basicConfig(level=logging.INFO) # Setup basic logging for main
logger = logging.getLogger(__name__)

OUTPUT_SCRIPT_DIR = config.OUTPUT_SCRIPT_DIR
OUTPUT_AUDIO_DIR = config.OUTPUT_AUDIO_DIR
OUTPUT_SRT_DIR = config.OUTPUT_SRT_DIR
OUTPUT_IMAGE_DIR = config.OUTPUT_IMAGE_DIR
OUTPUT_VIDEO_DIR = config.OUTPUT_VIDEO_DIR # Added for consistency

os.makedirs(OUTPUT_SCRIPT_DIR, exist_ok=True)
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_SRT_DIR, exist_ok=True)
os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)
os.makedirs(OUTPUT_VIDEO_DIR, exist_ok=True) # Added for consistency

# --- State Variables ---
script_path_state = gr.Textbox(label="script_path_state_hidden", visible=False, interactive=True)
# New state to hold detailed script segments from Phase 2 (including visual prompts)
processed_segments_state = gr.State([])
run_id_state = gr.Textbox(label="run_id_state_hidden", visible=False, interactive=True) # New state for Run ID
next_steps_log_state = gr.Textbox(label="Next Steps / Log", interactive=False, lines=7, value="Welcome! Start by generating a script in Phase 1.")

def handle_generate_script(
    subject_type, story_length, complexity, user_prompt,
    style_primary, style_secondary, enable_web_search, additional_instructions,
    language # Removed enable_image_generation, art_style_for_script_image
    # enable_image_generation, art_style_for_script_image # Added art_style
):
    try:
        # Pass all relevant params from UI, including those used by generate_script
        # generate_script now returns (script_path, run_id)
        script_path, run_id = generate_script(
            subject=user_prompt, # Main subject/prompt from user
            output_dir=OUTPUT_SCRIPT_DIR,
            language=language,
            # category, content_type_area, purpose can be derived or set to defaults if not in UI
            # For now, using subject_type as a proxy for category if needed, or add to UI
            category=subject_type,
            use_web_search=enable_web_search,
            creativity=config.DEFAULT_CREATIVITY, # Assuming a default or could add to UI
            tone=config.DEFAULT_TONE, # Assuming a default or could add to UI
            # Pass UI specific params
            subject_type=subject_type,
            story_length=story_length,
            complexity=complexity,
            user_prompt=user_prompt, # Explicitly passing
            style_primary=style_primary,
            style_secondary=style_secondary,
            additional_instructions=additional_instructions
        )

        # image_path = None # Image generation removed from Phase 1
        status_message = ""

        if script_path and os.path.exists(script_path):
            status_message = f"Script generated: {os.path.basename(script_path)}"
            
            # Image generation in Phase 1 is removed.
            # if enable_image_generation:
            #     try:
            #         with open(script_path, 'r', encoding='utf-8') as f:
            #             script_content = f.read()
            #         # Pass art_style to generate_image_from_script
            #         # This call would need run_id if we kept it:
            #         # image_path = generate_image_from_script(script_content, OUTPUT_IMAGE_DIR, art_style_for_script_image, run_id=run_id)
            #         if image_path:
            #             status_message += f"\nImage generated: {os.path.basename(image_path)}"
            #         else:
            #             status_message += "\nImage generation (single script image) failed."
            #     except Exception as img_e:
            #         status_message += f"\nImage generation error: {str(img_e)}"

            next_log_message = f"✅ Phase 1 Complete: Script '{os.path.basename(script_path)}' generated."
            # if image_path:
            #     next_log_message += f"\n🖼️ Optional image '{os.path.basename(image_path)}' also generated."
            # else:
            #     next_log_message += "\nOptional image was not generated or failed." # No longer relevant here
            next_log_message += f"\nRun ID: {run_id}"
            next_log_message += "\n\n➡️ Next Steps:\n1. Proceed to Phase 2 to generate Speech & SRT using the generated script.\n2. (Optional) Upload a different script in Phase 2 if you prefer.\n3. Generate images (overview and scene-by-scene) in Phase 3."
            # Return None for script_image_display as it's removed
            # The 6th item in the return tuple corresponds to the removed script_image_display
            return script_path, run_id, status_message, gr.update(value=None), gr.update(value=None), next_log_message
        else:
            # script_path would be None if generate_script failed before returning run_id
            next_log_message = "❌ Error: Script generation failed. Please check the status message above and your inputs, then try again."
            # Adjust return tuple length
            return None, None, "Error: Script generation failed.", gr.update(value=None), gr.update(value=None), next_log_message
    except KeyError as e: # Keep your specific error handling
        logger.error(f"handle_generate_script KeyError: {e}", exc_info=True)
        next_log_message = f"❌ Error in Phase 1 (KeyError): {e}. Please check your inputs."
        return None, None, f"Error generating script (KeyError): {e}", None, None, next_log_message
    except Exception as e:
        logger.error(f"handle_generate_script error: {e}", exc_info=True)
        next_log_message = f"❌ An unexpected error occurred in Phase 1: {e}. Check logs for details."
        return None, None, f"An unexpected error occurred: {e}", None, None, next_log_message


def handle_generate_speech_and_srt(script_file_from_state, script_file_from_upload, default_voice_selection, run_id_from_state):
    final_script_path = None
    if script_file_from_upload is not None:
        final_script_path = script_file_from_upload.name
    elif script_file_from_state and os.path.exists(script_file_from_state):
        final_script_path = script_file_from_state
    else:
        log_msg = "❌ Error in Phase 2: No script provided or the script path from Phase 1 is invalid. Please generate a script in Phase 1 or upload one."
        return "Error: No script provided or path invalid.", None, None, [], gr.update(value=script_file_from_state), log_msg

    if not final_script_path:
        log_msg = "❌ Error in Phase 2: Script path is missing. Please generate a script in Phase 1 or upload one."
        return "Error: Script path is missing.", None, None, [], gr.update(value=script_file_from_state), log_msg

    try:
        # convert_script_to_speech_and_srt now returns processed_segments as the third item
        audio_output_path, srt_output_path, processed_segments = convert_script_to_speech_and_srt(
            script_file_path=final_script_path,
            output_dir=config.BASE_OUTPUT_DIR,
            default_voice_selection=default_voice_selection,
            run_id=run_id_from_state # Pass run_id
        )

        log_msg = ""
        if audio_output_path and srt_output_path:
            status_msg = f"Audio and SRT generated!\nAudio: {os.path.basename(audio_output_path)}\nSRT: {os.path.basename(srt_output_path)}"
            log_msg = f"✅ Phase 2 Complete: Audio and SRT generated.\n🔊 Audio: {os.path.basename(audio_output_path)}\n📄 SRT: {os.path.basename(srt_output_path)}\n\n➡️ Next Steps:\n1. Proceed to Phase 3 (Scene-by-Scene Images tab) to generate images for your video.\n2. (Optional) Generate a single overview image in Phase 3 (Single Script Image tab)."
        elif audio_output_path:
            status_msg = f"Audio generated, SRT failed.\nAudio: {os.path.basename(audio_output_path)}"
            log_msg = f"⚠️ Phase 2 Warning: Audio generated, but SRT generation failed.\n🔊 Audio: {os.path.basename(audio_output_path)}\nVideo generation in Phase 4 might be impacted without an SRT file.\n\n➡️ Next Steps:\n1. You can still try to generate scene images in Phase 3.\n2. Check logs for SRT generation errors."
        else:
            status_msg = "Error: Speech and/or SRT generation failed. Check logs."
            log_msg = "❌ Error in Phase 2: Speech and/or SRT generation failed. Please check the status message and logs."

        # Update the processed_segments_state
        return status_msg, audio_output_path, srt_output_path, processed_segments, gr.update(value=final_script_path), log_msg
    except Exception as e:
        logger.error(f"handle_generate_speech_and_srt error: {e}", exc_info=True)
        log_msg = f"❌ An unexpected error occurred in Phase 2: {e}. Check logs for details."
        return f"Unexpected error in speech/SRT: {e}", None, None, [], gr.update(value=final_script_path), log_msg


def handle_generate_single_image_main(script_file_from_state, art_style_selection, run_id_from_state): # Removed script_file_from_upload
    final_script_path = None
    # Always use the script from Phase 1 state
    if script_file_from_state and os.path.exists(script_file_from_state):
        final_script_path = script_file_from_state
    else:
        log_msg = "❌ Error in Phase 3 (Overview Image): No script available from Phase 1. Please generate a script first."
        return "Error: No script from Phase 1 for overview image.", None, log_msg

    # Redundant check as it's covered above, but kept for safety, can be removed.
    if not final_script_path:
        log_msg = "❌ Error in Phase 3 (Overview Image): Script path is missing. Please ensure a script was generated in Phase 1."
        return "Error: Script path missing for overview image.", None, log_msg

    try:
        with open(final_script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        # Pass art_style and run_id to generate_image_from_script
        # The run_id_from_state will be used for naming the overview image correctly.
        image_path = generate_image_from_script(script_content, OUTPUT_IMAGE_DIR, art_style_selection, run_id=run_id_from_state)
        if image_path:
            log_msg = f"🖼️ Phase 3 (Overview Image): Image '{os.path.basename(image_path)}' generated successfully for the current project."
            return f"Overview image generated: {os.path.basename(image_path)}", image_path, log_msg
        else:
            log_msg = "❌ Error in Phase 3 (Single Image): Image generation failed. Check status and logs."
            return "Error: Single image generation failed.", None, log_msg
    except Exception as e:
        logger.error(f"handle_generate_single_image_main error: {e}", exc_info=True)
        log_msg = f"❌ An unexpected error occurred in Phase 3 (Single Image): {e}. Check logs."
        return f"Error generating single image: {e}", None, log_msg


def handle_generate_scene_images(processed_segments_state, art_style_selection, run_id_from_state): # Renamed segments_from_state to processed_segments_state
    log_msg = ""
    if not processed_segments_state: # Check the renamed parameter
        log_msg = "❌ Error in Phase 3 (Scene Images): No processed script segments available. Please complete Phase 2 (Generate Speech & SRT) first."
        return "Error: No processed script segments available for scene images. Please generate speech & SRT first.", None, [], log_msg

    try:
        # generate_scene_images_from_segments now takes the segments list and art_style
        updated_segments_with_paths = generate_scene_images_from_segments(
            script_segments_with_visuals=processed_segments_state, # Use the renamed parameter
            output_dir=OUTPUT_IMAGE_DIR,
            art_style=art_style_selection,
            run_id=run_id_from_state # Pass run_id
        )

        if not updated_segments_with_paths:
            log_msg = "⚠️ Phase 3 (Scene Images): No images were generated or scene processing failed. Check status and logs."
            return "No images generated or scene processing failed.", None, [], log_msg

        gallery_images = []
        first_image_path = None
        for i, scene in enumerate(updated_segments_with_paths):
            if scene.get('image_path'):
                if first_image_path is None:
                    first_image_path = scene['image_path']
                caption = f"Scene {scene.get('scene_number', i+1)}: {scene.get('text', '')[:100]}..."
                gallery_images.append((scene['image_path'], caption))

        success_count = sum(1 for scene in updated_segments_with_paths if scene.get('image_path'))
        status_message = f"Generated {success_count} of {len(updated_segments_with_paths)} scene images."
        if success_count > 0:
            log_msg = f"✅ Phase 3 (Scene Images) Complete: Generated {success_count} of {len(updated_segments_with_paths)} scene images. Images are in the gallery.\n\n➡️ Next Steps:\n1. Proceed to Phase 4 to generate the complete video using these assets."
        else:
            log_msg = f"⚠️ Phase 3 (Scene Images): No images were successfully generated. Check status and logs. You might need to adjust prompts or art style."
        
        return status_message, first_image_path, gallery_images, log_msg
    except Exception as e:
        logger.error(f"handle_generate_scene_images error: {e}", exc_info=True)
        log_msg = f"❌ An unexpected error occurred in Phase 3 (Scene Images): {e}. Check logs."
        return f"Error generating scene images: {e}", None, [], log_msg


# handle_generate_video remains largely the same but ensure scene_images_data (from gallery)
# is correctly processed if you intend to use those specific images.
# If it's to use newly generated images, the flow would be different.
# For now, assuming it uses the gallery output which is image paths.
def handle_generate_video(audio_file_path, srt_file_path, scene_images_gallery_data, # scene_images_gallery_data is from gr.Gallery
                          video_width, video_height, video_fps,
                          video_bitrate, audio_bitrate, transition_duration, run_id_from_state): # Added run_id_from_state
    from app.phase4_video import FFMPEG_AVAILABLE, FFMPEG_VERSION # Local import for check
    log_msg = ""
    if not FFMPEG_AVAILABLE:
        log_msg = f"❌ Error in Phase 4: FFmpeg is not available ({FFMPEG_VERSION}). Please install FFmpeg and ensure it's in your system PATH to generate videos."
        return f"Error: FFmpeg not available ({FFMPEG_VERSION}). Install FFmpeg.", None, log_msg

    if not audio_file_path or not os.path.exists(audio_file_path):
        log_msg = "❌ Error in Phase 4: Audio file is missing or invalid. Please ensure audio was generated in Phase 2 or upload a valid audio file."
        return f"Error: Audio file missing or invalid: {audio_file_path}", None, log_msg
    if not srt_file_path or not os.path.exists(srt_file_path):
        log_msg = "❌ Error in Phase 4: SRT file is missing or invalid. Please ensure SRT was generated in Phase 2 or upload a valid SRT file."
        return f"Error: SRT file missing or invalid: {srt_file_path}", None, log_msg

    # Extract image paths from the gallery data if it's provided
    scene_image_paths = []
    if scene_images_gallery_data: # This is list of (filepath, caption) tuples
        scene_image_paths = [item[0] for item in scene_images_gallery_data if item and os.path.exists(item[0])]

    if not scene_image_paths:
        # As a fallback, if gallery is empty, consider if we should try to re-generate based on SRT.
        # For now, require images to be present in gallery if that's the source.
        # This part might need refinement based on desired UX (e.g. if user didn't click "Generate Scene Images")
        logger.warning("No scene images passed from gallery to video generation.")
        # Optionally, could try to call a function here to get image paths if SRT is present
        # but that would mean re-running image gen if not already done.
        # For this iteration, we assume images are provided if gallery data exists.
        # If you want video to work even if scene images were not explicitly generated and shown in gallery,
        # you'd need to pass the `processed_segments_state` here too and call `generate_scene_images_from_segments`
        # if `scene_image_paths` is empty.
        log_msg = "❌ Error in Phase 4: No scene images available from the gallery. Please generate scene images in Phase 3."
        return "Error: No scene images available from the gallery for video generation.", None, log_msg

    try:
        success, result = generate_video_from_assets(
            audio_file=audio_file_path,
            srt_file=srt_file_path,
            scene_images=scene_image_paths, # Pass the list of paths
            custom_settings={
                "width": int(video_width), "height": int(video_height), "fps": int(video_fps),
                "video_bitrate": video_bitrate, "audio_bitrate": audio_bitrate,
                "transition_duration": float(transition_duration)
            },
            run_id=run_id_from_state # Pass run_id
        )
        if success:
            log_msg = f"🎉 Video Generation Complete! Your video '{os.path.basename(result)}' has been generated successfully."
            return f"Video generated: {os.path.basename(result)}", result, log_msg
        else:
            log_msg = f"❌ Error in Phase 4: Video generation failed. Reason: {result}. Check status and logs."
            return f"Error generating video: {result}", None, log_msg
    except Exception as e:
        logger.error(f"handle_generate_video error: {e}", exc_info=True)
        log_msg = f"❌ An unexpected error occurred in Phase 4 (Video Generation): {e}. Check logs."
        return f"Unexpected error in video generation: {e}", None, log_msg


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Storyteller AI: Script to Speech, Subtitles, Images & Video")

    # Central Log/Next Steps area
    with gr.Row():
        next_steps_log = gr.Textbox(label="Next Steps / Log", interactive=False, lines=5, value="Welcome! Start by generating a script in Phase 1, or upload an existing script in Phase 2.") # Defined here

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## Phase 1: Generate Story Script")
            # script_path_state and processed_segments_state are already defined globally
            # ... (your existing Phase 1 UI inputs: subject_type, story_length, etc.)
            subject_type = gr.Dropdown(label="Subject Type", choices=["short story", "news report", "educational content", "dialogue", "monologue", "advertisement script", "podcast segment"], value="short story", allow_custom_value=True)
            story_length = gr.Radio(label="Story Length", choices=["short", "medium", "long"], value="short")
            complexity = gr.Radio(label="Complexity", choices=["simple", "intermediate", "advanced"], value=config.DEFAULT_COMPLEXITY)
            user_prompt = gr.Textbox(label="User Prompt", placeholder="e.g., A cat who dreams of flying", lines=3)
            language = gr.Dropdown(label="Language", choices=["English", "Arabic"], value=config.DEFAULT_LANGUAGE, allow_custom_value=True)
            style_primary = gr.Dropdown(label="Primary Style", choices=["narrative", "informative", "conversational", "dramatic", "humorous", "formal", "informal"], value=config.DEFAULT_PRIMARY_STYLE, allow_custom_value=True)
            style_secondary = gr.Dropdown(label="Secondary Style (Optional)", choices=["none", "suspenseful", "uplifting", "factual", "technical"], value=config.DEFAULT_SECONDARY_STYLE, allow_custom_value=True)
            enable_web_search = gr.Checkbox(label="Enable Web Search for Context", value=False)
            # enable_image_generation_p1 = gr.Checkbox(label="Generate Image for Script (Phase 1)", value=True) # REMOVED
            additional_instructions = gr.Textbox(label="Additional Instructions (Optional)", placeholder="e.g., Ensure 3 characters. Surprise ending.", lines=2)

            # Art style for the single image generated in Phase 1 - REMOVED
            # art_style_p1_image = gr.Dropdown(label="Art Style for Script Image", choices=config.AVAILABLE_ART_STYLES, value=config.DEFAULT_ART_STYLE)


            generate_script_btn = gr.Button("Generate Script", variant="primary") # Updated button text
            script_output_status = gr.Textbox(label="Script Generation Status", interactive=False)
            # script_path_state is already defined above

            # script_image_display = gr.Image(label="Generated Script Image (from Phase 1)", type="filepath", interactive=False) # REMOVED

        with gr.Column(scale=1):
            gr.Markdown("## Phase 2: Convert Script to Speech & SRT")
            upload_script_file_p2 = gr.File(label="Upload Script File (Optional, .txt)", type="filepath", file_types=[".txt"]) # Renamed for clarity
            voice_choices = config.AVAILABLE_VOICES
            default_voice_selection = gr.Dropdown(label="Default Voice for Narration", choices=voice_choices, value=config.DEFAULT_VOICE_NARRATOR)
            generate_speech_srt_btn = gr.Button("Generate Speech & SRT", variant="primary")
            speech_srt_status = gr.Textbox(label="Speech & SRT Status", interactive=False, lines=3)
            audio_output_display = gr.Audio(label="Generated Audio", type="filepath", interactive=False)
            srt_output_display = gr.File(label="Generated SRT File", type="filepath", interactive=False, file_count="single")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## Phase 3: Generate Images")
            art_style_images = gr.Dropdown(label="Art Style for Images", choices=config.AVAILABLE_ART_STYLES, value=config.DEFAULT_ART_STYLE) # Renamed

            gr.Markdown("### A. Overview/Thumbnail Image")
            gr.Markdown("Generate a single overview or thumbnail image for the **current script** (from Phase 1). Uses the 'Art Style for Images' selected above.")
            generate_single_image_btn = gr.Button("Generate Overview Image", variant="secondary")
            single_image_status = gr.Textbox(label="Overview Image Status", interactive=False)
            standalone_image_display = gr.Image(label="Generated Overview Image", type="filepath", interactive=False)

            gr.Markdown("---") # Visual separator

            gr.Markdown("### B. Scene-by-Scene Images")
            gr.Markdown("Uses script segments (including visual prompts and timings from Phase 2) to generate images for each scene. Uses the 'Art Style for Images' selected above.")
            generate_scene_images_btn = gr.Button("Generate Scene Images", variant="secondary")
            scene_images_status = gr.Textbox(label="Scene Images Status", interactive=False)
            scene_image_preview = gr.Image(label="First Scene Image Preview", type="filepath", interactive=False)
            scene_gallery_display = gr.Gallery(label="Scene Images Gallery", show_label=True, columns=[2], rows=[2], object_fit="contain", height="auto")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## Phase 4: Generate Complete Video")
            # ... (your existing Phase 4 UI inputs: audio, srt, video settings) ...
            # Inputs for audio and SRT for video - these can be wired from Phase 2 outputs
            # or allow uploads if user wants to use external files.
            # For simplicity, we'll assume they are wired or user uploads if Phase 2 wasn't run.
            gr.Markdown("### Video Assets\nAudio and SRT files below will be auto-filled if generated in Phase 2. Otherwise, you can upload them manually. Scene images are taken from the 'Scene Images Gallery' populated in Phase 3.")
            upload_audio_file_p4 = gr.Audio(label="Audio File for Video", type="filepath")
            upload_srt_file_p4 = gr.File(label="SRT File for Video", type="filepath", file_types=[".srt"])
            # The line below is now incorporated into the markdown above for better flow.
            # gr.Markdown("Scene images for video are taken from the 'Scene Images Gallery' above.")

            with gr.Accordion("Video Settings", open=False):
                with gr.Row():
                    video_width = gr.Number(label="Width", value=1920, precision=0)
                    video_height = gr.Number(label="Height", value=1080, precision=0)
                    video_fps = gr.Number(label="FPS", value=30, precision=0)
                with gr.Row():
                    video_bitrate = gr.Textbox(label="Video Bitrate", value="4M") # Default from config
                    audio_bitrate = gr.Textbox(label="Audio Bitrate", value="192k") # Default from config
                    transition_duration = gr.Slider(label="Transition Duration (s)", minimum=0, maximum=3, value=1, step=0.1)

            generate_video_btn = gr.Button("Generate Video", variant="primary")
            video_generation_status = gr.Textbox(label="Video Generation Status", interactive=False)
            video_output_display = gr.Video(label="Generated Video", interactive=False)

    # --- Event Handlers ---
    generate_script_btn.click(
        fn=handle_generate_script,
        inputs=[
            subject_type, story_length, complexity, user_prompt,
            style_primary, style_secondary, enable_web_search, additional_instructions,
            language # Removed enable_image_generation_p1, art_style_p1_image
        ],
        # script_image_display (6th item) removed from outputs list
        outputs=[script_path_state, run_id_state, script_output_status, audio_output_display, srt_output_display, next_steps_log]
    )

    generate_speech_srt_btn.click(
        fn=handle_generate_speech_and_srt,
        inputs=[script_path_state, upload_script_file_p2, default_voice_selection, run_id_state], # Added run_id_state
        # Output now includes processed_segments_state
        outputs=[speech_srt_status, audio_output_display, srt_output_display, processed_segments_state, script_path_state, next_steps_log]
    )

    generate_single_image_btn.click(
        fn=handle_generate_single_image_main, # Use renamed handler
        # Inputs: use script_path_state (if P1 generated) or the new upload_script_file_p3_single
        # For simplicity, let's assume it uses script_path_state or the P3 upload, and the P3 art style.
        # This might need a radio button to select source if both are present.
        # For now, prefer uploaded script if present for this specific button. - This comment is now outdated.
        # Inputs now only take script_path_state (for the current script), art style, and run_id.
        inputs=[script_path_state, art_style_images, run_id_state],
        outputs=[single_image_status, standalone_image_display, next_steps_log]
    )

    generate_scene_images_btn.click(
        fn=handle_generate_scene_images,
        inputs=[processed_segments_state, art_style_images, run_id_state],
        outputs=[scene_images_status, scene_image_preview, scene_gallery_display, next_steps_log]
    )

    # Wire outputs of Phase 2 to inputs of Phase 4
    audio_output_display.change(fn=lambda x: x, inputs=[audio_output_display], outputs=[upload_audio_file_p4])
    srt_output_display.change(fn=lambda x: x, inputs=[srt_output_display], outputs=[upload_srt_file_p4])

    # (Scene gallery is already an input to handle_generate_video)

    generate_video_btn.click(
        fn=handle_generate_video,
        inputs=[
            upload_audio_file_p4, upload_srt_file_p4, scene_gallery_display, # scene_gallery_display provides image paths
            video_width, video_height, video_fps,
            video_bitrate, audio_bitrate, transition_duration,
            run_id_state # Added run_id_state
        ],
        outputs=[video_generation_status, video_output_display, next_steps_log]
    )

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        # logger.critical("GEMINI_API_KEY environment variable not set.") # Use logger if defined globally before this
        print("CRITICAL: GEMINI_API_KEY environment variable not set. Please set it before running.")
        # raise EnvironmentError("GEMINI_API_KEY environment variable not set.") # Or raise
        exit(1) # Exit if key is missing

    demo.launch(debug=True)