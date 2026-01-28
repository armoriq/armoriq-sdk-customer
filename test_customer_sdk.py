#!/usr/bin/env python3
"""
Quick Test Script for Customer SDK
===================================

Run this to verify the SDK is working correctly.
Tests all major functions without needing real services.

Usage:
    python test_customer_sdk.py
"""

import sys
sys.path.insert(0, '/home/hari/Videos/Armoriq/armoriq-sdk-customer')

from armoriq import Client, Action
from armoriq.exceptions import AuthenticationError, PlanError

def test_client_initialization():
    """Test 1: Client initialization"""
    print("\n" + "="*60)
    print("TEST 1: Client Initialization")
    print("="*60)
    
    try:
        # Test with auto-generated user_id
        client = Client(api_key="test_key_123")
        print(f"✅ Client created with auto user_id: {client.user_id}")
        assert client.user_id.startswith("customer_")
        
        # Test with custom user_id
        client2 = Client(api_key="test_key_123", user_id="john_doe")
        print(f"✅ Client created with custom user_id: {client2.user_id}")
        assert client2.user_id == "john_doe"
        
        # Test environment presets
        client3 = Client(api_key="test_key", environment="local")
        print(f"✅ Local environment: {client3.iap_endpoint}")
        assert "localhost" in client3.iap_endpoint
        
        print("\n✅ All initialization tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_plan_creation():
    """Test 2: Plan creation"""
    print("\n" + "="*60)
    print("TEST 2: Plan Creation")
    print("="*60)
    
    try:
        client = Client(api_key="test_key")
        
        # Test single action plan
        plan = client.create_plan(
            goal="Test plan",
            actions=[
                Action(tool="test_tool", params={"param1": "value1"})
            ]
        )
        print(f"✅ Single action plan created: {plan.goal}")
        assert len(plan.actions) == 1
        
        # Test multiple actions
        plan2 = client.create_plan(
            goal="Multi-action plan",
            actions=[
                Action(tool="tool1", params={"x": 1}),
                Action(tool="tool2", params={"y": 2}),
                Action(tool="tool3", params={"z": 3})
            ]
        )
        print(f"✅ Multi-action plan created with {len(plan2.actions)} actions")
        assert len(plan2.actions) == 3
        
        # Test plan to dict conversion
        plan_dict = plan.to_dict()
        print(f"✅ Plan converted to dict: {plan_dict.keys()}")
        assert "goal" in plan_dict
        assert "actions" in plan_dict
        
        print("\n✅ All plan creation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_error_handling():
    """Test 3: Error handling"""
    print("\n" + "="*60)
    print("TEST 3: Error Handling")
    print("="*60)
    
    try:
        client = Client(api_key="test_key")
        
        # Test empty actions
        try:
            plan = client.create_plan(goal="Empty plan", actions=[])
            print("❌ Should have raised PlanError for empty actions")
            return False
        except PlanError as e:
            print(f"✅ Correctly raised PlanError: {e.message}")
        
        # Test Action model
        action = Action(tool="test", params={"x": 1}, description="Test action")
        print(f"✅ Action created with description: {action.description}")
        
        # Test Token model
        from armoriq.models import Token
        token = Token(token_string="test_token_abc123", expires_at="2026-01-20")
        print(f"✅ Token string representation: {str(token)}")
        assert str(token) == "test_token_abc123"
        
        # Test ToolResult model
        from armoriq.models import ToolResult
        result = ToolResult(success=True, data={"temp": 72})
        print(f"✅ ToolResult success: {bool(result)}")
        assert bool(result) == True
        
        result_fail = ToolResult(success=False, data=None, error="Test error")
        print(f"✅ ToolResult failure: {bool(result_fail)}")
        assert bool(result_fail) == False
        
        print("\n✅ All error handling tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_headers_and_config():
    """Test 4: Headers and configuration"""
    print("\n" + "="*60)
    print("TEST 4: Headers & Configuration")
    print("="*60)
    
    try:
        client = Client(api_key="test_api_key_abc123")
        
        # Check headers
        print(f"✅ API Key header set: {'X-API-Key' in client._headers}")
        assert client._headers["X-API-Key"] == "test_api_key_abc123"
        
        print(f"✅ SDK version header: {client._headers['X-ArmorIQ-SDK']}")
        assert "customer-python" in client._headers["X-ArmorIQ-SDK"]
        
        # Check endpoint configuration
        print(f"✅ IAP endpoint: {client.iap_endpoint}")
        print(f"✅ Proxy endpoint: {client.proxy_endpoint}")
        
        print("\n✅ All configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_models():
    """Test 5: Data models"""
    print("\n" + "="*60)
    print("TEST 5: Data Models")
    print("="*60)
    
    try:
        from armoriq.models import Plan, Action, Token, ToolResult
        
        # Test Action dataclass
        action = Action(tool="get_weather", params={"city": "Boston"})
        print(f"✅ Action: tool={action.tool}, params={action.params}")
        
        # Test Plan dataclass
        plan = Plan(
            goal="Get weather",
            actions=[action],
            plan_id="test_plan_123"
        )
        print(f"✅ Plan: goal={plan.goal}, plan_id={plan.plan_id}")
        
        # Test Token dataclass
        token = Token(
            token_string="eyJ0eXAi...",
            expires_at="2026-01-20T10:00:00Z",
            plan_id="test_plan_123"
        )
        print(f"✅ Token: {token.token_string[:20]}...")
        
        # Test ToolResult dataclass
        result = ToolResult(
            success=True,
            data={"temperature": 72, "condition": "sunny"},
            tool_name="get_weather"
        )
        print(f"✅ ToolResult: success={result.success}, data={result.data}")
        
        print("\n✅ All model tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_exceptions():
    """Test 6: Exception classes"""
    print("\n" + "="*60)
    print("TEST 6: Exception Classes")
    print("="*60)
    
    try:
        from armoriq.exceptions import (
            ArmorIQError,
            AuthenticationError,
            ToolInvocationError,
            PlanError,
            NetworkError
        )
        
        # Test base exception
        try:
            raise ArmorIQError("Base error")
        except ArmorIQError as e:
            print(f"✅ ArmorIQError: {e}")
        
        # Test AuthenticationError
        try:
            raise AuthenticationError("Invalid API key")
        except AuthenticationError as e:
            print(f"✅ AuthenticationError: {e.message}")
        
        # Test ToolInvocationError
        try:
            raise ToolInvocationError("get_weather", "Tool timeout")
        except ToolInvocationError as e:
            print(f"✅ ToolInvocationError: {e.tool_name} - {e.message}")
        
        # Test PlanError
        try:
            raise PlanError("Invalid action format")
        except PlanError as e:
            print(f"✅ PlanError: {e.message}")
        
        # Test NetworkError
        try:
            raise NetworkError("http://localhost:8082", "Connection refused")
        except NetworkError as e:
            print(f"✅ NetworkError: {e.endpoint} - {e.message}")
        
        print("\n✅ All exception tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("ARMORIQ CUSTOMER SDK - COMPREHENSIVE TEST SUITE")
    print("🚀"*30)
    
    print("\n✨ Testing Customer SDK without GCP credentials!")
    print("   - No service accounts")
    print("   - No KMS configuration")
    print("   - Just API keys!\n")
    
    tests = [
        test_client_initialization,
        test_plan_creation,
        test_error_handling,
        test_headers_and_config,
        test_models,
        test_exceptions
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100
    
    print(f"\nTests Passed: {passed}/{total} ({percentage:.1f}%)")
    
    if passed == total:
        print("\n✅ ✅ ✅ ALL TESTS PASSED! ✅ ✅ ✅")
        print("\n🎉 Customer SDK is working correctly!")
        print("   Ready to use with real services.\n")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        print("   Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
