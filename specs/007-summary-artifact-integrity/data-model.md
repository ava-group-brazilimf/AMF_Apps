# Data Model: Summary Artifact Integrity (007)

**Feature**: `007-summary-artifact-integrity`
**Date**: 2026-07-08

---

## Entities

### ArtifactCheckResult (in-memory, not persisted)

Emitted by Step 0.5 of `summary-agent.md` as structured stdout. Not written to a separate file.

| Field | Type | Description |
|---|---|---|
| `status` | `"OK" \| "ARTIFACT-MISSING" \| "ARTIFACT-EMPTY"` | Result for one artifact entry |
| `section_name` | `string` | HTML section ID from artifact-map.yaml (e.g. `s-test-plan`) |
| `relative_path` | `string` | Path relative to project root (e.g. `outputs/qa/test-plan.md`) |
| `absolute_path` | `string` | Resolved absolute path checked on disk |
| `file_size_bytes` | `integer \| null` | File size when file exists; null when missing |

### ArtifactCheckSummary (emitted at end of Step 0.5)

| Field | Type | Description |
|---|---|---|
| `total` | `integer` | Total artifacts checked |
| `ok` | `integer` | Artifacts that pass (exist, size > 0) |
| `missing` | `integer` | Artifacts not found on disk |
| `empty` | `integer` | Artifacts found but size = 0 |
| `sections_omitted` | `string[]` | List of section names omitted from HTML |

---

## Emit Format

Step 0.5 emits these exact line formats (one per artifact):

```
# When all OK:
[ARTIFACT-CHECK] OK — {N} artefatos verificados, 0 ausentes

# When an artifact is missing:
[ARTIFACT-MISSING: {section_name}] — arquivo ausente: {relative_path}

# When an artifact exists but is empty:
[ARTIFACT-EMPTY: {section_name}] — arquivo vazio (0 bytes): {relative_path}

# Summary line (always emitted):
[ARTIFACT-CHECK] Resultado: {ok}/{total} OK | {missing} ausentes | {empty} vazios
  Seções omitidas: [{section_name_1}, {section_name_2}, ...]
```

---

## HTML Omission Marker

When a section is omitted due to a missing/empty artifact, the agent injects:

```html
<!-- OMITTED: artifact missing or empty — {relative_path} -->
```

as the only content for that section slot (not rendered in the visible HTML body).

---

## C11 Rule Targets (in generated HTML)

| Rule | Detects | Severity | Pattern |
|---|---|---|---|
| C11.1 | Literal `[INCOMPLETE]` in HTML text nodes | error | `re.search(r'\[INCOMPLETE\]', html)` |
| C11.2 | Unresolved `[ARTIFACT-MISSING` marker in HTML | error | `re.search(r'\[ARTIFACT-MISSING', html)` |
| C11.3 | `<table>` with `<thead>` but zero `<tbody><tr>` rows | warn | BeautifulSoup / regex scan of `<table>` blocks |

---

## State Transitions for a Section

```
artifact_map entry
    │
    ▼ Step 0.5 checks existence + size
    ├─ OK (exists, size > 0) ──────────────► section rendered normally by build script
    ├─ MISSING (not on disk) ─────────────► [ARTIFACT-MISSING:] emitted; section omitted
    └─ EMPTY (exists, size = 0) ──────────► [ARTIFACT-EMPTY:] emitted; section omitted
                                              HTML comment injected at section slot
```
