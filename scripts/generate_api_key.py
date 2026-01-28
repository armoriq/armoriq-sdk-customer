#!/usr/bin/env python3
"""
Generate a secure API key for local testing and print its SHA-256 hash.

Usage:
  python3 scripts/generate_api_key.py

Copy the generated key into the customer proxy `.env` as `ARMORIQ_DEV_API_KEY`
or export it in your shell before starting the proxy:

  export ARMORIQ_DEV_API_KEY=<the-key>

The proxy in development will load `ARMORIQ_DEV_API_KEY` automatically.
"""
import secrets
import hashlib
import sys

def generate_key(length: int = 40) -> str:
    # URL-safe base64-like string
    return secrets.token_urlsafe(length)

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def main():
    key = generate_key(32)
    hashed = hash_key(key)
    print("# API key (plaintext) - keep this secret")
    print(key)
    print()
    print("# SHA-256 hash (for proxy internal store lookup)")
    print(hashed)

    print()
    print("# Quick usage (fish shell):")
    print(f"set -x ARMORIQ_DEV_API_KEY '{key}'")
    print("# Or add to /path/to/armoriq-proxy-server-customer/.env:\nARMORIQ_DEV_API_KEY=<the-key>")

if __name__ == '__main__':
    main()
