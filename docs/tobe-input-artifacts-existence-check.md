TO-BE Pipeline — Input Artifact Existence Check

> **Fonte**: `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` (v2.4.0)
> **Projeto usado para verificação de existência**: `Meu-ERP-008-AST-LLM-Master-Orchestrator`
> **Gerado em**: 2026-07-13
> **Escopo**: todos os artefatos de entrada declarados pelo orquestrador TO-BE cujo path está
> sob `outputs/asis/` ou `outputs/tobe/` (exclui `context/project-config.yaml`,
> `context/shared-context.md` e referências de `src/shared/`, que não pertencem à árvore
> `outputs/` do projeto).
> Paths relativos a `projects/Meu-ERP-008-AST-LLM-Master-Orchestrator/`.1. Resumo

Foram extraídas **163 referências de entrada** (linhas de tabelas "Inputs obrigatórios" /
"Fontes obrigatórias" / "Gate de entrada") ao longo de 23 seções de fase do
`orchestrator-tobe.md` (0-Pre → 7.8), cobrindo **79 paths distintos**. Duas fases nomeadas no
"Agent Team Gerenciado" — **Fase 7** (`user-journeys-tobe.md`) e **Fase 8**
(`azure-infra-estimator-tobe.md`) — não possuem seção `### Fase N —` própria neste arquivo (nem
tabela de Inputs, nem bloco `Invocar`), então não contribuem linhas a esta auditoria; isso já é
um discrepância documentada em `docs/tobe-architecture-io-map.md` §4.3.

Contra o projeto `Meu-ERP-008-AST-LLM-Master-Orchestrator`, **78 das 163 referências (48%)
resolvem para um arquivo existente em disco (SIM)** e **85 (52%) não resolvem (NÃO)**. O achado
mais notável não é "fase não executada": vários artefatos **obrigatórios/bloqueantes** segundo o
orquestrador — por exemplo `outputs/tobe/docs/architecture-blueprint.md` (gate de 6 fases
diferentes) e `outputs/tobe/migration/wave-model.json` (gate de 5 fases diferentes) — aparecem
como **NÃO** mesmo com fases claramente posteriores já materializadas no projeto (`migration-plan.md`,
`coexistence-strategy.md`, `architecture-technical.md` existem). Isso indica que o projeto foi
gerado por uma execução cujos artefatos TO-BE vivem em paths/nomes **diferentes** dos que
`orchestrator-tobe.md` v2.4.0 declara hoje (ex.: `outputs/tobe/architecture-blueprint.md` em vez
de `outputs/tobe/docs/architecture-blueprint.md`; `outputs/tobe/docs/wave-model.json` em vez de
`outputs/tobe/migration/wave-model.json`) — ver §3 para detalhes.

## 2. Tabela de Verificação

