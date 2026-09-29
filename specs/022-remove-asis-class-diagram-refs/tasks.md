# Bugfix Tasks: Remove AS-IS Class Diagram References

**Plan**: `specs/022-remove-asis-class-diagram-refs/plan.md`
**Change type**: `bugfix` | **Scope**: 16 files, 19 edits, 1 function removal

> Complete categories sequentially. [P] marks tasks parallelizable within a category.
> **Disambiguation rule**: path has `asis/` → REMOVE · path has `tobe/` → KEEP.
> Full rules in `data-model.md § Invariants`.

---

## Category 1 — Pre-flight: Read Context & Confirm State

Must complete before any edit. Reads the exact content around each change point so edits are precise.

- [X] **1.1** Read `specs/022-remove-asis-class-diagram-refs/data-model.md` in full — this is the authoritative change manifest for all 19 edits
- [X] **1.2** [P] Read lines 90–115 of `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml` — confirm `- diagrams/class-diagram.mmd` is present
- [X] **1.3** [P] Read lines 38–55 of `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md` — confirm both `Class Diagram` rows exist
- [X] **1.4** [P] Read lines 95–106 of `src/modules/ava-fabric-agents/asis-diagnostic/templates/reports/asis-solution-report.md` — confirm the `Class Diagram` table row exists
- [X] **1.5** [P] Read lines 100–115 of `docs/agents-catalog.md` — confirm `class_diagram:` line exists in the `ava-asis-solution-delphi` output block
- [X] **1.6** [P] Read lines 85–100 of `docs/asis-diagnostic-io-map.md` — confirm `- \`asis/diagrams/class-diagram.mmd\`` is present
- [X] **1.7** [P] Read lines 148–168 and 204–220 of `docs/guia-execucao-fluxo-agentes.md` — confirm which occurrence is AS-IS (under F1 section) and which is TO-BE (under F2 section)
- [X] **1.8** [P] Read lines 38–55 of `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` — confirm `class_diagram:` block is present
- [X] **1.9** [P] Read lines 265–275 and 705–725 of `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` — confirm `class` key locations
- [X] **1.10** [P] Read lines 104–120 of `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-03-build-html.md` — confirm `{{CLASS_DIAGRAM}}` row exists and `{{TOBE_CLASS_DIAGRAM}}` row is adjacent

---

## Category 2 — Module Config & Shared Definitions (Tier 1)

Authoritative artifact registry. Apply before all downstream consumers.

- [X] **2.1** Edit `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml` — remove `- diagrams/class-diagram.mmd` from the `# Diagrams (.mmd)` list; keep all other `.mmd` entries (`c4-context`, `c4-container`, `c4-component`, `component-diagram`)
- [X] **2.2** Edit `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md` — remove the `| Class Diagram | \`asis/diagrams/class-diagram.mmd\` |` row and the `| Class Diagram Drawio (VB6 only) | \`asis/diagrams/class-diagram.drawio\` |` row; verify table alignment is intact
- [X] **2.3** Edit `src/modules/ava-fabric-agents/asis-diagnostic/templates/reports/asis-solution-report.md` — remove the `| Class Diagram | Mermaid | \`projects/{project_name}/outputs/asis/diagrams/class-diagram.mmd\` |` row from the **Artefatos Gerados** table; verify surrounding rows (`C4 Context`, `C4 Container`, `C4 Component`, `Bounded Context Map`, `Pattern Classifications`) remain intact

---

## Category 3 — Documentation Edits (Tier 2)

Reflects updated module registry in developer-facing docs.

- [X] **3.1** Edit `docs/agents-catalog.md` — remove the `class_diagram: projects/{PROJECT_NAME}/outputs/asis/diagrams/class-diagram.mmd` line from the `ava-asis-solution-delphi` output YAML block; verify `c4_component:` and `seq_diagrams:` lines above/below remain intact
- [X] **3.2** Edit `docs/asis-diagnostic-io-map.md` — remove ` - \`asis/diagrams/class-diagram.mmd\`` from the outputs list; also search for `class-diagram.mmd` in any **Mandatory subset** paragraph in the same file and remove it there too
- [X] **3.3** Edit `docs/guia-execucao-fluxo-agentes.md` — remove ONLY the `│   ├── class-diagram.mmd` line that appears under the **F1 directory tree** (AS-IS section, `outputs/asis/diagrams/`); **DO NOT** remove the occurrence under the F2 directory tree (`outputs/tobe/diagrams/`) — verify the preserved TO-BE entry still reads `├── class-diagram.mmd` under `tobe/diagrams/`

