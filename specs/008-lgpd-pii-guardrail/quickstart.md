# Quickstart Validation Guide: LGPD PII Guardrail

**Feature**: `specs/008-lgpd-pii-guardrail`
**Created**: 2026-07-08

---

## Prerequisites

- A project under `projects/{project_name}/` exists with generated backend source code in
  `outputs/tobe/source-code/{module}/`
- `projects/{project_name}/outputs/tobe/docs/security-architecture.md` exists with a
  Section 7 containing PII field mappings (or use a project without it to test fallback)

---

## Validation Scenario 1 — Guardrail Triggers on PII Entity

**Setup**: Project with a `Cliente` entity containing `cpf` and `email` fields in a C#
file under `outputs/tobe/source-code/`, where `ILogger.LogInformation("email: {email}", customer.Email)`
appears **without** masking.

**Steps**:
1. Invoke `coder-dotnet-backend.md` (or `ava-stack-orchestrator` targeting the project)
2. After code generation completes, observe the Security Compliance Review Gate output

**Expected outcome**:
- The guardrail Passo 2a.1 resolves `pii_fields` from `security-architecture.md §7` (or fallback)
- Passo 2a.2 detects unmasked `email` in `ILogger` → `lgpd_01[email] = "FAIL"`
- `lgpd_gate = "BLOCKED"`
- `AgentResult.security_gate = "BLOCKED"`, `human_gate_required = true`
- `SecurityComplianceReport-Backend.md` has `## LGPD PII Compliance` section with `email → ❌ FAIL`

---

## Validation Scenario 2 — No PII Fields

**Setup**: Project with a `Produto` entity (no `cpf`, `email`, `nome`, `endereco`, `telefone`,
`dataNascimento` fields). `security-architecture.md §7` is absent.

**Steps**:
1. Invoke `coder-dotnet-backend.md`
2. Observe the Security Compliance Review Gate output

**Expected outcome**:
- `pii_fields = []` (empty after fallback scan)
- Guardrail sets `lgpd_gate = "N/A"`
- `SecurityComplianceReport-Backend.md` `## LGPD PII Compliance` notes: "Nenhum campo PII detectado — verificação ignorada"
- Code generation completes normally; `AgentResult.success = true`

---

## Validation Scenario 3 — All Checks Pass

**Setup**: Project with `Cliente` entity containing `cpf` and `email`, where:
- All `ILogger` calls use `PiiMask.Mask(customer.Cpf)` / `PiiMask.Mask(customer.Email)`
- `ApplicationDbContext.SaveChangesAsync` override records audit entries
- No `/anonymize` or `/delete-data` endpoints generated (or they have `[Authorize(Policy="DataOwnerOrDPO")]`)

**Expected outcome**:
- All PII fields → `lgpd_01 = PASS`, `lgpd_02 = PASS`, `lgpd_03 = N/A` or `PASS`
- `lgpd_gate = "APPROVED"`
- `SecurityComplianceReport-Backend.md` shows all ✅ rows in `## LGPD PII Compliance`
- Handoff Report: `lgpd_gate: APPROVED`

---

## Key Files to Inspect After Validation

| File | What to verify |
|---|---|
| `outputs/tobe/docs/security/SecurityComplianceReport-Backend.md` | Contains `## LGPD PII Compliance` section with correct rows |
| Agent Handoff Report | Contains `lgpd_gate: APPROVED\|BLOCKED\|APPROVED_WITH_RISKS\|N/A` |
| `coder-dotnet-backend.md` frontmatter | `version: "1.1.0"` and updated `description` with LGPD phrases |
| `CHANGELOG.md` | Entry for `[1.1.0] — coder-dotnet-backend — 2026-07-08` |
