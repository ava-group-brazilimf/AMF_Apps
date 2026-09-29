# Quickstart: Validation Guide — Bridge FastQA AST Simplification

**Feature**: 023-bridge-fastqa-ast-simplification
**Phase**: 1 — Validation after implementation

---

## Prerequisites

```bash
cd "c:/_git/pbi_2494/imfai-ava-fabric-apps-agents"

BRIDGE="src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md"
ORCH="src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md"
IOMAP="docs/asis-diagnostic-io-map.md"
```

---

## Check 1 — Removed Input References (must be only in deprecation notices)

```bash
echo "=== Removed inputs must not be PRIMARY inputs ==="
# Note: 2 occurrences are expected (in deprecation notices saying "NÃO utilizar")
echo -n "functional-requirements.md (expect ≤ 2 deprecation-notice lines): "
grep -c "functional-requirements.md" "$BRIDGE"

echo -n "business-rules.md (expect ≤ 2 deprecation-notice lines): "
grep -c "business-rules.md" "$BRIDGE"

# These must be 0 — they would indicate active use
echo -n "estimate_effort (expect 0): "
grep -c "estimate_effort" "$BRIDGE"

echo -n "ac_scope_analysis (expect 0): "
grep -c "ac_scope_analysis" "$BRIDGE"

echo -n "validate_scenarios (expect 0): "
grep -c "validate_scenarios" "$BRIDGE"
```

Expected: `estimate_effort`, `ac_scope_analysis`, `validate_scenarios` = 0; `functional-requirements.md` and `business-rules.md` ≤ 2 (deprecation notices only).

---

## Check 2 — New Input References (must be ≥ 2 each)

```bash
echo "=== AST inputs must be present ==="
echo -n "01_business_rules.json: "
grep -c "01_business_rules.json" "$BRIDGE"

echo -n "02_form_business_rules.json: "
grep -c "02_form_business_rules.json" "$BRIDGE"

echo -n "03_database_rules.json: "
grep -c "03_database_rules.json" "$BRIDGE"

echo -n "compressed/ path: "
grep -c "delphi-ast-raw/compressed" "$BRIDGE"

echo -n "extraction/ fallback: "
grep -c "delphi-ast-raw/extraction" "$BRIDGE"
```

Expected: all ≥ 2.

---

## Check 3 — Eliminated Pipeline Steps (must be 0)

```bash
echo "=== Eliminated steps must be absent ==="
echo -n "estimate_effort: "
grep -c "estimate_effort" "$BRIDGE"

echo -n "ac_scope_analysis: "
grep -c "ac_scope_analysis" "$BRIDGE"

echo -n "validate_scenarios: "
grep -c "validate_scenarios" "$BRIDGE"
```

Expected: all 0.

---

## Check 4 — Version Bump

```bash
echo "=== Version check ==="
echo -n "version 4.0.0 in frontmatter: "
grep -c "version: \"4.0.0\"" "$BRIDGE"

echo -n "version 3.3.0 must be absent: "
grep -c "3.3.0" "$BRIDGE"
```

Expected: `4.0.0` = 1, `3.3.0` = 0.

---

## Check 5 — Test Plan Template Sections (exactly 5)

```bash
echo "=== Test plan template section count ==="
# Count ## N. headings inside the template block
grep -c "^## [1-9]\." "$BRIDGE"
```

Expected: 5 (sections 1, 2, 3, 4, 5).

---

## Check 6 — Hard Stop Procedure Present

```bash
echo "=== Hard stop procedure ==="
echo -n "validate_ast_inputs: "
grep -c "validate_ast_inputs" "$BRIDGE"

echo -n "HARD STOP: "
grep -c "HARD STOP" "$BRIDGE"
```

Expected: both ≥ 1.

---

## Check 7 — Observability Version

```bash
echo "=== Observability version ==="
echo -n "version 4.0.0 in observer call: "
grep -c "version 4.0.0" "$BRIDGE"
```

Expected: 1.

---

## Check 8 — Orchestrator Sync

