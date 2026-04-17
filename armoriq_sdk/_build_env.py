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

ARMORIQ_ENV: str = "staging"

# Endpoint table — keep in sync with GCP Cloud Run domain mappings
# (verified via `gcloud beta run domain-mappings describe --domain=...`).
#   prod:
#     api.armoriq.ai        → conmap-auto            (us-central1)
#     iap.armoriq.ai        → csrg-execution-service (us-central1)
#     proxy.armoriq.ai      → armoriq-proxy-server   (us-central1)
#   staging:
#     staging-api.armoriq.ai          → conmap-auto-staging            (us-central1)
#     csrg-execution-service-staging* → csrg-execution-service-staging (us-central1; no custom domain yet)
#     cloud-run-proxy.armoriq.io      → armoriq-proxy-dev              (europe-west1)
ENDPOINTS = {
    "production": {
        "backend": "https://api.armoriq.ai",
        "proxy": "https://proxy.armoriq.ai",
        "iap": "https://iap.armoriq.ai",
    },
    "staging": {
        "backend": "https://staging-api.armoriq.ai",
        "proxy": "https://cloud-run-proxy.armoriq.io",
        "iap": "https://csrg-execution-service-staging-77dabykria-uc.a.run.app",
    },
}


def resolve(kind: str) -> str:
    import os

    override = os.getenv("ARMORIQ_ENV", ARMORIQ_ENV).lower()
    if override not in ENDPOINTS:
        override = "production"
    return ENDPOINTS[override][kind]
