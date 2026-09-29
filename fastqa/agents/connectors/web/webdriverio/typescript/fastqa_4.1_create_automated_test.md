---
name: "fastqa_4.1_create_automated_test_webdriverio_typescript_web"
description: "Criador de Testes Automatizados — WebdriverIO + TypeScript (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: WebdriverIO + TypeScript (Web)

## 🎯 Objetivo
Gerar testes automatizados Web em **WebdriverIO + TypeScript** seguindo o padrão Page Object Model.

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
> - Teste: `{funcionalidade.kebab}.spec.ts`
> - Page Object: `{FuncionalidadePascalCase}.page.ts`
> - Dados: `{funcionalidade.kebab}.data.json`
> - Exemplo: `"login usuario"` → `login-usuario.spec.ts`, `LoginUsuario.page.ts`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── wdio.conf.ts
├── data/
│   └── {funcionalidade.kebab}.data.json
├── pages/
│   ├── BasePage.ts
│   └── {FuncionalidadePascalCase}.page.ts
├── support/
│   └── helpers.ts
├── tests/
│   └── {funcionalidade.kebab}.spec.ts
├── results/
├── tsconfig.json
└── package.json
```

---

## 📝 Templates

### Spec File (`{funcionalidade.kebab}.spec.ts`)
```typescript
import { expect } from '@wdio/globals';
import { LoginUsuarioPage } from '../pages/LoginUsuario.page';
import testData from '../data/login-usuario.data.json';

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

### Page Object (`{FuncionalidadePascalCase}.page.ts`)
```typescript
import { BasePage } from './BasePage';

export class LoginUsuarioPage extends BasePage {
  get emailInput() { return $('[data-testid="email"]'); }
  get passwordInput() { return $('[data-testid="password"]'); }
  get loginButton() { return $('[data-testid="login-btn"]'); }
  get welcomeMessage() { return $('[data-testid="welcome-msg"]'); }
  get errorMessage() { return $('[data-testid="error-msg"]'); }

  async open() {
    await super.open('/login');
  }

  async fillEmail(email: string) {
    await this.emailInput.waitForDisplayed();
    await this.emailInput.setValue(email);
  }

  async fillPassword(password: string) {
    await this.passwordInput.setValue(password);
  }

  async clickLogin() {
    await this.loginButton.click();
  }

  async login(email: string, password: string) {
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.clickLogin();
  }
}
```

### Base Page (`BasePage.ts`)
```typescript
export class BasePage {
  protected baseUrl = process.env.BASE_URL ?? '{{BASE_URL}}';

  async open(path: string) {
    await browser.url(`${this.baseUrl}${path}`);
    await browser.waitUntil(
      () => browser.execute(() => document.readyState === 'complete'),
      { timeout: 15000, timeoutMsg: 'Página não carregou em 15s' }
    );
  }

  async waitForVisible(selector: string, timeout = 10000) {
    const el = $(selector);
    await el.waitForDisplayed({ timeout });
    return el;
  }

  async waitForUrl(urlPart: string, timeout = 10000) {
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes(urlPart),
      { timeout, timeoutMsg: `URL não contém "${urlPart}" em ${timeout}ms` }
    );
  }
}
```

### Helpers (`support/helpers.ts`)
```typescript
export async function clearBrowserState() {
  await browser.deleteCookies();
  await browser.execute(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

export async function takeScreenshot(name: string) {
  await browser.saveScreenshot(`results/${name}-${Date.now()}.png`);
}
```

### Data File (`{funcionalidade.kebab}.data.json`)
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

### Config (`config/wdio.conf.ts`)
```typescript
import { Options } from '@wdio/types';
import * as dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(__dirname, '../.env') });

export const config: Options.Testrunner = {
  runner: 'local',
  specs: ['{{TESTS_DIR}}/**/*.spec.ts'],
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

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "types": ["@wdio/globals/types", "node"]
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules"]
}
```

### package.json
```json
{
  "name": "fastqa-webdriverio-typescript",
  "private": true,
  "scripts": {
    "test": "wdio run config/wdio.conf.ts"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@wdio/cli": "^9.18.0",
    "@wdio/globals": "^9.18.0",
    "@wdio/junit-reporter": "^9.18.0",
    "@wdio/local-runner": "^9.18.0",
    "@wdio/mocha-framework": "^9.18.0",
    "@wdio/spec-reporter": "^9.18.0",
    "@wdio/types": "^9.18.0",
    "dotenv": "^16.4.5",
    "expect-webdriverio": "^5.4.1",
    "ts-node": "^10.9.2",
    "typescript": "^5.5.0",
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
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.conf.ts
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.conf.ts --spec tests/{funcionalidade.kebab}.spec.ts
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.conf.ts --spec tests/{funcionalidade.kebab}.spec.ts
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ElementNotFound** → revisar `data-testid` no Page Object
   - **browser is not defined** → verificar se está usando `@wdio/globals`
   - **Cannot find module** → verificar imports TypeScript e `tsconfig.json`
   - **TimeoutError** → aumentar `waitforTimeout` no `wdio.conf.ts`
   - **AssertionError** → revisar valor esperado no `expect`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
