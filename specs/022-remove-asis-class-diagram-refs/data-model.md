# Data Model: Remove AS-IS Class Diagram References

**Feature**: 022-remove-asis-class-diagram-refs  
**Phase**: 1 — Change manifest

> This is a cleanup/bugfix spec. There is no domain data model.
> This file catalogs the **exact strings to remove** per file, serving as
> the authoritative change manifest for `speckit.tasks` and implementers.

---

## Change Manifest

### Group A — Documentation (4 files)

#### A1 · `docs/agents-catalog.md`

Remove the `class_diagram:` YAML key-value line from the `ava-asis-solution-delphi` output block:

```diff
- class_diagram: projects/{PROJECT_NAME}/outputs/asis/diagrams/class-diagram.mmd
```

Neighboring lines to preserve:
```
c4_component: projects/{PROJECT_NAME}/outputs/asis/diagrams/c4-component.mmd
seq_diagrams: projects/{PROJECT_NAME}/outputs/asis/diagrams/seq-*.mmd
```

---

#### A2 · `docs/asis-diagnostic-io-map.md`

Remove from the outputs list (around line 92):

```diff
-   - `asis/diagrams/class-diagram.mmd`
```

Also check if `class-diagram.mmd` appears in a **Mandatory subset** paragraph in the same file — remove it there too.

---

#### A3 · `docs/guia-execucao-fluxo-agentes.md`

Remove **only the AS-IS occurrence** (under F1 directory tree, ~line 156):

```diff
-│   ├── class-diagram.mmd
```

**KEEP** the occurrence under F2 directory tree (~line 211, inside `outputs/tobe/diagrams/`).

---

#### A4 · `docs/full-pipeline-guide.md`

No changes — zero matches confirmed.

---

### Group B — AS-IS Diagnostic Module (3 files)

#### B1 · `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml`

Remove from the `# Diagrams (.mmd)` section:

```diff
-     - diagrams/class-diagram.mmd
```

---

#### B2 · `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md`

Remove two table rows from the Solution Agent table:

```diff
-| Class Diagram          | `asis/diagrams/class-diagram.mmd`         |
-| Class Diagram Drawio (VB6 only) | `asis/diagrams/class-diagram.drawio` |
```

---

#### B3 · `src/modules/ava-fabric-agents/asis-diagnostic/templates/reports/asis-solution-report.md`

Remove one table row from **section 9 — Artefatos Gerados**:

```diff
-| Class Diagram    | Mermaid | `projects/{project_name}/outputs/asis/diagrams/class-diagram.mmd` |
```

---

### Group C — Summary Data & Agent (2 files)

#### C1 · `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`

Remove the `class_diagram:` block (3 lines):

```diff
-      class_diagram:
-        path: "project/outputs/asis/diagrams/class-diagram.mmd"
-        section: "s-asis-arch"
```

---

#### C2 · `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`

**Edit 1** — Remove `class` from the `Keys AS-IS:` contract list in the `D.staticDiagrams` table:

```diff
-| D.staticDiagrams | renderStaticDiagrams() | Keys AS-IS: `er`, `class`, `comp`, ...
+| D.staticDiagrams | renderStaticDiagrams() | Keys AS-IS: `er`, `comp`, ...
```

**Edit 2** — Remove the `"class"` key from the inline JSON example (~line 711):

```diff
-         "class":      "<conteúdo de asis/diagrams/class-diagram.mmd sanitizado>",
```

The `"tobeClass"` line immediately below it must remain:
```
         "tobeClass":  "<conteúdo de tobe/diagrams/class-diagram.mmd sanitizado>",
```

---

### Group D — Summary Workflow (1 file)

#### D1 · `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-03-build-html.md`

Remove the `{{CLASS_DIAGRAM}}` row from the placeholder mapping table (~line 109):

```diff
-| `{{CLASS_DIAGRAM}}`                   | `asis/diagrams/class-diagram.mmd`                                 | `class_diagram`     |
```

Keep the `{{TOBE_CLASS_DIAGRAM}}` row (~line 116) unchanged:
```
| `{{TOBE_CLASS_DIAGRAM}}`              | `tobe/diagrams/class-diagram.mmd`                                 | `tobe_class`        |
```

If the file also contains a `D.staticDiagrams.class ← class_diagram` injection instruction, remove that line too.

---

### Group E — Summary Python Utilities (5 files)

#### E1 · `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py`

**Edit 1** — Remove from `ARTIFACT_MAP["ava-asis-solution-delphi"]` (~line 74):

```diff
-        {"key": "class-diagram", "path": "asis/diagrams/class-diagram.mmd"},
```

**Edit 2** — Remove from `diagrams` dict (~line 1260):

