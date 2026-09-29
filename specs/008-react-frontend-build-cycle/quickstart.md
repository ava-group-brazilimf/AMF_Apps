# Quickstart Validation Guide: ava-stack-react-frontend (Build Cycle Mode)

**Feature**: `008-react-frontend-build-cycle`
**Date**: 2026-07-13

This guide describes how to validate the implemented agents end-to-end.
It covers prerequisites, setup, invocation, and expected outcomes — not implementation details.

---

## Prerequisites

| #   | Requirement                                                                 | Verify With                                       |
| --- | --------------------------------------------------------------------------- | ------------------------------------------------- |
| 1   | AVA Fabric agents workspace checked out                                     | `git status`                                      |
| 2   | A project with `project-config.yaml` configured                             | See project setup below                           |
| 3   | F2 artifacts exist: `architecture-blueprint.md`, `security-architecture.md` | `dir outputs\tobe\docs\`                          |
| 4   | Wave 1 readiness gate approved                                              | `readiness-gate-status.json → status: "APPROVED"` |
| 5   | Node.js LTS + npm installed (for build validation)                          | `node -v && npm -v`                               |

---

## Project Setup (Minimal Validation Config)

Create or use an existing project directory:

```
projects/test-react-frontend/
└── context/
    ├── project-config.yaml
    └── agent-task-config.yaml
```

Minimal `project-config.yaml` for this validation:

```yaml
project_name: "test-react-frontend"
pipeline_mode: "build-cycle"
tobe_stack:
  frontend_framework: "react"
  frontend_version: "18"
  package_manager: "npm"
  ui_library: "shadcn"
auth:
  provider: "azure-ad"
architecture_patterns:
  cqrs: false
```

Stub F2 artifacts (minimum viable for gate to pass):

```
projects/test-react-frontend/outputs/
├── tobe/docs/
│   ├── architecture-blueprint.md    ← must list at least 1 bounded context
│   └── security-architecture.md    ← must be non-empty
└── readiness-gate/wave-1/
    └── readiness-gate-status.json  ← {"status": "APPROVED"}
```

Minimum `architecture-blueprint.md` excerpt for BC extraction:

```markdown
## Bounded Contexts

### BC-01: Financial Management

- **Name**: financial-management
- **UI Screens**: Invoice List, Invoice Detail, Payment Form

### BC-02: Customer Registry

