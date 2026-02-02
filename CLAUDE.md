# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI TestGen is an intelligent test generation and coverage gating pipeline that:
- Analyzes Python code using AST parsing (tree-sitter)
- Generates meaningful tests using LLM integration (OpenAI, Groq, Ollama)
- Automatically detects and fixes failing tests (up to 3 iterations)
- Measures code coverage and enforces thresholds (default: 90%)
- Integrates with SonarQube for enterprise quality gates
- Posts results to GitHub PRs with sticky comments

## Common Commands

### Test Generation
```bash
# Generate tests for a target repository
python -m src.gen --target /path/to/code --outdir tests/generated --force

# Gap-focused mode (only generate for uncovered code)
python -m src.gen --target /path/to/code --coverage-mode gap-focused
```

### Running Tests
```bash
# Run tests with coverage
pytest tests/ --cov=/path/to/code --cov-report=xml --cov-report=html --json-report

# Run specific test file
pytest tests/test_file.py -v

# Run with markers
pytest -m "use_parameterize or io_tests" tests/
```

### Auto-Fix Failing Tests
```bash
python run_auto_fixer.py --test-dir tests --project-root . --max-iterations 3

# With custom pytest args
python run_auto_fixer.py --test-dir tests/generated --pytest-args "-v,-x,-k,test_user"
```

### Other Utilities
```bash
# Detect existing tests in a repository
python src/detect_manual_tests.py /path/to/repo

# Analyze coverage gaps
python src/coverage_gap_analyzer.py --target /path/to/code --current-dir . --output coverage_gaps.json

# Run complete pipeline
bash pipeline_runner.sh
```

## Architecture

### Pipeline Flow
```
Clone Repo → Detect Tests → Run Tests → Check Coverage
    ↓ (if below threshold)
Analyze Code (AST) → Framework Detection → Generate Tests (LLM)
    ↓
Run Combined Tests → Auto-Fix Failures → Measure Coverage
    ↓
Upload to SonarQube → Generate Summary → Post PR Comment
```

### Key Modules

