# Spec: Test Cases Overview Extractor — Lightweight Summary Artifact

**Feature Branch**: `028-test-cases-overview-extractor`
**Created**: 2026-07-23
**Status**: Draft
**Change Type**: `modify-existing` + new utility script
**Spec Number**: `028`

> **Language note**: This spec is a planning document written in **English**.
> Implementation changes in agent `.md` files and HTML templates MUST keep Brazilian Portuguese per Constitution Article V.

---

## 1. Overview

The `ava-summary` agent currently renders the full content of `projects/{project_name}/outputs/asis/qa/test-cases.md` verbatim into `D.testCasesContent` — and this content is displayed in the **Test Cases** section of the generated HTML report. For projects with large legacy codebases, `test-cases.md` can grow to hundreds of test case blocks, making the Summary HTML impractical to load and navigate.

This feature introduces two changes:

1. **A standalone Python utility script** (`generate_test_cases_overview.py`) that reads `test-cases.md` and produces a compact `test-cases-overview.md` artifact containing:
   - The **total number of test cases** found in the file
   - A **summary table of the first 10 test cases** (columns: ID, Título, Módulo, Prioridade, Tipo, Regras, Passos)

2. **A pipeline integration** that makes the `ava-summary` builder use `test-cases-overview.md` as the content source for `D.testCasesContent` — falling back to triggering the extractor script if the overview file does not yet exist.

### Source Artifacts

| Artifact | Path | Role |
|---|---|---|
| Input | `projects/{project_name}/outputs/asis/qa/test-cases.md` | Full test case inventory (large) |
| Output | `projects/{project_name}/outputs/asis/qa/test-cases-overview.md` | Compact overview for HTML embedding |

### Motivation

- `test-cases.md` for a medium-sized ERP can exceed 500 KB of Markdown (100+ CT- blocks, each with full Passos tables).
- Embedding this verbatim into the Summary HTML (`D.testCasesContent`) inflates file size unnecessarily and makes the browser tab sluggish.
- The overview artifact provides the essential statistics (total count + first 10 cases) without the full payload — sufficient for the executive/pipeline-review audience of the Summary report.

---

## 2. Affected Components

| Component | Change Type | Description |
|---|---|---|
| `build_summary_comprehensive.py` | Modify | Add `build_test_cases_overview()` function; call it in `build_comprehensive_substitutions()` replacing the old `_tc_raw_path` read; result used as `D.testCasesContent` |
| **`generate_test_cases_overview.py`** (new) | Create | Thin CLI wrapper that imports and calls `build_test_cases_overview()` from `build_summary_comprehensive.py`; accepts `--project` arg; always overwrites |
| `summary-agent.md` | Modify | Update Step 0 F1 read list; update `D.testCasesContent` data source mapping and description |
| `summary-validate-agent.md` | Modify | Add C11.38 rule: `test-cases-overview.md` exists after summary generation when `test-cases.md` has CT- entries |
| `validate_summary.py` | Modify | Implement C11.38 check |

---

## 3. Detailed Changes

### 3.1 New Function: `build_test_cases_overview()` in `build_summary_comprehensive.py`

The extraction logic lives as a new function **inside `build_summary_comprehensive.py`** — consistent with the existing `build_test_cases()`, `build_risk_data()`, etc. pattern. This avoids subprocess overhead and keeps the pipeline self-contained.

**Signature**:
```python
def build_test_cases_overview(asis_dir: Path, limit: int = 10) -> str:
    """Generate test-cases-overview.md and return its content.

    Always overwrites the overview file (refreshes on every summary run).
    limit: number of rows in the preview table (default 10, not exposed via CLI).
    Returns the written content as a string, or "" when test-cases.md is absent.
    """
```

**Algorithm**:
1. **Locate source**: `asis_dir / "qa" / "test-cases.md"`
   - If not found: return `""`
2. **Extract test cases** (same parser used by `build_test_cases()`):
   - Split content on `^## CT-` (regex, multiline)
   - For each block extract: `id`, `title`, `priority`, `type`, `module`, `rules`, `steps` (count of `| N |` rows inside `### Passos`)
3. **Compute totals**: `total = len(all_blocks)`
4. **Select first 10**: `top10 = all_blocks[:10]`
5. **Build overview markdown** and **write** to `asis_dir / "qa" / "test-cases-overview.md"` (**always overwrite**):

