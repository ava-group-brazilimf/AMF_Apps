---
description: FastQA — Fase 2: Geração e Validação de Cenários de Teste.
applyTo: '**'
tools: ['playwright-web', 'memory', 'sequential-thinking']
---

# FastQA — Fase 2: Geração e Validação de Cenários de Teste

> **Arquivo:** `02-fastqa-test-design.instructions.md`
> **Escopo:** Comandos de geração de cenários Gherkin (Web e API) e validação de cenários
> **Índice geral:** Consulte `00-fastqa-index.instructions.md`

---

## 🔀 Prefixos de Comando

Todos os comandos neste arquivo suportam **dois prefixos**:

| Prefixo | Comportamento |
|---------|--------------|
| `@fastqa:` | Execução direta do workflow |
| `@fastqa_code:` | Ativa o modo **TEA** (Test Architect & Quality Advisor) em `code_qa/_bmad/bmm/agents/tea.md` **antes** de executar o workflow |

> Quando o comando for chamado com `@fastqa_code:`, **sempre ativar o TEA primeiro**, depois seguir o workflow normalmente.

---

## 🎯 Regra Crítica — Gherkin

> **REGRA OBRIGATÓRIA para TODOS os comandos de geração de cenários:**
> - ✅ Por padrão, keywords em **INGLÊS**: `Feature`, `Scenario`, `Given`, `When`, `Then`, `And`, `But`, `Background`, `Scenario Outline`, `Examples`
> - ✅ Para `@fastqa:test_case_with_fastqa`, respeitar o **formato configurado** em `test_case_format` (`gherkin` ou `step_by_step`) e o idioma selecionado no wizard (Português, Inglês ou Español)
> - ✅ Conteúdo (descrições, steps) em **PORTUGUÊS**

---

## 📋 Comandos — Análise de Escopo de Critérios de Aceite

### 🔍 `ac_scope_analysis` — Análise de Escopo de ACs para Geração de Testes

Analisa uma User Story para classificar rapidamente quais Critérios de Aceite (ACs) devem ser cobertos na geração de casos de teste e quais podem ser excluídos ou adiados. **Também sugere sub-itens específicos dentro de ACs** que não são críticos o suficiente para justificar cenários de teste dedicados.

**Template:** `fastqa/agents/core/fastqa_2.5_ac_scope_analyzer.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar no chat a User Story (US) — aceita:
   - **Arquivo local:** caminho para `.md` na pasta `fastqa/manual_test/US/`
   - **Conteúdo colado:** texto da US diretamente no chat
   - **ID da US:** ex: `10-3-4` → busca automática em `fastqa/manual_test/US/`
3. **AGUARDAR** o envio da US pelo usuário
4. Executar análise em 3 passos (otimizado para velocidade):
   - **Passo 1 — Scan de Exclusões:** Identificar ACs que a própria US declara como fora do escopo de QA (marcadores: "Não será validado em QA", variantes)
   - **Passo 2 — Classificação por Impacto:** Classificar cada AC restante como 🔴 Crítico, 🟡 Importante ou 🔵 Baixa Prioridade
   - **Passo 2.1 — Varredura de Sub-itens:** Para ACs 🔴 e 🟡, identificar sub-itens internos que podem ser dispensados (redundâncias, detalhes visuais, comportamentos implícitos do framework, notas informativas que alteram outra US)
   - **Passo 3 — Geração do Relatório:** Montar relatório com matriz completa, sugestões de exclusão parcial e recomendações
5. Salvar análise em: `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md`

**Critérios de Classificação:**

| Classificação | Critério |
|---------------|----------|
| 🚫 Excluído | US declara explicitamente "Não será validado em QA" ou variantes |
| 🔴 Crítico | Fluxos principais, validações obrigatórias, integrações essenciais, regras de negócio core |
| 🟡 Importante | Validações de formato/limites, fluxos alternativos, modais, uploads, edge cases |
| 🔵 Baixa Prioridade | Responsividade/layout, comportamentos visuais puros, funcionalidades de leitura já cobertas por outra US |

**Integração com outros comandos:**
- Executar **antes** de `test_case_with_fastqa` ou `test_case_with_playwright_mcp`
- O gherkin_writer deve consultar o arquivo `[US-ID]_ac_scope.md` para definir escopo de cenários
- O validator considera o escopo definido ao calcular cobertura

**Pré-requisitos:**
- User Story disponível (arquivo, chat ou Azure DevOps)
- Nenhuma dependência obrigatória de outros comandos

---

## 📋 Comandos — Geração de Cenários Web

### 📝 `test_case_with_fastqa` / `test_case_with_avanade_code` — Geração de Casos de Teste

Gera casos de teste a partir de User Stories, usando o formato configurado em `fastqa/scripts/project_config.json` (`test_case_format`):
- **`gherkin`** → cenários em formato Gherkin (`.feature`)
- **`step_by_step`** → casos de teste em formato passo a passo (tabela ou lista)

> **Nota:** `test_case_with_avanade_code` é o alias `@fastqa_code:` que ativa o TEA antes.

**Template (baseado no `test_case_format` lido do `project_config.json`):**
- `gherkin` → `fastqa/agents/core/fastqa_2.1_gherkin_writer.md`
- `step_by_step` → `fastqa/agents/core/fastqa_2.6_step_by_step_writer.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Ler `fastqa/scripts/project_config.json`: obter `test_case_format` e `test_management_tool`
3. Executar wizard interativo (formato, idioma, limite de steps, etc.)
4. Ao final do wizard, apresentar a pergunta de **Fonte do Conteúdo** e **AGUARDAR** resposta do usuário:
   - **Opção 1 — Informar uma US/PBI específica:** usuário descreve a US, cola link do Azure DevOps/Jira ou fornece o conteúdo dos arquivos de requisitos no chat
   - **Opção 2 — Listar USs/PBIs/Enables existentes na pasta `US/`:** listar os itens encontrados em `fastqa/manual_test/US/` para o usuário selecionar
