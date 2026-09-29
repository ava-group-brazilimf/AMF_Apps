# Agent Development Tasks: Summary Artifact Integrity Verification

**Plan**: `specs/007-summary-artifact-integrity/plan.md`
**Agent ID**: `ava-summary` + `ava-summary-validate` (modify existing) | **Phase**: `F8` | **Module**: `summary`
**PBI**: 2299 | **Change Type**: modify-existing | **Version Bump**: 1.0.0 → 1.1.0 (MINOR)

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 3 is SKIPPED (plan section 7: no schema changes required).

---

## Category 1 — Agent Frontmatter Update

Must complete before Category 2. Both files are `modify-existing` — no new files created.

- [X] **1.1** Open `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` and bump frontmatter version from `1.0.0` to `1.1.0`
- [X] **1.2** Update `date:` field in `summary-agent.md` frontmatter to `2026-07-08`
- [X] **1.3** [P] Update `description: |` in `summary-agent.md` frontmatter to mention the pre-build integrity check (add one sentence after existing description, before the `Ativa com:` line)
- [X] **1.4** [P] Open `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md` and bump frontmatter version to `1.1.0`
- [X] **1.5** [P] Update `description: |` in `summary-validate-agent.md` to mention C11 rule category (append before `Activates with:` line)

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. Tasks 2.1–2.5 concern `summary-agent.md`; tasks 2.6–2.9 concern `summary-validate-agent.md`; tasks 2.8–2.9 also concern `validate_summary.py`.

### PBI 2300 + 2301 — Pre-build check in summary-agent.md

- [X] **2.1** Insert new section `## Step 0.5 — Verificação de Integridade de Artefatos (Pré-Build)` into `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` immediately **before** `## Execution Steps`. The section must contain:
  - NTP guard: `NTP_STEP05 = Bash: python src/shared/utils/ntp_time.py` (required when `TIMING_MODE == FULL`)
  - Objective paragraph in Brazilian Portuguese
  - Full algorithm (steps 1–4 per plan Phase 0): path resolution from `artifact-map.yaml`, existence check, size check, `[ARTIFACT-MISSING]`/`[ARTIFACT-EMPTY]` emit logic, summary line
  - Omission behavior: sections in `sections_omitted` are skipped in Step 3; `<!-- OMITTED: artifact missing or empty — {relative_path} -->` injected at slot
  - **Invariant rule**: markers `[ARTIFACT-MISSING]` and `[ARTIFACT-EMPTY]` MUST NOT appear in final HTML — stdout only
- [X] **2.2** In the MICRO timing table (FULL template, around line 87–90 in the agent), add a new row for Step 0.5 **before** the Step 1 row:
  ```
  │ Step 0.5 — Verificação de Integridade│ Descoberta   │ ✅/❌/⏳ │ YYYY-MM-DDTHH:MM:SS-03:00 │ YYYY-MM-DDTHH:MM:SS-03:00 │ X hora(s), Y minuto(s) e Z segundo(s)│
  ```
- [X] **2.3** In the MICRO timing table (STATUS_ONLY template, around line 108–111), add a new row for Step 0.5 **before** the Step 1 row:
  ```
  │ Step 0.5 — Verificação de Integridade│ ✅/❌/⏳ │
  ```
- [X] **2.4** Verify that the timing invariant block at the top of the agent (`## ⛔ Output Invariant — Timing Final`) still lists the correct step count; update its MICRO table enumeration if it hard-codes step names
- [X] **2.5** Verify the `Timing Initialization` block still references Step 1 correctly after the insertion (no off-by-one references)

### PBI 2302 — C11 rules in summary-validate-agent.md

- [X] **2.6** Add C11 row to the **Rule Catalog** table in `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md` after the C9 row:
  ```markdown
  | **C11 Artifact Integrity** | C11.1–C11.3 | Detects unresolved `[INCOMPLETE]`/`[ARTIFACT-MISSING]` placeholders and tables with zero data rows in generated HTML |
  ```
