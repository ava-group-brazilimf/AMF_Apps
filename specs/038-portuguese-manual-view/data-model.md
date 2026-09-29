# Data Model: Full-Quality Portuguese (PT-BR) Manual View Support

**Feature**: `038-portuguese-manual-view`

This feature extends existing Summary data handling. It introduces no new persisted business entity and does not change existing output paths or source artifacts.

## 1. Language Target

| Field             | Type              | Rules                                                                                                                                                                   |
| ----------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `language_target` | internal/CLI enum | Internal parameter and CLI input (`--language-target`) accepting `en` or `pt`; it is not serialized as a result field. Omitted means the existing English default path. |
| `explicit`        | boolean           | True only when the caller requested PT-BR targeting. PT validation is non-blocking for ordinary English generation only because it is not invoked.                      |
| `blocking`        | boolean           | True for unresolved target-language findings. For explicit `pt`, this must be error-level and block exactly like C8.                                                    |

## 2. Summary Artifact

| Field               | Type   | Rules                                                                                   |
| ------------------- | ------ | --------------------------------------------------------------------------------------- |
| `project_name`      | string | Preserve exact project identifier.                                                      |
| `artifact_path`     | path   | Preserve existing path and filename contract.                                           |
| `content`           | text   | Default rendered state remains English; PT manual view is complete PT-BR when targeted. |
| `trace_id`          | string | Propagate without mutation.                                                             |
| `validation_status` | enum   | Existing validation result plus target-specific language outcome.                       |

## 3. Generated Text Region

| Field              | Type          | Rules                                                                                           |
| ------------------ | ------------- | ----------------------------------------------------------------------------------------------- |
| `region_id`        | string        | Stable diagnostic location, e.g. `architectural_patterns.justification`.                        |
| `source_kind`      | enum          | `template_label`, `builder_fallback`, `source_derived_prose`, `report_text`, `technical_value`. |
| `raw_value`        | string        | Original value; source remains read-only.                                                       |
| `rendered_en`      | string        | English default value where applicable.                                                         |
| `rendered_pt`      | string        | PT-BR manual-view value where applicable.                                                       |
| `protected_tokens` | array[string] | Exact tokens excluded from normalization and detection.                                         |
| `language_status`  | enum          | `english`, `portuguese`, `protected`, `empty`, `non_compliant`, `not_applicable`.               |

## 4. Protected Technical Value

Protected categories include code symbols, class and method names, file paths, URLs, technical identifiers, ADR filenames, Markdown references, project names, proper nouns, standard acronyms, exact traceability references, `reference_artifact`, and `adr_reference`. Numeric, boolean, enum, and structured values are protected when their field contract identifies them as non-prose.

Protection is byte-for-byte. A value may be embedded in Portuguese prose, but its exact token must remain unchanged and must not produce a language false positive.

## 5. Language Compliance Result

| Field                      | Type          | Rules                                                                                                  |
| -------------------------- | ------------- | ------------------------------------------------------------------------------------------------------ |
| `artifact_path`            | path          | Artifact checked.                                                                                      |
| `is_compliant`             | boolean       | True only when all inspectable regions satisfy the requested target.                                   |
| `offending_regions`        | array[object] | `region_id`, diagnostic message, and optional location/evidence.                                       |
| `ignored_protected_values` | array[string] | Tokens excluded from language detection.                                                               |
| `mode`                     | enum          | Existing `summary` or `remediation`.                                                                   |
| `target`                   | enum          | Serialized schema/result field, `en` or `pt`; populated from the internal `language_target` parameter. |
| `blocking`                 | boolean       | True whenever unresolved findings exist; for explicit PT this drives error-level failure.              |

## 6. Remediation Result

| Field             | Type              | Rules                                                                                  |
| ----------------- | ----------------- | -------------------------------------------------------------------------------------- |
| `errors_before`   | integer           | Existing error-level count before rebuild.                                             |
| `errors_after`    | integer           | Includes explicit PT language errors when PT targeting is active.                      |
| `remaining`       | array[string]     | Failing check IDs, including PT language check ID.                                     |
| `success`         | boolean           | False whenever `errors_after > 0`; no warning-only success for targeted PT.            |
| `language_target` | internal/CLI enum | Internal target used for this run; serialized remediation/result output uses `target`. |

## 7. Architectural Pattern Record

Existing fields are retained:

- `pattern_name`: normalize prose to target language; preserve recognized technical/proper names.
- `layer`: normalize human-readable layer labels; preserve technical identifiers.
- `justification`: normalize source-derived prose.
- `trade_offs`: normalize each prose item deterministically.
- `reference_artifact`: preserve exact value.
- `adr_reference`: preserve exact value.

## 8. State Transitions

```text
RAW_SOURCE
  → CLASSIFIED (prose vs protected/non-prose)
  → TARGET_NORMALIZED (en default or explicit pt)
  → RENDERED / EMBEDDED
  → TARGET_VALIDATED_COMPLIANT

RAW_SOURCE
  → CLASSIFIED
  → UNSAFE_OR_RESIDUAL_PROSE
  → TARGET_VALIDATED_NON_COMPLIANT
  → BLOCKED (error-level; errors_after > 0 for targeted remediation)
```

## 9. Relationships

```text
Source Artifact (read-only)
        │
        └── Builder language boundary ──> English default + PT manual-view values
                                              │
                                              ├── HTML selector / setLang('pt')
                                              ├── Markdown/report output
                                              └── Targeted language compliance result

Summary Artifact ──official rebuild──> Remediation Result
                                      └── same error-level target gate
```
