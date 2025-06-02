import os
import sys
import re
from google import genai
from google.genai import types # Import types
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from datetime import datetime
import logging # Import logging

# Add the project root to the sys.path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.web_search import search_web, format_search_results
from app import config # Import config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@retry(
    wait=wait_exponential(multiplier=1, min=config.API_RETRY_DELAY_MIN, max=config.API_RETRY_DELAY_MAX),
    stop=stop_after_attempt(config.API_RETRY_ATTEMPTS),
    retry=retry_if_exception_type(Exception), # Catch all exceptions for retry
    reraise=True
)
def generate_search_query(client, model_name: str, subject: str, user_prompt: str) -> str:
    """
    Generates an optimized web search query using the LLM based on the subject and user prompt.
    """
    prompt = f"""
    Based on the following subject and user prompt, generate a concise and effective web search query.
    The query should be optimized to find relevant information for generating a story script.
    
    Subject: {subject}
    User Prompt: {user_prompt}
    
    Examples:
    Subject: "Impact of AI on journalism in the Middle East"
    User Prompt: "How is AI changing newsrooms?"
    Search Query: "AI impact on Middle East journalism newsroom changes"
    
    Subject: "The basics of Quantum Computing"
    User Prompt: "Explain quantum computing simply."
    Search Query: "Quantum Computing basics simple explanation"
    
    Generate only the search query, no additional text.
    """
    
    generation_config = {
        "temperature": 0.1, # Keep temperature low for factual query generation
        "top_p": 0.95,
        "max_output_tokens": 100,
    }

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[types.Content(parts=[types.Part.from_text(text=prompt)])],
            generation_config=generation_config,
        )
        
        generated_text = response.text
        if generated_text is not None:
            stripped_query = generated_text.strip()
            if stripped_query: # Ensure it's not empty after stripping
                return stripped_query
            else:
                logger.warning("Gemini returned an empty string for search query generation. Using fallback.")
        else:
            logger.warning("Gemini returned None for search query generation. Using fallback.")

        # Fallback logic
        fallback_query_parts = []
        if subject and subject.strip():
            fallback_query_parts.append(subject.strip())
        if user_prompt and user_prompt.strip() and user_prompt.strip() not in (s.strip() for s in fallback_query_parts):
            fallback_query_parts.append(user_prompt.strip())
        
        if not fallback_query_parts:
            logger.warning("Subject and user_prompt are empty or identical for search query fallback. Using a generic query.")
            return "general information" # A very generic fallback
            
        final_fallback_query = " ".join(fallback_query_parts)
        logger.info(f"Using fallback search query: {final_fallback_query}")
        return final_fallback_query

    except AttributeError as ae: # Specifically catch AttributeError if .text is missing or similar
        logger.error(f"AttributeError during search query generation (likely response.text was None or malformed): {ae}")
         # Fallback logic (repeated for clarity, could be refactored into a helper)
        fallback_query_parts = []
        if subject and subject.strip():
            fallback_query_parts.append(subject.strip())
        if user_prompt and user_prompt.strip() and user_prompt.strip() not in (s.strip() for s in fallback_query_parts):
            fallback_query_parts.append(user_prompt.strip())
        if not fallback_query_parts: return "general information"
        return " ".join(fallback_query_parts)
    except Exception as e:
        logger.error(f"Unexpected error generating search query: {e}")
        # Fallback logic (repeated for clarity)
        fallback_query_parts = []
        if subject and subject.strip():
            fallback_query_parts.append(subject.strip())
        if user_prompt and user_prompt.strip() and user_prompt.strip() not in (s.strip() for s in fallback_query_parts):
            fallback_query_parts.append(user_prompt.strip())
        if not fallback_query_parts: return "general information"
        return " ".join(fallback_query_parts)

