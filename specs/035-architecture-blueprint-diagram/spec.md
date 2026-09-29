# Agent Specification: Architecture Blueprint Diagram Generation

**Feature Branch**: `035-architecture-blueprint-diagram`  
**Created**: 2026-08-05  
**Status**: Draft  
**Change Type**: bugfix  
**Input**: Architecture Blueprint documentation shows a placeholder instead of a generated Mermaid diagram.

> This specification defines user-visible behavior and quality outcomes. Implementation details are intentionally deferred to planning.

---

## 1. Feature Overview

The migration documentation must reliably present an Architecture Blueprint diagram whenever the project contains sufficient architectural information. The pipeline must identify the responsible generating agent, preserve the generated Mermaid artifact, render it in the Blueprint section, and distinguish generation, discovery, rendering, and execution failures.

The publication gate must reject a client-facing report when a required Architecture Blueprint diagram is missing or cannot be rendered.

## 2. User Scenarios & Testing

### Scenario 1 — Blueprint diagram generated and rendered (Priority: P1)

**Story**: As an architect reviewing the migration documentation, I want the Architecture Blueprint section to show the actual architecture diagram so that I can understand the proposed system without inspecting source files.

**Why this priority**: The diagram is a primary architecture deliverable and its absence makes the documentation incomplete.

**Acceptance Scenarios**:

1. **Given** a project with sufficient architectural information, **When** the architecture workflow completes, **Then** a valid Mermaid Architecture Blueprint artifact is produced and the Blueprint section renders that artifact.
2. **Given** a generated Blueprint artifact, **When** the report is opened, **Then** the placeholder text `(diagrama não disponível — execute o agente correspondente)` is not displayed anywhere in the Architecture Blueprint section.
3. **Given** a generated Blueprint artifact, **When** the report is inspected, **Then** the generating agent, artifact path, generation status, and rendering status are available as traceable quality metadata.

### Scenario 2 — Missing or incomplete architecture information (Priority: P1)

**Story**: As a migration operator, I want missing architectural inputs to be reported explicitly so that a missing diagram is not confused with a renderer failure.

**Acceptance Scenarios**:

1. **Given** a project without sufficient architectural information, **When** the workflow runs, **Then** it reports that the Blueprint cannot be generated because the required architectural input is missing.
2. **Given** a project with sufficient architectural information but no Blueprint artifact, **When** validation runs, **Then** the result is a missing-artifact finding that identifies the expected artifact and responsible agent.
3. **Given** a project where the responsible agent did not execute, **When** validation runs, **Then** the result identifies missing agent execution separately from diagram generation failure.

### Scenario 3 — Generation versus rendering failure (Priority: P1)

**Story**: As a quality reviewer, I want generation and rendering failures separated so that the responsible team can remediate the correct stage.

**Acceptance Scenarios**:

1. **Given** an invalid or absent Mermaid artifact after the generating agent ran, **When** validation runs, **Then** the report classifies the issue as diagram generation failure or missing artifact, not rendering failure.
2. **Given** a valid Mermaid artifact that the renderer cannot process, **When** validation runs, **Then** the report classifies the issue as rendering failure and preserves the artifact evidence.
3. **Given** a valid artifact and successful rendering, **When** publication validation runs, **Then** the Architecture Blueprint quality gate passes.

### Scenario 4 — Publication quality gate (Priority: P1)

**Story**: As a delivery owner, I want publication to fail for a missing or unrenderable required Blueprint diagram so that incomplete architecture documentation cannot be released.

**Acceptance Scenarios**:

1. **Given** a required Blueprint artifact is missing, **When** the publication gate runs, **Then** publication fails with a blocking finding.
2. **Given** Blueprint generation or rendering fails, **When** the publication gate runs, **Then** publication fails and the report states the failure category and remediation owner.
3. **Given** generation and rendering both succeed, **When** publication occurs, **Then** the report includes the generated Blueprint diagram and its trace metadata.

## 3. Functional Requirements

### Ownership and generation

- **FR-001**: The architecture workflow MUST identify the agent responsible for generating the Architecture Blueprint Mermaid artifact before attempting publication.
- **FR-002**: When sufficient architectural information is available, the responsible agent MUST generate a non-empty Mermaid artifact representing the Architecture Blueprint.
- **FR-003**: The generated artifact MUST have a traceable expected path, project association, and generating-agent association.
- **FR-004**: The pipeline MUST preserve the generated artifact as a distinct output that can be inspected independently of the rendered report.

### Rendering and presentation

- **FR-005**: The Blueprint renderer MUST automatically consume the generated Architecture Blueprint artifact.
- **FR-006**: The Architecture Blueprint section MUST NOT display the placeholder `(diagrama não disponível — execute o agente correspondente)` when sufficient architectural information and a valid artifact are available.
- **FR-007**: A successful report MUST provide a rendered Architecture Blueprint diagram and expose enough metadata to identify the source artifact and generating agent.

