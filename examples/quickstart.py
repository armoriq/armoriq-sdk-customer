"""
ArmorIQ Customer SDK - Quick Start Example
==========================================

This example shows the simplest way to use ArmorIQ SDK:
1. Create a plan
2. Get a token
3. Call a tool

✨ NO GCP CREDENTIALS REQUIRED! ✨
Just provide your API key and you're ready to go.

Requirements:
- Weather MCP running on port 8083 (or use remote MCP)
- ArmorIQ IAP running (production or local)
- ArmorIQ Proxy running (production or local)
- Your API key from platform.armoriq.ai
"""

from armoriq import Client, Action

def main():
    print("🚀 ArmorIQ Customer SDK - Quick Start")
    print("=" * 50)
    print("✨ No GCP credentials, no KMS, no service accounts!\n")
    
    # Step 1: Initialize client (JUST AN API KEY!)
    print("Step 1: Initializing client...")
    print("  💡 Tip: Get your API key from platform.armoriq.ai")
    
    client = Client(
        api_key="demo-api-key",  # Replace with your actual API key
        environment="local"  # Change to "production" when ready
    )
    print(f"  ✅ Client initialized (user: {client.user_id})\n")
    
    # Step 2: Create a plan
    print("Step 2: Creating execution plan...")
    plan = client.create_plan(
        goal="Get weather information for Boston",
        actions=[
            Action(
                tool="get_weather",
                params={"city": "Boston"},
                description="Fetch current weather for Boston"
            )
        ]
    )
    print(f"  ✅ Plan created: {plan.goal}\n")
    
    # Step 3: Get access token (backend handles all crypto!)
    print("Step 3: Getting access token...")
    print("  🔒 Backend handles Ed25519 signing & Merkle proofs")
    token = client.get_token(plan, expires_in=3600)
    print(f"  ✅ Token obtained (expires in 1 hour)\n")
    
    # Step 4: Call the tool
    print("Step 4: Calling weather tool...")
    result = client.call(
        mcp="weather-mcp",
        tool="get_weather",
        params={"city": "Boston"},
        token=token
    )
    
    # Step 5: Display results
    if result.success:
        print("  ✅ Tool execution successful!")
        print(f"\n📊 Result:")
        print(f"   {result.data}\n")
    else:
        print(f"  ❌ Tool execution failed: {result.error}\n")
    
    print("=" * 50)
    print("🎉 Done! That's how easy it is to use ArmorIQ SDK.")
    print("\n💡 Key Takeaway: No GCP setup required!")
    print("   - No service account JSON files")
    print("   - No KMS configuration")
    print("   - Just your API key!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check your API key at platform.armoriq.ai")
        print("   2. Ensure Weather MCP is running (python app.py)")
        print("   3. Verify endpoints are accessible")
