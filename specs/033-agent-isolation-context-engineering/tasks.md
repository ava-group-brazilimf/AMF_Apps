# Agent Development Tasks: Isolamento de Janela por Agente + Context Engineering

**Plan**: `specs/033-agent-isolation-context-engineering/plan.md`
**Agent ID**: — (nenhum agente novo) | **Phase**: `F1` (referência) | **Module**: `asis-diagnostic` + `src/shared/tools`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Marcos: **M1** = Cat. 1 · **M2** = Cat. 2 · **M3** = Cat. 3 · **M4** = Cat. 4–6 · **M5** = Cat. 7.

---

## Category 1 — Fundação: `AGENTS.md` + wrappers gerados (M1)

Bloqueia todas as demais categorias.

- [ ] **1.1** Criar `AGENTS.md` na raiz do repo, **≤ 8 KB**, em pt-BR, com as seções:
  identidade e escopo da esteira (F1–F8, orquestrador × agente) · **Output Integrity Rules**
  destiladas de `.github/copilot-instructions.md` L255–310 · **protocolo de retrieval**
  (pack primeiro; ingestão exaustiva proibida; consulta dirigida por símbolo/padrão; nunca `cat` de
  arquivo grande) · **orçamento de contexto** (~106.551 úteis; degradar e **registrar**, nunca
  truncar em silêncio) · **protocolo de handoff por extract** · **protocolo do `shared-context.md`**
  (índice, não depósito; passar paths, nunca conteúdo) · **batch write** numa única chamada
  `powershell` · guardrails comuns (read-only no legado, mascarar credenciais, `trace_id` sem mutar,
  `ast-raw/` negado pelo hook) · convenções de path · **resolução de linguagem** via
  `legacy_technology` do `project-config.yaml`
- [ ] **1.2** Envolver o conteúdo herdável em delimitadores exatos
  `<!-- AGENTS-CORE:START -->` / `<!-- AGENTS-CORE:END -->` (o gerador copia **só** esse trecho)
- [ ] **1.3** Verificar `AGENTS.md` language-agnostic: **nenhuma** menção a delphi, vb6, vbnet,
  cobol, powerbuilder, dotnet/.NET, java, angular ou versão de framework
- [ ] **1.4** Criar `src/shared/tools/generate_agent_wrappers.py`, alimentado por
  `agent_registry.catalog()` — nunca por lista manual:
  - mover `TOOL_NAME_MAP` de `agent_runner.py:81` (hoje sem uso) para cá;
    `Read→view · Write→create · Edit→edit · Glob→glob · Grep→grep · Bash→powershell ·
    WebFetch→web_fetch · WebSearch→web_search`
  - emitir `tools:` (**nunca** `allowed-tools:`) e **não** emitir `version:` — vai em
    `metadata.version`, derivada do frontmatter canônico
  - emitir `name`, `description` (do registry, pt-BR), `model: claude-sonnet-4`,
    `target: github-copilot`, `user-invocable: true`, `metadata: {version, phase, module}`
  - corpo: cabeçalho `GERADO — não editar à mão` + bloco `AGENTS-CORE` injetado + ponteiro
    `Read src/modules/.../agents/{role}.md` + estratégia de contexto (slice do
    `AGENT_ARTIFACT_SLICE` + output contract do `ARTIFACT_CONTRACTS`)
  - **hard fail** se o corpo resultante ≥ 30.000 chars
- [ ] **1.5** [P] Implementar `--check` (exit 1 se algum wrapper em disco divergir do que o gerador
  produziria) e `--phase F{N}` (geração parcial)
- [ ] **1.6** [P] Preflight: falhar se `~/.copilot/agents/` contiver arquivo de nome colidente com
  `.github/agents/` — o diretório do usuário tem precedência e quebra a reprodutibilidade
- [ ] **1.7** Gerar os **102** wrappers em `.github/agents/` (107 arquivos de spec menos 4
  sub-skills de `db-analyzer/skills/` e 1 agente depreciado), substituindo o
  `ava-asis-inventory.agent.md` escrito à mão pelo equivalente gerado
