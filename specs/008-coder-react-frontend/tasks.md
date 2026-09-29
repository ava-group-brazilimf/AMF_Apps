# Agent Development Tasks: coder-react-frontend

**Plan**: `specs/008-coder-react-frontend/plan.md`
**Agent ID**: `ava-stack-react-frontend` | **Phase**: `F3` | **Module**: `tech-stack`
**Change Type**: `modify-existing` — MAJOR bump (`0.1.0-stub` -> `1.0.0`)
**Target file**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 3 is SKIPPED (plan section 7: no schema changes).
> Categories 4, 6, and 7 can all run in parallel after Category 2 completes.

---

## Category 1 -- Agent Frontmatter & Contract Definition

Must complete before Category 2. Clears the STUB state and establishes the new contract.

- [X] **1.1** Open `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` and replace the entire STUB frontmatter block with the Article II-compliant frontmatter:
  - `name: "ava-stack-react-frontend"` — matches `^ava-[a-z0-9-]+$`
  - `version: "1.0.0"` (MAJOR bump from `0.1.0-stub`)
  - `description: |` in Brazilian Portuguese, ending with `Ativa com: "gerar frontend React", "generate React frontend", "react codegen", "criar componente React", "scaffold React feature".`
  - `allowed-tools: Read, Write, Edit, Glob, Bash` — **keep `Bash`** (required by task 2.10 step 2 to invoke `npx openapi-typescript`; the existing stub already has `Bash`; removing it silently breaks the service layer at runtime)
  - Remove `date:` field (not valid per Article II)
  - Remove `## 🚧 Stub Response Protocol` section entirely
  - Remove `## Stack (when implemented)` section entirely

- [X] **1.2** Write `## Output Contract` YAML block in the agent body using lowercase `{project_name}` paths:
  ```yaml
  outputs:
    frontend_code:  "projects/{project_name}/outputs/tobe/source-code/frontend/"
    components:     "projects/{project_name}/outputs/tobe/source-code/frontend/src/features/"
  mandatory_docs:
    - "projects/{project_name}/outputs/tobe/docs/delivery/ImplementationNotes.md"
    - "projects/{project_name}/outputs/tobe/docs/delivery/ChangedScreens.md"
    - "projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md"
  ```

- [X] **1.3** Verify all output paths use the F3 codegen folder (`outputs/tobe/source-code/`) — NOT `outputs/tobe/docs/` for the source code output

- [X] **1.4** Write `## Input Contract` YAML block with all fields from `data-model.md`:
  - HARD STOP fields: `project_name`, `pipeline_mode`, `frontend_framework`
  - Required fields: `frontend_version`, `auth_provider`, `bounded_contexts`, `trace_id`
  - Optional fields: `ui_library`, `openapi_spec_paths`, `language`, `client_name`

- [X] **1.5** Update existing `.github/skills/ava-stack-react-frontend/SKILL.md`:
  - Remove the STUB routing protocol block (`╔══ STUB AGENT...╚══`)
  - Remove `implementation.status: STUB` handoff block
  - Ensure SKILL.md (1) resolves `project_name` from `project-config.yaml`, (2) reads `agent-task-config.yaml` + `shared-context.md`, (3) delegates to `coder-react-frontend.md`

---

## Category 2 -- Agent Behavior & Instructions

Depends on Category 1. This is the core rewrite — 18 instruction sections in Brazilian Portuguese.
All sections follow the structural parity of `coder-angular-frontend.md`.

- [X] **2.1** Write `## Routing Guard — Verificar Pipeline Mode` section (PBI 2323):
  - READ `project-config.yaml` → extract `pipeline_mode` and `tobe_stack.frontend_framework`
  - SE `frontend_framework != "react"` → emit `FRAMEWORK INCOMPATIVEL` error box → STOP; no artifacts written
  - SE `pipeline_mode == "build-cycle"` → emit redirect box for `ava-build-cycle-react-scaffold` → STOP
  - SE `pipeline_mode == "generic"` OR absent → continue

