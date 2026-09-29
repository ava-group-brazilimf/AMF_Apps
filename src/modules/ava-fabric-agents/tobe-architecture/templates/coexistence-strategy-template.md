---
template_id: coexistence-strategy
agent: ava-tobe-coexistence-strategy
version: "1.0.0"
date: 2026-06-08
description: "Template canônico do documento de estratégia de coexistência — schema obrigatório para coexistence-strategy.md"
---

# Coexistence Strategy Template

> **Load when**: executing Step 8 of the Execution Protocol, when generating `coexistence-strategy.md`.

```markdown
# Estratégia de Coexistência AS-IS ↔ TO-BE

| Campo | Valor |
|---|---|
| **Projeto** | {{PROJECT_NAME}} |
| **TraceID** | {{TRACE_ID}} |
| **Gerado em** | {{GENERATED_AT}} |
| **Versão do Agente** | {{AGENT_VERSION}} |
| **Architecture Style** | {{ARCHITECTURE_STYLE}} |
| **Feature Flag Provider** | {{FEATURE_FLAG_PROVIDER}} |

---

## 1. Modelo de Zonas

### Definição de Zonas

| Zona | Nome | Descrição | Roteamento |
|------|------|-----------|------------|
| **Z1** | Legacy (Host) | {{Z1_DESCRIPTION}} | Gateway roteia para legado |
| **Z2** | Migrated (Fig) | {{Z2_DESCRIPTION}} | Gateway roteia para novo serviço |
| **Z3** | Coexistence | {{Z3_DESCRIPTION}} | Gateway roteia por feature flag |

### Regras de Transição

- Estado inicial: todos os BCs em **Z1**
- Progressão obrigatória: Z1 → Z3 → Z2 (NUNCA Z1 → Z2 direto)
- Rollback permitido: Z2 → Z3 ou Z3 → Z1 via toggle de feature flag (sem deploy)
- Estado terminal: todos os BCs em **Z2** após cutover completo

### Classificação por Wave

| BC ID | BC Name | Wave | Zona em W0 | Zona em W1 | Zona em W2 | Zona em W3 | Zona em W4 |
|---|---|---|---|---|---|---|---|
| {{BC_ID}} | {{BC_NAME}} | {{WAVE}} | {{ZONE_W0}} | {{ZONE_W1}} | {{ZONE_W2}} | {{ZONE_W3}} | {{ZONE_W4}} |

> Fonte: `wave-model.json` + `bounded-context-map.md` TO-BE

---

## 2. Roteamento de Tráfego

### Gateway / Façade

{{GATEWAY_DESCRIPTION}}

### Regras de Routing por Tipo

| Tipo | Mecanismo de Roteamento | Feature Flag | Observação |
|------|------------------------|--------------|------------|
| **APIs REST** | Gateway com MigrationRouter + FeatureFlagResolver | `migration.{bc_name}.{scope}.enabled` | Roteamento por endpoint ou BC inteiro |
| **Eventos/Filas** | Dual-subscribe pattern | Feature flag para desativar consumer legado | Ambos consomem durante Z3; validação cruzada |
| **Jobs/Batch** | Dual-run com comparação de resultado | Feature flag para desativar job legado | Execução paralela com validação |

### Fronteira com CD Agent

> **Responsabilidade deste agente**: roteamento funcional (feature flags por BC, decisão de qual implementação serve o request).
> **Responsabilidade do `cd-agent.md`**: deploy de infraestrutura (blue-green, canary deploy, rollback de infra).
> As responsabilidades são distintas e complementares — NÃO se sobrepõem.

> Fonte: `architecture-blueprint.md` TO-BE

---

## 3. Catálogo de Feature Flags

### Provider: {{FEATURE_FLAG_PROVIDER}}

| Flag Name | BC | Scope | Wave Ativação | Wave Remoção | Critérios de Flip |
|---|---|---|---|---|---|
| `migration.{{BC_NAME_KEBAB}}.{{SCOPE}}.enabled` | {{BC_NAME}} | {{SCOPE}} | {{WAVE_ACTIVATION}} | {{WAVE_REMOVAL}} | {{FLIP_CRITERIA}} |

### Naming Convention

```
migration.{bc_name_kebab}.{scope}.enabled
```

- `bc_name_kebab`: nome do BC em kebab-case (ex: `accounts-payable`)
- `scope`: `all` para flag do BC inteiro, ou `{endpoint_name_kebab}` para flag granular
- Todas as flags iniciam em `enabled=false` e são ativadas conforme protocolo de graduação (§5)

> Fonte: `project-config.yaml` → `tobe_stack.feature_flags.provider`

---

## 4. Estratégia de Sincronização de Dados

> ⚠️ Esta seção define **diretivas arquiteturais** (estratégia por BC). A implementação (scripts, configs, código) é responsabilidade do Build Cycle (F3).
> Regra default: `legacy wins` durante Z3 — o legado é source of truth até graduação completa a 100%.

| BC | Direção | Mecanismo | Frequência | Conflito | Confidence |
|---|---|---|---|---|---|
| {{BC_NAME}} | {{DIRECTION}} | {{MECHANISM}} | {{FREQUENCY}} | {{CONFLICT_RULE}} | {{CONFIDENCE}} |

**Direção**: `legacy→new` · `new→legacy` · `bidirecional`
**Mecanismo**: `CDC/Change Tracking` · `batch ETL` · `event bridging`
**Frequência**: `real-time` · `near-real-time` · `scheduled`
**Conflito**: `legacy wins` (default Z3) · `new wins` (apenas pós-graduação) · `manual resolution`
**Confidence**: `HIGH` (input disponível) · `LOW` (input ausente — marcado `[A DEFINIR]`)

> Fonte: `db-analysis-report.md` + `events-pubsub-inventory.md`

---

## 5. Protocolo de Graduação

### Fases de Tráfego

| Fase | % Tráfego | Métricas | Thresholds | Duração Mínima | Ação se Falha |
|---|---|---|---|---|---|
| Shadow | 0% | Health check do novo serviço | Service UP + no critical errors | 24h | Corrigir antes de avançar |
| Canary | 10% | Error rate, latência p95, data comparison | Error rate < 0.1%, p95 ≤ AS-IS × 1.1, data comparison 100% | 48h | Rollback automático para 0% |
| Ampliação | 50% | Métricas canary + validação funcional QA | Mesmos thresholds + sign-off QA | 72h | Rollback automático para 10% |
| Full | 100% | Todos os anteriores consolidados | Critérios validados por 48h contínuas | 48h | Rollback automático para 50% |

### Rollback Automático

- **Trigger**: error rate > 1% OU latência p95 > AS-IS × 1.5
- **Ação**: flip feature flag para legacy imediatamente (sem deploy)
- **Notificação**: alerta ao Squad Owner + registro em log de graduação

### Evidência para Go/No-Go

- **F4a**: Feature flags configuradas para todos os BCs da wave ✅
- **F4c**: Critérios de graduação definidos (métricas + thresholds) ✅

---

## 6. Protocolo de Decommission

### Pré-condições

- BC em zona Z2 por no mínimo N dias (conforme rollback window do tipo de wave)
- Todas as métricas do protocolo de graduação estáveis durante o período completo

### Rollback Windows por Tipo de Wave

| Tipo de Wave | Rollback Window Default | Override |
|---|---|---|
| W1 `domain_read` | 14 dias | Configurável por BC via wave-plan |
| W2 `domain_write` | 30 dias | Configurável por BC via wave-plan |
| W3 `domain_core` | 45 dias | Configurável por BC via wave-plan |

### Checklist de Decommission por BC

- [ ] 1. Todas as feature flags do BC em `enabled=true` por ≥ rollback window
- [ ] 2. Zero rollbacks acionados no período
- [ ] 3. Data sync desativado sem erros
- [ ] 4. Legacy endpoints removidos do Gateway routing
- [ ] 5. Sign-off do Squad Owner do BC

### Ações Pós-Decommission

1. Remover feature flags do BC do provider
2. Remover ACL adapters do módulo
3. Remover data sync services do BC
4. Atualizar zona para `DECOMMISSIONED` na matrix
5. Registrar data de decommission no wave-plan

### Evidência para Go/No-Go

- **F4b**: Data sync validado (legacy vs new comparison passing) ✅
- **F4d**: Protocolo de rollback testado para BCs da wave ✅

---

## 7. Cobertura de Eventos e Filas

### Estratégia por Tipo de Componente

| Tipo | Estratégia Z3 | Validação | Critério de Desativação do Legado |
|------|---------------|-----------|-----------------------------------|
| **APIs REST** | Roteamento via Gateway com feature flag | Data comparison por request | Feature flag em 100% por ≥ rollback window |
| **Eventos/Filas** | Dual-subscribe — ambos consomem o mesmo evento | Novo sistema processa e valida contra legado | Validação OK por ≥ rollback window; legado para de consumir |
| **Jobs/Batch** | Dual-run com comparação de resultado | Comparação output do job legado vs novo | Feature flag para desativar job legado após validação |

### Cobertura por BC

| BC | Eventos Produzidos | Eventos Consumidos | Filas | Jobs | Estratégia |
|---|---|---|---|---|---|
| {{BC_NAME}} | {{EVENTS_PRODUCED}} | {{EVENTS_CONSUMED}} | {{QUEUES}} | {{JOBS}} | {{STRATEGY}} |

> ⚠️ Dual-write é TEMPORÁRIO e exclusivo de Z3 (conforme §8 Prohibited Patterns do `strangler-fig.md`).

> Fonte: `events-pubsub-inventory.md`

---

## 8. Rollback Strategy Consolidada

### Estratégia por Tipo de Componente

| Tipo | Mecanismo de Rollback | Tempo de Rollback | Automatizado? |
|---|---|---|---|
| API REST | Feature flag toggle → Gateway redireciona para legado | Imediato (< 1 min) | ✅ Sim |
| Evento/Fila | Reativar consumer legado + desativar consumer novo | < 5 min | ⚠️ Semi-automático |
| Job/Batch | Feature flag toggle → próxima execução usa job legado | Próximo ciclo de execução | ✅ Sim |
| Dados | Legacy wins (source of truth durante Z3) — sem rollback de dados necessário | N/A durante Z3 | N/A |

### Janela de Rollback por Tipo de Wave

| Tipo de Wave | Janela | Justificativa |
|---|---|---|
| W1 `domain_read` | 14 dias | Leitura apenas — risco baixo, validação rápida |
| W2 `domain_write` | 30 dias | Escrita — requer validação de integridade de dados |
| W3 `domain_core` | 45 dias | Core — máxima observação antes de decommission |

### Evidência para Go/No-Go

- **F4d**: Protocolo de rollback testado para BCs da wave ✅
```
