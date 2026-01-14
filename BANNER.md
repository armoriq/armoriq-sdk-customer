```
   ___                             ______ ____
  / _ | ______ _  ___  ____  ____/  _/ /_/ __/   ____ ____
 / __ |/ __/  ' \/ _ \/ __/ / / _/ / / _ \_\ \  / __// __ \
/_/ |_/_/ /_/_/_/\___/_/ /_/_/ /___/\___/___/ /_/  /_/ /_/
                                                           
        Python SDK for Intent-Based Agent Development
                    with CSRG-IAP Integration
```

# ArmorIQ SDK

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-yellow.svg)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

> **Intent Assurance for AI Agents** - Secure, auditable, and verifiable agent actions

---

## 🎯 What is ArmorIQ SDK?

ArmorIQ SDK provides a **simple 4-method API** for building AI agents that use the **Canonical Structured Reasoning Graph (CSRG)** Intent Assurance Plane (IAP) for secure action execution.

**The Problem**: AI agents need to execute actions securely with clear intent verification.

**The Solution**: ArmorIQ SDK provides:
- ✅ **Plan Canonicalization** - Deterministic plan hashing
- ✅ **Intent Tokens** - Signed, time-bound authorization
- ✅ **Token Verification** - Automatic validation before execution
- ✅ **Audit Trail** - Complete action history

---

## 🚀 Quick Start (30 seconds)

```bash
# Install
pip install armoriq-sdk

# Use
from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(
    iap_endpoint="https://iap.example.com",
    user_id="user123",
    agent_id="my-agent"
)

# 1. Capture plan
plan = client.capture_plan("gpt-4", "Book flight to Paris")

# 2. Get token
token = client.get_intent_token(plan)

# 3. Execute
result = client.invoke("travel-mcp", "book_flight", token)
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [📖 README](README.md) | Complete user guide |
| [⚡ QUICKSTART](QUICKSTART.md) | 5-minute getting started |
| [🏗️ ARCHITECTURE](ARCHITECTURE.md) | System design & flows |
| [👨‍💻 DEVELOPMENT](DEVELOPMENT.md) | Developer guidelines |
| [📊 REPORT](IMPLEMENTATION_REPORT.md) | Implementation details |
| [📝 CHANGELOG](CHANGELOG.md) | Version history |

---

## 🎓 Examples

Explore working examples in [`examples/`](examples/):

- **basic_agent.py** - Simple usage pattern
- **multi_mcp_agent.py** - Coordinate multiple MCPs
- **delegation_example.py** - Agent-to-agent delegation
- **error_handling.py** - Error recovery patterns

---

## 🏗️ Architecture

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Agent      │────▶│  ArmorIQ    │────▶│    IAP       │
│  (Your Code) │     │    SDK      │     │  (CSRG)      │
└──────────────┘     └─────────────┘     └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Proxy      │────▶ MCPs
                    │  (Verify)    │
                    └──────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams.

---

## ✨ Features

### Core Features
- ✅ 4 simple APIs: `capture_plan()`, `get_intent_token()`, `invoke()`, `delegate()`
- ✅ Type-safe with Pydantic models
- ✅ Token caching with expiry
- ✅ Automatic retry logic
- ✅ Comprehensive error handling

### Security
- ✅ CSRG plan canonicalization
- ✅ Ed25519 token signing
- ✅ Automatic token verification
- ✅ Intent matching validation
- ✅ Append-only audit trail

### Developer Experience
- ✅ Full test coverage (40+ tests)
- ✅ Extensive documentation
- ✅ Working examples
- ✅ Environment config
- ✅ Context manager support

---

## 📦 Installation

### From PyPI (when published)
```bash
pip install armoriq-sdk
```

### From Source
```bash
git clone https://github.com/armoriq/armoriq-sdk-python
cd armoriq-sdk-python
./setup.sh
```

---

## 🧪 Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=armoriq_sdk

# Quick verification
./test.sh
```

---

## 🤝 Contributing

Contributions welcome! See [DEVELOPMENT.md](DEVELOPMENT.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🔗 Related Projects

- **CSRG-IAP**: Intent Assurance Plane service
- **ArmorIQ Proxy**: MCP routing and verification
- **Conmap Auto**: Configuration management

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/armoriq/armoriq-sdk-python/issues)
- **Docs**: [Full Documentation](README.md)
- **Examples**: [Working Examples](examples/)

---

<div align="center">

**Built with ❤️ for the ArmorIQ Platform**

[Documentation](README.md) • [Quickstart](QUICKSTART.md) • [Architecture](ARCHITECTURE.md) • [Examples](examples/)

</div>
