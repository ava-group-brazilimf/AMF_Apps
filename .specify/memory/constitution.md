# AVA Fabric Agents — IMFAI Constitution

> This constitution governs the **development of agents and modules** within the
> IMFAI (`ava-fabric-agents`) project. It applies whenever a new agent is created,
> an existing agent is modified, or a phase is extended. Agents produced under this
> constitution target enterprises migrating legacy systems (Delphi, VB6, COBOL,
> PowerBuilder) to cloud-native .NET / Azure.

---

## Core Principles

### I. Configuration-Driven (NON-NEGOTIABLE)

No agent may hardcode technology versions, cloud regions, stack choices, or
environment identifiers. All such values are resolved at runtime from:

- `projects/{PROJECT_NAME}/context/project-config.yaml` — per-project overrides
- `src/shared/data/reference-architecture.yaml` — canonical technology reference
- `docs/architecture/ConfigStackDotNet.yaml` — stack-specific defaults

Agents MUST reference these sources by documented key paths, never by literal
values.

### II. Agent Contract Standard (NON-NEGOTIABLE)

Every agent `.md` file MUST begin with a YAML frontmatter block conforming to:

```yaml
---
name: "ava-{phase}-{role}"   # e.g. ava-asis-solution-delphi
version: "MAJOR.MINOR.PATCH" # Semantic versioning (SemVer)
description: |               # Multi-line: what the agent does + activation phrases
  [1-2 sentences describing the agent's responsibility in Portuguese.]
  Ativa com: "[phrase 1]", "[phrase 2]", "[phrase 3]".
allowed-tools: Read, Write, Edit   # Space-separated Claude Code tool names
                                   # Valid values: Read Write Edit Glob Grep Bash
---
```

**What does NOT go in frontmatter** (common mistake to avoid):
- `phase`, `module`, `inputs`, `outputs`, `dependencies` — these are NOT frontmatter fields.
  Phase ownership is implied by the naming convention `ava-{phase}-{role}`.

**Output Contract** belongs in the agent body as a `## Output Contract` section:

```yaml
## Output Contract
```yaml
outputs:
  artifact_name: "projects/{project_name}/outputs/{phase}/{filename}.md"
  metrics_json:  "projects/{project_name}/outputs/{phase}/{filename}.json"
```
```

Note: output paths use **lowercase** `{project_name}`, not `{PROJECT_NAME}`.

The `name` field must match pattern `^ava-[a-z0-9-]+$`.

### III. Pipeline Execution Contract

The master-orchestrator executes phases in the following strict sequence:

```
F1 → ava-summary → F2 → ava-summary → F3 → F3S → ava-summary → F4 → ava-summary
                                   → F5 → ava-summary
                                   → F6 → ava-summary
                                   → F7 → ava-summary (FINAL)
```

**F3S — SpecKit Planning** sits between the prototype and code generation. It is not
optional and it is not a sub-phase: `ava-speckit-orchestrator` dispatches it as its own
top-level step. Its position is causal — `spec-prototype.md` needs F3 as a source, and the
F4 coders need its tasks as input. See `specs/039-speckit-planning-layer/`.

`ava-summary` is invoked **after every phase** — not only at the end. F3
(Prototype) is dispatched by the master-orchestrator directly, as its own
top-level step right after F2/TO-BE completes — it is **not** a sub-phase
nested inside another orchestrator. The correct master sequence is
**F1→F2→F3→F3S→F4→F5→F6→F7** (AS-IS → TO-BE → Prototype → SpecKit Planning →
Stack → QA → DevOps → Deliverables).

Mandatory quality gates:

| Gate | Position | Trigger |
|---|---|---|
| `security_gate` (F1 Consistency Gate C1–C8) | After F1 | `BLOCKED` → F2 cannot start |
| `human_gate` | Within F1 | `human_gate_required: true` when risk.level ≥ high |
| F2 AS-IS Quality Gate | Before F2 body | 17 mandatory F1 artifacts must be non-empty |
| F3S Entry Gate (`artifact_gate_speckit.py --gate entry`) | Before F3S | Missing TO-BE or prototype input → F3S aborts, no partial generation |
| F3S Exit Gate (`artifact_gate_speckit.py --gate exit`) | After F3S, before F4 | `speckit_traceability` + `prototype_coverage` must both exit 0 → otherwise F4 does not start |
| Requestor Inspection (`ava-requestor-inspection`) | Before F3 Build Cycle | 9 artifact groups A–I must be `APPROVED` |
| Package Approval Doc | Before F3 Build Cycle | Human SME signature required |
| Security Compliance Gate | F7 | `BLOCKED` → prevents client delivery |
| Summary Validator (55 rules, 10 categories) | After every phase | Exit 1 → blocks promotion |

- Every phase has exactly one orchestrator agent that coordinates all agents in that phase.
- Agents MUST NOT skip phases or call agents from non-adjacent phases.
- Phase orchestrators emit `next_agent` pointing to the next phase's orchestrator upon completion.
- The Summary HTML is **exclusively** produced by `build_summary_comprehensive.py` — never generated inline.

### IV. Module Registration (NON-NEGOTIABLE)

Every new agent must be registered in the **module-level** `module.yaml` before
the spec is considered complete. Each phase has its own module registry:

```
src/modules/ava-fabric-agents/{module-id}/module.yaml
```

For example: `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml`

The module-level `module.yaml` format:
```yaml
agents:
  - id: ava-{phase}-{role}           # agent ID
    file: agents/{role}.md           # path relative to module root
    skill: ava-{phase}-{role}        # skill name (omit if internal-only)
```

The **top-level** `module.yaml` at the repo root only needs updating when an
entirely new module (phase) is created — not when adding agents to an existing phase.
Module IDs are lowercase-hyphenated (e.g., `asis-diagnostic`).

### V. Language Convention

All agent instruction bodies (sections after the frontmatter) MUST be written in
**Brazilian Portuguese** (`pt-BR`). This applies to:
- `## Papel & Persona` (Role & Persona)
- `## Habilidades` / `## Skills`
- `## Contrato de Saída` / `## Output Contract`
- All instruction steps, rules, and guardrails

Frontmatter fields (`name`, `version`, `description`, `allowed-tools`) use
mixed language: field keys are English, `description` content is Portuguese.

SKILL.md files (`.github/skills/`) use Portuguese for instruction text.

### VI. Test-First Agent Behavior

Before implementing agent behavior (instructions / prompts), BDD scenarios in
Given-When-Then format must be written for:

1. Nominal path (well-formed legacy input → expected artifacts produced)
2. Edge case (missing fields, empty codebase, unknown tech version)
3. Quality gate path (when risk is high, `human_gate_required` = true)

Scenarios drive both the agent instruction design and the F5 QA test cases.

### VII. Security-First (F1 Mandatory)

Every F1 AS-IS diagnostic MUST include a security sub-pipeline covering SAST,
dependency scanning, threat modeling, OWASP Top 10, and LGPD/GDPR compliance.
No new F1 agent may bypass the security orchestrator (`ava-asis-security-orchestrator`).
Security findings propagate to the risk register in `AgentResult.risk`.

### VIII. Observability & Traceability

- Every agent must propagate `trace_id` (UUID) from input to output without mutation.
- Agents emitting diagrams use Mermaid v11+ syntax validated against
  `src/shared/templates/diagrams/mermaid-guardrails.md`.
- Structured logs use W3C Trace Context correlation IDs (OpenTelemetry).
- Agents MUST NOT write to stdout/stderr in ways that corrupt structured JSON output.

### IX. Clean Architecture Alignment

Generated code artifacts follow the mandatory layer order:

```
Domain → Application → Infrastructure → Presentation
```