- **Name**: customer-registry
- **UI Screens**: Customer List, Customer Profile
```

---

## Validation Scenario 1 — Build-Cycle Scaffold (Nominal)

### Invocation

```
@ava-build-cycle-react-scaffold
```

Or via orchestrator (normal pipeline path):

```
@ava-stack-orchestrator
```

_(Orchestrator reads `pipeline_mode == "build-cycle"` and `frontend_framework == "react"`,
dispatches `ava-build-cycle-react-scaffold` automatically.)_

### Expected Outcomes

1. **Pre-flight box** emitted showing all inputs ✅ and F2 gate `PROCEED`
2. Agent creates directory structure at `outputs/tobe/source-code/frontend/`
3. Files present at minimum:
   - `package.json` (contains `react`, `@azure/msal-react`, `react-router-dom`, `zustand`, `@tanstack/react-query`)
   - `vite.config.ts`
   - `tsconfig.json` (with `"strict": true`)
   - `src/main.tsx`, `src/App.tsx`, `src/router/index.tsx`
   - `src/auth/msal-config.ts` (MSAL for azure-ad)
   - `src/financial-management/` — full 5-layer structure
   - `src/customer-registry/` — full 5-layer structure
   - `.env.example` — contains `VITE_AZURE_AD_CLIENT_ID`, `VITE_AZURE_AD_AUTHORITY`, `VITE_API_BASE_URL`
4. `implementation-status.json` contains `"status": "COMPLETED"`, `"build": "PENDING"`
5. `scaffold-manifest.json` lists all BCs and generated file count

See [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md) for exact JSON format.

---

## Validation Scenario 2 — Build Validation (Toolchain Available)

After scaffold generation, invoke build validator:

```
@ava-stack-build-validator
```

### Expected Outcomes

1. `npm install` runs without error
2. `tsc --noEmit` exits 0 (no TypeScript errors)
3. `npm run build` exits 0 (Vite build succeeds)
4. `implementation-status.json` updated: `"build": "PASS"`

---

## Validation Scenario 3 — Generic Mode Guard

Modify `project-config.yaml` to set `pipeline_mode: "generic"` (or remove it), then invoke:

```
@ava-stack-react-frontend
```

### Expected Outcomes

1. Agent does NOT emit a redirect message (it proceeds with generic generation)
2. Outputs are written to `outputs/tobe/source-code/frontend/`
3. `implementation.status: COMPLETED` in output

_Then test the guard the other way: keep `pipeline_mode: "build-cycle"` and invoke `@ava-stack-react-frontend`._

### Expected Outcomes (build-cycle guard)

1. Agent emits redirect box pointing to `@ava-build-cycle-react-scaffold`
2. Agent exits without generating any files
3. No files written to `outputs/tobe/source-code/frontend/`

---

## Validation Scenario 4 — Missing F2 Gate (Blocked)

Remove `readiness-gate-status.json` (or set `status: "PENDING"`), then invoke:

```
@ava-build-cycle-react-scaffold
```

### Expected Outcomes

1. F2 gate check emits `⛔ BLOCKED`
2. `implementation-status.json` written with `"status": "BLOCKED"` and `blocked_reason` set
3. No scaffold files written (only the status JSON)

---

## Validation Scenario 5 — BC Without UI (Minimal Scaffold)

Add a BC with no screens to `architecture-blueprint.md`:

```markdown
### BC-03: Integration Gateway

- **Name**: integration-gateway
- **UI Screens**: _(none — integration-only BC)_
```

### Expected Outcomes

1. `src/integration-gateway/ui/index.tsx` exists with placeholder comment
2. `implementation-status.json → bounded_contexts_minimal` contains `"integration-gateway"`
3. `implementation.status` is still `"COMPLETED"` (not PARTIAL)
4. `scaffold-manifest.json → bounded_contexts[2].scaffold_mode` is `"minimal"`

---

## Validation Scenario 6 — Stub Registry and Orchestrator Routing

Check that `stub-registry.yaml` shows COMPLETE for both entries:

```bash
grep -A 5 "coder-react-frontend" src/shared/data/stub-registry.yaml
grep -A 5 "build-cycle-react-scaffold" src/shared/data/stub-registry.yaml
```

Expected: both entries have `status: COMPLETE`.

Check orchestrator routing table:

```bash
grep -A 2 "react" src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md
```

Expected: `react` row shows `✅ Implemented` for both generic and build-cycle rows.

---

## Validation Checklist

| #   | Check                            | Pass Criterion                                                        |
| --- | -------------------------------- | --------------------------------------------------------------------- |
| 1   | Scaffold generated for all BCs   | All `src/{bc_name}/` directories exist                                |
| 2   | Full scaffold has 5 layers       | `domain/`, `application/`, `infrastructure/`, `ui/`, `tests/` present |
| 3   | Minimal BC has placeholder only  | `src/{bc_name}/ui/index.tsx` with comment                             |
| 4   | No hardcoded credentials         | `grep -r "clientId\s*=" src/auth/` shows only env var references      |
| 5   | implementation-status.json valid | Matches schema in `contracts/implementation-status-contract.md`       |
| 6   | build-cycle guard works          | Redirect emitted when `pipeline_mode == "build-cycle"` in coder agent |
| 7   | Generic guard works              | No redirect when `pipeline_mode == "generic"`                         |
| 8   | F2 gate blocks                   | BLOCKED when `readiness-gate-status.json` missing                     |
| 9   | stub-registry COMPLETE           | Both entries updated                                                  |
| 10  | SKILL.md created                 | `.github/skills/ava-stack-react-frontend/SKILL.md` exists             |
