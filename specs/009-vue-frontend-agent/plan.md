# Agent Implementation Plan: ava-stack-vue-frontend

**Branch**: `009-vue-frontend-agent` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-vue-frontend-agent/spec.md`

---

## Summary

| Field                   | Value                                                                                                                                                                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Agent ID**            | `ava-stack-vue-frontend` — modify-existing (v0.1.0-stub → v1.0.0)                                                                                                                                                                                |
| **Phase**               | F3 (Tech Stack — codegen)                                                                                                                                                                                                                        |
| **Module**              | `tech-stack`                                                                                                                                                                                                                                     |
| **Primary Requirement** | Implement Vue 3 + Composition API frontend scaffold per bounded context with Pinia, Vue Router 4, MSAL/Auth0, and Security Compliance Review Gate — full implementation replacing the STUB.                                                      |
| **Technical Approach**  | Rewrite `coder-vue-frontend.md` from stub to full agent body mirroring `coder-angular-frontend.md`'s output contract and execution steps, adapted for Vue 3 stack; create missing SKILL.md; update orchestrator routing table and stub-registry. |
| **Change Type**         | `modify-existing`                                                                                                                                                                                                                                |
| **Files changed**       | `coder-vue-frontend.md` (rewrite), `.github/skills/ava-stack-vue-frontend/SKILL.md` (create), `orchestrator-stack.md` (routing table), `stub-registry.yaml`, `module.yaml` (remove `status: stub`), `CHANGELOG.md`                               |

---

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9)._

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded — all versions resolved from `project-config.yaml → tobe_stack.*` and `ConfigStackDotNet.yaml` at runtime; UI library from `tobe_stack.ui_library`.
- [x] **Article II** — Frontmatter contains ONLY `name`, `version`, `description`, `allowed-tools` — confirmed in spec §2.
- [x] **Article II** — `ava-stack-vue-frontend` matches `^ava-[a-z0-9-]+$` ✅
- [x] **Article III** — F3 placement valid; `ava-stack-orchestrator` dispatches after F2 gate; `ava-summary` runs after F3.
- [x] **Article IV** — Module-level `module.yaml` diff prepared (see Plan §5); `status: stub` line removed.
- [x] **Article V** — Agent body language is Brazilian Portuguese; SKILL.md also in pt-BR.
- [x] **Article VI** — BDD scenarios in spec §4: 4 scenarios covering nominal (S1), routing-guard (S2), missing BC map (S3), and orchestrator gate (S4).
- [x] **Article VII** — Security sub-pipeline: Security Compliance Review Gate embedded in agent (identical to Angular agent); DOMPurify for v-html per `frontend-governance.md`; `npm audit` gate.
- [x] **Article VIII** — `trace_id` propagated from `project-config.yaml → trace_id` → `implementation-status.json.trace_id` unchanged.
- [x] **Article IX** — N/A: LLM prompt file. Clean Architecture applies to generated Vue code artifacts, not this agent's `.md` source.
- [x] **Article X** — **MAJOR** (0.1.0-stub → 1.0.0; output contract changes from STUB/SKIPPED to COMPLETED).
- [x] **Article XI** — `ava-stack-vue-frontend`: user-facing, SKILL.md **created** at `.github/skills/ava-stack-vue-frontend/SKILL.md`.

### Quality Gate Check

- [x] No [NEEDS CLARIFICATION] markers remain in spec
- [x] All outputs follow `projects/{project_name}/outputs/tobe/source-code/frontend/` and `projects/{project_name}/outputs/tobe/docs/`
- [x] Downstream `next_agent`: `ava-stack-build-validator` — confirmed to exist in `tech-stack/agents/build-validator-agent.md`

---

## 1. Technical Context

| Dimension          | Choice                                                              | Source                                                        |
| ------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------- |
| Agent type         | LLM prompt file (`.md`)                                             | N/A — not compiled                                            |
| Frontend framework | Vue 3 (Composition API + `<script setup>`)                          | `project-config.yaml → tobe_stack.frontend_version` (runtime) |
| Bundler            | Vite 5 + `@vitejs/plugin-vue`                                       | research.md §5; `create-vue` default                          |
| State management   | Pinia (official Vue 3 store)                                        | research.md §2                                                |
| Auth (azure-ad)    | `@azure/msal-browser` + `@azure/msal-vue`                           | `project-config.yaml → auth.provider`; research.md §4         |
| Auth (other)       | Auth0 Vue SDK or generic OIDC                                       | research.md §4                                                |
| UI library         | From `tobe_stack.ui_library` (Vuetify / PrimeVue / Naive UI / none) | Article I — resolved at runtime                               |
| Testing            | Vitest + Vue Test Utils v2 ≥ 80%                                    | research.md §6                                                |
| TypeScript         | Strict mode + `skipLibCheck: true`                                  | research.md §7                                                |
| Build validation   | Vite Pipeline (VF0–VF6) in `build-validator-agent.md`               | Same as React agent (008)                                     |
| API client         | Fetch/Axios wrappers per BC from OpenAPI spec                       | research.md §8; generated by `ava-docs-tobe`                  |
| XSS mitigation     | DOMPurify before `v-html`                                           | `frontend-governance.md §XSS`                                 |
| Routing            | Vue Router 4 + `() => import()` lazy routes per BC                  | research.md §3                                                |

**Project overrides**: `projects/{project_name}/context/project-config.yaml → overrides` (Article I, Rule 4)

---

## 2. Phase Placement

```
F1 → ava-summary → F2 → ava-summary → F3 → ava-summary
                                    → F5 → ava-summary
                                    → F7 → ava-summary
                                    → F6 → ava-summary (FINAL)
