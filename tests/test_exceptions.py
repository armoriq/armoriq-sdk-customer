"""
Unit tests for ArmorIQ SDK exceptions.
"""

import pytest

from armoriq_sdk.exceptions import (
    ArmorIQException,
    InvalidTokenException,
    IntentMismatchException,
    TokenExpiredException,
    MCPInvocationException,
    DelegationException,
    ConfigurationException,
)


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance."""

    def test_base_exception(self):
        """Test base ArmorIQException."""
        exc = ArmorIQException("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)

    def test_invalid_token_exception_inherits_base(self):
        """Test InvalidTokenException inherits from base."""
        exc = InvalidTokenException("token error")
        assert isinstance(exc, ArmorIQException)
        assert isinstance(exc, Exception)

    def test_intent_mismatch_exception_inherits_base(self):
        """Test IntentMismatchException inherits from base."""
        exc = IntentMismatchException("mismatch error")
        assert isinstance(exc, ArmorIQException)

    def test_token_expired_exception_inherits_invalid_token(self):
        """Test TokenExpiredException inherits from InvalidTokenException."""
        exc = TokenExpiredException("expired error")
        assert isinstance(exc, InvalidTokenException)
        assert isinstance(exc, ArmorIQException)


class TestInvalidTokenException:
    """Test InvalidTokenException."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = InvalidTokenException("Token is invalid")
        assert str(exc) == "Token is invalid"
        assert exc.token_id is None

    def test_with_token_id(self):
        """Test exception with token ID."""
        exc = InvalidTokenException("Token is invalid", token_id="token_123")
        assert exc.token_id == "token_123"


class TestIntentMismatchException:
    """Test IntentMismatchException."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = IntentMismatchException("Action not in plan")
        assert str(exc) == "Action not in plan"
        assert exc.action is None
        assert exc.plan_hash is None

    def test_with_details(self):
        """Test exception with action and plan hash."""
        exc = IntentMismatchException(
            "Action not allowed", action="test_action", plan_hash="hash_123"
        )
        assert exc.action == "test_action"
        assert exc.plan_hash == "hash_123"


class TestTokenExpiredException:
    """Test TokenExpiredException."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = TokenExpiredException("Token expired")
        assert str(exc) == "Token expired"
        assert exc.expired_at is None

    def test_with_expiry_time(self):
        """Test exception with expiry timestamp."""
        exc = TokenExpiredException("Token expired", token_id="token_123", expired_at=123456.0)
        assert exc.token_id == "token_123"
        assert exc.expired_at == 123456.0


class TestMCPInvocationException:
    """Test MCPInvocationException."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = MCPInvocationException("Invocation failed")
        assert str(exc) == "Invocation failed"
        assert exc.mcp is None
        assert exc.action is None
        assert exc.status_code is None

    def test_with_details(self):
        """Test exception with MCP details."""
        exc = MCPInvocationException(
            "Service unavailable", mcp="test-mcp", action="test_action", status_code=503
        )
        assert exc.mcp == "test-mcp"
        assert exc.action == "test_action"
        assert exc.status_code == 503


class TestDelegationException:
    """Test DelegationException."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = DelegationException("Delegation failed")
        assert str(exc) == "Delegation failed"
        assert exc.target_agent is None

    def test_with_target_agent(self):
        """Test exception with target agent."""
        exc = DelegationException("Cannot delegate", target_agent="agent_123")
        assert exc.target_agent == "agent_123"


class TestConfigurationException:
    """Test ConfigurationException."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = ConfigurationException("Invalid configuration")
        assert str(exc) == "Invalid configuration"
        assert isinstance(exc, ArmorIQException)


class TestExceptionUsage:
    """Test exception usage patterns."""

    def test_catch_specific_exception(self):
        """Test catching specific exception."""
        with pytest.raises(InvalidTokenException) as exc_info:
            raise InvalidTokenException("test error", token_id="token_123")

        assert exc_info.value.token_id == "token_123"

    def test_catch_base_exception(self):
        """Test catching base exception catches all."""
        with pytest.raises(ArmorIQException):
            raise InvalidTokenException("test error")

        with pytest.raises(ArmorIQException):
            raise IntentMismatchException("test error")

        with pytest.raises(ArmorIQException):
            raise MCPInvocationException("test error")

    def test_exception_can_be_reraised(self):
        """Test exceptions can be caught and reraised."""
        try:
            raise InvalidTokenException("original error", token_id="token_123")
        except InvalidTokenException as e:
            # Re-raise with same details
            with pytest.raises(InvalidTokenException) as exc_info:
                raise e

            assert exc_info.value.token_id == "token_123"
