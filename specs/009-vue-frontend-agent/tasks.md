# Agent Development Tasks: ava-prototype v1.1.0

**Plan**: `specs/009-vue-frontend-agent/plan.md`  
**Agent ID**: `ava-prototype` | **Phase**: `F3` | **Module**: `prototype`

> Esta é uma **revisão MINOR** de um agente existente (1.0.0 → 1.1.0).  
> Nenhum novo agente é criado. Nenhuma alteração de schema JSON.  
> Complete as categorias sequencialmente. Use [P] para tasks paralelizáveis dentro de uma categoria.  
> Categorias 4, 5, 6 e 7 podem rodar em paralelo após a Categoria 2 concluir.

---

## Category 1 — Frontmatter & Contract Definition

Deve ser concluída antes de qualquer outra categoria. Desbloqueia tudo.

- [x] **1.1** Abrir `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` e atualizar o frontmatter YAML:
  - `version: "1.0.0"` → `version: "1.1.0"`
  - Verificar que `name: "ava-prototype"` está correto (padrão `^ava-[a-z0-9-]+$`)
  - Verificar que `allowed-tools: Read, Write, Edit` está correto (somente ferramentas válidas do Claude Code)
  - Verificar que `description` está em PT-BR com frases `Ativa com:` incluindo os 5 triggers existentes
  - **NÃO** adicionar campos `phase`, `module`, `inputs`, `outputs` ao frontmatter

- [x] **1.2** Atualizar a seção `## Output Contract` em `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`:
  - Adicionar ao bloco `prototype_gate_result` os 3 campos novos:
    ```yaml
    ux_heuristics_applied: [] # ex: ["H1","H2","H4","H5","H6","H9"]
    form_validation_applied: false # true se ao menos 1 formulário com validação
    error_pattern_applied: false # true se ao menos 1 padrão de erro implementado
    ```
  - Atualizar as condições de `status: "PASS"` para incluir:
    - `form_validation_applied = true` quando user-journeys.md contém formulários
    - `ux_heuristics_applied` contém ao menos H1, H4, H6, H9
  - Manter todos os campos existentes do contrato inalterados (backward compatibility)

- [x] **1.3** Verificar que os paths de output em `## Output Contract` continuam corretos:
  - `projects/{project_name}/outputs/tobe/prototype/index.html`
  - `projects/{project_name}/outputs/tobe/prototype/screen-list.md`
  - `projects/{project_name}/outputs/tobe/prototype/demo-script.md`
  - `projects/{project_name}/outputs/tobe/prototype/figma-spec.md`
  - Confirmar que usam `{project_name}` em minúsculas (NÃO `{PROJECT_NAME}`)

---

## Category 2 — Agent Behavior & Instructions

Depende da Categoria 1 concluída.

- [x] **2.1** Atualizar a seção `## Pre-Execution — Leitura Obrigatória` em `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`:
  - Adicionar como **item 5 (opcional)**:
    ```
    5. `projects/{project_name}/outputs/asis/docs/functional-requirements.md` — regras de negócio
       AS-IS para enriquecer labels, campos e validações específicas do domínio
       - **Opcional:** se ausente, o agente prossegue sem ele; registrar `⚠️ functional-requirements.md ausente — enrichment skipped` no Pre-Flight
    ```
  - Atualizar o bloco `PRE-FLIGHT CHECK` para listar `functional-requirements.md` com indicador `[⚠️ opcional]`

