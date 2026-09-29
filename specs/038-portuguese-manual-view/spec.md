# Full-Quality Portuguese (PT-BR) Manual View Support

**Feature Branch**: `038-portuguese-manual-view`
**Created**: 2026-08-07
**Status**: Draft
**Change Type**: modify-existing
**Input**: Feature description: Full-Quality Portuguese (PT-BR) Manual View Support

> This specification is written in English. It defines user-visible behavior and outcomes without prescribing implementation details.

## 1. Scope and Language Policy

The Summary and Summary-Remediation pipelines shall preserve English as the default rendered and generated language, exactly as established by feature 037. This feature improves only the Portuguese view selected manually through the existing language selector or `setLang('pt')` path.

When Portuguese is selected, all generated human-readable content must be complete, consistent, and well-formed Brazilian Portuguese (PT-BR), including static labels, section titles, table headers, source-derived prose, fallback text, recommendations, Architectural Patterns content, and equivalent free-text fields throughout the Summary. Protected technical values remain unchanged.

Portuguese normalization must be deterministic and local. Source artifacts remain read-only, and no remote or LLM translation service is introduced. If content cannot be safely normalized without inventing business meaning, it must be preserved only where it is a protected value or reported as non-compliant rather than silently presented as valid PT-BR.

## 2. User Scenarios (Given-When-Then)

### Scenario 1 - Complete Portuguese manual view (Priority: P1)

**Story**: As a solution architect or reviewer, I want the manually selected Portuguese Summary view to be fully coherent in PT-BR so that I can trust it as a first-class alternative to the English view.

**Why this priority**: A mixed-language manual view undermines review quality and stakeholder confidence.

**Acceptance Scenarios**:

1. **Given** a freshly generated Summary with English or mixed-language source-derived content, **When** the reviewer selects Portuguese using the existing selector, **Then** all visible section titles, table headers, labels, and human-readable prose are rendered in well-formed PT-BR.
2. **Given** the Portuguese view is active, **When** the reviewer inspects Architectural Patterns, **Then** pattern names that are prose, layers, descriptions, justifications, trade-offs, recommendations, and surrounding narrative are coherent PT-BR.
3. **Given** the reviewer returns to English through the existing selector, **When** the English view is displayed, **Then** English remains the default-compatible view and its content is unchanged by Portuguese normalization.

### Scenario 2 - Deterministic source-derived normalization (Priority: P1)

**Story**: As a reviewer, I want source-derived prose normalized consistently without fabricated business content so that Portuguese results remain trustworthy.

**Why this priority**: Source-derived text is the main cause of mixed-language and inconsistent output.

**Acceptance Scenarios**:

1. **Given** source data contains English prose, mixed Portuguese/English prose, or known legacy labels, **When** the Portuguese view renders it, **Then** deterministic local normalization produces PT-BR equivalent wording where safe.
2. **Given** a source value is empty, null, numeric, coded, or otherwise not safely translatable, **When** the Portuguese view renders it, **Then** it does not invent business content and preserves the value only when its field contract allows it.
3. **Given** identical source inputs are processed repeatedly, **When** Portuguese normalization is applied, **Then** the same visible result and compliance outcome are produced each time.

### Scenario 3 - Protected technical values (Priority: P1)

**Story**: As a solution architect, I want technical references preserved exactly while prose is localized so that the Portuguese view remains traceable and actionable.

**Why this priority**: Translating technical identifiers could break navigation, traceability, or technical meaning.

**Acceptance Scenarios**:

1. **Given** Portuguese rendering includes code symbols, class names, method names, file paths, URLs, technical identifiers, ADR filenames, Markdown references, project names, proper nouns, standard acronyms, `reference_artifact`, or `adr_reference`, **When** the view is generated, **Then** each protected value remains byte-for-byte identical to its source value.
2. **Given** protected values resemble Portuguese or English words, **When** compliance validation runs, **Then** they are excluded from false-positive language findings while surrounding prose is still evaluated.

### Scenario 4 - Explicit Portuguese compliance validation (Priority: P1)

**Story**: As a QA reviewer, I want an explicit PT-BR compliance check so that Portuguese quality can be assessed without changing the English default gate.

**Why this priority**: Manual-view quality needs an auditable result equivalent to the existing English-default quality bar.

**Acceptance Scenarios**:

1. **Given** a validation or remediation run explicitly targets the Portuguese view, **When** validation completes, **Then** it evaluates Portuguese text-bearing regions and reports deterministic diagnostics for non-compliant content.
2. **Given** validation targets only the English default view, **When** it completes, **Then** the existing English compliance behavior remains unchanged and the Portuguese gate does not block English generation.
3. **Given** the Portuguese compliance check finds unresolved mixed-language or unsafe prose, **When** the quality result is produced, **Then** the Portuguese view is reported as non-compliant and cannot be presented as fully quality-assured.

### Scenario 5 - Portuguese-aware remediation (Priority: P1)

**Story**: As a reviewer, I want Summary-Remediation to repair Portuguese-view quality without changing the English default state.

**Why this priority**: Existing artifacts may contain legacy mixed-language Portuguese content and need a safe repair path.

**Acceptance Scenarios**:

1. **Given** an existing Summary contains incomplete or mixed-language Portuguese-view content, **When** remediation explicitly targets Portuguese quality, **Then** the official builder/template path normalizes the Portuguese view and the post-remediation Portuguese check passes or reports explicit unresolved findings.
2. **Given** Portuguese remediation completes, **When** the English default state is inspected, **Then** its language, content, output paths, metadata, and compliance result remain unaffected.
3. **Given** remediation cannot safely normalize a non-protected prose value, **When** it completes, **Then** it does not invent business content and reports the remaining finding rather than claiming success.

## 3. Functional Requirements

- **FR-01**: English shall remain the default rendered and generated language for all Summary and Summary-Remediation artifacts, unchanged from feature 037.
- **FR-02**: Selecting Portuguese through the existing selector or `setLang('pt')` shall render all generated text-bearing content in complete, well-formed PT-BR.
- **FR-03**: Portuguese rendering shall cover static labels, section titles, table headers, empty states, status labels, fallback text, recommendations, narrative passages, and source-derived prose across all Summary sections.
- **FR-04**: Source-derived human-readable prose, including Architectural Patterns fields such as `pattern_name`, `layer`, `justification`, and `trade_offs`, shall be normalized into PT-BR using deterministic local rules without remote or LLM translation.
- **FR-05**: Protected technical values, including code symbols, class names, method names, file paths, URLs, technical identifiers, ADR filenames, Markdown references, project names, proper nouns, standard acronyms, exact traceability references, `reference_artifact`, and `adr_reference`, shall remain byte-for-byte identical.
- **FR-06**: Portuguese normalization shall preserve the existing selector interaction, `setLang()` behavior, PT dictionary, EN dictionary, output contracts, and manual switching semantics.
- **FR-07**: An explicit Portuguese language-compliance validation mode shall inspect the manually selected Portuguese view using a quality bar equivalent to the English-default gate, while remaining non-blocking for default English generation unless Portuguese is explicitly requested.
- **FR-08**: Portuguese compliance diagnostics shall identify the artifact, view/region, and offending non-compliant or unsafe prose, while excluding protected values and machine-readable identifiers from false positives.
- **FR-09**: Summary-Remediation shall be able to target Portuguese-view quality, reuse the official generation and validation path, report unresolved findings, and preserve the English default state.
- **FR-10**: Existing structural, placeholder, artifact-integrity, Mermaid, traceability, content-completeness, and English-default checks shall remain active and compatible.
- **FR-11**: Source artifacts shall remain read-only and no generated process shall modify source content to achieve Portuguese normalization.
- **FR-12**: Repeated generation, switching, validation, and remediation with identical inputs and settings shall produce deterministic visible results and validation outcomes.
- **FR-13**: No language beyond English and PT-BR, no remote translation, and no removal or restructuring of the existing selector or dictionaries shall be introduced.

## 4. Edge Cases

- Source prose is entirely English, entirely Portuguese, or mixed within one field.
- A source-derived field contains technical terms that must remain exact within Portuguese prose.
- A protected path, URL, ADR filename, acronym, proper noun, or traceability reference resembles ordinary prose.
- The value is empty, null, numeric, coded, serialized, or otherwise unsafe to translate.
- Portuguese content appears in nested source objects, generated tables, fallback rows, Markdown, or embedded HTML data.
- An older Summary artifact contains legacy mixed-language content and is remediated with Portuguese targeting enabled.
- Portuguese targeting is omitted; English default generation must still succeed under feature 037 behavior.
- A Portuguese compliance check is run against an artifact that lacks sufficient renderable content; it must report an explicit, actionable result.

## 5. Key Entities

