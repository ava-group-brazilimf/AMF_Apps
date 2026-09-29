# Agent Specification: Isolamento de Janela por Agente + Context Engineering (GitHub Copilot CLI)

**Feature Branch**: `033-agent-isolation-context-engineering`
**Created**: 2026-08-02
**Status**: Draft
**Change Type**: add-new (`AGENTS.md` · gerador de wrappers · context pack · hook de enforcement)
+ modify-existing (`agent_runner.py` · `F1.yaml` · `orchestrator-asis.md` MAJOR · 3 utils PATCH)
**Input**: "Todo agente chamado pelo orquestrador da fase executa em uma janela isolada, usando com
mais eficiência a feature do GitHub Copilot CLI; todos os agentes customizados em
`.github/agents/*.agent.md`. O `AGENTS.md` deve ser criado com as regras/guardrails gerais para o
GitHub Copilot carregar — nada específico de linguagem legada, serve para java, delphi, .net e
outras; todos os agentes herdam. O shared context deve ser trabalhado de maneira eficiente com um
contexto de memória. **O modo de execução via GitHub CLI permanece o mesmo** — a diferença é que, ao
executar o orquestrador, os agentes invocados atuam na própria janela de contexto."

---

## 1. Identidade

Sem agente novo. Muda **como** os 102 agentes despacháveis existentes são invocados e **o que** cada um enxerga.

| Componente | Papel |
|---|---|
| `AGENTS.md` (raiz) | **Novo.** Fonte única dos guardrails gerais, 100% language-agnostic. Carregado nativamente no fluxo humano; injetado nos wrappers no fluxo do runner |
| `src/shared/tools/generate_agent_wrappers.py` | **Novo.** Gera os 102 `.github/agents/*.agent.md` a partir do `agent_registry.py` |
| `src/shared/tools/context_pack.py` | **Novo.** Materializa o contexto de cada agente em disco, dentro do orçamento — o "shared context com memória" |
| `src/shared/tools/hooks/pretooluse_guard.py` + `.github/hooks/ava-guardrails.json` | **Novos.** Transformam o LARGE ARTIFACT PROTOCOL de prosa em regra executável |
| `src/shared/tools/agent_runner.py` | **Existe (M1).** Ganha context pack, paralelismo, escada de retry e `execution_backend` |
| `src/shared/data/pipeline-dag/F1.yaml` | **Existe (parcial).** Passa de 3 nós para o DAG F1 completo |
| `orchestrator-asis.md` | 193.848 → ~15 KB. Deixa de despachar in-prompt e passa a invocar o runner |
| `src/shared/utils/validate_language_agnostic.py` | **Novo.** Lint por allowlist sobre `AGENTS.md` + wrappers |

**Agentes novos**: nenhum. **Skills novas**: nenhuma (os 75 `SKILL.md` continuam sendo a entrada humana).

---

## 2. Problem Statement

### P-1 — Uma janela para 102 agentes

O ponto de entrada real da esteira são os **orquestradores de fase** (`ava-asis-orchestrator` F1,
`ava-tobe-orchestrator` F2, `ava-stack-orchestrator` F4, `ava-qa-orchestrator` F5,
`ava-devops-orchestrator` F6 + F3/F7/F8). Cada um despacha seus sub-agentes **dentro do próprio
prompt** (`DISPATCH @agent-id` + `AWAIT "↳ ✅ [agent-id]"`, `orchestrator-asis.md` § DAG Event
Protocol, L165). Consequência direta: **tudo compartilha uma janela de contexto**.

O modo de falha está documentado em `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md`: em
`processaERP-008` (363 units, 174.375 LOC — **um décimo** do alvo de 1,5M LOC) a saída AST comprimida
somou **761.376 tokens**. Chamadas de 34, 5 e 62 minutos; 3 dispatches do mesmo agente em 16
segundos; **8 de 19 artefatos F1 nunca gerados**.

Compressão não resolve acumulação — só adia o estouro.

### P-2 — O orçamento real é metade do que a esteira assume

Medido no M0 (`docs/copilot-cli-runtime-facts.md`, Copilot CLI 1.0.77, 6 sondas nesta máquina):

| Fato | Valor medido | Consequência |
|---|---|---|
| Janela | **128.000**, não 200.000 (75 ocorrências de `tokenLimit`, todas 128000) | os limiares 400K/700K de `context_budget.py` foram calibrados contra uma janela que não existe |
| Overhead estático baseline | 29.871 (23,3%) | sobram ~90K, não 200K |
| Overhead com as flags do runner | **13.449 (−55%)** ⚠️ obsoleto — ver § 2.1 | **~106.551 úteis por processo** |
| `--no-custom-instructions` | **−11.372** | maior alavanca isolada |
| `--excluded-tools=skill` | −4.400 | as 75 skills entram no system prompt |
| `--disable-builtin-mcps` | −619 | grátis, mas não é onde está o ganho |

O CLI já emitiu o aviso explícito em 2 sessões reais: `session.warning` →
`"warningType":"compaction_static_context_budget"` → *"Static context is using 76% of available input
tokens… system messages and tool definitions cannot be reclaimed."*

