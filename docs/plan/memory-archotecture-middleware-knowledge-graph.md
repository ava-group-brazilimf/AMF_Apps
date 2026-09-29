> ℹ️ **RESERVADO para a spec 034.**
>
> A spec 033 entrega o *context pack determinístico* (fatia orçada + índice de artefatos
> upstream, em disco). O knowledge graph descrito aqui é a evolução do retrieval e pluga
> **sem mudar os agentes** — o pack é um arquivo, e trocar quem o produz é invisível para
> quem o consome. Ver `specs/033-.../research.md` § 2.1.

---

Ready for review
Select text to add comments on the plan
Memory Architecture Middleware — Knowledge → Graph → Retrieval (F1 AS-IS + F2 TO-BE)
Context
Hoje o caminho entre a extração AST e os agentes especializados é estático: run_ast_analysis.py grava 10 JSONs monolíticos em outputs/asis/ast-raw/{lang}/compressed/, e cada agente recebe uma fatia fixa declarada em AGENT_ARTIFACT_SLICE (context_budget.py:79-112). Isso resolveu a causa-raiz RC-1 da ISSUE-002 (761 k tokens por runSubagent), mas tem três limites estruturais:

Granularidade de arquivo, não de fato. O ava-asis-db-analyzer recebe 03+04+05 inteiros mesmo quando só precisa das tabelas de um bounded context. Daí o LARGE ARTIFACT PROTOCOL (extração seletiva via Bash+Python, com caps de 500 regras / 200 forms / 300 procs) — uma gambiarra de leitura espalhada por cada agente.
Não há relações consultáveis. As arestas existem só implicitamente: module_partitioner.py monta um grafo uses com igraph+Leiden, usa para particionar e descarta; sql_ir_generator.py infere FKs e grava sql-ir.json. Ninguém consegue perguntar "quais regras tocam a tabela CONTAS_PAGAR".
Zero rastreabilidade F1→F2. A Fase 2 lê os .md da Fase 1 como texto. Não há vínculo verificável entre uma decisão TO-BE (ADR, bounded context, endpoint) e a evidência AS-IS que a originou.
Objetivo: inserir um middleware determinístico de 3 camadas entre o AST e os agentes, ativo em F1 e F2, que (a) normaliza os artefatos em unidades de conhecimento endereçáveis com proveniência, (b) materializa o grafo tipado que hoje é jogado fora, e (c) entrega a cada agente um context pack montado por travessia de grafo + ranking lexical, dentro do orçamento de tokens.

Decisões tomadas (confirmadas com o requisitante)
Decisão	Escolha
Backend Knowledge/Graph	Arquivos + SQLite (knowledge-units.jsonl + graph.json + memory.sqlite FTS5). Zero serviço novo.
Estratégia de Retrieval	Determinística: travessia de grafo + BM25. Sem embeddings, 100 % reprodutível.
Escopo	F1 e F2 juntos, incluindo write-back TO-BE e arestas derived_from.
Interface com os agentes	Arquivo em disco + Read — orquestrador gera memory/packs/{agent-id}.json e passa o caminho no dispatch.
Princípios invioláveis (herdados do repo)
Degradar, nunca quebrar. Todo ponto de entrada segue o padrão de _probe_headroom() / _load_context_budget() / o try/except em volta do ModulePartitioner (run_ast_analysis.py:980-999): falha de memória → aviso + comportamento atual.
Filesystem é a única evidência aceita. Coerente com artifact_gate.py; nada de estado em processo.
Fonte canônica única. AGENT_ARTIFACT_SLICE continua sendo a autoridade da fatia — a Retrieval Layer a usa como seed, nunca a duplica (mesma regra que headroom_context.py já respeita via importlib).
Um dispatch, uma chamada Bash. A geração de packs é batched por wave, pelo mesmo motivo de artifact_gate --wave (ISSUE-002 § RC-3: N chamadas serializam a wave).
Estilo do repo. Docstrings em pt-BR com preâmbulo "por que isto existe", stdlib primeiro, imports pesados defensivos, sys.stdout.reconfigure(encoding="utf-8") no topo (Windows).
Arquitetura
Onde vive o código
src/shared/tools/memory/ — e não asis-diagnostic/utils/, porque a camada serve F1 e F2. src/shared/tools/ já é o lar das ferramentas cross-phase (agent_registry.py, pipeline_observer.py, headroom/); asis-diagnostic/utils/ é phase-scoped por convenção.

