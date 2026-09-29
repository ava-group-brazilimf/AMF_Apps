---
name: ava-build-cycle-dotnet-scaffold
version: "1.0.0"
description: |
  Lê o architecture-blueprint.md e o ConfigStackDotNet.yaml, extrai os bounded contexts
  identificados e gera o scaffolding completo da solução .NET 9/10 em Clean Architecture:
  solution file, projetos .csproj por camada (Domain / Application / Infrastructure / API / Tests),
  global.json, Directory.Build.props, Directory.Packages.props (CPM) e estrutura de pastas.
  CQRS é configurável via architecture_patterns.cqrs em ConfigStackDotNet.yaml:
    true  → Application layer com Commands/ Queries/ Handlers/ Validators/ (MediatR)
    false → Application layer com Services/ Interfaces/ DTOs/ (serviços simples)
  Ativa com: "gerar scaffolding .NET", "criar solução Clean Architecture",
  "scaffold bounded context", "gerar estrutura projeto .NET", "build cycle scaffold",
  "create dotnet solution", "generate .NET solution structure", "scaffolding .NET 9".
allowed-tools: Read, Write, Edit, Bash, Glob
---

# AVA — Build Cycle .NET Scaffold Agent

> **Agent:** `ava-build-cycle-dotnet-scaffold`
> **Role:** Gera o scaffolding completo da solução .NET a partir dos bounded contexts do blueprint.
> **Trigger:** Executar após Wave 1 (IaC gerado). Pré-condição para todos os agentes de código backend.

## Role & Persona

Arquiteto de Software .NET especialista em Clean Architecture e DDD.

---

> ⛔ **Package guardrails (pacotes proibidos, versões canônicas, transitive override):**
> Ver [@dotnet-nuget-policy](../../tobe-architecture/agents/dotnet-nuget-policy.md) — seções "CRITICAL PACKAGE GUARDRAILS" e "Tabela Canônica de Versões".

Gera a estrutura esqueleto da solução — projetos, referências entre camadas,
packages centralizados e arquivos de configuração — sem gerar lógica de negócio.
O scaffolding é o contrato estrutural que todos os demais agentes de código (CQRS,
EF Core, Minimal APIs) seguirão. Por isso, nomes e referências devem ser precisos e consistentes.

## Input Contract

```yaml
inputs:
  project_name: string          # Lido de project-config.yaml
  dotnet_sdk_version: string    # Lido de ConfigStackDotNet.yaml → tobe_stack.dotnet_sdk_version
  backend_version: string       # Lido de ConfigStackDotNet.yaml → tobe_stack.backend_version
  cqrs: boolean                 # Lido de ConfigStackDotNet.yaml → architecture_patterns.cqrs
  bounded_contexts: string[]    # Lido de architecture-blueprint.md (extração automática)
  solution_layers: string[]     # Lido de ConfigStackDotNet.yaml → solution_layers
  trace_id: string
```

## Execution Steps

### Step 1 — Leitura de Contexto

> Apply: [@backend-context-protocol](../../shared/backend-context-protocol.md) — `@backend-override-resolution` + `@backend-dotnet-invariants`

```
1.0  Override resolution: ver @backend-override-resolution acima.

1.1  Ler project-config.yaml:
     → project_name, context_stack_base_path

1.2  Ler ConfigStackDotNet.yaml (via context_stack_base_path):
     → tobe_stack.dotnet_sdk_version   (ex: "9.0.x")
     → tobe_stack.backend_version      (ex: "9.0")
     → architecture_patterns.cqrs      (true | false)
     → architecture_patterns.mediator  (ex: "mediatr")
     → solution_layers                 (["Domain","Application","Infrastructure","Presentation","Tests"])
     → persistence.orm                 (ex: "efcore")
     → persistence.read_model          (ex: "dapper")
     → persistence.cache_provider      (ex: "redis")
     → auth.provider                   (ex: "azure-ad")

1.3  Ler outputs/tobe/docs/architecture-blueprint.md:
     → Extrair bounded contexts: procurar por seções "## {Nome}" ou blocos "Bounded Context: {Nome}"
       ou lista "bounded_contexts:" no front-matter do arquivo
     → SE nenhum BC encontrado → perguntar ao usuário: "Liste os bounded contexts separados por vírgula"
     → Normalizar nomes: PascalCase, sem espaços (ex: "Gestão de Pedidos" → "GestãoPedidos" → "Pedidos")

1.4  Derivar solution_prefix: PascalCase de project_name sem espaços/hífens
     Ex: "Meu-ERP" → "MeuERP"

1.5  Exibir plano antes de gerar:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ 🏗️  BUILD CYCLE — Scaffolding .NET {backend_version}                  │
     │                                                                      │
     │  Solução    : {solution_prefix}.sln                                  │
     │  SDK        : {dotnet_sdk_version}                                   │
     │  CQRS       : {cqrs} ({mediator})                                    │
     │  BCs        : {lista de bounded contexts}                            │
     │  Projetos   : {N BCs × 4 camadas} + Shared (2) + Tests              │
     └──────────────────────────────────────────────────────────────────────┘
```

### Step 1.6 — Resolução de Versões NuGet (OBRIGATÓRIO antes do Step 2)

> ⛔ **GUARDRAIL:** Versões de pacotes NuGet **NUNCA** são hardcoded neste agente.
> Todas as versões são resolvidas dinamicamente consultando a NuGet API pública no momento
> da geração. Isso garante compatibilidade com o TFM alvo e pacotes sempre atualizados.
>
> Este step DEVE ser executado antes do Step 2.3 (Directory.Packages.props).
> O resultado (`resolved_versions`) é o único input aceito para escrever `<PackageVersion>`.

```
PROTOCOLO DE RESOLUÇÃO NUGET
============================

Input:  backend_version   (ex: "10.0", "9.0", "8.0")  ← lido no Step 1.2
        package_list      (lista de todos os pacotes do Step 6 — Package Catalog)

Para CADA pacote em package_list, executar:

PASSO A — Obter versões disponíveis
  GET https://api.nuget.org/v3-flatcontainer/{packageId-lowercase}/index.json
  → Extrair lista de versões estáveis (sem sufixo -preview / -rc / -beta / -alpha)
  → Ordenar descendente → candidato = versão mais recente estável

PASSO B — Verificar compatibilidade com o TFM
  GET https://api.nuget.org/v3-flatcontainer/{packageId-lowercase}/{version}/{packageId-lowercase}.nuspec
  → Parsear <dependencies> → procurar <group targetFramework=".NETCoreApp{backend_version}">
    OU <group targetFramework="net{backend_version}">
    OU <group> sem targetFramework (compatível com todos os TFMs)
  SE nenhum grupo compatível encontrado:
    → Tentar próxima versão estável mais recente na lista
    → Repetir até encontrar versão compatível OU esgotar lista
  SE lista esgotada sem compatibilidade:
    → BLOCKED: "Pacote {packageId} não tem versão estável compatível com net{backend_version}.
                Verificar manualmente em https://www.nuget.org/packages/{packageId}"

PASSO C — Aplicar floor de segurança (dotnet-nuget-policy.md)
  Ler [@dotnet-nuget-policy](../../tobe-architecture/agents/dotnet-nuget-policy.md)
  → Seção "Security Floors" → verificar se o pacote tem versão mínima por CVE
  SE versão_resolvida < floor_mínimo:
    → Usar floor_mínimo como versão final
    → Logar: "⚠️ {packageId}: versão {versão_resolvida} substituída por floor de segurança {floor_mínimo}"

PASSO D — Registrar resultado
  resolved_versions[packageId] = versão_final

Ao final: exibir tabela de resolução antes de prosseguir para Step 2:
  ┌───────────────────────────────────────────────────────────────────────────┐
  │ 📦 NuGet Resolution — net{backend_version}                                │
  │                                                                           │
  │  PackageId                                  Versão Resolvida   Fonte      │
  │  ─────────────────────────────────────────  ─────────────────  ────────── │
  │  Carter                                     8.2.1              NuGet API  │
  │  MediatR                                    12.4.1             NuGet API  │
  │  FluentValidation                           11.11.0            NuGet API  │
  │  Microsoft.EntityFrameworkCore.SqlServer    10.0.0             NuGet API  │
  │  ...                                        ...                ...        │
  └───────────────────────────────────────────────────────────────────────────┘

SE qualquer pacote retornar BLOCKED → interromper geração e reportar ao usuário.
SE NuGet API inacessível (timeout/offline):
  → BLOCKED: "NuGet API inacessível. Sem resolução dinâmica de versões não é possível garantir
    compatibilidade com net{backend_version}. Verificar conexão ou consultar
    https://www.nuget.org/packages manualmente e fornecer as versões como input."
  → NÃO usar versões de memória de treinamento como fallback — dados de treinamento são defasados.
```