| Fase  | Agente                                        | Nome do arquivo de Entrada                 | Path do Arquivo                                           | Existente (SIM/NÃO) |
| ----- | --------------------------------------------- | ------------------------------------------ | --------------------------------------------------------- | -------------------- |
| 0-Pre | architecture-decision-matrix-tobe.md          | master-report.md                           | outputs/asis/master-report.md                             | SIM                  |
| 0-Pre | architecture-decision-matrix-tobe.md          | bounded-context-map.md (AS-IS)             | outputs/asis/bounded-context-map.md                       | SIM                  |
| 0-Pre | architecture-decision-matrix-tobe.md          | gaps-risks-report.md                       | outputs/asis/gaps-risks-report.md                         | NÃO                 |
| 0     | adr-tobe.md                                   | architecture-decision-matrix.md            | outputs/tobe/docs/architecture-decision-matrix.md         | SIM                  |
| 0     | adr-tobe.md                                   | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 0     | adr-tobe.md                                   | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 0     | adr-tobe.md                                   | screen-navigation-map.md                   | outputs/asis/docs/screen-navigation-map.md                | SIM                  |
| 0     | adr-tobe.md                                   | screen-rules.md                            | outputs/asis/docs/screen-rules.md                         | SIM                  |
| 0     | adr-tobe.md                                   | value-chain.md                             | outputs/asis/docs/value-chain.md                          | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-001-greenfield-rewrite.md              | outputs/tobe/docs/decisions/ADR-001-greenfield-rewrite.md | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-002-database.md                        | outputs/tobe/docs/decisions/ADR-002-database.md           | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-003-security.md                        | outputs/tobe/docs/decisions/ADR-003-security.md           | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-004-backend.md                         | outputs/tobe/docs/decisions/ADR-004-backend.md            | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-005-frontend.md                        | outputs/tobe/docs/decisions/ADR-005-frontend.md           | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-006-integration.md                     | outputs/tobe/docs/decisions/ADR-006-integration.md        | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-007-observability.md                   | outputs/tobe/docs/decisions/ADR-007-observability.md      | SIM                  |
| 1     | architecture-design-tobe.md                   | ADR-008-audit-log.md                       | outputs/tobe/docs/decisions/ADR-008-audit-log.md          | SIM                  |
| 1     | architecture-design-tobe.md                   | INDEX.md (ADRs)                            | outputs/tobe/docs/decisions/INDEX.md                      | SIM                  |
| 1     | architecture-design-tobe.md                   | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 1     | architecture-design-tobe.md                   | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 1     | architecture-design-tobe.md                   | value-chain.md                             | outputs/asis/docs/value-chain.md                          | SIM                  |
| 1     | architecture-design-tobe.md                   | screen-navigation-map.md                   | outputs/asis/docs/screen-navigation-map.md                | SIM                  |
| 1     | architecture-design-tobe.md                   | bounded-context-map.md (AS-IS)             | outputs/asis/bounded-context-map.md                       | SIM                  |
| 1     | architecture-design-tobe.md                   | bounded-context-map.md (TO-BE, trigger TD) | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 1.4   | database-policy-tobe.md                       | ADR-002-database.md                        | outputs/tobe/docs/decisions/ADR-002-database.md           | SIM                  |
| 1.4   | database-policy-tobe.md                       | schema-inventory.md                        | outputs/asis/db/schema-inventory.md                       | NÃO                 |
| 1.4   | database-policy-tobe.md                       | stored-procedures-map.md                   | outputs/asis/db/stored-procedures-map.md                  | NÃO                 |
| 1.4   | database-policy-tobe.md                       | triggers-map.md                            | outputs/asis/db/triggers-map.md                           | NÃO                 |
| 1.4   | database-policy-tobe.md                       | bounded-context-map.md (TO-BE)             | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 1.5   | database-design-tobe.md                       | ADR-002-database.md                        | outputs/tobe/docs/decisions/ADR-002-database.md           | SIM                  |
| 1.5   | database-design-tobe.md                       | sql-strategy.md                            | outputs/tobe/db/sql-strategy.md                           | NÃO                 |
| 1.5   | database-design-tobe.md                       | schema-inventory.md                        | outputs/asis/db/schema-inventory.md                       | NÃO                 |
| 1.5   | database-design-tobe.md                       | er-diagram.mmd                             | outputs/asis/db/er-diagram.mmd                            | SIM                  |
| 1.5   | database-design-tobe.md                       | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 1.5   | database-design-tobe.md                       | stored-procedures-map.md                   | outputs/asis/db/stored-procedures-map.md                  | NÃO                 |
| 1.6   | security-design-tobe.md                       | ADR-003-security.md                        | outputs/tobe/docs/decisions/ADR-003-security.md           | SIM                  |
| 1.6   | security-design-tobe.md                       | security-map.md                            | outputs/asis/security-map.md                              | NÃO                 |
| 1.6   | security-design-tobe.md                       | vulnerabilities.md                         | outputs/asis/vulnerabilities.md                           | NÃO                 |
| 1.6   | security-design-tobe.md                       | compliance-gaps.md                         | outputs/asis/compliance-gaps.md                           | NÃO                 |
| 1.6   | security-design-tobe.md                       | gap-register.json                          | outputs/asis/gap-register.json                            | NÃO                 |
| 1.6   | security-design-tobe.md                       | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 2     | architecture-technical-tobe.md                | ADR-001-greenfield-rewrite.md              | outputs/tobe/docs/decisions/ADR-001-greenfield-rewrite.md | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-002-database.md                        | outputs/tobe/docs/decisions/ADR-002-database.md           | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-003-security.md                        | outputs/tobe/docs/decisions/ADR-003-security.md           | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-004-backend.md                         | outputs/tobe/docs/decisions/ADR-004-backend.md            | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-005-frontend.md                        | outputs/tobe/docs/decisions/ADR-005-frontend.md           | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-006-integration.md                     | outputs/tobe/docs/decisions/ADR-006-integration.md        | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-007-observability.md                   | outputs/tobe/docs/decisions/ADR-007-observability.md      | SIM                  |
| 2     | architecture-technical-tobe.md                | ADR-008-audit-log.md                       | outputs/tobe/docs/decisions/ADR-008-audit-log.md          | SIM                  |
| 2     | architecture-technical-tobe.md                | INDEX.md (ADRs)                            | outputs/tobe/docs/decisions/INDEX.md                      | SIM                  |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | tech-framework-document.md                 | outputs/tobe/docs/tech-framework-document.md              | NÃO                 |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | bounded-context-map.md (AS-IS)             | outputs/asis/bounded-context-map.md                       | SIM                  |
| 2.5   | migration-plan-tobe.md (trigger backlog-tobe) | db/ (Database Design TO-BE, dir)           | outputs/tobe/db/                                          | SIM                  |
| 2.7   | migration-plan-tobe.md (trigger WM)           | inventory-report.md                        | outputs/asis/inventory-report.md                          | NÃO                 |
| 2.7   | migration-plan-tobe.md (trigger WM)           | api-map.md                                 | outputs/asis/api-map.md                                   | SIM                  |
| 2.7   | migration-plan-tobe.md (trigger WM)           | data-structure.md                          | outputs/asis/db/data-structure.md                            | SIM                  |
| 2.7   | migration-plan-tobe.md (trigger WM)           | bounded-context-map.md (AS-IS)             | outputs/asis/bounded-context-map.md                       | SIM                  |
| 2.7   | migration-plan-tobe.md (trigger WM)           | gaps-risks-report.md                       | outputs/asis/gaps-risks-report.md                         | NÃO                 |
| 2.7   | migration-plan-tobe.md (trigger WM)           | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 2.7   | migration-plan-tobe.md (trigger WM)           | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 2.7   | migration-plan-tobe.md (trigger WM)           | bounded-context-map.md (TO-BE)             | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 3     | measure-size-tobe.md                          | backlog-tobe.md                            | outputs/tobe/docs/backlog-tobe.md                         | NÃO                 |
| 3     | measure-size-tobe.md                          | wave-model.json                            | outputs/tobe/migration/wave-model.json                    | NÃO                 |
| 3     | measure-size-tobe.md                          | inventory-report.md                        | outputs/asis/inventory-report.md                          | NÃO                 |
| 3     | measure-size-tobe.md                          | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 4     | migration-plan-tobe.md (main)                 | wave-model.json                            | outputs/tobe/migration/wave-model.json                    | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | sizing-report.md                           | outputs/tobe/docs/sizing-report.md                        | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 4     | migration-plan-tobe.md (main)                 | gaps-risks-report.md                       | outputs/asis/gaps-risks-report.md                         | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | backlog-tobe.md                            | outputs/tobe/docs/backlog-tobe.md                         | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | integration-matrix.md                      | outputs/tobe/docs/integration-matrix.md                   | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | tshirt-sizing-rationale.md                 | outputs/tobe/docs/tshirt-sizing-rationale.md              | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | migration-priority-matrix.md               | outputs/tobe/migration/migration-priority-matrix.md       | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 4     | migration-plan-tobe.md (main)                 | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 4     | migration-plan-tobe.md (main)                 | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 4     | migration-plan-tobe.md (main)                 | tech-framework-document.md                 | outputs/tobe/docs/tech-framework-document.md              | NÃO                 |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | wave-plan.md                               | outputs/tobe/docs/wave-plan.md                            | NÃO                 |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | migration-activity-plan.md                 | outputs/tobe/migration/migration-activity-plan.md         | NÃO                 |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | migration-priority-matrix.md               | outputs/tobe/migration/migration-priority-matrix.md       | NÃO                 |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | pilot-metrics.md                           | outputs/tobe/migration/pilot-metrics.md                   | NÃO                 |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | strategy-align-feedback.md                 | outputs/tobe/migration/strategy-align-feedback.md         | NÃO                 |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 4.2   | migration-plan-tobe.md (trigger WCR)          | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 4.3   | coexistence-strategy-tobe.md                  | wave-model.json                            | outputs/tobe/migration/wave-model.json                    | NÃO                 |
| 4.3   | coexistence-strategy-tobe.md                  | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 4.3   | coexistence-strategy-tobe.md                  | integration-matrix.md                      | outputs/tobe/docs/integration-matrix.md                   | NÃO                 |
| 4.3   | coexistence-strategy-tobe.md                  | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 4.3   | coexistence-strategy-tobe.md                  | db-analysis-report.md                      | outputs/asis/db/db-analysis-report.md                        | NÃO                 |
| 4.3   | coexistence-strategy-tobe.md                  | events-pubsub-inventory.md                 | outputs/asis/events-pubsub-inventory.md                   | NÃO                 |
| 4.3   | coexistence-strategy-tobe.md                  | gap-register.json                          | outputs/asis/gap-register.json                            | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | wave-model.json                            | outputs/tobe/migration/wave-model.json                    | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | integration-matrix.md                      | outputs/tobe/docs/integration-matrix.md                   | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | tshirt-sizing-rationale.md                 | outputs/tobe/docs/tshirt-sizing-rationale.md              | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | ai-estimation-report.md                    | outputs/tobe/docs/ai-estimation-report.md                 | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | manual-gap-list.md                         | outputs/tobe/docs/manual-gap-list.md                      | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | migration-executive-summary.md             | outputs/tobe/docs/migration-executive-summary.md          | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | migration-plan.md                          | outputs/tobe/docs/migration-plan.md                       | SIM                  |
| 4.5   | risk-mitigation-tobe.md                       | wave-plan.md                               | outputs/tobe/docs/wave-plan.md                            | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | ado-work-items.md                          | outputs/tobe/docs/ado-work-items.md                       | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | migration-gantt.mmd                        | outputs/tobe/diagrams/migration-gantt.mmd                 | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | migration-activity-plan.md                 | outputs/tobe/migration/migration-activity-plan.md         | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | activity-dependency-graph.md               | outputs/tobe/migration/activity-dependency-graph.md       | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | migration-priority-matrix.md               | outputs/tobe/migration/migration-priority-matrix.md       | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | coexistence-strategy.md                    | outputs/tobe/docs/coexistence-strategy.md                 | SIM                  |
| 4.5   | risk-mitigation-tobe.md                       | coexistence-matrix.md                      | outputs/tobe/docs/coexistence-matrix.md                   | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | coexistence-architecture.mmd               | outputs/tobe/diagrams/coexistence-architecture.mmd        | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | risk-register.json                         | outputs/asis/risk-register.json                           | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | gap-list-report.md                         | outputs/asis/gap-list-report.md                           | NÃO                 |
| 4.5   | risk-mitigation-tobe.md                       | security-map.md                            | outputs/asis/security-map.md                              | NÃO                 |
| 4.6   | gaps-risks-asis.md (`@ava-asis-gaps-risks`) | risk-register.json                         | outputs/asis/risk-register.json                           | NÃO                 |
| 4.6   | gaps-risks-asis.md (`@ava-asis-gaps-risks`) | risk-mitigation-plan.md                    | outputs/tobe/risk-mitigation-plan.md                      | NÃO                 |
| 4.61  | openapi-spec-tobe.md                          | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 4.61  | openapi-spec-tobe.md                          | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 4.61  | openapi-spec-tobe.md                          | ADR-004-backend.md                         | outputs/tobe/docs/decisions/ADR-004-backend.md            | SIM                  |
| 4.7   | coder-dotnet.md                               | tech-framework-document.md                 | outputs/tobe/docs/tech-framework-document.md              | NÃO                 |
| 4.7   | coder-dotnet.md                               | patterns-applied.json                      | outputs/tobe/patterns-applied.json                        | NÃO                 |
| 4.7   | coder-dotnet.md                               | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 4.7   | coder-dotnet.md                               | ADR-004-backend.md                         | outputs/tobe/docs/decisions/ADR-004-backend.md            | SIM                  |
| 4.7   | coder-dotnet.md                               | docs-research-bundle.md                    | outputs/tobe/docs/research/docs-research-bundle.md        | NÃO                 |
| 5     | docs-tobe.md (trigger OA)                     | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 5     | docs-tobe.md (trigger OA)                     | migration-plan.md                          | outputs/tobe/docs/migration-plan.md                       | SIM                  |
| 5.2   | docs-tobe.md (trigger RN)                     | business-rules.md                          | outputs/asis/docs/business-rules.md                       | SIM                  |
| 5.2   | docs-tobe.md (trigger RN)                     | functional-requirements.md                 | outputs/asis/docs/functional-requirements.md              | SIM                  |
| 5.2   | docs-tobe.md (trigger RN)                     | screen-rules.md                            | outputs/asis/docs/screen-rules.md                         | SIM                  |
| 5.2   | docs-tobe.md (trigger RN)                     | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 5.2   | docs-tobe.md (trigger RN)                     | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 5.1   | developer-guide-tobe.md                       | tech-framework-document.md                 | outputs/tobe/docs/tech-framework-document.md              | NÃO                 |
| 5.1   | developer-guide-tobe.md                       | coding-standards.md                        | outputs/tobe/coding-standards.md                          | NÃO                 |
| 5.1   | developer-guide-tobe.md                       | solution-structure.md                      | outputs/tobe/solution-structure.md                        | NÃO                 |
| 5.1   | developer-guide-tobe.md                       | nuget-packages.md                          | outputs/tobe/nuget-packages.md                            | NÃO                 |
| 6     | test-plan-tobe.md (trigger TP)                | bounded-context-map.md                     | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 6     | test-plan-tobe.md (trigger TP)                | regras-negocio.md (fallback: business-rules.md) | outputs/asis/docs/regras-negocio.md                       | SIM                  |
| 6     | test-plan-tobe.md (trigger TP)                | wave-plan.md                               | outputs/tobe/docs/wave-plan.md                            | NÃO                 |
| 6     | test-plan-tobe.md (trigger TP)                | architecture-blueprint.md                  | outputs/tobe/docs/architecture-blueprint.md               | NÃO                 |
| 6     | test-plan-tobe.md (trigger TP)                | tech-framework-document.md                 | outputs/tobe/docs/tech-framework-document.md              | NÃO                 |
| 6     | test-plan-tobe.md (trigger TP)                | security-architecture.md                   | outputs/tobe/docs/security-architecture.md                | NÃO                 |
| 6     | test-plan-tobe.md (trigger TP)                | coexistence-strategy.md                    | outputs/tobe/docs/coexistence-strategy.md                 | SIM                  |
| 6     | test-plan-tobe.md (trigger TP)                | risk-mitigation-plan.md                    | outputs/tobe/risk-mitigation-plan.md                      | NÃO                 |
| 6     | test-plan-tobe.md (trigger TP)                | user-journeys-report.md                    | outputs/tobe/user-journeys/user-journeys-report.md        | NÃO                 |
| 7.5   | designer-system-tobe.md (trigger DS)          | ADR-005-frontend.md                        | outputs/tobe/docs/decisions/ADR-005-frontend.md           | SIM                  |
| 7.5   | designer-system-tobe.md (trigger DS)          | user-journeys-report.md                    | outputs/tobe/user-journeys/user-journeys-report.md        | NÃO                 |
| 7.5   | designer-system-tobe.md (trigger DS)          | bounded-context-map.md (fallback)          | outputs/tobe/docs/bounded-context-map.md                  | SIM                  |
| 7.5   | designer-system-tobe.md (trigger DS)          | screen-flow.md                             | outputs/asis/docs/screen-flow.md                          | NÃO                 |

