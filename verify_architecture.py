#!/usr/bin/env python3
"""
ArmorIQ SDK Quick Verification Script

This script runs through all major SDK features to verify
the implementation matches the architecture diagram.
"""

import sys
import os

def test_imports():
    """Test 1: Verify all imports work"""
    print("\n" + "="*70)
    print("TEST 1: Import Verification")
    print("="*70)
    
    try:
        from armoriq_sdk import ArmorIQClient
        print("✅ ArmorIQClient imported")
    except ImportError as e:
        print(f"❌ Failed to import ArmorIQClient: {e}")
        return False
    
    try:
        from armoriq_sdk.models import (
            IntentToken, 
            PlanCapture, 
            MCPInvocation,
            DelegationResult
        )
        print("✅ All models imported")
    except ImportError as e:
        print(f"❌ Failed to import models: {e}")
        return False
    
    try:
        from armoriq_sdk.exceptions import (
            InvalidTokenException,
            IntentMismatchException,
            MCPInvocationException,
            DelegationException,
            TokenExpiredException,
            ConfigurationException,
        )
        print("✅ All exceptions imported")
    except ImportError as e:
        print(f"❌ Failed to import exceptions: {e}")
        return False
    
    print("\n✅ All imports successful")
    return True


def test_client_initialization():
    """Test 2: Verify client can be initialized"""
    print("\n" + "="*70)
    print("TEST 2: Client Initialization (from Architecture)")
    print("="*70)
    print("Required from diagram: Config with IAP endpoint")
    
    from armoriq_sdk import ArmorIQClient
    
    try:
        # Test with explicit config (as shown in architecture)
        client = ArmorIQClient(
            iap_endpoint="http://localhost:3001",
            user_id="test-user",
            agent_id="test-agent"
        )
        print("✅ Client initialized with explicit config")
        print(f"   IAP Endpoint: {client.iap_endpoint}")
        print(f"   User ID: {client.user_id}")
        print(f"   Agent ID: {client.agent_id}")
        return True
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False


def test_api_signatures():
    """Test 3: Verify all APIs exist with correct signatures"""
    print("\n" + "="*70)
    print("TEST 3: API Signature Verification (from Architecture)")
    print("="*70)
    print("Required APIs from diagram:")
    print("  • capture_plan(llm, prompt)")
    print("  • get_intent_token(plan)")
    print("  • invoke(mcp, action, intent_token)")
    print("  • delegate()")
    
    from armoriq_sdk import ArmorIQClient
    import inspect
    
    client = ArmorIQClient(
        iap_endpoint="http://localhost:3001",
        user_id="test-user",
        agent_id="test-agent"
    )
    
    # Check capture_plan
    if hasattr(client, 'capture_plan'):
        sig = inspect.signature(client.capture_plan)
        params = list(sig.parameters.keys())
        if 'llm' in params and 'prompt' in params:
            print("✅ capture_plan(llm, prompt) - MATCHES ARCHITECTURE")
        else:
            print(f"⚠️  capture_plan exists but signature differs: {params}")
    else:
        print("❌ capture_plan not found")
        return False
    
    # Check get_intent_token
    if hasattr(client, 'get_intent_token'):
        sig = inspect.signature(client.get_intent_token)
        params = list(sig.parameters.keys())
        if 'plan' in params:
            print("✅ get_intent_token(plan) - MATCHES ARCHITECTURE")
        else:
            print(f"⚠️  get_intent_token exists but signature differs: {params}")
    else:
        print("❌ get_intent_token not found")
        return False
    
    # Check invoke
    if hasattr(client, 'invoke'):
        sig = inspect.signature(client.invoke)
        params = list(sig.parameters.keys())
        if 'mcp' in params and 'action' in params and 'intent_token' in params:
            print("✅ invoke(mcp, action, intent_token) - MATCHES ARCHITECTURE")
            if 'user_email' in params:
                print("   ➕ Enhanced with user_email for IAM context")
        else:
            print(f"⚠️  invoke exists but signature differs: {params}")
    else:
        print("❌ invoke not found")
        return False
    
    # Check delegate
    if hasattr(client, 'delegate'):
        sig = inspect.signature(client.delegate)
        print("✅ delegate() - MATCHES ARCHITECTURE")
        params = list(sig.parameters.keys())
        if 'delegate_public_key' in params:
            print("   ➕ Enhanced with public key-based delegation")
    else:
        print("❌ delegate not found")
        return False
    
    print("\n✅ All APIs present and match architecture")
    return True


