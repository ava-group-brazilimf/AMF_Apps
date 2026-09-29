---
description: FastQA — Fase 3: Execução de Testes Manuais (Web, API e Mobile).
applyTo: '**'
tools: ['playwright-web', 'playwright-api', 'appium-mcp', 'azureDevOps', 'memory', 'sequential-thinking']
---

# FastQA — Fase 3: Execução de Testes Manuais

> **Arquivo:** `03-fastqa-execution.instructions.md`
> **Escopo:** Comandos de execução manual de testes Web e API via Playwright MCP
> **Índice geral:** Consulte `00-fastqa-index.instructions.md`

---

## 🔀 Prefixos de Comando

| Prefixo | Comportamento |
|---------|--------------|
| `@fastqa:` | Execução direta do workflow |
| `@fastqa_code:` | Ativa o modo **TEA** (Test Architect) em `code_qa/_bmad/bmm/agents/tea.md` **antes** de executar o workflow |

---

## 📋 Comandos — Execução Web

### 🎬 `run_manual_test` — Execução de Testes Manuais (Web)

Executa cenários Gherkin via Playwright MCP com captura automática de evidências e integração opcional com Azure DevOps.

O usuário escolhe o **formato de evidência** antes da execução:
- **📷 Screenshot** — Captura de imagem por step + `browser_snapshot` para registrar textos visíveis
- **🎥 Vídeo** — Gravação contínua com capítulos por step via `browser_start_video` / `browser_video_chapter` / `browser_stop_video` (requer `--caps=devtools` no servidor MCP)

**Agent:** `fastqa/agents/core/fastqa_3.1_run_manual_test.md`

**Workflow:**
1. Solicitar identificação do Test Case a ser utilizado e **AGUARDAR** resposta do usuário
2. Carregar cenário Gherkin de: `fastqa/manual_test/test_cases/`
3. Solicitar a URL da aplicação e **AGUARDAR** resposta
4. Solicitar o **formato de evidência** (📷 Screenshot ou 🎥 Vídeo) e **AGUARDAR** resposta
5. Validar MCP Playwright configurado em `.vscode/mcp.json`
6. Executar cenário passo a passo com o Playwright MCP, de forma manual
7. Salvar evidências em: `fastqa/manual_test/evidence/[TS-ID]/`
8. Perguntar se deseja enviar resultado para Azure DevOps e **AGUARDAR** resposta:
   - Se **Sim**: Executar `@fastqa:azdo_upload_test_execution` automaticamente
     - Solicitar: Test Plan ID, Test Suite ID, Test Case ID, Resultado (Passed/Failed)
     - Upload automático: Evidências + Status + Bug (se Failed)
     - Exibir: Test Run ID e URL no Azure DevOps
   - Se **Não**: Apenas confirmar salvamento local das evidências
   - Se **Ver parâmetros**: Mostrar como executar o comando manualmente depois

**Pré-requisitos:**
- Cenários Gherkin validados (via `validate_scenarios`)
- MCP Playwright configurado em `.vscode/mcp.json` com `--caps=devtools` (obrigatório para modo Vídeo)
- [Opcional] MCP Azure DevOps configurado (para integração automática)

---

### 🚀 `run_parallel_tests` — Execução Paralela de Testes (Web)

Executa múltiplos cenários Gherkin em browsers separados via servidores Playwright MCP isolados, com captura de evidências POR STEP.

O usuário escolhe o **formato de evidência** antes da execução (aplicado a todos os cenários):
- **📷 Screenshot** — Captura de imagem por step + `browser_snapshot` para registrar textos visíveis
- **🎥 Vídeo** — Gravação contínua com capítulos por step via `browser_start_video` / `browser_video_chapter` / `browser_stop_video` (requer `--caps=devtools` no servidor MCP)

**Agent:** `fastqa/agents/core/fastqa_3.2_run_parallel_execution.md`

**Workflow:**
1. Solicitar identificação dos cenários a executar e **AGUARDAR** resposta
2. Carregar cenários de: `fastqa/manual_test/test_cases/`
3. Solicitar a URL da aplicação e **AGUARDAR** resposta
4. Solicitar o **formato de evidência** (📷 Screenshot ou 🎥 Vídeo) e **AGUARDAR** resposta
5. Atribuir cada cenário a um servidor MCP e apresentar tabela para confirmação
6. Executar cada cenário no servidor MCP atribuído com evidência POR STEP
7. Gerar relatório consolidado + detalhamento por cenário
8. Salvar evidências em: `fastqa/manual_test/evidence/TS-{NNN}/`
9. Perguntar se deseja enviar resultados para Azure DevOps e **AGUARDAR** resposta:
   - Se **Sim**: Executar `upload-test-execution.command.ts` para cada cenário
   - Se **Não**: Apenas confirmar salvamento local das evidências

**Pré-requisitos:**
- Múltiplos cenários Gherkin validados
- MCP Playwright configurado com **múltiplos servidores** em `.vscode/mcp.json` com `--caps=devtools` (obrigatório para modo Vídeo)
- Servidores MCP paralelos são criados automaticamente pelo agente conforme a quantidade de cenários informada
- [Opcional] MCP Azure DevOps configurado (para integração automática)

