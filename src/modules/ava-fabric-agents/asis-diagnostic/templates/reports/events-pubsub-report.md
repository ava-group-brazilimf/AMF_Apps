---
template_id: "events-pubsub-report"
agent: "ava-asis-events-pubsub"
version: "1.0.0"
---

# Events, Pub/Sub & Queues Inventory — {{PROJECT_NAME}}

**TraceID**: `{{TRACE_ID}}`
**Data**: {{GENERATED_AT}}
**Tecnologia**: {{LEGACY_TECHNOLOGY}}
**Escopo**: {{SCOPE}}

---

## 1. Sumário

| Métrica | Valor |
|---------|-------|
| Total de eventos | {{TOTAL_EVENTS}} |
| Total de filas (queues) | {{TOTAL_QUEUES}} |
| Total de padrões Pub/Sub | {{TOTAL_PUBSUB}} |
| Mecanismos IPC | {{TOTAL_IPC}} |
| DB Queues (tabela-fila) | {{TOTAL_DB_QUEUES}} |
| File Queues | {{TOTAL_FILE_QUEUES}} |
| Eventos órfãos | {{ORPHAN_EVENTS}} |
| Risco CRITICAL | {{RISK_CRITICAL}} |
| Risco HIGH | {{RISK_HIGH}} |
| Risco MEDIUM | {{RISK_MEDIUM}} |
| Risco LOW | {{RISK_LOW}} |

---

## 2. Grid Consolidado de Eventos

> Ordenado por `Ocorrências` desc. Inclui TODAS as categorias.

| # | Chave | Categoria | Sub-Categoria | Descrição | Mecanismo | Papel | Ocorrências | Qtd Arquivos | Risco |
|---|-------|-----------|---------------|-----------|-----------|-------|-------------|-------------|-------|
{{#each EVENTS_ALL}}
| {{@index}} | `{{key}}` | {{category}} | {{subcategory}} | {{description}} | {{mechanism}} | {{role}} | **{{occurrences}}** | {{file_count}} | {{risk_badge}} |
{{/each}}

---

## 3. Grid de Filas (Queues)

| # | Chave | Tipo | Tecnologia | Descrição | Ocorrências | Produtores | Consumidores | Risco |
|---|-------|------|------------|-----------|-------------|------------|--------------|-------|
{{#each QUEUES}}
| {{@index}} | `{{key}}` | {{type}} | {{technology}} | {{description}} | **{{occurrences}}** | {{producers}} | {{consumers}} | {{risk_badge}} |
{{/each}}

---

## 4. Grid de Pub/Sub

| # | Chave | Padrão | Publisher(s) | Subscriber(s) | Fan-out | Ocorrências | Risco |
|---|-------|--------|-------------|----------------|---------|-------------|-------|
{{#each PUBSUB}}
| {{@index}} | `{{key}}` | {{pattern}} | {{publishers}} | {{subscribers}} | {{fanout}} | **{{occurrences}}** | {{risk_badge}} |
{{/each}}

---

## 5. Referências por Chave (Top {{TOP_N}})

> Detalhamento das chaves mais repetidas no código.

{{#each TOP_KEYS}}
### {{key}} — {{occurrences}} ocorrências

| # | Arquivo | Linha | Contexto | Papel |
|---|---------|-------|----------|-------|
{{#each references}}
| {{@index}} | `{{file}}` | L{{line}} | `{{context}}` | {{role}} |
{{/each}}

{{/each}}

---

## 6. Eventos Órfãos

| # | Chave | Tipo | Declarado em | Problema | Recomendação |
|---|-------|------|-------------|----------|--------------|
{{#each ORPHAN_EVENTS_LIST}}
| {{@index}} | `{{key}}` | {{type}} | `{{declared_in}}` | {{problem}} | {{recommendation}} |
{{/each}}

---

## 7. Diagrama de Fluxo

```mermaid
{{EVENTS_FLOW_DIAGRAM}}
```

---

## 8. Matriz de Risco de Migração

| Mecanismo | Quantidade | Risco | Equivalente TO-BE |
|-----------|-----------|-------|-------------------|
{{#each RISK_MATRIX}}
| {{mechanism}} | {{count}} | {{risk_badge}} | {{tobe_equivalent}} |
{{/each}}

---

## 9. Recomendações para TO-BE

{{#each RECOMMENDATIONS}}
### {{@index}}. {{title}}
- **Impacto**: {{impact}}
- **Esforço**: {{effort}}
- **Ação**: {{action}}
{{/each}}
