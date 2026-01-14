#!/usr/bin/env fish
# ArmorIQ SDK - Quick Test Script
# Run this to verify your SDK installation

echo "🧪 ArmorIQ SDK - Quick Test"
echo "============================"
echo ""

# Check Python version
echo "📍 Checking Python version..."
set python_version (python --version 2>&1 | awk '{print $2}')
echo "   Python $python_version"

# Check if in SDK directory
if not test -f pyproject.toml
    echo "❌ Error: Not in armoriq-sdk-python directory"
    echo "   Please cd to the SDK directory first"
    exit 1
end

# Check if dependencies installed
echo ""
echo "📦 Checking dependencies..."
if test -d .venv
    echo "   ✅ Virtual environment found"
else
    echo "   ⚠️  Virtual environment not found"
    echo "   Run: uv sync"
    exit 1
end

# Run quick import test
echo ""
echo "🔍 Testing SDK import..."
uv run python -c "from armoriq_sdk import ArmorIQClient; print('   ✅ SDK import successful')" 2>/dev/null
if test $status -ne 0
    echo "   ❌ Failed to import SDK"
    echo "   Run: uv sync"
    exit 1
end

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
uv run pytest tests/ -q --tb=no
set test_status $status

if test $test_status -eq 0
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "⚠️  Some tests failed - check output above"
end

# Check for running services
echo ""
echo "🔌 Checking for running services..."

# Check IAP
set iap_status (curl -s http://localhost:8000/health 2>/dev/null)
if test -n "$iap_status"
    echo "   ✅ IAP service detected at http://localhost:8000"
else
    echo "   ⚠️  IAP service not detected at http://localhost:8000"
    echo "      Start with: cd ../csrg-iap && uv run python -m csrg_iap.main"
end

# Check Proxy
set proxy_status (curl -s http://localhost:3001/health 2>/dev/null)
if test -n "$proxy_status"
    echo "   ✅ Proxy service detected at http://localhost:3001"
else
    echo "   ⚠️  Proxy service not detected at http://localhost:3001"
    echo "      Start with: cd ../armoriq-proxy-server && npm run start:dev"
end

# Summary
echo ""
echo "📊 Summary"
echo "=========="

if test $test_status -eq 0
    echo "   ✅ SDK is installed correctly"
else
    echo "   ⚠️  SDK installation may have issues"
end

if test -n "$iap_status"; and test -n "$proxy_status"
    echo "   ✅ Services are running"
    echo ""
    echo "🚀 Ready to run examples!"
    echo "   Try: uv run python examples/basic_agent.py"
else
    echo "   ⚠️  Some services are not running"
    echo ""
    echo "📝 To run examples, start:"
    if test -z "$iap_status"
        echo "   1. IAP: cd ../csrg-iap && uv run python -m csrg_iap.main"
    end
    if test -z "$proxy_status"
        echo "   2. Proxy: cd ../armoriq-proxy-server && npm run start:dev"
    end
end

echo ""
echo "📚 Documentation:"
echo "   - Quick Start: less QUICKSTART.md"
echo "   - Examples: ls examples/"
echo "   - Full Docs: less README.md"
echo ""