Arquivo	Camada	Responsabilidade
schema.py	—	Ontologia: tipos de nó/aresta, dataclass KnowledgeUnit, cunhagem determinística de uid. Fonte única da ontologia.
knowledge_builder.py	Knowledge	Lê os 10 artefatos AST + sql-ir.json + business-rules-catalog.json → knowledge-units.jsonl.
graph_store.py	Graph	Deriva arestas tipadas → graph.json; carrega em igraph sob demanda; API de travessia. Reutiliza as comunidades Leiden de module-partition.json.
index_store.py	Graph/Retrieval	memory.sqlite: tabelas units, edges + virtual table FTS5 units_fts. sqlite3 puro.
retrieval.py	Retrieval	retrieve(project, agent_id, phase, budget, scope) → context pack. Seed → expansão → BM25 → corte por orçamento.
tobe_writer.py	Knowledge (F2)	Lê artefatos TO-BE → unidades F2 + arestas derived_from apontando para uids F1.
memory_cli.py	—	CLI única: build, graph, index, retrieve, writeback, stats, verify.
__init__.py	—	Reexporta build_asis_memory, build_tobe_memory, retrieve.
Onde vivem os dados
projects/{p}/outputs/asis/memory/          # F1 — escrito pelo Step 0.5
├── knowledge-units.jsonl                  # 1 unidade por linha
├── graph.json                             # {"nodes":[uid,...], "edges":[...]}
├── memory.sqlite                          # índice FTS5 + arestas (derivado, regenerável)
├── manifest.json                          # counts, hashes, run_id, schema_version
└── packs/{agent-id}.json                  # context packs gerados por wave

projects/{p}/outputs/tobe/memory/          # F2 — escrito pelos hooks de write-back
├── knowledge-units.jsonl
├── graph.json                             # nós F2 + arestas derived_from → uids F1
├── memory.sqlite
├── manifest.json
└── packs/{agent-id}.json
O retrieval de F2 abre os dois stores: F1 read-only + F2. memory.sqlite é derivado — apagá-lo e rodar memory_cli.py index reconstrói.

Layer 1 — Knowledge: a unidade de conhecimento
O envelope AST já entrega identidade e proveniência estáveis (source_ref{file,line,containing_type,containing_member}). A camada só normaliza:

{
  "uid": "f1:rule:01#a3f9c1d2",
  "phase": "F1",
  "type": "rule",
  "subtype": "validation",
  "name": "ValidaCPFCliente",
  "module": "Financeiro",
  "artifact": "01_business_rules",
  "text": "CPF deve ter 11 dígitos e DV válido antes de gravar",
  "tokens": 87,
  "source_ref": {"file": "uCliente.pas", "line": 412,
                 "containing_type": "TCliente", "containing_member": "Validar"},
  "attrs": { }
}
uid determinístico: {phase}:{type}:{artifact_num}#{sha1(natural_key)[:8]}, onde natural_key é normalizada (lowercase, path basename). Reextrair o AST não muda o uid — é o que faz as arestas derived_from de F2 sobreviverem a um re-run de F1.
Tipos de nó: unit, form, rule, db_rule, table, column, relationship, procedure, integration, api, test, module (F1); bounded_context, adr, entity_tobe, endpoint, wave, risk (F2).
tokens é pré-calculado no build — é o que permite o corte por orçamento no retrieval sem recontar.
Fontes por tipo:

Tipo	Artefato de origem
unit, module	08_code_overview + module-partition.json
form	02_form_business_rules
rule	01_business_rules + business-rules-catalog.json (paridade obrigatória)
db_rule, procedure	03_database_rules, 05_procedures (assinatura + resumo; nunca corpo completo)
table, column, relationship	04_database_schemas + sql-ir.json
integration, api	06_integrations, 07_apis
test	09_test_coverage
Invariante de paridade: count(type=rule) deve bater com business-rules-catalog.json.counts.total. Divergência → verify falha com exit 1, mesmo contrato de business_rules_catalog_generator.py.

Layer 2 — Graph Memory
graph.json guarda arestas tipadas com evidência:

{"src": "f1:unit:08#1a2b3c4d", "dst": "f1:table:04#5e6f7a8b",
 "type": "reads_table", "weight": 1.0, "evidence": "03_database_rules"}
