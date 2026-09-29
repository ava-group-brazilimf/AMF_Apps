# Agent Implementation Plan: coder-dotnet-backend — LGPD PII Guardrail

**Spec**: `specs/008-lgpd-pii-guardrail/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-coder-dotnet-backend` (module.yaml) / `ava-stack-dotnet-backend` (frontmatter) |
| **Target File** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |
| **Phase** | `F3` (Tech Stack / Code Generation) |
| **Module** | `tech-stack` |
| **Primary Requirement** | Add an LGPD PII Guardrail subsection inside the existing Security Compliance Review Gate that enforces masking in ILogger calls, audit-log coverage, and RBAC on sensitive endpoints when generated entities contain PII fields |
| **Technical Approach** | Insert a new `### LGPD PII Compliance Guardrail (OBRIGATÓRIO)` subsection after the existing Step 2 classification block; it reads §7 PII field list, inspects generated code for LGPD-01..04 checks, and appends `## LGPD PII Compliance` section to `SecurityComplianceReport-Backend.md` |
| **Change Type** | `modify-existing` |
| **Version Bump** | MINOR: `1.0.0` → `1.1.0` |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9).*

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded; guardrail reads `security-architecture.md` §7 at runtime; C# masking patterns referenced by API name only
- [x] **Article II** — Frontmatter update: only `name`, `version`, `description`, `allowed-tools` modified
- [x] **Article II** — Agent name `ava-stack-dotnet-backend` matches `^ava-[a-z0-9-]+$` ✅
- [x] **Article III** — Phase F3, no pipeline sequence change; guardrail is an internal step within the existing Security Compliance Review Gate
- [x] **Article IV** — `module.yaml` already has `ava-coder-dotnet-backend` registered; no new entry needed (modify-existing) ✅ N/A
- [x] **Article V** — New guardrail instructions written in Brazilian Portuguese
- [x] **Article VI** — BDD scenarios in spec section 4: nominal (S1), edge no-PII (S2), gate blocked (S3), edge missing artifact (S4)
- [x] **Article VII** — Security impact: guardrail strengthens LGPD compliance; does not bypass `ava-asis-security-orchestrator`
- [x] **Article VIII** — `trace_id` not directly handled (LLM prompt file); N/A per plan template note
- [x] **Article IX** — N/A — this is an LLM prompt file, not generated code
- [x] **Article X** — MINOR bump: `1.0.0` → `1.1.0`; `CHANGELOG.md` entry required
- [x] **Article XI** — SKILL.md already exists at `.github/skills/ava-coder-dotnet/SKILL.md`; only agent `.md` body modified ✅

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec
- [x] Output path `projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Backend.md` consistent with existing agent contract ✅
- [x] Downstream next_agent (`ava-stack-orchestrator`) already exists ✅

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime | .NET 8, C# 12 | reference-architecture.yaml -> tech_stack.backend |
| Frontend | Angular 17, TypeScript 5.3 | reference-architecture.yaml -> tech_stack.frontend |
| ORM | EF Core 8 / Dapper | reference-architecture.yaml -> tech_stack.backend.orm |
| Cloud | Azure Container Apps | reference-architecture.yaml -> tech_stack.infrastructure |
| Observability | OpenTelemetry -> Azure Monitor | reference-architecture.yaml -> tech_stack.observability |
| Security | Azure AD B2C, SonarQube | reference-architecture.yaml -> tech_stack.security |
| Testing | xUnit 2.7, Playwright, k6 | reference-architecture.yaml -> tech_stack.backend.testing |
| IaC | Bicep / Terraform | reference-architecture.yaml -> tech_stack.infrastructure.iac |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

Master pipeline sequence (F4 is a sub-phase of F2, not a standalone step):
```
F1 → ava-summary → F2 → ava-summary → F3 → ava-summary
                                    → F5 → ava-summary
                                    → F7 → ava-summary
                                    → F6 → ava-summary (FINAL)
```

This agent's position (unchanged by this PBI):
```
F3: ava-stack-orchestrator dispatches → ava-coder-dotnet-backend (this agent)
  → Security Compliance Review Gate (existing)
    → [NEW] LGPD PII Compliance Guardrail (steps 2a.1..2a.6)
  → Handoff Report → ava-stack-orchestrator
```

