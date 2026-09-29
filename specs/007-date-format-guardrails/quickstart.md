# Quickstart: Validating Date Format Guardrails

**Feature**: `007-date-format-guardrails`
**Date**: 2026-07-07

---

## Prerequisites

- Access to the `src/modules/ava-fabric-agents/tech-stack/agents/` directory
- Access to `src/shared/data/patterns/angular/`
- `CHANGELOG.md` at repo root

---

## Validation Scenarios

### Scenario A — G10 present in `coder-dotnet-backend.md`

**Command**:
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "G10|DateTimeKind\.Utc|ISO 8601" | Select-Object -First 5
```

**Expected output**: At least 3 matches including `G10`, `DateTimeKind.Utc`, and `ISO 8601`.

**Version check**:
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern 'version:' | Select-Object -First 1
```
Expected: `version: "1.1.0"`

---

### Scenario B — G-DATE present in `coder-angular-frontend.md`

**Command**:
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md" `
  -Pattern "G-DATE|LOCALE_ID|MAT_DATE_LOCALE|dd/MM/yyyy" | Select-Object -First 5
```

**Expected output**: At least 4 matches.

**Frontmatter duplicate check**:
```powershell
$lines = Get-Content "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md"
$versionLines = $lines | Select-String "^version:" | Measure-Object
# Expected: Count = 1 (no duplicate)
Write-Host "version: lines = $($versionLines.Count)"
```
Expected: `version: lines = 1`

**Version check**:
```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md" `
  -Pattern 'version:' | Select-Object -First 1
```
Expected: `version: "1.1.0"`

---

### Scenario C — "Padrões de Data e Hora" in `angular-patterns-reference.md`

**Command**:
```powershell
Select-String -Path "src\shared\data\patterns\angular\angular-patterns-reference.md" `
  -Pattern "Padrões de Data|dd/MM/yyyy|ISO 8601|MAT_DATE_LOCALE" | Select-Object -First 5
```

**Expected output**: At least 4 matches including all three pattern names.

---

### Scenario D — CHANGELOG records both version bumps

**Command**:
```powershell
Select-String -Path "CHANGELOG.md" -Pattern "coder-dotnet-backend.*1\.1\.0|coder-angular-frontend.*1\.1\.0"
```

**Expected output**: Two matches (one for each agent).

---

## End-to-End Contract Verification

The full date contract can be summarized as:

```
Backend DTO:          DateTime.UtcNow  →  "2026-07-07T00:00:00Z"  (ISO 8601, G10)
Angular app.config:   LOCALE_ID='pt-BR' + registerLocaleData(localePtBr)  (G-DATE)
Angular template:     {{ item.dueDate | date:'dd/MM/yyyy' }}  →  "07/07/2026"  (G-DATE)
```

All four validation scenarios passing confirms the contract is enforced end-to-end.
