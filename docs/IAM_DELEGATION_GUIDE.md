# IAM Context and Delegation Guide

## Overview

ArmorIQ SDK provides sophisticated IAM (Identity and Access Management) context passing and public key-based delegation to enable secure, auditable multi-agent workflows. This guide explains how these features work and how to use them effectively.

## IAM Context Injection

### What is IAM Context?

IAM context is metadata about the requesting user/agent that gets injected into every MCP tool invocation. It enables MCP tools to:

- **Verify permissions**: Check if the caller has access to requested resources
- **Apply role-based access control**: Enforce different behaviors for different roles
- **Audit actions**: Track who performed what action
- **Filter data**: Return data scoped to the user's permissions

### How It Works

When you call `client.invoke()`, the SDK automatically builds an IAM context dictionary from the intent token and passes it to the MCP:

```python
# You call:
result = client.invoke(
    mcp="loan-mcp",
    action="get_customer_loans",
    intent_token=token,
    params={"customer_id": "CUST-123"},
    user_email="john.doe@example.com"
)

# SDK automatically adds _iam_context:
# {
#   "email": "john.doe@example.com",
#   "user_email": "john.doe@example.com",
#   "user_id": "user-12345",
#   "agent_id": "loan-agent",
#   "allowed_tools": ["get_customer_loans", "check_eligibility"]
# }
```

### IAM Context Structure

The `_iam_context` dictionary contains:

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | User's email address |
| `user_email` | string | Alias for email (backward compatibility) |
| `user_id` | string | Unique user identifier |
| `agent_id` | string | Agent identifier making the request |
| `allowed_tools` | list[str] | Tools permitted by policy validation |
| `loan_role` | string | Optional role (e.g., "requester", "approver") |
| `loan_limit` | float | Optional limit for financial operations |

### MCP Tool Integration

MCP tools receive IAM context as the `_iam_context` parameter:

```python
# In your MCP tool (mcp_tools.py)
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("loan-mcp")

@mcp.tool()
def get_customer_loans(
    customer_id: str,
    user_email: str,
    _iam_context: Optional[dict] = None
) -> dict:
    """
    Get loans for a customer with IAM permission checks.
    """
    # Check permissions
    if _iam_context:
        allowed_tools = _iam_context.get("allowed_tools", [])
        if "get_customer_loans" not in allowed_tools:
            raise PermissionError("Tool not allowed by policy")
        
        # Check if user can access this customer
        requester_email = _iam_context.get("email")
        if not can_access_customer(requester_email, customer_id):
            raise PermissionError("Access denied to customer data")
    
    # Fetch and return loans
    loans = fetch_loans_from_db(customer_id)
    return {"loans": loans}
```

### Policy Validation

Intent tokens include `policy_validation` with `allowed_tools`:

```json
{
  "policy_validation": {
    "domain": "loan-processing",
    "target_type": "customer",
    "matched_policies": ["loan-policy-v1"],
    "allowed_tools": [
      "check_eligibility",
      "get_customer_loans",
      "process_loan"
    ],
    "allowed_endpoints": [
      "/loan-mcp/check_eligibility",
      "/loan-mcp/get_customer_loans"
    ]
  }
}
```

The SDK extracts `allowed_tools` and passes it in `_iam_context`.

## Public Key-Based Delegation

### Why Public Key Delegation?

Traditional delegation uses shared secrets or trust chains. Public key delegation provides:

- **Cryptographic verification**: Delegated tokens are cryptographically bound to delegate's public key
- **No shared secrets**: Delegates don't need access to original credentials
- **Revocable**: Delegations can be revoked without affecting original token
- **Auditable**: Every delegation is logged with public key signatures

### How It Works

