# Agent Implementation Plan: Design Tokens Propagation — Prototype → Frontend Agents

**Branch**: `008-design-tokens-propagation` | **Date**: 2026-07-08 | **Spec**: [spec.md](spec.md)

**Input**: PBI #2333 — Propagação de design tokens do protótipo para agentes frontend (Angular e React)

---

## Summary

| Field | Value |
|---|---|
| **Agents modified** | `ava-prototype` · `ava-stack-angular-frontend` · `ava-stack-react-frontend` |
| **Phases** | F4 Prototype (sub-phase of F2) · F3 Tech Stack |
| **Modules** | `prototype` · `tech-stack` |
| **Primary Requirement** | `prototype-agent.md` exports `design-tokens.json`; frontend agents consume it as mandatory input before generating any CSS/SCSS |
| **Technical Approach** | Add token extraction step + new output to prototype; add G-DT pre-generation guardrail + 2 mandatory inputs to Angular agent; document planned contract in React stub |
| **Change Type** | `modify-existing` — 3 agent files, MINOR/MAJOR version bumps |

---

## Constitution Check

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded: token schema uses keys/patterns, not
  literal CSS framework versions; JSON key names derived from design-system.md keys at runtime.
- [x] **Article II** — Frontmatter contains ONLY `name`, `version`, `description`, `allowed-tools`:
  all three agents already conform; only `version` fields change.
- [x] **Article II** — Agent names match `^ava-[a-z0-9-]+$`:
  `ava-prototype` ✅ · `ava-stack-angular-frontend` ✅ · `ava-stack-react-frontend` ✅
- [x] **Article III** — Phase placement valid: F4 Prototype is a sub-phase of F2 (constitution
  confirms); F3 Angular/React placement unchanged; pipeline order `F2→F3` ensures prototype runs first.
- [x] **Article IV** — Module-level `module.yaml` diff prepared — see Plan section 5.
- [x] **Article V** — Agent body language is Brazilian Portuguese: all new guardrail prose,
  step descriptions, and comments are in pt-BR.
- [x] **Article VI** — BDD scenarios: spec section 4 has 5 scenarios covering export (S1),
  HARD STOP (S2), G-DT guardrail (S3), React stub (S4), and CSS fidelity (S5).
- [x] **Article VII** — Security sub-pipeline impact: G-DT reads a local JSON file using `Read`
  tool. No network access, no secrets, no external dependencies. No security sub-pipeline impact.
- [x] **Article VIII** — trace_id propagation: N/A — all three files are LLM prompt `.md` files;
  they do not handle `trace_id` in their body.
- [x] **Article IX** — Clean Architecture: N/A — all three are LLM prompt files. Generated Angular
  SCSS does not cross CA layers.
- [x] **Article X** — Version bumps:
  - `prototype-agent.md`: undeclared → `1.1.0` (MINOR: new output artifact, backward-compatible).
  - `coder-angular-frontend.md`: `1.0.0` → `2.0.0` (MAJOR: new mandatory inputs added).
  - `coder-react-frontend.md`: `0.1.0-stub` → `0.2.0-stub` (MINOR: new stub documentation).
- [x] **Article XI** — Skill/Agent split:
  - `ava-prototype`: user-facing; SKILL.md exists at `.github/skills/ava-prototype/SKILL.md` — no change.
  - `ava-stack-angular-frontend`: user-facing; SKILL.md exists — no change.
  - `ava-stack-react-frontend`: internal (stub); no SKILL.md — per constitution "internal-only" rule.

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec.
- [x] New output (`design-tokens.json`) follows `projects/{project_name}/outputs/tobe/prototype/` — correct F4 path.
- [x] Angular agent downstream (`ava-stack-orchestrator`) confirmed to exist in `tech-stack/module.yaml`.
- [x] Angular agent's own downstream (`ava-stack-build-validator` or equivalent) unaffected — no output path changes.

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Agent runtime | LLM prompt files (`.md`) | N/A — not compiled |
| Token format | JSON with schema version `"1.0"` | `contracts/design-tokens.schema.json` |
| CSS delivery | Custom properties via `:root` block in `styles.scss` | research.md Decision 2 |
| Token source | `design-system.md` (already in prototype context) | research.md Decision 1 |
| Guardrail position | Before first scaffolding step in Angular agent | research.md Decision 3 |
| React stub scope | Documentation only — no enforcement | research.md Decision 4 |
| Pre-Flight panel | Reuse existing `╔══╣ PRE-FLIGHT CHECK ╠══╗` format | research.md Decision 6 |

**No new libraries, frameworks, or runtime versions introduced.**

---