- [X] **2.7** Add C11 description text below the Rule Catalog table (in Brazilian Portuguese):
  > **C11 Artifact Integrity** — Verifica que o HTML gerado não contém marcadores de artefato ausente (`[INCOMPLETE]`, `[ARTIFACT-MISSING]`) não resolvidos e não contém tabelas com zero linhas de dados. C11.1 e C11.2 são `error` (bloqueiam promoção); C11.3 é `warn`.
- [X] **2.8** [P] Add the three `_c11_1`, `_c11_2`, `_c11_3` Python functions to `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` immediately after the `_c9_3` function (before the `# ════ Runner` comment), exactly as specified in plan Phase 3
- [X] **2.9** [P] Add three `Check(...)` registrations to the `CHECKS` list in `validate_summary.py` after the `C9.3` entry and before the closing `]`, exactly as specified in plan Phase 3:
  - `Check("C11.1", "Artifact Integrity", "error", ...)` → `_c11_1`
  - `Check("C11.2", "Artifact Integrity", "error", ...)` → `_c11_2`
  - `Check("C11.3", "Artifact Integrity", "warn", ...)` → `_c11_3`

---

## Category 3 — Shared Schema Updates

**SKIPPED** — plan section 7 confirms no changes to `agent-task.schema.json` or `agent-result.schema.json`.

---

## Category 4 — Module Registration

Can run in parallel with Category 2 after Category 1 completes.

- [X] **4.1** Open `src/modules/ava-fabric-agents/summary/module.yaml` and change `version:` from `"1.0.0"` to `"1.1.0"`
- [X] **4.2** Confirm no new agent entries are needed (existing `ava-summary` and `ava-summary-validate` entries are unchanged)
- [X] **4.3** Confirm the top-level `module.yaml` at repo root is NOT modified (no new phase/module created)

---

## Category 5 — Quality Gate Checklists

Can run in parallel with Category 4.

- [X] **5.1** Verify `summary-validate-agent.md` Rule Catalog now shows 11 categories (C1–C11) after task 2.6
- [X] **5.2** Verify C11.1 and C11.2 are `"error"` level (block promotion / exit 1) and C11.3 is `"warn"` level (does not block)
- [X] **5.3** [P] Verify that the `[ARTIFACT-MISSING]` / `[ARTIFACT-EMPTY]` invariant rule in Step 0.5 is unambiguous: markers appear only in stdout, never in HTML
- [X] **5.4** [P] Verify the omission behavior is correctly specified: sections in `sections_omitted` receive only the `<!-- OMITTED: ... -->` HTML comment, not empty section markup

---

## Category 6 — Acceptance Validation

Depends on Category 2. Maps to quickstart.md scenarios and PBI 2303.

### PBI 2303 — Sophia Project Validation

- [X] **6.1** Run `python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP` (or available test project) to confirm existing C1–C9 checks still pass (regression baseline)
- [ ] **6.2** [P] Trigger `ava-summary` on a test project and verify Step 0.5 output in stdout:
  - When all artifacts present: `[ARTIFACT-CHECK] OK — N artefatos verificados, 0 ausentes`
  - Format matches exactly as specified in data-model.md Emit Format section
- [ ] **6.3** [P] Simulate a missing artifact (rename one output file) and verify:
  - `[ARTIFACT-MISSING: {section_name}]` line emitted to stdout
  - `[ARTIFACT-CHECK] Resultado:` summary line lists 1 ausente
  - Generated HTML does NOT contain the literal string `[ARTIFACT-MISSING`
  - HTML section slot contains `<!-- OMITTED: artifact missing or empty — ... -->`
- [ ] **6.4** [P] Simulate an empty artifact (truncate one output file to 0 bytes) and verify:
  - `[ARTIFACT-EMPTY: {section_name}]` line emitted to stdout
  - Section omitted from HTML
- [ ] **6.5** [P] Run C11 rule validation (Scenario C from quickstart.md):
  - Inject `[INCOMPLETE]` literal into a test summary HTML
  - Run `validate_summary.py --project {test_project}`
  - Confirm: exit code 1, `ERROR C11.1` in output
- [ ] **6.6** [P] Run C11.2 validation:
  - Inject `[ARTIFACT-MISSING: test]` literally into HTML
  - Confirm: exit code 1, `ERROR C11.2` in output
