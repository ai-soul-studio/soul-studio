import os
import re
import json
import subprocess
import tempfile
import shutil
import platform
import logging
from datetime import datetime
from app import config
import traceback # Added import for traceback

# Configure logging
logger = logging.getLogger(__name__)

# --- FFmpeg Configuration ---
FFMPEG_OUTPUT_DIR = os.path.join(config.BASE_OUTPUT_DIR, "videos")
os.makedirs(FFMPEG_OUTPUT_DIR, exist_ok=True)

# Check if FFmpeg is available
def check_ffmpeg():
    """Check if FFmpeg is installed and available in the system PATH.
    
    Returns:
        Tuple of (is_available, version_info)
    """
    try:
        # Check if ffmpeg is in the PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return False, "FFmpeg not found in system PATH"
        
        # Get FFmpeg version
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False # Do not raise exception on non-zero exit
        )
        
        if result.returncode == 0:
            # Extract version from the output
            version_info = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            return True, version_info
        else:
            return False, f"FFmpeg found but returned error: {result.stderr}"
    except Exception as e:
        return False, f"Error checking FFmpeg: {str(e)}"

# Get FFmpeg availability status
FFMPEG_AVAILABLE, FFMPEG_VERSION = check_ffmpeg()

# Default video settings
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080
DEFAULT_VIDEO_FPS = 30
DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_VIDEO_BITRATE = "4M" # Default to 4 Mbps
DEFAULT_AUDIO_BITRATE = "192k" # Default to 192 kbps
DEFAULT_SUBTITLE_FONT = "Arial"
DEFAULT_SUBTITLE_SIZE = 24
DEFAULT_SUBTITLE_COLOR = "white"
DEFAULT_SUBTITLE_BORDER = "black"
DEFAULT_SUBTITLE_BORDER_SIZE = 2
DEFAULT_VIDEO_QUALITY = 23 # CRF value for libx264 (0-51, lower is better quality)

# Transition settings
DEFAULT_TRANSITION_DURATION = 1.0  # seconds

def parse_srt_file(srt_file_path):
    """Parse an SRT file and return a list of subtitle entries.
    
    Args:
        srt_file_path: Path to the SRT file
        
    Returns:
        List of dictionaries with keys: index, start_time, end_time, text, start_seconds, end_seconds, duration
    """
    if not os.path.exists(srt_file_path):
        raise FileNotFoundError(f"SRT file not found: {srt_file_path}")
    
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split the content by double newline (which separates subtitle entries)
    subtitle_blocks = re.split(r'\n\n+', content.strip())
    subtitles = []
    
    for block in subtitle_blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3: # Need at least index, time, text
            continue  # Skip invalid blocks
        
        try:
            index = int(lines[0])
            time_line = lines[1]
            text = '\n'.join(lines[2:])  # Join all remaining lines as the subtitle text
            
            # Parse the time line (format: 00:00:00,000 --> 00:00:00,000)
            time_match = re.match(r'(\d+):(\d+):(\d+),(\d+)\s+-->\s+(\d+):(\d+):(\d+),(\d+)', time_line)
            if not time_match:
                logger.warning(f"Invalid time format in SRT block: {block}")
                continue  # Skip entries with invalid time format
            
            # Extract time components
            start_h, start_m, start_s, start_ms = map(int, time_match.groups()[:4])
            end_h, end_m, end_s, end_ms = map(int, time_match.groups()[4:])
            
            # Calculate start and end times in seconds
            start_seconds = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000.0
            end_seconds = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000.0
            
            subtitles.append({
                'index': index,
                'start_time': f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d}",
                'end_time': f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}",
                'text': text,
                'start_seconds': start_seconds,
                'end_seconds': end_seconds,
                'duration': max(0.1, end_seconds - start_seconds) # Ensure duration is positive and at least 0.1s
            })
        except ValueError as ve: # Catch if int conversion fails
            logger.warning(f"ValueError parsing subtitle index: {lines[0]} in block: {block}. Error: {ve}")
            continue
        except Exception as e:
            logger.error(f"Error parsing subtitle block: {block}. Error: {e}")
            continue
    
    return subtitles

