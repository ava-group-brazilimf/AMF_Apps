# Draw.io Governance — IMFAI AVA Fabric Agents

> **Version:** 1.0.0 — May 2026  
> **Applies to:** ALL agents that produce `.drawio` files — `asis-diagnostic`, `tobe-architecture`, `migration-plan`, and any future agent.  
> **Reference this file as:** `@drawio-governance`

---

## ABSOLUTE INVARIANT

> ⚠️ **ALL agents that produce `.drawio` files MUST follow every rule in this document. No exceptions.**

Whenever ANY agent generates or modifies a `.drawio` file (C4 diagrams, architecture diagrams, class diagrams, sequence diagrams, Gantt, etc.), the following rules are **NON-NEGOTIABLE**.

---

## Relação com Mermaid (Dual-Output Rule)

- Para CADA diagrama gerado em `.mmd`, criar **SIMULTANEAMENTE** um arquivo `.drawio` nativo com a mesma representação visual.
- **REGRA ABSOLUTA: NÃO converter mermaid → drawio.** Os dois formatos são gerados **independentemente** a partir dos mesmos dados de análise — nunca um a partir do outro.
- A ordem de escrita é: escrever o `.mmd` **e imediatamente a seguir** o `.drawio` correspondente (mesmo nome base).
- Se não houver dados suficientes → usar placeholder (ver seção "Placeholder Mínimo").
- Ao final de cada agente: consolidar todos os diagramas num único arquivo multi-page (ex: `diagrama-tobe.drawio`, `diagrama-componentes.drawio`) com uma `<diagram>` por diagrama.

---

## Rule 1 — Edge Style (MANDATORY)

Todas as arestas/conexões em qualquer arquivo `.drawio` **DEVEM** usar o style string completo abaixo:

```xml
<mxCell style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;jumpStyle=arc;jumpSize=10;" edge="1" parent="1" source="..." target="...">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

**Atributos obrigatórios em todo edge:**

| Atributo | Valor | Motivo |
|---|---|---|
| `edgeStyle` | `orthogonalEdgeStyle` | Routing ortogonal — setas previsíveis e legíveis |
| `rounded` | `1` | Cantos arredondados — visual profissional |
| `orthogonalLoop` | `1` | Evita loops com routing incorreto |
| `jettySize` | `auto` | Pontos de conexão limpos nos nós |
| `html` | `1` | Suporte a HTML em labels |
| `jumpStyle` | `arc` | Setas que se cruzam mostram arco (não sobreposição) |
| `jumpSize` | `10` | Tamanho do arco de cruzamento |

**PROIBIDO:** usar `rounded=0` — todo edge herda `rounded=1` como padrão mínimo.

---

## Rule 2 — No Crossing Arrows (MANDATORY)

- Setas **NÃO DEVEM** se cruzar sempre que fisicamente possível.
- Usar waypoints (`mxPoint` na `mxGeometry`) para rotear setas ao redor de obstáculos.
- Reordenar/reposicionar nós para minimizar cruzamentos **antes** de adicionar conexões.
- Aplicar estratégia de layout hierárquico ou em camadas (agrupar nós relacionados).
- Se um cruzamento for absolutamente inevitável (diagramas muito complexos), usar `jumpStyle=arc;jumpSize=10` — o arco visual indica o cruzamento sem ambiguidade.
- **Regra de ouro: planejar posicionamento dos nós ANTES de desenhar as conexões** — layout primeiro, conexões depois.

---

## Rule 3 — No Overlapping Arrows (MANDATORY)

- Setas **NÃO DEVEM** compartilhar o mesmo caminho visual nem se sobrepor.
- Cada conexão **DEVE** ter sua própria rota visual distinta.
- Manter espaçamento mínimo de **20px** entre setas paralelas.
- Usar pontos de entrada/saída distribuídos nas bordas dos nós — evitar que todas as setas saiam/cheguem pelo mesmo ponto.
- Para múltiplas conexões na mesma direção, variar os pontos de origem/destino:

```xml
<!-- Seta 1 — sai pelo centro-bottom -->
exitX="0.5" exitY="1" exitDx="0" exitDy="0"
<!-- Seta 2 — sai pelo bottom-left -->
exitX="0.25" exitY="1" exitDx="0" exitDy="0"
<!-- Seta 3 — sai pelo bottom-right -->
exitX="0.75" exitY="1" exitDx="0" exitDy="0"
```

---

## Algoritmo de Routing em 7 Passos

Aplicar este algoritmo ao gerar QUALQUER arquivo `.drawio`:

```
1. DETERMINE a direção do layout:
   - C4 / Deployment → top-to-bottom (TB)
   - BPMN / Flows    → left-to-right (LR)

