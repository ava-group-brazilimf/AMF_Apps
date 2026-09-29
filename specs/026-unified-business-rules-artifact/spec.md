# Agent Specification: Unified Business Rules & Functional Requirements Artifact

**Feature Branch**: `026-unified-business-rules-artifact`
**Created**: 2026-07-21
**Status**: Draft
**Change Type**: `modify-existing`
**Input**: Consolidate `functional-requirements.md`, `business-rules.md`, and `code-business-rules.md` into a single unified `business-rules.md` artifact.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (multiple agents) |
| **Phase** | `F1` (AS-IS Diagnostic) |
| **Primary Agent** | `ava-asis-documentation` (v1.6.0 → v2.0.0) |
| **Secondary Agent** | `ava-asis-solution-delphi` (v2.5.0 → v2.6.0) |
| **Scope** | All agents that reference `functional-requirements.md` or `code-business-rules.md` in their Input Contracts |
| **Version Bump** | MAJOR for `ava-asis-documentation` (output contract change — artifact removed); MINOR for `ava-asis-solution-delphi` (artifact removed from output contract) |

---

## 2. Problem Statement

Three artifacts currently co-exist in the AS-IS diagnostic output that describe overlapping,
complementary information about business behavior:

| Artifact | Producer | Location | Content |
|---|---|---|---|
| `functional-requirements.md` | `ava-asis-documentation` (trigger RF) | `asis/docs/functional-requirements.md` | Functional requirements (FR-NNN) extracted from code documentation |
| `business-rules.md` | `ava-asis-documentation` (trigger RN) | `asis/docs/business-rules.md` | Business rules (BR-NNN / RN-XX-NN) mined from documentation |
| `code-business-rules.md` | `ava-asis-solution-delphi` (Step 3) | `asis/code-business-rules.md` | Business rules mined from AST/code (BR-NNNN IDs) |

**Pain points:**
- Downstream agents (coder backends, QA agents, TO-BE architects) must read multiple artifacts to understand business behavior.
- `code-business-rules.md` partially duplicates `business-rules.md` with different ID schemes.
- Consumers (TO-BE agents) implement fallback logic (`code-business-rules.md` OR `business-rules.md`) that adds complexity.

**Proposed solution:** Merge into a single canonical `asis/docs/business-rules.md` with two distinct sections:
1. **Business Rules section** — preserves the existing `business-rules.md` format (BR-NNN / RN-XX-NN)
2. **Functional Requirements section** — migrates content from `functional-requirements.md` (FR-NNN)

`code-business-rules.md` is discontinued. The existing `business-rules.md` ID scheme (BR-NNN / RN-XX-NN) prevails. AST-extracted business rules remain accessible via the raw `01_business_rules.json` artifact; they are **not** merged into the unified file.

---

## 3. Output Contract Changes

### 3.1 `ava-asis-documentation` — New unified output contract

**Removed artifact**: `asis/docs/functional-requirements.md` (discontinued)

**Modified artifact**: `asis/docs/business-rules.md` — now contains **two sections**:

```markdown
# Business Rules & Functional Requirements — {project_name} AS-IS

## Functional Requirements

[existing functional-requirements.md content — FR-NNN format per parser-contracts.md]

---

## Business Rules

[existing business-rules.md content — BR-NNN / RN-XX-NN format per parser-contracts.md Formato A or B]
```

**Retained artifacts** (no change):
- `asis/docs/value-chain.md`
- `asis/docs/screen-navigation-map.md`
- `asis/docs/screen-flow.mmd`
- `asis/docs/screen-rules.md`
- `asis/docs/prototype-asis/`

**Output Contract summary (v2.0.0)**:

```yaml
outputs:
  value_chain:           "projects/{project_name}/outputs/asis/docs/value-chain.md"
  business_rules:        "projects/{project_name}/outputs/asis/docs/business-rules.md"   # now includes FR section
  screen_navigation_map: "projects/{project_name}/outputs/asis/docs/screen-navigation-map.md"
  screen_flow_mmd:       "projects/{project_name}/outputs/asis/docs/screen-flow.mmd"
  screen_rules:          "projects/{project_name}/outputs/asis/docs/screen-rules.md"
  prototype_asis:        "projects/{project_name}/outputs/asis/docs/prototype-asis/"
```

