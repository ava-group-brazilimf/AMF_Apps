# F5 QA — Agent Input/Output Map

> **Driven by**: `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md` (v1.2.2)
> **Purpose**: canonical reference for every agent this orchestrator dispatches, what each one
> reads (inputs) and writes (outputs), and how their artifacts chain together.
> All paths are relative to `projects/{project_name}/outputs/` unless stated otherwise.
> Project config is always at `projects/{project_name}/context/project-config.yaml`.

---

## 1. Overview — Agents Dispatched

`qa-orchestrator-agent.md` handles **11 trigger codes** (`QS`, `GR`, `BM`, `TS`, `TC`, `FTM`,
`DBI`, `AS`, `ET`, `EC`, `PT`, `RS` — 12 counting `RS` separately), resolving to **9
QA-module implementing files** (two of them — `test-case-generator-agent.md` and
`script-generator-agent.md` — are dispatched twice each, under two different trigger
codes / modes with distinct output shapes) plus **2 cross-module dispatches** into
`devops-agents`.

| # | Agent ID (dispatch name) | Trigger(s) | Implementing file | Sequencing |
|---|---|---|---|---|
| 1 | `ava-qa-gaps-requirements` | `GR` (part of `QS`) | `agents/gaps-requirements-agent.md` | Sequential — first |
| 2 | `ava-qa-behavior-mapping` | `BM` (part of `QS`) | `agents/behavior-mapping-agent.md` | Sequential — after GR |
| 3 | `ava-qa-bridge-fastqa-tobe` (Momento 1 — scenario generation) | `TS` (part of `QS`/`QE`) | `agents/bridge-fastqa-tobe.md` | Sequential — before TC (absorbed the deprecated `ava-qa-scenario-generator`, v2.1.0) |
| 4 | `ava-qa-test-case-generator` (mode TC) | `TC` (part of `QS`) | `agents/test-case-generator-agent.md` | Parallel with TS |
| 5 | `ava-qa-test-case-generator` (mode FTM) | `FTM` | `agents/test-case-generator-agent.md` | Standalone — own pre-condition gate |
| 6 | `ava-qa-script-generator` (default mode) | `AS` (part of `QS`) | `agents/script-generator-agent.md` | Sequential — after TC |
| 7 | `ava-qa-script-generator` (`mode: regression`) | `RS` | `agents/script-generator-agent.md` | Sequential — after PT |
| 8 | `ava-qa-db-integrity-test` | `DBI` | `agents/db-integrity-test-agent.md` | Standalone — own pre-condition gate; **not** part of `QS` sequence |
| 9 | `ava-qa-defect-identifier` | (during automation execution, no dedicated trigger code) | `agents/defect-identifier-agent.md` | During execution |
| 10 | `ava-qa-exploratory` | `ET` (part of `QS`) | `agents/exploratory-agent.md` | Parallel with EC; verification+retry gate |
| 11 | `ava-qa-evidence-capture` | `EC` (part of `QS`) | `agents/evidence-capture-agent.md` | Parallel with ET |
| 12 | `ava-devops-cd` (→ `ava-devops-compare-version`) | `PT` (terminal-mandatory after almost every trigger) | `devops-agents/agents/cd-agent.md` (→ `devops-agents/agents/compare-version-agent.md`) | Sequential — after EC |
| 13 | `ava-devops-ci` (base mode, conditional) + (`mode: inject-regression-gate`) | `RS` (terminal-mandatory after PT) | `devops-agents/agents/ci-agent.md` | Sequential — after RS's script-generator step |

`QS` is the full quality-strategy trigger: **GR → BM → TS + TC (parallel) → AS → ET + EC
(parallel) → PT → RS**. Every other artifact-producing trigger (`GR`, `BM`, `TS`, `TC`,
`AS`, `ET`, `EC`) runs standalone but is followed automatically by the **Terminal Mandatory
Steps (PT → RS)** — see §Pre-condition Gates and the coverage table in the orchestrator
file. `FTM` and the isolated `PT`/`RS` triggers do **not** re-trigger PT→RS (they are
either the terminal step itself or explicitly excluded).

---

## 2. Per-Agent Input/Output Detail

### `ava-qa-gaps-requirements` — `agents/gaps-requirements-agent.md` (trigger `GR`)

- **Inputs (all mandatory — own Pre-condition Gate)**:
  `outputs/tobe/docs/architecture-blueprint.md`, `outputs/tobe/solution-structure.md`,
  `outputs/tobe/docs/bounded-context-map.md`, `outputs/tobe/docs/decisions/ADR-004-backend.md`,
  `outputs/tobe/docs/decisions/ADR-005-frontend.md`, `context/project-config.yaml`
  (`architecture_patterns`, `solution_layers`, `persistence`). Any missing artifact →
  blocking message citing F2 (TO-BE Architecture) incomplete.
- **Reference data (not project outputs)**: `src/shared/checklists/testability-gaps-checklist.md`,
  `src/shared/data/patterns/testability-antipatterns.yaml`
- **Dispatch params**: implicit (invoked first, no explicit param table in the file beyond the
  Input Contract above); receives `project_name` via `project-config.yaml` resolution.
