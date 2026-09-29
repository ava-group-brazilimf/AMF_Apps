---
report_id: "{{REPORT_ID}}"
agent_id: "{{AGENT_ID}}"
agent_name: "{{AGENT_NAME}}"
trace_id: "{{TRACE_ID}}"
generated_at: "{{TIMESTAMP}}"
project: "{{PROJECT_NAME}}"
version: "{{REPORT_VERSION}}"
status: "{{STATUS}}"
---

# {{REPORT_TITLE}}

## Sumário Executivo
> Resumo em 3–5 linhas do que foi analisado, o que foi encontrado e a recomendação principal.

| Campo | Valor |
|-------|-------|
| Agente | {{AGENT_NAME}} ({{AGENT_ID}}) |
| Escopo | {{SCOPE}} |
| Data | {{TIMESTAMP}} |
| Status | {{STATUS}} |
| Risco geral | {{RISK_LEVEL}} |

---

## 1. Contexto e Escopo
> O que foi analisado, o que está fora do escopo, premissas assumidas.

## 2. Metodologia
> Como a análise foi conduzida, ferramentas utilizadas, fontes de dados.

## 3. Resultados
> Findings detalhados, organizados por categoria/módulo.

### 3.1 {{FINDING_CATEGORY_1}}
### 3.2 {{FINDING_CATEGORY_2}}

## 4. Riscos Identificados

| ID | Descrição | Severidade | Probabilidade | Impacto | Mitigação |
|----|-----------|------------|---------------|---------|-----------|
| R-01 | | 🔴 Crítico | | | |
| R-02 | | 🟡 Médio | | | |

## 5. Recomendações

| Prioridade | Recomendação | Responsável | Prazo |
|------------|-------------|-------------|-------|
| P0 | | | |
| P1 | | | |

## 6. Artefatos Gerados

| Artefato | Tipo | Localização |
|---------|------|------------|
| | | |

## 7. Próximos Passos
> O que deve acontecer após este relatório, quem aciona e em qual ordem.

---
*Relatório gerado automaticamente pela AVA Fabric — {{AGENT_NAME}} v{{REPORT_VERSION}}*
