# Agent Development Tasks: Summary — Add Test Cases AS-IS Menu

**Plan**: `specs/025-summary-asis-test-cases-menu/plan.md`
**Change Type**: `modify-existing` | **Phase**: F8 | **Module**: `summary`
**Agents affected**: `ava-summary` (1.7.0→1.8.0), `ava-summary-validate` (1.4.0→1.4.1), `ava-summary-remediation` (1.4.0→1.4.1)

> Complete categories sequentially. [P] = parallelizable within the same category.
> Categories 3 and 4 are N/A for this `modify-existing` change (no new agent, no schema changes).
> Categories 5, 6, 7 can start in parallel only after Category 2 is complete.

---

## Category 1 — Agent Frontmatter & Contract Definition

*Must complete before Category 2. Establishes the version intent for all three agents.*

- [X] **1.1** [P] Bump `summary-agent.md` frontmatter version: `1.7.0` → `1.8.0`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`
- [X] **1.2** [P] Bump `summary-validate-agent.md` frontmatter version: `1.4.0` → `1.4.1`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`
- [X] **1.3** [P] Bump `summary-remediation-agent.md` frontmatter version: `1.4.0` → `1.4.1`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`

---

## Category 2 — Core Implementation

*Depends on Category 1. Steps 2.1–2.3 are sequential (builder function → call site → injection). Steps 2.4–2.12 can be split across builder (2.10–2.12) and template (2.4–2.9) work in parallel once 2.1–2.3 are done.*

- [X] **2.1** Add `build_test_cases(asis_dir: Path) -> list` function to `build_summary_comprehensive.py`
  - File: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - Insert after the `build_test_map()` function definition (~line 6741+)
  - Logic: split on `## CT-` H2 headings; extract `id`, `title`, `priority`, `type`, `module`, `rules`, `steps` (count of data rows in `### Passos` table), `preconditions`, `steps_raw`, `postconditions`; return `[]` when file absent
  - See `data-model.md` for the full `TestCaseEntry` schema and parsing rules per field

- [X] **2.2** Add call site for `build_test_cases()` in the main build function
  - File: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - After line `test_map, test_gaps = build_test_map(asis_dir)` (~line 7627), add:
    `test_cases = build_test_cases(asis_dir)`

- [X] **2.3** Inject `testCases` into the `data_injection` f-string
  - File: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - In the `data_injection` f-string (~line 8175), after `testGaps` line, add:
    `f'  testCases: {safe_json(test_cases)},\n'`
  - Also update the build metrics log line (~line 8044) to include `testCases={len(test_cases)}`

- [X] **2.4** Add sidebar nav item for `s-f1-tc` to `summary-template.html`
  - File: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`
  - Insert after the `s-f1-qa` nav item (line ~776) and before `s-f1-db`:
    ```html
    <div class="ni" onclick="nav('s-f1-tc',this)">
      <span class="nd" id="nd-f1-tc"></span>
      <span data-i18n="nav-tc">Test Cases</span>
      <span class="nb" id="nb-tc" style="display:none">0</span>
    </div>
    ```

- [X] **2.5** Add section body `<div id="s-f1-tc">` to `summary-template.html`
  - File: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`
  - Insert after the closing `</div>` of the `s-f1-qa` section (~line 1333) and before `<!-- F1: Banco de Dados -->`:
    7-column table (ID | Título | Módulo | Prioridade | Tipo | Regras | Passos); KPI area `#kpi-tc`; badge `#tag-tc`; `tbody#tb-tc-body`
  - See plan.md section 7.5 for the complete HTML block
  - ✔ SC-006 guard: confirm the new section does NOT introduce any `<script src=` or `<link href=` CDN reference

- [X] **2.6** Add 10 i18n keys to both `pt:` and `en:` JS objects in `summary-template.html`
  - File: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`
  - Keys: `nav-tc`, `pg-tc`, `card-tc`, `th-tc-id`, `th-tc-title`, `th-tc-module`, `th-tc-priority`, `th-tc-type`, `th-tc-rules`, `th-tc-steps`
  - See plan.md section 1 i18n table for PT/EN values

- [X] **2.7** Add `renderTCKpis()` JS function to `summary-template.html`
  - File: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`
  - Insert after `renderTestTables()` function
  - Reads `D.testCases`; updates `#nb-tc` badge, `#tag-tc`, `#nd-f1-tc` dot, `#kpi-tc` tiles (Total, P0, Funcionais, Negativos/Edge)
  - See plan.md section 7.7 for complete function code

