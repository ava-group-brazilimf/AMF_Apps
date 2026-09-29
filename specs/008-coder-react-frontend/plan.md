# Agent Implementation Plan: coder-react-frontend

**Branch**: `PBI-2322` | **Date**: 2026-07-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-coder-react-frontend/spec.md`

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-react-frontend` |
| **Phase** | F3 (Tech Stack — codegen) |
| **Module** | `tech-stack` |
| **Primary Requirement** | Replace the STUB `coder-react-frontend.md` with a full production-ready implementation that generates Vite + React 18 + TypeScript strict frontend code per bounded context, with all 10 patterns from PBI 2322. |
| **Technical Approach** | Rewrite `coder-react-frontend.md` following structural parity of `coder-angular-frontend.md`; bump version `0.1.0-stub` to `1.0.0`; update `stub-registry.yaml`, `module.yaml`, `orchestrator-stack.md`, and `SKILL.md`. |
| **Change Type** | `modify-existing` — **MAJOR** version bump |
| **Files changed** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` (primary rewrite), `src/shared/data/stub-registry.yaml`, `src/modules/ava-fabric-agents/tech-stack/module.yaml`, `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md`, `.github/skills/ava-stack-react-frontend/SKILL.md`, `CHANGELOG.md` |

---

## Constitution Check

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded — React version read from `project-config.yaml -> tobe_stack.frontend_version`; `openapi-typescript` invoked via `npx` (no version pinned in agent body)
- [x] **Article II** — Frontmatter contains ONLY: `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools` — `date` field removed from frontmatter
- [x] **Article II** — agent `name` matches pattern `^ava-[a-z0-9-]+$` — `ava-stack-react-frontend`
- [x] **Article III** — Phase placement valid — F3, routed by `ava-stack-orchestrator` when `frontend_framework == "react"` — no pipeline routing change
- [x] **Article IV** — Module-level `module.yaml` diff prepared — see section 5; `status: stub` line removed
- [x] **Article V** — Agent body language is Brazilian Portuguese — all 20 instruction sections in pt-BR
- [x] **Article VI** — BDD scenarios in spec section 4 — 5 scenarios covering nominal (8 ACs), routing guard, security gate, edge case, test scaffolder
- [x] **Article VII** — Security sub-pipeline impact assessed — Security Compliance Review Gate is a mandatory step inside the agent body; runs after codegen, before handoff; no interaction with F1 security pipeline
- [x] **Article VIII** — trace_id propagation — N/A: LLM prompt file; `trace_id` passed via `AgentResult.trace_id` by convention
- [x] **Article IX** — Clean Architecture — N/A: agent is an LLM prompt file; generated React code uses feature-based structure
- [x] **Article X** — Version bump: **MAJOR** (`0.1.0-stub` -> `1.0.0`). Output Contract changes from empty to full artifact set. CHANGELOG.md entry required.
- [x] **Article XI** — Skill/Agent split: SKILL.md exists; must be updated to remove STUB routing protocol

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec or research
- [x] All outputs follow `projects/{project_name}/outputs/tobe/source-code/frontend/`
- [x] Downstream `next_agent` confirmed: `ava-stack-orchestrator`

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Agent runtime | LLM prompt file (.md) | N/A |
| Frontend framework | React 18 | `project-config.yaml -> tobe_stack.frontend_version` (runtime) |
| Build tool | Vite 5 + @vitejs/plugin-react | spec section 7, research section 3 |
| Language | TypeScript 5+ strict | research section 3 |
| Server state | TanStack Query v5 | research section 1 |
| Client state | Zustand | research section 1 |
| Service layer types | openapi-typescript | research section 2 |
| Charts | Recharts (default) | research section 4 |
| Auth | MSAL React / @azure/msal-react | `project-config.yaml -> auth.provider` (runtime) |
| Testing | Vitest + @testing-library/react | research section 9 |
| CSP | meta tag or vite-plugin-csp | research section 7 |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

```
F2 -> ava-summary -> F3 -> ava-summary -> F5 -> ava-summary -> F7 -> ava-summary -> F6 -> ava-summary (FINAL)
```

This agent position:
```
F3 -> ava-stack-orchestrator
     -> [frontend_framework == "react"] -> ava-stack-react-frontend  [THIS AGENT]
     -> emits next_agent: ava-stack-orchestrator
F3 Orchestrator -> ava-summary
```

`human_gate_required: true` conditions:
- `security_gate: BLOCKED` (PII in localStorage; dangerouslySetInnerHTML without DOMPurify)
- `risk.level == "critical"` (hardcoded secret found in generated code)

---

## 3. Clean Architecture Alignment

```
Domain         -> NO  (LLM prompt file)
Application    -> NO  (LLM prompt file)
Infrastructure -> NO  (LLM prompt file)
Presentation   -> NO  (LLM prompt file)
```

Generated React code uses feature-based structure (data-model.md): `components/` (Presentation), `hooks/` (Application), `stores/` (Application), `services/` (Infrastructure), `types/` (Domain).

Cross-layer coupling: NONE within the agent file.

---

## 4. Agent File Structure

```
.github/skills/ava-stack-react-frontend/
+-- SKILL.md     <- update: remove STUB protocol; delegate to active agent

