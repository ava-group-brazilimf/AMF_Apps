---
name: "fastqa_4.1_create_automated_test_web_cypress_javascript"
description: "Criador de Testes Automatizados — Cypress + JavaScript (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Cypress + JavaScript (Web)

## 🎯 Objetivo
Gerar scripts automatizados em **Cypress + JavaScript** para testes de interface Web seguindo o padrão Page Object Model.

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `platforms[selected].details.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `platforms[selected].details.custom_paths.tests` → `{{TESTS_DIR}}`
- `platforms[selected].details.custom_paths.pages` → `{{PAGES_DIR}}`
- `platforms[selected].details.custom_paths.config` → `{{CONFIG_DIR}}`
- `platforms[selected].details.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/web`
- `{{TESTS_DIR}} = automated_test/web/tests`
- `{{PAGES_DIR}} = automated_test/web/pages`
- `{{CONFIG_DIR}} = automated_test/web/config`
- `{{RESULTS_DIR}} = automated_test/web/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade informada pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo de teste: `{funcionalidade-kebab}.cy.js`
> - Page Object: `{FuncionalidadePascalCase}.page.js`
> - Arquivo de dados: `{funcionalidade-kebab}.data.json`
> - Exemplo: funcionalidade `"login usuario"` → `login-usuario.cy.js`, `LoginUsuario.page.js`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── cypress.config.js
├── data/
│   └── {funcionalidade-kebab}.data.json
├── pages/
│   └── {FuncionalidadePascalCase}.page.js
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
const { LoginUsuarioPage } = require('../pages/LoginUsuario.page');
const testData = require('../data/{funcionalidade-kebab}.data.json');

describe('{{FEATURE_NAME}}', () => {
  const page = new LoginUsuarioPage();

  beforeEach(() => {
    page.navigate();
  });

  it('{{SCENARIO_NAME}}', () => {
    // Given — página carregada no beforeEach

    // When
    page.fillEmail(testData.validUser.email);
    page.fillPassword(testData.validUser.password);
    page.clickLogin();

    // Then
    cy.url().should('include', '/dashboard');
    cy.contains('Bem-vindo').should('be.visible');
  });
});
```

### Page Object (`{FuncionalidadePascalCase}.page.js`)
```javascript
class LoginUsuarioPage {
  navigate() {
    cy.visit(`${Cypress.env('BASE_URL')}/login`);
  }

  fillEmail(email) {
    cy.get('[data-cy=email]').clear().type(email);
  }

  fillPassword(password) {
    cy.get('[data-cy=password]').clear().type(password);
  }

  clickLogin() {
    cy.get('[data-cy=login-button]').click();
  }
}

module.exports = { LoginUsuarioPage };
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

### Cypress Config (`config/cypress.config.js`)
```javascript
const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: '',
    specPattern: '{{TESTS_DIR}}/**/*.cy.js',
    supportFile: '{{AUTOMATION_ROOT}}/support/e2e.js',
    videosFolder: '{{RESULTS_DIR}}/videos',
    screenshotsFolder: '{{RESULTS_DIR}}/screenshots',
    viewportWidth: 1366,
    viewportHeight: 768,
    video: true,
    screenshotOnRunFailure: true,
    env: {
      BASE_URL: 'https://app.exemplo.com'
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
// Adicione custom commands para ações reutilizáveis:
// Cypress.Commands.add('login', (email, password) => { ... });
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
   - **Syntax** → corrigir require/import inválido ou seletores ausentes
   - **Elemento não encontrado** → revisar seletor `data-cy` no Page Object
   - **Assertion falhou** → ajustar valor esperado ou adicionar espera explícita
   - **Timeout** → adicionar `{ timeout: 10000 }` ao comando
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
