# Agent Specification: AS-IS Pipeline Context Budget + Dispatch Guard

**Feature Branch**: `030-asis-pipeline-context-budget-dispatch-guard`
**Created**: 2026-07-29
**Status**: Implemented
**Change Type**: modify-existing (2 agent files, MINOR each — nenhum campo de Output Contract removido)
+ add-new (2 utilitários determinísticos + 1 guia)
**Input**: `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md` — "Implemente a solução e documente via speckit"

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-asis-orchestrator` | `agents/orchestrator-asis.md` | `2.21.1` → `2.22.0` (MINOR) |
| `ava-asis-solution-delphi` | `agents/solution-delphi.md` | `2.6.0` → `2.7.0` (MINOR) |

**Phase**: F1. **Module**: `asis-diagnostic`.

Novos utilitários (não são agentes — não têm frontmatter, seguindo o precedente de
`module_partitioner.py` / `sql_ir_generator.py`):

| Utilitário | Papel |
|---|---|
| `utils/context_budget.py` | Mede o payload comprimido e resolve `execution_mode` + fatia de artefatos por agente |
| `utils/artifact_gate.py` | Verifica se os artefatos obrigatórios de um agente já existem — guard pré-dispatch e relatório de completude F1 |

## 2. Problem Statement

Na execução F1 de `processaERP-008` (363 units, 174.375 LOC, 4.254 regras de negócio) a esteira
rodou **110,6 minutos** e encerrou com **8 dos 19 artefatos F1 ausentes**. A extração AST em si
foi normal (4m 14s); o tempo foi consumido por três chamadas de subagente de 2.062s, 319s e
**3.700s**, separadas por três gaps de silêncio de 30–35 minutos cada.

A ISSUE-002 identificou quatro causas:

- **RC-1 (primária) — sobrecarga de contexto.** O payload comprimido do projeto é de
  **761.376 tokens**. Cada `runSubagent` carregava esse payload inteiro + spec do agente +
  resultados de tool, ultrapassando 800K tokens por turno. Cada restart de subagente
  reconstruía o mesmo contexto sem ganho de conhecimento.
- **RC-2 — retry sem guard.** Três `runSubagent` para o mesmo agente em 16 segundos
  (20:26:21 → 20:26:37 → 20:27:09): as duas primeiras chamadas retornaram cedo, o orquestrador
  não detectou e redespachou imediatamente, triplicando o custo.
- **RC-3 — sem paralelismo real.** Agentes sem dependência mútua foram despachados em série.
- **RC-4 — perda de continuação.** Ao retornar da chamada de 62 minutos, a sessão pai não
  retomou a escrita dos artefatos restantes, e nada reaproveitou os 11 já produzidos.

O orquestrador só tinha verificação de artefatos **depois** da conclusão de um agente
(`verify_artifacts()`). Não havia nenhuma medida de volume antes do dispatch, nenhuma noção de
"quanto contexto este agente precisa", e nenhuma forma barata de retomar uma esteira parcial.

## 3. Decision

### 3.1 Context Budget Gate (M-1 / M-2 / M-3) — orquestrador MINOR

Nova seção `### Context Budget Gate` em `orchestrator-asis.md`, avaliada **uma vez**, logo após
`evaluate_solution_gate()` retornar `OPEN` e **antes** do primeiro dispatch da Wave 2 — o
momento mais cedo possível, já que o `manifest.json` só existe depois do Step 0 do agente de
solução.

`evaluate_context_budget()` invoca `context_budget.py --json` (1 `Bash`, sem custo de LLM) e
registra no contexto de execução, **por agente**:

- `ast_artifact_slice[]` — só os `compressed/*.json` que aquele agente consome (**M-1**),
  derivado dos `## Input Contract` reais de cada agente (specs/010);
- `execution_mode` — `subagent` (≤400K) · `inline` (>400K, **M-2**) · `bc_scoped` (>700K,
  **M-3**: 1 dispatch por bounded context via `module-partition.json`).

Os limiares vêm de `project-config.yaml` (`context_budget_inline_threshold`,
`context_budget_bc_scoped_threshold`), com defaults 400K/700K — nunca hardcoded no agente.