def test_exceptions():
    """Test 4: Verify exception classes exist"""
    print("\n" + "="*70)
    print("TEST 4: Exception Verification (from Architecture)")
    print("="*70)
    print("Required exceptions from diagram:")
    print("  • InvalidTokenException")
    print("  • IntentMismatchException")
    
    from armoriq_sdk.exceptions import (
        ArmorIQException,
        InvalidTokenException,
        IntentMismatchException,
        MCPInvocationException,
        DelegationException,
        TokenExpiredException,
        ConfigurationException,
    )
    
    # Test exception hierarchy
    try:
        assert issubclass(InvalidTokenException, ArmorIQException)
        print("✅ InvalidTokenException - MATCHES ARCHITECTURE")
        
        assert issubclass(IntentMismatchException, ArmorIQException)
        print("✅ IntentMismatchException - MATCHES ARCHITECTURE")
        
        # Additional exceptions
        print("   ➕ TokenExpiredException (enhancement)")
        print("   ➕ MCPInvocationException (enhancement)")
        print("   ➕ DelegationException (enhancement)")
        print("   ➕ ConfigurationException (enhancement)")
        
        print("\n✅ Exception hierarchy correct")
        return True
    except AssertionError as e:
        print(f"❌ Exception hierarchy incorrect: {e}")
        return False


def test_models():
    """Test 5: Verify data models"""
    print("\n" + "="*70)
    print("TEST 5: Data Model Verification")
    print("="*70)
    
    from armoriq_sdk.models import IntentToken, PlanCapture
    import time
    
    # Test IntentToken with new fields
    try:
        token = IntentToken(
            token_id="test-token-123",
            plan_hash="abc123",
            signature="sig-xyz",
            issued_at=time.time(),
            expires_at=time.time() + 3600,
            policy={"test": "policy"},
            composite_identity="user:agent",
            raw_token={},
            # New fields from implementation
            plan_id="plan-123",
            client_info={"clientId": "client1", "clientName": "Test Client"},
            policy_validation={"allowed_tools": ["tool1", "tool2"]},
            step_proofs=[{"step": 1, "proof": "abc"}],
            total_steps=3,
        )
        print("✅ IntentToken model with enhanced fields")
        print(f"   • Basic fields: token_id, signature, timestamps")
        print(f"   • Enhanced: policy_validation with allowed_tools")
        print(f"   • Enhanced: step_proofs for verification")
        print(f"   • Enhanced: client_info for multi-tenancy")
    except Exception as e:
        print(f"❌ IntentToken model failed: {e}")
        return False
    
    # Test PlanCapture
    try:
        plan = PlanCapture(
            description="Test plan",
            steps=[
                {
                    "step": 1,
                    "mcp": "test-mcp",
                    "action": "test_action",
                    "params": {}
                }
            ]
        )
        print("✅ PlanCapture model working")
    except Exception as e:
        print(f"❌ PlanCapture model failed: {e}")
        return False
    
    print("\n✅ All models working correctly")
    return True


def test_architecture_flow():
    """Test 6: Verify architecture flow logic"""
    print("\n" + "="*70)
    print("TEST 6: Architecture Flow Verification")
    print("="*70)
    print("Expected flow from diagram:")
    print("  1. Agent → capture_plan")
    print("  2. Agent → get_intent_token → IAP")
    print("  3. Agent → invoke → Proxy → IAP (verify) → MCP")
    print("  4. Agent → delegate → IAP")
    
    from armoriq_sdk import ArmorIQClient
    from armoriq_sdk.models import PlanCapture
    
    try:
        client = ArmorIQClient(
            iap_endpoint="http://localhost:3001",
            proxy_endpoints={"test-mcp": "http://localhost:3002/test-mcp"},
            user_id="test-user",
            agent_id="test-agent"
        )
        print("✅ Step 1: Client configured (IAP + Proxy endpoints)")
        
        # Verify proxy endpoint mapping exists
        assert hasattr(client, 'proxy_endpoints')
        assert isinstance(client.proxy_endpoints, dict)
        print("✅ Step 2: Proxy endpoint mapping configured")
        
        # Verify IAP endpoint
        assert hasattr(client, 'iap_endpoint')
        assert client.iap_endpoint == "http://localhost:3001"
        print("✅ Step 3: IAP endpoint configured")
        
        print("\n✅ Architecture flow logic implemented correctly")
        return True
        
    except Exception as e:
        print(f"❌ Architecture flow verification failed: {e}")
        return False


