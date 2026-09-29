# Guia de Pré-requisitos Mobile (Windows)

---

## Step 1 — Instalar o JDK (Java Development Kit)

1. Acesse https://www.oracle.com/java/technologies/downloads/
2. Baixe e instale o JDK 17+ para Windows
3. Configure a variável de ambiente `JAVA_HOME`:
   1. Abra **Configurações do Sistema** → **Variáveis de Ambiente**
   2. Crie a variável `JAVA_HOME` com o caminho da instalação (ex.: `C:\Program Files\Java\jdk-17`)
   3. Adicione `%JAVA_HOME%\bin` ao `Path`
4. Valide:
   ```cmd
   java -version
   echo %JAVA_HOME%
   ```

---

## Step 2 — Instalar o Android Studio e o Android SDK

1. Acesse https://developer.android.com/studio e baixe o Android Studio
2. Execute o instalador e siga o wizard (marque **Android SDK** e **Android Virtual Device**)
3. Após instalar, abra o Android Studio → **Settings** → **Languages & Frameworks** → **Android SDK**
4. Na aba **SDK Platforms**, instale a versão do Android desejada (ex.: Android 14)
5. Na aba **SDK Tools**, marque e instale:
   - Android SDK Build-Tools
   - Android SDK Command-line Tools
   - Android SDK Platform-Tools
   - Android Emulator
   - Android Emulator hypervisor driver (installer)
   - Google USB Driver
   - Google Web Driver
   - Intel x86 Emulator Accelerator (HAXM installer)
6. Configure as variáveis de ambiente:
   1. Crie `ANDROID_HOME` → `C:\Users\<user>\AppData\Local\Android\Sdk`
   2. Adicione ao `Path`:
      - `%ANDROID_HOME%\platform-tools`
      - `%ANDROID_HOME%\emulator`
      - `%ANDROID_HOME%\cmdline-tools\latest\bin`
7. Valide:
   ```cmd
   adb version
   emulator -list-avds
   ```

---

## Step 3 — Instalar o Node.js e npm

1. Acesse https://nodejs.org/ e baixe a versão LTS
2. Execute o instalador (npm é incluído automaticamente)
3. Valide:
   ```cmd
   node -v
   npm -v
   ```

---

## Step 4 — Instalar o Appium Server

1. Instale globalmente:
   ```cmd
   npm install -g appium@latest
   ```
2. Instale o driver de automação:
   ```cmd
   appium driver install uiautomator2
   ```
3. Valide:
   ```cmd
   appium --version
   appium driver list --installed
   ```
4. Inicie o servidor (porta padrão `4723`):
   ```cmd
   appium
   ```

---

## Step 5 — Validar o Ambiente com Appium Doctor

1. Instale:
   ```cmd
   npm install -g appium-doctor
   ```
2. Execute:
   ```cmd
   appium-doctor --android
   ```
3. Verifique a saída — corrija **todos** os itens marcados como ❌ antes de prosseguir

---

## Step 6 — Instalar o Appium Inspector

1. Acesse https://github.com/appium/appium-inspector/releases
2. Baixe o instalador `.exe` e instale
3. Abra o Appium Inspector e configure a conexão:
   - **Remote Host:** `127.0.0.1`
   - **Remote Port:** `4723`
   - **Remote Path:** `/`
4. Preencha as capabilities JSON para iniciar uma sessão:
   ```json
   {
     "platformName": "Android",
     "appium:deviceName": "emulator-5554",
     "appium:automationName": "UiAutomator2",
     "appium:autoGrantPermissions": true,
     "appium:APP_PACKAGE": "com.example.app",
     "appium:APP_ACTIVITY": ".MainActivity",
     "appium:app": "C:\\caminho\\do\\app.apk"
   }
   ```
5. Clique em **Start Session** para inspecionar os elementos da aplicação

---

## Step 7 — Configurar o Emulador Android

### Opção A — Via Android Studio

1. Abra o Android Studio → **Device Manager** (ícone de celular na barra lateral)
2. Clique em **Create Virtual Device**
3. Selecione o hardware (ex.: Pixel 7)
4. Selecione a imagem do sistema (ex.: Android 14 — API 34)
5. Dê um nome ao AVD e clique em **Finish**
6. Clique em ▶ para iniciar

### Opção B — Via linha de comando

```cmd
emulator -list-avds
emulator -avd nome-do-emulador
adb devices
```

### Dispositivo físico (alternativa)

1. No aparelho Android, acesse **Configurações** → **Sobre o telefone**
2. Toque 7 vezes em **Número da versão** para ativar as opções de desenvolvedor
3. Volte em **Configurações** → **Opções do desenvolvedor**
4. Ative **Depuração USB**
5. Conecte o cabo USB e aceite a permissão de depuração no aparelho
6. Valide:
   ```cmd
   adb devices
   ```
   O dispositivo deve aparecer como `device` (não `unauthorized`)
   ```bash
   adb devices
   ```
