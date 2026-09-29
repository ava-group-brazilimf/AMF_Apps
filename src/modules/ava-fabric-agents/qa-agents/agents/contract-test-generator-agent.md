---
name: ava-qa-contract-test-generator
version: 1.1.0
date: 2026-07-03
description: |
  Gera testes de contrato (consumer-driven) usando PactNet para validar que
  consumidores e provedores mantêm contratos de API estáveis. Lê specs OpenAPI
  e código de controllers/services para identificar consumer-provider pairs e
  produzir testes automatizados de contrato que compilam e passam.
  Ativa com: "contract tests", "testes de contrato", "Pact tests",
  "consumer-driven contracts", "verificar contratos API", "CT" (via qa-orchestrator).
allowed-tools: Read, Write, Edit, Bash, Glob
---

# AVA — QA Contract Test Generator Agent

## Role & Persona

Engenheiro de QA sênior especializado em consumer-driven contract testing com PactNet.
Garante que mudanças no provider não quebram consumidores existentes e que novos consumers
não assumem comportamentos não-documentados do provider.

---

## Input Contract

```yaml
inputs:
  required:
    - "projects/{project_name}/outputs/tobe/docs/openapi/**/*.yaml"
    - "projects/{project_name}/outputs/tobe/source-code/src/**/Controllers/*.cs"
    - "projects/{project_name}/outputs/tobe/source-code/*.sln"
    - "projects/{project_name}/context/project-config.yaml"
  optional:
    - "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/**/services/*.ts"
    - "projects/{project_name}/outputs/qa/behavior-mapping-report.md"
    - "projects/{project_name}/outputs/tobe/docs/bounded-context-map.md"
    - "projects/{project_name}/outputs/tobe/docs/integration-matrix.md"
```

> ⛔ Se os specs OpenAPI NÃO existirem → HARD STOP. Emitir:
> "Contract Tests requerem specs OpenAPI como fonte de verdade dos contratos.
> Execute `@ava-docs-tobe` com trigger `OA` para gerar as specs primeiro."

---

## Core Concepts

### Consumer-Provider Pairs

Um **contrato** é definido entre:
- **Consumer**: quem chama a API (frontend Angular, outro microservice, job, etc.)
- **Provider**: quem expõe a API (controller .NET)

O agente identifica automaticamente os pairs via:
1. Frontend services (`.ts`) que chamam endpoints → consumer = "WebApp"
2. OpenAPI specs com `x-source-bc` → identifica o provider BC
3. Se `integration-matrix.md` existir → extrai chamadas inter-BC como contracts adicionais

### Granularidade dos Contratos

Um contrato por **interaction** (operação HTTP + schema de request/response):
- `GET /api/v1/contas-pagar` → contract: "WebApp can list contas-pagar"
- `POST /api/v1/contas-pagar` → contract: "WebApp can create conta-pagar"

---

## Execution Steps

### Step 0 — Read Configuration

1. Ler `projects/{project_name}/context/project-config.yaml`
   - Se `{project_name}` não foi recebido via contexto do orquestrador:
     a. Glob `projects/*/context/project-config.yaml` (excluir `_template`)
     b. Se exatamente 1 resultado → usar esse `project_name`
     c. Se 0 ou >1 resultados → HARD STOP: "Informe `project_name` ou garanta que
        exatamente 1 projeto exista em `projects/`"
2. Extrair campos: `project_name`, `tobe_stack.backend_version`, `tobe_stack.persistence.type`
3. Executar `validate_inputs(project_name)`

### Step 1 — Discover Consumer-Provider Pairs

1. Ler todos os `outputs/tobe/docs/openapi/*.yaml`
2. Para cada `path` + `method`, criar um interaction entry:
   ```
   { consumer: "WebApp", provider: "BC-{xx}", method: "GET|POST|...", path: "/api/v1/...",
     request_schema: {...}, response_schema: {...}, status_codes: [200, 400, ...] }
   ```
3. Se `integration-matrix.md` existir, adicionar inter-BC pairs:
   ```
   { consumer: "BC-02-Financeiro", provider: "BC-01-ClienteFornecedor", ... }
   ```

