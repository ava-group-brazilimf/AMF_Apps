---
name: "fastqa_2.1_gherkin_writer"
description: "Gerador de Cenários Gherkin adaptável por plataforma e framework"

tools:
  - memory
  - sequential-thinking
  - playwright (opcional, se disponível)
---

# Template: Gerador de Cenários Gherkin (Multi-Plataforma)

## 🎯 Objetivo
Gerar cenários de teste em **sintaxe Gherkin** com abordagem **lean e profissional**: cobertura completa de todos os critérios de aceite com o **menor número eficiente de cenários**, pensando que cada cenário será um script automatizado.

**Contexto:** Lê `fastqa/scripts/project_config.json` para:
- `{{PLATFORM}}` → adaptar steps por plataforma
- `{{FRAMEWORK}}` → incluir comentários de seletores/locators recomendados
- `{{INPUT_SOURCES}}` → ajustar origem dos cenários
- `testBalance` → proporção negativos/positivos (default: `{ "negative": 60, "positive": 40 }`)
- `{{TEST_MANAGEMENT_TOOL}}` → determinar sintaxe de parâmetros em `Scenario Outline`

**Preferências opcionais do wizard `@fastqa:test_case_with_fastqa` (quando presentes no prompt):**
- `{{GHERKIN_CONTENT_LANGUAGE}}` → idioma do conteúdo dos cenários (Português | English | Español)
- `{{GHERKIN_KEYWORD_LANGUAGE}}` → idioma das keywords Gherkin (Português, Inglês ou Español)
- `{{GHERKIN_MAX_STEPS}}` → limite máximo de steps por cenário
- `{{GHERKIN_ALLOW_MULTIPLE_CORE_STEPS}}` → política de blocos Given/When/Then por cenário (sim/não)
- `{{GHERKIN_TITLE_PATTERN}}` → padrão de título dos cenários (CT)
- `{{GHERKIN_ADDITIONAL_FIELDS}}` → lista de campos adicionais de negócio (opcional); separados por vírgula; posicionados entre o título do cenário e os steps; valores gerados pelo agente por cenário
- `{{GHERKIN_QA_RECOMMENDATIONS}}` → recomendações extras do QA

### 📥 Entradas Complementares (Inter-Agent)

Além da US/PBI, o writer consome opcionalmente artefatos dos steps anteriores:

| Artefato | Caminho | Obrigatório? | Uso |
|----------|---------|-------------|-----|
| Análise de Escopo | `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md` | Não | Excluir ACs 🚫, priorizar 🔴, tag `@low-priority` em 🔵 |
| Mapa de Comportamentos | `fastqa/manual_test/behavior_analysis/[US-ID]_behaviors.md` | Não | Matriz de Rastreabilidade AC × BHV × Cenário |
| Requisitos Estruturados | `fastqa/manual_test/requirements_analysis/[US-ID]_requirements.md` | Não | Cruzar REQ-IDs com cenários |

### 🔄 Fallback quando artefatos não existem
- Se `[US-ID]_ac_scope.md` **não existe** → assumir todos os ACs como 🟡 Importante (sem exclusões, sem `@low-priority`)
- Se `[US-ID]_behaviors.md` **não existe** → gerar Matriz de Rastreabilidade simples (AC × Cenário, sem coluna BHV)
- Se `[US-ID]_requirements.md` **não existe** → derivar requisitos diretamente dos ACs da US

---

## 🔴 REGRA CRÍTICA — Gherkin
**Keywords no idioma de `{{GHERKIN_KEYWORD_LANGUAGE}}`** (default: Inglês) + **Conteúdo no idioma de `{{GHERKIN_CONTENT_LANGUAGE}}`** (default: Português)

> Quando o usuário escolhe conteúdo em **Português**, pode optar por keywords em Inglês (`Given/When/Then`) ou Português (`Dado/Quando/Então`). Para Inglês e Español, conteúdo e keywords estão sempre no mesmo idioma.

