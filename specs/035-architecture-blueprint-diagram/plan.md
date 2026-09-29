# Implementation Plan: Architecture Blueprint Diagram Generation

**Branch**: `035-architecture-blueprint-diagram` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)

## Summary

The repository already defines the Architecture Blueprint owners and Mermaid paths, but the lifecycle is not enforced end-to-end. AS-IS Delphi architecture is owned by `ava-asis-solution-delphi` and writes `projects/{project_name}/outputs/asis/diagrams/architecture-blueprint.mmd`. TO-BE architecture is owned by `ava-tobe-architecture-design`, dispatched by `ava-tobe-orchestrator` through trigger `CB`, and writes `projects/{project_name}/outputs/tobe/diagrams/architecture-blueprint.mmd` alongside `tobe/docs/architecture-blueprint.md` and the companion HTML. The Summary renderer consumes AS-IS through `D.staticDiagrams.asisArchBlueprint` and TO-BE through `D.staticDiagrams.tobeArchBlueprint`, populated by `build_summary_comprehensive.py` and rendered by `renderAllDiagrams()`/`renderStaticDiagrams()`.

The failure is a contract/lifecycle gap rather than one single confirmed root cause: the current pipeline permits a missing or empty source to flow into the template, where `renderAllDiagrams()` replaces it with `(diagrama não disponível — execute o agente correspondente)`. Existing contracts also contain inconsistent fallback behavior, including a TO-BE orchestrator instruction that allows a placeholder artifact. This plan makes ownership, artifact registration, discovery, generation, rendering, and publication status explicit and blocks publication for missing or unrenderable required diagrams.

## Technical Context

| Dimension                | Decision                                                                                                                              | Evidence                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Implementation language  | Python utilities plus Markdown agent/workflow instructions                                                                            | Existing Summary builder, diagram gate, and agent specs          |
| AS-IS owner              | `ava-asis-solution-delphi` for Delphi; technology-specific sibling solution agent for other supported legacy stacks                   | `solution-delphi.md`, AS-IS module registry                      |
| TO-BE owner              | `ava-tobe-architecture-design`, dispatched by `ava-tobe-orchestrator` trigger `CB`                                                    | `orchestrator-tobe.md` and `architecture-design-tobe.md`         |
| AS-IS artifact           | `projects/{project_name}/outputs/asis/diagrams/architecture-blueprint.mmd` plus `asis/architecture-blueprint.md` evidence             | AS-IS agent output sections and module output list               |
| TO-BE artifacts          | `projects/{project_name}/outputs/tobe/diagrams/architecture-blueprint.mmd`, `tobe/docs/architecture-blueprint.md`, and companion HTML | TO-BE CB output contract                                         |
| Summary source injection | `build_summary_comprehensive.py` → `D.staticDiagrams.asisArchBlueprint` / `tobeArchBlueprint`                                         | `collect_static_diagrams()` and placeholder substitutions        |
| Browser renderer         | `renderAllDiagrams()` populates `<pre class="mermaid">`; `renderStaticDiagrams()` calls Mermaid rendering per node                    | `summary-template.html`                                          |
| Pre-write validation     | Existing `src/shared/utils/validate_diagram.py` is the single `.mmd` write gate                                                       | AS-IS and TO-BE agent guardrails                                 |
| Quality report           | New canonical Blueprint quality JSON plus Markdown projection, integrated with existing validation/publication checks                 | Feature specification and `blueprint-quality-report.schema.json` |
| Testing                  | Focused unit/integration tests plus existing Mermaid/Summary regression suites                                                        | Repository test layout and quickstart                            |
| Storage                  | Preserve existing AS-IS/TO-BE output contracts; quality reports belong with Summary validation artifacts                              | Existing output conventions                                      |
| Configuration            | Resolve project and stack from `project-config.yaml`; do not hardcode technology versions or project names                            | Constitution Article I                                           |
| Traceability             | Preserve `trace_id` without mutation across agent, artifact record, report, and Summary                                               | Constitution Article VIII                                        |
| Scope                    | Architecture Blueprint source lifecycle and rendering/publication gate only                                                           | Feature spec                                                     |

## Failure classification from current implementation

