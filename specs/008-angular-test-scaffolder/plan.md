# Agent Implementation Plan: Angular Test Scaffolder

**Spec**: `specs/008-angular-test-scaffolder/spec.md`
**Branch**: `008-angular-test-scaffolder`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-angular-frontend` |
| **Phase** | `F3` |
| **Module** | `tech-stack` |
| **Change Type** | `modify-existing` — MINOR bump `1.0.0` ? `1.1.0` |
| **Target File** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` |
| **Primary Requirement** | Add a Test Scaffolder step that generates `*.spec.ts` for every Service, Guard, Interceptor, and Pipe produced by the agent, and sets the 80% coverage threshold in `angular.json`. |
| **Technical Approach** | Insert new **Step 9.5 — Test Scaffolder** between existing Steps 9 and 10; fix frontmatter duplicate keys; add 2 new Consistency Gate checklist items in Step 10. |

---

## Constitution Check

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded; Angular/Karma versions come from `tobe_stack.frontend_version` in `project-config.yaml`
- [x] **Article II** — Frontmatter updated to `name`, `version`, `description` (PT + activation phrases), `allowed-tools` only; duplicate `version:` and `date:` keys removed
- [x] **Article II** — Agent `name` = `ava-stack-angular-frontend` matches `^ava-[a-z0-9-]+$` ?
- [x] **Article III** — Phase F3, position unchanged; `ava-stack-orchestrator` dispatches; `ava-summary` runs after F3 completes
- [x] **Article IV** — `module.yaml` entry already exists (modify-existing); no update needed
- [x] **Article V** — All new agent body text in Brazilian Portuguese
- [x] **Article VI** — BDD scenarios in spec section 4: 7 scenarios covering Services, Guards, Interceptors, Pipes, coverage threshold, edge (no public methods), routing guard bypass
- [x] **Article VII** — No security sub-pipeline impact; test files are generated artifacts, not security controls. Existing Security Compliance Gate unchanged.
- [x] **Article VIII** — `trace_id` propagated unchanged through SKILL.md wrapper; no new trace logic needed
- [x] **Article IX** — N/A: this is an LLM prompt file (`.md`), not generated application code
- [x] **Article X** — Version bump: `1.0.0` ? `1.1.0` (MINOR — new non-breaking scaffolding step added)
- [x] **Article XI** — `modify-existing`; SKILL.md at `.github/skills/ava-stack-angular-frontend/SKILL.md` already exists and does not change

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec
- [x] All output paths use `projects/{project_name}/outputs/tobe/source-code/` (correct F3 convention)
- [x] `next_agent` unchanged — still returns to `ava-stack-orchestrator`

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Frontend | Angular (version from `tobe_stack.frontend_version`) | `ConfigStackDotNet.yaml` ? `tobe_stack.frontend_version` |
| Test runner | Karma + Jasmine (default) | Already scaffolded in Step 2 `package.json` devDependencies |
| Test API style | Standalone: `provideHttpClient()` + `provideHttpClientTesting()` | Angular 17+ standalone-first convention (research R-03) |
| Guard spec | `TestBed.runInInjectionContext()` for functional guards | Angular 17 (research R-04) |
| Interceptor spec | `withInterceptors([fn])` | Angular 17 standalone API (research R-05) |
| Coverage config | `coverageThreshold` in `angular.json` under `test.options` | `karma-coverage` v2.x API (research R-02) |
| Coverage target | 80% statements/branches/functions/lines | PBI 2283 AC; read from `project-config.yaml ? coverage_threshold`, default 80 |
| Jest override | Emit WARNING, continue with Karma/Jasmine | Research R-01 (Jest migration out of scope) |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

Master pipeline sequence (unchanged):
```
F1 -> ava-summary -> F2 -> ava-summary -> F3 -> ava-summary
                                       -> F5 -> ava-summary
                                       -> F7 -> ava-summary
                                       -> F6 -> ava-summary (FINAL)
```

This agent's position (unchanged):
```
ava-stack-orchestrator
  -> ava-stack-angular-frontend (THIS AGENT — F3)
     -> ava-stack-build-validator (runs ng test post-generation)
  -> ava-stack-orchestrator (continues to containerize / CI)
```

**Quality gate at this phase**: `summary-validator` (after F3 completes); `ava-stack-build-validator` validates `ng test` pass.

Conditions for `human_gate_required: true` (unchanged):
- Security compliance gate returns `NON_COMPLIANT`

---

## 3. Clean Architecture Alignment

```
Domain         -> N/A — agent is an LLM prompt file (.md), not generated application code
Application    -> N/A
Infrastructure -> N/A
Presentation   -> N/A
```

