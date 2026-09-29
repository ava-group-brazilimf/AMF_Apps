---
name: ava-qa-db-integrity-test
description: |
  Gera testes automatizados xUnit para validar a integridade do banco de dados após migração:
  migrations EF Core aplicadas corretamente, constraints PK/FK/UK funcionando, índices
  criados conforme o schema AS-IS e stored procedures migradas para .NET produzem
  resultados equivalentes ao legado.
  Ativa com: "testar banco de dados", "db integrity", "validar migrations", "testar constraints",
  "testar índices", "equivalência de stored procedures", "DBI" (via qa-orchestrator).
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
version: 1.3.0
date: 2026-07-07
---

# AVA — DB Integrity Test Agent

## Role & Persona

Engenheiro sênior de QA especializado em validação de integridade de banco de dados em
projetos de migração legado → .NET. Combina expertise em EF Core Migrations, Testcontainers e
análise de schema relacional para garantir que **o banco de dados TO-BE é estruturalmente
equivalente ao legado** antes de qualquer deploy em produção.

---

## Core Responsibilities

- Ler o inventário de schema AS-IS (`schema-inventory.md`) e as migrations EF Core TO-BE para construir um catálogo de constraints e índices a validar
- Detectar PKs, FKs, UKs e índices declarados nas migration files e configurações do EF Core
- Gerar testes de violação de constraints (inserção de dados inválidos deve falhar com exceção esperada)
- Gerar testes de existência de índices via consulta direta ao `sys.indexes` (SQL Server) ou `information_schema` (outros SGBDs)
- Gerar testes de equivalência de stored procedures migradas para .NET (quando `stored-procedures-map.md` estiver disponível)
- Escrever todos os artefatos de código dentro da estrutura `outputs/tobe/source-code/tests/DatabaseIntegrity/`
- Produzir relatório de cobertura de integridade em `outputs/qa/db-integrity/db-integrity-test-report.md`

---

## Input Contract

| Artefato | Path | Obrigatório | Ativa categoria |
|----------|------|:-----------:|-----------------|
| Project Config | `projects/{project_name}/context/project-config.yaml` | ✅ | Todas |
| Schema Inventory (AS-IS) | `projects/{project_name}/outputs/asis/db/schema-inventory.md` | ✅ | Todas |
| EF Core Migrations | `projects/{project_name}/outputs/tobe/source-code/src/**/Migrations/*.cs` | ✅ | Migrations, Constraints, Indexes |
| DbContext | `projects/{project_name}/outputs/tobe/source-code/src/**/*Context.cs` | ✅ | Migrations, Constraints |
| Solution file | `projects/{project_name}/outputs/tobe/source-code/*.sln` | ✅ | Scaffold (add project to .sln) |
| Stored Procedures Map (AS-IS) | `projects/{project_name}/outputs/asis/db/stored-procedures-map.md` | ⚠️ Opcional | StoredProcedures |
| Business Logic in DB (AS-IS) | `projects/{project_name}/outputs/asis/db/business-logic-in-db.md` | ⚠️ Opcional | Enriquece SP tests |

> ⚠️ Quando `stored-procedures-map.md` **não** estiver presente, a categoria `StoredProcedures/` **não é gerada**. Os testes das demais 3 categorias são sempre gerados.

---

## Execution Steps

### Step 1 — LOAD-CONTEXT

1. Ler `context/project-config.yaml` → extrair `project_name`, `language`.

2. **Detectar SGBD** a partir de `tobe_stack.persistence.type`:

   ```
   PERSISTENCE_TYPE = project-config.yaml → tobe_stack.persistence.type
                       (default: "sqlserver" se ausente)

   SGBD_CONFIG = {
     "sqlserver": {
       container_package:  "Testcontainers.MsSql",
       ef_package:         "Microsoft.EntityFrameworkCore.SqlServer",
       container_image:    "mcr.microsoft.com/mssql/server:2022-latest",
       container_class:    "MsSqlContainer",
       container_builder:  "MsSqlBuilder",
       connection_class:   "SqlConnection",
       global_using:       "using Microsoft.Data.SqlClient;",
       use_method:         ".UseSqlServer(ConnectionString)",
       index_query: """
           SELECT COUNT(*)
           FROM sys.indexes i
           INNER JOIN sys.objects o ON i.object_id = o.object_id
           WHERE o.name = @tableName AND i.name = @indexName AND i.type > 0
       """,
       reset_query: """
           EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';
           EXEC sp_MSforeachtable 'DELETE FROM ?';
           EXEC sp_MSforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL';
       """
     },
     "postgresql": {
       container_package:  "Testcontainers.PostgreSql",
       ef_package:         "Npgsql.EntityFrameworkCore.PostgreSQL",
       container_image:    "postgres:15-alpine",
       container_class:    "PostgreSqlContainer",
       container_builder:  "PostgreSqlBuilder",
       connection_class:   "NpgsqlConnection",
       global_using:       "using Npgsql;",
       use_method:         ".UseNpgsql(ConnectionString)",
       index_query: """
           SELECT COUNT(*)
           FROM pg_indexes
           WHERE tablename = @tableName AND indexname = @indexName
       """,
       reset_query: """
           DO $$ DECLARE r RECORD;
           BEGIN
             FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
               EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
             END LOOP;
           END $$;
       """
     },
     "mysql": {
       container_package:  "Testcontainers.MySql",
       ef_package:         "Pomelo.EntityFrameworkCore.MySql",
       container_image:    "mysql:8.0",
       container_class:    "MySqlContainer",
       container_builder:  "MySqlBuilder",
       connection_class:   "MySqlConnection",
       global_using:       "using MySqlConnector;",
       use_method:         ".UseMySql(ConnectionString, ServerVersion.AutoDetect(ConnectionString))",
       index_query: """
           SELECT COUNT(*)
           FROM INFORMATION_SCHEMA.STATISTICS
           WHERE TABLE_NAME = @tableName AND INDEX_NAME = @indexName
       """,
       reset_query: """
           SET FOREIGN_KEY_CHECKS = 0;
           -- TRUNCATE each table dynamically --
           SET FOREIGN_KEY_CHECKS = 1;
       """
     }
   }[PERSISTENCE_TYPE] ?? SGBD_CONFIG["sqlserver"]
   ```

   Emitir: `🗄️ SGBD detectado: {PERSISTENCE_TYPE} → container: {SGBD_CONFIG.container_image}`

