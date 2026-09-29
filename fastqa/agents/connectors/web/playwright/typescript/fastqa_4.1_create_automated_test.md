---
name: "fastqa_4.1_create_automated_test_playwright_typescript_web"
description: "Criador de Testes Automatizados — Playwright + TypeScript (Web)"

tools:
  - playwright mcp
  - memory
  - sequential-thinking
---

# Connector: Playwright + TypeScript

## 🎯 Objetivo
Criar testes automatizados Playwright funcionais e prontos para execução, seguindo:
- ✅ Page Object Model (POM)
- ✅ Estrutura modular do projeto
- ✅ Integração com MCP Playwright
- ✅ Código TypeScript executável
- ✅ Baseado em evidências manuais ou cenários Gherkin

### 🔒 Regra mandatória de escrita de testes
- `test.describe` **sempre** no formato de funcionalidade: `PBI-XX - Funcionalidade`
- `test` **sempre** no formato de caso: `CT-XX - Nome do caso`
- `test.step` **sempre** com keyword BDD: `Given`, `When`, `Then`, `And`
- Cada `test.step` deve conter **somente chamada de método** de `pages/` ou `support/`
- É **proibido** escrever código explícito de interação/validação dentro do `test.step` (`expect`, `page.locator`, `page.click`, loops, condicionais)
- `beforeEach` e `afterEach` devem reutilizar funções compartilhadas de `support/fixtures.ts`

**Foco:** IMPLEMENTAR testes funcionais imediatamente, não apenas orientar.

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` -> `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` -> `{{TESTS_DIR}}`
- `folder_structure.custom_paths.pages` -> `{{PAGES_DIR}}`
- `folder_structure.custom_paths.config` -> `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` (opcional) -> `{{RESULTS_DIR}}`

Fallback legado (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/web`
- `{{TESTS_DIR}} = automated_test/web/tests`
- `{{PAGES_DIR}} = automated_test/web/pages`
- `{{CONFIG_DIR}} = automated_test/web/config`
- `{{RESULTS_DIR}} = automated_test/web/results`

Regra de precedência: esta seção prevalece sobre exemplos legados hardcoded eventualmente existentes no restante do documento.

---

## � Instalação

```bash
# 1. Instalar dependências
npm install -D @playwright/test dotenv

# 2. Instalar browsers
npx playwright install

# 3. (Opcional) Instalar apenas chromium
npx playwright install chromium
```

---

## 📂 Estrutura de Saída

```
{{AUTOMATION_ROOT}}/
├── config/
│   ├── playwright.config.ts
│   ├── .env.dev
│   ├── .env.test
│   └── .env.prod
├── data/
│   └── {funcionalidade}.data.json
├── pages/
│   └── {FuncionalidadePascalCase}Page.page.ts
├── support/
│   ├── fixtures.ts
│   ├── helpers.ts
│   └── hooks.ts
├── tests/
│   └── {funcionalidade}.spec.ts
└── results/
    ├── playwright-report/
    ├── {PBI-ID}/
    │   ├── CT-1/
    │   │   └── {HH}h{MM}m{SS}s/    ← timestamp da execução (ex: 14h23m07s)
    │   └── CT-2/
    │       └── {HH}h{MM}m{SS}s/
    └── test-results-{ProjectName}.json
```

> **ℹ️ Como gerar o timestamp no playwright.config.ts:**
> ```typescript
> const ts = new Date().toTimeString().slice(0,8).replace(/:/g, 'h').replace(/(\d{2})h(\d{2})$/, '$1m$2s');
> // ex: '14h23m07s'
> ```

---

## � Exemplo Prático Real - Teste Completo (Logo Avanade)

Este é um **exemplo profissional completo** que implementa TODOS os padrões descritos neste documento.

### Page Object: ContatoPage.page.ts
```typescript
import { Page, Locator } from '@playwright/test';

export class ContatoPage {
  readonly page: Page;
  readonly logoAvanade: Locator;
  readonly botaoContato: Locator;

  constructor(page: Page) {
    this.page = page;
    this.logoAvanade = page.locator('[data-testid="logo-avanade"]');
    this.botaoContato = page.locator('[data-testid="btn-contato"]');
  }

  async navegarPara(url: string) {
    await this.page.goto(url, { waitUntil: 'networkidle' });
  }

  async isLogoVisivel(): Promise<boolean> {
    return await this.logoAvanade.isVisible();
  }
  
  async validarLogoVisivel(): Promise<void> {
    const visivel = await this.isLogoVisivel();
    if (!visivel) {
      throw new Error('Logo não está visível');
    }
  }

  async isButtonVisivel(): Promise<boolean> {
    return await this.botaoContato.isVisible();
  }
  
  async validarBotaoVisivel(): Promise<void> {
    const visivel = await this.isButtonVisivel();
    if (!visivel) {
      throw new Error('Botão de contato não está visível');
    }
  }

  async clicarBotaoContato() {
    await this.botaoContato.click();
  }
  
  async validarTextoBotonContainsContato(): Promise<void> {
    const texto = await this.botaoContato.textContent();
    if (!texto?.toLowerCase().includes('contato')) {
      throw new Error(`Texto do botão não contém 'contato'. Texto atual: "${texto}"`);
    }
  }
  
  async validarUrlContainsContato(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
    const url = this.page.url();
    if (!url.toLowerCase().includes('contato')) {
      throw new Error(`URL não contém 'contato'. URL atual: "${url}"`);
    }
  }
}
```

