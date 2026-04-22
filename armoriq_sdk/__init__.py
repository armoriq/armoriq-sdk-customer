"""
ArmorIQ SDK - Build Secure AI Agents

A Python SDK for building AI agents with cryptographic intent verification.
Provides simple APIs for plan capture, token management, and secure MCP
tool invocation with built-in security.

Author: ArmorIQ Team <license@armoriq.io>
"""

from .client import ArmorIQClient
from .session import (
    ArmorIQSession,
    EnforceResult,
    ReportOptions,
    SessionMode,
    SessionOptions,
)
from .plan_builder import (
    ToolNameParser,
    build_plan_from_tool_calls,
    default_tool_name_parser,
    hash_tool_calls,
)
from .exceptions import (
    ArmorIQException,
    ConfigurationException,
    DelegationException,
    IntentMismatchException,
    InvalidTokenException,
    MCPInvocationException,
    PolicyBlockedException,
    PolicyHoldException,
    TokenExpiredException,
)
from .models import (
    ApprovedDelegation,
    DelegationRequest,
    DelegationRequestParams,
    DelegationRequestResult,
    DelegationResult,
    HoldInfo,
    IntentToken,
    InvokeOptions,
    MCPInvocation,
    MCPInvocationResult,
    MCPSemanticMetadata,
    McpCredential,
    McpCredentialMap,
    PlanCapture,
    PolicyContext,
    SDKConfig,
    ToolCall,
    ToolSemanticEntry,
)

__version__ = "0.3.2"
VERSION = __version__
__author__ = "ArmorIQ Team"
AUTHOR = __author__
__email__ = "license@armoriq.io"
EMAIL = __email__

__all__ = [
    # Core
    "ArmorIQClient",
    "ArmorIQSession",
    "SessionOptions",
    "SessionMode",
    "EnforceResult",
    "ReportOptions",
    # Plan helpers
    "build_plan_from_tool_calls",
    "default_tool_name_parser",
    "hash_tool_calls",
    "ToolNameParser",
    # Exceptions
    "ArmorIQException",
    "InvalidTokenException",
    "IntentMismatchException",
    "MCPInvocationException",
    "TokenExpiredException",
    "DelegationException",
    "ConfigurationException",
    "PolicyBlockedException",
    "PolicyHoldException",
    # Models
    "IntentToken",
    "PlanCapture",
    "MCPInvocation",
    "MCPInvocationResult",
    "DelegationRequest",
    "DelegationResult",
    "SDKConfig",
    "MCPSemanticMetadata",
    "ToolSemanticEntry",
    "PolicyContext",
    "InvokeOptions",
    "HoldInfo",
    "DelegationRequestParams",
    "DelegationRequestResult",
    "ApprovedDelegation",
    "ToolCall",
    "McpCredential",
    "McpCredentialMap",
    # Metadata
    "VERSION",
    "AUTHOR",
    "EMAIL",
]

# Optional framework integrations (each requires its own extra to be installed)
try:
    from .integrations import (
        ArmorIQAnthropic,
        ArmorIQCrew,
        ArmorIQGoogleADK,
        ArmorIQLangChain,
        ArmorIQOpenAI,
    )
    __all__ += [
        "ArmorIQCrew",
        "ArmorIQLangChain",
        "ArmorIQGoogleADK",
        "ArmorIQOpenAI",
        "ArmorIQAnthropic",
    ]
except Exception:
    pass
