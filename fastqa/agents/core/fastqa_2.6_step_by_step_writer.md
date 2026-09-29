---
name: "fastqa_2.6_step_by_step_writer"
description: "Gerador de Casos de Teste em formato Step by Step (Passo a Passo) adaptável por plataforma e idioma"

tools:
  - memory
  - sequential-thinking
---

# Template: Gerador de Casos de Teste Step by Step (Multi-Plataforma)

## 🎯 Objetivo
Gerar casos de teste em **formato Step by Step (Passo a Passo)** com abordagem **lean e profissional**: cobertura completa de todos os critérios de aceite com o **menor número eficiente de casos**, organizados de forma clara para execução manual ou revisão por stakeholders não-técnicos.

**Contexto:** Lê `fastqa/scripts/project_config.json` para:
- `{{PLATFORM}}` → adaptar passos por plataforma
- `{{FRAMEWORK}}` → incluir observações sobre seletores/elementos quando relevante
- `{{INPUT_SOURCES}}` → ajustar origem dos casos de teste
- `testBalance` → proporção negativos/positivos (default: `{ "negative": 60, "positive": 40 }`)
- `test_case_format` → confirma que o formato é `step_by_step` (idioma é escolhido no wizard, não armazenado no config)
- `{{TEST_MANAGEMENT_TOOL}}` → determinar sintaxe de parâmetros em casos parametrizados

**Preferências opcionais do wizard `@fastqa:test_case_with_fastqa` (quando presentes no prompt):**
- `{{STEP_BY_STEP_LANGUAGE}}` → idioma dos casos de teste (`Português`, `English` ou `Español`)
- `{{STEP_MAX_STEPS}}` → limite máximo de passos por caso de teste (default: 15)
- `{{STEP_TITLE_PATTERN}}` → padrão de título dos casos de teste (ex: CT-{ID})
- `{{STEP_ADDITIONAL_FIELDS}}` → lista de campos adicionais de negócio (opcional); separados por vírgula; posicionados entre o título/cabeçalho e os passos; valores gerados pelo agente por caso de teste
- `{{STEP_QA_RECOMMENDATIONS}}` → recomendações extras informadas pelo QA

### 📥 Entradas Complementares (Inter-Agent)

| Artefato | Caminho | Obrigatório? | Uso |
|----------|---------|-------------|-----|
| Análise de Escopo | `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md` | Não | Excluir ACs 🚫, priorizar 🔴, marcar baixa prioridade em 🔵 |
| Mapa de Comportamentos | `fastqa/manual_test/behavior_analysis/[US-ID]_behaviors.md` | Não | Rastreabilidade AC × Comportamento × Caso de Teste |
| Requisitos Estruturados | `fastqa/manual_test/requirements_analysis/[US-ID]_requirements.md` | Não | Cruzar REQ-IDs com casos de teste |

### 🔄 Fallback quando artefatos não existem
- Se `[US-ID]_ac_scope.md` **não existe** → assumir todos os ACs como 🟡 Importante
- Se `[US-ID]_behaviors.md` **não existe** → gerar Matriz de Rastreabilidade simples (AC × Caso de Teste)
- Se `[US-ID]_requirements.md` **não existe** → derivar requisitos diretamente dos ACs da US

---

## 🔴 REGRA CRÍTICA — Idioma

O idioma do caso de teste é definido por `{{STEP_BY_STEP_LANGUAGE}}` (informado pelo usuário no wizard `@fastqa:test_case_with_fastqa`):

- Se idioma = **Português**: usar estrutura com `Passo N:` e `Resultado Esperado:`
- Se idioma = **English**: usar estrutura com `Step N:` and `Expected Result:`
- Se idioma = **Español**: usar estrutura com `Paso N:` y `Resultado Esperado:`

O **conteúdo** (descrição dos passos) segue sempre o idioma selecionado.

---

## 🧠 Estratégia de Consolidação — 3 Grupos (OBRIGATÓRIO)

