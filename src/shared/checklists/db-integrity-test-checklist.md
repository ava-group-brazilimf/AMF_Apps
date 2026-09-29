---
name: db-integrity-test-checklist
description: "Checklist de validação obrigatório para o agente ava-qa-db-integrity-test antes de finalizar outputs"
version: "1.1.0"
agent: "ava-qa-db-integrity-test"
gate: "Step 8 — UPDATE-SOLUTION (antes de gerar o relatório final)"
---

# DB Integrity Test — Validation Checklist

> **Quando aplicar**: O agente `ava-qa-db-integrity-test` DEVE executar este checklist
> antes de escrever os arquivos finais (Step 9 — GENERATE-REPORT).
> Todos os critérios de severidade `BLOCKING` devem passar para que o gate seja `✅ PASS`.
> Critérios `WARNING` podem passar com ressalva (`⚠️ PASS_WITH_WARNINGS`).

---

## Critérios de Validação

| #  | ID | Critério | Severidade | Regra | Ação se falhar |
|----|----|----------|:----------:|-------|----------------|
| 1  | `CHK-DB-MIGRATION` | Cobertura de migrations | `BLOCKING` | Cada migration em `MIGRATION_CATALOG` tem ≥ 1 `[Fact]` em `MigrationValidationTests.cs` | Adicionar `[Fact]` para a migration sem cobertura |
| 2  | `CHK-DB-PK` | Cobertura de PKs | `BLOCKING` | Cada PK em `PK_CATALOG` tem ≥ 1 `[Fact]` de violação em `PrimaryKeyTests.cs` | Adicionar `[Fact]` de violação para a PK descoberta |
| 3  | `CHK-DB-FK` | Cobertura de FKs | `BLOCKING` | Cada FK em `FK_CATALOG` tem ≥ 1 `[Fact]` de violação em `ForeignKeyTests.cs` | Adicionar `[Fact]` de violação para a FK descoberta |
| 4  | `CHK-DB-UK` | Cobertura de UKs | `BLOCKING` | Cada UK em `UK_CATALOG` tem ≥ 1 `[Fact]` de violação em `UniqueKeyTests.cs` | Adicionar `[Fact]` de violação para a UK descoberta |
| 5  | `CHK-DB-INDEX` | Cobertura de índices | `BLOCKING` | Cada índice em `INDEX_CATALOG` tem ≥ 1 `[Fact]` de existência em `IndexExistenceTests.cs` | Adicionar `[Fact]` de existência para o índice descoberto |
| 6  | `CHK-DB-BASE` | Classe base presente | `BLOCKING` | `DatabaseIntegrityTestBase.cs` existe, aplica migrations via `MigrateAsync()` e expõe `ResetDatabaseAsync()` e `OpenDirectConnectionAsync()` | Criar ou corrigir `DatabaseIntegrityTestBase.cs` conforme template |
| 7  | `CHK-DB-SP-EQUIV` | Cobertura de SPs (quando aplicável) | `BLOCKING` | Se `SP_CATALOG` não estiver vazio: ≥ 80% das SPs têm `[Fact]` real (não `Skip`) em `SpEquivalenceTests.cs` | Mapear equivalente .NET faltante ou marcar explicitamente como `[Fact(Skip=...)]` com TODO |
| 8  | `CHK-DB-CONN-STRING` | Sem connection string hardcoded | `BLOCKING` | Nenhum arquivo `.cs` gerado contém string literal de connection string — todos usam `ConnectionString` da base class | Substituir pela propriedade `ConnectionString` exposta pela base class |
| 9  | `CHK-DB-CLEANUP` | Isolamento entre testes | `WARNING` | Cada classe de teste implementa `IAsyncLifetime` e chama `ResetDatabaseAsync()` em `InitializeAsync()` | Adicionar `IAsyncLifetime` e `ResetDatabaseAsync()` na classe de teste |
| 10 | `CHK-DB-NAMING` | Nomenclatura de métodos | `WARNING` | Métodos seguem padrão `{Entity/Constraint/Index}_{Scenario}_{ExpectedResult}` (ex.: `PrimaryKey_Pedido_Id_RejectsInsertOfDuplicateKey`) | Renomear método para seguir a convenção |
| 11 | `CHK-DB-SQL-PARAM` | Sem interpolação SQL | `WARNING` | Nenhuma query ADO.NET usa interpolação de string — todas usam `cmd.Parameters.AddWithValue(...)` | Substituir interpolação por parâmetros SQL |
| 12 | `CHK-DB-TRACEABILITY` | Rastreabilidade TC-ID | `WARNING` | Cada `[Fact]` tem comentário `// DBI-{categoria}-{NNN}` acima da declaração | Adicionar comentário de rastreabilidade ao `[Fact]` |
| 13 | `CHK-DB-SLN` | Projeto na solution | `WARNING` | `{SolutionName}.DatabaseIntegrity.Tests.csproj` está referenciado no arquivo `.sln` | Adicionar bloco `Project(...)EndProject` na `.sln` |
| 14 | `CHK-DB-RUNTIME` | Container runtime disponível | `WARNING` | Docker ou Podman está rodando (verificado no Step 2.5) | Instalar Docker Desktop ou iniciar `podman machine start` antes da execução dos testes |
| 15 | `CHK-DB-SGBD-MATCH` | SGBD alinhado com project-config.yaml | `BLOCKING` | O Testcontainer image (`SGBD_CONFIG.container_image`) e as queries de schema (`SGBD_CONFIG.index_query`) correspondem ao `tobe_stack.persistence.type` configurado | Verificar Step 1 — SGBD_CONFIG e garantir consistência entre `project-config.yaml` e templates gerados |