Note: The generated `*.spec.ts` files are test code (not Clean Architecture layers). They live alongside source files in `outputs/tobe/source-code/frontend/src/app/`.

---

## 4. Agent File Structure (unchanged)

Skill/Agent two-layer split (Constitution Article XI):

```
.github/skills/ava-stack-angular-frontend/
+-- SKILL.md                         ? unchanged (routing wrapper)

src/modules/ava-fabric-agents/tech-stack/agents/
+-- coder-angular-frontend.md        ? MODIFIED (this PBI)
```

**Dispatch mode**: user-facing (SKILL.md already exists, unchanged)

---

## 5. module.yaml Impact

**N/A** — `modify-existing`. The agent is already registered in `src/modules/ava-fabric-agents/tech-stack/module.yaml`. No `module.yaml` changes required.

---

## 6. Observability & Trace Propagation

N/A for this change. `trace_id` flows through `shared-context.md` via the SKILL.md wrapper, unchanged.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | No new input fields |
| `agent-result.schema.json` | NO | `artifacts` array already captures all output paths |

---

## 8. Implementation Phases

### Phase 0 — Research (COMPLETE)
All unknowns resolved in `research.md`:
- **R-01**: Karma/Jasmine chosen as default test runner
- **R-02**: `coverageThreshold` format under `angular.json ? test.options`
- **R-03**: `provideHttpClient()` + `provideHttpClientTesting()` for Angular 17 standalone
- **R-04**: `TestBed.runInInjectionContext()` + `MsalService` stub for guards
- **R-05**: `withInterceptors([fn])` for functional interceptor specs
- **R-06**: New step inserted as **Step 9.5** between Step 9 and Step 10
- **R-07**: Pipe spec generates 3 test cases minimum (nominal, null, invalid)
- **R-08**: MINOR version bump `1.0.0` ? `1.1.0`

### Phase 1 — Agent Body Changes (5 edits, 1 file)

**File**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`

#### Edit 1.1 — Frontmatter Fix + Version Bump

Target: YAML frontmatter block (lines 1–14 approx.)

Modifications:
- Remove the first `version: 1.0.0` and `date: 2026-06-01` duplicate lines
- Update the remaining `version` to `"1.1.0"`
- Add `"test scaffolder Angular"` to the `Ativa com:` list in `description`

Result frontmatter:
```yaml
---
name: ava-stack-angular-frontend
version: "1.1.0"
date: 2026-06-10
description: |
  Gera código Angular production-ready com boas práticas: standalone
  components, signals, lazy loading, MSAL para auth, NgRx para state.
  Inclui scaffolding automático de *.spec.ts para Services, Guards,
  Interceptors e Pipes com mocks padrão (HttpClientTestingModule, MsalService).
  Versão lida de `tobe_stack.frontend_version` em project-config.yaml.
  Ativa com: "gerar componente Angular", "criar tela", "Angular frontend",
  "NgRx store", "MSAL authentication", "test scaffolder Angular".
allowed-tools: Read, Write, Edit, Glob
---
```

#### Edit 1.2 — Output Contract Extension

Target: `## Output Contract` ? `outputs:` block

Append after the existing `components:` line:
```yaml
  service_spec:     "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/{bc}/{name}.service.spec.ts"
  guard_spec:       "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/{bc}/guards/{name}.guard.spec.ts"
  interceptor_spec: "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/core/interceptors/{name}.interceptor.spec.ts"
  pipe_spec:        "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/shared/pipes/{name}.pipe.spec.ts"
```

#### Edit 1.3 — Testing Requirements Update

Target: `## Testing Requirements` section

Update the `Unit = 80%` line to clarify automatic scaffolding:
```markdown
- **Unit = 80%** — scaffolding automático de *.spec.ts via Step 9.5 para services, pipes, guards e interceptors
```

#### Edit 1.4 — New Step 9.5 (inserted before Step 10)

Full Portuguese instruction block. Key sub-steps:

| Sub-step | Description |
|---|---|
| 9.5.0 | Read `tobe_stack.test_runner`; warn if Jest (Karma/Jasmine is default) |
| 9.5.1 | Modify generated `angular.json`: add `codeCoverage: true` + `coverageThreshold` (80% all dimensions) under `test.options` |
| 9.5.2 | For each `*.service.ts`: generate `*.service.spec.ts` with `provideHttpClient()` + `provideHttpClientTesting()` and one `it()` per public method |
| 9.5.3 | For each `*.guard.ts`: generate `*.guard.spec.ts` with `MsalService` stub + `TestBed.runInInjectionContext()` + `canActivate: true/false` tests |
| 9.5.4 | For each `*.interceptor.ts`: generate `*.interceptor.spec.ts` with `withInterceptors([fn])` + `HttpTestingController` + `afterEach(() => httpMock.verify())` |
| 9.5.5 | For each `*.pipe.ts`: generate `*.pipe.spec.ts` with direct class instantiation + 3 `it()` cases (nominal, null, invalid); no TestBed |

