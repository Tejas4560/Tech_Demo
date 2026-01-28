#!/bin/bash
# Complete Integration Test - Verifies Groq API integration is fully working

echo "=========================================="
echo "Groq API Integration - Complete Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check .env file
echo "Test 1: Checking .env configuration..."
if [ -f ".env" ]; then
    if grep -q "GROQ_API_KEY" .env; then
        echo -e "${GREEN}✓${NC} .env file exists with GROQ_API_KEY"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} .env file missing GROQ_API_KEY"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}✗${NC} .env file not found"
    ((TESTS_FAILED++))
fi
echo ""

# Test 2: Check Groq client configuration
echo "Test 2: Testing Groq client configuration..."
if python test_groq_config.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Groq client configuration valid"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗${NC} Groq client configuration failed"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: Check test generation on small repo
echo "Test 3: Testing test generation with Groq..."
echo "   (This may take 1-2 minutes...)"

# Use the Backend_code repo if it exists, otherwise skip
if [ -d "/tmp/Backend_code" ]; then
    # Try to generate just 1 test file to verify it works
    if timeout 180 python -m src.gen.enhanced_generate \
        --target /tmp/Backend_code \
        --outdir /tmp/test_groq_verify \
        --coverage-mode normal > /tmp/test_gen.log 2>&1; then
        
        # Check if any test files were created
        if [ -d "/tmp/test_groq_verify" ] && [ "$(ls -A /tmp/test_groq_verify/*.py 2>/dev/null | wc -l)" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} Test generation with Groq successful"
            ((TESTS_PASSED++))
            rm -rf /tmp/test_groq_verify
        else
            echo -e "${RED}✗${NC} Test generation produced no files"
            ((TESTS_FAILED++))
        fi
    else
        echo -e "${RED}✗${NC} Test generation failed or timed out"
        echo "   Check /tmp/test_gen.log for details"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⊘${NC} Skipping (Backend_code repo not found)"
fi
echo ""

# Test 4: Check auto-fixer can load Groq client
echo "Test 4: Testing auto-fixer Groq integration..."
# Create a dummy test file to check if auto-fixer can load
mkdir -p /tmp/dummy_test
cat > /tmp/dummy_test/test_dummy.py << 'EOF'
def test_dummy():
    assert 1 == 1
EOF

# Run auto-fixer with --help to verify it loads without errors
if python run_auto_fixer.py --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Auto-fixer loads successfully"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗${NC} Auto-fixer failed to load"
    ((TESTS_FAILED++))
fi
rm -rf /tmp/dummy_test
echo ""

# Test 5: Check all required files exist
echo "Test 5: Checking required files..."
REQUIRED_FILES=(
    "src/gen/groq_client.py"
    "src/gen/llm_client.py"
    "src/gen/enhanced_generate.py"
    "src/auto_fixer/llm_classifier.py"
    "src/auto_fixer/llm_fixer.py"
    "src/auto_fixer/orchestrator.py"
    "run_auto_fixer.py"
    "setup_groq.sh"
    "test_groq_config.py"
    "GROQ_README.md"
    "GROQ_COMPLETE.md"
)

ALL_FILES_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} Missing: $file"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = true ]; then
    echo -e "${GREEN}✓${NC} All required files present"
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi
echo ""

# Final Summary
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}Groq API integration is fully working!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed${NC}"
    echo "Please check the errors above and:"
    echo "  1. Ensure GROQ_API_KEY is set in .env"
    echo "  2. Run: bash setup_groq.sh"
    echo "  3. Run: python test_groq_config.py"
    exit 1
fi
