---
name: "fastqa_4.1_create_automated_test_webdriverio_typescript_mobile"
description: "Criador de Testes Automatizados — WebdriverIO + TypeScript (Mobile)"

tools:
  - memory
  - sequential-thinking
  - appium-mcp
---

# Connector: WebdriverIO + TypeScript (Mobile)

## 🎯 Objetivo
Gerar scripts automatizados em **WebdriverIO + TypeScript** para testes mobile nativos e híbridos, usando o **Appium** como driver subjacente via `@wdio/appium-service`. O projeto segue configurações split (shared + android) e coleta automática de evidências (screenshot + gravação de tela).

---

## 🔰 Passo 0 — Verificar Ambiente Mobile (Obrigatório)

> **Antes de qualquer ação**, perguntar ao usuário:
>
> **"Você já possui o ambiente mobile configurado? (Appium, Android SDK, emulador/dispositivo)"**

**Se o usuário responder NÃO ou tiver dúvida**, exibir o guia abaixo e **aguardar confirmação** antes de prosseguir:

| # | Requisito | Verificação |
|---|---|---|
| 1 | JDK 17+ instalado | `java -version` |
| 2 | Android Studio + SDK instalado | Android SDK Manager |
| 3 | Variável `ANDROID_HOME` configurada | `echo %ANDROID_HOME%` |
| 4 | Node.js v22+ instalado | `node -v` |
| 5 | Appium 2.x instalado | `appium -v` |
| 6 | Emulador ou dispositivo físico conectado | `adb devices` |

Para instalar o WebdriverIO (executar dentro da pasta `automated_test/`):

```cmd
npm init wdio@latest .
npm install appium-mcp@latest
npx appium driver install uiautomator2
```

> 📖 Guia completo de pré-requisitos: `fastqa/agents/connectors/mobile/MOBILE_GUIDE.md`
> 📖 Guia WebdriverIO: `fastqa/agents/connectors/mobile/webdriverio/DEVELOPER_WEBDRIVERIO_GUIDE.md`

**Se o usuário confirmar que o ambiente está pronto**, prosseguir para o Passo 0.1 (verificação do Appium MCP).

**0.1 — Verificar Appium MCP (obrigatório para locators precisos):**

Verificar disponibilidade via `tool_search_tool_regex` com padrão `appium_get_page_source|appium_find_elements`:

- **Disponível** → registrar ferramentas; durante a geração de Screen Objects usar `appium_get_page_source` para obter a árvore XML da tela atual e `appium_find_elements` para confirmar os accessibility IDs reais — substituir todos os placeholders pelos valores inspecionados
- **Não disponível** → informar ao usuário:

> ⚠️ O servidor **appium-mcp** não está ativo. Para gerar locators precisos com base nos elementos reais do app:
> 1. Pressione `Ctrl+Shift+P` → "MCP: List Servers"
> 2. Localize **appium-mcp** e clique em **Start**
> 3. Confirme que o Appium Server está rodando (`appium --version`) e que há dispositivo/emulador conectado (`adb devices`)
>
> 📖 Configuração: `.vscode/mcp.json` (servidor `appium-mcp`)
>
> Deseja **continuar sem o MCP** (locators baseados nos test cases fornecidos) ou **aguardar ativação**?

**Aguardar resposta** antes de prosseguir.

---

**0.2 — Identificar Cenários (obrigatório quando múltiplos):**

Após receber o arquivo com os Test Cases, contar quantos `Scenario` / `it` / casos de teste existem:

- **1 cenário** → prosseguir diretamente
- **Mais de 1 cenário** → listar todos numerados e perguntar ao usuário:

> **"Encontrei [N] cenários no arquivo:**
> 1. [nome do cenário 1]
> 2. [nome do cenário 2]
> ...
>
> Deseja automatizar **todos** ou **cenários específicos**? (ex.: `1, 3` ou `todos`)"

