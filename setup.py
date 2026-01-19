""""""

ArmorIQ SDK - Customer EditionArmorIQ SDK - Python SDK for Intent Assurance Plane

Simple, powerful SDK for building AI-powered toolsBuild secure AI agents with cryptographic verification

""""""

from setuptools import setup, find_packages

from setuptools import setup, find_packagesfrom pathlib import Path



with open("README.md", "r", encoding="utf-8") as fh:# Read README for long description

    long_description = fh.read()readme_file = Path(__file__).parent / "README.md"

long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(

    name="armoriq",setup(

    version="1.0.0",    name="armoriq-sdk",

    author="ArmorIQ Team",    version="0.1.1",

    author_email="support@armoriq.io",    author="ArmorIQ Team",

    description="Simple, powerful SDK for building AI-powered tools with security built-in",    author_email="support@armoriq.io",

    long_description=long_description,    description="Python SDK for ArmorIQ Intent Assurance Plane - Build secure AI agents with cryptographic verification",

    long_description_content_type="text/markdown",    long_description=long_description,

    url="https://github.com/armoriq/sdk-customer",    long_description_content_type="text/markdown",

    project_urls={    url="https://armoriq.ai",

        "Bug Tracker": "https://github.com/armoriq/sdk-customer/issues",    project_urls={

        "Documentation": "https://docs.armoriq.io",        "Documentation": "https://docs.armoriq.io",

        "Source Code": "https://github.com/armoriq/sdk-customer",        "Source Code": "https://github.com/armoriq/armoriq-sdk-python",

    },        "Bug Reports": "https://github.com/armoriq/armoriq-sdk-python/issues",

    packages=find_packages(),        "Changelog": "https://github.com/armoriq/armoriq-sdk-python/blob/main/CHANGELOG.md",

    classifiers=[    },

        "Development Status :: 4 - Beta",    packages=find_packages(exclude=["tests*", "examples*", "docs*"]),

        "Intended Audience :: Developers",    classifiers=[

        "Topic :: Software Development :: Libraries :: Python Modules",        "Development Status :: 4 - Beta",

        "Topic :: Security",        "Intended Audience :: Developers",

        "License :: OSI Approved :: MIT License",        "Topic :: Software Development :: Libraries :: Python Modules",

        "Programming Language :: Python :: 3",        "Topic :: Security",

        "Programming Language :: Python :: 3.8",        "Topic :: Scientific/Engineering :: Artificial Intelligence",

        "Programming Language :: Python :: 3.9",        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3.10",        "Programming Language :: Python :: 3",

        "Programming Language :: Python :: 3.11",        "Programming Language :: Python :: 3.9",

        "Programming Language :: Python :: 3.12",        "Programming Language :: Python :: 3.10",

    ],        "Programming Language :: Python :: 3.11",

    python_requires=">=3.8",        "Programming Language :: Python :: 3.12",

    install_requires=[        "Operating System :: OS Independent",

        "requests>=2.28.0",    ],

    ],    python_requires=">=3.9",

    extras_require={    install_requires=[

        "dev": [        "httpx>=0.24.0",

            "pytest>=7.0.0",        "pydantic>=2.0.0",

            "pytest-cov>=4.0.0",        "cryptography>=41.0.0",

            "black>=23.0.0",    ],

            "flake8>=6.0.0",    extras_require={

            "mypy>=1.0.0",        "dev": [

        ],            "pytest>=7.0.0",

    },            "pytest-asyncio>=0.21.0",

    keywords="armoriq mcp ai security authentication authorization tools",            "pytest-cov>=4.0.0",

    license="MIT",            "black>=23.0.0",

)            "mypy>=1.0.0",

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
