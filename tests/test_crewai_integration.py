"""
Tests for ArmorIQ CrewAI integration.

No crewai install is needed — a fake crewai module is injected into
sys.modules before the integration is imported.
"""

import asyncio
import json
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject a fake crewai module before importing ArmorIQCrew
# ---------------------------------------------------------------------------

_fake_crewai = types.ModuleType("crewai")


class FakeCrew:
    """Minimal stand-in for crewai.Crew."""

    def __init__(self, *args, **kwargs):
        self.agents = kwargs.get("agents", [])
        self.tasks = kwargs.get("tasks", [])
        self._kickoff_result = "crew result"

    def kickoff(self, inputs=None):
        return self._kickoff_result

    async def kickoff_async(self, inputs=None):
        return self._kickoff_result


_fake_crewai.Crew = FakeCrew
sys.modules.setdefault("crewai", _fake_crewai)

# Now import the module under test (crewai is available in sys.modules)
from armoriq_sdk.integrations.crewai import (  # noqa: E402
    ArmorIQCrew,
    _build_plan,
    _collect_armoriq_tools,
    _wrap_tool,
)
from armoriq_sdk.client import ArmorIQClient  # noqa: E402
from armoriq_sdk.exceptions import (  # noqa: E402
    ArmorIQException,
    MCPInvocationException,
)
from armoriq_sdk.models import IntentToken, PlanCapture  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers / fixtures
# ---------------------------------------------------------------------------


class FrozenTool:
    """Simulates a Pydantic v2 frozen model: __setattr__ raises TypeError."""

    def __init__(self, name, mcp, action):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "mcp", mcp)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "_run", self._default_run)

    def _default_run(self, *args, **kwargs):
        return f"default:{self.action}"

    def __setattr__(self, key, value):
        raise TypeError("FrozenTool is immutable — use object.__setattr__")


def _make_armoriq_tool(name="tool1", mcp="my-mcp", action="do_thing"):
    return FrozenTool(name=name, mcp=mcp, action=action)


def _make_plain_tool(name="plain"):
    """A tool without .mcp / .action attributes."""
    t = MagicMock()
    t.name = name
    del t.mcp
    del t.action
    return t


def _make_agent(tools=None):
    agent = MagicMock()
    agent.tools = tools if tools is not None else []
    return agent


def _make_token(steps=None, validity=3600.0):
    """Build a valid IntentToken with matching raw_token plan."""
    now = datetime.now().timestamp()
    plan_steps = steps or [{"action": "do_thing", "mcp": "my-mcp"}]
    raw_token = {
        "plan": {"goal": "test goal", "steps": plan_steps},
        "token": {"signature": "sig123"},
        "plan_hash": "abc123",
        "merkle_root": "root123",
        "intent_reference": "ref-001",
        "composite_identity": "ci-001",
    }
    return IntentToken(
        token_id="ref-001",
        plan_hash="abc123",
        plan_id="plan-001",
        signature="sig123",
        issued_at=now,
        expires_at=now + validity,
        policy={},
        composite_identity="ci-001",
        client_info=None,
        policy_validation=None,
        step_proofs=[],
        total_steps=len(plan_steps),
        raw_token=raw_token,
    )


def _make_mock_client(token=None):
    """Return a Mock with spec=ArmorIQClient with sensible return values."""
    client = MagicMock(spec=ArmorIQClient)
    t = token or _make_token()
    plan_capture = PlanCapture(
        plan={"goal": "test goal", "steps": [{"action": "do_thing", "mcp": "my-mcp"}]},
        llm="gpt-4o",
        prompt="test goal",
    )
    client.capture_plan.return_value = plan_capture

    invoke_result = MagicMock()
    invoke_result.result = "invoke output"
    client.invoke.return_value = invoke_result
    client.get_intent_token.return_value = t
    return client


# ---------------------------------------------------------------------------
# TestCollectArmoriqTools
# ---------------------------------------------------------------------------


