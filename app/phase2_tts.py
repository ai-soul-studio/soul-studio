import os
import re
from google import genai
from google.genai import types
from pydub import AudioSegment
from .utils import save_binary_file, convert_to_wav, parse_audio_mime_type # Assuming utils.py is in the same app directory
from . import config
import mimetypes
import datetime
import time
import logging

logger = logging.getLogger(__name__)

def parse_script_file(script_file_path: str) -> list[dict]:
    """
    Reads and parses a text script file to extract style/tone, speaker labels, text,
    and embedded visual prompts.

    Args:
        script_file_path (str): The path to the script file (.txt).

    Returns:
        list[dict]: A list of dictionaries, each containing 'text', 'speaker', 
                    'style' (the full first line), and 'visual_prompt'.
    """
    segments = []
    overall_style_info = "Unknown Style"
    current_visual_prompt = "No specific visual prompt for this segment." # Default

    with open(script_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return segments

    first_line = lines[0].strip()
    if first_line:
        overall_style_info = first_line
    else:
        overall_style_info = "Style: Unknown, Tone: Unknown"
    
    script_lines = lines[1:]

    for line in script_lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("VISUAL_PROMPT:"):
            current_visual_prompt = line.replace("VISUAL_PROMPT:", "", 1).strip()
            # This visual prompt applies to the NEXT dialogue/narration line
            continue 
        
        # This line is dialogue or narration
        speaker = "Narrator" # Default if no speaker label
        text_content = line

        if ":" in line:
            parts = line.split(":", 1)
            potential_speaker = parts[0].strip()
            if len(potential_speaker.split()) <= 3 and len(potential_speaker) < 30:
                speaker = potential_speaker
                text_content = parts[1].strip()
            # else, it's dialogue with a colon, speaker remains default, text_content is the whole line
        
        if text_content:
            segments.append({
                "text": text_content,
                "speaker": speaker,
                "style": overall_style_info,
                "visual_prompt": current_visual_prompt 
            })
            current_visual_prompt = "No specific visual prompt for this segment." # Reset for next potential segment without its own VP
                                                                                # Or, you might want to carry it forward if VPs are sparse.
                                                                                # For now, explicit VP per text segment is assumed by prompt.
    return segments

def _ms_to_srt_time(total_ms: int) -> str:
    if total_ms < 0: total_ms = 0
    hours = total_ms // 3600000
    total_ms %= 3600000
    minutes = total_ms // 60000
    total_ms %= 60000
    seconds = total_ms // 1000
    milliseconds = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def convert_script_to_speech_and_srt(script_file_path: str, output_dir: str, default_voice_selection: str = "Erinome", run_id: str = None) -> tuple[str | None, str | None, list[dict]]:
    """
    Converts a script file into multi-speaker audio, generates an SRT file,
    and returns detailed segment information including visual prompts.
    Uses run_id for consistent file naming if provided.

    Returns:
        tuple[str | None, str | None, list[dict]]: 
            Paths to the saved audio file, SRT file, and the list of processed_audio_segments_info.
    """
    script_segments = parse_script_file(script_file_path)
    if not script_segments:
        logger.warning("No segments found in script file.")
        return None, None, []

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    tts_model_name = config.GEMINI_TTS_MODEL
    
    combined_audio = AudioSegment.empty()
    processed_audio_segments_info = [] 

    total_segments = len(script_segments)
    logger.info(f"Found {total_segments} segments to process for TTS.")

    available_voices = config.AVAILABLE_VOICES
    speaker_voice_map = {}
    voice_index = 0
    
    for segment in script_segments:
        speaker_label = segment["speaker"]
        if speaker_label not in speaker_voice_map:
            speaker_voice_map[speaker_label] = available_voices[voice_index % len(available_voices)]
            voice_index += 1
    
    default_voice = default_voice_selection

    temp_audio_processing_dir = os.path.join(output_dir, "audio", "temp_segments")
    os.makedirs(temp_audio_processing_dir, exist_ok=True)

    for i, script_segment_data in enumerate(script_segments):
        logger.info(f"Processing TTS for segment {i + 1} of {total_segments}...")
        
        text_to_speak = script_segment_data["text"]
        speaker_label = script_segment_data["speaker"]
        visual_prompt_for_segment = script_segment_data["visual_prompt"] # Get the visual prompt
        
        voice_name_to_use = speaker_voice_map.get(speaker_label, default_voice)
        
        logger.info(f"TTS input for speaker {speaker_label} (voice {voice_name_to_use}): \"{text_to_speak[:100]}...\"")

        # API Call (same as your original, just ensuring it uses GEMINI_TTS_MODEL from config)
        contents = [types.Content(parts=[types.Part.from_text(text=text_to_speak)])]
        speech_settings = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name_to_use)
            )
        )
        # Top-level GenerateContentConfig with TTS specific fields directly
        api_call_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=speech_settings
        )
        
        segment_audio_pydub = None
        segment_duration_ms = 0

        try:
            response = client.models.generate_content(
                model=tts_model_name, 
                contents=contents, 
                config=api_call_config # Use the correctly structured GenerateContentConfig
            )
            time.sleep(config.TTS_RATE_LIMIT_DELAY)

            audio_data_bytes = None
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        inline_data = part.inline_data
                        audio_data_bytes = inline_data.data
                        mime_type_full = inline_data.mime_type
                        
                        file_extension = mimetypes.guess_extension(mime_type_full)
                        temp_audio_path_base = f"temp_segment_{i}"
                        audio_data_to_save = audio_data_bytes

                        if mime_type_full.startswith("audio/L16") or \
                           file_extension is None or \
                           file_extension.lower() not in ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.opus']:
                            logger.info(f"Segment {i}: Received raw audio ('{mime_type_full}'). Converting to WAV.")
                            try:
                                audio_data_to_save = convert_to_wav(audio_data_bytes, mime_type_full)
                                file_extension = ".wav"
                            except Exception as conversion_error:
                                logger.error(f"Error converting segment {i} to WAV: {conversion_error}. Skipping segment.")
                                audio_data_bytes = None
                                break 
                        
                        if audio_data_bytes is None: continue

                        temp_audio_path = os.path.join(temp_audio_processing_dir, f"{temp_audio_path_base}{file_extension}")
                        save_binary_file(temp_audio_path, audio_data_to_save)
                        
                        try:
                            current_segment_audio_pydub = AudioSegment.from_file(temp_audio_path)
                            segment_audio_pydub = current_segment_audio_pydub # Assign to outer scope var
                            segment_duration_ms = len(segment_audio_pydub)
                            combined_audio += segment_audio_pydub
                        except Exception as e:
                            logger.error(f"Error loading segment {i} from file {temp_audio_path}: {e}")
                        finally:
                            if os.path.exists(temp_audio_path):
                                try: os.remove(temp_audio_path)
                                except OSError as e: logger.warning(f"Could not remove temp file {temp_audio_path}: {e}")
                        break 
        except Exception as e:
            logger.error(f"Error calling Gemini API for segment {i} ('{text_to_speak[:30]}...'): {e}")
            if "RESOURCE_EXHAUSTED" in str(e):
                logger.warning("Rate limit likely hit.")
        
        processed_audio_segments_info.append({
            "text": text_to_speak, 
            "speaker": speaker_label, 
            "duration_ms": segment_duration_ms, # Use duration from loaded audio
            "visual_prompt": visual_prompt_for_segment # Store the visual prompt
        })
        if not segment_audio_pydub:
             logger.warning(f"No audio data processed for segment {i}: '{text_to_speak[:30]}...'")


    try:
        if os.path.exists(temp_audio_processing_dir) and not os.listdir(temp_audio_processing_dir):
            os.rmdir(temp_audio_processing_dir)
    except OSError as e:
        logger.warning(f"Could not remove empty temp directory {temp_audio_processing_dir}: {e}")

    audio_file_path = None
    file_identifier = run_id if run_id else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if len(combined_audio) > 0:
        final_audio_dir = os.path.join(output_dir, "audio")
        os.makedirs(final_audio_dir, exist_ok=True)
        audio_file_name = f"{file_identifier}_audio.mp3"
        audio_file_path = os.path.join(final_audio_dir, audio_file_name)
        combined_audio.export(audio_file_path, format="mp3")
        logger.info(f"Combined audio saved to: {audio_file_path}")
    else:
        logger.warning("No audio was combined. Audio file not created.")

    srt_content = []
    current_srt_time_ms = 0
    for idx, info in enumerate(processed_audio_segments_info):
        if info["duration_ms"] > 0 :
            start_time_str = _ms_to_srt_time(current_srt_time_ms)
            end_time_ms = current_srt_time_ms + info["duration_ms"]
            end_time_str = _ms_to_srt_time(end_time_ms)
            
            srt_content.append(str(idx + 1))
            srt_content.append(f"{start_time_str} --> {end_time_str}")
            # Visual prompt is not part of SRT text, but available in processed_audio_segments_info
            srt_content.append(f"{info['speaker']}: {info['text']}\n")
            
            current_srt_time_ms = end_time_ms
    
    srt_file_path = None
    if srt_content:
        final_srt_dir = os.path.join(output_dir, "srt")
        os.makedirs(final_srt_dir, exist_ok=True)
        srt_file_name = f"{file_identifier}_srt.srt"
        srt_file_path = os.path.join(final_srt_dir, srt_file_name)
        with open(srt_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
        logger.info(f"Final SRT saved to: {srt_file_path}")
    else:
        logger.warning("No content for SRT file. SRT file not created.")

    return audio_file_path, srt_file_path, processed_audio_segments_info # Return the segments info

if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is set
    if "GEMINI_API_KEY" not in os.environ:
        # Attempt to load from .env.local if key not in environment
        from dotenv import load_dotenv
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env.local') # Assuming .env.local is in the parent directory of 'app'
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
        
        if "GEMINI_API_KEY" not in os.environ:
            logger.error("Error: GEMINI_API_KEY environment variable not set. Please set it or add it to .env.local in the project root.")
            exit()
        else:
            logger.info("Loaded GEMINI_API_KEY from .env.local")


    # Configure basic logging for the test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Create a dummy script file for testing
    dummy_script_content = """Style: Epic Fantasy Narration, Tone: Majestic
Narrator: In a land of myth, and a time of magic... the destiny of a great kingdom rested on the shoulders of a young boy.
VISUAL_PROMPT: A vast, misty mountain range at dawn, a lone castle visible in the distance.
Speaker 1: The dragon approaches! We must warn the king!
VISUAL_PROMPT: A close-up of a worried face, looking towards a dark, stormy sky where a dragon silhouette is barely visible.
Speaker 2: We must stand our ground! For honor, for glory!
VISUAL_PROMPT: Two knights in shining armor drawing their swords, standing defiantly.
Narrator: And so, the battle for the ages began, under a sky filled with fire and shadow.
VISUAL_PROMPT: A wide shot of a medieval battle, dragons breathing fire, knights clashing.
"""
    # Define base output directory for testing
    test_base_output_dir = os.path.join(os.getcwd(), "outputs_test_phase2_visual") 
    os.makedirs(test_base_output_dir, exist_ok=True)

    # Define script input directory and path for testing
    test_script_input_dir = os.path.join(test_base_output_dir, "scripts_input_visual")
    os.makedirs(test_script_input_dir, exist_ok=True)
    dummy_script_path = os.path.join(test_script_input_dir, "dummy_visual_test_script.txt")

    with open(dummy_script_path, "w", encoding="utf-8") as f:
        f.write(dummy_script_content)

    logger.info(f"Attempting to process script: {dummy_script_path}")
    logger.info(f"Output will be in base directory: {test_base_output_dir}")

    try:
        # Note the change in return values: now includes processed_segments_info
        generated_audio_path, generated_srt_path, processed_segments_info = convert_script_to_speech_and_srt(
            dummy_script_path,
            test_base_output_dir,
            run_id="testrun_20230101_000000" # Added dummy run_id for testing
        )
        
        if generated_audio_path:
            logger.info(f"\nGenerated audio saved to: {generated_audio_path}")
        else:
            logger.warning("\nAudio generation failed or produced no output.")

        if generated_srt_path:
            logger.info(f"Generated SRT saved to: {generated_srt_path}")
            with open(generated_srt_path, "r", encoding="utf-8") as f:
                logger.info("\n--- Generated SRT Content ---")
                logger.info(f.read())
                logger.info("-----------------------------")
        else:
            logger.warning("SRT generation failed or produced no output.")

        if processed_segments_info:
            logger.info("\n--- Processed Segments Info (including Visual Prompts) ---")
            for i, segment_info in enumerate(processed_segments_info):
                logger.info(f"Segment {i+1}:")
                logger.info(f"  Speaker: {segment_info['speaker']}")
                logger.info(f"  Text: \"{segment_info['text'][:50]}...\"")
                logger.info(f"  Duration (ms): {segment_info['duration_ms']}")
                logger.info(f"  Visual Prompt: {segment_info['visual_prompt']}")
            logger.info("---------------------------------------------------------")
        else:
            logger.warning("No processed segment information returned.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during the test run: {e}", exc_info=True)
    finally:
        logger.info(f"\nTest finished. Check '{test_base_output_dir}' for outputs.")
