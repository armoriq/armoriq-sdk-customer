# ArmorIQ SDK Architecture & Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER APPLICATION                             │
│                                                                      │
│  from armoriq_sdk import ArmorIQClient                              │
│                                                                      │
│  client = ArmorIQClient(...)                                        │
│  plan = client.capture_plan("gpt-4", "Book flight")                │
│  token = client.get_intent_token(plan)                             │
│  result = client.invoke("travel-mcp", "book_flight", token)        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ARMORIQ SDK (Python)                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │            ArmorIQClient (client.py)                  │          │
│  │                                                       │          │
│  │  • capture_plan()  ────────► CSRG Canonicalization  │          │
│  │  • get_intent_token() ─────► IAP Token Request      │          │
│  │  • invoke() ───────────────► Proxy Invocation       │          │
│  │  • delegate() ─────────────► IAP Delegation         │          │
│  │                                                       │          │
│  │  Token Cache | Error Handling | HTTP Client          │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │         Data Models (models.py)                       │          │
│  │  IntentToken | PlanCapture | MCPInvocation           │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │       Exceptions (exceptions.py)                      │          │
│  │  InvalidTokenException | IntentMismatchException      │          │
│  └──────────────────────────────────────────────────────┘          │
└────────┬───────────────────────┬──────────────────┬─────────────────┘
         │                       │                  │
         ▼                       ▼                  ▼
┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
│   CSRG-IAP      │   │  ArmorIQ Proxy   │   │  ArmorIQ Proxy  │
│   (Port 8000)   │   │    Server A      │   │    Server B     │
│                 │   │  (Port 3001)     │   │  (Port 3002)    │
│  • Token Issue  │   │                  │   │                 │
│  • Verification │   │  • Token Verify  │   │  • Token Verify │
│  • Delegation   │   │  • MCP Route     │   │  • MCP Route    │
│  • Audit Log    │   │                  │   │                 │
└─────────────────┘   └────────┬─────────┘   └────────┬────────┘
                               │                      │
                               ▼                      ▼
                      ┌─────────────────┐   ┌─────────────────┐
                      │   Travel MCP    │   │  Finance MCP    │
                      │                 │   │                 │
                      │ • book_flight   │   │ • get_balance   │
                      │ • book_hotel    │   │ • transfer      │
                      │ • cancel        │   │ • invest        │
                      └─────────────────┘   └─────────────────┘
```

## Data Flow Sequence

### 1. Plan Capture
```
User App → SDK.capture_plan(llm, prompt)
  └─► CSRG.canonicalize(plan)
      └─► Return: PlanCapture {
            plan_hash: "abc123...",
            merkle_root: "def456...",
            ordered_paths: [...]
          }
```

### 2. Token Acquisition
```
User App → SDK.get_intent_token(plan)
  └─► HTTP POST → IAP /intent
      └─► IAP: Validate + Sign
          └─► Return: IntentToken {
                token_id: "token_789",
                signature: "sig_xyz...",
                expires_at: timestamp
              }
```

### 3. Action Invocation
```
User App → SDK.invoke(mcp, action, token)
  └─► Check Token Expiry (local)
      └─► HTTP POST → Proxy /invoke {
            mcp: "travel-mcp",
            action: "book_flight",
            intent_token: {...},
            params: {...}
          }
          └─► Proxy: Verify Token with IAP
              └─► Proxy: Route to MCP
                  └─► MCP: Execute Action
                      └─► Return: MCPInvocationResult {
                            status: "success",
                            result: {...}
                          }
```

### 4. Agent Delegation
```
User App → SDK.delegate(target_agent, subtask, token)
  └─► HTTP POST → IAP /delegate
      └─► IAP: Create Trust Delta
          └─► IAP: Issue New Token
              └─► Return: DelegationResult {
                    new_token: {...},
                    trust_delta: {...}
                  }
```

## Error Handling Flow

```
SDK Method Call
  │
  ├─► Configuration Error? ─► ConfigurationException
  │
  ├─► Token Expired? ─────────► TokenExpiredException
  │
  ├─► HTTP Request
  │    │
  │    ├─► 401/403 ─────────► InvalidTokenException
  │    ├─► 409 ──────────────► IntentMismatchException
  │    ├─► 5xx ──────────────► MCPInvocationException
  │    └─► Network Error ────► MCPInvocationException
  │
  └─► Success ───────────────► Return Result
