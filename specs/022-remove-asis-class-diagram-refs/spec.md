# Spec: Remove AS-IS Class Diagram References

**Feature Branch**: `022-remove-asis-class-diagram-refs`
**Created**: 2026-07-17
**Status**: Draft
**Change Type**: `bugfix`
**Spec Number**: `022`

> **Language note**: This spec is a planning document written in **English**.
> Implementation changes in agent `.md` files MUST keep Brazilian Portuguese per Constitution Article V.

---

## 1. Overview

The artifact `asis/diagrams/class-diagram.mmd` was removed from the AS-IS pipeline.
Its generation instructions were already removed from `solution-delphi.md`. However,
references to this artifact still exist across documentation, module configuration, agent
files, summary utilities, and report templates.

This spec defines the complete, safe removal of all AS-IS `class-diagram.mmd` references
while **preserving** all references to `tobe/diagrams/class-diagram.mmd` (the TO-BE class
diagram, produced by `ava-tobe-architecture-design` and consumed by the Summary pipeline
unchanged).

### Scope Definition

| Reference type | Decision |
|---|---|
| `asis/diagrams/class-diagram.mmd` | **REMOVE** — artifact no longer generated in F1 |
| `asis/diagrams/class-diagram.drawio` | **REMOVE** — derived from the above; no longer generated |
| `tobe/diagrams/class-diagram.mmd` | **KEEP** — TO-BE artifact, unaffected |
| `{{CLASS_DIAGRAM}}` HTML placeholder | **REMOVE** — maps to the AS-IS artifact |
| `{{TOBE_CLASS_DIAGRAM}}` HTML placeholder | **KEEP** — maps to the TO-BE artifact |
| `D.staticDiagrams.class` key | **REMOVE** — key bound to the AS-IS file |
| `D.staticDiagrams.tobeClass` key | **KEEP** — key bound to the TO-BE file |
| `_synthesize_class_diagram()` function | **REMOVE** — synthesizer for the absent AS-IS artifact |

---

## 2. Change Type

This is a **bugfix / cleanup** — not a new agent. It spans:

- 4 documentation files
- 4 AS-IS diagnostic module files
- 5 Summary pipeline files (agents, data, utils, workflows)

No frontmatter version bumps are required unless a changed agent `.md` file
carries meaningful functional changes in addition to the reference removal.
In practice, only `solution-delphi.md` and `orchestrator-asis.md` (if modified)
warrant version bumps (PATCH).

---

## 3. Affected Files and Required Changes

### 3.1 Documentation Files

#### `docs/agents-catalog.md`

**Context** (line ~106 — output block for `ava-asis-solution-delphi`):

```yaml
class_diagram: projects/{PROJECT_NAME}/outputs/asis/diagrams/class-diagram.mmd
```

**Action**: Remove the `class_diagram:` line from the output block.
Neighboring entries (`c4_context`, `c4_container`, `c4_component`, `seq_diagrams`) must remain.
The `seq_diagrams:` entry that follows must NOT be removed.

---

#### `docs/asis-diagnostic-io-map.md`

**Context** (line ~92 — outputs list for `ava-asis-solution-delphi`):

```
  - `asis/diagrams/class-diagram.mmd`
```

**Action**: Remove this list item. Also remove `asis/diagrams/class-diagram.mmd` from
the **Mandatory subset** paragraph if it appears there. The surrounding `.mmd` entries
(`architecture-blueprint.mmd`, `c4-{context,container,component}.mmd`,
`component-diagram.mmd`, `diagrama-sequencia-*.mmd`) must remain.

---

#### `docs/guia-execucao-fluxo-agentes.md`

**Context** (lines ~156 and ~211 — two directory-tree blocks under F1 section):

```
│   ├── class-diagram.mmd
```

**Action**: Remove both occurrences. Each appears inside an `outputs/asis/diagrams/`
subtree. Surrounding sibling entries (`c4-context.mmd`, `c4-container.mmd`,
`c4-component.mmd`, `sequence-*.mmd`) must remain.

**Validation rule**: The TO-BE directory tree (under F2, ~line 211) also shows
`class-diagram.mmd` inside `outputs/tobe/diagrams/` — **DO NOT remove that occurrence**.
Check whether `class-diagram.mmd` is nested under `outputs/asis/diagrams/` (remove)
or `outputs/tobe/diagrams/` (keep).

---

#### `docs/full-pipeline-guide.md`

Grep returned zero matches — **no changes required** for this file. Verified clean.

