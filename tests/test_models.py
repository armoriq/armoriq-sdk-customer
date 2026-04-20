"""
Unit tests for ArmorIQ SDK models.

Covers the full model surface at parity with the TS SDK.
"""

import pytest
from datetime import datetime

from armoriq_sdk.models import (
    ApprovedDelegation,
    DelegationRequest,
    DelegationRequestParams,
    DelegationRequestResult,
    DelegationResult,
    HoldInfo,
    IntentToken,
    InvokeOptions,
    MCPInvocation,
    MCPInvocationResult,
    MCPSemanticMetadata,
    PlanCapture,
    PolicyContext,
    SDKConfig,
    ToolCall,
    ToolSemanticEntry,
)


def _make_token(offset_secs: float = 3600) -> IntentToken:
    now = datetime.now().timestamp()
    return IntentToken(
        token_id="tok_1",
        plan_hash="hash_1",
        signature="sig_1",
        issued_at=now,
        expires_at=now + offset_secs,
        policy={"rules": []},
        composite_identity="identity_1",
        raw_token={"plan": {"steps": []}, "token": {}},
    )


class TestIntentToken:
    def test_creation(self):
        token = _make_token()
        assert token.token_id == "tok_1"
        assert token.plan_hash == "hash_1"
        assert not token.is_expired

    def test_is_expired_when_past(self):
        token = _make_token(offset_secs=-3600)
        assert token.is_expired
        assert token.time_until_expiry < 0

    def test_time_until_expiry(self):
        token = _make_token(offset_secs=1800)
        assert 1790 < token.time_until_expiry < 1810

    def test_frozen(self):
        token = _make_token()
        with pytest.raises(Exception):
            token.token_id = "modified"

    def test_optional_fields(self):
        token = _make_token()
        assert token.jwt_token is None
        assert token.policy_snapshot is None
        assert token.client_info is None


class TestPlanCapture:
    def test_creation(self):
        capture = PlanCapture(
            plan={"goal": "test", "steps": [{"action": "x"}]},
            llm="gpt-4",
            prompt="do x",
            metadata={"key": "value"},
        )
        assert capture.llm == "gpt-4"
        assert capture.plan["goal"] == "test"
        assert capture.metadata["key"] == "value"

    def test_optional_fields(self):
        capture = PlanCapture(plan={"steps": []})
        assert capture.llm is None
        assert capture.prompt is None
        assert capture.metadata == {}


class TestMCPInvocation:
    def test_creation(self):
        token = _make_token()
        inv = MCPInvocation(
            mcp="m",
            action="a",
            params={"k": "v"},
            intent_token=token,
            merkle_proof=[{"position": 0, "hash": "sib"}],
        )
        assert inv.mcp == "m"
        assert inv.action == "a"
        assert inv.params["k"] == "v"
        assert len(inv.merkle_proof) == 1


class TestMCPInvocationResult:
    def test_creation(self):
        r = MCPInvocationResult(
            mcp="m",
            action="a",
            result={"data": "ok"},
            execution_time=1.5,
        )
        assert r.status == "success"
        assert r.verified is True
        assert r.execution_time == 1.5

    def test_defaults(self):
        r = MCPInvocationResult(mcp="m", action="a")
        assert r.status == "success"
        assert r.metadata == {}


class TestDelegationModels:
    def test_delegation_request(self):
        token = _make_token()
        req = DelegationRequest(
            target_agent="agent_x",
            subtask={"action": "y"},
            intent_token=token,
            delegate_public_key="abcd",
        )
        assert req.target_agent == "agent_x"
        assert req.validity_seconds == 300.0

    def test_delegation_result(self):
        token = _make_token()
        result = DelegationResult(
            delegation_id="d_1",
            delegated_token=token,
            delegate_public_key="abcd",
            expires_at=token.expires_at,
            status="delegated",
        )
        assert result.delegation_id == "d_1"
        assert result.status == "delegated"
        assert result.new_token is token

    def test_delegation_request_params_aliases(self):
        params = DelegationRequestParams(
            tool="send_payment",
            action="execute",
            requester_email="user@co.com",
            amount=100.5,
            domain="stripe",
            plan_id="p_1",
        )
        dumped = params.model_dump(by_alias=True, exclude_none=True)
        assert dumped["requesterEmail"] == "user@co.com"
        assert dumped["planId"] == "p_1"
        assert "requesterRole" not in dumped

    def test_delegation_request_result(self):
        r = DelegationRequestResult.model_validate(
            {"delegationId": "d_1", "status": "pending", "expiresAt": "2026-04-18T00:00:00Z"}
        )
        assert r.delegation_id == "d_1"
        assert r.expires_at == "2026-04-18T00:00:00Z"

    def test_approved_delegation(self):
        r = ApprovedDelegation.model_validate(
            {
                "delegationId": "d_1",
                "approverEmail": "boss@co.com",
                "approverRole": "cfo",
                "delegationToken": "tok_xyz",
            }
        )
        assert r.delegation_id == "d_1"
        assert r.approver_role == "cfo"


