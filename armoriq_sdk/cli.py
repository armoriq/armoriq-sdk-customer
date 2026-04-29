"""
ArmorIQ CLI entrypoint.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .config import (
    ArmorIQConfig,
    ArmorIQConfigError,
    IdentityConfig,
    IntentConfig,
    MCPAuthConfig,
    MCPServerConfig,
    PolicyConfig,
    ProxyConfig,
    load_armoriq_config,
    resolve_env_reference,
    save_armoriq_config,
)


CHECK = "\u2713"
STATE_DIR = Path.home() / ".armoriq"
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "cli.log"
import os as _os

from ._build_env import resolve as _resolve_env_endpoint

# Precedence for the /iap/sdk/register URL:
#   1. ARMORIQ_REGISTER_URL — full URL override (power user / CI)
#   2. BACKEND_ENDPOINT or ARMORIQ_BACKEND_URL — append /iap/sdk/register
#   3. ARMORIQ_ENV (env var) — picks "production" or "staging" from _build_env
#   4. _build_env.ARMORIQ_ENV baked-in default (production on main, staging on dev)
def _resolve_control_plane_endpoint() -> str:
    explicit = _os.getenv("ARMORIQ_REGISTER_URL")
    if explicit:
        return explicit
    backend = _os.getenv("BACKEND_ENDPOINT") or _os.getenv("ARMORIQ_BACKEND_URL")
    if backend:
        return f"{backend.rstrip('/')}/iap/sdk/register"
    return f"{_resolve_env_endpoint('backend').rstrip('/')}/iap/sdk/register"


CONTROL_PLANE_REGISTER_ENDPOINT = _resolve_control_plane_endpoint()


class CLIError(RuntimeError):
    """CLI command failure."""


@dataclass
class MCPDiscoveryResult:
    reachable: bool
    tools: List[str]
    error: Optional[str] = None


def _print(message: str = "") -> None:
    sys.stdout.write(f"{message}\n")


def _mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}***{secret[-4:]}"


def _load_state() -> Dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: Dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(event: str, details: Dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
        }
    )
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")


def _prompt(question: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    response = input(f"{question}{suffix}: ").strip()
    return response if response else (default or "")


def _prompt_yes_no(question: str, default: bool = False) -> bool:
    default_raw = "y" if default else "n"
    response = _prompt(question, default_raw).lower()
    return response in {"y", "yes"}


def _looks_like_auth_error(error: Optional[str]) -> bool:
    if not error:
        return False
    lower = error.lower()
    return "401" in error or "403" in error or "unauthorized" in lower or "forbidden" in lower


def _prompt_mcp_auth() -> MCPAuthConfig:
    while True:
        auth_type = _prompt("Auth method — type 'bearer' or 'api_key'", "bearer").strip().lower()
        if auth_type in {"bearer", "api_key"}:
            break
        _print("  Please type 'bearer' or 'api_key' (or press Enter for bearer).")
    if auth_type == "bearer":
        while True:
            token = _prompt("Bearer token (value or $ENV_VAR)").strip()
            if token:
                return MCPAuthConfig(type="bearer", token=token)
            _print("  Token cannot be empty.")
    while True:
        key_value = _prompt("API key (value or $ENV_VAR)").strip()
        if key_value:
            return MCPAuthConfig(type="api_key", api_key=key_value)
        _print("  API key cannot be empty.")


def _auto_server_id(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "server").lower()
    parts = [part for part in hostname.split(".") if part]
    if len(parts) >= 3 and parts[0] in {"mcp", "api"}:
        return re.sub(r"[^a-z0-9-]", "-", parts[1])
    if len(parts) >= 2:
        return re.sub(r"[^a-z0-9-]", "-", parts[-2])
    return re.sub(r"[^a-z0-9-]", "-", parts[0]) if parts else "server"


def _resolve_auth_headers(auth: MCPAuthConfig) -> Dict[str, str]:
    if auth.type == "none":
        return {}
    if auth.type == "bearer":
        token = resolve_env_reference(auth.token or "")
        if not token:
            raise CLIError("bearer token is empty after env resolution")
        return {"Authorization": f"Bearer {token}"}
    api_key = resolve_env_reference(auth.api_key or "")
    if not api_key:
        raise CLIError("api_key auth value is empty after env resolution")
    return {"X-API-Key": api_key}


def _extract_tool_names(payload: object) -> List[str]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], str):
            return sorted(set(str(item) for item in payload))
        if payload and isinstance(payload[0], dict):
            names = [item.get("name") for item in payload if isinstance(item, dict) and item.get("name")]
            return sorted(set(names))
        return []
    if isinstance(payload, dict):
        if "tools" in payload:
            return _extract_tool_names(payload.get("tools"))
        if "result" in payload:
            return _extract_tool_names(payload.get("result"))
    return []


def _parse_mcp_body(body: str) -> object:
    match = re.search(r"data:\s*(\{.*\})", body)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return json.loads(body)


def discover_mcp_tools(server: MCPServerConfig, timeout: float = 8.0) -> MCPDiscoveryResult:
    try:
        auth_headers = _resolve_auth_headers(server.auth)
    except CLIError as exc:
        return MCPDiscoveryResult(reachable=False, tools=[], error=str(exc))

    base_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2024-11-05",
    }
    headers = {**base_headers, **auth_headers}

    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ArmorIQ-CLI", "version": "1.0.0"},
        },
        "id": 1,
    }
    tools_request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}

    url = server.url.rstrip("/")
    parsed = urlparse(server.url)
    candidates = [url]
    if not parsed.path or parsed.path == "/":
        candidates.extend([f"{url}/mcp", f"{url}/sse"])

    last_error: Optional[str] = None

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            for candidate in candidates:
                try:
                    init_resp = client.post(candidate, json=init_request, headers=headers)
                except Exception as exc:
                    last_error = str(exc)
                    continue
                if init_resp.status_code >= 400:
                    last_error = f"HTTP {init_resp.status_code}"
                    if init_resp.status_code in (401, 403):
                        break
                    continue

                session_headers = dict(headers)
                session_id = init_resp.headers.get("mcp-session-id")
                if session_id:
                    session_headers["mcp-session-id"] = session_id
                _ = init_resp.text

                try:
                    tools_resp = client.post(candidate, json=tools_request, headers=session_headers)
                except Exception as exc:
                    last_error = str(exc)
                    continue
                if tools_resp.status_code >= 400:
                    last_error = f"HTTP {tools_resp.status_code}"
                    continue

                try:
                    payload = _parse_mcp_body(tools_resp.text)
                except Exception as exc:
                    last_error = f"invalid response body: {exc}"
                    continue

                if isinstance(payload, dict) and payload.get("error"):
                    err = payload["error"]
                    msg = err.get("message") if isinstance(err, dict) else str(err)
                    last_error = f"MCP error: {msg}"
                    continue

                tools = _extract_tool_names(payload)
                return MCPDiscoveryResult(reachable=True, tools=tools)
    except Exception as exc:
        return MCPDiscoveryResult(reachable=False, tools=[], error=str(exc))

    return MCPDiscoveryResult(reachable=False, tools=[], error=last_error or "unreachable")


def validate_api_key(api_key: str, proxy_url: str, timeout: float = 8.0) -> None:
    """Verify the API key by hitting either the backend's SDK bootstrap
    endpoint (local dev) or the proxy's health endpoint (prod default).

    Precedence:
      1. BACKEND_ENDPOINT / ARMORIQ_BACKEND_URL env var → POST {backend}/iap/sdk/bootstrap
      2. proxy_url arg → GET {proxy}/health

    The bootstrap path is preferred when available — it's more strict
    (actually resolves org + agent from the key), while /health only
    returns 200/401.
    """
    resolved_key = resolve_env_reference(api_key)
    if not resolved_key:
        raise CLIError("API key is empty. Set ARMORIQ_API_KEY or update identity.api_key.")
    headers = {"X-API-Key": resolved_key}
    backend = _os.getenv("BACKEND_ENDPOINT") or _os.getenv("ARMORIQ_BACKEND_URL")
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        if backend:
            response = client.post(
                f"{backend.rstrip('/')}/iap/sdk/bootstrap",
                headers={**headers, "Content-Type": "application/json"},
                json={},
            )
        else:
            response = client.get(f"{proxy_url.rstrip('/')}/health", headers=headers)
        if response.status_code == 401:
            raise CLIError("API key authentication failed (401).")
        if response.status_code >= 400:
            raise CLIError(f"API key validation failed (HTTP {response.status_code}).")


def _validate_policy_tools(
    policy: PolicyConfig, discovered_tools: Dict[str, List[str]]
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    known_refs = set()
    for server_id, tools in discovered_tools.items():
        for tool in tools:
            known_refs.add(f"{server_id}.{tool}")
    for ref in policy.allow:
        if "*" in ref or ":" in ref:
            continue
        if ref not in known_refs:
            errors.append(f"allow ref not found: {ref}")
    for ref in policy.deny:
        if "*" in ref or ":" in ref:
            continue
        if ref not in known_refs:
            errors.append(f"deny ref not found: {ref}")
    return len(errors) == 0, errors


def _register_with_control_plane(config: ArmorIQConfig) -> Dict:
    api_key = config.identity.resolved_api_key()
    if not api_key:
        raise CLIError("identity.api_key resolved to empty value")
    payload = config.to_yaml_dict()
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=12.0, follow_redirects=True) as client:
        response = client.post(CONTROL_PLANE_REGISTER_ENDPOINT, json=payload, headers=headers)
    if response.status_code >= 400:
        raise CLIError(
            f"Control plane registration failed at {CONTROL_PLANE_REGISTER_ENDPOINT} "
            f"(HTTP {response.status_code})"
        )
    try:
        return response.json()
    except Exception:
        return {}


def cmd_init(args: argparse.Namespace) -> int:
    _print("ArmorIQ CLI v1.0.0")
    _print("")

    default_api_key = "$ARMORIQ_API_KEY"
    api_key_input = _prompt("API Key", default_api_key)
    agent_id = _prompt("Agent ID", "my-agent")
    user_id = _prompt("User ID", "default")
    environment = _prompt("Environment", "sandbox").strip().lower() or "sandbox"
    if environment not in {"sandbox", "production"}:
        raise CLIError("Environment must be 'sandbox' or 'production'.")

    proxy_url = _resolve_env_endpoint("proxy")
    try:
        validate_api_key(api_key_input, proxy_url)
        _print(f"{CHECK} Credentials verified")
    except CLIError as exc:
        _print(f"Credentials check warning: {exc}")

    mcp_servers: List[MCPServerConfig] = []
    discovered_by_server: Dict[str, List[str]] = {}
    while True:
        prompt_label = (
            "Add MCP server URL (empty to skip)"
            if not mcp_servers
            else "Add another MCP server URL (empty to finish)"
        )
        server_url = _prompt(prompt_label).strip()
        if not server_url:
            break

        probe_server = MCPServerConfig(
            id="probe", url=server_url, auth=MCPAuthConfig(type="none")
        )
        discovery = discover_mcp_tools(probe_server)
        auth = MCPAuthConfig(type="none")

        if not discovery.reachable and _looks_like_auth_error(discovery.error):
            _print(
                f"  This MCP server requires authentication ({discovery.error})."
            )
            auth = _prompt_mcp_auth()
            probe_server = MCPServerConfig(id="probe", url=server_url, auth=auth)
            discovery = discover_mcp_tools(probe_server)

        if discovery.reachable:
            _print(
                f"{CHECK} Connection verified. {len(discovery.tools)} tools discovered"
                + (":" if discovery.tools else ".")
            )
            if discovery.tools:
                _print(f"    {', '.join(discovery.tools)}")
        else:
            _print(f"  Connection warning: {discovery.error}")

        auto_id = _auto_server_id(server_url)
        server_id = _prompt("Server ID", auto_id)
        description = _prompt("Description", "")

        server = MCPServerConfig(
            id=server_id,
            url=server_url,
            description=description or None,
            auth=auth,
        )
        mcp_servers.append(server)
        if discovery.reachable:
            discovered_by_server[server.id] = discovery.tools
        _print("")

    allow_refs: List[str] = []
    for server_id, tools in discovered_by_server.items():
        allow_refs.extend(f"{server_id}.{tool}" for tool in tools)

    config = ArmorIQConfig(
        identity=IdentityConfig(api_key=api_key_input, user_id=user_id, agent_id=agent_id),
        environment=environment,
        proxy=ProxyConfig(url=proxy_url, timeout=30, max_retries=3),
        mcp_servers=mcp_servers,
        policy=PolicyConfig(allow=sorted(set(allow_refs)), deny=[]),
        intent=IntentConfig(ttl_seconds=300, require_csrg=True),
    )
    save_armoriq_config(config, args.output)
    _append_log("init", {"config_path": str(Path(args.output).resolve())})

    _print(f"Generated {args.output}")
    _print("Next: edit the policy block, then run `armoriq register`")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config = load_armoriq_config(args.config)
    _print(f"{CHECK} Config syntax valid")

    validate_api_key(config.identity.api_key, config.proxy.url)
    _print(f"{CHECK} API key authenticated")

    discovered: Dict[str, List[str]] = {}
    for server in config.mcp_servers:
        discovery = discover_mcp_tools(server)
        if not discovery.reachable:
            raise CLIError(
                f"{server.id} MCP not reachable: {discovery.error or 'unknown error'}"
            )
        discovered[server.id] = discovery.tools
        _print(
            f"{CHECK} {server.id} MCP reachable ({len(discovery.tools)} tools)"
        )

    valid_policy, policy_errors = _validate_policy_tools(config.policy, discovered)
    if not valid_policy:
        raise CLIError("Policy references invalid tools: " + "; ".join(policy_errors))
    _print(f"{CHECK} Policy references valid tool names")
    _print("Ready to register.")

    _append_log("validate", {"config_path": str(Path(args.config).resolve())})
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    config = load_armoriq_config(args.config)
    _print("Registering with ArmorIQ control plane...")

    if args.dry_run:
        response: Dict = {"proxy_endpoint": config.proxy.url}
    else:
        response = _register_with_control_plane(config)

    discovered: Dict[str, List[str]] = {}
    for server in config.mcp_servers:
        result = discover_mcp_tools(server)
        discovered[server.id] = result.tools if result.reachable else []

    _print(f"{CHECK} Agent {config.identity.agent_id} registered")
    for server in config.mcp_servers:
        tool_count = len(discovered.get(server.id, []))
        _print(f"{CHECK} MCP server {server.id} registered ({tool_count} tools)")
    _print(
        f"{CHECK} Policy applied ({len(config.policy.allow)} allowed, {len(config.policy.deny)} denied)"
    )
    proxy_endpoint = response.get("proxy_endpoint") or config.proxy.url
    _print(f"{CHECK} Proxy endpoint: {proxy_endpoint}")
    _print("")
    _print("Your agent is ready. Use the SDK as usual:")
    _print("")
    _print("  from armoriq_sdk import ArmorIQClient")
    _print('  client = ArmorIQClient.from_config("armoriq.yaml")')

    state = {
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(Path(args.config).resolve()),
        "agent_id": config.identity.agent_id,
        "user_id": config.identity.user_id,
        "environment": config.environment,
        "proxy_endpoint": proxy_endpoint,
        "mcp_servers": [server.id for server in config.mcp_servers],
    }
    _save_state(state)
    _append_log("register", state)
    return 0


def _backend_base() -> str:
    explicit = _os.getenv("BACKEND_ENDPOINT") or _os.getenv("ARMORIQ_BACKEND_URL")
    if explicit:
        return explicit.rstrip("/")
    return _resolve_env_endpoint("backend").rstrip("/")


def _require_credentials():
    from .credentials import load_credentials, get_credentials_path

    creds = load_credentials()
    if not creds:
        raise CLIError(
            f"Not logged in ({get_credentials_path()} missing). Run `armoriq login` first."
        )
    return creds


def cmd_orgs(args: argparse.Namespace) -> int:
    creds = _require_credentials()
    url = f"{_backend_base()}/iap/sdk/orgs"
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            response = client.get(url, headers={"X-API-Key": creds.apiKey})
    except Exception as exc:
        raise CLIError(f"Failed to reach {url}: {exc}")

    if response.status_code == 401:
        raise CLIError("API key rejected (401). Try `armoriq login` again.")
    if response.status_code >= 400:
        raise CLIError(f"Failed to list orgs (HTTP {response.status_code}).")

    payload = response.json()
    orgs = payload.get("data") or []
    if not orgs:
        _print("You don't belong to any organizations.")
        return 0

    name_w = max(len("NAME"), max(len(o.get("name", "")) for o in orgs))
    role_w = max(len("ROLE"), max(len(o.get("userRole", "")) for o in orgs))
    header = (
        f"  {'NAME'.ljust(name_w)}  {'ORG_ID'.ljust(36)}  "
        f"{'ROLE'.ljust(role_w)}  MEMBERS"
    )
    _print(header)
    _print("  " + "-" * (len(header) - 2))
    for org in orgs:
        marker = f"{CHECK} " if org.get("active") else "  "
        name = (org.get("name") or "").ljust(name_w)
        org_id = (org.get("orgId") or "").ljust(36)
        role = (org.get("userRole") or "").ljust(role_w)
        members = str(org.get("memberCount") or 0)
        _print(f"{marker}{name}  {org_id}  {role}  {members}")
    _print("")
    _print(f"Active org is marked with {CHECK}. Switch with `armoriq switch-org <name-or-id>`.")
    _append_log("orgs", {"count": len(orgs)})
    return 0


def cmd_switch_org(args: argparse.Namespace) -> int:
    from .credentials import Credentials, save_credentials

    creds = _require_credentials()
    target = (args.org or "").strip()
    if not target:
        raise CLIError("Target org (id or name) is required.")

    url = f"{_backend_base()}/iap/sdk/switch-org"
    body = {"org": target}
    if getattr(args, "key_name", None):
        body["keyName"] = args.key_name

    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            response = client.post(
                url,
                json=body,
                headers={"X-API-Key": creds.apiKey, "Content-Type": "application/json"},
            )
    except Exception as exc:
        raise CLIError(f"Failed to reach {url}: {exc}")

    if response.status_code == 401:
        raise CLIError("API key rejected (401). Try `armoriq login` again.")
    if response.status_code == 403:
        raise CLIError(f"You are not a member of '{target}'.")
    if response.status_code == 404:
        raise CLIError(f"No organization named '{target}' (or matching that id).")
    if response.status_code == 400:
        detail = ""
        try:
            detail = response.json().get("message") or ""
        except Exception:
            pass
        raise CLIError(detail or "Bad request.")
    if response.status_code >= 400:
        raise CLIError(f"Switch failed (HTTP {response.status_code}).")

    payload = response.json()
    new_api_key = payload.get("api_key")
    new_org_id = payload.get("org_id")
    new_org_name = payload.get("org_name") or target
    if not new_api_key or not new_org_id:
        raise CLIError("Switch response missing api_key or org_id.")

    save_credentials(
        Credentials(
            apiKey=new_api_key,
            email=creds.email,
            userId=creds.userId,
            orgId=new_org_id,
            savedAt=datetime.now(timezone.utc).isoformat(),
        )
    )

    # Agent registration (state.json) was org-scoped — invalidate it so the
    # next step is obvious.
    state_existed = STATE_FILE.exists()
    if state_existed:
        try:
            STATE_FILE.unlink()
        except OSError:
            pass

    _print(f"{CHECK} Switched to {new_org_name} (org_id={new_org_id})")
    _print(f"{CHECK} New API key saved.")
    if state_existed:
        _print("  Previous agent registration cleared. Re-run `armoriq register` in this org.")
    _append_log(
        "switch-org",
        {"org_id": new_org_id, "org_name": new_org_name, "cleared_state": state_existed},
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = _load_state()
    if not state:
        _print("No local registration state found. Run `armoriq register` first.")
        return 1

    _print(f"Agent: {state.get('agent_id', 'unknown')}")
    _print(f"User: {state.get('user_id', 'unknown')}")
    _print(f"Environment: {state.get('environment', 'unknown')}")
    _print(f"Registered at: {state.get('registered_at', 'unknown')}")
    _print(f"Proxy endpoint: {state.get('proxy_endpoint', 'unknown')}")
    mcp_servers = state.get("mcp_servers", [])
    _print(f"MCP servers: {', '.join(mcp_servers) if mcp_servers else '(none)'}")
    return 0


def _print_logs_from_offset(offset: int) -> int:
    if not LOG_FILE.exists():
        return 0
    with LOG_FILE.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                ts = event.get("timestamp", "")
                event_name = event.get("event", "")
                details = event.get("details", {})
                _print(f"[{ts}] {event_name}: {json.dumps(details, sort_keys=True)}")
            except Exception:
                _print(line)
        return handle.tell()


def cmd_logs(args: argparse.Namespace) -> int:
    if not LOG_FILE.exists():
        _print("No CLI logs found yet.")
        return 0

    follow = args.follow
    offset = 0
    offset = _print_logs_from_offset(offset)
    if not follow:
        return 0

    try:
        while True:
            time.sleep(1.0)
            offset = _print_logs_from_offset(offset)
    except KeyboardInterrupt:
        return 0


# ─── API key management commands ───────────────────────────────────
# Closes #24. The backend already exposes:
#   GET  /api-keys                   (JwtAuth — uses the cached login JWT)
#   POST /api-keys/:id/revoke
# We list/revoke against those, and `prune` revokes anything expired or
# unused for >90 days. Plus a soft warning when key count gets high.

KEY_COUNT_WARN_THRESHOLD = 8
PRUNE_LAST_USED_DAYS = 90
PRUNE_NEVER_USED_DAYS = 30


def _request_keys(creds, method: str, path: str, **kwargs) -> "httpx.Response":
    url = f"{_backend_base()}{path}"
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            response = client.request(
                method,
                url,
                headers={"X-API-Key": creds.apiKey, **kwargs.pop("headers", {})},
                **kwargs,
            )
    except Exception as exc:
        raise CLIError(f"Failed to reach {url}: {exc}")
    if response.status_code == 401:
        raise CLIError("API key rejected (401). Try `armoriq login` again.")
    if response.status_code >= 400:
        try:
            detail = response.json().get("message") or ""
        except Exception:
            detail = ""
        raise CLIError(f"{path} failed (HTTP {response.status_code}): {detail}".rstrip(": "))
    return response


def _list_keys_payload(creds) -> List[Dict]:
    response = _request_keys(creds, "GET", "/api-keys")
    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    return []


def cmd_keys_list(args: argparse.Namespace) -> int:
    creds = _require_credentials()
    keys = _list_keys_payload(creds)
    if not keys:
        _print("No API keys found for this account.")
        return 0
    name_w = max(len("NAME"), max(len(k.get("name") or "") for k in keys))
    id_w = max(len("ID"), max(len(k.get("id") or "") for k in keys))
    _print(f"  {'NAME'.ljust(name_w)}  {'ID'.ljust(id_w)}  STATUS    LAST USED")
    _print("  " + "-" * (name_w + id_w + 30))
    for k in keys:
        name = (k.get("name") or "").ljust(name_w)
        kid = (k.get("id") or "").ljust(id_w)
        status = (k.get("status") or "unknown").ljust(8)
        last = k.get("lastUsedAt") or "-"
        _print(f"  {name}  {kid}  {status}  {last}")
    _print("")
    if len(keys) > KEY_COUNT_WARN_THRESHOLD:
        _print(
            f"\033[33m!\033[0m You have {len(keys)} API keys. Consider "
            f"`armoriq keys prune` to revoke unused keys."
        )
    _append_log("keys-list", {"count": len(keys)})
    return 0


def cmd_keys_revoke(args: argparse.Namespace) -> int:
    creds = _require_credentials()
    key_id = (getattr(args, "key_id", "") or "").strip()
    if not key_id:
        raise CLIError("Usage: armoriq keys revoke <id>")
    _request_keys(creds, "POST", f"/api-keys/{key_id}/revoke", json={})
    _print(f"{CHECK} Revoked key {key_id}.")
    _append_log("keys-revoke", {"id": key_id})
    return 0


def cmd_keys_prune(args: argparse.Namespace) -> int:
    creds = _require_credentials()
    keys = _list_keys_payload(creds)
    now = datetime.now(timezone.utc)

    def _is_candidate(k: Dict) -> bool:
        status = (k.get("status") or "").lower()
        if status == "revoked":
            return False
        if k.get("apiKey") and k.get("apiKey") == creds.apiKey:
            return False  # never prune the key we're authed with
        expires_at = k.get("expiresAt")
        if expires_at:
            try:
                if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < now:
                    return True
            except Exception:
                pass
        last_used_at = k.get("lastUsedAt")
        if last_used_at:
            try:
                age_days = (now - datetime.fromisoformat(last_used_at.replace("Z", "+00:00"))).days
                if age_days > PRUNE_LAST_USED_DAYS:
                    return True
            except Exception:
                pass
            return False
        created_at = k.get("createdAt")
        if created_at:
            try:
                age_days = (now - datetime.fromisoformat(created_at.replace("Z", "+00:00"))).days
                if age_days > PRUNE_NEVER_USED_DAYS:
                    return True
            except Exception:
                pass
        return False

    candidates = [k for k in keys if _is_candidate(k)]
    if not candidates:
        _print("Nothing to prune — all keys are either active, recent, or already revoked.")
        return 0

    _print(f"Found {len(candidates)} prune candidate(s):")
    for k in candidates:
        _print(f"  {k.get('id')} {k.get('name') or ''} (last used {k.get('lastUsedAt') or 'never'})")

    if not args.yes:
        _print("")
        _print("Re-run with --yes to actually revoke these.")
        return 0

    revoked = 0
    for k in candidates:
        try:
            _request_keys(creds, "POST", f"/api-keys/{k['id']}/revoke", json={})
            _print(f"{CHECK} Revoked {k['id']}")
            revoked += 1
        except CLIError as exc:
            _print(f"\033[31m✘\033[0m Failed to revoke {k['id']}: {exc}")
    _append_log("keys-prune", {"revoked": revoked, "candidates": len(candidates)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="armoriq",
        description="ArmorIQ SDK CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Interactive setup, generates armoriq.yaml")
    init_parser.add_argument(
        "--output",
        default="armoriq.yaml",
        help="Output config path (default: armoriq.yaml)",
    )
    init_parser.set_defaults(func=cmd_init)

    validate_parser = subparsers.add_parser(
        "validate", help="Check config, verify credentials, test MCP connectivity"
    )
    validate_parser.add_argument(
        "--config",
        default="armoriq.yaml",
        help="Config file path (default: armoriq.yaml)",
    )
    validate_parser.set_defaults(func=cmd_validate)

    register_parser = subparsers.add_parser(
        "register", help="Push config to ArmorIQ control plane"
    )
    register_parser.add_argument(
        "--config",
        default="armoriq.yaml",
        help="Config file path (default: armoriq.yaml)",
    )
    register_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip network registration and write local registration state only",
    )
    register_parser.set_defaults(func=cmd_register)

    status_parser = subparsers.add_parser(
        "status", help="Show what's registered and active"
    )
    status_parser.set_defaults(func=cmd_status)

    logs_parser = subparsers.add_parser(
        "logs", help="Stream activity logs from terminal"
    )
    logs_parser.add_argument(
        "--follow",
        action=argparse.BooleanOptionalAction,
        default=sys.stdout.isatty(),
        help="Continue streaming new log lines",
    )
    logs_parser.set_defaults(func=cmd_logs)

    from .cli_auth import cmd_login, cmd_logout, cmd_whoami

    login_parser = subparsers.add_parser(
        "login", help="Log in to ArmorIQ via browser (OAuth device-code flow)"
    )
    login_parser.add_argument("--backend", help="Override backend URL")
    login_parser.add_argument(
        "--org",
        help="Pre-select an organization (by id or exact name). Optional; the browser flow still lets you change it.",
    )
    login_parser.set_defaults(func=cmd_login)

    logout_parser = subparsers.add_parser("logout", help="Remove saved credentials")
    logout_parser.set_defaults(func=cmd_logout)

    whoami_parser = subparsers.add_parser(
        "whoami", help="Show current authentication status"
    )
    whoami_parser.set_defaults(func=cmd_whoami)

    orgs_parser = subparsers.add_parser(
        "orgs", help="List organizations your account belongs to"
    )
    orgs_parser.set_defaults(func=cmd_orgs)

    switch_parser = subparsers.add_parser(
        "switch-org",
        help="Switch to a different organization (mints a new API key scoped to it)",
    )
    switch_parser.add_argument(
        "org",
        help="Target organization — pass the org_id (UUID) or exact organization name.",
    )
    switch_parser.add_argument(
        "--key-name",
        dest="key_name",
        help="Optional name for the new API key (default: cli-YYYY-MM-DD).",
    )
    switch_parser.set_defaults(func=cmd_switch_org)

    keys_parser = subparsers.add_parser(
        "keys",
        help="Manage API keys (list, revoke, prune unused).",
    )
    keys_sub = keys_parser.add_subparsers(dest="keys_command", required=True)

    keys_list_parser = keys_sub.add_parser("list", help="List API keys for this account.")
    keys_list_parser.set_defaults(func=cmd_keys_list)

    keys_revoke_parser = keys_sub.add_parser(
        "revoke",
        help="Revoke a single API key by id.",
    )
    keys_revoke_parser.add_argument("key_id", help="The API key id (not the secret value).")
    keys_revoke_parser.set_defaults(func=cmd_keys_revoke)

    keys_prune_parser = keys_sub.add_parser(
        "prune",
        help="Revoke API keys that are expired or haven't been used in >90 days.",
    )
    keys_prune_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt and revoke immediately.",
    )
    keys_prune_parser.set_defaults(func=cmd_keys_prune)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ArmorIQConfigError as exc:
        _print(f"Config error: {exc}")
        return 1
    except CLIError as exc:
        _print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
