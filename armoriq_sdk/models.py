"""
Pydantic models for ArmorIQ SDK data structures.

Mirrors the TypeScript SDK models at parity. Field naming uses Python's
``snake_case`` at the API boundary; all TS interfaces have corresponding
pydantic models here.
"""

from typing import Any, Callable, Dict, List, Literal, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class IntentToken(BaseModel):
    """Represents a signed intent token from IAP."""

    model_config = ConfigDict(frozen=True)

    token_id: str = Field(..., description="Unique token identifier (intent_reference)")
    plan_hash: str = Field(..., description="CSRG canonical plan hash")
    plan_id: Optional[str] = Field(None, description="Plan ID from IAP")
    signature: str = Field(..., description="Ed25519 signature")
    issued_at: float = Field(..., description="Unix timestamp of issuance")
    expires_at: float = Field(..., description="Unix timestamp of expiration")
    policy: Dict[str, Any] = Field(default_factory=dict, description="Policy manifest")
    composite_identity: str = Field(..., description="Composite identity hash")
    client_info: Optional[Dict[str, Any]] = Field(None, description="Client information")
    policy_validation: Optional[Dict[str, Any]] = Field(
        None, description="Policy validation with allowed_tools"
    )
    step_proofs: List[Any] = Field(
        default_factory=list, description="Merkle proofs for steps"
    )
    total_steps: int = Field(0, description="Total steps in plan")
    raw_token: Dict[str, Any] = Field(..., description="Full raw token payload")
    jwt_token: Optional[str] = Field(None, description="JWT token for verify-step endpoint")
    policy_snapshot: Optional[List[Dict[str, Any]]] = Field(
        None, description="OPA-formatted policy snapshot for proxy → OPA enforcement"
    )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now().timestamp() > self.expires_at

    @property
    def time_until_expiry(self) -> float:
        """Get seconds until token expiry (negative if expired)."""
        return self.expires_at - datetime.now().timestamp()


