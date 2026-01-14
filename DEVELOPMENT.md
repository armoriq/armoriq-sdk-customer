# ArmorIQ SDK Development Guide

## Project Structure

```
armoriq-sdk-python/
├── armoriq_sdk/           # Main SDK package
│   ├── __init__.py        # Package exports
│   ├── client.py          # ArmorIQClient class
│   ├── models.py          # Pydantic data models
│   └── exceptions.py      # Custom exceptions
├── examples/              # Example scripts
│   ├── basic_agent.py     # Basic usage example
│   ├── multi_mcp_agent.py # Multi-MCP coordination
│   ├── delegation_example.py # Agent delegation
│   └── error_handling.py  # Error handling patterns
├── tests/                 # Unit tests
│   ├── test_client.py     # Client tests
│   ├── test_models.py     # Model tests
│   └── test_exceptions.py # Exception tests
├── pyproject.toml         # Project configuration
├── README.md              # User documentation
└── DEVELOPMENT.md         # This file
```

## Development Setup

### Prerequisites

- Python 3.9+
- `uv` package manager
- Running CSRG-IAP instance (for integration tests)
- Running ArmorIQ Proxy instance (for integration tests)

### Initial Setup

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
cd armoriq-sdk-python
uv sync

# Run tests
uv run pytest
```

## Development Workflow

### 1. Making Changes

```bash
# Edit code in armoriq_sdk/
vim armoriq_sdk/client.py

# Format code
uv run black armoriq_sdk tests

# Type check
uv run mypy armoriq_sdk

# Lint
uv run ruff check armoriq_sdk
```

### 2. Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=armoriq_sdk --cov-report=html

# Run specific test file
uv run pytest tests/test_client.py

# Run specific test
uv run pytest tests/test_client.py::TestClientInitialization::test_client_creation_with_all_params

# Run with verbose output
uv run pytest -v

# Run integration tests (requires services running)
uv run pytest -m integration
```

### 3. Testing Examples

```bash
# Run basic example
uv run python examples/basic_agent.py

# Run multi-MCP example
uv run python examples/multi_mcp_agent.py

# Run delegation example
uv run python examples/delegation_example.py
```

## Testing Against Real Services

### Start Required Services

1. **CSRG-IAP Service** (Port 8000)
```bash
cd ../csrg-iap
uv run python -m csrg_iap.main
```

2. **ArmorIQ Proxy Server** (Port 3001)
```bash
cd ../armoriq-proxy-server
npm run start:dev
```

### Run Integration Tests

```bash
# Set environment variables
export IAP_ENDPOINT=http://localhost:8000
export USER_ID=test_user
export AGENT_ID=test_agent

# Run integration tests
uv run pytest tests/integration/ -v
```

## API Development Guidelines

### Adding a New API Method

1. **Define the method in `client.py`:**
```python
def new_method(self, param: str) -> ResultType:
    """
    Brief description.
    
    Args:
        param: Description
        
    Returns:
        Description
        
    Raises:
        ExceptionType: Description
    """
    # Implementation
    pass
```

2. **Add corresponding model in `models.py`:**
```python
class NewMethodResult(BaseModel):
    """Result from new_method."""
    field: str = Field(..., description="Description")
```

3. **Add tests in `tests/test_client.py`:**
```python
class TestNewMethod:
    """Test new_method functionality."""
    
    def test_new_method_success(self, client):
        """Test successful case."""
        # Test implementation
        pass
```

4. **Add example in `examples/`:**
```python
# examples/new_method_example.py
# Demonstrate usage
```

5. **Update exports in `__init__.py`:**
```python
from .models import NewMethodResult

__all__ = [..., "NewMethodResult"]
```

## Code Style

### Python Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use type hints for all function signatures
- Write docstrings for all public methods (Google style)

### Example Code Style

```python
def example_method(
    self,
    required_param: str,
    optional_param: Optional[int] = None,
) -> ExampleResult:
    """
    Brief one-line description.
    
    Longer description if needed. Can span multiple lines
    and include details about the method's purpose.
    
    Args:
        required_param: Description of required parameter
        optional_param: Description of optional parameter
        
    Returns:
        ExampleResult with fields described here
        
    Raises:
        ValueError: When required_param is invalid
        ExampleException: When something specific fails
        
    Example:
        >>> result = client.example_method("test")
        >>> print(result.field)
    """
    # Implementation
    pass
```

## Testing Guidelines

### Unit Test Structure

```python
class TestFeature:
    """Test feature functionality."""
    
    def test_success_case(self, client, sample_data):
        """Test successful operation."""
        result = client.method(sample_data)
        assert result.field == expected_value
    
    def test_error_case(self, client):
        """Test error handling."""
        with pytest.raises(ExpectedException):
            client.method(invalid_data)
```

### Mock External Services

```python
@patch("armoriq_sdk.client.httpx.Client")
def test_with_mock(mock_http):
    """Test with mocked HTTP client."""
    mock_response = Mock()
    mock_response.json.return_value = {"data": "test"}
    mock_http.return_value.post.return_value = mock_response
    
    # Test code
```

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = ArmorIQClient(...)
# Now all SDK operations will log debug info
```

### Using ipdb

```python
# Add breakpoint in code
import ipdb; ipdb.set_trace()

# Run test with debugging
uv run pytest --pdb
```

## Release Process

1. **Update version in `pyproject.toml`**
2. **Update CHANGELOG.md**
3. **Run full test suite:**
   ```bash
   uv run pytest
   uv run pytest --cov=armoriq_sdk
   ```
4. **Build package:**
   ```bash
   uv build
   ```
5. **Publish to PyPI:**
   ```bash
   uv publish
   ```

## Common Issues

### Import Errors

If you see import errors, ensure dependencies are installed:
```bash
uv sync
```

### Test Failures

Check that required services are running for integration tests.

### Type Checking Errors

Run mypy to see detailed type errors:
```bash
uv run mypy armoriq_sdk
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run full test suite
5. Submit pull request

## Resources

- [CSRG-IAP Documentation](../csrg-iap/README.md)
- [ArmorIQ Proxy Documentation](../armoriq-proxy-server/README.md)
- [Architecture Diagram](../Architecture.pdf)
