# Artifact Size Governance — AVA AS-IS Module

> **Version:** 1.0.0 — May 2026
> **Applies to:** ALL agents in `asis-diagnostic` that generate artifacts.
> **Reference this file as:** `@artifact-size-governance`

---

## INVARIANTE ABSOLUTA

> ⚠️ **Todo agente que gera artefatos DEVE respeitar os limites desta tabela.**
> Esta regra tem **prioridade sobre instruções de completude** — é preferível um artefato
> compactado e válido do que um artefato completo e acima do limite hard.
> Quando encontrada após outro conteúdo, esta regra governa retroativamente
> toda a geração de artefatos remanescente na sessão.

---

## Completude vs. Tamanho — quando a completude 100% é obrigatória

> A regra de prioridade acima resolve o conflito completude-vs-tamanho **para artefatos
> gerados por LLM** (relatórios `.md` narrativos, onde compactar/curar é aceitável). Ela
> **não** autoriza descartar dados quando a completude 100% é um requisito de contrato
> downstream.

Quando uma fase downstream depende da enumeração **exaustiva** de um conjunto de dados
(ex: 100% das regras de negócio para a migração), a completude NÃO é sacrificada — ela é
movida para um **artefato determinístico dedicado**, gerado por utilitário Python (não por
LLM) e governado pelos limites de `.json` (com particionamento quando necessário):

| Conjunto exaustivo | Artefato determinístico (fonte de verdade) | Gerador | Artefato `.md` curado |
|---|---|---|---|
| 100% das regras de negócio AST | `asis/docs/business-rules-catalog.json` | `business_rules_catalog_generator.py` (pipeline pós-extração) | `business-rules.md` § "Business Rules" = resumo curado com ponteiro para o catálogo |

**Regra:** o `.md` gerado por LLM pode ser um resumo curado (respeitando os 600 KB), **desde
que** a enumeração 100% exista no artefato determinístico correspondente e o `.md` aponte
para ele. Nunca reportar "amostra representativa" sem que o conjunto completo exista em disco.

---

## 1. Limites por Tipo de Artefato

| Tipo | Limite Soft (⚠️ aviso) | Limite Hard (🔴 ação obrigatória) |
|------|------------------------|----------------------------------|
| `.md` relatórios | 300 KB | 600 KB |
| `.json` dados | 64 KB | 128 KB |
| `.mmd` diagramas | 32 KB | 64 KB |
| `.html` (summary) | 256 KB / arquivo | 5 MB total (agregado) |

> `.html` já é tratado por `build_summary_complete.py` — documentado aqui apenas para referência.

---

## 2. Comportamento ao Exceder

### 2a. Limite Soft atingido → ⚠️ AVISO

O agente DEVE:
1. Emitir o log de aviso (ver seção 3)
2. **Continuar** a geração, aplicando compactação preventiva:
   - Preferir tabelas em vez de prosa
   - Omitir exemplos redundantes
   - Usar referências cruzadas em vez de repetir conteúdo

### 2b. Limite Hard atingido → 🔴 AÇÃO OBRIGATÓRIA

O agente DEVE **parar** e aplicar a estratégia correspondente ao tipo antes de gravar:

| Tipo | Estratégia obrigatória |
|------|------------------------|
| `.md` relatórios | Converter seções narrativas em tabelas; sumarizar seções de baixo risco (P2/P3); particionar em `-part1.md`, `-part2.md` se necessário |
| `.json` dados | Manter apenas top-N nos arrays (ver seção 4); sumarizar os itens omitidos em um objeto `{ "truncated": true, "omitted_count": N }` |
| `.mmd` diagramas | Agrupar nós em `subgraph` por módulo; reduzir granularidade (módulo inteiro em vez de form/componente individual) |

> ⛔ **PROIBIDO**: reportar `completed` antes de aplicar a estratégia e gravar o artefato tratado.

---

## 3. Formato de Log Obrigatório

Emitir **exatamente** um destes logs ao detectar violação de limite:

```
⚠️ [SIZE-WARN] {nome_do_arquivo} — {tamanho_estimado_kb} KB estimado > soft limit {limite_kb} KB.
   Aplicando compactação preventiva.

🔴 [SIZE-BLOCK] {nome_do_arquivo} — {tamanho_estimado_kb} KB estimado > hard limit {limite_kb} KB.
   OBRIGATÓRIO: aplicar estratégia de compactação/particionamento antes de gravar.
   Estratégia aplicada: {compactar | particionar | trim-arrays | agrupar-nos}
```

**Exemplo real:**
```
🔴 [SIZE-BLOCK] business-rules.md — ~680 KB estimado > hard limit 600 KB.
   OBRIGATÓRIO: aplicar estratégia de compactação/particionamento antes de gravar.
   Estratégia aplicada: particionar → functional-requirements-part1.md + functional-requirements-part2.md
```

### Persistência obrigatória do log (OBRIGATÓRIO)

Após emitir o marcador acima, o agente DEVE gravar a entrada no log persistente:

```
Bash: python src/shared/utils/ntp_time.py  → obter timestamp
Write → outputs/asis/logs/size-events.log  (append — nunca sobrescrever)
```

**Formato da linha a gravar:**
```
{timestamp_iso} | {WARN|BLOCK} | {nome_do_arquivo} | {tamanho_estimado_kb} KB | {soft|hard} {limite_kb} KB | estratégia: {descricao}
```

