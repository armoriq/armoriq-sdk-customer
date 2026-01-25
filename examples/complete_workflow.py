#!/usr/bin/env python3
"""
Complete Example: MCP Development with ArmorIQ API Keys

This example shows the full workflow:
1. Set up API key from dashboard
2. Initialize SDK with validation
3. Develop and test an MCP
4. Track usage in dashboard

Prerequisites:
    1. Get API key from https://platform.armoriq.ai/dashboard/api-keys
    2. Set environment variables (see below)
    3. Have your MCP server running
"""

import os
import sys
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.exceptions import (
    ConfigurationException,
    InvalidTokenException,
    MCPInvocationException
)

# ============================================================================
# STEP 1: Configure Environment
# ============================================================================
print("=" * 70)
print("ArmorIQ SDK - Complete MCP Development Example")
print("=" * 70)

# Check for API key
api_key = os.getenv("ARMORIQ_API_KEY")
if not api_key:
    print("\n❌ Error: ARMORIQ_API_KEY not set!")
    print("\n📝 To get started:")
    print("   1. Go to https://platform.armoriq.ai/dashboard/api-keys")
    print("   2. Click 'Create API Key'")
    print("   3. Copy your key (ak_live_...)")
    print("   4. Run: export ARMORIQ_API_KEY='your_key_here'")
    print()
    sys.exit(1)

print(f"\n✅ API Key loaded: ak_live_***{api_key[-8:]}")

# ============================================================================
# STEP 2: Initialize SDK (with automatic API key validation)
# ============================================================================
print("\n" + "─" * 70)
print("Initializing ArmorIQ SDK...")
print("─" * 70)

try:
    client = ArmorIQClient(
        # API key (reads from ARMORIQ_API_KEY env var)
        # User/Agent identity
        user_id=os.getenv("USER_ID", "developer@example.com"),
        agent_id=os.getenv("AGENT_ID", "my-mcp-agent"),
        # Endpoints (local development)
        proxy_endpoint="http://localhost:3001",
        use_production=False,
    )
    
    print(f"✅ SDK initialized successfully")
    print(f"   User: {client.user_id}")
    print(f"   Agent: {client.agent_id}")
    print(f"   Proxy: {client.proxy_endpoint}")
    
except ConfigurationException as e:
    print(f"❌ Configuration Error: {e}")
    sys.exit(1)

# ============================================================================
# STEP 3: Define Your MCP Plan
# ============================================================================
print("\n" + "─" * 70)
print("Capturing execution plan...")
print("─" * 70)

# Example: Weather MCP
plan_definition = {
    "goal": "Get weather forecast for a city",
    "steps": [
        {
            "action": "get_weather",
            "mcp": "weather-mcp",
            "params": {
                "city": "San Francisco",
                "units": "fahrenheit"
            }
        }
    ],
    "metadata": {
        "developer": client.user_id,
        "version": "1.0.0",
        "environment": "development"
    }
}

try:
    plan = client.capture_plan(
        llm="gpt-4",
        prompt="Get weather for San Francisco",
        plan=plan_definition
    )
    
    print(f"✅ Plan captured")
    print(f"   Goal: {plan.plan['goal']}")
    print(f"   Steps: {len(plan.plan['steps'])}")
    print(f"   First action: {plan.plan['steps'][0]['action']}")
    
except Exception as e:
    print(f"❌ Plan capture failed: {e}")
    client.close()
    sys.exit(1)

# ============================================================================
# STEP 4: Get Intent Token (validates API key with backend)
# ============================================================================
print("\n" + "─" * 70)
print("Requesting intent token...")
print("─" * 70)

try:
    token = client.get_intent_token(
        plan,
        validity_seconds=3600  # 1 hour
    )
    
    print(f"✅ Intent token issued")
    print(f"   Token ID: {token.token_id}")
    print(f"   Plan Hash: {token.plan_hash[:16]}...")
    print(f"   Expires in: {token.time_until_expiry:.1f}s")
    print(f"   Signature: {token.signature[:32]}...")
    
except InvalidTokenException as e:
    print(f"❌ Token issuance failed: {e}")
    print("\n💡 Possible reasons:")
    print("   - API key is invalid or revoked")
    print("   - Proxy server not running")
    print("   - CSRG IAP service not running")
    client.close()
    sys.exit(1)

# ============================================================================
# STEP 5: Invoke Your MCP
# ============================================================================
print("\n" + "─" * 70)
print("Invoking MCP action...")
print("─" * 70)

try:
    result = client.invoke(
        mcp="weather-mcp",
        action="get_weather",
        intent_token=token,
        params={
            "city": "San Francisco",
            "units": "fahrenheit"
        }
    )
    
    print(f"✅ MCP invocation successful")
    print(f"   Result: {result.result}")
    print(f"   Verified: {result.verified}")
    
except MCPInvocationException as e:
    print(f"❌ MCP invocation failed: {e}")
    print("\n💡 Possible reasons:")
    print("   - MCP server not running")
    print("   - Action not found in MCP")
    print("   - Invalid parameters")
    print("   - Token expired")

# ============================================================================
# STEP 6: Clean Up
# ============================================================================
client.close()

print("\n" + "=" * 70)
print("✅ Example completed successfully!")
print("=" * 70)

print("\n📊 Next Steps:")
print("   1. Check usage in dashboard: https://platform.armoriq.ai/dashboard/api-keys")
print("   2. View API key statistics (usage count, last used)")
print("   3. Create more API keys for different environments")
print("   4. Develop your own MCPs with this pattern")

print("\n🔐 Security Reminders:")
print("   - Never commit API keys to version control")
print("   - Use different keys for dev/staging/production")
print("   - Rotate keys regularly")
print("   - Revoke compromised keys immediately")

print("\n" + "=" * 70 + "\n")
