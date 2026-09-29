---
description: FastQA — Fase 6: Análise de Regressão por PR.
applyTo: '**'
tools: ['azureDevOps', 'memory', 'sequential-thinking']
---

# FastQA — Fase 6: Análise de Regressão

> **Arquivo:** `06-fastqa-regression.md`
> **Escopo:** Análise de regressão baseada em PRs — gerar mapa de regressão, analisar impacto de PRs, classificar risco e gerar plano de regressão priorizado
> **Índice geral:** Consulte `00-fastqa-index.instructions.md`

---

## 🔀 Prefixos de Comando

Todos os comandos neste arquivo suportam **dois prefixos**:

| Prefixo | Comportamento |
|---------|--------------|
| `@fastqa:` | Execução direta do workflow |
| `@fastqa_code:` | Ativa o modo **TEA** antes de executar o workflow |

---

## 🎯 Objetivo

Este arquivo contém instruções para análise de regressão baseada em PRs do repositório da **aplicação** (código de produção). O sistema:
1. Mapeia testes existentes a áreas funcionais via `regression-map.yaml`
2. Analisa PRs para identificar áreas impactadas
3. Cruza áreas impactadas com testes via 5 estratégias em cascata
4. Classifica por risco e gera plano de regressão priorizado

> **⚠️ REGRAS:**
> - ✅ **SEMPRE** utilizar scripts **TypeScript (.ts)** em `fastqa/scripts/regression/commands/`
> - ✅ Executar com: `npx tsx fastqa/scripts/regression/commands/<script>.command.ts`
> - ✅ O `regression-map.yaml` deve ser gerado ANTES de analisar PRs (recomendado)

---

## 🏗️ Arquitetura

```
┌──────────────────────────┐
│   FastQA Agents (Fase 6) │
│  @fastqa:regression_*    │
└───────────┬──────────────┘
            │ invoca
┌───────────▼──────────────┐
│  Scripts TypeScript      │
│  fastqa/scripts/         │
│  regression/commands/    │
├──────────────────────────┤
│ generate-regression-map  │ → Varre testes, gera regression-map.yaml
│ analyze-pr-regression    │ → Analisa PR, gera plano de regressão
└───────────┬──────────────┘
            │ usa
┌───────────▼──────────────┐
│  Providers               │
├──────────────────────────┤
│ Azure DevOps API         │ → PRs via REST API
│ Git Local (fallback)     │ → git diff / git log
└──────────────────────────┘

┌───────────────────────────────────────────┐
│  execute_regression_plan (Agent 6.3)      │
│  Executa via run_in_terminal diretamente  │
│  (sem script — usa comandos do framework)  │
├───────────────────────────────────────────┤
│ Lê plano MD → detecta globalAlerts         │
│ globalAlerts > 0 → executa TODOS os testes │
│ globalAlerts = 0 → executa testes mapeados │
└───────────────────────────────────────────┘
```

---

## 📋 Tabela de Comandos

| Comando | Descrição | Agent |
|---------|-----------|-------|
| `@fastqa:generate_regression_map` | Gerar mapa de regressão a partir dos testes | `fastqa/agents/core/fastqa_6.2_generate_regression_map.md` |
| `@fastqa:regression_analyze` | Analisar PR e gerar plano de regressão | `fastqa/agents/core/fastqa_6.1_regression_analyzer.md` |
| `@fastqa:execute_regression_plan` | Executar plano de regressão com análise AI de falhas | `fastqa/agents/core/fastqa_6.3_execute_regression_plan.md` |

---

## ⚙️ `@fastqa:generate_regression_map`

### Objetivo
Varrer o repositório de testes automatizados e manuais, inferir áreas funcionais a partir dos specs, features e page objects, e gerar o `regression-map.yaml`.

### Pré-requisitos
- `fastqa/scripts/project_config.json` configurado (via `@fastqa:setup_project`)
- Testes existentes no workspace (specs, features ou page objects)

### Workflow
1. **Carregar** `fastqa/agents/core/fastqa_6.2_generate_regression_map.md` via `read_file`
2. **Seguir** o fluxo de execução descrito no agent

### Script
```bash
npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts \
  [--output <path>] [--merge] [--layers <name:path,...>] \
  [--app-repo-path <path>] [--app-src-dirs <dirs>]
```

