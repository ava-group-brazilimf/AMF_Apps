# Baseline Findings — Phase 1 Discovery

**Feature**: `037-enforce-english-summary`
**Phase**: Phase 1 — Discovery and Baseline Verification (`T001`–`T007`)
**Date**: 2026-08-07
**Representative project**: `sophia`
**Scope rule**: Read-only discovery. No Summary prompts, templates, builders, validators, remediation logic, source artifacts, or generated Summary artifacts were modified.

## T001 — Summary entry-point inventory

| Entry point               | Location                                                                       | Observed responsibility and language path                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Summary agent             | `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`                | Defines Summary triggers (`GS`, `SAS`, `STO`, `SI`, `UP`), input `language: "pt"                                                                                                                                                                                                                                                                                                                                                                                                                             | "en"`with default`pt` at the Phase 1 baseline, and HTML/i18n behavior. The agent body contains Portuguese operational instructions because Article V requires agent instructions in pt-BR; this is not itself generated client output. |
| Summary workflow          | `src/modules/ava-fabric-agents/summary/workflows/generate-summary/workflow.md` | Declares `language` input with default `pt` at the Phase 1 baseline (line 41) and dispatches Steps 01–04.                                                                                                                                                                                                                                                                                                                                                                                                    |
| HTML builder              | `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`   | Reads source artifacts, builds substitutions and dynamic HTML rows, directly interpolates TO-BE pattern fields at lines 3193–3213, writes generated overview JSON at line 1434 and overview Markdown at line 6922, and writes client-facing compatibility reports at lines 7171–7174. Portuguese-derived parser labels and fallback values are present in the builder (for example `Camada` at lines 569–570, `Estado Global`/`Antipadrão Arq.` at line 2462, and pending wave defaults at lines 3671–3673). |
| Summary validator         | `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`              | C8 language consistency is implemented at lines 754–776. The check is skipped when project `language` is not `en` at lines 763–764. C8 registry entries are at lines 2485–2490. The validator also contains structural, placeholder, artifact, traceability, and content-completeness checks.                                                                                                                                                                                                                |
| Summary remediation agent | `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`    | Delegates rebuild to `build_summary_comprehensive.py` and validation to `validate_summary.py`; operates on existing outputs without rerunning upstream agents. Its script/reporting flow is described in Portuguese and must remain so under the repository language convention.                                                                                                                                                                                                                             |
| Remediation utility       | `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`             | Runs baseline validation at lines 61–82, rebuilds through the official builder at lines 558–570, revalidates at lines 573–590, writes remediation reports at lines 593–622, and blocks successful completion when `errors_after > 0` at lines 650–675.                                                                                                                                                                                                                                                       |

### Current output-language paths

- **Default path currently observed**: the template initializes `var lang = "pt"` at `summary-template.html:5845`; the workflow and agent contracts also default `language` to `pt`.
- **Manual PT/EN selector**: preserved and functional. The selector is at `summary-template.html:2236–2242` and calls `setLang(this.value)`.
- **Manual switching implementation**: `function setLang(l)` begins at `summary-template.html:8550`; it updates `lang`, applies the selected i18n dictionary to `[data-i18n]`, title, and placeholder attributes, updates `document.documentElement.lang`, and rerenders dynamic sections.
- **No source or generated artifact was modified** during this phase.

## T002 — Workflow audit