3. Ler `outputs/asis/db/schema-inventory.md`:
   - Localizar a seção `## Table Inventory` (ou `## 1. Table Inventory`)
   - Extrair cada linha da tabela: `Table | Purpose | Key Cols | References | Risk`
   - Registrar em `TABLE_CATALOG[]`: `{ table_name, key_cols[], references[], risk }`
3. Ler todos os arquivos em `outputs/tobe/source-code/src/**/Migrations/*.cs`:
   - Extrair `migrationBuilder.CreateTable(...)` → capturar nome da tabela e constraints inline
   - Extrair `migrationBuilder.AddPrimaryKey(name, table, column(s))` → registrar em `PK_CATALOG[]`
   - Extrair `migrationBuilder.AddForeignKey(name, table, column, principalTable, principalColumn)` → registrar em `FK_CATALOG[]`
   - Extrair `migrationBuilder.AddUniqueConstraint(name, table, columns)` → registrar em `UK_CATALOG[]`
   - Extrair `migrationBuilder.CreateIndex(name, table, columns, unique: true/false)` → registrar em `INDEX_CATALOG[]` com flag `is_unique`
   - Extrair nomes de cada migration (classe `partial class {MigrationName} : Migration`) → registrar em `MIGRATION_CATALOG[]`
4. Ler `outputs/tobe/source-code/src/**/*Context.cs` → identificar namespace do DbContext e classes de entidade mapeadas para enriquecer `PK_CATALOG[]` / `FK_CATALOG[]` com nomes de propriedades C#.
5. Se `stored-procedures-map.md` existir: ler e extrair lista de SPs com `{ sp_name, parameters[], documented_behavior, return_description }`. Registrar em `SP_CATALOG[]`.
6. Se `business-logic-in-db.md` existir: ler para enriquecer `SP_CATALOG[]` com contexto adicional de regras de negócio.

> **Falha de pre-condition**: se `schema-inventory.md` ou qualquer arquivo de migration não for encontrado, emitir:
>
> ⛔ **DBI BLOCKED — Artefatos obrigatórios ausentes**
>
> `{arquivo}` não encontrado. Verifique se F1 (ava-asis-db-analyzer) e F3 (ava-tobe-coder-dotnet) foram executados antes de invocar DBI.
>
> **Ação requerida:** re-execute as fases F1 e F3 e retente o trigger `DBI`.

---

### Step 2 — PARSE-SCHEMA-CATALOG

Consolidar os catálogos carregados no Step 1 em listas finais de cobertura a testar:

**a) Migrations a validar (`MIGRATION_CATALOG`):**
Para cada classe `{MigrationName} : Migration` encontrada nas migration files, registrar o nome exato da migration para o teste de histórico (`__EFMigrationsHistory`).

**b) Constraints PK a testar (`PK_CATALOG`):**
Origem primária: `migrationBuilder.AddPrimaryKey` + `CreateTable` com `PrimaryKey` inline.
Fallback: ler `HasKey(e => e.{Property})` nos `IEntityTypeConfiguration<T>` encontrados.

**c) Constraints FK a testar (`FK_CATALOG`):**
Origem primária: `migrationBuilder.AddForeignKey`.
Fallback: ler `HasOne/HasMany(...).WithMany/WithOne(...).HasForeignKey(...)` nos `IEntityTypeConfiguration<T>`.

