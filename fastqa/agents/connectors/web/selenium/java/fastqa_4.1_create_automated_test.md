---
name: "fastqa_4.1_create_automated_test_selenium_java_web"
description: "Criador de Testes Automatizados — Selenium + Java (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Selenium + Java

## 🎯 Objetivo
Gerar scripts automatizados em **Selenium + Java** a partir de cenários Gherkin.

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
│   │   ├── BasePage.java
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

import org.junit.jupiter.api.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import pages.LoginPage;
import static org.junit.jupiter.api.Assertions.*;

public class LoginTest {
    static WebDriver driver;
    LoginPage loginPage;

    @BeforeAll
    static void setup() {
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless", "--window-size=1366,768");
        driver = new ChromeDriver(options);
        driver.manage().timeouts().implicitlyWait(java.time.Duration.ofSeconds(10));
    }

    @BeforeEach
    void init() {
        loginPage = new LoginPage(driver);
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
        assertTrue(driver.getCurrentUrl().contains("/dashboard"));
        assertEquals("Bem-vindo", loginPage.getWelcomeMessage());
    }

    @AfterAll
    static void teardown() { driver.quit(); }
}
```

### Page Object (`LoginPage.java`)
```java
package pages;

import org.openqa.selenium.*;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class LoginPage extends BasePage {
    @FindBy(id = "email") private WebElement emailInput;
    @FindBy(id = "password") private WebElement passwordInput;
    @FindBy(css = "button[type='submit']") private WebElement loginButton;
    @FindBy(className = "welcome-text") private WebElement welcomeMsg;

    public LoginPage(WebDriver driver) {
        super(driver);
        PageFactory.initElements(driver, this);
    }

    public void navigate() { driver.get("{{BASE_URL}}/login"); }
    public void fillEmail(String email) { emailInput.clear(); emailInput.sendKeys(email); }
    public void fillPassword(String pwd) { passwordInput.clear(); passwordInput.sendKeys(pwd); }
    public void clickLogin() { loginButton.click(); }
    public String getWelcomeMessage() { return welcomeMsg.getText(); }
}
```

---

## 📋 Pré-requisitos
- Java 17+, Maven 3.8+
- `selenium-java`, `junit-jupiter`, `webdrivermanager`

## 🔧 Comandos de Execução
```bash
mvn test
mvn test -Dtest=LoginTest
mvn surefire-report:report
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
   - **Compile** → corrigir imports Java / tipos
   - **NoSuchElementException** → revisar `By` locator no Page Object
   - **AssertionError** → ajustar `assertEquals` ou pré-condição
   - **TimeoutException** → aumentar `WebDriverWait` / adicionar `ExpectedConditions`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
