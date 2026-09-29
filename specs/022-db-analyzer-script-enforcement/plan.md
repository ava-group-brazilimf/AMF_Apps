# Implementation Plan: DB-Analyzer Script Enforcement & AST Completeness Validation

**Branch**: `022-db-analyzer-script-enforcement` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-db-analyzer-script-enforcement/spec.md`

## Summary

This feature modifies the existing `ava-asis-db-analyzer` agent (v1.4.0 → v1.5.0) to enforce deterministic script execution for ER diagram generation, add DFM-to-DDL transformation for AST artifact consumption, and implement post-generation completeness assertions. This is an agent behavioral specification change — no new software modules, APIs, or data models are introduced.

## Technical Context

**Language/Version**: Agent instructions (Brazilian Portuguese per Constitution Article V)

**Primary Dependencies**: Existing Python scripts (`gen_er_diagram.py`, `validate_diagram.py`)

**Storage**: N/A — agent specification file only

**Testing**: Manual validation via agent execution in IMFAI pipeline

**Target Platform**: IMFAI F1 AS-IS Diagnostic phase

**Project Type**: Agent instruction modification

**Performance Goals**: N/A

**Constraints**: Must preserve existing non-Delphi fallback paths; must maintain `build_summary_comprehensive.py` parser contracts

**Scale/Scope**: Single agent file modification (~200 lines of instruction text)

## Constitution Check

*GATE: Must pass before implementation*

- [x] Agent name pattern (`^ava-[a-z0-9-]+$`) — `ava-asis-db-analyzer`
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools`
- [x] Output paths use lowercase `{project_name}`
- [x] BDD scenarios cover nominal, edge, gate paths
- [x] No technology versions hardcoded
- [x] Skill/Agent split declared

**Result**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/022-db-analyzer-script-enforcement/
├── spec.md              # Feature specification
├── tasks.md             # Implementation tasks
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/
├── db-analyzer.md              # Agent body — PRIMARY EDIT TARGET
└── skills/
    ├── mysql-agent.md          # Unchanged
    ├── mariadb-agent.md        # Unchanged
    ├── oracle-agent.md         # Unchanged
    └── sqlserver-agent.md      # Unchanged

src/shared/tools/
└── gen_er_diagram.py           # Existing script — must be invoked

src/shared/utils/
└── validate_diagram.py         # Existing validator — must be used
```

## Complexity Tracking

No constitution violations require justification.