### P-2.1 — Os 102 wrappers mudam o orçamento (re-medido em 2026-08-03)

O M0 mediu com **1** agente customizado em disco. Depois que a spec gerou os 102 wrappers e o
`AGENTS.md`, os números mudaram o suficiente para invalidar o orçamento anterior
(`docs/copilot-cli-runtime-facts.md` § 10):

| Sonda | `systemTokens` | `toolDefinitions` | Total |
|---|---:|---:|---:|
| M0 baseline (1 agente, sem `AGENTS.md`) | 21.719 | 8.074 | 29.793 |
| `.bat` interativo hoje | 23.709 | 18.920 | **42.629** |
| Flags do runner do M0 (`skill` só) | 6.042 | 18.175 | 24.217 |
| Flags do runner **+ `task` excluída** | 5.157 | 5.781 | **10.938** |

Duas leituras, ambas verificadas:

1. **O `AGENTS.md` é carregado automaticamente** — `systemTokens` +1.990, coerente com os 8,1 KB.
   Nenhuma flag necessária; basta o CLI enxergar a raiz do repo.
2. **O catálogo dos 102 agentes viaja na definição da tool `task`** (+10.846 tokens ≈ 120 por
   agente). Sem excluí-la, os wrappers **anulariam** a economia das flags no processo isolado:
   24.217 em vez de 13.449. Com `--excluded-tools=skill,task` o estático cai para **10.938** —
   melhor que o número original — e o orçamento útil sobe para **~109.062**. Um nó folha do DAG
   não delega para ninguém.

### P-3 — Ingestão exaustiva por design

Todo agente analítico faz ingestão total: `step-02-code-analysis.md` traz o critério *"Todos os
arquivos do escopo classificados"*. Em ~80 arquivos `.md` **não há uma única menção** a chunking,
retrieval, sumarização, compactação, orçamento de tokens ou amostragem. A única técnica de redução
existente (grep-extract do `artifact-map.yaml`) está isolada na fase F8. O escopo só é filtrado por
`scope_modules` manual, com default `"all"` — e em `MeuERP-002` a chave nem existe (bug §2.5).

O `shared-context.md` é um blackboard relido "full content", sem compactação.

### P-4 — O formato `.agent.md` não está sendo usado

| Situação | Número |
|---|---|
| Specs de agente em `src/modules/**/agents/*.md` | **107** (3.512.663 chars) |
| Com wrapper `.github/agents/*.agent.md` | **1** (`ava-asis-inventory`, escrito à mão) |
| Com wrapper `.github/skills/*/SKILL.md` | 75 → **32 agentes sem nenhum wrapper** |
| `AGENTS.md` na raiz | **não existe** em lugar nenhum do repo |
| Corpos acima do cap de 30.000 chars | **37 de 107** (`orchestrator-asis.md` 193.848; `security-orchestrator-asis.md` 114.996) |

O dispatch por `@nome` para um agente sem wrapper **falha em silêncio**:
`tool.execution_complete → "success":false, error: "Skill not found: ava-qa-orchestrator"` — e a
sessão "caiu para execução direta", produzindo artefato nenhum.

Além disso, o M0 verificou que o frontmatter usado hoje pelos 107 agentes (`version:` +
`allowed-tools:`) é **descartado** pelo parser (`[WARNING] unknown fields ignored: version,
allowed-tools`); a chave enforçada é `tools:`. Um wrapper gerado com as chaves erradas nasce com
todas as tools liberadas e sem versão.

### P-5 — Dois bugs de runtime que hoje passam por "problema de contexto"

Encontrados nos logs, não são hipótese:

1. **Sub-agentes internos não herdam o modelo BYOK.** `subagent.started →
   "agentName":"general-purpose","model":"gpt-5.4"`, seguido de `session.error → "Model
   'claude-sonnet-4-6' not found on provider (HTTP 404)"` e `subagent.completed` com
   `"totalToolCalls":0`. Parte dos "agentes que não produziram nada" é roteamento de modelo, não
   janela.
2. **`--add-dir` não cerca nada.** `-C <REPO_ROOT>` é obrigatório (as 107 specs usam paths
   repo-relativos), e o `cwd`/`gitRoot` é implicitamente permitido — então `outputs/asis/ast-raw/`
   já está dentro da árvore liberada. O LARGE ARTIFACT PROTOCOL existe só como texto de prompt.

### P-6 — Regra em prosa não é enforcement

As mitigações existentes (`AGENT_ARTIFACT_SLICE`, LARGE ARTIFACT PROTOCOL, proxy Headroom,
`artifact_gate.py`) estão certas, mas vivem em texto de prompt. As 14 regras do DAG Event Protocol
dependem do LLM lembrar de segui-las. O repo já provou onde isso dá: `specs/032` catalogou **51
violações de consistência** mantidas à mão em ~100 arquivos.

---

## 3. Decision

### 3.1 Isolamento híbrido — um formato de agente, dois modos de entrada