### Step 2 — Gerar Arquivos de Configuração da Solução

```
2.1  global.json
     {
       "sdk": {
         "version": "{dotnet_sdk_version}",
         "rollForward": "latestMinor",
         // ⚠️ GUARDRAIL: Use "latestMinor", NOT "latestPatch".
         // "latestPatch" fails when the installed SDK has a different feature band
         // (e.g., 8.0.4xx vs 8.0.1xx). "latestMinor" picks the highest installed
         // patch within the major, making the solution resilient across dev machines
         // and CI/CD agents without requiring a specific SDK feature band.
         "allowPrerelease": false
       }
     }

2.2  Directory.Build.props
     <Project>
       <PropertyGroup>
         <TargetFramework>net{backend_version}</TargetFramework>
         <Nullable>enable</Nullable>
         <ImplicitUsings>enable</ImplicitUsings>
         <AnalysisLevel>latest-recommended</AnalysisLevel>
         <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
         <LangVersion>latest</LangVersion>
         <WarningsAsErrors></WarningsAsErrors>
         <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
         <!-- Redireciona bin/obj para fora do repo encurtando o caminho total.
              O target CreateBaseOutputDirs abaixo garante que o diretorio exista. -->
         <BaseOutputPath Condition="$([MSBuild]::IsOSPlatform('Windows'))">C:\avaout\$(MSBuildProjectName)\bin\</BaseOutputPath>
         <BaseIntermediateOutputPath Condition="$([MSBuild]::IsOSPlatform('Windows'))">C:\avaout\$(MSBuildProjectName)\obj\</BaseIntermediateOutputPath>
         <GenerateDocumentationFile>true</GenerateDocumentationFile>
         <!-- NuGetAuditMode=direct: audit only directly-referenced packages, not transitive.
              Transitive deps (e.g. System.Security.Cryptography.Xml pulled by EF Core / SqlClient)
              cannot be controlled by this solution; auditing them causes NU1902/NU1903 errors
              on packages owned by upstream vendors (Microsoft). Direct packages are fully
              controlled and patched via Directory.Packages.props. -->
         <NuGetAuditMode>direct</NuGetAuditMode>
         <!-- ⚠️ GUARDRAIL: CS1591 suppressed globally.
              GenerateDocumentationFile=true + TreatWarningsAsErrors=true (não ativo nesta configuração)
              causaria CS1591 em todo membro público sem XML doc comment. Agents generate skeleton
              code without XML docs → build always fails without this suppression.
              CA1716 and CA1000 are DDD conventions (Error type, Result<T> factory pattern).
              CA1711: IDomainEventHandler ends in 'EventHandler' by DDD convention — intentional.
              IDE0011: Generated skeleton code may omit braces on single-statement if blocks;
                       EnforceCodeStyleInBuild=true escalates this to error in CI. -->
         <NoWarn>$(NoWarn);CS1591;CA1716;CA1000;CA1711;IDE0011;ASPDEPR002;CA1050</NoWarn>
       </PropertyGroup>

       <Target Name="CreateBaseOutputDirs" BeforeTargets="BeforeBuild" Condition="$([MSBuild]::IsOSPlatform('Windows'))">
         <MakeDir Directories="$(BaseOutputPath);$(BaseIntermediateOutputPath)" />
       </Target>
     </Project>

2.3  Directory.Packages.props  (Central Package Management — OBRIGATÓRIO neste step)
     > ⛔ **GUARDRAIL CPM:** Este arquivo DEVE ser gerado AGORA, neste Step 2, ANTES de qualquer
     > `.csproj` (Steps 3–5). Todos os `<PackageReference>` gerados são sem versão (CPM-only).
     > Se `Directory.Packages.props` estiver ausente quando o restore executar, NuGet dispara
     > NU1015 em TODOS os projetos com PackageReference sem versão.
     > ⛔ NÃO pule este passo. ⛔ NÃO mova para depois do Step 3.
     → Conteúdo: usar o catálogo do "Step 6 — Package Catalog" com versões de `resolved_versions` (Step 1.6)
     → ManagePackageVersionsCentrally = true
     → Cada `<PackageVersion Include="X" Version="Y" />` usa Y = `resolved_versions['X']` — nunca versão de memória de treinamento

2.4  .editorconfig
     → root = true
     → [*.cs]: indent_style=space, indent_size=4, csharp_style_namespace_declarations=file_scoped
     → dotnet_sort_system_directives_first=true
     → dotnet_style_qualification_for_field=false

2.5  NuGet.config
     → Source: nuget.org (https)
     → Sem credenciais hardcoded

2.6  .gitignore
     → Template padrão dotnet (bin/, obj/, *.user, .vs/, .idea/)
     → Adicionar: *.env, appsettings.*.json (exceto Development), secrets/

2.7  {solution_prefix}.sln
     → Incluir todos os projetos gerados
     → Organizar em solution folders por bounded context:
       Solution Items/  → global.json, Directory.Build.props, Directory.Packages.props
       src/Shared/      → SharedKernel + Contracts
       src/{BC1}/       → 4 projetos do BC1
       src/{BC2}/       → 4 projetos do BC2
       tests/           → todos os Test projects
```

### Step 3 — Gerar Projetos Shared

> ⛔ **PRÉ-FLIGHT OBRIGATÓRIO antes do Step 3:**
> Verificar que `Directory.Packages.props` foi gerado (Step 2.3).
> SE ausente → BLOCKED: "Gere Directory.Packages.props (Step 2.3) antes de continuar.
> Todos os PackageReference são sem versão (CPM-only). Sem CPM, NU1015 ocorre em todos os projetos."

