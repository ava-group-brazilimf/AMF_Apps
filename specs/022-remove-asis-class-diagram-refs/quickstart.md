# Quickstart: Validate AS-IS Class Diagram Reference Removal

**Feature**: 022-remove-asis-class-diagram-refs  
**Phase**: 1 — Validation guide

---

## Prerequisites

- Repo cloned at `c:\_git\pbi_2494\imfai-ava-fabric-apps-agents`
- Python 3.10+ available (`python --version`)
- All changes in `data-model.md` applied

---

## Validation Steps

### Step 1 — Zero AS-IS references remain

```powershell
# Must return: no output (0 matches)
grep -rn "asis/diagrams/class-diagram" . --include="*.md" --include="*.yaml" --include="*.py"
```

Expected: **empty output**.

---

### Step 2 — Zero `CLASS_DIAGRAM` template variables remain (AS-IS only)

```powershell
# Must return: no output (only TOBE_CLASS_DIAGRAM should exist)
grep -rn '"CLASS_DIAGRAM"' src/ --include="*.py" --include="*.md"
```

Expected: **empty output** (any `TOBE_CLASS_DIAGRAM` match is fine — it's TO-BE).

---

### Step 3 — TO-BE references untouched

```powershell
# Must return at least 6 matches (same as before changes)
grep -rn "tobe/diagrams/class-diagram" . --include="*.md" --include="*.py"
```

Expected: ≥ 6 matches, all in TO-BE context (e.g. `summary-agent.md`, `build_summary_comprehensive.py`, `step-03-build-html.md`).

---

### Step 4 — Python syntax validation

```powershell
python -m py_compile src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py
python -m py_compile src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py
python -m py_compile src/modules/ava-fabric-agents/summary/utils/remediate_summary.py
python -m py_compile src/modules/ava-fabric-agents/summary/utils/validate_summary.py
python -m py_compile src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py
python -m py_compile src/modules/ava-fabric-agents/summary/utils/validate_drawio_integration.py
```

Expected: **no output** (exit code 0 for each).

---

### Step 5 — YAML syntax validation

```powershell
python -c "import yaml; yaml.safe_load(open('src/modules/ava-fabric-agents/asis-diagnostic/module.yaml', encoding='utf-8'))"
python -c "import yaml; yaml.safe_load(open('src/modules/ava-fabric-agents/summary/data/artifact-map.yaml', encoding='utf-8'))"
```

Expected: **no output** (exit code 0 for each).

---

### Step 6 — Comprehensive scan for residual `class-diagram.mmd` in AS-IS context

```powershell
# Review every match manually — confirm none are in asis/ context
grep -rn "class-diagram.mmd" . --include="*.md" --include="*.yaml" --include="*.py" | grep -v "tobe/" | grep -v "TOBE_CLASS"
```

Expected: **empty output** after the filter. Any remaining match must be reviewed to confirm it is not an AS-IS reference.

---

### Step 7 — `_synthesize_class_diagram` function removed

```powershell
# Must return: no output
grep -n "_synthesize_class_diagram" src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py
```

Expected: **empty output**.

---

### Step 8 — Summary build smoke-test (optional, requires a project)

If a project exists at `projects/Meu-ERP/`:

```powershell
cd c:\_git\pbi_2494\imfai-ava-fabric-apps-agents
python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project Meu-ERP 2>&1 | Select-String -Pattern "class-diagram|CLASS_DIAGRAM|KeyError|FileNotFoundError"
```

Expected: **no output** (no class-diagram errors from the build).

---

## Pass Criteria

All 7 mandatory steps (1–7) must produce empty output / exit code 0. Step 8 is optional but recommended when a project is available.