## 2. Phase Placement

```
F1 → ava-summary → F2 (incl. F4 Prototype)
  F2: ava-tobe-orchestrator
      → ava-prototype  [MODIFIED: outputs design-tokens.json]
  → ava-summary → F3
  F3: ava-stack-orchestrator
      → ava-stack-angular-frontend  [MODIFIED: G-DT guardrail + new inputs]
      → ava-stack-react-frontend    [MODIFIED: stub docs only]
  → ava-summary → F5 → F7 → F6 → ava-summary (FINAL)
```

**Quality gate at this phase**: Summary Validator (runs after every phase) — no change.

`human_gate_required` impact: G-DT emits HARD STOP when `design-tokens.json` is absent but
does not set `human_gate_required: true`. The invoking developer must run `ava-prototype` first.

---

## 3. Clean Architecture Alignment

```
Domain         → NO  — agent is an LLM prompt file
Application    → NO
Infrastructure → NO
Presentation   → NO
```

> All three targets are `.md` instruction files. The Angular SCSS generated by
> `coder-angular-frontend.md` targets the Presentation layer of the client project,
> but the agent file itself has no CA layer affiliation.

---

## 4. Agent File Structure

**Modify-existing**: no new files created.

### 4a. `prototype-agent.md`

```
src/modules/ava-fabric-agents/prototype/agents/
└── prototype-agent.md    ← modified
    Sections changed:
    ├── [frontmatter]     version field added: "1.1.0"
    ├── [Output Contract] design_tokens entry added
    └── [NEW SECTION]     ## Extração de Design Tokens
                          positioned after "Protocolo de Seleção do BC Inicial"
                          before "Protocolo de Handoff para ava-stack-orchestrator"
```

**Dispatch mode**: user-facing (SKILL.md at `.github/skills/ava-prototype/SKILL.md` — no change)

**allowed-tools**: `Read, Write, Edit` — already present; sufficient for writing `design-tokens.json`.

### 4b. `coder-angular-frontend.md`

```
src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-angular-frontend.md    ← modified
    Sections changed:
    ├── [frontmatter]        version: "1.0.0" → "2.0.0"
    ├── [Input Contract]     2 new CRÍTICOS entries (prototype_screens, design_tokens)
    ├── [Pre-Flight Check]   rows added for new inputs
    └── [NEW SECTION]        ## Guardrail G-DT — Tokens de Design do Protótipo
                             positioned after Pre-Flight Check,
                             before the first scaffolding/generation step
```

**Dispatch mode**: user-facing (SKILL.md at `.github/skills/ava-stack-angular-frontend/SKILL.md` — no change)

**allowed-tools**: `Read, Write, Edit, Glob` — already present.

### 4c. `coder-react-frontend.md`

```
src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-react-frontend.md    ← modified
    Sections changed:
    ├── [frontmatter]      version: "0.1.0-stub" → "0.2.0-stub"
    ├── [## TODO section]  2 new TODO items for design token contract + G-DT
    ├── [NEW SECTION]      ## Contrato de Entrada Planejado (Design Tokens)
    └── [NEW SECTION]      ## Guardrail G-DT (Planejado)
                           both positioned before "FASE OBRIGATÓRIA — Registro de Observabilidade"
```

**Dispatch mode**: internal (stub; no SKILL.md per constitution Article XI)

---

## 5. module.yaml Impact

### `src/modules/ava-fabric-agents/prototype/module.yaml`

```yaml
# BEFORE
version: "1.0.0"
outputs:
  base_path: "projects/{project_name}/outputs/tobe/prototype"
  files:
    - "index.html"
    - "demo-script.md"
    - "figma-spec.md"
    - "README.md"

# AFTER
version: "1.1.0"
outputs:
  base_path: "projects/{project_name}/outputs/tobe/prototype"
  files:
    - "index.html"
    - "demo-script.md"
    - "figma-spec.md"
    - "README.md"
    - "design-tokens.json"    # [NEW]
```

### `src/modules/ava-fabric-agents/tech-stack/module.yaml`

```yaml
# BEFORE
version: "1.3.0"

# AFTER
version: "1.4.0"
# Reason: ava-stack-angular-frontend MAJOR bump → module MINOR bump (new capability added)
```

No agent entry changes — IDs and file paths are unchanged.

**Top-level `module.yaml`**: no change (no new module/phase created).

---

## 6. Observability & Trace Propagation

