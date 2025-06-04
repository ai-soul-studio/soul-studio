from google.adk.agents import Agent

def simple_tool(text: str) -> str:
    """A very simple tool that echoes the input text."""
    return f"Tool received: {text}"

root_agent = Agent(
    name="minimal_direct_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="A minimal agent for debugging ADK setup, direct file.",
    instruction="I am a minimal agent. I can use a simple tool.",
    tools=[simple_tool]
)
