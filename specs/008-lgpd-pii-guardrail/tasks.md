# Agent Development Tasks: coder-dotnet-backend — LGPD PII Guardrail

**Plan**: `specs/008-lgpd-pii-guardrail/plan.md`
**Agent ID**: `ava-stack-dotnet-backend` (frontmatter) | **Phase**: `F3` | **Module**: `tech-stack`
**Change Type**: `modify-existing` | **Version Bump**: MINOR `1.0.0 → 1.1.0`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 3 (schema) and Category 4 (module registration) are **N/A** for this modify-existing change.
> Categories 5, 6, and 7 can run in parallel after Category 2 completes.

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before Category 2. Locate the target file and apply the MINOR version bump.

- [X] **1.1** Locate target file `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` and confirm current `version: "1.0.0"` in frontmatter
- [X] **1.2** Update `version` field: `"1.0.0"` → `"1.1.0"` in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
- [X] **1.3** Update `description` field: append LGPD activation phrases (`"guardrail LGPD backend"`, `"verificar compliance LGPD endpoints"`, `"PII masking backend"`) to the existing `Ativa com:` list in the same file
- [X] **1.4** Verify `allowed-tools` already includes `Glob` and `Grep` (required for the new guardrail Grep steps); add if missing

> **1.5 — N/A**: SKILL.md already exists at `.github/skills/ava-coder-dotnet/SKILL.md`; no new skill file required.
> **Output Contract** — N/A: existing `mandatory_docs` entry already declares `SecurityComplianceReport-Backend.md`; no new output path added.

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. All insertion work targets `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`.
The anchor for insertion is the line `3. GERAR relatório:` inside `### Procedimento` of `## Security Compliance Review Gate (OBRIGATÓRIO)`.

- [X] **2.1** Insert the `### LGPD PII Compliance Guardrail (OBRIGATÓRIO)` subsection header immediately before the `3. GERAR relatório:` line, with its preamble paragraph (Brazilian Portuguese, Constitution Article V):
  ```
  ### LGPD PII Compliance Guardrail (OBRIGATÓRIO — executa após Step 2, antes da geração do relatório)
  
  Este guardrail verifica que o código gerado aplica os controles obrigatórios da LGPD
  para cada campo PII identificado no BC atual.
  ```

- [X] **2.2** Insert **Passo 2a.1** (PII field resolution) block after the subsection header in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`:
  - Read `security-architecture.md` §7; extract PII field list for the current BC
  - If §7 absent or file missing: fall back to canonical list `["cpf", "email", "nome", "endereco", "telefone", "dataNascimento"]`
  - Add fallback warning line to report: `"security-architecture.md §7 ausente — usando lista de fallback"`
  - Assign result to `pii_fields`

- [X] **2.3** Insert **Passo 2a.2** (LGPD-01: ILogger masking check) block in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`:
  - Grep `outputs/tobe/source-code/{module}/**/*.cs` for `ILogger.*Log.*` calls containing each `{campo}` without `PiiMask.Mask`, `_anonymizer.Anonymize`, `"[MASKED]"`, or `DestructureBy`
  - On match: `lgpd_01[campo] = "FAIL"` + finding `"arquivo:linha — ILogger expõe '{campo}' sem masking"`
  - No match: `lgpd_01[campo] = "PASS"`

- [X] **2.4** Insert **Passo 2a.3** (LGPD-02: audit log coverage) block in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`:
  - Grep `outputs/tobe/source-code/{module}/**/Infrastructure/**/*.cs` for `override.*SaveChangesAsync|IAuditLog|IAuditService`
  - Per entity with PII fields: missing pattern → `lgpd_02[entidade] = "FAIL"` + finding; found → `"PASS"`

- [X] **2.5** Insert **Passo 2a.4** (LGPD-03: RBAC on sensitive endpoints) block in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`:
  - Grep `outputs/tobe/source-code/{module}/**/API/**/*.cs` for `anonymize|delete-data|AnonymizeController|DeleteDataController`
  - Per endpoint found: missing `[Authorize(Policy = "DataOwnerOrDPO")]` → `lgpd_03[endpoint] = "FAIL"` + finding; has attribute → `"PASS"`
  - No `/anonymize` or `/delete-data` endpoint found → `lgpd_03 = "N/A"` (not generated — no violation)

