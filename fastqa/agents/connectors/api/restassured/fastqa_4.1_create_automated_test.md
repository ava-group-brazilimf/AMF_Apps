---
name: "fastqa_4.1_create_automated_test_restassured"
description: "Criador de Testes Automatizados — RestAssured + Java (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: RestAssured + Java (API)

## 🎯 Objetivo
Gerar scripts automatizados em **RestAssured + JUnit 5** para testes de API REST.

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

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade/endpoint informado pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo de teste: `{FuncionalidadePascalCase}Test.java`
> - Arquivo de dados: `{funcionalidade_snake}_data.json`
> - Exemplo: funcionalidade `"usuarios"` → `UsuariosTest.java`, `usuarios_data.json`

```
{{AUTOMATION_ROOT}}/
├── src/
│   ├── main/java/
│   │   ├── config/
│   │   │   └── ApiConfig.java
│   │   └── support/
│   │       └── ApiClient.java
│   └── test/java/tests/
│       └── {FuncionalidadePascalCase}Test.java
├── data/
│   └── {funcionalidade_snake}_data.json
├── results/
└── pom.xml
```

---

## 📝 Templates

### Spec File (`UsersTest.java`)
```java
package tests;

import io.restassured.RestAssured;
import io.restassured.response.Response;
import org.junit.jupiter.api.*;
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class UsersTest {

    static String authToken;

    @BeforeAll
    static void setup() {
        RestAssured.baseURI = "{{BASE_URL}}";

        authToken = given()
            .contentType("application/json")
            .body("{\"email\":\"admin@teste.com\",\"password\":\"Senha@123\"}")
        .when()
            .post("/auth/login")
        .then()
            .statusCode(200)
            .extract().path("token");
    }

    @Test
    @Order(1)
    @DisplayName("Listar usuários com sucesso")
    void testListarUsuariosComSucesso() {
        given()
            .header("Authorization", "Bearer " + authToken)
        .when()
            .get("/api/users")
        .then()
            .statusCode(200)
            .body("data", notNullValue())
            .body("data.size()", greaterThan(0));
    }

    @Test
    @Order(2)
    @DisplayName("Retornar 401 sem token")
    void testRetornar401SemToken() {
        when()
            .get("/api/users")
        .then()
            .statusCode(401);
    }

    @Test
    @Order(3)
    @DisplayName("Criar usuário com dados válidos")
    void testCriarUsuarioComDadosValidos() {
        String body = "{\"email\":\"novo@teste.com\",\"name\":\"Novo Usuário\",\"password\":\"Senha@123\"}";

        given()
            .header("Authorization", "Bearer " + authToken)
            .contentType("application/json")
            .body(body)
        .when()
            .post("/api/users")
        .then()
            .statusCode(201)
            .body("email", equalTo("novo@teste.com"))
            .body("name", equalTo("Novo Usuário"));
    }
}
```

### pom.xml (dependências)
```xml
<dependencies>
    <dependency>
        <groupId>io.rest-assured</groupId>
        <artifactId>rest-assured</artifactId>
        <version>5.4.0</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>5.10.0</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>io.rest-assured</groupId>
        <artifactId>json-schema-validator</artifactId>
        <version>5.4.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## 📋 Pré-requisitos
- Java 17+, Maven

## 🔧 Comandos de Execução
```bash
mvn test
mvn test -Dtest=UsersTest
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
   - **Compile** → corrigir imports Java / tipos RestAssured
   - **Connection refused** → verificar `RestAssured.baseURI`
   - **Status code mismatch** → ajustar `.then().statusCode()` ou header de auth
   - **JsonPath error** → corrigir expressão `Matchers` ou estrutura do body
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
