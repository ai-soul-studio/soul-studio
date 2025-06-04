from google.adk.agents import Agent
import logging
import os
from dotenv import load_dotenv

# Configure basic logging to see ADK outputs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Minimal agent.py: Starting up. Attempting to load .env and check API key.")

# Load .env file from the project root (one level up from adk_agent)
project_root_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')

if os.path.exists(project_root_env_path):
    logger.info(f"Found project root .env file at: {project_root_env_path}. Loading it.")
    load_dotenv(dotenv_path=project_root_env_path, override=True)
else:
    logger.warning(f"Project root .env file NOT found at: {project_root_env_path}. Checking adk_agent/.env")
    # Fallback to checking .env within adk_agent directory
    adk_agent_env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(adk_agent_env_path):
        logger.info(f"Found adk_agent .env file at: {adk_agent_env_path}. Loading it.")
        load_dotenv(dotenv_path=adk_agent_env_path, override=True)
    else:
        logger.warning(f"adk_agent .env file also NOT found at: {adk_agent_env_path}. Relying on system environment variables for GOOGLE_API_KEY.")

# Check for GOOGLE_API_KEY
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logger.warning("GOOGLE_API_KEY is NOT set in the environment. ADK initialization might fail or use default credentials if not configured for Vertex AI.")
else:
    logger.info(f"GOOGLE_API_KEY is set. Length: {len(api_key)}. (Key itself is not logged for security)")
    # Explicitly set GOOGLE_GENAI_USE_VERTEXAI to False if API key is primary and Vertex AI is not explicitly True
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "False").lower() != "true":
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
        logger.info("Set GOOGLE_GENAI_USE_VERTEXAI=False for API key usage.")
    else:
        logger.info("GOOGLE_GENAI_USE_VERTEXAI is True. ADK will likely attempt to use Vertex AI credentials.")

logger.info("Minimal agent.py: Defining a simple tool and agent.")

def simple_tool(text: str) -> str:
    """A very simple tool that echoes the input text."""
    logger.info(f"simple_tool called with: {text}")
    return f"Tool received: {text}"

root_agent = Agent(
    name="minimal_debug_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="A minimal agent for debugging ADK setup.",
    instruction="I am a minimal agent. I can use a simple tool.",
    tools=[simple_tool]
)

logger.info(f"Minimal agent.py: root_agent defined: {root_agent.name}. Script execution finished.")

# If running this script directly (e.g., python -m adk_agent.agent), this part won't be hit by `adk run`.
# For direct execution test:
if __name__ == "__main__":
    logger.info("Running agent.py directly (__name__ == '__main__'). This is for testing the script itself.")
    logger.info("To run the ADK server, use 'adk run adk_agent.agent:root_agent'")

