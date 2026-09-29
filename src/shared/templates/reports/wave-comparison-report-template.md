---
report_id: "{{REPORT_ID}}"
agent_id: "ava-devops-compare-version"
agent_name: "AVA Compare Version"
trace_id: "{{TRACE_ID}}"
generated_at: "{{TIMESTAMP}}"
project: "{{PROJECT_NAME}}"
wave_id: "{{WAVE_ID}}"
wave_name: "{{WAVE_NAME}}"
version: "{{REPORT_VERSION}}"
status: "{{STATUS}}"
verdict: "{{VERDICT}}"
---

# Relatório de Comparação AS-IS × TO-BE — Wave {{WAVE_ID}}

## Sumário Executivo

> {{EXECUTIVE_SUMMARY}}

| Campo | Valor |
|-------|-------|
| Projeto | {{PROJECT_NAME}} |
| Wave | {{WAVE_NAME}} ({{WAVE_ID}}) |
| Data de Geração | {{TIMESTAMP}} |
| Veredicto | {{VERDICT}} |
| Paridade Funcional | {{PARITY_PCT}}% |
| Risco Geral | {{RISK_LEVEL}} |

---

## 1. Escopo da Comparação

| Dimensão | AS-IS | TO-BE |
|----------|-------|-------|
| Módulos avaliados | {{ASIS_MODULES}} | {{TOBE_MODULES}} |
| Endpoints/Operações | {{ASIS_ENDPOINT_COUNT}} | {{TOBE_ENDPOINT_COUNT}} |
| Período de coleta | {{ASIS_COLLECTION_PERIOD}} | {{TOBE_COLLECTION_PERIOD}} |
| Ambiente | {{ASIS_ENVIRONMENT}} | {{TOBE_ENVIRONMENT}} |

---

## 2. Métricas Comparativas

### 2.1 Performance

| Métrica | AS-IS | TO-BE | Delta | Threshold | Status |
|---------|-------|-------|-------|-----------|--------|
| Latência média (ms) | {{ASIS_LATENCY_AVG}} | {{TOBE_LATENCY_AVG}} | {{DELTA_LATENCY_AVG}} | ≤ {{THRESHOLD_LATENCY_AVG}}ms | {{STATUS_LATENCY_AVG}} |
| Latência P95 (ms) | {{ASIS_LATENCY_P95}} | {{TOBE_LATENCY_P95}} | {{DELTA_LATENCY_P95}} | ≤ {{THRESHOLD_LATENCY_P95}}ms | {{STATUS_LATENCY_P95}} |
| Latência P99 (ms) | {{ASIS_LATENCY_P99}} | {{TOBE_LATENCY_P99}} | {{DELTA_LATENCY_P99}} | ≤ {{THRESHOLD_LATENCY_P99}}ms | {{STATUS_LATENCY_P99}} |
| Throughput (req/s) | {{ASIS_THROUGHPUT}} | {{TOBE_THROUGHPUT}} | {{DELTA_THROUGHPUT}} | ≥ {{THRESHOLD_THROUGHPUT}} | {{STATUS_THROUGHPUT}} |
| Error rate (%) | {{ASIS_ERROR_RATE}} | {{TOBE_ERROR_RATE}} | {{DELTA_ERROR_RATE}} | ≤ {{THRESHOLD_ERROR_RATE}}% | {{STATUS_ERROR_RATE}} |

### 2.2 Cobertura de Testes

| Métrica | AS-IS Baseline | TO-BE Atual | Delta | Threshold | Status |
|---------|----------------|-------------|-------|-----------|--------|
| Cobertura de linha (%) | {{ASIS_LINE_COV}} | {{TOBE_LINE_COV}} | {{DELTA_LINE_COV}} | ≥ {{THRESHOLD_LINE_COV}}% | {{STATUS_LINE_COV}} |
| Cobertura de branch (%) | {{ASIS_BRANCH_COV}} | {{TOBE_BRANCH_COV}} | {{DELTA_BRANCH_COV}} | ≥ {{THRESHOLD_BRANCH_COV}}% | {{STATUS_BRANCH_COV}} |
| Testes unitários | {{ASIS_UNIT_TESTS}} | {{TOBE_UNIT_TESTS}} | {{DELTA_UNIT_TESTS}} | ≥ {{THRESHOLD_UNIT_TESTS}} | {{STATUS_UNIT_TESTS}} |
| Testes integração | {{ASIS_INTEG_TESTS}} | {{TOBE_INTEG_TESTS}} | {{DELTA_INTEG_TESTS}} | ≥ {{THRESHOLD_INTEG_TESTS}} | {{STATUS_INTEG_TESTS}} |
| Testes E2E | {{ASIS_E2E_TESTS}} | {{TOBE_E2E_TESTS}} | {{DELTA_E2E_TESTS}} | ≥ {{THRESHOLD_E2E_TESTS}} | {{STATUS_E2E_TESTS}} |

