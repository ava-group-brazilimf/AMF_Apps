# Agent Development Tasks: AST-Artifact Consumption Extension + compressed/ Path Fix

**Plan**: `specs/010-asis-agents-ast-artifact-consumption/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm all 6 frontmatter versions match their own FASE OBRIGATÓRIA `--version` literal
  ```bash
  # see quickstart.md "Version consistency" section
  ```
  **Result**: all matched.

## Category 2 — Implementation

- [x] **2.1** `solution-delphi.md`: 17× `extraction/` → `compressed/`; version PATCH `2.1.0`→`2.1.1` — DONE
- [x] **2.2** `shared/output-paths.md`, `docs/asis-diagnostic-io-map.md`: same path correction — DONE
- [x] **2.3** `test-qa-asis.md`: Input Contract row + Step 1.5 existence check + Skill 1/2 primary-source notes; version `3.0.0`→`3.1.0` — DONE
- [x] **2.4** `inventory-asis.md`: new Input Contract section + Skills-level primary-source note + Form Registry procedure primary-source note; version `1.3.0`→`1.4.0` — DONE
- [x] **2.5** `db-analyzer.md`: new Input Contract section + new `### AST Data Ingestion` subsection + Table Inventory/Business Logic Detector notes; version `1.3.0`→`1.4.0` — DONE
- [x] **2.6** `events-pubsub-asis.md`: new Input Contract section + new Step 0 + Step 1 partial-primary-source note; version `1.0.0`→`1.1.0` — DONE
- [x] **2.7** `documentation-asis.md`: new Input Contract section + FT/RF inline primary-source notes; version `1.5.9`→`1.6.0` — DONE

## Category 3 — Schema Updates — SKIP

No new JSON schema authored; all artifacts already documented in `specs/007-solution-delphi-ast-consumption/data-model.md`.

## Category 4 — Module Registration — SKIP

No `module.yaml` change; all changes are `modify-existing`, same agent IDs.

## Category 5 — Quality Gate Checklists

- [x] **5.1** `extraction/` fully eliminated: `grep -c` → 0/0/0 across the 3 affected files
- [x] **5.2** `compressed/` count matches prior `extraction/` count (17) in `solution-delphi.md`
- [x] **5.3** `Fallback` heading present and non-zero in all 5 newly-wired agent files
- [x] **5.4** Fence balance confirmed across all 6 touched agent files
- [x] **5.5** `pipeline_observer.py` + `generate_observability_report.py` catalog versions synced for the 4 catalogued agents (`events-pubsub` absent from both, pre-existing gap)
- [x] **5.6** Both touched Python files compile (`py_compile`)

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — resumed run: all 5 agents use AST as primary source when present — PASS (structural)
- [x] **6.2** CA02 — fresh run, race unfavorable: safe, unblocked fallback — PASS (structural; real-run timing not testable in this session, documented as a known limitation)
- [x] **6.3** CA03 — non-Delphi project: AST checks skip entirely — PASS (structural)
- [x] **6.4** CA04 — path correction verified — PASS

## Category 7 — Documentation

- [x] **7.1** `shared/output-paths.md`, `docs/asis-diagnostic-io-map.md` — updated for the path fix
- [x] **7.2** This spec-kit documentation (spec/plan/research/quickstart/tasks/checklist) — DONE

## Completion Checklist

- [x] All 6 agent files structurally verified sound (fence balance, Fallback preservation, version consistency)
- [x] `compressed/` is now the canonical path everywhere `solution-delphi.md` reads AST artifacts
- [x] 5 agents (test-qa, inventory, db-analyzer, events-pubsub, documentation) now check for and prefer AST artifacts when present, with original behavior fully preserved as fallback
- [x] Every partial-coverage/permanent-exception case (orphan_dfm, DB vendor, Events/PubSub/IPC, FT navigation edges, RN's deliberate distinctness, PR's absent procedure) stated honestly, not oversold
- [x] Phase A race condition documented as a known limitation, not silently fixed or ignored — reordering `orchestrator-asis.md`'s dispatch phases explicitly out of scope
- [x] Security sub-agents, non-Delphi solution agents, and pure-consolidation agents explicitly excluded with reasoning
