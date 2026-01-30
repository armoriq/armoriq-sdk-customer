# **ArmorIQ SDK \- API Reference**

## **Table of Contents**

1. Installation  
2. Client Initialization  
3. Core Methods  
4. Data Models  
5. MCP Directory  
6. Error Handling  
7. Advanced Usage  
8. Configuration  
9. Troubleshooting  
10. Best Practices

## **Installation**

### **Requirements**

* Python 3.8 or higher  
* pip 20.0 or higher  
* HTTPS-capable network connection

### **Install from PyPI**

```
pip install armoriq-sdk
```

### **Install with Development Dependencies**

```
pip install armoriq-sdk[dev]
```

### **Verify Installation**

```py
import armoriq_sdk
print(armoriq_sdk.__version__)  # Should print: 1.0.0
```

## **Client Initialization**

### **ArmorIQClient**

The main entry point for interacting with ArmorIQ.

```py
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(
    api_key: str = None,
    user_id: str = None,
    agent_id: str = None,
    proxy_url: str = None,
    timeout: int = 30,
    max_retries: int = 3,
    verify_ssl: bool = True
)
```

#### **Parameters**

| Parameter | Type | Required | Default | Description |
| ----- | ----- | ----- | ----- | ----- |
| api\_key | str | Yes | ARMORIQ\_API\_KEY env var | Your API key (format: ak\_live\_\<64 hex\>) |
| user\_id | str | Yes | ARMORIQ\_USER\_ID env var | User identifier for tracking |
| agent\_id | str | Yes | ARMORIQ\_AGENT\_ID env var | Unique agent identifier |
| proxy\_url | str | No | https://proxy.armoriq.io | ArmorIQ Proxy base URL |
| timeout | int | No | 30 | Request timeout in seconds |
| max\_retries | int | No | 3 | Max retry attempts for failed requests |
| verify\_ssl | bool | No | True | Verify SSL certificates |

#### **Returns**

ArmorIQClient instance

#### **Raises**

* ValueError: If required parameters are missing  
* InvalidAPIKeyError: If API key format is invalid

#### **Example**

```py
import os
from armoriq_sdk import ArmorIQClient

# Using environment variables (recommended)
client = ArmorIQClient()

# Explicit parameters
client = ArmorIQClient(
    api_key="ak_live_" + "a" * 64,
    user_id="user_12345",
    agent_id="analytics_bot_v1",
    proxy_url="https://proxy.armoriq.io",
    timeout=60
)

# Custom configuration
client = ArmorIQClient(
    api_key=os.getenv("ARMORIQ_API_KEY"),
    user_id=get_current_user_id(),
    agent_id=f"agent_{uuid.uuid4()}",
    max_retries=5
)
```

## **Core Methods**

### **capture\_plan()**

**Design Philosophy:** It **captures the agent's intent** as an LLM generates the plan dynamically from natural language. This is the foundation of ArmorIQ's intent-based security model.

Captures an execution plan from a prompt. The plan structure contains the steps the agent intends to execute.

```py
client.capture_plan(
    llm: str,
    prompt: str,
    plan: dict = None,
    metadata: dict = None
) -> PlanCapture
```

**Primary Use Case: LLM-Generated Plans**

```
# ✓ Recommended: Let LLM generate the plan
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch user data, calculate risk score, and store result"
)
# LLM autonomously decides which MCPs and actions to use
```

**Advanced Use Case: Constrained Plans**

```
# When you need explicit control (testing, templating, guardrails)
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Execute predefined workflow",
    plan={"steps": [...]}  # Optional: Provide structure
)
```

#### **Parameters**

| Parameter | Type | Required | Description |
| ----- | ----- | ----- | ----- |
| llm | str | Yes | LLM identifier (e.g., "gpt-4", "claude-3", "gpt-3.5-turbo") |
| prompt | str | Yes | Natural language description of what to do |
| plan | dict | No | Optional pre-defined plan structure (if omitted, LLM generates it) |
| metadata | dict | No | Optional metadata to attach to plan |

**Plan Structure (if providing explicit plan):**

```json
{
    "steps": [
        {
            "action": str,         # Action name (required)
            "mcp": str,            # MCP name (required)
            "description": str,    # Human-readable description (optional)
            "metadata": dict       # Additional metadata (optional)
        }
    ],
    "metadata": dict               # Plan-level metadata (optional)
}
```

#### **Returns**

PlanCapture object containing:

```py
{
    "plan": dict,                  # Original or LLM-generated plan
    "llm": str,                    # LLM used
    "prompt": str,                 # Original prompt
    "metadata": dict               # Attached metadata
}
```

#### **Raises**

* InvalidPlanError: If plan structure is invalid  
* ValueError: If required fields are missing  
* CSRGException: If CSRG canonicalization fails

#### 

#### **Examples**

**Method 1: Prompt-based (LLM generates plan)**