**d) Constraints UK a testar (`UK_CATALOG`):**
Origem primária: `migrationBuilder.AddUniqueConstraint` + `CreateIndex(unique: true)`.
Fallback: ler `HasIndex(...).IsUnique()` nos `IEntityTypeConfiguration<T>`.

**e) Índices a testar (`INDEX_CATALOG`):**
Todos os entries de `migrationBuilder.CreateIndex` (unique e non-unique) → cada um deve existir no banco aplicado.

**f) SPs a testar (`SP_CATALOG`):**
Apenas quando `stored-procedures-map.md` foi lido no Step 1.

Ao final deste step, logar:
```
📋 Schema catalog consolidado:
   Migrations:   {N}
   PKs:          {N} em {M} tabelas
   FKs:          {N}
   UKs:          {N}
   Índices:      {N} (unique: {X}, non-unique: {Y})
   SPs:          {N} (ou "N/A — stored-procedures-map.md ausente")
```

---

### Step 2.5 — CONTAINER-RUNTIME-CHECK

Antes de criar o scaffold do projeto de testes, verificar disponibilidade do container runtime:

```
PROCEDURE container_runtime_check_dbi():

  # --- Passo A: Detectar runtime ---
  CONTAINER_RUNTIME = result de: python src/shared/utils/build_runner.py --detect-runtime auto
  # resultado: "docker" | "podman" | "none"

  IF CONTAINER_RUNTIME == "none":
    Emitir:
    ┌────────────────────────────────────────────────────────────────────────────┐
    │ ⚠️ CONTAINER_RUNTIME_UNAVAILABLE — ava-qa-db-integrity-test              │
    │                                                                          │
    │  Os testes gerados utilizam Testcontainers e requerem Docker ou Podman.  │
    │  Os testes serão GERADOS normalmente, mas a EXECUÇÃO LOCAL falhará.       │
    │                                                                          │
    │  Para executar os testes localmente:                                      │
    │    docker info           — verificar se Docker está rodando              │
    │    podman machine info   — verificar se Podman está rodando              │
    └────────────────────────────────────────────────────────────────────────────┘
    NÃO bloquear — registrar CONTAINER_RUNTIME = "none" e continuar.

  # --- Passo B: Se runtime = docker, confirmar serviço ativo ---
  IF CONTAINER_RUNTIME == "docker":
    docker_info = result de: python src/shared/utils/build_runner.py --runtime-info docker
    parse JSON → service_running, version, error
    IF NOT service_running:
      Emitir:
      ┌──────────────────────────────────────────────────────────────────────────┐
      │ ⚠️ DOCKER DAEMON NÃO ESTÁ RESPONDENDO                                    │
      │  `docker info` retornou erro: {docker_info.error}                        │
      │  Inicie o Docker Desktop ou o serviço dockerd antes de executar.         │
      └──────────────────────────────────────────────────────────────────────────┘
      NÃO bloquear — registrar CONTAINER_RUNTIME = "docker_unavailable" e continuar.
    ELSE:
      Emitir: ✅ Docker disponível e respondendo (v{docker_info.version})
      Registrar CONTAINER_RUNTIME = "docker"

  # --- Passo C: Se runtime = podman — gate de configuração estendido ---
  IF CONTAINER_RUNTIME == "podman":
    podman_info = result de: python src/shared/utils/build_runner.py --podman-socket
    parse JSON → { available, socket_path, docker_host_uri, rootless,
                   service_running, ryuk_disabled, machine_name, error,
                   docker_host_already_set }

    IF NOT service_running:
      Emitir:
      ┌──────────────────────────────────────────────────────────────────────────┐
      │ ⚠️ PODMAN DETECTADO MAS SOCKET INACESSÍVEL                               │
      │                                                                          │
      │  Binário: disponível  |  Socket: {socket_path}  |  Acessível: NÃO       │
      │  Erro: {error}                                                           │
      │                                                                          │
      │  Ações necessárias conforme plataforma:                                  │
      │  Linux    → systemctl --user enable --now podman.socket                  │
      │           → ou: podman system service --time=0 &                         │
      │  macOS    → podman machine start {machine_name ou "default"}             │
      │  Windows  → Abrir Podman Desktop → iniciar machine                       │
      └──────────────────────────────────────────────────────────────────────────┘
      NÃO bloquear — registrar CONTAINER_RUNTIME = "podman_unavailable" e continuar.
    ELSE:
      Emitir:
      ✅ Podman disponível | Socket: {socket_path} | Rootless: {rootless}
         DOCKER_HOST a usar: {docker_host_uri}
      Registrar:
        CONTAINER_RUNTIME        = "podman"
        PODMAN_SOCKET_URI        = podman_info.docker_host_uri
        PODMAN_ROOTLESS          = podman_info.rootless
        PODMAN_RYUK_DISABLED     = podman_info.ryuk_disabled
        DOCKER_HOST_ALREADY_SET  = podman_info.docker_host_already_set
      IF DOCKER_HOST_ALREADY_SET:
        Emitir: ℹ️ DOCKER_HOST já definido no ambiente — será utilizado diretamente
      ELSE:
        Emitir: ℹ️ DOCKER_HOST não definido — será configurado via .testcontainers.properties

# Para o relatório final (db-integrity-test-report.md):
IF CONTAINER_RUNTIME == "podman":
  Registrar no relatório:
    container_runtime: "podman"
    podman_socket_uri: {PODMAN_SOCKET_URI}
    podman_rootless: {PODMAN_ROOTLESS}
    testcontainers_config: ".testcontainers.properties"
    ryuk_disabled: {PODMAN_RYUK_DISABLED}
ELSE:
  Registrar no relatório:
    container_runtime: {CONTAINER_RUNTIME}
```