### Teste: contatoAvanade.spec.ts
```typescript
import { test, expect } from '@playwright/test';
import { ContatoPage } from '../pages/ContatoPage';
import { setupTest, teardownTest } from '../support/fixtures';

test.describe('PBI-13 - Validação da logo e botão de contato', () => {
  let contatoPage: ContatoPage;

  test.beforeEach(async ({ page }) => {
    contatoPage = new ContatoPage(page);
    await setupTest(page, contatoPage);
  });

  test.afterEach(async ({ page }) => {
    await teardownTest(page);
  });

  test('CT-14 - Exibir logo da Avanade no cabeçalho', async () => {
    await test.step('Given que acesso a página inicial da Avanade', async () => {
      await contatoPage.navegarPara('https://www.avanade.com/pt-br');
    });

    await test.step('When a página carrega completamente', async () => {
      await expect(contatoPage.logoAvanade).toBeVisible();
    });

    await test.step('Then deve exibir a logo da Avanade no cabeçalho', async () => {
      await contatoPage.validarLogoVisivel();
    });
  });

  test('CT-15 - Validar botão "Entre em contato conosco" está visível', async () => {
    await test.step('Given que estou na página inicial da Avanade', async () => {
      await contatoPage.navegarPara('https://www.avanade.com/pt-br');
    });

    await test.step('When vejo o cabeçalho da página', async () => {
      await contatoPage.validarBotaoVisivel();
    });

    await test.step('Then o botão "Entre em contato" deve estar visível', async () => {
      await contatoPage.validarBotaoVisivel();
    });

    await test.step('And o texto do botão deve estar legível', async () => {
      await contatoPage.validarTextoBotonContainsContato();
    });
  });

  test('CT-16 - Clicar botão deve navegar para página de contato', async () => {
    await test.step('Given que estou na página inicial da Avanade', async () => {
      await contatoPage.navegarPara('https://www.avanade.com/pt-br');
    });

    await test.step('And o botão "Entre em contato" está visível', async () => {
      await contatoPage.validarBotaoVisivel();
    });

    await test.step('When clico no botão "Entre em contato"', async () => {
      await contatoPage.clicarBotaoContato();
    });

    await test.step('Then devo navegar para página ou seção de contato', async () => {
      await contatoPage.validarUrlContainsContato();
    });
  });
});
```

**Executar:**
```bash
npx playwright test tests/contatoAvanade.spec.ts
npx playwright show-report
```

---

## �📝 Templates

### Spec File (`{feature}.spec.ts`)
```typescript
import { test, expect } from '@playwright/test';
import { NomePage } from '../pages/NomePage';
import { setupTest, teardownTest } from '../support/fixtures';

test.describe('PBI-XX - Funcionalidade descritiva', () => {
  let nomePage: NomePage;

  test.beforeEach(async ({ page }) => {
    nomePage = new NomePage(page);
    await setupTest(page, nomePage);
  });

  test.afterEach(async ({ page }) => {
    await teardownTest(page);
  });

  test('CT-XX - Descrição clara do caso de teste', async () => {
    await test.step('Given que [condição inicial do cenário]', async () => {
      await nomePage.navegarPara('https://exemplo.com');
    });
    
    await test.step('When [ação do usuário]', async () => {
      await nomePage.realizarAcao('Texto de entrada');
    });
    
    await test.step('Then [resultado esperado]', async () => {
      await nomePage.validarResultadoEsperado();
    });

    await test.step('And [validação adicional]', async () => {
      await nomePage.validarEstadoEsperado();
    });
  });
});
```

### Page Object (`{PageName}.page.ts`)
```typescript
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel('E-mail');
    this.passwordInput = page.getByLabel('Senha');
    this.loginButton = page.getByRole('button', { name: 'Entrar' });
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }

  async navigate() {
    await this.page.goto('{{BASE_URL}}/login');
    await this.page.waitForLoadState('networkidle');
  }

  async fillEmail(email: string) {
    await this.emailInput.fill(email);
  }

  async fillPassword(password: string) {
    await this.passwordInput.fill(password);
  }

  async clickLogin() {
    await this.loginButton.click();
  }

  async isErrorMessageVisible(): Promise<boolean> {
    return await this.errorMessage.isVisible();
  }
  
  async validarMensagemErroVisivel(): Promise<void> {
    const visivel = await this.isErrorMessageVisible();
    if (!visivel) {
      throw new Error('Mensagem de erro não está visível');
    }
  }

  async submitLoginForm(email: string, password: string) {
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.clickLogin();
  }
}
```

### Data File (`{feature}.data.json`)
```json
{
  "validUser": {
    "email": "usuario@teste.com",
    "password": "Senha@123"
  },
  "invalidUser": {
    "email": "invalido@teste.com",
    "password": "senhaerrada"
  }
}
```

### Support File - Fixtures (`support/fixtures.ts`)
```typescript
import { Page } from '@playwright/test';

/**
 * Preparação padrão para todos os testes
 * Responsável por:
 * - Limpar cookies/storage
 * - Configurar timeout global
 * - Preparar dados iniciais
 */
export async function setupTest(page: Page, pageObject?: any) {
  // Limpar dados locais e cookies
  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  // Configurar timeout global
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(30000);

  // Inicializar state/dados se necessário
  if (pageObject?.initialize) {
    await pageObject.initialize();
  }
}

/**
 * Limpeza padrão após cada teste
 * Responsável por:
 * - Fechar conexões abertas
 * - Limpar dados de teste
 * - Capturar screenshots em caso de falha
 */
export async function teardownTest(page: Page) {
  // Fechar abas abertas
  const pages = page.context().pages();
  for (const p of pages) {
    if (p !== page) {
      await p.close();
    }
  }

  // Limpar dados de teste
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  // Página será fechada automaticamente pelo Playwright
}

/**
 * Setup para testes de autenticação
 */
export async function setupAuthenticatedTest(
  page: Page,
  loginPage: any,
  credentials: { email: string; password: string }
) {
  await setupTest(page);
  await loginPage.navigate();
  await loginPage.submitLoginForm(credentials.email, credentials.password);
  await page.waitForLoadState('networkidle');
}
```

