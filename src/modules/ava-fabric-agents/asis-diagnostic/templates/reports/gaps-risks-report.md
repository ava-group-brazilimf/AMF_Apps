---
template_id: "gaps-risks-report"
agent: "ava-asis-gaps-risks"
version: "1.0.0"
---

<!-- i18n: apply [@governance-apps](../../../shared/governance-apps.md) § gaps-risks-report — if language="en", replace all PT headings and table labels per the i18n table in that section -->

# Gaps & Risks Report — {{PROJECT_NAME}}

**TraceID**: `{{TRACE_ID}}`
**Data**: {{GENERATED_AT}}
**Score de Risco Global**: {{RISK_SCORE}}/100 — {{RISK_LEVEL}}

---

## 1. Sumário Executivo de Riscos

| Severidade | Quantidade |
|------------|-----------|
| 🔴 Crítico (P0) | {{CRITICAL_COUNT}} |
| 🟠 Alto (P1) | {{HIGH_COUNT}} |
| 🟡 Médio (P2) | {{MEDIUM_COUNT}} |
| 🟢 Baixo (P3) | {{LOW_COUNT}} |
| **Total** | **{{TOTAL_COUNT}}** |

## 2. Risk Register Completo

| ID | Categoria | Descrição | Probabilidade | Impacto | Score | Mitigação | Status |
|----|-----------|-----------|---------------|---------|-------|-----------|--------|
{{#each RISKS}}
| {{id}} | {{category}} | {{description}} | {{probability}} | {{impact}} | {{score}} | {{mitigation}} | Aberto |
{{/each}}

## 3. Top Riscos Críticos (P0)

{{#each CRITICAL_RISKS}}
### {{id}} — {{title}}
**Categoria**: {{category}}
**Descrição**: {{description}}
**Evidência**: `{{evidence_file}}:{{evidence_line}}`
**Impacto no projeto**: {{project_impact}}
**Mitigação recomendada**: {{mitigation}}
**Responsável**: {{owner}}

---
{{/each}}

## 4. Gaps Identificados

### 4.1 Gaps Funcionais
| ID | Funcionalidade AS-IS | Status no TO-BE | Ação Necessária |
|----|---------------------|-----------------|----------------|
{{#each FUNCTIONAL_GAPS}}
| {{id}} | {{feature}} | {{tobe_status}} | {{action}} |
{{/each}}

### 4.2 Gaps Técnicos
| ID | Componente AS-IS | Equivalente TO-BE | Complexidade |
|----|-----------------|------------------|-------------|
{{#each TECHNICAL_GAPS}}
| {{id}} | {{asis_component}} | {{tobe_equivalent}} | {{complexity}} |
{{/each}}

## 5. Riscos por Módulo / Bounded Context

{{#each BC_RISKS}}
### {{bounded_context}}
- Risk score: {{score}}/100
- Top risco: {{top_risk}}
- Recomendação: {{recommendation}}
{{/each}}

## 6. Próximos Passos Recomendados

| Prioridade | Ação | Responsável | Prazo |
|------------|------|-------------|-------|
| P0 | {{ACTION_1}} | | Sprint 1 |
| P0 | {{ACTION_2}} | | Sprint 1 |
| P1 | {{ACTION_3}} | | Sprint 2 |

---
*Gerado por AVA Fabric — Gaps & Risks Agent v{{VERSION}}*