def generate_ffmpeg_script(audio_file, srt_file, scene_images, output_file=None, custom_settings=None, run_id: str = None): # Added run_id
    """Generate an FFmpeg script to create a video from audio, SRT, and scene images.
    
    Args:
        audio_file: Path to the audio file
        srt_file: Path to the SRT file
        scene_images: List of image paths or dictionary mapping scene indices to image paths
        output_file: Path to the output video file (optional)
        custom_settings: Dictionary of custom video settings (optional)
        
    Returns:
        Tuple of (ffmpeg_script, output_file_path)
    """
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")
    
    if not os.path.exists(srt_file):
        raise FileNotFoundError(f"SRT file not found: {srt_file}")
    
    # Parse SRT file to get scene timings
    subtitles = parse_srt_file(srt_file)
    if not subtitles:
        raise ValueError("SRT file parsing yielded no valid subtitles.")

    # Prepare scene images
    scene_image_map = {}
    valid_images_for_script = []

    if isinstance(scene_images, list):
        for i, image_path in enumerate(scene_images):
            if i < len(subtitles): # Map to corresponding subtitle
                if image_path and os.path.exists(image_path):
                    scene_image_map[subtitles[i]['index']] = image_path
                    valid_images_for_script.append(image_path)
                else:
                    logger.warning(f"Image path for subtitle index {subtitles[i]['index']} not found or invalid: {image_path}")
            else: # More images than subtitles, log and ignore extra images
                 logger.warning(f"More images provided than subtitle entries. Ignoring extra image: {image_path}")
    elif isinstance(scene_images, dict):
        for scene_idx_key, image_path in scene_images.items():
            if image_path and os.path.exists(image_path):
                # Ensure key is int for consistent lookup
                try:
                    scene_idx_int = int(scene_idx_key)
                    scene_image_map[scene_idx_int] = image_path
                    valid_images_for_script.append(image_path)
                except ValueError:
                    logger.warning(f"Invalid scene index key in scene_images dict: {scene_idx_key}")
            else:
                logger.warning(f"Image path for scene index {scene_idx_key} not found or invalid: {image_path}")
    
    if not valid_images_for_script:
        # If no valid images, perhaps use a default blank image or raise error
        # For now, let's try to proceed, FFmpeg might handle it or create a very short video
        logger.warning("No valid images found to include in the video. The video might be very short or fail.")

    # Apply custom settings or use defaults
    settings = {
        'width': DEFAULT_VIDEO_WIDTH,
        'height': DEFAULT_VIDEO_HEIGHT,
        'fps': DEFAULT_VIDEO_FPS,
        'video_codec': DEFAULT_VIDEO_CODEC,
        'audio_codec': DEFAULT_AUDIO_CODEC,
        'video_bitrate': DEFAULT_VIDEO_BITRATE, # Added
        'audio_bitrate': DEFAULT_AUDIO_BITRATE,
        'subtitle_font': DEFAULT_SUBTITLE_FONT,
        'subtitle_size': DEFAULT_SUBTITLE_SIZE,
        'subtitle_color': DEFAULT_SUBTITLE_COLOR,
        'subtitle_border': DEFAULT_SUBTITLE_BORDER,
        'subtitle_border_size': DEFAULT_SUBTITLE_BORDER_SIZE,
        'transition_duration': DEFAULT_TRANSITION_DURATION,
        'video_quality': DEFAULT_VIDEO_QUALITY # Added
    }
    
    if custom_settings:
        if isinstance(custom_settings, dict):
            # Filter out None values from custom_settings before updating
            # And ensure numeric values are indeed numeric
            filtered_custom_settings = {}
            for k, v in custom_settings.items():
                if v is not None:
                    if k in ['width', 'height', 'fps', 'subtitle_size', 'subtitle_border_size', 'video_quality', 'transition_duration']:
                        try:
                            filtered_custom_settings[k] = int(v) if k != 'transition_duration' else float(v)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid numeric value for {k}: {v}. Using default.")
                    else:
                        filtered_custom_settings[k] = v
            settings.update(filtered_custom_settings)
        else:
            logger.warning(f"custom_settings is not a dictionary: {type(custom_settings)}, ignoring.")
    
    # Generate output file path if not provided
    if not output_file:
        file_identifier = run_id if run_id else f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_file = os.path.join(FFMPEG_OUTPUT_DIR, f"{file_identifier}_video.mp4")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    ffmpeg_cmd_parts = ["ffmpeg", "-y"] # Start with basic command
    
    # Add input images first (looping through subtitles to maintain order)
    # This is important for filter_complex stream indexing.
    image_input_streams_map = {} # Maps subtitle_index to ffmpeg_input_index
    ffmpeg_input_index = 0 # 0 will be audio

    # Add audio file as the first input
    ffmpeg_cmd_parts.extend(["-i", audio_file])
    ffmpeg_input_index += 1

    # Add image inputs
    subtitle_to_image_map = [] # List of (subtitle_data, image_path, ffmpeg_stream_index)
    for subtitle_entry in subtitles:
        image_path = scene_image_map.get(subtitle_entry['index'])
        if image_path and os.path.exists(image_path):
            ffmpeg_cmd_parts.extend(["-i", image_path])
            subtitle_to_image_map.append((subtitle_entry, image_path, ffmpeg_input_index))
            ffmpeg_input_index += 1
        else: # If no image for this subtitle, we might need to insert a blank or hold previous
            logger.warning(f"No image found for subtitle index {subtitle_entry['index']}. This subtitle might not have a visual.")
            # For simplicity, we'll skip adding an image input here.
            # The filter_complex logic will need to handle missing images.

    if not subtitle_to_image_map:
        raise ValueError("No valid images could be mapped to subtitles. Cannot generate video.")

    filter_complex_parts = []
    last_video_stream = ""
    total_video_segments = 0

    # Scale and prepare each image segment
    for i, (subtitle_data, img_path, stream_idx) in enumerate(subtitle_to_image_map):
        duration = subtitle_data['duration']
        # Scale, pad, set SAR
        filter_complex_parts.append(
            f"[{stream_idx}:v]scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease,pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1[scaled{i}]"
        )
        # Trim to duration and set PTS for this segment
        filter_complex_parts.append(
            f"[scaled{i}]trim=duration={duration},setpts=PTS-STARTPTS[vid_seg{i}]"
        )
        total_video_segments += 1
    
    # Concatenate video segments
    if total_video_segments > 0:
        concat_inputs = "".join([f"[vid_seg{i}]" for i in range(total_video_segments)])
        filter_complex_parts.append(
            f"{concat_inputs}concat=n={total_video_segments}:v=1:a=0[concatenated_video]"
        )
        last_video_stream = "[concatenated_video]"
    else: # Should not happen if we raise error earlier
        raise ValueError("No video segments to concatenate.")

    # Add subtitles using the subtitles filter
    # Note: Subtitle file paths need to be escaped for FFmpeg.
    # FFmpeg on Windows has issues with complex paths with subtitles filter. A simpler path or relative path might be better.
    # Or, ensure the path is correctly escaped.
    escaped_srt_path = srt_file.replace('\\', '/').replace(':', '\\\\:') if platform.system() == "Windows" else srt_file
    
    # Subtitle styling
    # Example: "FontName='Arial',FontSize=24,PrimaryColour=&H00FFFFFF,BorderStyle=1,OutlineColour=&H00000000,Outline=2"
    # Note: Colors are &HAABBGGRR for FFmpeg ASS styling. White: &H00FFFFFF, Black: &H00000000
    # For simplicity, we'll use common color names and let FFmpeg handle them if possible, or convert them.
    # PrimaryColour is text color, OutlineColour is border color.
    # BorderStyle=1 means outline + drop shadow. Outline=border_thickness.
    
    # Convert common color names to ASS format (approximate)
    def to_ass_color(color_name_or_hex):
        # Basic conversion, extend as needed
        color_map = {
            "white": "&HFFFFFF", # Alpha=00
            "black": "&H000000", # Alpha=00
            "red":   "&H0000FF",
            "green": "&H00FF00",
            "blue":  "&HFF0000",
            "yellow":"&H00FFFF",
        }
        # If it's a hex color, ensure it starts with #
        if color_name_or_hex.startswith('#'):
            hex_color = color_name_or_hex.lstrip('#')
            if len(hex_color) == 6: # RRGGBB
                return f"&H{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}" # Convert to BBGGRR
            elif len(hex_color) == 8: # AARRGGBB
                return f"&H{hex_color[6:8]}{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}" # Convert to AABBGGRR (alpha first)
        
        # Default alpha FF (opaque) if not specified by &H prefix
        color_val = color_map.get(color_name_or_hex.lower(), "&HFFFFFF") # Default to white
        if not color_val.startswith("&H"): # if it was a mapped name like "white"
             color_val = "&H" + "FF" + color_val.replace("&H","") # Add FF for alpha, remove original &H
        elif len(color_val) == 8: # &HBBGGRR
            color_val = "&H" + "FF" + color_val.replace("&H","") # Add FF for alpha

        return color_val


    style_args = f"FontName='{settings['subtitle_font']}',FontSize={settings['subtitle_size']}," \
                 f"PrimaryColour={to_ass_color(settings['subtitle_color'])}," \
                 f"BorderStyle=1,OutlineColour={to_ass_color(settings['subtitle_border'])}," \
                 f"Outline={settings['subtitle_border_size']}"

    filter_complex_parts.append(
        f"{last_video_stream}subtitles='{escaped_srt_path}':force_style='{style_args}'[video_with_subs]"
    )
    last_video_stream = "[video_with_subs]"

    ffmpeg_cmd_parts.extend(["-filter_complex", ";".join(filter_complex_parts)])
    
    # Map streams
    ffmpeg_cmd_parts.extend(["-map", last_video_stream]) # Map final video stream
    ffmpeg_cmd_parts.extend(["-map", "0:a"]) # Map audio from the first input (index 0)
    
    # Output options
    ffmpeg_cmd_parts.extend(["-c:v", settings['video_codec']])
    if settings['video_codec'] == 'libx264':
        ffmpeg_cmd_parts.extend(["-preset", "medium"]) # Good balance of speed and quality
        ffmpeg_cmd_parts.extend(["-crf", str(settings['video_quality'])]) # Constant Rate Factor
    elif settings.get('video_bitrate'): # If other codec or if bitrate is specified
         ffmpeg_cmd_parts.extend(["-b:v", str(settings['video_bitrate'])])

    ffmpeg_cmd_parts.extend(["-c:a", settings['audio_codec']])
    if settings.get('audio_bitrate'):
        ffmpeg_cmd_parts.extend(["-b:a", str(settings['audio_bitrate'])])
    
    ffmpeg_cmd_parts.extend(["-pix_fmt", "yuv420p"]) # For wide compatibility
    ffmpeg_cmd_parts.extend(["-r", str(settings['fps'])])
    ffmpeg_cmd_parts.append("-shortest") # Finish encoding when the shortest input stream ends
    
    ffmpeg_cmd_parts.append(output_file) # Add output file path
    
    # Join parts into a single string for execution, especially helpful for Windows.
    # However, subprocess on non-Windows prefers a list.
    # The execution function will handle this.
    final_ffmpeg_cmd_str = " ".join(f'"{part}"' if " " in part and not (part.startswith("'") and part.endswith("'")) else part for part in ffmpeg_cmd_parts)
    # Log the command string to be executed
    logger.info(f"Generated FFmpeg command string: {final_ffmpeg_cmd_str}")

    return final_ffmpeg_cmd_str, output_file # Return the string command

