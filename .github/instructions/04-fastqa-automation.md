---
description: FastQA — Fase 4: Automação de Testes (Web, API e Mobile).
applyTo: '**'
tools: ['playwright-web', 'memory', 'sequential-thinking']
---

# FastQA — Fase 4: Automação de Testes

> **Arquivo:** `04-fastqa-automation.instructions.md`
> **Escopo:** Geração de scripts automatizados, instalação de frameworks e regras de implementação API
> **Índice geral:** Consulte `00-fastqa-index.instructions.md`

---

## 🔀 Prefixos de Comando

| Prefixo | Comportamento |
|---------|--------------|
| `@fastqa:` | Execução direta do workflow |
| `@fastqa_code:` | Ativa o modo **TEA** (Test Architect) em `code_qa/_bmad/bmm/agents/tea.md` **antes** de executar o workflow |

---

## 📋 Comandos — Automação Web / Mobile

### 🤖 `automate_test` — Automação de Testes Web/Mobile

Gera scripts automatizados a partir de cenários Gherkin ou evidências manuais, usando o framework e linguagem configurados no projeto.

**Template Web:** `fastqa/agents/core/fastqa_4.1_create_automated_test.md`  
**Resolver:** `fastqa/agents/resolver.md` — roteia para o connector correto conforme `project_config.json` e injeta caminhos dinâmicos

> **📌 Agent resolvido dinamicamente:** O resolver seleciona o connector correto para a combinação plataforma/framework/linguagem configurada (ex.: `connectors/web/playwright/typescript/`, `connectors/api/cypress/javascript/`, `connectors/mobile/webdriverio/typescript/`, etc.) — não há template fixo de entrada.

**Workflow:**
1. Solicitar identificação do arquivo com os Test Cases a serem utilizados e **AGUARDAR** resposta
2. Solicitar o **nome da funcionalidade** sendo testada (ex: `login`, `checkout-produto`, `recuperar-senha`) e **AGUARDAR** resposta
   - Usar como **slug kebab-case** nos nomes de arquivo gerados: `{funcionalidade}.spec.ts`, `{funcionalidade}.data.json`
   - Converter para **PascalCase** no nome da Page Object: `{FuncionalidadePascalCase}Page.page.ts`
   - Exemplo: funcionalidade `"login usuario"` → arquivo `login-usuario.spec.ts` → page `LoginUsuarioPage.page.ts`
3. Solicitar arquivo de test_cases ou evidências como referência e **AGUARDAR** resposta
4. Validar ambiente conforme framework/linguagem configurado no projeto (`scripts/project_config.json`)
5. Solicitar a URL base do sistema (ex: `https://app.example.com`) e **AGUARDAR** resposta
6. Gerar arquivos automaticamente na pasta da plataforma configurada:

####
| Modo | Fonte de Caminhos | Exemplo de Saída |
|------|-------------------|------------------|
| **Scaffold** | Padrão pré-definido | `automated_test/web/tests/`, `automated_test/web/pages/`, etc. |
| **Attach** | `project_config.json → folder_structure.custom_paths` | Caminhos personalizados do usuário (ex.: `tests/e2e/`, `src/pages/`) |

> **💡 Nota:** O resolver extrai `{{AUTOMATION_ROOT}}`, `{{TESTS_DIR}}`, `{{PAGES_DIR}}`, `{{CONFIG_DIR}}` e `{{RESULTS_DIR}}` (opcional) do `project_config.json` e injeta no connector selecionado. Fallback automático para `automated_test/{platform}` se caminhos customizados não estiverem definidos.

**Padrões de Design:**
- **Web:** Page Object Model (POM) com locators descritivos
- **Mobile:** Screen Object Pattern com gestures e swipes
- **AAA Pattern:** Arrange-Act-Assert em todos os testes
- **TypeScript:** Tipagem forte e interfaces

**Pré-requisitos:**
- Framework e linguagem configurados em `project_config.json`
- Dependências do framework instaladas (ver `fastqa/agents/resolver.md` para comandos)
- Se ambiente não estiver pronto → executar `@fastqa:install_framework`