**Totais**: 138 linhas · 70 SIM · 68 NÃO.

> Nota: as linhas da Fase 7.8 (`test-plan-consolidated-tobe.md`) foram removidas após a
> unificação do agente `ava-test-plan-tobe` v5.0.0, que agora consome os mesmos artefatos
> enriquecedores diretamente na Fase 6.

## 3. Observações

**1. O padrão dominante não é "fase ainda não executada" — é divergência de path/nome entre o
que `orchestrator-tobe.md` v2.4.0 declara e o que este projeto efetivamente gravou em disco.**
O projeto claramente passou por um pipeline TO-BE completo — `outputs/tobe/` contém
`architecture-blueprint.md`, `architecture-technical.md`, `migration-plan.md`,
`coexistence-strategy.md`, `wave-model.json`, `risk-mitigation.md`, `design-system.md`,
`user-journeys.md`, `test-plan-consolidated.md`, `database-policy.md`, código-fonte gerado em
`source-code/`, etc. — mas quase nenhum desses arquivos está no path/nome que o orquestrador atual
espera:

| O que o orquestrador declara                           | O que existe de fato no projeto                                          |
| ------------------------------------------------------ | ------------------------------------------------------------------------ |
| `outputs/tobe/docs/architecture-blueprint.md`        | `outputs/tobe/architecture-blueprint.md` (sem `docs/`)               |
| `outputs/tobe/migration/wave-model.json`             | `outputs/tobe/docs/wave-model.json` (sem `migration/`)               |
| `outputs/tobe/docs/tech-framework-document.md`       | `outputs/tobe/docs/architecture-technical.md` (nome diferente)         |
| `outputs/tobe/risk-mitigation-plan.md`               | `outputs/tobe/docs/risk-mitigation.md` (path e nome diferentes)        |
| `outputs/tobe/designer-system.md`                    | `outputs/tobe/docs/design-system.md` (path e nome diferentes)          |
| `outputs/tobe/user-journeys/user-journeys-report.md` | `outputs/tobe/docs/user-journeys.md` (path e nome diferentes)          |
| `outputs/tobe/qa/test-plan.md`                          | `outputs/tobe/docs/test-plan-consolidated.md` (path e nome diferentes) |
| `outputs/tobe/db/sql-strategy.md`                    | `outputs/tobe/docs/database-policy.md` (path e nome diferentes)        |
| `outputs/tobe/docs/db-design-report.md`              | `outputs/tobe/db/database-design.md` (path e nome diferentes)          |

