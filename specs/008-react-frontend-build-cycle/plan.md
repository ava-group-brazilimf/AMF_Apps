# Agent Implementation Plan: ava-stack-react-frontend (Build Cycle Mode)

**Branch**: `008-react-frontend-build-cycle` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-react-frontend-build-cycle/spec.md`

---

## Summary

| Field                   | Value                                                                                                                                                                                                                                                           |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent ID (1A)**       | `ava-stack-react-frontend` — modify-existing (v0.1.0-stub → v1.0.0)                                                                                                                                                                                             |
| **Agent ID (1B)**       | `ava-build-cycle-react-scaffold` — new internal agent (v1.0.0)                                                                                                                                                                                                  |
| **Phase**               | F3 (Tech Stack — codegen)                                                                                                                                                                                                                                       |
| **Module**              | `tech-stack`                                                                                                                                                                                                                                                    |
| **Primary Requirement** | Implement React 18 + Vite + TypeScript scaffold per bounded context in build-cycle mode, compatible with `build-cycle-python-scaffold` output contract.                                                                                                         |
| **Technical Approach**  | Upgrade `coder-react-frontend.md` from stub to full implementation with build-cycle redirect; create `build-cycle-react-scaffold.md` following `build-cycle-python-scaffold.md` patterns; create missing SKILL.md; update orchestrator routing + stub-registry. |
| **Change Type**         | `modify-existing` (1A) + new sub-agent (1B)                                                                                                                                                                                                                     |
| **Files changed**       | `coder-react-frontend.md`, `build-cycle-react-scaffold.md` (new), `SKILL.md` (new), `orchestrator-stack.md`, `stub-registry.yaml`, `module.yaml` (tech-stack), `CHANGELOG.md`                                                                                   |

---

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9)._

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded — all versions resolved from `project-config.yaml → tobe_stack.*` at runtime; `docs-researcher` fetches current versions pre-codegen.
- [x] **Article II** — Frontmatter contains ONLY `name`, `version`, `description`, `allowed-tools` — confirmed in spec §2A and §2B.
- [x] **Article II** — `ava-stack-react-frontend` ✅ and `ava-build-cycle-react-scaffold` ✅ match `^ava-[a-z0-9-]+$`.
- [x] **Article III** — F3 placement valid; `ava-stack-orchestrator` dispatches after F2 gate; `ava-summary` runs after F3.
- [x] **Article IV** — Module-level `module.yaml` diff prepared (see Plan section 5).
- [x] **Article V** — Agent body language is Brazilian Portuguese; SKILL.md also in pt-BR.
- [x] **Article VI** — BDD scenarios in spec §4: 4 scenarios covering nominal, absent gate, BC without UI, and routing guard.
- [x] **Article VII** — Security sub-pipeline impact: `npm audit --audit-level=high` embedded in scaffold. No F1 security sub-pipeline change.
- [x] **Article VIII** — `trace_id` propagated from `AgentTask.trace_id` → `implementation-status.json.trace_id` unchanged.
- [x] **Article IX** — N/A: LLM prompt files. Clean Architecture applies to generated React code artifacts, not to this agent's source.
- [x] **Article X** — 1A: **MAJOR** (0.1.0-stub → 1.0.0, stub→full, output contract changes). 1B: **v1.0.0** (new agent).
- [x] **Article XI** — `ava-stack-react-frontend`: user-facing, SKILL.md created at `.github/skills/ava-stack-react-frontend/SKILL.md`. `ava-build-cycle-react-scaffold`: internal-only (no SKILL.md), dispatched exclusively by `ava-stack-orchestrator`.

### Quality Gate Check

- [x] No [NEEDS CLARIFICATION] markers remain in spec
- [x] All outputs follow `projects/{project_name}/outputs/tobe/source-code/frontend/...`
- [x] Downstream `next_agent`: `ava-stack-build-validator` — confirmed to exist in `tech-stack/agents/build-validator-agent.md`

---

## 1. Technical Context

| Dimension          | Choice                                                        | Source                                                        |
| ------------------ | ------------------------------------------------------------- | ------------------------------------------------------------- |
| Agent type         | LLM prompt file (`.md`)                                       | N/A — not compiled                                            |
| Frontend framework | React 18                                                      | `project-config.yaml → tobe_stack.frontend_version` (runtime) |
| Bundler            | Vite 5 (SPA default)                                          | research.md §1; `"ssr"` mode → Next.js (future)               |
| State management   | Zustand + TanStack Query v5                                   | research.md §2                                                |
| Auth               | `@azure/msal-react` (azure-ad default) / `@auth0/auth0-react` | `project-config.yaml → auth.provider`                         |
| UI library         | From `tobe_stack.ui_library`                                  | Article I — resolved at runtime                               |
| Testing            | Vitest + React Testing Library + msw                          | research.md §5                                                |
| Build validation   | Vite Pipeline (VF0–VF6) in `build-validator-agent.md`         | research.md §6                                                |
| Routing            | React Router v6 Data API + `React.lazy()`                     | research.md §7                                                |
| API client         | Stub pattern → deferred to `ava-docs-tobe`                    | research.md §8                                                |
| CQRS               | Application layer adapts from `architecture_patterns.cqrs`    | research.md §12                                               |
| Cloud              | Azure (Key Vault for secrets via env vars)                    | `reference-architecture.yaml → infrastructure`                |

**Project overrides**: `projects/{project_name}/context/project-config.yaml → overrides` (Article I, Rule 4)

---

## 2. Phase Placement

```
F1 → ava-summary → F2 → ava-summary → F3 → ava-summary
                                    → F5 → ava-summary
                                    → F7 → ava-summary
                                    → F6 → ava-summary (FINAL)
