---
name: "fastqa_4.1_create_automated_test_karate"
description: "Criador de Testes Automatizados — Karate + Java (API + BDD)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Karate + Java (API + BDD)

## 🎯 Objetivo
Gerar scripts automatizados em **Karate DSL** para testes de API com sintaxe BDD nativa.

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
> - Feature file: `{funcionalidade-kebab}.feature`
> - Runner: `{FuncionalidadePascalCase}Runner.java`
> - Arquivo de dados: `{funcionalidade-kebab}_data.json`
> - Exemplo: funcionalidade `"usuarios"` → `usuarios.feature`, `UsuariosRunner.java`

```
{{AUTOMATION_ROOT}}/
├── src/test/java/
│   ├── karate-config.js
│   ├── {funcionalidade-kebab}/
│   │   ├── {funcionalidade-kebab}.feature
│   │   ├── {FuncionalidadePascalCase}Runner.java
│   │   └── helpers.js
│   └── common/
│       └── auth.feature
├── data/
│   └── {funcionalidade-kebab}_data.json
├── results/
└── pom.xml
```

---

## 📝 Templates

### Feature File (`users.feature`)
```gherkin
Feature: Gerenciamento de Usuários
  API REST para CRUD de usuários do sistema

  Background:
    * url baseUrl
    * def authToken = callonce read('classpath:common/auth.feature').token

  Scenario: Listar usuários com sucesso
    Given path '/api/users'
    And header Authorization = 'Bearer ' + authToken
    When method get
    Then status 200
    And match response.data == '#[_ > 0]'
    And match each response.data contains { id: '#number', email: '#string' }

  Scenario: Retornar 401 sem token de autenticação
    Given path '/api/users'
    When method get
    Then status 401

  Scenario: Criar usuário com dados válidos
    Given path '/api/users'
    And header Authorization = 'Bearer ' + authToken
    And request { email: 'novo@teste.com', name: 'Novo Usuário', password: 'Senha@123' }
    When method post
    Then status 201
    And match response.email == 'novo@teste.com'
    And match response.name == 'Novo Usuário'

  Scenario Outline: Validar campos obrigatórios
    Given path '/api/users'
    And header Authorization = 'Bearer ' + authToken
    And request { email: '<email>', name: '<name>' }
    When method post
    Then status 400

    Examples:
      | email           | name          |
      |                 | Teste         |
      | test@test.com   |               |
      | invalid-email   | Teste         |
```

### Auth (`common/auth.feature`)
```gherkin
Feature: Autenticação

  Scenario: Obter token de autenticação
    Given url baseUrl
    And path '/auth/login'
    And request { email: 'admin@teste.com', password: 'Senha@123' }
    When method post
    Then status 200
    * def token = response.token
```

### Karate Config (`karate-config.js`)
```javascript
function fn() {
  var config = {
    baseUrl: karate.properties['baseUrl'] || '{{BASE_URL}}'
  };
  karate.configure('connectTimeout', 30000);
  karate.configure('readTimeout', 30000);
  return config;
}
```

### Runner (`UsersRunner.java`)
```java
package users;

import com.intuit.karate.junit5.Karate;

class UsersRunner {
    @Karate.Test
    Karate testUsers() {
        return Karate.run("users").relativeTo(getClass());
    }
}
```

### pom.xml (dependências)
```xml
<dependencies>
    <dependency>
        <groupId>com.intuit.karate</groupId>
        <artifactId>karate-junit5</artifactId>
        <version>1.4.1</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## 📋 Pré-requisitos
- Java 17+, Maven

## 🔧 Comandos de Execução
```bash
mvn test                                   # Todos
mvn test -Dtest=UsersRunner                # Específico
mvn test -DbaseUrl=https://staging.api.com # Com URL customizada
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
mvn test -Dtest={FuncionalidadePascalCase}Runner
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **Compile** → corrigir imports Java do Runner
   - **KarateException** → revisar sintaxe Karate no `.feature` (indent, `*` prefix)
   - **Status code mismatch** → ajustar `Then status` ou header de auth
   - **Match failed** → corrigir expressão `match` ou dados do fixture
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