Nova **Regra Fundamental 10**: despachar um agente da Wave 2 sem `ast_artifact_slice` definido é
violação de contrato. O prompt de dispatch nunca instrui um agente a "ler todos os artefatos
comprimidos".

### 3.2 Dispatch Guard (M-4) — orquestrador MINOR

Nova seção `### Dispatch Guard — Artifact Existence Precheck`, com três guards em
`should_dispatch(agent_id, project_name)`:

1. **Anti-storm** — `dispatched_in_current_iteration` (resetado a cada iteração do Streaming
   COLLECT Protocol) proíbe dois dispatches do mesmo agente na mesma iteração. É o guard que
   quebra exatamente a rajada de 3 chamadas em 16s do RC-2.
2. **Teto de tentativas** — `dispatch_attempts >= 4` → `on_retries_exhausted()`.
3. **Artefatos presentes** — `artifact_gate.py --agent {id} --json`; se completo, o agente é
   promovido a `completed` + `artifacts_confirmed: true` + `dispatch_skipped_reason:
   "artifacts_present"` **sem gastar subagente**, e os eventos de DAG dependentes disparam
   normalmente.

Nova **Regra Fundamental 11**: o guard é chamado antes de **todo** dispatch — Wave 1, Wave 2,
Phase B/C, retries da `retry_queue`, `dispatch_bridge_fastqa()`, `remediate_pending_agents()` e
o DISPATCH AUDIT do COLLECT loop. Quando `dispatch: true`, o prompt carrega `artifacts_missing[]`
e o agente regenera **apenas o que falta**.

`retry_config` ganha `dispatch_guard: mandatory`, `max_dispatch_per_iteration: 1` e
`retry_scope: missing_artifacts_only`.

### 3.3 Resume Detection (RC-4) — orquestrador MINOR

Novo **Step 0.3** no `## Reasoning Approach`, executado em todos os triggers **exceto**
`SA|FULL` (onde o usuário pediu explicitamente reset): roda `artifact_gate.py --all --json`,
pré-registra como `completed` tudo que já está em disco e exibe
`📦 Contrato F1: {N}/{total} artefatos ({pct}%)` com a lista do que falta.

Consequência prática: uma esteira interrompida é retomada disparando o trigger normal — a
esteira despacha apenas os agentes pendentes em vez de repetir horas de inferência já pagas.

### 3.4 Step 0.6 no agente de solução (RC-1 / RC-4) — solution-delphi MINOR

O agente de solução é o único que legitimamente cobre os 9 artefatos (761.376 tokens em
`processaERP-008` — 100% do payload), então **slicing não se aplica a ele**. A mitigação é outra:

- **Step 0.6 — Context Budget & Resume Check** roda `context_budget.py --agent
  ava-asis-solution-delphi` e escolhe a estratégia: fluxo normal (`subagent`), **escrita
  incremental obrigatória** por artefato (`inline`), ou processamento **um bounded context por
  vez** (`bc_scoped`).
- **Resume por artefato (idempotência)**: antes de (re)gerar qualquer artefato do Output
  Contract, verificar se ele já existe com tamanho > 0 → pular. Se o orquestrador enviou
  `artifacts_missing[]`, gerar exclusivamente esses.

O LARGE ARTIFACT PROTOCOL do Step 0 (extração seletiva via `Bash`, nunca `Read` raw em artefatos
≥ 200KB) continua valendo em qualquer modo — o Context Budget não o substitui.

### 3.5 M-5 (paralelismo) — reforço documental, sem mudança estrutural

A `phase_a_wave2` já era `mode: on_event` com dispatch dos 5 agentes em sequência de dispatch. O
RC-3 foi violação da Regra Fundamental 3, não ausência de mecanismo. A correção é uma nota
explícita no `dispatch_schedule` nomeando a serialização como violação, mais o
`dispatch_guard: mandatory` na wave.

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Projeto grande: modo degradado escolhido antes do gasto (CA01)

**Given** um projeto cujo `compressed/manifest.json` soma 761.376 tokens, **When** o Solution
Agent Gate abre e o orquestrador avalia `evaluate_context_budget()`, **Then** o bloco
`🧮 CONTEXT BUDGET` é exibido com `execution_mode: bc_scoped`, e cada agente da Wave 2 é
despachado com sua fatia (`db-analyzer`: 559.144 tokens → `inline`; `inventory`: 72.434 →
`subagent`; `events-pubsub`: 417 → `subagent`) em vez do payload completo.

