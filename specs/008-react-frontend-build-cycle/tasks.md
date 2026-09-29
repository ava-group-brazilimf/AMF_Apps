# Agent Development Tasks: ava-stack-react-frontend (Build Cycle Mode)

**Plan**: `specs/008-react-frontend-build-cycle/plan.md`
**Agent ID**: `ava-stack-react-frontend` (1A) + `ava-build-cycle-react-scaffold` (1B) | **Phase**: `F3` | **Module**: `tech-stack`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 3 is SKIPPED â€” plan Â§7 confirms no schema changes required.
> Categories 4, 5, 6, 7 can run in parallel after Category 2 completes.

---

## Category 1 â€” Agent Frontmatter & Contract Definition

Must complete before Category 2. 1A and 1B tasks within this category can run in parallel after task 1.1.

- [x] **1.1** Read `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` in full before modifying â€” verify current stub structure, identify all sections to replace
- [x] **1.2** Rewrite YAML frontmatter in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`: `name: "ava-stack-react-frontend"`, `version: "1.0.0"` (MAJOR bump from `0.1.0-stub`), `description` in pt-BR ending with activation phrases, `allowed-tools: Read, Write, Edit, Bash, Glob, Grep` â€” remove all stub-era fields
- [x] **1.3** [P] Create new file `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md` with YAML frontmatter: `name: "ava-build-cycle-react-scaffold"`, `version: "1.0.0"`, `description` in pt-BR (see spec Â§2B for exact text), `allowed-tools: Read, Write, Edit, Bash, Glob, Grep`
- [x] **1.4** Write `## Output Contract` section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` â€” paths: `projects/{project_name}/outputs/tobe/source-code/frontend/` and `implementation-status.json`, using lowercase `{project_name}`
- [x] **1.5** [P] Write `## Output Contract` section in `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md` â€” list all output paths from spec Â§3B (package.json, vite.config.ts, tsconfig.json, index.html, .env.example, src/main.tsx, src/router/index.tsx, src/auth/_, src/shared/_, src/{bc_name}/\*, scaffold-manifest.json, implementation-status.json)
- [x] **1.6** [P] Create `.github/skills/ava-stack-react-frontend/SKILL.md`: (1) resolve `project_name` from `projects/_template/context/project-config.yaml`, prompt user if absent; (2) read `projects/{PROJECT_NAME}/context/agent-task-config.yaml` + `shared-context.md`; (3) delegate to `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` â€” reference `.github/skills/ava-stack-angular-frontend/SKILL.md` for exact structure

---

## Category 2 â€” Agent Behavior & Instructions

Depends on Category 1.
Tasks 2.1â€“2.6 (agent 1A) and tasks 2.7â€“2.18 (agent 1B) can run in parallel â€” they write to different files.

### 2A â€” `coder-react-frontend.md` (modify-existing)

- [x] **2.1** Write **Routing Guard** section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`: READ `project-config.yaml` â†’ extract `pipeline_mode`; if `pipeline_mode == "build-cycle"` emit redirect box pointing to `@ava-build-cycle-react-scaffold` and stop; if `"generic"` or absent â†’ continue (reference `coder-angular-frontend.md` Routing Guard for exact box format)
- [x] **2.2** Write **Transition Notifications** and **Data Sovereignty** sections in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` (reference `coder-angular-frontend.md` for exact format; adapt agent name and next-agent pointer)
- [x] **2.3** Write **Role & Persona** section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`: React 18 senior dev, TypeScript strict, MSAL/Auth0, Clean Architecture per bounded context, Vitest + RTL â€” in pt-BR
- [x] **2.4** Write **Input Contract** section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` (fields: project_name, frontend_version from `tobe_stack.frontend_version`, cqrs, bounded_contexts, auth_provider, ui_library, package_manager, trace_id)
- [x] **2.5** Write numbered **scaffold execution steps** (generic mode) in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`: Step 1 read project-config.yaml; Step 2 extract BCs from architecture-blueprint.md; Steps 3â€“7 generate per-BC files (domain/, application/, ui/, tests/); Step 8 write implementation-status.json (status: COMPLETED); Step 9 invoke build-validator
- [x] **2.6** [P] Write **Observability & FASE OBRIGATÃ“RIA** section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`: trace_id propagation from AgentTask â†’ implementation-status.json; mandatory observability registration Bash block (reference existing agents for exact block format)

### 2B â€” `build-cycle-react-scaffold.md` (new agent)

