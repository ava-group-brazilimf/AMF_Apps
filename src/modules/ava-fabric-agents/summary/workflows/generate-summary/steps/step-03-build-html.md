# Step 03 — Construção do HTML

## Objetivo

Carregar o template HTML Avanade e injetar todos os dados extraídos no Step 02,
produzindo o arquivo HTML final autocontido.

## Template Source

```
src/modules/ava-fabric-agents/summary/templates/html/summary-template.html
```

## Ações

### 3.1 — Carregar template

```
Ler: src/modules/ava-fabric-agents/summary/templates/html/summary-template.html
Armazenar como string mutável: HTML_CONTENT
```

### 3.2 — Substituir placeholders do header

Substituir cada `{{PLACEHOLDER}}` com o valor do `summary-data.json`:

| Placeholder             | Fonte                                       |
| ----------------------- | ------------------------------------------- |
| `{{PROJECT_NAME}}`      | project_context.name                        |
| `{{GENERATED_AT}}`      | timestamp atual (formato: DD/MM/YYYY HH:MM) |
| `{{COVERAGE}}`          | kpis.coverage (ou "N/D")                    |
| `{{SCOPE}}`             | project_context.scope                       |
| `{{EXEC_PCT}}`          | exec_summary.exec_pct                       |
| `{{AGENTS_OK}}`         | exec_summary.agents_ok (done count)         |
| `{{TOTAL_AGENTS}}`      | exec_summary.effective_total (= TOTAL_AGENTS - skipped) |
| `{{AGENTS_ERR}}`        | exec_summary.agents_err (= TOTAL_AGENTS - AGENTS_OK) |
| `{{LEGACY_TECH}}`       | project_context.technology                  |
| `{{TRACE_ID}}`          | project_context.trace_id                    |
| `{{EXECUTIVE_SUMMARY}}` | **NÃO usar mais.** Ver seção 3.2b abaixo    |

### 3.2b — Gerar Executive Summary com estado inicial em inglês (i18n)

O Executive Summary deve ser gerado com o estado inicial em **inglês**.
O builder DEVE inicializar o HTML com `var lang = "en"` por padrão,
independentemente do trigger de invocação; somente `language: pt` explícito ou
troca manual pelo seletor pode selecionar a visão portuguesa.
O seletor PT/EN e os dois dicionários existentes permanecem funcionais para
troca manual após a abertura do artefato. Injetar no objeto JavaScript `D`
(seção 3.4) o texto padrão em inglês; não remover o caminho PT existente.

```javascript
execSummary: {
  pt: "<p>...resumo em português...</p>",
  en: "<p>...summary in English...</p>"
}
```

O template renderizará inicialmente o idioma inglês via `renderExecSummary()`;
`setLang('pt')` continua disponível para troca manual.
O placeholder `{{EXECUTIVE_SUMMARY}}` no HTML **não existe mais** — não tentar substituí-lo.

### 3.3 — Injetar KPIs

Substituir `{{TOTAL_FILES}}`, `{{TEXT_FILES}}`, `{{TOTAL_LOC}}`, etc.
com os valores de `kpis`.
Para campos ausentes → usar `"N/D"`.

### 3.4 — Injetar dados do JavaScript DATA object

Localizar no template o comentário `/* INJECT_DATA_HERE */` e substituir
com o objeto JavaScript gerado a partir de `summary-data.json`.

Substituições obrigatórias de placeholders no objeto `const D`:

- Substituir `{{ARTIFACT_INVENTORY_JSON}}` com JSON.stringify do inventário por agente
- Substituir `{{AGENT_STATUS_JSON}}` com JSON.stringify do mapa de status por agente
- Substituir `{{FILE_TREE_JSON}}` com JSON.stringify(FILE_TREE_JSON) do Step 01.3b
  Fallback: `{}` se FILE_TREE_JSON estiver vazio ou não gerado.
- Substituir `{{SECURITY_REVIEW_JSON}}` com JSON.stringify(securityReview) do Step 2.9
  ⚠️ Usar SEMPRE os dados consolidados do Step 2.9 (33+ linhas) — NUNCA ler `security-findings.json` diretamente aqui
- Substituir `{{FINDINGS_SUMMARY_JSON}}` com JSON.stringify(findingsSummary) do Step 2.9

