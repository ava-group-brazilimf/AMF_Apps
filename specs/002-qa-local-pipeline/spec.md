# Agent Specification: QA Local Execution Pipeline, Observability & Test Pyramid

**Feature Branch**: `002-qa-local-pipeline`
**Created**: 2026-07-06
**Status**: Draft
**Change Type**: new-agent + modify-existing
**Input**: Agent description: "Pipeline de Execução Local de QA, Observabilidade e QA Test Pyramid"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

This feature introduces one new agent, one new utility script, and modifies several
existing components across the QA pipeline (F5).

### 1.1 Primary New Agent

| Field | Value |
|---|---|
| **Agent ID** | `ava-qa-local-runner` |
| **Version** | `1.0.0` |
| **Phase** | `F5` |
| **Module** | `qa-agents` |
| **Role** | Orchestrates local QA test execution across Unit / Integration / Contract / Frontend layers, validates pre-conditions, collects metrics, and produces the consolidated QA Execution Report with the visual Test Pyramid |
| **Skill** | `ava-qa-local-runner` |
| **Dispatch** | user-facing via SKILL.md + internally dispatched by `ava-qa-orchestrator` (trigger `LR`) |

### 1.2 Supporting New Component

| Field | Value |
|---|---|
| **Component** | `qa_preflight.py` |
| **Type** | Python utility script (internal — no SKILL.md) |
| **Location** | `src/shared/utils/qa_preflight.py` |
| **Role** | Pre-flight validation: checks required artifacts (OpenAPI specs, contract files, Angular components) and tool availability (dotnet, Node.js, Docker/Podman) before any test suite executes |
| **Invoked by** | `ava-qa-local-runner` (Step 1) |

### 1.3 Modified Agents & Components

| Component | Current Version | New Version | Bump Type | Change Summary |
|---|---|---|---|---|
| `ava-qa-bridge-fastqa-tobe` | `1.2.0` | `2.0.0` | MAJOR | Mandatory spec-read confirmation, canonical path enforcement (`outputs/tobe/qa/fastqa/`), Fraud Guard for synthetic outputs, `FQ` trigger registration in `ava-qa-orchestrator` |
| `ava-qa-contract-test-generator` | existing | MINOR | Adds 69-criterion validation checklist, mandatory observability event emission, NTP-protected timestamp guardrail |
| `ava-qa-frontend-test-generator` | existing | MINOR | Adds 69-criterion validation checklist, Playwright API template reference, mandatory observability event emission, NTP-protected timestamp guardrail |
| `build_summary_comprehensive.py` | N/A (utility) | N/A | Parses new `test-pyramid-metrics.json` and renders QA Test Pyramid section in HTML summary |
| `ava-qa-orchestrator` | existing | MINOR | Registers `FQ` trigger → dispatches `ava-qa-bridge-fastqa-tobe`; registers `LR` trigger → dispatches `ava-qa-local-runner` |

> Because `ava-qa-bridge-fastqa-tobe` already has an entry in
> `src/modules/ava-fabric-agents/qa-agents/module.yaml`, no new registration is needed
> for that agent — only the version bump and body changes.
> `ava-qa-local-runner` requires a NEW entry in `module.yaml` (Article IV).

---

## 2. Agent Frontmatter

### Primary: `ava-qa-local-runner` (new)

```yaml
---
name: "ava-qa-local-runner"
version: "1.0.0"
description: |
  Orquestra a execução local do pipeline de QA nas camadas Unit, Integration,
  Contract e Frontend. Valida pré-condições via qa_preflight.py, executa suítes
  em sequência, coleta métricas e gera o relatório HTML consolidado com a QA
  Test Pyramid.
  Ativa com: "executar testes locais", "qa local pipeline", "run qa pipeline",
  "qa test runner", "executar suítes de teste", "LR".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

### Modified: `ava-qa-bridge-fastqa-tobe` (MAJOR bump — v1.2.0 → v2.0.0)

```yaml
---
name: "ava-qa-bridge-fastqa-tobe"
version: "2.0.0"
description: |
  Bridge Agent entre o pipeline TO-BE (F2/F3/F5) e o ecossistema FastQA.
  Gera artefatos exclusivamente no caminho canônico outputs/tobe/qa/fastqa/.
  Exige confirmação de leitura integral do spec antes de qualquer execução.
  Bloqueia geração de outputs sintéticos via Fraud Guard.
  Ativa com: "bridge FastQA TO-BE", "gerar testes FastQA TO-BE",
  "FastQA API tests", "testes exploratórios API", "bridge tobe fastqa", "FQ".