5. Após receber a US, usar o template correspondente como modelo para geração dos casos
6. **REGRA CRÍTICA (Gherkin):** Keywords em INGLÊS + conteúdo em PORTUGUÊS
7. **REGRA CRÍTICA (Step by Step):** idioma definido pelo wizard em tempo de execução
8. Salvar casos em: `fastqa/manual_test/test_cases/{nome-da-funcionalidade}/`
   - Gherkin: `[US-ID].feature`
   - Step by Step: `[US-ID].md`

**Pré-requisitos:**
- User Story disponível (Azure DevOps ou documento)
- Recomendado: executar pipeline completo (`load_pbi` → `identify_gaps` → `analyze_requirements` → `map_behaviors`)

---

### 📝 `test_case_with_playwright_mcp` — Geração de Casos de Teste com Playwright MCP

Gera cenários de teste em formato Gherkin a partir de User Stories com o apoio do Playwright MCP para explorar a aplicação.

**Template:** `fastqa/agents/core/fastqa_2.1_gherkin_writer.md`

**Workflow:**
1. Solicitar identificação da User Story (US) a ser utilizada e **AGUARDAR** resposta
2. Perguntar se existe a URL da aplicação onde os testes serão executados:
   - Se **Sim** → prosseguir para 2.1
   - Se **Não** → pular para passo 3
3. **2.1.** Solicitar a URL
4. **2.2.** Perguntar se deve ser utilizada a Extensão Chrome do Playwright. Se sim, pedir para habilitar e **AGUARDAR** resposta
5. **2.3.** Utilizar o Playwright MCP: `playwright-web` do arquivo `.vscode/mcp.json` para explorar a URL e focar na geração dos cenários conforme a US informada
6. Usar o template como modelo para geração dos cenários
7. **REGRA CRÍTICA:** Keywords em INGLÊS + conteúdo em PORTUGUÊS
8. Salvar cenários em um único arquivo em: `fastqa/manual_test/test_cases/`
   - Nome do arquivo: `[US-ID].feature`

**Pré-requisitos:**
- User Story disponível (Azure DevOps ou documento)
- MCP Playwright configurado em `.vscode/mcp.json`
- Recomendado: executar pipeline completo

---

## 📋 Comandos — Geração de Cenários API

### 🔌 `api_generate_scenarios` — Geração de Cenários Gherkin para API

Gera cenários de teste em formato Gherkin para APIs REST a partir de um cURL ou URL de documentação (Swagger/OpenAPI).

**Template:** `fastqa/agents/core/fastqa_2.1_api_gherkin_writer.md`

**Workflow:**
1. Solicitar input do usuário e **AGUARDAR** resposta:
   - **Opção 1:** cURL de exemplo da API
   - **Opção 2:** URL da documentação Swagger/OpenAPI