**Injeção de ccTop (Complexidade Ciclomática — seção Inventário & Métricas):**

- Localizar no template a linha que contém `ccTop: []`
- Substituir por `ccTop: {JSON.stringify(ccTop)},` onde `ccTop` vem do Step 2.10
- ⚠️ NUNCA deixar `ccTop: []` — se Step 2.10 retornou array vazio, manter `ccTop: []` somente quando `bounded_contexts` também estiver vazio
- Exemplo esperado: `ccTop: [{"rank":1,"file":"Contas a Pagar","method":"3 forms / 650 LOC","cc":5.0}, ...],`

**Injeção de fileTypes (Arquivos por Tipo — seção KPIs & Métricas):**

- Localizar no template a linha que contém `fileTypes:[` (pode ter o array hardcoded com q:"0")
- Substituir o array inteiro por `fileTypes: {JSON.stringify(fileTypes)},` onde `fileTypes` vem do Step 2.11
- Garantir que cada item tenha q como string (ex: `"22"`, não `22`)
- ⚠️ NUNCA deixar todos os q como "0" — isso indica que os dados reais não foram injetados

O FILE_TREE_JSON é a árvore completa de todos os arquivos em `outputs/` agrupados
por top-level directory. Permite ao HTML exibir 100% dos arquivos em disco no
painel "Explorer de Arquivos", independente do mapeamento manual por agente.

Formato dos dados em `summary-data.json`:

```javascript
const D = {
  project: "PROJETO",
  generatedAt: "DATA",
  risks: [ ... ],        // array de riscos do risk register
  patterns: [ ... ],     // padrões arquiteturais
  bc: [ ... ],           // bounded contexts
  waves: [ ... ],        // migration waves
  packages: [ ... ],     // NuGet packages
  agentStatus: { ... },  // status por agente
  artifactInventory: { ... }, // artefatos por fase
  diagrams: { ... },     // conteúdo .mmd
  // ...todos os demais campos
};
```

### 3.5 — Injetar diagramas Mermaid

**Mapeamento canônico — placeholder → arquivo fonte (OBRIGATÓRIO):**

| Placeholder no HTML               | Arquivo fonte (path em outputs/)           | Chave em DiagramMap   |
| --------------------------------- | ------------------------------------------ | --------------------- |
| `{{C4_CONTEXT_DIAGRAM}}`          | `asis/diagrams/c4-context.mmd`             | `c4_context`          |
| `{{C4_CONTAINER_DIAGRAM}}`        | `asis/diagrams/c4-container.mmd`           | `c4_container`        |
| `{{C4_COMPONENT_DIAGRAM}}`        | `asis/diagrams/c4-component.mmd`           | `c4_component`        |
| `{{COMPONENT_DIAGRAM}}`           | `asis/diagrams/component-diagram.mmd`      | `component_diagram`   |
| `{{ER_DIAGRAM}}`                  | `asis/db/er-diagram.mmd`                   | `er_diagram`          |
| `{{TOBE_C4_DIAGRAM}}`             | `tobe/diagrams/c4-context.mmd`             | `tobe_c4`             |
| `{{TOBE_ARCH_BLUEPRINT_DIAGRAM}}` | `tobe/diagrams/architecture-blueprint.mmd` | `tobe_arch_blueprint` |
| `{{TOBE_C4_CONTAINER_DIAGRAM}}`   | `tobe/diagrams/c4-container.mmd`           | `tobe_c4cnt`          |
| `{{TOBE_C4_COMPONENT_DIAGRAM}}`   | `tobe/diagrams/c4-component.mmd`           | `tobe_c4comp`         |
| `{{TOBE_CLASS_DIAGRAM}}`          | `tobe/diagrams/class-diagram.mmd`          | `tobe_class`          |
| `{{CONTEXT_MAP_DIAGRAM}}`         | `tobe/diagrams/context-map.mmd`            | `tobe_context_map`    |
| `{{GANTT_DIAGRAM}}`               | `tobe/diagrams/migration-gantt.mmd`        | `tobe_gantt`          |
| `{{TOBE_ER_DIAGRAM}}`             | `tobe/diagrams/mer-diagram-tobe.mmd`       | `tobe_er_diagram`     |
| `{{TOBE_SEQ_DIAGRAM}}`            | `tobe/diagrams/seq-arquitetural-tobe.mmd`  | `tobe_seq`            |
| `{{SOLUTION_STRUCTURE}}`          | `tobe/diagrams/solution-structure.mmd`     | `solution_structure`  |
| `{{CLEAN_ARCH_STRUCTURE}}`        | `tobe/diagrams/clean-arch.mmd`             | `clean_arch`          |