**Aguardar resposta** antes de prosseguir. Usar a seleção do usuário para determinar quais `it()` blocos gerar no spec.

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` -> `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` -> `{{TESTS_DIR}}`
- `folder_structure.custom_paths.pages` -> `{{PAGES_DIR}}`
- `folder_structure.custom_paths.config` -> `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` (opcional) -> `{{RESULTS_DIR}}`

Fallback legado (se vazio):

> O subdiretório (`android/` ou `ios/`) é determinado por `platform.details.mobile_capabilities.platform_name` no `project_config.json`.

- `{{AUTOMATION_ROOT}} = automated_test/mobile`
- `{{TESTS_DIR}} = automated_test/mobile/android/tests` (ou `ios/tests` para iOS)
- `{{PAGES_DIR}} = automated_test/mobile/android/screen` (ou `ios/screen` para iOS)
- `{{CONFIG_DIR}} = automated_test/mobile/config`
- `{{RESULTS_DIR}} = automated_test/mobile/android/results` (ou `ios/results` para iOS)

Regra de precedência: esta seção prevalece sobre exemplos legados hardcoded eventualmente existentes no restante do documento.

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade informada pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo de teste: `{funcionalidade-kebab}.spec.ts`
> - Screen Object: `{funcionalidade-kebab}.screen.ts`
> - Componente Modal: `{componente-kebab}.modal.ts`
> - Arquivo de dados: `{funcionalidade-kebab}.data.json`
> - Exemplo: funcionalidade `"login usuario"` → `login-usuario.spec.ts`, `login-usuario.screen.ts`, `login-usuario.data.json`

```
{{AUTOMATION_ROOT}}/
├── android/
│   ├── components/
│   │   └── {componente-kebab}.modal.ts
│   ├── data/
│   │   └── {funcionalidade-kebab}.data.json
│   ├── results/
│   │   └── (evidências geradas automaticamente)
│   ├── screen/
│   │   └── {funcionalidade-kebab}.screen.ts
│   ├── support/
│   │   ├── utils.ts
│   │   └── jsonManager.ts
│   └── tests/
│       └── {funcionalidade-kebab}.spec.ts
├── app/
│   └── (colocar .apk aqui)
├── config/
│   ├── .env.stg
│   ├── .env.prod
│   ├── wdio.shared.conf.ts
│   └── wdio.android.conf.ts
├── package.json
└── tsconfig.json
```

---

## 🏗️ Scaffold Inicial (Obrigatório na primeira execução)

> **Antes de criar qualquer arquivo de teste**, verificar se a infraestrutura do projeto mobile já existe.

**Critério:** Verificar se `{{AUTOMATION_ROOT}}/config/wdio.shared.conf.ts` existe no workspace.

- **NÃO existe** → criar todos os arquivos da tabela abaixo usando os templates da seção seguinte
- **Já existe** → pular scaffold e ir direto para a criação do teste

> Após criar os arquivos de infraestrutura, executar: `cd {{AUTOMATION_ROOT}} && npm install && npx appium driver install uiautomator2`

### Arquivos de infraestrutura a criar:

| Arquivo | Template |
|---|---|
| `{{AUTOMATION_ROOT}}/package.json` | Seção `package.json` abaixo |
| `{{AUTOMATION_ROOT}}/tsconfig.json` | Seção `tsconfig.json` abaixo |
| `{{AUTOMATION_ROOT}}/config/wdio.shared.conf.ts` | Seção Config Compartilhada abaixo |
| `{{AUTOMATION_ROOT}}/config/wdio.android.conf.ts` | Seção Config Android abaixo |
| `{{AUTOMATION_ROOT}}/config/.env.stg` | Seção `.env.stg` abaixo |
| `{{AUTOMATION_ROOT}}/config/.env.prod` | Seção `.env.prod` abaixo |
| `{{AUTOMATION_ROOT}}/android/support/utils.ts` | Seção Utilitários abaixo |
| `{{AUTOMATION_ROOT}}/android/support/jsonManager.ts` | Seção Gerenciador de Evidências abaixo |
| `{{AUTOMATION_ROOT}}/android/components/README.md` | `# components\nComponentes reutilizáveis de UI (modais, dialogs).` |
| `{{AUTOMATION_ROOT}}/android/data/README.md` | `# data\nArquivos de dados de teste (JSON).` |
| `{{AUTOMATION_ROOT}}/android/results/README.md` | `# results\nEvidências geradas automaticamente (screenshots, vídeos, JSONs).` |
| `{{AUTOMATION_ROOT}}/app/README.md` | `# app\nColocar o APK aqui para execução local.` |

