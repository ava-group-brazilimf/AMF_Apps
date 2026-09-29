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
Plano — Context Engineering em escala para os agentes .md no GitHub Copilot CLI
Context
A esteira AVA Fabric (42 agentes .md, hoje crescendo para 100+) degrada quando o legado escala para 300K–1.5M LOC: a janela de contexto satura, os agentes falham em capturar informação, alucinam ou não geram os documentos esperados.

Causa-raiz (confirmada na análise do repo): todo agente analítico faz ingestão exaustiva — "Glob all .pas/.dfm/.dpr → classificar todos os arquivos" (step-02-code-analysis.md, critério "Todos os arquivos do escopo classificados"). Não há uma única menção a chunking, RAG, retrieval, sumarização, compactação, orçamento de tokens ou amostragem em ~80 arquivos .md. O estado é um blackboard em disco (shared-context.md) relido "full content", sem compactação. A única técnica de redução existente (grep-extract do artifact-map.yaml) está isolada na fase F8. O escopo só é filtrado por scope_modules manual (default "all").

Objetivo: aplicar Context Engineering ao formato .md e adotar os custom agents nativos do GitHub Copilot CLI (cada sub-agente com janela de contexto própria) para executar cada agente isolado, sem perda de contexto nem de informação relevante. As regras são independentes da superfície de execução — valem também para o motor LangGraph em engine/.