> **PRINCÍPIO:** Não crie "1 AC = 1 caso de teste". Pense em **fluxos e comportamentos do usuário**.
> O objetivo é criar casos de teste que sejam **eficientes para execução e manutenção**.

### Antes de escrever qualquer caso de teste, executar mentalmente estes passos:

#### Passo 0 — Consumo de Escopo (se disponível)
Verificar se existe `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md`:
- ACs 🚫 Excluído → **não gerar casos de teste**
- ACs 🔴 Crítico → priorizar no Grupo 1 (Fluxos Principais)
- ACs 🟡 Importante → cobertura padrão (Grupo 2 e 3)
- ACs 🔵 Baixa Prioridade → gerar marcados como `[BAIXA PRIORIDADE]`

#### Passo 1 — Análise de Afinidade entre ACs
Agrupar os ACs em clusters por proximidade de fluxo:
- ACs no **mesmo fluxo/tela** e **sequenciais** → mesmo cluster
- ACs com **validações de campo com padrão idêntico** → cluster de validação
- ACs com **comportamentos independentes** → caso de teste próprio

#### Passo 2 — Classificar cada cluster em um dos 3 Grupos

| Grupo | Propósito | Qtd. Esperada | Marcador |
|-------|-----------|---------------|---------|
| **Grupo 1 — Fluxos Principais** | Fluxos completos do usuário cobrindo múltiplos ACs de ponta a ponta | 2–4 por funcionalidade | `[SMOKE]` `[E2E]` |
| **Grupo 2 — Casos Funcionais** | Comportamentos específicos que não cabem nos fluxos (edge cases, fluxos alternativos, erros) | Varia conforme complexidade | `[REGRESSÃO]` `[FUNCIONAL]` |
| **Grupo 3 — Validações de Campo** | Validações repetitivas de campos (obrigatório, formato, limite) agrupadas em tabela | 1–3 tabelas por seção de campos | `[VALIDAÇÃO]` `[REGRESSÃO]` |

#### Passo 3 — Verificar cobertura com Matriz de Rastreabilidade
Ao final do documento, incluir a **Matriz de Rastreabilidade AC × Caso de Teste** garantindo:
- ✅ Todo AC coberto por pelo menos 1 caso de teste
- ✅ Nenhum caso redundante
- ✅ Equilíbrio positivos/negativos (conforme `testBalance`; default: 60% negativos, 40% positivos)

---

## 📐 Regras de Consolidação

### CONSOLIDAR (mesmo caso de teste) quando:
- ✅ ACs estão na mesma tela e são ações sequenciais do usuário
- ✅ Um AC é pré-condição natural de outro
- ✅ ACs descrevem estados do mesmo componente
- ✅ ACs possuem validação de campo com padrão idêntico

### SEPARAR (casos distintos) quando:
- ❌ ACs testam comportamentos independentes
- ❌ ACs têm pré-condições conflitantes
- ❌ ACs envolvem integrações externas distintas
- ❌ ACs descrevem fluxos alternativos com ramificações

---

## 📄 Formato de Saída

### Cabeçalho do Documento

```markdown
# Casos de Teste — [Nome da Funcionalidade]
**US/PBI:** [US-ID]
**Data:** [data atual]
**Responsável:** [nome do QA]
**Versão:** 1.0

---
```

### Estrutura de um Caso de Teste — PORTUGUÊS

```markdown
## CT-[ID] — [Título descritivo do caso de teste]

**Tipo:** [Positivo / Negativo]
**Prioridade:** [Alta / Média / Baixa]
**Marcador:** [SMOKE] / [REGRESSÃO] / [FUNCIONAL] / [VALIDAÇÃO]
**Critério de Aceite coberto:** AC-[número(s)]
{{STEP_TITLE_PATTERN_LINE}}{{STEP_ADDITIONAL_FIELDS_LINES}}

**Pré-condições:**
- [Condição 1 necessária antes de iniciar o teste]
- [Condição 2, se houver]

**Dados de Entrada:**
| Campo | Valor |
|-------|-------|
| [campo] | [valor] |

**Passos:**

| # | Ação | Resultado Esperado |
|---|------|-------------------|
| Passo 1 | [Ação clara e objetiva] | [Resultado verificável] |
| Passo 2 | [Ação clara e objetiva] | [Resultado verificável] |
| Passo N | [Ação clara e objetiva] | [Resultado verificável] |

**Resultado Final Esperado:**
> [Descrição do estado final do sistema após o último passo]

---
```

