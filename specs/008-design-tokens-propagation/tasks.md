# Agent Development Tasks: Design Tokens Propagation — Prototype → Frontend Agents

**Plan**: `specs/008-design-tokens-propagation/plan.md`
**Agents**: `ava-prototype` · `ava-stack-angular-frontend` · `ava-stack-react-frontend` | **Phases**: F4 · F3 | **Modules**: `prototype` · `tech-stack`

> Change type: `modify-existing` — 3 agent files
> Targets: `prototype-agent.md` (1.1.0) · `coder-angular-frontend.md` (2.0.0) · `coder-react-frontend.md` (0.2.0-stub)
> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 3 is N/A (no schema changes). Categories 5, 6, 7 can all run in parallel after Category 2 completes.
> Plan §8 phase-to-category mapping: Phase 0 = Cat 1 · Phase 1 (specs) = pre-done · Category 2 = Cat 2 body · Category 4 = Cat 4 · Category 5 = Cat 6 validation · Category 7 = Cat 7 docs.

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before Category 2. Three agents; all are `modify-existing` so no new files are created.
Only `version` fields change in frontmatter. Output Contract: one new entry in `prototype-agent.md` only.
SKILL.md files for all three agents remain unchanged.

- [X] **1\.1** Open `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` and verify its frontmatter block contains **only** the four allowed fields (`name`, `version`, `description`, `allowed-tools`). Note: this file currently has **no `version:` field** — that is the defect to fix. Confirm no extra keys (`phase`, `module`, `inputs`, `outputs`, `dependencies`) are present.

- [X] **1\.2** Add `version: "1.1.0"` to the frontmatter of `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. Insert it as the third line of the frontmatter block, after `name:` and before `description:`. The resulting block must be:
  ```yaml
  ---
  name: ava-prototype
  version: "1.1.0"
  description: |
    ...
  allowed-tools: Read, Write, Edit
  ---
  ```

- [X] **1\.3** In the `## Output Contract` section of `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`, add `design_tokens` as a new output entry. The updated YAML block must be:
  ```yaml
  outputs:
    prototype:      "projects/{project_name}/outputs/tobe/prototype/"
    demo_script:    "projects/{project_name}/outputs/tobe/prototype/demo-script.md"
    figma_spec:     "projects/{project_name}/outputs/tobe/prototype/figma-spec.md"
    screen_list:    "projects/{project_name}/outputs/tobe/prototype/screen-list.md"
    design_tokens:  "projects/{project_name}/outputs/tobe/prototype/design-tokens.json"
  ```

- [X] **1\.4** Open `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` and verify its frontmatter. Note: this file has a **duplicate `version:` key** (appears twice — once as `version: 1.0.0` and once as `version: "1.0.0"`). Remove the duplicate (keep the quoted form `"1.0.0"` as the canonical one), then bump to `"2.0.0"`. The clean frontmatter must be:
  ```yaml
  ---
  name: ava-stack-angular-frontend
  version: "2.0.0"
  description: |
    ...
  allowed-tools: Read, Write, Edit, Glob
  ---
  ```
  Do NOT add or modify the `date:` field — it is not an allowed frontmatter key per Article II. Bump `version` only; leave all other existing fields exactly as-is.

- [X] **1\.5** Open `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` and bump `version: "0.1.0-stub"` to `version: "0.2.0-stub"` in its frontmatter. Verify no other frontmatter keys are added or removed.

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. Execute sub-groups **A → B → C** in order (each sub-group targets a different file and is independent of the others within sub-group ordering, but all three can be parallelised once Category 1 is complete).

### Sub-group A — `prototype-agent.md`: Token Extraction Section

- [X] **2\.1** Locate the section `## Protocolo de Seleção do BC Inicial` in `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. Identify the section immediately following it (which should be `## Protocolo de Handoff para ava-stack-orchestrator` or similar). The new `## Extração de Design Tokens` section must be inserted **between** these two sections.

