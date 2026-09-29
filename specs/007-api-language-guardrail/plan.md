# Agent Implementation Plan: Language Normalization Guardrail

**Spec**: `specs/007-api-language-guardrail/spec.md`
**Branch**: `007-api-language-guardrail`
**Date**: 2026-07-07
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) -- do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` — two existing agent files patched |
| **Agent 1** | `ava-tobe-spec` (`tobe-architecture/agents/openapi-spec-tobe.md`) |
| **Agent 2** | `ava-stack-dotnet-backend` (`tech-stack/agents/coder-dotnet-backend.md`) |
| **Phase** | F2 (`ava-tobe-spec`) · F3 (`ava-stack-dotnet-backend`) |
| **Module** | `tobe-architecture` · `tech-stack` |
| **Primary Requirement** | Guarantee all generated API path segments, operationIds, and C# identifiers are in English, even when source bounded-context-map names are in PT-BR |
| **Technical Approach** | Add a transliteration table + guardrail section to `openapi-spec-tobe.md` and a G10 guardrail (cross-referencing the table) to `coder-dotnet-backend.md`; bump both agent versions to `1.1.0` |

---

## Constitution Check

*GATE: Pre-implementation verification. All items checked against spec + research findings.*

### Constitution Gates

- [x] **Article I** -- No technology versions hardcoded: patches add rule text only, no version literals
- [x] **Article II** -- Frontmatter after patch retains only `name`, `version`, `description`, `allowed-tools`
- [x] **Article II** -- Agent names unchanged: `ava-tobe-spec` ✅ · `ava-stack-dotnet-backend` ✅ (both match `^ava-[a-z0-9-]+$`)
- [x] **Article III** -- N/A: no new phase assignments; existing phase placements unchanged
- [x] **Article IV** -- N/A: `modify-existing` — no new agents, module.yaml unchanged
- [x] **Article V** -- New content in both agent bodies will be in Brazilian Portuguese
- [x] **Article VI** -- Spec section 4 contains 4 scenarios: nominal (S1, S3), edge (S2, S3-AC4), gate (S4)
- [x] **Article VII** -- N/A: no new F1 agent; F2/F3 changes do not affect security sub-pipeline
- [x] **Article VIII** -- N/A: patches add static rule text; no execution flow changes, no trace_id paths
- [x] **Article IX** -- N/A: these are LLM prompt `.md` files, not generated code artifacts
- [x] **Article X** -- MINOR bump for both: `openapi-spec-tobe.md` → `1.1.0` (unversioned→MINOR); `coder-dotnet-backend.md` → `1.0.0`→`1.1.0`
- [x] **Article XI** -- N/A: both agents already have SKILL.md; no new agents created

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec
- [x] Existing output paths unchanged: `openapi-{bc_name}.yaml` · `tobe/source-code/`
- [x] Downstream: `coder-dotnet-backend.md` reads the openapi spec output — chain preserved

**DECISION: PROCEED** ✅

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Agent 1 file | `src/modules/ava-fabric-agents/tobe-architecture/agents/openapi-spec-tobe.md` | Spec §1 |
| Agent 2 file | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` | Spec §1 |
| Agent body language | Brazilian Portuguese (pt-BR) | Constitution Article V |
| Version bump | MINOR (1.1.0) for both | Research R2, R7 |
| Transliteration table size | 25 canonical PT-BR → EN pairs | Research R3 |
| Insertion point — Agent 1 | New `### Guardrail de Idioma` section inside `## Skills`, before `## i18n` | Research R1 |
| Insertion point — Agent 2 | New `### G10` immediately after `### G9` block | Research R2 |
| Single source of truth | Table lives only in `openapi-spec-tobe.md`; G10 cross-references it | Research R3 |
| Sophia validation | Deferred — project not in workspace | Research R5 |

---

## 2. Implementation Steps

### Step 1 — Patch `openapi-spec-tobe.md`: add version + guardrail section

**File**: `src/modules/ava-fabric-agents/tobe-architecture/agents/openapi-spec-tobe.md`

**Change 1a** — Add `version: "1.1.0"` to frontmatter (after `allowed-tools` line)

**Change 1b** — Insert new section `### Guardrail de Idioma — Normalização para Inglês` inside `## Skills`, immediately before `## i18n — Idioma dos Artefatos`. This section must contain:

- Rule header (⚠️ guardrail title, enforcement level: ERROR)
- Transliteration algorithm (5 steps: strip suffix → tokenize → lookup → reconstruct → annotate)
- Canonical transliteration table (25 PT-BR → EN pairs in 5 domain groups)
- `[LANG-NORM]` annotation convention
- `[NEEDS TRANSLATION]` fallback convention

### Step 2 — Patch `coder-dotnet-backend.md`: version bump + G10 + G1-G10 reference

**File**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