---

## Gate Logic

```
BLOCKING_PASS  = ALL critérios com severidade BLOCKING passaram
WARNING_COUNT  = COUNT de critérios WARNING que falharam

if NOT BLOCKING_PASS:
    gate = ❌ FAIL
    action = Corrigir todos os BLOCKING antes de prosseguir para Step 9
elif WARNING_COUNT > 0:
    gate = ⚠️ PASS_WITH_WARNINGS
    action = Registrar warnings no relatório, prosseguir para Step 9
else:
    gate = ✅ PASS
    action = Prosseguir para Step 9
```

---

## Template de Resultado (para inclusão no relatório)

```markdown
## Validation Checklist

| #  | ID | Critério | Status | Detalhes |
|----|----|----------|:------:|----------|
| 1  | CHK-DB-MIGRATION | Cobertura de migrations | ✅ / ❌ | {N}/{total} migrations cobertas |
| 2  | CHK-DB-PK | Cobertura de PKs | ✅ / ❌ | {N}/{total} PKs cobertas |
| 3  | CHK-DB-FK | Cobertura de FKs | ✅ / ❌ | {N}/{total} FKs cobertas |
| 4  | CHK-DB-UK | Cobertura de UKs | ✅ / ❌ | {N}/{total} UKs cobertas |
| 5  | CHK-DB-INDEX | Cobertura de índices | ✅ / ❌ | {N}/{total} índices cobertos |
| 6  | CHK-DB-BASE | Classe base presente | ✅ / ❌ | DatabaseIntegrityTestBase.cs {encontrada / ausente} |
| 7  | CHK-DB-SP-EQUIV | Cobertura de SPs | ✅ / ❌ / N/A | {N}/{total} SPs com teste real ({%}) |
| 8  | CHK-DB-CONN-STRING | Sem connection string hardcoded | ✅ / ❌ | {N} ocorrências encontradas |
| 9  | CHK-DB-CLEANUP | Isolamento entre testes | ✅ / ⚠️ | {N}/{total} classes com ResetDatabaseAsync |
| 10 | CHK-DB-NAMING | Nomenclatura de métodos | ✅ / ⚠️ | {N} métodos fora do padrão |
| 11 | CHK-DB-SQL-PARAM | Sem interpolação SQL | ✅ / ⚠️ | {N} ocorrências de interpolação |
| 12 | CHK-DB-TRACEABILITY | Rastreabilidade TC-ID | ✅ / ⚠️ | {N}/{total} [Fact]s sem comentário DBI-ID |
| 13 | CHK-DB-SLN | Projeto na solution | ✅ / ⚠️ | Projeto {referenciado / não referenciado} na .sln |
| 14 | CHK-DB-RUNTIME | Container runtime | ✅ / ⚠️ | Container runtime {disponível / indisponível} |
| 15 | CHK-DB-SGBD-MATCH | SGBD alinhado | ✅ / ❌ | Testcontainer e queries {alinhados / desalinhados} com {persistence.type} |

**Gate Result:** ✅ PASS / ⚠️ PASS_WITH_WARNINGS / ❌ FAIL
```
