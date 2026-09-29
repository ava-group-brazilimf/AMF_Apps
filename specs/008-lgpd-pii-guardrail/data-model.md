# Data Model: LGPD PII Compliance Guardrail

**Feature**: `specs/008-lgpd-pii-guardrail`
**Created**: 2026-07-08

---

## Runtime Inputs (resolved inside `coder-dotnet-backend.md` during guardrail execution)

| Field | Type | Source | Notes |
|---|---|---|---|
| `pii_fields` | `List<string>` | `security-architecture.md` §7 or canonical fallback | Case-insensitive match against property/parameter names |
| `bc_source_path` | `string` | `outputs/tobe/source-code/{module}/` | Root path for Grep scans |
| `security_architecture_path` | `string` | `outputs/tobe/docs/security-architecture.md` | Read at start of guardrail |

## Canonical PII Field Fallback List

Used when `security-architecture.md` §7 is absent or unreadable:

| Canonical name | Common C# aliases |
|---|---|
| `cpf` | `CPF`, `Cpf`, `numeroCpf` |
| `email` | `Email`, `emailAddress` |
| `nome` | `Nome`, `nomeCompleto`, `firstName`, `lastName` |
| `endereco` | `Endereco`, `logradouro`, `address` |
| `telefone` | `Telefone`, `celular`, `phone` |
| `dataNascimento` | `DataNascimento`, `birthDate`, `dtNasc` |

---

## Per-Field Check Result

```
PiiFieldCheck {
  field_name:           string    # e.g. "cpf"
  lgpd_01_log_masking:  string    # "PASS" | "FAIL" | "N/A"
  lgpd_02_audit_log:    string    # "PASS" | "FAIL" | "N/A"
  lgpd_03_rbac:         string    # "PASS" | "FAIL" | "N/A"
  lgpd_04_dto_exposure: string    # "PASS" | "WARN" | "N/A"
  findings:             List<string>   # file:line references per failure
  status:               string    # "COMPLIANT" | "NON_COMPLIANT" | "WARNING"
}
```

## LGPD Gate Verdict (derived)

| Condition | `lgpd_gate` value | Effect on `AgentResult` |
|---|---|---|
| Any LGPD-01, LGPD-02, or LGPD-03 = FAIL | `BLOCKED` | `security_gate = "BLOCKED"`, `human_gate_required = true` |
| Any LGPD-04 = WARN, no -01/-02/-03 FAIL | `APPROVED_WITH_RISKS` | Proceeds; warning in report |
| `pii_fields` is empty | `N/A` | Guardrail skipped; no block |
| All checks PASS | `APPROVED` | Proceeds normally |

---

## Report Section Schema (`## LGPD PII Compliance`)

Appended to `projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Backend.md`:

```
Header row: Campo PII | LGPD-01 | LGPD-02 | LGPD-03 | LGPD-04 | Status
Data rows:  one per pii_field (✅ PASS | ❌ FAIL — file:line | ➖ N/A | ⚠️ WARN)
Footer:     lgpd_gate: APPROVED | APPROVED_WITH_RISKS | BLOCKED | N/A
Details:    ## Findings Detalhados section (only when any ❌ present)
```

## Impact on Existing Report Structure

| Section | Change |
|---|---|
| `## Summary` | `❌ Não Conforme` count updated if LGPD checks fail |
| `## Detailed Assessment` | Unchanged |
| `## Non-Compliant Items` | LGPD findings appended when `lgpd_gate = BLOCKED` |
| `## LGPD PII Compliance` | **NEW** — appended at end of file |

## Impact on Handoff Report

| Field | Change |
|---|---|
| `security_gate` | Set to `BLOCKED` if `lgpd_gate = BLOCKED` |
| `human_gate_required` | Set to `true` if `lgpd_gate = BLOCKED` |
| `lgpd_gate` | **NEW** field added to Handoff Report output |
