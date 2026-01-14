"""
Agent Delegation Example

Demonstrates delegating subtasks to other agents
with trust updates.
"""

import logging
from armoriq_sdk import ArmorIQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    print("🤝 Agent Delegation Example")
    print("=" * 60)

    # Initialize parent agent
    parent_client = ArmorIQClient(
        iap_endpoint="http://localhost:8000",
        proxy_endpoints={"orchestration-mcp": "http://localhost:3001"},
        user_id="demo_user",
        agent_id="parent_agent",
    )

    # Parent agent's main task
    main_task_prompt = """
    Organize a company retreat:
    1. Book venue and catering (delegate to events agent)
    2. Arrange transportation (delegate to travel agent)
    3. Send invitations (delegate to comms agent)
    """

    print(f"\n📋 Main Task: {main_task_prompt}\n")

    # Capture main plan
    main_plan = parent_client.capture_plan(llm="gpt-4", prompt=main_task_prompt)
    print(f"✅ Main plan captured: {main_plan.plan_hash[:16]}...")

    # Get parent token
    parent_token = parent_client.get_intent_token(main_plan, validity_seconds=3600)
    print(f"✅ Parent token issued: {parent_token.token_id}\n")

    # Delegate subtasks
    print("🎬 Delegating subtasks...")
    print("-" * 60)

    # Subtask 1: Delegate to events agent
    print("\n1️⃣ Delegating venue booking to events agent...")
    try:
        events_subtask = {
            "goal": "Book venue and catering for 50 people",
            "steps": [
                {"action": "search_venues", "capacity": 50},
                {"action": "book_venue", "date": "2026-04-15"},
                {"action": "arrange_catering", "menu": "standard"},
            ],
        }

        events_delegation = parent_client.delegate(
            target_agent="events_agent",
            subtask=events_subtask,
            intent_token=parent_token,
            trust_policy={"max_budget": 5000, "requires_approval": False},
        )

        print(f"   ✅ Delegated to events_agent")
        print(f"      New Token: {events_delegation.new_token.token_id}")
        print(f"      Trust Delta: {events_delegation.trust_delta}")

    except Exception as e:
        logger.error(f"Events delegation failed: {e}")

    # Subtask 2: Delegate to travel agent
    print("\n2️⃣ Delegating transportation to travel agent...")
    try:
        travel_subtask = {
            "goal": "Arrange transportation for 50 people",
            "steps": [
                {"action": "quote_bus_rental", "passengers": 50},
                {"action": "book_bus", "date": "2026-04-15"},
            ],
        }

        travel_delegation = parent_client.delegate(
            target_agent="travel_agent",
            subtask=travel_subtask,
            intent_token=parent_token,
            trust_policy={"max_budget": 2000},
        )

        print(f"   ✅ Delegated to travel_agent")
        print(f"      New Token: {travel_delegation.new_token.token_id}")

    except Exception as e:
        logger.error(f"Travel delegation failed: {e}")

    # Subtask 3: Delegate to comms agent
    print("\n3️⃣ Delegating invitations to comms agent...")
    try:
        comms_subtask = {
            "goal": "Send retreat invitations to all employees",
            "steps": [
                {"action": "load_employee_list"},
                {"action": "create_invitation", "template": "retreat_2026"},
                {"action": "send_bulk_email", "recipients": "all_employees"},
            ],
        }

        comms_delegation = parent_client.delegate(
            target_agent="comms_agent",
            subtask=comms_subtask,
            intent_token=parent_token,
            trust_policy={"data_access": "employee_emails"},
        )

        print(f"   ✅ Delegated to comms_agent")
        print(f"      New Token: {comms_delegation.new_token.token_id}")

    except Exception as e:
        logger.error(f"Comms delegation failed: {e}")

    print("\n" + "=" * 60)
    print("✨ All subtasks delegated successfully!")
    print("\n📊 Delegation Summary:")
    print("   - 3 agents coordinated")
    print("   - Trust policies enforced")
    print("   - Audit trail maintained")

    parent_client.close()


if __name__ == "__main__":
    main()