- Domain: entities, value objects, domain events, interfaces
- Application: use cases, commands/queries (CQRS via MediatR), DTOs, validators
- Infrastructure: EF Core repos, external service adapters, migrations
- Presentation: ASP.NET Core controllers, middleware, health checks

No layer may reference a layer above it. Cross-layer coupling justifications must
be documented in the plan's Complexity Tracking section.

### X. Versioning & Breaking Changes

- Agent versions follow `MAJOR.MINOR.PATCH` (SemVer).
- Changing `inputs` or `outputs` contract = MAJOR bump.
- Adding optional fields = MINOR bump.
- Bug fixes in agent instructions = PATCH bump.
- Breaking changes require migration notes in `CHANGELOG.md`.

### XI. Skill/Agent Separation (NON-NEGOTIABLE)

Every user-facing agent MUST be split into two distinct files:

| Layer | Location | Responsibility |
|---|---|---|
| **SKILL.md** | `.github/skills/ava-{phase}-{role}/SKILL.md` | Thin routing wrapper: resolves `project_name` from `project-config.yaml`, reads `agent-task-config.yaml` + `shared-context.md`, delegates to the agent body |
| **Agent `.md`** | `src/modules/ava-fabric-agents/{module}/agents/{role}.md` | All actual behavior: guardrails, output contracts, execution steps, quality gate logic |

To change **routing or bootstrap logic** → edit the SKILL.md.  
To change **behavior, output format, or gate logic** → edit the agent `.md`.

Some agents are **internal-only** (dispatched by orchestrators, no SKILL.md):
- Agents marked `_(no skill — internal)_` in phase agent tables
- All security sub-agents under `ava-asis-security-orchestrator`
- All build-cycle template agents under `tech-stack/templates/`

A spec proposing a new user-facing agent MUST declare whether it will have a SKILL.md
or be internal-only, and justify the choice.

---

## Quality Gate Requirements

### Pre-implementation Gates (checked by `/speckit.plan`)

- [ ] Agent `name` follows `ava-{phase}-{role}` pattern and matches `^ava-[a-z0-9-]+$`
- [ ] Frontmatter contains ONLY `name`, `version`, `description`, `allowed-tools`
- [ ] `description` is in Portuguese and includes activation phrases
- [ ] `allowed-tools` lists only valid Claude Code tool names
- [ ] `## Output Contract` YAML block uses lowercase `{project_name}` in paths
- [ ] Agent body language is Brazilian Portuguese (Article V)
- [ ] BDD scenarios written for nominal, edge, and gate paths (Article VI)
- [ ] Security sub-pipeline impact assessed (Article VII)
- [ ] No technology versions hardcoded in agent body (Article I)

### Architecture Gates (checked by `/speckit.plan`)

- [ ] Clean Architecture layer ordering respected (Article IX)
- [ ] `trace_id` propagation documented (Article VIII)
- [ ] Module-level `module.yaml` diff included in plan (Article IV)
- [ ] `CHANGELOG.md` entry prepared if MAJOR/MINOR bump (Article X)
- [ ] Skill/Agent split declared: SKILL.md or internal-only, with justification (Article XI)

---

## Technology Reference

Canonical technology choices (agents must reference, not override):

| Layer | Technology |
|---|---|
| Backend runtime | .NET 8, C# 12, ASP.NET Core 8 |
| ORM / micro-ORM | EF Core 8 / Dapper |
| Mediator | MediatR 12 |
| Frontend | Angular 17, TypeScript 5.3, NgRx Signals |
| Cloud | Microsoft Azure (Container Apps, API Management, Service Bus) |
| IaC | Bicep / Terraform |
| Observability | OpenTelemetry → Azure Monitor / Application Insights |
| Security | Azure AD B2C, OAuth2/OIDC, Azure Key Vault, SonarQube |
| Testing | xUnit 2.7, Moq, FluentAssertions, Testcontainers, Jest, Playwright, k6 |

