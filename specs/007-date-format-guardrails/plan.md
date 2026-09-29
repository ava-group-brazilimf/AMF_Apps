# Implementation Plan: Date Format Guardrails

**Branch**: `007-date-format-guardrails` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-date-format-guardrails/spec.md`

---

## Summary

| Field | Value |
| --- | --- |
| **Change Type** | `modify-existing` (2 agent files + 1 shared reference document) |
| **Primary Requirement** | Enforce ISO 8601 UTC on backend DTOs and pt-BR locale + explicit DatePipe format on Angular frontend |
| **Technical Approach** | **All guardrail content already exists.** Remaining work: version bumps (1.0.0 → 1.1.0) on both agent files, consolidation of duplicate YAML frontmatter in `coder-angular-frontend.md`, and a `CHANGELOG.md` entry |

---

## Technical Context

**Language/Version**: Markdown agent instruction files; YAML frontmatter (no runtime language)

**Primary Dependencies**:
- `coder-dotnet-backend.md` (F3 tech-stack module) — `version: "1.0.0"` → `"1.1.0"`
- `coder-angular-frontend.md` (F3 tech-stack module) — `version: "1.0.0"` → `"1.1.0"`; frontmatter deduplication
- `angular-patterns-reference.md` (shared data/patterns) — content complete; no structural changes

**Storage**: N/A — no database or file storage contract changes

**Testing**: Validation via `quickstart.md` grep/Select-String commands

**Target Platform**: Agent instruction files consumed by GitHub Copilot / Claude Code

**Performance Goals**: N/A

**Constraints**: Must not change any `## Output Contract` section (would require MAJOR bump); must not hardcode framework versions (Article I)

**Scale/Scope**: 3 files, ~3 line changes total (version bumps + frontmatter fix) + 4-line CHANGELOG entry

---

## Constitution Check

- [x] **Article I** — No technology versions hardcoded; guardrail text references `DateTimeKind`, `DatePipe` patterns only, with version resolved at runtime from `tobe_stack.*`
- [x] **Article II** — Frontmatter fix removes duplicate keys; single well-formed block after the change; `version: "1.1.0"` follows SemVer; agent name unchanged
- [x] **Article V** — Guardrail text is in Brazilian Portuguese; no English instruction bodies
- [x] **Article X** — New guardrail content = new behavior added = MINOR bump (1.0.0 → 1.1.0); no MAJOR bump needed (Output Contract unchanged)
- [x] **Article XI** — Modify-existing change; no new SKILL.md required; SKILL.md routing unchanged
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## Project Structure

### Documentation (this feature)

```text
specs/007-date-format-guardrails/
├── spec.md           ✅ created by /speckit.specify
├── plan.md           ✅ this file
├── research.md       ✅ Phase 0 output
├── data-model.md     ✅ Phase 1 output
├── quickstart.md     ✅ Phase 1 output
├── tasks.md          ← Phase 2 output (/speckit.tasks — NOT created here)
└── checklists/
    └── requirements.md  ✅ created by /speckit.specify
```

### Source Code (changes)

```text
src/modules/ava-fabric-agents/tech-stack/agents/
├── coder-dotnet-backend.md      ← version: "1.0.0" → "1.1.0"  (line 10)
└── coder-angular-frontend.md    ← frontmatter dedup + version → "1.1.0"

src/shared/data/patterns/angular/
└── angular-patterns-reference.md  ← NO CHANGE (content already complete)

CHANGELOG.md  ← add entries for both version bumps
```

---

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO

See [research.md](research.md).

**Key finding**: All three primary guardrail changes (G10, G-DATE, Padrões de Data e Hora)
already exist in the target files — added as a hotfix before this spec was formalized.
Remaining work is purely administrative: version bumps + frontmatter deduplication.

### Phase 1 — Design ✅ CONCLUÍDO

See [data-model.md](data-model.md) and [quickstart.md](quickstart.md).

- Delta spec defined: only frontmatter changes + CHANGELOG entry remain
- Frontmatter fix specified: duplicate `version`/`date` keys → single `version: "1.1.0"`, `date: 2026-07-07`
- Validation scenarios defined in quickstart.md (4 scenarios, all PowerShell-executable)

### Phase 2 — Implementation

Three atomic changes, executable in any order:

| Step | File | Change |
| --- | --- | --- |
| 2.1 | `coder-dotnet-backend.md` | Bump `version: "1.0.0"` → `version: "1.1.0"` |
| 2.2 | `coder-angular-frontend.md` | Remove first duplicate `version`/`date` pair; bump surviving `version` to `"1.1.0"`, `date` to `2026-07-07` |
| 2.3 | `CHANGELOG.md` | Add entries for both agent version bumps under `## [Unreleased]` |

### Phase 3 — Verification

Run all four validation scenarios from [quickstart.md](quickstart.md):

- Scenario A: G10 present + version 1.1.0 in backend agent
- Scenario B: G-DATE present + no duplicate keys + version 1.1.0 in frontend agent
- Scenario C: "Padrões de Data e Hora" present in reference doc
- Scenario D: CHANGELOG records both version bumps

---

## Complexity Tracking

No Constitution violations. No cross-layer coupling. No complexity to justify.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-[PHASE]-[ROLE]` |
| **Phase** | `F[N]` |
| **Module** | `[MODULE_ID]` |
| **Primary Requirement** | [One sentence from spec section 1 Role] |
| **Technical Approach** | [One sentence summary] |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9).*

### Constitution Gates

- [ ] **Article I** -- No technology versions hardcoded in agent body
- [ ] **Article II** -- Frontmatter contains ONLY: `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools`
- [ ] **Article II** -- agent `name` matches pattern `^ava-[a-z0-9-]+$`
- [ ] **Article III** -- Phase placement valid (F[N] receives from F[N-1] orchestrator; ava-summary runs after every phase)
- [ ] **Article IV** -- Module-level `module.yaml` diff prepared (see Plan section 5)
- [ ] **Article V** -- Agent body language is Brazilian Portuguese
- [ ] **Article VI** -- BDD scenarios in spec section 4 (nominal + edge + gate paths)
- [ ] **Article VII** -- Security sub-pipeline impact assessed
- [ ] **Article VIII** -- trace_id propagation documented (see Plan section 6)
- [ ] **Article IX** -- Clean Architecture layer ordering respected
  > ℹ️ **LLM prompt agents**: mark this N/A — Clean Architecture applies to generated *code* artifacts (F3 codegen), not `.md` instruction files. Complete section 3 with `NO` for all layers and note "agent is an LLM prompt file".
- [ ] **Article X** -- Version bump type determined: MAJOR / MINOR / PATCH
- [ ] **Article XI** -- Skill/Agent split declared (SKILL.md path or internal-only with justification)

### Quality Gate Check

- [ ] No [NEEDS CLARIFICATION] markers remain in spec
- [ ] All outputs follow projects/{project_name}/outputs/[phase]/...
- [ ] Downstream next_agent confirmed to exist

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