2. POSITION todos os nós usando layout hierárquico/em camadas
   - Agrupar nós relacionados em containers/swimlanes
   - Alinhar em grid — espaçamento mínimo 40px entre nós

3. ASSIGN portas de entrada/saída por nó conforme direção da conexão:
   - Top ports    → chegada de camada superior
   - Bottom ports → saída para camada inferior
   - Left/Right   → conexões peer-to-peer

4. ROUTE edges usando caminhos ortogonais com waypoints
   - Aplicar o style string completo da Rule 1

5. CHECK cruzamentos — se encontrados:
   a. Tentar reordenar nós dentro da mesma camada
   b. Tentar ajustar waypoints
   c. Último recurso: jumpStyle=arc

6. CHECK sobreposições — se encontradas:
   a. Distribuir pontos de saída/entrada nas bordas dos nós
   b. Adicionar offsets de waypoint (mínimo 20px de separação)

7. VALIDATE: todos os edges têm o style string completo (Rule 1)?
   → Se não → corrigir antes de salvar o arquivo
```

---

## Critical Path Style

Para conexões em **caminho crítico**, highlights, ou dependências de alta prioridade:

```xml
style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#d32f2f;strokeWidth=2;fontColor=#d32f2f;fontSize=11;"
```

| Atributo extra | Valor |
|---|---|
| `strokeColor` | `#d32f2f` (vermelho) |
| `strokeWidth` | `2` (linha mais grossa) |
| `fontColor` | `#d32f2f` (label vermelho) |
| `fontSize` | `11` |

Usar em: setas de dependência bloqueante, caminho crítico de migração (Gantt), relações de alta severidade em diagramas de risco.

---

## Layout Strategy por Tipo de Diagrama

### C4 Level 1 — Context
- Sistema-sob-design **no centro** do canvas
- Atores externos e sistemas externos ao **redor da periferia**
- Direção: **top-to-bottom** para fluxo primário, **left-to-right** para fluxo secundário

### C4 Level 2 — Container
- Layout **horizontal em camadas**:
  - Frontend → topo
  - Backend (APIs, services) → meio
  - Data (BDs, queues, storage) → base
- Usar swimlanes/containers para separar trust boundaries

### C4 Level 3 — Component
- **Agrupar por bounded context** (um container draw.io por BC)
- Dependências fluindo **de cima para baixo**
- Peer connections: **left-to-right**

### Deployment Diagrams
- Organizar por **environment zones**: Internet → DMZ → App Tier → Data Tier
- Usar swimlanes/containers para separar visualmente trust boundaries
- Conexões de rede **NÃO DEVEM** cruzar zone boundaries visualmente (rotear ao redor)

### BPMN / Flow Diagrams
- Fluxo principal **estritamente left-to-right**
- Branches de decisão: topo (yes) e base (no) — **nunca para trás**
- Merge points alinhados verticalmente com seus split points

---

## Pre-Output Checklist (Self-Verification Obrigatória)

O agente **DEVE** verificar cada item antes de salvar qualquer arquivo `.drawio`:

- [ ] Todos os edges usam `edgeStyle=orthogonalEdgeStyle` com `rounded=1`
- [ ] Todos os edges têm `orthogonalLoop=1;jettySize=auto;html=1;jumpStyle=arc;jumpSize=10`
- [ ] Nenhuma seta se cruza com outra (ou usa arc jump se inevitável)
- [ ] Nenhuma seta compartilha o mesmo caminho visual (sem sobreposições)
- [ ] Posicionamento dos nós segue layout hierárquico/em camadas
- [ ] Labels das setas são legíveis e não sobrepõem outros elementos
- [ ] Cada conexão tem pontos de entrada/saída distintos nos nós
- [ ] Nenhum caractere proibido nos atributos XML (ver Rule 4)
- [ ] Nenhum emoji em `value`, `style`, ou `name` attributes
- [ ] Encoding UTF-8 sem BOM no início do arquivo
- [ ] O arquivo NÃO é um stub ou placeholder — contém shapes/barras/nós
      reais com geometria (mxGeometry com width > 0 e height > 0), não
      apenas caixas de texto referenciando outros formatos