- **Outputs**: `outputs/qa/gaps-requirements-report.md` (primary; also existing file that
  receives a new "Testability Gaps" section), `outputs/qa/gaps-requirements/` (artifacts dir),
  `outputs/tobe/docs/testability-gaps-report.md` (new, v-tagged "NOVO" in the Output Contract),
  plus in-band `testability_status` (`PASS|CONDITIONAL|BLOCKED`) and `testability_score` (0-100).
- **Behavior of note**: computes a combined `requirements_status` + `testability_status` →
  `overall_status`; if testability is `BLOCKED`, the orchestrator is instructed to halt the
  pipeline and demand an architecture fix before continuing to `ava-qa-behavior-mapping`.

### `ava-qa-behavior-mapping` — `agents/behavior-mapping-agent.md` (v1.0.0, trigger `BM`)

- **Inputs (hard "Dependency Tree Validation" — ✅ = blocking)**:
  `context/project-config.yaml` ✅, `outputs/asis/bounded-context-map.md` ✅,
  `outputs/asis/architecture-blueprint.md` ✅, `outputs/asis/pattern-classifications.json` ✅,
  `outputs/asis/docs/functional-requirements.md` ✅, `outputs/asis/docs/business-rules.md` ✅;
  plus 10 optional (⬜) AS-IS artifacts (`vcl-lifecycle-map.md`, `data-access-profile.md`,
  `schema-inventory.md`, `stored-procedures-map.md`, `business-logic-in-db.md`,
  `screen-navigation-map.md`, `screen-rules.md`, `value-chain.md`, `inventory-report.md`,
  `gaps-risks-report.md`, `gap-list-report.md`).
- **Full-source-read note**: the agent's STEP 2 (`SOURCE-SCAN`) does `Glob` for individual
  `.pas` files named in `bounded-context-map.md`'s `Forms:`/`Units:` lists — scoped to
  named forms/units, not a full-tree walk. See §3.
- **Dispatch params**: `project_name`, `language`, `legacy_technology` (from project-config).
- **Outputs**: `outputs/qa/behavior-mapping/behavior-catalog.json` (atomic `Write`-only JSON
  array, schema `BH-NNNN` entries), `outputs/qa/behavior-mapping-report.md`,
  `outputs/qa/behavior-mapping/` (artifacts dir).
- **Downstream criticality**: `behavior-catalog.json` is the **hard-blocking** input for the
  `FTM` trigger's Pre-condition Gate Step 4 (see §Mandatory Inputs/Gates below) and is also
  consumed by `ava-qa-bridge-fastqa-tobe` (Momento 1 — scenario generation).

### `ava-qa-bridge-fastqa-tobe` (Momento 1) — `agents/bridge-fastqa-tobe.md` (v2.0.0, trigger `TS`)

> ⚠️ **2026-08-05**: absorbed the deprecated `ava-qa-scenario-generator` (v2.1.0, see
> `agents/scenario-generator-agent.md`, kept only as a historical schema reference). This
> agent now runs in two moments: **Momento 1** (this section, trigger `TS`, generates BDD
> scenarios for **all** Test Case groups) and **Momento 2** (trigger `FQ`, API-only exploratory
> testing + Playwright/TS automation, reusing the `.feature` produced here).

- **Inputs**: `context/project-config.yaml` ✅; in `full-scenario-generation` mode reads
  `outputs/tobe/qa/test-cases.md` (all groups) + `outputs/tobe/docs/openapi/*.yaml`; in
  `wave-delegation` mode receives the delegation contract directly from `ava-test-plan-tobe`
  (`br_fr_list`, `architecture_context`, `user_journeys`, `acceptance_criteria`, `baseline_plan`,
  `output_dir`) and skips the standalone gate entirely.
- **Wave-aware mode**: when invoked by `ava-test-plan-tobe` (not by the QA orchestrator)
  with a `delegation` payload (`wave`, `br_fr_list`, `output_dir: features/wave-{N}/`),
  writes to a wave subdirectory instead of the root `features/` dir and must tag ≥1 `@smoke`
  happy-path scenario per bounded context.
- **Dispatch params**: `project_name`, `language`, `invocation_mode` (`full-scenario-generation`
  | `wave-delegation` | `exploration-automation`).
- **Outputs (legacy Output Contract preserved)**: `outputs/tobe/tests/features/*.feature` (or
  `wave-{N}/`) Gherkin, min. 15 scenarios/run in `full-scenario-generation` mode,
  `outputs/qa/scenario-generator-report.md`, `outputs/qa/scenario-generator/scenario-register.json`
  (fixed-contract JSON array — same schema as the deprecated agent).

### `ava-qa-test-case-generator` — `agents/test-case-generator-agent.md` (v1.0.0) — **dual trigger**

This single implementing file handles two distinct trigger codes with different output
shapes.

#### Mode TC — trigger `TC` (part of `QS`)

- **Inputs**: `context/project-config.yaml`; `outputs/tobe/user-journeys.md`,
  `outputs/qa/scenario-generator/scenario-register.json`, `outputs/tobe/acceptance-criteria.md`
  (all marked required "for TC" in the Input Contract table, no explicit gate logic beyond that).
- **Outputs**: `outputs/qa/test-case-generator-report.md` (formal test cases: input, expected
  output, steps), `outputs/qa/test-case-generator/`.