### Support File - Helpers (`support/helpers.ts`)
```typescript
import { Page } from '@playwright/test';

/**
 * Aguardar por múltiplos seletores até que um fique visível
 */
export async function waitForAnyElementVisible(
  page: Page,
  selectors: string[],
  timeout = 5000
): Promise<string> {
  try {
    return await Promise.race(
      selectors.map(selector =>
        page.waitForSelector(selector, { state: 'visible', timeout })
          .then(() => selector)
      )
    );
  } catch {
    throw new Error(`Nenhum elemento visível entre: ${selectors.join(', ')}`);
  }
}

/**
 * Extrair texto de múltiplos elementos
 */
export async function getMultipleTexts(page: Page, selector: string): Promise<string[]> {
  return await page.locator(selector).allTextContents();
}

/**
 * Validar URL contém string esperada
 */
export async function expectUrlContains(page: Page, expectedString: string) {
  const url = page.url();
  if (!url.includes(expectedString)) {
    throw new Error(`URL "${url}" não contém "${expectedString}"`);
  }
}

/**
 * Aguardar elemento e tomar screenshot
 */
export async function captureElementScreenshot(
  page: Page,
  selector: string,
  filename: string
) {
  const element = page.locator(selector);
  await element.waitFor({ state: 'visible' });
  await element.screenshot({ path: `results/${filename}` });
}
```

---

### Config File (`config/playwright.config.ts`)
```typescript
import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import path from 'path';

// Ler variáveis de ambiente externas - OBRIGATÓRIAS PARA RASTREAR EVIDÊNCIAS
const projectName = process.env.PROJECT_NAME || 'nome-do-projeto';
const environment = process.env.ENVIRONMENT || 'dev';
const pbiId = process.env.PBI_ID || null;              // Ex: 'PBI-13'
const usId = process.env.US_ID || null;                // Ex: 'US-5'
const tcId = process.env.TC_ID || 'test-execution';    // Ex: 'TC-14' (obrigatório)

// Validar se PBI_ID ou US_ID foi fornecido
const featureId = pbiId || usId;
if (!featureId) {
  console.warn('⚠️  AVISO: PBI_ID ou US_ID não foi definido. Use: PBI_ID="PBI-X" npx playwright test');
}

// Determina o arquivo de ambiente dinamicamente
const envFilePath = path.resolve(__dirname, '.env.' + environment);
dotenv.config({ path: envFilePath });

// Construir outputDir obrigatório: {{RESULTS_DIR}}/{PBI-ID}/{TC-ID}
// Usar path dinâmico vindo do project_config.json (com fallback legado)
const baseResultsPath = process.env.RESULTS_DIR || 'automated_test/web/results';
const resultsPath = featureId && tcId 
  ? path.join(baseResultsPath, featureId, tcId)
  : path.join(baseResultsPath, projectName + '-' + environment);

console.log(`📝 Configuração Playwright:`);
console.log(`   - Ambiente: ${envFilePath}`);
console.log(`   - PBI/US: ${featureId || 'não definido'}`);
console.log(`   - TC: ${tcId}`);
console.log(`   - Output: ${resultsPath}`);

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: '../tests',
  outputDir: resultsPath,
  timeout: 180000, // 180 segundos (3 minutos) para cada teste
  expect: {
    timeout: 30000, // 30 segundos para asserções com expect
  },
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { 
      outputFolder: path.join(baseResultsPath, 'playwright-report', `${projectName}-${environment}`),
      open: 'never', // Não abrir automaticamente
    }],
    ['json', { 
      outputFile: path.join(baseResultsPath, `test-results-${projectName}.json`)
    }],
    ['list'], // Mostra progresso no terminal
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('')`. */
    baseURL: process.env.BASE_URL,
    
    headless: false, // Navegador VISÍVEL para desenvolvimento

    actionTimeout: 15000, // 15 segundos para ações (click, fill, etc)
    navigationTimeout: 90000, // 90 segundos para navegação

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: environment === 'dev' ? 'on' : 'on-first-retry',
    screenshot: environment === 'dev' ? 'on' : 'only-on-failure',
    video: environment === 'dev' ? 'on' : 'retain-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }, // HD completo
      },
    },
    // Outros navegadores comentados - descomentar se necessário
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
});
```

**Estrutura de Evidências - PADRÃO OBRIGATÓRIO:**

A estrutura de outputs deve SEMPRE respeitar este padrão:
```
{workspace}/automated_test/web/results/
├── {PBI-ID ou US-ID}/
│   ├── {TC-ID}/
│   │   ├── test-results/                     ← Resultados de execução
│   │   │   └── index.html
│   │   ├── screenshots/
│   │   ├── videos/
│   │   ├── traces/
│   │   └── logs/
│   ├── {TC-ID-2}/
│   └── {TC-ID-3}/
├── PBI-2/
│   ├── TC-21/
│   └── TC-22/
└── test-results-{projectName}.json           ← Relatório consolidado
```

**Exemplos REAIS:**
```
automated_test/web/results/PBI-13/CT-14/
automated_test/web/results/PBI-2/TC-21/
automated_test/web/results/US-5/TC-45/
automated_test/web/results/US-2/TC-21/
```

**Como funciona:**
1. **PBI_ID** ou **US_ID** — Definido via variável de ambiente (uma ou outra, nunca ambas)
2. **TC_ID** — ID do test case sendo executado (exemplo: `TC-14`, `CT-21`)
3. playwright.config.ts **automaticamente** cria essa estrutura no outputDir
---

## Exemplo Completo: Edição de Recursos

### Page Object (pages/EdicaoRecursoPage.ts)

```typescript
import { Page, Locator } from '@playwright/test';

export class EdicaoRecursoPage {
  readonly page: Page;
  readonly btnEditar: Locator;
  readonly campoTitulo: Locator;
  readonly campoDescricao: Locator;
  readonly btnSalvar: Locator;
  readonly mensagemSucesso: Locator;
  readonly mensagemErro: Locator;

  constructor(page: Page) {
    this.page = page;
    this.btnEditar = page.locator('[data-testid="btn-editar"]');
    this.campoTitulo = page.locator('#campo-titulo');
    this.campoDescricao = page.locator('#campo-descricao');
    this.btnSalvar = page.locator('#btn-salvar');
    this.mensagemSucesso = page.locator('[role="alert"].sucesso');
    this.mensagemErro = page.locator('[role="alert"].erro');
  }

  async navegarPara(url: string) {
    await this.page.goto(url, { waitUntil: 'networkidle' });
  }

  async abrirEdicao() {
    await this.btnEditar.click();
    await this.campoTitulo.waitFor({ state: 'visible' });
  }

  async preencherTitulo(titulo: string) {
    await this.campoTitulo.fill(titulo);
  }