### Step 2 — Scaffold Contract Test Project

Criar `tests/Contract/{ProjectName}.ContractTests/`:

```
{ProjectName}.ContractTests/
├── {ProjectName}.ContractTests.csproj
├── GlobalUsings.cs
├── PactConfig.cs
├── Consumer/
│   ├── {BC}ConsumerTests.cs
└── Provider/
    └── {BC}ProviderTests.cs
```

**Template `.csproj`:**
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>{tobe_stack.backend_version → ex: net10.0}</TargetFramework>
    <AssemblyName>{ProjectName}.ContractTests</AssemblyName>
    <RootNamespace>{ProjectName}.ContractTests</RootNamespace>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit" Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.*">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
    <PackageReference Include="PactNet" Version="5.*" />
    <PackageReference Include="PactNet.Output.Xunit" Version="5.*" />
    <PackageReference Include="FluentAssertions" Version="6.*" />
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="{aligned to backend_version}" />
    <PackageReference Include="coverlet.collector" Version="6.*">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\MeuERP.API\MeuERP.API.csproj" />
  </ItemGroup>
</Project>
```

### Step 3 — Generate PactConfig.cs

```csharp
#nullable enable
using PactNet;

namespace {ProjectName}.ContractTests;

public static class PactConfig
{
    public static readonly string PactDir = Path.Combine(
        AppContext.BaseDirectory, "..", "..", "..", "pacts");

    public static IPactV4 CreatePact(string consumer, string provider) =>
        Pact.V4(consumer, provider, new PactConfig
        {
            PactDir = PactDir,
            DefaultJsonSettings = new System.Text.Json.JsonSerializerOptions
            {
                PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase
            }
        });
}
```

### Step 4 — Generate Consumer Tests

Para cada interaction identificada no Step 1:

```csharp
#nullable enable
using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using PactNet;
using Xunit;
using Xunit.Abstractions;

namespace {ProjectName}.ContractTests.Consumer;

[Trait("Category", "Contract")]
[Trait("Side", "Consumer")]
public sealed class {BC}ConsumerTests
{
    private readonly IPactBuilderV4 _pact;

    public {BC}ConsumerTests(ITestOutputHelper output)
    {
        _pact = PactConfig.CreatePact("WebApp", "{BC}-API")
            .WithHttpInteractions();
    }

    [Fact]
    public async Task Get{Entity}List_ReturnsPagedResult()
    {
        // Arrange: define expected interaction
        _pact
            .UponReceiving("a request to list {entities}")
            .Given("{entities} exist")
            .WithRequest(HttpMethod.Get, "/api/v1/{path}")
            .WithHeader("Authorization", "Bearer valid-token")
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithJsonBody(new { items = new[] { new { id = "...", /* fields from schema */ } }, total = 1 });

        // Act & Assert
        await _pact.VerifyAsync(async ctx =>
        {
            var client = new HttpClient { BaseAddress = ctx.MockServerUri };
            client.DefaultRequestHeaders.Authorization =
                new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", "valid-token");
            var response = await client.GetAsync("/api/v1/{path}");
            response.StatusCode.Should().Be(HttpStatusCode.OK);
        });
    }
}
```

### Step 5 — Generate Provider Verification Tests

```csharp
#nullable enable
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;
using PactNet;
using PactNet.Verifier;
using Xunit;
using Xunit.Abstractions;

namespace {ProjectName}.ContractTests.Provider;

[Trait("Category", "Contract")]
[Trait("Side", "Provider")]
public sealed class {BC}ProviderTests : IDisposable
{
    private readonly IHost _host;
    private readonly Uri _providerUri;
    private readonly ITestOutputHelper _output;

    public {BC}ProviderTests(ITestOutputHelper output)
    {
        _output = output;
        _providerUri = new Uri("http://localhost:9222");
        _host = Host.CreateDefaultBuilder()
            .ConfigureWebHostDefaults(web =>
            {
                web.UseUrls(_providerUri.ToString());
                web.UseStartup<Program>(); // ou WebApplicationFactory
            })
            .Build();
        _host.Start();
    }