```
Gerar 2 projetos shared (sem BC prefix):

3.1  src/Shared/{solution_prefix}.SharedKernel/
     {solution_prefix}.SharedKernel.csproj:
       <PropertyGroup>
         <!-- ⚠️ GUARDRAIL: CS1591/CA1716/CA1000 suppressed for SharedKernel.
              Already covered by Directory.Build.props globally; kept here for explicitness. -->
         <NoWarn>$(NoWarn);CS1591;CA1716;CA1000</NoWarn>
       </PropertyGroup>
       <!-- ⚠️ GUARDRAIL: Microsoft.EntityFrameworkCore (base package) is required here.
            SharedKernel contains AuditInterceptor and base entity types that reference
            EF Core types (SaveChangesInterceptor, EntityState, ChangeTracker, etc.).
            WITHOUT this reference the project will not compile even though
            Microsoft.EntityFrameworkCore.SqlServer is present in Infrastructure —
            that package does NOT transitively export the base EF Core types to SharedKernel. -->
       <PackageReference Include="Microsoft.EntityFrameworkCore" />
       <PackageReference Include="MediatR" />   ← SE cqrs: true
       Sem referências a outros projetos da solução

     Estrutura de pastas:
       Domain/
         Primitives/
           Entity.cs          ← classe base abstrata Entity<TId>
           AggregateRoot.cs   ← herda Entity, lista de DomainEvents
           ValueObject.cs     ← record abstrato com igualdade estrutural
           IDomainEvent.cs    ← interface marker
         Common/
           Result.cs          ← Result<T, TError> para evitar exceptions no domínio
           Error.cs           ← record Error(string Code, string Description)
           PagedList.cs       ← para queries paginadas

3.2  src/Shared/{solution_prefix}.Contracts/
     {solution_prefix}.Contracts.csproj:
       Sem PackageReferences externos (apenas tipos primitivos e records)

     Estrutura de pastas:
       IntegrationEvents/     ← eventos publicados para outros BCs
         {vazio — preenchido pelos agentes de domínio}
```

### Step 4 — Gerar Projetos por Bounded Context

> Repetir para cada BC em bounded_contexts[]:

> ⚠️ **GUARDRAIL — ProjectReference: Regras de Caminho (OBRIGATÓRIO)**
>
> Todas as `<ProjectReference>` DEVEM incluir o nome do arquivo `.csproj` no final.
> `<ProjectReference Include="../Foo" />` é INVÁLIDO — NuGet não resolve diretórios.
>
> **Tabela de profundidade por layer** (estrutura: `source-code/src/{BC}/{Prefix}.{BC}.Layer/`):
>
> | Projeto origem | Destino | Caminho correto |
> |----------------|---------|-----------------|
> | `src/{BC}/{Pfx}.{BC}.Domain/` | SharedKernel | `../../Shared/{Pfx}.SharedKernel/{Pfx}.SharedKernel.csproj` |
> | `src/{BC}/{Pfx}.{BC}.Application/` | Domain (mesmo BC) | `../{Pfx}.{BC}.Domain/{Pfx}.{BC}.Domain.csproj` |
> | `src/{BC}/{Pfx}.{BC}.Infrastructure/` | Domain (mesmo BC) | `../{Pfx}.{BC}.Domain/{Pfx}.{BC}.Domain.csproj` |
> | `src/{BC}/{Pfx}.{BC}.Infrastructure/` | Application (mesmo BC) | `../{Pfx}.{BC}.Application/{Pfx}.{BC}.Application.csproj` |
> | `src/{BC}/{Pfx}.{BC}.Api/` | Application (mesmo BC) | `../{Pfx}.{BC}.Application/{Pfx}.{BC}.Application.csproj` |
> | `src/{BC}/{Pfx}.{BC}.Api/` | Infrastructure (mesmo BC) | `../{Pfx}.{BC}.Infrastructure/{Pfx}.{BC}.Infrastructure.csproj` |
> | `hosts/{Pfx}.Api/` | SharedKernel | `../../src/Shared/{Pfx}.SharedKernel/{Pfx}.SharedKernel.csproj` |
> | `tests/{BC}/{Pfx}.{BC}.Tests.Unit/` | Application | `../../../src/{BC}/{Pfx}.{BC}.Application/{Pfx}.{BC}.Application.csproj` |
> | `tests/{BC}/{Pfx}.{BC}.Tests.Unit/` | Domain | `../../../src/{BC}/{Pfx}.{BC}.Domain/{Pfx}.{BC}.Domain.csproj` |
> | `tests/{BC}/{Pfx}.{BC}.Tests.Integration/` | Api | `../../../src/{BC}/{Pfx}.{BC}.Api/{Pfx}.{BC}.Api.csproj` |
>
> **Fórmula de verificação:** profundidade = nível do `.csproj` em relação a `source-code/`.
> `src/{BC}/Layer/` = 3 níveis → vai 2 `..` para chegar em `src/` → mais 1 nível para `Shared/`.
> `hosts/Host/` = 2 níveis → vai 2 `..` para chegar em `source-code/` → desce `src/Shared/`.
> `tests/{BC}/Layer/` = 3 níveis → vai 3 `..` para chegar em `source-code/` → desce `src/`.