Decisões do usuário: (1) isolamento via custom agents nativos (.github/agents/*.agent.md); (2) retrieval file-based (grep/glob + manifesto); (3) escopo = padrão de referência (F1, 8 agentes) + AGENTS.md + guia em docs/, replicável aos 42→100+.

As 5 técnicas de Context Engineering mapeadas ao formato .md
Os quatro pilares (Write / Select / Compress / Isolate) adaptados a agentes .md no Copilot CLI:

Técnica	O que muda no formato .md	Onde entra
1. Isolate — offloading por sub-agente	Cada agente vira custom agent nativo com janela própria. O orchestrator delega (tool agent) o trabalho pesado; a janela do orchestrator só vê resumos + paths, nunca o 1.5M LOC.	.github/agents/*.agent.md; orchestrator com tools: [agent, read, search]
2. Select — retrieval "just-in-time"	Trocar "Glob all + classificar tudo" por: (a) 1º passo barato gera manifesto/índice; (b) agentes leem o manifesto e recuperam só as fatias relevantes via search (Grep/Glob) + leitura por faixa de linhas. Nunca cat de arquivo grande inteiro.	novo ava-repo-manifest; bodies "retrieval-first"
3. Compress — redução / compactação	Cada agente emite resumo estruturado compacto (o Output Contract). Generalizar o padrão grep-extract do artifact-map para todo handoff: o consumidor puxa só as linhas/valores que precisa. Map-reduce hierárquico: relatório parcial por módulo → redutor → master. Orçamento de tokens por agente.	AGENTS.md (protocolo de extract) + bodies
4. Write — memória externa em disco	Manter shared-context.md pequeno e curado (status + índice de artefatos + decisões); nunca despejar conteúdo nele. Passar paths, não conteúdo (já é convenção — reforçar). Estado grande dividido em notas por-módulo + manifesto.	shared-context.md, outputs/asis/_manifest/
5. Chunk — partição por bounded-context (map-reduce)	Fan-out de um sub-agente por módulo/bounded-context (usando scope_modules alimentado pelo manifesto), cada um com contexto limitado ao seu módulo. Priorização por risco/complexidade (output do inventory realimenta a ingestão: módulos complexos → análise mais profunda).	orchestrator + manifesto
Query engineering (transversal): os agentes fazem perguntas dirigidas (grep por símbolos/padrões: CREATE PROCEDURE, TForm, strings SQL) em vez de leituras abertas. Dedup: guardrails/persona/convenções repetidos migram para AGENTS.md (carregado globalmente pelo Copilot CLI), mantendo cada .agent.md enxuto (< limite de 30K chars) e as regras aplicadas em toda a esteira.

Modelo de execução no GitHub Copilot CLI
Custom agents nativos (formato oficial): arquivos .agent.md em .github/agents/ (projeto) — precedência sobre ~/.copilot/agents/ (usuário). Frontmatter YAML:

---
name: ava-asis-inventory
description: Inventário quantitativo (LOC, complexidade, acoplamento) do legado. # required — dirige seleção por inferência
tools: [read, search, execute]     # analíticos: SEM edit. Coder agents: + edit
model: claude-sonnet-5             # análise pesada → modelo forte; simples → barato
target: github-copilot
user-invocable: true
---
# corpo = system prompt (máx 30.000 chars): dispatcher fino + estratégia de contexto
Execução isolada de cada agente (2 modos):
Programático, isolamento máximo (1 processo por agente): copilot --agent ava-asis-inventory --prompt "...".
Interativo: /agent (picker) ou "Use the ava-asis-inventory agent on ...".
Orchestrator → sub-agentes: o orchestrator recebe o tool agent e delega cada fase a um sub-agente, que roda em janela isolada e devolve só um resumo + paths. É o modelo atual (orchestrator→time), agora com isolamento real de contexto — resolve diretamente o overload.
Salvaguardas nativas: auto-compactação a 95% do limite e "persistent codebase memory" (Pro/Pro+) — usar como rede de segurança, não como estratégia.
É preciso instruir os .md para o CLI? Sim, o mínimo: (a) formato — converter para .agent.md com description (obrigatório) + tools; (b) corpo — diretrizes de contexto (retrieval-first, orçamento, escrever resumo em disco, orchestrator delega via agent). As regras comuns ficam em AGENTS.md (sem duplicar em cada agente).
Mudanças concretas (escopo de referência = F1 + guia)
1. AGENTS.md (raiz do repo) — carregado globalmente pelo Copilot CLI. Concentra (dedup): convenções de path/projeto, protocolo de retrieval (manifesto-first, nunca ingestão exaustiva, orçamento de tokens por agente), protocolo de handoff por extract (grep/regex em vez de "read entire file"), protocolo do shared-context.md (pequeno, só índice), e guardrails comuns (read-only no legado, mascarar credenciais, propagar trace_id).

2. .github/agents/ — 8 agentes F1 como .agent.md (dispatchers finos que apontam para o domínio em src/modules/.../agents/*.md — preserva fonte única — e aplicam as regras do AGENTS.md):

ava-repo-manifest.agent.md — NOVO 1º passo barato: varre o legado com Bash/Grep/Glob (wc, find, contagem por extensão/módulo, entrypoints, SPs) e grava outputs/asis/_manifest/ (file-tree, LOC por arquivo/módulo, mapa de módulos, hotspots). tools: [read, search, execute].
ava-asis-orchestrator.agent.md — tools: [agent, read, search]; corpo: ler manifesto → particionar por módulo/risco → delegar cada análise a sub-agente → agregar resumos (não conteúdo) no master report.
ava-asis-solution-delphi / inventory / db-analyzer / security-review / documentation / gaps-risks — tools: [read, search, execute], sem edit; corpo: retrieval-first (ler manifesto, recuperar fatias, faixas de linha), emitir resumo estruturado do Output Contract.
3. Retrieval-first no workflow F1 — ajustar step-02-code-analysis.md e o body dos agentes analíticos em src/modules/.../agents/*.md: substituir "Glob all → classificar todos" por "ler manifesto → recuperar/priorizar → analisar por fatia com orçamento". Adicionar fase manifest (raiz) ao workflow.md antes de code-analysis/db-analysis/security/inventory.

4. Generalizar o extract-map — pequeno context-map.yaml (inspirado no artifact-map.yaml) declarando, por artefato de handoff, o extract que o consumidor deve usar (regex/grep/faixa) em vez de reler o arquivo inteiro.

5. docs/context-engineering-copilot-cli.md — guia que responde às 3 perguntas do usuário: diagnóstico do overload; catálogo das 5 técnicas com exemplos aplicados ao .md; e o passo-a-passo de execução isolada no Copilot CLI (--agent, /agent, orchestrator com tool agent, o que colocar no .agent.md vs no AGENTS.md).

Compatibilidade: os SKILL.md em .claude/skills e .github/skills permanecem para o Claude Code; os novos .github/agents/*.agent.md são o caminho nativo do Copilot CLI. src/modules/.../agents/*.md continua fonte única do conteúdo de domínio.

Verificação (end-to-end)
Estrutura/frontmatter: copilot lista os 8 agentes (/agent); cada .agent.md tem description e tools válidos e body < 30K chars.
Isolamento de contexto: rodar o orchestrator num legado de teste e confirmar (via eventos/uso de tokens do CLI) que a janela do orchestrator permanece pequena enquanto os sub-agentes fazem a leitura pesada em janelas próprias — o overload não reaparece.
Retrieval-first (não-degradação): gerar um legado sintético grande (script criando N arquivos até ~centenas de milhares de LOC) e rodar copilot --agent ava-asis-inventory --prompt ...; confirmar que o agente lê o manifesto e recupera fatias (não faz cat do repo inteiro) e ainda produz inventory-report.md completo — sem alucinar/omitir.
Map-reduce por módulo: confirmar que o orchestrator particiona por módulo (do manifesto) e que cada sub-agente gera relatório parcial, consolidados no master report sem estourar contexto.
Handoff por extract: um agente downstream (ex.: gaps-risks) consome só as linhas extraídas (grep) dos artefatos upstream, não o conteúdo inteiro.
Paridade: comparar os artefatos gerados com os de referência em projects/Meu-ERP/outputs/asis/ (estrutura/seções equivalentes).
Rollout (42 → 100+ agentes)
F1 (este plano) valida o padrão: AGENTS.md + .agent.md finos + manifesto + retrieval-first + extract-map.
Replicar o molde para F2–F8 (mesmo frontmatter, mesmos protocolos globais no AGENTS.md — só o body de domínio muda).
Gerar os .agent.md a partir de src/modules/.../agents/*.md (fonte única) por script, evitando manutenção tripla (.claude/skills, .github/skills, .github/agents).
Escala extrema (1.5M+ LOC): plugar um MCP retrieval server (embeddings/BM25) como tool search_code por-agente (mcp-servers no frontmatter) sem mudar os bodies — camada opcional prevista, fora do escopo desta referência.