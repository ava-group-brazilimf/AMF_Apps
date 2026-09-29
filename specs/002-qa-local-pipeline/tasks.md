# Agent Development Tasks: QA Local Execution Pipeline, Observability & Test Pyramid

**Plan**: `specs/002-qa-local-pipeline/plan.md`
**Agent ID**: `ava-qa-local-runner` (new) + 4 modify-existing | **Phase**: `F5` | **Module**: `qa-agents`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> This feature spans 1 new agent + 5 modify-existing components — tasks are organized by
> IMFAI category, not by component.

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before Category 2. Declares the primary new agent identity and all version bumps.

- [ ] **1.1** Create `src/modules/ava-fabric-agents/qa-agents/agents/local-runner-agent.md` (empty file to establish path)
- [ ] **1.2** Write YAML frontmatter block in `local-runner-agent.md`:
  - `name: "ava-qa-local-runner"` — matches `^ava-[a-z0-9-]+$`
  - `version: "1.0.0"`
  - `description: |` — Portuguese body ending with `Ativa com: "executar testes locais", "qa local pipeline", "run qa pipeline", "qa test runner", "executar suítes de teste", "LR".`
  - `allowed-tools: Read, Write, Edit, Bash, Glob, Grep`
  - Do NOT add `phase`, `module`, `inputs`, `outputs`, or `dependencies` to frontmatter
- [ ] **1.3** Write `## Output Contract` YAML block in `local-runner-agent.md` with all 5 lowercase `{project_name}` paths:
  - `preflight_report: "projects/{project_name}/outputs/qa/preflight-report.json"`
  - `test_results: "projects/{project_name}/outputs/qa/test-results.json"`
  - `test_pyramid_data: "projects/{project_name}/outputs/qa/test-pyramid-metrics.json"`
  - `consolidated_report: "projects/{project_name}/outputs/qa/qa-execution-report.html"`
  - `ci_pipeline: "projects/{project_name}/outputs/tobe/devops/qa-ci-pipeline.yml"`
- [ ] **1.4** Verify output path conventions from `plan.md §4`:
  - `outputs/qa/` used for F5 execution artifacts ✓
  - `outputs/tobe/devops/` used for CI YAML ✓
  - `outputs/tobe/qa/fastqa/` is bridge agent's canonical path (NOT `outputs/qa/fastqa/`) ✓
- [ ] **1.5** Create `.github/skills/ava-qa-local-runner/SKILL.md` (user-facing dispatch — Article XI):
  - Step 1: resolve `project_name` from `projects/*/context/project-config.yaml` (exclude `_template`)
  - Step 2: read `projects/{project_name}/context/agent-task-config.yaml` and `shared-context.md`
  - Step 3: pass `language` from `project-config.yaml` to downstream agent
  - Step 4: delegate to `src/modules/ava-fabric-agents/qa-agents/agents/local-runner-agent.md`
- [ ] **1.6** [P] Declare version bumps for all modify-existing components (no file changes yet — just document decisions for Category 2):
  - `ava-qa-bridge-fastqa-tobe`: `1.2.0` → `2.0.0` (MAJOR — breaking path contract)
  - `ava-qa-orchestrator`: `1.6.0` → `1.7.0` (MINOR — new `LR` trigger + path corrections)
  - `ava-qa-contract-test-generator`: `1.1.0` → `1.2.0` (MINOR — observability + checklist)
  - `ava-qa-frontend-test-generator`: `1.1.0` → `1.2.0` (MINOR — observability + checklist + template)

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. Tasks are grouped by component; within each group, the order matters.

### 2-A: New agent `ava-qa-local-runner`

- [ ] **2.1** Write `## Papel & Persona` section in `local-runner-agent.md` (pt-BR):
  - Persona: Engenheiro de plataforma QA, garante execução orquestrada e observável do pipeline
  - Scope boundary: wrapper formal de `qa_preflight.py` + `qa_test_runner.py`; não substitui os scripts
- [ ] **2.2** Write `## Input Contract` section in `local-runner-agent.md`:
  - Required: `projects/{project_name}/context/project-config.yaml`
  - Optional: `projects/{project_name}/outputs/qa/test-results.json`, `projects/{project_name}/outputs/tobe/source-code/*.sln`
