# Implementation Plan: Test Cases Overview Extractor

**Spec**: `specs/028-test-cases-overview-extractor/spec.md`
**Branch**: `028-test-cases-overview-extractor`
**Change Type**: `modify-existing` + new utility script
**Tech Stack**: Python 3.x, stdlib only (re, pathlib, argparse)

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | modify-existing + new utility script |
| **Phase** | F8 — Summary (ava-summary) |
| **Module** | `summary` |
| **Primary Requirement** | Embed only a compact overview (total count + first 10 rows) instead of the full `test-cases.md` content in the Summary HTML |
| **Technical Approach** | Add `build_test_cases_overview()` to `build_summary_comprehensive.py`; replace the `_tc_raw_path` read with a call to the new function; add thin CLI wrapper; add C11.38 validator rule |

---

## Constitution Check

*This spec modifies existing Python utility scripts and agent `.md` files — not a new agent creation. Constitution articles mapped accordingly.*

- [x] **Article I** — No technology versions hardcoded; Python stdlib only, no version-pinned deps
- [x] **Article II** — No new agent frontmatter; `summary-agent.md` version bump only (PATCH 1.8.0 → 1.8.1)
- [x] **Article III** — Phase placement unchanged; `ava-summary` remains F8
- [x] **Article IV** — No new agent registered; `module.yaml` N/A
- [x] **Article V** — `summary-agent.md` body is Portuguese; plan and spec are English (correct)
- [x] **Article VI** — BDD scenarios in spec section 4 cover nominal, overwrite, CLI, edge, graceful-degradation paths
- [x] **Article VII** — Security: no user input reaches the new function; paths come from `project_name` (internal); no injection risk
- [x] **Article VIII** — N/A; utility scripts do not emit `AgentResult`
- [x] **Article IX** — N/A; changes are LLM prompt files + Python utilities, not generated application code
- [x] **Article X** — Version bumps: `summary-agent.md` PATCH 1.8.0 → 1.8.1; `summary-validate-agent.md` PATCH
- [x] **Article XI** — No new Skill/Agent split required; changes are internal to existing agents

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec
- [x] All outputs follow `projects/{project_name}/outputs/asis/qa/...`
- [x] Downstream consumer confirmed: `renderTestCasesContent()` in `summary-template.html` (no template change needed)

---

## 1. Technical Context

| Dimension | Detail | Source |
|---|---|---|
| Python runtime | 3.x, stdlib only: `re`, `pathlib`, `argparse` | Existing utils in same module use same pattern |
| Existing parser | `build_test_cases()` at line ~6722 in `build_summary_comprehensive.py` | Confirmed via code read |
| Current `testCasesContent` source | Lines ~7305-7306: reads `test-cases.md` raw with `_tc_raw_path` | Confirmed via code read |
| Validator pattern | `_c11_N(ctx: Ctx) -> Result` registered in `CHECKS` list at line ~2287 | Confirmed via code read |
| C11 last rule | `_c11_37` at line 1763; registered in CHECKS at line ~2658 | Confirmed via code read |
| CLI wrapper pattern | `generate_fallback_artifacts.py` in `asis-diagnostic/utils/` | Confirmed; same directory |
| HTML rendering | `D.testCasesContent` → `renderTestCasesContent()` → `_mdToHtml()` | No template change needed |

---

## 2. Phase Placement

This change affects only the **F8 — Summary** phase:

```
... -> ava-summary (F8)
         |
         +-- build_summary_comprehensive.py
               |
               +-- build_test_cases_overview()  [NEW — always runs, always overwrites]
               +-- build_test_cases()            [UNCHANGED — D.testCases source]
               +-- test_cases_content = ...      [CHANGED — calls overview fn, not raw read]
```

`ava-summary` invocation sequence is unchanged. The new function is called in the same data-extraction block as `build_test_cases()`.

**Quality gate at this phase**: `summary-validator` (after every phase) — extended with C11.38 (`warn`).

