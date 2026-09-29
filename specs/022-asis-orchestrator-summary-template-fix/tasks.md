# Agent Development Tasks: ava-asis-orchestrator â€” SAS Hook Summary Template Fix

**Plan**: `specs/022-asis-orchestrator-summary-template-fix/plan.md`
**Agent ID**: `ava-asis-orchestrator` | **Phase**: `F1` | **Module**: `asis-diagnostic`
**Change Type**: `bugfix` (PATCH `2.20.0 â†’ 2.20.1`)

> This is a PATCH bugfix. Categories 1 (frontmatter), 3 (schemas), 4 (module registration),
> and 5 (checklists) are N/A â€” the agent already exists, contracts are unchanged, and
> no registration is needed. Only Categories 2 and 6 require work.
> All tasks are in the single file:
> `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`

---

## Category 1 â€” Agent Frontmatter & Contract Definition

*Partially applicable â€” only the version/date fields need updating.*

- [X] **1.1** In `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` frontmatter, change `version: "2.20.0"` â†’ `version: "2.20.1"`
- [X] **1.2** In the same frontmatter, change `date: 2026-07-15` â†’ `date: 2026-07-21`

---

## Category 2 â€” Agent Behavior & Instructions

*Core fix. Depends on Category 1.*

- [X] **2.1** In `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`, locate the **"## Hook: AVA Summary"** section (currently ~line 2011)
- [X] **2.2** Replace the section body with the new content from plan Â§8 Phase 1:
  - Keep the code block `â†’ ava-summary | trigger: SAS` unchanged
  - Add the `â›” OBRIGATÃ“RIO` mandate block forbidding inline HTML generation and requiring `build_summary_comprehensive.py --project {project_name}`
  - Add the `success_criteria` YAML block: `Summary HTML contains "AVA Fabric Summary Template v1.0"` + `Summary HTML size > 150 KB`
  - Add the **ValidaÃ§Ã£o pÃ³s-execuÃ§Ã£o** block: `âœ… Summary template OK` on success; `âš ï¸ SUMMARY TEMPLATE MISMATCH â€” invocar @ava-summary-remediation para reconstruir` on failure
  - Preserve the final sentence: "O Summary Agent Ã© opcional â€” pode ser pulado se o usuÃ¡rio digitar `SKIP`. Ao pular: omitir o despacho de `ava-summary` e toda a validaÃ§Ã£o acima."
- [X] **2.3** [P] Verify the FP workflow section ("## Workflow: Full Pipeline") is **not** modified â€” it already has the correct `success_criteria` block

---

## Category 3 â€” Shared Schema Updates

*N/A â€” plan Â§7 confirms no schema changes.*

---

## Category 4 â€” Module Registration

*N/A â€” `ava-asis-orchestrator` already registered in `asis-diagnostic/module.yaml`. PATCH bump does not require re-registration.*

---

## Category 5 â€” Quality Gate Checklists

*N/A â€” no new checklist items; the fix adds a runtime validation instruction, not a new checklist gate.*

---

## Category 6 â€” Acceptance Validation & QA Integration

*Depends on Category 2.*

- [X] **6.1** Run grep tests from plan Â§10 to verify the fix is present:
  - `grep -n "build_summary_comprehensive.py"` in `orchestrator-asis.md` â†’ expect â‰¥2 matches (SAS hook + FP workflow)
  - `grep -n "success_criteria"` in `orchestrator-asis.md` â†’ expect â‰¥2 matches
  - `grep -n "AVA Fabric Summary Template"` in `orchestrator-asis.md` â†’ expect â‰¥2 matches
  - `grep -n "SUMMARY TEMPLATE MISMATCH"` in `orchestrator-asis.md` â†’ expect â‰¥1 match
  - `grep -n "SKIP"` in the Hook section â†’ must be present (backward-compat preserved)
  - `grep -n "^version:"` in frontmatter â†’ must return `"2.20.1"`
- [X] **6.2** [P] Confirm the FP workflow `success_criteria` block is unchanged (regression check)

---

## Category 7 â€” CHANGELOG & Release Notes

*Depends on Category 2 completing successfully.*

- [X] **7.1** Prepend to `CHANGELOG.md` the following entry:

  ```markdown
  ## [2026-07-21] â€” F1 Orchestrator: Summary hook agora exige template via script (022-asis-orchestrator-summary-template-fix)

  - **ava-asis-orchestrator v2.20.1** (PATCH)
  - Problema: ao executar em modo SA, o hook `SAS` despachava `ava-summary` sem
    mandar usar `build_summary_comprehensive.py`, permitindo geraÃ§Ã£o HTML inline
    nÃ£o-conforme com o template AVA Fabric.
  - Fix: seÃ§Ã£o "Hook: AVA Summary" inclui agora instruÃ§Ã£o obrigatÃ³ria de uso do
    script, bloco `success_criteria` (assinatura + tamanho > 150 KB) e validaÃ§Ã£o
    pÃ³s-execuÃ§Ã£o com aviso `âš ï¸ SUMMARY TEMPLATE MISMATCH` quando a assinatura nÃ£o
    Ã© encontrada. Modo SKIP inalterado.
  ```

---

## Dependencies

```
Category 1  (frontmatter version bump)
    â””â”€â”€ Category 2  (hook section body fix)
            â”œâ”€â”€ Category 6  (grep validation tests)  [parallelizable within Cat 6]
            â””â”€â”€ Category 7  (CHANGELOG entry)
```

Categories 3, 4, 5 are skipped entirely (N/A for PATCH bugfix on existing agent).

---

## Parallel Execution

After Category 2 completes, tasks 6.1 and 6.2 can run in parallel.

---

## Implementation Strategy

**MVP**: Tasks 1.1 â†’ 1.2 â†’ 2.1 â†’ 2.2 â†’ 6.1 â†’ 7.1 (in order).
Task 2.3 and 6.2 are regression checks that run alongside 6.1.
Total: **8 tasks** across 3 active categories.

