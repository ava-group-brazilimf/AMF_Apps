# Protocolo de Conversão Protótipo → Componente (P2C)

> **Versão:** 1.0.0 · **Data:** 2026-08-04
> Referenciado por: `coder-angular-frontend.md`, `coder-react-frontend.md`
> Spec: `specs/034-prototype-to-component-conversion/`
> Produtor dos artefatos consumidos: `prototype/agents/prototype-agent.md` (F3)

Este documento define as partes **independentes de framework** da conversão do protótipo
navegável (F3) em componentes de frontend (F4): leitura dos artefatos, junção das fontes,
artefato intermediário, vínculo de regras de negócio, junção com o contrato de API, assertion
de fidelidade e códigos de aviso.

As partes **específicas de framework** — tabela de mapeamento de constructs, templates por
arquétipo e o encaixe nos Execution Steps — ficam no corpo de cada agente.

---

## 1. Regras de autoridade

| Pergunta | Fonte autoritativa |
|---|---|
| *Quais* telas existem, seu status, BC, referência AS-IS e endpoint declarado | `screen-list.md` |
| *Como* cada tela é — estrutura, campos, colunas, botões, atributos `aria-*` | `index.html` |
| Valores de token CSS | `design-tokens.json` → `:root` do `index.html` → defaults do agente |
| Inventário de componentes e mapa de interação (**consultivo**, nunca bloqueante) | `figma-spec.md` §2, §4 |
| Método, path e tipos que **viram código** | **contrato OpenAPI** (ver §5) |

⛔ Nenhum agente de F4 escreve em `projects/{project_name}/outputs/tobe/prototype/` — esse
diretório pertence ao agente F3.

**Caminhos de entrada:**

```
projects/{project_name}/outputs/tobe/prototype/index.html
projects/{project_name}/outputs/tobe/prototype/screen-list.md
projects/{project_name}/outputs/tobe/prototype/design-tokens.json
projects/{project_name}/outputs/tobe/prototype/figma-spec.md        (consultivo)
```

---

## 2. Procedimento de extração

### 2.1 Passe P1 — `screen-list.md`

```
1. Localizar a primeira linha que casa com  ^#\s+Prototype Screen List
   → TUDO acima dela é a seção "## Warnings" e NÃO é inventário.
   → SE a seção existir:
       prototype.warnings_section_present = true
       copiar as linhas da tabela para prototype.source_warnings[]
       (re-emitidas em ImplementationNotes.md — o motivo da qualidade reduzida
        precisa sobreviver de F3 até F4)
   → SE o heading não existir (defensivo): usar a primeira tabela markdown cujo
     cabeçalho contenha simultaneamente "Screen" e "Status".

2. Parse da tabela:
   → separar por "|", aplicar trim, descartar a linha de separação "---"
   → ⛔ INDEXAR COLUNAS PELO NOME DO CABEÇALHO, NUNCA POR POSIÇÃO.
     A coluna opcional `api_source` desloca todas as demais.

3. Normalização por linha:
   screen_name  = conteúdo bruto da célula
   screen_id    = kebab(lower(sem-acentos(screen_name)))
   status       = lower(primeiro token antes de " — ")
                  (o protótipo escreve "excluded — design system not applicable")
                  → fora de {included, excluded, deferred} = "unknown"
                    → tratado como "deferred" + P2C-W007
   bc_kebab     = mesma regra de normalização de BC já usada pelo agente
   api_method   \ split de `METHOD /path` entre crases
   api_path     /  → vazio, "—" ou "N/A"  →  api.declared = null
   asis_ref     = null quando a célula começa com "new"
   asis_justification = restante da célula (também guarda a justificativa de
                        priorização RNF04 nas linhas `deferred`)
   api.source_hint = valor da coluna `api_source`, quando presente
```

### 2.2 Passe P2 — `index.html`

**Extração global (uma vez):**

```
shell.topbar   = existe #topbar
shell.sidebar  = existe #sidebar
shell.content  = existe #content
shell.nav_items[] = cada <a href="#view-*"> da sidebar
                    → { label, target_view, bc, group }
shell.global_dialogs = { error_modal:  existe #error-modal,
                         confirm_modal: existe showConfirmModal(),
                         toast_host:    existe showSuccessToast()/showErrorToast() }
tokens_inline  = bloco :root do <style> (fallback de design-tokens.json)
```

**Por `<section id="view-{name}" class="view">`:**

