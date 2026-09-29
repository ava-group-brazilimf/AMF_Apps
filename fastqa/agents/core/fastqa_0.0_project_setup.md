---
name: "fastqa_0.0_project_setup"
description: "Wizard interativo de configuração do projeto FastQA via chat"

tools:
  - memory
  - sequential-thinking
---

# FastQA Agent — Setup do Projeto (@fastqa:setup_project)

## 🎯 Objetivo
Configurar o projeto FastQA coletando preferências do usuário e gerando a estrutura de pastas + arquivo de persistência.

---

## 📋 Fluxo de Perguntas (Sequencial)

### Pergunta 1 — Análise de Requisitos
> **Qual o propósito/objetivo da aplicação que será testada?**
> (Descreva brevemente o que a aplicação faz)
> ⚠️ **SALVAR EM:** `analysis.purpose` e `analysis.application_description`

### Pergunta 2 — Gestão de Projeto
> **Existe projeto em alguma ferramenta de gestão?**
> - [1] Azure DevOps
> - [2] Jira
> - [3] Nenhuma
>
> Se **Azure DevOps**: solicitar Org URL, Projeto e PAT
> Se **Jira**: solicitar URL e Project Key
> ⚠️ **SALVAR EM:** `project_management.tool`, `project_management.azure_devops.*`, `project_management.jira.*`

### Pergunta 3 — Plataforma
> **Qual a plataforma que está testando?**
> - [1] Web
> - [2] Mobile  
> - [3] API
> - [4] Desktop
> ⚠️ **SALVAR EM:** `platform.type` (lowercase: web, mobile, api, desktop)

### Pergunta 3.1 — Capabilities Mobile (Condicional — apenas se Plataforma = Mobile)
> Após selecionar a plataforma (Android/iOS), o usuário escolhe se quer configurar as capabilities agora ou depois.
> Se escolher **"Não, configurar depois"**, as capabilities ficam vazias e podem ser editadas em `project_config.json`.
>
> **3.1a — Plataforma Mobile (obrigatória):** Android ou iOS?
> - [1] Android
> - [2] iOS
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.platform_name`
> ⚠️ Define automaticamente `automation_name`: `UiAutomator2` (Android) ou `XCUITest` (iOS)
>
> **3.1b — Configurar capabilities agora? (obrigatória)**
> - [1] Sim, configurar agora
> - [2] Não, configurar depois
> Se `Não`, pular para a próxima pergunta.
>
> **3.1c — Nome do Dispositivo (opcional):**
> Ex.: `emulator-5554`, `Pixel 7`, `iPhone 15`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.device_name`
>
> **3.1d — Auto Grant Permissions (opcional, apenas Android):**
> Conceder permissões automaticamente ao app?
> - [S] Sim → `true`
> - [N] Não → `false`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.auto_grant_permissions`
>
> **3.1d — Versão da Plataforma (opcional, apenas iOS):**
> Ex.: `17.2`, `16.4`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.platform_version`
>
> **3.1e — Caminho do App (opcional):**
> Caminho do APK (Android) ou IPA (iOS). Ex.: `apps/app.apk`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.app_path`
>
> **3.1f — APP_PACKAGE (opcional, apenas Android):**
> Package do app. Ex.: `com.example.app`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.app_package`
>
> **3.1g — APP_ACTIVITY (opcional, apenas Android):**
> Activity principal. Ex.: `.MainActivity`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.app_activity`
>
> **3.1f — Bundle ID (opcional, apenas iOS):**
> Bundle ID do app. Ex.: `com.example.app`
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.bundle_id`
>
> **3.1h — Appium Server URL (opcional):**
> URL do servidor Appium (padrão: `http://localhost:4723`)
> ⚠️ **SALVAR EM:** `platform.details.mobile_capabilities.appium_server_url`

### Pergunta 4 — Abordagem BDD
> **Utilizam Gherkin (BDD)?**
> - [S] Sim
> - [N] Não

### Pergunta 5 — Conector de SAÍDA (framework + linguagem)
> **Qual o framework de automação?**
> *(Opções filtradas pela plataforma escolhida na Pergunta 3)*
>
> | Plataforma | Frameworks Disponíveis |
> |------------|----------------------|
> | Web | Playwright, Cypress, Selenium, Robot |
> | Mobile | WebdriverIO, Selenium, Robot |
> | API | Playwright, RestAssured, Supertest, Requests, Karate, Postman, Robot |
> | Desktop | Playwright, Selenium, Robot |
>
> **Qual a linguagem de automação?**
> *(Opções filtradas pelo framework escolhido)*
>
> | Framework | Linguagens Disponíveis |
> |-----------|----------------------|
> | Playwright | TypeScript, JavaScript, Python, Java, C# |
> | Cypress | TypeScript, JavaScript |
> | Robot | Python |
> | Selenium | Python, Java, C#, JavaScript, TypeScript |
> | WebdriverIO | TypeScript, JavaScript |
> | RestAssured | Java |
> | Supertest | TypeScript, JavaScript |
> | Requests | Python |
> | Karate | Java |
> | Postman | JavaScript |

