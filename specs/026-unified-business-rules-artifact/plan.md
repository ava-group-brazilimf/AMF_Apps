# Implementation Plan: Unified Business Rules & Functional Requirements Artifact

**Branch**: `026-unified-business-rules-artifact` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

---

## Summary

| Field | Value |
|---|---|
| **Agents modified** | `ava-asis-documentation` (v1.6.0 → v2.0.0), `ava-asis-solution-delphi` (v2.5.0 → v2.6.0) |
| **Agents updated (refs only)** | 22 agent files referencing `functional-requirements.md`; 5 coder files with `code-business-rules.md` |
| **Scripts modified** | `build_summary_comprehensive.py`, `build_summary_complete.py`, `validate_summary.py` |
| **Phase** | F1 (AS-IS), cross-cutting (Summary + TO-BE + QA + Tech-Stack) |
| **Primary Requirement** | Merge `functional-requirements.md` and `code-business-rules.md` into a single unified `asis/docs/business-rules.md` with two sections: `## Functional Requirements` (FR-NNN) then `## Business Rules` (BR-NNN) |
| **Technical Approach** | (1) Add `BRF` trigger to `documentation-asis.md` — single-pass atomic write. (2) Update `RF`/`RN` to upsert their own section. (3) Update orchestrator dispatch chain. (4) Update summary parsers. (5) Remove `code-business-rules.md` from `solution-delphi.md`. (6) Update all downstream Input Contract references. |

---

## Technical Context

**Language/Version**: Markdown (agent bodies in pt-BR); Python 3 (summary utilities — stdlib only)

**Primary Dependencies**: `build_summary_comprehensive.py`, `build_summary_complete.py`, `validate_summary.py` — pure stdlib (regex, pathlib, json)

**Storage**: `projects/{project_name}/outputs/asis/docs/business-rules.md` (unified artifact)

**Testing**: `python validate_summary.py` on a project with unified artifact; grep audit over all impacted files

**Target Platform**: N/A — agent `.md` instruction files + Python utility scripts

**Project Type**: `modify-existing` — no new agents, no new modules

**Constraints**: `parse_func_reqs()` must support both new path (`business-rules.md`) and legacy path (`functional-requirements.md`) via fallback — consistent with existing codebase pattern

**Scale/Scope**: 29 agent/script files; ~150 targeted line edits

---

## Constitution Check

- [X] **Article I** — No technology versions hardcoded; Python parsing uses regex/pathlib only
- [X] **Article II** — `ava-asis-documentation` → v2.0.0 (MAJOR: output contract removal); `ava-asis-solution-delphi` → v2.6.0 (MINOR); names remain `^ava-[a-z0-9-]+$`; no new frontmatter fields
- [X] **Article III** — No pipeline phase sequence change; orchestrator-asis.md dispatch chain updated in-place
- [X] **Article IV** — No new agents → `module.yaml` unchanged
- [X] **Article V** — Agent body text in Brazilian Portuguese; all affected agents already comply
- [X] **Article VI** — 5 BDD scenarios in spec Section 6 covering all modified paths
- [X] **Article VII** — No security sub-pipeline impact; no F1 security agent modified
- [X] **Article VIII** — `trace_id` propagation unaffected
- [X] **Article IX** — N/A: no Clean Architecture layers modified
- [X] **Article X** — MAJOR bump for `ava-asis-documentation`; MINOR for `ava-asis-solution-delphi`
- [X] **Article XI** — Both primary agents already have SKILL.md wrappers; no split change needed

### Quality Gate Check

- [X] No `[NEEDS CLARIFICATION]` markers in spec
- [X] 5 clarifications recorded in spec § Clarifications
- [X] All impacted files catalogued in spec Section 5

---

## Project Structure

### Documentation (this feature)

```text
specs/026-unified-business-rules-artifact/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← /speckit.tasks output (not created here)
```

### Source Files Modified