class PlanCapture(BaseModel):
    """
    Represents a captured plan ready for token issuance.

    The plan structure contains only the steps the agent intends to execute.
    Hash and Merkle tree generation happen later in ``get_intent_token()``
    on the CSRG-IAP service side.
    """

    plan: Dict[str, Any] = Field(..., description="Plan structure with steps")
    llm: Optional[str] = Field(None, description="LLM identifier")
    prompt: Optional[str] = Field(None, description="Original prompt")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class MCPInvocation(BaseModel):
    """Represents an MCP action invocation request."""

    mcp: str = Field(..., description="MCP identifier")
    action: str = Field(..., description="Action to invoke (tool name)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    intent_token: IntentToken = Field(..., description="Intent token")
    merkle_proof: Optional[List[Dict[str, Any]]] = Field(
        None, description="Merkle proof for action"
    )
    iam_context: Optional[Dict[str, Any]] = Field(
        None, description="IAM context (email, user_id, role, limits)"
    )


class MCPInvocationResult(BaseModel):
    """Result from an MCP action invocation."""

    mcp: str = Field(..., description="MCP identifier")
    action: str = Field(..., description="Action invoked")
    result: Any = Field(None, description="Action result")
    status: str = Field("success", description="Execution status")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    verified: bool = Field(True, description="Token verification status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class DelegationRequest(BaseModel):
    """Request for delegating a subtask to another agent."""

    target_agent: str = Field(..., description="Target agent identifier")
    subtask: Dict[str, Any] = Field(..., description="Subtask to delegate")
    intent_token: IntentToken = Field(..., description="Current intent token")
    trust_policy: Optional[Dict[str, Any]] = Field(
        None, description="Trust policy for delegation"
    )
    delegate_public_key: str = Field(..., description="Public key of delegate")
    validity_seconds: float = Field(300.0, description="Token validity in seconds")


class DelegationResult(BaseModel):
    """Result from a delegation request."""

    delegation_id: str = Field(..., description="Delegation identifier")
    delegated_token: IntentToken = Field(..., description="Delegated intent token")
    delegate_public_key: str = Field(..., description="Public key of delegate")
    target_agent: Optional[str] = Field(None, description="Target agent identifier")
    expires_at: float = Field(..., description="Expiration timestamp")
    trust_delta: Dict[str, Any] = Field(default_factory=dict, description="Trust delta")
    status: str = Field("delegated", description="Delegation status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")

    @property
    def new_token(self) -> IntentToken:
        """Alias for delegated_token (deprecated)."""
        return self.delegated_token


class ToolSemanticEntry(BaseModel):
    """Semantic metadata for a single tool on an MCP server."""

    is_financial: Optional[bool] = Field(None, alias="isFinancial")
    transaction_type: Optional[str] = Field(None, alias="transactionType")
    amount_fields: Optional[List[str]] = Field(None, alias="amountFields")
    amount_unit: Optional[str] = Field(None, alias="amountUnit")
    currency: Optional[str] = None
    recipient_field: Optional[str] = Field(None, alias="recipientField")
    category: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class MCPSemanticMetadata(BaseModel):
    """Semantic metadata for an MCP server (tool annotations + role mapping)."""

    mcp_id: str = Field("", alias="mcpId")
    name: str = ""
    tool_metadata: Dict[str, ToolSemanticEntry] = Field(
        default_factory=dict, alias="toolMetadata"
    )
    role_mapping: Dict[str, str] = Field(default_factory=dict, alias="roleMapping")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PolicyContext(BaseModel):
    """Policy context enriched from semantic metadata."""

    is_financial: bool = False
    transaction_type: Optional[str] = None
    amount: Optional[float] = None
    recipient_id: Optional[str] = None


class HoldInfo(BaseModel):
    """Information about a hold enforcement action."""

    delegation_id: Optional[str] = None
    reason: str
    amount: Optional[float] = None
    approval_threshold: Optional[float] = None
    tool: str
    mcp: str

    model_config = ConfigDict(extra="allow")


class InvokeOptions(BaseModel):
    """Options for the enhanced invoke_with_policy() method."""

    wait_for_approval: Optional[bool] = None
    delegation_timeout_ms: Optional[int] = None
    on_hold: Optional[Callable[[HoldInfo], None]] = None
    user_email: Optional[str] = None
    requester_role: Optional[str] = None
    requester_limit: Optional[float] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DelegationRequestParams(BaseModel):
    """Parameters for creating a delegation request."""

    tool: str
    action: str
    arguments: Optional[Dict[str, Any]] = None
    amount: Optional[float] = None
    requester_email: str = Field(..., alias="requesterEmail")
    requester_role: Optional[str] = Field(None, alias="requesterRole")
    requester_limit: Optional[float] = Field(None, alias="requesterLimit")
    domain: Optional[str] = None
    target_url: Optional[str] = Field(None, alias="targetUrl")
    plan_id: Optional[str] = Field(None, alias="planId")
    intent_reference: Optional[str] = Field(None, alias="intentReference")
    merkle_root: Optional[str] = Field(None, alias="merkleRoot")
    reason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DelegationRequestResult(BaseModel):
    """Result from creating a delegation request."""

    delegation_id: str = Field(..., alias="delegationId")
    status: str
    expires_at: str = Field(..., alias="expiresAt")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ApprovedDelegation(BaseModel):
    """Result from checking an approved delegation."""

    delegation_id: str = Field(..., alias="delegationId")
    approver_email: str = Field(..., alias="approverEmail")
    approver_role: str = Field(..., alias="approverRole")
    delegation_token: Optional[str] = Field(None, alias="delegationToken")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ToolCall(BaseModel):
    """
    A single tool call as surfaced by an LLM framework (ADK, LangChain,
    OpenAI Agents, Vercel AI SDK, etc.). Used by ArmorIQSession to capture
    a plan without making the caller hand-build the SDK plan shape.
    """

    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class _McpCredBearer(BaseModel):
    auth_type: Literal["bearer"] = Field("bearer", alias="authType")
    token: str
    model_config = ConfigDict(populate_by_name=True)


class _McpCredApiKey(BaseModel):
    auth_type: Literal["api_key"] = Field("api_key", alias="authType")
    api_key: str = Field(..., alias="apiKey")
    header_name: Optional[str] = Field(None, alias="headerName")
    model_config = ConfigDict(populate_by_name=True)


class _McpCredBasic(BaseModel):
    auth_type: Literal["basic"] = Field("basic", alias="authType")
    username: str
    password: str
    model_config = ConfigDict(populate_by_name=True)


class _McpCredNone(BaseModel):
    auth_type: Literal["none"] = Field("none", alias="authType")
    model_config = ConfigDict(populate_by_name=True)


McpCredential = Union[_McpCredBearer, _McpCredApiKey, _McpCredBasic, _McpCredNone]
"""
Credential for an upstream MCP. Forwarded per-call to the proxy via the
``X-Armoriq-MCP-Auth`` header. The proxy injects the appropriate upstream
auth header and drops this one before forwarding. Armoriq does not store
these values.
"""

McpCredentialMap = Dict[str, McpCredential]
"""Map of MCP identifier to runtime credential."""


class SDKConfig(BaseModel):
    """SDK configuration."""

    iap_endpoint: str = Field(..., description="IAP endpoint URL")
    proxy_endpoint: Optional[str] = Field(None, description="Default proxy endpoint")
    backend_endpoint: Optional[str] = Field(None, description="Backend endpoint")
    proxy_endpoints: Dict[str, str] = Field(
        default_factory=dict, description="MCP proxy endpoints"
    )
    user_id: str = Field(..., description="User identifier")
    agent_id: str = Field(..., description="Agent identifier")
    context_id: Optional[str] = Field(None, description="Context identifier")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    use_production: bool = Field(True, description="Use production endpoints")
    mcp_credentials: Optional[Dict[str, Any]] = Field(
        None, description="Per-MCP runtime credentials"
    )
