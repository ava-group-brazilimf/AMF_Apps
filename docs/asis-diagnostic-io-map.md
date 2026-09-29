# F1 AS-IS Diagnostic — Agent Input/Output Map

> **Driven by**: `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` (v2.18.1; business-rules-generator references updated for v2.23)
> **Purpose**: canonical reference for every agent this orchestrator dispatches, what each one
> reads (inputs) and writes (outputs), and how their artifacts chain together.
> All paths are relative to `projects/{project_name}/outputs/` unless stated otherwise.
> Project config is always at `projects/{project_name}/context/project-config.yaml`.

---

## 1. Overview — Agents Dispatched

`orchestrator-asis.md` dispatches **16 top-level agent targets**, resolving to
**23 distinct implementing files** (4 `doc:*` skill triggers collapse into a
single `documentation-asis.md`; only one of the 5 legacy-language solution
agents fires per run, selected by `legacy_technology`).

| # | Agent ID (dispatch name) | Implementing file |
|---|---|---|
| 1 | `ava-asis-solution-delphi` (when `legacy_technology: delphi`) | `agents/solution-delphi.md` |
| 2 | `ava-asis-solution-vb` (when `vb6`) | `agents/solution-vb.md` |
| 3 | `ava-asis-solution-cobol` (when `cobol`) 🚧 STUB | `agents/solution-cobol.md` |
| 4 | `ava-asis-solution-vbnet` (when `vbnet`) 🚧 STUB | `agents/solution-vbnet.md` |
| 5 | `ava-asis-solution-powerbuilder` (when `powerbuilder`) 🚧 STUB | `agents/solution-powerbuilder.md` |
| 6 | `ava-asis-security-orchestrator` (conditional: `security_enabled_asis`) | `agents/security/security-orchestrator-asis.md` |
| 7 | `ava-asis-inventory` | `agents/inventory-asis.md` |
| 8 | `ava-asis-db-analyzer` | `agents/db-analyzer/db-analyzer.md` (→ `db-analyzer/skills/{mysql,mariadb,oracle,sqlserver}-agent.md`) |
| 9 | `ava-asis-events-pubsub` | `agents/events-pubsub-asis.md` |
| 10 | `doc:FT`/`VC`/`RT`/`PR` (documentation skills) | `agents/documentation-asis.md` — see §1a |
| 11 | `ava-asis-business-rules-generator` (conditional — dispatched when the solution agent produces `10_business_rule_cases.json`) | `agents/business-rules-generator-agent.md` |
| 12 | `ava-asis-gap-migration-analyzer` | `agents/gap-migration-analyzer.md` |
| 13 | `ava-asis-gaps-risks` | `agents/gaps-risks-asis.md` |
| 14 | `ava-asis-bridge-fastqa` | `agents/bridge-fastqa-asis.md` |

`ava-asis-security-orchestrator` additionally dispatches **7 security sub-agents**:

| Sub-agent ID | File |
|---|---|
| `ava-asis-security-sast` | `agents/security/sast-asis.md` |
| `ava-asis-security-iast` | `agents/security/iast-asis.md` |
| `ava-asis-security-threat-model` | `agents/security/threat-model-asis.md` |
| `ava-asis-security-taint` | `agents/security/taint-asis.md` |
| `ava-asis-security-dependency-config` | `agents/security/dependency-config-asis.md` |
| `ava-asis-security-pt-pattern` | `agents/security/pt-pattern-asis.md` |
| `ava-asis-security-review` | `agents/security/security-review-asis.md` |

**Not part of this DAG** (excluded from this map): `agents/security-review-asis.md`
(root level — `deprecated: true`, `replaced_by: agents/security/security-review-asis.md`)
and `agents/baseline-test-generator-asis.md` (manual/standalone trigger only).

### 1a. Documentation skill variants → single file