### Estrutura de um Caso de Teste — ENGLISH

```markdown
## TC-[ID] — [Descriptive title of the test case]

**Type:** [Positive / Negative]
**Priority:** [High / Medium / Low]
**Tag:** [SMOKE] / [REGRESSION] / [FUNCTIONAL] / [VALIDATION]
**Acceptance Criteria covered:** AC-[number(s)]
{{STEP_TITLE_PATTERN_LINE}}{{STEP_ADDITIONAL_FIELDS_LINES}}

**Preconditions:**
- [Condition 1 required before starting the test]
- [Condition 2, if any]

**Input Data:**
| Field | Value |
|-------|-------|
| [field] | [value] |

**Steps:**

| # | Action | Expected Result |
|---|--------|----------------|
| Step 1 | [Clear and objective action] | [Verifiable result] |
| Step 2 | [Clear and objective action] | [Verifiable result] |
| Step N | [Clear and objective action] | [Verifiable result] |

**Final Expected Result:**
> [Description of the final system state after the last step]

---
```

---

## 🔢 Regras de Numeração

- Se `{{STEP_TITLE_PATTERN}}` for informado, aplicar no campo **Título** do caso de teste.
  - Exemplo: `CT-001` → `CT-001 — Realizar login com credenciais válidas`
- Se não informado, usar numeração sequencial simples: `CT-01`, `CT-02`, etc.
- Em inglês, usar `TC-` (Test Case) em vez de `CT-`.

---

## 📊 Limite de Passos por Caso de Teste

### 🔧 Sintaxe de Parametrização por Ferramenta de Gestão de Testes

Quando um caso de teste for parametrizado (mesma lógica, múltiplos conjuntos de dados), a notação dos parâmetros depende de `{{TEST_MANAGEMENT_TOOL}}`:

| Ferramenta | Sintaxe nos passos e campos de dados |
|------------|--------------------------------------|
| `Azure DevOps Test Plans` | `@paramName` |
| `Jira + Zephyr Scale` | `${paramName}` |
| `Jira + Xray` | `<paramName>` |
| `Jira + AssertThat` | `<paramName>` |
| `Nenhuma` (padrão) | `<paramName>` |

**Exemplos:**

✅ **Azure DevOps Test Plans:**
```markdown
## CT-05 — Validar campo obrigatório vazio [PARAMETRIZADO]

**Parâmetros:**
| @campo  | @mensagem_esperada    |
|---------|-----------------------|
| Nome    | Nome é obrigatório.   |
| E-mail  | E-mail inválido.      |
| CPF     | CPF é obrigatório.    |

| # | Ação | Resultado Esperado |
|---|------|-------------------|
| Passo 1 | Acessar a tela de cadastro | Tela exibida |
| Passo 2 | Limpar o campo @campo e clicar fora | Campo perde o foco |
| Passo 3 | Observar mensagem de validação | A mensagem @mensagem_esperada é exibida em vermelho |
```

✅ **Jira + Zephyr Scale:**
```markdown
| Passo 2 | Limpar o campo ${campo} e clicar fora | Campo perde o foco |
| Passo 3 | Observar mensagem de validação | A mensagem ${mensagem_esperada} é exibida em vermelho |
```

✅ **Jira + Xray / AssertThat / Nenhuma (padrão):**
```markdown
| Passo 2 | Limpar o campo <campo> e clicar fora | Campo perde o foco |
| Passo 3 | Observar mensagem de validação | A mensagem <mensagem_esperada> é exibida em vermelho |
```

