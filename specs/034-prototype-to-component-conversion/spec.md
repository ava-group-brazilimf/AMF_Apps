# Agent Specification: Prototype → Component Conversion (P2C) for React and Angular Frontends

**Feature Branch**: `034-prototype-to-component-conversion`
**Created**: 2026-08-04
**Status**: Draft
**Change Type**: `modify-existing` (2 coder agents + 1 orchestrator, `tech-stack` module) + 3 new shared files
**Input**: "Atualmente os agentes de frontend não utilizam o protótipo de navegação da aplicação
gerado na fase 3 — prototype. O resultado é uma aplicação gerada sem nenhuma conexão com o design
já projetado para a aplicação."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (guardrail prose, comments, step descriptions) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> Agent frontmatter keys are English; values (`description`) are Portuguese.
> Acceptance scenarios are in English for BDD traceability with F5 QA agents.

---

## 1. Agent Identity

| Agent ID | Target file | Version transition |
|---|---|---|
| `ava-stack-angular-frontend` | `tech-stack/agents/coder-angular-frontend.md` | `2.0.0` → **`3.0.0`** (MAJOR) |
| `ava-stack-react-frontend` | `tech-stack/agents/coder-react-frontend.md` | `1.0.0` → **`2.0.0`** (MAJOR) |
| `ava-stack-orchestrator` | `tech-stack/agents/orchestrator-stack.md` | unchanged (bugfix inside an existing step) |

**Phase**: F4 (Tech Stack / Codegen) · **Module**: `tech-stack`
**Depends on**: `specs/008-design-tokens-propagation` (design-tokens.json contract),
`specs/021-frontend-backend-api-contract-integration` (per-BC OpenAPI resolution),
`specs/029-screen-flow-batch-protocol` (completeness-assertion pattern),
`specs/020-codegen-business-rules-architecture-config` §8 (server-side-only rules are not omissions).

**Why MAJOR on both** (Article X — *"Changing `inputs` or `outputs` contract = MAJOR bump"*):

- Angular: `prototype_screens` / `design_tokens` move from `CRÍTICOS — HARD STOP` to
  `OPCIONAIS — degradam com WARN` (input contract change), and the generated output layout moves
  from one page per bounded context to one page per screen (output contract change).
- React: the Input Contract gains a mandatory business-rules catalog and the output layout
  becomes per-screen.

**New shared files** (not agents — no `module.yaml` entry required):

| Path | Purpose |
|---|---|
| `src/modules/ava-fabric-agents/shared/prototype-conversion-protocol.md` | Framework-independent P2C protocol, referenced by both agents |
| `src/shared/data/patterns/react/react-patterns-reference.md` | Binding React patterns reference (the Angular counterpart already existed) |
| `src/shared/data/scaffold-manifests/react-scaffold-manifest.yaml` | React scaffold manifest — did not exist |

---

## 2. Problem Statement

The pipeline runs `F3 Prototype` before `F4 Stack/Codegen`. `ava-prototype` (v1.2.0) produces a
complete navigable prototype in `projects/{project_name}/outputs/tobe/prototype/`: a
self-contained `index.html` (one `<section class="view">` per screen, `#topbar`/`#sidebar`/`#content`
shell, form validation, three error layers, Nielsen H1–H10 heuristics, and a per-screen metadata
comment carrying `Screen / BC / API / AS-IS ref / UX rules`), plus `screen-list.md`,
`design-tokens.json`, `figma-spec.md` and `demo-script.md`.

The frontend coder agents ignore nearly all of it.

### Root Cause

**React** (`coder-react-frontend.md`, v1.0.0, 215 lines) — `grep -ci prototype` returns **0**.
The Input Contract declares neither `prototype_screens` nor `design_tokens`; Steps 4–6 emit a fixed
per-BC template (`{BcName}ListPage.tsx` / `{BcName}DetailPage.tsx`). This is a **regression**:
`specs/008-design-tokens-propagation` §1c already mandated those inputs for React; the 2026-07-14
rewrite to v1.0.0 dropped them (`grep -i prototype` over `specs/008-coder-react-frontend` → 0 hits).

