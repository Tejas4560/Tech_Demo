#!/usr/bin/env python3
"""
Test script to verify Groq API configuration.
Run this to ensure your GROQ_API_KEY is set up correctly.
"""
import os
import sys
import importlib.util
from pathlib import Path

def load_module_from_file(module_name, file_path):
    """Load a Python module from a file path without triggering package imports."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def test_groq_configuration():
    """Test Groq API configuration."""
    print("=" * 60)
    print("Testing Groq API Configuration")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Checking environment variables...")
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY")
    
    if not groq_key:
        print("   ❌ GROQ_API_KEY not set")
        print()
        print("   Please set your Groq API key:")
        print("   1. Get a key from https://console.groq.com/keys")
        print("   2. Add to .env file: GROQ_API_KEY=your_key_here")
        print("   3. Or export: export GROQ_API_KEY=your_key_here")
        return False
    
    if groq_key == "your_groq_api_key_here":
        print("   ❌ GROQ_API_KEY still has placeholder value")
        print("   Please update .env with your actual API key")
        return False
    
    print(f"   ✅ GROQ_API_KEY is set ({groq_key[:10]}...)")
    print()
    
    # Check groq package
    print("2. Checking groq package installation...")
    try:
        import groq
        print(f"   ✅ groq package installed (version: {groq.__version__ if hasattr(groq, '__version__') else 'unknown'})")
    except ImportError:
        print("   ❌ groq package not installed")
        print("   Run: pip install groq")
        return False
    print()
    
    # Test client creation - load groq_client directly without package imports
    print("3. Testing Groq client creation...")
    try:
        # Load groq_client module directly to avoid package __init__.py
        groq_client_path = Path(__file__).parent / 'src' / 'gen' / 'groq_client.py'
        groq_client = load_module_from_file('groq_client_test', groq_client_path)
        
        client = groq_client.create_client()
        model = groq_client.get_deployment_name()
        print(f"   ✅ Client created successfully")
        print(f"   📦 Model: {model}")
    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test API call
    print("4. Testing API call...")
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from Groq!' and nothing else."}
        ]
        
        print("   🔄 Making test API call...")
        response = groq_client.create_chat_completion(client, model, messages, max_tokens=50)
        
        print(f"   ✅ API call successful!")
        print(f"   📝 Response: {response[:100]}")
    except Exception as e:
        print(f"   ❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test unified LLM client detection
    print("5. Testing unified LLM client detection...")
    try:
        # Check environment to determine which client would be used
        azure_key = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        
        if groq_key and not azure_key:
            print("   ✅ Unified client will use Groq")
        elif azure_key:
            print("   ⚠️  Unified client will use Azure OpenAI (Groq key ignored)")
            print("   💡 To use Groq, remove or comment out AZURE_OPENAI_* variables in .env")
        else:
            print("   ❌ No API configured in unified client")
            return False
    except Exception as e:
        print(f"   ⚠️  Could not check unified client: {e}")
    print()
    
    print("=" * 60)
    print("✅ All tests passed! Your Groq API is configured correctly.")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Run the test generator:")
    print("     python -m src.gen.enhanced_generate --target . --outdir tests/generated")
    print()
    print("  2. Or use the full pipeline:")
    print("     bash pipeline_runner.sh")
    print()
    
    return True

if __name__ == "__main__":
    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        if os.path.exists(".env"):
            load_dotenv()
            print("📋 Loaded environment from .env")
            print()
    except ImportError:
        pass
    
    success = test_groq_configuration()
    sys.exit(0 if success else 1)
