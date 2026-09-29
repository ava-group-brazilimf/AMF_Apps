# Agent Development Tasks: Observability Self-Report Activation Fix

**Plan**: `specs/004-observability-self-report-activation-fix/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm all 5 files' frontmatter versions bumped
  ```bash
  grep -n '^version' src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  grep -n '^version' src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md
  grep -n '^version' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
  grep -n '^version' src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md
  grep -n '^version' src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md
  ```
  **Result**: `1.4.0` / `2.18.1` / `2.1.1` / `1.7.1` / `1.2.1` respectively.

## Category 2 — Implementation

- [x] **2.1** master-orchestrator.md: `init` inlined in Step 0.4 — DONE
- [x] **2.2** master-orchestrator.md: `track`+`finalize` inlined in Completion Signal — DONE
- [x] **2.3** master-orchestrator.md: old appendix demoted to reference-only — DONE
- [x] **2.4** master-orchestrator.md: `5.8`/`5.9` duplicate numbering fixed — DONE
- [x] **2.5** orchestrator-asis.md: `track` inlined in Orchestration Completion Gate — DONE
- [x] **2.6** orchestrator-tobe.md: `track` inlined in Execution Timing Output — DONE
- [x] **2.7** orchestrator-stack.md: `track` inlined in Execution Timing Output — DONE
- [x] **2.8** qa-orchestrator-agent.md: new Passo T3 with `track` — DONE
- [x] **2.9** orchestrator-tobe.md incidental fixes ({project_name}, stray fence, line endings) — DONE

## Category 3/4 — SKIP (no schema or module.yaml changes)

## Category 5 — Quality Gate Checklists

- [x] **5.1** Confirm no unintended content change beyond the planned edits in any of the 5 files (checked via `git diff --stat`; `orchestrator-tobe.md`'s large diff traced to cosmetic editor table-reformatting, confirmed byte-identical text)

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — one correctly-placed `track` call per file — PASS
- [x] **6.2** CA02 — fence balance — PASS
- [x] **6.3** CA03 — end-to-end dry run — PASS (per-agent metrics.json + 4-sheet Excel produced)
- [x] **6.4** CA04 — 92 leaf files confirmed still unfixed (documents the gap accurately) — PASS

## Category 7 — Documentation

- [x] **7.1** `specs/003-agent-self-observability/spec.md` cross-referenced with this fix
- [ ] **7.2** `.github/copilot-instructions.md` SPECKIT block — optional, not updated this pass (low value churn for a bugfix PBI; `specs/003`'s pointer is still reasonably current context)
- [ ] **7.3** Root `CHANGELOG.md` entry — recommended follow-up, not added this pass to keep this fix minimal and reviewable in isolation

## Completion Checklist

- [x] All 5 files fixed and verified
- [x] Dry run proves the mechanism works end-to-end for the first time
- [x] 92-file gap stated explicitly, not silently implied fixed
- [x] Incidental regressions found while editing were corrected
