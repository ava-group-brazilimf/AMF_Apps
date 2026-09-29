# Tasks: DB-Analyzer Script Enforcement & AST Completeness Validation

**Input**: Design documents from `/specs/022-db-analyzer-script-enforcement/`

**Prerequisites**: spec.md (required)

**Note**: This feature modifies an existing LLM agent specification (`ava-asis-db-analyzer`, v1.4.0 → v1.5.0). There are no runnable code tasks — all work is editing the agent `.md` instruction file. No test tasks are included as this is an agent behavioral spec, not a software module with unit tests.

## Path Conventions

- Agent body: `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md`
- Pre-write validator: `src/shared/utils/validate_diagram.py`
- ER diagram generator: `src/shared/tools/gen_er_diagram.py`
- Mermaid guardrails: `src/modules/ava-fabric-agents/asis-diagnostic/shared/mermaid-guardrails.md`

---

## Phase 1: Setup (Verification)

**Purpose**: Verify environment and confirm files exist before modification

- [x] T001 Verify `db-analyzer.md` exists at `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md`
- [x] T002 Verify `gen_er_diagram.py` exists at `src/shared/tools/gen_er_diagram.py`
- [x] T003 Verify `validate_diagram.py` exists at `src/shared/utils/validate_diagram.py`
- [x] T004 Verify module.yaml entry for `ava-asis-db-analyzer` exists (no registration changes needed)

---

## Phase 2: Foundational (Agent Version & Frontmatter)

**Purpose**: Update agent identity and frontmatter to reflect v1.5.0

**⚠️ CRITICAL**: All subsequent tasks depend on this phase

- [x] T005 Update frontmatter version from `1.4.0` to `1.5.0` in `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md`
- [x] T006 Update frontmatter `description` to mention deterministic script execution and completeness validation (Portuguese)

**Checkpoint**: Frontmatter updated; agent now identifies as v1.5.0

---

## Phase 3: User Story 1 — Script Execution Enforcement (Priority: P1) 🎯 MVP

**Goal**: Ensure `er-diagram.mmd` is produced ONLY via `gen_er_diagram.py` execution, never by direct `Write`

**Independent Test**: After this phase, the agent body must contain a mandatory script invocation section for ER diagram generation and must explicitly prohibit writing `.mmd` files directly via `Write`.

### Implementation for User Story 1

- [x] T007 [P] Add `## ER Diagram Generation — Script Execution Gate` section in `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md`
- [x] T008 [P] Define the mandatory Bash command invocation for `gen_er_diagram.py` with `--project`, `--input`, and `--output` arguments in the new section
- [x] T009 [P] Specify piping output through `validate_diagram.py` with exit code handling (0=PASS, 1=FAIL/regenerate, 2=FIXED) → max 3 retry attempts
- [x] T010 Update the existing `er-diagram.mmd` line in `## Mandatory Write Step` to reference the Script Execution Gate instead of direct Write
- [x] T011 Strengthen the existing `> 🛑 PRE-WRITE VALIDATION GATE` block to explicitly prohibit `.mmd` generation for ER diagrams via Write — restrict the gate to other diagram types only (if any)

**Checkpoint**: Agent instructions now mandate script execution for ER diagram generation

---

## Phase 4: User Story 2 — AST Data Ingestion with DFM-to-DDL Transformation (Priority: P2)

**Goal**: Make the agent correctly consume `04_database_schemas.json` by transforming DFM unit-name-keyed data into DDL-compatible table definitions

**Independent Test**: After this phase, the `## AST Data Ingestion` section must describe a deterministic transformation from `_compaction: "table"` format (unit names, `_schema`/`_rows`) to the `payload.tables[]` + `payload.inferred_tables[]` format expected by downstream consumers.

### Implementation for User Story 2

- [x] T012 Add DFM-to-DDL transformation specification in `## AST Data Ingestion` section of `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md`
- [x] T013 Define unit-name-to-table-name rule: strip `U` prefix, convert `CamelCase` → `UPPER_SNAKE_CASE` (e.g., `UPontoMarcacao` → `PONTO_MARCACAO`)
- [x] T014 Define DFM-field-to-DDL-column mapping: map `_schema` headers (`delphi_type`, `name`) + `_rows` values to `{name, type}` column objects with simple types (`int`, `string`, `datetime`, `decimal`, `boolean`)
- [x] T015 Add format-validation branch: if `04_database_schemas.json` top-level keys do NOT contain `_compaction="table"`, emit structured warning and fall back to SQL-inline/connection-string path
- [x] T016 Update `## Input Contract` table to reflect the actual `_compaction="table"` + `_schema`/`_rows` format of `04_database_schemas.json` (remove reference to `payload.tables[]` DDL expectation)
- [x] T017 Ensure the transformation output is compatible with `gen_er_diagram.py` expected input format (`payload.inferred_tables[]` + `payload.tables[]` with `name` and `operations` fields)

