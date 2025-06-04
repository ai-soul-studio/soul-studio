import os

# --- Output Directories ---
BASE_OUTPUT_DIR = "outputs"
OUTPUT_SCRIPT_DIR = os.path.join(BASE_OUTPUT_DIR, "scripts")
OUTPUT_AUDIO_DIR = os.path.join(BASE_OUTPUT_DIR, "audio")
OUTPUT_SRT_DIR = os.path.join(BASE_OUTPUT_DIR, "srt")
OUTPUT_IMAGE_DIR = os.path.join(BASE_OUTPUT_DIR, "images")
OUTPUT_VIDEO_DIR = os.path.join(BASE_OUTPUT_DIR, "videos")

# --- Gemini API Configuration ---
# Model names (using latest model names as per custom instructions)
GEMINI_STORY_GEN_MODEL = "gemini-2.5-flash-preview-05-20"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts" # Corrected model name
GEMINI_IMAGE_MODEL = "models/imagen-3.0-generate-002"
GEMINI_STORY_GEN_MODEL_MAX_TOKENS = 4096 # Added for phase1_story_gen.py

# --- API Configuration ---
API_RETRY_ATTEMPTS = 5
API_RETRY_DELAY_MIN = 4 # Increased min delay
API_RETRY_DELAY_MAX = 10 # Increased max delay
TTS_RATE_LIMIT_DELAY = 6  # seconds between TTS requests

# Default voices for TTS
DEFAULT_VOICE_NARRATOR = "Umbriel"
DEFAULT_VOICE_SPEAKER1 = "Zephyr"
DEFAULT_VOICE_SPEAKER2 = "Puck"

# Available voices for TTS (from Gemini API documentation)
AVAILABLE_VOICES = [
    "Zephyr", "Puck", "Umbriel", "Erinome", "Fable", "Adonis", "Aphrodite", "Apollo", "Artemis", 
    "Athena", "Atlas", "Aura", "Boreas", "Castor", "Circe", "Daphne", "Echo", "Eros", "Freya", 
    "Hades", "Hera", "Hermes", "Hestia", "Iris", "Janus", "Juno", "Loki", "Luna", "Mars", 
    "Mercury", "Minerva", "Morpheus", "Nemesis", "Nereus", "Odin", "Orion", "Pan", "Persephone", 
    "Phoebe", "Pluto", "Poseidon", "Rhea", "Selene", "Sol", "Terra", "Thalia", "Titan", 
    "Venus", "Vesta", "Vulcan", "Zeus"
]

# --- Web Search Configuration ---
BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"

# --- Script Generation Parameters (Defaults) ---
DEFAULT_LANGUAGE = "English"
DEFAULT_STORY_LENGTH = "short"
DEFAULT_COMPLEXITY = "simple"
DEFAULT_PRIMARY_STYLE = "narrative"
DEFAULT_SECONDARY_STYLE = "none"
DEFAULT_CREATIVITY = 0.7
DEFAULT_TONE = "neutral"
DEFAULT_TARGET_AUDIENCE = "general public"
DEFAULT_KEY_MESSAGE = "No specific key message"
DEFAULT_EMOTIONAL_ARC = "neutral"

# --- Image Generation Parameters (Defaults) ---
DEFAULT_ART_STYLE = "cinematic"
AVAILABLE_ART_STYLES = [
    "cinematic", "photorealistic", "anime", "manga", "watercolor", "oil painting", 
    "charcoal sketch", "pixel art", "vector art", "3d render", "fantasy art", 
    "sci-fi concept art", "steampunk", "cyberpunk", "impressionistic", "surreal", "none"
]