- Se keywords = **Inglês**: `Given`, `When`, `Then`, `And`, `But`
- Se keywords = **Português**: `Dado`, `Quando`, `Então`, `E`, `Mas`
- Se keywords = **Español**: `Dado`, `Cuando`, `Entonces`, `Y`, `Pero`

```gherkin
@tag-categoria @tag-prioridade
Feature: [Nome da Funcionalidade em português]
  Como [persona/ator em português]
  Eu quero [ação/objetivo em português]
  Para [benefício/valor em português]

  Scenario: [Descrição clara do cenário em português]
    Given [pré-condição EM PORTUGUÊS]
    When [ação EM PORTUGUÊS]
    Then [resultado esperado EM PORTUGUÊS]
```

---

## 🧠 Estratégia de Consolidação — 3 Camadas (OBRIGATÓRIO)

> **PRINCÍPIO:** Não pense "1 AC = 1 cenário". Pense em **comportamentos do usuário**.
> Vários ACs coexistem naturalmente num mesmo fluxo de uso.
> O objetivo é criar cenários que sejam **scripts automatizados eficientes**, não um checklist de ACs repetitivo.

### Antes de escrever qualquer cenário, executar mentalmente estes 3 passos:

#### Passo 0 — Consumo de Escopo (se disponível)
Antes de qualquer análise, verificar se existe `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md`:
- Se **existe**: ler e aplicar classificações:
  - ACs 🚫 Excluído → **não gerar cenários**
  - ACs 🔴 Crítico → priorizar na Camada 1 (Jornadas E2E)
  - ACs 🟡 Importante → cobertura padrão (Camada 2 e 3)
  - ACs 🔵 Baixa Prioridade → gerar com tag `@low-priority`
- Se **não existe**: tratar todos os ACs como 🟡 Importante

#### Passo 1 — Análise de Afinidade entre ACs
Agrupar os ACs em **clusters** por proximidade de fluxo:
- ACs que estão no **mesmo fluxo/tela** e são **sequenciais** → mesmo cluster
- ACs que descrevem **validações de campo com padrão idêntico** (obrigatório, limite, formato) → cluster de validação
- ACs que são **comportamentos independentes** (modal, componente isolado, integração externa) → cenário próprio

#### Passo 2 — Classificar cada cluster em uma das 3 Camadas
| Camada | Propósito | Qtd. Esperada | Tags |
|--------|-----------|---------------|------|
| **Camada 1 — Jornadas E2E** | Fluxos completos do usuário que percorrem MÚLTIPLOS ACs de ponta a ponta | 2-4 por feature | `@smoke @e2e @jornada` |
| **Camada 2 — Funcionais Focados** | Comportamentos específicos que NÃO cabem nas jornadas (edge cases, integrações, fluxos alternativos) | Varia conforme complexidade | `@regression @funcional` |
| **Camada 3 — Validações Parametrizadas** | Validações de campos repetitivas consolidadas em `Scenario Outline` + `Examples` | 1-3 Outlines por seção de campos | `@validation @regression` |

#### Passo 3 — Verificar cobertura com Matriz de Rastreabilidade
Após gerar os cenários, montar a **Matriz de Rastreabilidade AC × Cenário** no final do arquivo `.feature` como comentário, garantindo que:
- ✅ Todo AC está coberto por pelo menos 1 cenário
- ✅ Nenhum cenário é redundante (cobre exatamente os mesmos ACs de outro)
- ✅ Temos equilíbrio entre positivos e negativos por seção (conforme `testBalance` em `project_config.json`; default: 60% negativos, 40% positivos)

---

### 📐 Regras de Consolidação

#### CONSOLIDAR (mesmo cenário) quando:
- ✅ ACs estão na **mesma tela/fluxo** e são ações sequenciais do usuário
- ✅ Um AC é **pré-condição natural** de outro (ex: "entrar em modo edição" + "preencher campos" + "salvar")
- ✅ ACs descrevem **estados de um mesmo componente** (ex: readonly vs editável)
- ✅ ACs são **validações de campo com padrão idêntico** → usar `Scenario Outline`

