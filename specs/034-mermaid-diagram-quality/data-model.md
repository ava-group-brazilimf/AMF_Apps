# Data Model: Mermaid Diagram Quality

## Canonical configuration

The validator resolves `diagramValidation` from `.config/diagram-validation.yaml` via `DiagramValidationConfigLoader`. `diagramValidation` and `diagramValidation.mermaid` are mandatory objects. `renderingProfile` and `readability` are optional and receive defaults. Missing or malformed mandatory sections, or invalid value types, are blocking. Missing optional nested keys use documented defaults.

```yaml
diagramValidation:
	mermaid:
		acceptanceBaselineVersion: "11.14.0"
		rendererVersion: "11.14.0"
		strictCompatibility: true
	readability:
		maxNodeLabelLengthChars: 60
		maxRelationshipLabelLengthChars: 80
	renderingProfile:
		viewportWidth: 1440
		viewportHeight: 900
		zoomLevel: 1.0
		fontFamily: "Arial, sans-serif"
		fontSizePx: 14
		theme: "default"
		deviceScaleFactor: 1
```

Readability thresholds: zero blocking overlaps; zero critical edge crossings; warning at more than 10 total crossings, more than 25 nodes, or more than 35 edges; maximum relationship label length 80 characters; minimum label-to-element spacing 8 px; minimum node spacing 24 px.

## MermaidArtifact

Represents one discovered Mermaid source artifact or fenced Mermaid block.

| Field                       | Type    | Required | Rules                                                        |
| --------------------------- | ------- | -------: | ------------------------------------------------------------ |
| `artifactPath`              | string  |      yes | Authoritative stable project-relative artifact identifier.   |
| `artifactName`              | string  |       no | Optional display name; never replaces `artifactPath`.        |
| `diagramId`                 | string  |      yes | Stable diagram/block identifier.                             |
| `diagramName`               | string  |       no | Optional display name; never replaces `diagramId`.           |
| `blockIndex`                | integer |      yes | Zero-based block index for Markdown; `0` for `.mmd`.         |
| `diagramName`               | string  |      yes | Derived from filename, heading, or block context.            |
| `diagramType`               | string  |      yes | Detected Mermaid type; `unknown` is invalid for publication. |
| `status`                    | enum    |      yes | `PASS`, `WARN`, `BLOCKED`.                                   |
| `rendererStatus`            | enum    |      yes | `AVAILABLE`, `RENDERER_UNAVAILABLE`, `NOT_RUN`, `FAILED`.    |
| `effectiveRenderingProfile` | object  |      yes | Actual viewport, zoom, font, theme, and scale.               |

## SyntaxFinding

| Field                  | Type         | Required | Rules                                                     |
| ---------------------- | ------------ | -------: | --------------------------------------------------------- |
| `finding_id`           | string       |      yes | Unique within the report.                                 |
| `artifact_id`          | string       |      yes | References `MermaidArtifact.artifact_id`.                 |
| `rule`                 | string       |      yes | Canonical guardrail rule identifier.                      |
| `severity`             | enum         |      yes | `INFO`, `WARNING`, `ERROR`.                               |
| `line`                 | integer/null |       no | One-based source line when known.                         |
| `column`               | integer/null |       no | One-based source column when known.                       |
| `message`              | string       |      yes | Human-readable explanation.                               |
| `original`             | string/null  |       no | Sanitized excerpt of the original source; secrets masked. |
| `fixed`                | string/null  |       no | Corrected excerpt when applicable.                        |
| `root_cause`           | string       |      yes | Hypothesis or deterministic cause.                        |
| `recommended_fix`      | string       |      yes | Actionable remediation.                                   |
| `corrected_example`    | string/null  |       no | Safe example when one can be produced.                    |
| `validation_after_fix` | enum         |      yes | `PASS`, `FAIL`, `NOT_ATTEMPTED`.                          |
| `correction_class`     | enum         |      yes | `DETERMINISTIC`, `NOT_SAFELY_CORRECTABLE`.                |

## VisualFinding

| Field             | Type          | Required | Rules                                                                                       |
| ----------------- | ------------- | -------: | ------------------------------------------------------------------------------------------- |
| `finding_id`      | string        |      yes | Unique within the report.                                                                   |
| `artifact_id`     | string        |      yes | References the authoritative `artifactPath`.                                                |
| `category`        | enum          |      yes | `OVERLAP`, `CROSSING`, `CONGESTION`, `SPACING`, `LABEL_LENGTH`, `DEFAULT_VIEW_READABILITY`. |
| `severity`        | enum          |      yes | `INFO`, `WARNING`, `ERROR`.                                                                 |
| `evidence_source` | enum          |      yes | `RENDERED_GEOMETRY`, `STRUCTURAL_HEURISTIC`, `MANUAL_REVIEW`.                               |
| `confidence`      | number        |      yes | Range $0 \le confidence \le 1$.                                                             |
| `elements`        | array[string] |      yes | Node, edge, label, or boundary identifiers involved.                                        |
| `description`     | string        |      yes | Problem description.                                                                        |
| `impact`          | string        |      yes | Effect on architecture review/readability.                                                  |
| `recommendation`  | string        |      yes | Spacing, shortening, restructuring, or segmentation action.                                 |
| `status`          | enum          |      yes | `PASS`, `WARN`, `BLOCKED`.                                                                  |

