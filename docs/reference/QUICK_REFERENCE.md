# ArmorIQ SDK - Quick Reference Summary

**Version:** 0.1.1 | **Status:** Production Ready ✅ | **Date:** January 16, 2026

---

## 📋 Executive Summary

The **ArmorIQ SDK** enables developers to build **secure, auditable AI agents** with cryptographic proof of reasoning. Every action is automatically signed with Ed25519 and canonicalized using CSRG (Canonical Serializable Reasoning Graphs).

**In 3 Lines:**
```python
from armoriq_sdk import ArmorIQClient
client = ArmorIQClient(user_id="alice", agent_id="my-agent")
result = client.invoke("loan-mcp", "check_eligibility", {...})
# ✅ Automatic security, audit trails, and compliance!
```

---

## 🏗️ Architecture Flow

```
User Code
    ↓
ArmorIQ SDK (this package)
    ↓
    ├─→ ConMap Auto (api.armoriq.io) ────→ Agent/MCP Discovery
    ├─→ IAP (iap.armoriq.io) ────────────→ Token Issuance + Security
    ├─→ Proxy (cloud-run-proxy.armoriq.io) → Action Routing + Verification
    └─→ MCPs (various) ───────────────────→ Business Logic Execution
```

**What Happens:**
1. **Capture Plan** - SDK records what agent plans to do
2. **Get Token** - IAP issues cryptographic token (Ed25519 signed)
3. **Execute Action** - Proxy verifies token and routes to MCP
4. **Audit Trail** - Complete execution log with proofs

---

## 🚀 Core Capabilities

### 1. **Automatic Security** 🔒
- **Ed25519 Signatures** on every action
- **CSRG Canonicalization** for verification
- **Merkle Trees** for efficient proofs
- **Intent-Based Access** (actions must match plan)

### 2. **Agent-to-Agent Protocol** 🤝
```python
# Primary agent delegates to sub-agent
delegation_token = finance_agent.delegate(
    to_agent_id="risk-agent",
    capabilities=["calculate_risk"],
    expires_in=3600
)

# Sub-agent acts with delegated authority
risk_agent = ArmorIQClient(
    user_id="alice",
    agent_id="risk-agent",
    delegation_token=delegation_token
)
```

**Features:**
- Hierarchical trust chains
- Capability scoping
- Time-bounded delegations
- Complete authority tracing
- Revocation support

### 3. **MCP Protocol Integration** 🔌
```python
# Discover available MCPs
mcps = client.discover_mcps()

# Invoke any MCP tool
result = client.invoke("loan-mcp", "check_eligibility", {...})
```

**Features:**
- Auto-discovery through ConMap
- Dynamic routing via Proxy
- Schema validation
- Multi-MCP workflows
- Error recovery

### 4. **Reasoning Graph Capture** 🧠
```python
with client.capture_plan() as plan:
    plan.think("Analyzing loan application")
    plan.tool_call("credit-mcp", "check_score", {...})
    plan.observe("credit_score", "{{result.score}}")
    plan.tool_call("loan-mcp", "calculate_rate", {
        "score": "{{credit_score}}"
    })

# Get complete reasoning graph
graph = client.get_reasoning_graph(token)
```

**Features:**
- Complete thought process captured
- Conditional branches preserved
- Tool calls recorded
- Cryptographic proof of each step
- Visualization-ready JSON

### 5. **Complete Audit Trails** 📊
```python
# Get audit trail
audit = client.get_audit_trail(
    agent_id="loan-processor",
    start_date="2026-01-01",
    end_date="2026-01-16"
)
```

**Features:**
- Immutable logs (Merkle tree commitment)
- Time-ordered events
- Queryable by agent/time/action
- Compliance-ready
- Cryptographic proofs included

### 6. **Proof Generation** 📜
```python
# Generate proof for specific step
proof = client.generate_proof(
    intent_token=token,
    step_index=2
)

# Verify proof
is_valid = client.verify_proof(proof)

# Export for auditors
proof_json = proof.to_json()
```

