# Implementation Plan: Mermaid Diagram Quality

**Branch**: `034-mermaid-diagram-quality` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

## Summary

Extend the existing diagram sanitization and pre-write validation path into a complete Mermaid quality pipeline. All discovered Mermaid artifacts will be inventoried, sanitized, syntax-validated against the mandatory Mermaid 11.14.0 acceptance baseline, optionally rendered for geometry-based readability analysis, corrected only when deterministic, and blocked from publication when validation remains unsuccessful. The implementation explicitly analyzes syntax errors, compatibility violations, invalid node identifiers, invalid relationships, unescaped characters, label/container/boundary overlap, edge crossings, congestion, and decomposition opportunities. It preserves existing agent ownership, output paths, Summary integration, trace propagation, and configuration-driven compatibility settings.

## Technical Context

| Dimension               | Decision                                                                                                                                                     | Source                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| Implementation language | Python utilities and Markdown agent instructions                                                                                                             | Existing `src/shared/utils/` and agent modules     |
| Diagram source          | Raw `.mmd` files and fenced Mermaid blocks in Markdown                                                                                                       | Existing outputs and Summary builder               |
| Sanitization            | Extend `sanitize_diagrams.py`                                                                                                                                | Existing shared sanitizer and guardrails           |
| Pre-write gate          | Extend `validate_diagram.py`                                                                                                                                 | Existing single point of diagram write             |
| Batch audit             | New shared utility under `src/shared/utils/` or existing validation package after discovery                                                                  | Required for complete-project coverage             |
| Rendering               | Configured Mermaid-compatible renderer when available; explicit unavailable evidence otherwise                                                               | Research decision                                  |
| Report format           | Canonical JSON plus Markdown projection                                                                                                                      | `data-model.md` and contract schema                |
| Testing                 | Existing unified checks plus focused Python tests and renderer-backed integration tests                                                                      | Repository test conventions                        |
| Storage                 | Project output artifacts under `outputs/asis/docs/` unless an existing owning contract requires another path                                                 | Constitution output conventions                    |
| Compatibility           | Resolve `diagramValidation.mermaid` from project configuration; default acceptance and renderer versions to 11.14.0; fail closed on malformed configuration  | Clarification + Constitution Article I             |
| Rendering profile       | `defaultRenderingProfile` is 1440x900, zoom 1.0, Arial 14px, default theme, scale 1; `effectiveRenderingProfile` records validated overrides                 | Clarification                                      |
| Readability thresholds  | Zero blocking overlaps/critical crossings; warning above 10 crossings, 25 nodes, or 35 edges; max label 80 chars; 8px/24px spacing                           | Clarification                                      |
| Validator ownership     | Syntax, Sanitization, Render, Geometry, Complexity, and Quality Gate components in shared internal utility                                                   | Clarification                                      |
| Configuration loader    | `DiagramValidationConfigLoader` reads `.config/diagram-validation.yaml`; project override -> feature model -> built-in defaults                              | Clarification                                      |
| Markdown projection     | `MermaidQualityMarkdownReportGenerator` reads canonical JSON and writes the required Markdown sections                                                       | Clarification                                      |
| Runtime schemas         | `contracts/*.schema.json` is canonical; optional `src/contracts/` copies are generated and drift-checked                                                     | Clarification                                      |
| Summary integration     | `MermaidQualitySummaryAdapter` reads both quality JSON files and produces stable Summary metadata                                                            | Clarification                                      |
| Performance             | Batch validation must be deterministic and bounded by configured artifact/size limits                                                                        | Existing context-budget and batch-write guardrails |
| Constraints             | Do not write invalid Mermaid; do not mutate legacy repository; mask secrets; preserve trace ID                                                               | `AGENTS.md`, constitution, feature spec            |
| Scope                   | All Mermaid artifacts discovered in a project, including AS-IS/TO-BE and Markdown fences; correctness and readability are both blocking publication concerns | Feature requirements                               |

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] Article I — No technology version is hardcoded in agent instructions; `diagramValidation.mermaid` resolves the mandatory 11.14.0 baseline and fails closed when malformed. **Pass**.
- [x] Article II — Existing agent frontmatter and output contracts remain the governing contracts; any changed agent must keep the four-field frontmatter. **Pass**.
- [x] Article III — Existing phase orchestration is preserved; validation is invoked at the owning generator boundary and consumed by downstream Summary/QA gates. **Pass**.
- [x] Article IV — No new agent/module is required by the specification; existing registries are reviewed and version-bumped only if implementation changes an agent contract. **Pass**.
- [x] Article V — Any changed agent body will be written in Brazilian Portuguese; this plan and machine contracts may remain English. **Pass**.
- [x] Article VI — Nominal, empty/incomplete, correction, and quality-gate BDD scenarios are present in `spec.md`. **Pass**.
- [x] Article VII — Sanitization and secret masking are included; the existing F1 security sub-pipeline is not bypassed. **Pass**.
- [x] Article VIII — `traceId` propagation and Mermaid guardrail validation are explicit. **Pass**.
- [x] Article IX — No generated application layer is changed; shared validation remains isolated from domain code. **Pass**.
- [x] Article X — Existing behavior changes require a MINOR version bump for the affected agent contract; no breaking output path change is planned. **Pass pending implementation diff review**.
- [x] Article XI — Existing skills remain thin routers; behavior changes belong in agent bodies/shared utilities. **Pass**.

