"""
Plan-shape helpers used by ArmorIQSession and framework integrations.

Most LLM frameworks surface tool calls as a flat list of ``{name, args}``.
The SDK accepts that shape directly so plugin code doesn't have to
hand-construct ``{goal, steps: [...]}`` every time.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from .models import ToolCall


ToolNameParser = Callable[[str], Tuple[str, str]]
"""A callable that parses ``tool_name`` into ``(mcp, action)``."""


def default_tool_name_parser(
    default_mcp_name: Optional[str] = None,
) -> ToolNameParser:
    """
    Default tool-name convention: ``<MCP>__<action>``. Matches the proxy's
    MCP gateway and the convention used by sdk-admin-agent.

        "Stripe__create_payment" -> ("Stripe", "create_payment")
        "create_payment"          -> uses default_mcp_name, else raises.
    """

    def _parser(tool_name: str) -> Tuple[str, str]:
        idx = tool_name.find("__")
        if idx == -1:
            if not default_mcp_name:
                raise ValueError(
                    f'Tool "{tool_name}" is not namespaced as <MCP>__<action> '
                    "and no default_mcp_name was set on the session."
                )
            return default_mcp_name, tool_name
        mcp = tool_name[:idx]
        action = tool_name[idx + 2 :]
        if not mcp or not action:
            raise ValueError(f'Tool "{tool_name}" has a malformed MCP prefix.')
        return mcp, action

    return _parser


def _as_tool_call(tc: Union[ToolCall, Dict[str, Any]]) -> ToolCall:
    if isinstance(tc, ToolCall):
        return tc
    return ToolCall(name=tc["name"], args=tc.get("args") or {})


def build_plan_from_tool_calls(
    tool_calls: Sequence[Union[ToolCall, Dict[str, Any]]],
    goal: Optional[str] = None,
    tool_name_parser: Optional[ToolNameParser] = None,
    default_mcp_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an SDK-shaped plan dict from a flat list of tool calls."""
    parser = tool_name_parser or default_tool_name_parser(default_mcp_name)
    steps: List[Dict[str, Any]] = []
    for tc in tool_calls:
        call = _as_tool_call(tc)
        mcp, action = parser(call.name)
        steps.append(
            {
                "action": action,
                "tool": action,
                "mcp": mcp,
                "params": call.args or {},
                "description": f"Call {action} on {mcp}",
            }
        )
    return {"goal": goal or "agent task", "steps": steps}


def hash_tool_calls(
    tool_calls: Sequence[Union[ToolCall, Dict[str, Any]]],
) -> str:
    """
    Stable hash over a tool-calls list — used by ``ArmorIQSession`` to skip
    re-minting when the LLM re-emits the same plan in the same turn.

    Uses the same JSON canonicalization as ``JSON.stringify`` in TS
    (no key sorting), so TS and Python produce matching digests.
    """
    canonical_list = [
        {"name": _as_tool_call(tc).name, "args": _as_tool_call(tc).args or {}}
        for tc in tool_calls
    ]
    canonical = json.dumps(canonical_list, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