---

## Category 4 — Summary Data & Agent Contracts (Tier 3)

Updates the declarative data sources consumed by the Summary build pipeline.

- [X] **4.1** Edit `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` — remove the full `class_diagram:` block (three lines: `class_diagram:`, `path: "project/outputs/asis/diagrams/class-diagram.mmd"`, `section: "s-asis-arch"`); verify YAML indentation of neighboring keys is preserved
- [X] **4.2** Edit `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` — **Edit A**: in the `D.staticDiagrams` contract table row, remove `class` from the `Keys AS-IS:` comma-separated list (keep all other AS-IS keys: `er`, `comp`, `seqCadCp`, `seqBaixaCp`, `c4ctx`, `c4cnt`, `c4comp`, `gantt`, `cleanarch`, `solution`); **Edit B**: remove the `"class": "<conteúdo de asis/diagrams/class-diagram.mmd sanitizado>"` line from the inline JSON example; confirm `"tobeClass": "<conteúdo de tobe/diagrams/class-diagram.mmd sanitizado>"` on the line immediately after is NOT removed
- [X] **4.3** Edit `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-03-build-html.md` — remove the `| \`{{CLASS_DIAGRAM}}\` | \`asis/diagrams/class-diagram.mmd\` | \`class_diagram\` |` row from the placeholder mapping table; confirm `| \`{{TOBE_CLASS_DIAGRAM}}\` | \`tobe/diagrams/class-diagram.mmd\` | \`tobe_class\` |` row directly below is unchanged; also remove any `D.staticDiagrams.class ← class_diagram` injection line if present in the same file

---

## Category 5 — Python Utilities: Low Risk (Tier 4a)

Independent single-location edits. Apply in any order.

- [X] **5.1** Edit `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` — remove `"class-diagram": "class",` from the `STEM_TO_KEY` dict inside `_c3_2`; verify surrounding entries (`"c4-context"`, `"c4-container"`, `"c4-component"`, `"component-diagram"`) remain; run `python -m py_compile` to confirm syntax
- [X] **5.2** Edit `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py` — **Edit A**: remove `class-diagram|` from the `DIAGRAM_NAME_PATTERN` regex alternation (the `r"(c4-context|c4-container|c4-component|class-diagram|..."` pattern); **Edit B**: remove the `"class-diagram.mmd": ("ava-asis-solution-delphi", "classDiagram\n  class SistemaLegado {{...")` entry from the `ASIS_DIAGRAM_TEMPLATES` synthesis dict; run `python -m py_compile` to confirm syntax
- [X] **5.3** [P] Edit `src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py` — remove the `("Class Diagram", "class-diagram.mmd", "page-class")` tuple from the `overall_diagrams` list inside `build_overall_architecture_drawio`; the `("Component Diagram", "component-diagram.mmd", "page-component")` entry above it must remain; run `python -m py_compile` to confirm syntax
- [X] **5.4** [P] Edit `src/modules/ava-fabric-agents/summary/utils/validate_drawio_integration.py` — remove `"class-diagram.drawio",` from the validation list (~line 94); run `python -m py_compile` to confirm syntax

---

## Category 6 — Python Utilities: Multi-Location & Function Removal (Tier 4b)

Higher-risk edits with multiple touch points in the same file.

- [X] **6.1** Edit `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py` — three independent edits:
  - **Edit 1** (~line 74): remove `{"key": "class-diagram", "path": "asis/diagrams/class-diagram.mmd"},` from the `ARTIFACT_MAP["ava-asis-solution-delphi"]` list
  - **Edit 2** (~line 1260): remove `"class": _read_and_sanitize(diag / "class-diagram.mmd"),` from the `diagrams` dict; confirm `"tobeClass": _read_and_sanitize(tobe_diag / "class-diagram.mmd")` a few lines below is untouched
  - **Edit 3** (~line 2181): remove `"CLASS_DIAGRAM": _read_and_sanitize(asis_dir / "diagrams" / "class-diagram.mmd"),` from the template variable map; confirm `"TOBE_CLASS_DIAGRAM":` entry is untouched
  - Run `python -m py_compile src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py`