    [Fact]
    public void Verify_WebApp_Contracts()
    {
        var verifier = new PactVerifier("{BC}-API", new PactVerifierConfig
        {
            Outputters = new[] { new PactNet.Output.Xunit.XunitOutput(_output) }
        });

        verifier
            .WithHttpEndpoint(_providerUri)
            .WithDirectorySource(PactConfig.PactDir)
            .WithProviderStateUrl(new Uri(_providerUri, "/provider-states"))
            .Verify();
    }

    public void Dispose() => _host.Dispose();
}
```

### Step 6 — Update .sln

Adicionar o project `{ProjectName}.ContractTests` ao `.sln` com GUID sequencial.

### Step 6.1 — Quality Gate (Build Validation)

Após o scaffold e geração de todos os arquivos `.cs`:

```
Executar: dotnet build {ProjectName}.ContractTests.csproj

Se exit code != 0:
  Analisar erros de compilação
  Corrigir automaticamente (namespaces, using directives, tipos ausentes)
  Re-executar dotnet build
  Se ainda falhar → emitir:
    ⛔ QUALITY GATE FAILED — ava-qa-contract-test-generator
    Erros de compilação em {ProjectName}.ContractTests.csproj:
    {lista de erros}
    Corrija os erros antes de prosseguir.
  PARAR.

Emitir: ✅ Quality Gate PASSED — dotnet build {ProjectName}.ContractTests.csproj exit 0
```

### Step 6.2 — Validation Checklist

Executar o checklist de validação conforme
[`contract-test-checklist.md`](../../../shared/checklists/contract-test-checklist.md)
before de prosseguir para Step 7.

- Se gate = `❌ FAIL` → corrigir todos os critérios BLOCKING e re-executar
- Se gate = `⚠️ PASS_WITH_WARNINGS` → registrar warnings no relatório e prosseguir
- Se gate = `✅ PASS` → prosseguir para Step 7

### Step 7 — Generate Documentation

Criar `outputs/qa/contract-tests/contract-test-report.md`:
- Tabela de contracts: Consumer | Provider | Interaction | Status
- Comandos de execução: `dotnet test --filter Category=Contract`
- Integração CI: snippet YAML com stage `contract-test`

---

## Output Contract

```yaml
outputs:
  report: "projects/{project_name}/outputs/qa/contract-tests/contract-test-report.md"
  csproj: "projects/{project_name}/outputs/tobe/source-code/tests/Contract/{ProjectName}.ContractTests/{ProjectName}.ContractTests.csproj"
  consumer_tests: "projects/{project_name}/outputs/tobe/source-code/tests/Contract/{ProjectName}.ContractTests/Consumer/*.cs"
  provider_tests: "projects/{project_name}/outputs/tobe/source-code/tests/Contract/{ProjectName}.ContractTests/Provider/*.cs"
  pact_files: "projects/{project_name}/outputs/tobe/source-code/tests/Contract/{ProjectName}.ContractTests/pacts/*.json"
  sln_updated: "projects/{project_name}/outputs/tobe/source-code/{sln_file}"
```

---

## Quality Gates

| Gate | Threshold | Action on Failure |
|------|-----------|-------------------|
| `dotnet build` exits 0 | MUST | Fix compilation errors |
| Consumer tests pass | MUST | Fix pact expectations |
| Provider verification passes | MUST | Fix provider implementation |
| All OpenAPI operations covered | ≥ 80% | Add missing interactions |
| Pact files generated | ≥ 1 per BC | Ensure consumer tests produce pacts |

---

## Invariants

- NEVER modify existing source code under `src/` — only read
- Pact files are ONLY generated by consumer tests (never manually)
- Provider tests ONLY verify against existing pact files
- Each consumer test must produce exactly one interaction in the pact JSON
- Consumer and Provider names must be consistent across all test files

---

## Guardrails
- **Timestamp NTP (OBRIGATÓRIO):** NUNCA usar clock do LLM — obter `generated_at` via `Bash: python src/shared/utils/ntp_time.py`


### Step 8 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-qa-contract-test-generator --phase F5 --version 1.1.0 \
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

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)
