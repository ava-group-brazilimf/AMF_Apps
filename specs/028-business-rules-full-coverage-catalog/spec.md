# Agent Specification: Business Rules Full-Coverage Catalog

**Feature Branch**: `028-business-rules-full-coverage-catalog`
**Created**: 2026-07-24
**Status**: Draft
**Change Type**: `modify-existing`
**Input**: Guarantee that 100% of the business rules mapped by the deterministic AST extraction (`01_business_rules.json` + `02_form_business_rules.json`) are present in the AS-IS business-rules output consumed by downstream migration phases.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (documentation-asis.md) MUST remain in
> **Brazilian Portuguese** per Constitution Article V. The new Python utility
> follows the existing `utils/` convention (Portuguese docstrings/logs).

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (agent) + `new` (deterministic utility) |
| **Phase** | `F1` (AS-IS Diagnostic) |
| **Primary Agent** | `ava-asis-documentation` (v2.0.0 → v3.0.0 — MAJOR, output contract change) |
| **New Utility** | `business_rules_catalog_generator.py` (infra, not an agent — no `module.yaml` entry, mirrors `module_partitioner.py`) |
| **Pipeline** | `run_delphi_ast_analysis.py` — new Step 0.7 |
| **Downstream consumers updated** | `coder-dotnet-backend`, `coder-go-backend`, `coder-java-backend`, `coder-python-backend`, `coder-angular-frontend` (Input Contract → prefer catalog) |
| **Version Bump** | MAJOR for `ava-asis-documentation` (new required output `business-rules-catalog.json`; RN protocol reworked from transcription to catalog-read) |

---

## 2. Problem Statement

`processaERP-005/outputs/asis/docs/business-rules.md` contained only **8 Business Rules**
explicitly labelled a *"amostra representativa"* of the **4.254 rules** detected by the
deterministic AST extractor — a ~99.8% loss of behavioral rules that downstream migration
phases (TO-BE architecture, codegen, test-plan) depend on.

**Root cause:**
1. `business-rules.md` is produced by an **LLM agent** (`ava-asis-documentation`, skill RN).
   An LLM cannot reliably transcribe thousands of discrete AST records into Markdown — it
   summarizes/samples.
2. The agent's instructions self-conflict: *"Mapear 100% Regras de Negócio"* vs.
   `artifact-size-governance.md`'s **INVARIANTE ABSOLUTA** (600 KB hard limit *"tem
   prioridade sobre completude"*). 4254 BRs ≈ ~2 MB. The LLM resolved the conflict by
   sampling and pointing at the raw JSON.
3. Wrong tool: lossless enumeration of structured AST data is a **deterministic
   transformation**, already an established pattern in the repo (`module_partitioner.py`,
   `sql_ir_generator.py`).

**Fix:** A deterministic utility enumerates 100% of the rules into
`business-rules-catalog.json` (lossless source of truth), run automatically in the
post-extraction pipeline. `business-rules.md` becomes a curated human summary that points
to the catalog. Downstream consumers read the catalog for the exhaustive set.

---

## 3. Output Contract

```yaml
outputs:
  business_rules_catalog: "projects/{project_name}/outputs/asis/docs/business-rules-catalog.json"
  business_rules_md:      "projects/{project_name}/outputs/asis/docs/business-rules.md"  # curated summary (existing)
```

- `business-rules-catalog.json` — new canonical artifact. Schema + parity invariants
  documented in `parser-contracts.md` § "business-rules-catalog.json".
- `business-rules.md` § "Business Rules" — curated summary; MUST open with a coverage note
  stating `counts.total` and linking the catalog (never "amostra" without the pointer).

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 - Nominal Path (Priority: P1) 🎯 MVP

**Story**: Como orquestrador de migração, quero que 100% das regras de negócio detectadas
pelo AST estejam disponíveis em um artefato lossless, para que o codegen implemente todas as
regras sem perda.

**Acceptance Scenarios**:

1. **Given** a Delphi project with `01_business_rules.json` (`payload.counts.total = N`) and `02_form_business_rules.json`, **When** `run_delphi_ast_analysis.py` runs, **Then** `business-rules-catalog.json` exists with `counts.from_01 == N` and `counts.total == count(rules)`, and the process exits 0.
2. **Given** the above, **When** the catalog is written, **Then** every rule carries `id`, `category`, `unit`, `source`, and `domain_relevant`, and no rule from the source JSONs is missing.

### Scenario 2 - Edge Case: Missing/Empty AST (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a project where `01_business_rules.json` and `02_form_business_rules.json` are absent, **When** the generator runs, **Then** it writes a catalog with `counts.total: 0` and exits 0 (non-blocking).
2. **Given** `legacy_technology != "delphi"`, **When** the documentation agent runs RN, **Then** it falls back to source-code discovery and does not require the catalog.

### Scenario 3 - Quality Gate: Parity Violation (Priority: P1)

**Why this priority**: Safety gate — silent rule loss must be impossible.

**Acceptance Scenarios**:

1. **Given** the decoded rule count from `01` does not match `payload.counts.total`, **When** the generator runs, **Then** it logs `❌ PARIDADE 01 falhou` and exits with code **1** (nothing written silently as complete).
2. **Given** the RN skill executes with a Delphi AST available, **When** it writes `business-rules.md`, **Then** the `## Business Rules` section opens with the coverage note pointing to the catalog and never reports an "amostra" without that pointer.

---

## 5. Quality Gate Requirements

- [ ] `business-rules-catalog.json` `counts.total == counts.from_01 + counts.from_02_validations == len(rules)`
- [ ] `counts.from_01 == payload.counts.total` of `01_business_rules.json` (zero loss)
- [ ] Parity mismatch → generator exit code 1
- [ ] Generator is deterministic (no LLM), runs in the post-extraction pipeline
- [ ] `documentation-asis.md` frontmatter version bumped to `3.0.0`
- [ ] Downstream coder Input Contracts prefer `business-rules-catalog.json`
- [ ] No technology versions hardcoded
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Producer | Reason |
|---|---|---|
| `01_business_rules.json`, `02_form_business_rules.json` | `ava-fabric-delphi-analyzer` (AST extraction) | Source of the rules to enumerate |
| `run_delphi_ast_analysis.py` pipeline | AS-IS orchestration | Hosts Step 0.7 that invokes the generator |

---

## 7. Exclusions

- Human-readable narrative/curation of rules — remains in `business-rules.md` (LLM agent).
- Rule *classification/priority* semantics beyond `domain_relevant` heuristic — out of scope.
- Non-Delphi legacy technologies — keep existing source-code fallback (no catalog).

---

## 8. Assumptions

- The AST artifacts use the compressed string encodings decoded by the generator
  (`__buckets:type` for `01`; `[N]{schema}` + embedded-JSON `fields` for `02`).
- `project-config.yaml` exists; optional `business_rules_ui_units` overrides the UI-noise heuristic.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| 100% coverage | `business-rules-catalog.json` `counts.from_01 == 01_business_rules.json payload.counts.total` |
| No silent loss | Parity mismatch → exit 1 |
| Downstream ready | Coder agents read the catalog as authoritative BR set |
| No regression | `build_summary_comprehensive.py` still parses `business-rules.md` |