class TestCollectArmoriqTools(unittest.TestCase):
    def test_returns_armoriq_tools(self):
        tool = _make_armoriq_tool()
        agent = _make_agent([tool])
        result = _collect_armoriq_tools([agent])
        self.assertEqual(result, [tool])

    def test_skips_tool_without_mcp(self):
        tool = MagicMock()
        del tool.mcp
        tool.action = "x"
        agent = _make_agent([tool])
        result = _collect_armoriq_tools([agent])
        self.assertEqual(result, [])

    def test_skips_tool_without_action(self):
        tool = MagicMock()
        tool.mcp = "mcp"
        del tool.action
        agent = _make_agent([tool])
        result = _collect_armoriq_tools([agent])
        self.assertEqual(result, [])

    def test_deduplicates_same_object_across_agents(self):
        tool = _make_armoriq_tool()
        agent1 = _make_agent([tool])
        agent2 = _make_agent([tool])
        result = _collect_armoriq_tools([agent1, agent2])
        self.assertEqual(result, [tool])

    def test_multiple_distinct_tools(self):
        t1 = _make_armoriq_tool("t1", "mcp1", "a1")
        t2 = _make_armoriq_tool("t2", "mcp2", "a2")
        agent = _make_agent([t1, t2])
        result = _collect_armoriq_tools([agent])
        self.assertEqual(set(id(t) for t in result), {id(t1), id(t2)})

    def test_agent_with_no_tools_attr(self):
        agent = MagicMock(spec=[])  # no 'tools' attribute
        result = _collect_armoriq_tools([agent])
        self.assertEqual(result, [])

    def test_agent_with_none_tools(self):
        agent = _make_agent(None)
        result = _collect_armoriq_tools([agent])
        self.assertEqual(result, [])

    def test_mixed_armoriq_and_plain_tools(self):
        armoriq = _make_armoriq_tool()
        plain = _make_plain_tool()
        agent = _make_agent([armoriq, plain])
        result = _collect_armoriq_tools([agent])
        self.assertEqual(result, [armoriq])


# ---------------------------------------------------------------------------
# TestBuildPlan
# ---------------------------------------------------------------------------


class TestBuildPlan(unittest.TestCase):
    def _task(self, description=None, expected_output=None):
        t = MagicMock()
        t.description = description
        t.expected_output = expected_output
        return t

    def test_correct_steps_built(self):
        tool = _make_armoriq_tool(mcp="mcp1", action="act1")
        tasks = [self._task("do something")]
        plan = _build_plan([tool], tasks)
        self.assertEqual(plan["steps"], [{"action": "act1", "mcp": "mcp1"}])

    def test_deduplicates_same_mcp_action_combo(self):
        t1 = _make_armoriq_tool("t1", "mcp1", "act1")
        t2 = _make_armoriq_tool("t2", "mcp1", "act1")  # same (mcp, action)
        plan = _build_plan([t1, t2], [])
        self.assertEqual(len(plan["steps"]), 1)

    def test_goal_from_task_description(self):
        tasks = [self._task("buy milk"), self._task("pick up kids")]
        plan = _build_plan([], tasks)
        self.assertIn("buy milk", plan["goal"])
        self.assertIn("pick up kids", plan["goal"])

    def test_fallback_to_expected_output(self):
        task = self._task(description=None, expected_output="result ready")
        plan = _build_plan([], [task])
        self.assertIn("result ready", plan["goal"])

    def test_generic_fallback_when_no_tasks(self):
        plan = _build_plan([], [])
        self.assertEqual(plan["goal"], "Execute crew tasks")

    def test_plan_has_required_keys(self):
        plan = _build_plan([], [])
        self.assertIn("goal", plan)
        self.assertIn("steps", plan)


# ---------------------------------------------------------------------------
# TestWrapTool
# ---------------------------------------------------------------------------


class TestWrapTool(unittest.TestCase):
    def setUp(self):
        self.tool = _make_armoriq_tool(mcp="mcp1", action="act1")
        self.client = _make_mock_client()
        self.token = _make_token()

    def test_returns_original_callable(self):
        original = self.tool._run
        returned = _wrap_tool(self.tool, self.client, self.token)
        self.assertIs(returned, original)

    def test_patched_run_calls_invoke_with_correct_args(self):
        _wrap_tool(self.tool, self.client, self.token)
        self.tool._run(param1="v1")
        self.client.invoke.assert_called_once_with(
            mcp="mcp1",
            action="act1",
            intent_token=self.token,
            params={"param1": "v1"},
        )

    def test_string_result_returned_as_is(self):
        self.client.invoke.return_value.result = "hello"
        _wrap_tool(self.tool, self.client, self.token)
        result = self.tool._run()
        self.assertEqual(result, "hello")

    def test_dict_result_json_encoded(self):
        self.client.invoke.return_value.result = {"key": "val"}
        _wrap_tool(self.tool, self.client, self.token)
        result = self.tool._run()
        self.assertEqual(result, json.dumps({"key": "val"}))

    def test_armoriq_exception_reraised_unchanged(self):
        exc = MCPInvocationException("boom", mcp="mcp1", action="act1")
        self.client.invoke.side_effect = exc
        _wrap_tool(self.tool, self.client, self.token)
        with self.assertRaises(MCPInvocationException) as ctx:
            self.tool._run()
        self.assertIs(ctx.exception, exc)

    def test_object_setattr_bypass_works_on_frozen_tool(self):
        """Patching must succeed even though FrozenTool.__setattr__ raises."""
        original = self.tool._run
        _wrap_tool(self.tool, self.client, self.token)
        # After patch, _run should be different from original
        self.assertIsNot(self.tool._run, original)