```
view_id         = valor do id
view_slug       = view_id sem o prefixo "view-"
is_initial_view = a lista de classes contém "active"

metadata: parsear o comentário final com
  ^\s*(Screen|BC|API|AS-IS ref|UX rules)\s*:\s*(.*)$

censo de constructs → bloco constructs{} (ver §3)

archetype (avaliado NESTA ORDEM — é o que substitui o template fixo):
  1. <form> com ≥1 .field-group  E  .data-table   → "list-detail"
  2. <form> com ≥1 .field-group                   → "form"
  3. .data-table                                   → "list"
  4. ≥3 blocos de card/KPI, sem form e sem tabela  → "dashboard"
  5. caso contrário                                → "content"
```

### 2.3 Passe P3 — junção

Chaves avaliadas em ordem; a primeira que casar vence. Registrar `join_key_used`:

| Ordem | Chave | `join_key_used` |
|---|---|---|
| 1 | `screen_id == view_slug` | `slug` |
| 2 | metadata `Screen:` normalizado == `screen_name` normalizado | `name` |
| 3 | tupla `(bc, api_method, api_path)` | `endpoint` |
| 4 | similaridade de conjunto de tokens ≥ 0.8 nos nomes normalizados — **aceita apenas se única dentro do mesmo BC** | `fuzzy` |

### 2.4 Passe P4 — matriz de discrepância

| # | `screen-list.md` | `index.html` | Ação | Código |
|---|---|---|---|---|
| A | `included` | presente | Converter. `source: "both"`, `fidelity: "full"` | — |
| B | `included` | **ausente** | **Converter mesmo assim** só a partir da linha: `archetype` default `list`, `fidelity: "metadata-only"`, `source: "screen-list-only"`. Entra no numerador **e** no denominador | `P2C-W005` |
| C | `deferred` | ausente | Não converter. `conversion_required: false`. Emitir linha de TODO em `ImplementationNotes.md`. **Fora** do denominador | — |
| D | `deferred` | **presente** | Converter — o HTML é prova de que foi gerada. `effective_status: "included"`. Entra no denominador | `P2C-W007` |
| E | `excluded` | ausente | Pular. Registrar com `reason: "excluded"`. Fora do denominador | — |
| F | `excluded` | **presente** | **Não** converter — `screen-list.md` é autoridade sobre status. Registrar a contradição | `P2C-W007` |
| G | **ausente** | presente | Tela órfã → converter. `source: "html-only"`, `effective_status: "included"`. Entra no denominador | `P2C-W006` |

**Definição do denominador (escrever literalmente no agente):**

```
effective_status = "included"  SE status == "included"
                             OU (view presente no index.html E status != "excluded")

expected_screens = [s for s in screens if s.effective_status == "included"]
```

Isto satisfaz "100% das telas `included` viram componentes" e ao mesmo tempo é robusto a um
`screen-list.md` desatualizado.

---

## 3. Artefato intermediário — `prototype-conversion-map.json`

**Caminho:** `projects/{project_name}/outputs/tobe/source-code/frontend/prototype-conversion-map.json`

Fica dentro do output root do frontend (não em `outputs/tobe/prototype/`, que pertence a F3),
acompanha o código, é diffável e é referenciado no Handoff.

**Escrito duas vezes:**

1. `phase: "planned"` — logo após o passe P4, com `expected_artifacts[]` preenchido e
   `generated: false`.
2. `phase: "verified"` — após a geração, com o bloco `assertion` completo.

> Gravar os caminhos esperados **antes** de gerar é o que transforma a assertion de fidelidade
> numa checagem pura de existência de arquivo, sem exigir tooling Python novo.