### Scenario 2 — Projeto pequeno: comportamento inalterado (CA02)

**Given** um projeto cujo payload comprimido soma menos de 400K tokens, **When** o gate roda,
**Then** `execution_mode: subagent` para todos os agentes e a esteira se comporta exatamente
como na v2.21 — o único efeito visível é o bloco informativo de budget.

### Scenario 3 — Retry storm bloqueado (CA03)

**Given** um agente que já foi despachado na iteração corrente do COLLECT loop, **When** uma
condição dispara um segundo dispatch do mesmo `agent_id` na mesma iteração, **Then**
`should_dispatch()` retorna `{dispatch: false, reason: "already_dispatched_this_iteration"}`,
loga `DISPATCH_STORM_BLOCKED` e nenhum subagente é gasto.

### Scenario 4 — Artefatos já presentes: dispatch pulado (CA04)

**Given** `processaERP-008` com `inventory-report.md`, `metrics.json`, `complexity-map.md` e
`.internal/form-registry.json` já em disco, **When** o guard avalia `ava-asis-inventory`,
**Then** retorna `{dispatch: false, reason: "artifacts_present"}`, o agente entra no registry
como `completed` + `artifacts_confirmed: true`, e os eventos de DAG dependentes disparam
normalmente.

### Scenario 5 — Retomada de esteira interrompida (CA05)

**Given** `processaERP-008` com 3/12 artefatos do contrato F1 em disco, **When** o usuário
dispara `SA` (não `SA|FULL`), **Then** o Step 0.3 exibe `📦 Contrato F1: 3/12 artefatos
(25.0%)` com a lista das 9 ausências, pré-registra `solution-delphi`, `inventory` e
`events-pubsub` como `completed`, e a esteira despacha apenas os agentes pendentes.

### Scenario 6 — Step 0 (AST) não rodou: degrada e continua (CA06)

**Given** um projeto sem `compressed/manifest.json`, **When** `evaluate_context_budget()` roda,
**Then** o utilitário sai com código 3, o orquestrador loga `CONTEXT_BUDGET_UNAVAILABLE`, assume
`execution_mode: subagent` e prossegue — o gate **nunca** interrompe a esteira (mesma filosofia
"degrada e continua" de specs/011/012; `HALT` continua reservado a STUB e retries esgotados).

### Scenario 7 — Falha do guard não impede entrega (CA07)

**Given** `artifact_gate.py` falhando (exit 2 ou erro de execução), **When**
`should_dispatch()` é chamado, **Then** assume `{dispatch: true}` e loga aviso — o guard pode
evitar trabalho redundante, nunca impedir uma entrega.

## 5. Quality Gate Requirements

- [x] Agent IDs inalterados; frontmatter alterado apenas em `version` e `description` (Art. II)
- [x] Version bumps MINOR nos dois agentes — apenas adições, nenhum contrato removido (Art. X)
- [x] Nenhum limiar hardcoded — `context_budget_*_threshold` resolvidos do `project-config.yaml` com defaults (Art. I)
- [x] Corpo dos agentes e logs/docstrings dos utilitários em pt-BR (Art. V)
- [x] Cenários BDD cobrem caminho feliz, projeto pequeno, retry storm, skip por artefato, resume, AST ausente e falha do guard (Art. VI)
- [x] Consistência de versão: frontmatter == literal `--version` da FASE OBRIGATÓRIA == catálogo de `pipeline_observer.py` / `generate_observability_report.py`, por agente
- [x] Nenhum marcador `[NEEDS CLARIFICATION]` remanescente

## 6. Dependencies

- `utils/run_ast_analysis.py` — inalterado; continua sendo o produtor de
  `compressed/manifest.json` e `metrics.jsonl`, a única fonte de tokens do Context Budget.
- `utils/module_partitioner.py` — inalterado; `module-partition.json` é o insumo do modo
  `bc_scoped` (M-3).
- `§ Artifact Output Contract per Agent` do `orchestrator-asis.md` — a tabela agora tem um
  espelho executável (`ARTIFACT_CONTRACTS` em `artifact_gate.py`); alterar um lado exige
  alterar o outro.
