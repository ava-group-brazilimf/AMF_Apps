# Agent Specification: Headroom Context Compression — Tool + Proxy Interceptor

**Feature Branch**: `031-headroom-context-compression-proxy`
**Created**: 2026-07-30
**Status**: Implemented
**Change Type**: add-new (1 tool com 4 módulos + proxy + MCP server)
+ modify-existing (5 agentes F1, MINOR cada — nenhum campo de Output Contract removido)
+ modify-existing (2 consumidores determinísticos de artefatos AST)
**Input**: `headroom-integration-prompt-v2.md` — "Crie a implementação do tools headroom.
Documente via speckit. Pasta da tools src/shared/tools."

---

## 1. Identidade

Esta feature **não introduz um agente novo**. Entrega uma tool determinística
(sem custo de LLM) mais uma camada de proxy, seguindo o precedente de
`context_budget.py` / `artifact_gate.py` (specs/030): utilitários sem frontmatter,
invocados pelos agentes via diretiva `Bash:`.

| Componente | Papel |
|---|---|
| `src/shared/tools/headroom/vendor/` | Fork embedded (git subtree) de `headroom-ai` 0.33.0 |
| `headroom_config.py` | Resolve a config: env > `project-config.yaml` > `headroom.yaml` |
| `headroom_context.py` | **Único** decodificador do formato Headroom + fatia por agente |
| `headroom_tool.py` | CLI: `slice · decode · compress · metrics · stats · doctor · proxy` |
| `mcp_server.py` | MCP server `ava-headroom` (5 ferramentas sob demanda) |
| `copilot-cli-headroom.bat` | Copilot CLI BYOK roteado pelo proxy 8787 |

Agentes modificados (todos F1, módulo `asis-diagnostic`):

| Agente | Arquivo | Versão |
|---|---|---|
| `ava-asis-solution-delphi` | `agents/solution-delphi.md` | `2.7.0` → `2.8.0` |
| `ava-asis-inventory` | `agents/inventory-asis.md` | `1.5.0` → `1.6.0` |
| `ava-asis-db-analyzer` | `agents/db-analyzer/db-analyzer.md` | `1.5.0` → `1.6.0` |
| `ava-asis-events-pubsub` | `agents/events-pubsub-asis.md` | `1.1.0` → `1.2.0` |
| `ava-asis-documentation` | `agents/documentation-asis.md` | `3.0.0` → `3.1.0` |

## 2. Problem Statement

A esteira gasta contexto e tempo enviando payload não comprimido ao LLM. Na
execução F1 de `processaERP-008` (ISSUE-002), o payload comprimido somou
**761.376 tokens**, produzindo `runSubagent` de 34, 5 e **62** minutos,
**110,6 min** totais e **8 de 19 artefatos F1 ausentes**.

A spec 030 atacou o *dispatch* (medir antes de gastar, fatiar por agente, guard
anti-storm). Restaram três lacunas, todas do lado da **compressão**:

**P-1 — Nada intercepta as chamadas ao LLM.**
Não existe cliente LLM em Python neste repositório: `grep -rE '^\s*(import|from)\s+(openai|anthropic|azure)' --include=*.py src/` retorna zero.
Os ~97 agentes são arquivos `.md` executados por um *host surface* (Copilot CLI,
Copilot Chat, Claude Code) contra o endpoint Foundry. Não há ponto de código onde
inserir um "step 0 de compressão". A única camada por onde 100% das requisições
passam é um **proxy local**.

**P-2 — O que já está comprimido não é lido.**
A pré-compressão roda hoje **fora** deste repo, no analisador
`ava-fabric-delphi-analyzer/src/headroom_precompress.py`, e grava
`outputs/asis/ast-raw/{lang}/compressed/`. Mas:

- `sql_ir_generator.py` foi **forçado de volta** para `extraction/` com um NOTE
  explicando por quê: o SmartCrusher reescreve arrays como string tabular e
  `table.get(...)` estoura `AttributeError` sobre uma `str`.
- `build_summary_comprehensive.py` carregava um unwrap inline de
  `factored_array` — 4 linhas que só cobriam **um** dos dois formatos possíveis,
  e apenas para `stored_procedures`.

