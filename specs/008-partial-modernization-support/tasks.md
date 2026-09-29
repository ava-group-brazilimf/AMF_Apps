# Agent Development Tasks: Partial Modernization Support — Strangler Fig Pattern

**Plan**: `specs/008-partial-modernization-support/plan.md`
**Change Type**: `modify-existing` (multi-file — no new agents)
**PBI**: 2316 | **Child PBIs**: 2317, 2318, 2319, 2320, 2321

> Complete categories sequentially. [P] marks tasks parallelizable within a category.
> Categories 4 and 5 are N/A (no new agents, no new module registrations).
> Categories 6 and 7 can run in parallel after Category 2 completes.

---

## Category 1 — Version Bumps (Prerequisite)

Must complete before Category 2. These unblock all downstream agent-body edits.

- [X] **1.1** Bump `version` in `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md` frontmatter: `"1.2.0"` → `"1.3.0"` *(PBI 2318)*
- [X] **1.2** [P] Bump `version` in `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` frontmatter: `"1.7.1"` → `"1.8.0"` *(PBI 2319)*

---

## Category 2 — Config Schema + Agent Body Changes

Depends on Category 1. Sub-tasks within each PBI are sequential; PBIs run independently.

### 2.A — Config Template (PBI 2317)

- [X] **2.1** Insert `modernization_scope` and `target_modules` fields in `projects/_template/context/project-config.yaml` immediately after the `scope_modules: "all"` line, including the full inline comment block in Portuguese as specified in plan.md §Phase 1. Verify no other keys are displaced.

### 2.B — Master-Orchestrator Routing Branch (PBI 2318)

- [X] **2.2** Add validation steps `0.3a / 0.3b / 0.3c` to the `## Execution Steps → Step 0` section of `master-orchestrator.md`, after the existing `0.3 EXTRACT configuração de pipeline` block. Include the pre-flight block template (╔═══╗ box) for `DECISION: PROCEED / BLOCKED` as defined in plan.md §2a.2.
- [X] **2.3** Add the conditional Step 0.5 ASCII box to the Execution Pipeline diagram in `master-orchestrator.md`, inserted before the `FASE 1` box. Box text: `PASSO 0.5 — Coexistence Strategy (partial mode)` with `@ava-tobe-coexistence-strategy` dispatch and `on(step-0.5 ✓ | scope==full → skip)` gate annotation (plan.md §2a.3).
- [X] **2.4** Add a conditional row `| F2 (pré) | Coexistence Strategy | \`ava-tobe-coexistence-strategy\` | partial-only — passo 0.5 |` to the Agent Team table in `master-orchestrator.md`, immediately before the existing `F2 | TO-BE Orchestrator` row (plan.md §2a.4).
- [X] **2.5** Add `modernization_scope` and `target_modules` to the `## Input Contract` YAML block in `master-orchestrator.md`, after the existing optional fields block (plan.md §2a.5).

### 2.C — Stack-Orchestrator BC Filter Guard (PBI 2319)

- [X] **2.6** Add step `0.3c READ modernization_scope e target_modules` to `## Sequência de Execução → Step 0` in `orchestrator-stack.md`, after the existing `0.3b RESOLVE agent roster` block. Compute `filtered_bcs` and emit partial-mode LOG as specified in plan.md §2b.2.
- [X] **2.7** Add the BC Filter Check block (`[BC FILTER CHECK — executado apenas quando filtered_bcs != null]`) to `orchestrator-stack.md`, immediately before the first BC codegen dispatch in the execution sequence. Include the BC filter table emission (plan.md §2b.2).

---

## Category 3 — Shared Schema Updates

**N/A** — no changes to `agent-task.schema.json` or `agent-result.schema.json`.

---

## Category 4 — Module Registration

**N/A** — no new agents. Existing `module.yaml` registrations for both
`ava-master-orchestrator` and `ava-stack-orchestrator` are unchanged.

---

## Category 5 — Quality Gate Checklists

Depends on Category 2. Verify the four validation rules from data-model.md are enforced.