```
Para cada BC "{BCName}":

4.1  src/{BCName}/{solution_prefix}.{BCName}.Domain/
     {solution_prefix}.{BCName}.Domain.csproj:
       <ProjectReference Include="../../Shared/{solution_prefix}.SharedKernel/{solution_prefix}.SharedKernel.csproj" />
       Sem PackageReferences externos

     Estrutura de pastas:
       Entities/
       ValueObjects/
       Events/
       Repositories/          ← interfaces (IRepository<T>)
       Services/              ← domain services (interfaces)
       Exceptions/

4.2  src/{BCName}/{solution_prefix}.{BCName}.Application/
     {solution_prefix}.{BCName}.Application.csproj:
       <ProjectReference Include="../{solution_prefix}.{BCName}.Domain/{solution_prefix}.{BCName}.Domain.csproj" />
       SE cqrs: true:
         <PackageReference Include="MediatR" />
         <PackageReference Include="FluentValidation" />
         <!-- ⚠️ GUARDRAIL: FluentValidation.DependencyInjectionExtensions is separate from FluentValidation.
              AddValidatorsFromAssemblyContaining<T>() lives in this package. Required in both cqrs modes. -->
         <PackageReference Include="FluentValidation.DependencyInjectionExtensions" />
       SE cqrs: false:
         <PackageReference Include="FluentValidation" />
         <!-- ⚠️ GUARDRAIL: DependencyInjectionExtensions required for AddValidatorsFromAssemblyContaining -->
         <PackageReference Include="FluentValidation.DependencyInjectionExtensions" />
         <!-- ⚠️ GUARDRAIL: Mapster mapping — DO NOT use IMapper / ServiceMapper DI pattern.
              IMapper and ServiceMapper from Mapster.DependencyInjection are NOT resolvable
              via the `Mapster.DependencyInjection` namespace in .NET 10. The namespace does
              not export these types in a way usable with standard DI registration.
              ⛔ NEVER generate: using Mapster.DependencyInjection; or services.AddScoped<IMapper, ServiceMapper>()
              ✅ CORRECT pattern — register TypeAdapterConfig globally in DependencyInjection.cs:
                 using Mapster;
                 TypeAdapterConfig.GlobalSettings.Scan(Assembly.GetExecutingAssembly());
              Inject IMapper ONLY if you add the MapsterMapper NuGet package separately.
              ⛔ MapsterMapper is NOT the same as Mapster.DependencyInjection — pick one approach. -->
         <PackageReference Include="Mapster" />

     Estrutura de pastas SE cqrs: true:
       Commands/
         {vazio — preenchido por ava-build-cycle-cqrs}
       Queries/
         {vazio — preenchido por ava-build-cycle-cqrs}
       Handlers/
         {vazio — preenchido por ava-build-cycle-cqrs}
       Validators/
         {vazio — preenchido por ava-build-cycle-cqrs}
       Behaviors/
         {vazio — ValidationBehavior, LoggingBehavior gerados por ava-build-cycle-cqrs}
       DTOs/
       Mappings/
       Abstractions/
         IApplicationService.cs   ← interface marker

     Estrutura de pastas SE cqrs: false:
       Services/
         I{BCName}Service.cs      ← interface do serviço de aplicação
       DTOs/
       Mappings/
       Abstractions/
         IUnitOfWork.cs           ← OBRIGATÓRIO — definido localmente (não existe no SharedKernel)
       DependencyInjection.cs     ← extension method: IServiceCollection.Add{BCName}Application()

     <!-- ⚠️ GUARDRAIL: When cqrs: false, Application/DependencyInjection.cs MUST be generated.
          The host's Program.cs calls Add{BCName}Application() at startup.
          If this file is missing, the build fails with CS0117 at the host project.
          Generate this file NOW as part of the Application layer scaffold — do not defer. -->
     DependencyInjection.cs template (cqrs: false):

     ```csharp
     #nullable enable
     using FluentValidation;
     using {solution_prefix}.{BCName}.Application.Services;
     using Microsoft.Extensions.DependencyInjection;

     namespace {solution_prefix}.{BCName}.Application;

     public static class DependencyInjection
     {
         public static IServiceCollection Add{BCName}Application(
             this IServiceCollection services)
         {
             // Register FluentValidation validators from this assembly
             // Requires FluentValidation.DependencyInjectionExtensions package
             services.AddValidatorsFromAssemblyContaining<{PrimaryServiceClass}>();

             // Register each application service interface → implementation
             // Repeat for every I{Service} / {Service} pair in Services/
             services.AddScoped<I{PrimaryServiceClass}, {PrimaryServiceClass}>();

             return services;
         }
     }
     ```
     Where {PrimaryServiceClass} is the first (or primary) concrete service in Services/.
     Repeat services.AddScoped<I{X}, {X}>() for every additional service in the folder.

     <!-- ⚠️ GUARDRAIL (cqrs: false): IUnitOfWork MUST be defined in Application/Abstractions/ —
          NOT imported from SharedKernel.Domain.Common (IUnitOfWork does NOT exist in SharedKernel).
          ❌ ERRADO: using {solution_prefix}.SharedKernel.Domain.Common; → CS0246 (IUnitOfWork not found)
          ✅ CORRETO: using {solution_prefix}.{BCName}.Application.Abstractions; → namespace local
          Gere SEMPRE o arquivo abaixo junto com o scaffold da camada Application quando cqrs: false. -->
     IUnitOfWork.cs template (cqrs: false — Abstractions/):

     ```csharp
     #nullable enable
     namespace {solution_prefix}.{BCName}.Application.Abstractions;

     /// <summary>
     /// Unit of Work — encapsulates DbContext.SaveChangesAsync for the Application layer.
     /// Implemented by Infrastructure/{BCName}DbContext (partial) or a dedicated UnitOfWork class.
     /// </summary>
     public interface IUnitOfWork
     {
         Task<int> SaveChangesAsync(CancellationToken cancellationToken = default);
     }
     ```

4.3  src/{BCName}/{solution_prefix}.{BCName}.Infrastructure/
     {solution_prefix}.{BCName}.Infrastructure.csproj:
       <!-- ⚠️ GUARDRAIL: Infrastructure projects use IHttpContextAccessor (ASP.NET Core type).
            Class libraries targeting net10.0 must declare a FrameworkReference to access
            ASP.NET Core types. Without it, CS0234/CS0246 will occur at compile time. -->
       <FrameworkReference Include="Microsoft.AspNetCore.App" />
       <!-- ⚠️ GUARDRAIL: Infrastructure DEVE referenciar TANTO Domain QUANTO Application.
            Domain: repositório herda de Repository<T,TId> que usa tipos de domínio.
            Application: IUnitOfWork e interfaces de repositório vivem na camada Application.
            Omitir qualquer uma causa CS0234/CS0246 em DependencyInjection.cs e repositórios. -->
       <ProjectReference Include="../{solution_prefix}.{BCName}.Domain/{solution_prefix}.{BCName}.Domain.csproj" />
       <ProjectReference Include="../{solution_prefix}.{BCName}.Application/{solution_prefix}.{BCName}.Application.csproj" />
       <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" />
       <PackageReference Include="Microsoft.EntityFrameworkCore.Tools" PrivateAssets="all" />
       <PackageReference Include="Dapper" />
       <PackageReference Include="StackExchange.Redis" />
       <PackageReference Include="Microsoft.Extensions.Caching.StackExchangeRedis" />

     Estrutura de pastas:
       Persistence/
         {BCName}DbContext.cs      ← esqueleto com OnModelCreating vazio
         Configurations/           ← Fluent API por entidade (preenchido por ava-build-cycle-efcore)
         Migrations/               ← geradas pelo EF Core
         Repositories/             ← implementações das interfaces do Domain
       Services/                   ← implementações de domain services externos
       DependencyInjection.cs      ← extension method: IServiceCollection.Add{BCName}Infrastructure()

4.4  src/{BCName}/{solution_prefix}.{BCName}.Api/
     {solution_prefix}.{BCName}.Api.csproj:
       <!-- ⚠️ GUARDRAIL: BC Api projects are LIBRARIES, not executables.
            The host (hosts/MeuERP.Api) is the entrypoint. OutputType must be Library.
            Using <OutputType>none</OutputType> or any invalid value causes CS2019. -->
       <PropertyGroup>
         <OutputType>Library</OutputType>
       </PropertyGroup>
       <ProjectReference Include="../{solution_prefix}.{BCName}.Application/{solution_prefix}.{BCName}.Application.csproj" />
       <ProjectReference Include="../{solution_prefix}.{BCName}.Infrastructure/{solution_prefix}.{BCName}.Infrastructure.csproj" />
       <PackageReference Include="Carter" />
       <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" />
       <PackageReference Include="Microsoft.Identity.Web" />
       <PackageReference Include="Microsoft.ApplicationInsights.AspNetCore" />
       <!-- ⚠️ GUARDRAIL: Swashbuckle removed — incompatible with Microsoft.OpenApi 2.0 required by
            Microsoft.AspNetCore.OpenApi {aspnet_version}. Use built-in AddOpenApi/MapOpenApi. -->
       <!-- ⚠️ GUARDRAIL: The following packages are required but NOT included transitively.
            Omitting any one of them causes CS1061/CS0246 at compile time: -->
       <!-- Required for .WithOpenApi() on Carter route groups -->
       <PackageReference Include="Microsoft.AspNetCore.OpenApi" />
       <!-- Required for .AddSqlServer() health check extension method -->
       <PackageReference Include="AspNetCore.HealthChecks.SqlServer" />
       <!-- Required for Serilog ApplicationInsights sink (.WriteTo.ApplicationInsights) -->
       <PackageReference Include="Serilog.Sinks.ApplicationInsights" />
       <!-- Required for DefaultAzureCredential and Key Vault access in non-Development -->
       <PackageReference Include="Azure.Identity" />
       <PackageReference Include="Azure.Extensions.AspNetCore.Configuration.Secrets" />
       <!-- ⛔ GUARDRAIL: For Azure Monitor / Application Insights telemetry via OpenTelemetry,
            use ONLY <PackageReference Include="Azure.Monitor.OpenTelemetry.AspNetCore" />.
            DO NOT use OpenTelemetry.Exporter.AzureMonitor — this package does NOT exist on NuGet.
            DO NOT use Microsoft.ApplicationInsights.AspNetCore TOGETHER with Azure.Monitor.* —
            pick ONE telemetry sink per project. -->

     Estrutura de pastas:
       Modules/                   ← ICarterModule por feature (preenchido por ava-build-cycle-minimal-apis)
       Middleware/
       Extensions/
         WebApplicationExtensions.cs
       Program.cs                 ← minimal hosting model com comentários de seção

     Program.cs esqueleto:
       var builder = WebApplication.CreateBuilder(args);
       // § Authentication
       // § Authorization
       // § Application Services (Add{BCName}Application)
       // § Infrastructure Services (Add{BCName}Infrastructure)
       // § Carter (Minimal APIs)
       // § OpenAPI (built-in: builder.Services.AddOpenApi("v1"))
       // § Application Insights
       var app = builder.Build();
       // § Middleware pipeline
       // § Carter (MapCarter)
       // § OpenAPI endpoint (app.MapOpenApi())
       app.Run();
```