### 3.2 `ava-asis-solution-delphi` — Removed output

**Removed artifact**: `asis/code-business-rules.md` (discontinued)

The `BusinessRuleRegistry[]` data extracted from `01_business_rules.json` in Step 3 is no longer written as a standalone file. Downstream consumers that needed BR IDs for code generation now read them from `asis/docs/business-rules.md` (Business Rules section).

---

## 4. Unified `business-rules.md` Format Specification

### Section 1: Business Rules (existing format preserved)

Supports both Formato A and Formato B from `parser-contracts.md`:

**Formato A (preferred):**
```markdown
## BR-001: Título da Regra
**Source**: NomeArquivo.pas — `NomeProcedure` procedure
**Rule**: Descrição completa da regra de negócio.
**Impact**: Impacto desta regra no sistema ou na migração.
**Priority**: MEDIUM
```

**Formato B (domain table):**
```markdown
## Domain: {NomeDomínio}
| ID | Category | Rule | Confirmed? |
|----|----------|------|------------|
| RN-XX-01 | BRN | Descrição da regra. | ✅ Code |
```

### Section 2: Functional Requirements (existing format preserved)

**Formato A (preferred):**
```markdown
## FR-001: Título do Requisito
**Module**: NomeDoModulo
**Description**: Descrição completa do requisito funcional.
**Priority**: HIGH
```

**Formato B (table by module):**
```markdown
## Module: Customer & Supplier
| FR-001 | Register client with CPF/CNPJ | CPF validated, record saved | frmClientesFornecedores |
```

### New trigger: `BRF` (combined single-pass generation)

A new `BRF` trigger is added to `ava-asis-documentation` that generates **both sections in one execution pass**:

1. Runs the VC-dependent FR extraction (same logic as `RF`)
2. Runs the FR-dependent BR mining (same logic as `RN`)
3. Writes the complete unified `business-rules.md` atomically

`trigger ALL` dispatches `BRF` instead of separate `RF` + `RN` calls (Level 2 of DAG, after VC). This eliminates one DAG level and establishes deterministic section ordering without upsert complexity.

Updated **ALL Trigger DAG** (v2.0.0):
```
Level 1 (parallel): VC + FT
Level 2 (parallel): BRF + RT   ← BRF replaces RF; RN level eliminated
Level 3 (sequential): PR        ← depends on RT + BRF
```

Individual triggers `RF` and `RN` are retained for partial/incremental runs and use upsert semantics (append/replace own section only).

### Invariants (unified file)

- Top-level header: `# Business Rules & Functional Requirements — {project_name} AS-IS`
- **Section order**: `## Functional Requirements` first, `## Business Rules` second (matches DAG: FR extraction precedes BR mining; FR is the primary entry point for downstream TO-BE agents)
- **Single-pass write (BRF / ALL)**: writes both sections atomically in declared order
- **Incremental write (upsert — RF or RN only)**: each individual trigger appends or replaces only its own section without overwriting the other
- FR cross-validation (FR↔value-chain) still runs in the RF/BRF skill and marks `[PENDENTE DE REVISÃO]` as before
- BR IDs: `BR-NNN` or `RN-XX-NN`; FR IDs: `FR-NNN` (all zero-padded, `:` separator)
- The `## ⚠️ Avisos de Validação` section (produced by FR cross-validation) goes at the end of `## Functional Requirements` subsection
- Parser `build_summary_comprehensive.py` will be updated to read both sections from the single file

---

## 5. Impacted Files Catalog

### Primary agents (output contract changes)

| File | Change | Version |
|---|---|---|
| `asis-diagnostic/agents/documentation-asis.md` | Add new `BRF` trigger (single-pass combined generation); update RF/RN skills to upsert into unified file; remove `functional-requirements.md` from Output Contract; update Skills table, DAG execution model, Output Verification, Pre-Completion Validation Checklist | v1.6.0 → v2.0.0 |
| `asis-diagnostic/agents/solution-delphi.md` | Remove `code-business-rules.md` from Step 3, Step 14, Output Contract, Input Contract table, and all inline references | v2.5.0 → v2.6.0 |