- [x] **2.7** [P] Write **Routing Guard** section in `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md`: READ project-config.yaml â†’ extract `pipeline_mode` AND `tobe_stack.frontend_framework`; if `pipeline_mode != "build-cycle"` â†’ â›” ABORT; if `frontend_framework != "react"` â†’ â›” ABORT; both correct â†’ continue (reference `build-cycle-python-scaffold.md` Routing Guard for exact format)
- [x] **2.8** [P] Write **Gate de PrÃ©-condiÃ§Ãµes F2** section in `build-cycle-react-scaffold.md`: VERIFY `outputs/tobe/docs/architecture-blueprint.md` (absent â†’ BLOCKED); VERIFY `outputs/tobe/docs/security-architecture.md` (absent â†’ BLOCKED); VERIFY `outputs/readiness-gate/wave-1/readiness-gate-status.json` exists AND `status == "APPROVED"` (absent or non-APPROVED â†’ BLOCKED); if all present â†’ continue (reference `build-cycle-python-scaffold.md` Â§Gate de PrÃ©-condiÃ§Ãµes for exact format)
- [x] **2.9** [P] Write **Role & Persona** + **Data Sovereignty** sections in `build-cycle-react-scaffold.md`: React 18 senior dev, Vite 5, TypeScript strict, MSAL, Zustand + TanStack Query, Clean Architecture per BC â€” in pt-BR; Data Sovereignty: no workspace data sent externally, only GET/HEAD to public docs
- [x] **2.10** [P] Write **Input Contract** section in `build-cycle-react-scaffold.md`: project_name, frontend_version (from `tobe_stack.frontend_version`), frontend_framework (must be `"react"`), bundler (from `tobe_stack.rendering_mode`, default `"vite"`), package_manager (from `tobe_stack.package_manager`, default `"npm"`), ui_library (from `tobe_stack.ui_library`), auth_provider (from `auth.provider`, default `"azure-ad"`), cqrs (from `architecture_patterns.cqrs`), bounded_contexts (extracted from architecture-blueprint.md), trace_id
- [x] **2.11** [P] Write **BC extraction step** in `build-cycle-react-scaffold.md` (Step 1): READ architecture-blueprint.md; parse bounded context names (kebab-case); for each BC determine `has_ui` (presence of UI Screens / Telas section); classify as `full` (has_ui=true) or `minimal` (has_ui=false); log classified list
- [x] **2.12** [P] Write **root project files generation** steps in `build-cycle-react-scaffold.md` (Step 2): generate `package.json` with semver ranges resolved at runtime â€” write `"react": "^{major}.0.0"` using the value from `tobe_stack.frontend_version` (e.g. `"18"` â†’ `"^18.0.0"`); `docs-researcher` provides the exact latest patch version in Step 1.5; include react-dom, vite@^5, @vitejs/plugin-react, typescript, react-router-dom@^6, zustand, @tanstack/react-query, vitest, @testing-library/react, msw, and auth library resolved from `auth.provider`; generate `vite.config.ts`; `tsconfig.json` (strict: true, noImplicitAny: true); `tsconfig.node.json`; `index.html`; `.env.example` (VITE_API_BASE_URL, auth env vars per provider â€” never hardcode values). **If `tobe_stack.rendering_mode == "ssr"` is detected**, emit âš ï¸ warning: "Next.js SSR nÃ£o implementado neste release â€” usando Vite SPA como fallback." and continue with Vite.
- [x] **2.13** [P] Write **shared layer generation** steps in `build-cycle-react-scaffold.md` (Step 3): generate `src/main.tsx` (MsalProvider or Auth0Provider wrapping App); `src/App.tsx` (RouterProvider); `src/router/index.tsx` (createBrowserRouter with lazy() per BC route + AuthGuard); `src/auth/msal-config.ts` or `auth0-config.ts` (env-var references only); `src/auth/AuthGuard.tsx`; `src/shared/components/` (Button.tsx, Input.tsx, Table.tsx, Modal.tsx stubs); `src/shared/api/index.ts` (API_BASE_URL stub)
- [x] **2.14** [P] Write **per-BC full scaffold** steps in `build-cycle-react-scaffold.md` (Step 4, for each BC with has_ui=true): generate `src/{bc_name}/domain/types.ts`; `src/{bc_name}/application/` (if cqrs=true: commands/, queries/, handlers/; if cqrs=false: services/, hooks/, dtos/); `src/{bc_name}/infrastructure/api/{BcName}Api.ts`; `src/{bc_name}/ui/pages/{BcName}ListPage.tsx` and `{BcName}DetailPage.tsx`; `src/{bc_name}/ui/components/`; `src/{bc_name}/tests/unit/{BcName}Page.test.tsx`; `src/{bc_name}/tests/integration/`
- [x] **2.15** [P] Write **per-BC minimal scaffold** steps in `build-cycle-react-scaffold.md` (Step 5, for each BC with has_ui=false): generate only `src/{bc_name}/ui/index.tsx` with placeholder comment explaining BC has no UI screens; log BC as `scaffold_mode: minimal`
- [x] **2.16** [P] Write **npm install + npm audit gate** steps in `build-cycle-react-scaffold.md` (Step 6): run `{package_manager} install --prefix {output_dir}`; run `{package_manager} audit --audit-level=high`; if exit code non-zero â†’ set `security_compliance: FAIL`, populate `security_findings` (level, count, packages); if clean â†’ set `security_compliance: PASS`; implementation.status stays COMPLETED regardless
- [x] **2.17** [P] Write **output file writing** steps in `build-cycle-react-scaffold.md` (Step 7): write `scaffold-manifest.json` (agent, version, generated_at ISO-8601, project_name, frontend_version, bundler, package_manager, auth_provider, cqrs, bounded_contexts array with scaffold_mode and files_generated, total_files_generated); write `implementation-status.json` (agent, version, implementation.status: COMPLETED, build: PENDING, security_compliance, bounded_contexts_scaffolded, bounded_contexts_minimal, outputs_generated, trace_id) â€” schema per `contracts/implementation-status-contract.md`
- [x] **2.18** [P] Write **Observability & FASE OBRIGATÃ“RIA** section in `build-cycle-react-scaffold.md`: trace_id propagated unchanged from input to implementation-status.json and scaffold-manifest.json; mandatory observability registration Bash block (reference `build-cycle-python-scaffold.md` observability section for exact format)

