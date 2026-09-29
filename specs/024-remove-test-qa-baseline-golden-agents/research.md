# Research: Remove Agents ava-asis-test-qa, ava-asis-baseline-test-generator, ava-asis-golden-dataset-capture

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-20

---

## R-01: Verify discontinued agent files exist in the codebase

**Decision**: Agent `.md` files are present; SKILL.md wrappers are present. All are confirmed dead code after this spec — they remain on disk but are removed from all active pipeline references.

**Findings**:
- `src/modules/ava-fabric-agents/asis-diagnostic/agents/test-qa-asis.md` — present
- `src/modules/ava-fabric-agents/asis-diagnostic/agents/baseline-test-generator-asis.md` — present
- `src/modules/ava-fabric-agents/asis-diagnostic/agents/golden-dataset-capture-asis.md` — present
- `.github/skills/ava-asis-test-qa/SKILL.md` — present
- `.github/skills/ava-asis-baseline-test-generator/SKILL.md` — present
- `.github/skills/ava-asis-golden-dataset-capture/SKILL.md` — present

**Rationale**: Not deleting files in this spec (confirmed per §6 Assumptions). Deletion is a separate operational decision.

---

## R-02: Verify artifact_contracts for ava-asis-bridge-fastqa in orchestrator-asis.md

**Decision**: The existing `ava-asis-bridge-fastqa` contract block only lists `qa/test-plan.md` with a `size_threshold`. It must be extended with `qa/test-gaps.md`, `qa/gap-analysis.md`, and `qa/test-cases.md`.

**Finding**: Current block (from orchestrator-asis.md):
```yaml
ava-asis-bridge-fastqa:
  mandatory:
    - "qa/test-plan.md"
  size_threshold:
    "qa/test-plan.md": 3000
```

**Target block** after edit A-07:
```yaml
ava-asis-bridge-fastqa:
  mandatory:
    - "qa/test-plan.md"
    - "qa/test-gaps.md"
    - "qa/gap-analysis.md"
    - "qa/test-cases.md"
  size_threshold:
    "qa/test-plan.md": 3000
```

---

## R-03: Verify Step 15 structure in bridge-fastqa-asis.md

**Decision**: Step 15 (`publish_qa_artifacts`) already handles gap-analysis, test-cases, and test-plan. A 4th sub-step must be added for `test-gaps.md` generation. The procedure call is `transform_gaps_to_test_gaps(gap_content, business_rules, N)`.

**Finding**: Existing sub-steps in Step 15:
1. Copy gap-analysis → `qa/gap-analysis.md`
2. Aggregate test cases → `qa/test-cases.md`
3. Confirm test-plan.md (copied in Step 14)

New sub-step 4 must derive `test-gaps.md` from `PBI-{N}_gaps.md` + `business_rules[]` (already available in memory from Step 2).

---

## R-04: Verify golden_dataset_enabled_asis scope across the codebase

**Decision**: Flag appears only in `orchestrator-asis.md` (guard block, Step 2 read, Consistency Gate C2c, dispatch rule). No other active files reference it. Removal is complete after GROUP A edits.

---

## R-05: Verify summary utility reads for discontinued artifacts

**Decision**: `build_summary_complete.py` and `build_summary_comprehensive.py` both contain fallback chains for `test-map.md`, `test-baseline.md`, `test-coverage-asis.md`, and `golden-dataset.json`. These must be removed. The `test-gaps.md` read is retained. A guarded read for `09_test_coverage.json` is added.

**Alternatives considered**: Replacing artifact paths with empty-string fallbacks — rejected because it would silently produce empty summary sections without error visibility. Direct removal with `09_test_coverage.json` as primary is cleaner.

---

## R-06: Confirm test-gaps.md format consumed by downstream agents

**Decision**: `test-gaps.md` is consumed by `summary-agent.md` (field `testGaps`), `summary-remediation-agent.md` (Regra C), and `validate_summary.py`. Format must include `TG-NNN` IDs with a `Risco` column (P0/P1/P2). The `transform_gaps_to_test_gaps` output template defined in spec §3.18 satisfies all three consumers.
