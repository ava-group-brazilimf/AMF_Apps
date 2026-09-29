# Feature Spec: Revisão do Agente de Prototipação (ava-prototype)

**Feature**: Agente de Prototype  
**Spec Branch**: `009-vue-frontend-agent`  
**Agent**: `ava-prototype` (revisão do agente existente)  
**Phase**: F3 (Prototype)  
**Version bump**: 1.0.0 → 1.1.0 (MINOR — adição de comportamentos, sem quebra de contrato de saída)

---

## 1. Role (Responsabilidade do Agente)

O agente `ava-prototype` é responsável por gerar protótipos HTML navegáveis que simulam o sistema futuro (TO-BE) de forma fiel às regras de negócio identificadas nas fases anteriores. O protótipo serve como artefato de validação com stakeholders antes do início do Build Cycle.

**Ativação**: `"criar protótipo"`, `"gerar demo"`, `"prototype TO-BE"`, `"wireframes navegáveis"`, `"demo sistema migrado"`.

---

## 2. Functional Requirements

### RF01 — Geração de Protótipo HTML Navegável

O agente DEVE gerar um protótipo HTML único (`index.html`) completamente autocontido (sem dependências externas CDN) que simule o sistema futuro, incluindo:

- Todas as telas mapeadas nas jornadas do usuário (user-journeys.md)
- Navegação funcional entre telas via links e botões
- Menu lateral (sidebar) e barra superior consistentes em todas as telas
- Dados de exemplo (mock data) em listas, tabelas e campos

### RF02 — Consumo de Artefatos de Entrada

O agente DEVE consumir os seguintes artefatos (★ = obrigatório — Pre-Flight BLOCKED se ausente; ○ = opcional — Pre-Flight avisa mas prossegue):

1. ★ `projects/{project_name}/outputs/tobe/docs/design-system.md` — tokens de cor, tipografia, componentes e layout
2. ★ `projects/{project_name}/outputs/tobe/docs/user-journeys.md` — jornadas, telas e fluxos
3. ○ `projects/{project_name}/outputs/tobe/docs/api-map.md` — mapeamento tela→endpoint; fallback: openapi-spec.yaml se ausente
4. ★ `projects/{project_name}/outputs/tobe/docs/bounded-context-map.md` — BC responsável por cada módulo
5. ○ `projects/{project_name}/outputs/asis/docs/functional-requirements.md` — regras de negócio AS-IS para enriquecer labels e validações
6. ○ `projects/{project_name}/outputs/tobe/docs/openapi-spec.yaml` — spec de API (fallback quando api-map.md ausente)

### RF03 — Simulação de Validações de Formulário

O agente DEVE implementar validações client-side em todos os formulários gerados:

- Campos obrigatórios: exibir mensagem vermelha sob o campo ao submeter sem preencher
- Formato inválido (email, CPF, CNPJ, datas): exibir mensagem descritiva junto ao campo
- Comprimento mínimo/máximo: sinalizar visualmente com ícone de erro (✗) e texto explicativo
- Sucesso de submissão: exibir mensagem positiva (toast verde, modal ou banner) confirmando a ação; após exibição do toast, chamar `form.reset()` para retornar o formulário ao estado inicial (limpar todos os campos)
- O estado de erro DEVE ser visível sem rolagem — campo com erro recebe `aria-invalid="true"` e scroll automático

### RF04 — Mensagens de Erro do Sistema

Em cenários de falha simulada (botão "Simular Erro"), o protótipo DEVE exibir:

- Modal ou toast com mensagem amigável, clara e objetiva (sem stack traces)
- Sugestão de ação para o usuário (ex: "Tente novamente" ou "Contacte o suporte")
- Identificador de correlação simulado (ex: `ID: ERR-20240115-001`) para fins de rastreabilidade demonstrativa

### RF05 — Aplicação das Heurísticas de Nielsen-Norman

O HTML gerado DEVE seguir as 10 heurísticas de usabilidade de Nielsen-Norman:

- **H1 Visibilidade do status**: indicadores de carregamento, breadcrumbs e título de página sempre visíveis
- **H2 Correspondência com o mundo real**: labels em linguagem do negócio (ex: "Nota Fiscal" e não "Invoice")
- **H3 Controle e liberdade**: botões "Cancelar" e "Voltar" em todos os formulários
- **H4 Consistência e padrões**: mesmo componente (ex: botão primário azul) para mesma ação em todas as telas
- **H5 Prevenção de erros**: confirmação antes de ações destrutivas (modal de confirmação)
- **H6 Reconhecer e não lembrar**: labels visíveis em todos os campos (sem placeholder-only)
- **H7 Flexibilidade e eficiência**: atalhos de teclado documentados no demo-script.md
- **H8 Design estético e minimalista**: sem informações irrelevantes; hierarquia visual clara
- **H9 Recuperação de erros**: mensagens descritivas + ação corretiva sugerida
- **H10 Ajuda e documentação**: tooltips explicativos em campos complexos (ex: "CNPJ: 00.000.000/0001-00")

### RF06 — Consistência Visual entre Telas

> Nota: RF06 é implementado principalmente pela heurística H4 de RF05. Listado separadamente para rastreabilidade de stakeholder.

- O agente DEVE aplicar os mesmos tokens de CSS (cores, fontes, espaçamentos) definidos em `design-system.md` em todas as telas
- O usuário NÃO deve precisar reaprender a interface ao navegar entre módulos/BCs
- Componentes reutilizáveis (header, sidebar, breadcrumbs, tabelas, botões) DEVEM ser idênticos em todas as telas

---

## 3. Non-Functional Requirements

### RNF01 — Autocontido

O `index.html` DEVE ser um arquivo único sem dependências externas (CSS e JS inline ou base64). Abre corretamente offline com `file://`.

### RNF02 — UX Heuristics Compliance

O protótipo DEVE estar em conformidade com as heurísticas H1–H10 de Nielsen-Norman (conforme RF05). O `figma-spec.md` DEVE incluir uma tabela de checklist H1–H10 por tela.

### RNF03 — Acessibilidade Básica

- `aria-label` em ícones sem texto
- `aria-invalid="true"` em campos com erro
- Contraste mínimo 4.5:1 entre texto e fundo (WCAG AA)
- Navegação por Tab funcional entre campos de formulário

### RNF04 — Desempenho de Geração

O agente DEVE gerar o protótipo completo em uma única invocação, sem dividir em múltiplos passos de geração. Se o projeto tiver mais de 15 telas, o agente DEVE:

- Priorizar as 15 telas de maior relevância (determinadas por frequência nas jornadas do usuário)
- Registrar as telas excluídas no `screen-list.md` com `status: "deferred"` e justificativa de priorização
- Incluir as telas não geradas em `prototype_gate_result.missing_inputs` com prefixo `"screen-deferred:"`

---

## 4. Acceptance Criteria (BDD Scenarios)

### CA01 — Protótipo HTML consistente com regras de negócio

```gherkin
Feature: Geração de Protótipo Navegável

  Scenario: CA01 — Protótipo gerado consistente com jornadas e regras de negócio
    Given o agente recebe user-journeys.md com 3 jornadas (Login, CadastroCliente, EmissaoNF)
    And design-system.md com tokens de cor e componentes Angular Material
    And bounded-context-map.md mapeando 2 BCs (CustomerSupplier, Fiscal)
    When o agente executa a geração do protótipo
    Then é gerado um index.html autocontido com 3 telas navegáveis
    And cada tela reflete os campos, ações e fluxos descritos em user-journeys.md
    And o menu lateral lista os 2 BCs como seções de navegação
    And o screen-list.md lista as 3 telas com status "included"

  Scenario: CA01-EDGE — user-journeys.md ausente
    Given user-journeys.md não existe no output path
    When o agente tenta executar
    Then o agente emite BLOCKED no Pre-Flight Check
    And lista user-journeys.md como missing prerequisite
    And não gera nenhum arquivo de output
```

### CA02 — Consumo dos artefatos necessários