#### Mode FTM — trigger `FTM` (standalone, own Pre-condition Gate at the orchestrator level)

- **Inputs**: `outputs/tobe/docs/spec.md` ✅ (fallback order: `functional-spec.md` →
  `spec-kit/*.md` → last-resort `outputs/asis/docs/functional-requirements.md`);
  `outputs/qa/behavior-mapping/behavior-catalog.json` ✅ (fallback: `behavior-mapping-report.md`
  by textual heuristic; if **both** absent → hard `⛔ FTM BLOCKED` at the agent level, mirroring
  the orchestrator's own FTM gate Step 4); `outputs/asis/docs/functional-requirements.md`
  (enrichment, non-blocking); `outputs/tobe/acceptance-criteria.md` (fallback: derive from each
  RF's Business Rules).
- **Outputs**: `outputs/qa/functional-test-matrix.md` — a full RF → acceptance-scenario
  traceability matrix with priority (P0–P3), test type (`Acceptance|Integration|Unit|E2E|Smoke`),
  and an explicit `AS-IS Behavior Ref` column (`BH-ID` or `[NOT_MAPPED]`) sourced from
  `behavior-catalog.json`'s `fr_to_bh_index`.
- **Validation gate before write**: every P0 RF must have ≥1 `Smoke` scenario; every
  P0/P1 RF must have ≥1 sad-path scenario; a "Gaps de Cobertura" section is always emitted
  (even if empty).

### `ava-qa-script-generator` — `agents/script-generator-agent.md` (v1.2.0) — **dual mode**

> ⚠️ Frontmatter has two conflicting `version`/`date` pairs — see §4 Discrepancy.

#### Default mode — trigger `AS` (part of `QS`, after TC)

- **Inputs**: `outputs/qa/test-case-generator-report.md` (required),
  `outputs/tobe/source-code/src/**` (required — **unbounded glob over the entire generated
  backend source tree**, see §3), `outputs/tobe/source-code/{project_name}.sln` (required);
  optional: `outputs/qa/behavior-mapping-report.md`, `outputs/qa/script-generator-report.md`.
  Step 7 (Parity Suite Plan) additionally has its own dependency gate on
  `outputs/tobe/user-journeys.md` and/or `outputs/qa/behavior-mapping-report.md`.
- **Outputs**: `outputs/qa/script-generator-report.md`; QA docs under `outputs/qa/scripts/`
  (unit/integration overviews, run instructions); source-code test projects under
  `outputs/tobe/source-code/tests/Unit/**`, `tests/Integration/**`, `tests/Parity/**`
  (`.csproj` + `.cs` files, xUnit/Moq/FluentAssertions); `.sln` update;
  `outputs/qa/parity-suite-plan.md`; `outputs/qa/parity-evidence/*.json`.
- **Quality gates**: `dotnet build`/`dotnet test` exit 0, domain coverage ≥80%, 100% TC-ID
  traceability, ≥6 parity journeys covered, no production-code modification (interface-gap
  exception allowed).

#### `mode: regression` — trigger `RS` (invoked by the orchestrator after PT)

- **Inputs**: `mode: regression`, `source: outputs/tobe/parity-test-report.md`,
  `trait_tag: Regression`, `output_dir: outputs/qa/regression-suite/`,
  `filter: status == EQUIVALENT` — i.e. it re-reads the **PT** agent's own output
  (`parity-test-report.md`), not raw source code.
- **Outputs**: `outputs/qa/regression-suite/Regression.Tests/Regression.Tests.csproj`,
  `outputs/qa/regression-suite/Regression.Tests/{BoundedContext}/*.cs` (one file per BC,
  `[Trait("Type","Regression")]` + `[Trait("BoundedContext", ...)]` per `[Fact]`),
  `outputs/qa/regression-suite/regression-suite-report.md`. If zero `EQUIVALENT` scenarios
  are found → registers a warning and produces no test files.

### `ava-qa-db-integrity-test` — `agents/db-integrity-test-agent.md` (v1.1.0, trigger `DBI`)

- **Inputs**: `context/project-config.yaml` ✅; `outputs/asis/db/schema-inventory.md` ✅
  (F1); `outputs/tobe/source-code/src/**/Migrations/*.cs` ✅ (F3 — **scoped glob**, only the
  `Migrations/` subfolder of the generated tree, not the full source, see §3);
  `outputs/tobe/source-code/src/**/*Context.cs` ✅ (also scoped — filename-pattern glob, not
  a full-tree read); `outputs/tobe/source-code/*.sln` ✅; optional:
  `outputs/asis/db/stored-procedures-map.md` ⚠️ (enables the `StoredProcedures/` test
  category), `outputs/asis/db/business-logic-in-db.md` ⚠️ (enrichment only).
- **Own pre-condition failure message** (agent-level, independent of the orchestrator's DBI
  gate): "schema-inventory.md ou qualquer arquivo de migration não encontrado — verifique se
  F1 e F3 foram executados."
- **Outputs**: `outputs/qa/db-integrity/db-integrity-test-report.md`; source-code test
  project under `outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/`
  (`.csproj`, `GlobalUsings.cs`, `DatabaseIntegrityTestBase.cs`, and per-category `.cs` files
  under `Migrations/`, `Constraints/`, `Indexes/`, `StoredProcedures/` — the last one only if
  `SP_CATALOG` is non-empty); `.sln` update.
- Only reachable via the explicit `DBI` trigger — **not** part of the `QS` sequence (confirmed
  by both the orchestrator's Routing section and its own trigger table).

### `ava-qa-defect-identifier` — `agents/defect-identifier-agent.md` (stub-level file)

- **Inputs**: none declared — the file has no `## Input Contract` section at all; it is the
  thinnest agent in the QA team (Role & Persona + generic Core Responsibilities boilerplate
  only, no Execution Algorithm).
- **Outputs**: `outputs/qa/defect-identifier-report.md`, `outputs/qa/defect-identifier/`
  (per its Output Contract — the only concrete artifact declared in the file).
- **Trigger**: no dedicated trigger code in the orchestrator's Triggers/Menu table; the
  Agent Team QA table lists it as running "Durante execução" (during automation execution),
  implying it is invoked as a byproduct of `AS`/`ET`/`EC` rather than addressably on its own.
  See §4 Discrepancy.

### `ava-qa-exploratory` — `agents/exploratory-agent.md` (v2.0.0, trigger `ET`)

- **Inputs**: `context/project-config.yaml` ✅; `outputs/asis/master-report.md` ✅
  (hard pre-condition gate — blocks if absent, requiring F1 completion);
  `outputs/asis/docs/functional-requirements.md` ✅ (non-blocking WARN if absent — baseline
  becomes partial); 10 further optional (⬜) AS-IS artifacts (`business-rules.md`,
  `architecture-blueprint.md`, `pattern-classifications.json`, `bounded-context-map.md`,
  `screen-navigation-map.md`, `events-pubsub-inventory.md`, `gap-list-report.md`, `shared-context.md`).
- **Full-source-read note**: the agent is explicitly named "Static Analysis Mode" (STEP 3
  header) — it analyzes existing AS-IS **documentation artifacts**, not the legacy repository
  source tree directly; no `Glob`/`Grep` over `repository_path` appears anywhere in the file.
  See §3.
- **Orchestrator-enforced output contract + verification/retry gate** (unique to this agent
  among all QA agents): the `QS` Routing section passes an explicit instruction requiring
  exactly 4 files — `findings-catalog.json`, `session-log.md`, `tobe-preservation-list.md`,
  `exploratory-report.md` — and forbids any "guide"/"template" file. After the agent
  completes, the orchestrator's **"6b. ET VERIFICATION GATE"** checks for
  `outputs/qa/exploratory/findings-catalog.json`; if missing, it re-invokes the agent **once**
  with a `⛔ RETRY` instruction pointing at STEP 4/5 of the agent's own spec; if still missing
  after retry, it logs `❌ ET FAILED` and **continues without blocking the pipeline**. The
  agent file itself mirrors this with its own STEP 6 `SELF-VALIDATION` (re-`Read`s all 4
  files before signaling completion).
- **Outputs**: `outputs/qa/exploratory-report.md`, `outputs/qa/exploratory/session-log.md`,
  `outputs/qa/exploratory/findings-catalog.json` (EXP-NNN entries; `[]` if zero findings),
  `outputs/qa/exploratory/tobe-preservation-list.md` (MUST_PRESERVE/SHOULD_PRESERVE subset).

### `ava-qa-evidence-capture` — `agents/evidence-capture-agent.md` (v2.1.0, trigger `EC`)

> ⚠️ Frontmatter uses `data: 2026-06-01` instead of `date:` — likely a typo, see §4.

- **Inputs**: `context/project-config.yaml` ✅; `outputs/qa/scenario-generator-report.md` ✅,
  `outputs/qa/scenario-generator/scenario-register.json` ✅ (both produced by
  `ava-qa-bridge-fastqa-tobe`, Momento 1),
  `outputs/qa/test-case-generator-report.md` ✅; optional: `outputs/tobe/source-code/tests/**/*.cs` ⬜,
  `outputs/qa/evidence-capture/xunit-results/` ⬜, `outputs/qa/defect-identifier-report.md` ⬜,
  `outputs/qa/behavior-mapping-report.md` ⬜, `outputs/qa/evidence-capture/diffs/` ⬜,
  `outputs/qa/exploratory-report.md` ⬜, `outputs/qa/qa-master-report.md` ⬜,
  `outputs/tobe/source-code/tests/**/*.csproj` ⬜ (used to actually *run* `dotnet test`, not
  just to read source).
- **Pre-Condition Gate (hard, #1)**: requires `outputs/qa/qa-master-report.md` **OR**
  simultaneous presence of `scenario-generator-report.md` + `test-case-generator-report.md`;
  else `⛔ UPSTREAM_NOT_COMPLETE` and abort.
- **Full-source-read note**: "exploration"/collection here is scoped — it globs `tests/**/*.cs`
  and `tests/**/*.csproj` to find and *execute* test projects (xUnit/Jest/pytest runners), and
  diffs `outputs/tobe/`/`outputs/asis/` **module output artifacts** for parity comparison, not
  the legacy or generated application's full raw source. See §3.
- **Outputs**: `outputs/qa/evidence-capture-report.md`, `outputs/qa/parity-dashboard.md`,
  `outputs/qa/evidence-capture/compliance-package/` (4-part bundle: screenshots index, logs,
  diffs, dashboard), `outputs/qa/evidence-capture/diffs/`, `outputs/qa/evidence-capture/logs/`,
  `outputs/qa/evidence-capture/screenshots/index.md`,
  `outputs/qa/evidence-capture-package-index.md` (SHA-256 checksums). Applies mandatory PII
  redaction (CPF/email/phone/secret patterns) before persisting any log/output.
- **Downstream gate role**: `outputs/qa/evidence-capture-report.md` is the file the
  orchestrator's `PT` Routing step checks for existence of before invoking `ava-devops-cd`
  (see §Mandatory Inputs/Gates).

### `ava-devops-cd` → `ava-devops-compare-version` — `devops-agents/agents/cd-agent.md` / `compare-version-agent.md` (trigger `PT`)

- **Interface passed in by QA orchestrator**: `project_name`, `invoke_context: qa-orchestrator`
  ("sem deploy ativo — modo standalone").
- **What `ava-devops-cd` does with it**: its own "Post-Deploy Handoff — Parity Test" section
  recognizes `invoke_context = "qa-orchestrator"` (Condição B, standalone) as equivalent to
  its normal Condição A (pipeline smoke tests PASSED) and immediately invokes
  `ava-devops-compare-version`, passing `project_name`, `wave_id`, `invoke_context`, and the
  golden-dataset/BDD-fallback payload source.
- **`ava-devops-compare-version`'s own gate check artifact**: `project-config.yaml`'s
  `wave_approval.parity_endpoints`; if unconfigured, the report is generated with
  `status: NOT_EXECUTED` rather than blocking.
- **What comes back**: `projects/{project_name}/outputs/tobe/parity-test-report.md`
  (per-BC parity score — mandatory section per BC) and
  `projects/{project_name}/outputs/tobe/wave-approval.md` (Go/No-Go verdict + SME/QA-Lead
  sign-off, mandatory for Business Rule Validation).
- **QA orchestrator's own pre-condition for invoking PT at all**: `outputs/qa/evidence-capture-report.md`
  must exist (EC completed) — else warns and stops (manual trigger) or SKIPPED (terminal-mandatory
  context).
- Internals of the comparison algorithm (golden-dataset dual-fan-out, field tolerances, BRV
  category overrides) are intentionally **not** deep-dived here — out of scope per this
  document's brief.

### `ava-devops-ci` — `devops-agents/agents/ci-agent.md` (trigger `RS`, two sub-invocations)

- **Interface passed in (base-mode, conditional)**: no `mode` param — invoked only if
  **neither** `outputs/tobe/source-code/.github/workflows/ci.yml` **nor**
  `outputs/tobe/source-code/azure-pipelines.yml` exists yet; the QA orchestrator records
  `CI_BASE_CREATED: true/false` in `shared-context.md` accordingly.
- **Interface passed in (regression-gate mode)**: `mode: inject-regression-gate`,
  `test_filter: 'Trait("Type", "Regression")'`, `on_triggers: [pull_request, push_to_main, pre_deploy]`,
  `blocking: true`, `report_artifact: regression-results`.
- **What comes back**: injects/updates a `regression-gate` job (GitHub Actions) or
  `RegressionGate` stage (Azure DevOps) that runs
  `dotnet test outputs/qa/regression-suite/Regression.Tests/Regression.Tests.csproj --filter 'Trait("Type","Regression")'`,
  gated with `needs: build-and-test` / `dependsOn: BuildAndTest` so failures block
  deploy/merge. Output paths match the orchestrator's own Output Contract
  (`.../tobe/source-code/.github/workflows/ci.yml`, `.../azure-pipelines.yml`) exactly.
- **Note**: `ci-agent.md`'s own `inject-regression-gate` routing (its step 4, line ~210)
  already self-handles the "no CI file exists yet" case by running a full base-mode
  generation internally before injecting the gate — see §4 Discrepancy for the resulting
  overlap with the orchestrator's own Step 4 pre-check.
- Internals of the CI agent's multi-stack build/coverage/SAST logic are intentionally not
  deep-dived — out of scope per this document's brief.

---

## 3. Full Source Re-Read Flags

The AS-IS pipeline's main code-analysis agent (`solution-delphi.md`) was recently
re-architected to consume pre-extracted AST JSON artifacts instead of walking the full
legacy repository tree (see `docs/asis-diagnostic-io-map.md` §2). The table below assesses
every QA agent's input scope against the same standard.

| Agent | Scope found | Verdict | Evidence |
|---|---|---|---|
| `ava-qa-db-integrity-test` | `outputs/tobe/source-code/src/**/Migrations/*.cs` and `src/**/*Context.cs` | ✅ **Scoped** — globs target only the `Migrations/` subfolder and files matching `*Context.cs`, not the full generated source tree | Input Contract: `"projects/{project_name}/outputs/tobe/source-code/src/**/Migrations/*.cs"` / `"...src/**/*Context.cs"` |
| `ava-qa-script-generator` (default `AS` mode) | `outputs/tobe/source-code/src/**` (required) | 🚩 **FLAG — unbounded full-source read** | Input Contract: `required: ["...outputs/tobe/source-code/src/**", "...{project_name}.sln"]`; Step 1 explicitly instructs: *"Ler todos os domain aggregates em `outputs/tobe/source-code/src/Modules/**/Domain/*.cs` e `src/SharedKernel/**/*.cs`"* — a glob over the entire generated backend tree, not an OpenAPI spec, API contract, or narrower manifest |
| `ava-qa-script-generator` (`mode: regression`, `RS` trigger) | `outputs/tobe/parity-test-report.md` only | ✅ **Scoped** — reads the PT agent's report, not source code | Routing — mode: regression, "Step R1 — Ler o parity-test-report.md" |
| `ava-qa-exploratory` | AS-IS documentation/report artifacts (`master-report.md`, `functional-requirements.md`, `business-rules.md`, `architecture-blueprint.md`, etc.) | ✅ **Scoped** — explicitly a "Static Analysis Mode" over AS-IS artifacts; no `repository_path` glob/grep found in the file | STEP 3 header: *"EXECUTE-EXPLORATION (Static Analysis Mode)"*; Input Contract lists only `outputs/asis/*` artifact paths, never `repository_path` |
| `ava-qa-evidence-capture` | `outputs/tobe/source-code/tests/**/*.cs`, `tests/**/*.csproj` (to execute test runners), plus `outputs/tobe/`/`outputs/asis/` artifact diffing | ✅ **Scoped** — targets only the `tests/` subtree (to run `dotnet test`/Jest/pytest) and compares already-produced module outputs, not raw application source | Input Contract: `"...tests/**/*.cs"` ⬜, `"...tests/**/*.csproj"` ⬜; STEP 2a: *"Listar todos os artefatos em `outputs/tobe/` e `outputs/asis/` por módulo"* (artifact-level, not source-level) |
| `ava-qa-defect-identifier` | None declared | N/A — no `## Input Contract` section exists in the file at all; cannot be scored either way | File contains only Role & Persona + generic boilerplate, no Execution Algorithm |
| `ava-qa-behavior-mapping` | `Glob` for named `.pas` files listed in `bounded-context-map.md`'s `Forms:`/`Units:` | ✅ **Scoped** — targeted per-file glob driven by an upstream artifact list, not a blanket repository walk | STEP 2a/2b: *"Localizar o arquivo `.pas` correspondente usando `Glob`... Para cada form listado no BC (`Forms: [...]`)"* |

**Summary**: 1 of 9 QA-module agents (`ava-qa-script-generator`, default `AS` mode) performs
an unbounded full-source-tree read (`outputs/tobe/source-code/src/**`) to derive unit-test
targets, rather than consuming a narrower manifest (e.g. an OpenAPI spec, an API-map
artifact, or a domain-model summary already produced upstream). This is the QA-phase
analogue of the AS-IS pipeline's pre-optimization pattern and is a candidate for the same
kind of scoped-artifact refactor.

---

## 4. Discrepancies Found

These are documentation/spec inconsistencies surfaced while building this map — recorded
here, not silently corrected, since resolving them requires a decision about which file is
authoritative.

### 4.1 `ava-qa-defect-identifier` has no addressable trigger or Input Contract

The orchestrator's "Agent Team QA" table lists `ava-qa-defect-identifier` as running
"Durante execução" (during automation execution), but no trigger code in the Triggers/Menu
table (`QS`, `GR`, `BM`, `TS`, `TC`, `FTM`, `DBI`, `AS`, `ET`, `EC`, `PT`, `RS`) maps to it
explicitly, and no Routing section ever calls `ava-qa-defect-identifier` by name. The agent
file itself has no `## Input Contract` section — it is the only QA agent in the team with no
declared inputs at all. This mirrors the `asis-diagnostic-io-map.md` §4.2 pattern (an agent
referenced as part of the team but with no traceable dispatch path) — here the gap is the
inverse: the *file* exists and is thin, but the *orchestrator* never explicitly invokes it.

### 4.2 `script-generator-agent.md` has duplicate/conflicting frontmatter `version`/`date`

The YAML frontmatter block declares `version: 1.2.0` / `date: 2026-06-11` (lines 3–4) and
then, before the closing `---`, a second `version: 1.0.0` / `date: 2026-06-03` (lines 12–13).
The orchestrator's own Agent Team QA table and the agent's internal observability
self-report block (`--version 1.2.0`) both treat `1.2.0` as canonical, so `1.0.0`/`2026-06-03`
appears to be stale leftover metadata never removed when the file was bumped to `1.2.0`.

### 4.3 `evidence-capture-agent.md` frontmatter uses `data:` instead of `date:`

Line 4 of the frontmatter reads `data: 2026-06-01` — every sibling agent file in
`qa-agents/agents/` uses the key `date:`. Cosmetic only (does not affect dispatch), but
means any tooling that parses frontmatter `date` for this file will find it absent.

### 4.4 Redundant CI-base-generation logic between orchestrator Step 4 and `ci-agent.md`'s own fallback

The QA orchestrator's `RS` Routing (Step 4) explicitly checks whether `ci.yml` /
`azure-pipelines.yml` exists and, if not, invokes `ava-devops-ci` in base mode *before*
invoking it again in `mode: inject-regression-gate`, recording `CI_BASE_CREATED` either way.
However, `ci-agent.md`'s own `inject-regression-gate` routing (its internal step 4) already
states: *"Se nenhum arquivo CI existir → executar geração completa do pipeline CI (modo
padrão, todos os quality gates)... depois prosseguir com a injeção do bloco regression-gate
normalmente"* — i.e. the callee already self-handles the missing-CI case. The orchestrator's
extra pre-check is not incorrect, but it duplicates logic already implemented inside the
callee; a single `mode: inject-regression-gate` call would suffice, and the orchestrator's
two-call sequence risks a double base-pipeline-generation attempt if both sides' fallback
logic fire independently in different runtimes.

### 4.5 `FTM`'s dependency on `behavior-catalog.json` — gate exists on both sides, but is well-formed (not a gap)

Unlike `asis-diagnostic-io-map.md` §4.2 (an undocumented `test-qa:QA` skill referenced by two
files but produced by neither), the `FTM` → `behavior-catalog.json` dependency checked here
**is** fully traceable: the orchestrator's own Pre-condition Gate (FTM) Step 4 checks for
`outputs/qa/behavior-mapping/behavior-catalog.json` and blocks with an explicit instruction
to run trigger `BM` first; `ava-qa-behavior-mapping`'s Output Contract confirms it is the sole
producer at that exact path; and `test-case-generator-agent.md`'s own FTM-mode STEP 1 repeats
the same check independently (with its own fallback to `behavior-mapping-report.md` and its
own blocking message). No gap found — flagged here only because the task brief asked this
dependency be checked explicitly against the AS-IS doc's precedent.

### 4.6 `db-integrity-test-agent.md` Input Contract table omits its own STEP 1 fallback sources

The Input Contract table marks `EF Core Migrations` and `DbContext` files as strictly
required (✅), but STEP 2's `PARSE-SCHEMA-CATALOG` describes fallback extraction paths for
PK/FK/UK data from `IEntityTypeConfiguration<T>` classes (`HasKey`, `HasOne/HasMany`,
`HasIndex(...).IsUnique()`) when the primary `migrationBuilder.*` calls aren't found in the
migration files. These fallback source files are never listed in the Input Contract table
itself — a minor documentation gap, not a blocking issue since they're additive to already-
scoped migration/context files.

---

## 5. Cross-Agent Consumption Summary

| Consuming agent | Reads from | Relationship |
|---|---|---|
| `ava-qa-behavior-mapping` | 6 mandatory AS-IS artifacts (bounded-context-map, architecture-blueprint, pattern-classifications, functional-requirements, business-rules) + 10 optional | hard-blocking dependency gate |
| `ava-qa-bridge-fastqa-tobe` (Momento 1) | `behavior-mapping-report.md` (own-agent fallback to `user-journeys.md` + `acceptance-criteria.md`) — absorbed the deprecated `ava-qa-scenario-generator` | blocking-with-fallback |
| `ava-qa-test-case-generator` (TC mode) | `scenario-register.json` (ava-qa-bridge-fastqa-tobe, Momento 1) + `user-journeys.md` + `acceptance-criteria.md` | direct sibling read |
| `ava-qa-test-case-generator` (FTM mode) | `spec.md` (TO-BE, F2) + `behavior-catalog.json` (behavior-mapping, hard-blocking) + `functional-requirements.md` (AS-IS, enrichment) | dual-gated — TO-BE spec AND AS-IS behavior catalog both required |
| `ava-qa-script-generator` (AS mode) | `test-case-generator-report.md` + full `outputs/tobe/source-code/src/**` (🚩 unscoped) + `user-journeys.md`/`behavior-mapping-report.md` (Step 7 gate) | mixed — artifact read + unscoped source read |
| `ava-qa-script-generator` (RS mode) | `parity-test-report.md` (PT agent's own output) filtered by `status == EQUIVALENT` | indirect — via PT's output, not raw source |
| `ava-qa-db-integrity-test` | `schema-inventory.md` (AS-IS/F1) + EF Core migrations (TO-BE/F3, scoped glob) | dual-phase hard-blocking gate (F1 **and** F3) |
| `ava-qa-exploratory` | `master-report.md` (AS-IS/F1, hard-blocking) + `functional-requirements.md` (soft) + 8 further optional AS-IS artifacts | hard-blocking on F1 completion only |
| `ava-qa-evidence-capture` | `qa-master-report.md` **OR** (`scenario-generator-report.md` + `test-case-generator-report.md`) | hard-blocking "upstream QA complete" gate |
| `ava-devops-cd` (PT) | `evidence-capture-report.md` (orchestrator-level gate) + `wave-plan.md` + `test-plan.md`/`functional-test-matrix.md` (post-deploy validation via test artifacts, smoke suites deprecated in v4.0.0) | cross-module, orchestrator-checked before dispatch |
| `ava-devops-compare-version` | `golden-dataset.json` (primary) / BDD scenarios (fallback) + `project-config.yaml` `wave_approval.*` | invoked internally by `ava-devops-cd`, not directly by QA orchestrator |
| `ava-devops-ci` (RS) | `parity-test-report.md`-derived `regression-suite/Regression.Tests.csproj` (via script-generator RS mode) + existing `ci.yml`/`azure-pipelines.yml` | cross-module, two-call sequence (base + inject-regression-gate) |
| Terminal Mandatory Steps (PT→RS) | `evidence-capture-report.md` (gates PT) → `parity-test-report.md` (gates RS) | global invariant appended to every artifact-producing trigger except `FTM`/`PT`/`RS` themselves |

---

## Appendix — Mandatory Inputs and Pre-condition Gates (verbatim logic)

### Mandatory Inputs (applies to `QS` and all sub-agents)

| File | Path | Required by | Validation rule |
|---|---|---|---|
| `bounded-context-map.md` | `outputs/tobe/docs/bounded-context-map.md` | `QS` and all sub-agents | Must exist **and** contain ≥1 bounded context |

### Pre-condition Gate (QS)

Runs before *any* `QS` action.
1. **Existence**: `Read` `outputs/tobe/docs/bounded-context-map.md` — if missing, block with reason `"não foi encontrado"`.
2. **Content — ≥1 Bounded Context**: satisfied by *any* of: ≥1 `## ` heading (excluding the doc title), ≥1 non-separator/non-header table row containing `|`, or ≥1 occurrence of pattern `BC-\d+`. If none match, block with reason `"existe mas não contém nenhum bounded context definido"`.
3. **PASS**: emit `✅ [PRE-CONDITION GATE: PASS]` and proceed.
4. **Blocking message**: fixed template instructing to run trigger `SD` on `ava-tobe-orchestrator` (i.e. complete F2) and re-run `QS`.

### Pre-condition Gate (FTM)

Runs before *any* `FTM` action.
1. **spec.md (TO-BE) existence** — checks in fallback order: `outputs/tobe/docs/spec.md` → `outputs/tobe/docs/spec-kit/` (dir with `.md` files) → `outputs/tobe/docs/functional-spec.md`. None found → block, reason `"spec.md (TO-BE) não foi encontrado (F2 incompleta)"`.
2. **≥1 RF in spec.md** — satisfied by ≥1 `## FR-`/`### FR-` heading or ≥1 occurrence of `FR-\d+`. Fails → block, reason `"spec.md existe mas não contém nenhum RF definido"`.
3. **functional-requirements.md (AS-IS)** — soft check: if missing, log `⚠️ WARN` and continue (non-blocking; traceability becomes partial).
4. **behavior-catalog.json (AS-IS) — ⛔ BLOCKING**: `Read` `outputs/qa/behavior-mapping/behavior-catalog.json`. Missing → block, reason `"behavior-catalog.json não encontrado em outputs/qa/behavior-mapping/ — a rastreabilidade ao behavior catalog AS-IS é um requisito obrigatório do trigger FTM"`; instructs running trigger `BM` first.
5. **PASS** (steps 1, 2, 4 satisfied): emit `✅ [PRE-CONDITION GATE FTM: PASS]` and delegate to `ava-qa-test-case-generator` with `trigger: FTM`.

### Pre-condition Gate (DBI)

Runs before *any* `DBI` action.
1. **schema-inventory.md (F1)**: `Read` `outputs/asis/db/schema-inventory.md`. Missing → block, reason `"schema-inventory.md não encontrado — F1 (ava-asis-db-analyzer) não foi executada"`.
2. **Migration files (F3)**: `Glob` `outputs/tobe/source-code/src/**/Migrations/*.cs`. Zero matches → block, reason `"nenhuma migration EF Core encontrada — F3 (ava-tobe-coder-dotnet) não foi executada ou o projeto ainda não possui migrations"`.
3. **PASS**: emit `✅ [PRE-CONDITION GATE DBI: PASS]` and delegate to `ava-qa-db-integrity-test`.
4. **Blocking message**: fixed template requiring both F1 (`ava-asis-orchestrator`) and F3 (`ava-tobe-orchestrator`) to be completed before re-running `DBI`.

### Terminal Mandatory Steps (PT → RS) — global invariant

Runs after the core logic of **any** trigger that produces QA artifacts (`QS`, `GR`, `BM`,
`TS`, `TC`, `AS`, `ET`, `EC`). Excluded: standalone `PT`, standalone `RS` (they are the steps
themselves), and `FTM` (traceability matrix only — produces no parity evidence).

- **Step T1 (PT)**: if `outputs/qa/evidence-capture-report.md` exists → run PT routing with
  `invoke_context: terminal-mandatory`; else log `PT | ⚠️ SKIPPED (evidence-capture-report.md ausente)`
  and move on. If `parity_endpoints` isn't configured in `project-config.yaml` → log
  `PT | NOT_EXECUTED` and move on.
- **Step T2 (RS)**: if `outputs/tobe/parity-test-report.md` exists → run RS routing with
  `invoke_context: terminal-mandatory`; else log `RS | ⚠️ SKIPPED (parity-test-report.md ausente — PT não executado)`.
  Never blocks delivery of artifacts already produced by the original trigger.
- Followed unconditionally by the mandatory observability tracking call
  (`pipeline_observer.py ... track --agent ava-qa-orchestrator --phase F5`).
