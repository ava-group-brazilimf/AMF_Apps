# Agent Development Tasks: Mermaid Diagram Quality

**Plan**: `specs/034-mermaid-diagram-quality/plan.md`
**Agent ID**: `ava-asis-documentation` + shared Mermaid validation utilities | **Phase**: `F1` cross-cutting | **Module**: `asis-diagnostic` + `src/shared/utils`

> This is a modify-existing cross-cutting feature. No new user-facing agent, SKILL.md, module registration, or schema change is planned unless implementation discovery proves an existing contract must be extended. Complete categories sequentially; tasks marked `[P]` can run in parallel after their dependencies.

---

## Category 1 -- Agent Frontmatter & Contract Definition

- [x] 1.1 Confirm the existing `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md` frontmatter remains valid with only `name`, `version`, `description`, and `allowed-tools`, and record the required MINOR version bump for the new publication-gate behavior.
- [ ] 1.2 Confirm the existing `.github/skills/ava-asis-documentation/SKILL.md` remains a thin router and does not absorb Mermaid generation or validation behavior.
- [ ] 1.3 Reconcile the feature output contract with existing contracts in `src/shared/utils/validate_diagram.py`, `src/shared/utils/sanitize_diagrams.py`, and the documentation agent; select canonical project-relative report paths without creating duplicate artifacts.
- [ ] 1.4 Define and implement `diagramValidation.mermaid.acceptanceBaselineVersion`, `rendererVersion`, and `strictCompatibility`; default the baseline and renderer to `11.14.0`, fail closed on malformed configuration, and preserve external renderer configurability.
- [ ] 1.5 Document the diagram write invariant in `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md`: every generated `.mmd` artifact must pass the shared write gate before persistence.
- [x] 1.6 Implement `DiagramValidationConfigLoader` for `.config/diagram-validation.yaml`; require `diagramValidation` and `diagramValidation.mermaid`, default optional `renderingProfile` and `readability`, validate `maxNodeLabelLengthChars: 60` and `maxRelationshipLabelLengthChars: 80`, and block invalid types.

---

## Category 2 -- Agent Behavior & Instructions

Depends on Category 1.

- [ ] 2.1 Update the Mermaid generation and persistence instructions in `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md` in Brazilian Portuguese to require fenced `mermaid` blocks in Markdown and raw Mermaid syntax in `.mmd` files.
- [ ] 2.2 Add deterministic Mermaid sanitization instructions to `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md` covering quotes, parentheses, brackets, pipes, HTML fragments, control characters, Unicode hazards, reserved tokens, invalid node identifiers, invalid relationship definitions, and secret masking.
- [ ] 2.3 Add the correction/revalidation loop to `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md`: capture findings, apply only safe corrections, revalidate, persist only passing content, and stop after the configured retry limit.
- [ ] 2.4 Add C4 Container readability authoring rules to `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md` for concise/wrapped relationship labels, explicit layout direction, spacing, grouping, edge-crossing reduction, default-zoom readability, and segmentation of dense diagrams.
- [ ] 2.5 Add the quality-gate behavior to `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md`: `APPROVED`, `APPROVED_WITH_WARNINGS`, or `BLOCKED`; any Mermaid 11.14.0 syntax/compatibility error or blocking readability defect must reject publication and set `human_gate_required: true`.
- [ ] 2.6 Add the required `traceId`, project path, evidence, and next-agent propagation rules to the agent instructions without changing unrelated F1 security orchestration behavior.
- [ ] 2.7 Update `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md` with the canonical Mermaid 11.14.0 compatibility, supported-syntax, C4 readability, label-safety, overlap, decomposition, and publication-gate rules after reconciling existing guidance.
- [ ] 2.8 Define deterministic versus semantic transformations: normalize IDs, escape labels, remove unsupported HTML, shorten/wrap labels, increase spacing, and split by clear boundaries automatically; require regeneration/human approval for relationship removal/direction changes, boundary or container changes, concept renaming, dependency omission, or semantic reclassification.
- [ ] 2.9 Define separate `maxNodeLabelLengthChars: 60` and `maxRelationshipLabelLengthChars: 80`; prefer wrapping and allow truncation only with demonstrated semantic preservation.

---

## Category 3 -- Shared Schema Updates

The feature introduces a report contract but does not change `agent-task` or `agent-result` schemas. Implement the report schema as a standalone contract and validate it.

