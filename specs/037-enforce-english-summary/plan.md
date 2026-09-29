# Implementation Plan: Enforce English-Default Summary Output

**Branch**: `037-enforce-english-summary` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/037-enforce-english-summary/spec.md`

## Summary

Fix the existing F8 Summary and Summary-Remediation pipelines so that their generated artifacts open/render in English by default. The existing PT/EN selector, `setLang()` behavior, and both i18n dictionaries remain functional for manual viewing. The implementation will normalize default-view human-readable source-derived values, preserve exact technical and traceability values, and add a deterministic validation check for the initial English state. Remediation will reuse the same builder and validator so legacy mixed-language default views are repaired or explicitly blocked.

## Technical Context

**Language/Version**: Python used by existing Summary utilities; HTML/JavaScript in the existing Summary template; versions resolved from repository configuration and existing project files.

**Primary Dependencies**: Existing `build_summary_comprehensive.py`, `remediate_summary.py`, `validate_summary.py`, Summary HTML template/i18n code, existing test framework and fixtures. No new remote translation service is planned.

**Storage**: Existing project output files under `projects/{project_name}/outputs/summary/`; read-only source artifacts under the project outputs and context directories.

**Testing**: Existing repository test configuration plus focused Summary builder/template/validator/remediation regression tests. Exact command to be confirmed during implementation task discovery.

**Target Platform**: Windows-compatible repository tooling and offline/file-based Summary HTML generation.

**Project Type**: Repository-based agent pipeline with Python build/validation utilities and a self-contained HTML report.

**Performance Goals**: Preserve existing Summary and remediation execution behavior; language normalization and validation must be deterministic and bounded by the already processed generated content.

**Constraints**:

- Scope is limited to `ava-summary`, `ava-summary-remediation`, and Summary-specific supporting code/assets.
- Source artifacts remain read-only and unchanged.
- Existing output paths, filenames, traceability metadata, artifact contracts, structural checks, and non-language quality checks remain compatible.
- English is the default generated/rendered output language. The existing user-selectable PT/EN mode remains supported; no additional languages or new multilingual capability is added.
- Technical identifiers, code symbols, paths, URLs, project names, acronyms, ADR filenames, Markdown references, proper nouns, and exact traceability references must be preserved.
- No layout redesign, Mermaid fix, navigation redesign, or unrelated F1-F7 changes.

**Scale/Scope**: All Summary generation modes (`GS`, `SAS`, `STO`, `SI`, and supported update/validation paths) plus Summary-Remediation rebuilds, all Summary sections, Markdown outputs, HTML outputs, and remediation reports.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Gate                                          | Status | Evidence / plan                                                                                                                                                                                                                                  |
| --------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Configuration-driven (Article I)              | PASS   | No technology version or environment value is introduced. Existing configuration and project data remain authoritative. The fixed English policy is a feature requirement, not a technology choice.                                              |
| Agent contract standard (Article II)          | PASS   | Existing agent IDs and output paths are preserved; only behavior and PATCH versions change. Validation metadata remains compatible with existing reports/contracts.                                                                              |
| Pipeline execution contract (Article III)     | PASS   | The plan changes only Summary generation and validation behavior. The official builder remains the sole HTML producer and Summary validator remains the quality gate.                                                                            |
| Module registration (Article IV)              | PASS   | Existing `summary/module.yaml` entries remain; no new agent/module is planned. Verify version references if required by repository registry tests.                                                                                               |
| Language convention (Article V)               | PASS   | Agent instruction bodies and workflow documentation remain in the repository-required Brazilian Portuguese convention. The feature's generated client-facing default state is English; the existing optional Portuguese view remains functional. |
| Test-first behavior (Article VI)              | PASS   | The existing agents are modified with nominal, edge, quality-gate, pattern, and remediation scenarios from `spec.md`; focused tests will be added.                                                                                               |
| Security-first (Article VII)                  | PASS   | No F1 security behavior is changed. Existing security findings and technical identifiers are preserved as data; no security sub-pipeline bypass is introduced.                                                                                   |
| Observability and traceability (Article VIII) | PASS   | `trace_id` and exact traceability references remain unchanged; no stdout protocol or observability contract is removed.                                                                                                                          |
| Clean Architecture alignment (Article IX)     | N/A    | This is a Summary builder/template/validator bugfix, not generated application code.                                                                                                                                                             |
| Versioning (Article X)                        | PASS   | Existing `ava-summary` and `ava-summary-remediation` agent versions receive PATCH bumps because behavior is corrected without changing required inputs/outputs.                                                                                  |
| Skill/Agent separation (Article XI)           | PASS   | Existing SKILL.md routing remains; behavior changes belong in agent bodies and Summary utilities/templates.                                                                                                                                      |

**Gate result**: PASS. No constitutional violation requires a complexity exception.

## Current Behavior Analysis

1. `summary-agent.md` currently permits `language: "pt" | "en"`, defaults to Portuguese, and describes bilingual Executive Summary generation; the default must change to English without removing the selector capability.
2. `step-03-build-html.md` explicitly instructs generation of PT and EN Executive Summary data.
3. `summary-template.html` contains an intentional language selector, Portuguese defaults, Portuguese section labels/table headers, and PT/EN i18n content. The defect is the initial/default branch and labels, not the existence of the selector.
4. `build_summary_comprehensive.py` directly interpolates source-derived pattern fields into `TOBE_PATTERNS_ROWS`, emits Portuguese fallback strings and labels, and contains Portuguese hardcoded values in substitutions and generated report text.
5. `validate_summary.py` has a conditional C8 language check that skips when language is not `en`; C8.3 requires both PT and EN i18n keys, which is incompatible with the new single-language artifact invariant.
6. `remediate_summary.py` rebuilds through the official builder and calls the existing validator before and after rebuild, so it can enforce the invariant without a separate rebuild path.

### Data classification

- **Generated labels/templates**: normalize directly in agent instructions, workflow text that drives output, template text, i18n mappings, and builder fallback strings.
- **Source-derived human-readable prose**: pass through deterministic English normalization before HTML/Markdown/report rendering.
- **Protected values**: paths, URLs, code symbols, identifiers, class/method names, project names, acronyms, ADR filenames, Markdown references, proper nouns, and exact traceability references remain exact and are excluded from false-positive language detection.

## Clarification: Default English State and Existing Language Selector

The existing Portuguese/English selector, `setLang()` behavior, and PT/EN i18n dictionaries are intentional and remain in scope as a supported manual viewing capability. The implementation must not remove or disable them. English is enforced only for the initial/default rendered state and for generated Markdown/report content that has no interactive language view. A Portuguese view reached solely through manual selector interaction is outside the English-default compliance gate.

## Proposed Implementation Approach

### Phase A — Align agent/workflow contracts

- Update `summary-agent.md` to make English the default generated/rendered language, retain the existing PT/EN selector capability, remove only the conflicting bilingual-generation requirement for the default state, and specify protected-value preservation and default-view validation behavior.
- Update `summary-remediation-agent.md` to require English-default rebuilds/reports, repair legacy mixed-language default content through the official builder, preserve selector/i18n behavior, and treat residual default-view language findings as blocking.
- Update `step-02-extract.md`, `step-03-build-html.md`, `step-04-validate-deliver.md`, and workflow configuration where applicable so they define the English initial state while preserving manual Portuguese switching.
- Keep agent instruction bodies in the repository-required Brazilian Portuguese convention where applicable; the generated-output policy applies to produced artifacts, not agent instruction language.

### Phase B — Normalize template labels and rendering defaults

- Audit `summary-template.html` as the canonical HTML source for visible labels, headings, table headers, empty states, status labels, navigation labels, and i18n values.
- Ensure the initial/default branch uses complete English labels while preserving the existing selector UI, `setLang()` behavior, PT dictionary, and EN dictionary.
- Do not remove or disable the existing Portuguese rendering path; the compliance check applies only to the initial/default English view.
- Ensure fallback labels for missing data, phase-not-run, pending, approval, report status, and remediation status are English.
- Do not translate protected technical identifiers or exact references.

### Phase C — Normalize builder and report content

- Add a Summary-local deterministic normalization/classification boundary in `build_summary_comprehensive.py` or a directly scoped Summary utility.
- Normalize generated fallback strings, `index.md` text, builder status/narrative strings, and report-facing labels to English.
- Apply the boundary to source-derived human-readable fields in the default English view, prioritizing Architectural Patterns (`pattern_name`, `layer`, `justification`, `trade_offs`) and then the other generated tables/narrative sections listed in the specification. The existing Portuguese view is not required to normalize these source-derived fields.
- Preserve `reference_artifact`, `adr_reference`, code symbols, paths, URLs, project names, acronyms, proper nouns, and exact traceability references.
- Escape and serialize normalized values using existing HTML/JSON/Markdown safety behavior; do not alter artifact paths or `trace_id`.
- Surface unresolved unsafe prose to validation rather than silently emitting it as valid English.

### Phase D — Enforce the validator gate

- Extend `validate_summary.py` with a deterministic check for the default rendered/generated English state of HTML/Markdown/report content.
- Inspect visible/generated text and embedded generated prose while ignoring protected technical values, machine-readable values, and non-prose identifiers where exact preservation is required.
- Replace conditional C8 behavior with an unconditional check of the default English state, regardless of configured default-language metadata; retain validation that both PT and EN i18n dictionaries and selector behavior exist. Do not apply the gate to a Portuguese view reached only through manual selector interaction.
- Add diagnostics identifying artifact, default-view region, and offending text; fail/block rather than report valid output when residual Portuguese or unsafe non-English generated prose remains in the default state.
- Keep all existing structural, placeholder, traceability, artifact-integrity, Mermaid, and content-completeness checks active.
- Keep validator output compatible with existing `Check`, JSON report, and remediation failure accounting structures.

### Phase E — Integrate remediation

- Make `remediate_summary.py` run the same default-English-state validator before and after rebuild.
- Ensure the official builder/template path repairs legacy mixed-language default content while preserving the PT/EN selector and dictionaries; do not patch generated HTML through a divergent hand-built remediation path.
- Include language findings in existing remediation reports using English generated report text, without changing report paths or required top-level fields.
- Keep the existing success rule: remediation cannot report completion as successful when any error-level language finding remains.
- Preserve idempotence and source read-only behavior.

## Artifact Impact

| Area                  | Expected files/components                                                                                                                                                   | Purpose                                                                                                                                |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Agent behavior        | `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`; `summary-remediation-agent.md`                                                                             | English-default instructions requiring English as the initial/default generated language, while preserving the existing PT/EN selector |
| Workflow instructions | `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-02-extract.md`; `step-03-build-html.md`; `step-04-validate-deliver.md`; possibly `workflow.md` | Document English default output while preserving manual PT switching                                                                   |
| HTML template         | `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`                                                                                                | Normalize the default English branch while preserving selector, `setLang()`, and both dictionaries                                     |
| Builder               | `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` and, if needed, a new Summary-local utility                                                    | Normalize source-derived prose and hardcoded generated fallbacks; preserve technical values                                            |
| Validator             | `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`                                                                                                           | Deterministic blocking English-default gate that validates only the default rendered state and diagnostics                             |
| Remediation           | `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`                                                                                                          | Reuse language gate and report residual failures in English                                                                            |
| Tests                 | Existing `tests/summary/` plus focused new Summary language tests                                                                                                           | Generation, template, patterns, protected values, remediation, regression paths                                                        |
| Registry/metadata     | Existing `summary/module.yaml` only if registry/version checks require it                                                                                                   | No new agent; preserve existing registrations and update only required version metadata                                                |

No files under unrelated F1-F7 agent modules or source repositories are in scope.

## Validation Strategy

1. Generate Summary in every supported mode using representative fixtures and assert existing output paths/files remain present.
2. Inspect the initial/default generated HTML, generated Markdown (`index.md` and remediation report), and generated JSON-backed human-readable fields for English-default compliance; do not evaluate a Portuguese view reached through manual switching as a failure.
3. Validate the default Architectural Patterns section separately: English title, headers, pattern names where prose, layer, descriptions/justifications, trade-offs, references, and ADR references.
4. Run Summary-Remediation against deliberately mixed-language legacy HTML and assert rebuild + post-validation produce English-default output; the existing Portuguese manual-view path is unaffected and remains supported, or the run is blocked with findings.
5. Verify source artifacts have unchanged hashes/content after generation and remediation.
6. Verify protected technical values remain exact: code symbols, class/method names, paths, URLs, project names, acronyms, ADR filenames, Markdown references, proper nouns, and traceability IDs.
7. Run existing structural and artifact-integrity checks, placeholder checks, Mermaid compatibility checks, and content-completeness checks to prove no unrelated regression.
8. Run repeated generation/remediation with identical inputs and compare normalized language outputs and validation results for determinism.
9. Verify non-compliant output cannot be reported as valid by checking validator exit/status and remediation `errors_after` handling.

## Test Strategy

- Unit tests for label normalization, protected-value classification, source-derived prose normalization, and language diagnostics.
- Builder tests with Portuguese source content and mixed Portuguese/English source content.
- Architectural Patterns tests covering table headers, row descriptions, justifications, trade-offs, technical references, ADR references, and deterministic repeated output.
- Template tests ensuring the initial/default view is English while the PT/EN selector, `setLang()` path, and both dictionaries remain present and functional.
- Markdown/report tests for English-default-compliant `index.md` and remediation reports, validating the default state rather than the manually selected Portuguese view.
- Remediation integration test with an existing mixed-language Summary and assertions for rebuild, post-validation, source preservation, and failure behavior for unresolved content.
- Protected-value tests for paths, URLs, class/method names, project names, acronyms, ADR filenames, Markdown references, proper nouns, and exact traceability references.
- Regression tests for output locations, filenames, `summary-data.json`, `trace_id`, existing checks, and idempotence.

## Risks and Mitigations

| Risk                                            | Mitigation                                                                                                                                                                       |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Over-translating technical identifiers          | Use field/context-aware protected-value classification; preserve exact tokens and validate them separately.                                                                      |
| Language detection false positives              | Detect prose regions rather than raw tokens; ignore protected values, machine-readable data, code, paths, URLs, and acronyms; require explicit diagnostics for ambiguous values. |
| Remediation preserves legacy Portuguese         | Rebuild through the current official builder/template and run the same blocking language validator after rebuild.                                                                |
| Portuguese labels remain hardcoded in templates | Audit template text, i18n dictionaries, default attributes, empty states, and fallback labels; add template regression assertions.                                               |
| Markdown and HTML diverge                       | Normalize shared builder/report strings before both renderers and validate both artifact types independently.                                                                    |
| Source mutation                                 | Keep all source reads read-only and test hashes/content before and after execution.                                                                                              |
| Existing downstream parser breakage             | Preserve paths, artifact names, required metadata, JSON shape, trace IDs, and existing validation result structure.                                                              |
| Nondeterministic translation                    | Do not add remote translation; use deterministic local mappings/normalization and block unsafe residual prose.                                                                   |

## Definition of Done

- `ava-summary` generates Summary HTML, Markdown, and narrative content whose default rendered state is English.
- `ava-summary-remediation` rebuilds legacy/mixed-language Summary artifacts with an English default state or blocks with explicit default-view language findings, while preserving manual PT switching.
- Architectural Patterns is fully English in labels, headers, descriptions, justifications, trade-offs, fallback content, and surrounding narrative.
- Markdown and HTML artifacts pass the deterministic language gate.
- Source artifacts remain unchanged.
- Existing output paths, artifact names, traceability metadata, and output contracts remain compatible.
- Existing structural, artifact-integrity, Mermaid, placeholder, and traceability validations continue to pass.
- Technical identifiers and exact references are preserved and not falsely flagged.
- Repeated runs with identical inputs are deterministic and remediation remains idempotent.
- No Portuguese content appears in the DEFAULT rendered state of supported Summary artifacts; Portuguese remains available exclusively through the existing manual selector.

## Project Structure

### Documentation (this feature)

```text
specs/037-enforce-english-summary/
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── language-compliance.schema.json
└── plan.md
```

### Source Code (repository root)

```text
src/modules/ava-fabric-agents/summary/
├── agents/
│   ├── summary-agent.md
│   └── summary-remediation-agent.md
├── workflows/generate-summary/
│   ├── workflow.md
│   └── steps/
│       ├── step-02-extract.md
│       ├── step-03-build-html.md
│       └── step-04-validate-deliver.md
├── templates/html/
│   └── summary-template.html
└── utils/
    ├── build_summary_comprehensive.py
    ├── validate_summary.py
    └── remediate_summary.py

tests/summary/
└── focused English-default generation, validation, and remediation tests
```

**Structure Decision**: Modify the existing Summary module in place. No new agent or module is introduced, and no output contract path changes.

## Complexity Tracking

No constitutional violations. No complexity exception is required.