**Exemplo:**
```
2026-05-21T14:32:07Z | BLOCK | business-rules.md | 680 KB | hard 600 KB | estratégia: particionar → part1+part2
2026-05-21T14:45:19Z | WARN  | complexity-map.md          | 320 KB | soft 300 KB | estratégia: compactação preventiva
```

> ⚠️ Se `outputs/asis/logs/` não existir → criar o diretório antes de gravar.
> O arquivo `size-events.log` é **append-only** — nunca truncar entradas anteriores.
> Ausência deste arquivo ao final da sessão indica que nenhum limite foi atingido (comportamento válido).

---

## 4. Regras de Trim por Artefato `.json`

| Artefato | Campos array a trimar | Critério de corte | Complemento |
|---|---|---|---|
| `complexity-map.md` (`.md` com regras de json) | Métodos na tabela CC | Top-50 por CC decrescente | Acrescentar linha `> ⚠️ Exibindo top 50 métodos por CC. Total original: {N}` |
| `risk-register.json` | Array `risks[]` | Manter P0 + P1 completos; omitir P2/P3 | Acrescentar `{ "truncated": true, "p2_omitted": N, "p3_omitted": N }` ao fim do JSON |
| `form-registry.json` | Array `forms[]` | Não trimar — particionar por módulo | Criar `form-registry-{modulo}.json` por bounded context |
| `gap-register.json` | Array `gaps[]` | Manter CRITICAL + HIGH; sumarizar MEDIUM/LOW | Acrescentar `{ "medium_count": N, "low_count": N, "truncated": true }` |

---

## 5. Regras de Particionamento para `.md`

Quando um relatório `.md` for particionado:

```yaml
partitioning_rules:
  naming:
    - original: "business-rules.md"
      parts:    ["functional-requirements-part1.md", "functional-requirements-part2.md"]
    - original: "inventory-report.md"
      parts:    ["inventory-report-part1.md", "inventory-report-part2.md"]
    - original: "business-rules.md"
      parts:    ["business-rules-part1.md", "business-rules-part2.md"]

  header_required:
    - "Cada part DEVE iniciar com: `> ⚠️ Artefato particionado — este é o {N}º de {total} arquivos.`"
    - "Part 1 SEMPRE contém o sumário executivo e os itens de maior prioridade (CRITICAL/HIGH/P0/P1)"
    - "Part 2+ contém os itens de menor prioridade (MEDIUM/LOW/P2/P3)"

  output_contract_update:
    - "Agente DEVE listar TODOS os parts no Output Verification antes de reportar completed"
    - "O Orchestrator Consistency Gate (C2 — ARTIFACT-COMPLETE) aceita -part1 como substituto do artefato original"
```

---

## 6. Regras de Agrupamento para `.mmd`

Quando um diagrama `.mmd` exceder o limite hard:

```
Antes (granularidade form):
    frmContasPagar["frmContasPagar<br/>(Browse CP)"]
    frmCadastroCP["frmCadastroCP<br/>(Cadastro CP)"]
    frmFornecedores["frmFornecedores<br/>(Lookup)"]

Depois (granularidade módulo):
    subgraph FIN["Módulo: Financeiro (3 forms)"]
        CP["Contas a Pagar (Browse + Cadastro)"]
        FORN["Fornecedores (Lookup)"]
    end
```

**Regra de agrupamento:**
- Agrupar todos os forms de um mesmo bounded context em um `subgraph`
- Usar contagem de forms como legenda: `"NomeModulo (N forms)"`
- Manter detalhamento individual apenas para forms com navegação inter-módulos

---

## 7. Estimativa de Tamanho — Como Calcular

Como os agentes LLM não têm acesso a `os.path.getsize()` no momento da geração, usar estimativas:

| Referência | Estimativa |
|---|---|
| 1 seção `## FR-NNN: Título` completa (Formato A) | ~0,5 KB |
| 1 linha de tabela Markdown | ~0,1 KB |
| 1 nó Mermaid com label | ~0,05 KB |
| 1 objeto JSON de risco completo | ~0,3 KB |
| 1 objeto JSON de form-registry | ~0,2 KB |

**Gatilho prático (contar durante geração):**

| Tipo | Acionar estimativa quando... |
|---|---|
| `.md` relatório | Ultrapassar 600 FRs, 1.200 BRs, ou 3.000 linhas de tabela |
| `.json` | Ultrapassar 200 objetos no array principal |
| `.mmd` | Ultrapassar 640 nós (estimativa: 640 × 0,05 KB ≈ 32 KB soft) |

---

## 8. Referência Cruzada com Outros Contratos

| Contrato | Relação com este documento |
|---|---|
| [`parser-contracts.md`](./parser-contracts.md) | Formatos fixos de campos — este documento não altera schemas; apenas limita volume |
| [`output-paths.md`](./output-paths.md) | Paths canônicos permanecem inalterados; artefatos particionados usam sufixo `-partN` |
| [`retry-protocol.md`](./retry-protocol.md) | Se agente falhar ao aplicar compactação → retry com `force_compact: true` |
| `orchestrator-asis.md` C2 (ARTIFACT-COMPLETE) | `-part1.md` é aceito como substituto do artefato original no check de completude |
