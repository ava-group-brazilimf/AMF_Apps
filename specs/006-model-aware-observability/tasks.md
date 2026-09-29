# Agent Development Tasks: Model-Aware Observability

**Plan**: `specs/006-model-aware-observability/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm both tool scripts still compile after the edits
  ```bash
  python -m py_compile src/shared/tools/pipeline_observer.py src/shared/tools/agent_observability.py
  ```
  **Result**: OK.

## Category 2 — Implementation

- [x] **2.1** `pipeline_observer.py`: `MODEL_PRICING`, `DEFAULT_MODEL`, `_get_pricing_for_model()`, model-aware `_calc_cost` — DONE
- [x] **2.2** `agent_observability.py`: same treatment — DONE
- [x] **2.3** Batch-replace hardcoded `--model "Claude Opus 4.6"` across 96 agent files — DONE, 0 errors
- [x] **2.4** Manually fix `orchestrator-tobe.md` (missing heading + model fix + recurring dropped-fence regression) — DONE
- [x] **2.5** Update `observability-self-report.md` (v2.1.0) — DONE
- [x] **2.6** Update `src/shared/tools/README.md` with the pricing table — DONE

## Category 3/4 — SKIP (no schema or module.yaml changes)

## Category 5 — Quality Gate Checklists

- [x] **5.1** Confirm CLI default changed from Opus to Sonnet tier in both scripts
  ```bash
  grep -n 'DEFAULT_MODEL = ' src/shared/tools/pipeline_observer.py src/shared/tools/agent_observability.py
  ```

## Category 6 — Acceptance Validation

- [x] **6.1** CA01/CA02/CA03 — cost varies correctly by model, safe fallback — PASS
- [x] **6.2** CA04 — mixed models within the same pipeline run — PASS
- [x] **6.3** CA05 — zero hardcoded literals, 97/97 files with placeholder — PASS
- [x] **6.4** CA06 — fence balance, only pre-existing unrelated case remains — PASS

## Category 7 — Documentation

- [x] **7.1** This spec-kit documentation (spec/plan/research/quickstart/tasks/checklist)
- [ ] **7.2** Root `CHANGELOG.md` entry — recommended follow-up, not added this pass

## Completion Checklist

- [x] All 97 files verified structurally sound and functionally correct
- [x] Tool re-tested against 6 different model strings + 1 mixed-model end-to-end run
- [x] Recurring `orchestrator-tobe.md` regression fixed again and flagged for awareness