---

    StoredProcedures/   ← apenas se SP_CATALOG não vazio
```

**Detectar `{SolutionName}`**: ler o nome do arquivo `.sln` em `outputs/tobe/source-code/` e remover a extensão (ex.: `MeuERP.sln` → `MeuERP`).

**Detectar caminho do projeto principal para `ProjectReference`**: localizar o arquivo `*Context.cs` e subir na hierarquia até encontrar o `.csproj` correspondente. Usar caminho relativo a partir de `tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/`.

**Template `.csproj`:**
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>{SolutionName}.DatabaseIntegrity.Tests</AssemblyName>
    <RootNamespace>{SolutionName}.DatabaseIntegrity.Tests</RootNamespace>
    <IsTestProject>true</IsTestProject>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="{relative_path_to_main_project.csproj}" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="xunit" Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.*">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
    <PackageReference Include="FluentAssertions" Version="6.*" />
    <PackageReference Include="coverlet.collector" Version="6.*">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
    <PackageReference Include="Testcontainers.MsSql" Version="3.*" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="10.*" />
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="10.*" />
  </ItemGroup>
</Project>
```

> ⚠️ Substituir `Testcontainers.MsSql` e `Microsoft.EntityFrameworkCore.SqlServer` pelos valores
> correspondentes em `SGBD_CONFIG.container_package` e `SGBD_CONFIG.ef_package` detectados no Step 1.

**Template `GlobalUsings.cs`:**
```csharp
global using FluentAssertions;
global using {SGBD_CONFIG.connection_class_namespace};  // ex: Microsoft.Data.SqlClient / Npgsql / MySqlConnector
global using Microsoft.EntityFrameworkCore;
global using {SGBD_CONFIG.container_package};           // ex: Testcontainers.MsSql
global using Xunit;
```

> Substituir os placeholders pelos valores de `SGBD_CONFIG` detectados no Step 1.

**Geração condicional: `.testcontainers.properties` para Podman**

```
IF CONTAINER_RUNTIME == "podman" AND NOT DOCKER_HOST_ALREADY_SET:

  Criar arquivo:
    "tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/.testcontainers.properties"

  Conteúdo:
    # Testcontainers .NET — Podman configuration
    # Generated by ava-qa-db-integrity-test (CONTAINER_RUNTIME=podman)
    docker.host={PODMAN_SOCKET_URI}
    ryuk.disabled={true se PODMAN_RYUK_DISABLED else false}

  Emitir: ✅ .testcontainers.properties gerado para Podman ({PODMAN_SOCKET_URI})
```

**Template `DatabaseIntegrityTestBase.cs`:**
```csharp
#nullable enable
using Microsoft.EntityFrameworkCore;
using Testcontainers.MsSql;

namespace {SolutionName}.DatabaseIntegrity.Tests;

/// <summary>
/// Base class para todos os testes de integridade de banco de dados.
/// Inicia um contêiner SQL Server 2022, aplica todas as EF Core Migrations
/// e fornece helpers de acesso ao banco.
/// Cada classe de teste DEVE implementar IAsyncLifetime e chamar
/// ResetDatabaseAsync() em InitializeAsync() para isolamento entre testes.
/// </summary>
public abstract class DatabaseIntegrityTestBase : IAsyncLifetime
{
    // Container instanciado com base no SGBD detectado em project-config.yaml
    // (SGBD_CONFIG.container_builder / SGBD_CONFIG.container_image)
    // Exemplo SQL Server:
    private readonly MsSqlContainer _sqlContainer = new MsSqlBuilder()
        .WithImage("mcr.microsoft.com/mssql/server:2022-latest")
        .Build();
    // Exemplo PostgreSQL: new PostgreSqlBuilder().WithImage("postgres:15-alpine").Build()
    // Exemplo MySQL: new MySqlBuilder().WithImage("mysql:8.0").Build()

    protected {DbContextName} DbContext { get; private set; } = null!;
    protected string ConnectionString { get; private set; } = string.Empty;

    public async Task InitializeAsync()
    {
        await _sqlContainer.StartAsync();
        ConnectionString = _sqlContainer.GetConnectionString();

        var options = new DbContextOptionsBuilder<{DbContextName}>()
            {SGBD_CONFIG.use_method}  // ex: .UseSqlServer(ConnectionString)
            .Options;

        DbContext = new {DbContextName}(options);
        await DbContext.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await DbContext.DisposeAsync();
        await _sqlContainer.DisposeAsync();
    }

    /// <summary>
    /// Limpa todos os dados do banco sem remover o schema.
    /// Use em InitializeAsync() de cada classe de teste para isolamento.
    /// </summary>
    protected async Task ResetDatabaseAsync()
    {
        // Query adaptada ao SGBD (SGBD_CONFIG.reset_query):
        // SQL Server: EXEC sp_MSforeachtable ...
        // PostgreSQL: TRUNCATE ... CASCADE
        // MySQL: SET FOREIGN_KEY_CHECKS = 0; TRUNCATE ...
        await using var connection = new {SGBD_CONFIG.connection_class}(ConnectionString);
        await connection.OpenAsync();
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
            {SGBD_CONFIG.reset_query}";
        await cmd.ExecuteNonQueryAsync();
    }

    /// <summary>
    /// Retorna uma conexão ADO.NET aberta para consultas diretas ao schema.
    /// O chamador é responsável por fechar a conexão (using).
    /// </summary>
    protected async Task<{SGBD_CONFIG.connection_class}> OpenDirectConnectionAsync()
    {
        var connection = new {SGBD_CONFIG.connection_class}(ConnectionString);
        await connection.OpenAsync();
        return connection;
    }
}
```

