# Implementation Tasks: Architecture Blueprint Diagram Generation

**Plan**: `specs/035-architecture-blueprint-diagram/plan.md`
**Specification**: `specs/035-architecture-blueprint-diagram/spec.md`
**Scope**: End-to-end observability from architecture-agent execution through Mermaid rendering and publication.

> Tasks are dependency-ordered. `[P]` means the task can run in parallel with other tasks in the same dependency boundary. Every task includes an explicit file path.

## Category 1 — Contract and ownership baseline

- [ ] T001 Confirm AS-IS owner `ava-asis-solution-delphi`, canonical artifact `projects/{project_name}/outputs/asis/diagrams/architecture-blueprint.mmd`, and companion document contract in `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md`.
- [ ] T002 Confirm TO-BE owner `ava-tobe-architecture-design`, `CB` dispatch through `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`, and canonical artifact `projects/{project_name}/outputs/tobe/diagrams/architecture-blueprint.mmd`.
- [ ] T003 [P] Add the AS-IS and TO-BE Blueprint ownership records to `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` without changing existing output paths.
- [ ] T004 [P] Add canonical Blueprint artifact entries and responsible-agent metadata to `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml` and the TO-BE module registry file that owns `ava-tobe-architecture-design`.
- [ ] T005 [P] Record the lifecycle contract and status vocabulary in `specs/035-architecture-blueprint-diagram/data-model.md` and validate the JSON schema at `specs/035-architecture-blueprint-diagram/contracts/blueprint-quality-report.schema.json`.

## Category 2 — Agent execution and generation validation

- [ ] T006 Update the AS-IS execution protocol in `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md` to emit an explicit Blueprint generation status, expected artifact path, actual artifact path, and trace ID after the Mermaid write gate.
- [ ] T007 Update the TO-BE `CB` execution protocol in `src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-design-tobe.md` to emit the same generation metadata after writing `tobe/diagrams/architecture-blueprint.mmd`.
- [ ] T008 Update the `CB` orchestration chain in `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` to verify the generating agent executed, record retry outcomes, and stop using a placeholder `.mmd` as a recovery artifact.
- [ ] T009 Update the AS-IS phase orchestration validation in `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` to distinguish `AGENT_NOT_EXECUTED` from an agent that executed but failed to produce the Blueprint.
- [ ] T010 Implement deterministic non-empty and unresolved-token checks for both canonical `.mmd` files in `src/shared/utils/validate_diagram.py`, classifying empty/placeholder/invalid source as generation failure before rendering.
- [ ] T011 [P] Add unit fixtures for valid, empty, placeholder-only, unresolved-token, and syntactically invalid Blueprint Mermaid content under `tests/fixtures/mermaid/architecture-blueprint/`.
- [ ] T012 [P] Add focused tests for generation status classification and placeholder rejection in `tests/unit/test_blueprint_generation_validation.py`.

## Category 3 — Registration, discovery, and path resolution

- [ ] T013 Implement a shared canonical-path resolver for AS-IS and TO-BE Blueprint artifacts in `src/shared/utils/blueprint_quality.py`, using project configuration and phase ownership rather than hardcoded project names.
- [ ] T014 Implement artifact discovery in `src/shared/utils/blueprint_quality.py` that records `expectedPath`, `discoveredPath`, artifact size, registration status, and alternate candidate paths without silently substituting an unowned file.
- [ ] T015 Add explicit `MISSING_ARTIFACT`, `DISCOVERY_FAILED`, and `UNREGISTERED` classifications in `src/shared/utils/blueprint_quality.py` and preserve the responsible generating agent for each finding.
- [ ] T016 [P] Add registration/discovery regression checks to `src/shared/checks/suites/mermaid_files.py` for both `asis/diagrams/architecture-blueprint.mmd` and `tobe/diagrams/architecture-blueprint.mmd`.
- [ ] T017 [P] Add unit tests for AS-IS/TO-BE path resolution, alternate-path reporting, missing files, and registration mismatch in `tests/unit/test_blueprint_discovery.py`.

## Category 4 — Quality report and diagnostics

- [ ] T018 Implement `BlueprintArtifactRecord` construction and status aggregation in `src/shared/utils/blueprint_quality.py` with separate `agentExecutionStatus`, `generationStatus`, `artifactStatus`, `renderingStatus`, and `gateStatus` fields.
- [ ] T019 Implement canonical JSON and Markdown quality-report writers in `src/shared/utils/blueprint_quality.py` using `specs/035-architecture-blueprint-diagram/contracts/blueprint-quality-report.schema.json` and the paths defined by the Summary output contract.
- [ ] T020 Add explicit diagnostic findings for `MISSING_INPUT`, `AGENT_NOT_EXECUTED`, `GENERATION_FAILED`, `MISSING_ARTIFACT`, `DISCOVERY_FAILED`, `RENDERING_FAILED`, and `PASS` in `src/shared/utils/blueprint_quality.py`.
- [ ] T021 [P] Add report-schema and status-aggregation tests in `tests/unit/test_blueprint_quality_report.py` covering expected path, actual path, owner, statuses, remediation, and unchanged trace ID.
- [ ] T022 [P] Add Markdown report rendering tests in `tests/unit/test_blueprint_quality_markdown.py` verifying that generation and rendering failures are reported separately.

