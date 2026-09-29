# Agent Development Tasks: ava-summary-remediation

**Plan**: `specs/015-summary-remediation-agent/plan.md`
**Agent ID**: `ava-summary-remediation` | **Phase**: `F8` | **Module**: `summary`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.

---

## Category 1 — Agent Frontmatter & Contract Definition

- [ ] **1.1** Create `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`
- [ ] **1.2** Write YAML frontmatter: `name: "ava-summary-remediation"`, `version: "1.0.0"`, `description:` (pt-BR + "Ativa com:" phrases), `allowed-tools: Read, Write, Edit, Glob, Grep, Bash`
- [ ] **1.3** Write `## Output Contract` YAML block (`remediated_html`, `fix_report`, `fix_report_json` — see `spec.md` section 3)
- [ ] **1.4** Verify output path uses `projects/{project_name}/outputs/summary/`
- [ ] **1.5** Create `.github/skills/ava-summary-remediation/SKILL.md` — resolve `project_name`, read `agent-task-config.yaml` + `shared-context.md`, delegate to the agent `.md` (mirror `.github/skills/ava-summary/SKILL.md`)

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1.

- [ ] **2.1** Write **Responsibility** section: independent post-pipeline repair, idempotent, never overwrites existing `outputs/` artifacts
- [ ] **2.2** Write **Input Contract**: `project_name` (resolved via SKILL.md)
- [ ] **2.3** Write numbered Phase 0-7 instructions (pt-BR), adapting the `FS` draft (`summary (1).md`) plus the new **Phase 5 — Content/UI Guards** covering all 22 items in `spec.md`'s traceability table:
  - Phase 0 — Pre-flight & Audit (baseline validator run, artifact existence audit, D.* source integrity matrix, JSON schema validation, Markdown parser contract validation, Mermaid pre-validation, builder resources validation)
  - Phase 1 — Artifact Resolution (7 rules A-G from the `FS` draft, reused verbatim)
  - Phase 2 — Missing Diagram Synthesis (reused verbatim)
  - Phase 3 — Mermaid Sanitization (reused verbatim, calls `sanitize_mmd()`)
  - Phase 4 — Security Data Reconciliation (reused verbatim)
  - **Phase 5 — Content/UI Guards (NEW)** — for HTML built by a pre-fix builder version: apply the same suppression/removal logic as the permanent template fix (items 1-22), by re-running the (now-fixed) builder rather than patching HTML by hand
  - Phase 6 — Rebuild (`python build_summary_comprehensive.py --project {project_name}`)
  - Phase 7 — Re-validate + Fix Report (`python validate_summary.py --project {project_name}`, diff `FAILURES_BEFORE`/`FAILURES_AFTER`, write `remediation-report.md`/`.json`)
- [ ] **2.4** Write **Output Format** spec for `remediation-report.md` (before/after table, improvement %, synthesized-file list, pending items with `Rerun: @{agent}` pointers)
- [ ] **2.5** Add **Security Compliance** note: agent only reads/writes within `projects/{project_name}/outputs/`, never touches `.gitignore`, never commits/pushes
- [ ] **2.6** Write **Guardrails**: never overwrite an existing `outputs/` artifact; synthesized files tagged `# synthesized-by-FS — replace with output from @{agent}`; abort hard if `summary-template.html` is missing

---

## Category 3 — Shared Schema Updates

**SKIP** — no changes to `agent-task.schema.json` / `agent-result.schema.json` (plan.md section 7).

---

## Category 4 — Module Registration

Depends on Category 1.

- [ ] **4.1** Add agent entry to `src/modules/ava-fabric-agents/summary/module.yaml`:
  ```yaml
  - id: ava-summary-remediation
    file: agents/summary-remediation-agent.md
    skill: ava-summary-remediation
  ```
- [ ] **4.2** Bump `module.yaml` `version:` `1.0.0` → `1.1.0`
- [ ] **4.3** [P] Add row to `.github/copilot-instructions.md` under `### F8 — Summary`:
  `| `@ava-summary-remediation` | Repara exibição/dados de um Summary já gerado, sem re-executar a esteira |`

---

## Category 5 — Quality Gate Checklists

- [ ] **5.1** Add items to `src/shared/checklists/migration-design-checklist.md` (or the summary-specific checklist if one exists) covering: agent registered in module.yaml + SKILL.md exists + copilot-instructions row present (Agent registration protocol, Guardrail 12 of `summary-agent.md`)
- [ ] **5.2** [P] Verify `- [ ]` checkbox format matches existing checklist conventions

---

## Category 6 — Acceptance Validation & QA Integration

Depends on Category 2 and on Category "Permanent Fixes" (see note below — this category also covers the column-A fixes since they ship in the same PR).

> Note: unlike a typical single-agent feature, this feature also modifies three existing files
> (`summary-template.html`, `build_summary_comprehensive.py`, `validate_summary.py`). Those edits
> are tracked here as they are what Scenario 1/2 in `spec.md` actually validate.