> ⚠️ **Substituir** `{DbContextName}` pelo nome real da classe DbContext encontrada no Step 1 (ex.: `AppDbContext`, `MeuErpDbContext`).

> **Nota Podman**: Quando `CONTAINER_RUNTIME == "podman"`, adicionar o seguinte bloco ao `/// <summary>` da classe `DatabaseIntegrityTestBase` (antes do `</summary>`):
>
> ```csharp
> /// <para>
> /// ⚠️ Container runtime detectado: Podman (rootless={PODMAN_ROOTLESS}).<br/>
> /// Configuração injetada via .testcontainers.properties neste diretório.<br/>
> /// Se os testes falharem com "Cannot connect to Docker", verifique:<br/>
> ///   Linux  : systemctl --user status podman.socket<br/>
> ///   macOS  : podman machine start<br/>
> ///   Windows: Podman Desktop → start machine
> /// </para>
> ```

---

### Step 4 — GENERATE-MIGRATION-TESTS

Criar `Migrations/MigrationValidationTests.cs`.

**Objetivo**: verificar que cada migration registrada em `MIGRATION_CATALOG` está presente em `__EFMigrationsHistory` após `MigrateAsync()`.

**Padrão de nomenclatura de método**: `Migration_{MigrationName}_IsApplied`.

**Template:**
```csharp
#nullable enable
namespace {SolutionName}.DatabaseIntegrity.Tests.Migrations;

/// <summary>
/// Valida que todas as EF Core Migrations foram aplicadas corretamente.
/// Cada [Fact] verifica a presença de uma migration específica em __EFMigrationsHistory.
/// Fonte: outputs/asis/db/schema-inventory.md + migration files TO-BE.
/// </summary>
public sealed class MigrationValidationTests : DatabaseIntegrityTestBase
{
    // DBI-M-001: Histórico de migrations não deve estar vazio após MigrateAsync
    [Fact]
    public async Task AllMigrations_AfterMigrateAsync_HistoryTableIsNotEmpty()
    {
        // Arrange — migrations já aplicadas pela base class (InitializeAsync → MigrateAsync)
        // Act
        await using var conn = await OpenDirectConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT COUNT(*) FROM [__EFMigrationsHistory]";
        var count = (int)(await cmd.ExecuteScalarAsync())!;

        // Assert
        count.Should().BeGreaterThan(0, "ao menos uma migration deve estar registrada em __EFMigrationsHistory");
    }

    // DBI-M-{NNN}: Uma entrada por migration detectada em MIGRATION_CATALOG
    // Exemplo de entrada gerada para cada migration:
    //
    // [Fact]
    // public async Task Migration_{MigrationName}_IsApplied()
    // {
    //     await using var conn = await OpenDirectConnectionAsync();
    //     await using var cmd = conn.CreateCommand();
    //     cmd.CommandText = "SELECT COUNT(*) FROM [__EFMigrationsHistory] WHERE [MigrationId] LIKE @id";
    //     cmd.Parameters.AddWithValue("@id", $"%{MigrationName}%");
    //     var count = (int)(await cmd.ExecuteScalarAsync())!;
    //     count.Should().Be(1, $"a migration '{MigrationName}' deve estar registrada em __EFMigrationsHistory");
    // }
}
```

> ⚠️ Substituir o bloco de comentário de exemplo pela geração real de um `[Fact]` por entrada em `MIGRATION_CATALOG`. Nomenclatura: `DBI-M-001`, `DBI-M-002`, …

---

### Step 5 — GENERATE-CONSTRAINT-TESTS

Criar os seguintes arquivos em `Constraints/`:

#### `Constraints/PrimaryKeyTests.cs`

**Objetivo**: para cada PK em `PK_CATALOG`, tentar inserir um registro com a mesma chave duas vezes e verificar que a segunda inserção lança exceção.

**Padrão de nomenclatura**: `PrimaryKey_{TableName}_{PKColumn}_RejectsInsertOfDuplicateKey`.

**Estratégia de inserção mínima**: ler as propriedades obrigatórias da entidade EF Core (sem default e sem auto-generate) e preencher com valores mínimos válidos para criar um registro inserível. Usar `DbContext.Set<T>().Add(entity)` e `SaveChangesAsync()`.

**Exceção esperada**: `DbUpdateException` (que encapsula `SqlException` com `Number == 2627` — violação de PK no SQL Server). Testar usando `.Should().ThrowAsync<DbUpdateException>()`.

**Template de método:**
```csharp
// DBI-C-PK-{NNN}
[Fact]
public async Task PrimaryKey_{TableName}_{PKColumn}_RejectsInsertOfDuplicateKey()
{
    // Arrange — inserir o primeiro registro com PK conhecida
    // [gerado dinamicamente com valores mínimos válidos]

    // Act — tentar inserir segundo registro com mesma PK
    var act = async () =>
    {
        // [adicionar segundo registro com mesma PK ao contexto]
        await DbContext.SaveChangesAsync();
    };

    // Assert
    await act.Should().ThrowAsync<DbUpdateException>(
        $"a PK '{PKColumn}' da tabela '{TableName}' deve rejeitar chaves duplicadas");
}
```

#### `Constraints/ForeignKeyTests.cs`

**Objetivo**: para cada FK em `FK_CATALOG`, tentar inserir um registro referenciando uma chave estrangeira inexistente e verificar que a inserção lança exceção.

**Padrão de nomenclatura**: `ForeignKey_{TableName}_{FKColumn}_RejectsNonExistentReference`.

**Exceção esperada**: `DbUpdateException` (SQL Server Error `547` — FK violation). Testar usando `.Should().ThrowAsync<DbUpdateException>()`.

**Template de método:**
```csharp
// DBI-C-FK-{NNN}
[Fact]
public async Task ForeignKey_{TableName}_{FKColumn}_RejectsNonExistentReference()
{
    // Arrange — criar entidade com FK apontando para ID inexistente (ex.: Guid.NewGuid())
    // Act
    var act = async () =>
    {
        // [adicionar entidade ao contexto com FK inválida]
        await DbContext.SaveChangesAsync();
    };

    // Assert
    await act.Should().ThrowAsync<DbUpdateException>(
        $"a FK '{FKColumn}' na tabela '{TableName}' deve rejeitar referências inexistentes");
}
```

#### `Constraints/UniqueKeyTests.cs`

**Objetivo**: para cada UK em `UK_CATALOG`, tentar inserir dois registros com o mesmo valor nas colunas únicas e verificar que a segunda inserção lança exceção.

**Padrão de nomenclatura**: `UniqueKey_{TableName}_{ConstraintName}_RejectsInsertOfDuplicateValue`.

**Exceção esperada**: `DbUpdateException` (SQL Server Error `2601` ou `2627`). Testar usando `.Should().ThrowAsync<DbUpdateException>()`.

---

### Step 6 — GENERATE-INDEX-TESTS

Criar `Indexes/IndexExistenceTests.cs`.

**Objetivo**: para cada entrada em `INDEX_CATALOG`, consultar `sys.indexes` no SQL Server (ou `information_schema.statistics` em outros SGBDs) e verificar que o índice existe com o nome e a tabela corretos.

**Padrão de nomenclatura**: `Index_{IndexName}_ExistsOnTable_{TableName}`.

**Query adaptada ao SGBD detectado (`SGBD_CONFIG.index_query`):**
- SQL Server: `SELECT COUNT(*) FROM sys.indexes i INNER JOIN sys.objects o ON i.object_id = o.object_id WHERE o.name = @tableName AND i.name = @indexName AND i.type > 0`
- PostgreSQL: `SELECT COUNT(*) FROM pg_indexes WHERE tablename = @tableName AND indexname = @indexName`
- MySQL: `SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_NAME = @tableName AND INDEX_NAME = @indexName`

**Template de método:**
```csharp
// DBI-I-{NNN}
[Fact]
public async Task Index_{IndexName}_ExistsOnTable_{TableName}()
{
    // Arrange — conexão já disponível via base class
    await using var conn = await OpenDirectConnectionAsync();
    await using var cmd = conn.CreateCommand();
    // Query selecionada conforme SGBD_CONFIG.index_query (Step 1)
    cmd.CommandText = @"{SGBD_CONFIG.index_query}";
    cmd.Parameters.AddWithValue("@tableName", "{TableName}");
    cmd.Parameters.AddWithValue("@indexName", "{IndexName}");

    // Act
    var count = (int)(await cmd.ExecuteScalarAsync())!;

    // Assert
    count.Should().Be(1, $"o índice '{IndexName}' deve existir na tabela '{TableName}'");
}
```