- **Summary Artifact**: A generated HTML, Markdown, JSON-backed, or report artifact produced by Summary.
- **Portuguese Manual View**: The rendered Summary state selected through the existing selector or `setLang('pt')`.
- **Protected Technical Value**: A value whose exact bytes must be preserved, such as a path, URL, code symbol, identifier, ADR filename, or traceability reference.
- **Source-Derived Prose**: Human-readable text read from project artifacts and displayed in Summary sections.
- **Language Compliance Result**: A deterministic result describing whether a targeted rendered view satisfies its requested language quality bar.
- **Language Target**: The explicitly requested validation/remediation target (`en` for default English or `pt` for manual PT-BR view).
- **Normalization Finding**: A diagnostic for mixed-language, unsafe, unresolved, or otherwise non-compliant human-readable content.

## 6. Dependencies

| Dependency                                                               | Reason                                                                         |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Existing Summary agent and generation workflow                           | Produces the HTML and generated supporting artifacts.                          |
| Existing Summary template, selector, `setLang()`, and PT/EN dictionaries | Provides the manual view and interaction that must remain functional.          |
| Summary builder and source extraction logic                              | Supplies shared generated labels and source-derived prose.                     |
| Summary validator and existing C8 gate                                   | Supplies the English quality baseline and compatible result/report structures. |
| Summary-Remediation utility and agent                                    | Rebuilds and validates existing artifacts for explicit PT-BR targeting.        |
| Existing Summary tests and fixtures                                      | Provide regression coverage for default English and manual PT behavior.        |

## 7. Exclusions

- Changing English from the default state established by feature 037.
- Removing, disabling, or restructuring the existing PT/EN selector, `setLang()` function, or i18n dictionaries.
- Supporting languages other than English and PT-BR.
- Remote, network-based, or LLM translation.
- Modifying source artifacts or the legacy repository.
- Translating protected technical values.
- Redesigning Summary layout, navigation, Mermaid behavior, or unrelated pipeline phases.

## 8. Assumptions

- The existing PT/EN dictionaries provide the baseline for static Portuguese labels and remain authoritative for interaction semantics.
- Deterministic local normalization rules can cover approved human-readable vocabulary and can flag unsafe or unknown prose.
- A Portuguese compliance run is explicitly requested by a validation/remediation option or equivalent targeted execution context; it does not run as a blocking default-English gate.
- Existing output paths, filenames, metadata, traceability fields, and validation result structures remain authoritative.
- The official Summary builder/template path remains the only supported generation path for remediated artifacts.

## 9. Success Criteria

| Criterion                  | Measure                                                                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Portuguese completeness    | 100% of visible generated labels, headings, table headers, fallback text, and safely normalizable prose in an explicitly targeted Portuguese view pass PT-BR compliance. |
| Protected-value integrity  | 100% of protected technical values remain byte-for-byte identical to source values after generation, switching, validation, and remediation.                             |
| Default-language stability | 100% of Summary and Summary-Remediation runs without an explicit PT target retain the English default state and existing English compliance result.                      |
| Determinism                | Repeated runs with identical inputs and language target produce identical normalized content and validation outcomes.                                                    |
| Remediation quality        | Targeted Portuguese remediation either passes the PT-BR gate or blocks/reports every unresolved finding; it never claims full success silently.                          |
| Interaction compatibility  | Existing selector and `setLang()` switching remain functional in all regression scenarios.                                                                               |
| Regression safety          | Existing structural, artifact-integrity, Mermaid, placeholder, traceability, content-completeness, and English-default checks continue to pass.                          |
| Source preservation        | Source artifacts remain unchanged after generation and remediation.                                                                                                      |

## 10. Change Impact and Versioning

This is a behavior change to the existing Summary and Summary-Remediation agents and supporting Summary utilities. Existing input and output contracts remain compatible; agent versions should receive the repository-appropriate non-breaking version increment during planning. No new agent or module is introduced. Existing Summary module registration and user-facing skills remain in place unless implementation discovery identifies a required metadata update.

## 11. Quality Gate Requirements

- [ ] Existing Summary and Summary-Remediation contracts remain compatible.
- [ ] English remains the default generated/rendered state.
- [ ] Existing selector, `setLang()`, and both dictionaries remain present and functional.
- [ ] PT-BR validation is explicit and non-blocking for default English unless requested.
- [ ] Nominal, edge, protected-value, validation-gate, and remediation scenarios are covered.
- [ ] Protected technical values are preserved exactly.
- [ ] Source artifacts remain read-only.
- [ ] Deterministic local normalization is used; no remote or LLM translation is introduced.
- [ ] Existing structural and English-default quality checks remain active.
- [ ] No `[NEEDS CLARIFICATION]` markers remain.

## Clarifications

None required. The feature description defines the default-language policy, manual interaction path, protected-value rules, validation mode, and remediation boundary sufficiently for planning.