Conditions for `human_gate_required: true`: N/A — utility-level change, no risk escalation.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO — no entity changes
Application    -> NO — no use case changes
Infrastructure -> NO — filesystem reads/writes only (existing pattern)
Presentation   -> NO — no HTML template changes
```

Cross-layer coupling: NONE — `build_test_cases_overview()` is a pure utility function (Path in → str out + file written).

---

## 4. File Structure

### New function (primary change)
```
src/modules/ava-fabric-agents/summary/utils/
  build_summary_comprehensive.py       [MODIFY — add build_test_cases_overview(); update line ~7305]
  validate_summary.py                  [MODIFY — add _c11_38(); register in CHECKS]
```

### New CLI wrapper
```
src/modules/ava-fabric-agents/asis-diagnostic/utils/
  generate_test_cases_overview.py      [CREATE — thin wrapper importing build_test_cases_overview()]
```

### Agent documentation
```
src/modules/ava-fabric-agents/summary/agents/
  summary-agent.md                     [MODIFY — Step 0 read list; D.testCasesContent mapping; v1.8.1]
  summary-validate-agent.md            [MODIFY — C11.38 rule entry; increment rule count]
```

**Dispatch mode**: internal-only — no new SKILL.md.

---

## 5. module.yaml Impact

**N/A** — no new agents registered.

---

## 6. Observability & Trace Propagation

**N/A** — utility scripts do not emit `AgentResult` and do not propagate `trace_id`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | — |
| `agent-result.schema.json` | NO | — |
| `D.*` field schema (`summary-agent.md`) | PATCH | `D.testCasesContent` description updated: preferred source is `test-cases-overview.md` |

---

## 8. Implementation Phases

### Phase 0 — Research (COMPLETE — inline)

All unknowns resolved via codebase inspection before planning:

| Unknown | Resolution |
|---|---|
| Insertion point for `build_test_cases_overview()` | After `build_test_cases()` body (~line 6795 in `build_summary_comprehensive.py`) |
| Lines to replace for `test_cases_content` | Lines ~7305-7306 (two lines → one call) |
| `_c11_38` insertion point | After `_c11_37` body (~line 1784), before `# Auto-fix functions` comment |
| C11.38 CHECKS entry point | After C11.37 entry (~line 2665), before `Check("C12.1", ...)` |
| CLI wrapper import path | `sys.path.insert(0, str(_SCRIPT_DIR.parents[2] / "summary" / "utils"))` |
| `build_test_cases_overview()` reuses parser | Calls `build_test_cases(asis_dir)` internally; slices `[:limit]` |

No `research.md` file required — all research is documented inline above.

---

### Phase 1 — Design & Contracts

#### Data Model: `TestCaseRow` (unchanged — same dict as `build_test_cases()`)

```python
{
    "id":       str,   # "CT-001"
    "title":    str,   # "Baixa Completa de Conta a Pagar"
    "priority": str,   # "P0"
    "type":     str,   # "Funcional"
    "module":   str,   # "Contas a Pagar — Baixa"
    "rules":    str,   # "BR-0001, BR-0002"
    "steps":    int,   # count of data rows in ### Passos table
}
```

#### Output Contract: `test-cases-overview.md`

Path: `projects/{project_name}/outputs/asis/qa/test-cases-overview.md`

```markdown
# Test Cases — Overview

> **Gerado automaticamente** por `build_summary_comprehensive.py`.
> Fonte: `asis/qa/test-cases.md`

## Resumo

| Métrica | Valor |
|---|---|
| Total de Test Cases | {total} |
| Test Cases exibidos nesta visão | {displayed} |

## Primeiros {displayed} Test Cases

| ID | Título | Módulo | Prioridade | Tipo | Regras | Passos |
|---|---|---|---|---|---|---|
| {id} | {title} | {module} | {priority} | {type} | {rules} | {steps} |
...
```

Where `displayed = min(total, limit)` and `limit = 10` (default, not exposed via CLI).

#### `build_test_cases_overview()` — Full Implementation

