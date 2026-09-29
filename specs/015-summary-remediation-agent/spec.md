# Agent Specification: ava-summary-remediation

**Feature Branch**: `015-summary-remediation-agent`
**Created**: 2026-07-09
**Status**: Draft
**Change Type**: new-agent
**Input**: Agent description: "Adicionar um agente de remediação do summário executivo, executável de forma independente após o workflow de migração (master-orchestrator, orquestradores individuais ou o próprio ava-summary), que corrige problemas de exibição de dados e diagramas no HTML gerado."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-summary-remediation` |
| **Version** | `1.0.0` |
| **Phase** | `F8` (Summary — cross-cutting, runs after any phase) |
| **Module** | `summary` |
| **Role** | Post-pipeline repair agent: audits an already-generated Summary HTML (or a project with incomplete/malformed upstream artifacts), resolves what it safely can without re-running upstream agents, rebuilds via `build_summary_comprehensive.py`, and re-validates via `validate_summary.py`. |
| **Skill** | `ava-summary-remediation` |
| **Dispatch** | user-facing via SKILL.md |

This is a **new agent**, sibling to the existing `ava-summary` (builder) and `ava-summary-validate` (gate) agents already registered in `src/modules/ava-fabric-agents/summary/module.yaml`.

---

## 2. Agent Frontmatter

```yaml
---
name: "ava-summary-remediation"
version: "1.0.0"
description: |
  Agente de reparo pós-pipeline do Summary executivo. Audita um HTML já gerado
  (ou artefatos incompletos em outputs/), resolve o que for seguro sem
  re-executar agentes upstream, reconstrói via build_summary_comprehensive.py
  e revalida via validate_summary.py.
  Ativa com: "corrigir o summary", "remediar o summary", "@ava-summary-remediation",
  "consertar visualização do summary".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---
```

---

## 3. Output Contract

```yaml
## Output Contract
outputs:
  remediated_html: "projects/{project_name}/outputs/summary/AVA-FABRIC-SUMMARY-{project_name}-{date}.html"
  fix_report:       "projects/{project_name}/outputs/summary/remediation-report.md"
  fix_report_json:  "projects/{project_name}/outputs/summary/remediation-report.json"
```

The agent overwrites only the Summary HTML it itself owns (the file `ava-summary` also produces). It never overwrites any other pre-existing artifact under `outputs/` — see Guardrail in section 7 (Exclusions) and the authorized exception inherited from the `FS` mode draft (`summary (1).md`, attached by the requester): synthesized files are written **only when the target does not already exist**, and are tagged `# synthesized-by-FS — replace with output from @{agent}` on line 1 (kept verbatim from the existing convention so downstream tooling that already recognizes this tag keeps working).

---

## Functional Changes by Component

Two classes of change ship together in this feature:

**(A) Permanent fixes** — applied once to the shared builder/template/validator so every *newly generated* Summary is already correct, independent of this new agent ever running (see Decision 1 in `plan.md`).

**(B) The new agent itself** — `ava-summary-remediation`, which re-applies the same class of fixes to *already-generated* HTML (legacy summaries) or to projects whose upstream artifacts are missing/malformed, as an idempotent, standalone repair pass.