---

### 3.2 AS-IS Diagnostic Module Files

#### `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml`

**Context** (line ~100 — diagram artifacts list):

```yaml
    # Diagrams (.mmd)
    - diagrams/c4-context.mmd
    - diagrams/c4-container.mmd
    - diagrams/c4-component.mmd
    - diagrams/class-diagram.mmd          ← REMOVE
    - diagrams/component-diagram.mmd
    # Diagrams (.drawio)
    - diagrams/c4-context.drawio
    - diagrams/c4-container.drawio
    - diagrams/c4-component.drawio
    - diagrams/component-diagram.drawio   ← the drawio counterpart stays
```

**Action**: Remove `- diagrams/class-diagram.mmd` from the `.mmd` section.

> Note: There is **no** `- diagrams/class-diagram.drawio` line because the drawio artifacts
> are agent-level only for VB6 stack (confirmed by `output-paths.md`). However, if such a
> line exists, remove it too.

---

#### `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md`

**Context** (lines ~42 and ~48 — Solution Agent table):

```markdown
| Class Diagram          | `asis/diagrams/class-diagram.mmd`         |
...
| Class Diagram Drawio (VB6 only) | `asis/diagrams/class-diagram.drawio` |
```

**Action**: Remove both rows. The surrounding rows (`C4 Component`, `Component Diagram`,
`Sequence Diagrams`, `C4 Context Drawio (VB6 only)`, `C4 Container Drawio (VB6 only)`,
etc.) must remain intact. Table formatting (column widths, alignment) must be preserved.

---

#### `src/modules/ava-fabric-agents/asis-diagnostic/templates/reports/asis-solution-report.md`

**Context** (line ~100 — "Artefatos Gerados" table):

```markdown
| Class Diagram    | Mermaid | `projects/{project_name}/outputs/asis/diagrams/class-diagram.mmd` |
```

**Action**: Remove this table row. Surrounding rows (`C4 Context`, `C4 Container`,
`C4 Component`, `Bounded Context Map`, `Pattern Classifications`) must remain.

---

#### `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md`

Grep returned zero matches — the generation instructions were already removed.
**No changes required** for this file. Verified clean.

---

#### `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`

Grep returned zero matches — **no changes required** for this file. Verified clean.

---

### 3.3 Summary Pipeline — Data Files

#### `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`

**Context** (lines ~43-47 — AS-IS artifacts block):

```yaml
      class_diagram:
        path: "project/outputs/asis/diagrams/class-diagram.mmd"
        section: "s-asis-arch"
```

**Action**: Remove the entire `class_diagram:` block (key + `path:` + `section:` lines).
Neighboring entries (`c4_context`, `c4_container`, `bounded_contexts`, etc.) must remain.
YAML indentation must be preserved.

---

### 3.4 Summary Pipeline — Agent Files

#### `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`

**Multiple occurrences — review each by context:**

| Location | Content | AS-IS or TO-BE | Action |
|---|---|---|---|
| **Diagram Reader** bullet input list (~line 231) | `diagrams/*.mmd` wildcard | The wildcard already covers all `.mmd` in `asis/diagrams/` — no specific `class-diagram.mmd` reference here; this entry does not need to change | **KEEP** |
| **D.staticDiagrams** `class` key description (~line 711) | `"class": "<conteúdo de asis/diagrams/class-diagram.mmd sanitizado>"` | AS-IS | **REMOVE** |
| **D.staticDiagrams** `tobeClass` key description (~line 719) | `"tobeClass": "<conteúdo de tobe/diagrams/class-diagram.mmd sanitizado>"` | TO-BE | **KEEP** |
| **D.staticDiagrams contract** Keys AS-IS list (~line 271 area) | `Keys AS-IS: er, class, comp, seqCadCp, seqBaixaCp, c4ctx, c4cnt, c4comp, ...` | `class` is AS-IS | **REMOVE** `class` from the `Keys AS-IS:` list |
| `staticDiagrams.tobeClass` row in the table | `tobe/diagrams/class-diagram.mmd` | TO-BE | **KEEP** |

**Contract update**: The `D.staticDiagrams` contract note states:
> "ALL keys MUST be present even when source `.mmd` is absent — emit `""`"

Since `class-diagram.mmd` is permanently removed (not temporarily missing), the `class` key
should be **removed entirely** from the contract list and from the `D.staticDiagrams` object.
The rendering function `renderStaticDiagrams()` must be checked — if it references
`D.staticDiagrams.class` directly in the HTML template, the template also needs updating.
This is tracked in Section 3.5 (HTML template).