```gherkin
  Scenario: CA02 — Artefatos de entrada consumidos corretamente
    Given todos os artefatos de entrada existem (design-system.md, user-journeys.md, api-map.md, bounded-context-map.md, functional-requirements.md)
    When o agente executa o Pre-Flight Check
    Then todos os inputs aparecem como [✅] no bloco PRE-FLIGHT CHECK
    And o prototype_gate_result.artifacts lista todos os outputs produzidos
    And screen-list.md inclui coluna api_source com valor "api-map"

  Scenario: CA02-EDGE — api-map.md ausente mas openapi-spec.yaml disponível
    Given api-map.md não existe
    And openapi-spec.yaml existe com 10 operações
    When o agente executa o fallback de openapi
    Then screen-list.md lista as telas com coluna api_source "openapi-derived"
    And o prototype_gate_result.missing_inputs inclui "api-map.md"
    And o status do gate é "PASS" (não é bloqueante)
```

### CA03 — Mensagens claras em formulários e navegação

```gherkin
  Scenario: CA03 — Validação de formulário com mensagem de erro
    Given o protótipo inclui a tela "CadastroCliente" com campo Email obrigatório
    When o usuário tenta submeter o formulário sem preencher o Email
    Then o campo Email exibe borda vermelha e mensagem "E-mail é obrigatório"
    And o foco retorna ao campo com erro
    And o botão de submit fica desabilitado durante processamento

  Scenario: CA03 — Mensagem de sucesso após submissão válida
    Given o protótipo inclui a tela "CadastroCliente"
    When o usuário preenche todos os campos corretamente e submete
    Then exibe toast verde com mensagem "Cliente cadastrado com sucesso!"
    And a tela retorna ao estado inicial (formulário limpo)

  Scenario: CA03 — Mensagem de erro do sistema (simulada)
    Given o protótipo inclui botão "Simular Erro" em qualquer tela de formulário
    When o usuário clica em "Simular Erro"
    Then exibe modal com título "Ocorreu um erro inesperado"
    And a mensagem inclui ação sugerida "Tente novamente ou contacte o suporte"
    And exibe um identificador de correlação no formato "ID: ERR-YYYYMMDD-NNN"
```

---

## 5. Out of Scope

- Geração de código Angular ou React real (responsabilidade do `ava-stack-*` agents)
- Backend real ou chamadas HTTP (o protótipo é 100% mock/estático)
- Testes automatizados do protótipo (responsabilidade do `ava-qa-script-generator`)
- Internacionalização (i18n) — o idioma é definido pela linguagem do negócio do projeto

---

## 6. Dependencies

| Artefato Prerequisito                          | Produzido por                  | Obrigatório                          |
| ---------------------------------------------- | ------------------------------ | ------------------------------------ |
| `outputs/tobe/docs/design-system.md`           | `ava-tobe-architecture-design` | SIM                                  |
| `outputs/tobe/docs/user-journeys.md`           | `ava-tobe-user-journeys`       | SIM                                  |
| `outputs/tobe/docs/bounded-context-map.md`     | `ava-tobe-architecture-design` | SIM                                  |
| `outputs/tobe/docs/api-map.md`                 | `ava-docs-tobe`                | NÃO (fallback: openapi-spec.yaml)    |
| `outputs/tobe/docs/openapi-spec.yaml`          | `ava-docs-tobe`                | NÃO (fallback se api-map.md ausente) |
| `outputs/asis/docs/functional-requirements.md` | `ava-asis-documentation`       | NÃO (enriquece regras de negócio)    |

---

## 7. Files to Modify / Create

| Tipo      | Arquivo                                                             | Motivo                                                |
| --------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| MODIFY    | `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` | Adicionar regras de UX, validação e mensagens de erro |
| MODIFY    | `src/modules/ava-fabric-agents/prototype/module.yaml`               | Atualizar versão para 1.1.0                           |
| MODIFY    | `.github/skills/ava-prototype/SKILL.md`                             | Adicionar artefatos funcionais como inputs            |
| NO CHANGE | Output Contract                                                     | Mesmos outputs — nenhuma quebra de contrato           |