**Workflow:**
1. Solicitar input do usuário e **AGUARDAR** resposta:
   - **Opção 1:** cURL de exemplo da API
   - **Opção 2:** URL da documentação Swagger/OpenAPI
2. Analisar o input:
   - Se **cURL**: extrair método HTTP, URL, headers, body
   - Se **URL Swagger**: navegar e mapear endpoints disponíveis
3. Gerar cenários Gherkin seguindo padrão REST:
   - Mapear `Given` → pré-condições (autenticação, dados de entrada)
   - Mapear `When` → ação HTTP (`GET`, `POST`, `PUT`, `DELETE`)
   - Mapear `Then` → validações (status code, response body, headers, schema)
4. Incluir tags obrigatórias: `@api @{método} @{categoria}`
   - Categorias: `@smoke`, `@positive`, `@negative`, `@error`, `@security`, `@validation`
5. **REGRA CRÍTICA:** Keywords em INGLÊS + conteúdo em PORTUGUÊS
6. Salvar cenários em: `fastqa/manual_test/test_cases/api/{nome-recurso}.feature`
   - Nomenclatura: `{verbo}-{recurso}.feature` (ex: `get-users.feature`, `post-books.feature`)

**Padrão de Nomenclatura de Arquivos:**
```
manual_test/test_cases/api/
├── get-users.feature        # GET /api/users
├── post-users.feature       # POST /api/users
├── put-users.feature        # PUT /api/users/:id
├── delete-users.feature     # DELETE /api/users/:id
└── get-books.feature        # GET /api/books
```

**Exemplo — Geração a partir de cURL:**

Input:
```bash
curl -X GET "https://api.example.com/api/books" \
  -H "Authorization: Bearer token123" \
  -H "Accept: application/json"
```

Output esperado (`get-books.feature`):
```gherkin
@api @get @books @smoke
Feature: API - Consulta de livros
  Como um usuário autenticado da API
  Eu quero consultar a lista de livros disponíveis
  Para que eu possa visualizar o catálogo completo

  Background:
    Given que o usuário está autenticado com token válido
    And que a base URL é "https://api.example.com"

  @positive @smoke
  Scenario: Consultar lista de livros com sucesso
    When o usuário envia uma requisição GET para "/api/books"
    Then o status code da resposta deve ser 200
    And o response body deve conter uma lista de livros
    And cada livro deve conter os campos "id", "title", "author"

  @negative @error
  Scenario: Consultar livros sem autenticação
    Given que o usuário NÃO está autenticado
    When o usuário envia uma requisição GET para "/api/books"
    Then o status code da resposta deve ser 401
    And o response body deve conter a mensagem "Unauthorized"

  @negative @error
  Scenario: Consultar livros com token expirado
    Given que o usuário está autenticado com token expirado
    When o usuário envia uma requisição GET para "/api/books"
    Then o status code da resposta deve ser 401
    And o response body deve conter a mensagem "Token expired"

  @security
  Scenario: Validar headers de segurança na resposta
    When o usuário envia uma requisição GET para "/api/books"
    Then o status code da resposta deve ser 200
    And o header "Content-Type" deve ser "application/json"
    And o header "X-Content-Type-Options" deve ser "nosniff"
```

**Exemplo — Geração a partir de URL Swagger:**

Input: `https://api.example.com/swagger`

Output esperado (`crud-users.feature`):
```gherkin
@api @crud @users
Feature: API - CRUD de Usuários
  Como um administrador da API
  Eu quero gerenciar usuários via endpoints REST
  Para manter o cadastro atualizado

  Background:
    Given que o usuário está autenticado como administrador
    And que a base URL é "https://api.example.com"

  @get @positive
  Scenario: Listar todos os usuários
    When o usuário envia uma requisição GET para "/api/users"
    Then o status code da resposta deve ser 200
    And o response body deve conter uma lista de usuários

  @post @positive
  Scenario: Criar um novo usuário com dados válidos
    When o usuário envia uma requisição POST para "/api/users" com body:
      | campo    | valor              |
      | name     | João Silva         |
      | email    | joao@email.com     |
      | role     | user               |
    Then o status code da resposta deve ser 201
    And o response body deve conter o campo "id"

  @put @positive
  Scenario Outline: Atualizar dados de um usuário existente
    Given que existe um usuário com id "<id>"
    When o usuário envia uma requisição PUT para "/api/users/<id>" com body:
      | campo | valor   |
      | name  | <nome>  |
    Then o status code da resposta deve ser 200
    And o campo "name" no response deve ser "<nome>"

    Examples:
      | id | nome           |
      | 1  | Maria Santos   |
      | 2  | Pedro Oliveira |

  @delete @positive
  Scenario: Remover um usuário existente
    Given que existe um usuário com id "99"
    When o usuário envia uma requisição DELETE para "/api/users/99"
    Then o status code da resposta deve ser 204
```