**Gate decision**: **PROCEED**. Clarifications resolve the previous critical/high findings. Mermaid 11.14.0 is the acceptance baseline, renderer-unavailable production publication fails closed, and readability is measured using the defined profile and thresholds.

### Explicit analysis scope

The Analyze phase MUST inspect every discovered Mermaid artifact and record, where applicable: syntax errors; Mermaid 11.14.0 compatibility violations; invalid node identifiers; invalid relationship definitions; unescaped characters; label overlap; container overlap; boundary overlap; excessive edge crossings; congestion; connector readability; complexity; and opportunities for diagram decomposition.

### Validation ownership

| Component                      | Responsibility                                                                      | Publication effect                                                                |
| ------------------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `MermaidSyntaxValidator`       | Mermaid 11.14.0 declarations, syntax, nodes, and relationships                      | Any error blocks                                                                  |
| `MermaidSanitizationValidator` | Safe IDs, node/edge labels, escaping, reserved tokens, and `NOT_SAFELY_CORRECTABLE` | Unsafe/unrecoverable input blocks                                                 |
| `MermaidRenderValidator`       | Renderer execution, render failures, screenshots, and evidence                      | Render failure blocks production                                                  |
| `DiagramGeometryValidator`     | Label overlap, element overlap, crossings, spacing, and default-view geometry       | Threshold breach blocks                                                           |
| `DiagramComplexityValidator`   | Congestion, node/edge warning thresholds, and decomposition recommendations         | Blocking readability breach blocks                                                |
| `MermaidQualityGate`           | Aggregates all component results and controls publication                           | Produces PASS/FAIL/APPROVED_WITH_WARNINGS                                         |
| `MermaidQualitySummaryAdapter` | Reads both quality JSON files and produces stable Summary metadata                  | Exposes status, publication, counts, renderer/environment, paths, and diagram IDs |
| `MermaidRendererVersionCheck`  | Verifies renderer availability and configured version before rendering              | Unavailable/incompatible renderer blocks                                          |

Renderer fallback: when the renderer is unavailable, the report status is `RENDERER_UNAVAILABLE`; production publication is blocked, while local development may downgrade it only through an explicit local-development override.

Configuration behavior: `diagramValidation` and `diagramValidation.mermaid` are mandatory objects. `renderingProfile` and `readability` are optional and receive defaults. Missing or malformed mandatory sections in `.config/diagram-validation.yaml` are blocking; missing optional nested keys in valid sections use defaults. `strictCompatibility: false` may suppress advisory diagnostics only and never permits syntax or compatibility failures.

Geometry evidence uses SVG coordinates, element identifiers, bounding boxes, intersection area, overlap percentage, spacing distance, and involved edge IDs. The public report is camelCase; any internal snake_case adapter must be transformed before public JSON is written.

`MermaidQualityMarkdownReportGenerator` must generate these sections: Summary, Configuration Resolution, Rendering Profile, Quality Gate Result, Blocking Findings, Warning Findings, Diagram-Level Results, Corrected Mermaid Examples, Not Safely Correctable Items, Viewer Smoke Test Results, and Fixture Matrix Results. `MermaidQualitySummaryAdapter` reads `mermaid-quality-report.json` and `mermaid-quality-gate.json` and produces stable Summary metadata.

### Publication quality gates

- Mermaid syntax MUST be validated before Markdown persistence.
- Unsupported, deprecated, and experimental syntax MUST be rejected.
- Any syntax error or compatibility violation MUST reject publication.
- Relationship labels MUST remain visible and readable at default zoom and MUST NOT overlap containers, components, boundaries, cards, external systems, or other visible architectural elements.
- Dense diagrams MUST be spaced, reorganized, simplified, or split before publication; if safe optimization cannot restore readability, the gate is `BLOCKED` and `human_gate_required: true`.

## Project Structure

### Documentation

```text
specs/034-mermaid-diagram-quality/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── mermaid-quality-report.schema.json
│   └── mermaid-quality-gate.schema.json
├── quickstart.md
└── checklists/requirements.md
```

### Source Code

