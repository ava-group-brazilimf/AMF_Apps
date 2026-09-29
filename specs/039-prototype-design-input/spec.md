# Agent Specification: Client Design Input for Prototype

**Feature Branch**: `039-prototype-design-input`
**Created**: 2026-08-10
**Status**: Draft
**Change Type**: bugfix
**Input**: Agent description: "Modify ava-prototype so it consumes an existing client design file from the project input directory, applies client design precedence, documents provenance and gaps, and never generates a `.fig` file."

> **Language note**: This specification is written in English. The modified agent body MUST remain in Brazilian Portuguese per Constitution Article V.

---

## 1. Agent Identity

| Field        | Value                                                                                     |
| ------------ | ----------------------------------------------------------------------------------------- |
| ---          | ---                                                                                       |
| **Agent ID** | `ava-prototype`                                                                           |
| **Version**  | `1.3.0`                                                                                   |
| **Phase**    | `F3`                                                                                      |
| **Module**   | `prototype`                                                                               |
| **Role**     | Generate a navigable HTML prototype using client-provided design evidence when available. |
| **Skill**    | `ava-prototype`                                                                           |
| **Dispatch** | user-facing via existing SKILL.md and directly dispatched by the master orchestrator      |

**Existing agent file**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`.

**Version rationale**: MINOR bump because the agent gains an optional declarative input and new traceability metadata while preserving the existing mandatory business-rules input and prototype output flow.

---

## 2. Agent Frontmatter

The existing frontmatter remains limited to `name`, `version`, `description`, and `allowed-tools`. The description will be updated in Portuguese to state that the agent consumes client design input when available and falls back deterministically when absent.

No new agent, skill, or module is created. The existing `prototype/module.yaml` registration remains valid and its version/output metadata must be reviewed for consistency with the updated contract.

---

## 3. Output Contract

```yaml
outputs:
  prototype_html: "projects/{project_name}/outputs/tobe/prototype/index.html"
  demo_script: "projects/{project_name}/outputs/tobe/prototype/demo-script.md"
  figma_spec: "projects/{project_name}/outputs/tobe/prototype/figma-spec.md"
  readme: "projects/{project_name}/outputs/tobe/prototype/README.md"
  design_tokens: "projects/{project_name}/outputs/tobe/prototype/design-tokens.json"
  design_traceability: "projects/{project_name}/outputs/tobe/prototype/design-input-traceability.json"
  execution_log: "projects/{project_name}/outputs/tobe/prototype/execution-log.json"
