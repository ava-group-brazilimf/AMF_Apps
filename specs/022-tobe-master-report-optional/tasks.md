# Agent Development Tasks: ava-tobe-orchestrator (bugfix)

**Plan**: `specs/022-tobe-master-report-optional/plan.md`
**Agent ID**: `ava-tobe-orchestrator` | **Phase**: `F2` | **Module**: `tobe-architecture`
**Change type**: bugfix — PATCH (`2.4.1` → `2.4.2`)

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Categories 3 and 4 are **N/A** (no schema changes; agent already registered).

---

## Category 1 — Frontmatter Version Bump

_Must complete before Category 2 body edits._

- [X] **1.1** Open `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` and confirm current `version: "2.4.1"` in frontmatter (line ~12)
- [X] **1.2** Replace `version: "2.4.1"` with `version: "2.4.2"` in the frontmatter block of `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`

---

## Category 2 — Agent Body Edits

_Depends on Category 1. All three edits are independent — apply with a single multi-replace call._

- [X] **2.1** Edit **Fase 0-Pre pre-condition** in `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` (line ~145):

  Replace:
  ```
  - **Pré-condição**: outputs AS-IS concluídos (`master-report.md`, `bounded-context-map.md`, `gaps-risks-report.md`)
  ```
  With:
  ```
  - **Pré-condição**: outputs AS-IS essenciais presentes — `bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md` (ver Gate SD); `master-report.md` é opcional — se ausente, emitir `[AVISO]` e prosseguir
  ```

- [X] **2.2** Edit **Trigger table SD gate** in `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` (lines ~1495–1496):

  Replace:
  ```
  > ⛔ **[SD] Gate Obrigatório — AS-IS Master Report**: Antes de qualquer execução do trigger `SD`, verificar se `projects/{project_name}/outputs/asis/master-report.md` existe. Se não existir → **PARAR IMEDIATAMENTE** com a mensagem:
  > `[GATE FAILED] AS-IS Master Report não encontrado. Execute o diagnóstico AS-IS (F1) antes de iniciar o design TO-BE`
  ```
  With:
  ```
  > ⚠️ **[SD] Verificação Opcional — AS-IS Master Report**: Antes de executar o trigger `SD`, verificar se `projects/{project_name}/outputs/asis/master-report.md` existe. Se não existir → emitir **aviso não-bloqueante**:
  > `[AVISO] master-report.md não encontrado. O pipeline TO-BE prosseguirá com os artefatos AS-IS disponíveis. Para gerar o relatório consolidado execute: @ava-asis-orchestrator trigger: SR`
  ```

- [X] **2.3** Edit **Reasoning Approach step 1** in `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` (line ~1810):

  Replace (just the opening clause up to the timing continuation `;`):
  ```
  1. **Validate** — **[GATE OBRIGATÓRIO — apenas trigger `SD`]** verificar se `projects/{project_name}/outputs/asis/master-report.md` existe; SE não existir → **PARAR IMEDIATAMENTE** com a mensagem: `[GATE FAILED] AS-IS Master Report não encontrado. Execute o diagnóstico AS-IS (F1) antes de iniciar o design TO-BE`;
  ```
  With:
  ```
  1. **Validate** — **[VERIFICAÇÃO OPCIONAL — apenas trigger `SD`]** verificar se `projects/{project_name}/outputs/asis/master-report.md` existe; SE não existir → emitir `[AVISO] master-report.md ausente — pipeline prosseguirá com artefatos AS-IS disponíveis` (**não interromper**); verificar artefatos essenciais (`bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md`) — SE todos ausentes → **PARAR IMEDIATAMENTE** com `[GATE FAILED] Artefatos essenciais do AS-IS não encontrados. Execute @ava-asis-orchestrator antes de iniciar o design TO-BE`;
  ```

---

## Category 3 — Shared Schema Updates

> **N/A** — no changes to `agent-task.schema.json` or `agent-result.schema.json`.

---

## Category 4 — Module Registration

> **N/A** — `ava-tobe-orchestrator` is already registered in `src/modules/ava-fabric-agents/tobe-architecture/module.yaml`. No new agent. No SKILL.md change.

---

## Category 5 — Quality Gate Checklists

- [X] **5.1** [P] Verify that after Edit 2.2, the `[@artifact-only-consumption-protocol](../../shared/artifact-only-consumption-protocol.md) §2.2` note on the line immediately after the SD gate block is **unchanged** (retained verbatim)
- [X] **5.2** [P] Confirm the `⚠️` symbol in Edit 2.2 renders correctly in the agent file (not escaped or corrupted)
- [X] **5.3** [P] Confirm `⛔` no longer appears anywhere in the SD gate block (lines ~1495–1500) — run: `Select-String -Path "src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md" -Pattern "GATE OBRIGATÓRIO — apenas trigger" | Select-Object Line`

---

## Category 6 — Acceptance Validation

_Depends on Category 2._

- [X] **6.1** **Scenario 1** — Validate non-blocking path: confirm `[GATE OBRIGATÓRIO — apenas trigger` no longer appears in `orchestrator-tobe.md` using grep search
- [X] **6.2** [P] **Scenario 1** — Confirm `[AVISO]` and `[VERIFICAÇÃO OPCIONAL` appear in the edited sections
- [X] **6.3** [P] **Scenario 2** — Backward compatibility: confirm the artifact-only-consumption-protocol escalation note is still present after the SD gate block
- [X] **6.4** [P] **Scenario 3** — Essential gate preserved: confirm `PARAR IMEDIATAMENTE` still appears in Reasoning Approach step 1 for the case where all essential artifacts are absent
- [X] **6.5** Validate against `quickstart.md` checklist — all 5 verification items pass

---

## Category 7 — Documentation & Catalog Update

_Can run parallel with Category 6._

- [X] **7.1** [P] Add `### Fixed` entry to `CHANGELOG.md` under the current `## [Unreleased]` section:
  ```
  ### Fixed
  - `ava-tobe-orchestrator` v2.4.2: Removida obrigatoriedade bloqueante de `master-report.md`
    no trigger `SD`. O arquivo passa a ser verificado com aviso não-bloqueante; o pipeline
    prossegue com os artefatos AS-IS presentes. Gate de artefatos essenciais
    (`bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md`)
    permanece bloqueante quando todos ausentes.
  ```
- [X] **7.2** [P] Update `docs/agents-catalog.md` — bump version entry for `ava-tobe-orchestrator` from `2.4.1` to `2.4.2`

---

## Completion Checklist

- [X] Category 1 complete — frontmatter shows `version: "2.4.2"`
- [X] Category 2 complete — 3 edits applied, verified by grep
- [X] Category 3 skipped (N/A)
- [X] Category 4 skipped (N/A)
- [X] Category 5 complete — escalation note intact, `⛔` removed from SD gate block
- [X] Category 6 complete — all 3 scenarios validated
- [X] Category 7 complete — `CHANGELOG.md` and `agents-catalog.md` updated