---

## Category 3 â€” Shared Schema Updates

**SKIPPED** â€” plan Â§7 confirms `agent-task.schema.json` and `agent-result.schema.json` require no changes. Output contract uses custom `implementation-status.json` schema defined in `contracts/implementation-status-contract.md`.

---

## Category 4 â€” Module Registration

Depends on Category 1. Tasks 4.1â€“4.4 can run in parallel.

- [x] **4.1** Update `src/modules/ava-fabric-agents/tech-stack/module.yaml`: remove `status: stub` line from the `ava-stack-react-frontend` entry (keep id, file, routing_key)
- [x] **4.2** [P] Add new entry to `src/modules/ava-fabric-agents/tech-stack/module.yaml`: `id: ava-build-cycle-react-scaffold`, `file: templates/build-cycle-react-scaffold.md`, `routing_key: "react+build-cycle"` â€” omit `skill:` field (internal-only per Article XI)
- [x] **4.3** [P] Update `src/shared/data/stub-registry.yaml` entry `coder-react-frontend`: change `status: STUB` â†’ `status: COMPLETE`; update `notes` to document implementation date and key choices (Vite 5, Zustand + TanStack Query, MSAL, build-cycle delegation)
- [x] **4.4** [P] Add new entry to `src/shared/data/stub-registry.yaml` for `build-cycle-react-scaffold`: `id: build-cycle-react-scaffold`, `file: tech-stack/templates/build-cycle-react-scaffold.md`, `agent_name: ava-build-cycle-react-scaffold`, `routing_key: "pipeline_mode == 'build-cycle' AND tobe_stack.frontend_framework == 'react'"`, `dispatched_by: tech-stack/agents/orchestrator-stack.md`, `status: COMPLETE`, `priority: HIGH`, `notes` describing what was implemented

---

## Category 5 â€” Quality Gate Checklists

Depends on Category 2.

- [x] **5.1** Verify F2 Preconditions Gate in `build-cycle-react-scaffold.md` covers all 3 required artifacts (architecture-blueprint.md, security-architecture.md, readiness-gate-status.json with APPROVED status) â€” each missing artifact emits a distinct â›” BLOCKED message with the producing agent name (per spec Scenario 2 acceptance criteria)
- [x] **5.2** [P] Verify Routing Guard in `coder-react-frontend.md` emits the redirect box with correct target (`@ava-build-cycle-react-scaffold`) when `pipeline_mode == "build-cycle"` and stops without generating files (per spec Scenario 4)
- [x] **5.3** [P] Verify Routing Guard in `build-cycle-react-scaffold.md` emits distinct â›” ABORT messages for wrong `pipeline_mode` and wrong `frontend_framework` independently (per spec Scenario 4 acceptance criteria 1 and 2)
- [x] **5.4** [P] Grep `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` and `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md` for hardcoded version strings (e.g. `@18`, `@5`, `v6`, `"18"`, `react-router-dom@6`) â€” all version references in agent bodies must use runtime-resolved placeholders or instruct `docs-researcher` to supply the version (Article I compliance)

---

## Category 6 â€” Acceptance Validation & Orchestrator Update

Depends on Category 2. Tasks 6.2â€“6.5 can run in parallel after 6.1.

