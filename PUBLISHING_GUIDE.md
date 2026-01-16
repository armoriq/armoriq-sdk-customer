# 🚀 ArmorIQ SDK - Publishing & Distribution Guide

## Goal: Make SDK Available to Users

This guide covers how to publish the ArmorIQ SDK and make it usable for developers.

---

## 📦 Option 1: PyPI (Recommended - Public/Private)

### **Step 1: Prepare Package Structure**

Ensure your package structure is correct:
```
armoriq-sdk-python/
├── armoriq_sdk/
│   ├── __init__.py
│   ├── client.py
│   ├── models.py
│   ├── exceptions.py
│   └── ...
├── tests/
├── examples/
├── docs/
├── setup.py
├── pyproject.toml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

### **Step 2: Create setup.py**

```python
# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="armoriq-sdk",
    version="1.0.0",
    author="ArmorIQ Team",
    author_email="support@armoriq.io",
    description="Python SDK for ArmorIQ Intent Assurance Plane - Build secure AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/armoriq/armoriq-sdk-python",
    packages=find_packages(exclude=["tests*", "examples*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
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
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "armoriq=armoriq_sdk.cli:main",  # Optional CLI tool
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/armoriq/armoriq-sdk-python/issues",
        "Documentation": "https://docs.armoriq.io",
        "Source": "https://github.com/armoriq/armoriq-sdk-python",
    },
)
```

### **Step 3: Create pyproject.toml (Modern Python)**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "armoriq-sdk"
version = "1.0.0"
description = "Python SDK for ArmorIQ Intent Assurance Plane"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "ArmorIQ Team", email = "support@armoriq.io"}
]
keywords = ["ai", "security", "agent", "mcp", "intent", "verification"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Security",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "cryptography>=41.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[project.urls]
Homepage = "https://armoriq.io"
Documentation = "https://docs.armoriq.io"
Repository = "https://github.com/armoriq/armoriq-sdk-python"
Issues = "https://github.com/armoriq/armoriq-sdk-python/issues"

[tool.setuptools.packages.find]
where = ["."]
include = ["armoriq_sdk*"]
exclude = ["tests*", "examples*"]
```

### **Step 4: Create MANIFEST.in**

```
# MANIFEST.in
include README.md
include LICENSE
include CHANGELOG.md
include requirements.txt
recursive-include armoriq_sdk *.py
recursive-include docs *.md
recursive-include examples *.py
prune tests
prune .github
```

### **Step 5: Build the Package**

```bash
cd /home/hari/Videos/Armoriq/armoriq-sdk-python

# Install build tools
pip install build twine

# Build the distribution
python -m build

# This creates:
# dist/armoriq_sdk-1.0.0-py3-none-any.whl
# dist/armoriq-sdk-1.0.0.tar.gz
```

### **Step 6: Test Installation Locally**

```bash
# Test in a clean virtual environment
python -m venv test_env
source test_env/bin/activate  # or test_env/bin/activate.fish

# Install from local wheel
pip install dist/armoriq_sdk-1.0.0-py3-none-any.whl

# Test import
python -c "from armoriq_sdk import ArmorIQClient; print('✅ SDK installed successfully!')"

# Deactivate
deactivate
```

### **Step 7: Publish to PyPI**

```bash
# Create PyPI account at https://pypi.org/account/register/
# Create API token at https://pypi.org/manage/account/token/

# Upload to TestPyPI first (for testing)
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ armoriq-sdk

# If everything works, upload to real PyPI
python -m twine upload dist/*

# Now users can install with:
# pip install armoriq-sdk
```

---

## 📦 Option 2: Private PyPI (For Internal/Enterprise Users)

### **Using AWS CodeArtifact**

```bash
# 1. Create CodeArtifact repository
aws codeartifact create-repository \
    --domain armoriq \
    --domain-owner YOUR_AWS_ACCOUNT_ID \
    --repository armoriq-sdk \
    --description "ArmorIQ SDK Python packages"

# 2. Get authorization token
export CODEARTIFACT_AUTH_TOKEN=`aws codeartifact get-authorization-token \
    --domain armoriq \
    --domain-owner YOUR_AWS_ACCOUNT_ID \
    --query authorizationToken \
    --output text`

# 3. Configure pip
aws codeartifact login \
    --tool pip \
    --domain armoriq \
    --domain-owner YOUR_AWS_ACCOUNT_ID \
    --repository armoriq-sdk

# 4. Publish package
python -m twine upload \
    --repository-url `aws codeartifact get-repository-endpoint \
        --domain armoriq \
        --domain-owner YOUR_AWS_ACCOUNT_ID \
        --repository armoriq-sdk \
        --format pypi \
        --query repositoryEndpoint \
        --output text` \
    dist/*

# 5. Users install with:
# pip install armoriq-sdk --index-url YOUR_CODEARTIFACT_URL
```

### **Using JFrog Artifactory**

```bash
# 1. Build package
python -m build

# 2. Upload to Artifactory
curl -u username:password \
    -T dist/armoriq_sdk-1.0.0-py3-none-any.whl \
    "https://artifactory.armoriq.io/artifactory/pypi-local/armoriq-sdk/1.0.0/"

# 3. Users install with:
# pip install armoriq-sdk --index-url https://artifactory.armoriq.io/artifactory/api/pypi/pypi-local/simple
```

---

## 📦 Option 3: GitHub Packages (For Open Source)

### **Step 1: Configure GitHub Actions**

```yaml
# .github/workflows/publish.yml
name: Publish to GitHub Packages

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to GitHub Packages
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.GITHUB_TOKEN }}
      run: |
        python -m twine upload \
          --repository-url https://upload.pypi.org/legacy/ \
          dist/*
```

### **Step 2: Users Install**

```bash
# Users install with:
pip install armoriq-sdk
```

