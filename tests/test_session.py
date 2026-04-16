"""
Unit tests for ArmorIQSession.

Covers:
- ``start_plan()``   — builds plan, mints token, idempotent re-call
- ``enforce_local()`` — token expiry, plan-binding, denied tools, allow-list
- ``check()``        — mode-aware dispatch (local downgrades 'hold' → 'block')
- ``dispatch()``     — proxy-mode direct invocation
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from armoriq_sdk import (
    ArmorIQClient,
    ArmorIQSession,
    IntentToken,
    SessionOptions,
    ToolCall,
)


def _client_with_token(token: IntentToken) -> ArmorIQClient:
    c = ArmorIQClient(
        api_key="ak_test_xxx",
        _skip_api_key_validation=True,
        use_production=False,
    )
    c.http_client = MagicMock()
    c.capture_plan = MagicMock(
        side_effect=lambda llm, prompt, plan: MagicMock(plan=plan, llm=llm, prompt=prompt)
    )
    c.get_intent_token = MagicMock(return_value=token)
    return c


def _make_token(
    plan_steps=None,
    expires_offset: float = 3600,
    policy_validation=None,
    policy_snapshot=None,
) -> IntentToken:
    now = datetime.now().timestamp()
    steps = plan_steps or [{"action": "charge", "mcp": "Stripe"}]
    return IntentToken(
        token_id="tok_1",
        plan_hash="hash_1",
        signature="sig_1",
        issued_at=now,
        expires_at=now + expires_offset,
        policy={},
        composite_identity="ci_1",
        policy_validation=policy_validation,
        policy_snapshot=policy_snapshot,
        raw_token={"plan": {"steps": steps}, "token": {}},
        total_steps=len(steps),
    )


class TestStartPlan:
    def test_builds_plan_and_mints_token(self):
        token = _make_token()
        client = _client_with_token(token)
        session = client.start_session()
        calls = [ToolCall(name="Stripe__charge", args={"amount": 1})]

        result = session.start_plan(calls, goal="test")
        assert result is token
        client.capture_plan.assert_called_once()
        client.get_intent_token.assert_called_once()

    def test_empty_tool_calls_raises(self):
        client = _client_with_token(_make_token())
        session = client.start_session()
        with pytest.raises(ValueError, match="no tool calls"):
            session.start_plan([])

    def test_idempotent_for_same_hash(self):
        token = _make_token()
        client = _client_with_token(token)
        session = client.start_session()
        calls = [ToolCall(name="Stripe__charge", args={"amount": 1})]

        session.start_plan(calls)
        session.start_plan(calls)
        assert client.get_intent_token.call_count == 1

    def test_remints_for_different_calls(self):
        token1 = _make_token()
        token2 = _make_token()
        client = _client_with_token(token1)
        client.get_intent_token.side_effect = [token1, token2]
        session = client.start_session()

        session.start_plan([ToolCall(name="Stripe__charge", args={"amount": 1})])
        session.start_plan([ToolCall(name="Stripe__refund", args={"id": "x"})])
        assert client.get_intent_token.call_count == 2


class TestEnforceLocal:
    def test_no_token_blocks(self):
        client = _client_with_token(_make_token())
        session = client.start_session()
        result = session.enforce_local("Stripe__charge", {})
        assert result.allowed is False
        assert result.action == "block"
        assert "start_plan" in (result.reason or "")

    def test_expired_token_blocks(self):
        token = _make_token(expires_offset=-60)
        client = _client_with_token(token)
        session = client.start_session()
        session._current_token = token
        session._declared_tools = {"Stripe__charge", "charge"}
        result = session.enforce_local("Stripe__charge", {})
        assert result.action == "block"
        assert "expired" in (result.reason or "")

    def test_tool_not_in_plan(self):
        token = _make_token()
        client = _client_with_token(token)
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={})])

        result = session.enforce_local("Stripe__refund", {})
        assert result.action == "block"
        assert "tool-not-in-plan" in (result.reason or "")

    def test_allow_when_in_plan(self):
        token = _make_token()
        client = _client_with_token(token)
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={})])

        result = session.enforce_local("Stripe__charge", {})
        assert result.allowed is True
        assert result.action == "allow"

    def test_denied_tools_list(self):
        token = _make_token(
            policy_validation={
                "denied_tools": ["charge"],
                "denied_reasons": ["charge: over limit"],
                "default_enforcement_action": "block",
            }
        )
        client = _client_with_token(token)
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={})])

        result = session.enforce_local("Stripe__charge", {})
        assert result.action == "block"
        assert "over limit" in (result.reason or "")

    def test_not_in_allowed_tools(self):
        token = _make_token(
            policy_snapshot=[
                {
                    "policyName": "StripePol",
                    "targetName": "Stripe",
                    "rules": {"allowedTools": ["refund"]},
                }
            ]
        )
        client = _client_with_token(token)
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={})])

        result = session.enforce_local("Stripe__charge", {})
        assert result.action == "block"
        assert "not in the allowed tools" in (result.reason or "")

    def test_amount_threshold_block(self):
        token = _make_token(
            policy_snapshot=[
                {
                    "policyName": "P",
                    "targetName": "Stripe",
                    "rules": {
                        "allowedTools": ["charge"],
                        "amountThreshold": {
                            "maxPerTransaction": 100,
                            "currency": "USD",
                        },
                    },
                }
            ]
        )
        client = _client_with_token(token)
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={"amount": 500})])

        result = session.enforce_local("Stripe__charge", {"amount": 500})
        assert result.action == "block"
        assert "exceeds" in (result.reason or "")

    def test_amount_threshold_hold(self):
        token = _make_token(
            policy_snapshot=[
                {
                    "policyName": "P",
                    "targetName": "Stripe",
                    "rules": {
                        "allowedTools": ["charge"],
                        "amountThreshold": {
                            "requireApprovalAbove": 100,
                            "currency": "USD",
                        },
                    },
                }
            ]
        )
        client = _client_with_token(token)
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={"amount": 500})])

        result = session.enforce_local("Stripe__charge", {"amount": 500})
        assert result.action == "hold"


class TestCheckModeDispatch:
    def test_local_mode_downgrades_hold_to_block(self):
        token = _make_token(
            policy_snapshot=[
                {
                    "policyName": "P",
                    "targetName": "Stripe",
                    "rules": {
                        "allowedTools": ["charge"],
                        "amountThreshold": {
                            "requireApprovalAbove": 10,
                            "currency": "USD",
                        },
                    },
                }
            ]
        )
        client = _client_with_token(token)
        session = client.start_session(SessionOptions(mode="local"))
        session.start_plan([ToolCall(name="Stripe__charge", args={"amount": 100})])
        result = session.check("Stripe__charge", {"amount": 100})
        assert result.action == "block"
        assert "ARMORIQ_MODE=proxy" in (result.reason or "")


class TestDispatch:
    def test_invokes_client_invoke(self):
        token = _make_token()
        client = _client_with_token(token)
        client.invoke = MagicMock(
            return_value=MagicMock(result={"ok": True})
        )
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={"a": 1})])
        out = session.dispatch("Stripe__charge", {"a": 1})
        assert out == {"ok": True}
        client.invoke.assert_called_once()

    def test_no_token_raises(self):
        client = _client_with_token(_make_token())
        session = client.start_session()
        with pytest.raises(RuntimeError, match="before start_plan"):
            session.dispatch("Stripe__charge", {})


class TestReset:
    def test_clears_state(self):
        client = _client_with_token(_make_token())
        session = client.start_session()
        session.start_plan([ToolCall(name="Stripe__charge", args={})])
        assert session.current_token is not None
        session.reset()
        assert session.current_token is None


class TestSessionStart:
    def test_client_start_session_returns_session(self):
        client = _client_with_token(_make_token())
        session = client.start_session()
        assert isinstance(session, ArmorIQSession)
        assert session.current_mode == "local"

    def test_start_session_with_proxy_mode(self):
        client = _client_with_token(_make_token())
        session = client.start_session(SessionOptions(mode="proxy"))
        assert session.current_mode == "proxy"
