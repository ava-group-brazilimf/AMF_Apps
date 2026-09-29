# Implementation Plan: Unicode-Safe Regex Guardrail

**Branch**: `007-unicode-safe-regex-guardrail` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-unicode-safe-regex-guardrail/spec.md`

---

## Summary

| Field | Value |
|---|---|
| **Agent IDs** | `ava-stack-dotnet-backend`, `ava-stack-angular-frontend` |
| **Phase** | `F3` (Tech Stack) |
| **Module** | `tech-stack` |
| **Primary Requirement** | Prevent generation of `[a-zA-Z]` regex patterns for PT-BR text fields; enforce `\p{L}` (backend) and `/^[\p{L}\s\-']+$/u` (frontend) |
| **Technical Approach** | Add Guardrail G10 to `coder-dotnet-backend.md`, add equivalent GUARDRAIL block to `coder-angular-frontend.md`, add canonical PT-BR Validation Patterns section to `angular-patterns-reference.md`; PATCH bump both agents |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Article | Requirement | Status |
|---|---|---|
| I — Config-Driven | No technology versions hardcoded in guardrail text | ✅ PASS |
| II — Agent Contract Standard | PATCH version bump; no frontmatter fields added/removed | ✅ PASS |
| III — Pipeline Execution Contract | No pipeline sequence changes (bugfix, not new phase) | ✅ PASS |
| IV — Module Registration | No new agent → no `module.yaml` update needed (modify-existing) | ✅ PASS |
| V — Language Convention | All new guardrail text written in pt-BR | ✅ PASS |
| VI — BDD Scenarios | Spec section 4 covers nominal (S1, S2), reference (S3), edge (S4) | ✅ PASS |
| VII — Security Sub-pipeline | No security surface change; Unicode-permissive is correct | ✅ PASS |
| VIII — trace_id | N/A — LLM prompt `.md` files; no trace_id propagation | ✅ PASS |
| IX — Clean Architecture | N/A — agent is an LLM prompt file, not a code artifact | ✅ PASS |
| X — Version Bump | PATCH (`1.0.0 → 1.0.1`) — bug fix, no contract change | ✅ PASS |
| XI — Skill/Agent Split | Existing SKILL.md unchanged; modify-existing | ✅ PASS |

**DECISION: PROCEED** — all gates pass.

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime | .NET 8, C# 12 | reference-architecture.yaml → tech_stack.backend |
| Frontend | Angular 17, TypeScript 5.3 | reference-architecture.yaml → tech_stack.frontend |
| Agent files | Markdown (`.md`) | Agent instruction format — IMFAI standard |
| Testing | PowerShell `Select-String` greps | quickstart.md |
| No new dependencies | — | Bugfix only; no new packages |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

**N/A** — This is a `bugfix` (modify-existing) targeting `F3` Tech Stack agents.
No pipeline sequence changes. Both agents are already registered and dispatched
via existing SKILL.md files.

---

## 3. Clean Architecture Alignment

N/A — both agents are LLM prompt `.md` files. Clean Architecture applies to generated
code artifacts, not to agent instruction files.

---

## 4. Agent File Structure (modify-existing)

**No new files created in `src/` or `.github/skills/`.**

Files modified in-place:

```
src/modules/ava-fabric-agents/tech-stack/agents/
├── coder-dotnet-backend.md     ← version 1.0.0 → 1.0.1, +G10 block
└── coder-angular-frontend.md   ← version 1.0.0 → 1.0.1, +principle line, +GUARDRAIL block

src/shared/data/patterns/angular/
└── angular-patterns-reference.md  ← version 1.0.0 → 1.0.1, +PT-BR Validation Patterns section
```

---

## 5. module.yaml Impact

**N/A** — `modify-existing` change type. Both agents are already registered in
`src/modules/ava-fabric-agents/tech-stack/module.yaml`. No new entries needed.

---

## 6. Observability & Trace Propagation

**N/A** — LLM prompt `.md` files. No trace_id propagation required.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| agent-task.schema.json | NO | No new input fields |
| agent-result.schema.json | NO | No new output fields |

---

## 8. Implementation Steps (tasks.md breakdown preview)

| # | Task | File | Category |
|---|---|---|---|
| 1 | Bump version to `1.0.1` in `coder-dotnet-backend.md` | `coder-dotnet-backend.md` line 10 | Cat 2 |
| 2 | Insert G10 guardrail block after G9 | `coder-dotnet-backend.md` ~line 209 | Cat 2 |
| 3 | Bump version to `1.0.1` in `coder-angular-frontend.md` (2 occurrences) | `coder-angular-frontend.md` lines 3, 12 | Cat 2 |
| 4 | Add Unicode-safe principle one-liner to tech principles list | `coder-angular-frontend.md` ~line 69 | Cat 2 |
| 5 | Add GUARDRAIL (Unicode Regex PT-BR) block in GUARDRAILS DE BUILD | `coder-angular-frontend.md` ~line 870 | Cat 2 |
| 6 | Bump version to `1.0.1` in `angular-patterns-reference.md` frontmatter | `angular-patterns-reference.md` line 4 | Cat 2 |
| 7 | Append PT-BR Validation Patterns section at end of file | `angular-patterns-reference.md` EOF | Cat 2 |
| 8 | Update agent context reference in `copilot-instructions.md` | `.github/copilot-instructions.md` | Cat 5 |

*Full task breakdown with IMFAI 7-category format generated by `/speckit.tasks`.*

---

## 9. Complexity Tracking

No constitution violations. No complexity justification required.

---

## 10. Test Strategy

| Test | Tool | Target | Pass Criterion |
|---|---|---|---|
| G10 presence | `Select-String` | `coder-dotnet-backend.md` | `### G10` heading found |
| Version bump backend | `Select-String` | `coder-dotnet-backend.md` | `version: "1.0.1"` |
| Angular guardrail presence | `Select-String` | `coder-angular-frontend.md` | `GUARDRAIL (Unicode Regex PT-BR)` found |
| Principle one-liner presence | `Select-String` | `coder-angular-frontend.md` | `Regex PT-BR Unicode-safe` found |
| Version bump frontend (×2) | `Select-String` | `coder-angular-frontend.md` | both `version` = `1.0.1` |
| PT-BR section presence | `Select-String` | `angular-patterns-reference.md` | `## PT-BR Validation Patterns` found |
| No forbidden patterns outside notes | `Select-String + Where-Object` | both agent `.md` files | 0 unguarded `[a-zA-Z]` matches |

Full quickstart commands: [quickstart.md](quickstart.md)
