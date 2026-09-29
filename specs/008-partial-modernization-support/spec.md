# Agent Specification: Partial Modernization Support — Strangler Fig Pattern

**Feature Branch**: `008-partial-modernization-support`
**Created**: 2026-07-09
**Status**: Draft
**PBI**: 2316
**Change Type**: modify-existing (multi-file — MINOR version bumps)
**Input**: "Adicionar suporte à modernização parcial ao pipeline IMFAI: campo
modernization_scope no project-config, branch de roteamento no master-orchestrator,
e documentação de uso (Strangler Fig pattern)."

> **Language note**: This spec is a planning document written in **English**.
> Agent body implementations (category 2 tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Change Identity

| Field            | Value |
|------------------|-------|
| **Change Type**  | `modify-existing` — no new agent files |
| **Phase(s)**     | F2 (TO-BE arch), F3 (codegen), Config (project-config template), Docs |
| **Scope**        | Cross-cutting: config schema + 2 agent files + 2 doc files |
| **Version Bumps** | `ava-master-orchestrator`: `1.2.0` → `1.3.0` (MINOR: new routing branch) |
|                  | `ava-stack-orchestrator`: current → +MINOR (new `target_modules` gate) |

### Target Files

| # | File | Change |
|---|------|--------|
| 1 | `projects/_template/context/project-config.yaml` | Add `modernization_scope` + `target_modules` fields |
| 2 | `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md` | Add `partial` routing branch |
| 3 | `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` | Add `target_modules` filter guard |
| 4 | `docs/full-pipeline-guide.md` | Add "Modernização Parcial" section |
| 5 | `README.md` | Add link to partial modernization guide |

> **`modify-existing` notes:**
> - No new agent `.md` files. No new module.yaml entries needed.
> - SKILL.md files unchanged (routing logic lives in agent `.md`, not SKILL.md — Article XI).
> - `CHANGELOG.md` entry required for each MINOR bump (Article X).

---

## 2. Problem Statement

The `ava-tobe-coexistence-strategy` agent exists in F2 but is only dispatched as
**step 4.3 of the full pipeline** (`ava-tobe-orchestrator`). Teams that want to
modernize a **single bounded context** without executing the complete F1→F2→…→F6
pipeline have no supported entry point.

### Current gaps

| # | Gap | Impact |
|---|-----|--------|
| G1 | No `modernization_scope` field in `project-config.yaml` | Teams manually fork the pipeline; config is undocumented |
| G2 | `master-orchestrator` has no `partial` routing branch | Cannot trigger coexistence-strategy early |
| G3 | F3 codegen ignores `target_modules` | Generates code for ALL BCs even when only one is in scope |
| G4 | No usage documentation for partial mode | Onboarding friction; Strangler Fig pattern unguided |

---

## 3. Solution Overview

```
project-config.yaml
  modernization_scope: full | partial   ← new field (default: "full")
  target_modules: [BC1, BC2]            ← new field (used when scope=partial)
         │
         ▼
master-orchestrator reads modernization_scope
         │
    ┌────┴──────────────────┐
    │ scope == "partial"    │
    │                       │
    ▼                       ▼
ava-tobe-coexistence-strategy    (normal F1→F2→… pipeline)
  (dispatched BEFORE F2)
         │
         ▼
F2 proceeds with coexistence strategy already resolved
         │
         ▼
F3 stack-orchestrator reads target_modules
→ skips BCs NOT in target_modules list
```

---

## 4. Field Specification — `project-config.yaml`

### `modernization_scope`

```yaml
# modernization_scope: Define o escopo da modernização.
#   "full"    → Pipeline completo F1→F2→F3→F5→F7→F6 (default).
#               Todos os bounded contexts são processados.
#   "partial" → Modernização incremental via Strangler Fig pattern.
#               Apenas os BCs em target_modules são migrados.
#               Ativa: coexistence-strategy ANTES de F2 (passo 0.5).
modernization_scope: "full"
```

### `target_modules`

```yaml
# target_modules: Lista de bounded contexts a modernizar (usado quando
#   modernization_scope = "partial").
#   Formato: lista YAML de strings correspondentes aos IDs de BC em
#   scope_modules.
#   Exemplo: ["financeiro", "cadastro"]
#   Ignorado quando modernization_scope = "full".
target_modules: []
```

**Validation rules** (enforced by master-orchestrator pre-flight):
1. If `modernization_scope == "partial"` and `target_modules` is empty → HARD STOP with error message.
2. If `modernization_scope == "full"` and `target_modules` is non-empty → WARN (ignored) and proceed.
3. `target_modules` entries must be a subset of `scope_modules` when `scope_modules ≠ "all"`.

---

## 5. Master-Orchestrator Routing Branch (partial mode)

### Step 0.5 — inserted between PRE-FLIGHT and F1

When `modernization_scope == "partial"`:

```
┌─── PASSO 0.5 — Coexistence Strategy (partial mode) ────────────────────────┐
│  ▶ @ava-tobe-coexistence-strategy                                           │
│  on(coexistence-strategy ✓) → proceed to F1                                │
└────────────────────────────────────────────────────────────────────────────┘
```

The coexistence strategy output (`coexistence-strategy.md`) is written to
`projects/{project_name}/outputs/tobe/docs/` BEFORE F1 runs, so the AS-IS
orchestrator can cross-reference migration zones (Z1/Z2/Z3) during analysis.

### Pre-flight validation block (partial mode only)

```
╔══════════════════════════════════════════════════════════════════════╗
║  PARTIAL MODERNIZATION MODE — PRE-FLIGHT                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  modernization_scope: partial                                       ║
║  target_modules: {list}                                             ║
║  coexistence-strategy: [will run at step 0.5]                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  DECISION: [PROCEED | BLOCKED]                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Version bump

`ava-master-orchestrator`: `1.2.0` → `1.3.0`
- Reason: new routing branch and pre-flight block (backward-compatible MINOR).

---

## 6. F3 Stack-Orchestrator `target_modules` Gate

### Guard logic

When `modernization_scope == "partial"` and `target_modules` is non-empty:

```
For each BC in codegen queue:
  IF bc_id NOT IN target_modules:
    SKIP bc_id — log: "⏭ BC '{bc_id}' fora de target_modules — ignorado."
  ELSE:
    proceed with codegen for bc_id
```

The guard runs **after** the Stack-Orchestrator pre-flight and **before** any
BC-level codegen agent is dispatched. No BC outside `target_modules` receives
a codegen dispatch.

### Gate output

The Stack-Orchestrator emits a table in its execution log:

| BC ID | In `target_modules`? | Action |
|-------|----------------------|--------|
| `financeiro` | ✅ | Codegen dispatched |
| `rh` | ❌ | Skipped — partial mode |
| `cadastro` | ✅ | Codegen dispatched |

---

## 7. User Scenarios (Given-When-Then)

### Scenario 1 — Partial scope: valid config, coexistence strategy dispatched (P1)

**Story**: Como arquiteto de migração, quero executar o pipeline com
`modernization_scope: partial` e `target_modules: ["financeiro"]` para que apenas
o BC financeiro seja modernizado e a estratégia de coexistência seja resolvida
antes de F2.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `modernization_scope: partial` and
   `target_modules: ["financeiro"]`, **When** `ava-master-orchestrator` starts,
   **Then** it displays the partial mode pre-flight block and dispatches
   `ava-tobe-coexistence-strategy` at step 0.5 before F1.
2. **Given** step 0.5 completes, **Then** `coexistence-strategy.md` exists in
   `outputs/tobe/docs/` before `ava-asis-orchestrator` runs.
3. **Given** F3 stack-orchestrator runs with `target_modules: ["financeiro"]`,
   **Then** only the `financeiro` BC receives a codegen dispatch; all other BCs
   are logged as skipped.

---

### Scenario 2 — Partial scope: empty `target_modules` → HARD STOP (P1)

**Story**: Dado que o scope é partial mas `target_modules` está vazio, o
orchestrator deve bloquear a execução com mensagem clara.

**Acceptance Scenarios**:

1. **Given** `modernization_scope: partial` and `target_modules: []`,
   **When** the master-orchestrator runs pre-flight, **Then** it emits
   `DECISION: BLOCKED` and the error:
   `"modernization_scope=partial requer target_modules não-vazio."`.
2. **Given** the HARD STOP, **Then** no F1 agent is invoked and no output files
   are created.

---

### Scenario 3 — Full scope: `target_modules` field present but ignored (P2)

**Story**: Dado que o scope é full e `target_modules` está preenchido (configuração
errônea), o orchestrator deve avisar mas prosseguir normalmente.

**Acceptance Scenarios**:

1. **Given** `modernization_scope: full` and `target_modules: ["financeiro"]`,
   **When** the master-orchestrator reads config, **Then** it emits a WARN:
   `"target_modules ignorado: modernization_scope=full processa todos os BCs."`.
2. **Given** the WARN, **Then** the pipeline proceeds with the full sequence
   (no step 0.5, no BC filtering in F3).

---

### Scenario 4 — Full scope: default behavior unchanged (P1)

**Story**: Dado que `modernization_scope` não está definido (campo ausente ou "full"),
o pipeline executa de forma idêntica ao comportamento anterior.

**Acceptance Scenarios**:

1. **Given** an existing `project-config.yaml` without `modernization_scope`,
   **When** the master-orchestrator reads config, **Then** it defaults to `full`
   and follows the original pipeline sequence without step 0.5 or any BC filtering.
2. **Given** `modernization_scope: full` (explicitly set), **Then** same behavior
   as above — fully backward-compatible.

---

## 8. Documentation Changes

### `docs/full-pipeline-guide.md` — New section

Add section **"Modernização Parcial (Strangler Fig Pattern)"** containing:
- Explanation of when to use partial mode vs. full pipeline
- Step-by-step: how to configure `modernization_scope` and `target_modules`
- Example `project-config.yaml` snippet for partial mode
- Pipeline diagram showing step 0.5 insertion
- Migration zones (Z1/Z2/Z3) cross-reference from `ava-tobe-coexistence-strategy`
- Graduation protocol: moving from partial to full migration

### `README.md` — New link

Add a "Modernização Parcial" link in the **Getting Started** or **Pipeline** section
pointing to the new guide section in `docs/full-pipeline-guide.md`.

---

## 9. Quality Gate Requirements

- [x] Change type is `modify-existing` — no new agent IDs (Article IV N/A for new registration)
- [x] SKILL.md files unchanged — routing in agent `.md` only (Article XI)
- [x] `project-config.yaml` new fields documented with inline comments in Portuguese (Article I)
- [x] `modernization_scope` defaults to `"full"` — fully backward-compatible (Article X)
- [x] Pre-flight validation blocks specified for partial mode (Constitution §Pre-implementation Gates)
- [x] BDD scenarios cover: nominal partial, HARD STOP, ignored field, and backward-compat (Article VI)
- [x] Security sub-pipeline impact: NONE — partial mode does not skip security sub-pipeline in F1 (Article VII)
- [x] No technology versions hardcoded in spec (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] CHANGELOG.md entries required for `master-orchestrator` v1.3.0 and `stack-orchestrator` MINOR bump

---

## 10. Dependencies

| Dependency | File | Reason |
|---|---|---|
| `ava-tobe-coexistence-strategy` | `src/modules/ava-fabric-agents/tobe-architecture/agents/coexistence-strategy-tobe.md` | Must exist (already present) — dispatched at step 0.5 |
| `ava-stack-orchestrator` | `src/modules/ava-fabric-agents/tech-stack/agents/stack-orchestrator.md` | Receives `target_modules` gate |
| `project-config.yaml` template | `projects/_template/context/project-config.yaml` | Schema source |

---

## 11. Assumptions

1. `ava-tobe-coexistence-strategy` already handles being invoked standalone (before F2) — no changes needed to that agent.
2. `scope_modules: "all"` + `modernization_scope: "partial"` is a valid combination: `target_modules` names the partial subset even when the full codebase is in scope.
3. The Stack-Orchestrator already has a BC-level dispatch loop — adding a guard before the loop requires a MINOR edit only.
4. `full-pipeline-guide.md` exists and has an identifiable section structure for insertion.