```
PRODUÇÃO   humano → copilot-cli-headroom.bat → ava-asis-orchestrator (~15 KB)
                       └ powershell: agent_runner.py --project P --phase F1
                            ├ copilot -p --agent ava-asis-inventory     ← janela própria
                            ├ copilot -p --agent ava-asis-db-analyzer   ← janela própria
                            └ copilot -p --agent ava-asis-events-pubsub ← janela própria

INTERATIVO humano → copilot → /agent → ava-asis-inventory               ← janela própria (nativa)
```

**O modo de execução via CLI não muda.** `copilot-cli-headroom.bat` e `copilot-cli-v1.bat` ficam
byte-idênticos; o humano abre o CLI e chama o orquestrador da fase exatamente como hoje. A única
diferença é que o orquestrador troca N dispatches in-prompt por **uma** chamada ao runner, e cada
agente nasce numa janela limpa de ~106K.

Por que o runner e não só a delegação nativa: o M0 já observou o bug P-5.1 (sub-agente cai em
`gpt-5.4` e 404). O runner **pina** `--model claude-sonnet-4`, gera o `--session-id`, e portanto lê
`events.jsonl` num caminho determinístico — sem parsear stdout. Isso dá gate, retry, telemetria real
e detecção de `context_overflow`, que a delegação nativa não oferece. A delegação nativa continua
disponível porque os wrappers são `user-invocable` e model-invocable.

Cada fase é autônoma: F1 migra sem tocar em F2. O gate entre fases continua sendo o que já é —
artefatos em disco, verificados por `artifact_gate.py`.

### 3.2 `AGENTS.md` é a fonte única, entregue por dois caminhos

**A tensão central desta spec:** `--no-custom-instructions` é a maior economia medida (−11.372) e é
exatamente a flag que **desliga o carregamento do `AGENTS.md`**. Requisito e otimização são
diretamente conflitantes.

```
AGENTS.md (raiz, ≤ 8 KB, language-agnostic)
   │
   ├─ fluxo INTERATIVO ──── o Copilot CLI carrega nativamente
   │
   └─ fluxo RUNNER (--no-custom-instructions)
         └─ generate_agent_wrappers.py injeta o bloco delimitado
            <!-- AGENTS-CORE:START --> … <!-- AGENTS-CORE:END -->
            no corpo de cada .agent.md gerado
```

O bloco é **injetado, nunca editado à mão**; `tests/test_agent_wrappers.py` afirma que o bloco de
todo wrapper bate byte-a-byte com `AGENTS.md`. Custo: ~1,5K tokens no corpo do agente — cobrado **só
na janela dele** — contra 11,4K de custom instructions em **todo** processo. Herança real, sem
regressão de orçamento.

Conteúdo do `AGENTS.md`, todo neutro de linguagem: Output Integrity Rules destiladas · protocolo de
retrieval (pack primeiro, ingestão exaustiva proibida, consulta dirigida) · orçamento de contexto
(~106K; degradar e registrar, nunca truncar em silêncio) · protocolo de handoff por extract ·
protocolo do `shared-context.md` (índice, não depósito; passar paths, nunca conteúdo) · batch write ·
guardrails comuns (read-only no legado, mascarar credenciais, `trace_id` sem mutar) · convenções de
path · resolução de linguagem via `legacy_technology` do `project-config.yaml`.

`.github/copilot-instructions.md` **permanece** para o fluxo humano e para o bloco gerenciado do
SpecKit (`<!-- SPECKIT START/END -->`, que `/speckit.plan` reescreve).

### 3.3 Os 102 wrappers são gerados, não escritos

Fonte: `agent_registry.py` — o registro canônico que **já existe** e que nasceu justamente porque dois
`AGENT_CATALOG` mantidos à mão divergiram ("52 de 101 agentes ausentes, 18 versões divergentes",
`specs/032`). Escrever 102 wrappers à mão recriaria exatamente esse modo de falha.

Regras impostas pelo M0, todas verificadas:

| Regra | Motivo medido |
|---|---|
| Emitir `tools:`, **não** `allowed-tools:` | `allowed-tools` é descartado; `tools` é enforçado de verdade |
| **Não** emitir `version:` — vai em `metadata:` | `version` é descartado com warning |
| Mapear `Bash→powershell`, `Read→view`, `Write→create`, `Glob→glob`, `Grep→grep` | a tool de shell chama-se `powershell`; o `TOOL_NAME_MAP` já existe em `agent_runner.py:81` sem uso |
| Corpo < 30.000 chars | cap verificado; 37 dos 107 corpos originais estouram |
| Preflight falha em colisão com `~/.copilot/agents/` | o diretório do usuário tem precedência sobre `.github/agents/` |

O wrapper é fino (~2 KB) e aponta para a spec canônica em `src/modules/.../agents/*.md`, que
permanece **a fonte única do conteúdo de domínio**. É o mesmo padrão dos 75 `SKILL.md` atuais
(~890 chars), agora com cobertura completa e `tools:` correto.

Gera-se **102** — os 107 arquivos de spec menos as 4 sub-skills de `db-analyzer/skills/`
(apoio lido por um agente pai, sem identidade de execução) e 1 agente depreciado. Fecha a lacuna
dos 32 agentes hoje alcançáveis só por dispatch textual.

### 3.4 O "shared context com memória" é um context pack determinístico em disco

