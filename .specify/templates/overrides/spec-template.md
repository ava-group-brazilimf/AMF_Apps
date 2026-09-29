# Agent Specification: [AGENT_NAME]

**Feature Branch**: `[###-agent-role]`
**Created**: [DATE]
**Status**: Draft
**Change Type**: [new-agent | modify-existing | bugfix]
**Input**: Agent description: "$ARGUMENTS"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-[PHASE]-[ROLE]` |
| **Version** | `1.0.0` |
| **Phase** | `F[N]` |
| **Module** | `[MODULE_ID]` |
| **Role** | [One-sentence description of what this agent does] |
| **Skill** | `ava-[PHASE]-[ROLE]` <!-- or: _(no skill -- internal)_ if dispatched only by orchestrator --> |
| **Dispatch** | [user-facing via SKILL.md \| internal-only via orchestrator] |

> **If Change Type is `modify-existing` or `bugfix`**:
> - Reference the existing agent file path (do not create a new file)
> - Determine version bump type: MAJOR (contract change) / MINOR (new field) / PATCH (fix)
> - The module.yaml entry already exists — Category 4 tasks are N/A
> - The SKILL.md already exists (if user-facing) — Category 1.5 is N/A

---

## 2. Agent Frontmatter

The agent `.md` file opens with YAML frontmatter (Constitution Article II):

```yaml
---
name: "ava-[PHASE]-[ROLE]"   # e.g. ava-asis-gdpr-check
version: "1.0.0"
description: |
  [1-2 sentences in Portuguese describing the agent's responsibility.]
  Ativa com: "[activation phrase 1]", "[activation phrase 2]", "[activation phrase 3]".
allowed-tools: Read, Write, Edit   # Claude Code tools: Read Write Edit Glob Grep Bash
---
```

Do NOT include `phase`, `module`, `inputs`, `outputs`, or `dependencies` in frontmatter.
These are not valid frontmatter fields in IMFAI agents.

---

## 3. Output Contract

The `## Output Contract` YAML block in the agent body (Constitution Article II):

```yaml
## Output Contract
```yaml
outputs:
  [artifact_name]:  "projects/{project_name}/outputs/[phase]/[filename].md"
  [metrics_file]:   "projects/{project_name}/outputs/[phase]/[filename].json"
  # Add one entry per artifact. Use lowercase {project_name} (not {PROJECT_NAME}).
```
```

> **New file vs. append decision**: Before listing artifacts, check whether this agent
> writes to a *new* file or *appends to an existing* one (e.g., `risk-register.json`).
> Appending to an existing contract file preserves downstream parser compatibility
> (e.g., `build_summary_comprehensive.py` — check `src/modules/ava-fabric-agents/summary/utils/`
> before creating a separate output file).

Path conventions:
| Phase | Output folder |
|---|---|
| F1 (AS-IS) | `projects/{project_name}/outputs/asis/` |
| F2 (TO-BE arch) | `projects/{project_name}/outputs/tobe/docs/` |
| F3 (codegen) | `projects/{project_name}/outputs/tobe/source-code/` |
| F5 (QA) | `projects/{project_name}/outputs/qa/` |
| F7 (DevOps) | `projects/{project_name}/outputs/tobe/devops/` |
| F6 (Deliverables) | `projects/{project_name}/outputs/deliverables/` |

---

## 4. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions (`**Story**:`) may be written in
> Brazilian Portuguese — IMFAI developers and client stakeholders read them.
> Acceptance scenarios (Given/When/Then) MUST be in English for BDD traceability
> with F5 QA agents (`ava-qa-behavior-mapping`, `ava-qa-scenario-generator`).

### Scenario 1 - Nominal Path (Priority: P1)

**Story**: As the migration orchestrator, I want [AGENT_NAME] to [PRIMARY_BEHAVIOR] so that [BUSINESS_OUTCOME].

**Why this priority**: [Value delivered]

**Acceptance Scenarios**:

1. **Given** a [LEGACY_TECHNOLOGY] project with a valid AgentTask, **When** the agent executes, **Then** it produces [PRIMARY_ARTIFACT] and `AgentResult.success` is true.
2. **Given** the above, **When** execution completes, **Then** `AgentResult.artifacts` lists all files and `AgentResult.next_agent` is set.

---

### Scenario 2 - Edge Case: Empty Codebase (Priority: P2)

**Why this priority**: Defensive handling of incomplete inputs.

**Acceptance Scenarios**:

1. **Given** a codebase with no [RELEVANT_CONTENT], **When** the agent executes, **Then** it produces an artifact noting absence and `AgentResult.success` is true.
2. **Given** the above, **Then** `AgentResult.risk.level` is 'low'.

---

### Scenario 3 - Quality Gate: High-Risk Finding (Priority: P1)

**Why this priority**: Safety gate -- must never be skipped.

**Acceptance Scenarios**:

1. **Given** analysis reveals [HIGH_RISK_CONDITION], **When** the agent executes, **Then** `AgentResult.risk.level` is 'high' or 'critical' and `AgentResult.human_gate_required` is true.
2. **Given** the above, **Then** `AgentResult.risk.findings` has severity >= 'high' and orchestrator pauses.

---

## 5. Quality Gate Requirements

- [ ] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [ ] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] Agent registered in module-level `module.yaml` diff included in plan (Article IV)
- [ ] All output paths use lowercase `{project_name}` and correct phase folder (Article II)
- [ ] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [ ] Security sub-pipeline impact assessed (Article VII)
- [ ] No technology versions hardcoded (Article I)
- [ ] Skill/Agent split declared: SKILL.md or internal-only with justification (Article XI)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Phase orchestrator | `ava-[PHASE]-orchestrator` | Must complete before this agent runs |
| [OTHER_DEPENDENCY] | `ava-[PHASE]-[ROLE]` | [Why this output is needed] |

---

## 7. Exclusions

- [EXCLUSION_1] -- handled by `ava-[OTHER_AGENT]`
- [EXCLUSION_2] -- out of scope

---

## 8. Assumptions

- [ASSUMPTION_1] -- e.g. 'The legacy repo is cloned at repository_path'
- [ASSUMPTION_2] -- e.g. 'project-config.yaml exists at `projects/{project_name}/context/`'

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Artifacts produced | All paths in section 3 exist after execution |
| Contract compliance | AgentResult validates against agent-result.schema.json |
| Gate accuracy | human_gate_required correctly set when risk >= high |
| No regression | Existing agents in module are unaffected |