Toda a subárvore `outputs/tobe/migration/` — de onde 8 dos 9 artefatos de `migration-plan-tobe.md`
das Fases 2.7/4 deveriam vir (`wave-model.json`, `integration-matrix.md`,
`tshirt-sizing-rationale.md`, `migration-priority-matrix.md`, `migration-activity-plan.md`,
`activity-dependency-graph.md`, `pilot-metrics.md`, `strategy-align-feedback.md`) — **não existe
no projeto**; isso sozinho é responsável por 15 das 85 linhas NÃO desta tabela. Da mesma forma,
`outputs/tobe/tests/` (4 linhas NÃO na Fase 7.8) e o diretório AS-IS `outputs/asis/db/` com os
nomes esperados (`schema-inventory.md`, `stored-procedures-map.md`, `triggers-map.md` — 5 linhas
NÃO nas Fases 1.4/1.5) também estão ausentes, embora artefatos AS-IS equivalentes existam sob
outros nomes (`outputs/asis/db/db-analysis.md`, `outputs/asis/inventory.md`,
`outputs/asis/risk-register.md`, `outputs/asis/events-pubsub.md`). Isso sugere fortemente que o
projeto foi gerado por uma versão anterior (ou uma variante experimental — o nome do projeto
referencia "AST-LLM", consistente com o trabalho recente de `specs/012-solution-delphi-ast-analyzer-config-path`
e a integração AST+LLM no AS-IS) do pipeline, cujas convenções de path divergiam
significativamente das atuais.

