# Implementation Plan: Full-Quality Portuguese (PT-BR) Manual View Support

**Branch**: `038-portuguese-manual-view` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/038-portuguese-manual-view/spec.md`

## Summary

Extend the existing Summary language boundary so the manually selected Portuguese view is deterministically normalized to coherent PT-BR while English remains the unchanged default. Preserve technical/protected values byte-for-byte, keep the selector and both dictionaries functional, add explicit target-aware PT validation with error-level blocking semantics, and integrate targeted PT remediation through the official builder/template/validator path.

## Technical Context

**Language/Version**: Python used by existing Summary utilities; HTML/JavaScript in the self-contained Summary template; versions and runtime behavior remain repository-configured.
**Primary Dependencies**: Existing `summary_language.py`, `build_summary_comprehensive.py`, `validate_summary.py`, `remediate_summary.py`, `summary-template.html`, Summary workflow/agent contracts, and pytest-based Summary tests. No remote translation dependency.
**Storage**: Existing project outputs under `projects/{project_name}/outputs/summary/`; read-only source artifacts under project outputs/context; feature design artifacts under `specs/038-portuguese-manual-view/`.
**Testing**: `python -m pytest tests/summary`, focused unit tests for target-aware normalization/protected values, template/selector regression tests, validator gate tests, and remediation integration tests. All end-to-end validation uses the isolated fixture created by the explicit Fixture-First task below; real projects such as `sophia` and `MeuERP-002` are not required for feature acceptance.
**Target Platform**: Windows-compatible repository tooling and offline/file-based Summary HTML generation.
**Project Type**: Repository-based agent pipeline with Python generation/validation/remediation utilities and a self-contained HTML report.
**Performance Goals**: Preserve current generation and remediation behavior; target-aware normalization and validation must be deterministic and bounded by already processed generated/source-derived content, with no network calls.

**Constraints**:

- English remains the default generated/rendered state exactly as established by feature 037.
- PT validation is invoked only when explicitly targeted; when targeted, unresolved/unsafe findings are error-level and block exactly like English C8.
- A targeted PT remediation run must leave `errors_after > 0`, return nonzero, and avoid a success claim when PT findings remain.
- Source artifacts remain read-only and protected technical values remain byte-for-byte identical.
- Existing output paths, filenames, JSON/report shapes, selector interaction, `setLang()`, i18n dictionaries, traceability metadata, and non-language checks remain compatible.
- No remote/LLM translation, new language, layout redesign, Mermaid redesign, or unrelated F1-F7 changes.

**Scale/Scope**: All supported Summary generation modes and Summary-Remediation runs, all human-readable Summary sections, Architectural Patterns, HTML/manual switching, generated Markdown/reports, embedded generated data, explicit PT validation, and targeted remediation.

## Canonical Contract

The **Language Compliance Result** uses the canonical schema at `specs/037-enforce-english-summary/contracts/language-compliance.schema.json`. The canonical schema will be extended in T018 to add a required `target` field constrained to `en` or `pt`. Until T018 is complete, the schema does not yet include this field.

There is exactly one authoritative schema file. `validate_summary.py` must load the extended schema from the 037 path at runtime after T018. No independently maintained schema is created under feature 038; the feature-local contract copy is removed by T018 and must not be consumed by the validator.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Gate                                          | Status | Evidence / plan                                                                                                                                |
| --------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Configuration-driven (Article I)              | PASS   | No technology version, cloud region, or environment choice is introduced. Language target is an explicit feature input.                        |
| Agent contract standard (Article II)          | PASS   | Existing agent IDs and output paths remain. New language-target behavior is optional and documented.                                           |
| Pipeline execution contract (Article III)     | PASS   | The official Summary builder remains the only HTML producer; validator remains the quality gate; remediation reuses the official rebuild path. |
| Module registration (Article IV)              | PASS   | No new agent/module is introduced; existing Summary registration is preserved.                                                                 |
| Language convention (Article V)               | PASS   | Agent/workflow instructions remain pt-BR; generated client-facing PT-BR quality is handled separately.                                         |
| Test-first behavior (Article VI)              | PASS   | Nominal, edge, protected-value, explicit PT gate, default-English regression, and remediation scenarios are specified.                         |
| Security-first (Article VII)                  | N/A    | No F1 security pipeline behavior changes; security identifiers are protected.                                                                  |
| Observability and traceability (Article VIII) | PASS   | `trace_id`, exact references, report structures, and structured validation behavior are preserved.                                             |
| Clean Architecture alignment (Article IX)     | N/A    | This is a Summary utility/template/validator change, not generated application code.                                                           |
| Versioning (Article X)                        | PASS   | Existing Summary and Summary-Remediation agents receive the repository-appropriate non-breaking increment.                                     |
| Skill/Agent separation (Article XI)           | PASS   | Existing SKILL.md routing remains; behavior changes belong in agent bodies, workflows, and utilities.                                          |

**Gate result**: PASS. No constitutional violation requires a complexity exception.

## Research Summary

- `summary_language.py` is the existing offline deterministic normalization boundary and will be extended rather than replaced.
- The template already preserves `var lang = "en"`, PT/EN dictionaries, selector markup, and `setLang()`; these remain interaction contracts.
- `validate_summary.py` already has blocking C8 checks and compatible `Check`/JSON/report structures.
- `remediate_summary.py` already computes `errors_before`, `errors_after`, remaining checks, reports, and exit status; explicit PT findings must use the same error-level path.
- The full research record is in [research.md](research.md); the target data model is in [data-model.md](data-model.md).

## Proposed Implementation Approach

### Fixture-First — Isolated end-to-end test project (must precede Phases A–E)

- Create a minimal, self-contained fixture project dedicated to feature 038 before changing the language utility, builder, validator, or remediation flow.
- Include a complete valid `project-config.yaml` and `shared-context.md`, plus the minimum source/output structure required by the Summary builder and validator.
- Include `patterns-applied.json` with 2–3 entries using the exact fields consumed by the builder: `pattern_name`, `layer`, `justification`, `reference_artifact`, `trade_offs`, and `adr_reference`; cover English, Portuguese, and mixed-language prose plus protected values.
- Include a valid, resolvable Mermaid input required by the Summary path, or explicitly bypass that dependency through the fixture configuration, so unrelated Mermaid placeholder failures cannot block feature tests.
- Reuse this fixture for every Phase A–E test and validation scenario. Do not use `sophia` or `MeuERP-002` as the required end-to-end acceptance fixture because their pre-existing defects are outside feature 038.

### Phase A — Target-aware language model

- Extend the Summary-local utility with `language_target` (`en` or explicit `pt`), deterministic PT-BR mappings, field-aware protected-value handling, and residual unsafe/non-target diagnostics.
- Keep existing English behavior and default signatures compatible.
- Cover Architectural Patterns and equivalent source-derived free-text fields.

### Phase B — Render and data integration

- Route human-readable builder substitutions and fallbacks through target-aware normalization or language-specific render values.
- Keep selector markup, `setLang()`, `I18N.pt`, `I18N.en`, `var lang = "en"`, output paths, JSON shape, trace IDs, references, and escaping behavior intact.

### Phase C — Explicit PT compliance gate

- Add an explicit `--language-target pt` validation path; omission retains English C8 behavior.
- Register targeted PT findings as error-level blocking checks. Diagnostics identify target, artifact/region, and evidence while excluding protected and machine-readable values.

### Phase D — Targeted remediation

- Add the same optional language-target argument to remediation and pass it through official builder/validator execution.
- For explicit PT runs, unresolved findings must make `errors_after > 0`, produce no success claim, and return nonzero.

### Phase E — Regression tests

- Add focused tests for PT normalization, mixed-language residual detection, protected values, determinism, template switching, explicit PT validation, default English regression, and targeted remediation failure semantics, all reusing the isolated fixture.

## Artifact Impact

| Area               | Expected files/components                                                         | Purpose                                                                              |
| ------------------ | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| Language utility   | `src/modules/ava-fabric-agents/summary/utils/summary_language.py`                 | Target-aware deterministic PT-BR normalization and protected-value diagnostics.      |
| Builder/template   | `build_summary_comprehensive.py`; `templates/html/summary-template.html`          | Localize dynamic prose while preserving English default and selector behavior.       |
| Validator          | `validate_summary.py`                                                             | Explicit PT gate with C8-equivalent error-level blocking.                            |
| Remediation        | `remediate_summary.py`                                                            | Thread PT target, preserve official rebuild, enforce `errors_after` and exit status. |
| Contracts/docs     | Existing Summary agents and workflow steps                                        | Document optional PT target without changing pt-BR instruction convention.           |
| Tests              | `tests/summary/` focused language and remediation tests plus the isolated fixture | Verify feature and regressions without reliance on unrelated real-project defects.   |
| Canonical contract | `specs/037-enforce-english-summary/contracts/language-compliance.schema.json`     | Extend the existing schema in T018 with required serialized `target: en              | pt`; this is the only schema loaded by `validate_summary.py`. |

No unrelated F1-F7 agent or source-repository files are in scope.

## Validation Strategy

1. Create and validate the isolated feature-038 fixture before implementation phases begin; confirm its config, shared context, exact `patterns-applied.json` fields, and Mermaid path are valid.
2. Run existing Summary tests and structural checks using the isolated fixture rather than relying on `sophia` or `MeuERP-002`.
3. Generate the fixture with English, Portuguese, and mixed source prose and inspect default English plus manual PT-BR views.
4. Verify Architectural Patterns and representative free-text sections, protected values, selector behavior, and English restoration.
5. Run omitted-target validation and confirm English C8 is unchanged.
6. Run explicit PT validation against compliant and deliberately non-compliant fixture data; confirm serialized `target: pt`, error-level blocking, diagnostics, and the canonical 037 schema.
7. Run targeted PT remediation on the fixture; confirm official rebuild, `errors_after > 0`, nonzero exit, and no success claim for unresolved findings.
8. Verify output paths, filenames, JSON/report shape, trace IDs, source hashes, determinism, and all existing non-language checks.

## Risks and Mitigations

| Risk                                            | Mitigation                                                                            |
| ----------------------------------------------- | ------------------------------------------------------------------------------------- |
| PT normalization corrupts technical identifiers | Field-aware masking and byte-for-byte protected-value tests.                          |
| Detector false positives                        | Scan prose regions and exclude protected/machine-readable values.                     |
| PT gate becomes warning-only                    | Use `level="error"`; assert `errors_after > 0`, nonzero exit, and no success message. |
| English default regresses                       | Keep omitted-target path and `var lang = "en"` tests.                                 |
| Builder/remediation divergence                  | Use official builder and shared validator.                                            |
| Source mutation                                 | Read-only input discipline and source hash tests.                                     |
| Nondeterministic translation                    | Local deterministic mappings only; unresolved content blocks targeted compliance.     |

## Definition of Done

- English remains the unchanged default.
- Manual PT selection provides complete, coherent PT-BR for safely normalizable generated content.
- Protected technical values remain byte-for-byte identical.
- Explicit PT validation is deterministic, diagnostic, error-level, and blocking.
- Targeted PT remediation leaves `errors_after > 0`, exits nonzero, and never reports success when PT errors remain.
- Selector, `setLang()`, dictionaries, contracts, traceability, source immutability, and existing checks remain compatible.

## Project Structure

```text
specs/038-portuguese-manual-view/
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
└── plan.md

# Canonical language contract (extended in place by T018):
specs/037-enforce-english-summary/contracts/language-compliance.schema.json

src/modules/ava-fabric-agents/summary/
├── agents/
├── workflows/generate-summary/
├── templates/html/summary-template.html
└── utils/{summary_language,build_summary_comprehensive,validate_summary,remediate_summary}.py

tests/summary/
└── focused PT normalization, validation, selector, remediation tests, and isolated fixture
```

**Structure Decision**: Modify the existing Summary module in place. No new agent or module is introduced, no output contract path changes, and no second language-compliance schema is maintained.

## Complexity Tracking

No constitutional violations. No complexity exception is required.