```py
# Let LLM generate the plan structure
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch user data from database and calculate risk score"
)

print(f"Generated {len(captured.plan['steps'])} steps")
print(f"Plan: {captured.plan}")
```

**Method 2: Explicit plan structure**

```py
# Provide exact plan structure
explicit_plan = {
    "steps": [
        {"action": "fetch_data", "mcp": "data-mcp"},
        {"action": "analyze", "mcp": "analytics-mcp"}
    ]
}
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Analyze data",  # Still required for context
    plan=explicit_plan      # Use this exact structure
)

print(f"Steps: {len(captured.plan['steps'])}")
```

**Method 3: Plan with metadata**

```py
# Include metadata for tracking
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Calculate credit risk for loan application",
    plan={
        "steps": [
            {
                "action": "calculate_risk",
                "mcp": "analytics-mcp",
                "description": "Calculate credit risk score",
                "metadata": {"priority": "high"}
            }
        ]
    },
    metadata={
        "purpose": "credit_assessment",
        "version": "1.2.0",
        "tags": ["finance", "risk"]
    }
)

print(f"Metadata: {captured.metadata}")
```

**What happens during capture\_plan()?**

1. SDK receives prompt and optional plan structure  
2. If no plan provided, LLM generates it (or uses a template in current version)  
3. Plan structure is validated and stored  
4. Returns PlanCapture object with plan steps

### **get\_intent\_token()**

Requests a cryptographically signed token from ArmorIQ for executing your plan.

```py
client.get_intent_token(
    plan_capture: PlanCapture,
    policy: dict = None,
    validity_seconds: float = 60.0
) -> IntentToken
```

#### **Parameters**

| Parameter | Type | Required | Default | Description |
| ----- | ----- | ----- | ----- | ----- |
| plan\_capture | PlanCapture | Yes | \- | Captured plan from capture\_plan() |
| policy | dict | No | {"allow": \["\*"\], "deny": \[\]} | Authorization policy (see Policy Structure below) |
| validity\_seconds | float | No | None | Token validity in seconds |

**Policy Structure:**

```json
{
    "allow": list[str],            # Allowed actions (glob patterns, e.g., "analytics-mcp/*")
    "deny": list[str],             # Denied actions (glob patterns, e.g., "data-mcp/delete_*")
    "allowed_tools": list[str],    # Whitelisted tool names (optional)
    "rate_limit": int,             # Requests per hour (optional)
    "ip_whitelist": list[str],     # Allowed IPs/CIDR ranges (optional)
    "time_restrictions": {         # Time-based access (optional)
        "allowed_hours": list[int],    # 0-23 (e.g., [9, 10, 11, ..., 17] for 9 AM - 5 PM)
        "allowed_days": list[str]      # ["Monday", "Tuesday", ...]
    },
    "priority": int                # Policy priority 0-100 (higher = more important)
}
```

**Creating Policies:**

Policies can be defined programmatically (in SDK) or visually (ArmorIQ Canvas):

**Method 1: Programmatic (SDK)**

```py
policy = {
    "allow": ["analytics-mcp/*", "data-mcp/fetch_*"],
    "deny": ["data-mcp/delete_*"],
    "allowed_tools": ["read_file", "analyze", "aggregate"],
    "rate_limit": 100,
    "ip_whitelist": ["10.0.0.0/8"],
    "time_restrictions": {
        "allowed_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17],
        "allowed_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    }
}

token = client.get_intent_token(
    plan_capture=plan,
    policy=policy,
    validity_seconds=3600
)
```

**Method 2: Visual Policy Builder (ArmorIQ Canvas)**

Use the drag-and-drop interface at [https://armoriq.io/dashboard/policies:](https://armoriq.io/dashboard/policies:)

1. Click "Canvas" button to open visual builder  
2. Drag users, MCPs, and agents onto canvas  
3. Connect entities with edges (connections)  
4. Click edge to configure permissions visually  
5. Use "Browse Tools" to select allowed tools from MCP  
6. Set IP restrictions, time windows, rate limits  
7. Save policy with name and priority  
8. Use policy ID in SDK:

```py
# Use policy created in Canvas
token = client.get_intent_token(
    plan_capture=plan,
    policy_id="f88cf4c7-732d-44ff-901b-fd3d882c2ecf",  # From Canvas
    validity_seconds=3600
)

# Or fetch policy JSON from API and use directly
import requests
policy_response = requests.get(
   f"https://api.armoriq.io/policies/f88cf4c7-732d-44ff-901b-fd3d882c2ecf",
   headers={"Authorization": f"Bearer {user_jwt}"}
)
policy = policy_response.json()["data"]["permissions"]

token = client.get_intent_token(
    plan_capture=plan,
    policy=policy,
    validity_seconds=3600
)
```

**Policy Encoding:**

The policy is **automatically encoded into the CSRG token JWT payload** and cryptographically verified during execution. The proxy enforces policy rules before routing requests to MCPs.

#### **Flow**

1. SDK → ArmorIQ Backend \`POST /iap/sdk/token’ with X-API-Key   
2. Backend validates API key (database lookup) and builds identity bundle   
3. Backend → CSRG-IAP \`POST /intent\` with plan  
4. CSRG-IAP converts plan to Merkle tree structure  
5. CSRG-IAP calculates SHA-256 hash from canonical representation  
6. CSRG-IAP signs token with Ed25519  
7. Token with hash, merkle\_root, and step\_proofs returned to SDK via backend.

#### **Returns**

dict containing:

```json
{
    "success": bool,               # Always True if no exception
    "token": str,                  # JWT token string
    "plan_hash": str,              # SHA-256 of plan
    "merkle_root": str,            # Merkle tree root
    "expires_at": int,             # Unix timestamp
    "issued_at": int               # Unix timestamp
}
```

#### **Raises**

* AuthenticationError: If API key is invalid  
* TokenIssuanceError: If token creation fails  
* NetworkError: If proxy is unreachable

#### **Example**

```py
# Basic usage - LLM generates plan
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Analyze the dataset"
)
token_response = client.get_intent_token(plan)
token = token_response["token"]

