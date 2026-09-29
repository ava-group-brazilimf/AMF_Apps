# Agent Specification: ava-asis-orchestrator (bugfix — summary template non-compliance on auto dispatch)

**Feature Branch**: `022-asis-orchestrator-summary-template-fix`
**Created**: 2026-07-21
**Status**: Draft
**Change Type**: `bugfix`
**Input**: Sistema: MeuERP. Problema: Ao executar o agente summary de forma automática pelo orquestrador AS-IS, o sumário gerado não seguiu o layout template do sumário.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-asis-orchestrator` |
| **Version** | `1.x.x → PATCH bump` |
| **Phase** | `F1` |
| **Module** | `asis-diagnostic` |
| **Role** | Coordinates the full AS-IS diagnostic pipeline and dispatches `ava-summary` at completion |
| **Skill** | `ava-asis-orchestrator` |
| **Dispatch** | user-facing via SKILL.md and internally as the F1 coordinator |

> **Change Type is `bugfix`**:
> - Existing file: `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`
> - Version bump type: **PATCH** (behaviour fix — no contract change)
> - `module.yaml` entry already exists — Category 4 tasks are N/A
> - SKILL.md already exists — Category 1.5 is N/A

---

## 2. Problem Statement

### Observed Behaviour

When the AS-IS orchestrator completes the diagnostic pipeline and automatically dispatches `ava-summary` (via the **"Hook: AVA Summary"** section using trigger `SAS`), the generated Summary HTML does **not** follow the AVA Fabric template layout (`build_summary_comprehensive.py`).

Evidence (attached screenshot) shows the summary rendered with the correct visual structure only when the agent is invoked manually. In automatic dispatch (SAS trigger from the orchestrator), the agent may bypass or not correctly invoke `build_summary_comprehensive.py`, resulting in non-compliant HTML output.

### Root-Cause Hypothesis

The "Hook: AVA Summary" section of `orchestrator-asis.md` dispatches `ava-summary | trigger: SAS` with a single-line instruction but **does not explicitly mandate** that `build_summary_comprehensive.py` must be executed — it only says the hook is optional. This leaves the summary agent free to generate HTML inline (without the script), producing layout that does not match the official AVA Fabric template.

In contrast, the **FP (Full Pipeline)** workflow explicitly calls `@ava-summary | GS` with the instruction *"Validar assinatura do template no HTML gerado"* and includes a `success_criteria` block that checks for `"AVA Fabric Summary Template v1.0"` in the output — creating an implicit enforcement path absent from the `SAS` hook.

### Distinction Between Triggers

| Trigger | Path | Template enforced? |
|---------|------|--------------------|
| `GS` (FP workflow) | Step 4 in "Workflow: Full Pipeline" | ✅ Yes — explicit `success_criteria` |
| `SAS` (auto hook after SA) | "Hook: AVA Summary" section | ❌ No — no enforcement |

---

## 3. Agent Frontmatter (no change)

The frontmatter of `orchestrator-asis.md` is not modified; only the **Hook: AVA Summary** section body is updated. Version bump is PATCH.

---

## 4. Output Contract (no change)

The `ava-asis-orchestrator` output contract is unchanged. The fix affects only the dispatch instruction for `ava-summary`, not the orchestrator's own artifacts.

---

## 5. User Scenarios (Given-When-Then)

> Story descriptions are in Brazilian Portuguese; acceptance scenarios in English for BDD traceability.

### Scenario 1 — Nominal: Summary uses template on automatic SAS dispatch (Priority: P1)

**Story**: Como responsável pela esteira de migração, quero que o agente `ava-summary` sempre gere o Summary HTML usando o script `build_summary_comprehensive.py` quando acionado automaticamente pelo `ava-asis-orchestrator`, para que o layout do relatório seja sempre o template padrão AVA Fabric.

**Why this priority**: Direct user impact — incorrect layout breaks trust and readability of the AS-IS diagnostic report.

**Acceptance Scenarios**:

1. **Given** the AS-IS orchestrator completes the full SA workflow, **When** it auto-dispatches `ava-summary | SAS`, **Then** `ava-summary` MUST invoke `build_summary_comprehensive.py` as its primary HTML generation step.
2. **Given** the above, **When** the HTML is generated, **Then** the file contains the string `"AVA Fabric Summary Template v1.0"` (or the current canonical template signature).
3. **Given** the above, **When** the HTML is generated, **Then** the file size is > 150 KB.

---

### Scenario 2 — Validation: Template signature check blocks non-compliant output (Priority: P1)

**Story**: Como engenheiro de qualidade, quero que o orquestrador AS-IS valide a assinatura do template no HTML gerado após o Summary, para que um Summary não-conforme seja detectado e reportado antes de encerrar a execução.

**Acceptance Scenarios**:

1. **Given** `ava-summary | SAS` completes, **When** the orchestrator checks the output HTML, **Then** it verifies the template signature and emits `✅ Summary template OK` on success.
2. **Given** the output HTML does NOT contain the template signature, **When** the orchestrator checks, **Then** it emits a `⚠️ SUMMARY TEMPLATE MISMATCH` warning and suggests invoking `@ava-summary-remediation`.

---

### Scenario 3 — Parity: SAS and GS dispatch reach equivalent output quality (Priority: P2)

**Story**: Como desenvolvedor da esteira, quero que o caminho `SAS` (hook automático) gere um Summary equivalente ao caminho `GS` (Full Pipeline), para eliminar inconsistências entre execuções manuais e automáticas.

**Acceptance Scenarios**:

1. **Given** the same project artifacts, **When** the orchestrator dispatches via `SAS`, **Then** the generated Summary is structurally equivalent to a Summary generated via `GS` on the same project.
2. **Given** the above, **Then** both outputs pass the same 55-rule Summary Validator.

---

### Scenario 4 — Backward-compat: SKIP still works (Priority: P3)

**Story**: Como usuário avançado, quero poder digitar `SKIP` para pular o Summary após o SA, sem que a nova validação quebre o fluxo.

**Acceptance Scenarios**:

1. **Given** the user types `SKIP` after the orchestrator prompts, **When** the hook is reached, **Then** the orchestrator skips Summary dispatch gracefully and completes without error.

---

## 6. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | The "Hook: AVA Summary" section of `orchestrator-asis.md` MUST explicitly instruct that `ava-summary` MUST use `build_summary_comprehensive.py` (not inline HTML generation) when dispatched via `SAS`. |
| FR-02 | The dispatch instruction for `SAS` MUST include a `success_criteria` block identical to the one in the FP workflow (template signature check + file size > 150 KB). |
| FR-03 | After `ava-summary | SAS` returns, the orchestrator MUST verify that the generated HTML contains the template signature string `"AVA Fabric Summary Template v1.0"`. |
| FR-04 | If the template signature check fails, the orchestrator MUST emit a `⚠️ SUMMARY TEMPLATE MISMATCH` warning and provide the path to invoke `@ava-summary-remediation`. |
| FR-05 | The SKIP option MUST remain functional — when the user types `SKIP`, the orchestrator skips Summary dispatch and all associated validation steps. |
| FR-06 | The version field in the `orchestrator-asis.md` frontmatter MUST be bumped by PATCH (e.g., `1.x.y → 1.x.(y+1)`). |

---

## 7. Success Criteria

1. After the fix, a full AS-IS pipeline run (SA mode) generates a Summary HTML that contains `"AVA Fabric Summary Template v1.0"` 100% of the time.
2. The Summary HTML produced via automatic SAS dispatch is structurally equivalent to one produced via manual GS invocation on the same project.
3. The orchestrator emits a clear warning (not a silent failure) when the template check fails.
4. The SKIP workflow is unaffected — users who opt out of Summary do not encounter errors.
5. The fix touches only `orchestrator-asis.md` (PATCH bump) — no other agent files are modified.

---

## 8. Scope

**In scope**:
- Updating the **"Hook: AVA Summary"** section in `orchestrator-asis.md` to enforce `build_summary_comprehensive.py` and add the `success_criteria` block.
- Adding post-dispatch template signature validation logic in the orchestrator.
- PATCH version bump in `orchestrator-asis.md` frontmatter.

**Out of scope**:
- Changes to `summary-agent.md` itself.
- Changes to `build_summary_comprehensive.py`.
- Changes to any other orchestrator or phase agent.
- The FP workflow path (already enforces the template correctly).

---

## 9. Assumptions

- The `build_summary_comprehensive.py` script already produces compliant HTML with the correct template when called with the right arguments — it is not the source of the bug.
- The template signature string `"AVA Fabric Summary Template v1.0"` is the canonical marker written by `build_summary_comprehensive.py` into every generated HTML.
- The PATCH fix does not change any Input/Output contract, so no downstream agent adapters need updating.
- The `ava-summary-remediation` agent already handles post-hoc repair of non-compliant summaries and does not need changes.

---

## 10. Dependencies

| Artifact | Status |
|----------|--------|
| `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` | Exists — modify |
| `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` | Exists — read-only reference |
| `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` | Exists — read-only reference |