Grupo	Tipos de aresta
Estrutural F1	uses, belongs_to_module, declares_form, validates, reads_table, writes_table, calls_procedure, has_column, references (FK), exposes_api, integrates_with, covered_by_test
F2	maps_to_bc, decided_by (→ ADR), realizes (endpoint → regra), derived_from (unidade F2 → uid F1)
Reuso, não reimplementação. As arestas uses e a atribuição belongs_to_module vêm de module-partition.json, já produzido pelo Leiden em module_partitioner.py. graph_store.py não roda Leiden de novo; consome o resultado. Se module-partition.json faltar, os nós ficam sem module e o retrieval degrada para escopo global.
igraph é opcional. A travessia BFS com profundidade limitada é stdlib (adjacência em dict). igraph só é carregado — defensivamente — para métricas de centralidade opcionais no ranking.
Layer 3 — Retrieval
retrieve(project, agent_id, phase, budget_tokens, scope):

Seed — AGENT_ARTIFACT_SLICE[agent_id] define os artefatos-semente; os nós daqueles artefatos entram no conjunto inicial. Agente desconhecido (fatia None) → pack vazio + known_agent: false, exatamente como build_agent_context() faz hoje.
Escopo — se scope-filter-manifest.json estiver ativo (scope_modules != "all"), filtra por belongs_to_module.
Expansão — BFS até max_traversal_depth (default 2) por tipos de aresta relevantes ao agente (mapa AGENT_EDGE_PROFILE em retrieval.py; ex.: db-analyzer → reads_table|writes_table|has_column|references|calls_procedure).
Ranking — BM25 via bm25() do FTS5 sobre os termos do perfil do agente. Nó-semente tem boost fixo; distância de travessia é penalidade. Fallback: se o SQLite do ambiente não tiver FTS5, cai para sobreposição de tokens em Python puro — mesma ordem determinística.
Corte — acumula por tokens até pack_token_budget, respeitando per_type_caps (herda os caps do LARGE ARTIFACT PROTOCOL: 500 regras / 200 forms / 300 db rules / 200 tabelas / 300 procedures).
Emissão — packs/{agent-id}.json:
{
  "schema_version": "1.0.0",
  "project": "MeuERP-002", "phase": "F1",
  "agent_id": "ava-asis-db-analyzer",
  "known_agent": true,
  "generated_from": {"seed_artifacts": ["03_database_rules","04_database_schemas","05_procedures"],
                     "edge_profile": ["reads_table","writes_table","has_column","references"],
                     "scope_modules": "all", "depth": 2},
  "budget": {"limit": 60000, "used": 41230, "truncated_types": {"procedure": 312}},
  "units": [ { /* KnowledgeUnit completa, com source_ref */ } ],
  "edges": [ { /* arestas entre as unidades incluídas */ } ],
  "fallback": null
}
Determinismo obrigatório: mesmo input → pack byte-idêntico. Ordenação de desempate por uid; nenhum set() iterado sem sorted().

Wiring — pontos de integração
1. run_ast_analysis.py — build (F1)
Após o SqlIrGenerator e antes de _validate_output (linha ~1000), mesmo padrão guardado dos outros dois pós-processadores:

if _memory_enabled(config):
    print("   ⏳ Building memory layer (knowledge + graph + index)...")
    try:
        from ava_memory import build_asis_memory
        build_asis_memory(project_name, language=language)
    except Exception as exc:
        print(f"   ⚠️  Memory build falhou: {exc} — prosseguindo.")
Nunca altera o exit code do AST.

2. context_budget.py — orçamento
AGENT_ARTIFACT_SLICE não muda (continua canônica). Acréscimos:

--memory: quando os packs existem, agents[].tokens passa a reportar o tamanho real do pack, não a soma dos artefatos.
execution_mode ganha curto-circuito: com memória ativa e pack ≤ inline_threshold, o modo permanece subagent mesmo com o total do projeto acima do limiar. É o ganho central do middleware — o bc_scoped deixa de ser necessário para projetos grandes.
Novo campo memory: {enabled, units, edges, packs_present} no JSON.
3. headroom_context.py — montagem de contexto
build_agent_context(project, agent_id, language, *, include_payloads=True, use_memory=None). use_memory=None lê memory.enabled do project-config.yaml. Ativo → delega para retrieval.retrieve() e devolve o pack; inativo ou falho → comportamento atual, verbatim. A assinatura existente continua válida; nenhum chamador quebra.