> ⚠️ **ATENÇÃO — paths TO-BE:** Todos os arquivos `.mmd` TO-BE residem em `tobe/diagrams/` com suas sub-keys correspondentes.
> `{{GANTT_DIAGRAM}}` vem de `tobe/diagrams/migration-gantt.mmd` — NUNCA de `tobe/migration-gantt.mmd`.
> `{{CONTEXT_MAP_DIAGRAM}}` vem de `tobe/diagrams/context-map.mmd` — NÃO do arquivo `.drawio`.

> ⚠️ **Sobre `{{VALUE_CHAIN_DIAGRAM}}`**: Este placeholder NÃO existe no template HTML atual.
> O diagrama `tobe/diagrams/value-chain.mmd` é exibido pelo File Explorer / Deliverable Viewer
> quando o usuário clica no artefato. Não há `<pre class="mermaid">` dedicado para ele.
> Não tentar injetar `{{VALUE_CHAIN_DIAGRAM}}` — o placeholder não existe.

Para cada placeholder da tabela acima:

1. Ler o conteúdo do arquivo correspondente em DiagramMap (chave conforme tabela)
2. Sanitizar com `sanitize_mmd()` (remover emoji, substituir →, escapar backticks)
3. Substituir o `{{PLACEHOLDER}}` pelo conteúdo sanitizado
4. Injetar também no objeto `D.staticDiagrams` via a chave correspondente:
   - `D.staticDiagrams.tobeArchBlueprint` ← `tobe_arch_blueprint`
   - `D.staticDiagrams.tobeC4` ← `tobe_c4`
   - `D.staticDiagrams.tobeC4cnt` ← `tobe_c4cnt`
   - `D.staticDiagrams.tobeC4comp` ← `tobe_c4comp`
   - `D.staticDiagrams.tobeEr` ← `tobe_er_diagram` (conteúdo de `tobe/diagrams/mer-diagram-tobe.mmd`)

Se diagrama não disponível → **não injetar texto hardcoded**.
O template usa `t('lbl-no-diagram')` automaticamente via `renderAllDiagrams()`.
Deixar o conteúdo vazio ou com o placeholder original — o JS tratará.

**Extração do `architecture-blueprint.mmd`**:

- Fonte: `projects/{project_name}/outputs/tobe/diagrams/architecture-blueprint.mmd`
- Sanitizar com `sanitize_mmd()` (remover emoji, substituir →, escapar backticks)
- Injetar em `D.staticDiagrams.tobeArchBlueprint`
- Se não existir → placeholder vazio, template trata via `renderAllDiagrams()`

### 3.5b — Injetar dados do Value Chain (seção `s-f2-vc`)

Se `value-chain-mapping.md` existe em `outputs/tobe/`:

1. Parsear a tabela "Module × Business Processes" → gerar `<tr>` no `<tbody id="tb-vc-modules">`
2. Parsear a tabela "Cross-Module Value Flow" → gerar `<tr>` no `<tbody id="tb-vc-flows">`
3. Parsear a tabela "Value Chain Improvements" → gerar `<tr>` no `<tbody id="tb-vc-improvements">`
4. Atualizar `<span id="vc-tag">` com contagem (ex: `6 modules · 18 processes`)
5. Marcar `nd-f2-vc` com classe `ok`

Se `value-chain-mapping.md` **não existe** → marcar seção com `lbl-phase-not-run` e `nd-f2-vc` com classe `idle`.

### 3.5c — Injetar dados de Sizing & Effort Calculator

> ⚠️ **CRÍTICO — Placeholder obrigatório no bloco JavaScript:**
> O placeholder `{{EFFORT_CALC_WAVES_JSON}}` está dentro do bloco `<script>` do template
> na propriedade `effortCalcWaves:` do objeto `const D`. Deixá-lo sem substituição provoca
> **SyntaxError no JavaScript**, que impede toda a navegação lateral e os renderizadores.
> **SEMPRE substituir antes de salvar o HTML final.**

