# Agent Implementation Plan: Mandatory Spec Read Before Every Cross-Agent Dispatch

**Spec**: `specs/013-master-orchestrator-mandatory-spec-read/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (2 orchestrator agent files + 1 module.yaml, no new agents) |
| **Primary Requirement** | `master-orchestrator.md` dispatching F1 (`@ava-asis-orchestrator \| SA \| FULL`) skipped the AST extraction step that runs correctly on standalone invocation. Root cause: dispatch is a bare `DISPATCH @agent + params`, with no instruction to `Read` the target's spec first — same pattern at all 24 dispatch points (F1-F7) and one level down in `orchestrator-asis.md`'s own Wave 1 dispatch |
| **Technical Approach** | Global `## Dispatch Protocol` guardrail + `Spec File` lookup column in `master-orchestrator.md`'s existing `## Agent Team` table; inline `⛔ Read(...)` prefix at each of the 24 `DISPATCH` lines (no renumbering); identical single-site fix in `orchestrator-asis.md` Step 3.1; collateral `devops-agents/module.yaml` registration fix for 4 agents discovered missing while building the path table |
| **Implementation Status** | Complete. Structural greps below. |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except `version`/`date`/`description` on both agent files.
- [x] **Article IV** — `devops-agents/module.yaml` registration gap fixed as part of this PBI (4 agents).
- [x] **Article V** — pt-BR body content preserved throughout both agent files.
- [x] **Article VI** — BDD scenarios cover the reported bug, its log-visibility symptom, the F2-F7 consistency extension, and the collateral registration fix.
- [x] **Article X (SemVer)** — MINOR for `master-orchestrator.md` (new section + 24 sites, nothing removed), PATCH for `orchestrator-asis.md` (single-site hardening) and `devops-agents/module.yaml` (registration only).
- [x] No `[NEEDS CLARIFICATION]` markers — both scope questions (fix both dispatch points? all F1-F7 or just F1?) resolved with the user via `AskUserQuestion` before implementation.

## Technical Context

Pure Markdown/prose edits to 2 LLM-prompt agent files (not executable code) plus one YAML
registration fix. "Implementation" means rewriting the dispatch contract so the *next* LLM-driven
execution of `master-orchestrator` reliably loads each target agent's full spec before "becoming"
it, closing an implicit-judgment dependency that worked in a small/focused context (standalone
invocation) but failed in a large/complex one (7-phase pipeline execution).

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
2 parallel Explore agents, cross-verified with direct reads: (1) confirmed `master-orchestrator.md`'s
F1 dispatch (and all 23 other dispatch points) has zero `Read`/SubAgent/Task-tool mechanism — the
only correct precedent in the whole repo is `dispatch_bridge_fastqa()` inside `orchestrator-asis.md`
itself; (2) confirmed `orchestrator-asis.md`'s own trigger handling (`SA`/`SA|FULL`/`FP`) is
trigger-agnostic for Phase A — ruled out as the bug's location; (3) confirmed the target project's
`ava_ast_analyzer_path` was correctly configured — ruled out config as the cause. One Explore agent
flagged and correctly ignored an injected fake "system-reminder" embedded in tool output — did not
act on it, flagged it per policy instead.

### Phase 1 — Scope Confirmation ✅ CONCLUÍDO
2 `AskUserQuestion` rounds resolved: fix both dispatch points (master→asis AND asis→solution), and
apply the hardening to all F1-F7 dispatch points, not just the reported F1 case.

### Phase 2 — Path Resolution ✅ CONCLUÍDO
Grepped every relevant `module.yaml` (`asis-diagnostic`, `tobe-architecture`, `prototype`,
`tech-stack`, `qa-agents`, `devops-agents`, `deliverables`, `summary`) to build the 24-entry
agent→spec-file table with zero guessed paths. Discovered mid-way that 4 `devops-agents` files
(`cost-estimate-agent.md`, `iac-aws/gcp/k8s-native-agent.md`) exist on disk but were never
registered — verified each file's own frontmatter (`status`/`implementation.status`) before
deciding how to register them (3 as `status: stub`, 1 as a normal entry).