- [X] **2\.2** Insert the `## Extração de Design Tokens` section into `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` at the position identified in task 2.1. The section must contain (all in Brazilian Portuguese):

  a. **Heading and trigger rule**: A brief intro (1–2 sentences) stating that after all wireframes are generated, the agent extracts design tokens from `design-system.md` (already loaded in Pre-Execution step 1) and writes them to `design-tokens.json`.

  b. **4-step extraction procedure**:
     1. Read `design-system.md` and identify CSS custom properties (`--nome-da-variavel: valor`)
     2. Map each variable to the corresponding `design-tokens.json` field using the table in §b below
     3. For fields not found in `design-system.md`: try deriving from generated wireframe HTML (`style` attributes or `<style>` blocks); if still absent, use documented default and record `"source": "default"`
     4. Write `projects/{project_name}/outputs/tobe/prototype/design-tokens.json`

  c. **Mapping table** (`design-system.md` variable → `design-tokens.json` field) with at minimum these rows:
     `--space-*` / `--spacing-*` → `spacing.*` family; `--color-primary-*` → `colors.primary`; `--color-secondary-*` → `colors.secondary`; `--color-background` → `colors.background`; `--color-surface` → `colors.surface`; `--color-on-primary` → `colors.on_primary`; `--color-error` → `colors.error`; `--color-warning` → `colors.warning`; `--color-success` → `colors.success`; `--font-family-base` → `typography.font_family_base`; `--font-family-heading` → `typography.font_family_heading`; `--font-size-base/sm/lg` → `typography.font_size_*`; `--line-height-base` → `typography.line_height_base`; `--sidebar-width` → `layout.sidebar_width`; `--sidebar-collapsed-width` → `layout.sidebar_collapsed_width`; `--header-height` → `layout.header_height`; `--content-padding` → `layout.content_padding`; `--max-content-width` → `layout.max_content_width`.

  d. **Semantic matching note**: A `> ⚠️` callout stating that if `design-system.md` uses different naming (e.g., `--primary` instead of `--color-primary-500`), use semantic context match — not exact string match.

  e. **JSON structure template** showing the required top-level keys: `schema_version`, `generated_by`, `project_name`, `spacing`, `colors`, `typography`, `layout` (see `specs/008-design-tokens-propagation/data-model.md` for the full field list). Inline example values must be placeholders (e.g., `"#valor"`, `"16px"`) — **no hardcoded literal colors or dimensions**.

- [X] **2\.3** [P] Read the newly inserted section end-to-end and verify: (a) the 4 steps are complete and deterministic; (b) the mapping table covers all 26 data fields listed in `data-model.md`; (c) the `schema_version` in the JSON template is `"1.0"` and `generated_by` is `"ava-prototype"`; (d) no technology versions are hardcoded (Article I); (e) the section is entirely in Brazilian Portuguese (Article V).

### Sub-group B — `coder-angular-frontend.md`: Input Contract + G-DT Guardrail

- [X] **2\.4** [P] In `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`, locate the `## Input Contract` YAML block and find the `# CRÍTICOS — HARD STOP se ausentes ou inválidos` comment line. Append `prototype_screens` and `design_tokens` as the last two entries in the CRÍTICOS block:
  ```yaml
  prototype_screens:  file  # projects/{project_name}/outputs/tobe/prototype/screen-list.md
                            # HARD STOP se ausente: executar ava-prototype antes
  design_tokens:      file  # projects/{project_name}/outputs/tobe/prototype/design-tokens.json
                            # HARD STOP se ausente: executar ava-prototype antes
  ```

- [X] **2\.5** [P] In `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`, locate the Pre-Flight Check panel by searching for the literal string `╔══════════════════════════════════════════════════════════════╗` — this is the stable panel header anchor. Add two new rows to the **Input Contract** section of that panel:
  ```
  ║  [✅|❌] prototype_screens: projects/{project_name}/outputs/tobe/prototype/screen-list.md   ║
  ║  [✅|❌] design_tokens:     projects/{project_name}/outputs/tobe/prototype/design-tokens.json ║
  ```
  The `[✅|❌]` indicator follows the same pattern as existing rows (resolved at runtime based on file existence).