| # | Problem (as reported) | Class | Component | Fix |
|---|---|---|---|---|
| 1-4 | KPI Classes/Métodos/Complexidade/Endpoints showing `0` | A | `build_summary_comprehensive.py`, `summary-template.html` | Investigate parser root cause; hide KPI tile in `renderKPIs()` when value is a real `0` (not a legitimate metric) |
| 5-6 | KPI Tabelas BD / Volume BD Insert showing `N/D` | A | `summary-template.html` | Hide tile in `renderKPIs()` when value is `N/D` (Volume BD Insert has no data source today — always hidden until one exists) |
| 7 | KPI Telas/Forms showing `0` | A | `summary-template.html` | Hide tile when `0` |
| 8 | KPI "Componentes (fcid)" tile | A | `summary-template.html` L2291 | Remove tile unconditionally from the static `D.kpis` array |
| 9 | Risk table ID column renders literal `R-???` | A | `summary-template.html` (`renderRisks()`) | Remove the ID column from the Risk table entirely (decision confirmed with requester) |
| 10 | "Identified Patterns" table empty | A | `summary-template.html` (`renderPatterns()`) | Hide card when `D.patterns` is empty/all-zero |
| 11 | Bounded Context Map (AS-IS) Forms/Units/LOC columns empty | A | `build_summary_comprehensive.py` (`parse_bounded_contexts`), `summary-template.html` (`renderBC()`) | Hide empty columns/rows |
| 12 | Functional Requirements table empty | A | `summary-template.html`, `build_summary_comprehensive.py` (`parse_func_reqs`) | Hide the **entire submenu** (nav item) when `D.funcReqs` is empty |
| 13 | Business Rules (Rules Mapping) table empty | A | `summary-template.html`, `build_summary_comprehensive.py` (`parse_biz_rules`) | Hide the **entire submenu** when `D.bizRules` is empty |
| 14a | Screen Flow Overview shows agent execution metadata | A | Screen Flow overview render | Remove agent-metadata cards; keep only cards with real values |
| 14b | Card "Rules Categories" | A | `summary-template.html` | Remove card unconditionally |
| 14c | Card + tab "Screen Rules" | A | `summary-template.html`, `build_summary_comprehensive.py` (`parse_screen_rules`) | Remove card and tab unconditionally |
| 15a | Inventory & Metrics: empty/zero/N-D cards | A | Inventory render | Hide when zero/N-D |
| 15b | Inventory & Metrics: "Complexidade" table | A | `summary-template.html` | Remove table unconditionally |
| 16 | Test Baselines: "Tests existentes" table empty | A | `build_summary_comprehensive.py` (`build_test_map`), template render | Hide when empty |
| 17a-c | Banco de Dados AS-IS: empty cards, empty Schema Inventory, empty Stored Procedures | A | `build_summary_comprehensive.py` (`_parse_schema_subsections`), template render | Hide when empty |
| 18a | `screen-rules` deliverable shows agent name/execution metadata | A | Content Embedder / Deliverable Viewer | Strip metadata before display |
| 18b | "value-chain" appears in Deliverables | A | `build_summary_comprehensive.py` (Deliverables classification, ~L5817) | Remove from classification |
| 19 | "Artefatos — AG-10" card (Blueprint C4) | A | `summary-template.html` L1529 | Remove card unconditionally |
| 20 | BC TO-BE cards "Aprovados"/"Parâmetros DDD"/"Squad" + table "BCs Refinados" | A | `summary-template.html` (`renderBCMetrics()`, `renderTOBEBCDetail()`) | Remove cards and table unconditionally |
| 21 | Regras de Negócio TO-BE table empty | A | `build_summary_comprehensive.py` (`parse_tobebn`) | Fallback to `D.bizRules` (AS-IS) when `tobe/docs/regras-negocio.md` is absent |
| 22 | Incorrect/out-of-order `AG-NN` numbering shown throughout the summary | A | `summary-template.html` (card bylines, `card-arts-ag*`/`card-bearts`/`card-fearts`/`card-scripts`/`card-pkgarts`/`card-demoarts`/`card-iac`/`card-protoarts` i18n keys, `AGENTS[]`) | Remove the `AG-NN` token everywhere it is displayed (do not renumber) |
| — | All of the above, for HTML already generated before this fix ships, or for projects with missing/malformed source artifacts | B | New agent `ava-summary-remediation` | Audit → resolve missing artifacts (7 rules, reused from the `FS` draft) → synthesize safe fallbacks → sanitize Mermaid → reconcile security data → apply the same Content/UI guards as column A (Phase 5, new) → rebuild via `build_summary_comprehensive.py` → re-validate via `validate_summary.py` (including new `C11.*` checks) → fix report |

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 - Nominal Path: Legacy Summary Repair (Priority: P1)

**Story**: Como usuário da esteira de migração, quero rodar `@ava-summary-remediation {project_name}` sobre um summary já gerado (por uma versão antiga do builder, antes desta feature) para que ele passe a exibir corretamente todos os menus e submenus, sem precisar re-executar toda a esteira.

**Why this priority**: É o cenário central do pedido — reparo independente pós-pipeline.

**Acceptance Scenarios**:

1. **Given** a project with an existing `AVA-FABRIC-SUMMARY-*.html` generated before this feature shipped, **When** the agent executes, **Then** it produces an updated HTML where none of the 22 issues listed in "Functional Changes by Component" are visible, and `AgentResult.success` is true.
2. **Given** the above, **When** execution completes, **Then** `remediation-report.md`/`.json` list every issue found (before) and every issue fixed (after), and `validate_summary.py --project {project_name}` exits 0 with the new `C11.*` checks passing.

---

### Scenario 2 - Edge Case: Already-Clean Summary (Priority: P2)

**Why this priority**: The agent must be safely idempotent — repeated or unnecessary runs must not corrupt a healthy summary.

**Acceptance Scenarios**:

1. **Given** a project whose Summary HTML was generated by the fixed builder/template (column A already applied) and has no missing artifacts, **When** the agent executes, **Then** it makes no content changes (rebuild produces byte-equivalent D.* data) and reports `0 issues found`.
2. **Given** the above, **Then** `AgentResult.risk.level` is 'low' and no file under `outputs/` other than the Summary HTML/report files is modified.