**2. Cruzamento com bugs já documentados em `docs/tobe-architecture-io-map.md` §4:**

- **§4.7** (`outputs/asis/docs/screen-flow.md` referenciado mas nunca produzido) — **confirmado
  neste projeto**: a linha Fase 7.5 / `designer-system-tobe.md` / `screen-flow.md` é NÃO, e o
  AS-IS realmente produziu `outputs/asis/docs/screen-flow.mmd` (não `.md`) — exatamente a
  discrepância descrita no §4.7. Não é uma falha deste projeto; é um path que **nunca** resolveria
  em nenhum projeto, em qualquer estágio do pipeline.
- **§4.6** (`test-plan-tobe.md` exige `architecture-technical.md`, que nenhum agente produz porque
  `architecture-technical-tobe.md` grava `tech-framework-document.md`) — este projeto tem, de
  fato, um arquivo chamado `outputs/tobe/docs/architecture-technical.md` em disco, o que é uma
  evidência concreta de que uma versão anterior do agente realmente gravava sob esse nome — a
  migração de nome para `tech-framework-document.md` (refletida nas 9 linhas ADR/INDEX + demais
  linhas "tech-framework-document.md" desta tabela, todas NÃO) é o que quebrou a compatibilidade
  para este projeto específico.
- **§4.4** (`risk-mitigation-tobe.md` esperava `outputs/tobe/migration-plan.md` sem `docs/`,
  corrigido em `specs/016-tobe-artifact-only-guardrail` para `outputs/tobe/docs/migration-plan.md`)
  — a correção está confirmada em vigor: a linha Fase 4.5 / `migration-plan.md` usa o path
  corrigido (`outputs/tobe/docs/migration-plan.md`) e resolve **SIM** neste projeto.
