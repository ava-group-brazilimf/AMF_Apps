# Data Model: ava-stack-vue-frontend

**Feature**: `009-vue-frontend-agent`
**Phase**: 1 — Design & Contracts
**Date**: 2026-07-13

---

## Overview

This feature upgrades an LLM prompt agent (`.md` instruction file) from stub to full
implementation. The "entities" described here are the **scaffolding domain objects** that
the agent reasons about and produces — they exist as directory structures, Vue SFC files,
and JSON manifests. No database rows or class hierarchies are involved in the agent itself.

---

## Entity 1 — `VueProject` (Root Scaffold)

Represents the top-level Vue 3 frontend project generated for a given project.

| Field              | Type                                                    | Source                                              | Notes                                        |
| ------------------ | ------------------------------------------------------- | --------------------------------------------------- | -------------------------------------------- |
| `project_name`     | `string`                                                | `project-config.yaml → project_name`                | Kebab-case, e.g. `my-erp`                    |
| `frontend_version` | `string`                                                | `project-config.yaml → tobe_stack.frontend_version` | Vue major version, e.g. `"3"`                |
| `auth_provider`    | `"azure-ad"` \| `"auth0"` \| `string`                   | `project-config.yaml → auth.provider`               | Default `"azure-ad"` if absent               |
| `ui_library`       | `"vuetify"` \| `"primevue"` \| `"naive-ui"` \| `string` | `project-config.yaml → tobe_stack.ui_library`       | Default: none (plain CSS)                    |
| `pipeline_mode`    | `"generic"` \| `"build-cycle"`                          | `project-config.yaml → pipeline_mode`               | `"build-cycle"` triggers WARN+fallback       |
| `package_manager`  | `"npm"` \| `"pnpm"` \| `"yarn"`                         | `project-config.yaml → tobe_stack.package_manager`  | Default `"npm"`                              |
| `bounded_contexts` | `BoundedContextModule[]`                                | Extracted from `bounded-context-map.md` / task      | At least 1 required                          |
| `trace_id`         | `string`                                                | `project-config.yaml → trace_id`                    | UUID; propagated unchanged to all outputs    |
| `language`         | `"pt"` \| `"en"` \| `"es"`                              | `project-config.yaml → language`                    | Controls UI label language in generated code |

**Validation Rules**:

- `frontend_version` must be non-empty and start with `"3"` (Vue 3.x)
- `bounded_contexts` must contain at least 1 entry
- If `auth_provider` is absent, default to `"azure-ad"` (do not error)
- If `pipeline_mode` is absent, treat as `"generic"`
- All secrets (Client ID, Tenant ID, redirect URI) must be in `import.meta.env.VITE_*` — never hardcoded

**Output Root**: `projects/{project_name}/outputs/tobe/source-code/frontend/`

---

## Entity 2 — `BoundedContextModule`

Represents one bounded context's frontend module within the Vue project.

| Field             | Type      | Source                                  | Notes                                        |
| ----------------- | --------- | --------------------------------------- | -------------------------------------------- |
| `name`            | `string`  | Extracted from `bounded-context-map.md` | Kebab-case, e.g. `"financial-management"`    |
| `display_name`    | `string`  | Extracted from bounded-context-map      | Human-readable, used in nav and route titles |
| `route_path`      | `string`  | Derived: `"/{name}"`                    | Vue Router route path                        |
| `has_list_view`   | `boolean` | Inferred from BC entity list            | Generates `{BCName}ListView.vue` if true     |
| `has_detail_view` | `boolean` | Inferred from BC entity attributes      | Generates `{BCName}DetailView.vue` if true   |

**File structure per BC** (generated under `src/views/{bc-kebab}/` and `src/stores/`):

```
src/
├── views/{bc-kebab}/
│   ├── {BCName}ListView.vue      ← list with v-for :key, loading/empty/error states
│   └── {BCName}DetailView.vue    ← detail/form with Pinia dispatch
├── stores/
│   └── {bc-kebab}.store.ts       ← Pinia store (state + actions + getters)
├── composables/
│   └── use{BCName}.ts            ← optional: encapsulates store + API calls
└── tests/
    ├── {bc-kebab}.store.spec.ts
    └── {BCName}View.spec.ts
```

---

## Entity 3 — `PiniaStore` (per BC)

Represents one Pinia store module generated for a bounded context.

| Field     | Type     | Notes                                                       |
| --------- | -------- | ----------------------------------------------------------- |
| `id`      | `string` | Pinia store ID: `"{bc-kebab}-store"`                        |
| `state`   | object   | BC entity collection + loading + error flags                |
| `getters` | object   | Derived/filtered views of state                             |
| `actions` | object   | Async fetch/create/update/delete methods calling API client |

**Pattern** (generated code):

