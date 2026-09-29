# Plano SQL IR → MER na Branch feature/PBI-2555

> **Branch atual**: `feature/PBI-2555-implement-leiden-module-partitioner`
> **Objetivo**: Gerar uma SQL Intermediate Representation (IR) normalizada a partir dos artefatos AST (`03_database_rules.json`, `04_database_schemas.json`, `05_procedures.json`) e torná-la consumível por um **MER Agent** para desenho de Modelo Entidade-Relacionamento, respeitando o escopo de módulos (`scope-filter-manifest.json`).

---

## 1. Entendimento do Estado Atual (Branch PBI-2555)

### Artefatos AST Disponíveis (AS-IS Diagnostic)

| JSON | Campo Relevante | Descrição |
|---|---|---|
| `03_database_rules.json` | `payload.rules[].{type, operation, tables[], source_ref:{file,line}, id}` | Operações de escrita (insert/update/delete) por tabela, com rastreamento ao arquivo-fonte Delphi |
| `04_database_schemas.json` | `payload.tables[].{name, columns_count, unit}` (DDL-derived) | Tabelas derivadas de DDL ou inferidas do SQL inline |
| `04_database_schemas.json` | `payload.inferred_tables[].{name, origin, accessed_columns[], operations[], used_in[]}` | Tabelas inferidas do código, com colunas acessadas e operações |
| `04_database_schemas.json` | `payload.dataset_fields[].{dataset, fields:[{name, delphi_type}]}` | Campos de datasets Delphi (TADOQuery, TTable etc.) |
| `05_procedures.json` | `payload.stored_procedures[]` | Stored procedures no lado do SGBD (vazio para aplicações desktop puras) |
| `05_procedures.json` | `payload.code_procedures[].{unit, class, name, kind, params, returns, loc, calls, source_ref}` | Procedimentos/funções no código Delphi |

### Artefatos de Particionamento (Já Existentes na Branch)

| Artefato | Onde | Estrutura |
|---|---|---|
| `module-partition.json` | `outputs/asis/ast-raw/{language}/compressed/` | `{ "Financeiro": ["uContasPagar.pas", ...], ... }` |
| `scope-filter-manifest.json` | `outputs/asis/ast-raw/{language}/compressed/` | `{ scope_modules, included_units[], excluded_units[], module_partition, source, resolution }` |

### Gap Identificado
Não há **nenhum** artefato que normalize os dados de banco dos JSONs AST em uma estrutura unificada que um agente possa consumir para gerar um MER. O `db-analyzer.md` consome os JSONs **diretamente** e gera `schema-inventory.md`, `er-diagram.mmd`, etc., mas um agente de MER downstream precisa de uma IR separada.

---

## 2. SQL Intermediate Representation (IR) — Especificação

### 2.1 Schema do `sql-ir.json` (Novo Artefato)

