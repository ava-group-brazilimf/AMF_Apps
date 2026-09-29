# Matriz de Decisão Arquitetural — {{PROJECT_NAME}}

> **Agente**: `ava-tobe-architecture-decision-matrix` v1.0.0  
> **Fase**: 0-Pre (pré-ADR Generation)  
> **Gerado em**: {{GENERATED_AT}}  
> **Trace ID**: {{TRACE_ID}}

---

## 1. Contexto do Projeto

| Sinal | Valor | Fonte |
|---|---|---|
| `migration_readiness_score` | {{MIGRATION_READINESS_SCORE}} | `outputs/asis/master-report.md` |
| `coupling_index` | {{COUPLING_INDEX}} | `outputs/asis/master-report.md` |
| `bounded_context_count` | {{BOUNDED_CONTEXT_COUNT}} | `outputs/asis/docs/bounded-context-map.md` |
| `loc_total` | {{LOC_TOTAL}} | `outputs/asis/master-report.md` |
| `legacy_technology` | {{LEGACY_TECHNOLOGY}} | `project-config.yaml` |
| `compliance_required` | {{COMPLIANCE_REQUIRED}} | `project-config.yaml → country` |
| `container_runtime_declared` | {{CONTAINER_RUNTIME_DECLARED}} | `project-config.yaml → tobe_stack.infrastructure` |
| `auth_declared` | {{AUTH_DECLARED}} | `project-config.yaml → tobe_stack.auth` |
| `security_gate` | {{SECURITY_GATE}} | `outputs/asis/master-report.md` |
| `tech_debt_index` | {{TECH_DEBT_INDEX}} | `outputs/asis/gaps-risks-report.md` |

> **Limitações de Dados**: {{DATA_LIMITATIONS_OR_NONE}}

---

## 2. Guardrails Aplicados

| ID | Nome | Condição Avaliada | Status | Efeito |
|---|---|---|---|---|
| GR-01 | Legado Altamente Acoplado | `coupling_index == HIGH OR migration_readiness_score < 40` | {{GR01_STATUS}} | {{GR01_EFFECT}} |
| GR-02 | Ausência de Container Infrastructure | `container_runtime NOT declared` | {{GR02_STATUS}} | {{GR02_EFFECT}} |
| GR-03 | Migration Readiness Baixo | `migration_readiness_score < 40` | {{GR03_STATUS}} | {{GR03_EFFECT}} |
| GR-04 | Alta Contagem de Bounded Contexts | `bounded_context_count > 15` | {{GR04_STATUS}} | {{GR04_EFFECT}} |
| GR-05 | Compliance sem Security Layer | `compliance_required AND auth NOT declared` | {{GR05_STATUS}} | {{GR05_EFFECT}} |

> **Legenda**: ✅ NOT_TRIGGERED · ⚠️ TRIGGERED (delta/cap) · 🚫 TRIGGERED (blocked)

---

## 3. Pontuação por Critério

> Escala: 1 (desfavorável) → 10 (muito favorável). Scores ajustados aos sinais reais do projeto.
> Pesos somam 100%. Células marcadas com `†` indicam ajuste por guardrail.

