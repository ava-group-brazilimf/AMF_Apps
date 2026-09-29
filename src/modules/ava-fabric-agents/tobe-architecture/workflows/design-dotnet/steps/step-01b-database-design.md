# Step 01b-database-design — Database Design TO-BE

## Objetivo
Executar a Fase 1.5 da esteira TO-BE: gerar o Database Design completo da arquitetura alvo,
traduzindo o schema AS-IS para a engine alvo declarada em `project-config.yaml`.
Produz DDL normalizado, ERD Mermaid TO-BE e HTML bilíngue (EN/PT) com diagrama renderizado.

## Posição na Esteira
```
Fase 0  — ADR Generation        (adr-tobe)
Fase 1  — Blueprint + BCs       (architecture-design-tobe: CB → BC → TD)
Fase 1.5 — DB Design TO-BE      ← ESTE STEP
Fase 2  — Tech Framework        (architecture-technical-tobe: SS → NP → CS → QG → TF)
```

## Gate de Entrada (verificar antes de iniciar)
- [ ] `projects/{project_name}/outputs/tobe/docs/decisions/ADR-002-database.md` existe
- [ ] `projects/{project_name}/outputs/asis/db/schema-inventory.md` existe
- [ ] `projects/{project_name}/outputs/asis/db/er-diagram.mmd` existe
- Se ADR-002 ausente → **interromper** e alertar: "Execute a Fase 0 (adr-tobe) antes de prosseguir"

## Agente Responsável
`agents/database-design-tobe.md`

## Inputs
| Prioridade | Fonte | Path |
|---|---|---|
| 1 | `project-config.yaml` | `projects/{project_name}/context/project-config.yaml` |
| 2 | ADR-002 Database | `projects/{project_name}/outputs/tobe/docs/decisions/ADR-002-database.md` |
| 3 | Schema Inventory AS-IS | `projects/{project_name}/outputs/asis/db/schema-inventory.md` |
| 4 | ER Diagram AS-IS | `projects/{project_name}/outputs/asis/db/er-diagram.mmd` |
| 5 | Business Rules AS-IS | `projects/{project_name}/outputs/asis/docs/business-rules.md` |
| 6 | Stored Procedures Map AS-IS | `projects/{project_name}/outputs/asis/db/stored-procedures-map.md` |

## Output Files (checklist)

| # | Arquivo | Descrição |
|---|---|---|
| 1 | `projects/{project_name}/outputs/tobe/docs/db-design-report.md` | Relatório completo §1–§10 |
| 2 | `projects/{project_name}/outputs/tobe/diagrams/mer-diagram-tobe.mmd` | ERD Mermaid `erDiagram` TO-BE |
| 3 | `projects/{project_name}/outputs/tobe/docs/db-design-report.html` | HTML bilíngue EN/PT autocontido |

## Acceptance Criteria

### AC-1: `db-design-report.md`
- [ ] Arquivo criado em `projects/{project_name}/outputs/tobe/docs/`
- [ ] Seções §1–§10 todas presentes com conteúdo substantivo
- [ ] Engine alvo derivada de `persistence.engine` (não hardcoded)
- [ ] Tipos monetários: `NUMERIC(18,2)` ou `DECIMAL(18,2)` — FLOAT/REAL/MONEY proibidos
- [ ] Colunas de audit em todas as tabelas (se `audit_fields: true`)
- [ ] Estratégia soft-delete documentada (se `soft_delete: true`)
- [ ] ADR-002 referenciado na seção §1
- [ ] Índices P1 para todas as tabelas com Risk HIGH

### AC-2: `mer-diagram-tobe.mmd`
- [ ] Arquivo criado em `projects/{project_name}/outputs/tobe/diagrams/`
- [ ] Começa com `erDiagram`
- [ ] Todas as entidades TO-BE presentes com colunas corretas (dialect resolvido)
- [ ] Colunas de audit incluídas (se `audit_fields: true`)
- [ ] Sintaxe Mermaid v11.14.0 válida

### AC-3: `db-design-report.html`
- [ ] Toggle idioma EN/PT funcional (JavaScript sem reload)
- [ ] Toggle dark/light theme funcional
- [ ] ERD renderizado via Mermaid CDN
- [ ] KPI strip com 4 métricas
- [ ] Cards §1–§10 colapsáveis
- [ ] Branding Avanade `#FF5800`
- [ ] Footer com `trace_id`

## Critério de Conclusão
- Todos os 3 arquivos gerados e salvos nos paths corretos
- Validation Gate do agente `database-design-tobe.md` executado e aprovado
- Nenhum arquivo `outputs/asis/` modificado (anti-regressão)
- Agente reportou conclusão ao Orchestrator TO-BE com status `FASE_1.5: COMPLETE`
