# Agent Specification: coder-dotnet-backend — LGPD PII Guardrail

**Feature Branch**: `008-lgpd-pii-guardrail`
**Created**: 2026-07-08
**Status**: Draft
**Change Type**: modify-existing
**Input**: PBI #2294 — Guardrail de compliance LGPD para endpoints com dados pessoais no coder .NET

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-dotnet-backend` (frontmatter) / `ava-coder-dotnet-backend` (module.yaml) — see note below |
| **Version** | MINOR bump: `1.0.0 → 1.1.0` |
| **Phase** | `F3` (Tech Stack / Code Generation) |
| **Module** | `tech-stack` |
| **Role** | Adds an LGPD PII Guardrail section to the Security Compliance Review Gate inside `coder-dotnet-backend.md`, enforcing masking, audit-log, and RBAC checks whenever generated entities contain PII fields |
| **Skill** | _(no skill for this dispatch path — see note below)_ |
| **Dispatch** | internal-only via `ava-stack-orchestrator` (`routing_key: "dotnet"`) |
| **Target file** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |

> **Change Type is `modify-existing`**:
> - Target file already exists; no new file is created.
> - Version bump type: **MINOR** (new guardrail section = new optional behavior, no contract removal).
> - `module.yaml` entry already exists — Category 4 module-registration tasks are N/A.
> - Agent is dispatched internally by `ava-stack-orchestrator`; no user-facing SKILL.md is involved in this dispatch path — Category 1.5 is N/A.
>
> **Naming note**: The file `coder-dotnet-backend.md` has three different identifiers in use:
> - frontmatter `name`: `ava-stack-dotnet-backend`
> - `module.yaml` id: `ava-coder-dotnet-backend` (with `routing_key: "dotnet"`)
> - `.github/skills/ava-coder-dotnet/SKILL.md` exists but routes to a **different file** (`tobe-architecture/agents/coder-dotnet.md`) — do not use it for this change.
> Resolving this naming inconsistency is out of scope for this PBI.

---

## 2. Agent Frontmatter (updated `description` only)

The existing frontmatter in `coder-dotnet-backend.md` must have its `version` bumped and `description` updated to reference the new LGPD guardrail activation phrase:

```yaml
---
name: "ava-stack-dotnet-backend"
version: "1.1.0"
description: |
  Gera código C# production-ready para entidades, repositórios e handlers
  seguindo Clean Architecture, CQRS e EF Core.
  Inclui guardrail de compliance LGPD que verifica masking de campos PII
  em ILogger, audit log em operações de escrita e RBAC nos endpoints
  /anonymize e /delete-data.
  Ativa com: "gerar código backend", "codegen dotnet", "guardrail LGPD backend",
  "verificar compliance LGPD endpoints", "PII masking backend".
allowed-tools: Read, Write, Edit, Glob, Grep
---
```

---

## 3. Output Contract

This change **appends** to the existing Security Compliance Review Gate section within `coder-dotnet-backend.md`. It does **not** produce a standalone new artifact file; instead it enriches the existing `SecurityComplianceReport-Backend.md` output already declared in the agent.

| Artifact | Path | Notes |
|---|---|---|
| LGPD section in compliance report | `projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Backend.md` | New `## LGPD PII Compliance` section appended; does not replace existing content |

> **Append decision**: `SecurityComplianceReport-Backend.md` is an existing output artifact.
> The guardrail adds a new `## LGPD PII Compliance` section (one row per PII field) rather than
> creating a separate file, preserving `build_summary_comprehensive.py` parser compatibility.

---

## 4. Guardrail Specification

### 4.1 PII Field Canonical Set