| Flag | Descrição |
|------|-----------|
| `--output` | Caminho de saída (default: `fastqa/scripts/regression-map.yaml`) |
| `--merge` | Preserva `app_patterns` customizados do mapa existente |
| `--layers` | Camadas de teste a varrer no formato `name:path` separadas por vírgula. Ex: `e2e:test/e2e,api:test/api`. Se omitido, usa paths do `project_config.json` |
| `--app-repo-path` | Caminho do repositório da aplicação (código de produção). Quando fornecido, o script varre a estrutura da app e gera `app_patterns` precisos baseados nos paths reais |
| `--app-src-dirs` | Diretórios fonte da app a varrer (vírgula-separado). Ex: `src,lib,routes`. Se omitido, varre toda a raiz excluindo `node_modules`, `dist`, `test*`, etc. |

### Varredura Multi-Camada

O agent **solicita ao usuário** os caminhos de testes E2E, API e Unitários antes de executar. Isso permite mapear projetos com múltiplas camadas de teste em diretórios distintos.

- **1 camada informada:** testes sem prefixo (backward-compatible)
- **Múltiplas camadas:** testes prefixados com `[layer]` no YAML (ex: `[api] loginApiSpec.ts`, `[unit] insecuritySpec.ts`)
- **Extensões reconhecidas:** `.spec.ts`, `.test.ts`, `Spec.ts`, `Spec.js` (Frisby/Jest/Mocha), `.feature`, etc.

### App-Aware Patterns

Quando `--app-repo-path` é fornecido, o script varre o código da aplicação e cruza com as áreas inferidas dos testes para gerar `app_patterns` precisos:

- Analisa paths reais da aplicação usando a mesma lógica de `deriveAreaName` do analisador de PR
- Se múltiplos arquivos estão no mesmo diretório → padrão de diretório: `routes/login/**`
- Se arquivos espalhados → padrões individuais: `routes/login.ts`, `lib/insecurity.ts`
- Áreas da app sem testes correspondentes são reportadas no resumo como "sem cobertura"
- Se `--merge` ativo: `app_patterns` manuais do YAML existente têm prioridade sobre os auto-gerados

### Saída
- Arquivo `fastqa/scripts/regression-map.yaml` gerado/atualizado
- Resumo de áreas detectadas e testes mapeados
- **🤖 Revisão Inteligente (AI Review):** Após o script gerar o YAML bruto, o agente IA automaticamente:
  - Consolida áreas semanticamente equivalentes (ex: tags de `.feature` → `ui`)
  - Substitui `app_patterns` genéricos por paths reais da aplicação
  - Preenche `description` com texto significativo
  - Organiza áreas em seções temáticas
  - Refina `global_triggers` com paths de infraestrutura reais
- Para pular a revisão AI: use `--no-ai-review` (gera apenas o YAML bruto)

---

## ⚙️ `@fastqa:regression_analyze`

### Objetivo
Receber um PR do repositório da aplicação, identificar áreas impactadas, cruzar com testes existentes e gerar plano de regressão priorizado.

### Pré-requisitos
- `fastqa/scripts/project_config.json` configurado
- `fastqa/scripts/regression-map.yaml` gerado (recomendado, mas não obrigatório)
- Para Azure DevOps: PAT configurado e `@fastqa:azdo_health` OK
- Para Git local: repositório da aplicação clonado localmente

### Providers

| Provider | Quando usar | Input |
|----------|-------------|-------|
| Azure DevOps | PR no Azure DevOps | URL do PR ou ID + repo |
| Git Local | Repo local / fallback | Caminho do repo da aplicação |

### Workflow
1. **Carregar** `fastqa/agents/core/fastqa_6.1_regression_analyzer.md` via `read_file`
2. **Seguir** o fluxo de execução descrito no agent

### Script
```bash
npx tsx fastqa/scripts/regression/commands/analyze-pr-regression.command.ts \
  --pr-url <URL>                    # URL do PR (Azure DevOps)
  --pr-id <ID> --repo <REPO>       # Ou ID + repo (Azure DevOps)
  --app-repo-path <PATH>           # Ou caminho local do repo da app
  [--target-branch <BRANCH>]       # Branch alvo (default: develop)
  [--dry-run]                       # Simular sem gerar relatório
```

### Saída
- Relatório Markdown em `fastqa/manual_test/regression_analysis/PR-{id}_regression_plan.md`
- Resumo no chat com:
  - Áreas impactadas e testes por nível de risco (🔴🟠🟡🟢⚪)
  - Comandos de execução prontos para copiar
  - Ações sugeridas (executar smoke, regressão completa, criar testes para gaps)

