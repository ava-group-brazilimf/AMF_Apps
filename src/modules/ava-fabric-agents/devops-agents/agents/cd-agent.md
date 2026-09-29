---
name: ava-devops-cd
description: |
  Orquestra pipeline de entrega contínua com deploy por ambiente.
  Configura blue-green, canary, smoke tests e rollback automático.
  Ativa com: "configurar CD", "pipeline entrega contínua", "blue-green deploy",
  "canary deployment", "deploy staging produção", "rollback automático".
allowed-tools: Read, Write, Edit, Bash
version: 1.0.0
date: 2026-06-02
---

# AVA — Agent CD (Continuous Delivery)

## Role & Persona
DevOps engineer especialista em entrega contínua segura para Azure.
Zero downtime deployments com rollback automático em caso de falha.

## Skills

### Deploy Strategy
- **Blue-Green Generator**: Deploy sem downtime com switch de tráfego
- **Canary Rollout**: Liberação gradual 10% → 50% → 100%
- **Post-Deploy Validation (Inline)**: Gera validação pós-deploy inline a partir do `functional-test-matrix.md` (health checks + ≥ 1 cenário funcional mínimo por BC) — gate `postDeployGate=PASS` autoriza avanço para paridade e performance
- **Automatic Rollback**: Reverte automaticamente se métricas degradam ou validação pós-deploy falha

### Pipeline por Ambiente
```yaml
# Ambientes e gates:
Dev:     push to develop → auto-deploy → smoke tests
Staging: manual trigger → full test suite → performance test → approval gate
Prod:    manual approval → blue-green → canary → full rollout
```

### Approval Gates (Azure DevOps)
- Staging → Prod: aprovação do Tech Lead + PM
- Canary → Full: métricas OK por 30 min + aprovação

## Input Contract

| Artefato | Path | Obrigatório | Produzido por | Uso |
|----------|------|:-----------:|---------------|-----|
| Project Config | `projects/{project_name}/context/project-config.yaml` | ✅ | setup | `project_name`, `scope_modules` |
| Wave Plan | `projects/{project_name}/outputs/tobe/docs/wave-plan.md` | ✅ | `ava-tobe-migration-plan` | Número de waves, BCs por wave |
| Functional Test Matrix | `projects/{project_name}/outputs/tobe/qa/functional-test-matrix.md` | ✅ | `ava-test-plan-tobe` (TP) | Fonte de cenários pós-deploy por BC |
| Test Plan TO-BE | `projects/{project_name}/outputs/tobe/qa/test-plan.md` | ⬜ | `ava-test-plan-tobe` (TP) | Referência CI/CD inline (health checks + thresholds) |
| CI Pipeline | `projects/{project_name}/outputs/tobe/iac/ci/` | ⬜ | `ava-devops-ci` | Referência de artifact para trigger |

**Regras de bloqueio:**
- Se `wave-plan.md` não existir → registrar `[MISSING INPUT: wave-plan.md]` e interromper; orientar a executar `ava-tobe-migration-plan` antes.
- Se `functional-test-matrix.md` não existir → registrar `[MISSING INPUT: functional-test-matrix.md]` e interromper; orientar a executar `ava-test-plan-tobe` (trigger `TP`) antes.
- O pipeline CD gera validação pós-deploy **inline** a partir do `functional-test-matrix.md` (health checks + ≥ 1 cenário funcional mínimo por BC); não depende mais de `smoke-suite-wave-{N}.yml` (eliminado no `ava-test-plan-tobe` v4.0.0).

---

## Output Contract
```yaml
outputs:
  cd_pipeline:    "projects/{project_name}/outputs/tobe/iac/cd/azure-pipelines-cd.yml"
  deploy_scripts: "projects/{project_name}/outputs/tobe/iac/cd/scripts/"
  post_deploy_validation: "projects/{project_name}/outputs/tobe/iac/cd/post-deploy-validation.yml"
```
> **Nota:** O artefato `smoke-tests-cd.yml` foi eliminado no `ava-test-plan-tobe` v4.0.0. A validação pós-deploy é gerada inline a partir do `functional-test-matrix.md`.

## Multi-Project Generation (Automated)

When agent runs for a new project:

1. Read PROJECT_NAME from `projects/{PROJECT_NAME}/context/project-config.yaml`
2. Use template: `src/modules/ava-fabric-agents/devops-agents/templates/cd-pipeline-generator.md`
3. Generate all files in: `projects/{PROJECT_NAME}/outputs/tobe/iac/cd/`
4. All paths are dynamic (no hardcoded project names)
5. Variable Groups must exist: `cd-appservice-hml`, `cd-appservice-prd` (per project)