- [ ] **2.3** Write `## Pre-condition Gate` section in `local-runner-agent.md`:
  - Bloqueia se `qa_preflight.py` retorna exit 1 (FAIL): emitir `⛔ PRE-CONDITION GATE: BLOCKED — preflight-report.json: FAIL`
  - Se script ausente: registrar `PREFLIGHT_SKIPPED` e continuar (não bloquear)
- [ ] **2.4** Write `## Execution Steps` (7 passos numerados, em pt-BR) in `local-runner-agent.md`:
  - Step 1: Ler `project-config.yaml` e `shared-context.md`; extrair `project_name`, `trace_id`, `language`, `qa_runner.retry_count`
  - Step 2: Executar `python src/shared/utils/qa_preflight.py --project {project_name}` → ler `preflight-report.json`; se `overall == "FAIL"` → bloquear
  - Step 3: Executar `python src/shared/utils/qa_test_runner.py --project {project_name} --mode local --retry {retry_count}` → aguardar conclusão
  - Step 4: Ler `test-results.json` e `test-pyramid-metrics.json` gerados; validar schemas
  - Step 5: Gerar `qa-execution-report.html` com seção Test Summary (dados de `test-results.json`) + link/embed da QA Test Pyramid
  - Step 6: Gerar `qa-ci-pipeline.yml` em `outputs/tobe/devops/` com jobs `test:unit`, `test:integration`, `test:contract`, `test:frontend`; detecção automática de projetos via `dotnet sln list`; suporte a `github-actions` ou `azure-devops` conforme `project-config.yaml → devops_platform`
  - Step 7: Emitir `↳ ✅ [ava-qa-local-runner]` com resumo: total de testes, status por camada, path do HTML report
- [ ] **2.5** Write `## Completion Checklist Gate` (6 critérios obrigatórios antes do Step 7) in `local-runner-agent.md`:
  - `preflight-report.json` existe em `outputs/qa/`
  - `test-results.json` existe em `outputs/qa/`
  - `test-pyramid-metrics.json` existe em `outputs/qa/`
  - `qa-execution-report.html` existe em `outputs/qa/`
  - `qa-ci-pipeline.yml` existe em `outputs/tobe/devops/`
  - `trace_id` propagado no sinal de conclusão
- [ ] **2.6** Write `## Guardrails` section in `local-runner-agent.md`:
  - Não executar suítes de teste se `qa_preflight.py` retornar FAIL
  - Não gerar outputs sintéticos — todo HTML deve ser baseado em `test-results.json` lido
  - `qa-ci-pipeline.yml` NUNCA com caminhos `.csproj` hardcoded — usar `dotnet sln list`
  - Se `qa_test_runner.py` exit 0 mas `test-results.json` ausente → ABORT com erro explícito

### 2-B: Python scripts — `qa_preflight.py` additions

- [ ] **2.7** Add `check_openapi_specs(project_name)` function to `src/shared/utils/qa_preflight.py`:
  - Glob: `projects/{project_name}/outputs/tobe/docs/openapi/*.yaml`
  - PASS if ≥ 1 file found; FAIL if 0 files found
  - Return dict `{"id": "openapi_specs", "status": "PASS|FAIL", "detail": "..."}`
- [ ] **2.8** Add `check_contract_files(project_name)` function to `src/shared/utils/qa_preflight.py`:
  - Glob patterns: `*Consumer*.cs` and `*Pact*.cs` under `outputs/tobe/source-code/` (recursive)
  - WARNING (not FAIL) if 0 files found — CT trigger may not have run yet
  - Return dict with `"id": "contract_files"`
- [ ] **2.9** Add `check_angular_components(project_name)` function to `src/shared/utils/qa_preflight.py`:
  - Glob: `outputs/tobe/source-code/frontend/src/app/**/*.component.ts` (recursive)
  - WARNING (not FAIL) if 0 files found — FT trigger may not have run yet
  - Return dict with `"id": "angular_components"`
