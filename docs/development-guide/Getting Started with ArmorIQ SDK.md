# Getting Started with ArmorIQ SDK

This guide covers the current SDK flow and the new CLI-based onboarding.

## Prerequisites

- Python 3.9+
- An ArmorIQ API key from [platform.armoriq.ai](https://platform.armoriq.ai)

## Install

```bash
pip install armoriq-sdk
```

The package installs both CLI entrypoints:

```bash
armoriq --help
armoriq-cli --help
```

## Recommended Setup: CLI + armoriq.yaml

### 1. Initialize config

```bash
armoriq init
```

This interactive flow:
- verifies credentials
- captures agent/user/environment
- optionally discovers tools from MCP servers
- writes `armoriq.yaml`

### 2. Validate config

```bash
armoriq validate
```

Checks:
- YAML schema
- API key authentication
- MCP reachability
- policy tool references

### 3. Register

```bash
armoriq register
```

This registers the agent configuration with ArmorIQ control-plane and stores local status used by:

```bash
armoriq status
armoriq logs
```

## armoriq.yaml Schema

```yaml
version: v1

identity:
  api_key: $ARMORIQ_API_KEY
  user_id: jani-advisor
  agent_id: crewai-ferry-agent

environment: sandbox   # sandbox | production

proxy:
  url: https://customer-proxy.armoriq.ai
  timeout: 30
  max_retries: 3

mcp_servers:
  - id: ferryhopper
    url: https://mcp.ferryhopper.com/mcp
    description: Ferry route search and booking
    auth: none

  - id: github-mcp
    url: https://api.github.com/mcp
    description: GitHub repository operations
    auth:
      type: bearer
      token: $GITHUB_TOKEN

policy:
  allow:
    - ferryhopper.search_routes
    - ferryhopper.get_schedule
    - github-mcp.read_repository
  deny:
    - github-mcp.delete_repository
    - github-mcp.write:main

intent:
  ttl_seconds: 300
  require_csrg: true
```

Notes:
- `identity.api_key` can be a literal or env reference like `$ARMORIQ_API_KEY`.
- `auth` can be `none`, `bearer`, or `api_key`.

## Initialize SDK Client

### Option A: from config (recommended)

```python
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient.from_config("armoriq.yaml")
```

### Option B: direct constructor

```python
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(
    api_key="ak_live_your_key",
    user_id="user_001",
    agent_id="data_analyzer_v1",
)
```

## Core Execution Flow

### 1. Capture plan

`capture_plan(...)` requires an explicit `plan` dictionary.

```python
plan_capture = client.capture_plan(
    llm="gpt-4",
    prompt="Fetch sales data and compute summary metrics",
    plan={
        "goal": "Analyze sales",
        "steps": [
            {"mcp": "analytics-mcp", "action": "fetch_data", "params": {"dataset": "sales_2024"}},
            {"mcp": "analytics-mcp", "action": "analyze", "params": {"metrics": ["mean", "median"]}},
        ],
    },
)
```

### 2. Get intent token

```python
token = client.get_intent_token(
    plan_capture=plan_capture,
    validity_seconds=300,
    policy={
        "allow": ["analytics-mcp/fetch_data", "analytics-mcp/analyze"],
        "deny": [],
    },
)
```

### 3. Invoke MCP actions

```python
result = client.invoke(
    mcp="analytics-mcp",
    action="fetch_data",
    intent_token=token,
    params={"dataset": "sales_2024"},
)

print(result.result)
```

## Delegation (Optional)

```python
delegation = client.delegate(
    intent_token=token,
    delegate_public_key="<delegate-ed25519-public-key-hex>",
    validity_seconds=1800,
)

subagent_token = delegation.delegated_token
```

## Environment Variables

You can provide configuration via env vars as an alternative to YAML:

- `ARMORIQ_API_KEY`
- `USER_ID`
- `AGENT_ID`
- `CONTEXT_ID` (optional)
- `ARMORIQ_ENV` (`production` or `development`)
- `IAP_ENDPOINT` (optional override)
- `PROXY_ENDPOINT` (optional override)
- `BACKEND_ENDPOINT` (optional override)

## Minimal End-to-End Example

```python
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient.from_config("armoriq.yaml")

plan_capture = client.capture_plan(
    llm="gpt-4",
    prompt="Look up weather in Boston",
    plan={
        "goal": "Weather lookup",
        "steps": [
            {"mcp": "weather-mcp", "action": "get_weather", "params": {"city": "Boston"}}
        ],
    },
)

token = client.get_intent_token(plan_capture=plan_capture, validity_seconds=300)

result = client.invoke(
    mcp="weather-mcp",
    action="get_weather",
    intent_token=token,
    params={"city": "Boston"},
)

print(result.result)
client.close()
```
