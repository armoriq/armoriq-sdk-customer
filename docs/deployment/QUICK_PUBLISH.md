# 🚀 Quick Start: Publishing ArmorIQ SDK

## For Immediate Beta Release (Fastest - Do This First!)

### Option 1: GitHub Direct Installation (5 minutes)

This is the **fastest way** to make the SDK available to users right now.

```bash
# 1. Navigate to SDK directory
cd /home/hari/Videos/Armoriq/armoriq-sdk-python

# 2. Commit and push your code
git add .
git commit -m "Release v1.0.0-beta: Production-ready SDK"
git push origin develop

# 3. Create and push a tag
git tag v1.0.0-beta
git push origin v1.0.0-beta

# 4. Share this command with beta users:
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta
```

**Users can install immediately with:**
```bash
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta
```

✅ **Done!** Your SDK is now available to users.

---

## For PyPI Distribution (When Ready for Public Release)

### Option 2: Publish to PyPI (30 minutes)

This makes it available via `pip install armoriq-sdk`

```bash
# 1. Navigate to SDK directory
cd /home/hari/Videos/Armoriq/armoriq-sdk-python

# 2. Run the publish script
./publish.sh

# This will:
# - Clean previous builds
# - Install dependencies
# - Build the package  
# - Validate it

# 3. Create PyPI account (if you don't have one)
# Visit: https://pypi.org/account/register/

# 4. Create API token
# Visit: https://pypi.org/manage/account/token/
# Save token securely

# 5. Upload to TestPyPI first (for testing)
python -m twine upload --repository testpypi dist/*
# Username: __token__
# Password: <your-test-pypi-token>

# 6. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ armoriq-sdk

# 7. If everything works, upload to real PyPI
python -m twine upload dist/*
# Username: __token__
# Password: <your-pypi-token>

# 8. Verify
pip install armoriq-sdk
```

✅ **Done!** SDK is on PyPI. Users can now: `pip install armoriq-sdk`

---

## Verification Steps

### Test the Installation

```bash
# Create a test environment
python -m venv test_env
source test_env/bin/activate.fish  # or .bash_profile

# Install from your chosen method
pip install armoriq-sdk
# OR
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta

# Test import
python -c "from armoriq_sdk import ArmorIQClient; print('✅ SDK works!')"

# Run example
cat > test_sdk.py << 'EOF'
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.models import PlanCapture

# Initialize
client = ArmorIQClient(
    iap_endpoint="http://localhost:8082",
    user_id="test-user",
    agent_id="test-agent"
)

# Create plan
plan = PlanCapture(
    plan={"goal": "Test", "actions": []},
    plan_hash="test",
    merkle_root="test"
)

print("✅ ArmorIQ SDK is working!")
print(f"Client: {client}")
print(f"Plan: {plan}")
EOF

python test_sdk.py

# Cleanup
deactivate
rm -rf test_env test_sdk.py
```

---

## Share with Users

### Beta Users Email Template

```
Subject: ArmorIQ SDK v1.0.0-beta is Ready!

Hi Team,

The ArmorIQ SDK is now available for beta testing! 🎉

INSTALLATION:
  pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta

QUICK START:
  from armoriq_sdk import ArmorIQClient
  
  client = ArmorIQClient(
      iap_endpoint="https://iap.armoriq.io",
      user_id="your-user-id",
      agent_id="your-agent-id"
  )

DOCUMENTATION:
  - README: https://github.com/armoriq/armoriq-sdk-python
  - Examples: https://github.com/armoriq/armoriq-sdk-python/tree/develop/examples
  - API Docs: https://docs.armoriq.io

WHAT'S INCLUDED:
  ✅ Secure plan capture
  ✅ Intent token issuance
  ✅ MCP invocation
  ✅ Agent delegation
  ✅ Full documentation

FEEDBACK:
  Please share any issues or suggestions at:
  https://github.com/armoriq/armoriq-sdk-python/issues

Happy building!
ArmorIQ Team
```

---

## Documentation Website (Optional)

### Using GitHub Pages

```bash
cd /home/hari/Videos/Armoriq/armoriq-sdk-python

# Install MkDocs
pip install mkdocs mkdocs-material

# Create docs
mkdocs new docs

# Build
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy

# Your docs will be at:
# https://armoriq.github.io/armoriq-sdk-python/
```

---

## Summary

### ✅ Fastest Path (Do This Now):
1. Push code to GitHub ✅
2. Tag as v1.0.0-beta ✅
3. Share Git install command with users ✅
4. Users can install immediately ✅

### ✅ For Production (Do Later):
1. Test with beta users
2. Incorporate feedback
3. Publish to PyPI
4. Announce publicly

### ✅ Right Now:
```bash
cd /home/hari/Videos/Armoriq/armoriq-sdk-python
git add .
git commit -m "Release v1.0.0-beta"
git tag v1.0.0-beta
git push origin develop --tags
```

**That's it! Your SDK is now usable by anyone with:**
```bash
pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0-beta
```

🎉 **Congratulations! Your SDK is published!** 🎉