- [ ] **2.10** Add JSON file output to `qa_preflight.py` `main()`:
  - Write `projects/{project_name}/outputs/qa/preflight-report.json` with full check results and `overall` field (PASS/WARNING/FAIL)
  - `overall` derivation: FAIL if any check is FAIL; WARNING if any check is WARNING and none are FAIL; PASS otherwise
  - Add `get_ntp_timestamp()` helper (see Task 2.11) and populate `generated_at` + `ntp_fallback` fields in the JSON
- [ ] **2.11** Add `get_ntp_timestamp(ntp_server: str) -> tuple` to `src/shared/utils/qa_preflight.py`:
  - Try `ntplib.NTPClient().request(ntp_server, version=3, timeout=2)` — return `(iso_ts, False)`
  - On any exception: return `(datetime.now(timezone.utc).isoformat(), True)`
  - `ntp_server` read from `project-config.yaml → quality_gates.ntp_server`; default `"pool.ntp.org"`
  - Import `ntplib` inside try/except ImportError (soft dependency)

### 2-C: Python scripts — `qa_test_runner.py` additions

- [ ] **2.12** Add `--retry` argument to `argparse` in `src/shared/utils/qa_test_runner.py`:
  - `parser.add_argument("--retry", type=int, default=None)`
  - If `--retry` not specified: read `qa_runner.retry_count` from `project-config.yaml`; default 0 if absent
  - Add `retry_count` field (int) to root of output JSON
- [ ] **2.13** Add `run_with_retry(run_fn, *args, max_retries, **kwargs)` wrapper in `src/shared/utils/qa_test_runner.py`:
  - Loop `max_retries + 1` times; break early on zero failures
  - Set `suite["retry_attempts"]` = number of extra attempts made (0 = ran once and passed)
  - Print `⚠️ Retry {n}/{max}` on each retry
- [ ] **2.14** Add `write_pyramid_metrics(suites, output_dir, project_name, ntp_fallback)` function in `src/shared/utils/qa_test_runner.py`:
  - Layer mapping: `unit` → Unit; `integration`+`db`+`contract` → Integration; `frontend`+`playwright` → E2E
  - Write `projects/{project_name}/outputs/qa/test-pyramid-metrics.json` per schema in `data-model.md §1`
  - Compute `unit_pct`, `integration_pct`, `e2e_pct`; include `target_distribution: {unit_pct: 70.0, integration_pct: 20.0, e2e_pct: 10.0}`
  - Call at end of `main()` after `write_results()`
- [ ] **2.15** Add same `get_ntp_timestamp()` helper (or import from shared) and populate `execution_timestamp` + `ntp_fallback` in `test-results.json`

### 2-D: `ava-qa-bridge-fastqa-tobe` — MAJOR path migration (v1.2.0 → v2.0.0)

- [ ] **2.16** Bump version in `src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md`:
  - `version: "1.2.0"` → `version: "2.0.0"` in frontmatter
  - Update `date` field to `2026-07-06`
- [ ] **2.17** Migrate all output path references in `bridge-fastqa-tobe.md` from `outputs/qa/fastqa/` to `outputs/tobe/qa/fastqa/`:
  - Output Contract table (lines ~170–172): 3 paths
  - `qa_dir` variable (line ~969): 1 path
  - Completion Signal paths (lines ~1094–1096): 3 paths
  - Guardrail notes (lines ~1116, ~1129): 2 path references
  - Execution Invariant (line ~24): 1 path in the prohibition rule
- [ ] **2.18** Add Fraud Guard declaration to `## ⛔ Execution Invariant` section in `bridge-fastqa-tobe.md`:
  ```
  ❌ Emitir conteúdo não fundamentado em artefatos lidos explicitamente (FRAUD GUARD)
     → Cada Write() DEVE ser precedido por ao menos um Read() do artefato fonte
     → Se nenhum Read() foi executado antes do Write() → ABORT: "FRAUD_GUARD: synthetic output detected"
  ```
- [ ] **2.19** Update spec-read confirmation string in `bridge-fastqa-tobe.md` to reference `v2.0.0`:
  - Change `"✅ SPEC LIDO: ava-qa-bridge-fastqa-tobe v{version}"` references so version is explicit as `v2.0.0`

### 2-E: `ava-qa-orchestrator` — MINOR bump (v1.6.0 → v1.7.0)