  async preencherDescricao(descricao: string) {
    await this.campoDescricao.fill(descricao);
  }

  async clicarSalvar() {
    await this.btnSalvar.click();
  }

  async isMensagemSucessoVisivel(): Promise<boolean> {
    return await this.mensagemSucesso.isVisible();
  }

  async isMensagemErroVisivel(): Promise<boolean> {
    return await this.mensagemErro.isVisible();
  }

  async obterTextoMensagemErro(): Promise<string | null> {
    if (await this.mensagemErro.isVisible()) {
      return await this.mensagemErro.textContent();
    }
    return null;
  }
}
```

### Teste (tests/edicaoRecurso.spec.ts)

```typescript
import { test, expect } from '@playwright/test';
import { EdicaoRecursoPage } from '../pages/EdicaoRecursoPage';
import { setupTest, teardownTest } from '../support/fixtures';
import recursosData from '../data/edicaoRecurso.json';

test.describe('PBI-13 - Edição de Recursos da Plataforma', () => {
  let edicaoPage: EdicaoRecursoPage;

  test.beforeEach(async ({ page }) => {
    edicaoPage = new EdicaoRecursoPage(page);
    await setupTest(page, edicaoPage);
  });

  test.afterEach(async ({ page }) => {
    await teardownTest(page);
  });

  test('CT-14 - Editar título e descrição de recurso com sucesso', async () => {
    await test.step('Given que estou na página de recursos e há um recurso disponível', async () => {
      await edicaoPage.navegarPara('https://app.exemplo.com/recursos');
    });

    await test.step('When clico no botão de editar o recurso', async () => {
      await edicaoPage.abrirEdicao();
    });

    await test.step('Then preenchendo os campos de título e descrição com dados válidos', async () => {
      await edicaoPage.preencherTitulo(recursosData.recursoValido.titulo);
      await edicaoPage.preencherDescricao(recursosData.recursoValido.descricao);
    });

    await test.step('And clico em salvar', async () => {
      await edicaoPage.clicarSalvar();
    });

    await test.step('And deve exibir mensagem de sucesso', async () => {
      const sucesso = await edicaoPage.isMensagemSucessoVisivel();
      expect(sucesso).toBe(true);
    });
  });

  test('CT-15 - Validar campos obrigatórios ao tentar salvar sem dados', async () => {
    await test.step('Given que estou na página de edição de recursos', async () => {
      await edicaoPage.navegarPara('https://app.exemplo.com/recursos');
      await edicaoPage.abrirEdicao();
    });

    await test.step('When clico em salvar sem preencher os campos obrigatórios', async () => {
      await edicaoPage.preencherTitulo('');
      await edicaoPage.preencherDescricao('');
      await edicaoPage.clicarSalvar();
    });

    await test.step('Then deve exibir mensagem de erro', async () => {
      const erro = await edicaoPage.isMensagemErroVisivel();
      expect(erro).toBe(true);
    });

    await test.step('And a mensagem deve indicar que os campos são obrigatórios', async () => {
      const textoErro = await edicaoPage.obterTextoMensagemErro();
      expect(textoErro).toContain('obrigatório');
    });
  });

  test('CT-16 - Validar tamanho máximo do título', async () => {
    await test.step('Given que estou no formulário de edição', async () => {
      await edicaoPage.navegarPara('https://app.exemplo.com/recursos');
      await edicaoPage.abrirEdicao();
    });

    await test.step('When preenchendo o título com mais de 255 caracteres', async () => {
      const tituloGrande = 'A'.repeat(300);
      await edicaoPage.preencherTitulo(tituloGrande);
    });

    await test.step('Then o campo deve limitar a entrada em 255 caracteres', async () => {
      const valorAtual = await edicaoPage.campoTitulo.inputValue();
      expect(valorAtual.length).toBeLessThanOrEqual(255);
    });
  });
});
```

### Dados de Teste (data/edicaoRecurso.json)

```json
{
  "recursoValido": {
    "titulo": "Novo Recurso de Teste Automatizado",
    "descricao": "Esta é uma descrição detalhada para validação de edição de recurso no sistema de testes automatizados"
  },
  "recursoInvalido": {
    "titulo": "",
    "descricao": ""
  },
  "recursoComCaracteresEspeciais": {
    "titulo": "Recurso@!#$%^&*()Teste",
    "descricao": "Descrição com caracteres especiais: @!#$%^&*()"
  }
}
```

---

## Massa de Dados (../data/)

### Exemplo: recursos.json

```json
{
  "recursoValido": {
    "titulo": "Recurso de Teste Automatizado",
    "descricao": "Descrição detalhada para validação"
  },
  "recursoInvalido": {
    "titulo": "",
    "descricao": ""
  }
}
```

**Uso no teste:**

```typescript
import recursosData from '../data/recursos.json';

test('Teste com massa de dados', async ({ page }) => {
  const dados = recursosData.recursoValido;
  await edicaoPage.editarRecurso(dados.titulo, dados.descricao);
  // ...
});
```

---

## 📋 Pré-requisitos
- Node.js v22+
- `npm install -D @playwright/test dotenv`
- `npx playwright install`

## � Ordem de Operações (OBRIGATÓRIA)

### 1️⃣ **Gerar playwright.config.ts**

O arquivo **DEVE** incluir:
- Leitura de **PBI_ID** e **US_ID** via variáveis de ambiente
- Leitura de **TC_ID** (obrigatório para rastreamento)
- **outputDir** construído OBRIGATORIAMENTE: `{{RESULTS_DIR}}/{PBI-ID ou US-ID}/{TC-ID}`
- Carregamento de `.env.{environment}` (dev, test, prod)
- Timeouts: test 180s, expect 30s, action 15s, navigation 90s
- headless: false (navegador visível)

**Template já disponível acima na seção "Config File" da documentação.**

### 2️⃣ **Verificar/Instalar Playwright**

Validar que Playwright está completamente instalado em `{{AUTOMATION_ROOT}}`:
```bash
cd {{AUTOMATION_ROOT}}

# Verificar se package.json existe
ls -la package.json

# Se NÃO existe, criar:
npm init -y