4. artifact_gate.py — gating
Novo modo --memory-status --json, devolvendo {ready, units, edges, packs: {agent_id: bool}, stale: bool} (stale = manifest.run_id ≠ run_id do AST atual). check_wave() passa a incluir memory_ready no retorno, para o orquestrador decidir entre passar context_pack ou cair no contrato de input clássico. ARTIFACT_CONTRACTS não muda — memória não é entregável de agente.

5. orchestrator-asis.md (F1)
Novo Step 0.5 — Memory Build, logo após o Step 0 (AST): uma chamada Bash para memory_cli.py build --project {p}. Gate não-bloqueante: falha → registrar memory_enabled=false para o run e seguir com o slicing de hoje.
Antes de cada wave, uma única chamada batched (nunca uma por agente — Regra 3 / ISSUE-002 § RC-3): python src/shared/tools/memory/memory_cli.py retrieve --project {p} --wave phase_a_wave2 gerando todos os packs da wave de uma vez.
Payload de dispatch ganha context_pack: projects/{p}/outputs/asis/memory/packs/{agent-id}.json.
Waves espelhadas de artifact_gate.WAVES — memory_cli.py importa aquele dict por path em vez de copiá-lo.
6. orchestrator-tobe.md (F2)
Nova Fase 0-Mem — Memory Bootstrap, antes da Fase 0-Pre (linha 194): memory_cli.py retrieve --project {p} --phase F2 --wave tobe_bootstrap, lendo o store F1. Sob o Non-Blocking Gate Protocol: ausência do store F1 → SKIPPED + aviso + prossegue.
Write-back incremental após as fases que produzem conhecimento consumido adiante — Fase 0 (ADRs), Fase 1 (BC map + blueprint), Fase 1.5 (DB design), Fase 4.61 (OpenAPI por BC): memory_cli.py writeback --project {p} --phase F2 --source adr|bc|db|openapi Cada chamada emite unidades F2 e resolve derived_from contra os uids F1 (casamento por source_ref.file + nome normalizado; sem casamento → aresta omitida e contabilizada em manifest.unresolved_derived_from, nunca inventada).
Fases posteriores passam a recuperar do store F2 além do F1 — é assim que a Fase 5.2 (Regras de Negócio TO-BE) enxerga o que a Fase 1 decidiu sem reler os .md inteiros.
7. Novo protocolo compartilhado
src/modules/ava-fabric-agents/shared/memory-context-protocol.md — segue o formato dos irmãos em shared/. Define: o que é um context pack, como lê-lo, precedência (pack presente → autoridade; ausente → ## Input Contract clássico), e a proibição de reler repository_path (mantém o artifact-only-consumption-protocol). Os agentes consumidores ganham o include link-style [MemoryContext](../shared/memory-context-protocol.md).

8. project-config.yaml — feature flag
Bloco novo, documentado em projects/_template/context/.project-config-exemple-.yaml:

memory:
  enabled: true                  # default do repo: false (opt-in) — true em MeuERP-002 para validação
  graph:
    reuse_module_partition: true
    max_traversal_depth: 2
  retrieval:
    strategy: "graph+bm25"
    seed_from_artifact_slice: true
    pack_token_budget: 60000
    per_type_caps: {rule: 500, form: 200, db_rule: 300, table: 200, procedure: 300, column: 2000}
  writeback:
    f2_enabled: true
Ausência do bloco ≡ enabled: false ≡ esteira atual, bit a bit.

Dependências
Apenas stdlib (json, sqlite3, hashlib, csv, pathlib) + pyyaml, já exigido. python-igraph/leidenalg continuam sendo dependência do module_partitioner, e a memória só os toca de forma defensiva/opcional. Nenhuma dependência nova obrigatória. Nenhum serviço novo.

Sequência de implementação
Marco	Entrega
M1	schema.py + knowledge_builder.py + `memory_cli.py build
M2	graph_store.py + index_store.py + `memory_cli.py graph
M3	retrieval.py + memory_cli.py retrieve (por agente e --wave). Wiring em headroom_context.py e context_budget.py.
M4	Hook em run_ast_analysis.py, --memory-status em artifact_gate.py, memory-context-protocol.md, edições no orchestrator-asis.md.
M5	tobe_writer.py + memory_cli.py writeback, edições no orchestrator-tobe.md (Fase 0-Mem + 4 hooks de write-back), arestas derived_from.
M6	Suite memory_integrity, testes, specs/033-*, bloco no template de config e nos docs.
Ordem obrigatória: M1→M2→M3 são sequenciais; M4 e M5 dependem de M3; M6 fecha.

Arquivos a criar / modificar
Criar

src/shared/tools/memory/{__init__,schema,knowledge_builder,graph_store,index_store,retrieval,tobe_writer,memory_cli}.py
src/shared/tools/memory/tests/test_{schema,knowledge_builder,graph_store,retrieval,tobe_writer}.py
src/shared/tools/memory/README.md
src/modules/ava-fabric-agents/shared/memory-context-protocol.md
src/shared/checks/suites/memory_integrity.py
specs/033-memory-architecture-middleware/{spec,plan,research,data-model,quickstart,tasks}.md + contracts/{knowledge-unit,graph-edge,context-pack}.schema.json (mesma estrutura de specs/031-headroom-context-compression-proxy/)
Modificar

run_ast_analysis.py — hook de build guardado (~L1000)
context_budget.py — --memory, curto-circuito de execution_mode
headroom_context.py — use_memory em build_agent_context()
artifact_gate.py — --memory-status, memory_ready em check_wave()
orchestrator-asis.md — Step 0.5 + retrieve por wave + context_pack no dispatch
orchestrator-tobe.md — Fase 0-Mem + 4 hooks de write-back
.project-config-exemple-.yaml e projects/MeuERP-002/context/project-config.yaml — bloco memory:
src/shared/checks/cli.py — registrar a suite memory_integrity
.specify/memory/constitution.md — registrar a camada nas Output Path Conventions
Verificação end-to-end (projeto MeuERP-002)
# 1. AST + build automático da memória
python src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py --project MeuERP-002

# 2. Camadas Knowledge/Graph — contagens e paridade com o catálogo de regras
python src/shared/tools/memory/memory_cli.py stats  --project MeuERP-002
python src/shared/tools/memory/memory_cli.py verify --project MeuERP-002   # exit 1 se paridade quebrar

# 3. Retrieval — pack de um agente e de uma wave inteira
python src/shared/tools/memory/memory_cli.py retrieve --project MeuERP-002 --agent ava-asis-db-analyzer --json
python src/shared/tools/memory/memory_cli.py retrieve --project MeuERP-002 --wave phase_a_wave2

# 4. Determinismo — dois retrieves seguidos devem ser byte-idênticos
python src/shared/tools/memory/memory_cli.py retrieve --project MeuERP-002 --agent ava-asis-db-analyzer > a.json
python src/shared/tools/memory/memory_cli.py retrieve --project MeuERP-002 --agent ava-asis-db-analyzer > b.json
Compare-Object (Get-Content a.json) (Get-Content b.json)   # sem saída = OK

# 5. Orçamento com e sem memória (o modo deve melhorar, nunca piorar)
python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project MeuERP-002 --json
python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project MeuERP-002 --memory --json

# 6. Gate
python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py --project MeuERP-002 --memory-status --json

# 7. Integridade + testes
python -m src.shared.checks.cli --suite memory_integrity --project MeuERP-002
pytest src/shared/tools/memory/tests -q

# 8. Regressão do caminho degradado — com memory.enabled=false a esteira roda idêntica ao baseline
Critérios de aceite

verify passa: count(rule) == business-rules-catalog.json.counts.total; toda aresta tem as duas pontas existentes; toda unidade tem source_ref ou synthetic: true explícito.
Todo pack respeita pack_token_budget e reporta truncamento em vez de silenciar (regra "no silent caps").
Dois retrieves consecutivos produzem bytes idênticos.
memory.enabled: false → run_ast_analysis.py, context_budget.py e build_agent_context() produzem saída idêntica ao baseline atual.
F2: toda unidade TO-BE ou tem derived_from resolvido, ou está contabilizada em manifest.unresolved_derived_from — nunca uma aresta inventada.
F1 ponta a ponta em MeuERP-002 gera os 12 artefatos de F1_OUTPUT_CONTRACT com memory.enabled: true.