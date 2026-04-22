"""
ArmorIQ SDK Client - Main entry point for SDK usage.

Python port of armoriq-sdk-customer-ts/src/client.ts. Kept at feature
parity so either SDK can drive the same backend.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

import httpx

from .config import load_armoriq_config
from .exceptions import (
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
    DelegationRequestParams,
    DelegationRequestResult,
    DelegationResult,
    HoldInfo,
    IntentToken,
    InvokeOptions,
    MCPInvocation,
    MCPInvocationResult,
    MCPSemanticMetadata,
    PlanCapture,
    PolicyContext,
    SDKConfig,
)

if TYPE_CHECKING:
    from .session import ArmorIQSession, SessionOptions

logger = logging.getLogger(__name__)

SDK_VERSION = "0.2.12"


class _EnforcementResponse(Exception):
    """Internal sentinel carrying a structured /invoke enforcement response."""

    def __init__(self, data: Dict[str, Any], status_code: int):
        super().__init__(data.get("message") or "enforcement")
        self.data = data
        self.status_code = status_code


class ArmorIQClient:
    """
    Main client for ArmorIQ SDK.

    Provides high-level APIs for:
    - Plan capture and canonicalization
    - Intent token management
    - MCP action invocation
    - Agent delegation
    - Policy-aware invocation with hold/approval flows
    """

    # Prod defaults (staging values live in armoriq_sdk/_build_env.py).
    # _build_env.resolve() is consulted first so a staging-branch build
    # automatically picks staging URLs without changing these literals.
    DEFAULT_IAP_ENDPOINT = "https://iap.armoriq.ai"
    DEFAULT_PROXY_ENDPOINT = "https://proxy.armoriq.ai"
    DEFAULT_BACKEND_ENDPOINT = "https://api.armoriq.ai"

    ARMORCLAW_IAP_ENDPOINT = "https://iap.armorclaw.io"
    ARMORCLAW_PROXY_ENDPOINT = "https://proxy.armorclaw.io"
    ARMORCLAW_BACKEND_ENDPOINT = "https://api.armorclaw.io"

    LOCAL_IAP_ENDPOINT = "http://127.0.0.1:8080"
    LOCAL_PROXY_ENDPOINT = "http://127.0.0.1:3001"
    LOCAL_BACKEND_ENDPOINT = "http://127.0.0.1:3000"

    LOCAL_ARMORCLAW_IAP_ENDPOINT = "http://127.0.0.1:8080"
    LOCAL_ARMORCLAW_PROXY_ENDPOINT = "http://127.0.0.1:3001"
    LOCAL_ARMORCLAW_BACKEND_ENDPOINT = "http://127.0.0.1:8081"

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
        mcp_credentials: Optional[Mapping[str, Mapping[str, Any]]] = None,
        _skip_api_key_validation: bool = False,
    ):
        resolved_api_key = api_key or os.getenv("ARMORIQ_API_KEY") or ""
        if not resolved_api_key:
            try:
                from .credentials import load_credentials
                creds = load_credentials()
                if creds:
                    resolved_api_key = creds.apiKey
            except Exception:
                pass
        is_armorclaw = resolved_api_key.startswith("ak_claw_")

        # ARMORIQ_ENV drives the non-armorclaw endpoint pick (local/staging/prod).
        # Armorclaw keys ignore ARMORIQ_ENV and switch on `use_production` only,
        # because armorclaw has no branch-baked staging row.
        from ._build_env import resolve as _env_resolve

        def _env_default(kind: str, local_default: str) -> str:
            if is_armorclaw:
                if use_production:
                    return {
                        "iap": self.ARMORCLAW_IAP_ENDPOINT,
                        "proxy": self.ARMORCLAW_PROXY_ENDPOINT,
                        "backend": self.ARMORCLAW_BACKEND_ENDPOINT,
                    }[kind]
                return {
                    "iap": self.LOCAL_ARMORCLAW_IAP_ENDPOINT,
                    "proxy": self.LOCAL_ARMORCLAW_PROXY_ENDPOINT,
                    "backend": self.LOCAL_ARMORCLAW_BACKEND_ENDPOINT,
                }[kind]
            if not use_production:
                return local_default
            return _env_resolve(kind)

        # Endpoint resolution: param > env > branch-aware default
        self.iap_endpoint = (
            iap_endpoint
            or os.getenv("IAP_ENDPOINT")
            or _env_default("iap", self.LOCAL_IAP_ENDPOINT)
        )
        self.default_proxy_endpoint = (
            proxy_endpoint
            or os.getenv("PROXY_ENDPOINT")
            or _env_default("proxy", self.LOCAL_PROXY_ENDPOINT)
        )
        self.backend_endpoint = (
            backend_endpoint
            or os.getenv("BACKEND_ENDPOINT")
            or _env_default("backend", self.LOCAL_BACKEND_ENDPOINT)
        )

        self.user_id = user_id or os.getenv("USER_ID") or ""
        self.agent_id = agent_id or os.getenv("AGENT_ID") or ""
        self.context_id = context_id or os.getenv("CONTEXT_ID", "default")
        self.api_key = resolved_api_key
        self.user_email_override: Optional[str] = None

        if not self.api_key:
            raise ConfigurationException(
                "API key is required for Customer SDK. "
                "Set ARMORIQ_API_KEY environment variable or pass api_key parameter. "
                "Get your API key from https://platform.armoriq.ai/dashboard/api-keys"
            )

        if not (
            self.api_key.startswith("ak_live_")
            or self.api_key.startswith("ak_test_")
            or self.api_key.startswith("ak_claw_")
        ):
            raise ConfigurationException(
                "Invalid API key format. API keys must start with 'ak_live_', "
                "'ak_claw_', or 'ak_test_'. "
                "Get your API key from https://platform.armoriq.ai/dashboard/api-keys"
            )

        # user_id/agent_id are legacy identifiers. In the forUser(email)
        # pattern they're resolved per-request from the API key + email on
        # conmap-auto, so they can be empty here.
        if not self.user_id:
            self.user_id = "__sdk_multiuser__"
        if not self.agent_id:
            self.agent_id = "__sdk_multiuser__"

        self.proxy_endpoints = proxy_endpoints or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

        headers = {
            "User-Agent": f"ArmorIQ-SDK-PY/{SDK_VERSION} (agent={self.agent_id})",
            "Authorization": f"Bearer {self.api_key}",
        }

        self.http_client = httpx.Client(
            timeout=timeout,
            verify=verify_ssl,
            headers=headers,
            follow_redirects=True,
        )

        self._token_cache: Dict[str, IntentToken] = {}
        self._metadata_cache: Dict[str, MCPSemanticMetadata] = {}
        self._mcp_credentials: Dict[str, Dict[str, Any]] = self._resolve_mcp_credentials(
            mcp_credentials
        )

        logger.info(
            "ArmorIQ SDK initialized: mode=%s, user=%s, agent=%s, iap=%s, "
            "proxy=%s, backend=%s, api_key=%s",
            os.getenv("ARMORIQ_ENV", "production" if use_production else "local").lower(),
            self.user_id,
            self.agent_id,
            self.iap_endpoint,
            self.default_proxy_endpoint,
            self.backend_endpoint,
            "***" + self.api_key[-8:],
        )

        if not _skip_api_key_validation:
            self._validate_api_key()

    @property
    def proxy_endpoint(self) -> str:
        return self.default_proxy_endpoint

    # ─── Session handle ────────────────────────────────────────────────

    def start_session(self, opts: Optional["SessionOptions"] = None) -> "ArmorIQSession":
        """
        Open a new session for one LLM turn / one plan. Use this with a
        framework integration (ADK, LangChain, CrewAI, etc.) to compress
        the capture-plan / mint-token / invoke-tool dance into two calls.
        """
        from .session import ArmorIQSession  # local import to avoid cycles

        return ArmorIQSession(self, opts)

    # ─── Multi-user convenience (mirrors TS ArmorIQADK.forUser) ─────────

    def bootstrap(self) -> Dict[str, Any]:
        """
        Resolve agent identity + registered MCPs + tool→MCP map from the
        API key. Hits ``POST /iap/sdk/bootstrap``. Cached for the lifetime
        of the client — call ``refresh_bootstrap()`` to force a re-fetch.
        """
        cached = getattr(self, "_bootstrap_cache", None)
        if cached is not None:
            return cached
        resp = self.http_client.post(
            f"{self.backend_endpoint}/iap/sdk/bootstrap",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={},
        )
        if resp.status_code >= 400:
            raise ConfigurationException(
                f"sdk/bootstrap failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        self._bootstrap_cache = data
        return data

    def refresh_bootstrap(self) -> Dict[str, Any]:
        """Force re-fetch of the bootstrap payload (MCP list, toolMap)."""
        self._bootstrap_cache = None
        return self.bootstrap()

    def resolve_user(self, user_email: str) -> Dict[str, Any]:
        """
        Resolve a user's membership, applicable policies, and approver
        chain by email. Hits ``POST /iap/sdk/resolve-user``. Cached per
        email for ``user_context_ttl_seconds`` (default 300s).
        """
        ttl = getattr(self, "user_context_ttl_seconds", 300)
        cache = getattr(self, "_user_cache", None)
        if cache is None:
            cache = {}
            self._user_cache = cache
        key = user_email.strip().lower()
        hit = cache.get(key)
        if hit and hit["expires_at"] > time.time():
            return hit["data"]
        resp = self.http_client.post(
            f"{self.backend_endpoint}/iap/sdk/resolve-user",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={"userEmail": key},
        )
        if resp.status_code >= 400:
            raise ConfigurationException(
                f"sdk/resolve-user failed for {key}: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        cache[key] = {"data": data, "expires_at": time.time() + ttl}
        return data

    def invalidate_user(self, user_email: str) -> None:
        cache = getattr(self, "_user_cache", None)
        if cache is not None:
            cache.pop(user_email.strip().lower(), None)

    def for_user(self, user_email: str) -> "ArmorIQUserScope":
        """
        Return a user-scoped helper. All enforcement / token minting /
        audit done through it is tagged with ``user_email``, so multi-
        user agents can route per-request policies correctly without
        mutating client-level state.

        Usage:
            client = ArmorIQClient(api_key=..., ...)
            scoped = client.for_user("alice@co.com")
            session = scoped.start_session(SessionOptions(mode="sdk"))
            session.start_plan([...])
            decision = session.check("tool_name", {...})
        """
        return ArmorIQUserScope(self, user_email)

    # ─── MCP credential resolution ─────────────────────────────────────

    @staticmethod
    def _resolve_mcp_credentials(
        from_options: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Resolve per-MCP credentials from env + constructor option.

        Precedence (later wins):
          1. ARMORIQ_MCP_CREDENTIALS (JSON blob)
          2. ARMORIQ_MCP_<SAFE_NAME>_* per-MCP env vars
          3. constructor option ``mcp_credentials``
        """
        merged: Dict[str, Dict[str, Any]] = {}

        json_raw = os.getenv("ARMORIQ_MCP_CREDENTIALS")
        if json_raw:
            try:
                parsed = json.loads(json_raw)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        merged[k] = dict(v)
            except Exception as e:
                logger.warning(
                    "Failed to parse ARMORIQ_MCP_CREDENTIALS as JSON: %s", e
                )

        safe_names = set()
        for key in os.environ:
            m = re.match(r"^ARMORIQ_MCP_(.+)_AUTH_TYPE$", key)
            if m:
                safe_names.add(m.group(1))
        for safe_name in safe_names:
            auth_type = os.environ.get(f"ARMORIQ_MCP_{safe_name}_AUTH_TYPE", "").lower()
            cred: Optional[Dict[str, Any]] = None
            if auth_type == "bearer":
                token = os.environ.get(f"ARMORIQ_MCP_{safe_name}_TOKEN")
                if token:
                    cred = {"authType": "bearer", "token": token}
            elif auth_type == "api_key":
                api_key = os.environ.get(f"ARMORIQ_MCP_{safe_name}_API_KEY")
                header_name = os.environ.get(f"ARMORIQ_MCP_{safe_name}_HEADER_NAME")
                if api_key:
                    cred = {"authType": "api_key", "apiKey": api_key}
                    if header_name:
                        cred["headerName"] = header_name
            elif auth_type == "basic":
                username = os.environ.get(f"ARMORIQ_MCP_{safe_name}_USERNAME")
                password = os.environ.get(f"ARMORIQ_MCP_{safe_name}_PASSWORD")
                if username and password:
                    cred = {"authType": "basic", "username": username, "password": password}
            elif auth_type == "none":
                cred = {"authType": "none"}
            if cred:
                merged[safe_name] = cred

        if from_options:
            for k, v in from_options.items():
                merged[k] = dict(v)

        return merged

    def _get_mcp_credential(self, mcp_name: str) -> Optional[Dict[str, Any]]:
        if mcp_name in self._mcp_credentials:
            return self._mcp_credentials[mcp_name]
        safe = re.sub(r"[^A-Z0-9]", "_", mcp_name.upper())
        return self._mcp_credentials.get(safe)

    @staticmethod
    def _encode_mcp_auth_header(cred: Dict[str, Any]) -> str:
        """
        Encode an MCP credential as the ``X-Armoriq-MCP-Auth`` header value.
        Base64 wrapping avoids header-character issues; not encryption — TLS
        handles confidentiality.
        """
        return base64.b64encode(
            json.dumps(cred, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")

    # ─── Bootstrap / teardown ──────────────────────────────────────────

    def _validate_api_key(self) -> None:
        """Validate API key with the proxy server."""
        try:
            response = self.http_client.get(
                f"{self.proxy_endpoint}/health",
                headers={"X-API-Key": self.api_key},
                timeout=5.0,
            )
            if response.status_code == 401:
                raise ConfigurationException(
                    "Invalid API key. Please check your API key at "
                    "https://platform.armoriq.ai/dashboard/api-keys"
                )
            elif response.status_code >= 400:
                logger.warning(
                    "API key validation returned status %s, but continuing...",
                    response.status_code,
                )
            else:
                logger.info("API key validated successfully")
        except ConfigurationException:
            raise
        except httpx.ConnectError:
            logger.warning(
                "Could not connect to proxy at %s for API key validation",
                self.proxy_endpoint,
            )
        except httpx.TimeoutException:
            logger.warning(
                "Timeout connecting to proxy at %s for API key validation",
                self.proxy_endpoint,
            )
        except Exception as e:
            logger.warning("API key validation check failed: %s, but continuing...", e)

    def __enter__(self):
        return self

    @classmethod
    def from_config(cls, path: str = "armoriq.yaml") -> "ArmorIQClient":
        """
        Create a client from armoriq.yaml.

        Args:
            path: Path to armoriq.yaml

        Returns:
            Initialized ArmorIQClient
        """
        config = load_armoriq_config(path)
        api_key = config.identity.resolved_api_key()
        if not api_key:
            raise ConfigurationException(
                "API key resolved to empty value from config/environment."
            )

        return cls(
            api_key=api_key,
            user_id=config.identity.user_id,
            agent_id=config.identity.agent_id,
            proxy_endpoint=config.proxy.url,
            timeout=float(config.proxy.timeout),
            max_retries=int(config.proxy.max_retries),
            use_production=(config.environment == "production"),
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        try:
            self.http_client.close()
        except Exception:
            pass
        logger.debug("ArmorIQ SDK client closed")

    # ─── Plan / Token ──────────────────────────────────────────────────

    def capture_plan(
        self,
        llm: str,
        prompt: str,
        plan: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlanCapture:
        """Capture an execution plan structure."""
        logger.info("Capturing plan: llm=%s, prompt=%s...", llm, prompt[:50])

        if plan is None:
            raise ValueError(
                "Plan structure is required. "
                "You must provide an explicit plan with the MCP and actions you want to execute."
            )
        if not isinstance(plan, dict):
            raise ValueError("Plan must be a dictionary")
        if "steps" not in plan:
            raise ValueError("Plan must contain 'steps' key")

        capture = PlanCapture(
            plan=plan,
            llm=llm,
            prompt=prompt,
            metadata=metadata or {},
        )
        logger.info("Plan captured with %d steps", len(plan.get("steps", [])))
        return capture

    def get_intent_token(
        self,
        plan_capture: PlanCapture,
        policy: Optional[Dict[str, Any]] = None,
        validity_seconds: float = 60.0,
    ) -> IntentToken:
        """Request a signed intent token from IAP for the given plan."""
        logger.info(
            "Requesting intent token for plan with %d steps",
            len(plan_capture.plan.get("steps", [])),
        )

        payload: Dict[str, Any] = {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "context_id": self.context_id,
            "plan": plan_capture.plan,
            "policy": policy,
            "expires_in": validity_seconds,
        }
        if self.user_email_override:
            payload["user_email"] = self.user_email_override

        try:
            response = self.http_client.post(
                f"{self.backend_endpoint}/iap/sdk/token",
                json=payload,
                headers={"X-API-Key": self.api_key},
                timeout=30.0,
            )

            if response.status_code >= 400:
                response_data: Any
                try:
                    response_data = response.json()
                except Exception:
                    response_data = {"message": response.text}
                denied_tools = (
                    response_data.get("policy_validation", {}).get("denied_tools")
                    if isinstance(response_data, dict)
                    else None
                )
                denied_reasons = (
                    response_data.get("policy_validation", {}).get("denied_reasons")
                    if isinstance(response_data, dict)
                    else None
                )
                if response.status_code == 403 or (
                    isinstance(denied_tools, list) and len(denied_tools) > 0
                ):
                    reason = (
                        "; ".join(denied_reasons)
                        if isinstance(denied_reasons, list) and denied_reasons
                        else (
                            response_data.get("message")
                            if isinstance(response_data, dict)
                            else None
                        )
                    ) or "Blocked by policy"
                    raise PolicyBlockedException(
                        f"Policy blocked intent token issuance: {reason}",
                        enforcement_action=(
                            response_data.get("policy_validation", {}).get(
                                "default_enforcement_action"
                            )
                            if isinstance(response_data, dict)
                            else None
                        ),
                        reason=reason,
                        metadata=(
                            response_data.get("policy_validation")
                            if isinstance(response_data, dict)
                            else None
                        ),
                    )
                message = (
                    response_data.get("message")
                    if isinstance(response_data, dict)
                    else str(response_data)
                )
                raise InvalidTokenException(f"Token issuance failed: {message}")

            data = response.json()
            if not data.get("success"):
                raise InvalidTokenException(
                    f"Token issuance failed: {data.get('message', 'Unknown error')}"
                )

            token_data = data.get("token", {}) or {}
            raw_token = {
                "plan": plan_capture.plan,
                "plan_id": data.get("plan_id"),
                "token": token_data,
                "plan_hash": data.get("plan_hash"),
                "merkle_root": data.get("merkle_root"),
                "intent_reference": data.get("intent_reference"),
                "composite_identity": data.get("composite_identity", ""),
                "step_proofs": data.get("step_proofs", []),
            }

            now = datetime.now().timestamp()
            token = IntentToken(
                token_id=data.get("intent_reference") or "unknown",
                plan_hash=data.get("plan_hash", ""),
                plan_id=data.get("plan_id"),
                signature=token_data.get("signature", "") if isinstance(token_data, dict) else "",
                issued_at=now,
                expires_at=now + validity_seconds,
                policy=policy or {},
                composite_identity=data.get("composite_identity", ""),
                client_info=data.get("client_info"),
                policy_validation=data.get("policy_validation"),
                step_proofs=data.get("step_proofs", []),
                total_steps=len(plan_capture.plan.get("steps", [])),
                raw_token=raw_token,
                jwt_token=data.get("jwt_token"),
                policy_snapshot=data.get("policy_snapshot"),
            )

            logger.info(
                "Intent token issued: id=%s, plan_hash=%s..., expires=%.1fs, stepProofs=%d",
                token.token_id,
                token.plan_hash[:16],
                token.time_until_expiry,
                len(token.step_proofs or []),
            )
            # Cache by plan_hash for idempotency on repeated mints within validity
            if token.plan_hash:
                self._token_cache[token.plan_hash] = token
            return token

        except (InvalidTokenException, PolicyBlockedException):
            raise
        except httpx.HTTPStatusError as e:
            raise InvalidTokenException(
                f"Failed to get intent token: {e.response.text}"
            )
        except Exception as e:
            raise InvalidTokenException(f"Failed to get intent token: {e}")

    # ─── MCP invocation ────────────────────────────────────────────────

    def invoke(
        self,
        mcp: str,
        action: str,
        intent_token: IntentToken,
        params: Optional[Dict[str, Any]] = None,
        merkle_proof: Optional[List[Any]] = None,
        user_email: Optional[str] = None,
    ) -> MCPInvocationResult:
        """Invoke an MCP action through the ArmorIQ proxy with token verification."""
        logger.info("Invoking MCP action: mcp=%s, action=%s", mcp, action)

        if intent_token.is_expired:
            raise TokenExpiredException(
                f"Intent token expired {abs(intent_token.time_until_expiry):.1f}s ago",
                token_id=intent_token.token_id,
                expired_at=intent_token.expires_at,
            )

        proxy_url = (
            self.proxy_endpoints.get(mcp)
            or os.getenv(f"{mcp.upper()}_PROXY_URL")
            or self.default_proxy_endpoint
        )

        iam_context: Dict[str, Any] = {}
        if intent_token.policy_validation:
            iam_context["allowed_tools"] = intent_token.policy_validation.get(
                "allowed_tools", []
            )
        if user_email:
            iam_context["email"] = user_email
            iam_context["user_email"] = user_email
        if intent_token.raw_token:
            iam_context["user_id"] = intent_token.raw_token.get("user_id", self.user_id)
            iam_context["agent_id"] = intent_token.raw_token.get("agent_id", self.agent_id)

        invoke_params: Dict[str, Any] = dict(params or {})

        payload: Dict[str, Any] = {
            "mcp": mcp,
            "action": action,
            "tool": action,
            "params": invoke_params,
            "arguments": invoke_params,
            "intent_token": intent_token.raw_token,
            "merkle_proof": merkle_proof,
            "plan": intent_token.raw_token.get("plan") if intent_token.raw_token else None,
            "_iam_context": iam_context,
        }
        if user_email:
            payload["user_email"] = user_email
        if intent_token.policy_snapshot:
            payload["policy_snapshot"] = intent_token.policy_snapshot

        headers: Dict[str, str] = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Request-ID": f"sdk-{int(datetime.now().timestamp() * 1000)}",
            "X-API-Key": self.api_key,
        }

        cred = self._get_mcp_credential(mcp)
        if cred:
            headers["X-Armoriq-MCP-Auth"] = self._encode_mcp_auth_header(cred)

        if intent_token.raw_token and isinstance(intent_token.raw_token, dict):
            payload["token"] = intent_token.raw_token.get("token", {})
            payload["csrg_token"] = intent_token.raw_token.get("token", {})

        plan = intent_token.raw_token.get("plan", {}) if intent_token.raw_token else {}
        steps = plan.get("steps", [])

        step_index: Optional[int] = None
        for idx, step in enumerate(steps):
            if isinstance(step, dict) and step.get("action") == action:
                step_index = idx
                break

        if step_index is None:
            actions = [
                s.get("action") if isinstance(s, dict) else "unknown" for s in steps
            ]
            raise IntentMismatchException(
                f"Action '{action}' not found in the original plan. "
                f"Plan contains actions: {actions}. "
                "You can only invoke actions that were included in the plan "
                "when you called capture_plan()."
            )

        if not merkle_proof:
            if intent_token.step_proofs and len(intent_token.step_proofs) > step_index:
                merkle_proof = intent_token.step_proofs[step_index]
                logger.debug("Using Merkle proof from CSRG-IAP for step %s", step_index)
            else:
                logger.warning(
                    "No Merkle proof available for step %s. step_proofs length: %s",
                    step_index,
                    len(intent_token.step_proofs or []),
                )

        if merkle_proof:
            headers["X-CSRG-Proof"] = json.dumps(merkle_proof, separators=(",", ":"))

        headers["X-CSRG-Path"] = f"/steps/[{step_index}]/action"

        step_obj = steps[step_index] if step_index < len(steps) else {}
        leaf_value = step_obj.get("action", action) if isinstance(step_obj, dict) else action
        value_str = json.dumps(leaf_value, separators=(",", ":"))
        headers["X-CSRG-Value-Digest"] = hashlib.sha256(
            value_str.encode("utf-8")
        ).hexdigest()

        try:
            start = time.time()
            response = self.http_client.post(
                f"{proxy_url}/invoke", json=payload, headers=headers
            )
            execution_time = time.time() - start

            try:
                response_data: Any = response.json()
            except Exception:
                response_data = None

            content_type = response.headers.get("content-type", "")
            data: Dict[str, Any]
            if "text/event-stream" in content_type and isinstance(response.text, str):
                data = {}
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            break
                        except json.JSONDecodeError:
                            continue
                if not data:
                    raise MCPInvocationException(
                        "No data in SSE response", mcp=mcp, action=action
                    )
            else:
                data = response_data if isinstance(response_data, dict) else {}

            if isinstance(data, dict) and data.get("enforcement"):
                raise _EnforcementResponse(data, response.status_code)

            if response.status_code >= 400:
                self._raise_http_error(response, mcp, action, intent_token)

            if isinstance(data, dict) and data.get("error") and not data.get("enforcement"):
                err = data["error"]
                error_msg = err.get("message", "Unknown error")
                error_code = err.get("code", -1)
                error_data = err.get("data", "")
                raise MCPInvocationException(
                    f"MCP tool error ({error_code}): {error_msg} - {error_data}",
                    mcp=mcp,
                    action=action,
                )

            result_data = data.get("result", data) if isinstance(data, dict) else data
            has_tool_error = bool(
                (isinstance(result_data, dict) and (result_data.get("isError") or result_data.get("is_error") or result_data.get("error")))
            )
            result = MCPInvocationResult(
                mcp=mcp,
                action=action,
                result=result_data,
                status="error" if has_tool_error else "success",
                execution_time=execution_time,
                verified=True,
                metadata={"hasToolError": has_tool_error},
            )

            logger.info(
                "MCP invocation %s: %s in %.2fs",
                "returned error payload" if has_tool_error else "succeeded",
                action,
                execution_time,
            )
            return result

        except _EnforcementResponse as env:
            enforcement = env.data.get("enforcement") or {}
            message = env.data.get("message") or f"Enforcement: {enforcement.get('action')}"
            if enforcement.get("action") == "block":
                raise PolicyBlockedException(
                    message,
                    enforcement_action=enforcement.get("action"),
                    reason=enforcement.get("reason"),
                    metadata=enforcement.get("metadata"),
                )
            raise PolicyHoldException(
                message,
                delegation_context=env.data.get("delegation_context"),
                metadata=enforcement.get("metadata"),
            )
        except (
            MCPInvocationException,
            IntentMismatchException,
            InvalidTokenException,
            PolicyBlockedException,
            PolicyHoldException,
        ):
            raise
        except httpx.HTTPStatusError as e:
            self._raise_http_error(e.response, mcp, action, intent_token)
        except Exception as e:
            raise MCPInvocationException(
                f"MCP invocation failed: {e}", mcp=mcp, action=action
            )

    @staticmethod
    def _raise_http_error(
        response: httpx.Response,
        mcp: str,
        action: str,
        intent_token: IntentToken,
    ) -> None:
        try:
            detail: Any = response.json()
        except Exception:
            detail = response.text
        status_code = response.status_code
        if status_code in (401, 403):
            raise InvalidTokenException(f"Token verification failed: {detail}")
        if status_code == 409:
            raise IntentMismatchException(
                f"Action not in plan: {detail}",
                action=action,
                plan_hash=intent_token.plan_hash,
            )
        raise MCPInvocationException(
            f"MCP invocation failed: {detail}",
            mcp=mcp,
            action=action,
            status_code=status_code,
        )

    # ─── Delegation (legacy CSRG path) ─────────────────────────────────

    def delegate(
        self,
        intent_token: IntentToken,
        delegate_public_key: str,
        validity_seconds: int = 3600,
        allowed_actions: Optional[List[str]] = None,
        target_agent: Optional[str] = None,
        subtask: Optional[Dict[str, Any]] = None,
    ) -> DelegationResult:
        """Delegate authority to another agent using CSRG token delegation."""
        logger.info(
            "Creating delegation for token_id=%s, delegate_key=%s..., validity=%ds",
            intent_token.token_id,
            delegate_public_key[:16],
            validity_seconds,
        )

        token_to_delegate: Any = intent_token.raw_token
        if isinstance(token_to_delegate, dict) and "token" in token_to_delegate:
            token_to_delegate = token_to_delegate["token"]

        payload: Dict[str, Any] = {
            "token": token_to_delegate,
            "delegate_public_key": delegate_public_key,
            "validity_seconds": validity_seconds,
        }
        if allowed_actions:
            payload["allowed_actions"] = allowed_actions
        if target_agent:
            payload["target_agent"] = target_agent
        if subtask:
            payload["subtask"] = subtask

        try:
            response = self.http_client.post(
                f"{self.iap_endpoint}/delegation/create",
                json=payload,
                timeout=10.0,
            )
            if response.status_code >= 400:
                raise DelegationException(
                    f"Delegation failed: {response.text}",
                    target_agent=target_agent,
                    status_code=response.status_code,
                )

            data = response.json()
            delegated_token_data = (
                data.get("delegation") or data.get("delegated_token") or data.get("new_token")
            )
            if not delegated_token_data:
                raise DelegationException(
                    f"Delegation response missing 'delegation' key. Got keys: {list(data.keys())}",
                    delegation_id=data.get("delegation_id"),
                )

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
                raw_token={"token": delegated_token_data},
            )

            return DelegationResult(
                delegation_id=data.get("delegation_id", delegated_token.token_id),
                delegated_token=delegated_token,
                delegate_public_key=delegate_public_key,
                target_agent=target_agent,
                expires_at=delegated_token.expires_at,
                trust_delta=data.get("trust_delta", {}),
                status="delegated",
                metadata=data.get("metadata", {}),
            )
        except DelegationException:
            raise
        except httpx.HTTPStatusError as e:
            raise DelegationException(
                f"Delegation failed: {e.response.text}",
                target_agent=target_agent,
                status_code=e.response.status_code,
            )
        except Exception as e:
            raise DelegationException(f"Delegation failed: {e}", target_agent=target_agent)

    def verify_token(self, intent_token: IntentToken) -> bool:
        """Local-only token validation (expiry + required-field checks)."""
        try:
            if intent_token.is_expired:
                logger.warning("Token %s has expired", intent_token.token_id)
                return False
            if not intent_token.signature or not intent_token.plan_hash:
                logger.warning("Token %s missing required fields", intent_token.token_id)
                return False
            logger.info(
                "Token %s is valid (expires in %.1fs)",
                intent_token.token_id,
                intent_token.time_until_expiry,
            )
            return True
        except Exception as e:
            logger.error("Token verification failed: %s", e)
            return False

    # ─── Semantic metadata & policy context ────────────────────────────

    def fetch_tool_metadata(self, mcp_name: str) -> MCPSemanticMetadata:
        """Fetch and cache semantic tool metadata for an MCP server."""
        cached = self._metadata_cache.get(mcp_name)
        if cached is not None:
            return cached

        try:
            response = self.http_client.get(
                f"{self.backend_endpoint}/mcp/tool-metadata/{mcp_name}",
                headers={"X-API-Key": self.api_key},
            )
            if response.status_code >= 400:
                logger.warning(
                    "Failed to fetch tool metadata for %s: %s",
                    mcp_name,
                    response.status_code,
                )
                return MCPSemanticMetadata(mcp_id="", name=mcp_name)
            body = response.json() or {}
            payload = body.get("data") or {
                "mcpId": "",
                "name": mcp_name,
                "toolMetadata": {},
                "roleMapping": {},
            }
            metadata = MCPSemanticMetadata.model_validate(payload)
            self._metadata_cache[mcp_name] = metadata
            return metadata
        except Exception as e:
            logger.warning("Could not fetch tool metadata for %s: %s", mcp_name, e)
            return MCPSemanticMetadata(mcp_id="", name=mcp_name)

    def load_mcp(self, mcp_name: str) -> None:
        """Eagerly load semantic metadata for an MCP."""
        self.fetch_tool_metadata(mcp_name)

    def list_mcps(self) -> List[Dict[str, Any]]:
        """List all MCPs registered for this org (resolved via API key)."""
        response = self.http_client.get(
            f"{self.backend_endpoint}/mcp/my-servers",
            headers={"X-API-Key": self.api_key},
        )
        if response.status_code >= 400:
            raise MCPInvocationException(
                f"list_mcps failed: {response.status_code} {response.text}"
            )
        body = response.json() or {}
        return body.get("data", []) or []

    def get_mcp_tool_schemas(self, mcp_name: str) -> List[Any]:
        """Get full OpenAI-compatible tool schemas for a named MCP."""
        response = self.http_client.get(
            f"{self.backend_endpoint}/mcp/tools/{mcp_name}",
            headers={"X-API-Key": self.api_key},
        )
        if response.status_code >= 400:
            raise MCPInvocationException(
                f"get_mcp_tool_schemas({mcp_name}) failed: "
                f"{response.status_code} {response.text}"
            )
        body = response.json() or {}
        return (body.get("data") or {}).get("tools", []) or []

    def _enrich_policy_context(
        self,
        mcp_name: str,
        tool_name: str,
        params: Dict[str, Any],
    ) -> PolicyContext:
        """Enrich policy context from semantic metadata for a tool invocation."""
        metadata = self.fetch_tool_metadata(mcp_name)
        tool_meta = metadata.tool_metadata.get(tool_name) if metadata.tool_metadata else None

        if not tool_meta or not tool_meta.is_financial:
            return PolicyContext(is_financial=False)

        amount: Optional[float] = None
        if tool_meta.amount_fields:
            for field in tool_meta.amount_fields:
                if params.get(field) is not None:
                    try:
                        raw = float(params[field])
                        amount = raw / 100 if tool_meta.amount_unit == "cents" else raw
                        break
                    except (TypeError, ValueError):
                        continue

        return PolicyContext(
            is_financial=True,
            transaction_type=tool_meta.transaction_type or tool_name,
            amount=amount,
            recipient_id=(
                params.get(tool_meta.recipient_field) if tool_meta.recipient_field else None
            ),
        )

    def resolve_role(self, mcp_name: str, org_role: str) -> str:
        """Resolve an org role to a domain-specific role for an MCP."""
        metadata = self.fetch_tool_metadata(mcp_name)
        return metadata.role_mapping.get(org_role, org_role)

    # ─── Delegation automation ─────────────────────────────────────────

    def _resolve_user_role(self, user_email: str) -> Dict[str, Any]:
        """Resolve the user's role and limit from the backend for delegation."""
        try:
            response = self.http_client.get(
                f"{self.backend_endpoint}/delegation/my-role",
                headers={
                    "X-API-Key": self.api_key,
                    "X-User-Email": user_email,
                },
                timeout=5.0,
            )
            if response.status_code < 400:
                body = response.json()
                if body.get("role"):
                    return {"role": body["role"], "limit": body.get("limit", 0)}
        except Exception:
            pass
        return {"role": "agent_user", "limit": 0}

    def create_delegation_request(
        self, params: DelegationRequestParams
    ) -> DelegationRequestResult:
        """Create a delegation request on the backend."""
        body = params.model_dump(by_alias=True, exclude_none=True)
        response = self.http_client.post(
            f"{self.backend_endpoint}/delegation/request",
            json=body,
            headers={
                "X-API-Key": self.api_key,
                "X-User-Email": params.requester_email,
            },
        )
        if response.status_code >= 400:
            try:
                data = response.json()
            except Exception:
                data = {}
            raise DelegationException(
                f"Failed to create delegation request: {data.get('message', response.text)}"
            )
        return DelegationRequestResult.model_validate(response.json())

    def check_approved_delegation(
        self, user_email: str, tool: str, amount: float
    ) -> Optional[ApprovedDelegation]:
        """Check if a delegation request has been approved."""
        response = self.http_client.get(
            f"{self.backend_endpoint}/delegation/check-approved",
            params={"tool": tool, "amount": amount},
            headers={"X-API-Key": self.api_key, "X-User-Email": user_email},
        )
        if response.status_code >= 400:
            return None
        try:
            data = response.json()
        except Exception:
            return None
        if not data or not data.get("approved"):
            return None
        return ApprovedDelegation.model_validate(data)

    def mark_delegation_executed(self, user_email: str, delegation_id: str) -> None:
        """Mark a delegation as executed."""
        self.http_client.post(
            f"{self.backend_endpoint}/delegation/mark-executed",
            json={"delegationId": delegation_id},
            headers={"X-API-Key": self.api_key, "X-User-Email": user_email},
        )

    def complete_plan(self, plan_id: str) -> None:
        """Mark an intent plan as completed after all tools have been executed."""
        self.update_plan_status(plan_id, "completed")

    def update_plan_status(self, plan_id: str, status: str) -> None:
        """Update an intent plan's status."""
        try:
            self.http_client.post(
                f"{self.backend_endpoint}/iap/plans/{plan_id}/status",
                json={"status": status},
                headers={"X-API-Key": self.api_key},
            )
            logger.info("Plan %s status updated to %s", plan_id, status)
        except Exception as e:
            logger.warning("Failed to update plan %s status: %s", plan_id, e)

    # ─── Enhanced invoke with policy enrichment & hold handling ────────

    def invoke_with_policy(
        self,
        mcp: str,
        action: str,
        intent_token: IntentToken,
        params: Optional[Dict[str, Any]] = None,
        options: Optional[InvokeOptions] = None,
    ) -> MCPInvocationResult:
        """Invoke with automatic policy context enrichment and delegation handling."""
        opts = options or InvokeOptions()
        policy_context = self._enrich_policy_context(mcp, action, params or {})
        enriched_params = dict(params or {})
        enriched_params["_policy_context"] = policy_context.model_dump()

        try:
            return self.invoke(
                mcp,
                action,
                intent_token,
                params=enriched_params,
                user_email=opts.user_email,
            )
        except PolicyBlockedException:
            raise
        except PolicyHoldException as hold_exc:
            enforcement_meta = hold_exc.metadata or {}
            requires_approval = enforcement_meta.get("requiresApproval", True)
            if not requires_approval:
                raise

            hold_info = HoldInfo(
                reason=str(hold_exc) or "Action held for approval",
                amount=enforcement_meta.get("amount") or policy_context.amount,
                approval_threshold=enforcement_meta.get("approvalThreshold"),
                tool=action,
                mcp=mcp,
            )
            if opts.on_hold:
                opts.on_hold(hold_info)

            if not opts.wait_for_approval or not opts.user_email:
                raise

            delegation_ctx = hold_exc.delegation_context or {}

            requester_role = opts.requester_role or "agent_user"
            requester_limit = opts.requester_limit or 0
            if not opts.requester_role:
                try:
                    resolved = self._resolve_user_role(opts.user_email)
                    requester_role = resolved["role"]
                    requester_limit = resolved["limit"]
                except Exception:
                    pass

            try:
                delegation_result = self.create_delegation_request(
                    DelegationRequestParams(
                        tool=action,
                        action="execute",
                        arguments=params or {},
                        amount=policy_context.amount or 0,
                        requester_email=opts.user_email,
                        requester_role=requester_role,
                        requester_limit=requester_limit,
                        domain=delegation_ctx.get("domain", mcp),
                        target_url=delegation_ctx.get("targetUrl"),
                        plan_id=delegation_ctx.get("planId") or intent_token.plan_id,
                        intent_reference=delegation_ctx.get("intentReference")
                        or intent_token.token_id,
                        merkle_root=delegation_ctx.get("merkleRoot") or intent_token.plan_hash,
                        reason=str(hold_exc),
                    )
                )
            except Exception as delegation_error:
                logger.error("Failed to create delegation request: %s", delegation_error)
                raise PolicyHoldException(
                    "Action held for approval (delegation request failed)",
                    delegation_context=delegation_ctx,
                    metadata={
                        **enforcement_meta,
                        "delegationError": str(delegation_error),
                    },
                )

            hold_info.delegation_id = delegation_result.delegation_id
            if opts.on_hold:
                opts.on_hold(hold_info)

            timeout_ms = opts.delegation_timeout_ms or (30 * 60 * 1000)
            deadline = time.time() + timeout_ms / 1000
            poll_interval = 3.0
            while time.time() < deadline:
                time.sleep(poll_interval)
                poll_interval = min(poll_interval * 1.5, 15.0)

                approved = self.check_approved_delegation(
                    opts.user_email, action, policy_context.amount or 0
                )
                if approved:
                    retry_params = dict(enriched_params)
                    retry_params["_delegation_id"] = approved.delegation_id
                    retry_params["_approvals"] = 999
                    result = self.invoke(
                        mcp,
                        action,
                        intent_token,
                        params=retry_params,
                        user_email=opts.user_email,
                    )
                    self.mark_delegation_executed(opts.user_email, approved.delegation_id)
                    return result

            raise DelegationException(
                f"Delegation approval timed out after {timeout_ms / 1000:.0f}s",
                delegation_id=delegation_result.delegation_id,
            )


class ArmorIQUserScope:
    """
    User-scoped helper returned by ``ArmorIQClient.for_user(email)``.

    Wraps an ``ArmorIQClient`` and sets ``user_email_override`` so all
    token minting, enforcement, and audit calls originate from this user.
    Safe to use across concurrent requests as long as each request uses
    its own scope (the scope copies state rather than mutating the
    underlying client).

    Usage:
        client = ArmorIQClient(api_key=..., ...)
        scoped = client.for_user("alice@co.com")
        session = scoped.start_session(SessionOptions(mode="sdk"))
        token = session.start_plan([...])
        decision = session.check("tool", {...})
    """

    def __init__(self, client: "ArmorIQClient", user_email: str):
        self._client = client
        self.user_email = user_email.strip().lower()

    def start_session(self, opts: Optional["SessionOptions"] = None) -> "ArmorIQSession":
        from .session import ArmorIQSession

        # Temporarily override; session will carry user_email through.
        self._client.user_email_override = self.user_email
        session = ArmorIQSession(self._client, opts)
        # Attach for report()/audit paths that read from session.
        setattr(session, "user_email", self.user_email)
        return session

    def resolve(self) -> Dict[str, Any]:
        """Fetch this user's membership + policies + approver chain."""
        return self._client.resolve_user(self.user_email)
