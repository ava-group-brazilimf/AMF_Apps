# Quickstart: Validate Clean Architecture & SOLID Guardrail (spec 007)

**Date**: 2026-07-07
**Spec**: `specs/007-dotnet-clean-arch-solid-guardrail/spec.md`

---

## Prerequisites

- Workspace: `c:\CODIGOS CAMINHO\Agentes-Fabrica\imfai-ava-fabric-apps-agents`
- PowerShell 5.1+ (or Git Bash for grep commands)
- Target file: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

---

## Validation 1 — Version Bumped

Confirms frontmatter version is `1.0.1`:

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern 'version: "1\.0\.1"'
```

**Expected**: 1 match on line 6.

---

## Validation 2 — G10 Section Present

Confirms the new guardrail heading was inserted:

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "### G10"
```

**Expected**: 1 match.

---

## Validation 3 — All 4 Anti-Pattern Pairs Present

Confirms all four ERRADO/CORRETO pairs are documented:

```powershell
$f = "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md"
$content = Get-Content $f -Raw

# Must find at least 4 ERRADO blocks and 4 CORRETO blocks in the G10 section
$errado = ([regex]::Matches($content, "ERRADO")).Count
$correto = ([regex]::Matches($content, "CORRETO")).Count

"ERRADO blocks: $errado (expected >= 4)"
"CORRETO blocks: $correto (expected >= 4)"
```

**Expected**: `ERRADO blocks: ≥ 4`, `CORRETO blocks: ≥ 4`.

---

## Validation 4 — Post-Generation Verification Section Present

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "Verificação Pós-Geração"
```

**Expected**: 1 match.

---

## Validation 5 — Grep Commands Documented

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "new \[A-Za-z\]\*Repository"
```

**Expected**: 1 match (inside the post-generation verification section).

---

## Validation 6 — Rule 7 Added to Regras Invioláveis

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "ISender \(MediatR\)"
```

**Expected**: ≥ 1 match (once in Regras Invioláveis rule 7, once in G10).

---

## Validation 7 — Section Order Correct

Confirms the three new/modified sections appear in the correct order:

```powershell
$f = "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md"
$lines = Get-Content $f
$g10Line    = ($lines | Select-String "### G10").LineNumber
$caTemplate = ($lines | Select-String "## Clean Architecture Template").LineNumber
$verGate    = ($lines | Select-String "## Verificação Pós-Geração").LineNumber
$secGate    = ($lines | Select-String "## Security Compliance Review Gate").LineNumber

"G10 at line $g10Line (must be < Clean Architecture Template at $caTemplate)"
"Verificação Pós-Geração at $verGate (must be < Security Compliance at $secGate)"

if ($g10Line -lt $caTemplate -and $verGate -lt $secGate) {
  "✅ Section order CORRECT"
} else {
  "❌ Section order WRONG — check insertion points"
}
```

**Expected**: `✅ Section order CORRECT`.

---

## Validation 8 — No Regression in Existing Guardrails

Confirms G1–G9 headings are still present:

```powershell
1..9 | ForEach-Object {
  $match = Select-String `
    -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
    -Pattern "### G$_"
  if ($match) { "✅ G$_ present" } else { "❌ G$_ MISSING" }
}
```

**Expected**: All 9 lines show `✅ G{N} present`.

---

## End-to-End Scenario (manual)

To verify AC #4 (Sophia project zero violations), run the post-generation grep
after invoking `ava-stack-dotnet-backend` on the Sophia project:

```bash
# In Git Bash or WSL, from workspace root:
grep -rn "new [A-Za-z]*Repository" \
  "projects/sophia/outputs/tobe/source-code/" \
  --include="*.cs" | grep -v "/Infrastructure/"

grep -rn "\bDbContext\b" \
  "projects/sophia/outputs/tobe/source-code/" \
  --include="*.cs" | grep -v "/Infrastructure/" | grep -v "\.Tests/"
```

**Expected**: Both commands produce zero output lines.
