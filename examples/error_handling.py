"""
Error Handling Example

Demonstrates comprehensive error handling for common scenarios.
"""

import logging
from armoriq_sdk import (
    ArmorIQClient,
    InvalidTokenException,
    IntentMismatchException,
    TokenExpiredException,
    MCPInvocationException,
    DelegationException,
    ConfigurationException,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_invalid_token():
    """Demonstrate InvalidTokenException handling."""
    print("\n🔴 Scenario 1: Invalid Token")
    print("-" * 60)

    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={"test-mcp": "http://localhost:3001"},
        user_id="test_user",
        agent_id="error_test_agent",
    )

    try:
        plan = client.capture_plan("gpt-4", "Test action")
        token = client.get_intent_token(plan)

        # Simulate invalid token by tampering
        from copy import deepcopy

        invalid_token = deepcopy(token)
        invalid_token.raw_token["signature"] = "invalid_signature"

        # Try to invoke with invalid token
        client.invoke("test-mcp", "test_action", invalid_token)

    except InvalidTokenException as e:
        print(f"✅ Caught InvalidTokenException: {e}")
        print(f"   Token ID: {e.token_id}")
    finally:
        client.close()


def handle_expired_token():
    """Demonstrate TokenExpiredException handling."""
    print("\n⏰ Scenario 2: Expired Token")
    print("-" * 60)

    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={"test-mcp": "http://localhost:3001"},
        user_id="test_user",
        agent_id="error_test_agent",
    )

    try:
        import time

        plan = client.capture_plan("gpt-4", "Time-sensitive action")

        # Get token with very short validity
        token = client.get_intent_token(plan, validity_seconds=1)
        print(f"Token expires in: {token.time_until_expiry:.1f}s")

        # Wait for expiration
        print("Waiting for token to expire...")
        time.sleep(2)

        # Try to use expired token
        client.invoke("test-mcp", "test_action", token)

    except TokenExpiredException as e:
        print(f"✅ Caught TokenExpiredException: {e}")
        print(f"   Expired at: {e.expired_at}")
    finally:
        client.close()


def handle_intent_mismatch():
    """Demonstrate IntentMismatchException handling."""
    print("\n⚠️  Scenario 3: Intent Mismatch")
    print("-" * 60)

    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={"test-mcp": "http://localhost:3001"},
        user_id="test_user",
        agent_id="error_test_agent",
    )

    try:
        # Capture plan for specific actions
        plan = client.capture_plan("gpt-4", "Only book flight, nothing else")
        token = client.get_intent_token(plan)

        # Try to execute action not in plan
        client.invoke(
            "test-mcp",
            "book_hotel",  # Not in original plan!
            token,
            params={"location": "Paris"},
        )

    except IntentMismatchException as e:
        print(f"✅ Caught IntentMismatchException: {e}")
        print(f"   Action: {e.action}")
        print(f"   Plan Hash: {e.plan_hash[:16]}...")
    finally:
        client.close()


def handle_mcp_invocation_error():
    """Demonstrate MCPInvocationException handling."""
    print("\n🔌 Scenario 4: MCP Invocation Error")
    print("-" * 60)

    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={
            "nonexistent-mcp": "http://localhost:9999"  # Invalid endpoint
        },
        user_id="test_user",
        agent_id="error_test_agent",
    )

    try:
        plan = client.capture_plan("gpt-4", "Test unavailable service")
        token = client.get_intent_token(plan)

        # Try to invoke unavailable MCP
        client.invoke("nonexistent-mcp", "test_action", token)

    except MCPInvocationException as e:
        print(f"✅ Caught MCPInvocationException: {e}")
        print(f"   MCP: {e.mcp}")
        print(f"   Action: {e.action}")
        print(f"   Status Code: {e.status_code}")
    finally:
        client.close()


def handle_configuration_error():
    """Demonstrate ConfigurationException handling."""
    print("\n⚙️  Scenario 5: Configuration Error")
    print("-" * 60)

    try:
        # Try to initialize without required config
        client = ArmorIQClient(
            iap_endpoint=None,  # Missing!
            user_id="test_user",
            agent_id="error_test_agent",
        )

    except ConfigurationException as e:
        print(f"✅ Caught ConfigurationException: {e}")


def handle_delegation_error():
    """Demonstrate DelegationException handling."""
    print("\n🤝 Scenario 6: Delegation Error")
    print("-" * 60)

    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        user_id="test_user",
        agent_id="error_test_agent",
    )

    try:
        plan = client.capture_plan("gpt-4", "Delegate to unavailable agent")
        token = client.get_intent_token(plan)

        # Try to delegate to non-existent agent
        client.delegate(
            target_agent="nonexistent_agent",
            subtask={"action": "test"},
            intent_token=token,
        )

    except DelegationException as e:
        print(f"✅ Caught DelegationException: {e}")
        print(f"   Target Agent: {e.target_agent}")
    finally:
        client.close()


def main():
    print("=" * 60)
    print("🧪 ArmorIQ SDK - Error Handling Examples")
    print("=" * 60)

    scenarios = [
        ("Invalid Token", handle_invalid_token),
        ("Expired Token", handle_expired_token),
        ("Intent Mismatch", handle_intent_mismatch),
        ("MCP Invocation Error", handle_mcp_invocation_error),
        ("Configuration Error", handle_configuration_error),
        ("Delegation Error", handle_delegation_error),
    ]

    for name, handler in scenarios:
        try:
            handler()
        except Exception as e:
            logger.error(f"Unexpected error in {name}: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("✨ Error handling examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
