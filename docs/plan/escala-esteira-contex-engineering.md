> ⚠️ **SUPERSEDIDO — consolidado em `specs/033-agent-isolation-context-engineering/`.**
>
> Este documento foi absorvido pela spec 033 (isolamento de janela por agente + context
> engineering), que é a **fonte única** a partir de 2026-08-02. Ele fica aqui como registro do
> raciocínio original; decisões, números e escopo vigentes estão na spec.
>
> | Onde olhar | Para quê |
> |---|---|
> | `specs/033-.../spec.md` | problema, decisões e critérios de aceite |
> | `specs/033-.../plan.md` | Constitution Check e desenho técnico |
> | `specs/033-.../tasks.md` | plano de execução em 7 categorias |
> | `specs/033-.../research.md` | fatos medidos do M0 + as 5 técnicas + alternativas descartadas |
> | `docs/copilot-cli-runtime-facts.md` | os números de runtime (medidos, não estimados) |

---

Ready for review
Select text to add comments on the plan
Escalar a esteira AVA Fabric — orquestradores de fase invocando agentes isolados

## STATUS

| Milestone | Estado |
|---|---|
| M0 — Spike de medição | ✅ **CONCLUÍDO** → `docs/copilot-cli-runtime-facts.md` |
| M1 — Runner mínimo | 🔨 em implementação |
| M2–M8 | pendentes |

### Correções que o M0 impôs a este plano (medidas, não estimadas)

1. **`--excluded-tools=skill` vira flag padrão do runner.** Não estava no desenho. Rende ~−4.400
   tokens (as 75 skills entram no prompt de sistema). Com ela o overhead estático cai de **29.871 →
   13.449 (−55%)**, não os ~90K que este documento estimava. **Orçamento real: ~106K úteis**, não 90K.
2. **`--disable-builtin-mcps` rende quase nada** (−619, não os 8.273 supostos). Manter, mas o ganho
   está em `--no-custom-instructions` (−11.372) e `--excluded-tools=skill`.
3. **`--context long_context` NÃO foi verificado** — a flag é aceita e registra `contextTier`, mas
   nenhuma sessão long_context chegou a compactar, então o limite desse tier é desconhecido. **Removido
   do wave1** (§1.1) até haver medição. As 75 ocorrências de `tokenLimit` observadas são `128000`.
4. **O proxy Headroom é bloqueador, não detalhe.** 87 erros 404 em 25 sessões; **71 apontam para
   `127.0.0.1:8787`**, contra 6 no endpoint direto. As 6 sondas do M0 foram direto e todas deram
   `exit 0`. O runner roda hoje **só na rota direta**; rodar comprimido exige antes o shim de
   `/v1/models/{id}` (Anexo A de `docs/02-esteira-github-cli.md`).

Também verificado no M0: **`tools:` é enforçado de verdade** no `.agent.md`; `version:` e
`allowed-tools:` são **descartados** (`unknown fields ignored: version, allowed-tools`); a tool de shell
chama-se **`powershell`**, não `bash`; `exit 0` em sucesso, `1` em erro de argumento.

Context
A esteira roda 103 agentes .md numa única sessão interativa do GitHub Copilot CLI. O ava-master-orchestrator não está em uso — o ponto de entrada real são os orquestradores de fase (ava-asis-orchestrator F1, ava-tobe-orchestrator F2, ava-stack-orchestrator F4, ava-qa-orchestrator F5, ava-devops-orchestrator F6, + F3/F7/F8). Cada um despacha seus sub-agentes dentro do próprio prompt (DISPATCH @agent-id + AWAIT "↳ ✅ [agent-id]"), então tudo compartilha uma janela de contexto.

O modo de falha está documentado no repo (docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md): em processaERP-008 (363 units, 174.375 LOC — um décimo do alvo de 1.5M LOC) a saída AST comprimida somou 761.376 tokens. Chamadas de 34, 5 e 62 minutos, 3 dispatches do mesmo agente em 16 segundos, 8 de 19 artefatos F1 nunca gerados.

