# F2 TO-BE Architecture — Agent Input/Output Map

# F2 TO-BE Architecture — Agent Input/Output Map

> **Driven by**: `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` (v2.3.0)
> **Purpose**: canonical reference for every agent this orchestrator dispatches across phases
> 0-Pre through 8 of the TO-BE architecture pipeline (F2), what each one reads (inputs) and
> writes (outputs), how their artifacts chain together, and where the documentation is
> internally inconsistent.
> All paths are relative to `projects/{project_name}/outputs/` unless stated otherwise.
> Project config is always at `projects/{project_name}/context/project-config.yaml`.

---

## 1. Overview — Agents Dispatched

`orchestrator-tobe.md` dispatches **20 implementing files inside `tobe-architecture/agents/`**
(one of which, `migration-plan-tobe.md`, is invoked 4 times under different triggers across
3 phases, and one, `docs-tobe.md`, is invoked twice under different triggers), plus
**3 cross-module agents** (one AS-IS skill reused for residual risk, one tech-stack research
agent read as an optional input, and one tech-stack build-validation agent whose ownership is
disputed — see §4), plus **1 ambiguous codegen dispatch** resolved dynamically from
`tobe_stack.backend_framework`, plus **3 `deliverables/` module agents** invoked at the very
end of the pipeline (post-Fase 8 gates) that are out of the primary architecture-design scope
and are only listed here for completeness.

| #  | Phase                               | Agent ID / dispatch                                                                                 | Implementing file                                     | Notes                                                                             |
| -- | ----------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------- |
| 1  | 0-Pre                               | `architecture-decision-matrix-tobe.md`                                                            | `agents/architecture-decision-matrix-tobe.md`       | Produces`decision_matrix_result`, hard gate for Fase 0                          |
| 2  | 0                                   | `adr-tobe.md` (`ava-tobe-adr`)                                                                  | `agents/adr-tobe.md`                                | Generates all 8 ADRs +`INDEX.md`                                                |
| 3  | 1                                   | `architecture-design-tobe.md` (`ava-tobe-architecture-design`), triggers `CB`→`BC`→`TD` | `agents/architecture-design-tobe.md`                | Blueprint, Bounded Contexts, 5 detailed diagrams                                  |
| 4  | 1.4                                 | `database-policy-tobe.md`, trigger `DBP`                                                        | `agents/database-policy-tobe.md`                    | Renders corporate`sql-strategy.md.j2` policy                                    |
| 5  | 1.5                                 | `database-design-tobe.md`, trigger `DB`                                                         | `agents/database-design-tobe.md`                    | DB design report + TO-BE ERD                                                      |
| 6  | 1.6                                 | `security-design-tobe.md`                                                                         | `agents/security-design-tobe.md`                    | Also re-entered in**Modo B** during Fase 5.5 for CVE remediation            |
| 7  | 2                                   | `architecture-technical-tobe.md`, triggers `SS`→`NP`→`CS`→`QG`→`TF`→`PA`         | `agents/architecture-technical-tobe.md`             | Tech Framework Document,`Directory.Packages.props`, `patterns-applied.json`   |
| 8  | 2.5                                 | `migration-plan-tobe.md`, trigger `backlog-tobe`                                                | `agents/migration-plan-tobe.md`                     | Preliminary TO-BE backlog (Steps B1–B5)                                          |
| 9  | 2.7                                 | `migration-plan-tobe.md`, trigger `WM`                                                          | `agents/migration-plan-tobe.md`                     | Wave composition —`wave-model.json` (FP/SP = 0 placeholders)                   |
| 10 | 3                                   | `measure-size-tobe.md`                                                                            | `agents/measure-size-tobe.md`                       | IFPUG sizing; updates`wave-model.json` FP/SP in place                           |
| 11 | 4                                   | `migration-plan-tobe.md` (main invocation, Steps 5–6.5–8 + A1–A3)                              | `agents/migration-plan-tobe.md`                     | Derived artifacts from the wave model (gap-list, Gantt, ADO items, activity plan) |
| 12 | 4.2 (conditional)                   | `migration-plan-tobe.md`, trigger `WCR`                                                         | `agents/migration-plan-tobe.md`                     | Only after a PILOT or Strategy Align feedback; otherwise skipped                  |
| 13 | 4.3                                 | `coexistence-strategy-tobe.md` (`ava-tobe-coexistence-strategy`)                                | `agents/coexistence-strategy-tobe.md`               | AS-IS↔TO-BE coexistence strategy + matrix                                        |
| 14 | 4.5                                 | `risk-mitigation-tobe.md`                                                                         | `agents/risk-mitigation-tobe.md`                    | Risk mitigation plan                                                              |
| 15 | 4.6                                 | `@ava-asis-gaps-risks`, trigger `"gerar risk-register-residual.json"`                           | `asis-diagnostic/agents/gaps-risks-asis.md`         | **Cross-module** — AS-IS skill re-invoked for residual risk register       |
| 16 | 4.61                                | `openapi-spec-tobe.md` (`ava-tobe-spec`), trigger `OA-BC` per BC                              | `agents/openapi-spec-tobe.md`                       | Design-first OpenAPI 3.1 per bounded context; hard gate before codegen            |
| 17 | 4.65                                | `ava-stack-docs-researcher`                                                                       | `tech-stack/agents/docs-researcher-agent.md`        | **Cross-module, optional/non-blocking** — cached 24h, consumed by codegen  |
| 18 | 4.7                                 | `{resolved_coder_agent}`, trigger `SC` per BC                                                   | **Ambiguous** — see §4.1                      | Resolved from`tobe_stack.backend_framework` via `CODER_AGENTS` map            |
| 19 | 5.5                                 | `ava-stack-build-validator` (per orchestrator text)                                               | `tech-stack/agents/build-validator-agent.md`        | **Ownership disputed** — see §4.2                                         |
| 20 | 5                                   | `docs-tobe.md` (`ava-docs-tobe`), trigger `OA`                                                | `agents/docs-tobe.md`                               | Unified`openapi-spec.yaml` + `api-map.md`                                     |
| 21 | 5.2                                 | `docs-tobe.md`, trigger `RN`                                                                    | `agents/docs-tobe.md`                               | `regras-negocio.md` (AS-IS → TO-BE business rules)                             |
| 22 | 5.1                                 | `developer-guide-tobe.md` (`ava-developer-guide-tobe`), trigger `DG`                          | `agents/developer-guide-tobe.md`                    | `wiki/developer-guide.md`                                                       |
| 23 | 6                                   | `test-plan-tobe.md` (`ava-test-plan-tobe`), trigger `TP`                                      | `agents/test-plan-tobe.md`                          | Full test plan + test-cases + gap-analysis + traceability          |
| 24 | 7 (undocumented phase — see §4.3) | `user-journeys-tobe.md` (`ava-tobe-user-journeys`)                                              | `agents/user-journeys-tobe.md`                      | BDD user journeys (happy/sad path)                                                |
| 25 | 7.5                                 | `designer-system-tobe.md` (`ava-tobe-designer-system`), trigger `DS`                          | `agents/designer-system-tobe.md`                    | Angular Design System catalog                                                     |
| 26 | 8 (undocumented phase — see §4.3) | `azure-infra-estimator-tobe.md` (`ava-tobe-azure-infra-estimator`)                              | `agents/azure-infra-estimator-tobe.md`              | Azure SKU matrix + cost estimates                                                 |
| 28 | Gate F2→F3                         | `ava-requestor-inspection`                                                                        | `deliverables/agents/requestor-inspection-agent.md` | Out of primary scope — human sign-off packaging                                  |
| 29 | Step F1                             | `ava-deliverable-strategy-align`                                                                  | `deliverables/agents/strategy-align-agent.md`       | Out of primary scope — PM-led session materials                                  |
| 30 | Step F2                             | `ava-deliverable-package-approval-doc`                                                            | `deliverables/agents/package-approval-doc-agent.md` | Out of primary scope — Human SME sign-off packet                                 |