## MermaidQualityFinding

Every finding uses the public report contract fields: `id`, `severity`, `category`, `artifactPath`, `diagramId`, `diagramType`, `description`, `impact`, `rootCause`, `evidence`, `recommendation`, and exactly one of `correctedMermaidExample` or `notSafelyCorrectableReason`.

Categories include `SYNTAX`, `COMPATIBILITY`, `SANITIZATION`, `RENDERING`, `READABILITY`, `OVERLAP`, `CROSSING`, `CONGESTION`, `SPACING`, `LABEL_LENGTH`, `DEFAULT_VIEW_READABILITY`, and `CONFIGURATION`. `OVERLAP` requires `overlapTargetType` from `CONTAINER`, `COMPONENT`, `BOUNDARY`, `CARD`, `SYSTEM`, `EXTERNAL_SYSTEM`, or `VISIBLE_ELEMENT`.

Evidence includes the effective rendering profile, optional screenshot path, renderer status, and structural fallback evidence. Geometry findings additionally include SVG coordinate evidence with bounding boxes, intersection area, overlap percentage, spacing distance, and involved edge IDs when available.

## Validator ownership

`DiagramValidationConfigLoader` loads `.config/diagram-validation.yaml`; `MermaidSyntaxValidator` handles syntax/declarations/nodes/relationships; `MermaidSanitizationValidator` handles safe IDs, node labels, edge labels, escaping, and reserved tokens; `MermaidRendererVersionCheck` verifies renderer availability/version; `MermaidRenderValidator` handles rendering and screenshots; `DiagramGeometryValidator` handles overlaps, crossings, and spacing; `DiagramComplexityValidator` handles density and decomposition; `MermaidQualityGate` controls publication; `MermaidQualityMarkdownReportGenerator` projects canonical JSON into Markdown.

## CorrectionAttempt

| Field         | Type    | Required | Rules                      |
| ------------- | ------- | -------: | -------------------------- |
| `attempt`     | integer |      yes | Monotonic attempt number.  |
| `rule`        | string  |      yes | Correction rule applied.   |
| `changed`     | boolean |      yes | Whether source changed.    |
| `before_hash` | string  |      yes | Hash before correction.    |
| `after_hash`  | string  |      yes | Hash after correction.     |
| `result`      | enum    |      yes | `PASS`, `FAIL`, `SKIPPED`. |
| `notes`       | string  |       no | Masked diagnostic details. |

## MermaidQualityReport

| Field                       | Type                         | Required | Rules                         |
| --------------------------- | ---------------------------- | -------: | ----------------------------- |
| `schemaVersion`             | string                       |      yes | Canonical schema version.     |
| `feature`                   | string                       |      yes | `mermaid-diagram-quality`.    |
| `projectName`               | string                       |      yes | Project identifier.           |
| `traceId`                   | string                       |      yes | Propagated without mutation.  |
| `generatedAt`               | string                       |      yes | ISO-8601 timestamp.           |
| `acceptanceBaselineVersion` | string                       |      yes | `11.14.0`.                    |
| `rendererVersion`           | string                       |      yes | Resolved renderer version.    |
| `defaultRenderingProfile`   | object                       |      yes | Documented default reference. |
| `effectiveRenderingProfile` | object                       |      yes | Actual validated profile.     |
| `artifactsAnalyzed`         | integer                      |      yes | Artifact count.               |
| `diagramsAnalyzed`          | integer                      |      yes | Diagram count.                |
| `blockingFindings`          | integer                      |      yes | Blocking finding count.       |
| `warningFindings`           | integer                      |      yes | Warning finding count.        |
| `findings`                  | array[MermaidQualityFinding] |      yes | Canonical findings.           |

### State transitions

```text
DISCOVERED -> SANITIZED -> VALIDATED
VALIDATED -> PUBLISHED                       (syntax PASS and readability acceptable)
VALIDATED -> CORRECTING -> VALIDATED         (deterministic correction)
VALIDATED -> BLOCKED                          (uncorrectable syntax or blocking readability)
```

### Invariants

1. Every artifact in the project scan appears exactly once in `artifacts`.
2. `quality_gate = APPROVED` implies zero syntax errors and zero blocking visual findings.
3. `quality_gate = BLOCKED` implies at least one error-level syntax or visual finding.
4. A correction attempt cannot be marked `PASS` without a subsequent validation result.
5. All excerpts and evidence are secret-masked and project-scoped.
6. Public files use camelCase; any internal snake_case adapter must be transformed before writing public JSON.
7. Every finding contains exactly one non-empty correction field: `correctedMermaidExample` or `notSafelyCorrectableReason`.