```ts
// src/stores/{bc-kebab}.store.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { {BCEntity} } from '@/models/{bc-kebab}.model'

export const use{BCName}Store = defineStore('{bc-kebab}-store', () => {
  const items = ref<{BCEntity}[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchAll = async () => { ... }
  const create = async (payload: Create{BCEntity}Dto) => { ... }

  return { items, loading, error, fetchAll, create }
})
```

---

## Entity 4 — `ImplementationStatusReport`

The JSON artifact written at execution end, read by `ava-stack-orchestrator` and F8 summary.

| Field                         | Type       | Value / Source                                                     |
| ----------------------------- | ---------- | ------------------------------------------------------------------ |
| `agent`                       | `string`   | `"ava-stack-vue-frontend"` (const)                                 |
| `version`                     | `string`   | `"1.0.0"` (agent version)                                          |
| `implementation.status`       | `string`   | `"COMPLETED"` on success; `"BLOCKED"` or `"PARTIAL"` on failure    |
| `build`                       | `string`   | `"PENDING"` (set by scaffold); updated by build-validator          |
| `security_compliance`         | `string`   | `"COMPLIANT"` / `"PARTIAL"` / `"NON_COMPLIANT"` / `"SKIPPED"`      |
| `security_compliance_report`  | `string`   | Path to `SecurityComplianceReport-Frontend.md`                     |
| `build_cycle_fallback`        | `boolean?` | `true` if `pipeline_mode == "build-cycle"` triggered WARN+fallback |
| `bounded_contexts_scaffolded` | `string[]` | List of BC names that were processed                               |
| `outputs_generated`           | `string[]` | All generated file paths (relative to `output_root`)               |
| `trace_id`                    | `string`   | From `project-config.yaml → trace_id`; propagated unchanged        |

**Output path**: `projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json`

**Schema**: See [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md)

---

## Entity 5 — `ScaffoldFiles` (root project files)

These files are generated unconditionally as the root scaffolding:

| File                  | Purpose               | Notes                                                                          |
| --------------------- | --------------------- | ------------------------------------------------------------------------------ |
| `package.json`        | Project manifest      | vue, vite, pinia, vue-router, vitest, @vitejs/plugin-vue; versions from config |
| `vite.config.ts`      | Vite configuration    | `@vitejs/plugin-vue` plugin; path aliases `@/` → `src/`                        |
| `tsconfig.json`       | TypeScript config     | `strict: true`, `skipLibCheck: true`, `moduleResolution: "bundler"`            |
| `tsconfig.app.json`   | App-specific tsconfig | Extends `tsconfig.json`; includes `src/`                                       |
| `index.html`          | Vite entry point      | `<div id="app">`, title from `{project_title}`                                 |
| `src/main.ts`         | Vue application entry | Creates app, registers router + pinia + auth plugin                            |
| `src/App.vue`         | Root component        | `<RouterView />` + nav sidebar                                                 |
| `src/router/index.ts` | Vue Router 4 config   | All BC routes (lazy) + auth guard                                              |
| `src/plugins/auth.ts` | MSAL or Auth0 plugin  | Configured from `import.meta.env.VITE_*`                                       |
| `src/models/`         | TypeScript interfaces | One model file per BC entity                                                   |
| `src/api/`            | HTTP client modules   | Fetch/Axios wrappers per BC; no hardcoded URLs                                 |
| `.env.example`        | Environment template  | `VITE_MSAL_CLIENT_ID`, `VITE_MSAL_TENANT_ID`, `VITE_API_BASE_URL`              |

---

## State Transitions

```
Agent invoked
    │
    ▼
[Routing Guard] pipeline_mode == "build-cycle"?
    ├─ YES → emit ⚠️ WARN, set build_cycle_fallback=true, continue generic
    └─ NO  → continue generic
    │
    ▼
[PRE-FLIGHT] Read project-config.yaml, ConfigStackDotNet.yaml, bounded-context-map.md
    ├─ project_name missing  → ask user (SOFT STOP)
    ├─ frontend_version missing → HARD STOP
    └─ bounded-context-map.md missing → use task BC list (WARNING)
    │
    ▼
[SCAFFOLD] Generate root files → generate per-BC files (views, store, composable, tests)
    │
    ▼
[SECURITY GATE] Read security-architecture.md → classify controls → write SecurityComplianceReport
    ├─ security-architecture.md missing → security_compliance = "SKIPPED"
    └─ found → COMPLIANT / PARTIAL / NON_COMPLIANT
    │
    ▼
[CONSISTENCY CHECK] Verify all BCs have required files; no dangling imports
    │
    ▼
[HANDOFF] Write implementation-status.json → emit handoff block → return to ava-stack-orchestrator
    implementation.status = "COMPLETED"
```