```bash
echo "=== Orchestrator artifact_contracts sync ==="
echo -n "estimate_effort/PBI in external_mandatory: "
grep -c "estimate_effort/PBI" "$ORCH"

echo -n "ac_scope.md in external_mandatory: "
grep -c "ac_scope.md" "$ORCH"

echo -n "validation_report in external_mandatory: "
grep -c "validation_report" "$ORCH"

echo -n "v4.0.0 in dispatch prompt: "
grep -c "v4.0.0" "$ORCH"

echo -n "16 Steps in dispatch prompt: "
grep -c "16 Steps" "$ORCH"

echo -n "size_threshold 3000: "
grep -c "3000" "$ORCH"
```

Expected: first three = 0; last three ≥ 1.

---

## Check 9 — IO Map Sync

```bash
echo "=== IO Map bridge-fastqa entry ==="
echo -n "01_business_rules.json in IO map: "
grep -c "01_business_rules.json" "$IOMAP"

echo -n "functional-requirements as mandatory input in IO map: "
grep -c "mandatory.*functional-requirements" "$IOMAP"

echo -n "estimate_effort in IO map outputs: "
grep -c "estimate_effort" "$IOMAP"

echo -n "ac_scope in IO map outputs: "
grep -c "ac_scope" "$IOMAP"

echo -n "validation_report in IO map outputs: "
grep -c "validation_report" "$IOMAP"

echo -n "AST JSON artifacts in cross-agent table: "
grep -c "AST JSON" "$IOMAP"
```

Expected: `01_business_rules.json` ≥ 1; `mandatory.*functional-requirements` = 0; `estimate_effort`/`ac_scope`/`validation_report` in outputs = 0; `AST JSON` ≥ 1.

---

## Full Validation Summary

Run all checks:

```bash
echo "=== FULL VALIDATION: bridge-fastqa-ast-simplification ==="

PASS=0
FAIL=0

check() {
  local label="$1"
  local count="$2"
  local expected_op="$3"  # "eq0" or "gte1"
  if [[ "$expected_op" == "eq0" && "$count" -eq 0 ]]; then
    echo "✅ $label"
    ((PASS++))
  elif [[ "$expected_op" == "gte1" && "$count" -ge 1 ]]; then
    echo "✅ $label"
    ((PASS++))
  else
    echo "❌ $label (got $count)"
    ((FAIL++))
  fi
}

check "functional-requirements.md removed"   $(grep -c "functional-requirements.md" "$BRIDGE") "eq0"
check "business-rules.md removed"            $(grep -c "business-rules.md" "$BRIDGE") "eq0"
check "estimate_effort removed"              $(grep -c "estimate_effort" "$BRIDGE") "eq0"
check "ac_scope_analysis removed"            $(grep -c "ac_scope_analysis" "$BRIDGE") "eq0"
check "validate_scenarios removed"           $(grep -c "validate_scenarios" "$BRIDGE") "eq0"
check "01_business_rules.json present"       $(grep -c "01_business_rules.json" "$BRIDGE") "gte1"
check "02_form_business_rules.json present"  $(grep -c "02_form_business_rules.json" "$BRIDGE") "gte1"
check "03_database_rules.json present"       $(grep -c "03_database_rules.json" "$BRIDGE") "gte1"
check "version 4.0.0"                        $(grep -c "version: \"4.0.0\"" "$BRIDGE") "gte1"
check "validate_ast_inputs present"          $(grep -c "validate_ast_inputs" "$BRIDGE") "gte1"
check "HARD STOP present"                    $(grep -c "HARD STOP" "$BRIDGE") "gte1"
check "orch: estimate_effort removed"        $(grep -c "estimate_effort/PBI" "$ORCH") "eq0"
check "orch: ac_scope removed"               $(grep -c "ac_scope.md" "$ORCH") "eq0"
check "orch: v4.0.0 dispatch"               $(grep -c "v4.0.0" "$ORCH") "gte1"
check "iomap: AST JSON inputs"               $(grep -c "01_business_rules.json" "$IOMAP") "gte1"
check "iomap: estimate_effort removed"       $(grep -c "estimate_effort" "$IOMAP") "eq0"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && echo "🎉 ALL CHECKS PASSED" || echo "⚠️  FIX FAILURES BEFORE MERGING"
```
