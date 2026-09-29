# Agent Development Tasks: Observability Mandatory Phase

**Plan**: `specs/005-observability-mandatory-phase/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm no agent contract fields (`name`/`description`/`allowed-tools`) changed
  ```bash
  git diff --stat -- src/modules/ava-fabric-agents | grep -v "insertions(+)"
  ```
  **Result**: only `master-orchestrator.md` and `orchestrator-tobe.md` show mixed +/- (expected, manual edits); all 92 batch files show pure insertions.

## Category 2 — Implementation

- [x] **2.1** Build tiered anchor detector (5 tiers) — DONE, dry-run reviewed and iteratively broadened
- [x] **2.2** Batch-apply to 92 leaf-agent files — DONE, 0 errors
- [x] **2.3** Verify + individually confirm the 3 severely-misplaced files resolve correctly — DONE
- [x] **2.4** Re-strengthen the 5 orchestrator-tier files with the new template — DONE
- [x] **2.5** Fix unrelated pre-existing dropped-fence regression in `orchestrator-tobe.md` — DONE (incidental, found while editing)
- [x] **2.6** Reframe `observability-self-report.md` as reference/rationale material (v2.0.0) + environment caveat — DONE
- [x] **2.7** Add environment-requirement caveat to `src/shared/tools/README.md` — DONE

## Category 3/4 — SKIP (no schema or module.yaml changes)

## Category 5 — Quality Gate Checklists

- [x] **5.1** Confirm the environmental constraint is stated honestly in at least 3 places (shared doc, tools README, spec.md) — PASS

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — 97/97 files with FASE OBRIGATÓRIA, 0 missing the command, 1 pre-existing unrelated fence issue — PASS
- [x] **6.2** CA02 — 3 previously-misplaced files verified individually by direct read — PASS
- [x] **6.3** CA03 — tool genericity across 2 different project names — PASS
- [x] **6.4** CA04 — environmental limitation documented — PASS

## Category 7 — Documentation

- [x] **7.1** `specs/003` and `specs/004` cross-referenced with this fix (recommended follow-up — see below)
- [ ] **7.2** Root `CHANGELOG.md` entry — recommended, not added this pass (keep this fix reviewable in isolation, matching specs/004's approach)
- [ ] **7.3** `.github/copilot-instructions.md` SPECKIT pointer update to `specs/005` — optional, low priority for a same-day iterative bugfix chain

## Completion Checklist

- [x] All 97 files verified structurally sound
- [x] 3 known misplaced files individually re-verified, not assumed fixed
- [x] Tool re-confirmed generic (2 different project names)
- [x] Environmental constraint documented, not hidden
- [x] Unrelated regression found while editing (`orchestrator-tobe.md` dropped fence) fixed
