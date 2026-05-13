"""
armoriq login / logout / whoami.

OAuth 2.0 device-code flow (RFC 8628). Ports
armoriq-sdk-customer-ts/src/cli/commands/{login,logout,whoami}.ts.

The browser approval page either redirects straight back to our
local callback with the key, or — if the callback can't be reached —
we fall back to polling /auth/device/token.
"""

from __future__ import annotations

import argparse
import http.server
import os
import queue
import socket
import threading
import time
import webbrowser
from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

import httpx

from ._build_env import resolve as _resolve_env
from .credentials import (
    Credentials,
    clear_credentials,
    get_credentials_path,
    load_credentials,
    save_credentials,
)


SUCCESS_HTML = b"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ArmorIQ</title>
<link rel="icon" href="https://armoriq.ai/images/favicon.svg" type="image/svg+xml">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         display: flex; align-items: center; justify-content: center; height: 100vh;
         margin: 0; background: #f8fafc; color: #1e293b; }
  .card { text-align: center; padding: 3rem; background: white;
          border-radius: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          max-width: 400px; }
  .check { width: 64px; height: 64px; background: #dcfce7; border-radius: 50%;
           display: flex; align-items: center; justify-content: center;
           margin: 0 auto 1.5rem; }
  .check svg { width: 32px; height: 32px; color: #16a34a; }
  h2 { margin: 0 0 0.5rem; font-size: 1.25rem; }
  p { margin: 0; font-size: 0.875rem; color: #64748b; }
</style></head><body>
<div class="card">
  <div class="check">
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
    </svg>
  </div>
  <h2>Authorized</h2>
  <p>You can close this tab and return to your terminal.</p>
</div>
</body></html>"""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_callback_server(
    port: int,
) -> Tuple["queue.Queue[dict]", http.server.ThreadingHTTPServer]:
    result_q: "queue.Queue[dict]" = queue.Queue(maxsize=1)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            if u.path == "/callback":
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(SUCCESS_HTML)
                except BrokenPipeError:
                    pass
                try:
                    result_q.put_nowait(q)
                except queue.Full:
                    pass
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args, **kwargs):  # silence default stderr logs
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return result_q, srv


def cmd_login(args: argparse.Namespace) -> int:
    backend = (
        getattr(args, "backend", None)
        or os.getenv("ARMORIQ_BACKEND_URL")
        or _resolve_env("backend")
    ).rstrip("/")

    requested_org = (getattr(args, "org", None) or "").strip()
    requested_product = (
        (getattr(args, "product", None) or "").strip()
        or (os.getenv("ARMORIQ_PRODUCT") or "").strip()
    )

    print("")
    print("  \033[1m\033[36m┃ ArmorIQ Login\033[0m")
    print("")

    port = _find_free_port()
    callback_url = f"http://localhost:{port}/callback"
    result_q, srv = _start_callback_server(port)

    code_body = {"callback_url": callback_url}
    if requested_product:
        code_body["product"] = requested_product

    try:
        r = httpx.post(
            f"{backend}/auth/device/code",
            json=code_body,
            timeout=10.0,
        )
        r.raise_for_status()
        dc = r.json()
    except Exception as exc:
        srv.shutdown()
        print(f"  \033[31m✘\033[0m Failed to request device code: {exc}")
        return 1

    device_code = dc["device_code"]
    user_code = dc["user_code"]
    verification_complete = dc["verification_uri_complete"]
    interval = int(dc.get("interval", 5) or 5)
    expires_in = int(dc.get("expires_in", 600) or 600)

    sep = "&" if "?" in verification_complete else "?"
    browser_url = f"{verification_complete}{sep}callback={quote(callback_url, safe='')}"
    if requested_org:
        browser_url += f"&org={quote(requested_org, safe='')}"
    if requested_product:
        browser_url += f"&product={quote(requested_product, safe='')}"

    print("  Opening browser...\n")
    try:
        webbrowser.open(browser_url)
    except Exception:
        print("  \033[33m!\033[0m Browser didn't open automatically.")

    print("  If the browser didn't open, visit:")
    print(f"    \033[36m\033[1m{browser_url}\033[0m\n")
    print(f"  Confirm this code in your browser: \033[1m{user_code}\033[0m\n")

    print("  Waiting for authorization...", end="", flush=True)

    deadline = time.time() + expires_in
    result: Optional[dict] = None
    last_poll_err: Optional[str] = None

    while time.time() < deadline and result is None:
        try:
            cb = result_q.get(timeout=interval)
            key = cb.get("key") or ""
            if key:
                result = {
                    "api_key": key,
                    "email": cb.get("email", ""),
                    "user_id": cb.get("user_id", ""),
                    "org_id": cb.get("org_id", ""),
                }
                break
        except queue.Empty:
            pass

        try:
            pr = httpx.post(
                f"{backend}/auth/device/token",
                json={"deviceCode": device_code},
                timeout=10.0,
            )
            data = pr.json()
            err = data.get("error")
            if err in ("authorization_pending", "slow_down"):
                continue
            if err:
                last_poll_err = data.get("error_description") or err
                break
            if data.get("api_key"):
                result = {
                    "api_key": data["api_key"],
                    "email": data.get("email", ""),
                    "user_id": data.get("user_id", ""),
                    "org_id": data.get("org_id", ""),
                }
                break
        except httpx.RequestError:
            continue

    srv.shutdown()

    if result is None:
        print(" \033[31m✘\033[0m")
        msg = last_poll_err or "Timed out waiting for authorization. Run `armoriq login` again."
        print(f"  \033[31m✘\033[0m {msg}")
        return 1

    save_credentials(
        Credentials(
            apiKey=result["api_key"],
            email=result.get("email", "") or "",
            userId=result.get("user_id", "") or "",
            orgId=result.get("org_id", "") or "",
            savedAt=datetime.now(timezone.utc).isoformat(),
        )
    )

    print(" \033[32m✔\033[0m")
    print("")
    email = result.get("email") or "unknown"
    org = result.get("org_id") or "unknown"
    print(f"  \033[32m✔\033[0m Logged in as \033[1m{email}\033[0m (org: {org})")
    print(f"  \033[32m✔\033[0m API key saved to {get_credentials_path()}")
    print("")
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    if clear_credentials():
        print(f"  \033[32m✔\033[0m Credentials removed from {get_credentials_path()}")
    else:
        print("  \033[2mNo credentials found — already logged out.\033[0m")
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    creds = load_credentials()
    if not creds:
        print("  \033[2mNot logged in. Run `armoriq login` to authenticate.\033[0m")
        return 0
    print("")
    print("  \033[1m\033[36m┃ ArmorIQ Credentials\033[0m")
    print("")
    key_preview = (creds.apiKey[:16] + "...") if len(creds.apiKey) > 16 else creds.apiKey
    print(f"  Email:    \033[1m{creds.email or 'unknown'}\033[0m")
    print(f"  API Key:  \033[2m{key_preview}\033[0m")
    print(f"  User ID:  \033[2m{creds.userId or 'n/a'}\033[0m")
    print(f"  Org ID:   \033[2m{creds.orgId or 'n/a'}\033[0m")
    print(f"  Saved at: \033[2m{creds.savedAt or 'n/a'}\033[0m")
    print(f"  File:     \033[2m{get_credentials_path()}\033[0m")
    print("")
    return 0