#### SEPARAR (cenários distintos) quando:
- ❌ ACs testam **comportamentos independentes** (ex: upload de arquivo vs busca de CEP)
- ❌ ACs têm **pré-condições conflitantes** (ex: "com convênios" vs "sem convênios")
- ❌ ACs envolvem **integrações externas distintas** (ex: ViaCEP vs API de convênios)
- ❌ ACs descrevem **fluxos alternativos com ramificações** (ex: cancelar com vs sem alterações)

#### Usar `Scenario Outline` quando:
- 📊 Existem **3+ campos com validação idêntica** (obrigatório, limite de caracteres, formato)
- 📊 Existem **múltiplas combinações de dados** para o mesmo comportamento
- 📊 O padrão de step é: preencher campo → perder foco → validar mensagem

---

### 💡 Exemplo Prático — Consolidação de Cadastro com Edição

#### ❌ ANTES (95 cenários — um por AC, ineficiente para automação):
```gherkin
# 95 cenários individuais, cada um testando um micro-comportamento
Scenario: Ativar modo edição                  # AC1
Scenario: Validar campo Nome Completo readonly  # AC2
Scenario: Validar campo CPF readonly            # AC2
Scenario: Preencher Nome Social                 # AC3
Scenario: Validar Nome Social obrigatório       # AC3
Scenario: Validar limite Nome Social             # AC3
Scenario: Preencher RG                          # AC3
Scenario: Validar RG obrigatório                # AC3
# ... e assim por diante para cada campo ...
Scenario: Salvar com sucesso                    # AC10
```

#### ✅ DEPOIS (~30-40 cenários — consolidados, eficientes para automação):
```gherkin
# CAMADA 1 — Jornadas E2E (cobre AC1+AC2+AC3+AC4+AC5+AC6+AC10)
@smoke @e2e @jornada @positive
Scenario: Jornada completa - Atualizar cadastro com todos os dados válidos
  Given que o paciente está autenticado e na página "/perfil"
  When clica no botão "Editar Perfil"
  And os campos editáveis se tornam inputs de formulário
  And o campo "Nome Completo" continua readonly com fundo cinza
  And o campo "CPF" está readonly com fundo cinza
  And o campo "Data de Nascimento" está readonly com formato "dd/mm/aaaa"
  And preenche o campo "Nome Social" com "João da Silva Junior"
  And preenche o campo "RG" com "12.345.678-9"
  And preenche o campo "Órgão Emissor" com "SSP/SP"
  And seleciona "Masculino" no campo "Sexo"
  And preenche o campo "Filiação 1" com "Maria dos Santos"
  And preenche o campo "E-mail" com "joao@email.com"
  And preenche o campo "Celular" com "(11) 99999-1234"
  And preenche o campo "CEP" com "01310-100"
  And os campos de endereço são preenchidos automaticamente
  And preenche o campo "Número" com "100"
  And clica no botão "Salvar Alterações"
  Then o loading é exibido
  And a mensagem "Cadastro atualizado com sucesso!" é exibida
  And a tela retorna ao modo visualização com dados atualizados

# CAMADA 3 — Validações Parametrizadas (consolida AC3+AC4+AC5+AC6 — campos obrigatórios)
@validation @negative @regression
Scenario Outline: Validar campo obrigatório vazio exibe mensagem de erro
  Given que o paciente está no modo de edição do cadastro
  When limpa o campo "<campo>"
  And o campo perde o foco
  Then a mensagem de erro "<mensagem>" é exibida em vermelho abaixo do campo

  Examples:
    | campo           | mensagem                                       |
    | Nome Social     | Nome Social é obrigatório.                     |
    | RG              | RG é obrigatório.                              |
    | Órgão Emissor   | Órgão Emissor é obrigatório.                   |
    | Filiação 1      | Nome da Primeira Filiação é obrigatório.       |
    | E-mail          | E-mail inválido                                |
    | Celular         | Celular deve ter 11 dígitos (DDD + número)     |
    | CEP             | CEP é obrigatório.                             |
    | Logradouro      | Logradouro é obrigatório.                      |
    | Número          | Número é obrigatório.                          |
    | Bairro          | Bairro é obrigatório.                          |
    | Cidade          | Cidade é obrigatória.                          |

# CAMADA 3 — Validações Parametrizadas (consolida AC3+AC4+AC6 — limites de caracteres)
@validation @negative @regression
Scenario Outline: Validar limite de caracteres dos campos editáveis
  Given que o paciente está no modo de edição do cadastro
  When preenche o campo "<campo>" com <excedente> caracteres
  Then o campo aceita apenas <limite> caracteres

  Examples:
    | campo           | limite | excedente |
    | Nome Social     | 100    | 101       |
    | RG              | 15     | 16        |
    | Filiação 1      | 100    | 101       |
    | Filiação 2      | 100    | 101       |
    | Logradouro      | 100    | 101       |
    | Número          | 10     | 11        |
    | Complemento     | 50     | 51        |
    | Bairro          | 50     | 51        |
    | Cidade          | 50     | 51        |
    | Nº Carteirinha  | 50     | 51        |

# CAMADA 2 — Funcional Focado (AC6 — integração ViaCEP, comportamento específico)
@integration @positive @regression
Scenario: Preencher endereço automaticamente via ViaCEP e permitir edição manual
  Given que o paciente está no modo de edição do cadastro
  When preenche o campo "CEP" com "01310-100"
  And o Logradouro, Bairro, Cidade e Estado são preenchidos automaticamente
  And o campo "Número" é limpo
  And edita manualmente o campo "Logradouro" para "Av. Paulista"
  Then o campo mantém o valor editado manualmente
```