> **⚠️ REGRA:** aplicar a mesma sintaxe em **todos** os casos parametrizados do documento. Nunca misturar formatos. Se `{{TEST_MANAGEMENT_TOOL}}` não for informado, usar o padrão `<paramName>`.

---
- Limite máximo de passos: `{{STEP_MAX_STEPS}}` (fallback: **15 passos**)
- Se um fluxo exceder o limite, **dividir em casos de teste complementares** com referência cruzada:
  - `CT-03A — Fluxo de Cadastro (Parte 1: Dados Pessoais)`
  - `CT-03B — Fluxo de Cadastro (Parte 2: Endereço e Confirmação)`

---

## 💡 Exemplo Prático — Login (Português)

```markdown
# Casos de Teste — Login e Autenticação
**US/PBI:** US-42
**Data:** 2025-07-01
**Responsável:** Ana QA
**Versão:** 1.0

---

## CT-01 — Login com credenciais válidas

**Tipo:** Positivo
**Prioridade:** Alta
**Marcador:** [SMOKE] [E2E]
**Critério de Aceite coberto:** AC-1, AC-3

**Pré-condições:**
- Usuário cadastrado no sistema com status ativo
- Acesso à tela de login: `https://app.exemplo.com/login`

**Dados de Entrada:**
| Campo | Valor |
|-------|-------|
| E-mail | usuario@teste.com |
| Senha | Senha@123 |

**Passos:**

| # | Ação | Resultado Esperado |
|---|------|-------------------|
| Passo 1 | Acessar a URL `https://app.exemplo.com/login` | A tela de login é exibida com campos de e-mail e senha |
| Passo 2 | Preencher o campo "E-mail" com `usuario@teste.com` | O valor é inserido corretamente |
| Passo 3 | Preencher o campo "Senha" com `Senha@123` | Os caracteres são exibidos como asteriscos |
| Passo 4 | Clicar no botão "Entrar" | O botão fica desabilitado enquanto autentica |

**Resultado Final Esperado:**
> O usuário é autenticado e redirecionado para o dashboard. A mensagem "Bem-vindo, Ana!" é exibida no cabeçalho.

---

## CT-02 — Login com senha incorreta

**Tipo:** Negativo
**Prioridade:** Alta
**Marcador:** [REGRESSÃO] [FUNCIONAL]
**Critério de Aceite coberto:** AC-2

**Pré-condições:**
- Usuário cadastrado no sistema
- Acesso à tela de login

**Dados de Entrada:**
| Campo | Valor |
|-------|-------|
| E-mail | usuario@teste.com |
| Senha | SenhaErrada |

**Passos:**

| # | Ação | Resultado Esperado |
|---|------|-------------------|
| Passo 1 | Acessar a tela de login | A tela de login é exibida |
| Passo 2 | Preencher "E-mail" com `usuario@teste.com` | O valor é inserido |
| Passo 3 | Preencher "Senha" com `SenhaErrada` | Os caracteres são ocultados |
| Passo 4 | Clicar em "Entrar" | Sistema processa a autenticação |

**Resultado Final Esperado:**
> A mensagem de erro "E-mail ou senha incorretos." é exibida em vermelho. O usuário permanece na tela de login. O campo de senha é limpo.

---

## CT-03 — Validações de campos obrigatórios

**Tipo:** Negativo
**Prioridade:** Média
**Marcador:** [VALIDAÇÃO] [REGRESSÃO]
**Critério de Aceite coberto:** AC-4, AC-5

**Pré-condições:**
- Acesso à tela de login

**Passos:**

