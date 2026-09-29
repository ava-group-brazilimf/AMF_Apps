# Quickstart Validation Guide: Summary Artifact Integrity (007)

**Feature**: `007-summary-artifact-integrity`
**Date**: 2026-07-08

---

## Prerequisites

- A project with at least one complete phase run (e.g., Sophia or Meu-ERP)
- Python 3.11+ available at `python`
- Repository root as working directory

---

## Scenario A — All Artifacts Present (happy path)

### Setup
```bash
# Use an existing project with a complete F1 run
PROJECT=Sophia   # or Meu-ERP
```

### Run
```bash
# Trigger the summary agent (will invoke Step 0.5 internally)
# In Copilot chat: type "gerar summary" for project {PROJECT}
```

### Expected Output (Step 0.5 stdout)
```
[ARTIFACT-CHECK] Verificando 42 artefatos em artifact-map.yaml...
[ARTIFACT-CHECK] OK — 42 artefatos verificados, 0 ausentes
[ARTIFACT-CHECK] Resultado: 42/42 OK | 0 ausentes | 0 vazios
  Seções omitidas: []
```

### Validation
```bash
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project $PROJECT
# Expected: exit 0; C11 section shows 0 errors, 0 warnings
```

---

## Scenario B — One Artifact Missing (missing artifact path)

### Setup
```bash
PROJECT=Meu-ERP
# Temporarily rename a known artifact to simulate drift
mv projects/$PROJECT/outputs/qa/test-plan.md projects/$PROJECT/outputs/qa/test-plan.md.bak
```

### Run
```bash
# Trigger summary agent in Copilot chat
```

### Expected Output (Step 0.5 stdout)
```
[ARTIFACT-CHECK] Verificando N artefatos em artifact-map.yaml...
[ARTIFACT-MISSING: s-test-plan] — arquivo ausente: outputs/qa/test-plan.md
[ARTIFACT-CHECK] Resultado: N-1/N OK | 1 ausente | 0 vazios
  Seções omitidas: [s-test-plan]
```

### Validation
```bash
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project $PROJECT
# Expected: exit 0 (C11 errors only trigger on unresolved markers in HTML)
# The s-test-plan section must be absent from HTML (not an empty table)
grep -c "ARTIFACT-MISSING" projects/$PROJECT/outputs/summary/AVA-FABRIC-SUMMARY-*.html
# Expected: 0  (the omission comment is <!-- OMITTED: ... --> not [ARTIFACT-MISSING])
```

### Restore
```bash
mv projects/$PROJECT/outputs/qa/test-plan.md.bak projects/$PROJECT/outputs/qa/test-plan.md
```

---

## Scenario C — Validate C11 Rules (placeholder detection)

### Setup
Inject a literal `[INCOMPLETE]` string into the generated HTML to simulate a regression.

```bash
# After a normal summary run:
HTML=$(ls projects/$PROJECT/outputs/summary/AVA-FABRIC-SUMMARY-*.html | head -1)
# Inject placeholder (test only):
sed -i 's/<\/body>/[INCOMPLETE]<\/body>/' "$HTML"
```

### Run
```bash
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project $PROJECT
```

### Expected Output
```
ERROR C11.1 — placeholder [INCOMPLETE] found in HTML body
```
Exit code: **1**

### Restore
```bash
sed -i 's/\[INCOMPLETE\]//' "$HTML"
```

---

## Success Checklist

- [ ] Scenario A: `[ARTIFACT-CHECK] OK — N artefatos verificados, 0 ausentes`
- [ ] Scenario A: `validate_summary.py` exits 0; C11 section 0 errors
- [ ] Scenario B: `[ARTIFACT-MISSING: ...]` line emitted for renamed file
- [ ] Scenario B: Generated HTML has no `[ARTIFACT-MISSING]` literal string
- [ ] Scenario C: `validate_summary.py` exits 1; ERROR C11.1 reported
- [ ] Sophia project: complete run returns exit 0, `c11_errors: 0` in validation-report.json
