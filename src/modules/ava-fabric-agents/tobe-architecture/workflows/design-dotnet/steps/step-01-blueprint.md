# Step 01-blueprint — Blueprint Arquitetural TO-BE

## Objetivo
Executar fase de Blueprint Arquitetural TO-BE do workflow TO-BE Design.
Produzir o documento de arquitetura alvo com stack tecnológico definido em `project-config.yaml` (`tobe_stack.*`),
estrutura de 4 layers (Domain, Application, Infrastructure, Presentation),
padrões Clean Architecture + CQRS + DDD, tecnologias de persistência, autenticação, cache e observabilidade.
Deve referenciar o `architecture-blueprint.md` AS-IS para evidenciar a evolução.

## Inputs
- AS-IS Master Report (`outputs/asis/master-report.md`)
- AS-IS Architecture Blueprint (`outputs/asis/architecture-blueprint.md`) — referência obrigatória
- Outputs das fases anteriores
- `project-config.yaml` (language, project_name, tech_lead_name)

## Output Files (checklist)

| # | Arquivo | Descrição |
|---|---------|-----------|
| 1 | `outputs/tobe/docs/architecture-blueprint.md` | Documento principal de arquitetura TO-BE |
| 2 | `outputs/tobe/diagrams/architecture-blueprint.mmd` | Diagrama Mermaid layered (flowchart TB) |
| 3 | `outputs/tobe/architecture-blueprint.html` | HTML autocontido com diagrama + cards macro |

## Acceptance Criteria

### AC-1: `architecture-blueprint.md`
- [ ] Arquivo criado em `projects/{project_name}/outputs/tobe/docs/`
- [ ] Contém seções obrigatórias: Stack, Solution Structure, Layers, Patterns, ADR refs, Technology Radar
- [ ] Stack especifica tecnologias conforme `tobe_stack.*` e `persistence.*` do project-config.yaml (backend framework + versão, frontend, ORM, engine de BD, auth, cache)
- [ ] Layers: Domain → Application → Infrastructure → Presentation (4 camadas, Dependency Inversion)
- [ ] Patterns: Clean Architecture + CQRS + DDD + Repository + UoW + Strangler Fig
- [ ] Referencia explicitamente `outputs/asis/architecture-blueprint.md` (tabela AS-IS → TO-BE)
- [ ] Tech Lead name presente como reviewer
- [ ] Sem placeholders `{{...}}` residuais

### AC-2: `diagrams/architecture-blueprint.mmd`
- [ ] Diagrama `flowchart TB` com todos os tiers (Clients, Host, Presentation, Application, Domain, Infrastructure, Data, External, Observability)
- [ ] `classDef` styling por camada
- [ ] Nodes para: frontend framework, backend framework + versão, MediatR, ORM, cache provider, BD engine, serviços externos, observabilidade (conforme project-config.yaml)
- [ ] Máximo 2 níveis de subgraph
- [ ] IDs: apenas `[A-Za-z0-9_]`

### AC-3: `architecture-blueprint.html`
- [ ] HTML autocontido (sem dependências externas exceto Mermaid CDN)
- [ ] Diagrama Mermaid renderizado
- [ ] Cards colapsáveis com tópicos macro: Evolution, Stack, Layers, Patterns, BCs, Auth, Cache, Observability, Quality Gates, ADRs
- [ ] KPI strip (readiness score, bounded contexts count, waves count)
- [ ] Branding Avanade (cor #FF5800)
- [ ] Dark/light theme toggle
- [ ] Footer com trace_id

## Critério de Conclusão
- Todos os 3 arquivos gerados e salvos nas suas respectivas pastas em `projects/{project_name}/outputs/tobe/`
- Agente reportou conclusão ao Orchestrator TO-BE
- Acceptance criteria 1–3 verificados
