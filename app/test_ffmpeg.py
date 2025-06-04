import os
import sys
import time
from datetime import datetime

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.phase4_video import (
    check_ffmpeg,
    parse_srt_file,
    generate_ffmpeg_script,
    execute_ffmpeg_command,
    generate_video_from_assets,
    FFMPEG_AVAILABLE,
    FFMPEG_VERSION
)

def test_ffmpeg_availability():
    """Test if FFmpeg is available"""
    print("\n=== Testing FFmpeg Availability ===")
    print(f"FFmpeg available: {FFMPEG_AVAILABLE}")
    print(f"FFmpeg version: {FFMPEG_VERSION}")
    
    if not FFMPEG_AVAILABLE:
        print("FFmpeg is not available. Please install FFmpeg to continue.")
        return False
    
    return True

def test_parse_srt():
    """Test SRT parsing functionality"""
    print("\n=== Testing SRT Parsing ===")
    
    # Create a simple SRT file for testing
    test_srt_content = """
1
00:00:00,000 --> 00:00:05,000
This is the first subtitle.

2
00:00:05,500 --> 00:00:10,000
This is the second subtitle.

3
00:00:10,500 --> 00:00:15,000
This is the third subtitle.
"""
    
    test_srt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_subtitles.srt")
    
    with open(test_srt_path, "w", encoding="utf-8") as f:
        f.write(test_srt_content)
    
    print(f"Created test SRT file at: {test_srt_path}")
    
    # Parse the SRT file
    subtitles = parse_srt_file(test_srt_path)
    
    print(f"Parsed {len(subtitles)} subtitles:")
    for subtitle in subtitles:
        print(f"  {subtitle['index']}: {subtitle['start_time']} --> {subtitle['end_time']} ({subtitle['duration']}s)")
    
    return test_srt_path, subtitles

def test_generate_ffmpeg_script(srt_path):
    """Test FFmpeg script generation"""
    print("\n=== Testing FFmpeg Script Generation ===")
    
    # For a proper test, we need real audio and image files
    # Let's check if we have any existing audio files in the outputs directory
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs_test_phase2")
    audio_dir = os.path.join(outputs_dir, "audio")
    
    # Find an existing audio file or create a silent audio file
    test_audio_path = None
    if os.path.exists(audio_dir):
        for file in os.listdir(audio_dir):
            if file.endswith(".mp3") or file.endswith(".wav"):
                test_audio_path = os.path.join(audio_dir, file)
                print(f"Using existing audio file: {test_audio_path}")
                break
    
    if not test_audio_path:
        # Create a silent audio file using FFmpeg
        test_audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_audio.mp3")
        silent_cmd = f'ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 15 -q:a 9 -acodec libmp3lame "{test_audio_path}"'
        print(f"Creating silent audio file with command: {silent_cmd}")
        success, output = execute_ffmpeg_command(silent_cmd)
        if not success:
            print(f"Failed to create silent audio: {output}")
            test_audio_path = None
        else:
            print(f"Created silent audio file at: {test_audio_path}")
    
    if not test_audio_path:
        print("Could not create or find a valid audio file for testing.")
        return None, None, None, None
    
    # Create test images (color frames) using FFmpeg
    test_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")
    os.makedirs(test_images_dir, exist_ok=True)
    
    colors = ["red", "green", "blue"]
    test_image_paths = []
    
    for i, color in enumerate(colors):
        image_path = os.path.join(test_images_dir, f"test_image_{i}.png")
        img_cmd = f'ffmpeg -y -f lavfi -i color={color}:s=640x480 -frames:v 1 "{image_path}"'
        print(f"Creating {color} test image with command: {img_cmd}")
        success, output = execute_ffmpeg_command(img_cmd)
        if success:
            test_image_paths.append(image_path)
            print(f"Created test image at: {image_path}")
        else:
            print(f"Failed to create test image: {output}")
    
    if not test_image_paths:
        print("Could not create any valid test images.")
        return None, None, None, None
    
    print(f"Created {len(test_image_paths)} test images in: {test_images_dir}")
    
    # Generate FFmpeg script
    try:
        ffmpeg_script, output_path = generate_ffmpeg_script(
            audio_file=test_audio_path,
            srt_file=srt_path,
            scene_images=test_image_paths
        )
        
        print(f"Generated FFmpeg script:\n{ffmpeg_script}")
        print(f"Output path: {output_path}")
        
        return test_audio_path, test_image_paths, ffmpeg_script, output_path
    except Exception as e:
        print(f"Error generating FFmpeg script: {str(e)}")
        return None, None, None, None

def test_execute_ffmpeg_command():
    """Test executing a simple FFmpeg command"""
    print("\n=== Testing FFmpeg Command Execution ===")
    
    # Create a simple FFmpeg command that just displays version info
    test_cmd = "ffmpeg -version"
    
    print(f"Executing command: {test_cmd}")
    
    success, output = execute_ffmpeg_command(test_cmd)
    
    if success:
        print("FFmpeg command executed successfully")
        print(f"Output: {output[:100]}..." if len(output) > 100 else f"Output: {output}")
    else:
        print(f"FFmpeg command failed: {output}")
    
    return success