`projects/{p}/outputs/.context/{agent_id}/context-pack.md`, escrito pelo runner **antes** do spawn:

| Seção | Conteúdo | Por quê |
|---|---|---|
| 1 — Sua fatia | AST já decodificado do formato Headroom, limitado ao `AGENT_ARTIFACT_SLICE` | o agente não precisa descobrir o que ler |
| 2 — Índice de artefatos upstream | paths + seções + tamanho (~1 KB), **nunca conteúdo** | hand-off barato; o consumidor puxa só o que precisa |
| 3 — Como consultar o que não está aqui | `headroom_tool.py slice \| decode` | `ast-raw/` é negado pelo hook; a alternativa tem que ser acionável |
| 4 — Seu output contract | do `artifact_gate` — o que falta | o agente sabe exatamente o que produzir |
| 5 — Estado da fase | extrato curado do `shared-context.md` | o blackboard vira índice |

Reusa `headroom_context.build_agent_context()` (`headroom_context.py:335+`), que **já existe** e já
devolve a fatia decodificada com `tokens_estimated`. O pack é a materialização disso em disco.

**Gate de orçamento** — a peça que falta hoje: se a fatia excede o budget, o pack degrada para
*query-only* (seção 1 vira contagens + instruções de consulta) e **registra a decisão no próprio
pack**. Nenhum agente recebe pack maior que a janela. Hoje o runner só imprime um `⚠`.

**Determinismo obrigatório**: mesmo input → pack byte-idêntico (ordenação por chave; nenhum `set()`
iterado sem `sorted()`).

**Fora de escopo, reservado para a spec 034**: knowledge graph, `ast_index.py`, FTS5/BM25,
write-back F2. A camada de consulta usada aqui é `headroom_tool.py slice|decode`, **que já existe** —
reuso em vez de código novo.

### 3.5 O hook `preToolUse` é o primeiro enforcement executável

```json
{"permissionDecision": "deny",
 "permissionDecisionReason": "Artefato AST fora do context pack. Use: python src/shared/tools/headroom/headroom_tool.py slice -p <proj> --artifact <n>"}
```

Nega leitura sob `outputs/asis/ast-raw/` ou de arquivo ≥ 200 KB. É necessário porque `--add-dir`
não cerca o repo (P-5.2) — o enforcement tem que vir do hook, não do escopo de path. `--add-dir` fica
só para as árvores de código legado **fora** do repo.

É a primeira vez que o LARGE ARTIFACT PROTOCOL vira regra que o modelo não pode ignorar.

### 3.6 O DAG é A fonte, com teste anti-divergência

`pipeline-dag/F1.yaml` passa de 3 nós (wave2) para o DAG F1 completo, extraído das tabelas
`## Agent Team` / `Artifact Output Contract per Agent` de `orchestrator-asis.md`.

