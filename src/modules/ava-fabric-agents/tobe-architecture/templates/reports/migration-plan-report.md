---
template_id: "migration-plan-report"
agent: "ava-tobe-migration-plan"
version: "1.0.0"
---

<!-- i18n: apply [@governance-apps](../../../shared/governance-apps.md) § migration-plan-report — if language="en", replace all PT headings and table labels per the i18n table in that section -->

# Migration Plan — {{PROJECT_NAME}}

**TraceID**: `{{TRACE_ID}}`
**Data**: {{GENERATED_AT}}
**Estratégia**: Strangler Fig Pattern
**Total de Waves**: {{WAVE_COUNT}}
**Duração estimada**: {{TOTAL_DURATION}} sprints

---

## 1. Sumário do Plano

| Métrica | Valor |
|---------|-------|
| Módulos a migrar | {{MODULE_COUNT}} |
| Total de waves | {{WAVE_COUNT}} |
| Story points estimados | {{TOTAL_SP}} |
| Duração total | {{TOTAL_DURATION}} sprints |
| Team size recomendado | {{TEAM_SIZE}} devs |

## 2. Cronograma de Waves (Gantt)

```mermaid
gantt
    title Migration Waves Plan
    dateFormat YYYY-MM-DD
    section Preparação
    Sprint de Extração de SPs :crit, sp-extract, {{START_DATE}}, 2w
    Setup infraestrutura      :infra, after sp-extract, 1w
{{#each WAVES}}
    section Wave {{number}} — {{name}}
    Desenvolvimento           :wave-{{number}}-dev, {{start}}, {{dev_duration}}
    Testes e validação        :wave-{{number}}-test, after wave-{{number}}-dev, {{test_duration}}
    Deploy e monitoramento    :milestone, wave-{{number}}-deploy, after wave-{{number}}-test, 0d
{{/each}}
```

## 3. Detalhamento das Waves

{{#each WAVES}}
---
### Wave {{number}}: {{name}}

| Campo | Valor |
|-------|-------|
| Módulos | {{modules}} |
| Duração | {{duration}} sprints |
| Story Points | {{story_points}} SP |
| Risco | {{risk_level}} |
| Feature Flag | `{{feature_flag}}` |

#### Bounded Contexts Incluídos
{{#each bounded_contexts}}
- **{{name}}**: {{description}}
{{/each}}

#### Dependências
{{#if dependencies}}
- Requer conclusão de: {{dependencies}}
{{else}}
- Sem dependências de waves anteriores
{{/if}}

#### Critérios de Aceite (go/no-go)
- [ ] Cobertura de testes ≥ {{coverage_threshold}}%
- [ ] Zero findings Critical/High no SonarQube
- [ ] Paridade funcional ≥ 99.5% (Compare Version Test)
- [ ] Performance ≤ AS-IS p95 latência
- [ ] Cliente validação funcional concluída
- [ ] Human go/no-go gate aprovado

#### Rollback Strategy
{{rollback_strategy}}

#### ADO Work Items
- Epic: {{ado_epic_id}}
- Features: {{feature_count}} features
- Stories: {{story_count}} user stories
{{/each}}

## 4. Estratégia de Coexistência (Strangler Fig)

```
AS-IS (Delphi) ──── Feature Flag ──── TO-BE (.NET)
     ↑                    │                 ↑
     │            0% → 10% → 50% → 100%     │
     └──── Fallback automático se erro ──────┘
```

**Fluxo por wave**:
1. Deploy TO-BE módulo em produção (feature flag = 0%)
2. Ativar para 10% do tráfego → monitorar
3. Validar métricas → ativar para 50%
4. Validação final → 100%
5. Desativar código Delphi do módulo após 30 dias

## 5. Riscos do Plano

| Risco | Probabilidade | Impacto | Mitigação |
|-------|-------------|---------|-----------|
| SP com lógica bloqueando Wave 1 | Alta | Alto | Sprint de Extração antecipado |
| Dados legados incompatíveis | Média | Alto | Data migration scripts validados |
| Performance inferior ao Delphi | Baixa | Médio | Benchmark contínuo + otimização |

---
*Gerado por AVA Fabric — Migration Plan Agent v{{VERSION}}*