---

## 📋 Comandos — Execução API

### 🔌 `run_manual_api_test_swagger` — Execução Manual de Testes API via Swagger

Executa testes manuais de API utilizando o Playwright MCP para navegar na documentação Swagger/OpenAPI e realizar chamadas HTTP interativas com captura de evidências.

**Agent:** `fastqa/agents/core/fastqa_3.3_run_manual_api_test.md`

> **⚠️ REQUER** Playwright MCP habilitado. Servidor recomendado: `playwright-api` em `.vscode/mcp.json`

**Workflow (15 etapas):**

1. Solicitar identificação da User Story / PBI e **AGUARDAR** resposta
2. **Validar** que o Playwright MCP está configurado e ativo (recomendado: servidor `playwright-api`)
3. Solicitar a **URL do Swagger/OpenAPI** e **AGUARDAR** resposta
4. **Navegar** até a página do Swagger via Playwright MCP
5. **Explorar** a documentação e listar todos os endpoints/recursos disponíveis
6. Solicitar ao usuário qual **recurso** (ex: `/api/books`, `/api/users`) deseja testar e **AGUARDAR** resposta
7. Exibir **operações HTTP disponíveis** para o recurso selecionado (GET, POST, PUT, DELETE, PATCH)
8. Solicitar quais **operações** deseja executar e **AGUARDAR** resposta
9. Para cada operação selecionada:
   a. Expandir o endpoint no Swagger via Playwright
   b. Preencher parâmetros e body (se necessário)
   c. Clicar em **"Try it out"** → **"Execute"**
   d. Capturar **screenshot** do resultado
   e. Registrar: Status Code, Response Body, Response Headers, Tempo de resposta
   f. Validar resultado (PASS/FAIL) com base nos critérios esperados
10. **Repetir** para cada operação selecionada
11. Após executar todas as operações, gerar **relatório consolidado** em markdown:
    - Tabela com: Endpoint, Método, Status Code, Resultado (PASS/FAIL), Tempo
    - Detalhes de cada resposta
    - cURL equivalente de cada chamada
    - Lista de bugs encontrados (se houver)
12. Salvar evidências em: `fastqa/manual_test/evidence/api/[recurso][Endpoint]/`
    - Screenshots de cada execução
    - Relatório `.md` consolidado
    - Arquivo com comandos cURL equivalentes
13. Perguntar se deseja **gerar cenários Gherkin** a partir dos testes executados e **AGUARDAR** resposta:
    - Se **Sim**: Gerar `.feature` usando o template `fastqa_2.1_api_gherkin_writer.md` e salvar em `manual_test/test_cases/api/`
    - Se **Não**: Apenas confirmar salvamento das evidências
14. Perguntar se deseja **enviar resultado para Azure DevOps** e **AGUARDAR** resposta
15. Perguntar se deseja testar outro recurso/endpoint

**Estrutura de Evidências:**
```
manual_test/evidence/api/
├── books/
│   ├── GET/
│   │   ├── screenshot-001.png
│   │   ├── response.json
│   │   └── curl-command.txt
│   ├── POST/
│   │   ├── screenshot-001.png
│   │   └── response.json
│   └── report.md               # Relatório consolidado do recurso
├── users/
│   ├── GET/
│   ├── POST/
│   ├── PUT/
│   ├── DELETE/
│   └── report.md
└── api-test-report.md           # Relatório geral de todos os recursos
```

**Pré-requisitos:**
- MCP Playwright configurado em `.vscode/mcp.json` (servidor `playwright-api` recomendado)
- URL da documentação Swagger/OpenAPI disponível
- Servidor MCP ativo

---

## � Comandos — Execução Mobile

### 📱 `run_mobile_test` — Execução de Testes Manuais (Mobile)

Executa cenários Gherkin em aplicativos **Android/iOS** via **Appium MCP** com captura automática de evidências via **📷 Screenshot** (PNG por step) e integração opcional com Azure DevOps.

**Agent:** `fastqa/agents/core/fastqa_3.4_run_mobile_test.md`

> **⚠️ REQUER** Appium MCP habilitado (`appium-mcp` em `.vscode/mcp.json`), Appium Server rodando e emulador/dispositivo conectado.

**Workflow:**
1. Verificar automaticamente disponibilidade do `appium-mcp` via `tool_search_tool_regex`:
   - **Disponível** → confirmar e prosseguir
   - **Não disponível** → orientar ativação e **PARAR** até confirmação
2. Solicitar identificação do(s) Test Case(s) a executar (1 ou mais) e **AGUARDAR** resposta
3. Carregar cenários Gherkin de `fastqa/manual_test/test_cases/`
4. Solicitar a plataforma alvo (Android/iOS) e confirmar capabilities de `fastqa/agents/connectors/mobile/capabilities.json`
5. Criar pastas de evidências: `fastqa/manual_test/evidence/MOBILE-TC-{ID}/`
6. Iniciar sessão Appium MCP com as capabilities carregadas
7. Executar cada cenário passo a passo via Appium MCP com screenshot obrigatório por step:
   - `appium_find_elements` para localizar elementos
   - `appium_click`, `appium_tap`, `appium_type`, `appium_swipe` para interações
   - `appium_get_text` para assertivas de resultado
   - `appium_screenshot` após cada step