**Change 2a** — Update `version: "1.0.0"` → `version: "1.1.0"` in frontmatter

**Change 2b** — Insert `### G10 — Language Normalization — Identificadores C# em inglês` immediately after the G9 block (before `## Clean Architecture Template`). This section must contain:
- Rule title and scope (Controllers, Commands, Queries, Handlers, DTOs, file names, namespaces)
- Explicit exemption for XML doc tags (`<summary>`, `<param>`, `<returns>`) — MAY be PT-BR
- Cross-reference to transliteration table in `openapi-spec-tobe.md`
- Resolution algorithm (3 steps: check if already normalized → apply table → flag unknown)
- `// [G10-NEEDS-TRANSLATION]` annotation convention

**Change 2c** — Update `G1-G9 existentes (non-blocking)` → `G1-G10 existentes (non-blocking)` in the routing guard section

### Step 3 — CHANGELOG.md entry

**File**: `CHANGELOG.md`

Add MINOR entries for both agents documenting PBI #2304.

---

## 3. Project Structure

### Documentation (this feature)

```text
specs/007-api-language-guardrail/
├── spec.md          # Feature specification
├── plan.md          # This file
├── research.md      # Phase 0 research findings
├── data-model.md    # Rule structures and transliteration table design
├── quickstart.md    # Validation guide
└── checklists/
    └── requirements.md
```

### Source Files Modified

```text
src/modules/ava-fabric-agents/
├── tobe-architecture/agents/openapi-spec-tobe.md  ← MINOR patch (version + guardrail)
└── tech-stack/agents/coder-dotnet-backend.md      ← MINOR patch (version + G10)

CHANGELOG.md  ← MINOR entries for both agents
```

---

## 4. Module.yaml Impact

**N/A** — `modify-existing` change type. No new agents, no new module registrations.

Both modules already have their agents registered:

| Module | file | agent |
|---|---|---|
| `tobe-architecture` | `agents/openapi-spec-tobe.md` | `ava-tobe-spec` (no skill listed — registered as internal) |
| `tech-stack` | `agents/coder-dotnet-backend.md` | `ava-stack-dotnet-backend` |

---

## 5. Skill.md Impact

**N/A** — Both agents already have SKILL.md files. The routing/bootstrap behavior of the skills is unchanged; only agent body behavior changes.

---

## 6. Observability & trace_id

**N/A** — These are static LLM prompt instruction files. No execution flow, no trace_id propagation paths added or changed.

---

## 7. Security Impact Assessment

**Minimal / N/A** — Changes are text additions to LLM prompt files. No authentication, authorization, secret handling, or data access logic is modified. No new network calls or storage paths are introduced.

---

## 8. Downstream Impact

| Consumer | Impact |
|---|---|
| `coder-dotnet-backend.md` (reads openapi spec output) | Positive: input is now guaranteed English — G10 becomes a no-op for well-formed inputs |
| `ava-stack-build-validator` | Positive: fewer PT-BR identifier errors in generated C# code |
| F5 QA agents (`ava-qa-scenario-generator`) | Positive: consistent English identifiers improve BDD scenario readability |
| Contract tests | Positive: no more mixed-language path regressions |
| Sophia project (Scenario 4) | **Deferred** — project not in workspace; validate separately |

---

## 9. Complexity Tracking

> No Constitution gate violations. No exceptions required.

---

## Post-Design Constitution Re-check

All gates remain **PASS** after Phase 1 design:

- Transliteration table is embedded in agent body (no external file dependency) ✅
- G10 cross-reference uses a path-safe relative reference ✅
- Output contracts for both agents are **unchanged** ✅
- No hardcoded versions in new content ✅
- PT-BR body language maintained for all new instructional content ✅

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime | .NET 8, C# 12 | reference-architecture.yaml -> tech_stack.backend |
| Frontend | Angular 17, TypeScript 5.3 | reference-architecture.yaml -> tech_stack.frontend |
| ORM | EF Core 8 / Dapper | reference-architecture.yaml -> tech_stack.backend.orm |
| Cloud | Azure Container Apps | reference-architecture.yaml -> tech_stack.infrastructure |
| Observability | OpenTelemetry -> Azure Monitor | reference-architecture.yaml -> tech_stack.observability |
| Security | Azure AD B2C, SonarQube | reference-architecture.yaml -> tech_stack.security |
| Testing | xUnit 2.7, Playwright, k6 | reference-architecture.yaml -> tech_stack.backend.testing |
| IaC | Bicep / Terraform | reference-architecture.yaml -> tech_stack.infrastructure.iac |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

Master pipeline sequence (F4 is a sub-phase of F2, not a standalone step):
```
F1 -> ava-summary -> F2 -> ava-summary -> F3 -> ava-summary
                                       -> F5 -> ava-summary
                                       -> F7 -> ava-summary
                                       -> F6 -> ava-summary (FINAL)
```

