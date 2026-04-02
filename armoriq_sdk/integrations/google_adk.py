"""
ArmorIQ SDK — Google ADK Integration (Coming Soon)

Requires: pip install armoriq-sdk[google-adk]
"""


class ArmorIQGoogleADK:
    """ArmorIQ integration for Google ADK. (Coming soon)"""

    def __init__(self, *args, armoriq_client, **kwargs):
        try:
            import google.adk  # noqa: F401
        except ImportError:
            raise ImportError(
                "google-adk is not installed.\n"
                "Install it with: pip install armoriq-sdk[google-adk]"
            )
        raise NotImplementedError(
            "ArmorIQ Google ADK integration is not yet implemented."
        )