# Instalar as 4 dependências obrigatórias
npm install -D @playwright/test @types/node dotenv typescript

# Instalar os browsers (chromium, firefox, webkit)
npx playwright install

# Validar instalação
npx playwright --version
```

**Validação de sucesso:** Deve retornar `Playwright Test vX.XX.X`

### 3️⃣ **Gerar Código** (pages, tests, support, data)

Após Playwright validado e instalado:
```bash
# Criar estrutura de arquivos obrigatória
# ✅ Page Objects                → pages/{NomePage}.page.ts
# ✅ Testes                       → tests/{feature}.spec.ts
# ✅ Helpers & Fixtures           → support/fixtures.ts, helpers.ts
# ✅ Massa de dados               → data/{feature}.data.json
# ✅ Arquivos de configuração     → config/.env.{dev,test,prod}

# Exemplo com estrutura mínima
mkdir -p pages tests support data
touch pages/.gitkeep tests/.gitkeep support/.gitkeep data/.gitkeep
touch config/.env.dev
```

**Estrutura final esperada:**
```
{{AUTOMATION_ROOT}}/
├── config/
│   ├── playwright.config.ts      (✅ com suporte PBI_ID/US_ID/TC_ID)
│   ├── .env.dev
│   ├── .env.test
│   └── .env.prod
├── data/
│   └── {feature}.data.json
├── pages/
│   ├── {PageName}.page.ts
│   └── {PageName2}.page.ts
├── support/
│   ├── fixtures.ts
│   ├── helpers.ts
│   └── hooks.ts
├── tests/
│   └── {feature}.spec.ts
└── results/                      (gerado automaticamente no primeiro run)
    ├── PBI-13/TC-14/
    ├── US-5/TC-21/
    └── test-results-{projectName}.json
```

---

## 🔧 Comandos de Execução

### Com Rastreamento Obrigatório (PBI-ID + TC-ID)
```bash
cd {{AUTOMATION_ROOT}}

# Executar com PBI_ID (preferido para requisitos/epics)
PBI_ID="PBI-13" TC_ID="TC-14" PROJECT_NAME="avanade-web" ENVIRONMENT="dev" npx playwright test

# Executar com US_ID (preferido para user stories)
US_ID="US-5" TC_ID="TC-21" PROJECT_NAME="avanade-web" ENVIRONMENT="dev" npx playwright test

# Executar teste específico com rastreamento
PBI_ID="PBI-13" TC_ID="TC-15" PROJECT_NAME="avanade-web" npx playwright test tests/contatoAvanade.spec.ts

# Com navegador visível (headed mode)
PBI_ID="PBI-13" TC_ID="TC-14" PROJECT_NAME="avanade-web" ENVIRONMENT="dev" npx playwright test --headed

# Interface gráfica (UI mode)
PBI_ID="PBI-13" TC_ID="TC-14" PROJECT_NAME="avanade-web" npx playwright test --ui

# Modo debug com browser
PBI_ID="PBI-13" TC_ID="TC-14" PROJECT_NAME="avanade-web" npx playwright test --debug
```

### Execução Sem Rastreamento (não recomendado)
```bash
# Teste específico (cria em results/projeto-dev/)
npx playwright test tests/{feature}.spec.ts

# Todos os testes
npx playwright test

# Resultado do relatório
npx playwright show-report
```

### Variáveis de Ambiente - Referência Completa
| Variável | Obrigatória | Exemplo | Descrição |
|----------|-------------|---------|-----------|
| `PBI_ID` | Semi | `PBI-13` | ID da PBI (Product Backlog Item) - OU US_ID |
| `US_ID` | Semi | `US-5` | ID da User Story - OU PBI_ID |
| `TC_ID` | ✅ SIM | `TC-14` | ID do Test Case (obrigatório para rastreamento) |
| `PROJECT_NAME` | ✅ SIM | `avanade-web` | Nome do projeto |
| `ENVIRONMENT` | Opcional | `dev` | Ambiente (dev, test, prod) - padrão: dev |
| `ENVIRONMENT` (arquivo) | Opcional | `.env.dev` | Arquivo de configuração carregado automaticamente |

**Resultado esperado:**
```
✅ Evidências salvas em: {{RESULTS_DIR}}/PBI-13/TC-14/
   - screenshots/
   - videos/
   - traces/
   - test-results/
```
---

## ✅ Checklist de Validação de Rastreamento

**ANTES de executar os testes, validar que tudo está configurado corretamente:**

- [ ] **PBI_ID ou US_ID foi definido** — Ao menos um dos dois deve estar presente
- [ ] **TC_ID foi definido** — ✅ OBRIGATÓRIO para rastreamento (ex: `TC-14`, `CT-21`)
- [ ] **PROJECT_NAME foi definido** — ✅ OBRIGATÓRIO (ex: `avanade-web`)
- [ ] **ENVIRONMENT foi definido** — Opcional (padrão: `dev` se não informado)
- [ ] **Variáveis exportadas ou em command line** — Verificar se estão acessíveis via `echo $PBI_ID`
- [ ] **Diretório base existe** — `{{AUTOMATION_ROOT}}`
- [ ] **Arquivo config/playwright.config.ts existe** — Com suporte a PBI_ID/US_ID/TC_ID
- [ ] **Arquivo .env.dev/.env.test/.env.prod existe** — Com BASE_URL e outras credenciais
- [ ] **npx playwright --version retorna versão válida** — Versão 1.40+ recomendado
- [ ] **Browsers instalados** — Executar `npx playwright install` se necessário
- [ ] **Estrutura de pastas criada** — pages/, tests/, support/, data/ com arquivos mínimos
- [ ] **TypeScript compila sem erros** — Executar `npx tsc --noEmit` para validar

**Validação de execução:**
```bash
# Confirmar que as variáveis estão prontas
echo $PBI_ID           # Deve exibir PBI-13 (ou similar)
echo $US_ID            # Ou exibir US-5 (se usando US em vez de PBI)
echo $TC_ID            # Deve exibir TC-14 (obrigatório)
echo $PROJECT_NAME     # Deve exibir avanade-web

