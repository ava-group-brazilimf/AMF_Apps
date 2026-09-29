# Quickstart Validation Guide: Language Normalization Guardrail (#2304)

**Branch**: `007-api-language-guardrail`
**Date**: 2026-07-07

---

## Prerequisites

- Workspace cloned: `c:\CODIGOS CAMINHO\Agentes-Fabrica\imfai-ava-fabric-apps-agents`
- At least one project with a `bounded-context-map.md` that contains PT-BR Command/Query names (e.g., `Meu-ERP`)

---

## How to Validate the Changes

This feature modifies two LLM prompt (`.md`) agent files — there is no build step. Validation is done by:
1. Grepping for the expected sections/rules in the modified files
2. Performing a manual spot-check of agent execution against a sample input

---

## Validation 1 — Guardrail section exists in openapi-spec-tobe.md (Task #2305)

```powershell
# Check that the guardrail section is present
Select-String -Path "src\modules\ava-fabric-agents\tobe-architecture\agents\openapi-spec-tobe.md" `
  -Pattern "Guardrail de Idioma" -CaseSensitive

# Expected output: one match showing the section header
# If no match: the guardrail section was not added

# Check that the transliteration table contains at least 10 pairs
$matches = Select-String -Path "src\modules\ava-fabric-agents\tobe-architecture\agents\openapi-spec-tobe.md" `
  -Pattern "^\| [a-z]+ \| [a-z]+" 
Write-Host "Transliteration pairs found: $($matches.Count)"
# Expected: >= 10 (target: 25)

# Check version was added
Select-String -Path "src\modules\ava-fabric-agents\tobe-architecture\agents\openapi-spec-tobe.md" `
  -Pattern "^version:" -CaseSensitive
# Expected: version: "1.1.0"
```

---

## Validation 2 — Transliteration table is self-consistent (Task #2306)

```powershell
# Verify [LANG-NORM] annotation convention is documented
Select-String -Path "src\modules\ava-fabric-agents\tobe-architecture\agents\openapi-spec-tobe.md" `
  -Pattern "\[LANG-NORM\]"
# Expected: at least one line documenting the annotation format

# Verify [NEEDS TRANSLATION] fallback is documented
Select-String -Path "src\modules\ava-fabric-agents\tobe-architecture\agents\openapi-spec-tobe.md" `
  -Pattern "\[NEEDS TRANSLATION"
# Expected: at least one line showing the fallback placeholder syntax
```

---

## Validation 3 — G10 guardrail exists in coder-dotnet-backend.md (Task #2307)

```powershell
# Check G10 is present
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "### G10" -CaseSensitive
# Expected: one match

# Check G10 mentions XML doc exemption
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "XML|summary|param" | Where-Object { $_.LineNumber -gt 193 } | Select-Object -First 5
# Expected: lines near G10 mention XML docs exemption

# Check G10 cross-references openapi-spec-tobe.md
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "openapi-spec-tobe" | Where-Object { $_.LineNumber -gt 193 }
# Expected: at least one match after the G9 section

# Check version was bumped
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "^version:" -CaseSensitive
# Expected: version: "1.1.0"

# Check G1-G9 reference was updated to G1-G10
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" `
  -Pattern "G1-G10"
# Expected: one match (the routing guard section)
```

---

## Validation 4 — No PT-BR tokens remain in generated output (Scenario 1 spot-check)

> Manual validation against Meu-ERP project (if it has a bounded-context-map.md)

```powershell
# Check if Meu-ERP has a bounded-context-map
Test-Path "projects\Meu-ERP\outputs\tobe\docs\bounded-context-map.md"

# If exists: spot-check for PT-BR Command names
Select-String -Path "projects\Meu-ERP\outputs\tobe\docs\bounded-context-map.md" `
  -Pattern "Command|Query" | Select-Object -First 10
# Then manually verify the openapi spec uses English paths for those commands
```

---

## Expected Outcomes After All Tasks Complete

| Check | Expected Result |
|---|---|
| `openapi-spec-tobe.md` has `version: "1.1.0"` | ✅ |
| `openapi-spec-tobe.md` has transliteration table with ≥ 10 pairs | ✅ |
| `openapi-spec-tobe.md` documents `[LANG-NORM]` annotation | ✅ |
| `openapi-spec-tobe.md` documents `[NEEDS TRANSLATION]` fallback | ✅ |
| `coder-dotnet-backend.md` has `version: "1.1.0"` | ✅ |
| `coder-dotnet-backend.md` has `### G10` section | ✅ |
| G10 explicitly exempts XML doc tags | ✅ |
| G10 cross-references transliteration table in openapi-spec-tobe.md | ✅ |
| Routing guard updated from `G1-G9` to `G1-G10` | ✅ |
| `CHANGELOG.md` has MINOR entry for both agents | ✅ |
