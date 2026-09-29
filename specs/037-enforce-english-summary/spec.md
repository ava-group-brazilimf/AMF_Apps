# Enforce English-Default Summary Output

**Feature Branch**: `037-enforce-english-summary`
**Created**: 2026-08-07
**Status**: Draft
**Change Type**: bugfix
**Input**: Feature description: Enforce English as the default output state in Summary and Summary-Remediation generation.

> This specification is written in English. It defines behavior and outcomes without prescribing implementation details.

## 1. Agent Identity

| Field        | Value                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent ID** | `ava-summary` and `ava-summary-remediation`                                                                                                 |
| **Version**  | PATCH version bump for both existing agents                                                                                                 |
| **Phase**    | F8                                                                                                                                          |
| **Module**   | `summary`                                                                                                                                   |
| **Role**     | Generate and repair Summary artifacts with English as the default rendered language while preserving the existing optional Portuguese view. |
| **Skill**    | `ava-summary` and `ava-summary-remediation`                                                                                                 |
| **Dispatch** | User-facing and orchestrator-dispatched                                                                                                     |

## 2. Scope and Language Policy

The Summary and Summary-Remediation pipelines shall generate and initially render artifacts in English by default. The existing Portuguese/English selector and PT/EN i18n dictionaries in the Summary HTML template are intentional and must remain fully functional as an optional, user-triggered viewing capability. The English compliance policy applies to the default rendered/generated state, without user-initiated language switching.

Source artifacts may contain Portuguese or mixed-language content. Source artifacts themselves are not modified. During Summary generation or remediation, source-derived human-readable text shall be translated or normalized into English before it is rendered in the default English view. The existing Portuguese view is not required to normalize source-derived text beyond preserving its current selector/i18n behavior.

The default-language policy applies consistently and deterministically to every supported Summary execution mode and to every remediation run. Manual switching through the existing selector remains supported and is outside the compliance gate for the default rendered state. Adding languages or building new multilingual capabilities is out of scope.

## 3. Output Contract

Existing Summary and Summary-Remediation output contracts remain unchanged. The change adds a default-language invariant: every generated Summary artifact must open/render in English by default, while preserving the existing PT/EN selector, required structural metadata, traceability metadata, and validation metadata.

## 4. User Scenarios (Given-When-Then)

### Scenario 1 - Summary generation defaults to English (Priority: P1)

**Story**: As a solution architect or reviewer, I want Summary artifacts to be entirely in English so that global stakeholders can consume them consistently.

**Why this priority**: Mixed-language deliverables reduce clarity and professional quality and can block international review.

**Acceptance Scenarios**:

1. **Given** a valid project with source documentation containing Portuguese or mixed-language terms, **When** the Summary pipeline generates its artifacts, **Then** every generated section title, table header, table value, description, justification, trade-off, recommendation, and narrative passage is rendered in English.
2. **Given** a freshly generated Summary artifact is opened without user interaction or a script-triggered switch to Portuguese, **When** the initial view is rendered, **Then** all default-state labels, headings, table headers, and generated prose are in English, including Architectural Patterns headers `Pattern`, `Layer`, `Justification`, `Reference`, `Trade-offs`, and `ADR`.
3. **Given** source artifacts contain Portuguese content, **When** the Summary renders source-derived content, **Then** the source files remain unchanged and the rendered content uses English equivalents.
4. **Given** a freshly generated Summary artifact is opened, **When** the user manually uses the existing PT/EN selector, **Then** the selector remains functional and allows switching to the Portuguese view without being removed or disabled.

### Scenario 2 - Architectural Patterns defaults to English (Priority: P1)

**Why this priority**: Architectural Patterns is a recurring source of mixed-language output and is explicitly required by stakeholders.

**Acceptance Scenarios**:

1. **Given** architectural pattern data includes Portuguese headers, descriptions, trade-offs, justifications, or references, **When** the Architectural Patterns section is rendered, **Then** all visible text is in English.
2. **Given** the Architectural Patterns section is rendered across repeated executions with the same inputs, **When** the outputs are compared, **Then** the language treatment is consistent and deterministic.

