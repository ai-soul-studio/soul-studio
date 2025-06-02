import os
import sys
import re
from google import genai
from google.genai import types # Import types
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from datetime import datetime

# Add the project root to the sys.path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.web_search import search_web, format_search_results

# Load environment variables
load_dotenv()

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception), # Catch all exceptions for retry
    reraise=True
)
def generate_script(
    subject: str,
    output_dir: str,
    language: str = "Arabic",
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
    emotional_arc: str = "neutral" # rising, falling, neutral, mixed
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
    model_name = "gemini-2.5-flash-preview-05-20"

    web_context = ""
    
    if use_web_search:
        try:
            # Perform web search
            search_results = search_web(subject)
            web_context = f"\n\nWeb Context:\n{format_search_results(search_results)}"
        except Exception as e:
            print(f"Warning: Web search failed with error: {e}. Proceeding without web context.")
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
        # Stream response for better performance
        response = client.models.generate_content(
            model=model_name,
            contents=[types.Content(parts=[types.Part.from_text(text=prompt_text)])],
            generation_config=generation_config,
            stream=True,
        )

        # Stream and accumulate response
        script_content = ""
        for chunk in response:
            if chunk.text:
                script_content += chunk.text

        # Robust validation of output format
        if not script_content.strip().startswith(f"Style: {formatted_video_styles.split(',')[0].strip()}, Tone: {tone.capitalize()}"):
            raise ValueError("Generated script does not adhere to the required starting format 'Style: [Primary Style], Tone: [Tone]'")
        
        if not re.search(r"^\w+:", script_content, re.MULTILINE):
            raise ValueError("Generated script does not contain clear speaker labels (e.g., 'Narrator:', 'Character 1:')")

    except Exception as e:
        print(f"API call failed: {e}")
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
    
    script_file_path = os.path.join(output_dir, "scripts", file_name)

    os.makedirs(os.path.dirname(script_file_path), exist_ok=True)
    with open(script_file_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return script_file_path

if __name__ == "__main__":
    # Ensure the 'outputs/scripts' directory exists for testing
    output_script_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(os.path.join(output_script_dir, "scripts"), exist_ok=True)
    
    print("🧪 Testing enhanced story generation...")
    
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
            "emotional_arc": "informative and slightly cautionary"
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
            "emotional_arc": "rising wonder and excitement"
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
            "emotional_arc": "mixed, with moments of joy, sadness, and wisdom"
        }
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"\n🔬 Test #{i}: {test['subject']}")
        try:
            start_time = datetime.now()
            script_path = generate_script(**test, output_dir=output_script_dir)
            gen_time = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Generated in {gen_time:.1f}s: {os.path.basename(script_path)}")
            with open(script_path, "r", encoding="utf-8") as f:
                print(f"\n📝 Content sample:\n{f.read()[:200]}...")
                
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            # The retry mechanism is now handled by tenacity within generate_script
            # No need for manual retry logic here
