# Quickstart — Validação do ava-prototype v1.1.0

Guia de validação end-to-end para confirmar que a revisão do agente funciona corretamente.

---

## Pré-requisitos

1. Projeto de teste configurado em `projects/Test-PBI366/` (ou qualquer projeto com artefatos F2 prontos)
2. Artefatos F2 presentes:
   - `outputs/tobe/docs/design-system.md` ← obrigatório
   - `outputs/tobe/docs/user-journeys.md` ← obrigatório
   - `outputs/tobe/docs/bounded-context-map.md` ← obrigatório
   - `outputs/tobe/docs/api-map.md` ← opcional (testar com e sem)
   - `outputs/asis/docs/functional-requirements.md` ← opcional

---

## Cenário 1: Execução nominal (CA01 + CA02)

### Setup

Verifique que os artefatos obrigatórios existem:

```bash
# Ajustar PROJECT_NAME conforme necessário
ls projects/Test-PBI366/outputs/tobe/docs/design-system.md
ls projects/Test-PBI366/outputs/tobe/docs/user-journeys.md
ls projects/Test-PBI366/outputs/tobe/docs/bounded-context-map.md
```

### Execução

No GitHub Copilot Chat (VS Code):

```
@ava-prototype
```

Quando solicitado o nome do projeto, informar: `Test-PBI366`

### Resultado Esperado

1. **Pre-Flight Check**: todos os inputs obrigatórios aparecem como [✅]
2. **Outputs gerados**:
   ```
   projects/Test-PBI366/outputs/tobe/prototype/index.html      ← existe e abre no browser
   projects/Test-PBI366/outputs/tobe/prototype/screen-list.md  ← lista todas as telas
   projects/Test-PBI366/outputs/tobe/prototype/demo-script.md  ← tem seção "Cenários de Erro (CA03)"
   projects/Test-PBI366/outputs/tobe/prototype/figma-spec.md   ← tem tabela H1-H10
   ```
3. **Gate result** emitido antes de COMPLETED com `status: "PASS"`
4. **Campos v1.1.0 presentes no gate result**:
   - `ux_heuristics_applied` com ao menos `["H1","H4","H6","H9"]`
   - `form_validation_applied: true` (se user-journeys.md tem formulários)
   - `error_pattern_applied: true`

### Validação Manual do index.html

Abrir `index.html` no browser e verificar:

- [ ] Sidebar com links por Bounded Context
- [ ] Breadcrumb visível no header de cada tela (H1)
- [ ] Labels visíveis em todos os campos de formulário (H6)
- [ ] Botão "Cancelar" presente em todos os formulários (H3)
- [ ] CSS custom properties (`--color-primary`, etc.) declaradas no `<style>`

---

## Cenário 2: Fallback sem api-map.md (CA02-EDGE)

### Setup

Remover temporariamente o api-map.md (ou usar projeto sem ele):

```bash
# Testar em projeto que NÃO tem api-map.md
```

### Resultado Esperado

- Pre-Flight Check mostra `api-map.md` como [⚠️ ausente — fallback ativo]
- `screen-list.md` inclui coluna `api_source` com valor `openapi-derived`
- `prototype_gate_result.missing_inputs` inclui `"api-map.md"`
- `prototype_gate_result.status` = `"PASS"` (não é bloqueante)
- `prototype_gate_result.api_source` = `"openapi-derived"`

---

## Cenário 3: Validação de formulário e mensagens de erro (CA03)

### Validação no Browser

Abrir o `index.html` gerado e navegar até uma tela com formulário:

**Teste de campo obrigatório:**

1. Deixar campo obrigatório em branco
2. Clicar no botão de submissão
3. Esperado: borda vermelha no campo + texto de erro abaixo do campo + scroll automático até o campo

**Teste de formato inválido:**

1. Preencher campo de email com `"nao-e-email"`
2. Clicar em submeter
3. Esperado: mensagem de formato inválido junto ao campo + `aria-invalid="true"` no elemento (verificar com DevTools)