- [x] 3.1 [P] Finalize `specs/034-mermaid-diagram-quality/contracts/mermaid-quality-report.schema.json` against the implemented report fields, including artifact identity, syntax findings, visual findings, corrections, summary counts, gate status, and `human_gate_required`.
- [ ] 3.2 [P] Add or update the runtime copy of the Mermaid quality report schema at the repository’s established shared-schema location only if existing tooling requires a source copy outside `specs/034-mermaid-diagram-quality/contracts/`.
- [ ] 3.3 [P] Add schema validation coverage rejecting missing `traceId`, incomplete authoritative `artifactPath`/`diagramId` entries, invalid statuses, invalid confidence ranges, and `BLOCKED` reports without `humanGateRequired: true`.
- [ ] 3.4 [P] Run `python debug_schema.py` or the repository’s established schema validation command if shared schemas are changed, and record the result in the implementation evidence.
- [x] 3.5 [P] Add and validate `contracts/mermaid-quality-gate.schema.json`, including renderer-unavailable behavior, check statuses, publication permission, and mandatory `11.14.0` baseline.
- [ ] 3.6 [P] Keep `contracts/*.schema.json` as canonical sources; generate/copy runtime schemas to `src/contracts/` only when required and add a drift comparison that fails the quality gate on divergence.

---

## Category 4 -- Module Registration

No new agent or module is planned.

- [ ] 4.1 Verify `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml` already registers `ava-asis-documentation`; do not add a duplicate entry.
- [ ] 4.2 Verify the top-level `module.yaml` remains unchanged and preserves the required `bmad_version`.
- [ ] 4.3 [P] If implementation creates a dedicated internal batch-auditor module entry, add exactly one module-level registration with its real file path and document why it cannot be invoked through the existing documentation agent; otherwise record Category 4 as no-op.

---

## Category 5 -- Quality Gate Checklists

- [ ] 5.1 Extend the applicable F1 readiness/consistency checklist in `src/modules/ava-fabric-agents/asis-diagnostic/` or the existing shared checklist location with Mermaid artifact discovery, completeness, sanitization, syntax, readability, and traceability checks.
- [ ] 5.2 Add checklist items requiring every discovered `.mmd` file and Markdown Mermaid fence to appear in `mermaid-quality-report.json` and the Markdown projection.
- [ ] 5.3 Add checklist items requiring zero published syntax errors, no unsafe labels, revalidation after corrections, and `BLOCKED` plus `human_gate_required` for persistent failures.
- [ ] 5.4 Add C4 Container checks for relationship-label visibility, container/component/card/external-system/boundary overlap, edge crossings, congestion, default-zoom readability, long-label shortening/wrapping, and decomposition recommendations.
- [ ] 5.5 [P] Verify all new checklist entries use the repository’s required `- [ ]` format and are compatible with existing F1 gate automation.

---

## Category 6 -- Acceptance Validation & QA Integration

Depends on Category 2 and the shared utility implementation.

