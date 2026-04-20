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


def discover_mcp_tools(server: MCPServerConfig, timeout: float = 8.0) -> MCPDiscoveryResult:
    try:
        headers = _resolve_auth_headers(server.auth)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            rpc_payload = {"jsonrpc": "2.0", "id": "armoriq-cli", "method": "tools/list", "params": {}}
            candidates = [server.url.rstrip("/"), f"{server.url.rstrip('/')}/mcp"]
            for candidate in candidates:
                try:
                    response = client.post(candidate, json=rpc_payload, headers=headers)
                    if response.status_code >= 400:
                        continue
                    tools = _extract_tool_names(response.json())
                    return MCPDiscoveryResult(reachable=True, tools=tools)
                except Exception:
                    continue

            response = client.get(server.url, headers=headers)
            if response.status_code >= 400:
                return MCPDiscoveryResult(
                    reachable=False,
                    tools=[],
                    error=f"HTTP {response.status_code}",
                )
            tools = []
            try:
                tools = _extract_tool_names(response.json())
            except Exception:
                tools = []
            return MCPDiscoveryResult(reachable=True, tools=tools)
    except Exception as exc:
        return MCPDiscoveryResult(reachable=False, tools=[], error=str(exc))


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

    proxy_url = "https://customer-proxy.armoriq.ai"
    try:
        validate_api_key(api_key_input, proxy_url)
        _print(f"{CHECK} Credentials verified")
    except CLIError as exc:
        _print(f"Credentials check warning: {exc}")

    mcp_servers: List[MCPServerConfig] = []
    discovered_by_server: Dict[str, List[str]] = {}
    while _prompt_yes_no("Add an MCP server? (y/n)", default=False):
        server_url = _prompt("MCP Server URL")
        auto_id = _auto_server_id(server_url)
        server_id = _prompt("Server ID", auto_id)
        auth_type = _prompt("Auth type [none/bearer/api_key]", "none").strip().lower()
        if auth_type not in {"none", "bearer", "api_key"}:
            raise CLIError("Auth type must be one of: none, bearer, api_key.")
        description = _prompt("Description", "")
        if auth_type == "bearer":
            token = _prompt("Bearer token (value or $ENV_VAR)")
            auth = MCPAuthConfig(type="bearer", token=token)
        elif auth_type == "api_key":
            key_value = _prompt("API key (value or $ENV_VAR)")
            auth = MCPAuthConfig(type="api_key", api_key=key_value)
        else:
            auth = MCPAuthConfig(type="none")

        server = MCPServerConfig(
            id=server_id,
            url=server_url,
            description=description or None,
            auth=auth,
        )
        mcp_servers.append(server)
        discovery = discover_mcp_tools(server)
        if discovery.reachable:
            discovered_by_server[server.id] = discovery.tools
            _print(
                f"{CHECK} Connection verified. {len(discovery.tools)} tools discovered:"
            )
            if discovery.tools:
                _print(f"    {', '.join(discovery.tools)}")
            else:
                _print("    (no tools returned by server)")
        else:
            _print(f"Connection warning for {server.id}: {discovery.error}")
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
    login_parser.set_defaults(func=cmd_login)

    logout_parser = subparsers.add_parser("logout", help="Remove saved credentials")
    logout_parser.set_defaults(func=cmd_logout)

    whoami_parser = subparsers.add_parser(
        "whoami", help="Show current authentication status"
    )
    whoami_parser.set_defaults(func=cmd_whoami)

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