| Critério | Peso | STY-001<br>Simple Monolith | STY-002<br>Clean Arch. | STY-003<br>Vertical Slice | STY-004<br>Modular Monolith | STY-005<br>Microservices | STY-006<br>Cloud-Native |
|---|---|---|---|---|---|---|---|
| **C-01** Decomponibilidade do Legado | 10% | {{S001_C01}} | {{S002_C01}} | {{S003_C01}} | {{S004_C01}} | {{S005_C01}} | {{S006_C01}} |
| **C-02** Viabilidade de Migração | 15% | {{S001_C02}} | {{S002_C02}} | {{S003_C02}} | {{S004_C02}} | {{S005_C02}} | {{S006_C02}} |
| **C-03** Time to First Release | 12% | {{S001_C03}} | {{S002_C03}} | {{S003_C03}} | {{S004_C03}} | {{S005_C03}} | {{S006_C03}} |
| **C-04** Manutenibilidade LP | 10% | {{S001_C04}} | {{S002_C04}} | {{S003_C04}} | {{S004_C04}} | {{S005_C04}} | {{S006_C04}} |
| **C-05** Escalabilidade Independente | 8% | {{S001_C05}} | {{S002_C05}} | {{S003_C05}} | {{S004_C05}} | {{S005_C05}} | {{S006_C05}} |
| **C-06** Isolamento de Dados | 8% | {{S001_C06}} | {{S002_C06}} | {{S003_C06}} | {{S004_C06}} | {{S005_C06}} | {{S006_C06}} |
| **C-07** Complexidade Operacional | 10% | {{S001_C07}} | {{S002_C07}} | {{S003_C07}} | {{S004_C07}} | {{S005_C07}} | {{S006_C07}} |
| **C-08** Testabilidade | 8% | {{S001_C08}} | {{S002_C08}} | {{S003_C08}} | {{S004_C08}} | {{S005_C08}} | {{S006_C08}} |
| **C-09** DDD fit | 10% | {{S001_C09}} | {{S002_C09}} | {{S003_C09}} | {{S004_C09}} | {{S005_C09}} | {{S006_C09}} |
| **C-10** Conformidade e Segurança | 9% | {{S001_C10}} | {{S002_C10}} | {{S003_C10}} | {{S004_C10}} | {{S005_C10}} | {{S006_C10}} |

---

## 4. Score Ponderado Final

$$\text{Score}_{\text{estilo}} = \sum_{i=1}^{10} \text{peso}_i \times \text{nota}_i$$

| Rank | Estilo | Score Ponderado | Status |
|---|---|---|---|
| 🥇 1 | {{RANK1_STYLE}} | **{{RANK1_SCORE}}** | ✅ RECOMENDADO |
| 🥈 2 | {{RANK2_STYLE}} | {{RANK2_SCORE}} | Runner-up |
| 3 | {{RANK3_STYLE}} | {{RANK3_SCORE}} | Viável |
| 4 | {{RANK4_STYLE}} | {{RANK4_SCORE}} | Não recomendado |
| 5 | {{RANK5_STYLE}} | {{RANK5_SCORE}} | Não recomendado |
| 6 | {{RANK6_STYLE}} | {{RANK6_SCORE}} | {{RANK6_STATUS}} |

**Gap vencedor → runner-up**: {{GAP_PCT}}% → Confiança: **{{CONFIDENCE}}**

---

## 5. Recomendação Arquitetural

### Estilo Selecionado: {{SELECTED_STYLE_NAME}} (`{{SELECTED_STYLE_ID}}`)

> {{RECOMMENDATION_SUMMARY_PARAGRAPH}}

### Drivers-chave da decisão

| Critério | Score Vencedor | Score Runner-up | Diferencial |
|---|---|---|---|
{{KEY_DRIVERS_TABLE}}

### Por que os demais estilos foram descartados

| Estilo | Razão principal de descarte |
|---|---|
{{DISCARDED_STYLES_TABLE}}

---

## 6. Runner-up e Caminho de Evolução

**Runner-up**: {{RUNNER_UP_STYLE_NAME}} (score: {{RUNNER_UP_SCORE}})

> {{RUNNER_UP_CONTEXT}}

**Caminho de evolução do estilo vencedor**:

```
{{EVOLUTION_PATH}}
```

> **Trigger de evolução**: {{EVOLUTION_TRIGGER}}

---

## 7. Artefatos Produzidos

| Artefato | Path | Consumido por |
|---|---|---|
| Este relatório | `projects/{{PROJECT_NAME}}/outputs/tobe/docs/architecture-decision-matrix.md` | Revisão humana |
| Bloco `decision_matrix_result` | Embutido neste arquivo (seção abaixo) | `adr-tobe` (Fase 0) |

---

## 8. Bloco decision_matrix_result

> ⚠️ Este bloco YAML é a saída estruturada consumida pelo agente `adr-tobe`.
> Não editar manualmente — gerado pelo agente `ava-tobe-architecture-decision-matrix`.

```yaml
{{DECISION_MATRIX_RESULT_YAML}}
```