### Shared contracts

| File | Change |
|---|---|
| `asis-diagnostic/shared/parser-contracts.md` | Update `## functional-requirements.md` section header to `## Functional Requirements section (within business-rules.md)`; add note about unified file structure |
| `asis-diagnostic/shared/output-paths.md` | Remove `asis/docs/functional-requirements.md` row; update `asis/docs/business-rules.md` description |
| `asis-diagnostic/shared/artifact-size-governance.md` | Update size rules for the merged `business-rules.md` |

### Orchestrator & workflows

| File | Change |
|---|---|
| `asis-diagnostic/agents/orchestrator-asis.md` | Update deps references: `functional-requirements.md` → `business-rules.md` |
| `asis-diagnostic/workflows/analyze-delphi/steps/step-03-documentation.md` | Update expected output |
| `asis-diagnostic/workflows/analyze-delphi/steps/step-05-consolidation.md` | Update path |

### Summary agents & scripts

| File | Change |
|---|---|
| `summary/agents/summary-agent.md` | Update parser logic to read FR section from `business-rules.md` |
| `summary/agents/summary-validate-agent.md` | Update validation reference |
| `summary/workflows/generate-summary/steps/step-01-discover.md` | Remove `functional-requirements.md` row; update `business-rules.md` note |
| `summary/utils/build_summary_comprehensive.py` | Update artifact discovery list and `parse_func_reqs()` to read from `asis/docs/business-rules.md` (FR section) |
| `summary/utils/build_summary_complete.py` | Same — update artifact key path and parser function |
| `summary/utils/validate_summary.py` | Update `src` path and parser reference from `functional-requirements.md` to `business-rules.md` |

### TO-BE Architecture agents

| File | Change |
|---|---|
| `tobe-architecture/agents/adr-tobe.md` | Update Input Contract: `functional-requirements.md` → `asis/docs/business-rules.md` (FR section) |
| `tobe-architecture/agents/architecture-decision-matrix-tobe.md` | Same |
| `tobe-architecture/agents/architecture-design-tobe.md` | Same |
| `tobe-architecture/agents/docs-tobe.md` | Same |

### Prototype agent

| File | Change |
|---|---|
| `prototype/agents/prototype-agent.md` | Update Input Contract reference |

### QA agents

| File | Change |
|---|---|
| `qa-agents/agents/behavior-mapping-agent.md` | Update Input Contract: `functional-requirements.md` → `asis/docs/business-rules.md` |
| `qa-agents/agents/exploratory-agent.md` | Same |
| `qa-agents/agents/qa-orchestrator-agent.md` | Update verification step |
| `qa-agents/agents/test-case-generator-agent.md` | Update reference |

### Coder (tech-stack) agents — `code-business-rules.md` fallback removal

| File | Change |
|---|---|
| `tech-stack/agents/coder-dotnet-backend.md` | Remove `code-business-rules.md` fallback; single source `asis/docs/business-rules.md` |
| `tech-stack/agents/coder-angular-frontend.md` | Same |
| `tech-stack/agents/coder-go-backend.md` | Same |
| `tech-stack/agents/coder-java-backend.md` | Same |
| `tech-stack/agents/coder-python-backend.md` | Same |

### FastQA bridge

| File | Change |
|---|---|
| `asis-diagnostic/agents/bridge-fastqa-asis.md` | Update exclusion note to reference unified artifact |

---

## 6. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal: RF skill produces unified file (Priority: P1)

**Story**: Como orquestrador de migração, quero que `ava-asis-documentation` gere um único arquivo `business-rules.md` contendo regras de negócio E requisitos funcionais, para que agentes downstream precisem ler apenas um artefato.

**Acceptance Scenarios**:

