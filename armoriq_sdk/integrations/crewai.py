"""
ArmorIQ SDK — CrewAI Integration

Wraps CrewAI's Crew class to automatically issue ArmorIQ intent tokens
and route MCP tool calls through ArmorIQ's verification layer.

Usage:
    from armoriq_sdk.integrations import ArmorIQCrew

    crew = ArmorIQCrew(
        agents=[...],
        tasks=[...],
        armoriq_client=client,
        llm="gpt-4o",
    )
    result = crew.kickoff()

Requires: pip install armoriq-sdk[crewai]
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ..exceptions import ArmorIQException

logger = logging.getLogger(__name__)


def _collect_armoriq_tools(agents) -> list:
    """Collect all ArmorIQ tools (tools with .mcp and .action) from agents.

    Deduplicates by object identity — the same tool object on multiple agents
    is only returned once.
    """
    seen_ids = set()
    tools = []
    for agent in agents:
        for tool in getattr(agent, "tools", []) or []:
            if hasattr(tool, "mcp") and hasattr(tool, "action"):
                tid = id(tool)
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    tools.append(tool)
    return tools


def _build_plan(tools, tasks) -> dict:
    """Build an ArmorIQ plan dict from the crew's tools and tasks.

    Returns:
        {"goal": str, "steps": [{"action": str, "mcp": str}, ...]}

    Steps are deduplicated by (mcp, action) pair.
    """
    # Derive goal from task descriptions
    goal_parts = []
    for task in tasks:
        desc = getattr(task, "description", None) or getattr(task, "expected_output", None)
        if desc:
            goal_parts.append(desc)
    goal = " ".join(goal_parts) if goal_parts else "Execute crew tasks"

    # Build steps — one per unique (mcp, action) combo
    seen_combos = set()
    steps = []
    for tool in tools:
        combo = (tool.mcp, tool.action)
        if combo not in seen_combos:
            seen_combos.add(combo)
            steps.append({"action": tool.action, "mcp": tool.mcp})

    return {"goal": goal, "steps": steps}


def _wrap_tool(tool, client, token):
    """Patch tool._run to route through ArmorIQ invoke().

    Uses object.__setattr__ to bypass Pydantic v2's frozen __setattr__.

    Returns:
        The original _run callable (for later restoration).
    """
    original_run = tool._run  # capture before patching

    def _armoriq_run(*args, **kwargs):
        params = kwargs if kwargs else (args[0] if args else {})
        result = client.invoke(
            mcp=tool.mcp,
            action=tool.action,
            intent_token=token,
            params=params,
        )
        value = result.result
        return value if isinstance(value, str) else json.dumps(value)

    object.__setattr__(tool, "_run", _armoriq_run)
    return original_run


class ArmorIQCrew:
    """CrewAI Crew wrapper that integrates ArmorIQ intent verification.

    All positional/keyword arguments (except armoriq_client, llm, and
    token_validity_seconds) are forwarded to CrewAI's Crew constructor.

    Args:
        armoriq_client: Initialized ArmorIQClient instance.
        llm: LLM identifier string passed to capture_plan (e.g. "gpt-4o").
        token_validity_seconds: How long the issued intent token is valid.
        *args / **kwargs: Forwarded to crewai.Crew.

    Raises:
        ImportError: If crewai is not installed (with pip install instructions).
    """

    def __init__(self, *args, armoriq_client, llm, token_validity_seconds=3600.0, **kwargs):
        try:
            from crewai import Crew  # noqa: F401
        except ImportError:
            raise ImportError(
                "crewai is not installed.\n"
                "Install it with: pip install armoriq-sdk[crewai]"
            )
        self._armoriq_client = armoriq_client
        self._llm = llm
        self._token_validity_seconds = token_validity_seconds
        self._agents = list(kwargs.get("agents", []) or [])
        self._tasks = list(kwargs.get("tasks", []) or [])
        self._crew = Crew(*args, **kwargs)

    def _issue_token(self):
        """Issue an ArmorIQ intent token for the crew's tools and tasks.

        Returns None (with a warning) when no ArmorIQ tools are found.
        """
        tools = _collect_armoriq_tools(self._agents)
        if not tools:
            logger.warning("No ArmorIQ tools found; crew runs without ArmorIQ verification")
            return None

        plan_dict = _build_plan(tools, self._tasks)
        plan = self._armoriq_client.capture_plan(
            llm=self._llm,
            prompt=plan_dict["goal"],
            plan=plan_dict,
        )
        return self._armoriq_client.get_intent_token(
            plan,
            validity_seconds=self._token_validity_seconds,
        )

    def _patch_tools(self, token) -> dict:
        """Patch all ArmorIQ tools to route through ArmorIQ invoke().

        Returns:
            Mapping of id(tool) → original _run for later restoration.
        """
        originals: Dict[int, Any] = {}
        for agent in self._agents:
            for tool in getattr(agent, "tools", []) or []:
                if hasattr(tool, "mcp") and hasattr(tool, "action"):
                    tid = id(tool)
                    if tid not in originals:
                        originals[tid] = _wrap_tool(tool, self._armoriq_client, token)
        return originals

    def _restore_tools(self, originals: dict):
        """Restore original _run methods after crew execution."""
        for agent in self._agents:
            for tool in getattr(agent, "tools", []) or []:
                tid = id(tool)
                if tid in originals:
                    object.__setattr__(tool, "_run", originals[tid])

    def kickoff(self, inputs=None):
        """Run the crew synchronously with ArmorIQ verification.

        Args:
            inputs: Optional inputs forwarded to crewai.Crew.kickoff().

        Returns:
            The result returned by crewai.Crew.kickoff().
        """
        token = self._issue_token()
        originals = self._patch_tools(token) if token is not None else {}
        try:
            return self._crew.kickoff(inputs=inputs)
        finally:
            if originals:
                self._restore_tools(originals)

    async def kickoff_async(self, inputs=None):
        """Run the crew asynchronously with ArmorIQ verification.

        Token issuance is synchronous (httpx is blocking); only the inner
        crewai.Crew.kickoff_async() call is awaited.

        Args:
            inputs: Optional inputs forwarded to crewai.Crew.kickoff_async().

        Returns:
            The result returned by crewai.Crew.kickoff_async().
        """
        token = self._issue_token()  # synchronous — httpx is blocking
        originals = self._patch_tools(token) if token is not None else {}
        try:
            return await self._crew.kickoff_async(inputs=inputs)
        finally:
            if originals:
                self._restore_tools(originals)
