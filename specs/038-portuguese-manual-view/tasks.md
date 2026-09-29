# Implementation Tasks: Full-Quality Portuguese (PT-BR) Manual View Support

**Feature**: `038-portuguese-manual-view`
**Plan**: [plan.md](plan.md)
**Canonical language schema**: `specs/037-enforce-english-summary/contracts/language-compliance.schema.json`

## Phase 1 — Fixture Creation

**Goal**: Establish a clean, isolated end-to-end baseline before modifying feature code. The fixture is reused by all later phases; `sophia` and `MeuERP-002` are not acceptance fixtures.

- [ ] T001 Create the isolated feature-038 fixture project structure under `tests/summary/fixtures/038-portuguese-manual-view/project/`, including `context/`, `outputs/asis/`, `outputs/tobe/`, `outputs/qa/`, `outputs/deliverables/`, and `outputs/summary/`.
- [ ] T002 Create a complete valid `project-config.yaml` and `shared-context.md` under `tests/summary/fixtures/038-portuguese-manual-view/project/context/`, with the project name, English default, trace metadata, and Summary-required configuration fields.
- [ ] T003 Create `tests/summary/fixtures/038-portuguese-manual-view/project/outputs/tobe/patterns-applied.json` with 2–3 builder-compatible records using the exact fields `pattern_name`, `layer`, `justification`, `reference_artifact`, `trade_offs`, and `adr_reference`; include English, Portuguese, and mixed-language prose plus protected values.
- [ ] T004 Create valid, resolvable Mermaid fixture input under `tests/summary/fixtures/038-portuguese-manual-view/project/outputs/` or configure the fixture to bypass unrelated Mermaid generation while preserving the required compatibility gate path.
- [x] T005 Add `tests/summary/test_038_fixture_baseline.py` to run the unmodified `build_summary_comprehensive.py` and `validate_summary.py` against the isolated fixture, assert generated HTML/output reports and baseline output paths, require C8.1 to pass, and explicitly allow-list only the known minimal-fixture non-language validator errors before feature code changes.
- [x] T006 [P] Add fixture source-hash helpers and baseline assertions in `tests/summary/test_038_fixture_baseline.py` to prove fixture source artifacts remain unchanged during baseline generation and validation.

## Phase 2 — Target-Aware Language Utility (Phase A)

**Goal**: Extend deterministic local normalization while preserving existing English signatures and protected-token behavior.

- [ ] T007 Extend `normalize_text`, `normalize_mapping`, and related APIs in `src/modules/ava-fabric-agents/summary/utils/summary_language.py` with an optional `language_target`/target parameter accepting `en` or `pt`, preserving the current English default behavior and backward-compatible call signatures.
- [ ] T008 Add deterministic PT-BR normalization mappings and residual-language diagnostics in `src/modules/ava-fabric-agents/summary/utils/summary_language.py` for source-derived prose, including pattern names, layers, justifications, trade-offs, fallbacks, recommendations, and equivalent free-text values.
- [ ] T009 Reuse and extend the existing protected-token masking/restoration path in `src/modules/ava-fabric-agents/summary/utils/summary_language.py` for PT normalization, preserving `reference_artifact`, `adr_reference`, code symbols, class/method names, paths, URLs, ADR filenames, Markdown references, project names, proper nouns, acronyms, and traceability identifiers byte-for-byte.
- [ ] T010 Implement target-aware unsafe/unresolved diagnostics in `src/modules/ava-fabric-agents/summary/utils/summary_language.py` using the existing `LanguageDiagnostic`/`NormalizationResult` structure and target-specific status values without inventing business content for empty, coded, or non-text values.
- [ ] T011 [P] Add `tests/summary/test_summary_language_pt.py` covering English default normalization, entirely Portuguese prose, mixed-language prose, empty/null/numeric values, deterministic repeated normalization, and unresolved PT diagnostics using the isolated fixture data.
- [ ] T012 [P] Add protected-value assertions in `tests/summary/test_summary_language_pt.py` for paths, URLs, code symbols, ADR filenames, proper nouns, acronyms, `reference_artifact`, `adr_reference`, and exact traceability values.

## Phase 3 — Render and Data Integration (Phase B)

**Goal**: Ensure builder-generated dynamic content supports the PT manual view without changing the English default or selector contract.

