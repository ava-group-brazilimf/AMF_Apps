# Agent Specification: Design Tokens Propagation — Prototype → Frontend Agents

**Feature Branch**: `008-design-tokens-propagation`
**Created**: 2026-07-08
**Status**: Draft
**Change Type**: modify-existing (3 agent files)
**PBI**: [#2333 — Propagação de design tokens do protótipo para agentes frontend (Angular e React)](https://dev.azure.com/...)
**Input**: "O agente prototype-agent.md gera wireframes HTML navegáveis mas não exporta um arquivo de
design tokens estruturado. Os agentes frontend (coder-angular-frontend.md e coder-react-frontend.md)
não leem os artefatos do protótipo como entrada, gerando CSS/SCSS que não respeita o espaçamento,
layout e estrutura visual definidos pelo protótipo."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (guardrail prose, comments, step descriptions) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> Agent frontmatter keys are English; values (description) are Portuguese.

---

## 1. Agent Identity — Three Agents Modified

This spec governs modifications to three existing agents. All are `modify-existing`.

### 1a. prototype-agent.md

| Field          | Value |
|----------------|-------|
| **Agent ID**   | `ava-prototype` |
| **Version**    | _(no version declared)_ → **`1.1.0`** (add missing version + MINOR: new output artifact) |
| **Phase**      | F4 (Prototype — sub-phase of F2) |
| **Module**     | `prototype` |
| **Role**       | Generates navigable HTML prototype. **Extended**: now also exports `design-tokens.json` alongside the HTML wireframes. |
| **Skill**      | `ava-prototype` (already registered) |
| **Dispatch**   | user-facing via SKILL.md + internal via `ava-tobe-orchestrator` |
| **Target file**| `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` |

### 1b. coder-angular-frontend.md

| Field          | Value |
|----------------|-------|
| **Agent ID**   | `ava-stack-angular-frontend` |
| **Version**    | `1.0.0` → **`2.0.0`** (MAJOR: new mandatory inputs added to Input Contract) |
| **Phase**      | F3 (Tech Stack — codegen) |
| **Module**     | `tech-stack` |
| **Role**       | Generates production-ready Angular frontend. **Extended**: reads `prototype_screens` and `design_tokens` from Input Contract before generating any CSS/SCSS. |
| **Skill**      | `ava-stack-angular-frontend` (already registered) |
| **Dispatch**   | user-facing via SKILL.md + internal via `ava-stack-orchestrator` |
| **Target file**| `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` |

### 1c. coder-react-frontend.md

| Field          | Value |
|----------------|-------|
| **Agent ID**   | `ava-stack-react-frontend` |
| **Version**    | `0.1.0-stub` → **`0.2.0-stub`** (MINOR: input contract stubs added for future implementation) |
| **Phase**      | F3 (Tech Stack — codegen) |
| **Module**     | `tech-stack` |
| **Role**       | Stub agent for React frontend. **Extended**: Input Contract now declares `prototype_screens` and `design_tokens` as required inputs (enforced when the stub is promoted to full implementation). |
| **Skill**      | `ava-stack-react-frontend` (already registered) |
| **Dispatch**   | internal via `ava-stack-orchestrator` |
| **Target file**| `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` |

> **`modify-existing` notes (all three agents)**:
> - No new files created. Edit the three existing agent `.md` files only.
> - `module.yaml` entries already exist — Category 4 (module registration) tasks cover version bumps only.
> - `SKILL.md` files already exist — Category 1.5 (skill creation) is N/A.

---

## 2. Problem Statement

### Root Cause
The `ava-prototype` agent produces navigable HTML wireframes that encode spacing,
sidebar widths, header heights, color palettes, and typography as inline HTML
attributes and CSS custom properties. This visual contract is **never exported**
as a machine-readable artifact.

The `ava-stack-angular-frontend` and `ava-stack-react-frontend` agents generate
CSS/SCSS without reading any prototype artifact, causing a **visual divergence**
between what stakeholders approved (the prototype) and what gets deployed (the
generated frontend). Concrete failure: Sophia project CSS used hardcoded values
that differed from the prototype's sidebar width and header height.

### What Changes in Each Agent

**prototype-agent.md**:
- Extracts design tokens from the HTML wireframes it generates (or from
  `design-system.md` if already read) and writes them to `design-tokens.json`.
- `design-tokens.json` captures: `spacing`, `colors`, `typography`, `layout`
  (sidebar width, header height, content padding, etc.).

**coder-angular-frontend.md**:
- Adds `prototype_screens` and `design_tokens` as mandatory inputs in the
  Input Contract (HARD STOP if absent).
- Adds a guardrail (**G-DT**) executed before any CSS/SCSS is written: reads
  `design-tokens.json` and resolves all spacing, color, and dimension values
  from the token map instead of hardcoding them.
- AppShell, Sidebar, and Header layout components are explicitly called out
  as requiring token-derived values for widths, heights, and paddings.

**coder-react-frontend.md**:
- Adds the same Input Contract entries (stub-level: documented for future
  implementation, not enforced at stub response time).
- Adds the same G-DT guardrail stub (not enforced until stub is promoted).

---

## 3. Output Contract Changes

### 3a. prototype-agent.md — New Output Added

```yaml
# BEFORE
outputs:
  prototype:    "projects/{project_name}/outputs/tobe/prototype/"
  demo_script:  "projects/{project_name}/outputs/tobe/prototype/demo-script.md"
  figma_spec:   "projects/{project_name}/outputs/tobe/prototype/figma-spec.md"
  screen_list:  "projects/{project_name}/outputs/tobe/prototype/screen-list.md"

# AFTER (design_tokens added)
outputs:
  prototype:      "projects/{project_name}/outputs/tobe/prototype/"
  demo_script:    "projects/{project_name}/outputs/tobe/prototype/demo-script.md"
  figma_spec:     "projects/{project_name}/outputs/tobe/prototype/figma-spec.md"
  screen_list:    "projects/{project_name}/outputs/tobe/prototype/screen-list.md"
  design_tokens:  "projects/{project_name}/outputs/tobe/prototype/design-tokens.json"
```

### design-tokens.json — Mandatory Schema

```json
{
  "schema_version": "1.0",
  "generated_by": "ava-prototype",
  "project_name": "{project_name}",
  "spacing": {
    "base_unit": "8px",
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "xxl": "48px"
  },
  "colors": {
    "primary":     "#value",
    "secondary":   "#value",
    "background":  "#value",
    "surface":     "#value",
    "on_primary":  "#value",
    "error":       "#value",
    "warning":     "#value",
    "success":     "#value"
  },
  "typography": {
    "font_family_base":    "value",
    "font_family_heading": "value",
    "font_size_base":      "16px",
    "font_size_sm":        "14px",
    "font_size_lg":        "20px",
    "line_height_base":    "1.5"
  },
  "layout": {
    "sidebar_width":        "value (px or rem)",
    "sidebar_collapsed_width": "value",
    "header_height":        "value",
    "content_padding":      "value",
    "max_content_width":    "value"
  }
}
```

Values are extracted from the prototype HTML/CSS generated in the same execution.
If a value is not determinable from the prototype, the agent uses the design-system.md
token as fallback and marks the field with `"source": "design-system-fallback"`.

### 3b. coder-angular-frontend.md — New Inputs (no output change)

```yaml
# ADDED to Input Contract — CRÍTICOS section
prototype_screens:  file  # projects/{project_name}/outputs/tobe/prototype/screen-list.md
                          # HARD STOP se ausente: execute ava-prototype first
design_tokens:      file  # projects/{project_name}/outputs/tobe/prototype/design-tokens.json
                          # HARD STOP se ausente: execute ava-prototype first
```

Output contract remains unchanged.

### 3c. coder-react-frontend.md — New Inputs (stub-level, no enforcement)

Same input declarations as Angular, documented under a `## Planned Input Contract`
section in the stub body.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Prototype exports design-tokens.json (Priority: P1)

**Story**: Como orquestrador de migração, quero que o ava-prototype exporte
design-tokens.json após gerar wireframes, para que os agentes frontend possam
consumir os tokens de design sem precisar reimplementar a lógica de extração.

**Acceptance Scenarios**:

1. **Given** a prototype execution completes with at least one HTML wireframe
   generated, **When** the agent finalizes its Output Contract, **Then**
   `design-tokens.json` exists at
   `projects/{project_name}/outputs/tobe/prototype/design-tokens.json`.
2. **Given** the above, **Then** the JSON file contains all four top-level keys:
   `spacing`, `colors`, `typography`, and `layout`.
3. **Given** the prototype HTML uses `--sidebar-width: 240px` as a CSS variable,
   **Then** `design_tokens.layout.sidebar_width` equals `"240px"`.
4. **Given** `design-system.md` is present but the prototype HTML does not
   specify a sidebar width, **Then** the agent falls back to `design-system.md`
   and marks the field `"source": "design-system-fallback"`.

---

### Scenario 2 — Angular agent blocks when design_tokens is absent (Priority: P1)

**Story**: Como guardrail de qualidade, quero que o agente Angular pare com
HARD STOP se design-tokens.json não existir, para evitar geração de CSS
desconectado do protótipo.

**Acceptance Scenarios**:

1. **Given** `design-tokens.json` does not exist at the expected path and
   `prototype_screens` is also absent, **When** the Angular agent runs its
   Pre-Flight Check, **Then** both inputs are marked `❌ MISSING` and the
   decision is `BLOCKED`.
2. **Given** the BLOCKED decision, **Then** the agent emits a message stating
   which agent must run first (`ava-prototype`) and does **not** generate any
   CSS, SCSS, or TypeScript file.
3. **Given** only `design_tokens` is missing but `prototype_screens` is present,
   **Then** the agent still blocks (both are mandatory).

---

### Scenario 3 — Guardrail G-DT: layout components use token-derived values (Priority: P1)

**Story**: Como revisor de qualidade CSS, quero que AppShell, Sidebar e Header
usem valores derivados dos design tokens, para que o CSS gerado seja fiel ao
protótipo aprovado pelo cliente.

**Acceptance Scenarios**:

1. **Given** `design_tokens.layout.sidebar_width = "240px"`, **When** the Angular
   agent generates the Sidebar component SCSS, **Then** the generated rule uses
   `width: var(--sidebar-width, 240px)` (or equivalent token reference) and does
   **not** contain a hardcoded `width: 240px` literal outside of a `:root` token
   declaration.
2. **Given** `design_tokens.layout.header_height = "64px"`, **When** the agent
   generates the Header component, **Then** the SCSS uses `height: var(--header-height, 64px)`.
3. **Given** `design_tokens.spacing.md = "16px"`, **When** the agent generates
   content padding for the AppShell, **Then** `padding` values reference
   `var(--spacing-md, 16px)` rather than hardcoded pixel values.
4. **Given** the above, **Then** a `:root` CSS block at the application level
   declares all token variables, sourced exclusively from `design-tokens.json`.

---

### Scenario 4 — React stub acknowledges the input contract (Priority: P2)

**Story**: Como desenvolvedor que futuramente implementará o agente React,
quero que o contrato de inputs já esteja documentado no stub, para que a
implementação não quebre o pipeline de tokens.

**Acceptance Scenarios**:

1. **Given** the React stub agent is invoked after prototype execution,
   **When** it emits its stub response, **Then** the response includes a
   `## Planned Input Contract` note referencing `design-tokens.json`.
   _(Portuguese implementation artifact: `## Contrato de Entrada Planejado (Design Tokens)` — per Article V)_
2. **Given** the stub is eventually promoted to a full implementation,
   **Then** the G-DT guardrail documented in the stub body becomes active
   without requiring additional spec work.

---

### Scenario 5 — CSS fidelity validation for Sophia project (Priority: P1)

**Story**: Como QA do projeto Sophia, quero verificar que o CSS gerado
corresponde aos espaçamentos e dimensões do protótipo aprovado.

**Acceptance Scenarios**:

1. **Given** the Sophia project prototype defines `sidebar_width = "260px"`
   and `header_height = "56px"`, **When** the Angular agent generates the
   Sophia frontend with the new G-DT guardrail active, **Then** the generated
   SCSS contains `:root` declarations `--sidebar-width: 260px` and
   `--header-height: 56px` derived from `design-tokens.json`.
2. **Given** the above, **Then** no component SCSS file contains a hardcoded
   sidebar or header dimension that contradicts the token values.

---

## 5. Quality Gate Requirements

- [ ] Three agent `.md` files modified — no new files created (Article II)
- [ ] `prototype-agent.md` gains version `1.1.0` in frontmatter (currently undeclared)
- [ ] `coder-angular-frontend.md` version bumped `1.0.0` → `2.0.0` (MAJOR: new mandatory inputs)
- [ ] `coder-react-frontend.md` version bumped `0.1.0-stub` → `0.2.0-stub` (MINOR: new stub declarations)
- [ ] `design-tokens.json` schema documented in prototype-agent Output Contract (Article II)
- [ ] BDD scenarios cover: export, HARD STOP, G-DT guardrail, stub acknowledgment, CSS fidelity (Article VI)
- [ ] No new output paths break existing F3 downstream consumers (Article III)
- [ ] `module.yaml` version entries updated for all 3 agents (Article IV)
- [ ] No technology versions hardcoded in any new spec or agent text (Article I)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency                    | Agent ID                  | Reason |
|-------------------------------|---------------------------|--------|
| Prototype execution           | `ava-prototype`           | Must produce `design-tokens.json` before Angular/React agents run |
| TO-BE architecture (design system) | `ava-tobe-architecture-design` | Source of design-system.md used as fallback for token extraction |
| Angular frontend (current)    | `ava-stack-angular-frontend` | Modified agent; must not break existing Angular codegen contract |

---

## 7. Exclusions

- Token extraction from Figma files — handled by `ava-prototype` only when figma-spec.md is present
- CSS-in-JS token consumption (e.g., styled-components, emotion) — out of scope; Angular uses SCSS
- Automatic token diff between AS-IS and TO-BE — handled by `ava-devops-compare-version`
- React full implementation (CSS token consumption) — blocked until stub is promoted; tracked in `stub-registry.yaml`

---

## 8. Assumptions

- `design-system.md` exists at `projects/{project_name}/outputs/tobe/docs/design-system.md` before prototype executes (already required by prototype Pre-Execution step 1)
- The `ava-prototype` agent always executes before frontend codegen agents in the `ava-stack-orchestrator` pipeline
- SCSS custom properties (CSS variables) are the canonical token delivery mechanism for Angular; no CSS-in-JS token library is introduced
- `design-tokens.json` schema version `1.0` is stable for this PBI; additions are additive (MINOR bumps only)
- The Sophia project is used as the validation case for Scenario 5; its prototype must be regenerated with this updated agent before validation

---

## Success Criteria

| Criterion | Measure |
|-----------|---------|
| `design-tokens.json` exported | File exists and validates against the mandatory schema after any prototype execution |
| Angular agent HARD STOP enforced | Angular agent blocks with `BLOCKED` decision when `design-tokens.json` is absent |
| G-DT guardrail active | AppShell, Sidebar, Header SCSS contains no hardcoded dimension values — all sourced from `:root` token declarations |
| React stub updated | `coder-react-frontend.md` documents the planned input contract and G-DT stub |
| No regression | Existing Angular codegen for projects that already ran `ava-prototype` is unaffected (tokens are consumed, not replaced) |
| Sophia CSS fidelity | Sidebar width and header height in generated SCSS match `design-tokens.json` values derived from the Sophia prototype |