```

This agent's position within F3:

```
F2 Orchestrator → requestor-inspection gate → package-approval gate
F3 → ava-stack-orchestrator
   → [Step 1.5] ava-stack-docs-researcher (Vue bundle)
   → [Step 2–9] ava-stack-vue-frontend (this agent)
   → [Step 8a]  ava-stack-build-validator → PASS | FAIL | TOOLCHAIN_UNAVAILABLE
   → [Step 10]  handoff to ava-summary
F3 Orchestrator → ava-summary
```

**Quality gates at this phase**: Requestor Inspection (pre-F3), Package Approval (pre-F3), Security Compliance Review Gate (within agent), Summary Validator (after phase).

`human_gate_required: true` conditions: inherited from F1 risk register — not re-evaluated by F3 scaffold agents.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO  -- agent is an LLM prompt file
Application    -> NO
Infrastructure -> NO
Presentation   -> NO
```

> **Note**: This agent IS a generator of Clean Architecture Vue code. The generated
> frontend follows a per-BC structure: `views/{bc}/` → `stores/` → `composables/` → `api/` → `tests/`.

Cross-layer coupling: NONE

---

## 4. Agent File Structure

Skill/Agent two-layer split (Constitution Article XI):

```
# User-facing coder agent (modify-existing)
.github/skills/ava-stack-vue-frontend/
└── SKILL.md                             ← CREATE (currently missing)

src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-vue-frontend.md                ← MODIFY (0.1.0-stub → 1.0.0; full rewrite)

# Supporting changes
src/modules/ava-fabric-agents/tech-stack/module.yaml                       ← MODIFY (remove status: stub)
src/shared/data/stub-registry.yaml                                         ← MODIFY (status: COMPLETE)
src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md      ← MODIFY (routing table ✅)
CHANGELOG.md                                                               ← MODIFY
```

**Agent frontmatter** (`coder-vue-frontend.md`):

```yaml
---
name: "ava-stack-vue-frontend"
version: "1.0.0"
description: |
  Gera código Vue 3 production-ready com Composition API, TypeScript strict,
  Pinia para state management, Vue Router 4 com lazy loading e MSAL/Auth0 para autenticação.
  Versão lida de `tobe_stack.frontend_version` em project-config.yaml.
  Ativa com: "gerar frontend Vue", "generate Vue frontend", "vue codegen",
  "criar tela Vue", "Vue 3 frontend".
allowed-tools: Read, Write, Edit, Glob
---
```

**Dispatch mode**: user-facing — SKILL.md required (dispatched by `ava-stack-orchestrator` routing + directly by user).

SKILL.md must: (1) resolve `project_name` from `project-config.yaml`, (2) read `agent-task-config.yaml` + `shared-context.md`, (3) delegate to `src/modules/ava-fabric-agents/tech-stack/agents/coder-vue-frontend.md`.

**Shared resources**: `frontend-governance.md`, `jsts-research-instructions.md`

---

## 5. module.yaml Impact

File: `src/modules/ava-fabric-agents/tech-stack/module.yaml`

Diff to apply (remove `status: stub` — entry already exists):

```yaml
# BEFORE
- id: ava-stack-vue-frontend
  file: agents/coder-vue-frontend.md
  routing_key: "vue"
  status: stub # ← DELETE THIS LINE

# AFTER
- id: ava-stack-vue-frontend
  file: agents/coder-vue-frontend.md
  routing_key: "vue"
```

The **top-level** `module.yaml` at the project root does NOT need updating — `tech-stack` is an existing module.

---

## 6. Observability & Trace Propagation

Propagation chain:

```
project-config.yaml → trace_id
  → [read in Step 1 — Leitura de Contexto]
  → implementation-status.json.trace_id   (Step 10 — Handoff)
  → build_summary_comprehensive.py reads for F8 HTML
```

`trace_id` is propagated unchanged — no mutation. The agent reads it from `project-config.yaml`
and writes it verbatim to all output artifacts that include a `trace_id` field.

Pipeline observer call: the agent's observability section (carried from the stub) must be
retained — `python src/shared/tools/pipeline_observer.py -p {project_name} track` with
agent name `ava-stack-vue-frontend` and version `1.0.0`.

---

## 7. Schema Changes

