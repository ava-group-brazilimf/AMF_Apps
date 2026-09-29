# Artifact Inventory (Data Model): Remove Agents 024

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-20

---

## Artifacts Removed from Pipeline

| Artifact path | Former producer | Consumers removed alongside |
|---|---|---|
| `projects/{p}/outputs/asis/qa/test-map.md` | `ava-asis-test-qa` | `summary-agent.md` `testMap` fallback |
| `projects/{p}/outputs/asis/qa/test-coverage-asis.md` | `ava-asis-test-qa` | `summary-agent.md` fallback; `build_summary_*.py` reads |
| `projects/{p}/outputs/asis/qa/test-baseline.md` | `ava-asis-test-qa` | `summary-agent.md` fallback; `remediate_summary.py` synthesis |
| `projects/{p}/outputs/asis/qa/test-cases-baseline-asis.md` | `ava-asis-baseline-test-generator` | None found |
| `projects/{p}/outputs/asis/qa/test-cases-baseline-asis.json` | `ava-asis-baseline-test-generator` | None found |
| `projects/{p}/outputs/qa/golden-dataset.json` | `ava-asis-golden-dataset-capture` | `build_summary_*.py` reads |
| `projects/{p}/outputs/qa/golden-dataset-capture-report.md` | `ava-asis-golden-dataset-capture` | `build_summary_*.py` reads |
| `projects/{p}/outputs/qa/golden-dataset-execution-log.md` | `ava-asis-golden-dataset-capture` | None found |

---

## Artifacts Retained / Transferred

| Artifact path | Former producer | New producer | Status |
|---|---|---|---|
| `projects/{p}/outputs/asis/qa/test-gaps.md` | `ava-asis-test-qa` (partial) | `ava-asis-bridge-fastqa` Step 15 | **KEEP — new producer** |

---

## Existing `ava-asis-bridge-fastqa` QA Artifacts (updated)

| Artifact path | Status | Change |
|---|---|---|
| `projects/{p}/outputs/asis/qa/test-gaps.md` | **RENAME** | Formerly `qa/gap-analysis.md` — same artifact, new name |
| `projects/{p}/outputs/asis/qa/test-cases.md` | **KEEP** | Unchanged |
| `projects/{p}/outputs/asis/qa/test-plan.md` | **KEEP** | Unchanged |

---

## New `test-gaps.md` Structure

Produced by `transform_gaps_to_test_gaps()` in bridge-fastqa Step 15.

```markdown
# Test Gaps — {project_name} (PBI-{N})

**Gerado por**: ava-asis-bridge-fastqa v4.1.0 — Step 15
**PBI Origem**: PBI-{N}

| ID    | Descrição         | Categoria  | Módulo  | Risco | Recomendação |
|-------|-------------------|------------|---------|-------|--------------|
| TG-001| {gap_description} | {categoria}| {módulo}| P0/P1/P2 | {ação} |
```

**Severity mapping**: `crítico` → `P0` | `médio` → `P1` | `baixo` → `P2`

**Source**: `fastqa/manual_test/gap_analysis/PBI-{N}_gaps.md` (categories) + `business_rules[]` (module attribution)

---

## Updated `artifact_contracts` Entry (orchestrator-asis.md)

```yaml
ava-asis-bridge-fastqa:
  mandatory:
    - "qa/test-plan.md"   # unchanged
    - "qa/test-gaps.md"   # RENAMED from qa/gap-analysis.md
    - "qa/test-cases.md"  # unchanged
  size_threshold:
    "qa/test-plan.md": 3000
```

---

## Summary Data Source Changes (summary-agent.md)

| Data key | Before | After |
|---|---|---|
| `testMap` | `qa/test-map.md` → fallback `qa/test-coverage-asis.md` → fallback `qa/test-baseline.md` → fallback AST `09_test_coverage.json` | `delphi-ast-raw/compressed/09_test_coverage.json` primary; `[AUSENTE]` for non-Delphi |
| `testGaps` | `qa/test-gaps.md` + fallback from `qa/test-coverage-asis.md` section | `qa/test-gaps.md` only |