```json
{
  "schema_version": "1.0",
  "artifact_id": "prototype-conversion-map",
  "generated_by": "{agent_id}",
  "agent_version": "{agent_version}",
  "framework": "angular | react",
  "project_name": "{project_name}",
  "trace_id": "{trace_id}",
  "generated_at": "ISO8601",
  "phase": "planned | verified",

  "prototype": {
    "available": true,
    "index_html": "outputs/tobe/prototype/index.html",
    "screen_list": "outputs/tobe/prototype/screen-list.md",
    "design_tokens": "outputs/tobe/prototype/design-tokens.json",
    "design_tokens_source": "design-tokens.json | index-html | default",
    "figma_spec": "outputs/tobe/prototype/figma-spec.md",
    "warnings_section_present": false,
    "source_warnings": []
  },

  "shell": {
    "topbar": true, "sidebar": true, "content": true,
    "nav_items": [
      { "label": "Contas a Pagar", "target_view": "view-ap-list", "bc": "ap", "group": "Financeiro" }
    ],
    "global_dialogs": { "error_modal": true, "confirm_modal": true, "toast_host": true }
  },

  "counts": {
    "screen_list_rows": 0, "status_included": 0, "status_deferred": 0, "status_excluded": 0,
    "html_views": 0, "expected_conversions": 0, "generated_conversions": 0,
    "orphan_html_views": 0, "missing_html_for_included": 0
  },

  "screens": [
    {
      "screen_id": "ap-list",
      "screen_name": "Contas a Pagar — Lista",
      "view_id": "view-ap-list",
      "bc": "ap", "bc_label": "Contas a Pagar",
      "status": "included", "effective_status": "included",
      "source": "both", "join_key_used": "slug",
      "is_initial_view": false,
      "asis_ref": "frmContasPagar", "asis_justification": null,
      "ux_rules": ["H1", "H4", "H6", "H9"],
      "archetype": "list",

      "api": {
        "declared": "GET /v1/contas-pagar",
        "contract_status": "MATCHED | MATCHED_BY_PATH | MATCHED_BY_OPERATION | MISSING_IN_CONTRACT | NO_CONTRACT | NO_ENDPOINT",
        "resolved": { "method": "GET", "path": "/accounts-payable", "operation_id": "listAccountsPayable" },
        "contract_source": "outputs/tobe/docs/openapi/bc03-ap.yaml",
        "divergence": { "type": "method | path | none", "severity": "warning | high", "note": "" }
      },

      "constructs": {
        "data_table": {
          "present": true,
          "columns": [{ "key": "valor", "label": "Valor", "type": "text|money|date|status" }],
          "row_actions": ["edit", "delete"]
        },
        "form": {
          "present": false,
          "fields": [{
            "id": "", "name": "", "label": "", "type": "", "required": false,
            "pattern": null, "minlength": null, "maxlength": null,
            "hint": null, "error_msg": null, "aria_describedby": null,
            "in_advanced_details": false
          }]
        },
        "buttons": { "primary": 1, "danger": 1, "cancel": 0, "back": 1, "simulate_error": 0 },
        "confirm_modal_calls": 1, "error_modal_calls": 0,
        "toasts": { "success": false, "error": true },
        "alert_banner": true, "details_advanced": false,
        "breadcrumb": true, "help_panel": false, "field_hints": 0,
        "status_values": ["pending", "paid", "overdue"],
        "aria": { "labels": 6, "live_regions": 2, "modal_dialogs": 1 }
      },

      "business_rules": ["BR-0012", "FBR-0042"],
      "dropped_constructs": ["btn-simular-erro"],

      "expected_artifacts": [
        { "path": "src/...", "kind": "page | tpl | style | spec | schema | hook", "blocking": true }
      ],
      "generated": false,
      "fidelity": "full | metadata-only"
    }
  ],

  "assertion": {
    "assertion_id": "prototype-screen-conversion",
    "status": "PASS | FAIL | SKIPPED",
    "expected": 0, "generated": 0, "coverage_pct": 0.0,
    "missing": [], "retry_count": 0, "evaluated_at": "ISO8601"
  },

  "prototype_fidelity": "full | partial | degraded | none"
}
```

---

## 4. Vínculo de regras de negócio

### 4.1 A chave de junção já existe

`business_rules_catalog_generator.py` emite, para `category == "form_validation"` (ids
`FBR-nnnn`), os campos `form`, `form_class`, `field`, `component_class`, `event_handlers`,
`has_validation`, `expression`, `unit`, `domain_relevant`. O metadata do protótipo carrega
`AS-IS ref: frmContasPagar`. Portanto **`rule.form == screen.asis_ref` é uma junção direta e
determinística** — sem heurística — para a maior e mais relevante classe de regras de UI.

**Fonte primária:** `projects/{project_name}/outputs/asis/docs/business-rules-catalog.json`
(enumeração 100%). Fallback: `business-rules.md` (apenas resumo curado — nunca usar como fonte
de completude).

### 4.2 Algoritmo de vínculo (avaliado em ordem; registrar `binding`)