**src/gen/** - AI test generation
- `__main__.py` - CLI entry point (`python -m src.gen`)
- `enhanced_generate.py` - Main universal test generator
- `openai_client.py`, `groq_client.py`, `ollama_client.py` - LLM integrations

**src/auto_fixer/** - Automatic test fixing
- `orchestrator.py` - Main fix coordinator (runs up to 3 iterations)
- `failure_parser.py` - Parse pytest JSON output
- `llm_classifier.py` - LLM-powered failure classification
- `ast_patcher.py` - Apply AST-based code patches

**src/framework_handlers/** - Framework-specific logic
- `manager.py` - Framework detection & routing
- `fastapi_handler.py`, `flask_handler.py`, `django_handler.py` - Framework patterns
- `universal_handler.py` - Fallback for unknown projects

**src/** - Core utilities
- `analyzer.py` - Universal AST code analysis
- `coverage_gap_analyzer.py` - Identifies uncovered code sections
- `detect_manual_tests.py` - Test discovery in target repos

## Environment Variables

**Required for LLM (one of these):**
- `GROQ_API_KEY` - Groq API key
- `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT`
- `OLLAMA_HOST` - Local Ollama server URL

**Optional:**
- `MIN_COVERAGE_THRESHOLD` - Default 90%
- `SONAR_HOST_URL`, `SONAR_TOKEN` - SonarQube integration
- `GIT_PUSH_TOKEN` - GitHub token for auto-commits
- `TESTGEN_DEBUG` - Enable debug output

## Output Files

- `coverage.xml` - Cobertura format coverage
- `htmlcov/` - Interactive HTML coverage report
- `test-results.xml` - JUnit format test results
- `summary.json` - Comprehensive pipeline metrics
- `ast_full_analysis.json` - Full code AST analysis
- `coverage_gaps.json` - Uncovered code analysis
- `auto_fixer_report.json` - Fix attempt details

## pytest Configuration

The project uses `pytest.ini` with:
- `asyncio_mode = auto` - Async test support
- Branch coverage tracking enabled
- Custom markers: `use_parameterize`, `io_tests`, `use_fixtures`, `skipped_and_xfailing_tests`

## CI/CD

GitHub Actions workflow (`.github/workflows/ai-test-pipeline.yml`) supports:
- Manual dispatch with repo URL, branch, coverage threshold
- Pull request triggers
- Reusable workflow (`workflow_call`) for import by other repos

Workflow outputs: `generated_tests_count`, `coverage_before`, `coverage_after`, `coverage_delta`, `tests_passed`, `tests_failed`, `pipeline_status`

## Reusable Workflow Integration

This pipeline is designed to be used across multiple Python projects via GitHub's reusable workflow feature.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  YOUR PYTHON PROJECT REPO (e.g., my-flask-app)                  │
│                                                                 │
│  .github/workflows/ai-testgen.yml  ◄── Template you add        │
│                                                                 │
│  on:                                                            │
│    push:                                                        │
│      branches: [main]                                           │
│                                                                 │
│  jobs:                                                          │
│    ai-tests:                                                    │
│      uses: Tejas4560/Tech_Demo/.../ai-test-pipeline.yml@TEST5   │
│            ▲                                                    │
└────────────│────────────────────────────────────────────────────┘
             │
             │ references (workflow_call)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  TECH_DEMO REPO (Main Pipeline)                                 │
│                                                                 │
│  .github/workflows/ai-test-pipeline.yml                         │
│                                                                 │
│  - Clones your repo                                             │
│  - Analyzes code (AST)                                          │
│  - Generates tests (LLM)                                        │
│  - Runs tests + coverage                                        │
│  - Auto-fixes failures                                          │
│  - Posts results to PR                                          │
└─────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **You push code** to your Python project repo
2. **Template triggers** (`ai-testgen.yml` in your repo)
3. **Calls the main pipeline** via `workflow_call`
4. **Pipeline runs**: analyzes code, generates tests, measures coverage
5. **Results posted** back to your repo (PR comments, coverage reports)

### Template Workflow for Your Python Projects

Add this file to any Python project to enable automatic test generation:

**`.github/workflows/ai-testgen.yml`**
```yaml
name: AI Test Generation

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  ai-tests:
    uses: Tejas4560/Tech_Demo/.github/workflows/ai-test-pipeline.yml@TEST5
    with:
      min_coverage: 85
    secrets:
      GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

### Minimal Project Structure Required

```
your-python-repo/
├── .github/
│   └── workflows/
│       └── ai-testgen.yml   ← Only this file needed
├── src/
│   └── your_code.py
└── requirements.txt
```

The heavy lifting happens in the main `Tech_Demo` pipeline - consumer repos just reference it.

## GitHub Pages Coverage Reports

The pipeline can automatically deploy interactive HTML coverage reports to GitHub Pages, allowing developers to view detailed coverage information without downloading artifacts.

### How It Works

1. Pipeline generates HTML coverage report (`htmlcov/`)
2. Report is deployed to `gh-pages` branch under `coverage/<run_number>/`
3. Live URL is included in:
   - Job Summary (Actions tab)
   - PR Comments (sticky comment)
   - Workflow outputs (`coverage_report_url`)

### Enabling GitHub Pages

**For consumer repos using this pipeline:**

1. Go to repo Settings → Pages
2. Set Source to "Deploy from a branch"
3. Select `gh-pages` branch, `/ (root)` folder
4. Save

### URL Format

```
https://<owner>.github.io/<repo>/coverage/<run_number>/
```

Example: `https://tejas4560.github.io/my-flask-app/coverage/42/`

### Disabling Pages Deployment

In your `ai-testgen.yml`:

```yaml
jobs:
  ai-tests:
    uses: Tejas4560/Tech_Demo/.github/workflows/ai-test-pipeline.yml@TEST5
    with:
      min_coverage: 85
      deploy_pages: 'false'  # Disable GitHub Pages deployment
    secrets:
      GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```
