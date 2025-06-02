[package]
# Enforce correct SDK usage
ban = google-generative-ai
require = google-genai

[imports]
# Ensure only current SDK imports are used
ban = from google.generativeai import *
require = from google import genai

[models]
# Force use of latest model names
require = gemini-2.5-flash-preview-05-20
require = gemini-2.5-flash-preview-tts
require = models/imagen-3.0-generate-002

[api_keys]
# Ban hardcoding API keys
ban = api_key='hardcoded_value'
require_pattern = ^os\.environ\["GEMINI_API_KEY"\]$

[style]
# Prefer named model selection
prefer_named_model = True

[errors]
# Define custom error messages
google-generative-ai = Deprecated package. Use `google-genai` instead.
hardcoded_api_key = API key must be stored in environment variable.
wildcard_import = Avoid wildcard imports. Use explicit import paths.

[migration]
# Remapping deprecated to new usage
replace = from google.generativeai import -> from google import genai
replace = genai.GenerativeModel -> genai.Client

[testing]
# Enforce test presence
require_test_for = generate_content

[code_example]
# Example code for image generation with Google's Imagen model
# To run this code you need to install the following dependencies:
# pip install google-genai pillow

def generate():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    result = client.models.generate_images(
        model="models/imagen-3.0-generate-002",
        prompt="""INSERT_INPUT_HERE""",
        config=dict(
            number_of_images=1,
            output_mime_type="image/jpeg",
            person_generation="ALLOW_ADULT",
            aspect_ratio="1:1",
        ),
    )

    if not result.generated_images:
        print("No images generated.")
        return

    if len(result.generated_images) != 1:
        print("Number of images generated does not match the requested number.")

    for generated_image in result.generated_images:
        image = Image.open(BytesIO(generated_image.image.image_bytes))
        image.show()


if __name__ == "__main__":
    generate()