src/modules/ava-fabric-agents/tech-stack/agents/
+-- coder-react-frontend.md   <- FULL rewrite; 20 sections from data-model.md
```

Agent frontmatter (Article II compliant — no extra fields):
```yaml
---
name: "ava-stack-react-frontend"
version: "1.0.0"
description: |
  Gera codigo React 18 + Vite + TypeScript strict production-ready por bounded context:
  Zustand/TanStack Query para state, MSAL para auth, padroes de Modal, FilterPanel,
  CRUD com cache invalidation, formulario de Update com pre-populacao via useQuery,
  service layer via openapi-typescript, guardrail de graficos, Security Compliance Gate,
  e Test Scaffolder com Vitest + React Testing Library.
  Roteamento: tobe_stack.frontend_framework == "react".
  Ativa com: "gerar frontend React", "generate React frontend", "react codegen",
  "criar componente React", "scaffold React feature".
allowed-tools: Read, Write, Edit, Glob
---
```

---

## 5. module.yaml Impact

`src/modules/ava-fabric-agents/tech-stack/module.yaml` — remove `status: stub`:

```yaml
# BEFORE
  - id: ava-stack-react-frontend
    file: agents/coder-react-frontend.md
    routing_key: "react"
    status: stub

# AFTER
  - id: ava-stack-react-frontend
    file: agents/coder-react-frontend.md
    routing_key: "react"
```

Top-level `module.yaml` at repo root: NOT updated (no new module).

---

## 6. Observability and Trace Propagation

N/A — LLM prompt file. `trace_id` flows via SKILL.md wrapper through `shared-context.md`.
Agent body reads `trace_id` from task context and copies unchanged to `AgentResult.trace_id`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| agent-task.schema.json | NO | Existing input fields sufficient |
| agent-result.schema.json | NO | `implementation.status: "COMPLETE"` already valid |

---

## 8. Implementation Phases

### Phase 0 — Frontmatter + STUB removal (prerequisite)

Files: `coder-react-frontend.md`

Replace entire file content with clean structure:
- Frontmatter: Article II compliant (name, version 1.0.0, description pt-BR, allowed-tools)
- Remove: `date` field, `## Stub Response Protocol`, `## Stack (when implemented)`
- Verify: `name` matches `^ava-[a-z0-9-]+$`

---

### Phase 1 — Routing Guard + Required Scaffolding (PBI 2323)

Section: `## Routing Guard — Verificar Pipeline Mode` + `## Scaffolding Obrigatorio`

Routing Guard logic:
```
READ project-config.yaml
  -> extrair pipeline_mode, tobe_stack.frontend_framework

SE frontend_framework != "react":
  -> Emitir caixa FRAMEWORK INCOMPATIVEL
  -> NÃO gerar artefatos; Encerrar

SE pipeline_mode == "build-cycle":
  -> Redirecionar para ava-build-cycle-react-scaffold; Encerrar

SE pipeline_mode == "generic" OU ausente:
  -> Continuar execucao
```

Required scaffolding files (each with documented failure if absent):
- `index.html` — Vite entry point (build fails without it)
- `src/main.tsx` — React DOM root
- `src/App.tsx` — Root component
- `vite.config.ts` — plugin-react for JSX transform
- `tsconfig.json` — strict:true, skipLibCheck:true, jsx:react-jsx
- `vitest.config.ts` — environment:jsdom
- `package.json` — all deps listed in data-model.md

---

### Phase 2 — Modal Pattern (PBI 2324)

Section: `## Padrao de Modal`

Rules:
- `isOpen: boolean` always in parent; NEVER useState inside modal
- `onClose: () => void` typed; no default value
- All domain props typed (no `any`)
- Accessibility: `aria-modal="true"`, `aria-label` on close button
- Anti-pattern block: `useState(false)` inside modal -> PROIBIDO

---

### Phase 3 — FilterPanel Simultaneous Criteria (PBI 2325)

Section: `## Padrao de FilterPanel`

Rules:
- `useFilterStore` (Zustand) with `filters: Record<string, unknown>`
- `filteredData` via `useMemo` with `Array.every()` — ALL criteria simultaneously
- Anti-pattern: `forEach` + early `return` -> PROIBIDO (root cause of PBI 2245/2246)

---

### Phase 4 — CRUD + Cache Invalidation (PBI 2326)

Section: `## Padrao CRUD (useQuery + useMutation)`

Rules:
- GET: `useQuery({ queryKey: [bc, entity], queryFn })`
- POST/PUT/DELETE: `useMutation({ mutationFn, onSuccess: () => queryClient.invalidateQueries(...) })`
- `onSuccess` with `invalidateQueries` is MANDATORY on every mutation (root cause of PBI 2250)
- Loading, Empty, Error states required on every list component

---

### Phase 5 — Update Form Pre-population (PBI 2327)

Section: `## Formulario de Update com Pre-populacao`

