# Implementation Tasks: Architecture Blueprint Mermaid Compatibility

**Plan**: `specs/036-architecture-blueprint-mermaid-compatibility/plan.md`
**Spec**: `specs/036-architecture-blueprint-mermaid-compatibility/spec.md`
**Feature directory**: `specs/036-architecture-blueprint-mermaid-compatibility/`
**Scope**: Mermaid compatibility validation and remediation only; artifact generation, discovery, injection, and orchestration are not reimplemented.

## Category 1 — Feature and Context Validation

- [ ] T001 Verify the feature directory exists at `specs/036-architecture-blueprint-mermaid-compatibility/` and contains `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/blueprint-compatibility-report.schema.json`.
- [ ] T002 Verify `.github/copilot-instructions.md` references `specs/036-architecture-blueprint-mermaid-compatibility/plan.md` as the active SpecKit plan without altering unrelated instructions.
- [ ] T003 [P] Add a setup diagnostic in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` that records the resolved feature directory, project name, and empty `BRANCH` value without using branch metadata to construct artifact or report paths.
- [ ] T004 [P] Add tests in `tests/summary/test_blueprint_compatibility_context.py` proving that an empty `BRANCH` does not change artifact paths, report paths, or task execution, and that required branch metadata produces an explicit diagnostic rather than silent continuation.

## Category 2 — Renderer Source of Truth and Runtime Discovery

- [ ] T005 Locate and codify the Summary renderer source in `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`, including the inline `mermaid.min.js` bundle path, `mermaid.initialize()` configuration, and `mermaid.render()` call path.
- [ ] T006 Implement effective renderer metadata discovery in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py`, reporting `rendererSource`, bundle hash/path, runtime version, initialization options, and whether the configured runtime is the Summary runtime.
- [ ] T007 Implement runtime version verification in `src/modules/ava-fabric-agents/summary/utils/render_blueprint_compatibility.py`, failing with `RENDERER_CONFIGURATION_FAILURE` when the bundle is missing/unreadable and with `MERMAID_VERSION_INCOMPATIBILITY` when the effective runtime differs from the required baseline.
- [ ] T008 [P] Add renderer source-of-truth tests in `tests/summary/test_renderer_source_of_truth.py` proving that validation uses the Summary-local bundle and rejects a separate Mermaid installation or mismatched runtime.
- [ ] T009 [P] Add a minimal runtime probe fixture in `tests/summary/fixtures/renderer_probe.html` that loads the same inline bundle/configuration as Summary and exposes effective Mermaid version, C4 parser availability, and initialization failures.

## Category 3 — Dialect and Static Compatibility Validation