- [ ] **6.1** Apply permanent template fixes to `summary-template.html` per the traceability table in `spec.md`:
  - [ ] **6.1a** [P] Unconditional removals: item 8 (Componentes FCID tile, `D.kpis` array), item 14b (Rules Categories card), item 14c (Screen Rules card + tab), item 15b (Complexidade table in Inventory & Metrics), item 19 (Artefatos AG-10 card), item 20 (BC TO-BE Aprovados/DDD/Squad cards + BCs Refinados table)
  - [ ] **6.1b** [P] `renderRisks()`: remove ID column (item 9)
  - [ ] **6.1c** Conditional hide-when-empty: `renderKPIs()` (items 1-7), `renderPatterns()` (item 10), `renderBC()` (item 11), submenu nav visibility for Functional Requirements (item 12) and Business Rules (item 13), Inventory & Metrics cards (item 15a), Test Baselines table (item 16), Banco de Dados AS-IS cards/Schema/SPs (items 17a-c)
  - [ ] **6.1d** Screen Flow Overview: remove agent-metadata cards (item 14a)
  - [ ] **6.1e** [P] Remove `AG-NN` token from bylines, `card-arts-ag*`/`card-bearts`/`card-fearts`/`card-scripts`/`card-pkgarts`/`card-demoarts`/`card-iac`/`card-protoarts` i18n keys (pt+en), and `AGENTS[]` display names (item 22)
- [ ] **6.2** Apply permanent builder fixes to `build_summary_comprehensive.py`:
  - [ ] **6.2a** `parse_tobebn()` fallback to `D.bizRules` when `tobe/docs/regras-negocio.md` absent (item 21)
  - [ ] **6.2b** [P] Remove `value-chain` from Deliverables classification (item 18b)
  - [ ] **6.2c** Root-cause investigation + parser fixes for items 1-4, 10, 11, 16, 17 where the cause is a format mismatch, not just missing data
- [ ] **6.3** Add `C11` category to `validate_summary.py` (`C11.1`-`C11.16`, one per row of the traceability table, plus `_fix_c11_*` functions where the check is auto-fixable at the HTML level)
- [ ] **6.4** Create `remediate_summary.py` implementing Phase 0-7 from Category 2
- [ ] **6.5** Level 1 — Unit: `python build_summary_comprehensive.py --project {test_project}` → `✅ SUCESSO!`, open HTML, visually confirm all 22 items fixed
- [ ] **6.6** Level 2 — Validation: `python validate_summary.py --project {test_project}` → exit 0, `C11.*` checks pass
- [ ] **6.7** Level 3 — Remediation standalone: run `@ava-summary-remediation` (or `remediate_summary.py`) against a pre-fix legacy HTML / a project with deliberately incomplete artifacts → confirm fix report, no pre-existing `outputs/` file overwritten
- [ ] **6.8** [P] Confirm CA02: repeat 6.5-6.6 on ≥2 projects with different legacy/target stacks
- [ ] **6.9** Confirm idempotency: re-run remediation on an already-clean summary → 0 changes reported

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6.

- [ ] **7.1** [P] Update `docs/agents-catalog.md` if it exists (ID, version, phase, module, role, output artifacts) — otherwise skip if the catalog does not track F8 agents individually
- [ ] **7.2** [P] Add `CHANGELOG.md` entry: new agent + display-fix summary + `C11` category addition
- [ ] **7.3** [P] Update `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`: correct rule count (from "~55" to the real total after `C11`), add `C11` to the category table, **do not** touch the pre-existing `C10` doc drift (out of scope)
- [ ] **7.4** [P] Verify `summary/module.yaml` diagram/comment (if any) reflects the new agent

---

## Completion Checklist

- [ ] All 7 categories complete
- [ ] `SKILL.md` created and routes correctly (Article XI)
- [ ] Agent `.md` frontmatter validated (name pattern, required fields only)
- [ ] `module.yaml` committed with version bump
- [ ] Agent validated: Level 1 + Level 2 + Level 3 all pass (Category 6)
- [ ] CA01 confirmed: every one of the 22 items verified visually absent/fixed
- [ ] CA02 confirmed: verified on ≥2 different-stack projects
- [ ] `docs/agents-catalog.md` updated (if applicable)
- [ ] `CHANGELOG.md` entry committed
- [ ] `.github/copilot-instructions.md` F8 table updated

---

## Addendum A (2026-07-10) — Console errors, AST extraction wiring

See `spec.md` Addendum A (items 23-33) and `plan.md` Addendum A. Tasks, mapped to the existing 7-category structure (no new categories needed — this is a bugfix/extension round, not a new agent):