- [X] **6.2** Edit `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — six edits in order:
  - **Edit 1** (~line 166): remove `{"key": "class-diagram", "path": "asis/diagrams/class-diagram.mmd"},` from `ARTIFACT_MAP["ava-asis-solution-delphi"]`
  - **Edit 2** (~line 2149): remove `"class-diagram",` from the `DIAG_NAMES` set (inside the file tree categorizer)
  - **Edit 3** (~line 3634): remove `"CLASS_DIAGRAM": sanitize_mmd(read_text(asis_dir / "diagrams" / "class-diagram.mmd")),` from the template variable map; confirm `"TOBE_CLASS_DIAGRAM":` entry is untouched
  - **Edit 4** (~line 5017): remove `("class", diag_dir / "class-diagram.mmd"),` from the `candidates` list in `collect_static_diagrams`; confirm `("tobeClass", outputs_dir / "tobe" / "diagrams" / "class-diagram.mmd")` tuple is untouched
  - **Edit 5** (~line 5096): remove the `"class-diagram.mmd":` entry from `ASIS_DIAGRAM_TEMPLATES` dict (the whole 4-line block including tuple value)
  - **Edit 6**: remove the `_synthesize_class_diagram(asis_dir: Path) -> str` function in its entirety (all lines from `def _synthesize_class_diagram` to the closing `return` of the function), then locate and remove its call site (a line like `result["class"] = _synthesize_class_diagram(asis_dir)` or similar in `collect_static_diagrams`)
  - Run `python -m py_compile src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
- [X] **6.3** [P] Edit `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py.backup` — apply only Edit 1 from task 6.1 (same ARTIFACT_MAP entry); this is a backup file and not executed — low priority, apply if maintaining backup parity

---

## Category 7 — Verification

Run all checks against the final state of the repository.

- [X] **7.1** Run: `grep -rn "asis/diagrams/class-diagram" . --include="*.md" --include="*.yaml" --include="*.py"` — expected: **zero matches**
- [X] **7.2** Run: `grep -rn '"CLASS_DIAGRAM"' src/ --include="*.py" --include="*.md"` — expected: **zero matches** (only `TOBE_CLASS_DIAGRAM` references are acceptable)
- [X] **7.3** Run: `grep -rn "tobe/diagrams/class-diagram" . --include="*.md" --include="*.py"` — expected: **≥ 6 matches** (must equal pre-change count; confirm none were accidentally removed)
- [X] **7.4** [P] Run `python -m py_compile` on all 6 modified Python files and confirm exit 0 for each:
  - `build_summary_complete.py`
  - `build_summary_comprehensive.py`
  - `remediate_summary.py`
  - `validate_summary.py`
  - `generate_drawio_from_mermaid.py`
  - `validate_drawio_integration.py`
- [X] **7.5** [P] Run YAML syntax check on both modified YAML files:
  - `python -c "import yaml; yaml.safe_load(open('src/modules/ava-fabric-agents/asis-diagnostic/module.yaml', encoding='utf-8'))"`
  - `python -c "import yaml; yaml.safe_load(open('src/modules/ava-fabric-agents/summary/data/artifact-map.yaml', encoding='utf-8'))"`
- [X] **7.6** Run: `grep -n "_synthesize_class_diagram" src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — expected: **zero matches**
- [X] **7.7** Run comprehensive scan: `grep -rn "class-diagram.mmd" . --include="*.md" --include="*.yaml" --include="*.py" | grep -v "tobe/" | grep -v "TOBE_CLASS"` — expected: **zero matches** after filtering; any remaining match must be investigated

---

## Completion Checklist

- [X] All 7 categories complete
- [X] Zero `asis/diagrams/class-diagram` references remaining
- [X] Zero `CLASS_DIAGRAM` (non-TOBE) template variables remaining
- [X] TO-BE references (≥ 6) untouched and verified
- [X] `_synthesize_class_diagram` function fully removed
- [X] All 6 Python files pass `py_compile`
- [X] Both YAML files pass `yaml.safe_load`
- [X] `docs/guia-execucao-fluxo-agentes.md` — TO-BE `class-diagram.mmd` entry under `tobe/diagrams/` still present
