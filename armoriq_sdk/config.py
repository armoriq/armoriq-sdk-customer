"""
ArmorIQ CLI/SDK configuration models and YAML helpers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DEFAULT_PROXY_URL = "https://customer-proxy.armoriq.ai"


class ArmorIQConfigError(ValueError):
    """Raised when armoriq.yaml is invalid."""


def resolve_env_reference(value: str) -> str:
    """
    Resolve values like '$ENV_VAR' or '${ENV_VAR}' from environment.
    Returns the original value when it is not an env reference.
    """
    if not isinstance(value, str):
        return value
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.getenv(env_name, "")
    if value.startswith("$") and len(value) > 1 and " " not in value:
        env_name = value[1:]
        return os.getenv(env_name, "")
    return value


class IdentityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str
    user_id: str
    agent_id: str

    def resolved_api_key(self) -> str:
        return resolve_env_reference(self.api_key)


class ProxyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = DEFAULT_PROXY_URL
    timeout: int = 30
    max_retries: int = 3


class MCPAuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["none", "bearer", "api_key"] = "none"
    token: Optional[str] = None
    api_key: Optional[str] = None

    @model_validator(mode="after")
    def validate_auth_fields(self) -> "MCPAuthConfig":
        if self.type == "bearer" and not self.token:
            raise ValueError("bearer auth requires 'token'")
        if self.type == "api_key" and not self.api_key:
            raise ValueError("api_key auth requires 'api_key'")
        return self

    def to_yaml_value(self):
        if self.type == "none":
            return "none"
        if self.type == "bearer":
            return {"type": "bearer", "token": self.token}
        return {"type": "api_key", "api_key": self.api_key}


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    description: Optional[str] = None
    auth: MCPAuthConfig = Field(default_factory=MCPAuthConfig)

    @field_validator("auth", mode="before")
    @classmethod
    def normalize_auth(cls, value):
        if value is None:
            return {"type": "none"}
        if isinstance(value, str):
            return {"type": value}
        return value


class PolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow: List[str] = Field(default_factory=list)
    deny: List[str] = Field(default_factory=list)


class IntentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ttl_seconds: int = 300
    require_csrg: bool = True


class ArmorIQConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["v1"] = "v1"
    identity: IdentityConfig
    environment: Literal["sandbox", "production"] = "sandbox"
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    mcp_servers: List[MCPServerConfig] = Field(default_factory=list)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    intent: IntentConfig = Field(default_factory=IntentConfig)

    @model_validator(mode="after")
    def validate_unique_server_ids(self) -> "ArmorIQConfig":
        ids = [server.id for server in self.mcp_servers]
        if len(ids) != len(set(ids)):
            raise ValueError("mcp_servers contain duplicate 'id' values")
        return self

    def to_yaml_dict(self) -> Dict:
        data: Dict = {
            "version": self.version,
            "identity": {
                "api_key": self.identity.api_key,
                "user_id": self.identity.user_id,
                "agent_id": self.identity.agent_id,
            },
            "environment": self.environment,
            "proxy": {
                "url": self.proxy.url,
                "timeout": self.proxy.timeout,
                "max_retries": self.proxy.max_retries,
            },
            "mcp_servers": [],
            "policy": {
                "allow": self.policy.allow,
                "deny": self.policy.deny,
            },
            "intent": {
                "ttl_seconds": self.intent.ttl_seconds,
                "require_csrg": self.intent.require_csrg,
            },
        }
        for server in self.mcp_servers:
            server_data: Dict = {
                "id": server.id,
                "url": server.url,
                "auth": server.auth.to_yaml_value(),
            }
            if server.description:
                server_data["description"] = server.description
            data["mcp_servers"].append(server_data)
        return data


def load_armoriq_config(path: Union[str, Path] = "armoriq.yaml") -> ArmorIQConfig:
    file_path = Path(path)
    if not file_path.exists():
        raise ArmorIQConfigError(f"Config file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    try:
        return ArmorIQConfig.model_validate(raw)
    except Exception as exc:  # pragma: no cover - exercised in tests via message
        raise ArmorIQConfigError(str(exc)) from exc


def save_armoriq_config(config: ArmorIQConfig, path: Union[str, Path] = "armoriq.yaml") -> None:
    file_path = Path(path)
    with file_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config.to_yaml_dict(), handle, sort_keys=False)
