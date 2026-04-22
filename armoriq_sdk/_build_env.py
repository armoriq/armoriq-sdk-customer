"""
Build-time environment marker.

This file is the ONLY difference between the `dev` and `main` branches —
merging dev → main conflicts on this single constant, which is intentional
so the release owner consciously flips the default before publishing prod.

  main branch  →  ARMORIQ_ENV = "production"  (prod URLs; published as stable)
  dev  branch  →  ARMORIQ_ENV = "staging"     (staging URLs; published as -dev)

The baked constant is the branch-baked default. Set ARMORIQ_ENV=local (or
staging/production) in your shell to override at runtime — matches the TS
SDK's behavior. Per-endpoint env vars (BACKEND_ENDPOINT / IAP_ENDPOINT /
PROXY_ENDPOINT) still win over both.
"""

import os as _os

ARMORIQ_ENV: str = "staging"

# Endpoint table — keep in sync with GCP Cloud Run domain mappings
# (verified via `gcloud beta run domain-mappings describe --domain=...`).
#   prod:
#     api.armoriq.ai        → conmap-auto            (us-central1)
#     iap.armoriq.ai        → csrg-execution-service (us-central1)
#     proxy.armoriq.ai      → armoriq-proxy-server   (us-central1)
#   staging:
#     staging-api.armoriq.ai          → conmap-auto-staging            (us-central1)
#     iap-staging.armoriq.ai          → csrg-execution-service-staging (us-central1)
#     cloud-run-proxy.armoriq.io      → armoriq-proxy-dev              (europe-west1)
#   local: matches startup.md canonical ports — conmap-auto :3000,
#     armoriq-proxy-server :3001, csrg-iap :8080.
ENDPOINTS = {
    "production": {
        "backend": "https://api.armoriq.ai",
        "proxy": "https://proxy.armoriq.ai",
        "iap": "https://iap.armoriq.ai",
    },
    "staging": {
        "backend": "https://staging-api.armoriq.ai",
        "proxy": "https://cloud-run-proxy.armoriq.io",
        "iap": "https://iap-staging.armoriq.ai",
    },
    "local": {
        "backend": "http://127.0.0.1:3000",
        "proxy": "http://127.0.0.1:3001",
        "iap": "http://127.0.0.1:8080",
    },
}


def _active_env() -> str:
    override = (_os.getenv("ARMORIQ_ENV") or "").strip().lower()
    if override in ENDPOINTS:
        return override
    return ARMORIQ_ENV


def resolve(kind: str) -> str:
    return ENDPOINTS[_active_env()][kind]