---

## 📝 Templates

### Config Compartilhada (`config/wdio.shared.conf.ts`)

> Config base reutilizável por todas as plataformas (Android, iOS futuro). Contém timeouts, framework, reporters e hooks genéricos.

```typescript
import type { Options } from '@wdio/types';

export const config: Partial<Options.Testrunner> = {
  runner: 'local',
  maxInstances: 1,
  logLevel: 'error',
  bail: 0,
  waitforTimeout: 30000,
  connectionRetryTimeout: 150000,
  connectionRetryCount: 3,
  framework: 'mocha',
  reporters: ['spec'],
  mochaOpts: {
    ui: 'bdd',
    timeout: 300000,
  },
};
```

### Config Android (`config/wdio.android.conf.ts`)

> **📌 REGRA:** Antes de gerar, ler `fastqa/scripts/project_config.json` → `platform.details.mobile_capabilities` e usar os valores configurados. Se `mobile_capabilities` estiver vazio, usar os valores default indicados nos comentários.

```typescript
import { config as sharedConfig } from './wdio.shared.conf.js';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import dotenv from 'dotenv';
import type { Options } from '@wdio/types';

// ── Carregar variáveis de ambiente por --TEST_ENV=stg|prod ──
const testEnv = process.argv.find(arg => arg.startsWith('--TEST_ENV='))?.split('=')[1] || 'stg';
const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, `.env.${testEnv}`) });

declare global {
  var evidenceDir: string;
}

export const config: Options.Testrunner = {
  ...sharedConfig,

  port: 4723,
  specs: [join(__dirname, '../android/tests/**/*.spec.ts')],

  capabilities: [{
    platformName: '{{MOBILE_PLATFORM_NAME}}',                        // default: 'Android'
    'appium:deviceName': '{{MOBILE_DEVICE_NAME}}',                   // default: 'emulator-5554'
    'appium:automationName': '{{MOBILE_AUTOMATION_NAME}}',           // default: 'UiAutomator2'
    'appium:app': join(__dirname, '../app/{{MOBILE_APP_FILE}}'),      // default: 'app.apk'
    'appium:appPackage': '{{MOBILE_APP_PACKAGE}}',                   // Android-only (comentar se vazio)
    'appium:appActivity': '{{MOBILE_APP_ACTIVITY}}',                 // Android-only (comentar se vazio)
    'appium:appWaitActivity': '*',
    'appium:autoGrantPermissions': {{MOBILE_AUTO_GRANT_PERMISSIONS}}, // default: true
    'appium:noReset': true,
    // iOS-only (remover bloco acima e descomentar):
    // 'appium:bundleId': '{{MOBILE_BUNDLE_ID}}',
  }],

  services: [['appium', {
    command: 'appium',
  }]],

  // ── Hooks de Evidência ──

  beforeTest: async function (test) {
    // Limpar e reativar o app antes de cada teste
    try {
      await driver.terminateApp('{{MOBILE_APP_PACKAGE}}');
    } catch (_) { /* app pode não estar rodando */ }
    await driver.activateApp('{{MOBILE_APP_PACKAGE}}');

    // Criar pasta de evidências para este teste
    const safeName = `${test.parent} - ${test.title}`.replace(/[<>:"/\\|?*]/g, '_');
    const evidenceDir = join(__dirname, `../android/results/${safeName}`);
    if (!existsSync(evidenceDir)) {
      mkdirSync(evidenceDir, { recursive: true });
    }
    global.evidenceDir = evidenceDir;

    // Iniciar gravação de tela
    await driver.startRecordingScreen();
  },

  afterTest: async function (test, context, { error, passed }) {
    try {
      // Parar gravação e salvar vídeo
      const video = await driver.stopRecordingScreen();
      const videoPath = join(global.evidenceDir, 'recording.mp4');
      writeFileSync(videoPath, video, 'base64');

      // Capturar screenshot final
      const screenshot = await driver.takeScreenshot();
      const status = passed ? 'PASSED' : 'FAILED';
      const screenshotPath = join(global.evidenceDir, `${status}_screenshot.png`);
      writeFileSync(screenshotPath, screenshot, 'base64');

      // Encerrar app
      await driver.terminateApp('{{MOBILE_APP_PACKAGE}}');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.error('Erro ao coletar evidências:', msg);
    }
  },
};
```

