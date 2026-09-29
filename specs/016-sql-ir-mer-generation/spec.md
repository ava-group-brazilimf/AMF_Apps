# Spec 016 — SQL IR & MER Generation

> **PBI**: 2555 (extensão — SQL IR sub-task)
> **Branch**: `feature/PBI-2555-implement-leiden-module-partitioner`
> **Fase**: F1 → F2 (AS-IS Diagnostic → TO-BE Architecture)
> **Owner**: AS-IS Diagnostic utils + TO-BE Architecture agent

## 1. Contexto & Motivação

O particionador de módulos (Leiden) introduzido na PBI-2555 permite modernizar
apenas um subconjunto de bounded contexts. Entretanto, o agente `db-analyzer`
gera artefatos (`schema-inventory.md`, `er-diagram.mmd`) para TODO o repositório
ou para o escopo filtrado de forma limitada. Não existe uma **representação
intermediária normalizada** dos dados de banco que:
1. Seja consumível por máquina (outros agentes);
2. Respeite o escopo de módulos (`scope-filter-manifest.json`);
3. Sirva de base para geração de MER (Modelo Entidade-Relacionamento) na Fase F2.

Esta spec define a SQL Intermediate Representation (`sql-ir.json`) e o agente
que a consome para produzir MER.

## 2. Requisitos Funcionais

### 2.1 SQL IR (`sql-ir.json`)

| ID | Requisito | Critério de Aceitação |
|---|---|---|
| R1 | Derivar de `03_database_rules.json`, `04_database_schemas.json`, `05_procedures.json` | 100% dos dados desses 3 JSONs refletidos no IR quando disponíveis |
| R2 | Normalizar entidades com atributos, PK, FK, operações e risco | Cada tabela vira entidade; colunas inferidas ou de DDL viram atributos |
| R3 | Inferir relacionamentos por convenção de nome (`id_<entidade>`) | FK heurísticas detectadas com nível de confiança |
| R4 | Respeitar `scope-filter-manifest.json` | Entidades/procedures fora de `included_units` devem ser excluídas (ou marcadas externas) |
| R5 | Suportar entidades externas (ghost) | Quando `include_external_refs: true`, manter referência a entidades fora do escopo |
| R6 | Gerar `sql-ir.json` em UTF-8, indentado, na pasta `compressed/` | Local canônico: `projects/{proj}/outputs/asis/ast-raw/{legacy_technology}/compressed/sql-ir.json`; mirror legado opcional: `projects/{proj}/outputs/asis/delphi-ast-raw/compressed/sql-ir.json` |

### 2.2 MER Agent (`ava-tobe-sql-schema-to-mer`)

| ID | Requisito | Critério de Aceitação |
|---|---|---|
| R7 | Consumir `sql-ir.json` como fonte primária | Não reler JSONs cruzados; usar apenas IR |
| R8 | Gerar `mer-diagram-tobe.mmd` (Mermaid erDiagram) | Diagrama válido passando em `validate_diagram.py` |
| R9 | Gerar `mer-report.md` com tabelas Markdown | Relatório human-readable com entidades, atributos, relacionamentos |
| R10 | Gerar MER por módulo quando `scope_modules != "all"` | Um `.mmd` por módulo em `diagrams/mer-{module}.mmd` |
| R11 | Incluir entidades externas como "ghost" quando configurado | Comentário `%% FORA DO ESCOPO` no Mermaid |
| R12 | Pre-Write Validation Gate para `.mmd` | Sempre usar `validate_diagram.py` antes de escrever `.mmd` |

## 3. Requisitos Não-Funcionais

- **Performance**: `sql_ir_generator.py` deve rodar em < 5s para projetos até 500 entidades.
- **Idempotência**: Rodar 2x deve produzir o mesmo `sql-ir.json` (timestamp à parte).
- **Degradação Graceful**: Se algum dos 3 JSONs AST estiver ausente, continuar com os disponíveis; nunca falhar silenciosamente.

## 4. Contratos de Dados

Ver [data-model.md](data-model.md) para o schema completo do `sql-ir.json`.

## 5. Checklist de Implementação

- [x] A1 — Criar `sql_ir_generator.py`
- [x] A2 — Integrar em `run_delphi_ast_analysis.py` (Step 0.6)
- [x] A3 — Atualizar `project-config.yaml` template
- [x] A4 — Criar agente `sql-schema-to-mer-agent.md`
- [ ] A5 — Testes unitários `test_sql_ir_generator.py`
- [ ] A6 — Validar com projeto real (Meu-ERP ou similar)
- [ ] A7 — Atualizar `docs/asis-diagnostic-io-map.md` com `sql-ir.json`
- [ ] A8 — Registrar agente no `orchestrator-tobe.md`

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Inferência de FK ruim | Flag `confidence` + review humano no `mer-report.md` |
| `sql-ir.json` muito grande | Streaming / paginação futura (não no MVP) |
| Agente downstream não encontra IR | Degradar para `schema-inventory.md` (comportamento atual) |

## 7. Status

- **Planejamento**: ✅ Completo (este documento)
- **Implementação SQL IR**: ✅ `sql_ir_generator.py` commitado
- **Implementação MER Agent**: ✅ `sql-schema-to-mer-agent.md` commitado
- **Testes**: ⬜ Pendente
