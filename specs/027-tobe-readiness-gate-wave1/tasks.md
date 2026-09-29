# Agent Development Tasks: ava-tobe-orchestrator — Readiness Gate Wave 1

**Plan**: `specs/027-tobe-readiness-gate-wave1/plan.md`
**Agent ID**: `ava-tobe-orchestrator` | **Phase**: `F2` | **Module**: `tobe-architecture`

> **Change Type**: `modify-existing` — 9 string patches to a single file.
> Complete categories sequentially. All tasks touch `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`.

---

## Category 1 — Frontmatter Update

Must complete before any other category. Unblocks Categories 2–7.

- [X] **1.1** Apply **E1** — In `orchestrator-tobe.md` frontmatter, update `version: "2.4.1"` → `version: "2.5.0"` and `date: 2026-07-13` → `date: 2026-07-22`

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. Apply all 8 content edits to `orchestrator-tobe.md`.

- [X] **2.1** Apply **E2** — Add `ava-readiness-gate` row to `## Agent Team Gerenciado` table after the `| Azure Infra Estimator TO-BE | 8 — Estimativa de infraestrutura Azure |` row:
  ```
  | Readiness Gate (`ava-readiness-gate`) | **8.1 — Gate de Readiness (Pré-Build Cycle, Wave 1)** |
  ```

- [X] **2.2** Apply **E3** — Insert the complete `### Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle)` section (see `plan.md §8.1` for full text in pt-BR) **before** `### Gate F2→F3 — Requestor Inspection & Validation` (line 1452). The section must include:
  - `⛔ Read(src/modules/ava-fabric-agents/shared/readiness-gate.md) OBRIGATÓRIO` dispatch line
  - Idempotency check block (`> ⚠️ **Gate Idempotente**`)
  - `wave_number: 1` hardcoded declaration
  - Decision table (APPROVED / CONDITIONAL / BLOCKED actions)
  - BLOCKED invariant (`⛔ **INVARIANTE ABSOLUTA (BLOCKED)**`)
  - artifact-only-consumption-protocol reference
  - Completion checklist (5 items)

- [X] **2.3** Apply **E4** — Update `### TODO Items` header from `(contrato fixo — 14 items)` to `(contrato fixo — 15 items)` in `orchestrator-tobe.md`

- [X] **2.4** Apply **E4b** — Add row 15 to the TODO Items table after row 14 (`wcr`):
  ```
  | 15 | `readiness-gate` | Execute Fase 8.1 — Readiness Gate Wave 1 | Step 3 | ava-readiness-gate gate_decision APPROVED ✓ |
  ```

- [X] **2.5** Apply **E4c** — In `### Regras de atualização`, change `Emitir \`TodoWrite\` com TODAS as 14 tasks` → `TODAS as 15 tasks`

- [X] **2.6** Apply **E5** — In `## Agent Completion Registry`, append `, \`ava-readiness-gate\`` at the end of the `**Agent IDs:**` line (after `ava-tobe-azure-infra`)

- [X] **2.7** [P] Apply **E6** — Add `ava-readiness-gate | 8.1-Gate` row after **each** `ava-tobe-azure-infra | 8-Del` row in the **FULL MICRO table** (2 occurrences: Reasoning Approach ~line 1880 and Execution Timing Output ~line 2175):
  ```
       | ava-readiness-gate            | 8.1-Gate  | [STATUS]  | [PREENCHER: ISO-03:00]  | [PREENCHER: ISO-03:00]  | [Xm Ys] |
  ```

- [X] **2.8** [P] Apply **E7** — Add `ava-readiness-gate | 8.1-Gate` row after **each** `ava-tobe-azure-infra | 8-Del` row in the **STATUS_ONLY MICRO table** (2 occurrences: Reasoning Approach ~line 1912 and Execution Timing Output ~line 2213):
  - For pipe-table (Reasoning Approach): `| ava-readiness-gate            | 8.1-Gate  | [STATUS] |`
  - For box-drawing table (Execution Timing Output): `  │ ava-readiness-gate            │ 8.1-Gate  │ ✅/❌/⏳ │`

---

## Category 3 — Shared Schema Updates

**SKIP** — plan.md §7 confirms no schema changes.

---

## Category 4 — Module Registration

**SKIP** — `modify-existing` change; `module.yaml` entry for `ava-tobe-orchestrator` already exists in `src/modules/ava-fabric-agents/tobe-architecture/module.yaml`. No registration needed.

---

## Category 5 — Quality Gate Checklists