| Failure class                 | Current evidence                                                                                                                                                  | Required handling                                                                                             |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Missing agent execution       | Agent status is inferred from output presence in Summary; TO-BE orchestration has explicit CB ownership but no unified Blueprint lifecycle record                 | Record `AGENT_NOT_EXECUTED` using orchestration/shared-context evidence; block required publication           |
| Missing artifact generation   | AS-IS/TO-BE contracts require `.mmd`, but the renderer receives empty content when the source is absent; TO-BE text currently permits a placeholder fallback      | Record `GENERATION_FAILED` or `MISSING_ARTIFACT`; never create/accept placeholder architecture evidence       |
| Missing artifact registration | AS-IS module and Summary maps cover paths, but TO-BE consumers and Summary mappings are distributed across multiple files and include inconsistent document paths | Reconcile all registries/maps against canonical phase-specific contracts and add automated consistency checks |
| Artifact discovery failure    | Builder reads exact paths and `collect_static_diagrams()` drops empty keys; alternate valid paths are not surfaced as a distinct diagnostic                       | Record expected versus discovered path and `DISCOVERY_FAILED`/`UNREGISTERED` when applicable                  |
| Renderer integration failure  | Template fallback intentionally converts empty diagram data into the localized unavailable-diagram text; renderer catches errors and leaves code view             | Preserve source evidence, record `RENDERING_FAILED`, and block publication for required diagrams              |
| Orchestration failure         | CB has retry/checklist behavior but allows placeholder creation and does not emit a shared generation/rendering status contract                                   | Replace placeholder fallback with explicit failed gate, retry result, and structured status handoff           |

## Constitution Check

_Gate: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] Article I — Configuration-driven: no project, stack, or version is hardcoded in the plan or proposed agent behavior.
- [x] Article II — Existing agent frontmatter and output contracts remain authoritative; no new user-facing agent is required.
- [x] Article III — Existing phase order and Summary integration are preserved; the gate is added at owning generation/publication boundaries.
- [x] Article IV — No new module is required; existing AS-IS, TO-BE, Summary, and shared utility registries will be updated only where contract consistency requires it.
- [x] Article V — Any changed agent body/workflow instructions will be written in Brazilian Portuguese; machine contracts may remain English.
- [x] Article VI — Nominal, missing-input, missing-execution, generation-failure, rendering-failure, and publication-gate scenarios are defined in `spec.md`.
- [x] Article VII — No F1 security pipeline is bypassed; quality metadata must preserve secret masking.
- [x] Article VIII — Mermaid validation and unchanged trace propagation are explicit.
- [x] Article IX — No application-layer code is changed; shared validation remains isolated from domain code.
- [x] Article X — Existing agent behavior/output paths are preserved; affected agent instructions receive a PATCH bump unless implementation reveals an output-contract change requiring a higher bump.
- [x] Article XI — No new skill is needed; behavior changes belong to existing agent bodies and shared utilities.

**Gate decision**: **PROCEED**.

## Project Structure

### Documentation

```text
specs/035-architecture-blueprint-diagram/
├── spec.md
├── research.md
├── data-model.md
├── contracts/
│   └── blueprint-quality-report.schema.json
├── quickstart.md
└── plan.md
```

### Implementation areas

```text
src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md
src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-design-tobe.md
src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py
src/modules/ava-fabric-agents/summary/utils/validate_summary.py
src/modules/ava-fabric-agents/summary/templates/html/summary-template.html
src/modules/ava-fabric-agents/summary/data/artifact-map.yaml
src/shared/utils/validate_diagram.py
src/shared/checks/suites/mermaid_files.py

tests/unit/
tests/integration/
tests/fixtures/mermaid/
```

**Structure Decision**: Keep architecture ownership in the existing AS-IS/TO-BE agents. Add lifecycle validation and reporting in shared/summary utilities, then update the existing orchestration and renderer contracts. Do not add a competing architecture generator.

## Phase 0 — Research Findings

Research is recorded in `research.md`. Key decisions:

1. Preserve separate AS-IS and TO-BE owners and paths.
2. Treat the canonical `.mmd` source as the only valid rendering input.
3. Replace placeholder artifact fallback with a blocking, categorized gate.
4. Keep document and diagram artifacts separate but cross-linked.
5. Report generation and rendering independently.

## Phase 1 — Design

### Lifecycle algorithm

1. Resolve the architecture scope (`ASIS` or `TOBE`) and canonical owner from the existing phase contract.
2. Resolve the expected `.mmd` path and companion document path.
3. Inspect orchestration/shared-context evidence for responsible-agent execution.
4. Discover the exact expected artifact; record alternate candidates without silently substituting them.
5. Validate presence, non-empty content, absence of unresolved placeholders, and Mermaid validity through the existing write/validation gate.
6. Populate the Summary diagram data only from the validated artifact.
7. Render the populated diagram independently and record renderer success/failure.
8. Emit the canonical quality report with separate statuses and findings.
9. Block publication for missing, invalid, or unrenderable required Blueprint artifacts.