**Angular** (`coder-angular-frontend.md`, v2.0.0, 3689 lines) — partial consumption only:

| | Status |
|---|---|
| `design-tokens.json` → `:root` in `styles.scss` (Guardrail G-DT) | ✅ consumed |
| `screen-list.md` | ❌ declared as CRITICAL, shown in PRE-FLIGHT, **never used in any step** |
| `index.html` | ❌ **never read by any frontend agent in the repo** |
| Screen templates | ❌ every BC gets the same `<ul>@for (item of items(); track item.id) { <li>{{ item.id }}</li> }</ul>` |

The agent itself admits the gap — `## TODOs Pendentes` line 3580:
*"Implementar templates de lista/detalhe específicos por BC (atualmente usando `<ul>` genérico)"*.

**Net effect**: only colours and spacing survive. Layout, screens, forms, tables, filters, modals,
states and navigation flow are discarded.

### Collateral defects blocking the goal

1. `master-orchestrator.md` § Fase 3 declares F3 **non-blocking** (*"o protótipo é um artefato de
   demonstração, não um pré-requisito de codegen"*), yet Angular's G-DT **HARD STOPs** without
   `design-tokens.json`. The agent contradicts the orchestrator.
2. `orchestrator-stack.md` runs `verify_scaffold.py --manifest angular` for the frontend
   **regardless of framework**, and `react-scaffold-manifest.yaml` did not exist — React frontends
   fail that gate today.
3. `build-validator-agent.md` (v2.3.0) runs install → build → lint → CVE scan. It **never runs
   tests**, so Angular's `coverageThreshold` was configured and never exercised.
4. Angular Step 9.5 scaffolds specs for services, guards, interceptors and pipes — **never for
   components/pages**. Converted screens would be the only generated code without tests.
5. Constitution Article II violations already present: both frontmatters carried a `date:` key, and
   Angular declared `allowed-tools: Read, Write, Edit, Glob` while invoking `Bash:` in Steps
   2.17 / 10.1 / 11.

### What Changes in Each Agent

| Concern | Angular (3.0.0) | React (2.0.0) |
|---|---|---|
| Prototype inventory | new Step 1.2d | new Step 1.4 |
| Tokens fallback chain | G-DT Passo 1 rewritten (HARD STOP removed) | G-DT is entirely new |
| Construct mapping | new `Guardrail G-P2C` | new `Guardrail G-P2C-React` |
| Shared components | +DS-010..DS-013, +ToastService/ConfirmService; DS-002/DS-007 gain optional inputs | RX-001..RX-014 replace the `Button/Input/Table/Modal` stubs |
| Screen generation | Steps 7.3–7.6 bodies replaced (per screen, archetype-driven) | Step 5 (new) |
| Business rules | §1.2b already existed — bound to screens | Step 1.5 entirely new |
| API contract | §1.2c already existed — joined with screen metadata | Step 1.6 entirely new |
| Fidelity assertion | new Step 9.8 | new Step 6.5 |
| Test execution | new Step 9.9 | Step 7 renamed and extended |
| Scaffold gate | already existed (§2.17) | new Step 2.8 |

---

## 3. Output Contract Changes

### 3.1 `ava-stack-angular-frontend`

```yaml
# BEFORE
outputs:
  frontend_code:    "projects/{project_name}/outputs/tobe/source-code/frontend/"
  components:       "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/"
  service_spec:     ".../src/app/{bc}/services/{name}.service.spec.ts"
  guard_spec:       ".../src/app/{bc}/guards/{name}.guard.spec.ts"
  interceptor_spec: ".../src/app/core/interceptors/{name}.interceptor.spec.ts"
  pipe_spec:        ".../src/app/shared/pipes/{name}.pipe.spec.ts"
```

```yaml
# AFTER
outputs:
  frontend_code:    "projects/{project_name}/outputs/tobe/source-code/frontend/"
  components:       "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/"
  prototype_conversion_map: "projects/{project_name}/outputs/tobe/source-code/frontend/prototype-conversion-map.json"
  screen_page:      ".../src/app/{bc}/pages/{screen_id}/{screen_id}-page.component.ts"
  screen_spec:      ".../src/app/{bc}/pages/{screen_id}/{screen_id}-page.component.spec.ts"
  service_spec:     ".../src/app/{bc}/services/{name}.service.spec.ts"
  guard_spec:       ".../src/app/{bc}/guards/{name}.guard.spec.ts"
  interceptor_spec: ".../src/app/core/interceptors/{name}.interceptor.spec.ts"
  pipe_spec:        ".../src/app/shared/pipes/{name}.pipe.spec.ts"
mandatory_docs:
  # ... existing entries unchanged ...
  - "projects/{project_name}/outputs/tobe/docs/business-rules-implementation-frontend.json"  # NEW
```

### 3.2 `ava-stack-react-frontend`

```yaml
# BEFORE
outputs:
  react_project_scaffold: "projects/{project_name}/outputs/tobe/source-code/frontend/"
  scaffold_manifest:      ".../frontend/scaffold-manifest.json"
  implementation_status:  ".../frontend/implementation-status.json"
```

```yaml
# AFTER
outputs:
  react_project_scaffold:   "projects/{project_name}/outputs/tobe/source-code/frontend/"
  scaffold_manifest:        ".../frontend/scaffold-manifest.json"
  implementation_status:    ".../frontend/implementation-status.json"
  prototype_conversion_map: ".../frontend/prototype-conversion-map.json"
  screen_page:              ".../frontend/src/{bc}/ui/pages/{ScreenPascal}Page.tsx"
  screen_test:              ".../frontend/src/{bc}/ui/pages/__tests__/{ScreenPascal}Page.test.tsx"
mandatory_docs:
  - ".../outputs/tobe/docs/delivery/frontend/react/ImplementationNotes.md"
  - ".../outputs/tobe/docs/delivery/frontend/react/ChangedScreens.md"
  - ".../outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md"
  - ".../outputs/tobe/docs/business-rules-implementation-frontend.md"
  - ".../outputs/tobe/docs/business-rules-implementation-frontend.json"
```

### 3.3 Handoff contract (both agents)

New required fields — full definition in the shared protocol §9:

```yaml
prototype_fidelity:          full | partial | degraded | none
prototype_conversion_map:    outputs/tobe/source-code/frontend/prototype-conversion-map.json
screens_expected:            0
screens_converted:           0
screens_coverage_pct:        0.0
screen_assertion:            PASS | FAIL | SKIPPED
design_tokens_source:        design-tokens.json | index-html | default
unit_tests:                  { status: PASS | BELOW_THRESHOLD | TOOLCHAIN_UNAVAILABLE,
                               coverage_pct: { statements, branches, functions, lines } }
business_rules_status:       COMPLETE | PARTIAL
business_rules_coverage_pct: 0.0
api_divergences:             0
p2c_warnings:                []
```

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal Path (Priority: P1)

```gherkin
Given a project whose F3 phase completed and produced
      outputs/tobe/prototype/{index.html, screen-list.md, design-tokens.json}
  And screen-list.md lists 12 screens with status "included" and 2 with status "deferred"
  And each screen carries an API endpoint in its prototype metadata comment
  And a per-BC OpenAPI contract exists under outputs/tobe/docs/openapi/
 When ava-stack-angular-frontend runs in pipeline_mode "generic"
 Then it writes prototype-conversion-map.json with counts.expected_conversions == 12
  And it generates exactly 12 page components, one per included screen,
      under src/app/{bc}/pages/{screen_id}/
  And each page's header renders the literal `Screen:` value from the prototype metadata
  And zero generated templates contain "<li>{{ item.id }}</li>"
  And the 2 deferred screens appear under "## TODOs Pendentes" in ImplementationNotes.md
  And the Handoff reports prototype_fidelity: full and screen_assertion: PASS
```

### Scenario 2 — Edge Case: Prototype Absent (Priority: P1)

```gherkin
Given a project where outputs/tobe/prototype/ contains neither index.html nor screen-list.md
 When ava-stack-react-frontend runs in pipeline_mode "generic"
 Then it emits the P2C-W001 warning box naming both missing artifacts
  And it does NOT hard stop
  And it writes prototype-conversion-map.json with prototype.available: false,
      screens: [] and assertion.status: "SKIPPED"
  And it falls back to the generic per-bounded-context generation rules
  And design tokens fall back to the agent defaults with design_tokens_source: "default"
  And the Handoff reports prototype_fidelity: none
  And implementation.status may still be COMPLETED
```

> This scenario encodes the user's explicit requirement — *"Em caso de não existir o protótipo
> gerado, os agentes devem emitir um WARN avisando o usuário e seguir com geração de código
> conforme as regras estabelecidas nos agentes"* — and resolves the contradiction with
> `master-orchestrator.md`, which declares F3 non-blocking.

### Scenario 3 — Quality Gate: Fidelity Assertion Fails (Priority: P1)

```gherkin
Given a prototype with 12 included screens
  And the agent generated page components for only 10 of them
 When the fidelity assertion runs (Angular Step 9.8 / React Step 6.5)
 Then the assertion reports expected: 12, generated: 10, missing_count: 2
  And the agent generates exactly the 2 missing screens and re-runs the assertion
  And after at most 3 iterations, if screens are still missing,
      assertion.status becomes "FAIL" and prototype_fidelity becomes "degraded"
  And the Handoff reports implementation.status: PARTIAL — never COMPLETED
```

---

## 5. Quality Gate Requirements

| Gate | Where | Blocking? | Rule |
|---|---|---|---|
| Scaffold Gate | Angular §2.17 · React 2.8 | Yes | `verify_scaffold.py --manifest {framework}`; any `blocking: true` file missing → HARD STOP |
| Fidelity — existence | Angular 9.8.1 · React 6.5.1 | Yes | `count(generated) == count(effective_status == "included")`, max 3 repair iterations |
| Fidelity — anti-stub | Angular 9.8.2 · React 6.5.2 | Yes | zero occurrences of the generic stub marker in generated templates |
| Business rules | Angular 9.8.5 · React 6.5.4 | Partially | 100% of `exact-form`/`unit` bound rules must carry `// Implements: BR-XXXX`; `bc-fallback` rules only report |
| Typecheck / build | Angular 9.9 · React 7.3/7.6 | Yes | `ng build` / `tsc --noEmit` + `vite build` must succeed; failures route to `@ava-stack-build-fixer` (max 2 iterations) |
| Unit tests | Angular 9.9.3 · React 7.4 | Yes, with one exemption | Runner exits non-zero below threshold. `TOOLCHAIN_UNAVAILABLE` (no Chrome for Karma) is reported and **non-blocking** |
| Consistency Gate | Angular 10.1 · React `## Consistency Verification Gate` | Yes | includes the new `CONVERSÃO DE PROTÓTIPO (P2C)` block |
| Security Compliance | both | No (reports) | control-by-control review against `security-architecture.md` |

**`COMPLETED` preconditions** — the Handoff must not report `COMPLETED` when
`screen_assertion == FAIL`, `business_rules_status == PARTIAL` due to a hard-binding failure, or
`unit_tests.status == BELOW_THRESHOLD`. `screen_assertion == SKIPPED` and
`unit_tests.status == TOOLCHAIN_UNAVAILABLE` are known, reported degradations and do **not** block.

---

## 6. Dependencies

| Depends on | Why |
|---|---|
| `ava-prototype` v1.2.0 (F3) | Produces `index.html`, `screen-list.md`, `design-tokens.json` — consumed, never mutated |
| `ava-asis-documentation` (F1) | Produces `business-rules-catalog.json`, the authoritative rule enumeration |
| Backend coder (F4, Step 3.5) | Produces/resolves the per-BC OpenAPI contract |
| `ava-stack-build-fixer` v1.1.0 | Repair loop for build and typecheck failures |
| `ava-stack-build-validator` v2.3.0 | Post-codegen build gate — unchanged; note that it does **not** run tests, which is why Step 9.9 / Step 7.4 exist |
| `verify_scaffold.py` | Scaffold gate; resolves `{manifest_id}-scaffold-manifest.yaml` relative to the repo root |

---

## 7. Exclusions

- **Vue and Blazor frontend coders are out of scope.** Both have zero prototype references today.
  The shared protocol was authored to be framework-independent so they can adopt it later without
  a rewrite, but this spec does not modify them.
- **`ava-prototype` is not modified.** Its output contract is already sufficient; F4 agents read
  `outputs/tobe/prototype/` and never write to it.
- **`build-validator-agent.md` is not modified.** Adding test execution to its containerised
  pipeline would require changing the `node:alpine` image (no Chrome). Test execution lives in the
  coder agents instead, with `TOOLCHAIN_UNAVAILABLE` as a first-class outcome.
- **No browser smoke run.** "Guarantee it works" is scoped to *compiles + unit tests pass*.
- **No pixel-perfect visual regression.** Fidelity is asserted structurally (screen count,
  archetype, literal title, constructs), not by image diff.

---

## 8. Assumptions

- `verify_scaffold.py` is invoked from the repository root. Its first manifest search path resolves
  to `src/shared/shared/data/scaffold-manifests` (non-existent), so resolution always falls through
  to the CWD-relative path.
- Node is available in the frontend output root for the assertion one-liner; a Python equivalent is
  the documented fallback for the pre-`npm install` case.
- `business_rules_catalog_generator.py` emits `form` for `category == "form_validation"` rules,
  making `rule.form == screen.asis_ref` a deterministic join.
- RNF04 caps the **prototype** at 15 includable screens per invocation, not the converter. Deferred
  screens are outside the assertion denominator by definition and must be listed explicitly so that
  `prototype_fidelity: full` is never misread as "the whole system was converted".
- The OpenAPI contract is authoritative over the prototype's `API:` comment for anything that
  becomes code.

---

## Success Criteria

Mechanical, grep-verifiable acceptance — same style as `specs/021`.

| # | Check | Expected |
|---|---|---|
| SC-01 | `grep -c "prototype" coder-react-frontend.md` | > 0 (was 0) |
| SC-02 | `grep -n "prototype-conversion-map.json"` in both agents | present |
| SC-03 | `grep -n "prototype_fidelity"` in both Handoff sections | present |
| SC-04 | `grep -n "HARD STOP"` inside Angular's `### Guardrail G-DT` | absent (replaced by P2C-W004) |
| SC-05 | `grep -n "business-rules-catalog.json" coder-react-frontend.md` | present (was 0) |
| SC-06 | `grep -n "api_contract_status" coder-react-frontend.md` | present (was 0) |
| SC-07 | `grep -n "^date:"` in both frontmatters | absent (Article II) |
| SC-08 | `grep -n "allowed-tools" coder-angular-frontend.md` | contains `Bash` |
| SC-09 | `grep -c "<li>{{ item.id }}</li>" coder-angular-frontend.md` | appears only inside PROIBIDO/assertion blocks, never as a template to emit |
| SC-10 | `ls src/shared/data/scaffold-manifests/react-scaffold-manifest.yaml` | exists |
| SC-11 | `grep -n -- "--manifest angular" orchestrator-stack.md` | absent for the frontend gate |
| SC-12 | `python src/shared/utils/verify_agent_observability.py --agent ava-stack-{react,angular}-frontend` | exit 0 (E3 satisfied) |
| SC-13 | `python src/shared/tools/generate_agent_wrappers.py --check` | exit 0 after regeneration |
| SC-14 | Pipeline run with prototype present | `counts.generated_conversions == counts.expected_conversions`, `assertion.status: PASS` |
| SC-15 | Pipeline run with `outputs/tobe/prototype/` renamed away | P2C-W001 emitted, `prototype_fidelity: none`, generation completes without error |