- **§4.3** (Fases 7 e 8 sem seção própria) — confirmado durante a extração: não há bloco
  `### Fase 7 —` nem `### Fase 8 —` em `orchestrator-tobe.md` v2.4.0, então nenhuma linha desta
  tabela é atribuída a essas duas fases (consistente com a ausência total de tabela de Inputs para
  elas).

**3. Artefatos AS-IS genuinamente ausentes (não é problema de nome/path — o artefato realmente
não foi gerado para este projeto):** `outputs/asis/gaps-risks-report.md` (bloqueante em 3 fases
diferentes: 0-Pre, 2.7 e 4 — mesmo path, sempre NÃO), `outputs/asis/security-map.md`,
`outputs/asis/vulnerabilities.md`, `outputs/asis/compliance-gaps.md`, `outputs/asis/gap-register.json`
e `outputs/asis/risk-register.json` (usado em `.json`, enquanto o projeto tem apenas
`outputs/asis/risk-register.md`) não têm equivalente sob nenhum nome na árvore `outputs/asis/`
deste projeto — sugerindo que o diagnóstico de segurança/riscos AS-IS (gaps-risks-asis,
security-map) rodou com um escopo/versão que não gerou esses artefatos específicos, e não apenas
um problema de nomenclatura.

**4. Não é sinal de problema — apenas fase ainda não alcançada / não aplicável a este projeto:**
os artefatos condicionais da Fase 4.2 (`pilot-metrics.md`, `strategy-align-feedback.md` — a fase é
explicitamente condicional a um PILOT ou feedback do usuário, nenhum dos dois presente) e os
diretórios `outputs/tobe/user-journeys/`, `outputs/tobe/strategy-align/` (não fazem parte do
escopo desta tabela) são esperados estarem ausentes independentemente de qual convenção de path
esteja em vigor.