Source: `src/shared/data/reference-architecture.yaml` (version 1.0.0)

---

## Governance

- This constitution supersedes all agent-level comments, inline assumptions, and
  prior informal conventions.
- Amendments require: (1) documented rationale, (2) update to this file with new
  version number, (3) backwards-compatibility assessment.
- All `/speckit.plan` outputs must pass Pre-implementation Gates before proceeding.
- Complexity exceptions must be logged in the plan's Complexity Tracking table
  with explicit justification.
- BMAD framework compatibility: `bmad_version: >=6.0.0` must be preserved in
  the top-level `module.yaml`.

**Version**: 1.5.0 | **Ratified**: 2026-06-17 | **Last Amended**: 2026-08-12

> **v1.5.0 amendment rationale**: Added **F3S — SpecKit Planning** between F3 and F4, with
> its entry and exit gates in the mandatory quality gate table. The amendment is not a
> reorganisation: it records a phase that did not exist. The audit of
> `nopcommerce-02-cli-ava` measured prototype fidelity at 13%, business rules at 17%, API
> conformance at 14% and a failing `dotnet build` behind a report that declared
> `PASS (Simulated)`. Two mechanical causes sat upstream of prompt quality: no TO-BE
> artifact ever reached the code generator, and F4 was a single 140-file dispatch against a
> 128k output ceiling. F3S produces the intermediate contract and the traceability spine
> that make code generation divisible and verifiable. No existing phase was renumbered —
> the `F3S` suffix was chosen precisely to avoid renumbering F4..F8, which appear in agent
> prose, reports and already-delivered artifacts. See `specs/039-speckit-planning-layer/`.

> **v1.4.0 amendment rationale**: Corrected the canonical pipeline phase order.
> Prototype was previously documented as "F4, a sub-phase of F2" with no
> standalone dispatch; it is now F3, a real top-level step dispatched directly
> by `master-orchestrator.md` right after F2/TO-BE completes. Stack moved
> F3→F4, DevOps moved F7→F6, Deliverables moved F6→F7. QA (F5) and Summary
> (cross-cutting, referenced as F8 where a label is needed) are unchanged.
> This reconciles Article III, the Phase → Module Mapping table, and the
> Output Path Conventions table, which previously each disagreed with each
> other and with `master-orchestrator.md`'s own actual dispatch order.

---

## Project Reference

> This section is a concrete lookup table for use when filling in spec, plan, and task
> templates. It does not introduce new principles — it maps the abstractions above to
> real paths in this repository.

### Phase → Module Mapping

| Phase | Module ID | Module folder | Orchestrator agent |
|---|---|---|---|
| F1 — AS-IS Diagnostic | `asis-diagnostic` | `src/modules/ava-fabric-agents/asis-diagnostic/` | `ava-asis-orchestrator` |
| F2 — TO-BE Architecture | `tobe-architecture` | `src/modules/ava-fabric-agents/tobe-architecture/` | `ava-tobe-orchestrator` |
| F3 — Prototype | `prototype` | `src/modules/ava-fabric-agents/prototype/` | _(dispatched directly by master-orchestrator)_ |
| F3S — SpecKit Planning | `speckit` | `src/modules/ava-fabric-agents/speckit/` | `ava-speckit-orchestrator` |
| F4 — Stack / Codegen | `tech-stack` | `src/modules/ava-fabric-agents/tech-stack/` | `ava-stack-orchestrator` |
| F5 — QA | `qa-agents` | `src/modules/ava-fabric-agents/qa-agents/` | `ava-qa-orchestrator` |
| F6 — DevOps | `devops-agents` | `src/modules/ava-fabric-agents/devops-agents/` | _(sequential)_ |
| F7 — Deliverables | `deliverables` | `src/modules/ava-fabric-agents/deliverables/` | _(sequential)_ |
| F8 — Summary (cross-cutting) | `summary` | `src/modules/ava-fabric-agents/summary/` | `ava-summary` |

