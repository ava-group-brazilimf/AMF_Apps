# Tasks — Spec 037: Enforce English-Default Summary Output

**Plan**: `specs/037-enforce-english-summary/plan.md`
**Scope**: `ava-summary`, `ava-summary-remediation`, Summary module assets, and Summary-specific tests only.
**Implementation order**: Complete phases sequentially. Parallel tasks may run within a phase when their dependencies are satisfied.

## Phase 1 — Discovery and Baseline Verification

- [ ] T001 Inventory Summary generation, validation, and remediation entry points in `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`, `summary-remediation-agent.md`, `utils/build_summary_comprehensive.py`, `utils/validate_summary.py`, and `utils/remediate_summary.py`; record every current Portuguese, bilingual, or language-selectable output path in `specs/037-enforce-english-summary/baseline-findings.md`.
- [ ] T002 [P] Audit all Summary workflow instructions in `src/modules/ava-fabric-agents/summary/workflows/generate-summary/` for bilingual generation, Portuguese fallback labels, and conflicting language defaults (default rendered state only; the existing PT/EN selector and dictionaries remain unaffected); append findings to `specs/037-enforce-english-summary/baseline-findings.md`.
- [ ] T003 [P] Audit `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` for Portuguese visible text, PT/EN selectors, i18n dictionaries, default attributes, table headers, section headings, empty states, and fallback labels (default rendered state only; the existing PT/EN selector and dictionaries remain unaffected); record exact keys/locations in `baseline-findings.md`.
- [ ] T004 [P] Audit `build_summary_comprehensive.py` for hardcoded Portuguese strings, direct source-derived interpolation, Markdown/index/report generation, table and section mappings, Architectural Patterns rendering, and fallback values; record affected functions and fields in `baseline-findings.md`.
- [ ] T005 [P] Audit `validate_summary.py` and `remediate_summary.py` for existing language checks, structural/traceability/artifact-integrity checks, pre/post remediation flow, and success/blocking behavior; record compatibility constraints in `baseline-findings.md`.
- [ ] T006 [P] Inspect existing Summary tests under `tests/summary/` and repository test configuration; identify reusable fixtures and the exact commands needed for focused builder, validator, template, and remediation tests in `specs/037-enforce-english-summary/quickstart.md`.
- [ ] T007 Establish a baseline run using an existing representative project fixture; capture current output paths, artifact names, `trace_id`, validation results, and source hashes without modifying source artifacts, and store the evidence under `specs/037-enforce-english-summary/baseline/`.

## Phase 2 — Prompt and Instruction Updates

- [ ] T008 Update `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` to make English the default generated/rendered language across all execution modes, preserve the existing PT/EN selector and dictionaries, remove only conflicting bilingual-default instructions, require English default labels/prose, preserve protected technical values, and require default-view gate failure to block valid output; bump only the agent PATCH version.
- [ ] T009 Update `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md` to require English-default rebuilds and remediation reports, normalize default-view source-derived prose, repair legacy Portuguese default content through the official builder, preserve selector/i18n behavior and structure/traceability, and report unresolved default-view language failures as blocking; bump only the agent PATCH version.
- [ ] T010 [P] Align `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-02-extract.md` with default-English extraction/normalization rules, including protected values and Architectural Patterns fields.
- [ ] T011 [P] Align `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-03-build-html.md` with fixed English initial output (default rendered state only; the existing PT/EN selector and dictionaries remain unaffected), preserving the existing PT/EN selector and documenting normalization before default HTML/Markdown embedding.
- [ ] T012 [P] Align `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-04-validate-deliver.md` and `workflow.md` with the blocking default-English validation gate while preserving existing selector, i18n, artifact, and structural behavior.
- [ ] T013 Verify prompt and workflow changes remain in the repository-required agent instruction language, contain no new output paths, and consistently cover all supported Summary and remediation execution paths documented in `spec.md`.

## Phase 3 — Template, Mapping, and Builder Updates

