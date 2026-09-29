# AVA Fabric Agents — Catálogo de Agentes

**Versão:** 1.5  
**Data:** 2026-07-07  
**Total de agentes:** 53

> Catálogo completo de todos os agentes do AVA Fabric, organizados por fase da esteira de migração.  
> Cada agente é um arquivo `.md` em `src/modules/ava-fabric-agents/` que pode ser invocado diretamente pelo Claude Code.

---

## Índice

- [Visão Geral da Esteira](#visão-geral-da-esteira)
- [F1 — AS-IS Diagnostic](#f1--as-is-diagnostic)
- [F2 — TO-BE Architecture](#f2--to-be-architecture)
- [F3 — Prototype](#f3--prototype)
- [F4 — Tech Stack](#f4--tech-stack)
- [F5 — QA Agents](#f5--qa-agents)
- [F6 — DevOps](#f6--devops)
- [F7 — Deliverables](#f7--deliverables)
- [F8 — Summary (cross-cutting, executado após cada fase)](#f8--summary)
- [Convenções e Contratos](#convenções-e-contratos)

---

## Visão Geral da Esteira

```
projects/{PROJECT_NAME}/inputs/
  └─ código-fonte legado (Delphi, COBOL, VB6...)

F1 ─── AS-IS Diagnostic        ─── 8 agentes  →  projects/{PROJECT_NAME}/outputs/asis/
F2 ─── TO-BE Architecture       ─── 12 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/
F3 ─── Prototype                ─── 1 agente   →  projects/{PROJECT_NAME}/outputs/tobe/prototype/
F4 ─── Tech Stack               ─── 3 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/source-code/
F5 ─── QA Agents                ─── 10 agentes  →  projects/{PROJECT_NAME}/outputs/qa/
F6 ─── DevOps                   ─── 5 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/iac/
F7 ─── Deliverables             ─── 7 agentes  →  projects/{PROJECT_NAME}/outputs/deliverables/
F8 ─── Summary (cross-cutting)  ─── 2 agentes  →  projects/{PROJECT_NAME}/outputs/summary/
```

---

## F1 — AS-IS Diagnostic

Fase de diagnóstico completo do sistema legado. O orchestrator coordena os sub-agentes em duas waves — Wave 1 (agente de solução + segurança, imediato) → Solution Agent Gate → Wave 2 (6 agentes, dependentes dos artefatos do agente de solução) — e consolida os resultados no Master Report.

### `ava-asis-orchestrator`

| Campo       | Valor                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` |
| **Papel**   | Coordenador da esteira de diagnóstico AS-IS                                 |
| **Trigger** | Ponto de entrada da fase F1                                                 |

**Responsabilidades:**

- Valida o repositório legado de entrada
- Detecta tecnologia (Delphi, COBOL, VB6)
- Despacha o agente de solução (leitura via AST) primeiro; interrompe a esteira e alerta o usuário se ele não gerar os artefatos obrigatórios
- Dispara os demais sub-agentes somente após o agente de solução completar com sucesso
- Consolida resultados no `master-report.md`
- Executa quality gate antes de liberar para F2

**Input:**

```yaml
repository_path: string # caminho do repositório legado
legacy_technology: string # "delphi" | "cobol" | "vb6"
project_name: string
```

**Output:**

```yaml
master_report: projects/{PROJECT_NAME}/outputs/asis/master-report.md
trace_id: string
sub_reports: string[] # paths de cada relatório parcial
```

---

### `ava-asis-solution-delphi`

| Campo       | Valor                                                                     |
| ----------- | ------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md` |
| **Papel**   | Análise estática do código Delphi/Pascal                                  |

**Responsabilidades:**

- Classifica padrões arquiteturais: SmartUI, DataModule, Two-Tier, Rich Domain
- Gera diagramas C4 (Context, Container, Component)
- Mapeia bounded contexts e módulos funcionais
- Extrai API map (forms, eventos, dependências)
- Gera diagramas de classe e sequência

**Output:**

```yaml
architecture_blueprint: projects/{PROJECT_NAME}/outputs/asis/architecture-blueprint.md
c4_context: projects/{PROJECT_NAME}/outputs/asis/diagrams/c4-context.mmd
c4_container: projects/{PROJECT_NAME}/outputs/asis/diagrams/c4-container.mmd
c4_component: projects/{PROJECT_NAME}/outputs/asis/diagrams/c4-component.mmd
seq_diagrams: projects/{PROJECT_NAME}/outputs/asis/diagrams/seq-*.mmd
api_map: projects/{PROJECT_NAME}/outputs/asis/api-map.md
```

---

### `ava-asis-db-analyzer`

| Campo       | Valor                                                                             |
| ----------- | --------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md` |
| **Papel**   | Análise completa do banco de dados legado                                         |

**Sub-skills por SGBD:**

- `ava-db-mysql` — `skills/mysql-agent.md`
- `ava-db-sqlserver` — `skills/sqlserver-agent.md`
- `ava-db-oracle` — `skills/oracle-agent.md`
- `ava-db-mariadb` — `skills/mariadb-agent.md`

**Responsabilidades:**

- Detecta o SGBD automaticamente
- Reconstrói schema via análise estática
- Gera diagrama ER em Mermaid
- Identifica lógica de negócio em SQL, SPs e triggers
- Avalia qualidade do schema (tipos, integridade, auditoria)

**Output:**

```yaml
db_type: projects/{PROJECT_NAME}/outputs/asis/db/db-type.json
schema_inventory: projects/{PROJECT_NAME}/outputs/asis/db/schema-inventory.md
er_diagram: projects/{PROJECT_NAME}/outputs/asis/db/er-diagram.mmd
stored_procs_map: projects/{PROJECT_NAME}/outputs/asis/db/stored-procedures-map.md
biz_logic_in_db: projects/{PROJECT_NAME}/outputs/asis/db/business-logic-in-db.md
db_quality: projects/{PROJECT_NAME}/outputs/asis/db/db-quality-report.md
```

---

### `ava-asis-security-review`

| Campo       | Valor                                                                          |
| ----------- | ------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/security-review-asis.md` |
| **Papel**   | Security engineer — OWASP e compliance LGPD                                    |

**Responsabilidades:**

- Mapeia vulnerabilidades por categoria OWASP (SQL Injection, credenciais expostas, etc.)
- Identifica dados PII sem proteção (LGPD Arts. 46–48)
- Avalia ausência de autenticação, autorização e auditoria
- Calcula score de segurança por dimensão

**Output:**

```yaml
security_map: projects/{PROJECT_NAME}/outputs/asis/security-map.md
vulnerabilities: projects/{PROJECT_NAME}/outputs/asis/vulnerabilities.md
compliance_gaps: projects/{PROJECT_NAME}/outputs/asis/compliance-gaps.md
```

---

### `ava-asis-documentation` (v3.0.0)

| Campo       | Valor                                                                        |
| ----------- | ---------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md` |
| **Papel**   | Extração de regras de negócio, requisitos funcionais, e mapeamento de fluxo de telas (Screen Flow Mapper) |

**Responsabilidades:**

- Mapeia cadeia de valor e fluxos principais
- Documenta telas e navegação
- **Screen Flow Mapper (v3.0.0)**: gera diagramas de fluxo de tela por bounded context com assertion de completude (protocolo de lotes para projetos > 80 forms)

> Extração de regras de negócio (RNs) e requisitos funcionais (RFs) foi movida para
> `ava-asis-business-rules-generator` (ver abaixo) — `ava-asis-documentation` não produz
> mais `business-rules.md`.

**Output:**

```yaml
value_chain: projects/{PROJECT_NAME}/outputs/asis/docs/value-chain.md
screen_flow: projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow.md
screen_flow_bc_artifacts: projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow-*.mmd  # intermediários por BC (v3.0.0)
completeness_assertion: projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow-completeness.json  # PASS/FAIL com coverage_pct (v3.0.0)
```

---

### `ava-asis-business-rules-generator`

| Campo       | Valor                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/business-rules-generator-agent.md`         |
| **Papel**   | Curadoria semiântica de `10_business_rule_cases.json` em regras de negócio e requisitos funcionais consolidados |

**Responsabilidades:**

- Cura regras de negócio do catálogo AST (`10_business_rule_cases.json`), infere bounded contexts e prioridade
- Deriva requisitos funcionais (FRs) agrupando regras coesas por bounded context
- Gera `business-rules.md` (Formato A — section headers `BR-000N`/`FR-000N`) e seu espelho `business-rules.json`
- Remove os arquivos temporários de `work_dir` (`ast-raw/{language}/tmp/`) após confirmar os artefatos finais

**Output:**

```yaml
business_rules_md: projects/{PROJECT_NAME}/outputs/asis/docs/business-rules.md  # unificado: contém ## Functional Requirements + ## Business Rules
business_rules_json: projects/{PROJECT_NAME}/outputs/asis/docs/business-rules.json  # espelho JSON determinístico do .md
```

---

### `ava-asis-inventory`

| Campo       | Valor                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/inventory-asis.md` |
| **Papel**   | Inventário quantitativo e métricas do sistema legado                     |

**Responsabilidades:**

- Conta LOC, arquivos, métodos, classes por módulo
- Mapeia complexidade ciclomática estimada
- Gera mapa de dependências entre componentes

**Output:**

```yaml
inventory_report: projects/{PROJECT_NAME}/outputs/asis/inventory-report.md
metrics_json: projects/{PROJECT_NAME}/outputs/asis/metrics.json
complexity_map: projects/{PROJECT_NAME}/outputs/asis/complexity-map.md
```

---


### `ava-asis-gaps-risks`

| Campo       | Valor                                                                     |
| ----------- | ------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/gaps-risks-asis.md` |
| **Papel**   | Consolidador de gaps e risk register — último a executar em F1            |

**Responsabilidades:**

- Agrega findings de todos os 7 agentes AS-IS
- Calcula Risk Score: `Probabilidade × Impacto` (máx 25)
- Classifica riscos em P0 (bloqueante), P1 (crítico), P2 (alto), P3 (baixo)
- Gera recomendação de estratégia de migração por wave

**Output:**

```yaml
gaps_risks_report: projects/{PROJECT_NAME}/outputs/asis/gaps-risks-report.md
risk_register: projects/{PROJECT_NAME}/outputs/asis/risk-register.json
migration_risks: projects/{PROJECT_NAME}/outputs/asis/migration-risks-summary.md
```

---

## F2 — TO-BE Architecture

Fase de design da solução alvo em .NET 10. Recebe o `master-report.md` da F1 como entrada principal.

### `ava-tobe-orchestrator`

| Campo         | Valor                                                                         |
| ------------- | ----------------------------------------------------------------------------- |
| **Arquivo**   | `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` |
| **Versão**    | `2.5.0`                                                                       |
| **Papel**     | Coordenador da esteira TO-BE                                                  |
| **Trigger**   | Input: artefatos essenciais AS-IS (`bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md`); `master-report.md` é opcional (aviso não-bloqueante se ausente) |

**Responsabilidades:**

- Garante que o design TO-BE é coerente com o diagnóstico AS-IS
- Sequencia blueprint → technical → sizing → migration plan → codegen → docs → tests
- Executa Fase 8.1 (Readiness Gate Wave 1) após Azure Infra Estimator como gate humano pré-Build Cycle
- Executa quality gate antes de liberar para F3

---

### `ava-tobe-adr`

| Campo       | Valor                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/adr-tobe.md`     |
| **Papel**   | Phase 0 — materializa os 8 ADRs obrigatórios (Nygard) antes do Blueprint |

**Responsabilidades:**

- Deriva conteúdo de `shared-context.md` + artefatos AS-IS + `project-config.yaml`
- Gera ADR-001 (stack) · ADR-002 (BD) · ADR-003 (auth) · ADR-004 (CQRS) · ADR-005 (DDD) · ADR-006 (observability) · ADR-007 (LGPD) · ADR-008 (migration)
- Sobrescreve incondicionalmente arquivos existentes em `docs/decisions/`

**Output:**

```yaml
adrs: projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-{001..008}-*.md
index: projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/INDEX.md
```

---

### `ava-tobe-adr`

| Campo       | Valor                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/adr-tobe.md`     |
| **Papel**   | Phase 0 — materializa os 8 ADRs obrigatórios (Nygard) antes do Blueprint |

**Responsabilidades:**

- Deriva conteúdo de `shared-context.md` + artefatos AS-IS + `project-config.yaml`
- Gera ADR-001 (stack) · ADR-002 (BD) · ADR-003 (auth) · ADR-004 (CQRS) · ADR-005 (DDD) · ADR-006 (observability) · ADR-007 (LGPD) · ADR-008 (migration)
- Sobrescreve incondicionalmente arquivos existentes em `docs/decisions/`

**Output:**

```yaml
adrs: projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-{001..008}-*.md
index: projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/INDEX.md
```

---

### `ava-tobe-architecture-design`

| Campo       | Valor                                                                                |
| ----------- | ------------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-design-tobe.md` |
| **Papel**   | Arquiteto de soluções — DDD, CQRS, Clean Architecture                                |

**Responsabilidades:**

- Define bounded contexts TO-BE derivados do AS-IS
- Gera diagramas C4 TO-BE (Context, Container, Component)
- Mapeia APIs REST por bounded context
- Define estratégia de autenticação (Azure AD B2C / ASP.NET Identity)

**Output:**

```yaml
architecture_blueprint: projects/{PROJECT_NAME}/outputs/tobe/docs/architecture-blueprint.md
c4_diagrams: projects/{PROJECT_NAME}/outputs/tobe/diagrams/
api_map: projects/{PROJECT_NAME}/outputs/tobe/docs/api-map.md
```

---

### `ava-tobe-database-design`

| Campo       | Valor                                                                            |
| ----------- | -------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/database-design-tobe.md` |
| **Papel**   | Fase 1.5 — Database Design TO-BE (após Blueprint, antes de Tech Framework)       |

**Responsabilidades:**

- Deriva engine alvo de `project-config.yaml` (nunca hardcoded)
- Gera DDL normalizado (3NF+) com snake_case, colunas de auditoria e soft delete
- Produz ERD Mermaid `erDiagram` TO-BE
- Gera HTML bilíngue autocontido (PT/EN toggle)

**Output:**

```yaml
db_design_report: projects/{PROJECT_NAME}/outputs/tobe/docs/db-design-report.md
er_diagram: projects/{PROJECT_NAME}/outputs/tobe/diagrams/mer-diagram-tobe.mmd
db_design_html: projects/{PROJECT_NAME}/outputs/tobe/docs/db-design-report.html
```

---

### `ava-tobe-architecture-technical`

| Campo       | Valor                                                                                   |
| ----------- | --------------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-technical-tobe.md` |
| **Papel**   | Tech lead — stack técnica, packages e configuração                                      |

**Responsabilidades:**

- Seleciona e versiona NuGet packages por camada (Domain, Application, Infrastructure, API)
- Define estrutura de pastas da solution
- Especifica appsettings, Key Vault, logging (Application Insights)

**Output:**

```yaml
tech_framework_doc: projects/{PROJECT_NAME}/outputs/tobe/docs/tech-framework-document.md
solution_structure: projects/{PROJECT_NAME}/outputs/tobe/solution-structure.md
nuget_packages: projects/{PROJECT_NAME}/outputs/tobe/nuget-packages.md
```

---

### `ava-tobe-user-journeys`

| Campo       | Valor                                                                          |
| ----------- | ------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/user-journeys-tobe.md` |
| **Papel**   | Jornadas do usuário TO-BE com BDD Gherkin — happy path + sad path por jornada  |

**Responsabilidades:**

- Deriva jornadas dos bounded contexts e fluxos funcionais do AS-IS (quantidade variável)
- Para cada jornada: happy path (fluxo de sucesso) + sad path (falha/regra violada/timeout)
- Gera cenários Gherkin completos (`Feature` / `Scenario` / `Given-When-Then`)
- Produz relatório mestre com rastreabilidade jornada ↔ bounded context ↔ requisito

**Output:**

```yaml
journeys_report: projects/{PROJECT_NAME}/outputs/tobe/user-journeys/user-journeys-report.md
happy_paths: projects/{PROJECT_NAME}/outputs/tobe/user-journeys/happy-path/{slug}-happy-path.feature
sad_paths: projects/{PROJECT_NAME}/outputs/tobe/user-journeys/sad-path/{slug}-sad-path.feature
```

---

### `ava-tobe-measure-size`

| Campo       | Valor                                                                         |
| ----------- | ----------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/measure-size-tobe.md` |
| **Papel**   | Sizing e estimativa de esforço por wave                                       |

**Responsabilidades:**

- Calcula Function Points a partir das métricas AS-IS
- Estima esforço (Story Points) por módulo e wave
- Gera sizing de infraestrutura Azure (SKUs, réplicas, storage)

**Output:**

```yaml
sizing_report: projects/{PROJECT_NAME}/outputs/tobe/docs/sizing-report.md
effort_calc: projects/{PROJECT_NAME}/outputs/tobe/docs/effort-calculator.md
infra_sizing: projects/{PROJECT_NAME}/outputs/tobe/docs/infra-sizing.md
```

---

### `ava-tobe-migration-plan`

| Campo       | Valor                                                                           |
| ----------- | ------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/migration-plan-tobe.md` |
| **Papel**   | Plano de migração por wave com dependências e gates                             |

**Responsabilidades:**

- Define sequência de waves (Wave 0 = pré-migração, Wave N = go-live)
- Ordena módulos por risco × valor (menor risco primeiro)
- Gera Gantt chart em Mermaid
- Define critérios de aceite e rollback por wave

**Output:**

```yaml
migration_plan: projects/{PROJECT_NAME}/outputs/tobe/docs/migration-plan.md
wave_plan: projects/{PROJECT_NAME}/outputs/tobe/docs/wave-plan.md
gantt_chart: projects/{PROJECT_NAME}/outputs/tobe/diagrams/migration-gantt.mmd
```

---

### `ava-coder-dotnet`

| Campo       | Valor                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/coder-dotnet.md` |
| **Papel**   | Geração de código .NET 10 com Clean Architecture, CQRS e DDD             |

**Responsabilidades:**

- Gera entidades de domínio, value objects e domain events
- Implementa Commands, Queries, Handlers (MediatR)
- Gera Repositories com EF Core parametrizado
- Cria testes unitários (xUnit + FluentAssertions + Moq)

**Output:**

```yaml
source_code: projects/{PROJECT_NAME}/outputs/tobe/source-code/
```

---

### `ava-docs-tobe`

| Campo       | Valor                                                                 |
| ----------- | --------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tobe-architecture/agents/docs-tobe.md` |
| **Papel**   | Documentação técnica TO-BE                                            |

**Responsabilidades:**

- Gera spec OpenAPI a partir dos endpoints implementados
- Escreve ADRs (Architecture Decision Records) em `docs/decisions/`
- Produz Technical Design Document (TDD)

**Output:**

```yaml
openapi: projects/{PROJECT_NAME}/outputs/tobe/docs/openapi/
adrs: docs/decisions/
tdd: projects/{PROJECT_NAME}/outputs/tobe/docs/technical-design-document.md
```

---

### `ava-test-plan-tobe`

| Campo       | Valor                                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/test-plan-tobe.md`                             |
| **Papel**   | Plano de testes TO-BE — pirâmide (70/20/10), ferramentas com versões, CI strategy, coverage thresholds |

**Responsabilidades:**

- Define pirâmide de testes (70 % unit / 20 % integration / 10 % E2E) por bounded context
- Especifica tool stack com versões LTS (xUnit · Moq · FluentAssertions · Playwright · k6)
- Documenta ambientes de teste (Local · CI PR Gate · CI Main · Staging · Production)
- Define estratégia de dados de teste (fixtures / factories / Testcontainers)
- Especifica CI strategy — PR gate com condições de bloqueio
- Define thresholds de cobertura por camada (Domain ≥ 90 % / Application ≥ 85 % / Infra+API ≥ 70 %)
- Gera smoke suite para validação pós-deploy
- Especifica plano de carga com k6 (Baseline · Stress · Spike)
- Inclui checklist de aprovação QA Lead

**Output:**

```yaml
test_plan: projects/{PROJECT_NAME}/outputs/tobe/qa/test-plan.md
functional_tests: projects/{PROJECT_NAME}/outputs/tobe/qa/functional-test-matrix.md
traceability_matrix: projects/{PROJECT_NAME}/outputs/tobe/tests/traceability-matrix.md
automatable_cases: projects/{PROJECT_NAME}/outputs/tobe/tests/automatable-test-cases.md
```

---

## F3 — Prototype

> Despachado diretamente pelo `master-orchestrator.md` como fase própria, logo após F2/TO-BE
> concluir (não é mais aninhado dentro do `ava-tobe-orchestrator`).

### `ava-prototype`

| Campo       | Valor                                                                                                                                                                |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`                                                                                                  |
| **Papel**   | Prototipação de UI navegável do sistema TO-BE                                                                                                                        |
| Campo       | Valor                                                                                                                                                                |
| ----------- | -------------------------------------------------------------------------------------------                                                                          |
| **Arquivo** | `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`                                                                                                  |
| **Versão**  | `1.2.0`                                                                                                                                                              |
| **Papel**   | Prototipação de UI navegável do sistema TO-BE com UX heurísticas, validação de formulários, suporte a artefatos opcionais com aviso de confirmação e log de execução |

**Responsabilidades:**

- Gera HTML navegável autocontido com UX baseada nas 10 heurísticas de Nielsen-Norman (H1–H10)
- Implementa validação de formulários client-side via Constraint Validation API (sem CDN)
- Inclui padrões de mensagem de erro em 3 camadas (modal, toast, inline banner)
- Gera especificação Figma com `## UX Heuristics Checklist` (H1–H10 × telas)
- Escreve roteiro de demonstração com seções `## Cenários de Erro (CA03)` e `## Atalhos de Teclado (H7)`
- Suporta `business-rules.md` (seção `## Functional Requirements`) como input opcional para enriquecer labels e validações

**Output:**

```yaml
prototype: projects/{PROJECT_NAME}/outputs/tobe/prototype/
index_html: projects/{PROJECT_NAME}/outputs/tobe/prototype/index.html
demo_script: projects/{PROJECT_NAME}/outputs/tobe/prototype/demo-script.md
figma_spec: projects/{PROJECT_NAME}/outputs/tobe/prototype/figma-spec.md
screen_list: projects/{PROJECT_NAME}/outputs/tobe/prototype/screen-list.md
```

---

## F4 — Tech Stack

Fase de implementação de código por tecnologia. Recebe o blueprint TO-BE e gera código pronto para revisão.

### `ava-stack-orchestrator`

| Campo       | Valor                                                                   |
| ----------- | ----------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` |
| **Papel**   | Coordenador da camada de implementação                                  |

Coordena `ava-stack-dotnet-backend` e `ava-stack-angular-frontend` garantindo consistência entre os contratos de API.

---

### `ava-stack-dotnet-backend`

| Campo       | Valor                                                                     |
| ----------- | ------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |
| **Versão**  | `1.0.1`                                                                   |
| **Papel**   | Desenvolvedor C# sênior — ASP.NET Core + Clean Architecture               |

**Responsabilidades:**

- Implementa controllers REST com validação (FluentValidation)
- Configura EF Core com migrations
- Implementa Unit of Work e Repository Pattern
- Configura autenticação JWT / Azure AD
- **LGPD PII Compliance Guardrail** (v1.1.0+): verifica masking em ILogger (LGPD-01), audit log por entidade com PII (LGPD-02), RBAC em `/anonymize`/`/delete-data` (LGPD-03), DTO exposure warning (LGPD-04)
- Suporta `persistence.multi_tenancy.enabled: true` — gera scaffolding Finbuckle.MultiTenant completo (TenantResolutionMiddleware, {BCName}DbContext MT variant, KeyVaultTenantConnectionStringResolver)
- Guardrail G10 (Clean Architecture anti-patterns SRP/DIP) e verificação pós-geração adicionados (PBI 2274)

**Output:**

```yaml
source_code: projects/{project_name}/outputs/tobe/source-code/{module}/
test_code: projects/{project_name}/outputs/tobe/source-code/{module}.Tests/
migrations: projects/{project_name}/outputs/tobe/source-code/Migrations/
```

---

### `ava-stack-angular-frontend`

| Campo       | Valor                                                                                                                                                                                                                                                               |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`                                                                                                                                                                                         |
| **Versão**  | `3.0.0`                                                                                                                                                                                                                                                             |
| **Papel**   | Desenvolvedor Angular 17+ — TypeScript strict, standalone components. Converte o protótipo navegável da Fase 3 em componentes: **uma página por tela**, não por bounded context. Artefatos do protótipo são opcionais — a ausência degrada com WARN (P2C-W001..W004), nunca bloqueia. |

**Responsabilidades:**

- **Conversão P2C** — lê `index.html` + `screen-list.md` do protótipo, deriva o inventário de telas em `prototype-conversion-map.json` e gera uma página por tela `included`, com template escolhido pelo arquétipo (`list` / `form` / `list-detail` / `dashboard` / `content`)
- Gera componentes standalone com Angular Signals (13 componentes DS + `ToastService` / `ConfirmService`)
- Implementa services com HttpClient tipado a partir do contrato OpenAPI por BC; divergências protótipo × contrato são registradas, nunca resolvidas em silêncio
- Configura roteamento (uma rota por tela), guards e interceptors
- Gera módulo de autenticação (MSAL para Azure AD)
- Aplica guardrail G-DT: `:root` com tokens de design e `var(--token)` obrigatório em componentes de layout; sem `design-tokens.json`, cai para o `:root` do `index.html` e depois para defaults
- Espelha as regras de negócio com representação em UI, marcadas com `// Implements: BR-XXXX` e verificadas por assertion
- Scaffolding automático de `*.spec.ts` para Services, Guards, Interceptors, Pipes **e telas convertidas**
- **Executa** `ng test --code-coverage` com threshold (não apenas configura); sem Chrome no ambiente reporta `TOOLCHAIN_UNAVAILABLE` sem bloquear
- Assertion de fidelidade bloqueante: 100% das telas `included` viram componentes, com no máximo 3 iterações de reparo

**Output:**

```yaml
frontend_code: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/
components: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/src/app/
prototype_conversion_map: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/prototype-conversion-map.json
```

---

### `ava-stack-react-frontend`

| Campo           | Valor                                                                     |
| --------------- | ------------------------------------------------------------------------- |
| **Versão**      | `2.0.0`                                                                   |
| **Fase**        | F4                                                                        |
| **Módulo**      | `tech-stack`                                                              |
| **Arquivo**     | `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` |
| **SKILL**       | `.github/skills/ava-stack-react-frontend/SKILL.md`                        |
| **Routing key** | `tobe_stack.frontend_framework == "react"` (modo generic)                 |
| **Dispatch**    | user-facing via SKILL.md + dispatched by orchestrator                     |

**Responsabilidades:**

- **Conversão P2C** — lê `index.html` + `screen-list.md` do protótipo (F3) e gera **uma página por tela**, não por bounded context; template escolhido pelo arquétipo
- Gera código React 18 + TypeScript 5 production-ready por bounded context (modo generic)
- Routing Guard: framework incompatível ou modo `build-cycle` → redireciona e encerra
- Configura Vite, Router v6, Zustand + TanStack Query, MSAL / Auth0
- Guardrail G-DT: `src/styles/tokens.css` a partir de `design-tokens.json`, com fallback para o `:root` do `index.html` e depois defaults
- Conjunto RX-001..RX-014 de componentes compartilhados (substitui os stubs `Button`/`Input`/`Table`/`Modal`)
- Espelha as regras de negócio via schemas Zod marcados com `// Implements: BR-XXXX`, verificados por assertion
- Integra com o contrato OpenAPI por BC; divergências protótipo × contrato são registradas, nunca silenciadas
- Scaffold Gate determinístico (`verify_scaffold.py --manifest react`)
- **Executa** `vitest run --coverage` com threshold (não apenas configura) + `tsc --noEmit` + `vite build`
- Assertion de fidelidade bloqueante: 100% das telas `included` viram componentes
- Executa npm audit gate, Security Compliance Review Gate e invoca `ava-stack-build-validator`

**Output:**

```yaml
react_project_scaffold: projects/{project_name}/outputs/tobe/source-code/frontend/
implementation_status: projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json
```

---

### `ava-build-cycle-react-scaffold`

| Campo           | Valor                                                                              |
| --------------- | ---------------------------------------------------------------------------------- |
| **Versão**      | `1.0.0`                                                                            |
| **Fase**        | F3                                                                                 |
| **Módulo**      | `tech-stack`                                                                       |
| **Arquivo**     | `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md` |
| **SKILL**       | _(nenhum — agente interno, Article XI)_                                            |
| **Routing key** | `pipeline_mode == "build-cycle" AND tobe_stack.frontend_framework == "react"`      |
| **Dispatch**    | internal-only via `ava-stack-orchestrator`                                         |

**Responsabilidades:**

- Lê `architecture-blueprint.md` e classifica BCs por `has_ui` (full vs. minimal)
- Gera scaffolding completo: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `.env.example`
- Gera camada shared: `main.tsx`, `App.tsx`, router lazy-load, AuthGuard, shared components
- Gera por BC (full): `domain/`, `application/`, `infrastructure/`, `ui/`, `tests/`
- Gera por BC (minimal): placeholder `index.tsx`
- Gate de segurança via `npm audit --audit-level=high`
- Escreve `implementation-status.json` com `"status": "COMPLETED"`

**Output:**

```yaml
react_project_scaffold: projects/{project_name}/outputs/tobe/source-code/frontend/
scaffold_manifest: projects/{project_name}/outputs/tobe/source-code/frontend/scaffold-manifest.json
implementation_status: projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json
```

---

### `ava-stack-vue-frontend`

| Campo           | Valor                                                                   |
| --------------- | ----------------------------------------------------------------------- |
| **Versão**      | `1.0.0`                                                                 |
| **Fase**        | F3                                                                      |
| **Módulo**      | `tech-stack`                                                            |
| **Arquivo**     | `src/modules/ava-fabric-agents/tech-stack/agents/coder-vue-frontend.md` |
| **SKILL**       | `.github/skills/ava-stack-vue-frontend/SKILL.md`                        |
| **Routing key** | `tobe_stack.frontend_framework == "vue"` (modo generic)                 |
| **Dispatch**    | user-facing via SKILL.md + dispatched by orchestrator                   |

**Responsabilidades:**

- Gera código Vue 3 + TypeScript strict production-ready por bounded context (modo generic)
- Routing Guard: em modo `build-cycle`, emite WARN e continua em modo generic (`build_cycle_fallback: true`)
- Composition API + `<script setup>` obrigatório — Options API proibida
- Configura Vite 5, `@vitejs/plugin-vue`, Vue Router 4 com lazy loading
- Gera Pinia stores por BC com Composition API setup
- Integra MSAL (`@azure/msal-vue`) para Azure AD ou Auth0 (`@auth0/auth0-vue`)
- XSS guard: DOMPurify obrigatório antes de qualquer `v-html`
- Gera testes Vitest + Vue Test Utils v2 por BC
- Executa Security Compliance Review Gate e gera `SecurityComplianceReport-Frontend.md`

**Output:**

```yaml
vue_project_scaffold: projects/{project_name}/outputs/tobe/source-code/frontend/
implementation_status: projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json
```

---

## F4 — Prototype

### `ava-prototype`

| Campo       | Valor                                                               |
| ----------- | ------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` |
| **Papel**   | Prototipação de UI navegável do sistema TO-BE                       |

**Responsabilidades:**

- Gera especificação Figma detalhada por tela
- Escreve roteiro de demonstração da jornada crítica
- Cria HTML navegável como demo interativo

**Output:**

```yaml
prototype: projects/{PROJECT_NAME}/outputs/tobe/prototype/
demo_script: projects/{PROJECT_NAME}/outputs/tobe/prototype/demo-script.md
figma_spec: projects/{PROJECT_NAME}/outputs/tobe/prototype/figma-spec.md
```

---

### `ava-stack-react-frontend`

| Campo       | Valor                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| **Versão**  | `2.0.0`                                                                    |
| **Arquivo** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`  |
| **Papel**   | Desenvolvedor React 18+ — Vite, TypeScript strict, TanStack Query, Zustand. Converte o protótipo navegável da Fase 3 em componentes, uma página por tela. |

**Responsabilidades:**

- Conversão P2C: uma página por tela `included` do protótipo, com template por arquétipo
- Gera estrutura por bounded context em `src/{bc}/` (domain / application / infrastructure / ui)
- React Hook Form + Zod obrigatórios; `useState` por campo é proibido (ver `react-patterns-reference.md`)
- Conjunto RX-001..RX-014 de componentes compartilhados em `src/shared/ui/`
- Service layer derivado do contrato OpenAPI por BC; hooks TanStack Query por tela
- Executa Security Compliance Review Gate (CSP, PII localStorage, XSS)
- Test Scaffolder Vitest + RTL por tela, mais teste de schema Zod por tela de formulário
- Executa `tsc --noEmit`, `vitest run --coverage` (threshold ≥ 80%) e `vite build`

**Output:**

```yaml
frontend_code: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/
components: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/src/{bc}/ui/
prototype_conversion_map: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/prototype-conversion-map.json
```

---

## F4 — Prototype

### `ava-prototype`

| Campo       | Valor                                                                                                                                                             |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`                                                                                               |
| **Versão**  | `1.1.0`                                                                                                                                                           |
| **Papel**   | Prototipação de UI navegável do sistema TO-BE. Exporta `design-tokens.json` (spacing, colors, typography, layout) para consumo pelos agentes de codegen frontend. |

**Responsabilidades:**

- Gera especificação Figma detalhada por tela
- Escreve roteiro de demonstração da jornada crítica
- Cria HTML navegável como demo interativo
- Extrai tokens de design de `design-system.md` e grava `design-tokens.json`

**Output:**

```yaml
prototype: projects/{PROJECT_NAME}/outputs/tobe/prototype/
demo_script: projects/{PROJECT_NAME}/outputs/tobe/prototype/demo-script.md
figma_spec: projects/{PROJECT_NAME}/outputs/tobe/prototype/figma-spec.md
design_tokens: projects/{PROJECT_NAME}/outputs/tobe/prototype/design-tokens.json
```

---

## F5 — QA Agents

Fase de qualidade. O orchestrator pode executar agentes em paralelo ou sequencialmente conforme a estratégia.

### `ava-qa-orchestrator`

| Campo       | Valor                                                                     |
| ----------- | ------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md` |
| **Papel**   | Coordenador da estratégia de QA                                           |

**Output:**

```yaml
quality_strategy: projects/{PROJECT_NAME}/outputs/qa/quality-strategy.md
qa_master_report: projects/{PROJECT_NAME}/outputs/qa/qa-master-report.md
```

---

### `ava-qa-gaps-requirements`

| Campo       | Valor                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/gaps-requirements-agent.md` |
| **Papel**   | Mapeamento de gaps de requisitos para cobertura de QA                       |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/gaps-requirements-report.md`

---

### `ava-qa-behavior-mapping`

| Campo       | Valor                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/behavior-mapping-agent.md` |
| **Papel**   | Mapeamento de comportamentos esperados do sistema TO-BE                    |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/behavior-mapping-report.md`

---

### `ava-qa-scenario-generator`

| Campo       | Valor                                                                        |
| ----------- | ---------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/scenario-generator-agent.md` |
| **Papel**   | Geração de cenários de teste (BDD / Gherkin)                                 |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/scenario-generator/`

---

### `ava-qa-test-case-generator`

| Campo       | Valor                                                                         |
| ----------- | ----------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/test-case-generator-agent.md` |
| **Papel**   | Geração de casos de teste formais a partir dos cenários                       |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/test-case-generator/`

---

### `ava-qa-script-generator`

| Campo       | Valor                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/script-generator-agent.md` |
| **Papel**   | Scripts de automação — xUnit, Playwright, k6                               |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/script-generator/`

---

### `ava-qa-exploratory`

| Campo       | Valor                                                                 |
| ----------- | --------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/exploratory-agent.md` |
| **Papel**   | Roteiros de teste exploratório por jornada crítica                    |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/exploratory/`

---

### `ava-qa-evidence-capture`

| Campo       | Valor                                                                                                                                                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/evidence-capture-agent.md`                                                                                                                                                      |
| **Papel**   | Coleta e organiza todas as evidências dos testes de paridade — screenshots de outputs idênticos, logs de execução, diff reports e dashboards de paridade — para compor o pacote de evidências de compliance exigido pelo aceite |

**Output:**

```yaml
report: projects/{PROJECT_NAME}/outputs/qa/evidence-capture-report.md
parity_dashboard: projects/{PROJECT_NAME}/outputs/qa/parity-dashboard.md
compliance_package: projects/{PROJECT_NAME}/outputs/qa/evidence-capture/compliance-package/
diff_reports: projects/{PROJECT_NAME}/outputs/qa/evidence-capture/diffs/
execution_logs: projects/{PROJECT_NAME}/outputs/qa/evidence-capture/logs/
screenshots_index: projects/{PROJECT_NAME}/outputs/qa/evidence-capture/screenshots/index.md
package_index: projects/{PROJECT_NAME}/outputs/qa/evidence-capture-package-index.md
```

---

### `ava-qa-defect-identifier`

| Campo       | Valor                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/defect-identifier-agent.md` |
| **Papel**   | Identificação, classificação e priorização de defeitos                      |

**Output:** `projects/{PROJECT_NAME}/outputs/qa/defect-identifier/`

---

### `ava-qa-db-integrity-test`

| Campo       | Valor                                                                          |
| ----------- | ------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/db-integrity-test-agent.md`    |
| **Papel**   | Gera testes xUnit de integridade de banco de dados após migração legado → .NET |
| **Trigger** | `DBI` (via qa-orchestrator)                                                    |

**Inputs obrigatórios:**

- `outputs/asis/db/schema-inventory.md` (F1 completa)
- `outputs/tobe/source-code/src/**/Migrations/*.cs` (F4 completa)

**Inputs opcionais:**

- `outputs/asis/db/stored-procedures-map.md` — ativa categoria `StoredProcedures/`

**Output:**

```yaml
report: projects/{PROJECT_NAME}/outputs/qa/db-integrity/db-integrity-test-report.md
test_code: projects/{PROJECT_NAME}/outputs/tobe/source-code/tests/DatabaseIntegrity/
```

**Categorias de testes geradas:**

| Categoria           | O que valida                                                 |
| ------------------- | ------------------------------------------------------------ |
| `Migrations/`       | Cada migration EF Core registrada em `__EFMigrationsHistory` |
| `Constraints/`      | Violação de PK, FK e UK gera `DbUpdateException`             |
| `Indexes/`          | Existência de cada índice via `sys.indexes`                  |
| `StoredProcedures/` | Equivalência de SPs migradas para .NET (condicional)         |

---

### `ava-qa-contract-test-generator`

| Campo       | Valor                                                                               |
| ----------- | ----------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/contract-test-generator-agent.md`   |
| **Papel**   | Gera testes de contrato consumer-driven (PactNet) entre Frontend↔Backend e inter-BC |
| **Trigger** | `CT` (via qa-orchestrator)                                                          |

**Inputs obrigatórios:**

- `outputs/tobe/docs/openapi/*.yaml` (OpenAPI specs)
- `outputs/tobe/source-code/src/**/Controllers/*.cs` (source code backend)

**Output:**

```yaml
report: projects/{PROJECT_NAME}/outputs/qa/contract-tests/contract-test-report.md
test_code: projects/{PROJECT_NAME}/outputs/tobe/source-code/tests/Contract/
```

---

### `ava-qa-frontend-test-generator`

| Campo       | Valor                                                                             |
| ----------- | --------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/frontend-test-generator-agent.md` |
| **Papel**   | Gera testes Jest + Angular Testing Library para components, services e stores     |
| **Trigger** | `FT` (via qa-orchestrator)                                                        |

**Inputs obrigatórios:**

- `outputs/tobe/source-code/frontend/src/app/**/*.component.ts`

**Output:**

```yaml
report: projects/{PROJECT_NAME}/outputs/qa/frontend-tests/frontend-test-report.md
test_code: projects/{PROJECT_NAME}/outputs/tobe/source-code/frontend/src/app/**/*.spec.ts
```

---

### `ava-qa-bridge-fastqa-tobe`

| Campo       | Valor                                                                                                                   |
| ----------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md`                                                  |
| **Papel**   | Bridge TO-BE → FastQA: gera testes API black-box (Playwright/TS), exploratórios live (POISED/VADER) e automação externa |
| **Trigger** | `FQ` (via qa-orchestrator)                                                                                              |

**Inputs obrigatórios:**

- `outputs/tobe/qa/test-cases.md` (Test Cases TO-BE consolidados)
- `outputs/tobe/docs/openapi/*.yaml` (OpenAPI specs)

**Output:**

```yaml
gherkin_scenarios: projects/{PROJECT_NAME}/outputs/qa/fastqa/gherkin-scenarios.md
exploratory_report: projects/{PROJECT_NAME}/outputs/qa/fastqa/exploratory-api-report.md
automation_summary: projects/{PROJECT_NAME}/outputs/qa/fastqa/automation-summary.md
automated_tests: automated_test/api/tests/*.spec.ts
```

**Escopo complementar (NON-NEGOTIABLE):**

- ✅ API black-box tests (Playwright/TS contra API running)
- ✅ Exploratory API live testing (POISED/VADER)
- ❌ NÃO gera Unit, Integration, Contract, DB Integrity, Frontend tests (cobertos por outros agents)

---

## F6 — DevOps

Fase de infraestrutura e pipelines. Todos os artefatos são gerados como código (IaC).

### `ava-devops-iac`

| Campo       | Valor                                                             |
| ----------- | ----------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/devops-agents/agents/iac-agent.md` |
| **Papel**   | Platform Engineer — IaC para Azure (Bicep / Terraform)            |

**Responsabilidades:**

- Provisiona recursos Azure: App Service, SQL Database, Key Vault, Application Insights
- Configura managed identity e RBAC
- Gera scripts de inicialização de ambiente

**Output:**

```yaml
terraform: projects/{PROJECT_NAME}/outputs/tobe/iac/terraform/
bicep: projects/{PROJECT_NAME}/outputs/tobe/iac/bicep/
ansible: projects/{PROJECT_NAME}/outputs/tobe/iac/ansible/
```

---

### `ava-devops-ci`

| Campo       | Valor                                                            |
| ----------- | ---------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/devops-agents/agents/ci-agent.md` |
| **Papel**   | Pipeline CI — build, test, análise de qualidade                  |

**Responsabilidades:**

- Gera workflow GitHub Actions e/ou Azure Pipelines
- Configura SonarQube, SAST e gate de cobertura
- Integra análise de pacotes NuGet (vulnerabilidades)

**Output:**

```yaml
github_actions: projects/{PROJECT_NAME}/outputs/tobe/iac/ci/.github/workflows/ci.yml
azure_devops_ci: projects/{PROJECT_NAME}/outputs/tobe/iac/ci/azure-pipelines-ci.yml
sonar_config: projects/{PROJECT_NAME}/outputs/tobe/iac/ci/sonar-project.properties
```

---

### `ava-devops-cd`

| Campo       | Valor                                                            |
| ----------- | ---------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/devops-agents/agents/cd-agent.md` |
| **Papel**   | Pipeline CD — deploy contínuo com validação pós-deploy inline     |

**Output:**

```yaml
cd_pipeline: projects/{PROJECT_NAME}/outputs/tobe/iac/cd/azure-pipelines-cd.yml
deploy_scripts: projects/{PROJECT_NAME}/outputs/tobe/iac/cd/scripts/
post_deploy_validation: projects/{PROJECT_NAME}/outputs/tobe/iac/cd/post-deploy-validation.yml
```

---

### `ava-devops-compare-version`

| Campo       | Valor                                                                         |
| ----------- | ----------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/devops-agents/agents/compare-version-agent.md` |
| **Papel**   | Comparação de paridade entre AS-IS e TO-BE em produção                        |

**Responsabilidades:**

- Executa payloads equivalentes nos dois sistemas
- Compara respostas campo a campo
- Gera relatório de paridade e aprova wave para go-live

**Output:**

```yaml
parity_report: projects/{PROJECT_NAME}/outputs/tobe/parity-test-report.md
field_diff: projects/{PROJECT_NAME}/outputs/tobe/field-differences.json
wave_approval: projects/{PROJECT_NAME}/outputs/tobe/wave-approval.md
```

---

### `ava-devops-package-approval`

| Campo       | Valor                                                                          |
| ----------- | ------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/devops-agents/agents/package-approval-agent.md` |
| **Papel**   | Gate de aprovação de pacotes NuGet por pré-requisitos de arquitetura           |

**Responsabilidades:**

- Valida que os NuGet packages usados atendem requisitos de segurança e licença
- Verifica versões mínimas obrigatórias por camada

---

### `ava-devops-podman-run`

| Campo       | Valor                                                                     |
| ----------- | ------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/devops-agents/agents/podman-run-agent.md`  |
| **Versão**  | `1.0.0`                                                                   |
| **Skill**   | `ava-devops-podman-run`                                                   |
| **Papel**   | Execução local no Windows (Podman) da solução containerizada              |
| **Depende** | `ava-devops-containerize` (compose files + `.env.example`)                |
| **Guia**    | `docs/podman-windows-guide.md` — fonte da verdade dos comandos            |

**Responsabilidades:**

- Pré-flight bloqueante das dependências do host: versão do Windows, virtualização,
  WSL2, winget, Podman CLI, `podman compose`, RAM e disco livre — com remediação
  copiável para cada item ausente
- Auto-descoberta de todos os parâmetros dinâmicos (projeto, diretório de código-fonte,
  arquivos compose, serviços, portas, variáveis `${VAR}` obrigatórias); só pergunta ao
  usuário o que a descoberta não resolver
- Provisiona e inicia a Podman Machine dimensionando disco/RAM/CPU pelos recursos do host
- Resolve e escreve o `.env` (segredos gerados nunca são exibidos)
- Sobe a stack em modo detached e aguarda saúde com orçamento de tempo limitado
- Classifica falhas contra a tabela de troubleshooting do guia

**Triggers:** `PR` run completo · `PC` check-only · `PM` machine · `PE` env · `PU` up ·
`PS` status · `PL` logs · `PD` down · `PT` troubleshoot

**Output:**

```yaml
podman_preflight_report: projects/{PROJECT_NAME}/outputs/tobe/iac/containers/podman-preflight.md
podman_run_report: projects/{PROJECT_NAME}/outputs/tobe/iac/containers/podman-run-report.md
runtime_env_file: projects/{PROJECT_NAME}/outputs/tobe/source-code/.env
```

---

---

## F7 — Deliverables

Fase de empacotamento e publicação dos entregáveis para o cliente.

### `ava-deliverable-packager`

| Campo       | Valor                                                                 |
| ----------- | --------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/packager-agent.md` |
| **Papel**   | Empacotador central de entregáveis por wave                           |

**Output:**

```yaml
delivery_package: projects/{PROJECT_NAME}/outputs/deliverables/wave-{N}-package/
delivery_index: projects/{PROJECT_NAME}/outputs/deliverables/wave-{N}-index.md
delivery_report: projects/{PROJECT_NAME}/outputs/deliverables/wave-{N}-delivery-report.md
```

---

### `ava-deliverable-tech-docs`

| Campo       | Valor                                                                  |
| ----------- | ---------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/tech-docs-agent.md` |
| **Papel**   | Documentação técnica consolidada para handover                         |

**Output:** `projects/{PROJECT_NAME}/outputs/deliverables/tech-docs-agent/`

---

### `ava-deliverable-migration-plan`

| Campo       | Valor                                                                           |
| ----------- | ------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/migration-plan-publisher.md` |
| **Papel**   | Publicação do plano de migração em formato executivo                            |

**Output:** `projects/{PROJECT_NAME}/outputs/deliverables/migration-plan-publisher/`

---

### `ava-deliverable-security-compliance`

| Campo       | Valor                                                                            |
| ----------- | -------------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/security-compliance-agent.md` |
| **Papel**   | Relatório consolidado de segurança e LGPD para CISO/DPO                          |

**Responsabilidades:**

- Consolida todos os achados de segurança
- Gera evidências de tratamento dos riscos P0
- Produz declaração de conformidade LGPD

**Output:** `projects/{PROJECT_NAME}/outputs/deliverables/security-compliance-agent/`

---

### `ava-deliverable-test-evidence`

| Campo       | Valor                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/test-evidence-agent.md` |
| **Papel**   | Empacotamento de evidências de teste para aceite do cliente                |

**Output:** `projects/{PROJECT_NAME}/outputs/deliverables/test-evidence-agent/`

---

### `ava-deliverable-code-templates`

| Campo       | Valor                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/code-templates-agent.md` |
| **Papel**   | Templates de código reutilizáveis para o time do cliente                    |

**Output:** `projects/{PROJECT_NAME}/outputs/deliverables/code-templates-agent/`

---

### `ava-deliverable-client-demo`

| Campo       | Valor                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/deliverables/agents/client-demo-agent.md` |
| **Papel**   | Roteiro de demonstração executiva para o cliente                         |

**Responsabilidades:**

- Escreve roteiro detalhado por jornada crítica
- Gera apresentação de status do projeto
- Produz documento de aceite formal

**Output:**

```yaml
demo_script: projects/{PROJECT_NAME}/outputs/deliverables/demo-script.md
presentation: projects/{PROJECT_NAME}/outputs/deliverables/presentation-deck.md
acceptance_doc: projects/{PROJECT_NAME}/outputs/deliverables/acceptance-document.md
```

---

---

## F8 — Summary

### `ava-summary` (v1.1.0)

| Campo        | Valor                                                                                                                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Arquivo**  | `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`                                                                                                                                     |
| **Papel**    | Consolidação de todos os outputs em HTML executivo autocontido                                                                                                                                      |
| **Template** | `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`                                                                                                                        |
| **v1.1.0**   | Step 0.5: verificação de integridade de artefatos (existência + tamanho > 0) antes de gerar HTML; emite `[ARTIFACT-MISSING]`/`[ARTIFACT-EMPTY]` por artefato ausente e omite a seção correspondente |

**Modos de invocação:**

| Comando | Descrição                                             |
| ------- | ----------------------------------------------------- |
| `SI`    | Summary Independente — solicita o caminho dos outputs |
| `SAS`   | Summary AS-IS Only — gera com dados da F1 apenas      |
| `STOBE` | Summary TO-BE Only — gera com dados da F2 apenas      |
| `SFull` | Summary Completo — todas as fases disponíveis         |

**Input:**

```yaml
outputs_base_path: projects/{PROJECT_NAME}/outputs/ # default
project_name: string
```

**Output:**

```yaml
summary_html: projects/{PROJECT_NAME}/outputs/summary/AVA-FABRIC-SUMMARY-{PROJECT}-{DATE}.html
summary_index: projects/{PROJECT_NAME}/outputs/summary/index.md
data_json: projects/{PROJECT_NAME}/outputs/summary/summary-data.json
mermaid_js_cache: projects/{PROJECT_NAME}/outputs/summary/mermaid.min.js
```

**Características do HTML gerado:**

- 100% autocontido — zero dependências externas em runtime
- Mermaid.js injetado inline para renderização visual de diagramas
- Tema dark Avanade (vermelho `#FF0000`, fundo `#0A0A0A`)
- Diagramas com fundo claro e zoom via modal ao clique
- Suporte i18n PT-BR / EN
- Sidebar com navegação por fase

---

### `ava-summary-validate` (v1.1.0)

| Campo       | Valor                                                                                                                                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Arquivo** | `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`                                                                                                                               |
| **Papel**   | Quality gate não-regressivo do HTML Summary; bloqueia promoção ao cliente se qualquer regra `error` falhar                                                                                             |
| **v1.1.0**  | Categoria C11 Artifact Integrity adicionada (3 regras): C11.1 detecta `[INCOMPLETE]`, C11.2 detecta `[ARTIFACT-MISSING]` não resolvidos no HTML, C11.3 detecta tabelas com zero linhas de dados (warn) |

---

## Convenções e Contratos

### Estrutura de Outputs

```
project/
  inputs/          ← código-fonte legado (read-only para agentes)
  outputs/
    asis/          ← artefatos F1 (master-report, risk-register, diagrams...)
    tobe/          ← artefatos F2–F4 (blueprint, prototype, source-code, iac...)
    qa/            ← artefatos F5
    deliverables/  ← artefatos F7 (pacotes por wave)
    summary/       ← artefatos F8 (HTML executivo)
  context/
    shared-context.md      ← contexto compartilhado entre agentes
    project-config.yaml    ← configuração do projeto
```

### trace_id

Todos os agentes propagam o `trace_id` no formato `ava-{fase}-{data}-{projeto}`.  
Exemplo: `ava-asis-20260406-meu-erp`

### Guardrails Comuns

- Agentes **nunca modificam** arquivos em `src/` ou `projects/{PROJECT_NAME}/inputs/`
- Agentes **nunca abortam** por arquivo faltante — geram saída parcial marcada como "Pendente"
- Todo output inclui `trace_id` e timestamp para rastreabilidade
- Dados reais sempre têm precedência sobre valores calculados ou estimados

### Invocação via Skill

Cada agente tem uma skill correspondente em `.claude/skills/`:

```
/ava-asis-orchestrator      → dispara diagnóstico AS-IS completo
/ava-tobe-orchestrator      → dispara design TO-BE completo
/ava-summary                → gera HTML executivo
/ava-qa-orchestrator        → dispara estratégia de QA
/ava-devops-iac             → gera IaC Azure
```

---

_Atualizado em 2026-04-06 · AVA Fabric Agents v1.1 — Multi-Project + GitHub Copilot Skills_
