"""
Build-time environment marker.

This file is the ONLY difference between the `dev` and `main` branches —
merging dev → main conflicts on this single constant, which is intentional
so the release owner consciously flips the default before publishing prod.

  main branch  →  ARMORIQ_ENV = "production"  (prod URLs; published as stable)
  dev  branch  →  ARMORIQ_ENV = "staging"     (staging URLs; published as -dev)

The baked constant is the ONLY source of truth for which environment's
URLs to use — no runtime env-var override. To point the SDK at staging,
install the dev build; to override a specific endpoint for testing,
pass `backend_endpoint=...` to the ArmorIQClient constructor or set
BACKEND_ENDPOINT / IAP_ENDPOINT / PROXY_ENDPOINT env vars.
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
#     iap-staging.armoriq.ai          → csrg-execution-service-staging (us-central1)
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
        "iap": "https://iap-staging.armoriq.ai",
    },
}


def resolve(kind: str) -> str:
    return ENDPOINTS[ARMORIQ_ENV][kind]
