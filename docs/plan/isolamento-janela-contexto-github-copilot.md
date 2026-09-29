Ready for review
Select text to add comments on the plan
Spec 033 — Isolamento de janela por agente + Context Engineering (GitHub Copilot CLI)
Context
O que existe hoje
A esteira AVA Fabric roda 107 agentes .md (3,5M chars) numa única sessão interativa do GitHub Copilot CLI. O ponto de entrada real são os orquestradores de fase (ava-asis-orchestrator F1, ava-tobe-orchestrator F2, …), que despacham sub-agentes dentro do próprio prompt (DISPATCH @agent-id + AWAIT). Resultado: todos compartilham uma janela.

Falha documentada (docs/issues/ISSUE-002): em processaERP-008 (174.375 LOC — 1/10 do alvo de 1,5M) a saída AST somou 761.376 tokens; chamadas de 34/5/62 min; 8 de 19 artefatos F1 nunca gerados.

O que o M0 já mediu (docs/copilot-cli-runtime-facts.md)
Fato	Valor medido	Consequência
Janela	128.000 (não 200.000)	limiares 400K/700K de context_budget.py são ficção
Overhead estático baseline	29.871 (23%)	sobram ~90K
Overhead com flags do runner	13.449 (−55%)	~106K úteis por processo
--no-custom-instructions	−11.372	maior alavanca isolada
--excluded-tools=skill	−4.400	as 75 skills entram no system prompt
tools: no .agent.md	enforçado de verdade	restrição real
version:/allowed-tools:	descartados com warning	wrapper tem que emitir tools:
Tool de shell	powershell, não bash	mapear nos wrappers
Corpo do .agent.md	máx. 30.000 chars	orchestrator-asis.md = 193.848; security-orchestrator-asis.md = 114.996; 37 dos 107 estouram
Estado real do código (verificado agora)
Item	Situação
src/shared/tools/agent_runner.py	existe e funciona (670 linhas, untracked): DAG, gate, BYOK env, envelope, spawn isolado, parsing de events.jsonl, classificação, taskkill /T /F, telemetria, --dry-run
src/shared/data/pipeline-dag/F1.yaml	existe, só wave2 (3 nós); max_parallel: 1; max_attempts: 1
.github/agents/*.agent.md	1 de 107 (ava-asis-inventory, escrito à mão) — os outros 10 arquivos são tooling do SpecKit
AGENTS.md	NÃO EXISTE em lugar nenhum do repo
.github/skills/*/SKILL.md	75 — 32 agentes sem wrapper, alcançáveis só por dispatch textual (que falha em silêncio)
.github/copilot-instructions.md	28.907 chars; § "Available Skills (44 agents)" — defasado em 63
generate_agent_wrappers.py	não existe
context_pack.py, .github/hooks/	não existem
ast_index.py / ast_query.py	não existem
tests/test_pipeline_dag.py, test_agent_body_size.py	não existem
Retry, paralelismo, enforcement de budget	não implementados
Os 3 planos soltos em docs/plan/ (a consolidar)
escala-esteira-contex-engineering.md (runner/DAG, M0 ✅ / M1 🔨) · contex-eginerring-github-copilot.md (as 5 técnicas + AGENTS.md, feito no projeto inicial) · memory-archotecture-middleware-knowledge-graph.md (knowledge graph — fica para a spec 034).