---

### Scenario 3 - Quality Gate: Missing Template (Priority: P1)

**Why this priority**: Safety gate — the agent must never attempt to synthesize a summary without the base template.

**Acceptance Scenarios**:

1. **Given** `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` is missing or unreadable, **When** the agent executes, **Then** it aborts immediately with a clear `❌ BLOCKED` message naming the missing file, and does not attempt any write under `outputs/`.
2. **Given** the above, **Then** `AgentResult.human_gate_required` is true.

---

## 5. Quality Gate Requirements

- [ ] Agent ID follows `ava-summary-remediation` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [ ] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] Agent registered in `src/modules/ava-fabric-agents/summary/module.yaml` (Article IV)
- [ ] All output paths use lowercase `{project_name}` (Article II)
- [ ] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [ ] No technology/stack values hardcoded — all fixes are data-driven (empty/zero checks), not project- or stack-specific (Article I)
- [ ] Skill/Agent split declared: `.github/skills/ava-summary-remediation/SKILL.md` (Article XI)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Builder | `ava-summary` | Remediation rebuilds via the same `build_summary_comprehensive.py` script `ava-summary` uses |
| Validator | `ava-summary-validate` | Remediation re-validates via the same `validate_summary.py` script, including the new `C11` category added by this feature |

---

## 7. Exclusions

- Does not re-run any upstream agent (F1-F7) to regenerate missing source artifacts — only synthesizes safe placeholder fallbacks per the 7 resolution rules inherited from the `FS` draft, and only when the target file does not already exist.
- Never overwrites an existing artifact under `outputs/` other than the Summary HTML/report files it owns.
- Does not implement a new data source for "Volume BD Insert" (DB INSERT volume) — that KPI remains permanently hidden until a future feature adds a parser for it.
- Does not resolve the pre-existing `C10` category documentation drift in `summary-validate-agent.md` (documented but never implemented) — tracked as known debt, out of scope here.

---

## 8. Assumptions

- `projects/{project_name}/context/project-config.yaml` exists (standard project bootstrap).
- The project has at least been through `ava-summary` once (a Summary HTML exists) OR has `outputs/asis/` and/or `outputs/tobe/` with at least partial content — the agent can run on a fresh project too, in which case most sections will legitimately be absent and Phase 0 audit reports that instead of attempting synthesis.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| CA01 — Full menu/submenu coverage | After independent execution, the Summary HTML shows correct information in every menu/submenu it touches (per the "Functional Changes by Component" table) |
| CA02 — Project independence | The same fixes apply correctly across projects with different legacy technologies / target stacks, without any hardcoded stack/project logic |
| Idempotency | Re-running the agent on an already-remediated summary produces no further changes |
| No regression | `validate_summary.py` exit code 0 after remediation, including all new `C11.*` checks |

---

## Addendum A (2026-07-10) — Console errors, KPI hide-list broadening, AST extraction data source

**Trigger**: user ran `ava-summary-remediation` against `Meu-ERP-008-AST-LLM-Master-Orchestrator` (a project produced by the newer AST-based extraction pipeline, `outputs/asis/delphi-ast-raw/extraction/*.json`) and reported browser console Mermaid parse errors plus several remaining empty/N-D KPI cards and two more tables to remove. Per explicit instruction, this addendum extends the **same** spec/plan/tasks rather than opening a new spec — the underlying agent identity, architecture decisions, and traceability mechanism from the base spec are unchanged.

**Premise carried over unchanged**: all fixes below are project-independent — none reference `Meu-ERP-008` or any specific stack in the implementation, only in the reproduction steps.

### New items (23-33)