# Custom expiration
token_response = client.get_intent_token(
    plan= captured_plan,
    expires_in=7200  # 2 hours
)

# With policy
token_response = client.get_intent_token(
    plan= captured_plan,
    policy={
        "allow": ["analytics-mcp/*", "data-mcp/fetch_*"],
        "deny": ["data-mcp/delete_*"]
    },
    expires_in=1800  # 30 minutes
)

# Check expiration
import time
if time.time() < token_response["expires_at"]:
    print("Token is valid")
else:
    print("Token expired, get new one")
```

### **invoke()**

Executes an action on an MCP server with cryptographic verification.

```py
client.invoke(
    mcp: str,
    action: str,
    intent_token: IntentToken,
    params: dict = None,
    merkle_proof: list = None,
    user_email: str = None
) -> MCPInvocationResult
```

### **Parameters**

| Parameter | Type | Required | Default | Description |
| ----- | ----- | ----- | ----- | ----- |
| mcp | str | Yes | \- | MCP server name (e.g., "analytics-mcp") |
| action | str | Yes | \- | Action/tool to execute (must be in plan) |
| intent\_token | IntentToken | Yes | \- | Token from get\_intent\_token() |
| params | dict | No | {} | Action parameters |
| merkle\_proof | list | No | Auto-generated | Optional Merkle proof |
| user\_email | str | No | None | Optional user email |

#### **Flow**

1. SDK generates Merkle proof for this action from plan  
2. SDK → ArmorIQ Proxy POST /invoke with CSRG headers:  
   * X-API-Key: API key for authentication  
   * X-CSRG-Path: Path in plan (e.g., /steps/\[0\]/action)  
   * X-CSRG-Value-Digest: SHA256 hash of action value  
   * X-CSRG-Proof: JSON Merkle proof array  
3. Proxy performs IAP Step Verification:  
   * Validates Merkle proof against plan\_hash  
   * Verifies CSRG path matches plan structure  
   * Checks value digest matches action  
   * Verifies Ed25519 signature on token  
4. If verification passes, proxy routes to MCP server  
5. MCP executes action and returns result

#### **Returns**

dict containing:

```py
{
    "success": bool,               # Whether action succeeded
    "data": any,                   # Response data from MCP
    "error": str,                  # Error message (if failed)
    "execution_time_ms": int,      # Execution duration
    "mcp": str,                    # MCP that executed
    "action": str                  # Action that ran
}
```

#### **Raises**

* VerificationError: If IAP Step Verification fails  
* TokenExpiredError: If token has expired  
* MCPError: If MCP execution fails  
* NetworkError: If request fails

#### **Example**

```
# Basic invocation
result = client.invoke(
    mcp_name="analytics-mcp",
    action="analyze",
    token=token,
    params={"data": [1, 2, 3, 4, 5], "metrics": ["mean", "std"]}
)

if result["success"]:
    print(f"Results: {result['data']}")
    print(f"Took: {result['execution_time_ms']}ms")
else:
    print(f"Error: {result['error']}")

# With error handling
try:
    result = client.invoke("data-mcp", "fetch_data", token, {"source": "db"})
    
    if result["success"]:
        data = result["data"]
    else:
        logger.error(f"MCP error: {result['error']}")
        
except TokenExpiredError:
    # Get fresh token
    token = client.get_intent_token(plan)["token"]
    result = client.invoke("data-mcp", "fetch_data", token, {"source": "db"})
    
except VerificationError as e:
    # Action not in plan
    logger.error(f"Verification failed: {e}")
    # Need to recreate plan with correct actions

