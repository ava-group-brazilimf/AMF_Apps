# Contract: implementation-status.json Schema — Vue Frontend

**Feature**: `009-vue-frontend-agent`
**Agent**: `ava-stack-vue-frontend`
**Version**: 1.0.0
**Reuses schema from**: `specs/008-react-frontend-build-cycle/contracts/implementation-status-contract.md`
**Consumed by**: `ava-stack-orchestrator`, `build_summary_comprehensive.py` (F8)

---

## Output Path

```
projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json
```

## JSON Schema

The schema below extends the 008 schema with the optional `build_cycle_fallback` field
(specific to this agent's WARN+fallback behaviour on `pipeline_mode == "build-cycle"`).
All other fields are identical to the React agent's contract.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "ava-stack-vue-frontend/implementation-status",
  "title": "ImplementationStatus",
  "description": "Status output written by ava-stack-vue-frontend after scaffold generation",
  "type": "object",
  "required": [
    "agent",
    "version",
    "implementation",
    "build",
    "security_compliance",
    "bounded_contexts_scaffolded",
    "outputs_generated",
    "trace_id"
  ],
  "additionalProperties": false,
  "properties": {
    "agent": {
      "type": "string",
      "const": "ava-stack-vue-frontend"
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "SemVer agent version — must be '1.0.0'"
    },
    "implementation": {
      "type": "object",
      "required": ["status"],
      "additionalProperties": false,
      "properties": {
        "status": {
          "type": "string",
          "enum": ["COMPLETED", "BLOCKED", "PARTIAL"],
          "description": "COMPLETED = all BCs generated successfully; STUB is NEVER valid here"
        },
        "blocked_reason": {
          "type": "string",
          "description": "Human-readable explanation; present only when status == BLOCKED"
        }
      }
    },
    "build": {
      "type": "string",
      "enum": ["PASS", "FAIL", "TOOLCHAIN_UNAVAILABLE", "PENDING"],
      "description": "PENDING written by scaffold agent; updated by ava-stack-build-validator"
    },
    "security_compliance": {
      "type": "string",
      "enum": ["COMPLIANT", "PARTIAL", "NON_COMPLIANT", "SKIPPED"],
      "description": "SKIPPED when security-architecture.md is absent"
    },
    "security_compliance_report": {
      "type": "string",
      "description": "Relative path to SecurityComplianceReport-Frontend.md; present when not SKIPPED"
    },
    "build_cycle_fallback": {
      "type": "boolean",
      "description": "true if pipeline_mode was 'build-cycle' and agent fell back to generic mode"
    },
    "bounded_contexts_scaffolded": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "description": "Kebab-case names of BCs that were scaffolded"
    },
    "outputs_generated": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "description": "All generated file paths relative to output_root"
    },
    "trace_id": {
      "type": "string",
      "description": "UUID propagated from project-config.yaml unchanged"
    }
  }
}
```

## Example — Success (generic mode)

```json
{
  "agent": "ava-stack-vue-frontend",
  "version": "1.0.0",
  "implementation": { "status": "COMPLETED" },
  "build": "PENDING",
  "security_compliance": "COMPLIANT",
  "security_compliance_report": "projects/my-erp/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md",
  "bounded_contexts_scaffolded": ["financial-management", "accounts-payable"],
  "outputs_generated": [
    "projects/my-erp/outputs/tobe/source-code/frontend/package.json",
    "projects/my-erp/outputs/tobe/source-code/frontend/src/main.ts",
    "projects/my-erp/outputs/tobe/source-code/frontend/src/views/financial-management/FinancialManagementListView.vue"
  ],
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Example — build-cycle fallback (WARN, not BLOCKED)

```json
{
  "agent": "ava-stack-vue-frontend",
  "version": "1.0.0",
  "implementation": { "status": "COMPLETED" },
  "build": "PENDING",
  "security_compliance": "PARTIAL",
  "security_compliance_report": "projects/my-erp/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md",
  "build_cycle_fallback": true,
  "bounded_contexts_scaffolded": ["financial-management"],
  "outputs_generated": ["..."],
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Invariants

| Rule                               | Description                                                                             |
| ---------------------------------- | --------------------------------------------------------------------------------------- |
| `implementation.status` ≠ `"STUB"` | `STUB` is not a valid enum value — this enforces the complete removal of stub behaviour |
| `outputs_generated` non-empty      | Agent MUST NOT report COMPLETED with zero artifacts                                     |
| `trace_id` matches input           | Value copied verbatim from `project-config.yaml → trace_id`                             |
| `build` starts as `PENDING`        | Only `ava-stack-build-validator` sets `PASS` / `FAIL`                                   |
