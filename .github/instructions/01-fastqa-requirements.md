---
description: FastQA — Fase 0-1: Carregamento de Dados e Análise de Requisitos.
applyTo: '**'
tools: ['azureDevOps', 'memory', 'sequential-thinking']
---

# FastQA — Fase 0-1: Carregamento de Dados e Análise de Requisitos

> **Arquivo:** `01-fastqa-requirements.instructions.md`
> **Escopo:** Comandos de carregamento de dados (Fase 0) e análise de requisitos (Fase 1)
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

## 📋 Comandos — Fase 0: Pré-flight (Diagnóstico)

### 🔌 `azdo_health` — Diagnóstico da Integração Azure DevOps

Valida se o Azure DevOps está corretamente configurado antes de qualquer operação dependente.

**Template:** `fastqa/agents/core/fastqa_0.0_azdo_health.md`

**Workflow:**
1. Executar `check-health.command.ts` para verificar `.env`, variáveis e conectividade REST
2. Se todos os checks OK → confirmar e indicar próximo step (`@fastqa:load_pbi`)
3. Se algum check falhou → perguntar ao usuário:
   - **Sim** usar Azure DevOps → exibir passo-a-passo de configuração (`.env`, MCP, PAT)
   - **Não** → fallback documental: verificar/orientar criação de `fastqa/manual_test/US/PBI-{ID}.md`

**Pré-requisitos:**
- Pasta `fastqa/` inicializada no workspace
- Arquivo `fastqa/.env.example` presente (copiado pelo setup)

---

## 📋 Comandos — Fase 0: Carregamento dos Dados

### 📌 `load_pbi` — Carregamento de PBI do Azure DevOps

Carrega um Product Backlog Item (PBI) do Azure DevOps **ou de documentação local** e prepara os dados para o pipeline de QA.

**Template:** `fastqa/agents/core/fastqa_0.1_pbi_loader.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar ID do PBI ou URL do work item e **AGUARDAR** resposta do usuário
3. Verificar se MCP Azure DevOps está ativo e `azure_devops.enabled = true` em `project_config.json`
4. **Se MCP disponível:** carregar via MCP e salvar em memória como `pbi.current`
5. **Se MCP indisponível:** perguntar se o usuário quer usar AzDO (orienta `@fastqa:azdo_health`) ou usar fallback local (`fastqa/manual_test/US/`)
6. Exibir resumo dos dados carregados

**Pré-requisitos:**
- `@fastqa:azdo_health` executado com êxito (se usando AzDO)
- **OU** arquivo `fastqa/manual_test/US/PBI-{ID}.md` presente (se usando fallback local)
- ID ou URL do PBI disponível

---

## 📋 Comandos — Fase 1: Análise de Requisitos

### 🔍 `identify_gaps` — Identificação de Gaps em Requisitos

Analisa requisitos e identifica inconsistências, gaps e ambiguidades através de perguntas diretas.

**Template:** `fastqa/agents/core/fastqa_1.1_gap_identifier.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar no chat a US ou PBI que deve ser carregada e **AGUARDAR** resposta do usuário
3. Carregar requisitos (PBI, User Story ou documento)
4. Gerar lista numerada de perguntas sobre gaps identificados
5. Salvar análise em: `fastqa/manual_test/gap_analysis/`

**Pré-requisitos:**
- Requisitos disponíveis (carregados via `load_pbi` ou fornecidos manualmente)

---

### 📊 `estimate_effort` — Estimativa de Esforço de Testes

Gera estimativas de esforço de testes e planejamento de massa de dados para fase de Refinamento.

**Template:** `fastqa/agents/core/fastqa_1.2_refinement.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar no chat a US ou PBI que deve ser carregada e **AGUARDAR** resposta do usuário
3. Analisar requisitos validados (após `identify_gaps`)
4. Gerar cenários preliminares e estimativas de:
   - Tempo de revisão
   - Preparação de massa de dados
   - Tempo de execução
5. Salvar planejamento em: `fastqa/manual_test/estimate_effort/`

**Pré-requisitos:**
- Requisitos validados (recomendado executar `identify_gaps` primeiro)

---

### 📋 `analyze_requirements` — Análise e Estruturação de Requisitos

Estrutura requisitos em formato claro e testável, preparando para geração de cenários BDD.

**Template:** `fastqa/agents/core/fastqa_1.3_requirements_analyzer.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar no chat a US ou PBI que deve ser carregada e **AGUARDAR** resposta do usuário
3. Decompor requisitos em unidades atômicas
4. Eliminar ambiguidades linguísticas
5. Estabelecer rastreabilidade clara
6. Salvar análise em: `fastqa/manual_test/requirements_analysis/`

**Pré-requisitos:**
- Requisitos validados (recomendado executar `identify_gaps` primeiro)

---

### 🧩 `map_behaviors` — Mapeamento de Comportamentos

Decompõe requisitos em comportamentos testáveis com cobertura completa (fluxos principal, alternativos e exceções).

**Template:** `fastqa/agents/core/fastqa_1.4_behavior_specialist.md`

**Workflow:**
1. Se prefixo `@fastqa_code:` → ativar TEA primeiro
2. Solicitar no chat a US ou PBI que deve ser carregada e **AGUARDAR** resposta do usuário
3. Carregar requisitos estruturados (de `analyze_requirements`)
4. Mapear comportamentos sentença por sentença:
   - Fluxo principal
   - Fluxos alternativos
   - Fluxos de exceção
5. Aplicar técnicas de teste (particionamento, valor limite, tabela de decisão)
6. Salvar mapeamento em: `fastqa/manual_test/behavior_analysis/`

**Pré-requisitos:**
- Requisitos estruturados (recomendado executar `analyze_requirements` primeiro)

---

## 🔄 Fluxo Recomendado — Fases 0-1

```
@fastqa:load_pbi (ou fornecimento manual)
        ↓
@fastqa:identify_gaps
        ↓
@fastqa:estimate_effort (para Refinamento)
        ↓
@fastqa:analyze_requirements
        ↓
@fastqa:map_behaviors
        ↓
[Próxima fase → 02-fastqa-test-design.instructions.md]
```

---

**Versão:** 5.0 | **Atualização:** 21 de Fevereiro de 2026
