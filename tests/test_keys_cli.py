"""
Tests for `armoriq keys list / revoke / prune` (closes #24).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from typing import Any, List

import httpx
import pytest

from armoriq_sdk.cli import (
    cmd_keys_list,
    cmd_keys_revoke,
    cmd_keys_prune,
    KEY_COUNT_WARN_THRESHOLD,
)
from armoriq_sdk.credentials import Credentials


@pytest.fixture
def creds(monkeypatch):
    fake = Credentials(
        apiKey="ak_test_login",
        email="u@example.com",
        userId="u",
        orgId="o",
        savedAt=datetime.now(timezone.utc).isoformat(),
    )
    # The keys commands call _require_credentials() which loads from disk;
    # patch it to return our fake instead of touching ~/.armoriq.
    monkeypatch.setattr("armoriq_sdk.cli._require_credentials", lambda: fake)
    return fake


def _mock_httpx_client(responses: List[Any], captured: List[dict]):
    """Build a httpx.Client subclass that returns canned responses in order."""

    class _Mock:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def request(self, method, url, **kwargs):
            captured.append({"method": method, "url": url, "kwargs": kwargs})
            r = responses.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

    return _Mock()


def _resp(status: int, body: dict | list) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(body).encode("utf-8"), headers={"content-type": "application/json"})


def test_keys_list_prints_table(creds, monkeypatch, capsys):
    captured: List[dict] = []
    responses = [_resp(200, {"data": [
        {"id": "k1", "name": "main", "status": "active", "lastUsedAt": "2026-04-01T00:00:00Z"},
        {"id": "k2", "name": "ci", "status": "active", "lastUsedAt": None},
    ]})]
    monkeypatch.setattr("httpx.Client", lambda **kw: _mock_httpx_client(responses, captured))

    rc = cmd_keys_list(argparse.Namespace())
    assert rc == 0
    out = capsys.readouterr().out
    assert "main" in out and "ci" in out
    assert captured[0]["method"] == "GET"
    assert captured[0]["url"].endswith("/api-keys")
    assert captured[0]["kwargs"]["headers"]["X-API-Key"] == "ak_test_login"


def test_keys_list_warns_above_threshold(creds, monkeypatch, capsys):
    captured: List[dict] = []
    keys = [{"id": f"k{i}", "name": f"n{i}", "status": "active"} for i in range(KEY_COUNT_WARN_THRESHOLD + 2)]
    responses = [_resp(200, {"data": keys})]
    monkeypatch.setattr("httpx.Client", lambda **kw: _mock_httpx_client(responses, captured))

    cmd_keys_list(argparse.Namespace())
    assert "armoriq keys prune" in capsys.readouterr().out


def test_keys_revoke_calls_revoke_endpoint(creds, monkeypatch, capsys):
    captured: List[dict] = []
    responses = [_resp(200, {"ok": True})]
    monkeypatch.setattr("httpx.Client", lambda **kw: _mock_httpx_client(responses, captured))

    rc = cmd_keys_revoke(argparse.Namespace(key_id="abc"))
    assert rc == 0
    assert captured[0]["method"] == "POST"
    assert captured[0]["url"].endswith("/api-keys/abc/revoke")
    assert "Revoked key abc" in capsys.readouterr().out


def test_keys_revoke_requires_id(creds):
    from armoriq_sdk.cli import CLIError
    with pytest.raises(CLIError, match="Usage"):
        cmd_keys_revoke(argparse.Namespace(key_id=""))


def test_keys_prune_dry_run_lists_only(creds, monkeypatch, capsys):
    captured: List[dict] = []
    now = datetime.now(timezone.utc)
    keys = [
        {"id": "fresh", "name": "n", "status": "active", "lastUsedAt": now.isoformat()},
        {"id": "stale", "name": "n", "status": "active",
         "lastUsedAt": (now - timedelta(days=120)).isoformat()},
        {"id": "expired", "name": "n", "status": "active",
         "expiresAt": (now - timedelta(days=1)).isoformat()},
    ]
    responses = [_resp(200, {"data": keys})]
    monkeypatch.setattr("httpx.Client", lambda **kw: _mock_httpx_client(responses, captured))

    rc = cmd_keys_prune(argparse.Namespace(yes=False))
    assert rc == 0
    out = capsys.readouterr().out
    assert "stale" in out and "expired" in out
    assert "fresh" not in out
    assert "Re-run with --yes" in out
    # Only one HTTP call (the list) — no revokes happened.
    assert len(captured) == 1


def test_keys_prune_with_yes_revokes_candidates(creds, monkeypatch, capsys):
    captured: List[dict] = []
    now = datetime.now(timezone.utc)
    keys = [
        {"id": "stale", "name": "n", "status": "active",
         "lastUsedAt": (now - timedelta(days=120)).isoformat()},
    ]
    responses = [
        _resp(200, {"data": keys}),  # initial list
        _resp(200, {"ok": True}),    # revoke stale
    ]
    monkeypatch.setattr("httpx.Client", lambda **kw: _mock_httpx_client(responses, captured))

    rc = cmd_keys_prune(argparse.Namespace(yes=True))
    assert rc == 0
    assert any(c["url"].endswith("/api-keys/stale/revoke") for c in captured)


def test_keys_prune_skips_active_keys(creds, monkeypatch, capsys):
    captured: List[dict] = []
    now = datetime.now(timezone.utc)
    keys = [
        {"id": "fresh", "name": "n", "status": "active", "lastUsedAt": now.isoformat()},
    ]
    responses = [_resp(200, {"data": keys})]
    monkeypatch.setattr("httpx.Client", lambda **kw: _mock_httpx_client(responses, captured))

    rc = cmd_keys_prune(argparse.Namespace(yes=True))
    assert rc == 0
    assert "Nothing to prune" in capsys.readouterr().out