8. Registrar PASS/FAIL por step e por cenário
9. Encerrar sessão com `appium_stop_session`
10. Gerar relatório consolidado: `fastqa/manual_test/evidence/relatorio-mobile_{YYYY-MM-DD}.md`
11. Perguntar se deseja enviar resultado para Azure DevOps e **AGUARDAR** resposta:
    - Se **Sim**: Executar `@fastqa:azdo_upload_test_execution` para cada cenário
    - Se **Não**: Apenas confirmar salvamento local das evidências

**Pré-requisitos:**
- Cenários Gherkin validados (via `@fastqa:validate_scenarios`)
- Appium Server rodando na porta 4723 (`appium`)
- Emulador Android iniciado ou dispositivo físico conectado (`adb devices`)
- `capabilities.json` preenchido em `fastqa/agents/connectors/mobile/capabilities.json`
- `appium-mcp` configurado em `.vscode/mcp.json` e servidor iniciado
- [Opcional] MCP Azure DevOps configurado (para integração automática)

---

### 🔍 `run_mobile_exploratory_test` — Teste Exploratório Mobile

Realiza testes exploratórios em aplicativos **Android/iOS** via **Appium MCP** a partir de uma funcionalidade, PBI, US ou qualquer contexto informado no chat. O agent explora o comportamento do app usando heurísticas estruturadas e ao final gera evidências e/ou cenários de teste Gherkin com base nos achados.

**Agent:** `fastqa/agents/core/fastqa_3.5_run_mobile_exploratory_test.md`

> **⚠️ REQUER** Appium MCP habilitado (`appium-mcp` em `.vscode/mcp.json`), Appium Server rodando e emulador/dispositivo conectado.

**Workflow:**
1. Verificar disponibilidade do `appium-mcp` e do `capabilities.json`
2. Capturar contexto da exploração (funcionalidade, PBI, US ou descrição livre)
3. Solicitar escolha de **heurística**: SFDIPOT, VADER Mobile ou TOUR e **AGUARDAR** resposta
4. Solicitar **tempo disponível** para a sessão e **AGUARDAR** resposta
5. Perguntar se deseja **capturar evidências** (screenshots) e **AGUARDAR** resposta
6. Perguntar se deseja **gerar cenários Gherkin** a partir dos achados e **AGUARDAR** resposta
7. Solicitar plataforma alvo e capabilities; criar estrutura de pastas de evidências (se aplicável)
8. Iniciar sessão Appium MCP e executar exploração guiada pela heurística e tempo escolhidos
9. Registrar achados em tempo real: ✅ Esperado | 🐛 Bug | ⚠️ Dúvida | 💡 Sugestão
10. Encerrar sessão com `appium_stop_session`
11. Gerar relatório markdown: `fastqa/manual_test/evidence/relatorio-exploratorio-mobile_{YYYY-MM-DD}.md`
12. Se `GENERATE_SCENARIOS = true`: Gerar arquivo `.feature` com cenários em 3 camadas (Positivos, Negativos/Borda, Parametrizados) + Matriz de Rastreabilidade + Sugestão de Automação

**Pré-requisitos:**
- Appium Server rodando na porta 4723 (`appium`)
- Emulador Android iniciado ou dispositivo físico conectado (`adb devices`)
- `capabilities.json` preenchido em `fastqa/agents/connectors/mobile/capabilities.json`
- `appium-mcp` configurado em `.vscode/mcp.json` e servidor iniciado
- Contexto da exploração (funcionalidade, PBI, US ou descrição livre no chat)

---

## 🔄 Fluxo Recomendado — Fase 3

```
[Vindo da Fase 2 → 02-fastqa-test-design.instructions.md]
        ↓
┌─── Web ──────────────────────────────────────┐
│ @fastqa:run_manual_test                      │
│   ou (se múltiplos cenários)                 │
│ @fastqa:run_parallel_tests                   │
└──────────────────────────────────────────────┘
        ↓
┌─── API ──────────────────────────────────────┐
│ @fastqa:run_manual_api_test_swagger          │
└──────────────────────────────────────────────┘
        ↓
┌─── Mobile ───────────────────────────────────┐
│ @fastqa:run_mobile_test                      │
│   (1 ou mais cenários via Appium MCP)        │
│                                              │
│ @fastqa:run_mobile_exploratory_test          │
│   (exploração livre por heurística)          │
└──────────────────────────────────────────────┘
        ↓
[Evidências em fastqa/manual_test/evidence/]
        ↓
┌─── Opcional ─────────────────────────────────┐
│ Upload para Azure DevOps                     │
│ → @fastqa:azdo_upload_test_execution         │
│ → 05-fastqa-azure-devops.instructions.md     │
└──────────────────────────────────────────────┘
        ↓
[Próxima fase → 04-fastqa-automation.instructions.md]
```

---

**Versão:** 5.0 | **Atualização:** 21 de Fevereiro de 2026
