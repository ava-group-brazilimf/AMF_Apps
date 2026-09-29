# Quickstart Validation Guide: Unified Business Rules & Functional Requirements Artifact

**Feature**: `026-unified-business-rules-artifact`
**Date**: 2026-07-21

---

## Prerequisites

- A project with completed F1 AS-IS pipeline exists under `projects/{project_name}/`
- Python 3 available (`python --version`)
- Working directory: repo root (`c:/_git/pbi_2494/imfai-ava-fabric-apps-agents`)

---

## Validation Scenarios

### 1 — Unified file structure is correct

```bash
# After running ava-asis-documentation with trigger BRF or ALL:
python - << 'PY'
import re, sys
p = "projects/Meu-ERP/outputs/asis/docs/business-rules.md"
text = open(p, encoding="utf-8").read()

has_fr = bool(re.search(r'^## Functional Requirements', text, re.MULTILINE))
has_br = bool(re.search(r'^## Business Rules', text, re.MULTILINE))
fr_first = text.index("## Functional Requirements") < text.index("## Business Rules") if has_fr and has_br else None

print(f"has_fr={has_fr}, has_br={has_br}, fr_first={fr_first}")
assert has_fr, "FAIL: ## Functional Requirements section missing"
assert has_br, "FAIL: ## Business Rules section missing"
assert fr_first, "FAIL: ## Functional Requirements must come before ## Business Rules"
print("PASS: unified file structure correct")
PY
```

### 2 — `functional-requirements.md` does NOT exist

```bash
python -c "
import os
p = 'projects/Meu-ERP/outputs/asis/docs/functional-requirements.md'
assert not os.path.exists(p), f'FAIL: legacy file still present at {p}'
print('PASS: functional-requirements.md absent')
"
```

### 3 — `code-business-rules.md` does NOT exist

```bash
python -c "
import os
p = 'projects/Meu-ERP/outputs/asis/code-business-rules.md'
assert not os.path.exists(p), f'FAIL: deprecated file still present at {p}'
print('PASS: code-business-rules.md absent')
"
```

### 4 — Parser correctly extracts FR entries from unified file

```bash
python - << 'PY'
import sys
sys.path.insert(0, "src/modules/ava-fabric-agents/summary/utils")
from build_summary_comprehensive import parse_func_reqs
from pathlib import Path

p = Path("projects/Meu-ERP/outputs/asis/docs/business-rules.md")
reqs = parse_func_reqs(p)
print(f"funcReqs count: {len(reqs)}")
assert len(reqs) > 0, "FAIL: parse_func_reqs returned 0 entries from unified file"
for r in reqs[:3]:
    assert "id" in r and r["id"].startswith("FR-"), f"FAIL: bad entry {r}"
print("PASS: FR entries parsed correctly from unified file")
PY
```

### 5 — Summary validator passes with unified file

```bash
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py \
  --project Meu-ERP 2>&1 | grep -E "C2\.4|C11\.7|PASS|FAIL|ERROR"
# Expected: C2.4 PASS, C11.7 PASS (or WARN if funcReqs empty — not ERROR)
```

### 6 — Grep audit: no remaining references to discontinued artifacts

```bash
# Must return 0 matches (only allowed: this quickstart.md and spec files)
grep -r "functional-requirements\.md\|code-business-rules\.md" \
  src/modules/ava-fabric-agents/ \
  --include="*.md" --include="*.py" \
  -l | grep -v "specs/"
# Expected: empty output
```

---

## Expected Outcomes

| Check | Expected |
|-------|----------|
| `business-rules.md` exists | ✅ |
| `business-rules.md` has `## Functional Requirements` section | ✅ |
| `business-rules.md` has `## Business Rules` section | ✅ |
| FR section comes before BR section | ✅ |
| `functional-requirements.md` absent | ✅ |
| `code-business-rules.md` absent | ✅ |
| `parse_func_reqs()` returns > 0 entries from unified file | ✅ |
| `validate_summary.py` C2.4 = PASS | ✅ |
| Grep audit returns 0 files | ✅ |
