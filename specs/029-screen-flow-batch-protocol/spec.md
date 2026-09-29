# Agent Specification: ava-asis-documentation — Batch Protocol + Completude Assertion for screen-flow.mmd

**Feature Branch**: `029-screen-flow-batch-protocol`
**Created**: 2026-07-24
**Status**: Draft
**Change Type**: `modify-existing`
**Input**: Agent description: "Vou te contextualizar sobre um BUG na geração de diagramas de fluxo de telas com Mermaid. screen-flow.mmd: 1,8% cobertura — agente não executou gen_screen_flow.py (REGRA ABSOLUTA violada). Causa Raiz: Os agentes ava-asis-documentation foram instruídos a consumir os arquivos AST compactados, porém usaram conhecimento implícito do LLM sobre 'como um ERP Delphi brasileiro típico se parece' — e não os dados reais do analisador AST. Ausência de assertion de completude pós-geração: Nenhum agente possui validação pós-geração do tipo ASSERT count(flowchart_nodes) >= 80% of form_registry_count."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content for description.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-asis-documentation` |
| **Version** | `3.0.0` (MAJOR bump — adds REGRA ABSOLUTA de batch protocol + assertion de completude; changes FT behavior from single-shot to chunked iteration) |
| **Phase** | `F1` |
| **Module** | `asis-diagnostic` |
| **Role** | Agente de documentação funcional AS-IS. Altera o sub-skill FT (Screen Flow Mapper) para usar protocolo de geração em lotes por bounded context + assertion de completude, eliminando truncamento por output token limit. |
| **Skill** | `ava-asis-documentation` (existente) |
| **Dispatch** | user-facing via SKILL.md (existente) |

> **Change Type is `modify-existing`**:
> - File to modify: `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md`
> - Version bump: MAJOR (2.x → 3.0.0) — changes the FT sub-skill execution model from single-pass (all forms in one response) to chunked batch iteration by bounded context; adds mandatory post-generation assertion that was previously absent
> - The `module.yaml` entry already exists — Category 4 tasks are N/A
> - The `SKILL.md` already exists — Category 1.5 is N/A

---

## 2. Agent Frontmatter

The existing frontmatter in `documentation-asis.md` is updated for version and description wording to reflect the new FT execution model:

```yaml
---
name: "ava-asis-documentation"
version: "3.0.0"
description: |
  Gera documentação funcional AS-IS: cadeia de valor, requisitos funcionais,
  regras de negócio, screen-flow, protótipo navegável e regras de tela.
  NOVO em v3.0: Screen Flow Mapper usa protocolo de geração em lotes por bounded
  context com assertion de completude para evitar truncamento.
  Ativa com: "documentar sistema AS-IS", "extrair requisitos do legado",
  "gerar documentação funcional", "screen flow", "business rules", "value chain".
allowed-tools: Read Write Edit Bash
---
```

Do NOT include `phase`, `module`, `inputs`, `outputs`, or `dependencies` in frontmatter.
These are not valid frontmatter fields in IMFAI agents.

---

## 3. Output Contract

The `## Output Contract` YAML block in the agent body (Constitution Article II):

```yaml
## Output Contract
outputs:
  value_chain:        "projects/{project_name}/outputs/asis/docs/value-chain.md"
  business_rules:     "projects/{project_name}/outputs/asis/docs/business-rules.md"
  screen_navigation:  "projects/{project_name}/outputs/asis/docs/screen-navigation-map.md"
  screen_flow:        "projects/{project_name}/outputs/asis/docs/screen-flow.mmd"
  screen_rules:       "projects/{project_name}/outputs/asis/docs/screen-rules.md"
  prototype_dir:      "projects/{project_name}/outputs/asis/docs/prototype-asis/"
  screen_flow_bc_artifacts: "projects/{project_name}/outputs/asis/docs/screen-flow-*.mmd"
  completeness_assertion: "projects/{project_name}/outputs/asis/docs/screen-flow-completeness.json"
```

> **Note**: The `screen_flow_bc_artifacts` and `completeness_assertion` are new.
> The `completeness_assertion` JSON records the result of the PASS/FAIL assertion
> with counts and divergence metrics — consumed by the Summary validator and
> downstream QA agents (`ava-qa-behavior-mapping`).
> The numbered `screen-flow-*.mmd` files are intermediate artifacts that MUST be
> retained for debugging and evidence.

Path conventions:
| Phase | Output folder |
|---|---|
| F1 (AS-IS) | `projects/{project_name}/outputs/asis/` |

---

## 4. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions (`**Story**:`) are in Brazilian Portuguese;
> Acceptance scenarios (Given/When/Then) are in English for BDD traceability with F5 QA agents.

### Scenario 1 — Nominal Path: ERP with 665 forms (High-Volume Legacy)

**Story**: Como engenheiro de migração, quero que o screen-flow.mmd contenha pelo menos 80 das forms catalogadas no form-registry.json, para que o diagrama represente o sistema real e não uma amostra truncada.

**Why this priority**: P1 — this is the exact bug reported; truncation invalidates downstream architecture and summary artifacts.

**Acceptance Scenarios**:

1. **Given** a Delphi project with `form-registry.json` containing `N_registry` forms where `N_registry > 80`, **When** the FT sub-skill executes, **Then** it partitions forms by bounded context and generates one `screen-flow-{bc_id}.mmd` per batch.
2. **Given** the above, **When** all BC batches complete, **Then** the final merged `screen-flow.mmd` contains `N_nodes` unique form nodes where `N_nodes >= 0.8 * N_registry` — the completeness assertion PASSes.
3. **Given** the above, **When** the assertion runs, **Then** `screen-flow-completeness.json` is written with `status: "PASS"`, `coverage_pct`, `threshold_pct` (80), `N_nodes`, and `N_registry`.
4. **Given** a project with `N_registry <= 80`, **When** FT executes, **Then** the batch protocol is skipped and single-pass generation is used, with the same 80% assertion applied.

