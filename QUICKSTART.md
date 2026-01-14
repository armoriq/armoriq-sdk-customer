# ArmorIQ Python SDK - Quick Start Guide

## 🎯 Overview

The ArmorIQ Python SDK provides a simple, powerful interface for building AI agents with Intent Assurance Plane (IAP) integration. It handles plan canonicalization, intent token management, and secure MCP action invocation.

## 📦 Installation

### From PyPI (when published)
```bash
pip install armoriq-sdk
```

### From Source (Development)
```bash
git clone https://github.com/armoriq/armoriq-sdk-python
cd armoriq-sdk-python
./setup.sh
```

## 🚀 5-Minute Quick Start

### 1. Start Required Services

Terminal 1 - Start CSRG-IAP:
```bash
cd csrg-iap
uv run python -m csrg_iap.main
```

Terminal 2 - Start ArmorIQ Proxy:
```bash
cd armoriq-proxy-server
npm run start:dev
```

### 2. Write Your First Agent

Create `my_agent.py`:

```python
from armoriq_sdk import ArmorIQClient

# Initialize SDK
client = ArmorIQClient(
    iap_endpoint="http://localhost:8000",
    proxy_endpoints={
        "travel-mcp": "http://localhost:3001"
    },
    user_id="my_user",
    agent_id="my_agent"
)

# Capture a plan
plan = client.capture_plan(
    llm="gpt-4",
    prompt="Book a flight to Paris"
)

# Get intent token
token = client.get_intent_token(plan)

# Execute action
result = client.invoke(
    mcp="travel-mcp",
    action="book_flight",
    intent_token=token,
    params={"destination": "CDG"}
)

print(f"Success! {result}")
client.close()
```

### 3. Run Your Agent

```bash
python my_agent.py
```

## 🎓 Core Concepts

### Intent Flow

```
1. CAPTURE PLAN
   ↓
2. GET TOKEN (from IAP)
   ↓
3. INVOKE ACTION (through Proxy)
   ↓
4. VERIFY TOKEN (automatic)
   ↓
5. EXECUTE (on MCP)
```

### Key Components

- **IAP (Intent Assurance Plane)**: Issues and verifies intent tokens
- **Proxy**: Routes MCP requests with token verification
- **MCP (Model Context Protocol)**: Executes actual actions
- **SDK**: Simplifies the entire flow

## 📚 Common Patterns

### Pattern 1: Multi-Step Workflow

```python
# Single token, multiple actions
plan = client.capture_plan("gpt-4", "Book trip: flight + hotel")
token = client.get_intent_token(plan)

# Execute coordinated steps
flight = client.invoke("travel-mcp", "book_flight", token)
hotel = client.invoke("travel-mcp", "book_hotel", token)
```

### Pattern 2: Error Handling

```python
from armoriq_sdk import InvalidTokenException, IntentMismatchException

try:
    result = client.invoke("mcp", "action", token)
except InvalidTokenException as e:
    print(f"Token invalid: {e}")
except IntentMismatchException as e:
    print(f"Action not in plan: {e}")
```

### Pattern 3: Agent Delegation

```python
# Delegate subtask to another agent
delegation = client.delegate(
    target_agent="payment_agent",
    subtask={"action": "process_payment"},
    intent_token=token
)

# Child agent gets new token
child_token = delegation.new_token
```

### Pattern 4: Configuration from Environment

```bash
export IAP_ENDPOINT=http://localhost:8000
export USER_ID=my_user
export AGENT_ID=my_agent
```

```python
# No need to pass params - reads from env
client = ArmorIQClient()
```

## 🔍 API Reference

### ArmorIQClient

```python
client = ArmorIQClient(
    iap_endpoint: str,           # IAP service URL
    proxy_endpoints: Dict[str, str],  # MCP proxy URLs
    user_id: str,                # User identifier
    agent_id: str,               # Agent identifier
    timeout: float = 30.0,       # Request timeout
    max_retries: int = 3         # Retry attempts
)
```

### capture_plan()

```python
plan = client.capture_plan(
    llm: str,                    # LLM identifier
    prompt: str,                 # User prompt
    plan: Optional[Dict] = None, # Pre-generated plan
    metadata: Optional[Dict] = None
) -> PlanCapture
```

### get_intent_token()

```python
token = client.get_intent_token(
    plan_capture: PlanCapture,
    policy: Optional[Dict] = None,
    validity_seconds: float = 60.0
) -> IntentToken
```

### invoke()

```python
result = client.invoke(
    mcp: str,                    # MCP identifier
    action: str,                 # Action name
    intent_token: IntentToken,   # Token from get_intent_token()
    params: Optional[Dict] = None
) -> MCPInvocationResult
```

### delegate()

```python
delegation = client.delegate(
    target_agent: str,
    subtask: Dict,
    intent_token: IntentToken,
    trust_policy: Optional[Dict] = None
) -> DelegationResult
```

## 🛡️ Security Features

✅ **Plan Canonicalization**: CSRG ensures deterministic plan hashing  
✅ **Token Signing**: Ed25519 signatures from IAP  
✅ **Token Verification**: Automatic verification by proxies  
✅ **Intent Matching**: Actions verified against original plan  
✅ **Audit Trail**: All operations logged and auditable  
✅ **Token Expiry**: Time-bound token validity  

## 🐛 Troubleshooting

### "Connection refused" Error

**Problem**: Can't connect to IAP or Proxy

**Solution**:
```bash
# Check if services are running
curl http://localhost:8000/health  # IAP
curl http://localhost:3001/health  # Proxy

# Start services if needed
cd csrg-iap && uv run python -m csrg_iap.main
cd armoriq-proxy-server && npm run start:dev
```

### "InvalidTokenException" Error

**Problem**: Token validation failed

**Solutions**:
- Check token hasn't expired
- Verify IAP endpoint is correct
- Ensure user_id and agent_id are valid

### "IntentMismatchException" Error

**Problem**: Action not in original plan

**Solution**:
- Capture a new plan that includes the action
- Check action name matches plan exactly

### Import Errors

**Problem**: Can't import armoriq_sdk

**Solution**:
```bash
cd armoriq-sdk-python
uv sync
```

## 📖 Next Steps

1. **Run Examples**: `uv run python examples/basic_agent.py`
2. **Read Full Docs**: See `README.md` for complete documentation
3. **Development**: Check `DEVELOPMENT.md` for contribution guidelines
4. **Architecture**: Review `../Architecture.pdf` for system design

## 🤝 Support

- **Documentation**: [docs.armoriq.example.com](https://docs.armoriq.example.com)
- **Issues**: [GitHub Issues](https://github.com/armoriq/armoriq-sdk-python/issues)
- **Discord**: [discord.gg/armoriq](https://discord.gg/armoriq)

## 📄 License

MIT License - see LICENSE file