Local: `projects/{project}/outputs/asis/ast-raw/{language}/compressed/sql-ir.json`

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO8601>",
  "source": "delphi-ast-extraction",
  "project_name": "Meu-ERP",
  "scope": {
    "mode": "partial",
    "modules": ["Financeiro", "Vendas"],
    "included_units": ["uContasPagar.pas", "uPedido.pas"]
  },
  "statistics": {
    "entities_total": 42,
    "entities_in_scope": 15,
    "relationships_in_scope": 23,
    "procedures_in_scope": 8,
    "attributes_total": 187
  },
  "entities": [
    {
      "id": "ent-contas-pagar",
      "name": "contas_pagar",
      "display_name": "Contas a Pagar",
      "origin": "inferred_from_sql",
      "sources": [
        { "file": "uContasPagar.pas", "line": 145, "ref_type": "TQuery.SQL" }
      ],
      "module_owners": ["Financeiro"],
      "attributes": [
        {
          "name": "id",
          "type": "integer",
          "nullable": false,
          "is_pk": true,
          "is_fk": false,
          "source": "inferred"
        },
        {
          "name": "id_fornecedor",
          "type": "integer",
          "nullable": true,
          "is_pk": false,
          "is_fk": true,
          "references": { "entity": "ent-fornecedor", "attribute": "id" }
        }
      ],
      "operations": ["insert", "update", "select"],
      "risk_level": "HIGH"
    }
  ],
  "relationships": [
    {
      "id": "rel-001",
      "source_entity": "ent-contas-pagar",
      "target_entity": "ent-fornecedor",
      "cardinality": "many-to-one",
      "type": "foreign_key",
      "source_columns": ["id_fornecedor"],
      "target_columns": ["id"],
      "confidence": "inferred"
    }
  ],
  "procedures": [
    {
      "id": "proc-001",
      "name": "sp_calcula_saldo",
      "kind": "stored_procedure",
      "language": "sql",
      "source_unit": "uContasPagar.pas",
      "source_ref": { "file": "uContasPagar.pas", "line": 300 },
      "module_owners": ["Financeiro"],
      "operations": ["select", "update"],
      "affected_entities": ["ent-contas-pagar"],
      "loc": 45,
      "complexity": "medium"
    }
  ],
  "modules": {
    "Financeiro": {
      "entities": ["ent-contas-pagar", "ent-fornecedor"],
      "relationships": ["rel-001"],
      "procedures": ["proc-001"]
    }
  }
}
```

### 2.2 Regras de Escopo (Filtering)

O SQL IR DEVE respeitar `scope-filter-manifest.json`:

1. **Entidade é incluída** se pelo menos um `source.file` está em `included_units[]`.
2. **Stored Procedure é incluída** se `source_unit` está em `included_units[]`.
3. **Relacionamento é incluído** se **ambas** as entidades estão no escopo.
4. Relacionamentos que apontam para entidades **fora do escopo** são mantidos como referências externas (`external_reference: true`) para que o MER mostre fronteiras do módulo.

### 2.3 Normalização de Tipos (AS-IS Delphi → IR)

| Tipo Delphi/SQL Inferido | IR Type |
|---|---|
| `Integer`, `INT`, `BIGINT` | `integer` |
| `VARCHAR`, `STRING`, `NVARCHAR` | `string` |
| `DATE`, `DATETIME`, `TIMESTAMP` | `datetime` |
| `NUMERIC`, `DECIMAL`, `MONEY` | `decimal` |
| `BOOLEAN`, `BIT`, `TINYINT(1)` | `boolean` |
| `TEXT`, `MEMO`, `BLOB` | `text` |
| `FLOAT`, `REAL`, `DOUBLE` | `float` |
| Desconhecido | `unknown` |

---

## 3. Arquitetura da Implementação

### 3.1 Novo Componente: `sql_ir_generator.py`

**Localização sugerida**: `src/modules/ava-fabric-agents/asis-diagnostic/utils/sql_ir_generator.py`

Responsabilidades:
1. Ler `04_database_schemas.json` e normalizar entidades/atributos.
2. Ler `03_database_rules.json` e enriquecer entidades com operações (`insert/update/delete/select`).
3. Ler `05_procedures.json` e normalizar stored procedures/code procedures.
4. Ler `scope-filter-manifest.json` (se existir) e filtrar pelo escopo.
5. Inferir relacionamentos por convenção de nome (`id_fornecedor` → `fornecedor.id`).
6. Escrever `sql-ir.json`.

**Dependências**: Python stdlib (`json`, `pathlib`, `re`) + `pyyaml` (já usado no projeto).

### 3.2 Integração com `module_partitioner.py`

Após a chamada ao `ModulePartitioner.run()` em `run_ast_analysis.py` (Step 0.5), adicionar **Step 0.6** — SQL IR Generation:

```python
# No run_ast_analysis.py, após Step 0.5
if not skip_module_partitioner:
    try:
        from sql_ir_generator import SqlIrGenerator
        gen = SqlIrGenerator(project_name)
        gen.run()
    except Exception as exc:
        print(f"   ⚠️  SqlIrGenerator falhou: {exc} — prosseguindo sem IR.")
```

O `SqlIrGenerator` usará o `scope-filter-manifest.json` (se existir) para filtrar entidades.

### 3.3 Integração com `project-config.yaml` (Template)

Adicionar na seção de configuração do particionador (já existe `module_partitioner_resolution`):

```yaml
# ── SQL IR & MER Generation ──
sql_ir_generator:
  enabled: true                       # false = pula geração do sql-ir.json
  infer_relationships: true           # inferir FKs por convenção de nome
  include_external_refs: true         # incluir referências a entidades fora do escopo
  min_confidence: "medium"            # low | medium | high — filtro de confiança para inferências
```

### 3.4 Novo Agente: `sql-schema-to-mer-agent.md`

**Localização sugerida**: `src/modules/ava-fabric-agents/tobe-architecture/agents/sql-schema-to-mer-agent.md`

Este agente:
1. Lê `sql-ir.json` como **fonte primária**.
2. Lê `project-config.yaml` para descobrir `scope_modules` e `persistence.engine`.
3. Gera `mer-diagram.mmd` (Mermaid erDiagram) **por módulo**, se escopo for parcial.
4. Gera `mer-report.md` com descrição textual do modelo.
5. Respeita o Pre-Write Validation Gate para `.mmd` conforme `db-analyzer.md`.

**Output Contract**:
```yaml
outputs:
  mer_diagram: "projects/{project_name}/outputs/tobe/diagrams/mer-diagram-tobe.mmd"
  mer_report: "projects/{project_name}/outputs/tobe/docs/mer-report.md"
  mer_by_module:
    pattern: "projects/{project_name}/outputs/tobe/diagrams/mer-{module_name}.mmd"