### Variáveis de Ambiente (`config/.env.stg`)
```env
# Variáveis de ambiente — Staging
USER_EMAIL=usuario@teste.com
USER_SENHA=senha123
```

### Variáveis de Ambiente (`config/.env.prod`)
```env
# Variáveis de ambiente — Produção
USER_EMAIL=
USER_SENHA=
```

### Screen Object (`android/screen/{funcionalidade-kebab}.screen.ts`)

> **🔍 Se appium-mcp ativo:** Antes de fixar os locators, usar `appium_get_page_source` para obter a árvore XML da tela atual e `appium_find_elements` para validar os accessibility IDs reais. Substituir todos os `~placeholder` pelos valores inspecionados do app em execução.

> **Padrão:** Classe com **getters** para seletores (`$('~accessibilityId')`), métodos de ação com `waitForDisplayed`, e export como **singleton** (`export default new Classe()`).

```typescript
class LoginScreen {
  // ── Seletores (accessibility id) ──
  get inputEmail()    { return $('~inputEmail'); }
  get inputSenha()    { return $('~inputSenha'); }
  get btnEntrar()     { return $('~btnEntrar'); }
  get msgBemVindo()   { return $('~msgBemVindo'); }

  // ── Ações ──
  async preencherEmail(email: string): Promise<void> {
    await this.inputEmail.waitForDisplayed();
    await this.inputEmail.setValue(email);
  }

  async preencherSenha(senha: string): Promise<void> {
    await this.inputSenha.waitForDisplayed();
    await this.inputSenha.setValue(senha);
  }

  async clicarEntrar(): Promise<void> {
    await this.btnEntrar.waitForDisplayed();
    await this.btnEntrar.click();
  }

  async aguardarTelaPrincipal(): Promise<void> {
    await this.msgBemVindo.waitForDisplayed();
  }
}

export default new LoginScreen();
```

### Componente Modal (`android/components/{componente-kebab}.modal.ts`)

> **Padrão:** Componentes reutilizáveis de UI (modais, dialogs, bottom sheets) com getters + singleton.

```typescript
class PreferenciasModal {
  get btnFechar()   { return $('~btnFecharModal'); }
  get titulo()      { return $('~tituloModal'); }

  async fechar(): Promise<void> {
    await this.btnFechar.waitForDisplayed();
    await this.btnFechar.click();
  }

  async aguardarExibicao(): Promise<void> {
    await this.titulo.waitForDisplayed();
  }
}

export default new PreferenciasModal();
```

### Spec File (`android/tests/{funcionalidade-kebab}.spec.ts`)

```typescript
import loginScreen from '../screen/login.screen.js';
import testData from '../data/login.data.json' with { type: 'json' };

describe('{{FEATURE_NAME}}', () => {
  it('{{SCENARIO_NAME}}', async () => {
    await loginScreen.preencherEmail(testData.email);
    await loginScreen.preencherSenha(testData.senha);
    await loginScreen.clicarEntrar();
    await loginScreen.aguardarTelaPrincipal();

    await expect(loginScreen.msgBemVindo).toBeDisplayed();
  });
});
```

### Arquivo de Dados (`android/data/{funcionalidade-kebab}.data.json`)

```json
{
  "email": "usuario@teste.com",
  "senha": "senha123"
}
```

### Utilitários (`android/support/utils.ts`)

```typescript
/**
 * Encerra o app e o reativa (útil para limpar estado entre testes).
 */
export async function reiniciarApp(appPackage: string): Promise<void> {
  await driver.terminateApp(appPackage);
  await driver.activateApp(appPackage);
}

/**
 * Obtém o content-desc (accessibility id) de um elemento.
 */
export async function obterContentDesc(selector: string): Promise<string | null> {
  const element = await $(selector);
  return element.getAttribute('content-desc');
}

/**
 * Aguarda um elemento ficar visível com timeout customizado.
 */
export async function aguardarElemento(selector: string, timeout = 15000): Promise<WebdriverIO.Element> {
  const element = await $(selector);
  await element.waitForDisplayed({ timeout });
  return element;
}

/**
 * Realiza swipe vertical para cima.
 */
export async function swipeUp(): Promise<void> {
  const { width, height } = await driver.getWindowSize();
  await driver.action('pointer')
    .move({ duration: 0, x: width / 2, y: height * 0.8 })
    .down({ button: 0 })
    .move({ duration: 1000, x: width / 2, y: height * 0.2 })
    .up({ button: 0 })
    .perform();
}
```