## 4. Fechamento — `specs/017-tobe-path-corrections`

Investigação de acompanhamento (2 varreduras cruzando cada path referenciado nesta tabela contra
o `## Output Contract` real do respectivo agente produtor — não contra o layout físico do projeto
008, que se confirmou ser de uma convenção de path **anterior** à consolidação atual dos specs)
concluiu que a esmagadora maioria das 85 linhas "NÃO" **não são bugs de path** — são artefatos que
este projeto específico simplesmente nunca gerou (fases não executadas, diagnóstico AS-IS de
segurança/risco incompleto), ou correspondem a paths que já batem exatamente com o Output
Contract atual do agente produtor (o projeto 008 é que está desatualizado nesses casos, ex.:
`architecture-blueprint.md`, `sql-strategy.md`, `risk-mitigation-plan.md`, `designer-system.md`,
`user-journeys-report.md`, `tech-framework-document.md`).

Apenas **7 referências eram bugs genuínos** (path que não bate com nenhum produtor atual, ou
extensão/segmento de diretório errado) — todas corrigidas em `specs/017-tobe-path-corrections`:
`outputs/asis/db/triggers-map.md` (sem produtor — documentado como lacuna permanente, não
corrigível por redirecionamento), `outputs/asis/docs/screen-flow.md` → `.mmd`,
`outputs/asis/docs/test-plan.md` → `outputs/asis/qa/test-plan.md`,
`outputs/tobe/docs/architecture-technical.md` → `outputs/tobe/docs/tech-framework-document.md`
(15 ocorrências em `test-plan-tobe.md`), `outputs/tobe/architecture-design.md` e
`outputs/tobe/architecture-design-tobe.md` → `outputs/tobe/docs/architecture-blueprint.md`, e
`outputs/tobe/docs/test-plan-tobe.md` → `outputs/tobe/qa/test-plan.md`. Ver `docs/tobe-architecture-io-map.md`
§4.6–§4.9, §4.11, §4.16–§4.17 para o detalhamento por bug.
