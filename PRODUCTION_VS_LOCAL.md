# ArmorIQ SDK - Production vs Local Development

## 🚀 Production Mode (Default)

Connects to your deployed ArmorIQ services.

### Endpoints
- **IAP**: `https://customer-iap.armoriq.ai`
- **Proxy**: `https://customer-proxy.armoriq.ai`
- **Dashboard**: `https://platform.armoriq.ai`

### Usage

```python
from armoriq_sdk import ArmorIQClient

# Option 1: Explicit production (default)
client = ArmorIQClient(
    api_key="ak_live_394a3b12...",  # Live API key from dashboard
    user_id="developer@company.com",
    agent_id="my-production-agent"
    # use_production=True is default
)

# Option 2: Using environment variables
# export ARMORIQ_API_KEY="ak_live_394a3b12..."
# export USER_ID="developer@company.com"
# export AGENT_ID="my-production-agent"
client = ArmorIQClient()  # Auto-uses production
```

### When to Use
- ✅ Deploying to production
- ✅ Testing with real data
- ✅ Customer-facing applications
- ✅ CI/CD pipelines

---

## 🏠 Local Development Mode

Connects to services running on your local machine.

### Endpoints
- **IAP**: `http://localhost:8080`
- **Proxy**: `http://localhost:3001`
- **ConMap Auto**: `http://localhost:3000`
- **Frontend**: `http://localhost:5173`

### Usage

```python
from armoriq_sdk import ArmorIQClient

# Option 1: Explicit local mode
client = ArmorIQClient(
    api_key="ak_test_local123...",  # Test API key
    user_id="dev@localhost",
    agent_id="my-dev-agent",
    use_production=False  # 👈 Use local endpoints
)

# Option 2: Environment variable
# export ARMORIQ_ENV=development
# export ARMORIQ_API_KEY="ak_test_local123..."
client = ArmorIQClient()  # Auto-uses localhost
```

### Prerequisites for Local Mode

1. **Start all services:**
   ```bash
   # Terminal 1: ConMap Auto Customer (port 3000)
   cd conmap-auto-customer
   npm run start:dev
   
   # Terminal 2: Proxy Server Customer (port 3001)
   cd armoriq-proxy-server-customer
   npm run start:dev
   
   # Terminal 3: CSRG IAP Customer (port 8080)
   cd csrg-iap-customer
   ~/anaconda3/bin/python -m uvicorn csrg_iap.main:app --host 0.0.0.0 --port 8080
   
   # Terminal 4: Frontend (port 5173)
   cd armoriq-frontend-customer
   npm run dev
   ```

2. **Create local API key:**
   - Go to http://localhost:5173
   - Create an API key in the dashboard
   - Use it in your SDK

### When to Use
- ✅ Developing new features
- ✅ Testing changes locally
- ✅ Debugging issues
- ✅ No internet connection needed

---

## 🔄 Switching Between Modes

### Method 1: Code Parameter
```python
# Production
prod_client = ArmorIQClient(use_production=True)

# Local
local_client = ArmorIQClient(use_production=False)
```

### Method 2: Environment Variable
```bash
# Production
export ARMORIQ_ENV=production
python my_agent.py

# Local
export ARMORIQ_ENV=development
python my_agent.py
```

### Method 3: Explicit Endpoints
```python
# Custom staging environment
client = ArmorIQClient(
    proxy_endpoint="https://staging-proxy.armoriq.ai",
    iap_endpoint="https://staging-iap.armoriq.ai",
    api_key="ak_staging_..."
)
```

---

## 📊 Comparison

| Feature | Production | Local |
|---------|-----------|-------|
| **Endpoints** | customer-*.armoriq.ai | localhost:* |
| **API Keys** | Live keys (ak_live_...) | Test keys (ak_test_...) |
| **Token Signing** | GCP KMS (secure) | Local Ed25519 |
| **Database** | Cloud PostgreSQL | Local PostgreSQL |
| **SSL/HTTPS** | Yes | No |
| **Setup Required** | None (just API key) | All services locally |
| **Best For** | Real customers | Development/testing |

---

## 🧪 Complete Test Example

```python
#!/usr/bin/env python3
"""
Test SDK in both production and local modes
"""
import os
from armoriq_sdk import ArmorIQClient

def test_production():
    """Test with production endpoints"""
    print("🚀 Testing Production Mode")
    client = ArmorIQClient(
        api_key=os.getenv("ARMORIQ_API_KEY_PROD"),
        user_id="test@production.com",
        agent_id="prod-test-agent",
        use_production=True
    )
    
    plan = client.capture_plan("gpt-4", "Test production", 
                               plan={"goal": "Test", "steps": []})
    token = client.get_intent_token(plan)
    print(f"✅ Production token: {token.token_id}")
    client.close()

def test_local():
    """Test with local endpoints"""
    print("🏠 Testing Local Mode")
    client = ArmorIQClient(
        api_key=os.getenv("ARMORIQ_API_KEY_LOCAL"),
        user_id="test@localhost",
        agent_id="local-test-agent",
        use_production=False
    )
    
    plan = client.capture_plan("gpt-4", "Test local",
                               plan={"goal": "Test", "steps": []})
    token = client.get_intent_token(plan)
    print(f"✅ Local token: {token.token_id}")
    client.close()

if __name__ == "__main__":
    # Test production
    if os.getenv("ARMORIQ_API_KEY_PROD"):
        test_production()
    else:
        print("⚠️  Skipping production test (no ARMORIQ_API_KEY_PROD)")
    
    # Test local
    if os.getenv("ARMORIQ_API_KEY_LOCAL"):
        test_local()
    else:
        print("⚠️  Skipping local test (no ARMORIQ_API_KEY_LOCAL)")
```

---

## 🎯 Best Practices

1. **Use different API keys for each environment**
   - Production: `ak_live_...` (from platform.armoriq.ai)
   - Local: `ak_test_...` (from localhost:5173)

2. **Set environment variables**
   ```bash
   # .env.production
   ARMORIQ_ENV=production
   ARMORIQ_API_KEY=ak_live_...
   
   # .env.local
   ARMORIQ_ENV=development
   ARMORIQ_API_KEY=ak_test_...
   ```

3. **Never commit API keys**
   - Add `.env*` to `.gitignore`
   - Use secrets management in production

4. **Test locally first**
   - Develop with `use_production=False`
   - Test with production once stable
   - Deploy with confidence

---

## 📝 Quick Reference

```python
# ✅ Production (customer-facing)
ArmorIQClient(use_production=True)   # Default
ArmorIQClient()                       # Same as above

# ✅ Local (development)
ArmorIQClient(use_production=False)  # Localhost
os.environ["ARMORIQ_ENV"] = "development"

# ✅ Custom (staging, etc.)
ArmorIQClient(
    proxy_endpoint="https://custom.example.com",
    iap_endpoint="https://custom-iap.example.com"
)
```