**Teste de sucesso:**

1. Preencher todos os campos corretamente
2. Submeter o formulário
3. Esperado: toast verde com mensagem de sucesso + formulário retorna ao estado inicial

**Teste de erro do sistema:**

1. Clicar no botão "Simular Erro"
2. Esperado: modal com título "Ocorreu um erro inesperado" + mensagem amigável + identificador de correlação no formato `ERR-YYYYMMDD-NNN`

---

## Cenário 4: Pre-Flight bloqueado por ausência de artefato obrigatório

### Setup

Usar projeto sem `user-journeys.md`.

### Resultado Esperado

- Pre-Flight Check mostra `user-journeys.md` como [❌ MISSING]
- `DECISION: BLOCKED`
- Nenhum arquivo de output é gerado
- Agente informa qual agente deve rodar primeiro (`ava-tobe-user-journeys`)

---

## Referências

- Contrato de saída: [contracts/output-contract.md](contracts/output-contract.md)
- Modelo de dados: [data-model.md](data-model.md)
- Pesquisa técnica: [research.md](research.md)
- Spec completa: [spec.md](spec.md)

# Quickstart Validation Guide: ava-stack-vue-frontend

**Feature**: `009-vue-frontend-agent`
**Date**: 2026-07-13
**Purpose**: Prove the implementation works end-to-end without requiring full CI

---

## Prerequisites

1. A project exists at `projects/{project_name}/` with:
   - `context/project-config.yaml` containing `tobe_stack.frontend_framework: "vue"` and `pipeline_mode: "generic"`
   - `context/shared-context.md` (may be empty or AS-IS COMPLETE)
2. `docs/architecture/ConfigStackDotNet.yaml` exists with `tobe_stack.frontend_version: "3"`
3. `stub-registry.yaml` updated: `id: coder-vue-frontend → status: COMPLETE`
4. `orchestrator-stack.md` routing table: `vue | ava-stack-vue-frontend | ✅`

> **Project to use for validation**: `projects/Meu-ERP/` (already exists in workspace)

---

## §1 — Routing Table Verification

**Goal**: Confirm `orchestrator-stack.md` no longer shows `🚧 STUB` for vue.

```bash
# From repo root:
grep -A2 '"vue"' src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md
```

**Expected output** — must NOT contain `🚧 STUB`:

```
| `vue` | `ava-stack-vue-frontend` | ✅ |
```

---

## §2 — Stub Registry Verification

**Goal**: Confirm `coder-vue-frontend` is marked COMPLETE.

```powershell
# From repo root (PowerShell):
Select-String -Path "src/shared/data/stub-registry.yaml" -Pattern "coder-vue-frontend" -Context 0,5
```

**Expected**:

```yaml
- id: coder-vue-frontend
  status: COMPLETE
  owner: "ava-stack-vue-frontend@1.0.0"
```

---

## §3 — SKILL.md Exists and Delegates Correctly

**Goal**: Confirm SKILL.md was created and references the correct agent.

```powershell
Test-Path ".github/skills/ava-stack-vue-frontend/SKILL.md"   # must be True
Select-String -Path ".github/skills/ava-stack-vue-frontend/SKILL.md" -Pattern "coder-vue-frontend.md"
```

**Expected**: `Test-Path` returns `True`; grep shows the agent file reference.

---

## §4 — Agent Frontmatter Validation

**Goal**: Confirm the agent `.md` has correct YAML frontmatter (no STUB markers).

```powershell
# Read first 15 lines of the agent file
Get-Content "src/modules/ava-fabric-agents/tech-stack/agents/coder-vue-frontend.md" | Select-Object -First 15
```

**Expected**:

- `version: "1.0.0"` (not `0.1.0-stub`)
- No `🚧 STUB` text in frontmatter or body header
- `name: ava-stack-vue-frontend` present