**Quality gate at this phase**: Security Compliance Gate (F3 internal); Summary Validator (after F3 phase)

Conditions for `human_gate_required: true`:
- `lgpd_gate == "BLOCKED"` (any LGPD-01, LGPD-02, or LGPD-03 failure)

---

## 3. Clean Architecture Alignment

```
Domain         -> N/A
Application    -> N/A
Infrastructure -> N/A
Presentation   -> N/A
```

> ℹ️ This agent is an LLM prompt file. Clean Architecture applies to the *code it generates*, not the `.md` instruction file itself.

Cross-layer coupling: N/A

---

## 4. Agent File Structure

Skill/Agent two-layer split (Constitution Article XI) — **no changes to file structure**:

```
.github/skills/ava-coder-dotnet/
└── SKILL.md                         ← unchanged (routes to tobe-architecture/agents/coder-dotnet.md;
                                         naming inconsistency tracked separately, out of scope)

src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-dotnet-backend.md          ← MODIFIED: version bump + LGPD guardrail subsection
```

**Agent frontmatter** (updated fields):
```yaml
---
name: "ava-stack-dotnet-backend"
version: "1.1.0"
description: |
  Gera código C# production-ready seguindo Clean Architecture, CQRS
  com MediatR, EF Core, FluentValidation e boas práticas. Stack e versão
  lidos de `tobe_stack.backend_version` em project-config.yaml.
  Inclui guardrail de compliance LGPD que verifica masking de campos PII
  em ILogger, audit log em operações de escrita e RBAC nos endpoints
  /anonymize e /delete-data.
  Ativa com: "gerar código .NET", "criar endpoint", "implement C# class",
  "CQRS command", "EF Core migration", "guardrail LGPD backend",
  "verificar compliance LGPD endpoints", "PII masking backend".
allowed-tools: Read, Write, Edit, Bash, Glob
---
```

**Dispatch mode**: internal-only — dispatched by `ava-stack-orchestrator` based on `tobe_stack.backend_framework == "dotnet"`

**Shared resources**: agent-task.schema.json | agent-result.schema.json | reference-architecture.yaml | mermaid-guardrails.md

---

## 5. module.yaml Impact

**No changes required.** The `ava-coder-dotnet-backend` entry already exists in
`src/modules/ava-fabric-agents/tech-stack/module.yaml`:

```yaml
  - id: ava-coder-dotnet-backend        # already registered ✅
    file: agents/coder-dotnet-backend.md
    routing_key: "dotnet"
```

The top-level `module.yaml` at the repo root does **not** require updating (no new phase/module created).

---

## 6. Observability & Trace Propagation

N/A — LLM prompt agent. `trace_id` flows transparently via `shared-context.md` and the
SKILL.md wrapper without explicit handling in the agent body.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| agent-task.schema.json | NO | No new input fields added |
| agent-result.schema.json | NO | `security_gate` and `human_gate_required` already exist; `lgpd_gate` is a sub-field in the report, not a top-level AgentResult field |

---

## 8. Implementation Steps

### Step 1 — Version Bump (frontmatter)

In `coder-dotnet-backend.md`, update:
- `version`: `"1.0.0"` → `"1.1.0"`
- `description`: add LGPD activation phrases (see section 4 frontmatter block above)

### Step 2 — Insert LGPD PII Compliance Guardrail subsection

Locate the anchor line `3. GERAR relatório:` inside `### Procedimento` of
`## Security Compliance Review Gate (OBRIGATÓRIO)`. Insert the complete
`### LGPD PII Compliance Guardrail (OBRIGATÓRIO)` block (steps 2a.1–2a.6)
**before** that step 3 line.

The guardrail block (Brazilian Portuguese, Constitution Article V):

```markdown
### LGPD PII Compliance Guardrail (OBRIGATÓRIO — executa após Step 2, antes da geração do relatório)

Este guardrail verifica que o código gerado aplica os controles obrigatórios da LGPD
para cada campo PII identificado no BC atual.

**Passo 2a.1 — Resolver lista de campos PII**

```
READ projects/{project_name}/outputs/tobe/docs/security-architecture.md
→ Localizar Seção 7 (LGPD Compliance Controls)
→ Extrair a tabela ou lista de campos PII mapeados ao BC atual

