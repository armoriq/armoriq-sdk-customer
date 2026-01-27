"""
ArmorIQ Customer SDK - Simplified Client
Clean, user-friendly API for building MCPs without complexity

NO GCP credentials required - works with just an API key!
Perfect for hackathons, demos, and rapid prototyping.
"""

import requests
from typing import Dict, List, Any, Optional
from .models import Plan, Action, Token, ToolResult
from .exceptions import (
    AuthenticationError,
    ToolInvocationError,
    PlanError,
    NetworkError
)


class Client:
    """
    ArmorIQ Client for simple MCP integration
    
    Example:
        ```python
        from armoriq import Client, Action
        
        # Initialize client
        client = Client(
            user_id="developer123",
            api_key="your-api-key"
        )
        
        # Create a plan
        plan = client.create_plan(
            goal="Get weather for Boston",
            actions=[
                Action(
                    tool="get_weather",
                    params={"city": "Boston"}
                )
            ]
        )
        
        # Get token
        token = client.get_token(plan)
        
        # Call tool
        result = client.call(
            mcp="weather-mcp",
            tool="get_weather",
            params={"city": "Boston"},
            token=token
        )
        
        print(result.data)
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        user_id: Optional[str] = None,
        iap_endpoint: str = "https://iap.armoriq.io",
        proxy_endpoint: str = "https://proxy.armoriq.io",
        environment: str = "production"
    ):
        """
        Initialize ArmorIQ Client
        
        SIMPLIFIED: No GCP credentials, no KMS, no service accounts!
        Just provide your API key and you're ready to go.
        
        Args:
            api_key: Your API key from ArmorIQ dashboard (https://dashboard.armoriq.io)
            user_id: Optional user identifier (auto-generated if not provided)
            iap_endpoint: ArmorIQ IAP service endpoint (default: production)
            proxy_endpoint: ArmorIQ Proxy endpoint (default: production)
            environment: "production", "staging", or "local" (auto-configures endpoints)
            
        Examples:
            # Production (default)
            >>> client = Client(api_key="your-api-key")
            
            # Local development
            >>> client = Client(
            ...     api_key="dev-key",
            ...     environment="local"
            ... )
            
            # Custom endpoints
            >>> client = Client(
            ...     api_key="your-key",
            ...     iap_endpoint="http://localhost:8082",
            ...     proxy_endpoint="http://localhost:3001"
            ... )
        """
        self.api_key = api_key
        
        # Auto-generate user_id if not provided
        if user_id is None:
            import uuid
            self.user_id = f"customer_{uuid.uuid4().hex[:8]}"
        else:
            self.user_id = user_id
        
        # Auto-configure endpoints based on environment
        if environment == "local":
            self.iap_endpoint = "http://localhost:8082"
            self.proxy_endpoint = "http://localhost:3001"
        elif environment == "staging":
            self.iap_endpoint = "https://iap-staging.armoriq.io"
            self.proxy_endpoint = "https://proxy-staging.armoriq.io"
        else:  # production
            self.iap_endpoint = iap_endpoint.rstrip('/')
            self.proxy_endpoint = proxy_endpoint.rstrip('/')
        
        # Set default headers (API key authentication only)
        self._headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-ArmorIQ-SDK": "customer-python/1.0.0"
        }
    
    def create_plan(
        self,
        goal: str,
        actions: List[Action]
    ) -> Plan:
        """
        Create an execution plan
        
        Args:
            goal: What you want to accomplish
            actions: List of Action objects defining the tools to call
            
        Returns:
            Plan object
            
        Example:
            ```python
            plan = client.create_plan(
                goal="Get weather for multiple cities",
                actions=[
                    Action(tool="get_weather", params={"city": "Boston"}),
                    Action(tool="get_weather", params={"city": "NYC"})
                ]
            )
            ```
        """
        if not actions:
            raise PlanError("Plan must contain at least one action")
        
        return Plan(goal=goal, actions=actions)
    
    def get_token(self, plan: Plan, expires_in: int = 3600) -> Token:
        """
        Get an access token for executing a plan
        
        SIMPLIFIED: No GCP service accounts, no KMS configuration!
        The backend handles all security with your API key.
        
        Args:
            plan: The plan to execute
            expires_in: Token expiration in seconds (default: 1 hour)
            
        Returns:
            Token object ready to use with call()
            
        Raises:
            AuthenticationError: If API key is invalid
            PlanError: If plan is invalid
            NetworkError: If request fails
            
        Note:
            The token is cryptographically signed by ArmorIQ's backend.
            You don't need to provide any keys or credentials!
        """
        try:
            # Build request payload - NO GCP CONFIG NEEDED!
            payload = {
                "user_id": self.user_id,
                "agent_id": f"customer_{self.user_id}",
                "context_id": "default",
                "plan": plan.to_dict(),
                "policy": {
                    "allow": [action.tool for action in plan.actions],
                    "deny": [],
                    "metadata": {
                        "inject_iam_context": False,  # Customer SDK doesn't use IAM
                        "sdk_version": "customer-1.0.0",
                        "sdk_type": "customer"
                    }
                },
                "expires_in": expires_in
            }
            
            # Request token from IAP (backend handles all crypto)
            response = requests.post(
                f"{self.iap_endpoint}/token/issue",
                json=payload,
                headers=self._headers,
                timeout=10
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            
            if response.status_code != 200:
                error_msg = response.json().get('error', 'Unknown error')
                raise PlanError(f"Token issuance failed: {error_msg}")
            
            data = response.json()
            
            return Token(
                token_string=data.get('token'),
                expires_at=data.get('expires_at'),
                plan_id=plan.plan_id
            )
            
        except requests.exceptions.Timeout:
            raise NetworkError(self.iap_endpoint, "Request timed out")
        except requests.exceptions.ConnectionError:
            raise NetworkError(self.iap_endpoint, "Could not connect to server")
        except Exception as e:
            if isinstance(e, (AuthenticationError, PlanError, NetworkError)):
                raise
            raise PlanError(f"Unexpected error: {str(e)}")
    
    def call(
        self,
        mcp: str,
        tool: str,
        params: Dict[str, Any],
        token: Token
    ) -> ToolResult:
        """
        Call a tool on an MCP
        
        Args:
            mcp: MCP identifier (e.g., "weather-mcp")
            tool: Tool name (e.g., "get_weather")
            params: Tool parameters as dictionary
            token: Access token from get_token()
            
        Returns:
            ToolResult object with success status and data
            
        Raises:
            ToolInvocationError: If tool execution fails
            NetworkError: If request fails
            
        Example:
            ```python
            result = client.call(
                mcp="weather-mcp",
                tool="get_weather",
                params={"city": "Boston"},
                token=token
            )
            
            if result.success:
                print(result.data)
            else:
                print(f"Error: {result.error}")
            ```
        """
        try:
            # Build request payload
            payload = {
                "mcp": mcp,
                "action": tool,
                "params": params
            }
            
            # Add token to headers
            headers = {
                **self._headers,
                "Authorization": f"Bearer {token.token_string}"
            }
            
            # Call tool via proxy
            response = requests.post(
                f"{self.proxy_endpoint}/api/invoke",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Parse response
            if response.status_code == 200:
                data = response.json()
                return ToolResult(
                    success=True,
                    data=data.get('result', data),
                    tool_name=tool
                )
            else:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
                return ToolResult(
                    success=False,
                    data=None,
                    error=error_msg,
                    tool_name=tool
                )
                
        except requests.exceptions.Timeout:
            raise NetworkError(self.proxy_endpoint, "Request timed out")
        except requests.exceptions.ConnectionError:
            raise NetworkError(self.proxy_endpoint, "Could not connect to server")
        except Exception as e:
            if isinstance(e, NetworkError):
                raise
            raise ToolInvocationError(tool, str(e))
    
    def execute_plan(self, plan: Plan) -> List[ToolResult]:
        """
        Execute all actions in a plan sequentially
        
        Args:
            plan: The plan to execute
            
        Returns:
            List of ToolResult objects, one per action
            
        Example:
            ```python
            results = client.execute_plan(plan)
            for i, result in enumerate(results):
                print(f"Action {i+1}: {result.success}")
            ```
        """
        # Get token for plan
        token = self.get_token(plan)
        
        # Execute each action
        results = []
        for action in plan.actions:
            # Note: MCP name needs to be provided somehow
            # For now, we'll raise an error suggesting to use call() directly
            raise NotImplementedError(
                "execute_plan() requires MCP routing logic. "
                "Please use call() method directly for now."
            )
        
        return results
