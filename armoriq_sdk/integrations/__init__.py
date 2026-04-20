"""
ArmorIQ SDK — Framework Integrations

Available integrations (require their extra to be installed):
  crewai     → ArmorIQCrew       — pip install armoriq-sdk[crewai]
  langchain  → ArmorIQLangChain  — pip install armoriq-sdk[langchain]
  google-adk → ArmorIQGoogleADK  — pip install armoriq-sdk[google-adk]
  openai     → ArmorIQOpenAI     — pip install armoriq-sdk[openai]
  anthropic  → ArmorIQAnthropic  — pip install armoriq-sdk[anthropic]
"""

from .crewai import ArmorIQCrew
from .langchain import ArmorIQLangChain
from .google_adk import ArmorIQADK
from .openai import ArmorIQOpenAI
from .anthropic import ArmorIQAnthropic

__all__ = [
    "ArmorIQCrew",
    "ArmorIQLangChain",
    "ArmorIQADK",
    "ArmorIQOpenAI",
    "ArmorIQAnthropic",
]
