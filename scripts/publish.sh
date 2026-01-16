#!/bin/bash
# ArmorIQ SDK - Quick Publishing Script

set -e

echo "🚀 ArmorIQ SDK Publishing Script"
echo "================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo -e "${RED}❌ Error: setup.py not found. Run this script from the SDK root directory.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Clean previous builds${NC}"
rm -rf dist/ build/ *.egg-info
echo "✅ Cleaned"
echo ""

echo -e "${YELLOW}Step 2: Install build dependencies${NC}"
pip install --upgrade build twine
echo "✅ Dependencies installed"
echo ""

echo -e "${YELLOW}Step 3: Build the package${NC}"
python -m build
echo "✅ Package built"
echo ""

echo -e "${YELLOW}Step 4: Check the package${NC}"
python -m twine check dist/*
echo "✅ Package validated"
echo ""

echo -e "${GREEN}Package is ready!${NC}"
echo ""
echo "📦 Built files:"
ls -lh dist/
echo ""

echo "Next steps:"
echo "==========="
echo ""
echo "For TestPyPI (recommended for testing):"
echo "  python -m twine upload --repository testpypi dist/*"
echo ""
echo "For PyPI (production):"
echo "  python -m twine upload dist/*"
echo ""
echo "For Git distribution (beta users):"
echo "  git tag v1.0.0"
echo "  git push origin develop --tags"
echo "  Share: pip install git+https://github.com/armoriq/armoriq-sdk-python.git@v1.0.0"
echo ""
echo "To test locally:"
echo "  pip install dist/armoriq_sdk-*.whl"
echo ""
