# Data Model: screen-flow-completeness.json

**Version**: 1.0.0  
**Format**: JSON  
**Produced by**: `ava-asis-documentation` FT sub-skill (post-generation assertion)  
**Consumed by**: `ava-summary` (Summary Validator), `ava-qa-behavior-mapping`

---

## Purpose

Captures the result of the mandatory post-generation completeness assertion for `screen-flow.mmd`. The assertion verifies that the merged screen flow diagram contains at least 80% of the forms cataloged in `form-registry.json` (or glob fallback).

---

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ScreenFlowCompleteness",
  "type": "object",
  "required": [
    "assertion_id",
    "version",
    "project_name",
    "status",
    "threshold_pct",
    "coverage_pct",
    "N_nodes",
    "N_registry",
    "retry_count",
    "generated_at"
  ],
  "properties": {
    "assertion_id": {
      "type": "string",
      "const": "screen-flow-completeness",
      "description": "Canonical identifier for this assertion type"
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "Schema version (SemVer)"
    },
    "project_name": {
      "type": "string",
      "description": "Kebab-case project name from project-config.yaml"
    },
    "status": {
      "type": "string",
      "enum": ["PASS", "FAIL", "SKIPPED"],
      "description": "PASS: coverage >= threshold; FAIL: coverage < threshold; SKIPPED: form-registry.json unavailable and glob fallback also empty"
    },
    "threshold_pct": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Minimum coverage percentage required (default: 80)"
    },
    "coverage_pct": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Actual coverage: (N_nodes / N_registry) * 100"
    },
    "N_nodes": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of unique form nodes in the final merged screen-flow.mmd"
    },
    "N_registry": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of entries in form-registry.json (or glob fallback)"
    },
    "missing_forms": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of form_id values from form-registry.json NOT present in screen-flow.mmd. Omitted when status is PASS or SKIPPED."
    },
    "retry_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 3,
      "description": "How many retry attempts were performed before reaching this result"
    },
    "bc_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of bounded context batches generated (optional diagnostic)"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp from NTP (via src/shared/utils/ntp_time.py)"
    }
  },
  "additionalProperties": false
}
```

---

## Example — PASS

```json
{
  "assertion_id": "screen-flow-completeness",
  "version": "1.0.0",
  "project_name": "processaERP-001",
  "status": "PASS",
  "threshold_pct": 80,
  "coverage_pct": 82.5,
  "N_nodes": 133,
  "N_registry": 161,
  "retry_count": 0,
  "bc_count": 8,
  "generated_at": "2026-07-24T14:00:00Z"
}
```

---

## Example — FAIL (after 3 retries)

```json
{
  "assertion_id": "screen-flow-completeness",
  "version": "1.0.0",
  "project_name": "processaERP-001",
  "status": "FAIL",
  "threshold_pct": 80,
  "coverage_pct": 62.1,
  "N_nodes": 100,
  "N_registry": 161,
  "missing_forms": [
    "frmBancosCad",
    "frmFluxoCaixa",
    "frmRelatorioVendas"
  ],
  "retry_count": 3,
  "bc_count": 8,
  "generated_at": "2026-07-24T14:30:00Z"
}
```

---

## Downstream Consumption

### Summary Validator (`ava-summary`)

The Summary Validator (55 rules) reads `screen-flow-completeness.json` during F1 artifact validation:

- If `status == "FAIL"` → Summary HTML displays a warning card with coverage percentage and missing forms count
- If `retry_count >= 3` AND `status == "FAIL"` → Summary blocks promotion until `human_gate_required` is resolved

### QA Behavior Mapping (`ava-qa-behavior-mapping`)

- Uses `missing_forms` array to flag screens that need manual behavior cataloging
- Cross-references `N_nodes` with `behavior-catalog.json` to verify test coverage alignment

### Observability Pipeline

- `pipeline_observer.py` logs `screen-flow-completeness` metrics with `trace_id`
- Coverage percentage is emitted as `screen_flow_coverage_pct` metric for trend analysis
