"""
Tests for the retry/idempotency layer added to ArmorIQClient (PR #22 port).

Covers:
  - 5xx triggers retry, 4xx does not
  - Network errors trigger retry
  - Idempotency-Key is reused across retries (so the backend can dedupe)
  - max_retries=0 disables retry entirely
  - Stable Idempotency-Key for delegation/mark-executed and plan/status
"""

from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

import httpx
import pytest

from armoriq_sdk.client import ArmorIQClient


@pytest.fixture
def client(monkeypatch):
    """Construct a client without hitting the network for validation."""
    monkeypatch.setenv("ARMORIQ_API_KEY", "ak_claw_test-retry")
    monkeypatch.setenv("USER_ID", "u")
    monkeypatch.setenv("AGENT_ID", "a")
    # ak_claw_ skips the validateApiKey ping during construction.
    return ArmorIQClient(_skip_api_key_validation=True)


def _resp(status: int, body: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json=body or {})


def test_5xx_triggers_retry(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    calls: List[tuple] = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs.get("headers", {}).get("Idempotency-Key")))
        if len(calls) < 3:
            return _resp(503)
        return _resp(200, {"ok": True})

    client.http_client.post = fake_post  # type: ignore
    response = client._retry_post("https://x/y", json={}, idempotency_key="key1")
    assert response.status_code == 200
    assert len(calls) == 3
    # Same Idempotency-Key on every attempt — so the backend can dedupe.
    assert all(k == "key1" for _, k in calls)


def test_4xx_does_not_retry(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    calls: List[str] = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return _resp(400, {"message": "bad request"})

    client.http_client.post = fake_post  # type: ignore
    response = client._retry_post("https://x/y", json={})
    assert response.status_code == 400
    assert len(calls) == 1


def test_network_error_triggers_retry(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    attempts = {"n": 0}

    def fake_post(url, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise httpx.ConnectError("boom")
        return _resp(200)

    client.http_client.post = fake_post  # type: ignore
    response = client._retry_post("https://x/y", json={})
    assert response.status_code == 200
    assert attempts["n"] == 2


def test_max_retries_zero_disables_retry(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    client.max_retries = 0
    attempts = {"n": 0}

    def fake_post(url, **kwargs):
        attempts["n"] += 1
        return _resp(503)

    client.http_client.post = fake_post  # type: ignore
    response = client._retry_post("https://x/y", json={})
    assert response.status_code == 503
    assert attempts["n"] == 1


def test_mark_delegation_executed_uses_stable_idempotency_key(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    captured: List[dict] = []

    def fake_post(url, **kwargs):
        captured.append({
            "url": url,
            "headers": kwargs.get("headers", {}),
            "json": kwargs.get("json"),
        })
        return _resp(200)

    client.http_client.post = fake_post  # type: ignore
    client.mark_delegation_executed("u@example.com", "deleg-123")
    assert len(captured) == 1
    assert captured[0]["headers"]["Idempotency-Key"] == "mark-exec:deleg-123"
    assert captured[0]["headers"]["X-User-Email"] == "u@example.com"
    assert captured[0]["json"] == {"delegationId": "deleg-123"}


def test_update_plan_status_uses_stable_idempotency_key(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    captured: List[dict] = []

    def fake_post(url, **kwargs):
        captured.append({"url": url, "headers": kwargs.get("headers", {})})
        return _resp(200)

    client.http_client.post = fake_post  # type: ignore
    client.update_plan_status("plan-9", "completed")
    assert len(captured) == 1
    assert captured[0]["headers"]["Idempotency-Key"] == "plan-status:plan-9:completed"


def test_complete_plan_delegates_to_update_plan_status(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_a, **_kw: None)
    seen_status: List[str] = []

    def fake_post(url, **kwargs):
        body = kwargs.get("json") or {}
        seen_status.append(body.get("status"))
        return _resp(200)

    client.http_client.post = fake_post  # type: ignore
    client.complete_plan("plan-x")
    assert seen_status == ["completed"]
