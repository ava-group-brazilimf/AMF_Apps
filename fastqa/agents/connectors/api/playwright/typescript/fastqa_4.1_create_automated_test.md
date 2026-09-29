---
name: "fastqa_4.1_create_automated_test_playwright_typescript_api"
description: "Criador de Testes Automatizados — Playwright + TypeScript (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Playwright + TypeScript (API)

## 🎯 Objetivo
Gerar testes automatizados de API REST em **Playwright + TypeScript** usando `APIRequestContext`.

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
> - Teste: `{funcionalidade}.api.spec.ts`
> - Client: `{FuncionalidadePascalCase}Client.ts`
> - Dados: `{funcionalidade}.data.json`
> - Exemplo: `"autenticacao"` → `autenticacao.api.spec.ts`, `AutenticacaoClient.ts`

```
{{AUTOMATION_ROOT}}/
├── config/
│   ├── playwright.config.ts
│   ├── .env.dev
│   └── .env.test
├── clients/
│   └── {FuncionalidadePascalCase}Client.ts
├── schemas/
│   └── {funcionalidade}.schema.json
├── support/
│   ├── api-fixtures.ts
│   └── api-helpers.ts
├── data/
│   └── {funcionalidade}.data.json
├── tests/
│   └── {funcionalidade}.api.spec.ts
└── results/
```

---

## 📝 Templates

### Spec File (`{funcionalidade}.api.spec.ts`)
```typescript
import { test, expect } from '@playwright/test';
import { AutenticacaoClient } from '../clients/AutenticacaoClient';
import testData from '../data/autenticacao.data.json';

test.describe('PBI-XX - Autenticação API', () => {
  let client: AutenticacaoClient;

  test.beforeEach(async ({ request }) => {
    client = new AutenticacaoClient(request);
  });

  test('CT-XX - Login com credenciais válidas retorna token', async () => {
    await test.step('Given payload de login válido', async () => {});

    await test.step('When POST /auth/login', async () => {
      const response = await client.login(testData.validUser);
      await test.step('Then status 200', async () => {
        expect(response.status()).toBe(200);
      });
      await test.step('And body contém token', async () => {
        const body = await response.json();
        expect(body).toHaveProperty('token');
        expect(body.token).toBeTruthy();
      });
    });
  });

  test('CT-XX - Login com credenciais inválidas retorna 401', async () => {
    await test.step('Given payload de login inválido', async () => {});

    await test.step('When POST /auth/login com credenciais erradas', async () => {
      const response = await client.login(testData.invalidUser);
      await test.step('Then status 401', async () => {
        expect(response.status()).toBe(401);
      });
      await test.step('And body contém mensagem de erro', async () => {
        const body = await response.json();
        expect(body).toHaveProperty('error');
      });
    });
  });
});
```

### API Client (`{FuncionalidadePascalCase}Client.ts`)
```typescript
import { APIRequestContext, APIResponse } from '@playwright/test';

export class AutenticacaoClient {
  constructor(private readonly request: APIRequestContext) {}

  async login(credentials: { email: string; password: string }): Promise<APIResponse> {
    return await this.request.post('/auth/login', {
      data: credentials,
    });
  }

  async logout(token: string): Promise<APIResponse> {
    return await this.request.post('/auth/logout', {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  async getProfile(token: string): Promise<APIResponse> {
    return await this.request.get('/auth/profile', {
      headers: { Authorization: `Bearer ${token}` },
    });
  }
}
```

### Data File (`{funcionalidade}.data.json`)
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

### API Fixtures (`support/api-fixtures.ts`)
```typescript
import { test as base, APIRequestContext } from '@playwright/test';

type ApiFixtures = {
  authenticatedRequest: APIRequestContext;
  authToken: string;
};

export const test = base.extend<ApiFixtures>({
  authToken: async ({ request }, use) => {
    const response = await request.post('/auth/login', {
      data: { email: process.env.TEST_EMAIL, password: process.env.TEST_PASSWORD },
    });
    const body = await response.json();
    await use(body.token);
  },
  authenticatedRequest: async ({ playwright, authToken }, use) => {
    const context = await playwright.request.newContext({
      baseURL: process.env.BASE_URL,
      extraHTTPHeaders: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
    });
    await use(context);
    await context.dispose();
  },
});

export { expect } from '@playwright/test';
```

### API Helpers (`support/api-helpers.ts`)
```typescript
import { APIResponse } from '@playwright/test';

export async function assertStatusCode(response: APIResponse, expected: number) {
  if (response.status() !== expected) {
    const body = await response.text();
    throw new Error(
      `Esperado status ${expected}, recebido ${response.status()}.\nBody: ${body}`
    );
  }
}

export async function assertBodyHasProperty(response: APIResponse, property: string) {
  const body = await response.json();
  if (!(property in body)) {
    throw new Error(
      `Propriedade "${property}" não encontrada no body: ${JSON.stringify(body)}`
    );
  }
  return body[property];
}

export async function assertResponseTime(response: APIResponse, maxMs: number) {
  // Playwright não expõe timing diretamente no APIResponse
  // Use request interception ou medir externamente
}
```

### Playwright Config (`config/playwright.config.ts`)
```typescript
import { defineConfig } from '@playwright/test';
import * as dotenv from 'dotenv';
import path from 'path';

const environment = process.env.ENVIRONMENT || 'dev';
dotenv.config({ path: path.resolve(__dirname, `.env.${environment}`) });

export default defineConfig({
  testDir: '../tests',
  outputDir: '../results',
  timeout: 30000,
  reporter: [
    ['html', { outputFolder: '../results/playwright-report', open: 'never' }],
    ['json', { outputFile: '../results/test-results.json' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL,
    extraHTTPHeaders: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  },
});
```

---

## 📋 Pré-requisitos
- Node.js v22+
- `npm install -D @playwright/test dotenv`

## 🔧 Instalação
```bash
npm install -D @playwright/test dotenv
```

## 🚀 Comandos de Execução
```bash
npx playwright test tests/                              # Todos os testes
npx playwright test tests/{funcionalidade}.api.spec.ts  # Específico
npx playwright show-report results/playwright-report    # Ver relatório
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
npx playwright test tests/{funcionalidade}.api.spec.ts --reporter=list
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ECONNREFUSED** → API não está no ar ou `BASE_URL` incorreto
   - **expect(received).toBe(expected)** → status code diferente do esperado; revisar endpoint/payload
   - **Cannot read properties of undefined** → campo ausente no response body
   - **Import error** → verificar paths dos `clients/` e `support/`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