- [ ] 6.1 [P] Add unit tests for `src/shared/utils/sanitize_diagrams.py` covering clean flowcharts, sequence diagrams, C4 diagrams, class diagrams, ER diagrams, Gantt diagrams, fences, invisible characters, prohibited characters, emojis, literal `\\n`, unsafe labels, invalid node IDs, unclosed subgraphs, and self-loops.
- [ ] 6.2 [P] Add CLI tests for `src/shared/utils/validate_diagram.py` covering exit `0` for clean content, exit `2` for deterministic fixes, exit `1` for unfixable content, no-write behavior on failure, and sanitized output on success.
- [x] 6.3 Implement and test the project-wide Mermaid auditor at the selected shared path from `specs/034-mermaid-diagram-quality/plan.md`; verify discovery of `.mmd` files and fenced Mermaid blocks in Markdown without invented paths and require one report entry per artifact.
- [ ] 6.4 Add report-generation tests verifying `mermaid-quality-report.json`, `mermaid-quality-report.md`, and `mermaid-quality-gate.json` contain project name, unchanged `traceId`, artifact completeness, syntax evidence, visual evidence status, correction attempts, and final gate decision.
- [ ] 6.4a Add report-generation tests for the canonical camelCase fields (`schemaVersion`, `projectName`, `traceId`, `feature`, `generatedAt`, baseline/renderer versions, default/effective profiles, counts, and findings) and reject legacy snake_case public output.
- [ ] 6.4b Require exactly one non-empty `correctedMermaidExample` or `notSafelyCorrectableReason` for every finding.
- [ ] 6.5 [P] Add fixtures under the repository’s established test-fixture location for valid diagrams, correctable diagrams, prohibited syntax, incomplete blocks, dense C4 Container relationships, empty projects, missing renderer, and secret-containing labels.
- [ ] 6.6 [P] Add structural readability tests for label/container/component/card/external-system/boundary overlap heuristics, excessive edge crossings, congestion, connector length, default-zoom readability, complexity, long-label handling, and C4 segmentation recommendations.
- [ ] 6.7 [P] Add renderer-backed integration tests against Mermaid 11.14.0 when the configured renderer is available; when unavailable, assert that the report records limited visual evidence rather than claiming a visual PASS.
- [ ] 6.7a [P] Implement `MermaidRendererVersionCheck` before render validation and smoke tests; emit `RENDERER_UNAVAILABLE` or blocking `COMPATIBILITY` findings for unavailable/incompatible renderers.
- [ ] 6.7b [P] Add structured `geometryEvidence` tests for SVG coordinate system, element IDs, bounding boxes, intersection area, overlap percentage, spacing distance, and involved edge IDs.
- [ ] 6.7c [P] Require `geometryEvidence` for `OVERLAP`, `CROSSING`, and `SPACING` findings and reject those findings when required evidence is absent.
- [ ] 6.7d [P] Add fixtures for strict compatibility true/false with advisory findings and blocking compatibility violations; blocking Mermaid 11.14.0 incompatibility must fail in both modes.
- [ ] 6.8 Map the feature scenarios to F5 QA inputs by updating the applicable behavior/scenario/test-case artifacts or generation instructions used by `ava-qa-behavior-mapping`, `ava-qa-scenario-generator`, and `ava-qa-test-case-generator`.
- [ ] 6.9 Run existing Mermaid and Summary regression checks, including `src/shared/checks/suites/mermaid_files.py`, `src/shared/checks/suites/mermaid_runtime.py`, Summary HTML checks, and any applicable validation scripts; assert that no portal/report output contains `Syntax error in text` or `mermaid version 11.14.0` error text.
- [ ] 6.10 Run the quickstart scenarios from `specs/034-mermaid-diagram-quality/quickstart.md` against a controlled project and preserve evidence for syntax correctness, Mermaid 11.14.0 rendering, blueprint rendering, label visibility, no-overlap behavior, decomposition, and no-manual-correction delivery without modifying unrelated project outputs.
- [ ] 6.11 [P] Add viewer smoke tests for Blueprint Architecture, C4 Container, Flow, Dependency, Integration, and general Architecture diagrams at the default 1440x900, zoom 1.0 profile; verify no `Syntax error in text`, rendering success, visible labels, zero blocking overlap, and default-view readability.

---

## Category 7 -- Documentation & Catalog Update

Can run in parallel with Category 6 after behavior and contract decisions are stable.

- [ ] 7.1 [P] Update `docs/agents-catalog.md` with the `ava-asis-documentation` version, Mermaid publication-gate behavior, diagnostic outputs, and validation ownership.
- [ ] 7.2 [P] Add a `CHANGELOG.md` entry for the agent MINOR version bump and the new Mermaid quality-gate/report contract; mention any backward-compatible schema additions.
- [ ] 7.3 [P] Update `docs/summary-io-map.md` if the Summary consumes the Mermaid quality report or new Mermaid diagnostic artifacts, documenting the canonical input paths and fallback behavior.
- [x] 7.3a [P] Implement `MermaidQualitySummaryAdapter` to read both quality JSON files and surface status, publicationAllowed, blocking/warning counts, rendererStatus, executionEnvironment, affected artifact paths, and affected diagram IDs; stable JSON remains mandatory even if UI rendering is deferred.
- [x] 7.4a [P] Implement `MermaidQualityMarkdownReportGenerator` with all eleven required Markdown sections and preserve every finding/example/reason.
- [ ] 7.4 [P] Update `docs/full-pipeline-guide.md` or the applicable F1 execution guide with the pre-write Mermaid validation and persistent-failure gate.
- [ ] 7.5 [P] Update `specs/034-mermaid-diagram-quality/quickstart.md` with the final auditor command, exact report paths, renderer availability behavior, and regression commands after implementation paths are finalized.
- [ ] 7.6 [P] Verify the agent/module diagram and any generated catalog references remain consistent with `module.yaml`; do not add a new agent node unless Category 4 created a registered internal auditor.

