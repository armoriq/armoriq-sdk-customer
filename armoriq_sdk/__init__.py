"""
ArmorIQ SDK - Build Secure AI Agents

A Python SDK for building AI agents with cryptographic intent verification.
Provides simple APIs for plan capture, token management, and secure MCP
tool invocation with built-in security.

Author: ArmorIQ Team <license@armoriq.io>
"""

from .client import ArmorIQClient
from .exceptions import (
    ArmorIQException,
    InvalidTokenException,
    IntentMismatchException,
    MCPInvocationException,
    TokenExpiredException,
)
from .models import IntentToken, PlanCapture, MCPInvocation, DelegationResult

__version__ = "0.2.1"
__author__ = "ArmorIQ Team"
__email__ = "license@armoriq.io"

__all__ = [
    "ArmorIQClient",
    "ArmorIQException",
    "InvalidTokenException",
    "IntentMismatchException",
    "MCPInvocationException",
    "TokenExpiredException",
    "IntentToken",
    "PlanCapture",
    "MCPInvocation",
    "DelegationResult",
]