# ---------------------------------------------------------------------------
# TestArmorIQCrewInit
# ---------------------------------------------------------------------------


class TestArmorIQCrewInit(unittest.TestCase):
    def _make_crew(self, **extra):
        client = _make_mock_client()
        defaults = dict(agents=[], tasks=[], armoriq_client=client, llm="gpt-4o")
        defaults.update(extra)
        return ArmorIQCrew(**defaults), client

    def test_stores_client_llm_validity(self):
        crew, client = self._make_crew(token_validity_seconds=1800.0)
        self.assertIs(crew._armoriq_client, client)
        self.assertEqual(crew._llm, "gpt-4o")
        self.assertEqual(crew._token_validity_seconds, 1800.0)

    def test_default_token_validity(self):
        crew, _ = self._make_crew()
        self.assertEqual(crew._token_validity_seconds, 3600.0)

    def test_raises_import_error_when_crewai_missing(self):
        # Temporarily remove crewai from sys.modules
        saved = sys.modules.pop("crewai")
        try:
            # Re-import the module so the class sees no crewai
            import importlib
            import armoriq_sdk.integrations.crewai as mod
            importlib.reload(mod)
            with self.assertRaises(ImportError) as ctx:
                mod.ArmorIQCrew(agents=[], tasks=[], armoriq_client=None, llm="x")
            self.assertIn("pip install armoriq-sdk[crewai]", str(ctx.exception))
        finally:
            sys.modules["crewai"] = saved
            # Reload to restore normal state
            import importlib
            import armoriq_sdk.integrations.crewai as mod
            importlib.reload(mod)


# ---------------------------------------------------------------------------
# TestArmorIQCrewKickoff
# ---------------------------------------------------------------------------


class TestArmorIQCrewKickoff(unittest.TestCase):
    def _make_crew_with_tool(self, tool=None, client=None):
        if tool is None:
            tool = _make_armoriq_tool()
        agent = _make_agent([tool])
        task = MagicMock()
        task.description = "do stuff"
        task.expected_output = "done"
        if client is None:
            client = _make_mock_client()
        crew = ArmorIQCrew(
            agents=[agent],
            tasks=[task],
            armoriq_client=client,
            llm="gpt-4o",
        )
        return crew, client, tool

    def test_capture_plan_called_with_correct_args(self):
        crew, client, _ = self._make_crew_with_tool()
        crew.kickoff()
        client.capture_plan.assert_called_once()
        call_kwargs = client.capture_plan.call_args
        self.assertEqual(call_kwargs.kwargs["llm"], "gpt-4o")
        plan_arg = call_kwargs.kwargs["plan"]
        self.assertIn("steps", plan_arg)

    def test_get_intent_token_called_with_validity(self):
        crew, client, _ = self._make_crew_with_tool()
        crew.kickoff()
        client.get_intent_token.assert_called_once()
        call_kwargs = client.get_intent_token.call_args
        self.assertEqual(call_kwargs.kwargs["validity_seconds"], 3600.0)

    def test_inputs_forwarded_to_inner_crew(self):
        crew, client, _ = self._make_crew_with_tool()
        with patch.object(crew._crew, "kickoff", return_value="result") as mock_kickoff:
            crew.kickoff(inputs={"x": 1})
            mock_kickoff.assert_called_once_with(inputs={"x": 1})

    def test_returns_crew_result(self):
        crew, client, _ = self._make_crew_with_tool()
        with patch.object(crew._crew, "kickoff", return_value="my result"):
            result = crew.kickoff()
        self.assertEqual(result, "my result")

    def test_no_token_when_no_armoriq_tools(self):
        plain = _make_plain_tool()
        agent = _make_agent([plain])
        client = _make_mock_client()
        crew = ArmorIQCrew(agents=[agent], tasks=[], armoriq_client=client, llm="gpt-4o")
        crew.kickoff()
        client.capture_plan.assert_not_called()
        client.get_intent_token.assert_not_called()

    def test_tools_restored_after_success(self):
        tool = _make_armoriq_tool()
        original_run = tool._run
        crew, client, _ = self._make_crew_with_tool(tool=tool, client=_make_mock_client())
        crew.kickoff()
        self.assertIs(tool._run, original_run)

    def test_tools_restored_after_exception(self):
        tool = _make_armoriq_tool()
        original_run = tool._run
        crew, client, _ = self._make_crew_with_tool(tool=tool)
        with patch.object(crew._crew, "kickoff", side_effect=RuntimeError("oops")):
            with self.assertRaises(RuntimeError):
                crew.kickoff()
        self.assertIs(tool._run, original_run)

    def test_non_armoriq_tools_not_wrapped(self):
        plain = _make_plain_tool()
        plain_run = plain._run
        armoriq = _make_armoriq_tool()
        agent = _make_agent([plain, armoriq])
        client = _make_mock_client()
        crew = ArmorIQCrew(agents=[agent], tasks=[], armoriq_client=client, llm="gpt-4o")
        crew.kickoff()
        # plain tool's _run must be untouched
        self.assertIs(plain._run, plain_run)


