# Quickstart — Validating the Unicode-Safe Regex Guardrail

**Feature**: `007-unicode-safe-regex-guardrail`
**Date**: 2026-07-07

---

## Prerequisites

- The three target files have been modified (see [plan.md](plan.md)):
  - `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  - `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`
  - `src/shared/data/patterns/angular/angular-patterns-reference.md`
- A working IMFAI project (e.g., `projects/Meu-ERP/`) with a bounded context that has `Nome` or similar text fields

---

## Scenario A — Verify G10 is present in `coder-dotnet-backend.md`

**Command:**
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "G10"
```

**Expected output:**
```
coder-dotnet-backend.md:NNN:### G10 — Regex Unicode-safe para campos de texto PT-BR ...
```

**Verify the version bump:**
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "version"
```

Expected: `version: "1.0.1"`

---

## Scenario B — Verify Angular guardrail is present in `coder-angular-frontend.md`

**Command:**
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md" -Pattern "Unicode Regex PT-BR"
```

**Expected output:**
```
coder-angular-frontend.md:NNN:⚠️ **GUARDRAIL (Unicode Regex PT-BR)** ...
```

**Verify the one-liner in principles:**
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md" -Pattern "Regex PT-BR Unicode-safe"
```

Expected: one match in the tech principles list.

---

## Scenario C — Verify reference section in `angular-patterns-reference.md`

**Command:**
```powershell
Select-String -Path "src\shared\data\patterns\angular\angular-patterns-reference.md" -Pattern "PT-BR Validation Patterns"
```

**Expected output:**
```
angular-patterns-reference.md:NNN:## PT-BR Validation Patterns
```

---

## Scenario D — Verify no `[a-zA-Z]` patterns remain for text fields

**Command (search for forbidden pattern in agent files):**
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "\[a-zA-Z\]" | Where-Object { $_.Line -notmatch "PROIBIDO|proibido|forbidden|G10" }
```

**Expected:** no matches (any remaining occurrences should only appear inside the G10 "PROIBIDO" note).

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md" -Pattern "\[a-zA-Z" | Where-Object { $_.Line -notmatch "PROIBIDO|proibido|forbidden|GUARDRAIL" }
```

**Expected:** no matches (any remaining occurrences should only appear inside the guardrail "proibido" note).

---

## Scenario E — Manual codegen smoke test (optional, requires LLM invocation)

1. Invoke `@ava-stack-dotnet-backend` on `projects/Meu-ERP/` or another test project
2. Locate a generated entity with a `Nome` field in `outputs/tobe/source-code/`
3. Grep the generated `.cs` file:

```powershell
Select-String -Path "projects\Meu-ERP\outputs\tobe\source-code\**\*.cs" -Pattern "\[RegularExpression" -Recurse
```

**Expected:** all `[RegularExpression]` attributes on text fields use `\p{L}`, not `[a-zA-Z]`.

4. Invoke `@ava-stack-angular-frontend` and grep the generated TypeScript:

```powershell
Select-String -Path "projects\Meu-ERP\outputs\tobe\source-code\frontend\**\*.ts" -Pattern "Validators\.pattern" -Recurse
```

**Expected:** all `Validators.pattern(...)` calls on text fields include the `u` flag.

---

## Pass Criteria

| Check | Criterion |
|---|---|
| G10 in `coder-dotnet-backend.md` | Section heading `### G10` present |
| Version bump backend | `version: "1.0.1"` |
| Guardrail in `coder-angular-frontend.md` | `GUARDRAIL (Unicode Regex PT-BR)` block present |
| One-liner in principles list | `Regex PT-BR Unicode-safe` line present |
| Version bump frontend | Both `version` occurrences updated to `1.0.1` |
| PT-BR Validation Patterns section | `## PT-BR Validation Patterns` heading present |
| No forbidden patterns outside notes | Scenario D returns 0 matches |