# Confirmar que outputDir será criado corretamente
echo "{{RESULTS_DIR}}/$PBI_ID/$TC_ID"
# Resultado esperado: {{RESULTS_DIR}}/PBI-13/TC-14
```

---

## Boas Práticas

### Separação de Responsabilidades (Page Object Model)
✅ **Page Object** contém TODA a lógica de interação  
✅ **Teste** apenas orquestra chamadas de métodos das Pages/Support

**Nunca coloque lógica de teste (page.fill, page.click) diretamente nos testes.**

### Seletores Robustos - Ordem de Prioridade
1️⃣ `[data-testid="elemento"]` — PREFERIDO (mais robusto)  
2️⃣ `#id-unico` — ID único  
3️⃣ `getByRole()` e `getByLabel()` — Acessibilidade  
4️⃣ Seletores CSS muito específicos — Último recurso  
❌ XPath complexo e classes genéricas — PROIBIDO

### Esperas Dinâmicas (Obrigatório)
✅ `.waitFor({ state: 'visible' })`  
✅ `.waitForLoadState('networkidle')`  
✅ `expect().toBeVisible()`  
❌ `.waitForTimeout()` — NUNCA usar (extremamente frágil)

### Reutilização via Support Files
Funções comuns em `support/fixtures.ts` evitam duplicação em múltiplos testes.

---

## 📏 Convenções Profissionais

### Nomenclatura de Testes (Padrão BDD)
✅ **describe**: `PBI-XX - Funcionalidade Descritiva`  
✅ **test**: `CT-XX - Descrição Clara do Caso de Teste`  
✅ **test.step**: `Given/When/Then/And + descrição em português`

### Estrutura de test.step() - Padrão BDD em Português
```typescript
// ✅ CORRETO - Segue formato BDD com ações claras
await test.step('Given que o botão "Entre em contato conosco" está visível', async () => {
  await contatosPage.navegarPara(url);
});

await test.step('When clica no botão "Entre em contato conosco"', async () => {
  await contatosPage.clicarBotaoContato();
});

await test.step('Then deve navegar para página ou seção de contato', async () => {
  await contatosPage.validarNavegacaoParaContato();
});

await test.step('And o texto do botão deve estar legível', async () => {
  await contatosPage.validarTextoBotaoLegivel();
});

// ❌ INCORRETO - Lógica explícita no step
await test.step('Clicar botão', async () => {
  const botao = page.locator('button');  // ❌ Evitar!
  await botao.click();                   // ❌ Evitar!
});
```

### Organização de Métodos em Page Objects
```typescript
// ✅ CORRETO - Apenas chamadas de métodos da página
await test.step('When o usuário edita o recurso', async () => {
  await edicaoPage.preencherTitulo('Novo Título');
  await edicaoPage.preencherDescricao('Nova descrição');
  await edicaoPage.clicarSalvar();
});

// ❌ INCORRETO - Lógica explícita e locators diretos
await test.step('Editar recurso', async () => {
  const titulo = page.locator('#campo-titulo');      // ❌ Evitar!
  await titulo.fill('Novo Título');                  // ❌ Evitar!
  const salvar = page.locator('#btn-salvar');        // ❌ Evitar!
  await salvar.click();                              // ❌ Evitar!
});
```

### Localização de Elementos - Prioridade
```typescript
// ✅ PRIORIDADE 1 - data-testid (RECOMENDADO)
this.botao = page.locator('[data-testid="btn-salvar"]');

// ✅ PRIORIDADE 2 - ID único
this.campoEmail = page.locator('#email-input');

// ✅ PRIORIDADE 3 - Role + Label (Acessibilidade)
this.botaoEntrar = page.getByRole('button', { name: 'Entrar' });
this.campoSenha = page.getByLabel('Senha');

// ✅ PRIORIDADE 4 - CSS específico
this.mensagemErro = page.locator('[role="alert"].erro');

// ❌ EVITAR - XPath complexo
this.elemento = page.locator('//form/div[5]/button[@type="submit"]');

// ❌ EVITAR - Classes genéricas
this.botao = page.locator('.btn');      // Muito genérico!
this.campo = page.locator('.form-input'); // Muito genérico!
```

### beforeEach / afterEach - Reutilizar Support
```typescript
// ✅ CORRETO - Usar funções do support
test.beforeEach(async ({ page }) => {
  nomePage = new NomePage(page);
  await setupTest(page, nomePage);           // Função do support/fixtures.ts
});

test.afterEach(async ({ page }) => {
  await teardownTest(page);                  // Função do support/fixtures.ts
});

// ❌ INCORRETO - Código duplicado
test.beforeEach(async ({ page }) => {
  await page.context().clearCookies();       // ❌ Duplicado em vários testes!
  localStorage.clear();                      // ❌ Duplicado em vários testes!
  // ...
});
```

### Nomenclatura de Arquivos
| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Arquivo de teste | `{funcionalidade}.spec.ts` | `edicaoRecurso.spec.ts` |
| Page Object | `{PageName}.page.ts` | `EdicaoRecursoPage.page.ts` |
| Dados de teste | `{funcionalidade}.data.json` | `edicaoRecurso.data.json` |
| Helpers | `helpers.ts` | `support/helpers.ts` |
| Fixtures | `fixtures.ts` | `support/fixtures.ts` |
| Config | `playwright.config.ts` | `config/playwright.config.ts` |

---

## Checklist de Qualidade Profissional

Antes de considerar o teste completo, validar:

### Nomenclatura & Padrão BDD
- [ ] **test.describe** segue padrão: `PBI-XX - Funcionalidade descritiva`
- [ ] **test** segue padrão: `CT-XX - Descrição clara do caso de teste`
- [ ] Cada **test.step** contém keyword BDD: `Given`, `When`, `Then`, `And`
- [ ] **test.steps** descrevem comportamento em português, não implementação