| # | Problem | Class | Component | Fix |
|---|---|---|---|---|
| 23 | Mermaid parse error on `diag-solution`: literal YAML comment (`# Ex: "Meu-ERP", "Projeto-X"`) leaked into a diagram node label | A (root cause) + B (self-heal) | `remediate_summary.py` (`_read_project_config`/`_yaml_scalar`), Phase 3 (`_repair_leaked_yaml_comment`) | Root cause: the config-value regex captured the whole rest of the line, including a trailing `# comment`. Fixed the regex to stop at an unquoted `#`. Self-heal: Phase 3 now strips the known leak signature from any already-corrupted `.mmd` file on disk. |
| 24 | "No diagram type detected" console error on synthesized sequence diagrams | A + B | `remediate_summary.py` (`_mmd_with_tag`, Phase 3 `_repair_legacy_leading_tag`) | Root cause: the `# synthesized-by-FS` provenance tag was written as the literal first line of `.mmd` files — Mermaid requires the diagram-type keyword (`sequenceDiagram`, `flowchart`, …) to be the first significant token. Fixed to append the tag as a trailing `%%` Mermaid comment. Self-heal: Phase 3 detects and relocates a legacy leading `#` tag on existing files. |
| 25 | Sequence diagram actor/participant aliases rendering as `"'''''''''Usuario'''''''''"` (growing worse on every remediation run) | A (shared bug) | `build_summary_comprehensive.py` (`sanitize_mmd` → `_fix_seq_alias`) | Root cause: `_fix_seq_alias` was not idempotent — it treated a pre-existing wrapping `"..."` as literal content, escaped the quotes to `'`, and re-wrapped in a new pair of quotes, so every re-run of `sanitize_mmd()` (a shared function, not specific to this feature) added two stray quote characters per side. Fixed by stripping any pre-existing leading/trailing quote run before processing — self-healing regardless of how many times a file was previously corrupted, verified against a 9-quote-corrupted real file. |
| 26 | Blueprint Architecture (`diagrams/architecture-blueprint.mmd`) renders as a completely empty diagram box | A | `build_summary_comprehensive.py` | The template placeholder `{{ASIS_ARCH_BLUEPRINT_DIAGRAM}}` was never wired to any source — only the TO-BE equivalent (`TOBE_ARCH_BLUEPRINT_DIAGRAM`) existed. Added the missing AS-IS substitution reading `asis/diagrams/architecture-blueprint.mmd`. |
| 27 | KPI "Complexidade ≥10" / "Camadas" / "Módulos" showing `N/D` even when source data exists | A | `build_summary_comprehensive.py` | `COMPLEX_METHODS` looked for a non-existent field name (`high_complexity_methods` instead of the AST pipeline's `highest_cc_files`) and used the `x or "N/D"` idiom, which silently treats a legitimate `0` as "no data". `LAYER_COUNT` looked for `bounded_contexts` (a different concept) instead of the AST pipeline's own `layer_breakdown` model. `MODULE_COUNT` had the same `0 or "N/D"` trap. Fixed field mapping (prefer `layer_breakdown`) and replaced the truthiness pattern with an explicit `_first_not_none()` helper across all three. |
| 28 | Premise: **any** KPI tile showing `0` or `N/D` should be removed from view, not just the original 7 | A | `summary-template.html` | Unified `KPI_HIDDEN_IF_ZERO`/`KPI_HIDDEN_IF_ND` (two lists, single-condition each) into one `KPI_HIDDEN_IF_EMPTY` list checked against `v==='0' \|\| v==='N/D'`, extended to cover `kpi-layers`/`kpi-modules` (new) in addition to the original 7 keys. Same unification applied to the DB KPI strip (`DB_KPI_HIDDEN_IF_EMPTY`) and the Inventory & Metrics KPI strip (`INV_HIDDEN_IF_EMPTY`). |
| 29 | Remove "Estrutura de Camadas" table | A | `summary-template.html` | Removed the `tb-layers` card, `renderLayers()`, its call sites, and orphaned i18n keys (`card-layers`, pt/en) — unconditional. |
| 30 | Remove "Arquivos por Tipo" table | A | `summary-template.html` | Removed the `tb-filetypes` card, `renderFileTypes()`, its call sites, and orphaned i18n keys (`card-filetypes`, pt/en) — unconditional. |
| 31 | Remove "Complexidade Ciclomática" table (supersedes the earlier decision in item 15b, which had kept it because it was believed to be the only rendering path for `D.ccTop`) | A | `summary-template.html` | Removed the `tb-complexity` card, `renderComplexityTable()`, its call site, and orphaned i18n keys (`card-complexity`, pt/en) — unconditional, per explicit follow-up instruction. `D.ccTop` itself is unaffected and still populated (C2.2/C2.10 continue to validate the data, independent of whether it is rendered). |
| 32 | F1 sections (Screen Flow, Inventário & Métricas, Test Baseline AS-IS, Banco de Dados AS-IS, Gap List) should also check the newer AST extraction artifacts under `outputs/asis/delphi-ast-raw/extraction/*.json` when the traditional markdown/JSON source is thin or absent, and hide cleanly when no data exists anywhere | A | `build_summary_comprehensive.py` (+ minimal template additions where a genuinely new table was warranted, e.g. Inventory LOC-by-BC breakdown) | Optional, additive data source — never required, never assumed present. Detailed per-section mapping: Screen Flow ← `02_form_business_rules.json`; Inventory & Métricas ← `inventory.md` (LOC by Bounded Context table, new card) + existing `metrics.json`-derived KPIs; Test Baseline ← `09_test_coverage.json` as an additional fallback after `test-map.md`; Banco de Dados AS-IS ← `04_database_schemas.json` (`inferred_tables`) as a fallback for `D.dbSchema` when `schema-inventory.md` is thin; Gap List ← verified/fixed against `gap-register.json` (no dedicated AST JSON source exists for gaps — they are a downstream analysis product, not raw extraction). |
| 33 | New regression guards | A | `validate_summary.py` | Added `C11.18` (no "Arquivos por Tipo" table) and `C11.19` (no "Estrutura de Camadas" table). Updated `C11.10`'s check to assert the "Complexidade Ciclomática" table is fully absent (previously it could only best-effort-avoid a false positive on the table because removal wasn't yet possible without losing the only rendering path for `D.ccTop` — item 31 above resolved that). Broadened `C11.1`/`C11.2` from checking raw pre-filter KPI array values (a design that produced false positives once client-side hiding shipped) to verifying the `KPI_HIDDEN_IF_EMPTY` guard mechanism itself is present and wired — the correct check given the hiding happens in the browser, not in the generated data. Total rule count: 82 → 84. |
| 34 | Menu F1-AS-IS → Riscos always shows "0 RISCOS" for projects produced by the AST extraction pipeline, even when the project has a fully-populated risk register | A | `build_summary_comprehensive.py` (`build_risk_data`, new `_parse_risk_register_md`), `validate_summary.py` (`C11.20`) | Root cause: `build_risk_data()` only ever read `risk-register.json` — some pipeline variants (confirmed: the AST-LLM Master Orchestrator pipeline) emit `risk-register.md` instead, with no `.json` counterpart at all. Added `_parse_risk_register_md()`, a header-driven markdown-table parser (robust to column reordering, tolerant of missing columns) used as a fallback whenever `risk-register.json` is absent or empty; it also opportunistically extracts a mitigation summary from any `### RISK-NNN: Title` / `**Mitigation:**` action-plan subsection when present. Extended `CAT_MAP` with the additional category names this markdown format uses (Testing, Data, Business Rule, Integration). Added `C11.20` to guard the regression (checks either source file directly for real data and asserts `D.risks` is non-empty when one exists). Verified: 17/17 risks now correctly populate the Risk Register for the reporting project (`Meu-ERP-008-AST-LLM-Master-Orchestrator`), with zero impact on the 6 other test projects that already use `risk-register.json`. Total rule count: 84 → **85**. |