**Non-dispatched skills worth noting**: `docs-tobe.md` also defines triggers `AD` (ADR Writer),
`TD` (Technical Design Document), `RM` (README per module), `CL` (CHANGELOG), `WK` (wiki
publish) and `RQ` (Requirements traceability, producing `functional-requirements-tobe.md`) —
**none of these 6 triggers are ever invoked by `orchestrator-tobe.md`** in any phase section.
They exist in the agent file but are not part of the documented pipeline DAG.

---

## 2. Per-Agent Input/Output Detail

### Fase 0-Pre — `architecture-decision-matrix-tobe.md` (`ava-tobe-architecture-decision-matrix`, v1.0.0)

- **Dispatch params**: `project_name`
- **Inputs (all blocking — read via canonical procedure, no fallback permitted)**:
  `src/shared/data/reference-architecture.yaml` (6 `architecture_styles`, 10 `decision_criteria`,
  5 `decision_guardrails` — fabricating values outside this file is explicitly forbidden),
  `context/project-config.yaml`, `context/shared-context.md`,
  `outputs/asis/master-report.md`, `outputs/asis/docs/bounded-context-map.md`,
  `outputs/asis/docs/business-rules.md`, `outputs/asis/docs/functional-requirements.md`,
  `outputs/asis/gaps-risks-report.md`, `outputs/asis/db/schema-inventory.md`
- **Outputs**: `outputs/tobe/docs/architecture-decision-matrix.md` + in-band `decision_matrix_result`
  block (consumed by `adr-tobe.md`)

### Fase 0 — `adr-tobe.md` (`ava-tobe-adr`, v1.1.0)

- **Dispatch params**: `project_name`, `decision_matrix_result` (from Fase 0-Pre)
- **Inputs (3 mandatory sources, no fallback)**: `context/shared-context.md`;
  `outputs/asis/docs/{business-rules,functional-requirements,screen-navigation-map,screen-rules,value-chain}.md`;
  `context/project-config.yaml`
- **Outputs**: `outputs/tobe/docs/decisions/ADR-{001..008}-{slug}.md` (8 files, canonical slugs,
  unconditionally overwritten) + `outputs/tobe/docs/decisions/INDEX.md`. Each ADR must cite ≥ 1
  concrete AS-IS evidence ID (`SEC-NNN`, `BR-NNN`, `FR-NNN`, `R-NNN`, `TG-NNN`) or is marked
  `Status: [INCOMPLETO]`, which hard-blocks Fase 1.

### Fase 1 — `architecture-design-tobe.md` (`ava-tobe-architecture-design`, v1.0.0), triggers `CB`→`BC`→`TD`

- **Dispatch params**: `project_name`, `language`
- **Inputs (blocking — all 8 ADRs are a hard gate before any trigger runs)**: the 8 ADR files +
  `docs/decisions/INDEX.md`; `context/project-config.yaml`;
  `outputs/asis/docs/{business-rules,functional-requirements,value-chain,screen-navigation-map}.md`;
  `outputs/asis/bounded-context-map.md`; `context/shared-context.md`