- `pyyaml` — já dependência do módulo (usado por `module_partitioner.py`).

## 7. Exclusions

- **Reexecução do `processaERP-008`** (ISSUE-002 §6 ação 1) — ação operacional, não de código.
  Fica **habilitada** pelo Step 0.3 + Dispatch Guard, mas exige uma execução real da esteira
  (na ordem de dezenas de minutos) e não foi disparada nesta entrega.
- **M-3 dentro do agente de solução** — o `bc_scoped` está especificado no Step 0.6 como
  estratégia obrigatória, mas o loop por bounded context nos Steps 3-13 não foi decomposto em
  sub-steps numerados. O agente recebe a instrução e o `module-partition.json`; a decomposição
  fina fica para um PBI seguinte, quando houver uma execução `bc_scoped` real para calibrar.
- **`solution-{vb,cobol,vbnet,powerbuilder}.md`** — o Step 0.6 foi adicionado apenas ao
  `solution-delphi.md`, o único com extração AST real. Os demais herdam a fatia em
  `AGENT_ARTIFACT_SLICE` (para quando ganharem AST) mas não têm o step.
- **7 sub-agentes de segurança + `security-orchestrator`** — domínio próprio, não consomem
  artefatos AST; fatia 0 e nenhuma mudança de comportamento.
- **Globs de `fastqa/manual_test/`** no contrato do `bridge-fastqa` — marcados `advisory` no
  `artifact_gate.py`: aquele diretório é global do workspace (não é por projeto), então um PBI
  de outro projeto produziria um falso "presente" e faria o guard pular um dispatch necessário.
  A decisão de completude fica com os paths project-scoped (`qa/*`).

## 8. Assumptions

- `manifest.json.artifacts[].tokens_out` é a melhor estimativa disponível do custo de contexto
  por artefato — é o mesmo número que o motor `headroom` grava em `metrics.jsonl`, e o único
  disponível sem tokenizar o conteúdo novamente.
- Os limiares 400K/700K vêm da observação empírica da ISSUE-002 (761K → 62 min por chamada) e
  do `perf_pipeline_ntp.py`, que já usava exatamente esses valores como WARNING/CRITICAL. Não
  foram calibrados contra uma bateria de projetos — por isso são configuráveis por projeto.
- Existência de arquivo com tamanho > 0 é proxy suficiente para "artefato entregue". O
  `bridge-fastqa` é a exceção conhecida (`qa/test-plan.md` exige ≥ 3.000 bytes, para rejeitar
  placeholder), e o mesmo limiar já era usado pelo `verify_artifacts()`.
- `fastqa/manual_test/` é global do workspace — assumido a partir da estrutura de paths do
  contrato existente (`external_mandatory.base`), não de uma verificação de isolamento por
  projeto.

## Success Criteria

| Criterion | Measure |
|---|---|
| Budget medido antes do gasto | `context_budget.py --project processaERP-008` → `total_tokens: 761376`, `execution_mode: bc_scoped`, exit 2 |
| Slicing reduz contexto por agente | Nenhum agente da Wave 2 recebe 100% do payload: maior fatia = `db-analyzer` 73,4%; menor = `events-pubsub` 0,1% |
| Guard detecta o que já existe | `artifact_gate.py --project processaERP-008 --all` → `solution-delphi`/`inventory`/`events-pubsub` = SKIP; demais = DISPATCH; exit 1 |
| Contrato F1 auditável | Mesma execução reporta `📦 Contrato F1: 3/12 (25.0%)` com as 9 ausências nomeadas |
| Guard nunca bloqueia entrega | Erro do `artifact_gate.py` → `{dispatch: true}`; `manifest.json` ausente → `execution_mode: subagent` |
| Anti retry storm documentado como invariante | Regra Fundamental 11 + `max_dispatch_per_iteration: 1` no `retry_config` |
| Consistência de versão | `grep '"2.22.0"'` casa em `orchestrator-asis.md` (frontmatter + `--version`) e nos 2 catálogos de observabilidade; idem `2.7.0` para `solution-delphi` |
| Padrão documentado | `docs/guia-repositorios-legados-grandes.md` cobre sintoma, causa, checklist de pré-execução, tuning e procedimento de retomada |