**⚠️ Risco #1 — quarta fonte de verdade.** O repo já tem três espelhos manuais que divergiram:
`artifact_gate.ARTIFACT_CONTRACTS` (*"espelha 1:1 a tabela de `orchestrator-asis.md`; alterar um lado
exige alterar o outro"*), `context_budget.AGENT_ARTIFACT_SLICE`, e os dois `AGENT_CATALOG` que
produziram o `agent_registry.py`. Adicionar um quarto par manual **pioraria** o modo de falha
recorrente do repo.

Mitigação obrigatória — `tests/test_pipeline_dag.py`:
`dag.nodes ≡ ARTIFACT_CONTRACTS.keys() ≡ agent_registry.catalog()` **e**
`dag[n].slice ≡ AGENT_ARTIFACT_SLICE[n]` (comparação de **conteúdo**, não só de presença como o
`validate_dag` atual) + aciclicidade + todo nó com `slice`, `timeout_s` e artefatos.

### 3.7 O orquestrador de fase encolhe para o que só ele pode fazer

`orchestrator-asis.md`: 193.848 → ~15 KB. Fica com: resolver `project-config.yaml` /
`legacy_technology` / `scope_modules` / `trace_id`; Step 0 (AST via `run_ast_analysis.py`) e o
Solution Agent Gate (regra 9 — HALT total em falha ou `implementation_status == STUB`); **uma**
chamada ao runner; ler o relatório, aplicar os gates de fase, consolidar `master-report.md` + Summary.

Saem do prompt e viram `F1.yaml`: `## Execution DAG` (L99), `## DAG Event Protocol` (L165 — as 14
regras + `dispatch_schedule`), a tabela `Artifact Output Contract per Agent` (L839) e a tabela de
roteamento `SOLUTION_AGENTS` hoje duplicada como comentário YAML (passa a vir do `agent_registry`).

As regras 10/11/13/14 (Context Budget Gate · Dispatch Guard · `artifacts_confirmed` **medido, nunca
declarado** · Wave Guard) deixam de ser prosa e viram código no runner — que já faz gate, budget e
verificação por artefato. Isso resolve o cap de 30 KB **sem** "progressive disclosure" genérico.

### 3.9 Feedback de execução — 4 recomendações apuradas (2026-08-03)

Uma sessão real do Copilot CLI emitiu 4 recomendações ao terminar. Cada uma foi apurada contra o
código e contra 70 sessões de log. **Duas se confirmaram, duas não** — e as recusas ficam aqui com o
motivo, porque recusa sem evidência é opinião.

| # | Recomendação | Veredito | O que foi feito |
|---|---|---|---|
| 1 | "sempre sync mode para agentes AS-IS — background sem `read_agent` descarta resultados" | ✅ **confirmada, e pior do que descrita** | Ver abaixo — não é modo de execução, é modelo |
| 2 | "configure `HEADROOM_LOG_FILE` para timestamps NTP reais" | ❌ **errada** | A variável não gera timestamp NTP e já é default (`headroom.yaml:49` → `proxy_env()`). Provável eco de `headroom_tool.py:470-471`. Corrigido o defeito **vizinho**: o fallback silencioso do `ntp_time.py` |
| 3 | "aguarde 1 turno antes de validar arquivos — timing de propagação" | ❌ **sem lastro** | Nenhum incidente do repo atribui artefato ausente a latência; o único falso negativo documentado (ISSUE-003 § 6.1) era **path errado**, e os arquivos estavam em disco o tempo todo. Um sleep cego o teria escondido |
| 4 | "`AGENTS.md=AUSENTE` não apareceu → carregou" | ✅ confirmada, evidência fraca | O echo do `.bat` só prova que o **arquivo existe**. A prova direta é `/instructions` |

**O achado da #1** (`docs/copilot-cli-runtime-facts.md` § 11): em 1.033 dispatches de subagente,
`general-purpose`→`gpt-5.4` terminou com **zero tool calls em 53 de 53** e `explore`→`gpt-5.4-mini`
em **19 de 24**, contra 1% do `task`→`claude-sonnet-4`. São **78 dispatches desperdiçados**, e a
esteira seguiu como se tivessem retornado resultado. A causa não é modo de execução: os tipos
embutidos trazem modelo próprio, e sob BYOK a troca dispara validação do wire model que retorna 404 —
o subagente morre antes da primeira ferramenta. Nenhuma quantidade de `sync mode` corrige isso.

Correções, todas nesta entrega:

- **`AGENTS.md` § 5 (D1/D2)** — proíbe delegar a `general-purpose`/`explore`. Entra pelo bloco
  `AGENTS-CORE`, então alcança **F1–F8** de uma vez; a `FILE_PERSISTENCE_RULE` equivalente só existia
  em 8 arquivos sob `asis-diagnostic/`. Isso elevou o teto do `AGENTS.md` de 8 KB para **9 KB** —
  decisão deliberada, ~250 tokens a mais por janela.
- **`agent_runner._classify()`** — subagente fora do modelo pinado **ou** com 0 tool calls vira
  `config_error` (aborta, não retenta). Vem **antes** do gate de artefato: se o subagente morreu, o
  artefato ausente é consequência, e reportar a causa vale mais que o sintoma.
- **`check_session_health.py`** — o mesmo diagnóstico para o caminho **interativo**, onde não há runner.
- **`ntp_time.py`** — o fallback deixa de ser mudo: stderr + **exit 3**, e `--json` com `ntp_fallback`.
  Stdout e a invocação sem flags ficam idênticos, senão quebraria a auto-aprovação de
  `.vscode/settings.json` e os ~10 call sites.
- **`artifact_gate.py --recheck-ms`** — re-check **só** no caminho negativo e **só** se pedido. No
  guard pré-dispatch "incompleto" é o estado normal, então re-checar ali atrasaria todo agente. Com
  contador: se após alguns runs o resgate não acontecer, a recomendação #3 cai com dado.

**Não resolvido:** `subagents.agents.<nome>.model = "inherit"` é a correção de raiz no CLI, mas o
caminho do arquivo de settings **não foi confirmado** (§ 11.4 dos runtime facts) — criar
`~/.copilot/settings.json` não produziu reação observável. Enquanto isso, a detecção acima é a
garantia.

### 3.10 Segunda rodada de feedback (2026-08-04) — 3 recomendações

Apuradas contra 4.369 `tool.execution_complete` de 56 sessões e sondas de `systemTokens`
(`docs/copilot-cli-runtime-facts.md` § 12).

| Recomendação | Veredito | Ação |
|---|---|---|
| "background agents para escritas simples → `edit` direto ou `task` `mode: sync`" | ✅ correta, mas **incompleta** | O modo não é a maior falha: **289 das 345 falhas de `task` (84%) são `Maximum sub-agent depth of 4 reached`**. Viraram `AGENTS.md` § D3 (nunca aninhar delegação) e § D4 (escrita simples é `create`/`edit` direto) |
| "custom instructions ~22K → mover roteamento FastQA" | ✅ **correta, e maior que o estimado** | O índice FastQA sozinho custava **6.815 tokens em toda sessão** (`applyTo: '**'`). Medido que o CLI **honra `applyTo`**: escopar para `fastqa/**` rende o mesmo que remover. Roteamento preservado por 1 linha em `copilot-instructions.md` |
| "`glob` não-confiável no Windows → `Get-ChildItem`" | ❌ **errada e prejudicial** | `glob` falha em **4 de 545 (0%)** e as 4 são path de branch antiga. `powershell` falha em 22 de 1.191 (1%) **e** tem colisão de `shellId`, que `glob` não tem. A troca migraria de 0% para 1%. Virou `AGENTS.md` § C8 |

Uma quarta afirmação do diagnóstico — "os agentes declaram tools BMAD (`memory`,
`sequential-thinking`, `browser`) no frontmatter" — **não procede**: nenhuma spec em
`src/modules/ava-fabric-agents/**` as declara. Elas só existem nos 8 arquivos FastQA de
`.github/instructions/`. O problema das "tools inexistentes" e o do peso das custom instructions são
**o mesmo defeito**, resolvido pelo escopo do `applyTo`. A regra § D5 fica como prevenção de drift.

