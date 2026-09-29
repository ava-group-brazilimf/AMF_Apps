# Research: Guardrail G10 — GlobalExceptionHandler Tipado

**Phase**: 0 (Pre-design audit)
**Date**: 2026-07-07
**Feature**: `007-dotnet-global-exception-handler`

---

## Audit: Current state of `coder-dotnet-backend.md`

**File path**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
**Current version**: `1.0.0` (date: 2026-06-10)

### Already present (no changes needed)

| Content | Location | Notes |
|---|---|---|
| G10 heading + preamble | line ~210 | "G10 — GlobalExceptionHandler — Exceções Tipadas por Domínio" |
| `DomainException` abstract base class | G10 hierarchy block | `abstract class DomainException(string message, string? detail = null)` |
| `NotFoundException` class | G10 hierarchy block | Maps → HTTP 404 |
| `BusinessRuleViolationException` class | G10 hierarchy block | Maps → HTTP 422 |
| `GlobalExceptionHandler : IExceptionHandler` template | G10 template block | Uses `IExceptionHandler` interface (ASP.NET Core 8+) |
| Switch: NotFoundException → 404 | G10 switch | Present |
| Switch: BusinessRuleViolationException → 422 | G10 switch | Present |
| Switch: DomainException → 400 | G10 switch | Present |
| Switch: `_` → 500 | G10 switch | Present |
| Mapping table (5 rows incl. ValidationException) | G10 section | Table row for `ValidationException → 400` exists |
| `problem.Extensions["type"]` URI | G10 template | SC-4 satisfied — `type` field is set |
| `⛔ NUNCA` constraints | G10 section | Present |
| Program.cs registration snippet | G10 section | `AddExceptionHandler<GlobalExceptionHandler>()` present |
| `ErrorOr<T>` handler template | Post-G10 section | Full `MatricularAlunoCommand` example with `Error.NotFound`, `Error.Conflict` |
| `⛔ NUNCA usar throw NotFoundException...` prohibition | Post-G10 template | SC-5 satisfied |

### Gaps remaining (changes required)

| Gap | Location | Evidence |
|---|---|---|
| Routing guard says "G1-G9 existentes" | line ~59 | Stale — G10 now exists, text must read "G1-G10 existentes" |
| `ValidationException` class absent from hierarchy code block | G10 hierarchy code block | Only `DomainException`, `NotFoundException`, `BusinessRuleViolationException` defined |
| `ValidationException` absent from `TryHandleAsync` switch | G10 switch expression | Switch has 4 arms (NotFoundException, BusinessRuleViolationException, DomainException, `_`) — no ValidationException arm |

---

## Decisions

### Decision 1 — Result<T> vs ErrorOr<T>

- **Decision**: Standardise on `ErrorOr<T>` (the `ErrorOr` NuGet library)
- **Rationale**: The file already uses `ErrorOr<T>` throughout the handler template section. The user's spec request used `Result<T>` as a conceptual term. They are equivalent (discriminated-union return types). Using `ErrorOr<T>` maintains consistency.
- **Alternatives considered**: Custom `Result<T>` struct — rejected (adds maintenance burden; `ErrorOr` is already referenced).

### Decision 2 — ValidationException placement in hierarchy

- **Decision**: Add `ValidationException` class as a direct subclass of `DomainException`, mapping → HTTP 400.
- **Rationale**: The mapping table row already exists. The class definition is missing — it must be added to the hierarchy code block for completeness.
- **Note on FluentValidation**: FluentValidation's own `ValidationException` (from the `FluentValidation` namespace) is different from this `DomainException`-derived type. The G10 comment already states "tratada pelo pipeline de validação MediatR" — this `ValidationException` is the domain-layer fallback for cases that slip through the MediatR pipeline.
- **Alternatives considered**: Keep mapping table only, no class — rejected (LLM consuming the guardrail needs a concrete class template to generate the file).

### Decision 3 — Switch arm position for ValidationException

- **Decision**: Insert `ValidationException` arm BEFORE `DomainException` (more specific first).
- **Rationale**: C# pattern matching switch is order-sensitive for inheritance hierarchies. `ValidationException : DomainException` — if `DomainException` is listed first, `ValidationException` would match the `DomainException` arm and never reach its own. Order: NotFoundException → BusinessRuleViolationException → ValidationException → DomainException → `_`.
- **Alternatives considered**: After DomainException — incorrect (would be unreachable).

---

## Summary: No NEEDS CLARIFICATION remaining

All 5 success criteria are either already satisfied or have a clear, unambiguous edit path.
Proceed to Phase 1 (data-model.md).