| Ordem | Predicado | `binding` | Força |
|---|---|---|---|
| B1 | `lower(rule.form) == lower(screen.asis_ref)` | `exact-form` | **hard** |
| B2 | `rule.unit` casa com `screen.asis_ref` sob o conjunto de sufixos (`u{Nome}.pas`, `{Nome}.pas`, `frm{Nome}`, `{Nome}`) | `unit` | **hard** |
| B3 | `rule.unit` → BC (via bounded-context-map do AS-IS) igual a `screen.bc`, e a tela é a tela primária desse BC (`archetype == "form"`, senão `"list"`) | `bc-fallback` | soft |
| B4 | nenhum dos anteriores | `unbound` | reportado |

### 4.3 Predicado de representabilidade em UI (denominador fechado)

```
ui_representable(rule) :=
     rule.category EM {"form_validation", "validation"}
  OU (rule.category EM {"threshold", "classification"}
      E normalize(rule.target | rule.field) casa com algum nome em
          screen.constructs.form.fields[].name
       OU screen.constructs.data_table.columns[].key)
  OU rule.expression contém um literal de mensagem exibida ao usuário
SENÃO → server_side_only    (NÃO é omissão — ver spec 020 §8)
```

### 4.4 Marcador obrigatório no código

É o que torna a assertion greppável. Imediatamente acima do validator/effect:

```
// Implements: BR-0012 — <expressão, ≤100 caracteres>
```

Regex de detecção: `^\s*//\s*Implements:\s*((BR|FBR)-\d{4})`

### 4.5 Artefato de rastreabilidade

`projects/{project_name}/outputs/tobe/docs/business-rules-implementation-frontend.md`
(legível) **+** irmão machine-readable no mesmo diretório:

```json
{
  "schema_version": "1.0",
  "framework": "angular | react",
  "project_name": "{project_name}",
  "trace_id": "{trace_id}",
  "totals": {
    "catalog_rules": 0, "ui_representable": 0,
    "implemented_hard": 0, "implemented_soft": 0,
    "unbound": 0, "server_side_only": 0
  },
  "rules": [{
    "id": "FBR-0042", "category": "form_validation",
    "asis_form": "frmContasPagar", "screen_id": "ap-form",
    "binding": "exact-form", "status": "IMPLEMENTED | MISSING",
    "file": "src/...", "symbol": "documentoValidator",
    "evidence": "// Implements: FBR-0042 …"
  }],
  "unbound_ui_rules": []
}
```

### 4.6 Assertion de regras de negócio

```
PARA CADA rule em ui_representable:
    hits = grep -R "Implements: {rule.id}" {output_root}/src
    rule.status = hits > 0 ? "IMPLEMENTED" : "MISSING"

ASSERT count(status == "IMPLEMENTED" E binding EM {exact-form, unit})
    == count(ui_representable          E binding EM {exact-form, unit})   # HARD — bloqueante

REPORT business_rules_coverage_pct sobre TODO o conjunto ui_representable  # SOFT — informativo
```

Falha → implementar os validators faltantes e reexecutar (máximo 2 iterações). Persistindo →
`business_rules_status: "PARTIAL"`, ids em `unbound_ui_rules[]`, emitir `P2C-W009`.

> A metade **hard** bloqueia `implementation.status: COMPLETED`. A metade **soft** apenas
> reporta: uma regra com binding `bc-fallback` pode genuinamente não ter tela onde morar, e
> reprovar a execução inteira por causa disso seria desonesto.

---

## 5. Junção com o contrato de API

### 5.1 Normalização (aplicada aos dois lados antes de comparar)

```
método  → maiúsculas
path    → remover barra final
        → /\d+      →  /{id}
        → /:param   →  /{param}
        → comparação de segmentos case-insensitive
        → extrair o prefixo de versão (/v1) para campo separado
prefixo de versão: o OpenAPI normalmente o carrega em servers[].url —
                   comparar strings cruas produz FALSO NEGATIVO
lado contrato → também remover o componente de path de servers[].url antes de indexar
```

**Precedência de contrato** (a mesma já usada pelo agente Angular):

```
1. projects/{project_name}/outputs/tobe/docs/openapi/bc*-{bc-kebab}.yaml   (design-first)
2. projects/{project_name}/outputs/tobe/source-code/backend/openapi/{bc}.yaml  (exportado pelo backend)
```

Construir o índice `(método, path_normalizado) → { operationId, params, requestSchema, responseSchema, tags }`.

### 5.2 Classes de correspondência