- [X] **2.6** Insert **Passo 2a.5** (LGPD-04: DTO exposure warning) block in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`:
  - Grep `outputs/tobe/source-code/{module}/**/*.cs` for `HttpClient.*Post|HttpClient.*Put|_http.*Post|_http.*Put` containing a `pii_fields` value without masking
  - Found → `lgpd_04 = "WARN"` (non-blocking); not found → `lgpd_04 = "PASS"`

- [X] **2.7** Insert **Passo 2a.6** (lgpd_gate verdict) block in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`:
  - `BLOCKED` if any `lgpd_01|lgpd_02|lgpd_03 = "FAIL"` → set `AgentResult.security_gate = "BLOCKED"` and `human_gate_required = true`
  - `APPROVED_WITH_RISKS` if `lgpd_04 = "WARN"` (no -01/-02/-03 failures)
  - `N/A` if `pii_fields` is empty → also write note to report: "Nenhum campo PII detectado — verificação ignorada"
  - `APPROVED` otherwise

- [X] **2.8** Update the existing `3. GERAR relatório:` step in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` to append the `## LGPD PII Compliance` section when `pii_fields` is non-empty, using the table format (one row per PII field: campo | LGPD-01 | LGPD-02 | LGPD-03 | LGPD-04 | Status) plus the `**lgpd_gate**: ...` footer line

- [X] **2.9** Update the `## LGPD PII Compliance` report section to include: if `lgpd_gate = "BLOCKED"` → also update `Overall Status` in the `## Summary` table to `NON_COMPLIANT` and append findings to `## Non-Compliant Items`

- [X] **2.10** Update `## Handoff Report` section in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` to include `lgpd_gate: {APPROVED | APPROVED_WITH_RISKS | BLOCKED | N/A}` in the reported fields list

---

## Category 3 — Shared Schema Updates

**N/A** — Plan section 7 confirms no schema changes required. `security_gate` and `human_gate_required` already exist in `agent-result.schema.json`. `lgpd_gate` is a sub-field within the report, not a top-level AgentResult field.

---

## Category 4 — Module Registration

**N/A** — `ava-coder-dotnet-backend` is already registered in `src/modules/ava-fabric-agents/tech-stack/module.yaml`. No new entry required.

---

## Category 5 — Quality Gate Checklists

Can run in parallel with Categories 6 and 7.

- [X] **5.1** Add LGPD guardrail checklist items to `specs/008-lgpd-pii-guardrail/checklists/requirements.md`:
  - `- [ ] Passo 2a.1 present: PII field resolution from §7 with fallback`
  - `- [ ] Passo 2a.2 present: LGPD-01 ILogger masking check`
  - `- [ ] Passo 2a.3 present: LGPD-02 audit log coverage check`
  - `- [ ] Passo 2a.4 present: LGPD-03 RBAC endpoint check`
  - `- [ ] Passo 2a.5 present: LGPD-04 DTO exposure warning`
  - `- [ ] Passo 2a.6 present: lgpd_gate verdict derivation logic`
  - `- [ ] report section format correct (table header + rows + lgpd_gate footer)`
  - `- [ ] Handoff Report includes lgpd_gate field`
- [X] **5.2** Verify all checklist items use `- [ ]` format and are actionable

---

## Category 6 — Acceptance Validation & QA Integration

Can run in parallel with Categories 5 and 7. Depends on Category 2.

- [X] **6.1** Validate **Scenario 1 (Nominal — P1)** against spec section 4:
  - Entity with `cpf`, `email`, `telefone`; all ILogger calls use `PiiMask.Mask(...)`; `SaveChangesAsync` override present; no `/anonymize` endpoint
  - Expected: `lgpd_gate = "APPROVED"`, `## LGPD PII Compliance` table shows all ✅ rows
- [X] **6.2** Validate **Scenario 2 (Edge: no PII — P2)** against spec section 4:
  - Entity with no PII field names; `security-architecture.md §7` absent
  - Expected: `lgpd_gate = "N/A"`, report section notes "Nenhum campo PII detectado — verificação ignorada", `AgentResult.success = true`