### New guardrail for `remediate_summary.py`

**Guardrail 7 (new)**: Phase 3 (Mermaid Sanitization) is authorized to *modify* — not just leave alone — any `.mmd` file that carries a `# synthesized-by-FS` provenance marker (leading or trailing), specifically to repair the two known corruption signatures above (legacy leading tag, leaked YAML comment). This is a narrow, additive exception to the "never overwrite" guardrail (section 3 of this spec / Guardrail 1 of the agent body): it only ever repairs the agent's *own* placeholder output, identified by its own tag, never a real upstream artifact.

## Addendum A.2 (2026-07-12) — Exact risk count, Eventos empty-state, credibility guardrail

**Trigger**: (1) user reported the Risk Register count must equal the exact item count in `risk-register.md`, not merely be non-zero; (2) the "Eventos, Filas & Pub/Sub" menu shows a zero-content KPI grid + empty table instead of communicating that the data simply isn't collected yet; (3) **critical** — `Meu-ERP-001`'s summary (generated 2026-07-12, *after* Addendum A shipped) still exhibited the exact `diag-solution` Mermaid parse error documented as fixed in Addendum A, because the corrupted `solution-structure.mmd` file synthesized by an early (pre-fix) run of `remediate_summary.py` was still sitting on disk — the code fix was correct and self-healing (proven on `Meu-ERP-008`), but the agent had never been *re-run* against `Meu-ERP-001` to actually apply the self-heal. The user correctly identified this as a credibility risk: a documented "fix" that isn't verified end-to-end on every previously-touched project is not a fix from the client's perspective.