### Output Path Conventions

| Phase | Output folder (relative to project root) |
|---|---|
| F1 AS-IS artifacts | `projects/{project_name}/outputs/asis/` |
| F2 TO-BE docs | `projects/{project_name}/outputs/tobe/docs/` |
| F2 TO-BE decisions (ADRs) | `projects/{project_name}/outputs/tobe/docs/decisions/` |
| F3 Prototype | `projects/{project_name}/outputs/tobe/prototype/` |
| F3S SpecKit planning | `projects/{project_name}/outputs/tobe/speckit/` — `specs/NNN-slug/{spec,plan,tasks}.md` |
| F4 Generated source code | `projects/{project_name}/outputs/tobe/source-code/` |
| F5 QA artifacts | `projects/{project_name}/outputs/qa/` |
| F6 DevOps / IaC | `projects/{project_name}/outputs/tobe/devops/` |
| F7 Deliverables | `projects/{project_name}/outputs/deliverables/` |
| F8 Summary HTML | `projects/{project_name}/outputs/summary/` |

### `allowed-tools` Guidelines by Phase

| Phase type | Typical tools | Reason |
|---|---|---|
| F1 analysis (read-only) | `Read, Glob, Grep, Bash` | Scans legacy source, runs metrics |
| F2 design (write docs) | `Read, Write, Edit` | Produces architecture documents |
| F3 prototype (write) | `Read, Write, Edit` | Produces navigable HTML demo |
| F4 codegen (write code) | `Read, Write, Edit, Bash` | Scaffolds + runs build scripts |
| F5 QA (write + test) | `Read, Write, Edit, Bash, Glob` | Generates scenarios + runs scripts |
| F6/F7 (package/deploy) | `Read, Write, Edit` | Produces delivery artifacts |
| F8 summary (build) | `Read, Write, Edit, Bash` | Invokes Python build script |

### Resolving `project_name` at Runtime

All SKILL.md files resolve the active project name using this standard sequence:

1. Read `projects/_template/context/project-config.yaml` → field `project_name`
2. If absent or empty, ask the user: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use `{project_name}` to resolve all output paths: `projects/{project_name}/outputs/...`

The project config lives at: `projects/{project_name}/context/project-config.yaml`  
The shared agent context lives at: `projects/{project_name}/context/shared-context.md`

### Key Shared Resource Paths

| Resource | Path |
|---|---|
| Reference architecture (canonical tech stack) | `src/shared/data/reference-architecture.yaml` |
| Agent input schema | `src/shared/schemas/agent-task.schema.json` |
| Agent output schema | `src/shared/schemas/agent-result.schema.json` |
| Mermaid guardrails | `src/shared/templates/diagrams/mermaid-guardrails.md` |
| Wave approval schema | `src/shared/schemas/wave-approval.schema.json` |
| Agents catalog | `docs/agents-catalog.md` |
| Full pipeline guide | `docs/full-pipeline-guide.md` |
| Readiness gate checklist | `src/shared/checklists/readiness-gate-checklist.md` |

### Existing Agent Counts (as of v1.3.0)

| Phase | Agents | Internal-only |
|---|---|---|
| F1 | 15 (incl. 7 security sub-agents) | 3 (gap-migration-analyzer, events-pubsub, solution-vb) |
| F2 | 21 | 8 (database-policy, database-design, risk-mitigation, spec, nuget-policy, designer-system, developer-guide, azure-infra-estimator) |
| F3 | 1 (ava-prototype) | 0 |
| F4 | 5 build-cycle + 5 generic coders | all build-cycle agents |
| F5 | 9 | 0 |
| F6 | 7 (incl. cloud-specific stubs) | 2 (build-cycle-iac, monitoring-observability) |
| F7 | 10 | 0 |
| F8 | 2 | 1 (summary-validate) |
