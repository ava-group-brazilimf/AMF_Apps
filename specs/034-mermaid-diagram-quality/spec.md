# Agent Specification: Mermaid Diagram Quality

**Feature Branch**: `034-mermaid-diagram-quality`
**Created**: 2026-08-04
**Status**: Draft
**Change Type**: modify-existing
**Input**: Agent description: "Robust Mermaid Diagram Generation and Visualization"

> This specification defines a platform capability, not a new user-facing agent. The implementation must follow the repository's existing Mermaid generation and validation ownership, while preserving configuration-driven behavior.

---

## 1. Agent Identity

| Field        | Value                                                                                        |
| ------------ | -------------------------------------------------------------------------------------------- |
| **Agent ID** | `ava-asis-documentation` and related existing diagram generators/validators                  |
| **Version**  | `3.1.0`                                                                                      |
| **Phase**    | `F1` with cross-cutting validation                                                           |
| **Module**   | `asis-diagnostic` and shared diagram validation                                              |
| **Role**     | Generate, sanitize, validate, correct, and quality-gate Mermaid diagrams before publication. |
| **Skill**    | Existing skills and internal validators; no new skill required                               |
| **Dispatch** | Existing orchestrators and diagram-producing agents                                          |

This is a modify-existing change. The affected agent specifications, shared Mermaid guardrails, generators, and validators already exist. No new agent or module registration is required unless implementation discovery identifies an existing registry entry that must be version-bumped.

---

## 2. Problem and Business Value

Mermaid diagrams produced during AS-IS documentation can fail in the target viewer with syntax errors, including failures reported by Mermaid 11.14.0. C4 Container diagrams can also be technically valid but difficult to read because relationship labels overlap containers or boundaries.

The feature establishes a reliable publication gate so architecture, dependency, integration, flow, and blueprint diagrams are syntactically valid, renderable, sanitized, and sufficiently readable without manual correction.

---

## 3. Scope

### In scope

- Mermaid source blocks generated or persisted by the platform.
- Syntax compatibility validation against the configured Mermaid compatibility target.
- Sanitization of source-derived labels and metadata.
- Automatic correction for safe, deterministic syntax issues.
- Diagnostic reporting for syntax and visual-quality findings.
- Readability checks for label overlap, congestion, edge crossings, and C4 Container layout.
- Blocking publication when a Mermaid artifact remains invalid after correction attempts.
- Regression coverage for existing AS-IS, TO-BE, prototype, and Summary consumers.

### Out of scope

- Replacing Mermaid with a different diagramming technology.
- Requiring a specific browser, rendering engine, cloud service, or deployment environment.
- Subjective redesign of business architecture beyond readability and diagram structure.
- Changing unrelated migration outputs when no Mermaid artifact is involved.

---

## 4. User Scenarios and Acceptance Tests

### Scenario 1 — Valid diagram is published (Priority: P1)

**Story**: As an architect, I want generated diagrams to render reliably so that I can review architecture and migration decisions without manual repair.

**Acceptance Scenarios**:

1. **Given** a project containing valid Mermaid diagrams, **When** the documentation workflow runs, **Then** each diagram is parsed successfully by the configured Mermaid compatibility validator and the Markdown artifact is published.
2. **Given** a valid C4 Container diagram with relationship labels, **When** readability checks run, **Then** labels remain visible and no reported label intersects a container, boundary, or component.
3. **Given** all diagram checks pass, **When** publication completes, **Then** the diagnostic report records the analyzed files, diagram types, validation status, and evidence.

### Scenario 2 — Invalid or unsafe source is corrected (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a diagram containing source-derived quotes, pipes, brackets, HTML fragments, unsupported directives, or invalid Mermaid tokens, **When** sanitization and validation run, **Then** deterministic corrections are applied and the diagram is revalidated.
2. **Given** a correctable syntax failure, **When** correction completes, **Then** the persisted Markdown contains the corrected Mermaid block and the report records the original issue, correction, and revalidation result.
3. **Given** an uncorrectable syntax failure, **When** the retry limit is reached, **Then** the diagram is not published as deliverable content, the report contains the error location and recommended correction, and the quality gate is `BLOCKED`.

### Scenario 3 — Empty or incomplete inputs are handled safely (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a project with no Mermaid artifacts, **When** the workflow runs, **Then** it produces a diagnostic report with zero analyzed diagrams and does not invent diagram content.
2. **Given** a Markdown file with an incomplete Mermaid block, **When** validation runs, **Then** the artifact is reported as invalid with the file, block, and likely cause; no invalid block is silently accepted.

