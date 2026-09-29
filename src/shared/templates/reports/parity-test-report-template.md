---
report_id: "{{REPORT_ID}}"
agent_id: "ava-devops-compare-version"
agent_name: "AVA Compare Version"
trace_id: "{{TRACE_ID}}"
generated_at: "{{TIMESTAMP}}"
project: "{{PROJECT_NAME}}"
wave_id: "{{WAVE_ID}}"
wave_name: "{{WAVE_NAME}}"
golden_dataset_version: "{{GOLDEN_DATASET_VERSION}}"
status: "{{STATUS}}"
---

# Parity Test Report — Wave {{WAVE_ID}}

## Sumário Executivo

| Campo | Valor |
|-------|-------|
| Projeto | {{PROJECT_NAME}} |
| Wave | {{WAVE_NAME}} ({{WAVE_ID}}) |
| Data de Geração | {{TIMESTAMP}} |
| Golden Dataset | `{{GOLDEN_DATASET_PATH}}` (v{{GOLDEN_DATASET_VERSION}}) |
| Total de entradas executadas | {{TOTAL_ENTRIES}} |
| Bounded Contexts avaliados | {{TOTAL_BC_COUNT}} |
| Índice de Paridade Global | **{{GLOBAL_PARITY_PCT}}%** |
| Threshold mínimo | {{THRESHOLD_PARITY_PCT}}% |
| Veredicto Global | **{{GLOBAL_VERDICT}}** |

---

## 1. Score de Paridade por Bounded Context

| Bounded Context | Entradas | Matches | Divergências | Exceções Aprovadas | Timeouts | Paridade (%) | Status |
|---|---|---|---|---|---|---|---|
| {{BC_NAME}} | {{BC_TOTAL}} | {{BC_MATCHES}} | {{BC_DIVERGENCES}} | {{BC_EXCEPTIONS}} | {{BC_TIMEOUTS}} | {{BC_PARITY_PCT}}% | {{BC_STATUS}} |

> **Status:** ✅ PASS (≥ {{THRESHOLD_PARITY_PCT}}%) | ❌ FAIL (< {{THRESHOLD_PARITY_PCT}}%) | ⚠️ PARCIAL (≥ 90% mas abaixo do threshold)

---

## 2. Detalhamento por Bounded Context

<!--
  Repetir o bloco abaixo (seções 2.N) para cada Bounded Context presente no golden dataset.
  O agente substitui {BC_NAME} pelo nome real do BC em cada bloco.
-->

### 2.{{BC_INDEX}} — {{BC_NAME}}

**Score:** {{BC_PARITY_PCT}}% ({{BC_MATCHES}} matches / {{BC_TOTAL}} entradas) | Status: {{BC_STATUS}}

#### Resultados por Operação

| # | ID | Operação | Método | Match | AS-IS Status | TO-BE Status | Latência AS-IS (ms) | Latência TO-BE (ms) |
|---|---|---|---|---|---|---|---|---|
| {{ROW_NUM}} | {{ENTRY_ID}} | {{OPERATION}} | {{METHOD}} | {{MATCH_STATUS}} | {{ASIS_HTTP_STATUS}} | {{TOBE_HTTP_STATUS}} | {{ASIS_LATENCY_MS}} | {{TOBE_LATENCY_MS}} |

#### Divergências Identificadas

| # | ID | Operação | Campo | Valor AS-IS | Valor TO-BE | Severidade | Exceção Aprovada |
|---|---|---|---|---|---|---|---|
| {{DIV_NUM}} | {{ENTRY_ID}} | {{OPERATION}} | {{FIELD_PATH}} | {{ASIS_VALUE}} | {{TOBE_VALUE}} | {{SEVERITY}} | {{EXCEPTION_STATUS}} |

> Se não houver divergências: `Nenhuma divergência identificada neste Bounded Context.`

---

## 3. Timeouts Registrados

| # | ID | Bounded Context | Operação | Sistema | Duração (ms) | Observação |
|---|---|---|---|---|---|---|
| {{TO_NUM}} | {{ENTRY_ID}} | {{BC_NAME}} | {{OPERATION}} | AS-IS \| TO-BE | {{DURATION_MS}} | {{OBSERVATION}} |

> Se timeout_count / total_entries > 10% em qualquer BC, gerar alerta: `⚠️ BC {{BC_NAME}}: {{TIMEOUT_PCT}}% de timeouts — investigar disponibilidade do endpoint.`

---

## 4. Exceções Aprovadas

| # | ID | Bounded Context | Operação | Campo | Motivo | Aprovador | Data |
|---|---|---|---|---|---|---|---|
| {{EXC_NUM}} | {{ENTRY_ID}} | {{BC_NAME}} | {{OPERATION}} | {{FIELD_PATH}} | {{REASON}} | {{APPROVER}} | {{APPROVAL_DATE}} |

---

## 5. Índice de Paridade Global

```
Global Parity Index = Σ(bc_parity_pct × bc_entries) / Σ(bc_entries)
                    = {{GLOBAL_PARITY_CALC}}
                    = {{GLOBAL_PARITY_PCT}}%
```

| BC | Paridade (%) | Entradas | Peso (%) | Contribuição |
|---|---|---|---|---|
| {{BC_NAME}} | {{BC_PARITY_PCT}} | {{BC_TOTAL}} | {{BC_WEIGHT_PCT}} | {{BC_CONTRIBUTION}} |
| **GLOBAL** | — | {{TOTAL_ENTRIES}} | 100% | **{{GLOBAL_PARITY_PCT}}%** |

---

## 6. Veredicto Consolidado por Bounded Context

| Bounded Context | Paridade (%) | Threshold | Veredicto | Critérios Bloqueantes |
|---|---|---|---|---|
| {{BC_NAME}} | {{BC_PARITY_PCT}}% | {{THRESHOLD_PARITY_PCT}}% | {{BC_VERDICT}} | {{BC_BLOCKERS}} |

**Veredicto Global: {{GLOBAL_VERDICT}}**

> GO → todos os BCs atingiram o threshold de paridade
> NO-GO → ≥ 1 BC abaixo do threshold
> CONDICIONAL → BCs abaixo do threshold possuem exceções aprovadas cobrindo todas as divergências