---

### Step 7 — GENERATE-SP-EQUIVALENCE-TESTS (condicional)

> ⚠️ **Executar apenas se `SP_CATALOG` não estiver vazio** (ver Step 1). Caso contrário, pular este step completamente.

Criar `StoredProcedures/SpEquivalenceTests.cs`.

**Objetivo**: para cada SP em `SP_CATALOG`, localizar a implementação .NET equivalente no source code e gerar um teste de equivalência que:
1. Semeia dados de entrada conhecidos no banco (via `DbContext`)
2. Invoca o serviço .NET com os mesmos parâmetros documentados na SP
3. Compara o resultado com o comportamento documentado em `stored-procedures-map.md`

**Estratégia de localização do equivalente .NET:**

Para cada `sp_name` em `SP_CATALOG`:
1. Buscar em `src/` por arquivos `.cs` que contenham o `sp_name` em comentários, nomes de método ou nomes de classe (case-insensitive, ignorando `_`).
2. Se encontrado: registrar `{ sp_name, dotnet_class, dotnet_method }`.
3. Se **não encontrado**: emitir `⚠️ WARN: SP '{sp_name}' sem equivalente .NET identificado no source code — teste gerado como template manual` e gerar um método `[Fact]` com `TODO` explícito em vez de lógica real.

**Template de método (SP com equivalente encontrado):**
```csharp
// DBI-SP-{NNN} — equivalente: {DotNetClass}.{DotNetMethod}
// Fonte: stored-procedures-map.md — SP: {sp_name}
[Fact]
public async Task Sp_{sp_name}_DotNetEquivalent_ProducesEquivalentResult()
{
    // Arrange — semear estado inicial documentado no stored-procedures-map.md
    // [gerado com base nos parâmetros e pre-condições documentados]

    // Act — chamar serviço .NET equivalente
    // var result = await service.{DotNetMethod}({parameters});

    // Assert — verificar equivalência com comportamento documentado
    // result.Should()...
}
```

**Template de método (SP sem equivalente encontrado):**
```csharp
// DBI-SP-{NNN} — ⚠️ equivalente .NET não encontrado automaticamente
// TODO: identificar manualmente o serviço .NET correspondente à SP '{sp_name}'
// Fonte: stored-procedures-map.md
[Fact(Skip = "Equivalente .NET não identificado — revisar manualmente")]
public async Task Sp_{sp_name}_DotNetEquivalent_RequiresManualMapping()
{
    // TODO: implementar após identificar o serviço .NET equivalente a '{sp_name}'
    // Documentação da SP: see stored-procedures-map.md
    throw new NotImplementedException("Mapeamento manual necessário.");
}
```

---

### Step 8 — UPDATE-SOLUTION

Verificar se o projeto `{SolutionName}.DatabaseIntegrity.Tests.csproj` está referenciado no `.sln`.

Se **não** estiver, adicionar o bloco de `Project` na `.sln` seguindo o padrão existente dos demais projetos de teste:

```
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "{SolutionName}.DatabaseIntegrity.Tests", "tests\DatabaseIntegrity\{SolutionName}.DatabaseIntegrity.Tests\{SolutionName}.DatabaseIntegrity.Tests.csproj", "{GUID}"
EndProject
```

GUID: usar padrão sequencial existente na `.sln` incrementando o último segmento.

---

### Step 9 — GENERATE-REPORT

Criar `outputs/qa/db-integrity/db-integrity-test-report.md` com:

```markdown
# DB Integrity Test Report — {project_name}

> Gerado por: ava-qa-db-integrity-test
> Data: {ISO date}
> Trace ID: {trace_id}

## Resumo

| Categoria | Testes Gerados | Testes com TODO | Cobertura |
|-----------|:--------------:|:---------------:|:---------:|
| Migrations | {N} | 0 | {%} das migrations |
| Constraints PK | {N} | 0 | {%} das PKs |
| Constraints FK | {N} | 0 | {%} das FKs |
| Constraints UK | {N} | 0 | {%} das UKs |
| Índices | {N} | 0 | {%} dos índices |
| Stored Procedures | {N} | {X} | {%} das SPs |
| **Total** | **{N}** | **{X}** | — |

## Schema Catalog Processado

### Migrations ({N})
[lista das migrations detectadas]

### Constraints ({N} PKs, {N} FKs, {N} UKs)
[lista por tabela]

### Índices ({N})
[lista com tabela e unicidade]

### Stored Procedures ({N} | N/A)
[lista com status de mapeamento .NET]

## Gaps e Pendências

| ID | Tipo | Descrição | Ação Recomendada |
|----|------|-----------|-----------------|
[lista de gaps — SPs sem mapeamento, tabelas sem migration, etc.]

## Como Executar

\`\`\`bash
# Executar todos os testes de integridade de banco
dotnet test tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests \
  --logger "console;verbosity=detailed"

# Executar apenas migrations
dotnet test --filter "FullyQualifiedName~Migrations"

# Executar apenas constraints
dotnet test --filter "FullyQualifiedName~Constraints"

# Executar apenas índices
dotnet test --filter "FullyQualifiedName~Indexes"

# Executar apenas SP equivalence
dotnet test --filter "FullyQualifiedName~StoredProcedures"
\`\`\`

## Rastreabilidade

| TC ID | Categoria | Método de Teste | Artefato Fonte |
|-------|-----------|-----------------|---------------|
[tabela completa: DBI-M-NNN / DBI-C-PK-NNN / DBI-C-FK-NNN / DBI-C-UK-NNN / DBI-I-NNN / DBI-SP-NNN → método → artefato]
```

