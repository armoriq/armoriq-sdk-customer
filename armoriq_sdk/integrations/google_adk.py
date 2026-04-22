"""
ArmorIQ — Google ADK integration (Python).

Multi-user pattern:

    from armoriq_sdk.integrations.google_adk import ArmorIQADK

    armoriq = ArmorIQADK(api_key=os.environ["ARMORIQ_API_KEY"])

    # per-request, inside your chat handler:
    scope = armoriq.for_user(user_email, goal=message)
    scope.install(root_agent)
    try:
        async for event in runner.run_async(...):
            ...
    finally:
        scope.uninstall(root_agent)

The bundle installs three ADK lifecycle callbacks on the agent:

    after_model_callback  → mint intent token from LLM tool calls
    before_tool_callback  → enforce per-user policy, block/hold if needed
    after_tool_callback   → audit report

One `ArmorIQADK` instance per process; bootstrap (org, MCPs, toolMap) is
cached. `for_user(email)` resolves + caches user context for 5 min.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from ..client import ArmorIQClient, ArmorIQUserScope
from ..models import ToolCall
from ..session import ArmorIQSession, ReportOptions, SessionMode, SessionOptions

logger = logging.getLogger("armoriq.integrations.google_adk")

ToolNameParser = Any  # Callable[[str], Tuple[str, str]]


class ArmorIQADK:
    """Process-wide ArmorIQ factory for Google ADK agents."""

    def __init__(
        self,
        *,
        api_key: str,
        backend_endpoint: Optional[str] = None,
        iap_endpoint: Optional[str] = None,
        proxy_endpoint: Optional[str] = None,
        use_production: bool = True,
        default_mcp_name: Optional[str] = None,
        tool_name_parser: Optional[ToolNameParser] = None,
        validity_seconds: int = 300,
        mode: SessionMode = "sdk",
        llm: str = "agent",
    ) -> None:
        self.client = ArmorIQClient(
            api_key=api_key,
            backend_endpoint=backend_endpoint,
            iap_endpoint=iap_endpoint or backend_endpoint,
            proxy_endpoint=proxy_endpoint or backend_endpoint,
            use_production=use_production,
            _skip_api_key_validation=True,
        )
        self.default_mcp_name = default_mcp_name
        self._custom_parser = tool_name_parser
        self.validity_seconds = validity_seconds
        self.mode: SessionMode = mode
        self.llm = llm
        self._bootstrap: Optional[Dict[str, Any]] = None

    def bootstrap(self) -> Dict[str, Any]:
        if self._bootstrap is None:
            self._bootstrap = self.client.bootstrap()
            logger.info(
                "[armoriq] bootstrap: org=%s mcps=%s toolMap=%d",
                self._bootstrap["org"]["name"],
                [m["name"] for m in self._bootstrap["mcps"]],
                len(self._bootstrap.get("toolMap", {})),
            )
        return self._bootstrap

    def _tool_name_parser(self):
        if self._custom_parser is not None:
            return self._custom_parser
        bootstrap = self.bootstrap()
        tool_map: Dict[str, str] = bootstrap.get("toolMap", {})
        default_mcp = self.default_mcp_name

        def _parse(tool_name: str) -> Tuple[str, str]:
            mcp = tool_map.get(tool_name)
            if mcp:
                return (mcp, tool_name)
            if "__" in tool_name:
                prefix, action = tool_name.split("__", 1)
                return (prefix, action)
            if default_mcp:
                return (default_mcp, tool_name)
            return ("unknown", tool_name)

        return _parse

    def invalidate_user(self, user_email: str) -> None:
        self.client.invalidate_user(user_email)

    def for_user(self, user_email: str, *, goal: Optional[str] = None) -> "_ArmorIQADKBundle":
        """Build a per-request ADK callback bundle scoped to one user."""
        self.bootstrap()
        scope: ArmorIQUserScope = self.client.for_user(user_email)
        return _ArmorIQADKBundle(
            factory=self,
            scope=scope,
            user_email=user_email.strip().lower(),
            goal=goal,
        )


class _ArmorIQADKBundle:
    """Per-request ADK bundle — installs/uninstalls lifecycle callbacks."""

    def __init__(
        self,
        *,
        factory: ArmorIQADK,
        scope: ArmorIQUserScope,
        user_email: str,
        goal: Optional[str],
    ) -> None:
        self.factory = factory
        self.scope = scope
        self.user_email = user_email
        self.goal = goal or "agent task"
        self.session: Optional[ArmorIQSession] = None
        self._plan_minted = False
        self._blocked_tools: set = set()
        self._blocked_actions: dict = {}
        self._agent = None
        self._saved: Dict[str, Any] = {}

    def _ensure_session(self) -> ArmorIQSession:
        if self.session is None:
            self.session = self.scope.start_session(
                SessionOptions(
                    mode=self.factory.mode,
                    validity_seconds=self.factory.validity_seconds,
                    llm=self.factory.llm,
                    tool_name_parser=self.factory._tool_name_parser(),
                    default_mcp_name=self.factory.default_mcp_name,
                )
            )
        return self.session

    async def _after_model(self, callback_context, llm_response):
        try:
            if self._plan_minted:
                return None
            parts = getattr(llm_response.content, "parts", []) or []
            tool_calls = []
            for p in parts:
                fc = getattr(p, "function_call", None)
                if fc and fc.name:
                    tool_calls.append(
                        ToolCall(name=fc.name, args=dict(fc.args) if fc.args else {})
                    )
            if not tool_calls:
                return None
            self._ensure_session().start_plan(tool_calls, goal=self.goal)
            self._plan_minted = True
            logger.info(
                "[armoriq] plan minted user=%s tools=%d", self.user_email, len(tool_calls)
            )
        except Exception as exc:
            logger.warning("[armoriq] after_model_callback failed: %s", exc)
        return None

    async def _before_tool(self, tool, args, tool_context):
        tool_name = getattr(tool, "name", str(tool))
        try:
            decision = self._ensure_session().check(
                tool_name, args or {}, user_email=self.user_email
            )
            if not decision.allowed:
                policy = (
                    f" (policy: {decision.matched_policy})"
                    if decision.matched_policy
                    else ""
                )

                if decision.action == "hold":
                    logger.info(
                        "[armoriq] HELD %s user=%s reason=%s — waiting for approval...",
                        tool_name, self.user_email, decision.reason,
                    )
                    # Poll for approval (check every 3s, up to 60s)
                    approved = False
                    for attempt in range(20):
                        await asyncio.sleep(3)
                        retry = self._ensure_session().check(
                            tool_name, args or {}, user_email=self.user_email
                        )
                        if retry.allowed:
                            logger.info("[armoriq] APPROVED %s after %ds", tool_name, (attempt + 1) * 3)
                            approved = True
                            break
                        if retry.action != "hold":
                            break
                        logger.debug("[armoriq] still waiting for approval... (%d/%d)", attempt + 1, 20)

                    if approved:
                        return None  # let ADK call the tool

                    self._blocked_tools.add(tool_name)
                    self._blocked_actions[tool_name] = "hold"
                    return {
                        "error": f"Approval timed out{policy}. Reason: {decision.reason or 'policy-hold'}.",
                        "armoriq_enforcement": {
                            "blocked": True,
                            "action": "hold",
                            "reason": decision.reason,
                            "matched_policy": decision.matched_policy,
                            "tool": tool_name,
                            "delegation_id": decision.delegation_id,
                        },
                    }

                # Hard block
                self._blocked_tools.add(tool_name)
                self._blocked_actions[tool_name] = decision.action
                logger.info(
                    "[armoriq] BLOCKED %s user=%s action=%s reason=%s",
                    tool_name, self.user_email, decision.action, decision.reason,
                )
                return {
                    "error": f"This action is not permitted by your organization's policy{policy}. Reason: {decision.reason or 'policy-blocked'}.",
                    "armoriq_enforcement": {
                        "blocked": True,
                        "action": decision.action,
                        "reason": decision.reason,
                        "matched_policy": decision.matched_policy,
                        "tool": tool_name,
                        "delegation_id": decision.delegation_id,
                    },
                }
        except Exception as exc:
            logger.warning("[armoriq] before_tool_callback failed: %s", exc)
        return None

    async def _after_tool(self, tool, args, tool_context, tool_response):
        tool_name = getattr(tool, "name", str(tool))
        try:
            if tool_name in self._blocked_tools:
                action = self._blocked_actions.pop(tool_name, "block")
                self._blocked_tools.discard(tool_name)
                if action != "hold":
                    self._ensure_session().report(
                        tool_name, args or {}, tool_response,
                        ReportOptions(status="failed", error_message="Blocked by policy"),
                    )
                return None
            self._ensure_session().report(tool_name, args or {}, tool_response)
        except Exception as exc:
            logger.warning("[armoriq] after_tool_callback failed: %s", exc)
        return None

    def install(self, agent: Any) -> "_ArmorIQADKBundle":
        """Attach the three callbacks to the ADK agent."""
        self._agent = agent
        self._saved = {
            "after_model_callback": getattr(agent, "after_model_callback", None),
            "before_tool_callback": getattr(agent, "before_tool_callback", None),
            "after_tool_callback": getattr(agent, "after_tool_callback", None),
        }
        agent.after_model_callback = self._after_model
        agent.before_tool_callback = self._before_tool
        agent.after_tool_callback = self._after_tool
        return self

    def uninstall(self, agent: Optional[Any] = None) -> None:
        a = agent or self._agent
        if a is None:
            return
        a.after_model_callback = self._saved.get("after_model_callback")
        a.before_tool_callback = self._saved.get("before_tool_callback")
        a.after_tool_callback = self._saved.get("after_tool_callback")
