# Quickstart: Mermaid Diagram Quality

## Prerequisites

- Repository root as the current directory.
- Python runtime configured for the repository.
- A project with `projects/{project_name}/context/project-config.yaml` and generated outputs.
- A project override at `.config/diagram-validation.yaml`; `diagramValidation` and `diagramValidation.mermaid` are mandatory. `renderingProfile` and `readability` are optional and receive documented defaults. Missing/malformed mandatory sections block validation.
- Mermaid validation/rendering capability resolved by project configuration. The default `diagramValidation` profile uses acceptance baseline and renderer `11.14.0`, a 1440x900 viewport, zoom 1.0, Arial 14px, default theme, and device scale factor 1.

If optional Mermaid keys are absent inside a valid `diagramValidation`, the validator defaults the baseline and renderer to `11.14.0` and strict compatibility to `true`. If the entire object is missing or malformed, validation fails closed with a blocking configuration finding.

## 1. Validate one Mermaid artifact without writing

Pipe a raw Mermaid document to the shared validator using `--type mmd`. Expected result:

- exit `0`: clean or warning-only input;
- exit `2`: deterministic correction was applied and the corrected content is emitted;
- exit `1`: unfixable content; no artifact may be published.

## 2. Validate and publish through the write gate

Use the shared pre-write gate for generated `.mmd` artifacts. The target path must remain under the owning project output directory. A successful command writes only sanitized content.

## 3. Run the project-wide Mermaid audit

Run the planned batch auditor for the selected project. It must:

1. Discover every `.mmd` file and Mermaid fence in Markdown artifacts.
2. Resolve the compatibility target and `traceId`.
3. Sanitize and validate each artifact.
4. Attempt only deterministic corrections and revalidate.
5. Collect structural and rendered visual evidence when available.
6. Produce the canonical JSON report, Markdown report, and quality-gate decision.

The auditor must run the six validator components: syntax, sanitization, render, geometry, complexity, and quality gate.

## 4. Validate the report contract

Validate the generated JSON against `contracts/mermaid-quality-report.schema.json`. Confirm:

- every discovered artifact has a report entry;
- no artifact with a syntax error has `PASS` status;
- correction attempts have a subsequent validation result;
- `BLOCKED` includes `human_gate_required: true`;
- `traceId` and project name match the project context.
- `artifactPath` and `diagramId` are authoritative; `artifactName` and `diagramName` are optional display fields.
- public fields use camelCase (`projectName`, `traceId`, `schemaVersion`, `effectiveRenderingProfile`);
- every finding contains artifact, diagram, category, root cause, impact, evidence, recommendation, and either a corrected example or `notSafelyCorrectableReason`;
- thresholds are enforced: zero blocking overlaps, zero critical crossings, maximum 80-character relationship labels, warning above 10 crossings/25 nodes/35 edges, 8px label spacing, and 24px node spacing.
- every finding contains exactly one non-empty correction example or not-safely-correctable reason.

## 5. Run regression checks

Run the existing repository checks covering Mermaid files, Mermaid runtime embedding, Summary HTML data, and Summary navigation. The feature is not complete if the Summary viewer regresses or raw Mermaid source is shown where SVG rendering is expected.

Run the viewer smoke test for Blueprint Architecture, C4 Container, Flow, Dependency, Integration, and general Architecture diagrams. No `Syntax error in text` message is acceptable.

## 6. Acceptance scenarios

### Nominal

Use a valid flowchart, sequence, C4, class, ER, and Gantt fixture. The report should show all artifacts as `PASS` and the gate should be `APPROVED` or `APPROVED_WITH_WARNINGS` only when warnings are non-blocking.

### Correctable input

Use a fixture with a Mermaid fence in a `.mmd` file, invisible characters, unsupported arrows, or literal `\\n` in a label. The validator should emit a correction, revalidate, and persist only the corrected form.

### Uncorrectable input

Use a prohibited diagram type, unclosed subgraph, or self-loop requiring semantic redesign. The artifact must not be treated as published success; the report must contain an error and the gate must be `BLOCKED`.

### Readability failure

Use a dense C4 Container fixture with long relationship labels and crossing edges. The report must identify structural or rendered evidence, recommend shortening/spacing/segmentation, and block publication when the defect is classified as blocking.

### Renderer unavailable

Production publication is blocked with `RENDERER_UNAVAILABLE`. Local development may downgrade this to a warning only when an explicit local-development override is configured and structural checks pass.

### Markdown projection

`MermaidQualityMarkdownReportGenerator` reads `mermaid-quality-report.json` and produces the required eleven-section `mermaid-quality-report.md` without dropping findings.

## Expected deliverables

- `projects/{project_name}/outputs/asis/docs/mermaid-quality-report.md`
- `projects/{project_name}/outputs/asis/docs/mermaid-quality-report.json`
- `projects/{project_name}/outputs/asis/docs/mermaid-quality-gate.json`
- Corrected Mermaid artifacts at their existing owning paths, only after validation succeeds.
