"""
Simplified exceptions for ArmorIQ Customer SDK
User-friendly error messages without exposing internal details
"""


class ArmorIQError(Exception):
    """Base exception for all ArmorIQ SDK errors"""
    pass


class AuthenticationError(ArmorIQError):
    """Raised when authentication fails"""
    
    def __init__(self, message="Authentication failed. Please check your API key."):
        self.message = message
        super().__init__(self.message)


class ToolInvocationError(ArmorIQError):
    """Raised when tool invocation fails"""
    
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = f"Tool '{tool_name}' failed: {message}"
        super().__init__(self.message)


class PlanError(ArmorIQError):
    """Raised when plan creation/validation fails"""
    
    def __init__(self, message: str):
        self.message = f"Plan error: {message}"
        super().__init__(self.message)


class NetworkError(ArmorIQError):
    """Raised when network communication fails"""
    
    def __init__(self, endpoint: str, message: str):
        self.endpoint = endpoint
        self.message = f"Network error connecting to {endpoint}: {message}"
        super().__init__(self.message)
