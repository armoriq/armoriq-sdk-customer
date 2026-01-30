# ArmorIQ Concepts

Understanding the architecture, security model, and core concepts behind ArmorIQ SDK.

## Table of Contents

1. Architecture Overview  
2. Core Concepts  
3. Intent Plans  
4. Token Lifecycle  
5. Policy Management  
6. Agent Delegation  
7. Security Model  
8. CSRG (Canonical Structured Reasoning Graph)  
9. IAP Step Verification  
10. MCPs (Model Context Providers)  
11. Authentication Flow  
12. Common Patterns  
13. Performance Considerations  
14. Security Best Practices  
    

## **Architecture Overview**

ArmorIQ uses a **proxy-based architecture** where all agent requests flow through a secure verification layer before reaching MCP servers.

### **Components**

| Component | Purpose | Technology |
| ----- | ----- | ----- |
| **ArmorIQ SDK** | SDK helping agents connect to ArmorIQ services | Python 3.8+ |
| **ArmorIQ Proxy** | Security gateway and verifier | NestJS/TypeScript |
| **CSRG-IAP** | Token signing and plan canonicalization | FastAPI/Python |

## **Core Concepts**

### **1\. Intent-Based Execution**

Instead of directly calling services, you declare your **intent** (what you want to do) upfront. This intent becomes a cryptographically verified contract.

**The ArmorIQ Innovation: LLM \+ Cryptographic Security**

ArmorIQ bridges two worlds:

1. **AI Agents** that use LLMs to reason and plan dynamically  
2. **Zero-Trust Security** that cryptographically verifies every action

**Traditional Approach:**

```py
# Direct calls - no verification
api.call("service1", "action1")
api.call("service2", "action2")
api.call("service3", "action3")  # Could be malicious!
```

**ArmorIQ Approach:**

```py
# Step 1: Agent captures intent (LLM generates plan)
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch sales data and analyze Q4 performance"
)
# LLM decides: data-mcp/fetch_sales → analytics-mcp/analyze


# Step 2: Get cryptographic proof for the LLM-generated plan
token = client.get_intent_token(captured_plan)


# Step 3: Only declared actions can execute
client.invoke(
    mcp="data-mcp",
    action="fetch_sales",
    intent_token=token,
    params={...}
)   # ✓ Verified (in plan)

client.invoke(
    mcp="analytics-mcp",
    action="analyze",
    intent_token=token,
    params={...}
)  # ✓ Verified (in plan)

client.invoke(
    mcp="data-mcp",
    action="delete_all",
    intent_token=token,
    params={...}
)    # ✗ Fails - LLM didn't plan this!
```

### 

### **Key Insight:** Even though the LLM generated the plan dynamically, every action is ***cryptographically verified*****.** This prevents:

* ### Prompt injection attacks (malicious prompts can't execute unplanned actions)

* ### Agent drift (agent can't deviate from captured intent)

* ### Unauthorized escalation (even if compromised, agent is bound to the plan)

### **2\. Zero Trust Security**

ArmorIQ follows **zero trust** principles:

* Every action is verified cryptographically  
* Tokens are time-limited and non-reusable  
* Plans are immutable once signed  
* All requests are authenticated  
* Complete audit trail maintained

### **3\. Declarative Plans**

Plans are **declarative**, not imperative. More importantly, they're **LLM-generated**, not manually coded.

```py
# ✓ Agent captures intent from natural language
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch user data and calculate credit score"
)
# LLM generates declarative plan:
# [
#   {"action": "fetch_data", "mcp": "data-mcp"},
#   {"action": "calculate_score", "mcp": "analytics-mcp"}
# ]
```

**Why This Matters:**

* **LLM Autonomy**: Agent decides the best approach based on prompt  
* **Cryptographic Binding**: Even dynamic plans are immutably verified  
* **Declarative Security**: You secure what the agent wants, not how it does it  
* **No Implementation Details**: MCPs handle the how, plans declare the what

## **Intent Plans**

### **What is an Intent Plan?**

An **Intent Plan** is a structured document that declares all actions an agent intends to execute. Think of it as a "pre-approved checklist" that gets cryptographically signed.

### **LLM-Driven Plan Creation: capture\_plan() not specify\_plan()**

**Critical Design Philosophy:**

ArmorIQ is designed for **AI agents that use LLMs to generate plans dynamically**, not for statically-defined workflows. This is why the API is called capture\_plan(), you're **capturing the agent's intent** as the LLM generates it, not manually specifying every step.

**Traditional (Static) Approach:**

```
# ✗ Manual specification - not how ArmorIQ works
plan = {
    "steps": [
        {"action": "fetch_data", "mcp": "data-mcp"},
        {"action": "analyze", "mcp": "analytics-mcp"}
    ]
}
```

**ArmorIQ (Dynamic) Approach:**

```
# ✓ LLM generates the plan from natural language
captured_plan = client.capture_plan(
    llm="gpt-4",                                          # LLM generates the plan
    prompt="Analyze Q4 sales data and generate report"   # Natural language intent
)

# The LLM decides:
# - Which MCPs to use
# - Which actions to call
# - In what order
# - With what parameters
```

**Why capture\_plan() is Revolutionary:**

1. **Dynamic Reasoning**: Agent adapts plan based on context, user input, and environment  
2. **Natural Language**: Users express intent in plain English, not code  
3. **Agent Autonomy**: LLM chooses the best sequence of actions  
4. **Flexible Execution**: Different prompts → different plans → different execution paths

**Example: Same Task, Different Plans**

```
# Prompt 1: Simple request
plan1 = client.capture_plan(
    llm="gpt-4",
    prompt="Get sales data"
)
# LLM generates: [data-mcp/fetch_sales]

# Prompt 2: Complex request
plan2 = client.capture_plan(
    llm="gpt-4", 
    prompt="Get sales data, analyze trends, and email report to CFO"
)
# LLM generates: [data-mcp/fetch_sales, analytics-mcp/analyze_trends, 
#                 analytics-mcp/generate_report, email-mcp/send_email]
```

**When to Use Explicit Plans:**

While LLM-generated plans are the primary use case, you can provide explicit plan structures when:

* **Testing**: You want deterministic behavior for unit tests  
* **Templating**: You have reusable workflow templates  
* **Guardrails**: You want to constrain the LLM's options