### Scenario 4 — Dense diagrams are made readable or gated (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a diagram whose relationship labels overlap nodes or whose layout is congested, **When** readability analysis runs, **Then** the report identifies the overlap/congestion evidence and recommends restructuring, spacing, shortening, or segmentation.
2. **Given** a dense C4 Container diagram that can be deterministically reorganized, **When** optimization runs, **Then** the resulting diagram has improved spacing and no blocking overlap findings.
3. **Given** a diagram that remains unreadable after safe optimization, **When** the quality gate evaluates it, **Then** publication is blocked and `human_gate_required` is true.

---

## 5. Functional Requirements

### Canonical validation configuration

The canonical configuration is:

```yaml
diagramValidation:
  mermaid:
    acceptanceBaselineVersion: "11.14.0"
    rendererVersion: "11.14.0"
    strictCompatibility: true
  renderingProfile:
    viewportWidth: 1440
    viewportHeight: 900
    zoomLevel: 1.0
    fontFamily: "Arial, sans-serif"
    fontSizePx: 14
    theme: "default"
    deviceScaleFactor: 1
  readability:
    maxNodeLabelLengthChars: 60
    maxBlockingOverlaps: 0
    maxLabelContainerOverlapPercent: 0
    maxLabelBoundaryOverlapPercent: 0
    maxLabelCardOverlapPercent: 0
    maxLabelComponentOverlapPercent: 0
    maxCriticalEdgeCrossings: 0
    maxTotalEdgeCrossingsWarning: 10
    maxRelationshipLabelLengthChars: 80
    maxNodesPerDiagramWarning: 25
    maxEdgesPerDiagramWarning: 35
    minLabelToElementSpacingPx: 8
    minNodeSpacingPx: 24
```

Resolution rules:

1. Load the canonical project override from `.config/diagram-validation.yaml` using `DiagramValidationConfigLoader`.
2. `diagramValidation` and `diagramValidation.mermaid` are mandatory objects.
3. `diagramValidation.renderingProfile` and `diagramValidation.readability` are optional objects that receive defaults when absent.
4. If `diagramValidation` or `diagramValidation.mermaid` is missing, malformed, or not an object, emit a blocking `CONFIGURATION` finding and disallow publication.
5. If valid mandatory sections exist, apply defaults only to missing optional nested keys.
6. Use `diagramValidation.mermaid.acceptanceBaselineVersion` when present.
7. Default the acceptance baseline to `11.14.0` when absent.
8. Default `rendererVersion` to the acceptance baseline.
9. When `strictCompatibility` is true, unsupported, deprecated, or experimental syntax blocks publication.
10. Invalid value types fail closed with a blocking `CONFIGURATION` finding; malformed project overrides never fall back silently.

Mermaid 11.14.0 is the mandatory acceptance baseline. Runtime renderer settings remain externally configurable only when they satisfy the baseline and strict compatibility policy.

Configuration precedence is: `.config/diagram-validation.yaml` project override, canonical feature configuration model, then built-in defaults. The default rendering profile is an acceptance reference; `effectiveRenderingProfile` records the validated profile actually used.

