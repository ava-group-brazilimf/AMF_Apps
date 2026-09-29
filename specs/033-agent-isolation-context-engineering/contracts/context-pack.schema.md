# Contrato — `context-pack.md`

**Produtor**: `src/shared/tools/context_pack.py` (chamado pelo `agent_runner.py` antes do spawn)
**Consumidor**: o agente, via a linha 2 do envelope (*"Seu contexto já está materializado em … Leia-o
PRIMEIRO"*)
**Caminho**: `projects/{project_name}/outputs/.context/{agent_id}/context-pack.md`
**Protocolo**: `src/modules/ava-fabric-agents/shared/context-pack-protocol.md`

---

## Regras invioláveis

| # | Regra | Por quê |
|---|---|---|
| R1 | **Nenhum pack pode exceder o orçamento** do agente | é o gate que falta hoje; o runner só imprime um `⚠` |
| R2 | Excedeu → **degradar para query-only e registrar a decisão dentro do pack** | "no silent caps": truncar em silêncio faz o agente reportar cobertura que não teve |
| R3 | **Determinístico**: mesmo input → bytes idênticos | ordenação por chave; nenhum `set()` sem `sorted()`; nenhum timestamp no corpo |
| R4 | A seção 2 carrega **paths, nunca conteúdo** | é o hand-off barato; embutir conteúdo recria a acumulação que a spec resolve |
| R5 | **Pack presente → autoridade.** Ausente → `## Input Contract` clássico | degradar, nunca quebrar |
| R6 | Agente desconhecido (fatia `None`) → pack vazio com `known_agent: false` | mesmo comportamento de `build_agent_context()` hoje; nunca exceção |

Orçamento de referência: `agent_runner.USABLE_CONTEXT = 106.551`
(= 128.000 janela − 13.449 estático − ~8.000 de reserva de saída; M0 § 3).

---

## Estrutura

````markdown
# Context Pack — {agent_id}

| campo | valor |
|---|---|
| run_id | {run_id} |
| project | {project_name} |
| language | {legacy_technology} |
| trace_id | {trace_id}                  <!-- propagado sem mutação, Art. VIII -->
| known_agent | true \| false |
| mode | full \| query-only              <!-- R2 -->
| tokens | 11.240 / 106.551 úteis |
| seed_artifacts | [08_code_overview, 02_form_business_rules] |

<!-- Presente APENAS quando mode == query-only. Nunca omitir silenciosamente. -->
> ⚠️ **Degradação registrada.** A fatia decodificada somava {n} tokens, acima do orçamento de
> {budget}. A seção 1 foi reduzida a contagens; use a seção 3 para recuperar o detalhe.
> Artefatos afetados: {lista}.

## 1. Sua fatia AST (já decodificada do formato Headroom)

### 08_code_overview
…conteúdo decodificado, limitado ao AGENT_ARTIFACT_SLICE…

### 02_form_business_rules
…

<!-- Em mode: query-only esta seção vira contagens + como consultar: -->
### 08_code_overview — 363 units, 174.375 LOC (conteúdo não embutido)

## 2. Índice de artefatos upstream

| artefato | agente produtor | tamanho | seções |
|---|---|---|---|
| outputs/asis/inventory-report.md | ava-asis-inventory | 42 KB | Resumo, Métricas, Complexidade |

> Leia sob demanda. **Não estão embutidos aqui de propósito** — extraia só as linhas que precisa
> (grep/faixa), conforme o protocolo de handoff do `AGENTS.md`.

## 3. Como consultar o que não está aqui

```powershell
python src/shared/tools/headroom/headroom_tool.py slice -p {project_name} --artifact <n>
python src/shared/tools/headroom/headroom_tool.py decode -p {project_name} --artifact <n>
```

> `outputs/asis/ast-raw/` é **negado** pelo hook `preToolUse`. Use a consulta acima.

## 4. Seu output contract

| artefato | estado |
|---|---|
| outputs/asis/inventory-report.md | FALTANDO |
| outputs/asis/metrics.json | FALTANDO |
| outputs/asis/.internal/form-registry.json | presente |

> Origem: `artifact_gate.ARTIFACT_CONTRACTS[{agent_id}]`. `artifacts_confirmed` É MEDIDO,
> NUNCA DECLARADO.

## 5. Estado da fase

<!-- Extrato CURADO do shared-context.md: status + índice de decisões. Nunca o arquivo inteiro. -->
````

---

## Campos do `--json`

```json
{
  "schema_version": "1.0.0",
  "project": "MeuERP-002",
  "agent_id": "ava-asis-inventory",
  "phase": "F1",
  "known_agent": true,
  "mode": "full",
  "path": "projects/MeuERP-002/outputs/.context/ava-asis-inventory/context-pack.md",
  "budget": { "limit": 106551, "used": 11240, "degraded_artifacts": [] },
  "seed_artifacts": ["08_code_overview", "02_form_business_rules"],
  "output_contract": { "missing": ["outputs/asis/inventory-report.md"], "present": [] }
}
```

Exit codes (mesma convenção de `headroom_tool.py`): `0` OK · `1` degradado · `2` erro de uso.

---

## Reuso obrigatório

| Precisa de | Use | Não crie |
|---|---|---|
| decodificar o formato SmartCrusher/Headroom | `headroom_context.read_artifact_payload()` | outro decoder — é o único no repo |
| a fatia por agente | `context_budget.AGENT_ARTIFACT_SLICE` via `headroom_context.build_agent_context()` | uma cópia da tabela de fatias |
| o output contract | `artifact_gate.ARTIFACT_CONTRACTS` / `check_agent()` | uma lista paralela de artefatos |
| a linguagem e os paths | `context_budget.load_project_config()` / `resolve_compressed_dir()` | resolução de path própria |

Fora de escopo (**spec 034**): knowledge graph, `ast_index.py`, FTS5/BM25, write-back F2. O pack é um
arquivo em disco — trocar quem o produz é invisível para quem o consome.