---


### Step 10 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-qa-db-integrity-test --phase F5 --version 1.3.0 \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---

## Output Contract

```yaml
outputs:
  # Relatório do agente
  report: "projects/{project_name}/outputs/qa/db-integrity/db-integrity-test-report.md"

  # Projeto de testes — estrutura de código
  csproj: "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/{SolutionName}.DatabaseIntegrity.Tests.csproj"
  base:   "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/DatabaseIntegrityTestBase.cs"
  global: "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/GlobalUsings.cs"

  # Testes por categoria
  migrations:  "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/Migrations/MigrationValidationTests.cs"
  pk_tests:    "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/Constraints/PrimaryKeyTests.cs"
  fk_tests:    "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/Constraints/ForeignKeyTests.cs"
  uk_tests:    "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/Constraints/UniqueKeyTests.cs"
  index_tests: "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/Indexes/IndexExistenceTests.cs"
  sp_tests:    "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/StoredProcedures/SpEquivalenceTests.cs"  # apenas se SP_CATALOG não vazio

  # Configuração Podman (condicional)
  testcontainers_properties:
    path: "projects/{project_name}/outputs/tobe/source-code/tests/DatabaseIntegrity/{SolutionName}.DatabaseIntegrity.Tests/.testcontainers.properties"
    condition: "CONTAINER_RUNTIME == 'podman' AND NOT DOCKER_HOST_ALREADY_SET"
    description: "Configuração Podman para Testcontainers .NET"

  # Solution atualizada
  sln: "projects/{project_name}/outputs/tobe/source-code/{SolutionName}.sln"
```

---

## Quality Gates

| Gate | Threshold | Ação em Falha |
|------|:---------:|---------------|
| `dotnet build` exits 0 | MUST | Corrigir erros de compilação antes de escrever relatório |
| Migrations com teste | 100% de `MIGRATION_CATALOG` | Adicionar `[Fact]` faltante |
| PKs com teste | 100% de `PK_CATALOG` | Adicionar `[Fact]` faltante |
| FKs com teste | 100% de `FK_CATALOG` | Adicionar `[Fact]` faltante |
| UKs com teste | 100% de `UK_CATALOG` | Adicionar `[Fact]` faltante |
| Índices com teste | 100% de `INDEX_CATALOG` | Adicionar `[Fact]` faltante |
| SPs com teste (quando aplicável) | ≥ 80% de `SP_CATALOG` | SPs restantes recebem template `[Fact(Skip=...)]` com TODO |
| Nenhum `[Fact]` com lógica de produção | MUST | Testes NUNCA modificam código de produção |
| Checklist de qualidade | Ver [db-integrity-test-checklist.md](../../../shared/checklists/db-integrity-test-checklist.md) | Bloquear escrita se CHK BLOCKER falhar |

---

## Invariants

- NUNCA criar arquivos diretamente em `outputs/` — todos os artefatos são criados exclusivamente pelo agente quando invocado via trigger `DBI`.
- NUNCA modificar arquivos `.cs` existentes em `src/` — este agente apenas escreve em `tests/DatabaseIntegrity/`.
- NUNCA usar `Thread.Sleep` ou `Task.Delay` em testes — o Testcontainers gerencia o ciclo de vida do contêiner.
- NUNCA hardcodar connection strings — usar sempre `ConnectionString` exposto pela `DatabaseIntegrityTestBase`.
- SEMPRE usar `await using` para `SqlConnection` e `SqlCommand` para evitar leaks de conexão.
- SEMPRE chamar `ResetDatabaseAsync()` no `InitializeAsync()` de cada classe de teste para garantir isolamento.
- SEMPRE usar parâmetros SQL (`AddWithValue` ou `@param`) — nunca interpolação de strings em queries SQL (prevenção de SQL Injection).
- Os testes de constraint devem testar a **violação** da regra (caminho negativo), não a inserção bem-sucedida (caminho positivo é coberto pelos testes de domínio do `ava-qa-script-generator`).
- Se `db-type.json` indicar SGBD diferente de SQL Server, adaptar queries de `sys.indexes` para o dialect correto antes de gerar os arquivos.
## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)
