# Data Model: QA Local Execution Pipeline

**Feature**: `002-qa-local-pipeline`
**Date**: 2026-07-06

---

## 1. `test-pyramid-metrics.json`

New file emitted by `qa_test_runner.py` alongside `test-results.json`.
Consumed by `build_summary_comprehensive.py` to render the QA Test Pyramid section.

```json
{
  "generated_at": "2026-07-06T12:00:00Z",
  "ntp_fallback": false,
  "project": "Meu-ERP",
  "layers": {
    "unit": {
      "total": 0,
      "passed": 0,
      "failed": 0,
      "skipped": 0,
      "suites": []
    },
    "integration": {
      "total": 0,
      "passed": 0,
      "failed": 0,
      "skipped": 0,
      "suites": []
    },
    "e2e": {
      "total": 0,
      "passed": 0,
      "failed": 0,
      "skipped": 0,
      "suites": []
    }
  },
  "totals": {
    "all_tests": 0,
    "unit_pct": 0.0,
    "integration_pct": 0.0,
    "e2e_pct": 0.0
  },
  "target_distribution": {
    "unit_pct": 70.0,
    "integration_pct": 20.0,
    "e2e_pct": 10.0
  }
}
```

**Field semantics**:

| Field | Type | Source | Notes |
|---|---|---|---|
| `generated_at` | ISO-8601 string | NTP-protected system time | `ntp_fallback: true` if NTP unreachable |
| `layers.unit` | Layer object | suites with `type == "unit"` | Aggregated from `test-results.json` |
| `layers.integration` | Layer object | suites with `type in ["integration", "db"]` | Aggregated |
| `layers.e2e` | Layer object | suites with `type in ["frontend", "playwright"]` | Aggregated |
| `layers.*.suites` | string[] | `suite.project` values contributing to the layer | For drill-down hover in HTML |
| `totals.unit_pct` | float | `unit.total / all_tests * 100` | 0 if `all_tests == 0` |
| `target_distribution.*` | float | Hardcoded targets per pyramid convention | Unit 70% / Integration 20% / E2E 10% |

**Layer object schema**:
```json
{
  "total": "<int>",
  "passed": "<int>",
  "failed": "<int>",
  "skipped": "<int>",
  "suites": ["<string>"]
}
```

---

## 2. `preflight-report.json`

Existing implicit output of `qa_preflight.py` — formally added to the output contract.
The script currently prints to stdout. This model adds a JSON file output.

```json
{
  "generated_at": "2026-07-06T12:00:00Z",
  "ntp_fallback": false,
  "project": "Meu-ERP",
  "overall": "PASS",
  "checks": [
    {
      "id": "container_runtime",
      "status": "PASS",
      "detail": "docker daemon running"
    },
    {
      "id": "dotnet_sdk",
      "status": "PASS",
      "detail": "dotnet 8.0.100 >= required 8.0"
    },
    {
      "id": "nodejs",
      "status": "PASS",
      "detail": "node v22.1.0 >= required 20.0"
    },
    {
      "id": "npm",
      "status": "PASS",
      "detail": "npm 10.5.0"
    },
    {
      "id": "nuget_feed",
      "status": "PASS",
      "detail": "2 NuGet source(s) enabled"
    },
    {
      "id": "frontend_packages",
      "status": "PASS",
      "detail": "npm ls --depth 0 OK"
    },
    {
      "id": "openapi_specs",
      "status": "PASS",
      "detail": "3 OpenAPI spec file(s) found in outputs/tobe/docs/openapi/"
    },
    {
      "id": "contract_files",
      "status": "PASS",
      "detail": "2 contract test file(s) found"
    },
    {
      "id": "angular_components",
      "status": "PASS",
      "detail": "15 Angular component(s) found"
    }
  ]
}
```

**`overall` derivation rule**:
- `"PASS"` — all checks are `PASS`
- `"WARNING"` — at least one `WARNING`, zero `FAIL`
- `"FAIL"` — at least one `FAIL`

**Exit code mapping**:
- `PASS` → exit 0
- `WARNING` → exit 2
- `FAIL` → exit 1

---

## 3. `test-results.json` (existing schema — additions highlighted)

The existing schema is preserved. Two fields are **added** to each suite entry:

```json
{
  "execution_timestamp": "ISO-8601",
  "ntp_fallback": false,
  "container_runtime": "docker | podman | none",
  "retry_count": 0,
  "suites": [
    {
      "type": "unit | integration | contract | db | frontend | playwright",
      "framework": "xunit | jest | playwright",
      "project": "<string>",
      "total": 0,
      "passed": 0,
      "failed": 0,
      "skipped": 0,
      "coverage_line": null,
      "coverage_branch": null,
      "duration_ms": 0,
      "status": "PASS | FAIL | NOT_EXECUTED",
      "retry_attempts": 0,
      "trx_path": null
    }
  ],
  "summary": {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "not_executed": 0,
    "success_rate": 0.0,
    "overall_status": "PASS | FAIL | PARTIAL"
  }
}
```

**New fields** (additions to existing schema):
| Field | Type | Notes |
|---|---|---|
| `ntp_fallback` (root) | boolean | true if NTP unreachable at execution time |
| `retry_count` (root) | int | `--retry` argument value used for this run |
| `suites[].retry_attempts` | int | Number of retry attempts made for this suite (0 = ran once) |

---

## 4. Observability Event Schema

New — emitted by `ava-qa-contract-test-generator` and `ava-qa-frontend-test-generator` to their respective output report files.

```json
{
  "event": "test_generation_started | test_generation_completed | test_generation_failed",
  "agent": "ava-qa-contract-test-generator | ava-qa-frontend-test-generator",
  "version": "1.2.0",
  "trace_id": "<UUID propagated from orchestrator>",
  "timestamp": "ISO-8601 (NTP-protected)",
  "ntp_fallback": false,
  "project": "Meu-ERP",
  "payload": {
    "tests_generated": 0,
    "files_created": [],
    "duration_ms": 0,
    "checklist_path": "src/shared/checklists/contract-test-checklist.md"
  }
}
```

This event block is appended at the **end** of each generator's report file (`.md`) as a fenced JSON block under `## Observability`.