# ---------------------------------------------------------------------------
# TestArmorIQCrewKickoffAsync
# ---------------------------------------------------------------------------


class TestArmorIQCrewKickoffAsync(unittest.TestCase):
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_kickoff_async_awaits_inner_crew(self):
        tool = _make_armoriq_tool()
        agent = _make_agent([tool])
        client = _make_mock_client()
        crew = ArmorIQCrew(agents=[agent], tasks=[], armoriq_client=client, llm="gpt-4o")

        async def fake_kickoff_async(inputs=None):
            return "async result"

        with patch.object(crew._crew, "kickoff_async", side_effect=fake_kickoff_async):
            result = self._run(crew.kickoff_async(inputs={"y": 2}))
        self.assertEqual(result, "async result")

    def test_tools_restored_after_async_exception(self):
        tool = _make_armoriq_tool()
        original_run = tool._run
        agent = _make_agent([tool])
        client = _make_mock_client()
        crew = ArmorIQCrew(agents=[agent], tasks=[], armoriq_client=client, llm="gpt-4o")

        async def fail(inputs=None):
            raise RuntimeError("async boom")

        with patch.object(crew._crew, "kickoff_async", side_effect=fail):
            with self.assertRaises(RuntimeError):
                self._run(crew.kickoff_async())
        self.assertIs(tool._run, original_run)


# ---------------------------------------------------------------------------
# TestErrorPropagation
# ---------------------------------------------------------------------------


class TestErrorPropagation(unittest.TestCase):
    def _make_crew(self):
        tool = _make_armoriq_tool()
        agent = _make_agent([tool])
        client = _make_mock_client()
        crew = ArmorIQCrew(agents=[agent], tasks=[], armoriq_client=client, llm="gpt-4o")
        return crew, client

    def test_capture_plan_exception_propagates(self):
        crew, client = self._make_crew()
        client.capture_plan.side_effect = ValueError("bad plan")
        with self.assertRaises(ValueError, msg="bad plan"):
            crew.kickoff()

    def test_get_intent_token_exception_propagates(self):
        crew, client = self._make_crew()
        client.get_intent_token.side_effect = RuntimeError("token error")
        with self.assertRaises(RuntimeError):
            crew.kickoff()

    def test_mcp_invocation_exception_propagates_unchanged(self):
        tool = _make_armoriq_tool()
        agent = _make_agent([tool])
        client = _make_mock_client()
        exc = MCPInvocationException("invoke boom", mcp="mcp1", action="act1")
        client.invoke.side_effect = exc

        crew = ArmorIQCrew(agents=[agent], tasks=[], armoriq_client=client, llm="gpt-4o")

        # Patch inner crew to actually call the tool
        def run_tool(inputs=None):
            tool._run(param="v")
            return "done"

        with patch.object(crew._crew, "kickoff", side_effect=run_tool):
            with self.assertRaises(MCPInvocationException) as ctx:
                crew.kickoff()
        self.assertIs(ctx.exception, exc)


if __name__ == "__main__":
    unittest.main()
