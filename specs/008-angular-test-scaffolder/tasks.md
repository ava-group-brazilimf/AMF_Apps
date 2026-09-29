# Agent Development Tasks: Angular Test Scaffolder

**Plan**: `specs/008-angular-test-scaffolder/plan.md`
**Agent ID**: `ava-stack-angular-frontend` | **Phase**: `F3` | **Module**: `tech-stack`
**Change Type**: `modify-existing` — MINOR bump `1.0.0 → 1.1.0`
**Target File**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 3 (Schema) and Category 4 (Registration) are N/A for this modify-existing change.

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before Category 2. Unblocks all downstream categories.

- [X] **1.1** Fix frontmatter in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`: remove duplicate `version: 1.0.0` (line 2) and `date: 2026-06-01` (line 3); update the remaining `version` field to `"1.1.0"`; verify only `name`, `version`, `date`, `description`, and `allowed-tools` remain (no `phase`, `module`, `inputs`, `outputs`)
- [X] **1.2** [P] Extend `## Output Contract` → `outputs:` block in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`: append four new entries — `service_spec`, `guard_spec`, `interceptor_spec`, `pipe_spec` — each pointing to `projects/{project_name}/outputs/tobe/source-code/frontend/src/app/{path}/{name}.{type}.spec.ts` (see data-model.md §2 for exact paths)
- [X] **1.3** [P] Update `## Testing Requirements` section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`: change the `Unit ≥ 80%` bullet to note that spec file generation is now **automático via Step 9.5** (not manual); add the `"test scaffolder Angular"` activation phrase to the `Ativa com:` list in the frontmatter `description`

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. Tasks 2.1–2.7 are sequential (all edits to the same contiguous section).

- [X] **2.1** Insert `### Step 9.5 — Test Scaffolder` section header in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` immediately before the existing `### Step 10 — Quality Gate + Docs` heading; write the step preamble (PT-BR): file count note, purpose statement, and sub-step **9.5.0** — `READ project-config.yaml → tobe_stack.test_runner`; if value is `"jest"` emit `⚠️ WARNING: test_runner=jest — continuando com Karma/Jasmine (migração Jest fora de escopo deste PBI)` and proceed; if absent or `"karma"` continue silently
- [X] **2.2** Write sub-step **9.5.1** inside Step 9.5 in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (PT-BR): modify the already-generated `angular.json` (at `outputs/tobe/source-code/frontend/angular.json`) to add `"codeCoverage": true` and `"coverageThreshold": { "statements": 80, "branches": 80, "functions": 80, "lines": 80 }` under `projects.<project-name>.architect.test.options`; read threshold from `project-config.yaml → coverage_threshold` if present, default to 80
- [X] **2.3** Write sub-step **9.5.2** inside Step 9.5 in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (PT-BR): for each `*.service.ts` generated in Steps 3–8, generate the companion `*.service.spec.ts` using template 2.1 from data-model.md — Angular 17 standalone API (`provideHttpClient()` + `provideHttpClientTesting()`), one `it()` per public method; include the edge-case guard: if the service has zero public methods, generate a single smoke test `it('should be created', () => expect(service).toBeTruthy())`
- [X] **2.4** Write sub-step **9.5.3** inside Step 9.5 in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (PT-BR): for each `*.guard.ts` generated, generate `*.guard.spec.ts` using template 2.2 from data-model.md — `TestBed.runInInjectionContext()` for functional guards; `MsalService` stub with `instance.getActiveAccount`; two tests: `canActivate → true` (authenticated) and `canActivate → false` (unauthenticated + `router.navigate` called)
- [X] **2.5** Write sub-step **9.5.4** inside Step 9.5 in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (PT-BR): for each `*.interceptor.ts` generated, generate `*.interceptor.spec.ts` using template 2.3 from data-model.md — `provideHttpClient(withInterceptors([fn]))` + `provideHttpClientTesting()`; `HttpTestingController` with `afterEach(() => httpMock.verify())`; one pass-through request test
- [X] **2.6** Write sub-step **9.5.5** inside Step 9.5 in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (PT-BR): for each `*.pipe.ts` generated, generate `*.pipe.spec.ts` using template 2.4 from data-model.md — direct class instantiation (no `TestBed`); inspect the `transform()` signature to derive nominal/null/invalid test values; minimum 3 `it()` blocks: nominal transformation, null input returns `''`, invalid type returns `''`
- [X] **2.7** Update `### Step 10 — Quality Gate + Docs` → Consistency Verification Gate checklist table in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`: add new `TESTES UNITÁRIOS` section at the end of the gate box with two items: `[✅|❌] Cada {bc}.service.ts gerado tem {bc}.service.spec.ts correspondente` and `[✅|❌] angular.json → test.options.coverageThreshold configurado (todos ≥ 80)`

---

## Category 3 — Shared Schema Updates

**SKIPPED** — Plan §7 confirms no changes to `agent-task.schema.json` or `agent-result.schema.json`. The `artifacts` array in `AgentResult` already captures all output paths.

---

## Category 4 — Module Registration

**SKIPPED** — `modify-existing` change. Agent `ava-stack-angular-frontend` is already registered in `src/modules/ava-fabric-agents/tech-stack/module.yaml`. SKILL.md at `.github/skills/ava-stack-angular-frontend/SKILL.md` is unchanged.

---

## Category 5 — Quality Gate Checklists

Can run parallel with Categories 6 and 7 after Category 2 completes.

- [X] **5.1** Verify Constitution compliance in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` after all Category 2 edits: (a) frontmatter has exactly one `version: "1.1.0"` and no duplicate keys; (b) Step 9.5 body is entirely in Brazilian Portuguese; (c) no technology versions (Angular version numbers, Karma/Jasmine version numbers) are hardcoded in the new step — all resolved from `tobe_stack.frontend_version`; (d) Handoff section still lists `build: PASS` as a required gate (unchanged)

