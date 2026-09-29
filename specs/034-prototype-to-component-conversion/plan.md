# Agent Implementation Plan: Prototype → Component Conversion (P2C)

**Branch**: `034-prototype-to-component-conversion` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Frontend coder agents ignore the navigable prototype produced in F3, so the generated
application has no connection to the design already approved with stakeholders.

---

## Summary

| Field | Value |
|---|---|
| **Agents modified** | `ava-stack-angular-frontend` · `ava-stack-react-frontend` · `ava-stack-orchestrator` (bugfix) |
| **Phase** | F4 (Tech Stack / Codegen) |
| **Module** | `tech-stack` |
| **Primary Requirement** | The first step of either frontend agent consumes the F3 prototype and converts its navigation structure into components per the language's coding guidelines; missing prototype degrades with WARN instead of blocking |
| **Technical Approach** | One framework-independent shared include (`prototype-conversion-protocol.md`) + per-agent construct mapping + a deterministic file-existence assertion driven by `expected_artifacts[]` written *before* generation |
| **Change Type** | `modify-existing` — 3 agent files, MAJOR/MAJOR/none · plus 3 new shared (non-agent) files |

---

## Constitution Check

### Pre-implementation Gates

- [x] **Article I** — No technology versions hardcoded: package versions continue to be resolved by
  `@ava-stack-docs-researcher`; `coverage_threshold` reads from `project-config.yaml` (default 80);
  design token defaults are CSS values, not framework versions.
- [x] **Article II** — Frontmatter contains ONLY `name`, `version`, `description`, `allowed-tools`.
  **This spec fixes two pre-existing violations**: the `date:` key is removed from both agents, and
  `Bash` is added to Angular's `allowed-tools` (Steps 2.17/10.1/11 already invoked it).
- [x] **Article II** — Agent names match `^ava-[a-z0-9-]+$`: unchanged.
- [x] **Article II** — Output paths use lowercase `{project_name}`: verified in both Output Contracts.
- [x] **Article III** — Phase placement valid: both agents remain F4; they consume F3 outputs
  (adjacent phase) and F1 business rules via published artifacts, never by re-reading legacy code.
- [x] **Article IV** — `module.yaml` diff prepared — see §5. Both agents already registered; only the
  module version changes.
- [x] **Article V** — Agent body language is Brazilian Portuguese: all new guardrails, steps and
  warning texts are pt-BR. This planning document is English by convention.
- [x] **Article VI** — BDD scenarios written for nominal (prototype present → `full`), edge
  (prototype absent → `P2C-W001` → `none`, continues), and gate (assertion fails after 3 retries →
  `degraded` + `PARTIAL`) paths — spec §4.
- [x] **Article VII** — Security sub-pipeline impact assessed: the security sub-pipeline is
  F1-scoped and untouched. F4 impact is additive — React gains a Security Compliance Review Gate it
  never had, and the XSS/secrets/PII invariants are now explicit in both agents.
- [x] **Article I** — No technology versions hardcoded in the new shared files: the React patterns
  reference documents APIs and conventions, never pinned versions.

### Architecture Gates

- [x] **Article IX** — Clean Architecture layer ordering respected: React output keeps
  `domain → application → infrastructure → ui`; Zod schemas live in `domain/`, hooks in
  `application/`, HTTP clients in `infrastructure/`, pages in `ui/`. Angular keeps the smart/dumb
  split — only `*-page.component.ts` touches the Store.
- [x] **Article VIII** — `trace_id` propagation documented: both agents copy `trace_id` unmodified
  into `prototype-conversion-map.json`, `business-rules-implementation-frontend.json`,
  `implementation-status.json` and the Handoff.
- [x] **Article IV** — Module-level `module.yaml` diff included — §5.
- [x] **Article X** — `CHANGELOG.md` entry prepared (MAJOR ×2).
- [x] **Article XI** — Skill/Agent split declared: both SKILL.md files already exist and route by
  agent id; no routing or bootstrap change is required, so only the agent `.md` bodies change.

