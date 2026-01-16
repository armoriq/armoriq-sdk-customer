# ArmorIQ SDK - Complete Capabilities Overview

**ArmorIQ SDK v0.1.1**  
**Date:** January 16, 2026  
**Status:** Production Ready ✅

---

## 🎯 What is ArmorIQ SDK?

The ArmorIQ SDK is a **Python library that enables developers to build secure, auditable AI agents** with cryptographic proof of reasoning. It provides automatic security through Ed25519 signatures and CSRG (Canonical Serializable Reasoning Graphs) for every action.

**In Simple Terms:** Build AI agents that can prove what they did, why they did it, and that they were authorized to do it.

---

## 🏗️ Complete Architecture Flow

### 1. User Builds an Agent

```python
from armoriq_sdk import ArmorIQClient

# Initialize client
client = ArmorIQClient(
    user_id="alice@company.com",
    agent_id="finance-agent",
    # Production endpoints configured automatically!
)

# Agent decides what to do
with client.capture_plan() as plan:
    plan.think("User wants to check loan eligibility")
    plan.tool_call("loan-mcp", "check_eligibility", {
        "customer_id": "CUST_001",
        "amount": 50000
    })

# Get cryptographic token
token = client.get_intent_token()
```

### 2. SDK → IAP (Intent Authorization Platform)

**What Happens:**
```
SDK sends plan to: https://iap.armoriq.io/intent

IAP Process:
├─ Receives the reasoning plan
├─ Applies CSRG canonicalization (creates standard form)
├─ Generates Merkle tree of all steps
├─ Creates Ed25519 signature
└─ Returns Intent Token (cryptographically signed proof)
```

**Result:** Your agent now has a **cryptographic proof** of what it planned to do.

### 3. SDK → Proxy (Action Verification & Routing)

**What Happens:**
```
SDK sends action + token to: https://cloud-run-proxy.armoriq.io/invoke

Proxy Process:
├─ Receives token + action request
├─ Verifies Ed25519 signature with IAP
├─ Checks if action matches the original plan
├─ Validates permissions and policies
├─ Routes to the correct MCP server
└─ Returns result with audit trail
```

**Result:** Action is executed **only if it matches the plan** and is properly authorized.

### 4. Proxy → MCP (Model Context Protocol Server)

**What Happens:**
```
Proxy forwards validated request to MCP

MCP Process:
├─ Receives verified request from proxy
├─ Executes business logic (check loan, book flight, etc.)
├─ Returns structured result
└─ Result flows back through proxy to SDK
```

**Result:** Business logic executes securely with complete audit trail.

---

## 🚀 Core Capabilities

### 1. **Automatic Security** 🔒

**What You Get:**
- **Ed25519 Signatures**: Every action cryptographically signed
- **CSRG Canonicalization**: Plans normalized for verification
- **Merkle Trees**: Efficient proof of reasoning steps
- **Intent-Based Access**: Actions must match declared intent

**Why It Matters:**
```python
# You write simple code:
client.invoke("loan-mcp", "approve_loan", {"amount": 10000})

# SDK automatically:
✅ Canonicalizes the request
✅ Gets cryptographic token
✅ Verifies with IAP
✅ Creates audit trail
✅ Proves authorization
```

### 2. **Multi-Agent Collaboration** 🤝

**Agent-to-Agent Protocol:**

```python
# Finance Agent delegates to Risk Agent
finance_agent = ArmorIQClient(
    user_id="alice",
    agent_id="finance-agent"
)

# Create delegation token
delegation_token = finance_agent.delegate(
    to_agent_id="risk-assessment-agent",
    capabilities=["calculate_risk_score", "check_credit"],
    expires_in=3600  # 1 hour
)

# Risk Agent can now act on behalf of Finance Agent
risk_agent = ArmorIQClient(
    user_id="alice",
    agent_id="risk-assessment-agent",
    delegation_token=delegation_token  # Uses delegated authority
)

# All actions trace back to original authority
result = risk_agent.invoke("risk-mcp", "calculate_score", {...})
```

**Delegation Features:**
- ✅ **Hierarchical Trust**: Agents can delegate to sub-agents
- ✅ **Capability Scoping**: Limit what delegated agent can do
- ✅ **Time-Bounded**: Delegations expire automatically
- ✅ **Audit Trail**: Complete chain of authority preserved
- ✅ **Revocation**: Cancel delegations anytime