- [ ] **1.8** Criar `src/shared/utils/validate_language_agnostic.py` — **allowlist**, não denylist
  (`shared/dotnet-research-instructions.md` legitimamente contém `dotnet`); modos `--report`
  (mede a dívida sem quebrar o build) e `--strict` (CI); alvos desta spec: `AGENTS.md` e
  `.github/agents/`
- [ ] **1.9** Criar `tests/tools/test_agent_wrappers.py` (nesse diretório de propósito: o CHK-04 do
  `validate-agent-observability.yml` já coleta `tests/tools`, então o gate vale sem tocar no CI):
  102/102 presentes · nenhum órfão · `name` casa
  `^ava-[a-z0-9-]+$` · `tools` presente e só com nomes reais do CLI · `version` e `allowed-tools`
  **ausentes** do frontmatter · corpo < 30.000 chars · bloco `AGENTS-CORE` **byte-idêntico** ao de
  `AGENTS.md` · `metadata.version` igual ao frontmatter canônico
- [ ] **1.10** [P] Cap hard ≤ 30.000 chars coberto no mesmo arquivo de teste, e **hard fail** no
  gerador — o wrapper nunca é truncado para caber
- [ ] **1.11** [P] Criar `tests/utils/test_validate_language_agnostic.py`: `AGENTS.md` limpo em
  `--strict`; corpo gerado dos wrappers neutro; placeholder de runtime (`{language}`) não é violação

---

## Category 2 — Context pack + enforcement (M2)

Depende da Category 1.

- [ ] **2.1** Criar `src/shared/tools/context_pack.py` reusando
  `headroom_context.build_agent_context(project, agent_id, language)` — **não** reimplementar o
  decoder SmartCrusher
- [ ] **2.2** Emitir `projects/{project_name}/outputs/.context/{agent_id}/context-pack.md` com as
  5 seções do contrato: (1) fatia AST decodificada · (2) índice de artefatos upstream — paths,
  seções e tamanho, **nunca conteúdo** · (3) como consultar o que não está no pack
  (`headroom_tool.py slice|decode`) · (4) output contract do `artifact_gate` com o que falta ·
  (5) extrato curado do `shared-context.md`
- [ ] **2.3** **Gate de orçamento**: se a fatia decodificada excede o budget, degradar para
  *query-only* (seção 1 vira contagens + instruções) e **registrar a decisão dentro do pack**.
  Nenhum pack pode sair maior que o orçamento — hoje o runner só imprime `⚠`
- [ ] **2.4** Garantir determinismo: ordenação por chave, nenhum `set()` iterado sem `sorted()`,
  nenhum timestamp no corpo do pack. Dois builds seguidos → bytes idênticos
- [ ] **2.5** [P] CLI: `--project`, `--agent`, `--phase`, `--json`; exit 0 OK / 1 degradado / 2 erro
  de uso (mesma convenção de `headroom_tool.py`)
- [ ] **2.6** Criar `src/modules/ava-fabric-agents/shared/context-pack-protocol.md` — o que é um
  pack, como lê-lo, precedência (**pack presente → autoridade; ausente → `## Input Contract`
  clássico**), e a proibição de reler `repository_path` (preserva o
  `artifact-only-consumption-protocol`)
- [ ] **2.7** Criar `src/shared/tools/hooks/pretooluse_guard.py` + `.github/hooks/ava-guardrails.json`:
  negar leitura sob `outputs/asis/ast-raw/` ou de arquivo ≥ 200 KB, devolvendo
  `{"permissionDecision":"deny","permissionDecisionReason":"Artefato AST fora do context pack. Use: python src/shared/tools/headroom/headroom_tool.py slice -p <proj> --artifact <n>"}`
- [ ] **2.8** [P] Testes: pack acima do budget degrada e registra · dois builds byte-idênticos ·
  agente desconhecido (fatia `None`) → pack vazio com `known_agent: false`, sem exceção