- **Outputs (per orchestrator's per-trigger tables)**:
  - `CB`: `outputs/tobe/docs/architecture-blueprint.md`, `outputs/tobe/diagrams/architecture-blueprint.mmd`, `outputs/tobe/architecture-blueprint.html`
  - `BC`: `outputs/tobe/docs/bounded-context-map.md`, `outputs/tobe/diagrams/context-map.mmd` + `.drawio`
  - `TD`: `outputs/tobe/diagrams/{c4-context,c4-container,c4-component,class-diagram,seq-arquitetural-tobe}.mmd` + matching `.drawio` for each
  - **Note**: the agent's own `## Output Contract` (line 786) is a **superset** that also lists
    `api_map`, `user_journeys`, `value_chain`, `value_chain_drawio`, `value_chain_mapping`,
    `er_diagram_tobe` (+`.drawio`), `designer_system`, `screen_coherence_review` — several of
    these overlap with artifacts owned by other dedicated agents. See §4.10.

### Fase 1.4 — `database-policy-tobe.md` (`ava-tobe-database-policy`), trigger `DBP`

- **Dispatch params**: `project_name`
- **Inputs**: `src/shared/data/policies/sql-strategy.version` (blocking), Jinja2 template
  `templates/reports/sql-strategy.md.j2` (blocking), `context/project-config.yaml` (blocking),
  `outputs/tobe/docs/decisions/ADR-002-database.md` (**hard gate — blocks Fase 1.4 entirely if
  absent**); `outputs/asis/db/{schema-inventory,stored-procedures-map,triggers-map}.md` and
  `outputs/tobe/docs/bounded-context-map.md` (all optional — render `[FONTE AUSENTE]` if missing,
  blocks only phase *approval*, not execution); `outputs/asis/docs/business-rules.md` (optional support)
- **Outputs**: `outputs/tobe/db/sql-strategy.md`, `outputs/tobe/db/.history/sql-strategy-{policy_version}-{trace_id}.md`, `outputs/tobe/db/sql-strategy.manifest.json`

### Fase 1.5 — `database-design-tobe.md` (`ava-tobe-database-design`), trigger `DB`

- **Dispatch params**: `project_name`
- **Inputs (blocking hard-stop gates)**: `outputs/tobe/docs/decisions/ADR-002-database.md`;
  `outputs/tobe/db/sql-strategy.md` (must exist with `template_version == policy_version`, i.e.
  Fase 1.4 must have completed); `context/project-config.yaml`. **Artifact-based (non-blocking
  enrichment)**: `outputs/asis/db/schema-inventory.md`, `outputs/asis/db/er-diagram.mmd`,
  `outputs/asis/docs/business-rules.md`, `outputs/asis/db/stored-procedures-map.md`
- **Outputs**: `outputs/tobe/docs/db-design-report.md`, `outputs/tobe/diagrams/mer-diagram-tobe.mmd`, `outputs/tobe/docs/db-design-report.html`

### Fase 1.6 — `security-design-tobe.md` (`ava-tobe-security-design`)

- **Dispatch params**: `project_name`, `skip_z-curve-remediation`
- **Inputs — Modo A (normal)**: `outputs/tobe/docs/decisions/ADR-003-security.md` (hard gate);
  `context/project-config.yaml`; `outputs/asis/security-map.md`; `outputs/asis/vulnerabilities.md`;
  `outputs/asis/compliance-gaps.md`; `outputs/asis/gap-register.json`;
  `outputs/tobe/docs/architecture-blueprint.md`
- **Inputs — Modo B (CVE remediation, re-entered during Fase 5.5)**: in-band `cve_handoff` payload
  built from the `cves` field of `build_gate_result` — no file reads, no ADR-003 requirement
- **Outputs**: `outputs/tobe/docs/security-architecture.md` (15 sections), `outputs/tobe/diagrams/security-architecture.mmd` + `.drawio`. Modo B returns only an in-band `{ outcome, action | alternative }` to the caller — it does not regenerate the markdown/diagram artifacts.

### Fase 2 — `architecture-technical-tobe.md` (`ava-tobe-architecture-technical`), triggers `SS`→`NP`→`CS`→`QG`→`TF`→`PA`

- **Dispatch params**: `project_name`
- **Inputs (blocking)**: all 8 ADRs (vinculantes — ADR always wins over config on conflict);
  `context/project-config.yaml`; `src/shared/data/patterns/{dotnet,angular,git}/*-patterns-reference.md` (read before trigger `CS`)
- **Outputs**: `outputs/tobe/docs/tech-framework-document.md`, `outputs/tobe/solution-structure.md`,
  `outputs/tobe/nuget-packages.md`, `outputs/tobe/source-code/Directory.Packages.props`,
  `outputs/tobe/coding-standards.md`, `outputs/tobe/config/{.editorconfig,stylecop.json,Directory.Build.props,quality-gates.md,sonar-project.properties}`,
  `outputs/tobe/patterns-applied.json`

### Fase 2.5 — `migration-plan-tobe.md`, trigger `backlog-tobe`

- **Dispatch params**: `project_name`
- **Inputs (blocking gate)**: `outputs/tobe/docs/tech-framework-document.md` (Fase 2) +
  `outputs/tobe/docs/bounded-context-map.md` (Fase 1); plus `context/project-config.yaml`,
  `context/shared-context.md`, `outputs/tobe/docs/architecture-blueprint.md`,
  `outputs/asis/docs/{business-rules,functional-requirements}.md`,
  `outputs/asis/bounded-context-map.md`, `outputs/tobe/db/`
- **Outputs**: `outputs/tobe/docs/backlog-tobe.md` (1 of the 14 canonical Output Contract files —
  explicitly footnoted by the agent itself as "input herdado, NÃO output do fluxo padrão")

### Fase 2.7 — `migration-plan-tobe.md`, trigger `WM`

- **Dispatch params**: `project_name`
- **Inputs**: `context/project-config.yaml`; `outputs/asis/inventory-report.md`;
  `outputs/asis/api-map.md`; `outputs/asis/db/data-structure.md`; `outputs/asis/bounded-context-map.md`;
  `outputs/asis/gaps-risks-report.md`; `outputs/asis/docs/{business-rules,functional-requirements}.md`;
  `outputs/tobe/docs/bounded-context-map.md`. Explicitly does **not** require `sizing-report.md`
  (that dependency was removed to break a former circularity with Fase 3).
- **Outputs**: `outputs/tobe/migration/wave-model.json` (FP/SP = 0 placeholders),
  `outputs/tobe/docs/integration-matrix.md`, `outputs/tobe/docs/tshirt-sizing-rationale.md`,
  `outputs/tobe/migration/migration-priority-matrix.md`

### Fase 3 — `measure-size-tobe.md` (`ava-tobe-measure-size`, v1.0.0)

- **Dispatch params**: `project_name`
- **Inputs (Prerequisite Gate — hard-blocking)**: `outputs/tobe/docs/backlog-tobe.md`
  (primary input, agent aborts entirely if absent); `outputs/tobe/migration/wave-model.json`
  (also hard-blocking). **Additional**: `context/project-config.yaml`, `context/shared-context.md`,
  `outputs/asis/inventory-report.md`, `outputs/tobe/docs/bounded-context-map.md`, `outputs/tobe/db/`
  (all logged as gaps if missing, not hard-blocking)
- **Outputs**: `outputs/tobe/docs/sizing-report.md`, `outputs/tobe/docs/effort-calculator.md`
  (uses template `templates/reports/effort-calculator.md.j2`), `outputs/tobe/docs/infra-sizing.md`,
  `outputs/tobe/docs/cost-estimate.md`, and an **in-place update** of
  `outputs/tobe/migration/wave-model.json` (fills `fp`/`sp` per BC and `total_fp`/`total_sp` per wave — no other field is touched)

### Fase 4 — `migration-plan-tobe.md` (main invocation)

- **Dispatch params**: `project_name`
- **Inputs**: `outputs/tobe/migration/wave-model.json` (updated in Fase 3, read as SSoT — not
  regenerated), `outputs/tobe/docs/sizing-report.md`, `outputs/tobe/docs/bounded-context-map.md`,
  `outputs/asis/gaps-risks-report.md`, `context/project-config.yaml`; inherited
  `outputs/tobe/docs/backlog-tobe.md`; already-generated Fase 2.7 artifacts (`integration-matrix.md`,
  `tshirt-sizing-rationale.md`, `migration-priority-matrix.md`); plus
  `outputs/asis/docs/{business-rules,functional-requirements}.md`,
  `outputs/tobe/docs/architecture-blueprint.md`, `outputs/tobe/docs/tech-framework-document.md`
- **Outputs**: `outputs/tobe/docs/{ai-estimation-report,manual-gap-list,migration-executive-summary,migration-plan,wave-plan,ado-work-items}.md`,
  `outputs/tobe/diagrams/migration-gantt.mmd` + `.drawio`,
  `outputs/tobe/migration/{migration-activity-plan,activity-dependency-graph}.md`.
  (Full Output Contract totals **14 files**, split 4 in Fase 2.7 + 10 here.)

### Fase 4.2 (conditional) — `migration-plan-tobe.md`, trigger `WCR`

- **Gate**: only runs if a PILOT wave produced `pilot-metrics.md`, OR `strategy-align-feedback.md`
  exists, OR the user explicitly requests `WCR` — otherwise this phase is **skipped** entirely
- **Inputs**: `outputs/tobe/docs/wave-plan.md`, `outputs/tobe/migration/migration-activity-plan.md`,
  `outputs/tobe/migration/migration-priority-matrix.md`,
  `outputs/tobe/migration/pilot-metrics.md` (if executed),
  `outputs/tobe/migration/strategy-align-feedback.md` (if available),
  `outputs/asis/docs/{business-rules,functional-requirements}.md`,
  `outputs/tobe/docs/bounded-context-map.md`
- **Outputs**: `outputs/tobe/migration/{wave-plan-refined,migration-priority-matrix-refined,wcr-changelog}.md`
  (3 extra files, not part of the 14-file base Output Contract)

### Fase 4.3 — `coexistence-strategy-tobe.md` (`ava-tobe-coexistence-strategy`, v1.0.0)

- **Dispatch params**: `project_name`
- **Inputs (4 blocking + 1 blocking config, 3 non-blocking)**: blocking —
  `outputs/tobe/migration/wave-model.json`, `outputs/tobe/docs/bounded-context-map.md`,
  `outputs/tobe/docs/integration-matrix.md`, `outputs/tobe/docs/architecture-blueprint.md`,
  `context/project-config.yaml`; non-blocking (marks `[FONTE AUSENTE]` / `CONFIDENCE: LOW`) —
  `outputs/asis/db/db-analysis-report.md`, `outputs/asis/events-pubsub-inventory.md`,
  `outputs/asis/gap-register.json`
- **Outputs**: `outputs/tobe/docs/coexistence-strategy.md` (8 sections),
  `outputs/tobe/docs/coexistence-matrix.md`, `outputs/tobe/diagrams/coexistence-architecture.mmd` + `.drawio`

### Fase 4.5 — `risk-mitigation-tobe.md` (`ava-tobe-risk-mitigation`)

- **Dispatch params**: `project_name`
- **Gate**: all 14 Output Contract files of the migration-plan agent (Fase 2.7 + 4) plus the 4
  Output Contract files of Fase 4.3 must exist and be non-empty (18 files total) before this
  phase can start
- **Inputs**: `outputs/asis/risk-register.json`, `outputs/asis/gap-list-report.md`,
  `outputs/tobe/migration-plan.md` ⚠️ (see §4.4 — path mismatch vs. the actual artifact),
  `outputs/asis/security-map.md`, `context/project-config.yaml`
- **Outputs**: `outputs/tobe/risk-mitigation-plan.md` (8 mandatory sections; hard invariant: 0 P0 without an owner)

### Fase 4.6 — `@ava-asis-gaps-risks` (**cross-module**, `asis-diagnostic/agents/gaps-risks-asis.md`)

- **Dispatch params**: `project_name`, `trace_id`, `legacy_technology`, trigger phrase `"gerar risk-register-residual.json"`
- **Gate**: `outputs/tobe/risk-mitigation-plan.md` (Fase 4.5) must exist
- **Inputs**: `outputs/asis/risk-register.json`, `outputs/tobe/risk-mitigation-plan.md`
- **Outputs**: `outputs/tobe/risk-register-residual.json` (same schema as `asis/risk-register.json`
  + 6 residual fields; only risks with `residual_score > 0` are kept; hard gate: 0 residual risks
    with `residual_score ≥ 20`)
- This is the same implementing file documented in `docs/asis-diagnostic-io-map.md` §2 for the
  AS-IS pipeline — the TO-BE orchestrator re-invokes it with a different trigger phrase for a
  cross-phase skill (residual risk), not a second copy of the agent.

### Fase 4.61 — `openapi-spec-tobe.md` (`ava-tobe-spec`), trigger `OA-BC` (once per BC)

- **Dispatch params**: `project_name`, BC identifier
- **Gate**: `outputs/tobe/docs/bounded-context-map.md` + `outputs/tobe/docs/architecture-blueprint.md` must exist
- **Inputs**: `outputs/tobe/docs/bounded-context-map.md`, `outputs/tobe/docs/architecture-blueprint.md`,
  `context/project-config.yaml`, `outputs/tobe/docs/decisions/ADR-004-backend.md`. Guardrail:
  paths/operationIds/schemas must be derivable strictly from `bounded-context-map.md` — nothing invented.
- **Outputs**: `outputs/tobe/docs/openapi/bc{NN}-{nome-bc-kebab}.yaml` (one file per BC, OpenAPI
  3.1.0). Explicitly does **not** produce the unified `openapi-spec.yaml` — that is `docs-tobe.md`'s job (Fase 5).
  ⛔ Hard gate: Fase 4.7 cannot start until every BC has its spec file confirmed.

### Fase 4.65 — `ava-stack-docs-researcher` (**cross-module**, `tech-stack/agents/docs-researcher-agent.md`, v1.0.0)

- Not directly invoked as a phase by `orchestrator-tobe.md` itself — it belongs to
  `ava-stack-orchestrator`'s own pipeline (Step 1.5) and is documented here only because Fase 4.7
  reads its output.
- **Output consumed downstream**: `outputs/tobe/docs/research/docs-research-bundle.md` (24h cache).
  Path matches exactly between the producer agent's Output Contract and the orchestrator-tobe's
  Fase 4.7 input table.

### Fase 4.7 — `{resolved_coder_agent}`, trigger `SC` (once per BC) — **see §4.1 for naming ambiguity**

- **Dispatch params**: `project_name`, BC identifier, `trace_id`, `language`
- **Resolution**: `orchestrator-tobe.md` reads `tobe_stack.backend_framework` from
  `project-config.yaml` and maps it via a hardcoded `CODER_AGENTS` dict to a short id
  (`coder-dotnet`, `coder-java-backend`, `coder-python-backend`, `coder-go-backend`, `coder-node-backend`)
- **Gate**: `outputs/tobe/docs/tech-framework-document.md` + `outputs/tobe/patterns-applied.json`
  (Fase 2) must exist; per-BC OpenAPI spec `bc{NN}-*.yaml` (Fase 4.61) must exist before any `.cs`/`.csproj` is written
- **Inputs (`coder-dotnet.md`, the tobe-architecture candidate)**: `outputs/tobe/docs/tech-framework-document.md`,
  `outputs/tobe/docs/bounded-context-map.md` (BC Existence Pre-condition — hard stop if file
  missing or BC not found), `context/project-config.yaml`, `outputs/tobe/docs/decisions/ADR-004-backend.md`,
  per-BC OpenAPI spec; **optional/non-blocking**: `outputs/tobe/docs/research/docs-research-bundle.md`
  (per the orchestrator's dispatch instructions — the agent file itself never mentions this input, see §4.1)
- **Outputs**: `outputs/tobe/source-code/{BC}.{Domain,Application,Infrastructure,API,Tests}/...`
  (fully artifact-based scaffold — no re-reading of full generated source, no reading of the
  legacy repository; see §3), plus the in-band `build_gate_result` block (`status`, `errors[]`,
  `cves[]`, `hintpath_violations[]`) required before the trigger can be declared `COMPLETED`.

### Fase 5.5 — Build & Security Validation Gate — **see §4.2 for ownership dispute**

- Not a new agent dispatch by itself — the orchestrator **consolidates** the `build_gate_result`
  blocks received from every Fase 4.7 `{resolved_coder_agent}` invocation, and (if CVEs on
  auth/crypto/transport/identity packages are found) hands off to `security-design-tobe.md` Modo B.
- Text in the phase body says validation is delegated to `ava-stack-build-validator`
  (`tech-stack/agents/build-validator-agent.md`) invoked by `ava-stack-orchestrator`'s Steps
  6a/8a — but the orchestrator's own "Agent Team Gerenciado" table lists Build Validator as one
  of *its own* managed agents at phase 5.5.

### Fase 5 — `docs-tobe.md` (`ava-docs-tobe`), trigger `OA`

- **Dispatch params**: `project_name`
- **Inputs**: `outputs/tobe/docs/bounded-context-map.md` (Fase 1), `outputs/tobe/docs/migration-plan.md`
  (Fase 4), `context/project-config.yaml`; API Map Generator sub-step additionally reads the
  freshly generated `openapi-spec.yaml` + `outputs/tobe/docs/user-journeys.md` (fallback: `[sem tela mapeada]` if absent)
- **Outputs**: `outputs/tobe/docs/openapi/openapi-spec.yaml` (unified, consolidates the per-BC
  `bcNN-*.yaml` files from Fase 4.61), `outputs/tobe/docs/api-map.md` (hard gate — trigger `OA`
  cannot be declared complete without it)

### Fase 5.2 — `docs-tobe.md`, trigger `RN`

- **Dispatch params**: `project_name`
- **Gate**: `outputs/tobe/docs/bounded-context-map.md` + `outputs/tobe/docs/architecture-blueprint.md` (Fase 1)
- **Inputs**: `outputs/asis/docs/{business-rules,functional-requirements,screen-rules}.md`,
  `outputs/tobe/docs/bounded-context-map.md`, `outputs/tobe/docs/architecture-blueprint.md`
- **Outputs**: `outputs/tobe/docs/regras-negocio.md` (100% AS-IS rule coverage required)

### Fase 5.1 — `developer-guide-tobe.md` (`ava-developer-guide-tobe`, v1.0.0), trigger `DG`

- **Dispatch params**: `project_name`
- **Gate**: `outputs/tobe/docs/tech-framework-document.md` (Fase 2)
- **Inputs (blocking)**: `context/project-config.yaml`, `outputs/tobe/docs/tech-framework-document.md`,
  `outputs/tobe/coding-standards.md`, `outputs/tobe/solution-structure.md`, `outputs/tobe/nuget-packages.md`.
  **Optional (agent's own Input Contract, wider than the orchestrator's 5-item table)**:
  `outputs/tobe/docs/migration-plan.md`, `outputs/tobe/docs/runbook.md` (never produced by any
  agent in this map), `outputs/tobe/docs/test-plan-tobe.md` ⚠️ (path mismatch — actual file is
  `outputs/tobe/qa/test-plan.md`, see §4.11), `outputs/tobe/docs/security-architecture.md`,
  `outputs/tobe/docs/architecture-blueprint.md`
- **Outputs**: `outputs/tobe/docs/wiki/developer-guide.md` (9 sections, frontmatter with `trace_id`/`version`/`tech_lead`)

### Fase 6 — `test-plan-tobe.md` (`ava-test-plan-tobe`, v3.1.0), trigger `TP`

- **Dispatch params**: `project_name`
- **Inputs (blocking)**: `context/project-config.yaml`, `outputs/tobe/docs/wave-plan.md`,
  `outputs/tobe/docs/migration-plan.md`, `outputs/tobe/docs/architecture-blueprint.md`,
  `outputs/asis/master-report.md`, `src/shared/checklists/wave-gonogo-checklist.md`,
  `outputs/asis/docs/business-rules.md`, `outputs/asis/docs/functional-requirements.md`,
  `outputs/asis/qa/test-strategy-asis.md` ⚠️, `outputs/asis/qa/test-execution-plan-asis.md` ⚠️
  (see §4.13 — both flagged `✅ obrigatório` but their producer is undocumented per the AS-IS
  map's own §4.2), `outputs/tobe/docs/architecture-technical.md` ⚠️ (see §4.6 — this file is
  never produced by any agent)
- **Inputs (optional, degrade gracefully)**: `outputs/tobe/docs/bounded-context-map.md`,
  `outputs/asis/gaps-risks-report.md`, `outputs/asis/gap-list-report.md`,
  `outputs/tobe/docs/business-rules-tobe.md` (also a naming mismatch — the actual file is
  `regras-negocio.md`, see §4.5), `outputs/tobe/docs/security-architecture.md`
- **Outputs**: `outputs/tobe/qa/test-plan.md`, `outputs/tobe/qa/functional-test-matrix.md`,
  `outputs/tobe/tests/traceability-matrix.md`, `outputs/tobe/tests/automatable-test-cases.md`
- **Full-source-read check**: no `repository_path` or `source-code/` reads found — purely
  artifact-based (see §3).

### Fase 7 (no dedicated phase section in the orchestrator — see §4.3) — `user-journeys-tobe.md` (`ava-tobe-user-journeys`)

- Listed in the "Agent Team Gerenciado" table as "7 — Jornadas do usuário + BDD" and dispatched
  in the timing/registry machinery, but **there is no `### Fase 7 —` body** in `orchestrator-tobe.md`
  defining its gate, inputs or outputs the way every other phase has. The following is derived
  entirely from the agent file itself.
- **Inputs (per the agent's own "Inputs Esperados" table)**: `outputs/asis/master-report.md`,
  `outputs/tobe/architecture-design.md` ⚠️ (never produced by any agent — see §4.9),
  `outputs/asis/bounded-context-map.md` ⚠️ (reads the **AS-IS** BC map, not the TO-BE one used
  by every sibling agent — see §4.9), `context/shared-context.md`
- **Outputs**: `outputs/tobe/user-journeys/user-journeys-report.md`, per-journey `.feature` files
  under `outputs/tobe/user-journeys/{happy-path,sad-path}/`, plus a mandatory combined-feature
  mirror at `outputs/tobe/tests/features/{journey-N-slug}.feature` consumed by the gherkin validation check

### Fase 7.5 — `designer-system-tobe.md` (`ava-tobe-designer-system`), trigger `DS`

- **Dispatch params**: `project_name`
- **Gate**: `outputs/tobe/docs/decisions/ADR-005-frontend.md`
- **Inputs**: ADR-005; `context/project-config.yaml`; `outputs/tobe/user-journeys/user-journeys-report.md`
  (if it exists); `outputs/tobe/docs/bounded-context-map.md` (fallback if Fase 7 wasn't run);
  `outputs/asis/docs/screen-flow.md` ⚠️ (see §4.7 — this exact filename is never produced by the
  AS-IS pipeline). Explicit invariant: only UI pattern *categories* may be derived — entity
  names, form fields and business rules must never be transcribed.
- **Outputs**: `outputs/tobe/designer-system.md` (DS-001..DS-010 minimum, WCAG 2.1 AA checklist, design tokens)

### Fase 8 (no dedicated phase section in the orchestrator — see §4.3) — `azure-infra-estimator-tobe.md` (`ava-tobe-azure-infra-estimator`, v1.0.0)

- Same gap as Fase 7 — listed in the Agent Team table and the timing tables ("Fase 8 — Infra"),
  referenced by the Migration Design Gate and by Step F1 as a completed artifact group, but has
  **no `### Fase 8 —` body**.
- **Inputs (Read Priority, in order)**: `outputs/tobe/sizing-report.md` ⚠️ (path mismatch — actual
  is `outputs/tobe/docs/sizing-report.md`, see §4.8), `outputs/tobe/architecture-design-tobe.md` ⚠️
  (never produced — actual is `outputs/tobe/docs/architecture-blueprint.md`), `outputs/asis/`
  (enrichment reads), and an optional inline `infra-params` override block pasted into the prompt.
  Because both preferred paths are wrong, this agent effectively always falls through to reading
  `outputs/asis/` directly and/or relying on the inline override.
- **Outputs**: `outputs/tobe/azure-infra/{metrics-snapshot.yaml,sku-matrix.md,cost-estimate-{dev,staging,prod}.md,tco-summary.md,assumption-audit.md,azure-infra-estimation-report.md}`,
  plus `READ-GATE-BLOCKER.md` only on failure

### Gate F2→F3 / Step F1 / Step F2 — `deliverables/` module agents (out of primary scope)

- `ava-requestor-inspection` (`deliverables/agents/requestor-inspection-agent.md`): reads the 9
  F2 artifact groups, writes `outputs/tobe/requestor-inspection/{requestor-inspection-index, requestor-inspection-checklist,requestor-inspection-package-report}.md`
- `ava-deliverable-strategy-align` (`deliverables/agents/strategy-align-agent.md`): writes
  `outputs/tobe/strategy-align/{session-agenda,strategy-align-record}.md`
- `ava-deliverable-package-approval-doc` (`deliverables/agents/package-approval-doc-agent.md`):
  writes `outputs/tobe/package-approval-doc/package-approval-document.md`
- These three are documented here only for completeness of "everything `orchestrator-tobe.md`
  dispatches" — their own Input/Output Contracts belong to the `deliverables/` module and are
  out of scope for a detailed breakdown in this map.

---

## 3. Full Source Re-Read Flags

The AS-IS pipeline was recently optimized so `solution-delphi.md` consumes pre-extracted AST
JSON artifacts instead of re-reading the entire legacy repository (see
`docs/asis-diagnostic-io-map.md` §2, `ava-asis-solution-delphi`). The same check was run against
every agent dispatched by `orchestrator-tobe.md`:

- **No agent reads `repository_path` or the legacy source tree directly.** A repo-wide grep for
  `repository_path` across `tobe-architecture/agents/*.md` returns zero matches. Every TO-BE
  agent consumes already-extracted AS-IS markdown/JSON artifacts (`business-rules.md`,
  `architecture-blueprint.md`, `bounded-context-map.md`, `schema-inventory.md`, etc.) — never the
  raw `.pas`/`.dfm`/`.dpr` files.
- **No agent reads the generated TO-BE `outputs/tobe/source-code/` tree file-by-file.** The only
  three references to `outputs/tobe/source-code/` outside `coder-dotnet.md` itself are all
  narrow, targeted checks, not tree-wide reads:
  - `architecture-technical-tobe.md` — writes (not reads) `Directory.Packages.props` there.
  - `docs-tobe.md` — writes (not reads) per-module `README.md` files there.
  - `developer-guide-tobe.md` — checks only for the *existence* of a single file
    (`docker-compose.yml`) to decide whether to document a Docker Compose alternative; it does
    not read source code content.
- `coder-dotnet.md` itself (the primary candidate for a "read everything" pattern, being the
  codegen agent) never re-reads its own previously generated `.cs` files in bulk — it works BC by
  BC via `## BC Existence Pre-condition` (reads only `bounded-context-map.md`) and enforces
  `## Output Size Limits` per trigger (e.g. `SC` capped at 15 files / 2000 lines). Its Gate Pré-
  Entrega (Fase 4 of its own Ordem Obrigatória) shells out to
  `src/shared/checks/validate-dotnet-build.ps1`, which runs `dotnet build` /
  `dotnet list package --vulnerable` over the source tree — this is **compiler/CLI-level
  validation**, not the LLM ingesting the source tree into its context window, so it does not
  constitute the anti-pattern this check is screening for.
- `test-plan-tobe.md` and `developer-guide-tobe.md` — the two
  agents explicitly called out as likely candidates — were checked individually; **none of them
  reference `source-code/` or `repository_path` at all.** They are 100% artifact/report-based
  (wave-plan.md, migration-plan.md, tech-framework-document.md, ADRs, etc.).

**Conclusion**: the TO-BE architecture pipeline does **not** exhibit the redundant full-source-read
anti-pattern in either direction (re-reading AS-IS legacy source, or re-reading the generated
TO-BE source tree). All 20 `tobe-architecture` agents are artifact/report consumers by design.

**Update (`specs/016-tobe-artifact-only-guardrail`)**: as of this PBI, the absence documented
above is no longer just an observed static fact — it is an **enforced** invariant, via
`src/modules/ava-fabric-agents/shared/artifact-only-consumption-protocol.md`, referenced from
`orchestrator-tobe.md` and all 20 dispatched agent files. That guardrail is paired with a
mandatory `Read()`-before-dispatch protocol that closes the "agent improvises past a missing
input" gap — the practical mechanism by which the anti-pattern could have been triggered even
though no agent ever declared it in its own Input Contract.

---

## 4. Discrepancies Found

These are documentation/spec inconsistencies surfaced while building this map — recorded here,
not silently corrected, since resolving them requires a decision about which file is authoritative.

### 4.1 Ambiguous resolution of `{resolved_coder_agent}` for `.NET` (Fase 4.7)

`orchestrator-tobe.md`'s `CODER_AGENTS` map resolves `backend_framework: "dotnet"` to the short
id `"coder-dotnet"`. For the other four supported stacks, the resolved id matches a `tech-stack/agents/`
filename **exactly**: `coder-java-backend` → `coder-java-backend.md`, `coder-python-backend` →
`coder-python-backend.md`, `coder-go-backend` → `coder-go-backend.md`, `coder-node-backend` →
`coder-node-backend.md`. For `.NET`, however, `"coder-dotnet"` does **not** match the tech-stack
filename (`coder-dotnet-backend.md`, `name: ava-stack-dotnet-backend`) — it matches, verbatim,
`tobe-architecture/agents/coder-dotnet.md` (`name: ava-coder-dotnet`) instead. Both files are
plausible, self-contained "generate C# code for a bounded context" agents with materially
different behavior:

- `tobe-architecture/agents/coder-dotnet.md` — always executes; no `pipeline_mode` routing guard;
  own multi-phase NuGet/CPM resolution protocol and its own build/CVE gate
  (`validate-dotnet-build.ps1`) producing the `build_gate_result` the orchestrator expects.
- `tech-stack/agents/coder-dotnet-backend.md` — opens with a **Routing Guard** that reads
  `project-config.yaml → pipeline_mode`; if `pipeline_mode == "build-cycle"`, it refuses to run
  and redirects to a **third** family of agents (`@ava-build-cycle-dotnet-scaffold`,
  `@ava-build-cycle-efcore`, `@ava-build-cycle-cqrs`, `@ava-build-cycle-minimal-apis` — templates
  under `tech-stack/templates/build-cycle-*-agent.md`, part of `orchestrator-stack.md`'s own F3
  Build Cycle, not `orchestrator-tobe.md`).

This documentation does not resolve which of the two (or three) implementations actually fires
for `.NET` projects — it depends on filename-vs-slug resolution rules and on `pipeline_mode` that
live outside both files. **Flagged, not resolved.**

### 4.2 Dual ownership of the Fase 5.5 Build & Security Validation Gate

`orchestrator-tobe.md`'s "Agent Team Gerenciado" table (near the top of the file) lists
`Build Validator (ava-stack-build-validator) | 5.5` as one of **its own** managed agents. The
Fase 5.5 section body, however, states explicitly: *"A validação determinística de build
(compilação, lint, CVE scan) é delegada ao agente `ava-stack-build-validator` invocado pelo
`ava-stack-orchestrator` nos Steps 6a (backend) e 8a (frontend). O `orchestrator-tobe` recebe o
resultado consolidado via `build_gate_result` — NÃO executa validação diretamente."*
Cross-checking `tech-stack/agents/orchestrator-stack.md` confirms `ava-stack-build-validator` is
indeed invoked there, at Steps 6a/8 (backend/frontend), as part of the **F3 Build Cycle** — a
separate phase of the overall pipeline that runs only after the `Gate F2→F3` (Requestor
Inspection) in `orchestrator-tobe.md`. Yet the actual `build_gate_result` block that Fase 5.5
consolidates in `orchestrator-tobe.md` comes from the `{resolved_coder_agent}` invocations of
Fase 4.7 (each coder agent runs its own build/CVE gate and returns `build_gate_result` before
being marked `COMPLETED`) — not from `ava-stack-build-validator`, which hasn't run yet at that
point in the pipeline. The Agent Team table's listing of Build Validator as an F2-owned agent at
phase 5.5 is inconsistent with both the phase body text and with the actual data flow.
**Flagged, not resolved.**

### 4.3 Fases 7 and 8 have no dedicated `### Fase N —` sections

Every other phase (0-Pre through 7.8) has a full `### Fase N — {title}` section documenting its
gate, "Inputs obrigatórios" table, "Outputs obrigatórios" table and completion checklist. Fase 7
("Jornadas do usuário + BDD" / `user-journeys-tobe.md`) and Fase 8 ("Estimativa de infraestrutura
Azure" / `azure-infra-estimator-tobe.md`) are both named in the "Agent Team Gerenciado" table, in
the Progress Tracker item `fase-4` ("Execute Fase 4.7–8 — Code + Delivery"), and throughout the
timing/registry/Output Contract machinery (`ava-tobe-user-journeys`, `ava-tobe-azure-infra`) —
but neither has a phase body. Their gates and inputs had to be reconstructed in this map entirely
from the agent files themselves (§2, Fase 7 and Fase 8 entries above), which in turn surfaced two
further path-mismatch bugs local to those agent files (§4.8, §4.9).

### 4.4 `risk-mitigation-tobe.md` input path drops the `docs/` segment

`orchestrator-tobe.md`'s Fase 4.5 input table and `risk-mitigation-tobe.md`'s own "Input Sources"
table both list `projects/{project_name}/outputs/tobe/migration-plan.md` as an input. The actual
artifact, per both `migration-plan-tobe.md`'s Output Contract and the orchestrator's own Fase 4
output table, is written to `outputs/tobe/docs/migration-plan.md` (with the `docs/` segment).
As written, this input would never resolve.

**Status**: Fixed in specs/016-tobe-artifact-only-guardrail — path corrected to
`outputs/tobe/docs/migration-plan.md`.

### 4.5 `docs-tobe.md`'s TDD Publisher skill uses a whole family of pre-`docs/`-convention paths

The **TDD Publisher** sub-skill (trigger `TD`, never actually dispatched by the orchestrator —
see §1) lists 15 "Inputs obrigatórios" including `outputs/tobe/architecture-blueprint.md`,
`outputs/tobe/bounded-context-map.md`, `outputs/tobe/api-map.md`, `outputs/tobe/tech-framework-document.md`,
`outputs/tobe/wave-plan.md`, `outputs/tobe/migration-executive-summary.md`, `outputs/tobe/user-journeys.md`
— none with the `docs/` segment that every one of these artifacts actually uses in its producing
agent's Output Contract (`outputs/tobe/docs/architecture-blueprint.md`,
`outputs/tobe/docs/bounded-context-map.md`, etc.). This looks like a legacy list predating the
`outputs/tobe/docs/` convention adopted by the rest of the pipeline. Since `TD` is never
dispatched by `orchestrator-tobe.md`, this is latent rather than actively breaking anything today.

### 4.6 `test-plan-tobe.md` requires a file that is never produced: `architecture-technical.md`

`test-plan-tobe.md` marks `outputs/tobe/docs/architecture-technical.md` as a **✅ obrigatório**
input (used to calibrate Step 1d — technical/resiliency test adjustments) in no fewer than 8
places across the file. No agent in the pipeline produces a file with this name —
`architecture-technical-tobe.md`'s Output Contract only writes `tech-framework-document.md`. This
required input will always resolve to `[MISSING INPUT: architecture-technical.md]`, permanently
skipping Step 1d (contract tests / resiliency adjustments) even though the file is marked mandatory.

**Status**: Reclassified as non-blocking in specs/016-tobe-artifact-only-guardrail. The dead-path
reference itself is fixed in specs/017-tobe-path-corrections — all 15 occurrences in
`test-plan-tobe.md` now point to `outputs/tobe/docs/tech-framework-document.md` (the file
`architecture-technical-tobe.md` actually writes), which covers the same underlying content (TO-BE
technical stack — messaging, external APIs, microservices, resilience).

### 4.7 `outputs/asis/docs/screen-flow.md` is referenced but never produced

Both `orchestrator-tobe.md` (Fase 7.5 input table) and `designer-system-tobe.md` (Input Sources
#5) reference `projects/{project_name}/outputs/asis/docs/screen-flow.md` as a TO-BE input sourced
from the AS-IS pipeline. Per `docs/asis-diagnostic-io-map.md` §1a, the Screen Flow Mapper (`FT`)
skill actually produces `docs/screen-navigation-map.md` + `docs/screen-flow.mmd` — there is no
`screen-flow.md`. This input will always be absent.

**Status**: Reviewed in specs/016-tobe-artifact-only-guardrail — confirmed already non-blocking
(priority-5 enrichment row, outside the agent's `## Gate`). The wrong-extension reference itself
is fixed in specs/017-tobe-path-corrections — `designer-system-tobe.md` now points to
`outputs/asis/docs/screen-flow.mmd` (the real Mermaid artifact the `FT` skill produces), not the
`.md` variant that never existed.

### 4.8 `azure-infra-estimator-tobe.md`'s preferred Read Priority paths do not exist

The agent's Step 1 "Read Priority" list attempts, in order: (1) `outputs/tobe/sizing-report.md`,
(2) `outputs/tobe/architecture-design-tobe.md`, (3) `outputs/asis/` (enrichment), (4) inline
`infra-params` override. Path (1) is missing the `docs/` segment (`measure-size-tobe.md`
actually writes `outputs/tobe/docs/sizing-report.md`); path (2) does not correspond to any
producer at all (`architecture-design-tobe.md`'s primary blueprint output is
`outputs/tobe/docs/architecture-blueprint.md`). In practice, this agent's two "preferred" reads
both miss, so it always falls through to reading `outputs/asis/` directly or relying on the
inline override block.

**Status**: Path (1) fixed in specs/016-tobe-artifact-only-guardrail — `outputs/tobe/sizing-report.md`
→ `outputs/tobe/docs/sizing-report.md`. Path (2) fixed in specs/017-tobe-path-corrections —
`architecture-design-tobe.md` (dead reference, no producer) → `outputs/tobe/docs/architecture-blueprint.md`
(the real, closest-equivalent artifact, produced by `architecture-design-tobe.md`'s `CB` trigger),
corrected in all 6 occurrences across the Read Priority list, the estimation-profile decision
table, the READ ATTEMPT LOG format, and 2 BDD scenarios.

### 4.9 `user-journeys-tobe.md`'s own input list contains a dead path and an inconsistent BC map source

The agent's "Inputs Esperados" table lists `outputs/tobe/architecture-design.md`, which no agent
produces (closest match is `outputs/tobe/docs/architecture-blueprint.md`). It also lists
`outputs/asis/bounded-context-map.md` (the **AS-IS** bounded context map) as its BC source, while
every other Fase-7-and-later consumer (`designer-system-tobe.md`, `test-plan-tobe.md`,
`coder-dotnet.md`, etc.) reads the **TO-BE** map at `outputs/tobe/docs/bounded-context-map.md`.
Whether this is an intentional AS-IS/TO-BE dual-read or a copy-paste leftover from before the
TO-BE BC map existed is not documented.

**Status**: The dead-path half is fixed in specs/017-tobe-path-corrections —
`outputs/tobe/architecture-design.md` → `outputs/tobe/docs/architecture-blueprint.md`. The
AS-IS/TO-BE BC map source inconsistency (second half) is deliberately left as-is: the AS-IS file
genuinely exists (not a broken path), so it's a design ambiguity, not a path bug — deferred to a
future PBI.

### 4.10 `architecture-design-tobe.md`'s Output Contract overlaps with dedicated downstream agents

The agent's `## Output Contract` (Fase 1) lists `api_map: "outputs/tobe/docs/api-map.md"`,
`user_journeys: "outputs/tobe/docs/user-journeys.md"`, `designer_system: "outputs/tobe/docs/designer-system.md"`,
and `value_chain`/`value_chain_mapping`/`er_diagram_tobe` entries. Each of these has its own
dedicated, later-phase owner per the orchestrator's phase-by-phase tables: `api-map.md` is owned
by `docs-tobe.md` (Fase 5, `OA` trigger), `designer-system.md` by `designer-system-tobe.md` (Fase
7.5, at path `outputs/tobe/designer-system.md` — no `docs/` segment, yet another mismatch with
this list), and user journeys by `user-journeys-tobe.md` (Fase 7, at
`outputs/tobe/user-journeys/user-journeys-report.md`, not `outputs/tobe/docs/user-journeys.md`).
It is unclear whether `architecture-design-tobe.md` is expected to also (redundantly) write these
files during Fase 1, or whether this Output Contract is a stale superset from before the
dedicated agents existed. **Flagged, not resolved.**

### 4.11 `developer-guide-tobe.md`'s optional "Test Plan TO-BE" input path is wrong

Listed as `outputs/tobe/docs/test-plan-tobe.md`; the actual file, per `test-plan-tobe.md`'s
Output Contract and the orchestrator's Fase 6 table, is `outputs/tobe/qa/test-plan.md` (no `docs/`
segment, different filename). Non-blocking, so this only silently degrades Section 6 content.

**Status**: Fixed in specs/017-tobe-path-corrections — `developer-guide-tobe.md`'s Input Contract
row and its 2 prose references (Seção 7 template) now point to `outputs/tobe/qa/test-plan.md`.

### 4.12 ~~Fase 7.8 gate checks fewer files than `test-plan-consolidated-tobe.md` requires~~ (RESOLVIDO)

> **Status**: RESOLVIDO. A Fase 7.8 e o agente `test-plan-consolidated-tobe.md` foram eliminados
> na unificação com `test-plan-tobe.md` v5.0.0 (PBI 2525). As responsabilidades de consolidação
> e enriquecimento foram absorvidas pela Fase 6, cujo gate agora disciplina seus próprios inputs
> obrigatórios e enriquecedores.

### 4.13 `test-plan-tobe.md` hard-requires two AS-IS artifacts flagged as undocumented upstream

`test-plan-tobe.md` marks `outputs/asis/qa/test-strategy-asis.md` and
`outputs/asis/qa/test-execution-plan-asis.md` as **✅ obrigatório** inputs. Per
`docs/asis-diagnostic-io-map.md` §4.2 ("Undocumented `test-qa:QA` skill"), these exact two files
are required inputs of `golden-dataset-capture-asis.md` but are **not produced by any documented
agent** in the AS-IS pipeline — `test-qa-asis.md` (v3.0.0) documents no `QA` trigger or output
that would create them. This TO-BE gate inherits the same unresolved dependency: if the AS-IS
`test-qa:QA` skill is indeed unimplemented, Fase 6 of the TO-BE pipeline is permanently blocked
on inputs that can never exist, unless the runtime has an undocumented fallback.

### 4.14 `ava-developer-guide-tobe` missing from the final MICRO timing table

The Step 6 "Parte 3 — Tabela MICRO" template (used mid-execution) and the `STATUS_ONLY` table
both include a row for `ava-developer-guide-tobe | 5.1-Del`. The final "Execução Concluída" MICRO
table template near the end of the file (used for the actual closing output, both `FULL` and
`false` variants) omits this row entirely — it jumps from `ava-tobe-docs-rn` (5.2-Del) straight to
`ava-tobe-test-plan` (6-Del). Cosmetic — mirrors the AS-IS map's own §4.3
(`ava-asis-events-pubsub` missing from a summary table) in spirit; does not affect execution logic.

### 4.15 Output Contract `per_agent` YAML block is incomplete

The `## Output Contract` YAML (`per_agent` map, near the end of the file) lists timing entries
for only 18 of the 21 core `Agent IDs` enumerated one section earlier in "Agent Completion
Registry" — missing `ava-tobe-docs-rn`, `ava-developer-guide-tobe`, and `ava-tobe-spec` (plus,
implicitly, `{resolved_coder_agent}` and `build-security-gate`, which have no fixed agent id
to key on). Cosmetic — does not block execution.

### 4.16 `outputs/asis/db/triggers-map.md` referenced by 2 TO-BE agents but never produced by any AS-IS agent

`database-policy-tobe.md` (Input Contract, source 7) and `orchestrator-tobe.md`'s mirrored Fase
1.4 input table reference `outputs/asis/db/triggers-map.md` as a recommended (non-blocking)
enrichment source. `db-analyzer.md`'s `## Output Contract` declares exactly 7 outputs
(`db-type.json`, `schema-inventory.md`, `er-diagram.mmd`, `stored-procedures-map.md`,
`business-logic-in-db.md`, `db-quality-report.md`, `db-analysis-report.md`) — none named
`triggers-map.md`; trigger data only exists as an integer count field embedded inside
`db-type.json`, never as a standalone report. This input can never resolve, under any current or
past agent revision.

**Status**: Documented in specs/017-tobe-path-corrections as a permanent, structural gap (not a
"currently absent" one) in both referencing files — annotated in-place with an explanation rather
than redirected to a non-equivalent file (`db-type.json`/`business-logic-in-db.md` are supersets,
not 1:1 substitutes for a triggers report).

### 4.17 `outputs/asis/docs/test-plan.md` referenced by `orchestrator-tobe.md`'s Fase 7.8 gate uses the wrong directory segment

Both the Fase 7.8 "Gate de entrada" checklist and its Input Contract table reference
`outputs/asis/docs/test-plan.md` as an F1 bridge-fastqa artifact. `bridge-fastqa-asis.md`'s own
Output Contract writes to `outputs/asis/qa/test-plan.md` (confirmed also in `orchestrator-asis.md`,
4+ cross-references including a 5 KB size-threshold gate) — the `docs/` segment is wrong, no agent
ever writes there.

**Status**: Fixed in specs/017-tobe-path-corrections — both occurrences in `orchestrator-tobe.md`
corrected to `outputs/asis/qa/test-plan.md`.

---

## 5. Cross-Agent Consumption Summary

| Consuming agent                                              | Reads from                                                                                                                                            | Relationship                                                                                            |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `adr-tobe.md`                                              | `architecture-decision-matrix-tobe.md` (`decision_matrix_result`)                                                                                 | hard gate — Fase 0 cannot start without it                                                             |
| `architecture-design-tobe.md`                              | all 8 ADRs +`INDEX.md` (Fase 0)                                                                                                                     | hard gate — every Fase 1 trigger blocked if any ADR missing or`[INCOMPLETO]`                         |
| `database-policy-tobe.md`                                  | `ADR-002-database.md`                                                                                                                               | hard gate                                                                                               |
| `database-design-tobe.md`                                  | `ADR-002-database.md` + `outputs/tobe/db/sql-strategy.md` (Fase 1.4)                                                                              | 2 hard gates — both must pass                                                                          |
| `security-design-tobe.md`                                  | `ADR-003-security.md`                                                                                                                               | hard gate (Modo A only — Modo B bypasses this)                                                         |
| `architecture-technical-tobe.md`                           | all 8 ADRs                                                                                                                                            | hard gate — ADR always wins over`project-config.yaml` on conflict                                    |
| `migration-plan-tobe.md` (`backlog-tobe`)                | `tech-framework-document.md` (Fase 2) + `bounded-context-map.md` TO-BE (Fase 1)                                                                   | hard gate                                                                                               |
| `migration-plan-tobe.md` (`WM`)                          | `bounded-context-map.md` TO-BE + AS-IS artifacts                                                                                                    | hard gate; explicitly independent of`sizing-report.md`                                                |
| `measure-size-tobe.md`                                     | `backlog-tobe.md` (2.5) + `wave-model.json` (2.7)                                                                                                 | 2 hard Prerequisite Gates — agent aborts entirely if either missing                                    |
| `migration-plan-tobe.md` (main)                            | `wave-model.json` updated by `measure-size-tobe.md` (Fase 3)                                                                                      | SSoT — read, never regenerated                                                                         |
| `coexistence-strategy-tobe.md`                             | `wave-model.json`, `bounded-context-map.md`, `integration-matrix.md`, `architecture-blueprint.md` (all Fase 1–2.7)                           | 4 hard gates                                                                                            |
| `risk-mitigation-tobe.md`                                  | all 14 migration-plan Output Contract files + 4 coexistence files (18 total)                                                                          | hard gate before Fase 4.5                                                                               |
| `@ava-asis-gaps-risks` (residual)                          | `outputs/tobe/risk-mitigation-plan.md` (Fase 4.5)                                                                                                   | hard gate                                                                                               |
| `openapi-spec-tobe.md`                                     | `bounded-context-map.md` + `architecture-blueprint.md` (Fase 1)                                                                                   | hard gate; spec content must derive strictly from BC map                                                |
| `{resolved_coder_agent}`                                   | `tech-framework-document.md` + `patterns-applied.json` (Fase 2), per-BC OpenAPI spec (4.61)                                                       | 2 hard gates — codegen cannot start without either                                                     |
| `{resolved_coder_agent}`                                   | `docs-research-bundle.md` (`ava-stack-docs-researcher`, cross-module)                                                                             | optional/non-blocking — falls back to guardrails G1-G9                                                 |
| Fase 5.5 (gate)                                              | `build_gate_result` from every Fase 4.7 invocation                                                                                                  | consolidation, not a single-file read                                                                   |
| `docs-tobe.md` (`OA`)                                    | `bounded-context-map.md` (Fase 1) + `migration-plan.md` (Fase 4)                                                                                  | hard gate;`api-map.md` sub-step also reads `openapi-spec.yaml` (self) + `user-journeys.md` (soft) |
| `docs-tobe.md` (`RN`)                                    | `bounded-context-map.md` + `architecture-blueprint.md` (Fase 1)                                                                                   | hard gate                                                                                               |
| `developer-guide-tobe.md`                                  | `tech-framework-document.md` + 3 Fase-2 config artifacts                                                                                            | hard gate; 5 further optional enrichers                                                                 |
| `test-plan-tobe.md`                                        | `wave-plan.md`, `migration-plan.md`, `architecture-blueprint.md` (Fase 1–4), AS-IS BR/FR, AS-IS `test-strategy`/`test-execution-plan` ⚠️ | mixed hard/soft — see §4.13 for the undocumented-upstream risk                                        |
| `designer-system-tobe.md`                                  | `ADR-005-frontend.md`                                                                                                                               | hard gate; user-journeys + BC map + AS-IS screen-flow all soft                                          |
| `azure-infra-estimator-tobe.md`                            | `outputs/asis/` (enrichment, since both preferred TO-BE paths are broken — §4.8)                                                                  | degraded fan-in due to path bugs                                                                        |
| `ava-requestor-inspection` (Gate F2→F3)                   | 9 artifact groups spanning the entire F2 pipeline                                                                                                     | final consolidation before Build Cycle handoff                                                          |
