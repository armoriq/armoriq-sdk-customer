"""
ArmorIQ SDK - Python SDK for Intent Assurance Plane
Build secure AI agents with cryptographic verification
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="armoriq-sdk",
    version="0.1.1",
    author="ArmorIQ Team",
    author_email="support@armoriq.io",
    description="Python SDK for ArmorIQ Intent Assurance Plane - Build secure AI agents with cryptographic verification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://armoriq.ai",
    project_urls={
        "Documentation": "https://docs.armoriq.io",
        "Source Code": "https://github.com/armoriq/armoriq-sdk-python",
        "Bug Reports": "https://github.com/armoriq/armoriq-sdk-python/issues",
        "Changelog": "https://github.com/armoriq/armoriq-sdk-python/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests*", "examples*", "docs*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings[python]>=0.24.0",
        ],
    },
    keywords=[
        "ai",
        "security",
        "agent",
        "mcp",
        "intent",
        "verification",
        "cryptography",
        "zero-trust",
        "armoriq",
    ],
    include_package_data=True,
    zip_safe=False,
)