SE §7 não encontrada ou arquivo ausente:
  → USAR lista canônica de fallback:
    ["cpf", "email", "nome", "endereco", "telefone", "dataNascimento"]
  → Adicionar aviso no relatório:
    "security-architecture.md §7 ausente — usando lista de fallback"

pii_fields = [lista resolvida acima]
```

**Passo 2a.2 — Verificação LGPD-01: Masking em ILogger**

```
PARA CADA campo EM pii_fields:
  GREP outputs/tobe/source-code/{module}/**/*.cs
    padrão: ILogger.*Log.*\({campo}\) SEM (PiiMask\.Mask|_anonymizer\.Anonymize|"\[MASKED\]"|DestructureBy)

  SE padrão encontrado (ILogger expõe campo sem masking):
    → lgpd_01[campo] = "FAIL"
    → registrar finding: "arquivo:linha — ILogger expõe '{campo}' sem masking"
  SENÃO:
    → lgpd_01[campo] = "PASS"
```

**Passo 2a.3 — Verificação LGPD-02: Audit Log em operações de escrita**

```
PARA CADA entidade COM campos EM pii_fields:
  GREP outputs/tobe/source-code/{module}/**/Infrastructure/**/*.cs
    padrão: override.*SaveChangesAsync|IAuditLog|IAuditService

  SE padrão NÃO encontrado:
    → lgpd_02[entidade] = "FAIL"
    → registrar finding: "entidade '{entidade}' com PII sem interceptor de audit log"
  SENÃO:
    → lgpd_02[entidade] = "PASS"
```

**Passo 2a.4 — Verificação LGPD-03: RBAC em endpoints sensíveis**

```
GREP outputs/tobe/source-code/{module}/**/API/**/*.cs
  padrão: (anonymize|delete-data|AnonymizeController|DeleteDataController)

PARA CADA endpoint encontrado:
  SE endpoint NÃO tem [Authorize(Policy = "DataOwnerOrDPO")]:
    → lgpd_03[endpoint] = "FAIL"
    → registrar finding: "endpoint sem [Authorize(Policy=\"DataOwnerOrDPO\")]"
  SENÃO:
    → lgpd_03[endpoint] = "PASS"

SE nenhum endpoint /anonymize ou /delete-data encontrado:
  → lgpd_03 = "N/A" (não gerado — sem violação)
```

**Passo 2a.5 — Verificação LGPD-04: Campos PII em DTOs externos (aviso)**

```
GREP outputs/tobe/source-code/{module}/**/*.cs
  padrão: (HttpClient.*Post|HttpClient.*Put|_http.*Post|_http.*Put)
    contendo qualquer campo de pii_fields sem (PiiMask\.Mask|_anonymizer\.Anonymize|"\[MASKED\]")

SE padrão encontrado:
  → lgpd_04 = "WARN" (não bloqueia)
SENÃO:
  → lgpd_04 = "PASS"
```

**Passo 2a.6 — Determinar veredicto lgpd_gate**

```
SE qualquer lgpd_01[*] = "FAIL"
   OU qualquer lgpd_02[*] = "FAIL"
   OU qualquer lgpd_03[*] = "FAIL":
  → lgpd_gate = "BLOCKED"
  → AgentResult.security_gate = "BLOCKED"
  → AgentResult.human_gate_required = true

SENÃO SE lgpd_04 = "WARN":
  → lgpd_gate = "APPROVED_WITH_RISKS"

SENÃO SE pii_fields vazio:
  → lgpd_gate = "N/A"

SENÃO:
  → lgpd_gate = "APPROVED"
```
```

### Step 3 — Update report generation step

In the existing Step 3 instruction inside `### Procedimento`, append:

```
→ SE pii_fields não vazio:
    APPEND seção "## LGPD PII Compliance" ao relatório (formato: tabela por campo + lgpd_gate verdict)
→ SE lgpd_gate = "BLOCKED":
    Atualizar Overall Status para NON_COMPLIANT no ## Summary do relatório
```

