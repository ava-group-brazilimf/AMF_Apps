---
name: tobe-quality-gate
description: "Checklist de quality gate para aprovação da arquitetura TO-BE"
version: "1.1.0"
applies_to: tobe-architecture
updated_by: "PBI-363 — Design System applicability assessment and screen coherence review"
---

# TO-BE Quality Gate Checklist

## Obrigatório antes de iniciar codegen

### Arquitetura
- [ ] Solution blueprint TO-BE aprovado pelo CTO/Tech Lead
- [ ] Bounded contexts mapeados 1:1 com módulos AS-IS (ou justificado quando diferente)
- [ ] Clean Architecture layers definidas por bounded context
- [ ] Estratégia de banco de dados TO-BE definida (EF Core / Dapper / mix)
- [ ] API surface design completo (REST + gRPC onde aplicável)
- [ ] ADRs escritos para as 5 decisões mais importantes

### Técnico
- [ ] Tech Framework Document aprovado
- [ ] NuGet packages selecionados e versionados
- [ ] Quality gates definidos (cobertura ≥ 80%, zero blocker Sonar)
- [ ] .editorconfig e StyleCop configurados
- [ ] Git flow e branch strategy definidos

### Planejamento
- [ ] Sizing e estimativas revisados pelo PM
- [ ] Migration Waves Plan com sequência de módulos definida
- [ ] Critérios de aceite definidos para cada wave
- [ ] Rollback strategy documentada para cada wave
- [ ] Feature flags strategy definida (Strangler Fig)

### Design System & UI Review
- [ ] `designer-system.md` contém **Seção 0 — Applicability Declaration** com todos os bounded contexts listados (nenhum BC omitido)
- [ ] Todos os BCs com `Applies = Yes` possuem exemplos de componentes e tokens documentados em `designer-system.md`
- [ ] Todos os BCs com `Applies = No` ou `Partial` possuem entrada em **Non-Applicable Cases** com: motivo, alternativa visual e responsável pela UI — entrada vazia ou ausente é **falha de gate**
- [ ] Wireframes do protótipo usam exclusivamente tokens e componentes definidos em `designer-system.md`
- [ ] `screen-coherence-review.md` gerado e revisado pelo Tech Lead
- [ ] Cada tela TO-BE é rastreável a um formulário AS-IS ou possui justificativa explícita de tela nova

### Wave Approval Criteria (por wave)
- [ ] Cobertura de testes ≥ 80% (line coverage)
- [ ] Zero findings Critical ou High no SonarQube
- [ ] Zero vulnerabilidades OWASP Critical
- [ ] Paridade funcional ≥ 99.5% (Compare Version Test)
- [ ] Performance igual ou melhor que AS-IS (p95 latência)
- [ ] SME do cliente validou funcionalmente
- [ ] Human go/no-go gate aprovado