- [ ] **2.20** Bump `version: 1.6.0` → `version: 1.7.0` and `date: "2026-07-06"` in `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md`
- [ ] **2.21** Add `ava-qa-local-runner` row to Agent Team QA table in `qa-orchestrator-agent.md`:
  - `| ava-qa-local-runner | Execução Local | Após RS (trigger LR) — substitui chamada direta a qa_test_runner.py |`
- [ ] **2.22** Add `LR` trigger to Triggers / Menu table in `qa-orchestrator-agent.md`:
  - `| LR | **Local Runner** — executa pipeline QA local completo (pré-condições + suítes + HTML + CI YAML) |`
- [ ] **2.23** Update Output Contract in `qa-orchestrator-agent.md` — 3 path changes + 4 new entries:
  - Change `fastqa_gherkin_scenarios`, `fastqa_exploratory_report`, `fastqa_automation_summary` from `outputs/qa/fastqa/` to `outputs/tobe/qa/fastqa/`
  - Add: `preflight_report`, `test_results`, `test_pyramid_data`, `qa_execution_report` (all under `outputs/qa/`)
- [ ] **2.24** Replace step `11b` body in `qa-orchestrator-agent.md`: substitute direct `python src/shared/utils/qa_test_runner.py` call with dispatch to `ava-qa-local-runner` (trigger `LR`); update JSON path reading and failure handling per plan Task 5.1
- [ ] **2.25** Update FQ COMPLETION GATE (step 9c) in `qa-orchestrator-agent.md`: replace all `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/` in glob patterns and existence checks
- [ ] **2.26** Update bridge dispatch instruction text in step 9 of `qa-orchestrator-agent.md`: update the `outputs/tobe/qa/fastqa/` path reference in the inline instruction passed to the bridge agent

### 2-F: `ava-qa-contract-test-generator` — MINOR bump (v1.1.0 → v1.2.0)

- [ ] **2.27** [P] Bump `version: 1.1.0` → `version: 1.2.0` and `date: "2026-07-06"` in `src/modules/ava-fabric-agents/qa-agents/agents/contract-test-generator-agent.md`
- [ ] **2.28** [P] Add `## Observabilidade` section to `contract-test-generator-agent.md` (pt-BR):
  - Events: `test_generation_started` (at Step 1 start), `test_generation_completed` (final step, success), `test_generation_failed` (irrecoverable error)
  - Format reference: `specs/002-qa-local-pipeline/data-model.md §4`
  - Append event block as fenced JSON under `## Observabilidade` in `contract-test-report.md` output
- [ ] **2.29** [P] Add `## NTP Timestamp Guardrail` section to `contract-test-generator-agent.md`:
  - NTP server: `project-config.yaml → quality_gates.ntp_server` (default: `pool.ntp.org`), timeout 2s
  - Fallback: `datetime.utcnow()` with `ntp_fallback: true` — execution NOT blocked
- [ ] **2.30** [P] Add `## Checklist de Validação` section to `contract-test-generator-agent.md`:
  - Reference: `src/shared/checklists/contract-test-checklist.md`
  - Rule: if file absent → register `CHECKLIST_NOT_FOUND` and proceed (do not block)

### 2-G: `ava-qa-frontend-test-generator` — MINOR bump (v1.1.0 → v1.2.0)

- [ ] **2.31** [P] Bump `version: 1.1.0` → `version: 1.2.0` and `date: "2026-07-06"` in `src/modules/ava-fabric-agents/qa-agents/agents/frontend-test-generator-agent.md`
- [ ] **2.32** [P] Add optional input to Input Contract in `frontend-test-generator-agent.md`:
  - `"src/shared/templates/playwright-api-tobe.template.ts"` — Playwright API template reference
- [ ] **2.33** [P] Add `## Observabilidade`, `## NTP Timestamp Guardrail`, and `## Checklist de Validação` sections to `frontend-test-generator-agent.md` (same pattern as Tasks 2.28–2.30, but referencing `frontend-test-checklist.md`)

### 2-H: `build_summary_comprehensive.py` — QA Test Pyramid section