- [X] **2.8** Add `renderTestCases()` JS function to `summary-template.html`
  - File: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`
  - Insert after `renderTCKpis()`
  - Reads `D.testCases`; hides `#card-tc-wrap` when empty; renders rows into `#tb-tc-body`; priority badge uses `.sc`/`.sa`/`.sm`/`.sb2` classes
  - ⚠️ Check if an HTML-escape helper (`h()` or `esc()`) already exists — reuse if so, otherwise define locally
  - See plan.md section 7.8 for complete function code

- [X] **2.9** Wire `renderTCKpis()` and `renderTestCases()` into `renderAll()`
  - File: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`
  - Locate `renderAll()` function; add both calls adjacent to other `render*` calls

- [X] **2.10** [P] Add `_c11_37()` function to `validate_summary.py`
  - File: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`
  - Insert after `_c11_36()` function definition (~line 1785)
  - Logic: if `asis/qa/test-cases.md` absent → `Result(True, "skipped")`; if no CT- headings → `Result(True, "skipped")`; otherwise check `D.testCases` is non-empty in HTML via regex
  - See plan.md section 7.10 for complete function code

- [X] **2.11** [P] Add `Check("C11.37", ...)` entry to `CHECKS` list in `validate_summary.py`
  - File: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`
  - Insert after the `C11.36` entry (~line 2659)
  - Level: `"warn"` (optional artifact — does not block summary promotion)
  - See plan.md section 7.10 for complete `Check(...)` call

- [X] **2.12** [P] Add Rule J block to `phase1_artifact_resolution()` in `remediate_summary.py`
  - File: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`
  - Insert after the Rule I block (~line 267)
  - Guard: only synthesize placeholder when `qa/test-cases.md` absent AND `fastqa/manual_test/` does not exist
  - Placeholder header: `SYNTH_TAG.replace("{agent}", "ava-asis-bridge-fastqa")`
  - See plan.md section 7.11 for complete Rule J code

---

## Category 3 — Shared Schema Updates

**N/A** — no changes to `agent-task.schema.json` or `agent-result.schema.json`.

---

## Category 4 — Module Registration

**N/A** — no new agents created; no `module.yaml` changes required.

---

## Category 5 — Quality Gate Checklists

*Can run in parallel with Category 6 once Category 2 is complete.*

- [X] **5.1** Add C11.37 rule row to C11 table in `summary-validate-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`
  - Add after C11.36 row in the `### C11 Content Completeness & UI Cleanup — Rule Detail` table:
    `| C11.37 | warn | D.testCases non-empty when asis/qa/test-cases.md has ≥1 CT- heading | não |`
  - Also increment the rule count in the description frontmatter by 1

- [X] **5.2** Add Regra J paragraph to Fase 1 section in `summary-remediation-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`
  - Add after Regra I paragraph in the `### Fase 1` section
  - Describe the synthesis guard logic (absent file + absent `fastqa/manual_test/` directory)

- [X] **5.3** Add C11.37 heuristics row to Fase 5 table in `summary-remediation-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`
  - Add to the heuristics table in `### Fase 5`:
    `| **Test Cases AS-IS não pode ficar vazio com dado real disponível** | O menu "Test Cases" (F1-AS-IS) NUNCA deve exibir D.testCases vazio quando asis/qa/test-cases.md possui entradas CT- válidas. | build_test_cases() (build_summary_comprehensive.py); guardado por C11.37 |`

---

## Category 6 — Acceptance Validation

*Depends on Category 2 complete. Validate all 4 scenarios from spec.md.*

- [X] **6.1** Rebuild summary for `Meu-ERP_w_AST` and verify build succeeds
  - `python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project Meu-ERP_w_AST`
  - Expected: `✅ SUCESSO!` + no Python traceback

- [X] **6.2** [P] Verify `D.testCases` is non-empty in the generated HTML
  - Grep the output HTML for `"testCases":[` and confirm array is not `[]`
  - Expected count = number of `## CT-` headings in `asis/qa/test-cases.md` (6 entries from `Meu-ERP_w_AST`)

- [X] **6.3** [P] Run `validate_summary.py` and confirm C11.37 passes
  - `python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP_w_AST`
  - Expected: exit code 0; C11.37 listed as `passed`
  - Also confirms SC-007: all pre-existing C11.* checks must remain `passed` (no regression)

- [X] **6.4** [P] Visual check in browser (spec scenario 1)
  - Open generated HTML; sidebar must show "Test Cases" under F1 — Diagnóstico AS-IS
  - Click the item: section "Test Cases AS-IS" must display 4 KPI tiles + table with ≥1 row
  - Nav dot `nd-f1-tc` must be green; badge `nb-tc` must show the TC count

