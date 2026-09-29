# Phase 0 — Research: QA Local Execution Pipeline

**Feature**: `002-qa-local-pipeline`
**Date**: 2026-07-06
**Status**: COMPLETE — all unknowns resolved

---

## Decision 1: Implementation state of `qa_preflight.py`

**Decision**: `qa_preflight.py` EXISTS at `src/shared/utils/qa_preflight.py` (205 lines) — partial implementation.

**Current coverage (already implemented)**:
- Container runtime check (Docker/Podman daemon)
- .NET SDK version check (vs `tobe_stack.backend_version`)
- Node.js version check (vs `tobe_stack.node_version`)
- npm availability check
- NuGet feed connectivity check
- Frontend `package.json` resolution check

**Missing (required by spec CA01)**:
- Artifact existence check: OpenAPI specs (`outputs/tobe/docs/openapi/*.yaml`)
- Artifact existence check: contract files (`outputs/tobe/source-code/src/**/Pact*.cs` or similar)
- Artifact existence check: Angular component files (`outputs/tobe/source-code/frontend/src/app/**/*.component.ts`)
- NTP timestamp protection for the preflight report (CA15)

**Rationale**: Add three new `check_*` functions to the existing script. The script exit-code contract (0/1/2) is already correct and must not change.

**Alternatives considered**: Replace with a new agent. Rejected — the Python script pattern already established by `build_runner.py` is consistent and testable without an agent wrapper.

---

## Decision 2: Implementation state of `qa_test_runner.py`

**Decision**: `qa_test_runner.py` EXISTS at `src/shared/utils/qa_test_runner.py` (361 lines) — partial implementation.

**Current coverage (already implemented)**:
- Detects container runtime (Docker/Podman/none)
- Runs Unit, Integration (DB), Contract, Frontend (Jest), Playwright API test suites
- Parses TRX and JUnit XML results
- Produces `test-results.json` with the schema documented in the file header
- `NOT_EXECUTED` for integration/DB when container runtime unavailable

**Missing (required by spec CA05, CA06, CA19)**:
- `--retry` argument and retry loop (CA05)
- `test-pyramid-metrics.json` output (CA19) — layer-aggregated counts for pyramid visualization
- `--retry_count` read from `project-config.yaml` as fallback when `--retry` not set

**Rationale**: Extend `main()` with a retry wrapper and add `write_pyramid_metrics()` at the end of execution. Existing JSON schema is preserved; `test-pyramid-metrics.json` is a second output file.

**Alternatives considered**: Generate pyramid from inside the HTML builder only. Rejected — decoupling pyramid data from the report builder allows independent testing of metrics accuracy.

---

## Decision 3: `ava-qa-bridge-fastqa-tobe` path migration

**Decision**: `ava-qa-bridge-fastqa-tobe` v1.2.0 uses `outputs/qa/fastqa/` throughout. All occurrences must change to `outputs/tobe/qa/fastqa/`. This is a **MAJOR** version bump (1.2.0 → 2.0.0) per Constitution Article X.

**Scope of changes in bridge agent**:
- Line 24: `❌ Gravar qualquer arquivo em outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/`
- Line 170–172: Output Contract paths
- Line 969: `qa_dir` variable
- Lines 1094–1096: Completion Signal paths
- Line 1116: Guardrail note
- Line 1129: Canonical step reference

**`ava-qa-orchestrator` must also change** its Output Contract paths (`outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/`). This is part of the orchestrator's MINOR bump.

**Rationale**: The canonical path `outputs/tobe/qa/fastqa/` places FastQA artifacts within the TO-BE output tree, consistent with the fact that these tests validate the TO-BE system. The previous `outputs/qa/fastqa/` path was ambiguous (could be mistaken for AS-IS QA output).

**Alternatives considered**: Keep `outputs/qa/fastqa/` and add a symlink. Rejected — symlinks are not portable across Windows/Linux and create confusion in artifact inventory.

---

## Decision 4: `ava-qa-local-runner` — new agent vs. orchestrator step

**Decision**: Create `ava-qa-local-runner` as a **new agent** with a SKILL.md, dispatched by `ava-qa-orchestrator` via a new `LR` trigger.

**Rationale**: The orchestrator's step 11b already calls `qa_test_runner.py` inline. Formalizing this as an agent:
1. Enables standalone user invocation (`@ava-qa-local-runner`) without running the full QS pipeline
2. Provides a formal Output Contract (HTML report, pyramid JSON)
3. Satisfies the Constitution Article XI requirement for user-facing agents
4. Allows version-independent evolution of the local runner without touching the orchestrator body

**Implementation note**: The orchestrator's step 11b will be updated to dispatch `ava-qa-local-runner` instead of calling `qa_test_runner.py` directly, maintaining the same behaviour.

**Alternatives considered**: Pure Python CLI entry-point (no agent wrapper). Rejected — inconsistent with the agent-first philosophy of IMFAI; users couldn't invoke it through the Copilot interface.

