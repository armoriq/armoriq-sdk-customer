"""
Custom exceptions for ArmorIQ SDK.
"""


class ArmorIQException(Exception):
    """Base exception for all ArmorIQ SDK errors."""

    pass


class InvalidTokenException(ArmorIQException):
    """
    Raised when an intent token is invalid.
    
    This can occur due to:
    - Invalid signature
    - Token expiration
    - Token revocation
    - Malformed token structure
    """

    def __init__(self, message: str, token_id: str = None):
        super().__init__(message)
        self.token_id = token_id


class IntentMismatchException(ArmorIQException):
    """
    Raised when an action doesn't match the original intent plan.
    
    This occurs when trying to execute an action that was not
    included in the canonicalized plan used to generate the token.
    """

    def __init__(self, message: str, action: str = None, plan_hash: str = None):
        super().__init__(message)
        self.action = action
        self.plan_hash = plan_hash


class TokenExpiredException(InvalidTokenException):
    """
    Raised when an intent token has expired.
    
    Tokens have a validity period set during issuance.
    This exception is raised when attempting to use an expired token.
    """

    def __init__(self, message: str, token_id: str = None, expired_at: float = None):
        super().__init__(message, token_id)
        self.expired_at = expired_at


class MCPInvocationException(ArmorIQException):
    """
    Raised when an MCP action invocation fails.
    
    This can occur due to:
    - MCP server unavailable
    - Action not found
    - Invalid parameters
    - Proxy verification failure
    """

    def __init__(
        self, message: str, mcp: str = None, action: str = None, status_code: int = None
    ):
        super().__init__(message)
        self.mcp = mcp
        self.action = action
        self.status_code = status_code


class DelegationException(ArmorIQException):
    """
    Raised when agent delegation fails.
    
    This can occur due to:
    - Target agent unavailable
    - Trust delegation rejected
    - Invalid subtask structure
    """

    def __init__(self, message: str, target_agent: str = None):
        super().__init__(message)
        self.target_agent = target_agent


class ConfigurationException(ArmorIQException):
    """
    Raised when SDK configuration is invalid.
    
    This can occur due to:
    - Missing required configuration
    - Invalid endpoint URLs
    - Missing credentials
    """

    pass
