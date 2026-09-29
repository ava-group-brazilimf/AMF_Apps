# Research: ava-stack-react-frontend (Build Cycle Mode)

**Feature**: `008-react-frontend-build-cycle`
**Phase**: 0 — Outline & Research
**Date**: 2026-07-13

---

## §1 — Bundler: Vite vs. Next.js

**Decision**: Vite 5 (SPA default)

**Rationale**: The build-cycle pipeline targets migrating legacy monoliths into
APIs + SPAs hosted in Azure Container Apps. Server-Side Rendering (SSR) is not
in scope for the AS-IS migration target. Next.js App Router adds significant
infrastructure complexity (edge functions, streaming, server components) with no
benefit for the legacy-migration use case. Vite delivers faster builds, simpler
config, and native ESM — consistent with the `build-cycle-python-scaffold` philosophy
of minimal-footprint scaffolding.

**Next.js activation path**: reserved for `tobe_stack.rendering_mode == "ssr"` config
key (future spec). Default (absent or `"spa"`) → Vite.

**Alternatives considered**:

- Next.js App Router — rejected: SSR complexity unnecessary for migration SPA
- Create React App — rejected: deprecated, no active maintenance
- Parcel — rejected: limited TypeScript strict support

---

## §2 — State Management: Zustand vs. TanStack Query vs. Redux Toolkit

**Decision**: Zustand (client state) + TanStack Query (server/async state) — two-library pattern

**Rationale**: Modern React 18 projects overwhelmingly prefer:

- **TanStack Query v5** for server state (API calls, caching, pagination) — eliminates
  `useEffect`+`useState` data-fetching boilerplate
- **Zustand** for UI/client state (modals, selected items, user preferences) — minimal API,
  no boilerplate, React-idiomatic

Redux Toolkit is heavier and better suited to teams already using Redux. For a scaffold
starting from zero, Zustand + TanStack Query has better DX and less ceremony.

When `architecture_patterns.cqrs == true`, the scaffold generates Zustand store slices
named `*Commands` (write) and React Query queries named `*Queries` (read), mirroring CQRS.

**Alternatives considered**:

- Redux Toolkit — rejected: boilerplate-heavy for greenfield builds
- MobX — rejected: non-mainstream, harder onboarding for legacy Delphi teams
- TanStack Query alone — rejected: still needs something for UI-only state

---

## §3 — Authentication: MSAL React vs. Auth0

**Decision**: `@azure/msal-react` by default (`auth.provider == "azure-ad"`), with
conditional branch for `"auth0"` (uses `@auth0/auth0-react`)

**Rationale**: The canonical AVA Fabric reference architecture uses Azure AD B2C
(`reference-architecture.yaml → security.identity`). MSAL React is the Microsoft-provided
SDK with first-class Azure AD integration. The same SDK pattern used by `build-cycle-angular-agent.md`
is replicated here for React.

Auth pattern:

- `MsalProvider` wraps `<App />`
- `useIsAuthenticated()` hook gates protected routes
- `useMsal()` provides `acquireTokenSilent` for API calls
- `AuthenticatedTemplate` / `UnauthenticatedTemplate` for conditional rendering

**Alternatives considered**:

- Passport.js — rejected: server-side library, not applicable to SPA
- Firebase Auth — not in AVA Fabric reference; would require new config keys

---

## §4 — UI Component Library

**Decision**: Resolved at runtime from `tobe_stack.ui_library` (Article I — no hardcoding)

Default fallback order (when `ui_library` is absent):

1. `shadcn` (Radix UI + Tailwind CSS) — modern, accessible, copy-paste components
2. `mui` (Material UI v6) — enterprise-grade, opinionated

The scaffold generates a `src/shared/components/` directory with placeholder primitives
(`Button.tsx`, `Input.tsx`, `Table.tsx`, `Modal.tsx`) regardless of UI library choice.
Library-specific imports are injected based on the resolved config value.

---

## §5 — Testing: Vitest + React Testing Library

**Decision**: Vitest 1.x + React Testing Library 14.x + jsdom

**Rationale**: Vitest is the natural testing companion to Vite — same config, instant
hot reload, compatible with Jest API (no migration effort). React Testing Library enforces
user-centric testing, reducing test fragility.

E2E tests are out of scope for the scaffold (handled by `ava-qa-script-generator`).
Integration test setup uses `msw` (Mock Service Worker) for API mocking.

Test structure per BC:

```
{bc_name}/tests/
├── unit/         # Component + hook tests (React Testing Library)
└── integration/  # API integration tests (msw + TanStack Query)
```

---

## §6 — Build Validator Compatibility

**Decision**: The `ava-stack-build-validator` uses the **Vite Pipeline** (VF0–VF6 gates)
for React — identical to the Svelte/Vue path described in `jsts-research-instructions.md`
and `build-validator-agent.md`.

Validation sequence:

1. `npm install` (or `pnpm install` if `package_manager == "pnpm"`)
2. `npx tsc --noEmit` (TypeScript strict check)
3. `npm run build` (Vite build)
4. `npm run lint` (ESLint flat config)
5. `npm audit --audit-level=high` (security gate)

The scaffold must generate a `package.json` with `build`, `lint`, and `test` scripts
to be compatible with the build validator.

---

## §7 — Routing: React Router v6 (Data API)

**Decision**: React Router v6 with Data API (createBrowserRouter)

**Rationale**: React Router v6 Data API provides loader functions for per-route data
fetching — reduces TanStack Query usage for simple cases and integrates with lazy()
for code splitting. Lazy-loaded routes (`React.lazy`) are the default for all BC modules.

Route guard pattern: `<AuthGuard>` component wraps all authenticated routes, calling
`useIsAuthenticated()` from MSAL.

---

## §8 — OpenAPI TypeScript Client

**Decision**: Stub pattern — scaffold generates a `src/shared/api/` directory with
placeholder client; real generation is deferred to `ava-docs-tobe` (OpenAPI spec generation).

The scaffold generates:

```typescript
// src/shared/api/index.ts — stub to be replaced
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
// Real client generated by ava-docs-tobe → openapi-typescript
```

---

## §9 — Routing Guard Compatibility with `coder-react-frontend.md`

**Decision**: `coder-react-frontend.md` (v1.0.0) uses the same routing guard pattern
as `coder-angular-frontend.md`:

```
SE pipeline_mode == "build-cycle":
  → emit redirect message pointing to @ava-build-cycle-react-scaffold
  → stop, do not generate artifacts

SE pipeline_mode == "generic" OU ausente:
  → execute full generic generation
```

This clean separation avoids any dual-path complexity in the coder agent.

---

## §10 — Orchestrator-Stack Routing Table Update

**Decision**: Add two rows to `orchestrator-stack.md` frontend routing table:

| `tobe_stack.frontend_framework` | Agent                            | Status         |
| ------------------------------- | -------------------------------- | -------------- |
| `react` (generic mode)          | `ava-stack-react-frontend`       | ✅ Implemented |
| `react` (build-cycle mode)      | `ava-build-cycle-react-scaffold` | ✅ Implemented |

Routing condition in Step 0.3b:

```
IF frontend_framework == "react" AND pipeline_mode == "build-cycle":
  dispatch ava-build-cycle-react-scaffold
ELIF frontend_framework == "react":
  dispatch ava-stack-react-frontend (generic)
```

---

## §11 — SKILL.md Pattern

**Decision**: New `.github/skills/ava-stack-react-frontend/SKILL.md` following
`.github/skills/ava-stack-angular-frontend/SKILL.md` exactly:

1. Reads `project_name` from `project-config.yaml`
2. Reads `agent-task-config.yaml` + `shared-context.md`
3. Delegates to `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`

`ava-build-cycle-react-scaffold` has NO SKILL.md (internal-only, Article XI).

---

## §12 — CQRS Mode in React Scaffold

**Decision**: CQRS flag (`architecture_patterns.cqrs`) affects the Application layer
structure per BC, mirroring the Python scaffold pattern:

| `cqrs: true`            | `cqrs: false`           |
| ----------------------- | ----------------------- |
| `application/commands/` | `application/services/` |
| `application/queries/`  | `application/hooks/`    |
| `application/handlers/` | `application/dtos/`     |

Zustand store structure also adapts:

- `cqrs: true` → separate `{bc}CommandStore.ts` (mutations) + React Query hooks (reads)
- `cqrs: false` → combined `{bc}Store.ts` (state + queries)

---

## Summary of All Decisions

| #   | Topic        | Decision                                           | Rationale Key                                  |
| --- | ------------ | -------------------------------------------------- | ---------------------------------------------- |
| 1   | Bundler      | Vite 5 (SPA)                                       | Simpler, faster, aligned with migration target |
| 2   | State        | Zustand + TanStack Query v5                        | Best DX, minimal boilerplate                   |
| 3   | Auth         | MSAL React (`azure-ad`) / conditional Auth0        | Reference architecture standard                |
| 4   | UI Lib       | Runtime from `tobe_stack.ui_library`               | Article I — no hardcoding                      |
| 5   | Testing      | Vitest + RTL + msw                                 | Native Vite companion                          |
| 6   | Build gate   | Vite Pipeline (VF0–VF6)                            | Compatible with build-validator-agent.md       |
| 7   | Routing      | React Router v6 Data API + lazy()                  | Code splitting per BC                          |
| 8   | API client   | Stub pattern → deferred to ava-docs-tobe           | Avoids premature coupling                      |
| 9   | Coder guard  | Same pattern as Angular: redirect in build-cycle   | Separation of concerns                         |
| 10  | Orchestrator | Two routing rows for react (generic + build-cycle) | Explicit routing                               |
| 11  | SKILL.md     | Created for coder; absent for build-cycle template | Article XI compliance                          |
| 12  | CQRS         | Application layer adapts, Zustand store adapts     | Mirrors Python scaffold                        |