**Real-World Example:**
```
Travel Planning Agent
├─ Delegates to Flight Booking Agent
│  └─ Books flights within budget
├─ Delegates to Hotel Booking Agent
│  └─ Books hotels in approved locations
└─ Delegates to Payment Agent
   └─ Processes payments within limits

All actions traceable back to original user authorization!
```

### 3. **MCP Protocol Integration** 🔌

**Connect to Any MCP Server:**

```python
# SDK automatically discovers and connects to MCPs
mcps = client.discover_mcps()

# Invoke tools on any MCP
result = client.invoke(
    mcp_server_url="https://loan-mcp.company.com",
    tool_name="check_eligibility",
    parameters={"customer_id": "123"}
)
```

**MCP Features:**
- ✅ **Auto-Discovery**: Find available MCPs through ConMap
- ✅ **Dynamic Routing**: Proxy routes to correct MCP
- ✅ **Schema Validation**: Parameters validated automatically
- ✅ **Error Handling**: Graceful fallbacks and retries
- ✅ **Multi-MCP Workflows**: Chain multiple MCPs together

### 4. **Reasoning Graph Capture** 🧠

**Track Agent's Thinking:**

```python
with client.capture_plan() as plan:
    # Capture reasoning steps
    plan.think("User wants loan information")
    
    # Branch based on conditions
    if loan_amount > 100000:
        plan.think("Large loan, need extra approval")
        plan.tool_call("approval-mcp", "request_manager_approval", {...})
    
    # Call multiple tools
    plan.tool_call("credit-mcp", "check_score", {...})
    plan.tool_call("loan-mcp", "calculate_rate", {...})
    plan.tool_call("notification-mcp", "send_email", {...})

# Get full reasoning graph
graph = client.get_reasoning_graph(intent_token)
```

**Graph Features:**
- ✅ **Complete History**: Every reasoning step captured
- ✅ **Conditional Logic**: Branches and decisions preserved
- ✅ **Tool Calls**: All MCP invocations recorded
- ✅ **Merkle Proof**: Cryptographic proof of each step
- ✅ **Visualization Ready**: Export to JSON for UI display

### 5. **ConMap Auto Integration** 🗺️

**Automatic Agent Registration:**

```python
# SDK automatically registers your agent
client = ArmorIQClient(
    user_id="alice",
    agent_id="finance-agent",
    capabilities=["loan_processing", "risk_assessment"],
    auto_register=True  # Registers with ConMap
)

# Your agent is now discoverable!
# Other agents can find and delegate to it
```

**ConMap Features:**
- ✅ **Agent Directory**: All agents discoverable
- ✅ **Capability Discovery**: Find agents by what they can do
- ✅ **MCP Registry**: Directory of all MCP servers
- ✅ **Health Monitoring**: Track agent availability
- ✅ **Load Balancing**: Route to available instances

### 6. **Proof Generation** 📜

**Generate Cryptographic Proofs:**

```python
# Generate proof for specific step
proof = client.generate_proof(
    intent_token=token,
    step_index=2,  # Prove step 2 was in original plan
    include_merkle_path=True
)

# Verify proof independently
is_valid = client.verify_proof(proof)

# Export for auditing
proof_json = proof.to_json()
```

**Proof Features:**
- ✅ **Merkle Path**: Cryptographic proof of inclusion
- ✅ **Ed25519 Signature**: Unforgeable signatures
- ✅ **Timestamped**: All proofs include timestamps
- ✅ **Exportable**: JSON format for auditors
- ✅ **Non-Repudiation**: Agent cannot deny actions

### 7. **Audit Trail** 📊

**Complete Execution History:**

```python
# Get audit trail for all actions
audit = client.get_audit_trail(
    agent_id="finance-agent",
    start_date="2026-01-01",
    end_date="2026-01-16"
)

# Audit includes:
# - All plans created
# - All tokens issued
# - All actions executed
# - All delegations created
# - Complete reasoning graphs
# - Cryptographic proofs
```

**Audit Features:**
- ✅ **Immutable Log**: Cannot be altered after creation
- ✅ **Merkle Tree Commitment**: Cryptographic proof of integrity
- ✅ **Time-Ordered**: Chronological event sequence
- ✅ **Queryable**: Filter by agent, time, action type
- ✅ **Compliance Ready**: Meets regulatory requirements

---

## 🎨 Advanced Features

### 8. **Policy Enforcement** ⚖️

**Declarative Access Control:**

