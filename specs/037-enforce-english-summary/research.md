# Research: English-Only Summary Output

**Feature**: `037-enforce-english-summary`
**Date**: 2026-08-07

## Decision 1 — Enforce the invariant at both generation and validation boundaries

**Decision**: Apply English-only instructions and normalization in `ava-summary` and `ava-summary-remediation`, then make `validate_summary.py` enforce the invariant as a blocking quality gate for generated Summary artifacts.

**Rationale**: The current implementation has language drift in multiple layers. The Summary agent contract still accepts `language: "pt" | "en"` with `pt` as the default; the workflow explicitly generates a bilingual Executive Summary; the HTML template contains a PT/EN language selector and many Portuguese defaults; and C8 validation skips drift checks unless the configuration language is `en`. Generation-only changes would not protect remediation or legacy artifacts, while validation-only changes would block output without repairing known sources.

**Alternatives considered**:

- Change only the agent prompts: insufficient because templates and Python fallbacks emit Portuguese independently.
- Change only the HTML template: insufficient because builder-generated rows, Markdown, `index.md`, remediation reports, and source-derived prose can still drift.
- Use a non-blocking warning: rejected because the specification requires non-compliant output not to be reported as valid.

## Decision 2 — Make English the fixed Summary language, not a user-selectable output mode

**Decision**: Remove or neutralize PT output paths within the Summary scope and treat English as the only generated language. Preserve technical identifiers and exact traceability values through explicit protected-value rules rather than translating them.

**Rationale**: The specification explicitly excludes multilingual output and user-selectable language configuration. The current template's `pt` default, selector, bilingual executive summary, and PT i18n values directly conflict with FR-01 through FR-09.

**Alternatives considered**:

- Keep the selector but default to English: rejected because users could still obtain Portuguese output.
- Keep bilingual data and hide PT at render time: rejected because generated artifacts and embedded data would still contain non-English content.

## Decision 3 — Normalize human-readable source-derived text before rendering

**Decision**: Introduce a deterministic, local normalization boundary in the Summary builder for human-readable source-derived prose and labels. The boundary must leave protected technical values unchanged and must return an explicit non-compliance result when text cannot be safely normalized.

**Rationale**: Source artifacts are read-only and may contain Portuguese or mixed-language content. The builder currently passes several values through directly, including TO-BE pattern `name`, `layer`, `justification`, `reference_artifact`, `trade_offs`, and `adr_reference`, as well as parsed Markdown content. A single normalization boundary provides consistent behavior across HTML rows, Markdown, and embedded data while respecting preservation rules.

**Alternatives considered**:

- Mutate source files before Summary generation: prohibited by the specification.
- Translate every string indiscriminately: unsafe for class names, paths, URLs, ADR filenames, acronyms, and exact references.
- Rely only on a stopword detector: useful as a gate but not sufficient to translate or normalize source-derived prose.

## Decision 4 — Treat Architectural Patterns as a first-class regression target

**Decision**: Add focused extraction/rendering/validation coverage for the TO-BE Architectural Patterns data and its visible table, including headers, descriptions, justifications, trade-offs, references, and ADR references.

**Rationale**: The current builder directly interpolates pattern fields into HTML and includes a Portuguese fallback message. The HTML template also contains mixed-language labels. This is the recurring defect named in the specification and must be tested independently from broad Summary checks.

**Alternatives considered**:

- Validate only the final HTML globally: rejected because a global pass can obscure which pattern field regressed.
- Test only the i18n dictionary: rejected because row values are source-derived and bypass static labels.

## Decision 5 — Share one language-validation contract between Summary and remediation

**Decision**: Implement the language check in the existing Summary validation path and invoke that same validator after remediation rebuild. Include the result in existing validation/report output without changing existing artifact paths or adding an incompatible output contract.

**Rationale**: `remediate_summary.py` already calls `validate_summary._run_checks()` before and after rebuild, computes failures, and writes remediation reports. Reusing this path ensures remediation cannot report success while language errors remain and avoids a second divergent validator.

**Alternatives considered**:

- Add a separate remediation-only language script: rejected due to drift risk and duplicate logic.
- Add a new required output artifact solely for language metadata: unnecessary and could break downstream consumers; existing validation results can carry the gate result.

## Decision 6 — Preserve compatibility metadata and protected values

**Decision**: Keep existing Summary output filenames, directories, `summary-data.json` structure, `index.md` location, `trace_id`, artifact paths, identifiers, URLs, Markdown references, and technical names compatible. Update only human-readable labels/content and validation status needed for the invariant.

**Rationale**: FR-11 and the output contract require compatibility. The implementation must distinguish prose from values whose exact form is semantically significant.

**Alternatives considered**:

- Rename or relocate outputs to signal the language policy: rejected as unrelated and breaking.
- Translate filenames and identifiers: explicitly prohibited by FR-12 and the preservation rules.

## Current Behavior Findings

1. `summary-agent.md` describes a configurable `language: "pt" | "en"` input with a Portuguese default and instructs the builder to generate a bilingual Executive Summary.
2. `summary-remediation-agent.md` delegates rebuilds to `build_summary_comprehensive.py` and validation to `validate_summary.py`, but contains Portuguese operational/reporting text and no English-only invariant.
3. `step-03-build-html.md` explicitly specifies PT/EN Executive Summary generation.
4. `step-04-validate-deliver.md` specifies Portuguese fallback content for `index.md` and other generated messages.
5. `summary-template.html` contains a PT/EN selector, Portuguese defaults, Portuguese section labels, and PT i18n values; this permits a Portuguese final artifact and language switching.
6. `build_summary_comprehensive.py` contains Portuguese fallback strings and directly interpolates source-derived pattern fields into HTML. It also has hardcoded Portuguese TO-BE fallback values such as pending wave labels and approval labels.
7. `validate_summary.py` C8 is conditional on `language == "en"`, so the default `pt` mode bypasses the relevant embedded-content drift check. C8.3 currently requires both PT and EN i18n values, which conflicts with an English-only artifact requirement.
8. `remediate_summary.py` rebuilds and revalidates through the existing builder/validator, making it the correct integration point for enforcing the same gate after repair.

## Unresolved Implementation Questions Resolved for Planning

- **Translation dependency**: Do not introduce a remote or nondeterministic translation service. Use deterministic local mappings/normalization for generated labels and a controlled normalization strategy for supported source-derived prose; unresolved unsafe text must fail the language gate rather than be silently accepted.
- **Technical values**: Classify protected values by field/context and preserve them exactly. The language validator must ignore protected tokens and machine-readable identifiers while inspecting surrounding prose.
- **Scope boundary**: Changes are limited to `src/modules/ava-fabric-agents/summary/**`, Summary-specific tests, and feature planning artifacts. No unrelated F1-F7 agents or Mermaid/layout/navigation behavior is planned.
