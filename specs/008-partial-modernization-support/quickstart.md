# Quickstart: Partial Modernization Support — Validation Guide

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-09

---

## Prerequisites

- Workspace: `c:\CODIGOS CAMINHO\Agentes-Fabrica\imfai-ava-fabric-apps-agents`
- Feature branch `008-partial-modernization-support` checked out
- A test project under `projects/` (e.g., `projects/Meu-ERP/`)

---

## Scenario A — Full backward-compatibility (Scenario 4 from spec)

**Validates**: existing configs without `modernization_scope` work unchanged.

1. Ensure `projects/Meu-ERP/context/project-config.yaml` has **no** `modernization_scope` field.
2. Trigger `@ava-master-orchestrator | FP`
3. **Expected**: no step 0.5 in output, no BC filtering in F3, pipeline runs identically to pre-feature.

---

## Scenario B — Partial mode HARD STOP (Scenario 2 from spec)

**Validates**: empty `target_modules` blocks the pipeline with a clear error.

1. Add to `projects/Meu-ERP/context/project-config.yaml`:
   ```yaml
   modernization_scope: "partial"
   target_modules: []
   ```
2. Trigger `@ava-master-orchestrator | FP`
3. **Expected output** (pre-flight block):
   ```
   ╔══════════════════════════════════════════════════════════════════════╗
   ║  PARTIAL MODERNIZATION MODE — PRE-FLIGHT                            ║
   ╠══════════════════════════════════════════════════════════════════════╣
   ║  modernization_scope: partial                                       ║
   ║  target_modules: []                                                 ║
   ╠══════════════════════════════════════════════════════════════════════╣
   ║  DECISION: BLOCKED                                                  ║
   ║  Reason: modernization_scope=partial requer target_modules não-vazio║
   ╚══════════════════════════════════════════════════════════════════════╝
   ```
4. **Expected**: no F1 agent dispatched, no output files created.

---

## Scenario C — Partial mode nominal (Scenario 1 from spec)

**Validates**: coexistence-strategy dispatched at step 0.5; F3 skips non-listed BCs.

1. Add to `projects/Meu-ERP/context/project-config.yaml`:
   ```yaml
   modernization_scope: "partial"
   target_modules: ["financeiro"]
   ```
2. Trigger `@ava-master-orchestrator | FP`
3. **Expected at step 0.5**:
   - `@ava-tobe-coexistence-strategy` dispatched
   - `projects/Meu-ERP/outputs/tobe/docs/coexistence-strategy.md` created before F1 starts
4. **Expected at F3**:
   - Stack-orchestrator logs: `⏭ BC 'rh' fora de target_modules — ignorado.`
   - Only `financeiro` BC receives codegen dispatch.

---

## Scenario D — Full scope with non-empty target_modules (Scenario 3 from spec)

**Validates**: `target_modules` is silently ignored when `scope=full`.

1. Add to `projects/Meu-ERP/context/project-config.yaml`:
   ```yaml
   modernization_scope: "full"
   target_modules: ["financeiro"]
   ```
2. Trigger `@ava-master-orchestrator | FP`
3. **Expected**: WARN message `"target_modules ignorado: modernization_scope=full processa todos os BCs."` 
   then pipeline proceeds normally with no step 0.5 and no BC filtering.

---

## Scenario E — project-config.yaml template validation

**Validates**: new fields present and documented in template.

```powershell
$cfg = Get-Content "projects/_template/context/project-config.yaml" -Raw
$cfg -match "modernization_scope" | Should -BeTrue
$cfg -match "target_modules"       | Should -BeTrue
```

---

## Scenario F — Documentation present

**Validates**: guide section and README link in place.

```powershell
Select-String -Path "docs/full-pipeline-guide.md" -Pattern "Strangler Fig" | Should -Not -BeNullOrEmpty
Select-String -Path "README.md" -Pattern "moderniza.*parcial|partial.*moderniz" | Should -Not -BeNullOrEmpty
```

---

## Scenario G — CHANGELOG entries present

```powershell
Select-String -Path "CHANGELOG.md" -Pattern "1\.3\.0" | Should -Not -BeNullOrEmpty
Select-String -Path "CHANGELOG.md" -Pattern "1\.8\.0" | Should -Not -BeNullOrEmpty
```