```

The existing artifact names remain compatible unless the implementation proves that `figma-spec.md` is a generated design specification rather than a `.fig` export. The agent MUST NOT create, export, or claim to create a binary `.fig` file. The traceability artifact must record the selected source, configured path, detected format, extraction status, mapped categories, and unmapped fields/gaps.

### Clarified implementation decisions

- The traceability contract includes `limitation_severity` (`high|medium|low|none`), `limitation_code`, and `gate_impact` (`blocks|warns|none`). `high` applies when `source_integrity` is `failed`, or when all selected-file content is rejected and no valid `design-system.md` fallback exists. `high` uses `gate_impact: "warns"`; it does not block the pipeline. `medium` applies to malformed input with a safe fallback or a partially unmapped category; `low` applies to unsupported optional/non-visual fields; `none` applies to successful client ingestion without material limitation or fallback without those conditions. `medium`, `low`, and `none` use `gate_impact: "none"`.
- The parser, mapper, sanitizer, integrity hasher, and traceability writer are implemented exclusively as deterministic rules in the Brazilian Portuguese protocol of `prototype-agent.md`. No separate executable helper, agent, skill, module, phase, or technology is introduced.
- Every task that edits `prototype-agent.md` writes its section directly in pt-BR and must not introduce English into the agent body. Checkpoints T018a, T034a, and T040a validate language and consistency; T042 performs final consolidation only.
- The traceability invariants are mandatory: fallback sources require a non-null `fallback_reason`; `source: "client"` requires a non-null `used_file`; and a detected-but-rejected file remains in `detected_file` while `used_file` is null.
- The malformed-design fixture contains exactly one malformed case for each supported format: Figma JSON, W3C Tokens JSON, CSS, Markdown, and SCSS.
- Sanitizer tests include API-key-like values, passwords, and connection strings; these values are recorded only as safe unmapped gaps and must not appear in traceability, logs, or Summary HTML.
- The internal token model includes a sixth category, `layout`, populated only from Figma JSON export sources (frame/page hierarchy, component position/composition). Screen generation consumes `business-rules.md`, user journeys, architecture, and client layout when available from Figma; layout is not applied as a post-hoc style-only pass. `business-rules.md` remains authoritative for functional completeness: missing mandatory elements are supplemented generically and recorded as layout gaps. W3C Tokens, CSS, Markdown, and SCSS remain style-only by format limitation, which is a documented scope boundary, not a defect.

## Clarifications

### Session 2026-08-10

- Q: How are high-severity ingestion limitations classified and surfaced? → A: Use the explicit `limitation_severity`, `limitation_code`, and `gate_impact` contract and deterministic rules defined above.
- Q: Where do parser, mapper, sanitizer, hasher, and traceability behaviors execute? → A: As deterministic rules in the pt-BR protocol of the existing `prototype-agent.md`, with no separate executable helper.
- Q: How are intermediate language and repeated agent-file edits controlled? → A: Each editing task writes pt-BR immediately; checkpoints T018a, T034a, and T040a validate language and consistency; T042 performs final consolidation only.
- Q: Which traceability invariants are mandatory? → A: Fallback requires `fallback_reason`; client requires `used_file`; detected-but-rejected input keeps `detected_file` and sets `used_file` to null.
- Q: What security and fixture details are mandatory? → A: Secret-like values are never emitted, and malformed input covers one case per supported format.

### Session 2026-08-11

- Q: Is any automated or manual verification step required before this feature is considered complete? → A: No. The team explicitly waived both the automated pytest suite and the manual verification checklist for this feature. Implementation tasks alone constitute the Definition of Done.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 - Client Figma JSON takes precedence (Priority: P1)

**Story**: As a migration stakeholder, I want the prototype to consume my existing design export so that the generated screens reflect the approved visual language instead of generic agent defaults.

**Why this priority**: Applying approved client tokens is the core bug fix and prevents visual drift.

**Acceptance Scenarios**:

1. **Given** a valid `figma-export.json` under `projects/{project_name}/inputs/design/` and `design_input.enabled: true`, **When** `ava-prototype` executes, **Then** the HTML prototype uses the extracted client colors, typography, spacing, grid, and mapped component patterns wherever those values are available.
2. **Given** the same input, **When** execution completes, **Then** the design traceability artifact identifies the exact file path, detected Figma JSON format, extracted categories, and any unmapped fields.
3. **Given** client design tokens conflict with generic UX defaults, **When** the prototype is generated, **Then** client-provided values win for the applicable token or component and the generic fallback is not silently substituted.

### Scenario 2 - Supported format discovery and explicit file selection (Priority: P1)

**Story**: As a project owner, I want deterministic design-file discovery so that the prototype uses the intended source without manual file renaming.

**Acceptance Scenarios**:

1. **Given** no exact `design_input.file` is configured, **When** multiple compatible files exist, **Then** the agent selects one according to the documented priority: Figma JSON, W3C Design Tokens JSON, CSS variables, Markdown guide, then SCSS variables.
2. **Given** `design_input.file` names an existing compatible file, **When** the agent executes, **Then** it consumes that file and records the explicit-selection decision.
3. **Given** `design_input.file` names a missing or unsupported file, **When** the agent executes, **Then** it records a deterministic configuration gap and uses the documented fallback without silently selecting a different explicit file.

### Scenario 3 - Fallback and disabled input (Priority: P1)

**Story**: As an operator, I want safe fallback behavior so that prototype generation remains deterministic when client design input is unavailable or intentionally disabled.

**Acceptance Scenarios**:

1. **Given** no compatible file under the configured design directory, **When** the agent executes, **Then** it does not generate a `.fig` file, uses `design-system.md` as the first fallback, and uses generic CSS tokens only when that fallback is unavailable.
2. **Given** `design_input.enabled: false`, **When** the agent executes, **Then** it does not scan the design directory, uses the documented internal fallback, and records that client ingestion was disabled.
3. **Given** a malformed compatible file, **When** the agent executes, **Then** it reports the parse limitation in traceability and follows the documented fallback rather than silently ignoring the failure.

### Scenario 4 - Summary and output provenance (Priority: P1)

**Story**: As a reviewer, I want the Phase 3 result and Summary to identify the design source so that I can verify whether the prototype followed client or fallback guidance.

**Acceptance Scenarios**:

1. **Given** a successful client-design ingestion, **When** the Phase 3 summary is generated, **Then** it explicitly labels the source as client-provided and includes file, path, format, and mapping status.
2. **Given** a fallback execution, **When** the Phase 3 summary is generated, **Then** it explicitly labels the fallback source and explains why client input was not used.
3. **Given** unmapped client design fields, **When** traceability is generated, **Then** each gap has an identifiable field/category and a non-silent limitation note.

### Scenario 5 - Quality gate and input integrity (Priority: P1)

**Story**: As a pipeline operator, I want the agent to preserve existing gates and input integrity while changing only design-source behavior.

**Acceptance Scenarios**:

1. **Given** the mandatory `business-rules.md` is missing, **When** the agent executes, **Then** the existing blocked pre-flight behavior remains unchanged and no prototype artifact is generated.
2. **Given** a client design file exists, **When** execution completes, **Then** the source input remains unchanged and `trace_id` is propagated without mutation.
3. **Given** a high-severity design ingestion limitation that prevents reliable styling, **When** the agent evaluates the result, **Then** the limitation is surfaced in the result/traceability and the existing pipeline gate semantics are preserved.

### Scenario 6 - Client layout drives screen generation, not only styling (Priority: P1)

**Story**: As a migration stakeholder, I want the prototype's screen structure, not only its colors, to reflect my Figma design, so the generated prototype resembles the approved design rather than a generic layout repainted with brand colors.

**Why this priority**: Approved design standards include screen layout and component composition, not only visual tokens.

**Acceptance Scenarios**:

1. **Given** a valid Figma JSON export with frame/page/component hierarchy under `inputs/design/`, **When** `ava-prototype` executes, **Then** each business-rule-required screen with a corresponding frame uses that frame's section layout and component composition as the generated HTML structure.
2. **Given** a business-rule-required screen has no corresponding Figma frame, **When** the prototype is generated, **Then** the screen is still generated with the generic layout heuristic and traceability records a low-severity layout gap.
3. **Given** a Figma frame omits an element required by a mandatory business rule, **When** the prototype is generated, **Then** `business-rules.md` remains authoritative, the required element is added, and the frame deviation is recorded as a medium-severity layout gap.
4. **Given** a non-Figma design source is used, **When** the prototype is generated, **Then** only visual tokens are applied, generic layout heuristics remain active, and the format limitation is documented rather than reported as a defect.

---

## 5. Quality Gate Requirements

- [ ] Agent ID remains `ava-prototype` and version is incremented to `1.3.0`.
- [ ] Frontmatter contains only the allowed fields and Portuguese activation description.
- [ ] Existing module registration and `ava-prototype` skill routing remain consistent.
- [ ] Output paths use lowercase `{project_name}` and preserve the F3 prototype directory.
- [ ] BDD scenarios cover nominal client ingestion, missing/disabled/malformed input, and quality-gate/integrity paths.
- [ ] Security impact is assessed; design files are treated as untrusted input and must not introduce executable content or secret leakage into generated HTML/logs.
- [ ] No technology versions or environment values are hardcoded.
- [ ] Existing business-rules pre-flight and `trace_id` behavior remain compatible.
- [ ] The agent body remains in Brazilian Portuguese.
- [ ] No `[NEEDS CLARIFICATION]` markers remain.

---

## 6. Dependencies

| Dependency               | Agent ID / Artifact                                               | Reason                                                           |
| ------------------------ | ----------------------------------------------------------------- | ---------------------------------------------------------------- |
| Prototype dispatch       | `ava-master-orchestrator`                                         | Dispatches F3 after TO-BE completion.                            |
| Mandatory business rules | `ava-asis-documentation` → `outputs/asis/docs/business-rules.md`  | Supplies domain rules required to create screens.                |
| Internal design fallback | `ava-tobe-designer-system` → `outputs/tobe/docs/design-system.md` | First fallback when client design input is unavailable.          |
| Summary                  | `ava-summary`                                                     | Must expose design provenance in Phase 3 reporting.              |
| Project configuration    | `projects/{project_name}/context/project-config.yaml`             | Supplies optional `design_input` configuration and project path. |

---

## 7. Exclusions

- Generating or exporting binary `.fig` files.
- Automatic conversion between unsupported design formats.
- Replacing the existing business-rules pre-flight gate.
- Redesigning client visual language or inventing a new design system when client evidence is usable.
- Changing unrelated F1–F7 agent behavior.

---

## 8. Assumptions

- `design_input` is an optional project configuration section; absent configuration defaults to enabled discovery at `inputs/design`.
- The configured design path is relative to `projects/{project_name}/` unless an existing repository convention explicitly permits a safe project-relative path.
- Supported discovery priority is Figma JSON, W3C Design Tokens JSON, CSS, Markdown, then SCSS.
- If several files have equal priority and no exact file is configured, deterministic lexical ordering selects the first candidate and the decision is recorded.
- Existing `design-system.md` remains the first internal fallback, followed by generic CSS tokens.
- Extracted values are sanitized before insertion into HTML/CSS and arbitrary executable content is never copied into generated output.
- The summary can consume the traceability artifact through the existing prototype artifact discovery path; if a Summary code change is required, it is part of implementation planning rather than a new output contract.

---

## Success Criteria

| Criterion                  | Measure                                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Client source precedence   | In a fixture with conflicting client and generic tokens, 100% of mapped client token assertions match the client source in generated HTML/CSS.  |
| Deterministic discovery    | Repeated runs with the same inputs select the same source and produce identical source-selection metadata.                                      |
| Fallback correctness       | Missing, disabled, and malformed input cases produce no `.fig` file and identify the selected fallback and reason.                              |
| Traceability completeness  | Every run records source status, path, format, mapped categories, unmapped fields, and limitation reason when applicable.                       |
| Summary visibility         | Phase 3 Summary identifies client versus fallback source for 100% of prototype runs.                                                            |
| Regression safety          | Existing mandatory business-rules blocking, output contract, trace propagation, and non-design prototype acceptance scenarios continue to pass. |
| Input integrity and safety | Client design files remain byte-for-byte unchanged, and generated output contains no untrusted executable payload copied from design input.     |
