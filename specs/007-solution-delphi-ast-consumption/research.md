# Research Notes: Solution Delphi AST Consumption

## 1. The AST pipeline already exists, partially wired

`src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py`
(untracked, already present before this PBI) is a thin wrapper — not itself
an AST parser. It:

1. Reads `project-config.yaml` for `repository_path`/`legacy_technology`; no-ops if not Delphi.
2. Shells out to `{analyzer_path}/src/run_pipeline.py` — a script belonging
   to a **separate, external tool** (`ava-fabric-delphi-analyzer`, found on
   disk at `C:\Desenv\repo\tool\ava-fabric-delphi-analyzer`, not part of this
   repo), passing `repository_path` and output dirs.
3. Verifies (does not itself generate) that the 8 expected filenames exist
   afterward, plus `manifest.json`/`metrics.jsonl`.
4. Writes a log file and prints a one-line summary from `08_code_overview.json`.

The **real** AST work happens entirely in the external tool: `DelphiAST`
(a native, compiled Delphi/Object-Pascal parser) via a CLI binary
(`ava_ast_cli`/`ava_ast_cli.exe`), invoked for `.pas` files only. `.dfm`
(forms) are **never** parsed via AST — always regex, per the external tool's
own README: "`.dfm` é analisado por regex (DelphiAST cobre só `.pas`)". A
regex fallback also fills gaps the AST/IR doesn't cover elsewhere. Each
JSON's `payload.counts.mode` (e.g. `"ast+regex-fallback"`) self-reports which
technique produced it.

## 2. `solution-delphi.md` already had partial, uncommitted wiring

Before this PBI, `solution-delphi.md` had an existing (uncommitted) "Step 0 —
Deterministic AST Extraction (Prerequisite)" section wiring 6 of the 8 JSON
files as an **optional, non-blocking** enhancement: if Step 0 succeeded,
Steps 3, 6, 7, 9, 10, 12 used the JSON as primary source; otherwise, every
step fell back 100% to raw `Glob`/`Grep`/`Read`. `01_business_rules.json`
and `02_form_business_rules.json` were referenced nowhere in the file. This
PBI's job was to complete and harden this existing design, not build it from
scratch.

## 3. Confirmed real JSON schemas (not assumed)

All 8 schemas were read directly from a real, already-executed sample run at
`projects/Meu-ERP-006-AST-LLM/outputs/asis/delphi-ast-raw/extraction/`
(see `data-model.md`) — not inferred from the wrapper script (which doesn't
construct the JSON itself) or from the external tool's source. This grounded
every design decision in this PBI in actual, verified data shapes.

## 4. Why some Steps/Analyses genuinely can't stop reading raw source

Checked every one of the 8 schemas against Steps 1, 2, 4's 10-analysis
table:

- **Step 1 (Repository Inventory)**: `08_code_overview.json.payload.classes`
  has `{name, parent, file, line}` for every class — sufficient to derive
  Forms/DataModules/Units groupings without a `Glob` scan. **Redesigned to
  use this.**
- **Step 2 (`.dpr` bootstrap)**: no schema captures `Application.CreateForm`
  order or startup sequence — `.dpr` is a project file, not a compilation
  unit, and outside `DelphiAST`'s `.pas`-only scope. **Kept as a narrow,
  explicit exception** (one small file, not "the codebase").
- **Step 4 Analyses #5 (Global State), #8 (Concurrency), #11 partial
  (generic hardcoded-value/dead-code detection), #13 (File Export)**: none
  of the 8 schemas has fields for global variable detection, threading
  primitives, or file-export call patterns. **Confirmed no AST coverage
  exists — these remain Grep-based**, stated honestly in the spec as a real
  limitation of today's external tool, not glossed over.

## 5. `.drawio` removal is safe — confirmed by an existing, unrelated script

Before deleting all native `.drawio` generation from `solution-delphi.md`,
checked whether any downstream consumer depends on it. Found
`src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py`
(existing, unmodified by this PBI) — its own docstring: "REUSE: Zero code
duplication - uses existing .mmd files," generating consolidated
`AS-IS-{C4,Overall-Architecture,BPMN,Sequence}-Diagrams.drawio` files by
reading `.mmd` files at Summary-build time. This means solution-delphi's
`.mmd` outputs (unchanged by this PBI) already feed a working, non-duplicated
`.drawio` synthesis path — removing the agent's own native XML-authoring
logic loses nothing, it just stops duplicating work already done correctly
at the right layer.

## 6. Naming-collision check for the new artifact

`asis-diagnostic/shared/output-paths.md`'s "Documentation Agent" section
already lists `Business Rules | asis/docs/business-rules.md` (produced by
`ava-asis-documentation` from doc-mining). The new artifact this PBI adds —
code-mined business rules from `01_business_rules.json` — was deliberately
named `asis/code-business-rules.md` to avoid clobbering that existing,
unrelated artifact. Confirmed no other agent or shared doc already uses this
exact filename.

## 7. Scope boundary confirmed

`solution-vb.md` was checked and confirmed to have a near-identical
`.drawio` scaffold (same skill/step/template structure) but **no** AST tool
integration — `DelphiAST` is Delphi-specific, and no equivalent VB6 AST tool
exists in this repo or referenced anywhere. Left untouched, as agreed in the
plan, with `output-paths.md`'s shared table annotated `(VB6 only)` on the
now-Delphi-orphaned `.drawio` rows so the shared file still reads correctly
for both agents.