### Phase 3 — `master-orchestrator.md` Hardening ✅ CONCLUÍDO
New `## Dispatch Protocol` section (global rule + rationale + log-visibility reinforcement);
`## Agent Team` table extended with `Spec File` column (+ 3 previously-absent STUB rows for
completeness); all 24 `DISPATCH @agent-id` lines prefixed with `⛔ Read(path) OBRIGATÓRIO (ver §
Dispatch Protocol) →` — inline, no sub-step renumbering, applied uniformly including the 4
conditional cloud-provider branches inside Step 6.5. Frontmatter version + changelog line.

### Phase 4 — `orchestrator-asis.md` Step 3.1 Hardening ✅ CONCLUÍDO
Same `⛔ Read(...)` pattern inserted before `invocar @{resolved_solution_agent}`, referencing the
`SOLUTION_AGENTS` routing table already defined in Step 2 for path resolution (dynamic per
`legacy_technology`, unlike the 24 static paths in master-orchestrator.md). Frontmatter version +
changelog line.

### Phase 5 — Collateral Module Registration Fix ✅ CONCLUÍDO
`devops-agents/module.yaml`: added `ava-devops-cost-estimate`, `ava-devops-iac-aws`,
`ava-devops-iac-gcp`, `ava-devops-iac-k8s-native` — the latter 3 marked `status: stub` after
confirming each file's own frontmatter self-declares `🚧 STUB — NOT IMPLEMENTED` /
`version: "0.1.0-stub"`. Version bumped `1.0.0`→`1.0.1`.

### Phase 6 — Verification (this session)
Structural greps confirming exactly 24 `⛔ Read(` occurrences in `master-orchestrator.md`, the
Step 3.1 fix present in `orchestrator-asis.md`, and all 4 collateral registrations present in
`devops-agents/module.yaml` — see `## Test Strategy` below. No live pipeline run possible in this
session (prose instruction files, not executable code) — consistent with `specs/008`/`specs/010`/
`specs/011`'s own precedent of structural-only verification for this repo's agent-spec PBIs.

## Complexity Tracking

| Item | Status |
|---|---|
| 24 mechanical edits risk introducing a typo/wrong-path at any single site | Every path in the `Spec File` table was grepped directly from `module.yaml`, not typed from memory; final verification greps confirm the count (24) and presence, not just "some edits happened" |
| Renumbering all 24 dispatch sub-steps would have been far more invasive | Deliberately avoided — the `Read` instruction was folded into the existing numbered `DISPATCH` line instead of becoming its own new sub-step, keeping the diff minimal and low-risk |
| Discovering 4 unregistered `devops-agents` entries mid-PBI (unplanned scope creep risk) | Verified each file's own frontmatter before registering (3 confirmed STUB via `🚧 STUB — NOT IMPLEMENTED` + `0.1.0-stub` version; 1 confirmed real via a normal `1.0.0` version and full description) rather than assuming; kept as a small, directly-relevant collateral fix rather than a separate PBI, since the path table required knowing these paths anyway |
| Whether the same gap exists inside other orchestrators' own internal sub-dispatches | Explicitly excluded (spec.md §8) rather than silently expanding scope beyond what the user confirmed — flagged as a possible future PBI instead |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| All 24 dispatch points hardened | `grep -c "⛔ Read("` in `master-orchestrator.md` | 24 |
| Step 3.1 hardened | `grep -n "Read(" ` in `orchestrator-asis.md` around Step 3.1 | Present, referencing `resolved_solution_agent` |
| Collateral registrations present | `grep -c "ava-devops-cost-estimate\|ava-devops-iac-aws\|ava-devops-iac-gcp\|ava-devops-iac-k8s-native"` in `devops-agents/module.yaml` | 4 |
| No orphaned/duplicate Agent Team rows | Row count in `## Agent Team` table matches 24 dispatch points + 7 `ava-summary` rows |  31 rows |
| Frontmatter version consistency | `master-orchestrator.md` `version: "1.4.0"`, `orchestrator-asis.md` `version: "2.19.1"`, `devops-agents/module.yaml` `version: "1.0.1"` | All match |
