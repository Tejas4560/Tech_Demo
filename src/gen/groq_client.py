# src/gen/groq_client.py
"""
Groq API client adapter - drop-in replacement for Azure OpenAI client.
Provides the same interface as openai_client.py but uses Groq API.
"""
import os
import time
from typing import Dict, List, Optional

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("WARNING: groq package not installed. Install with: pip install groq")

# Inline env functions to avoid relative import issues
ENABLE_DEBUG = os.getenv("TESTGEN_DEBUG", "0").lower() in ("1", "true", "yes")

def get_any_env(*names: str) -> str:
    """Get environment variable from multiple possible names. Raises RuntimeError if none found."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    raise RuntimeError(f"Missing required environment variable. Tried: {', '.join(names)}")

def get_optional_env(*names: str, default: str = "") -> str:
    """Get environment variable from multiple possible names with default fallback."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


class GroqAPIError(Exception):
    """Base exception for Groq API errors."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(GroqAPIError):
    """Rate limit exceeded error."""
    pass


class APITimeoutError(GroqAPIError):
    """API timeout error."""
    pass


class APIError(GroqAPIError):
    """General API error."""
    pass


def create_client() -> Groq:
    """Create Groq client with comprehensive configuration."""
    if not GROQ_AVAILABLE:
        raise RuntimeError("groq package not installed. Install with: pip install groq")
    
    try:
        api_key = get_any_env("GROQ_API_KEY", "GROQ_KEY")
        client = Groq(api_key=api_key)

        if ENABLE_DEBUG:
            print(f"✅ Groq client created successfully")

        return client

    except Exception as e:
        raise RuntimeError(f"Failed to create Groq client: {e}")


def get_openai_client() -> Groq:
    """Get configured Groq client (alias for create_client for compatibility)."""
    return create_client()


def get_deployment_name() -> str:
    """
    Get the model name for Groq.
    Defaults to llama-3.3-70b-versatile (best for code generation).
    """
    return get_optional_env(
        "GROQ_MODEL", 
        "GROQ_DEPLOYMENT",
        default="llama-3.3-70b-versatile"
    )


def create_chat_completion(client: Groq, deployment: str, messages: List[Dict[str, str]], 
                          max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
    """
    Create chat completion with robust error handling and retry logic.
    
    Args:
        client: Groq client
        deployment: Model name (e.g., "llama-3.3-70b-versatile")
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens to generate (None for model default)
        temperature: Sampling temperature (0.0 to 2.0, default 1.0)
    
    Returns:
        Generated content as string
    
    Raises:
        RuntimeError: If all retry attempts fail
    """
    
    retry_delays = [1, 3, 6]  # Progressive backoff
    last_error = None
    
    for attempt, delay in enumerate(retry_delays + [0]):  # Extra attempt without delay
        try:
            if ENABLE_DEBUG:
                print(f"🔄 Attempt {attempt + 1}: Creating chat completion with Groq...")
            
            # Apply delay for retries
            if delay > 0:
                time.sleep(delay)
            
            # Prepare request parameters
            request_params = {
                "model": deployment,
                "messages": messages,
            }
            
            # Add optional parameters
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            if temperature is not None:
                request_params["temperature"] = temperature
            else:
                request_params["temperature"] = 0.7  # Good default for code generation
            
            if ENABLE_DEBUG:
                print(f"📝 Using model: {deployment}")
                print(f"🌡️  Temperature: {request_params.get('temperature', 'default')}")
                if max_tokens:
                    print(f"📊 Max tokens: {max_tokens}")
            
            # Make API call
            response = client.chat.completions.create(**request_params)
            
            # Extract content from response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    if ENABLE_DEBUG:
                        print(f"✅ Successfully generated {len(content)} characters")
                    return content
                else:
                    raise RuntimeError("Empty response content from Groq API")
            else:
                raise RuntimeError("No choices returned from Groq API")
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit errors
            if "rate" in error_str and "limit" in error_str:
                last_error = f"Rate limit exceeded: {e}"
                if ENABLE_DEBUG:
                    print(f"⏳ Rate limit hit on attempt {attempt + 1}, retrying...")
                continue
            
            # Check for timeout errors
            elif "timeout" in error_str:
                last_error = f"API timeout: {e}"
                if ENABLE_DEBUG:
                    print(f"⏱️  Timeout on attempt {attempt + 1}, retrying...")
                continue
            
            # Check for authentication errors (don't retry)
            elif "auth" in error_str or "api key" in error_str or "401" in error_str:
                raise RuntimeError(f"Authentication error: {e}. Check your GROQ_API_KEY.")
            
            # Check for invalid request errors (don't retry)
            elif "400" in error_str or "invalid" in error_str:
                raise RuntimeError(f"Invalid request: {e}")
            
            # Generic error - retry
            else:
                last_error = f"Unexpected error: {e}"
                if ENABLE_DEBUG:
                    print(f"❌ Error on attempt {attempt + 1}: {e}")
                continue
    
    # All attempts failed
    raise RuntimeError(f"Chat completion failed after {len(retry_delays) + 1} attempts. Last error: {last_error}")


def validate_client_configuration() -> bool:
    """
    Validate that the Groq client can be configured and used.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Test client creation
        client = create_client()
        deployment = get_deployment_name()
        
        if ENABLE_DEBUG:
            print(f"✅ Groq client configuration validation passed")
            print(f"📦 Model: {deployment}")
        
        return True
        
    except Exception as e:
        print(f"❌ Groq client configuration validation failed: {e}")
        print(f"\n💡 Make sure you have:")
        print(f"   1. Installed groq: pip install groq")
        print(f"   2. Set GROQ_API_KEY environment variable")
        print(f"   3. (Optional) Set GROQ_MODEL for custom model selection")
        return False


def estimate_token_count(text: str) -> int:
    """
    Rough estimation of token count for text.
    Uses simple heuristic: ~4 characters per token on average.
    """
    return len(text) // 4


def prepare_messages_for_generation(system_prompt: str, user_prompt: str, 
                                  max_total_tokens: int = 32000) -> List[Dict[str, str]]:
    """
    Prepare and validate messages for generation, ensuring they fit within token limits.
    
    Args:
        system_prompt: System message content
        user_prompt: User message content  
        max_total_tokens: Maximum total tokens for the request
    
    Returns:
        List of properly formatted messages
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Estimate token usage
    total_tokens = sum(estimate_token_count(msg["content"]) for msg in messages)
    
    if total_tokens > max_total_tokens:
        # Truncate user prompt to fit within limits
        system_tokens = estimate_token_count(system_prompt)
        available_for_user = max_total_tokens - system_tokens - 1000  # Reserve for response
        
        if available_for_user > 0:
            max_user_chars = available_for_user * 4  # Rough conversion back to characters
            if len(user_prompt) > max_user_chars:
                user_prompt = user_prompt[:max_user_chars] + "\n... (truncated for length)"
                messages[1]["content"] = user_prompt
                
                if ENABLE_DEBUG:
                    print(f"✂️  Truncated user prompt to {len(user_prompt)} characters")
        else:
            raise RuntimeError("System prompt too long - cannot fit user content")
    
    return messages


# Legacy function aliases for backward compatibility
client = create_client
deployment_name = get_deployment_name  
chat_completion_create = lambda cli, dep, msgs: create_chat_completion(cli, dep, msgs)

# Export exception classes for error handling
__all__ = ['create_client', 'get_deployment_name', 'create_chat_completion', 
           'validate_client_configuration', 'RateLimitError', 'APIError', 'APITimeoutError',
           'get_openai_client']
