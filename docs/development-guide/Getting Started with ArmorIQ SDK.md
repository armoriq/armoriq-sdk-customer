# **Getting Started with ArmorIQ SDK**

## What is ArmorIQ?

ArmorIQ SDK enables you to build **intelligent agents** that securely execute actions across multiple services (MCPs \- Model Context Providers). Think of it as a secure orchestration layer for AI agents.

**Key Benefits:**

* **Secure by Design**: Cryptographically verified action execution  
* **Intent-Based**: Declare what you want to do, not how  
* **Multi-Service**: Connect to multiple MCPs with one SDK  
* **Production Ready**: Built-in authentication, rate limiting, and monitoring

### Quick Installation:

#### **Prerequisites**

* Python 3.8 or higher  
* pip package manager  
* ArmorIQ API key (get one at [platform.armoriq.ai](https://platform.armoriq.ai/))

#### **Install**

```py
pip install armoriq-sdk
```

That's it\! You're ready to build your first agent.

## 

## 

## **Your First Agent**

## Let's build a simple data analysis agent that fetches and analyzes data.

### **Step 1: Initialize the SDK**

```py
from armoriq_sdk import ArmorIQClient

# Initialize with your credentials
client = ArmorIQClient(
    api_key="ak_live_your_api_key_here",  # Get from platform.armoriq.ai
    user_id="user_001",                    # Your application user ID
    agent_id="data_analyzer_v1"            # Your agent identifier
)
```

### **Step 2: Create an Intent Plan**

An **Intent Plan** is a declaration of what your agent wants to do. You provide a natural language prompt, and the SDK converts it to a structured plan that gets cryptographically verified.

```py
# Capture the plan from a prompt
# The SDK will create a structured plan from your prompt
captured_plan = client.capture_plan(
    llm="gpt-4",                                    # LLM to use for planning
    prompt="Fetch sales data and analyze metrics"  # What you want to do
)

print(f"Plan captured with {len(captured_plan.plan['steps'])} steps")

```

**Alternative: Pre-defined Plan**

If you want more control, you can provide a pre-built plan structure:

```py
# Define explicit plan structure
plan_structure = {
    "steps": [
        {
            "action": "fetch_data",
            "mcp": "analytics-mcp",
            "description": "Get sales data for analysis"
        },
        {
            "action": "analyze",
            "mcp": "analytics-mcp",
            "description": "Calculate statistics"
        }
    ]
}

# Capture with pre-defined structure
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Analyze sales data",
    plan=plan_structure  # Optional: Use your structure instead of LLM generation
```

###  What happens during capture\_plan()?

1. ### SDK takes your prompt (and optional plan structure)

2. ### Plan structure is validated and stored

3. ### Returns PlanCapture object ready for token request

### **Step 3: Get an Intent Token**

The token is a cryptographically signed proof that your plan is authorized. You can optionally include a **policy** to restrict what actions are allowed.

```py
# Request authorization token
token_response = client.get_intent_token(
    plan=captured_plan,
    expires_in=3600,  # Token valid for 1 hour
    policy={           # Optional: Define access policy
        "allow": ["*"],  # Allow all actions
        "deny": []       # No denied actions
    }
)

token = token_response["token"]
print(f"✓ Token issued: {token[:20]}...")
```

**Policy Options:**

Policies control what actions can be executed. You can define them programmatically or using the **visual policy builder** at [platform.armoriq.ai](https://platform.armoriq.ai/):

```py
# Allow specific actions only
policy = {
    "allow": ["analytics-mcp/analyze", "data-mcp/fetch_*"],
    "deny": ["data-mcp/delete_*"]
}

# With additional restrictions
policy = {
    "allow": ["*"],
    "deny": [],
    "allowed_tools": ["read_file", "write_file"],  # Tool restrictions
    "rate_limit": 100,                              # Requests per hour
    "ip_whitelist": ["192.168.1.0/24"]            # IP restrictions
}

token_response = client.get_intent_token(
    plan=captured_plan,
    policy=policy,  # Policy automatically built into CSRG token
    expires_in=3600
)
```

## Visual Policy Builder:

Instead of writing policies manually, use the **ArmorIQ Canvas** \- a visual drag-and-drop interface:

1. Go to [platform.armoriq.ai/dashboard/policies](https://platform.armoriq.ai/dashboard/policies)  
2. Click "Canvas" to open the visual builder  
3. Drag and drop: Users → MCPs → Agents  
4. Define permissions visually (read, create, update, delete)  
5. Set allowed tools, IP restrictions, time windows  
6. Export policy JSON or use directly via API

The canvas-built policy is automatically encoded into the CSRG token during get\_intent\_token().

### **Step 4: Execute Actions**

Now execute each step in your plan. The SDK automatically verifies each action.

```py
# Step 1: Fetch data
data_response = client.invoke(
    mcp_name="analytics-mcp",
    action="fetch_data",
    token=token,
    params={"dataset": "sales_2024"}
)
sales_data = data_response["data"]
print(f"✓ Fetched {len(sales_data)} records")

# Step 2: Analyze data
analysis_response = client.invoke(
    mcp_name="analytics-mcp",
    action="analyze",
    token=token,
    params={
        "data": sales_data,
        "metrics": ["mean", "median", "std"]
    }
)

print(f"✓ Analysis complete: {analysis_response['results']}")
```

### **Complete Example**

````py
from armoriq_sdk import ArmorIQClient

# Initialize {#initialize  data-source-line="199"}
client = ArmorIQClient(
    api_key="ak_live_your_api_key_here",
    user_id="user_001",
    agent_id="data_analyzer_v1"
)

# Capture plan from prompt {#capture-plan-from-prompt  data-source-line="206"}
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch sales data from 2024 and calculate mean and median"
)

# Get authorization token {#get-authorization-token  data-source-line="212"}
token_response = client.get_intent_token(plan=captured_plan, expires_in=3600)
token = token_response["token"]

# Execute actions {#execute-actions  data-source-line="216"}
data = client.invoke("analytics-mcp", "fetch_data", token, {"dataset": "sales_2024"})
results = client.invoke("analytics-mcp", "analyze", token, {
    "data": data["data"],
    "metrics": ["mean", "median"]
})

print(f"Results: {results['results']}")
``` {data-source-line="224"}
````

**Alternative with pre-defined plan:**

````py
from armoriq_sdk import ArmorIQClient

# Initialize {#initialize-1  data-source-line="231"}
client = ArmorIQClient(
    api_key="ak_live_your_api_key_here",
    user_id="user_001",
    agent_id="data_analyzer_v1"
)

# Pre-define plan structure {#pre-define-plan-structure  data-source-line="238"}
plan_structure = {
    "steps": [
        {"action": "fetch_data", "mcp": "analytics-mcp"},
        {"action": "analyze", "mcp": "analytics-mcp"}
    ]
}

# Capture with explicit structure {#capture-with-explicit-structure  data-source-line="246"}
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Analyze sales data",
    plan=plan_structure  # Use explicit structure
)

# Get authorization {#get-authorization  data-source-line="253"}
token_response = client.get_intent_token(plan=captured_plan, expires_in=3600)
token = token_response["token"]

# Execute {#execute  data-source-line="257"}
data = client.invoke("analytics-mcp", "fetch_data", token, {"dataset": "sales_2024"})
results = client.invoke("analytics-mcp", "analyze", token, {
    "data": data["data"],
    "metrics": ["mean", "median"]
})

print(f"Results: {results['results']}")
``` {data-source-line="265"}
````

**Output:**

```
✓ Token issued: eyJhbGciOiJFZERTQS...
✓ Fetched 1250 records
✓ Analysis complete: {'mean': 45.2, 'median': 42.0}
Results: {'mean': 45.2, 'median': 42.0}
```

## **What Just Happened?**

Let's break down what the SDK did for you:

1. **Plan Canonicalization**: CSRG-IAP converted your plan to a canonical structure (CSRG format) and hashed it  
2. **Token Issuance**: SDK sent your plan to ArmorIQ Proxy, which validated your API key and requested CSRG-IAP to canonicalize it and issue a signed token.  
3. **Merkle Proof Generation**: Each action generates a cryptographic proof it was in the plan  
4. **IAP Verification**: ArmorIQ Proxy verifies each action matches the signed plan  
5. **Secure Execution**: Only after verification, your action executes on the MCP server

**Security Benefits:**

* No one can execute actions not in your plan  
* Tokens are time-limited and single-use  
* All actions are cryptographically verified  
* Complete audit trail of agent behavior

## **Agent Delegation (Multi-Agent Workflows)**

Delegate authority to sub-agents for specialized tasks. Ideal for hierarchical workflows where different agents handle different parts of a complex task.

### **Quick Example**

```py
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Parent agent creates the main plan
parent_client = ArmorIQClient(
    user_id="manager",
    agent_id="parent_agent"
)
parent_plan = parent_client.capture_plan(
    llm="gpt-4",
    prompt="Organize company retreat: venue, catering, transportation"
)
parent_token = parent_client.get_intent_token(
    plan_capture=parent_plan,
    validity_seconds=3600
)

# Generate keypair for sub-agent
delegate_private_key = ed25519.Ed25519PrivateKey.generate()
delegate_public_key = delegate_private_key.public_key()

pub_key_hex = delegate_public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
).hex()

# Delegate venue booking to events specialist
delegation_result = parent_client.delegate(
    intent_token=parent_token,
    delegate_public_key=pub_key_hex,
    validity_seconds=1800,  # 30 minutes
    allowed_actions=[
        "search_venues",
        "book_venue",
        "arrange_catering"
    ]
)

# Sub-agent uses delegated (restricted) token
events_client = ArmorIQClient(
    user_id="events_team",
    agent_id="events_agent"
)

result = events_client.invoke(
    mcp="events-mcp",
    action="book_venue",
    intent_token=delegation_result.delegated_token,
    params={"venue_id": "v123", "date": "2026-04-15"}
)

        "venue_id": "v123",
        "date": "2026-04-15"
    }
)
```

## 

### **Key Benefits**

* **Cryptographic Security:** Delegated tokens are bound to an Ed25519 public key  
* **Least Privilege:** Sub-agents only get access to explicitly allowed actions.  
* **Time-Limited:** Delegated tokens expire faster than parent tokens  
* **Auditable:** Every delegation is tracked with a unique `delegation_id`

## **Common Patterns**

### **Pattern 1: Multi-Step Data Pipeline**

```py
# LLM generates multi-step plan {#llm-generates-multi-step-plan  data-source-line="420"}
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch data, transform it, analyze, and store results"
)
# Get token once, execute multiple steps {#get-token-once-execute-multiple-steps  data-source-line="483"}
token = client.get_intent_token(
    plan_capture=captured_plan,
    validity_seconds=3600
)

raw_data = client.invoke(
    mcp="data-mcp",
    action="fetch_data",
    intent_token=token,
    params={...}
)

clean_data = client.invoke(
    mcp="data-mcp",
    action="transform",
    intent_token=token,
    params={"data": raw_data.result}
)

insights = client.invoke(
    mcp="analytics-mcp",
    action="analyze",
    intent_token=token,
    params={"data": clean_data.result}
)

client.invoke(
    mcp="data-mcp",
    action="store",
    intent_token=token,
    params={"results": insights.result}
)
```

### **Pattern 2: Conditional Execution**

```py
# Include both possible paths in plan {#include-both-possible-paths-in-plan  data-source-line="438"}
captured_plan = client.capture_plan(
    llm="gpt-4",
    prompt="Check status and process as new or existing"
)
token = client.get_intent_token(captured_plan)["token"]

status = client.invoke("data-mcp", "check_status", token, {...})
if status["is_new"]:
    result = client.invoke("data-mcp", "process_new", token, {...})
else:
    result = client.invoke("data-mcp", "process_existing", token, {...})
```

### **Pattern 3: Parallel Execution**

```py
import concurrent.futures

plan = {
    "steps": [
        {"action": "analyze", "mcp": "analytics-mcp"},  # Can repeat same action
        {"action": "analyze", "mcp": "analytics-mcp"},
        {"action": "analyze", "mcp": "analytics-mcp"}
    ]
}

token = client.get_intent_token(client.capture_plan(plan))["token"]

datasets = ["sales", "marketing", "operations"]

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(
            client.invoke, 
            "analytics-mcp", 
            "analyze", 
            token, 
            {"dataset": ds}
        )
        for ds in datasets
    ]
    
    results = [f.result() for f in futures]
```

### 

### **Error Handling**

Always handle errors gracefully:

```py
from armoriq_sdk.exceptions import (
    TokenExpiredError,
    VerificationError,
    MCPError
)

try:
    token = client.get_intent_token(plan=plan)["token"]
    result = client.invoke("analytics-mcp", "analyze", token, params)
    
except TokenExpiredError:
    # Token expired, get a new one
    token = client.get_intent_token(plan=plan)["token"]
    result = client.invoke("analytics-mcp", "analyze", token, params)
    
except VerificationError as e:
    # Action not in plan or verification failed
    print(f"Verification failed: {e}")
    # Re-create plan with correct actions
    
except MCPError as e:
    # MCP execution failed
    print(f"MCP error: {e.message}")
    # Handle MCP-specific error
    
except Exception as e:
    # Unexpected error
    print(f"Unexpected error: {e}")
```

## 

## **Configuration**

### **Token Expiration**

```py
# Short-lived token (5 minutes)
token = client.get_intent_token(plan=plan, expires_in=300)

# Long-lived token (24 hours)
token = client.get_intent_token(plan=plan, expires_in=86400)
```

### **Logging**

```py
import logging

# Enable SDK logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("armoriq_sdk")
```

## **Best Practices**

### Do This

1. **Declare all possible actions upfront** in your plan  
2. **Use descriptive action names** (fetch\_user\_data not action1)  
3. **Handle token expiration** gracefully with retry logic  
4. **Keep tokens short-lived** (1 hour default is good)  
5. **Log all agent actions** for debugging and auditing  
6. **Use one client instance** per agent (reuse connections)

### Avoid This

1. **Don't modify plans after getting tokens** \- verification will fail  
2. **Don't share tokens between agents** \- use separate API keys  
3. **Don't hardcode API keys** \- use environment variables  
4. **Don't skip error handling** \- network issues happen  
5. **Don't create new clients for each request** \- connection overhead  
6. **Don't execute actions not in the plan** \- verification will fail

## **Environment Variables**

Set up your environment:

```py
# .env file
ARMORIQ_API_KEY=ak_live_your_api_key_here
ARMORIQ_PROXY_URL=https://customer-proxy.armoriq.ai
```

Use in code:

```py
import os
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(
    api_key=os.getenv("ARMORIQ_API_KEY"),
    user_id=os.getenv("ARMORIQ_USER_ID"),
    agent_id="my_agent",
    proxy_url=os.getenv("ARMORIQ_PROXY_URL")
)
```

## **Testing Your Integration**

### **Test API Key**

```py
from armoriq_sdk import ArmorIQClient

try:
    client = ArmorIQClient(
        api_key="ak_live_...",
        user_id="test_user",
        agent_id="test_agent"
    )
    
    # Simple plan to test connectivity
    captured_plan = client.capture_plan(
        llm="gpt-4",
        prompt="Test connectivity with ping"
    )
    token = client.get_intent_token(plan=captured_plan)

    print("✓ API key valid and proxy reachable")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### **Test MCP Availability**

```py
# Test if MCP is available
try:
    captured_plan = client.capture_plan(
        llm="gpt-4",
        prompt="Test analytics MCP availability"
    )
    token = client.get_intent_token(plan=captured_plan)["token"]

    result = client.invoke(
        "analytics-mcp",
        "test",
        token,
        {}
    )
    
    print(f"✓ analytics-mcp available: {result}")
    
except Exception as e:
    print(f"✗ analytics-mcp unavailable: {e}")
```

## **Quick Reference**

### **Essential Methods**

```py
# Initialize client
client = ArmorIQClient(api_key, user_id, agent_id)

# Capture plan
plan = client.capture_plan(plan_dict)

# Get token
token_response = client.get_intent_token(plan, expires_in=3600)
token = token_response["token"]

# Execute action
result = client.invoke(mcp_name, action, token, params)
```

### 

### **Token Response Structure**

```
{
    "success": True,
    "token": "eyJhbGc...",      # JWT token (created by CSRG-IAP with hash&Merkle)
    "plan_hash": "abc123...",   # SHA256 of plan (created by CSRG-IAP)
    "merkle_root": "def456...", # Merkle tree root (created by CSRG-IAP)
    "expires_at": 1234567890    # Unix timestamp

}
```

### **Invoke Response Structure**

```
{
    "success": True,
    "data": { ... },            # MCP response data
    "execution_time_ms": 145,   # How long it took
    "mcp": "analytics-mcp",     # Which MCP executed
    "action": "analyze"         # Which action ran
}
```

## **Getting Help**

### Common Issues

**"Invalid API key"**

* Check your API key starts with ak\_live\_  
* Verify it's 64 hexadecimal characters after the prefix  
* Ensure no extra spaces or newlines

**"Token expired"**

* Tokens are time-limited (default 1 hour)  
* Get a new token when expired  
* Consider longer expires\_in for long-running tasks

**"Step verification failed"**

* Action not declared in original plan  
* Plan was modified after getting token  
* Recreate token with correct plan