| Placeholder                  | Fonte                            | Formato esperado               |
| ---------------------------- | -------------------------------- | ------------------------------ |
| `{{EFFORT_CALC_WAVES_JSON}}` | `tobe/docs/effort-calculator.md` | JSON array — ver schema abaixo |

**Schema do array `effortCalcWaves`:**

```json
[
  {
    "wave": "W0 Foundation",
    "fp": 20,
    "sp": "N/D",
    "hours_raw": 528,
    "hours_overhead": 607,
    "hours_final": 728,
    "sprints": 2
  },
  {
    "wave": "W1 Reference Data",
    "fp": 8,
    "sp": "N/D",
    "hours_raw": 115,
    "hours_overhead": 132,
    "hours_final": 159,
    "sprints": 1
  }
]
```

**Parsing de `effort-calculator.md`:**

1. Localizar a tabela "Effort by Wave" (contém colunas Wave, FP, Factor, ...)
2. Para cada linha de dados (não header, não separator):
   - `wave` = coluna 1 (nome da wave)
   - `fp` = coluna 2 (int)
   - `hours_raw` = coluna 8 (Base hours, int, remover vírgulas)
   - `hours_overhead` = coluna 9 (`+Overhead 15%`, int)
   - `hours_final` = última coluna (`Total Hours`, int)
   - `sprints` = `max(1, round(hours_final / 320))` (sprint de 2 semanas × 4 devs)
   - `sp` = `"N/D"` (Story Points não calculados nesta fase)
3. Serializar como `JSON.stringify(array)`
4. Substituir `{{EFFORT_CALC_WAVES_JSON}}` com o resultado

Se `effort-calculator.md` não existe → substituir com `[]` (array vazio).
**NUNCA** deixar `{{EFFORT_CALC_WAVES_JSON}}` literal no HTML final.

### 3.6 — Marcar seções sem dados

Para cada seção cuja fase não foi executada:
Adicionar após o `<div class="ph">`:

```html
<div style="padding:20px;text-align:center;color:var(--g2);font-size:12px">
  <span data-i18n="lbl-phase-not-run"
    >⏳ Esta fase ainda não foi executada. Execute o workflow correspondente
    para ver os dados aqui.</span
  >
</div>
```

**IMPORTANTE:** Usar `data-i18n="lbl-phase-not-run"` para que o texto mude ao trocar idioma.

### 3.7 — Injetar timestamp e trace_id no rodapé

Substituir no `.wm`: `{{GENERATED_AT}}` e `{{TRACE_ID}}`

### 3.8 — Definir nome do arquivo de saída

```
filename = "AVA-FABRIC-SUMMARY-{PROJECT_NAME}-{DATE_YYYYMMDD}.html"
Exemplo:  "AVA-FABRIC-SUMMARY-ClinicaDental-20260402.html"
```

## Regras de Injeção

### Para tabelas

Se a lista de dados tem itens → gerar `<tr>` para cada item
Se a lista está vazia → inserir linha única: `<td colspan="N" style="text-align:center;color:var(--g2)" data-i18n="lbl-no-data">Nenhum dado disponível</td>`
**IMPORTANTE:** Usar `data-i18n="lbl-no-data"` para que o texto mude ao trocar idioma.

### Para artifact chips

Para cada artefato no inventário de uma fase → gerar:

```html
<span class="arc" title="{path}"
  >{icon} {key}<span class="ext">{EXT}</span></span
>
```

Ícones por extensão: MD=📄, JSON={}, MMD=〰, YML=⚙, CS=#, TS=⬡, HTML=🌐, SQL=🗄, DIR=📁

### Para agent cards

Para cada agente → usar status do `agent_status`:

- `done` → classe `sd` (verde) + mostrar contagem de artefatos
- `pending` → classe `si` (cinza) + mostrar "Aguardando execução"

## Critério de Conclusão

- HTML_CONTENT sem erros de sintaxe
- Pelo menos 5 placeholders `{{` substituídos
- Arquivo `AVA-FABRIC-SUMMARY-*.html` com tamanho > 50KB