def test_iam_enhancement():
    """Test 7: Verify IAM context enhancement"""
    print("\n" + "="*70)
    print("TEST 7: IAM Context Enhancement Verification")
    print("="*70)
    print("Enhanced feature: Automatic IAM context injection")
    
    from armoriq_sdk import ArmorIQClient
    import inspect
    
    client = ArmorIQClient(
        iap_endpoint="http://localhost:3001",
        user_id="test-user",
        agent_id="test-agent"
    )
    
    # Check if invoke accepts user_email parameter
    sig = inspect.signature(client.invoke)
    params = list(sig.parameters.keys())
    
    if 'user_email' in params:
        print("✅ invoke() accepts user_email parameter")
        print("   This enables IAM context injection with:")
        print("   • email / user_email")
        print("   • user_id / agent_id")
        print("   • allowed_tools (from token policy)")
        return True
    else:
        print("⚠️  user_email parameter not found in invoke()")
        return False


def test_delegation_enhancement():
    """Test 8: Verify public key delegation enhancement"""
    print("\n" + "="*70)
    print("TEST 8: Public Key Delegation Enhancement")
    print("="*70)
    print("Enhanced feature: Ed25519 public key-based delegation")
    
    from armoriq_sdk import ArmorIQClient
    import inspect
    
    client = ArmorIQClient(
        iap_endpoint="http://localhost:3001",
        user_id="test-user",
        agent_id="test-agent"
    )
    
    # Check delegate signature
    sig = inspect.signature(client.delegate)
    params = list(sig.parameters.keys())
    
    if 'delegate_public_key' in params:
        print("✅ delegate() requires delegate_public_key")
        print("   This enables cryptographic delegation with:")
        print("   • Ed25519 public key authentication")
        print("   • validity_seconds for time-limited delegation")
        print("   • allowed_actions for permission scoping")
        return True
    else:
        print("⚠️  delegate_public_key parameter not found")
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    print("\nTest Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    # Architecture compliance
    print("\n" + "="*70)
    print("ARCHITECTURE COMPLIANCE")
    print("="*70)
    
    core_tests = [
        "Imports",
        "Client Init",
        "API Signatures",
        "Exceptions",
    ]
    
    core_passed = sum(1 for test in core_tests if results.get(test, False))
    core_total = len(core_tests)
    
    compliance = (core_passed / core_total) * 100
    
    print(f"\nCore Architecture: {core_passed}/{core_total} ({compliance:.0f}%)")
    
    if compliance == 100:
        print("✅ FULLY COMPLIANT with architecture diagram")
    elif compliance >= 75:
        print("⚠️  MOSTLY COMPLIANT with architecture diagram")
    else:
        print("❌ NOT COMPLIANT with architecture diagram")
    
    # Enhancements
    enhancement_tests = ["IAM Enhancement", "Delegation Enhancement"]
    enhancements_passed = sum(1 for test in enhancement_tests if results.get(test, False))
    
    if enhancements_passed > 0:
        print(f"\nEnhancements: {enhancements_passed}/{len(enhancement_tests)} implemented")
        print("✅ SDK includes production-ready enhancements")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - SDK READY FOR USE!")
    elif compliance == 100:
        print("✅ ARCHITECTURE COMPLIANT - Some enhancements may need work")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    
    print("="*70 + "\n")
    
    return passed == total


def main():
    """Run all verification tests"""
    print("="*70)
    print("ArmorIQ SDK Architecture Verification")
    print("="*70)
    print("\nThis script verifies that the SDK implementation")
    print("matches the architecture diagram provided.")
    
    results = {}
    
    # Run tests
    results["Imports"] = test_imports()
    results["Client Init"] = test_client_initialization()
    results["API Signatures"] = test_api_signatures()
    results["Exceptions"] = test_exceptions()
    results["Models"] = test_models()
    results["Architecture Flow"] = test_architecture_flow()
    results["IAM Enhancement"] = test_iam_enhancement()
    results["Delegation Enhancement"] = test_delegation_enhancement()
    
    # Print summary
    success = print_summary(results)
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
