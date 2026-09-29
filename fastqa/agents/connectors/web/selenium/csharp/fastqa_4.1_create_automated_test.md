---
name: "fastqa_4.1_create_automated_test_selenium_csharp_web"
description: "Criador de Testes Automatizados — Selenium + C# (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Selenium + C#

## 🎯 Objetivo
Gerar scripts automatizados em **Selenium + C# (.NET)** a partir de cenários Gherkin.

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
dotnet new nunit -n FastQA.Web.Selenium.Tests
cd FastQA.Web.Selenium.Tests

# 2. Instalar pacotes
dotnet add package Selenium.WebDriver
dotnet add package Selenium.Support
dotnet add package WebDriverManager
dotnet add package NUnit
dotnet add package NUnit3TestAdapter
dotnet add package Microsoft.NET.Test.Sdk

# 3. Build
dotnet build
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
│   ├── BasePage.cs
│   └── {FuncionalidadePascalCase}Page.cs
├── Tests/
│   └── {FuncionalidadePascalCase}Tests.cs
├── Data/
│   └── {funcionalidade_snake}_data.json
├── Support/
│   └── TestBase.cs
├── Results/
├── FastQA.Web.Selenium.Tests.csproj
└── .runsettings
```

---

## 📝 Templates

### Spec File (`LoginTests.cs`)
```csharp
using NUnit.Framework;
using OpenQA.Selenium;
using Pages;

namespace Tests;

[TestFixture]
public class LoginTests : TestBase
{
    private LoginPage _loginPage = null!;

    [SetUp]
    public void Setup() => _loginPage = new LoginPage(Driver);

    [Test]
    [Description("Login com credenciais válidas")]
    public void LoginComCredenciaisValidas()
    {
        // Given
        _loginPage.Navigate();

        // When
        _loginPage.FillEmail("usuario@teste.com");
        _loginPage.FillPassword("Senha@123");
        _loginPage.ClickLogin();

        // Then
        Assert.That(Driver.Url, Does.Contain("/dashboard"));
        Assert.That(_loginPage.GetWelcomeMessage(), Is.EqualTo("Bem-vindo"));
    }
}
```

### Page Object (`LoginPage.cs`)
```csharp
using OpenQA.Selenium;

namespace Pages;

public class LoginPage : BasePage
{
    private IWebElement EmailInput => Driver.FindElement(By.Id("email"));
    private IWebElement PasswordInput => Driver.FindElement(By.Id("password"));
    private IWebElement LoginButton => Driver.FindElement(By.CssSelector("button[type='submit']"));
    private IWebElement WelcomeMsg => Driver.FindElement(By.ClassName("welcome-text"));

    public LoginPage(IWebDriver driver) : base(driver) { }

    public void Navigate() => Driver.Navigate().GoToUrl("{{BASE_URL}}/login");
    public void FillEmail(string email) { EmailInput.Clear(); EmailInput.SendKeys(email); }
    public void FillPassword(string pwd) { PasswordInput.Clear(); PasswordInput.SendKeys(pwd); }
    public void ClickLogin() => LoginButton.Click();
    public string GetWelcomeMessage() => WelcomeMsg.Text;
}
```

---

### Config File (`FastQA.Web.Selenium.Tests.csproj`)
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
    <PackageReference Include="NUnit" Version="4.0.0" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
    <PackageReference Include="Selenium.WebDriver" Version="4.16.0" />
    <PackageReference Include="Selenium.Support" Version="4.16.0" />
    <PackageReference Include="WebDriverManager" Version="2.17.0" />
  </ItemGroup>
</Project>
```

### TestBase (`TestBase.cs`)
```csharp
using NUnit.Framework;
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using WebDriverManager;
using WebDriverManager.DriverConfigs.Impl;

namespace Support;

public class TestBase
{
    protected IWebDriver Driver = null!;

    [SetUp]
    public void BaseSetup()
    {
        new DriverManager().SetUpDriver(new ChromeConfig());
        var options = new ChromeOptions();
        options.AddArgument("--window-size=1366,768");
        if (Environment.GetEnvironmentVariable("CI") != null)
            options.AddArgument("--headless");
        Driver = new ChromeDriver(options);
        Driver.Manage().Timeouts().ImplicitWait = TimeSpan.FromSeconds(10);
    }

    [TearDown]
    public void BaseTeardown() => Driver?.Quit();
}
```

---

## 📋 Pré-requisitos
- .NET 8+
- `dotnet add package Selenium.WebDriver`
- `dotnet add package NUnit`
- `dotnet add package WebDriverManager`

## 🔧 Comandos de Execução
```bash
dotnet test
dotnet test --filter "LoginTests"
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
   - **Compile** → corrigir `using` ausente / tipos C#
   - **NoSuchElementException** → revisar `By` locator no Page Object
   - **AssertionException** → ajustar `Assert` ou pré-condição
   - **WebDriverTimeoutException** → aumentar `WebDriverWait` timeout
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