- [ ] **2.9** Ligar o pack ao runner: `agent_runner.build_envelope()` (`agent_runner.py:238`) passa a
  apontar para o pack em vez de listar caminhos de `compressed/*.json`

---

## Category 3 — DAG completo + runner (M3)

Depende da Category 2.

- [ ] **3.1** Expandir `src/shared/data/pipeline-dag/F1.yaml` de 3 nós (wave2) para o DAG F1
  completo, extraído de `orchestrator-asis.md` §§ `## Agent Team` (L74),
  `## Execution DAG` (L99), `dispatch_schedule` (L165+) e `Artifact Output Contract per Agent` (L839)
- [ ] **3.2** Criar `tests/tools/test_pipeline_dag.py` — **mitigação obrigatória do risco R1**:
  aciclicidade · `dag.nodes ≡ artifact_gate.ARTIFACT_CONTRACTS.keys() ≡ agent_registry.catalog()` ·
  **`dag[n].slice ≡ context_budget.AGENT_ARTIFACT_SLICE[n]`** (comparação de **conteúdo**; o
  `validate_dag()` atual só checa presença) · todo nó tem `slice`, `timeout_s` e artefatos
- [ ] **3.3** `agent_runner.py`: honrar `max_parallel` do DAG (hoje é lido e ignorado; o laço é
  estritamente sequencial), alinhado ao `compression_max_workers` do Headroom
- [ ] **3.4** `agent_runner.py`: implementar a **escada de retry**
  (hoje `max_attempts: 1`, sem laço nenhum):
  | Tentativa | Mudança |
  |---|---|
  | 1 | baseline |
  | 2 | novo `--session-id`; prompt ganha bloco de reparo: `artifacts_missing` do gate + `session.error.message` + os 3 últimos `tool.execution_complete` com `success:false` |
  | 3 | degradar: pack reduzido à fatia obrigatória; se houve `context_overflow`, recortar por bounded context de `module-partition.json` |
  | 4 | só agentes `solution-*` (alinhado ao "max 4x" do `retry-protocol.md`) |
- [ ] **3.5** Backoff 30 s → 120 s **apenas** para `statusCode` ∈ {429, 5xx}. **Nunca** para 404
  (é configuração BYOK → `config_error`, aborta a fase). **Nunca** para artefato-ausente (é problema
  de prompt, não de transporte). `artifact_gate` roda antes de cada tentativa (anti-retry-storm)
- [ ] **3.6** [P] `agent_runner.py`: ler `execution_backend: inprompt | process` do
  `project-config.yaml` e **recusar rodar** se `inprompt` (default)
- [ ] **3.7** [P] `agent_runner.py`: usar `BENIGN_LOG_PATTERNS` (já definido, sem referência) para
  filtrar os 3 ruídos benignos do M0 § 1.9 e não gerar falso positivo de falha
- [ ] **3.8** [P] Recalibrar `context_budget.py`: documentar que 400K/700K são heurística de **total
  de pipeline**, não orçamento por agente; o valor por processo é
  `agent_runner.USABLE_CONTEXT = 106.551`
- [ ] **3.9** [P] Testes com `events.jsonl` sintético: 404 → `config_error` sem retry ·
  `exit 0` sem artefato → `failed` · `execution_backend: inprompt` → runner recusa

---

## Category 4 — Encolher o orquestrador de fase (M4)

Depende da Category 3.

- [ ] **4.1** Reescrever `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`:
  **193.848 → ~15 KB**, mantendo só: resolução de `project-config.yaml` / `legacy_technology` /
  `scope_modules` / `trace_id` · Step 0 (AST via `run_ast_analysis.py`) · Solution Agent Gate
  (regra 9 — HALT total em falha ou `implementation_status == STUB`) · **uma** chamada
  `powershell: python src/shared/tools/agent_runner.py --project {p} --phase F1` · leitura do
  relatório do runner, gates de fase, consolidação de `master-report.md` + Summary
