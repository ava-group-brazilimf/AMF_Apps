---
name: "fastqa_6.3_execute_regression_plan"
description: "Executa o plano de regressão gerado pelo regression_analyze, roda os testes e gera relatório de execução com análise AI de falhas"

tools:
  - run_in_terminal
  - get_terminal_output
  - memory
  - sequential-thinking
---

# Template: Executor de Plano de Regressão

## 🎯 Objetivo
Receber um plano de regressão (Markdown gerado por `@fastqa:regression_analyze`), verificar alertas de impacto global, executar os testes localmente ou via pipeline, cruzar resultados com o plano original, analisar falhas com IA e gerar relatório de execução completo.

> **REGRA CRÍTICA:** Se após análise semântica (Step 1.5) a IA concluir que há risco funcional real, o escopo de execução DEVE ser escalado para TODOS os testes (e2e + api + unit). Os testes mapeados no plano servem como prioridade de análise de falhas, NÃO como filtro de execução. A presença de alertas globais **por si só** não implica escalação — a IA deve avaliar o conteúdo dos diffs.

**Contexto:** Este agent lê o plano de regressão (Markdown) de `fastqa/manual_test/regression_analysis/` e usa `fastqa/scripts/project_config.json` para configuração de framework/paths.

---

## 📥 Entrada

### Parâmetros Aceitos
```typescript
{
  planPath?: string;      // Caminho do plano de regressão (.md ou .json)
  mode?: 'local' | 'pipeline';   // Modo de execução (default: local)
  layer?: string;         // Filtro de layer: e2e, api, unit, all (default: all)
}
```

### Validações
1. Verificar se existe pelo menos um plano em `fastqa/manual_test/regression_analysis/`
2. Ler `fastqa/scripts/project_config.json` para obter framework e caminhos
3. Verificar se dependências do framework estão instaladas (node_modules)

---

## 📤 Saída (Contrato)

### Sucesso
- Relatório Markdown salvo em `fastqa/manual_test/regression_analysis/PR-{id}_execution_report_{timestamp}.md`
- Relatório JSON salvo ao lado para consumo programático
- Resumo apresentado no chat com resultados por área e análise de falhas

### Erro
- Mensagem clara com ações sugeridas (instalar dependências, gerar plano primeiro, etc.)

---

## 🔄 Fluxo de Execução

### 1️⃣ Localizar Plano de Regressão

- Listar arquivos em `fastqa/manual_test/regression_analysis/` que contenham `regression_plan` (`.md` ou `.json`):
  ```bash
  ls fastqa/manual_test/regression_analysis/*regression_plan*
  ```
- **Se múltiplos planos encontrados:** Apresentar lista numerada ao usuário e **AGUARDAR** escolha:
  ```
  📋 Planos de regressão disponíveis:
  
    1. PR-90468_regression_plan.md (14/04/2026)
    2. PR-90421_regression_plan.md (12/04/2026)
  
  Qual plano deseja executar? (número ou caminho)
  ```

- **Se nenhum plano encontrado:**
  ```
  ⚠️ Nenhum plano de regressão encontrado em fastqa/manual_test/regression_analysis/.
  
  Execute primeiro: @fastqa:regression_analyze
  ```
  - Encerrar.

- **Se o usuário informou o caminho diretamente:** Usar o caminho fornecido.

### 1️⃣.5️⃣ Analisar Risco Real do Plano (Decisão de Escopo pela IA)

> **Esta etapa é uma ANÁLISE SEMÂNTICA, não uma regra mecânica.**
> A IA deve LER o plano completo, COMPREENDER o que mudou, e DECIDIR se faz sentido
> escalar o escopo para todos os testes ou executar apenas os mapeados.

#### O que ler no plano

Usar `read_file` no arquivo `PR-{id}_regression_plan.md` e processar as seguintes informações:

1. **Seção de Alertas Globais** — Identificar se existem alertas `🔴 global-impact` ou `🔴 global-trigger`
2. **Seção "Risco Consolidado do PR"** — Ler a classificação geral da IA que gerou o plano (🟢/🟡/🟠/🔴)
3. **Seção "Análise de Impacto por Arquivo"** — Ler as classificações individuais (`cosmetic_change`, `functional_change`, `config_change`, `refactor_change`) e as justificativas com citação dos diffs
4. **Bloco `<!-- ai_risk_context -->`** (se existir) — Contexto estruturado com `risk_level`, `all_diffs_cosmetic`, `summary` — serve como ponto de partida para a análise, mas a IA faz sua própria avaliação