**N/A** — All three targets are LLM prompt files. Trace context is provided through
`shared-context.md` via the SKILL.md wrapper layer. No changes to `trace_id` handling.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | No new pipeline-level inputs |
| `agent-result.schema.json` | NO | HARD STOP uses existing error messaging; no new result fields |
| `design-tokens.schema.json` | NEW (spec artifact only) | Located at `specs/008-design-tokens-propagation/contracts/design-tokens.schema.json`. Optional CI validation; not a pipeline schema. |

---

## 8. Implementation Phases (Task Categories)

### Category 1 — Spec artifacts ✅ (complete)

- [x] `spec.md`
- [x] `checklists/requirements.md`
- [x] `research.md`
- [x] `data-model.md`
- [x] `quickstart.md`
- [x] `contracts/design-tokens.schema.json`

### Category 1.5 — SKILL.md (N/A — all skills already exist, no changes needed)

### Category 2 — Agent body modifications

**Task 2.1** — `prototype-agent.md`: Add `version: "1.1.0"` to frontmatter  
**Task 2.2** — `prototype-agent.md`: Add `design_tokens` entry to `## Output Contract` YAML block  
**Task 2.3** — `prototype-agent.md`: Add `## Extração de Design Tokens` section with mapping table (positioned after "Protocolo de Seleção do BC Inicial")  

**Task 2.4** — `coder-angular-frontend.md`: Bump frontmatter version `"1.0.0"` → `"2.0.0"`  
**Task 2.5** — `coder-angular-frontend.md`: Add `prototype_screens` and `design_tokens` entries in Input Contract CRÍTICOS block  
**Task 2.6** — `coder-angular-frontend.md`: Add Pre-Flight Check rows for `prototype_screens` and `design_tokens`  
**Task 2.7** — `coder-angular-frontend.md`: Add `## Guardrail G-DT` section (HARD STOP logic + `:root` template + layout component rule)  

**Task 2.8** — `coder-react-frontend.md`: Bump frontmatter version `"0.1.0-stub"` → `"0.2.0-stub"`  
**Task 2.9** — `coder-react-frontend.md`: Add `## Contrato de Entrada Planejado (Design Tokens)` section  
**Task 2.10** — `coder-react-frontend.md`: Add `## Guardrail G-DT (Planejado)` section  
**Task 2.11** — `coder-react-frontend.md`: Add 2 TODO items to `## TODO — Implementation Required`  

### Category 3 — Gate logic (N/A — no new `human_gate_required` conditions)

### Category 4 — Registration

**Task 4.1** — `prototype/module.yaml`: bump version `1.0.0` → `1.1.0`; add `design-tokens.json` to `outputs.files`  
**Task 4.2** — `tech-stack/module.yaml`: bump version `1.3.0` → `1.4.0`  
_(CHANGELOG entries belong in Category 7 per the task template — see tasks.md §7.1)_  

### Category 5 — Quality assurance (post-implementation)

**Task 5.1** — Validate no hardcoded dimension values appear in plan/agent examples outside `:root`  
**Task 5.2** — Validate `design-tokens.json` schema against `contracts/design-tokens.schema.json`  
**Task 5.3** — Execute quickstart scenarios 1–4 against Sophia project  

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| Article X — MAJOR bump for Angular | `coder-angular-frontend.md` 1.0.0 → 2.0.0 breaks pipelines invoking it without `design-tokens.json` | Projects following the standard pipeline (F2 → F3) will have `ava-prototype` output before reaching the Angular agent. The bump is a contract formalization of an already-implied dependency. | HARD STOP message names `ava-prototype` explicitly; quickstart.md documents the prerequisite order. |
| Article III — prototype before frontend | If `ava-prototype` was skipped, Angular agent blocks entirely | F4 Prototype is a F2 sub-phase per constitution. Any project following standard pipeline will have prototype artifacts before reaching F3 codegen. | Pre-Flight Check gives actionable fix; spec section 6 documents the dependency. |

---

## 10. Test Strategy

| Test Type | Validation | Target | Quickstart Scenario |
|---|---|---|---|
| Output existence | PowerShell `Test-Path` | `design-tokens.json` after prototype run | S1 |
| Schema validation | `ajv validate` | `design-tokens.json` vs schema | S1 |
| HARD STOP enforcement | Manual invocation with absent tokens | Angular agent blocks | S2 |
| G-DT `:root` block | SCSS file inspection (`-match ":root"`) | `styles.scss` has `:root` | S3 |
| No hardcoded values | Regex scan on Sidebar/Header SCSS | `var()` used, not literals | S3 |
| React stub docs | Response inspection | Stub mentions `design-tokens.json` | S4 |
| Sophia fidelity | Manual comparison of token values | Generated dims match prototype | S5 |
| Regression | Existing Angular test run | No break for already-prototyped projects | All |

