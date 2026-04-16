"""
Build-time environment marker.

This file is the ONLY difference between the `dev` and `main` branches —
merging dev → main conflicts on this single constant, which is intentional
so the release owner consciously flips the default before publishing prod.

  main branch  →  ARMORIQ_ENV = "production"  (CLI + SDK default to api.armoriq.io)
  dev  branch  →  ARMORIQ_ENV = "staging"     (CLI + SDK default to staging-api.armoriq.io)

Users can always override at runtime via:
  - ARMORIQ_ENV env var
  - BACKEND_ENDPOINT / ARMORIQ_BACKEND_URL env vars
  - explicit constructor args on ArmorIQClient
"""

ARMORIQ_ENV: str = "production"

# Endpoint table — keep in sync with GCP Cloud Run domain mappings
# (verified via `gcloud beta run domain-mappings describe --domain=...`).
ENDPOINTS = {
    "production": {
        "backend": "https://api.armoriq.io",
        "proxy": "https://cloud-run-proxy.armoriq.io",
        "iap": "https://iap.armoriq.io",
    },
    "staging": {
        "backend": "https://staging-api.armoriq.io",
        "proxy": "https://staging-proxy.armoriq.io",
        "iap": "https://staging-iap.armoriq.io",
    },
}


def resolve(kind: str) -> str:
    import os

    override = os.getenv("ARMORIQ_ENV", ARMORIQ_ENV).lower()
    if override not in ENDPOINTS:
        override = "production"
    return ENDPOINTS[override][kind]
