# Agent Specification: Summary Artifact Integrity Verification

**Feature Branch**: `007-summary-artifact-integrity`
**Created**: 2026-07-08
**Status**: Draft
**PBI**: 2299
**Change Type**: modify-existing
**Input**: Agent description: "Verificação de integridade de artefatos antes da geração do Summary HTML"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-summary` (modify existing) |
| **Version** | `1.0.0` → `1.1.0` (MINOR — new behavior: pre-build verification step) |
| **Phase** | `F8` |
| **Module** | `summary` |
| **Role** | Adds pre-build artifact integrity check to summary-agent.md and expands validation rules in summary-validate-agent.md |
| **Skill** | `ava-summary` (existing skill, no new skill needed) |
| **Dispatch** | user-facing via SKILL.md (existing) |

> **Change Type `modify-existing`**:
> - Target file 1: `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`
> - Target file 2: `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`
> - Version bump: MINOR (new pre-build verification step, backward-compatible)
> - module.yaml entry already exists — Category 4 tasks are version-bump only
> - SKILL.md already exists — Category 1.5 is N/A

---

## 2. Agent Frontmatter

**summary-agent.md** — version bump only (no frontmatter content change):

```yaml
---
name: "ava-summary"
version: "1.1.0"   # bumped from 1.0.0
description: |
  Consolida todos os relatórios gerados pelos workflows AS-IS e TO-BE da AVA Fabric
  e produz um relatório HTML interativo padronizado com design Avanade.
  Agora inclui verificação de integridade de artefatos antes da geração HTML:
  confirma existência e tamanho > 0 de cada entrada em artifact-map.yaml;
  emite [ARTIFACT-MISSING: nome_secao] por artefato ausente e omite a seção.
  Ativa com: "gerar summary", "consolidar relatórios", "generate summary report",
  "relatório html", "summary ava", "consolidate reports", "generate html report",
  "ava summary", "gerar relatório final", "final report".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
date: 2026-07-08
---
```

**summary-validate-agent.md** — version bump only:

```yaml
---
name: "ava-summary-validate"
version: "1.1.0"   # bumped from 1.0.0
description: |
  Non-regression quality gate for the Summary HTML. Runs after `ava-summary`
  and audits the generated file against ~55 rules derived from historical fixes
  plus new C11 rules: detects HTML sections containing placeholder text
  ([INCOMPLETE], [ARTIFACT-MISSING]) and tables with zero data rows.
  Activates with: "validate summary", "audit summary", "check summary integrity",
  "summary validator", "summary-validate", "validar summary".