```

---

## 4. Checklist de Implementação

### Fase A — Infrastructure Python (utils)

- [ ] **A1.** Criar `src/modules/ava-fabric-agents/asis-diagnostic/utils/sql_ir_generator.py`
  - [ ] Parser de `04_database_schemas.json` → entidades
  - [ ] Parser de `03_database_rules.json` → operações por entidade
  - [ ] Parser de `05_procedures.json` → procedures
  - [ ] Inferência de relacionamentos por convenção de nome (`^id_(\w+)$`)
  - [ ] Filtro por `scope-filter-manifest.json` (incluir external_refs opcional)
  - [ ] Escrita de `sql-ir.json`
- [ ] **A2.** Adicionar testes unitários em `tests/utils/test_sql_ir_generator.py`
- [ ] **A3.** Integrar `SqlIrGenerator` em `run_ast_analysis.py` (Step 0.6)
- [ ] **A4.** Atualizar `module_partitioner.py` docstring para listar `sql-ir.json` como artefato produzido pelo pipeline AS-IS

### Fase B — Configuração

- [ ] **B1.** Atualizar `projects/_template/context/project-config.yaml` com bloco `sql_ir_generator`
- [ ] **B2.** Atualizar `docs/module-partitioner-guide.md` com seção sobre SQL IR e MER
- [ ] **B3.** Atualizar `docs/asis-diagnostic-io-map.md` com o novo artefato `sql-ir.json`

### Fase C — Agente MER

- [ ] **C1.** Criar `src/modules/ava-fabric-agents/tobe-architecture/agents/sql-schema-to-mer-agent.md`
  - [ ] Input Contract com `sql-ir.json`
  - [ ] Lógica de geração de `erDiagram` Mermaid por módulo
  - [ ] Pre-Write Validation Gate para `.mmd`
  - [ ] Output Contract (`mer-diagram-tobe.mmd`, `mer-report.md`, `mer-{module}.mmd`)
- [ ] **C2.** Adicionar `sql-schema-to-mer-agent.md` ao catálogo de agentes (`docs/agents-catalog.md`)
- [ ] **C3.** Registrar o agente no `orchestrator-tobe.md` com dependência do `database-design-tobe.md`

### Fase D — Integração nos Agentes Existentes

- [ ] **D1.** Atualizar `db-analyzer.md` para mencionar `sql-ir.json` como fallback/auxiliar
- [ ] **D2.** Atualizar `database-design-tobe.md` para consumir `sql-ir.json` quando disponível (enriquecimento do MER)
- [ ] **D3.** Atualizar `solution-delphi.md` para mencionar `sql-ir.json` como artefato do Step 0

### Fase E — Documentação & Validação

- [ ] **E1.** Criar spec em `specs/016-sql-ir-mer-generation/` com:
  - `spec.md` — requisitos e contratos
  - `data-model.md` — schema do `sql-ir.json`
  - `research.md` — motivação e alternativas consideradas
- [ ] **E2.** Validar que `validate_summary.py` lê `sql-ir.json` (se existir) sem erros
- [ ] **E3.** Validar que `build_summary_comprehensive.py` não quebra com a presença do novo artefato

---

## 5. Decisões Arquiteturais (ADRs)

### ADR-001: Local do `sql-ir.json`
`outputs/asis/ast-raw/{language}/compressed/sql-ir.json` — junto aos outros artefatos AST, pois é derivado deles.

### ADR-002: Estratégia de Escopo no SQL IR
O filtro aplica-se **antes** da escrita do `sql-ir.json`. O arquivo sempre reflete o escopo ativo (total ou parcial). Isso simplifica o consumo downstream — o MER agent não precisa reimplementar lógica de filtro.

### ADR-003: Inferência de Relacionamentos
Usar heurística de convenção de nome (`id_<entidade>` → `<entidade>.id`) com nível de confiança `medium`. Relacionamentos inferidos são marcados com `"confidence": "inferred"` e `"type": "foreign_key_convention"`. Relacionamentos explícitos (quando o AST extrair FKs DDL) usam `"confidence": "explicit"`.

### ADR-004: Agente MER separado do Database Design TO-BE
O `sql-schema-to-mer-agent` é um agente **especializado** que roda **antes** do `database-design-tobe.md`. Ele cria o MER a partir do SQL IR. O `database-design-tobe.md` pode consumir o MER como entrada adicional, mas sua responsabilidade principal é o DDL TO-BE e o design físico.

---

## 6. Riscos & Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Inferência de FK por convenção de nome é imprecisa | MER com relacionamentos errados | Flag `confidence` + review humano no `mer-report.md`; `min_confidence` config |
| `04_database_schemas.json` não tem detalhes de colunas para tabelas DDL-derived | Atributos incompletos no IR | Usar `inferred_tables` + `dataset_fields` como fallback; marcar `incomplete: true` |
| Escopo parcial esconde relacionamentos críticos | MER do módulo fica isolado | `include_external_refs: true` mantém "ghost entities" no diagrama |
| Agente downstream não encontra `sql-ir.json` | Falha silenciosa | Degradar graceful até `schema-inventory.md` (comportamento atual) |

---

## 7. Próximos Passos

1. **Revisar este plano** — aprovar/adjustar ecks
2. **Implementar Fase A** — `sql_ir_generator.py` + testes
3. **Implementar Fase B** — config + docs
4. **Implementar Fase C** — agente MER
5. **Implementar Fase D/E** — integração + validação
6. **Commitar** na branch `feature/PBI-2555-implement-leiden-module-partitioner`