Ou seja: pagava-se o custo da compressão sem colher o benefício, e o único
"decoder" existente era parcial e duplicável.

**P-3 — A economia não é medida por agente.**
`manifest.json` tem `tokens_in/tokens_out` por *artefato*, nunca por *agente*.
Não há como responder "quanto o `db-analyzer` economizou nesta execução".

## 3. Decision

### 3.1 Fork embedded via git subtree (I4)

```
git subtree add --prefix src/shared/tools/headroom/vendor \
  https://github.com/headroomlabs-ai/headroom.git main --squash
```

2.193 arquivos, 60,5 MB, `headroom-ai` 0.33.0. Atualizável com `git subtree pull`
sem quebrar a integração. O build backend do vendor é **maturin** (Rust), então
`setup.ps1`/`setup.sh` detectam `cargo`: com Rust, instalam o fork em modo
editável; sem, instalam o wheel PyPI da **mesma versão** e o fork fica como
referência/patch source. O container (`Containerfile`) instala Rust e **sempre**
builda o fork.

O venv fica em `src/shared/tools/headroom/.venv`, isolado (I7) — o venv principal
do repo continua stdlib-only.

### 3.2 Proxy como ponto de interceptação (P-1 / I3)

`copilot-cli-headroom.bat` é uma cópia de `copilot-cli-v1.bat` com **uma** linha
alterada: `COPILOT_PROVIDER_BASE_URL` aponta para `http://127.0.0.1:8787` em vez
do endpoint. Todo o resto — leitura de `.copilot-key`, `COPILOT_PROVIDER_TYPE=anthropic`,
header `anthropic-version: 2023-06-01`, `--autopilot --no-ask-user` — é preservado.

O proxy encaminha para o endpoint real via `ANTHROPIC_TARGET_API_URL`. **O headroom
não tem flag `--upstream`** (verificado em `headroom proxy --help`, 0.33.0); o
destino Anthropic é `--anthropic-api-url` / `ANTHROPIC_TARGET_API_URL`.

Se o proxy não responder, o `.bat` **degrada para o endpoint direto com aviso** —
nunca bloqueia a sessão (I5). `copilot-cli-v1.bat` fica intacto como rollback.

`run_standalone.ps1` / `.sh` sobem o proxy sem projeto, artefato ou agente (I1).

### 3.3 Decodificador único (P-2 / I10)

`headroom_context.py` é o único lugar do repo que conhece o formato Headroom.
Cobre os **dois** formatos que a pré-compressão produz, determinados
empiricamente rodando o compressor real:

**[A] Motor real — string tabular do SmartCrusher**

```
[400]{columns:int,kind:string,loc:int,name:string,pk:string,schema:string}
3,table,100,TBL_000,ID_0,dbo
```

Cabeçalho `[N]{chave:tipo,…}` (chaves alfabéticas) + linhas **CSV RFC 4180**:
aspas `"`, escape `""`, quebras de linha dentro de campo citado, campo vazio =
`null`. Tipos `string · int · float · bool · json`, sufixo `?` = nullable.
Decodificado com o módulo `csv` da stdlib — **lossless**, validado em roundtrip.

**[B] Motor fallback — `factored_array`**

```json
{"__headroom__": "factored_array", "schema": [...], "count": 400,
 "kept": 90, "sampled": true, "rows": [[...]]}
```

Aqui `sampled: true` é **perda real**. `decode_report()` expõe `rows_dropped`
para que o consumidor saiba que está lendo uma amostra.

`decode_headroom()` é recursivo, idempotente e passa conteúdo não-comprimido
intacto — o consumidor pode chamá-lo sem saber se o artefato foi comprimido.

### 3.4 Reconexão dos consumidores (P-2)

- **`build_summary_comprehensive.py`**: o unwrap inline de 4 linhas sai; entra
  `decode_headroom(raw_sps)`. Ganho colateral: agora cobre também o formato [A],
  que a versão anterior não tratava.
