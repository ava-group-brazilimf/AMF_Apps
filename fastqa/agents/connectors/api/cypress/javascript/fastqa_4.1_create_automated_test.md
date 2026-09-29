---
name: "fastqa_4.1_create_automated_test_cypress_javascript_api"
description: "Criador de Testes Automatizados — Cypress + JavaScript (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Cypress + JavaScript (API)

## 🎯 Objetivo
Gerar scripts automatizados em **Cypress + JavaScript** para testes de API usando `cy.request()`.

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` -> `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` -> `{{TESTS_DIR}}`
- `folder_structure.custom_paths.config` -> `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` (opcional) -> `{{RESULTS_DIR}}`

Fallback legado (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/api`
- `{{TESTS_DIR}} = automated_test/api/tests`
- `{{CONFIG_DIR}} = automated_test/api/config`
- `{{RESULTS_DIR}} = automated_test/api/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade informada pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo de teste: `{funcionalidade-kebab}.cy.js`
> - Arquivo de dados: `{funcionalidade-kebab}.data.json`
> - Exemplo: funcionalidade `"autenticar usuario"` → `autenticar-usuario.cy.js`, `autenticar-usuario.data.json`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── cypress.config.js
├── data/
│   └── {funcionalidade-kebab}.data.json
├── support/
│   ├── commands.js
│   └── e2e.js
├── tests/
│   └── {funcionalidade-kebab}.cy.js
└── results/
```

---

## 📝 Templates

### Spec File (`{funcionalidade-kebab}.cy.js`)
```javascript
const testData = require('../data/{funcionalidade-kebab}.data.json');

describe('{{FEATURE_NAME}} — API', () => {

  it('{{SCENARIO_NAME}}', () => {
    // Given — autenticação
    cy.request({
      method: 'POST',
      url: `${Cypress.env('API_BASE_URL')}/auth/login`,
      body: {
        email: testData.validUser.email,
        password: testData.validUser.password
      }
    }).then((authResponse) => {
      expect(authResponse.status).to.eq(200);
      const token = authResponse.body.token;

      // When — chamada ao endpoint alvo
      cy.request({
        method: 'GET',
        url: `${Cypress.env('API_BASE_URL')}/recurso`,
        headers: { Authorization: `Bearer ${token}` }
      }).then((response) => {

        // Then — validações
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('id');
      });
    });
  });
});
```

### Arquivo de Dados (`{funcionalidade-kebab}.data.json`)
```json
{
  "validUser": {
    "email": "usuario@exemplo.com",
    "password": "SenhaSegura123"
  }
}
```

### Cypress Config (`cypress.config.js`)
```javascript
const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: '',
    specPattern: '{{TESTS_DIR}}/**/*.cy.js',
    supportFile: '{{AUTOMATION_ROOT}}/support/e2e.js',
    videosFolder: '{{RESULTS_DIR}}/videos',
    screenshotsFolder: '{{RESULTS_DIR}}/screenshots',
    video: false,
    screenshotOnRunFailure: false,
    env: {
      API_BASE_URL: 'https://api.exemplo.com'
    }
  }
});
```

### Support File (`support/e2e.js`)
```javascript
require('./commands');
```

### Commands Custom (`support/commands.js`)
```javascript
// Adicione custom commands para ações de API reutilizáveis:
// Cypress.Commands.add('apiLogin', (email, password) => { ... });
```

---

## 📋 Pré-requisitos
- Node.js v22+
- `npm install cypress --save-dev`

## 🔧 Comandos de Execução
```bash
npx cypress open                                         # Interface gráfica
npx cypress run                                          # Modo headless
npx cypress run --spec "{{TESTS_DIR}}/**/*.cy.js"        # Específico
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
npx cypress run --spec "tests/{funcionalidade-kebab}.cy.js"
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída completa + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **Syntax** → corrigir require/import inválido ou propriedades de request incorretas
   - **Status code inesperado** → verificar URL, método HTTP e body enviado
   - **Assertion falhou** → ajustar propriedades esperadas no response body
   - **Timeout / Network** → verificar `API_BASE_URL` no `cypress.config.js`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