```

These agents' position within F3:

```
F2 Orchestrator → requestor-inspection gate → package-approval gate
F3 → ava-stack-orchestrator
   → [Step 1.5] ava-stack-docs-researcher (React bundle)
   → [Step 2-5] ava-stack-react-frontend (generic) OR ava-build-cycle-react-scaffold (build-cycle)
   → [Step 6a/8] ava-stack-build-validator → PASS | FAIL | TOOLCHAIN_UNAVAILABLE
   → [Step 10] handoff to ava-summary
F3 Orchestrator → ava-summary
```

**Quality gates at this phase**: Requestor Inspection (pre-F3), Package Approval, F2 Preconditions Gate (within scaffold), Summary Validator (after phase).

`human_gate_required: true` conditions: inherited from F1 risk register — not re-evaluated by F3 scaffold agents.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO  -- agent is an LLM prompt file
Application    -> NO
Infrastructure -> NO
Presentation   -> NO
```

> **Note**: These agents ARE the generators of Clean Architecture React code.
> The generated frontend follows a per-BC 5-layer structure:
> `domain/` → `application/` → `infrastructure/` → `ui/` → `tests/`.

Cross-layer coupling: NONE

---

## 4. Agent File Structure

Skill/Agent two-layer split (Constitution Article XI):

```
# 1A — User-facing coder agent (modify-existing)
.github/skills/ava-stack-react-frontend/
└── SKILL.md                                    ← CREATE (currently missing)

src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-react-frontend.md                     ← MODIFY (0.1.0-stub → 1.0.0)

# 1B — Internal-only build-cycle template (new)
src/modules/ava-fabric-agents/tech-stack/templates/
└── build-cycle-react-scaffold.md               ← CREATE (no SKILL.md)

# Supporting changes
src/modules/ava-fabric-agents/tech-stack/module.yaml         ← MODIFY
src/shared/data/stub-registry.yaml                           ← MODIFY
src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md  ← MODIFY
CHANGELOG.md                                                 ← MODIFY
```

**Agent frontmatter — 1A** (`coder-react-frontend.md`):

```yaml
---
name: "ava-stack-react-frontend"
version: "1.0.0"
description: |
  Gera código React 18 + TypeScript 5+ production-ready por bounded context,
  com Vite ou Next.js App Router, Zustand ou TanStack Query para estado,
  React Router v6, autenticação MSAL (Azure AD) ou Auth0, e integração com
  cliente TypeScript gerado a partir do OpenAPI. Em modo build-cycle, delega
  ao agente ava-build-cycle-react-scaffold.
  Ativa com: "gerar frontend React", "generate React frontend", "react codegen",
  "criar projeto React", "React 18 por bounded context".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

**Agent frontmatter — 1B** (`build-cycle-react-scaffold.md`):

```yaml
---
name: "ava-build-cycle-react-scaffold"
version: "1.0.0"
description: |
  Lê o architecture-blueprint.md e o project-config.yaml, extrai os bounded contexts
  e gera o scaffolding completo do projeto React 18 + Vite + TypeScript 5 em Clean
  Architecture por BC: package.json raiz, estrutura de módulos (domain / application /
  infrastructure / ui / tests), router lazy-load, autenticação MSAL, serviços HTTP via
  OpenAPI TypeScript client, Vitest + React Testing Library e gate de segurança via
  npm audit. CQRS é configurável via architecture_patterns.cqrs em project-config.yaml.
  Ativa com: "gerar scaffolding React", "criar projeto React build-cycle",
  "scaffold bounded context React", "build cycle React scaffold".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

**Dispatch mode**:

- 1A `coder-react-frontend.md`: user-facing (SKILL.md required)
- 1B `build-cycle-react-scaffold.md`: internal-only (dispatched by `ava-stack-orchestrator` only)