```
┌──────────────┐                    ┌──────────────┐
│ User Agent   │                    │ Approval     │
│              │                    │ Agent        │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │ 1. Generate keypair               │
       │    (approval agent)                │
       │                                   │
       │ 2. delegate(                      │
       │      token,                       │
       │      approval_public_key)         │
       ├──────────────────────────────────>│
       │                                   │
       │ 3. IAP validates & creates        │
       │    delegated token                │
       │                                   │
       │<──────────────────────────────────┤
       │    DelegationResult               │
       │                                   │
       │                                   │ 4. Use delegated
       │                                   │    token with
       │                                   │    private key
       │                                   │
```

### Step-by-Step Example

#### 1. Generate Delegate Keypair

The delegate agent generates an Ed25519 keypair:

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate keypair
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Serialize public key to hex
pub_key_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)
pub_key_hex = pub_key_bytes.hex()

print(f"Public key: {pub_key_hex}")
# Output: "a3b2c1d4e5f6..."
```

#### 2. Create Delegation

The delegating agent calls `delegate()` with the public key:

```python
from armoriq_sdk import ArmorIQClient

# User agent with original token
user_client = ArmorIQClient(
    iap_endpoint="http://localhost:3001",
    user_id="user-123",
    agent_id="loan-user-agent"
)

# Get original token
token = user_client.get_intent_token(plan)

# Delegate to approval agent
delegation_result = user_client.delegate(
    intent_token=token,
    delegate_public_key=pub_key_hex,
    validity_seconds=1800,  # 30 minutes
    allowed_actions=["approve_loan", "reject_loan"]
)

print(f"Delegation ID: {delegation_result.delegation_id}")
print(f"Delegated token: {delegation_result.delegated_token.token_id}")
```

#### 3. Use Delegated Token

The delegate agent uses the delegated token with their private key:

```python
# Approval agent
approval_client = ArmorIQClient(
    iap_endpoint="http://localhost:3001",
    user_id="approval-system",
    agent_id="loan-approval-agent"
)

# Use delegated token
result = approval_client.invoke(
    mcp="loan-mcp",
    action="approve_loan",
    intent_token=delegation_result.delegated_token,
    params={
        "customer_id": "CUST-123",
        "loan_amount": 150000,
        "approver_notes": "Verified income and credit score"
    },
    user_email="approver@example.com"
)

print(f"Approval result: {result.result}")
```

### Delegation Constraints

You can constrain delegations:

```python
# Limit to specific actions
delegation = client.delegate(
    intent_token=token,
    delegate_public_key=pub_key_hex,
    allowed_actions=["approve_loan"],  # Only this action
    validity_seconds=600  # 10 minutes only
)
```

### Delegation Chain

Delegations can be chained:

```
User Agent → Manager Agent → Approval Agent
   token₁  →     token₂     →     token₃
```

Each delegation narrows permissions:

```python
# User agent delegates to manager
delegation1 = user_client.delegate(
    intent_token=user_token,
    delegate_public_key=manager_pubkey,
    allowed_actions=["approve_loan", "reject_loan", "request_info"]
)