### 2.3 Vulnerabilidades

| Severidade | AS-IS | TO-BE | Delta | Threshold | Status |
|------------|-------|-------|-------|-----------|--------|
| 🔴 Crítica | {{ASIS_VULN_CRITICAL}} | {{TOBE_VULN_CRITICAL}} | {{DELTA_VULN_CRITICAL}} | 0 | {{STATUS_VULN_CRITICAL}} |
| 🟠 Alta | {{ASIS_VULN_HIGH}} | {{TOBE_VULN_HIGH}} | {{DELTA_VULN_HIGH}} | ≤ {{THRESHOLD_VULN_HIGH}} | {{STATUS_VULN_HIGH}} |
| 🟡 Média | {{ASIS_VULN_MEDIUM}} | {{TOBE_VULN_MEDIUM}} | {{DELTA_VULN_MEDIUM}} | ≤ {{THRESHOLD_VULN_MEDIUM}} | {{STATUS_VULN_MEDIUM}} |
| 🔵 Baixa | {{ASIS_VULN_LOW}} | {{TOBE_VULN_LOW}} | {{DELTA_VULN_LOW}} | — | {{STATUS_VULN_LOW}} |
| SonarQube Gate | {{ASIS_SONAR_GATE}} | {{TOBE_SONAR_GATE}} | — | Pass | {{STATUS_SONAR_GATE}} |

### 2.4 Function Points Cobertos

| Métrica | Planejado | Implementado | Coberto por Testes | Status |
|---------|-----------|--------------|-------------------|--------|
| FPs totais da wave | {{FP_PLANNED}} | {{FP_IMPLEMENTED}} | {{FP_TESTED}} | {{STATUS_FP}} |
| % Implementação | — | {{FP_IMPL_PCT}}% | — | {{STATUS_FP_IMPL}} |
| % Cobertura funcional | — | — | {{FP_COV_PCT}}% | {{STATUS_FP_COV}} |

---

## 3. Evidências de Paridade Funcional

### 3.1 Resumo de Paridade

| Métrica | Valor | Threshold | Status |
|---------|-------|-----------|--------|
| Operações testadas | {{PARITY_OPS_TESTED}} / {{PARITY_OPS_TOTAL}} | 100% | {{STATUS_PARITY_OPS}} |
| Paridade funcional geral | {{PARITY_PCT}}% | ≥ {{THRESHOLD_PARITY_PCT}}% | {{STATUS_PARITY}} |
| Campos com divergência | {{PARITY_FIELDS_DIVERGENT}} | 0 (obrigatórios) | {{STATUS_PARITY_FIELDS}} |
| Exceções documentadas | {{PARITY_EXCEPTIONS_COUNT}} | — | — |

### 3.2 Resultados por Operação

| # | Operação | Payload | AS-IS Response | TO-BE Response | Match | Observação |
|---|----------|---------|----------------|----------------|-------|------------|
| {{ROW_NUM}} | {{OPERATION_NAME}} | {{PAYLOAD_REF}} | {{ASIS_RESPONSE_STATUS}} | {{TOBE_RESPONSE_STATUS}} | {{MATCH_STATUS}} | {{OBSERVATION}} |

### 3.3 Divergências Identificadas

| # | Operação | Campo | Valor AS-IS | Valor TO-BE | Severidade | Justificativa |
|---|----------|-------|-------------|-------------|------------|---------------|
| {{DIV_NUM}} | {{DIV_OPERATION}} | {{DIV_FIELD}} | {{DIV_ASIS_VALUE}} | {{DIV_TOBE_VALUE}} | {{DIV_SEVERITY}} | {{DIV_JUSTIFICATION}} |

