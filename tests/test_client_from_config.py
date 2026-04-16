from unittest.mock import patch

from armoriq_sdk import ArmorIQClient


def test_from_config_builds_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARMORIQ_API_KEY", "ak_test_abc123")
    config_path = tmp_path / "armoriq.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: v1",
                "identity:",
                "  api_key: $ARMORIQ_API_KEY",
                "  user_id: jani-advisor",
                "  agent_id: crewai-ferry-agent",
                "environment: sandbox",
                "proxy:",
                "  url: https://customer-proxy.armoriq.ai",
                "  timeout: 45",
                "  max_retries: 5",
                "mcp_servers: []",
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

    with patch("armoriq_sdk.client.httpx.Client") as mock_http:
        mock_http.return_value.get.return_value.status_code = 200
        client = ArmorIQClient.from_config(str(config_path))

    assert client.user_id == "jani-advisor"
    assert client.agent_id == "crewai-ferry-agent"
    assert client.api_key == "ak_test_abc123"
    assert client.proxy_endpoint == "https://customer-proxy.armoriq.ai"
    assert client.timeout == 45.0
    assert client.max_retries == 5