- [X] **6.5** Test absent artifact scenario (spec scenario 2)
  - Rename `asis/qa/test-cases.md` to `.bak`; rebuild; run validator
  - Expected: `D.testCases` is `[]`; section is hidden or empty; C11.37 reports `skipped`; exit code 0
  - Restore the file after the test

- [X] **6.6** [P] Run remediation and confirm Rule J reports N/A for existing project
  - `python src/modules/ava-fabric-agents/summary/utils/remediate_summary.py --project Meu-ERP_w_AST`
  - Expected: `test-cases.md` already exists → Rule J does not add any synthesized artifact

- [X] **6.7** Verify C11.37 warn-path — confirm validator fires `warn` when `D.testCases` is empty despite real data (spec scenario 3)
  - Temporarily add `return []` as first line of `build_test_cases()` in `build_summary_comprehensive.py`
  - Rebuild: `python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project Meu-ERP_w_AST`
  - Run: `python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP_w_AST`
  - Expected: C11.37 fires as `warn`; report lists the check with remediation pointing to `build_test_cases()`
  - Revert the temporary patch after the test

- [X] **6.8** [P] Verify Regra J synthesis path — confirm placeholder is created when all upstream data is absent
  - Create a minimal temp project dir under `projects/` with empty `outputs/asis/qa/` and no `fastqa/manual_test/`
  - Run: `python src/modules/ava-fabric-agents/summary/utils/remediate_summary.py --project <temp-project>`
  - Expected: `asis/qa/test-cases.md` written with `synthesized-by-FS` header; log line "Rule J: synthesized placeholder test-cases.md"
  - Delete the temp project dir after the test

---

## Category 7 — Documentation & Catalog Update

*Can run in parallel with Category 6 once Category 2 is complete.*

- [X] **7.1** [P] Add `asis/qa/test-cases.md` to Step 0 F1 read list in `summary-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`
  - Add after the `test-gaps.md` line in the **F1 — Diagnóstico AS-IS** `Read:` block:
    `Read: asis/qa/test-cases.md  (CT-NNN blocks — ava-asis-bridge-fastqa Step 17b; optional)`

- [X] **7.2** [P] Add `D.testCases` row to the D.* Field Schemas table in `summary-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`
  - Row: `| D.testCases | renderTestCases() | {id, title, priority, type, module, rules, steps, preconditions, steps_raw, postconditions} |`

- [X] **7.3** [P] Add `testCases` row to the Data Source Mapping table in `summary-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`
  - Row: `| testCases | asis/qa/test-cases.md | ## CT-\d+ headings → extract metadata fields + step count |`

- [X] **7.4** [P] Add Test Cases entry to the Output HTML Structure in `summary-agent.md`
  - File: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`
  - Under F1, after `└─ Test Gaps` line:
    `└─ Test Cases               ← qa/test-cases.md (CT-NNN blocks: id, title, priority, type, module, rules, steps)`

- [X] **7.5** [P] Add `CHANGELOG.md` entry
  - File: `CHANGELOG.md`
  - Add entry for all three version bumps describing the new Test Cases AS-IS section and related validator/remediation changes

- [X] **7.6** [P] Update `docs/summary-io-map.md`
  - File: `docs/summary-io-map.md`
  - Add `asis/qa/test-cases.md` as a recognized F1 input row (Fase → F1 / Submenu → Test Cases / Arquivo de Entrada → `asis/qa/test-cases.md`)
  - This ensures future remediation agents and pipeline observers recognize `test-cases.md` as a known input and do not flag it as an unexpected artifact

---

## Completion Checklist

- [ ] All Category 1–2 tasks complete
- [ ] Categories 5, 6, 7 complete
- [ ] `build_summary_comprehensive.py` builds without errors for `Meu-ERP_w_AST`
- [ ] `validate_summary.py` exits 0 and C11.37 shows `passed`
- [ ] C11.37 warn-path confirmed (task 6.7 — fires `warn` when `D.testCases` forced empty)
- [ ] Visual check: "Test Cases" nav item and section render correctly in browser
- [ ] Absent artifact scenario: no errors, C11.37 shows `skipped`
- [ ] All three agent `.md` files have correct version in frontmatter
- [ ] `docs/summary-io-map.md` updated with `test-cases.md` row (task 7.6)
- [ ] `CHANGELOG.md` entry committed