**SKILL.md** (1A): (1) resolve `project_name` from `project-config.yaml`, (2) read `agent-task-config.yaml` + `shared-context.md`, (3) delegate to `coder-react-frontend.md`. Reference: `.github/skills/ava-stack-angular-frontend/SKILL.md`.

**Shared resources**: `jsts-research-instructions.md` (React section §3), `frontend-governance.md`

---

## 5. module.yaml Impact

File: `src/modules/ava-fabric-agents/tech-stack/module.yaml`

Diff to apply:

```yaml
# Remove status: stub from existing entry:
- id: ava-stack-react-frontend
  file: agents/coder-react-frontend.md
  routing_key: "react"
  # DELETE LINE: status: stub

# Add new entry (no skill: field — internal-only):
- id: ava-build-cycle-react-scaffold # NEW
  file: templates/build-cycle-react-scaffold.md # NEW
  routing_key: "react+build-cycle" # NEW
```

The **top-level** `module.yaml` does NOT need updating — `tech-stack` is an existing module.

---

## 6. Observability & Trace Propagation

Propagation chain:

```
AgentTask.trace_id
  → [copied unchanged into agent execution]
  → implementation-status.json.trace_id
  → scaffold-manifest.json (same trace_id)
  → build_summary_comprehensive.py reads for F8 HTML
```

Both `coder-react-frontend.md` (generic) and `build-cycle-react-scaffold.md` propagate `trace_id`.

---

## 7. Schema Changes

| Schema                     | Change Required | Description                                                            |
| -------------------------- | --------------- | ---------------------------------------------------------------------- |
| `agent-task.schema.json`   | NO              | Agent reads `project_name`, `trace_id` — both already present          |
| `agent-result.schema.json` | NO              | Output via `implementation-status.json` custom schema, not AgentResult |

> See [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md)

---

## 8. Implementation Phases (tasks.md categories)

> **Note (M1 remediation)**: The "Category N" labels below are implementation groupings
> used in this plan for narrative clarity — they do NOT map 1:1 to tasks.md IMFAI category
> numbers. tasks.md is the authoritative task structure for `/speckit.implement`.
> Cross-reference by topic, not by category number.

**Category 1** — Modify `coder-react-frontend.md` (1A):

- Frontmatter: `name`, `version: 1.0.0`, Portuguese description, `allowed-tools`
- Body: Routing Guard (build-cycle → redirect; generic → execute), generic scaffold steps, Output Contract, Observability

**Category 2** — Create `build-cycle-react-scaffold.md` (1B):

- Frontmatter, Routing Guard (abort on wrong keys), F2 Preconditions Gate
- Role & Persona, Input Contract
- Scaffold execution steps (per-BC: Vite, TypeScript, React Router, auth, state, tests)
- npm install + npm audit gate, write `implementation-status.json` (PENDING) + `scaffold-manifest.json`
- Observability section

**Category 3** — Create `SKILL.md` for `ava-stack-react-frontend`

**Category 4** — Update `orchestrator-stack.md` routing table + Step 0.3b

**Category 5** — Update `stub-registry.yaml` (both entries COMPLETE)

**Category 6** — Update `module.yaml` (tech-stack)

**Category 7** — Update `CHANGELOG.md`

---

## 9. Complexity Tracking

No Constitution gate failures — all gates pass. No complexity justification required.

| Gate                      | Status | Note                                                |
| ------------------------- | ------ | --------------------------------------------------- |
| Article I (no hardcoding) | PASS   | All versions from `project-config.yaml`             |
| Article II (frontmatter)  | PASS   | Both frontmatter blocks conform                     |
| Article XI (SKILL split)  | PASS   | Coder: SKILL.md created; build-cycle: internal-only |
| Article X (version bump)  | PASS   | 1A: MAJOR (stub→full); 1B: new v1.0.0               |

---

## 10. Test Strategy

| Test Type         | Tool                        | Target                                                                                                                          | Spec Scenario |
| ----------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| Contract (output) | JSON Schema                 | `implementation-status.json` matches [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md) | All           |
| Nominal BDD       | Manual + quickstart.md      | Build-cycle scaffold generates all BCs                                                                                          | Scenario 1    |
| Blocked gate      | Manual + quickstart.md      | F2 gate blocks when artifacts missing                                                                                           | Scenario 2    |
| Minimal BC        | Manual + quickstart.md      | BC without UI gets minimal scaffold                                                                                             | Scenario 3    |
| Routing guard     | Manual + quickstart.md      | Wrong `pipeline_mode` → abort                                                                                                   | Scenario 4    |
| Build validation  | `ava-stack-build-validator` | `npm run build` exits 0                                                                                                         | Quickstart §2 |
| Stub registry     | grep                        | Both entries COMPLETE after implementation                                                                                      | Quickstart §6 |
| Regression        | Existing F3 tests           | No change to `build-cycle-python-scaffold`, `build-cycle-angular-agent`                                                         | —             |
