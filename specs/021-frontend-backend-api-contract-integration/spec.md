# Agent Specification: Real Frontend-Backend API Contract Integration

**Feature Branch**: `021-frontend-backend-api-contract-integration`
**Created**: 2026-07-15
**Status**: Implemented
**Change Type**: modify-existing (3 files across `tech-stack` module — MINOR each)
**Input**: "Deve haver integração entre frontend e backend. O frontend deve consumir as APIs
geradas no backend, deve ser entregue um código compilando e funcional para usuário final."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-stack-dotnet-backend` | `tech-stack/agents/coder-dotnet-backend.md` | `2.1.0` → `2.2.0` (MINOR) |
| `ava-stack-angular-frontend` | `tech-stack/agents/coder-angular-frontend.md` | `1.2.0` → `1.3.0` (MINOR) |
| `ava-stack-orchestrator` | `tech-stack/agents/orchestrator-stack.md` | `1.7.1` → `1.8.0` (MINOR — Steps 4/6 gain real procedures, no field removed) |

**Phase**: F4. **Depends on**: `specs/019` (same Execution Steps sections).

---

## 2. Problem Statement

Direct read of `coder-angular-frontend.md`'s Step 7.7-7.8 (per-BC service and model generation)
confirms the frontend does **not** consume any contract from the backend:

```typescript
// models/{bc}.model.ts — generated as-is today:
export interface {BCPascal}Model {
  id:        string;
  createdAt: string;
  updatedAt: string;
  // TODO: adicionar campos específicos do domínio {BC_LABEL}
}
```
```typescript
// {bc}.service.ts — generated as-is today, only 2 methods, generic REST guess:
getAll(): Observable<{BCPascal}Item[]> { return this.http.get<...>(this.baseUrl); }
getById(id: string): Observable<{BCPascal}Item> { return this.http.get<...>(`${this.baseUrl}/${id}`); }
```

`coder-dotnet-backend.md`'s only mention of OpenAPI is a bare Skills bullet ("API Layer
Generator: ... OpenAPI annotations") — no instruction to export a consumable contract file.
`orchestrator-stack.md`'s Step 4 ("Gerar contratos de API (OpenAPI spec)") and Step 6 ("Validar
consistência entre contratos backend ↔ frontend") are each a single line in the numbered
execution sequence, with no procedure, no artifact path, and no verification mechanism behind
them.

Separately, `project-config.yaml` already declares `build_runner.api_client_generation:
"openapi-nswag"` — an explicit, pre-existing intent to generate the TypeScript client from
NSwag/OpenAPI — but zero agent files in the repository reference "nswag" (confirmed by grep).
The configured mechanism was never implemented.

There is, however, already a **design-first** OpenAPI contract generated before codegen: Fase
4.61 of `orchestrator-tobe.md` produces `outputs/tobe/docs/openapi/bcNN-*.yaml` per bounded
context, gated by `overrides.tobe_api.contract_first: true` (already set in the real
Meu-ERP-001 `project-config.yaml`). Neither backend nor frontend coder reads it today.

---

## 3. Decision

### 3.1 `coder-dotnet-backend.md`
New instruction, inserted before the API layer generation step: SE
`outputs/tobe/docs/openapi/bcNN-*.yaml` exists for the BC being generated → generate
Controllers/Minimal APIs **conforming** to that contract (routes, verbs, request/response
schemas) rather than freely. SE it does not exist → export a build-time OpenAPI document
(`Microsoft.AspNetCore.OpenApi`/Swashbuckle, already implied by G8's Swagger guardrail) to
`outputs/tobe/source-code/backend/openapi/{bc}.yaml`. Either way, a machine-readable contract
must exist at a predictable path by the end of backend codegen, and its path is reported in the
Handoff.

### 3.2 `coder-angular-frontend.md`
New **blocking** pre-generation input at Step 1 (pre-flight): the resolved contract from §3.1.
When `project-config.yaml`'s `build_runner.api_client_generation == "openapi-nswag"` (or
equivalent), Steps 7.7/7.8 (service/model generation) are rewritten to derive fields and methods
**from the contract's schemas and paths** — replacing the hardcoded `id`/`createdAt`/`updatedAt`/
`TODO` placeholder model and the `getAll()`/`getById()`-only guessed service with the BC's real
DTO shape and the full set of verbs/paths it actually exposes. SE no contract is available at
all (neither design-first nor backend-exported) → degrade with an explicit
`api_contract_status: MISSING` in the Handoff instead of silently generating placeholders as
today.

