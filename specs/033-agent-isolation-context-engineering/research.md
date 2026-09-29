# Research — Isolamento de Janela por Agente + Context Engineering

**Spec**: `specs/033-agent-isolation-context-engineering/spec.md`
**Fonte primária**: `docs/copilot-cli-runtime-facts.md` (spike M0, medido nesta máquina em 2026-08-02)

> Tudo na seção 1 foi **medido**, não estimado. Nenhum arquivo do repo foi alterado durante o spike
> (a sonda `.github/agents/zz-m0-probe.agent.md` foi criada e removida). Fonte dos números:
> `~/.copilot/session-state/<sessionId>/events.jsonl`, campo `session.shutdown`.

---

## 1. Fatos de runtime do Copilot CLI 1.0.77

### 1.1 A janela é 128.000, não 200.000

`grep '"tokenLimit"' ~/.copilot/session-state/*/events.jsonl` → **75 ocorrências, todas `128000`**.
Emitido em `session.compaction_start` e `session.truncation`.

**Impacto:** os limiares de `context_budget.py` (`inline > 400.000`, `bc_scoped > 700.000`) e a
documentação do Headroom (*"janela 200.000 tokens"*) foram calibrados contra uma janela que não
existe. Eles continuam válidos como heurística do **total do pipeline**, não como orçamento por
agente.

### 1.2 Overhead estático — e como cortá-lo 55%

5 sondas idênticas (`-p "reply with exactly: OK"`, `-C <repo root>`, `--model claude-sonnet-4`),
variando só as flags:

| Sonda | Flags adicionais | `systemTokens` | `toolDefinitionsTokens` | **Total estático** | Δ |
|---|---|---:|---:|---:|---:|
| **P1** | — (baseline) | 21.719 | 8.074 | **29.871** | — |
| **P2** | `--no-custom-instructions` | 10.347 | 8.074 | **18.499** | **−11.372** |
| **P3** | `--disable-builtin-mcps` | 21.517 | 7.657 | **29.252** | −619 |
| **P4** | P2 + P3 + `--excluded-tools=skill` | 6.042 | 7.329 | **13.449** | **−16.422 (−55%)** |
| **P5** | `--context long_context` | 21.727 | 8.074 | 29.879 | +8 (ruído) |

P1 rodou duas vezes: 29.871 e 29.873 → repetibilidade ±2 tokens.

Leitura:

- **`--no-custom-instructions` é a maior alavanca (−11.372).** É *mais* do que
  `.github/copilot-instructions.md` sozinho (28,9 KB ≈ 7,2K tokens), logo a flag remove **outras
  fontes de custom instructions** também. Não foi isolado quais. **É essa observação que gera a
  tensão central da spec (§3.2): a flag que economiza mais é a que desliga o `AGENTS.md`.**
- `--disable-builtin-mcps` rende pouco (−619): o `github-mcp-server` responde por só 417 dos 8.074
  tokens de definição de tool. Vale ligar (é grátis), mas não é onde está o ganho.
- `--excluded-tools=skill` rende ~−4.400 (derivado de P4 vs P2+P3). As 75 skills de `.github/skills/`
  entram no prompt de sistema. No modelo de runner o agente recebe a spec por `view`, então não
  precisa da tool `skill` — é ganho limpo. **Promovida a flag padrão do runner.**

### 1.3 Orçamento real por processo

```
128.000  janela
−13.449  estático com as flags do runner (P4)
− ~8.000  reserva de saída
─────────
~106.000 úteis para context pack + spec + trabalho
```

Contra o baseline atual (29.871 estáticos) sobrariam ~90.000. **As flags recuperam ~16K tokens por
processo** — em F1 com ~19 nós, ~312K tokens de overhead evitado por execução.

O CLI já avisou explicitamente em 2 sessões reais: `session.warning` →
`"warningType":"compaction_static_context_budget"` → *"Static context is using 76% of available input
tokens… system messages and tool definitions cannot be reclaimed."*

### 1.4 `--context long_context` — NÃO verificado

