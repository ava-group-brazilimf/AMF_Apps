# Quickstart Validation Guide: Remove Agents 024

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-20

---

## Prerequisites

- Access to the workspace `c:\_git\pbi_2494\imfai-ava-fabric-apps-agents`
- Git on a feature branch (e.g., `024-remove-test-qa-baseline-golden-agents`)
- All 18 files in the change plan edited and saved

---

## Validation Steps

### Step 1 — No discontinued agent references in active files

```bash
grep -r "ava-asis-test-qa\|ava-asis-baseline-test-generator\|ava-asis-golden-dataset-capture" \
  --include="*.md" --include="*.py" --include="*.yaml" \
  --exclude-dir=".git" --exclude-dir="specs" .
```

**Expected**: Zero matches. Any match is a missed edit.

---

### Step 2 — `golden_dataset_enabled_asis` fully removed

```bash
grep -r "golden_dataset_enabled_asis\|golden-dataset-capture\|golden_dataset" \
  --include="*.md" --include="*.py" --include="*.yaml" \
  --exclude-dir=".git" --exclude-dir="specs" .
```

**Expected**: Zero matches.

---

### Step 3 — `test-gaps.md` registered in `artifact_contracts` under `ava-asis-bridge-fastqa`

```bash
grep -A 10 "ava-asis-bridge-fastqa:" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md \
  | grep "test-gaps.md"
```

**Expected**: One match — `- "qa/test-gaps.md"`.

---

### Step 4 — `bridge-fastqa-asis.md` version bumped

```bash
grep "^version:" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md
```

**Expected**: `version: "4.1.0"`

---

### Step 5 — Step 15 of bridge-fastqa generates test-gaps.md

```bash
grep "test-gaps.md" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md
```

**Expected**: ≥2 matches — one in the Output Contract table, one in Step 15, one in Step 16 completion signal.

---

### Step 6 — Summary utilities clean of discontinued paths

```bash
grep -rn "test-map\|test-baseline\|test-coverage-asis\|golden-dataset" \
  src/modules/ava-fabric-agents/summary/utils/
```

**Expected**: Zero matches.

---

### Step 7 — validate_summary.py updated message

```bash
grep "Test Gaps\|test-gaps" \
  src/modules/ava-fabric-agents/summary/utils/validate_summary.py
```

**Expected**: Match containing `test-gaps.md · delphi-ast-raw/compressed/09_test_coverage.json`.

---

### Step 8 — module.yaml no longer contains discontinued agents

```bash
grep "ava-asis-test-qa\|ava-asis-baseline-test-generator\|ava-asis-golden-dataset-capture" \
  src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
```

**Expected**: Zero matches.

---

### Step 9 — orchestrator DAG counts updated

```bash
grep "Wave 2 (5 agents)\|7 agentes\|sub_agents_count.*13" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md
```

**Expected**: ≥1 match for each of the three updated counts.

---

## Pass Criteria Summary

| Check | Expected |
|---|---|
| Discontinued agent references | 0 matches |
| `golden_dataset_enabled_asis` references | 0 matches |
| `test-gaps.md` in bridge-fastqa `artifact_contracts` | ≥1 match |
| bridge-fastqa version | `4.1.0` |
| test-gaps.md in bridge-fastqa Step 15 + Step 16 | ≥2 matches |
| Summary utils clean | 0 matches |
| `validate_summary.py` updated message | ≥1 match |
| `module.yaml` clean | 0 matches |
| Orchestrator counts updated | ≥1 match each |