@retry(
    wait=wait_exponential(multiplier=1, min=config.API_RETRY_DELAY_MIN, max=config.API_RETRY_DELAY_MAX),
    stop=stop_after_attempt(config.API_RETRY_ATTEMPTS),
    retry=retry_if_exception_type(Exception), # Catch all exceptions for retry
    reraise=True
)
def generate_script(
    subject: str,
    output_dir: str,
    language: str = "English",
    duration: str = "short",  # "short" (1-3 min), "medium" (4-7 min), "long" (8+ min)
    category: str = "Uncategorized",  # User-defined category
    content_type_area: str = "General",  # User-defined content type/area
    purpose: str = "General Information",  # User-defined purpose
    video_styles: list[str] = None,  # List of styles like ["Educational", "Storytelling"]
    use_web_search: bool = False,
    creativity: float = 0.7,  # 0.0 (factual) to 1.0 (highly creative)
    tone: str = "neutral",  # neutral, humorous, dramatic, inspirational
    target_audience: str = "general public", # Specific target audience
    key_message: str = "No specific key message", # Central message to convey
    emotional_arc: str = "neutral", # rising, falling, neutral, mixed
    # New parameters from Gradio UI
    subject_type: str = "short story",
    story_length: str = "short",
    complexity: str = "simple",
    user_prompt: str = "",
    style_primary: str = "narrative",
    style_secondary: str = "none",
    additional_instructions: str = ""
) -> str:
    """
    Generates a script based on the subject and various content parameters.
    Saves the script content to a unique file in the specified output directory.

    Args:
        subject (str): The subject of the content.
        output_dir (str): The directory to save the generated script file.
        language (str): The desired language for the script (e.g., "Arabic", "English").
        duration (str): Approximate desired duration ("short", "medium", "long").
        category (str): The category of the content.
        content_type_area (str): The specific type or subject area.
        purpose (str): The purpose of the video/content.
        video_styles (list[str]): A list of selected video styles.
        use_web_search (bool): Whether to use web search for context. Defaults to False.
        creativity (float): Level of creativity for the script (0.0 to 1.0).
        tone (str): The emotional tone of the script.
        target_audience (str): The intended audience for the script.
        key_message (str): The central message or takeaway.
        emotional_arc (str): The desired emotional progression of the narrative.

    Returns:
        str: The path to the saved script file.
    """
    if video_styles is None:
        video_styles = ["Informative"] # Default style if none provided

    # Initialize the Gemini client
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Use the specified model for text generation
    model_name = config.GEMINI_STORY_GEN_MODEL

    web_context = ""
    
    if use_web_search:
        try:
            # Generate optimized search query using LLM
            optimized_query = generate_search_query(client, model_name, subject, user_prompt)
            logger.info(f"Generated search query: {optimized_query}")
            
            if optimized_query and len(optimized_query.strip()) > 3: # Basic check for a meaningful query (e.g., not just "a")
                # Perform web search with the optimized query
                search_results = search_web(optimized_query) # Assuming search_web can handle empty results gracefully
                if search_results:
                    web_context = f"\n\nWeb Context:\n{format_search_results(search_results)}"
                else:
                    logger.info(f"Web search with query '{optimized_query}' yielded no results.")
                    web_context = "" # Ensure web_context is empty if no results
            else:
                logger.warning(f"Optimized search query ('{optimized_query}') was empty or too short. Skipping web search.")
                web_context = ""
        except Exception as e:
            logger.warning(f"Web search attempt failed with error: {e}. Proceeding without web context.")
            web_context = ""
    
    # Determine approximate word count based on duration
    if duration == "short":
        length_instruction = "approximately 150-300 words (1-3 minutes)"
    elif duration == "medium":
        length_instruction = "approximately 400-700 words (4-7 minutes)"
    elif duration == "long":
        length_instruction = "approximately 800-1200 words (8+ minutes)"
    else:
        length_instruction = "approximately 200-250 words (2-3 minutes)" # Default if duration is not recognized

    # Format video styles for the prompt
    formatted_video_styles = ", ".join(video_styles) if video_styles else "not specified"

    # Enhanced prompt engineering for better narrative structure and emotional engagement
    prompt_text = f"""
You are an expert AI scriptwriter specializing in {category} content. 
Generate a compelling script in {language} based on these detailed specifications:

**User-Provided Context**
- Subject Type: {subject_type}
- Story Length: {story_length}
- Complexity: {complexity}
- User Prompt: {user_prompt}
- Primary Style (UI): {style_primary}
- Secondary Style (UI): {style_secondary}
- Additional Instructions: {additional_instructions}

**Core Elements**
- Subject: {subject}
- Duration: {length_instruction}
- Purpose: {purpose}
- Primary Styles: {formatted_video_styles}
- Tone: {tone.capitalize()}
- Creativity Level: {creativity}/1.0 (0.0 is factual, 1.0 is highly imaginative)
- Target Audience: {target_audience}
- Key Message: {key_message}
- Emotional Arc: {emotional_arc} (e.g., rising tension, falling action, neutral, mixed emotions)

**Structural Requirements for Consistent Narrative Flow**
1. Opening (approx. 10-15% of script):
   - Hook the audience immediately (first 1-3 lines).
   - Clearly establish the context and introduce the main subject or problem.
   - Hint at the journey or discovery to come.
2. Development (approx. 60-70% of script):
   - Build the narrative with logical progression and rising action/insights.
   - Introduce new information, arguments, or character interactions.
   - Ensure smooth transitions between paragraphs and ideas.
   - If applicable, present challenges, conflicts, or questions that drive the story forward.
3. Climax/Turning Point (approx. 5-10% of script):
   - Create an emotional peak, a significant revelation, or the resolution of a central conflict.
   - This should be the most impactful part of the script.
4. Resolution/Conclusion (approx. 10-15% of script):
   - Provide a satisfying conclusion that ties up loose ends.
   - Offer clear takeaways, a call to action, or a final thought that resonates with the audience.
   - Reinforce the key message.

**Character Development** (if applicable, for multi-speaker scripts)
- Create distinct and memorable voices for different speakers.
- Develop subtle or explicit character arcs where appropriate, showing growth or change.
- Use natural, culturally appropriate dialogue that reveals personality and advances the plot.
- Ensure each character's dialogue contributes meaningfully to the narrative and emotional arc.

**Emotional Engagement Guidelines**
- Incorporate emotional hooks throughout the script to maintain audience interest.
- Use vivid sensory language and evocative descriptions to create immersive scenes.
- Build empathy for characters or connection to the subject matter.
- Vary sentence structure and pacing to enhance emotional impact.
- Include at least one memorable phrase, quote, or profound insight.

**Technical Specifications**
- First line of the script MUST be: "Style: [Primary Style], Tone: [{tone}]"
- Speaker labels: Clear and consistent (e.g., "Narrator:", "Expert:", "Character 1:"). Each speaker's dialogue should start on a new line.
- Language: Natural and fluent {language} with appropriate idioms and cultural nuances.
- Pacing: Match word density and sentence length to the specified duration target.
- Avoid jargon unless explicitly part of the content_type_area and explained.

**Web Context** (if available):{web_context}

**Output Format Example**
Style: Documentary, Tone: Inspirational

Narrator: في بداية الرحلة، نجد أنفسنا أمام تحديات عظيمة...
Historian: (مشيراً إلى الخريطة) هذه البقعة الصغيرة غيرت مجرى التاريخ...
Witness: شعرت بأنني جزء من شيء أكبر من ذاتي...
"""
    # Configure generation parameters
    generation_config = {
        "temperature": creativity,
        "top_p": 0.95,
        "max_output_tokens": 2048,
    }

    try:
        # Generate content
        response = client.models.generate_content(
            model=model_name,
            contents=[types.Content(parts=[types.Part.from_text(text=prompt_text)])],
            generation_config=generation_config,
        )
        
        # Log prompt feedback for debugging
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            logger.info(f"Gemini prompt feedback for story generation: {response.prompt_feedback}")
            if response.prompt_feedback.block_reason:
                logger.error(f"Gemini content generation for story was blocked. Reason: {response.prompt_feedback.block_reason}. This may cause formatting issues.")
        
        # Ensure response.text exists and is not None before trying to validate
        if not response.text:
            logger.error("Gemini response for story generation is empty or None.")
            raise ValueError("Generated script is empty or None from API.")

        # Robust validation of output format
        # Use a more flexible check for primary style if multiple styles are joined
        primary_style_to_check = style_primary.strip() # Use the direct primary style from input
        
        # Check if the script starts with the expected format
        # Make the check case-insensitive for style and tone for robustness
        expected_start_pattern = re.compile(
            rf"Style:\s*{re.escape(primary_style_to_check)}\s*,\s*Tone:\s*{re.escape(tone.capitalize())}",
            re.IGNORECASE
        )
        
        # Get the first line for checking
        first_line = response.text.strip().split('\n', 1)[0]

        if not expected_start_pattern.match(first_line):
            logger.error(f"Generated script first line: '{first_line}'")
            logger.error(f"Expected pattern: Style: {primary_style_to_check}, Tone: {tone.capitalize()}")
            # Log the beginning of the problematic script for debugging
            problematic_script_start = response.text[:500].replace('\n', '\\n') # Show first 500 chars, escape newlines for logging
            logger.error(f"Start of problematic script (up to 500 chars): '{problematic_script_start}...'")
            raise ValueError(f"Generated script does not adhere to the required starting format 'Style: [Primary Style], Tone: [Tone]'. Primary style checked: '{primary_style_to_check}', Tone: '{tone.capitalize()}'")
        
        if not re.search(r"^\s*\w+:", response.text, re.MULTILINE): # Allow leading spaces for speaker tags
            problematic_script_start = response.text[:500].replace('\n', '\\n')
            logger.error(f"Problematic script (up to 500 chars) lacking speaker labels: '{problematic_script_start}...'")
            raise ValueError("Generated script does not contain clear speaker labels (e.g., 'Narrator:', 'Character 1:'). Ensure labels are at the start of a line.")

    except types.StopCandidateException as sce: # More specific exception from Gemini
        logger.error(f"Gemini API call for story generation stopped due to safety or other reasons: {sce}")
        logger.error(f"Prompt feedback if available: {response.prompt_feedback if hasattr(response, 'prompt_feedback') else 'N/A'}")
        if hasattr(response, 'text') and response.text:
            problematic_script_start = response.text[:500].replace('\n', '\\n')
            logger.error(f"Content generated before stop (up to 500 chars): '{problematic_script_start}...'")
        raise # Re-raise for tenacity
    except Exception as e:
        logger.error(f"API call for story generation failed: {e}")
        # Check if response and response.text exist before trying to log
        if 'response' in locals() and hasattr(response, 'text') and response.text:
            problematic_script_start = response.text[:500].replace('\n', '\\n')
            logger.error(f"Content generated before error (if any, up to 500 chars): '{problematic_script_start}...'")
        raise # Re-raise the exception for tenacity to catch and retry

    # Save with descriptive filename
    # Sanitize subject for filename, allowing spaces and hyphens, and ensuring it's not too long
    safe_subject = "".join(c for c in subject if c.isalnum() or c in " _-").replace(" ", "_")[:40].strip()
    if not safe_subject: # Fallback if subject becomes empty after sanitization
        safe_subject = "untitled"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Include more parameters in filename for better descriptiveness
    file_name_parts = [
        "script",
        safe_subject,
        language.lower(),
        duration,
        tone,
        timestamp
    ]
    file_name = "_".join(part for part in file_name_parts if part) + ".txt"
    
    script_file_path = os.path.join(output_dir, file_name)

    os.makedirs(os.path.dirname(script_file_path), exist_ok=True)
    with open(script_file_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    logger.info(f"Script saved to: {script_file_path}")

    return script_file_path

if __name__ == "__main__":
    # Ensure the 'outputs/scripts' directory exists for testing
    output_script_dir = os.path.join(os.getcwd(), config.OUTPUT_SCRIPT_DIR) # Use config
    os.makedirs(output_script_dir, exist_ok=True)
    
    logger.info("🧪 Testing enhanced story generation...")
    
    tests = [
        {
            "subject": "Impact of AI on journalism in the Middle East",
            "language": "Arabic",
            "duration": "short",
            "category": "Current Events",
            "content_type_area": "Technology and Media",
            "purpose": "To inform the public",
            "video_styles": ["News", "Formal"],
            "use_web_search": True,
            "tone": "professional",
            "creativity": 0.4,
            "target_audience": "journalists and media professionals",
            "key_message": "AI is transforming journalism, requiring adaptation and ethical considerations.",
            "emotional_arc": "informative and slightly cautionary",
            "subject_type": "news report",
            "story_length": "short",
            "complexity": "intermediate",
            "user_prompt": "How is AI changing newsrooms?",
            "style_primary": "informative",
            "style_secondary": "none",
            "additional_instructions": "Focus on ethical challenges."
        },
        {
            "subject": "The basics of Quantum Computing",
            "language": "English",
            "duration": "medium",
            "category": "Science and Technology",
            "content_type_area": "Physics",
            "purpose": "To educate beginners",
            "video_styles": ["Educational", "Technical"],
            "use_web_search": False,
            "tone": "inspirational",
            "creativity": 0.7,
            "target_audience": "high school students and general science enthusiasts",
            "key_message": "Quantum computing holds immense potential to revolutionize technology.",
            "emotional_arc": "rising wonder and excitement",
            "subject_type": "educational content",
            "story_length": "medium",
            "complexity": "simple",
            "user_prompt": "Explain quantum computing simply.",
            "style_primary": "informative",
            "style_secondary": "technical",
            "additional_instructions": "Use analogies."
        },
        {
            "subject": "Traditional folk tales from Kuwait",
            "language": "Arabic",
            "duration": "long",
            "category": "Cultural Heritage",
            "content_type_area": "Folklore",
            "purpose": "To preserve cultural traditions",
            "video_styles": ["Storytelling", "Dramatic"],
            "use_web_search": True,
            "tone": "dramatic",
            "creativity": 0.9,
            "target_audience": "children and cultural enthusiasts",
            "key_message": "Kuwaiti folk tales are rich in wisdom and cultural identity.",
            "emotional_arc": "mixed, with moments of joy, sadness, and wisdom",
            "subject_type": "short story",
            "story_length": "long",
            "complexity": "advanced",
            "user_prompt": "Tell a traditional Kuwaiti folk tale.",
            "style_primary": "narrative",
            "style_secondary": "dramatic",
            "additional_instructions": "Include a moral lesson."
        }
    ]
    
    for i, test in enumerate(tests, 1):
        logger.info(f"\n🔬 Test #{i}: {test['subject']}")
        try:
            start_time = datetime.now()
            script_path = generate_script(**test, output_dir=output_script_dir)
            gen_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Generated in {gen_time:.1f}s: {os.path.basename(script_path)}")
            with open(script_path, "r", encoding="utf-8") as f:
                logger.info(f"\n📝 Content sample:\n{f.read()[:200]}...")
                
        except Exception as e:
            logger.error(f"❌ Failed: {str(e)}")
            # The retry mechanism is now handled by tenacity within generate_script
            # No need for manual retry logic here