The guardrail must recognize the following canonical PII field identifiers (case-insensitive match against property names and parameter names in generated C# code):

| Canonical Name | Common aliases |
|---|---|
| `cpf` | `CPF`, `Cpf`, `numeroCpf` |
| `email` | `Email`, `emailAddress` |
| `nome` | `Nome`, `nomeCompleto`, `firstName`, `lastName` |
| `endereco` | `Endereco`, `logradouro`, `address` |
| `telefone` | `Telefone`, `celular`, `phone` |
| `dataNascimento` | `DataNascimento`, `birthDate`, `dtNasc` |

The PII field list is sourced from `security-architecture.md` Section 7 of the active project. The canonical set above is the fallback when `security-architecture.md` is absent.

### 4.2 Checks Performed

| Check ID | Description | Failure Action |
|---|---|---|
| `LGPD-01` | Every `ILogger.Log*` call that includes a PII field value MUST apply masking (e.g. `[MASKED]`, `PiiMask.Mask(...)`, or `_anonymizer.Anonymize(...)`). | Block generation; emit `security_gate: BLOCKED` |
| `LGPD-02` | Every entity with ≥1 PII field MUST have an audit-log interceptor or EF Core `SaveChangesAsync` override that records write operations. | Block generation; emit `security_gate: BLOCKED` |
| `LGPD-03` | Endpoints matching `/anonymize` or `/delete-data` MUST have `[Authorize(Policy = "DataOwnerOrDPO")]` attribute. | Block generation; emit `security_gate: BLOCKED` |
| `LGPD-04` | PII fields in entity DTOs sent to external services MUST NOT appear in plain text (must use masking or exclusion). | Warning only; emit `security_gate: APPROVED_WITH_RISKS` |

### 4.3 Report Section Format

The `## LGPD PII Compliance` section added to `SecurityComplianceReport-Backend.md`:

```markdown
## LGPD PII Compliance

| Campo PII | LGPD-01 (masking log) | LGPD-02 (audit log write) | LGPD-03 (RBAC endpoint) | LGPD-04 (DTO externo) | Status |
|---|---|---|---|---|---|
| cpf | ✅ PASS | ✅ PASS | ➖ N/A | ✅ PASS | ✅ COMPLIANT |
| email | ✅ PASS | ✅ PASS | ➖ N/A | ✅ PASS | ✅ COMPLIANT |
| ...  | ...     | ...     | ...     | ...           | ...     |

**lgpd_gate**: APPROVED | APPROVED_WITH_RISKS | BLOCKED | N/A
```

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal: Entity with PII Fields, All Checks Pass (Priority: P1)

**Story**: Como o agente de geração de código .NET, quero verificar automaticamente
que entidades com campos PII estão em conformidade com a LGPD antes de confirmar
o código gerado, garantindo que masking, audit log e RBAC estejam presentes.

**Acceptance Scenarios**:

1. **Given** a Bounded Context schema containing a `Cliente` entity with `cpf`, `email`, and `telefone` fields, **When** `coder-dotnet-backend` generates the entity and its controller, **Then** the LGPD guardrail (LGPD-01..03) executes automatically within the Security Compliance Review Gate.
2. **Given** the generated code applies `PiiMask.Mask(cpf)` in all `ILogger.Log*` calls, **When** LGPD-01 runs, **Then** it passes and the report marks `cpf → LGPD-01: ✅ PASS`.
3. **Given** an EF Core `SaveChangesAsync` override records audit entries for `Cliente` write operations, **When** LGPD-02 runs, **Then** it passes and the report marks `Cliente → LGPD-02: ✅ PASS`.
4. **Given** the `/anonymize` endpoint has `[Authorize(Policy = "DataOwnerOrDPO")]`, **When** LGPD-03 runs, **Then** it passes and `SecurityComplianceReport-Backend.md` receives a `## LGPD PII Compliance` section with `lgpd_gate: APPROVED`.

---

### Scenario 2 — Edge Case: No PII Fields in Schema (Priority: P2)

**Why this priority**: Guardrail must be transparent when no PII is present — must not block or warn unnecessarily.

**Acceptance Scenarios**:

1. **Given** a Bounded Context schema with no properties matching the canonical PII set, **When** `coder-dotnet-backend` executes, **Then** the LGPD guardrail skips all four checks.
2. **Given** the above, **Then** the `## LGPD PII Compliance` section notes "Nenhum campo PII detectado — verificação ignorada" and `lgpd_gate: N/A`.
3. **Given** the above, **Then** `AgentResult.success` is `true` and code generation proceeds normally.

---

### Scenario 3 — Quality Gate: PII Field Without Masking (Priority: P1)

**Why this priority**: LGPD violation must always block generation to prevent data leakage.

**Acceptance Scenarios**:

1. **Given** a `Paciente` entity with a `cpf` field where the generated `ILogger.LogInformation("CPF: {cpf}", paciente.Cpf)` call is present **without** masking, **When** LGPD-01 runs, **Then** it fails with finding `"ILogger exposes cpf without masking in PacienteService.cs:42"`.
2. **Given** the above, **Then** `AgentResult.security_gate` is `BLOCKED` and code generation is halted.
3. **Given** the above, **Then** the `SecurityComplianceReport-Backend.md` records `cpf → LGPD-01: ❌ FAIL` with the specific file and line reference.
4. **Given** the above, **Then** `AgentResult.human_gate_required` is `true`.

---

### Scenario 4 — Edge Case: Missing security-architecture.md (Priority: P2)

**Why this priority**: Graceful degradation when prerequisite artifact is absent.

**Acceptance Scenarios**:

1. **Given** `security-architecture.md` Section 7 is absent or the file does not exist, **When** the guardrail initializes, **Then** it falls back to the canonical PII set defined in section 4.1 of this spec.
2. **Given** the above, **Then** a warning is added to the report: "security-architecture.md Section 7 not found — using fallback PII field list".
3. **Given** the above, **Then** `AgentResult.success` remains `true` (fallback does not block).

---

## 6. Quality Gate Requirements

- [ ] Agent frontmatter `name: "ava-stack-dotnet-backend"` follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [ ] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] No new `module.yaml` registration needed — entry already exists (Article IV)
- [ ] Output path uses lowercase `{project_name}` and correct phase folder `tobe/docs/` (Article II)
- [ ] BDD scenarios cover nominal (S1), edge/no-PII (S2), gate/blocked (S3), edge/missing-artifact (S4) (Article VI)
- [ ] Security sub-pipeline impact: guardrail is additive; does not replace `ava-asis-security-orchestrator` (Article VII)
- [ ] No technology versions hardcoded in guardrail logic; canonical PII list is in agent body (Article I)
- [ ] Skill/Agent split: SKILL.md already exists — only agent `.md` body modified (Article XI)
- [ ] No `[NEEDS CLARIFICATION]` markers remain
- [ ] MINOR version bump and `CHANGELOG.md` entry prepared (Article X)