---

## Decision 5: QA Test Pyramid visualization approach

**Decision**: Two-component implementation:
1. `qa_test_runner.py` emits `test-pyramid-metrics.json` with layer-aggregated counts after test execution
2. `build_summary_comprehensive.py` reads `test-pyramid-metrics.json` and injects a CSS+SVG pyramid into the `<section id="qa-test-pyramid">` HTML block

**Layer mapping**:
| Layer | Suite types aggregated |
|---|---|
| Unit | `unit` |
| Integration | `integration`, `db` |
| E2E / Frontend | `frontend`, `playwright` |

**Fallback**: If `test-pyramid-metrics.json` is absent, the section renders "No metrics available" without throwing an exception.

**Rationale**: Decoupled approach allows the pyramid to be rendered from CI data without re-running `qa_test_runner.py`. The same `test-pyramid-metrics.json` can be produced by CI pipelines and fed into the HTML report.

**Alternatives considered**: JavaScript chart embedded in the HTML template (Chart.js/D3). Rejected — external script dependency violates the "self-contained HTML" principle of `ava-summary`.

---

## Decision 6: 69-criterion checklist count source

**Decision**: The 69-criterion count for both `contract-test-checklist.md` (CA08) and `frontend-test-checklist.md` (CA09) is a domain requirement from the spec. The criteria are authored during implementation.

**Rationale for 69 criteria (contract tests)**:
- PactNet consumer setup: ~15 criteria
- PactNet provider setup: ~15 criteria
- Consumer-provider pair identification: ~10 criteria
- Test execution and publishing: ~10 criteria
- Observability + NTP guardrail: ~9 criteria
- CI integration: ~10 criteria

**Rationale for 69 criteria (frontend tests)**:
- Component isolation setup: ~15 criteria
- Service + Store testing: ~15 criteria
- Angular Testing Library query patterns: ~12 criteria
- Jest configuration: ~8 criteria
- Observability + NTP guardrail: ~9 criteria
- CI integration: ~10 criteria

**Alternatives considered**: Derive count from automated analysis of existing test files. Rejected — the checklists are prescriptive (what should be tested) not descriptive (what is tested).

---

## Decision 7: Playwright API template location

**Decision**: `src/shared/templates/playwright-api-tobe.template.ts` — shared template, not project-specific.

**Rationale**: The template is reused across all projects. It provides the base `playwright.config.ts` + `base-api-test.ts` structure for FastQA TO-BE API tests, resolving `baseURL` from an environment variable (never hardcoded).

**Template must include**:
- `playwright.config.ts` pattern with env-based `baseURL`
- `base-api-test.ts` fixture extending `test` with auth header injection
- Example `health.spec.ts` showing GET, POST, auth, 4xx/5xx patterns
- Comments indicating which sections to replace per project

---

## Decision 8: NTP timestamp guardrail implementation

**Decision**: NTP timestamp guardrail is implemented as a **Python utility function** in `qa_preflight.py` and `qa_test_runner.py`, shared via a common import from `src/shared/utils/ntp_guard.py` (or inline if import is unavailable).

**Fallback**: If NTP server is unreachable within 2 seconds, use `datetime.now(timezone.utc)` and add a `"ntp_fallback": true` flag to the output JSON. Execution is NOT blocked.

**NTP server**: Read from `project-config.yaml → quality_gates.ntp_server`; default `pool.ntp.org`.

**Rationale**: Strict NTP blocking would cause failures in air-gapped environments. The fallback+flag approach satisfies CA15 (protected timestamp) without breaking offline execution.

---

## Summary: Implementation Gap Table

| Component | Exists | Complete | Work Required |
|---|:---:|:---:|---|
| `qa_preflight.py` | ✅ | ❌ | Add artifact checks + NTP timestamp |
| `qa_test_runner.py` | ✅ | ❌ | Add retry + pyramid metrics output |
| `ava-qa-local-runner` agent | ❌ | — | Create new agent + SKILL.md |
| `ava-qa-bridge-fastqa-tobe` v2.0.0 | ❌ | — | Path migration + Fraud Guard label |
| `ava-qa-orchestrator` MINOR bump | ❌ | — | `LR` trigger + path corrections |
| `ava-qa-contract-test-generator` MINOR | ❌ | — | Observability section + checklist ref |
| `ava-qa-frontend-test-generator` MINOR | ❌ | — | Observability + checklist + template ref |
| QA Test Pyramid (HTML) | ❌ | — | Add to `build_summary_comprehensive.py` |
| `contract-test-checklist.md` | ❌ | — | Create (69 criteria) |
| `frontend-test-checklist.md` | ❌ | — | Create (69 criteria) |
| `playwright-api-tobe.template.ts` | ❌ | — | Create |
| `docs/agents-catalog.md` path update | ❌ | — | Update path references (CA22) |
