# Contrato — `src/shared/data/pipeline-dag/F{N}.yaml`

**Produtor**: humano (extraído das tabelas do orquestrador da fase)
**Consumidores**: `agent_runner.py` (`load_dag` / `validate_dag`) e `tests/test_pipeline_dag.py`
**Estado**: `F1.yaml` existe com `wave2` apenas; a Category 3 da `tasks.md` completa o DAG. F2–F8 não
existem.

---

## ⚠️ Este arquivo é A fonte, não um espelho

O repo já tem três espelhos manuais que divergiram:

| Fonte | Onde | Como divergiu |
|---|---|---|
| `ARTIFACT_CONTRACTS` | `asis-diagnostic/utils/artifact_gate.py` | *"espelha 1:1 a tabela de `orchestrator-asis.md`; alterar um lado exige alterar o outro"* |
| `AGENT_ARTIFACT_SLICE` | `asis-diagnostic/utils/context_budget.py` | fatia por agente, mantida à mão |
| `AGENT_CATALOG` (×2) | `pipeline_observer.py`, `generate_observability_report.py` | *"52 de 101 agentes ausentes, 18 versões divergentes"* — foi o que originou o `agent_registry.py` |

Acrescentar um quarto par manual **pioraria** o modo de falha recorrente do repo. Por isso
`tests/test_pipeline_dag.py` compara **conteúdo**, não presença:

```
dag.nodes            ≡ artifact_gate.ARTIFACT_CONTRACTS.keys()
dag.nodes            ≡ agent_registry.catalog()
dag[n].slice         ≡ context_budget.AGENT_ARTIFACT_SLICE[n]      ← o que falta hoje
```

O `validate_dag()` atual só verifica **presença** do id e do `slice`. Isso não pega o caso real:
alguém muda a fatia num lado e não no outro.

---

## Esquema

```yaml
version: 1                          # obrigatório; bump = mudança de formato
phase: F1                           # obrigatório; validado contra o nome do arquivo
module: asis-diagnostic             # informativo
orchestrator: ava-asis-orchestrator # quem invoca o runner
max_parallel: 3                     # alinhado ao compression_max_workers do Headroom (R5)

defaults:                           # herdados por nó que omitir
  timeout_s: 900
  max_attempts: 4                   # M1 usa 1; a escada de retry sobe para 4 (Cat. 3)
  model: claude-sonnet-4            # NUNCA 'auto' — sem pin cai em gpt-5.4 e 404

waves:
  - id: wave1
    blocking: true                  # falha aqui aborta a fase
    implemented: true               # false => o runner emite ⏸ e pula a wave
    agents:
      - id: "ava-asis-solution-{legacy_technology}"   # resolvido por artifact_gate.resolve_solution_agent()
        slice: all                                    # 'all' ou lista de artefatos
        timeout_s: 3600
        max_ai_credits: 80
        large_artifact_protocol: true
        # context: long_context   <- NÃO USAR: o tier é aceito mas o tokenLimit
        #                             dele é desconhecido (M0 § 1.4)

  - id: wave2
    depends_on: [wave1]
    implemented: true
    agents:
      - id: ava-asis-inventory
        slice: [08_code_overview, 02_form_business_rules]
        timeout_s: 900
        max_ai_credits: 30
```

### Campos por nó

| Campo | Obrigatório | Regra |
|---|---|---|
| `id` | sim | tem que existir em `ARTIFACT_CONTRACTS` **e** em `agent_registry.catalog()`. O placeholder `{legacy_technology}` é o único permitido |
| `slice` | sim | `all` ou lista; tem que ser **idêntica** a `AGENT_ARTIFACT_SLICE[id]`. Lista vazia `[]` é válida (consolidadores) |
| `timeout_s` | herda | ao estourar: `taskkill /PID <pid> /T /F` — `terminate()` deixa o node órfão no Windows (R10) |
| `max_attempts` | herda | teto 4, alinhado ao "max 4x" do `retry-protocol.md` |
| `max_ai_credits` | não | piso `MIN_AI_CREDITS = 30` aplicado pelo runner (R6) |
| `model` | herda | pinado; `auto` é proibido |
| `large_artifact_protocol` | não | informativo; o enforcement real é o hook `preToolUse` |

### Campos por wave

| Campo | Regra |
|---|---|
| `id` | único no arquivo |
| `blocking` | `true` → falha aborta a fase |
| `depends_on` | lista de ids de wave; o grafo tem que ser **acíclico** |
| `implemented` | `false` → runner emite `⏸` e pula, sem falhar. É como o `wave1` está hoje |

---

## Invariantes verificados por `tests/test_pipeline_dag.py`

1. `version == 1` e `phase` casa o nome do arquivo.
2. Grafo de waves **acíclico**; todo `depends_on` aponta para wave existente.
3. `id` de wave único; `id` de nó único no arquivo.
4. Todo nó implementado existe nas três fontes e declara `slice`.
5. `slice` **idêntica** a `AGENT_ARTIFACT_SLICE` (conteúdo, com ordem normalizada).
6. Todo nó tem artefatos declarados em `ARTIFACT_CONTRACTS` (lista não vazia).
7. `timeout_s` e `max_attempts` resolvem (do nó ou de `defaults`).
8. Nenhum nó traz `context: long_context` — o tier não foi medido.

Falha em qualquer um = exit 1 no CI, nomeando **os dois lados** da divergência.
