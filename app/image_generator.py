import os
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from . import config
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

@retry(
    wait=wait_exponential(multiplier=1, min=config.API_RETRY_DELAY_MIN, max=config.API_RETRY_DELAY_MAX),
    stop=stop_after_attempt(config.API_RETRY_ATTEMPTS),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def generate_image_from_script(script_content: str, output_dir: str = None) -> str:
    """
    Generate an image based on script content using Google's Imagen model.
    
    Args:
        script_content (str): The script content to generate image from
        output_dir (str): Directory to save the generated image
        
    Returns:
        str: Path to the generated image file
    """
    if output_dir is None:
        output_dir = config.OUTPUT_IMAGE_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract a visual prompt from the script content
    visual_prompt = extract_visual_prompt_from_script(script_content)
    
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        result = client.models.generate_images(
            model=config.GEMINI_IMAGE_MODEL,
            prompt=visual_prompt,
            config=dict(
                number_of_images=1,
                output_mime_type="image/jpeg",
                person_generation="ALLOW_ADULT",
                aspect_ratio="1:1",
            ),
        )
        
        if not result.generated_images:
            logger.warning("No images generated.")
            return None
            
        if len(result.generated_images) != 1:
            logger.warning("Number of images generated does not match the requested number.")
        
        # Save the generated image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"generated_image_{timestamp}.jpg"
        image_path = os.path.join(output_dir, image_filename)
        
        for generated_image in result.generated_images:
            image = Image.open(BytesIO(generated_image.image.image_bytes))
            image.save(image_path, "JPEG")
            logger.info(f"Image saved to: {image_path}")
            return image_path
            
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise

def extract_visual_prompt_from_script(script_content: str) -> str:
    """
    Extract a visual description from script content for image generation.
    
    Args:
        script_content (str): The script content
        
    Returns:
        str: A visual prompt for image generation
    """
    # Remove speaker labels and extract descriptive content
    lines = script_content.split('\n')
    descriptive_lines = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Style:'):
            continue
            
        # Remove speaker labels (e.g., "Narrator:", "Character:")
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                line = parts[1].strip()
        
        descriptive_lines.append(line)
    
    # Take the first few lines for visual context
    visual_content = ' '.join(descriptive_lines[:3])
    
    # Create a focused visual prompt
    visual_prompt = f"Create a cinematic, high-quality image representing: {visual_content[:200]}..."
    
    logger.info(f"Generated visual prompt: {visual_prompt[:100]}...")
    return visual_prompt

def generate_thumbnail_for_script(script_path: str, output_dir: str = None) -> str:
    """
    Generate a thumbnail image for a script file.
    
    Args:
        script_path (str): Path to the script file
        output_dir (str): Directory to save the thumbnail
        
    Returns:
        str: Path to the generated thumbnail
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        return generate_image_from_script(script_content, output_dir)
        
    except Exception as e:
        logger.error(f"Error generating thumbnail for script {script_path}: {e}")
        return None