### 5 Estratégias de Cascata

| # | Estratégia | Confiança |
|---|-----------|-----------|
| 1 | `regression-map.yaml` — app_patterns | Alta |
| 2 | Tags em `.feature` files | Média-Alta |
| 3 | Nome de arquivo por convenção | Média |
| 4 | Busca textual no conteúdo | Baixa |
| 5 | Impacto global (config/middleware/database) | Global |

---

## 🔗 Dependências

Os scripts de regressão dependem de pacotes adicionais:

```bash
cd fastqa && npm install js-yaml minimatch && npm install -D @types/js-yaml
```

> Esses pacotes já devem estar instalados se o `@fastqa:setup_project` incluiu as dependências de regressão. Caso contrário, instale manualmente.

---

## 📂 Estrutura de Arquivos

```
fastqa/
├── scripts/
│   ├── regression-map.yaml                              # Mapa app↔testes
│   └── regression/
│       ├── types/
│       │   └── regression.types.ts                      # Tipos compartilhados
│       ├── utils/
│       │   └── area-name.utils.ts                       # deriveAreaName (compartilhado)
│       ├── providers/
│       │   ├── git-local.provider.ts                    # Provider Git local
│       │   └── pr-provider.resolver.ts                  # Resolver de providers
│       └── commands/
│           ├── generate-regression-map.command.ts        # Gerar regression-map
│           └── analyze-pr-regression.command.ts          # Analisar PR
├── agents/core/
│   ├── fastqa_6.1_regression_analyzer.md                # Agent de análise
│   ├── fastqa_6.2_generate_regression_map.md            # Agent de geração do mapa
│   └── fastqa_6.3_execute_regression_plan.md            # Agent de execução do plano
└── manual_test/
    └── regression_analysis/                             # Relatórios gerados
        ├── PR-{id}_regression_plan.md
        └── PR-{id}_execution_report_{timestamp}.md
```

---

## ⚙️ `@fastqa:execute_regression_plan`

### Objetivo
Receber um plano de regressão gerado por `@fastqa:regression_analyze`, executar os testes localmente ou via pipeline, analisar falhas com IA e gerar relatório de execução.

### Pré-requisitos
- Plano de regressão gerado em `fastqa/manual_test/regression_analysis/`
- `fastqa/scripts/project_config.json` configurado
- Framework de testes instalado (dependências em node_modules)

### Workflow
1. **Carregar** `fastqa/agents/core/fastqa_6.3_execute_regression_plan.md` via `read_file`
2. **Seguir** o fluxo de execução descrito no agent

### 🚨 Regra de Escalação por Impacto Global

> **REGRA CRÍTICA:** Quando o plano de regressão contém `globalAlerts` (alertas `🔴 global-impact` ou `🔴 global-trigger`), o escopo de execução **DEVE** ser automaticamente escalado para **TODOS os testes** (e2e + api + unit), independente de filtros do usuário.

| Condição | Escopo de Execução |
|----------|-------------------|
| `globalAlerts > 0` | **TODOS os testes** (suite completa) |
| `globalAlerts = 0` | Apenas testes mapeados no plano |

**Motivo:** Alterações em configuração global, middleware ou infraestrutura podem afetar qualquer parte do sistema. Uma execução parcial pode não detectar regressões indiretas.

**Testes mapeados vs. Todos os testes:**
- Os testes mapeados no plano servem como **prioridade de análise de falhas** (investigação detalhada com contexto do PR)
- Os demais testes recebem análise simplificada em caso de falha
- O escopo de **execução** é ALL quando há alertas globais

### Execução Direta (sem script)

O agent executa os testes diretamente via terminal usando os comandos do framework:

```bash
# Suite completa (quando globalAlerts > 0)
npx cypress run                    # E2E
npm test                           # Unit + API

# Specs mapeados apenas (quando globalAlerts = 0)
npx cypress run --spec "login.spec.ts,..."
npm test -- loginApiSpec.ts ...
```

### Saída
- Relatório Markdown em `fastqa/manual_test/regression_analysis/PR-{id}_execution_report_{timestamp}.md`
- Resumo no chat com resultados por área, taxa de sucesso e análise AI de falhas
- Ações de continuidade sugeridas (`@fastqa:verify_and_fix`, `@fastqa:azdo_generate_report`, etc.)