- [x] T010 Implement dialect detection in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` for the first Mermaid declaration, including `flowchart` and `C4Container`, and classify unknown declarations as `UNSUPPORTED_DIALECT`.
- [x] T011 Implement C4 construct extraction in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` for `Person`, `Container`, `ContainerDb`, `System_Ext`, and `Rel`, preserving source line/column and raw source evidence.
- [ ] T012 Implement static validation rules in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` for supported declarations, malformed C4 calls, unsupported directives, invalid parameter counts, and unrecognized C4 constructs; return `INVALID_MERMAID` or `UNSUPPORTED_C4_SYNTAX` with explicit diagnostics.
- [x] T013 Ensure static validation consults the effective renderer capability record before returning `VALID_MERMAID`; a `C4Container` source must remain unsupported or inconclusive when the configured runtime has not proven C4 support.
- [x] T014 Ensure static validation preserves the raw `.mmd` source and separately records sanitized content, transformations, hashes, and line-oriented diagnostics without overwriting the original input.
- [ ] T015 [P] Add static validator unit tests in `tests/summary/test_blueprint_static_validation.py` for valid flowchart, valid C4 declarations, invalid Mermaid, unknown dialect, malformed C4 syntax, unsupported directives, and C4 support unavailable.
- [x] T016 [P] Add the observed Sophia fixture at `tests/summary/fixtures/sophia-tobe-c4container.mmd`, beginning with `C4Container` and containing `Person(...)`, `Container(...)`, `ContainerDb(...)`, `System_Ext(...)`, and `Rel(...)`.

## Category 4 — Runtime Render Validation

- [ ] T017 Implement dynamic validation in `src/modules/ava-fabric-agents/summary/utils/render_blueprint_compatibility.py` using the exact Summary Mermaid bundle, initialization, and `mermaid.render()` path rather than a separately installed Mermaid runtime.
- [x] T018 Capture parser exceptions, initialization exceptions, unsupported diagram-type errors, SVG generation errors, exact error text, and available line/column details in the compatibility result in `src/modules/ava-fabric-agents/summary/utils/render_blueprint_compatibility.py`.
- [ ] T019 Implement C4 capability probing in `src/modules/ava-fabric-agents/summary/utils/render_blueprint_compatibility.py` using minimal fixtures for `C4Container`, `Person`, `Container`, `ContainerDb`, `System_Ext`, and `Rel`, distinguishing unsupported dialect from unsupported C4 construct.
- [x] T020 Add runtime result mapping in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` for `VALID_MERMAID`, `RENDERER_CONFIGURATION_FAILURE`, `MERMAID_VERSION_INCOMPATIBILITY`, `UNSUPPORTED_DIALECT`, `UNSUPPORTED_C4_SYNTAX`, and `RENDERING_FAILURE`.
- [ ] T021 Add runtime compatibility tests in `tests/summary/test_blueprint_runtime_render.py` that call the real local bundle through `mermaid.render()` and include the Sophia `C4Container` source as a regression case.
- [ ] T022 [P] Add failure fixtures and harness controls in `tests/summary/fixtures/` for renderer version mismatch, missing/incompatible configuration, parser failure, unsupported C4, and post-parse SVG/render failure.

## Category 5 — Source Integrity, Report, and Publication Gate

- [ ] T023 Implement SHA-256 tracking in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` for raw artifact content, sanitized content, `D.staticDiagrams` content, `renderAllDiagrams()` content, `renderStaticDiagrams()` content, and the exact `mermaid.render()` input.
- [ ] T024 Instrument `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` to expose non-secret source hashes and stage diagnostics for `renderAllDiagrams()`, `renderStaticDiagrams()`, and `mermaid.render()` without publishing raw source as a fallback diagram.
- [ ] T025 Add source-integrity tests in `tests/summary/test_blueprint_source_integrity.py` covering identical content, documented sanitization, truncation/escaping mismatch, and unrecorded mutation; unrecorded mismatch must produce `BLOCK`.
- [x] T026 Generate `projects/{project_name}/outputs/summary/blueprint-compatibility-report.json` from the compatibility pipeline using `contracts/blueprint-compatibility-report.schema.json` and the canonical camelCase contract, including `traceId`, `projectName`, `artifactPath`, `diagramId`, `rendererVersion`, `rendererSource`, `detectedDialect`, `c4Detected`, `c4SupportedByRenderer`, `staticValidationStatus`, `runtimeRenderStatus`, `rootCause`, `stage`, `confidence`, `construct`, `diagnosticEvidence`, `hashes`, `exactErrorMessage`, `recommendedFix`, and `publicationAllowed`.
- [ ] T027 Generate `projects/{project_name}/outputs/summary/blueprint-compatibility-report.md` from the same camelCase result as the JSON report, including renderer evidence, dialect/C4 findings, producer provenance, complete hash comparison, root-cause classification, remediation, and publication decision.
- [x] T028 [P] Add report contract tests in `tests/summary/test_blueprint_compatibility_report.py` validating the JSON schema, required fields, enum classifications, hash formats, redaction rules, and consistency between JSON and Markdown reports.
- [ ] T029 Implement the fail-closed publication gate in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` and integrate it with `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`; block when runtime rendering fails, C4 is unsupported, Mermaid version is incompatible, evidence is absent/stale, hashes mismatch, or visible Mermaid error strings would be published.
- [ ] T030 Enforce no silent conversion in `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` and related sanitization code: never rewrite `C4Container` to `flowchart` implicitly, never emit an undiagnosed placeholder, and require a recorded remediation decision for intentional conversion.
- [ ] T031 [P] Add publication-gate tests in `tests/summary/test_blueprint_publication_gate.py` proving all blocking conditions return `publicationAllowed: false` and only complete static/runtime/integrity evidence returns `publicationAllowed: true`.