```text
src/modules/ava-fabric-agents/
├── asis-diagnostic/
│   ├── agents/
│   │   ├── documentation-asis.md           ← v2.0.0: BRF trigger + unified output + DAG update
│   │   ├── solution-delphi.md              ← v2.6.0: remove code-business-rules.md generation
│   │   ├── orchestrator-asis.md            ← BRF dispatch + updated deps
│   │   └── bridge-fastqa-asis.md           ← update exclusion note
│   ├── shared/
│   │   ├── parser-contracts.md             ← update FR section context
│   │   ├── output-paths.md                 ← remove functional-requirements.md row
│   │   └── artifact-size-governance.md     ← update size rules for merged file
│   └── workflows/analyze-delphi/steps/
│       ├── step-03-documentation.md        ← update expected output
│       └── step-05-consolidation.md        ← update path
├── summary/
│   ├── agents/
│   │   ├── summary-agent.md                ← update parser reference
│   │   └── summary-validate-agent.md       ← update validation reference
│   ├── utils/
│   │   ├── build_summary_comprehensive.py  ← parse_func_reqs() call site + discovery list
│   │   ├── build_summary_complete.py       ← parse_functional_requirements() + discovery list
│   │   └── validate_summary.py             ← src path + Check C2.4 description
│   └── workflows/generate-summary/steps/
│       └── step-01-discover.md             ← remove functional-requirements.md row
├── tobe-architecture/agents/
│   ├── adr-tobe.md                         ← Input Contract: fr path → business-rules.md
│   ├── architecture-decision-matrix-tobe.md
│   ├── architecture-design-tobe.md
│   └── docs-tobe.md
├── prototype/agents/
│   └── prototype-agent.md                  ← Input Contract: fr path update
├── qa-agents/agents/
│   ├── behavior-mapping-agent.md
│   ├── exploratory-agent.md
│   ├── qa-orchestrator-agent.md
│   └── test-case-generator-agent.md
└── tech-stack/agents/
    ├── coder-dotnet-backend.md             ← remove code-business-rules.md fallback
    ├── coder-angular-frontend.md
    ├── coder-go-backend.md
    ├── coder-java-backend.md
    └── coder-python-backend.md
```

---

## Phase 0 — Research

### Resolved Questions

| Question | Answer | Evidence |
|---|---|---|
| Orchestrator dispatch chain for RF → RN? | `VC✓` → `doc:RF` (dep: `value-chain.md`); `RF✓` → `doc:RN` (dep: `functional-requirements.md`); `RF✓ + RN✓` → `bridge-fastqa` | `orchestrator-asis.md:204` |
| BRF replacement for the RF→RN chain? | `VC✓` → `doc:BRF` (dep: `value-chain.md`); `BRF✓` → `bridge-fastqa` | Spec § 4 + orchestrator model |
| `parse_func_reqs()` location + call site? | Defined at line 5396; called at line 7215 with `asis_dir / "docs" / "functional-requirements.md"` | `build_summary_comprehensive.py:5396,7215` |
| Artifact discovery entry in `build_summary_comprehensive.py`? | Line 169: `{"key": "functional-requirements", "path": "asis/docs/functional-requirements.md"}` | `build_summary_comprehensive.py:169` |
| `build_summary_complete.py` touch points? | Line 77 (discovery list); Line 949 (`parse_functional_requirements()`); Line 956 (hardcoded path); Line 2589 (call site) | `build_summary_complete.py:77,949,956,2589` |
| `validate_summary.py` touch points? | Line 300 (src path); Lines 2307–2308 (Check C2.4 description); Lines 2499–2500 (Check C11.7) | `validate_summary.py:300,2307,2499` |
| Does `parse_func_reqs()` need section-scoping? | No — FR-NNN regex already filters; `## Business Rules` headers (`BR-NNN`, `Domain:`) won't match FR patterns | `build_summary_comprehensive.py:5405-5450` + Spec § Clarification Q4 |
| Coder-agent fallback pattern to simplify? | `READ business-rules.md; READ code-business-rules.md → if code-business-rules.md: authoritative; else BLOCKED` | `coder-dotnet-backend.md:70-73` |
| `parse_func_reqs()` behavior on missing file? | Returns `[]` — safe to point at `business-rules.md`; no exception | `build_summary_comprehensive.py:5399-5400` |
| `FUNC_NAMES` constant at line 2144? | Set `{"functional-requirements", "business-rules", ...}` — remove `"functional-requirements"` entry; `"business-rules"` already present | `build_summary_comprehensive.py:2144` |

---

## Phase 1 — Design & Contracts

### Data Model

**Unified `business-rules.md` canonical structure (v2.0.0)**:

```markdown
# Business Rules & Functional Requirements — {project_name} AS-IS
**trace_id**: {trace_id}
**Generated**: {YYYY-MM-DD}

---

## Functional Requirements

[FR-NNN entries — Formato A section headers OR Formato B module tables]
[## ⚠️ Avisos de Validação (appended by cross-validation if FRs with unconfirmed modules exist)]

---

## Business Rules

[BR-NNN / RN-XX-NN entries — Formato A section headers OR Formato B domain tables]
```

