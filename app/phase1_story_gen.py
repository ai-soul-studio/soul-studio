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
    
    try:
        # Ensure client is properly initialized (passed as arg or initialized here if not)
        if client is None:
             api_key = os.environ.get("GEMINI_API_KEY")
             if not api_key:
                 raise ValueError("GEMINI_API_KEY not found in environment variables.")
             client = genai.Client(api_key=api_key)

        response = client.models.generate_content( # Corrected: client.generate_content for gemini-pro, or client.models.generate_content
            model=model_name, # Assuming model_name is something like 'models/gemini-pro' or a specific generative model
            contents=[types.Content(parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(
                 temperature=0.9,
                 max_output_tokens=2000,
                 tools=[], # Explicitly set tools to an empty list
             ),
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
        MAX_FALLBACK_QUERY_LENGTH = 250
        s_subject = subject.strip() if subject else ""
        s_user_prompt = user_prompt.strip() if user_prompt else ""
        final_fallback_query = ""
        if s_subject and len(s_subject) < MAX_FALLBACK_QUERY_LENGTH // 2:
            final_fallback_query = s_subject
            if s_user_prompt and s_user_prompt != s_subject:
                remaining_length = MAX_FALLBACK_QUERY_LENGTH - len(final_fallback_query) - 1
                if remaining_length > 10:
                    final_fallback_query += " " + s_user_prompt[:remaining_length]
        elif s_user_prompt and len(s_user_prompt) < MAX_FALLBACK_QUERY_LENGTH // 2:
            final_fallback_query = s_user_prompt
        elif s_subject:
            final_fallback_query = s_subject[:MAX_FALLBACK_QUERY_LENGTH]
        elif s_user_prompt:
            final_fallback_query = s_user_prompt[:MAX_FALLBACK_QUERY_LENGTH]
        else:
            final_fallback_query = "general information"
        final_fallback_query = final_fallback_query.strip()
        if not final_fallback_query:
             final_fallback_query = "general topic information"
        logger.info(f"Using fallback search query: {final_fallback_query}")
        return final_fallback_query

    except AttributeError as ae:
        logger.error(f"AttributeError during search query generation: {ae}")
        return subject.strip()[:200] if subject and subject.strip() else "general information"
    except Exception as e:
        logger.error(f"Unexpected error generating search query: {e}")
        return subject.strip()[:200] if subject and subject.strip() else "general information"

@retry(
    wait=wait_exponential(multiplier=1, min=config.API_RETRY_DELAY_MIN, max=config.API_RETRY_DELAY_MAX),
    stop=stop_after_attempt(config.API_RETRY_ATTEMPTS),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def generate_script(
    subject: str,
    output_dir: str,
    language: str = "English",
    # Parameters from original function signature in uploaded file
    category: str = "Uncategorized",
    content_type_area: str = "General",
    purpose: str = "General Information",
    use_web_search: bool = False,
    creativity: float = 0.7,
    tone: str = "neutral",
    target_audience: str = "general public",
    key_message: str = "No specific key message",
    emotional_arc: str = "neutral",
    # New parameters from Gradio UI (as per uploaded file)
    subject_type: str = "short story",
    story_length: str = "short",
    complexity: str = "simple",
    user_prompt: str = "", # This is often the same as 'subject' or a more detailed version
    style_primary: str = "narrative",
    style_secondary: str = "none",
    additional_instructions: str = ""
) -> tuple[str, str]:
    """
    Generates a script based on the subject and various content parameters,
    including embedded visual prompts for each scene.
    Saves the script content to a unique file in the specified output directory.
    Returns the script file path and a unique run_id.
    """
    # Ensure API key is loaded
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file or environment variables.")
    client = genai.Client(api_key=api_key)

    model_name = config.GEMINI_STORY_GEN_MODEL
    web_context = ""
    
    if use_web_search:
        try:
            optimized_query = generate_search_query(client, model_name, subject, user_prompt)
            logger.info(f"Generated search query: {optimized_query}")
            if optimized_query and len(optimized_query.strip()) > 3:
                search_results = search_web(optimized_query)
                if search_results:
                    web_context = f"\n\nWeb Context:\n{format_search_results(search_results)}"
                else:
                    logger.info(f"Web search with query '{optimized_query}' yielded no results.")
                    web_context = ""
            else:
                logger.warning(f"Optimized search query ('{optimized_query}') was empty or too short. Skipping web search.")
                web_context = ""
        except Exception as e:
            logger.warning(f"Web search attempt failed with error: {e}. Proceeding without web context.")
            web_context = ""
    
    if story_length == "short":
        length_instruction = "approximately 150-300 words (1-3 minutes)"
    elif story_length == "medium":
        length_instruction = "approximately 400-700 words (4-7 minutes)"
    elif story_length == "long":
        length_instruction = "approximately 800-1200 words (8+ minutes)"
    else:
        length_instruction = f"approximately 200-250 words (defaulting for unrecognized story_length: {story_length})"

    prompt_text = f"""
You are an expert AI scriptwriter and professional YouTube content creator, specializing in crafting engaging narratives for {category} videos.
Your goal is to generate a compelling script in {language} that is perfect for a YouTube video, based on these detailed specifications.
The script MUST include embedded visual prompts for an AI image generator for each distinct scene or segment of narration.

**User-Provided Context**
- Subject Type: {subject_type}
- Story Length: {story_length} ({length_instruction})
- Complexity: {complexity}
- User Prompt: {user_prompt if user_prompt else subject}
- Primary Style (UI): {style_primary}
- Secondary Style (UI): {style_secondary if style_secondary and style_secondary.lower() != 'none' else 'Not specified'}
- Additional Instructions: {additional_instructions if additional_instructions else 'None'}

**Core Elements**
- Subject: {subject}
- Purpose: {purpose}
- Tone: {tone.capitalize()}
- Creativity Level: {creativity}/1.0 (0.0 is factual, 1.0 is highly imaginative)
- Target Audience: {target_audience}
- Key Message: {key_message}
- Emotional Arc: {emotional_arc}

**Structural Requirements for YouTube Narrative Flow**
1. Hook & Introduction (approx. 10-15% of script):
   - Strong YouTube Hook: Grab attention in the first 5-10 seconds.
   - Introduce subject/characters/problem.
   - Set scene, hint at video's exploration.
2. Build-up & Engagement (approx. 60-70% of script):
   - Develop narrative logically for video.
   - Maintain interest with new info, plot points.
   - Use storytelling techniques (suspense, humor) appropriate to style.
   - Smooth transitions, consider visual pacing.
   - Present challenges/conflicts driving the story.
3. Climax/Peak Interest (approx. 5-10% of script):
   - Powerful emotional peak, revelation, or conflict resolution.
   - Impactful and memorable.
4. Resolution & Call to Action/Outro (approx. 10-15% of script):
   - Satisfying conclusion.
   - Clear takeaways, reinforce key message.
   - YouTube-appropriate outro (final thought, question, hint for future).

**Visual Prompt Generation for Each Scene/Segment (CRITICAL INSTRUCTIONS)**
- For **every** distinct scene, paragraph, or significant block of narration/dialogue, you **MUST** generate a highly descriptive and actionable visual prompt suitable for an advanced AI image generator (like Google Imagen or Midjourney).
- **Detail is Key**: Each prompt should be rich in detail to ensure unique and relevant image generation. Do not use generic prompts.
- **Elements to Include in Each Visual Prompt**:
    - **Setting/Environment**: Describe the location, time of day, weather, and key background elements. (e.g., "A sun-drenched medieval marketplace bustling with activity, stalls overflowing with colorful goods, a distant castle on a hill under a clear blue sky.")
    - **Characters (if any)**: Describe their appearance (clothing, notable features), their expressions, and their poses or actions within the scene. If characters reappear, maintain consistency in their description. (e.g., "A young knight with determined eyes, clad in shining silver armor with a red plume on his helmet, stands defiantly, sword raised.")
    - **Key Objects/Props**: Mention any important objects in the scene. (e.g., "A glowing crystal orb rests on an ancient stone pedestal.")
    - **Action/Activity**: What is happening in the scene? (e.g., "A spaceship narrowly avoids laser fire during a chaotic dogfight in an asteroid field.")
    - **Mood/Atmosphere**: Convey the feeling of the scene (e.g., "mysterious and suspenseful," "joyful and celebratory," "eerie and desolate").
    - **Artistic Style (Optional but Recommended)**: Suggest a style if appropriate (e.g., "photorealistic," "anime style," "impressionistic painting," "cinematic lighting," "cyberpunk aesthetic").
    - **Camera Angle/Composition (Optional but Recommended)**: Suggest a viewpoint (e.g., "wide angle shot," "extreme close-up on the character's eyes," "dynamic low-angle shot," "Dutch angle").
- **Uniqueness**: Each visual prompt should be tailored to its specific scene to avoid repetitive imagery.
- **Format for Output:** The script must strictly follow this format. Embed the visual prompt on its own line, immediately before the text it corresponds to, using the marker "VISUAL_PROMPT:".

  **Good Example of a Detailed Visual Prompt:**
  VISUAL_PROMPT: Cinematic wide shot of a desolate, windswept alien desert at sunset. Twin violet suns cast long, eerie shadows from towering, crimson rock formations. A lone, cloaked figure (gender-neutral, weathered face partially visible) struggles against the wind, their silhouette small against the vast, orange sky. Dust devils dance in the distance. Mood: isolated, determined, harsh. Style: epic sci-fi concept art.

  Narrator: The journey across Xylos was a test of endurance, each step a battle against the elements.

  **Another Good Example:**
  VISUAL_PROMPT: Extreme close-up on an old, wrinkled hand gently opening a dusty, leather-bound locket. Inside, a faded photograph of a smiling young woman. Soft, warm light illuminates the scene, possibly from a nearby window. Mood: nostalgic, tender, melancholic. Style: photorealistic, shallow depth of field.

  Old Man: (Voice trembling slightly) I never forgot her... not for a single day.

**Character Development for Spoken Delivery** (if applicable)
- Distinct voices for speakers.
- Subtle character arcs.
- Natural, culturally appropriate dialogue revealing personality and advancing plot.
- Each character's dialogue contributes meaningfully.
- Embed Natural Language Style Instructions for TTS: (e.g., "Say angrily:", "(Whispering)") within the dialogue text itself.

**YouTube Engagement & Delivery Guidelines**
- Conversational Tone: Natural and engaging when spoken.
- Pacing for Viewers: Vary sentence length.
- Maintain Interest: Use questions, suspense, personality.
- Clarity and Conciseness.
- Memorable Moments.

**Technical Specifications for Script Format**
- First line: "Style: {style_primary}, Tone: {tone.capitalize()}" (This line MUST be in English, exactly as provided here, using the English style and tone names. The rest of the script should be in {language}.)
- Speaker labels: Clear and consistent (e.g., "Narrator:", "Expert:", "Character 1:"). Each speaker's dialogue on a new line.
- Visual Prompts: Each on its own line starting with "VISUAL_PROMPT:", preceding the related dialogue/narration.
- Language: The main body of the script must be in natural and fluent {language}.

**Web Context** (if available):{web_context}

**Example Output Snippet (Illustrative of Format):**
Style: Sci-Fi Adventure, Tone: Exciting
VISUAL_PROMPT: Dynamic shot of a sleek spaceship blasting off from a desert planet, plumes of smoke and fire erupting from its engines, twin moons visible in the alien sky. Style: concept art.
Narrator: The year is 2342. Humanity's last hope leaves a dying Earth.
VISUAL_PROMPT: Interior of the spaceship bridge, holographic displays flickering, Captain Eva Rostova (woman, 30s, short brown hair, determined expression, wearing a dark blue uniform) staring intently at a star map.
Captain Rostova: (Say with determination): Set course for the Kepler nebula. There's no turning back.
"""
    try:
        response = client.models.generate_content( # Corrected for client instance
            model=model_name,
            contents=[types.Content(parts=[types.Part.from_text(text=prompt_text)])],
            config=types.GenerateContentConfig( # Corrected
                temperature=creativity, # This was correctly 'creativity' in your original code
                top_p=0.95, # Standard Top P
                max_output_tokens=config.GEMINI_STORY_GEN_MODEL_MAX_TOKENS if hasattr(config, 'GEMINI_STORY_GEN_MODEL_MAX_TOKENS') else 4096, # Increased, ensure config has this or use a sensible default like 4096
                tools=[], # Explicitly set tools to an empty list
            )
        )
        
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            logger.info(f"Gemini prompt feedback for story generation: {response.prompt_feedback}")
            if response.prompt_feedback.block_reason:
                logger.error(f"Gemini content generation for story was blocked. Reason: {response.prompt_feedback.block_reason}. This may cause formatting issues.")
        
        if not response.text:
            logger.error("Gemini response for story generation is empty or None (response.text is falsy).")
            # (rest of your detailed error logging for empty response)
            raise ValueError("Generated script is empty or None from API. Check logs for details.")

        # Validation (first line and speaker labels)
        first_line_text = response.text.strip().split('\n', 1)[0]
        expected_start_pattern = re.compile(
            rf"Style:\s*{re.escape(style_primary.strip())}\s*,\s*Tone:\s*{re.escape(tone.capitalize())}", # Use style_primary directly
            re.IGNORECASE
        )
        if not expected_start_pattern.match(first_line_text):
            logger.error(f"Generated script first line: '{first_line_text}'")
            logger.error(f"Expected pattern: Style: {style_primary.strip()}, Tone: {tone.capitalize()}")
            raise ValueError(f"Generated script does not adhere to 'Style: [Primary Style], Tone: [Tone]'. Checked: '{style_primary.strip()}', '{tone.capitalize()}'")
        
        # Check for VISUAL_PROMPT: lines and Speaker: lines
        if not (re.search(r"^VISUAL_PROMPT:", response.text, re.MULTILINE) and \
                re.search(r"^\s*\w+:", response.text, re.MULTILINE)):
            problematic_script_start = response.text[:500].replace('\n', '\\n')
            logger.error(f"Problematic script (up to 500 chars) lacking VISUAL_PROMPT or speaker labels: '{problematic_script_start}...'")
            raise ValueError("Generated script must contain 'VISUAL_PROMPT:' lines AND speaker labels (e.g., 'Narrator:').")


    except Exception as e:
        logger.error(f"API call for story generation failed: {e}")
        # (rest of your general exception logging)
        raise

    safe_subject = "".join(c for c in subject if c.isalnum() or c in " _-").replace(" ", "_")[:40].strip() or "untitled"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_id = f"{safe_subject}_{timestamp}"
    # Simplified script filename using run_id. Details like language, length, tone are in the script content.
    file_name = f"{run_id}_script.txt"
    script_file_path = os.path.join(output_dir, file_name)

    os.makedirs(os.path.dirname(script_file_path), exist_ok=True)
    with open(script_file_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    logger.info(f"Script with visual prompts saved to: {script_file_path} (Run ID: {run_id})")

    return script_file_path, run_id

if __name__ == "__main__":
    output_script_dir = os.path.join(os.getcwd(), config.OUTPUT_SCRIPT_DIR)
    os.makedirs(output_script_dir, exist_ok=True)
    logger.info("🧪 Testing story generation with embedded visual prompts...")
    
    test_params = {
        "subject": "A journey to Mars",
        "output_dir": output_script_dir,
        "language": "English",
        "category": "Sci-Fi",
        "subject_type": "short story",
        "story_length": "short",
        "complexity": "simple",
        "user_prompt": "Tell a short story about the first human journey to Mars, focusing on the astronauts' emotions.",
        "style_primary": "narrative",
        "tone": "hopeful",
        "creativity": 0.8,
        "use_web_search": False 
    }
    try:
        script_path, run_id = generate_script(**test_params)
        logger.info(f"✅ Test script generated: {script_path} with Run ID: {run_id}")
        with open(script_path, "r", encoding="utf-8") as f:
            logger.info(f"\n📝 Content sample:\n{f.read()[:500]}...")
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")