- [X] **6.3** Validate **Scenario 3 (Gate: LGPD-01 FAIL — P1)** against spec section 4:
  - Entity with `email`; `ILogger.LogInformation("email: {email}", customer.Email)` without masking
  - Expected: `lgpd_gate = "BLOCKED"`, `security_gate = "BLOCKED"`, `human_gate_required = true`, report row `email → LGPD-01: ❌ FAIL — CustomerService.cs:42`
- [X] **6.4** Validate **Scenario 4 (Edge: missing security-architecture.md — P2)** against spec section 4:
  - `security-architecture.md` absent; entity has `cpf` field
  - Expected: fallback list used, warning added to report, `AgentResult.success = true`
- [X] **6.5** [P] Confirm the new `## LGPD PII Compliance` section in `SecurityComplianceReport-Backend.md` does not break `orchestrator-stack.md` step 6b.3 (reads `Overall Status` — must still resolve correctly)
- [X] **6.6** [P] Confirm the new `lgpd_gate` field in Handoff Report does not conflict with existing `security_gate` field in `agent-result.schema.json`
- [X] **6.7** [P] Validate **Scenario 5 (LGPD-04: APPROVED_WITH_RISKS — P2)**:
  - Entity with `email`; `HttpClient.PostAsync` sends plain `customer.Email` to an external service without masking
  - Expected: `lgpd_gate = "APPROVED_WITH_RISKS"`, report row `email → LGPD-04: ⚠️ WARN`, generation is **not** blocked, `AgentResult.success = true`

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Categories 5 and 6.

- [X] **7.1** [P] Add `CHANGELOG.md` entry for `[1.1.0] — coder-dotnet-backend — 2026-07-08`:
  ```markdown
  ## [1.1.0] — coder-dotnet-backend — 2026-07-08
  ### Added
  - LGPD PII Compliance Guardrail (LGPD-01..04) inside Security Compliance Review Gate
  - Per-field masking check on ILogger calls (LGPD-01)
  - Audit log coverage check for entities with PII fields (LGPD-02)
  - RBAC check on /anonymize and /delete-data endpoints (LGPD-03)
  - DTO exposure warning for external service calls (LGPD-04)
  - `## LGPD PII Compliance` section in SecurityComplianceReport-Backend.md
  - `lgpd_gate` verdict field in Handoff Report
  ```
- [X] **7.2** [P] Update `docs/agents-catalog.md`: bump version to `1.1.0` for the `ava-coder-dotnet-backend` / `ava-stack-dotnet-backend` entry; add note "Includes LGPD PII Compliance Guardrail (LGPD-01..04)"

---

## Completion Checklist

- [X] Categories 1 and 2 complete (all 10 tasks: 1.1–1.4 and 2.1–2.10)
- [X] Categories 3 and 4 confirmed N/A
- [X] Category 5 complete (checklist items added)
- [X] Category 6 complete (all 5 scenarios validated: 6.1–6.7)
- [X] Category 7 complete (CHANGELOG + catalog updated)
- [X] `coder-dotnet-backend.md` frontmatter `version` is `"1.1.0"` ✓
- [X] `## Security Compliance Review Gate` section contains `### LGPD PII Compliance Guardrail` subsection with all 6 steps (2a.1–2a.6) ✓
- [X] `SecurityComplianceReport-Backend.md` generation step appends `## LGPD PII Compliance` section ✓
- [X] Handoff Report section includes `lgpd_gate` field ✓
- [X] CHANGELOG.md entry committed ✓

---

## Dependencies

```
Category 1 → Category 2 (frontmatter must be set before behavior)
Category 2 → Category 6 (validation requires the guardrail to exist)
Categories 5, 6, 7 → can run in parallel after Category 2 completes
```

## Parallel Execution Opportunities

After Category 2 completes:
- **Thread A**: Category 5 (checklist) + Category 7 (CHANGELOG, catalog)
- **Thread B**: Category 6 (scenario validation 6.1–6.4, then 6.5–6.6)

## Implementation Strategy (MVP First)

**MVP** (minimum to unblock PBI validation):
1. Categories 1 and 2 in full (the actual guardrail implementation)
2. Task 7.1 (CHANGELOG)

**Complete** (all acceptance criteria met):
3. Categories 5, 6, 7 in full
