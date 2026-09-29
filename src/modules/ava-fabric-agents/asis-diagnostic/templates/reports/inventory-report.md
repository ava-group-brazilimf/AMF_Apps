---
template_id: "inventory-report"
agent: "ava-asis-inventory"
version: "1.0.0"
---

<!-- i18n: apply [@governance-apps](../../../shared/governance-apps.md) § inventory-report — if language="en", replace all PT headings and table labels per the i18n table in that section -->

# Inventário Quantitativo AS-IS — {{PROJECT_NAME}}

**TraceID**: `{{TRACE_ID}}`
**Data**: {{GENERATED_AT}}

---

## 1. Totalizadores Gerais

| Métrica | Total |
|---------|-------|
| Linhas de código (LOC) | {{TOTAL_LOC}} |
| Linhas de código efetivo (sem comentários/brancos) | {{EFFECTIVE_LOC}} |
| Número de arquivos | {{FILE_COUNT}} |
| Número de classes / forms | {{CLASS_COUNT}} |
| Número de métodos / procedures | {{METHOD_COUNT}} |
| Número de módulos / packages | {{MODULE_COUNT}} |
| Número de camadas identificadas | {{LAYER_COUNT}} |
| Stored procedures | {{SP_COUNT}} |
| Tabelas no banco | {{TABLE_COUNT}} |

## 2. Distribuição por Módulo

| Módulo | LOC | Classes | Métodos | Complexidade Média |
|--------|-----|---------|---------|-------------------|
{{#each MODULES}}
| {{name}} | {{loc}} | {{classes}} | {{methods}} | {{avg_complexity}} |
{{/each}}

## 3.  — Maior Complexidade Ciclomática

| # | Arquivo | Método | Complexidade | Caminho |
|---|---------|--------|-------------|---------|
{{#each TOP_COMPLEXITY}}
| {{rank}} | {{file}} | {{method}} | {{complexity}} | `{{path}}` |
{{/each}}

> ⚠️ Complexidade > 10 = candidato a refatoração prioritária na migração

## 4.  — Maiores Arquivos (LOC)

| # | Arquivo | LOC | Tipo | Caminho |
|---|---------|-----|------|---------|
{{#each TOP_LOC}}
| {{rank}} | {{file}} | {{loc}} | {{type}} | `{{path}}` |
{{/each}}

## 5. Camadas Identificadas

| Camada | Descrição | Arquivos | LOC |
|--------|-----------|---------|-----|
{{#each LAYERS}}
| {{name}} | {{description}} | {{file_count}} | {{loc}} |
{{/each}}

## 6. Matriz de Acoplamento entre Módulos

> Células com valor alto (>5) indicam acoplamento excessivo — risco de migração

```
{{COUPLING_MATRIX}}
```

## 7. Métricas de Qualidade Estimadas

| Métrica | Valor | Benchmark |
|---------|-------|-----------|
| Complexidade ciclomática média | {{AVG_COMPLEXITY}} | < 5 (ideal) |
| % de código duplicado estimado | {{DUPLICATION_PCT}}% | < 3% (ideal) |
| Cobertura de testes atual | {{TEST_COVERAGE}}% | — |
| Ratio comentários / código | {{COMMENT_RATIO}}% | 15–30% |

---
*Gerado por AVA Fabric — Inventory AS-IS Agent v{{VERSION}}*
