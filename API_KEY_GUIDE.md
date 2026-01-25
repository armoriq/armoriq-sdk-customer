# ArmorIQ Customer SDK - API Key Authentication Guide

## Quick Start

### 1. Get Your API Key

1. Go to [https://dashboard.armoriq.io/api-keys](https://dashboard.armoriq.io/api-keys)
2. Click **"Create API Key"**
3. Copy your API key (starts with `ak_live_`)
4. **Save it securely** - you'll only see it once!

### 2. Set Up Your Environment

Create a `.env` file in your project:

```bash
# ArmorIQ Customer SDK Configuration
ARMORIQ_API_KEY=ak_live_your_key_here
USER_ID=your_user_id
AGENT_ID=your_agent_name
```

**Security Note:** Never commit `.env` files to version control! Add `.env` to your `.gitignore`.

### 3. Install the SDK

```bash
pip install armoriq-sdk
```

### 4. Basic Usage

```python
from armoriq_sdk import ArmorIQClient

# Initialize the client (reads from environment variables)
client = ArmorIQClient(
    proxy_endpoint="http://localhost:3001",  # Local development
    use_production=False  # Set True for production
)

# Capture a plan
plan = client.capture_plan(
    "gpt-4",
    "Book a flight to Paris",
    plan={
        "goal": "Book a flight to Paris",
        "steps": [
            {
                "action": "search_flights",
                "mcp": "travel-mcp",
                "params": {"destination": "Paris"}
            }
        ]
    }
)

# Get an intent token (validates API key)
token = client.get_intent_token(plan)
print(f"✅ Token issued: {token.token_id}")

# Invoke MCP action
result = client.invoke(
    mcp="travel-mcp",
    action="search_flights",
    intent_token=token,
    params={"destination": "Paris"}
)

print(f"✅ Result: {result.result}")
```

### 5. Error Handling

```python
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.exceptions import (
    ConfigurationException,
    InvalidTokenException,
    MCPInvocationException
)

try:
    client = ArmorIQClient()
    plan = client.capture_plan("gpt-4", "Test")
    token = client.get_intent_token(plan)
    
except ConfigurationException as e:
    # API key missing or invalid format
    print(f"❌ Configuration error: {e}")
    print("   Get your API key from https://dashboard.armoriq.io/api-keys")
    
except InvalidTokenException as e:
    # Token issuance failed (e.g., invalid API key)
    print(f"❌ Token error: {e}")
    print("   Check your API key is correct and not expired")
    
except MCPInvocationException as e:
    # MCP call failed
    print(f"❌ MCP invocation error: {e}")
```

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ARMORIQ_API_KEY` | ✅ Yes | Your API key from dashboard | `ak_live_394a3b...` |
| `USER_ID` | ✅ Yes | Your user identifier | `john.doe@company.com` |
| `AGENT_ID` | ✅ Yes | Your agent/app name | `my-travel-agent` |
| `CONTEXT_ID` | ❌ No | Optional context (default: "default") | `production` |
| `PROXY_ENDPOINT` | ❌ No | Proxy URL (default: production) | `http://localhost:3001` |
| `ARMORIQ_ENV` | ❌ No | Environment mode | `development` or `production` |

## API Key Best Practices

### ✅ DO:
- Store API keys in environment variables
- Use different API keys for development and production
- Rotate API keys regularly
- Revoke compromised keys immediately
- Monitor usage in the dashboard

### ❌ DON'T:
- Commit API keys to version control
- Share API keys in public channels
- Use production keys in development
- Hardcode API keys in your code
- Log or print API keys in plaintext

## Monitoring

Track your API key usage:
1. Go to [dashboard.armoriq.io/api-keys](https://dashboard.armoriq.io/api-keys)
2. View:
   - **Usage Count**: Total API calls
   - **Last Used**: When the key was last used
   - **Status**: Active/Expired/Revoked

## Troubleshooting

### "API key is required"
- **Cause**: `ARMORIQ_API_KEY` environment variable not set
- **Solution**: Set the environment variable or pass `api_key` parameter

### "Invalid API key format"
- **Cause**: API key doesn't start with `ak_live_` or `ak_test_`
- **Solution**: Get a valid API key from the dashboard

### "Token issuance failed"
- **Cause**: API key is invalid, expired, or revoked
- **Solution**: 
  1. Check the key in the dashboard
  2. Generate a new key if needed
  3. Update your `.env` file

### "Could not connect to proxy"
- **Cause**: Proxy server not running or wrong endpoint
- **Solution**:
  1. For local dev: Start proxy with `npm run start` in `armoriq-proxy-server-customer/`
  2. Check `PROXY_ENDPOINT` matches your proxy URL

## Example: MCP Development Workflow

```python
#!/usr/bin/env python3
"""
Example: Developing an MCP with ArmorIQ SDK
"""
import os
from armoriq_sdk import ArmorIQClient

# Load from .env file (or use environment variables)
client = ArmorIQClient(
    api_key=os.getenv("ARMORIQ_API_KEY"),
    user_id=os.getenv("USER_ID"),
    agent_id=os.getenv("AGENT_ID"),
    proxy_endpoint="http://localhost:3001",
    use_production=False
)

# 1. Define your plan
plan = client.capture_plan(
    "gpt-4",
    "Get weather for San Francisco",
    plan={
        "goal": "Get current weather",
        "steps": [
            {
                "action": "get_weather",
                "mcp": "weather-mcp",
                "params": {"city": "San Francisco"}
            }
        ]
    }
)

# 2. Get intent token (validates API key)
token = client.get_intent_token(plan)
print(f"✅ Token: {token.token_id}")

# 3. Invoke your MCP
result = client.invoke(
    mcp="weather-mcp",
    action="get_weather",
    intent_token=token,
    params={"city": "San Francisco"}
)

print(f"✅ Weather: {result.result}")

# 4. Clean up
client.close()
```

## Support

- **Dashboard**: [dashboard.armoriq.io](https://dashboard.armoriq.io)
- **API Reference**: [docs.armoriq.io/sdk](https://docs.armoriq.io/sdk)
- **Issues**: Contact support@armoriq.io