**Section ordering**: `## Functional Requirements` FIRST, `## Business Rules` SECOND.
Rationale: matches BRF DAG execution order (FR extraction precedes BR mining).

**Write modes**:

| Trigger | Write mode | Sections written |
|---------|-----------|-----------------|
| `BRF` | Atomic full-file write | Both sections in declared order |
| `ALL` | Dispatches `BRF` | Both sections |
| `RF` (individual) | Upsert own section only | FR section only |
| `RN` (individual) | Upsert own section only | BR section only |

**Upsert algorithm** (RF/RN individual triggers):
1. File absent → create with own section only (no stubs for the absent section)
2. File present, own section found → replace from section header to next `---` or EOF
3. File present, own section absent → append section at end of file

---

### Parser Interface Changes

**`build_summary_comprehensive.py` — `parse_func_reqs()` call site (line 7215)**:

```python
# AFTER — path-fallback: support legacy functional-requirements.md for projects run before spec-026
_fr_path = asis_dir / "docs" / "business-rules.md"
if not _fr_path.exists():
    _fr_path = asis_dir / "docs" / "functional-requirements.md"  # legacy fallback
func_reqs = parse_func_reqs(_fr_path)
```

`parse_func_reqs()` body unchanged — FR-NNN regex already ignores BR-NNN/Domain: headers.

**`build_summary_comprehensive.py` — artifact discovery list (line 169)**:
- DELETE `{"key": "functional-requirements", "path": "asis/docs/functional-requirements.md"}` entry
- Existing `"business-rules"` entry at line ~170 already covers the unified file

**`build_summary_complete.py` — `parse_functional_requirements()` path (line 956)**:

```python
# AFTER
_fr_path = asis_dir / "docs" / "business-rules.md"
if not _fr_path.exists():
    _fr_path = asis_dir / "docs" / "functional-requirements.md"
text = read_text(_fr_path)
```

**`validate_summary.py` — `_c2_4()` src path (line 300)**:

```python
# AFTER
_src_br = ctx.outputs_dir / "asis" / "docs" / "business-rules.md"
_src_fr = ctx.outputs_dir / "asis" / "docs" / "functional-requirements.md"  # legacy
src = _src_br if _src_br.exists() else _src_fr
```

**`validate_summary.py` — Check C2.4 description (line 2308)**:

```python
# AFTER
"parse_func_reqs() reads ## Functional Requirements section from business-rules.md (legacy: functional-requirements.md).", _c2_4),
```

---

### Orchestrator Dispatch Update

**`orchestrator-asis.md` Phase B rules**:

```yaml
# BEFORE
- { trigger: "VC✓", dispatch: doc:RF, blocking: true, deps: value-chain.md }
- { trigger: "RF✓", dispatch: doc:RN, blocking: true, deps: functional-requirements.md }
- { trigger: "RF✓ + RN✓", dispatch: bridge-fastqa, blocking: false }

# AFTER
- { trigger: "VC✓",   dispatch: doc:BRF,       blocking: true,  deps: value-chain.md }
- { trigger: "BRF✓",  dispatch: bridge-fastqa, blocking: false }
```

Individual `doc:RF` and `doc:RN` remain valid for partial re-runs but are removed from the
primary Phase B dispatch chain.

---

### Coder Agent Pattern Update (all 5 files)

```markdown
# BEFORE
READ projects/{project_name}/outputs/asis/docs/business-rules.md
READ projects/{project_name}/outputs/asis/code-business-rules.md
  → SE code-business-rules.md existir: usar como fonte AUTORITATIVA de IDs BR-XXXX
  → SE nenhum dos dois existir: ⛔ BLOCKED — "business-rules.md/code-business-rules.md ausentes."

# AFTER
READ projects/{project_name}/outputs/asis/docs/business-rules.md
  → SE existir: usar IDs BR-XXXX da seção ## Business Rules
  → SE não existir: ⛔ BLOCKED — "asis/docs/business-rules.md ausente.
    Execute ava-asis-documentation (trigger BRF ou ALL) antes do codegen."
```

---

### contracts/

No external interfaces, public APIs, or CLI schemas are modified. `contracts/` directory omitted.