| File                                     | Location    | Finding                                                                                                                                                                                                                                         |
| ---------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workflows/generate-summary/workflow.md` | Lines 33–42 | Input table exposes `language`; default is `pt` at line 41. This is a default-language conflict for the clarified feature, not a reason to remove the selector.                                                                                 |
| `steps/step-02-extract.md`               | Lines 1–225 | Extraction instructions contain Portuguese headings and fallback terms such as `N/D`; the step describes source parsing and normalization but has no explicit default-English policy.                                                           |
| `steps/step-03-build-html.md`            | Lines 36–45 | Explicitly instructs bilingual Executive Summary generation with `pt` and `en` fields. Lines 207 and 223–224 instruct i18n-based language switching for phase/no-data messages. Preserve switching; revise the default branch in a later phase. |
| `steps/step-04-validate-deliver.md`      | Lines 1–126 | Validates placeholders, sections, autocontainment, output paths, and report/index generation, but has no default-English compliance gate. Generated fallback examples are Portuguese.                                                           |

## T003 — Template audit

### Selector and i18n — cross-check of earlier C1 finding

| Element            | Exact location                      | Branch/behavior                                                             |
| ------------------ | ----------------------------------- | --------------------------------------------------------------------------- |
| Language label     | `summary-template.html:2238`        | Static bilingual selector label: `Idioma / Language`.                       |
| PT option          | `summary-template.html:2240`        | Manual Portuguese branch: `<option value="pt">Português (PT-BR)</option>`.  |
| EN option          | `summary-template.html:2241`        | Manual English branch: `<option value="en">English (EN-US)</option>`.       |
| Selector callback  | `summary-template.html:2239`        | `onchange="setLang(this.value)"`; must remain functional.                   |
| PT dictionary      | `summary-template.html:5262` onward | `I18N.pt` dictionary; Portuguese manual branch.                             |
| EN dictionary      | `summary-template.html:5553` onward | `I18N.en` dictionary; intended default-English branch.                      |
| Language state     | `summary-template.html:5845`        | `var lang = "pt"`; current initial/default state is Portuguese.             |
| Switching function | `summary-template.html:8550` onward | `setLang(l)` applies the selected dictionary and rerenders dynamic content. |

### Architectural Patterns — cross-check of earlier C2 finding

| Content                               | Exact location                    | Provenance                                                                                                |
| ------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Navigation-pattern header `Padrão`    | `summary-template.html:2959`      | Static template markup for the navigation-pattern table; Portuguese visible default text.                 |
| Pattern table header `Padrão` / `ADR` | `summary-template.html:3831–3832` | Static template markup with i18n keys.                                                                    |
| Layer header `Camada`                 | `summary-template.html:3920`      | Static template markup with i18n key `th-layer`.                                                          |
| TO-BE PT pattern dictionary values    | `summary-template.html:5375`      | `I18N.pt` values for `th-pattern-name`, `th-justification`, `th-reference`, `th-tradeoffs`, and `th-adr`. |
| TO-BE EN pattern dictionary values    | `summary-template.html:5666`      | `I18N.en` equivalents: `Pattern`, `Justification`, `Reference Artifact`, `Trade-offs`, `ADR`.             |
| TO-BE pattern table headers           | `summary-template.html:3975–3980` | Static markup uses i18n keys; rendered language comes from `I18N[lang]`.                                  |
| Direct `Referência` header            | `summary-template.html:3131`      | Static template/i18n header in the Security Review table.                                                 |

**Conclusion**: Portuguese Architectural Patterns headers originate from the template markup and PT i18n dictionary, not from `build_summary_comprehensive.py`. Pattern row values originate from source-derived data and builder interpolation.

## T004 — Builder audit

- `build_summary_comprehensive.py:3193–3213` reads `tobe/patterns-applied.json`, extracts `pattern_name`, `layer`, `justification`, `reference_artifact`, `trade_offs`, and `adr_reference`, then directly interpolates them into `TOBE_PATTERNS_ROWS`.
- `build_summary_comprehensive.py:3210–3213` emits a fallback row when `patterns-applied.json` is unavailable.
- `build_summary_comprehensive.py:569–570` parses Portuguese source headings containing `Camada`.
- `build_summary_comprehensive.py:2462` contains Portuguese classification labels (`Estado Global`, `Antipadrão Arq.`, `Dep. Circular`).
- `build_summary_comprehensive.py:3671–3673` contains Portuguese fallback wave labels (`TO-BE design pendente`, `Stack codegen pendente`, `QA e entrega pendentes`).
- `build_summary_comprehensive.py:3687–3688` contains Portuguese fallback approval values (`Pendente`).
- `build_summary_comprehensive.py:6922` writes a generated overview Markdown file; `build_summary_comprehensive.py:7171–7174` writes compatibility reports. The builder does not itself implement the PT/EN selector; that behavior belongs to the HTML template.
- Source-derived data is read from project outputs and is not modified by the builder in this audit.

## T005 — Validator and remediation audit

### C8 cross-check of earlier C5 finding

| Check                     | Exact location                  | Finding                                                                                                                                            |
| ------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| C8 implementation         | `validate_summary.py:754–776`   | `PT_STOPWORDS` and `_c8_1(ctx)` inspect embedded file content.                                                                                     |
| Skip condition            | `validate_summary.py:763–764`   | `if (ctx.config.get("language") or "pt") != "en": return Result(True, "language != en; skipped")`; with `language: pt`, language drift is skipped. |
| C8 registry               | `validate_summary.py:2485–2490` | C8.1 is only a warning and is described as conditional on `language=en`; C8.3 requires selected PT and EN i18n keys.                               |
| Selector structural check | `validate_summary.py:646`       | Validator locates `function setLang` in the generated HTML.                                                                                        |

### Remediation flow and compatibility constraints

- `remediate_summary.py:61–82` invokes the validator in-process and can apply existing auto-fixes.
- `remediate_summary.py:558–570` rebuilds via the official `build_summary_comprehensive.py` script.
- `remediate_summary.py:573–590` computes `errors_before`, `errors_after`, fixed IDs, remaining IDs, and improvement percentage.
- `remediate_summary.py:593–622` writes `remediation-report.md` and `remediation-report.json`.
- `remediate_summary.py:650–675` returns failure when error-level findings remain; this is the compatibility point for a future default-English gate.
- Existing structural, artifact-integrity, Mermaid, placeholder, traceability, and content-completeness checks must remain active.
- The existing PT/EN selector and dictionaries must remain functional; the future gate must inspect only the initial/default English state.

## T006 — Test and fixture audit

Existing `tests/summary/` contains:

- `test_blueprint_compatibility.py`
- `test_blueprint_report_contract.py`
- `test_c4_component_segmentation.py`
- `test_c4_relationship_sanitizer.py`
- `fixtures/`

No focused English-default language, template-default, builder-normalization, or remediation-language test file currently exists under `tests/summary/`.

Repository test configuration:

- `pytest.ini` is not present at the repository root.
- `pyproject.toml` is not present at the repository root.
- Existing tests use pytest conventions and can be invoked with `python -m pytest tests/summary` after confirming the environment.
- Existing utility scripts are executable directly with Python from the repository root.

Recommended future focused commands (not executed in Phase 1):

- `python -m pytest tests/summary`
- `python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project sophia`
- `python src/modules/ava-fabric-agents/summary/utils/remediate_summary.py --project sophia`
- `python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project sophia` (generation-affecting; do not run until implementation phase)

## T007 — Baseline evidence

Baseline collection was read-only and did not rebuild or regenerate the Summary.

| Measurement                     | Result                                                                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Representative project          | `sophia`                                                                                                                 |
| Existing Summary HTML           | `projects/sophia/outputs/summary/AVA-FABRIC-SUMMARY-sophia-2026-08-07.html`                                              |
| HTML size                       | 11,074,697 bytes                                                                                                         |
| Template signature              | Present: `AVA Fabric Summary Template v1.0`                                                                              |
| Selector                        | Present: PT and EN options, `id="lsel"`                                                                                  |
| `setLang()`                     | Present                                                                                                                  |
| PT/EN dictionaries              | Both present                                                                                                             |
| Current default language marker | `var lang = "pt"`                                                                                                        |
| `summary-data.json`             | Absent                                                                                                                   |
| `index.md`                      | Absent                                                                                                                   |
| HTML `data-trace`               | `unknown`                                                                                                                |
| Project-config `trace_id`       | Empty in `projects/sophia/context/shared-context.md`                                                                     |
| Source/output files hashed      | 752 files under `outputs/asis`, `outputs/tobe`, `outputs/qa`, `outputs/deliverables`, and `outputs/devops` where present |
| Summary HTML SHA-256            | `1574DA3BD2EA0D5FBA3F4D694084E47B1491FB39344B764E2063B1562E4A8581`                                                       |
| Source hash manifest            | `specs/037-enforce-english-summary/baseline/source-sha256-before.txt`                                                    |

The baseline project is an existing artifact set rather than a clean reproducible fixture: its Summary HTML exists, but `summary-data.json` and `index.md` are absent and `shared-context.md` contains stale MeuERP-007 references. These facts are recorded as baseline evidence and are not repaired in Phase 1.

## Phase 1 Closure

- T001–T007 discovery completed.
- No Summary agent prompt, workflow, HTML template, builder, validator, remediation utility, source artifact, or generated Summary artifact was modified.
- The existing PT/EN selector and `setLang()` path are preserved and documented for later implementation.
- Phase 2 is intentionally not started.

## Post-Implementation Regression Fixes

During feature `038-portuguese-manual-view` Phase 1 fixture validation, the first isolated end-to-end Summary generation and validation cycle exposed four regressions in the existing feature-037 implementation scope. These were not previously exercised successfully against `sophia` or `MeuERP-002`, whose project-specific issues blocked earlier smoke attempts.

1. **Normalization import scope — `NameError`**
   - **Location**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py:31–38`, failure at the Architectural Patterns call site formerly around line `3202`.
   - **Fix**: Moved the `summary_language` import for `normalize_architectural_pattern` and `normalize_text` outside the unrelated PyYAML `except ImportError` block, making the utilities available regardless of PyYAML availability.