Medições que mudam o diagnóstico
Levantadas do runtime real (copilot --help, ~/.copilot/session-state/*/events.jsonl, ~/.copilot/logs/*.log, docs oficiais do Copilot CLI) — não são estimativas:

Fato	Valor medido	Consequência
Janela de contexto	128.000, não 200.000	session.compaction_start → "tokenLimit":128000
Prompt de sistema	systemTokens: 21.037	não reclamável
Definições de tool	toolDefinitionsTokens: 8.273	não reclamável
Overhead estático	~29.000 tokens (23%)	sobram ~90K úteis, não 200K
copilot-instructions.md	28,9 KB ≈ 7,5–8K tokens	+6% da janela, em todo processo
Corpo de .agent.md	máx. 30.000 caracteres	37 dos 107 agentes estouram
orchestrator-asis.md	193.848 caracteres (~48K tokens)	37% da janela só para existir
O CLI já emitiu o aviso explícito numa sessão real: session.warning / warningType: "compaction_static_context_budget" — "Static context is using 76% of available input tokens... system messages and tool definitions cannot be reclaimed."

Ou seja: os limiares de context_budget.py (400K inline / 700K bc_scoped) foram calibrados contra uma janela que não existe. O orçamento real por agente é ~90K, não 200K.

Dois bugs de runtime que hoje passam por "problema de contexto"
Encontrados nos logs, não são hipótese:

Sub-agentes internos não herdam o modelo BYOK. subagent.started → "agentName":"general-purpose","model":"gpt-5.4", seguido de session.error → "Model 'claude-sonnet-4-6' not found on provider at http://127.0.0.1:8787 (HTTP 404)", e subagent.completed com "totalToolCalls":0. explore roda em gpt-5.4-mini. Parte dos "agentes que não produziram nada" é roteamento de modelo, não janela.
Dispatch por @nome falha em silêncio. tool.execution_complete → "success":false, error: "Skill not found: ava-qa-orchestrator", e a sessão "caiu para execução direta".
Causa raiz
Uma janela compartilhada por N agentes. Compressão não resolve acumulação — só adia o estouro. As mitigações existentes (AGENT_ARTIFACT_SLICE, LARGE ARTIFACT PROTOCOL, proxy Headroom, artifact_gate.py) estão certas mas vivem em texto de prompt, não em enforcement.

O que habilita a correção
O Copilot CLI 1.0.77 instalado suporta isolamento por processo e hooks de permissão — capacidades que a esteira não usa hoje:

-p, --prompt <text>          executa e sai (não-interativo)
--agent <agent>              agente customizado (.github/agents/*.agent.md)
--session-id <uuid>          define o UUID → events.jsonl determinístico
--no-custom-instructions     não carrega os 28,9 KB de copilot-instructions.md
--disable-builtin-mcps       remove github-mcp-server das toolDefinitions
--output-format json / --share / --secret-env-vars / --max-ai-credits
E .github/hooks/*.json com preToolUse, que retorna {"permissionDecision":"allow|deny|ask","permissionDecisionReason":"..."} — o enforcement real que o LARGE ARTIFACT PROTOCOL nunca teve.

Arquitetura alvo
O orquestrador de fase continua sendo o agente que invoca os demais — mas invoca como processo isolado, não como texto no próprio prompt. Sem master orchestrator.

                 ANTES (por fase)                          DEPOIS (por fase)
   ┌──────────────────────────────────┐      ┌────────────────────────────────────────┐
   │ ava-asis-orchestrator            │      │ ava-asis-orchestrator  (~15 KB)        │
   │   193.848 chars = 37% da janela  │      │   gates + consolidação + narrativa     │
   │   └ DISPATCH @a  (in-prompt)     │      │   └ Bash: agent_runner.py --phase F1   │
   │   └ DISPATCH @b  (in-prompt)     │      └──────────────┬─────────────────────────┘
   │   └ DISPATCH @c  (in-prompt)     │            lê pipeline-dag/F1.yaml
   │                                  │         ┌───────────┼───────────┐
   │  acumula 761K numa janela de 128K│         ▼           ▼           ▼
   └──────────────────────────────────┘    copilot -p   copilot -p   copilot -p
                                            agente A     agente B     agente C
                                            ~90K limpo  ~90K limpo  ~90K limpo ✅
Cada fase é autônoma: F1 pode migrar sem tocar em F2. O gate entre fases continua sendo o que já é hoje — artefatos em disco, verificados por artifact_gate.py.

Decisões
Confirmadas por você: runner determinístico · context pack + query CLI · runner assume observabilidade · --no-custom-instructions por agente · perfis de linguagem + lint em CI.

Ajuste desta revisão: escopo é o orquestrador de fase, não o master. O master-orchestrator.md fica intacto e fora do plano.

Fora de escopo: progressive disclosure geral nos .md (entra só onde o cap de 30 KB obriga), decisions.jsonl / glossary.json / state_tool.py, e map-reduce genérico.

Escopo 1 — Runner por fase
1.1 DAG por fase — src/shared/data/pipeline-dag/F{N}.yaml (NOVOS)
Um arquivo por fase, extraído das tabelas ## Agent Team / dispatch_schedule do orquestrador correspondente (em orchestrator-asis.md: linhas 187–266 e a tabela Artifact Output Contract per Agent na 839).

version: 1
phase: F1
module: asis-diagnostic
orchestrator: ava-asis-orchestrator
max_parallel: 3                    # alinhado ao compression_max_workers do Headroom
waves:
  - id: wave1
    blocking: true
    agents:
      - id: ava-asis-solution-{legacy_technology}
        slice: all
        # context: long_context  -- REMOVIDO no M0: tier aceito, mas limite nao verificado
        timeout_s: 3600
        max_ai_credits: 40
  - id: wave2
    depends_on: [wave1]
    agents:
      - {id: ava-asis-inventory,     slice: [08_code_overview, 02_form_business_rules], timeout_s: 900}
      - {id: ava-asis-db-analyzer,   slice: [03_database_rules, 04_database_schemas, 05_procedures]}
      - {id: ava-asis-events-pubsub, slice: [06_integrations]}
⚠️ Risco #1 do plano — quarta fonte de verdade. O repo já tem três "espelhos manuais" que divergem: artifact_gate.py::ARTIFACT_CONTRACTS ("espelha 1:1 a tabela de orchestrator-asis.md; alterar um lado exige alterar o outro"), context_budget.py::AGENT_ARTIFACT_SLICE, e agent_registry.py — que existe justamente porque dois AGENT_CATALOG manuais divergiram ("52 de 101 agentes ausentes, 18 versões divergentes"). O DAG deve ser A fonte: artifact_gate e context_budget passam a importar dele, com tests/test_pipeline_dag.py afirmando dag.nodes == ARTIFACT_CONTRACTS.keys() == agent_registry.catalog(). Adicionar como quarto par piora o modo de falha recorrente do repo.

1.2 Runner — src/shared/tools/agent_runner.py (NOVO)
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --wave wave2
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --agent ava-asis-inventory
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --dry-run   # sem inferência
Por nó, na ordem:

Gate — artifact_gate.py --agent A --json; exit 0 = artefatos presentes → skip.
Budget — context_budget.build_budget(), com limiares recalibrados para ~90K úteis.
Context pack — materializa .context/{agent_id}/context-pack.md (§2.2).
Spawn — processo copilot -p isolado (§1.3).
Verificação — events.jsonl + artifact_gate (§1.5). Artefato é a autoridade.
Retry — escada de reparo (§1.6).
Telemetria — pipeline_observer.py track com números reais de session.shutdown.
--dry-run é requisito de design: valida o runner sem gastar inferência.

1.3 Comando emitido por agente
copilot -p "<envelope ~1200 chars>"
  --agent ava-asis-inventory
  -C <REPO_ROOT>                          # NÃO o dir do projeto — as specs usam paths repo-relativos
  --add-dir <raiz do código legado fora do repo>
  --model claude-sonnet-4                 # nunca 'auto' — foi assim que general-purpose caiu em gpt-5.4
  --allow-all-tools --no-ask-user
  --no-custom-instructions                # M0: -11.372 tokens
  --disable-builtin-mcps                  # M0: -619 tokens
  --excluded-tools=skill                  # M0: -4.400 tokens (as 75 skills entram no system prompt)
  --output-format json --session-id <uuid4 do runner>
  --log-level error --log-dir  projects/{p}/outputs/.runs/{run_id}/logs/{agent_id}
  --share                      projects/{p}/outputs/.runs/{run_id}/transcripts/{agent_id}.md
  --secret-env-vars COPILOT_PROVIDER_BEARER_TOKEN
  --no-auto-update --no-remote --no-remote-export
  --max-ai-credits <do DAG>
Justificativas não-óbvias:

-C <REPO_ROOT>, não o dir do projeto. As 105 specs usam paths repo-relativos (python src/shared/tools/pipeline_observer.py, src/modules/ava-fabric-agents/...). Mudar o cwd quebra todas.
--model explícito — corrige o bug #1 do Context: sem pin, o modelo default não é o BYOK e a chamada 404 contra o proxy Headroom.
--session-id gerado pelo runner — é a jogada central. Depois do exit, o runner lê %USERPROFILE%\.copilot\session-state\<uuid>\events.jsonl num caminho determinístico. Não parsear stdout.
--disable-builtin-mcps — remove o github-mcp-server das toolDefinitionsTokens (8.273 medidos) e elimina o ruído Connecting to IDE MCP server presente em todo log.
--secret-env-vars — sem isso, --share e o JSONL capturam a chave BYOK de .copilot-key.
--no-remote --no-remote-export — o export remoto está ligado por default (api.business.githubcopilot.com/agents). Não se quer 103 sessões de código legado exportadas.
Não usar --allow-all / --yolo (implicam --allow-all-paths), --autopilot (-p já roda até o fim; autopilot adiciona turnos de continuação), --resume/--continue (cada nó precisa nascer limpo).
Montar o argv como lista Python, shell=False — o envelope contém quebras de linha, crases e {}.

O ambiente do filho é o do pai + o bloco BYOK que hoje vive em copilot-cli-headroom.bat (linhas 44–83). O runner porta esse bloco, roda headroom_tool.py proxy status e registra compression=on|off por nó — hoje o bypass é silencioso.

1.4 Envelope do prompt
Execute o agente `{agent_id}` para o projeto `{project}`.

1. Read `{abs_spec_path}` e siga LITERALMENTE os Execution Steps. Nao improvise.
2. Seu contexto ja esta materializado em `{abs_context_pack}`. Leia-o PRIMEIRO.
3. PROIBIDO ler arquivos sob `projects/{project}/outputs/asis/ast-raw/`.
   Para consultar o AST:
   python src/shared/tools/ast_query.py -p {project} --select <tabela> --where <k=v> --limit N
4. Vars: project_name={project} | trace_id={trace_id} | language={lang} | scope_modules={scope}
5. Faltando (artifact_gate): {artifacts_missing}
6. NAO execute blocos `pipeline_observer.py ... track` — o runner registra.
7. Grave TODO o output contract em UMA chamada Bash (shared/batch-write-protocol.md).
1.5 Detecção de conclusão — em camadas, artefato manda
Exit code — M0 confirmou: 0 = sucesso, 1 = erro de argumento. Não distingue falha de artefato, por isso o gate manda.
events.jsonl no caminho escolhido pelo runner:
session.task_complete → data.summary (narrativa final, guardar).
session.error → {errorType, message, statusCode}. 404 de modelo = falha de configuração: abortar a fase, não retentar.
session.compaction_start ou session.truncation presentes → flag context_overflow, mesmo que o nó tenha "passado". É a assinatura exata da ISSUE-002 e o sinal para apertar aquele pack.
session.shutdown → modelMetrics.*.usage (inputTokens, outputTokens, cacheReadTokens), totalApiDurationMs, codeChanges.filesModified, systemTokens, toolDefinitionsTokens.
artifact_gate.py --json — AUTORIDADE. Nó que "passou" sem artefato é failed. Não é política nova: orchestrator-asis.md:184 já diz "artifacts_confirmed É MEDIDO, NUNCA DECLARADO".
Timeout do DAG → matar a árvore de processos (taskkill /PID <pid> /T /F; Popen.terminate() deixa o filho node órfão no Windows).
session.shutdown entrega de graça exatamente o que pipeline_observer track pede hoje via bloco Bash: em 206 lugares.

1.6 Escada de retry
Tentativa	Mudança
1	Baseline.
2	Novo --session-id. Prompt ganha bloco de reparo: artifacts_missing do gate + session.error.message + os 3 últimos tool.execution_complete com success:false.
3	Degradar: pack reduzido à fatia obrigatória; --effort high; se houve context_overflow, recortar por bounded context de module-partition.json.
4	Só agentes solution-* (alinhado ao "max 4x" do retry-protocol.md).
Backoff (30s → 120s) apenas para statusCode em {429, 5xx}. Nunca para 404. Nunca para artefato-ausente — isso é problema de prompt, não de transporte. Todo artifact_gate roda antes de cada tentativa (anti-retry-storm já existente).

1.7 Wrappers — .github/agents/ava-*.agent.md (NOVOS, gerados)
Formato verificado (docs oficiais + o parser do próprio CLI, que loga unknown field ignored: handoffs):

Campo	Obrigatório
description	sim
name, tools, model, target, disable-model-invocation, user-invocable, mcp-servers, metadata	não
Corpo: máximo 30.000 caracteres.
O frontmatter atual dos agentes usa version: e allowed-tools: — ambos seriam descartados com warning. A chave correta é tools:.
~/.copilot/agents/ vence .github/agents/ em colisão de nome → preflight deve falhar se houver colisão (reprodutibilidade).
Gerar wrappers finos (≤2 KB) com generate_agent_wrappers.py, alimentado por agent_registry.py. O wrapper carrega description + tools: + model: + o destilado de ~30 linhas das Output Integrity Rules (§3.2). A spec real chega por Read explícito no -p. É o mesmo padrão dos SKILL.md atuais (14 linhas).

Gera-se 103, não 75 — fechando a lacuna em que 28 sub-agentes só eram alcançáveis por dispatch textual (que, conforme o Context, falha em silêncio).

1.8 O orquestrador de fase depois da mudança
orchestrator-asis.md cai de 193.848 para ~15 KB. Fica com o que só ele pode fazer:

resolver project-config.yaml, legacy_technology, scope_modules, trace_id;
Step 0 (extração AST via run_ast_analysis.py) e o Solution Agent Gate;
Bash: python src/shared/tools/agent_runner.py --project P --phase F1 — a invocação isolada;
ler o relatório do runner, aplicar os gates de fase, consolidar master-report.md e o Summary.
O DAG, a tabela de contratos, o dispatch protocol e as tabelas de roteamento saem do prompt e viram pipeline-dag/F1.yaml. Isso resolve o cap de 30 KB para os orquestradores sem "progressive disclosure" genérico. Mesmo tratamento para F2, F4, F5, F6.

Escopo 2 — Context engineering
2.1 Enforcement por hook — .github/hooks/ava-guardrails.json (NOVO)
Correção de premissa: --add-dir não cerca outputs/asis/ast-raw/. O cwd e o gitRoot são implicitamente permitidos, e -C <REPO_ROOT> é obrigatório (§1.3) — então o AST está dentro da árvore liberada. --add-dir só adiciona.

O enforcement real é um hook preToolUse (src/shared/tools/hooks/pretooluse_guard.py) que nega leitura quando o path está sob outputs/asis/ast-raw/ ou o arquivo tem ≥200 KB, devolvendo:

{"permissionDecision":"deny",
 "permissionDecisionReason":"Artefato AST fora do context pack. Use: python src/shared/tools/ast_query.py -p <proj> --select <t> --where <k=v> --limit N"}
É a primeira vez que o LARGE ARTIFACT PROTOCOL vira regra executável em vez de prosa. --add-dir fica só para as árvores de código legado fora do repo.

2.2 Context packs materializados
projects/{p}/outputs/.context/{agent_id}/context-pack.md, escrito pelo runner antes do spawn:

# Context Pack — ava-asis-inventory
run_id: … | project: MeuERP-002 | language: delphi | tokens: 11.240 / ~90.000 úteis

## 1. Sua fatia AST (já decodificada do formato Headroom)
### 08_code_overview   ### 02_form_business_rules

## 2. Índice de artefatos upstream        ← hand-off barato (~1 KB)
| artefato | agente produtor | tamanho | seções |
> Leia sob demanda. Não estão embutidos aqui de propósito.

## 3. Como consultar o que não está aqui
python src/shared/tools/ast_query.py -p MeuERP-002 --select … --where … --limit …
> ast-raw/ é negado pelo hook preToolUse. Use a query.

## 4. Seu output contract (do artifact_gate)
| outputs/asis/inventory-report.md | FALTANDO |
Se a fatia decodificada exceder o budget, o runner degrada para query-only (seção 1 vira só contagens + instruções) e registra a decisão no pack. Nenhum agente recebe pack maior que a janela — é o gate que faltava. A seção 2 é a versão barata do hand-off, sem introduzir uma nova superfície de ferramentas nos 103 prompts.

2.3 Query layer — ast_index.py + ast_query.py (NOVOS)
ast_index.py roda uma vez por projeto, após run_ast_analysis.py, e constrói outputs/asis/ast-raw/ast-index.sqlite decodificando via headroom_context.py (read_artifact_payload) — o único decoder do formato SmartCrusher no repo. Tabelas: units, classes, procedures, business_rules, forms, db_tables, db_rules, integrations, apis.

Sem FTS5 na v1. Os 10 artefatos são estruturados; tabelas indexadas + --where cobrem os casos reais. FTS5 adiciona tempo de build e um segundo dialeto de query para uma necessidade ainda não demonstrada — entra quando uma consulta falhar sem ele.

ast_query.py -p MeuERP-002 --select business_rules --where unit=CadastroCliente \
             --fields id,type,expression,source_ref --limit 200 --format md
ast_query.py -p MeuERP-002 --count business_rules --group-by type
--format md por default: markdown tabular custa menos tokens que JSON pretty e é o que o agente vai transcrever. Efeito: a consulta que hoje exige carregar 4 MB de sql-ir.json devolve ~8 KB.

2.4 Determinismo sobre LLM
Já existe boa parte (business_rules_catalog_generator.py com assert de paridade, module_partitioner.py, sql_ir_generator.py, gen_er_diagram.py). Estender e tornar obrigatório, não criar: ast_index.py emite outputs/asis/.internal/metrics-computed.json (LOC, classes, procedures, forms, tabelas, BR por tipo) e inventory-asis.md passa a transcrever em vez de contar. Elimina a alucinação numérica na origem.

2.5 Bugs de contexto a corrigir junto
Todos no caminho exato que este plano toca:

projects/MeuERP-002/context/project-config.yaml:9 — linha malformada: scope_modules foi engolido pelo comentário de trace_id. O filtro de escopo não existe nesse projeto.
quality_gates: declarado duas vezes — _template (L330 e L599) e MeuERP-002 (L226 e L332). Em YAML o segundo vence; o primeiro bloco é descartado em silêncio.
run_ast_analysis.py::_ensure_manifest_metrics grava tokens_out = len(text) (caracteres) sob files[], enquanto context_budget.py lê artifacts[].tokens_out — manifest sintetizado faz o budget gate ler 0 tokens e liberar tudo como subagent.
summary-agent.md (14 ocorrências) e summary-remediation-agent.md ainda apontam para asis/delphi-ast-raw/ em vez de ast-raw/{language}/.
Escopo 3 — Enxugar os processos
3.1 Runner assume a observabilidade — migração por agente, não em massa
Os ~206 blocos Bash: pipeline_observer.py ... track são hoje a única observabilidade do caminho interativo, e src/shared/utils/verify_agent_observability.py exige a presença deles (enforçado em .azure-pipelines/validate-agent-observability.yml). Deletar em massa deixa o CI vermelho e a fase cega.

Sequência segura:

Tornar pipeline_observer track idempotente por (run_id, agent_id, attempt) — assim linha do runner e linha do agente não podem contar duas vezes.
Runner passa a emitir track com --tokens-in/--tokens-out/--duration-ms reais de session.shutdown.modelMetrics.
Remover o bloco agente a agente, atualizando verify_agent_observability.py no mesmo commit (a regra vira "agente migrado pode omitir").
Ganho final: ~200 tool calls a menos por run — com o overhead medido em ISSUE-003-tool-call-overhead-f1-f2-performance.md, é a maior economia de tempo isolada. Elimina também as 51 inconsistências já catalogadas (3 agentes reportando o id de outro, 6 com a fase errada), porque o dado passa a vir do processo e não de um literal copiado à mão.

headroom_tool.py attribute continua funcionando — as janelas de execução ficam mais precisas.

3.2 --no-custom-instructions por agente
28,9 KB ≈ 7,5–8K tokens de prompt não reclamável numa janela de 128K, em cada processo. O session.warning medido ("Static context is using 76%…") é evidência direta de que é esta classe de custo que empurra a compactação.

⚠️ Medir antes: .github/instructions/ soma 253 KB, e 05-fastqa-azure-devops.md sozinho tem 143 KB. Se o CLI estiver aplicando esses arquivos, o custo estático domina tudo. A flag diz que desabilita "custom instructions from AGENTS.md and related files" — confirmar em M0.

As 4 Output Integrity Rules (copilot-instructions.md L255–310) são obrigatórias e não podem sumir:

Regra	Novo lar
1 — nunca escrever em outputs/ manualmente	destilado no .agent.md + batch-write
2 — ler a spec completa antes de agir	envelope do runner, linha 1
3 — PRE-FLIGHT com DECISION: [PROCEED|BLOCKED]	substituída por artifact_gate.py — o gate determinístico faz o mesmo, antes do processo existir, sem gastar inferência
4 — precedência project-config.yaml → overrides	perfis de stack (§4) + envelope
Destilado de ~30 linhas no corpo de cada .agent.md gerado, com teste afirmando sua presença. É estritamente melhor que o status quo: 30 linhas dirigidas em vez de 28,9 KB de catálogo de skills. copilot-instructions.md continua carregando no fluxo interativo humano.

Escopo 4 — Núcleo language-agnostic (workstream paralelo)
Ortogonal ao problema de contexto — não faz a ISSUE-002 sumir e toca .specify/memory/constitution.md, que é a raiz de governança. Roda em branch separada.

4.1 Perfis
src/shared/data/languages/{delphi,dotnet,java,cobol,vb6,vbnet,powerbuilder}.yaml — perfil do legado: extensões, solution_agent, chave do analisador AST, override de slice, doc de idiomas, exemplos de diagrama.
src/shared/data/stacks/{dotnet,java-spring,python-fastapi,node-nest,go-gin}.yaml — perfil do alvo, absorvendo o que hoje está hardcoded em reference-architecture.yaml (.NET 8 / EF Core 8 / MediatR 12 / Serilog 4 / xUnit 2.7 / Angular 17 / NgRx / Azure AD B2C).
O mecanismo de resolução já existe: SOLUTION_AGENTS[legacy_technology] (orchestrator-asis.md:738) e BACKEND_AGENTS[backend_framework] (orchestrator-stack.md:120). Os perfis apenas movem esses dicts de dentro do prompt para YAML, onde runner e CI conseguem lê-los.

4.2 Limpeza (contagem atual de tokens de stack por arquivo)
Arquivo	Ocorrências	O que sai
projects/_template/context/project-config.yaml	19	dotnet_sdk_version, mediator: mediatr, orm: efcore, logging: serilog, xunit, playwright, openapi-nswag, lista ava-build-cycle-dotnet-* → stack_profile: + stack_overrides: {}; legacy_technology perde o default "delphi"
summary-agent.md	18	delphi-ast-raw/ → ast-raw/{language}/ (§2.5)
.github/copilot-instructions.md	13	L5, L66, L100, L172, L120/139/155/156, L301–303
shared/frontend-governance.md	11	Angular (DomSanitizer, environment.ts, angular.json) → shared/frontend/angular-governance.md
shared/backend-context-protocol.md	8	separar em genérico + shared/backend/{dotnet,java,python,go,node}-invariants.md; include @backend-dotnet-invariants → @backend-{backend_language}-invariants (hoje lista coder-java/go/python como consumidores e entrega invariantes .NET)
.specify/memory/constitution.md	7	Art. IX (MediatR/EF Core/ASP.NET Core), tabela Technology Reference L228–244, L6–7, L20. Corrige a contradição: o Art. I proíbe hardcode de versão e a L234 hardcoda
shared/mermaid-guardrails.md	5	exemplos C4 Delphi/Spring → languages/*.yaml → diagram_examples
Também contaminados: asis-diagnostic/shared/output-paths.md, gaps-risks-asis.md:263, exploratory-agent.md (heurísticas Delphi/VCL), behavior-mapping-agent.md, adr-tobe.md, architecture-decision-matrix-tobe.md, database-design-tobe.md, shared/artifact-only-consumption-protocol.md, .specify/templates/overrides/plan-template.md, module.yaml, README.md. Modelo limpo a seguir: shared/governance-apps.md.

4.3 Lint — src/shared/utils/validate_language_agnostic.py (NOVO)
Allowlist de arquivos genéricos, não denylist global — src/shared/data/stacks/*.yaml e shared/dotnet-research-instructions.md legitimamente contêm dotnet. Modo --report primeiro (mede a dívida sem quebrar o build), depois --strict no CI. Sem isso a limpeza regride na primeira PR.

Compatibilidade
M0–M3 não tocam nenhum arquivo existente. O caminho interativo é preservado por construção.
execution_backend: inprompt | process em project-config.yaml, default inprompt. O runner recusa rodar se for inprompt; o Context Budget Gate do orquestrador lê a mesma chave.
.github/skills/ (entrada humana) e .github/agents/ (entrada do runner) coexistem e apontam para a mesma spec — correção de spec cai nos dois.
copilot-cli-headroom.bat e copilot-cli-v1.bat intactos.
Rollback = parar de invocar agent_runner.py.
Migração fase a fase: F1 (a que tem a falha documentada) → F5 → F2 → demais.
Milestones
M0 — Spike de medição (maior valor por hora; primeiro)
Zero mudanças no repo. 5 sondas copilot -p "reply OK" --session-id <uuid> --output-format json sob o env BYOK, variando: (a) baseline, (b) +--no-custom-instructions, (c) +--disable-builtin-mcps, (d) +--excluded-tools skill, (e) --context long_context. Ler ~/.copilot/session-state/<uuid>/events.jsonl → session.shutdown.systemTokens / toolDefinitionsTokens, session.start.contextTier. Sondar um .agent.md descartável com tools: [bash] pedindo um view, para confirmar que tools: é enforçado. Confirmar semântica de exit code. Verificar: tabela de systemTokens por combinação; tokenLimit de long_context; tools: enforçado; exit codes. Saída: docs/copilot-cli-runtime-facts.md.

M1 — Runner mínimo, 1 agente, sem paralelismo
Só arquivos novos: agent_runner.py, pipeline-dag/F1.yaml (só wave2), .github/agents/ava-asis-inventory.agent.md. Spawn → events.jsonl → artifact_gate → track. Verificar: produz form-registry.json e uma linha de track com tokens ≠ 0; segunda execução dá skip pelo gate; SA|FULL byte-idêntico.

M2 — DAG completo de F1, ondas, paralelismo, retry
max_parallel: 3. --dry-run imprimindo os comandos exatos. Novo tests/test_pipeline_dag.py: aciclicidade + dag ≡ artifact_gate ≡ agent_registry + todo nó tem artefatos, slice e timeout. Verificar: dry-run revisado à mão; F1 real em MeuERP-002 entrega 19/19 artefatos (era 11/19); zero session.compaction_start entre os nós.

M3 — Context packs + hook de enforcement
context_pack.py, .github/hooks/ava-guardrails.json, hooks/pretooluse_guard.py. Verificar: um agente-sonda tentando view sql-ir.json é negado; o deny aparece como hook.start/hook.end no events.jsonl; pico de currentTokens por nó cai medidamente vs M2.

M4 — Query layer
ast_index.py, ast_query.py. Primeira modificação em agentes existentes (seções Input Contract), atrás de execution_backend: process. Verificar: build do índice < 60 s sobre os 7,1 MB de extraction; --select business_rules --where unit=X --limit 50 < 1 s e < 4 KB; F1 reexecutado produz artefatos equivalentes a M3. Conferir --count business_rules contra manifest.json (esperado 4.254 em processaERP-11) e contra business-rules-catalog.json, que já tem assert de paridade.

M5 — Observabilidade consolidada
pipeline_observer.py idempotente; remoção por agente; verify_agent_observability.py atualizado no mesmo commit. Verificar: CI verde; relatório mostra a mesma cobertura de agentes antes/depois; comparar wall-clock de F1.

M6 — Cap de 30 KB
Encolher orchestrator-asis.md (193.848 → ~15 KB) movendo DAG e contratos para YAML; dividir os demais 37 agentes acima do cap em references/*.md. tests/test_agent_body_size.py (hard ≤30.000 chars). Verificar: zero unknown field ignored e zero warning de prompt grande no --log-dir de um run completo.

M7 — Estender às demais fases
F5 → F2 → F4/F6/F7/F8, um pipeline-dag/F{N}.yaml por vez. Fan-out por bounded context apenas para os ava-asis-solution-* — são os únicos que carregam a fatia completa (todos os outros recebem 1–3 artefatos ou []); map-reduce genérico para 103 nós é injustificado.

M8 — Language-agnostic (branch separada, §4)
Riscos
#	Risco	Mitigação
R1	pipeline-dag.yaml vira 4ª fonte de verdade divergente	É A fonte; artifact_gate/context_budget importam dela; tests/test_pipeline_dag.py
R2	Janela é 128K com ~29K estáticos, não 200K → limiares 400K/700K sem sentido por agente	Recalibrar para ~90K úteis; manter os valores atuais só como heurística de total de pipeline
R3	-C REPO_ROOT anula o escopo de --add-dir	Hook preToolUse é o enforcement; --add-dir só para fontes fora do repo
R4	Env BYOK não propagado → 404 de modelo (já observado)	Portar copilot-cli-headroom.bat L44–83 para o runner, com --model pinado e falha rápida no 404
R5	Proxy Headroom único vs N processos paralelos	max_parallel alinhado ao compression_max_workers; registrar compression=on/off por nó
R6	Estouro de créditos/rate-limit em 103 processos	--max-ai-credits por nó no DAG + budget global no runner
R7	~/.copilot/agents/ sombreia .github/agents/	Preflight falha em colisão de nome
R8	Cap de 30.000 chars (37 agentes acima)	Wrappers finos agora; M6 divide os corpos
R9	Remover os 206 blocos de track cega o caminho interativo	track idempotente + remoção por agente + CI atualizado no mesmo commit
R10	Timeout deixa processos node órfãos no Windows	taskkill /PID <pid> /T /F, não terminate()
R11	Skills ainda carregam nos processos, inflando os 21K de system prompt	Medir em M0; se material, --excluded-tools skill