Depends on Category 2. Verify internal consistency of the modified file.

- [X] **5.1** Verify the `### Fase 8.1` checklist (inserted in 2.2) contains exactly 5 `- [ ]` items:
  1. Idempotência verificada
  2. `readiness-gate-status.json` exists
  3. `readiness-gate-report.md` exists
  4. `gate_decision == "APPROVED"` (novo ou cacheado) or CONDITIONAL with PM confirm
  5. If BLOCKED → all downstream steps NÃO executados

- [X] **5.2** Verify that none of the following existing sections were accidentally modified or removed:
  - `### Gate F2→F3 — Requestor Inspection & Validation`
  - `### Gate 8→Build Cycle — Migration Design Checklist`
  - `### Step F1 — Strategy Align`
  - `### Step F2 — Package Approval Document`

- [X] **5.3** Verify the idempotency condition is correctly stated: file exists AND `gate_decision == "APPROVED"` → skip; `gate_decision == "CONDITIONAL"` → re-invoke

---

## Category 6 — Acceptance Validation

Depends on Category 2. Run grep checks per `plan.md §10 Quickstart Validation`.

- [X] **6.1** **E1 check** — Verify version bump:
  ```powershell
  Select-String 'version: "2.5.0"' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
  # Expected: 1 match
  ```

- [X] **6.2** **E2 check** — Verify Agent Team row:
  ```powershell
  Select-String 'ava-readiness-gate' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md | Select-Object -First 2
  # Expected: row in Agent Team table present
  ```

- [X] **6.3** **E3 check** — Verify Fase 8.1 section is present and positioned before Gate F2→F3:
  ```powershell
  $f = "src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md"
  $fase81 = (Select-String '### Fase 8.1' $f).LineNumber
  $gateF2 = (Select-String '### Gate F2→F3' $f).LineNumber
  # Expected: $fase81 -lt $gateF2
  ```

- [X] **6.4** **E4/E4b/E4c check** — Verify TODO table has 15 items:
  ```powershell
  Select-String 'contrato fixo — 15 items' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
  Select-String 'readiness-gate.*Wave 1' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
  # Expected: 1 match each
  ```

- [X] **6.5** **E5 check** — Verify Agent IDs list includes ava-readiness-gate:
  ```powershell
  Select-String 'ava-readiness-gate' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md | Measure-Object | Select-Object Count
  # Expected: ≥9 matches total
  ```

- [X] **6.6** **E6/E7 check** — Verify 8.1-Gate appears in all 4 timing tables:
  ```powershell
  Select-String '8.1-Gate' src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
  # Expected: ≥4 matches (2 FULL + 2 STATUS_ONLY)
  ```

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6.

- [X] **7.1** [P] Add `CHANGELOG.md` entry:
  ```
  ## [2.5.0] — 2026-07-22
  ### Changed
  - `ava-tobe-orchestrator` (v2.4.1 → v2.5.0): Added Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle).
    Invokes `ava-readiness-gate` with `wave_number: 1` after Phase 8 (Azure Infra Estimator) and before
    Gate F2→F3 (Requestor Inspection). Gate is idempotent (skips if APPROVED cached). BLOCKED decision
    halts all subsequent F3-transition steps (Gate F2→F3, Migration Design Checklist, Strategy Align,
    Package Approval).
  ```

- [X] **7.2** [P] Update `docs/agents-catalog.md` — find the `ava-tobe-orchestrator` entry and change version from `2.4.1` to `2.5.0`

- [X] **7.3** [P] Check `docs/full-pipeline-guide.md` for any F2 pipeline flow diagram or description that lists end-of-F2 gates — if found, add a note that Fase 8.1 (Readiness Gate) now precedes Gate F2→F3

---

## Completion Checklist

- [X] Category 1 complete (E1 — frontmatter version bump)
- [X] Category 2 complete (E2–E7 — all 8 content patches applied)
- [X] Category 3 SKIPPED (no schema changes)
- [X] Category 4 SKIPPED (modify-existing, module.yaml unchanged)
- [X] Category 5 complete (internal consistency verified)
- [X] Category 6 complete (all 6 grep validations pass)
- [X] Category 7 complete (CHANGELOG + catalog + guide updated)
- [X] No `[NEEDS CLARIFICATION]` markers remain in `orchestrator-tobe.md`
- [X] Existing sections (Gate F2→F3, Gate 8→Build Cycle, Steps F1/F2) unchanged
- [X] `CHANGELOG.md` entry committed
- [X] `docs/agents-catalog.md` updated