```markdown
# Test Cases — Overview

> **Gerado automaticamente** por `build_summary_comprehensive.py`.
> Fonte: `asis/qa/test-cases.md`

## Resumo

| Métrica | Valor |
|---|---|
| Total de Test Cases | {total} |
| Test Cases exibidos nesta visão | {min(total, 10)} |

## Primeiros {min(total, 10)} Test Cases

| ID | Título | Módulo | Prioridade | Tipo | Regras | Passos |
|---|---|---|---|---|---|---|
| CT-001 | ... | ... | P0 | Funcional | BR-0001 | 5 |
...
```

6. **Return** the written string content.

---

### 3.1b Standalone CLI Script: `generate_test_cases_overview.py`

**Location**: `src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_test_cases_overview.py`

A **thin wrapper** for manual/CI invocation. It imports and calls `build_test_cases_overview()` from `build_summary_comprehensive.py`:

```python
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3] / "summary" / "utils"))
from build_summary_comprehensive import build_test_cases_overview

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    args = ap.parse_args()
    asis_dir = Path("projects") / args.project / "outputs" / "asis"
    content = build_test_cases_overview(asis_dir)
    if content:
        print(f"[OK] test-cases-overview.md generated")
        print(f"     Output: {asis_dir / 'qa' / 'test-cases-overview.md'}")
        sys.exit(0)
    else:
        print(f"[ERROR] test-cases.md not found at {asis_dir / 'qa' / 'test-cases.md'}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Always overwrites** the overview file (since `build_test_cases_overview()` always writes).

---

### 3.2 `build_summary_comprehensive.py` — Call `build_test_cases_overview()` and use result

In `build_comprehensive_substitutions()` / the main data-building block, **replace** the current `test_cases_content` assignment (lines ~7305–7306) with a call to the new function:

```python
# 3.2a — Generate overview (always overwrites) and use as D.testCasesContent
test_cases_content = build_test_cases_overview(asis_dir)   # returns "" when test-cases.md absent
```

The function always regenerates the overview file and returns its content as a string — ready for injection into `D.testCasesContent`. No subprocess, no conditional skip. Remove the old `_tc_raw_path` assignment.

### 3.3 `build_summary_comprehensive.py` — Change `D.testCasesContent` source

In the `_build_d_object()` / content embedding logic, change the source for `testCasesContent` from `test-cases.md` to `test-cases-overview.md`:

**Before** (current behavior):
```python
tc_content_path = asis_dir / "qa" / "test-cases.md"
test_cases_content = tc_content_path.read_text(encoding="utf-8", errors="replace") if tc_content_path.exists() else ""
```

**After** (new behavior):
```python
tc_overview_path = asis_dir / "qa" / "test-cases-overview.md"
tc_full_path = asis_dir / "qa" / "test-cases.md"
# Prefer overview; fall back to full file only if overview absent
if tc_overview_path.exists():
    test_cases_content = tc_overview_path.read_text(encoding="utf-8", errors="replace")
elif tc_full_path.exists():
    test_cases_content = tc_full_path.read_text(encoding="utf-8", errors="replace")
else:
    test_cases_content = ""
```

> **Note**: The `D.testCases` list (used for the KPI tiles and table — spec 025) is **NOT affected** by this change. `D.testCases` continues to be parsed directly from `test-cases.md`. Only `D.testCasesContent` (the full markdown string rendered via `_mdToHtml()`) is switched to the overview source.

---

### 3.4 `summary-agent.md` — Step 0 F1 Read List

Add to the **F1 — Diagnóstico AS-IS** read block (after the `test-cases.md` line):

```
Read: asis/qa/test-cases-overview.md  (compact overview — generated by generate_test_cases_overview.py; preferred source for D.testCasesContent)
```

---

### 3.5 `summary-agent.md` — `D.testCasesContent` Data Source Mapping

Update the data source mapping entry for `testCasesContent`:

| D.* Field | Source File(s) | Parser Pattern |
|---|---|---|
| `testCasesContent` | `asis/qa/test-cases-overview.md` (preferred); fallback: `asis/qa/test-cases.md` | Raw UTF-8 string; rendered via `_mdToHtml()` in the Test Cases section; `""` when both files absent. Overview is auto-generated by `generate_test_cases_overview.py` before embedding. |

---

### 3.6 `summary-agent.md` — `D.testCasesContent` Field Schema Description

Update the `D.*` Field Schemas table entry:

| D.* Field | Template Function | Required Keys |
|---|---|---|
| `D.testCasesContent` | `renderTestCasesContent()` | `string` — raw markdown content of `asis/qa/test-cases-overview.md` (compact: total count + first 10 rows); falls back to `test-cases.md` if overview absent; rendered via `_mdToHtml()` in the Test Cases section; `""` when both files absent |

---

### 3.7 `summary-validate-agent.md` — C11.38 Rule

Add to the **C11 Content Completeness & UI Cleanup** rule table:

| Rule | Level | Check | Auto-fix |
|---|---|---|---|
| C11.38 | `warn` | `asis/qa/test-cases-overview.md` exists when `asis/qa/test-cases.md` exists and has ≥ 1 `## CT-` heading | não |

