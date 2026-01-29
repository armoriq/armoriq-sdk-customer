"""
ArmorIQ SDK Client - Main entry point for SDK usage.
"""

import os
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime

import httpx

# Optional CSRG-IAP imports
try:
    from csrg_iap.core.csrg import CanonicalStructuredReasoningGraph
    from csrg_iap.core.intent import IntentCommit
    from csrg_iap.core.crypto import Ed25519PrivateKey
    CSRG_AVAILABLE = True
except ImportError:
    CSRG_AVAILABLE = False
    # Create placeholder types for type hints
    CanonicalStructuredReasoningGraph = None
    IntentCommit = None
    Ed25519PrivateKey = None

from .models import (
    IntentToken,
    PlanCapture,
    MCPInvocation,
    MCPInvocationResult,
    DelegationRequest,
    DelegationResult,
    SDKConfig,
)
from .exceptions import (
    InvalidTokenException,
    IntentMismatchException,
    MCPInvocationException,
    DelegationException,
    TokenExpiredException,
    ConfigurationException,
)

logger = logging.getLogger(__name__)


class ArmorIQClient:
    """
    Main client for ArmorIQ SDK.
    
    Provides high-level APIs for:
    - Plan capture and canonicalization
    - Intent token management
    - MCP action invocation
    - Agent delegation
    
    Example:
        >>> # Production (default endpoints)
        >>> client = ArmorIQClient(
        ...     user_id="user123",
        ...     agent_id="my-agent"
        ... )
        >>> 
        >>> # Development/Local
        >>> client = ArmorIQClient(
        ...     iap_endpoint="http://localhost:8082",
        ...     proxy_endpoint="http://localhost:3001",
        ...     user_id="user123",
        ...     agent_id="my-agent"
        ... )
        >>> 
        >>> plan = client.capture_plan("gpt-4", "Book a flight to Paris")
        >>> token = client.get_intent_token(plan)
        >>> result = client.invoke("travel-mcp", "book_flight", token)
    """
    
    # Production endpoints (default) - Customer-facing services
    DEFAULT_IAP_ENDPOINT = "https://customer-iap.armoriq.ai"  # CSRG-IAP (Ed25519 tokens)
    DEFAULT_PROXY_ENDPOINT = "https://customer-proxy.armoriq.ai"  # Proxy server (validation only)
    DEFAULT_BACKEND_ENDPOINT = "https://customer-api.armoriq.ai"  # Backend (IAP token issuance)
    
    # Local development endpoints
    LOCAL_IAP_ENDPOINT = "http://localhost:8080"  # Local CSRG-IAP
    LOCAL_PROXY_ENDPOINT = "http://localhost:3001"  # Local proxy
    LOCAL_BACKEND_ENDPOINT = "http://localhost:3000"  # Local Backend (conmap-auto)

    def __init__(
        self,
        iap_endpoint: Optional[str] = None,
        proxy_endpoint: Optional[str] = None,
        backend_endpoint: Optional[str] = None,
        proxy_endpoints: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        context_id: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True,
        api_key: Optional[str] = None,
        use_production: bool = True,
    ):
        """
        Initialize ArmorIQ client.
        
        The SDK supports both production and local development modes:
        
        **Production Mode (default):**
        - IAP: https://customer-iap.armoriq.ai
        - Proxy: https://customer-proxy.armoriq.ai
        - ConMap: https://customer-api.armoriq.ai
        
        **Local Development Mode:**
        - IAP: http://localhost:8080
        - Proxy: http://localhost:3001
        - ConMap: http://localhost:3000
        
        Args:
            iap_endpoint: IAP service endpoint URL (overrides defaults)
            proxy_endpoint: Default proxy endpoint URL (overrides defaults)
            proxy_endpoints: Dict mapping MCP names to specific proxy URLs
            user_id: User identifier (or USER_ID env var)
            agent_id: Agent identifier (or AGENT_ID env var)
            context_id: Optional context identifier
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            verify_ssl: Whether to verify SSL certificates
            api_key: API key for authentication (required)
            use_production: Use production endpoints (default: True). Set False for local development.
            
        Raises:
            ConfigurationException: If required configuration is missing
            
        Environment Variables:
            ARMORIQ_API_KEY: API key for authentication (required)
            USER_ID: User identifier (required if not passed as arg)
            AGENT_ID: Agent identifier (required if not passed as arg)
            CONTEXT_ID: Context identifier (default: "default")
            ARMORIQ_ENV: Set to "development" to use local endpoints
            IAP_ENDPOINT: Override IAP endpoint
            PROXY_ENDPOINT: Override default proxy endpoint
            
        Examples:
            >>> # Production (default)
            >>> client = ArmorIQClient(
            ...     api_key="ak_live_...",
            ...     user_id="dev@company.com",
            ...     agent_id="my-agent"
            ... )
            
            >>> # Local development
            >>> client = ArmorIQClient(
            ...     api_key="ak_test_...",
            ...     user_id="dev@company.com",
            ...     agent_id="my-agent",
            ...     use_production=False
            ... )
            
            >>> # Or use environment variable
            >>> # export ARMORIQ_ENV=development
            >>> client = ArmorIQClient()
        """
        # Determine if using production based on environment
        env_mode = os.getenv("ARMORIQ_ENV", "production").lower()
        use_prod = use_production and (env_mode == "production")
        
        # Load IAP endpoint (priority: parameter > env var > default production/local)
        if iap_endpoint:
            self.iap_endpoint = iap_endpoint
        elif os.getenv("IAP_ENDPOINT"):
            self.iap_endpoint = os.getenv("IAP_ENDPOINT")
        elif use_prod:
            # Production: Use customer-facing CSRG-IAP
            self.iap_endpoint = self.DEFAULT_IAP_ENDPOINT
        else:
            # Local development
            self.iap_endpoint = self.LOCAL_IAP_ENDPOINT
        
        # Load proxy endpoint (for action validation only)
        if proxy_endpoint:
            self.default_proxy_endpoint = proxy_endpoint
        elif os.getenv("PROXY_ENDPOINT"):
            self.default_proxy_endpoint = os.getenv("PROXY_ENDPOINT")
        elif use_prod:
            # Production: Use customer-facing proxy
            self.default_proxy_endpoint = self.DEFAULT_PROXY_ENDPOINT
        else:
            # Local development
            self.default_proxy_endpoint = self.LOCAL_PROXY_ENDPOINT
        
        # Load backend endpoint (for token issuance - IAP calls go through backend)
        if backend_endpoint:
            self.backend_endpoint = backend_endpoint
        elif os.getenv("BACKEND_ENDPOINT"):
            self.backend_endpoint = os.getenv("BACKEND_ENDPOINT")
        elif use_prod:
            # Production: Use customer-facing backend
            self.backend_endpoint = self.DEFAULT_BACKEND_ENDPOINT
        else:
            # Local development
            self.backend_endpoint = self.LOCAL_BACKEND_ENDPOINT
        
        # Load user/agent identifiers
        self.user_id = user_id or os.getenv("USER_ID")
        self.agent_id = agent_id or os.getenv("AGENT_ID")
        self.context_id = context_id or os.getenv("CONTEXT_ID", "default")
        self.api_key = api_key or os.getenv("ARMORIQ_API_KEY")

        # Validate required config
        if not self.api_key:
            raise ConfigurationException(
                "API key is required for Customer SDK. "
                "Set ARMORIQ_API_KEY environment variable or pass api_key parameter. "
                "Get your API key from https://platform.armoriq.ai/dashboard/api-keys"
            )
        
        # Validate API key format (ak_live_ or ak_test_ prefix)
        if not (self.api_key.startswith("ak_live_") or self.api_key.startswith("ak_test_")):
            raise ConfigurationException(
                f"Invalid API key format. API keys must start with 'ak_live_' or 'ak_test_'. "
                f"Get your API key from https://platform.armoriq.ai/dashboard/api-keys"
            )
        
        if not self.user_id:
            raise ConfigurationException("user_id is required (set USER_ID env var)")
        if not self.agent_id:
            raise ConfigurationException("agent_id is required (set AGENT_ID env var)")

        self.proxy_endpoints = proxy_endpoints or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

        # Initialize HTTP client
        headers = {"User-Agent": f"ArmorIQ-SDK/0.1.0 (agent={self.agent_id})"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.http_client = httpx.Client(
            timeout=timeout,
            verify=verify_ssl,
            headers=headers,
            follow_redirects=True,
        )

        # Token cache
        self._token_cache: Dict[str, IntentToken] = {}

        logger.info(
            f"ArmorIQ SDK initialized: mode={'production' if use_prod else 'development'}, "
            f"user={self.user_id}, agent={self.agent_id}, "
            f"iap={self.iap_endpoint}, proxy={self.default_proxy_endpoint}, "
            f"backend={self.backend_endpoint}, "
            f"api_key={'***' + self.api_key[-8:] if self.api_key else 'None'}"
        )
        
        # Validate API key with proxy on initialization
        self._validate_api_key()

    @property
    def proxy_endpoint(self) -> str:
        """Get the default proxy endpoint URL."""
        return self.default_proxy_endpoint
    
    def _validate_api_key(self):
        """
        Validate API key with the proxy server.
        This is called during initialization to ensure the API key is valid.
        """
        try:
            # Make a simple health check with the API key
            headers = {"X-API-Key": self.api_key}
            response = self.http_client.get(
                f"{self.proxy_endpoint}/health",
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 401:
                raise ConfigurationException(
                    f"Invalid API key. Please check your API key at https://platform.armoriq.ai/dashboard/api-keys"
                )
            elif response.status_code >= 400:
                logger.warning(f"API key validation returned status {response.status_code}, but continuing...")
            else:
                logger.info(f"✅ API key validated successfully")
                
        except httpx.ConnectError:
            logger.warning(f"Could not connect to proxy at {self.proxy_endpoint} for API key validation")
        except httpx.TimeoutException:
            logger.warning(f"Timeout connecting to proxy at {self.proxy_endpoint} for API key validation")
        except ConfigurationException:
            raise
        except Exception as e:
            logger.warning(f"API key validation check failed: {e}, but continuing...")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()

    def close(self):
        """Close HTTP client and cleanup resources."""
        self.http_client.close()
        logger.debug("ArmorIQ SDK client closed")

    def capture_plan(
        self,
        llm: str,
        prompt: str,
        plan: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlanCapture:
        """
        Capture an execution plan structure.
        
        The plan is simply validated and stored. Hash and Merkle tree
        generation happens later in get_intent_token() on the CSRG-IAP service.
        
        This method takes either:
        1. An LLM identifier and prompt (will call LLM to generate plan), OR
        2. A pre-generated plan dictionary
        
        Args:
            llm: LLM identifier (e.g., "gpt-4", "claude-3")
            prompt: User prompt or instruction
            plan: Optional pre-generated plan (if None, will use LLM)
            metadata: Optional metadata to attach
            
        Returns:
            PlanCapture with plan structure (hash/Merkle created later by CSRG-IAP)
            
        Example:
            >>> plan = client.capture_plan("gpt-4", "Book flight and hotel")
            >>> print(f"Plan has {len(plan.plan['steps'])} steps")
        """
        logger.info(f"Capturing plan: llm={llm}, prompt={prompt[:50]}...")

        # Plan must be provided by the user
        # Users should define their plan based on their onboarded MCPs and tools
        if plan is None:
            raise ValueError(
                "Plan structure is required. "
                "You must provide an explicit plan with the MCP and actions you want to execute.\n\n"
                "Example:\n"
                "  plan = client.capture_plan(\n"
                "      llm='gpt-4',\n"
                "      prompt='Your task description',\n"
                "      plan={\n"
                "          'goal': 'Your task description',\n"
                "          'steps': [\n"
                "              {\n"
                "                  'action': 'your_tool_name',\n"
                "                  'mcp': 'your-mcp-name',\n"
                "                  'params': {'param1': 'value1'}\n"
                "              }\n"
                "          ]\n"
                "      }\n"
                "  )\n\n"
                "Note: Use the MCP name and tool names from your onboarded MCPs on the ArmorIQ platform."
            )

        # Validate plan structure
        if not isinstance(plan, dict):
            raise ValueError("Plan must be a dictionary")
        
        if "steps" not in plan:
            raise ValueError("Plan must contain 'steps' key")

        # Return PlanCapture with just the plan structure
        # Hash and Merkle tree will be created by CSRG-IAP service
        capture = PlanCapture(
            plan=plan,
            llm=llm,
            prompt=prompt,
            metadata=metadata or {},
        )

        logger.info(
            "Plan captured with %d steps",
            len(plan.get("steps", [])),
        )
        return capture

    def get_intent_token(
        self,
        plan_capture: PlanCapture,
        policy: Optional[Dict[str, Any]] = None,
        validity_seconds: float = 60.0,
    ) -> IntentToken:
        """
        Request a signed intent token from IAP for the given plan.
        
        The CSRG-IAP service will:
        - Convert plan to Merkle tree structure
        - Calculate SHA-256 hash from canonical representation
        - Sign with Ed25519
        - Return token with hash and merkle_root
        
        Args:
            plan_capture: PlanCapture from capture_plan()
            policy: Optional policy manifest (defaults to allow-all)
            validity_seconds: Token validity duration in seconds
            
        Returns:
            IntentToken containing signed token and metadata
            
        Raises:
            InvalidTokenException: If token issuance fails
            
        Example:
            >>> plan = client.capture_plan("gpt-4", "Book flight")
            >>> token = client.get_intent_token(plan)
            >>> print(f"Token expires: {token.expires_at}")
        """
        logger.info(f"Requesting intent token for plan with {len(plan_capture.plan.get('steps', []))} steps")

        # Prepare request payload for Backend /iap/sdk/token endpoint
        # The Backend will call CSRG-IAP to create hash and Merkle tree
        # NOTE: IAP calls go through Backend, NOT through Proxy
        payload = {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "context_id": self.context_id,
            "plan": plan_capture.plan,
            "policy": policy,
            "expires_in": validity_seconds,
        }

        # Call Backend token issuance endpoint (SDK → Backend → CSRG-IAP)
        try:
            headers = {"X-API-Key": self.api_key}
            response = self.http_client.post(
                f"{self.backend_endpoint}/iap/sdk/token",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                raise InvalidTokenException(f"Token issuance failed: {data.get('message', 'Unknown error')}")
            
            # Parse token response (now includes hash and merkle_root from CSRG-IAP)
            token_data = data.get("token", {})
            
            # Add plan to token for Merkle proof generation during invoke()
            raw_token = {
                "plan": plan_capture.plan,
                "token": token_data,
                "plan_hash": data.get("plan_hash"),
                "merkle_root": data.get("merkle_root"),
                "intent_reference": data.get("intent_reference"),
                "composite_identity": data.get("composite_identity", ""),
            }
            
            token = IntentToken(
                token_id=data.get("intent_reference", "unknown"),
                plan_hash=data.get("plan_hash", ""),
                plan_id=data.get("plan_id"),
                signature=token_data.get("signature", "") if isinstance(token_data, dict) else "",
                issued_at=datetime.now().timestamp(),
                expires_at=datetime.now().timestamp() + validity_seconds,
                policy=policy or {},
                composite_identity=data.get("composite_identity", ""),
                client_info=data.get("client_info"),
                policy_validation=data.get("policy_validation"),
                step_proofs=data.get("step_proofs", []),
                total_steps=len(plan_capture.plan.get("steps", [])),
                raw_token=raw_token,
            )

            logger.info(f"Intent token issued: id={token.token_id}, plan_hash={token.plan_hash[:16]}..., expires={token.time_until_expiry:.1f}s")
            return token

        except httpx.HTTPStatusError as e:
            logger.error(f"Backend returned error: {e.response.status_code} - {e.response.text}")
            raise InvalidTokenException(f"Failed to get intent token: {e.response.text}")
        except Exception as e:
            logger.error(f"Failed to get intent token: {e}")
            raise InvalidTokenException(f"Failed to get intent token: {str(e)}")

    def invoke(
        self,
        mcp: str,
        action: str,
        intent_token: IntentToken,
        params: Optional[Dict[str, Any]] = None,
        merkle_proof: Optional[list] = None,
        user_email: Optional[str] = None,
    ) -> MCPInvocationResult:
        """
        Invoke an MCP action through the ArmorIQ proxy with token verification.
        
        Args:
            mcp: MCP identifier (e.g., "travel-mcp", "finance-mcp")
            action: Action name to invoke (tool name)
            intent_token: Intent token from get_intent_token()
            params: Optional action parameters
            merkle_proof: Optional Merkle proof (auto-generated if not provided)
            user_email: Optional user email (required for some MCPs)
            
        Returns:
            MCPInvocationResult with action result
            
        Raises:
            InvalidTokenException: If token is invalid or expired
            IntentMismatchException: If action not in original plan
            MCPInvocationException: If MCP invocation fails
            
        Example:
            >>> result = client.invoke(
            ...     "travel-mcp",
            ...     "book_flight",
            ...     token,
            ...     params={"dest": "CDG"},
            ...     user_email="user@example.com"
            ... )
        """
        logger.info(f"Invoking MCP action: mcp={mcp}, action={action}")

        # Check token expiry
        if intent_token.is_expired:
            raise TokenExpiredException(
                f"Intent token expired {abs(intent_token.time_until_expiry):.1f}s ago",
                token_id=intent_token.token_id,
                expired_at=intent_token.expires_at,
            )

        # Get proxy endpoint for this MCP
        proxy_url = self.proxy_endpoints.get(mcp)
        if not proxy_url:
            # Try environment variable for specific MCP
            proxy_url = os.getenv(f"{mcp.upper()}_PROXY_URL")
            if not proxy_url:
                # Fall back to default proxy endpoint
                proxy_url = self.default_proxy_endpoint
                logger.debug(f"Using default proxy endpoint for {mcp}: {proxy_url}")

        # Build IAM context from token
        iam_context = {}
        if intent_token.policy_validation:
            allowed_tools = intent_token.policy_validation.get("allowed_tools", [])
            iam_context["allowed_tools"] = allowed_tools
        
        if user_email:
            iam_context["email"] = user_email
            iam_context["user_email"] = user_email
        
        # Add user_id and other identity info
        if intent_token.raw_token:
            iam_context["user_id"] = intent_token.raw_token.get("user_id", self.user_id)
            iam_context["agent_id"] = intent_token.raw_token.get("agent_id", self.agent_id)

        # Prepare invocation payload (matching armoriq-proxy-server format)
        invoke_params = params or {}
        invoke_params["_iam_context"] = iam_context
        if user_email:
            invoke_params["user_email"] = user_email

        payload = {
            "mcp": mcp,
            "action": action,
            "tool": action,  # FastMCP uses 'tool' name
            "params": invoke_params,
            "arguments": invoke_params,  # Some MCPs use 'arguments'
            "intent_token": intent_token.raw_token,
            "merkle_proof": merkle_proof,
            "plan": intent_token.raw_token.get("plan") if intent_token.raw_token else None,  # Include plan for proof generation
        }

        # Prepare headers with CSRG token and proof headers
        headers = {
            "Accept": "application/json, text/event-stream",  # MCP servers require both
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",  # Prevent caching issues
            "X-Request-ID": f"sdk-{datetime.now().timestamp()}",  # Unique request ID
        }
        
        # IMPORTANT: Include API key for customer SDK authentication
        # The proxy needs this to detect customer SDK mode and skip JWT verification
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        # Send CSRG token structure in payload
        if intent_token.raw_token and isinstance(intent_token.raw_token, dict):
            # Include the full CSRG token in payload for proxy to forward to /verify/action
            payload["token"] = intent_token.raw_token.get("token", {})
            payload["csrg_token"] = intent_token.raw_token.get("token", {})
            
            # IMPORTANT: For customer SDK with API key, do NOT send Authorization Bearer header
            # The proxy uses API key auth (auth_method='api_key') to detect customer SDK mode
            # Adding a Bearer token would make it look like enterprise SDK and cause 404
            # Only set Authorization header for enterprise SDK (when not using API key)
            if not self.api_key:
                # Enterprise SDK: Send the composite_identity as Bearer token
                auth_value = intent_token.raw_token.get("composite_identity") or intent_token.token_id
                headers["Authorization"] = f"Bearer {auth_value}"
        
        # Find the step index for this action in the plan
        # CRITICAL: Must verify against the correct LEAF node for the action being invoked
        plan = intent_token.raw_token.get("plan", {}) if intent_token.raw_token else {}
        steps = plan.get("steps", [])
        
        # Find which step contains this action
        step_index = None
        for idx, step in enumerate(steps):
            if isinstance(step, dict) and step.get("action") == action:
                step_index = idx
                break
        
        if step_index is None:
            raise IntentMismatchException(
                f"Action '{action}' not found in the original plan. "
                f"Plan contains actions: {[s.get('action') if isinstance(s, dict) else 'unknown' for s in steps]}. "
                f"You can only invoke actions that were included in the plan when you called capture_plan()."
            )
        
        # Use Merkle proof from CSRG-IAP (step_proofs) instead of generating locally
        # CRITICAL: Merkle proof generation must ONLY be done by CSRG-IAP, not by SDK
        if not merkle_proof:
            # Try to get proof from step_proofs provided by CSRG-IAP
            if intent_token.step_proofs and len(intent_token.step_proofs) > step_index:
                merkle_proof = intent_token.step_proofs[step_index]
                logger.debug(f"Using Merkle proof from CSRG-IAP for step {step_index}")
            else:
                logger.warning(
                    f"No Merkle proof available for step {step_index}. "
                    f"step_proofs length: {len(intent_token.step_proofs) if intent_token.step_proofs else 0}. "
                    f"Note: Merkle proofs should be generated by CSRG-IAP during token issuance."
                )
        
        # Add CSRG proof to headers if available
        if merkle_proof:
            import json
            headers["X-CSRG-Proof"] = json.dumps(merkle_proof)
            logger.debug(f"Added CSRG proof header for step {step_index}")
        
        # CSRG path points to the action leaf node
        csrg_path = f"/steps/[{step_index}]/action"
        headers["X-CSRG-Path"] = csrg_path
        
        # Value digest for CSRG verification - MUST match the actual value in the plan
        # Get the LEAF value from the plan that was used to generate the token
        import hashlib
        import json
        
        logger.debug(f"[MERKLE DEBUG] raw_token keys: {list(intent_token.raw_token.keys()) if intent_token.raw_token else 'None'}")
        logger.debug(f"[MERKLE DEBUG] plan from token: {plan}")
        
        # Extract the leaf value at the path we're verifying
        # For /steps/[step_index]/action, the value is plan["steps"][step_index]["action"]
        step_obj = steps[step_index] if step_index < len(steps) else {}
        leaf_value = step_obj.get("action", action) if isinstance(step_obj, dict) else action
        
        # CRITICAL: Use the same JSON canonicalization as CSRG-IAP
        # CSRG uses: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        value_str = json.dumps(leaf_value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        value_digest = hashlib.sha256(value_str.encode("utf-8")).hexdigest()
        headers["X-CSRG-Value-Digest"] = value_digest
        
        logger.debug(f"CSRG Verification Details:")
        logger.debug(f"  Path: {csrg_path}")
        logger.debug(f"  Leaf Value: {leaf_value}")
        logger.debug(f"  Value String (canonical): {value_str}")
        logger.debug(f"  Digest: {value_digest}")
        
        # Call proxy
        try:
            start_time = datetime.now()
            
            # Verbose logging with print for debugging
            print(f"\n� DEBUG: Making POST request to: {proxy_url}/invoke")
            print(f"� DEBUG: Headers: {json.dumps({k: v[:50] + '...' if len(str(v)) > 50 else v for k, v in headers.items()}, indent=2)}")
            print(f"� DEBUG: Payload mcp={payload.get('mcp')}, action={payload.get('action')}")
            
            # For SSE responses, we need to read the entire stream before checking status
            # because the status might only be available after the stream completes
            with self.http_client.stream('POST', f"{proxy_url}/invoke", json=payload, headers=headers) as response:
                # Debug logging
                print(f"� DEBUG: Response status: {response.status_code}")
                print(f"� DEBUG: Response Content-Type: {response.headers.get('content-type')}")
                
                # Read the entire response
                content = b""
                chunk_count = 0
                for chunk in response.iter_bytes():
                    content += chunk
                    chunk_count += 1
                
                execution_time = (datetime.now() - start_time).total_seconds()
                response_text = content.decode('utf-8')
                print(f"🔍 DEBUG: Read {chunk_count} chunks, total {len(content)} bytes")
                print(f"🔍 DEBUG: Response lines:")
                for i, line in enumerate(response_text.split('\n')[:10]):
                    print(f"🔍 DEBUG:   Line {i}: {repr(line)}")
                
                # Now check status after reading
                response.raise_for_status()
                
                # Handle SSE format responses (text/event-stream)
                content_type = response.headers.get('content-type', '')
                if 'text/event-stream' in content_type:
                    # Parse SSE format: lines starting with "data: " contain JSON
                    logger.debug(f"Handling SSE response")
                    data = None
                    for line in response_text.split('\n'):
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove "data: " prefix
                            try:
                                data = json.loads(data_str)
                                logger.debug(f"Parsed SSE data: {data}")
                                break
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse SSE line: {data_str}, error: {e}")
                                continue
                    
                    if data is None:
                        logger.error("No valid JSON data found in SSE response")
                        raise MCPInvocationException("No data in SSE response", mcp=mcp, action=action)
                else:
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON response: {response_text[:500]}")
                        raise MCPInvocationException(f"Invalid JSON response", mcp=mcp, action=action)
            
            # Check for JSON-RPC error
            if 'error' in data:
                error_msg = data['error'].get('message', 'Unknown error')
                error_code = data['error'].get('code', -1)
                error_data = data['error'].get('data', '')
                raise MCPInvocationException(
                    f"MCP tool error ({error_code}): {error_msg} - {error_data}",
                    mcp=mcp,
                    action=action
                )
            
            # Extract result from JSON-RPC response
            result_data = data.get('result', data)

            # Extract result from JSON-RPC response
            result_data = data.get('result', data)

            result = MCPInvocationResult(
                mcp=mcp,
                action=action,
                result=result_data,
                status="success",
                execution_time=execution_time,
                verified=True,
                metadata={},
            )

            logger.info(f"MCP invocation succeeded: {action} in {execution_time:.2f}s")
            return result

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            
            # Safely read error detail from response
            try:
                # Check if response is already read
                if hasattr(e.response, '_content'):
                    error_detail = e.response.text
                else:
                    # For streaming responses, read the content first
                    error_detail = e.response.read().decode('utf-8')
            except Exception:
                error_detail = f"Status {status_code}"

            # Parse specific error types
            if status_code == 401 or status_code == 403:
                raise InvalidTokenException(f"Token verification failed: {error_detail}")
            elif status_code == 409:
                raise IntentMismatchException(
                    f"Action not in plan: {error_detail}",
                    action=action,
                    plan_hash=intent_token.plan_hash,
                )
            else:
                raise MCPInvocationException(
                    f"MCP invocation failed: {error_detail}",
                    mcp=mcp,
                    action=action,
                    status_code=status_code,
                )

        except Exception as e:
            logger.error(f"MCP invocation error: {e}")
            raise MCPInvocationException(f"MCP invocation failed: {str(e)}", mcp=mcp, action=action)

    def delegate(
        self,
        intent_token: IntentToken,
        delegate_public_key: str,
        validity_seconds: int = 3600,
        allowed_actions: Optional[list] = None,
        target_agent: Optional[str] = None,
        subtask: Optional[Dict[str, Any]] = None,
    ) -> DelegationResult:
        """
        Delegate authority to another agent using CSRG token delegation.
        
        Args:
            intent_token: Intent token to delegate
            delegate_public_key: Public key of the delegate agent (Ed25519 hex format)
            validity_seconds: Delegation validity in seconds (default: 3600)
            allowed_actions: Optional list of allowed actions (defaults to all from original token)
            target_agent: Optional target agent identifier (deprecated, use delegate_public_key)
            subtask: Optional subtask plan (deprecated, use allowed_actions)
            
        Returns:
            DelegationResult with delegated token
            
        Raises:
            DelegationException: If delegation creation fails
            InvalidTokenException: If original token is invalid
            
        Example:
            >>> # Generate delegate keypair
            >>> from cryptography.hazmat.primitives.asymmetric import ed25519
            >>> delegate_private_key = ed25519.Ed25519PrivateKey.generate()
            >>> delegate_public_key = delegate_private_key.public_key()
            >>> pub_key_bytes = delegate_public_key.public_bytes(
            ...     encoding=serialization.Encoding.Raw,
            ...     format=serialization.PublicFormat.Raw
            ... )
            >>> pub_key_hex = pub_key_bytes.hex()
            >>> 
            >>> result = client.delegate(
            ...     token,
            ...     delegate_public_key=pub_key_hex,
            ...     validity_seconds=1800
            ... )
        """
        logger.info(
            f"Creating delegation for token_id={intent_token.token_id}, "
            f"delegate_key={delegate_public_key[:16]}..., validity={validity_seconds}s"
        )

        # Extract the inner token dict from raw_token
        # raw_token has structure: {intent_reference, token, plan_hash, ...}
        # CSRG-IAP /delegation/create expects just the inner 'token' dict
        token_to_delegate = intent_token.raw_token
        
        # If raw_token is the response structure, extract the inner token
        if isinstance(token_to_delegate, dict) and "token" in token_to_delegate:
            token_to_delegate = token_to_delegate["token"]

        # Prepare delegation request matching CsrgDelegationRequest
        payload = {
            "token": token_to_delegate,
            "delegate_public_key": delegate_public_key,
            "validity_seconds": validity_seconds,
        }
        
        # Add allowed_actions if specified
        if allowed_actions:
            payload["allowed_actions"] = allowed_actions
        
        # Legacy support for target_agent/subtask
        if target_agent:
            payload["target_agent"] = target_agent
        if subtask:
            payload["subtask"] = subtask

        # Call IAP delegation endpoint
        try:
            response = self.http_client.post(
                f"{self.iap_endpoint}/delegation/create",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # Parse delegation response
            # CSRG-IAP returns {"delegation": {...}} structure
            delegated_token_data = data.get("delegation") or data.get("delegated_token") or data.get("new_token")
            if not delegated_token_data:
                raise DelegationException(
                    f"Delegation response missing 'delegation' key. Got keys: {list(data.keys())}",
                    delegation_id=data.get("delegation_id"),
                )

            # Create IntentToken from delegated token
            # Delegation response has minimal structure, map to IntentToken fields
            delegated_token = IntentToken(
                token_id=delegated_token_data.get("token_id", ""),
                plan_hash=delegated_token_data.get("plan_hash", intent_token.plan_hash),
                plan_id=delegated_token_data.get("plan_id"),
                signature=delegated_token_data.get("signature", ""),
                issued_at=delegated_token_data.get("issued_at", datetime.now().timestamp()),
                expires_at=delegated_token_data.get("expires_at", 0),
                policy=delegated_token_data.get("policy", {}),
                composite_identity=delegated_token_data.get("composite_identity", ""),
                client_info=delegated_token_data.get("client_info"),
                policy_validation=delegated_token_data.get("policy_validation"),
                step_proofs=delegated_token_data.get("step_proofs", []),
                total_steps=delegated_token_data.get("total_steps", 0),
                raw_token={"token": delegated_token_data},  # Wrap in expected structure
            )

            result = DelegationResult(
                delegation_id=data.get("delegation_id", delegated_token.token_id),
                delegated_token=delegated_token,
                delegate_public_key=delegate_public_key,
                target_agent=target_agent,
                expires_at=delegated_token.expires_at,
                trust_delta=data.get("trust_delta", {}),
                status="delegated",
                metadata=data.get("metadata", {}),
            )

            logger.info(f"Delegation successful: delegation_id={result.delegation_id}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Delegation failed: {e.response.status_code} - {e.response.text}")
            raise DelegationException(
                f"Delegation failed: {e.response.text}",
                delegation_id=data.get("delegation_id") if 'data' in locals() else None,
                status_code=e.response.status_code,
            )
        except Exception as e:
            logger.error(f"Delegation request error: {str(e)}")
            raise DelegationException(f"Delegation request error: {str(e)}") from e
            logger.error(f"Delegation error: {e}")
            raise DelegationException(f"Delegation failed: {str(e)}", target_agent=target_agent)

    def verify_token(self, intent_token: IntentToken) -> bool:
        """
        Verify an intent token with IAP.
        
        Note: This is mainly for testing. In production, the proxy
        handles all token verification via Merkle proof checking.
        
        Args:
            intent_token: Token to verify
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Perform local token validation
            # Check expiration
            if intent_token.is_expired:
                logger.warning(f"Token {intent_token.token_id} has expired")
                return False
            
            # Check required fields
            if not intent_token.signature or not intent_token.plan_hash:
                logger.warning(f"Token {intent_token.token_id} missing required fields")
                return False
            
            logger.info(f"Token {intent_token.token_id} is valid (expires in {intent_token.time_until_expiry:.1f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False
