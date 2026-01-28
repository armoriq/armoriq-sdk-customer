# 🚀 ArmorIQ SDK (Python)

**Simple, powerful SDK for building AI-powered tools with security built-in.**

Build MCP (Model Context Protocol) tools that your AI agents can safely call, with **ZERO security complexity**. The ArmorIQ SDK provides a simple, powerful interface for building AI agents that use the Canonical Structured Reasoning Graph (CSRG) Intent Assurance Plane (IAP) for secure, auditable action execution.

---

## ✨ Why Choose ArmorIQ SDK?

### 🎯 **No GCP Credentials Required!**

- ❌ No service account JSON files
- ❌ No KMS configuration
- ❌ No IAM role setup
- ✅ **Just one API key - that's it!**

### 🚀 **Perfect For:**

- 🎓 **Hackathons** - Get started in 5 minutes

- 💡 **Student Projects** - No cloud complexity## ⚡ Quick Start```

- 🔬 **Rapid Prototyping** - Test ideas fast

- 🎨 **Creative Tools** - Focus on building, not configuring┌─────────┐     capture_plan()      ┌──────────┐

- 📚 **Learning** - Simple, clean API

### Installation│  Agent  │ ──────────────────────> │ IAP      │

### 🔒 **Security Without Complexity**

ArmorIQ handles all the hard stuff:│         │                          │ (CSRG)   │

- ✅ Ed25519 cryptographic signatures

- ✅ Merkle proof verification```bash└─────────┘                          └──────────┘

- ✅ Token expiration and rotation

- ✅ Rate limiting and abuse protectionpip install armoriq     │                                    │



**You just need an API key!**```     │ get_intent_token()                 │



---     │ <──────────────────────────────────┘



## ⚡ 5-Minute Quickstart### Hello World     │



### Step 1: Install     │ invoke(mcp, action, token)



```bash```python     ├──────────────────────> ┌──────────────┐

pip install armoriq

```from armoriq import Client, Action     │                         │ AIQ Proxy A  │──> MCP A



### Step 2: Get Your API Key     │                         └──────────────┘



1. Go to [dashboard.armoriq.io](https://dashboard.armoriq.io)# 1. Initialize client     │                                 │

2. Sign up (free!)

3. Click **Generate API Key**client = Client(     │                         verify_token(IAP)

4. Copy your key (starts with `ak_`)

    user_id="your-user-id",     │

**No GCP setup required!** 🎉

    api_key="your-api-key"     └──────────────────────> ┌──────────────┐

### Step 3: Write Your First Script

)                               │ AIQ Proxy B  │──> MCP B

```python

from armoriq import Client, Action                               └──────────────┘



# Initialize with just your API key# 2. Create a plan```

client = Client(api_key="ak_your_key_here")

plan = client.create_plan(

# Create a plan

plan = client.create_plan(    goal="Get weather for Boston",## Features

    goal="Get weather for Boston",

    actions=[Action(tool="get_weather", params={"city": "Boston"})]    actions=[

)

        Action(✅ **Simple API** - 4 core methods: `capture_plan()`, `get_intent_token()`, `invoke()`, `delegate()`  

# Get token (backend handles all crypto!)

token = client.get_token(plan)            tool="get_weather",✅ **Intent Verification** - Every action verified against the original plan  



# Call your tool            params={"city": "Boston"}✅ **Multi-MCP Support** - Seamlessly route actions across multiple MCPs  

result = client.call(

    mcp="weather-mcp",        )✅ **IAM Context Injection** - Automatic IAM context passing to MCP tools  

    tool="get_weather",

    params={"city": "Boston"},    ]✅ **Public Key Delegation** - Ed25519-based secure delegation between agents  

    token=token

))✅ **Token Management** - Automatic token caching and refresh  



print(result.data)  # {"temp": 72, "condition": "sunny"}✅ **Type-Safe** - Full Pydantic models and type hints  

