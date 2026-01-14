#!/usr/bin/env fish
# ArmorIQ SDK Development Setup Script

echo "🚀 ArmorIQ SDK Setup"
echo "===================="
echo ""

# Check for uv
if not command -v uv &> /dev/null
    echo "❌ Error: 'uv' is not installed"
    echo "   Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
end

echo "✅ Found uv package manager"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

if test $status -eq 0
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
end

echo ""
echo "🧪 Running tests..."
uv run pytest

if test $status -eq 0
    echo "✅ All tests passed"
else
    echo "⚠️  Some tests failed - review output above"
end

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate.fish"
echo ""
echo "  2. Run examples:"
echo "     uv run python examples/basic_agent.py"
echo ""
echo "  3. Run tests:"
echo "     uv run pytest"
echo "     uv run pytest --cov=armoriq_sdk"
echo ""
echo "  4. Start development:"
echo "     - Edit code in armoriq_sdk/"
echo "     - Add tests in tests/"
echo "     - Run examples in examples/"
echo ""
