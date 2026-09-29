# Agent Implementation Plan: Dotnet Coder Backend — Guardrails G10 & G11

**Branch**: `007-dotnet-compile-guardrails` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-dotnet-compile-guardrails/spec.md`

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-dotnet-backend` |
| **Phase** | F3 (Tech Stack — codegen) |
| **Module** | `tech-stack` |
| **Primary Requirement** | Add guardrails G10 (namespace conflict scan) and G11 (SDK version check) as pre-generation HARD STOP gates to `coder-dotnet-backend.md`, and repair the structural corruption introduced when G10/G11 were informally added. |
| **Technical Approach** | Replace the corrupted G10+G11 region with clean authoritative content (per spec §6–§7); update flow references; bump version 1.0.0 → 1.1.0. |
| **Change Type** | `modify-existing` — MINOR version bump |
| **Files changed** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` (only) |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9).*

### Constitution Gates

- [x] **Article I** -- No technology versions hardcoded in agent body — G11 reads version from `project-config.yaml → tobe_stack.backend_version`; `dotnet --version` is a runtime call; no literal version values in the guardrail text.
- [x] **Article II** -- Frontmatter contains ONLY: `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools` — existing frontmatter compliant; only `version` field changes.
- [x] **Article II** -- agent `name` matches pattern `^ava-[a-z0-9-]+$` — `ava-stack-dotnet-backend` ✅
- [x] **Article III** -- Phase placement valid — F3, already in pipeline; no phase routing change.
- [x] **Article IV** -- Module-level `module.yaml` diff prepared (see Plan section 5)
- [x] **Article V** -- Agent body language is Brazilian Portuguese — guardrail prose in pt-BR ✅
- [x] **Article VI** -- BDD scenarios in spec section 4 — 5 scenarios covering nominal + edge + gate paths ✅
- [x] **Article VII** -- Security sub-pipeline impact assessed — G11 calls `dotnet --version` via Bash (read-only, no secrets, no network). G10 GLOBs `.csproj` files (read-only). No security sub-pipeline impact.
- [x] **Article VIII** -- trace_id propagation — N/A: this is an LLM prompt file (`.md`). Agents do not handle trace_id in their body.
- [x] **Article IX** -- Clean Architecture layer ordering — N/A: agent is an LLM prompt file. Guardrails operate on the *host* project structure, not on this agent's own source.
- [x] **Article X** -- Version bump: **MINOR** (1.0.0 → 1.1.0). New guardrail sections added; no contract change; existing G1–G9 unaffected; backward-compatible.
- [x] **Article XI** -- Skill/Agent split: user-facing via `.github/skills/ava-stack-dotnet-backend/SKILL.md` (already exists). No change to SKILL.md.

### Quality Gate Check

- [x] No [NEEDS CLARIFICATION] markers remain in spec
- [x] G10/G11 are pre-generation gates — they do NOT produce additional output files; existing output contract unchanged
- [x] Downstream `next_agent` unchanged — this agent still routes to `ava-stack-angular-frontend` or equivalent next step in the stack orchestrator

---

## 1. Technical Context

| Dimension | Choice | Source |
|-----------|--------|--------|
| Agent runtime | LLM prompt file (`.md`) | N/A — not compiled code |
| Backend TFM | Resolved at runtime from `project-config.yaml → tobe_stack.backend_version` | Article I |
| CLI tool | `dotnet --version` (Bash, G11) | Built-in .NET SDK |
| File scan | `Glob: src/**/*.csproj` or `outputs/tobe/source-code/**/*.csproj` (G10) | MSBuild convention |
| Namespace inference | `<RootNamespace>` element OR parent folder name (MSBuild default) | MSBuild convention |
| Version comparison | Major.minor numeric comparison (`installed >= required`) | G11 spec §7 |

**Project overrides**: `projects/{project_name}/context/project-config.yaml → tobe_stack.backend_version`

**No new dependencies introduced.** G10/G11 use only Bash + Glob tools already in `allowed-tools`.

---

## 2. Phase Placement

This change modifies an existing F3 agent. No orchestration routing changes.

```
F2 Orchestrator → ava-stack-orchestrator
F3 → ava-stack-dotnet-backend  [THIS AGENT — gates G11→G10 added pre-generation]
   → ava-stack-angular-frontend (or equivalent, per stack config)