**Pré-requisitos:**
- Nenhum obrigatório (pode ser executado de forma independente)
- Recomendado: documentação Swagger/OpenAPI disponível

---

### 🔍 `exploratory_api_test` — Testes Exploratórios de API com Heurísticas

Executa testes exploratórios de API utilizando heurísticas estruturadas (**POISED** ou **VADER**) para descobrir comportamentos não óbvios, edge cases e vulnerabilidades.

**Template:** `fastqa/agents/core/fastqa_2.3_exploratory_api_test.md`

**Workflow:**
1. Perguntar abordagem de execução e **AGUARDAR** resposta:
   - **Opção 1:** Com Swagger UI (via Playwright MCP) — Recomendado
   - **Opção 2:** Chamadas diretas à API (fallback)
2. Perguntar qual heurística usar e **AGUARDAR** resposta:
   - **POISED:** Parameters, Output, Interoperability, Security, Error, Data (testes abrangentes)
   - **VADER:** Verbs, Authorization, Data, Errors, Responsiveness (testes focados)
3. Se Opção 1 (Swagger):
   - Validar MCP Playwright habilitado (servidor `playwright-exploratory` ou similar)
   - Solicitar URL do Swagger
   - Listar recursos disponíveis
   - Usuário seleciona recurso para testar
   - Executar testes exploratórios conforme heurística selecionada
   - Capturar screenshots de cada teste
4. Se Opção 2 (Direto):
   - Solicitar URL base da API e endpoints
   - Executar testes via PowerShell/cURL
   - Capturar responses e curl commands
5. Gerar relatório consolidado em: `manual_test/evidence/api/exploratory-{recurso}-{timestamp}/report.md`
6. Salvar evidências por heurística aplicada

**Heurísticas:**

**POISED (Comprehensive):**
- **P**arameters — Valores válidos/inválidos, limites, tipos
- **O**utput — Formato, estrutura, informações
- **I**nteroperability — Compatibilidade, padrões
- **S**ecurity — Autenticação, autorização, proteção
- **E**rror — Tratamento de exceções, recovery
- **D**ata — Qualidade, integridade, escalabilidade

**VADER (Focused):**
- **V**erbs — Métodos HTTP (GET, POST, PUT, DELETE, PATCH)
- **A**uthorization — Tokens, API keys, permissões
- **D**ata — Tipagem, paginação, formato, tamanho
- **E**rrors — Códigos HTTP, mensagens de erro
- **R**esponsiveness — Performance, concorrência, timeout

**Pré-requisitos:**
- [Se Swagger] MCP Playwright configurado e ativo
- URL da API (Swagger ou endpoint base)
- **⚠️ IMPORTANTE:** Executar apenas em ambiente de **teste/development** (não produção)

---

### 💣 `destructive_api_test` — Testes Destrutivos de API

Executa testes destrutivos para encontrar fraquezas, pontos de falha e vulnerabilidades em APIs REST sob condições adversas.

**Template:** `fastqa/agents/core/fastqa_2.4_destructive_api_test.md`

**Workflow:**
1. **⚠️ VALIDAÇÃO OBRIGATÓRIA:** Confirmar ambiente de teste/desenvolvimento
   - Perguntar: "Confirma que está testando em ambiente SEGURO (não produção)?"
   - **AGUARDAR** resposta afirmativa antes de prosseguir
   - Se negativa: Cancelar execução
2. Perguntar abordagem de execução e **AGUARDAR** resposta:
   - **Opção 1:** Com Swagger UI (via Playwright MCP)
   - **Opção 2:** Chamadas diretas à API
