"""
Pydantic models for ArmorIQ SDK data structures.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class IntentToken(BaseModel):
    """
    Represents a signed intent token from IAP.
    
    Attributes:
        token_id: Unique identifier for this token (intent_reference)
        plan_hash: CSRG hash of the canonical plan
        plan_id: Plan ID from IAP
        signature: Ed25519 signature from IAP
        issued_at: Token issuance timestamp
        expires_at: Token expiration timestamp
        policy: Policy manifest applied to this token
        composite_identity: Composite identity hash (user+agent+context)
        client_info: Client information (clientId, clientName, orgId)
        policy_validation: Policy validation result with allowed_tools
        step_proofs: Array of Merkle proofs for each step
        total_steps: Total number of steps in plan
        raw_token: Full raw token payload
    """

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
    step_proofs: List[Dict[str, Any]] = Field(
        default_factory=list, description="Merkle proofs for steps"
    )
    total_steps: int = Field(0, description="Total steps in plan")
    raw_token: Dict[str, Any] = Field(..., description="Full raw token payload")

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
    Hash and Merkle tree generation happens later in get_intent_token() 
    on the CSRG-IAP service side.
    
    Attributes:
        plan: Plan structure with steps
        llm: LLM identifier used to generate the plan
        prompt: Original prompt used
        metadata: Additional metadata
    """

    plan: Dict[str, Any] = Field(..., description="Plan structure with steps")
    llm: Optional[str] = Field(None, description="LLM identifier")
    prompt: Optional[str] = Field(None, description="Original prompt")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class MCPInvocation(BaseModel):
    """
    Represents an MCP action invocation request.
    
    Attributes:
        mcp: MCP identifier
        action: Action name to invoke (tool name)
        params: Action parameters
        intent_token: Intent token for verification
        merkle_proof: Optional Merkle proof for this action
        iam_context: IAM context to pass to MCP tool (email, user_id, role, limits)
    """

    mcp: str = Field(..., description="MCP identifier")
    action: str = Field(..., description="Action to invoke (tool name)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    intent_token: IntentToken = Field(..., description="Intent token")
    merkle_proof: Optional[List[Dict[str, Any]]] = Field(
        None, description="Merkle proof for action"
    )
    iam_context: Optional[Dict[str, Any]] = Field(
        None, description="IAM context (email, loan_role, loan_limit, allowed_tools)"
    )


class MCPInvocationResult(BaseModel):
    """
    Result from an MCP action invocation.
    
    Attributes:
        mcp: MCP identifier
        action: Action that was invoked
        result: Action result data
        status: Execution status
        execution_time: Time taken to execute (seconds)
        verified: Whether token verification succeeded
    """

    mcp: str = Field(..., description="MCP identifier")
    action: str = Field(..., description="Action invoked")
    result: Any = Field(None, description="Action result")
    status: str = Field("success", description="Execution status")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    verified: bool = Field(True, description="Token verification status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class DelegationRequest(BaseModel):
    """
    Request for delegating a subtask to another agent.
    
    Attributes:
        target_agent: Target agent identifier
        subtask: Subtask plan to delegate
        intent_token: Current intent token
        trust_policy: Optional trust policy for delegation
        delegate_public_key: Public key of delegate agent
        validity_seconds: Token validity in seconds
    """

    target_agent: str = Field(..., description="Target agent identifier")
    subtask: Dict[str, Any] = Field(..., description="Subtask to delegate")
    intent_token: IntentToken = Field(..., description="Current intent token")
    trust_policy: Optional[Dict[str, Any]] = Field(
        None, description="Trust policy for delegation"
    )
    delegate_public_key: str = Field(..., description="Public key of delegate")
    validity_seconds: float = Field(300.0, description="Token validity in seconds")


class DelegationResult(BaseModel):
    """
    Result from a delegation request.
    
    Attributes:
        delegation_id: Unique delegation identifier
        delegated_token: New intent token for the delegated subtask
        delegate_public_key: Public key of the delegate agent
        target_agent: Optional target agent identifier
        expires_at: Expiration timestamp
        trust_delta: Trust update applied
        status: Delegation status
        metadata: Extra metadata
    """

    delegation_id: str = Field(..., description="Delegation identifier")
    delegated_token: IntentToken = Field(..., description="Delegated intent token")
    delegate_public_key: str = Field(..., description="Public key of delegate")
    target_agent: Optional[str] = Field(None, description="Target agent identifier")
    expires_at: float = Field(..., description="Expiration timestamp")
    trust_delta: Dict[str, Any] = Field(default_factory=dict, description="Trust delta")
    status: str = Field("delegated", description="Delegation status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")
    
    # Deprecated fields for backwards compatibility
    @property
    def new_token(self) -> IntentToken:
        """Alias for delegated_token (deprecated)"""
        return self.delegated_token


class SDKConfig(BaseModel):
    """
    SDK configuration.
    
    Attributes:
        iap_endpoint: IAP service endpoint URL
        proxy_endpoints: Mapping of MCP identifiers to proxy URLs
        user_id: User identifier
        agent_id: Agent identifier
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        verify_ssl: Whether to verify SSL certificates
    """

    iap_endpoint: str = Field(..., description="IAP endpoint URL")
    proxy_endpoints: Dict[str, str] = Field(
        default_factory=dict, description="MCP proxy endpoints"
    )
    user_id: str = Field(..., description="User identifier")
    agent_id: str = Field(..., description="Agent identifier")
    context_id: Optional[str] = Field(None, description="Context identifier")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    api_key: Optional[str] = Field(None, description="Optional API key for authentication")