Objetivo desta spec
Todo agente invocado pelo orquestrador de fase roda em janela de contexto própria.
Todos os 107 agentes viram custom agents nativos em .github/agents/*.agent.md.
AGENTS.md na raiz com os guardrails gerais — zero conteúdo de linguagem legada, válido para delphi, java, .net, cobol, vb6, powerbuilder e o que vier. Todos herdam.
Shared context com memória: context pack materializado por agente + shared-context.md pequeno e curado, com enforcement executável (não prosa).
Restrição inviolável do usuário
O modo de execução via GitHub CLI permanece o mesmo. copilot-cli-headroom.bat e copilot-cli-v1.bat intactos; o humano continua abrindo o CLI e chamando o orquestrador da fase do mesmo jeito. A única diferença é que os agentes invocados passam a atuar na própria janela.

Decisões tomadas (confirmadas)
Decisão	Escolha
Isolamento	Híbrido — todos os agentes viram .agent.md reais; produção via runner por processo, delegação nativa disponível para uso interativo
Escopo de validação	F1 (asis-diagnostic, 28 agentes) como padrão de referência — wrappers gerados para os 107
Memória	Context pack determinístico agora; knowledge graph = spec 034
Planos antigos	Consolidados nesta spec; docs/plan/*.md passam a apontar para ela
A tensão central que este plano resolve
--no-custom-instructions (−11.372 tokens, a maior economia medida) desliga o carregamento do AGENTS.md. Ou seja: o requisito "AGENTS.md carregado, todos herdam" e a otimização do runner são diretamente conflitantes.

Solução — AGENTS.md é a fonte única, entregue por dois caminhos:

AGENTS.md (raiz, ~6 KB, language-agnostic)
   │
   ├─ caminho INTERATIVO (humano) ──── Copilot CLI carrega nativamente
   │
   └─ caminho RUNNER (--no-custom-instructions)
          └─ generate_agent_wrappers.py injeta o bloco delimitado
             <!-- AGENTS-CORE:START --> … <!-- AGENTS-CORE:END -->
             no corpo de cada .agent.md gerado
O bloco é injetado, nunca editado à mão; tests/test_agent_wrappers.py afirma que o bloco de todo wrapper bate byte-a-byte com AGENTS.md. Custo: ~1,5K tokens no corpo do agente (cobrado só na janela dele), contra 11,4K de custom instructions em todo processo. Herança real, sem regressão.

Entregas
1. AGENTS.md (raiz) — NOVO, language-agnostic
Alvo ≤ 8 KB. Conteúdo, todo neutro de linguagem:

Seção	Conteúdo
Identidade & escopo	o que é a esteira, fases F1–F8, papel de orquestrador vs agente
Output Integrity Rules	as 4 regras de copilot-instructions.md L255–310, destiladas (nunca escrever em outputs/ fora do contrato; ler a spec inteira antes de agir; precedência project-config.yaml → overrides; artefato é a autoridade, nunca declarado)
Protocolo de retrieval	manifesto/pack primeiro; proibida ingestão exaustiva ("Glob all → classificar tudo"); consulta dirigida (grep por símbolo/padrão) em vez de leitura aberta; nunca cat de arquivo grande
Orçamento de contexto	~106K úteis por processo; se a fatia excede, degradar para query e registrar, nunca truncar em silêncio
Protocolo de handoff	consumidor extrai as linhas/valores que precisa (grep/faixa), não relê o artefato inteiro — generaliza o artifact-map.yaml da F8
Protocolo do shared-context.md	pequeno e curado: status + índice de artefatos + decisões. Passar paths, nunca conteúdo
Batch write	todo output contract numa única chamada powershell (shared/batch-write-protocol.md)
Guardrails comuns	read-only no legado; mascarar credenciais; propagar trace_id sem mutar; ast-raw/ é negado por hook — usar headroom_tool.py slice
Convenções de path	projects/{project_name}/outputs/{phase}/…
Resolução de linguagem	legacy_technology vem do project-config.yaml; nenhuma regra assume delphi/.net/java
Guardado por src/shared/utils/validate_language_agnostic.py --report (allowlist, não denylist — shared/dotnet-research-instructions.md legitimamente contém dotnet), rodando sobre AGENTS.md + .github/agents/*.agent.md. Escopo do lint nesta spec: só esses dois alvos.

A dívida já mapeada fica registrada na spec como follow-on, não é corrigida aqui: orchestrator-asis.md:2075 ## Delphi Backup Cleanup (MANDATORY when legacy_technology == delphi) (fase obrigatória do orquestrador travada numa linguagem) · asis-diagnostic/shared/delphi-patterns.md (arquivo por-linguagem dentro de shared/) · shared/backend-context-protocol.md (nome genérico, conteúdo .NET) · shared/mermaid-guardrails.md (32.982 chars, aplica a tudo, 5 menções a Delphi) · .github/instructions/ (253 KB, 100% FastQA) · 46 .md sob src/modules mencionando delphi.

.github/copilot-instructions.md permanece para o fluxo humano e para o bloco gerenciado do SpecKit (<!-- SPECKIT START/END -->, que /speckit.plan reescreve).

2. src/shared/tools/generate_agent_wrappers.py — NOVO
Alimentado por agent_registry.py (fonte canônica já existente — evita o 4º catálogo manual que já divergiu duas vezes no repo).

Emite .github/agents/ava-*.agent.md para os 107 agentes. É o mesmo padrão dos 75 SKILL.md atuais (~890 chars, ponteiro fino para a spec canônica) — agora com tools: enforçado e cobertura completa:

---
name: ava-asis-inventory
description: <do registry, pt-BR>
tools: ["view", "create", "edit", "glob", "grep", "powershell"]   # mapeado de allowed-tools
model: claude-sonnet-4
target: github-copilot
user-invocable: true
metadata: {version: "2.1.0", phase: "F1", module: "asis-diagnostic"}
---
# GERADO — não editar à mão. Fonte: src/modules/.../agents/inventory-asis.md
<!-- AGENTS-CORE:START --> …conteúdo de AGENTS.md… <!-- AGENTS-CORE:END -->
## Sua spec canônica
Read `src/modules/ava-fabric-agents/asis-diagnostic/agents/inventory-asis.md` e siga LITERALMENTE.
## Estratégia de contexto
<slice do AGENT_ARTIFACT_SLICE> · <output contract do ARTIFACT_CONTRACTS>
Regras impostas pelo M0: emitir tools: (não allowed-tools:), não emitir version: (vai em metadata:), mapear Bash→powershell, Read→view, Write→create, Glob→glob, Grep→grep (o TOOL_NAME_MAP já existe em agent_runner.py:81-109, hoje sem uso — mover para o gerador). Analíticos sem edit/create além do próprio contrato. Corpo < 30.000 chars.

Fecha a lacuna dos 32 agentes sem SKILL.md, hoje alcançáveis só por dispatch textual — que, conforme os logs, falha em silêncio (tool.execution_complete success:false, "Skill not found: ava-qa-orchestrator" → "caiu para execução direta").

Preflight: falhar se ~/.copilot/agents/ contiver nome colidente (precedência do dir de usuário).

3. src/shared/tools/context_pack.py — NOVO (o "shared context com memória")
Reusa headroom_context.build_agent_context(project, agent_id, language) (src/shared/tools/headroom/headroom_context.py:335+) — já existe e já devolve a fatia decodificada com tokens_estimated. O pack é a materialização em disco disso:

projects/{p}/outputs/.context/{agent_id}/context-pack.md

# Context Pack — ava-asis-inventory
run_id … | project … | language … | tokens: 11.240 / 106.551 úteis

## 1. Sua fatia (já decodificada do formato Headroom)
## 2. Índice de artefatos upstream (~1 KB — paths + seções, NÃO conteúdo)
## 3. Como consultar o que não está aqui
   python src/shared/tools/headroom/headroom_tool.py slice -p {p} --artifact <n> …
   > ast-raw/ é negado pelo hook preToolUse.
## 4. Seu output contract (do artifact_gate) — o que falta
## 5. Estado da fase (extrato curado do shared-context.md)
Gate de orçamento: se a fatia excede o budget, degrada para query-only (seção 1 vira contagens + instruções) e registra a decisão no pack — nenhum agente recebe pack maior que a janela. É o gate que falta hoje (o runner só imprime ⚠).
Determinístico: mesmo input → pack byte-idêntico (ordenação por chave, nada de set() sem sorted()).
agent_runner.build_envelope() (agent_runner.py:238) passa a apontar para o pack em vez de listar caminhos de compressed/*.json.
Novo protocolo compartilhado src/modules/ava-fabric-agents/shared/context-pack-protocol.md: pack presente → autoridade; ausente → ## Input Contract clássico (degradar, nunca quebrar).
shared-context.md passa a ser índice, não depósito — regra em AGENTS.md, verificada por tamanho no CI.
Fora de escopo (spec 034): knowledge graph, ast_index.py, FTS5/BM25, write-back F2. A camada de consulta usada aqui é headroom_tool.py slice|decode, que já existe.

4. .github/hooks/ava-guardrails.json + src/shared/tools/hooks/pretooluse_guard.py — NOVOS
Primeira vez que o LARGE ARTIFACT PROTOCOL vira regra executável:

{"permissionDecision": "deny",
 "permissionDecisionReason": "Artefato AST fora do context pack. Use: headroom_tool.py slice -p <proj> --artifact <n>"}
Nega leitura sob outputs/asis/ast-raw/ ou arquivo ≥ 200 KB. Necessário porque -C <REPO_ROOT> é obrigatório (as 105 specs usam paths repo-relativos) e portanto --add-dir não cerca nada — a árvore do repo já está liberada.

5. agent_runner.py — completar (arquivo já existe)
Item	Mudança
Context pack	chamar context_pack.build() antes do spawn; envelope aponta para o pack
Paralelismo	honrar max_parallel do DAG (hoje lido e ignorado); alinhar ao compression_max_workers do Headroom
Escada de retry	1 baseline · 2 novo --session-id + bloco de reparo (artifacts_missing + session.error.message + 3 últimos tool.execution_complete com success:false) · 3 degradar pack + recortar por bounded context · 4 só solution-*. Backoff 30→120s só para 429/5xx. Nunca para 404 (é config) nem para artefato-ausente (é prompt)
Budget	recalibrar: USABLE_CONTEXT=106.551 já está no runner; propagar para context_budget.py (400K/700K viram heurística de total de pipeline, não por agente)
Modo	ler execution_backend: inprompt|process do project-config.yaml; recusar rodar se inprompt
Limpeza	BENIGN_LOG_PATTERNS (já definido, sem uso) passa a filtrar os 3 ruídos conhecidos do M0
6. pipeline-dag/F1.yaml — completar + teste anti-divergência
De 3 nós (wave2) para o DAG F1 completo, extraído das tabelas ## Agent Team / Artifact Output Contract per Agent de orchestrator-asis.md.

Risco #1 do repo — 4ª fonte de verdade. Já existem três espelhos manuais que divergiram (ARTIFACT_CONTRACTS, AGENT_ARTIFACT_SLICE, AGENT_CATALOG — o agent_registry.py nasceu porque "52 de 101 agentes ausentes, 18 versões divergentes"). Mitigação obrigatória:

tests/test_pipeline_dag.py — aciclicidade + dag.nodes ≡ ARTIFACT_CONTRACTS.keys() ≡ agent_registry.catalog() + dag.slice ≡ AGENT_ARTIFACT_SLICE (hoje validate_dag só checa presença, não conteúdo) + todo nó tem slice, timeout_s e artefatos.

7. orchestrator-asis.md — 193.848 → ~15 KB
Fica só com o que só ele pode fazer: resolver project-config.yaml / legacy_technology / scope_modules / trace_id; Step 0 (AST via run_ast_analysis.py) e o Solution Agent Gate (regra 9 do DAG Event Protocol — HALT total em falha ou implementation_status == STUB); uma chamada powershell: python src/shared/tools/agent_runner.py --project P --phase F1; ler o relatório do runner, aplicar os gates de fase, consolidar master-report.md + Summary.

Saem do prompt e viram F1.yaml: ## Execution DAG (L99), ## DAG Event Protocol (L165, as 14 regras + dispatch_schedule), a tabela Artifact Output Contract per Agent, e a tabela de roteamento SOLUTION_AGENTS hoje duplicada como comentário YAML (passa a vir de agent_registry.py). As regras 10/11/13/14 (Context Budget Gate, Dispatch Guard, artifacts_confirmed medido, Wave Guard) deixam de ser prosa e viram código no runner — que já faz gate, budget e verificação por artefato. Resolve o cap de 30 KB sem "progressive disclosure" genérico. Mesmo tratamento depois para security-orchestrator-asis.md (114.996 chars) e os orquestradores F2/F4/F5/F6.

8. Bugs no caminho exato desta mudança (corrigir junto)
projects/MeuERP-002/context/project-config.yaml:9 — malformada: scope_modules foi engolido pelo comentário de trace_id; a chave não existe → filtro de escopo inativo.
quality_gates: declarado duas vezes (L226 e L332) — YAML mantém o segundo, o primeiro some em silêncio. Mesmo bug em projects/_template (L330/L599).
run_ast_analysis.py::_ensure_manifest_metrics grava tokens_out = len(text) sob files[], enquanto context_budget.py lê artifacts[].tokens_out → budget lê 0 e libera tudo.
Contradição viva: verify_agent_observability.py (+ CI validate-agent-observability.yml) exige os blocos pipeline_observer track à mão, mas o wrapper e o envelope mandam o agente não executá-los. Correção: tornar pipeline_observer track idempotente por (run_id, agent_id, attempt) e a regra do verificador virar "agente migrado pode omitir", no mesmo commit.
9. Documentação SpecKit
specs/033-agent-isolation-context-engineering/ (033 é o próximo número; templates efetivos são os de .specify/templates/overrides/):

Arquivo	Base
spec.md	overrides/spec-template.md — seções 1–8 + ## Success Criteria; Change Type: add-new + modify-existing
plan.md	overrides/plan-template.md — ## Summary, ## Constitution Check (Artigos I–XI + Quality Gate Check), seções 1–10
tasks.md	overrides/tasks-template.md — 7 categorias, numeração N.N (não T001)
research.md	absorve docs/copilot-cli-runtime-facts.md (M0) + as 5 técnicas de Context Engineering
quickstart.md	roteiro de verificação end-to-end
contracts/agent-wrapper.schema.json, contracts/context-pack.schema.md	frontmatter válido do .agent.md e formato do pack
checklists/requirements.md	checklist-template.md — CHK-C01…C07 verbatim primeiro
Depois: docs/plan/{escala-esteira,contex-eginerring-github-copilot}.md passam a apontar para a spec como fonte única; memory-archotecture-* fica reservado para a spec 034.

Tensão constitucional a declarar em Complexity Tracking (não ignorar): o Artigo II exige frontmatter com apenas name/version/description/allowed-tools, mas o schema do Copilot CLI descarta version e allowed-tools e exige tools. Posição desta spec: o Artigo II governa as specs canônicas em src/modules/.../agents/*.md (inalteradas); os .github/agents/*.agent.md são artefatos gerados governados pelo schema do CLI. Registrar em ## 9. Complexity Tracking e propor a emenda de escopo do Artigo II na spec.

Sequência de implementação
Marco	Entrega	Critério de aceite
M1	AGENTS.md + generate_agent_wrappers.py + 107 wrappers + tests/test_agent_wrappers.py	copilot lista os 107 em /agent; zero unknown fields ignored no --log-level warning; todo corpo < 30.000 chars; bloco AGENTS-CORE idêntico a AGENTS.md; lint language-agnostic em --report
M2	context_pack.py + context-pack-protocol.md + hook preToolUse	agente-sonda tentando view em ast-raw/*.json é negado (hook.start/hook.end no events.jsonl); pack de todo agente F1 ≤ budget; dois builds seguidos byte-idênticos
M3	F1.yaml completo + test_pipeline_dag.py + paralelismo + retry + execution_backend	--dry-run imprime os comandos exatos; teste falha se DAG divergir de ARTIFACT_CONTRACTS/AGENT_ARTIFACT_SLICE/agent_registry
M4	orchestrator-asis.md ~15 KB + test_agent_body_size.py + bugs §8 + track idempotente	F1 real em MeuERP-002 fecha o F1_OUTPUT_CONTRACT (12/12 paths obrigatórios; 19/19 artefatos, era 11/19); zero session.compaction_start/truncation entre os nós; CI verde
M5	Docs SpecKit 033 completos + docs/plan/* redirecionados	/speckit.analyze sem inconsistências
—	(follow-on) F2–F8 · spec 034 memory graph · limpeza language-agnostic do repo	fora desta spec
Ordem obrigatória: M1 → M2 → M3 → M4. M5 pode correr em paralelo a partir do M2.

Verificação end-to-end
# 0. Preflight — formato dos wrappers (o que o M0 provou que quebra em silêncio)
python src/shared/tools/generate_agent_wrappers.py --check      # exit 1 se drift vs agent_registry
python -m pytest tests/test_agent_wrappers.py tests/test_agent_body_size.py -q
copilot --log-level warning -p "list agents" --no-ask-user      # zero "unknown fields ignored"

# 1. AGENTS.md language-agnostic
python src/shared/utils/validate_language_agnostic.py --report --paths AGENTS.md .github/agents

# 2. DAG não divergiu das 3 fontes existentes
python -m pytest tests/test_pipeline_dag.py -q

# 3. Context pack — orçamento e determinismo
python src/shared/tools/context_pack.py --project MeuERP-002 --phase F1 --json
python src/shared/tools/context_pack.py --project MeuERP-002 --agent ava-asis-inventory > a.md
python src/shared/tools/context_pack.py --project MeuERP-002 --agent ava-asis-inventory > b.md
Compare-Object (Get-Content a.md) (Get-Content b.md)            # sem saída = OK

# 4. Runner — dry-run primeiro (não gasta inferência), depois real
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --dry-run
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --json

# 5. ISOLAMENTO — a prova central. Por nó, em ~/.copilot/session-state/<sid>/events.jsonl:
#    session.shutdown.systemTokens ≈ 13.449  e  currentTokens << 128.000
#    ZERO session.compaction_start / session.truncation
Get-ChildItem projects/MeuERP-002/outputs/.runs/*/logs -Recurse -Filter events.jsonl |
  ForEach-Object { Get-Content $_ | Select-String 'compaction_start|truncation' }   # vazio = OK