Rationale: `warn` (not `error`) — the overview is auto-generated by `build_summary_comprehensive.py`; if it is missing, the builder should have generated it. A `warn` signals a build anomaly without blocking the summary.

Also update the rule count in the agent `description` frontmatter (increment by 1).

---

### 3.8 `validate_summary.py` — C11.38 Implementation

```python
def _c11_38(ctx: Ctx) -> Result:
    """test-cases-overview.md exists when test-cases.md has CT- headings."""
    asis_dir = ctx.outputs_dir / "asis"
    tc_path = asis_dir / "qa" / "test-cases.md"
    overview_path = asis_dir / "qa" / "test-cases-overview.md"
    if not tc_path.exists():
        return Result(True, "test-cases.md absent — C11.38 skipped")
    text = tc_path.read_text(encoding="utf-8", errors="replace")
    has_ct = bool(re.search(r'^## CT-', text, re.MULTILINE))
    if not has_ct:
        return Result(True, "test-cases.md has no CT- headings — C11.38 skipped")
    exists = overview_path.exists()
    return Result(
        exists,
        "test-cases-overview.md present" if exists
        else "test-cases.md has CT- entries but test-cases-overview.md is missing — "
             "run generate_test_cases_overview.py or re-run build_summary_comprehensive.py"
    )
```

Register in `CHECKS` list with `id="C11.38"`, `level="warn"`.

---

## 4. User Scenarios

### Scenario 1 — Overview generated and displayed in HTML

**Story**: Como revisor do pipeline, quero ver apenas o resumo compacto dos test cases AS-IS no relatório HTML, sem que o arquivo seja inflado pelo conteúdo completo de centenas de casos de teste.

```gherkin
Given asis/qa/test-cases.md exists with 120 CT- blocks
And asis/qa/test-cases-overview.md does not yet exist
When build_summary_comprehensive.py runs
Then generate_test_cases_overview.py is invoked automatically
And test-cases-overview.md is created with total=120 and table of first 10 rows
And D.testCasesContent contains the content of test-cases-overview.md (not test-cases.md)
And the Test Cases section in the HTML renders the compact overview via _mdToHtml()
```

### Scenario 2 — Overview already exists; always overwritten

**Story**: Como desenvolvedor, quero que o builder sempre regenere o overview para refletir o estado atual de test-cases.md.

```gherkin
Given asis/qa/test-cases.md exists with 50 CT- blocks
And asis/qa/test-cases-overview.md already exists (previously generated)
When build_summary_comprehensive.py runs
Then build_test_cases_overview() is called and overwrites test-cases-overview.md
And D.testCasesContent is populated from the freshly generated test-cases-overview.md
```

### Scenario 3 — Script run standalone via CLI

**Story**: Como engenheiro do pipeline, quero poder regenerar o overview manualmente apontando para um projeto específico.

```gherkin
Given I run: python generate_test_cases_overview.py --project processaERP
And projects/processaERP/outputs/asis/qa/test-cases.md exists with 80 CT- blocks
When the script completes
Then exit code is 0
And test-cases-overview.md is created at projects/processaERP/outputs/asis/qa/test-cases-overview.md
And the file contains a "Total de Test Cases: 80" row in the Resumo table
And the file contains exactly 10 rows in the "Primeiros 10 Test Cases" table
```

### Scenario 4 — Source file absent; script exits with error

```gherkin
Given projects/myproject/outputs/asis/qa/test-cases.md does not exist
When I run: python generate_test_cases_overview.py --project myproject
Then exit code is 1
And console prints: [ERROR] test-cases.md not found at projects/myproject/outputs/asis/qa/test-cases.md
```

### Scenario 5 — Graceful degradation when test-cases.md is empty or malformed