### Step 5 — Gerar Projetos de Teste

```
Para cada BC "{BCName}":

5.1  tests/{BCName}/{solution_prefix}.{BCName}.Tests.Unit/
     {solution_prefix}.{BCName}.Tests.Unit.csproj:
       <!-- ⚠️ GUARDRAIL: Path depth = 3 levels (tests/{BC}/{ProjectName}/).
            ../../../ sobe para source-code/ → src/{BC}/
            ❌ ERRADO: ../../src/  (resolve para tests/src/ — não existe → MSB9008)
            ✅ CORRETO: ../../../src/ (resolve para source-code/src/ → correto)
            SEMPRE incluir o nome completo do arquivo .csproj no final do Include. -->
       <ProjectReference Include="../../../src/{BCName}/{solution_prefix}.{BCName}.Application/{solution_prefix}.{BCName}.Application.csproj" />
       <ProjectReference Include="../../../src/{BCName}/{solution_prefix}.{BCName}.Domain/{solution_prefix}.{BCName}.Domain.csproj" />
       <PackageReference Include="xunit" />
       <PackageReference Include="xunit.runner.visualstudio" PrivateAssets="all" />
       <PackageReference Include="Moq" />
       <PackageReference Include="FluentAssertions" />
       <PackageReference Include="Microsoft.NET.Test.Sdk" />

     Estrutura de pastas:
       SE cqrs: true:
         Handlers/
         Validators/
       SE cqrs: false:
         Services/
       Domain/

5.2  tests/{BCName}/{solution_prefix}.{BCName}.Tests.Integration/
     {solution_prefix}.{BCName}.Tests.Integration.csproj:
       <!-- ⚠️ GUARDRAIL: Path depth = 3 levels — mesma regra do Tests.Unit acima.
            SEMPRE incluir o nome completo do arquivo .csproj no final do Include. -->
       <ProjectReference Include="../../../src/{BCName}/{solution_prefix}.{BCName}.Api/{solution_prefix}.{BCName}.Api.csproj" />
       <PackageReference Include="xunit" />
       <PackageReference Include="xunit.runner.visualstudio" PrivateAssets="all" />
       <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" />
       <PackageReference Include="FluentAssertions" />
       <PackageReference Include="Testcontainers.MsSql" />
       <PackageReference Include="Testcontainers.Redis" />
       <PackageReference Include="Microsoft.NET.Test.Sdk" />
       <!-- ⚠️ GUARDRAIL: Transitive override obrigatório — CVE GHSA-g94r-2vxg-569j (NU1902 Moderate).
            Testcontainers.MsSql 4.0.0 puxa OpenTelemetry.Api transitivamente em versão vulnerável.
            NuGetAuditMode=all (padrão sem Directory.Build.props) elevaria a erro se TreatWarningsAsErrors=true estivesse ativo.
            O CPM pin (Step 6) sozinho NÃO ativa o override para pacotes puramente transitivos —
            é obrigatório adicionar <PackageReference> direto neste .csproj para que o pin seja efetivo.
            Ver: dotnet-nuget-policy.md → "Regra de Transitive Override" -->
       <!-- transitive override: required by Testcontainers.MsSql — sem este PackageReference o CPM pin é ignorado -->
       <PackageReference Include="OpenTelemetry.Api" />

     Estrutura de pastas:
       Fixtures/
         WebAppFactory.cs    ← esqueleto WebApplicationFactory<Program>
       Endpoints/
```

### Step 6 — Package Catalog (Directory.Packages.props)