- [ ] T014 Normalize the default rendered branch of `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` so visible labels, headings, table headers, empty states, statuses, navigation labels, and fallback text are English without changing DOM IDs, output layout, Mermaid behavior, artifact contracts, the Portuguese dictionary, the English dictionary, the selector UI, or `setLang()` behavior.
- [ ] T015 Set and enforce English as the default/initial language configuration in `summary-template.html`, explicitly preserving the PT/EN selector, `setLang()` function, and both i18n dictionaries; do not remove or disable Portuguese rendering.
- [ ] T016 [P] Add a regression test using a freshly generated Summary HTML artifact opened without user interaction or a script-triggered `setLang('pt')` call; assert the initial view renders English labels, including Architectural Patterns headers `Pattern`, `Layer`, `Justification`, `Reference`, `Trade-offs`, and `ADR`.
- [ ] T017 Normalize the template i18n dictionary's English branch and all default `data-i18n`/`data-i18n-title`/placeholder values in `summary-template.html`, including Architectural Patterns, Technology Framework, Solution Structure, Migration Waves, ADR references, and related tables; preserve the PT branch unchanged except where required to keep existing switching functional.
- [ ] T018 [P] Replace hardcoded Portuguese fallback, status, pending, approval, wave, section, and table-label strings emitted in the default branch by `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` with English equivalents while preserving exact technical values and existing placeholder/data shapes.
- [ ] T019 [P] Update Summary Markdown generation in `build_summary_comprehensive.py` for `index.md`, generated narrative text, empty-state text, and report-facing labels so the default/generated Markdown is English with unchanged paths and metadata; do not change the existing PT/EN HTML switching behavior.
- [ ] T020 Normalize the TO-BE Architectural Patterns rendering in `build_summary_comprehensive.py`: template/i18n owns default headers, while builder/source-derived fields `pattern_name`, `layer`, `justification`, and `trade_offs` are normalized for the default English view; preserve `reference_artifact` and `adr_reference`, and use an English no-data fallback.
- [ ] T021 Normalize only Summary-emitted source-derived mappings in `build_summary_comprehensive.py`, limited to Technology Framework, Solution Structure, Migration Wave Plan, ADR references, recommendations, descriptions, and trade-offs; do not translate protected values or unrelated F1–F7 artifacts.
- [ ] T022 [P] Audit and update any remaining Summary-specific legacy template copies or generated-label sources that are actually used by the official builder; do not modify unrelated backup artifacts unless the implementation proves they are executable inputs.
- [ ] T023 Run a source scan over the Summary module and generated-label mapping tests to confirm the default/executable Summary path emits English by default while preserving the PT/EN selector, both dictionaries, and manual `setLang()` switching; exclude agent instructions and read-only source artifacts.

## Phase 4 — Source-Derived Text Normalization

- [ ] T024 Implement the Summary-local deterministic text classification/normalization utility in `src/modules/ava-fabric-agents/summary/utils/` using the data model: distinguish template labels, builder fallbacks, default-view source-derived prose, report text, and technical values.
- [ ] T025 Implement protected-token extraction and restoration for code symbols, class names, method names, file paths, URLs, technical identifiers, ADR filenames, Markdown references, project names, proper nouns, standard acronyms, exact traceability references, and non-prose numeric/boolean/coded values.
- [ ] T026 Implement bounded deterministic local mappings/rules for supported Portuguese and mixed-language human-readable prose in the default English view; return an explicit non-compliance/unsafe result instead of inventing content when normalization confidence is insufficient.
- [ ] T027 Integrate normalization before default English HTML row generation, Markdown generation, JSON-backed human-readable data, and remediation report generation; ensure source files are read-only and only rendered copies are changed.
- [ ] T028 Apply the normalization utility to every default-view Architectural Patterns field and explicitly verify protected `reference_artifact` and `adr_reference` values remain byte-for-byte unchanged.
- [ ] T029 Integrate empty, null, numeric, coded, structured, and non-textual value handling so no business content is invented and surrounding default-view explanatory labels remain English.
- [ ] T030 Add deterministic diagnostics for unsafe or residual non-English text in the default state, including artifact/region identifiers compatible with `language-compliance.schema.json` and existing validator/report structures.

## Phase 5 — Language Compliance Gate