- **`sql_ir_generator.py`**: `extraction/` **continua sendo a fonte preferida** —
  o gerador é determinístico e precisa de 100% das entidades, e o motor fallback
  amostra linhas. O que muda é o novo `_load_ast()`: quando `extraction/` não
  existe, usa `compressed/` decodificado em vez de produzir um `sql-ir.json`
  vazio em silêncio.

### 3.5 Fonte canônica única de fatia (I10)

`headroom_context.AGENT_ARTIFACT_SLICE` **importa** o dict de
`asis-diagnostic/utils/context_budget.py` via `importlib.util.spec_from_file_location`.
O `AGENT_ARTIFACT_MAP` proposto em `docs/plan/headroom-integration-implementation.md`
**não foi criado** — duas fontes concorrentes seriam exatamente a classe de bug
que esta entrega existe para evitar. Há um teste que falha se alguém reintroduzir
o segundo mapa.

### 3.6 Métricas por agente (P-3 / I6)

`headroom_tool.py metrics` faz append em
`projects/{project}/outputs/observability/headroom-metrics.jsonl`, ao lado de
`agent-events.jsonl` e `pipeline-run-state.json`, reusando o idioma de append de
`pipeline_observer._write_agent_metrics`. Timestamps em BRZ (`-03:00`), como o
resto do repo.

Os 5 agentes que consomem artefatos AST ganharam um **Step 1.1 — Registro de
Compressão Headroom** logo após o `track` do Step 1, com o comando literal inline
(sem `@referência`: `observability-self-report.md` v2.2.0 registra que a
indireção era lida pelos LLMs como texto descritivo, não como instrução).

### 3.7 Configuração em camadas (Artigo I)

Precedência: **env** (`HEADROOM_*`, `AVA_FOUNDRY_*`, `ANTHROPIC_TARGET_API_URL`)
→ **`projects/{p}/context/project-config.yaml` bloco `headroom:`** →
**`src/shared/tools/headroom/headroom.yaml`**. Merge recursivo: sobrescrever
`proxy.port` preserva o resto do bloco `proxy`. Nenhum endpoint, modelo ou limiar
hardcoded em código.

### 3.8 Correção de duas premissas do prompt de origem

| Premissa do prompt | Realidade verificada | Consequência |
|---|---|---|
| `HeadroomStep` como step 0 Python em cada agente, chamando `self.foundry_client.call()` | Não há classe de agente nem cliente LLM no repo | Substituído por proxy (interceptação) + CLI via `Bash:` |
| `AZURE_OPENAI_ENDPOINT` + `gpt-4o` + limite 128K | O endpoint é **Anthropic-compatible** (`…services.ai.azure.com/anthropic`), wire model `claude-sonnet-4-6`, limite **200K** | O gap **L1** de `docs/plan/headroom-integration-implementation.md` ("comprime para 200K mas infere em 128K") **não procede** — 200K é o número certo. A correção é tornar o limite explícito e configurável, não alterá-lo. |

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Interceptação de 100% das requisições (CA01)

**Given** o proxy no ar em `127.0.0.1:8787` com `ANTHROPIC_TARGET_API_URL`
apontando para o Foundry, **When** o operador inicia a sessão por
`copilot-cli-headroom.bat`, **Then** `COPILOT_PROVIDER_BASE_URL` é o proxy, toda
requisição passa pela compressão antes do upstream, e `headroom perf` registra
`tokens_before`/`tokens_after`/`latency_ms` por chamada.

### Scenario 2 — Proxy fora do ar não bloqueia a sessão (CA02)

**Given** o proxy não iniciado, **When** o operador roda
`copilot-cli-headroom.bat`, **Then** o script emite `WARNING: Headroom proxy não
respondeu`, define `COPILOT_PROVIDER_BASE_URL` como o endpoint direto, imprime
`headroom compression=no` e a sessão inicia normalmente — sem compressão.

### Scenario 3 — Artefato comprimido pelo motor real é lido sem erro (CA03)

**Given** `05_procedures.json` em `compressed/` com
`payload.stored_procedures` na forma `"[400]{…}\n<csv>"`, **When**
`build_summary_comprehensive.py` monta a tabela de stored procedures, **Then**
`decode_headroom` devolve 400 dicts e a tabela é preenchida — onde antes o
unwrap inline não reconhecia o formato e a tabela ficava vazia.

