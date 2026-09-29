# Guia do Desenvolvedor — WebdriverIO + Appium (Mobile)

## 1. Arquitetura do Projeto

```
├── mobile/
│   ├── android/
│   │   ├── components/
│   │   ├── data/
│   │   ├── results/
│   │   ├── screen/
│   │   ├── support/
│   │   └── tests/
│   ├── app/
│   └── config/
│       ├── env/
│       ├── wdio.android.conf.js
│       └── wdio.shared.conf.js
├── package.json
├── .gitignore
└── README.md
```

---

## 2. Instalação das Dependências

Execute dentro da pasta `automated_test`:

```cmd
npm init wdio@latest .
```

Durante o assistente interativo, selecione as seguintes opções:

| Pergunta | Resposta |
|---|---|
| A project named "..." was detected, correct? | **Yes** |
| What type of testing would you like to do? | **E2E Testing - of Web or Mobile Applications** |
| Where is your automation backend located? | **On my local machine** |
| Which environment you would like to automate? | **Mobile - native, hybrid and mobile web apps, on Android or iOS** |
| Which mobile environment you'd like to automate? | **Android** (using UiAutomator2) |
| Which framework do you want to use? | **Mocha** |
| Do you want to use Typescript to write tests? | **No** |
| Do you want WebdriverIO to autogenerate some test files? | **No** |
| Which reporter do you want to use? | **spec, json** |
| Do you want to add a plugin to your test setup? | *(nenhum — pressionar Enter)* |
| Would you like to include Visual Testing? | **No** |
| Do you want to add a service to your test setup? | **appium** |
| Do you want me to run `npm install`? | **Yes** |

Após o assistente finalizar, instale o MCP do Appium e o driver Android:

```cmd
npm install appium-mcp@latest
npx appium driver install uiautomator2
```

---

## 3. Configuração de Capabilities (Android)

No arquivo `wdio.android.conf.js` (ou `wdio.conf.ts`), configure as capabilities obrigatórias:

```js
capabilities: [{
    platformName: 'Android',
    'appium:deviceName': 'emulator-5554',
    'appium:automationName': 'UiAutomator2',
    'appium:autoGrantPermissions': true,
    'appium:APP_PACKAGE': 'com.example.app',
    'appium:APP_ACTIVITY': '.MainActivity',
    'appium:app': path.join(process.cwd(), 'app/app.apk'),
}]
```

| Capability | Descrição |
|------------|-----------|
| `platformName` | Plataforma do dispositivo (`Android`) |
| `appium:deviceName` | Nome do dispositivo ou emulador |
| `appium:automationName` | Engine de automação (`UiAutomator2`) |
| `appium:autoGrantPermissions` | Concede permissões automaticamente ao app |
| `appium:APP_PACKAGE` | Package do app Android |
| `appium:APP_ACTIVITY` | Activity principal do app |
| `appium:app` | Caminho absoluto do APK |

---

## 4. Mapeamento de Elementos

### Seletores disponíveis

- **Accessibility ID** (preferido):
    ```js
    const element = await $('~elementId');
    ```
- **Resource ID:**
    ```js
    const element = await $('android=new UiSelector().resourceId("com.example:id/button")');
    ```
- **Classe:**
    ```js
    const element = await $('android=new UiSelector().className("android.widget.Button")');
    ```
- **Texto:**
    ```js
    const element = await $('android=new UiSelector().text("Entrar")');
    ```
- **XPath** (evitar quando possível):
    ```js
    const element = await $('//android.widget.TextView[@text="Entrar"]');
    ```

### Ferramentas de mapeamento

- **Appium Inspector** — interface visual para inspecionar elementos
- **UIAutomatorViewer** — incluso no Android SDK

### Boas práticas

- Prefira `accessibility id` sempre que possível
- Evite XPath longos
- Centralize seletores em arquivos de screen/page objects

---

## 5. Configuração Compartilhada (`wdio.shared.conf.js`)

O `wdio.shared.conf.js` centraliza configurações comuns entre Android e iOS:

```js
const path = require('path');

exports.config = {
    runner: 'local',
    framework: 'mocha',
    mochaOpts: { timeout: 60000 },
    reporters: ['spec'],
    services: ['appium'],
    waitforTimeout: 10000,
    connectionRetryTimeout: 90000,
    connectionRetryCount: 3,
    logLevel: 'info',
};
```

O `wdio.android.conf.js` herda do shared e adiciona as capabilities Android:

```js
const path = require('path');
const { config } = require('./wdio.shared.conf');

exports.config = {
    ...config,
    specs: ['../android/tests/**/*.js'],
    capabilities: [{
        platformName: 'Android',
        'appium:deviceName': 'emulator-5554',
        'appium:automationName': 'UiAutomator2',
        'appium:autoGrantPermissions': true,
        'appium:APP_PACKAGE': 'com.example.app',
        'appium:APP_ACTIVITY': '.MainActivity',
        'appium:app': path.join(process.cwd(), 'app/app.apk'),
    }],
};
```

---

## 6. Execução dos Testes

### Iniciar o Appium Server

```cmd
appium
```

> Se estiver usando `@wdio/appium-service`, o servidor é iniciado automaticamente ao rodar os testes.

### Iniciar o emulador

```cmd
emulator -list-avds
emulator -avd nome-do-emulador
```

### Executar testes

```cmd
npx wdio run wdio.conf.js
npx wdio run mobile/config/wdio.android.conf.js
npm run test:android
npm run test:android:debug
```

---

## 7. Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `SessionNotCreatedError` | Appium Server não está rodando ou capabilities incorretas | Verifique se o Appium está ativo (`appium`) e se `deviceName` corresponde a `adb devices` |
| `Could not find a connected Android device` | Emulador não iniciado ou USB não autorizado | Execute `adb devices` e confirme que o dispositivo aparece como `device` |
| `App not found` | Caminho do APK inválido | Verifique se o caminho em `appium:app` é absoluto e o arquivo existe |
| `ECONNREFUSED 127.0.0.1:4723` | Appium Server não está rodando na porta esperada | Inicie com `appium` ou configure `@wdio/appium-service` |
| `Element not found` | Seletor incorreto ou tela não carregou | Use Appium Inspector para validar o seletor e aumente o `waitforTimeout` |
| `Permission denied` | App não tem permissões necessárias | Confirme `appium:autoGrantPermissions: true` nas capabilities |

---

## 8. Referências

- [Documentação WebdriverIO](https://webdriver.io/docs/gettingstarted)
- [WebdriverIO Appium Service](https://webdriver.io/docs/appium-service)
- [Appium](https://appium.io/)
- [Mocha](https://mochajs.org/)