- [ ] T031 Implement the language-compliance result model and serialization in `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` according to `specs/037-enforce-english-summary/contracts/language-compliance.schema.json` (default rendered state only; the existing PT/EN selector and dictionaries remain unaffected), preserving existing validator result compatibility and without requiring a new output artifact.
- [ ] T032 Add a blocking validator check for the default rendered/generated HTML state, visible labels, headings, table headers/cells, embedded default-view prose, and generated Summary Markdown/report artifacts; ignore protected technical values without allowing default-view prose violations.
- [ ] T033 Make the language gate unconditional for the default English state regardless of configured default-language metadata, while preserving and validating the existing PT/EN i18n keys and selector behavior; do not apply the gate to the Portuguese view reached only through manual selector interaction.
- [ ] T034 Add an explicit default-state Architectural Patterns validation check covering English section title, headers, pattern rows, descriptions, justifications, trade-offs, fallback content, references, and ADR references.
- [ ] T035 Integrate the default-English language check into the existing validation registry/quality result so selector/i18n presence, structural, placeholder, traceability, artifact-integrity, Mermaid, and content-completeness checks continue to run and remain independently reported.
- [ ] T036 Ensure non-compliant default-language results are error-level/blocking and cannot be treated as valid or promotion-ready; preserve existing JSON/report fields and remediation failure accounting.
- [ ] T037 Validate the compliance result against `specs/037-enforce-english-summary/contracts/language-compliance.schema.json`, including compliant default state, non-compliant default state, protected-token, and diagnostic-region cases.

## Phase 6 — Summary-Remediation Behavior

- [ ] T038 Update `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py` to run the shared default-English-state validator in baseline and post-rebuild validation without introducing a divergent repair path.
- [ ] T039 Ensure remediation rebuilds legacy mixed-language Summary HTML through `build_summary_comprehensive.py` and the official template, replacing non-English default content while preserving valid structure, traceability metadata, paths, filenames, technical identifiers, selector UI, and PT/EN dictionaries.
- [ ] T040 Update remediation report generation to use English-default generated headings, statuses, diagnostics, and narrative text while preserving existing report paths and required JSON fields; manual Portuguese switching remains supported in HTML.
- [ ] T041 Ensure unresolved or unsafe default-view source-derived content produces explicit language findings, keeps `errors_after > 0`, blocks a success result, and is reported as pending/non-compliant rather than silently accepted.
- [ ] T042 Verify remediation remains idempotent: a second run over a compliant default-English artifact produces no language regressions, preserves source artifacts and selector/i18n behavior, and reports no new default-view language failures.

## Phase 7 — Tests and Regression Validation

- [ ] T043 Add unit tests for deterministic normalization of Portuguese source prose and mixed Portuguese/English prose in the default English view, including expected English output and unsafe-text diagnostics; do not require normalization for the manually selected Portuguese view.
- [ ] T044 Add protected-value tests covering code symbols, class names, method names, file paths, URLs, technical identifiers, ADR filenames/references, Markdown references, project names, proper nouns, standard acronyms, exact traceability references, and empty/null/numeric/coded values.
- [ ] T045 Add template regression tests proving a freshly generated artifact initially renders English labels, section titles, table headers, and fallback labels while the PT/EN selector, `setLang()` path, and both dictionaries remain present and functional; do not test for their absence.
- [ ] T046 Add Architectural Patterns tests for default English headers `Pattern`, `Layer`, `Justification`, `Reference`, `Trade-offs`, and `ADR`; test row normalization, preserved references/ADR IDs, fallback content, and deterministic repeated rendering.
- [ ] T047 Add builder integration tests using Portuguese and mixed-language source artifacts; assert the initial/default HTML, Markdown, and JSON-backed human-readable output is English while source files remain byte-for-byte unchanged and manual Portuguese switching remains available.
- [ ] T048 Add default-state language-gate tests for compliant HTML/Markdown, Portuguese violations, mixed-language violations, ambiguous/unsafe text that must block, protected technical values, manual Portuguese-view exclusion, and schema-valid compliance results.
- [ ] T049 Add Summary-Remediation integration tests using legacy HTML with Portuguese default-state content; assert regeneration repairs the default view, preserves structure/traceability/selector/i18n behavior, validates Markdown/HTML, preserves source hashes, and blocks unresolved default-view violations.
- [ ] T050 Add regression tests confirming existing Summary output paths, artifact names, `summary-data.json` shape, `index.md`, `trace_id`, selector/dictionary presence, and non-language validator checks remain compatible.
- [ ] T051 Add repeated-run determinism tests for Summary generation and remediation using identical inputs, comparing normalized default-view content and validation outcomes.
- [ ] T052 [P] Run the focused Summary test suite and record raw command/result evidence for later consolidation in `quickstart.md` during Phase 8.
- [ ] T053 [P] Run the existing Summary structural, artifact-integrity, traceability, placeholder, Mermaid, and content-completeness validation suites and record any pre-existing failures separately.