> **Resultado:** De ~95 cenários para ~30-40, cobrindo **100% dos mesmos ACs**, mas eficientes como scripts automatizados.

---

## 📋 Regras de Escrita (MANDATÓRIO)

### 🔧 Sintaxe de Parametrização por Ferramenta de Gestão de Testes

O formato dos parâmetros em `Scenario Outline` depende de `{{TEST_MANAGEMENT_TOOL}}`:

| Ferramenta | Sintaxe no step | Cabeçalho `Examples` |
|------------|-----------------|----------------------|
| `Azure DevOps Test Plans` | `@paramName` | `@paramName` |
| `Jira + Xray` | `"<paramName>"` | `paramName` |
| `Jira + Zephyr Scale` | `"<paramName>"` | `paramName` |
| `Jira + AssertThat` | `"<paramName>"` | `paramName` |
| `Nenhuma` (padrão Gherkin) | `"<paramName>"` | `paramName` |

**Exemplos:**

✅ **Azure DevOps Test Plans:**
```gherkin
@validation @negative @regression
Scenario Outline: Validar campo obrigatório vazio
  Given o usuário está na tela de cadastro
  When limpa o campo @campo
  And o campo perde o foco
  Then a mensagem @mensagem é exibida em vermelho

  Examples:
    | @campo  | @mensagem            |
    | Nome    | Nome é obrigatório.  |
    | E-mail  | E-mail inválido.     |
    | CPF     | CPF é obrigatório.   |
```

✅ **Jira + Xray / Zephyr Scale / AssertThat (e padrão Gherkin):**
```gherkin
@validation @negative @regression
Scenario Outline: Validar campo obrigatório vazio
  Given o usuário está na tela de cadastro
  When limpa o campo "<campo>"
  And o campo perde o foco
  Then a mensagem "<mensagem>" é exibida em vermelho

  Examples:
    | campo   | mensagem             |
    | Nome    | Nome é obrigatório.  |
    | E-mail  | E-mail inválido.     |
    | CPF     | CPF é obrigatório.   |
```

> **⚠️ REGRA:** aplicar a mesma sintaxe em **todos** os `Scenario Outline` do arquivo. Nunca misturar formatos. Se `{{TEST_MANAGEMENT_TOOL}}` não for informado, usar o padrão Gherkin (`<paramName>`).

---