---

## Rule 4 — XML Character Sanitization (MANDATORY)

> ⚠️ Draw.io é XML — caracteres especiais em atributos `value=""` e `name=""` DEVEM ser
> entity-encoded ou removidos. Falha em sanitizar causa `.drawio` corrompido que não abre.

### 4.1 — Caracteres que DEVEM ser entity-encoded em atributos XML

| Caractere | Entity | Contexto |
|---|---|---|
| `&` | `&amp;` | SEMPRE — dentro de `value=""`, `style=""`, `name=""` |
| `<` | `&lt;` | SEMPRE — dentro de atributos (fora de tags `<b>`, `<br/>`, `<font>` intencionais) |
| `>` | `&gt;` | SEMPRE — dentro de atributos (fora de tags intencionais) |
| `"` (aspas retas) | `&quot;` | Dentro de atributos que já usam `"` como delimitador |

> **Nota:** Draw.io usa HTML inline em `value=""` — tags como `<b>`, `<br/>`, `<font>`, `<i>` são PERMITIDAS e NÃO devem ser entity-encoded.

### 4.2 — Caracteres PROIBIDOS em Draw.io

Aplicar as mesmas regras de [mermaid-guardrails.md](mermaid-guardrails.md) seção "Caracteres PROIBIDOS", com adaptações para XML:

| Caractere | Unicode | Substituto em Draw.io |
|---|---|---|
| `—` em-dash | U+2014 | ` - ` (espaço-hífen-espaço) |
| `–` en-dash | U+2013 | ` - ` |
| `"` `"` curly quotes | U+201C/U+201D | `&quot;` ou remover |
| `'` `'` curly single quotes | U+2018/U+2019 | `'` (U+0027) |
| `→` `←` `↔` unicode arrows | U+2192/U+2190/U+2194 | remover ou usar `to` / `from` no texto |
| `─` `│` box-drawing | U+2500/U+2502 | remover |
| Emojis | U+1F000+ | remover completamente |
| NBSP | U+00A0 | espaço simples U+0020 |
| BOM | U+FEFF | remover |
| Zero-width space/joiner | U+200B/U+200C/U+200D | remover |
| `•` bullet | U+2022 | `*` ou `&amp;bull;` |

### 4.3 — Regras para `<diagram name="...">`

O atributo `name` de `<diagram>` aparece como **tab title** no Draw.io editor:

- **PROIBIDO:** em-dash, en-dash, emojis, unicode arrows no `name`
  - ❌ `<diagram name="Architecture Blueprint — Meu-ERP TO-BE">`
  - ✅ `<diagram name="Architecture Blueprint - Meu-ERP TO-BE">`
- **PROIBIDO:** `&` não-encoded
  - ❌ `<diagram name="BPMN & Processes">`
  - ✅ `<diagram name="BPMN and Processes">`
- **Recomendado:** ASCII-only para nomes de diagram tabs

### 4.4 — Regras para `<mxCell value="...">`

O atributo `value` é renderizado como HTML no Draw.io:

- HTML tags permitidos: `<b>`, `<i>`, `<u>`, `<br/>`, `<font style="...">`, `<sup>`, `<sub>`
- `\n` literal é IGNORADO pelo renderizador — usar `<br/>` para multi-linha
- Acentuação portuguesa (á, é, í, ó, ú, ã, õ, â, ê, ô, ç) é PERMITIDA (UTF-8)
- **`&` em texto livre DEVE ser `&amp;`** — ex: `"AP &amp; AR"` (não `"AP & AR"`)
- Emojis são PROIBIDOS — removê-los antes de gravar

### 4.5 — Protocolo de Sanitização Draw.io (Pre-Generation)

Antes de gravar qualquer arquivo `.drawio`, o agente DEVE:

