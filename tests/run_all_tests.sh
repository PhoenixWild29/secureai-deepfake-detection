#!/bin/bash
# Run All Tests Script
# Executes all test suites and generates report

set -e

echo "🧪 Running SecureAI Guardian Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create test results directory
mkdir -p test_results

# Run tests
echo -e "${YELLOW}Running API endpoint tests...${NC}"
python -m pytest tests/test_api_endpoints.py -v --tb=short > test_results/api_tests.txt 2>&1
API_EXIT=$?

echo -e "${YELLOW}Running performance tests...${NC}"
python -m pytest tests/test_performance.py -v --tb=short > test_results/performance_tests.txt 2>&1
PERF_EXIT=$?

# Generate summary
echo ""
echo "========================================"
echo "Test Results Summary"
echo "========================================"

if [ $API_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ API Tests: PASSED${NC}"
else
    echo -e "${RED}❌ API Tests: FAILED${NC}"
fi

if [ $PERF_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ Performance Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Performance Tests: FAILED${NC}"
fi

# Overall status
if [ $API_EXIT -eq 0 ] && [ $PERF_EXIT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Check test_results/ for details.${NC}"
    exit 1
fi

