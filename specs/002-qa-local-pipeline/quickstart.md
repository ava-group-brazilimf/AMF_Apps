# Quickstart — QA Local Pipeline Validation Guide

**Feature**: `002-qa-local-pipeline`
**Date**: 2026-07-06

---

## Prerequisites

1. A project under `projects/Meu-ERP/` with F3 source code generated
2. Python 3.9+ on PATH
3. `.NET SDK 8+` on PATH (for unit/integration test suites)
4. `Node.js 20+` and `npm` on PATH (for frontend/Playwright suites)
5. Docker or Podman running (for integration/DB test suites — optional for basic validation)

---

## Validation Scenario 1: Pre-flight passes with full artifact set (CA01–CA03)

**Purpose**: Verify `qa_preflight.py` detects missing artifacts correctly.

```bash
# Should PASS (all artifacts exist in Meu-ERP)
python src/shared/utils/qa_preflight.py --project Meu-ERP
echo "Exit code: $?"   # Expected: 0
```

**Expected output** (to stdout + `outputs/qa/preflight-report.json`):
```
🔍 QA Preflight — project: Meu-ERP
...
✅ PASS: container_runtime — docker daemon running
✅ PASS: dotnet_sdk — dotnet 8.x.x >= required 8.0
✅ PASS: nodejs — node v22.x >= required 20.0
✅ PASS: npm — npm 10.x.x
✅ PASS: nuget_feed — 2 NuGet source(s) enabled
✅ PASS: frontend_packages — npm ls OK
✅ PASS: openapi_specs — 3 spec file(s) found
✅ PASS: contract_files — 2 contract file(s) found
✅ PASS: angular_components — 15 component(s) found
Overall: PASS
```

---

## Validation Scenario 2: Pre-flight blocks on missing OpenAPI (CA01, CA03)

```bash
# Temporarily remove openapi directory
mv projects/Meu-ERP/outputs/tobe/docs/openapi projects/Meu-ERP/outputs/tobe/docs/openapi.bak

python src/shared/utils/qa_preflight.py --project Meu-ERP
echo "Exit code: $?"   # Expected: 1 (FAIL)

# Restore
mv projects/Meu-ERP/outputs/tobe/docs/openapi.bak projects/Meu-ERP/outputs/tobe/docs/openapi
```

**Expected**: `❌ FAIL: openapi_specs — 0 spec file(s) found in outputs/tobe/docs/openapi/` and exit 1.

---

## Validation Scenario 3: Test runner executes suites in order (CA04)

```bash
python src/shared/utils/qa_test_runner.py --project Meu-ERP --mode local
```

**Expected**: Suites appear in output in order: Unit → Integration → Contract → Frontend → Playwright.
`projects/Meu-ERP/outputs/qa/test-results.json` is created.
`projects/Meu-ERP/outputs/qa/test-pyramid-metrics.json` is created with non-null layer data.

---

## Validation Scenario 4: Retry on failure (CA05)

```bash
# Override: temporarily break a test to force failure (or use a project with known failing tests)
python src/shared/utils/qa_test_runner.py --project Meu-ERP --retry 2 --types unit
```

**Expected**: `test-results.json` shows `retry_count: 2` at root level; individual suites show `retry_attempts: 1` or `retry_attempts: 2` depending on when they pass.

---

## Validation Scenario 5: Pyramid metrics populated (CA19)

```bash
python src/shared/utils/qa_test_runner.py --project Meu-ERP --mode local
cat projects/Meu-ERP/outputs/qa/test-pyramid-metrics.json
```

**Expected**: `layers.unit.total`, `layers.integration.total`, `layers.e2e.total` are populated from the test run. `totals.unit_pct + totals.integration_pct + totals.e2e_pct ≈ 100.0`.

---

## Validation Scenario 6: HTML pyramid section (CA17, CA18)

```bash
# After test-pyramid-metrics.json exists:
python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project Meu-ERP
# Open the generated HTML:
start projects/Meu-ERP/outputs/summary/summary.html
```

**Expected**: Page contains a `<section id="qa-test-pyramid">` with a visual pyramid showing Unit / Integration / E2E layers and test counts.

---

## Validation Scenario 7: Bridge canonical path guard (CA12)

1. Invoke `@ava-qa-bridge-fastqa-tobe` (FQ trigger) on project Meu-ERP
2. After completion, verify:

```bash
# All bridge artifacts MUST exist here:
ls projects/Meu-ERP/outputs/tobe/qa/fastqa/

# NONE should exist at the old path:
ls projects/Meu-ERP/outputs/qa/fastqa/  # Should be empty or non-existent
```

---

## Validation Scenario 8: CI pipeline targets (CA20, CA21)

```bash
cat projects/Meu-ERP/outputs/tobe/devops/qa-ci-pipeline.yml | grep "test:"
```

**Expected**: Lines matching `test:unit`, `test:integration`, `test:contract`, `test:frontend` as independent job entries. No hardcoded `.csproj` paths — discovery uses `dotnet sln list` or glob patterns.

---

## Validation Scenario 9: Checklists have exactly 69 criteria (CA08, CA09)

```bash
grep -c "^\- \[" src/shared/checklists/contract-test-checklist.md
grep -c "^\- \[" src/shared/checklists/frontend-test-checklist.md
```

**Expected**: Both commands output `69`.

---

## Validation Scenario 10: Playwright template compiles (CA10)

```bash
cd src/shared/templates
npx tsc --noEmit --target ES2020 --moduleResolution node playwright-api-tobe.template.ts 2>&1
echo "Exit code: $?"   # Expected: 0
```