- [ ] **4.2** Remover do prompt (passam a viver em `F1.yaml`): `## Execution DAG` (L99) ·
  `## DAG Event Protocol` (L165, as 14 regras + `dispatch_schedule`) · tabela
  `Artifact Output Contract per Agent` (L839) · tabela `SOLUTION_AGENTS` duplicada como comentário
  YAML (passa a vir do `agent_registry`)
- [ ] **4.3** Confirmar que as regras 10/11/13/14 (Context Budget Gate · Dispatch Guard ·
  `artifacts_confirmed` **medido, nunca declarado** · Wave Guard) estão cobertas por código no
  runner antes de sair do prompt — nenhuma regra pode desaparecer sem substituto executável
- [ ] **4.4** Bump **MAJOR** em `orchestrator-asis.md` (o contrato de dispatch muda) — Art. X
- [ ] **4.5** [P] Regenerar o wrapper do orquestrador e confirmar corpo < 30.000 chars

---

## Category 5 — Correções de bug no caminho tocado (M4)

- [ ] **5.1** `projects/MeuERP-002/context/project-config.yaml:9` — linha **malformada**:
  `scope_modules` foi engolido pelo comentário de `trace_id`, então a chave **não existe** e o filtro
  de escopo está inativo. Corrigir e acrescentar `execution_backend: process`
- [ ] **5.2** `quality_gates:` **declarado duas vezes** — `MeuERP-002` (L226 e L332) e
  `projects/_template` (L330 e L599). Em YAML o segundo vence; o primeiro bloco é descartado em
  silêncio. Fundir e deixar uma declaração só
- [ ] **5.3** `run_ast_analysis.py::_ensure_manifest_metrics` grava `tokens_out = len(text)`
  (caracteres) sob `files[]`, enquanto `context_budget.py` lê `artifacts[].tokens_out` — manifesto
  sintetizado faz o budget gate ler 0 tokens e liberar tudo como `subagent`
- [ ] **5.4** [P] Documentar `execution_backend` em
  `projects/_template/context/.project-config-exemple-.yaml` (ausência ≡ `inprompt` ≡ esteira atual)

---

## Category 6 — Observabilidade e validação de aceite (M4)

Depende da Category 4. **Resolve uma contradição viva**: `verify_agent_observability.py` exige os
blocos `track` à mão, enquanto o wrapper e o envelope mandam o agente **não** executá-los.

- [ ] **6.1** Tornar `pipeline_observer.py track` **idempotente por `(run_id, agent_id, attempt)`** —
  a linha do runner e a do agente não podem contar duas vezes
- [ ] **6.2** Runner emite `track` com `--tokens-in` / `--tokens-out` / `--duration-ms` **reais** de
  `session.shutdown.modelMetrics`, em vez de literais copiados à mão
- [ ] **6.3** Atualizar `src/shared/utils/verify_agent_observability.py` **no mesmo commit**: a regra
  E* vira "agente migrado pode omitir o bloco". Remoção em massa deixaria o CI vermelho e a fase cega
- [ ] **6.4** Validar **CA01 — isolamento** (o critério central): rodar F1 completo em `MeuERP-002` e
  confirmar, por nó, `session.shutdown.systemTokens ≈ 13.449`, `currentTokens ≪ 128.000` e
  **zero** `session.compaction_start` / `session.truncation`
- [ ] **6.5** Validar **CA02 — modo de execução inalterado**:
  `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` sem saída; operador roda o
  `.bat` e chama o orquestrador F1 exatamente como antes
- [ ] **6.6** [P] Validar **CA07 — enforcement**: sonda tentando `view` em
  `outputs/asis/ast-raw/**` é **negada**, com `hook.start` / `hook.end` no `events.jsonl`
- [ ] **6.7** [P] Validar **paridade de artefatos**: `artifact_gate.py --project MeuERP-002 --json`
  fecha o `F1_OUTPUT_CONTRACT` (12/12 paths obrigatórios; 19/19 artefatos, era 11/19), com estrutura
  equivalente à referência em `projects/Meu-ERP/outputs/asis/`
