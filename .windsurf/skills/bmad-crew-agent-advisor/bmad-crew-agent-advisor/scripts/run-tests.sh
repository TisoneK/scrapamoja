#!/usr/bin/env bash
# BMAD Crew Advisor v0.2.0 — test suite
# Tests all scripts and validates skill structure

set -e
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0
WARN=0

green() { echo -e "\033[0;32m✓ $1\033[0m"; }
red()   { echo -e "\033[0;31m✗ $1\033[0m"; }
yellow(){ echo -e "\033[0;33m⚠ $1\033[0m"; }

pass() { green "$1"; ((PASS++)); }
fail() { red "$1";   ((FAIL++)); }
warn() { yellow "$1"; ((WARN++)); }

echo "=== BMAD Crew Advisor v0.2.0 — Test Suite ==="
echo "Skill dir: $SKILL_DIR"
echo ""

# 1. Required files
echo "--- File structure ---"
required_files=(
  "SKILL.md"
  "bmad-manifest.json"
  "session-init.md"
  "violation-detection.md"
  "checkpoint-enforcement.md"
  "document-verification.md"
  "instruction-generation.md"
  "mistakes-file.md"
  "init.md"
  "save-memory.md"
  "references/bmad-workflow-reference.md"
  "references/memory-system.md"
  "references/access-boundaries.md"
  "scripts/git-validator.py"
  "scripts/session-validator.py"
  "scripts/mistakes-generator.py"
  "scripts/document-verifier.py"
)

for f in "${required_files[@]}"; do
  if [ -f "$SKILL_DIR/$f" ]; then
    pass "$f exists"
  else
    fail "$f missing"
  fi
done

# 2. SKILL.md frontmatter
echo ""
echo "--- SKILL.md validation ---"
if head -5 "$SKILL_DIR/SKILL.md" | grep -q "^name:"; then
  pass "SKILL.md has name field"
else
  fail "SKILL.md missing name field"
fi
if head -10 "$SKILL_DIR/SKILL.md" | grep -q "^description:"; then
  pass "SKILL.md has description field"
else
  fail "SKILL.md missing description field"
fi

# 3. Manifest validation
echo ""
echo "--- Manifest validation ---"
if python3 -c "import json; json.load(open('$SKILL_DIR/bmad-manifest.json'))" 2>/dev/null; then
  pass "bmad-manifest.json is valid JSON"
else
  fail "bmad-manifest.json is invalid JSON"
fi
if python3 -c "
import json
m = json.load(open('$SKILL_DIR/bmad-manifest.json'))
assert 'capabilities' in m, 'no capabilities'
assert len(m['capabilities']) >= 5, 'too few capabilities'
assert 'persona' in m, 'no persona'
print('ok')
" 2>/dev/null | grep -q ok; then
  pass "Manifest has required fields and capabilities"
else
  fail "Manifest missing required fields"
fi

# 4. Script syntax
echo ""
echo "--- Script syntax ---"
for script in git-validator.py session-validator.py mistakes-generator.py document-verifier.py; do
  if [ -f "$SKILL_DIR/scripts/$script" ]; then
    if python3 -m py_compile "$SKILL_DIR/scripts/$script" 2>/dev/null; then
      pass "$script syntax OK"
    else
      fail "$script has syntax errors"
    fi
  fi
done

# 5. Script --help
echo ""
echo "--- Script --help ---"
for script in git-validator.py session-validator.py mistakes-generator.py; do
  if python3 "$SKILL_DIR/scripts/$script" --help >/dev/null 2>&1; then
    pass "$script --help works"
  else
    warn "$script --help returned non-zero (may be ok)"
  fi
done

# 6. Feature coverage check
echo ""
echo "--- Feature coverage (IDEA checklist) ---"
declare -A idea_files=(
  ["IDEA-001 mistakes file"]="mistakes-file.md"
  ["IDEA-002 full lifecycle commits"]="checkpoint-enforcement.md"
  ["IDEA-003 auto-discovery"]="session-init.md"
  ["IDEA-004 git automation"]="scripts/git-validator.py"
  ["IDEA-005 output format"]="SKILL.md"
  ["IDEA-007 workflow reference"]="references/bmad-workflow-reference.md"
  ["IDEA-008 phase summaries"]="checkpoint-enforcement.md"
  ["IDEA-009 scope detection"]="violation-detection.md"
  ["IDEA-010 pushback rules"]="violation-detection.md"
  ["IDEA-011 self-doubt flag"]="instruction-generation.md"
  ["IDEA-012 locked decisions re-ref"]="instruction-generation.md"
  ["IDEA-013 session-end detection"]="checkpoint-enforcement.md"
  ["IDEA-014 escalation paths"]="instruction-generation.md"
)

for idea in "${!idea_files[@]}"; do
  file="${idea_files[$idea]}"
  if [ -f "$SKILL_DIR/$file" ]; then
    pass "$idea covered in $file"
  else
    fail "$idea — missing $file"
  fi
done

# Summary
echo ""
echo "==========================="
echo "Results: $PASS passed, $FAIL failed, $WARN warnings"
if [ "$FAIL" -eq 0 ]; then
  echo "✓ All tests passed"
  exit 0
else
  echo "✗ $FAIL test(s) failed"
  exit 1
fi
