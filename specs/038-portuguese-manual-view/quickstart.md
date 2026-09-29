# Quickstart: Validate Full-Quality Portuguese (PT-BR) Manual View Support

**Feature**: `038-portuguese-manual-view`

## Prerequisites

- Repository dependencies for the existing Summary pytest and Python utilities.
- A Summary fixture/project with `project-config.yaml`, source artifacts, and the existing HTML template.
- The existing output contract and selector/i18n assets.

## Validation scenarios

### 1. Default English regression

Run the existing Summary generation and validation path without a PT target.

Expected:

- Initial HTML state remains English (`var lang = "en"`).
- Existing C8 and all structural/content checks remain active.
- No PT language check blocks ordinary English generation.

### 2. Manual PT-BR view

Open the generated HTML, select `Português (PT-BR)`, and exercise `setLang('pt')`.

Expected:

- Static labels and all visible generated prose are coherent PT-BR.
- Architectural Patterns prose, fallbacks, recommendations, and dynamic rows are PT-BR.
- Switching back to English restores the unchanged English default-compatible view.

### 3. Protected values

Use Architectural Patterns data containing `reference_artifact`, `adr_reference`, URLs, paths, code symbols, acronyms, and traceability IDs embedded in prose.

Expected:

- Protected values are byte-for-byte unchanged.
- Surrounding prose is normalized to PT-BR.
- Protected values are excluded from false-positive diagnostics.

### 4. Explicit PT validation gate

Run Summary validation with the implementation's explicit PT target option against a compliant and a deliberately mixed-language fixture.

Expected:

- Compliant PT view passes.
- Unresolved/unsafe PT prose produces an error-level language finding.
- The result is blocking, not warning-only, and the command exits nonzero for the non-compliant fixture.

### 5. Targeted remediation gate

Run Summary-Remediation with the explicit PT target against an existing mixed-language artifact.

Expected:

- Rebuild uses the official builder/template path.
- PT content is normalized where safe.
- English default state, output paths, metadata, selector, and dictionaries remain intact.
- If PT findings remain, `errors_after > 0`, the report does not claim success, and the process exits nonzero.

### 6. Determinism and source preservation

Repeat generation, PT validation, and targeted remediation with identical inputs. Compare outputs and source hashes.

Expected:

- Normalized values and validation results are identical across runs.
- Source artifacts remain unchanged.
- Existing structural, Mermaid, placeholder, artifact-integrity, traceability, and content-completeness checks remain passing where the fixture is otherwise valid.

## Commands

Use the repository's existing entry points and the explicit target option established by implementation tasks:

- Summary generation: `build_summary_comprehensive.py --project <project>`
- Default validation: `validate_summary.py --project <project>`
- Targeted PT validation: `validate_summary.py --project <project> --language-target pt`
- Targeted PT remediation: `remediate_summary.py --project <project> --language-target pt`
- Summary tests: `python -m pytest tests/summary`

The exact option spelling must remain consistent between validator, remediation, agent instructions, and tests.

## Contract references

- [Language compliance schema](../037-enforce-english-summary/contracts/language-compliance.schema.json)
- [Data model](data-model.md)
- [Requirements](spec.md)