# Custom timeout
result = client.invoke(
    "analytics-mcp",
    "long_analysis",
    token,
    {"dataset": "large"},
    timeout=120  # 2 minutes
)
```

### **delegate()**

Delegate authority to another agent using cryptographic token delegation. This allows an agent to grant temporary, restricted access to a sub-agent for executing specific subtasks.

```py
client.delegate(
    intent_token: IntentToken,
    delegate_public_key: str,
    validity_seconds: int = 3600,
    allowed_actions: list = None,
    subtask: dict = None
) -> DelegationResult
```

#### **Parameters**

| Parameter | Type | Required | Default | Description |
| ----- | ----- | ----- | ----- | ----- |
| intent\_token | IntentToken | Yes | \- | Parent agent's intent token to delegate |
| delegate\_public\_key | str | Yes | \- | Ed25519 public key of delegate agent (hex format) |
| validity\_seconds | int | No | 3600 | Delegation token validity in seconds |
| allowed\_actions | list | No | None | List of allowed actions (defaults to all from parent token) |
| subtask | dict | No | None | Optional subtask plan structure |

#### **Returns**

DelegationResult containing:

```
{
    "delegation_id": str,          # Unique delegation identifier
    "delegated_token": IntentToken, # New token for delegate agent
    "delegate_public_key": str,    # Public key of delegate
    "expires_at": float,           # Unix timestamp of expiration
    "trust_delta": dict,           # Trust update applied
    "status": str                  # Delegation status
}
```

#### **Raises**

* DelegationException: If delegation creation fails  
* InvalidTokenException: If parent token is invalid or expired  
* AuthenticationError: If IAP endpoint is unreachable

#### **Flow**

1. Parent agent creates main plan and gets token  
2. Parent calls delegate() with delegate's public key  
3. SDK → CSRG-IAP POST /delegation/create  
4. IAP creates new token with:  
   * Restricted permissions (if allowed\_actions specified)  
   * Delegate's public key bound cryptographically  
   * Shorter validity period  
5. Delegated token returned to parent  
6. Parent sends delegated token to sub-agent  
7. Sub-agent uses delegated token for authorized actions only

#### **Example**

**Basic Delegation:**

```
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate keypair for delegate agent
delegate_private_key = ed25519.Ed25519PrivateKey.generate()
delegate_public_key = delegate_private_key.public_key()

# Convert public key to hex format
pub_key_bytes = delegate_public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)
pub_key_hex = pub_key_bytes.hex()

# Delegate authority
delegation_result = client.delegate(
    intent_token=parent_token,
    delegate_public_key=pub_key_hex,
    validity_seconds=1800,  # 30 minutes
    allowed_actions=["book_venue", "arrange_catering"]
)

print(f"✅ Delegation created: {delegation_result.delegation_id}")
print(f"Delegated token: {delegation_result.delegated_token.token_id}")

# Send delegated token to sub-agent
sub_agent_client.invoke(
    "events-mcp",
    "book_venue",
    delegation_result.delegated_token,
    {"venue_id": "v123", "date": "2026-04-15"}
)
```

**Multi-Agent Workflow:**

```
# Parent agent: Company retreat organizer
parent_plan = parent_client.capture_plan(
    llm="gpt-4",
    prompt="Organize company retreat: venue, catering, transportation"
)
parent_token = parent_client.get_intent_token(parent_plan)

# Delegate to events specialist
events_delegation = parent_client.delegate(
    parent_token,
    delegate_public_key=events_agent_pubkey,
    allowed_actions=["search_venues", "book_venue", "arrange_catering"],
    subtask={
        "goal": "Book venue and catering for 50 people",
        "budget": 5000
    }
)

# Delegate to travel specialist  
travel_delegation = parent_client.delegate(
    parent_token,
    delegate_public_key=travel_agent_pubkey,
    allowed_actions=["quote_bus_rental", "book_bus"],
    subtask={
        "goal": "Arrange transportation for 50 people",
        "budget": 2000
    }
)

# Sub-agents work independently with restricted tokens
# Events agent can only book venues/catering
# Travel agent can only arrange transportation
```

**Delegation Chain (Hierarchical):**

```py
# Level 1: Manager delegates to Team Lead
lead_delegation = manager_client.delegate(
    manager_token,
    delegate_public_key=team_lead_pubkey,
    validity_seconds=7200
)

