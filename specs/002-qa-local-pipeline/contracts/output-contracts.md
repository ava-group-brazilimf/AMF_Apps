# Output Contracts: QA Local Execution Pipeline

**Feature**: `002-qa-local-pipeline`
**Date**: 2026-07-06

---

## Contract 1: `ava-qa-local-runner` (new agent)

```yaml
inputs:
  required:
    - "projects/{project_name}/context/project-config.yaml"
  optional:
    - "projects/{project_name}/outputs/qa/test-results.json"
    - "projects/{project_name}/outputs/tobe/source-code/*.sln"

outputs:
  preflight_report:    "projects/{project_name}/outputs/qa/preflight-report.json"
  test_results:        "projects/{project_name}/outputs/qa/test-results.json"
  test_pyramid_data:   "projects/{project_name}/outputs/qa/test-pyramid-metrics.json"
  consolidated_report: "projects/{project_name}/outputs/qa/qa-execution-report.html"
  ci_pipeline:         "projects/{project_name}/outputs/tobe/devops/qa-ci-pipeline.yml"

next_agent: "ava-summary"
```

**Blocking conditions**:
- `preflight-report.json` overall == `"FAIL"` → agent sets `AgentResult.success = false` and stops before test execution

---

## Contract 2: `ava-qa-bridge-fastqa-tobe` v2.0.0 (BREAKING path change)

```yaml
inputs:
  required:
    - "projects/{project_name}/outputs/tobe/qa/test-cases.md"
    - "projects/{project_name}/outputs/tobe/docs/openapi/*.yaml"
    - "projects/{project_name}/context/project-config.yaml"
  optional:
    - "fastqa/scripts/project_config.tobe.json"

outputs:
  fastqa_gherkin:    "projects/{project_name}/outputs/tobe/qa/fastqa/gherkin-scenarios.md"
  fastqa_exploratory: "projects/{project_name}/outputs/tobe/qa/fastqa/exploratory-api-report.md"
  fastqa_automation:  "projects/{project_name}/outputs/tobe/qa/fastqa/automation-summary.md"

canonical_path_guard: "outputs/tobe/qa/fastqa/"
# Any write outside this path is a CRITICAL protocol violation.
```

**Migration from v1.2.0**: `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/` everywhere.

---

## Contract 3: `ava-qa-contract-test-generator` v1.2.0 (MINOR additions)

```yaml
# Added outputs (existing outputs unchanged):
outputs:
  # existing (unchanged):
  contract_test_report: "projects/{project_name}/outputs/qa/contract-tests/contract-test-report.md"
  # added:
  observability_events: "appended to contract-test-report.md under ## Observability section"

# Added inputs (optional):
inputs:
  optional:
    - "src/shared/checklists/contract-test-checklist.md"   # validation checklist reference
```

---

## Contract 4: `ava-qa-frontend-test-generator` v1.2.0 (MINOR additions)

```yaml
# Added outputs (existing outputs unchanged):
outputs:
  # existing (unchanged):
  frontend_test_report: "projects/{project_name}/outputs/qa/frontend-tests/frontend-test-report.md"
  # added:
  observability_events: "appended to frontend-test-report.md under ## Observability section"

# Added inputs (optional):
inputs:
  optional:
    - "src/shared/checklists/frontend-test-checklist.md"   # validation checklist reference
    - "src/shared/templates/playwright-api-tobe.template.ts"  # Playwright template reference
```

---

## Contract 5: New Shared Artifacts

```yaml
contract_test_checklist:
  path: "src/shared/checklists/contract-test-checklist.md"
  format: "Markdown with 69 checkbox items"
  consumed_by:
    - "ava-qa-contract-test-generator"

frontend_test_checklist:
  path: "src/shared/checklists/frontend-test-checklist.md"
  format: "Markdown with 69 checkbox items"
  consumed_by:
    - "ava-qa-frontend-test-generator"

playwright_api_template:
  path: "src/shared/templates/playwright-api-tobe.template.ts"
  format: "TypeScript (must pass tsc --noEmit)"
  consumed_by:
    - "ava-qa-frontend-test-generator"
    - "ava-qa-bridge-fastqa-tobe"
```

---

## Contract 6: `ava-qa-orchestrator` v1.7.0 (MINOR — trigger + path)

```yaml
# Changed outputs (path migration for FQ artifacts):
outputs:
  # changed from outputs/qa/fastqa/ to outputs/tobe/qa/fastqa/:
  fastqa_gherkin_scenarios:  "projects/{project_name}/outputs/tobe/qa/fastqa/gherkin-scenarios.md"
  fastqa_exploratory_report: "projects/{project_name}/outputs/tobe/qa/fastqa/exploratory-api-report.md"
  fastqa_automation_summary: "projects/{project_name}/outputs/tobe/qa/fastqa/automation-summary.md"
  # new outputs (from LR trigger):
  preflight_report:    "projects/{project_name}/outputs/qa/preflight-report.json"
  test_results:        "projects/{project_name}/outputs/qa/test-results.json"
  test_pyramid_data:   "projects/{project_name}/outputs/qa/test-pyramid-metrics.json"
  qa_execution_report: "projects/{project_name}/outputs/qa/qa-execution-report.html"

# New trigger registered:
triggers:
  LR: "Local Runner — dispatches ava-qa-local-runner for local test execution"
```
