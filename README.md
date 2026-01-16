# ArmorIQ SDK (Python)

**Intent-based Agent Development with CSRG-IAP Integration**

The ArmorIQ SDK provides a simple, powerful interface for building AI agents that use the Canonical Structured Reasoning Graph (CSRG) Intent Assurance Plane (IAP) for secure, auditable action execution.

## Architecture

```
┌─────────┐     capture_plan()      ┌──────────┐
│  Agent  │ ──────────────────────> │ IAP      │
│         │                          │ (CSRG)   │
└─────────┘                          └──────────┘
     │                                    │
     │ get_intent_token()                 │
     │ <──────────────────────────────────┘
     │
     │ invoke(mcp, action, token)
     ├──────────────────────> ┌──────────────┐
     │                         │ AIQ Proxy A  │──> MCP A
     │                         └──────────────┘
     │                                 │
     │                         verify_token(IAP)
     │
     └──────────────────────> ┌──────────────┐
                               │ AIQ Proxy B  │──> MCP B
                               └──────────────┘
```

## Features

✅ **Simple API** - 4 core methods: `capture_plan()`, `get_intent_token()`, `invoke()`, `delegate()`  
✅ **Intent Verification** - Every action verified against the original plan  
✅ **Multi-MCP Support** - Seamlessly route actions across multiple MCPs  
✅ **IAM Context Injection** - Automatic IAM context passing to MCP tools  
✅ **Public Key Delegation** - Ed25519-based secure delegation between agents  
✅ **Token Management** - Automatic token caching and refresh  
✅ **Type-Safe** - Full Pydantic models and type hints  
✅ **Async-First** - Built on modern async/await patterns  
✅ **Error Handling** - Clear exceptions for token and intent issues  

## Installation

```bash
pip install armoriq-sdk
```

For development:

```bash
# Clone the repo
git clone https://github.com/armoriq/armoriq-sdk-python
cd armoriq-sdk-python

# Install with uv
uv sync

# Or with pip
pip install -e ".[dev]"
```

## Configuration

### Production Endpoints (Default)

The SDK automatically connects to ArmorIQ production services:

- **IAP (Intent Assurance Plane)**: `https://iap.armoriq.io`
- **Proxy Server**: `https://cloud-run-proxy.armoriq.io`
- **ConMap API**: `https://api.armoriq.io`

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
AGENT_ID=your-agent-id
USER_ID=your-user-id

# Optional - Override production endpoints
# IAP_ENDPOINT=https://iap.armoriq.io
# PROXY_ENDPOINT=https://cloud-run-proxy.armoriq.io

# For local development
# ARMORIQ_ENV=development  # Uses localhost endpoints
```

### Local Development

For local testing with services running on localhost:

```bash
export ARMORIQ_ENV=development
export AGENT_ID=test-agent
export USER_ID=test-user
```

This automatically uses:
- IAP: `http://localhost:8082`
- Proxy: `http://localhost:3001`

## Quick Start

### Production Usage

```python
from armoriq_sdk import ArmorIQClient

# Production (uses default endpoints)
client = ArmorIQClient(
    user_id="user123",
    agent_id="my-agent"
)

# 1. Capture a plan from LLM output
plan = client.capture_plan(
    llm="gpt-4",
    prompt="Book a flight to Paris and reserve a hotel"
)

# 2. Get an intent token from IAP
token = client.get_intent_token(plan)

# 3. Execute actions through MCP proxies
try:
    result = client.invoke(
        mcp="travel-mcp",
        action="book_flight",
        intent_token=token,
        params={"destination": "CDG", "date": "2026-02-15"}
    )
    print(f"Flight booked: {result}")
    
except InvalidTokenException as e:
    print(f"Token validation failed: {e}")
```

## Core API

### `capture_plan(llm: str, prompt: str) -> Dict`

Captures an execution plan from an LLM response and converts it to canonical CSRG format.

**Parameters:**
- `llm`: LLM identifier (e.g., "gpt-4", "claude-3")
- `prompt`: User prompt or instruction

**Returns:** Canonical plan dictionary ready for token issuance

---

### `get_intent_token(plan: Dict) -> IntentToken`

