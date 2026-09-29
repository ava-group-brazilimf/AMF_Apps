---
name: "fastqa_4.1_create_automated_test_playwright_java_web"
description: "Criador de Testes Automatizados — Playwright + Java (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Playwright + Java

## 🎯 Objetivo
Gerar scripts automatizados em **Playwright + Java** a partir de cenários Gherkin.

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

## 📂 Estrutura de Saída

```
## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade informada pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo de teste: `{FuncionalidadePascalCase}Test.java`
> - Page Object: `{FuncionalidadePascalCase}Page.java`
> - Arquivo de dados: `{funcionalidade_snake}_data.json`
> - Exemplo: funcionalidade `"login"` → `LoginTest.java`, `LoginPage.java`, `login_data.json`

```
{{AUTOMATION_ROOT}}/
├── src/
│   ├── main/java/pages/
│   │   └── {FuncionalidadePascalCase}Page.java
│   └── test/java/tests/
│       └── {FuncionalidadePascalCase}Test.java
├── data/
│   └── {funcionalidade_snake}_data.json
├── results/
├── pom.xml
└── README.md
```

---

## 📝 Templates

### Spec File (`LoginTest.java`)
```java
package tests;

import com.microsoft.playwright.*;
import org.junit.jupiter.api.*;
import pages.LoginPage;
import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class LoginTest {
    static Playwright playwright;
    static Browser browser;
    BrowserContext context;
    Page page;
    LoginPage loginPage;

    @BeforeAll
    static void launchBrowser() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(true));
    }

    @BeforeEach
    void createContext() {
        context = browser.newContext();
        page = context.newPage();
        loginPage = new LoginPage(page);
    }

    @Test
    @DisplayName("Login com credenciais válidas")
    void testLoginComCredenciaisValidas() {
        // Given
        loginPage.navigate();

        // When
        loginPage.fillEmail("usuario@teste.com");
        loginPage.fillPassword("Senha@123");
        loginPage.clickLogin();

        // Then
        assertThat(page).hasURL(java.util.regex.Pattern.compile(".*dashboard"));
        assertThat(page.getByText("Bem-vindo")).isVisible();
    }

    @AfterEach
    void closeContext() { context.close(); }

    @AfterAll
    static void closeBrowser() { browser.close(); playwright.close(); }
}
```

### Page Object (`LoginPage.java`)
```java
package pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

public class LoginPage {
    private final Page page;
    private final Locator emailInput;
    private final Locator passwordInput;
    private final Locator loginButton;

    public LoginPage(Page page) {
        this.page = page;
        this.emailInput = page.getByLabel("E-mail");
        this.passwordInput = page.getByLabel("Senha");
        this.loginButton = page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Entrar"));
    }

    public void navigate() { page.navigate("{{BASE_URL}}/login"); }
    public void fillEmail(String email) { emailInput.fill(email); }
    public void fillPassword(String password) { passwordInput.fill(password); }
    public void clickLogin() { loginButton.click(); }
}
```

---

## 📋 Pré-requisitos
- Java 17+
- Maven 3.8+
- Dependência: `com.microsoft.playwright:playwright:1.40+`

## 🔧 Comandos de Execução
```bash
mvn test                                    # Todos os testes
mvn test -Dtest=LoginTest                   # Específico
mvn surefire-report:report                  # Relatório
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
mvn test -Dtest={FuncionalidadePascalCase}Test
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **Compile** → corrigir imports Java / tipos Playwright
   - **Locator not found** → revisar `page.locator()` / `page.getByRole()` no Page Object
   - **AssertionError** → ajustar `assertThat()` ou pré-condição
   - **TimeoutError** → aumentar `page.setDefaultTimeout()` ou adicionar `waitFor()`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
