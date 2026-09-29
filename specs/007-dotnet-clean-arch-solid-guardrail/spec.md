# Agent Specification: Clean Architecture & SOLID Guardrail for coder-dotnet-backend

**Feature Branch**: `007-dotnet-clean-arch-solid-guardrail`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: modify-existing
**PBI**: [2274 — Guardrail de Clean Architecture e SOLID: prevencao de anti-patterns em controllers .NET](https://dev.azure.com)
**Input**: Add explicit Clean Architecture guardrail with SOLID negative examples and post-generation verification to `coder-dotnet-backend.md`.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-dotnet-backend` |
| **Current Version** | `1.0.0` |
| **New Version** | `1.0.1` |
| **Version Bump Type** | PATCH — adds new guardrail section (G10) and post-generation verification step; no output contract change |
| **Phase** | `F3` |
| **Module** | `tech-stack` |
| **Target File** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |
| **Role** | Generates production-ready C# backend code following Clean Architecture, CQRS, EF Core |
| **Skill** | `ava-stack-dotnet-backend` (existing — no changes required) |
| **Dispatch** | user-facing via SKILL.md (existing) |

> **modify-existing rules applied**:
> - Module.yaml entry already exists — Category 4 tasks are N/A
> - SKILL.md already exists — Category 1.5 is N/A
> - No new output contract files — Section 3 documents no change to `## Output Contract`

---

## 2. Agent Frontmatter

No changes to frontmatter keys or `allowed-tools`. Only the `version` field is bumped:

```yaml
---
name: ava-stack-dotnet-backend
version: "1.0.1"    # was "1.0.0"
description: |
  Gera código C# production-ready seguindo Clean Architecture, CQRS
  com MediatR, EF Core, FluentValidation e boas práticas. Stack e versão
  lidos de `tobe_stack.backend_version` em project-config.yaml.
  Ativa com: "gerar código .NET", "criar endpoint", "implement C# class",
  "CQRS command", "EF Core migration".
allowed-tools: Read, Write, Edit, Bash, Glob
---
```

---

## 3. Output Contract

**No changes.** The output contract (`source_code`, `test_code`, `migrations`,
`mandatory_docs`) remains identical. This change adds enforcement rules and negative
examples inside the agent body, not new artifact paths.

---

## 4. Changes Required

### 4.1 New Guardrail G10 — Clean Architecture Anti-Patterns (SOLID: SRP & DIP)

Insert a new guardrail section **`### G10`** after the existing `### G9` block in the
`## ⚠️ GUARDRAILS` section of `coder-dotnet-backend.md`.

**Rules enforced by G10**:

| Rule | Description |
|---|---|
| **G10-R1** | (SRP) Business logic MUST NOT reside in controllers. Controllers dispatch via `ISender.Send(...)` exclusively and return HTTP results — no business decisions inline. |
| **G10-R2** | (DIP) Application layer handlers MUST NEVER reference `DbContext` directly. All persistence is accessed exclusively through repository interfaces (e.g., `ITitleRepository`). |
| **G10-R3** | (DIP) NEVER use `new ConcreteRepository(...)` in handlers or application services. All repository dependencies are injected via constructor. |
| **G10-R4** | (DIP) NEVER use `new ConcreteService(...)` in handlers or application services. All service dependencies are injected via constructor. |

**Negative examples to document** (anti-patterns with corrective counterpart):

| Anti-Pattern | SOLID Violation | Negative (❌) | Positive (✅) |
|---|---|---|---|
| Business logic in controller | SRP | `if (amount > limit) { return BadRequest(...); }` inside a controller action | Logic lives in a `Command` handler; controller calls `_sender.Send(cmd)` |
| Direct DbContext in Application | DIP | `_dbContext.Titles.FirstOrDefault(...)` in a handler | `await _titleRepository.GetByIdAsync(id)` via injected `ITitleRepository` |
| Direct `new Repository()` in handler | DIP | `var repo = new TitleRepository(_dbContext);` | Repository injected via constructor: `private readonly ITitleRepository _repo;` |
| Direct `new Service()` in handler | DIP | `var svc = new NotificationService();` | Service injected via constructor: `private readonly INotificationService _svc;` |

### 4.2 New Post-Generation Verification Step

Insert as a new standalone section `## Verificação Pós-Geração — Clean Architecture Compliance`,
placed immediately after the closing fence of `## Output Contract` and before
`## Security Compliance Review Gate` (resolved in research.md §6).

The verification runs **after all code files are written** and **before the Security
Compliance Review Gate** (existing step). On violation the agent MUST NOT proceed to the
Security Compliance Review Gate.

**Verification commands** (Bash — uses pipe-filter pattern per research.md §2 for cross-platform compatibility):

```bash
# Must return 0 results — any match is a violation
grep -rn "new [A-Za-z]*Repository" \
  "projects/{project_name}/outputs/tobe/source-code/" \
  --include="*.cs" | grep -v "/Infrastructure/"

grep -rn "\bDbContext\b" \
  "projects/{project_name}/outputs/tobe/source-code/" \
  --include="*.cs" | grep -v "/Infrastructure/" | grep -v "\.Tests/"
```

**Decision logic**:
- If either grep returns ≥ 1 result → emit `⛔ VIOLATION DETECTED` with file/line details and halt generation output
- If both return 0 results → emit `✅ Clean Architecture compliance verified` and proceed

---

## 5. User Scenarios (Given-When-Then)

> **Story descriptions in Portuguese. Acceptance scenarios in English.**

### Scenario 1 — Nominal Path: Guardrail G10 prevents anti-pattern generation (Priority: P1)

**Story**: Como o agente `ava-stack-dotnet-backend`, ao gerar código de controller e handler,
quero garantir que o código produzido não viola SRP e DIP, para que o código gerado passe na
verificação pós-geração com zero resultados de `new.*Repository` e `DbContext` fora de Infrastructure.

**Acceptance Scenarios**:

1. **Given** a project with `pipeline_mode = "generic"` and a controller instruction to generate a `POST /titles` endpoint, **When** the agent generates the controller, **Then** the controller body contains only `await _sender.Send(command)` and no `DbContext` or repository references.
2. **Given** the above, **When** the agent generates the corresponding handler, **Then** the handler uses `await _titleRepository.GetByIdAsync(id)` (injected interface), not `_dbContext.Titles.*` or `new TitleRepository(...)`.
3. **Given** generation completes, **When** the post-generation grep verification runs, **Then** both grep commands return 0 results and the agent emits `✅ Clean Architecture compliance verified`.

---

### Scenario 2 — Edge Case: G10 passive guardrail text is self-contained and prevents anti-pattern generation (Priority: P1)

> **Note (C3 remediation)**: G10 is a static Markdown instruction in the agent body, not a runtime auto-correction mechanism. "Prevention" means the guardrail text is explicit enough that the LLM does not generate anti-patterns. The post-generation grep gate (Scenario 3) catches anything that slips through.

**Story**: Como o agente `ava-stack-dotnet-backend`, quero que o texto do guardrail G10 seja suficientemente explícito para que o código gerado não precise de correção pós-hoc, garantindo que a verificação pós-geração passe com zero violações em condições normais.

**Acceptance Scenarios**:

1. **Given** a project generating a `GET /titles/{id}` handler, **When** the G10 guardrail is active in the agent body, **Then** the generated handler does NOT contain `_dbContext.*` or `new TitleRepository(...)` — the LLM follows the documented correct patterns.
2. **Given** generation completes, **When** the post-generation verification runs, **Then** both grep commands return 0 results and the agent emits `✅ Clean Architecture compliance verificada`.

---

### Scenario 3 — Quality Gate: Violation detected post-generation halts output (Priority: P1)

**Story**: Como o agente, se o código gerado contém lógica de negócio em um controller,
quero que a verificação pós-geração detecte e sinalize a violação, para que o time de QA
receba um alerta claro antes do handoff.

**Acceptance Scenarios**:

1. **Given** the generated code contains `if (amount > limit) { return BadRequest(...); }` inside a controller action, **When** the post-generation verification runs, **Then** the agent emits `⛔ VIOLATION DETECTED` with the file path and line number.
2. **Given** the above, **Then** the agent emits the full violation output format (`⛔ VIOLATION DETECTED — G10`, arquivo:linha, padrão detectado, regra ID, ação requerida) and does NOT proceed to the Security Compliance Review Gate.
3. **Given** the above, **Then** the agent terminates the generation pipeline at the verification step — no further output files are written and the Security Compliance Review Gate is not invoked.

---

## 6. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern — `ava-stack-dotnet-backend` (existing, unchanged)
- [x] Frontmatter change is PATCH only: version `1.0.0 → 1.0.1`, no contract change
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] Module.yaml entry already exists — Category 4 tasks are N/A (Article IV)
- [x] No new output paths introduced — Output Contract unchanged (Article II)
- [x] BDD scenarios cover nominal (G10 prevents), edge (auto-correct), and gate (halt on violation) paths (Article VI)
- [x] No hardcoded technology versions in G10 guardrail (Article I)
- [x] SKILL.md already exists — no dispatch changes required (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Stack orchestrator | `ava-stack-orchestrator` | Routes invocation to `ava-stack-dotnet-backend` |
| Docs researcher | `ava-stack-docs-researcher` | Provides `docs-research-bundle.md` consumed before codegen (existing Step 1.5) |
| Build validator | `ava-stack-build-validator` | Runs after codegen to confirm `dotnet build` still passes with generated code |

---

## 8. Exclusions

- **EF Core migration files** (`Migrations/` folder) — exempt from grep verification; they legitimately reference `DbContext` in Infrastructure
- **DbContext registration in `DependencyInjection.cs`** (Infrastructure layer) — legitimate, not a violation
- **Unit test projects** (`*.Tests/`) — test files may mock repositories; exempt from G10-R4 grep check
- **`ava-stack-angular-frontend`** — out of scope; frontend has no C# layer
- **`ava-build-cycle-*` agents** — out of scope; G10 targets the generic pipeline path only

---

## 9. Assumptions

- The `coder-dotnet-backend.md` agent file is at `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
- Existing guardrails G1–G9 remain unchanged; G10 is inserted after G9
- The project Sophia validation (AC #4 of PBI 2274) is verified via the post-generation grep step, not a separate agent
- `grep` (bash) or `Select-String` (PowerShell) is available during agent execution (`allowed-tools` includes `Bash`)
- Repository interface naming convention follows `I{EntityName}Repository` pattern (established by existing template)

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Guardrail G10 present | `coder-dotnet-backend.md` contains `### G10` section with G10-R1 through G10-R4 rules |
| Negative examples documented | At least 4 anti-pattern / correct-pattern pairs (SRP × 1, DIP × 3) |
| Post-generation verification present | Grep commands for `new.*Repository` and `DbContext` outside `Infrastructure/` documented in agent body |
| Zero violations in Sophia | Running grep on `projects/sophia/outputs/tobe/source-code/` (excluding `Infrastructure/`) returns 0 matches |
| Build unaffected | `dotnet build` continues to pass on all existing generated projects after this change |
| Version bumped | Frontmatter shows `version: "1.0.1"` |
