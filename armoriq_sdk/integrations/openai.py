"""
ArmorIQ SDK — OpenAI Integration (Coming Soon)

Requires: pip install armoriq-sdk[openai]
"""


class ArmorIQOpenAI:
    """ArmorIQ integration for OpenAI. (Coming soon)"""

    def __init__(self, *args, armoriq_client, **kwargs):
        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "openai is not installed.\n"
                "Install it with: pip install armoriq-sdk[openai]"
            )
        raise NotImplementedError(
            "ArmorIQ OpenAI integration is not yet implemented."
        )
