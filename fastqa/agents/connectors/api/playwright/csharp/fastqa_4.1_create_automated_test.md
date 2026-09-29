---
name: "fastqa_4.1_create_automated_test_playwright_csharp_api"
description: "Criador de Testes Automatizados — Playwright + C# (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Playwright + C# (API)

## 🎯 Objetivo
Gerar testes automatizados de API REST em **Playwright + C# (.NET)** usando `IAPIRequestContext`.

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `platforms[selected].details.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `platforms[selected].details.custom_paths.tests` → `{{TESTS_DIR}}`
- `platforms[selected].details.custom_paths.config` → `{{CONFIG_DIR}}`
- `platforms[selected].details.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/api`
- `{{TESTS_DIR}} = automated_test/api/Tests`
- `{{CONFIG_DIR}} = automated_test/api/Config`
- `{{RESULTS_DIR}} = automated_test/api/Results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Teste: `{FuncionalidadePascalCase}ApiTests.cs`
> - Client: `{FuncionalidadePascalCase}Client.cs`
> - Dados: `{funcionalidade_snake}_data.json`
> - Exemplo: `"autenticacao"` → `AutenticacaoApiTests.cs`, `AutenticacaoClient.cs`

```
{{AUTOMATION_ROOT}}/
├── Clients/
│   └── {FuncionalidadePascalCase}Client.cs
├── Support/
│   └── ApiHelper.cs
├── Data/
│   └── {funcionalidade_snake}_data.json
├── Tests/
│   └── {FuncionalidadePascalCase}ApiTests.cs
├── Results/
└── FastQA.Api.Tests.csproj
```

---

## 📝 Templates

### Spec File (`{FuncionalidadePascalCase}ApiTests.cs`)
```csharp
using System.Text.Json;
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;
using FastQA.Api.Tests.Clients;

namespace FastQA.Api.Tests.Tests;

[TestFixture]
public class AutenticacaoApiTests : PlaywrightTest
{
    private IAPIRequestContext _request = null!;
    private AutenticacaoClient _client = null!;

    [SetUp]
    public async Task SetupAsync()
    {
        _request = await Playwright.APIRequest.NewContextAsync(new()
        {
            BaseURL = Environment.GetEnvironmentVariable("BASE_URL") ?? "{{BASE_URL}}",
            ExtraHTTPHeaders = new Dictionary<string, string>
            {
                ["Content-Type"] = "application/json",
                ["Accept"] = "application/json"
            }
        });
        _client = new AutenticacaoClient(_request);
    }

    [TearDown]
    public async Task TeardownAsync() => await _request.DisposeAsync();

    [Test]
    [Category("positivo")]
    public async Task LoginComCredenciaisValidas_DeveRetornarToken()
    {
        var response = await _client.LoginAsync("usuario@teste.com", "Senha@123");

        Assert.That(response.Status, Is.EqualTo(200));
        var body = JsonSerializer.Deserialize<JsonElement>(await response.TextAsync());
        Assert.That(body.TryGetProperty("token", out var token), Is.True);
        Assert.That(token.GetString(), Is.Not.Empty);
    }

    [Test]
    [Category("negativo")]
    public async Task LoginComCredenciaisInvalidas_DeveRetornar401()
    {
        var response = await _client.LoginAsync("errado@teste.com", "senhaerrada");

        Assert.That(response.Status, Is.EqualTo(401));
        var body = JsonSerializer.Deserialize<JsonElement>(await response.TextAsync());
        Assert.That(body.TryGetProperty("error", out _), Is.True);
    }
}
```

### API Client (`{FuncionalidadePascalCase}Client.cs`)
```csharp
using Microsoft.Playwright;

namespace FastQA.Api.Tests.Clients;

public class AutenticacaoClient
{
    private readonly IAPIRequestContext _request;

    public AutenticacaoClient(IAPIRequestContext request)
    {
        _request = request;
    }

    public async Task<IAPIResponse> LoginAsync(string email, string password)
    {
        return await _request.PostAsync("/auth/login", new()
        {
            DataObject = new { email, password }
        });
    }

    public async Task<IAPIResponse> LogoutAsync(string token)
    {
        return await _request.PostAsync("/auth/logout", new()
        {
            Headers = new Dictionary<string, string>
            {
                ["Authorization"] = $"Bearer {token}"
            }
        });
    }

    public async Task<IAPIResponse> GetProfileAsync(string token)
    {
        return await _request.GetAsync("/auth/profile", new()
        {
            Headers = new Dictionary<string, string>
            {
                ["Authorization"] = $"Bearer {token}"
            }
        });
    }
}
```

### Project File (`FastQA.Api.Tests.csproj`)
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.44.0" />
    <PackageReference Include="NUnit" Version="4.0.1" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.9.0" />
  </ItemGroup>
</Project>
```

---

## 📋 Pré-requisitos
- .NET 8+
- Playwright CLI

## 🔧 Instalação
```bash
dotnet build
pwsh bin/Debug/net8.0/playwright.ps1 install
```

## 🚀 Comandos de Execução
```bash
dotnet test                                              # Todos os testes
dotnet test --filter "Category=positivo"                 # Filtrar por categoria
BASE_URL=https://staging.api.com dotnet test             # URL por variável
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
dotnet test --filter "FullyQualifiedName~{FuncionalidadePascalCase}ApiTests"
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **HttpRequestException** → API não está no ar ou `BASE_URL` incorreto
   - **AssertionException: status** → status diferente do esperado; revisar endpoint/payload
   - **NullReferenceException** → campo ausente no response body
   - **CS0246 (type not found)** → verificar `using` e namespaces
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
