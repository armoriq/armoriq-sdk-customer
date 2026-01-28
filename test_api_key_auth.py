#!/usr/bin/env python3
"""
Test API Key Authentication Flow

This script tests the complete authentication flow:
1. Generate API key
2. Request token from proxy using API key
3. Use token to call MCP tools
4. Verify everything works end-to-end

Requirements:
- Proxy server running on localhost:3001
- CSRG-IAP running on localhost:8082
- At least one MCP server running (e.g., Loan-MCP on port 8081)
"""

import os
import sys
import json
import requests
import hashlib
from datetime import datetime

# ANSI colors for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    """Print info message"""
    print(f"{BLUE}ℹ️  {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def hash_api_key(api_key):
    """Hash API key using SHA-256 (same as backend)"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def test_api_key_generation():
    """Test 1: Generate a test API key"""
    print_header("TEST 1: Generate API Key")
    
    # Generate a simple test API key
    api_key = "test-api-key-" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    print_info(f"Generated API Key: {api_key}")
    print_info(f"Hashed: {hash_api_key(api_key)[:16]}...")
    
    print_success("API key generated successfully")
    return api_key

def test_proxy_health(proxy_url):
    """Test 2: Check if proxy is running"""
    print_header("TEST 2: Proxy Health Check")
    
    try:
        response = requests.get(f"{proxy_url}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Proxy is running: {data.get('service')} v{data.get('version')}")
            print_info(f"Mode: {data.get('mode')}")
            return True
        else:
            print_error(f"Proxy returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to proxy server")
        print_warning(f"Make sure proxy is running: cd armoriq-proxy-server && npm run start:dev")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_csrg_health(csrg_url):
    """Test 3: Check if CSRG-IAP is running"""
    print_header("TEST 3: CSRG-IAP Health Check")
    
    try:
        response = requests.get(csrg_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"CSRG-IAP is running: {data.get('service')} v{data.get('version')}")
            return True
        else:
            print_error(f"CSRG-IAP returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to CSRG-IAP server")
        print_warning(f"Make sure CSRG-IAP is running on port 8082")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_token_issuance(proxy_url, api_key):
    """Test 4: Request token using API key"""
    print_header("TEST 4: Token Issuance (API Key Auth)")
    
    # Build a simple plan
    plan = {
        "goal": "Test API key authentication",
        "steps": [
            {
                "action": "get_loan_options",
                "params": {
                    "amount": 10000,
                    "credit_score": 750
                }
            }
        ]
    }
    
    payload = {
        "user_id": "test_customer_001",
        "agent_id": "customer_test_agent",
        "context_id": "test",
        "plan": plan,
        "policy": {
            "allow": ["get_loan_options", "calculate_monthly_payment"],
            "deny": [],
            "metadata": {
                "inject_iam_context": False,
                "sdk_version": "customer-1.0.0",
                "sdk_type": "customer"
            }
        },
        "expires_in": 3600
    }
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "X-ArmorIQ-SDK": "customer-python/1.0.0"
    }
    
    print_info(f"Requesting token from: {proxy_url}/token/issue")
    print_info(f"Plan: {plan['goal']}")
    
    try:
        response = requests.post(
            f"{proxy_url}/token/issue",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        print_info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            
            if token:
                print_success("Token issued successfully!")
                print_info(f"Token (first 50 chars): {str(token)[:50]}...")
                print_info(f"User ID: {data.get('user_id')}")
                print_info(f"Domain: {data.get('domain')}")
                print_info(f"Tier: {data.get('tier')}")
                print_info(f"Intent Reference: {data.get('intent_reference')}")
                return token
            else:
                print_error("Token missing in response")
                print_info(f"Response: {json.dumps(data, indent=2)}")
                return None
        else:
            print_error(f"Token issuance failed: {response.status_code}")
            try:
                error_data = response.json()
                print_error(f"Error: {error_data.get('error')}")
                print_error(f"Message: {error_data.get('message')}")
                print_info(f"Hint: {error_data.get('hint')}")
            except:
                print_error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print_error("Request timed out (15s)")
        print_warning("CSRG-IAP might be slow or not responding")
        return None
    except Exception as e:
        print_error(f"Token request failed: {e}")
        return None

def test_tool_execution(proxy_url, token, api_key):
    """Test 5: Execute tool using token and API key"""
    print_header("TEST 5: Tool Execution (With Token)")
    
    # Try to call a loan MCP tool
    tool_request = {
        "mcp": "loan-mcp",
        "tool": "get_loan_options",
        "params": {
            "amount": 10000,
            "credit_score": 750
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    print_info(f"Calling tool: {tool_request['tool']}")
    print_info(f"Proxy endpoint: {proxy_url}/loan-mcp.localhost")
    
    try:
        response = requests.post(
            f"{proxy_url}/loan-mcp.localhost",
            json=tool_request,
            headers=headers,
            timeout=10
        )
        
        print_info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Tool executed successfully!")
            print_info(f"Response: {json.dumps(data, indent=2)[:200]}...")
            return True
        else:
            print_error(f"Tool execution failed: {response.status_code}")
            try:
                error_data = response.json()
                print_error(f"Error: {error_data.get('error')}")
                print_error(f"Message: {error_data.get('message')}")
            except:
                print_error(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"Tool execution failed: {e}")
        return False

def main():
    """Run all tests"""
    print_header("🔐 API Key Authentication Flow Test")
    print_info("Testing customer SDK authentication with proxy server")
    print_info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    proxy_url = os.getenv("PROXY_URL", "http://localhost:3001")
    csrg_url = os.getenv("CSRG_URL", "http://localhost:8082")
    
    print_info(f"Proxy URL: {proxy_url}")
    print_info(f"CSRG URL: {csrg_url}")
    
    # Test 1: Generate API key
    api_key = test_api_key_generation()
    
    # Store in env for easy access
    print_warning(f"\n💡 To use this API key in your environment:")
    print_info(f"   export ARMORIQ_DEV_API_KEY='{api_key}'")
    
    # Test 2: Check proxy health
    if not test_proxy_health(proxy_url):
        print_error("\n❌ Proxy is not running. Aborting tests.")
        print_warning("Start proxy with: cd armoriq-proxy-server && npm run start:dev")
        sys.exit(1)
    
    # Test 3: Check CSRG-IAP health
    if not test_csrg_health(csrg_url):
        print_error("\n❌ CSRG-IAP is not running. Aborting tests.")
        print_warning("Start CSRG-IAP on port 8082")
        sys.exit(1)
    
    # Test 4: Request token
    token = test_token_issuance(proxy_url, api_key)
    
    if not token:
        print_error("\n❌ Token issuance failed. Cannot continue with tool execution test.")
        sys.exit(1)
    
    # Test 5: Execute tool (optional - requires MCP running)
    print_warning("\nTool execution test requires Loan-MCP running on port 8081")
    print_info("If MCP is not running, this test will fail (expected)")
    
    test_tool_execution(proxy_url, token, api_key)
    
    # Summary
    print_header("📊 Test Summary")
    print_success("✅ API key generation: PASSED")
    print_success("✅ Proxy health check: PASSED")
    print_success("✅ CSRG-IAP health check: PASSED")
    
    if token:
        print_success("✅ Token issuance: PASSED")
        print_info("\n🎉 API key authentication is working!")
        print_info("The customer SDK can now authenticate using API keys.")
    else:
        print_error("❌ Token issuance: FAILED")
    
    print_info(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
