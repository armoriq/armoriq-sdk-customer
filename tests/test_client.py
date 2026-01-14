"""
Unit tests for ArmorIQ SDK client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from armoriq_sdk import (
    ArmorIQClient,
    InvalidTokenException,
    IntentMismatchException,
    TokenExpiredException,
    MCPInvocationException,
    ConfigurationException,
)
from armoriq_sdk.models import IntentToken, PlanCapture


@pytest.fixture
def mock_http_client():
    """Mock httpx client."""
    with patch("armoriq_sdk.client.httpx.Client") as mock:
        yield mock.return_value


@pytest.fixture
def client(mock_http_client):
    """Create test client."""
    return ArmorIQClient(
        iap_endpoint="http://test-iap.example.com",
        proxy_endpoints={"test-mcp": "http://test-proxy.example.com"},
        user_id="test_user",
        agent_id="test_agent",
    )


@pytest.fixture
def sample_plan():
    """Sample plan capture."""
    return PlanCapture(
        plan={"goal": "test", "steps": [{"action": "test_action"}]},
        plan_hash="test_plan_hash_123",
        merkle_root="test_merkle_root",
        ordered_paths=["/steps/0/action"],
        llm="gpt-4",
        prompt="test prompt",
    )


@pytest.fixture
def sample_token():
    """Sample intent token."""
    now = datetime.now().timestamp()
    return IntentToken(
        token_id="test_token_123",
        plan_hash="test_plan_hash_123",
        signature="test_signature",
        issued_at=now,
        expires_at=now + 3600,
        policy={"rules": []},
        composite_identity="test_identity",
        raw_token={"token_id": "test_token_123"},
    )


class TestClientInitialization:
    """Test client initialization and configuration."""

    def test_client_creation_with_all_params(self):
        """Test creating client with all parameters."""
        client = ArmorIQClient(
            iap_endpoint="http://iap.example.com",
            proxy_endpoints={"mcp1": "http://proxy1.example.com"},
            user_id="user1",
            agent_id="agent1",
            context_id="ctx1",
            timeout=60.0,
            max_retries=5,
        )

        assert client.iap_endpoint == "http://iap.example.com"
        assert client.user_id == "user1"
        assert client.agent_id == "agent1"
        assert client.context_id == "ctx1"
        assert client.timeout == 60.0
        assert client.max_retries == 5

    def test_client_creation_from_env(self, monkeypatch):
        """Test creating client from environment variables."""
        monkeypatch.setenv("IAP_ENDPOINT", "http://env-iap.example.com")
        monkeypatch.setenv("USER_ID", "env_user")
        monkeypatch.setenv("AGENT_ID", "env_agent")

        client = ArmorIQClient()

        assert client.iap_endpoint == "http://env-iap.example.com"
        assert client.user_id == "env_user"
        assert client.agent_id == "env_agent"

    def test_client_missing_iap_endpoint(self):
        """Test error when IAP endpoint missing."""
        with pytest.raises(ConfigurationException, match="iap_endpoint is required"):
            ArmorIQClient(user_id="user1", agent_id="agent1")

    def test_client_missing_user_id(self):
        """Test error when user_id missing."""
        with pytest.raises(ConfigurationException, match="user_id is required"):
            ArmorIQClient(iap_endpoint="http://iap.example.com", agent_id="agent1")

    def test_client_missing_agent_id(self):
        """Test error when agent_id missing."""
        with pytest.raises(ConfigurationException, match="agent_id is required"):
            ArmorIQClient(iap_endpoint="http://iap.example.com", user_id="user1")

    def test_client_context_manager(self, client):
        """Test client as context manager."""
        with client as c:
            assert c is client
        # Should close HTTP client
        client.http_client.close.assert_called_once()


class TestCapturePlan:
    """Test plan capture functionality."""

    @patch("armoriq_sdk.client.CanonicalStructuredReasoningGraph")
    def test_capture_plan_basic(self, mock_csrg, client):
        """Test basic plan capture."""
        # Mock CSRG
        mock_csrg_instance = Mock()
        mock_csrg_instance.plan_hash = "test_hash_123"
        mock_csrg_instance.merkle_root = "test_merkle"
        mock_csrg_instance.ordered_paths = ["/step1", "/step2"]
        mock_csrg.return_value = mock_csrg_instance

        plan = client.capture_plan(llm="gpt-4", prompt="test prompt")

        assert isinstance(plan, PlanCapture)
        assert plan.plan_hash == "test_hash_123"
        assert plan.merkle_root == "test_merkle"
        assert plan.llm == "gpt-4"
        assert plan.prompt == "test prompt"
        assert len(plan.ordered_paths) == 2

    @patch("armoriq_sdk.client.CanonicalStructuredReasoningGraph")
    def test_capture_plan_with_provided_plan(self, mock_csrg, client):
        """Test plan capture with pre-generated plan."""
        mock_csrg_instance = Mock()
        mock_csrg_instance.plan_hash = "custom_hash"
        mock_csrg_instance.merkle_root = "custom_merkle"
        mock_csrg_instance.ordered_paths = []
        mock_csrg.return_value = mock_csrg_instance

        custom_plan = {"custom": "plan", "steps": []}
        plan = client.capture_plan(llm="gpt-4", prompt="test", plan=custom_plan)

        assert plan.plan["custom"] == "plan"
        mock_csrg.assert_called_once()


class TestGetIntentToken:
    """Test intent token acquisition."""

    def test_get_intent_token_success(self, client, sample_plan, mock_http_client):
        """Test successful token acquisition."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent_reference": "token_123",
            "plan_hash": "test_hash",
            "token": {
                "signature": "sig_123",
                "issued_at": datetime.now().timestamp(),
                "expires_at": datetime.now().timestamp() + 300,
                "composite_identity": "identity_123",
            },
        }
        mock_http_client.post.return_value = mock_response

        token = client.get_intent_token(sample_plan)

        assert isinstance(token, IntentToken)
        assert token.token_id == "token_123"
        mock_http_client.post.assert_called_once()

    def test_get_intent_token_caching(self, client, sample_plan, mock_http_client):
        """Test token caching."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent_reference": "token_123",
            "plan_hash": "test_hash",
            "token": {
                "signature": "sig",
                "issued_at": datetime.now().timestamp(),
                "expires_at": datetime.now().timestamp() + 3600,
                "composite_identity": "id",
            },
        }
        mock_http_client.post.return_value = mock_response

        # First call
        token1 = client.get_intent_token(sample_plan)

        # Second call should use cache
        token2 = client.get_intent_token(sample_plan)

        assert token1.token_id == token2.token_id
        # Should only call IAP once
        assert mock_http_client.post.call_count == 1

    def test_get_intent_token_http_error(self, client, sample_plan, mock_http_client):
        """Test token acquisition HTTP error."""
        import httpx

        mock_http_client.post.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock(status_code=500, text="Server error")
        )

        with pytest.raises(InvalidTokenException, match="Failed to get intent token"):
            client.get_intent_token(sample_plan)


class TestInvoke:
    """Test MCP invocation."""

    def test_invoke_success(self, client, sample_token, mock_http_client):
        """Test successful MCP invocation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {"data": "success"},
            "status": "success",
            "verified": True,
        }
        mock_response.status_code = 200
        mock_http_client.post.return_value = mock_response

        result = client.invoke("test-mcp", "test_action", sample_token, params={"key": "value"})

        assert result.mcp == "test-mcp"
        assert result.action == "test_action"
        assert result.status == "success"
        assert result.verified is True
        mock_http_client.post.assert_called_once()

    def test_invoke_expired_token(self, client, sample_token):
        """Test invocation with expired token."""
        # Create expired token
        expired_token = IntentToken(
            token_id="expired_123",
            plan_hash="hash",
            signature="sig",
            issued_at=datetime.now().timestamp() - 7200,
            expires_at=datetime.now().timestamp() - 3600,  # Expired 1h ago
            policy={},
            composite_identity="id",
            raw_token={},
        )

        with pytest.raises(TokenExpiredException, match="Intent token expired"):
            client.invoke("test-mcp", "test_action", expired_token)

    def test_invoke_invalid_token(self, client, sample_token, mock_http_client):
        """Test invocation with invalid token."""
        import httpx

        mock_response = Mock(status_code=401, text="Invalid token")
        mock_http_client.post.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=mock_response
        )

        with pytest.raises(InvalidTokenException, match="Token verification failed"):
            client.invoke("test-mcp", "test_action", sample_token)

    def test_invoke_intent_mismatch(self, client, sample_token, mock_http_client):
        """Test invocation with intent mismatch."""
        import httpx

        mock_response = Mock(status_code=409, text="Action not in plan")
        mock_http_client.post.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=mock_response
        )

        with pytest.raises(IntentMismatchException, match="Action not in plan"):
            client.invoke("test-mcp", "test_action", sample_token)

    def test_invoke_mcp_error(self, client, sample_token, mock_http_client):
        """Test invocation with MCP error."""
        import httpx

        mock_response = Mock(status_code=500, text="MCP internal error")
        mock_http_client.post.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=mock_response
        )

        with pytest.raises(MCPInvocationException, match="MCP invocation failed"):
            client.invoke("test-mcp", "test_action", sample_token)