```

## Token Lifecycle

```
┌────────────────────────────────────────────────────┐
│  TOKEN LIFECYCLE                                   │
├────────────────────────────────────────────────────┤
│                                                    │
│  1. CREATION (IAP)                                 │
│     Plan Hash + Identity → Sign → Token           │
│     ↓                                              │
│  2. CACHING (SDK)                                  │
│     Store: plan_hash:validity → Token             │
│     ↓                                              │
│  3. USAGE (Multiple Times)                         │
│     ├─ Check Expiry (local)                       │
│     ├─ Verify Signature (proxy/IAP)               │
│     └─ Execute Action (MCP)                        │
│     ↓                                              │
│  4. EXPIRATION                                     │
│     expires_at < now → TokenExpiredException       │
│     ↓                                              │
│  5. REFRESH (if needed)                            │
│     New plan capture → New token                   │
│                                                    │
└────────────────────────────────────────────────────┘
```

## Security Boundaries

```
┌──────────────────────────────────────────────────┐
│ TRUST ZONES                                      │
├──────────────────────────────────────────────────┤
│                                                  │
│  Zone 1: User Application                       │
│  ├─ Has: SDK Client                             │
│  ├─ Can: Create plans, request tokens           │
│  └─ Cannot: Forge tokens, bypass verification   │
│                                                  │
│  ───────────── SDK BOUNDARY ──────────────       │
│                                                  │
│  Zone 2: ArmorIQ SDK                             │
│  ├─ Has: HTTP client, CSRG integration          │
│  ├─ Can: Cache tokens, validate expiry          │
│  └─ Cannot: Sign tokens, execute without token  │
│                                                  │
│  ───────────── NETWORK BOUNDARY ──────────       │
│                                                  │
│  Zone 3: IAP (Intent Assurance Plane)           │
│  ├─ Has: Signing keys, policy engine            │
│  ├─ Can: Issue tokens, verify signatures        │
│  └─ Authority: Central trust anchor             │
│                                                  │
│  Zone 4: Proxy Servers                           │
│  ├─ Has: Token verification logic               │
│  ├─ Can: Route to MCPs, enforce policy          │
│  └─ Must: Verify every token with IAP           │
│                                                  │
│  Zone 5: MCPs (Execution Layer)                  │
│  ├─ Has: Action implementations                 │
│  ├─ Can: Execute verified actions only          │
│  └─ Cannot: Access unverified requests          │
│                                                  │
└──────────────────────────────────────────────────┘
```

## File Organization

```
armoriq-sdk-python/
│
├── armoriq_sdk/              # Core SDK package
│   ├── __init__.py           # Package exports
│   ├── client.py             # ArmorIQClient (main API)
│   ├── models.py             # Pydantic models
│   └── exceptions.py         # Custom exceptions
│
├── examples/                 # Usage examples
│   ├── basic_agent.py        # Simple usage
│   ├── multi_mcp_agent.py    # Multi-service
│   ├── delegation_example.py # Agent delegation
│   ├── error_handling.py     # Error patterns
│   └── README.md             # Example guide
│
├── tests/                    # Test suite
│   ├── test_client.py        # Client tests
│   ├── test_models.py        # Model tests
│   ├── test_exceptions.py    # Exception tests
│   ├── conftest.py           # Pytest config
│   └── __init__.py           # Test package
│
├── docs/                     # Documentation
│   ├── README.md             # User guide
│   ├── QUICKSTART.md         # Quick start
│   ├── DEVELOPMENT.md        # Dev guide
│   ├── CHANGELOG.md          # Version history
│   └── PROJECT_SUMMARY.md    # Implementation summary
│
└── config/                   # Configuration
    ├── pyproject.toml        # Project config
    ├── .gitignore            # Git ignores
    ├── LICENSE               # MIT license
    └── setup.sh              # Setup script
```

## API Call Patterns

### Pattern 1: Simple Action
```python
client = ArmorIQClient(...)
plan = client.capture_plan("gpt-4", "Do X")
token = client.get_intent_token(plan)
result = client.invoke("mcp", "action", token)
```

### Pattern 2: Multi-Action Workflow
```python
client = ArmorIQClient(...)
plan = client.capture_plan("gpt-4", "Do X, Y, Z")
token = client.get_intent_token(plan)

result1 = client.invoke("mcp1", "action_x", token)
result2 = client.invoke("mcp2", "action_y", token)
result3 = client.invoke("mcp3", "action_z", token)
```

### Pattern 3: Delegation
```python
client = ArmorIQClient(...)
plan = client.capture_plan("gpt-4", "Parent task")
token = client.get_intent_token(plan)

# Delegate subtask
delegation = client.delegate(
    "child_agent",
    {"subtask": "Child task"},
    token
)

# Child agent uses new token
child_token = delegation.new_token
```

### Pattern 4: Error Recovery
```python
client = ArmorIQClient(...)

try:
    plan = client.capture_plan("gpt-4", "Task")
    token = client.get_intent_token(plan)
    result = client.invoke("mcp", "action", token)
    
except TokenExpiredException:
    # Re-acquire token
    token = client.get_intent_token(plan)
    result = client.invoke("mcp", "action", token)
    
except IntentMismatchException:
    # Capture new plan
    plan = client.capture_plan("gpt-4", "Updated task")
    token = client.get_intent_token(plan)
    result = client.invoke("mcp", "action", token)
```

## Performance Characteristics

- **Plan Capture**: O(n) where n = plan nodes
- **Token Acquisition**: ~100-200ms (network + IAP)
- **Token Caching**: O(1) lookup
- **Action Invocation**: ~50-100ms (network + proxy + MCP)
- **Delegation**: ~150-250ms (network + IAP)

## Scalability

- **Concurrent Clients**: Limited by IAP capacity
- **Token Reuse**: Single token for multiple actions
- **Caching**: Reduces IAP load
- **Horizontal Scaling**: Multiple proxy instances
- **MCP Distribution**: MCPs can scale independently
