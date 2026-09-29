# Quickstart Validation Guide — 025 Summary Test Cases AS-IS Menu

## Prerequisites

- Project `Meu-ERP_w_AST` available with `asis/qa/test-cases.md` populated
- Python 3.x environment at the repo root
- `build_summary_comprehensive.py` and `validate_summary.py` accessible at `src/modules/ava-fabric-agents/summary/utils/`

## Step 1 — Verify source artifact

```bash
# Confirm test-cases.md exists and has CT- headings
grep -c "^## CT-" projects/Meu-ERP_w_AST/outputs/asis/qa/test-cases.md
# Expected: ≥1
```

## Step 2 — Rebuild the summary

```bash
python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py \
  --project Meu-ERP_w_AST
# Expected: ✅ SUCESSO!
```

## Step 3 — Smoke-test D.testCases injection

```bash
# Confirm D.testCases is present and non-empty in the generated HTML
grep -o '"testCases":\[' projects/Meu-ERP_w_AST/outputs/summary/AVA-FABRIC-SUMMARY-*.html | head -1
# Expected: "testCases":[
python -c "
import re, pathlib, json, glob
html_files = sorted(glob.glob('projects/Meu-ERP_w_AST/outputs/summary/AVA-FABRIC-SUMMARY-*.html'))
html = pathlib.Path(html_files[-1]).read_text(encoding='utf-8', errors='replace')
m = re.search(r'testCases\s*:\s*(\[[\s\S]*?\])\s*,\s*\n', html)
data = json.loads(m.group(1)) if m else []
print(f'D.testCases count: {len(data)}')
if data:
    print(f'First entry: {data[0]}')
"
# Expected: D.testCases count: ≥1
```

## Step 4 — Run the validator

```bash
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py \
  --project Meu-ERP_w_AST
# Expected: exit code 0; C11.37 check must appear as "passed" or "skipped"
# NOT expected: C11.37 firing as "warn" (that would mean D.testCases is empty while test-cases.md has CTs)
```

## Step 5 — Visual check in browser

Open the generated HTML file in a browser:
1. Sidebar → F1 — Diagnóstico AS-IS → **Test Cases** nav item should appear
2. Click "Test Cases" → section `Test Cases AS-IS` should display:
   - 4 KPI tiles (Total, P0, Funcionais, Negativos/Edge)
   - Table with columns: ID | Título | Módulo | Prioridade | Tipo | Regras | Passos
   - One row per CT- entry from `test-cases.md`
3. Nav dot for "Test Cases" should be green

## Step 6 — Test absent artifact scenario

```bash
# Temporarily rename test-cases.md
mv projects/Meu-ERP_w_AST/outputs/asis/qa/test-cases.md \
   projects/Meu-ERP_w_AST/outputs/asis/qa/test-cases.md.bak

# Rebuild
python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py \
  --project Meu-ERP_w_AST

# Validate — should pass (no warn for absent file)
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py \
  --project Meu-ERP_w_AST

# Restore
mv projects/Meu-ERP_w_AST/outputs/asis/qa/test-cases.md.bak \
   projects/Meu-ERP_w_AST/outputs/asis/qa/test-cases.md
```

Expected: `D.testCases` is `[]`, "Test Cases" section renders empty (or card hidden), validator C11.37 says "skipped".

## Step 7 — Run remediation (integration test)

```bash
python src/modules/ava-fabric-agents/summary/utils/remediate_summary.py \
  --project Meu-ERP_w_AST
# Expected: remediation-report.md shows Rule J as "Regra J: N/A — test-cases.md already exists"
# (because test-cases.md exists for this project)
```

## Expected Outcomes Summary

| Check | Expected |
|---|---|
| `build_test_cases()` returns entries | ≥1 `TestCaseEntry` dicts |
| `D.testCases` in HTML | Non-empty JSON array |
| Nav item visible | "Test Cases" in F1 sidebar |
| Section renders correctly | Table with 7 columns, ≥1 row |
| `validate_summary.py` C11.37 | `passed` |
| Absent artifact scenario | No errors; section empty; C11.37 `skipped` |
| Remediation Rule J | Reports N/A when file exists; synthesizes placeholder only when both file and `fastqa/manual_test/` are absent |