---

### 3.5 Summary Pipeline — Workflow Steps

#### `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-03-build-html.md`

**Context** (line ~109 — diagram placeholder table):

```markdown
| `{{CLASS_DIAGRAM}}`                   | `asis/diagrams/class-diagram.mmd`                                 | `class_diagram`     |
```

**Action**: Remove this row. The following row (line ~116) for `{{TOBE_CLASS_DIAGRAM}}` maps
to `tobe/diagrams/class-diagram.mmd` — **KEEP it unchanged**.

Also check the `D.staticDiagrams` injection instructions in the same file:
- Remove any `D.staticDiagrams.class` ← `class_diagram` injection line.
- Keep `D.staticDiagrams.tobeClass` ← `tobe_class` injection line.

---

### 3.6 Summary Pipeline — Python Utilities

#### `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py`

Three AS-IS references:

| Location | Code | Action |
|---|---|---|
| ARTIFACT_MAP `ava-asis-solution-delphi` section (~line 74) | `{"key": "class-diagram", "path": "asis/diagrams/class-diagram.mmd"}` | **REMOVE** entry |
| `diagrams` dict construction (~line 1260) | `"class": _read_and_sanitize(diag / "class-diagram.mmd")` | **REMOVE** key-value pair |
| template variable map (~line 2181) | `"CLASS_DIAGRAM": _read_and_sanitize(asis_dir / "diagrams" / "class-diagram.mmd")` | **REMOVE** key-value pair |
| `"tobeClass": _read_and_sanitize(tobe_diag / "class-diagram.mmd")` (~line 1271) | TO-BE key | **KEEP** |

> **Note**: `build_summary_complete.py.backup` (a backup file) also contains the ARTIFACT_MAP
> reference at line ~66. Backup files are not actively executed but should be updated for
> consistency if the team maintains them. Mark as low-priority/informational.

---

#### `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`

Five AS-IS references:

| Location | Code | Action |
|---|---|---|
| ARTIFACT_MAP `ava-asis-solution-delphi` section (~line 166) | `{"key": "class-diagram", "path": "asis/diagrams/class-diagram.mmd"}` | **REMOVE** entry |
| `DIAG_NAMES` set in file tree categorizer (~line 2149) | `"class-diagram"` in the set | **REMOVE** from set — this name is used to classify files in the deliverable submenu; since the file will no longer exist, the entry is dead code |
| template variable map (~line 3634) | `"CLASS_DIAGRAM": sanitize_mmd(read_text(asis_dir / "diagrams" / "class-diagram.mmd"))` | **REMOVE** key-value pair |
| `candidates` list in `collect_static_diagrams` (~line 5017) | `("class", diag_dir / "class-diagram.mmd")` | **REMOVE** tuple |
| `ASIS_DIAGRAM_TEMPLATES` dict (~line 5096–5100) | `"class-diagram.mmd": ("ava-asis-solution-delphi", "classDiagram\n ...")` | **REMOVE** entry |
| `_synthesize_class_diagram()` function (~line 5096–5130) | Full function body | **REMOVE** entire function |
| TO-BE: `("tobeClass", outputs_dir / "tobe" / "diagrams" / "class-diagram.mmd")` (~line 5025) | TO-BE candidate | **KEEP** |
| TO-BE: `"TOBE_CLASS_DIAGRAM": sanitize_mmd(...)` (~line 3646) | TO-BE template var | **KEEP** |

> ⚠️ When removing `_synthesize_class_diagram()`, also check if there is a call site
> that invokes it (likely in the same file, inside `collect_static_diagrams` or a
> wrapper function). The call site must also be removed.

---

#### `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`

Two AS-IS references:

| Location | Code | Action |
|---|---|---|
| `DIAGRAM_NAME_PATTERN` regex (~line 38) | `r"(c4-context\|c4-container\|c4-component\|class-diagram\|..."` | **REMOVE** `class-diagram\|` from the alternation. The pattern is used to detect misplaced diagrams (Rule H) — since `class-diagram.mmd` is no longer generated, it should not be recovered |
| `ASIS_DIAGRAM_TEMPLATES` / Rule G fallback synthesis (~line 319) | `"class-diagram.mmd": (...)` | **REMOVE** entry from the synthesis dict |

---

#### `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`

One AS-IS reference:

| Location | Code | Action |
|---|---|---|
| `_c3_2` check `STEM_TO_KEY` dict (~line 411) | `"class-diagram": "class"` | **REMOVE** — since the file is no longer generated, the validator must not flag its absence as a failed check. Removing the mapping excludes it from the C3.2 validation loop entirely |

---

### 3.7 Additional File — Discovered Scope (not in original list)

#### `src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py`

**Context** (~line 153 — `build_overall_architecture_drawio` function):

```python
overall_diagrams = [
    ("Component Diagram", "component-diagram.mmd", "page-component"),
    ("Class Diagram", "class-diagram.mmd", "page-class"),
]
```

**Action**: Remove the `("Class Diagram", "class-diagram.mmd", "page-class")` tuple from
`overall_diagrams`. The function already handles a missing file gracefully (checks
`if mermaid_code:` before adding the page), so this is a documentation/intent fix,
not a functional one. The "Component Diagram" entry must remain.

#### `src/modules/ava-fabric-agents/summary/utils/validate_drawio_integration.py`

**Context** (~line 94):

```python
"class-diagram.drawio",
```

**Action**: Remove `"class-diagram.drawio"` from the validation list. Since neither
`class-diagram.mmd` (AS-IS) nor its `.drawio` output will be generated, validating
for its existence would always fail. The entry is dead code.

> This file was not in the original list but is directly impacted by the removal
> of the drawio artifact. Including it ensures the validation pipeline remains consistent.

---

## 4. Context Disambiguation Rules

When evaluating any occurrence of `class-diagram` in the codebase, apply these rules:

1. **Path contains `asis/`** → AS-IS reference → **REMOVE**
2. **Path contains `tobe/`** → TO-BE reference → **KEEP**
3. **Variable name is `CLASS_DIAGRAM`** (no TOBE prefix) → AS-IS → **REMOVE**
4. **Variable name is `TOBE_CLASS_DIAGRAM`** → TO-BE → **KEEP**
5. **Dict key is `"class"` in `D.staticDiagrams`** → AS-IS → **REMOVE**
6. **Dict key is `"tobeClass"` in `D.staticDiagrams`** → TO-BE → **KEEP**
7. **Relative path `diag_dir / "class-diagram.mmd"`** where `diag_dir = asis_dir / "diagrams"` → AS-IS → **REMOVE**
8. **Relative path `tobe_diag / "class-diagram.mmd"`** → TO-BE → **KEEP**
9. **`{{CLASS_DIAGRAM}}` placeholder** → AS-IS → **REMOVE** row/reference
10. **`{{TOBE_CLASS_DIAGRAM}}` placeholder** → TO-BE → **KEEP**

---

## 5. User Scenarios

### Scenario 1 — Nominal: AS-IS pipeline runs without class diagram

**Story**: Como o pipeline AS-IS, quero que ao final da execução do `ava-asis-solution-delphi`,
nenhum agente, script ou validador espere ou verifique a existência de
`asis/diagrams/class-diagram.mmd`, para que o pipeline não produza falsos negativos.

**Acceptance Scenarios**:

1. **Given** the AS-IS pipeline executes successfully, **When** `ava-asis-solution-delphi` completes, **Then** no artifact map, module.yaml, or validator references `asis/diagrams/class-diagram.mmd`.
2. **Given** the Summary build runs after F1, **When** `build_summary_comprehensive.py` is invoked, **Then** the script does not read, synthesize, or validate `asis/diagrams/class-diagram.mmd`.
3. **Given** a Summary HTML is generated, **When** `validate_summary.py` runs, **Then** the C3.2 check does not flag the absence of `class-diagram.mmd` in `asis/diagrams/`.

---

### Scenario 2 — TO-BE Class Diagram Preserved

**Story**: Como o Summary builder, quero que o diagrama de classes TO-BE continue sendo
renderizado no HTML, para que a documentação do sistema migrado permaneça completa.

**Acceptance Scenarios**:

1. **Given** `tobe/diagrams/class-diagram.mmd` exists after F2, **When** `build_summary_comprehensive.py` is invoked, **Then** `D.staticDiagrams.tobeClass` is populated with its content.
2. **Given** the step-03-build-html.md workflow runs, **Then** `{{TOBE_CLASS_DIAGRAM}}` is still defined in the placeholder mapping table and points to `tobe/diagrams/class-diagram.mmd`.
3. **Given** `docs/guia-execucao-fluxo-agentes.md` is read, **Then** `class-diagram.mmd` still appears in the TO-BE directory tree (under `outputs/tobe/diagrams/`) and NOT in the AS-IS tree.