> ⚠️ Este é o **catálogo de pacotes** (nomes + guardrails) para o `Directory.Packages.props`.
> **Versões NÃO são hardcoded aqui** — são preenchidas com `resolved_versions['PackageName']` resolvido no Step 1.6 (NuGet API).
> **Gerar este arquivo no Step 2.3** usando exclusivamente `resolved_versions` — nunca usar versões de memória de treinamento.

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>

  <!-- Versões preenchidas por resolved_versions do Step 1.6 (NuGet API dinâmica).
       Placeholder {resolved_versions['X']} é substituído pela versão resolvida antes de escrever o arquivo.
       Security floors aplicados via dotnet-nuget-policy.md (Step 1.6 Passo C). -->

  <ItemGroup Label="Application">  <!-- SE cqrs: false — Application Services pattern -->
    <PackageVersion Include="FluentValidation" Version="{resolved_versions['FluentValidation']}" />
    <PackageVersion Include="FluentValidation.AspNetCore" Version="{resolved_versions['FluentValidation.AspNetCore']}" />
    <!-- ⚠️ GUARDRAIL: FluentValidation.DependencyInjectionExtensions is a SEPARATE package.
         AddValidatorsFromAssemblyContaining<T>() lives here, NOT in the base FluentValidation package.
         Omitting this causes CS0117 / method-not-found at compile time. -->
    <PackageVersion Include="FluentValidation.DependencyInjectionExtensions" Version="{resolved_versions['FluentValidation.DependencyInjectionExtensions']}" />
    <!-- ⚠️ GUARDRAIL: Mapster — use TypeAdapterConfig.GlobalSettings (NOT IMapper/ServiceMapper DI).
         See Application layer GUARDRAIL above for the correct usage pattern. -->
    <PackageVersion Include="Mapster" Version="{resolved_versions['Mapster']}" />
    <!-- Mapster.DependencyInjection REMOVED: IMapper/ServiceMapper DI pattern does not work in .NET 10.
         Do NOT add Mapster.DependencyInjection to this file. -->
  </ItemGroup>

  <ItemGroup Label="CQRS">  <!-- SE cqrs: true — MediatR pipeline -->
    <PackageVersion Include="MediatR" Version="{resolved_versions['MediatR']}" />
    <PackageVersion Include="FluentValidation" Version="{resolved_versions['FluentValidation']}" />
    <PackageVersion Include="FluentValidation.AspNetCore" Version="{resolved_versions['FluentValidation.AspNetCore']}" />
  </ItemGroup>

  <ItemGroup Label="Persistence">
    <!-- net8.0: 8.0.x | net9.0: 9.0.x -->
    <!-- SECURITY: minimum 6.1.1 — required by AspNetCore.HealthChecks.SqlServer 9.x.
         Versions < 6.1.1 cause NU1605 downgrade conflict when HealthChecks is present.
         6.1.1 transitively requires Azure.Identity >= 1.14.2 — ensure Azure.Identity is pinned to 1.14.2+. -->
    <PackageVersion Include="Microsoft.Data.SqlClient" Version="{resolved_versions['Microsoft.Data.SqlClient']}" />
    <!-- ⛔ GUARDRAIL: DO NOT add System.Security.Cryptography.Xml to Directory.Packages.props
         and DO NOT add <PackageReference Include="System.Security.Cryptography.Xml" /> in any
         csproj file. Reason: adding it as a direct or central reference makes NuGet treat it as
         a directly-audited package. NuGetAuditMode=direct (already set in Directory.Build.props)
         means transitive packages are NOT audited. If you force it direct, NU1903 ("known high
         severity vulnerability") fires. Com TreatWarningsAsErrors=false o build não quebra, mas
         mantenha a prática de não forçar referência direta para não gerar warning/erro se a flag
         for reativada futuramente. The vulnerability in System.Security.Cryptography.Xml is a transitive risk from
         Microsoft.Data.SqlClient — leave it transitive so NuGetAuditMode=direct silences it. -->
    <!-- ⚠️ GUARDRAIL: Microsoft.EntityFrameworkCore (base) must be listed separately.
         SharedKernel references this directly for interceptor base types.
         SqlServer package does NOT re-export the base package transitively to all projects. -->
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="{resolved_versions['Microsoft.EntityFrameworkCore']}" />
    <PackageVersion Include="Microsoft.EntityFrameworkCore.SqlServer" Version="{resolved_versions['Microsoft.EntityFrameworkCore.SqlServer']}" />
    <PackageVersion Include="Microsoft.EntityFrameworkCore.Tools" Version="{resolved_versions['Microsoft.EntityFrameworkCore.Tools']}" />
    <PackageVersion Include="Dapper" Version="{resolved_versions['Dapper']}" />
    <PackageVersion Include="StackExchange.Redis" Version="{resolved_versions['StackExchange.Redis']}" />
    <PackageVersion Include="Microsoft.Extensions.Caching.StackExchangeRedis" Version="{resolved_versions['Microsoft.Extensions.Caching.StackExchangeRedis']}" />
  </ItemGroup>

  <ItemGroup Label="API">
    <PackageVersion Include="Carter" Version="{resolved_versions['Carter']}" />
    <!-- ⚠️ GUARDRAIL: Swashbuckle removed — incompatible with Microsoft.OpenApi 2.0 required by
         Microsoft.AspNetCore.OpenApi (TFM-locked). Use built-in AddOpenApi/MapOpenApi instead. -->
    <!-- ⚠️ GUARDRAIL: Microsoft.AspNetCore.OpenApi is REQUIRED for .WithOpenApi() on Carter route groups.
         This is the built-in .NET OpenAPI package (not Swashbuckle). Omitting causes CS1061. -->
    <PackageVersion Include="Microsoft.AspNetCore.OpenApi" Version="{resolved_versions['Microsoft.AspNetCore.OpenApi']}" />
    <PackageVersion Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="{resolved_versions['Microsoft.AspNetCore.Authentication.JwtBearer']}" />
    <!-- SECURITY floor: >= 4.0 obrigatório — consultar dotnet-nuget-policy.md → Security Floors.
         ⛔ NEVER use 3.x — GHSA-rpq8-q44m-2rpg remains unfixed in all 3.x releases. -->
    <PackageVersion Include="Microsoft.Identity.Web" Version="{resolved_versions['Microsoft.Identity.Web']}" />
    <PackageVersion Include="Microsoft.ApplicationInsights.AspNetCore" Version="{resolved_versions['Microsoft.ApplicationInsights.AspNetCore']}" />
    <!-- SECURITY floor: >= 1.17.2 — consultar dotnet-nuget-policy.md → Security Floors. -->
    <PackageVersion Include="Azure.Identity" Version="{resolved_versions['Azure.Identity']}" />
    <!-- ⚠️ GUARDRAIL: Azure.Core — pin explícito obrigatório.
         Azure.Monitor + Azure.Identity exportam DefaultAzureCredential no mesmo namespace.
         Sem este pin, CS0433 (ambiguous type) pode ocorrer em projetos Microsoft.NET.Sdk.Web.
         Adicionar <PackageReference Include="Azure.Core" /> ao host .csproj se CS0433 aparecer. -->
    <PackageVersion Include="Azure.Core" Version="{resolved_versions['Azure.Core']}" />
    <PackageVersion Include="Azure.Extensions.AspNetCore.Configuration.Secrets" Version="{resolved_versions['Azure.Extensions.AspNetCore.Configuration.Secrets']}" />
    <!-- ⚠️ GUARDRAIL: AspNetCore.HealthChecks.SqlServer is REQUIRED for .AddSqlServer() health check.
         This is NOT included transitively by any other package. Must be explicitly referenced
         in every *.Api.csproj that registers SQL Server health checks in Program.cs. -->
    <PackageVersion Include="AspNetCore.HealthChecks.SqlServer" Version="{resolved_versions['AspNetCore.HealthChecks.SqlServer']}" />
    <PackageVersion Include="AspNetCore.HealthChecks.Redis" Version="{resolved_versions['AspNetCore.HealthChecks.Redis']}" />
  </ItemGroup>

  <ItemGroup Label="Observability">
    <!-- Versões resolvidas via NuGet API (Step 1.6). Security floors em dotnet-nuget-policy.md. -->
    <!-- ⚠️ GUARDRAIL: Serilog.AspNetCore — alinhar com TFM do projeto. -->
    <PackageVersion Include="Serilog.AspNetCore" Version="{resolved_versions['Serilog.AspNetCore']}" />
    <!-- ⚠️ GUARDRAIL: Serilog.Sinks.Console is REQUIRED for .WriteTo.Console(...) in Program.cs.
         This is NOT included transitively by Serilog.AspNetCore. Must be listed in CPM —
         omission causes NU1010 (no PackageVersion for PackageReference). -->
    <PackageVersion Include="Serilog.Sinks.Console" Version="{resolved_versions['Serilog.Sinks.Console']}" />
    <PackageVersion Include="Serilog.Sinks.ApplicationInsights" Version="{resolved_versions['Serilog.Sinks.ApplicationInsights']}" />
    <!-- ⚠️ GUARDRAIL: Serilog.Enrichers.CorrelationId is REQUIRED for .Enrich.WithCorrelationId().
         This is NOT included transitively by Serilog.AspNetCore. Must be explicitly referenced
         in the host project and registered in DI/services to propagate X-Correlation-Id. -->
    <PackageVersion Include="Serilog.Enrichers.CorrelationId" Version="{resolved_versions['Serilog.Enrichers.CorrelationId']}" />
    <!-- SECURITY floor: >= 1.15.3 — consultar dotnet-nuget-policy.md → Security Floors. -->
    <PackageVersion Include="OpenTelemetry.Extensions.Hosting" Version="{resolved_versions['OpenTelemetry.Extensions.Hosting']}" />
    <PackageVersion Include="OpenTelemetry.Instrumentation.AspNetCore" Version="{resolved_versions['OpenTelemetry.Instrumentation.AspNetCore']}" />
    <!-- ⚠️ GUARDRAIL: OpenTelemetry.Instrumentation.Http is REQUIRED for .AddHttpClientInstrumentation().
         This is NOT included transitively by OpenTelemetry.Extensions.Hosting or Instrumentation.AspNetCore.
         Must be explicitly referenced in the host project.
         SECURITY floor: >= 1.14.0 — consultar dotnet-nuget-policy.md → Security Floors. -->
    <PackageVersion Include="OpenTelemetry.Instrumentation.Http" Version="{resolved_versions['OpenTelemetry.Instrumentation.Http']}" />
    <PackageVersion Include="OpenTelemetry.Exporter.OpenTelemetryProtocol" Version="{resolved_versions['OpenTelemetry.Exporter.OpenTelemetryProtocol']}" />
    <!-- ⚠️ GUARDRAIL: OpenTelemetry.Api — transitive override OBRIGATÓRIO.
         SECURITY floor: >= 1.15.3 — GHSA-g94r-2vxg-569j (Moderate CVE) — consultar dotnet-nuget-policy.md.
         O CPM pin sozinho NÃO basta — requer <PackageReference> direto em cada .csproj afetado
         (ver Step 5.2 — template dos Tests.Integration, e Step 4.4 — BC Api projects). -->
    <PackageVersion Include="OpenTelemetry.Api" Version="{resolved_versions['OpenTelemetry.Api']}" />
    <!-- ⛔ GUARDRAIL: OpenTelemetry.Exporter.AzureMonitor does NOT exist on NuGet (NU1101).
         The correct Azure Monitor package for ASP.NET Core is:
           Azure.Monitor.OpenTelemetry.AspNetCore   ← all-in-one for .NET web apps
         NOT any of these (all non-existent):
           OpenTelemetry.Exporter.AzureMonitor
           OpenTelemetry.AzureMonitor.Exporter
           AzureMonitor.OpenTelemetry.Exporter
         DO NOT reference any package with "AzureMonitor" as prefix/suffix in OpenTelemetry namespace.
         The correct NuGet org/namespace is Azure.Monitor.* (from Microsoft Azure SDK). -->
    <PackageVersion Include="Azure.Monitor.OpenTelemetry.AspNetCore" Version="{resolved_versions['Azure.Monitor.OpenTelemetry.AspNetCore']}" />
  </ItemGroup>

  <ItemGroup Label="Resilience">
    <PackageVersion Include="Polly" Version="{resolved_versions['Polly']}" />
    <!-- ⚠️ GUARDRAIL: Microsoft.Extensions.Http.Resilience — seguir versioning Microsoft.Extensions,
         não o versioning do TFM. Verificar NuGet API para versão compatível. -->
    <PackageVersion Include="Microsoft.Extensions.Http.Resilience" Version="{resolved_versions['Microsoft.Extensions.Http.Resilience']}" />
  </ItemGroup>

  <ItemGroup Label="Testing">
    <PackageVersion Include="xunit" Version="{resolved_versions['xunit']}" />
    <PackageVersion Include="xunit.runner.visualstudio" Version="{resolved_versions['xunit.runner.visualstudio']}" />
    <PackageVersion Include="Microsoft.NET.Test.Sdk" Version="{resolved_versions['Microsoft.NET.Test.Sdk']}" />
    <PackageVersion Include="Moq" Version="{resolved_versions['Moq']}" />
    <PackageVersion Include="FluentAssertions" Version="{resolved_versions['FluentAssertions']}" />
    <PackageVersion Include="Microsoft.AspNetCore.Mvc.Testing" Version="{resolved_versions['Microsoft.AspNetCore.Mvc.Testing']}" />
    <!-- ⚠️ GUARDRAIL: Testcontainers had a major version jump from 3.x to 4.0.0.
         Version 3.11.0 does NOT exist — always verify via NuGet API (Step 1.6). -->
    <PackageVersion Include="Testcontainers.MsSql" Version="{resolved_versions['Testcontainers.MsSql']}" />
    <PackageVersion Include="Testcontainers.Redis" Version="{resolved_versions['Testcontainers.Redis']}" />
  </ItemGroup>
</Project>
```

### Step 7 — Gerar docker-compose para Dev Local

```yaml
# docker-compose.yml — apenas infraestrutura (não a aplicação)
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      SA_PASSWORD: "${SQL_SA_PASSWORD}"   # via .env file (nunca hardcoded)
      ACCEPT_EULA: "Y"
      MSSQL_PID: Developer
    ports: ["1433:1433"]
    volumes: [sqlserver-data:/var/opt/mssql]
    # MANDATORY: SQL Server 2022 moved sqlcmd to /opt/mssql-tools18/bin/.
    # The fallback ensures the healthcheck works on both 2019 and 2022 images.
    healthcheck:
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1' -b -No 2>/dev/null || /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1'"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass "${REDIS_PASSWORD}"
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  sqlserver-data:

# docker-compose.override.yml — configurações de dev local
# Ler .env.example gerado na raiz com variáveis obrigatórias documentadas
```

### Step 8 — Security Gate (OBRIGATÓRIO — antes de COMPLETED)

> ⚠️ **INVARIANTE:** Este step NUNCA pode ser pulado. Um scaffold com CVEs ou build quebrado não é saída aceitável.

```
8.1  Scan de vulnerabilidades NuGet:
     Executar: dotnet list package --vulnerable --include-transitive 2>&1

     PARSEAR a saída linha a linha:
       - Cada linha de CVE tem o formato:
           > {PackageName} {CurrentVersion} -> {AdvisoryURL} ({Severity})
         onde AdvisoryURL = "https://github.com/advisories/GHSA-XXXX-XXXX-XXXX"

     SE nenhuma CVE encontrada ("No vulnerable packages were found"):
       → CVE scan: ✅ PASSED — avançar para 8.2

     SE encontrada qualquer CVE (qualquer severidade: Low / Moderate / High / Critical):
       → BLOQUEADO — NÃO retornar COMPLETED

       Para cada CVE encontrado, executar LOOP:

       a) Ler advisory do GitHub Advisories:
          URL: https://github.com/advisories/{GHSA-ID}
          Extrair:
            - Severity (Low / Moderate / High / Critical)
            - "Patched in version" (primeira versão segura)
            - "Affected versions" (range)
            - Package ecosystem (NuGet)
            - Root package (se transitive: qual package direto puxa esta dependência)

       b) Classificar tipo de fix necessário:
          TIPO-A — Pacote direto (consta em PackageReference ou PackageVersion):
            → Atualizar <PackageVersion Include="P" Version="{patched}"> em Directory.Packages.props
            → Verificar se outros projetos na solução são afetados pelo mesmo package

          TIPO-B — Pacote transitivo (não consta diretamente no CPM):
            → Aplicar Transitive Override:
               PASSO 1: Adicionar <PackageVersion Include="P" Version="{patched}"> em Directory.Packages.props
               PASSO 2: Adicionar <PackageReference Include="P" /> (sem Version) em cada .csproj afetado
                        ⚠️ EXCEÇÃO SDK.Web: NÃO adicionar se o package for fornecido pelo framework
                          (NU1510 ocorre quando se tenta override de package framework em SDK.Web).
                          Verificar com: dotnet list package --project {csproj} --include-transitive
               PASSO 3: Comentário obrigatório no .csproj:
                        <!-- transitive CVE override: {GHSA-ID} ({Severity}) — pulled by {ConsumerPackage} -->

          TIPO-C — Severidade High ou Critical + pacote de segurança (auth/crypto/TLS/JWT):
            → Aplicar TIPO-A ou TIPO-B conforme acima
            → Verificar `project-config.yaml → security_enabled_tobe`.
              SE `security_enabled_tobe == false`:
                - Emitir: `⚠️ [SECURITY PLACEHOLDER] Handoff para @ava-security-design-tobe SKIPPED — security_enabled_tobe=false.`
                - NÃO invocar @ava-security-design-tobe.
                - Registrar outcome: `{ ghsa_id, outcome: "skipped_security_disabled" }`.
              SENÃO:
                → OBRIGATÓRIO: handoff para @ava-security-design-tobe:
                  Enviar: { ghsa_id, severity, package, current_version, patched_version,
                            affected_component: "auth|crypto|transport|identity" }
                  @ava-security-design-tobe irá:
                    - Revisar impacto no threat model
                    - Avaliar substituição do pacote se vulnerabilidade for estrutural
                    - Gerar ADR de decisão de segurança se substituição for recomendada
                    - Retornar: approved_fix | substitute_package | escalate_to_architect

       c) Após aplicar todos os fixes do loop:
          Re-executar: dotnet list package --vulnerable --include-transitive
          Repetir 8.1 até: "No vulnerable packages were found"

       d) Documentar no resultado (Step 10):
          CVEs resolvidos: [ { ghsa_id, severity, package, fix_type, patched_version } ]
          Overrides aplicados: [ { package, csproj_list } ]
          Handoffs para security-design-tobe: [ { ghsa_id, outcome } ]

