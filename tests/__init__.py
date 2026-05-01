"""
Test ArmorIQ SDK package exports.
"""

from armoriq_sdk import (
    __version__,
    ArmorIQClient,
    ArmorIQException,
    InvalidTokenException,
    IntentMismatchException,
    MCPInvocationException,
    TokenExpiredException,
    IntentToken,
    PlanCapture,
    MCPInvocation,
    DelegationResult,
)


def test_version():
    """Package __version__ is defined and matches a semver-like shape."""
    import re
    assert __version__
    assert re.match(r"^\d+\.\d+\.\d+", __version__), __version__


def test_client_exported():
    """Test ArmorIQClient is exported."""
    assert ArmorIQClient is not None


def test_exceptions_exported():
    """Test all exceptions are exported."""
    assert ArmorIQException is not None
    assert InvalidTokenException is not None
    assert IntentMismatchException is not None
    assert MCPInvocationException is not None
    assert TokenExpiredException is not None


def test_models_exported():
    """Test all models are exported."""
    assert IntentToken is not None
    assert PlanCapture is not None
    assert MCPInvocation is not None
    assert DelegationResult is not None
