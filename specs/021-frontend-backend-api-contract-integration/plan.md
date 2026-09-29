# Agent Implementation Plan: Real Frontend-Backend API Contract Integration

**Spec**: `specs/021-frontend-backend-api-contract-integration/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (3 files, no new agents) |
| **Primary Requirement** | The frontend coder generates placeholder models (`id`/`createdAt`/`updatedAt`/`TODO`) and a guessed 2-method CRUD service, with zero read of any backend contract. The backend coder has no instruction to export a consumable contract. The orchestrator's own Steps 4/6 (contract generation/validation) are one-line descriptions with no procedure. |
| **Technical Approach** | Backend generates from (design-first) or exports (fallback) an OpenAPI contract at a predictable path; frontend consumes it for model/service generation, honoring the pre-existing but previously-dead `build_runner.api_client_generation` config; orchestrator Steps 4/6 describe the real procedure instead of a bare label. |
| **Implementation Status** | Complete. |

## Constitution Check
- [x] Article I — no hardcoded tech versions.
- [x] Article II — frontmatter unchanged except version/date.
- [x] Article VI — 3 BDD scenarios (design-first, backend-exported, no-contract).
- [x] Article X — MINOR on all 3 files.

## Technical Context
Pure prompt edits. No new scripts. The pre-existing `openapi-spec-tobe.md` (Fase 4.61) is
consumed as-is; not modified.

## Implementation Phases

### Phase 1 — Backend contract generation/export ✅ CONCLUÍDO
Added the design-first-vs-export branching instruction to `coder-dotnet-backend.md`.

### Phase 2 — Frontend contract consumption ✅ CONCLUÍDO
Rewrote the model/service generation guidance in `coder-angular-frontend.md` to derive from the
contract, honoring `build_runner.api_client_generation`; added explicit
`api_contract_status: MISSING` degradation for the no-contract case.

### Phase 3 — Orchestrator Steps 4/6 ✅ CONCLUÍDO
Expanded both steps in `orchestrator-stack.md`'s Sequência de Execução.

### Phase 4 — Verification ✅ CONCLUÍDO
Structural greps — see Test Strategy.

## Complexity Tracking

| Item | Status |
|---|---|
| Whether to introduce an actual NSwag/openapi-typescript CLI invocation | Deferred (spec §8) — kept consistent with this pipeline's existing LLM-driven (not tool-driven) codegen model; a future spec can add the CLI step if stricter guarantees are needed |
| Scope limited to dotnet+angular, not all 5 stack pairs | Matches `specs/019`/`020`'s precedent — Meu-ERP is the only project actually exercising this pipeline today |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| Backend contract instruction | `grep -n "openapi"` in `coder-dotnet-backend.md` | Present, describing design-first/export branching |
| Frontend honors config | `grep -n "api_client_generation"` in `coder-angular-frontend.md` | Present |
| Explicit degradation | `grep -n "api_contract_status"` in `coder-angular-frontend.md` | Present |
| Orchestrator Steps 4/6 expanded | Manual read of `orchestrator-stack.md` Sequência de Execução | Both steps have a procedure, not a bare label |
