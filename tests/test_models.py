"""
Unit tests for ArmorIQ SDK models.
"""

import pytest
from datetime import datetime

from armoriq_sdk.models import (
    IntentToken,
    PlanCapture,
    MCPInvocation,
    MCPInvocationResult,
    DelegationRequest,
    DelegationResult,
    SDKConfig,
)


class TestIntentToken:
    """Test IntentToken model."""

    def test_intent_token_creation(self):
        """Test creating intent token."""
        now = datetime.now().timestamp()
        token = IntentToken(
            token_id="test_123",
            plan_hash="hash_123",
            signature="sig_123",
            issued_at=now,
            expires_at=now + 3600,
            policy={"rules": []},
            composite_identity="identity_123",
            raw_token={"data": "test"},
        )

        assert token.token_id == "test_123"
        assert token.plan_hash == "hash_123"
        assert not token.is_expired

    def test_intent_token_is_expired(self):
        """Test token expiration check."""
        now = datetime.now().timestamp()
        expired_token = IntentToken(
            token_id="expired",
            plan_hash="hash",
            signature="sig",
            issued_at=now - 7200,
            expires_at=now - 3600,  # Expired 1h ago
            policy={},
            composite_identity="id",
            raw_token={},
        )

        assert expired_token.is_expired
        assert expired_token.time_until_expiry < 0

    def test_intent_token_time_until_expiry(self):
        """Test time until expiry calculation."""
        now = datetime.now().timestamp()
        token = IntentToken(
            token_id="test",
            plan_hash="hash",
            signature="sig",
            issued_at=now,
            expires_at=now + 1800,  # 30 minutes
            policy={},
            composite_identity="id",
            raw_token={},
        )

        time_left = token.time_until_expiry
        assert 1790 < time_left < 1810  # ~30 minutes

    def test_intent_token_immutable(self):
        """Test that IntentToken is immutable."""
        token = IntentToken(
            token_id="test",
            plan_hash="hash",
            signature="sig",
            issued_at=123.0,
            expires_at=456.0,
            policy={},
            composite_identity="id",
            raw_token={},
        )

        with pytest.raises(Exception):  # Pydantic frozen model
            token.token_id = "modified"


class TestPlanCapture:
    """Test PlanCapture model."""

    def test_plan_capture_creation(self):
        """Test creating plan capture."""
        plan = PlanCapture(
            plan={"steps": []},
            plan_hash="hash_123",
            merkle_root="merkle_123",
            ordered_paths=["/step1", "/step2"],
            llm="gpt-4",
            prompt="test prompt",
            metadata={"key": "value"},
        )

        assert plan.plan_hash == "hash_123"
        assert plan.llm == "gpt-4"
        assert len(plan.ordered_paths) == 2
        assert plan.metadata["key"] == "value"

    def test_plan_capture_optional_fields(self):
        """Test plan capture with optional fields."""
        plan = PlanCapture(
            plan={"test": "data"},
            plan_hash="hash",
            merkle_root="merkle",
        )

        assert plan.ordered_paths == []
        assert plan.llm is None
        assert plan.prompt is None
        assert plan.metadata == {}


class TestMCPInvocation:
    """Test MCPInvocation model."""

    def test_mcp_invocation_creation(self):
        """Test creating MCP invocation."""
        token = IntentToken(
            token_id="test",
            plan_hash="hash",
            signature="sig",
            issued_at=123.0,
            expires_at=456.0,
            policy={},
            composite_identity="id",
            raw_token={},
        )

        invocation = MCPInvocation(
            mcp="test-mcp",
            action="test_action",
            params={"key": "value"},
            intent_token=token,
            merkle_proof=[{"position": 0, "hash": "sibling"}],
        )

        assert invocation.mcp == "test-mcp"
        assert invocation.action == "test_action"
        assert invocation.params["key"] == "value"
        assert len(invocation.merkle_proof) == 1


class TestMCPInvocationResult:
    """Test MCPInvocationResult model."""

    def test_mcp_invocation_result_creation(self):
        """Test creating invocation result."""
        result = MCPInvocationResult(
            mcp="test-mcp",
            action="test_action",
            result={"data": "success"},
            status="success",
            execution_time=1.23,
            verified=True,
            metadata={"extra": "info"},
        )

        assert result.mcp == "test-mcp"
        assert result.status == "success"
        assert result.execution_time == 1.23
        assert result.verified is True

    def test_mcp_invocation_result_defaults(self):
        """Test invocation result with defaults."""
        result = MCPInvocationResult(
            mcp="test-mcp",
            action="test_action",
        )

        assert result.status == "success"
        assert result.verified is True
        assert result.metadata == {}


class TestDelegationModels:
    """Test delegation-related models."""

    def test_delegation_request_creation(self):
        """Test creating delegation request."""
        token = IntentToken(
            token_id="test",
            plan_hash="hash",
            signature="sig",
            issued_at=123.0,
            expires_at=456.0,
            policy={},
            composite_identity="id",
            raw_token={},
        )

        request = DelegationRequest(
            target_agent="agent_123",
            subtask={"action": "test"},
            intent_token=token,
            trust_policy={"policy": "strict"},
        )

        assert request.target_agent == "agent_123"
        assert request.subtask["action"] == "test"

    def test_delegation_result_creation(self):
        """Test creating delegation result."""
        token = IntentToken(
            token_id="test",
            plan_hash="hash",
            signature="sig",
            issued_at=123.0,
            expires_at=456.0,
            policy={},
            composite_identity="id",
            raw_token={},
        )

        result = DelegationResult(
            target_agent="agent_123",
            new_token=token,
            trust_delta={"type": "delegation"},
            status="delegated",
        )

        assert result.target_agent == "agent_123"
        assert result.status == "delegated"
        assert isinstance(result.new_token, IntentToken)


class TestSDKConfig:
    """Test SDK configuration model."""

    def test_sdk_config_creation(self):
        """Test creating SDK config."""
        config = SDKConfig(
            iap_endpoint="http://iap.example.com",
            proxy_endpoints={"mcp1": "http://proxy1.example.com"},
            user_id="user_123",
            agent_id="agent_123",
            context_id="ctx_123",
            timeout=60.0,
            max_retries=5,
            verify_ssl=False,
            api_key="secret_key",
        )

        assert config.iap_endpoint == "http://iap.example.com"
        assert config.user_id == "user_123"
        assert config.timeout == 60.0
        assert config.verify_ssl is False

    def test_sdk_config_defaults(self):
        """Test SDK config with defaults."""
        config = SDKConfig(
            iap_endpoint="http://iap.example.com",
            user_id="user_123",
            agent_id="agent_123",
        )

        assert config.proxy_endpoints == {}
        assert config.context_id is None
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.verify_ssl is True
        assert config.api_key is None