---

## §5 — Module YAML Status Field Removed

**Goal**: Confirm `module.yaml` no longer has `status: stub` for `ava-stack-vue-frontend`.

```powershell
Select-String -Path "src/modules/ava-fabric-agents/tech-stack/module.yaml" -Pattern "vue" -Context 0,4
```

**Expected**: Entry for `ava-stack-vue-frontend` has NO `status: stub` line.

---

## §6 — Agent Invocation: Nominal Path (manual LLM test)

**Goal**: Confirm the agent produces `implementation.status: COMPLETED` when invoked against `Meu-ERP`.

**Setup**: Ensure `projects/Meu-ERP/context/project-config.yaml` contains:

```yaml
project_name: "Meu-ERP"
pipeline_mode: "generic"
tobe_stack:
  frontend_framework: "vue"
  frontend_version: "3"
auth:
  provider: "azure-ad"
trace_id: "test-trace-001"
```

**Invoke**: In VS Code Copilot Chat:

```
@ava-stack-vue-frontend gerar frontend Vue para projeto Meu-ERP
```

**Expected handoff block in response**:

```yaml
implementation.status: COMPLETED
build: PENDING
security_compliance: COMPLIANT | PARTIAL | NON_COMPLIANT | SKIPPED
trace_id: test-trace-001
```

**Must NOT appear in response**:

- `implementation.status: STUB`
- `⚠️ STUB AGENT`
- `Status  : NOT IMPLEMENTED`

---

## §7 — Agent Invocation: build-cycle WARN+fallback (manual LLM test)

**Goal**: Confirm WARN+fallback behaviour when `pipeline_mode == "build-cycle"`.

**Setup**: Temporarily set in `project-config.yaml`:

```yaml
pipeline_mode: "build-cycle"
```

**Invoke**:

```
@ava-stack-vue-frontend gerar frontend Vue para projeto Meu-ERP
```

**Expected**:

- Warning message containing: `build-cycle Vue não implementado — continuando em modo generic`
- `implementation.status: COMPLETED` (not BLOCKED)
- `build_cycle_fallback: true` in handoff

**Must NOT appear**: Hard stop / error blocking the pipeline.

---

## §8 — Output Contract Verification (after §6)

**Goal**: Confirm all mandatory output files exist.

```powershell
# After running agent in §6:
$base = "projects/Meu-ERP/outputs/tobe"
Test-Path "$base/source-code/frontend/package.json"
Test-Path "$base/source-code/frontend/src/main.ts"
Test-Path "$base/source-code/frontend/src/router/index.ts"
Test-Path "$base/source-code/frontend/implementation-status.json"
Test-Path "$base/docs/delivery/ImplementationNotes.md"
Test-Path "$base/docs/delivery/ChangedScreens.md"
Test-Path "$base/docs/security/SecurityComplianceReport-Frontend.md"
```

**Expected**: All `Test-Path` calls return `True`.

---

## §9 — implementation-status.json Schema Check

**Goal**: Verify the JSON output matches the contract schema.

```powershell
$json = Get-Content "projects/Meu-ERP/outputs/tobe/source-code/frontend/implementation-status.json" | ConvertFrom-Json
$json.agent                       # must be "ava-stack-vue-frontend"
$json.implementation.status       # must be "COMPLETED"
$json.outputs_generated.Count     # must be >= 1
$json.trace_id                    # must match input trace_id
```

---

## §10 — Regression Check

**Goal**: Confirm Angular and React agents are unaffected.

```powershell
# Angular SKILL.md still delegates to coder-angular-frontend.md
Select-String ".github/skills/ava-stack-angular-frontend/SKILL.md" -Pattern "coder-angular-frontend.md"

# React coder still has version 1.0.0 (not regressed)
(Get-Content "src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md" | Select-Object -First 6) -match "1\.0\.0"
```

**Expected**: Both checks pass — no changes to Angular or React files.
