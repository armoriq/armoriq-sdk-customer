"""
Credential store for the armoriq CLI.

Mirrors armoriq-sdk-customer-ts/src/cli/credentials.ts (same JSON shape
and same path at ~/.armoriq/credentials.json, mode 0600) so both SDKs
can read each other's file during any transition.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

ARMORIQ_DIR = Path.home() / ".armoriq"
CREDENTIALS_FILE = ARMORIQ_DIR / "credentials.json"


@dataclass
class Credentials:
    apiKey: str
    email: str
    userId: str
    orgId: str
    savedAt: str


def load_credentials() -> Optional[Credentials]:
    try:
        if not CREDENTIALS_FILE.exists():
            return None
        data = json.loads(CREDENTIALS_FILE.read_text())
        key = data.get("apiKey")
        if isinstance(key, str) and key.startswith("ak_"):
            return Credentials(
                apiKey=key,
                email=data.get("email", "") or "",
                userId=data.get("userId", "") or "",
                orgId=data.get("orgId", "") or "",
                savedAt=data.get("savedAt", "") or "",
            )
        return None
    except Exception:
        return None


def save_credentials(creds: Credentials) -> None:
    ARMORIQ_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(asdict(creds), indent=2) + "\n")
    try:
        os.chmod(CREDENTIALS_FILE, 0o600)
    except OSError:
        pass


def clear_credentials() -> bool:
    try:
        if CREDENTIALS_FILE.exists():
            CREDENTIALS_FILE.unlink()
            return True
        return False
    except Exception:
        return False


def get_credentials_path() -> str:
    return str(CREDENTIALS_FILE)
