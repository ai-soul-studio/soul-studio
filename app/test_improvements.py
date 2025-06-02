#!/usr/bin/env python3
"""
Test script to validate the improvements made to the audio analyzer application.
This script tests various components and ensures they work correctly.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import config
from app.utils import save_binary_file, parse_audio_mime_type, convert_to_wav
from app.web_search import search_web, format_search_results
from app.image_generator import extract_visual_prompt_from_script

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_config():
    """Test configuration constants."""
    logger.info("Testing configuration...")
    
    # Test that all required constants are defined
    required_constants = [
        'GEMINI_STORY_GEN_MODEL',
        'GEMINI_TTS_MODEL', 
        'GEMINI_IMAGE_MODEL',
        'API_RETRY_ATTEMPTS',
        'TTS_RATE_LIMIT_DELAY',
        'AVAILABLE_VOICES'
    ]
    
    for constant in required_constants:
        assert hasattr(config, constant), f"Missing configuration constant: {constant}"
        logger.info(f"✓ {constant}: {getattr(config, constant)}")
    
    # Test model names follow the required pattern
    assert config.GEMINI_STORY_GEN_MODEL == "gemini-2.5-flash-preview-05-20"
    assert config.GEMINI_TTS_MODEL == "gemini-2.5-flash-preview-tts"
    assert config.GEMINI_IMAGE_MODEL == "models/imagen-3.0-generate-002"
    
    logger.info("✓ Configuration test passed")

def test_utils():
    """Test utility functions."""
    logger.info("Testing utility functions...")
    
    # Test parse_audio_mime_type
    result = parse_audio_mime_type("audio/L16;rate=24000")
    assert result['bits_per_sample'] == 16
    assert result['rate'] == 24000
    logger.info("✓ parse_audio_mime_type works correctly")
    
    # Test save_binary_file
    test_data = b"test data"
    test_dir = "test_temp"
    test_file = os.path.join(test_dir, "test_output.bin")
    
    try:
        success = save_binary_file(test_file, test_data)
        assert success, "save_binary_file should return True on success"
        assert os.path.exists(test_file), "File should be created"
        
        with open(test_file, 'rb') as f:
            saved_data = f.read()
        assert saved_data == test_data, "Saved data should match original"
        
        # Clean up
        os.remove(test_file)
        os.rmdir(test_dir)
        logger.info("✓ save_binary_file works correctly")
    except Exception as e:
        logger.error(f"save_binary_file test failed: {e}")
        # Clean up on error
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
        raise

def test_web_search():
    """Test web search functionality."""
    logger.info("Testing web search...")
    
    # Test with a simple query
    results = search_web("test query", num_results=1)
    
    # Should return a list (empty if no API key, populated if API key exists)
    assert isinstance(results, list), "search_web should return a list"
    
    if results:
        # If we got results, test the structure
        result = results[0]
        assert 'title' in result
        assert 'url' in result
        assert 'description' in result
        logger.info("✓ Web search returned properly formatted results")
    else:
        logger.info("✓ Web search handled missing API key gracefully")
    
    # Test format_search_results
    test_results = [
        {'title': 'Test Title', 'url': 'http://example.com', 'description': 'Test description'}
    ]
    formatted = format_search_results(test_results)
    assert 'Test Title' in formatted
    assert 'http://example.com' in formatted
    logger.info("✓ format_search_results works correctly")

def test_image_generator():
    """Test image generation utilities."""
    logger.info("Testing image generator...")
    
    # Test extract_visual_prompt_from_script
    test_script = """
Style: Narrative, Tone: Inspirational

Narrator: In a world where technology meets creativity, we discover amazing possibilities.
Character: The future is bright with endless opportunities for innovation.
Narrator: Together, we can build something extraordinary.
"""
    
    prompt = extract_visual_prompt_from_script(test_script)
    assert isinstance(prompt, str), "extract_visual_prompt_from_script should return a string"
    assert len(prompt) > 0, "Prompt should not be empty"
    assert "Create a cinematic" in prompt, "Prompt should contain expected prefix"
    logger.info("✓ extract_visual_prompt_from_script works correctly")

def test_environment():
    """Test environment setup."""
    logger.info("Testing environment setup...")
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        logger.info("✓ GEMINI_API_KEY is set")
    else:
        logger.warning("⚠ GEMINI_API_KEY is not set (required for full functionality)")
    
    brave_key = os.getenv('BRAVE_API_KEY')
    if brave_key:
        logger.info("✓ BRAVE_API_KEY is set")
    else:
        logger.warning("⚠ BRAVE_API_KEY is not set (web search will not work)")

def main():
    """Run all tests."""
    logger.info("Starting comprehensive test suite...")
    
    try:
        test_environment()
        test_config()
        test_utils()
        test_web_search()
        test_image_generator()
        
        logger.info("🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)