---

## Dependency Graph

```text
Category 1
   |
   v
Category 2 -----> Category 6
   |                  |
   v                  v
Category 3        Category 7
   |
   v
Category 4 -----> Category 5
```

### Requirement dependency overlays

- **Correctness path**: 1.4 -> 2.2/2.3/2.5 -> 3.1/3.3 -> 6.1/6.2/6.3/6.4 -> 6.7/6.9.
- **Readability path**: 2.4/2.7 -> 5.4 -> 6.5/6.6/6.7 -> 6.10.
- **Analysis completeness**: 6.3 must finish discovery before 6.4, 6.6, and 6.10 can be accepted; every artifact must have syntax and readability status, including explicit `NOT_AVAILABLE` evidence when rendered geometry cannot be obtained.
- **Publication gate**: 2.5 depends on both correctness and readability outcomes; no artifact can be marked publishable when Mermaid 11.14.0 syntax validation fails or a blocking overlap/congestion finding remains.
- **Blueprint/C4 acceptance**: 2.4 -> 6.6 -> 6.7 -> 6.10; C4 Container labels must be verified for no intersection with containers, components, cards, boundaries, or external systems.
- **Renderer fallback**: renderer available -> syntax + render geometry + smoke test; renderer unavailable -> structural checks plus `RENDERER_UNAVAILABLE`, blocking production publication and warning-only only for explicitly configured local development.
- **Finding contract**: every finding must include artifact, diagram, category, root cause, impact, recommendation, evidence, and either a corrected Mermaid example or `notSafelyCorrectableReason`.

- Category 1 must finish first because it establishes the existing agent contract, canonical configuration, and write invariant.
- Category 2 depends on Category 1 and unblocks implementation tests and QA integration.
- Category 3 can proceed after the report model is stable; it does not modify `agent-task`/`agent-result` by default, but must include both report and gate schemas.
- Category 4 verifies registration and is normally a no-op for this modify-existing feature.
- Category 5 depends on the finalized gate semantics.
- Category 6 depends on behavior, report/gate contracts, and validator ownership; its independent fixtures/unit tests can run in parallel once interfaces stabilize.
- Category 7 can run in parallel with Category 6 after paths and version changes are confirmed.

## Parallel Execution Examples

- After Category 1: run 3.1, 3.3, 4.1, and 5.1 in parallel once the report contract and gate paths are agreed.
- During Category 6: run sanitizer unit tests, CLI gate tests, fixture creation, schema tests, and structural readability tests in parallel because they use separate files.
- During Category 7: update catalog, changelog, Summary IO map, pipeline guide, and quickstart in parallel after implementation paths are final.

## Implementation Strategy

1. **MVP**: enforce shared pre-write sanitization/validation, produce the canonical syntax report and gate, and cover clean/correctable/unfixable fixtures.
2. **Increment 2**: add complete Markdown-fence/project-wide discovery and Summary/QA integration.
3. **Increment 3**: add structural readability heuristics and C4-specific recommendations.
4. **Increment 4**: add optional rendered-geometry evidence and block persistent visual defects.
5. **Final hardening**: run all regression suites, update documentation/catalogs, and verify no invalid Mermaid artifact is publishable.

## Completion Checklist

- [ ] 8.1 Complete all seven categories or explicitly mark no-op categories with evidence.
- [ ] 8.2 Confirm existing `ava-asis-documentation` frontmatter, SKILL routing, and module registration are valid.
- [x] 8.3 Confirm the shared sanitizer and pre-write gate enforce publication safety.
- [x] 8.4 Confirm the canonical report schema and report artifacts validate successfully.
- [x] 8.5 Confirm syntax, correction, empty-input, readability, and blocking scenarios pass.
- [ ] 8.6 Confirm existing Mermaid and Summary regression checks pass.
- [ ] 8.7 Confirm catalog, changelog, IO map, pipeline guide, and quickstart are updated.
- [ ] 8.8 Confirm no invalid Mermaid artifact is delivered as a successful output.
