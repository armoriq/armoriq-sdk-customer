"""
ArmorIQ SDK - Build Secure AI Agents
"""
from setuptools import setup, find_packages
from pathlib import Path

readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="armoriq-sdk",
    version="0.2.1",
    author="ArmorIQ Team",
    author_email="license@armoriq.io",
    description="ArmorIQ SDK - Build secure AI agents with cryptographic intent verification.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://armoriq.ai",
    project_urls={
        "Documentation": "https://docs.armoriq.io",
        "Source Code": "https://github.com/armoriq/armoriq-sdk-python",
    },
    packages=find_packages(exclude=["tests*", "examples*"]),
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "pytest-asyncio>=0.21.0", "black", "mypy"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="armoriq sdk ai agents security verification",
)