### Pergunta 6 — Conector de ENTRADA (input)
> **Qual(is) input(s) utilizará?**
> *(Opções filtradas pela plataforma escolhida)*
>
> | Plataforma | Inputs Disponíveis |
> |------------|-------------------|
> | Web | User Story (US), Página/URL, Swagger Schema, Postman Collection |
> | Mobile | User Story (US), APK/IPA, Página/URL |
> | API | Swagger Schema, Postman Collection, User Story (US) |
> | Desktop | User Story (US), Página/URL |
> ⚠️ **SALVAR EM:** `connectors.input.type` e `connectors.input.sources` (array)

### Pergunta 7 — Avanade CODE
> **Configuração do Avanade CODE:**
> - [1] Isolada
> - [2] Integrada com o Time
> - [3] Não instalar no momento
> ⚠️ **SALVAR EM:** `avanade_code.enabled` (boolean) e `avanade_code.mode` (string)
> ⚠️ **SALVAR EM:** `avanade_code.enabled` (boolean) e `avanade_code.mode` (string)

---

## 📂 Regras de Geração de Estrutura

### Pastas Base (sempre criadas)
```
fastqa/
├── agents/core/
├── agents/connectors/
├── config/
├── manual_test/US/
├── manual_test/gap_analysis/
├── manual_test/estimate_effort/
├── manual_test/requirements_analysis/
├── manual_test/behavior_analysis/
├── manual_test/test_cases/
├── manual_test/evidence/
├── automated_test/tests/
├── automated_test/config/
├── automated_test/data/
├── automated_test/support/
└── automated_test/results/
```

### Pastas Condicionais

| Condição | Pastas Adicionais |
|----------|-------------------|
| Plataforma = **Web** ou **Desktop** | `automated_test/page/` |
| Plataforma = **Mobile** | `automated_test/screens/`, `automated_test/apk/` |
| Plataforma = **API** | `automated_test/schemas/`, `automated_test/collections/`, `automated_test/mocks/` |
| BDD = **Sim** | `manual_test/features/` |
| Input contém **Swagger** | `manual_test/swagger/` |
| Input contém **Postman** | `manual_test/postman/` |
| Input contém **APK/IPA** | `manual_test/apk/` |
| Gestão = **Azure DevOps** | `scripts/`, `scripts/logs/` |

---

## 💾 Persistência
Salvar todas as respostas em: `fastqa/scripts/project_config.json` usando o seguinte mapeamento:

**Estrutura do JSON:**
```json
{
  "metadata": {
    "created_at": "timestamp",
    "updated_at": "timestamp", 
    "version": "1.0",
    "status": "configured"
  },
  "analysis": {
    "purpose": "Resposta da Pergunta 1",
    "application_description": "Resposta da Pergunta 1",
    "domain": "web|mobile|api|desktop (da Pergunta 3)"
  },
  "project_management": {
    "tool": "Resposta da Pergunta 2",
    "azure_devops": { "enabled": true/false },
    "jira": { "enabled": true/false }
  },
  "platform": {
    "type": "web|mobile|api|desktop (da Pergunta 3, lowercase)",
    "details": {
      "mobile_capabilities": {
        "platform_name": "Android|iOS (Pergunta 3.1a)",
        "platform_version": "versão iOS (Pergunta 3.1c, vazio se Android)",
        "device_name": "nome do dispositivo (Pergunta 3.1b)",
        "automation_name": "UiAutomator2|XCUITest (auto)",
        "auto_grant_permissions": true,
        "app_path": "caminho do APK/IPA (Pergunta 3.1d)",
        "app_package": "package Android (Pergunta 3.1e, vazio se iOS)",
        "app_activity": "activity Android (Pergunta 3.1f, vazio se iOS)",
        "bundle_id": "bundle ID iOS (Pergunta 3.1e, vazio se Android)",
        "appium_server_url": "http://localhost:4723 (Pergunta 3.1g)"
      }
    }
  },
  "testing_approach": {
    "use_gherkin_bdd": true/false, // Pergunta 4
    "test_levels": ["unit", "integration", "e2e"]
  },
  "connectors": {
    "output": {
      "automation_framework": "framework (Pergunta 5, lowercase)",
      "language": "linguagem (Pergunta 5, lowercase)"
    },
    "input": {
      "type": "multi",
      "sources": ["array com inputs da Pergunta 6"]
    }
  },
  "avanade_code": {
    "enabled": true/false, // Pergunta 7
    "mode": "isolated|team|null", // Pergunta 7
    "configured_at": "timestamp"
  }
}
```

> **⚠️ NOTA:** O script de setup foi migrado para TypeScript. Execute: `npx tsx fastqa/scripts/setup/setup-wizard.command.ts`

---

## ⚠️ Regras
1. **AGUARDAR** resposta do usuário em CADA pergunta antes de avançar
2. Mostrar opções filtradas baseadas nas respostas anteriores
3. Ao final, exibir resumo e pedir confirmação antes de criar pastas
4. Criar arquivo `.gitkeep` em cada pasta vazia
5. Após salvar, informar que todos os agents FastQA lerão automaticamente o `project_config.json`