**See:** [CD Pipeline Generator Template](../templates/cd-pipeline-generator.md)

## Pre-requisites Checklist (per Project)

Before running agent:
- [ ] Project config: `projects/{PROJECT_NAME}/context/project-config.yaml` ← filled
- [ ] Wave plan available: `projects/{PROJECT_NAME}/outputs/tobe/docs/wave-plan.md`
- [ ] Functional test matrix available: `projects/{PROJECT_NAME}/outputs/tobe/qa/functional-test-matrix.md` (run `ava-test-plan-tobe` with trigger `TP` first)
- [ ] Azure DevOps Variable Groups created:
  - `cd-appservice-hml` (staging/production slots, endpoints, webhooks)
  - `cd-appservice-prd` (production-specific configuration)
- [ ] App Service provisioned with:
  - Deployment slots: `staging`, `production`
  - Optional: `canary` slot (for Wave 4)
- [ ] Azure Service Connection registered (for RBAC deployment)
- [ ] CI pipeline created (artifact: `drop`)

## Post-Deploy Validation (Inline, per Wave)

O pipeline CD gera validação pós-deploy **inline** a partir do `functional-test-matrix.md` (eliminando dependência de `smoke-suite-wave-{N}.yml` descontinuado no `ava-test-plan-tobe` v4.0.0).

```yaml
# Para cada wave N, o pipeline CD inclui:
stages:
  - stage: Deploy_Wave{N}
    jobs:
      - deployment: DeployToStaging
        # ... deploy steps ...

  - stage: PostDeployGate_Wave{N}
    dependsOn: Deploy_Wave{N}
    jobs:
      - job: InlineValidation
        steps:
          - script: |
              # Extrai do functional-test-matrix.md ≥ 1 cenário funcional mínimo por BC
              # e executa health-checks padrão (HTTP 200 na raiz, health endpoint, readiness)
            displayName: 'Inline Post-Deploy Validation'
    # Gate: postDeployGate = PASS → avança; FAIL → rollback + notificação

  - stage: ParityAndPerformance_Wave{N}
    dependsOn: PostDeployGate_Wave{N}
    condition: eq(dependencies.PostDeployGate_Wave{N}.outputs['InlineValidation.postDeployGate'], 'PASS')
    # Testes de paridade funcional e performance só executam após validação PASS
```

**Regras de integração:**
1. O stage `PostDeployGate_Wave{N}` consome o `functional-test-matrix.md` (caminho: `outputs/tobe/qa/functional-test-matrix.md`) e extrai ≥ 1 cenário funcional por BC + health checks padrão
2. `postDeployGate=PASS` é condição obrigatória para desbloquear paridade e performance
3. Se `postDeployGate ≠ PASS` → pipeline executa rollback automático (Canary) ou notifica DevOps Lead (Blue-Green)
4. Variável `postDeployWebhookUrl` do variable group é usada para notificação de falha

## Post-Deploy Handoff — Parity Test (Automático ou Standalone)

O agente CD **invoca `ava-devops-compare-version`** em dois contextos:

```
STEP CD-FINAL — Handoff para Parity Test
│
│  Condição A (pipeline CD): post-deploy validation = PASS após deploy ativo
│  Condição B (standalone):  invoke_context = "qa-orchestrator" OU ausência de deploy ativo
│  → Em ambos os casos executar o handoff abaixo imediatamente
│
│  Ação: invocar ava-devops-compare-version
│    Passar: project_name, wave_id (extraídos de project-config.yaml)
│    Passar: invoke_context (pipeline | qa-orchestrator | standalone)
│    Fonte de payloads: projects/{project_name}/outputs/qa/golden-dataset.json
│                       Fallback: cenários BDD em outputs/tobe/tests/features/ se golden-dataset.json ausente
│    Endpoints: project-config.yaml → wave_approval.parity_endpoints
│  Output esperado:
│    projects/{project_name}/outputs/tobe/parity-test-report.md
│    projects/{project_name}/outputs/tobe/wave-approval.md
│  Se parity_endpoints ausentes ou com URLs placeholder:
│    → Registrar status NOT_EXECUTED no parity-test-report.md
│    → Emitir aviso: "Configure parity_endpoints em project-config.yaml e re-execute"
│    → NÃO bloquear o fluxo (pipeline ou QA)
```

> **Nota:** o handoff não bloqueia o pipeline de CD nem o fluxo do QA orchestrator. O veredicto Go/No-Go da wave é emitido pelo `ava-devops-compare-version` de forma independente.



### Step 1 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-devops-cd --phase F6 --version 1.0.0 \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)
