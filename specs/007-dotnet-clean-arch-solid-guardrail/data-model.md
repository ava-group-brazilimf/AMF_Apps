# Data Model: Clean Architecture & SOLID Guardrail (spec 007)

**Date**: 2026-07-07
**Spec**: `specs/007-dotnet-clean-arch-solid-guardrail/spec.md`

> For a Markdown agent modification, the "data model" describes the structural
> changes to the agent file — the new sections, their position, and their content
> schema. No database entities or code data models are involved.

---

## Target File Structure (after change)

```
src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md
├── [frontmatter]                     version: "1.0.1"  (was "1.0.0")
├── ## Routing Guard
├── ## Input Adicional — Docs Research Bundle
├── ## Role & Persona
├── ## Regras Invioláveis de Código    ← ADD: rule 7 (ISender/IService only in controllers)
├── ## ⚠️ GUARDRAILS
│   ├── ### G1 — Mapster DI
│   ├── ### G2 — Domain member verification
│   ├── ### G3 — async sem await
│   ├── ### G4 — CA1305 / CA1310
│   ├── ### G5 — IAsyncDisposable
│   ├── ### G6 — Rate Limiting & Azure Monitor
│   ├── ### G7 — Azure Application Insights
│   ├── ### G8 — Health Endpoints
│   ├── ### G9 — NuGet Package Completeness
│   └── ### G10 — Clean Architecture Anti-Patterns (SOLID: SRP & DIP)  ← NEW
├── ## Clean Architecture Template
├── ## Skills
├── ## Output Contract                 (unchanged)
├── ## Verificação Pós-Geração         ← NEW SECTION
├── ## Security Compliance Review Gate (unchanged)
├── ## Handoff                         (unchanged)
└── ## FASE OBRIGATÓRIA               (unchanged)
```

---

## New Section: `### G10` Schema

**Heading**: `### G10 — Clean Architecture Anti-Patterns (SOLID: SRP & DIP)`

**Content structure**:
```
1. Opening diagnostic sentence (1 line)
2. Rules sub-table: G10-R1 through G10-R4 (4 rows)
3. Anti-pattern pairs: 4 × (❌ ERRADO block + ✅ CORRETO block)
   3a. SRP — Business logic in controller
   3b. DIP — Direct DbContext in Application handler
   3c. DIP — new ConcreteRepository() in handler
   3d. DIP — new ConcreteService() in handler
```

**Rule summary table fields**:

| Field | Type | Description |
|---|---|---|
| Rule ID | string | `G10-R1` to `G10-R4` |
| Violation | enum | `SRP`, `DIP`, `OCP` |
| Layer scope | enum | `Controller`, `Application`, `any` |
| Prohibited pattern | regex hint | e.g. `new.*Repository`, `DbContext` |
| Required alternative | string | e.g. inject `ITitleRepository` via constructor |

**Code block pairs per anti-pattern** (4 pairs):

| # | Anti-Pattern Label | Prohibited | Allowed |
|---|---|---|---|
| 1 | Lógica de negócio em controller | Any business decision `if`/computation in controller action body | `await _sender.Send(cmd)` only |
| 2 | DbContext direto no Application | `_dbContext.EntitySet.*` in any handler/service in Application layer | `await _repo.MethodAsync(...)` |
| 3 | `new Repository()` em handler | `new ConcreteRepository(...)` anywhere outside Infrastructure | Constructor-injected `IRepository` |
| 4 | `new Service()` em handler | `new ConcreteService(...)` anywhere outside Infrastructure | Constructor-injected `IService` |

---

## New Section: `## Verificação Pós-Geração — Clean Architecture Compliance` Schema

**Position**: Between `## Output Contract` closing fence and `## Security Compliance Review Gate`

**Content structure**:
```
1. Description (2 sentences)
2. Execution timing note
3. Bash verification commands (2 grep commands)
4. Decision table (PASS / VIOLATION logic)
5. Violation output format
```

**Decision table fields**:

| Field | Type | Values |
|---|---|---|
| `new.*Repository` match count (outside Infrastructure, Tests) | int | 0 = PASS; ≥1 = VIOLATION |
| `DbContext` match count (outside Infrastructure, Tests) | int | 0 = PASS; ≥1 = VIOLATION |
| Overall result | enum | `✅ PASS` / `⛔ VIOLATION DETECTED` |
| On VIOLATION | action | Emit file:line details; halt before Security Compliance Gate |

---

## Regras Invioláveis — New Rule 7

**Position**: Appended to the existing numbered list in `## Regras Invioláveis de Código`

**Content**: `7. Controllers injetam apenas ISender (MediatR) ou IService — nunca DbContext, Repository concreto ou Service concreto`

---

## Version Field Change

| Location | Old Value | New Value |
|---|---|---|
| `coder-dotnet-backend.md` frontmatter `version:` | `"1.0.0"` | `"1.0.1"` |