## Category 5 — Summary integration and rendering

- [ ] T023 Update `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` to inject only validated Blueprint source into `D.staticDiagrams.asisArchBlueprint` and `D.staticDiagrams.tobeArchBlueprint`, while retaining explicit lifecycle metadata.
- [ ] T024 Update `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` to distinguish missing source, registration/discovery failure, invalid generation, and renderer-ready source instead of silently collapsing all empty values.
- [ ] T025 Update `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` so the Architecture Blueprint sections consume the canonical `D.staticDiagrams` entries and display diagnostic metadata without treating the unavailable-diagram text as a successful result.
- [ ] T026 Update `renderAllDiagrams()` in `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` to preserve the source failure category and identify the expected artifact and generating agent when no source is available.
- [ ] T027 Update `renderStaticDiagrams()` in `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` to record `RENDERING_FAILED` independently when Mermaid rendering rejects otherwise valid source, while preserving the source artifact evidence.
- [ ] T028 [P] Add Summary builder integration tests in `tests/integration/test_blueprint_summary_integration.py` covering AS-IS injection, TO-BE injection, metadata propagation, and source discovery failure.
- [ ] T029 [P] Add renderer integration tests in `tests/integration/test_blueprint_renderer_integration.py` covering `renderAllDiagrams()`, `renderStaticDiagrams()`, successful rendering, renderer failure, and placeholder suppression.

## Category 6 — Publication gates and pipeline observability

- [ ] T030 Integrate the Blueprint quality evaluator into `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` so a required missing or invalid Blueprint produces a blocking error-level finding.
- [ ] T031 Integrate the Blueprint quality evaluator into `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` so publication cannot proceed when required Blueprint generation, discovery, or rendering fails.
- [ ] T032 Update `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md` to document expected artifact, actual artifact, generating agent, generation status, rendering status, and publication-blocking behavior.
- [ ] T033 Update `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` to consume and expose Blueprint quality metadata while preserving Summary as a consumer rather than an architecture producer.
- [ ] T034 Add publication-gate integration tests in `tests/integration/test_blueprint_publication_gate.py` proving missing artifact, invalid generation, discovery failure, and rendering failure return a blocking result.
- [ ] T035 [P] Add end-to-end observability fixture tests in `tests/integration/test_blueprint_pipeline_observability.py` proving the chain from agent execution through artifact discovery, Summary injection, renderer result, quality report, and gate decision.

## Category 7 — Documentation, regression, and delivery readiness

- [ ] T036 [P] Update `docs/summary-io-map.md` with canonical AS-IS/TO-BE Blueprint source paths, owners, renderer keys, and diagnostic statuses.
- [ ] T037 [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md` and the TO-BE output-path documentation with the canonical Mermaid artifact contracts.
- [ ] T038 [P] Update `CHANGELOG.md` with the Blueprint lifecycle validation and publication-gate change, using the version bump required by any affected agent contract.
- [ ] T039 Run the focused Blueprint tests and existing Mermaid/Summary validation suites, recording results in `specs/035-architecture-blueprint-diagram/quickstart.md` or the project test evidence path.
- [ ] T040 Verify no successful report contains `(diagrama não disponível — execute o agente correspondente)` in a required Blueprint section and that missing/failed cases contain explicit diagnostic findings in `tests/integration/test_blueprint_publication_gate.py`.
- [ ] T041 Verify the legacy repository remains read-only and that `trace_id` is unchanged from workflow input through quality report and Summary metadata in `tests/integration/test_blueprint_pipeline_observability.py`.

## Dependency Order

```text
T001-T005
   ↓
T006-T012 ───────────────┐
   ↓                     │
T013-T017               │
   ↓                     │
T018-T022               │
   └──────────────┬──────┘
                  ↓
T023-T029
                  ↓
T030-T035
                  ↓
T036-T041
```

## Parallel Execution Opportunities

- **After contract baseline**: T006–T009 can proceed in parallel by ownership area; T010–T012 can proceed in parallel with instruction updates once the canonical paths are confirmed.
- **After generation design**: T013–T017 and T018–T022 can proceed in parallel because discovery/path resolution and report projection have separate files/contracts.
- **After quality model completion**: T023–T027 can proceed in parallel by builder/template responsibility; T028–T029 can proceed in parallel after their implementation seams exist.
- **After Summary integration**: T030–T035 can proceed in parallel by gate, documentation, and end-to-end test responsibility.
- **Delivery**: T036–T038 can proceed in parallel; T039–T041 are final validation tasks.

## Implementation Strategy

1. Establish canonical ownership and paths before changing behavior.
2. Make generation and discovery failures observable before changing the renderer.
3. Integrate validated source and metadata into Summary.
4. Separate rendering failures from source failures.
5. Enforce the publication gate only after diagnostics are available.
6. Finish with regression, documentation, and end-to-end traceability validation.

## Completion Criteria

- [ ] All tasks T001–T041 are complete.
- [ ] AS-IS and TO-BE Blueprint owners and canonical paths are registered consistently.
- [ ] Generation, discovery, rendering, and publication statuses are independently observable.
- [ ] Required missing or unrenderable diagrams block publication.
- [ ] Successful Blueprint sections show rendered Mermaid and no unavailable-diagram placeholder.
- [ ] Focused and regression test suites pass.