8.2  Build de validação:
     Executar: dotnet build --no-incremental

     Gate: ZERO erros
       SE erros encontrados → corrigir antes de retornar COMPLETED
       SE ZERO erros       → Build: ✅ PASSED — avançar para Step 9
```

### Step 9 — Gerar KeyVaultOnboarding.md

> Gerar um único arquivo na raiz da solução para guiar a migração de User Secrets → Azure Key Vault antes de qualquer deploy em ambiente não-local.

```markdown
# KeyVaultOnboarding.md — Migração de Segredos para Azure Key Vault

## Por quê
Os agentes `@ava-build-cycle-efcore` e `@ava-build-cycle-minimal-apis` **exigem** que
`connection_source: "azure-keyvault"` esteja configurado. Connection strings em `.env`,
`appsettings.json` ou variáveis de ambiente são **bloqueadas** em ambientes não-locais.

## Passo a Passo

### 1. Local (dev) — User Secrets (somente)
```bash
# Por bounded context
dotnet user-secrets set "{bc_name}-sql-connection-string" \
  "Server=localhost,1433;Database={BCName};User Id=sa;Password=...;" \
  --project src/{BCName}/{solution_prefix}.{BCName}.Api
```

### 2. Key Vault — criar segredos
```bash
# Nome do segredo = exatamente o mesmo nome usado em User Secrets
az keyvault secret set \
  --vault-name "{keyvault_name}" \
  --name "{bc_name}-sql-connection-string" \
  --value "Server={server};Database={BCName};..."
```

