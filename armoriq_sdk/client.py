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
        >>> client = ArmorIQClient(
        ...     iap_endpoint="https://iap.example.com",
        ...     user_id="user123",
        ...     agent_id="my-agent"
        ... )
        >>> plan = client.capture_plan("gpt-4", "Book a flight to Paris")
        >>> token = client.get_intent_token(plan)
        >>> result = client.invoke("travel-mcp", "book_flight", token)
    """

    def __init__(
        self,
        iap_endpoint: Optional[str] = None,
        proxy_endpoints: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        context_id: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True,
        api_key: Optional[str] = None,
    ):
        """
        Initialize ArmorIQ client.
        
        Args:
            iap_endpoint: IAP service endpoint URL (or IAP_ENDPOINT env var)
            proxy_endpoints: Dict mapping MCP names to proxy URLs
            user_id: User identifier (or USER_ID env var)
            agent_id: Agent identifier (or AGENT_ID env var)
            context_id: Optional context identifier
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            verify_ssl: Whether to verify SSL certificates
            api_key: Optional API key for authentication
            
        Raises:
            ConfigurationException: If required configuration is missing
        """
        # Load from environment if not provided
        self.iap_endpoint = iap_endpoint or os.getenv("IAP_ENDPOINT")
        self.user_id = user_id or os.getenv("USER_ID")
        self.agent_id = agent_id or os.getenv("AGENT_ID")
        self.context_id = context_id or os.getenv("CONTEXT_ID", "default")
        self.api_key = api_key or os.getenv("ARMORIQ_API_KEY")

        # Validate required config
        if not self.iap_endpoint:
            raise ConfigurationException("iap_endpoint is required (set IAP_ENDPOINT env var)")
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
            f"ArmorIQ SDK initialized: user={self.user_id}, "
            f"agent={self.agent_id}, iap={self.iap_endpoint}"
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
            plan = {
                "goal": prompt,
                "steps": [
                    {"action": "parse_intent", "llm": llm},
                    {"action": "execute_plan", "provider": "mcp"},
                ],
                "metadata": metadata or {},
            }

        # Canonicalize with CSRG
        try:
            csrg = CanonicalStructuredReasoningGraph(plan)
            plan_hash = csrg.plan_hash
            merkle_root = csrg.merkle_root
            ordered_paths = csrg.ordered_paths

            capture = PlanCapture(
                plan=plan,
                plan_hash=plan_hash,
                merkle_root=merkle_root,
                ordered_paths=ordered_paths,
                llm=llm,
                prompt=prompt,
                metadata=metadata or {},
            )

            logger.info(f"Plan captured: hash={plan_hash[:16]}..., paths={len(ordered_paths)}")
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

        # Prepare request payload
        payload = {
            "plan": plan_capture.plan,
            "policy": policy
            or {"rules": [{"effect": "allow", "actions": ["*"], "resources": ["*"]}]},
            "identity": {
                "user_id": self.user_id,
                "agent_id": self.agent_id,
                "context_id": self.context_id,
            },
            "metadata": plan_capture.metadata,
            "validity_seconds": validity_seconds,
        }

        # Call IAP intent endpoint
        try:
            response = self.http_client.post(f"{self.iap_endpoint}/intent", json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse token response (matches conmap-auto structure)
            token_data = data.get("token", {})
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
            # Try default proxy pattern
            proxy_url = os.getenv(f"{mcp.upper()}_PROXY_URL")
            if not proxy_url:
                raise MCPInvocationException(
                    f"No proxy endpoint configured for MCP '{mcp}'", mcp=mcp
                )

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
        }

        # Call proxy
        try:
            start_time = datetime.now()
            response = self.http_client.post(f"{proxy_url}/invoke", json=payload)
            execution_time = (datetime.now() - start_time).total_seconds()

            response.raise_for_status()
            data = response.json()

            result = MCPInvocationResult(
                mcp=mcp,
                action=action,
                result=data.get("result"),
                status=data.get("status", "success"),
                execution_time=execution_time,
                verified=data.get("verified", True),
                metadata=data.get("metadata", {}),
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

        # Prepare delegation request matching CsrgDelegationRequest
        payload = {
            "token": intent_token.raw_token,
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
            delegated_token_data = data.get("delegated_token") or data.get("new_token")
            if not delegated_token_data:
                raise DelegationException(
                    "Delegation response missing 'delegated_token'",
                    delegation_id=data.get("delegation_id"),
                )

            # Create IntentToken from delegated token
            delegated_token = IntentToken.model_validate(delegated_token_data)

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
        Verify an intent token with IAP (mainly for testing).
        
        Args:
            intent_token: Token to verify
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            response = self.http_client.post(
                f"{self.iap_endpoint}/verify", json={"token": intent_token.raw_token}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False