```python
def build_test_cases_overview(asis_dir: Path, limit: int = 10) -> str:
    """Generate test-cases-overview.md and return its content.

    Always overwrites the output file (called on every summary run).
    Reuses build_test_cases() for parsing — single source of truth.
    Returns written content string, or "" when test-cases.md is absent.
    limit: max rows in preview table (default 10, not exposed via CLI).
    """
    tc_path = asis_dir / "qa" / "test-cases.md"
    overview_path = asis_dir / "qa" / "test-cases-overview.md"

    if not tc_path.exists():
        return ""

    all_cases = build_test_cases(asis_dir)
    total = len(all_cases)
    top = all_cases[:limit]
    displayed = len(top)

    rows = "\n".join(
        f"| {c['id']} | {c['title']} | {c['module']} | {c['priority']} "
        f"| {c['type']} | {c['rules']} | {c['steps']} |"
        for c in top
    )
    if not rows:
        rows = "| — | — | — | — | — | — | — |"

    content = (
        "# Test Cases — Overview\n\n"
        "> **Gerado automaticamente** por `build_summary_comprehensive.py`.\n"
        "> Fonte: `asis/qa/test-cases.md`\n\n"
        "## Resumo\n\n"
        "| Métrica | Valor |\n"
        "|---|---|\n"
        f"| Total de Test Cases | {total} |\n"
        f"| Test Cases exibidos nesta visão | {displayed} |\n\n"
        f"## Primeiros {displayed} Test Cases\n\n"
        "| ID | Título | Módulo | Prioridade | Tipo | Regras | Passos |\n"
        "|---|---|---|---|---|---|---|\n"
        f"{rows}\n"
    )

    overview_path.parent.mkdir(parents=True, exist_ok=True)
    overview_path.write_text(content, encoding="utf-8")
    return content
```

#### Replacement in `build_comprehensive_substitutions()` (~lines 7305-7306)

Remove:
```python
    _tc_raw_path = asis_dir / "qa" / "test-cases.md"
    test_cases_content = _tc_raw_path.read_text(encoding="utf-8", errors="replace") if _tc_raw_path.exists() else ""
```

Replace with (single line):
```python
    test_cases_content = build_test_cases_overview(asis_dir)
```

#### `_c11_38()` — Full Implementation

```python
def _c11_38(ctx: Ctx) -> Result:
    """test-cases-overview.md exists after summary generation when test-cases.md
    has CT- headings. Level is warn: the overview is auto-generated by
    build_summary_comprehensive.py on every run; if missing it indicates that
    build_test_cases_overview() was not called."""
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
             "build_test_cases_overview() must be called during every summary build; "
             "verify the call replaced the old _tc_raw_path read in build_comprehensive_substitutions()"
    )
```

#### CHECKS registration (after C11.37 entry, before C12.1)

```python
    Check("C11.38", "Content Completeness", "warn",
          "test-cases-overview.md exists when test-cases.md has CT- headings",
          "build_test_cases_overview() in build_summary_comprehensive.py must always be called "
          "and must write test-cases-overview.md — verify it replaced the old _tc_raw_path read.",
          _c11_38),
```

#### CLI wrapper — `generate_test_cases_overview.py`