| Skill | Trigger | Output |
|---|---|---|
| Value Chain Mapper | `VC` | `docs/value-chain.md` |
| Screen Flow Mapper | `FT` | `docs/screen-navigation-map.md` + `docs/screen-flow.mmd` |
| Screen Rules Extractor | `RT` | `docs/screen-rules.md` |
| Prototype AS-IS | `PR` | `docs/prototype-asis/` |

> `RF` (FR Extractor) and `RN` (Business Rule Miner) were removed from `documentation-asis.md`
> — both functions now live in `ava-asis-business-rules-generator`, which produces the unified
> `docs/business-rules.md` (`## Functional Requirements` + `## Business Rules`) plus its JSON
> mirror `docs/business-rules.json`.

---

## 2. Per-Agent Input/Output Detail

### `ava-asis-orchestrator` — `agents/orchestrator-asis.md`
- **Inputs (dispatch/user-provided)**: `repository_path`, `legacy_technology` (`delphi|vb6|cobol|vbnet|powerbuilder`), `project_name`, `trace_id`, `scope_modules[]` (optional), `language` (`pt|en`, default `pt`)
- **Files read**: `context/project-config.yaml` (`project_name`, `repository_path`, `legacy_technology`, `security_enabled_asis`, `timing_benchmark_enabled`)
- **Outputs**: `asis/master-report.md`, `sub_reports[]` (see §3), plus in-band `risk_summary{score, level}`, `report_status`, `next_phase`, `execution_timing{...}`

### `ava-asis-solution-delphi` — `agents/solution-delphi.md` (v2.1.1+)
> ⚠️ Updated by `specs/007-solution-delphi-ast-consumption`,
> `specs/009-solution-delphi-test-coverage-artifact`, and
> `specs/010-asis-agents-ast-artifact-consumption` (path correction) — no
> longer matches the generic pattern below (that still applies to
> `-vb`/`-cobol`/`-vbnet`/`-powerbuilder`).
- **Inputs (primary — 9 deterministic AST JSON artifacts, no raw source reading for covered analyses)**:
  `asis/ast-raw/{language}/compressed/{01_business_rules,02_form_business_rules,03_database_rules,04_database_schemas,05_procedures,06_integrations,07_apis,08_code_overview,09_test_coverage}.json`
  (the token-optimized variant — `extraction/` is pretty-printed/raw-fidelity only, not meant for LLM context; produced by `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py`, Step 0 — a single invocation, skipped entirely if all 9 files already exist). See the agent's own `## Input Contract` for the full per-file mapping.
