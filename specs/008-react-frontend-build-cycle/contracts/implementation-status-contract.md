# Contract: implementation-status.json Schema

**Feature**: `008-react-frontend-build-cycle`
**Agent**: `ava-build-cycle-react-scaffold`
**Version**: 1.0.0
**Consumed by**: `ava-stack-orchestrator`, `build_summary_comprehensive.py` (F8)

---

## Output Path

```
projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json
```

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "ava-build-cycle-react-scaffold/implementation-status",
  "title": "ImplementationStatus",
  "description": "Status output written by ava-build-cycle-react-scaffold after scaffold generation",
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
      "const": "ava-build-cycle-react-scaffold"
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "SemVer agent version"
    },
    "implementation": {
      "type": "object",
      "required": ["status"],
      "additionalProperties": false,
      "properties": {
        "status": {
          "type": "string",
          "enum": ["COMPLETED", "BLOCKED", "PARTIAL"]
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
      "description": "PENDING written by scaffold agent; updated to final status by ava-stack-build-validator"
    },
    "security_compliance": {
      "type": "string",
      "enum": ["PASS", "FAIL", "SKIPPED"]
    },
    "security_findings": {
      "type": "object",
      "description": "Present only when security_compliance == FAIL",
      "required": ["level", "count", "packages"],
      "additionalProperties": false,
      "properties": {
        "level": {
          "type": "string",
          "enum": ["critical", "high", "medium", "low"]
        },
        "count": {
          "type": "integer",
          "minimum": 0
        },
        "packages": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "bounded_contexts_scaffolded": {
      "type": "array",
      "items": { "type": "string" },
      "description": "BC names scaffolded in full mode"
    },
    "bounded_contexts_minimal": {
      "type": "array",
      "items": { "type": "string" },
      "description": "BC names scaffolded in minimal mode (no UI screens)"
    },
    "outputs_generated": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Relative file paths from outputs/tobe/source-code/frontend/"
    },
    "trace_id": {
      "type": "string",
      "format": "uuid",
      "description": "Propagated unchanged from AgentTask.trace_id"
    }
  }
}
```

## Example (COMPLETED)

```json
{
  "agent": "ava-build-cycle-react-scaffold",
  "version": "1.0.0",
  "implementation": {
    "status": "COMPLETED"
  },
  "build": "PENDING",
  "security_compliance": "PASS",
  "bounded_contexts_scaffolded": ["financial-management", "customer-registry"],
  "bounded_contexts_minimal": ["integration-gateway"],
  "outputs_generated": [
    "package.json",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.node.json",
    "index.html",
    ".env.example",
    "src/main.tsx",
    "src/App.tsx",
    "src/router/index.tsx",
    "src/auth/msal-config.ts",
    "src/auth/AuthGuard.tsx",
    "src/shared/components/Button.tsx",
    "src/shared/api/index.ts",
    "src/financial-management/domain/types.ts",
    "src/financial-management/application/services/FinancialService.ts",
    "src/financial-management/infrastructure/api/financialApi.ts",
    "src/financial-management/ui/pages/InvoiceListPage.tsx",
    "src/financial-management/tests/unit/InvoiceListPage.test.tsx",
    "src/customer-registry/domain/types.ts",
    "src/customer-registry/ui/pages/CustomerListPage.tsx",
    "src/integration-gateway/ui/index.tsx",
    "scaffold-manifest.json",
    "implementation-status.json"
  ],
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Example (BLOCKED)

```json
{
  "agent": "ava-build-cycle-react-scaffold",
  "version": "1.0.0",
  "implementation": {
    "status": "BLOCKED",
    "blocked_reason": "architecture-blueprint.md não encontrado em outputs/tobe/docs/. Execute @ava-tobe-architecture-design antes de continuar."
  },
  "build": "PENDING",
  "security_compliance": "SKIPPED",
  "bounded_contexts_scaffolded": [],
  "bounded_contexts_minimal": [],
  "outputs_generated": [],
  "trace_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

---

## Compatibility Notes

- `build_summary_comprehensive.py` reads `implementation.status` and `build` fields
  to determine the F3 frontend status row in the summary HTML.
- The `build` field MUST start as `"PENDING"` and be updated by `ava-stack-build-validator`.
  If `ava-stack-build-validator` is skipped (TOOLCHAIN_UNAVAILABLE), the build-validator
  writes `"TOOLCHAIN_UNAVAILABLE"`.
- This schema is compatible with the Python scaffold's `implementation-status.json`
  (same field names, same enum values) — `build_summary_comprehensive.py` does not
  need changes.