class TestSemanticMetadata:
    def test_tool_semantic_entry(self):
        entry = ToolSemanticEntry.model_validate(
            {
                "isFinancial": True,
                "amountFields": ["amount", "total"],
                "amountUnit": "cents",
                "currency": "USD",
                "transactionType": "payment",
                "recipientField": "destination",
            }
        )
        assert entry.is_financial is True
        assert entry.amount_fields == ["amount", "total"]
        assert entry.amount_unit == "cents"

    def test_mcp_semantic_metadata(self):
        meta = MCPSemanticMetadata.model_validate(
            {
                "mcpId": "mcp_1",
                "name": "Stripe",
                "toolMetadata": {
                    "charge": {"isFinancial": True, "amountFields": ["amount"]}
                },
                "roleMapping": {"admin": "owner"},
            }
        )
        assert meta.name == "Stripe"
        assert meta.tool_metadata["charge"].is_financial is True
        assert meta.role_mapping["admin"] == "owner"

    def test_empty_metadata(self):
        meta = MCPSemanticMetadata()
        assert meta.mcp_id == ""
        assert meta.tool_metadata == {}


class TestPolicyContext:
    def test_defaults(self):
        ctx = PolicyContext()
        assert ctx.is_financial is False
        assert ctx.amount is None

    def test_financial(self):
        ctx = PolicyContext(
            is_financial=True, transaction_type="payment", amount=50.0, recipient_id="r_1"
        )
        assert ctx.amount == 50.0


class TestHoldInfo:
    def test_required(self):
        h = HoldInfo(reason="over threshold", tool="charge", mcp="stripe")
        assert h.reason == "over threshold"
        assert h.amount is None

    def test_full(self):
        h = HoldInfo(
            delegation_id="d_1",
            reason="r",
            amount=100.0,
            approval_threshold=500.0,
            tool="t",
            mcp="m",
        )
        assert h.delegation_id == "d_1"
        assert h.amount == 100.0


class TestInvokeOptions:
    def test_defaults(self):
        opts = InvokeOptions()
        assert opts.wait_for_approval is None
        assert opts.on_hold is None
        assert opts.user_email is None

    def test_callback(self):
        captured = []

        def cb(info: HoldInfo) -> None:
            captured.append(info)

        opts = InvokeOptions(
            wait_for_approval=True,
            user_email="u@co.com",
            on_hold=cb,
            delegation_timeout_ms=60000,
        )
        opts.on_hold(HoldInfo(reason="x", tool="t", mcp="m"))
        assert len(captured) == 1
        assert opts.delegation_timeout_ms == 60000


class TestToolCall:
    def test_creation(self):
        tc = ToolCall(name="Stripe__charge", args={"amount": 100})
        assert tc.name == "Stripe__charge"
        assert tc.args["amount"] == 100

    def test_default_args(self):
        tc = ToolCall(name="x")
        assert tc.args == {}


class TestSDKConfig:
    def test_creation(self):
        cfg = SDKConfig(
            iap_endpoint="http://iap.example.com",
            proxy_endpoints={"m1": "http://p1.example.com"},
            user_id="u_1",
            agent_id="a_1",
            timeout=60.0,
            max_retries=5,
            verify_ssl=False,
            api_key="ak_test_xxx",
            use_production=False,
        )
        assert cfg.timeout == 60.0
        assert cfg.use_production is False

    def test_defaults(self):
        cfg = SDKConfig(iap_endpoint="http://iap", user_id="u", agent_id="a")
        assert cfg.proxy_endpoints == {}
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 3
        assert cfg.verify_ssl is True
        assert cfg.use_production is True