- [x] **6.1** Update **frontend routing table** in `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md`: change `react` row from `ðŸš§ STUB` to `âœ… Implemented`; add second `react (build-cycle)` row pointing to `ava-build-cycle-react-scaffold` as `âœ… Implemented`
- [x] **6.2** [P] Update **Step 0.3b** in `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md`: add conditional dispatch for `frontend_framework == "react"`: if `pipeline_mode == "build-cycle"` â†’ dispatch `ava-build-cycle-react-scaffold`; else â†’ dispatch `ava-stack-react-frontend`
- [x] **6.3** [P] Run `ava-build-cycle-react-scaffold` against a configured test project (use `projects/test-react-frontend/` per quickstart.md, or `projects/test-determinism/` if already configured with `frontend_framework: react` and `pipeline_mode: build-cycle`) â€” verify all output files listed in `## Output Contract` are created and `implementation-status.json` contains `"status": "COMPLETED"` (quickstart.md Scenario 1)
- [x] **6.4** [P] Run `ava-stack-react-frontend` (generic mode) against `projects/test-determinism/` with `pipeline_mode: build-cycle` â€” confirm redirect box appears and NO files are written (quickstart.md Scenario 3 guard path); then with `pipeline_mode: generic` â€” confirm scaffold is generated
- [x] **6.5** [P] Review spec Â§4 BDD scenarios â€” confirm each scenario is traceable to a quickstart.md validation check; add `BR-` or `FR-` traceability prefix to spec scenarios if missing (required for `ava-qa-behavior-mapping` input compatibility)
- [x] **6.6** [P] Run `@ava-stack-orchestrator` against the test project with `frontend_framework: react` and `pipeline_mode: build-cycle` â€” confirm the orchestrator dispatches `ava-build-cycle-react-scaffold` (not the stub redirect) per spec Scenario 1 acceptance criterion 1; verify Step 0.3b routing decision is logged

---

## Category 7 â€” Documentation & Catalog Update

Depends on Category 2. All tasks parallelizable.

- [x] **7.1** [P] Add `ava-stack-react-frontend` v1.0.0 entry to `docs/agents-catalog.md`: ID, version (1.0.0), phase (F3), module (tech-stack), role summary, dispatch (user-facing), output artifacts (frontend/ scaffold, implementation-status.json), routing key (`react`, generic mode)
- [x] **7.2** [P] Add `ava-build-cycle-react-scaffold` v1.0.0 entry to `docs/agents-catalog.md`: ID, version (1.0.0), phase (F3), module (tech-stack), role summary, dispatch (internal-only via orchestrator), output artifacts (full scaffold), routing key (`react + build-cycle`)
- [x] **7.3** [P] Add `CHANGELOG.md` entries: `ava-stack-react-frontend` v1.0.0 MAJOR (stub â†’ full implementation; build-cycle redirect; SKILL.md created); `ava-build-cycle-react-scaffold` v1.0.0 (new agent; React 18 + Vite 5 + Zustand + TanStack Query + MSAL; per-BC 5-layer scaffold; npm audit gate)
- [x] **7.4** [P] Verify `docs/full-pipeline-guide.md` â€” confirm React frontend is listed correctly in F3 section; update any ðŸš§ STUB references for React to âœ… Implemented; no structural pipeline changes needed
- [x] **7.5** [P] Verify `src/modules/ava-fabric-agents/shared/jsts-research-instructions.md` Â§React section lists all packages generated in task 2.12 â€” specifically check for `zustand`, `@tanstack/react-query`, `msw`, and `@azure/msal-react`; add any missing npm registry entries so `docs-researcher` can fetch current versions at codegen time

---

## Completion Checklist

- [x] All 6 active categories complete (Category 3 intentionally skipped)
- [x] `coder-react-frontend.md` frontmatter: `version: "1.0.0"`, no stub fields, redirect-only build-cycle guard (not delegation)
- [x] `build-cycle-react-scaffold.md` created: frontmatter, routing guard (abort on wrong keys), F2 gate, full body, observability section
- [x] `.github/skills/ava-stack-react-frontend/SKILL.md` created (user-facing dispatch)
- [x] `build-cycle-react-scaffold.md` has NO SKILL.md (internal-only â€” Article XI)
- [x] `module.yaml` (tech-stack): `ava-stack-react-frontend` no longer has `status: stub`; `ava-build-cycle-react-scaffold` entry added
- [x] `stub-registry.yaml`: both entries show `status: COMPLETE`
- [x] `orchestrator-stack.md`: `react` row shows âœ… Implemented for both generic and build-cycle modes
- [x] Agent validated against test project â€” `implementation-status.json` contains `"status": "COMPLETED"` (Category 6.3)
- [x] Orchestrator dispatch validated end-to-end (Category 6.6)
- [x] Article I verified â€” no hardcoded version strings in agent bodies (Category 5.4)
- [x] `jsts-research-instructions.md` React section covers all packages from task 2.12 (Category 7.5)
- [x] `docs/agents-catalog.md` updated (both agents)
- [x] `CHANGELOG.md` entry committed (both v1.0.0 entries)