| `contract_status` | Condição | Efeito |
|---|---|---|
| `MATCHED` | `(método, path)` exato | gerar a partir do contrato |
| `MATCHED_BY_PATH` | path casa, método difere | contrato vence; `divergence.type: "method"`, severidade `warning` |
| `MATCHED_BY_OPERATION` | sem match de path, mas existe **exatamente uma** operação com `tags[0] == bc` cujo `operationId`/`summary` casa por conjunto de tokens com o nome da tela | contrato vence; `divergence.type: "path"`, severidade `warning` |
| `MISSING_IN_CONTRACT` | contrato existe, nenhum candidato | gerar a camada de dados a partir do endpoint **declarado**, marcado `// ⚠️ Endpoint não presente no contrato OpenAPI`; severidade `high`; reportado no Handoff. **A tela ainda é gerada** — a regra de fidelidade supera a lacuna de contrato |
| `NO_CONTRACT` | nenhum arquivo de contrato para o BC | gerar do endpoint declarado; `api_contract_status[bc] = "MISSING"` + WARNING (comportamento de `specs/021`) |
| `NO_ENDPOINT` | a tela não declara API (`dashboard`, `content`) | sem camada de dados; página estática ou derivada |

### 5.3 Regra de conflito

> **O contrato OpenAPI vence em tudo que vira código** — método, path, `operationId` → nome do
> service/hook, tipos de request e response. O comentário `API:` do protótipo é documentação
> escrita por um agente de UX; o contrato é a verdade do backend, que precisa compilar e
> funcionar na integração.
>
> **Nenhuma divergência é resolvida em silêncio.** Cada uma é registrada em
> `screens[].api.divergence` e renderizada como a tabela `## Divergências Protótipo × Contrato
> de API` em `ImplementationNotes.md` — colunas: Tela · Declarado no protótipo · Resolvido no
> contrato · Tipo · Severidade · Ação sugerida.

Operações do contrato que nenhuma tela referencia **não** são erro — registrar em
`unused_operations[]`.

---

## 6. Assertion de fidelidade

```
E = [s em map.screens SE s.effective_status == "included"]
G = [s em E SE TODOS os s.expected_artifacts com blocking:true existem no filesystem]

ASSERT len(G) == len(E)
```

Execução determinística a partir de `{output_root}` (Node existe nas duas stacks):

```
Bash: node -e "const m=require('./prototype-conversion-map.json'),fs=require('fs');
const E=m.screens.filter(s=>s.effective_status==='included');const miss=[];
for(const s of E)for(const a of s.expected_artifacts)
  if(a.blocking&&!fs.existsSync(a.path))miss.push(s.screen_id+' :: '+a.path);
console.log(JSON.stringify({expected:E.length,
  generated:E.length-new Set(miss.map(x=>x.split(' :: ')[0])).size,
  missing_count:miss.length,missing:miss.slice(0,50)}));"
```

SE `node` ainda não estiver disponível (antes do `npm install`), usar o equivalente em Python.

**Segunda assertion — nível de template.** Pega o falso positivo do arquivo que existe mas
continua sendo o stub genérico. O padrão exato é definido por cada agente; a regra é:

```
ASSERT count(ocorrências do marcador de stub genérico nos arquivos gerados) == 0
```

**Em caso de falha:** gerar exatamente os artefatos faltantes e **reexecutar o mesmo comando**.
Máximo de **3 iterações** (`assertion.retry_count`). Persistindo `missing_count > 0`:

- `assertion.status: "FAIL"`
- `prototype_fidelity: "degraded"`
- Handoff reporta `implementation.status: PARTIAL` — **nunca** `COMPLETED`

Laço limitado. Nunca repetir indefinidamente.

---

## 7. Códigos de aviso (P2C-Wnnn)

### P2C-W001 — Protótipo ausente

Disparado quando **nem** `index.html` **nem** `screen-list.md` existem.

```
╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠️  P2C-W001 — PROTÓTIPO AUSENTE                                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Não encontrado : outputs/tobe/prototype/index.html                      ║
║                   outputs/tobe/prototype/screen-list.md                  ║
║                                                                          ║
║  Efeito : a conversão Protótipo→Componente NÃO será executada.           ║
║           O frontend será gerado com as regras genéricas por bounded     ║
║           context (1 página de lista por BC, template padrão).           ║
║                                                                          ║
║  Ação recomendada : executar @ava-prototype (F3) e re-executar este      ║
║                     agente para obter telas fiéis ao protótipo.          ║
║                                                                          ║
║  prototype_fidelity : none                                               ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**Comportamento: CONTINUAR.** Não há HARD STOP. O `prototype-conversion-map.json` ainda é
gravado, com `prototype.available: false`, `screens: []` e `assertion.status: "SKIPPED"` — a
assertion de fidelidade é **pulada, não reprovada**. A geração cai no comportamento genérico
por BC. `ImplementationNotes.md` ganha a seção `## Fidelidade ao Protótipo` declarando `none`
e o motivo.