allowed-tools: Read, Write, Glob, Grep
---
```

---

## 3. Output Contract

### `ava-qa-local-runner` — new outputs

```yaml
outputs:
  preflight_report:    "projects/{project_name}/outputs/qa/preflight-report.json"
  test_results:        "projects/{project_name}/outputs/qa/test-results.json"
  test_pyramid_data:   "projects/{project_name}/outputs/qa/test-pyramid-metrics.json"
  consolidated_report: "projects/{project_name}/outputs/qa/qa-execution-report.html"
  ci_pipeline:         "projects/{project_name}/outputs/tobe/devops/qa-ci-pipeline.yml"
```

### `ava-qa-bridge-fastqa-tobe` — canonical path (BREAKING CHANGE)

```yaml
outputs:
  fastqa_artifacts: "projects/{project_name}/outputs/tobe/qa/fastqa/"
  # ALL FastQA TO-BE artifacts MUST be written exclusively to this directory.
  # Writing to any other path is a critical execution error.
```

### New Shared Artifacts (checklists & templates)

```yaml
outputs:
  contract_test_checklist: "src/shared/checklists/contract-test-checklist.md"   # 69 criteria
  frontend_test_checklist: "src/shared/checklists/frontend-test-checklist.md"   # 69 criteria
  playwright_api_template: "src/shared/templates/playwright-api-tobe.template.ts"
