# Research: Full-Quality Portuguese (PT-BR) Manual View Support

**Feature**: `038-portuguese-manual-view`
**Date**: 2026-08-07

## Decision 1 — Keep English default and add an explicit PT target

**Decision**: Preserve `var lang = "en"` and all existing selector/`setLang()` behavior. Add an explicit language target for validation and targeted remediation; absent target means the existing English-default path.

**Rationale**: The template already supports the selector and both dictionaries. The feature changes the quality of the manually selected view, not the default policy. An explicit target prevents the PT gate from unexpectedly blocking ordinary English generation.

**Alternatives considered**:

- Make PT validation run on every build: rejected because it would change the English-default execution contract and add unnecessary blocking.
- Replace the selector with a server-side language option: rejected because it would alter existing interaction semantics.

## Decision 2 — Extend the existing deterministic Summary language boundary

**Decision**: Extend `summary_language.py` with target-aware normalization, protected-token masking, PT-BR vocabulary/normalization rules, and target-specific diagnostics. Reuse the same boundary from builder, template data preparation, validator, and remediation rather than introducing remote translation.

**Rationale**: The repository already has a Summary-local deterministic normalization utility used by the English path. Extending it keeps output deterministic, offline, testable, and consistent across HTML, Markdown, embedded data, and reports.

**Alternatives considered**:

- Add a translation API or LLM: rejected by the specification and incompatible with offline deterministic execution.
- Normalize only visible static labels: rejected because source-derived prose is the stated defect.
- Translate raw HTML after rendering: rejected because it risks altering protected identifiers and diverging from JSON/Markdown outputs.

## Decision 3 — Protect technical values before either normalization or detection

**Decision**: Preserve `reference_artifact`, `adr_reference`, code symbols, class/method names, paths, URLs, Markdown references, project names, proper nouns, acronyms, exact traceability IDs, and machine-readable values by field/context and token masking. Validate byte-for-byte preservation separately.

**Rationale**: Existing `summary_language.py` already masks several protected patterns and explicitly protects pattern reference fields. PT-BR normalization must use the same safety boundary, expanded where focused tests demonstrate a missing category.

**Alternatives considered**:

- Apply word substitutions to every string: rejected because it can corrupt technical values.
- Ignore all source-derived fields: rejected because prose quality is in scope.

## Decision 4 — Make PT compliance error-level and target-scoped

**Decision**: Add a target-aware compliance check to `validate_summary.py`. When `language_target=pt` is explicitly requested, unresolved/mixed/unsafe PT findings are error-level, blocking, and included in the same validation result/error accounting used by C8. Targeted remediation must leave `errors_after > 0` and exit nonzero when PT findings remain. When no PT target is supplied, the existing English C8 behavior remains the only language gate.

**Rationale**: The requested behavior explicitly requires the same blocking semantics as English C8, not warning-only treatment. Reusing `Check.level == "error"`, `run_all()` exit handling, and remediation `errors_after` prevents false success.

**Alternatives considered**:

- Warning-only PT diagnostics: rejected explicitly; it would allow a non-compliant targeted remediation to report success.
- Separate non-blocking report: rejected because it would diverge from C8 semantics.

## Decision 5 — Use the official builder/template path for targeted remediation

**Decision**: Add a PT target option to `remediate_summary.py` and pass it through the official builder/validator path. Preserve the English default state and write compatible remediation reports; targeted PT validation failures must be reflected in `errors_after` and the process exit code.

**Rationale**: Remediation already rebuilds through `build_summary_comprehensive.py` and validates in-process. Extending this flow avoids hand-patching generated HTML and preserves idempotence and existing output contracts.

**Alternatives considered**:

- Patch generated HTML directly: rejected because it would diverge from future rebuilds and risk changing the English default.
- Add a second remediation implementation: rejected due to duplicate logic and drift.

## Decision 6 — Preserve selector dictionaries while localizing dynamic content

**Decision**: Keep selector markup, `setLang()`, `I18N.pt`, and `I18N.en` structurally intact. Render dynamic source-derived values through target-aware data or language-specific render fields so that switching changes human-readable prose without changing protected values or the English default data contract.

**Rationale**: Static PT labels already exist, but builder-injected rows bypass the dictionary. Dynamic localization must address those rows while preserving the interaction contract.

**Alternatives considered**:

- Remove or rebuild the dictionaries: rejected by FR-06 and risks breaking existing selector behavior.
- Store only one translated value: rejected because both English default and PT manual views must remain available.

## Evidence reviewed

- `specs/037-enforce-english-summary/{spec.md,research.md,plan.md,data-model.md,quickstart.md}`
- `src/modules/ava-fabric-agents/summary/utils/summary_language.py`
- `build_summary_comprehensive.py`, `validate_summary.py`, `remediate_summary.py`
- `summary-template.html` selector, i18n dictionaries, `setLang()`, and default marker
- `summary/module.yaml`, existing Summary workflow and agent contracts
- `tests/summary/` existing pytest fixtures and tests
