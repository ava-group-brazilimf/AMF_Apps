# Data Model: SQL Intermediate Representation (`sql-ir.json`)

Artefato produzido por `sql_ir_generator.py` na Fase AS-IS (Step 0.6).
Fonte de verdade para agentes downstream de MER, Database Design TO-BE e
Summary Builder.

---

## Root Object

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-01-15T10:30:00Z",
  "source": "delphi-ast-extraction",
  "project_name": "Meu-ERP",
  "scope": { "mode": "full", "modules": [], "included_units": [] },
  "statistics": {
    "entities_total": 42,
    "entities_in_scope": 15,
    "relationships_in_scope": 23,
    "procedures_in_scope": 8,
    "attributes_total": 187
  },
  "entities": [],
  "relationships": [],
  "procedures": [],
  "modules": {}
}
```

---

## `scope` object

| Campo | Tipo | Descrição |
|---|---|---|
| `mode` | `"full"` \| `"partial"` | Indica se o IR foi filtrado por módulo |
| `modules` | `string[]` | Lista de módulos incluídos (vazio quando `mode: "full"`) |
| `included_units` | `string[]` | Lista de units incluídas (vazio quando `mode: "full"`) |

---

## `statistics` object

| Campo | Tipo | Descrição |
|---|---|---|
| `entities_total` | `int` | Total de entidades no IR |
| `entities_in_scope` | `int` | Entidades dentro do escopo (igual a total quando full) |
| `relationships_in_scope` | `int` | Relacionamentos dentro do escopo |
| `procedures_in_scope` | `int` | Procedimentos dentro do escopo |
| `attributes_total` | `int` | Soma de atributos de todas as entidades |

---

## `Entity` object

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | ✅ | Identificador único (ex: `ent-0001`) |
| `name` | `string` | ✅ | Nome técnico da entidade (snake_case) |
| `display_name` | `string` | ✅ | Nome humano-legível (Title Case) |
| `origin` | `string` | ✅ | `ddl`, `inferred_from_sql`, `dataset` |
| `sources` | `SourceRef[]` | ✅ | Rastreabilidade ao código-fonte |
| `module_owners` | `string[]` | ✅ | Módulos aos quais a entidade pertence |
| `attributes` | `Attribute[]` | ✅ | Lista de atributos/campos |
| `operations` | `string[]` | ✅ | Operações detectadas: `insert`, `update`, `delete`, `select` |
| `risk_level` | `string` | ✅ | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |

### `SourceRef` object

| Campo | Tipo | Descrição |
|---|---|---|
| `file` | `string` | Nome do arquivo `.pas` |
| `line` | `int` | Número da linha (0 se desconhecido) |
| `ref_type` | `string` | Tipo de referência: `table_definition`, `sql_inline`, `write_operation:insert`, etc. |

### `Attribute` object

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `name` | `string` | ✅ | Nome do atributo |
| `type` | `string` | ✅ | Tipo normalizado: `integer`, `string`, `datetime`, `decimal`, `boolean`, `text`, `float`, `unknown` |
| `nullable` | `boolean` | ✅ | Se permite NULL |
| `is_pk` | `boolean` | ✅ | Primary Key |
| `is_fk` | `boolean` | ✅ | Foreign Key (por convenção ou explícito) |
| `source` | `string` | ✅ | `ddl`, `inferred`, `dataset`, `synthetic` |

---

## `Relationship` object

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | ✅ | Identificador único (ex: `rel-0001`) |
| `source_entity` | `string` | ✅ | `id` da entidade source |
| `target_entity` | `string` | ✅ | `id` da entidade target |
| `cardinality` | `string` | ✅ | `one-to-one`, `one-to-many`, `many-to-one`, `many-to-many` |
| `type` | `string` | ✅ | `foreign_key_convention`, `foreign_key_explicit`, `inferred` |
| `source_columns` | `string[]` | ✅ | Colunas na entidade source |
| `target_columns` | `string[]` | ✅ | Colunas na entidade target |
| `confidence` | `string` | ✅ | `low`, `medium`, `high` |

---

## `Procedure` object

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | ✅ | Identificador único (ex: `proc-0001`) |
| `name` | `string` | ✅ | Nome da procedure/function |
| `kind` | `string` | ✅ | `stored_procedure`, `code_procedure` |
| `language` | `string` | ✅ | `sql`, `delphi` |
| `source_unit` | `string` | ✅ | Arquivo `.pas` de origem |
| `source_ref` | `object` | ⬜ | `{file, line}` |
| `module_owners` | `string[]` | ✅ | Módulos |
| `operations` | `string[]` | ✅ | Operações SQL executadas |
| `affected_entities` | `string[]` | ✅ | IDs de entidades afetadas |
| `loc` | `int` | ✅ | Lines of code |
| `complexity` | `string` | ✅ | `low`, `medium`, `high`, `unknown` |

---

## `modules` object

```json
{
  "Financeiro": {
    "entities": ["ent-0001", "ent-0002"],
    "relationships": ["rel-0001"],
    "procedures": ["proc-0001"]
  }
}
```

Este objeto agrega entidades/relacionamentos/procedures por módulo para
facilitar a geração de MERs parciais.

---

## Version History

| Versão | Data | Mudanças |
|---|---|---|
| 1.0.0 | 2026-01-15 | Versão inicial — schema mínimo viável (MVP) |
