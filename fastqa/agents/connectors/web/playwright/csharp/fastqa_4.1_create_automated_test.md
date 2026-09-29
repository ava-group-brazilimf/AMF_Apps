---
name: "fastqa_4.1_create_automated_test_playwright_csharp_web"
description: "Criador de Testes Automatizados — Playwright + C# (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Playwright + C#

## 🎯 Objetivo
Gerar scripts automatizados em **Playwright + C# (.NET)** a partir de cenários Gherkin.

---
## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` -> `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` -> `{{TESTS_DIR}}`
- `folder_structure.custom_paths.pages` -> `{{PAGES_DIR}}`
- `folder_structure.custom_paths.config` -> `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` (opcional) -> `{{RESULTS_DIR}}`

Fallback legado (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/{platform}`
- `{{TESTS_DIR}} = automated_test/{platform}/tests`
- `{{PAGES_DIR}} = automated_test/{platform}/pages` (ou `screens` para mobile)
- `{{CONFIG_DIR}} = automated_test/{platform}/config`
- `{{RESULTS_DIR}} = automated_test/{platform}/results`

Regra de precedência: esta seção prevalece sobre exemplos legados hardcoded eventualmente existentes no restante do documento.

---
## � Instalação

```bash
# 1. Criar projeto .NET
dotnet new nunit -n FastQA.Web.Tests
cd FastQA.Web.Tests

# 2. Instalar pacotes
dotnet add package Microsoft.Playwright.NUnit

# 3. Build para gerar binários
dotnet build

# 4. Instalar browsers
pwsh bin/Debug/net8.0/playwright.ps1 install
```

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade informada pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo de teste: `{FuncionalidadePascalCase}Tests.cs`
> - Page Object: `{FuncionalidadePascalCase}Page.cs`
> - Arquivo de dados: `{funcionalidade_snake}_data.json`
> - Exemplo: funcionalidade `"login"` → `LoginTests.cs`, `LoginPage.cs`, `login_data.json`

```
{{AUTOMATION_ROOT}}/
├── Pages/
│   └── {FuncionalidadePascalCase}Page.cs
├── Tests/
│   └── {FuncionalidadePascalCase}Tests.cs
├── Data/
│   └── {funcionalidade_snake}_data.json
├── Support/
│   └── TestBase.cs
├── Results/
├── FastQA.Web.Tests.csproj
└── .runsettings
```

---

## 📝 Templates

### Spec File (`LoginTests.cs`)
```csharp
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

namespace Tests;

[Parallelizable(ParallelScope.Self)]
[TestFixture]
public class LoginTests : PageTest
{
    private LoginPage _loginPage = null!;

    [SetUp]
    public async Task Setup()
    {
        _loginPage = new LoginPage(Page);
    }

    [Test]
    [Description("Login com credenciais válidas")]
    public async Task LoginComCredenciaisValidas()
    {
        // Given
        await _loginPage.NavigateAsync();

        // When
        await _loginPage.FillEmailAsync("usuario@teste.com");
        await _loginPage.FillPasswordAsync("Senha@123");
        await _loginPage.ClickLoginAsync();

        // Then
        await Expect(Page).ToHaveURLAsync(new Regex(".*dashboard"));
        await Expect(Page.GetByText("Bem-vindo")).ToBeVisibleAsync();
    }
}
```

### Page Object (`LoginPage.cs`)
```csharp
using Microsoft.Playwright;

namespace Pages;

public class LoginPage
{
    private readonly IPage _page;
    private ILocator EmailInput => _page.GetByLabel("E-mail");
    private ILocator PasswordInput => _page.GetByLabel("Senha");
    private ILocator LoginButton => _page.GetByRole(AriaRole.Button, new() { Name = "Entrar" });

    public LoginPage(IPage page) => _page = page;

    public async Task NavigateAsync() => await _page.GotoAsync("{{BASE_URL}}/login");
    public async Task FillEmailAsync(string email) => await EmailInput.FillAsync(email);
    public async Task FillPasswordAsync(string password) => await PasswordInput.FillAsync(password);
    public async Task ClickLoginAsync() => await LoginButton.ClickAsync();
}
```

---

### Config File (`FastQA.Web.Tests.csproj`)
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.40.0" />
    <PackageReference Include="NUnit" Version="4.0.0" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
  </ItemGroup>
</Project>
```

### Run Settings (`.runsettings`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<RunSettings>
  <Playwright>
    <BrowserName>chromium</BrowserName>
    <LaunchOptions>
      <Headless>true</Headless>
    </LaunchOptions>
  </Playwright>
</RunSettings>
```

---

## 📋 Pré-requisitos
- .NET 8+
- `dotnet add package Microsoft.Playwright.NUnit`
- `pwsh bin/Debug/net8.0/playwright.ps1 install`

## 🔧 Comandos de Execução
```bash
dotnet test                                        # Todos os testes
dotnet test --filter "LoginTests"                  # Específico
dotnet test --logger "html;LogFileName=report.html"  # Com relatório
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
dotnet test --filter "FullyQualifiedName~{FuncionalidadePascalCase}Tests"
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **Compile** → corrigir `using` ausente / tipos C# / namespaces
   - **Locator not found** → revisar `Locator()` / `GetByRole()` no Page Object
   - **PlaywrightException** → ajustar timeout ou seletor
   - **AssertionException** → ajustar `Expect()` ou pré-condição
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