#### Como raciocinar

A IA deve responder a estas perguntas sobre o plano, **citando evidências**:

- **As mudanças alteram comportamento funcional?** Comentários, espaçamento e formatação NÃO alteram. Mudança em lógica, validação, query, configuração de features SIM.
- **Os alertas globais refletem risco real?** Um alerta em `config/default.yml` por adicionar um comentário NÃO é risco real. Um alerta em `config/default.yml` por mudar `application.domain` ou desabilitar um feature flag É risco real.
- **A classificação do agent 6.1 faz sentido?** Se o plano diz "🟢 Risco Nenhum" e todos os diffs citados são comentários, a IA deve concordar. Se disser "🟢 Nenhum" mas houver mudança em query SQL, a IA deve discordar e escalar.

#### Decidir e comunicar

Após raciocinar, a IA toma a decisão:

**Se a IA concluir que há risco real** → `ESCALATION_MODE = true`
- Informar ao usuário com justificativa própria:
  ```
  🚨 Escalação de Escopo — Risco Real Identificado
  
  {explicação em 2-3 frases do que a IA encontrou e por que escalar}
  
  ➡️ Executando TODOS os testes (e2e + api + unit).
  ➡️ Testes mapeados no plano serão priorizados na análise de falhas.
  ```

**Se a IA concluir que NÃO há risco real** (mesmo com alertas globais) → `ESCALATION_MODE = false`
- Informar ao usuário:
  ```
  ℹ️ Alertas globais presentes, porém sem risco funcional.
  
  {explicação em 2-3 frases: quais alertas existem, por que a IA considera que não representam risco}
  
  ➡️ Executando apenas os testes mapeados no plano.
  💡 Para forçar escalação completa, informe: "forçar escalação"
  ```

**Se não houver alertas globais** → `ESCALATION_MODE = false`
- Prosseguir diretamente para Step 2

> **Princípios da decisão:**
> - A IA NÃO escala automaticamente por presença de alertas — ela **avalia o conteúdo** dos alertas
> - A IA PODE discordar do risco atribuído pelo agent 6.1 se, ao ler os diffs, encontrar evidência diferente
> - A IA DEVE citar trechos concretos dos diffs na justificativa (ex: "o diff em `config/default.yml` é `+ // fastqa-regression-sim`, apenas um comentário")
> - Se o usuário pedir "forçar escalação", escalar independente da análise

### 2️⃣ Escolher Modo e Filtros

- **Se `ESCALATION_MODE = true`:**
  - O escopo já está definido como **TODOS os testes, todas as layers**
  - Perguntar **apenas o modo** de execução:
    ```
    ⚙️ Modo de execução (escopo já definido: TODOS os testes):
    
    🖥️ Local — Executar na máquina (requer framework instalado)
    ☁️ Pipeline — Disparar pipeline no Azure DevOps
    
    O que prefere?
    ```

- **Se `ESCALATION_MODE = false`:**
  - Perguntar modo E escopo ao usuário:
    ```
    ⚙️ Configuração da execução:
    
    1. **Modo:**
       🖥️ Local — Executar testes na máquina (requer framework instalado)
       ☁️ Pipeline — Disparar pipeline no Azure DevOps (requer pipeline configurada)
    
    2. **Escopo:**
       🎯 Todos os testes do plano (padrão)
       🔴 Apenas alta prioridade (critical + high)
       📦 Apenas uma layer (e2e / api / unit)
    
    O que prefere? (pode combinar, ex: "local, só high, layer e2e")
    ```

- Se o usuário não especificar, usar: **modo local, todos os testes do plano, todas as layers.**

### 3️⃣a Execução Local

#### 3.1 — Verificar Pré-requisitos

- Ler `fastqa/scripts/project_config.json` → extrair `automation_framework`, `automation_root`
- Verificar se `node_modules` existe no `automation_root`:
  ```bash
  test -d fastqa/automated_test/node_modules && echo "OK" || echo "MISSING"
  ```
- Se `MISSING`:
  ```
  ⚠️ Dependências não instaladas. Executando npm install...
  ```
  - Executar: `cd fastqa/automated_test && npm install`

