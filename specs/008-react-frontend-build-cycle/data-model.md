# Data Model: ava-stack-react-frontend (Build Cycle Mode)

**Feature**: `008-react-frontend-build-cycle`
**Phase**: 1 — Design & Contracts
**Date**: 2026-07-13

---

## Overview

This feature involves LLM prompt agents (`.md` instruction files), not compiled code.
The "entities" described here are the **scaffolding domain objects** that the agents
reason about and produce — they exist as directory structures and JSON manifests, not
as database rows or class hierarchies.

---

## Entity 1 — `ReactProject` (Root Scaffold)

Represents the top-level React frontend project generated for a given project.

| Field              | Type                                      | Source                                              | Notes                                       |
| ------------------ | ----------------------------------------- | --------------------------------------------------- | ------------------------------------------- |
| `project_name`     | `string`                                  | `project-config.yaml`                               | Kebab-case, e.g. `my-erp`                   |
| `frontend_version` | `string`                                  | `project-config.yaml → tobe_stack.frontend_version` | React major version, e.g. `"18"`            |
| `bundler`          | `"vite"` \| `"nextjs"`                    | `project-config.yaml → tobe_stack.rendering_mode`   | `"spa"` → Vite (default); `"ssr"` → Next.js |
| `package_manager`  | `"npm"` \| `"pnpm"` \| `"yarn"`           | `project-config.yaml → tobe_stack.package_manager`  | Default: `"npm"`                            |
| `ui_library`       | `string`                                  | `project-config.yaml → tobe_stack.ui_library`       | e.g. `"shadcn"`, `"mui"`                    |
| `auth_provider`    | `"azure-ad"` \| `"auth0"` \| `"keycloak"` | `project-config.yaml → auth.provider`               | Default: `"azure-ad"`                       |
| `cqrs`             | `boolean`                                 | `project-config.yaml → architecture_patterns.cqrs`  | Affects Application layer structure         |
| `bounded_contexts` | `BoundedContextModule[]`                  | Extracted from `architecture-blueprint.md`          | One module per BC                           |

**Output Path**: `projects/{project_name}/outputs/tobe/source-code/frontend/`

**Validation Rules**:

- `frontend_version` must be a non-empty string
- `bounded_contexts` must contain at least 1 entry
- If `auth_provider` is absent, default to `"azure-ad"` (do not error)

---

## Entity 2 — `BoundedContextModule`

Represents one bounded context's frontend module within the React project.

| Field           | Type                    | Source                                     | Notes                                              |
| --------------- | ----------------------- | ------------------------------------------ | -------------------------------------------------- |
| `name`          | `string`                | Extracted from `architecture-blueprint.md` | Kebab-case, e.g. `"financial-management"`          |
| `display_name`  | `string`                | Extracted from blueprint                   | Human-readable BC name                             |
| `has_ui`        | `boolean`               | Inferred from blueprint                    | `false` if BC is integration-only (no screens)     |
| `routes`        | `RouteDefinition[]`     | Extracted from blueprint or empty          | Screen routes for this BC                          |
| `scaffold_mode` | `"full"` \| `"minimal"` | Derived from `has_ui`                      | `has_ui == false` → `"minimal"` (placeholder only) |

**Validation Rules**:

- If `has_ui == false`, scaffold in `minimal` mode (placeholder `index.tsx` only)
- `name` must be a valid directory name (no spaces, no uppercase)
- At least one BC in the project must have `has_ui == true`

**State Transitions**:

```
NOT_STARTED → SCAFFOLDING → SCAFFOLD_COMPLETE → BUILD_VALIDATED
                ↓ (on error)
              SCAFFOLD_FAILED
```

---

## Entity 3 — `RouteDefinition`

Represents one navigable screen/page within a bounded context.

| Field            | Type      | Notes                                             |
| ---------------- | --------- | ------------------------------------------------- |
| `path`           | `string`  | URL path segment, e.g. `"/financial/invoices"`    |
| `component_name` | `string`  | PascalCase, e.g. `"InvoiceListPage"`              |
| `lazy`           | `boolean` | Always `true` (all routes are lazy-loaded)        |
| `auth_required`  | `boolean` | Always `true` (all routes require authentication) |

---

## Entity 4 — `AuthConfig`

Configuration entity for authentication setup.