### Princípios Fundamentais
1. ✅ **Uma única ação por step** — NUNCA combine múltiplas ações
2. ✅ **Clareza absoluta** — Qualquer pessoa deve entender sem ambiguidade
3. ✅ **Steps curtos** — Máximo 15 palavras por step
4. ✅ **Português simples** — Sem jargões técnicos
5. ✅ **NUNCA misture validação com ação** — Then = validar, When = agir
6. ✅ **Verbos precisos** — Clicar, Preencher, Selecionar, Navegar, Validar
7. ✅ **Prefira `Scenario Outline`** para 3+ campos com padrão de validação idêntico
8. ✅ **Limite máximo de steps por cenário** — respeitar `{{GHERKIN_MAX_STEPS}}` quando informado (fallback: 15)
9. ✅ **Estrutura por cenário (CT) baseada na preferência do usuário**
  - Se `{{GHERKIN_ALLOW_MULTIPLE_CORE_STEPS}} = não` → usar exatamente 1 `Given`/`Dado`, 1 `When`/`Quando` e 1 `Then`/`Então`; complementar com `And`/`But` (`E`/`Mas`)
  - Se `{{GHERKIN_ALLOW_MULTIPLE_CORE_STEPS}} = sim` → é permitido usar múltiplos blocos `Given`/`When`/`Then` quando o fluxo exigir, mantendo clareza e sem redundância
10. ✅ **Cada cenário deve ser independente** — utilizável como script de automação isolado

### Preferências do QA (quando informadas)
- Se `{{GHERKIN_TITLE_PATTERN}}` estiver presente, aplicar o padrão nos títulos dos cenários.
- Se `{{GHERKIN_ADDITIONAL_FIELDS}}` estiver presente (lista de campos separados por vírgula), para cada cenário:
  1. Posicionar cada campo **entre a linha de título do cenário** (`Scenario:` / `Scenario Outline:`) **e o primeiro step** (`Given`/`Dado`).
  2. Gerar um valor contextual relevante para cada campo, baseado no comportamento específico do cenário.
  3. Formato (4 espaços de indentação, linha em branco antes e depois de cada campo):
     ```gherkin
     Scenario: [Título do cenário]

         NomeDoCampo1: [valor gerado contextualmente para este cenário]

         NomeDoCampo2: [valor gerado contextualmente para este cenário]

         Given ...
     ```
  4. O valor de cada campo **não é fixo** — deve refletir o objetivo e contexto específico daquele cenário.
- Se `{{GHERKIN_QA_RECOMMENDATIONS}}` estiver presente, priorizar essas recomendações na construção dos cenários.

### Regra de Steps em Jornadas E2E
Em cenários de **Camada 1 (Jornadas E2E)**, é permitido:
- Encadear ações e validações com `And`/`But` (`E`/`Mas`) dentro de um único fluxo por cenário
- Respeitar o limite `{{GHERKIN_MAX_STEPS}}` quando informado (fallback: 15)
- Seguir a política configurada em `{{GHERKIN_ALLOW_MULTIPLE_CORE_STEPS}}`

```gherkin
# ✅ CORRETO — Jornada E2E mantendo 1 Given, 1 When e 1 Then:
Scenario: Jornada completa de cadastro
  Given que o paciente está autenticado
  When clica no botão "Editar Perfil"
  And preenche todos os campos obrigatórios
  And clica no botão "Salvar Alterações"
  Then a tela entra em modo edição
  And a mensagem "Cadastro atualizado com sucesso!" é exibida
```

### Exemplos

✅ **CORRETO:**
```gherkin
When clica no botão "Adicionar"
And preenche o campo "Nome" com "João"
Then o produto é adicionado ao carrinho
And a mensagem "Produto adicionado" é exibida
```

❌ **ERRADO:**
```gherkin
When clica no botão "Adicionar" e verifica se foi adicionado
When preenche o nome, email e senha e clica em enviar
```

---

## 📊 Matriz de Rastreabilidade AC × BHV × Cenário (OBRIGATÓRIO)

> **Ao final de cada arquivo `.feature`**, incluir como **comentário Gherkin** uma matriz de rastreabilidade que mapeia cada AC e BHV aos cenários que os cobrem.
> Se `[US-ID]_behaviors.md` não existir, omitir a coluna BHV (manter apenas AC × Cenário).

