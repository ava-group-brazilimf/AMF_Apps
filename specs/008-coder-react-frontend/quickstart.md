# Quickstart: Validating coder-react-frontend v1.0.0

## Prerequisites

- Workspace: `c:\CODIGOS CAMINHO\Agentes-Fabrica\imfai-ava-fabric-apps-agents`
- Project: `projects/Meu-ERP/` (or any project with `frontend_framework: "react"`)
- No external services required — all validation is static (file existence + content inspection)

---

## CA01 — Routing Guard blocks on wrong framework

**Setup**: Temporarily set `frontend_framework: "angular"` in project-config.yaml (or use a test project).

**Trigger**: Invoke the agent with this config.

**PASS** if:
- Agent emits the routing error box with `FRAMEWORK INCOMPATÍVEL` warning
- No files are written under `outputs/tobe/source-code/frontend/`
- `AgentResult.success: false`

**Revert**: Restore `frontend_framework: "react"` before proceeding.

---

## CA02 — Required scaffolding files are generated

**Setup**: Use a project with `frontend_framework: "react"`, `pipeline_mode: "generic"`, and at least one BC.

**Trigger**: Invoke `@ava-stack-react-frontend` (or equivalent call via skill).

**PASS** if these files exist after execution:

```powershell
$base = "projects\Meu-ERP\outputs\tobe\source-code\frontend"
@("index.html","vite.config.ts","tsconfig.json","vitest.config.ts","src\main.tsx","src\App.tsx") | ForEach-Object {
  $p = Join-Path $base $_
  if (Test-Path $p) { Write-Host "✅ $_" } else { Write-Host "❌ MISSING: $_" }
}
```

---

## CA03 — Feature structure per BC

**PASS** if for each BC in `bounded_contexts`, the following paths exist:

```powershell
$bc = "financeiro"   # replace with actual BC name
$feat = "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\features\$bc"
@("components","hooks","stores","services","types") | ForEach-Object {
  if (Test-Path "$feat\$_") { Write-Host "✅ $bc/$_" } else { Write-Host "❌ MISSING: $bc/$_" }
}
```

---

## CA04 — Modal uses boolean isOpen + typed onClose

**PASS** if any generated `*.tsx` Modal file contains:

```powershell
Select-String -Path "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\**\*.tsx" `
  -Pattern "isOpen: boolean" -Recurse | Select-Object -First 1
```

Returns a match.

**FAIL** if `isOpen` is absent or the component manages its own open state internally with no prop.

---

## CA05 — FilterPanel applies all criteria simultaneously

**PASS** if the generated FilterPanel contains both patterns:

```powershell
Select-String -Path "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\**\*.ts" `
  -Pattern "useFilterStore|useMemo" -Recurse | Select-Object -First 3
```

Returns matches for both `useFilterStore` and `useMemo` in the same feature directory.

---

## CA06 — CRUD invalidates cache on mutation

**PASS** if any generated mutation hook contains `invalidateQueries`:

```powershell
Select-String -Path "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\**\*.ts" `
  -Pattern "invalidateQueries" -Recurse | Select-Object -First 1
```

Returns a match in a `useMutation` hook file.

---

## CA07 — Update form pre-populates via useQuery

**PASS** if any generated form component contains both `useQuery` and `reset`:

```powershell
Select-String -Path "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\**\*.tsx" `
  -Pattern "useQuery|reset\(" -Recurse | Group-Object Path | Where-Object { $_.Count -ge 2 }
```

Returns a file with both patterns.

---

## CA08 — Service layer uses openapi-typescript types

**PASS** if `api.d.ts` exists for at least one BC:

```powershell
Get-ChildItem "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\features" `
  -Filter "api.d.ts" -Recurse | Select-Object FullName
```

---

## CA09 — Security Compliance Report exists and is non-empty

```powershell
$report = "projects\Meu-ERP\outputs\tobe\docs\security\SecurityComplianceReport-Frontend.md"
if (Test-Path $report) {
  $lines = (Get-Content $report).Count
  Write-Host "✅ Report exists ($lines lines)"
} else { Write-Host "❌ MISSING" }
```

**PASS** if file exists and has > 10 lines.

---

## CA10 — Vitest spec generated alongside each component

**PASS** if every `.tsx` component file has a sibling `.spec.tsx`:

```powershell
Get-ChildItem "projects\Meu-ERP\outputs\tobe\source-code\frontend\src\features" `
  -Filter "*.tsx" -Recurse | Where-Object { $_.Name -notmatch "\.spec\." } | ForEach-Object {
  $spec = $_.FullName -replace "\.tsx$", ".spec.tsx"
  if (Test-Path $spec) { Write-Host "✅ $($_.Name)" } else { Write-Host "❌ MISSING spec for $($_.Name)" }
}
```

---

## CA11 — stub-registry.yaml updated to COMPLETE

```powershell
Select-String -Path "src\shared\data\stub-registry.yaml" `
  -Pattern "id: coder-react-frontend" -Context 0,3
```

**PASS** if the `status:` line within the `coder-react-frontend` block reads `COMPLETE` (not `STUB`).

---

## CA12 — module.yaml no longer marks react frontend as stub

```powershell
Select-String -Path "src\modules\ava-fabric-agents\tech-stack\module.yaml" `
  -Pattern "ava-stack-react-frontend" -Context 0,5
```

**PASS** if no `status: stub` line appears in the block.
