#!/bin/bash
# setup_groq.sh - Quick setup script for running the project with Groq API

set -e  # Exit on error

echo "🚀 Setting up AI Test Generation Pipeline with Groq API"
echo "========================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo "📝 Creating .env from .env.groq.example..."
    cp .env.groq.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your GROQ_API_KEY"
    echo ""
    echo "To get a Groq API key:"
    echo "  1. Visit https://console.groq.com/keys"
    echo "  2. Sign up or log in"
    echo "  3. Create a new API key"
    echo "  4. Copy the key and paste it in .env"
    echo ""
    read -p "Press Enter after you've added your GROQ_API_KEY to .env..."
fi

# Load environment variables
if [ -f ".env" ]; then
    echo "📋 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Validate Groq API key
if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your_groq_api_key_here" ]; then
    echo "❌ GROQ_API_KEY is not set or still has placeholder value"
    echo "Please edit .env and add your actual Groq API key"
    exit 1
fi

echo "✅ GROQ_API_KEY is set"
echo ""

# Test Groq client
echo "🧪 Testing Groq API connection..."
python3 test_groq_config.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Run the test generator:"
echo "     python -m src.gen.enhanced_generate --target . --outdir tests/generated"
echo ""
echo "  2. Or use the full pipeline (if you have a target repo):"
echo "     bash pipeline_runner.sh"
echo ""
echo "  3. Check the generated tests in tests/generated/"
echo ""
echo "💡 Tip: Set TESTGEN_DEBUG=1 in .env to see detailed output"
