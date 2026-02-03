"""
LLM Fixer

Generates fixed versions of failing test functions.
"""

import os
import sys
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .failure_parser import TestFailure


class LLMFixer:
    """
    Uses LLM to generate fixed versions of failing tests.

    Only fixes test_mistake failures, not code bugs.
    """

    SYSTEM_PROMPT = """You are an expert Python test fixing assistant. Your job is to fix failing test code.

Given:
1. A failing test function
2. The error/traceback
3. Relevant source code being tested
4. Available pytest fixtures from conftest.py (if any)

Generate a fixed version of the test function that will pass.

Rules:
- Fix ONLY the test code, never modify source code
- Preserve the test's original intent and coverage goals
- Fix common issues: imports, fixtures, assertions, mocks, setup/teardown
- Ensure the fixed test is syntactically correct
- Return ONLY the complete fixed test function, no explanations
- Include all necessary imports if they're missing
- Use proper pytest conventions
- USE EXISTING FIXTURES from conftest.py when available instead of creating new mocks

Return the complete fixed test function code."""

    def __init__(self, verbose: bool = False, test_directory: str = "tests"):
        """Initialize LLM fixer."""
        self.verbose = verbose
        self.test_directory = test_directory
        self.client = None
        self.using_ollama = False
        self._conftest_cache = {}  # Cache conftest.py contents

        # Check if Ollama should be used (local LLM)
        # Only check OLLAMA_MODEL for LLM provider (OLLAMA_HOST is for embeddings)
        ollama_model = os.getenv("OLLAMA_MODEL", "").strip()
        if ollama_model:
            try:
                # Load Ollama client dynamically
                import importlib.util
                from pathlib import Path

                current_file = Path(__file__).resolve()
                ollama_client_path = current_file.parent.parent / 'gen' / 'ollama_client.py'

                spec = importlib.util.spec_from_file_location(
                    "ollama_client_llm_fixer",
                    str(ollama_client_path)
                )
                ollama_module = importlib.util.module_from_spec(spec)
                sys.modules['ollama_client_llm_fixer'] = ollama_module
                spec.loader.exec_module(ollama_module)

                self.client = ollama_module.get_ollama_llm_client()
                self.using_ollama = True
                if verbose:
                    print(f"Using Ollama LLM for fixing: {os.getenv('OLLAMA_MODEL', 'deepseek-r1:latest')}")
            except Exception as e:
                if verbose:
                    print(f"Could not initialize Ollama LLM client: {e}")
                    print(f"Falling back to Azure OpenAI")

        # Fall back to unified LLM client (Groq or Azure OpenAI) if Ollama not configured or failed
        if self.client is None:
            try:
                # Load unified LLM client dynamically (supports both Groq and Azure OpenAI)
                import importlib.util
                from pathlib import Path

                current_file = Path(__file__).resolve()
                llm_client_path = current_file.parent.parent / 'gen' / 'llm_client.py'

                spec = importlib.util.spec_from_file_location(
                    "llm_client_llm_fixer",
                    str(llm_client_path)
                )
                llm_module = importlib.util.module_from_spec(spec)
                sys.modules['llm_client_llm_fixer'] = llm_module
                spec.loader.exec_module(llm_module)

                self.client = llm_module.get_openai_client()
                if verbose:
                    if llm_module.USE_GROQ:
                        print(f"🚀 Using Groq API for fixing")
                    elif llm_module.USE_AZURE:
                        print(f"☁️  Using Azure OpenAI for fixing")
            except Exception as e:
                print(f"Warning: Could not initialize LLM client: {e}")
                self.client = None

    def fix_test(
        self,
        failure: TestFailure,
        test_code: str,
        source_code: str,
        previous_fix_attempt: Optional[str] = None,
        previous_failure_output: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a fixed version of a failing test.

        Args:
            failure: TestFailure object
            test_code: Original failing test code
            source_code: Relevant source code being tested
            previous_fix_attempt: Previous fix that failed (for retry)
            previous_failure_output: Pytest output from previous failed fix attempt

        Returns:
            Fixed test code or None if fix failed
        """
        if not self.client:
            print("Error: OpenAI client not available")
            return None

        # Build prompt
        user_prompt = self._build_prompt(
            failure,
            test_code,
            source_code,
            previous_fix_attempt,
            previous_failure_output
        )

        # DEBUG: Show prompt size
        prompt_lines = user_prompt.count('\n')
        prompt_chars = len(user_prompt)
        estimated_tokens = prompt_chars // 4  # Rough estimate: 4 chars per token
        print(f"Prompt size: {prompt_lines} lines, {prompt_chars} chars (~{estimated_tokens} tokens)")

        try:
            # Call LLM
            # Get model name based on provider
            if self.using_ollama:
                model_name = os.getenv("OLLAMA_MODEL", "deepseek-r1:latest")
            else:
                # Check if using Groq or Azure OpenAI
                groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY")
                azure_key = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
                
                if groq_key and not azure_key:
                    # Using Groq
                    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                else:
                    # Using Azure OpenAI
                    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
                    if not model_name:
                        raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable not set")

            # Build request parameters
            request_params = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                # NO max_completion_tokens limit - let reasoning models use what they need
            }

            # Only set temperature if environment variable is set
            # Some Azure deployments don't support custom temperature
            temp = os.getenv("AUTOFIXER_LLM_TEMPERATURE")
            if temp is not None:
                request_params["temperature"] = float(temp)

            response = self.client.chat.completions.create(**request_params)


            # Extract fixed code
            content = response.choices[0].message.content.strip()

            # Clean up markdown code blocks if present
            fixed_code = self._extract_code(content)

            return fixed_code

        except Exception as e:
            print(f"Error generating fix: {e}")
            return None

    def _build_prompt(
        self,
        failure: TestFailure,
        test_code: str,
        source_code: str,
        previous_fix_attempt: Optional[str],
        previous_failure_output: Optional[str] = None
    ) -> str:
        """
        Build the prompt for test fixing with learning from previous failures.

        Args:
            failure: TestFailure object
            test_code: Original failing test code
            source_code: Relevant source code
            previous_fix_attempt: Previous failed fix
            previous_failure_output: Pytest output from previous failed fix

        Returns:
            Formatted prompt
        """
        # NO truncation - send all source code (embeddings already filtered to relevant code)
        # Modern LLMs can handle large contexts (deepseek-r1: 64k, gpt-4o-mini: 128k)
        source_code_display = source_code

        # Get conftest.py context (fixtures)
        conftest_context = self._get_conftest_context(failure.test_file)

        # ============================================================
        # DEBUG SAVING CODE - saves prompt components for analysis
        # ============================================================
        import datetime
        import os

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = "debug_prompts"
        os.makedirs(debug_dir, exist_ok=True)

        # Save each component to separate files
        with open(f"{debug_dir}/{timestamp}_test_code.py", "w") as f:
            f.write(test_code)

        with open(f"{debug_dir}/{timestamp}_source_code.py", "w") as f:
            f.write(source_code_display)

        with open(f"{debug_dir}/{timestamp}_traceback.txt", "w") as f:
            f.write(failure.traceback)

        with open(f"{debug_dir}/{timestamp}_conftest.py", "w") as f:
            f.write(conftest_context if conftest_context else "# No conftest.py found")

        # Save summary
        with open(f"{debug_dir}/{timestamp}_summary.txt", "w") as f:
            f.write(f"PROMPT SIZE BREAKDOWN\n")
            f.write(f"=" * 70 + "\n\n")
            f.write(f"Test: {failure.test_file}::{failure.test_name}\n\n")
            f.write(f"Test code:      {len(test_code):,} chars, {test_code.count(chr(10))} lines\n")
            f.write(f"Source code:    {len(source_code_display):,} chars, {source_code_display.count(chr(10))} lines\n")
            f.write(f"Traceback:      {len(failure.traceback):,} chars, {failure.traceback.count(chr(10))} lines\n")
            f.write(f"Conftest:       {len(conftest_context):,} chars, {conftest_context.count(chr(10)) if conftest_context else 0} lines\n")
        print(f"Debug saved: {debug_dir}/{timestamp}_*.txt")
        # ============================================================
        prompt = f"""# Fix This Failing Test

## Original Test Code
```python
{test_code}
```

## Error Information
**Exception:** {failure.exception_type}
**Message:** {failure.error_message}

## Traceback
```
{failure.traceback}
```

## Source Code Being Tested
```python
{source_code_display}
```
"""

        # Add conftest.py context if available
        if conftest_context:
            prompt += f"""
## Available Pytest Fixtures (from conftest.py)
These fixtures are available to use in your fix. USE THEM instead of creating new mocks when appropriate:
```python
{conftest_context}
```
"""

        if previous_fix_attempt and previous_failure_output:
            prompt += f"""
## Previous Fix Attempt (Failed)
```python
{previous_fix_attempt}
```

## Why the Previous Fix Failed
When we ran pytest on the above fix, it still failed with this output:

```
{previous_failure_output[:2000]}
```

**IMPORTANT:** Analyze WHY this fix failed:
- Is the API key dependency still not being handled?
- Are there other dependencies or fixtures that need to be mocked?
- Is the mock setup incorrect?
- Are there missing imports?
- Does the test need different assertions?

Generate a NEW fix that addresses these specific failure reasons. Don't repeat the same approach!
"""
        elif previous_fix_attempt:
            prompt += f"""
## Previous Fix Attempt (Failed)
```python
{previous_fix_attempt}
```

The previous fix attempt failed. Try a different approach.
"""

        prompt += """
## Task
Generate a fixed version of the test function that will pass.

**Common patterns to fix:**
1. **Use available fixtures from conftest.py:**
   - If a fixture provides what you need, ADD IT AS A PARAMETER to the test function
   - Example: `def test_something(client, sample_data):` uses fixtures named `client` and `sample_data`
   - DO NOT recreate what fixtures already provide

2. **Missing API key handling:**
   - Mock the `verify_api_key` dependency
   - Or set `REQUIRE_API_KEY=false` in environment
   - Example: `monkeypatch.setenv("REQUIRE_API_KEY", "false")`

3. **Missing fixture mocking:**
   - Use `monkeypatch.setattr()` to mock required attributes
   - Use `@patch()` decorator for external dependencies
   - Mock database connections, external APIs, etc.

4. **Incorrect imports:**
   - Ensure all required imports are present
   - Use correct module paths

5. **Wrong test setup:**
   - Initialize required fixtures properly
   - Set up test data correctly
   - Clean up after test if needed

6. **Assertion errors:**
   - Check the actual return type and value from the source code
   - Ensure assertions match the actual behavior

Return ONLY the complete fixed test function code (include decorators, docstring, everything).
"""

        return prompt

    def _extract_code(self, content: str) -> str:
        """
        Extract Python code from LLM response.

        Args:
            content: LLM response content

        Returns:
            Extracted code
        """
        # Remove markdown code blocks
        if "```python" in content:
            parts = content.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                return code.strip()

        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 3:
                code = parts[1]
                return code.strip()

        # If no code blocks, return as-is
        return content.strip()

    def _get_conftest_context(self, test_file_path: str) -> str:
        """
        Get conftest.py content for the test file's directory and parent directories.

        This provides the LLM with available fixtures that can be used in the fix.

        Args:
            test_file_path: Path to the failing test file

        Returns:
            Combined conftest.py content or empty string
        """
        from pathlib import Path

        test_path = Path(test_file_path).resolve()
        test_dir = test_path.parent

        conftest_contents = []
        current_dir = test_dir

        # Look for conftest.py in test directory and parents (up to 3 levels)
        for _ in range(4):
            conftest_path = current_dir / "conftest.py"

            # Check cache first
            cache_key = str(conftest_path)
            if cache_key in self._conftest_cache:
                content = self._conftest_cache[cache_key]
                if content:
                    conftest_contents.append(f"# From {conftest_path}\n{content}")
            elif conftest_path.exists():
                try:
                    with open(conftest_path, 'r') as f:
                        content = f.read()
                    self._conftest_cache[cache_key] = content
                    if content.strip():
                        conftest_contents.append(f"# From {conftest_path}\n{content}")
                except Exception as e:
                    if self.verbose:
                        print(f"Could not read {conftest_path}: {e}")
                    self._conftest_cache[cache_key] = ""
            else:
                self._conftest_cache[cache_key] = ""

            # Move to parent directory
            parent = current_dir.parent
            if parent == current_dir:
                break
            current_dir = parent

        if conftest_contents:
            return "\n\n".join(reversed(conftest_contents))  # Parent conftest first
        return ""

    def fix_test_full_file(
        self,
        failure: TestFailure,
        full_test_file_content: str,
        source_code: str
    ) -> Optional[str]:
        """
        Generate a fixed version of the entire test file.

        Useful when the fix requires changes to imports or setup.

        Args:
            failure: TestFailure object
            full_test_file_content: Complete test file content
            source_code: Relevant source code

        Returns:
            Fixed full test file or None
        """
        if not self.client:
            return None

        prompt = f"""# Fix This Test File

## Complete Test File
```python
{full_test_file_content}
```

## Failing Test
**Test Name:** {failure.test_name}
**Error:** {failure.exception_type}: {failure.error_message}

## Traceback
```
{failure.traceback}
```

## Source Code
```python
{source_code}
```

## Task
Fix the failing test `{failure.test_name}` in this test file.
You may need to fix imports, fixtures, or the test function itself.

Return the COMPLETE fixed test file."""

        try:
            # Get model name based on provider
            if self.using_ollama:
                model_name = os.getenv("OLLAMA_MODEL", "deepseek-r1:latest")
            else:
                # Azure OpenAI
                model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
                if not model_name:
                    raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable not set")

            # Build request parameters
            request_params = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                # NO max_completion_tokens limit - let reasoning models use what they need
            }

            # Only set temperature if environment variable is set
            # Some Azure deployments don't support custom temperature
            temp = os.getenv("AUTOFIXER_LLM_TEMPERATURE")
            if temp is not None:
                request_params["temperature"] = float(temp)

            response = self.client.chat.completions.create(**request_params)

            content = response.choices[0].message.content.strip()
            return self._extract_code(content)

        except Exception as e:
            print(f"Error generating full file fix: {e}")
            return None