3. Solicitar URL e recurso/endpoint para testar
4. Executar 7 categorias de testes destrutivos:
   - **1. Injeção de Código:** SQL, XSS, Command Injection, JSON Injection
   - **2. Malformação de Dados:** JSON/XML inválido, encoding incorreto
   - **3. Sobrecarga de recursos:** Payloads grandes, loops infinitos, requisições massivas
   - **4. Manipulação de headers:** Content-Type incorreto, headers gigantes, ausência de headers obrigatórios
   - **5. Ataques de autenticação:** Tokens inválidos, expirados, manipulados, replay attacks
   - **6. Path traversal:** `../../../etc/passwd`, manipulação de IDs, IDOR
   - **7. Race conditions:** Requisições simultâneas, concorrência, duplo submit
5. Para cada teste:
   - Enviar payload destrutivo
   - Capturar response (status code, body, headers)
   - Documentar se API está vulnerável ou protegida
   - Salvar evidência com classificação de severidade
6. Gerar relatório de vulnerabilidades em: `manual_test/evidence/api/destructive-{recurso}-{timestamp}/vulnerabilities-report.md`
7. Classificar vulnerabilidades encontradas:
   - 🔴 **CRÍTICA:** Exploração direta possível (SQL Injection, XSS funcionando)
   - 🟠 **ALTA:** Exposição de informações sensíveis, IDOR permitido
   - 🟡 **MÉDIA:** Falha no tratamento de erro, stack trace exposto
   - 🟢 **BAIXA:** Rate limiting ausente, headers de segurança faltando

**Categorias de Testes:**

| Categoria | Testes Executados | Vulnerabilidades Buscadas |
|-----------|------------------|---------------------------|
| **Injeção** | SQL, XSS, Command, JSON | Execução de código arbitrário |
| **Malformação** | JSON/XML quebrado, encoding | Parser crash, erro 500 |
| **Sobrecarga** | Payloads grandes (10MB+) | DoS, timeout, memory leak |
| **Headers** | Content-Type errado, headers gigantes | Bypass de validação |
| **Auth** | Token inválido, replay attack | Acesso não autorizado |
| **Path** | `../`, IDOR, manipulação de IDs | Acesso a recursos alheios |
| **Race** | Requisições simultâneas | Duplicatas, inconsistência |

**Pré-requisitos:**
- [Se Swagger] MCP Playwright configurado
- **⚠️ OBRIGATÓRIO:** Ambiente de teste/desenvolvimento
- **⚠️ PROIBIDO:** Execução em produção
- Autorização para executar testes destrutivos

---

## 📋 Comandos — Validação de Cenários

### ✅ `validate_scenarios` — Validação de Cenários Gherkin

Valida qualidade, cobertura e automabilidade dos cenários Gherkin gerados (Web e API).

**Template:** `fastqa/agents/core/fastqa_2.2_validator.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar identificação da User Story (US) a ser utilizada e **AGUARDAR** resposta
3. Carregar cenários de: `fastqa/manual_test/test_cases/`
4. Executar 5 fases de validação:
   - **Fase 1:** Análise de cobertura funcional
   - **Fase 2:** Validação de automabilidade
   - **Fase 3:** Auditoria de qualidade Gherkin
   - **Fase 4:** Matriz de rastreabilidade
   - **Fase 5:** Análise de lacunas
5. Gerar relatório com score (meta: ≥95/100)
6. Salvar cenários validados em: `fastqa/manual_test/test_cases/`

**Pré-requisitos:**
- Cenários Gherkin gerados (via `test_case_with_fastqa`, `test_case_with_playwright_mcp` ou `api_generate_scenarios`)

---

## 🔄 Fluxo Recomendado — Fase 2

```
[Vindo da Fase 1 → 01-fastqa-requirements.instructions.md]
        ↓
@fastqa:ac_scope_analysis  ← NOVO (define escopo de ACs)
        ↓
┌─── Web ────────────────────────────────────┐
│ @fastqa:test_case_with_fastqa              │
│   ou                                       │
│ @fastqa:test_case_with_playwright_mcp      │
└────────────────────────────────────────────┘
        ↓
┌─── API ────────────────────────────────────┐
│ @fastqa:api_generate_scenarios             │
└────────────────────────────────────────────┘
        ↓
@fastqa:validate_scenarios
        ↓
[Próxima fase → 03-fastqa-execution.instructions.md]
```

---

**Versão:** 5.1 | **Atualização:** 12 de Março de 2026