---

### Scenario 3 — Consistency Gate

**Story**: Como desenvolvedor, quero que após aplicar as mudanças não existam referências
residuais ao `asis/diagrams/class-diagram.mmd` em nenhum arquivo listado nesta spec.

**Acceptance Scenarios**:

1. **Given** all changes in Section 3 are applied, **When** `grep -r "asis/diagrams/class-diagram"` is run against the repository, **Then** zero matches are returned.
2. **Given** all changes are applied, **When** `grep -r '"CLASS_DIAGRAM"'` is run, **Then** zero matches are returned (only `TOBE_CLASS_DIAGRAM` references remain).
3. **Given** all changes are applied, **When** `grep -r '"class-diagram"'` is run in summary utils, **Then** zero matches remain in AS-IS context (only `TOBE_CLASS_DIAGRAM` or `tobe/diagrams/` context remains).

---

## 6. Quality Gate Requirements

- [ ] No `asis/diagrams/class-diagram.mmd` path reference remains in any file after changes
- [ ] No `asis/diagrams/class-diagram.drawio` path reference remains
- [ ] `{{CLASS_DIAGRAM}}` placeholder removed from workflow steps (not `{{TOBE_CLASS_DIAGRAM}}`)
- [ ] `D.staticDiagrams.class` key removed from Summary agent contract
- [ ] `D.staticDiagrams.tobeClass` key untouched in all files
- [ ] `tobe/diagrams/class-diagram.mmd` references unaffected in all TO-BE agents/utils
- [ ] `_synthesize_class_diagram()` function removed from `build_summary_comprehensive.py`
- [ ] YAML/Markdown table formatting preserved in all modified `.md` files
- [ ] Python list/dict syntax remains valid after entry removals (no trailing commas causing syntax errors)
- [ ] No new [NEEDS CLARIFICATION] markers remain

---

## 7. Dependencies

| Dependency | Reason |
|---|---|
| `solution-delphi.md` already updated | The generation instruction removal is the upstream cause; this spec cleans up downstream effects |
| TO-BE architecture agents unchanged | `ava-tobe-architecture-design` still generates `tobe/diagrams/class-diagram.mmd` |
| Summary HTML template (`summary-template.html`) | Must be checked for any `{{CLASS_DIAGRAM}}` injection or `D.staticDiagrams.class` JavaScript reference — not listed in the user's scope but should be verified |

---

## 8. Exclusions

- `tobe/diagrams/class-diagram.mmd` and all TO-BE agents referencing it — **out of scope**
- `docs/summary-io-map.md` — only mentions `tobe/diagrams/class-diagram.mmd` (TO-BE context); no changes needed
- `docs/tobe-architecture-io-map.md` — only mentions `tobe/diagrams/class-diagram.mmd` (TO-BE context); no changes needed
- `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` — references `class-diagram.mmd` only in a TO-BE context description; verify before closing this spec
- VB6/COBOL/PowerBuilder solution agents — they may have their own class diagram generation; only the Delphi AS-IS pipeline is addressed here

---

## 9. Assumptions

- The `class-diagram.mmd` artifact was intentionally removed from the Delphi AS-IS pipeline (confirmed: `solution-delphi.md` no longer contains generation instructions)
- VB6, COBOL, and PowerBuilder solution agents are not affected — their output contracts are separate
- The Summary HTML template's JavaScript (`renderStaticDiagrams()`) gracefully handles missing keys in `D.staticDiagrams` — removing `class` will not cause a JavaScript runtime error
- The `.backup` file (`build_summary_complete.py.backup`) is not executed by any pipeline step

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Zero residual AS-IS references | `grep -r "asis/diagrams/class-diagram" .` returns 0 matches |
| Zero `CLASS_DIAGRAM` template variables | `grep -r '"CLASS_DIAGRAM"' src/` returns 0 matches (only `TOBE_CLASS_DIAGRAM` remains) |
| TO-BE unaffected | `grep -r "tobe/diagrams/class-diagram" .` returns the same count as before the change |
| Python files valid | `python -m py_compile` passes on all modified `.py` files |
| YAML files valid | `python -c "import yaml; yaml.safe_load(open('file'))"` passes on modified `.yaml` files |
| Summary pipeline builds without error | `build_summary_comprehensive.py` executes without `KeyError` or `FileNotFoundError` for `class-diagram.mmd` |
| Validator clean | `validate_summary.py` does not report `class-diagram` as a missing artifact |