2. **Normalization rule iteration — `ValueError`**
   - **Location**: `src/modules/ava-fabric-agents/summary/utils/summary_language.py:40` and `:153`.
   - **Fix**: Corrected `_NORMALIZATION_RULES` construction to iterate over dictionary `.items()`, preserving the intended `(source, target)` pair structure consumed by `for source, target in _NORMALIZATION_RULES` without changing mappings.

3. **Mermaid bundle placeholder — shared template substitution failure**
   - **Location**: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html:1996–1999` and builder substitution logic in `build_summary_comprehensive.py:3706`, `:4327–4341`, and `:8264–8265`.
   - **Fix**: Reverted an accidental uncommitted working-tree change from the malformed multiline `MERMAID_JS;` form to the committed exact `<script>{{MERMAID_JS}}</script>` form. The feature-037 English-default and selector changes in the same template were preserved.

4. **Static Portuguese labels in the default view — C8.1 language leak**
   - **Locations**: `summary-template.html:2220` (`Escopo`), `:2505` (`cobertura`), `:4775` (`Recursos Provisionados`), and `:4840` (`Ambientes de Deploy`).
   - **Fix**: Replaced the four hardcoded default HTML values with the existing English dictionary values: `Scope`, `coverage`, `Provisioned Resources`, and `Deploy Environments`. `I18N.pt`, `I18N.en`, the selector, and `setLang()` behavior were unchanged.

All four fixes were verified through the isolated feature-038 fixture. The generated HTML completed successfully, `var lang = "en"` was confirmed, C8.1/C8.2/C8.3 passed, and fixture source files remained byte-for-byte unchanged. This was the first successful full generate-plus-validate cycle exercising feature 037's shared builder, normalization utility, template substitution, and English-default gate end-to-end.
