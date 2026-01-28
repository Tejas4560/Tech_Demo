# src/gen/llm_client.py
"""
Unified LLM client - automatically uses Groq or Azure OpenAI based on environment variables.
This is a drop-in replacement for openai_client.py that supports both providers.

This module is STANDALONE - it loads groq_client and openai_client dynamically to avoid
relative import issues when used by auto-fixer or other external tools.
"""
import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional

# Check which provider is configured
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")

# Determine which provider to use
USE_GROQ = bool(GROQ_API_KEY and not AZURE_API_KEY)
USE_AZURE = bool(AZURE_API_KEY)

# Dynamically load the appropriate client module
_client_module = None

def _load_client_module():
    """Load the appropriate client module dynamically."""
    global _client_module
    
    if _client_module is not None:
        return _client_module
    
    try:
        # Get the directory where this file is located
        current_file = Path(__file__).resolve()
        gen_dir = current_file.parent
        
        if USE_GROQ:
            # Load groq_client.py
            groq_client_path = gen_dir / 'groq_client.py'
            spec = importlib.util.spec_from_file_location("groq_client_dynamic", str(groq_client_path))
            _client_module = importlib.util.module_from_spec(spec)
            sys.modules['groq_client_dynamic'] = _client_module
            spec.loader.exec_module(_client_module)
            
        elif USE_AZURE:
            # Load openai_client.py
            openai_client_path = gen_dir / 'openai_client.py'
            spec = importlib.util.spec_from_file_location("openai_client_dynamic", str(openai_client_path))
            _client_module = importlib.util.module_from_spec(spec)
            sys.modules['openai_client_dynamic'] = _client_module
            spec.loader.exec_module(_client_module)
        else:
            # No client configured - return None
            _client_module = None
            
        return _client_module
        
    except Exception as e:
        print(f"Error loading client module: {e}")
        _client_module = None
        return None


# Define functions that delegate to the loaded module
def create_client():
    """Create LLM client (Groq or Azure OpenAI)."""
    module = _load_client_module()
    if module is None:
        raise RuntimeError(
            "No LLM API configured. Please set one of:\n"
            "  - GROQ_API_KEY for Groq (recommended, free tier available)\n"
            "  - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT for Azure OpenAI\n\n"
            "Quick setup with Groq:\n"
            "  1. Get API key from https://console.groq.com/keys\n"
            "  2. Set GROQ_API_KEY in .env file\n"
            "  3. Run: bash setup_groq.sh\n"
        )
    return module.create_client()


def get_deployment_name():
    """Get deployment/model name."""
    module = _load_client_module()
    if module is None:
        raise RuntimeError("No LLM API configured")
    return module.get_deployment_name()


def create_chat_completion(client, deployment: str, messages: List[Dict[str, str]], 
                          max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
    """Create chat completion."""
    module = _load_client_module()
    if module is None:
        raise RuntimeError("No LLM API configured")
    return module.create_chat_completion(client, deployment, messages, max_tokens, temperature)


def validate_client_configuration() -> bool:
    """Validate client configuration."""
    module = _load_client_module()
    if module is None:
        return False
    return module.validate_client_configuration()


def estimate_token_count(text: str) -> int:
    """Estimate token count."""
    module = _load_client_module()
    if module is None:
        return len(text) // 4  # Fallback estimation
    if hasattr(module, 'estimate_token_count'):
        return module.estimate_token_count(text)
    return len(text) // 4


def prepare_messages_for_generation(system_prompt: str, user_prompt: str, 
                                   max_total_tokens: int = 32000) -> List[Dict[str, str]]:
    """Prepare messages for generation."""
    module = _load_client_module()
    if module is None:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    if hasattr(module, 'prepare_messages_for_generation'):
        return module.prepare_messages_for_generation(system_prompt, user_prompt, max_total_tokens)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_openai_client():
    """Get OpenAI-compatible client (alias for create_client)."""
    return create_client()


# Exception classes - try to import from module, or define fallbacks
try:
    module = _load_client_module()
    if module and hasattr(module, 'RateLimitError'):
        RateLimitError = module.RateLimitError
        APIError = module.APIError
        APITimeoutError = module.APITimeoutError
    else:
        raise AttributeError("Module doesn't have exception classes")
except:
    # Fallback exception classes
    class RateLimitError(Exception):
        pass
    
    class APIError(Exception):
        pass
    
    class APITimeoutError(Exception):
        pass


# Export all functions with the same interface
__all__ = [
    'create_client',
    'get_deployment_name', 
    'create_chat_completion',
    'validate_client_configuration',
    'estimate_token_count',
    'prepare_messages_for_generation',
    'get_openai_client',
    'RateLimitError',
    'APIError',
    'APITimeoutError',
    'USE_GROQ',
    'USE_AZURE'
]