---

## Category 6 — Acceptance Validation & QA Integration

Can run parallel with Category 7 after Category 2 completes. Tasks 6.1–6.4 are independent [P].

- [X] **6.1** [P] Run quickstart.md Scenario 1 against a project generated by the updated agent: execute the `find` + shell script that checks each `*.service.ts`, `*.guard.ts`, `*.interceptor.ts`, and `*.pipe.ts` has a corresponding `*.spec.ts` — confirm zero `❌ MISSING` lines in output (validates plan Edits 1.4 §9.5.2–9.5.5)
- [X] **6.2** [P] Run quickstart.md Scenario 2: execute the Python JSON validation script against the generated `angular.json` and confirm `✅ angular.json coverage threshold OK` with `codeCoverage: true` and all four threshold dimensions ≥ 80 (validates plan Edit 1.4 §9.5.1)
- [X] **6.3** [P] Run quickstart.md Scenario 4: set `pipeline_mode: build-cycle` in `project-config.yaml` and invoke the updated agent; confirm the existing routing guard fires and no `*.spec.ts` files are written (validates S7 from spec — build-cycle bypass unchanged)
- [X] **6.4** [P] Run quickstart.md Scenario 5: execute `head -20 src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` and confirm `version: "1.1.0"` appears exactly once with no duplicate `version:` or `date:` keys (validates plan Edit 1.1)

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6 after Category 2 completes.

- [X] **7.1** [P] Add `CHANGELOG.md` entry under a new `## [1.1.0] — 2026-07-09` section for `ava-stack-angular-frontend`: `Add Test Scaffolder (Step 9.5) — automatic *.spec.ts generation for Services (provideHttpClient), Guards (MsalService stub), Interceptors (withInterceptors), and Pipes (direct instantiation); add coverageThreshold 80% to angular.json; fix duplicate frontmatter version/date keys (MINOR)`
- [X] **7.2** [P] Update `docs/agents-catalog.md` entry for `ava-stack-angular-frontend`: bump version to `1.1.0`; append `"Inclui scaffolding automático de *.spec.ts para Services, Guards, Interceptors e Pipes com mocks padrão"` to the capability description

---

## Completion Checklist

- [X] All categories complete (3 skipped: N/A)
- [X] `modify-existing`: SKILL.md unchanged — no new SKILL.md needed (Article XI)
- [X] `coder-angular-frontend.md` frontmatter validated: `version: "1.1.0"`, no duplicate keys
- [X] `module.yaml` unchanged (no registration step needed)
- [X] Agent validated via quickstart.md Scenarios 1–5 (Categories 6 + 5)
- [X] `docs/agents-catalog.md` updated (Category 7.2)
- [X] `CHANGELOG.md` entry committed (Category 7.1)
- [X] Note: quickstart.md Scenario 3 (`ng test --no-watch --code-coverage` in Sophia project) is deferred to PBI 2287 — manual human gate

---

## Dependency Graph

```
[Cat 1.1] ──────────────────────────────────────────────────────────────┐
[Cat 1.2] ─── [P after 1.1] ────────────────────────────────────────────┤
[Cat 1.3] ─── [P after 1.1] ────────────────────────────────────────────┤
                                                                         ▼
[Cat 2.1] → [Cat 2.2] → [Cat 2.3] → [Cat 2.4] → [Cat 2.5] → [Cat 2.6] → [Cat 2.7]
                                                                         │
                          ┌──────────────────────────────────────────────┘
                          ▼                  ▼                   ▼
                    [Cat 5.1 P]       [Cat 6.1–6.4 P]     [Cat 7.1–7.2 P]
```

## Parallel Execution Examples

**After Cat 1.1 completes** → run 1.2 and 1.3 simultaneously

**After Cat 2.7 completes** → run in parallel:
- 5.1 (Constitution compliance check)
- 6.1 (spec file existence check)
- 6.2 (angular.json JSON validation)
- 6.3 (build-cycle bypass check)
- 6.4 (version bump check)
- 7.1 (CHANGELOG.md)
- 7.2 (agents-catalog.md)

## Task Count Summary

| Category | Tasks | Status |
|---|---|---|
| 1 — Frontmatter & Contract | 3 | Active |
| 2 — Behavior & Instructions | 7 | Active |
| 3 — Schema Updates | 0 | N/A (skipped) |
| 4 — Module Registration | 0 | N/A (skipped) |
| 5 — Quality Gate | 1 | Active |
| 6 — Acceptance Validation | 4 | Active |
| 7 — Documentation | 2 | Active |
| **Total** | **17** | |

## MVP Scope

Categories 1 and 2 (10 tasks) constitute the MVP — the actual agent changes. Categories 5, 6, and 7 (7 tasks) are validation and documentation and can follow immediately after.