- [X] **2.2** Write `## Transition Notifications` section (parity with Angular agent):
  - Start: `↳ 🔄 [ava-stack-react-frontend] Working...`
  - Completion: `↳ ✅ [ava-stack-react-frontend] Completed → retornando ao ava-stack-orchestrator`

- [X] **2.3** Write `## Data Sovereignty — Regra Absoluta` section (parity with Angular agent):
  - No workspace data to external endpoints
  - Only GET/HEAD to public documentation permitted
  - Block any `fetch`/`Invoke-WebRequest` with body containing workspace data

- [X] **2.4** Write `## Role & Persona` section:
  - Desenvolvedor React sênior especialista em React 18, TypeScript strict, Vite, TanStack Query, Zustand e arquitetura baseada em features

- [X] **2.5** Write `## ⛔ Scaffolding Obrigatorio` section (PBI 2323 — parity with Angular agent's non-negotiable files):
  - `index.html` → failure: `Could not resolve entry module 'index.html'`
  - `src/main.tsx` → failure: build cannot find module
  - `src/App.tsx` → failure: required by `main.tsx`
  - `vite.config.ts` → failure: JSX transform fails without `@vitejs/plugin-react`
  - `tsconfig.json` → must include `"strict": true`, `"skipLibCheck": true`, `"jsx": "react-jsx"`
  - `vitest.config.ts` → must include `environment: "jsdom"`
  - `src/shared/lib/queryClient.ts` → exports a configured `QueryClient` instance used by `<QueryClientProvider>` in `main.tsx` and test wrappers (failure to generate causes `QueryClientProvider` usage in task 2.14 to break)
  - `package.json` → must list all required deps (react@18, react-dom, @tanstack/react-query, zustand, recharts, @azure/msal-react, openapi-typescript as devDep, vitest, @testing-library/react, @testing-library/user-event)

- [X] **2.6** Write `## Padrao de Modal` section (PBI 2324):
  - Interface: `isOpen: boolean` (parent-managed), `onClose: () => void`, typed domain props (no `any`)
  - Accessibility: `aria-modal="true"`, `aria-label` on close button
  - Anti-pattern guard: `useState(false)` inside modal → `⛔ PROIBIDO`
  - Anti-pattern guard: untyped `onClose` → `⛔ PROIBIDO`

- [X] **2.7** Write `## Padrao de FilterPanel` section (PBI 2325):
  - `useFilterStore` (Zustand): `filters: Record<string, unknown>`, `setFilter()`, `clearFilters()`
  - `filteredData` via `useMemo(() => data.filter(item => Object.entries(filters).every(...)), [data, filters])`
  - Anti-pattern guard: `forEach` + early `return` → `⛔ PROIBIDO` (causes first-match only — root cause PBI 2245/2246)

- [X] **2.8** Write `## Padrao CRUD (useQuery + useMutation)` section (PBI 2326):
  - GET: `useQuery({ queryKey: [bc, entity], queryFn })`
  - POST/PUT/DELETE: `useMutation({ mutationFn, onSuccess: () => queryClient.invalidateQueries({ queryKey: [bc, entity] }) })`
  - `onSuccess` + `invalidateQueries` is MANDATORY on every mutation → absence causes BLOCK (root cause PBI 2250)
  - Loading, Empty, Error states required on every list component

- [X] **2.9** Write `## Formulario de Update com Pre-populacao` section (PBI 2327):
  - `useQuery({ queryKey: [bc, entity, id], enabled: !!id })` — `enabled: !!id` mandatory
  - `useEffect(() => { if (data) form.reset(data) }, [data])` — must reset with FULL object
  - Anti-pattern: partial `reset({ field1: data.field1 })` → `⛔ PROIBIDO` (root cause PBI 2251)

- [X] **2.10** Write `## Camada de Servico via openapi-typescript` section (PBI 2328):
  - Step 1: check `project-config.yaml → tobe_stack.openapi_specs[bc]` for spec path
  - Step 2 (spec present): document `npx openapi-typescript {spec-path} -o src/features/{bc}/types/api.d.ts`
  - Step 3: generate typed `createApiClient` wrapper using generated `paths` type
  - Step 4: export typed `list()`, `getById()`, `create()`, `update()`, `delete()` functions
  - Step 5 (spec absent): generate placeholder with `// TODO: replace with generated openapi-typescript types` + WARNING in ImplementationNotes.md; **also set `AgentResult.risk.level = 'medium'`** and append an entry to `AgentResult.risk.findings` listing the BC name and the missing spec path (satisfies S4-AC2)

- [X] **2.11** Write `## Guardrail de Graficos — Eixos Explicitos` section (PBI 2329):
  - Before ANY chart component: READ OpenAPI spec → find endpoint → identify X field and Y field in response schema
  - Use ONLY those field names as `dataKey`
  - If indeterminate: add `⚠️ TODO` comment in component + WARNING in ImplementationNotes.md — NEVER invent generic names without marking

- [X] **2.12** Write `## Security Invariants (OBRIGATORIOS)` section:
  - XSS: never use `dangerouslySetInnerHTML` without `DOMPurify.sanitize()`
  - Secrets: never hardcode tokens, client IDs, API URLs — always `import.meta.env.VITE_*`
  - PII/Logs: never log personal data (name, email, CPF) — only IDs and error codes
  - Input: validate all user inputs (Zod schemas or controlled component patterns)

- [X] **2.13** Write `## Accessibility Invariants (WCAG 2.1 AA)` section (parity with Angular agent):
  - `aria-label` required on all action buttons without visible text
  - `alt` required on all `<img>`
  - Consistent focus order (`tabIndex`) in forms
  - WCAG 2.1 AA contrast: 4.5:1 text, 3:1 UI components

- [X] **2.14** Write `## Testing Requirements` section:
  - Every `.tsx` component generates sibling `.spec.tsx`
  - Import only from `vitest` and `@testing-library/react` — NEVER Jest globals
  - Wrap with `QueryClientProvider` when component uses TanStack Query
  - Minimum 3 tests per component: smoke render, primary interaction, mocked service hook

- [X] **2.15** Write `## Security Compliance Review Gate (OBRIGATORIO)` section (PBI 2330):
  - Executes AFTER codegen, BEFORE handoff — non-negotiable
  - Step 0 (parity with Angular agent): READ `projects/{project_name}/outputs/tobe/docs/security-architecture.md` → extract project-specific controls from §3 (Auth) and §4 (Input Validation); use these to augment the three standard checks below
  - Check 1 — PII em localStorage: regex scan for `localStorage.setItem` with keys matching `name|email|cpf|token|senha|password|phone|celular` → BLOCKED if found (HIGH severity)
  - Check 2 — CSP: `index.html` must have `<meta http-equiv="Content-Security-Policy">` OR `vite-plugin-csp` in `package.json` → APPROVED_WITH_RISKS if absent (MEDIUM)
  - Check 3 — dangerouslySetInnerHTML: must be accompanied by `DOMPurify.sanitize()` on same string → BLOCKED if bare (HIGH)
  - Gate output: write `SecurityComplianceReport-Frontend.md`
  - If BLOCKED: set `human_gate_required: true`; set `AgentResult.success: false`; stop pipeline

- [X] **2.16** Write `## Execution Steps` section — numbered, deterministic steps (1–N):
  1. Pre-flight: READ `project-config.yaml`; execute Routing Guard
  2. Emit start notification
  3. For each BC in `bounded_contexts`: generate feature directory structure
  4. For each BC: generate service layer (openapi-typescript or placeholder)
  5. For each BC: generate Zustand stores (`useFilterStore`, domain stores)
  6. For each BC: generate TanStack Query hooks (`useQuery`, `useMutation` with cache invalidation)
  7. For each BC: generate components (applying Modal, FilterPanel, CRUD, Update form, Chart guardrail patterns)
  8. For each BC: generate `.spec.tsx` test files for every component (Test Scaffolder)
  9. Generate required scaffolding files (`index.html`, `main.tsx`, `App.tsx`, `vite.config.ts`, `tsconfig.json`, `vitest.config.ts`, `package.json`)
  10. Execute Security Compliance Review Gate; write `SecurityComplianceReport-Frontend.md`
  11. Write `ImplementationNotes.md` and `ChangedScreens.md`
  12. Emit handoff (AgentResult JSON with `next_agent: ava-stack-orchestrator`)

- [X] **2.17** Write `## Handoff` section with `AgentResult` JSON structure:
  - Fields: `agent`, `version`, `trace_id`, `success`, `next_agent`, `artifacts`, `security_gate`, `risk`, `implementation`
  - `implementation.status`: `"COMPLETE"` (not `"STUB"`)
  - `next_agent`: `"ava-stack-orchestrator"`

- [X] **2.18** [P] Verify: every section title is in Brazilian Portuguese; no English section headers except `## Output Contract` and `## Input Contract` (standard contract section names)

---

## Category 3 -- Shared Schema Updates

**SKIPPED** — plan section 7 confirms no changes to `agent-task.schema.json` or `agent-result.schema.json`.
`implementation.status: "COMPLETE"` is already a valid value in the existing schema.

---

## Category 4 -- Module Registration

Depends on Category 1. Entry already exists — only clean up the stub marker.

- [X] **4.1** In `src/modules/ava-fabric-agents/tech-stack/module.yaml`, remove `status: stub` from the `ava-stack-react-frontend` entry:
  - BEFORE: entry has `routing_key: "react"` + `status: stub`
  - AFTER: entry has only `routing_key: "react"` (no status field)
  - Do NOT add a `skill:` key — the existing entry structure is preserved

- [X] **4.2** Verify the top-level `module.yaml` at repo root is NOT modified (no new module created)

- [X] **4.3** Verify `bmad_version: ">=6.0.0"` preserved in top-level `module.yaml`

---

## Category 5 -- Quality Gate Checklists

- [X] **5.1** Verify the Security Compliance Review Gate (written in task 2.15) correctly triggers `human_gate_required: true` for all three BLOCKED conditions: PII in localStorage, dangerouslySetInnerHTML without DOMPurify, critical hardcoded secret

- [X] **5.2** Verify the Routing Guard (task 2.1) correctly emits error and stops — no partial files created — when `frontend_framework != "react"`

- [X] **5.3** [P] Verify all 12 quickstart checks (CA01–CA12 in `quickstart.md`) have corresponding behavior in the agent instruction sections:
  - CA01 → task 2.1 (Routing Guard)
  - CA02 → task 2.5 (Scaffolding — including `queryClient.ts`)
  - CA03 → task 2.16 step 3 (BC structure)
  - CA04 → task 2.6 (Modal isOpen)
  - CA05 → task 2.7 (FilterPanel useMemo)
  - CA06 → task 2.8 (CRUD invalidateQueries)
  - CA07 → task 2.9 (Update form reset)
  - CA08 → task 2.10 (openapi-typescript api.d.ts; risk.level set in step 5)
  - CA09 → task 2.15 (Security Compliance Gate report — Step 0 reads security-architecture.md)
  - CA10 → task 2.14 (Test Scaffolder .spec.tsx)
  - CA11 → task 7.1 (stub-registry COMPLETE)
  - CA12 → task 4.1 (module.yaml clean)

- [X] **5.4** [P] Verify `AgentResult.success: false` is explicitly set when `security_gate: BLOCKED`

---

## Category 6 -- Acceptance Validation & QA Integration

Depends on Category 2.

- [X] **6.1** Confirm spec section 4 acceptance scenarios map to implemented behavior:
  - Scenario 1 (Nominal P1, 8 ACs) → tasks 2.1, 2.5–2.16 collectively satisfy all 8 sub-checks
  - Scenario 2 (Routing Guard P1) → task 2.1 handles `frontend_framework != "react"` and `pipeline_mode == "build-cycle"`
  - Scenario 3 (Security Gate P1) → task 2.15 handles PII-in-localStorage and dangerouslySetInnerHTML cases
  - Scenario 4 (Edge: missing OpenAPI P2) → task 2.10 step 5 generates placeholder with TODO + WARNING
  - Scenario 5 (Test Scaffolder P2) → task 2.14 generates `.spec.tsx` with Vitest + RTL imports

- [X] **6.2** [P] Run the agent against `projects/test-determinism/` (or `projects/Meu-ERP/` with `frontend_framework: "react"` set) to validate:
  - All paths in `## Output Contract` exist after execution
  - Output files are non-empty and follow the correct formats
  - No artifacts from other agents modified or deleted

- [X] **6.3** [P] Run quickstart.md validation checks CA01–CA12 using PowerShell and confirm all pass

- [X] **6.4** [P] Map spec section 4 BDD scenarios to F5 QA pipeline inputs:
  - Reference Scenario 1 as input to `ava-qa-behavior-mapping` with `BR-001` through `BR-012` traceability markers
  - Verify scenarios use standard `BR-NNN` / `FR-NNN` format

---

## Category 7 -- Documentation & Catalog Update

Can run parallel with Category 6.

- [X] **7.1** [P] In `src/shared/data/stub-registry.yaml`, update the `coder-react-frontend` entry:
  - Change `status: STUB` → `status: COMPLETE`
  - Keep the existing `notes:` field (references build-cycle variants still needed)
  - Keep all other fields (`file`, `agent_name`, `routing_key`, `dispatched_by`, `priority`, `owner`)

- [X] **7.2** [P] In `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md`:
  - Find and remove or update any STUB warning text for the `react` frontend routing key
  - Ensure the routing comment for `ava-stack-react-frontend` no longer says "STUB" or "NOT IMPLEMENTED"

- [X] **7.3** [P] Add `CHANGELOG.md` entry at the top of the changelog:
  ```
  ## [1.0.0] ava-stack-react-frontend — 2026-07-09
  ### Added (MAJOR)
  - Full implementation replacing STUB v0.1.0
  - Routing Guard (pipeline_mode + frontend_framework validation)
  - Vite + React 18 + TypeScript strict structure per bounded context
  - Modal pattern (isOpen boolean, typed onClose prop)
  - FilterPanel with simultaneous all-criteria filtering (Zustand + useMemo)
  - CRUD: useQuery + useMutation with mandatory invalidateQueries on success
  - Update form pre-population via useQuery + form.reset(fullObject) on mount
  - Service layer via openapi-typescript (types) + typed createApiClient wrapper
  - Chart guardrail: schema-driven X/Y axis dataKey resolution
  - Security Compliance Review Gate (CSP, PII, dangerouslySetInnerHTML)
  - Test Scaffolder: Vitest + RTL .spec.tsx per component
  ### Breaking
  - Output Contract changes from empty (STUB) to full artifact set
  - AgentResult.implementation.status changes from "STUB" to "COMPLETE"
  ```

- [X] **7.4** [P] Update `docs/agents-catalog.md`:
  - Find `ava-stack-react-frontend` entry (or add if missing)
  - Update: version `1.0.0`, status `COMPLETE`, outputs `outputs/tobe/source-code/frontend/`

---

## Completion Checklist

- [X] All categories complete (1, 2, 4, 5, 6, 7 — Category 3 skipped by plan)
- [X] `coder-react-frontend.md` has no STUB content; version is `1.0.0`; frontmatter is Article II compliant
- [X] SKILL.md updated — no STUB protocol; correctly delegates to active agent
- [X] `module.yaml` entry has no `status: stub`
- [X] Agent validated against test project — all 12 quickstart checks CA01–CA12 pass
- [X] `stub-registry.yaml` shows `status: COMPLETE` for `coder-react-frontend`
- [X] `orchestrator-stack.md` has no STUB warning for `react` routing
- [X] `docs/agents-catalog.md` updated with v1.0.0
- [X] `CHANGELOG.md` entry committed for v1.0.0 MAJOR


