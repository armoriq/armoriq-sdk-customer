from armoriq_sdk import cli
from armoriq_sdk.cli import MCPDiscoveryResult


def _write_config(path):
    path.write_text(
        "\n".join(
            [
                "version: v1",
                "identity:",
                "  api_key: ak_test_123",
                "  user_id: jani-advisor",
                "  agent_id: crewai-ferry-agent",
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
                "  allow:",
                "    - ferryhopper.search_routes",
                "  deny: []",
                "intent:",
                "  ttl_seconds: 300",
                "  require_csrg: true",
            ]
        ),
        encoding="utf-8",
    )


def test_validate_command_success(tmp_path, monkeypatch):
    config_path = tmp_path / "armoriq.yaml"
    _write_config(config_path)

    monkeypatch.setattr(cli, "validate_api_key", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cli,
        "discover_mcp_tools",
        lambda *args, **kwargs: MCPDiscoveryResult(
            reachable=True,
            tools=["search_routes", "get_schedule"],
        ),
    )
    monkeypatch.setattr(cli, "STATE_DIR", tmp_path / ".state")
    monkeypatch.setattr(cli, "STATE_FILE", tmp_path / ".state" / "state.json")
    monkeypatch.setattr(cli, "LOG_FILE", tmp_path / ".state" / "cli.log")

    code = cli.main(["validate", "--config", str(config_path)])
    assert code == 0


def test_register_dry_run_writes_state(tmp_path, monkeypatch):
    config_path = tmp_path / "armoriq.yaml"
    _write_config(config_path)

    monkeypatch.setattr(
        cli,
        "discover_mcp_tools",
        lambda *args, **kwargs: MCPDiscoveryResult(
            reachable=True,
            tools=["search_routes"],
        ),
    )
    monkeypatch.setattr(cli, "STATE_DIR", tmp_path / ".state")
    monkeypatch.setattr(cli, "STATE_FILE", tmp_path / ".state" / "state.json")
    monkeypatch.setattr(cli, "LOG_FILE", tmp_path / ".state" / "cli.log")

    code = cli.main(["register", "--dry-run", "--config", str(config_path)])
    assert code == 0
    assert cli.STATE_FILE.exists()
