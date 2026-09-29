# Agent Development Tasks: ava-stack-dotnet-backend (G10 patch)

**Plan**: `specs/007-dotnet-global-exception-handler/plan.md`
**Agent ID**: `ava-stack-dotnet-backend` | **Phase**: `F3` | **Module**: `tech-stack`
**Change type**: modify-existing (PATCH) | **Target**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Categories 3, 4, 5 are **SKIP** for this PATCH — see notes inline.

---

## Category 1 — Frontmatter & Contract Definition

> PATCH scope: only the version/date fields need changing. All other frontmatter fields are valid.

- [X] **1.1** In `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`, replace:
  ```
  version: "1.0.0"
  date: 2026-06-10
  ```
  with:
  ```
  version: "1.0.1"
  date: 2026-07-07
  ```
  _(Edit T1 from data-model.md — apply **after** 2.1–2.3 to confirm all content edits succeeded first)_

---

## Category 2 — Agent Behavior & Instructions

> **Depends on Category 1 being applied.** These are the 3 substantive edits that close SC-1, SC-2, SC-3.
> All 3 edits target the same file; apply them in order 2.1 → 2.2 → 2.3.

- [X] **2.1** Update routing guard — close SC-1.
  File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  Find (exact string, inside the `SE bundle NÃO EXISTIR` block):
  ```
    → PROSSEGUIR com guardrails G1-G9 existentes (non-blocking)
  ```
  Replace with:
  ```
    → PROSSEGUIR com guardrails G1-G10 existentes (non-blocking)
  ```

- [X] **2.2** Add `ValidationException` class to exception hierarchy code block — close SC-2.
  File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  Find (end of hierarchy block — last class definition):
  ```
  // SharedKernel/Exceptions/BusinessRuleViolationException.cs
  /// <summary>Regra de negócio violada → HTTP 422 Unprocessable Entity.</summary>
  public sealed class BusinessRuleViolationException(string rule, string? detail = null)
      : DomainException(rule, detail);
  ```
  Replace with:
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

- [X] **2.3** Add `ValidationException` switch arm to `GlobalExceptionHandler.TryHandleAsync` — close SC-3.
  File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  Find (switch expression body — 4 arms — **8-space indent** as in the actual file):
  ```
        var (statusCode, title) = exception switch
        {
            NotFoundException              => (StatusCodes.Status404NotFound,           "Recurso não encontrado"),
            BusinessRuleViolationException => (StatusCodes.Status422UnprocessableEntity, "Regra de negócio violada"),
            DomainException                => (StatusCodes.Status400BadRequest,          "Erro de domínio"),
            _                              => (StatusCodes.Status500InternalServerError,  "Erro interno")
        };
  ```
  Replace with (5 arms — `ValidationException` inserted BEFORE `DomainException`):
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
  > **Critical ordering**: `ValidationException` derives from `DomainException`. C# switch
  > matches first-fit on type hierarchy — `ValidationException` MUST appear before `DomainException`.

---

## Category 3 — Shared Schema Updates

> **SKIP** — no changes to `agent-task.schema.json` or `agent-result.schema.json`.
> Confirmed: plan section "Scale/Scope" shows no new output artifacts or schema fields.

---

## Category 4 — Module Registration

> **SKIP** — `src/modules/ava-fabric-agents/tech-stack/module.yaml` already registers
> `ava-stack-dotnet-backend`. PATCH version bumps do NOT require module.yaml changes.

---

## Category 5 — Quality Gate Checklists

> **SKIP** — `.github/skills/ava-stack-dotnet-backend/SKILL.md` already exists and
> correctly dispatches to the agent. No orchestrator wiring changes for this PATCH.

---

## Category 6 — Acceptance Validation

> Depends on Category 2 complete. Validates all 5 success criteria from spec.md.

