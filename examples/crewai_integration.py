"""
ArmorIQ SDK — CrewAI Integration Example

Demonstrates how to use ArmorIQCrew to run a CrewAI crew with
automatic ArmorIQ intent verification on every MCP tool call.

What this shows:
- Defining CrewAI tools that are recognised by ArmorIQ (mcp + action attrs)
- Building a crew with ArmorIQCrew instead of crewai.Crew directly
- How ArmorIQ issues an intent token before the crew runs
- How every MCP tool call is automatically routed through ArmorIQ

Requirements:
    pip install armoriq-sdk[crewai]

Environment variables:
    ARMORIQ_API_KEY  — your ArmorIQ API key  (required)
    USER_ID          — your user identifier   (required)
    AGENT_ID         — your agent identifier  (required)

Run:
    python examples/crewai_integration.py
"""

import logging
import os

from crewai import Agent, Crew, Task
from crewai.tools import BaseTool
from pydantic import Field

from armoriq_sdk import ArmorIQClient
from armoriq_sdk.integrations import ArmorIQCrew

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Define ArmorIQ-aware CrewAI tools
#
#    ArmorIQCrew recognises tools that have both a `.mcp` and an `.action`
#    attribute. Set these to the MCP name and tool name you onboarded on the
#    ArmorIQ platform. Everything else is standard CrewAI BaseTool usage.
# ---------------------------------------------------------------------------


class GetWeatherTool(BaseTool):
    """Fetch current weather conditions for a city."""

    name: str = "get_weather"
    description: str = "Get the current weather for a given city."

    # ArmorIQ attributes — must match what you onboarded on the platform
    mcp: str = Field(default="weather-mcp", exclude=True)
    action: str = Field(default="get_weather", exclude=True)

    def _run(self, city: str) -> str:
        # This method is replaced at runtime by ArmorIQCrew._patch_tools,
        # which routes the call through ArmorIQ's proxy for verification.
        # The implementation here is only reached if ArmorIQCrew is not used.
        raise RuntimeError("Tool called outside of ArmorIQCrew context")


class GetForecastTool(BaseTool):
    """Fetch a 5-day weather forecast for a city."""

    name: str = "get_forecast"
    description: str = "Get a 5-day weather forecast for a given city."

    mcp: str = Field(default="weather-mcp", exclude=True)
    action: str = Field(default="get_forecast", exclude=True)

    def _run(self, city: str, days: int = 5) -> str:
        raise RuntimeError("Tool called outside of ArmorIQCrew context")


# ---------------------------------------------------------------------------
# 2. Build the crew
# ---------------------------------------------------------------------------


def build_crew(client: ArmorIQClient) -> ArmorIQCrew:
    weather_tool = GetWeatherTool()
    forecast_tool = GetForecastTool()

    # Standard CrewAI agent — nothing ArmorIQ-specific here
    meteorologist = Agent(
        role="Meteorologist",
        goal="Provide accurate and concise weather information to users.",
        backstory=(
            "An expert meteorologist with 20 years of experience reading "
            "atmospheric data and communicating forecasts clearly."
        ),
        tools=[weather_tool, forecast_tool],
        verbose=True,
    )

    # Standard CrewAI tasks
    current_weather_task = Task(
        description="Get the current weather conditions for San Francisco and London.",
        expected_output="A brief summary of current conditions in both cities.",
        agent=meteorologist,
    )

    forecast_task = Task(
        description="Get the 5-day forecast for San Francisco and London.",
        expected_output="A concise 5-day outlook for both cities.",
        agent=meteorologist,
    )

    # ArmorIQCrew wraps crewai.Crew.
    # - armoriq_client: your initialised ArmorIQClient
    # - llm: the LLM identifier passed to capture_plan (informational)
    # - token_validity_seconds: how long the issued intent token is valid
    # All other kwargs are forwarded to crewai.Crew.
    return ArmorIQCrew(
        agents=[meteorologist],
        tasks=[current_weather_task, forecast_task],
        armoriq_client=client,
        llm="gpt-4o",
        token_validity_seconds=3600.0,
        verbose=True,
    )


# ---------------------------------------------------------------------------
# 3. Run
# ---------------------------------------------------------------------------


def main():
    print("ArmorIQ + CrewAI Integration Example")
    print("=" * 60)

    # Initialise the ArmorIQ client (reads ARMORIQ_API_KEY, USER_ID, AGENT_ID
    # from the environment, or pass them explicitly below).
    client = ArmorIQClient(
        api_key=os.getenv("ARMORIQ_API_KEY"),
        user_id=os.getenv("USER_ID", "demo_user"),
        agent_id=os.getenv("AGENT_ID", "weather_crew_agent"),
        # Use local development services (set use_production=True for prod)
        use_production=False,
    )

    print("\nStep 1 — Build ArmorIQCrew")
    print("-" * 40)
    crew = build_crew(client)
    print("Crew built. ArmorIQ tools detected: get_weather, get_forecast")

    print("\nStep 2 — kickoff() (ArmorIQ issues intent token automatically)")
    print("-" * 40)
    # Under the hood ArmorIQCrew:
    #   1. Collects all ArmorIQ tools from the agents
    #   2. Calls client.capture_plan() with the task goal + tool steps
    #   3. Calls client.get_intent_token() to receive a signed token
    #   4. Patches every tool._run to route through client.invoke()
    #   5. Calls crew.kickoff() — all MCP calls are verified by ArmorIQ
    #   6. Restores original _run methods (even on exception)
    result = crew.kickoff()

    print("\nStep 3 — Result")
    print("-" * 40)
    print(result)

    print("\nDone. All MCP calls were verified by ArmorIQ.")
    client.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