- [X] **2\.6** Locate the position in `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` where the Pre-Flight Check panel ends (just before the first scaffolding step or code generation begins). Insert the new `## Guardrail G-DT — Tokens de Design do Protótipo` section at this position. The section must contain (all in Brazilian Portuguese):

  a. **Header marker**: `⛔ **Executar antes de qualquer geração de CSS ou SCSS.**`

  b. **Passo 1 — Verificar existência de design-tokens.json**: A code/pseudo-code block showing:
     ```
     LEIA projects/{project_name}/outputs/tobe/prototype/design-tokens.json
       → AUSENTE: HARD STOP
         "Execute o agente ava-prototype antes de gerar o frontend.
          design-tokens.json não encontrado em outputs/tobe/prototype/"
       → PRESENTE: continuar para Passo 2
     ```

  c. **Passo 2 — Construir mapa de tokens CSS**: A fenced SCSS block showing the complete `:root` declaration using all fields from `design-tokens.json` (layout, spacing, colors, typography). Values must be template placeholders `{token.path}` — **no hardcoded values**. Include a comment at the top: `/* Tokens gerados a partir de design-tokens.json — NÃO editar manualmente */`. Instruct that this block must be added to the **beginning** of `src/styles.scss`, after any `@import` statements.

  d. **Passo 3 — Regra obrigatória para componentes de layout**: A rule stating that `AppShellComponent`, `SidebarComponent`, `HeaderComponent`, `LayoutComponent`, and any top-level layout wrapper components **MUST** reference layout tokens via `var(--token-name, fallback)`. Hardcoded dimension values are **PROHIBITED** in these components. Include an explicit ✅/❌ example pair showing both forms for `sidebar-width` and `header-height`.

- [X] **2\.7** [P] Read the G-DT section inserted in task 2.6 and verify: (a) Passo 1 HARD STOP message explicitly names `ava-prototype` as the prerequisite agent; (b) `:root` block in Passo 2 contains all 20+ custom property declarations from `data-model.md`; (c) Passo 3 lists all four named layout components and uses the `var(--token-name, fallback)` syntax; (d) no hardcoded color or dimension values appear outside placeholder braces; (e) section is entirely in Brazilian Portuguese.

### Sub-group C — `coder-react-frontend.md`: Stub Documentation

- [X] **2\.8** [P] In `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`, locate the `## TODO — Implementation Required` section. Add two new TODO items to the end of the list:
  ```markdown
  - [ ] Implement design token input contract (prototype_screens, design_tokens — align with coder-angular-frontend.md v2.0.0)
  - [ ] Implement G-DT guardrail (read design-tokens.json before CSS/JSS generation; HARD STOP if absent)
  ```

- [X] **2\.9** [P] In `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`, locate the section immediately before `## FASE OBRIGATÓRIA — Registro de Observabilidade`. Insert two new sections **before** that section (all in Brazilian Portuguese):

  **Section 1 — Contrato de Entrada Planejado (Design Tokens)**:
  - Opening note: `> ⚠️ Stub — não aplicado até implementação completa.`
  - A brief (2–3 sentence) explanation: when this agent is promoted from stub to full implementation, the following inputs will be **mandatory** in the Input Contract, aligned with `coder-angular-frontend.md v2.0.0`.
  - The input contract snippet:
    ```yaml
    prototype_screens:  file  # projects/{project_name}/outputs/tobe/prototype/screen-list.md
    design_tokens:      file  # projects/{project_name}/outputs/tobe/prototype/design-tokens.json
    ```

  **Section 2 — Guardrail G-DT (Planejado)**:
  - Opening note: `> ⚠️ Stub — não aplicado. Idêntico ao G-DT implementado em coder-angular-frontend.md v2.0.0.`
  - A bullet list describing what will happen when implemented: (1) read `design-tokens.json` before any CSS/JSS/CSS-in-JS generation; (2) HARD STOP if absent; (3) layout components (`AppShell`, `Sidebar`, `Header`) source dimensions from design tokens, not hardcoded values.