# 6. Hook — enforcement real, não prosa
copilot -p "view projects/MeuERP-002/outputs/asis/ast-raw/delphi/compressed/04_database_schemas.json" `
        --agent ava-asis-inventory --no-ask-user                # deve ser NEGADO pelo hook

# 7. Gate + paridade de artefatos
python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py --project MeuERP-002 --json
#    19/19 do F1_OUTPUT_CONTRACT; estrutura equivalente a
#    C:\Desenv\factory_apps\ava-fabric-apps-agents\projects\Meu-ERP\outputs\asis\

# 8. Modo de execução INALTERADO (a restrição do usuário)
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat   # sem diff
.\copilot-cli-headroom.bat        # humano abre igual; chama o orquestrador F1 igual

# 9. Caminho nativo (híbrido) continua funcionando
copilot   # /agent → escolher ava-asis-inventory → roda em janela própria

# 10. CI
python -m pytest tests/tools tests/utils -q
python src/shared/utils/verify_agent_observability.py
Arquivos
Criar — AGENTS.md · src/shared/tools/generate_agent_wrappers.py · src/shared/tools/context_pack.py · src/shared/tools/hooks/pretooluse_guard.py · .github/hooks/ava-guardrails.json · .github/agents/ava-*.agent.md (107, gerados) · src/modules/ava-fabric-agents/shared/context-pack-protocol.md · src/shared/utils/validate_language_agnostic.py · tests/{test_agent_wrappers,test_pipeline_dag,test_agent_body_size}.py · specs/033-agent-isolation-context-engineering/{spec,plan,tasks,research,quickstart}.md + contracts/ + checklists/requirements.md

Modificar — src/shared/tools/agent_runner.py (pack, paralelismo, retry, execution_backend) · src/shared/data/pipeline-dag/F1.yaml (DAG completo) · src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md (→ ~15 KB) · .../utils/context_budget.py (limiares viram heurística de pipeline) · .../utils/run_ast_analysis.py (bug tokens_out) · src/shared/tools/pipeline_observer.py (track idempotente) · src/shared/utils/verify_agent_observability.py (agente migrado pode omitir) · .azure-pipelines/validate-agent-observability.yml (paths + coletar tests/) · projects/MeuERP-002/context/project-config.yaml e projects/_template/... (bugs §8 + execution_backend: process) · docs/plan/*.md (redirecionar para a spec)

Intocados (por contrato) — copilot-cli-headroom.bat · copilot-cli-v1.bat · .github/skills/** (os 75 SKILL.md continuam sendo a entrada humana) · .github/copilot-instructions.md (fluxo humano + bloco gerenciado do SpecKit) · .github/agents/speckit.*.agent.md · src/modules/.../agents/*.md exceto orchestrator-asis.md · master-orchestrator.md (fora de escopo, conforme decisão anterior)

Rollback — parar de invocar agent_runner.py no orquestrador; execution_backend: inprompt restaura o caminho atual bit a bit.