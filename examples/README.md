# Examples README

This directory contains example scripts demonstrating various ArmorIQ SDK usage patterns.

## Prerequisites

Before running examples, ensure:

1. **CSRG-IAP service is running** (default: http://localhost:8000)
2. **ArmorIQ Proxy server(s) are running** (default: http://localhost:3001)
3. **SDK dependencies are installed**: `uv sync`

## Running Examples

### Basic Agent

Demonstrates fundamental SDK usage:
- Client initialization
- Plan capture
- Token acquisition
- MCP invocation

```bash
uv run python examples/basic_agent.py
```

### Multi-MCP Agent

Shows coordinating actions across multiple MCPs:
- Single plan with multiple services
- Conditional workflow execution
- Cross-service data flow

```bash
uv run python examples/multi_mcp_agent.py
```

### Delegation

Demonstrates agent-to-agent delegation:
- Subtask delegation
- Trust policy enforcement
- Parent-child agent coordination

```bash
uv run python examples/delegation_example.py
```

### Error Handling

Comprehensive error handling examples:
- Invalid token scenarios
- Token expiration handling
- Intent mismatch detection
- MCP invocation errors
- Configuration errors

```bash
uv run python examples/error_handling.py
```

## Configuration

Examples can be configured via environment variables:

```bash
# IAP endpoint
export IAP_ENDPOINT=http://localhost:8000

# User and agent identification
export USER_ID=demo_user
export AGENT_ID=example_agent

# Proxy endpoints (override defaults)
export TRAVEL_MCP_PROXY_URL=http://localhost:3001
export FINANCE_MCP_PROXY_URL=http://localhost:3002

# Run example
uv run python examples/basic_agent.py
```

## Modifying Examples

Each example is self-contained and can be modified to test different scenarios:

1. **Change the prompt**: Modify the prompt string to test different plans
2. **Add more MCPs**: Add entries to `proxy_endpoints` dict
3. **Adjust parameters**: Modify action parameters passed to `invoke()`
4. **Add error handling**: Wrap calls in try/except blocks

## Creating Your Own Examples

Use this template for new examples:

```python
"""
Your Example Name

Brief description of what this demonstrates.
"""

import logging
from armoriq_sdk import ArmorIQClient

logging.basicConfig(level=logging.INFO)

def main():
    # Initialize client
    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={"mcp-name": "http://localhost:3001"},
        user_id="demo_user",
        agent_id="your_agent",
    )
    
    try:
        # Your example code here
        plan = client.capture_plan("gpt-4", "Your prompt")
        token = client.get_intent_token(plan)
        result = client.invoke("mcp-name", "action", token)
        
        print(f"Result: {result}")
        
    finally:
        client.close()

if __name__ == "__main__":
    main()
```

## Troubleshooting

### Connection Errors

If you see connection errors:
1. Verify IAP service is running: `curl http://localhost:8000/health`
2. Verify proxy is running: `curl http://localhost:3001/health`
3. Check endpoint URLs in example configuration

### Token Errors

If you see token validation errors:
1. Ensure IAP service is properly configured
2. Check that user_id and agent_id are valid
3. Verify token hasn't expired (check validity_seconds)

### Import Errors

If you see import errors:
```bash
uv sync  # Reinstall dependencies
```

## Next Steps

After running examples:
1. Review the SDK source code in `armoriq_sdk/`
2. Read the full documentation in `README.md`
3. Check `DEVELOPMENT.md` for development guidelines
4. Write your own agent using the SDK!