### Demais códigos

| Código | Condição | Comportamento |
|---|---|---|
| `P2C-W002` | `screen-list.md` ausente, `index.html` presente | parsear só o HTML; toda view → `effective_status: "included"`; `prototype_fidelity: "partial"` |
| `P2C-W003` | `index.html` ausente, `screen-list.md` presente | converter todas as linhas `included` com `archetype: "list"`; toda tela `fidelity: "metadata-only"`; `prototype_fidelity: "partial"` |
| `P2C-W004` | `design-tokens.json` ausente | derivar `:root` do `index.html`; se também ausente, usar os defaults do agente; registrar `design_tokens_source`. **Substitui qualquer HARD STOP por ausência de tokens** |
| `P2C-W005` | tela `included` sem view no HTML (caso B) | aviso por tela; `fidelity: "metadata-only"` |
| `P2C-W006` | view órfã no HTML (caso G) | aviso por tela; convertida |
| `P2C-W007` | status contraditório (casos D/F) ou token de status não parseável | aviso; a matriz de §2.4 decide |
| `P2C-W008` | divergência protótipo ↔ contrato de API | aviso + linha na tabela de divergências |
| `P2C-W009` | regra de negócio representável em UI não vinculada a nenhuma tela | aviso + `unbound_ui_rules[]` |

Todo código emitido entra em `p2c_warnings[]` no Handoff, no formato `"{código}:{screen_id}"`
(ou só `"{código}"` quando global).

---

## 8. Enum `prototype_fidelity`

| Valor | Condição |
|---|---|
| `full` | protótipo presente, assertion `PASS`, cobertura 100%, sem `P2C-W002`/`W003`, zero telas com `fidelity: "metadata-only"` |
| `partial` | protótipo presente, assertion `PASS`, mas ≥1 tela `metadata-only` **ou** apenas um dos dois artefatos presente |
| `degraded` | protótipo presente, assertion `FAIL` após 3 tentativas |
| `none` | `P2C-W001` |

---

## 9. Campos obrigatórios do Handoff

Todo agente que aplica este protocolo DEVE reportar:

```yaml
prototype_fidelity:          full | partial | degraded | none
prototype_conversion_map:    outputs/tobe/source-code/frontend/prototype-conversion-map.json
screens_expected:            0
screens_converted:           0
screens_coverage_pct:        0.0
screen_assertion:            PASS | FAIL | SKIPPED
design_tokens_source:        design-tokens.json | index-html | default
unit_tests:
  status:                    PASS | BELOW_THRESHOLD | TOOLCHAIN_UNAVAILABLE
  coverage_pct:              { statements: 0, branches: 0, functions: 0, lines: 0 }
business_rules_status:       COMPLETE | PARTIAL
business_rules_coverage_pct: 0.0
api_divergences:             0
p2c_warnings:                []
```

> ⛔ **NUNCA** reportar `implementation.status: COMPLETED` quando:
> - `screen_assertion == FAIL`, ou
> - `business_rules_status == PARTIAL` por falha da metade **hard** da assertion de §4.6, ou
> - `unit_tests.status == BELOW_THRESHOLD`
>
> `unit_tests.status ∈ {PASS, TOOLCHAIN_UNAVAILABLE}` é pré-condição de `COMPLETED`.
> `screen_assertion == SKIPPED` (protótipo ausente) **não** impede `COMPLETED`.

---

## 10. Nota sobre RNF04

O agente `ava-prototype` limita-se a **15 telas incluíveis por invocação** (RNF04); o excedente
vira `deferred`. Esse limite governa o protótipo, **não** o conversor. Num ERP grande haverá
muitas linhas `deferred`, e elas ficam fora do denominador da assertion por definição (caso C
de §2.4).

⚠️ Por isso as telas `deferred` **DEVEM** ser listadas explicitamente em `## TODOs Pendentes`
do `ImplementationNotes.md` — para que ninguém leia `prototype_fidelity: full` como "o sistema
inteiro foi convertido".

---

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](./governance-apps.md)
