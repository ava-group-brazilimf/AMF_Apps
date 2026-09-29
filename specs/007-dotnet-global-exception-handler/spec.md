# Agent Specification: Guardrail G10 — GlobalExceptionHandler Tipado

**Feature Branch**: `007-dotnet-global-exception-handler`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: modify-existing
**Input**: "Adicionar guardrail G10 ao `coder-dotnet-backend.md` com template canônico de `GlobalExceptionHandler.cs` usando `IExceptionHandler` (ASP.NET Core 8+). Exceções de domínio DEVEM herdar de `DomainException`. Handlers MediatR retornam `Result<T>` para casos de negócio."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-dotnet-backend` (existing) |
| **Version bump** | `PATCH` — adds guardrail to existing set; no contract change |
| **Phase** | `F3` (Stack / Codegen) |
| **Module** | `tech-stack` |
| **Role** | Generates production-ready C# code following Clean Architecture |
| **Skill** | `ava-stack-dotnet-backend` (existing SKILL.md — no change) |
| **Dispatch** | user-facing via SKILL.md |

> **Change Type is `modify-existing`**:
> - Target file: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
> - Version bump: PATCH (adds guardrail G10 content; no output contract change)
> - module.yaml and SKILL.md already exist and do NOT need updating.

---

## 2. Problem Statement

The `coder-dotnet-backend.md` agent generates ASP.NET Core backends for each bounded context
in migration projects. The `dotnet-program-cs.md` template includes `app.UseExceptionHandler()`
and `builder.Services.AddProblemDetails()`, but **no guardrail enforces**:

1. A typed domain exception hierarchy (`DomainException` base + typed subclasses).
2. Explicit `Exception type → HTTP status code` mapping in `GlobalExceptionHandler`.
3. Consistent `ProblemDetails` schema (`type`, `title`, `detail`, `instance`) across all BCs.
4. A clear rule that MediatR handlers for **business** cases return `Result<T>` / `ErrorOr<T>`
   rather than throwing exceptions.

Without these guardrails the agent may:
- Return HTTP 200 with error payloads (masking errors from clients and monitoring).
- Return inconsistent error shapes between bounded contexts (BC-ContasPagar returns a different
  schema than BC-CadastroCF).
- Allow `throw new Exception("some message")` in business handlers, bypassing the structured
  error flow.

**Current state (as of 2026-07-07)**: G10 content was added to the file but the routing
guard section still references "G1-G9 existentes" (stale). The `ValidationException` type
appears in the mapping table but is absent from the exception hierarchy code block.
`ErrorOr<T>` (the `ErrorOr` NuGet library) is referenced in the template section but the
spec request uses the term `Result<T>` — both patterns are acceptable; this spec standardises
the naming and clarifies the contract.

---

## 3. Output Contract

> This spec modifies an **agent definition file** (not a project output file).
> No new entries in `outputs:` block — the guardrail affects what files the
> *agent generates* inside `projects/{project_name}/outputs/tobe/source-code/`.

Files the guardrail causes the **agent to generate** (generated artefacts, not spec artefacts):

| Generated file | Location inside generated project |
|---|---|
| `DomainException.cs` | `{Module}.Domain/Exceptions/DomainException.cs` |
| `NotFoundException.cs` | `{Module}.Domain/Exceptions/NotFoundException.cs` |
| `BusinessRuleViolationException.cs` | `{Module}.Domain/Exceptions/BusinessRuleViolationException.cs` |
| `ValidationException.cs` | `{Module}.Domain/Exceptions/ValidationException.cs` |
| `GlobalExceptionHandler.cs` | `{Module}.Infrastructure/Http/GlobalExceptionHandler.cs` |

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Handler returns typed result, not exception (P1)

**Story**: Como tech lead revisando o código gerado, quero que todos os handlers de negócio
retornem `ErrorOr<T>` em vez de lançar exceções, para que o fluxo de erro seja previsível
e rastreável em todos os BCs.

**Acceptance Scenarios**:

1. **Given** the agent is asked to generate a `RegistrarPagamentoCommand` handler,
   **When** the handler needs to signal "parcela not found",
   **Then** it calls `return Error.NotFound("Parcela.NotFound", "...")` and does NOT
   throw `NotFoundException` directly.

2. **Given** the generated `GlobalExceptionHandler.cs`,
   **When** an unhandled `NotFoundException` reaches it (e.g., from repository),
   **Then** it returns HTTP 404 with `ProblemDetails.status = 404` and
   `ProblemDetails.instance = <request path>`.

3. **Given** the generated `GlobalExceptionHandler.cs`,
   **When** an unhandled `BusinessRuleViolationException` reaches it,
   **Then** it returns HTTP 422 with `ProblemDetails.status = 422`.

4. **Given** the generated `GlobalExceptionHandler.cs`,
   **When** an unhandled `Exception` (infrastructure failure) reaches it,
   **Then** it returns HTTP 500 and logs at `LogError` level with full stack trace.

---

### Scenario 2 — Consistent ProblemDetails schema across BCs (P1)

**Story**: Como consumidor da API, quero que todos os endpoints retornem erros no mesmo
formato, para que meu código cliente não precise tratar schemas diferentes por bounded context.

**Acceptance Scenarios**:

1. **Given** any 4xx or 5xx error from any BC endpoint,
   **When** the response is inspected,
   **Then** it contains `type`, `title`, `detail`, and `instance` fields in the JSON body.

2. **Given** a `NotFoundException` thrown by `BC-ContasPagar`,
   **And** a `NotFoundException` thrown by `BC-CadastroCF`,
   **When** both errors are received by the client,
   **Then** both have identical JSON schema (same field set, same `type` URL pattern).

---

### Scenario 3 — Routing guard updated (P2)

**Story**: Como agente LLM, quero que a referência "G1-G9 existentes" no routing guard
seja atualizada para "G1-G10 existentes", para que G10 seja incluído nas verificações
non-blocking.

**Acceptance Scenarios**:

1. **Given** the routing guard block in `coder-dotnet-backend.md`,
   **When** the bundle is absent,
   **Then** the text reads "PROSSEGUIR com guardrails G1-G10 existentes (non-blocking)".

---

### Scenario 4 — ValidationException in hierarchy (P2)

**Story**: Como desenvolvedor que usa FluentValidation, quero que `ValidationException`
esteja na hierarquia de exceções, para que erros de validação de entrada também sejam
capturados e mapeados para HTTP 400 com schema consistente.

**Acceptance Scenarios**:

1. **Given** the exception hierarchy code block in G10,
   **When** a consumer looks up `ValidationException`,
   **Then** it finds a class definition inheriting from `DomainException` with HTTP 400 mapping.

2. **Given** the `GlobalExceptionHandler` switch expression,
   **When** a `ValidationException` is thrown,
   **Then** it is mapped to HTTP 400 (not 500).

---

## 5. Success Criteria

| # | Criterion | Source |
|---|---|---|
| SC-1 | Routing guard text updated from "G1-G9" to "G1-G10" | Scenario 3 |
| SC-2 | `ValidationException` class added to exception hierarchy code block | Scenario 4 |
| SC-3 | `ValidationException` added to switch expression in `GlobalExceptionHandler` → 400 | Scenario 4 |
| SC-4 | ProblemDetails schema comment in G10 lists all four fields: `type`, `title`, `detail`, `instance` | Scenario 2 |
| SC-5 | `ErrorOr<T>` / `Result<T>` note in G10 body clarifies that MediatR business handlers MUST NOT throw `DomainException` directly | Scenario 1 |

---

## 6. Scope and Boundaries

**In scope**:
- Edits to `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` only.
- Specifically: routing guard text (line ~59), G10 exception hierarchy code block, G10 switch expression.

**Out of scope**:
- Changes to SKILL.md, module.yaml, or any other agent file.
- Runtime testing of generated code (that is the concern of F5 QA agents).
- Adding new exception types beyond the canonical five (NotFoundException, BusinessRuleViolationException, ValidationException, DomainException, Exception).
- Changes to `dotnet-program-cs.md` (startup template) — Program.cs registration already uses correct calls per the existing G10 content.

---

## 7. Assumptions and Dependencies

| Assumption | Risk if Wrong |
|---|---|
| `IExceptionHandler` interface is available in ASP.NET Core 8+ | Low — confirmed in official docs |
| `ErrorOr<T>` NuGet package is already in the approved NuGet policy | Low — already referenced in agent body |
| FluentValidation pipeline exception is distinct from domain `ValidationException` | Medium — need to clarify in G10 that FluentValidation validation behaviour runs before reaching GlobalExceptionHandler in the MediatR pipeline |
| `Result<T>` in the spec request is synonymous with `ErrorOr<T>` pattern | Low — both represent discriminated union return types; spec standardises on `ErrorOr<T>` as the existing reference |