## Category 6 — Fixtures, Summary Smoke Tests, and Regression Validation

- [x] T032 Add fixture `tests/summary/fixtures/valid-flowchart.mmd` for a supported standard Mermaid flowchart.
- [x] T033 [P] Add fixture `tests/summary/fixtures/invalid-mermaid.mmd` for malformed Mermaid syntax.
- [x] T034 [P] Add fixture `tests/summary/fixtures/c4container-supported.mmd` for a minimal supported C4Container diagram.
- [ ] T035 [P] Add fixture `tests/summary/fixtures/c4container-unsupported.mmd` and a mocked capability profile that reports C4 unavailable.
- [x] T036 [P] Add fixture `tests/summary/fixtures/c4container-malformed.mmd` with an invalid C4 declaration or relationship.
- [ ] T037 [P] Add fixture/profile `tests/summary/fixtures/renderer-version-mismatch.json` for a runtime version different from the Summary baseline.
- [ ] T038 [P] Add fixture/profile `tests/summary/fixtures/renderer-configuration-failure.json` for missing bundle or initialization failure.
- [ ] T039 [P] Add fixture/profile `tests/summary/fixtures/runtime-render-failure.json` for a parser-pass/render-fail scenario.
- [ ] T040 [P] Add fixture `tests/summary/fixtures/source-hash-mismatch.json` for artifact-to-renderer-input mutation.
- [ ] T041 Add Summary viewer smoke test in `tests/summary/test_blueprint_summary_smoke.py` that builds/opens the generated Summary and verifies the Architecture Blueprint does not visibly display `Syntax error in text` or `mermaid version 11.14.0`, does not finish as raw Mermaid source, and either contains rendered SVG or an explicit compatibility diagnostic with publication blocked.
- [ ] T042 Run the historical C4 fixture and read the actual Sophia TO-BE artifact at test execution time from `projects/sophia/outputs/tobe/diagrams/architecture-blueprint.mmd`; record `artifactPath`, `rawMermaidHash`, first directive, `detectedDialect`, whether it is C4Container or flowchart, `rendererInputHash`, `runtimeRenderStatus`, and `rootCause`. If it is not C4Container, state that explicitly and preserve the historical fixture as separate evidence. Missing artifact is an upstream boundary diagnostic only.
- [ ] T043 [P] Run the existing Summary validator and focused compatibility suite, preserving evidence under `tests/summary/results/` or the repository's established test-results location.

## Category 7 — Documentation and Operational Guidance

- [ ] T044 Update `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md` with the supported diagram types, C4Container support contract, required renderer configuration, and the prohibition on silent C4-to-flowchart conversion.
- [ ] T045 Update `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` with the compatibility validation order, report fields, hash checkpoints, and fail-closed publication behavior.
- [ ] T046 Update `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md` with diagnostics for invalid Mermaid, unsupported dialect, unsupported C4 syntax, renderer configuration failure, version incompatibility, and runtime rendering failure. Document missing artifact only as an upstream boundary condition from the previous pipeline issue; do not reimplement generation or discovery here.
- [ ] T047 [P] Update `docs/summary-validator-guide.md` with troubleshooting for `Syntax error in text mermaid version 11.14.0`, including how to inspect renderer source/version, C4 capability, exact error, and compatibility reports.
- [ ] T048 [P] Update `docs/summary-io-map.md` with the JSON/Markdown report paths, source-hash checkpoints, and publication-gate decision flow.

## Dependencies and Execution Order