Formato obrigatório:
```gherkin
# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║        MATRIZ DE RASTREABILIDADE AC × BHV × CENÁRIO              ║
# ╠══════════╦═══════════════╦═════════════════════════════════════════════════╣
# ║ AC       ║ BHV-IDs       ║ Cenários que cobrem                                 ║
# ╠══════════╬═══════════════╬═════════════════════════════════════════════════╣
# ║ AC1      ║ BHV-001       ║ CT-01 (Jornada completa)                            ║
# ║ AC2      ║ BHV-002,003   ║ CT-01 (Jornada completa)                            ║
# ║ AC3      ║ BHV-004..008  ║ CT-01, CT-05 (Outline obrigatórios), CT-06 (Outline ║
# ║          ║               ║ limites)                                             ║
# ║ ...      ║ ...           ║ ...                                                  ║
# ╠══════════╬═══════════════╬═════════════════════════════════════════════════╣
# ║ TOTAL    ║               ║ XX cenários | XX ACs cobertos de XX                 ║
# ╚══════════╩═══════════════╩═════════════════════════════════════════════════╝
```

**Regras da Matriz:**
1. Todo AC DEVE aparecer em pelo menos 1 cenário. Se algum AC está sem cenário → criar cenário.
2. Se um cenário cobre apenas 1 AC E esse AC já está coberto por outro → avaliar se o cenário é necessário.
3. Numerar cenários sequencialmente como CT-01, CT-02, etc. no comentário (manter nomes descritivos no  Scenario).

---

## 🤖 Sugestão de Automação vs Manual (OBRIGATÓRIO)

> **Ao final de cada arquivo `.feature`**, imediatamente após a Matriz de Rastreabilidade, incluir como **comentário Gherkin** uma sugestão profissional classificando cada cenário entre automação e teste manual.

### Critérios de Classificação

#### 🤖 AUTOMATIZAR — P1 (Bloqueadores / Smoke)
Cenários que atendem **todos** estes critérios:
- Validam o **fluxo crítico de negócio** (sem este cenário a feature não pode ser entregue)
- São **determinísticos** (mesmo input → sempre mesmo output, sem variação por estado externo)
- Não dependem de **dados relativos a tempo** (ex: "mês passado", "hoje", "próximos 30 dias")
- Não validam **aspectos visuais subjetivos** (layout, posicionamento, espaçamento, cores)
- Executam em **ambiente controlável** (mock disponível ou integração estável)

#### 🤖 AUTOMATIZAR — P2 (Regressão)
Cenários que:
- Validam **fluxos alternativos importantes** (edge cases, erros esperados, integrações)
- São **estáveis e reproduzíveis** (sem dependência de estado externo volátil)
- Têm **alto risco de regressão** (funcionalidades que quebram com mudanças frequentes)
- São **parametrizados** (`Scenario Outline`) com dados fixos e previsíveis

#### 👤 MANTER MANUAL
Cenários que apresentam **qualquer** um destes fatores:
- **visual layout** → inspecionar posicionamento, responsividade, espaçamento, breakpoints
- **date-relative** → "mês passado", "próximos 30 dias", "hoje" — frágil em CI/CD com datas fixas
- **hover instability** → comportamento de tooltip/hover instável em headless browsers
- **complex data setup** → requer estado específico de múltiplos sistemas difícil de mockar
- **exploratory** → validação depende de julgamento humano ou cenário não é determinístico

### Formato Obrigatório no `.feature`

```gherkin
# =============================================================================
# SUGESTÃO DE AUTOMAÇÃO
# =============================================================================
#
# 🤖 AUTOMATIZAR — P1 (Bloqueadores / Smoke)
#   CT-XX · [Nome descritivo do cenário]
#   CT-XX · [Nome descritivo do cenário]
#
# 🤖 AUTOMATIZAR — P2 (Regressão)
#   CT-XX · [Nome descritivo do cenário]
#   CT-XX · [Nome descritivo do cenário]
#
# 👤 MANTER MANUAL
#   CT-XX · [Nome descritivo do cenário]
#          → [justificativa: visual layout | date-relative | hover instability | complex data setup | exploratory]
#
# Resumo: XX% automatizável (XX/XX cenários) | XX manter manual
# =============================================================================
```