A flag é aceita e `session.start` passa a registrar `"contextTier":"long_context"` (o baseline
registra `null`). Mas **nenhuma sessão long_context chegou a compactar**, então nenhum `tokenLimit`
foi emitido para esse tier. **O limite continua desconhecido.** Não assumir que é maior sem medir.
Removido do `wave1` do DAG.

### 1.5 `tools:` é enforçado — `version:` e `allowed-tools:` são descartados

Sonda com `tools: ["glob"]`, instruída a usar `view`. Resposta do modelo:

> *"I found `README.md` via glob, but I don't have a `view` tool available in this environment."*
> **TOOL_UNAVAILABLE**

Nenhum `tool.execution_start` de `view` no `events.jsonl`. **A restrição é real, não sugestão.**

Com `--log-level warning`:

```
[WARNING] .github\agents\zz-m0-probe.agent.md: unknown fields ignored: version, allowed-tools
```

O frontmatter atual dos 107 agentes usa **exatamente essas duas chaves**. Um gerador que as emitisse
produziria agentes com todas as tools liberadas e sem versão.

Campos aceitos: `description` (obrigatório), `name`, `tools`, `model`, `target`,
`disable-model-invocation`, `user-invocable`, `mcp-servers`, `metadata`.

### 1.6 Nomes reais das tools

De `"toolName"` em todas as sessões:

| Tool | Invocações | Tool | Invocações |
|---|---:|---|---:|
| `task` | 1.251 | `skill` | 35 |
| `powershell` | 918 | `read_powershell` | 24 |
| `view` | 674 | `sql` | 11 |
| `grep` | 577 | `task_complete` | 8 |
| `glob` | 455 | `read_agent` | 8 |
| `create` | 148 | `ask_user` | 7 |
| `edit` | 124 | `web_fetch`, `web_search`, … | 1–2 |

Dois pontos que afetam o gerador:

1. **A tool de shell chama-se `powershell`, não `bash`.** Os agentes escrevem `Bash:` nos Execution
   Steps (`batch-write-protocol.md` inclusive). Funciona hoje porque o modelo mapeia a intenção, mas
   qualquer `tools:` gerado precisa listar `powershell`.
2. **`task` é a tool mais usada (1.251)** — é o dispatch in-prompt de sub-agente que o runner
   substitui.

### 1.7 Detecção de conclusão