#### 3.2 — Executar Testes via Terminal

> **Não há script de execução dedicado.** O agent executa diretamente via `run_in_terminal` usando os comandos do framework do projeto.

##### a) Detectar framework e construir comandos

**Ler** `fastqa/scripts/project_config.json` → campo `automation_framework` e `automation_language`.
Adaptar o comando de execução conforme o framework configurado:

| Framework | Executar TODOS | Executar specs filtrados |
|-----------|---------------|-------------------------|
| **Cypress** (TS/JS) | `npx cypress run` | `npx cypress run --spec "spec1.ts,spec2.ts"` |
| **Playwright** (TS/JS) | `npx playwright test` | `npx playwright test spec1.ts spec2.ts` |
| **Jest** (TS/JS) | `npx jest` | `npx jest --testPathPattern "spec1\|spec2"` |
| **Mocha** (TS/JS) | `npx mocha "test/**/*.spec.ts"` | `npx mocha spec1.ts spec2.ts` |
| **Frisby** (JS) | `npm run frisby` | `npm run frisby -- --grep "spec1\|spec2"` |
| **Robot Framework** (Python) | `robot tests/` | `robot --include tag1 tests/` |
| **pytest** (Python) | `pytest` | `pytest spec1.py spec2.py` |

> Se o framework não estiver na tabela, ler a documentação do `package.json` (scripts) e inferir o comando correto.
> Se não for possível inferir, perguntar ao usuário: "Qual comando executa seus testes?"

##### b) Extrair lista de specs do plano

Para obter os specs a executar, ler no plano MD a seção `## 🏷️ Comandos de Execução` (ou `## 6. Comandos de Execução`):
- Dentro dos blocos ` ```bash `, extrair os paths de spec dos argumentos `--spec`, `--testPathPattern` ou paths soltos
- Agrupar por layer (e2e, api, unit) conforme labels/comentários do bloco
- Se a seção não existir ou não for parseável, fazer fallback: ler o JSON (`PR-{id}_regression_plan.json`) → campo `tests[]` → extrair `test_path` de cada item

##### c) Executar conforme modo de escalação

**Se `ESCALATION_MODE = true` (risco real confirmado pela IA):**
- Executar ALL layers sequencialmente usando o comando "TODOS" da tabela acima
- **NUNCA** usar `--spec` ou filtros quando em modo escalação global

**Se `ESCALATION_MODE = false`:**
- Executar apenas os specs extraídos no passo (b), agrupados por layer
- Usar o comando "filtrado" da tabela acima

##### d) Monitoramento

- Monitorar a saída em tempo real no terminal
- Aguardar conclusão (pode demorar vários minutos)
- **Timeout:** Se a execução exceder **15 minutos** sem produzir novo output, interromper e informar:
  ```
  ⏰ Execução sem output há 15 minutos. Possível travamento.
  
  Sugestões:
    1. Reduza o escopo: informe "apenas e2e" ou "apenas high"
    2. Verifique se o servidor da aplicação está rodando
    3. Verifique logs no terminal para erros silenciosos
  ```

#### 3.3 — Coletar Resultados

- Parsear saída do terminal para extrair: total, passed, failed, skipped
- Agrupar resultados por layer (unit, api, e2e)
- Identificar quais specs falharam

### 3️⃣b Execução via Pipeline

> ⚠️ **Em desenvolvimento.** Este modo requer integração com pipelines Azure DevOps que ainda não estão implementadas.
> Por enquanto, usar **modo Local** (3a). Se o usuário solicitar pipeline, informar:

```
⚠️ Execução via Pipeline ainda não está disponível.

A integração com Azure Pipelines será implementada em versão futura.
Por enquanto, use o modo Local para executar os testes.

