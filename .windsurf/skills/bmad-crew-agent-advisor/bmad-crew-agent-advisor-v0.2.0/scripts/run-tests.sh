#!/bin/bash
# Test Runner for BMAD Crew Advisor v0.2.0
# Runs validation tests for the enhanced advisor

set -e

echo "🛡️ BMAD Crew Advisor v0.2.0 Test Runner"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0
WARNINGS=0

# Function to print test result
print_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC} $test_name"
        ((PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗ FAIL${NC} $test_name: $message"
        ((FAILED++))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠ WARN${NC} $test_name: $message"
        ((WARNINGS++))
    fi
}

# Test 1: Check required files exist
echo "📁 Checking file structure..."

required_files=(
    "SKILL.md"
    "bmad-manifest.json"
    "session-init.md"
    "document-verification.md"
    "instruction-generation.md"
    "references/memory-system.md"
    "references/access-boundaries.md"
    "scripts/document-verifier.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_result "File exists: $file" "PASS"
    else
        print_result "File exists: $file" "FAIL" "Missing required file"
    fi
done

# Test 2: Validate manifest JSON
echo ""
echo "📋 Validating bmad-manifest.json..."

if command -v python3 &> /dev/null; then
    if python3 -c "import json; json.load(open('bmad-manifest.json'))" 2>/dev/null; then
        print_result "Manifest JSON syntax" "PASS"
        
        # Check required fields
        if python3 -c "
import json
data = json.load(open('bmad-manifest.json'))
required = ['module-code', 'persona', 'has-memory', 'capabilities']
for field in required:
    if field not in data:
        print(f'Missing field: {field}')
        exit(1)
print('All required fields present')
" 2>/dev/null; then
            print_result "Manifest required fields" "PASS"
        else
            print_result "Manifest required fields" "FAIL" "Missing required fields"
        fi
    else
        print_result "Manifest JSON syntax" "FAIL" "Invalid JSON"
    fi
else
    print_result "Manifest validation" "WARN" "Python3 not available for JSON validation"
fi

# Test 3: Check document verifier script
echo ""
echo "🔍 Testing document-verifier.py..."

if [ -f "scripts/document-verifier.py" ]; then
    if command -v python3 &> /dev/null; then
        # Test script syntax
        if python3 -m py_compile scripts/document-verifier.py 2>/dev/null; then
            print_result "Document verifier syntax" "PASS"
            
            # Test script help
            if python3 scripts/document-verifier.py --help > /dev/null 2>&1; then
                print_result "Document verifier help" "PASS"
            else
                print_result "Document verifier help" "WARN" "Help command failed"
            fi
        else
            print_result "Document verifier syntax" "FAIL" "Python syntax error"
        fi
    else
        print_result "Document verifier test" "WARN" "Python3 not available"
    fi
fi

# Test 4: Check SKILL.md frontmatter
echo ""
echo "📝 Validating SKILL.md frontmatter..."

if [ -f "SKILL.md" ]; then
    if command -v python3 &> /dev/null; then
        if python3 -c "
import re
with open('SKILL.md', 'r') as f:
    content = f.read()
    
# Check for YAML frontmatter
if not content.startswith('---'):
    print('No YAML frontmatter found')
    exit(1)

# Extract frontmatter
frontmatter = content.split('---')[1]
if 'name:' not in frontmatter:
    print('Missing name field')
    exit(1)
if 'description:' not in frontmatter:
    print('Missing description field')
    exit(1)
    
print('Frontmatter valid')
" 2>/dev/null; then
            print_result "SKILL.md frontmatter" "PASS"
        else
            print_result "SKILL.md frontmatter" "FAIL" "Invalid frontmatter"
        fi
    else
        print_result "SKILL.md validation" "WARN" "Python3 not available"
    fi
fi

# Test 5: Check memory system structure
echo ""
echo "🧠 Validating memory system references..."

if [ -f "references/memory-system.md" ]; then
    # Check for key sections
    if grep -q "session-state.md" references/memory-system.md; then
        print_result "Memory system structure" "PASS"
    else
        print_result "Memory system structure" "WARN" "Missing session-state.md reference"
    fi
    
    if grep -q "discovery-cache.md" references/memory-system.md; then
        print_result "Discovery cache reference" "PASS"
    else
        print_result "Discovery cache reference" "WARN" "Missing v0.2.0 discovery cache"
    fi
else
    print_result "Memory system file" "FAIL" "memory-system.md missing"
fi

# Test 6: Check v0.2.0 specific features
echo ""
echo "🚀 Validating v0.2.0 enhancements..."

# Check for auto-discovery in session-init.md
if grep -q "Auto-Discovery" session-init.md 2>/dev/null; then
    print_result "Auto-discovery feature" "PASS"
else
    print_result "Auto-discovery feature" "FAIL" "Missing auto-discovery implementation"
fi

# Check for document verification
if [ -f "document-verification.md" ]; then
    print_result "Document verification capability" "PASS"
else
    print_result "Document verification capability" "FAIL" "Missing document-verification.md"
fi

# Check for code review escalation in instruction-generation.md
if grep -q "escalation" instruction-generation.md 2>/dev/null; then
    print_result "Code review escalation" "PASS"
else
    print_result "Code review escalation" "FAIL" "Missing escalation paths"
fi

# Test 7: Check access boundaries
echo ""
echo "🔒 Validating access boundaries..."

if [ -f "references/access-boundaries.md" ]; then
    # Check for v0.2.0 sections
    if grep -q "Auto-Discovery Constraints" references/access-boundaries.md; then
        print_result "v0.2.0 access boundaries" "PASS"
    else
        print_result "v0.2.0 access boundaries" "WARN" "Missing enhanced constraints"
    fi
    
    # Check for deny zones
    if grep -q "Deny Zones" references/access-boundaries.md; then
        print_result "Deny zones defined" "PASS"
    else
        print_result "Deny zones defined" "WARN" "Missing deny zones"
    fi
else
    print_result "Access boundaries file" "FAIL" "access-boundaries.md missing"
fi

# Test 8: Check script permissions
echo ""
echo "🔐 Checking script permissions..."

if [ -f "scripts/document-verifier.py" ]; then
    if [ -x "scripts/document-verifier.py" ]; then
        print_result "Script executable permissions" "PASS"
    else
        print_result "Script executable permissions" "WARN" "document-verifier.py not executable"
    fi
fi

# Summary
echo ""
echo "📊 Test Summary"
echo "================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    echo "The BMAD Crew Advisor v0.2.0 is ready for deployment."
    exit_code=0
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Please fix the issues before deployment.${NC}"
    exit_code=1
fi

if [ $WARNINGS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Consider addressing the warnings for optimal performance.${NC}"
fi

exit $exit_code
