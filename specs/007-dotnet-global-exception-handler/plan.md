# Implementation Plan: Guardrail G10 — GlobalExceptionHandler Tipado

**Branch**: `007-dotnet-global-exception-handler` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-dotnet-global-exception-handler/spec.md`

---

## Summary

The `coder-dotnet-backend.md` agent already contains **G10** (GlobalExceptionHandler guardrail) and
the **ErrorOr<T> handler template** — added manually by the developer before this plan was created.

**Audit of current state reveals 3 remaining gaps:**

| Gap | SC | Status |
|---|---|---|
| Routing guard text reads "G1-G9 existentes" (stale) | SC-1 | NOT done |
| `ValidationException` class absent from exception hierarchy code block | SC-2 | NOT done |
| `ValidationException` absent from `GlobalExceptionHandler` switch expression | SC-3 | NOT done |
| ProblemDetails schema comment lists `type`, `title`, `detail`, `instance` | SC-4 | ALREADY PRESENT |
| ErrorOr<T> pattern documented + prohibition on throwing DomainException in handlers | SC-5 | ALREADY PRESENT |

**Technical approach**: 3 surgical text edits to `coder-dotnet-backend.md` + version bump `1.0.0 -> 1.0.1`.

---

## Technical Context

**Language/Version**: Markdown (agent definition file) — no runtime compilation
**Primary Dependencies**: `coder-dotnet-backend.md` is the sole target file
**Storage**: N/A
**Testing**: Manual grep/read_file verification after edit
**Target Platform**: LLM agent runtime context
**Project Type**: modify-existing (PATCH)
**Performance Goals**: N/A
**Constraints**: Edit MUST NOT break existing G1-G9 content; no YAML frontmatter fields removed
**Scale/Scope**: 3 text edits + 1 version bump in a single ~400-line markdown file

---

## Constitution Check

| Article | Requirement | Status |
|---|---|---|
| I — Configuration-Driven | Agent body reads `tobe_stack.backend_version`; no hardcoded versions introduced | PASS |
| II — Agent Contract Standard | Frontmatter valid; version bump `1.0.0 -> 1.0.1` (PATCH, additive guardrail) | PASS |
| III — Pipeline Execution Contract | modify-existing; no new pipeline dependencies | PASS |
| V — Language Convention | Guardrail body stays in Brazilian Portuguese | PASS |
| VI — Naming Convention | `name: ava-stack-dotnet-backend` unchanged | PASS |

**DECISION: PROCEED**

---

## Project Structure

### Documentation (this feature)

```text
specs/007-dotnet-global-exception-handler/
+-- plan.md              <- This file
+-- research.md          <- Phase 0 output
+-- data-model.md        <- Phase 1 output: exact change model
+-- quickstart.md        <- Phase 1 output: validation guide
+-- checklists/
|   +-- requirements.md  <- Already exists
+-- tasks.md             <- Phase 2 output (/speckit.tasks)
```

### Source Code

```text
src/modules/ava-fabric-agents/tech-stack/agents/
+-- coder-dotnet-backend.md   <- Only file modified; 3 edits + 1 version bump
```

---

## Phase 0 Research -> research.md

See [research.md](research.md).

All NEEDS CLARIFICATION resolved. G10 already exists; remaining work is 3 targeted edits
with zero external research dependencies.

---

## Phase 1 Design -> data-model.md + quickstart.md

See [data-model.md](data-model.md) for the exact diff specification (change model).
See [quickstart.md](quickstart.md) for end-to-end validation scenarios.

Contracts: N/A — no public API or external interface. The contract this guardrail
enforces is documented within the guardrail body (already present in the file).

### Agent Context Update

After plan creation, update the SPECKIT section in `.github/copilot-instructions.md`:
- Old reference: `specs/003-agent-self-observability/plan.md`
- New reference: `specs/007-dotnet-global-exception-handler/plan.md`

---

## Implementation Tasks (preview — full list in tasks.md)

| # | Task | Type | SC |
|---|---|---|---|
| T1 | Update YAML frontmatter: version `1.0.0 -> 1.0.1`, date `2026-07-07` | Edit | — |
| T2 | Update routing guard text from "G1-G9" to "G1-G10" | Edit | SC-1 |
| T3 | Add `ValidationException` class to exception hierarchy code block | Edit | SC-2 |
| T4 | Add `ValidationException` case to switch expression in `GlobalExceptionHandler` | Edit | SC-3 |
| T5 | Update agent context in `.github/copilot-instructions.md` | Edit | — |
