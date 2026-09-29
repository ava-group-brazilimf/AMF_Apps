# Research: Remove AS-IS Class Diagram References

**Feature**: 022-remove-asis-class-diagram-refs  
**Phase**: 0 — Findings from repository analysis

---

## Decision: Artifact removal is complete in `solution-delphi.md`

- **Decision**: `solution-delphi.md` already has no `class-diagram.mmd` generation instructions. The removal was the upstream trigger. This spec only cleans up downstream references.
- **Rationale**: Confirmed by `grep -r "class-diagram" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md` returning 0 matches.
- **Alternatives considered**: Re-adding the diagram generation — rejected (intentional removal).

---

## Decision: `orchestrator-asis.md` and `full-pipeline-guide.md` are already clean

- **Decision**: Both files return zero matches. No changes needed.
- **Rationale**: Direct grep verification.

---

## Decision: Two additional files are in scope (not in original list)

- **Decision**: `generate_drawio_from_mermaid.py` (line ~153) and `validate_drawio_integration.py` (line ~94) must be updated.
- **Rationale**: Both reference `class-diagram.mmd` in AS-IS context (the drawio builder reads it from `asis/diagrams/`, the validator checks for `class-diagram.drawio`). The drawio builder already handles missing files gracefully but the entry is dead code. The validator would produce a false failure.
- **Alternatives considered**: Leaving these files unchanged — rejected because it creates dead code and false validation failures.

---

## Decision: `_synthesize_class_diagram()` function must be fully removed

- **Decision**: The function `_synthesize_class_diagram` in `build_summary_comprehensive.py` (lines ~5096–5150) synthesizes a placeholder when `class-diagram.mmd` is absent. Since the artifact will **never** exist in AS-IS going forward, the synthesis logic is dead code. Remove it and its call site.
- **Rationale**: Keeping it would cause the Summary to still render a (synthesized) class diagram panel, contradicting the intent of the removal.
- **Alternatives considered**: Leaving the function and just removing the call site — rejected (dead code, and any accidental re-invocation would silently resurrect a fake artifact).

---

## Decision: `D.staticDiagrams.class` key to be removed

- **Decision**: Remove the `class` key from the `D.staticDiagrams` object built in both Python scripts and from the summary-agent.md contract description.
- **Rationale**: The D.staticDiagrams contract states "ALL keys MUST be present even when the source `.mmd` file does not exist — emit `""` instead of omitting". This rule was for *optional* files. Since the artifact is **permanently removed** (not optionally absent), the key should be omitted from the object entirely so the HTML template falls through to the "no-diagram" branch without injecting an empty entry.
- **Impact on HTML template**: `renderStaticDiagrams()` / `renderAllDiagrams()` in the HTML must handle a missing `class` key gracefully. The template already uses `t('lbl-no-diagram')` fallback — confirmed in `step-03-build-html.md`.
- **Alternatives considered**: Keep `class: ""` in the object — rejected (masks the removal intent; the contract note should be updated to reflect permanent removal).

---

## Decision: `STEM_TO_KEY` mapping in `validate_summary.py` — remove `class-diagram` entry

- **Decision**: The `_c3_2` validation check maps `.mmd` filenames to `D.staticDiagrams` keys. The `"class-diagram": "class"` entry causes a validation failure when `class-diagram.mmd` is absent. Remove it.
- **Rationale**: The validator must not penalize the correct behavior (no `class-diagram.mmd` in AS-IS).

---

## Decision: `DIAGRAM_NAME_PATTERN` regex in `remediate_summary.py` — update but don't break

- **Decision**: Remove `class-diagram|` from the alternation in `DIAGRAM_NAME_PATTERN`. This regex is used in **Rule H** (misplaced diagram recovery) to detect if a `.mmd` file in a wrong directory should be moved to `asis/diagrams/`. Since `class-diagram.mmd` won't exist, it should not be recoverable.
- **Rationale**: Rule H recovering a `class-diagram.mmd` would re-introduce the removed artifact.

---

## Decision: `guia-execucao-fluxo-agentes.md` has TWO occurrences — only AS-IS one removed

- **Decision**: Lines ~156 (AS-IS directory tree) and ~211 (TO-BE directory tree). Only line ~156 is under `outputs/asis/diagrams/` — remove it. Line ~211 is under `outputs/tobe/diagrams/` — keep it.
- **Rationale**: Verified by reading the file context (line 211 is in F2 section).
- **Evidence**: Line 156 is inside `## 4. F1 — Diagnóstico AS-IS`; line 211 is inside `## 5. F2 — Arquitetura TO-BE`.

---

## Summary of all changes (16 files, 19 exact edits)

| # | File | Edit | Context |
|---|------|------|---------|
| 1 | `docs/agents-catalog.md` | Remove `class_diagram:` line | AS-IS output block |
| 2 | `docs/asis-diagnostic-io-map.md` | Remove `- asis/diagrams/class-diagram.mmd` | outputs list |
| 3 | `docs/guia-execucao-fluxo-agentes.md` | Remove 1 of 2 `class-diagram.mmd` lines | AS-IS tree only |
| 4 | `src/.../asis-diagnostic/module.yaml` | Remove `- diagrams/class-diagram.mmd` | artifacts list |
| 5 | `src/.../shared/output-paths.md` | Remove 2 table rows | Class Diagram + Drawio |
| 6 | `src/.../reports/asis-solution-report.md` | Remove 1 table row | Artefatos Gerados |
| 7 | `src/.../summary/data/artifact-map.yaml` | Remove `class_diagram:` block (3 lines) | AS-IS artifacts |
| 8 | `src/.../summary/agents/summary-agent.md` | Remove `class` from AS-IS keys list + remove `"class"` key doc | D.staticDiagrams contract |
| 9 | `src/.../summary/workflows/.../step-03-build-html.md` | Remove `{{CLASS_DIAGRAM}}` row | placeholder table |
| 10 | `src/.../utils/build_summary_complete.py` | Remove 3 AS-IS references | ARTIFACT_MAP + diagrams dict + template vars |
| 11 | `src/.../utils/build_summary_comprehensive.py` | Remove 5 AS-IS references + `_synthesize_class_diagram` function | ARTIFACT_MAP + DIAG_NAMES + template + candidates + synthesizer |
| 12 | `src/.../utils/remediate_summary.py` | Remove `class-diagram\|` from regex + remove template entry | DIAGRAM_NAME_PATTERN + ASIS_DIAGRAM_TEMPLATES |
| 13 | `src/.../utils/validate_summary.py` | Remove `"class-diagram": "class"` | STEM_TO_KEY |
| 14 | `src/.../utils/generate_drawio_from_mermaid.py` | Remove `("Class Diagram", "class-diagram.mmd", "page-class")` tuple | overall_diagrams list |
| 15 | `src/.../utils/validate_drawio_integration.py` | Remove `"class-diagram.drawio"` | validation list |
| 16 | `build_summary_complete.py.backup` | Informational — same as #10 | low priority |