This agent's position:
```
F[N-1] Orchestrator -> emits next_agent: ava-[PHASE]-[ROLE]
F[N] -> [THIS AGENT] -> ava-[NEXT_AGENT]
     -> emits next_agent: ava-[NEXT_AGENT_OR_ORCHESTRATOR]
F[N] Orchestrator -> ava-summary (invoked after every phase completes)
```

**Quality gate at this phase**: [security_gate (F1) | requestor-inspection (pre-F3) | package-approval (pre-F3) | security-compliance (F6) | summary-validator (after every phase) | none]

Conditions for `human_gate_required: true`:
- [CONDITION_1] -- e.g. risk.level >= high
- [CONDITION_2] -- e.g. findings severity == critical

---

## 3. Clean Architecture Alignment

```
Domain         -> [YES/NO] -- [entities / value objects affected]
Application    -> [YES/NO] -- [use cases / commands / DTOs affected]
Infrastructure -> [YES/NO] -- [repos / external adapters affected]
Presentation   -> [YES/NO] -- [controllers / middleware affected]
```

Cross-layer coupling: [NONE | document here, justify in section 9]

---

## 4. Agent File Structure

Skill/Agent two-layer split (Constitution Article XI):

```
.github/skills/ava-[PHASE]-[ROLE]/
+-- SKILL.md                         <- routing wrapper (user-facing agents only)

src/modules/ava-fabric-agents/[MODULE_FOLDER]/agents/
+-- [agent-role].md                  <- frontmatter + Portuguese body
    +-- Optional: templates/
    +-- Optional: skills/
```

**Agent frontmatter** (correct fields — see Constitution Article II):
```yaml
---
name: "ava-[PHASE]-[ROLE]"
version: "1.0.0"
description: |
  [Portuguese description + "Ativa com: ..."]
allowed-tools: Read, Write, Edit
---
```

**Dispatch mode**: [user-facing (SKILL.md required) | internal-only (orchestrator dispatches)]

If user-facing: SKILL.md must (1) resolve `project_name`, (2) read `agent-task-config.yaml` + `shared-context.md`, (3) delegate to agent `.md`.

**Shared resources**: agent-task.schema.json | agent-result.schema.json | reference-architecture.yaml | mermaid-guardrails.md

---

## 5. module.yaml Impact

New agents register in the **module-level** `module.yaml` (Constitution Article IV):

```
src/modules/ava-fabric-agents/[MODULE_FOLDER]/module.yaml
```

Diff to apply:
```yaml
agents:
  # ... existing agents ...
  - id: ava-[PHASE]-[ROLE]           # [NEW]
    file: agents/[agent-role].md
    skill: ava-[PHASE]-[ROLE]        # omit this line if internal-only
```

The **top-level** `module.yaml` at the project root only needs updating when
creating an entirely new phase/module. Do NOT update it for agents added to
an existing phase.

---

## 6. Observability & Trace Propagation

> **For most agents**: this section is N/A. IMFAI agents are LLM prompt files that
> write markdown artifacts. They do not explicitly handle trace_id in their body.
> Skip this section unless this agent directly invokes the JSON schema pipeline
> (`agent-task.schema.json` / `agent-result.schema.json`).

If this agent uses the JSON schema pipeline:
```
Input: AgentTask.trace_id -> [copied unchanged] -> Output: AgentResult.trace_id
```

Activation phrases in agent `description` implicitly handle context routing.
The SKILL.md wrapper provides trace context through `shared-context.md`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| agent-task.schema.json | YES / NO | [description] |
| agent-result.schema.json | YES / NO | [description] |

> Schema change = MINOR or MAJOR version bump (Constitution Article IX).

---

## 8. Implementation Phases

**Phase 0** -- Frontmatter: write `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools`; verify agent name pattern; write `## Output Contract` block.

**Phase 1** -- Body: responsibility, numbered instructions, output format specs, security notes.

**Phase 2** -- Gate Logic: risk scoring, human_gate_required conditions, next_agent logic.

**Phase 3** -- BDD: confirm spec section 4, map to F5 QA, identify automation targets.

**Phase 4** -- Registration: module.yaml, agents-catalog.md, CHANGELOG.md, orchestrator deps.

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| [GATE_NAME] | [What failed] | [Why acceptable] | [How risk managed] |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Contract (input) | JSON Schema | 100% of AgentTask paths |
| Contract (output) | JSON Schema | 100% of AgentResult paths |
| Nominal BDD | xUnit | Spec section 4 Scenario 1 |
| Edge case BDD | xUnit | Spec section 4 Scenario 2 |
| Gate trigger | xUnit | Spec section 4 Scenario 3 |
| Regression | Existing suite | No existing agent broken |