### 3. Registrar Key Vault no host (`Program.cs`)
```csharp
// Requerido pelo @ava-build-cycle-efcore — sem isso a DI lança InvalidOperationException
builder.Configuration.AddAzureKeyVault(
    new Uri($"https://{keyvaultName}.vault.azure.net/"),
    new DefaultAzureCredential());
```

### 4. Checklist antes de deploy
- [ ] Todos os `{bc_name}-sql-connection-string` criados no Key Vault
- [ ] `AddAzureKeyVault()` registrado em `Program.cs` de cada Api project
- [ ] `.env` e `appsettings.*.json` **não** contêm connection strings reais
- [ ] Managed Identity ou Service Principal com `Key Vault Secrets User` role atribuído

## Referência
- `docs/architecture/ConfigStackDotNet.yaml` → `persistence.connection_source`
- `@ava-build-cycle-efcore` → Step 1.2b (pré-flight validation)
```

### Step 10 — Exibir Resultado

```
✅ BUILD CYCLE — Scaffolding Concluído
   Solução : {solution_prefix}.sln  |  SDK: .NET {backend_version}  |  CQRS: {enabled/disabled}
   BCs     : {N} — {lista de BCs}
   Projetos: Shared×2 + {N BCs}×4 código + {N BCs}×2 testes
   Artefatos: outputs/tobe/source-code/{solution_prefix}/
   Próximo : @ava-build-cycle-efcore → @ava-build-cycle-cqrs → @ava-build-cycle-minimal-apis
```

## Output Contract

```yaml
outputs:
  solution_root: "projects/{project_name}/outputs/tobe/source-code/{solution_prefix}/"
  solution_file: "projects/{project_name}/outputs/tobe/source-code/{solution_prefix}/{solution_prefix}.sln"
  shared_kernel:  "projects/{project_name}/outputs/tobe/source-code/{solution_prefix}/src/Shared/{solution_prefix}.SharedKernel/"
  per_bc_pattern: "projects/{project_name}/outputs/tobe/source-code/{solution_prefix}/src/{BCName}/"
  tests_pattern:  "projects/{project_name}/outputs/tobe/source-code/{solution_prefix}/tests/{BCName}/"
```

## Naming Reference

| Artefato | Padrão | Exemplo (prefix=MeuERP, BC=Pedidos) |
|----------|--------|--------------------------------------|
| Solution file | `{prefix}.sln` | `MeuERP.sln` |
| Domain project | `{prefix}.{BC}.Domain` | `MeuERP.Pedidos.Domain` |
| Application project | `{prefix}.{BC}.Application` | `MeuERP.Pedidos.Application` |
| Infrastructure project | `{prefix}.{BC}.Infrastructure` | `MeuERP.Pedidos.Infrastructure` |
| API project | `{prefix}.{BC}.Api` | `MeuERP.Pedidos.Api` |
| Unit tests | `{prefix}.{BC}.Tests.Unit` | `MeuERP.Pedidos.Tests.Unit` |
| Integration tests | `{prefix}.{BC}.Tests.Integration` | `MeuERP.Pedidos.Tests.Integration` |
| SharedKernel | `{prefix}.SharedKernel` | `MeuERP.SharedKernel` |
| Contracts | `{prefix}.Contracts` | `MeuERP.Contracts` |
| Root namespace | = project name | `MeuERP.Pedidos.Domain` |

## Failure Modes

| Cenário | Ação |
|---------|------|
| `architecture-blueprint.md` não encontrado | Perguntar BCs ao usuário; prosseguir |
| Nenhum BC extraído do blueprint | Perguntar: "Liste os bounded contexts separados por vírgula" |
| BC com nome que contém caracteres especiais | Normalizar para PascalCase sem espaços/acentos; avisar: "'{original}' normalizado para '{normalizado}'" |
| `dotnet_sdk_version` ausente no ConfigStackDotNet | Usar `"9.0.x"` como default e avisar |
| `cqrs` ausente no ConfigStackDotNet | Perguntar: "CQRS habilitado? (s/n)" — sem assumir default |
| Projeto já existe no path de output | Avisar: "Projeto '{nome}' já existe — sobrescrever? (s/n)" |
| Mais de 10 bounded contexts | WARN: "Solução com {N} BCs pode impactar tempo de build. Considere separar em múltiplos repositórios." |