## Phase 8 — Documentation and Quickstart Updates

- [ ] T054 Update `specs/037-enforce-english-summary/quickstart.md` with the confirmed test commands, Summary generation/remediation validation commands, expected default-English pass/fail behavior, preserved PT/EN switching behavior, and troubleshooting for default-language gate failures.
- [ ] T055 Document protected technical identifier behavior and examples of compliant versus non-compliant default-state output in `quickstart.md` or a directly scoped Summary developer note; do not add additional multilingual configuration guidance.
- [ ] T056 Document how to interpret default-language compliance diagnostics, offending regions, blocking status, manual Portuguese-view exclusion, and remediation `errors_after` results while preserving existing output contracts.

## Phase 9 — Final Verification

- [ ] T057 Run Summary generation across supported execution modes and verify every generated artifact initially renders in English, including Architectural Patterns, Technology Framework, Solution Structure, Migration Wave Plan, ADR references, Markdown, HTML, and generated reports; verify manual PT switching still works.
- [ ] T058 Run Summary-Remediation against a legacy mixed-language default view and verify regenerated HTML/Markdown/report content has an English default or is explicitly blocked with findings, while PT/EN switching remains functional.
- [ ] T059 Verify source artifacts remain unchanged using before/after hashes and confirm output paths, artifact names, `trace_id`, structural metadata, selector/i18n behavior, and validation contracts remain compatible.
- [ ] T060 Verify protected technical identifiers are preserved exactly and are not falsely reported as default-language violations.
- [ ] T061 Run the complete Summary regression and quality-gate suites; confirm existing structural, traceability, artifact-integrity, placeholder, Mermaid, selector/i18n, and content-completeness checks still pass.
- [ ] T062 Run repeated Summary and remediation executions with identical inputs and confirm deterministic default-English output, stable compliance results, and remediation idempotence.
- [ ] T063 Confirm a deliberately non-compliant default-language artifact cannot be reported as valid or promotion-ready and that remediation success is blocked when error-level default-view findings remain; manual Portuguese-view content must not trigger this gate.
- [ ] T064 Record final evidence and implementation status in `specs/037-enforce-english-summary/quickstart.md`, then mark this task list complete only after all clarified Definition of Done items in `plan.md` are verified.

## Dependencies and Execution Order

```text
Phase 1 Discovery
    ↓
Phase 2 Prompt/Instruction Updates
    ↓
Phase 3 Template/Mapping/Builder Updates ──┐
    ↓                                      │
Phase 4 Source Normalization ─────────────┤
    ↓                                      ├── Phase 7 Tests
Phase 5 Language Gate ────────────────────┘       ↓
    ↓                                             Phase 8 Documentation
Phase 6 Remediation ──────────────────────────────↓
                                                  Phase 9 Final Verification
```

- T002–T006 can run in parallel after T001 starts, provided they write to separate discovery sections or coordinate through `baseline-findings.md`.
- T010–T012 can run in parallel after T008–T009 establish the policy.
- T018–T019 and T022 can run in parallel after T014–T017 establish the canonical default-English template policy.
- T024–T026 can run in parallel after discovery, then T027–T030 depend on their interfaces.
- T031–T034 can be developed in parallel after the normalization contract is agreed; T035–T037 integrate and validate them.
- T043–T051 can be developed in parallel after the relevant implementation interfaces exist; T052–T053 run after the tests are complete.
- T054–T056 can run in parallel with final test execution once behavior is stable.

## Implementation Strategy

1. Establish a factual baseline without modifying source artifacts.
2. Lock the default-English policy in both agent prompts and workflows while preserving manual PT/EN switching.
3. Normalize template labels and builder fallbacks before adding the blocking gate.
4. Implement protected-value-aware deterministic source normalization.
5. Add the shared validation contract and make it blocking.
6. Integrate remediation through the official rebuild path.
7. Validate focused scenarios, regression behavior, source preservation, and determinism.
8. Complete final verification and evidence before reporting readiness.