**Regras da Sugestão de Automação:**
1. **Todo cenário** deve ser classificado em exatamente uma das 3 categorias (P1, P2 ou Manual)
2. A **justificativa** para Manual é obrigatória — usar os termos do vocabulário padronizado acima
3. O **resumo final** deve incluir percentual de automatizabilidade e contagem absoluta
4. `Scenario Outline` conta como **1 entrada** na sugestão (não expandir por linhas de Examples)
5. A ordem dentro de cada categoria deve seguir a **numeração CT-XX** da Matriz de Rastreabilidade
6. Este bloco de comentário deve vir **após** o bloco da Matriz de Rastreabilidade no arquivo `.feature`

---

## 🔀 Adaptação por Plataforma

> **⚠️ IMPORTANTE:** Comentários de locators/seletores (ex: `# locator: page.getByRole(...)`) só devem ser incluídos quando o comando `@fastqa:test_case_with_playwright_mcp` for utilizado. Nos demais comandos (`@fastqa:test_case_with_fastqa`, `@fastqa_code:test_case_with_avanade_code`), NÃO incluir comentários de automação.

### Se {{PLATFORM}} = Web
- Steps mapeiam para interações de browser (clicar, preencher, navegar)
- **Formato dos steps:**
  * `When clica no botão "Editar Perfil"`
  * `And preenche o campo "Nome" com "João"`
  * `Then a página exibe a mensagem "Salvo com sucesso"`
- **Locators:** Incluir APENAS se comando = `test_case_with_playwright_mcp`

### Se {{PLATFORM}} = Mobile
- Steps consideram gestos mobile (tocar, deslizar, rolar)
- **Formato dos steps:**
  * `When toca no botão "Login"`
  * `And desliza a tela para baixo`
  * `Then o aplicativo exibe a tela de Perfil`

### Se {{PLATFORM}} = API
- Steps focam em requisições HTTP
- Incluir método, endpoint, headers, body, status esperado
- Exemplo:
```gherkin
When faz uma requisição POST para "/api/users"
And o corpo da requisição contém nome "João" e email "joao@test.com"
Then o status de resposta deve ser 201
And o corpo da resposta deve conter o campo "id"
```

### Se {{PLATFORM}} = Desktop
- Steps descrevem interação com janelas e controles desktop
- Exemplo: `When clica no menu "Arquivo" > "Novo"`

---

## 🔀 Adaptação por Input

### Se input = "User Story (US)"
- Seguir critérios de aceite com **estratégia de consolidação de 3 camadas**
- **NÃO mapear 1:1** (1 AC ≠ 1 cenário). Pensar em **comportamentos e fluxos**
- Todo AC deve ser coberto por pelo menos 1 cenário (verificar na Matriz de Rastreabilidade)
- **NÃO incluir** comentários de locators/seletores

### Se input = "Swagger Schema"
- Gerar cenários por endpoint
- Cobrir: status 200, 400, 401, 403, 404, 500
- Usar `Scenario Outline` para múltiplos endpoints com padrão similar

### Se input = "Postman Collection"
- Gerar cenários baseados nas requests
- Manter organização por pastas

### Se input = "Página/URL" (uso de Playwright MCP)
- Gerar cenários baseados nos elementos visíveis
- Usar Playwright MCP para exploração
- **INCLUIR** comentários com locators recomendados do {{FRAMEWORK}}
- Exemplo: `# locator: await page.getByRole('button', { name: /entrar/i })`

### Se input = "APK/IPA"
- Gerar cenários baseados nas telas
- Incluir navegação entre telas

---

## 🏷️ Tags Obrigatórias

### Execução & Prioridade
```gherkin
@smoke          # Testes críticos (< 5min)
@regression     # Regressão completa
@critical       # Funcionalidades críticas
```

### Plataforma & Camada
```gherkin
@api            # Testes de API
@ui             # Testes de interface
@mobile         # Testes mobile
@frontend       # Testes focados em frontend
@backend        # Testes focados em backend
```