def test_generate_video(audio_path, srt_path, image_paths):
    """Test the complete video generation process"""
    print("\n=== Testing Complete Video Generation ===")
    
    if not audio_path or not srt_path or not image_paths or len(image_paths) == 0:
        print("Missing required inputs for video generation test.")
        return False, None
    
    # Verify all files exist
    if not os.path.exists(audio_path):
        print(f"Audio file does not exist: {audio_path}")
        return False, None
    
    if not os.path.exists(srt_path):
        print(f"SRT file does not exist: {srt_path}")
        return False, None
    
    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"Image file does not exist: {img_path}")
            return False, None
    
    # Set custom settings for faster testing
    custom_settings = {
        'width': 640,
        'height': 480,
        'fps': 30,
        'video_bitrate': '1M',  # Lower bitrate for faster encoding
        'audio_bitrate': '128k',
        'transition_duration': 0.5
    }
    
    print("Starting video generation...")
    print(f"Using audio: {audio_path}")
    print(f"Using SRT: {srt_path}")
    print(f"Using {len(image_paths)} images")
    print(f"Settings: {custom_settings}")
    
    start_time = time.time()
    
    try:
        success, result = generate_video_from_assets(
            audio_file=audio_path,
            srt_file=srt_path,
            scene_images=image_paths,
            custom_settings=custom_settings
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            print(f"Video generated successfully in {duration:.2f} seconds")
            print(f"Output video: {result}")
        else:
            print(f"Video generation failed: {result}")
        
        return success, result
    except Exception as e:
        print(f"Exception during video generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def cleanup_test_files(files_to_delete):
    """Clean up test files"""
    print("\n=== Cleaning Up Test Files ===")
    
    if not files_to_delete:
        print("No files to clean up.")
        return
    
    # First, filter out any None values or non-existent files
    valid_files = []
    for file_path in files_to_delete:
        if file_path and (os.path.exists(file_path) or os.path.isdir(file_path)):
            valid_files.append(file_path)
        elif file_path:
            print(f"File not found for cleanup: {file_path}")
    
    # Now clean up the valid files
    for file_path in valid_files:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                # Use shutil.rmtree for directories if available
                try:
                    import shutil
                    shutil.rmtree(file_path)
                    print(f"Deleted directory tree: {file_path}")
                except (ImportError, Exception) as e:
                    # Fall back to manual directory cleanup
                    print(f"Using manual directory cleanup for {file_path}")
                    for root, dirs, files in os.walk(file_path, topdown=False):
                        for name in files:
                            try:
                                os.remove(os.path.join(root, name))
                                print(f"Deleted file: {os.path.join(root, name)}")
                            except Exception as inner_e:
                                print(f"Error deleting file {os.path.join(root, name)}: {str(inner_e)}")
                        for name in dirs:
                            try:
                                os.rmdir(os.path.join(root, name))
                                print(f"Deleted subdirectory: {os.path.join(root, name)}")
                            except Exception as inner_e:
                                print(f"Error deleting directory {os.path.join(root, name)}: {str(inner_e)}")
                    try:
                        os.rmdir(file_path)
                        print(f"Deleted directory: {file_path}")
                    except Exception as inner_e:
                        print(f"Error deleting root directory {file_path}: {str(inner_e)}")
        except Exception as e:
            print(f"Error during cleanup of {file_path}: {str(e)}")
    
    print("Cleanup completed.")

def run_tests():
    """Run all tests"""
    print("=== Starting FFmpeg Integration Tests ===")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    files_to_cleanup = []
    test_success = True
    
    try:
        # Test FFmpeg availability
        if not test_ffmpeg_availability():
            print("Aborting tests as FFmpeg is not available.")
            return False
        
        # Test SRT parsing
        srt_path, subtitles = test_parse_srt()
        if srt_path:
            files_to_cleanup.append(srt_path)
        else:
            print("SRT parsing test failed.")
            test_success = False
        
        # Test FFmpeg script generation
        audio_path, image_paths, ffmpeg_script, output_path = test_generate_ffmpeg_script(srt_path)
        
        if audio_path:
            files_to_cleanup.append(audio_path)
        
        if image_paths and len(image_paths) > 0:
            # Add the individual image files to cleanup
            files_to_cleanup.extend(image_paths)
            # Also add the directory
            files_to_cleanup.append(os.path.dirname(image_paths[0]))
        
        # Test FFmpeg command execution
        if not test_execute_ffmpeg_command():
            print("FFmpeg command execution test failed.")
            test_success = False
        
        # Test complete video generation only if previous tests succeeded
        if audio_path and srt_path and image_paths and test_success:
            success, video_path = test_generate_video(audio_path, srt_path, image_paths)
            
            if success and video_path:
                files_to_cleanup.append(video_path)
                print("Video generation test succeeded.")
            else:
                print("Video generation test failed.")
                test_success = False
        else:
            print("Skipping video generation test due to missing prerequisites.")
    
    except Exception as e:
        print(f"Unexpected error during tests: {str(e)}")
        import traceback
        traceback.print_exc()
        test_success = False
    
    finally:
        # Always clean up test files, even if tests fail
        print("\nPerforming cleanup...")
        cleanup_test_files(files_to_cleanup)
    
    print("\n=== All Tests Completed ===" + (" Successfully" if test_success else " With Errors"))
    return test_success

if __name__ == "__main__":
    run_tests()