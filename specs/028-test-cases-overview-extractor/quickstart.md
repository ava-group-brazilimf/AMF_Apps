# Quickstart Validation Guide: Test Cases Overview Extractor

**Feature**: 028-test-cases-overview-extractor
**Purpose**: End-to-end validation that the feature works correctly after implementation

---

## Prerequisites

- Python 3.x installed
- Working `projects/{project_name}/outputs/asis/qa/test-cases.md` (with CT- blocks)
- Repository root as working directory

---

## Scenario 1 — Builder generates overview automatically

```bash
# From repo root
python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py \
  --project <project_name>
```

**Expected outcomes:**
- `projects/<project_name>/outputs/asis/qa/test-cases-overview.md` is created/overwritten
- File contains `# Test Cases — Overview` heading
- File contains `| Total de Test Cases | N |` row in Resumo table
- File contains `## Primeiros {min(N,10)} Test Cases` heading with a table of rows
- Generated HTML `D.testCasesContent` contains `# Test Cases — Overview` (not the full CT- blocks)

**Verify:**
```bash
head -20 projects/<project_name>/outputs/asis/qa/test-cases-overview.md
grep "Test Cases — Overview" projects/<project_name>/outputs/summary/AVA-FABRIC-SUMMARY-*.html
```

---

## Scenario 2 — CLI wrapper

```bash
# From repo root
python src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_test_cases_overview.py \
  --project <project_name>
```

**Expected output (exit 0):**
```
[OK] test-cases-overview.md generated
     Output: projects/<project_name>/outputs/asis/qa/test-cases-overview.md
```

**Error case — missing source:**
```bash
python src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_test_cases_overview.py \
  --project nonexistent-project
```

Expected: exit code 1, `[ERROR] test-cases.md not found at ...`

---

## Scenario 3 — Validator check C11.38

```bash
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py \
  --project <project_name>
```

**Expected**: C11.38 listed as `✅` (overview file present)

**To test warn path:**
```bash
# Delete the overview file, then run validator
rm projects/<project_name>/outputs/asis/qa/test-cases-overview.md
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project <project_name>
```

Expected: C11.38 fires as `⚠️ warn` with message pointing to `build_test_cases_overview()`

---

## Scenario 4 — D.testCases regression check (spec 025)

After running the builder, verify KPI tiles still work:

```bash
grep -o '"testCases":\s*\[.*\]' projects/<project_name>/outputs/summary/AVA-FABRIC-SUMMARY-*.html \
  | head -c 200
```

Expected: `"testCases": [{"id":"CT-001",...}]` — non-empty array

---

## Edge: < 10 test cases

If `test-cases.md` has only 5 CT- blocks:

```bash
cat projects/<project_name>/outputs/asis/qa/test-cases-overview.md | grep "Test Cases exibidos"
```

Expected: `| Test Cases exibidos nesta visão | 5 |` (not 10)
