# Agent Development Tasks: Real Frontend-Backend API Contract Integration

**Plan**: `specs/021-frontend-backend-api-contract-integration/plan.md`
**Status**: Implementation complete; verification passed.

## Category 1 — Version & Contract Verification

- [x] **1.1** `coder-dotnet-backend.md` → `2.2.0`
- [x] **1.2** `coder-angular-frontend.md` → `1.3.0`
- [x] **1.3** `orchestrator-stack.md` → `1.8.0`

## Category 2 — Implementation

- [x] **2.1** `coder-dotnet-backend.md`: new Step 3.5 — design-first contract conformance vs. build-time export branching; `api_contract_path` in Output Contract/Handoff — DONE
- [x] **2.2** `coder-angular-frontend.md`: new Step 1.2c — contract resolution (design-first → backend-exported → MISSING) + `build_runner.api_client_generation` honored — DONE
- [x] **2.3** `coder-angular-frontend.md`: Step 7.7 (`{bc}.service.ts`) rewritten — full CRUD method set derived from contract operations, not just getAll/getById, with explicit MISSING fallback — DONE
- [x] **2.4** `coder-angular-frontend.md`: Step 7.8 (`{bc}.model.ts`) rewritten — fields derived from contract schema (OpenAPI→TS type mapping table), with explicit MISSING fallback (TODO template preserved only for that case) — DONE
- [x] **2.5** `coder-angular-frontend.md`: `api_contract_status` added to Handoff — DONE
- [x] **2.6** `orchestrator-stack.md` Step 4: rewritten from a bare label to the real procedure (who generates the contract, where it lives, design-first vs. export) — DONE
- [x] **2.7** `orchestrator-stack.md` Step 6: rewritten from a bare label to a real, deterministic consistency check (comparing `api_contract_status` across backend/frontend Handoffs) — DONE
- [x] **2.8** `orchestrator-stack.md` frontmatter description: stale "ConfigStack.yaml" reference corrected to "project-config.yaml" (same class of stale-reference bug as `specs/019`'s Angular fix) — DONE

## Category 3 — Schema Updates — SKIP

`api_contract_path` / `api_contract_status` follow the same inline Handoff-field convention as
`business_rules_implemented` (`specs/020`) — no separate JSON schema file.

## Category 4 — Module Registration

N/A — no new agents.

## Category 5 — Quality Gate Checklists

- [x] **5.1** `grep -n "openapi"` in `coder-dotnet-backend.md` → present, describing design-first/export branching (verified)
- [x] **5.2** `grep -n "api_client_generation"` in `coder-angular-frontend.md` → present (verified)
- [x] **5.3** `grep -n "api_contract_status"` in `coder-angular-frontend.md` → present, 5 occurrences (Handoff field + Step 1.2c + Step 7.7 + Step 7.8) (verified)
- [x] **5.4** Manual read of `orchestrator-stack.md` Steps 4 and 6 → both now multi-line real procedures, not bare labels (verified)

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — design-first path: backend conforms to `bcNN-*.yaml`, frontend derives from the same contract
- [x] **6.2** CA02 — backend-exported fallback path: backend exports `backend/openapi/{bc}.yaml` when no design-first contract exists, frontend reads that instead
- [x] **6.3** CA03 — no-contract path: `api_contract_status: MISSING` reported explicitly in both Handoff and `ImplementationNotes.md`, not silently defaulted

## Category 7 — Documentation

- [x] **7.1** This spec-kit documentation (spec.md, plan.md, tasks.md) — DONE

## Completion Checklist

- [x] Placeholder frontend model (`id`/`createdAt`/`updatedAt`/`TODO`) is no longer the only
  outcome — it is now the explicit, flagged fallback for the `MISSING` case only
- [x] `getAll()`/`getById()`-only guessed service replaced with a full per-operation method set
  when a contract is available
- [x] Previously-dead `build_runner.api_client_generation` config is now read and honored
- [x] No new script/tool introduced (LLM-driven contract-following, consistent with the rest of
  the pipeline) — explicitly logged as a deferred option in spec §8, not an oversight
- [x] `orchestrator-stack.md` Steps 4/6 no longer aspirational one-liners