**Resultado líquido medido**, já incluindo o `AGENTS.md` crescer com as regras novas:
`systemTokens` **23.674 → 16.989**; estático total **42.594 → 35.909** (de 33% para 28% da janela).

O teto do `AGENTS.md` foi redesenhado: passou a medir o **bloco `AGENTS-CORE`** (8 KB — é o que é
replicado nos 102 wrappers e cobrado em toda janela) separado do **arquivo** (10 KB — cabeçalho de
mantenedor, cobrado uma vez no fluxo interativo). Medir só o arquivo confundia os dois custos e
forçava enxugar documentação para caber.

### 3.8 O que esta spec deliberadamente NÃO faz

Migrar as 8 fases de uma vez. F1 é a fase com a falha documentada e serve de padrão de referência;
F2–F8 replicam o molde depois, um `F{N}.yaml` por vez. Os 102 wrappers, porém, são gerados agora —
são script, custam pouco, e nada os consome até existir um DAG que os referencie.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Isolamento real de janela (CA01, P1)

**Story**: Como orquestrador da F1, quero delegar cada análise a um processo próprio para que a
minha janela nunca acumule o AST de 1,5M LOC.

**Given** um projeto cujo AST comprimido soma mais de 700K tokens,
**When** the orchestrator runs `agent_runner.py --project P --phase F1`,
**Then** each node spawns its own `copilot -p --agent <id>` process, and for every node
`session.shutdown.systemTokens ≈ 13.449` with `currentTokens` well below 128.000,
**And** no `session.compaction_start` or `session.truncation` event is emitted for any node.

### Scenario 2 — O modo de execução do usuário não muda (CA02, P1)

**Given** an operator who runs `copilot-cli-headroom.bat` and asks for the F1 orchestrator exactly as
before,
**When** the phase completes,
**Then** `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` reports no change,
**And** the artifacts produced are structurally equivalent to the reference run in
`projects/Meu-ERP/outputs/asis/`.

### Scenario 3 — Todo agente é invocável nativamente (CA03, P1)

**Given** the 102 generated wrappers in `.github/agents/`,
**When** the operator opens `copilot` and picks any agent through `/agent`,
**Then** the agent runs in its own context window,
**And** `copilot --log-level warning` emits **zero** `unknown fields ignored` warnings,
**And** every wrapper body is under 30.000 characters.

### Scenario 4 — Guardrails herdados de uma fonte única (CA04, P1)

**Given** `AGENTS.md` at the repo root,
**When** `generate_agent_wrappers.py` runs,
**Then** every wrapper carries the `AGENTS-CORE` block byte-identical to `AGENTS.md`,
**And** `tests/test_agent_wrappers.py` fails if any wrapper drifts from it,
**And** editing `AGENTS.md` and regenerating propagates the rule to all 102 agents.

### Scenario 5 — `AGENTS.md` serve qualquer linguagem legada (CA05, P1)

**Given** `AGENTS.md` and the generated wrappers,
**When** `validate_language_agnostic.py --report` scans them,
**Then** `AGENTS.md` reports **zero** legacy-technology tokens (`delphi`, `vb6`, `cobol`,
`powerbuilder`, `dotnet`, `java`, `vbnet`, `.pas`) under `--strict`,
**And** the generated wrapper **bodies** report zero as well — the only remaining hits are on the
inherited `description:` line, which comes from the canonical spec this feature does not edit,
**And** a project with `legacy_technology: java` resolves the same rules with no edit to `AGENTS.md`.

### Scenario 6 — Nenhum agente recebe pack maior que a janela (CA06, P1)

**Given** an agent whose `AGENT_ARTIFACT_SLICE` decodes to more tokens than the budget,
**When** `context_pack.build()` runs,
**Then** the pack degrades to query-only, records the decision inside the pack itself, and stays
under the budget,
**And** two consecutive builds with the same input produce byte-identical files.

### Scenario 7 — Leitura de AST cru é negada, não desencorajada (CA07, P1)

**Given** the `preToolUse` hook is registered,
**When** any agent tries `view` on a file under `outputs/asis/ast-raw/` or on any file ≥ 200 KB,
**Then** the call is denied with an actionable `permissionDecisionReason`,
**And** the denial appears as `hook.start` / `hook.end` in `events.jsonl`.

### Scenario 8 — O DAG não vira a quarta fonte divergente (CA08, P1)