### 3.3 `orchestrator-stack.md`
Step 4 and Step 6 of the "Sequência de Execução" are expanded from one-line descriptions into
real, verifiable procedures describing exactly what §3.1/§3.2 do and where the contract lives,
plus a lightweight consistency check comparing the frontend service's called paths/verbs against
the contract's declared paths/verbs at Step 6.

---

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `coder-dotnet-backend.md` | Generates from / exports OpenAPI contract at a predictable path |
| `coder-angular-frontend.md` | Consumes the contract for model/service generation; degrades explicitly, not silently, when absent |
| `orchestrator-stack.md` | Steps 4 and 6 become real procedures with an artifact path and a verification step |

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Contract-driven generation, design-first path (CA01)
**Given** `outputs/tobe/docs/openapi/bc02-contas-pagar.yaml` defines `GET /contas-pagar`,
`POST /contas-pagar`, `PUT /contas-pagar/{id}`, `DELETE /contas-pagar/{id}` and schema
`ContaPagarDto { id, fornecedor, valor, dataVencimento, status }`, **When** backend and frontend
are generated, **Then** the backend exposes exactly those 4 endpoints with that schema, and
`contas-pagar.service.ts` implements the 4 corresponding methods against a `ContaPagarModel`
with the 5 real fields — no `TODO`, no invented field.

### Scenario 2 — Contract-driven generation, backend-exported fallback path (CA02)
**Given** no design-first contract exists for a BC, **When** the backend generates that BC,
**Then** it exports `outputs/tobe/source-code/backend/openapi/{bc}.yaml` from its own
Controllers, and the frontend coder reads that exported file instead.

### Scenario 3 — No contract available anywhere: explicit degradation, not silent placeholders (CA03)
**Given** neither a design-first nor a backend-exported contract exists when the frontend coder
runs, **When** Step 1 of `coder-angular-frontend.md` checks for a contract, **Then** it reports
`api_contract_status: MISSING` in the Handoff and proceeds with a clearly-flagged
`ImplementationNotes.md` warning — not a silently-generated generic CRUD guess indistinguishable
from a real integration.

---

## 6. Quality Gate Requirements
- [x] Agent IDs unchanged (Article II)
- [x] MINOR bump on all 3 files (Article X)
- [x] BDD scenarios cover design-first, backend-exported, and no-contract paths (Article VI)
- [x] `build_runner.api_client_generation` config now honored, closing a previously dead config field

## 7. Dependencies
- `specs/019` — same Execution Steps sections in both coder agents.
- `orchestrator-tobe.md` Fase 4.61 (`openapi-spec-tobe.md`) — pre-existing design-first contract
  generator, consumed as-is, not modified by this spec.
- `project-config.yaml`'s pre-existing `build_runner.api_client_generation` and
  `overrides.tobe_api.contract_first` fields — read, not introduced, by this spec.

## 8. Exclusions
- No new script/tool for automated NSwag/openapi-typescript code generation is introduced in
  this spec — the coder agent follows the contract manually (LLM-driven generation matching the
  schema), consistent with how every other part of this pipeline works (prompt-driven codegen,
  not tool-driven). A future spec could introduce an actual `nswag` CLI invocation via `Bash` if
  stricter guarantees are needed.
- Java/Go/Python backend coders and non-Angular frontend stubs are out of scope — this spec
  targets the two coders actually used by Meu-ERP (dotnet + angular), matching `specs/019`/`020`'s
  established precedent of prioritizing the in-use stack pair.

## 9. Assumptions
- The design-first contract (Fase 4.61) is authoritative when it exists — the backend coder does
  not "improve on" or diverge from it; divergence is a bug, not a design choice.

## Success Criteria

| Criterion | Measure |
|---|---|
| Backend contract instruction present | `grep -n "openapi/bcNN"` or `grep -n "openapi/{bc}.yaml"` in `coder-dotnet-backend.md` → present |
| Frontend consumes contract | `grep -n "api_client_generation"` in `coder-angular-frontend.md` → present |
| Placeholder model removed for contract-driven case | Trace of Step 7.8 shows contract-derived fields replacing the `id/createdAt/updatedAt/TODO` template when a contract exists |
| Explicit degradation on missing contract | `grep -n "api_contract_status"` in `coder-angular-frontend.md` → present |
| Orchestrator Steps 4/6 are real procedures | `grep -c "^4\."` / manual read confirms more than 1 line of content per step |
