"""Strands integration: BeforeToolCallEvent enforcement (allow/block/hold/fail-closed).

These exercise the hook logic directly with a fake session + fake event, so they
prove the enforcement decisions without needing the strands package or a live
backend. The hold path relies on session.check() resolving the delegation poll
to allowed/blocked, which the hook then honors.
"""

from armoriq_sdk.integrations.strands import _ArmorIQStrandsHooks
from armoriq_sdk.session import EnforceResult


class _FakeScope:
    pass


class _FakeSession:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises

    def check(self, tool_name, args, user_email=None):
        if self._raises:
            raise self._raises
        return self._result


class _FakeEvent:
    def __init__(self, name, args):
        self.agent = object()
        self.tool_use = {"name": name, "input": args}
        self.cancel_tool = False


def _hooks_with(session):
    h = _ArmorIQStrandsHooks(
        factory=None, scope=_FakeScope(), user_email="u@acme.com", goal=None
    )
    h.session = session
    h._plan_started = True  # skip plan minting in these unit tests
    return h


def test_allow_does_not_cancel():
    h = _hooks_with(_FakeSession(EnforceResult(allowed=True, action="allow")))
    ev = _FakeEvent("Stripe__charge", {"amount": 10})
    h._before_tool_call(ev)
    assert ev.cancel_tool is False


def test_block_cancels_tool():
    h = _hooks_with(
        _FakeSession(EnforceResult(allowed=False, action="block", reason="not allowed"))
    )
    ev = _FakeEvent("Stripe__charge", {"amount": 999999})
    h._before_tool_call(ev)
    assert isinstance(ev.cancel_tool, str) and "block" in ev.cancel_tool


def test_hold_not_approved_cancels_tool():
    # check() returns not-allowed with action=hold after the delegation poll
    # times out or is rejected -> the tool must be cancelled.
    h = _hooks_with(
        _FakeSession(
            EnforceResult(allowed=False, action="hold", reason="awaiting approval")
        )
    )
    ev = _FakeEvent("Stripe__refund", {"amount": 500})
    h._before_tool_call(ev)
    assert isinstance(ev.cancel_tool, str) and "hold" in ev.cancel_tool


def test_hold_approved_runs_tool():
    # If the delegation is approved, check() returns allowed -> tool runs.
    h = _hooks_with(_FakeSession(EnforceResult(allowed=True, action="allow")))
    ev = _FakeEvent("Stripe__refund", {"amount": 500})
    h._before_tool_call(ev)
    assert ev.cancel_tool is False


def test_enforcement_error_fails_closed():
    h = _hooks_with(_FakeSession(raises=RuntimeError("backend down")))
    ev = _FakeEvent("Stripe__charge", {})
    h._before_tool_call(ev)
    assert isinstance(ev.cancel_tool, str) and "fail-closed" in ev.cancel_tool