### Scenario 3 - Summary-Remediation preserves the language invariant (Priority: P1)

**Story**: As a reviewer, I want remediation runs to repair default-view language inconsistencies instead of preserving them so that regenerated artifacts open consistently in English.

**Why this priority**: Remediation is a downstream path and can otherwise reintroduce or retain mixed-language content.

**Acceptance Scenarios**:

1. **Given** an existing Summary contains Portuguese or mixed-language generated content, **When** Summary-Remediation regenerates the artifact, **Then** the regenerated text-bearing content in the default rendered state is English.
2. **Given** remediation completes, **When** its validation finishes, **Then** the language invariant is evaluated as part of the quality result and a non-compliant artifact cannot be reported as valid.

### Scenario 4 - Missing or ambiguous source language (Priority: P2)

**Why this priority**: The pipeline must remain safe and deterministic when source text cannot be confidently normalized.

**Acceptance Scenarios**:

1. **Given** a source value is empty, non-textual, or not suitable for translation, **When** the Summary renders it, **Then** structural identifiers and required technical values are preserved without inventing business content, and surrounding explanatory text remains in English.
2. **Given** a generated text value cannot be normalized to English with sufficient confidence, **When** validation runs, **Then** the artifact is flagged as non-compliant or blocked rather than silently accepted as compliant with the English-default policy.

### Scenario 5 - Quality gate and traceability (Priority: P1)

**Why this priority**: Language enforcement must not weaken existing Summary quality, safety, or traceability controls.

**Acceptance Scenarios**:

1. **Given** a Summary or remediation execution completes, **When** its existing validation and reporting run, **Then** the language result is included without removing structural validation, traceability, or artifact-integrity checks.
2. **Given** an artifact fails the default rendered-state English check, **When** the pipeline evaluates promotion readiness, **Then** the artifact is not considered ready until the language issue is resolved.

## 5. Functional Requirements

- **FR-01**: The Summary pipeline shall generate and initially render all generated text in English by default; the existing Portuguese selector and i18n dictionary shall remain functional.
- **FR-02**: The Summary-Remediation pipeline shall regenerate artifacts whose default rendered/generated state is English while preserving the existing Portuguese selector and i18n behavior.
- **FR-03**: Section names and headings in the default rendered state shall be English.
- **FR-04**: Table column headers and generated table labels in the default rendered state shall be English.
- **FR-05**: Generated descriptions, justifications, recommendations, trade-offs, and narrative content in the default rendered state shall be English.
- **FR-06**: Portuguese or mixed-language source-derived human-readable text shall be translated or normalized into English before rendering in the default view, without modifying source artifacts; the existing Portuguese view is not required to normalize that source-derived text.
- **FR-07**: The default rendered/generated Markdown and HTML state shall not contain Portuguese sentences, labels, headings, or mixed-language generated passages.
- **FR-08**: The default-language policy shall cover all Summary sections, including Architectural Patterns, Technology Framework, Solution Structure, Migration Wave Plan, ADR references, and related generated tables and narrative descriptions.
- **FR-09**: The default-language policy shall apply to every supported Summary generation mode and every remediation-generated artifact; manual switching through the existing selector is outside the compliance gate.
- **FR-10**: Language compliance shall be evaluated by a deterministic validation rule or equivalent quality gate, and non-compliant output shall not be reported as valid.
- **FR-11**: Existing output paths, artifact names, traceability metadata, and non-language quality checks shall remain compatible unless a separate approved change is documented.
- **FR-12**: The implementation shall preserve technical identifiers, code symbols, file paths, URLs, standard acronyms, and other values whose meaning would be damaged by translation, while keeping surrounding explanatory text in English.
- **FR-13**: The default rendered/generated state of Summary and Summary-Remediation artifacts, without user-initiated language switching, shall be English. The existing Portuguese language selector and PT/EN i18n dictionary shall remain functional and shall not be removed.

## 6. Edge Cases

