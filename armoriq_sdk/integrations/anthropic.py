"""
ArmorIQ SDK — Anthropic Integration (Coming Soon)

Requires: pip install armoriq-sdk[anthropic]
"""


class ArmorIQAnthropic:
    """ArmorIQ integration for Anthropic. (Coming soon)"""

    def __init__(self, *args, armoriq_client, **kwargs):
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "anthropic is not installed.\n"
                "Install it with: pip install armoriq-sdk[anthropic]"
            )
        raise NotImplementedError(
            "ArmorIQ Anthropic integration is not yet implemented."
        )