---

## 7. Dependencies

| Dependency | Agent ID / Artifact | Reason |
|---|---|---|
| Security Architecture TO-BE | `ava-tobe-security-design` | Provides `security-architecture.md` Section 7 (canonical PII field list per BC) |
| Security Compliance Gate | `ava-deliverable-security-compliance` | Consumes the `SecurityComplianceReport-Backend.md` output — LGPD section must be compatible with its parser |
| Summary Validator | `build_summary_comprehensive.py` | Must not break when new `## LGPD PII Compliance` section is appended to the report |

---

## 8. Exclusions

- **Frontend LGPD checks** — handled by `ava-stack-angular-frontend` (separate scope)
- **Database-level PII masking** — handled by `ava-tobe-security-design` (section 7 TDE/DDM config)
- **SAST scanning** — handled by `ava-asis-security-orchestrator` sub-agents; this guardrail is codegen-time only
- **LGPD Data Subject Request (DSR) workflow** — out of scope; requires a separate PBI

---

## 9. Assumptions

- `coder-dotnet-backend.md` already contains a "Security Compliance Review Gate" section; the new LGPD guardrail is inserted within that section, not appended at file end.
- The existing `SecurityComplianceReport-Backend.md` output format is append-compatible (new `##` section does not break downstream parsers).
- `security-architecture.md` Section 7 uses a structured format (table or YAML block) parseable by the guardrail; if not, the canonical fallback list (section 4.1) is used.
- The `[Authorize(Policy = "DataOwnerOrDPO")]` policy name is canonical and registered in the project's authorization configuration as defined by `ava-tobe-security-design`.
- Version of `coder-dotnet-backend.md` at time of implementation is the one current in `main`; no concurrent modifications are assumed.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Guardrail integrated | `coder-dotnet-backend.md` contains a `### LGPD PII Compliance Guardrail` subsection within the Security Compliance Review Gate after the change |
| No PII in plain ILogger | Zero occurrences of unmasked PII field values in generated `ILogger.Log*` calls (verified by Scenario 3 test) |
| Audit log coverage | Every entity with ≥1 PII field has a corresponding EF Core audit interceptor or `SaveChangesAsync` override in generated code |
| RBAC on sensitive endpoints | Generated `/anonymize` and `/delete-data` endpoints always have `[Authorize(Policy="DataOwnerOrDPO")]` |
| Report section present | `SecurityComplianceReport-Backend.md` includes `## LGPD PII Compliance` with one row per detected PII field and an overall gate verdict |
| No regression | Existing tests for `coder-dotnet-backend.md` scenarios without PII fields continue to pass |
| Version bumped | Agent frontmatter `version` is incremented (MINOR) and `CHANGELOG.md` has a corresponding entry |