1. **Given** a Delphi project where `ava-asis-documentation` runs with trigger `ALL`, **When** execution completes, **Then** `BRF` was dispatched and `asis/docs/business-rules.md` exists containing both `## Functional Requirements` and `## Business Rules` sections (in that order) with valid FR-NNN and BR-NNN IDs respectively.
2. **Given** the above, **When** execution completes, **Then** `asis/docs/functional-requirements.md` does NOT exist (no legacy file created).
3. **Given** the above, **When** execution completes, **Then** the FR cross-validation (FR↔value-chain) still runs and marks non-matching modules `[PENDENTE DE REVISÃO]` within the `## Functional Requirements` section.

---

### Scenario 2 — Nominal: solution-delphi does NOT produce code-business-rules.md (Priority: P1)

**Story**: Como arquiteto TO-BE, quero que `ava-asis-solution-delphi` não gere mais `code-business-rules.md` para evitar a manutenção de dois catálogos de regras de negócio.

**Acceptance Scenarios**:

1. **Given** `ava-asis-solution-delphi` runs on a Delphi project with `01_business_rules.json` available, **When** Step 3 (BusinessRuleRegistry) and Step 14 (Write Outputs) execute, **Then** `asis/code-business-rules.md` is NOT written to disk.
2. **Given** the above, **When** downstream coder agents reference business rules, **Then** they read from `asis/docs/business-rules.md` (single source) and find the BR-NNN IDs there.

---

### Scenario 3 — Edge Case: Trigger RF or RN run independently (Priority: P2)

**Story**: Se apenas um dos skills (RF ou RN) for executado isoladamente, o arquivo `business-rules.md` ainda deve ser válido e completo para a seção gerada. Quando o trigger `BRF` ou `ALL` for usado, ambas as sessões devem ser geradas de uma única vez.

**Acceptance Scenarios**:

1. **Given** only trigger `RN` is invoked, **When** `ava-asis-documentation` runs, **Then** `business-rules.md` contains the `## Business Rules` section; the `## Functional Requirements` section is absent (upsert — no stub written).
2. **Given** only trigger `RF` is invoked, **When** `ava-asis-documentation` runs, **Then** `business-rules.md` contains the `## Functional Requirements` section; the `## Business Rules` section is absent.
3. **Given** trigger `BRF` is invoked, **When** execution completes, **Then** `business-rules.md` contains **both** sections in declared order (`## Functional Requirements` then `## Business Rules`) and the file passes the Pre-Completion Validation Checklist.
4. **Given** trigger `ALL` is invoked, **When** execution completes, **Then** `BRF` is dispatched (not RF + RN separately) and both sections are present in one atomic write.

---

### Scenario 4 — Backward compatibility: summary parser reads both sections (Priority: P1)

**Story**: Como usuário do relatório executivo, quero que o Summary HTML continue exibindo métricas de FRs e BRs corretamente após a consolidação dos artefatos.

**Acceptance Scenarios**:

1. **Given** `asis/docs/business-rules.md` contains both sections, **When** `build_summary_comprehensive.py` parses it, **Then** FR count and BR count metrics are correctly extracted and displayed in the HTML summary.
2. **Given** `asis/docs/functional-requirements.md` does NOT exist, **When** `build_summary_comprehensive.py` runs, **Then** no error is raised — it reads from `business-rules.md` only.

---

### Scenario 5 — Coder agents: single source for BR IDs (Priority: P2)

**Story**: Como agente coder (.NET, Angular, Go, Java, Python), quero ter uma única fonte de verdade para IDs de regras de negócio (BR-NNNN) em vez de dois arquivos com lógica de fallback.

**Acceptance Scenarios**:

1. **Given** `asis/docs/business-rules.md` exists with the `## Business Rules` section, **When** any coder agent reads BR IDs, **Then** it reads from `asis/docs/business-rules.md` and does not reference `code-business-rules.md`.
2. **Given** `asis/docs/business-rules.md` does NOT exist, **When** a coder agent attempts to read BR IDs, **Then** it is BLOCKED with: `"asis/docs/business-rules.md não encontrado — executar ava-asis-documentation primeiro"`.

---

## 7. Quality Gate Requirements

