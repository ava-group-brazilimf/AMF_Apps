---
checklist_id: wave-gonogo
version: "1.0.0"
description: |
  Checklist de critérios Go/No-Go para aprovação de wave.
  Todos os critérios obrigatórios devem ser atendidos para veredicto GO.
  Thresholds são configuráveis via project-config.yaml.
applies_to: ava-devops-compare-version
---

# Checklist Go/No-Go — Aprovação de Wave

## Instruções de Uso

1. Este checklist é preenchido automaticamente pelo agente `ava-devops-compare-version`
2. Thresholds são lidos de `projects/{project_name}/context/project-config.yaml`
3. Critérios marcados como **Obrigatório = ✅** bloqueiam aprovação se falharem
4. Critérios opcionais geram alerta mas não bloqueiam

---

## Seção A — Paridade Funcional

| # | Critério | Threshold | Obrigatório | Resultado | Evidência |
|---|----------|-----------|-------------|-----------|-----------|
| A1 | Paridade funcional geral ≥ threshold | `{{THRESHOLD_PARITY_PCT}}%` | ✅ | ⬜ | Link para parity-test-report |
| A2 | Zero divergências em campos de negócio obrigatórios | 0 divergências | ✅ | ⬜ | Link para field-differences.json |
| A3 | Exceções de paridade documentadas e aprovadas por SME | 100% aprovadas | ✅ | ⬜ | Link para exceções aprovadas |
| A4 | Todas as operações críticas testadas | 100% cobertas | ✅ | ⬜ | Link para resultados por operação |

---

## Seção B — Performance

| # | Critério | Threshold | Obrigatório | Resultado | Evidência |
|---|----------|-----------|-------------|-----------|-----------|
| B1 | Latência média TO-BE ≤ threshold configurado | `≤ {{THRESHOLD_LATENCY_AVG}}ms` | ✅ | ⬜ | Link para performance report |
| B2 | Latência P95 TO-BE ≤ threshold configurado | `≤ {{THRESHOLD_LATENCY_P95}}ms` | ✅ | ⬜ | Link para performance report |
| B3 | Throughput TO-BE ≥ threshold configurado | `≥ {{THRESHOLD_THROUGHPUT}} req/s` | ⬜ | ⬜ | Link para performance report |
| B4 | Error rate TO-BE ≤ threshold configurado | `≤ {{THRESHOLD_ERROR_RATE}}%` | ✅ | ⬜ | Link para performance report |
| B5 | Nenhuma regressão de performance >20% vs AS-IS | Delta ≤ 20% | ⬜ | ⬜ | Análise comparativa |

---

## Seção C — Cobertura de Testes

| # | Critério | Threshold | Obrigatório | Resultado | Evidência |
|---|----------|-----------|-------------|-----------|-----------|
| C1 | Cobertura de linha ≥ threshold | `≥ {{THRESHOLD_LINE_COV}}%` | ✅ | ⬜ | SonarQube / coverage report |
| C2 | Cobertura de branch ≥ threshold | `≥ {{THRESHOLD_BRANCH_COV}}%` | ⬜ | ⬜ | SonarQube / coverage report |
| C3 | Todos os cenários BDD da wave executados | 100% | ✅ | ⬜ | Test execution report |
| C4 | Smoke tests em staging: Pass | Pass | ✅ | ⬜ | CI/CD pipeline evidence |

---

## Seção D — Segurança e Vulnerabilidades

| # | Critério | Threshold | Obrigatório | Resultado | Evidência |
|---|----------|-----------|-------------|-----------|-----------|
| D1 | Zero vulnerabilidades críticas no TO-BE | 0 | ✅ | ⬜ | Security scan report |
| D2 | Vulnerabilidades altas ≤ threshold | `≤ {{THRESHOLD_VULN_HIGH}}` | ✅ | ⬜ | Security scan report |
| D3 | SonarQube Quality Gate: Pass | Pass | ✅ | ⬜ | SonarQube dashboard |
| D4 | OWASP dependency check sem bloqueadores | 0 bloqueadores | ✅ | ⬜ | Dependency report |

---

## Seção E — Completude Funcional

| # | Critério | Threshold | Obrigatório | Resultado | Evidência |
|---|----------|-----------|-------------|-----------|-----------|
| E1 | Function Points planejados 100% implementados | 100% | ✅ | ⬜ | FP tracking sheet |
| E2 | FPs cobertos por testes ≥ threshold | `≥ {{THRESHOLD_FP_COV_PCT}}%` | ✅ | ⬜ | Test-to-FP mapping |
| E3 | Nenhum requisito funcional da wave sem cobertura | 0 sem cobertura | ✅ | ⬜ | Requirements traceability |

---

## Seção F — Operacional

| # | Critério | Threshold | Obrigatório | Resultado | Evidência |
|---|----------|-----------|-------------|-----------|-----------|
| F1 | Rollback strategy documentada | Sim | ⬜ | ⬜ | Runbook link |
| F2 | Rollback testado em staging | Sim | ⬜ | ⬜ | Test evidence |
| F3 | Monitoramento/alertas configurados | Sim | ⬜ | ⬜ | Observability config |
| F4 | Feature flags configuradas (Strangler Fig) | Sim | ⬜ | ⬜ | Feature flag config |

---

## Seção G — Sign-offs

| # | Role | Obrigatório | Status | Nome | Data |
|---|------|-------------|--------|------|------|
| G1 | PM | ✅ | ⬜ Pendente | {{PM_NAME}} | — |
| G2 | Cliente/Sponsor | ✅ | ⬜ Pendente | {{CLIENT_NAME}} | — |
| G3 | Tech Lead | ⬜ | ⬜ Pendente | {{TECH_LEAD_NAME}} | — |

---

## Resumo de Decisão

```
┌─────────────────────────────────────────────────────────────┐
│  REGRA DE DECISÃO                                           │
├─────────────────────────────────────────────────────────────┤
│  GO        → Todos critérios obrigatórios (✅) atendidos    │
│               + Sign-offs PM e Cliente coletados            │
│                                                             │
│  NO-GO     → Qualquer critério obrigatório (✅) falhando   │
│               OU sign-off obrigatório ausente               │
│                                                             │
│  CONDICIONAL → Critérios obrigatórios OK mas opcionais     │
│                falhando — decisão do PM com aceite de risco │
└─────────────────────────────────────────────────────────────┘
```

| Total Obrigatórios | Atendidos | Falhando | Veredicto |
|--------------------|-----------|----------|-----------|
| {{MANDATORY_TOTAL}} | {{MANDATORY_PASS}} | {{MANDATORY_FAIL}} | **{{VERDICT}}** |

---

## Configuração de Thresholds

> Os valores abaixo devem estar em `projects/{project_name}/context/project-config.yaml`:

```yaml
wave_approval:
  thresholds:
    parity_pct: 99.5            # Paridade funcional mínima (%)
    latency_avg_ms: 500         # Latência média máxima (ms)
    latency_p95_ms: 1000        # Latência P95 máxima (ms)
    throughput_min: 100         # Throughput mínimo (req/s)
    error_rate_max_pct: 1.0     # Error rate máximo (%)
    line_coverage_pct: 80       # Cobertura de linha mínima (%)
    branch_coverage_pct: 70     # Cobertura de branch mínima (%)
    vuln_high_max: 0            # Vulnerabilidades altas máximas
    fp_coverage_pct: 95         # FPs cobertos por testes (%)
```

---

*Checklist gerado pela AVA Fabric — ava-devops-compare-version*
