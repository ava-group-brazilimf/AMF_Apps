# Research: Design Tokens Propagation — Prototype → Frontend Agents

**Feature**: `008-design-tokens-propagation`
**Date**: 2026-07-08

---

## Decision 1 — Token extraction strategy in `prototype-agent.md`

**Decision**: Extract tokens from the CSS custom properties defined in `design-system.md` (which
the prototype already reads as Pre-Execution step 1), not by parsing the generated HTML output.

**Rationale**: `design-system.md` is the **authoritative source** for visual tokens per the
prototype's existing Regras de Consistência section (`--color-primary-500`, `--font-family-base`,
`--space-4`). Parsing HTML output would require brittle regex on CSS inline strings. Reading
`design-system.md` (already loaded in context) is deterministic and matches the existing Pre-Execution
reading protocol.

**Alternatives considered**:
1. Parse generated HTML wireframes for inline CSS values — rejected: fragile, order-dependent, fails
   when tokens are referenced by variable name rather than resolved value.
2. Require a separate `design-tokens-source.json` input artifact — rejected: adds upstream dependency;
   the data is already in `design-system.md`.
3. Hardcode fallback values — rejected: violates Article I.

**Fallback rule**: When a specific layout token (e.g., `sidebar_width`) is not declared in
`design-system.md`, the agent records `"source": "prototype-derived"` using the measured
HTML attribute, or `"source": "default"` with a documented default value.

---

## Decision 2 — CSS custom property delivery in Angular SCSS

**Decision**: Generate a `:root` block in the application's global `styles.scss` that declares all
tokens from `design-tokens.json` as CSS custom properties. Component SCSS files reference these
properties using `var(--token-name, fallback)` syntax.

**Rationale**: CSS custom properties are the native Angular SCSS pattern — no new library dependency.
They work with Angular Material theming. They are accessible to all components without import
chains. The fallback value in `var()` ensures the component renders safely even if the `:root`
declaration is missing (e.g., in unit test environments).

**Alternatives considered**:
1. SCSS variables (`$sidebar-width: 240px`) — rejected: compile-time only, cannot be overridden
   at runtime by theming systems or client customization.
2. Angular CDK token injection — rejected: adds CDK version dependency; violates Article I for
   agents that must not hardcode library versions.
3. TypeScript constants (`export const SIDEBAR_WIDTH = '240px'`) — rejected: forces TypeScript
   imports in SCSS files (unsupported pattern).

**Token-to-CSS-property naming convention**:
```
design_tokens.layout.sidebar_width      → --sidebar-width
design_tokens.layout.header_height      → --header-height
design_tokens.layout.content_padding    → --content-padding
design_tokens.spacing.xs                → --spacing-xs
design_tokens.spacing.sm                → --spacing-sm
design_tokens.spacing.md                → --spacing-md
design_tokens.spacing.lg                → --spacing-lg
design_tokens.colors.primary            → --color-primary
design_tokens.colors.secondary          → --color-secondary
design_tokens.typography.font_family_base → --font-family-base
```

---

## Decision 3 — G-DT guardrail position within `coder-angular-frontend.md`

**Decision**: Insert G-DT immediately after the Pre-Flight Check block and before any code
generation step. Position: after "Input Contract" validation, before the first
`## Scaffolding` section.

**Rationale**: Mirrors the G10/G11 pattern in `coder-dotnet-backend.md` — pre-generation
gates execute before any file is written. This ensures that if `design-tokens.json` is
absent, zero files are produced and the HARD STOP message names the blocking agent
(`ava-prototype`).

**G-DT execution logic**:
```
1. READ projects/{project_name}/outputs/tobe/prototype/design-tokens.json
   → ABSENT: HARD STOP — "Execute ava-prototype first to generate design-tokens.json"
   → PRESENT: parse JSON, extract top-level keys

2. Validate schema_version == "1.0" (warn on mismatch, do not block)

3. Build CSS token map:
   FOR EACH token in layout, spacing, colors, typography:
     map to CSS custom property name (see Decision 2 naming convention)

4. Pass token map to code generation context — subsequent steps reference
   var(--token-name, fallback) instead of hardcoded values
```

---

## Decision 4 — React stub (`coder-react-frontend.md`) scope

**Decision**: Add only documentation to the stub — a `## Planned Input Contract` section
and a `## Guardrail G-DT (Planejado)` stub section. The stub response protocol (which returns
`implementation.status: STUB`) is unchanged. No enforcement occurs.

**Rationale**: The React stub explicitly declares `NOT IMPLEMENTED`. Enforcing G-DT would block
React frontend generation for projects that already have `design-tokens.json` — causing
unnecessary failures. The documentation ensures forward compatibility when the stub is promoted.

---

## Decision 5 — module.yaml updates

**prototype/module.yaml**:
- Add `design-tokens.json` to `outputs.files` list.
- Update `version` from `"1.0.0"` to `"1.1.0"`.

**tech-stack/module.yaml**:
- Agent `ava-coder-angular-frontend`: add `version: "2.0.0"` inline comment or note.
  (module.yaml tracks agent IDs and file paths; version is declared in the agent frontmatter itself.)
- Update module `version` from `"1.3.0"` to `"1.4.0"` (MINOR: new mandatory input contract).

---

## Decision 6 — HARD STOP display format (Pre-Flight Check)

**Decision**: Use the existing Pre-Flight Check panel format already defined in
`coder-angular-frontend.md` (the `╔══╣ PRE-FLIGHT CHECK ╠══╗` box at line ~399).
Extend the Input Contract section of that check to include `prototype_screens` and
`design_tokens` rows.

**No new display format needed** — reuse the existing panel structure.

---

## Unknowns Resolved

| Unknown | Resolution |
|---------|-----------|
| Where is `design-system.md` consumed in prototype? | Pre-Execution step 1 — agent reads it before generating any wireframe. Tokens already in context. |
| Does prototype always run before Angular frontend? | Per pipeline sequence (Article III), F4 Prototype is a sub-phase of F2. F3 frontend codegen runs after F2. `ava-prototype` must run before `ava-stack-angular-frontend`. |
| Is `allowed-tools` change needed? | `prototype-agent.md` currently has `Read, Write, Edit` — sufficient to write `design-tokens.json`. No change needed. |
| Does SKILL.md need updating? | No — skill files are routing wrappers. No input/output routing changes in the SKILL.md layer. |
| Angular `styles.scss` already generated? | Yes, `coder-angular-frontend.md` generates it as part of the Required Scaffolding Files. The G-DT guardrail adds the `:root` token block to this file. |