---

## Category 3 — Shared Schema Updates

**SKIP — N/A.** Plan §7 confirmed: `agent-task.schema.json` and `agent-result.schema.json` require no changes. `design-tokens.schema.json` is a spec-only contract artifact (`specs/008-design-tokens-propagation/contracts/`) — not a pipeline schema.

---

## Category 4 — Module Registration

Depends on Category 1. Both tasks can run in parallel.

- [X] **4\.1** [P] Update `src/modules/ava-fabric-agents/prototype/module.yaml`:
  - Bump `version:` from `"1.0.0"` to `"1.1.0"`
  - Add `"design-tokens.json"` as a new entry in the `outputs.files` list
  - All other fields (`name`, `display_name`, `description`, `handoff`, `agents`, `standalone`, `hooks`) remain unchanged
  - The final `outputs.files` list must be: `["index.html", "demo-script.md", "figma-spec.md", "README.md", "design-tokens.json"]`

- [X] **4\.2** [P] Update `src/modules/ava-fabric-agents/tech-stack/module.yaml`:
  - Bump module `version:` from `"1.3.0"` to `"1.4.0"`
  - All agent entries (`id`, `file`, `routing_key`, `status`) remain unchanged
  - No new agent entries are added

---

## Category 5 — Quality Gate Checklists

Can run after Category 2 completes. All tasks are independent.

- [X] **5\.1** [P] Structural validation of `prototype-agent.md`: (a) frontmatter contains exactly `name`, `version`, `description`, `allowed-tools` — no extra keys; (b) `version` is `"1.1.0"`; (c) `## Output Contract` contains exactly 5 output entries including `design_tokens`; (d) `## Extração de Design Tokens` section exists and appears after `## Protocolo de Seleção do BC Inicial`; (e) no code fence is left open in the new section.

- [X] **5\.2** [P] Structural validation of `coder-angular-frontend.md`: (a) frontmatter `version` is `"2.0.0"` with no duplicate `version:` key; (b) Input Contract CRÍTICOS block contains `prototype_screens` and `design_tokens` entries; (c) Pre-Flight Check panel includes rows for both new inputs; (d) `## Guardrail G-DT` section exists and appears before the first scaffolding section; (e) `## Guardrail G-DT` contains Passos 1, 2, and 3 in order; (f) Passo 3 lists `AppShellComponent`, `SidebarComponent`, `HeaderComponent`, and `LayoutComponent` by name.

- [X] **5\.3** [P] Structural validation of `coder-react-frontend.md`: (a) frontmatter `version` is `"0.2.0-stub"`; (b) `## TODO` section has 2 new items for design token contract and G-DT; (c) `## Contrato de Entrada Planejado (Design Tokens)` section exists; (d) `## Guardrail G-DT (Planejado)` section exists; (e) both new sections appear before `## FASE OBRIGATÓRIA — Registro de Observabilidade`.

- [X] **5\.4** [P] Verify spec §9 Quality Gate Requirements: all 10 checklist items from the spec are satisfiable by the implementation. Specifically: no `[NEEDS CLARIFICATION]` markers in any modified file; all output paths use lowercase `{project_name}`; both new outputs/inputs follow the correct F4 prototype path; no technology versions hardcoded in any new text.

---

## Category 6 — Acceptance Validation & QA Integration

Can run in parallel with Categories 5 and 7 after Category 2 completes.

- [X] **6\.1** [P] Trace **Spec Scenario 1** (prototype exports `design-tokens.json`, P1) through the `## Extração de Design Tokens` procedure in the updated `prototype-agent.md`: simulate a project where `design-system.md` contains `--color-primary-500: #1976D2`, `--sidebar-width: 240px`, `--header-height: 64px`, and `--spacing-md: 16px`. Confirm that following the 4-step procedure would produce a `design-tokens.json` with `colors.primary = "#1976D2"`, `layout.sidebar_width = "240px"`, `layout.header_height = "64px"`, and `spacing.md = "16px"`. Confirm the `schema_version` field would be `"1.0"` and `generated_by` would be `"ava-prototype"`.