Alternativa: Configure e dispare a pipeline manualmente no Azure DevOps
com os specs listados abaixo, depois use @fastqa:azdo_sync_pipeline_results
para importar os resultados.
```

**Quando implementado, o fluxo será:**

#### 3b.1 — Montar Variáveis de Pipeline

- Ler o plano JSON e extrair:
  - Lista de specs agrupados por layer
  - Tags de área para filtro
- Montar variáveis:
  ```
  SPECS_E2E = "login.spec.ts,register.spec.ts,..."
  SPECS_API = "loginApiSpec.ts,userApiSpec.ts,..."
  SPECS_UNIT = "insecuritySpec.ts,..."
  ```

#### 3b.2 — Disparar Pipeline

- Usar comando de trigger de pipeline (a ser implementado) com as variáveis montadas
- Aguardar conclusão com polling

#### 3b.3 — Verificar Resultados

- Usar `@fastqa:azdo_sync_pipeline_results` para importar resultados da pipeline
- Cross-referenciar resultados com o plano de regressão

### 4️⃣ Enriquecimento IA — Análise de Falhas

> **Este passo é o diferencial do execute_regression_plan**: a IA analisa cada falha com contexto do código.
> **Prioridade de análise**: Quando em `ESCALATION_MODE = true`, os testes são divididos em dois grupos:

#### Grupo A — Testes Mapeados no Plano (prioridade alta de análise)

São os testes listados na seção "Testes Impactados" do plano de regressão. Falhas nesses testes recebem **análise detalhada** com contexto do PR.

**Como correlacionar resultado de teste com o plano:**
- Extrair o **basename** do spec que falhou (ex: resultado `login.spec.ts` → basename `login.spec`)
- Buscar no plano (JSON `tests[]` ou tabela MD) um `test_path` que contenha esse basename
- Se match encontrado → é teste mapeado (Grupo A). Se não → é teste fora do plano (Grupo B)

**Para cada teste mapeado que FALHOU:**

1. **Ler o arquivo de teste** via `read_file`:
   - Usar `file_search` com o basename para encontrar o path completo no workspace
   - Identificar o que o teste valida (assertions, steps)

2. **Ler o arquivo da app** que disparou o teste:
   - Extrair o `sourceFile` da entrada correspondente no plano (campo do JSON ou citado na tabela MD)
   - Se `app_repo_path` estiver configurado em `project_config.json`, usar `read_file` no path combinado
   - Se o arquivo não for acessível, usar os **diffs do plano MD** (seção "Análise de Impacto por Arquivo") como contexto

3. **Classificar a falha** — a IA deve raciocinar usando as heurísticas abaixo:

   | Categoria | Heurísticas para identificar | Ação Recomendada |
   |-----------|------------------------------|------------------|
   | 🐛 **Bug Real** | Assertion falha em lógica de negócio (status code, valor calculado, permissão) **E** o PR alterou arquivo diretamente relacionado (verificar diffs do plano). Ex: "Expected 200 got 401" + PR alterou `routes/login.ts` → 🐛 | Reportar ao dev / criar bug |
   | 🔧 **Teste Quebrado** | Assertion falha por valor hardcoded desatualizado, selector CSS/XPath não encontrado na página, elemento `.should('exist')` ausente, dados de teste obsoletos. O código da app não foi alterado nessa área pelo PR. | `@fastqa:verify_and_fix` |
   | 🌐 **Ambiente** | Erro de conexão (`ECONNREFUSED`, `ENOTFOUND`), timeout genérico (`Timed out after 30000ms`), `net::ERR_CONNECTION_REFUSED`, `503 Service Unavailable`, database lock, porta em uso | Verificar ambiente e re-executar |
   | 🤷 **Inconclusivo** | Erro intermitente (passa em re-run), stack trace sem relação clara com diffs do PR, arquivo de teste ou app não acessível para leitura | Executar manualmente e investigar |

   > **Regra de desempate:** Se a causa não for clara, cruzar com os diffs do plano. Se o PR **alterou** o arquivo que o teste valida → preferir 🐛. Se o PR **NÃO** alterou → preferir 🔧 ou 🌐.

4. **Gerar análise estruturada:**
   ```
   ❌ loginApiSpec.ts — FALHOU (🎯 teste mapeado — análise detalhada)
      Categoria: 🐛 Bug Real
      Erro: "Expected status 200 but got 401"
      Análise: A alteração em /routes/login.ts modificou a validação de token.
               O teste espera resposta 200 para credenciais válidas, mas a nova
               lógica requer header "X-Auth-Version: 2" que o teste não envia.
      Ação: Reportar ao dev — a mudança de contrato de API pode afetar clientes.
   ```

#### Grupo B — Testes Não-Mapeados (análise simplificada)

São testes que não estavam no plano, executados em modo escalação global. Falhas nesses testes recebem **análise resumida**:

```
❌ basketApiSpec.ts — FALHOU (teste fora do plano — análise simplificada)
   Erro: "Expected status 200 but got 500"
   Ação sugerida: Verificar se é regressão indireta da alteração global.