- [x] T049 [P] Add contract-alignment tests in `tests/summary/test_blueprint_report_contract.py` asserting that public JSON and Markdown use camelCase fields and never expose `artifact_path`, `mermaid_version`, `classification`, or `trace_id`.
- [x] T050 Implement deterministic runtime version extraction in `src/modules/ava-fabric-agents/summary/utils/render_blueprint_compatibility.py` by loading the exact Summary bundle/configuration and reading `mermaid.version` or an equivalent runtime API; unreadable version must return `RENDERER_CONFIGURATION_FAILURE` at `RUNTIME_VERSION_PROBE` and mismatch must return `MERMAID_VERSION_INCOMPATIBILITY`.
- [ ] T051 [P] Add runtime-version tests in `tests/summary/test_renderer_version_probe.py` for successful extraction, unreadable version, and baseline mismatch using the actual Summary bundle rather than filename or package metadata.
- [ ] T052 Add producer provenance resolution in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py` for `producingAgent`, `producingAgentRole`, `sourceContractPath`, `artifactContractPath`, and `generationPhase`, using metadata first and the documented AS-IS/TO-BE mapping with `confidence: MEDIUM` when metadata is absent.
- [ ] T053 [P] Add provenance tests in `tests/summary/test_blueprint_provenance.py` covering metadata-derived producer identity and documented fallback mappings for `ava-asis-solution-delphi` and `ava-tobe-architecture-design`.
- [ ] T054 Add C4 capability matrix fixtures in `tests/summary/fixtures/c4-capability/` for native support, plugin/extension required but unavailable, support disabled by initialization, unsupported keyword, malformed construct, runtime initialization failure, and version mismatch; each fixture must map to the canonical `rootCause` and `stage` values.
- [ ] T055 Implement the ordered fail-closed pipeline in `src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py`: read artifact, hash raw source, detect dialect/constructs, probe version, probe C4, static validate, call `mermaid.render()`, hash renderer input, compare integrity, generate JSON, generate Markdown, evaluate publication, and only then write/promote Summary HTML.
- [ ] T056 Add publication-order tests in `tests/summary/test_blueprint_publication_order.py` proving that `publicationAllowed: false` prevents client-facing HTML write/promotion while allowing clearly marked diagnostic/test artifacts.
- [ ] T057 [P] Update `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` and `docs/summary-validator-guide.md` to document the camelCase public contract, runtime version probe, C4 capability matrix, producer provenance, complete hash object, and fail-closed publication ordering.

```text
T001-T004  → context and public contract diagnostics
T005-T009  → renderer source-of-truth
T010-T016  → dialect/static validation
T017-T022  → dynamic runtime validation
T023-T031  → integrity, report, no-conversion, and publication gate
T032-T043  → complete fixture matrix and actual Sophia regression
T044-T048  → documentation
T049-T057 → clarification hardening: contract, runtime probe, provenance, C4 matrix, ordering, and documentation
```

- The MVP is `T001-T002`, `T005-T007`, `T010-T013`, `T016-T021`, `T026`, `T029`, `T042`, `T050`, and `T055`.
- `T008-T009`, `T015-T016`, `T022`, and `T032-T040` can be developed in parallel after the renderer contract is established.
- `T023-T025` can proceed in parallel with runtime fixture work after the Summary call path is confirmed.
- `T044-T048` should be finalized after the compatibility classifications and report fields are stable.

## Implementation Strategy

1. **MVP first**: prove the actual renderer/version, classify C4, execute `mermaid.render()` against Sophia, produce the report, and block publication on failure.
2. **Incremental hardening**: add static grammar checks, hash checkpoints, no-conversion enforcement, complete failure fixtures, and UI smoke coverage.
3. **Fail closed**: missing, divergent, unsupported, or inconclusive evidence blocks publication; only an SVG render from the Summary runtime with matching source integrity allows publication.
4. **No unrelated remediation**: do not rework artifact generation, discovery, injection, or orchestration unless a test requires those paths to provide compatibility evidence.

## Completion Criteria

- [ ] All tasks follow the required checklist format with sequential IDs and explicit file paths.
- [ ] Renderer source, effective version, C4 support, and configuration are reported from the Summary runtime.
- [ ] The Sophia `C4Container` case is a regression fixture and receives an explicit root-cause classification.
- [ ] JSON and Markdown compatibility reports are generated and schema-valid.
- [ ] Publication is blocked for every non-renderable required Blueprint.
- [ ] Summary smoke tests prove no visible Mermaid error or undiagnosed raw-source fallback is published.
- [ ] Documentation distinguishes missing artifact, invalid Mermaid, unsupported dialect/C4, renderer configuration, version incompatibility, and rendering failure.