allowed-tools: Read, Bash, Glob, Grep, Write
---
```

---

## 3. Output Contract

These agents do not produce new output artifacts. They modify the behavior of
**existing** pipeline steps:

- `summary-agent.md` emits `[ARTIFACT-MISSING: {section_name}]` messages to
  stdout during execution (not written to a separate file).
- `summary-validate-agent.md` writes the existing artifacts:
  - `projects/{project_name}/outputs/summary/validation-report.md`
  - `projects/{project_name}/outputs/summary/validation-report.json`

The validation report now includes findings from the new **C11** category.

> No new output paths are required. Downstream parser in `build_summary_comprehensive.py`
> is unaffected (no schema change).

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Pre-build: All Artifacts Present (Priority: P1)

**Story**: Como o orquestrador da esteira, quero que o ava-summary verifique a existência
e o tamanho de todos os artefatos em artifact-map.yaml antes de iniciar a geração HTML,
para que artefatos ausentes sejam detectados antes de criar seções vazias.

**Why this priority**: Prevents silent empty sections in client-facing HTML.

**Acceptance Scenarios**:

1. **Given** all artifact paths in `artifact-map.yaml` exist with size > 0, **When** `ava-summary` runs Step 1 (Pre-build Integrity Check), **Then** it emits `[ARTIFACT-CHECK] OK — N artifacts verified` and proceeds to HTML generation.
2. **Given** the above, **When** execution completes, **Then** the generated HTML contains no sections with `[INCOMPLETE]` or `[ARTIFACT-MISSING]` placeholders.

---

### Scenario 2 — Pre-build: One or More Artifacts Missing (Priority: P1)

**Story**: Quero que o ava-summary emita um aviso claro por artefato ausente e omita
a seção correspondente do HTML, em vez de gerar uma seção vazia silenciosamente.

**Why this priority**: Core of PBI 2299 — replaces silent failure with explicit signal.

**Acceptance Scenarios**:

1. **Given** artifact `projects/{project_name}/outputs/qa/test-plan.md` is absent (path moved or not generated), **When** Step 1 runs, **Then** the agent emits `[ARTIFACT-MISSING: s-test-plan] — arquivo ausente: qa/test-plan.md` for each missing entry.
2. **Given** a missing artifact is detected, **When** HTML generation begins (Step 3), **Then** the corresponding HTML section is **omitted** (not rendered with empty content) and a status note `<!-- OMITTED: artifact missing — qa/test-plan.md -->` is injected as an HTML comment.
3. **Given** the above, **Then** the final `[ARTIFACT-CHECK]` summary lists all missing artifacts grouped by phase.

---

### Scenario 3 — Pre-build: Artifact Exists but is Empty (size = 0) (Priority: P1)

**Why this priority**: Zero-byte files are equally harmful as missing files.

**Acceptance Scenarios**:

1. **Given** an artifact path resolves to an existing file with size = 0 bytes, **When** Step 1 runs, **Then** the agent emits `[ARTIFACT-EMPTY: {section_name}] — arquivo vazio: {relative_path}`.
2. **Given** the above, **Then** the section is omitted from HTML (same behavior as missing).

---

### Scenario 4 — Validator: Detects [INCOMPLETE] Placeholder in Generated HTML (Priority: P1)

**Story**: Quero que o summary-validate-agent detecte seções com placeholder
[INCOMPLETE] ou [ARTIFACT-MISSING] no HTML gerado e reporte como erro (exit 1).

**Why this priority**: Validation gate must catch any placeholder that survived HTML generation.

**Acceptance Scenarios**:

1. **Given** the generated HTML contains a literal string `[INCOMPLETE]`, **When** `ava-summary-validate` runs rule C11.1, **Then** it reports `ERROR C11.1 — placeholder [INCOMPLETE] found at {context}` and returns exit code 1.
2. **Given** the generated HTML contains `[ARTIFACT-MISSING`, **When** rule C11.2 runs, **Then** it reports `ERROR C11.2 — unresolved [ARTIFACT-MISSING] marker found`.

---

### Scenario 5 — Validator: Detects Table with Zero Data Rows (Priority: P2)

**Why this priority**: Empty tables indicate data extraction failure without being caught
by existing rules.

**Acceptance Scenarios**:

1. **Given** a `<table>` element in the HTML has a `<thead>` but zero `<tbody><tr>` rows, **When** rule C11.3 runs, **Then** it reports `WARNING C11.3 — empty table detected in section {section_id}`.
2. **Given** all tables have at least one data row, **When** C11.3 runs, **Then** no warning is emitted and rule passes.

> Note: C11.3 is a **warning** (not error) — it does not trigger exit 1 on its own.

---

### Scenario 6 — Sophia Project Validation (Priority: P1)

**Story**: Quero que a validação executada no projeto Sophia (ou projeto equivalente com outputs completos) resulte em zero seções
vazias no Summary final, confirmando que a feature funciona em produção.

**Why this priority**: Acceptance criterion 5 from PBI 2299 — end-to-end proof.

**Acceptance Scenarios**:

1. **Given** a project with a complete output tree (Sophia or an equivalent such as Meu-ERP) and all artifact paths correct, **When** `ava-summary` runs with the new pre-build check, **Then** `[ARTIFACT-CHECK]` emits OK for all artifacts.
2. **Given** the above, **When** `ava-summary-validate` runs, **Then** exit code is 0, no C11 errors are reported, and `validation-report.json` shows `c11_errors: 0`.

---

## 5. Quality Gate Requirements

- [ ] Agent ID follows `ava-{phase}-{role}` pattern — existing IDs unchanged (Article II)
- [ ] Frontmatter bumped to `1.1.0` in both files (Article II)
- [ ] New rule category C11 added to summary-validate-agent.md with 3 rules (C11.1 error, C11.2 error, C11.3 warning)
- [ ] Pre-build step added as **Step 0.5** (before Step 1) in summary-agent.md execution flow
- [ ] `[ARTIFACT-MISSING]` and `[ARTIFACT-EMPTY]` markers are NOT present in the final HTML
- [ ] BDD scenarios cover all 4 acceptance criteria from PBI 2299
- [ ] No new hardcoded technology versions introduced (Article I)
- [ ] module.yaml version updated for `summary` module (Article IV)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent/Artifact | Reason |
|---|---|---|
| Artifact map | `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` | Source of truth for all artifact paths to verify |
| Summary builder | `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` | Must be verified not to break when a section is omitted |
| Validate script | `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` | C11 rules must be added or integrated here |
| Sophia project | `projects/Sophia/` (or equivalent) | Used for end-to-end acceptance validation per AC5 |

---

## 7. Exclusions

- Fixing pre-existing validation rules (C1–C10) — handled by `ava-summary-validate` existing rules
- Changing `artifact-map.yaml` paths to fix real path drift — this spec covers detection only, not remediation
- Generating new artifact files for missing content — out of scope (this is an integrity checker, not a content fixer)
- HTML template visual fixes (Mermaid rendering, submenu layout) — out of scope for this PBI

---

## 8. Assumptions

- `artifact-map.yaml` is the single source of truth for all artifact → HTML section mappings
- The pre-build check runs synchronously before any HTML generation step
- When a section is omitted due to a missing artifact, downstream sections that do not depend on it are unaffected
- The Sophia project has a complete output tree suitable for end-to-end validation
- `validate_summary.py` can be extended with new rule categories without breaking the existing `--project` CLI interface

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Pre-build verification added | `summary-agent.md` Step 0.5 block present and iterates all `artifact-map.yaml` entries |
| Clear missing artifact emission | Each absent/empty artifact produces one `[ARTIFACT-MISSING]` or `[ARTIFACT-EMPTY]` line with section name and file path |
| HTML has no empty/placeholder sections | Final HTML contains no literal `[INCOMPLETE]`, `[ARTIFACT-MISSING]`, or `[ARTIFACT-EMPTY]` strings |
| C11 rules in validator | `summary-validate-agent.md` Rule Catalog table includes C11 row (3 rules); `validate_summary.py` enforces them |
| Sophia project clean | End-to-end run on Sophia outputs returns exit 0 with `c11_errors: 0` |