**Given** `pipeline-dag/F1.yaml`,
**When** someone changes a node's `slice` without changing `AGENT_ARTIFACT_SLICE`,
**Then** `tests/test_pipeline_dag.py` fails in CI naming both sides of the divergence.

### Scenario 9 — Falha de configuração não é retentada (CA09, P2)

**Given** a node whose process returns `session.error` with `statusCode: 404` and
*"Model not found on provider"*,
**When** the runner classifies the result,
**Then** the status is `config_error`, the phase aborts, and **no** retry is attempted —
because 404 is BYOK misconfiguration, not a transient transport failure.

### Scenario 10 — Artefato ausente é falha, mesmo com `exit 0` (CA10, P1)

**Given** a node that exits 0 but did not write its output contract,
**When** `artifact_gate.py --agent <id> --json` runs after the process,
**Then** the node is classified `failed`, never `completed` —
`artifacts_confirmed` É MEDIDO, NUNCA DECLARADO (`orchestrator-asis.md:184`).

### Scenario 11 — Degradar, nunca quebrar (CA11, P2)

**Given** a project with `execution_backend: inprompt` (the default),
**When** the orchestrator runs,
**Then** the runner refuses to execute and the current in-prompt path runs unchanged,
**And** a project with no `.context/` pack falls back to the classic `## Input Contract`.

---

## 5. Quality Gate Requirements

- [ ] Nenhuma spec canônica em `src/modules/.../agents/*.md` tem o frontmatter alterado, exceto
      `orchestrator-asis.md` (Art. II preservado — ver §9 do plano)
- [ ] `AGENTS.md` passa em `validate_language_agnostic.py --strict` com **0 violações**; os wrappers
      rodam em `--report` (a `description` é herdada da spec canônica — dívida em § 7) (Art. I)
- [ ] Todo wrapper: `name` casa `^ava-[a-z0-9-]+$`, corpo < 30.000 chars, zero `unknown fields
      ignored` (Art. II)
- [ ] `orchestrator-asis.md` recebe bump **MAJOR** (contrato de dispatch muda) (Art. X)
- [ ] F1 continua produzindo o security sub-pipeline; `ava-asis-security-orchestrator` não é
      contornado (Art. VII)
- [ ] `trace_id` propagado sem mutação do `project-config.yaml` → envelope → pack → artefato (Art. VIII)
- [ ] `AGENTS.md`, corpos de wrapper e docstrings em pt-BR (Art. V)
- [ ] Ordem de fases preservada: o runner é intra-fase; F1→ava-summary→F2 não muda (Art. III)
- [ ] Nenhum agente novo → sem diff de `module.yaml` (Art. IV) e sem `SKILL.md` novo (Art. XI)
- [ ] 11 cenários BDD cobrindo nominal, edge e gate
- [ ] CI atualizado: `validate-agent-observability.yml` coleta os testes novos
- [ ] Nenhum marcador `[NEEDS CLARIFICATION]` remanescente

---

## 6. Dependencies

- **`docs/copilot-cli-runtime-facts.md` (M0)** — **autoridade** dos números de runtime. Toda decisão
  de flag e de orçamento cita uma linha dele. Copilot CLI ≥ 1.0.77.
- **`src/shared/tools/agent_registry.py`** — fonte canônica dos agentes (107 arquivos, 102 despacháveis). O gerador de wrappers
  depende de `catalog()` e do frontmatter continuar sendo a autoridade da versão.
- **`artifact_gate.ARTIFACT_CONTRACTS` / `context_budget.AGENT_ARTIFACT_SLICE`** — o DAG importa
  delas; `test_pipeline_dag.py` garante a equivalência.
- **`headroom_context.read_artifact_payload()` / `build_agent_context()`** — único decoder do formato
  SmartCrusher no repo; base do context pack.
- **`headroom_tool.py slice|decode`** — camada de consulta citada pelo hook e pela seção 3 do pack.
- **`.specify/memory/constitution.md` § Project Reference** — mapa Fase→Módulo usado pelo registry.
- **Rota BYOK direta.** O M0 registrou 87 erros 404 em 25 sessões, **71 apontando para o proxy
  Headroom** (`127.0.0.1:8787`), contra 6 no endpoint direto; as 6 sondas do M0 foram diretas e todas
  deram `exit 0`. O runner opera **na rota direta**; rodar comprimido exige antes o shim local de
  `/v1/models/{id}` (Anexo A de `src/shared/tools/headroom/docs/02-esteira-github-cli.md`).

---

## 7. Exclusions

- **F2–F8** — só F1 é validada aqui. Os wrappers dos 102 são gerados, mas apenas `F1.yaml` existe.
  Um `F{N}.yaml` por vez, começando por F5 (follow-on).
- **Knowledge graph / `ast_index.py` / FTS5 / write-back F2** — spec **034**
  (`docs/plan/memory-archotecture-middleware-knowledge-graph.md`). Esta spec entrega o context pack
  determinístico; o grafo pluga depois **sem mudar os agentes**.
- **`master-orchestrator.md`** — não está em uso; o ponto de entrada real são os orquestradores de
  fase. Fica intacto e fora do plano.