---

### 📱 `create_mobile_automation` — Criação de Automação Mobile (Appium)

Cria automação de testes Mobile com Appium usando o framework e linguagem configurados no projeto (WebdriverIO, Robot, Selenium). O comando força `platform = mobile` e roteia diretamente para o connector correto.

**Connector:** `fastqa/agents/connectors/mobile/{framework}/{language}/fastqa_4.1_create_automated_test.md`  
**Resolver:** `fastqa/agents/resolver.md` — carregado com `platform = mobile` forçado

> **📌 Agent resolvido dinamicamente:** O resolver seleciona o connector mobile correto para a combinação framework/linguagem configurada (ex.: `connectors/mobile/webdriverio/typescript/`, `connectors/mobile/webdriverio/javascript/`, `connectors/mobile/robot/python/`).

**Pré-requisitos — Passo 0 (verificar ANTES de iniciar):**

| # | Requisito | Comando de verificação |
|---|-----------|----------------------|
| 1 | JDK 17+ instalado e `JAVA_HOME` configurado | `java -version` |
| 2 | Android Studio + SDK instalados e `ANDROID_HOME` configurado | `adb version` |
| 3 | Node.js LTS + npm | `node -v && npm -v` |
| 4 | Appium Server + driver uiautomator2 | `appium --version && appium driver list --installed` |
| 5 | Ambiente validado com Appium Doctor | `appium-doctor --android` |
| 6 | Appium Inspector instalado | [Download](https://github.com/appium/appium-inspector/releases) |
| 7 | Emulador ou dispositivo físico conectado | `adb devices` |

> 📖 Guia completo de ambiente: `fastqa/agents/connectors/mobile/MOBILE_GUIDE.md`

**Se ainda não instalou o WebdriverIO + Appium MCP:**

```cmd
npm init wdio@latest .
npm install appium-mcp@latest
npx appium driver install uiautomator2
```

> 📖 Guia WebdriverIO: `fastqa/agents/connectors/mobile/webdriverio/DEVELOPER_WEBDRIVERIO_GUIDE.md`

**Workflow:**
1. Verificar pré-requisitos do ambiente mobile (Passo 0 no connector) e **AGUARDAR** confirmação do usuário
2. Verificar disponibilidade do **Appium MCP** via `tool_search_tool_regex` (padrão: `appium_get_page_source|appium_find_elements`):
   - **Disponível** → usar para inspecionar elementos reais do app durante a geração de Screen Objects (locators precisos)
   - **Não disponível** → informar o usuário para ativar: `Ctrl+Shift+P` → "MCP: List Servers" → Start **appium-mcp**; aguardar confirmação ou continuar sem MCP
3. Ler `project_config.json` para determinar `framework`, `language` e `platform.details.mobile_capabilities`
3. Verificar se o scaffold inicial já existe (`{{AUTOMATION_ROOT}}/config/wdio.shared.conf.js` ou equivalente); se não existir, criá-lo automaticamente
4. Solicitar o arquivo com os Test Cases a serem automatizados e **AGUARDAR** resposta
   - Após receber o arquivo, identificar **quantos cenários/scenarios** existem
   - **Se houver mais de 1 cenário**, listar todos numerados e perguntar:
     > **"Encontrei [N] cenários. Deseja automatizar todos ou algum específico?"**
     > - **Todos** → gerar um `spec.ts` por cenário (ou agrupados no mesmo `describe` se forem da mesma funcionalidade)
     > - **Específico(s)** → solicitar quais (ex.: `"1, 3"` ou nome do cenário) e **AGUARDAR** resposta
   - **Se houver apenas 1 cenário**, prosseguir diretamente
5. Solicitar o **nome da funcionalidade** (ex.: `login`, `checkout`, `cadastro`) e **AGUARDAR** resposta
   - Usar como slug kebab-case no nome dos arquivos: `{funcionalidade}.spec.ts`
   - Converter para PascalCase no nome do Screen Object: `{FuncionalidadePascalCase}Screen.ts`
6. Gerar arquivos na estrutura configurada:

| Tipo | Pasta | Exemplo de Nome |
|------|-------|----------------|
| **Screen Object** | `{{AUTOMATION_ROOT}}/android/screen/` | `LoginScreen.ts` |
| **Test Spec** | `{{AUTOMATION_ROOT}}/android/tests/` | `login.spec.ts` |
| **Test Data** | `{{AUTOMATION_ROOT}}/android/data/` | `login.data.json` |
| **Support** | `{{AUTOMATION_ROOT}}/android/support/` | helpers e utilitários |
| **Components** | `{{AUTOMATION_ROOT}}/android/components/` | componentes reutilizáveis |

> **💡 Nota:** `{{AUTOMATION_ROOT}}` é resolvido de `project_config.json → folder_structure.custom_paths.automation_root`; fallback para `automated_test/mobile`.

7. Executar o ciclo de auto-healing obrigatório (máx. 5 tentativas) após geração de todos os arquivos

**Padrões de Design:**
- **Screen Object Pattern** (equivalente ao POM para mobile) com locators descritivos
- Locators via `appium-mcp` (appium_find_elements) quando o MCP estiver ativo
- **AAA Pattern** (Arrange-Act-Assert) em todos os testes
- Suporte a gestures (`swipe`, `tap`, `longPress`) via helpers de components

**Pré-requisitos:**
- `project_config.json` configurado com `platform.type = 'Mobile'` e framework mobile
- Ambiente Appium + Android SDK configurado (Passo 0)
- Emulador ou dispositivo conectado (`adb devices`)
- Para WebdriverIO: dependências instaladas via `npm init wdio@latest .`

---

### ⚙️ `install_framework` — Instalação do Framework de Testes

Guia a instalação e configuração do framework escolhido no projeto.

**Workflow:**
1. Verificar framework configurado em `project_config.json`
2. Consultar `fastqa/agents/resolver.md` para obter o conector correto
3. Executar o script de instalação a partir da pasta `automated_test/` (raiz do workspace):

> **⚠️ IMPORTANTE:** Os comandos de instalação npm/pip devem ser executados **dentro da pasta `automated_test/`**. Essa pasta possui seu próprio `package.json` com scripts pré-configurados.

| Framework | Linguagem | Comando (executar em `automated_test/`) |
|-----------|-----------|----------------------------------------|
| Playwright | TypeScript | `npm run setup:playwright` |
| Cypress | TypeScript | `npm run install:cypress` |
| WebdriverIO | TypeScript | `npm run install:webdriverio` |
| WebdriverIO (Mobile) | JS/TS | `npm init wdio@latest .` *(interativo — ver `DEVELOPER_WEBDRIVERIO_GUIDE.md`)* |
| Supertest | TypeScript | `npm run install:supertest` |
| Selenium | Python | `pip install selenium pytest` |
| Robot | Python | `pip install robotframework robotframework-seleniumlibrary` |
| Selenium (Mobile) | Python | `pip install Appium-Python-Client selenium pytest` |
| Requests | Python | `pip install requests pytest` |
| RestAssured | Java | Adicionar dependência Maven/Gradle |
| Karate | Java | Adicionar dependência Maven |

4. Gerar arquivo de configuração no caminho definido em `project_config.json → folder_structure.custom_paths.config`; fallback para `automated_test/{web|api|mobile}/config/` em modo scaffold.
5. Preservar estrutura existente do projeto em modo attach;

---

## 📋 Comandos — Automação API

### 🔌 `api_create_automated` — Geração de Testes Automatizados de API

Gera scripts automatizados de testes de API a partir de cenários Gherkin, cURL ou URL, usando Playwright + TypeScript.

**Agent:** `fastqa/agents/core/fastqa_4.2_api_create_automated_test.md`

> **📌 RESOLUÇÃO DE CAMINHO:** Este agent é resolvido dinamicamente pelo `fastqa/agents/resolver.md` quando `platform.type === 'api'` e o comando `@fastqa:api_create_automated` for invocado. O resolver pode direcionar para este agent genérico em `core/` ou para connectors específicos em `connectors/api/{framework}/{language}/` conforme a configuração do projeto.

**Workflow:**
1. Solicitar **input** e **AGUARDAR** resposta do usuário. Aceita 3 opções:
   - **Opção 1:** Arquivo `.feature` — Caminho de cenário Gherkin existente
   - **Opção 2:** Comando `cURL` — Colado diretamente no chat
   - **Opção 3:** URL da API / Swagger — URL para geração automática
2. **Se Opção 2 (cURL) ou Opção 3 (URL):**
   - Executar primeiro o template `fastqa/agents/core/fastqa_2.1_api_gherkin_writer.md` para gerar cenários Gherkin
   - Salvar `.feature` gerado em `manual_test/test_cases/api/`
   - Em seguida, prosseguir para automação com o `.feature` gerado
3. Validar ambiente:
   - Node.js v22+ instalado
   - Playwright instalado (`npx playwright --version`)
   - Ler `project_config.json → folder_structure.custom_paths` para resolver o caminho raiz de API (`{{AUTOMATION_ROOT}}`); fallback para `automated_test/api/`
4. Mapear cenários Gherkin para implementação:
   - `Given` → Setup de dados, configuração de headers, autenticação
   - `When` → Chamada HTTP (endpoint + método + body)
   - `Then` → Validações (status code, response body, schema, headers)
5. Gerar **6 tipos de arquivo** automaticamente:

| Tipo | Pasta (dinâmica) | Padrão de Nome | Descrição |
|------|-----------------|----------------|-----------|
| **Client** | `{{AUTOMATION_ROOT}}/clients/` | `{recurso}.client.ts` | Funções de chamada HTTP |
| **Schema** | `{{AUTOMATION_ROOT}}/schemas/` | `{recurso}.schema.json` | JSON Schema de validação |
| **Fixture** | `{{AUTOMATION_ROOT}}/fixtures/` | `{recurso}.json` | Dados de teste |
| **Teste** | `{{TESTS_DIR}}/` | `{recurso}.spec.ts` | Testes Playwright (AAA Pattern) |
| **Config** | `{{CONFIG_DIR}}/` | `{recurso}.ts` | Configuração de endpoints |
| **Helper** | `{{AUTOMATION_ROOT}}/helpers/` | `{recurso}.ts` | Utilitários auxiliares |

> Fallback quando `custom_paths` não definido: `automated_test/api/{clients|schemas|fixtures|tests|config|helpers}`

6. Verificar que **TODOS** os arquivos foram criados nas pastas corretas

**Checklist de Implementação (8 passos):**
1. Identificar cenários no `.feature` (nomes, tags, steps)
2. Mapear Given/When/Then para endpoints, métodos e validações
3. Criar client com funções HTTP (`{recurso}.client.ts`)
4. Criar schemas de validação JSON (`{recurso}.schema.json`)
5. Criar fixtures com dados de teste (`{recurso}.json`)
6. Implementar testes com AAA Pattern — Arrange/Act/Assert (`{recurso}.spec.ts`)
7. Validar status codes, headers e schemas nas asserções
8. Verificar que **todos os arquivos foram criados em `{{AUTOMATION_ROOT}}`** (custom_paths) ou em `automated_test/api/` (fallback scaffold)

**Pré-requisitos:**
- Node.js v22+ e Playwright instalados
- `project_config.json` configurado com `folder_structure.custom_paths` (modo attach) ou estrutura `automated_test/api/` (scaffold)
- Input: `.feature`, cURL ou URL

---

## ⚠️ Regras de Implementação API (Obrigatórias)

### REGRA #0 — Estrutura de Pastas

> **SEMPRE** usar os caminhos definidos em `project_config.json → folder_structure.custom_paths`. Fallback para `automated_test/api/` somente quando `custom_paths` não estiver configurado (modo scaffold).

- ✅ CORRETO (attach): usar `{{AUTOMATION_ROOT}}`, `{{TESTS_DIR}}`, `{{CONFIG_DIR}}` conforme project_config
- ✅ CORRETO (scaffold): `automated_test/api/tests/`, `automated_test/api/config/`, `automated_test/api/schemas/`
- ❌ PROIBIDO: criar arquivo em subpasta diferente da configurada sem justificativa
- **SEMPRE** respeitar a estrutura de subdiretórios dentro do caminho raiz (`{{AUTOMATION_ROOT}}`)

```
{{AUTOMATION_ROOT}}/          ← custom_paths.automation_root ou automated_test/api
├── collections/    # Clients HTTP (*.client.ts)
├── schemas/        # JSON Schemas (*.schema.json)
├── fixtures/       # Dados de teste (*.json)
├── helpers/        # Utilitários (*.ts)
├── config/         # Configuração (*.ts)   ← custom_paths.config
├── tests/          # Testes Playwright (*.spec.ts)  ← custom_paths.tests
├── support/        # Suporte geral
├── data/           # Dados auxiliares
└── results/        # Resultados de execução  ← custom_paths.results (opcional)
```

### REGRA #1 — Importação de JSON

> **SEMPRE** usar `require()` para importar arquivos JSON (schemas e fixtures). **NUNCA** usar `import` para JSON.

✅ **CORRETO:**
```typescript
const bookSchema = require('../schemas/book.schema.json');
const userData = require('../fixtures/users.json');
const config = require('../config/api.config.json');
```

❌ **INCORRETO:**
```typescript
import bookSchema from '../schemas/book.schema.json';      // PROIBIDO
import userData from '../fixtures/users.json';              // PROIBIDO
import { bookSchema } from '../schemas/book.schema.json';  // PROIBIDO
```

**Motivo:** `import` para JSON requer configuração especial de `resolveJsonModule` no `tsconfig.json` e pode causar incompatibilidades com o setup padrão Playwright. O `require()` funciona de forma nativa e consistente.

---

## 🔧 Resolver e Connectors

O **Resolver** (`fastqa/agents/resolver.md`) roteia automaticamente para o connector correto baseado na configuração de `project_config.json`.

**Connectors disponíveis:**

| Categoria | Framework | Linguagens | Caminho |
|-----------|-----------|-----------|---------|
| **Web** | Playwright | TS, Python, Java, C# | `agents/connectors/web/playwright/{lang}/` |
| | Cypress | TS, JS | `agents/connectors/web/cypress/{lang}/` |
| | Selenium | Python, Java, C# | `agents/connectors/web/selenium/{lang}/` |
| | WebdriverIO | TS, JS | `agents/connectors/web/webdriverio/{lang}/` |
| | Robot | Python | `agents/connectors/web/robot/python/` |
| **Mobile** | WebdriverIO | TS, JS | `agents/connectors/mobile/webdriverio/{lang}/` |
| | Selenium | Python, Java, C# | `agents/connectors/mobile/selenium/{lang}/` |
| | Robot | Python | `agents/connectors/mobile/robot/python/` |
| **API** | Playwright | TS, Python, Java, C# | `agents/connectors/api/playwright/{lang}/` |
| | Cypress | TS, JS | `agents/connectors/api/cypress/{lang}/` |
| | Robot | Python | `agents/connectors/api/robot/python/` |
| | Supertest | TS | `agents/connectors/api/supertest/` |
| | Requests | Python | `agents/connectors/api/requests/` |
| | RestAssured | Java | `agents/connectors/api/restassured/` |
| | Karate | Java | `agents/connectors/api/karate/` |

---

## 🔄 Fluxo Recomendado — Fase 4

```
[Vindo da Fase 3 → 03-fastqa-execution.instructions.md]
        ↓
┌─── Preparação ───────────────────────────────┐
│ @fastqa:install_framework                    │
│ (se dependências não instaladas)             │
└──────────────────────────────────────────────┘
        ↓
┌─── Web/Mobile ───────────────────────────────┐
│ @fastqa:automate_test                        │
│ (cenários Gherkin → scripts automatizados)   │
└──────────────────────────────────────────────┘
        ↓
┌─── API ──────────────────────────────────────┐
│ @fastqa:api_create_automated                 │
│ (.feature / cURL / URL → testes Playwright)  │
│ ⚠️ REGRA #0: Arquivos em {{AUTOMATION_ROOT}} (ou automated_test/api/) │
│ ⚠️ REGRA #1: require() para JSON imports     │
└──────────────────────────────────────────────┘
        ↓
[Próxima fase → 05-fastqa-azure-devops.instructions.md]
```

---

## �️ `verify_and_fix` — Verificação, Correção e Refatoração de Scripts

Verifica scripts gerados, executa ciclo de auto-healing e sugere refatorações estruturais.

**Agent:** `fastqa/agents/core/fastqa_4.3_verify_and_fix.md`

**Workflow:**
1. Solicitar caminho do arquivo ou pasta a verificar → **AGUARDAR** resposta
2. Detectar framework pelo `project_config.json` ou pela extensão do arquivo
2.1. **Verificar disponibilidade do Playwright MCP** via `tool_search_tool_regex` (padrão: `browser_navigate|browser_snapshot`):
   - Se disponível → registrar prefixo MCP para uso no Passo 4
   - Se **não** disponível → informar ao usuário como ativar (Ctrl+Shift+P → "MCP: List Servers" → Start)
3. Executar o teste e capturar saída + exit code
4. Ciclo de auto-healing (máx. 5 tentativas):
   - Classificar erro (compile / locator / assertion / timeout / dependência)
   - **Se erro de Locator + MCP ativo → Inspeção DOM via Playwright MCP:**
     1. `browser_navigate` → URL da página testada
     2. `browser_click` → Fechar cookies/modais se necessário
     3. `browser_snapshot` → Capturar árvore de acessibilidade
     4. Analisar snapshot → Identificar elemento correto por `role`, `name`, `text`
     5. Definir seletor confiável (prioridade: `data-testid` > `role+name` > `aria-label` > `alt` > texto > `id` > CSS com contexto)
     6. Atualizar Page Object com novo seletor
   - **Se erro de Locator + MCP inativo → Solicitar ativação ao usuário** e AGUARDAR
   - Para outros tipos de erro → corrigir arquivo(s) diretamente
   - Reexecutar; se exit code = 0 → encerrar
5. Se falhar após 5 ciclos → reportar diagnóstico final com stack trace e sugestão manual
6. Independente do resultado → reportar **refatorações sugeridas**:
   - Violações de POM (locators / expect diretos no spec)
   - Métodos longos ou código duplicado
   - Nomenclatura fora do padrão BDD
   - Dados hardcoded no teste

> **⚠️ REGRA CRÍTICA:** Para erros de locator, **NUNCA** adivinhar seletores. **SEMPRE** usar `browser_snapshot` do Playwright MCP para inspecionar o DOM real antes de corrigir. Se o MCP não estiver ativo, **solicitar ativação** ao usuário — nunca usar scripts intermediários.

**Escopo:** Web (`.spec.ts`, `.cy.ts`, `.py`, `Test.java`, `Tests.cs`, `.robot`) + API (Supertest, RestAssured, Requests, Karate)

**Pré-requisitos:**
- Framework instalado e executável
- `project_config.json` configurado (ou o agente infere pelo tipo de arquivo)
- **Playwright MCP iniciado** em `.vscode/mcp.json` (Ctrl+Shift+P → "MCP: List Servers" → Start servidor `playwright*`)

---

## �🔄 Auto-Healing Loop (Obrigatório — Todas as Fases de Automação)

> **⚠️ REGRA INVIOLÁVEL:** Após gerar todos os arquivos de automação, o agente **DEVE** executar o ciclo de auto-healing antes de encerrar. **NUNCA** entregar scripts sem executá-los ao menos uma vez.

### Ciclo de Auto-Healing (máx. 5 tentativas)

```
┌─────────────────────────────────────────────────────────────────┐
│  APÓS GERAÇÃO DOS ARQUIVOS — INICIAR CICLO AUTO-HEALING         │
│                                                                 │
│  Tentativa 1..5:                                                │
│    1. Executar o(s) teste(s) gerado(s) (comando por framework)  │
│    2. Capturar saída completa + exit code                       │
│    3. Se exit code = 0 → ✅ SUCESSO — encerrar ciclo            │
│    4. Se exit code ≠ 0 → Classificar erro:                      │
│       a) Compile/Tipo  → corrigir imports, tipos, interfaces    │
│       b) Locator       → inspeção DOM via Playwright MCP         │
│          → browser_navigate → browser_snapshot → identificar     │
│          → atualizar Page Object com seletor confiável           │
│       c) Assertion     → ajustar valor esperado ou setup        │
│       d) Timeout       → adicionar waitFor / aumentar timeout   │
│       e) Módulo/Dep    → verificar instalação de dependências   │
│    5. Corrigir arquivo(s) problemático(s)                       │
│    6. Incrementar contador; se contador = 5 → reportar diagnóst.│
│                                                                 │
│  ❌ NUNCA ENCERRAR COM SCRIPTS COM FALHAS SEM REPORTAR          │
└─────────────────────────────────────────────────────────────────┘
```

### Comandos de execução por framework

> **⚠️ REGRA:** Sempre usar report **JSON** salvo em arquivo para que o agente analise todas as falhas de uma só vez via `read_file`. **NUNCA** usar `--reporter=line/list` ou filtrar output com `Select-String`/`grep`.

| Framework | Linguagem | Comando de execução (report JSON → arquivo) |
|-----------|-----------|----------------------------------------------|
| Playwright | TypeScript | `$env:PLAYWRIGHT_FORCE_TTY=0; npx playwright test --config={config} {arquivo} --reporter=json 2>$null \| Out-File -FilePath "{results_dir}/diagnostic-report.json" -Encoding utf8` |
| Playwright | Python | `pytest {arquivo} -v --json-report --json-report-file={results_dir}/diagnostic-report.json` |
| Playwright | Java | `mvn test -Dtest={ClassName} -Dsurefire.reportFormat=json` |
| Playwright | C# | `dotnet test --filter "FullyQualifiedName~{ClassName}" --logger "json;LogFileName=diagnostic-report.json"` |
| Cypress | TS / JS | `npx cypress run --spec "{arquivo}" --reporter json \| Out-File -FilePath "{results_dir}/diagnostic-report.json" -Encoding utf8` |
| Selenium | Python | `pytest {arquivo} -v --json-report --json-report-file={results_dir}/diagnostic-report.json` |
| Selenium | Java | `mvn test -Dtest={ClassName} -Dsurefire.reportFormat=json` |
| Selenium | C# | `dotnet test --filter "FullyQualifiedName~{ClassName}" --logger "json;LogFileName=diagnostic-report.json"` |
| Robot | Python | `robot --outputdir {results_dir} {arquivo}` (usa output.xml nativo) |
| WebdriverIO | TS / JS | `cd {automation_root} && npx wdio run config/wdio.conf.ts --spec tests/{arquivo}` |
| Supertest | TypeScript | `npx jest {arquivo} --verbose --json --outputFile={results_dir}/diagnostic-report.json` |
| Requests | Python | `pytest {arquivo} -v --json-report --json-report-file={results_dir}/diagnostic-report.json` |
| RestAssured | Java | `mvn test -Dtest={ClassName} -Dsurefire.reportFormat=json` |
| Karate | Java | `mvn test -Dtest={RunnerClass}` (usa target/karate-reports nativo) |

Após execução, o agente usa `read_file` no `diagnostic-report.json` para analisar **todos os erros** de uma só vez.

### Diagnóstico Final (se falhar após 5 ciclos)

Reportar ao usuário:
1. Resumo das tentativas (o que foi corrigido em cada ciclo)
2. Erro remanescente com stack trace completo
3. Tipo de erro classificado
4. Sugestão de próximo passo manual
5. Indicação do arquivo problemático e linha do erro

---

**Versão:** 5.0 | **Atualização:** 17 de Março de 2026