### 7. **Policy Enforcement** ⚖️
```python
policy = {
    "allowed_mcps": ["loan-mcp", "credit-mcp"],
    "max_loan_amount": 100000,
    "requires_approval_above": 50000,
    "allowed_hours": "09:00-17:00"
}

client = ArmorIQClient(
    user_id="alice",
    agent_id="loan-processor",
    policy=policy
)
# IAP enforces policy automatically!
```

### 8. **ConMap Discovery** 🗺️
```python
# Register agent
client = ArmorIQClient(
    user_id="alice",
    agent_id="my-agent",
    capabilities=["loan_processing", "risk_assessment"],
    auto_register=True  # Registers with ConMap
)

# Discover other agents
agents = client.discover_agents(capability="risk_assessment")

# Discover MCPs
mcps = client.discover_mcps(category="finance")
```

---

## 🎯 What Makes ArmorIQ Unique?

| Feature | ArmorIQ SDK | Traditional APIs |
|---------|-------------|------------------|
| **Security** | Ed25519 + CSRG automatic | Manual implementation |
| **Audit** | Immutable Merkle tree logs | Optional logging |
| **Delegation** | Built-in agent-to-agent | Not supported |
| **Reasoning** | Complete graph captured | No tracking |
| **Compliance** | Cryptographic proofs | Manual records |
| **Multi-Agent** | Native collaboration | Custom protocols |

---

## 📖 Complete API Reference

### Client Initialization
```python
client = ArmorIQClient(
    user_id: str,              # Required
    agent_id: str,             # Required
    iap_endpoint: str = None,  # Default: https://iap.armoriq.io
    proxy_endpoint: str = None,# Default: https://cloud-run-proxy.armoriq.io
    conmap_endpoint: str = None,# Default: https://api.armoriq.io
    policy: Dict = None,       # Access control policy
    delegation_token: str = None,  # For sub-agents
    auto_register: bool = False,   # Register with ConMap
    capabilities: List[str] = None,# Agent capabilities
    retry_config: Dict = None  # Retry settings
)
```

### Plan Capture
```python
with client.capture_plan() as plan:
    plan.think(reasoning: str)
    plan.tool_call(mcp: str, tool: str, params: Dict)
    plan.observe(key: str, value: Any)
    plan.delegated_call(delegation_token: str, mcp: str, tool: str, params: Dict)
```

### Token Management
```python
token = client.get_intent_token(plan: PlanCapture = None)
client.refresh_token(token: str)
```

### Execution
```python
result = client.invoke(
    mcp_server: str,
    tool_name: str,
    parameters: Dict,
    intent_token: str = None
)

result = client.execute_plan(intent_token: str)
```

### Delegation
```python
delegation = client.delegate(
    to_agent_id: str,
    capabilities: List[str],
    expires_in: int = 3600,
    max_amount: float = None
)

client.revoke_delegation(delegation_id: str)
```

### Proofs & Audit
```python
proof = client.generate_proof(intent_token: str, step_index: int)
is_valid = client.verify_proof(proof: Dict)
graph = client.get_reasoning_graph(intent_token: str)
audit = client.get_audit_trail(
    agent_id: str = None,
    start_date: str = None,
    end_date: str = None,
    filters: Dict = None
)
```

### Discovery
```python
mcps = client.discover_mcps(category: str = None)
agents = client.discover_agents(capability: str = None)
```

### Lifecycle
```python
client.close()
```

---

## 🌟 Real-World Examples

### Financial Services
```python
loan_agent = ArmorIQClient(user_id="banker", agent_id="loan-processor")

with loan_agent.capture_plan() as plan:
    plan.think("Processing loan application")
    plan.tool_call("kyc-mcp", "verify_identity", {...})
    plan.tool_call("credit-mcp", "check_score", {...})
    plan.tool_call("loan-mcp", "approve_or_reject", {...})
    plan.tool_call("notification-mcp", "notify_customer", {...})

result = loan_agent.execute_plan()
proof = loan_agent.generate_proof(result.token)  # For compliance
```

