# Quick Start Guide - Running with Groq API

## Prerequisites

- Python 3.9 or higher
- Groq API key (get from [https://console.groq.com/keys](https://console.groq.com/keys))

## Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
bash setup_groq.sh
```

This script will:
1. Create a virtual environment
2. Install all dependencies
3. Create `.env` file from template
4. Test your Groq API connection

## Option 2: Manual Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.groq.example .env

# Edit .env and add your Groq API key
nano .env  # or use your favorite editor
```

Add your API key:
```bash
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### 3. Test Configuration

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from gen.groq_client import validate_client_configuration
validate_client_configuration()
"
```

## Running the Test Generator

### Basic Usage

```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate

# Generate tests for current directory
python -m src.gen.enhanced_generate --target . --outdir tests/generated
```

### With Debug Output

```bash
# Set debug mode in .env
export TESTGEN_DEBUG=1

# Run generator
python -m src.gen.enhanced_generate --target . --outdir tests/generated
```

### Advanced Options

```bash
# Specify target directory and output
python -m src.gen.enhanced_generate \
  --target /path/to/your/project \
  --outdir tests/generated \
  --analysis ast_full_analysis.json

# Focus on specific files
python -m src.gen.enhanced_generate \
  --target . \
  --outdir tests/generated \
  --focus-files src/mymodule.py,src/utils.py
```

## Available Groq Models

Edit `GROQ_MODEL` in `.env` to change the model:

| Model | Best For | Speed | Quality |
|-------|----------|-------|---------|
| `llama-3.3-70b-versatile` | Code generation (default) | Fast | Excellent |
| `llama-3.1-70b-versatile` | General purpose | Fast | Excellent |
| `mixtral-8x7b-32768` | Long context | Medium | Very Good |
| `gemma2-9b-it` | Quick tasks | Very Fast | Good |

## Troubleshooting

### "groq package not installed"

```bash
pip install groq
```

### "GROQ_API_KEY is not set"

Make sure you've:
1. Created `.env` file
2. Added your API key (not the placeholder)
3. Exported the variable: `export $(cat .env | grep -v '^#' | xargs)`

### "Rate limit exceeded"

Groq has generous free tier limits, but if you hit them:
- Wait a few minutes
- Reduce the number of files being processed
- Use a smaller model (gemma2-9b-it)

### "Authentication error"

- Check your API key is correct
- Verify it hasn't expired
- Generate a new key at https://console.groq.com/keys

## What's Different from Azure OpenAI?

The project now uses `groq_client.py` instead of `openai_client.py`. The interface is identical, so all existing code works without modification.

**Advantages of Groq:**
- ✅ Faster inference (up to 10x faster)
- ✅ Free tier available
- ✅ No Azure account needed
- ✅ Simple API key authentication

## Next Steps

After generating tests:

1. **Review generated tests:**
   ```bash
   ls -la tests/generated/
   ```

2. **Run the tests:**
   ```bash
   pytest tests/generated/ -v
   ```

3. **Check coverage:**
   ```bash
   pytest tests/generated/ --cov=. --cov-report=html
   open htmlcov/index.html
   ```

4. **Use auto-fixer if tests fail:**
   ```bash
   python run_auto_fixer.py --test-dir tests/generated
   ```

## Environment Variables Reference

```bash
# Required
GROQ_API_KEY=your_api_key_here

# Optional
GROQ_MODEL=llama-3.3-70b-versatile  # Model selection
TESTGEN_DEBUG=1                      # Enable debug output
TESTGEN_OUTPUT_DIR=tests/generated   # Output directory
TESTGEN_MAX_RETRIES=3                # Retry attempts
MIN_COVERAGE_THRESHOLD=90            # Coverage target
```

## Getting Help

- Groq Documentation: https://console.groq.com/docs
- Groq API Keys: https://console.groq.com/keys
- Project Issues: Check the README.md for more details