### Validation and diagnostics

- **FR-008**: Validation MUST report a missing-artifact finding when the required Blueprint artifact is absent.
- **FR-009**: Validation MUST distinguish at least these outcomes: missing agent execution, insufficient architectural input, diagram generation failure, missing artifact, diagram rendering failure, and successful generation/rendering.
- **FR-010**: Quality reports MUST explicitly identify the expected Blueprint artifact, actual artifact discovered or absence, generating agent, generation status, and rendering status.
- **FR-011**: Validation findings MUST identify whether the issue is actionable before rendering, during rendering, or at publication.

### Publication gate

- **FR-012**: The publication pipeline MUST fail when a required Architecture Blueprint diagram is missing.
- **FR-013**: The publication pipeline MUST fail when the Blueprint artifact exists but cannot be rendered successfully.
- **FR-014**: The publication pipeline MUST pass the Blueprint gate only when the required artifact is present, valid, traceable to its generating agent, and successfully rendered.
- **FR-015**: Gate results MUST remain traceable to the project and workflow execution without exposing secrets or altering the legacy repository.

## 4. Key Entities

- **Architecture Blueprint artifact**: The Mermaid document representing the target or analyzed architecture.
- **Generating agent**: The pipeline agent accountable for producing the Blueprint artifact.
- **Artifact discovery record**: The validation record containing expected path, discovered path, and project association.
- **Generation status**: The result of the responsible agent's attempt to produce the artifact.
- **Rendering status**: The result of converting the artifact into the report's visible diagram.
- **Blueprint quality finding**: A categorized validation result for missing input, execution, generation, discovery, rendering, or publication.
- **Publication gate result**: The pass/fail decision controlling report release.

## 5. Edge Cases

- Architectural information exists in multiple eligible source files; the pipeline must select one canonical Blueprint artifact and report any alternatives.
- The responsible agent runs successfully but produces an empty Mermaid file; this is a generation failure, not a rendering failure.
- The artifact exists at an unexpected path; validation must report the expected and actual paths and must not silently treat an unowned file as the canonical output.
- The artifact is valid Mermaid but the renderer is unavailable or incompatible; this is a rendering/environment failure.
- The artifact contains a placeholder or unresolved template token; validation must report an invalid generation result and block publication.
- The project has insufficient architecture information; validation must report an input insufficiency finding rather than claiming a renderer failure.
- The report is regenerated; the result must remain deterministic and must not create duplicate canonical Blueprint artifacts.

## 6. Assumptions

- The existing architecture workflow and its responsible agent remain the owner of the Blueprint artifact; this change clarifies and enforces ownership rather than introducing a second competing producer.
- Mermaid artifacts follow the repository's existing diagram guardrails and project configuration.
- Existing project output conventions remain authoritative for the final artifact path.
- The report can be generated in a partial state for diagnostic purposes, but publication is blocked when the required Blueprint gate fails.
- Existing trace identifiers are propagated without mutation.

## 7. Dependencies

- Existing architecture workflow and orchestrator.
- Existing responsible architecture agent and its output contract.
- Existing Mermaid sanitization and validation utilities.
- Existing Blueprint renderer and report builder.
- Existing publication quality gate and validation reporting.

## 8. Non-Goals

- Redesigning the target architecture.
- Replacing Mermaid with another diagram format.
- Re-running unrelated upstream migration agents.
- Modifying the legacy repository.
- Hiding missing artifacts by substituting a static diagram or hardcoded architecture.

## Success Criteria

| Criterion               | Measure                                                                                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Blueprint visibility    | 100% of projects with sufficient architectural information show a rendered Architecture Blueprint diagram in the report.                             |
| Placeholder elimination | 0 published reports show the specified unavailable-diagram placeholder when a valid Blueprint artifact exists.                                       |
| Ownership traceability  | 100% of quality reports identify expected artifact, actual artifact, generating agent, generation status, and rendering status.                      |
| Failure classification  | 100% of tested missing-input, missing-execution, generation-failure, missing-artifact, and rendering-failure cases receive distinct classifications. |
| Publication safety      | 100% of missing or unrenderable required Blueprint diagrams block publication.                                                                       |
| Artifact integrity      | 100% of successful Blueprint artifacts are non-empty, valid Mermaid artifacts linked to the project execution trace.                                 |
| Regression protection   | Existing architecture reports and unrelated diagram sections continue to pass their current validation checks.                                       |

## Quality Gate Checklist

- [ ] Responsible agent and canonical artifact path are confirmed from existing contracts.
- [ ] Generation, discovery, rendering, and publication statuses are independently recorded.
- [ ] Mermaid artifact is validated before report publication.
- [ ] The unavailable-diagram placeholder is absent from successful Blueprint sections.
- [ ] Missing required artifacts block publication.
- [ ] BDD scenarios cover nominal, missing-input, failure-classification, and gate paths.
- [ ] Traceability and secret-masking requirements are preserved.
