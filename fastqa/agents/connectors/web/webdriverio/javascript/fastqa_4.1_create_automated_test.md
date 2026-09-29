---
name: "fastqa_4.1_create_automated_test_webdriverio_javascript_web"
description: "Criador de Testes Automatizados — WebdriverIO + JavaScript (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: WebdriverIO + JavaScript (Web)

## 🎯 Objetivo
Gerar testes automatizados Web em **WebdriverIO + JavaScript** seguindo o padrão Page Object Model.

---

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

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Teste: `{funcionalidade-kebab}.spec.js`
> - Page Object: `{FuncionalidadePascalCase}.page.js`
> - Dados: `{funcionalidade-kebab}.data.json`
> - Exemplo: `"login usuario"` → `login-usuario.spec.js`, `LoginUsuario.page.js`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── wdio.conf.js
├── data/
│   └── {funcionalidade-kebab}.data.json
├── pages/
│   ├── BasePage.js
│   └── {FuncionalidadePascalCase}.page.js
├── support/
│   └── helpers.js
├── tests/
│   └── {funcionalidade-kebab}.spec.js
├── results/
└── package.json
```

---

## 📝 Templates

### Spec File (`{funcionalidade-kebab}.spec.js`)
```javascript
const { expect } = require('@wdio/globals');
const { LoginUsuarioPage } = require('../pages/LoginUsuario.page');
const testData = require('../data/login-usuario.data.json');

describe('{{FEATURE_NAME}}', () => {
  const page = new LoginUsuarioPage();

  it('{{SCENARIO_NAME}}', async () => {
    await page.open();
    await page.fillEmail(testData.validUser.email);
    await page.fillPassword(testData.validUser.password);
    await page.clickLogin();

    await expect(page.welcomeMessage).toHaveText('Bem-vindo');
    await expect(browser).toHaveUrlContaining('/dashboard');
  });
});
```

### Page Object (`{FuncionalidadePascalCase}.page.js`)
```javascript
const { BasePage } = require('./BasePage');

class LoginUsuarioPage extends BasePage {
  get emailInput() { return $('[data-testid="email"]'); }
  get passwordInput() { return $('[data-testid="password"]'); }
  get loginButton() { return $('[data-testid="login-btn"]'); }
  get welcomeMessage() { return $('[data-testid="welcome-msg"]'); }
  get errorMessage() { return $('[data-testid="error-msg"]'); }

  async open() {
    await super.open('/login');
  }

  async fillEmail(email) {
    await this.emailInput.waitForDisplayed();
    await this.emailInput.setValue(email);
  }

  async fillPassword(password) {
    await this.passwordInput.setValue(password);
  }

  async clickLogin() {
    await this.loginButton.click();
  }

  async login(email, password) {
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.clickLogin();
  }
}

module.exports = { LoginUsuarioPage };
```

### Base Page (`BasePage.js`)
```javascript
class BasePage {
  constructor() {
    this.baseUrl = process.env.BASE_URL ?? '{{BASE_URL}}';
  }

  async open(path) {
    await browser.url(`${this.baseUrl}${path}`);
    await browser.waitUntil(
      () => browser.execute(() => document.readyState === 'complete'),
      { timeout: 15000, timeoutMsg: 'Página não carregou em 15s' }
    );
  }

  async waitForVisible(selector, timeout = 10000) {
    const el = $(selector);
    await el.waitForDisplayed({ timeout });
    return el;
  }

  async waitForUrl(urlPart, timeout = 10000) {
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes(urlPart),
      { timeout, timeoutMsg: `URL não contém "${urlPart}" em ${timeout}ms` }
    );
  }
}

module.exports = { BasePage };
```

### Helpers (`support/helpers.js`)
```javascript
async function clearBrowserState() {
  await browser.deleteCookies();
  await browser.execute(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

async function takeScreenshot(name) {
  await browser.saveScreenshot(`results/${name}-${Date.now()}.png`);
}

module.exports = { clearBrowserState, takeScreenshot };
```

### Data File (`{funcionalidade-kebab}.data.json`)
```json
{
  "validUser": {
    "email": "usuario@teste.com",
    "password": "Senha@123"
  },
  "invalidUser": {
    "email": "errado@teste.com",
    "password": "senhaerrada"
  }
}
```

### Config (`config/wdio.conf.js`)
```javascript
require('dotenv').config();

exports.config = {
  runner: 'local',
  specs: ['{{TESTS_DIR}}/**/*.spec.js'],
  maxInstances: 1,
  framework: 'mocha',
  mochaOpts: { ui: 'bdd', timeout: 60000 },
  reporters: [
    'spec',
    ['junit', { outputDir: '{{RESULTS_DIR}}' }]
  ],
  capabilities: [{
    browserName: 'chrome',
    'goog:chromeOptions': {
      args: ['--headless', '--disable-gpu', '--window-size=1920,1080']
    }
  }],
  baseUrl: process.env.BASE_URL ?? '{{BASE_URL}}',
  waitforTimeout: 10000,
  connectionRetryTimeout: 120000,
  connectionRetryCount: 3,
};
```

### package.json
```json
{
  "name": "fastqa-webdriverio-javascript",
  "private": true,
  "scripts": {
    "test": "wdio run config/wdio.conf.js"
  },
  "devDependencies": {
    "@wdio/cli": "^9.18.0",
    "@wdio/globals": "^9.18.0",
    "@wdio/junit-reporter": "^9.18.0",
    "@wdio/local-runner": "^9.18.0",
    "@wdio/mocha-framework": "^9.18.0",
    "@wdio/spec-reporter": "^9.18.0",
    "dotenv": "^16.4.5",
    "expect-webdriverio": "^5.4.1",
    "webdriverio": "^9.18.0"
  }
}
```

---

## 📋 Pré-requisitos
- Node.js v22+
- Chrome instalado

## 🔧 Instalação
```bash
cd {{AUTOMATION_ROOT}} && npm install
```

## 🚀 Comandos de Execução
```bash
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.conf.js
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.conf.js --spec tests/{funcionalidade-kebab}.spec.js
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.conf.js --spec tests/{funcionalidade-kebab}.spec.js
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ElementNotFound** → revisar `data-testid` no Page Object
   - **browser is not defined** → verificar se está usando `@wdio/globals`
   - **Cannot find module** → verificar `require()` e paths relativos
   - **TimeoutError** → aumentar `waitforTimeout` no `wdio.conf.js`
   - **AssertionError** → revisar valor esperado no `expect`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