- [ ] New `BRF` trigger added to `ava-asis-documentation` — generates both sections atomically; `trigger ALL` dispatches `BRF` (not RF + RN separately)
- [ ] `ava-asis-documentation` version bumped to `2.0.0` (MAJOR — output contract change)
- [ ] `ava-asis-solution-delphi` version bumped to `2.6.0` (MINOR — artifact removed)
- [ ] `functional-requirements.md` removed from all Input Contracts and output path lists
- [ ] `code-business-rules.md` removed from all Input Contracts and output path lists
- [ ] `business-rules.md` format documented in `parser-contracts.md` with both sections
- [ ] `build_summary_comprehensive.py`, `build_summary_complete.py`, and `validate_summary.py` updated to read FR section from `business-rules.md`
- [ ] All 22 agent files with `functional-requirements.md` references updated (grep audit)
- [ ] All 7 agent files with `code-business-rules.md` references updated (grep audit)
- [ ] Pre-Completion Validation Checklist in `documentation-asis.md` updated (6 artifacts, not 7)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 8. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| AS-IS Orchestrator | `ava-asis-orchestrator` | Dispatches `ava-asis-documentation`; dep references must be updated |
| Summary builder | `build_summary_comprehensive.py` | Parses artifact — must be updated to read unified file |
| Parser contracts | `parser-contracts.md` | Canonical format document — must be updated before agent bodies |

---

## 9. Exclusions

- The **content** of existing artifacts is not changed — only the file structure (merged vs. separate).
- `ava-asis-db-analyzer` artifacts are not affected.
- TO-BE code generation output is not affected.
- The AST extraction pipeline (`01_business_rules.json`) is not changed — only its downstream consumer (`solution-delphi.md`) stops writing `code-business-rules.md`.

---

## 10. Assumptions

- `business-rules.md` is the canonical output path for both BR and FR content after this change.
- The `## Business Rules` section uses the same IDs and formats as the current `business-rules.md`.
- The `## Functional Requirements` section uses the same IDs and formats as the current `functional-requirements.md`.
- The `build_summary_comprehensive.py` parser regex can be updated to look for section-scoped headers (`## Business Rules … ## BR-` and `## Functional Requirements … ## FR-`).
- No existing project output artifacts need to be migrated — only future pipeline runs use the new format.
- `bridge-fastqa-asis.md` exclusion note for `functional-requirements.md` is updated to reference the FR section of the unified file.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Artifact reduction | Pipeline produces 6 artifacts (down from 7 + 1 separate); `functional-requirements.md` and `code-business-rules.md` no longer written to disk |
| Single source of truth | All 22 agent files previously referencing `functional-requirements.md` now point to `asis/docs/business-rules.md` |
| Backward-compatible summary | Summary HTML shows same FR count, BR count, and module breakdowns as before the change |
| No broken coder agents | All 5 coder agents successfully read BR IDs from `asis/docs/business-rules.md` without fallback logic |
| Parser contract updated | `parser-contracts.md` documents the unified two-section format |

---

## Clarifications

### Session 2026-07-21

- Q: Which BR ID scheme governs the `## Business Rules` section in the unified file? → A: Existing `business-rules.md` definitions prevail (BR-NNN / RN-XX-NN). `code-business-rules.md` is discontinued; AST raw JSON (`01_business_rules.json`) remains accessible as source; no merge of AST rules into the unified file.
- Q: When individual triggers (RN or RF) run separately, how is the shared file written? → A: Append/upsert — each trigger writes only its own section; existing sections are preserved. `trigger ALL` always produces both sections in one pass.
- Q: Is updating `build_summary_comprehensive.py` in scope? → A: Yes — update `build_summary_comprehensive.py`, `build_summary_complete.py`, and `validate_summary.py` as part of this feature.
- Q: Should coder agents parse `business-rules.md` section-scoped (only `## Business Rules`) or whole-file? → A: Whole-file — `BR-` and `FR-` prefixes never clash; section-scoped parsing adds unnecessary complexity.
- Q: How to resolve section ordering vs. DAG execution order conflict? → A: Add new combined trigger `BRF` that generates both sections in one pass with deterministic order (`## Functional Requirements` first, `## Business Rules` second). `trigger ALL` dispatches `BRF` instead of separate RF+RN. Individual triggers retain upsert semantics.