| Field                  | Type                                      | Source                                | Notes                                 |
| ---------------------- | ----------------------------------------- | ------------------------------------- | ------------------------------------- |
| `provider`             | `"azure-ad"` \| `"auth0"` \| `"keycloak"` | `project-config.yaml → auth.provider` |                                       |
| `client_id_env_key`    | `string`                                  | Derived                               | e.g. `VITE_AZURE_AD_CLIENT_ID`        |
| `authority_env_key`    | `string`                                  | Derived                               | e.g. `VITE_AZURE_AD_AUTHORITY`        |
| `redirect_uri_env_key` | `string`                                  | Derived                               | e.g. `VITE_REDIRECT_URI`              |
| `config_file`          | `string`                                  | Derived from `provider`               | `msal-config.ts` or `auth0-config.ts` |

**Invariants**:

- All auth values are env-var references (`.env.example`) — never hardcoded literals
- `VITE_` prefix required for Vite env exposure

---

## Entity 5 — `ScaffoldManifest`

JSON artifact written at `scaffold-manifest.json`, consumed by downstream agents
(build-validator, ava-summary) for validation and reporting.

```typescript
interface ScaffoldManifest {
  agent: "ava-build-cycle-react-scaffold";
  version: string; // agent version, e.g. "1.0.0"
  generated_at: string; // ISO 8601
  project_name: string;
  frontend_version: string;
  bundler: "vite" | "nextjs";
  package_manager: "npm" | "pnpm" | "yarn";
  auth_provider: string;
  cqrs: boolean;
  bounded_contexts: {
    name: string;
    scaffold_mode: "full" | "minimal";
    files_generated: string[]; // relative paths from frontend/
  }[];
  total_files_generated: number;
}
```

---

## Entity 6 — `ImplementationStatus`

JSON artifact written at `implementation-status.json`, consumed by:

- `build_summary_comprehensive.py` (F8 summary)
- `ava-stack-orchestrator` (handoff signal)

```typescript
interface ImplementationStatus {
  agent: "ava-build-cycle-react-scaffold";
  version: string;
  implementation: {
    status: "COMPLETED" | "BLOCKED" | "PARTIAL";
    blocked_reason?: string; // present only when status == "BLOCKED"
  };
  build: "PASS" | "FAIL" | "TOOLCHAIN_UNAVAILABLE" | "PENDING";
  security_compliance: "PASS" | "FAIL" | "SKIPPED";
  security_findings?: {
    level: "critical" | "high" | "medium" | "low";
    count: number;
    packages: string[];
  };
  bounded_contexts_scaffolded: string[];
  bounded_contexts_minimal: string[]; // BCs scaffolded in minimal mode
  outputs_generated: string[]; // relative paths from frontend/
  trace_id: string; // UUID, propagated from AgentTask.trace_id
}
```

**Constraint**: `build` field must be updated by `ava-stack-build-validator`, NOT by
this scaffold agent. The scaffold agent writes `"PENDING"` and the build-validator
overwrites it with `"PASS"` | `"FAIL"` | `"TOOLCHAIN_UNAVAILABLE"`.

---

## Entity 7 — `AgentRoutingDecision` (orchestrator-stack.md)

Internal model used by `ava-stack-orchestrator` for frontend agent dispatch.

| Condition                                                              | Dispatched Agent                                   |
| ---------------------------------------------------------------------- | -------------------------------------------------- |
| `frontend_framework == "react"` AND `pipeline_mode == "build-cycle"`   | `ava-build-cycle-react-scaffold`                   |
| `frontend_framework == "react"` AND `pipeline_mode != "build-cycle"`   | `ava-stack-react-frontend` (generic)               |
| `frontend_framework == "angular"` AND `pipeline_mode == "build-cycle"` | `ava-build-cycle-angular` → `ava-build-cycle-ngrx` |
| `frontend_framework == "angular"` AND `pipeline_mode != "build-cycle"` | `ava-stack-angular-frontend` (generic)             |

---

## State Transitions for Scaffold Execution

```
INIT
 │
 ├─→ [routing guard check] ──(fail)──→ ABORTED (wrong routing keys)
 │
 ├─→ [F2 gate check] ──(fail)──→ BLOCKED (missing artifacts)
 │
 ├─→ [BC extraction from blueprint]
 │
 ├─→ [per-BC scaffold: full or minimal]
 │         │
 │         ├─→ SCAFFOLD_COMPLETE
 │         └─→ SCAFFOLD_FAILED (I/O error)
 │
 ├─→ [npm install + npm audit]
 │
 └─→ [write scaffold-manifest.json + implementation-status.json]
       │
       ├─→ build: "PENDING" (awaits build-validator)
       └─→ COMPLETED
```