- **Exit code**: `0` em todas as 6 sondas bem-sucedidas; `1` em erro de argumento (*"Invalid command
  format"* — o prompt precisa vir entre aspas). **Não distingue falha de artefato** → o gate manda.
- **`--output-format json`**: o último evento é `{"type":"result","sessionId":…,"exitCode":0,
  "usage":{…}}`.
- **`events.jsonl` (fonte de verdade, mais rica)**: `session.start` (`contextTier`, `model`) ·
  `session.shutdown` (`systemTokens`, `toolDefinitionsTokens`, `currentTokens`, `modelMetrics.*.usage`,
  `totalApiDurationMs`) · `session.compaction_start` / `session.truncation` (**sinal de
  `context_overflow`**) · `session.warning` · `session.error` · `tool.execution_complete`.

Taxonomia de erro observada: `errorType` ∈ {`query` (87), `authentication` (2), `quota` (1)};
`statusCode` ∈ {404 (87), 401 (1), 402 (1)}.

### 1.8 O proxy Headroom é bloqueador, não detalhe

**87 erros 404 em 25 sessões distintas**, todos "Model not found":

| Endpoint | Ocorrências |
|---|---:|
| `http://127.0.0.1:8787` (**proxy Headroom**) | **71** |
| `https://…services.ai.azure.com/anthropic` (direto) | 6 |
| `…openai.azure.com/openai/deployments/claude-sonnet-4-6` | 5 |
| outras variantes | 5 |

As 6 sondas do M0 foram **direto** ao Foundry e todas retornaram `exit 0`. O Copilot valida o wire
model via `GET /v1/models/{modelo}`, rota que o headroom encaminha em vez de responder localmente, e
a superfície Anthropic do Foundry devolve 404.

**Consequência:** o runner opera **hoje** só na rota direta. Rodar comprimido exige antes o shim
local de `/v1/models/{id}` (contorno 3 do Anexo A de `02-esteira-github-cli.md`). O runner registra
`compression=on|off` por nó e **não** degrada em silêncio — ao contrário do `.bat`, que degrada
silenciosamente hoje.

### 1.9 Ruído sem impacto funcional

Presente em todas as execuções, sem afetar `exit 0` — filtrar no parser de log do runner
(`BENIGN_LOG_PATTERNS`, já definido em `agent_runner.py` e ainda sem uso):

- `[ERROR] Request to Copilot Task API failed … /agents/tasks/<sid> … 404` — ocorre **mesmo com**
  `--no-remote --no-remote-export`.
- `[ERROR] GitHub MCP server configured after authentication`.
- `[WARNING] could not load remote agents, no GitHub remote found`.

### 1.10 `~/.copilot/agents/` não existe nesta máquina

O risco de shadowing do diretório de usuário sobre `.github/agents/` é **nulo hoje**. O preflight do
gerador deve mesmo assim falhar em colisão — o diretório pode ser criado a qualquer momento e tem
precedência.

---

## 2. As 5 técnicas de Context Engineering aplicadas ao formato `.md`

Os quatro pilares (Write / Select / Compress / Isolate) + partição, adaptados a agentes `.md`.
As regras são **independentes da superfície de execução** — valem também para o motor LangGraph em
`engine/`.

| # | Técnica | O que muda no `.md` | Onde entra nesta spec |
|---|---|---|---|
| **1** | **Isolate** — offloading por sub-agente | Cada agente vira custom agent nativo com janela própria. A janela do orquestrador só vê resumos + paths, nunca o 1,5M LOC | §3.1 · `agent_runner.py` · os 102 `.agent.md` |
| **2** | **Select** — retrieval *just-in-time* | Trocar "Glob all + classificar tudo" por: um passo barato gera o índice; o agente recupera só as fatias relevantes (grep/glob + faixa de linhas). Nunca `cat` de arquivo grande | §3.4 · `context_pack.py` seções 1 e 3 · regra em `AGENTS.md` |
| **3** | **Compress** — redução | Cada agente emite resumo estruturado compacto (o Output Contract). O padrão grep-extract do `artifact-map.yaml` (hoje isolado na F8) generaliza para todo handoff: o consumidor puxa só as linhas que precisa. Orçamento por agente | §3.4 · seção 2 do pack · protocolo de handoff em `AGENTS.md` |
| **4** | **Write** — memória externa em disco | `shared-context.md` pequeno e curado (status + índice + decisões); nunca despejar conteúdo. **Passar paths, não conteúdo** | §3.4 seção 5 · protocolo do `shared-context.md` em `AGENTS.md` |
| **5** | **Chunk** — partição por bounded-context | Fan-out de um sub-agente por módulo/bounded-context (`scope_modules` alimentado pelo particionamento), cada um limitado ao seu módulo. Priorização por risco/complexidade | `F1.yaml` (`max_parallel`) · degrau 3 da escada de retry (recorte por `module-partition.json`) |

**Query engineering (transversal):** os agentes fazem perguntas dirigidas (grep por símbolos/padrões:
`CREATE PROCEDURE`, `TForm`, strings SQL) em vez de leituras abertas.

**Dedup (transversal):** guardrails, persona e convenções repetidos migram para `AGENTS.md`,
mantendo cada `.agent.md` enxuto (< 30K chars) e as regras aplicadas em toda a esteira.

### 2.1 Por que só o pack, e não o knowledge graph, nesta spec

O plano `docs/plan/memory-archotecture-middleware-knowledge-graph.md` propõe três camadas
(knowledge-units → grafo tipado → retrieval BM25/FTS5). É a evolução certa da técnica 2, mas:

- O pack determinístico já resolve o modo de falha da ISSUE-002 (agente recebe fatia limitada e
  orçada) com **zero código de indexação novo** — reusa `headroom_context.build_agent_context()` e
  `headroom_tool.py slice|decode`, ambos existentes.
- O grafo acopla dois riscos independentes (isolamento de processo × qualidade de retrieval) numa
  entrega só.
- O grafo pluga **depois sem mudar os agentes**: o pack é um arquivo em disco, e trocar quem o
  produz é invisível para quem o consome.

Por isso: pack agora (spec 033), grafo na spec 034.

---

## 3. Alternativas consideradas e descartadas

| Alternativa | Por que não |
|---|---|
| **Delegação nativa pura** (orquestrador usa a tool `task` para cada `.agent.md`, sem runner) | O M0 observou `subagent.started → "model":"gpt-5.4"` seguido de 404 do modelo BYOK e `totalToolCalls: 0`. Sem `--model` pinado e sem `--session-id` determinístico não há gate, retry, telemetria real nem detecção de `context_overflow`. Fica **disponível** para uso interativo, não como caminho de produção |
| **Só reforçar as regras nos `.md`** (retrieval-first sem pack materializado) | É o que já falha hoje: regra em prosa depende do LLM lembrar. O repo já catalogou 51 violações de um bloco mantido à mão em ~100 arquivos (`specs/032`) |
| **Escrever os 102 wrappers à mão** | Recria exatamente o modo de falha que produziu o `agent_registry.py` ("52 de 101 agentes ausentes, 18 versões divergentes") |
| **Manter `--no-custom-instructions` e abrir mão do `AGENTS.md`** | Contraria o requisito explícito. A injeção do bloco resolve os dois lados |
| **Tirar `--no-custom-instructions` e encolher o `copilot-instructions.md`** | Custaria ~2K tokens em **todo** processo e exigiria mexer no arquivo que o `/speckit.plan` reescreve automaticamente. A injeção cobra o mesmo conteúdo só na janela do agente que o usa |
| **Migrar as 8 fases de uma vez** | Migra em massa uma esteira que funciona no caminho interativo — risco de regressão simultânea em todas as fases. F1 é a que tem a falha documentada |
| **`--allow-all` / `--yolo` no runner** | Implicam `--allow-all-paths`, anulando qualquer cerca de path. O `.bat` interativo usa e permanece intocado; o runner usa `--allow-all-tools --no-ask-user` |
| **`--autopilot`** | `-p` já roda até o fim; autopilot adiciona turnos de continuação |
| **`--resume` / `--continue`** | Cada nó precisa nascer com janela limpa — é o ponto inteiro da mudança |
| **FTS5 no índice de consulta** | Adiciona tempo de build e um segundo dialeto de query para uma necessidade ainda não demonstrada. Entra quando uma consulta falhar sem ele (spec 034) |
| **MCP retrieval server (embeddings) por agente** | Camada opcional para 1,5M+ LOC; plugável via `mcp-servers` no frontmatter **sem mudar os bodies**. Fora do escopo desta referência |

---

## 4. Referências

- `docs/copilot-cli-runtime-facts.md` — spike M0 (fonte de todos os números da seção 1)
- `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md` — o modo de falha
- `docs/issues/ISSUE-003-tool-call-overhead-f1-f2-performance.md` — overhead de tool call
- `src/shared/tools/headroom/docs/02-esteira-github-cli.md` § Anexo A — o 404 do proxy
- `specs/031-headroom-context-compression-proxy` · `specs/032-headroom-pipeline-wide-attribution`
- `specs/030-asis-pipeline-context-budget-dispatch-guard` — origem do `context_budget` / dispatch guard
- `.specify/memory/constitution.md` v1.4.0 § Project Reference — mapa Fase→Módulo
- `docs/plan/escala-esteira-contex-engineering.md` · `docs/plan/contex-eginerring-github-copilot.md`
  — planos consolidados nesta spec
- `docs/plan/memory-archotecture-middleware-knowledge-graph.md` — reservado para a spec 034
