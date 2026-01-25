#!/usr/bin/env python3
"""
Test script for API Key validation in ArmorIQ Customer SDK.

This demonstrates:
1. SDK initialization with API key validation
2. Getting an intent token
3. Using the token to invoke MCP actions

Usage:
    # Set your API key
    export ARMORIQ_API_KEY="ak_live_394a3b12f575ac0693a2ee5b268b142d4719f29e8ce0b762e3020c5aca1554e9"
    export USER_ID="test_user_001"
    export AGENT_ID="test_agent"
    
    # Run the test
    python test_api_key_validation.py
"""

import os
import sys
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.exceptions import ConfigurationException, InvalidTokenException

def test_api_key_validation():
    """Test API key validation flow."""
    
    print("=" * 70)
    print("ArmorIQ SDK - API Key Validation Test")
    print("=" * 70)
    
    # Test 1: Missing API key
    print("\n📝 Test 1: Missing API Key")
    print("-" * 70)
    try:
        # Temporarily remove API key
        api_key_backup = os.environ.get("ARMORIQ_API_KEY")
        if api_key_backup:
            del os.environ["ARMORIQ_API_KEY"]
        
        client = ArmorIQClient(
            proxy_endpoint="http://localhost:3001",
            user_id="test_user",
            agent_id="test_agent",
            use_production=False
        )
        print("❌ FAIL: Should have raised ConfigurationException")
    except ConfigurationException as e:
        print(f"✅ PASS: Correctly rejected missing API key")
        print(f"   Error: {e}")
    finally:
        # Restore API key
        if api_key_backup:
            os.environ["ARMORIQ_API_KEY"] = api_key_backup
    
    # Test 2: Invalid API key format
    print("\n📝 Test 2: Invalid API Key Format")
    print("-" * 70)
    try:
        client = ArmorIQClient(
            api_key="invalid_key_format",
            proxy_endpoint="http://localhost:3001",
            user_id="test_user",
            agent_id="test_agent",
            use_production=False
        )
        print("❌ FAIL: Should have raised ConfigurationException")
    except ConfigurationException as e:
        print(f"✅ PASS: Correctly rejected invalid API key format")
        print(f"   Error: {e}")
    
    # Test 3: Invalid API key (wrong key)
    print("\n📝 Test 3: Invalid API Key (Wrong Key)")
    print("-" * 70)
    try:
        client = ArmorIQClient(
            api_key="ak_live_0000000000000000000000000000000000000000000000000000000000000000",
            proxy_endpoint="http://localhost:3001",
            user_id="test_user",
            agent_id="test_agent",
            use_production=False
        )
        print("❌ FAIL: Should have raised ConfigurationException for invalid key")
    except ConfigurationException as e:
        print(f"✅ PASS: Correctly rejected invalid API key")
        print(f"   Error: {e}")
    
    # Test 4: Valid API key
    print("\n📝 Test 4: Valid API Key")
    print("-" * 70)
    api_key = os.getenv("ARMORIQ_API_KEY")
    if not api_key:
        print("⚠️  SKIP: ARMORIQ_API_KEY not set")
        return
    
    try:
        client = ArmorIQClient(
            api_key=api_key,
            proxy_endpoint="http://localhost:3001",
            user_id=os.getenv("USER_ID", "test_user_001"),
            agent_id=os.getenv("AGENT_ID", "test_agent"),
            use_production=False
        )
        print(f"✅ PASS: SDK initialized with valid API key")
        print(f"   API Key: ak_live_***{api_key[-8:]}")
        print(f"   User ID: {client.user_id}")
        print(f"   Agent ID: {client.agent_id}")
        print(f"   Proxy: {client.proxy_endpoint}")
        
        # Test 5: Get intent token
        print("\n📝 Test 5: Get Intent Token")
        print("-" * 70)
        try:
            plan = client.capture_plan(
                "gpt-4",
                "Test API key authentication flow",
                plan={
                    "goal": "Test API key authentication",
                    "steps": [
                        {
                            "action": "test_action",
                            "mcp": "test-mcp",
                            "params": {}
                        }
                    ]
                }
            )
            print(f"✅ Plan captured: {len(plan.plan['steps'])} steps")
            
            token = client.get_intent_token(plan)
            print(f"✅ PASS: Intent token issued successfully")
            print(f"   Token ID: {token.token_id}")
            print(f"   Plan Hash: {token.plan_hash[:16]}...")
            print(f"   Expires in: {token.time_until_expiry:.1f}s")
            
            return True
            
        except InvalidTokenException as e:
            print(f"❌ FAIL: Failed to get intent token")
            print(f"   Error: {e}")
            return False
        finally:
            client.close()
            
    except ConfigurationException as e:
        print(f"❌ FAIL: SDK initialization failed")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n")
    success = test_api_key_validation()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All tests passed!")
        print("\nNext steps:")
        print("1. Use the token to invoke MCP actions")
        print("2. The proxy will validate your API key on every request")
        print("3. Check usage stats in the dashboard at https://dashboard.armoriq.io/api-keys")
    else:
        print("❌ Some tests failed")
        sys.exit(1)
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()
