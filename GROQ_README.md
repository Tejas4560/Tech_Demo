# AI Test Generation Pipeline - Now with Groq Support! 🚀

This project now supports **Groq API** as an alternative to Azure OpenAI, making it easier and faster to get started!

## What Changed?

✅ **New Groq Support**: Use Groq's lightning-fast LLM inference (up to 10x faster than Azure)  
✅ **Unified Client**: Automatically detects and uses Groq or Azure OpenAI based on your environment  
✅ **Easy Setup**: Simple configuration with just an API key  
✅ **Free Tier**: Groq offers a generous free tier to get started  

## Quick Start with Groq

### 1. Get Your Groq API Key

1. Visit [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `gsk_...`)

### 2. Run the Setup Script

```bash
# Automated setup (recommended)
bash setup_groq.sh
```

This will:
- Create a virtual environment
- Install dependencies (including `groq` package)
- Create `.env` file
- Test your API connection

### 3. Configure Your API Key

Edit `.env` and add your key:

```bash
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### 4. Test the Configuration

```bash
python test_groq_config.py
```

You should see:
```
✅ All tests passed! Your Groq API is configured correctly.
```

### 5. Generate Tests!

```bash
# Basic usage
python -m src.gen.enhanced_generate --target . --outdir tests/generated

# With debug output
export TESTGEN_DEBUG=1
python -m src.gen.enhanced_generate --target . --outdir tests/generated
```

## Available Models

Edit `GROQ_MODEL` in `.env` to change the model:

| Model | Best For | Speed | Context |
|-------|----------|-------|---------|
| `llama-3.3-70b-versatile` | Code generation ⭐ | Very Fast | 128K |
| `llama-3.1-70b-versatile` | General purpose | Very Fast | 128K |
| `mixtral-8x7b-32768` | Long context | Fast | 32K |
| `gemma2-9b-it` | Quick tasks | Ultra Fast | 8K |

**Default**: `llama-3.3-70b-versatile` (recommended for code generation)

## Switching Between Groq and Azure OpenAI

The project automatically detects which API to use:

### Use Groq (Priority)
```bash
# Set in .env
GROQ_API_KEY=gsk_your_key_here
```

### Use Azure OpenAI
```bash
# Set in .env
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

**Note**: If both are set, Azure OpenAI takes priority. To use Groq, remove or comment out the Azure variables.

## Environment Variables

### Required (choose one)

**For Groq:**
```bash
GROQ_API_KEY=gsk_your_key_here
```

**For Azure OpenAI:**
```bash
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment
```

### Optional

```bash
# Model selection (Groq only)
GROQ_MODEL=llama-3.3-70b-versatile

# Debug output
TESTGEN_DEBUG=1

# Test generation settings
TESTGEN_OUTPUT_DIR=tests/generated
TESTGEN_MAX_RETRIES=3
MIN_COVERAGE_THRESHOLD=90
```

## Troubleshooting

### "groq package not installed"

```bash
pip install groq
```

### "GROQ_API_KEY is not set"

1. Create `.env` file from template:
   ```bash
   cp .env.groq.example .env
   ```

2. Edit `.env` and add your actual API key

3. Load environment:
   ```bash
   export $(cat .env | grep -v '^#' | xargs)
   ```

### "Rate limit exceeded"

Groq has generous free tier limits. If you hit them:
- Wait a few minutes
- Reduce the number of files being processed
- Use a smaller/faster model (gemma2-9b-it)

### "Authentication error"

- Verify your API key is correct (starts with `gsk_`)
- Check it hasn't expired
- Generate a new key at https://console.groq.com/keys

## Why Groq?

**Advantages over Azure OpenAI:**
- ✅ **10x faster** inference (Groq's custom LPU chips)
- ✅ **Free tier** available (no credit card required)
- ✅ **Simple setup** (just an API key)
- ✅ **No Azure account** needed
- ✅ **Lower latency** (especially for code generation)

**When to use Azure OpenAI:**
- You already have Azure credits
- You need GPT-4 specifically
- You have enterprise Azure requirements

## Files Added

- `src/gen/groq_client.py` - Groq API adapter
- `src/gen/llm_client.py` - Unified client (auto-detects Groq/Azure)
- `.env.groq.example` - Environment template
- `setup_groq.sh` - Automated setup script
- `test_groq_config.py` - Configuration test script
- `GROQ_QUICKSTART.md` - Detailed setup guide
- `GROQ_README.md` - This file

## Next Steps

1. ✅ Set up Groq API (you're here!)
2. Generate tests for your project
3. Run the tests: `pytest tests/generated/ -v`
4. Check coverage: `pytest tests/generated/ --cov=. --cov-report=html`
5. Use auto-fixer if needed: `python run_auto_fixer.py --test-dir tests/generated`

## Getting Help

- **Groq Documentation**: https://console.groq.com/docs
- **Groq API Keys**: https://console.groq.com/keys
- **Groq Models**: https://console.groq.com/docs/models
- **Project Issues**: See main README.md

## Original Azure OpenAI Setup

If you prefer to use Azure OpenAI, see the original README.md for setup instructions. The project supports both!

---

**Happy Testing with Groq! 🚀**