- [X] **6\.2** [P] Trace **Spec Scenario 2** (Angular HARD STOP when tokens absent, P1) through the G-DT Passo 1 block in the updated `coder-angular-frontend.md`: simulate `design-tokens.json` NOT present at `projects/test-project/outputs/tobe/prototype/design-tokens.json`. Confirm the procedure results in HARD STOP and that: (a) the stop message names `ava-prototype` explicitly; (b) the message references the expected file path; (c) no generation steps execute after the HARD STOP.

- [X] **6\.3** [P] Trace **Spec Scenario 3** (G-DT guardrail: layout components use token-derived values, P1) through Passo 2 and Passo 3 in the updated `coder-angular-frontend.md`: simulate `design-tokens.json` present with `layout.sidebar_width = "260px"`. Confirm that: (a) Passo 2 would produce a `:root` block containing `--sidebar-width: 260px`; (b) Passo 3 requires `SidebarComponent` to use `width: var(--sidebar-width, 260px)` — not the literal `260px`; (c) the ✅/❌ example pair in Passo 3 matches this scenario correctly.

- [X] **6\.4** [P] Trace **Spec Scenario 4** (React stub acknowledges planned input contract, P2) through the updated `coder-react-frontend.md`: confirm the stub response protocol (`implementation.status: STUB`) is unchanged, and that the new `## Contrato de Entrada Planejado` section documents `design-tokens.json` and `prototype_screens` as future mandatory inputs without triggering any HARD STOP in the stub response path.

- [X] **6\.5** [P] Map all 5 spec scenarios to F5 QA traceability: confirm each scenario's Given/When/Then format (spec §4) is directly usable as input to `ava-qa-behavior-mapping`. Note the behavior reference IDs to assign: `BR-DT-01` (token export), `BR-DT-02` (HARD STOP), `BR-DT-03` (G-DT layout), `BR-DT-04` (React stub), `BR-DT-05` (CSS fidelity). No file edits required — document findings in this task note.

- [X] **6\.6** [P] Execute the quickstart validation scenarios from `specs/008-design-tokens-propagation/quickstart.md` against the updated agents:
  - Scenario 1: confirm `design-tokens.json` would be produced with correct structure
  - Scenario 2: confirm BLOCKED output message format matches the quickstart expected output
  - Scenario 3: confirm `:root` block and `var()` usage in layout component SCSS are enforced by Passo 2/3; for the **Sophia project** specifically, verify `--sidebar-width: 260px` and `--header-height: 56px` are produced from `design-tokens.json` per Spec Scenario 5
  - Scenario 4: confirm React stub mentions `design-tokens.json` in its documentation sections

- [X] **6\.7** [P] Verify **regression safety** (SC-E): confirm that after all Category 2 modifications, the existing CRÍTICOS entries in `coder-angular-frontend.md` Input Contract (`project_name`, `pipeline_mode`, `frontend_version`, `auth_provider`, `bounded_contexts`, `trace_id`) are all still present and unmodified. Confirm no existing Input Contract field is renamed, removed, or has its HARD STOP semantics changed. Zero regressions in the existing input surface.

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Categories 5 and 6 after Category 2 completes.