### Estrutura & Separação de Responsabilidades
- [ ] **Lógica confinada em Page Objects** — Nenhum locator direto nos testes
- [ ] **test.step contém APENAS chamadas de métodos** — Sem `page.fill()`, `page.click()` direto
- [ ] **Nenhum `expect()` direto em test.step** — TODOS os expects em métodos das Pages
- [ ] **beforeEach/afterEach reutilizam** funções de `support/fixtures.ts`
- [ ] **Cada Page Object tem responsabilidade única clara**
- [ ] **Métodos compostos** em Page Object para operações comuns
- [ ] **Métodos de validação** (validarXXX) que contêm expects/assertions

### Seletores & Estabilidade
- [ ] **Seletores robustos**: data-testid > ID > role > CSS específico
- [ ] **NENHUM XPath** complexo ou frágil
- [ ] **NENHUMA espera estática** (`waitForTimeout`)
- [ ] **Esperas dinâmicas** via `waitFor()`, `waitForLoadState()`, `expect()`
- [ ] **Locators usam getByRole, getByLabel** quando possível (acessibilidade)

### Dados & Configurações
- [ ] **Massa de dados em JSON** — `data/{funcionalidade}.data.json`
- [ ] **Dados importados no teste** — Não hardcoded
- [ ] **Variáveis de ambiente** — Via `.env` (BASE_URL, credenciais, etc.)
- [ ] **Config Playwright** — Em `config/playwright.config.ts`

### Código TypeScript
- [ ] **TypeScript compila** sem erros
- [ ] **Tipos definidos explicitamente** — `async (...) => Promise<...>`
- [ ] **Imports corretos** — Caminhos relativos corretos
- [ ] **Sem `any` desnecessário** — Tipagem forte

### Executabilidade & Resultados
- [ ] **Teste executável** via `npx playwright test {feature}.spec.ts`
- [ ] **Relatórios gerados** em `results/` automaticamente
- [ ] **Screenshots em caso de falha** capturados automaticamente
- [ ] **Vídeos de falha** (opcional) configurados em `playwright.config.ts`

### Support & Reutilização
- [ ] **beforeEach calls** `setupTest()` do support
- [ ] **afterEach calls** `teardownTest()` do support
- [ ] **Helpers reutilizáveis** criados em `support/helpers.ts`
- [ ] **Fixtures customizados** definidos em `support/fixtures.ts` (se necessário)

### Documentação & Manutenibilidade
- [ ] **Page Object documentado** — Comentários JSDoc em métodos públicos
- [ ] **Teste auto-documentado** — Steps descrevem o que está acontecendo
- [ ] **Dados claros** — JSON com nomes descritivos
- [ ] **Estrutura fácil de estender** para novos casos de teste



---

## Instruções para Implementação

**REGRAS OBRIGATÓRIAS - PADRÃO PROFISSIONAL:**

1. **NOMENCLATURA BDD OBRIGATÓRIA**
   - `test.describe` = `PBI-XX - Funcionalidade Descritiva`
   - `test` = `CT-XX - Descrição Clara do Caso de Teste`
   - `test.step` = Conter palavra BDD (Given/When/Then/And) + descrição em português

2. **SEPARAÇÃO COMPLETA DE RESPONSABILIDADES**
   - ✅ Lógica **APENAS em Page Objects**
   - ✅ Testes contêm **APENAS orquestração** e assertions
   - ✅ Page Objects contêm **todos os locators e interações**
   - ❌ NUNCA código explícito (como `page.fill()`) dentro do teste

3. **test.step ESTRUTURADO**
   - Cada step contém **UMA ÚNICA responsabilidade**
   - Cada step chama **métodos de Page Objects**, nunca lógica direta
   - Format obrigatório: `'Given/When/Then/And [descrição em português]'`
   - Exemplos corretos:
     ```typescript
     await test.step('Given que acesso a página de login', async () => {
       await loginPage.navegarPara(url);
     });
     
     await test.step('When preencho e submeto as credenciais', async () => {
       await loginPage.submitLogin(email, senha);
     });
     
     await test.step('Then devo ver mensagem de sucesso', async () => {
       await loginPage.validarMensagemSucessoVisivel();
     });
     ```

4. **Support Files OBRIGATÓRIO**
   - ✅ `support/fixtures.ts` — setupTest(), teardownTest()
   - ✅ `support/helpers.ts` — Funções reutilizáveis
   - ✅ beforeEach/afterEach **SEMPRE** chamam functions do support
   - ❌ NUNCA duplicar setup/teardown em vários testes

5. **EXPECTS SEMPRE EM MÉTODOS DAS PAGES**
   - ✅ Método de validação na Page Object contém o `expect()`
   - ✅ test.step chama o método de validação
   - ❌ NUNCA `expect()` direto no test.step
   - ❌ NUNCA lógica ou assertions nos testes

6. **Page Objects Profissionais**
   - ✅ Seletores robustos (data-testid > ID > role > CSS)
   - ✅ Métodos compostos para operações comuns
   - ✅ Métodos de validação com `expect()` ou lógica de teste
   - ✅ Nenhum código de lógica de teste **nos testes** (.spec.ts)
   - ✅ TODOS os `expect()` e validações **dentro de Page Objects**
   - ❌ Nenhum `console.log()` ou debug code em produção

7. **SEMPRE IMPLEMENTAR FUNCIONALMENTE**
   - ✅ Criar arquivos de código EXECUTÁVEL
   - ✅ Fornecer comandos de execução específicos
   - ✅ Validar compilação TypeScript
   - ✅ Estrutura completa e pronta para rodar
   - ❌ Não fornecer APENAS orientações

8. **Massa de Dados**
   - ✅ Dados em `data/{funcionalidade}.data.json`
   - ✅ Importar no teste: `import dados from '../data/...'`
   - ✅ Usar dados: `await page.fillEmail(dados.usuario.email)`
   - ❌ NUNCA hardcoder valores nos testes

9. **Consistência com Projeto Existente**
   - ✅ Analisar testes já criados ANTES de implementar
   - ✅ Seguir mesmos padrões e convenções
   - ✅ Usar mesma estrutura de pastas
   - ✅ Compatibilidade com CI/CD existente

