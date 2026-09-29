# Change Model: Guardrail G10 — GlobalExceptionHandler Tipado

**Phase**: 1 (Design)
**Date**: 2026-07-07
**Feature**: `007-dotnet-global-exception-handler`
**Target file**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

> This document defines the **exact text changes** (diff specification) to be applied
> to the target file. All 4 edits are independent and can be applied in any order,
> though T1 (version bump) should be applied last to confirm all others succeeded.

---

## Edit T1 — Version + date bump (YAML frontmatter)

**Success Criterion**: — (housekeeping)

**Find** (exact string):
```
version: "1.0.0"
date: 2026-06-10
```

**Replace with**:
```
version: "1.0.1"
date: 2026-07-07
```

---

## Edit T2 — Routing guard: G1-G9 → G1-G10 (SC-1)

**Success Criterion**: SC-1

**Find** (exact string — include surrounding context for uniqueness):
```
  → PROSSEGUIR com guardrails G1-G9 existentes (non-blocking)
```

**Replace with**:
```
  → PROSSEGUIR com guardrails G1-G10 existentes (non-blocking)
```

---

## Edit T3 — Add ValidationException to hierarchy code block (SC-2)

**Success Criterion**: SC-2

**Find** (exact string — end of hierarchy block, after BusinessRuleViolationException):
```
// SharedKernel/Exceptions/BusinessRuleViolationException.cs
/// <summary>Regra de negócio violada → HTTP 422 Unprocessable Entity.</summary>
public sealed class BusinessRuleViolationException(string rule, string? detail = null)
    : DomainException(rule, detail);
```

**Replace with**:
```
// SharedKernel/Exceptions/BusinessRuleViolationException.cs
/// <summary>Regra de negócio violada → HTTP 422 Unprocessable Entity.</summary>
public sealed class BusinessRuleViolationException(string rule, string? detail = null)
    : DomainException(rule, detail);

// SharedKernel/Exceptions/ValidationException.cs
/// <summary>Entrada inválida (bypass do pipeline MediatR) → HTTP 400 Bad Request.</summary>
public sealed class ValidationException(string field, string message)
    : DomainException($"Validação falhou em '{field}': {message}", detail: $"field={field}")
{
    public string Field { get; } = field;
}
```

---

## Edit T4 — Add ValidationException arm to switch expression (SC-3)

**Success Criterion**: SC-3

**Rationale for ordering**: `ValidationException` derives from `DomainException`.
C# switch expressions match first-fit on type hierarchy, so `ValidationException` MUST
appear BEFORE `DomainException` to be reachable.

**Find** (exact string — **8-space indent** matching actual file at line 259):
```
        var (statusCode, title) = exception switch
        {
            NotFoundException              => (StatusCodes.Status404NotFound,           "Recurso não encontrado"),
            BusinessRuleViolationException => (StatusCodes.Status422UnprocessableEntity, "Regra de negócio violada"),
            DomainException                => (StatusCodes.Status400BadRequest,          "Erro de domínio"),
            _                              => (StatusCodes.Status500InternalServerError,  "Erro interno")
        };
```

**Replace with**:
```
        var (statusCode, title) = exception switch
        {
            NotFoundException              => (StatusCodes.Status404NotFound,            "Recurso não encontrado"),
            BusinessRuleViolationException => (StatusCodes.Status422UnprocessableEntity, "Regra de negócio violada"),
            ValidationException            => (StatusCodes.Status400BadRequest,           "Entrada inválida"),
            DomainException                => (StatusCodes.Status400BadRequest,           "Erro de domínio"),
            _                              => (StatusCodes.Status500InternalServerError,  "Erro interno")
        };
```

---

## Summary of all changes

| Edit | File | Lines affected (approx.) | SC |
|---|---|---|---|
| T1 | `coder-dotnet-backend.md` | 10–11 | — |
| T2 | `coder-dotnet-backend.md` | ~59 | SC-1 |
| T3 | `coder-dotnet-backend.md` | after line ~247 | SC-2 |
| T4 | `coder-dotnet-backend.md` | ~262–267 | SC-3 |
| T5 | `.github/copilot-instructions.md` | SPECKIT block | — |

No new files are created in the source tree. No YAML frontmatter fields are added or removed.
