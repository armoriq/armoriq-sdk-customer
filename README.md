# ArmorIQ SDK

**Build secure AI agents with cryptographic intent verification.**

The ArmorIQ SDK enables developers to build AI agents with built-in security and auditability. Just one API key - no cloud complexity.

---

## Why ArmorIQ?

- **Simple** - Just one API key, no cloud credentials
- **Secure** - Cryptographic verification for every action
- **Auditable** - Complete execution trail
- **Fast** - Get started in 5 minutes

---

## Installation

```bash
pip install armoriq-sdk
```

---

## Quick Start

### 1. Get Your API Key

Visit [dashboard.armoriq.io](https://dashboard.armoriq.io) to generate your API key.

### 2. Initialize the Client

```python
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(
    api_key="ak_your_key_here",
    user_id="your-user-id",
    agent_id="your-agent-id"
)
```

### 3. Capture Your Plan

```python
plan = {
    "goal": "Get weather forecast",
    "steps": [
        {
            "action": "get_weather",
            "tool": "weather_api",
            "inputs": {"city": "Boston"}
        }
    ]
}

plan_capture = client.capture_plan(
    llm="gpt-4",
    prompt="What's the weather in Boston?",
    plan=plan
)
```

### 4. Get Intent Token

```python
token = client.get_intent_token(plan_capture)
```

### 5. Invoke Actions

```python
result = client.invoke(
    mcp_name="weather-mcp",
    action="get_weather",
    intent_token=token,
    inputs={"city": "Boston"}
)

print(result)
```

---

## Documentation

For complete documentation, visit [docs.armoriq.ai](https://docs.armoriq.ai)

---

## Links

- [armoriq.ai](https://armoriq.ai)
- [docs.armoriq.ai](https://docs.armoriq.ai)
- [dashboard.armoriq.io](https://dashboard.armoriq.io)

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