**New `## LGPD PII Compliance` section format:**

```markdown
## LGPD PII Compliance

> Gerado por: LGPD PII Compliance Guardrail (ava-stack-dotnet-backend v1.1.0)
> Campos PII fonte: security-architecture.md §7 {ou "lista de fallback"}

| Campo PII | LGPD-01 (masking log) | LGPD-02 (audit log write) | LGPD-03 (RBAC endpoint) | LGPD-04 (DTO externo) | Status |
|---|---|---|---|---|---|
| cpf | ✅ PASS | ✅ PASS | ➟ N/A | ✅ PASS | ✅ COMPLIANT |
| email | ❌ FAIL — Service.cs:42 | ✅ PASS | ➟ N/A | ✅ PASS | ❌ NON_COMPLIANT |

**lgpd_gate**: APPROVED | APPROVED_WITH_RISKS | BLOCKED | N/A

### Findings Detalhados

- [LGPD-01] `CustomerService.cs:42` — ILogger expõe `email` sem masking.
  Correção: `PiiMask.Mask(customer.Email)`.
```

### Step 4 — Update Handoff Report section

In `## Handoff Report`, add:

```
- `lgpd_gate: {APPROVED | APPROVED_WITH_RISKS | BLOCKED | N/A}`
```

### Step 5 — CHANGELOG.md entry

```markdown
## [1.1.0] — coder-dotnet-backend — 2026-07-08
### Added
- LGPD PII Compliance Guardrail (LGPD-01..04) inside Security Compliance Review Gate
- Per-field masking check on ILogger calls (LGPD-01)
- Audit log coverage check for entities with PII fields (LGPD-02)
- RBAC check on /anonymize and /delete-data endpoints (LGPD-03)
- DTO exposure warning for external service calls (LGPD-04)
- `## LGPD PII Compliance` section in SecurityComplianceReport-Backend.md
- `lgpd_gate` verdict in Handoff Report
```

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| Article II — frontmatter name inconsistency | `module.yaml` id (`ava-coder-dotnet-backend`) ≠ frontmatter `name` (`ava-stack-dotnet-backend`) | Pre-existing inconsistency; not introduced by this PBI | Noted in research R5; separate cleanup PBI recommended |
| Article XI — SKILL.md routes to wrong file | `.github/skills/ava-coder-dotnet/SKILL.md` delegates to `tobe-architecture/agents/coder-dotnet.md` (different file) | Pre-existing routing issue; guardrail correctly targets `tech-stack/agents/coder-dotnet-backend.md` per PBI | Tracked separately; orchestrator dispatches via routing_key, not via SKILL.md |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Nominal BDD | Manual review | Spec Scenario 1: LGPD-01..04 PASS → report APPROVED, no block |
| Edge: no PII fields | Manual review | Spec Scenario 2: `lgpd_gate = "N/A"`, generation continues |
| Gate trigger: LGPD-01 FAIL | Manual review | Spec Scenario 3: `lgpd_gate = "BLOCKED"`, `human_gate_required = true` |
| Edge: missing security-architecture.md | Manual review | Spec Scenario 4: fallback canonical list, warning in report |
| Regression | Re-run existing scenarios (no PII fields) | Existing V-01..V-13 gate logic unaffected |

---

## Phase 0 — Research Summary

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Insert guardrail **inside** existing Security Compliance Review Gate | Avoids duplicate report generation; reuses existing §7 read | Separate new agent: rejected (increases pipeline complexity) |
| Append `## LGPD PII Compliance` to existing report | Preserves parser compatibility with `orchestrator-stack.md` step 6b.3 and `build_summary_comprehensive.py` | New separate report file: rejected (breaks downstream parsers) |
| Masking detection via Grep patterns | Deterministic; works on generated `.cs` files without compilation | AST analysis: rejected (requires Roslyn tooling not available in agent context) |
| Audit log detection via `IAuditLog\|SaveChangesAsync` Grep | Covers both DI-based and EF-override patterns | Require specific class name: rejected (too rigid for multi-BC variations) |
| Fallback to canonical PII list when §7 absent | Guarantees guardrail runs even on projects without full security-architecture.md | Block if §7 absent: rejected (too brittle for early-stage projects) |