### 3.4 Exceções Aprovadas

| # | Operação | Campo | Motivo da Exceção | Aprovador | Data |
|---|----------|-------|-------------------|-----------|------|
| {{EXC_NUM}} | {{EXC_OPERATION}} | {{EXC_FIELD}} | {{EXC_REASON}} | {{EXC_APPROVER}} | {{EXC_DATE}} |

---

## 4. Checklist Go/No-Go

| # | Critério | Resultado | Peso | Obrigatório |
|---|----------|-----------|------|-------------|
| 1 | Paridade funcional ≥ {{THRESHOLD_PARITY_PCT}}% | {{GONOGO_PARITY}} | Alto | ✅ |
| 2 | Zero vulnerabilidades críticas no TO-BE | {{GONOGO_VULN_CRITICAL}} | Alto | ✅ |
| 3 | Performance TO-BE ≤ threshold configurado | {{GONOGO_PERFORMANCE}} | Alto | ✅ |
| 4 | Cobertura de testes ≥ {{THRESHOLD_LINE_COV}}% | {{GONOGO_COVERAGE}} | Médio | ✅ |
| 5 | FPs planejados 100% implementados | {{GONOGO_FP_IMPL}} | Alto | ✅ |
| 6 | SonarQube Quality Gate: Pass | {{GONOGO_SONAR}} | Médio | ✅ |
| 7 | Divergências obrigatórias resolvidas ou aprovadas | {{GONOGO_DIVERGENCES}} | Alto | ✅ |
| 8 | Smoke tests em ambiente staging: Pass | {{GONOGO_SMOKE}} | Alto | ✅ |
| 9 | Rollback strategy documentada e testada | {{GONOGO_ROLLBACK}} | Médio | ⬜ |
| 10 | Evidências de paridade anexadas | {{GONOGO_EVIDENCE}} | Médio | ✅ |

### Resultado Consolidado

| Critérios obrigatórios | Atendidos | Não atendidos | Veredicto |
|------------------------|-----------|---------------|-----------|
| {{GONOGO_MANDATORY_TOTAL}} | {{GONOGO_MANDATORY_PASS}} | {{GONOGO_MANDATORY_FAIL}} | **{{VERDICT}}** |

---

## 5. Sign-offs

| Role | Nome | Decisão | Data | Comentário |
|------|------|---------|------|------------|
| PM | {{PM_NAME}} | {{PM_DECISION}} | {{PM_DATE}} | {{PM_COMMENT}} |
| Cliente/Sponsor | {{CLIENT_NAME}} | {{CLIENT_DECISION}} | {{CLIENT_DATE}} | {{CLIENT_COMMENT}} |
| Tech Lead | {{TECH_LEAD_NAME}} | {{TL_DECISION}} | {{TL_DATE}} | {{TL_COMMENT}} |

---

## 6. Artefatos Relacionados

| Artefato | Localização |
|----------|------------|
| Relatório de paridade detalhado | `projects/{{PROJECT_NAME}}/outputs/tobe/parity-test-report.md` |
| Diferenças campo a campo | `projects/{{PROJECT_NAME}}/outputs/tobe/field-differences.json` |
| Wave approval formal | `projects/{{PROJECT_NAME}}/outputs/tobe/wave-approval.md` |
| Evidências de teste | `projects/{{PROJECT_NAME}}/outputs/tobe/evidence/` |
| Performance report | `projects/{{PROJECT_NAME}}/outputs/tobe/performance-report.md` |

---

## 7. Próximos Passos

| # | Ação | Responsável | Condição |
|---|------|-------------|----------|
| 1 | Se **GO** → Iniciar deploy para produção | DevOps Lead | Todos sign-offs coletados |
| 2 | Se **NO-GO** → Remediar bloqueadores | Dev Team | Critérios obrigatórios falharam |
| 3 | Se **NO-GO** → Re-executar comparação após fix | QA Lead | Após correções implementadas |
| 4 | Arquivar evidências no repositório | PM | Independente do veredicto |

---

*Relatório gerado automaticamente pela AVA Fabric — ava-devops-compare-version v{{REPORT_VERSION}}*