Rules:
- `useQuery({ queryKey: [bc, entity, id], enabled: !!id })` — `enabled: !!id` mandatory
- `useEffect(() => { if (data) form.reset(data) }, [data])` — full object reset
- Anti-pattern: partial `reset({ field1: data.field1 })` -> PROIBIDO (root cause of PBI 2251)

---

### Phase 6 — Service Layer (PBI 2328)

Section: `## Camada de Servico via openapi-typescript`

Steps in agent instruction:
1. Check for OpenAPI spec path in `project-config.yaml -> tobe_stack.openapi_specs[bc]`
2. If present: `npx openapi-typescript {spec-path} -o src/features/{bc}/types/api.d.ts`
3. Generate `createApiClient` wrapper typed with generated `paths`
4. Export typed functions: `list()`, `getById()`, `create()`, `update()`, `delete()`
5. If spec absent: generate placeholder with TODO + WARNING in ImplementationNotes.md

---

### Phase 7 — Chart Guardrail (PBI 2329)

Section: `## Guardrail de Graficos — Eixos Explicitos`

Schema-first axis resolution:
```
ANTES de qualquer componente de grafico:
1. READ OpenAPI spec do BC
2. Localizar endpoint que alimenta o grafico
3. Identificar campo X e campo Y no schema de resposta
4. Usar APENAS esses nomes como dataKey
5. SE indeterminavei: TODO + WARNING em ImplementationNotes.md; NAO inventar nomes genericos
```

---

### Phase 8 — Security Compliance Gate (PBI 2330)

Section: `## Security Compliance Review Gate (OBRIGATORIO)`

Runs AFTER codegen, BEFORE handoff. Three checks:
1. **PII em localStorage**: regex scan — BLOCKED se encontrado (HIGH)
2. **CSP**: meta tag ou vite-plugin-csp — APPROVED_WITH_RISKS se ausente (MEDIUM)
3. **dangerouslySetInnerHTML**: deve ser acompanhado de DOMPurify.sanitize() — BLOCKED se ausente (HIGH)

Gate output: `SecurityComplianceReport-Frontend.md` (mandatory doc). If BLOCKED: `human_gate_required: true`.

---

### Phase 9 — Test Scaffolder (PBI 2331)

Section: `## Test Scaffolder (Vitest + React Testing Library)`

For every `.tsx` component, generate sibling `.spec.tsx` with:
1. Smoke render test
2. Primary interaction test (`@testing-library/user-event`)
3. Mocked service hook test (`vi.mock(...)`)

Rule: import only from `vitest` and `@testing-library/react` — NEVER Jest globals.
Wrap with `QueryClientProvider` when component uses TanStack Query.

---

### Phase 10 — Registry Cleanup (PBI 2332)

Five files:
1. `src/shared/data/stub-registry.yaml`: `status: STUB` -> `status: COMPLETE` for `coder-react-frontend` (keep `notes`)
2. `src/modules/ava-fabric-agents/tech-stack/module.yaml`: remove `status: stub` from entry
3. `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md`: remove STUB warning for `react` routing
4. `.github/skills/ava-stack-react-frontend/SKILL.md`: remove STUB protocol; delegate to active agent
5. `CHANGELOG.md`: add entry for `ava-stack-react-frontend` v1.0.0 MAJOR

---

## 9. Complexity Tracking

| Gate | Status | Justification |
|---|---|---|
| Article I (no hardcoded versions) | PASS | React version resolved from project-config.yaml at runtime |
| Article IX (Clean Architecture) | N/A | LLM prompt file; generated code uses feature-based structure |
| STUB-to-COMPLETE transition | MANAGED | 5 files tracked in Phase 10; all in `files changed` summary |
| Angular structural parity | TRACKED | 20-section structure mirrors Angular agent; React differences documented per section |
| Security Compliance Gate | MANDATORY | Phase 8; blocks if PII or bare dangerouslySetInnerHTML; human_gate_required on BLOCKED |

---

## 10. Test Strategy

Full validation in [quickstart.md](quickstart.md) — 12 PowerShell checks (CA01-CA12):

| CA | Test | Tool | Target |
|---|---|---|---|
| CA01 | Routing Guard wrong framework | Static inspection | No files written; success: false |
| CA02 | Required scaffolding | Test-Path | 6 non-negotiable files present |
| CA03 | Feature structure per BC | Test-Path | 5 subdirs per BC |
| CA04 | Modal typed props | Select-String | `isOpen: boolean` present |
| CA05 | FilterPanel simultaneous | Select-String | useFilterStore + useMemo |
| CA06 | CRUD cache invalidation | Select-String | invalidateQueries in mutation hook |
| CA07 | Update form pre-population | Select-String | useQuery + reset( in same component |
| CA08 | openapi-typescript types | Get-ChildItem | api.d.ts per BC |
| CA09 | Security report present | Test-Path + line count | Report > 10 lines |
| CA10 | Vitest spec per component | Get-ChildItem | .spec.tsx sibling for every .tsx |
| CA11 | stub-registry COMPLETE | Select-String | status: COMPLETE for coder-react-frontend |
| CA12 | module.yaml clean | Select-String | No status: stub in entry |