### Scenario 4 — `extraction/` ausente não zera o sql-ir (CA04)

**Given** um projeto onde `extraction/` foi descartado mas `compressed/` existe,
**When** `SqlIrGenerator.run()` executa, **Then** `_load_ast()` loga
`extraction/ ausente — usando compressed/ decodificado` e gera o `sql-ir.json`
com as entidades — em vez de escrever um IR vazio sem avisar.

### Scenario 5 — Fatia por agente antes do dispatch (CA05)

**Given** um projeto com `compressed/manifest.json`, **When**
`headroom_tool.py -p {p} slice --agent ava-asis-db-analyzer --json` roda,
**Then** devolve exatamente `["03_database_rules", "04_database_schemas",
"05_procedures"]` e o total de `tokens_out` correspondente, batendo com
`context_budget.py --agent` — porque ambos leem o **mesmo** dict.

### Scenario 6 — Economia atribuída ao agente (CA06)

**Given** o Step 1.1 executado por `ava-asis-inventory`, **When** o agente chama
`headroom_tool.py metrics --original 12400 --compressed 1860`, **Then** uma linha
JSONL é acrescentada a `outputs/observability/headroom-metrics.jsonl` com
`savings_pct: 85.0`, e `headroom_tool.py stats` agrega por agente.

### Scenario 7 — Esteira roda sem o motor instalado (CA07)

**Given** um clone sem `src/shared/tools/headroom/.venv`, **When**
`context_budget.py`, `sql_ir_generator.py` e `build_summary_comprehensive.py`
executam, **Then** todos funcionam normalmente: a decodificação é 100% stdlib e
o import de `headroom` é defensivo (`HEADROOM_AVAILABLE = False`). Só a
compressão fica indisponível, degradando para passthrough com aviso.

### Scenario 8 — Modo standalone sem a esteira (CA08)

**Given** nenhum projeto em `projects/` e nenhum agente rodando, **When**
`run_standalone.ps1` executa, **Then** o proxy sobe com os defaults de
`headroom.yaml` e aceita tráfego de qualquer cliente que aponte
`ANTHROPIC_BASE_URL` / `COPILOT_PROVIDER_BASE_URL` para ele.

## 5. Quality Gate Requirements

- [x] Nenhum endpoint, modelo ou limiar hardcoded — tudo em `headroom.yaml` /
      `project-config.yaml` / env (Art. I)
- [x] Version bumps MINOR nos 5 agentes — apenas adições, nenhum contrato removido (Art. X)
- [x] Consistência tripla nos agentes tocados: frontmatter == literal `--version`
      do `track` == `AGENT_CATALOG` em `pipeline_observer.py` **e**
      `generate_observability_report.py`
- [x] Docstrings, logs e corpo dos agentes em pt-BR (Art. V)
- [x] Proxy escuta em `127.0.0.1` por padrão, nunca `0.0.0.0`; `.copilot-key` e
      `.env` continuam gitignorados; nenhuma chave em arquivo versionado (Art. VII)
- [x] Métricas em `outputs/observability/`, ao lado dos artefatos existentes (Art. VIII)
- [x] Cenários BDD cobrem interceptação, degradação, os dois formatos de
      compressão, fatia, métricas, ausência do motor e standalone (Art. VI)
- [x] 22 testes em `tests/tools/test_headroom_context.py`, incluindo guarda
      contra a reintrodução de um segundo mapa de fatias
- [x] Nenhum marcador `[NEEDS CLARIFICATION]` remanescente

## 6. Dependencies

- `asis-diagnostic/utils/context_budget.py` — **fonte canônica** de
  `AGENT_ARTIFACT_SLICE` e de `resolve_compressed_dir()`. Alterar as fatias lá
  altera automaticamente a tool; o inverso não existe por construção.
- `headroom_precompress.py` (repo externo `ava-fabric-delphi-analyzer`) —
  produtor dos artefatos comprimidos. Não alterado nesta entrega.
- `copilot-cli-v1.bat` — base de `copilot-cli-headroom.bat`; permanece intacto
  como caminho de rollback.
