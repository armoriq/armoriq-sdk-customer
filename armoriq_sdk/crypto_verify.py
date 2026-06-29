"""Cryptographic verification helpers for intent tokens.

canonical_json matches the IAP signer's
json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
so verify_ed25519 can recompute the exact bytes a token signature covers.
"""

import json
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def verify_intent_token_signature(raw_token: Any) -> bool:
    """Verify the Ed25519 signature of an intent token (the csrg token dict
    stored under raw_token['token']) over the exact canonical payload the IAP
    signed. Returns False on missing material or a bad signature. No expiry check.
    """
    token_data = (raw_token or {}).get("token") or {}
    public_key_hex = token_data.get("public_key")
    signature_hex = token_data.get("signature")
    if not public_key_hex or not signature_hex or not token_data.get("plan_hash"):
        return False
    payload = {
        "plan_hash": token_data.get("plan_hash"),
        "issued_at": token_data.get("issued_at"),
        "expires_at": token_data.get("expires_at"),
        "policy": token_data.get("policy"),
        "identity": token_data.get("identity"),
        "public_key": token_data.get("public_key"),
        "version": token_data.get("version"),
    }
    if token_data.get("allowed_operations"):
        payload["allowed_operations"] = token_data["allowed_operations"]
    if token_data.get("resource_scope"):
        payload["resource_scope"] = token_data["resource_scope"]
    return verify_ed25519(public_key_hex, canonical_json(payload), signature_hex)


def verify_ed25519(public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    """Verify a raw Ed25519 signature (hex) over message with a raw 32-byte
    public key (hex). Returns False on any malformed input or bad signature."""
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except (InvalidSignature, ValueError):
        return False