def execute_ffmpeg_command(ffmpeg_command_str): # Now expects a string
    """Execute an FFmpeg command string and return the result.
    
    Args:
        ffmpeg_command_str: The FFmpeg command string to execute
        
    Returns:
        Tuple of (success, output_or_error_message)
    """
    try:
        logger.info(f"Executing FFmpeg command: {ffmpeg_command_str}")
        
        # Use shell=True carefully. Given we construct the command, it's less risky.
        # On Windows, shell=True is often necessary for complex commands.
        # On Linux/macOS, it's better to pass a list of args if possible, but a string with shell=True also works.
        process = subprocess.Popen(
            ffmpeg_command_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True, # Execute via shell
            text=True, # Decode stdout/stderr as text
            universal_newlines=True # Ensure newlines are handled correctly
        )
        
        logger.info(f"Started FFmpeg process with PID: {process.pid}")
        
        # Capture output. communicate() waits for the process to complete.
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("FFmpeg command executed successfully.")
            logger.debug(f"FFmpeg stdout: {stdout}")
            return True, "FFmpeg command executed successfully"
        else:
            error_msg = f"FFmpeg error (code {process.returncode}):\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            logger.error(error_msg)
            return False, error_msg
    except FileNotFoundError:
        logger.error("FFmpeg executable not found. Please ensure FFmpeg is installed and in your system's PATH.")
        return False, "FFmpeg executable not found."
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Error executing FFmpeg command: {e}\nTraceback: {tb_str}")
        return False, f"Error executing FFmpeg command: {str(e)}"