| Schema                       | Change Required | Description                                                                                                                                            |
| ---------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `agent-task.schema.json`     | NO              | Agent reads `project_name`, `trace_id` — both already present                                                                                          |
| `agent-result.schema.json`   | NO              | Output via `implementation-status.json` custom schema, not AgentResult                                                                                 |
| `implementation-status.json` | EXTEND          | `build_cycle_fallback: boolean` field added (optional); see [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md) |

---

## 8. Implementation Categories (tasks.md groupings)

> **Note**: The "Category N" labels below are implementation groupings for narrative clarity
> — they do NOT map 1:1 to tasks.md IMFAI category numbers. tasks.md is authoritative for
> `/speckit.implement`. Cross-reference by topic, not by category number.

**Category 1** — Rewrite `coder-vue-frontend.md` (full agent body):

- Frontmatter: `name`, `version: 1.0.0`, Portuguese description + activation phrases, `allowed-tools`
- Transition notifications (↳ 🔄 / ↳ ✅)
- Data Sovereignty rule (copy from Angular agent, adapt Vue references)
- Routing Guard (build-cycle → WARN+fallback; generic → proceed)
- Role & Persona (Vue 3 senior developer with Composition API, Pinia, MSAL)
- Mandatory patterns (Composition API, TypeScript strict, Pinia per BC, Vue Router 4 lazy, DOMPurify for v-html, `:key` on all `v-for`, loading/empty/error states)
- Input Contract (CRÍTICOS + IMPORTANTES fields)
- Output Contract (same paths as Angular agent)
- Required Scaffolding Files (package.json, vite.config.ts, tsconfig.json, index.html, main.ts, App.vue, .env.example)
- Security Invariants (XSS via DOMPurify, secrets via VITE\_\*, PII/logs)
- Accessibility Invariants (aria-label, alt, tabindex, WCAG 2.1 AA)
- Testing Requirements (Vitest ≥ 80%, Pinia store tests, Vue Test Utils component tests)
- Security Compliance Review Gate (identical procedure to Angular agent, Vue adaptations)
- Handoff block (implementation.status, build, security_compliance, outputs_generated, trace_id)
- Consistency Verification Gate (pre-Handoff checklist)
- Execution Steps (Step 1 context read + PRE-FLIGHT, Step 2 root scaffold, Steps 3–7 per-BC, Step 8 auth, Step 9 Security Gate, Step 10 Handoff)
- Observability section (pipeline_observer.py call)

**Category 2** — Create `SKILL.md` for `ava-stack-vue-frontend`:

- Follow `.github/skills/ava-stack-angular-frontend/SKILL.md` pattern exactly
- Resolve `project_name`, read context files, delegate to `coder-vue-frontend.md`

**Category 3** — Update `orchestrator-stack.md`:

- Routing table: `vue | ava-stack-vue-frontend | ✅` (remove `🚧 STUB`)
- No change to Step 0.3b FRONTEND_AGENTS dict (routing key `vue` already maps correctly)

**Category 4** — Update `stub-registry.yaml`:

- `id: coder-vue-frontend → status: COMPLETE, owner: "ava-stack-vue-frontend@1.0.0"`

**Category 5** — Update `module.yaml` (tech-stack):

- Remove `status: stub` from `ava-stack-vue-frontend` entry

**Category 6** — Update `CHANGELOG.md`:

- Entry: `ava-stack-vue-frontend@1.0.0 — stub → full implementation`

---

## 9. Complexity Tracking

No Constitution gate failures — all gates pass. No complexity justification required.

| Gate                      | Status | Note                                                               |
| ------------------------- | ------ | ------------------------------------------------------------------ |
| Article I (no hardcoding) | PASS   | All versions from `project-config.yaml` + `ConfigStackDotNet.yaml` |
| Article II (frontmatter)  | PASS   | Frontmatter conforms to standard                                   |
| Article XI (SKILL split)  | PASS   | SKILL.md created; agent body in tech-stack/agents/                 |
| Article X (version bump)  | PASS   | MAJOR (stub→full; contract changes)                                |

---

## 10. Test Strategy

| Test Type         | Tool                        | Target                                                                                                                          | Spec Scenario |
| ----------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| Contract (output) | JSON Schema                 | `implementation-status.json` matches [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md) | All           |
| Nominal BDD       | Manual + quickstart.md §6   | Generic mode scaffold generates all BCs                                                                                         | Scenario 1    |
| Routing guard     | Manual + quickstart.md §7   | build-cycle → WARN+fallback, not HARD STOP                                                                                      | Scenario 2    |
| Missing BC map    | Manual + quickstart.md §6   | Fallback to task BC list with WARNING                                                                                           | Scenario 3    |
| Orchestrator gate | grep + quickstart.md §1     | Routing table shows ✅, no 🚧 STUB                                                                                              | Scenario 4    |
| Build validation  | `ava-stack-build-validator` | `vite build` exits 0                                                                                                            | Quickstart §8 |
| Stub registry     | grep + quickstart.md §2     | `coder-vue-frontend` has `status: COMPLETE`                                                                                     | Quickstart §2 |
| Regression        | quickstart.md §10           | Angular and React agents unaffected                                                                                             | —             |