# Level 2: Team Lead delegates to Specialist
specialist_delegation = team_lead_client.delegate(
    lead_delegation.delegated_token,  # Use delegated token
    delegate_public_key=specialist_pubkey,
    validity_seconds=3600,
    allowed_actions=["execute_subtask"]  # Further restricted
)
```

#### **Security Properties**

* **Cryptographically Bound**: Delegation is signed with IAP's Ed25519 key  
* **Non-transferable**: Delegate cannot re-delegate without explicit permission  
* **Time-Limited**: Delegated tokens expire faster than parent tokens  
* **Action-Restricted**: Delegate can only execute allowed actions  
* **Auditable**: All delegations logged with delegation\_id and trust\_delta  
* **Revocable**: Parent token expiration invalidates all delegations

## **Data Models**

### **IntentPlan**

Returned by capture\_plan().

```json
{
    "canonical_plan": {
        "graph": {
            "steps": [
                {
                    "action": str,
                    "mcp": str,
                    "index": int,
                    "path": str,
                    "value_digest": str
                }
            ],
            "metadata": {
                "canonical_version": str,
                "plan_hash": str,
                "created_at": str
            }
        }
    },
    "plan_hash": str,
    "merkle_tree": {
        "root": str,
        "leaves": list[str],
        "proofs": dict
    },
    "created_at": str
}
```

### **IntentToken**

Returned by get\_intent\_token().

```json
{
    "success": bool,
    "token": str,                  # JWT format: header.payload.signature
    "plan_hash": str,              # SHA-256: "sha256:abc123..."
    "merkle_root": str,            # SHA-256: "sha256:def456..."
    "expires_at": int,             # Unix timestamp
    "issued_at": int               # Unix timestamp
}
```

**Token JWT Payload:**

```json
{
    "iss": "armoriq-csrg-iap",
    "sub": "user_001",
    "aud": "armoriq-proxy",
    "iat": 1737454200,
    "exp": 1737457800,
    "plan_hash": "sha256:...",
    "merkle_root": "sha256:...",
    "policy": {"allow": ["*"], "deny": []},
    "identity": {
        "user_id": "user_001",
        "agent_id": "my_agent",
        "api_key_id": "key_789"
    }
}
```

### **MCPResult**

Returned by invoke().

```
{
    "success": bool,
    "data": any,                   # MCP-specific response
    "error": str,                  # Present if success=False
    "execution_time_ms": int,
    "mcp": str,
    "action": str
}
```

## 

## **MCP Directory**

### **Eg: analytics-mcp**

Statistical analysis and data science operations.

#### **Actions**

##### **fetch\_data**

Retrieve datasets for analysis.

**Parameters:**

```
{
    "dataset": str,                # Dataset identifier (required)
    "filters": dict,               # Optional filters
    "limit": int                   # Max records (default: 1000)
}
```

**Returns:**

```
{
    "data": list[dict],            # Array of records
    "count": int,                  # Number of records
    "dataset": str                 # Dataset name
}
```

**Example:**

```
result = client.invoke("analytics-mcp", "fetch_data", token, {
    "dataset": "sales_2024",
    "filters": {"region": "US", "status": "completed"},
    "limit": 500
})

data = result["data"]["data"]
print(f"Fetched {result['data']['count']} records")
```

##### **analyze**

Calculate statistical metrics.

**Parameters:**

```
{
    "data": list[float],           # Numeric data (required)
    "metrics": list[str]           # Metrics to calculate (required)
}
```

**Supported Metrics:**

* mean: Average value  
* median: Middle value  
* std: Standard deviation  
* var: Variance  
* min: Minimum value  
* max: Maximum value  
* sum: Total sum  
* count: Number of values

**Returns:**

```
{
    "metrics": dict,               # Metric name → value
    "data_points": int             # Number of data points
}
```

**Example:**

```
result = client.invoke("analytics-mcp", "analyze", token, {
    "data": [10, 20, 30, 40, 50],
    "metrics": ["mean", "median", "std", "min", "max"]
})

metrics = result["data"]["metrics"]
print(f"Mean: {metrics['mean']}")
print(f"Std: {metrics['std']}")
```

##### **aggregate**

Group and aggregate data.

**Parameters:**

```
{
    "data": list[dict],            # Records to aggregate (required)
    "group_by": str,               # Field to group by (required)
    "aggregations": dict           # Field → function mapping (required)
}
```

**Aggregation Functions:**

* sum: Sum values  
* avg: Average values  
* count: Count records  
* min: Minimum value  
* max: Maximum value

**Returns:**

```
{
    "groups": list[dict],          # Grouped results
    "total_groups": int            # Number of groups
}
```

**Example:**

```
result = client.invoke("analytics-mcp", "aggregate", token, {
    "data": [
        {"region": "US", "sales": 100},
        {"region": "US", "sales": 150},
        {"region": "EU", "sales": 200}
    ],
    "group_by": "region",
    "aggregations": {
        "sales": "sum",
        "region": "count"
    }
})

for group in result["data"]["groups"]:
    print(f"{group['region']}: {group['sales_sum']} total sales")
```

## **Error Handling**

### **Exception Hierarchy**

```
ArmorIQError (base)
├── AuthenticationError
│   ├── InvalidAPIKeyError
│   └── APIKeyExpiredError
├── TokenError
│   ├── TokenExpiredError
│   ├── TokenInvalidError
│   └── TokenIssuanceError
├── VerificationError
│   ├── MerkleProofError
│   └── SignatureError
├── MCPError
│   ├── MCPNotFoundError
│   ├── ActionNotFoundError
│   └── InvalidParametersError
├── NetworkError
│   ├── ConnectionError
│   └── TimeoutError
└── ValidationError
```

### **Catching  Exceptions**

```py
from armoriq_sdk.exceptions import (
    ArmorIQError,
    AuthenticationError,
    TokenExpiredError,
    VerificationError,
    MCPError,
    NetworkError
)