See template structures in `data-model.md` sections 2.1–2.4.

#### Edit 1.5 — Step 10 Consistency Gate — New Items

Target: `### Step 10` ? Consistency Verification Gate checklist

Add new `TESTES UNITÁRIOS` section at the end of the gate table:
```
TESTES UNITÁRIOS
[?|?] Cada {bc}.service.ts gerado tem {bc}.service.spec.ts correspondente
[?|?] angular.json ? test.options.coverageThreshold configurado (todos = 80)
```

### Phase 2 — Gate Logic
No changes to risk scoring or `human_gate_required` conditions.

### Phase 3 — BDD Traceability

| Spec Scenario | Plan Step | Automation Target |
|---|---|---|
| S1: Service scaffolding | Edit 1.4 §9.5.2 | `quickstart.md` Scenario 1 (file existence check) |
| S2: Guard scaffolding | Edit 1.4 §9.5.3 | `quickstart.md` Scenario 3 |
| S3: Interceptor scaffolding | Edit 1.4 §9.5.4 | `quickstart.md` Scenario 3 |
| S4: Pipe scaffolding | Edit 1.4 §9.5.5 | `quickstart.md` Scenario 3 |
| S5: Coverage threshold | Edit 1.4 §9.5.1 + Edit 1.2 | `quickstart.md` Scenario 2 |
| S6: No public methods edge case | Edit 1.4 §9.5.2 (guard clause) | Smoke test in generated spec |
| S7: build-cycle bypass | Routing Guard (unchanged) | `quickstart.md` Scenario 4 |

### Phase 4 — Registration

| Artifact | Action |
|---|---|
| `src/modules/ava-fabric-agents/tech-stack/module.yaml` | No change (already registered) |
| `.github/skills/ava-stack-angular-frontend/SKILL.md` | No change |
| `CHANGELOG.md` | Add entry: `[1.1.0] ava-stack-angular-frontend: Add Test Scaffolder (Step 9.5) for Services, Guards, Interceptors and Pipes; add coverageThreshold 80% to angular.json; fix duplicate frontmatter keys` |
| `docs/agents-catalog.md` | Update capability description for `ava-stack-angular-frontend` |

---

## 9. Complexity Tracking

| Item | Complexity | Justification |
|---|---|---|
| `TestBed.runInInjectionContext()` for functional guards | Medium | Angular 17 API; not widely known; documented in R-04 |
| `withInterceptors([fn])` for functional interceptors | Medium | Replaces legacy `HTTP_INTERCEPTORS` multi-provider; R-05 |
| Pipe spec test case inference from `transform()` signature | Low | Model reads signature and generates matching `it()` blocks |
| Coverage threshold JSON format | Low | Straightforward `angular.json` edit; R-02 |
| Frontmatter duplicate key removal | Low | Bugfix; no behavioral change |
| Step 9.5 insertion between Steps 9 and 10 | Low | Non-breaking; Steps 1–9 and 10 numbering preserved |

No cross-layer coupling. No Constitution gate violations.

---

## 10. Acceptance Criteria Traceability

| PBI AC | Spec Scenario | Plan Edit | DoD |
|---|---|---|---|
| Test Scaffolder section added with explicit instructions | S1–S4 | Edit 1.4 | `### Step 9.5` in agent with full PT-BR sub-steps |
| Every Service has `.spec.ts` with HttpClient mock | S1 | Edit 1.4 §9.5.2 | Template uses `provideHttpClient()` + `provideHttpClientTesting()` |
| Every Guard has `.spec.ts` with MsalService + AuthService mocks | S2 | Edit 1.4 §9.5.3 | Template stubs both; tests both `canActivate` paths |
| Every Pipe has `.spec.ts` with transformation test cases | S4 | Edit 1.4 §9.5.5 | Minimum 3 `it()` blocks (nominal, null, invalid) |
| Coverage threshold 80% in angular.json | S5 | Edit 1.4 §9.5.1 | `coverageThreshold` with 80 in all 4 dimensions |
| Tests pass with `ng test --no-watch --code-coverage` | S3–S4 | Phase 3 | quickstart.md Scenario 3 passes; exit code 0 |