F3 Orchestrator → ava-summary
```

**Quality gate at this phase**: Summary Validator (runs after every phase) — no change.

`human_gate_required`: unchanged. G10/G11 emit HARD STOP messages but do not set `human_gate_required` — they require the invoking user to resolve the environment issue (SDK version or namespace rename) before re-invoking.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO  -- agent is an LLM prompt file; Clean Architecture applies to generated code artifacts only
Application    -> NO
Infrastructure -> NO
Presentation   -> NO
```

> **Note**: This agent IS the generator of Clean Architecture code. Guardrails G10/G11 are pre-generation gates that inspect the *host project structure* (`.csproj` files, environment), not the agent's own internal code.

---

## 4. Agent File Structure

**Modify-existing**: no new files created.

```
src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-dotnet-backend.md    ← ONLY file modified
    Sections changed:
    ├── [frontmatter] version: "1.0.0" → "1.1.0"
    ├── [Docs Research Bundle section] "G1-G9" → "G1-G11 (G10-G11: pré-geração bloqueantes; G1-G9: durante geração)"
    ├── [GUARDRAILS header] add category note distinguishing pre-generation from generation-time guards
    ├── [G10 section] replace corrupted block with authoritative content (spec §6)
    └── [G11 section] replace duplicate+corrupted block with single authoritative G11 (spec §7)
```

**Dispatch mode**: user-facing (SKILL.md already exists — no change)

SKILL.md at `.github/skills/ava-stack-dotnet-backend/SKILL.md` — no change needed.

**Allowed-tools**: `Read, Write, Edit, Bash, Glob` — already present. G11 uses `Bash` (dotnet --version), G10 uses `Glob` (csproj scan). Both tools already declared ✅

---

## 5. module.yaml Impact

**N/A — `modify-existing` change type.** `ava-stack-dotnet-backend` is already registered in:

```
src/modules/ava-fabric-agents/tech-stack/module.yaml
```

No new agent entry. No top-level `module.yaml` change. No SKILL.md change.

---

## 6. Observability & Trace Propagation

**N/A** — LLM prompt file. This agent does not handle `trace_id` in its body. G10/G11 are textual instruction blocks, not executable code in this repo's context.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|--------|-----------------|-------------|
| agent-task.schema.json | NO | G10/G11 read from existing input fields only (`project_name` → project-config.yaml) |
| agent-result.schema.json | NO | G10/G11 produce HARD STOP messages; when blocking, no `AgentResult` is emitted at all |

---

## 8. Implementation Phases

**Phase 0** -- Frontmatter: write `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools`; verify agent name pattern; write `## Output Contract` block.

**Phase 1** -- Body: responsibility, numbered instructions, output format specs, security notes.

**Phase 2** -- Gate Logic: risk scoring, human_gate_required conditions, next_agent logic.

**Phase 3** -- BDD: confirm spec section 4, map to F5 QA, identify automation targets.

**Phase 4** -- Registration: module.yaml, agents-catalog.md, CHANGELOG.md, orchestrator deps.

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| [GATE_NAME] | [What failed] | [Why acceptable] | [How risk managed] |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Contract (input) | JSON Schema | 100% of AgentTask paths |
| Contract (output) | JSON Schema | 100% of AgentResult paths |
| Nominal BDD | xUnit | Spec section 4 Scenario 1 |
| Edge case BDD | xUnit | Spec section 4 Scenario 2 |
| Gate trigger | xUnit | Spec section 4 Scenario 3 |
| Regression | Existing suite | No existing agent broken |