- [X] **7\.1** [P] Add `CHANGELOG.md` entries for all three version bumps (use the same format as existing entries in the file):
  - `ava-prototype v1.1.0` — MINOR: Added `## Extração de Design Tokens` step that exports `design-tokens.json` (spacing, colors, typography, layout) to `outputs/tobe/prototype/` after wireframe generation. Added version field to frontmatter (previously undeclared). Updated Output Contract with `design_tokens` entry.
  - `ava-stack-angular-frontend v2.0.0` — MAJOR: Added mandatory inputs `prototype_screens` and `design_tokens` to Input Contract (HARD STOP if absent). Added `## Guardrail G-DT` pre-generation gate: reads `design-tokens.json`, builds `:root` CSS custom property block in `styles.scss`, enforces `var(--token)` usage in AppShell/Sidebar/Header/Layout components.
  - `ava-stack-react-frontend v0.2.0-stub` — MINOR: Documented planned Input Contract (prototype_screens, design_tokens) and G-DT guardrail as stub sections for future implementation. Added 2 TODO items.

- [X] **7\.2** [P] Update `docs/agents-catalog.md` for all three agents:
  - `ava-prototype`: bump version to `1.1.0`; add to role summary: "Exports `design-tokens.json` (spacing, colors, typography, layout) to `outputs/tobe/prototype/` for consumption by frontend codegen agents."
  - `ava-stack-angular-frontend`: bump version to `2.0.0`; add to role summary: "Requires `design-tokens.json` from `ava-prototype` (HARD STOP if absent). G-DT guardrail derives all layout dimensions from prototype tokens via CSS custom properties in `styles.scss`."
  - `ava-stack-react-frontend`: bump version to `0.2.0-stub`; note planned design token integration in role summary.

---

## Completion Checklist

- [X] All 6 active categories (1, 2, 4, 5, 6, 7) complete
- [X] `prototype-agent.md`: version `"1.1.0"` in frontmatter, `design_tokens` in Output Contract, `## Extração de Design Tokens` section present (tasks 1.2, 1.3, 2.2)
- [X] `coder-angular-frontend.md`: version `"2.0.0"` with no duplicate key, new inputs in Input Contract and Pre-Flight Check, `## Guardrail G-DT` section with Passos 1–3 (tasks 1.4, 2.4, 2.5, 2.6)
- [X] `coder-react-frontend.md`: version `"0.2.0-stub"`, new TODO items, planned contract sections (tasks 1.5, 2.8, 2.9)
- [X] `prototype/module.yaml`: version `"1.1.0"`, `design-tokens.json` in `outputs.files` (task 4.1)
- [X] `tech-stack/module.yaml`: version `"1.4.0"` (task 4.2)
- [X] Structural validations passed for all 3 agent files (tasks 5.1–5.3)
- [X] All 5 spec scenarios traced successfully (tasks 6.1–6.4)
- [X] Regression safety verified — existing Angular Input Contract entries unchanged (task 6.7)
- [X] `CHANGELOG.md` entry committed (task 7.1)
- [X] `docs/agents-catalog.md` updated for all 3 agents (task 7.2)

---

## Dependencies

```
Category 1 ──► Category 2 (A, B, C run in parallel) ──┬──► Category 5 (all parallel)
                                                        ├──► Category 6 (all parallel)
                                                        └──► Category 7 (all parallel)

Category 4: runs in parallel with Category 2 (depends only on Category 1)
Category 3: SKIP (N/A)
```

## Parallel Execution Within Category 2

Sub-groups A, B, and C target different files and can run in parallel once Category 1 is complete:
- **Sub-group A** (tasks 2.1–2.3): `prototype-agent.md`
- **Sub-group B** (tasks 2.4–2.7): `coder-angular-frontend.md`
- **Sub-group C** (tasks 2.8–2.9): `coder-react-frontend.md`

Within each sub-group, tasks must run sequentially (each builds on the previous insertion).

## Parallel Execution After Category 2

Tasks **5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2** can all run in parallel once Category 2 completes.

## MVP Scope

Category 1 + Sub-groups A and B of Category 2 + Category 4 constitutes the minimum viable implementation:
- `prototype-agent.md` exports `design-tokens.json`
- `coder-angular-frontend.md` enforces G-DT guardrail
- `module.yaml` files updated

Sub-group C (React stub), Categories 5–7 (validation + docs) can follow in a second pass. However, given the total of 29 tasks across 3 small files, full execution in one pass is recommended.


