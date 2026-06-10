"""
Tests for agent identity attribution in the Google ADK integration.

Verifies that ArmorIQADK passes real agent_id instead of the
__sdk_multiuser__ fallback, matching the TS SDK fix (armoriq-sdk-customer-ts#49).
"""

from unittest.mock import MagicMock, patch

import pytest

from armoriq_sdk.integrations.google_adk import ArmorIQADK


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_adk(**overrides):
    defaults = dict(
        api_key="ak_test_fake123",
        use_production=False,
    )
    defaults.update(overrides)
    return ArmorIQADK(**defaults)


def _mock_bootstrap_response(agents=None, **extra):
    resp = {
        "org": {"name": "TestOrg"},
        "mcps": [],
        "toolMap": {},
    }
    if agents is not None:
        resp["agents"] = agents
    resp.update(extra)
    return resp


# ---------------------------------------------------------------------------
# 1. Explicit agent_name propagates to client.agent_id
# ---------------------------------------------------------------------------


class TestExplicitAgentName:
    def test_agent_id_set_from_agent_name(self):
        """When agent_name is passed, client.agent_id should be that name,
        not the __sdk_multiuser__ fallback."""
        adk = _make_adk(agent_name="member-care-agent")
        assert adk.client.agent_id == "member-care-agent"

    def test_agent_id_is_none_when_no_agent_name(self):
        """When agent_name is not passed, client.agent_id falls back to
        __sdk_multiuser__ (pre-existing behavior)."""
        adk = _make_adk()
        assert adk.client.agent_id == "__sdk_multiuser__"

    def test_explicit_agent_name_stored(self):
        adk = _make_adk(agent_name="claims-accuracy-agent")
        assert adk._explicit_agent_name == "claims-accuracy-agent"

    def test_no_agent_name_stored_as_none(self):
        adk = _make_adk()
        assert adk._explicit_agent_name is None


# ---------------------------------------------------------------------------
# 2. Bootstrap auto-resolves agent_id when exactly one agent is registered
# ---------------------------------------------------------------------------


class TestBootstrapAutoResolve:
    def test_auto_resolve_single_agent(self):
        """When bootstrap returns exactly one agent and no agent_name was
        provided, client.agent_id should be auto-resolved."""
        adk = _make_adk()
        mock_resp = _mock_bootstrap_response(
            agents=[{"agentId": "ag_123", "name": "member-care-agent"}]
        )
        adk.client.bootstrap = MagicMock(return_value=mock_resp)

        adk.bootstrap()

        assert adk.client.agent_id == "member-care-agent"

    def test_no_auto_resolve_when_explicit_name(self):
        """When agent_name was explicitly provided, bootstrap should NOT
        overwrite it even if there's one registered agent."""
        adk = _make_adk(agent_name="my-custom-agent")
        mock_resp = _mock_bootstrap_response(
            agents=[{"agentId": "ag_123", "name": "member-care-agent"}]
        )
        adk.client.bootstrap = MagicMock(return_value=mock_resp)

        adk.bootstrap()

        assert adk.client.agent_id == "my-custom-agent"

    def test_no_auto_resolve_multiple_agents(self):
        """When bootstrap returns multiple agents, should NOT guess which
        one to use — caller must provide agent_name explicitly."""
        adk = _make_adk()
        mock_resp = _mock_bootstrap_response(
            agents=[
                {"agentId": "ag_1", "name": "member-care-agent"},
                {"agentId": "ag_2", "name": "claims-accuracy-agent"},
            ]
        )
        adk.client.bootstrap = MagicMock(return_value=mock_resp)

        adk.bootstrap()

        assert adk.client.agent_id == "__sdk_multiuser__"

    def test_no_auto_resolve_zero_agents(self):
        """When bootstrap returns no agents, should not crash or resolve."""
        adk = _make_adk()
        mock_resp = _mock_bootstrap_response(agents=[])
        adk.client.bootstrap = MagicMock(return_value=mock_resp)

        adk.bootstrap()

        assert adk.client.agent_id == "__sdk_multiuser__"

    def test_no_auto_resolve_agent_without_name(self):
        """When the single agent entry has no 'name' field, should not crash."""
        adk = _make_adk()
        mock_resp = _mock_bootstrap_response(
            agents=[{"agentId": "ag_123"}]
        )
        adk.client.bootstrap = MagicMock(return_value=mock_resp)

        adk.bootstrap()

        assert adk.client.agent_id == "__sdk_multiuser__"

    def test_bootstrap_caches_result(self):
        """bootstrap() should only call client.bootstrap() once."""
        adk = _make_adk()
        mock_resp = _mock_bootstrap_response(
            agents=[{"agentId": "ag_123", "name": "member-care-agent"}]
        )
        adk.client.bootstrap = MagicMock(return_value=mock_resp)

        adk.bootstrap()
        adk.bootstrap()

        assert adk.client.bootstrap.call_count == 1


# ---------------------------------------------------------------------------
# 3. _set_agent_id on ArmorIQClient
# ---------------------------------------------------------------------------


class TestSetAgentId:
    def test_updates_agent_id(self):
        from armoriq_sdk.client import ArmorIQClient

        client = ArmorIQClient(
            api_key="ak_test_fake123",
            use_production=False,
            _skip_api_key_validation=True,
        )
        assert client.agent_id == "__sdk_multiuser__"

        client._set_agent_id("ihealth-agent")

        assert client.agent_id == "ihealth-agent"