- [X] **5.1** Verify rule V1 implemented: `scope=partial` + `target_modules: []` → `DECISION: BLOCKED` with message `"modernization_scope=partial requer target_modules não-vazio."` (master-orchestrator step 0.3a).
- [X] **5.2** [P] Verify rule V2 implemented: `scope=full` + non-empty `target_modules` → WARN emitted (not block) and pipeline continues (master-orchestrator step 0.3c).
- [X] **5.3** [P] Verify rule V4 implemented: BC not in `filtered_bcs` → logged `"⏭ BC '{bc_id}' fora de target_modules — ignorado."` and removed from dispatch queue (orchestrator-stack step 0.3c / BC filter block).
- [X] **5.4** [P] Verify backward-compat (rule implicit): `project-config.yaml` without `modernization_scope` → `partial_mode = false`, no step 0.5, no BC filtering. Read the spec Scenario 4 and confirm the agent body handles absent field with `default: "full"`.
- [X] **5.5** [P] Verify rule V3: quando `scope=partial`, `scope_modules ≠ "all"` e algum item de `target_modules` não existe em `scope_modules`, o master-orchestrator emite um WARN — e o item é silenciosamente ignorado pelo stack-orchestrator em F3 (sem HARD STOP).

---

## Category 6 — Acceptance Validation

Can run parallel with Category 7. Use quickstart.md scenarios as the validation checklist.

- [X] **6.1** Run quickstart Scenario A against a test project (`projects/test-determinism/` or `projects/Meu-ERP/`) — config without `modernization_scope` — confirm pipeline runs identically to pre-feature, no step 0.5 emitted.
- [X] **6.2** [P] Run quickstart Scenario B — `scope=partial`, `target_modules: []` — confirm the `DECISION: BLOCKED` pre-flight box is emitted and no F1 agent is dispatched.
- [X] **6.3** [P] Run quickstart Scenario C — `scope=partial`, `target_modules: ["financeiro"]` — confirm step 0.5 dispatches `ava-tobe-coexistence-strategy` and F3 log shows `⏭` for non-listed BCs.
- [X] **6.4** [P] Run PowerShell validation commands from quickstart.md Scenarios E, F, G:
  ```powershell
  # Scenario E — config fields present
  Select-String "projects/_template/context/project-config.yaml" -Pattern "modernization_scope"
  Select-String "projects/_template/context/project-config.yaml" -Pattern "target_modules"
  # Scenario F — docs present
  Select-String "docs/full-pipeline-guide.md" -Pattern "Strangler Fig"
  Select-String "README.md" -Pattern "moderniz"
  # Scenario G — CHANGELOG entries
  Select-String "CHANGELOG.md" -Pattern "1\.3\.0"
  Select-String "CHANGELOG.md" -Pattern "1\.8\.0"
  ```

---

## Category 7 — Documentation & CHANGELOG

Can run parallel with Category 6.

- [X] **7.1** Add the `## 🌿 Modernização Parcial (Strangler Fig Pattern)` section to `docs/full-pipeline-guide.md`, inserted before the existing `## 🆚 Comparação: SA vs FP` section (current line ~271). Section must contain all 7 sub-sections defined in plan.md §Phase 3a: Quando usar, Configuração, O que muda no pipeline, Diagrama, Passo a passo, Zonas de migração, Graduating de parcial para completo. *(PBI 2320)*
- [X] **7.2** [P] Add the partial modernization callout to `README.md`, after the `| **TOTAL** | **55** |` KPI table row and before `## Stack — Totalmente Configurável`. Callout text: `> 🌿 **Modernização Parcial (Strangler Fig)**: ...` linking to the new guide section (plan.md §Phase 3b). *(PBI 2321)*
- [X] **7.3** [P] Add CHANGELOG entries under `## [Unreleased]` in `CHANGELOG.md` for `ava-master-orchestrator 1.3.0 (MINOR)` and `ava-stack-orchestrator 1.8.0 (MINOR)` as specified in plan.md §Phase 4. *(PBI 2316)*

---

## Completion Checklist

- [X] All categories complete (Categories 3 and 4 intentionally N/A)
- [X] `project-config.yaml` template has both new fields with inline Portuguese comments
- [X] `master-orchestrator.md` version = `1.3.0`; steps 0.3a/0.3b/0.3c present; Step 0.5 box in diagram; conditional Agent Team row; Input Contract updated
- [X] `orchestrator-stack.md` version = `1.8.0`; step 0.3c present; BC filter block before first dispatch
- [X] Backward-compat confirmed: agent-body handles absent `modernization_scope` as `"full"`
- [X] `docs/full-pipeline-guide.md` — "Modernização Parcial" section with 7 sub-sections
- [X] `README.md` — partial modernization callout present
- [X] `CHANGELOG.md` — entries for v1.3.0 and v1.8.0
- [X] Quickstart scenarios A–G all pass (Category 6)
