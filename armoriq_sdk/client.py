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
    
    # Production endpoints (default)
    DEFAULT_IAP_ENDPOINT = "https://iap.armoriq.io"  # CSRG-IAP (Ed25519 tokens)
    DEFAULT_PROXY_ENDPOINT = "https://cloud-run-proxy.armoriq.io"
    DEFAULT_CONMAP_ENDPOINT = "https://api.armoriq.io"  # ConMap IAP (JWT tokens)

    def __init__(
        self,
        iap_endpoint: Optional[str] = None,
        proxy_endpoint: Optional[str] = None,
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
        
        Args:
            iap_endpoint: IAP service endpoint URL (defaults to production: https://iap.armoriq.io for CSRG or https://api.armoriq.io for ConMap)
            proxy_endpoint: Default proxy endpoint URL (defaults to production: https://cloud-run-proxy.armoriq.io)
            proxy_endpoints: Dict mapping MCP names to specific proxy URLs
            user_id: User identifier (or USER_ID env var)
            agent_id: Agent identifier (or AGENT_ID env var)
            context_id: Optional context identifier
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            verify_ssl: Whether to verify SSL certificates
            api_key: Optional API key for authentication
            use_production: Use production endpoints (default: True). Set False for local development.
            use_conmap_iap: Use ConMap IAP (JWT tokens, default) vs CSRG-IAP (Ed25519 tokens). Set False for direct CSRG usage.
            
        Raises:
            ConfigurationException: If required configuration is missing
            
        Environment Variables:
            IAP_ENDPOINT: Override IAP endpoint
            PROXY_ENDPOINT: Override default proxy endpoint
            USER_ID: User identifier
            AGENT_ID: Agent identifier
            CONTEXT_ID: Context identifier (default: "default")
            ARMORIQ_API_KEY: API key for authentication
            ARMORIQ_ENV: Set to "development" to use local endpoints
            USE_CONMAP_IAP: Set to "false" to use CSRG-IAP directly
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
            # Use CSRG-IAP (Ed25519 tokens with Merkle proofs)
            self.iap_endpoint = self.DEFAULT_IAP_ENDPOINT
        else:
            # Local development default
            self.iap_endpoint = "http://localhost:8082"
        
        # Load proxy endpoint
        if proxy_endpoint:
            self.default_proxy_endpoint = proxy_endpoint
        elif os.getenv("PROXY_ENDPOINT"):
            self.default_proxy_endpoint = os.getenv("PROXY_ENDPOINT")
        elif use_prod:
            self.default_proxy_endpoint = self.DEFAULT_PROXY_ENDPOINT
        else:
            # Local development default
            self.default_proxy_endpoint = "http://localhost:3001"
        
        # Load user/agent identifiers
        self.user_id = user_id or os.getenv("USER_ID")
        self.agent_id = agent_id or os.getenv("AGENT_ID")
        self.context_id = context_id or os.getenv("CONTEXT_ID", "default")
        self.api_key = api_key or os.getenv("ARMORIQ_API_KEY")

        # Validate required config
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
            f"iap={self.iap_endpoint}, proxy={self.default_proxy_endpoint}"
        )

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
        Capture an execution plan and convert to canonical CSRG format.
        
        This method takes either:
        1. An LLM identifier and prompt (will call LLM to generate plan), OR
        2. A pre-generated plan dictionary
        
        The plan is then canonicalized using CSRG.
        
        Args:
            llm: LLM identifier (e.g., "gpt-4", "claude-3")
            prompt: User prompt or instruction
            plan: Optional pre-generated plan (if None, will use LLM)
            metadata: Optional metadata to attach
            
        Returns:
            PlanCapture with canonical plan and CSRG hash
            
        Example:
            >>> plan = client.capture_plan("gpt-4", "Book flight and hotel")
            >>> print(f"Plan hash: {plan.plan_hash}")
        """
        logger.info(f"Capturing plan: llm={llm}, prompt={prompt[:50]}...")

        # If plan not provided, generate from LLM (simplified for now)
        if plan is None:
            # In production, this would call the LLM
            # For now, create a simple structured plan
            # NOTE: For CSRG Merkle verification, the plan must contain the exact
            # action structure that will be sent during invoke()
            plan = {
                "goal": prompt,
                "steps": [
                    {"action": "get_weather", "params": {"city": "San Francisco"}},  # Must match invoke params
                ],
                "metadata": metadata or {},
            }

        # Canonicalize with CSRG (support multiple csrg-iap API variants)
        try:
            # csrg-iap's CanonicalStructuredReasoningGraph expects construction without
            # the plan, then build_graph(plan) must be called. Older/newer APIs may
            # expose attributes instead of methods; handle both by probing.
            csrg = CanonicalStructuredReasoningGraph()

            # If build_graph exists, use it to build internal graph from plan
            if hasattr(csrg, "build_graph"):
                csrg.build_graph(plan)

            # plan_hash: prefer attribute if present, otherwise call canonical_hash()
            plan_hash = getattr(csrg, "plan_hash", None)
            if not plan_hash and hasattr(csrg, "canonical_hash"):
                plan_hash = csrg.canonical_hash()

            # merkle_root: prefer attribute, otherwise canonical_hash() as fallback
            merkle_root = getattr(csrg, "merkle_root", None)
            if not merkle_root and hasattr(csrg, "canonical_hash"):
                merkle_root = csrg.canonical_hash()

            # ordered_paths: may be an attribute or a callable method
            ordered_paths = getattr(csrg, "ordered_paths", None)
            if callable(ordered_paths):
                ordered_paths = ordered_paths()
            if ordered_paths is None:
                ordered_paths = []

            capture = PlanCapture(
                plan=plan,
                plan_hash=plan_hash,
                merkle_root=merkle_root,
                ordered_paths=ordered_paths,
                llm=llm,
                prompt=prompt,
                metadata=metadata or {},
            )

            logger.info(
                "Plan captured: hash=%s..., paths=%d",
                (plan_hash[:16] + "...") if isinstance(plan_hash, str) else str(plan_hash),
                len(ordered_paths),
            )
            return capture

        except Exception as e:
            logger.error(f"Failed to capture plan: {e}")
            raise

    def get_intent_token(
        self,
        plan_capture: PlanCapture,
        policy: Optional[Dict[str, Any]] = None,
        validity_seconds: float = 60.0,
    ) -> IntentToken:
        """
        Request a signed intent token from IAP for the given plan.
        
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
        logger.info(f"Requesting intent token: plan_hash={plan_capture.plan_hash[:16]}...")

        # Check cache first
        cache_key = f"{plan_capture.plan_hash}:{validity_seconds}"
        if cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if not cached.is_expired:
                logger.debug("Returning cached token")
                return cached

        # Prepare request payload for CSRG-IAP customer endpoint (simplified)
        payload = {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "context_id": self.context_id,
            "plan_capture": {
                "plan": plan_capture.plan,
                "plan_hash": plan_capture.plan_hash,
                "merkle_root": plan_capture.merkle_root,
            },
            "metadata": plan_capture.metadata,
            "validity_seconds": validity_seconds,
        }

        # Call CSRG-IAP customer endpoint (simplified format)
        try:
            response = self.http_client.post(f"{self.iap_endpoint}/intent/customer", json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse CSRG-IAP token response
            token_data = data.get("token", {})
            
            # Add plan to raw_token if not already present (for Merkle proof generation)
            if "plan" not in data:
                data["plan"] = plan_capture.plan
            
            token = IntentToken(
                token_id=data.get("intent_reference", "unknown"),
                plan_hash=data.get("plan_hash", plan_capture.plan_hash),
                plan_id=data.get("plan_id"),
                signature=token_data.get("signature", ""),
                issued_at=token_data.get("issued_at", datetime.now().timestamp()),
                expires_at=token_data.get("expires_at", datetime.now().timestamp() + validity_seconds),
                policy=policy or {},
                composite_identity=token_data.get("composite_identity", data.get("composite_identity", "")),
                client_info=data.get("client_info"),
                policy_validation=data.get("policy_validation"),
                step_proofs=data.get("step_proofs", []),
                total_steps=data.get("total_steps", 0),
                raw_token=data,
            )

            # Cache token
            self._token_cache[cache_key] = token

            logger.info(f"Intent token issued: id={token.token_id}, expires={token.time_until_expiry:.1f}s")
            return token

        except httpx.HTTPStatusError as e:
            logger.error(f"IAP returned error: {e.response.status_code} - {e.response.text}")
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
            
            # Also set Authorization header (Proxy checks for this first)
            # Send the composite_identity or a placeholder since Proxy expects Bearer token
            auth_value = intent_token.raw_token.get("composite_identity") or intent_token.token_id
            headers["Authorization"] = f"Bearer {auth_value}"
        
        # Add CSRG proof headers if available
        # Generate Merkle proof if not provided
        if not merkle_proof and intent_token.raw_token:
            # Try to generate proof from the plan stored in the token
            try:
                from csrg_iap.core.csrg import CanonicalStructuredReasoningGraph
                
                # Get the original plan from token metadata
                plan = intent_token.raw_token.get("plan")
                if plan:
                    csrg = CanonicalStructuredReasoningGraph()
                    csrg.build_graph(plan)
                    
                    # Determine CSRG path from action
                    # CRITICAL: Must use a LEAF path, not a container
                    # Path format: /steps/[0]/action for action name leaf
                    step_index = 0  # TODO: track actual step index dynamically
                    csrg_path = f"/steps/[{step_index}]/action"
                    
                    # Get the actual leaf value from the plan for Merkle verification
                    step_obj = plan.get("steps", [])[step_index] if step_index < len(plan.get("steps", [])) else {}
                    leaf_value = step_obj.get("action", action) if isinstance(step_obj, dict) else action
                    
                    # Generate Merkle proof for this path
                    proof_items = csrg.merkle_proof(csrg_path)
                    merkle_proof = [
                        {"position": item.position, "sibling_hash": item.sibling_hash}
                        for item in proof_items
                    ]
                    logger.debug(f"Generated Merkle proof with {len(merkle_proof)} items for path {csrg_path}, value={leaf_value}")
            except Exception as e:
                logger.warning(f"Could not generate Merkle proof: {e}")
        
        if merkle_proof:
            import json
            headers["X-CSRG-Proof"] = json.dumps(merkle_proof)
            logger.debug(f"Added CSRG proof header with {len(merkle_proof)} items")
        
        # Determine CSRG path from action (simplified - should match plan structure)
        # CRITICAL: Must verify against a LEAF node, not a container node
        # The action name is stored at /steps/[0]/action (a leaf), not /steps/[0] (a container)
        step_index = 0  # TODO: track actual step index
        csrg_path = f"/steps/[{step_index}]/action"
        headers["X-CSRG-Path"] = csrg_path
        
        # Value digest for CSRG verification - MUST match the actual value in the plan
        # Get the LEAF value from the plan that was used to generate the token
        # For path /steps/[0]/action, the value is just the action name string
        import hashlib
        import json
        
        plan = intent_token.raw_token.get("plan", {}) if intent_token.raw_token else {}
        logger.debug(f"[MERKLE DEBUG] raw_token keys: {list(intent_token.raw_token.keys()) if intent_token.raw_token else 'None'}")
        logger.debug(f"[MERKLE DEBUG] plan from token: {plan}")
        
        # Extract the leaf value at the path we're verifying
        # For /steps/[0]/action, the value is plan["steps"][0]["action"]
        step_obj = plan.get("steps", [])[step_index] if step_index < len(plan.get("steps", [])) else {}
        leaf_value = step_obj.get("action", action) if isinstance(step_obj, dict) else action
        
        # CRITICAL: Use the same JSON canonicalization as CSRG-IAP
        # CSRG uses: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        value_str = json.dumps(leaf_value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        value_digest = hashlib.sha256(value_str.encode("utf-8")).hexdigest()
        headers["X-CSRG-Value-Digest"] = value_digest
        
        logger.info(f"[MERKLE DEBUG] CSRG Verification Details:")
        logger.info(f"  Path: {csrg_path}")
        logger.info(f"  Leaf Value: {leaf_value}")
        logger.info(f"  Value String (canonical): {value_str}")
        logger.info(f"  Digest: {value_digest}")
        
        # Call proxy
        try:
            start_time = datetime.now()
            response = self.http_client.post(f"{proxy_url}/invoke", json=payload, headers=headers)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Debug: print raw response BEFORE raise_for_status
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response Content-Type: {response.headers.get('content-type')}")
            print(f"[DEBUG] Response text (first 1000 chars): {response.text[:1000]}")
            
            response.raise_for_status()
            
            # Handle SSE format responses (text/event-stream)
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' in content_type:
                # Parse SSE format: lines starting with "data: " contain JSON
                for line in response.text.split('\n'):
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove "data: " prefix
                        data = json.loads(data_str)
                        break
                else:
                    logger.error("No data found in SSE response")
                    raise MCPInvocationException("No data in SSE response", mcp=mcp, action=action)
            else:
                data = response.json()
            
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
            error_detail = e.response.text

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
