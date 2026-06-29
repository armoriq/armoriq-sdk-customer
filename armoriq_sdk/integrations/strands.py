"""
ArmorIQ SDK — AWS Strands Agents integration.

Mirrors the Google ADK bundle (google_adk.py): one factory per process, one
hook provider per (user, agent). It wires two Strands lifecycle hooks:

    AgentInitializedEvent  -> capture the agent's tool set as the intent plan
                              and mint the ArmorIQ intent token
    BeforeToolCallEvent    -> enforce per-user policy before each tool runs;
                              block/hold by setting event.cancel_tool

Enforcement is fail-closed: allow only on an explicit ArmorIQ allow; a block,
a hold that is not approved in time, or any enforcement error cancels the tool.
The hold path is handled inside session.check() (sdk mode -> _handle_hold ->
delegation request + approval poll), so HOLD becomes a real approval gate.

Usage:
    from armoriq_sdk import ArmorIQClient
    from armoriq_sdk.integrations.strands import ArmorIQStrands
    from strands import Agent

    armoriq = ArmorIQStrands(armoriq_client=ArmorIQClient(...), mode="sdk")
    hooks = armoriq.for_user("alice@acme.com", goal="reconcile invoices")
    agent = Agent(model=..., tools=[...], hooks=[hooks])
    agent("Pay invoice 1234")   # each tool call is enforced by ArmorIQ
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..client import ArmorIQClient, ArmorIQUserScope
from ..session import ArmorIQSession, SessionOptions

ToolNameParser = Any  # Callable[[str], Tuple[str, str]]

logger = logging.getLogger("armoriq.strands")


class ArmorIQStrands:
    """Process-wide factory. Holds the client + bootstrap; mints per-user hooks."""

    def __init__(
        self,
        *,
        armoriq_client: ArmorIQClient,
        mode: str = "sdk",
        validity_seconds: int = 3600,
        default_mcp_name: Optional[str] = None,
        tool_name_parser: Optional[ToolNameParser] = None,
    ) -> None:
        self.client = armoriq_client
        self.mode = mode
        self.validity_seconds = validity_seconds
        self.default_mcp_name = default_mcp_name
        self._custom_parser = tool_name_parser
        self._bootstrap: Optional[Dict[str, Any]] = None

    def bootstrap(self) -> Dict[str, Any]:
        if self._bootstrap is None:
            self._bootstrap = self.client.bootstrap()
        return self._bootstrap

    def _tool_name_parser(self) -> ToolNameParser:
        if self._custom_parser:
            return self._custom_parser
        tool_map: Dict[str, str] = self.bootstrap().get("toolMap", {})
        default_mcp = self.default_mcp_name or "unknown"

        def _parse(tool_name: str) -> Tuple[str, str]:
            mcp = tool_map.get(tool_name)
            if mcp:
                return (mcp, tool_name)
            if "__" in tool_name:
                prefix, action = tool_name.split("__", 1)
                return (prefix, action)
            return (default_mcp, tool_name)

        return _parse

    def invalidate_user(self, user_email: str) -> None:
        self.client.invalidate_user(user_email)

    def for_user(
        self, user_email: str, *, goal: Optional[str] = None
    ) -> "_ArmorIQStrandsHooks":
        scope = self.client.for_user(user_email)
        return _ArmorIQStrandsHooks(
            factory=self,
            scope=scope,
            user_email=user_email.strip().lower(),
            goal=goal,
        )


class _ArmorIQStrandsHooks:
    """HookProvider for one (user, agent). Pass to Agent(hooks=[...])."""

    def __init__(
        self,
        *,
        factory: ArmorIQStrands,
        scope: ArmorIQUserScope,
        user_email: str,
        goal: Optional[str],
    ) -> None:
        self.factory = factory
        self.scope = scope
        self.user_email = user_email
        self.goal = goal
        self.session: Optional[ArmorIQSession] = None
        self._plan_started = False

    # --- Strands HookProvider protocol ---
    def register_hooks(self, registry: Any, **_: Any) -> None:
        from strands.hooks.events import (
            AgentInitializedEvent,
            BeforeToolCallEvent,
        )

        registry.add_callback(AgentInitializedEvent, self._on_agent_initialized)
        registry.add_callback(BeforeToolCallEvent, self._before_tool_call)

    def _ensure_session(self) -> ArmorIQSession:
        if self.session is None:
            self.session = self.scope.start_session(
                SessionOptions(
                    mode=self.factory.mode,
                    validity_seconds=self.factory.validity_seconds,
                    tool_name_parser=self.factory._tool_name_parser(),
                    default_mcp_name=self.factory.default_mcp_name,
                )
            )
        return self.session

    def _start_plan(self, agent: Any) -> None:
        if self._plan_started:
            return
        tool_names: List[str] = list(getattr(agent, "tool_names", []) or [])
        if not tool_names:
            return
        tool_calls = [{"name": name, "args": {}} for name in tool_names]
        self._ensure_session().start_plan(tool_calls, goal=self.goal)
        self._plan_started = True
        logger.info(
            "[armoriq] strands plan minted user=%s tools=%d",
            self.user_email,
            len(tool_calls),
        )

    def _on_agent_initialized(self, event: Any) -> None:
        try:
            self._start_plan(event.agent)
        except Exception as exc:  # plan capture is best-effort at init
            logger.warning("[armoriq] strands plan capture failed: %s", exc)

    def _before_tool_call(self, event: Any) -> None:
        tool_use = getattr(event, "tool_use", None) or {}
        tool_name = tool_use.get("name") or ""
        args = tool_use.get("input") or {}
        try:
            if not self._plan_started:
                self._start_plan(event.agent)
            decision = self._ensure_session().check(
                tool_name, args, user_email=self.user_email
            )
            if not decision.allowed:
                reason = decision.reason or "blocked by policy"
                event.cancel_tool = f"ArmorIQ {decision.action}: {reason}"
                logger.info(
                    "[armoriq] strands blocked tool=%s action=%s reason=%s",
                    tool_name,
                    decision.action,
                    reason,
                )
        except Exception as exc:
            # Fail closed: never let a tool run if enforcement errored.
            logger.error("[armoriq] strands enforcement error (fail-closed): %s", exc)
            event.cancel_tool = f"ArmorIQ enforcement error (fail-closed): {exc}"