```py
# Explicit plan (advanced use case)
template_plan = {
    "steps": [
        {"action": "fetch_user_data", "mcp": "data-mcp"},
        {"action": "calculate_risk_score", "mcp": "analytics-mcp"}
    ]
}

captured = client.capture_plan(
    llm="gpt-4",
    prompt="Risk assessment for user_123",
    plan=template_plan  # LLM still involved, but constrained
)
```

**The Power of capture\_plan():**

* **Intelligent**: LLM reasons about best execution path  
* **Secure**: Every action is cryptographically verified (even LLM-generated ones)  
* **Intent-Driven**: Capture *what* the agent wants, not *how* to do it  
* **Adaptive**: Plans change as context changes

This is why ArmorIQ is called **Intent-Based Access Protocol** – you're securing the ***intent*****,** not pre-scripting the execution.

### **Plan Structure**

```
{
    "steps": [
        {
            "action": str,         # Action name (e.g., "analyze")
            "mcp": str,            # MCP name (e.g., "analytics-mcp")
            "description": str,    # Optional human-readable description
            "metadata": dict       # Optional metadata
        }
    ],
    "metadata": {                  # Optional plan-level metadata
        "purpose": str,
        "version": str,
        "tags": list
    }
}
```

### **Example Plans**

**Simple Plan:**

```
plan = {
    "steps": [
        {"action": "ping", "mcp": "test-mcp"}
    ]
}
```

**Multi-Step Pipeline:**

```py
plan = {
    "steps": [
        {
            "action": "fetch_user_data",
            "mcp": "data-mcp",
            "description": "Get user profile from database"
        },
        {
            "action": "calculate_risk_score",
            "mcp": "analytics-mcp",
            "description": "Calculate credit risk"
        },
        {
            "action": "store_result",
            "mcp": "data-mcp",
            "description": "Save risk score to database"
        }
    ],
    "metadata": {
        "purpose": "user_risk_assessment",
        "version": "1.0"
    }
}
```

**Conditional Branches:**

```py
# Include all possible paths
plan = {
    "steps": [
        {"action": "check_user_type", "mcp": "data-mcp"},
        {"action": "process_premium", "mcp": "billing-mcp"},   # Path A
        {"action": "process_free", "mcp": "billing-mcp"}       # Path B
    ]
}

# At runtime, choose which path to execute
# Both are pre-approved, so either can run
```

### **Plan Canonicalization**

When you call \`get\_intent\_token()\` with your plan, the **CSRG-IAP** service converts your plan to **CSRG** (Canonical Structured Reasoning Graph) format:

```py
# Capture from prompt
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Analyze sales data and generate report"
)
# Or with explicit plan structure
captured = client.capture_plan(
    llm="gpt-4",
    prompt="Data analysis workflow",
    plan={"steps": [{"action": "analyze", "mcp": "analytics-mcp"}]}
)

# Captured plan (CSRG format)
{
    "graph": {
        "steps": [
            {
                "action": "analyze",
                "mcp": "analytics-mcp",
                "index": 0,
                "path": "/steps/[0]",
                "value_digest": "sha256:abc123..."
            }
        ],
        "metadata": {
            "canonical_version": "1.0",
            "created_at": "2026-01-21T10:30:00Z",
            "plan_hash": "sha256:def456..."
        }
    }
}
```

**Why Canonicalization?**

* Ensures consistent hashing (same plan \= same hash)  
* Enables Merkle tree construction  
* Provides deterministic verification  
* Prevents tampering

## **Token Lifecycle**

### **Token Flow**

```
1. Plan Creation
   ├─> Agent defines steps
   ├─> SDK validates plan structure
   └─> Returns PlanCapture object

2. Token Request
   ├─> SDK → POST /iap/sdk/token (ArmorIQ Backend)
   ├─> Backend validates API key (database)
   ├─> Backend → POST /intent (CSRG-IAP)
   ├─> CSRG-IAP canonicalizes plan to CSRG format
   ├─> CSRG-IAP calculates plan hash (SHA-256)
   ├─> CSRG-IAP creates Merkle tree from plan
   ├─> CSRG-IAP signs with Ed25519 private key
   └─> Returns token + step_proofs to SDK


3. Token Receipt
   ├─> Token includes: plan_hash, merkle_root, signature
   ├─> SDK stores token and Merkle tree
   └─> Ready for action execution

4. Action Execution
   ├─> For each step, SDK generates Merkle proof
   ├─> SDK → POST /invoke with CSRG headers
   │   ├─> X-CSRG-Path: /steps/[0]/action
   │   ├─> X-CSRG-Value-Digest: sha256:...
   │   └─> X-CSRG-Proof: [merkle proof array]
   ├─> Proxy verifies with IAP Step Verification
   ├─> If valid, routes to MCP server
   └─> MCP executes and returns result

5. Token Expiration
   └─> After expires_in seconds, token invalid
```

### 

### **Token  Internals**

A token is a **JWT (JSON Web Token)** signed with Ed25519:

**Header:**

```json
{
  "alg": "EdDSA",
  "typ": "JWT"
}
```

**Payload:**

```json