- [ ] **2.34** Add `build_qa_pyramid_section(project_dir: Path) -> str` function to `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`:
  - Try: `json.loads((project_dir / "outputs/qa/test-pyramid-metrics.json").read_text())`
  - On `FileNotFoundError` or `json.JSONDecodeError`: return `<section id="qa-test-pyramid"><p class="no-data">No QA metrics available</p></section>`
  - On success: generate HTML table (Layer | Target % | Actual % | Total Tests | Status) + CSS pyramid visual
  - CSS pyramid: three `div` blocks with `clip-path` trapezoids, colors: Unit=green, Integration=orange, E2E=blue
  - Status indicator: ✅ if `|actual_pct - target_pct| <= 10`, ⚠️ otherwise
- [ ] **2.35** Inject `build_qa_pyramid_section()` call at the correct insertion point in `build_summary_comprehensive.py`:
  - Call after the existing test summary section (search for existing `test-summary` section anchor)
  - Inject the returned HTML string before `</body>`
  - If `test-pyramid-metrics.json` is absent: section renders gracefully (no exception propagation)

---

## Category 3 — Shared Schema Updates

Depends on Category 2 (schemas are extended after implementation is clear). Tasks 3.1–3.3 are independent.

- [ ] **3.1** [P] Formalize `test-pyramid-metrics.json` schema by documenting it in `src/shared/schemas/` (new file `test-pyramid-metrics.schema.json`) per `data-model.md §1`:
  - Fields: `generated_at`, `ntp_fallback`, `project`, `layers` (unit/integration/e2e), `totals`, `target_distribution`
  - Layer object: `{total, passed, failed, skipped, suites[]}`
- [ ] **3.2** [P] Extend `test-results.json` informal schema (documented in `qa_test_runner.py` docstring) with new fields:
  - Root: `ntp_fallback: bool`, `retry_count: int`
  - Per suite: `retry_attempts: int`
  - Update the docstring schema block in `qa_test_runner.py` to reflect additions
- [ ] **3.3** [P] Add `quality_gates.ntp_server` and `qa_runner.retry_count` to `projects/_template/context/project-config.yaml`:
  ```yaml
  quality_gates:
    ntp_server: "pool.ntp.org"
  qa_runner:
    retry_count: 0
  ```
- [ ] **3.4** Run `python debug_schema.py` to confirm no regressions in existing shared schemas

---

## Category 4 — Module Registration

Depends on Category 1 (agent identity must be established before registration).

- [ ] **4.1** Add `ava-qa-local-runner` entry to `src/modules/ava-fabric-agents/qa-agents/module.yaml`:
  ```yaml
  - id: ava-qa-local-runner
    file: agents/local-runner-agent.md
    skill: ava-qa-local-runner
  ```
- [ ] **4.2** Bump `qa-agents` module version `1.2.0` → `1.3.0` and update `date: "2026-07-06"` in the same file
- [ ] **4.3** Confirm top-level `module.yaml` at repo root does NOT need updating — `qa-agents` module already registered; no new phase/module created

---

## Category 5 — Quality Gate Checklists & Shared Templates

Can run parallel with Category 4 after Category 2 completes. Tasks 5.1–5.3 are fully independent.

- [ ] **5.1** Create `src/shared/checklists/contract-test-checklist.md` with **exactly 69 checkbox items** (CA08):
  - Group 1 — PactNet Consumer Setup (15 items): package install, `PactBuilder` config, consumer test class, pact file path, interaction definitions, request/response matchers, `PactVerifier` teardown, etc.
  - Group 2 — PactNet Provider Setup (15 items): `PactVerifier` config, provider states, `StateHandler` registration, middleware injection, `ProviderServiceHost` start/stop, etc.
  - Group 3 — Consumer-Provider Pair Identification (10 items): OpenAPI endpoint inventory, frontend service discovery, inter-BC communication mapping, etc.
  - Group 4 — Execution & Contract Publishing (10 items): `dotnet test` runner, pact broker URL config, `PublishResults` flag, version tagging, etc.
  - Group 5 — Observability & NTP (9 items): `test_generation_started` event, `test_generation_completed` event, NTP timestamp, `ntp_fallback` field, `trace_id` propagation, etc.
  - Group 6 — CI Integration (10 items): pipeline job `test:contract`, secrets for broker, blocking gate config, result publishing step, etc.
  - **Validate**: `grep -c "^- \[" src/shared/checklists/contract-test-checklist.md` must return `69`
