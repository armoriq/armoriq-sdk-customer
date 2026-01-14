"""
Multi-MCP Coordination Example

Demonstrates coordinating actions across multiple MCPs
with a single intent token.
"""

import logging
from armoriq_sdk import ArmorIQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    print("🌐 Multi-MCP Coordination Example")
    print("=" * 60)

    # Initialize client with multiple proxy endpoints
    client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={
            "travel-mcp": "http://localhost:3001",
            "finance-mcp": "http://localhost:3002",
            "email-mcp": "http://localhost:3003",
        },
        user_id="demo_user",
        agent_id="multi_mcp_agent",
    )

    # Create a complex plan involving multiple services
    prompt = """
    1. Check my account balance (finance)
    2. If balance > $1000, book flight to NYC (travel)
    3. Send confirmation email (email)
    """

    print(f"\n📋 Prompt: {prompt}\n")

    # Capture plan
    plan = client.capture_plan(llm="gpt-4", prompt=prompt)
    print(f"✅ Plan captured: {plan.plan_hash[:16]}...\n")

    # Get token
    token = client.get_intent_token(plan, validity_seconds=600)
    print(f"✅ Token issued: {token.token_id}\n")

    # Execute coordinated workflow
    print("🎬 Executing coordinated workflow...")
    print("-" * 60)

    # Step 1: Check balance via finance-mcp
    print("\n1️⃣ Checking account balance...")
    try:
        balance_result = client.invoke(
            mcp="finance-mcp",
            action="get_balance",
            intent_token=token,
            params={"account_id": "user_account"},
        )
        balance = balance_result.result.get("balance", 0)
        print(f"   Balance: ${balance:.2f}")

        # Step 2: Book flight if balance sufficient
        if balance > 1000:
            print("\n2️⃣ Balance sufficient! Booking flight...")
            flight_result = client.invoke(
                mcp="travel-mcp",
                action="book_flight",
                intent_token=token,
                params={
                    "origin": "SFO",
                    "destination": "JFK",
                    "date": "2026-03-01",
                },
            )
            booking_ref = flight_result.result.get("booking_ref")
            print(f"   ✅ Flight booked: {booking_ref}")

            # Step 3: Send confirmation email
            print("\n3️⃣ Sending confirmation email...")
            email_result = client.invoke(
                mcp="email-mcp",
                action="send_email",
                intent_token=token,
                params={
                    "to": "user@example.com",
                    "subject": "Flight Booking Confirmation",
                    "body": f"Your flight is confirmed! Booking: {booking_ref}",
                },
            )
            print(f"   ✅ Email sent: {email_result.result.get('message_id')}")

        else:
            print("\n2️⃣ Insufficient balance. Skipping flight booking.")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")

    print("\n" + "=" * 60)
    print("✨ Multi-MCP workflow complete!")

    client.close()


if __name__ == "__main__":
    main()
