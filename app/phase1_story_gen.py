import os
from google import genai

def generate_story_script(subject: str, output_dir: str) -> str:
    """
    Generates a story script based on the subject, including tone/style and speaker labels.
    Saves the script content to a unique file in the specified output directory.

    Args:
        subject (str): The subject of the story.
        output_dir (str): The directory to save the generated script file.

    Returns:
        str: The path to the saved script file.
    """
    # Initialize the Gemini client
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Use the specified model for text generation
    model_name = "gemini-2.5-flash-preview-05-20"

    # Develop a robust prompt for the model
    prompt_text = f"""
You are an expert storyteller. Your task is to generate a complete, short story script based on the provided subject.

Follow these instructions precisely:
1.  **Subject**: "{subject}"
2.  **Structure**: The story must have a complete narrative arc, including a clear beginning, a moment of conflict or discovery, and a satisfying resolution.
3.  **Length**: The final script should be approximately 200-250 words.
4.  **Output Format**:
    - The very first line must be the style or tone of the story (e.g., "Style: Mysterious Thriller").
    - Use the character names you invented as speaker labels (e.g., "Speaker 1:, Speaker 2:").
    - Do NOT include the character descriptions in the final output.
    - Do NOT include any SRT formatting, timestamps, or any text other than the style line and the dialogue.

Example of the required final output format:
Style: Hopeful Drama

Speaker 1: لا أعرف إذا كنت أستطيع فعل هذا. العاصفة جرفت كل شيء بعيدًا.
Speaker 2: ليس كل شيء، ماركوس. ما زلنا هنا. يمكننا إعادة البناء.
Speaker 1: بماذا؟ لم يبقَ لدينا شيء.
Speaker 2: لدينا بعضنا البعض. ولدينا شروق الشمس. إنها بداية.
"""
    contents = [
        genai.types.Content(
            role="user",
            parts=[
                genai.types.Part.from_text(text=prompt_text),
            ],
        ),
    ]
    generate_content_config = genai.types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    # Send the request to the Gemini API
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )

    # Receive the script formatted string response
    script_content = response.text

    # Save the script string to a unique file
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"story_script_{timestamp}.txt" # Changed extension to .txt
    script_file_path = os.path.join(output_dir, "scripts", file_name) # Changed sub-directory to "scripts"

    os.makedirs(os.path.dirname(script_file_path), exist_ok=True)
    with open(script_file_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return script_file_path

if __name__ == "__main__":
    # Example usage (for testing purposes)
    # Ensure GEMINI_API_KEY is set in your environment before running
    # For example: set GEMINI_API_KEY=YOUR_API_KEY_HERE
    # Then run: python app/phase1_story_gen.py
    
    # Create outputs/scripts directory if it doesn't exist
    output_script_dir = os.path.join(os.getcwd(), "outputs", "scripts") # Changed to "scripts"
    os.makedirs(output_script_dir, exist_ok=True)

    test_subject = "A brave knight on a quest to find a magical artifact"
    try:
        generated_script_path = generate_story_script(test_subject, os.path.join(os.getcwd(), "outputs")) # Changed function call
        print(f"Generated script saved to: {generated_script_path}")
        with open(generated_script_path, "r", encoding="utf-8") as f:
            print("\n--- Generated Script Content ---") # Changed title
            print(f.read())
            print("-----------------------------")
    except KeyError:
        print("Error: GEMINI_API_KEY environment variable not set. Please set it before running.")
    except Exception as e:
        print(f"An error occurred: {e}")



