# Data Model: Unified Business Rules & Functional Requirements Artifact

**Feature**: `026-unified-business-rules-artifact`
**Date**: 2026-07-21

---

## Unified `business-rules.md` — Structure v2.0.0

### Top-level header

```
# Business Rules & Functional Requirements — {project_name} AS-IS
**trace_id**: {trace_id}
**Generated**: {YYYY-MM-DD}
```

### Section 1: Functional Requirements

```
---

## Functional Requirements

[content]
```

Supports two sub-formats (parser-contracts.md):

| Sub-format | Header pattern | ID pattern |
|-----------|---------------|-----------|
| Formato A | `## FR-NNN: Title` | `FR-NNN` (3-digit) |
| Formato B | `## Module: Name` + table rows | `FR-NNN` in table |

Optional trailing sub-section (FR cross-validation):
```
## ⚠️ Avisos de Validação — Módulos Não Confirmados

| FR | Módulo Declarado | Status |
|----|-----------------|--------|
```

### Section 2: Business Rules

```
---

## Business Rules

[content]
```

Supports two sub-formats (parser-contracts.md):

| Sub-format | Header pattern | ID pattern |
|-----------|---------------|-----------|
| Formato A | `## BR-NNN: Title` | `BR-NNN` (3-digit) |
| Formato B | `## Domain: X` + table rows | `RN-XX-NN` |

---

## Write Mode Matrix

| Trigger | File exists? | Result |
|---------|-------------|--------|
| `BRF` | No | Create with both sections |
| `BRF` | Yes | Overwrite entire file with both sections |
| `RF` | No | Create with `## Functional Requirements` section only |
| `RF` | Yes, has `## Functional Requirements` | Replace FR section content |
| `RF` | Yes, no `## Functional Requirements` | Append FR section at end |
| `RN` | No | Create with `## Business Rules` section only |
| `RN` | Yes, has `## Business Rules` | Replace BR section content |
| `RN` | Yes, no `## Business Rules` | Append BR section at end |

---

## Parser Output Contract (unchanged from existing `funcReqs` schema)

`parse_func_reqs(path)` returns `list[dict]`:

```python
[
  {
    "id":       "FR-001",      # string, FR-NNN
    "desc":     "...",         # string, description text
    "module":   "Financeiro",  # string, module name
    "priority": "ALTA"         # string, ALTA | MEDIA | BAIXA
  },
  ...
]
```

Returns `[]` when file absent or no FR entries found. No exceptions raised.

---

## ID Invariants (unchanged)

| Artifact | ID format | Zero-padded | Separator |
|----------|-----------|------------|-----------|
| Functional Requirements | `FR-NNN` | Yes (3 digits) | `:` |
| Business Rules (Formato A) | `BR-NNN` | Yes (3 digits) | `:` |
| Business Rules (Formato B) | `RN-XX-NN` | Yes | None (domain + seq) |

All ID prefixes are distinct — no collision risk when parsing the unified file.