| # | Problem | Class | Component | Fix |
|---|---|---|---|---|
| 35 | Risk count must equal the *exact* item count in the source file, not just be non-empty | A | `validate_summary.py` (`C11.20`, strengthened) | `C11.20` was non-empty-only; strengthened to parse the actual source (JSON array length, or unique `RISK-NNN`/`R-NNN` row IDs in the markdown `## Risk Register` table) and assert `D.risks`' unique-id count matches exactly — catches under/over-counting, not just the empty case. |
| 36 | "Eventos, Filas & Pub/Sub" (F1-AS-IS) shows a zero-content KPI grid + empty table when no event data was collected | A | `summary-template.html` (`renderEvents()`, new `#events-empty-state`), `validate_summary.py` (`C11.21`, new) | This class of feature (event/queue/pub-sub reverse engineering) is not yet implemented for most legacy stacks — showing seven zero-valued KPI tiles reads as "we checked and found nothing" rather than "not implemented yet". `renderEvents()` now hides `#events-content-wrap` and shows `#events-empty-state` with the message "Essas informações estão em desenvolvimento e serão exibidas no futuro." whenever `D.events` is empty. New i18n key `msg-events-wip` (pt/en). `C11.21` guards the regression. |
| 37 | **Process gap, not a code bug**: a documented, code-level self-healing fix (Addendum A, items 23-25) does not retroactively repair a project until the remediation agent is actually *re-run* against it | Process | `summary-remediation-agent.md` | Re-ran `ava-summary-remediation` against every project touched during development/testing (`Meu-ERP-001`, `Meu-ERP-002`, `Meu-ERP-004`, `Meu-ERP-008-AST-LLM-Master-Orchestrator`) to close the loop. Added a **mandatory credibility guardrail** (agent body, Fase 7): the completion signal must read "✅ Concluído" ONLY when `errors_after == 0`; otherwise it must read "⚠️ Concluído com pendências" and enumerate every remaining error-level check by id — the agent must never claim success while a diagram still fails to render or a menu still shows incorrect data. |
| 38 | `Meu-ERP-004`: `classDiagram` (mislabeled `component-diagram.mmd`) failed C3.8 with `+setters/getters()` — a slash-separated compound method **call** (no `: ...` suffix) | A | `build_summary_comprehensive.py` (`sanitize_mmd`, Compatibility Rule 2) | Found while running the remediation agent end-to-end (item 37). The existing Rule 2 only handled `+setters/getters: ...` (placeholder-return-type shape); this file used a different shape, `+setters/getters()` (already-parenthesized, no colon/ellipsis). Added a third sub-rule normalising `name/name()` → `nameAndname() void`, mirroring the existing transform. Fixed by the remediation agent's own Phase 3 on the next run — verified `C3.8` cleared. |
| 39 | `Meu-ERP-004`: `docs/functional-requirements.md` has 12 real, well-formed requirements, but `D.funcReqs` rendered empty (`C2.4`) | A | `build_summary_comprehensive.py` (`parse_func_reqs`, Format 3) | Found while running the remediation agent end-to-end (item 37) — the file existed and was correctly structured (`### FR-CP-01: Title`, `**Module**:`, `**Description**:`), so this was not a "genuinely missing data" case. Root cause: Format 3's header regex required a bare `FR-\d+`/`RF-\d+` id with no module-letter segment; the real output from `ava-asis-documentation` uses module-prefixed ids (`FR-CP-01`, `FR-CR-01`, …), the same convention `parse_biz_rules()` already handled correctly. Broadened the regex to accept an optional `-[A-Za-z]+` module segment (and fixed a knock-on bug where the title then captured a leading `": "`). Verified: 0 → 12 requirements, `C2.4` cleared. |

### New guardrail for `summary-remediation-agent.md`

**Guardrail 7 (agent body, new)**: The completion signal is a factual claim, not a formality. "✅ Concluído" requires `errors_after == 0` from Fase 7's revalidation. Any remaining `error`-level check — Mermaid rendering (`C1.*`/`C3.*`), content completeness (`C11.*`), or otherwise — forces "⚠️ Concluído com pendências" with each remaining check id listed. This guardrail exists because a prior run silently reported success on `Meu-ERP-001` while a Mermaid parse error was still reachable in the browser; the exit code was already correct (non-zero) but the human-readable signal did not make that failure impossible to miss.

### Updated Success Criteria

| Criterion | Measure |
|---|---|
| CA03 — No console errors | Opening the generated Summary HTML in a browser produces zero Mermaid `[Mermaid]` console errors/warnings for any static or Deliverable-Viewer-rendered diagram |
| CA04 — Self-healing | Running the remediation agent against a summary/project affected by items 23-25 (regardless of how many times it was previously corrupted) fully repairs it in one pass |
| CA05 — Exact counts | Any count displayed anywhere in the Summary (Risk Register and beyond, by extension of the same heuristic) equals the actual item count in its source artifact, never an approximation |
| CA06 — Honest completion signal | The remediation agent's completion message never claims "✅ Concluído" while any error-level validator check remains failing |

## Addendum B (2026-07-12) — Mandatory Step 0 reads, elimination of remaining hardcoded/orphaned data, `load_project_config()` YAML fix