```python
#!/usr/bin/env python3
"""
generate_test_cases_overview.py

CLI wrapper for build_test_cases_overview().
Generates projects/{project_name}/outputs/asis/qa/test-cases-overview.md.
Always overwrites the output file.

Usage:
    python generate_test_cases_overview.py --project <project_name>
"""
import sys
import argparse
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR.parents[2] / "summary" / "utils"))

from build_summary_comprehensive import build_test_cases_overview  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate test-cases-overview.md from test-cases.md"
    )
    ap.add_argument("--project", required=True, help="Project name (e.g. processaERP)")
    args = ap.parse_args()

    asis_dir = Path("projects") / args.project / "outputs" / "asis"
    if not (asis_dir / "qa" / "test-cases.md").exists():
        print(f"[ERROR] test-cases.md not found at {asis_dir / 'qa' / 'test-cases.md'}")
        return 1

    content = build_test_cases_overview(asis_dir)
    if content:
        print(f"[OK] test-cases-overview.md generated")
        print(f"     Output: {asis_dir / 'qa' / 'test-cases-overview.md'}")
        return 0
    print(f"[ERROR] build_test_cases_overview() returned empty — check test-cases.md format")
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

---

## 9. Complexity Tracking

| Gate | Status | Notes |
|---|---|---|
| Article I (no hardcoding) | PASS | `limit=10` is a default parameter, not hardcoded |
| Article IV (module.yaml) | N/A | No new agent |
| Summary Validator | PASS | C11.38 is `warn`; no existing `error` checks affected |
| Regression — `D.testCases` (spec 025) | LOW RISK | `build_test_cases()` call is unchanged; only `test_cases_content` source changes |
| Regression — `D.testCasesContent` display | LOW RISK | `_mdToHtml()` renders any valid markdown; overview format is valid |

---

## 10. Test Strategy

| Test | Type | Validation |
|---|---|---|
| `build_test_cases_overview()` with valid `test-cases.md` (>10 CT-) | Integration | Run builder; check overview has `Total = N` and exactly 10 table rows |
| `build_test_cases_overview()` with `test-cases.md` absent | Edge | Returns `""`; no file written |
| `build_test_cases_overview()` with 0 CT- headings | Edge | Returns content with `total=0` and `| — | ... |` empty row |
| `build_test_cases_overview()` with < 10 CT- blocks | Edge | `displayed = actual count` (not padded to 10) |
| `build_test_cases_overview()` always overwrites | Regression | Run twice; verify file content is from second run |
| CLI wrapper exit 0 | Integration | `python generate_test_cases_overview.py --project processaERP` |
| CLI wrapper exit 1 (no source) | Edge | Project with no `test-cases.md` |
| `D.testCasesContent` in HTML is overview | Integration | Grep HTML for `# Test Cases — Overview` heading |
| C11.38 fires `warn` when overview absent | Validator | Delete overview; run `validate_summary.py`; check C11.38 in report |
| C11.38 skipped when `test-cases.md` absent | Validator | Project with no `test-cases.md` |
| C11.37 no regression (spec 025) | Validator | Verify `D.testCases` still populated |
| `D.testCases` KPI tiles no regression | Integration | Verify KPI count correct after change |

---

## Implementation Checklist

### Cat 1 — `build_summary_comprehensive.py` (primary)
- [ ] 1.1 Add `build_test_cases_overview(asis_dir: Path, limit: int = 10) -> str` after `build_test_cases()` body (~line 6795)
- [ ] 1.2 Replace lines ~7305-7306 (`_tc_raw_path` / `test_cases_content` 2-liner) with `test_cases_content = build_test_cases_overview(asis_dir)`

### Cat 2 — `validate_summary.py`
- [ ] 2.1 Add `_c11_38(ctx: Ctx) -> Result` after `_c11_37` body (~line 1784), before `# Auto-fix functions`
- [ ] 2.2 Register `Check("C11.38", ...)` in `CHECKS` after C11.37 entry (~line 2665), before `Check("C12.1", ...)`

### Cat 3 — CLI wrapper (new file)
- [ ] 3.1 Create `src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_test_cases_overview.py`

### Cat 4 — `summary-agent.md`
- [ ] 4.1 Add `Read: asis/qa/test-cases-overview.md` to Step 0 F1 read block (after the `test-cases.md` line)
- [ ] 4.2 Update `D.testCasesContent` row in D.* Field Schemas table (preferred source is overview)
- [ ] 4.3 Update `testCasesContent` row in Data Source Mapping table
- [ ] 4.4 Bump `version: 1.8.0` → `version: 1.8.1` in frontmatter

### Cat 5 — `summary-validate-agent.md`
- [ ] 5.1 Add C11.38 row to C11 rule table
- [ ] 5.2 Increment rule count in agent `description` frontmatter