- Source artifacts contain Portuguese labels in nested objects or generated tables.
- Source artifacts contain mixed Portuguese and English in the same paragraph or table row.
- Source artifacts contain empty, null, numeric, coded, or technical identifier values.
- Existing Summary HTML is from an older template or builder and contains legacy Portuguese text.
- Remediation repairs structural issues while also needing to normalize language.
- A technical name, proper noun, URL, file path, code symbol, or acronym resembles a non-English term but must remain unchanged.
- The same source inputs are processed repeatedly and must yield consistent language treatment.

## 7. Key Entities

- **Summary Artifact**: A generated Markdown or HTML document produced by the Summary pipeline.
- **Remediation Artifact**: A regenerated Summary artifact produced by Summary-Remediation.
- **Source Artifact**: Existing project documentation or structured data consumed by Summary generation; it remains read-only.
- **Language Compliance Result**: The validation outcome indicating whether generated text in the default rendered state satisfies the English-default policy; the Portuguese view reached through the existing selector is not evaluated by this result.
- **Generated Text Region**: A heading, label, table cell, narrative passage, or other human-readable content emitted by the pipeline.

## 8. Dependencies

| Dependency                                    | Agent or component                                         | Reason                                               |
| --------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------- |
| Summary generation                            | `ava-summary` and its existing generation workflow         | Produces the primary generated artifacts             |
| Summary remediation                           | `ava-summary-remediation` and its existing repair workflow | Regenerates artifacts that must retain the invariant |
| Summary validation                            | Existing Summary validation quality gate                   | Must enforce and report language compliance          |
| Shared Summary templates and extraction logic | Existing Summary module assets                             | May provide generated labels and source-derived text |
| Existing artifact contracts                   | Summary output contract and downstream consumers           | Must remain compatible                               |

## 9. Exclusions

- Modifying source artifacts or translating the legacy repository.
- Removing the existing Portuguese/English language selector or PT i18n dictionary from the Summary template.
- Building new multilingual features beyond the existing selector, such as additional languages.
- Rewriting unrelated F1-F7 agent content that is not emitted by Summary or Summary-Remediation.
- Translating technical identifiers, code symbols, URLs, file paths, or proper nouns when preservation is required for correctness.
- Changing Summary layout, navigation, Mermaid behavior, or unrelated artifact-generation rules except where necessary to enforce English as the default rendered output, without restricting the existing Portuguese selector view.

## 10. Assumptions

- English is the fixed default rendered/generated language for Summary and Summary-Remediation artifacts.
- The existing Portuguese/English selector and PT/EN i18n dictionaries remain supported for manual viewing after initial render.
- Existing Summary output contracts and artifact locations are authoritative.
- Source artifacts are read-only inputs.
- Existing structural and artifact-integrity validation remains in force.
- English normalization can be applied to human-readable generated text while preserving technical values.
- Any language detector or vocabulary policy must avoid treating technical identifiers and proper nouns as prose.

## Success Criteria

| Criterion                 | Measure                                                                                                                                                    |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| English default output    | 100% of generated Summary and Summary-Remediation artifacts open/render with English headings, labels, and narrative text before user-initiated switching. |
| Section coverage          | 100% of listed Summary sections and generated tables use English headings, labels, and narrative text in the default view.                                 |
| Source preservation       | 100% of source artifacts remain unchanged by Summary or remediation execution.                                                                             |
| Regression safety         | Existing Summary artifact-integrity and structural validation checks continue to pass for supported inputs.                                                |
| Determinism               | Repeated runs with identical inputs produce the same language-normalization behavior and validation result.                                                |
| Remediation effectiveness | A non-compliant existing Summary is regenerated into a compliant artifact, or the run is explicitly blocked with a reported language failure.              |
| Review usability          | Reviewers can inspect the initial generated view in English, while the existing manual PT/EN selector remains functional.                                  |

## Clarifications

### Session 2026-08-07

- Q: Should the existing Portuguese/English selector and PT/EN i18n dictionaries be removed to enforce English-only output? → A: No; preserve them and enforce English only for the default rendered/generated state.