```

> **Append decision**: `test-pyramid-metrics.json` is a NEW file consumed by
> `build_summary_comprehensive.py`. It does NOT append to an existing contract file,
> so it does not risk breaking existing downstream parsers.

Path conventions applied:

| Artifact | Phase Folder |
|---|---|
| Pre-flight report, test results, pyramid data, HTML report | `outputs/qa/` (F5) |
| CI pipeline YAML | `outputs/tobe/devops/` (F7) |
| FastQA TO-BE artifacts | `outputs/tobe/qa/fastqa/` (F5 canonical) |
| Checklists & Playwright template | `src/shared/` (shared utilities) |

---

## 4. User Scenarios (Given-When-Then)

> Story descriptions in Brazilian Portuguese. Acceptance scenarios in English for
> BDD traceability with `ava-qa-behavior-mapping` and `ava-qa-scenario-generator`.

---

### Scenario 1 — Nominal Path: Full QA Pipeline Execution (Priority: P1)

**Story**: Como o orquestrador da migração, quero que o pipeline QA valide o ambiente,
execute todas as suítes de teste em sequência e produza um relatório HTML com a pirâmide
de testes, para ter visibilidade completa da qualidade do sistema TO-BE.

**Why this priority**: Core feature — delivers the primary business value of the entire spec.

**Acceptance Scenarios**:

1. **Given** a project with OpenAPI specs, Angular components, contract files, dotnet, Node.js, and Docker available, **When** `ava-qa-local-runner` is triggered, **Then** `qa_preflight.py` executes first and all validations pass with exit code 0.
2. **Given** pre-flight passes, **When** `qa_test_runner.py` executes, **Then** suites run in strict order: Unit → Integration → Contract → Frontend, and metrics are collected for each layer.
3. **Given** all suites complete, **When** the report is generated, **Then** `qa-execution-report.html` is created containing a visual QA Test Pyramid section.
4. **Given** the above, **Then** `test-pyramid-metrics.json` is populated with per-layer test counts and percentages (Unit, Integration, E2E/Frontend).
5. **Given** execution completes, **Then** `AgentResult.success` is true and `AgentResult.artifacts` lists all five output files.

---

### Scenario 2 — Pre-flight Failure: Missing Required Artifact (Priority: P1)

**Story**: Como o engenheiro de QA, quero que o pipeline seja bloqueado imediatamente
quando artefatos obrigatórios estiverem ausentes, para evitar execuções mal fundamentadas.

**Why this priority**: Safety gate — failing fast prevents wasted cycles and misleading results.

**Acceptance Scenarios**:

1. **Given** OpenAPI spec files are absent from the expected path, **When** `qa_preflight.py` runs, **Then** it emits a structured error listing the missing artifact and exits with code 1.
2. **Given** `qa_preflight.py` exits with code 1, **When** the runner attempts to proceed to test execution, **Then** the test run is blocked and `preflight-report.json` records the failure reason.
3. **Given** `dotnet` CLI is not found on PATH, **When** `qa_preflight.py` validates tool availability, **Then** it emits "Tool not found: dotnet" and exits with code 1.
4. **Given** Docker and Podman are both absent, **When** `qa_preflight.py` validates container runtime, **Then** it emits "Container runtime not available" and the Integration suite is marked as skipped (not failed) in the report.

---

### Scenario 3 — Bridge FastQA: Spec-Read Guard & Fraud Guard (Priority: P1)

**Story**: Como o arquiteto de testes, quero garantir que o agente bridge-fastqa-tobe
sempre confirme a leitura do spec antes de gerar artefatos e bloqueie outputs sintéticos,
para manter a integridade dos artefatos de teste.

**Why this priority**: Quality gate — prevents cascading failures from hallucinated test content.

**Acceptance Scenarios**:

1. **Given** `ava-qa-bridge-fastqa-tobe` v2.0.0 is invoked, **When** execution begins, **Then** the agent emits "✅ SPEC LIDO: ava-qa-bridge-fastqa-tobe v2.0.0 — {N} steps, 5 elementos" before any step executes.
2. **Given** the agent attempts to write an artifact to a path outside `outputs/tobe/qa/fastqa/`, **Then** the Canonical Path Guard rejects the write and logs "CANONICAL PATH VIOLATION: expected outputs/tobe/qa/fastqa/, got {actual_path}".
3. **Given** generated content is not grounded in any read spec input (Fraud Guard detects synthetic output), **Then** the write is blocked and `AgentResult.success` is false with error "FRAUD_GUARD: synthetic output detected".
4. **Given** the `FQ` trigger is fired by `ava-qa-orchestrator`, **When** bridge agent starts, **Then** `AgentResult.trace_id` propagates unchanged from orchestrator input to bridge output.

---

### Scenario 4 — QA Test Pyramid Visualization (Priority: P2)

**Story**: Como o líder técnico, quero visualizar a distribuição de testes por camada
na pirâmide QA do relatório HTML, para garantir as proporções adequadas e comunicar
a cobertura ao cliente.

**Why this priority**: High value for client communication; does not block core execution.

**Acceptance Scenarios**:

1. **Given** `test-pyramid-metrics.json` is populated with layer counts, **When** `build_summary_comprehensive.py` runs, **Then** the HTML summary contains a `<section id="qa-test-pyramid">` block.
2. **Given** the pyramid section is rendered, **Then** it displays three layers — Unit (base), Integration (middle), E2E/Frontend (top) — with test count and percentage per layer.
3. **Given** `test-pyramid-metrics.json` is absent or empty, **When** the summary builder runs, **Then** the pyramid section renders with "No metrics available" and does not throw an exception.

---

### Scenario 5 — Edge Case: Retry on Suite Failure (Priority: P2)

**Story**: Como o engenheiro de CI, quero que o pipeline suporte retry configurável
para absorver flakiness temporária sem marcar a execução como falha definitiva.

**Why this priority**: Resilience requirement — prevents false negatives in unstable environments.

**Acceptance Scenarios**:

1. **Given** a test suite fails on the first attempt and `retry_count: 2` is configured in `project-config.yaml`, **When** the failure occurs, **Then** the runner re-executes the failed suite up to 2 additional times before marking it as failed.
2. **Given** the suite passes on retry attempt 2, **Then** `test-results.json` records `passed: true`, `retry_count: 1`, and the final status is `passed`.
3. **Given** all retry attempts are exhausted and the suite still fails, **Then** `test-results.json` records `passed: false`, `retry_count: {max}`, and the report marks the suite layer as `FAILED`.

---

### Scenario 6 — CI Pipeline: Independent Test Steps (Priority: P2)

**Story**: Como o engenheiro de DevOps, quero que o pipeline CI disponibilize etapas
independentes por camada de teste, para que regressões específicas sejam executadas
sem rodar toda a pirâmide.

**Why this priority**: CI efficiency — enables fast feedback on targeted changes.

**Acceptance Scenarios**:

1. **Given** `qa-ci-pipeline.yml` is generated, **Then** it contains four independent job targets: `test:unit`, `test:integration`, `test:contract`, `test:frontend`.
2. **Given** the CI pipeline runs, **Then** test project discovery is automatic — no hardcoded project paths appear in the YAML.
3. **Given** only `test:unit` is triggered, **Then** the other three targets do not execute and the overall pipeline does not fail.

---

## 5. Quality Gate Requirements

- [ ] `ava-qa-local-runner` Agent ID follows `^ava-[a-z0-9-]+$` pattern (Article II)
- [ ] `ava-qa-local-runner` frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] `ava-qa-local-runner` registered as new entry in `src/modules/ava-fabric-agents/qa-agents/module.yaml` (Article IV)
- [ ] `ava-qa-local-runner` SKILL.md created at `.github/skills/ava-qa-local-runner/SKILL.md` (Article XI)
- [ ] `qa_preflight.py` documented as internal-only (no SKILL.md) — invoked by `ava-qa-local-runner` (Article XI)
- [ ] `ava-qa-bridge-fastqa-tobe` version bumped MAJOR (1.2.0 → 2.0.0) — output path contract change (Article X)
- [ ] `ava-qa-orchestrator` receives MINOR bump — new `FQ` and `LR` triggers (Article X)
- [ ] All output paths use lowercase `{project_name}` and correct phase folder (Article II)
- [ ] BDD scenarios cover nominal (S1), safety gate (S2–S3), visualization (S4), edge (S5–S6) (Article VI)
- [ ] No technology versions hardcoded — retry config resolved from `project-config.yaml` (Article I)
- [ ] `ava-qa-contract-test-generator` observability events and NTP timestamp guardrail documented (Article VIII)
- [ ] `ava-qa-frontend-test-generator` observability events and NTP timestamp guardrail documented (Article VIII)
- [ ] Synthetic output Fraud Guard declared and enforced in `ava-qa-bridge-fastqa-tobe` v2.0.0 (Article VIII)
- [ ] `outputs/tobe/qa/fastqa/` canonical path enforcement verified in bridge agent (CA12)
- [ ] `build_summary_comprehensive.py` update noted with no breaking changes to existing parsers (Article IX)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent / Component | Reason |
|---|---|---|
| QA Orchestrator | `ava-qa-orchestrator` | Dispatches `ava-qa-local-runner` via `LR` trigger; dispatches bridge via `FQ` |
| F3 Stack Outputs | `ava-stack-orchestrator` | OpenAPI specs and Angular components must exist before `qa_preflight.py` validates them |
| F2 Architecture | `ava-tobe-architecture-design` | Contract file definitions must exist before contract test execution |
| Build Validator | `ava-stack-build-validator` | `.sln` must compile successfully before Unit/Integration suites run |
| Summary Builder | `build_summary_comprehensive.py` | Must be extended to parse `test-pyramid-metrics.json` |
| Agents Catalog | `docs/agents-catalog.md` | Must be updated to reference the canonical `outputs/tobe/qa/fastqa/` path (CA22) |

---

## 7. Exclusions

- Legacy AS-IS test execution — handled by `ava-asis-test-qa`
- Golden Dataset capture — handled by `ava-asis-golden-dataset-capture`
- Parity comparison (AS-IS vs TO-BE) — handled by `ava-devops-compare-version`
- DAST / penetration testing — handled by `ava-asis-security-orchestrator`
- Azure DevOps test plan synchronization — handled by FastQA `@fastqa:azdo_upload_test_execution`
- Cloud / remote test execution infrastructure — out of scope (local execution only)
- E2E browser navigation tests — out of scope; only Playwright API tests are covered
- Mobile test execution — handled by FastQA `@fastqa:run_mobile_test`
- Database integrity tests — handled by `ava-qa-db-integrity-test`

---

## 8. Assumptions

- The project's F3 output contains a `.sln` file discoverable by the `dotnet` CLI at the expected source-code path.
- OpenAPI specification files exist at `projects/{project_name}/outputs/tobe/docs/` (exact filename resolved at runtime, not hardcoded).
- Angular component files exist at `projects/{project_name}/outputs/tobe/source-code/frontend/`.
- Contract files (PactNet) exist at `projects/{project_name}/outputs/tobe/source-code/contracts/`.
- Retry configuration is expressed via `qa_runner.retry_count` in `project-config.yaml`; default is 0 (no retry).
- The NTP timestamp guardrail uses the system's configured NTP endpoint; if NTP is unreachable, the guardrail falls back to local system time and logs a warning (does not block execution).
- `build_summary_comprehensive.py` is updated as part of this feature's implementation tasks — existing summary sections are not affected.
- The 69-criterion checklists for contract tests and frontend tests were derived from domain analysis; exact criteria are defined during implementation (Category 2 tasks).
- `ava-qa-bridge-fastqa-tobe` v2.0.0 is backwards-incompatible with v1.x callers due to the canonical path change — callers must be updated (only `ava-qa-orchestrator`).

---

## Success Criteria

| Criterion | Measure | CA Ref |
|---|---|---|
| Pre-flight blocks missing artifacts | `qa_preflight.py` exits 1 when OpenAPI, contract, or Angular files are absent | CA01 |
| Pre-flight blocks missing tools | `qa_preflight.py` exits 1 when dotnet, node, or container runtime is unavailable | CA02 |
| Pipeline blocked on pre-flight failure | No test suite starts when `qa_preflight.py` exits non-zero | CA03 |
| Ordered test execution | `qa_test_runner.py` runs Unit → Integration → Contract → Frontend without deviation | CA04 |
| Retry resilience | Suites re-execute up to `retry_count` before permanent failure | CA05 |
| Metrics collected from all suites | `test-results.json` contains entries for all 4 executed layers | CA06 |
| Consolidated report generated | `qa-execution-report.html` exists and is non-empty after full run | CA07 |
| Contract test checklist has 69 criteria | `contract-test-checklist.md` contains exactly 69 checkboxes | CA08 |
| Frontend test checklist has 69 criteria | `frontend-test-checklist.md` contains exactly 69 checkboxes | CA09 |
| Playwright API template available | `playwright-api-tobe.template.ts` exists and passes `tsc --noEmit` | CA10 |
| Bridge spec-read mandatory | Bridge agent emits spec-read confirmation on every invocation before Step 1 | CA11 |
| Canonical output path enforced | Zero bridge artifacts written outside `outputs/tobe/qa/fastqa/` | CA12 |
| Synthetic output blocked | Fraud Guard rejects non-grounded outputs; `AgentResult.success = false` | CA13 |
| Observability events emitted | Contract and frontend generators emit structured events per execution | CA14 |
| NTP timestamp guardrail | All execution records include NTP-validated timestamp field | CA15 |
| Container availability checked | Integration runner validates Docker/Podman before testcontainers | CA16 |
| Visual QA Test Pyramid in HTML | Report contains pyramid section with layered distribution chart | CA17 |
| Pyramid shows per-layer distribution | Unit / Integration / E2E layers each display count and percentage | CA18 |
| Pyramid auto-populated from metrics | Parser reads `test-pyramid-metrics.json` and renders pyramid without manual input | CA19 |
| CI independent steps | `qa-ci-pipeline.yml` exposes `test:unit`, `test:integration`, `test:contract`, `test:frontend` as independent targets | CA20 |
| Auto test project detection | Runner discovers `.csproj` test projects dynamically; no hardcoded paths | CA21 |
| Documentation updated | `docs/agents-catalog.md` and related docs reference `outputs/tobe/qa/fastqa/` | CA22 |