---

## 1. Technical Context

The prototype is a *single* self-contained `index.html` with sibling `<section id="view-*" class="view">`
blocks, plus a `screen-list.md` manifest and a `design-tokens.json`. Two facts drive the design:

1. **The two prototype artifacts can disagree.** `screen-list.md` is authoritative for *which*
   screens exist and their status; `index.html` is authoritative for *what* each screen contains.
   A 7-case discrepancy matrix (protocol §2.4) resolves every combination into a single
   `effective_status`, which is what the assertion counts.
2. **The assertion must not require new tooling.** Writing `expected_artifacts[]` into the
   conversion map *before* generation reduces the check to file existence, runnable with a `node -e`
   one-liner from the output root.

Duplicating the parsing, matrix, schema, rule-binding and API-join prose into both agents would
guarantee drift, so it lives in one shared include and each agent carries only its own construct
mapping and step wiring.

---

## 2. Phase Placement

Both agents stay in **F4**, dispatched by `ava-stack-orchestrator` on
`tobe_stack.frontend_framework`. No phase boundary is crossed: F3 outputs are consumed as published
artifacts, and F1 business rules come from `business-rules-catalog.json` — never by re-reading
legacy source.

The one ordering constraint added: the prototype inventory step must run **before** the context
variables are derived, because a prototype screen can belong to a bounded context absent from
`bounded-context-map.md`. Hence Angular's new sub-step is `1.2d` (after 1.2c, before 1.3) and
React's is `1.4` (before the PRE-FLIGHT display).

---

## 3. Clean Architecture Alignment

| Layer | Angular | React |
|---|---|---|
| Domain | `src/app/{bc}/models/` | `src/{bc}/domain/` (types + Zod schemas) |
| Application | `src/app/store/{bc}/` (NgRx) | `src/{bc}/application/hooks/` |
| Infrastructure | `src/app/{bc}/{bc}.service.ts` | `src/{bc}/infrastructure/api/` |
| Presentation | `src/app/{bc}/pages/{screen_id}/` | `src/{bc}/ui/pages/` |

No layer references a layer above it. Shared UI components (DS-0xx / RX-0xx) are presentation-only
and dumb — they receive props and emit events, never fetching data or reading stores.

**Complexity note:** `DataTableComponent` / `DataTable<T>` renders the empty-state component
internally. This is a presentation-to-presentation composition, not a layer violation, and it is
what guarantees the mandatory empty state on every list without repeating it in each page.

---

## 4. Agent File Structure

### `coder-angular-frontend.md` (2.0.0 → 3.0.0)

| Action | Location | Change |
|---|---|---|
| MODIFY | frontmatter | remove `date:`, add `Bash`, bump version |
| MODIFY | `## Input Contract` | prototype inputs → new `# OPCIONAIS — degradam com WARN` group; add `prototype_index`, `business_rules_catalog`, `coverage_threshold`, `p2c_protocol` |
| MODIFY | `## Output Contract` | add `prototype_conversion_map`, `screen_page`, `screen_spec`, BR json |
| MODIFY | `#### 1.4` PRE-FLIGHT | `[CRÍTICO]` → `[OPCIONAL]`; move to the WARNING list with the rationale |
| **NEW** | `#### 1.2d` | prototype inventory (protocol passes P1–P4), writes the map with `phase: "planned"` |
| MODIFY | `#### 1.3` | add `{screens}`, `{screens_by_bc}`, `{prototype_fidelity}`, `{coverage_threshold}`; BCs become a union |
| MODIFY | `### Guardrail G-DT` Passo 1 | HARD STOP → P2C-W004 fallback chain + `design_tokens_source` |
| **NEW** | `### Guardrail G-P2C` | construct mapping, archetype rules, anti-stub marker — a guardrail, not a numbered step, so **zero renumbering** |
| **NEW** | `#### 5.9.1–5.9.6` | DS-010..DS-013, Toast/Confirm services, correlation-id interceptor edit. Decimal insertion preserves 5.10–5.13 |
| MODIFY | `#### 5.2`, `5.7`, `5.12`, `5.13` | optional inputs on DS-002/DS-007; barrel and file counts |
| **REPLACE bodies, keep numbers** | `#### 7.3`–`7.6` | one page per screen, archetype-driven template, per-screen routes |
| MODIFY | `#### 7.7` | operation set = union(contract, screen metadata) + divergence markers |
| MODIFY | `#### 9.1`, `9.2` | `navItems` from `shell.nav_items`, grouped |
| MODIFY | `#### 9.5.1` | `codeCoverageReporters` + `karma.conf.js` headless launcher |
| **NEW** | `#### 9.5.6` | spec per converted screen, incl. one `it()` per bound BR |
| **NEW** | `### Step 9.8` | fidelity assertion + repair loop + BR assertion |
| **NEW** | `### Step 9.9` | build & unit test execution |
| MODIFY | `#### 10.1`–`10.3`, `## Handoff`, `## Consistency Verification Gate` | P2C block, screen-level ChangedScreens, new Handoff fields; delete the now-done `<ul>` TODO |
| MODIFY | `### Step 11` | `--version 3.0.0` |