class TestDelegate:
    """Test agent delegation."""

    def test_delegate_success(self, client, sample_token, mock_http_client):
        """Test successful delegation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "delegation_id": "deleg_123",
            "subtask_hash": "subtask_hash",
            "new_token": {
                "signature": "new_sig",
                "issued_at": datetime.now().timestamp(),
                "expires_at": datetime.now().timestamp() + 1800,
                "composite_identity": "new_id",
                "policy": {},
            },
            "trust_delta": {"type": "delegation"},
        }
        mock_http_client.post.return_value = mock_response

        subtask = {"action": "subtask_action"}
        result = client.delegate("target_agent", subtask, sample_token)

        assert result.target_agent == "target_agent"
        assert isinstance(result.new_token, IntentToken)
        mock_http_client.post.assert_called_once()


class TestTokenVerification:
    """Test token verification."""

    def test_verify_token_valid(self, client, sample_token, mock_http_client):
        """Test verifying valid token."""
        mock_response = Mock(status_code=200)
        mock_http_client.post.return_value = mock_response

        result = client.verify_token(sample_token)

        assert result is True

    def test_verify_token_invalid(self, client, sample_token, mock_http_client):
        """Test verifying invalid token."""
        mock_response = Mock(status_code=401)
        mock_http_client.post.return_value = mock_response

        result = client.verify_token(sample_token)

        assert result is False
