"""
ArmorIQSession — the core primitive for framework integrations.

Two modes:

1. Observe mode (default, local) — MCP stays on the agent side:
     session.start_plan(tool_calls)                      # capture plan + mint token
     decision = session.enforce(tool_name, tool_args)    # check policy
     # ... framework calls MCP directly ...
     session.report(tool_name, tool_args, result)        # audit

2. Proxy mode — routes through the Armoriq proxy:
     session.start_plan(tool_calls)
     return session.dispatch(tool_name, tool_args)       # proxy handles everything
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Sequence, Union

import httpx

from .models import IntentToken, ToolCall
from .plan_builder import (
    ToolNameParser,
    build_plan_from_tool_calls,
    default_tool_name_parser,
    hash_tool_calls,
)

if TYPE_CHECKING:
    from .client import ArmorIQClient

logger = logging.getLogger(__name__)

SessionMode = Literal["local", "proxy", "sdk"]


@dataclass
class SessionOptions:
    tool_name_parser: Optional[ToolNameParser] = None
    default_mcp_name: Optional[str] = None
    validity_seconds: int = 3600
    llm: str = "agent"
    mode: SessionMode = "local"


@dataclass
class EnforceResult:
    allowed: bool
    action: Literal["allow", "block", "hold"]
    reason: Optional[str] = None
    delegation_id: Optional[str] = None
    matched_policy: Optional[str] = None


@dataclass
class ReportOptions:
    status: Literal["success", "failed", "error"] = "success"
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    is_delegated: Optional[bool] = None
    delegated_by: Optional[str] = None
    delegated_to: Optional[str] = None


class ArmorIQSession:
    """
    Session abstraction for one LLM turn / one plan.

    See ``armoriq-sdk-customer-ts/src/session.ts`` for the canonical docs.
    """

    def __init__(
        self,
        client: "ArmorIQClient",
        opts: Optional[SessionOptions] = None,
    ):
        self._client = client
        o = opts or SessionOptions()
        self._default_mcp_name = o.default_mcp_name
        self._tool_name_parser: ToolNameParser = (
            o.tool_name_parser or default_tool_name_parser(self._default_mcp_name)
        )
        self._validity_seconds = o.validity_seconds
        self._llm = o.llm
        self._mode: SessionMode = o.mode
        self._step_index: int = 0

        self._current_plan_hash: Optional[str] = None
        self._current_token: Optional[IntentToken] = None
        self._mcp_by_action: Dict[str, str] = {}
        self._declared_tools: set = set()

    # ─── Plan capture ──────────────────────────────────────────────────

    def start_plan(
        self,
        tool_calls: Sequence[Union[ToolCall, Dict[str, Any]]],
        goal: Optional[str] = None,
    ) -> IntentToken:
        """Capture a plan from the LLM's tool calls and mint an intent token."""
        if not tool_calls:
            raise ValueError("start_plan called with no tool calls.")

        h = hash_tool_calls(tool_calls)
        if self._current_token and self._current_plan_hash == h:
            return self._current_token

        plan = build_plan_from_tool_calls(
            tool_calls,
            goal=goal,
            tool_name_parser=self._tool_name_parser,
            default_mcp_name=self._default_mcp_name,
        )

        self._mcp_by_action.clear()
        self._declared_tools.clear()
        for step in plan["steps"]:
            self._mcp_by_action[step["action"]] = step["mcp"]
            self._declared_tools.add(step["action"])
            self._declared_tools.add(f"{step['mcp']}__{step['action']}")
        for tc in tool_calls:
            name = tc.name if isinstance(tc, ToolCall) else tc["name"]
            self._declared_tools.add(name)

        plan_capture = self._client.capture_plan(self._llm, goal or self._llm, plan)
        token = self._client.get_intent_token(
            plan_capture,
            validity_seconds=self._validity_seconds,
        )

        self._current_plan_hash = h
        self._current_token = token
        self._step_index = 0
        return token

    # ─── Policy enforcement ────────────────────────────────────────────

    def enforce_local(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> EnforceResult:
        """Local-mode enforcement — verifies plan binding + policy snapshot in-process."""
        if not self._current_token:
            return EnforceResult(
                allowed=False, action="block", reason="No intent token — call start_plan() first"
            )

        if self._current_token.is_expired:
            return EnforceResult(allowed=False, action="block", reason="token-expired")

        mcp, action = self._tool_name_parser(tool_name)
        in_plan = (
            tool_name in self._declared_tools
            or action in self._declared_tools
            or f"{mcp}__{action}" in self._declared_tools
        )
        if not in_plan:
            return EnforceResult(
                allowed=False,
                action="block",
                reason=f"tool-not-in-plan: '{tool_name}' was not declared in the captured plan",
            )

        pv = self._current_token.policy_validation or {}
        snapshot = self._current_token.policy_snapshot or []

        def rule_of(entry: Any) -> Any:
            if not isinstance(entry, dict):
                return entry
            return entry.get("memberRule") or entry.get("clientRule") or entry.get("rules") or entry

        governing_entry: Optional[Dict[str, Any]] = None
        if isinstance(snapshot, list):
            for entry in snapshot:
                r = rule_of(entry)
                if not r:
                    continue
                allowed = r.get("allowedTools") or []
                if not isinstance(allowed, list):
                    continue
                if action in allowed or tool_name in allowed:
                    governing_entry = entry
                    break
                if any(t == "*" or t.endswith("/*") or t.endswith("*") for t in allowed):
                    governing_entry = entry
                    break
                target = (entry.get("targetName") or entry.get("policyName") or "").lower()
                if mcp.lower() in target:
                    governing_entry = entry
                    break

        governing_rule = rule_of(governing_entry) if governing_entry else None
        governing_policy_name = (
            governing_entry.get("policyName") if isinstance(governing_entry, dict) else None
        )
        not_allowed_action = (
            (governing_entry.get("defaultEnforcementAction") if isinstance(governing_entry, dict) else None)
            or pv.get("default_enforcement_action")
            or "block"
        )

        denied_tools = pv.get("denied_tools")
        if isinstance(denied_tools, list):
            if tool_name in denied_tools or action in denied_tools:
                denied_reasons = pv.get("denied_reasons") or []
                reason_from_backend = next(
                    (r for r in denied_reasons if r.startswith(f"{action}:") or r.startswith(f"{tool_name}:")),
                    None,
                )
                reason = reason_from_backend or (
                    f"Tool '{action}' is denied by policy '{governing_policy_name}'"
                    if governing_policy_name
                    else f"Tool '{action}' is denied by policy"
                )
                return EnforceResult(
                    allowed=False,
                    action="hold" if not_allowed_action == "hold" else "block",
                    reason=reason,
                    matched_policy=governing_policy_name,
                )

        if governing_rule:
            allowed = governing_rule.get("allowedTools") or []
            if isinstance(allowed, list) and allowed:
                ok = (
                    "*" in allowed
                    or action in allowed
                    or tool_name in allowed
                )
                if not ok:
                    return EnforceResult(
                        allowed=False,
                        action="hold" if not_allowed_action == "hold" else "block",
                        reason=f"Tool '{action}' is not in the allowed tools for policy '{governing_policy_name}'",
                        matched_policy=governing_policy_name,
                    )
        elif isinstance(snapshot, list) and snapshot:
            allowed_tools = pv.get("allowed_tools")
            if isinstance(allowed_tools, list) and not allowed_tools:
                return EnforceResult(
                    allowed=False,
                    action="block",
                    reason=f"Tool '{action}' is not allowed by any policy in scope",
                )

        if governing_rule:
            threshold_decision = self._evaluate_amount_threshold(
                governing_rule, tool_args, action, mcp
            )
            if threshold_decision is not None:
                threshold_decision.matched_policy = governing_policy_name
                return threshold_decision

        return EnforceResult(
            allowed=True,
            action="allow",
            reason="Allowed by local policy evaluation",
            matched_policy=governing_policy_name,
        )

    def enforce_sdk(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_email: Optional[str] = None,
    ) -> EnforceResult:
        """SDK-mode enforcement: call conmap-auto's ``/iap/sdk/enforce`` directly."""
        if not self._current_token:
            raise RuntimeError(
                f'enforce_sdk("{tool_name}") called before start_plan().'
            )

        mcp, action = self._tool_name_parser(tool_name)
        resolved_mcp = self._mcp_by_action.get(action, mcp)
        in_plan = (
            tool_name in self._declared_tools
            or action in self._declared_tools
            or f"{resolved_mcp}__{action}" in self._declared_tools
        )
        if not in_plan:
            return EnforceResult(
                allowed=False,
                action="block",
                reason=f"tool-not-in-plan: '{tool_name}' was not declared in the captured plan",
            )

        try:
            response = self._client.http_client.post(
                f"{self._client.backend_endpoint}/iap/sdk/enforce",
                json={
                    "tool": action,
                    "arguments": tool_args,
                    "intent_token": self._current_token.raw_token,
                    "policy_snapshot": self._current_token.policy_snapshot,
                    "user_email": user_email,
                },
                headers={
                    "X-API-Key": self._client.api_key,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            data = response.json() or {}
            allowed = data.get("allowed") is not False
            action_decision = data.get("enforcementAction") or ("allow" if allowed else "block")
            matched = (data.get("matchedPolicy") or {}).get("name")
            if action_decision == "hold":
                return self._handle_hold(
                    tool_name,
                    tool_args,
                    EnforceResult(
                        allowed=False,
                        action="hold",
                        reason=data.get("reason") or data.get("message"),
                        matched_policy=matched,
                    ),
                    user_email=user_email,
                )
            return EnforceResult(
                allowed=allowed,
                action=action_decision,
                reason=data.get("reason") or data.get("message"),
                matched_policy=matched,
            )
        except Exception as e:
            logger.warning("enforce_sdk() failed: %s. Allowing tool call.", e)
            return EnforceResult(allowed=True, action="allow", reason="enforce-unavailable")

    def enforce(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> EnforceResult:
        """Proxy-mode enforcement: calls the proxy's /invoke with enforce_only=True."""
        if not self._current_token:
            raise RuntimeError(f'enforce("{tool_name}") called before start_plan().')

        mcp, action = self._tool_name_parser(tool_name)
        resolved_mcp = self._mcp_by_action.get(action, mcp)
        in_plan = (
            tool_name in self._declared_tools
            or action in self._declared_tools
            or f"{resolved_mcp}__{action}" in self._declared_tools
        )
        if not in_plan:
            return EnforceResult(
                allowed=False,
                action="block",
                reason=f"tool-not-in-plan: '{tool_name}' was not declared in the captured plan",
            )

        try:
            payload = {
                "enforce_only": True,
                "mcp": resolved_mcp,
                "tool": action,
                "action": action,
                "params": tool_args,
                "arguments": tool_args,
                "intent_token": self._current_token.raw_token,
                "plan": (self._current_token.raw_token or {}).get("plan"),
            }
            if self._current_token.policy_snapshot:
                payload["policy_snapshot"] = self._current_token.policy_snapshot

            response = self._client.http_client.post(
                f"{self._client.default_proxy_endpoint}/invoke",
                json=payload,
                headers={
                    "X-API-Key": self._client.api_key,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            if response.status_code == 403:
                data = {}
                try:
                    data = response.json() or {}
                except Exception:
                    pass
                return EnforceResult(
                    allowed=False,
                    action=data.get("action") or "block",
                    reason=data.get("reason") or data.get("message"),
                    matched_policy=data.get("matched_policy"),
                )
            data = response.json() or {}
            return EnforceResult(
                allowed=data.get("allowed") is not False,
                action=data.get("action") or ("block" if data.get("allowed") is False else "allow"),
                reason=data.get("reason"),
                delegation_id=data.get("delegation_id"),
                matched_policy=data.get("matched_policy"),
            )
        except httpx.HTTPError as e:
            logger.warning("enforce() failed: %s. Allowing tool call.", e)
            return EnforceResult(allowed=True, action="allow", reason="enforce-unavailable")

    def check(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_email: Optional[str] = None,
    ) -> EnforceResult:
        """Mode-aware enforcement entry point."""
        if self._mode == "sdk":
            return self.enforce_sdk(tool_name, tool_args, user_email=user_email)
        if self._mode == "local":
            decision = self.enforce_local(tool_name, tool_args)
            if decision.action == "hold":
                decision.action = "block"
                decision.reason = (
                    (decision.reason or "requires approval")
                    + " — switch ARMORIQ_MODE=proxy to enable approval workflows for this action."
                )
            return decision

        decision = self.enforce(tool_name, tool_args)
        if decision.action != "hold":
            return decision
        return self._handle_hold(tool_name, tool_args, decision, user_email=user_email)

    # ─── Report / dispatch ─────────────────────────────────────────────

    def report(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Any,
        opts: Optional[ReportOptions] = None,
    ) -> None:
        """Report a tool execution to the audit log AFTER the agent calls the MCP."""
        o = opts or ReportOptions()
        mcp, action = self._tool_name_parser(tool_name)
        resolved_mcp = self._mcp_by_action.get(action, mcp)

        try:
            token = self._current_token
            user_email = getattr(self._client, "user_email_override", None)

            output: Any = result
            if isinstance(result, str):
                output = {"text": result}
            elif result is None:
                output = {}

            self._client.http_client.post(
                f"{self._client.backend_endpoint}/iap/audit",
                json={
                    "token": (token.jwt_token if token else None) or (token.token_id if token else "unknown"),
                    "plan_id": (token.plan_id if token else None)
                    or (token.token_id if token else "unknown"),
                    "step_index": self._step_index,
                    "action": action,
                    "tool": action,
                    "mcp": resolved_mcp,
                    "input": tool_args,
                    "output": output,
                    "status": o.status,
                    "error_message": o.error_message,
                    "duration_ms": o.duration_ms,
                    "is_delegated": o.is_delegated,
                    "delegated_by": o.delegated_by,
                    "user_email": user_email,
                    "delegated_to": o.delegated_to,
                    "executed_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                },
                headers={
                    "X-API-Key": self._client.api_key,
                    "Content-Type": "application/json",
                },
                timeout=5.0,
            )
        except Exception as e:
            logger.warning("report() failed: %s", e)

        self._step_index += 1

    def dispatch(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Route a tool call through the Armoriq proxy. Returns the raw result."""
        if not self._current_token:
            raise RuntimeError(f'dispatch("{tool_name}") called before start_plan().')

        mcp, action = self._tool_name_parser(tool_name)
        resolved_mcp = self._mcp_by_action.get(action, mcp)
        result = self._client.invoke(resolved_mcp, action, self._current_token, params=tool_args)
        self._step_index += 1
        return result.result

    # ─── Helpers ───────────────────────────────────────────────────────

    def _handle_hold(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        hold_decision: EnforceResult,
        user_email: Optional[str] = None,
    ) -> EnforceResult:
        from .models import DelegationRequestParams  # local import keeps the dep light

        email = user_email or getattr(self._client, "user_id", None) or "unknown@armoriq"
        mcp, action = self._tool_name_parser(tool_name)
        resolved_mcp = self._mcp_by_action.get(action, mcp)

        amount = self._extract_amount(tool_args)
        try:
            approved = self._client.check_approved_delegation(email, action, amount or 0)
            if approved:
                try:
                    if approved.delegation_id:
                        self._client.mark_delegation_executed(email, approved.delegation_id)
                except Exception:
                    pass
                return EnforceResult(
                    allowed=True,
                    action="allow",
                    reason=f"Allowed by approved delegation {approved.delegation_id or ''}".strip(),
                    delegation_id=approved.delegation_id,
                    matched_policy=hold_decision.matched_policy,
                )
        except Exception:
            pass

        delegation_id: Optional[str] = None
        try:
            result = self._client.create_delegation_request(
                DelegationRequestParams(
                    tool=action,
                    action=action,
                    arguments=tool_args,
                    amount=amount,
                    requester_email=email,
                    domain=resolved_mcp,
                    plan_id=(self._current_token.plan_id if self._current_token else None),
                    intent_reference=(self._current_token.token_id if self._current_token else None),
                    merkle_root=(
                        (self._current_token.raw_token or {}).get("merkle_root")
                        if self._current_token
                        else None
                    ),
                    reason=hold_decision.reason,
                )
            )
            delegation_id = result.delegation_id
        except Exception as e:
            logger.warning("create_delegation_request failed: %s", e)

        return EnforceResult(
            allowed=False,
            action="hold",
            reason=hold_decision.reason or "Pending approval",
            delegation_id=delegation_id,
            matched_policy=hold_decision.matched_policy,
        )

    @staticmethod
    def _extract_amount(args: Dict[str, Any]) -> Optional[float]:
        if not isinstance(args, dict):
            return None
        for k in ("amount", "value", "total", "price", "cost"):
            v = args.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
        return None

    def _resolve_canonical_amount(
        self, mcp: str, tool_name: str, args: Dict[str, Any]
    ) -> Optional[float]:
        try:
            meta = self._client.fetch_tool_metadata(mcp)
            tool_meta = meta.tool_metadata.get(tool_name) if meta.tool_metadata else None
            if tool_meta and tool_meta.amount_fields:
                for field_name in tool_meta.amount_fields:
                    raw = args.get(field_name)
                    if raw is None:
                        continue
                    try:
                        num = float(raw)
                    except (TypeError, ValueError):
                        continue
                    return num / 100 if tool_meta.amount_unit == "cents" else num
        except Exception:
            pass
        return self._extract_amount(args)

    def _evaluate_amount_threshold(
        self,
        rule: Dict[str, Any],
        tool_args: Dict[str, Any],
        action: str,
        mcp: str,
    ) -> Optional[EnforceResult]:
        fin = (rule.get("financialRule") or {}).get("amountThreshold") or rule.get("amountThreshold")
        if not isinstance(fin, dict):
            return None

        amount = self._resolve_canonical_amount(mcp, action, tool_args)
        if amount is None:
            return None

        currency = fin.get("currency") or ""
        max_per = fin.get("maxPerTransaction")
        req_approval = fin.get("requireApprovalAbove")

        if isinstance(max_per, (int, float)) and amount > max_per:
            return EnforceResult(
                allowed=False,
                action="block",
                reason=f"Amount {amount} {currency} exceeds maxPerTransaction ({max_per})".strip(),
            )
        if isinstance(req_approval, (int, float)) and amount > req_approval:
            return EnforceResult(
                allowed=False,
                action="hold",
                reason=f"Amount {amount} {currency} requires approval (threshold: {req_approval})".strip(),
            )
        return None

    # ─── Session state ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Drop cached plan + token so the next start_plan() always mints fresh."""
        self._current_plan_hash = None
        self._current_token = None
        self._mcp_by_action.clear()
        self._declared_tools.clear()
        self._step_index = 0

    @property
    def current_token(self) -> Optional[IntentToken]:
        return self._current_token

    @property
    def current_mode(self) -> SessionMode:
        return self._mode