```python
# Define what agent can do
policy = {
    "agent_id": "finance-agent",
    "allowed_mcps": ["loan-mcp", "credit-mcp"],
    "max_loan_amount": 100000,
    "requires_approval_above": 50000,
    "allowed_hours": "09:00-17:00",
    "allowed_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}

client = ArmorIQClient(
    user_id="alice",
    agent_id="finance-agent",
    policy=policy
)

# IAP enforces policy automatically:
# ❌ Rejects actions outside allowed hours
# ❌ Rejects actions to non-allowed MCPs
# ❌ Rejects amounts exceeding limits
```

### 9. **Multi-Step Workflows** 🔄

**Chain Multiple Actions:**

```python
with client.capture_plan() as plan:
    # Step 1: Check credit
    plan.tool_call("credit-mcp", "check_score", {"customer_id": "123"})
    plan.observe("credit_score", "{{result.score}}")
    
    # Step 2: Calculate rate (depends on credit score)
    plan.tool_call("loan-mcp", "calculate_rate", {
        "credit_score": "{{credit_score}}",
        "amount": 50000
    })
    plan.observe("interest_rate", "{{result.rate}}")
    
    # Step 3: Generate offer
    plan.tool_call("offer-mcp", "create_offer", {
        "rate": "{{interest_rate}}",
        "term": 60
    })

# Execute entire workflow with single token
result = client.execute_plan()
```

### 10. **Error Recovery & Retries** 🔄

**Automatic Fault Tolerance:**

```python
client = ArmorIQClient(
    user_id="alice",
    agent_id="finance-agent",
    retry_config={
        "max_retries": 3,
        "backoff_factor": 2,
        "retry_on": [500, 502, 503, 504],
        "timeout": 30
    }
)

# SDK automatically:
# ✅ Retries failed requests
# ✅ Implements exponential backoff
# ✅ Handles timeouts gracefully
# ✅ Preserves audit trail of retries
```

### 11. **Development vs Production** 🔧

**Easy Testing:**

```python
# Production (default)
prod_client = ArmorIQClient(
    user_id="alice",
    agent_id="finance-agent"
    # Uses https://iap.armoriq.io automatically
)

# Development (local testing)
dev_client = ArmorIQClient(
    user_id="alice",
    agent_id="finance-agent",
    iap_endpoint="http://localhost:8082",
    proxy_endpoint="http://localhost:3001"
)

# Environment variable override
# export ARMORIQ_ENV=development
# SDK automatically uses localhost!
```

---

## 🌟 Real-World Use Cases

### Use Case 1: Financial Services

```python
# Loan Processing Agent
loan_agent = ArmorIQClient(user_id="banker", agent_id="loan-processor")

with loan_agent.capture_plan() as plan:
    plan.think("Processing loan application for customer")
    
    # Step 1: Verify identity
    plan.tool_call("kyc-mcp", "verify_identity", {"customer_id": "..."})
    
    # Step 2: Check credit (delegate to credit agent)
    credit_token = loan_agent.delegate("credit-agent", ["check_score"])
    plan.delegated_call(credit_token, "credit-mcp", "check_score", {...})
    
    # Step 3: Risk assessment (delegate to risk agent)
    risk_token = loan_agent.delegate("risk-agent", ["calculate_risk"])
    plan.delegated_call(risk_token, "risk-mcp", "assess_risk", {...})
    
    # Step 4: Make decision
    plan.tool_call("decision-mcp", "approve_or_reject", {...})
    
    # Step 5: Notify customer
    plan.tool_call("notification-mcp", "send_decision", {...})

# Execute with full audit trail
result = loan_agent.execute_plan()

# Generate proof for compliance
proof = loan_agent.generate_proof(result.token)
```

### Use Case 2: Travel Planning

```python
# Travel Agent coordinates multiple sub-agents
travel_agent = ArmorIQClient(user_id="user", agent_id="travel-planner")

# Delegate to specialized agents
flight_token = travel_agent.delegate("flight-agent", ["search", "book"])
hotel_token = travel_agent.delegate("hotel-agent", ["search", "book"])
payment_token = travel_agent.delegate("payment-agent", ["charge"], max_amount=5000)

# Each agent works independently but within delegation bounds
# All actions trace back to original user authorization
```

### Use Case 3: Healthcare

```python
# Patient Care Coordinator
care_agent = ArmorIQClient(user_id="doctor", agent_id="care-coordinator")

with care_agent.capture_plan() as plan:
    plan.think("Patient needs specialist referral")
    
    # HIPAA-compliant audit trail automatically maintained
    plan.tool_call("ehr-mcp", "get_patient_history", {"patient_id": "..."})
    plan.tool_call("specialist-mcp", "find_available", {"specialty": "cardiology"})
    plan.tool_call("scheduling-mcp", "book_appointment", {...})
    plan.tool_call("insurance-mcp", "verify_coverage", {...})

# Complete audit trail for regulatory compliance
audit = care_agent.get_audit_trail()
```

