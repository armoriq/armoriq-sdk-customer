import os

from armoriq_sdk.config import load_armoriq_config, save_armoriq_config


def test_load_and_resolve_env_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ARMORIQ_API_KEY", "ak_test_123")
    config_path = tmp_path / "armoriq.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: v1",
                "identity:",
                "  api_key: $ARMORIQ_API_KEY",
                "  user_id: jani",
                "  agent_id: ferry-agent",
                "environment: sandbox",
                "proxy:",
                "  url: https://customer-proxy.armoriq.ai",
                "  timeout: 30",
                "  max_retries: 3",
                "mcp_servers:",
                "  - id: ferryhopper",
                "    url: https://mcp.ferryhopper.com/mcp",
                "    auth: none",
                "policy:",
                "  allow: [ferryhopper.search_routes]",
                "  deny: []",
                "intent:",
                "  ttl_seconds: 300",
                "  require_csrg: true",
            ]
        ),
        encoding="utf-8",
    )

    config = load_armoriq_config(config_path)
    assert config.identity.api_key == "$ARMORIQ_API_KEY"
    assert config.identity.resolved_api_key() == "ak_test_123"
    assert config.mcp_servers[0].auth.type == "none"


def test_save_preserves_scalar_none_auth(tmp_path):
    config_path = tmp_path / "armoriq.yaml"
    source = tmp_path / "source.yaml"
    source.write_text(
        "\n".join(
            [
                "version: v1",
                "identity:",
                "  api_key: ak_test_123",
                "  user_id: user",
                "  agent_id: agent",
                "environment: sandbox",
                "proxy:",
                "  url: https://customer-proxy.armoriq.ai",
                "  timeout: 30",
                "  max_retries: 3",
                "mcp_servers:",
                "  - id: ferryhopper",
                "    url: https://mcp.ferryhopper.com/mcp",
                "    auth: none",
                "policy:",
                "  allow: []",
                "  deny: []",
                "intent:",
                "  ttl_seconds: 300",
                "  require_csrg: true",
            ]
        ),
        encoding="utf-8",
    )
    config = load_armoriq_config(source)
    save_armoriq_config(config, config_path)

    rendered = config_path.read_text(encoding="utf-8")
    assert "auth: none" in rendered
    assert os.path.exists(config_path)