```gherkin
Given asis/qa/test-cases.md exists but has no ## CT- headings
When build_summary_comprehensive.py runs
Then build_test_cases_overview() writes test-cases-overview.md with total=0 and an empty table
And D.testCasesContent contains the minimal overview (no crash)
And D.testCases remains [] (unchanged — sourced by build_test_cases())
```

### Scenario 6 — Validator detects missing overview when source exists

```gherkin
Given asis/qa/test-cases.md has 30 CT- headings
And asis/qa/test-cases-overview.md does not exist
When validate_summary.py runs
Then C11.38 fires as a "warn"
And the validation report lists remediation pointing to generate_test_cases_overview.py
```

---

## 5. Quality Gate Requirements

- [ ] Script uses `argparse`; no hardcoded project names (Article I)
- [ ] Output path uses lowercase `{project_name}` (Article II)
- [ ] `build_summary_comprehensive.py` does not crash if subprocess call fails (graceful fallback to full `test-cases.md`)
- [ ] `D.testCases` list (KPI tiles + table — spec 025) continues to be sourced from `test-cases.md` — unchanged
- [ ] `D.testCasesContent` is now sourced from `test-cases-overview.md` (preferred) or `test-cases.md` (fallback)
- [ ] C11.38 validator rule added with `warn` level
- [ ] No regression to existing C11.37 rule (spec 025)
- [ ] Script has no external dependencies beyond Python stdlib + pathlib

---

## 6. Dependencies

| Dependency | Component | Reason |
|---|---|---|
| Spec 025 — Test Cases AS-IS Menu | `summary-agent.md`, `build_summary_comprehensive.py` | This spec modifies the same `D.testCasesContent` data path introduced in spec 025 |
| `ava-asis-bridge-fastqa` | `test-cases.md` producer | Source file must exist for the script to run |

---

## 7. Exclusions

- `D.testCases` (KPI tiles and sortable table — spec 025) — sourced from `test-cases.md` directly; **not changed by this spec**
- Modification of `test-cases.md` itself — the script is read-only with respect to the source
- Regeneration on every summary build — only runs when `test-cases-overview.md` is absent
- Changes to the sidebar navigation item, section structure, or `renderTestCasesContent()` JS function — no HTML template changes required
- **"View all" link or expandable section** — the 10-row table + total count is the complete view in the HTML; the Summary is an executive/pipeline-review artifact and full test cases remain accessible via `asis/qa/test-cases.md` directly

---

## 8. Assumptions

- `test-cases.md` follows the `## CT-NNN — {title}` heading convention established by `ava-asis-bridge-fastqa` (Step 17b)
- Python stdlib (`re`, `pathlib`, `argparse`) is sufficient; no third-party packages needed
- `generate_test_cases_overview.py` is invoked by `build_summary_comprehensive.py` via `subprocess.run` (same pattern as other utility scripts in the pipeline)
- The overview artifact is stable once generated — it only needs regeneration if `test-cases.md` is updated (manual re-run)

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Overview artifact generated | `test-cases-overview.md` created with correct total count and 10-row table when source exists |
| HTML displays compact content | `D.testCasesContent` in generated HTML comes from `test-cases-overview.md`, not `test-cases.md`, when the former exists |
| Script is independently runnable | `python generate_test_cases_overview.py --project <name>` exits 0 and produces correct output |
| No regression to spec 025 | `D.testCases` list and KPI tiles continue to work as before |
| Graceful fallback | If overview generation fails, builder uses `test-cases.md` without crashing |
| Validator coverage | C11.38 emits `warn` when `test-cases-overview.md` is missing but `test-cases.md` has CT- entries |

---

## Clarifications

### Session 2026-07-23

- Q: When clicking "Test Cases" in the HTML, should users be able to access ALL test cases (not just the first 10), or is the 10-case overview the complete view? → A: Overview only — the 10-row table + total count is the complete view; no "view all" link needed. Summary is executive/pipeline-review audience.
- Q: Should CLI `generate_test_cases_overview.py` always overwrite, or skip if exists? → A: Always overwrite (Option A). Additionally: the overview must be regenerated on EVERY `ava-summary` run (not just when absent). Logic incorporated as `build_test_cases_overview()` function inside `build_summary_comprehensive.py`; CLI script is a thin wrapper that imports this function.
- Q: Should the row limit (10) be hardcoded or exposed as a `--limit N` CLI argument? → A: Hardcode 10. No `--limit` param. Function signature uses `limit: int = 10` internally for future extensibility, but CLI does not expose it.
