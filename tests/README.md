# ArmorIQ SDK Tests

This directory contains the test suite for the ArmorIQ SDK.

## Directory Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_client.py           # Unit tests for ArmorIQClient
├── test_exceptions.py       # Unit tests for exceptions
├── test_models.py           # Unit tests for data models
├── integration/             # Integration tests (not in git)
├── production/              # Production endpoint tests (not in git)
└── examples/                # Example usage tests (not in git)
```

## Running Tests

### Unit Tests (in repository)

```bash
# Run all unit tests
pytest tests/

# Run specific test file
pytest tests/test_client.py

# Run with coverage
pytest tests/ --cov=armoriq_sdk --cov-report=html
```

### Integration Tests (local only)

Integration tests require local services running:
- CSRG-IAP on port 8082
- ArmorIQ Proxy on port 3001
- MCP servers on their respective ports

```bash
# Run integration tests
pytest tests/integration/

# Run specific integration test
pytest tests/integration/test_complete_flow.py
```

### Production Tests (local only)

Production tests verify connectivity to live services:

```bash
# Test production endpoints
pytest tests/production/test_actual_production.py

# Test production configuration
pytest tests/production/test_production_endpoints.py
```

## Test Organization

### Unit Tests (Included in Git)
- `test_client.py` - Core client functionality
- `test_exceptions.py` - Exception handling
- `test_models.py` - Data model validation

These tests:
- ✅ Run without external services
- ✅ Fast execution
- ✅ Part of CI/CD pipeline
- ✅ Included in repository

### Integration Tests (Excluded from Git)
Located in `tests/integration/` - require running services:
- `test_complete_flow.py` - End-to-end flow testing
- `test_direct_verification.py` - Direct service communication
- `test_integration.py` - Service integration tests
- `test_config.py` - Configuration validation
- And more...

These tests:
- ⚠️ Require local services running
- ⚠️ Slower execution
- ⚠️ Not in CI/CD (service dependencies)
- ⚠️ Excluded from git (in .gitignore)

### Production Tests (Excluded from Git)
Located in `tests/production/` - test live production endpoints:
- `test_actual_production.py` - Production service verification
- `test_production_endpoints.py` - Endpoint connectivity tests

These tests:
- ⚠️ Hit live production services
- ⚠️ May incur costs or rate limits
- ⚠️ Not in CI/CD
- ⚠️ Excluded from git (in .gitignore)

### Example Tests (Excluded from Git)
Located in `tests/examples/` - demonstrate SDK usage:
- `test_real_user_example.py` - Real-world usage examples

These tests:
- 📚 Educational/documentation purpose
- 📚 Show complete workflows
- ⚠️ Excluded from git (in .gitignore)

## Writing Tests

### Unit Test Example

```python
import pytest
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.exceptions import ConfigurationException

def test_client_initialization():
    """Test basic client initialization."""
    client = ArmorIQClient(
        user_id="test-user",
        agent_id="test-agent"
    )
    assert client.user_id == "test-user"
    assert client.agent_id == "test-agent"
    client.close()

def test_missing_user_id():
    """Test that missing user_id raises exception."""
    with pytest.raises(ConfigurationException):
        ArmorIQClient(agent_id="test-agent")
```

### Integration Test Example

```python
import pytest
from armoriq_sdk import ArmorIQClient

@pytest.mark.integration
def test_end_to_end_flow():
    """Test complete SDK flow with local services."""
    client = ArmorIQClient(
        iap_endpoint="http://localhost:8082",
        proxy_endpoint="http://localhost:3001",
        user_id="test-user",
        agent_id="test-agent"
    )
    
    # Capture plan
    plan = client.capture_plan("gpt-4", "Test action")
    
    # Get token
    token = client.get_intent_token(plan)
    assert token is not None
    
    # Invoke action
    result = client.invoke("test-mcp", "test-action", token)
    assert result.status == "success"
    
    client.close()
```

## Test Requirements

Install test dependencies:

```bash
pip install -e ".[dev]"
```

Or manually:

```bash
pip install pytest pytest-cov pytest-asyncio httpx
```

## CI/CD Integration

Only unit tests are run in CI/CD:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: pytest tests/test_*.py --cov=armoriq_sdk
```

Integration and production tests must be run manually in appropriate environments.

## Test Coverage

Current coverage (unit tests only):

```bash
pytest tests/test_*.py --cov=armoriq_sdk --cov-report=term-missing
```

Target: 80%+ coverage for core functionality

## Debugging Tests

```bash
# Verbose output
pytest tests/ -v

# Show print statements
pytest tests/ -s

# Stop on first failure
pytest tests/ -x

# Run specific test
pytest tests/test_client.py::test_client_initialization

# Debug with pdb
pytest tests/ --pdb
```

## Notes

- Integration tests are excluded from git to keep the repo clean
- They're kept locally for development and manual testing
- Production tests should never be automated (cost/rate limit concerns)
- Always clean up resources (use `client.close()` or context managers)