- [ ] T013 Route Architectural Patterns and equivalent human-readable builder substitutions through target-aware normalization in `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`, preserving exact reference fields and existing HTML/JSON/Markdown escaping.
- [ ] T014 Normalize builder fallback, status, empty-state, recommendation, narrative, and report-facing values for the selected target in `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` while retaining English as the default generated state.
- [ ] T015 Preserve the selector, `setLang()`, `I18N.pt`, `I18N.en`, and `var lang = "en"` structure and behavior in `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`; add only target-aware dynamic rendering required for source-derived prose.
- [ ] T016 [P] Add `tests/summary/test_summary_template_language.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) to verify selector options, `setLang('pt')`, switching back to English, both dictionaries, initial English state, and localized Architectural Patterns rows.
- [ ] T017 [P] Add builder regression assertions in `tests/summary/test_summary_builder_pt.py` for all fixture pattern entries, representative free-text sections, English default output, PT manual-view output, output paths, and protected references.

## Phase 4 — Explicit Portuguese Compliance Gate (Phase C)

**Goal**: Extend the canonical 037 schema and validator with explicit PT targeting, using C8-equivalent error-level blocking semantics.

- [ ] T018 Extend the canonical schema in `specs/037-enforce-english-summary/contracts/language-compliance.schema.json` in place with the required `target` property constrained to `en` or `pt`; delete the non-authoritative `specs/038-portuguese-manual-view/contracts/language-compliance.schema.json` copy so no duplicate schema is maintained.
- [ ] T019 Add an explicit `--language-target {en,pt}` option to `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`, preserving omitted-target behavior as the existing English C8 path and loading only the canonical 037 schema at runtime.
- [ ] T020 Implement target-aware compliance extraction in `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` for visible/generated PT text regions and embedded source-derived prose, excluding protected values and machine-readable identifiers from false positives.
- [ ] T021 Register the explicit PT language check in `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` at `level="error"`, with `target: pt`, artifact/region/offending-text diagnostics, `blocking: true`, and the same failure accounting and exit semantics as C8.
- [ ] T022 [P] Add `tests/summary/test_summary_pt_validation.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) and covering omitted-target English regression, explicit PT compliant output, explicit PT mixed-language failure, unsafe prose failure, protected-value exclusion, canonical-schema loading, serialized `target`, and error-level blocking.
- [ ] T023 [P] Add schema validation coverage in `tests/summary/test_summary_pt_validation.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) and asserting both `target: en` and `target: pt` results validate against `specs/037-enforce-english-summary/contracts/language-compliance.schema.json` and no feature-038 schema is loaded.

## Phase 5 — Targeted Remediation (Phase D)

**Goal**: Reuse the official builder/validator path and make unresolved targeted PT findings block remediation exactly like C8.

- [ ] T024 Add the matching `--language-target {en,pt}` option to `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`, preserving omitted-target English-default behavior and passing the target through baseline and post-rebuild validation.
- [ ] T025 Ensure targeted PT validation findings contribute to `errors_before`, `errors_after`, `remaining`, remediation reports, and process exit status in `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`; unresolved PT findings must keep `errors_after > 0` and prevent success reporting.
- [ ] T026 Ensure targeted PT remediation invokes only the official `build_summary_comprehensive.py` rebuild path and preserves the English default marker, selector, dictionaries, output paths, metadata, and protected values in `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`.
- [ ] T027 [P] Add `tests/summary/test_summary_pt_remediation.py` covering targeted PT remediation success, unresolved PT blocking failure, `errors_after > 0`, nonzero exit, no success message, official rebuild invocation, and source-hash preservation using the isolated fixture.
- [ ] T028 [P] Add omitted-target remediation regression coverage in `tests/summary/test_summary_pt_remediation.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) and proving English-default remediation behavior and output state remain unchanged when no PT target is supplied.

## Phase 6 — Integrated Tests and Regression Coverage (Phase E)

**Goal**: Prove the full feature against the isolated fixture and protect unrelated Summary quality gates.