---

### Scenario 2 — Edge Case: Low-Context Fallback (LLM Skips Script Execution)

**Why this priority**: P1 — root cause of the bug; the agent generated inline instead of invoking the script under context-window pressure.

**Acceptance Scenarios**:

1. **Given** the LLM context window is near its limit after F1 has consumed ~80K tokens, **When** FT receives the instruction to generate screen-flow, **Then** the agent MUST invoke `Bash: python src/shared/tools/gen_screen_flow.py` and MUST NOT generate the mermaid content inline.
2. **Given** the agent attempts to generate screen-flow.mmd inline without invoking the script, **When** the orchestrator or validator detects this, **Then** it logs `[FT-INLINE-GENERATION-DETECTED]` and marks the sub-skill as FAILED, triggering a retry.
3. **Given** `gen_screen_flow.py` does not exist at the expected path, **When** FT executes, **Then** the agent falls back to the batch-protocol manual (per-BC subprocess calls with minimal arguments) and logs `[FT-SCRIPT-MISSING] fallback to batch protocol`.

---

### Scenario 3 — Quality Gate: Assertion FAILs (Coverage Below 80%)

**Why this priority**: P1 — safety gate preventing promotion of an incomplete artifact.

**Acceptance Scenarios**:

1. **Given** the merged `screen-flow.mmd` has `N_nodes < 0.8 * N_registry`, **When** the completeness assertion runs, **Then** `screen-flow-completeness.json` receives `status: "FAIL"`, `retry_allowed: true`, and a list of missing `form_id`s.
2. **Given** the assertion FAILs on the first attempt, **When** the agent retries, **Then** it re-runs the batch generation for BCs with missing forms (up to 3 retries), then re-runs the assertion.
3. **Given** the assertion FAILs after 3 retries, **When** FT completes, **Then** `AgentResult.success` remains `false`, `AgentResult.risk.level` is set to `"high"`, and `AgentResult.human_gate_required` is `true`.

---

## 5. Quality Gate Requirements

- [ ] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [ ] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] Agent registered in module-level `module.yaml` diff included in plan (Article IV)
- [ ] All output paths use lowercase `{project_name}` and correct phase folder (Article II)
- [ ] BDD scenarios cover nominal (high-volume), edge (LLM skips script), and gate (assertion FAIL) paths (Article VI)
- [ ] Security sub-pipeline impact assessed — screen-flow does not process secrets (no change from v2.x)
- [ ] No technology versions hardcoded — Python script path is relative, not version-locked (Article I)
- [ ] Skill/Agent split declared: SKILL.md already exists (Article XI)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Phase orchestrator | `ava-asis-orchestrator` | Must dispatch `ava-asis-documentation` after `ava-asis-inventory` or in parallel; `form-registry.json` is required for the batch protocol but the agent has a glob fallback |
| Form Registry artifact | `ava-asis-inventory` | `form-registry.json` is the canonical input for the batch protocol; without it the agent falls back to glob and the assertion uses glob count instead |
| Mermaid Guardrails | `src/shared/templates/diagrams/mermaid-guardrails.md` | All `.mmd` files must pass syntax validation |
| Summary Validator | `ava-summary` | Reads `screen-flow-completeness.json`; if `status: FAIL`, Summary HTML blocks promotion (Summary Validator Rule TBD) |

---

## 7. Exclusions

- **Bounded Context discovery algorithm** — handled by `ava-asis-solution-delphi`; FT assumes BC prefixes/paths are provided in `form-registry.json` or via `bounded-context-map.md`
- **Mermaid syntax validation** — handled by existing `validate_diagram.py` called per intermediate file and on the final merged file
- **Screen Navigation Map content generation** — the batch protocol changes only the `screen-flow.mmd` generation path; `screen-navigation-map.md` still embeds the final merged mermaid block
- **Prototype-ASIS generation** — unchanged from v2.x

---

## 8. Assumptions

- `form-registry.json` contains `form_id` and `bounded_context` (or `unit_path` / `directory` from which BC can be inferred) for each entry
- `gen_screen_flow.py` exists at `src/shared/tools/gen_screen_flow.py` and accepts `--project`, `--input`, `--output`, and `--bc-map` arguments
- `bounded-context-map.md` (produced by `ava-asis-solution-delphi`) is available for high-volume projects to define BC prefixes when `form-registry.json` lacks explicit BC
- Python 3.11+ is available in the execution environment for the script invocation
- Projects with fewer than 80 forms do not trigger the batch protocol; the assertion still runs but with no performance risk

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Coverage target | `screen-flow.mmd` contains >= 80% of forms in `form-registry.json` |
| Assertion file produced | `screen-flow-completeness.json` exists after FT with `status` and metrics |
| No inline generation under pressure | Zero occurrences of `[FT-INLINE-GENERATION-DETECTED]` in normal runs |
| Tool invocation rate | `gen_screen_flow.py` (or batch equivalent) is invoked for 100% of high-volume projects (>80 forms) |
| Retry resilience | Assertion FAIL triggers up to 3 retries; after 3 failures `human_gate_required = true` |
| Downstream consumption | `ava-summary` and `ava-qa-behavior-mapping` read `screen-flow-completeness.json` without error |
| No regression | Projects with <= 80 forms continue to work with single-pass generation |