1. **Verificar encoding**: arquivo DEVE ser UTF-8 sem BOM
2. **Verificar XML header**: `<?xml version="1.0" encoding="UTF-8"?>` DEVE ser a primeira linha
3. **Sanitizar `<diagram name="">`**: remover em-dash, en-dash, emojis, unicode arrows
4. **Sanitizar `<mxCell value="">`**: entity-encode `&` → `&amp;`, remover emojis, substituir em-dashes
5. **Sanitizar `<mxCell style="">`**: garantir que todos os edges têm style string completo (Rule 1)
6. **Validar XML well-formedness**: todas as tags DEVEM estar fechadas, atributos com aspas, nenhum `<` / `>` solto
7. **Verificar edge governance**: todos os edges com Rule 1 completo

---

## Gap Analysis — O que esta Governança Adiciona ao IMFAI

| Regra | Estado antes desta doc | Estado após |
|---|---|---|
| Dual-output (`.mmd` + `.drawio`) | ✅ documentado nos agents | ✅ consolidado aqui como referência única |
| Não converter Mermaid → Drawio | ✅ documentado nos agents | ✅ consolidado com invariant formal |
| Shape mapping por tipo de nó | ✅ tabela nos agents | ✅ mantido nos agents (não duplicar aqui) |
| Templates XML canônicos | ✅ nos agents | ✅ mantido nos agents (específicos por diagrama) |
| Edge style completo (`rounded=1`, `orthogonalLoop`, `jettySize`, `jumpStyle`) | ❌ ausente (`rounded=0` nos templates) | ✅ Rule 1 com style string obrigatório |
| Rule 2 — No Crossing Arrows | ❌ ausente | ✅ Rule 2 com waypoints e fallback arc |
| Rule 3 — No Overlapping Arrows | ❌ ausente | ✅ Rule 3 com distributed entry/exit points |
| Algoritmo de routing em 7 passos | ❌ ausente | ✅ algoritmo formal com checklist de fallback |
| Critical Path Style (stroke vermelho) | ❌ ausente | ✅ style string completo para caminho crítico |
| Layout Strategy por nível C4 | ❌ ausente | ✅ regras por L1/L2/L3/Deployment/BPMN |
| Pre-output checklist (self-verification) | ❌ ausente | ✅ 7 itens verificáveis antes de salvar |
| Invariant formal (`ABSOLUTE INVARIANT`) | ❌ ausente | ✅ declarado no topo com scope explícito |

---

## Pre-Write Validation Gate (OBRIGATÓRIO)

> ⚠️ **INVARIANTE ABSOLUTO:** Nenhum arquivo `.drawio` pode ser escrito diretamente em disco pelo agente.
> TODO `.drawio` DEVE passar pelo gate `validate_diagram.py` que valida, sanitiza e escreve atomicamente.
> Este é o ÚNICO ponto de escrita autorizado para arquivos `.drawio`.

### Como usar (em blocos Bash do agente)

```bash
# Gerar o conteúdo XML draw.io e pipar para o gate — o gate escreve em disco se PASS
cat <<'DRAWIO_EOF' | python src/shared/utils/validate_diagram.py --output projects/{project_name}/outputs/{phase}/diagrams/{filename}.drawio
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="AVA-Fabric">
  <diagram name="Diagram Title">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
DRAWIO_EOF
```

### Exit codes do gate

| Código | Status | Ação do agente |
|---|---|---|
| `0` | **PASS** — XML válido, escrito em disco | Prosseguir normalmente |
| `1` | **FAIL** — erros irrecuperáveis (XML malformado, etc.) | **REGENERAR** o conteúdo corrigindo os erros reportados no stderr |
| `2` | **FIXED** — conteúdo tinha problemas que foram auto-corrigidos, escrito em disco | Prosseguir (o gate já corrigiu) — verificar stderr para detalhes |

### O que o gate valida para Draw.io

- XML well-formedness (parseable pelo ElementTree)
- Sanitização de `<diagram name="">` — em-dash, emojis, unicode arrows
- Sanitização de `<mxCell value="">` — emojis, caracteres proibidos
- Edge governance (Rule 1) — todos os edges com style string completo
- Caracteres invisíveis (BOM, NBSP, ZWS) removidos
- Entity encoding de `&` em atributos value

### Fluxo obrigatório do agente

Idêntico ao fluxo de `.mmd` — ver [mermaid-guardrails.md § Pre-Write Validation Gate](mermaid-guardrails.md#pre-write-validation-gate-obrigatório) para o protocolo de 6 passos com retry.
