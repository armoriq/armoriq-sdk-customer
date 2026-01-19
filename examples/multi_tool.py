"""
ArmorIQ Customer SDK - Multi-Tool Example
========================================

Shows how to execute multiple tools in sequence using the same token.

This example:
1. Gets weather for multiple cities
2. Demonstrates proper error handling
3. Shows how to reuse tokens
"""

from armoriq import Client, Action
from armoriq.exceptions import ToolInvocationError, NetworkError

def main():
    print("🌍 Multi-City Weather Comparison\n")
    
    # Initialize client
    client = Client(
        user_id="developer123",
        api_key="demo-api-key",
        iap_endpoint="http://localhost:8082",
        proxy_endpoint="http://localhost:3001"
    )
    
    # Cities to check
    cities = ["Boston", "New York", "Los Angeles", "Chicago"]
    
    # Create plan for all cities
    print("Creating plan for multiple cities...")
    plan = client.create_plan(
        goal=f"Get weather for {len(cities)} cities",
        actions=[
            Action(
                tool="get_weather",
                params={"city": city},
                description=f"Get weather for {city}"
            )
            for city in cities
        ]
    )
    
    # Get token once (reusable for all actions in the plan)
    print("Getting access token...\n")
    token = client.get_token(plan)
    
    # Execute each action
    results = {}
    for city in cities:
        try:
            print(f"📍 Checking weather in {city}...")
            
            result = client.call(
                mcp="weather-mcp",
                tool="get_weather",
                params={"city": city},
                token=token
            )
            
            if result.success:
                results[city] = result.data
                print(f"   ✅ {result.data}")
            else:
                print(f"   ❌ Failed: {result.error}")
                
        except ToolInvocationError as e:
            print(f"   ❌ Tool error: {e.message}")
        except NetworkError as e:
            print(f"   ❌ Network error: {e.message}")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Successfully fetched weather for {len(results)}/{len(cities)} cities")
    
    if results:
        print(f"\n🌡️  Results:")
        for city, data in results.items():
            print(f"   {city}: {data}")


if __name__ == "__main__":
    main()