Requests a signed intent token from the IAP for the given plan.

**Parameters:**
- `plan`: Canonical plan from `capture_plan()`

**Returns:** `IntentToken` object containing the signed token and metadata

---

### `invoke(mcp: str, action: str, intent_token: IntentToken, params: Dict = None, user_email: str = None) -> MCPInvocationResult`

Executes an MCP action through the ArmorIQ proxy with token verification and IAM context injection.

**Parameters:**
- `mcp`: MCP identifier (e.g., "travel-mcp", "finance-mcp")
- `action`: Action name to invoke (tool name)
- `intent_token`: Token from `get_intent_token()`
- `params`: Optional action parameters
- `user_email`: Optional user email (injected into IAM context)

**Returns:** `MCPInvocationResult` with action result and metadata

**Raises:**
- `InvalidTokenException`: Token signature/expiry invalid
- `IntentMismatchException`: Action not in original plan
- `MCPInvocationException`: MCP invocation failed

**IAM Context:** The SDK automatically injects `_iam_context` parameter with:
- `email`: User email
- `user_id`: User identifier  
- `agent_id`: Agent identifier
- `allowed_tools`: List of allowed tools from policy validation

---

### `delegate(intent_token: IntentToken, delegate_public_key: str, validity_seconds: int = 3600, allowed_actions: List[str] = None) -> DelegationResult`

Delegates authority to another agent using public key-based CSRG delegation.

**Parameters:**
- `intent_token`: Token to delegate
- `delegate_public_key`: Public key of delegate agent (Ed25519 hex format)
- `validity_seconds`: Delegation validity in seconds (default: 3600)
- `allowed_actions`: Optional list of allowed actions (defaults to all)

**Returns:** `DelegationResult` with delegated token and metadata

**Raises:**
- `DelegationException`: Delegation creation failed
- `InvalidTokenException`: Original token is invalid

**Example:**
```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate delegate keypair
delegate_private_key = ed25519.Ed25519PrivateKey.generate()
delegate_public_key = delegate_private_key.public_key()
pub_key_bytes = delegate_public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)
pub_key_hex = pub_key_bytes.hex()

# Create delegation
result = client.delegate(
    intent_token=token,
    delegate_public_key=pub_key_hex,
    validity_seconds=1800,
    allowed_actions=["approve_loan", "process_payment"]
)

# Delegate uses new token
delegate_agent = ArmorIQClient(...)
delegate_agent.invoke(
    "loan-mcp",
    "approve_loan",
    result.delegated_token,
    params={"loan_id": "L123"}
)
```

## Configuration

The SDK can be configured via constructor or environment variables:

```python
client = ArmorIQClient(
    iap_endpoint="https://iap.armoriq.example.com",  # or IAP_ENDPOINT env var
    proxy_endpoints={
        "travel-mcp": "https://proxy-a.armoriq.example.com",
        "finance-mcp": "https://proxy-b.armoriq.example.com"
    },
    user_id="user123",
    agent_id="my-agent",
    timeout=30.0,
    max_retries=3
)
```

## Examples

See the `examples/` directory for complete examples:

- `basic_agent.py` - Simple agent with plan capture and execution
- `multi_mcp_agent.py` - Agent coordinating multiple MCPs
- `delegation_example.py` - Agent-to-agent delegation
- `error_handling.py` - Comprehensive error handling patterns

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=armoriq_sdk

# Format code
uv run black armoriq_sdk tests

# Type checking
uv run mypy armoriq_sdk
```

## Architecture Details

The SDK integrates with three key components:

1. **CSRG-IAP** - Issues intent tokens after plan canonicalization
2. **ArmorIQ Proxy** - Verifies tokens and routes MCP calls
3. **MCPs** - Execute actual actions (travel, finance, etc.)

### Security Model

- Every plan is converted to a canonical hash (CSRG)
- Intent tokens are Ed25519-signed by IAP
- Proxies verify tokens before executing actions
- Actions are checked against Merkle proofs of the plan
- All operations are append-only audited

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://docs.armoriq.example.com
- Issues: https://github.com/armoriq/armoriq-sdk-python/issues
- Discord: https://discord.gg/armoriq