| # | Ação | Resultado Esperado |
|---|------|-------------------|
| Passo 1 | Acessar a tela de login | A tela de login é exibida |
| Passo 2 | Deixar o campo "E-mail" em branco e clicar fora do campo | A mensagem "E-mail é obrigatório." é exibida em vermelho |
| Passo 3 | Preencher "E-mail" com valor sem formato válido (`abc`) e clicar fora | A mensagem "Informe um e-mail válido." é exibida |
| Passo 4 | Deixar o campo "Senha" em branco e clicar em "Entrar" | A mensagem "Senha é obrigatória." é exibida |

**Resultado Final Esperado:**
> Todas as mensagens de validação são exibidas. O formulário não é submetido.

---

## 📋 Matriz de Rastreabilidade

| AC | Descrição | Casos de Teste |
|----|-----------|----------------|
| AC-1 | Login com dados válidos deve autenticar | CT-01 |
| AC-2 | Login com senha incorreta deve exibir erro | CT-02 |
| AC-3 | Login bem-sucedido redireciona para dashboard | CT-01 |
| AC-4 | Campos obrigatórios devem exibir validação | CT-03 |
| AC-5 | E-mail deve ter formato válido | CT-03 |

**Cobertura:** 5/5 ACs cobertos ✅
```

---

## 💡 Exemplo Prático — Login (English)

```markdown
# Test Cases — Login and Authentication
**US/PBI:** US-42
**Date:** 2025-07-01
**Owner:** Ana QA
**Version:** 1.0

---

## TC-01 — Login with valid credentials

**Type:** Positive
**Priority:** High
**Tag:** [SMOKE] [E2E]
**Acceptance Criteria covered:** AC-1, AC-3

**Preconditions:**
- User registered in the system with active status
- Access to login screen: `https://app.example.com/login`

**Input Data:**
| Field | Value |
|-------|-------|
| Email | user@test.com |
| Password | Password@123 |

**Steps:**

| # | Action | Expected Result |
|---|--------|----------------|
| Step 1 | Navigate to `https://app.example.com/login` | The login screen is displayed with email and password fields |
| Step 2 | Fill the "Email" field with `user@test.com` | The value is entered correctly |
| Step 3 | Fill the "Password" field with `Password@123` | Characters are displayed as asterisks |
| Step 4 | Click the "Sign In" button | Button is disabled while authenticating |

**Final Expected Result:**
> The user is authenticated and redirected to the dashboard. The message "Welcome, Ana!" is displayed in the header.

---
```

---

## 📁 Arquivo de Saída

- Salvar em: `fastqa/manual_test/test_cases/[US-ID]/[US-ID]_test_cases.md`
- Nomear o arquivo com o identificador da US/PBI
- Se o arquivo já existir, **perguntar ao usuário se deseja sobrescrever ou adicionar novos casos**

---

## 🔗 Campos Adicionais por Caso de Teste

Se `{{STEP_ADDITIONAL_FIELDS}}` for informado (lista de campos separados por vírgula, ex: "Objective, Precondition" ou "Story Points, Épico"), para cada caso de teste:
1. Posicionar cada campo **entre o cabeçalho** (Tipo, Prioridade, Marcador, Critério de Aceite) **e a seção Pré-condições**.
2. Gerar um valor contextual relevante para cada campo, baseado no objetivo específico do caso de teste.
3. Formato:
   ```markdown
   **NomeDoCampo1:** [valor gerado contextualmente para este caso de teste]
   **NomeDoCampo2:** [valor gerado contextualmente para este caso de teste]
   ```
4. O valor **não é fixo** — deve refletir o objetivo e contexto específico daquele caso de teste.

> **Expansão do placeholder `{{STEP_ADDITIONAL_FIELDS_LINES}}`** nos templates de estrutura acima:
> - Se **não houver** campos adicionais → remover a linha inteiramente (não deixar linha vazia extra)
> - Se **houver** campos → expandir para uma linha `**NomeDoCampo:** [valor contextual]` por campo, separadas por nova linha

---

## 💬 Recomendações do QA

Se `{{STEP_QA_RECOMMENDATIONS}}` for informado, exibir no topo do documento:

```markdown
> ⚠️ **Observações do QA:** [Recomendações informadas]
```