- [ ] **6.7** [P] Run C11.3 validation:
  - Inject a `<table><thead>...</thead><tbody></tbody></table>` block into HTML
  - Confirm: exit code 0 (warning does not trigger exit 1), `WARNING C11.3` in output
- [ ] **6.8** Restore all test artifacts modified in tasks 6.3–6.7
- [ ] **6.9** [P] Run `validate_summary.py --project {test_project}` on the **unmodified** HTML produced in task 6.2 (no injection) and confirm C11.1 passes with exit 0 — verifying the natural generation path does not introduce `[INCOMPLETE]` on its own

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Category 6.

- [X] **7.1** [P] Update `docs/agents-catalog.md` entry for `ava-summary` (line ~1005): change version from `1.0.0` to `1.1.0` and add one-line description of the pre-build integrity check
- [X] **7.2** [P] Update `docs/agents-catalog.md` entry for `ava-summary-validate`: change version to `1.1.0` and mention C11 rule category
- [X] **7.3** [P] Add `CHANGELOG.md` entry under a new `## [1.1.0] — 2026-07-08` section (or the nearest unreleased section):
  - `ava-summary v1.0.0 → v1.1.0`: Added Step 0.5 pre-build artifact integrity check (PBI 2300, 2301)
  - `ava-summary-validate v1.0.0 → v1.1.0`: Added C11 Artifact Integrity rule category (3 rules) (PBI 2302)
  - `validate_summary.py`: Added `_c11_1`, `_c11_2`, `_c11_3` functions + Check registrations
  - `summary/module.yaml`: Version bumped to 1.1.0
- [X] **7.4** [P] Verify `docs/full-pipeline-guide.md` does not need updating (phase flow unchanged; Step 0.5 is internal to `ava-summary`)

---

## Completion Checklist

- [ ] All categories complete (3 skipped intentionally)
- [X] SKILL.md unchanged (routing unaffected — verified in task 1.1 context)
- [X] `summary-agent.md` has Step 0.5 section and updated MICRO tables (both FULL and STATUS_ONLY)
- [X] `summary-validate-agent.md` Rule Catalog shows C11 row (3 rules)
- [X] `validate_summary.py` has `_c11_1`, `_c11_2`, `_c11_3` functions and Check registrations
- [X] `module.yaml` version is `1.1.0`
- [ ] C11.1 and C11.2 trigger exit 1; C11.3 is warning only — verified in Category 6
- [ ] No `[ARTIFACT-MISSING]`/`[ARTIFACT-EMPTY]` literals appear in generated HTML — verified in task 6.3
- [X] `docs/agents-catalog.md` updated for both agents
- [X] `CHANGELOG.md` entry committed

---

## Dependencies

```
Category 1 (frontmatter bump)
    └─► Category 2 (behavior + validate_summary.py changes)
    └─► Category 4 (module.yaml) [parallel with Cat 2]
    └─► Category 5 (gate checklists) [parallel with Cat 4]
            └─► Category 6 (validation) [after Cat 2]
            └─► Category 7 (docs) [parallel with Cat 6]
Category 3: SKIPPED
```

## Parallel Execution by Phase

**Phase A** (can start immediately):
- 1.1 → 1.2 → 1.3 sequential; 1.4 and 1.5 parallel with 1.3

**Phase B** (after Category 1):
- 2.1 → 2.2 → 2.3 → 2.4 → 2.5 sequential (same file, order matters)
- 2.6 → 2.7 sequential (same file)
- 2.8 and 2.9 parallel with 2.6–2.7 (different file: validate_summary.py)
- 4.1 and 5.1–5.4 fully parallel with Phase B above

**Phase C** (after Category 2):
- 6.1 → 6.2 → 6.3 … 6.8 mostly parallel (different test scenarios)
- 7.1 → 7.4 all parallel with Phase C

## Implementation Strategy

MVP scope: tasks 1.1–1.5, 2.1–2.9, 4.1. This delivers the core PBI 2299 behavior (pre-build check + C11 rules).
Categories 5, 6, and 7 validate and document the MVP.