---

## 📚 API Summary

### Core APIs

| API | Purpose | Endpoint |
|-----|---------|----------|
| **ConMap Auto** | Agent & MCP discovery | `https://api.armoriq.io` |
| **CSRG-IAP** | Intent token issuance | `https://iap.armoriq.io` |
| **Proxy** | Action verification & routing | `https://cloud-run-proxy.armoriq.io` |
| **MCP Protocol** | Tool execution | Various MCP servers |

### SDK Methods

```python
# Initialization
client = ArmorIQClient(user_id, agent_id, **kwargs)

# Plan Capture
with client.capture_plan() as plan:
    plan.think(reasoning)
    plan.tool_call(mcp, tool, params)
    plan.observe(key, value)

# Token Management
token = client.get_intent_token(plan)
client.refresh_token(token)

# Execution
result = client.invoke(mcp, tool, params, token)
result = client.execute_plan(token)

# Delegation
delegation = client.delegate(to_agent, capabilities, expires_in)
client.revoke_delegation(delegation_id)

# Proofs & Audit
proof = client.generate_proof(token, step_index)
valid = client.verify_proof(proof)
graph = client.get_reasoning_graph(token)
audit = client.get_audit_trail(filters)

# Discovery
mcps = client.discover_mcps()
agents = client.discover_agents(capability)

# Lifecycle
client.close()
```

---

## 🎯 Key Differentiators

### What Makes ArmorIQ SDK Unique?

1. **Cryptographic Proof of Reasoning** 🔐
   - Every action has unforgeable proof
   - Merkle trees for efficient verification
   - Ed25519 signatures for security

2. **Intent-Based Access Control** 🎫
   - Declare what you plan to do
   - Get token for that specific plan
   - Cannot execute anything else with that token

3. **Agent-to-Agent Protocol** 🤝
   - Secure delegation between agents
   - Hierarchical trust chains
   - Complete authority tracing

4. **Built-in Compliance** 📋
   - Immutable audit trails
   - Regulatory-ready logging
   - Exportable proofs for auditors

5. **Developer Friendly** 💻
   - 3 lines to get started
   - Production-ready defaults
   - Comprehensive error handling

---

## 🚀 Getting Started

### Installation

```bash
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v0.1.1
```

### Hello World

```python
from armoriq_sdk import ArmorIQClient

# Initialize
client = ArmorIQClient(
    user_id="your-user-id",
    agent_id="my-first-agent"
)

# Create a plan
with client.capture_plan() as plan:
    plan.think("Checking loan eligibility")
    plan.tool_call("loan-mcp", "check_eligibility", {
        "customer_id": "CUST_001",
        "amount": 25000
    })

# Execute with automatic security
result = client.execute_plan()

print(f"Result: {result.data}")
print(f"Token: {result.token}")
print(f"Proof: {result.proof}")

client.close()
```

**That's it!** You now have:
- ✅ Cryptographic proof of reasoning
- ✅ Secure action execution
- ✅ Complete audit trail
- ✅ Compliance-ready logs

---

## 📖 Documentation

- **Quick Start:** `QUICKSTART.md`
- **Architecture:** `ARCHITECTURE.md`
- **API Reference:** `docs/api/`
- **Examples:** `examples/`
- **Deployment:** `docs/deployment/`

---

## 🎉 Summary

The ArmorIQ SDK provides:

✅ **4 Core APIs**: ConMap, IAP, Proxy, MCP Protocol  
✅ **Agent-to-Agent Protocol**: Secure delegation & collaboration  
✅ **Cryptographic Security**: Ed25519 + CSRG + Merkle trees  
✅ **Complete Audit Trails**: Immutable, queryable, compliant  
✅ **MCP Integration**: Connect to any Model Context Protocol server  
✅ **Reasoning Graphs**: Capture and prove agent thinking  
✅ **Policy Enforcement**: Declarative access control  
✅ **Production Ready**: Used in finance, healthcare, travel, and more  

**Build secure, auditable, collaborative AI agents in minutes!**

---

**ArmorIQ SDK v0.1.1** - January 16, 2026  
**Homepage:** https://armoriq.ai  
**Support:** support@armoriq.io