```

# 3. Get access token✅ **Async-First** - Built on modern async/await patterns  

### Step 4: Run It!

token = client.get_token(plan)✅ **Error Handling** - Clear exceptions for token and intent issues  

```bash

python my_first_mcp.py

```

# 4. Call your tool## Installation

**Done! No service accounts, no KMS, no headaches!** 🎉

result = client.call(

---

    mcp="weather-mcp",```bash

## 🆚 Customer SDK vs Enterprise SDK

    tool="get_weather",pip install armoriq-sdk

| Feature | Customer SDK | Enterprise SDK |

|---------|:------------:|:--------------:|    params={"city": "Boston"},```

| **GCP Credentials** | ❌ Not needed | ⚠️ Required |

| **Service Accounts** | ❌ Not needed | ⚠️ Required |    token=token

| **KMS Configuration** | ❌ Not needed | ⚠️ Required |

| **Setup Time** | ✅ 5 minutes | ⚠️ 2-3 hours |)For development:

| **API Complexity** | ✅ Simple (4 methods) | ⚠️ Complex (10+ methods) |

| **IAM Context** | ❌ Not exposed | ✅ Full control |

| **Delegation** | ❌ No | ✅ Yes |

| **Audit Trail** | ❌ No | ✅ Yes |# 5. Use the result```bash

| **Price** | 💚 Free tier | 💰 $999/month+ |

| **Perfect For** | Hackathons, demos | Enterprise apps |if result.success:# Clone the repo



**Need advanced features?** Upgrade to [Enterprise SDK](../armoriq-sdk-enterprise/README.md) later!    print(f"Weather: {result.data}")git clone https://github.com/armoriq/armoriq-sdk-python



---else:cd armoriq-sdk-python



## 📚 Core Concepts    print(f"Error: {result.error}")



### 1. Plans```# Install with uv

A **plan** describes what you want to do:

uv sync

```python

plan = client.create_plan(**That's it! 🎉**

    goal="Check weather for multiple cities",

    actions=[# Or with pip

        Action(tool="get_weather", params={"city": "Boston"}),

        Action(tool="get_weather", params={"city": "NYC"}),---pip install -e ".[dev]"

        Action(tool="get_weather", params={"city": "LA"})

    ]```

)

```## 📚 Core Concepts



### 2. Tokens## Configuration

A **token** is your secure pass (ArmorIQ backend handles all crypto):

### 1. Plans

```python

token = client.get_token(plan)A **plan** describes what you want to do:### Production Endpoints (Default)

# Token contains cryptographic proofs

# You don't need to understand the details!

```

```pythonThe SDK automatically connects to ArmorIQ production services:

### 3. Tool Calls