- [ ] T029 Add end-to-end fixture coverage in `tests/summary/test_summary_pt_end_to_end.py` for generation, selector switching, Architectural Patterns, representative sections, English restoration, PT compliance, and output-contract preservation.
- [ ] T030 Add determinism tests in `tests/summary/test_summary_pt_end_to_end.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) and comparing repeated normalization, generation, validation, and remediation results for identical fixture inputs and target settings.
- [ ] T031 Add byte-for-byte protected-value and source-read-only regression tests in `tests/summary/test_summary_pt_end_to_end.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) across generation, validation, switching, and remediation.
- [ ] T032 Add blocking-semantics assertions in `tests/summary/test_summary_pt_end_to_end.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) and proving explicit PT failures produce `errors_after > 0`, a nonzero process exit code, and no success message — matching C8's exact error-level blocking behavior, not merely “similar” behavior.
- [ ] T033 [P] Add regression assertions in `tests/summary/test_summary_regressions.py` using the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) for structural, artifact-integrity, Mermaid, placeholder, traceability, and content-completeness checks.
- [ ] T034 [P] Run `python -m pytest tests/summary` against the isolated feature-038 fixture (`tests/summary/fixtures/038-portuguese-manual-view/project/`) and record the result in the feature validation notes without modifying unrelated fixture/project outputs.

## Phase 7 — Documentation (Phase F)

- [ ] T035 Update `specs/038-portuguese-manual-view/quickstart.md` with the isolated fixture location, fixture contents, baseline command, default English command, explicit PT validation command, targeted PT remediation command, canonical 037 schema path, and troubleshooting for unresolved PT findings.
- [ ] T036 [P] Update Summary agent/workflow instructions in `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`, `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`, and `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-04-validate-deliver.md` to document optional PT targeting, canonical schema usage, and error-level blocking while keeping instruction text in pt-BR. Bump the PATCH version of `summary-agent.md` and `summary-remediation-agent.md` to reflect the optional PT-targeting capability, consistent with `plan.md`'s Versioning section and feature 037's precedent (T008/T009). Verify the version numbers are updated and any module/agent registry version references remain consistent.
- [ ] T037 [P] Update `src/modules/ava-fabric-agents/summary/workflows/generate-summary/workflow.md` with the optional target input and explicit PT validation/remediation semantics without changing the default `en` behavior.

## Phase 8 — Final Verification

- [ ] T038 Run the complete feature-038 test suite against the isolated fixture and verify all planned Phase A–F acceptance scenarios pass.
- [ ] T039 Verify the default English state remains unchanged across generation, validation, and omitted-target remediation, including `var lang = "en"`, C8 behavior, selector availability, dictionaries, output contracts, and traceability metadata.
- [ ] T040 Verify the PT-BR view is complete and coherent for Architectural Patterns and representative Summary sections, with unresolved unsafe prose blocked rather than silently accepted.
- [ ] T041 Verify all protected values remain byte-for-byte identical and no source artifact under the isolated fixture was modified.
- [ ] T042 Verify explicit PT remediation leaves `errors_after > 0`, exits nonzero, and never reports success when targeted PT findings remain.
- [ ] T043 Verify `validate_summary.py` consumes exactly one canonical schema at `specs/037-enforce-english-summary/contracts/language-compliance.schema.json` and no duplicate feature-038 schema is used.
- [ ] T044 Run repository error validation for all changed implementation, test, schema, and documentation files and resolve only feature-related errors.

## Dependencies and Execution Order

```text
T001 → T002 → T003 → T004 → T005 → T006
  └→ T007–T012 → T013–T017 → T018–T023 → T024–T028 → T029–T034 → T035–T037 → T038–T044
```

- The fixture baseline tasks T001–T006 are mandatory before any implementation task.
- T018 → T019 → T020/T021 → T022/T023.
- T007–T012 must precede builder integration; T013–T017 must precede end-to-end rendering tests.
- T019–T023 must precede targeted remediation tasks T024–T028.
- T029–T034 depend on the completed implementation phases and reuse the same fixture.
- Documentation tasks may proceed after the behavior and CLI option names are finalized.

## Parallel Execution Examples

- After T005 establishes a clean baseline, T006 can run in parallel with test-fixture review; no implementation task starts before T006.
- After T010, T011 and T012 can run in parallel because they modify separate test concerns.
- After T015, T016 and T017 can run in parallel.
- After T021, T022 and T023 can run in parallel.
- After T026, T027 and T028 can run in parallel.
- After T029, T030, T031, T032, and T033 can run in parallel.
- After behavior is finalized, T035, T036, and T037 can run in parallel.

## Implementation Strategy

1. **Fixture-first**: establish a valid, isolated baseline before touching production Summary code.
2. **MVP**: deliver deterministic PT normalization, protected-value preservation, selector-compatible rendering, and explicit blocking PT validation.
3. **Incremental delivery**: integrate remediation, full regression tests, and documentation only after the shared language boundary and canonical schema are stable.
4. **Safety**: keep English as the default, preserve source artifacts and technical identifiers, use the official builder/validator path, and fail closed on unresolved targeted PT findings.