```text
src/shared/utils/
├── sanitize_diagrams.py             # extend shared Mermaid normalization/reporting
├── validate_diagram.py              # extend pre-write gate and structured result handling
└── mermaid_quality_auditor.py       # internal batch discovery, validation, correction, visual evidence

src/shared/checks/
└── suites/mermaid_files.py           # extend project-wide regression checks as needed

tests/
├── unit/                             # sanitizer, parser, schema, heuristics
├── integration/                      # pre-write gate and project audit fixtures
└── fixtures/mermaid/                 # valid, correctable, invalid, dense C4 examples

src/modules/ava-fabric-agents/asis-diagnostic/agents/
└── documentation-asis.md             # update generation/write protocol if required

src/modules/ava-fabric-agents/shared/
└── mermaid-guardrails.md             # update canonical rules if required
```

**Structure Decision**: Keep implementation in shared Python utilities because multiple phases and agents emit Mermaid. The auditor is an internal utility, not a new user-facing agent or skill. Update agent instruction files only to mandate use of the shared gate and report contract.

## Phase 0 — Research Completed

Research decisions are recorded in [research.md](research.md): reuse existing sanitizer/gate, configuration-driven compatibility, source plus optional rendered validation, deterministic-only corrections, canonical JSON/Markdown reporting, and C4-specific readability evidence.

## Phase 1 — Design Completed

- [data-model.md](data-model.md) defines artifact, syntax finding, visual finding, correction, report states, and invariants.
- [contracts/mermaid-quality-report.schema.json](contracts/mermaid-quality-report.schema.json) defines the machine-readable report contract.
- [quickstart.md](quickstart.md) defines validation scenarios and expected gate behavior.
- `.github/copilot-instructions.md` now references this plan.

## Implementation Workstreams

1. **Discovery and extraction** — enumerate `.mmd` files and Markdown Mermaid fences without inventing paths; associate each artifact with project-relative identity and trace metadata.
2. **Configuration resolution** — load mandatory `diagramValidation.mermaid`, apply defaults to optional `renderingProfile` and `readability`, default baseline/renderer to 11.14.0, and emit a blocking configuration finding on missing/malformed mandatory sections.
3. **Syntax and sanitization validation** — run `MermaidSyntaxValidator` and `MermaidSanitizationValidator` for declarations, nodes, relationships, safe IDs, labels, edge labels, reserved tokens, and unsupported syntax.
4. **Correction and persistence** — apply only deterministic transformations, revalidate, and write only passing corrected content through the gate; classify semantic changes as `NOT_SAFELY_CORRECTABLE`.
5. **Render and geometry validation** — run `MermaidRenderValidator` and `DiagramGeometryValidator` using the effective profile; verify zero blocking overlaps, default-zoom visibility, crossings, and spacing.
6. **Complexity and layout optimization** — run `DiagramComplexityValidator`; space, reorganize, shorten/wrap, or split diagrams by clear boundaries when safe; block if readability cannot be restored.
7. **Reporting and quality gate** — generate canonical JSON, Markdown projection, and gate JSON; ensure every artifact and every required finding category is represented.
8. **Viewer smoke tests and regression** — render Blueprint, C4 Container, Flow, Dependency, Integration, and Architecture fixtures; confirm no `Syntax error in text` and no overlap at default view.
9. **Summary integration and documentation** — run `MermaidQualitySummaryAdapter` after the gate and before publication; update affected agent instructions in pt-BR, preserve Skill/Agent separation, update catalogs/changelog/IO docs, and keep security orchestration unchanged.

### Dependency sequence

`DiagramValidationConfigLoader` → schema validation → `MermaidSyntaxValidator` → `MermaidSanitizationValidator` → `MermaidRenderValidator` → `DiagramGeometryValidator` → `DiagramComplexityValidator` → `MermaidQualityGate` → `MermaidQualityMarkdownReportGenerator` → `MermaidQualitySummaryAdapter` → publication.

## Complexity Tracking

| Complexity                          | Justification                                                                                                   | Simpler alternative rejected because                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Optional rendered-geometry analysis | Source syntax cannot prove label/container overlap; rendered evidence is necessary for the visual requirements. | Structural heuristics alone would produce false confidence.                     |
| Canonical JSON plus Markdown report | Machine gates need structured data while architects need readable diagnostics.                                  | Markdown-only would require fragile downstream parsing.                         |
| Cross-cutting shared utility        | Mermaid is emitted by multiple agents/phases.                                                                   | Per-agent validators would diverge and violate the single write-gate principle. |

## Post-Design Constitution Re-Check

- [x] Configuration-driven compatibility retained.
- [x] Existing agent/skill separation retained.
- [x] No new output path is assumed until existing contracts are reconciled during implementation.
- [x] Security masking, trace propagation, and F1 security orchestration remain intact.
- [x] BDD scenarios and quality gates are represented in the design artifacts.
- [x] No unresolved `NEEDS CLARIFICATION` items remain.

**Post-design decision**: **PASS — ready for `/speckit.implement`**. The clarified plan has objective configuration, ownership, schemas, thresholds, fallback behavior, and validation activities.