try:
    captured_plan = client.capture_plan(
        llm="gpt-4",
        prompt="Analyze the data",
        plan=plan_dict  # Optional: provide structure
    )
    token_response = client.get_intent_token(captured_plan)
    result = client.invoke("analytics-mcp", "analyze", token_response["token"], params)
    
except AuthenticationError as e:
    # API key invalid or expired
    logger.error(f"Authentication failed: {e}")
    # Refresh API key
    
except TokenExpiredError as e:
    # Token expired, get new one
    logger.warning(f"Token expired: {e}")
    token_response = client.get_intent_token(capture_plan)
    result = client.invoke("analytics-mcp", "analyze", token_response["token"], params)
    
except VerificationError as e:
    # Action not in plan or verification failed
    logger.error(f"Verification failed: {e}")
    # Recreate plan with correct actions
    
except MCPError as e:
    # MCP execution failed
    logger.error(f"MCP error: {e.message}")
    # Handle MCP-specific error
    
except NetworkError as e:
    # Network issues
    logger.error(f"Network error: {e}")
    # Retry or use fallback
    
except ArmorIQError as e:
    # Catch-all for any ArmorIQ error
    logger.error(f"ArmorIQ error: {e}")
    
except Exception as e:
    # Unexpected error
    logger.exception(f"Unexpected error: {e}")
```

### **Error Response Format**

When invoke() returns success: False:

```json
{
    "success": False,
    "error": str,                  # Human-readable error message
    "error_code": str,             # Machine-readable error code
    "details": dict,               # Additional error context
    "mcp": str,                    # Which MCP failed
    "action": str                  # Which action failed
}
```

**Error Codes:**

* AUTH\_INVALID\_KEY: Invalid API key  
* AUTH\_EXPIRED\_KEY: API key expired  
* TOKEN\_EXPIRED: Token expired  
* TOKEN\_INVALID: Token signature invalid  
* VERIFICATION\_FAILED: IAP verification failed  
* MERKLE\_PROOF\_INVALID: Merkle proof validation failed  
* MCP\_NOT\_FOUND: MCP server not found  
* ACTION\_NOT\_FOUND: Action not available  
* INVALID\_PARAMS: Invalid parameters  
* NETWORK\_ERROR: Network connection failed  
* TIMEOUT: Request timed out  
* RATE\_LIMIT: Rate limit exceeded

## **Advanced Usage**

### **Custom Retry Logic**

```py
import time
from armoriq_sdk.exceptions import NetworkError, TokenExpiredError

def invoke_with_custom_retry(client, mcp, action, token, params, prompt):
    max_retries = 5
    base_delay = 1 
    for attempt in range(max_retries):
        try:
            return client.invoke(mcp, action, token, params)
            
        except TokenExpiredError:
            # Token expired, get new one
            captured_plan = client.capture_plan(
                llm="gpt-4",
                prompt=prompt  # e.g., "Execute analysis action"
            )
            token = client.get_intent_token(captured_plan)["token"]
            continue
            
        except NetworkError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                jitter = random.uniform(0, 0.1 * delay)  # Add jitter
                time.sleep(delay + jitter)
                continue
            raise 
    raise Exception("Max retries exceeded")
```

### **Connection Pooling**

```py
from armoriq_sdk import ArmorIQClient
import threading

class ArmorIQClientPool:
    def __init__(self, api_key, user_id, agent_id, pool_size=5):
        self.pool = [
            ArmorIQClient(api_key=api_key, user_id=user_id, agent_id=agent_id)
            for _ in range(pool_size)
        ]
        self.lock = threading.Lock()
        self.available = list(self.pool)
    
    def get_client(self):
        with self.lock:
            if self.available:
                return self.available.pop()
            else:
                # Pool exhausted, create new client
                return ArmorIQClient(...)
    
    def return_client(self, client):
        with self.lock:
            self.available.append(client)

# Usage
pool = ArmorIQClientPool(api_key="...", user_id="...", agent_id="...", pool_size=10)

def process_task(task):
    client = pool.get_client()
    try:
        # Use client
        result = client.invoke(...)
        return result
    finally:
        pool.return_client(client)
```

### 

### **Token Caching**

```py
import time
from typing import Dict, Tuple

class TokenCache:
    def __init__(self):
        self.cache: Dict[str, Tuple[str, int]] = {}  
    def get(self, plan_hash: str) -> str:
        if plan_hash in self.cache:
            token, expires_at = self.cache[plan_hash]
            # Return token if valid for at least 60 more seconds
            if time.time() < expires_at - 60:
                return token
        return None
    
    def set(self, plan_hash: str, token: str, expires_at: int):
        self.cache[plan_hash] = (token, expires_at)
    
    def clear_expired(self):
        now = time.time()
        self.cache = {
            k: v for k, v in self.cache.items()
            if v[1] > now
        }