### Travel Planning
```python
travel_agent = ArmorIQClient(user_id="user", agent_id="travel-planner")

# Delegate to specialized agents
flight_token = travel_agent.delegate("flight-agent", ["search", "book"])
hotel_token = travel_agent.delegate("hotel-agent", ["search", "book"])

# Sub-agents work independently within delegation bounds
```

### Healthcare
```python
care_agent = ArmorIQClient(user_id="doctor", agent_id="care-coordinator")

with care_agent.capture_plan() as plan:
    plan.think("Patient needs specialist referral")
    plan.tool_call("ehr-mcp", "get_patient_history", {...})
    plan.tool_call("specialist-mcp", "find_available", {...})
    plan.tool_call("scheduling-mcp", "book_appointment", {...})

# Complete HIPAA-compliant audit trail maintained automatically
```

---

## 🔐 Security Architecture

```
Plan → CSRG Canonicalize → Merkle Tree → Ed25519 Sign → Token

Action → Extract → Hash → Find in Merkle Tree → Verify Signature → Execute

✅ Every action cryptographically proven
✅ Cannot execute actions not in original plan
✅ Complete non-repudiation
✅ Tamper-proof audit trails
```

---

## 📦 Installation & Setup

```bash
# Install from GitHub
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v0.1.1

# Basic usage
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(user_id="alice", agent_id="my-agent")
# Production endpoints configured automatically!
```

---

## 🎯 Key Benefits

### For Developers
✅ **3 lines to get started**  
✅ **Production-ready defaults**  
✅ **Type-safe APIs**  
✅ **Comprehensive error handling**  
✅ **Automatic retries**  

### For Enterprises
✅ **Cryptographic proofs**  
✅ **Compliance-ready logs**  
✅ **Policy enforcement**  
✅ **Multi-agent collaboration**  
✅ **Complete audit trails**  

### For Users
✅ **Transparent actions**  
✅ **Explainable AI**  
✅ **Privacy protection**  
✅ **Trust through verification**  

---

## 📊 Production Status

| Component | Endpoint | Status |
|-----------|----------|--------|
| **IAP** | https://iap.armoriq.io | ✅ ONLINE |
| **Proxy** | https://cloud-run-proxy.armoriq.io | ✅ ONLINE |
| **ConMap** | https://api.armoriq.io | ✅ CONFIGURED |
| **SDK** | GitHub v0.1.1 | ✅ PUBLISHED |

---

## 📚 Documentation

- **Quick Start:** `QUICKSTART.md`
- **Full Capabilities:** `SDK_CAPABILITIES.md`
- **Visual Flow:** `FLOW_DIAGRAM.md`
- **Architecture:** `ARCHITECTURE.md`
- **Verification Report:** `VERIFICATION_REPORT.md`
- **API Reference:** `docs/api/`
- **Examples:** `examples/`

---

## 🎉 Summary

**ArmorIQ SDK v0.1.1** provides:

✅ **4 Core APIs**: ConMap, IAP, Proxy, MCP Protocol  
✅ **Agent-to-Agent Protocol**: Secure delegation & collaboration  
✅ **Cryptographic Security**: Ed25519 + CSRG + Merkle trees  
✅ **Complete Audit Trails**: Immutable, queryable, compliant  
✅ **Reasoning Graphs**: Capture and prove agent thinking  
✅ **Policy Enforcement**: Declarative access control  
✅ **Production Ready**: 8,805+ lines, 36 files, full documentation  

**Build secure, auditable, collaborative AI agents in minutes!**

---

**Homepage:** https://armoriq.ai  
**Support:** support@armoriq.io  
**GitHub:** https://github.com/armoriq/armoriq-sdk-python  
**Version:** 0.1.1 (January 16, 2026)
