"""
ArmorIQ SDK — LangChain Integration (Coming Soon)

Requires: pip install armoriq-sdk[langchain]
"""


class ArmorIQLangChain:
    """ArmorIQ integration for LangChain. (Coming soon)"""

    def __init__(self, *args, armoriq_client, **kwargs):
        try:
            import langchain  # noqa: F401
        except ImportError:
            raise ImportError(
                "langchain is not installed.\n"
                "Install it with: pip install armoriq-sdk[langchain]"
            )
        raise NotImplementedError(
            "ArmorIQ LangChain integration is not yet implemented."
        )