**Left untouched:** Steps 2, 3, 4, 6, 8, 9.5.0–9.5.5, Security Compliance Review Gate, G-DATE,
Required Scaffolding Files, i18n.

### `coder-react-frontend.md` (1.0.0 → 2.0.0)

Rewritten from 215 lines to a full agent. Gains the P2C protocol **and** the parity sections it
never had: `## Padrões Obrigatórios`, PRE-FLIGHT, `Guardrail G-DT`, `Guardrail G-P2C-React`,
business rules (1.5), API contract (1.6), Scaffold Gate (2.8), test infrastructure (2.7),
RX-001..RX-014 (Step 3), per-BC data layer (Step 4), converted screens (Step 5), router/AppShell
(Step 6), fidelity assertion (6.5), quality gate (Step 7), delivery docs (Step 8),
`## Consistency Verification Gate`, `## Handoff`, `## Security Compliance Review Gate`,
`## Accessibility Invariants`, `## Testing Requirements`.

### New shared files

| Path | Notes |
|---|---|
| `shared/prototype-conversion-protocol.md` | Framework-independent: authority rules, passes P1–P4, discrepancy matrix, map schema, BR binding, API join, assertion, `P2C-W001..W009`, `prototype_fidelity` enum, Handoff fields, RNF04 note |
| `src/shared/data/patterns/react/react-patterns-reference.md` | Mirrors the 6 sections of the Angular reference + TanStack query keys and Zustand slice conventions |
| `src/shared/data/scaffold-manifests/react-scaffold-manifest.yaml` | Flat shape only (`path`/`category`/`blocking`/`error_if_missing`) — the no-PyYAML fallback parser recognises nothing else |

---

## 5. module.yaml Impact

`src/modules/ava-fabric-agents/tech-stack/module.yaml`:

```diff
-version: "1.4.0"
+version: "1.5.0"
```

Both agents already appear under `agents:` with the correct `routing_key` (`angular`, `react`), so
no entry is added or removed. Per the spec template, Category 4 is a version bump only.

The three new files are **not agents** — they are a shared include and two data references — so
they require no `module.yaml` entry and are invisible to `agent_registry.py`.

---

## 6. Observability & Trace Propagation

- `trace_id` is copied without mutation from `project-config.yaml` into
  `prototype-conversion-map.json`, `business-rules-implementation-frontend.json`,
  `implementation-status.json` and the Handoff (Article VIII).
- The observability block literal must match the frontmatter or
  `verify_agent_observability.py` rule **E3** fails. Both were updated:
  Angular `--version 3.0.0`, React `--version 2.0.0`.
- `--phase F4` is unchanged and matches `PHASE_BY_MODULE["tech-stack"]`.
- Neither agent writes to stdout in a way that corrupts structured output; the new ASCII gate boxes
  are agent-response text, consistent with existing practice in this module.

