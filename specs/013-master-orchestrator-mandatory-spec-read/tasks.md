# Agent Development Tasks: Mandatory Spec Read Before Every Cross-Agent Dispatch

**Plan**: `specs/013-master-orchestrator-mandatory-spec-read/plan.md`
**Status**: Implementation complete; verification in progress.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm `master-orchestrator.md` frontmatter version (`1.4.0`) matches its own
  `v1.4:` changelog line.
- [x] **1.2** Confirm `orchestrator-asis.md` frontmatter version (`2.19.1`) matches its own
  `v2.19.1:` changelog line.

## Category 2 — Implementation

- [x] **2.1** `master-orchestrator.md`: new `## Dispatch Protocol` section (global rule +
  root-cause rationale + log-visibility reinforcement) — DONE
- [x] **2.2** `master-orchestrator.md`: `## Agent Team` table — new `Spec File` column, all 24
  unique paths resolved via `module.yaml` grep (not guessed); 3 previously-absent STUB rows
  (iac-aws/gcp/k8s-native) added for table completeness — DONE
- [x] **2.3** `master-orchestrator.md`: F1-F5 (5 single dispatch points) — `⛔ Read(...)` prefix
  added inline, no renumbering — DONE
- [x] **2.4** `master-orchestrator.md`: F6 (9 dispatch points incl. 4 conditional cloud-provider
  branches in Step 6.5) — same treatment — DONE
- [x] **2.5** `master-orchestrator.md`: F7 (7 dispatch points) — same treatment — DONE
- [x] **2.6** `orchestrator-asis.md` Step 3.1: `⛔ Read(...)` prefix before invoking
  `@{resolved_solution_agent}`, referencing the `SOLUTION_AGENTS` routing table — DONE
- [x] **2.7** `devops-agents/module.yaml`: registered `ava-devops-cost-estimate`,
  `ava-devops-iac-aws`, `ava-devops-iac-gcp`, `ava-devops-iac-k8s-native` (latter 3 as
  `status: stub`, verified against each file's own frontmatter) — DONE
- [x] **2.8** Frontmatter version/changelog updates on both agent files — DONE

## Category 3 — Schema Updates — SKIP

No new JSON artifact schema; this PBI only changes dispatch-instruction prose and a
`module.yaml` agent registry list.

## Category 4 — Module Registration

- [x] **4.1** `devops-agents/module.yaml` version `1.0.0`→`1.0.1` (PATCH — registration-only) —
  DONE (note: unlike most PBIs, this category is NOT skipped — see §2.7)

## Category 5 — Quality Gate Checklists

- [x] **5.1** `grep -c "⛔ Read("` in `master-orchestrator.md` → 24 (verified)
- [x] **5.2** `orchestrator-asis.md` Step 3.1 contains the `Read(...)` prefix before `invocar
  @{resolved_solution_agent}` (verified)
- [x] **5.3** `devops-agents/module.yaml` contains all 4 collateral registrations (verified)
- [x] **5.4** No dispatch sub-step was renumbered — diff limited to the `DISPATCH` line itself at
  each of the 24 sites

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — F1 via master-orchestrator now reads `orchestrator-asis.md` (which reads
  `solution-delphi.md`) before dispatching — PASS (structural)
- [x] **6.2** CA02 — live AST extraction log now reachable when dispatched via
  master-orchestrator, since the spec containing that `specs/012` instruction is actually loaded
  — PASS (structural; no live 30-min extraction run performed in this session)
- [x] **6.3** CA03 — all 22 other dispatch points (F2-F7) hardened identically for consistency —
  PASS (structural)
- [x] **6.4** CA04 — 4 previously-unregistered DevOps agents now resolve via `module.yaml` — PASS

## Category 7 — Documentation

- [x] **7.1** This spec-kit documentation (spec.md, plan.md, tasks.md) — DONE

## Completion Checklist

- [x] Root cause identified and confirmed via direct file reads, not inference alone (2 Explore
  agents, cross-checked against each other)
- [x] Both dispatch points fixed (master→asis AND asis→solution), per explicit user confirmation
- [x] All F1-F7 (24 total) dispatch points hardened, per explicit user confirmation — not scoped
  down to just the reported F1 case
- [x] Log-visibility request addressed as a direct consequence of the root-cause fix, plus an
  explicit reinforcement in the new `## Dispatch Protocol` section
- [x] Collateral `devops-agents/module.yaml` registration gap (4 agents) fixed, verified against
  each file's own frontmatter before deciding STUB vs. normal registration
- [x] No sub-step renumbering — diff kept minimal and low-risk across all 24+1 sites
- [x] No SubAgent/Task-tool mechanism introduced — existing inline dispatch convention preserved,
  only the spec-read requirement made explicit