- [ ] **6.8** [P] Regressão: `pytest tests/tools tests/utils -q` verde e cobertura de agentes
  idêntica antes/depois em `verify_agent_observability.py`

---

## Category 7 — Documentação e catálogo (M5)

Pode correr em paralelo com a Category 6 a partir da Category 2.

- [ ] **7.1** [P] Escrever `specs/033-agent-isolation-context-engineering/quickstart.md` — roteiro de
  verificação end-to-end
- [ ] **7.2** [P] Escrever os contratos: `contracts/agent-wrapper.schema.json` (frontmatter válido do
  `.agent.md`), `contracts/context-pack.schema.md` (as 5 seções + regra de degradação),
  `contracts/pipeline-dag.schema.md` (`version: 1`, waves, nós)
- [ ] **7.3** [P] Escrever `checklists/requirements.md` a partir de
  `.specify/templates/checklist-template.md` — `## IMFAI Constitution Compliance` com
  `CHK-C01…CHK-C07` **verbatim primeiro**, depois os itens específicos desta feature
- [ ] **7.4** [P] Redirecionar `docs/plan/escala-esteira-contex-engineering.md` e
  `docs/plan/contex-eginerring-github-copilot.md` para esta spec como fonte única;
  `docs/plan/memory-archotecture-middleware-knowledge-graph.md` fica reservado para a **spec 034**
- [ ] **7.5** [P] Entrada em `CHANGELOG.md`: bump MAJOR de `orchestrator-asis.md`, novo
  `execution_backend`, nota de migração e rollback
- [ ] **7.6** [P] Atualizar `docs/agents-catalog.md` — os 102 agentes ganham a coluna "wrapper
  `.agent.md`"
- [ ] **7.7** [P] Atualizar `.azure-pipelines/validate-agent-observability.yml`: acrescentar
  `src/shared/data/pipeline-dag/**`, `src/shared/tools/agent_runner.py`, `AGENTS.md` e
  `.github/agents/**` aos paths de trigger, e coletar `tests/` na raiz (hoje o CHK-04 só coleta
  `tests/tools` e `tests/utils`, então `test_pipeline_dag.py` não rodaria)
- [ ] **7.8** [P] Documentar em `docs/` o passo-a-passo de execução isolada: `--agent`, `/agent`,
  o que vai no `.agent.md` × o que vai no `AGENTS.md`, e o rollout F2–F8

---

## Category 8 — Feedback de execução (2026-08-03)

Apuração das 4 recomendações emitidas por uma sessão real do Copilot CLI. Ver `spec.md` § 3.9 e
`docs/copilot-cli-runtime-facts.md` § 11.

- [x] **8.1** Levantar os logs: 70 sessões, 1.033 `subagent.started`. Resultado: `general-purpose`
  53/53 e `explore` 19/24 com **zero tool calls**; 78 dispatches desperdiçados; falha nas duas rotas
  (72 proxy, 5 direto)
- [x] **8.2** `src/shared/tools/check_session_health.py` — detector de subagente fora do BYOK, sem
  tool call e de 404 de modelo. Escopos `--all` / `--session` / `--since`, saída `--json`, exit 1 em
  problema
- [x] **8.3** `agent_runner.py`: `read_session_facts()` extrai `subagent.started`/`completed`;
  `subagent_problems()` + `_classify()` classificam como `config_error` **antes** do gate de artefato
- [x] **8.4** `AGENTS.md` § 5 (D1/D2): proíbe delegar a `general-purpose`/`explore`, com o número
  medido. Chega às 8 fases pelo `AGENTS-CORE`; teto do arquivo elevado a 9 KB com justificativa no teste
- [x] **8.5** `ntp_time.py`: fallback sinaliza por stderr + exit 3; `--json` expõe `ntp_fallback`;
  stdout e invocação sem flags **inalterados** (contrato com `.vscode/settings.json`).
  `summary-agent.md` ganha o "como detectar" que faltava ao `[BENCHMARK BLOCKED]`
