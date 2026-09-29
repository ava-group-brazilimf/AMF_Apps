---
name: "fastqa_4.1_create_automated_test_playwright_java_api"
description: "Criador de Testes Automatizados — Playwright + Java (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Playwright + Java (API)

## 🎯 Objetivo
Gerar testes automatizados de API REST em **Playwright + Java** usando `APIRequestContext`.

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `platforms[selected].details.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `platforms[selected].details.custom_paths.tests` → `{{TESTS_DIR}}`
- `platforms[selected].details.custom_paths.config` → `{{CONFIG_DIR}}`
- `platforms[selected].details.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/api`
- `{{TESTS_DIR}} = automated_test/api/tests`
- `{{CONFIG_DIR}} = automated_test/api/config`
- `{{RESULTS_DIR}} = automated_test/api/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Teste: `{FuncionalidadePascalCase}ApiTest.java`
> - Client: `{FuncionalidadePascalCase}Client.java`
> - Dados: `{funcionalidade_snake}_data.json`
> - Exemplo: `"autenticacao"` → `AutenticacaoApiTest.java`, `AutenticacaoClient.java`

```
{{AUTOMATION_ROOT}}/
├── src/
│   ├── main/java/
│   │   ├── clients/
│   │   │   └── {FuncionalidadePascalCase}Client.java
│   │   └── support/
│   │       └── ApiHelper.java
│   └── test/java/tests/
│       └── {FuncionalidadePascalCase}ApiTest.java
├── data/
│   └── {funcionalidade_snake}_data.json
├── results/
└── pom.xml
```

---

## 📝 Templates

### Spec File (`{FuncionalidadePascalCase}ApiTest.java`)
```java
package tests;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.RequestOptions;
import org.junit.jupiter.api.*;
import clients.AutenticacaoClient;

import static org.junit.jupiter.api.Assertions.*;

public class AutenticacaoApiTest {
    static Playwright playwright;
    static APIRequestContext request;
    AutenticacaoClient client;

    @BeforeAll
    static void setup() {
        playwright = Playwright.create();
        request = playwright.request().newContext(
            new APIRequest.NewContextOptions()
                .setBaseURL(System.getenv("BASE_URL") != null ? System.getenv("BASE_URL") : "{{BASE_URL}}")
                .setExtraHTTPHeaders(java.util.Map.of(
                    "Content-Type", "application/json",
                    "Accept", "application/json"
                ))
        );
    }

    @BeforeEach
    void init() {
        client = new AutenticacaoClient(request);
    }

    @AfterAll
    static void teardown() {
        if (request != null) request.dispose();
        if (playwright != null) playwright.close();
    }

    @Test
    @DisplayName("CT-XX - Login com credenciais válidas retorna token")
    void loginComCredenciaisValidas() {
        APIResponse response = client.login("usuario@teste.com", "Senha@123");

        assertEquals(200, response.status());
        String body = response.text();
        assertTrue(body.contains("token"), "Body deve conter 'token': " + body);
    }

    @Test
    @DisplayName("CT-XX - Login com credenciais inválidas retorna 401")
    void loginComCredenciaisInvalidas() {
        APIResponse response = client.login("errado@teste.com", "senhaerrada");

        assertEquals(401, response.status());
        String body = response.text();
        assertTrue(body.contains("error"), "Body deve conter 'error': " + body);
    }
}
```

### API Client (`{FuncionalidadePascalCase}Client.java`)
```java
package clients;

import com.microsoft.playwright.APIRequestContext;
import com.microsoft.playwright.APIResponse;
import com.microsoft.playwright.options.RequestOptions;

public class AutenticacaoClient {
    private final APIRequestContext request;

    public AutenticacaoClient(APIRequestContext request) {
        this.request = request;
    }

    public APIResponse login(String email, String password) {
        return request.post("/auth/login",
            RequestOptions.create().setData(
                java.util.Map.of("email", email, "password", password)
            )
        );
    }

    public APIResponse logout(String token) {
        return request.post("/auth/logout",
            RequestOptions.create().setHeader("Authorization", "Bearer " + token)
        );
    }

    public APIResponse getProfile(String token) {
        return request.get("/auth/profile",
            RequestOptions.create().setHeader("Authorization", "Bearer " + token)
        );
    }
}
```

### POM (`pom.xml`)
```xml
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.fastqa</groupId>
  <artifactId>fastqa-playwright-api</artifactId>
  <version>1.0.0</version>

  <dependencies>
    <dependency>
      <groupId>com.microsoft.playwright</groupId>
      <artifactId>playwright</artifactId>
      <version>1.44.0</version>
    </dependency>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.1.2</version>
      </plugin>
    </plugins>
  </build>
</project>
```

---

## 📋 Pré-requisitos
- Java 17+
- Maven 3.8+

## 🔧 Instalação
```bash
mvn install
```

## 🚀 Comandos de Execução
```bash
mvn test                                                # Todos os testes
mvn test -Dtest=AutenticacaoApiTest                     # Específico
mvn test -DBASE_URL=https://staging.api.com             # URL por variável
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
mvn test -Dtest={FuncionalidadePascalCase}ApiTest
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ConnectException** → API não está no ar ou `BASE_URL` incorreto
   - **AssertionError: status** → status diferente do esperado; revisar endpoint/payload
   - **ClassNotFoundException** → verificar imports e estrutura de pacotes
   - **NullPointerException** → campo ausente no response body
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
