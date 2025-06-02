import os
import re
from google import genai
from google.genai import types
from pydub import AudioSegment
from .utils import save_binary_file, convert_to_wav, parse_audio_mime_type
from . import config
import mimetypes
import datetime # Moved import to top
import time # For rate limiting
import logging

# Configure logging
logger = logging.getLogger(__name__)

def parse_script_file(script_file_path: str) -> list[dict]:
    """
    Reads and parses a text script file to extract style/tone, speaker labels, and text.

    Args:
        script_file_path (str): The path to the script file (.txt).

    Returns:
        list[dict]: A list of dictionaries, each containing 'text', 'speaker', and 'style'.
                    The 'style' is the same for all segments, taken from the first line.
    """
    segments = []
    overall_style = "Unknown Style"
    with open(script_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return segments

    # First line for style/tone
    first_line = lines[0].strip()
    script_lines = lines[1:] # Assume first line is always metadata

    style_match = re.search(r"Style:\s*([^,]+)", first_line, re.IGNORECASE)
    tone_match = re.search(r"Tone:\s*([^,]+)", first_line, re.IGNORECASE)

    extracted_styles = style_match.group(1).strip() if style_match else "Unknown Style"
    extracted_tone = tone_match.group(1).strip() if tone_match else "Unknown Tone"
    
    overall_style = f"Style: {extracted_styles}, Tone: {extracted_tone}"

    for line in script_lines:
        line = line.strip()
        if not line: # Skip empty lines
            continue

        speaker = "Narrator" # Default if no speaker label
        text = line
        if ":" in line:
            parts = line.split(":", 1)
            # Simple heuristic: if the part before ':' is short and doesn't contain too many spaces, assume it's a speaker
            potential_speaker = parts[0].strip()
            if len(potential_speaker.split()) <= 3 and len(potential_speaker) < 30: # Allow multi-word speaker names
                speaker = potential_speaker
                text = parts[1].strip()
            else: # If it looks more like dialogue with a colon in it, treat as text from default speaker
                text = line 
        
        if text: # Ensure there's text to add
            segments.append({
                "text": text,
                "speaker": speaker,
                "style": overall_style # Add style to each segment for potential future use
            })
    return segments

def _ms_to_srt_time(total_ms: int) -> str:
    """Converts total milliseconds to SRT time string (HH:MM:SS,ms)."""
    if total_ms < 0: total_ms = 0 # Ensure non-negative
    hours = total_ms // 3600000
    total_ms %= 3600000
    minutes = total_ms // 60000
    total_ms %= 60000
    seconds = total_ms // 1000
    milliseconds = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def convert_script_to_speech_and_srt(script_file_path: str, output_dir: str, default_voice_selection: str = "Erinome") -> tuple[str | None, str | None]:
    """
    Converts a script file into multi-speaker audio, then generates an SRT file based on audio durations.

    Args:
        script_file_path (str): The path to the input script file (.txt).
        output_dir (str): The base directory to save the generated audio and SRT files.
                          Audio will be in 'output_dir/audio', SRT in 'output_dir/srt_final'.

    Returns:
        tuple[str | None, str | None]: Paths to the saved audio file and SRT file, or None if errors occur.
    """
    script_segments = parse_script_file(script_file_path)
    if not script_segments:
        print("No segments found in script file.")
        return None, None

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    tts_model_name = "models/gemini-2.5-flash-preview-tts" # Added models/ prefix
    
    combined_audio = AudioSegment.empty()
    processed_audio_segments_info = [] # To store {'text', 'speaker', 'duration_ms'}

    # Add this line to get the total number of segments
    total_segments = len(script_segments)
    print(f"Found {total_segments} segments to process.")

    # Use available voices from configuration
    available_voices = config.AVAILABLE_VOICES
    
    # Initialize speaker voice map and a counter for round-robin assignment
    speaker_voice_map = {}
    voice_index = 0
    
    # Assign voices to speakers in the script
    for segment in script_segments:
        speaker_label = segment["speaker"]
        if speaker_label not in speaker_voice_map:
            speaker_voice_map[speaker_label] = available_voices[voice_index % len(available_voices)]
            voice_index += 1
    
    # Default voice if a speaker somehow doesn't get mapped
    default_voice = default_voice_selection

    temp_audio_processing_dir = os.path.join(output_dir, "audio", "temp_segments")
    os.makedirs(temp_audio_processing_dir, exist_ok=True)

    for i, script_segment_data in enumerate(script_segments):
        # Add this line to print progress
        print(f"Processing segment {i + 1} of {total_segments}...")
        
        text_to_speak = script_segment_data["text"]
        speaker_label = script_segment_data["speaker"]
        
        voice_name_to_use = speaker_voice_map.get(speaker_label, default_voice)

        contents = [types.Content(parts=[types.Part.from_text(text=text_to_speak)])]
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name_to_use)
            )
        )
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"], speech_config=speech_config
        )

        try:
            response = client.models.generate_content(
                model=tts_model_name, 
                contents=contents, 
                generation_config=generate_content_config
            )
            time.sleep(config.TTS_RATE_LIMIT_DELAY) # Wait to respect API rate limits
        except Exception as e:
            logger.error(f"Error calling Gemini API for segment {i} ('{text_to_speak[:30]}...'): {e}")
            processed_audio_segments_info.append({
                "text": text_to_speak, "speaker": speaker_label, "duration_ms": 0, "audio_segment": None
            })
            if "RESOURCE_EXHAUSTED" in str(e):
                logger.warning("Rate limit likely hit. Consider increasing sleep time or checking API quota.")
            continue

        audio_data_bytes = None
        segment_audio_pydub = None

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    inline_data = part.inline_data
                    audio_data_bytes = inline_data.data
                    mime_type_full = inline_data.mime_type
                    
                    # Always use file-based conversion for robustness
                    file_extension = mimetypes.guess_extension(mime_type_full)
                    temp_audio_path_base = f"temp_segment_{i}"
                    audio_data_to_save = audio_data_bytes

                    # If mime type is L16, or if extension is not a common audio one, convert to WAV
                    if mime_type_full.startswith("audio/L16") or \
                       file_extension is None or \
                       file_extension.lower() not in ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.opus']: # Added more common types
                        
                        # --- MODIFIED LINE ---
                        print(f"Segment {i}: Received raw audio ('{mime_type_full}'). Adding WAV header.")
                        # --- END MODIFIED LINE ---
                        
                        try:
                            audio_data_to_save = convert_to_wav(audio_data_bytes, mime_type_full)
                            file_extension = ".wav"
                        except Exception as conversion_error:
                            print(f"Error converting segment {i} to WAV: {conversion_error}. Skipping segment.")
                            audio_data_bytes = None # Prevent further processing of this segment
                            break # Break from parts loop
                    
                    if audio_data_bytes is None: # If conversion failed
                        continue # Continue to next script_segment_data

                    temp_audio_path = os.path.join(temp_audio_processing_dir, f"{temp_audio_path_base}{file_extension}")
                    save_binary_file(temp_audio_path, audio_data_to_save)
                    
                    try:
                        segment_audio_pydub = AudioSegment.from_file(temp_audio_path)
                    except Exception as e:
                        print(f"Error loading segment {i} from file {temp_audio_path}: {e}")
                    finally:
                        if os.path.exists(temp_audio_path):
                            try:
                                os.remove(temp_audio_path)
                            except OSError as e:
                                print(f"Warning: Could not remove temp file {temp_audio_path}: {e}")
                    break # Processed audio data for this segment (from inline_data.data)
        
        if segment_audio_pydub:
            combined_audio += segment_audio_pydub
            processed_audio_segments_info.append({
                "text": text_to_speak, 
                "speaker": speaker_label, 
                "duration_ms": len(segment_audio_pydub),
                "audio_segment": segment_audio_pydub # Storing for potential direct use, though duration is key
            })
        else:
            print(f"Warning: No audio processed for segment {i}: '{text_to_speak[:30]}...'")
            processed_audio_segments_info.append({
                "text": text_to_speak, "speaker": speaker_label, "duration_ms": 0, "audio_segment": None
            })

    # Clean up temp segment directory if empty
    try:
        if os.path.exists(temp_audio_processing_dir) and not os.listdir(temp_audio_processing_dir):
            os.rmdir(temp_audio_processing_dir)
    except OSError as e:
        print(f"Warning: Could not remove empty temp directory {temp_audio_processing_dir}: {e}")


    # Save combined audio
    audio_file_path = None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if len(combined_audio) > 0:
        final_audio_dir = os.path.join(output_dir, "audio")
        os.makedirs(final_audio_dir, exist_ok=True)
        audio_file_name = f"story_narration_{ts}.mp3"
        audio_file_path = os.path.join(final_audio_dir, audio_file_name)
        combined_audio.export(audio_file_path, format="mp3")
        print(f"Combined audio saved to: {audio_file_path}")
    else:
        print("No audio was combined. Audio file not created.")

    # Generate SRT file
    srt_content = []
    current_srt_time_ms = 0
    for idx, info in enumerate(processed_audio_segments_info):
        if info["duration_ms"] > 0 : # Only include segments that have actual audio
            start_time_str = _ms_to_srt_time(current_srt_time_ms)
            end_time_ms = current_srt_time_ms + info["duration_ms"]
            end_time_str = _ms_to_srt_time(end_time_ms)
            
            srt_content.append(str(idx + 1))
            srt_content.append(f"{start_time_str} --> {end_time_str}")
            srt_content.append(f"{info['speaker']}: {info['text']}\n") # Add speaker to text line
            
            current_srt_time_ms = end_time_ms
    
    srt_file_path = None
    if srt_content:
        final_srt_dir = os.path.join(output_dir, "srt")
        os.makedirs(final_srt_dir, exist_ok=True)
        srt_file_name = f"final_story_{ts}.srt"
        srt_file_path = os.path.join(final_srt_dir, srt_file_name)
        with open(srt_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
        print(f"Final SRT saved to: {srt_file_path}")
    else:
        print("No content for SRT file. SRT file not created.")

    return audio_file_path, srt_file_path


if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is set
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY environment variable not set. Please set it before running.")
        exit()

    # Create a dummy script file for testing
    dummy_script_content = """Style: Epic Fantasy Narration
Narrator: In a land of myth, and a time of magic...
Speaker 1: The dragon approaches!
Speaker 2: We must stand our ground!
Narrator: And so, the battle began.
"""
    # Define base output directory for testing
    test_base_output_dir = os.path.join(os.getcwd(), "outputs_test_phase2") # Use a distinct test output
    os.makedirs(test_base_output_dir, exist_ok=True)

    # Define script input directory and path for testing
    test_script_input_dir = os.path.join(test_base_output_dir, "scripts_input")
    os.makedirs(test_script_input_dir, exist_ok=True)
    dummy_script_path = os.path.join(test_script_input_dir, "dummy_test_script.txt")

    with open(dummy_script_path, "w", encoding="utf-8") as f:
        f.write(dummy_script_content)

    # Output subdirectories will be created by the function if they don't exist
    # e.g., test_base_output_dir/audio, test_base_output_dir/srt_final

    print(f"Attempting to process script: {dummy_script_path}")
    print(f"Output will be in base directory: {test_base_output_dir}")

    try:
        generated_audio_path, generated_srt_path = convert_script_to_speech_and_srt(
            dummy_script_path, 
            test_base_output_dir # Pass the base output directory
        )
        
        if generated_audio_path:
            print(f"\nGenerated audio saved to: {generated_audio_path}")
            # play(AudioSegment.from_file(generated_audio_path)) # Optional playback
        else:
            print("\nAudio generation failed or produced no output.")

        if generated_srt_path:
            print(f"Generated SRT saved to: {generated_srt_path}")
            with open(generated_srt_path, "r", encoding="utf-8") as f:
                print("\n--- Generated SRT Content ---")
                print(f.read())
                print("-----------------------------")
        else:
            print("SRT generation failed or produced no output.")

    except Exception as e:
        print(f"An unexpected error occurred during the test run: {e}")
    finally:
        # Clean up dummy script file (optional, good for automated tests)
        # if os.path.exists(dummy_script_path):
        #     os.remove(dummy_script_path)
        # Consider cleaning up test_base_output_dir as well if it's purely for transient tests.
        print(f"\nTest finished. Check '{test_base_output_dir}' for outputs.")