def generate_video_from_assets(audio_file, srt_file, scene_images, output_file=None, custom_settings=None, run_id: str = None): # Added run_id
    """Generate a video from audio, SRT, and scene images using FFmpeg.
    
    Args:
        audio_file: Path to the audio file
        srt_file: Path to the SRT file
        scene_images: List of image paths or dictionary mapping scene indices to image paths
        output_file: Path to the output video file (optional)
        custom_settings: Dictionary of custom video settings (optional)
        run_id: Optional unique identifier for the generation run.
        
    Returns:
        Tuple of (success, output_file_path_or_error_message)
    """
    if not FFMPEG_AVAILABLE:
        logger.error(f"FFmpeg is not available or version info: {FFMPEG_VERSION}")
        return False, f"FFmpeg is not available: {FFMPEG_VERSION}. Please install FFmpeg to use this feature."
    
    try:
        if not audio_file or not os.path.exists(audio_file):
            return False, f"Audio file not found or not specified: {audio_file}"
        
        if not srt_file or not os.path.exists(srt_file):
            return False, f"SRT file not found or not specified: {srt_file}"
        
        if not scene_images: # Check if scene_images is empty or None
            return False, "No scene images provided."
        
        # Generate FFmpeg script (which is now a command string)
        ffmpeg_cmd_str, output_path = generate_ffmpeg_script(
            audio_file, srt_file, scene_images, output_file, custom_settings, run_id=run_id # Pass run_id
        )
        
        # Execute FFmpeg command string
        success, message = execute_ffmpeg_command(ffmpeg_cmd_str)
        
        if success:
            return True, output_path
        else:
            # Prepend context to the error message from FFmpeg
            return False, f"Video generation failed: {message}"
    except FileNotFoundError as fnf_error:
        logger.error(f"File not found during video generation: {fnf_error}")
        return False, f"File not found: {str(fnf_error)}"
    except ValueError as val_error:
        logger.error(f"ValueError during video generation: {val_error}")
        return False, f"Invalid value or configuration: {str(val_error)}"
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Unexpected error in generate_video_from_assets: {e}\nTraceback: {tb_str}")
        return False, f"An unexpected error occurred during video generation: {str(e)}"