- **Inputs (narrow accepted exception)**: the single `.dpr` project file (bootstrap/creation order — not covered by any AST artifact).
- **Inputs (degraded fallback only, if Step 0 fails)**: repository source directly (`.pas`/`.dfm`/`.dpr`/`.dpk`), with a `AST_UNAVAILABLE_DEGRADED_ANALYSIS` risk flag recorded.
- **Dispatch params**: `project_name`, `repository_path`, `trace_id`, `language`
- **Outputs**:
  - `asis/architecture-blueprint.md` (**enriched**, v2.1.0 — `NO_AUTOMATED_TEST_COVERAGE` Migration Readiness risk sourced from `09_test_coverage.json`, no new file), `asis/pattern-classifications.json`, `asis/bounded-context-map.md`
  - `asis/code-business-rules.md` (**new**, v2.0.0 — code-mined via `01_business_rules.json`; distinct from `ava-asis-documentation`'s doc-mined `asis/docs/business-rules.md`)
  - `asis/data-access-profile.md`, `asis/vcl-lifecycle-map.md`
  - `asis/api-map.md`, `asis/db/data-structure.md`, `asis/code-usage-analysis.md`
  - `asis/file-export-dependencies.md`, `asis/file-import-dependencies.md`, `asis/external-dependencies.md`
  - `asis/diagrams/architecture-blueprint.mmd`
  - `asis/diagrams/c4-{context,container,component}.mmd`
  - `asis/diagrams/component-diagram.mmd`
  - `asis/diagrams/diagrama-sequencia-{acao}-{modulo}.mmd` (min 2)
  - **No `.drawio` outputs** (removed in v2.0.0 — consolidated `.drawio` views are synthesized downstream from `.mmd` by `summary/utils/generate_drawio_from_mermaid.py` at Summary-build time)
  - **Mandatory subset** (checked by orchestrator `verify_artifacts()`): `architecture-blueprint.md`, `pattern-classifications.json`, `bounded-context-map.md`, `diagrams/architecture-blueprint.mmd`, `diagrams/c4-{context,container,component}.mmd`, `diagrams/component-diagram.mmd`, `diagrams/diagrama-sequencia-*.mmd` (min 2)

### `ava-asis-solution-{vb|cobol|vbnet|powerbuilder}` — `agents/solution-{vb|cobol|vbnet|powerbuilder}.md` (unchanged by this PBI)
- **Inputs (files)**: repository source directly (VB6-equivalent of `.pas`/`.dfm`/`.dpr`/`.dpk`/`.fmx`). No AST tool integration yet (DelphiAST is Delphi-specific) — no upstream agent-artifact dependency.
- **Dispatch params**: `project_name`, `repository_path`, `trace_id`, `language`
- **Outputs**: same shape as solution-delphi's pre-v2.0.0 contract, **including `.drawio` files** (unaffected by this PBI — tracked as a separate follow-up):
  - `asis/architecture-blueprint.md`, `asis/pattern-classifications.json`, `asis/bounded-context-map.md`
  - `asis/data-access-profile.md`, `asis/ui-lifecycle-map.md`
  - `asis/api-map.md`, `asis/db/data-structure.md`, `asis/code-usage-analysis.md`
  - `asis/file-export-dependencies.md`, `asis/file-import-dependencies.md`, `asis/external-dependencies.md`
  - `asis/diagrams/architecture-blueprint.mmd`
  - `asis/diagrams/c4-{context,container,component}.mmd` (+ `.drawio`)
  - `asis/diagrams/component-diagram.mmd` (+ `.drawio`)
  - `asis/diagrams/diagrama-sequencia-{acao}-{modulo}.mmd` (min 2, + `.drawio`)
  - `asis/diagrams/diagrama-componentes.drawio` (consolidated)
  - Stub agents (cobol/vbnet/powerbuilder) return `implementation.status: STUB`, `artifacts_confirmed: false`, empty `outputs_generated[]`
  > ⚠️ See §4 Discrepancy 1 — path segment mismatch vs. orchestrator/shared docs.

### `ava-asis-security-orchestrator` — `agents/security/security-orchestrator-asis.md`
- **Inputs**: required `project_name`, `trace_id`, `agent_chain`, `repository_path`, `legacy_technology`, `tech_stack[]`; optional `source.type`, `business_domain`, `environments[]`, `criticality`, `dependency_files[]`, `iac_files[]`, `previous_reports[]`, `sensitive_data_types[]`, `force_full_artifact_generation`, `output_format`, `sla_correction`, `responsible_teams{}`. Falls back to `project-config.yaml` for `repository_path`/`legacy_technology`/`tech_stack[]`.
- **Outputs** (all under `asis/`): `security-map.md`, `vulnerabilities.md`, `compliance-gaps.md`, `security/security-findings.json`, `security/executive-security-summary.md`, `security/technical-findings-report.md`, plus every sub-agent JSON (`security/{sast,threat-model,taint,iast,dependency-config,pt-pattern,security-review}-asis.json`) and their merged markdown artifacts (see sub-agent table below).

#### Security sub-agents — common input pattern
All 7 receive (dispatch params): `trace_id`, `agent_chain`, `known_finding_ids[]`, `project_name`, `repository_path`, `legacy_technology`, `tech_stack[]`, `business_domain`, `criticality`, `sensitive_data_types[]`, `language`, `force_full_artifact_generation`, plus a per-agent `source.type` (sast: `code|diff|repository-snapshot`; iast: `runtime-log|log|trace|execution-output|test-output`; threat-model: `architecture_artifacts|functional_requirements|detected_stack|asis_outputs`; taint: `code|repository-snapshot|asis_outputs`; dependency-config: `manifest|config|iac|pipeline-config|nuget-manifest`; pt-pattern: `pentest-report|finding-report|finding-list|response-output|asis_outputs`).

| Sub-agent | Outputs |
|---|---|
| `security/sast-asis.md` | `asis/security/sast-asis.json` + `asis/security/privilege-matrix.md`, `secret-management-plan.md` |
| `security/iast-asis.md` | `asis/security/iast-asis.json` + `asis/security/runtime-security-validation.md` |
| `security/threat-model-asis.md` | `asis/security/threat-model-asis.json` + `asset-inventory.md`, `attack-surface.md`, `threat-model-stride.md` |
| `security/taint-asis.md` | `asis/security/taint-asis.json` + `taint-flow-report.md` |
| `security/dependency-config-asis.md` | `asis/security/dependency-config-asis.json` + `supply-chain-risk-report.md`, `SBOM.md`, `sbom.cyclonedx.json` (conditional), `license-compliance-report.md`, `iac-cicd-security-report.md` (conditional) |
| `security/pt-pattern-asis.md` | `asis/security/pt-pattern-asis.json` + `remediation-backlog.md`, `pt-pattern-correlation.md`, `remediation-and-regression.md` |
| `security/security-review-asis.md` | `asis/security/security-review-asis.json` + `owasp-coverage-matrix.md`; also **appends/dedups** into `asis/vulnerabilities.md`, `asis/security-map.md`, `asis/compliance-gaps.md` |

### `ava-asis-inventory` — `agents/inventory-asis.md`
- **Inputs**: repository source directly (no `## Input Contract` section)
- **Dispatch params**: `project_name`, `repository_path`, `legacy_technology`, `language`
- **Outputs**: `asis/inventory-report.md`, `asis/metrics.json`, `asis/complexity-map.md`, `asis/.internal/form-registry.json` (intermediate — consumed by `doc:FT`)

### `ava-asis-db-analyzer` — `agents/db-analyzer/db-analyzer.md` (+ skills)
- **Inputs**: repository source (connection strings, config files, SQL scripts) directly; no upstream-agent artifact reads
- **Dispatch params**: `project_name`, `repository_path`, `legacy_technology`, `language`
- **Outputs**: `asis/db/db-type.json`, `asis/db/schema-inventory.md`, `asis/db/er-diagram.mmd`, `asis/db/stored-procedures-map.md`, `asis/db/business-logic-in-db.md`, `asis/db/db-quality-report.md`, `asis/db/db-analysis-report.md` (consolidated)

### `ava-asis-events-pubsub` — `agents/events-pubsub-asis.md`
- **Inputs**: repository source directly, no upstream agent-artifact reads
- **Dispatch params**: `project_name`, `repository_path`, `legacy_technology`, `language`
- **Outputs**: `asis/events-pubsub-inventory.md`, `asis/events-pubsub-grid.json`, `asis/diagrams/events-pubsub-flow.mmd`, `asis/events-pubsub-risks.md`
  > See §4 Discrepancy 3 — missing from the orchestrator's own summary table (cosmetic).

### `ava-asis-documentation` (`doc:FT`/`VC`/`RT`/`PR`) — `agents/documentation-asis.md`
- **Inputs**: `context/project-config.yaml` (`language`); `asis/.internal/form-registry.json` ⬜ (FT, from inventory); repository source directly (VC, FT)
- **Dispatch params**: `project_name`, `repository_path`, `legacy_technology`, `language`, skill trigger
- **Outputs**: `asis/docs/value-chain.md` (VC), `asis/docs/screen-navigation-map.md` + `screen-flow.mmd` (FT), `asis/docs/screen-rules.md` (RT), `asis/docs/prototype-asis/` (PR, min 1 file)
  > `RF`/`RN` skills removed (v2.23) — see `ava-asis-business-rules-generator` below.

### `ava-asis-business-rules-generator` — `agents/business-rules-generator-agent.md`
- **Inputs**: `context/project-config.yaml` (`project_name`); `asis/ast-raw/{language}/compressed/10_business_rule_cases.json` (primary) or `asis/ast-raw/{language}/extraction/10_business_rule_cases.json` (fallback) — produced by the solution agent's Step 0 AST extraction; dispatch is conditional on this file existing
- **Dispatch params**: `project_name`, `split_by_bounded_context` (default `false`), `derive_functional_requirements` (default `true`), `insufficient_evidence_min_business_score` (default `0`), `batch_size` (default `20`)
- **Outputs**: `asis/docs/business-rules.md` (unified `## Functional Requirements` + `## Business Rules`, Formato A section headers), `asis/docs/business-rules.json` (deterministic JSON mirror, same `BR-000N`/`FR-000N` IDs), optional `asis/docs/business-rules-{bc_slug}.md` (when `split_by_bounded_context=true`)

### `ava-asis-gap-migration-analyzer` — `agents/gap-migration-analyzer.md`
- **Inputs** (JSON payload from orchestrator, not file-path-based): `trace_id`, `project_name`, `language`, `source_stack{...}`, `target_stack{...}`, `artifacts[]` (list of `{type, path, count}`), `analysis_scope`
- **Outputs**: `asis/gap-list-report.md`, `asis/gap-register.json`, `asis/gap-analysis-summary.md`

### `ava-asis-gaps-risks` — `agents/gaps-risks-asis.md`
- **Inputs** (true consolidation — no `## Input Contract`, reads directly from other agents' outputs per its Consolidation Algorithm):
  1. `architecture-blueprint.md` (solution agent)
  2. `business-rules.md` (ava-asis-business-rules-generator)
  3. `security-map.md` (security-orchestrator/review)
  4. `complexity-map.md` (inventory)
  5. `test-gaps.md` (test-qa)
  6. `schema-inventory.md` + `business-logic-in-db.md` (db-analyzer)
  7. `tobe/risk-mitigation-plan.md` (cross-phase, residual-risk skill only)
- **Dispatch params**: `project_name`, `trace_id`, `legacy_technology`
- **Outputs**: `asis/gaps-risks-report.md`, `asis/risk-register.json`, `asis/migration-risks-summary.md`, `tobe/risk-register-residual.json` (cross-phase, residual-risk skill only)

### `ava-asis-bridge-fastqa` — `agents/bridge-fastqa-asis.md` (v4.0.0)
- **Inputs (v4.0.0 — BLOCKING — hard stop se ausentes em ambos os caminhos)**:
  - `asis/ast-raw/{language}/compressed/01_business_rules.json` (primário) ou `asis/ast-raw/{language}/extraction/01_business_rules.json` (fallback)
  - `asis/ast-raw/{language}/compressed/02_form_business_rules.json` (primário) ou `asis/ast-raw/{language}/extraction/02_form_business_rules.json` (fallback)
  - `asis/ast-raw/{language}/compressed/03_database_rules.json` (primário) ou `asis/ast-raw/{language}/extraction/03_database_rules.json` (fallback)
  - `context/project-config.yaml` (`project_name`, `legacy_technology`)
  > ⚠️ Inputs descontinuados (não mais utilizados): `functional-requirements.md`, `business-rules.md`, `screen-rules.md`, `screen-navigation-map.md`, `value-chain.md`, `bounded-context-map.md`
- **Dispatch params**: `project_name` (dispatched via `dispatch_bridge_fastqa(project_name)` on trigger `BRG✓` — `ava-asis-business-rules-generator` completion; superseded the removed `doc:RF✓ + doc:RN✓`)
- **Outputs** (workspace-root-relative, **not** under `outputs/asis/`):
  - `fastqa/manual_test/US/PBI-{N}.md`
  - `fastqa/manual_test/gap_analysis/PBI-{N}_gaps.md`, `requirements_analysis/PBI-{N}_requirements.md`, `behavior_analysis/PBI-{N}_behaviors.md`
  - `fastqa/manual_test/test_cases/**/PBI-{N}.md`, `test_cases/PBI-{N}_test_plan.md`
  - Copy for orchestrator/Summary HTML: `asis/qa/test-plan.md` (min 3 KB)

---

## 3. Canonical Path Reference

`src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md` maintains
this same map, organized by agent group, and is the file `orchestrator-asis.md`
links to via `[TemplatesOutput]`/`[OutputPaths]`. It corroborates the map above
with two notable points:
- Test QA section there lists paths **without** the `qa/` segment (matches
  the orchestrator's own `artifact_contracts`, contradicting `test-qa-asis.md`
  itself — see §4.1).
- Golden Dataset Capture's `outputs/qa/` (not `outputs/asis/`) location is
  called out explicitly, "para serem consumidos diretamente pelo
  `ava-devops-compare-version` sem conversão de path."

---

## 4. Discrepancies Found

These are documentation/spec inconsistencies surfaced while building this
map — recorded here, not silently corrected, since resolving them requires a
decision about which file is authoritative.

### 4.1 Undocumented `test-qa:QA` skill

`orchestrator-asis.md`'s `dispatch_schedule.phase_b` references a
`test-qa:QA` dispatch (triggered on `RF✓+RN✓`), which gates
`golden-dataset-capture` (on `test-qa:QA✓`). `golden-dataset-capture-asis.md`
hard-requires `asis/qa/test-execution-plan-asis.md` and
`asis/qa/test-strategy-asis.md` as mandatory inputs — but `test-qa-asis.md`
(v3.0.0) documents no `QA` trigger, skill, or corresponding output anywhere
in its own file. This looks like an undocumented/unimplemented skill that
two other specs (the orchestrator) both assume
exists.

### 4.2 `ava-asis-events-pubsub` missing from summary table

Present in the DAG diagram, `dispatch_schedule`, and `artifact_contracts` of
`orchestrator-asis.md`, but absent from its "Agent Team Gerenciado" markdown
table. Cosmetic documentation gap only — does not affect execution.

---

## 5. Cross-Agent Consumption Summary

| Consuming agent | Reads from | Relationship |
|---|---|---|
| `ava-asis-documentation` (FT skill) | `asis/.internal/form-registry.json` (inventory) | optional enrichment |
| `ava-asis-business-rules-generator` | `10_business_rule_cases.json` (solution agent's AST extraction) | conditional — dispatch skipped if the file is absent |
| `ava-asis-gaps-risks` | 7 upstream artifacts (architecture-blueprint, business-rules, security-map, complexity-map, test-gaps, schema-inventory, business-logic-in-db) | true consolidation |
| `ava-asis-bridge-fastqa` | AST JSON artifacts (3 mandatory — `compressed/` primary, `extraction/` fallback; hard stop if absent from both) | hard-blocking on all three |
| `ava-asis-gap-migration-analyzer` | orchestrator-curated `artifacts[]` list | indirect — via orchestrator payload, not direct sibling reads |
| `ava-asis-gaps-risks` vs. `ava-asis-gap-migration-analyzer` | **no dependency either direction** (confirmed via direct read — zero cross-references) | independent, reconciled only later at the orchestrator's Consistency Gate |
| `ava-asis-orchestrator` (master-report) | effectively all of the above, via Consistency Gate checks C2–C8 | final consolidation |