- [ ] **5.2** Create `src/shared/checklists/frontend-test-checklist.md` with **exactly 69 checkbox items** (CA09):
  - Group 1 — Component Isolation Setup (15 items): `TestBed.configureTestingModule`, stub providers, `NO_ERRORS_SCHEMA` decision, `fixture.detectChanges()` placement, etc.
  - Group 2 — Services & NgRx Store Testing (15 items): `MockStore`, `provideMockActions`, `provideHttpClientTesting`, `HttpTestingController`, selector testing, effect testing, etc.
  - Group 3 — Angular Testing Library Query Patterns (12 items): `getByRole`, `getByText`, `getByLabelText`, `findBy*` async, `queryBy*` absence, `userEvent` vs `fireEvent`, etc.
  - Group 4 — Jest Configuration (8 items): `jest.config.js` preset, `moduleNameMapper`, `transform`, `setupFilesAfterFramework`, `testEnvironment: jsdom`, etc.
  - Group 5 — Observability & NTP (9 items): same pattern as contract checklist Group 5
  - Group 6 — CI Integration (10 items): `npm test -- --ci`, `--passWithNoTests`, JUnit reporter, coverage threshold, pipeline job `test:frontend`, etc.
  - **Validate**: `grep -c "^- \[" src/shared/checklists/frontend-test-checklist.md` must return `69`
- [ ] **5.3** Create `src/shared/templates/playwright-api-tobe.template.ts` (CA10):
  - Include `playwright.config.ts` pattern: `baseURL: process.env.API_BASE_URL` — NEVER hardcoded; fail fast with clear error if env var absent
  - Include `base-api-test.ts` fixture extending `test` with `Authorization: Bearer ${process.env.API_TOKEN}` injection
  - Include example `health.spec.ts` with: GET 200 health check, POST 201 create resource, 401 when token absent, 404 not found, 5xx server error pattern
  - Mark all project-specific values with `// TODO: replace with project-specific values` comment
- [ ] **5.4** Validate checklist counts after creation:
  - `grep -c "^- \[" src/shared/checklists/contract-test-checklist.md` → must output `69`
  - `grep -c "^- \[" src/shared/checklists/frontend-test-checklist.md` → must output `69`
- [ ] **5.5** Validate Playwright template compiles (CA10):
  - Run: `cd src/shared/templates && npx tsc --noEmit --target ES2020 --moduleResolution node playwright-api-tobe.template.ts`
  - Exit code must be 0; fix any type errors before marking complete

---

## Category 6 — Acceptance Validation & QA Integration

Depends on Category 2. Tasks 6.2–6.5 are independent after 6.1.

- [ ] **6.1** Confirm spec `specs/002-qa-local-pipeline/spec.md` section 4 acceptance scenarios are complete:
  - S1 Nominal (P1): all 5 outputs produced, `AgentResult.success = true`
  - S2 Pre-flight Failure (P1): FAIL on missing OpenAPI → exit 1, no test suites execute
  - S3 Bridge Spec-Read Guard (P1): confirmation string emitted, Canonical Path Guard active, Fraud Guard active
  - S4 Pyramid Visualization (P2): HTML contains `<section id="qa-test-pyramid">` with 3 layers
  - S5 Retry on Failure (P2): `retry_attempts` recorded per suite
  - S6 CI Independent Steps (P2): 4 independent targets, no hardcoded paths
- [ ] **6.2** [P] Run `qa_preflight.py` against `projects/Meu-ERP/` and validate outputs per `quickstart.md §Scenario 1`:
  - `python src/shared/utils/qa_preflight.py --project Meu-ERP`
  - Check `projects/Meu-ERP/outputs/qa/preflight-report.json` exists and has `overall` field
  - Verify `generated_at` and `ntp_fallback` fields are present
