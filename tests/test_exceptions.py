"""
Unit tests for ArmorIQ SDK exceptions.

Mirrors parity with TypeScript SDK exception surface.
"""

import pytest

from armoriq_sdk.exceptions import (
    ArmorIQException,
    ConfigurationException,
    DelegationException,
    IntentMismatchException,
    InvalidTokenException,
    MCPInvocationException,
    PolicyBlockedException,
    PolicyHoldException,
    TokenExpiredException,
)


class TestExceptionHierarchy:
    def test_base_exception(self):
        exc = ArmorIQException("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)

    def test_invalid_token_inherits_base(self):
        assert isinstance(InvalidTokenException("e"), ArmorIQException)

    def test_intent_mismatch_inherits_base(self):
        assert isinstance(IntentMismatchException("e"), ArmorIQException)

    def test_token_expired_inherits_invalid_token(self):
        exc = TokenExpiredException("expired")
        assert isinstance(exc, InvalidTokenException)
        assert isinstance(exc, ArmorIQException)

    def test_policy_blocked_inherits_base(self):
        assert isinstance(PolicyBlockedException("blocked"), ArmorIQException)

    def test_policy_hold_inherits_base(self):
        assert isinstance(PolicyHoldException("hold"), ArmorIQException)

    def test_configuration_inherits_base(self):
        assert isinstance(ConfigurationException("bad"), ArmorIQException)


class TestInvalidTokenException:
    def test_basic(self):
        exc = InvalidTokenException("Token is invalid")
        assert str(exc) == "Token is invalid"
        assert exc.token_id is None

    def test_with_token_id(self):
        exc = InvalidTokenException("Token is invalid", token_id="token_123")
        assert exc.token_id == "token_123"


class TestIntentMismatchException:
    def test_basic(self):
        exc = IntentMismatchException("Action not in plan")
        assert exc.action is None
        assert exc.plan_hash is None

    def test_with_details(self):
        exc = IntentMismatchException("bad", action="tool_x", plan_hash="hash_abc")
        assert exc.action == "tool_x"
        assert exc.plan_hash == "hash_abc"


class TestTokenExpiredException:
    def test_basic(self):
        exc = TokenExpiredException("expired")
        assert exc.expired_at is None

    def test_with_expiry(self):
        exc = TokenExpiredException("expired", token_id="t", expired_at=123456.0)
        assert exc.token_id == "t"
        assert exc.expired_at == 123456.0


class TestMCPInvocationException:
    def test_basic(self):
        exc = MCPInvocationException("bad")
        assert exc.mcp is None and exc.action is None and exc.status_code is None

    def test_with_details(self):
        exc = MCPInvocationException("down", mcp="m", action="a", status_code=503)
        assert exc.mcp == "m"
        assert exc.action == "a"
        assert exc.status_code == 503


class TestDelegationException:
    def test_basic(self):
        exc = DelegationException("failed")
        assert exc.target_agent is None

    def test_with_details(self):
        exc = DelegationException(
            "failed",
            target_agent="agent_x",
            delegation_id="del_1",
            status_code=500,
        )
        assert exc.target_agent == "agent_x"
        assert exc.delegation_id == "del_1"
        assert exc.status_code == 500


class TestPolicyBlockedException:
    def test_basic(self):
        exc = PolicyBlockedException("blocked")
        assert exc.enforcement_action is None
        assert exc.reason is None
        assert exc.metadata is None

    def test_with_details(self):
        exc = PolicyBlockedException(
            "amount exceeds limit",
            enforcement_action="block",
            reason="over $500 cap",
            metadata={"tool": "send_payment", "amount": 1000},
        )
        assert exc.enforcement_action == "block"
        assert exc.reason == "over $500 cap"
        assert exc.metadata["amount"] == 1000


class TestPolicyHoldException:
    def test_basic(self):
        exc = PolicyHoldException("held for approval")
        assert exc.delegation_context is None
        assert exc.metadata is None

    def test_with_details(self):
        exc = PolicyHoldException(
            "manager approval required",
            delegation_context={"domain": "stripe", "targetUrl": "https://..."},
            metadata={"amount": 250, "approvalThreshold": 100},
        )
        assert exc.delegation_context["domain"] == "stripe"
        assert exc.metadata["approvalThreshold"] == 100


class TestExceptionUsage:
    def test_catch_specific(self):
        with pytest.raises(InvalidTokenException) as info:
            raise InvalidTokenException("x", token_id="tok_1")
        assert info.value.token_id == "tok_1"

    def test_catch_base(self):
        for exc_cls in (
            InvalidTokenException,
            IntentMismatchException,
            MCPInvocationException,
            DelegationException,
            PolicyBlockedException,
            PolicyHoldException,
        ):
            with pytest.raises(ArmorIQException):
                raise exc_cls("x")