- [x] **Category 2 (Agent Behavior)** — no change; the agent's Phase 0-7 body already covers this class of repair generically.
- [x] **Category 6 (Acceptance Validation)**:
  - [x] 6.10 Fix `sanitize_mmd()` → `_fix_seq_alias` non-idempotency (item 25)
  - [x] 6.11 Wire `ASIS_ARCH_BLUEPRINT_DIAGRAM` (item 26)
  - [x] 6.12 Fix `COMPLEX_METHODS`/`LAYER_COUNT`/`MODULE_COUNT` (item 27)
  - [x] 6.13 Fix `_read_project_config` YAML comment leak + add Phase 3 self-heal for items 23/24 (items 23-24)
  - [x] 6.14 Unify KPI hide-lists, add `kpi-layers`/`kpi-modules` (item 28)
  - [x] 6.15 Remove 3 tables (Arquivos por Tipo, Estrutura de Camadas, Complexidade Ciclomática) + `C11.18`/`C11.19` + `C11.10`/`C11.1`/`C11.2` rewrites (items 29-31, 33)
  - [x] 6.16 Wire `delphi-ast-raw/extraction/*.json` for Screen Flow (`parse_screen_forms_ast`), Inventory & Métricas (`parse_inventory_bc_breakdown` — new `D.invBcBreakdown` card), Test Baseline (`parse_test_map_ast`) (item 32, part 1)
  - [x] 6.17 Wire `delphi-ast-raw/extraction/*.json` for Banco de Dados AS-IS (Source E: `04_database_schemas.json` inferred tables, `05_procedures.json` stored_procedures), fix a real Gap List bug (`P0`-`P3` severity never mapped to complexity — `PRIORITY_TO_CPLX`), hide the MRS card when zero gaps (item 32, part 2)
  - [x] 6.18 Re-run Level 1-3 verification: `Meu-ERP-008-AST-LLM-Master-Orchestrator` → `✅ SUCCESS!`, `validate_summary.py` 84 passed/0 warn/0 error; `Meu-ERP-001` (no AST folder) → `✅ SUCCESS!`, no regression (2 pre-existing unrelated failures only: `C2.2`, `C3.7` — missing `complexity-map.md`/gantt diagram, both predate this feature)
- [x] **Category 7 (Documentation)**:
  - [x] 7.5 `CHANGELOG.md` entry for this addendum
  - [x] 7.6 Rule count references updated everywhere (82 → 84) — `validate_summary.py` docstring/comment, `summary-agent.md`, `summary-validate-agent.md`

### Addendum A.1 (2026-07-12) — Risk Register showing "0 RISCOS" (item 34)

- [x] 6.19 Add `_parse_risk_register_md()` fallback parser (`build_summary_comprehensive.py`) — used by `build_risk_data()` when `risk-register.json` is absent/empty
- [x] 6.20 Extend `CAT_MAP` with AST-pipeline category names (Testing/Data/Business Rule/Integration)
- [x] 6.21 Add `C11.20` regression guard (`validate_summary.py`) — checks either source file directly, asserts `D.risks` non-empty when real data exists
- [x] 6.22 Verify: `Meu-ERP-008-AST-LLM-Master-Orchestrator` → 17/17 risks populated, `validate_summary.py` 85 passed/0 warn/0 error; `Meu-ERP-002` (JSON-based, pre-existing) → no regression (2 pre-existing unrelated failures only: `C3.7`, `C11.16`); remediation agent re-run end-to-end → idempotent, 0 pending
- [x] 7.7 Rule count references updated everywhere (84 → 85)
- [x] 7.8 `summary-agent.md` v1.2.0 → v1.3.0, `summary-validate-agent.md` v1.1.0 → v1.2.0
- [x] 7.9 `CHANGELOG.md` entry for this sub-addendum

### Addendum A.2 (2026-07-12) — Exact risk count, Eventos empty-state, credibility guardrail (items 35-37)

- [x] 6.23 Strengthen `C11.20` to assert exact count match (JSON array length / unique markdown row-id count) vs `D.risks`, not just non-empty
- [x] 6.24 Add Eventos empty-state (`#events-empty-state`, `msg-events-wip` i18n key, `renderEvents()` toggle) + `C11.21` regression guard
- [x] 6.25 Add credibility guardrail to `summary-remediation-agent.md` (Fase 7) + matching fix in `remediate_summary.py`'s completion print (now conditionally emits "⚠️ Concluído com pendências" + lists remaining error ids when `errors_after > 0`, previously always printed "✅ Concluído" regardless)
- [x] 6.26 Re-run `ava-summary-remediation` end-to-end against every previously-touched project (`Meu-ERP-001`, `Meu-ERP-002`, `Meu-ERP-004`, `Meu-ERP-008-AST-LLM-Master-Orchestrator`) to close the process gap that left `Meu-ERP-001` with a stale corrupted diagram — see verification log in the final chat response for this addendum
- [x] 7.10 Rule count references updated everywhere (85 → 86)
- [x] 7.11 `summary-agent.md` v1.3.0 → v1.4.0, `summary-validate-agent.md` v1.2.0 → v1.3.0, `summary-remediation-agent.md` v1.0.0 → v1.1.0
- [x] 7.12 `CHANGELOG.md` entry for this sub-addendum