Execute your tools safely:plan = client.create_plan(



```python    goal="Check weather for multiple cities",- **IAP (Intent Assurance Plane)**: `https://iap.armoriq.io`

result = client.call(

    mcp="your-mcp-name",    actions=[- **Proxy Server**: `https://cloud-run-proxy.armoriq.io`

    tool="your-tool-name",

    params={"param1": "value1"},        Action(tool="get_weather", params={"city": "Boston"}),- **ConMap API**: `https://api.armoriq.io`

    token=token

)        Action(tool="get_weather", params={"city": "NYC"}),

```

        Action(tool="get_weather", params={"city": "LA"})### Environment Variables

---

    ]

## 🛠️ Building Your First MCP

)Create a `.env` file or set environment variables:

### Step 1: Create Your MCP Server

```

```python

# weather_mcp.py```bash

from fastmcp import FastMCP

### 2. Tokens# Required

mcp = FastMCP("Weather MCP")

A **token** is your secure pass to execute the plan:AGENT_ID=your-agent-id

@mcp.tool()

def get_weather(city: str) -> dict:USER_ID=your-user-id

    """Get current weather for a city"""

    # Your implementation here```python

    return {"city": city, "temp": 72, "condition": "sunny"}

token = client.get_token(plan)# Optional - Override production endpoints

if __name__ == "__main__":

    mcp.run(port=8083)# Token is automatically validated by ArmorIQ# IAP_ENDPOINT=https://iap.armoriq.io

```

```# PROXY_ENDPOINT=https://cloud-run-proxy.armoriq.io

### Step 2: Run Your MCP



```bash

python weather_mcp.py### 3. Tool Calls# For local development

# MCP running on http://localhost:8083

```Execute your tools safely:# ARMORIQ_ENV=development  # Uses localhost endpoints



### Step 3: Call It With ArmorIQ```



```python```python

from armoriq import Client, Action

result = client.call(### Local Development

# Just your API key - no GCP setup!

client = Client(api_key="ak_your_key")    mcp="your-mcp-name",



plan = client.create_plan(    tool="your-tool-name",For local testing with services running on localhost:

    goal="Get weather",

    actions=[Action(tool="get_weather", params={"city": "Boston"})]    params={"param1": "value1"},

)

    token=token```bash

token = client.get_token(plan)

result = client.call("weather-mcp", "get_weather", {"city": "Boston"}, token))export ARMORIQ_ENV=development



print(result.data)  # {"city": "Boston", "temp": 72, "condition": "sunny"}```export AGENT_ID=test-agent

```

export USER_ID=test-user

**No service accounts, no KMS - just works!** ✨

---```

---



## 🔧 Configuration

## 🛠️ Building Your First MCPThis automatically uses:

### Production (Default)

- IAP: `http://localhost:8082`

```python

# Uses production endpoints automatically### Step 1: Create Your MCP Server- Proxy: `http://localhost:3001`

client = Client(api_key="ak_your_key")

```



### Local Development```python## Quick Start



```python# my_mcp.py

# Point to local services

client = Client(from fastmcp import FastMCP### Production Usage

    api_key="dev-key",

    environment="local"  # Auto-configures to localhost

)

mcp = FastMCP("Calculator MCP")```python

# Or specify endpoints manually

client = Client(from armoriq_sdk import ArmorIQClient

    api_key="dev-key",

    iap_endpoint="http://localhost:8082",@mcp.tool()

    proxy_endpoint="http://localhost:3001"

)def add(a: int, b: int) -> int:# Production (uses default endpoints)

```

    """Add two numbers"""client = ArmorIQClient(

### Custom User ID (Optional)

    return a + b    user_id="user123",

```python

# Auto-generated by default    agent_id="my-agent"

client = Client(api_key="ak_your_key")

# user_id: "customer_a3f2d1b8"@mcp.tool())



# Or provide your owndef multiply(a: int, b: int) -> int:

client = Client(

    api_key="ak_your_key",    """Multiply two numbers"""# 1. Capture a plan from LLM output

    user_id="john_doe_123"

)    return a * bplan = client.capture_plan(

```

    llm="gpt-4",

---

if __name__ == "__main__":    prompt="Book a flight to Paris and reserve a hotel"

## 🎯 Common Use Cases

    mcp.run())

### 1. Weather Service

```

```python

client = Client(api_key="ak_your_key")# 2. Get an intent token from IAP



plan = client.create_plan(### Step 2: Run Your MCPtoken = client.get_intent_token(plan)

    goal="Get current weather",

    actions=[Action(tool="get_weather", params={"city": "Boston"})]

)

```bash# 3. Execute actions through MCP proxies

token = client.get_token(plan)

result = client.call("weather-mcp", "get_weather", {"city": "Boston"}, token)python my_mcp.pytry:

```

```    result = client.invoke(

### 2. Calculator

        mcp="travel-mcp",

```python

plan = client.create_plan(### Step 3: Call It With ArmorIQ        action="book_flight",

    goal="Calculate 5 + 3",

    actions=[Action(tool="add", params={"a": 5, "b": 3})]        intent_token=token,

)

```python        params={"destination": "CDG", "date": "2026-02-15"}

token = client.get_token(plan)

result = client.call("calc-mcp", "add", {"a": 5, "b": 3}, token)from armoriq import Client, Action    )

print(result.data)  # 8

```    print(f"Flight booked: {result}")



### 3. Content Generationclient = Client(user_id="dev123", api_key="...")    



```pythonexcept InvalidTokenException as e:

plan = client.create_plan(

    goal="Generate blog post",# Create plan    print(f"Token validation failed: {e}")

    actions=[Action(tool="generate_blog", params={"topic": "AI", "words": 500})]

)plan = client.create_plan(```



token = client.get_token(plan)    goal="Calculate 5 + 3",

result = client.call("content-mcp", "generate_blog", {"topic": "AI", "words": 500}, token)

```    actions=[## Core API



---        Action(tool="add", params={"a": 5, "b": 3})



## 🚨 Error Handling    ]### `capture_plan(llm: str, prompt: str) -> Dict`



```python)

from armoriq import Client, Action

from armoriq.exceptions import (Captures an execution plan from an LLM response and converts it to canonical CSRG format.

    AuthenticationError,

    ToolInvocationError,# Get token and call

    NetworkError

)token = client.get_token(plan)**Parameters:**



client = Client(api_key="ak_your_key")result = client.call(- `llm`: LLM identifier (e.g., "gpt-4", "claude-3")



try:    mcp="calculator-mcp",- `prompt`: User prompt or instruction

    plan = client.create_plan(...)

    token = client.get_token(plan)    tool="add",

    result = client.call(...)

        params={"a": 5, "b": 3},**Returns:** Canonical plan dictionary ready for token issuance

    if result.success:

        print(result.data)    token=token

    else:

        print(f"Tool failed: {result.error}"))---

        

except AuthenticationError:

    print("Invalid API key! Check dashboard.armoriq.io")

    print(result.data)  # Output: 8### `get_intent_token(plan: Dict) -> IntentToken`

except ToolInvocationError as e:

    print(f"Tool {e.tool_name} failed: {e.message}")```

    

except NetworkError as e:Requests a signed intent token from the IAP for the given plan.

    print(f"Network error: {e.message}")

```---



---**Parameters:**



## 📖 API Reference## 🎯 Common Use Cases- `plan`: Canonical plan from `capture_plan()`



### Client



```python### 1. Weather Service**Returns:** `IntentToken` object containing the signed token and metadata

Client(

    api_key: str,                    # Your API key (required)

    user_id: Optional[str] = None,   # Auto-generated if not provided

    iap_endpoint: str = "https://iap.armoriq.io",```python---

    proxy_endpoint: str = "https://proxy.armoriq.io",

    environment: str = "production"  # "production", "staging", or "local"# Call weather API

)

```plan = client.create_plan(### `invoke(mcp: str, action: str, intent_token: IntentToken, params: Dict = None, user_email: str = None) -> MCPInvocationResult`



### Methods    goal="Get current weather",



#### `create_plan(goal, actions)`    actions=[Action(tool="get_weather", params={"city": "Boston"})]Executes an MCP action through the ArmorIQ proxy with token verification and IAM context injection.

Create an execution plan.

)

**Args:**

- `goal` (str): What you want to accomplish**Parameters:**

- `actions` (List[Action]): List of actions to execute

token = client.get_token(plan)- `mcp`: MCP identifier (e.g., "travel-mcp", "finance-mcp")

**Returns:** `Plan` object

result = client.call("weather-mcp", "get_weather", {"city": "Boston"}, token)- `action`: Action name to invoke (tool name)

**Example:**

```python```- `intent_token`: Token from `get_intent_token()`

plan = client.create_plan(

    goal="Get weather",- `params`: Optional action parameters

    actions=[Action(tool="get_weather", params={"city": "Boston"})]

)### 2. Content Generation- `user_email`: Optional user email (injected into IAM context)

```



---

```python**Returns:** `MCPInvocationResult` with action result and metadata

#### `get_token(plan, expires_in=3600)`

Get an access token for a plan.# Generate blog post



**Args:**plan = client.create_plan(**Raises:**

- `plan` (Plan): The plan to execute

- `expires_in` (int): Token expiration in seconds (default: 1 hour)    goal="Generate blog content",- `InvalidTokenException`: Token signature/expiry invalid



**Returns:** `Token` object    actions=[Action(tool="generate_blog", params={"topic": "AI", "words": 500})]- `IntentMismatchException`: Action not in original plan



**Note:** Backend handles all cryptography. No GCP credentials needed!)- `MCPInvocationException`: MCP invocation failed



**Example:**

```python

token = client.get_token(plan, expires_in=7200)  # 2 hourstoken = client.get_token(plan)**IAM Context:** The SDK automatically injects `_iam_context` parameter with:

```

result = client.call("content-mcp", "generate_blog", {"topic": "AI", "words": 500}, token)- `email`: User email

---

```- `user_id`: User identifier  

#### `call(mcp, tool, params, token)`

Call a tool on an MCP.- `agent_id`: Agent identifier



**Args:**### 3. Data Analysis- `allowed_tools`: List of allowed tools from policy validation

- `mcp` (str): MCP identifier

- `tool` (str): Tool name

- `params` (dict): Tool parameters

- `token` (Token): Access token from get_token()```python---



**Returns:** `ToolResult` object# Analyze CSV data



**Example:**plan = client.create_plan(### `delegate(intent_token: IntentToken, delegate_public_key: str, validity_seconds: int = 3600, allowed_actions: List[str] = None) -> DelegationResult`

```python

result = client.call(    goal="Analyze sales data",

    mcp="weather-mcp",

    tool="get_weather",    actions=[Action(tool="analyze_csv", params={"file": "sales.csv"})]Delegates authority to another agent using public key-based CSRG delegation.

    params={"city": "Boston"},

    token=token)

)

```**Parameters:**



---token = client.get_token(plan)- `intent_token`: Token to delegate



## 🧪 Testingresult = client.call("analytics-mcp", "analyze_csv", {"file": "sales.csv"}, token)- `delegate_public_key`: Public key of delegate agent (Ed25519 hex format)



```python```- `validity_seconds`: Delegation validity in seconds (default: 3600)

# test_weather.py

import pytest- `allowed_actions`: Optional list of allowed actions (defaults to all)

from armoriq import Client, Action

---

@pytest.fixture

def client():**Returns:** `DelegationResult` with delegated token and metadata

    return Client(

        api_key="test-key",## 🔧 Configuration

        environment="local"

    )**Raises:**



def test_weather_tool(client):### Local Development- `DelegationException`: Delegation creation failed

    plan = client.create_plan(

        goal="Test weather",- `InvalidTokenException`: Original token is invalid

        actions=[Action(tool="get_weather", params={"city": "Boston"})]

    )```python

    

    token = client.get_token(plan)client = Client(**Example:**

    result = client.call("weather-mcp", "get_weather", {"city": "Boston"}, token)

        user_id="dev123",```python

    assert result.success

    assert "temperature" in result.data    api_key="dev-key",from cryptography.hazmat.primitives.asymmetric import ed25519

```

    iap_endpoint="http://localhost:8082",from cryptography.hazmat.primitives import serialization

Run tests:

```bash    proxy_endpoint="http://localhost:3001"

pytest test_weather.py

```)# Generate delegate keypair



---```delegate_private_key = ed25519.Ed25519PrivateKey.generate()



## 🐛 Troubleshootingdelegate_public_key = delegate_private_key.public_key()



### Issue: "Authentication failed"### Productionpub_key_bytes = delegate_public_key.public_bytes(

**Solution:** Check your API key at [dashboard.armoriq.io](https://dashboard.armoriq.io)

    encoding=serialization.Encoding.Raw,

```python

# ❌ Wrong```python    format=serialization.PublicFormat.Raw

client = Client(api_key="your-key")  # Literal string

client = Client()

# ✅ Correct

client = Client(api_key="ak_abc123...")  # Actual API key    user_id="prod-user",pub_key_hex = pub_key_bytes.hex()

```

    api_key="prod-api-key",

### Issue: "Token expired"

**Solution:** Get a new token or increase expiration:    iap_endpoint="https://iap.armoriq.io",# Create delegation



```python    proxy_endpoint="https://proxy.armoriq.io"result = client.delegate(

token = client.get_token(plan, expires_in=7200)  # 2 hours

```)    intent_token=token,



### Issue: "Tool not found"```    delegate_public_key=pub_key_hex,

**Solution:** Verify your MCP is running:

    validity_seconds=1800,

```bash

# Check if MCP is running---    allowed_actions=["approve_loan", "process_payment"]

curl http://localhost:8083/health

)

# Start your MCP

python your_mcp.py## 🚨 Error Handling

```

# Delegate uses new token

### Issue: "Do I need GCP credentials?"

**Answer:** **NO!** Customer SDK works with just an API key. No GCP setup required!```pythondelegate_agent = ArmorIQClient(...)



---from armoriq import Client, Actiondelegate_agent.invoke(



## 💰 Pricingfrom armoriq.exceptions import (    "loan-mcp",



### Free Tier (Perfect for Getting Started)    AuthenticationError,    "approve_loan",

- ✅ 1,000 API calls/month

- ✅ All core features    ToolInvocationError,    result.delegated_token,

- ✅ Community support

- ✅ No credit card required    NetworkError    params={"loan_id": "L123"}



### Starter ($29/month)))

- ✅ 10,000 calls/month

- ✅ Email support```

- ✅ 99% uptime SLA

client = Client(user_id="...", api_key="...")

### Pro ($99/month)

- ✅ 100,000 calls/month## Configuration

- ✅ Priority support

- ✅ 99.9% uptime SLAtry:

- ✅ Custom rate limits

    plan = client.create_plan(...)The SDK can be configured via constructor or environment variables:

**No hidden fees. No GCP bills. No surprise charges.**

    token = client.get_token(plan)

---

    result = client.call(...)```python

## 📞 Support

    client = ArmorIQClient(

- 📧 **Email**: support@armoriq.io

- 💬 **Discord**: [discord.gg/armoriq](https://discord.gg/armoriq)    if result.success:    iap_endpoint="https://iap.armoriq.example.com",  # or IAP_ENDPOINT env var

- 📖 **Docs**: [docs.armoriq.io](https://docs.armoriq.io)

- 🐛 **Issues**: [github.com/armoriq/sdk-customer/issues](https://github.com/armoriq/sdk-customer/issues)        print(result.data)    proxy_endpoints={

- 🎓 **Tutorials**: [youtube.com/@armoriq](https://youtube.com/@armoriq)

    else:        "travel-mcp": "https://proxy-a.armoriq.example.com",

**Response time**: Usually within 24 hours (Free tier) or 4 hours (Paid tiers)

        print(f"Tool failed: {result.error}")        "finance-mcp": "https://proxy-b.armoriq.example.com"

---

            },

## 🎓 Learning Resources

except AuthenticationError:    user_id="user123",

- 📺 [5-Minute Video Tutorial](https://youtube.com/@armoriq)

- 📖 [Complete Guide](https://docs.armoriq.io/customer-sdk)    print("Invalid API key!")    agent_id="my-agent",

- 🎨 [Example MCPs](./examples/)

- 💻 [GitHub Samples](https://github.com/armoriq/sdk-examples)        timeout=30.0,



---except ToolInvocationError as e:    max_retries=3



## 🚀 What's Next?    print(f"Tool {e.tool_name} failed: {e.message}"))



1. ✅ Install SDK: `pip install armoriq`    ```

2. ✅ Get API key from [dashboard.armoriq.io](https://dashboard.armoriq.io)

3. ✅ Build your first MCP (5 minutes!)except NetworkError as e:

4. 🎯 [Deploy to production](https://docs.armoriq.io/deployment)

5. 📊 [Monitor usage](https://dashboard.armoriq.io/usage)    print(f"Network error: {e.message}")## Examples

6. 🚀 [Scale up](https://dashboard.armoriq.io/billing)

```

---

See the `examples/` directory for complete examples:

## ❓ FAQ

---

**Q: Do I really not need GCP credentials?**  

A: **Correct!** ArmorIQ backend handles all security. You just need an API key.- `basic_agent.py` - Simple agent with plan capture and execution



**Q: Is this production-ready?**  ## 📖 API Reference- `multi_mcp_agent.py` - Agent coordinating multiple MCPs

A: **Yes!** Built on the same enterprise-grade infrastructure as our Enterprise SDK.

- `delegation_example.py` - Agent-to-agent delegation

**Q: Can I upgrade to Enterprise SDK later?**  

A: **Yes!** Easy migration path when you need advanced features.### Client- `error_handling.py` - Comprehensive error handling patterns



**Q: What about HIPAA/SOC2 compliance?**  

A: For compliance features, use [Enterprise SDK](../armoriq-sdk-enterprise/README.md).

```python## Development

**Q: How is this secured without GCP?**  

A: ArmorIQ backend uses Ed25519 signatures and Merkle proofs. You get security without complexity!Client(



---    user_id: str,          # Your user ID```bash



## 📜 License    api_key: str,          # Your API key# Install dev dependencies



MIT License - see [LICENSE](LICENSE) file    iap_endpoint: str,     # IAP service URL (optional)uv sync



---    proxy_endpoint: str    # Proxy service URL (optional)



## 🌟 Show Your Support)# Run tests



- ⭐ Star us on [GitHub](https://github.com/armoriq/sdk-customer)```uv run pytest

- 🐦 Follow us on [Twitter](https://twitter.com/armoriq)

- 💬 Join our [Discord](https://discord.gg/armoriq)



---### Methods# Run tests with coverage



**Happy building! 🎉**uv run pytest --cov=armoriq_sdk



**Remember:** No GCP credentials, no KMS, no complexity - just your API key and you're ready to go!#### `create_plan(goal, actions)`


Create an execution plan.# Format code

uv run black armoriq_sdk tests

**Args:**

- `goal` (str): What you want to accomplish# Type checking

- `actions` (List[Action]): List of actions to executeuv run mypy armoriq_sdk

```

**Returns:** `Plan` object

## Architecture Details

---

The SDK integrates with three key components:

#### `get_token(plan, expires_in=3600)`

Get an access token for a plan.1. **CSRG-IAP** - Issues intent tokens after plan canonicalization

2. **ArmorIQ Proxy** - Verifies tokens and routes MCP calls

**Args:**3. **MCPs** - Execute actual actions (travel, finance, etc.)

- `plan` (Plan): The plan to execute

- `expires_in` (int): Token expiration in seconds### Security Model



**Returns:** `Token` object- Every plan is converted to a canonical hash (CSRG)

- Intent tokens are Ed25519-signed by IAP

---- Proxies verify tokens before executing actions

- Actions are checked against Merkle proofs of the plan

#### `call(mcp, tool, params, token)`- All operations are append-only audited

Call a tool on an MCP.

## Contributing

**Args:**

- `mcp` (str): MCP identifierContributions welcome! Please see CONTRIBUTING.md for guidelines.

- `tool` (str): Tool name

- `params` (dict): Tool parameters## License

- `token` (Token): Access token

MIT License - see LICENSE file for details.

**Returns:** `ToolResult` object

## Support

---

- Documentation: https://docs.armoriq.example.com

## 🆚 vs Enterprise SDK- Issues: https://github.com/armoriq/armoriq-sdk-python/issues

- Discord: https://discord.gg/armoriq

| Feature | Customer SDK | Enterprise SDK |
|---------|--------------|----------------|
| **Simplicity** | ✅ Very simple | ⚠️ Complex |
| **IAM Context** | ❌ Not exposed | ✅ Full control |
| **Delegation** | ❌ No | ✅ Yes |
| **Audit Trails** | ❌ No | ✅ Yes |
| **Price** | 💚 Free tier | 💰 $999/month+ |
| **Use Case** | Simple tools | Enterprise apps |

**Need advanced features?** Check out [ArmorIQ Enterprise SDK](../armoriq-sdk-enterprise/README.md)

---

## 🤝 Examples

### Example 1: Multi-City Weather

```python
from armoriq import Client, Action

client = Client(user_id="dev123", api_key="...")

# Plan to check multiple cities
plan = client.create_plan(
    goal="Compare weather across cities",
    actions=[
        Action(tool="get_weather", params={"city": "Boston"}),
        Action(tool="get_weather", params={"city": "NYC"}),
        Action(tool="get_weather", params={"city": "LA"})
    ]
)

token = client.get_token(plan)

# Execute each action
cities = ["Boston", "NYC", "LA"]
for city in cities:
    result = client.call(
        mcp="weather-mcp",
        tool="get_weather",
        params={"city": city},
        token=token
    )
    print(f"{city}: {result.data}")
```

### Example 2: Calculator Chain

```python
# Chain calculations
plan = client.create_plan(
    goal="Calculate (5 + 3) * 2",
    actions=[
        Action(tool="add", params={"a": 5, "b": 3}),
        Action(tool="multiply", params={"a": 8, "b": 2})  # Use result from add
    ]
)

token = client.get_token(plan)

# First calculation
result1 = client.call("calc-mcp", "add", {"a": 5, "b": 3}, token)
print(f"5 + 3 = {result1.data}")  # 8

# Second calculation
result2 = client.call("calc-mcp", "multiply", {"a": result1.data, "b": 2}, token)
print(f"8 * 2 = {result2.data}")  # 16
```

---

## 🧪 Testing

```python
# test_my_mcp.py
import pytest
from armoriq import Client, Action

@pytest.fixture
def client():
    return Client(
        user_id="test-user",
        api_key="test-key",
        iap_endpoint="http://localhost:8082",
        proxy_endpoint="http://localhost:3001"
    )

def test_weather_tool(client):
    plan = client.create_plan(
        goal="Test weather",
        actions=[Action(tool="get_weather", params={"city": "Boston"})]
    )
    
    token = client.get_token(plan)
    result = client.call("weather-mcp", "get_weather", {"city": "Boston"}, token)
    
    assert result.success
    assert "temperature" in result.data
```

---

## 🐛 Troubleshooting

### Issue: "Authentication failed"
**Solution:** Check your API key in the ArmorIQ dashboard.

### Issue: "Token expired"
**Solution:** Get a new token or increase `expires_in`:
```python
token = client.get_token(plan, expires_in=7200)  # 2 hours
```

### Issue: "Tool not found"
**Solution:** Verify your MCP is running and tool name is correct.

### Issue: "Network error"
**Solution:** Check that endpoints are accessible:
```python
# Test connection
import requests
response = requests.get("http://localhost:3001/health")
print(response.status_code)  # Should be 200
```

---

## 📞 Support

- 📧 **Email**: support@armoriq.io
- 💬 **Discord**: [discord.gg/armoriq](https://discord.gg/armoriq)
- 📖 **Docs**: [docs.armoriq.io](https://docs.armoriq.io)
- 🐛 **Issues**: [github.com/armoriq/sdk/issues](https://github.com/armoriq/sdk/issues)

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file

---

## 🚀 What's Next?

1. ✅ Install SDK
2. ✅ Build your first MCP
3. ✅ Call it with ArmorIQ
4. 🎯 [Deploy to production](https://docs.armoriq.io/deployment)
5. 📊 [Monitor usage](https://dashboard.armoriq.io)

**Happy building! 🎉**