- [ ] **6.3** [P] Run `qa_test_runner.py` against `projects/Meu-ERP/` and validate per `quickstart.md §Scenario 3`:
  - `python src/shared/utils/qa_test_runner.py --project Meu-ERP --mode local`
  - Verify `test-results.json` and `test-pyramid-metrics.json` both created
  - Confirm `test-pyramid-metrics.json` has non-zero `layers` keys and `totals.unit_pct + integration_pct + e2e_pct ≈ 100`
- [ ] **6.4** [P] Validate bridge path migration by triggering FQ on `projects/Meu-ERP/` and checking per `quickstart.md §Scenario 7`:
  - Confirm all bridge artifacts appear in `projects/Meu-ERP/outputs/tobe/qa/fastqa/`
  - Confirm `projects/Meu-ERP/outputs/qa/fastqa/` is empty or non-existent (old path no longer written)
- [ ] **6.5** [P] Run the HTML summary builder and verify pyramid section per `quickstart.md §Scenario 6`:
  - `python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project Meu-ERP`
  - Open generated HTML; confirm `<section id="qa-test-pyramid">` exists with Unit / Integration / E2E rows
  - Also test with `test-pyramid-metrics.json` temporarily renamed → confirm "No QA metrics available" fallback renders without error

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6.

- [ ] **7.1** [P] Update `docs/agents-catalog.md`:
  - Replace all occurrences of `outputs/qa/fastqa/` with `outputs/tobe/qa/fastqa/`
  - Add `ava-qa-local-runner` entry in the F5 QA section: ID, version `1.0.0`, role summary, 5 output artifacts
- [ ] **7.2** [P] Add `CHANGELOG.md` entry for this feature (version date `2026-07-06`):
  - Breaking change: `ava-qa-bridge-fastqa-tobe` v2.0.0 — path `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/`
  - Migration action: `mv projects/*/outputs/qa/fastqa projects/*/outputs/tobe/qa/fastqa` for existing projects
  - New agent: `ava-qa-local-runner` v1.0.0
  - MINOR bumps: `ava-qa-orchestrator` v1.7.0, `ava-qa-contract-test-generator` v1.2.0, `ava-qa-frontend-test-generator` v1.2.0
- [ ] **7.3** [P] Update `docs/full-pipeline-guide.md` if it references the QA phase flow:
  - Add `LR` trigger to the QA phase trigger table
  - Update any `outputs/qa/fastqa/` path references to `outputs/tobe/qa/fastqa/`
- [ ] **7.4** [P] Verify `src/modules/ava-fabric-agents/qa-agents/module.yaml` diff reflects exactly the changes from Tasks 4.1–4.2 (no unintended modifications)

---

## Completion Checklist

- [ ] All 7 categories complete
- [ ] `ava-qa-local-runner` SKILL.md created at `.github/skills/ava-qa-local-runner/SKILL.md` (Article XI)
- [ ] `ava-qa-local-runner` frontmatter validated: `name` matches `^ava-[a-z0-9-]+$`, no forbidden fields
- [ ] `module.yaml` `qa-agents` bumped to `1.3.0` with new `ava-qa-local-runner` entry
- [ ] `ava-qa-bridge-fastqa-tobe` version is `2.0.0`, all `outputs/qa/fastqa/` occurrences replaced
- [ ] `ava-qa-orchestrator` version is `1.7.0`, step 11b dispatches to `ava-qa-local-runner`
- [ ] `qa_preflight.py` writes `preflight-report.json` with `openapi_specs`, `contract_files`, `angular_components` checks
- [ ] `qa_test_runner.py` writes `test-pyramid-metrics.json` after every run
- [ ] `contract-test-checklist.md` has exactly 69 criteria (validated by grep)
- [ ] `frontend-test-checklist.md` has exactly 69 criteria (validated by grep)
- [ ] `playwright-api-tobe.template.ts` passes `tsc --noEmit`
- [ ] HTML summary renders `<section id="qa-test-pyramid">` without error when metrics present and when absent
- [ ] `docs/agents-catalog.md` updated with canonical `outputs/tobe/qa/fastqa/` paths and `ava-qa-local-runner` entry
- [ ] `CHANGELOG.md` entry with MAJOR breaking change notice for `ava-qa-bridge-fastqa-tobe`
- [ ] `python debug_schema.py` returns 0 errors