---

## 📦 Option 4: Direct Git Installation (Simplest for Beta)

### **For Beta Users - No Publishing Needed!**

```bash
# Users can install directly from GitHub
pip install git+https://github.com/armoriq/armoriq-sdk-python.git

# Or specific branch/tag
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@develop
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0
```

### **For Private Repos**

```bash
# With SSH
pip install git+ssh://git@github.com/armoriq/armoriq-sdk-python.git

# With Personal Access Token
pip install git+https://USERNAME:TOKEN@github.com/armoriq/armoriq-sdk-python.git
```

---

## 📚 Option 5: Docker Image (For Containerized Users)

### **Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install SDK
COPY . /sdk
RUN pip install /sdk

# Optional: Install examples
COPY examples/ /app/examples/

CMD ["python"]
```

### **Build and Publish**

```bash
# Build image
docker build -t armoriq/sdk:1.0.0 .

# Push to Docker Hub
docker push armoriq/sdk:1.0.0

# Users can use:
# docker run -it armoriq/sdk:1.0.0 python
```

---

## 🎯 Recommended Publishing Strategy

### **Phase 1: Beta Testing (NOW)**
```bash
# Option: Direct Git installation
1. Push SDK to GitHub
2. Tag release: git tag v1.0.0-beta
3. Share with beta users:
   pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta
```

### **Phase 2: Private Release (After Proxy Fix)**
```bash
# Option: Private PyPI or GitHub Packages
1. Fix proxy token verification
2. Run full integration tests
3. Publish to private package index
4. Enterprise customers install via private index
```

### **Phase 3: Public Release (When Ready for GA)**
```bash
# Option: Public PyPI
1. Security audit
2. Performance benchmarks
3. Publish to PyPI: pip install armoriq-sdk
4. Announce on website/blog
```

---

## 📝 Pre-Publishing Checklist

### **Code Quality**
- [ ] All tests passing
- [ ] Code formatted (black/ruff)
- [ ] Type hints verified (mypy)
- [ ] No security vulnerabilities (bandit)
- [ ] Dependencies up to date

### **Documentation**
- [ ] README.md complete
- [ ] API documentation generated
- [ ] Examples working
- [ ] CHANGELOG.md updated
- [ ] LICENSE file included

### **Package Metadata**
- [ ] Version number set
- [ ] Author information correct
- [ ] Keywords appropriate
- [ ] Classifiers accurate
- [ ] URLs working

### **Testing**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Examples run successfully
- [ ] Tested on Python 3.9, 3.10, 3.11
- [ ] Tested on Linux, macOS, Windows

---

## 🚀 Quick Start Publishing Commands

### **For Immediate Beta Distribution**

```bash
cd /home/hari/Videos/Armoriq/armoriq-sdk-python

# 1. Ensure code is committed
git add .
git commit -m "Release v1.0.0-beta"
git tag v1.0.0-beta
git push origin develop --tags

# 2. Share with beta users
echo "Beta users can install with:"
echo "pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta"
```

### **For PyPI Distribution (When Ready)**

```bash
# 1. Install tools
pip install build twine

# 2. Build package
python -m build

# 3. Test locally
pip install dist/armoriq_sdk-1.0.0-py3-none-any.whl

# 4. Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# 5. Test from TestPyPI
pip install --index-url https://test.pypi.org/simple/ armoriq-sdk

# 6. Upload to PyPI (if test passed)
python -m twine upload dist/*

# 7. Users install
pip install armoriq-sdk
```

---

## 📖 Documentation Site Setup

### **Using MkDocs**

```bash
# 1. Install MkDocs
pip install mkdocs mkdocs-material

# 2. Create docs structure
mkdocs new .

# 3. Configure mkdocs.yml
cat > mkdocs.yml << EOF
site_name: ArmorIQ SDK Documentation
theme:
  name: material
  palette:
    primary: indigo
    accent: indigo

nav:
  - Home: index.md
  - Getting Started: quickstart.md
  - API Reference: api.md
  - Examples: examples.md
  - Architecture: architecture.md

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - admonition
EOF

# 4. Build docs
mkdocs build

# 5. Deploy to GitHub Pages
mkdocs gh-deploy

# Docs available at: https://armoriq.github.io/armoriq-sdk-python/
```

---

## 📧 User Onboarding Email Template

```
Subject: Welcome to ArmorIQ SDK Beta!

Hi [User],

Thanks for joining the ArmorIQ SDK beta program! Here's how to get started:

1. INSTALL THE SDK
   pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta

2. CONFIGURE YOUR CREDENTIALS
   export ARMORIQ_IAP_ENDPOINT="https://iap.armoriq.io"
   export ARMORIQ_API_KEY="your-api-key-here"

3. RUN YOUR FIRST EXAMPLE
   python examples/basic_agent.py

4. READ THE DOCS
   https://docs.armoriq.io

5. JOIN OUR SLACK
   https://armoriq.slack.com

Need help? Reply to this email or ping us on Slack!

Best,
ArmorIQ Team
```

---

## 🎯 Next Steps

### **Immediate (Do Now):**
```bash
# 1. Create setup.py and pyproject.toml
# 2. Test build locally
python -m build

# 3. Tag and push to GitHub
git tag v1.0.0-beta
git push origin develop --tags

# 4. Share with beta users via Git installation
```

### **This Week:**
```bash
# 1. Fix proxy token verification
# 2. Run full integration tests
# 3. Publish to TestPyPI
# 4. Get beta user feedback
```

### **Next Sprint:**
```bash
# 1. Incorporate feedback
# 2. Security audit
# 3. Publish to PyPI
# 4. Public announcement
```

---

**The SDK is ready to be shared with users! Start with Git installation for beta, then move to PyPI for production.** 🚀
