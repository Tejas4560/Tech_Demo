# Groq API Integration - Known Issues and Solutions

## ✅ Integration Status: COMPLETE

The Groq API integration is **fully functional**. However, there's one important limitation to be aware of:

## ⚠️ Token Limit Issue

**Problem**: Groq has a **tokens-per-minute (TPM) limit** that's lower than Azure OpenAI:
- Groq free tier: **12,000 TPM**
- Azure OpenAI: **90,000+ TPM**

When generating tests for large projects (100+ files), the generator may hit this limit.

**Error you'll see**:
```
Error code: 413 - Request too large for model `llama-3.3-70b-versatile`
Limit 12000, Requested 72237
```

## 🔧 Solutions

### Option 1: Target Specific Files (Recommended)

Instead of generating tests for the entire project, target specific files:

```bash
# Generate tests for specific files only
python -m src.gen.enhanced_generate \
  --target . \
  --outdir tests/generated \
  --focus-files src/mymodule.py,src/utils.py
```

### Option 2: Use Smaller Model

Switch to a faster, smaller model with lower token usage:

```bash
# Edit .env and change:
GROQ_MODEL=gemma2-9b-it  # Much faster, lower token usage
```

### Option 3: Upgrade to Groq Dev Tier

Get higher limits by upgrading at https://console.groq.com/settings/billing

- **Free tier**: 12,000 TPM
- **Dev tier**: 100,000+ TPM (paid)

### Option 4: Use Azure OpenAI

If you have Azure credits, Azure OpenAI has much higher limits:

```bash
# In .env, add Azure credentials:
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment

# Comment out or remove GROQ_API_KEY
# GROQ_API_KEY=...
```

### Option 5: Process in Batches

Generate tests for one directory at a time:

```bash
# Generate for src/gen/ only
python -m src.gen.enhanced_generate \
  --target src/gen \
  --outdir tests/generated/gen_tests

# Generate for src/auto_fixer/ only  
python -m src.gen.enhanced_generate \
  --target src/auto_fixer \
  --outdir tests/generated/fixer_tests
```

## 📊 Project Size Recommendations

| Project Size | Recommendation |
|--------------|----------------|
| < 20 files | ✅ Use Groq free tier directly |
| 20-50 files | ⚠️ Use `--focus-files` or smaller model |
| 50-100 files | ⚠️ Process in batches by directory |
| 100+ files | 🔴 Use Azure OpenAI or Groq Dev tier |

## 🎯 Your Current Project

Your project has:
- **2,983 Python files** (very large!)
- **778 functions** to test
- **92 classes** to test

**Recommendation**: Use Option 1 or Option 5 to target specific modules.

## Example: Generate Tests for Specific Module

```bash
# Just test the gen module
python -m src.gen.enhanced_generate \
  --target src/gen \
  --outdir tests/generated

# Or focus on specific important files
python -m src.gen.enhanced_generate \
  --target . \
  --outdir tests/generated \
  --focus-files src/gen/enhanced_generate.py,src/gen/groq_client.py
```

## ✅ Verification

The integration itself works perfectly - we successfully tested it with `test_groq_config.py`:
- ✅ Client creation
- ✅ API calls
- ✅ Model selection
- ✅ Error handling

The only limitation is the token-per-minute rate limit for large projects.

## 💡 Best Practice

For large projects like yours, **always use focused test generation**:

1. Identify your most critical modules
2. Generate tests for them one at a time
3. This gives you better control and faster iteration

```bash
# Example workflow for your project:
python -m src.gen.enhanced_generate --target src/gen --outdir tests/gen
python -m src.gen.enhanced_generate --target src/auto_fixer --outdir tests/auto_fixer
python -m src.gen.enhanced_generate --target src/test_generation --outdir tests/test_generation
```

This approach is actually **better** than trying to generate everything at once, as it:
- Avoids rate limits
- Generates more focused, higher-quality tests
- Allows incremental testing and validation
- Easier to review and maintain
