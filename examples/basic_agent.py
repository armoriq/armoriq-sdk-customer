"""
Basic ArmorIQ SDK Usage Example

Demonstrates:
- Client initialization
- Plan capture
- Token acquisition
- MCP invocation
"""

import logging
from armoriq_sdk import ArmorIQClient, InvalidTokenException, IntentMismatchException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Initialize the SDK client
    print("🚀 Initializing ArmorIQ SDK...")
    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",  # IAP service
        proxy_endpoints={
            "travel-mcp": "http://localhost:3001",  # Proxy for travel MCP
            "finance-mcp": "http://localhost:3002",  # Proxy for finance MCP
        },
        user_id="demo_user",
        agent_id="basic_agent",
        context_id="demo_context",
    )

    print("\n📋 Step 1: Capture Plan")
    print("=" * 60)

    # Capture a plan from a prompt
    prompt = "Book a flight from SFO to CDG on 2026-02-15 and reserve a hotel for 3 nights"
    plan = client.capture_plan(llm="gpt-4", prompt=prompt)

    print(f"✅ Plan captured successfully!")
    print(f"   Plan Hash: {plan.plan_hash[:32]}...")
    print(f"   Merkle Root: {plan.merkle_root[:32]}...")
    print(f"   Action Paths: {len(plan.ordered_paths)}")

    print("\n🎫 Step 2: Get Intent Token")
    print("=" * 60)

    # Get intent token from IAP
    token = client.get_intent_token(plan, validity_seconds=300)

    print(f"✅ Intent token issued!")
    print(f"   Token ID: {token.token_id}")
    print(f"   Expires in: {token.time_until_expiry:.1f} seconds")
    print(f"   Plan Hash: {token.plan_hash[:32]}...")

    print("\n🎬 Step 3: Invoke MCP Actions")
    print("=" * 60)

    # Invoke travel MCP to book flight
    try:
        print("Booking flight via travel-mcp...")
        flight_result = client.invoke(
            mcp="travel-mcp",
            action="book_flight",
            intent_token=token,
            params={
                "origin": "SFO",
                "destination": "CDG",
                "date": "2026-02-15",
                "passengers": 1,
            },
        )

        print(f"✅ Flight booked!")
        print(f"   Status: {flight_result.status}")
        print(f"   Execution Time: {flight_result.execution_time:.2f}s")
        print(f"   Result: {flight_result.result}")

    except InvalidTokenException as e:
        print(f"❌ Token validation failed: {e}")
    except IntentMismatchException as e:
        print(f"❌ Action not in plan: {e}")
    except Exception as e:
        print(f"❌ Invocation failed: {e}")

    # Invoke travel MCP to book hotel
    try:
        print("\nBooking hotel via travel-mcp...")
        hotel_result = client.invoke(
            mcp="travel-mcp",
            action="book_hotel",
            intent_token=token,
            params={
                "location": "Paris",
                "check_in": "2026-02-15",
                "check_out": "2026-02-18",
                "rooms": 1,
            },
        )

        print(f"✅ Hotel booked!")
        print(f"   Status: {hotel_result.status}")
        print(f"   Execution Time: {hotel_result.execution_time:.2f}s")
        print(f"   Result: {hotel_result.result}")

    except Exception as e:
        print(f"❌ Hotel booking failed: {e}")

    print("\n✨ Complete! All actions executed successfully.")
    print("=" * 60)

    # Cleanup
    client.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