- **FR-01**: The platform MUST validate every generated Mermaid diagram against the mandatory Mermaid 11.14.0 acceptance baseline before publication.
- **FR-02**: Generated Markdown MUST use fenced `mermaid` blocks with complete, supported diagram definitions.
- **FR-03**: Generators MUST avoid experimental, deprecated, and unsupported syntax unless explicitly allowed by the configured compatibility policy.
- **FR-04**: Source-derived labels and metadata MUST be sanitized for quotes, parentheses, brackets, pipes, HTML fragments, control characters, Unicode hazards, and Mermaid-reserved tokens.
- **FR-05**: Validation MUST report the file, diagram type, block identity or location, compatibility issue, violated rule, severity, and evidence.
- **FR-06**: The platform MUST attempt deterministic corrections for correctable failures and MUST revalidate after each correction.
- **FR-07**: Invalid Mermaid content MUST NOT be published as a successful deliverable. Persistent failure MUST produce a blocking quality-gate result.
- **FR-08**: The platform MUST analyze label visibility, overlap targets, edge crossings, spacing, congestion, connector length, and diagram complexity; geometry evidence is required when rendering is available.
- **FR-09**: C4 Container validation MUST specifically check that relationship descriptions do not intersect containers or boundaries and remain readable at default viewer zoom.
- **FR-10**: Dense diagrams MUST be eligible for safe layout optimization, label shortening, spacing changes, or segmentation into focused diagrams.
- **FR-11**: Each identified issue MUST include authoritative `artifactPath` and `diagramId`; optional `artifactName` and `diagramName` display values may be included, plus problem, impact, evidence, root-cause hypothesis, recommended fix, corrected syntax example when applicable, and readability recommendation.
- **FR-12**: The workflow MUST preserve `traceId` and project-scoped output paths for all diagnostic and gate artifacts.
- **FR-13**: Existing Summary and downstream consumers MUST receive stable Mermaid content and diagnostic metadata without requiring manual post-processing.
- **FR-14**: The validator MUST normalize node identifiers to Mermaid-safe IDs using letters, numbers, and underscores, prefixing identifiers that begin with a number with `node_` and rejecting reserved tokens as raw IDs.
- **FR-15**: Node labels MUST preserve business meaning while sanitizing quotes, control characters, unsupported HTML, and line breaks according to the diagram type.
- **FR-16**: Edge labels MUST be sanitized independently: pipes and quotes escaped, Markdown fragments and unsupported HTML removed, and labels over the configured maximum shortened without semantic loss when possible.
- **FR-17**: A value that cannot be safely sanitized MUST produce `NOT_SAFELY_CORRECTABLE`, preserve a masked original in diagnostics, and include a manual correction recommendation.
- **FR-18**: The Analyze phase MUST inspect every artifact for syntax errors, Mermaid 11.14.0 compatibility, invalid node identifiers, invalid relationships, unescaped characters, label/container/boundary/card/component overlap, edge crossings, congestion, and decomposition opportunities.
- **FR-19**: The default rendering profile MUST be used unless overridden, and labels MUST be readable at zoom 1.0 without hover, inspection, dragging, or manual editing.
- **FR-20**: Renderer unavailability MUST produce `RENDERER_UNAVAILABLE`; it is blocking for publication and warning-only only for explicitly configured local development.
- **FR-21**: `strictCompatibility: false` MAY suppress advisory diagnostics only; unsupported, deprecated, experimental, or Mermaid 11.14.0-incompatible syntax MUST still block publication.
- **FR-22**: Node and relationship labels MUST use separate configured limits (`maxNodeLabelLengthChars: 60`, `maxRelationshipLabelLengthChars: 80`); wrapping is preferred, and truncation is allowed only when semantic preservation is demonstrated.
- **FR-23**: The public report MUST use camelCase fields, require `projectName` and `traceId`, and use `OVERLAP` with `overlapTargetType` plus `CROSSING`, `CONGESTION`, `SPACING`, `LABEL_LENGTH`, and `DEFAULT_VIEW_READABILITY` for non-overlap findings.
- **FR-24**: `MermaidRendererVersionCheck` MUST verify renderer availability and version before rendering; incompatible renderer versions produce a blocking `COMPATIBILITY` finding.
- **FR-25**: `MermaidQualityMarkdownReportGenerator` MUST produce the Markdown projection from the canonical JSON report with all required sections.
- **FR-26**: `MermaidQualitySummaryAdapter` MUST read both quality JSON artifacts and produce stable Summary metadata containing status, publication permission, finding counts, renderer status, environment, affected paths, and diagram IDs.

---

## 6. Output Contract

The implementation should extend existing contracts rather than create duplicate artifacts.

```yaml
outputs:
  mermaid_quality_report: "projects/{project_name}/outputs/asis/docs/mermaid-quality-report.md"
  mermaid_quality_data: "projects/{project_name}/outputs/asis/docs/mermaid-quality-report.json"
  corrected_mermaid_artifacts: "projects/{project_name}/outputs/asis/docs/ and other existing Mermaid output paths"
  quality_gate: "projects/{project_name}/outputs/asis/docs/mermaid-quality-gate.json"
```

If existing validator or agent contracts already provide equivalent paths, the implementation MUST preserve those paths and extend their schemas compatibly rather than creating duplicate reports.

---

## 7. Diagnostic Report Requirements

For syntax findings, the report MUST include:

- Artifact and diagram name.
- Diagram type.
- Compatibility target and compatibility result.
- Invalid syntax and error location when available.
- Violated rule.
- Root-cause hypothesis.
- Recommended correction.
- Corrected Mermaid example or a reason no safe example can be produced.
- Correction attempts and final validation status.

For visual findings, the report MUST include:

- Label-overlap, container-overlap, boundary-overlap, edge-crossing, congestion, connector-readability, and complexity assessments.
- Evidence source and confidence.
- Impact assessment.
- Recommended spacing, restructuring, shortening, or segmentation.
- Final readability status.

The report MUST distinguish `PASS`, `WARN`, and `BLOCKED`; a `WARN` cannot hide a syntax failure.

Every finding MUST contain exactly one non-empty field: `correctedMermaidExample` for safe automatic corrections, or `notSafelyCorrectableReason` for semantic/manual corrections.

---

## 8. Quality Gates

