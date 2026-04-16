"""
Unit tests for ArmorIQ SDK client.

The client performs HTTP calls against the IAP / proxy / backend; all are
mocked via ``client.http_client`` so no network hits are made.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from armoriq_sdk import (
    ArmorIQClient,
    ConfigurationException,
    DelegationException,
    IntentMismatchException,
    InvalidTokenException,
    MCPInvocationException,
    PolicyBlockedException,
    TokenExpiredException,
)
from armoriq_sdk.models import (
    ApprovedDelegation,
    DelegationRequestParams,
    IntentToken,
    MCPSemanticMetadata,
    PlanCapture,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """A fully-constructed client with a mocked HTTP layer."""
    c = ArmorIQClient(
        api_key="ak_test_fake123",
        user_id="test_user",
        agent_id="test_agent",
        use_production=False,
        _skip_api_key_validation=True,
    )
    c.http_client = MagicMock()
    return c


@pytest.fixture
def sample_plan():
    return PlanCapture(
        plan={"goal": "test", "steps": [{"action": "do_thing", "mcp": "test-mcp"}]},
        llm="gpt-4",
        prompt="test",
        metadata={},
    )


def _make_token(action: str = "do_thing", mcp: str = "test-mcp") -> IntentToken:
    now = datetime.now().timestamp()
    raw = {
        "plan": {"goal": "g", "steps": [{"action": action, "mcp": mcp}]},
        "token": {"signature": "sig"},
        "plan_hash": "hash_1",
    }
    return IntentToken(
        token_id="tok_1",
        plan_hash="hash_1",
        signature="sig",
        issued_at=now,
        expires_at=now + 3600,
        policy={},
        composite_identity="ci",
        raw_token=raw,
        step_proofs=[[{"position": "left", "hash": "sib"}]],
        total_steps=1,
    )


def _response(status: int = 200, json_data=None, content_type: str = "application/json"):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.headers = {"content-type": content_type}
    resp.json.return_value = json_data or {}
    resp.text = ""
    return resp


# ---------------------------------------------------------------------------
# Configuration / API-key tests
# ---------------------------------------------------------------------------


class TestClientInitialization:
    def test_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("ARMORIQ_API_KEY", raising=False)
        with pytest.raises(ConfigurationException, match="API key is required"):
            ArmorIQClient(user_id="u", agent_id="a")

    def test_rejects_invalid_key_format(self):
        with pytest.raises(ConfigurationException, match="Invalid API key format"):
            ArmorIQClient(api_key="totally_wrong", _skip_api_key_validation=True)

    def test_accepts_ak_claw_prefix(self):
        c = ArmorIQClient(
            api_key="ak_claw_abc",
            use_production=True,
            _skip_api_key_validation=True,
        )
        assert c.api_key == "ak_claw_abc"
        assert c.iap_endpoint == ArmorIQClient.ARMORCLAW_IAP_ENDPOINT
        assert c.default_proxy_endpoint == ArmorIQClient.ARMORCLAW_PROXY_ENDPOINT
        assert c.backend_endpoint == ArmorIQClient.ARMORCLAW_BACKEND_ENDPOINT

    def test_accepts_ak_live_prefix(self):
        c = ArmorIQClient(
            api_key="ak_live_abc",
            use_production=True,
            _skip_api_key_validation=True,
        )
        assert c.iap_endpoint == ArmorIQClient.DEFAULT_IAP_ENDPOINT
        assert c.default_proxy_endpoint == ArmorIQClient.DEFAULT_PROXY_ENDPOINT
        assert c.backend_endpoint == ArmorIQClient.DEFAULT_BACKEND_ENDPOINT

    def test_uses_local_endpoints_when_not_production(self):
        c = ArmorIQClient(
            api_key="ak_test_abc",
            use_production=False,
            _skip_api_key_validation=True,
        )
        assert c.iap_endpoint == ArmorIQClient.LOCAL_IAP_ENDPOINT

    def test_env_override_endpoints(self, monkeypatch):
        monkeypatch.setenv("IAP_ENDPOINT", "http://env-iap.test")
        monkeypatch.setenv("BACKEND_ENDPOINT", "http://env-backend.test")
        monkeypatch.setenv("PROXY_ENDPOINT", "http://env-proxy.test")
        c = ArmorIQClient(api_key="ak_test_xxx", _skip_api_key_validation=True)
        assert c.iap_endpoint == "http://env-iap.test"
        assert c.backend_endpoint == "http://env-backend.test"
        assert c.default_proxy_endpoint == "http://env-proxy.test"

    def test_default_sdk_multiuser_ids(self):
        c = ArmorIQClient(api_key="ak_test_xxx", _skip_api_key_validation=True)
        assert c.user_id == "__sdk_multiuser__"
        assert c.agent_id == "__sdk_multiuser__"

    def test_context_manager(self, client):
        with client as c:
            assert c is client
        client.http_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# capture_plan
# ---------------------------------------------------------------------------


class TestCapturePlan:
    def test_basic(self, client):
        capture = client.capture_plan(
            "gpt-4",
            "a task",
            plan={"goal": "g", "steps": [{"action": "x"}]},
        )
        assert isinstance(capture, PlanCapture)
        assert capture.llm == "gpt-4"
        assert len(capture.plan["steps"]) == 1

    def test_requires_plan(self, client):
        with pytest.raises(ValueError, match="Plan structure is required"):
            client.capture_plan("gpt-4", "a task")

    def test_requires_steps(self, client):
        with pytest.raises(ValueError, match="'steps'"):
            client.capture_plan("gpt-4", "t", plan={"goal": "g"})


# ---------------------------------------------------------------------------
# get_intent_token
# ---------------------------------------------------------------------------


class TestGetIntentToken:
    def test_success(self, client, sample_plan):
        client.http_client.post.return_value = _response(
            200,
            {
                "success": True,
                "intent_reference": "tok_1",
                "plan_hash": "hash_1",
                "composite_identity": "ci_1",
                "token": {"signature": "sig_1"},
                "step_proofs": [[{"position": "left", "hash": "sib"}]],
                "policy_snapshot": [{"policyName": "p1"}],
                "jwt_token": "jwt.token.here",
            },
        )
        token = client.get_intent_token(sample_plan, validity_seconds=120)
        assert token.token_id == "tok_1"
        assert token.plan_hash == "hash_1"
        assert token.jwt_token == "jwt.token.here"
        assert token.policy_snapshot == [{"policyName": "p1"}]
        assert token.total_steps == 1

    def test_http_500_raises_invalid_token(self, client, sample_plan):
        client.http_client.post.return_value = _response(
            500, {"message": "down"}
        )
        with pytest.raises(InvalidTokenException, match="Token issuance failed"):
            client.get_intent_token(sample_plan)

    def test_403_raises_policy_blocked(self, client, sample_plan):
        client.http_client.post.return_value = _response(
            403,
            {
                "success": False,
                "message": "blocked",
                "policy_validation": {
                    "denied_tools": ["do_thing"],
                    "denied_reasons": ["do_thing: amount too high"],
                    "default_enforcement_action": "block",
                },
            },
        )
        with pytest.raises(PolicyBlockedException) as info:
            client.get_intent_token(sample_plan)
        assert info.value.reason is not None
        assert "amount too high" in info.value.reason
        assert info.value.enforcement_action == "block"

    def test_unsuccessful_body_raises_invalid_token(self, client, sample_plan):
        client.http_client.post.return_value = _response(
            200, {"success": False, "message": "sig fail"}
        )
        with pytest.raises(InvalidTokenException, match="Token issuance failed"):
            client.get_intent_token(sample_plan)


# ---------------------------------------------------------------------------
# invoke
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_success(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(
            200,
            {"result": {"ok": True}, "status": "success"},
        )
        result = client.invoke("test-mcp", "do_thing", token, params={"k": "v"})
        assert result.mcp == "test-mcp"
        assert result.action == "do_thing"
        assert result.status == "success"
        assert result.verified is True
        assert result.result == {"ok": True}

    def test_expired_token(self, client):
        now = datetime.now().timestamp()
        expired = IntentToken(
            token_id="t",
            plan_hash="h",
            signature="s",
            issued_at=now - 7200,
            expires_at=now - 3600,
            policy={},
            composite_identity="ci",
            raw_token={"plan": {"steps": [{"action": "do_thing"}]}},
        )
        with pytest.raises(TokenExpiredException, match="expired"):
            client.invoke("test-mcp", "do_thing", expired)

    def test_action_not_in_plan(self, client):
        token = _make_token(action="other_action")
        with pytest.raises(IntentMismatchException, match="not found in the original plan"):
            client.invoke("test-mcp", "do_thing", token)

    def test_401_raises_invalid_token(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(
            401, {"message": "bad token"}
        )
        with pytest.raises(InvalidTokenException):
            client.invoke("test-mcp", "do_thing", token)

    def test_409_raises_intent_mismatch(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(
            409, {"message": "not in plan"}
        )
        with pytest.raises(IntentMismatchException):
            client.invoke("test-mcp", "do_thing", token)

    def test_enforcement_block_raises_policy_blocked(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(
            200,
            {
                "enforcement": {
                    "action": "block",
                    "reason": "amount too big",
                    "metadata": {"amount": 9999},
                },
                "message": "blocked by policy",
            },
        )
        with pytest.raises(PolicyBlockedException) as info:
            client.invoke("test-mcp", "do_thing", token)
        assert info.value.reason == "amount too big"

    def test_500_raises_mcp_invocation(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(
            500, {"message": "boom"}
        )
        with pytest.raises(MCPInvocationException):
            client.invoke("test-mcp", "do_thing", token)

    def test_tool_error_in_result(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(
            200, {"result": {"isError": True, "text": "tool failure"}}
        )
        result = client.invoke("test-mcp", "do_thing", token)
        assert result.status == "error"
        assert result.metadata["hasToolError"] is True


# ---------------------------------------------------------------------------
# delegate (legacy CSRG path)
# ---------------------------------------------------------------------------


class TestDelegate:
    def test_success(self, client):
        token = _make_token()
        now = datetime.now().timestamp()
        client.http_client.post.return_value = _response(
            200,
            {
                "delegation_id": "d_1",
                "delegation": {
                    "token_id": "deleg_tok",
                    "plan_hash": "hash_1",
                    "signature": "new_sig",
                    "issued_at": now,
                    "expires_at": now + 1800,
                    "composite_identity": "new_ci",
                    "policy": {},
                },
                "trust_delta": {"type": "delegation"},
            },
        )
        result = client.delegate(token, delegate_public_key="abcd")
        assert result.delegation_id == "d_1"
        assert result.delegated_token.token_id == "deleg_tok"
        assert result.delegate_public_key == "abcd"

    def test_missing_delegation_key(self, client):
        token = _make_token()
        client.http_client.post.return_value = _response(200, {"delegation_id": "d"})
        with pytest.raises(DelegationException, match="missing 'delegation'"):
            client.delegate(token, delegate_public_key="abcd")

    def test_http_error_raises(self, client):
        token = _make_token()
        resp = _response(500, {"message": "down"})
        resp.text = "down"
        client.http_client.post.return_value = resp
        with pytest.raises(DelegationException, match="Delegation failed"):
            client.delegate(token, delegate_public_key="abcd")


# ---------------------------------------------------------------------------
# verify_token
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def test_valid(self, client):
        assert client.verify_token(_make_token()) is True

    def test_expired(self, client):
        now = datetime.now().timestamp()
        t = IntentToken(
            token_id="t",
            plan_hash="h",
            signature="s",
            issued_at=now - 7200,
            expires_at=now - 3600,
            policy={},
            composite_identity="ci",
            raw_token={},
        )
        assert client.verify_token(t) is False

    def test_missing_fields(self, client):
        now = datetime.now().timestamp()
        t = IntentToken(
            token_id="t",
            plan_hash="",
            signature="",
            issued_at=now,
            expires_at=now + 3600,
            policy={},
            composite_identity="ci",
            raw_token={},
        )
        assert client.verify_token(t) is False


# ---------------------------------------------------------------------------
# Semantic metadata & role resolution
# ---------------------------------------------------------------------------


class TestSemanticMetadata:
    def test_fetch_tool_metadata_caches(self, client):
        client.http_client.get.return_value = _response(
            200,
            {
                "data": {
                    "mcpId": "mcp_1",
                    "name": "Stripe",
                    "toolMetadata": {
                        "charge": {"isFinancial": True, "amountFields": ["amount"]}
                    },
                    "roleMapping": {"admin": "owner"},
                }
            },
        )
        meta = client.fetch_tool_metadata("Stripe")
        assert isinstance(meta, MCPSemanticMetadata)
        assert meta.tool_metadata["charge"].is_financial is True

        # Cache hit — no second HTTP call
        meta2 = client.fetch_tool_metadata("Stripe")
        assert meta2 is meta
        assert client.http_client.get.call_count == 1

    def test_fetch_tool_metadata_404_returns_empty(self, client):
        client.http_client.get.return_value = _response(404, {})
        meta = client.fetch_tool_metadata("Unknown")
        assert meta.tool_metadata == {}

    def test_load_mcp_delegates(self, client):
        client.http_client.get.return_value = _response(
            200, {"data": {"mcpId": "", "name": "X", "toolMetadata": {}, "roleMapping": {}}}
        )
        client.load_mcp("X")
        client.http_client.get.assert_called_once()

    def test_list_mcps(self, client):
        client.http_client.get.return_value = _response(
            200, {"data": [{"mcpId": "a", "name": "A", "url": "http://a"}]}
        )
        mcps = client.list_mcps()
        assert mcps == [{"mcpId": "a", "name": "A", "url": "http://a"}]

    def test_list_mcps_error(self, client):
        resp = _response(500, {})
        resp.text = "down"
        client.http_client.get.return_value = resp
        with pytest.raises(MCPInvocationException):
            client.list_mcps()

    def test_get_mcp_tool_schemas(self, client):
        client.http_client.get.return_value = _response(
            200, {"data": {"tools": [{"name": "charge"}]}}
        )
        schemas = client.get_mcp_tool_schemas("Stripe")
        assert schemas == [{"name": "charge"}]

    def test_resolve_role_known(self, client):
        client.http_client.get.return_value = _response(
            200,
            {
                "data": {
                    "mcpId": "",
                    "name": "Stripe",
                    "toolMetadata": {},
                    "roleMapping": {"admin": "owner"},
                }
            },
        )
        assert client.resolve_role("Stripe", "admin") == "owner"

    def test_resolve_role_fallback(self, client):
        client.http_client.get.return_value = _response(
            200,
            {
                "data": {
                    "mcpId": "",
                    "name": "Stripe",
                    "toolMetadata": {},
                    "roleMapping": {},
                }
            },
        )
        assert client.resolve_role("Stripe", "unknown") == "unknown"


# ---------------------------------------------------------------------------
# Delegation automation helpers
# ---------------------------------------------------------------------------


class TestDelegationAutomation:
    def test_create_delegation_request(self, client):
        client.http_client.post.return_value = _response(
            200,
            {
                "delegationId": "d_1",
                "status": "pending",
                "expiresAt": "2026-04-18T00:00:00Z",
            },
        )
        params = DelegationRequestParams(
            tool="charge",
            action="execute",
            requester_email="u@co.com",
            amount=1000.0,
        )
        result = client.create_delegation_request(params)
        assert result.delegation_id == "d_1"
        assert result.status == "pending"

    def test_create_delegation_request_failure(self, client):
        resp = _response(500, {"message": "down"})
        resp.text = "down"
        client.http_client.post.return_value = resp
        with pytest.raises(DelegationException):
            client.create_delegation_request(
                DelegationRequestParams(
                    tool="t", action="e", requester_email="u@co.com"
                )
            )

    def test_check_approved_delegation_found(self, client):
        client.http_client.get.return_value = _response(
            200,
            {
                "approved": True,
                "delegationId": "d_1",
                "approverEmail": "boss@co.com",
                "approverRole": "cfo",
            },
        )
        approved = client.check_approved_delegation("u@co.com", "charge", 100)
        assert isinstance(approved, ApprovedDelegation)
        assert approved.delegation_id == "d_1"

    def test_check_approved_delegation_not_approved(self, client):
        client.http_client.get.return_value = _response(200, {"approved": False})
        assert client.check_approved_delegation("u@co.com", "charge", 100) is None

    def test_check_approved_delegation_http_error(self, client):
        client.http_client.get.return_value = _response(404, {})
        assert client.check_approved_delegation("u@co.com", "charge", 100) is None

    def test_mark_delegation_executed(self, client):
        client.http_client.post.return_value = _response(200, {})
        client.mark_delegation_executed("u@co.com", "d_1")
        client.http_client.post.assert_called_once()
        _, call_kwargs = client.http_client.post.call_args
        assert call_kwargs["json"]["delegationId"] == "d_1"
        assert call_kwargs["headers"]["X-User-Email"] == "u@co.com"

    def test_complete_plan_updates_status(self, client):
        client.http_client.post.return_value = _response(200, {})
        client.complete_plan("p_1")
        called_url = client.http_client.post.call_args[0][0]
        assert "/iap/plans/p_1/status" in called_url


# ---------------------------------------------------------------------------
# MCP credential encoding
# ---------------------------------------------------------------------------


class TestMcpCredentials:
    def test_ctor_credentials(self):
        c = ArmorIQClient(
            api_key="ak_test_xxx",
            _skip_api_key_validation=True,
            mcp_credentials={"Stripe": {"authType": "bearer", "token": "tok_xyz"}},
        )
        cred = c._get_mcp_credential("Stripe")
        assert cred == {"authType": "bearer", "token": "tok_xyz"}

    def test_env_credentials(self, monkeypatch):
        monkeypatch.setenv("ARMORIQ_MCP_STRIPE_AUTH_TYPE", "bearer")
        monkeypatch.setenv("ARMORIQ_MCP_STRIPE_TOKEN", "tok_env")
        c = ArmorIQClient(api_key="ak_test_xxx", _skip_api_key_validation=True)
        cred = c._get_mcp_credential("STRIPE")
        assert cred["token"] == "tok_env"

    def test_json_credentials_env(self, monkeypatch):
        monkeypatch.setenv(
            "ARMORIQ_MCP_CREDENTIALS",
            '{"Svc": {"authType": "api_key", "apiKey": "ak_x"}}',
        )
        c = ArmorIQClient(api_key="ak_test_xxx", _skip_api_key_validation=True)
        assert c._get_mcp_credential("Svc")["apiKey"] == "ak_x"

    def test_encode_header_is_base64_json(self):
        import base64
        import json

        header = ArmorIQClient._encode_mcp_auth_header(
            {"authType": "bearer", "token": "tok"}
        )
        decoded = json.loads(base64.b64decode(header).decode("utf-8"))
        assert decoded == {"authType": "bearer", "token": "tok"}