```

**Regras:**
- Máximo 10 falhas de testes mapeados analisadas em detalhe
- Máximo 5 falhas de testes não-mapeados com análise simplificada (se mais, resumir)
- Se o arquivo de teste ou app não for acessível, classificar como "Inconclusivo"
- Ser conservador: preferir "Bug Real" quando a causa aponta para alteração no PR

### 5️⃣ Apresentar Resultado

Apresentar no chat com resultados e análise AI:

```
📊 Execução de Regressão — PR #{id}

📌 {título do PR}
   Modo: 🖥️ Local | ☁️ Pipeline
   Escalação: {🔴 Global Impact → Suite Completa | ⚪ Sem escalação → Testes mapeados}
   Duração: {tempo total}

📋 Resumo:
   Planejados:     {N}
   Executados:     {N}
   ✅ Passou:      {N}
   ❌ Falhou:      {N}
   ⏭️ Skipped:     {N}
   ⚠️ Não encontr.: {N}
   Taxa de sucesso: {X}%

{barra visual: 🟩🟩🟩🟩🟩🟩🟩🟩🟥🟥⬜ 80%}
```

**Se houve falhas (Seção 🔴):**
```
🔴 Falhas em Testes de Alta Prioridade:
   ❌ [critical] loginTest.spec.ts — Expected status 200, got 401
   ❌ [high] paymentApiSpec.ts — Timeout after 30000ms

🧠 Análise de Falhas (por IA):
   {análise detalhada da etapa 4}
```

**Resultados por área:**
```
📋 Resultados por Área:
   ✅ user (10/12 passou)
   ❌ login (1/3 falhou)
   ✅ payment (2/2 passou)
   ⚪ regression-gap-probe (sem testes)
```

**Relatório salvo:**
```
📄 Relatório: fastqa/manual_test/regression_analysis/PR-{id}_execution_report_{timestamp}.md
📊 JSON: fastqa/manual_test/regression_analysis/PR-{id}_execution_report_{timestamp}.json
```

### 6️⃣ Oferecer Ações de Continuidade

```
🏷️ Próximos passos:

  1️⃣ 🔧 Corrigir falhas automaticamente → @fastqa:verify_and_fix
  2️⃣ 📊 Sincronizar resultados com Test Plan → @fastqa:azdo_sync_pipeline_results  
  3️⃣ 📋 Gerar relatório formal → @fastqa:azdo_generate_report
  4️⃣ 🔄 Re-executar apenas os falhados → @fastqa:execute_regression_plan (informar "apenas falhados")
  5️⃣ 💡 Criar testes para gaps → @fastqa:test_case_with_fastqa
```

**Se jornada ativa:** Atualizar `fastqa/scripts/journey_state.json` com o step completado.

> **Fallback:** Se `journey_state.json` estiver malformado ou ausente, recriar com o estado atual
> (step `execute_regression_plan` como completado, steps anteriores como completados por inferência).
> Nunca falhar silenciosamente por conta de journey_state corrompido.

---

## 7️⃣ Tratamento de Erros

**Se plano JSON inválido:**
```
❌ O arquivo {path} não é um plano de regressão válido.
   Verifique se foi gerado por @fastqa:regression_analyze com a flag --json.
```

**Se framework não encontrado:**
```
⚠️ Framework "{framework}" não encontrado no automation_root.

Verifique:
  1. O project_config.json está configurado corretamente?
  2. As dependências foram instaladas? (cd {automation_root} && npm install)
```

**Se todos os testes falharam por timeout:**
```
⏰ Execução excedeu o timeout ({timeout}ms).

Sugestões:
  1. Reduza o escopo: informe "apenas e2e" ou "apenas high priority"
  2. Verifique se o servidor da aplicação está rodando
  3. Verifique logs no terminal para erros silenciosos
```

**Se nenhum resultado parseado:**
```
⚠️ Nenhum resultado de teste encontrado nos relatórios do framework.

Possíveis causas:
  • Os specs não foram encontrados no automation_root
  • O reporter JSON não gerou output válido
  • Verifique os logs de execução acima
```