---

## 7. Schema Changes

New contract: `contracts/prototype-conversion-map.schema.json` (JSON Schema draft-07), modelled on
`specs/008-design-tokens-propagation/contracts/design-tokens.schema.json` — `additionalProperties:
false` at every level, `const` on `schema_version` and `artifact_id`, repeated primitives factored
into `definitions`.

`react-scaffold-manifest.yaml` reuses the existing (unversioned, implicit) manifest shape validated
by `verify_scaffold.py`; no schema file is added for it because the Angular and dotnet manifests
have none either.

---

## 8. Implementation Phases (Task Categories)

| Phase | Category | Content |
|---|---|---|
| 0 | Cat 1 | Frontmatter, versions, Input/Output contracts |
| 1 | — | This spec, plan and tasks (pre-done) |
| 2 | Cat 2 | Agent bodies: shared protocol, guardrails, steps, gates, Handoff |
| 3 | Cat 3 | Shared data: react patterns reference, react scaffold manifest, JSON schema |
| 4 | Cat 4 | `module.yaml` version bump |
| 5 | Cat 5 | `checklists/requirements.md` |
| 6 | Cat 6 | Acceptance validation — the SC-01..SC-15 chain |
| 7 | Cat 7 | `CHANGELOG.md`, `docs/agents-catalog.md`, wrapper regeneration |

Ordering rationale: the shared protocol lands first because both agents reference it; the Angular
read-only phase (contracts + 1.2d + G-DT + G-P2C) is safe to land alone because it changes no
generated output; the Steps 7.3–7.6 replacement is the behaviour-changing commit and is isolated.

---

## 9. Complexity Tracking

| Complexity | Why it is justified | Simpler alternative rejected because |
|---|---|---|
| A separate shared include instead of inlining | ~250 lines of framework-independent prose would otherwise be duplicated across two agents | Duplication guarantees drift; the repo already has the `@frontend-governance` include convention |
| Writing the map twice (`planned` then `verified`) | Makes the assertion a pure file-existence check | Deriving expected paths at assert time would re-run the whole parsing and could disagree with what generation actually planned |
| Two assertions (existence + anti-stub) | A file can exist and still be the generic stub | Existence alone produced a false positive precisely for the bug this spec fixes |
| `TOOLCHAIN_UNAVAILABLE` as a first-class outcome | Karma needs a real browser; `build-validator` runs on `node:alpine` without Chrome | Failing the run would block every environment without Chrome; silently skipping would misreport an unverified build as verified |
| Hard/soft split in the business-rule assertion | `bc-fallback` bindings are heuristic | Failing the whole run on a heuristic binding would be dishonest; ignoring them entirely would hide real coverage gaps |
| Angular MAJOR rather than MINOR | Input criticality and output layout both change (Article X) | A MINOR bump would understate a breaking change in generated project structure |

---

## 10. Test Strategy

**Agent-level (this repo):** the SC-01..SC-13 grep and tooling checks in spec §Success Criteria —
`agent_registry.py`, `verify_agent_observability.py`, `generate_agent_wrappers.py --check`,
`verify_scaffold.py --manifest react`.

**Pipeline-level (generated projects):**

1. Project **with** prototype → `counts.generated_conversions == counts.expected_conversions`,
   `assertion.status: PASS`, `prototype_fidelity: full`, zero `<li>{{ item.id }}</li>`, unit tests
   green at or above threshold (SC-14).
2. Same project with `outputs/tobe/prototype/` renamed away → `P2C-W001` box,
   `prototype_fidelity: none`, `assertion.status: SKIPPED`, generation completes (SC-15).
3. A React project to exercise `--manifest react` and the corrected orchestrator gate.

**Generated-code-level:** every converted screen carries a spec asserting the literal prototype
title — the cheapest real fidelity check available, and the one that fails first if a generic
template ever comes back.
