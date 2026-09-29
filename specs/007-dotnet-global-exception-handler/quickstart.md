# Quickstart Validation Guide: Guardrail G10

**Phase**: 1 (Design)
**Date**: 2026-07-07
**Feature**: `007-dotnet-global-exception-handler`

---

## Prerequisites

- Workspace: `c:\CODIGOS CAMINHO\Agentes-Fabrica\imfai-ava-fabric-apps-agents`
- File edited: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

---

## Validation Scenarios

### V1 — Version bump applied (T1)

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern 'version: "1\.0\.1"'
```

**Expected**: 1 match on the frontmatter line.

---

### V2 — Routing guard updated (T2 / SC-1)

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern "G1-G10 existentes"
```

**Expected**: 1 match.

```powershell
# Negative check — old text must be gone:
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern "G1-G9 existentes"
```

**Expected**: 0 matches.

---

### V3 — ValidationException class present in hierarchy (T3 / SC-2)

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern "class ValidationException"
```

**Expected**: 1 match (the class definition in the hierarchy code block).

---

### V4 — ValidationException in switch expression (T4 / SC-3)

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern "ValidationException\s*=>"
```

**Expected**: 1 match (inside `TryHandleAsync` switch expression).

Additionally verify ordering — ValidationException MUST appear before DomainException:

```powershell
$content = Get-Content "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" -Raw
$valIdx = $content.IndexOf("ValidationException            =>")
$domIdx = $content.IndexOf("DomainException                =>")
if ($valIdx -lt $domIdx) { "PASS: ValidationException before DomainException" }
else { "FAIL: Wrong order" }
```

**Expected**: `PASS: ValidationException before DomainException`

---

### V5 — ProblemDetails type field present (SC-4 — already satisfied, regression check)

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern 'Extensions\["type"\]'
```

**Expected**: 1 match.

---

### V6 — ErrorOr prohibition present (SC-5 — already satisfied, regression check)

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern "NUNCA.*throw.*NotFoundException"
```

**Expected**: 1 match.

---

### V7 — No G9 stale reference remains

```powershell
# Count all remaining references to G9 (should be exactly 1 — the G9 heading itself)
(Select-String -Path "src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md" `
  -Pattern "G9").Count
```

**Expected**: 1 (the `### G9` heading line only — no "G1-G9 existentes" anymore).

---

## All-in-one validation script

```powershell
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
Write-Output ""
Write-Output "Result: $pass/$($checks.Count) PASS"
if ($fail -gt 0) { Write-Output "FAIL: $fail check(s) did not pass" }
```

**Expected output**: `Result: 8/8 PASS`