- [x] **8.6** `artifact_gate.py --recheck-ms` + re-check no `agent_runner.run_node()`, **só** no
  caminho negativo, com contador `gate_rescued_on_recheck`
- [x] **8.7** `.vscode/mcp.json`: `HEADROOM_LOG_FILE` no server `ava-headroom-cli` — único vetor real
  de log desligado. `.bat` deixa de dizer "carregado" (só prova que o arquivo existe)
- [ ] **8.8** `subagents.agents.<nome>.model = "inherit"` — **bloqueado**: caminho do settings não
  confirmado. Rodar `/subagents` numa sessão interativa, ler o arquivo gravado, versionar o path
- [ ] **8.9** *(follow-on)* Shim de `/v1/models/{id}` no proxy Headroom — 72 das 77 falhas são nessa
  rota; contorno desenhado no Anexo A de `02-esteira-github-cli.md` e nunca implementado
- [ ] **8.10** *(follow-on)* Fusos mistos em `pipeline-run-state.json`: `cmd_track` grava BRZ,
  `agent_runner._now_iso()` grava UTC; `pipeline_observer.py:806,1055` ordena por **string**

---

## Category 9 — Feedback de execução, 2ª rodada (2026-08-04)

Ver `spec.md` § 3.10 e `docs/copilot-cli-runtime-facts.md` § 12.

- [x] **9.1** Medir taxa de falha por ferramenta (junção `execution_start`→`execution_complete` por
  `toolCallId`): `glob` 0% · `grep` 0% · `powershell` 1% · `task` **25%** · `edit` 21%
- [x] **9.2** `AGENTS.md` § D3 — nunca aninhar delegação (289 das 345 falhas de `task`) e § D4 —
  escrita simples é `create`/`edit` direto
- [x] **9.3** `AGENTS.md` § D5 — não declarar tool inexistente no `tools:` (prevenção de drift)
- [x] **9.4** `AGENTS.md` § C8 — verificação de arquivo é `glob`/`grep`; recusa registrada da troca
  por `Get-ChildItem`, com o número que a contradiz
- [x] **9.5** `applyTo: 'fastqa/**'` no índice FastQA — **−6.815 tokens por sessão**; roteamento
  preservado por 1 linha em `.github/copilot-instructions.md`
- [x] **9.6** Teto do `AGENTS.md` redesenhado: `AGENTS-CORE` ≤ 8 KB (replicado 102×) e arquivo
  ≤ 10 KB (cobrado uma vez), com teste próprio para cada
- [ ] **9.7** *(follow-on)* 271 `File too large to read at once` + 27 `view_range out of bounds` —
  assinatura de ingestão exaustiva; é o que o context pack (Category 2) deve eliminar
- [ ] **9.8** *(follow-on)* `edit` com 21% de falha — 21 das 29 são ENOENT de branch antiga, mas
  vale confirmar que não há path relativo mal resolvido

---

## Completion Checklist

- [ ] As 7 categorias completas
- [ ] `AGENTS.md` ≤ 8 KB, language-agnostic, com os delimitadores `AGENTS-CORE`
- [ ] **102 de 102** wrappers gerados; `generate_agent_wrappers.py --check` verde
- [ ] `copilot --log-level warning` → **zero** `unknown fields ignored`
- [ ] `pytest tests/ -q` verde, incluindo `test_agent_wrappers`,
      `test_validate_language_agnostic` e `test_pipeline_dag`
- [ ] `validate_language_agnostic.py --strict --paths AGENTS.md` → 0 violações
- [ ] F1 real em `MeuERP-002`: `F1_OUTPUT_CONTRACT` 12/12 e **zero** `compaction_start`/`truncation`
- [ ] `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` sem saída
- [ ] `CHANGELOG.md` e `docs/agents-catalog.md` atualizados
- [ ] `docs/plan/*.md` redirecionados para esta spec
- [ ] Rollback verificado: `execution_backend: inprompt` restaura o caminho atual bit a bit
