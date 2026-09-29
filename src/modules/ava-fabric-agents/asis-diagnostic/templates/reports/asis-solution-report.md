---
template_id: "asis-solution-report"
agent: "{resolved_solution_agent}"  # set by orchestrator-asis at dispatch time (e.g. ava-asis-solution-delphi)
version: "1.0.0"
---

<!-- i18n: apply [@governance-apps](../../../shared/governance-apps.md) § asis-solution-report — if language="en", replace all PT headings and table labels per the i18n table in that section -->

# AS-IS Solution Report — {{PROJECT_NAME}}

**TraceID**: `{{TRACE_ID}}`
**Data**: {{GENERATED_AT}}
**Tecnologia**: {{LEGACY_TECHNOLOGY}}
**Escopo**: {{SCOPE}}

---

## 1. Sumário da Arquitetura AS-IS

| Métrica | Valor |
|---------|-------|
| Padrão dominante | {{DOMINANT_PATTERN}} |
| Bounded contexts identificados | {{BC_COUNT}} |
| Risco de migração global | {{RISK_LEVEL}} ({{RISK_SCORE}}/100) |
| Forms / telas mapeadas | {{FORM_COUNT}} |
| Units / classes identificadas | {{UNIT_COUNT}} |

## 2. Blueprint Arquitetural

### 2.1 Contexto (C4 Nível 1)
```mermaid
{{C4_CONTEXT_DIAGRAM}}
```

### 2.2 Containers (C4 Nível 2)
```mermaid
{{C4_CONTAINER_DIAGRAM}}
```

### 2.3 Componentes (C4 Nível 3 — por módulo)
```mermaid
{{C4_COMPONENT_DIAGRAM}}
```

## 3. Padrões Identificados

| Padrão | Ocorrências | % do código | Risco |
|--------|-------------|-------------|-------|
| Smart UI (Form-Centric) | {{COUNT}} | {{PCT}}% | 🔴 Alto |
| DataModule (Repository implícito) | {{COUNT}} | {{PCT}}% | 🟡 Médio |
| Two-Tier (SQL inline) | {{COUNT}} | {{PCT}}% | 🔴 Alto |
| Rich Domain (units com lógica) | {{COUNT}} | {{PCT}}% | 🟢 Baixo |

## 4. Bounded Context Map

| Bounded Context | Forms | Units | Risco | Tamanho estimado |
|----------------|-------|-------|-------|-----------------|
{{#each BOUNDED_CONTEXTS}}
| {{name}} | {{form_count}} | {{unit_count}} | {{risk}} | {{size}} SP |
{{/each}}

## 5. Diagramas

### 5.1 Diagrama de Sequência — {{MAIN_FLOW_NAME}}
```mermaid
{{SEQUENCE_DIAGRAM_MAIN}}
```

### 5.2 Diagrama de Componentes
```mermaid
{{COMPONENT_DIAGRAM}}
```

## 6. Mapa de APIs e Integrações
{{API_MAP}}

## 7. Estrutura de Dados
{{DATA_STRUCTURE}}

## 8. Findings Críticos

{{#each CRITICAL_FINDINGS}}
> ⚠️ **{{severity}}**: {{description}}
> **Localização**: `{{file}}:{{line}}`
> **Impacto na migração**: {{migration_impact}}
{{/each}}

## 9. Artefatos Gerados

| Artefato | Tipo | Path |
|---------|------|------|
| C4 Context | Mermaid | `projects/{project_name}/outputs/asis/diagrams/c4-context.mmd` |
| C4 Container | Mermaid | `projects/{project_name}/outputs/asis/diagrams/c4-container.mmd` |
| C4 Component | Mermaid | `projects/{project_name}/outputs/asis/diagrams/c4-component.mmd` |
| Bounded Context Map | Markdown | `projects/{project_name}/outputs/asis/bounded-context-map.md` |
| Pattern Classifications | JSON | `projects/{project_name}/outputs/asis/pattern-classifications.json` |

---
*Gerado por AVA Fabric — AS-IS Solution Agent (Delphi) v{{VERSION}}*