**Trigger**: a full artifact-to-menu audit (`docs/summary-io-map.md`, produced in a prior round by mapping every input file the Summary *should* read against what the builder/template *actually* read) surfaced a large amount of previously undocumented technical debt: dead render functions, ~13 fully-hardcoded UI elements masquerading as real data, 9 orphaned parsed-but-never-rendered security fields, 8 `ARTIFACT_MAP` path divergences against real agent output contracts, and a nav-dot key-swap bug. User's explicit, hard requirement for this round (verbatim): *"Nenhum dados do sumario pode ser estatico ou hardcode, todas as informações devem ser lidas e interpretadas dos arquivos gerados em poject_name/outputs conforme o mepamento feito"* and *"Aos arquivos que não estão sendo lidos devem obrigatoriamente ser lidos, conforme o guardrails e step 0 informado, para evitar que informações não apareçam"*. Per the standing instruction, this addendum extends the same spec rather than opening a new one.

**Premise carried over unchanged**: all fixes below are project-independent — none reference a specific project name or stack in the implementation.

### Step 0 — mandatory artifact reads

Both `summary-agent.md` (v1.4.0→**1.5.0**) and `summary-remediation-agent.md` (v1.1.0→**1.2.0**) now open with a **Step 0 — Leitura Obrigatória de Artefatos** (Fase 0 in the remediation agent) that enumerates, per phase group (Resumo Executivo, F1–F7), the exact `Read: {path}` checklist derived from `docs/summary-io-map.md`. This makes explicit — and machine-checkable in future audits — which input files each phase is contractually required to open and interpret before generating its section of the HTML, closing the gap where an artifact existed on disk but was never read by any parser. The remediation agent's Fase 0 was restructured into Passo 0.1 (reads the Step 0 checklist, builds `MISSING_READS[]`/`GENUINELY_ABSENT[]`) and Passo 0.2 (existing validator-baseline + template-existence audit, unchanged).

### New items (40-46)