**Checkpoint**: Agent can deterministically consume the real AST JSON format and produce valid input for the diagram generator

---

## Phase 5: User Story 3 — Completeness Assertion (Priority: P1)

**Goal**: Add post-generation validation that prevents silent data loss

**Independent Test**: After this phase, the agent must include a mandatory assertion step after all artifacts are generated, with explicit failure behavior (success=false, risk=critical, human_gate_required=true).

### Implementation for User Story 3

- [x] T018 Add `## Post-Generation Completeness Assertion` section in `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md`
- [x] T019 Define assertion formula: `diagram_entity_count >= 0.8 * schema_table_count` — where counts are tracked in-memory during generation (per Assumptions §9), not by reading generated files
- [x] T020 Define failure behavior: `AgentResult.success = false`, `AgentResult.risk.level = 'critical'`, `AgentResult.human_gate_required = true`, with diagnostic message listing actual vs expected counts
- [x] T021 Define skip condition: assertion is skipped when AST artifacts were not available (fallback path) or when `< 5` total tables (small schemas)
- [x] T022 Add assertion execution as final step before `## FASE OBRIGATÓRIA — Registro de Observabilidade`

**Checkpoint**: Agent now validates output completeness and blocks promotion on failure

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ensure version consistency, no regressions, and documentation alignment

- [x] T023 Update `## FASE OBRIGATÓRIA — Registro de Observabilidade` section to reference version `1.5.0` instead of `1.4.0`
- [x] T024 Add CHANGELOG.md entry for v1.5.0 describing the three fixes (script enforcement, DFM transformation, completeness assertion)
- [x] T025 Verify non-Delphi fallback paths are untouched (MySQL/MariaDB/Oracle/SQL Server agents remain unchanged)
- [x] T026 Verify `build_summary_comprehensive.py` parser contracts (5-column `Table Inventory` format) are preserved
- [x] T027 Cross-check `er-diagram.mmd` generation instructions against `mermaid-guardrails.md` for any syntax rule conflicts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only
- **Foundational (Phase 2)**: No dependencies — frontmatter update
- **User Story 1 (Phase 3 — Script Enforcement)**: Depends on Phase 2 (version bump)
- **User Story 2 (Phase 4 — AST Transformation)**: Depends on Phase 3 (script execution must be defined before diagram input format is specified)
- **User Story 3 (Phase 5 — Completeness)**: Depends on Phase 3 + Phase 4 (needs both generation method and data format to define assertion)
- **Polish (Phase 6)**: Depends on all implementation phases

### Execution Order Within User Stories

**User Story 1 (Script Enforcement)**:
1. Define new section heading (T007)
2. Define script invocation command (T008)
3. Define validation/retry logic (T009)
4. Wire into Mandatory Write Step (T010)
5. Restrict pre-write gate scope (T011)

**User Story 2 (AST Transformation)**:
1. Define transformation rules (T012–T014)
2. Add format-validation fallback (T015)
3. Update Input Contract documentation (T016)
4. Ensure generator compatibility (T017)

**User Story 3 (Completeness)**:
1. Define assertion section (T018)
2. Define formula (T019)
3. Define failure behavior (T020)
4. Define skip conditions (T021)
5. Position in execution flow (T022)

### Parallel Opportunities

- T007, T008, T009 (all in new section) can be drafted in parallel as they belong to the same new section
- T012, T013, T014 (transformation rules) can be drafted in parallel
- T018, T019, T020, T021 (assertion definition) can be drafted in parallel
- T023 through T027 (polish tasks) can be executed in parallel once implementation is complete

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Frontmatter update
3. Complete Phase 3: Script enforcement — this alone fixes the most critical bug (LLM inference instead of deterministic generation)
4. **STOP and VALIDATE**: Verify the agent body now mandates script execution for ER diagrams

### Incremental Delivery

1. Setup + Foundational → Agent identity updated
2. User Story 1 → Script enforcement in place → ER diagrams now deterministic
3. User Story 2 → AST transformation → Diagrams consume real data
4. User Story 3 → Completeness gate → Silent data loss prevented
5. Polish → Version consistency, changelog, regression check

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 27 |
| Setup Tasks | 4 |
| Foundational Tasks | 2 |
| US1 (Script Enforcement) Tasks | 5 |
| US2 (AST Transformation) Tasks | 6 |
| US3 (Completeness) Tasks | 5 |
| Polish Tasks | 5 |
| Parallel Opportunities | 3 groups |

**Suggested MVP Scope**: Complete up to Phase 3 (T001–T011) — this addresses the most critical issue (script non-execution) and makes ER diagrams deterministic immediately.