- [X] **6.1** Run the all-in-one validation script from `specs/007-dotnet-global-exception-handler/quickstart.md`:
  ```powershell
  cd "c:\CODIGOS CAMINHO\Agentes-Fabrica\imfai-ava-fabric-apps-agents"
  $f = "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md"
  $content = Get-Content $f -Raw
  $checks = @(
    @{ Name="V1 version 1.0.1";             Pass=($content -match 'version: "1\.0\.1"') },
    @{ Name="V2 G1-G10 routing guard";      Pass=($content -match "G1-G10 existentes") },
    @{ Name="V2-neg G1-G9 gone";            Pass=-not($content -match "G1-G9 existentes") },
    @{ Name="V3 ValidationException class"; Pass=($content -match "class ValidationException") },
    @{ Name="V4 ValidationException switch";Pass=($content -match "ValidationException\s*=>") },
    @{ Name="V4-ord ValidationException before DomainException"; Pass=(
        $content.IndexOf("ValidationException            =>") -lt
        $content.IndexOf("DomainException                =>")
    )},
    @{ Name="V5 ProblemDetails type field"; Pass=($content -match 'Extensions\["type"\]') },
    @{ Name="V6 ErrorOr prohibition";       Pass=($content -match "NUNCA.*throw.*NotFoundException") }
  )
  $pass = 0; $fail = 0
  foreach ($c in $checks) {
    $icon = if ($c.Pass) { "PASS" } else { "FAIL" }
    if ($c.Pass) { $pass++ } else { $fail++ }
    Write-Output "$icon  $($c.Name)"
  }
  Write-Output ""; Write-Output "Result: $pass/$($checks.Count) PASS"
  ```
  **Expected**: `Result: 8/8 PASS`. Do not proceed to Category 7 until this passes.

- [X] **6.2** [P] Spot-check markdown structure — verify G10 section is still intact after edits:
  ```powershell
  Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
    -Pattern "### G(10|9|8|7|6|5|4|3|2|1) "
  ```
  **Expected**: 10 matches (one heading per guardrail G1–G10, no guardrail deleted).

---

## Category 7 — Documentation & Catalog Update

> Can run parallel with Category 6.

- [X] **7.1** [P] Add `CHANGELOG.md` entry at the top:
  ```markdown
  ## [1.0.1] — 2026-07-07 — ava-stack-dotnet-backend
  ### Changed
  - G10: added `ValidationException` class to SharedKernel exception hierarchy (`sealed class ValidationException : DomainException` → HTTP 400)
  - G10: added `ValidationException` arm to `GlobalExceptionHandler.TryHandleAsync` switch expression (before `DomainException` arm — required for correct C# pattern matching)
  - Routing guard: updated stale "G1-G9 existentes" to "G1-G10 existentes"
  ```

- [X] **7.2** [P] In `docs/agents-catalog.md`, find the `ava-stack-dotnet-backend` row and bump version to `1.0.1`.

---

## Completion Checklist

- [ ] Category 1 complete — version `1.0.1`, date `2026-07-07` in frontmatter
- [ ] Category 2 complete — 3 edits applied (routing guard, ValidationException class, switch arm)
- [ ] Category 6 complete — validation script returns `8/8 PASS`
- [ ] Category 7 complete — CHANGELOG.md entry added, agents-catalog.md bumped
- [ ] No other agent files modified (SKILL.md, module.yaml, other guardrails untouched)

---

## Dependency Graph

```
1.1 (version bump)
  └─ 2.1 (routing guard)  ─┐
  └─ 2.2 (class def)       ├─ 6.1 (validation 8/8) ─┐
  └─ 2.3 (switch arm)     ─┘                          ├─ DONE
                               6.2 (structure check) ─┘
                               7.1 (CHANGELOG) ──────────── parallel with 6.*
                               7.2 (catalog)  ──────────── parallel with 6.*
```

## Parallel Opportunities

- `7.1` and `7.2` can execute while `6.1` is running
- `2.1`, `2.2`, `2.3` all target the same file and MUST be applied sequentially
- `6.2` can run in parallel with `6.1`