- **Syntax gate**: zero invalid Mermaid diagrams may be published.
- **Sanitization gate**: no unsafe source-derived label may bypass the sanitizer.
- **Readability gate**: blocking overlap or unreadable C4 relationships prevent publication.
- **Correction gate**: every correction is followed by revalidation and recorded evidence.
- **Completeness gate**: every discovered Mermaid artifact is represented in the diagnostic report.
- **Regression gate**: existing Mermaid consumers, Summary rendering, and offline viewing remain functional.
- **Renderer gate**: production publication requires renderer and viewer smoke-test evidence; `RENDERER_UNAVAILABLE` is blocking unless local-development non-blocking mode is explicitly configured.
- **Threshold gate**: any blocking overlap, critical edge crossing, syntax error, unsupported construct, unreadable default-view label, or spacing violation fails publication. Warnings are limited to non-blocking density, long-label, or edge-crossing signals that do not affect syntax, rendering, or readability.

A failed syntax gate or unrecoverable readability defect sets `quality_gate: BLOCKED` and `human_gate_required: true`.

### Validator ownership

- `MermaidSyntaxValidator`: Mermaid 11.14.0 syntax, declarations, nodes, and relationships.
- `MermaidSanitizationValidator`: IDs, labels, edge labels, escaping, reserved tokens, and `NOT_SAFELY_CORRECTABLE` classification.
- `MermaidRenderValidator`: configured renderer, rendering failures, screenshots, and rendering evidence.
- `DiagramGeometryValidator`: overlap, crossings, spacing, and default-view geometry.
- `DiagramComplexityValidator`: congestion, node/edge thresholds, and decomposition recommendations.
- `MermaidQualityGate`: aggregates all results and controls publication.
- `DiagramValidationConfigLoader`: loads `.config/diagram-validation.yaml`, validates and resolves configuration.
- `MermaidRendererVersionCheck`: verifies renderer availability and configured-version compatibility.
- `MermaidQualityMarkdownReportGenerator`: projects canonical JSON into the required Markdown report.

---

## 9. Dependencies and Exclusions

| Dependency                                       | Reason                                                      |
| ------------------------------------------------ | ----------------------------------------------------------- |
| Existing Mermaid guardrails                      | Canonical syntax and sanitization rules                     |
| Existing diagram generators                      | Sources of Mermaid artifacts to validate                    |
| Existing validation utilities                    | Reuse established CLI and report conventions                |
| Summary builder and validator                    | Downstream rendering and regression compatibility           |
| Project configuration and reference architecture | Resolve compatibility and runtime policy without hardcoding |

Security impact is limited but must be assessed because diagrams can contain source-derived metadata. Sanitization MUST prevent HTML/script injection into Markdown or viewer payloads, and credentials, tokens, and connection strings MUST be masked if encountered.

---

## 10. Assumptions

- The compatibility target is resolved through `.config/diagram-validation.yaml` and defaults; the implementation must not hardcode technology versions in agent instructions.
- A deterministic parser or renderer is available in the execution environment, or the workflow reports a blocked validation when it is unavailable rather than claiming success.
- Visual overlap checks may use rendered geometry when available; otherwise the report records the limitation and applies deterministic structural heuristics.
- Existing generated artifacts remain read-only except for the owning generator and approved corrected output path.
- The platform can process projects with no Mermaid artifacts without inventing findings.
- The shared auditor is an internal validation utility, not a new user-facing agent or skill.

---

## 11. Success Criteria

| Criterion                | Measure                                                                                                          |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Syntax reliability       | 100% of discovered Mermaid artifacts pass validation before publication; zero published syntax failures          |
| Viewer compatibility     | Every published diagram renders successfully in the supported viewer using the configured compatibility target   |
| Sanitization             | 100% of source-derived Mermaid labels pass sanitization checks                                                   |
| Correction traceability  | Every automatic correction records before/after evidence and a successful revalidation, or results in `BLOCKED`  |
| Readability              | Zero blocking label/container/boundary overlaps in published diagrams; dense diagrams are optimized or segmented |
| Diagnostic completeness  | 100% of discovered Mermaid artifacts appear in the report with status and evidence                               |
| Regression safety        | Existing Summary and downstream rendering checks remain passing for unaffected diagrams                          |
| Operational usability    | Architects can consume published diagrams without manual syntax or layout correction                             |
| Mermaid baseline         | All published diagrams validate against the mandatory 11.14.0 acceptance baseline                                |
| Default-view readability | All critical diagrams pass the configured 1440x900, zoom 1.0 profile with zero blocking overlaps                 |

---

## 12. Constitution and Implementation Notes

- This specification changes behavior of existing agents and validators; implementation must use the appropriate existing agent specifications and shared utilities.
- Any agent body change must be written in Brazilian Portuguese and follow the four-field frontmatter contract.
- Mermaid compatibility, retry limits, and rendering settings must be configuration-driven.
- BDD scenarios above cover nominal, empty/incomplete input, correction, and quality-gate paths.
- No security sub-pipeline is bypassed; diagram-derived security findings must follow existing F1 security orchestration when applicable.
