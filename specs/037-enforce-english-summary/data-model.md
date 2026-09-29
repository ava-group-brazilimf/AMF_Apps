# Data Model: English-Only Summary Output

**Feature**: `037-enforce-english-summary`

This feature does not introduce a new persisted domain entity. It defines the data classification and validation model required to render existing Summary data in English without changing existing output contracts.

## 1. Summary Artifact

A generated Markdown or HTML artifact produced under the existing Summary output directory.

| Field               | Type        | Rules                                                                          |
| ------------------- | ----------- | ------------------------------------------------------------------------------ |
| `project_name`      | string      | Existing project identifier; preserve exact value.                             |
| `artifact_path`     | path string | Existing path and filename contract; preserve.                                 |
| `content`           | text        | Human-readable generated regions must be English-only.                         |
| `trace_id`          | string      | Propagate without mutation.                                                    |
| `validation_status` | enum        | Existing status plus language gate outcome; non-compliant output is not valid. |

## 2. Generated Text Region

A human-readable region emitted by a builder or template.

| Field              | Type          | Rules                                                                                              |
| ------------------ | ------------- | -------------------------------------------------------------------------------------------------- |
| `region_id`        | string        | Stable logical identifier for diagnostics, such as section/key/field.                              |
| `source_kind`      | enum          | `template_label`, `builder_fallback`, `source_derived_prose`, `report_text`, or `technical_value`. |
| `raw_value`        | string        | Input value before normalization; source artifacts remain unchanged.                               |
| `rendered_value`   | string        | Final value written to Markdown/HTML/embedded data.                                                |
| `language_status`  | enum          | `english`, `protected`, `empty`, `non_compliant`, or `not_applicable`.                             |
| `protected_tokens` | array[string] | Exact values exempt from translation and language detection.                                       |

## 3. Protected Technical Value

A value whose exact representation is required for correctness or traceability.

Protected categories:

- Code symbols, class names, and method names.
- File paths, URLs, Markdown references, and ADR filenames.
- Technical identifiers, project names, standard acronyms, and proper nouns.
- Exact traceability references and machine-readable IDs.
- Numeric, boolean, enum, and structured values when not prose.

Protected values are preserved byte-for-byte where the existing contract requires exactness. Surrounding explanatory prose remains subject to English normalization.

## 4. Language Compliance Result

The deterministic validation result for one generated artifact.

| Field                      | Type          | Rules                                                                   |
| -------------------------- | ------------- | ----------------------------------------------------------------------- |
| `artifact_path`            | path string   | Artifact checked.                                                       |
| `is_compliant`             | boolean       | True only when all inspectable generated prose is English or protected. |
| `offending_regions`        | array[object] | Region ID, location, and diagnostic evidence for each failure.          |
| `ignored_protected_values` | array[string] | Protected tokens excluded from language detection.                      |
| `mode`                     | enum          | `summary` or `remediation`.                                             |
| `blocking`                 | boolean       | True when non-compliance prevents valid/promotion status.               |

## 5. Architectural Pattern Record

Existing source-derived record rendered in the Architectural Patterns section.

| Field                | Type          | Language rule                                                                           |
| -------------------- | ------------- | --------------------------------------------------------------------------------------- |
| `pattern_name`       | string        | Preserve recognized technical/proper names; human-readable names must be English.       |
| `layer`              | string        | Normalize prose labels to English; preserve technical layer identifiers where required. |
| `justification`      | string        | Translate/normalize to English.                                                         |
| `reference_artifact` | string        | Preserve exact path/reference.                                                          |
| `trade_offs`         | array[string] | Translate/normalize prose; preserve technical tokens.                                   |
| `adr_reference`      | string        | Preserve exact ADR identifier/filename/reference.                                       |

## 6. Relationships

```text
Source Artifact (read-only)
        │
        ├── parsed into existing Summary data structures
        │
        └── Generated Text Region ──normalize/protect──> rendered artifact
                                                           │
                                                           └── Language Compliance Result

Architectural Pattern Record ──render──> Architectural Patterns section
                                         │
                                         └── language gate + structural checks

Summary Artifact ──rebuild──> Remediation Artifact
                              │
                              └── same Language Compliance Result contract
```

## 7. State Transitions

```text
RAW_SOURCE
  → CLASSIFIED (prose vs protected technical value)
  → NORMALIZED_ENGLISH
  → RENDERED
  → VALIDATED_COMPLIANT

RAW_SOURCE
  → CLASSIFIED
  → NORMALIZATION_UNSAFE or residual non-English prose
  → VALIDATED_NON_COMPLIANT
  → BLOCKED / remediation required
```