- [x] **2.2** Adicionar seção `## Regras de UX — Heurísticas Nielsen-Norman (H1–H10)` no body do agente, após a seção `## Regras de Consistência com o Design System`. A seção deve conter instrução PT-BR com padrão HTML correspondente a cada heurística:
  - **H1 Visibilidade do status**: gerar `<nav class="breadcrumb">` + `<title>` de página em cada `<section class="screen">`; loading spinner mockado em botões de submissão
  - **H2 Correspondência com o mundo real**: labels usam terminologia do domínio de negócio extraída de `user-journeys.md` e `functional-requirements.md` (ex: "Nota Fiscal", "CNPJ", "Razão Social")
  - **H3 Controle e liberdade**: todo `<form>` deve ter `<button type="button" class="btn-cancel">Cancelar</button>` + `<button type="button" class="btn-back">← Voltar</button>`; ações destrutivas (excluir, cancelar pedido) disparam `showConfirmModal()`
  - **H4 Consistência e padrões**: botão primário sempre `class="btn-primary"` com cor `var(--color-primary-500)`; botão destrutivo sempre `class="btn-danger"`; tabela sempre `class="data-table"`; usar os mesmos CSS custom properties em todas as telas
  - **H5 Prevenção de erros**: implementar `showConfirmModal(title, message, onConfirm)` para ações destrutivas; desabilitar botão de submit durante simulação de processamento (`btn.disabled = true`)
  - **H6 Reconhecer e não lembrar**: todo `<input>` e `<select>` deve ter `<label>` visível (NÃO usar placeholder como único label); campos de formato complexo têm `<span class="field-hint">` com exemplo (ex: "00.000.000/0001-00")
  - **H7 Flexibilidade e eficiência**: documentar atalhos de teclado no `demo-script.md` (ex: `Ctrl+S` para salvar, `Esc` para fechar modal); tooltips `title="..."` em ícones de ação
  - **H8 Design estético e minimalista**: não exibir mais de 7±2 itens por seção de navegação; ocultar campos avançados em `<details>` colapsável; hierarquia visual usando `--font-size-lg/md/sm`
  - **H9 Recuperação de erros**: mensagens de erro devem descrever o problema + sugerir ação corretiva (ex: "CPF inválido — Verifique os dígitos e tente novamente"); NÃO usar mensagens genéricas como "Erro" ou "Falha"
  - **H10 Ajuda e documentação**: campos com formato específico têm `data-tooltip="..."` com `<div class="tooltip">` exibido em `focus`; seção de ajuda `<aside class="help-panel">` colapsável por BC
  - **Acessibilidade (RNF03)**: botões de ícone sem texto visível DEVEM ter `aria-label="..."` e `title="..."` (ex: `<button aria-label="Excluir registro" title="Excluir">🗑</button>`); confirmar que CSS custom properties de cor primária e de erro satisfazem contraste 4.5:1 contra fundo branco (`--color-primary` ≥ #0d47a1 ou equivalente; `--color-error` ≥ #b71c1c ou equivalente)

- [x] **2.3** Adicionar seção `## Validação de Formulários` no body do agente, após as regras de UX. A seção deve instruir o agente a gerar o seguinte padrão em todo `<form>` do protótipo:

  **Estrutura HTML de campo com validação:**

  ```html
  <div class="field-group">
    <label for="{fieldId}"
      >{Label} <span class="required-mark" aria-hidden="true">*</span></label
    >
    <input
      id="{fieldId}"
      name="{fieldName}"
      type="{type}"
      required
      aria-required="true"
      aria-invalid="false"
      aria-describedby="{fieldId}-error"
    />
    <span
      id="{fieldId}-error"
      class="error-msg"
      role="alert"
      aria-live="polite"
    ></span>
  </div>
  ```

  **Lógica JS de validação (Constraint Validation API — sem CDN):**

  ```js
  function validateForm(form) {
    let firstInvalid = null;
    form
      .querySelectorAll("[required], [pattern], [minlength], [maxlength]")
      .forEach((field) => {
        const errorEl = document.getElementById(field.id + "-error");
        if (!field.checkValidity()) {
          field.setAttribute("aria-invalid", "true");
          field.classList.add("field-error");
          if (errorEl) errorEl.textContent = getFieldErrorMessage(field);
          if (!firstInvalid) firstInvalid = field;
        } else {
          field.setAttribute("aria-invalid", "false");
          field.classList.remove("field-error");
          if (errorEl) errorEl.textContent = "";
        }
      });
    if (firstInvalid) {
      firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
      firstInvalid.focus();
    }
    return !firstInvalid;
  }

  function getFieldErrorMessage(field) {
    if (field.validity.valueMissing)
      return (
        field.labels[0]?.textContent?.replace("*", "").trim() + " é obrigatório"
      );
    if (field.validity.typeMismatch && field.type === "email")
      return "Informe um e-mail válido (ex: usuario@dominio.com)";
    if (field.validity.patternMismatch)
      return field.dataset.errorMsg || "Formato inválido";
    if (field.validity.tooShort) return `Mínimo ${field.minLength} caracteres`;
    if (field.validity.tooLong) return `Máximo ${field.maxLength} caracteres`;
    return "Valor inválido";
  }
  ```

  **Mensagem de sucesso após submit válido:**

  ```js
  function showSuccessToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast toast-success";
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }
  ```

  **CSS obrigatório para estado de erro:**

  ```css
  .field-error {
    border-color: var(--color-error, #d32f2f);
  }
  .error-msg {
    color: var(--color-error, #d32f2f);
    font-size: var(--font-size-sm, 0.75rem);
    display: block;
    margin-top: 4px;
  }
  .toast-success {
    background: var(--color-success, #2e7d32);
    color: #fff;
    padding: 12px 20px;
    border-radius: 4px;
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 1000;
  }
  ```

  **Regra**: todo formulário com campos marcados como `required` em `user-journeys.md` → `form_validation_applied = true`

  **Reset após sucesso (CA03-success)**: após `showSuccessToast()`, o handler de submit DEVE chamar `form.reset()` para retornar o formulário ao estado inicial; limpar todos os `aria-invalid` e `error-msg` dos campos chamando `form.querySelectorAll('[aria-invalid]').forEach(f => { f.setAttribute('aria-invalid','false'); f.classList.remove('field-error'); })`.

- [x] **2.4** Adicionar seção `## Padrões de Mensagem de Erro do Sistema` no body do agente, após a seção de validações. A seção define 3 camadas de erro:

  **Camada 1 — Modal (erros bloqueantes):**

  ```js
  function showErrorModal(title, message, correlationId) {
    const id =
      correlationId ||
      "ERR-" +
        new Date().toISOString().slice(0, 10).replace(/-/g, "") +
        "-" +
        String(Math.floor(Math.random() * 999) + 1).padStart(3, "0");
    document.getElementById("error-modal-title").textContent =
      title || "Ocorreu um erro inesperado";
    document.getElementById("error-modal-msg").textContent =
      message ||
      "Tente novamente. Se o problema persistir, contacte o suporte.";
    document.getElementById("error-modal-id").textContent = "ID: " + id;
    document.getElementById("error-modal").style.display = "flex";
  }
  ```

  **HTML do modal de erro (presente no body, oculto por padrão):**

  ```html
  <div
    id="error-modal"
    class="modal-overlay"
    style="display:none"
    role="dialog"
    aria-modal="true"
    aria-labelledby="error-modal-title"
  >
    <div class="modal-box modal-error">
      <h2 id="error-modal-title">Ocorreu um erro inesperado</h2>
      <p id="error-modal-msg"></p>
      <p class="correlation-id" id="error-modal-id"></p>
      <div class="modal-actions">
        <button
          class="btn-primary"
          onclick="document.getElementById('error-modal').style.display='none'"
        >
          Fechar
        </button>
      </div>
    </div>
  </div>
  ```

  **Camada 2 — Toast (erros não-bloqueantes):**

  ```js
  function showErrorToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast toast-error";
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 6000);
  }
  ```

  **Camada 3 — Inline Banner (degradação parcial):**

  ```html
  <div class="alert-banner alert-warning" role="alert" style="display:none">
    <span class="alert-icon">⚠</span>
    <span class="alert-message"
      >Dados parcialmente carregados. Algumas informações podem estar
      desatualizadas.</span
    >
  </div>
  ```

  **Botão "Simular Erro" obrigatório em cada tela de formulário:**

  ```html
  <button
    type="button"
    class="btn-secondary btn-simular-erro"
    onclick="showErrorModal('Falha na comunicação com o servidor', 'Não foi possível processar sua solicitação. Verifique sua conexão e tente novamente.')"
  >
    Simular Erro
  </button>
  ```

  **Regra**: ao menos 1 tela com botão "Simular Erro" → `error_pattern_applied = true`

- [x] **2.5** Atualizar a seção `## Regras de Rastreabilidade por Tela` para incluir campo `ux_heuristics` no metadado HTML de cada tela:

  ```html
  <!-- Prototype metadata
    Screen     : Nome da tela
    BC         : Nome do bounded context
    API        : METHOD /v1/endpoint
    AS-IS ref  : frmNomeTela (or "new screen — justified: <razão>")
    UX rules   : H1,H4,H6,H9 (lista de heurísticas aplicadas nesta tela)
  -->
  ```

- [x] **2.6** Atualizar a seção `## Protocolo de Handoff para ava-stack-orchestrator` para incluir os 3 campos novos no exemplo do `prototype_gate_result` e suas regras de preenchimento:
  - `ux_heuristics_applied: ["H1","H2","H4","H5","H6","H9"]` — derivado dos metadados de cada tela
  - `form_validation_applied: true` — `true` se ao menos 1 `<form>` com `validateForm()` foi gerado
  - `error_pattern_applied: true` — `true` se ao menos 1 botão "Simular Erro" + `showErrorModal()` presente no `index.html`

- [x] **2.7** Adicionar instrução de geração da seção `## UX Heuristics Checklist` no `figma-spec.md` ao body do agente (resolve RNF02):
  - A instrução deve especificar o formato da tabela:

    ```markdown
    ## UX Heuristics Checklist

    | Heurística                          | Tela 1 | Tela 2 | ... |
    | ----------------------------------- | ------ | ------ | --- |
    | H1 Visibilidade do status           | ✅     | ✅     |     |
    | H2 Correspondência com o mundo real | ✅     | ✅     |     |
    | H3 Controle e liberdade             | ✅     | ⚠️     |     |
    | H4 Consistência e padrões           | ✅     | ✅     |     |
    | H5 Prevenção de erros               | ✅     | N/A    |     |
    | H6 Reconhecer e não lembrar         | ✅     | ✅     |     |
    | H7 Flexibilidade e eficiência       | ⚠️     | N/A    |     |
    | H8 Design estético e minimalista    | ✅     | ✅     |     |
    | H9 Recuperação de erros             | ✅     | ✅     |     |
    | H10 Ajuda e documentação            | ✅     | ⚠️     |     |
    ```

  - Legenda: `✅` = satisfeito | `⚠️` = parcialmente satisfeito | `N/A` = não aplicável para esta tela
  - A tabela deve ser preenchida pelo agente para cada tela gerada no `index.html`

- [x] **2.8** Adicionar instrução de geração das seções obrigatórias no `demo-script.md` ao body do agente (resolve plan §8 Phase 1 e CA03):
  - Seção `## Cenários de Erro (CA03)` com passos numerados para demonstrar:
    1. Validação de campo obrigatório: submeter formulário vazio → campo fica vermelho + mensagem de erro embaixo do campo
    2. Submit válido: preencher todos os campos corretamente → toast de sucesso + formulário resetado (`form.reset()`)
    3. Erro do sistema: clicar em "Simular Erro" → modal com identificador de correlação no formato `ERR-YYYYMMDD-NNN`
  - Seção `## Atalhos de Teclado (H7)` documentando os atalhos implementados (ex: `Esc` fecha modal, `Tab` navega entre campos)
  - Ambas as seções são obrigatórias para `prototype_gate_result.status: "PASS"`

---

## Category 3 — Shared Schema Updates

**SKIP** — plan seção 7 confirma: `agent-task.schema.json` NÃO requer alteração; `agent-result.schema.json` NÃO requer alteração. Os novos campos do `prototype_gate_result` são extensão do bloco YAML inline do agente, não do schema JSON formal.

---

## Category 4 — Module Registration

Pode rodar em paralelo com Categorias 5, 6 e 7 após Categoria 2 concluir.

- [x] **4.1** Atualizar `src/modules/ava-fabric-agents/prototype/module.yaml`:
  - Alterar `version: "1.0.0"` → `version: "1.1.0"`
  - Verificar que `agents[0].id = ava-prototype`, `file = agents/prototype-agent.md` estão corretos
  - Verificar que `skill: ava-prototype` está presente na entrada do agente (obrigatório para agentes user-facing — Constitution Article IV); adicionar a linha se ausente
  - **NÃO** criar nova entrada de agente (ava-prototype já está registrado)

- [x] **4.2** Confirmar que o top-level `module.yaml` na raiz do repo **NÃO** precisa de atualização (nenhum novo módulo/fase criado — apenas revisão de agente existente)

---

## Category 5 — Quality Gate Checklists

Pode rodar em paralelo com Categorias 4, 6 e 7 após Categoria 2 concluir.

- [x] **5.1** Verificar que o bloco `PRE-FLIGHT CHECK` no agente está atualizado para listar os 6 inputs (5 originais + `functional-requirements.md`) com indicadores corretos:
  - `[✅]` para inputs presentes
  - `[❌]` para inputs obrigatórios ausentes (→ `DECISION: BLOCKED`)
  - `[⚠️ opcional]` para `functional-requirements.md` e `api-map.md` (não bloqueiam)

- [x] **5.2** [P] Confirmar que as condições `DECISION: PROCEED` vs `DECISION: BLOCKED` estão corretas:
  - `BLOCKED` se: `user-journeys.md` ausente OU `design-system.md` ausente OU `bounded-context-map.md` ausente
  - `PROCEED` se: os 3 obrigatórios presentes (independente de api-map.md ou functional-requirements.md)

- [x] **5.3** [P] Verificar que as condições de `prototype_gate_result.status: "PASS"` cobrem os novos critérios CA01/CA02/CA03:
  - `screen_count > 0` (CA01)
  - `form_validation_applied = true` quando user-journeys.md contém formulários (CA03)
  - `ux_heuristics_applied` contém H1, H4, H6, H9 (RNF02)

---

## Category 6 — Acceptance Validation & QA Integration

Pode rodar em paralelo com Categorias 4, 5 e 7 após Categoria 2 concluir.

- [x] **6.1** Confirmar que os scenarios CA01, CA02, CA03 em `specs/009-vue-frontend-agent/spec.md` seção 4 são completos e não ambíguos:
  - CA01-nominal (Given 3 jornadas → Then index.html com 3 telas navegáveis)
  - CA01-EDGE (Given user-journeys.md ausente → Then Pre-Flight BLOCKED)
  - CA02-nominal (Given todos os inputs → Then PRE-FLIGHT todos [✅])
  - CA02-EDGE (Given api-map.md ausente → Then `api_source: openapi-derived`, status PASS)
  - CA03-form-error (Given campo obrigatório vazio → Then borda vermelha + `aria-invalid="true"`)
  - CA03-success (Given submit válido → Then toast verde)
  - CA03-system-error (Given botão "Simular Erro" → Then modal com ERR-YYYYMMDD-NNN)

- [x] **6.2** [P] Executar o agente revisado contra `projects/test-determinism/` para validar:
  - `outputs/tobe/prototype/index.html` gerado e abre em browser com `file://`
  - `outputs/tobe/prototype/screen-list.md` lista todas as telas com colunas `Status` e `api_source`
  - `outputs/tobe/prototype/demo-script.md` contém seção "Cenários de Erro (CA03)"
  - `outputs/tobe/prototype/figma-spec.md` contém tabela UX Heuristics Checklist H1–H10
  - `prototype_gate_result` emitido antes de COMPLETED com `status: "PASS"`

- [x] **6.3** [P] Validar manualmente o `index.html` gerado no browser (conforme roteiro em `quickstart.md`):
  - Cenário 1: navegação entre telas funcionando
  - Cenário 3: campo obrigatório vazio → borda vermelha + scroll até o campo
  - Cenário 3: submit válido → toast verde
  - Cenário 3: botão "Simular Erro" → modal com identificador de correlação

- [x] **6.4** [P] Mapear scenarios CA01–CA03 como inputs para F5 QA:
  - Referenciá-los como `BR-F3-01`, `BR-F3-02`, `BR-F3-03` em `ava-qa-behavior-mapping`
  - Confirmar que os cenários usam formato `Given/When/Then` padrão Gherkin

- [x] **6.5** Confirmar que nenhum artifact existente de outros agentes foi modificado ou deletado durante a revisão (regressão — outputs de F1/F2 intactos)

- [x] **6.6** [P] Validar comportamento de RNF04 (limite de telas) conforme `projects/test-determinism/`:
  - Se o projeto tiver ≤15 telas: todas geradas normalmente; `screen-list.md` não contém entradas `deferred`
  - Se o projeto tiver >15 telas: `screen-list.md` contém telas com `status: "deferred"` e justificativa; `prototype_gate_result.missing_inputs` lista as telas não geradas com prefixo `"screen-deferred:"`
  - Se `test-determinism` tiver <16 telas: documentar como "testado via inspecção de instrução" no relatório de validação

---

## Category 7 — Documentation & Catalog Update

Pode rodar em paralelo com Categorias 4, 5 e 6 após Categoria 2 concluir.

- [x] **7.1** [P] Atualizar `.github/skills/ava-prototype/SKILL.md` — adicionar leitura opcional do novo input:

  ```markdown
  Opcionalmente, se disponível, leia também:
  `projects/{PROJECT_NAME}/outputs/asis/docs/functional-requirements.md`
  (usado para enriquecer labels e validações com terminologia do negócio)
  ```

  Manter o restante do SKILL.md inalterado (estrutura de 3 passos existente).

- [x] **7.2** [P] Adicionar entrada ao `CHANGELOG.md` conforme rascunho em `specs/009-vue-frontend-agent/plan.md` seção 11:

  ```markdown
  ## [1.1.0] — 2026-07-15

  ### Added (ava-prototype)

  - Regras de UX baseadas nas 10 heurísticas de Nielsen-Norman (H1–H10)
  - Validação de formulários client-side usando Constraint Validation API (sem CDN)
  - Padrões de mensagem de erro do sistema em 3 camadas: modal, toast, inline banner
  - Input opcional `functional-requirements.md` para enriquecer protótipo com regras AS-IS
  - Checklist H1–H10 por tela no `figma-spec.md`
  - Seção "Cenários de Erro (CA03)" no `demo-script.md`
  - Campos adicionais em `prototype_gate_result`: `ux_heuristics_applied`, `form_validation_applied`, `error_pattern_applied`

  ### Changed (ava-prototype)

  - Versão atualizada: 1.0.0 → 1.1.0
  ```

- [x] **7.3** [P] Atualizar `docs/agents-catalog.md` — encontrar entrada de `ava-prototype` e atualizar:
  - `version`: `"1.0.0"` → `"1.1.0"`
  - `description`: adicionar menção a UX heurísticas e validação de formulário
  - Verificar que `outputs` lista os 4 artefatos de saída (index.html, demo-script.md, figma-spec.md, screen-list.md)

---

## Dependency Graph

```
Category 1 (Frontmatter & Contract)
    └─→ Category 2 (Behavior & Instructions)
              ├─→ Category 4 (Module Registration)   [P com 5, 6, 7]
              ├─→ Category 5 (Quality Gate)           [P com 4, 6, 7]
              ├─→ Category 6 (Acceptance Validation)  [P com 4, 5, 7]
              └─→ Category 7 (Documentation)          [P com 4, 5, 6]
```

Category 3 (Schema Updates): SKIPPED

---

## Parallel Execution

Após Category 2 concluída, as seguintes tasks podem ser executadas em paralelo:

| Grupo A  | Grupo B       | Grupo C       |
| -------- | ------------- | ------------- |
| 4.1, 4.2 | 5.1, 5.2, 5.3 | 7.1, 7.2, 7.3 |

Category 6 tasks (6.2, 6.3) requerem Category 2 completa + agente executado contra test-determinism.

---

## Completion Checklist

- [x] Todas as 7 categorias completas (Categoria 3 skipped conforme justificativa)
- [x] SKILL.md atualizado com novo input opcional (`.github/skills/ava-prototype/SKILL.md`)
- [x] Frontmatter `version: "1.1.0"` em `prototype-agent.md`
- [x] `module.yaml` version `"1.1.0"` commitado com campo `skill: ava-prototype` presente
- [x] Agente validado contra `projects/test-determinism/` — todos os 4 outputs produzidos (Categoria 6)
- [x] Validação manual do `index.html` no browser: form validation + toast + error modal funcionando
- [x] `figma-spec.md` contém seção `## UX Heuristics Checklist` com tabela H1–10 × telas
- [x] `demo-script.md` contém seões `## Cenários de Erro (CA03)` e `## Atalhos de Teclado (H7)`
- [x] Comportamento RNF04 (>15 telas) validado conforme task 6.6
- [x] `docs/agents-catalog.md` atualizado com v1.1.0
- [x] `CHANGELOG.md` entrada commitada
- [x] Nenhuma regressão em outputs de F1/F2 (Category 6.5)