| # | Problem | Class | Component | Fix |
|---|---|---|---|---|
| 40 | Resumo Executivo/F1: "Volume BD INSERT" KPI always `N/D` — no parser ever existed | A | `build_summary_comprehensive.py` (`_count_db_insert_points`) | Now counts `operation=="insert"` entries in `03_database_rules.json`, falling back to `04_database_schemas.json` inferred-table operations. Relabelled the KPI ("Pontos de INSERT no código") to accurately describe a static-analysis call-site count rather than a runtime volume. |
| 41 | F1: Identified Patterns card and 9 Security Review fields (OWASP compliance, supplemental findings, etc.) parsed into `D.*` but never rendered anywhere | A | `build_summary_comprehensive.py` + `summary-template.html` | Restored `#card-patterns-wrap`/`#tb-patterns` wiring to the existing `renderPatterns()`; added `#card-owasp-compliance-wrap` and `#card-sec-supplemental-wrap` with new `renderOwaspCompliance()`/`renderSecuritySupplemental()` consuming the 9 previously-orphaned fields. Also replaced the hardcoded 8-swatch VCL color-palette fallback with real `.dfm` file extraction (`_extract_dfm_color_palette`). |
| 42 | F2: NuGet packages, Quality Gates, Sizing KPIs, Effort-by-BC, Sizing Azure, Migration Waves, Test Plan, and Stack&Patterns pills were literal hardcoded arrays in the template | A | `build_summary_comprehensive.py` (11 new parser functions: `_parse_nuget_packages`, `_parse_sizing_report`, `_parse_cost_estimate`, `_parse_infra_sizing`, `_build_sizing_azure`, `_parse_effort_by_bc`, `_build_waves`, `_parse_test_plan`, `_build_quality_gates`, `_extract_blueprint_patterns`, `_build_stack_pattern_pills`) + `summary-template.html` | Each hardcoded array replaced with a `{{X_JSON}}` placeholder populated from the real agent outputs (`wave-model.json` for waves, etc.). Also added a C4-context fallback badge and BC-TO-BE fallback labeling ("herdado do AS-IS") for when TO-BE-specific data isn't yet produced. |
| 43 | F3/F4/F5: prototype chips were a fixed hardcoded list; Backend/Frontend page titles hardcoded literal framework names; Cenários & Casos and Evidências tables were permanently empty (no parser existed) | A | `build_summary_comprehensive.py` + `summary-template.html` | Prototype chips now from a real glob (`_flatten_tree_node_files`/`list_prototype_chips`). Backend/Frontend titles now use `{{TOBE_BACKEND_VERSION}}`/`{{TOBE_FRONTEND_VERSION}}`. New `parse_scenario_register()`/`renderScenarios()` and `parse_defects()`/`renderDefects()` wired into the previously-dead `#tb-scen`/`#tb-defects` tables. |
| 44 | F6/F7: `ARTIFACT_MAP` paths diverged from the real `## Output Contract` of 6 agents (`ava-devops-iac`, `ava-devops-ci`, `ava-deliverable-tech-docs`, `ava-deliverable-client-demo`, `ava-deliverable-security-compliance`, `ava-deliverable-migration-plan`), causing false "missing" status; IaC/CI/CD data and the Security Compliance table were hardcoded/dead; Pre-Delivery and Acceptance checklists were unconditionally green regardless of evidence; nav dots for F6/F7 never lit up | A | `build_summary_comprehensive.py` (`ARTIFACT_MAP` corrections, new `_parse_iac_resources`, `_parse_ci_stages`, `_parse_cd_envs`, `_compute_delivery_checklists`, `_parse_security_report`) + `summary-template.html` (`renderNavDots()` dotMap fix) | Checklist booleans (QG1-QG6/AC1-AC8) are now computed from real evidence and are honest — `false` when evidence is absent, never fabricated `true`. The F6/F7 `dotMap` key-swap (F6 pointing at F7's DOM ids and vice versa) was corrected. |
| 45 | `load_project_config()` — the shared parser for `project-config.yaml` — silently dropped nearly every top-level field (any line with a trailing inline `# comment`, which is the norm in real config files) and could never parse nested YAML sections at all (`tobe_stack:`, `architecture_patterns:`, etc. always resolved to `{}`), degrading `SCOPE`, `LEGACY_TECH`, `TOBE_BACKEND_VERSION`, `TOBE_FRONTEND_VERSION` to their hardcoded defaults regardless of the project's real configuration | A | `build_summary_comprehensive.py` (`load_project_config`) | Switched to `yaml.safe_load()` (PyYAML, already a repo dependency used elsewhere in this module) with the flat-line regex retained only as a fallback for environments without PyYAML. Verified: a real `project-config.yaml` with 34 top-level keys and a nested `tobe_stack` block, previously reduced to a near-empty dict, now parses completely and correctly. |
| 46 | New regression guards for items 40-45 | A | `validate_summary.py` | Added `C11.22`-`C11.33` (12 new checks): config-driven placeholder resolution + cross-check against `project-config.yaml`'s `tobe_stack:` (C11.22); Volume BD INSERT data-driven, not stuck at `N/D` (C11.23); Identified Patterns card wired (C11.24); the 9 security fields have a render path (C11.25); VCL palette not reverted to the old 8-swatch hardcode (C11.26); F2 data sourced from `{{X_JSON}}` placeholders, not literal arrays (C11.27); Backend/Frontend titles use the version placeholders (C11.28); Scenarios/Defects tables wired (C11.29); nav-dot F6/F7 mapping correct, with auto-fix (C11.30); F6/F7 IaC/CI/CD/security-report data not hardcoded (C11.31); delivery checklists are not unconditionally all-green (C11.32); prototype chips not reverted to a fixed 3-file list (C11.33). Total unique check count: 85 → **97**. |
| 47 | Found during end-to-end revalidation: `Meu-ERP-002`'s `tobe/docs/regras-negocio.md` **exists** but uses a different real-world section shape ("## Business Rules Preservation Map" / "### BC-NN — Name" / `\| BR \| AS-IS Implementation \| TO-BE Implementation \|`) than the one `parse_tobebn()` recognizes (`## Métricas`, `## Tabela de Rastreabilidade`, `RN-BCxx-yy` row ids) — because the file is non-empty, the existing "file absent → AS-IS fallback" branch never triggered, so `D.tobebn.metrics`/`.traceability` silently came back empty (`C11.16` regression, unrelated to this round's 4 delegated fixes) | A | `build_summary_comprehensive.py` (`parse_tobebn`) | Extended the fallback condition: when the file is present but parsing yields empty `metrics` **and** empty `traceability` (no recognized section matched at all), apply the same AS-IS `_tobebn_from_asis_fallback()` used for the absent-file case, instead of returning an empty result. Verified: `Meu-ERP-002` — 27 AS-IS rules now populate `D.tobebn` via fallback; `C11.16` cleared, 98/98 checks passing. |

### Updated Success Criteria

| Criterion | Measure |
|---|---|
| CA07 — No static/hardcoded data | Every value rendered in the Summary HTML traces to a specific input file under `projects/{name}/outputs/**` (or a documented, explicitly-labeled "not yet implemented" empty state) — never a literal default baked into the builder or template |
| CA08 — Mandatory reads enforced | Every artifact listed in a phase's Step 0 checklist is read and, if present with data, reflected in the rendered HTML; genuinely absent artifacts produce a hidden section/empty-state, never silent omission of a section that should have rendered |
