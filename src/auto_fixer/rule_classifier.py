"""
Rule-Based Classifier

Classifies test failures as "test_mistake", "app_environment_error", or "unknown" based on patterns.
"""

import re
from typing import Literal
from .failure_parser import TestFailure


ClassificationType = Literal["test_mistake", "app_environment_error", "unknown"]


class RuleBasedClassifier:
    """
    Classifies test failures using pattern-matching rules.

    Returns:
    - "test_mistake" for common test-writing errors
    - "app_environment_error" for application code that depends on missing files/resources
    - "unknown" otherwise (could be code bug or complex test mistake)
    """

    # Patterns that indicate APPLICATION ENVIRONMENT errors
    # These are NOT test mistakes - the app code itself requires external resources
    # that don't exist in CI. These CANNOT be fixed by modifying tests.
    APP_ENVIRONMENT_PATTERNS = [
        # Missing data files (app code opens files that don't exist)
        (r"FileNotFoundError.*data/", "App requires data files not in CI"),
        (r"FileNotFoundError.*\.json", "App requires JSON data files"),
        (r"FileNotFoundError.*\.csv", "App requires CSV data files"),
        (r"FileNotFoundError.*\.yaml", "App requires YAML config files"),
        (r"FileNotFoundError.*\.yml", "App requires YAML config files"),
        (r"FileNotFoundError.*config", "App requires config files"),
        (r"No such file or directory.*data/", "App requires data directory"),

        # Database connection errors (app expects database)
        (r"OperationalError.*unable to open database", "App requires database"),
        (r"OperationalError.*could not connect", "App requires database connection"),
        (r"ConnectionRefusedError.*database", "App requires database connection"),
        (r"psycopg2\.OperationalError", "App requires PostgreSQL"),
        (r"pymysql\.err\.OperationalError", "App requires MySQL"),
        (r"sqlite3\.OperationalError", "App requires SQLite database file"),

        # External service dependencies
        (r"ConnectionRefusedError.*localhost", "App requires local service"),
        (r"ConnectionError.*refused", "App requires external service"),
        (r"requests\.exceptions\.ConnectionError", "App requires external API"),
        (r"urllib\.error\.URLError", "App requires network access"),

        # Environment variables (app reads required env vars)
        (r"KeyError.*os\.environ", "App requires environment variables"),
        (r"required environment variable", "App requires environment variables"),

        # Redis/Cache dependencies
        (r"redis\.exceptions\.ConnectionError", "App requires Redis"),
        (r"ConnectionRefusedError.*6379", "App requires Redis on default port"),

        # Message queue dependencies
        (r"pika\.exceptions\.AMQPConnectionError", "App requires RabbitMQ"),
        (r"kafka\.errors\.NoBrokersAvailable", "App requires Kafka"),
    ]

    # Patterns that indicate test mistakes
    TEST_MISTAKE_PATTERNS = [
        # Import errors in tests
        (r"ImportError|ModuleNotFoundError", "Missing import in test"),
        (r"cannot import name", "Wrong import in test"),

        # Fixture errors
        (r"fixture .* not found", "Missing or misspelled fixture"),
        (r"fixture .* doesn't exist", "Missing or misspelled fixture"),

        # AttributeError in test setup/assertions
        (r"AttributeError.*Mock|MagicMock", "Incorrect mock usage"),
        (r"AttributeError.*has no attribute", "Wrong attribute access in test"),

        # TypeError in test code
        (r"TypeError.*takes \d+ positional argument", "Wrong number of arguments in test"),
        (r"TypeError.*missing \d+ required positional argument", "Missing arguments in test"),
        (r"TypeError.*got an unexpected keyword argument", "Wrong keyword argument in test"),

        # NameError (undefined variable in test)
        (r"NameError.*name .* is not defined", "Undefined variable in test"),

        # Assertion errors with specific patterns
        (r"assert None", "Asserting on None (likely test setup issue)"),
        (r"AssertionError.*is not True", "Incorrect assertion pattern"),

        # Indentation errors in test
        (r"IndentationError", "Indentation error in test"),
        (r"SyntaxError", "Syntax error in test"),

        # Test configuration errors
        (r"pytest.*error|pytest.*failed", "Pytest configuration error"),

        # Database/ORM errors in test setup
        (r"DatabaseError.*no such table", "Database not set up in test"),
        (r"OperationalError.*no such table", "Database not set up in test"),

        # File not found in test fixtures (NOT app data files)
        (r"FileNotFoundError.*test.*fixture", "Missing test fixture file"),
        (r"FileNotFoundError.*conftest", "Missing conftest file"),

        # JSON decode errors (bad test data)
        (r"JSONDecodeError", "Invalid JSON in test data"),

        # Key errors (missing key in test data)
        (r"KeyError.*in test", "Missing key in test data"),

        # Client/request errors in tests
        (r"No route matches", "Incorrect route in test"),
        (r"404.*Not Found", "Wrong URL in test request"),

        # Async errors in tests
        (r"RuntimeError.*cannot be called from a running event loop", "Async setup issue in test"),
        (r"asyncio.*was never awaited", "Missing await in test"),
    ]

    # Patterns that suggest code bugs (not test mistakes)
    CODE_BUG_PATTERNS = [
        (r"ZeroDivisionError", "Code bug: division by zero"),
        (r"ValueError.*invalid literal", "Code bug: invalid value"),
        (r"IndexError.*out of range", "Code bug: index out of range"),
        (r"RecursionError", "Code bug: infinite recursion"),
    ]

    def __init__(self):
        pass

    def classify(self, failure: TestFailure) -> ClassificationType:
        """
        Classify a test failure.

        Args:
            failure: TestFailure object

        Returns:
            "test_mistake", "app_environment_error", or "unknown"
        """
        # Combine error message and traceback for analysis
        error_context = f"{failure.exception_type} {failure.error_message} {failure.traceback}"

        # FIRST: Check for app environment errors (cannot be fixed by modifying tests)
        # These indicate the APPLICATION CODE depends on external resources
        for pattern, description in self.APP_ENVIRONMENT_PATTERNS:
            if re.search(pattern, error_context, re.IGNORECASE):
                return "app_environment_error"

        # Check test mistake patterns
        for pattern, description in self.TEST_MISTAKE_PATTERNS:
            if re.search(pattern, error_context, re.IGNORECASE):
                return "test_mistake"

        # Check if it looks like a code bug
        for pattern, description in self.CODE_BUG_PATTERNS:
            if re.search(pattern, error_context, re.IGNORECASE):
                # Could be code bug - return unknown so LLM can decide
                return "unknown"

        # Additional heuristics based on traceback location
        if self._failure_in_test_file(failure):
            # If the error originates in the test file itself, more likely a test mistake
            if failure.exception_type in ["AttributeError", "TypeError", "NameError", "ImportError"]:
                return "test_mistake"

        # Default: unknown (let LLM decide)
        return "unknown"

    def _failure_in_test_file(self, failure: TestFailure) -> bool:
        """
        Check if the failure originated in the test file.

        Args:
            failure: TestFailure object

        Returns:
            True if failure is in test file
        """
        # Check if test file appears near the end of traceback
        traceback_lines = failure.traceback.split('\n')

        for line in reversed(traceback_lines[-10:]):  # Check last 10 lines
            if failure.test_file in line:
                return True

        return False

    def get_classification_reason(self, failure: TestFailure) -> str:
        """
        Get a human-readable reason for the classification.

        Args:
            failure: TestFailure object

        Returns:
            Reason string
        """
        error_context = f"{failure.exception_type} {failure.error_message} {failure.traceback}"

        # Find matching pattern - check app environment patterns first
        for pattern, description in self.APP_ENVIRONMENT_PATTERNS:
            if re.search(pattern, error_context, re.IGNORECASE):
                return f"APP ENV ERROR: {description}"

        for pattern, description in self.TEST_MISTAKE_PATTERNS:
            if re.search(pattern, error_context, re.IGNORECASE):
                return description

        for pattern, description in self.CODE_BUG_PATTERNS:
            if re.search(pattern, error_context, re.IGNORECASE):
                return description

        return "No specific pattern matched"