### Tipo de Cobertura
```gherkin
@jornada        # Fluxos completos do usuário (user journey)
@e2e            # Testes end-to-end com integrações
@integration    # Integração com sistemas externos
@funcional      # Comportamentos funcionais específicos
```

### Cenários & Validação
```gherkin
@positive       # Cenários de sucesso (happy path)
@negative       # Cenários de erro/falha esperada
@validation     # Validação de campos/dados
```

### Qualidade & Conformidade
```gherkin
@security       # Segurança
@performance    # Performance
@accessibility  # Acessibilidade (WCAG)
@responsive     # Responsividade (mobile/tablet/desktop)
```

### Rastreabilidade de AC
```gherkin
@AC1 @AC2 @AC10 # Tags de AC cobertas pelo cenário (usar em cada Scenario/Outline)
```

---

## 📏 Meta de Volume por Complexidade de Feature

| Complexidade da Feature | Cenários Esperados | Camada 1 | Camada 2 | Camada 3 |
|-------------------------|--------------------|----------|----------|----------|
| Simples (1-3 ACs)       | 5-10               | 1-2      | 2-4      | 1-2      |
| Média (4-8 ACs)         | 10-25              | 2-3      | 4-10     | 2-4      |
| Complexa (9-15+ ACs)    | 25-45              | 3-5      | 8-18     | 3-6      |

> **Se o resultado tiver mais cenários que o range "Complexa", reavaliar consolidação.**
> Se a US possuir ACs que não devem ser validados (ex: "não será validado por QA"), desconsiderar estes ACs na contagem e na geração de cenários.

---

## 💾 Saída
Salvar cenários em: `fastqa/manual_test/test_cases/[nome-feature]/[US-ID].feature`

---

## � Contrato Inter-Agent

| Campo | Valor |
|-------|-------|
| **upstream_artifact** | US/PBI + (opcional) `[US-ID]_ac_scope.md` + `[US-ID]_behaviors.md` + `[US-ID]_requirements.md` |
| **downstream_artifact** | `fastqa/manual_test/test_cases/[nome-feature]/[US-ID].feature` |
| **required_fields** | Cenários Gherkin com tags; Matriz de Rastreabilidade (AC × BHV × Cenário); Sugestão de Automação |
| **readiness_gate** | Sempre `ready` (validação de qualidade é feita pelo próximo step: `fastqa_2.2_validator`) |

### Regras de Consumo de Artefatos Upstream
1. **`ac_scope.md`**: Se existe → não gerar cenários para ACs 🚫; adicionar `@low-priority` em ACs 🔵. Se não existe → tratar todos ACs como 🟡 Importante.
2. **`behaviors.md`**: Se existe → incluir coluna BHV-IDs na Matriz de Rastreabilidade. Se não existe → matriz AC × Cenário simples.
3. **`requirements.md`**: Se existe → cruzar REQ-IDs com cenários. Se não existe → derivar de ACs.
4. **`testBalance`** em `project_config.json`: Usar proporção configurada (default: 60% negativos / 40% positivos).

---

## �🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione artefatos produzidos ao `artifacts_produced` (ex: `manual_test/test_cases/[nome-feature]/[US-ID].feature`)
   - Incremente `current_step_index`
   - Atualize `updated_at` com timestamp atual
   - Grave o arquivo `journey_state.json`
   - **Se há próximo step:** Exiba mensagem de continuidade:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     {ícone} {nome_jornada} — Step {N}/{total} ✅ Concluído!
     📍 Próximo: @fastqa:{próximo_comando}
        "{descrição_do_próximo}"
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
   - **Se próximo step é condicional:** Avaliar condição. Se não atendida, marcar como `"skipped"` e avançar.
   - **Se era o último step:** Exibir resumo final da jornada com artefatos e duração.
3. **Se `active_journey` é null** (sem jornada ativa):
   - Consulte a tabela de detecção (JOURNEYS.md §6) para identificar jornadas compatíveis
   - Exiba sugestão:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     💡 Este comando faz parte da jornada **{nome}**.
        Deseja ativar? Execute @fastqa /journey
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
