"""
Unit tests for plan-builder helpers.

Mirrors TS parity — same tool-name convention (<MCP>__<action>), same
digest over the canonical tool-call list.
"""

import hashlib
import json

import pytest

from armoriq_sdk import (
    build_plan_from_tool_calls,
    default_tool_name_parser,
    hash_tool_calls,
    ToolCall,
)


class TestDefaultToolNameParser:
    def test_parses_namespaced(self):
        parser = default_tool_name_parser()
        mcp, action = parser("Stripe__create_payment")
        assert mcp == "Stripe"
        assert action == "create_payment"

    def test_falls_back_to_default_mcp(self):
        parser = default_tool_name_parser("DefaultMCP")
        mcp, action = parser("plain_tool")
        assert mcp == "DefaultMCP"
        assert action == "plain_tool"

    def test_raises_without_default(self):
        parser = default_tool_name_parser()
        with pytest.raises(ValueError, match="not namespaced"):
            parser("plain_tool")

    def test_rejects_malformed(self):
        parser = default_tool_name_parser()
        with pytest.raises(ValueError, match="malformed"):
            parser("__no_prefix")
        with pytest.raises(ValueError, match="malformed"):
            parser("NoAction__")


class TestBuildPlanFromToolCalls:
    def test_basic(self):
        calls = [
            ToolCall(name="Stripe__charge", args={"amount": 100}),
            ToolCall(name="Stripe__refund", args={"id": "ch_1"}),
        ]
        plan = build_plan_from_tool_calls(calls, goal="run ops")
        assert plan["goal"] == "run ops"
        assert len(plan["steps"]) == 2
        assert plan["steps"][0]["mcp"] == "Stripe"
        assert plan["steps"][0]["action"] == "charge"
        assert plan["steps"][0]["params"] == {"amount": 100}
        assert plan["steps"][0]["tool"] == "charge"
        assert "Call charge on Stripe" in plan["steps"][0]["description"]

    def test_accepts_dict_tool_calls(self):
        plan = build_plan_from_tool_calls(
            [{"name": "Stripe__charge", "args": {"amount": 5}}]
        )
        assert plan["steps"][0]["mcp"] == "Stripe"

    def test_default_goal(self):
        plan = build_plan_from_tool_calls([ToolCall(name="M__a")])
        assert plan["goal"] == "agent task"

    def test_custom_parser(self):
        def parser(name):
            return name.split(":")

        plan = build_plan_from_tool_calls(
            [ToolCall(name="Svc:method")], tool_name_parser=parser
        )
        assert plan["steps"][0]["mcp"] == "Svc"
        assert plan["steps"][0]["action"] == "method"

    def test_default_mcp_passthrough(self):
        plan = build_plan_from_tool_calls(
            [ToolCall(name="plain_tool")], default_mcp_name="Local"
        )
        assert plan["steps"][0]["mcp"] == "Local"
        assert plan["steps"][0]["action"] == "plain_tool"


class TestHashToolCalls:
    def test_stable_for_same_input(self):
        calls = [ToolCall(name="a__b", args={"x": 1})]
        assert hash_tool_calls(calls) == hash_tool_calls(calls)

    def test_differs_for_different_input(self):
        a = [ToolCall(name="a__b", args={"x": 1})]
        b = [ToolCall(name="a__b", args={"x": 2})]
        assert hash_tool_calls(a) != hash_tool_calls(b)

    def test_matches_ts_canonicalization(self):
        """Hash must use JSON.stringify semantics (no key sort, compact separators)."""
        calls = [ToolCall(name="Stripe__charge", args={"amount": 100})]
        expected = hashlib.sha256(
            json.dumps(
                [{"name": "Stripe__charge", "args": {"amount": 100}}],
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        assert hash_tool_calls(calls) == expected

    def test_accepts_dict_form(self):
        calls = [{"name": "a__b", "args": {"x": 1}}]
        obj_form = [ToolCall(name="a__b", args={"x": 1})]
        assert hash_tool_calls(calls) == hash_tool_calls(obj_form)