# Usage
token_cache = TokenCache()

def get_token_cached(client, llm, prompt):
    captured = client.capture_plan(llm=llm, prompt=prompt)
    plan_hash = captured.plan_hash

    # Try cache first
    token = token_cache.get(plan_hash)
    if token:
        return token
    
    # Get new token
    response = client.get_intent_token(captured)
    token_cache.set(plan_hash, response["token"], response["expires_at"])
    
    return response["token"]
```

### **Batch Invocation**

```py
import concurrent.futures

def batch_invoke(client, mcp, action, token, params_list, max_workers=10):
    """
    Invoke same action with multiple parameter sets in parallel.
    
    Args:
        client: ArmorIQClient instance
        mcp: MCP name
        action: Action name
        token: Intent token
        params_list: List of parameter dicts
        max_workers: Max concurrent workers
    
    Returns:
        List of results in same order as params_list
    """
    def invoke_one(params):
        try:
            return client.invoke(mcp, action, token, params)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(invoke_one, params) for params in params_list]
        return [f.result() for f in futures]

# Usage
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Analyze multiple datasets in parallel"
)
token = client.get_intent_token(captured_plan)["token"]

params_list = [
    {"data": [1, 2, 3], "metrics": ["mean"]},
    {"data": [4, 5, 6], "metrics": ["median"]},
    {"data": [7, 8, 9], "metrics": ["std"]},
    # ... 100 total
]

results = batch_invoke(client, "analytics-mcp", "analyze", token, params_list)
```

## **Configuration**

### **Environment Variables**

```
# Required
export ARMORIQ_API_KEY="ak_live_<64_hex_chars>"
export ARMORIQ_USER_ID="user_12345"
export ARMORIQ_AGENT_ID="my_agent_v1"

# Optional
export ARMORIQ_PROXY_URL="https://proxy.armoriq.io"
export ARMORIQ_TIMEOUT="30"
export ARMORIQ_MAX_RETRIES="3"
export ARMORIQ_VERIFY_SSL="true"
export ARMORIQ_LOG_LEVEL="INFO"
```

### **Configuration File**

Create armoriq.yaml:

```
api_key: ${ARMORIQ_API_KEY}
user_id: user_12345
agent_id: my_agent_v1

proxy:
  url: https://proxy.armoriq.io
  timeout: 30
  max_retries: 3
  verify_ssl: true

logging:
  level: INFO
  format: json
  file: armoriq.log
```

**Load configuration:**

```py
import yaml
from armoriq_sdk import ArmorIQClient

with open("armoriq.yaml") as f:
    config = yaml.safe_load(f)

client = ArmorIQClient(
    api_key=config["api_key"],
    user_id=config["user_id"],
    agent_id=config["agent_id"],
    proxy_url=config["proxy"]["url"],
    timeout=config["proxy"]["timeout"],
    max_retries=config["proxy"]["max_retries"]
)
```

### **Logging Configuration**

```py
import logging

# Configure SDK logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get SDK logger
logger = logging.getLogger("armoriq_sdk")
logger.setLevel(logging.DEBUG)

# Add file handler
handler = logging.FileHandler("armoriq.log")
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)

# Now SDK operations will be logged
client = ArmorIQClient(...)
```

## **Troubleshooting**

### **Debug Mode**

Enable debug mode for detailed logging:

```
import logging
logging.basicConfig(level=logging.DEBUG)

from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(...)
client.debug = True  # Enable debug mode

# Now you'll see detailed request/response logs
```

### **Common Issues**

#### Issue: "Invalid API key format"

**Cause:** API key doesn't match expected format

**Solution:**

```
api_key = os.getenv("ARMORIQ_API_KEY")

# Validate format
assert api_key.startswith("ak_live_"), "API key must start with ak_live_"
assert len(api_key) == 72, f"API key must be 72 chars, got {len(api_key)}"
assert all(c in "0123456789abcdef" for c in api_key[8:]), "API key must be hex"
```

#### **Issue: "Step verification failed"**

**Cause:** Action not in original plan or Merkle proof invalid

**Solution:**

```py
# Ensure action is in the plan generated by LLM
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch data and analyze it"  # LLM will include both actions
)
token = client.get_intent_token(captured)["token"]

# This will work - action matches plan
result = client.invoke("data-mcp", "fetch_data", token, {})

# This will fail - action not in plan
result = client.invoke("data-mcp", "delete_data", token, {})  # ✗
```

#### **Issue: "Connection refused"**

**Cause:** ArmorIQ Proxy not reachable

**Solution:**

```py
# Test connectivity
import requests

proxy_url = "https://proxy.armoriq.io"