```diff
-        "class":         _read_and_sanitize(diag / "class-diagram.mmd"),
```

**Edit 3** — Remove from template variable map (~line 2181):

```diff
-        "CLASS_DIAGRAM":             _read_and_sanitize(asis_dir / "diagrams" / "class-diagram.mmd"),
```

All three TO-BE counterparts (`tobeClass`, `TOBE_CLASS_DIAGRAM`) must remain unchanged.

---

#### E2 · `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`

**Edit 1** — Remove from `ARTIFACT_MAP["ava-asis-solution-delphi"]` (~line 166):

```diff
-        {"key": "class-diagram", "path": "asis/diagrams/class-diagram.mmd"},
```

**Edit 2** — Remove `"class-diagram"` from `DIAG_NAMES` set (~line 2149):

```diff
-                       "architecture-blueprint", "context-map", "class-diagram",
+                       "architecture-blueprint", "context-map",
```

**Edit 3** — Remove from template variable map (~line 3634):

```diff
-        "CLASS_DIAGRAM":        sanitize_mmd(read_text(asis_dir / "diagrams" / "class-diagram.mmd")),
```

**Edit 4** — Remove from `candidates` list in `collect_static_diagrams` (~line 5017):

```diff
-        ("class",   diag_dir / "class-diagram.mmd"),
```

**Edit 5** — Remove the `"class-diagram.mmd"` entry from `ASIS_DIAGRAM_TEMPLATES` dict:

```diff
-    "class-diagram.mmd": (
-        "ava-asis-solution-delphi",
-        "classDiagram\n  class SistemaLegado {{\n"
-        "    +formularios: Form[]\n"
-        "    +executar() void\n  }}\n",
-    ),
```

**Edit 6** — Remove the `_synthesize_class_diagram()` function entirely (and its call site):

Locate the function definition:
```python
def _synthesize_class_diagram(asis_dir: Path) -> str:
    """Synthesize a minimal Mermaid classDiagram when class-diagram.mmd is absent.
    ...
    """
```
Remove the complete function body. Then locate and remove its call site (likely in `collect_static_diagrams` or its wrapper, checking `if not result.get("class"): result["class"] = _synthesize_class_diagram(asis_dir)`).

All TO-BE counterparts (`tobeClass`, `TOBE_CLASS_DIAGRAM`, `("tobeClass", outputs_dir / "tobe" / "diagrams" / "class-diagram.mmd")`) must remain.

---

#### E3 · `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`

**Edit 1** — Remove `class-diagram|` from `DIAGRAM_NAME_PATTERN` regex (~line 38):

```diff
-    r"(c4-context|c4-container|c4-component|class-diagram|"
+    r"(c4-context|c4-container|c4-component|"
```

**Edit 2** — Remove `"class-diagram.mmd"` entry from `ASIS_DIAGRAM_TEMPLATES` synthesis dict (~line 319):

```diff
-    "class-diagram.mmd": (
-        "ava-asis-solution-delphi",
-        "classDiagram\n  class SistemaLegado {{\n    +formularios: Form[]\n    +executar() void\n  }}\n",
-    ),
```

---

#### E4 · `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`

Remove from `STEM_TO_KEY` dict in `_c3_2` check (~line 411):

```diff
-        "class-diagram":         "class",
```

---

#### E5 · `src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py`

Remove from `overall_diagrams` list in `build_overall_architecture_drawio` (~line 153):

```diff
-        ("Class Diagram", "class-diagram.mmd", "page-class"),
```

---

#### E6 · `src/modules/ava-fabric-agents/summary/utils/validate_drawio_integration.py` (discovered scope)

Remove from the validation list (~line 94):

```diff
-    "class-diagram.drawio",
```

---

### Group F — Backup File (low priority, informational)

#### F1 · `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py.backup`

Same edit as E1/Edit 1. Backup file — apply only if the team maintains backup files in sync with the source.

---

## Invariants (must be verified after all edits)

| Invariant | Verification |
|---|---|
| Zero AS-IS class-diagram references | `grep -r "asis/diagrams/class-diagram" .` returns 0 |
| Zero `CLASS_DIAGRAM` variables | `grep -r '"CLASS_DIAGRAM"' src/` returns 0 (only `TOBE_CLASS_DIAGRAM` remains) |
| TO-BE references untouched | `grep -rn "tobe/diagrams/class-diagram" .` returns same count as before |
| Python syntax valid | `python -m py_compile` passes on all modified `.py` files |
| YAML syntax valid | `python -c "import yaml; yaml.safe_load(open('<file>'))"` passes on `.yaml` files |
| Markdown tables intact | No broken `|` column alignment in modified `.md` files |