- `headroom-ai` 0.33.0 (vendorizado). `pyyaml` (já dependência do módulo).
- Toolchain Rust — **opcional**; sem ele o setup usa o wheel PyPI.

## 7. Exclusions

- **`solution-{vb,vbnet,cobol,powerbuilder}.md`** — herdam a fatia em
  `AGENT_ARTIFACT_SLICE` mas não receberam o Step 1.1. Mesmo critério da
  spec 030 §7: só `solution-delphi` tem extração AST real hoje; `cobol` e
  `powerbuilder` são `0.1.0-stub`.
- **Agentes de consolidação** (`gaps-risks`, `bridge-fastqa`,
  `gap-migration-analyzer`, `security-orchestrator`) — fatia `[]`, não consomem
  artefatos AST; instrumentá-los só geraria linhas com economia zero.
- **Alterar `headroom_precompress.py`** (fase F2 do plano antigo) — exige PR no
  repositório externo. O limite 200K já está correto para o endpoint Anthropic,
  então a motivação original do gap L1 desapareceu.
- **Drift de versão pré-existente em agentes não tocados** — 4 agentes de solução
  seguem fora dos dois `AGENT_CATALOG`. É anterior a esta entrega e fora do
  escopo; registrado aqui para não se perder.
- **`podman-compose` como caminho padrão** — entregue e documentado, mas o fluxo
  suportado no dia a dia é o venv + `run_standalone.ps1`.
- **Reexecução do `processaERP-008`** — ação operacional. Esta entrega a
  habilita, mas não a dispara.

## 8. Assumptions

- O endpoint em `copilot-cli-v1.bat`
  (`aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic`, `claude-sonnet-4-6`)
  é o endpoint de produção da esteira. Se um deployment diferente for usado, o
  valor é sobrescrito por `project-config.yaml` ou env, sem tocar em código.
- Limite de contexto **200.000** tokens para `claude-sonnet-4-6`. Se o deployment
  tiver a janela de 1M habilitada, ajustar `context_limit` — é configurável
  exatamente por isso.
- O formato tabular do SmartCrusher (`[N]{k:t}\n<csv RFC 4180>`) foi determinado
  **empiricamente** contra `headroom-ai` 0.30.0/0.33.0 e validado em roundtrip
  lossless com 520 linhas (vírgulas, aspas, newlines embutidos, nulos, JSON
  aninhado). Não é um formato documentado publicamente — uma mudança de formato
  no upstream exige revalidar o roundtrip após `git subtree pull`.
- `manifest.artifacts[].tokens_out` continua sendo a melhor estimativa de custo
  de contexto por artefato (mesma premissa da spec 030).

## Success Criteria

| Criterion | Measure |
|---|---|
| Decodificação lossless | Roundtrip `compress()` → `decode_headroom()` devolve o objeto original: 520 linhas, 0 diferenças |
| Fonte única do formato | `grep -rn "__headroom__" src/ --exclude-dir=vendor` casa **apenas** em `headroom_context.py` |
| Fonte única da fatia | `grep -rn "AGENT_ARTIFACT_MAP" src/` vazio; `headroom_context.AGENT_ARTIFACT_SLICE` carrega 19 agentes de `context_budget.py` |
| Sem regressão nos consumidores | `pytest tests/utils/ -q` → 28 passed |
| Cobertura da tool | `pytest tests/tools/ -q` → 22 passed |
| Esteira roda sem a tool | `context_budget.py --project X --json` funciona com o venv da tool ausente |
| Interceptação | `copilot-cli-headroom.bat` imprime `headroom compression=yes` com o proxy no ar, `=no` sem ele — nos dois casos a sessão inicia |
| Standalone | `run_standalone.ps1` sobe o proxy sem nenhum projeto em `projects/` |
| Métricas por agente | `headroom_tool.py -p X stats` agrega o JSONL por `agent_id` com `savings_pct` |
| Consistência de versão | Nos 5 agentes tocados, frontmatter == `--version` == ambos os catálogos |
| Manutenção do fork | `git subtree pull --prefix src/shared/tools/headroom/vendor …` seguido de `pytest tests/tools/` |
