# Quickstart: Validate English-Only Summary Output

**Feature**: `037-enforce-english-summary`

## Prerequisites

- Repository dependencies used by the existing Summary test and validation commands.
- A project fixture or test project with `context/project-config.yaml` and Summary source artifacts.
- Existing Summary output contracts and template assets available.

## Validation scenarios

### 1. English source and generated labels

Run the existing Summary builder for a fixture with English source artifacts. Confirm that:

- The HTML, Markdown index, and JSON-backed generated text are written to the existing Summary paths.
- The English-only language gate passes.
- Existing structural, traceability, placeholder, artifact-integrity, and Mermaid checks remain unchanged and pass.

### 2. Portuguese source-derived prose

Use a fixture whose source documentation contains Portuguese labels and prose in the fields consumed by Summary. Run Summary generation and confirm that:

- Source files are byte-for-byte unchanged.
- Human-readable rendered prose is English.
- Protected values such as paths, URLs, code symbols, project names, ADR filenames, acronyms, and exact references are unchanged.
- The language compliance result passes.

### 3. Architectural Patterns

Provide `tobe/patterns-applied.json` with Portuguese or mixed-language values in `justification` and `trade_offs`, plus technical references and ADR identifiers. Generate the Summary and inspect the Architectural Patterns section.

Expected result:

- English section title, headers, descriptions, justifications, trade-offs, and fallback labels.
- Exact references and identifiers preserved.
- Repeated runs with identical inputs produce the same normalized values and validation result.

### 4. Remediation of a legacy mixed-language Summary

Start with an existing Summary HTML containing Portuguese labels or prose. Run Summary-Remediation.

Expected result:

- The builder regenerates the Summary through the official template path.
- The regenerated artifact is English-only.
- The remediation report remains English-only for generated report text.
- A residual language violation causes a failing/blocking validation result and prevents a success report.

### 5. Ambiguous or unsafe text

Provide a source-derived value that cannot be safely normalized, while including protected technical tokens. Run generation and validation.

Expected result:

- Protected values are not falsely flagged.
- Unsafe residual prose is reported with an offending region.
- The artifact is not reported as valid until resolved.

## Commands

Use the repository's existing Summary and test entry points. The implementation should preserve the established builder and remediation invocations:

- Summary generation: `build_summary_comprehensive.py --project <project>`
- Summary remediation: `remediate_summary.py --project <project>`
- Summary validation: `validate_summary.py --project <project>`

The exact test command and fixture names should be recorded in implementation tasks after inspecting the repository's test configuration. Do not alter output paths or use source-repository mutation as part of validation.

## Contract reference

- Compliance result shape: [contracts/language-compliance.schema.json](contracts/language-compliance.schema.json)
- Data classification and protected-value rules: [data-model.md](data-model.md)
- Requirements and acceptance scenarios: [spec.md](spec.md)