# Manager delegates to approver (further restricted)
delegation2 = manager_client.delegate(
    intent_token=delegation1.delegated_token,
    delegate_public_key=approver_pubkey,
    allowed_actions=["approve_loan"]  # Only approve, not reject
)
```

## Real-World Workflow: Loan Approval

### Scenario

1. **User** requests $150,000 loan
2. **User Agent** checks eligibility
3. **User Agent** delegates to **Approval Agent** (amount > $50k)
4. **Approval Agent** verifies and approves
5. Result flows back to user

### Implementation

See `examples/loan_delegation_workflow.py` for complete code.

**Key Points:**

- User agent generates approval agent's public key
- Delegation specifies `allowed_actions=["approve_loan"]`
- Approval agent receives delegated token with restricted permissions
- IAM context tracks entire chain: user → user_agent → approval_agent

### Benefits

✅ **Security**: Each agent only has permissions for its role  
✅ **Auditability**: Complete trail of who did what  
✅ **Scalability**: Add new agents without changing infrastructure  
✅ **Flexibility**: Dynamic delegation based on business rules  

## Best Practices

### IAM Context

1. **Always pass user_email**: Enables proper attribution and auditing
2. **Check allowed_tools**: Verify permissions before executing sensitive actions
3. **Log IAM context**: Include in audit logs for compliance
4. **Validate context in MCPs**: Don't trust client-side validation alone

### Delegation

1. **Generate keypairs securely**: Use `ed25519` with proper random sources
2. **Store private keys safely**: Use secure key management systems
3. **Use short validity periods**: Minimize window of compromise (< 1 hour)
4. **Limit allowed_actions**: Only delegate minimum required permissions
5. **Track delegations**: Monitor active delegations and revoke if needed

### Token Management

1. **Check token expiry**: Use `token.is_expired` before invocation
2. **Cache tokens**: Reuse tokens for multiple actions (until expiry)
3. **Handle expiry gracefully**: Refresh token or re-authenticate
4. **Don't log raw tokens**: Tokens contain sensitive signatures

## Troubleshooting

### "Tool not allowed by policy"

**Cause**: Action not in `allowed_tools` from policy validation

**Solution**: 
- Check `token.policy_validation.allowed_tools`
- Ensure action is in original plan
- Request broader policy if legitimate need

### "Delegation failed: Invalid public key"

**Cause**: Public key format incorrect

**Solution**:
- Use Ed25519 keys only
- Serialize to raw bytes, then hex: `public_key.public_bytes(encoding=Raw, format=Raw).hex()`
- Verify hex string is 64 characters (32 bytes)

### "Permission denied in IAM context"

**Cause**: MCP tool rejected request based on IAM context

**Solution**:
- Check user has permission for resource
- Verify `user_email` matches authorized user
- Check role-based access control rules

### "Delegated token expired"

**Cause**: Delegation validity period elapsed

**Solution**:
- Use shorter workflows
- Increase `validity_seconds` (max: 3600)
- Re-delegate if legitimate need persists

## Advanced Topics

### Custom IAM Fields

Add custom fields to IAM context:

```python
# In client initialization
client = ArmorIQClient(
    iap_endpoint="...",
    user_id="user-123",
    agent_id="my-agent",
    custom_context={
        "department": "finance",
        "cost_center": "CC-1234",
        "approval_level": 3
    }
)

# SDK merges custom_context into _iam_context
```

### Delegation Revocation

Revoke delegations when no longer needed:

```python
# Revoke specific delegation
client.revoke_delegation(delegation_id="DEL-123")

# Revoke all delegations for a token
client.revoke_all_delegations(intent_token=token)
```

### Multi-Level Approval

Implement multi-level approvals with delegation chains:

```python
# L1 approval
l1_delegation = user_client.delegate(
    token, l1_approver_pubkey,
    allowed_actions=["pre_approve_loan"]
)

# L2 approval (only if L1 passed)
l2_delegation = l1_client.delegate(
    l1_delegation.delegated_token,
    l2_approver_pubkey,
    allowed_actions=["final_approve_loan"]
)
```

## API Reference

### `invoke()` IAM Parameters

```python
def invoke(
    self,
    mcp: str,
    action: str,
    intent_token: IntentToken,
    params: Optional[Dict[str, Any]] = None,
    user_email: Optional[str] = None,
) -> MCPInvocationResult
```

**IAM Context Built From:**
- `user_email` parameter
- `intent_token.policy_validation.allowed_tools`
- `self.user_id` and `self.agent_id` from client
- `intent_token.raw_token` additional fields

### `delegate()` API

```python
def delegate(
    self,
    intent_token: IntentToken,
    delegate_public_key: str,
    validity_seconds: int = 3600,
    allowed_actions: Optional[List[str]] = None,
) -> DelegationResult
```

**Returns:**
```python
DelegationResult(
    delegation_id="DEL-abc123",
    delegated_token=IntentToken(...),
    delegate_public_key="a3b2c1d4...",
    expires_at=1735689600.0,
    status="delegated"
)
```

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [examples/loan_delegation_workflow.py](examples/loan_delegation_workflow.py) - Complete delegation example
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture details
- [API.md](API.md) - Full API reference