try:
    response = requests.get(f"{proxy_url}/health", timeout=5)
    if response.status_code == 200:
        print("Proxy reachable")
    else:
        print(f"Proxy returned {response.status_code}")
except requests.exceptions.ConnectionError:
    print("Cannot connect to proxy - check URL and network")
except requests.exceptions.Timeout:
    print("Connection timed out - check firewall")
```

#### **Issue: "Token expired"**

**Cause:** Token validity period elapsed

**Solution:**

```py
import time

def invoke_with_auto_refresh(client, llm, prompt, mcp, action, params):
    captured = client.capture_plan(llm=llm, prompt=prompt)
    token_response = client.get_intent_token(captured)
    token = token_response["token"]
    expires_at = token_response["expires_at"]
    
    # Check if token expired
    if time.time() >= expires_at:
        # Get fresh token
        token_response = client.get_intent_token(captured)
        token = token_response["token"]
    
    return client.invoke(mcp, action, token, params)
```

### **Performance Profiling**

```py
import time
from contextlib import contextmanager

@contextmanager
def profile(operation_name):
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        print(f"{operation_name}: {duration:.3f}s")

# Profile operations
with profile("capture_plan"):
    captured = client.capture_plan(llm="gpt-4", prompt="Analyze data")

with profile("get_token"):
    token_response = client.get_intent_token(captured)

with profile("invoke"):
    result = client.invoke("analytics-mcp", "analyze", token, params)
```

## **Best Practices**

### **1\. Client Lifecycle Management**

```
# ✓ Good - Singleton pattern
class AgentService:
    _client = None
    
    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = ArmorIQClient(...)
        return cls._client

# ✗ Bad - Creating clients repeatedly
def process_request():
    client = ArmorIQClient(...)  # New client every call!
    ...
```

### **2\. Plan Reusability**

```py
# ✓ Good - Cache common prompts for workflows
WORKFLOW_PROMPTS = {
    "user_analysis": "Fetch user data and analyze their behavior patterns",
    "data_pipeline": "Load data, transform it, and run analytics"
}

def run_workflow(workflow_name):
    prompt = WORKFLOW_PROMPTS[workflow_name]
    captured = client.capture_plan(llm="gpt-4", prompt=prompt)
    ...
```

### **3\. Error Recovery**

```py
# ✓ Good - Graceful degradation
def invoke_with_fallback(client, mcp, action, token, params, fallback_value=None):
    try:
        result = client.invoke(mcp, action, token, params)
        if result["success"]:
            return result["data"]
        else:
            logger.warning(f"MCP failed: {result['error']}")
            return fallback_value
    except Exception as e:
        logger.error(f"Invoke failed: {e}")
        return fallback_value
# Usage
data = invoke_with_fallback(
    client, "data-mcp", "fetch", token, {},
    fallback_value=[]  # Empty list if fails
)
```

### **4\. Monitoring and Metrics**

```
import time
from dataclasses import dataclass
from typing import List

@dataclass
class InvokeMetric:
    mcp: str
    action: str
    success: bool
    duration_ms: float
    timestamp: float

class MetricsCollector:
    def __init__(self):
        self.metrics: List[InvokeMetric] = []
    
    def record(self, mcp, action, success, duration_ms):
        self.metrics.append(InvokeMetric(
            mcp=mcp,
            action=action,
            success=success,
            duration_ms=duration_ms,
            timestamp=time.time()
        ))
    
    def get_stats(self):
        if not self.metrics:
            return {}
        
        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        avg_duration = sum(m.duration_ms for m in self.metrics) / total
        
        return {
            "total_invocations": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total,
            "avg_duration_ms": avg_duration
        }

# Usage
metrics = MetricsCollector()

start = time.time()
result = client.invoke(mcp, action, token, params)
duration_ms = (time.time() - start) * 1000

metrics.record(mcp, action, result["success"], duration_ms)

# Later
print(metrics.get_stats())
```

### **5\. Testing**

```
import unittest
from unittest.mock import Mock, patch

class TestAgent(unittest.TestCase):
    def setUp(self):
        self.client = ArmorIQClient(
            api_key="ak_live_" + "a" * 64,
            user_id="test_user",
            agent_id="test_agent"
        )
    
    @patch('armoriq_sdk.client.ArmorIQClient.invoke')
    def test_successful_invocation(self, mock_invoke):
        # Mock successful response
        mock_invoke.return_value = {
            "success": True,
            "data": {"result": 42},
            "execution_time_ms": 100
        }
        
        result = self.client.invoke("math-mcp", "calculate", "token", {})
        
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["result"], 42)
    
    @patch('armoriq_sdk.client.ArmorIQClient.get_intent_token')
    def test_token_expiration_handling(self, mock_get_token):
        # First call returns expired token
        # Second call returns fresh token
        mock_get_token.side_effect = [
            {"token": "expired_token", "expires_at": 0},
            {"token": "fresh_token", "expires_at": 9999999999}
        ]
        
        # Test auto-refresh logic
        ...
```