### Renderer behavior

- `build_summary_comprehensive.py` remains the source adapter and must provide explicit Blueprint source/status metadata.
- `renderAllDiagrams()` remains the DOM source population step.
- `renderStaticDiagrams()` remains the Mermaid rendering step.
- The unavailable-diagram text is allowed only for an explicitly non-required section with a `MISSING_INPUT`/`PENDING` quality record; it must not be emitted for a required Blueprint when architecture inputs are sufficient.
- Rendering exceptions must be classified as `RENDERING_FAILED`, not converted into a generic missing-diagram state.

### Quality report fields

The implementation must produce the fields in `data-model.md` and validate them against `contracts/blueprint-quality-report.schema.json`, including:

- expected artifact path;
- actual discovered path or null;
- generating agent;
- agent execution status;
- generation status;
- artifact status;
- rendering status;
- gate status;
- categorized findings and remediation;
- project and unchanged trace ID.

### Contract reconciliation

- Keep `asis/diagrams/architecture-blueprint.mmd` as AS-IS canonical source.
- Keep `tobe/diagrams/architecture-blueprint.mmd` as TO-BE canonical source.
- Keep `asis/architecture-blueprint.md` and `tobe/docs/architecture-blueprint.md` as companion evidence documents.
- Remove the TO-BE instruction that creates a placeholder `.mmd` after CB failure; replace it with a blocking retry/gate result.
- Ensure Summary artifact maps and status maps identify the responsible agent and exact `.mmd` source for both scopes.

## Implementation Workstreams

1. **Ownership and contract reconciliation** — update AS-IS/TO-BE agent and orchestrator instructions, module output maps, and Summary artifact maps.
2. **Artifact lifecycle validator** — implement deterministic Blueprint discovery/status classification and canonical JSON/Markdown report generation.
3. **Generation gate integration** — require the responsible agent's `.mmd` output to pass the existing diagram write/validation gate; prohibit placeholder artifacts.
4. **Summary adapter integration** — inject validated Blueprint source and lifecycle metadata into `D.staticDiagrams`/Summary data without hardcoded diagrams.
5. **Renderer diagnostics** — preserve source and emit a distinct rendering failure status when Mermaid rendering fails.
6. **Publication gate** — block publication on missing/invalid/unrenderable required Blueprint artifacts; expose findings to existing quality validation.
7. **Testing and fixtures** — add nominal, missing execution, missing artifact, invalid generation, renderer failure, alternate-path, and placeholder regression fixtures.
8. **Documentation and versioning** — update affected agent instructions in pt-BR, changelog only if contract/version impact requires it, and keep trace/security conventions.

## Test Strategy

- Unit tests for lifecycle classification, canonical path resolution, placeholder detection, report schema, and status aggregation.
- Integration tests for AS-IS and TO-BE builder injection, `renderAllDiagrams()` mapping, and `renderStaticDiagrams()` failure isolation.
- Gate tests proving missing artifact and render failure return non-zero publication status.
- Regression tests proving valid artifacts render and the localized placeholder is absent from successful Blueprint sections.
- Existing Mermaid validation and Summary unified checks remain mandatory.

## Complexity Tracking

| Complexity                                                         | Justification                                                                          | Simpler alternative rejected because                                              |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Two phase-specific lifecycle records                               | AS-IS and TO-BE have different owners, inputs, and canonical paths                     | One global producer would violate phase ownership and risk cross-phase overwrites |
| Separate generation and rendering statuses                         | A valid source can fail in the renderer, while an invalid source is a generation issue | One boolean cannot provide actionable remediation or satisfy acceptance criteria  |
| Structured report plus Markdown projection                         | Publication gates need machine-readable status; reviewers need readable evidence       | Markdown-only parsing is fragile and prevents reliable downstream gating          |
| Existing renderer fallback retained only for non-required sections | Partial summaries still need honest absence reporting                                  | Removing all fallback text would obscure legitimate incomplete phases             |

## Post-Design Constitution Re-Check

- [x] Configuration-driven owner/path resolution retained.
- [x] Existing agent and skill separation retained; no new user-facing agent introduced.
- [x] Existing output paths preserved.
- [x] Mermaid write gate, sanitization, trace propagation, and security masking retained.
- [x] BDD scenarios cover nominal, edge, failure classification, and publication gate behavior.
- [x] Summary remains a consumer and does not invent architecture.
- [x] No unresolved `NEEDS CLARIFICATION` items remain.

**Post-design decision**: **PASS — ready for `/speckit.tasks`**.