### Gerenciador de Evidências (`android/support/jsonManager.ts`)

```typescript
import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

interface Evidencia {
  teste: string;
  status: string;
  dataExecucao: string;
  [key: string]: unknown;
}

/**
 * Cria um JSON de evidência com metadados do teste.
 */
export function criarEvidencia(
  dir: string,
  testName: string,
  status: string,
  dados: Record<string, unknown> = {},
): string {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  const evidencia: Evidencia = {
    teste: testName,
    status,
    dataExecucao: new Date().toISOString(),
    ...dados,
  };

  const filePath = join(dir, 'evidencia.json');
  writeFileSync(filePath, JSON.stringify(evidencia, null, 2), 'utf-8');
  return filePath;
}
```

### `tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "declaration": false,
    "outDir": "./dist",
    "types": ["node", "@wdio/globals/types", "@wdio/mocha-framework"]
  },
  "include": ["android/**/*.ts", "config/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

### `package.json`

> **📌 Importante:** Este `package.json` fica na raiz `{{AUTOMATION_ROOT}}/`.

```json
{
  "name": "fastqa-webdriverio-typescript-mobile",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test:android": "npx wdio run config/wdio.android.conf.ts --TEST_ENV=stg",
    "test:android:prod": "npx wdio run config/wdio.android.conf.ts --TEST_ENV=prod",
    "test:android:grep": "npx wdio run config/wdio.android.conf.ts --TEST_ENV=stg --mochaOpts.grep",
    "test:android:spec": "npx wdio run config/wdio.android.conf.ts --TEST_ENV=stg --spec"
  },
  "devDependencies": {
    "@wdio/appium-service": "^9.20.0",
    "@wdio/cli": "^9.20.0",
    "@wdio/globals": "^9.20.0",
    "@wdio/local-runner": "^9.20.0",
    "@wdio/mocha-framework": "^9.20.0",
    "@wdio/spec-reporter": "^9.20.0",
    "@wdio/types": "^9.20.0",
    "appium-uiautomator2-driver": "^3.9.6",
    "dotenv": "^16.4.7",
    "ts-node": "^10.9.2",
    "typescript": "^5.7.3",
    "webdriverio": "^9.20.0"
  }
}
```

---

## 📋 Pré-requisitos
- Node.js v22+
- Appium Server 2.x (gerenciado automaticamente pelo `@wdio/appium-service`)
- Android SDK com platform-tools e emulador configurado
- AVD criado (ex: `Pixel_7_API_35`) ou dispositivo físico conectado via USB/Wi-Fi

## 🔧 Comandos de Execução
```bash
cd {{AUTOMATION_ROOT}} && npm install
cd {{AUTOMATION_ROOT}} && npx appium driver install uiautomator2
cd {{AUTOMATION_ROOT}} && npm run test:android
```

### Comandos Avançados
```bash
# Rodar teste específico por arquivo
cd {{AUTOMATION_ROOT}} && npm run test:android:spec -- android/tests/{funcionalidade-kebab}.spec.ts

# Rodar testes por grep (nome do describe/it)
cd {{AUTOMATION_ROOT}} && npm run test:android:grep -- "login"

# Rodar em ambiente de produção
cd {{AUTOMATION_ROOT}} && npm run test:android:prod
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
cd {{AUTOMATION_ROOT}} && npx wdio run config/wdio.android.conf.ts --TEST_ENV=stg --spec android/tests/{funcionalidade-kebab}.spec.ts
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída completa + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **SessionNotCreatedError** → verificar Appium Server rodando, `deviceName` e capabilities
   - **NoSuchElementError** → revisar locator `~accessibility-id` no Screen Object
   - **AssertionError** → ajustar valor esperado ou aguardar elemento aparecer
   - **Timeout** → aumentar `waitForDisplayed` ou ajustar sincronização
   - **TSError** → verificar tipos, imports e `tsconfig.json`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