{
  "iss": "armoriq-csrg-iap",
  "sub": "user_001",
  "aud": "armoriq-proxy",
  "iat": 1737454200,
  "exp": 1737457800,
  "plan_hash": "sha256:abc123...",
  "merkle_root": "sha256:def456...",
  "policy": {
    "allow": ["*"],
    "deny": [],
    "allowed_tools": ["read_file", "analyze"],
    "rate_limit": 100,
    "ip_whitelist": []
  },
  "identity": {
    "user_id": "user_001",
    "agent_id": "my_agent",
    "api_key_id": "key_789"
  }
}
```

**Note:** The policy field is automatically encoded into the token when you call get\_intent\_token() with a policy parameter. Policies can be defined programmatically or created using the **ArmorIQ Visual Policy Builder** (see Policy Management below).

**Signature:**

```
Ed25519 signature over header.payload
```

### **Token Properties**

| Property | Description | Example |
| ----- | ----- | ----- |
| plan\_hash | SHA-256 hash of canonical plan | sha256:abc123... |
| merkle\_root | Root of Merkle tree from plan | sha256:def456... |
| iat | Issued at (Unix timestamp) | 1737454200 |
| exp | Expires at (Unix timestamp) | 1737457800 |
| identity | User/agent/key identification | {user\_id, agent\_id, ...} |
| policy | Access control policy (if specified) | {allow, deny, allowed\_tools...} |

## **Policy Management**

### **What are Policies?**

**Policies** define fine-grained access control for your agents and MCPs. They specify:

* Who can access which MCPs  
* What actions are allowed/denied  
* Which tools can be used  
* IP whitelisting  
* Time-based restrictions  
* Rate limiting

Policies are **automatically encoded into CSRG tokens** during get\_intent\_token() and cryptographically verified during execution.

### **Policy Structure**

```py
policy = {
    "allow": [                    # Allowed action patterns (glob)
        "analytics-mcp/*",        # All analytics-mcp actions
        "data-mcp/fetch_*",       # data-mcp fetch actions only
        "math-mcp/calculate"      # Specific action
    ],
    "deny": [                     # Denied action patterns
        "data-mcp/delete_*",      # Block all delete actions
        "admin-mcp/*"             # Block entire MCP
    ],
    "allowed_tools": [            # Tool whitelist
        "read_file",
        "write_file",
        "analyze_data"
    ],
    "rate_limit": 100,            # Requests per hour
    "ip_whitelist": [             # Allowed IP ranges
        "10.0.0.0/8",
        "192.168.1.100"
    ],
    "time_restrictions": {        # Time-based access
        "allowed_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17],  # 9 AM -5 PM
        "allowed_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    },
    "priority": 10                # Higher = higher priority
}
```

### **Creating Policies**

### **Method 1: Programmatic (SDK)**

```py
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(...)

# Define policy
policy = {
    "allow": ["analytics-mcp/*"],
    "deny": ["data-mcp/delete_*"],
    "allowed_tools": ["read_file", "analyze"],
    "rate_limit": 50
}

# Get token with policy
token_response = client.get_intent_token(
    plan=captured_plan,
    policy=policy,  # Policy encoded into CSRG token
    expires_in=3600
)

# Policy is now cryptographically bound to token
token = token_response["token"]
```

### **Method 2: Visual Policy Builder (ArmorIQ Canvas)**

The **ArmorIQ Canvas** is a visual drag-and-drop interface for creating policies without writing code:

**Access:** [https://armoriq.io/dashboard/policies](https://armoriq.io/dashboard/policies)

**Features:**

* Visual flow editor with drag-and-drop  
* Connect users/clients to MCPs and agents  
* Define permissions visually (read, create, update, delete)  
* Select allowed tools from MCP tool browser  
* Set IP whitelisting and time restrictions  
* Visual policy preview and validation  
* Export as JSON or use via API

**Workflow:**

1. **Open Canvas Builder**  
   * Navigate to Dashboard → Policies → "Canvas" button  
   * Empty canvas with toolbox on left  
2. **Add Entities to Canvas**  
   * Drag **User** nodes (organization members)  
   * Drag **Client** nodes (OAuth clients)  
   * Drag **MCP** nodes (MCP servers)  
   * Drag **Agent** nodes (AI agents)  
3. **Create Connections**  
   * Click on User/Client node output port  
   * Drag to MCP/Agent node input port  
   * Connection created with default policy  
4. **Configure Permissions**  
   * Click on connection edge  
   * Right panel opens with configuration:  
     * **Basic Tab:**  
       * Checkboxes for read/create/update/delete  
       * Path patterns (e.g., /api/users/\*)  
       * Quick tool selection  
     * **Advanced Tab:**  
       * IP whitelist (CIDR notation)  
       * Time restrictions (hours/days)  
       * Rate limiting  
       * Custom JSON policy editor  
5. **Browse MCP Tools**  
   * Click "Browse Tools" for any MCP connection  
   * Modal shows all available tools from MCP  
   * Select which tools to allow  
   * Tools automatically added to allowed\_tools array  
6. **Save Policy**  
   * Set policy name and description  
   * Choose priority level (0-100)  
   * Set status (draft/active/inactive)  
   * Click "Save Policy"  
   * Policy stored in database with unique ID  
7. **Use Policy in SDK**

```py
# Use policy by ID
token_response = client.get_intent_token(
    plan=plan,
    policy_id="f88cf4c7-732d-44ff-901b-fd3d882c2ecf"
)

# Or fetch policy JSON and use directly
policy = api.get_policy("f88cf4c7-732d-44ff-901b-fd3d882c2ecf")
token_response = client.get_intent_token(
    plan=plan,
    policy=policy["permissions"]
)
```

### **Policy CRUD API**

ArmorIQ provides a full REST API for policy management:

**Base URL:** [https://api.armoriq.io/dashborad/policies](https://api.armoriq.io/dashborad/policies)

**Authentication:** User JWT token (from OAuth2 login)

**Key Endpoints:**

```py
# Create policy
POST /policies
Body: {name, description, targetType, targetId, permissions, allowedTools, ...}

# List all policies
GET /policies

# Get specific policy
GET /policies/:policyId

# Update policy
PATCH /policies/:policyId
Body: {permissions, allowedTools, priority, ...}

# Delete policy
DELETE /policies/:policyId

# Activate/deactivate
POST /policies/:policyId/activate
POST /policies/:policyId/deactivate
```

**Example: Create Policy via API**

```py
import requests

response = requests.post(
    "https://api.armoriq.io/policies",
    headers={"Authorization": f"Bearer {user_jwt}"},
    json={
        "name": "Data Analyst Policy",
        "description": "Read and analyze data, no modifications",
        "targetType": "mcp_server",
        "targetId": "analytics-mcp-id",
        "allowedMemberIds": ["user-membership-id"],
        "permissions": {
            "read": ["/api/data/*", "/api/reports/*"],
            "create": [],
            "update": [],
            "delete": []
        },
        "allowedTools": ["read_file", "analyze", "aggregate"],
        "priority": 10,
        "status": "active"
    }
)

policy = response.json()["data"]
policy_id = policy["policyId"]
```

### **Policy Evaluation**

When an action is invoked, ArmorIQ evaluates policies in this order:

```
1. Extract policy from CSRG token payload
2. Check if action matches "deny" patterns
   └─> If match, REJECT (403 Forbidden)
3. Check if action matches "allow" patterns
   └─> If match, continue to next checks
   └─> If no match, REJECT (403 Forbidden)
4. Check tool name in allowed_tools
   └─> If not in list, REJECT (403 Forbidden)
5. Check rate limit
   └─> If exceeded, REJECT (429 Too Many Requests)
6. Check IP whitelist
   └─> If not in range, REJECT (403 Forbidden)
7. Check time restrictions
   └─> If outside allowed hours/days, REJECT (403 Forbidden)
8. All checks passed → ALLOW execution
```

**Priority Resolution:**

If a user has multiple policies (e.g., from multiple roles), the **highest priority** matching policy is used:

```
# User has 3 policies:
Policy A: priority=10, allow=["data-mcp/*"]
Policy B: priority=50, allow=["analytics-mcp/*"], deny=["analytics-mcp/delete_*"]
Policy C: priority=5,  allow=["*"]

# Action: "analytics-mcp/analyze"
# Evaluation: Policy B matches (highest priority) → ALLOWED

# Action: "analytics-mcp/delete_report"
# Evaluation: Policy B matches (highest priority) → DENIED
```

### **Policy in Token Lifecycle**

Policies integrate seamlessly into the CSRG token flow:

```
1. Agent creates plan
   └─> Steps defined

2. Agent requests token with policy
   └─> SDK → POST /token/issue {plan, policy}
   
3. ArmorIQ Backend receives request
   └─> Validates API key (database)
   └─> Extracts policy (or fetches by policy_id)
   
4. Backend forwards to CSRG-IAP
   └─> POST /intent {plan, policy, identity}
   
5. CSRG-IAP creates token
   ├─> Canonicalizes plan → CSRG format
   ├─> Generates Merkle tree
   ├─> Embeds policy in JWT payload ← **Policy encoded here**
   └─> Signs with Ed25519 → Token issued
   
6. Agent invokes action
   └─> SDK → POST /invoke {action, params}
   └─> Includes token with embedded policy
   
7. ArmorIQ Proxy verifies
   ├─> IAP Step Verification (Merkle proof)
   ├─> Policy Evaluation ← **Policy checked here**
   │   ├─> Check deny patterns
   │   ├─> Check allow patterns
   │   ├─> Check allowed_tools
   │   ├─> Check rate_limit
   │   ├─> Check ip_whitelist
   │   └─> Check time_restrictions
   └─> If all pass, route to MCP
   
8. MCP executes action
   └─> Returns result (no policy checks in MCP)
```

**Key Points:**

* Policy is **cryptographically bound** to token (can't be modified)  
* Policy checked **before** action execution (zero trust)  
* MCP servers don't need policy logic (enforced at proxy)  
* Visual canvas makes policy creation accessible to non-developers

### **Policy Best Practices**

**1\. Use Least Privilege:**

```
# ✓ Good - specific actions only
policy = {
    "allow": ["analytics-mcp/read_*", "analytics-mcp/analyze"],
    "deny": ["analytics-mcp/delete_*", "analytics-mcp/modify_*"]
}

# ✗ Bad - overly permissive
policy = {"allow": ["*"], "deny": []}
```

**2\. Layer Policies by Priority:**

```
# Base policy (low priority)
base_policy = {
    "priority": 10,
    "allow": ["data-mcp/read_*"],
    "rate_limit": 50
}

# Admin override (high priority)
admin_policy = {
    "priority": 90,
    "allow": ["*"],
    "rate_limit": 1000
}
```

**3\. Use Time Restrictions for Temporary Access:**

```
# Contractor access - weekdays only
contractor_policy = {
    "allow": ["data-mcp/read_*"],
    "time_restrictions": {
        "allowed_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17],
        "allowed_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    }
}
```

**4\. Combine CRUD and SDK Policies:**

```
# 1. Create base policy via CRUD API (persisted)
api.create_policy({
    "name": "Data Analyst Base",
    "permissions": {...},
    "status": "active"
})

# 2. Layer additional restrictions in SDK (runtime)
token = client.get_intent_token(
    plan_capture=plan,
    policy_id="base-policy-id",
    validity_seconds=3600,
    policy_overrides={  # Additional runtime restrictions
        "rate_limit": 20,  # More restrictive than base
        "ip_whitelist": ["192.168.1.100"]  # Add IP restriction
    }
)
```

## **Agent Delegation**

### **What is Agent Delegation?**

**Agent Delegation** allows a parent agent to grant temporary, cryptographically-secured authority to sub-agents (delegates) for executing specific subtasks. This enables hierarchical multi-agent workflows where specialized agents work independently with restricted permissions.

### **Why Delegation?**

**Traditional Multi-Agent Problem:**

```py
# ✗ Unsafe: Sub-agents share parent's full credentials
sub_agent.run(parent_api_key)  # Sub-agent has full access!

# ✗ Unsafe: Manual permission management
if sub_agent_type == "events":
    allowed = ["book_venue"]
elif sub_agent_type == "travel":
    allowed = ["book_flight"]
# Error-prone, not cryptographically enforced
```

**ArmorIQ Delegation Solution:**

```py
# ✓ Safe: Cryptographically restricted sub-token
delegated_token = parent.delegate(
    parent_token,
    delegate_public_key=sub_agent_pubkey,
    allowed_actions=["book_venue", "arrange_catering"],
    validity_seconds=1800  # Expires in 30 mins
)

# Sub-agent can ONLY execute allowed actions
# Even if compromised, cannot escalate privileges
```

### 

### **Delegation Architecture**

```
┌─────────────────────────────────────────────────────────┐
│  Parent Agent (Manager)                                           │
│  Token: Full permissions for company retreat                      │
└──────────────────┬──────────────────────────────────────┘
                      │
                      │ delegate(allowed_actions=["book_venue"])
                      ↓
    ┌──────────────────────────────────────────┐
    │  CSRG-IAP Delegation Service                    │
    │  POST /delegation/create                        │
    │  ─────────────────────────                  │
    │  1. Validate parent token                       │
    │  2. Create restricted token bound to            │
    │     delegate's public key                       │
    │  3. Sign with Ed25519                           │
    │  4. Return delegated token                      │
    └──────────────────┬───────────────────────┘
                          │
                          │ delegated_token (restricted)
                          ↓
        ┌──────────────────────────────────────┐
        │  Sub-Agent (Events Specialist)              │
        │  Token: Can only book_venue                 │
        │  Cannot: book_flight, delete_data           │
        └──────────────────────────────────────┘
```

### **Delegation Flow**

**Step 1: Parent Creates Plan**

```py
parent_client = ArmorIQClient(
    user_id="manager_001",
    agent_id="parent_agent"
)

parent_plan = parent_client.capture_plan(
    llm="gpt-4",
    prompt="Organize company retreat: venue, catering, transportation"
)

parent_token = parent_client.get_intent_token( 
plan_capture = parent_plan, 
validity_seconds=7200 
)
```

**Step 2: Generate Delegate Keypair**

```py
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Delegate generates its own keypair
delegate_private_key = ed25519.Ed25519PrivateKey.generate()
delegate_public_key = delegate_private_key.public_key()

# Convert to hex for delegation
pub_key_bytes = delegate_public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)
delegate_pubkey_hex = pub_key_bytes.hex()

# Delegate shares public key with parent (safe to share)
```

**Step 3: Parent Delegates Authority**

```py
delegation_result = parent_client.delegate(
    intent_token=parent_token,
    delegate_public_key=delegate_pubkey_hex,
    validity_seconds=1800,  # 30 minutes
    allowed_actions=["search_venues", "book_venue", "arrange_catering"],
    subtask={
        "goal": "Book venue and catering for 50 people",
        "budget": 5000,
        "date": "2026-04-15"
    }
)
delegated_token = delegation_result.delegated_token
```

**Step 4: Parent Sends Token to Delegate**

```py
# Parent sends delegated token to sub-agent
# (via secure channel, API, message queue, etc.)
send_to_delegate(delegation_result.delegated_token)
```

**Step 5: Delegate Uses Token**

```py
# Sub-agent (events specialist) uses delegated token
delegate_client = ArmorIQClient(
    user_id="events_specialist",
    agent_id="events_agent"
)

# Can execute allowed actions
result = delegate_client.invoke(
mcp="events-mcp", 
action="book_venue", 
intent_token=delegated_token, 
params={"venue_id": "v123", "date": "2026-04-15"}
)  # ✓ Success - action is allowed

# Cannot execute forbidden actions
result = delegate_client.invoke(
    "travel-mcp",
    "book_flight",
    delegated_token,
    {"destination": "Paris"}
)  # ✗ Fails - action not in allowed_actions
```

### 

### **Use Cases**

**1\. Hierarchical Workflows**

```py
# CEO → VP → Manager → Specialist
ceo_token = ceo_client.get_intent_token(master_plan)

vp_token = ceo_client.delegate(ceo_token, vp_pubkey, allowed_actions=["approve_budget"])
mgr_token = vp_client.delegate(vp_token, mgr_pubkey, allowed_actions=["assign_tasks"])
spec_token = mgr_client.delegate(mgr_token, spec_pubkey, allowed_actions=["execute_task"])
```

**2\. Parallel Specialization**

```py
# Parent delegates to multiple specialists in parallel
events_token = parent.delegate(parent_token, events_agent_pubkey, 
                                allowed_actions=["venue_*", "catering_*"])
travel_token = parent.delegate(parent_token, travel_agent_pubkey,
                                allowed_actions=["flight_*", "hotel_*"])
comms_token = parent.delegate(parent_token, comms_agent_pubkey,
                               allowed_actions=["email_*", "notify_*"])

# Each specialist works independently
```

**3\. Temporary Access**

```py
# Grant contractor temporary access
contractor_token = company_agent.delegate(
    company_token,
    contractor_pubkey,
    validity_seconds=3600,  # 1 hour only
    allowed_actions=["read_data", "analyze"]  # No write access
)
```

### 

### **Security Properties**

| Property | Description | Benefit |
| ----- | ----- | ----- |
| **Cryptographic Binding** | Delegated token bound to delegate's Ed25519 public key | Only delegate can use token |
| **Action Restriction** | allowed\_actions enforced by IAP | Principle of least privilege |
| **Time-Limited** | Delegated tokens expire faster than parent | Limits attack window |
| **Non-Transferable** | Delegate cannot re-delegate without permission | Prevents unauthorized chains |
| **Auditable** | Every delegation logged with delegation\_id | Full audit trail |
| **Revocable** | Parent token expiration invalidates all delegations | Clean revocation |

### **Delegation vs Policies**

| Feature | Delegation | Policies |
| ----- | ----- | ----- |
| **Purpose** | Agent-to-agent authority transfer | User/org-level access control |
| **Scope** | Per-token, temporary | Global, persistent |
| **Creation** | Runtime (delegate() call) | Pre-defined (CRUD API or Canvas) |
| **Use Case** | Multi-agent workflows | Enterprise governance |
| **Binding** | Ed25519 public key | User/agent/MCP patterns |

**Use Both Together:**

```
# Policy: Enterprise-wide restrictions
policy = {
    "allow": ["*"],
    "deny": ["data-mcp/delete_*"],  # No one can delete
    "rate_limit": 100
}

parent_token = parent_client.get_intent_token(plan, policy=policy)

# Delegation: Further restrict for sub-agent
delegated_token = parent_client.delegate(
    parent_token,
    delegate_pubkey,
    allowed_actions=["data-mcp/read_*"]  # Even more restricted
)
# Delegate inherits policy restrictions + delegation restrictions
```

## **Security Model**

### **Multi-Layer Security**

ArmorIQ provides defense-in-depth with multiple security layers:

```
Layer 1: API Key Authentication
   ├─> X-API-Key header required
   ├─> Format: ak_live_<64 hex chars>
   ├─> Validated with bcrypt
   └─> Associated with user/agent metadata

Layer 2: Plan Canonicalization
   ├─> Converts to CSRG format
   ├─> Calculates deterministic hash
   ├─> Prevents tampering
   └─> Enables verification

Layer 3: Cryptographic Signing
   ├─> Ed25519 signing (CSRG-IAP)
   ├─> 256-bit security strength
   ├─> Quantum-resistant candidate
   └─> Fast verification

Layer 4: Merkle Tree Verification
   ├─> Each action has proof path
   ├─> O(log n) verification time
   ├─> Proves action in plan
   └─> Prevents unauthorized actions

Layer 5: IAP Step Verification (Proxy)
   ├─> Verifies Merkle proof
   ├─> Checks CSRG path
   ├─> Validates value digest
   ├─> Confirms Ed25519 signature
   └─> Only then routes to MCP

Layer 6: Time-Based Expiration
   ├─> Tokens expire after expires_in
   ├─> Limits attack window
   └─> Requires fresh tokens
```

### **Cryptographic Guarantees**

**Integrity**: Plans cannot be modified after signing

* SHA-256 hashing ensures any change produces different hash  
* Ed25519 signature verifies plan hasn't been tampered with

**Authenticity**: Tokens are issued by trusted CSRG-IAP

* Only CSRG-IAP has private Ed25519 key  
* Proxy verifies signature with public key

**Authorization**: Only declared actions can execute

* Merkle proofs verify action was in original plan  
* Proxy rejects actions not in plan

**Non-repudiation**: Complete audit trail

* All actions logged with timestamps  
* Signed tokens prove authorization  
* Merkle proofs prove action was approved

## **CSRG (Canonical Structured Reasoning Graph)**

### **What is CSRG?**

CSRG is a **canonical representation format** for intent plans. It ensures that the same intent always produces the same hash, enabling reliable cryptographic verification.

### **Why Canonical?**

**Problem without canonicalization:**

```py
# These are semantically identical but hash differently
plan1 = {"steps": [{"action": "a", "mcp": "m"}]}
plan2 = {"steps": [{"mcp": "m", "action": "a"}]}  # Different key order

hash(plan1) != hash(plan2)  # Different hashes!
```

**Solution with CSRG:**

```
canonical1 = canonicalize(plan1)
canonical2 = canonicalize(plan2)

hash(canonical1) == hash(canonical2)  # Same hash!
```

### **CSRG Structure**

A CSRG graph includes:

1. **Canonical Steps**: Sorted, indexed, with deterministic paths  
2. **Value Digests**: SHA-256 hash of each step's action  
3. **Metadata**: Version, timestamps, plan hash  
4. **Merkle Tree**: Binary tree for O(log n) verification

### **CSRG Example**

**Input Plan:**

```json
{
    "steps": [
        {"action": "fetch", "mcp": "data-mcp"},
        {"action": "analyze", "mcp": "analytics-mcp"}
    ]
}
```

**CSRG Output:**

```json
{
    "graph": {
        "steps": [
            {
                "action": "fetch",
                "mcp": "data-mcp",
                "index": 0,
                "path": "/steps/[0]",
                "value_digest": "sha256:a1b2c3..."
            },
            {
                "action": "analyze",
                "mcp": "analytics-mcp",
                "index": 1,
                "path": "/steps/[1]",
                "value_digest": "sha256:d4e5f6..."
            }
        ],
        "metadata": {
            "canonical_version": "1.0",
            "plan_hash": "sha256:g7h8i9...",
            "created_at": "2026-01-21T10:30:00Z"
        },
        "merkle_tree": {
            "root": "sha256:j0k1l2...",
            "leaves": [
                "sha256:a1b2c3...",  # Step 0 action digest
                "sha256:d4e5f6..."   # Step 1 action digest
            ],
            "proofs": {
                "0": [{"sibling": "sha256:d4e5f6...", "position": "right"}],
                "1": [{"sibling": "sha256:a1b2c3...", "position": "left"}]
            }
        }
    }
}
```

### 

### 

### 

### **Merkle Tree Construction**

For a 4-step plan, the Merkle tree looks like:

```
                  Root: H(H01 || H23)
                  /                  \
          H01: H(H0 || H1)      H23: H(H2 || H3)
          /           \          /           \
      H0: hash     H1: hash  H2: hash    H3: hash
      (step 0)     (step 1)  (step 2)    (step 3)
```

To verify step 1:

* Provide: H1, sibling H0, parent sibling H23  
* Compute: H01 \= H(H0 || H1), Root \= H(H01 || H23)  
* Compare: Computed Root \== Token's merkle\_root

**Complexity**: O(log n) verification time for n steps

## **IAP Step Verification**

### **What is IAP?**

**IAP (Intent Authorization Protocol)** is ArmorIQ's cryptographic verification mechanism that ensures every action matches the signed plan.

### **How IAP Works**

When an agent invokes an action, the SDK sends **CSRG headers**:

```
POST /invoke HTTP/1.1
Host: proxy.armoriq.io
X-API-Key: ak_live_...
Authorization: Bearer <token>
X-CSRG-Path: /steps/[0]/action
X-CSRG-Value-Digest: sha256:abc123...
X-CSRG-Proof: [{"sibling": "sha256:def...", "position": "right"}]

{
  "mcp": "analytics-mcp",
  "action": "analyze",
  "params": {...}
}
```

### **CSRG Headers**

| Header | Purpose | Example |
| ----- | ----- | ----- |
| X-CSRG-Path | Location of action in plan | /steps/\[0\]/action |
| X-CSRG-Value-Digest | SHA-256 of action value | sha256:abc123... |
| X-CSRG-Proof | Merkle proof (JSON array) | \[{"sibling": "...", "position": "right"}\] |

### **Verification Process**

ArmorIQ Proxy performs these checks (in IAPVerificationService.verifyStep()):

```
Step 1: Extract token from request
   └─> Decode JWT, verify Ed25519 signature

Step 2: Validate CSRG Path
   └─> Check path format: /steps/[index]/action

Step 3: Verify Merkle Proof
   ├─> Start with value_digest (leaf)
   ├─> Hash with siblings in proof
   ├─> Compute root
   └─> Compare with token's merkle_root

Step 4: Check Value Digest
   └─> Hash action from request body
   └─> Compare with X-CSRG-Value-Digest

Step 5: Validate Token Expiration
   └─> Check current time < exp

Step 6: Check Policy (if present)
   └─> Ensure action allowed by policy

If ALL checks pass: Route to MCP
If ANY check fails: Return 403 Forbidden
```

### **Example Verification**

**Agent Request:**

```
client.invoke("analytics-mcp", "analyze", token, {"data": [1,2,3]})
```

**SDK Generates:**

```
X-CSRG-Path: /steps/[0]/action
X-CSRG-Value-Digest: sha256:hash_of("analyze")
X-CSRG-Proof: [merkle siblings to prove step 0]
```

**Proxy Verifies:**

1. ✓ Token signature valid (Ed25519)  
2. ✓ Path /steps/\[0\]/action exists in plan  
3. ✓ Merkle proof valid (step 0 was in plan)  
4. ✓ Value digest matches hash of "analyze"  
5. ✓ Token not expired  
6. ✓ Action allowed by policy

**Result:** Request routed to analytics-mcp

### **Security Benefits**

**Prevents Action Injection:**

```py
# Agent gets token for plan with ["fetch_data"]
token = get_token({"steps": [{"action": "fetch_data", ...}]})

# Attacker tries to execute different action
client.invoke("data-mcp", "delete_all", token, {})
# ✗ FAILS: "delete_all" not in Merkle tree, verification fails
```

**Prevents Plan Modification:**

```py
# Agent gets token for plan
plan = {"steps": [{"action": "fetch", ...}]}
token = get_token(plan)

# Agent tries to add more actions
plan["steps"].append({"action": "delete", ...})
client.invoke("data-mcp", "delete", token, {})
# ✗ FAILS: Token's merkle_root doesn't match modified plan
```

**Prevents Token Reuse:**

```py
# Token expires after 1 hour
token = get_token(plan, expires_in=3600)

# After 1 hour
client.invoke("data-mcp", "fetch", token, {})
# ✗ FAILS: Token expired (exp < current time)
```

## 

## **MCPs (Model Context Providers)**

### **What is an MCP?**

An **MCP (Model Context Provider)** is a service that executes specific actions for agents. Think of MCPs as microservices that agents can orchestrate.

### **MCP Architecture**

```
Agent → ArmorIQ Proxy → MCP Server

MCP Server:
├─> Receives POST requests
├─> Executes action logic
├─> Returns results
└─> NO token verification (proxy handles it)
```

**Important**: MCPs don't verify tokens. The ArmorIQ Proxy handles all verification before routing requests to MCPs.

### **Example MCPs**

#### **analytics-mcp**

**Purpose**: Data analysis and statistical operations

**Actions**:

* fetch\_data: Retrieve datasets  
* analyze: Calculate statistics (mean, median, std, etc.)  
* aggregate: Group and aggregate data  
* visualize: Generate charts (returns data for visualization)

**Example**:

```py
result = client.invoke(
    "analytics-mcp",
    "analyze",
    token,
    {
        "data": [10, 20, 30, 40, 50],
        "metrics": ["mean", "median", "std"]
    }
)
# Returns: {"mean": 30, "median": 30, "std": 14.14}
```

#### **data-mcp**

**Purpose**: Data transformation and storage

**Actions**:

* store: Save data to storage  
* retrieve: Get data from storage  
* transform: Apply transformations (filter, map, reduce)  
* validate: Check data against schema

**Example**:

```py
result = client.invoke(
    "data-mcp",
    "transform",
    token,
    {
        "data": [1, 2, 3, 4, 5],
        "operation": "filter",
        "condition": {"gt": 2}
    }
)
# Returns: {"data": [3, 4, 5]}
```

## **Authentication Flow**

### **Complete Authentication Sequence**

```
Step 1: API Key Creation
   └─> User creates API key at armoriq.io
   └─> Format: ak_live_<64 hex chars>
   └─> Stored hashed (bcrypt) in database
   └─> Associated with user_id, permissions

Step 2: SDK Initialization
   └─> Agent provides API key to SDK
   └─> SDK stores key for subsequent requests

Step 3: Token Request
   └─> SDK → POST /iap/sdk/token (ArmorIQ Backend)
       ├─> Header: X-API-Key: ak_live_...
       ├─> Body: {plan, policy, expires_in}
       └─> Backend validates API key (database)
   
Step 4: API Key Validation
   └─> Backend extracts X-API-Key header
   └─> Queries database for key metadata
   └─> Verifies key exists and is active
   └─> Extracts user_id, agent_id, permissions

Step 5: Identity Bundle Construction
   └─> Backend creates identity bundle:
       {
         "user_id": "user_001",
         "agent_id": "my_agent",
         "api_key_id": "key_789",
         "permissions": ["analytics", "data"]
       }

Step 6: CSRG-IAP Request
   └─> Backend → POST /intent (CSRG-IAP)
       {
         "identity": identity_bundle,
         "plan": canonical_plan,
         "policy": policy,
         "validity_seconds": expires_in
       }

Step 7: Token Signing
   └─> CSRG-IAP canonicalizes plan
   └─> Creates Merkle tree
   └─> Signs with Ed25519 private key
   └─> Returns signed token

Step 8: Token Return
   └─> Proxy → SDK: {token, plan_hash, merkle_root, expires_at}
   └─> SDK stores token and Merkle tree

Step 9: MCP Invocation
   └─> SDK → POST /invoke (ArmorIQ Proxy)
       ├─> Header: X-API-Key (for rate limiting)
       ├─> Header: Authorization: Bearer <token>
       ├─> Header: X-CSRG-Path
       ├─> Header: X-CSRG-Value-Digest
       ├─> Header: X-CSRG-Proof
       └─> Body: {mcp, action, params}

Step 10: IAP Step Verification
   └─> Proxy verifies (IAPVerificationService.verifyStep):
       1. Token signature (Ed25519)
       2. Merkle proof (action in plan)
       3. CSRG path validity
       4. Value digest match
       5. Token expiration
       6. Policy compliance

Step 11: MCP Routing
   └─> If verification passes:
       └─> Proxy → MCP: POST /execute {action, params}
       └─> MCP executes and returns result
       └─> Proxy → SDK: result

Step 12: Result Return
   └─> SDK returns result to agent
   └─> Agent continues with next step or completes
```

### **Security Properties**

* **API Key**: Authenticates user/agent identity  
* **Token**: Authorizes specific plan execution  
* **Merkle Proof**: Proves action was in plan  
* **Ed25519 Signature**: Proves token authenticity  
* **Expiration**: Limits attack window

## **Common Patterns**

### **Pattern 1: Long-Running Workflows**

For workflows that take longer than token expiration:

```py
def long_workflow():
    # Get fresh token for each phase
    
    # Phase 1: Data collection (1 hour)
    plan1 = {"steps": [{"action": "fetch_data", "mcp": "data-mcp"}]}
    token1 = client.get_intent_token(client.capture_plan(plan1), expires_in=3600)["token"]
    data = client.invoke("data-mcp", "fetch_data", token1, {...})
    
    # Phase 2: Analysis (1 hour)
    plan2 = {"steps": [{"action": "analyze", "mcp": "analytics-mcp"}]}
    token2 = client.get_intent_token(client.capture_plan(plan2), expires_in=3600)["token"]
    results = client.invoke("analytics-mcp", "analyze", token2, {"data": data})
    
    # Phase 3: Storage (1 hour)
    plan3 = {"steps": [{"action": "store", "mcp": "data-mcp"}]}
    token3 = client.get_intent_token(client.capture_plan(plan3), expires_in=3600)["token"]
    client.invoke("data-mcp", "store", token3, {"results": results})
```

### 

### **Pattern 2: Dynamic Plans**

When you don't know exact steps upfront:

```py
# Include all possible actions in plan
plan = {
    "steps": [
        {"action": "check_status", "mcp": "data-mcp"},
        {"action": "process_a", "mcp": "analytics-mcp"},
        {"action": "process_b", "mcp": "analytics-mcp"},
        {"action": "process_c", "mcp": "analytics-mcp"},
        {"action": "store", "mcp": "data-mcp"}
    ]
}

token = client.get_intent_token(client.capture_plan(plan))["token"]

# Decide at runtime which to execute
status = client.invoke("data-mcp", "check_status", token, {})

if status["type"] == "A":
    result = client.invoke("analytics-mcp", "process_a", token, {...})
elif status["type"] == "B":
    result = client.invoke("analytics-mcp", "process_b", token, {...})
else:
    result = client.invoke("analytics-mcp", "process_c", token, {...})

client.invoke("data-mcp", "store", token, {"result": result})
```

### **Pattern 3: Error Recovery**

Handle transient failures with retry:

```py
import time
from armoriq_sdk.exceptions import MCPError

def invoke_with_retry(client, mcp, action, token, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.invoke(mcp, action, token, params)
        except MCPError as e:
            if e.retriable and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retry {attempt + 1} after {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
# Usage
result = invoke_with_retry(
    client,
    "analytics-mcp",
    "analyze",
    token,
    {"data": [1, 2, 3]}
)
```

### **Pattern 4: Batch Processing**

Process multiple items efficiently:

```py
# Single token for all items
items = ["item1", "item2", "item3", "item4", "item5"]

plan = {
    "steps": [
        {"action": "process", "mcp": "data-mcp"}
        for _ in items  # One step per item
    ]
}

token = client.get_intent_token(client.capture_plan(plan))["token"]

# Process in parallel
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(
            client.invoke,
            "data-mcp",
            "process",
            token,
            {"item": item}
        )
        for item in items
    ]
    
    results = [f.result() for f in futures]
```

## **Performance Considerations**

### **Token Caching**

Reuse tokens for multiple actions:

```py
# ✗ Inefficient - new token for each action
for i in range(100):
    plan = {"steps": [{"action": "analyze", "mcp": "analytics-mcp"}]}
    token = client.get_intent_token(client.capture_plan(plan))["token"]
    client.invoke("analytics-mcp", "analyze", token, {})
# 100 token requests!

# ✓ Efficient - one token for all actions
plan = {
    "steps": [{"action": "analyze", "mcp": "analytics-mcp"} for _ in range(100)]
}
token = client.get_intent_token(client.capture_plan(plan))["token"]

for i in range(100):
    client.invoke("analytics-mcp", "analyze", token, {})
# 1 token request!
```

### **Connection Pooling**

Reuse SDK client instances:

```py
# ✗ Creates new connections each time
def bad_pattern():
    client = ArmorIQClient(api_key="...", user_id="...", agent_id="...")
    result = client.invoke(...)
    # Connection closed

for _ in range(100):
    bad_pattern()  # 100 connection setups!

# ✓ Reuse connections
client = ArmorIQClient(api_key="...", user_id="...", agent_id="...")

for _ in range(100):
    result = client.invoke(...)  # 1 connection!
```

### **Parallel Execution**

Execute independent actions concurrently:

```py
import concurrent.futures

# Sequential - slow
results = []
for mcp in ["analytics-mcp", "data-mcp", "math-mcp"]:
    result = client.invoke(mcp, "query", token, {})
    results.append(result)
# Total time: 3 * action_time

# Parallel - fast
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(client.invoke, mcp, "query", token, {})
        for mcp in ["analytics-mcp", "data-mcp", "math-mcp"]
    ]
    results = [f.result() for f in futures]
# Total time: max(action_times)
```

### **Plan Size Optimization**

Keep plans reasonable in size:

```py
# ✗ Huge plan - slow Merkle tree construction
plan = {
    "steps": [
        {"action": f"action_{i}", "mcp": "data-mcp"}
        for i in range(10000)  # 10,000 steps!
    ]
}
# Merkle tree depth: log2(10000) ≈ 13 levels
# Token size: large

# ✓ Break into chunks
chunk_size = 100
for chunk in range(0, 10000, chunk_size):
    plan = {
        "steps": [
            {"action": f"action_{i}", "mcp": "data-mcp"}
            for i in range(chunk, min(chunk + chunk_size, 10000))
        ]
    }
    token = client.get_intent_token(client.capture_plan(plan))["token"]
    # Process chunk
# Merkle tree depth: log2(100) ≈ 7 levels per chunk
```

## **Security Best Practices**

### **1\. API Key Management**

**Do:**

* Store in environment variables or secrets manager  
* Rotate keys periodically (every 90 days)  
* Use different keys for dev/staging/prod  
* Revoke compromised keys immediately

**Don't:**

* Hardcode in source code  
* Commit to version control  
* Share between teams/agents  
* Log API keys

### **2\. Token Expiration**

**Do:**

* Use short-lived tokens (1 hour default)  
* Request new tokens for long workflows  
* Handle expiration gracefully

**Don't:**

* Set very long expiration (24+ hours)  
* Reuse expired tokens  
* Share tokens between agents

### **3\. Plan Security**

**Do:**

* Validate all action parameters  
* Use explicit action names  
* Include only necessary actions  
* Document plan purpose

**Don't:**

* Include unused actions "just in case"  
* Use wildcard actions  
* Modify plans after getting tokens  
* Execute untrusted plan content

### **4\. Network Security**

**Do:**

* Use HTTPS for all requests (enforced)  
* Validate SSL certificates  
* Use VPN for sensitive environments  
* Monitor for anomalies

**Don't:**

* Disable SSL verification  
* Use HTTP proxies for API keys  
* Expose proxy URLs publicly

### **5\. Error Handling**

**Do:**

* Log errors without exposing secrets  
* Implement rate limiting on retries  
* Monitor failed verifications  
* Alert on suspicious patterns

**Don't:**

* Log full tokens or API keys  
* Retry indefinitely  
* Ignore verification failures  
* Suppress security errors