- **Limpeza language-agnostic do repo** — mapeada, não corrigida aqui. Inclui as 9 `description:`
  de wrapper que herdam tecnologia da spec canônica (`ava-qa-behavior-mapping` cita Delphi,
  `ava-tobe-designer-system` e `ava-qa-frontend-test-generator` citam Angular,
  `ava-tobe-spec`/`ava-devops-ci` citam .NET, `ava-qa-db-integrity-test` cita EF Core,
  `ava-asis-security-sast` cita Delphi/VB6/COBOL) — corrigi-las é mudança de conteúdo do agente.
  E também:
  `orchestrator-asis.md:2075 ## Delphi Backup Cleanup (MANDATORY when legacy_technology == delphi)` ·
  `asis-diagnostic/shared/delphi-patterns.md` · `shared/backend-context-protocol.md` (nome genérico,
  conteúdo .NET) · `shared/mermaid-guardrails.md` (32.982 chars, 5 menções a Delphi) ·
  `.github/instructions/` (253 KB, 100% FastQA) · 46 `.md` sob `src/modules` mencionando delphi.
  Requer branch separada por tocar `.specify/memory/constitution.md`.
- **Perfis `languages/*.yaml` e `stacks/*.yaml`** — workstream paralelo (Escopo 4 do plano de escala).
- **Remoção em massa dos ~206 blocos `pipeline_observer track`** — só a idempotência e a regra
  "agente migrado pode omitir" entram aqui; a remoção é por agente, em follow-on.
- **MCP retrieval server (embeddings/BM25) como tool por-agente** — camada opcional prevista para
  escala extrema (1,5M+ LOC), fora do escopo desta referência.
- **`--context long_context`** — a flag é aceita e registra `contextTier`, mas nenhuma sessão
  long_context chegou a compactar, então o `tokenLimit` desse tier é **desconhecido**. Não usar até
  medir.

---

## 8. Assumptions

- **O corpo do `.agent.md` é o veículo confiável para os guardrails.** O M0 provou que `tools:` é
  enforçado; o corpo é system prompt. Se uma medição futura mostrar que o `AGENTS.md` carrega mesmo
  com `--no-custom-instructions`, a injeção vira redundante e pode ser removida sem mudar nada mais.
- **~106.551 tokens úteis por processo** = 128.000 − 13.449 estáticos − ~8.000 de reserva de saída.
  Se o CLI mudar o system prompt, o número muda; por isso ele é constante nomeada
  (`agent_runner.USABLE_CONTEXT`), não literal espalhado.
- **`exit 0` não prova sucesso.** O artefato é a autoridade — política já vigente, não nova.
- **`taskkill /PID <pid> /T /F`** é obrigatório no Windows; `Popen.terminate()` deixa o processo node
  filho órfão.
- **O `agent_registry` cobre 100% dos agentes despacháveis.** As 4 sub-skills de
  `db-analyzer/skills/*.md` são excluídas por `_is_dispatchable` — não têm identidade de execução e
  não recebem wrapper.
- **`~/.copilot/agents/` não existe nesta máquina hoje** (R7 é nulo agora), mas o diretório pode ser
  criado a qualquer momento e tem precedência — por isso o preflight falha em colisão mesmo assim.
- **`max_parallel` alinhado ao `compression_max_workers`** do Headroom: um proxy único atendendo N
  processos paralelos é um gargalo real.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Isolamento de contexto | Por nó: `systemTokens ≈ 13.449`, `currentTokens ≪ 128.000`, **zero** `session.compaction_start` / `session.truncation` num run F1 completo |
| Não-degradação em escala | F1 real em `MeuERP-002` fecha o `F1_OUTPUT_CONTRACT` — 12/12 paths obrigatórios, 19/19 artefatos (era 11/19 na ISSUE-002) |
| Cobertura de wrappers | **102 de 102** agentes despacháveis invocáveis por `--agent` e por `/agent` (era 1); os 32 sem `SKILL.md` deixam de depender de dispatch textual |
| Formato correto | **zero** `unknown fields ignored` em `--log-level warning`; **zero** corpo ≥ 30.000 chars |
| Herança de guardrails | Bloco `AGENTS-CORE` byte-idêntico em 102 wrappers; teste reprova no primeiro drift |
| Language-agnostic | `validate_language_agnostic.py --strict --paths AGENTS.md` → **0 violações**. Nos wrappers, `--report`: as ocorrências restantes são todas na linha `description:`, herdada da spec canônica, e estão listadas em § 7 como follow-on |
| Orçamento respeitado | Nenhum context pack acima do budget; degradação para query-only sempre registrada, nunca silenciosa |
| Determinismo | Dois `context_pack` consecutivos → bytes idênticos |
| Enforcement | `view` em `ast-raw/` **negado** pelo hook, com `hook.start`/`hook.end` no `events.jsonl` |
| Anti-divergência | `test_pipeline_dag.py` reprova se `F1.yaml` divergir de `ARTIFACT_CONTRACTS`, `AGENT_ARTIFACT_SLICE` ou `agent_registry.catalog()` |
| Modo de execução preservado | `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` sem saída |
| Rollback | `execution_backend: inprompt` restaura o caminho atual bit a bit |