10. **Seletores Robustos - ORDEM DE PRIORIDADE**
   - 1️⃣ `[data-testid="elemento"]` — PREFERIDO
   - 2️⃣ `#id-unico` — ID único
   - 3️⃣ `getByRole('button', { name: 'Texto' })` — Acessibilidade
   - 4️⃣ `getByLabel('Label')` — Labels associados
   - 5️⃣ Seletores CSS **muito específicos** — Último recurso
   - ❌ XPath complexo — PROIBIDO
   - ❌ Classes genéricas — `.btn`, `.card` — PROIBIDO

11. **Esperas Dinâmicas - OBRIGATÓRIO**
    - ✅ `.waitFor({ state: 'visible' })`
    - ✅ `.waitForLoadState('networkidle')`
    - ✅ `expect().toBeVisible()`
    - ❌ `.waitForTimeout()` — PROIBIDO

---

## Entregáveis Profissionais

Para cada solicitação de automação, ENTREGAR COMPLETO:

1. ✅ **Page Objects** novo/atualizado em `pages/`
   - Métodos com responsabilidade única
   - Locators robustos (data-testid preferido)
   - Métodos compostos para operações comuns
   - TypeScript com tipos explícitos
   
2. ✅ **Testes .spec.ts** completo em `tests/`
   - Nomenclatura: `PBI-XX - Descrição` (describe) + `CT-XX - Descrição` (test)
   - BDD completo: Given/When/Then/And em português
   - Apenas chamadas de métodos de Page Objects
   - Assertions validando comportamento esperado
   - beforeEach/afterEach usando support
   
3. ✅ **Support Files** em `support/`
   - `fixtures.ts` com setupTest/teardownTest
   - `helpers.ts` com funções reutilizáveis
   - Evitar duplicação em múltiplos testes
   
4. ✅ **Massa de dados** em `data/{funcionalidade}.data.json`
   - Diferentes cenários: válido, inválido, edge cases
   - Valores realistas e relevantes
   
5. ✅ **Configuração** em `config/playwright.config.ts`
   - Já incluso, apenas manter atualizado
   
6. ✅ **Comandos de execução** específicos e testados
   - Exemplos: `npx playwright test` e variações
   - Validação antes de entregar
   
7. ✅ **TypeScript compilando** sem erros
   - `npx tsc --noEmit` antes de entrega

---

## Tecnologias Utilizadas

- **Playwright** (JavaScript/TypeScript)
- **Page Object Model** (POM)
- **Microsoft Playwright MCP**
- **TypeScript** (tipagem forte)
- **Estrutura modular** de testes
- **Seletores robustos** (data-testid, ID, CSS)
- **Sincronização automática** (auto-wait)

---

## Próximos Passos Após Implementação

1. **Validar Executabilidade**
   ```bash
  npx playwright test {{TESTS_DIR}}/{feature}.spec.ts
   npx playwright show-report
   ```

2. **Revisar Relatórios & Artefatos**
   - ✅ HTML report em `results/`
   - ✅ Screenshots de falhas em `results/`
   - ✅ Vídeos de falhas (se configurado) em `results/`

3. **Validar Conformidade com Padrões**
   - ✅ Nomenclatura segue PBI-XX e CT-XX
   - ✅ BDD completo em todos os steps
   - ✅ Page Objects sem lógica de teste
   - ✅ Suporte reutilizavél

4. **Integrar com CI/CD** (Se necessário)
   ```bash
   npx playwright test --reporter=junit
   ```

5. **Manter Testes Atualizados**
   - ✅ Atualizar quando UI muda
   - ✅ Adicionar casos de teste conforme novas features
   - ✅ Refatorar Page Objects se necessário

6. **Documentação**
   - ✅ Adicionar comments JSDoc em métodos complexos
   - ✅ Manter README.md do projeto atualizado
   - ✅ Documentar configurações especiais

---

## Stack Profissional

- **Playwright** — Automação moderna e multi-browser
- **TypeScript** — Tipagem forte e segurança
- **Page Object Model** — Padrão industrial profissional
- **BDD em Português** — Clareza e manutenibilidade
- **Fixtures Reutilizáveis** — DRY principle
- **Dados Externalizados** — Flexibilidade e manutenção
- **Relatórios Integrados** — HTML, tracing, screenshots, vídeos

---

## Conclusão

Este padrão segue as **melhores práticas profissionais** da indústria de automação de testes:
- ✅ Padrão BDD em português claro e executável
- ✅ Separação profissional de responsabilidades
- ✅ Código reutilizável e fácil de manter
- ✅ Escalável para centenas de testes
- ✅ Documentado via próprio código (self-documenting)
- ✅ Compatível com CI/CD empresarial

**Foco:** Criar testes **legíveis por QA**, **mantíveis por devs**, **confiáveis em produção**.

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar. NUNCA entregar scripts sem executá-los ao menos uma vez.**

**Comando de execução para este framework:**
```bash
cd automated_test/web
PBI_ID="PBI-XX" TC_ID="TC-YY" PROJECT_NAME="nome-projeto" npx playwright test tests/{funcionalidade}.spec.ts --reporter=list
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída completa + exit code via `run_in_terminal`
2. Exit code = 0 → ✅ SUCESSO — encerrar e apresentar resultado ao usuário
3. Exit code ≠ 0 → classificar erro pela saída:
   - **TypeScript compile error** → corrigir imports, tipos, interfaces no `.spec.ts` ou `.page.ts`
   - **Locator /Target closed** → revisar seletor no Page Object (prioridade: `data-testid` → `id` → `role`)
   - **Assertion failed (expect)** → ajustar valor esperado ou step de `Given` (pré-condição)
   - **TimeoutError** → adicionar `waitFor({ state: 'visible' })` ou `waitForLoadState('networkidle')`
   - **Module not found** → verificar caminhos de import relativos
4. Corrigir arquivo(s) problemático(s) → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico completo:
   - Resumo do que foi corrigido em cada ciclo
   - Erro remanescente com stack trace
   - Arquivo e linha do problema
   - Sugestão de próximo passo manual

---

**FOCO MÁXIMO: IMPLEMENTAÇÃO FUNCIONAL E PADRÃO PROFISSIONAL**
Não fornecer orientações — CRIAR CÓDIGO PROFISSIONAL EXECUTÁVEL
