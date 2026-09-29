Ready for review
Select text to add comments on the plan
SpecKit F3S — reestruturação de saída e correções expostas pelo piloto
Context
A camada F3S foi entregue e executada. A execução real está em projects/nopcommerce-02-cli-ava/outputs/speckit/ — 26 arquivos: constitution, 7 specs, 7 plans, 7 tasks, compliance e traceability. Rodar os gates contra ela expôs defeitos dos dois lados, e o pedido de reestruturação chega junto.

O que foi pedido

Saída em {PROJECT_NAME}/outputs/tobe/speckit/ em vez de outputs/speckit/.
specs/ com uma pasta por spec no padrão SpecKit — 001-{nome}/ contendo spec.md, plan.md, tasks.md e demais arquivos.
Ajustar as referências nos agentes de codificação e nos demais consumidores.
O que o piloto revelou — medido, não inferido:

#	Achado	Consequência
A1	traceability.json usa chave raiz tasks, não entries; entradas sem group, target_stack, target_files, acceptance, source_anchor, verify_command	O fan-out da F4 é impossível — expand_foreach agrupa por group/target_stack. O razão de progresso também não pode ser criado
A2	task_id no formato TASK-BR-001, contra o T-XXX-000 do schema	Ids não casam entre artefatos
A3	tasks-*.md saiu como tabela Markdown compacta, não no bloco por task que o agente manda usar	O parser não reconhece nada: "nenhuma task declarada". A escolha do agente tem lógica — 175 tasks × 11 campos em blocos estoura o orçamento de saída
A4	total_tasks: 157 declarado, 175 reais	Contagem afirmada divergindo do real — o defeito que esta camada existe para eliminar, reaparecendo dentro dela
A5	0 de 7 specs contêm as 6 seções do readiness-gate C2	C2 continua reprovando; o produtor que criamos não satisfaz o consumidor
A6	spec-prototype.md tem 7 seções das 10 obrigatórias, e nenhum screen_id	CHK-PROTO-002/003 não têm o que casar
B1	CHK-SK-006 e CHK-SK-010 reportam OK com zero entradas	Passe vazio: a verificação anti-falso-positivo produzindo um falso positivo
B2	Chave raiz desconhecida vira [] em silêncio	O erro estrutural aparece como "nenhuma task", escondendo a causa
B3	O parser do screen-list.md assume ## Warnings antes do # Prototype Screen List; o arquivo real tem o H1 primeiro	Lê a tabela de warnings como inventário → "nenhuma tela included" em 15 telas válidas
B4	CHK-PROTO-006 não remove o base path /api/v1 de servers.url	17/17 falsos positivos
A1 é o mais grave: sem ele a F4 não expande, que era o ponto inteiro da Fase 3. B1 é o mais embaraçoso: um check que passa sem dados é exatamente o PASS (Simulated) que motivou o projeto.

A causa dominante de A1..A6 — a F3S rodou como um único despacho
execution-report_20260813_110523.md, linha da fase:

Fase	Agente	Skill	Input	Resp	OutMax	Tempo	Artefatos
F3S	ava-speckit-orchestrator	8KB	92.830	68.170	128.000	14,7 min	26
Skill de 8KB é o orchestrator-speckit.md sozinho. Os seis corpos de agente — constitution-agent.md, specification-agent.md, prototype-spec-agent.md, planning-agent.md, tasks-agent.md, compliance-agent.md, que é onde moram os contratos de formato, o schema da rastreabilidade, as 16 seções obrigatórias e os guardrails — nunca entraram em contexto. O modelo seguiu a tabela-resumo do orquestrador, não os contratos.

Isto é o mesmo defeito estrutural da F4 que a spec 039 documentou e corrigiu com foreach: o motor SDK carrega apenas o spec_path do orquestrador e proíbe tools, então toda cadeia declarada em prosa vira teatro. A F3S nasceu com o defeito que veio consertar.

Cada achado A é sintoma direto disso:

Achado	Explicação
A1, A2	tasks-agent.md não estava em contexto — o schema e o padrão de task_id também não
A3	175 tasks em blocos, mais 7 specs, 7 plans, constitution e compliance, tudo numa resposta: a tabela compacta foi economia de orçamento
A5, A6	as 6 seções do C2 e as 10 do protótipo estavam nos corpos que não carregaram
A4	contagem estimada em vez de contada, típico de geração sob pressão de orçamento
Não é falha de obediência do modelo. É a fase inteira comprimida numa chamada.

Mudança 1 — Caminho e layout
projects/{project_name}/outputs/tobe/speckit/
├── constitution.md
├── specs/
│   ├── 001-business-rules/   spec.md · plan.md · tasks.md
│   ├── 002-api/              spec.md · plan.md · tasks.md
│   ├── 003-api-map/          …
│   ├── 004-backlog/
│   ├── 005-waves/
│   ├── 006-test-cases/
│   └── 007-prototype/
├── traceability.json          ← autoridade legível por máquina
├── tasks-progress.json           ← razão, escrito só por ferramenta
├── ava-agents-progress.txt
├── compliance-report.md · compliance-status.json
└── execution-log.json
Cada pasta de feature aceita, opcionalmente, os arquivos que o SpecKit upstream já nomeia em .specify/scripts/powershell/common.ps1: research.md, data-model.md, quickstart.md, contracts/, checklists/. Obrigatórios são os três.

Numeração determinística. O registro feature fica em pipeline-dag/F3S.yaml, um por agente da wave2 — os números não são descobertos nem incrementados em runtime. Numeração inventada por LLM produziria pastas diferentes a cada execução e quebraria toda referência cruzada. Isto é o oposto do Get-HighestNumberFromSpecs do upstream, e a divergência é deliberada: aqui o conjunto de fontes é fechado e conhecido.

constitution.md fica na raiz de speckit/, não em memory/. Ela é referenciada por todos os agentes e por três coders; um nível a mais de caminho não compra nada.

Mudança 2 — traceability.json como autoridade
Hoje a máquina lê Markdown para descobrir tasks, e o Markdown mudou de forma. Isso inverte:

traceability.json carrega todos os campos que a maquinaria consome, com a raiz entries obrigatória e o schema em src/shared/schemas/speckit-traceability.schema.json.
tasks.md vira a visão humana, uma tabela derivada do JSON, dentro da pasta da feature.
As suítes leem o JSON; da tabela só conferem que não divergiu em task_id.
Parar de fazer parsing de Markdown no caminho crítico remove a classe inteira de fragilidade que A3 expôs — e resolve o conflito de orçamento de saída, porque a tabela é compacta por natureza.

Checks novos:

ID	Regra
CHK-SK-013	traceability.json valida contra o schema antes dos checks semânticos; chave raiz errada é erro nomeado, não zero silencioso
CHK-SK-014	toda specs/*/spec.md contém as 6 seções literais do readiness-gate C2
CHK-SK-015	todo task_id do JSON aparece na tabela de tasks.md da sua feature, e vice-versa
Checks corrigidos:

ID	Correção
CHK-SK-005	passa a ler o JSON; a contagem declarada é comparada com a real (mata A4)
CHK-SK-006 · 010	zero entradas reprova. Verificação sem dado não é verificação
CHK-PROTO-001	seleciona a tabela cujo cabeçalho contém Screen e Status, em vez de fatiar pelo H1 — é a regra defensiva que o próprio P2C §2.1 já prescreve
CHK-PROTO-006	remove o base path de servers.url antes de comparar o path
Mudança 3 — Fan-out da F3S nos dois runners
Sem isto, as correções de contrato da Mudança 4 não têm efeito nenhum: os corpos que as carregam continuam fora de contexto. Esta é a correção de causa; as demais são de conteúdo.

foreach ganha source: "dag", que expande um passo a partir das waves declaradas em pipeline-dag/{phase}.yaml — um despacho por agente, na ordem das waves, cada um com:

o corpo real do agente carregado pelo spec_path do registry (os 6 já resolvem);
a fatia de contexto que a própria wave declara em inputs;
o parâmetro da feature no prompt, para o agente saber qual fonte lhe cabe.
A F3S passa de 1 despacho para 11: constitution · 7 specs · plans · tasks · compliance. Cada um com orçamento de saída próprio, o que remove a pressão que produziu A3, A4, A5 e A6.

build_prompt ganha um segmento opcional nos dois runners:

@ava-speckit-specification | GS | project: {P} | feature: 001-business-rules
ava-pipeline-runner-cli.py precisa de três ajustes — é ele quem executou o piloto:

Local	Ajuste
PIPELINE	a entrada única de F3S é expandida pela função compartilhada que lê o F3S.yaml, como _apply_declared_inputs já faz com os manifestos — sem cópia manual da ordem
build_prompt	segmento feature: quando o passo o carrega
PHASE_ARTIFACT_CONTRACT["F3S"]	caminhos para tobe/speckit/…; plans e tasks deixam de existir como diretórios — passam a ser specs/*/plan.md e specs/*/tasks.md
PHASE_MAX_TOKENS não precisa de entrada para F3S: o default MAX_TOKENS já é 128.000, o mesmo teto de F3 e F4. Com o fan-out, nenhum despacho isolado chega perto disso.

A ordem continua vindo de um lugar só: pipeline-dag/F3S.yaml. Nenhum dos dois runners guarda a sequência das waves.

Mudança 4 — Contratos dos agentes
Com os corpos finalmente carregados, vale endurecer o que eles dizem — os achados A também apontam ambiguidade real nos contratos.

tasks-agent.md — citar o caminho do schema como contrato vinculante; listar os campos obrigatórios com o motivo de cada um (group e target_stack roteiam o fan-out; target_files e verify_command alimentam o razão; sem eles a task não pode ser verificada nem despachada); emitir entries[]; tasks.md como tabela derivada; nunca declarar contagem — quem conta é o check.
specification-agent.md — as 6 seções do C2 saem da descrição em tabela e passam a ser um bloco literal para copiar, com a nota de que traduzi-las reprova o gate; entram na Definition of Done. O template já as tem corretas: o agente precisa mandar copiá-lo.
prototype-spec-agent.md — mesmas 6 seções; emitir screen_id (screen-{kebab}) em cada tela, que é a chave que CHK-PROTO-002/003 casam; as 10 seções obrigatórias listadas como checklist verificável, não como tabela descritiva.
Todos os 7 — caminhos de saída para o layout novo.
Mudança 5 — Consumidores
Consumidor	Mudança
coder-{angular,react}-frontend.md	speckit_spec_prototype → outputs/tobe/speckit/specs/007-prototype/spec.md; idem plan e tasks
coder-dotnet-backend.md	Step 0.4 aponta para specs/{feature}/{spec,plan,tasks}.md
readiness-gate.md C2	glob → outputs/tobe/speckit/specs/*/spec.md
artifact-map.yaml	12 caminhos do bloco f3s_speckit
.specify/memory/constitution.md	linha F3S da tabela Output Path Conventions
ava-pipeline.yaml	advisory da F4 e inputs da F3S
context.py · task_ledger.py · artifact_gate_speckit.py	speckit_dir, _speckit_dir, _BASES["speckit"]
Arquivos
Alterados — 21 arquivos referenciam outputs/speckit (91 ocorrências), mais os testes:

Grupo	Caminhos
Fonte da verdade	src/shared/data/pipeline-dag/F3S.yaml (24 ocorrências + registro feature), src/shared/data/ava-pipeline.yaml
Módulo	speckit/module.yaml, os 7 speckit/agents/*.md, os 5 speckit/templates/*
Fan-out	src/shared/tools/pipeline_plan.py (dag_steps() + source: "dag"), src/shared/tools/ava_pipeline.py, ava-pipeline-runner-cli.py (expansão, build_prompt, PHASE_ARTIFACT_CONTRACT)
Ferramentas	src/shared/tools/task_ledger.py, speckit/utils/artifact_gate_speckit.py
Verificação	src/shared/checks/context.py, suites/speckit_traceability.py, suites/prototype_coverage.py
Consumidores	3 tech-stack/agents/coder-*.md, shared/readiness-gate.md, summary/data/artifact-map.yaml, .specify/memory/constitution.md
Documentação	specs/039-speckit-planning-layer/{spec,plan,tasks}.md, docs/plan/speckit-to-be-tak.md, CHANGELOG.md
Testes	test_speckit_check_suites.py, test_task_ledger.py, test_artifact_gate_speckit.py, test_pipeline_plan.py
Nenhum arquivo novo de código. As fixtures dos testes ganham o layout novo e os casos que travam os quatro defeitos B.

Migração do piloto
O conteúdo gerado é bom e não se perde. Movimentação mecânica:

outputs/speckit/specs/spec-business-rules.md  →  outputs/tobe/speckit/specs/001-business-rules/spec.md
outputs/speckit/plans/plan-business-rules.md  →  outputs/tobe/speckit/specs/001-business-rules/plan.md
outputs/speckit/tasks/tasks-business-rules.md →  outputs/tobe/speckit/specs/001-business-rules/tasks.md
…                                                (mesma regra para as 7 features)
outputs/speckit/{constitution,traceability,compliance-*,execution-log}  →  outputs/tobe/speckit/
outputs/speckit/ é removido depois da conferência de contagem. O execution-log.json recebe um bloco migration registrando o que precisa ser regerado e por quê: as 6 seções do C2 ausentes, os screen_id ausentes e a traceability.json fora do schema. O piloto fica visível como parcial, em vez de aparentar completo.

Regerar é ava-pipeline run -p nopcommerce-02-cli-ava --phase F3S depois das correções.

Verification
# 1. Layout novo, numeração determinística
python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py --list
#    exit_gate deve listar specs/ com min_count 7 sob outputs/tobe/speckit/
Get-ChildItem projects/nopcommerce-02-cli-ava/outputs/tobe/speckit/specs -Directory
#    001-business-rules … 007-prototype, cada uma com spec.md, plan.md, tasks.md

# 2. Os quatro defeitos B, travados por teste
python -m pytest tests/ava-fabric-agents/speckit/ -q
#    inclui: zero entradas reprova CHK-SK-006/010; chave raiz errada nomeia o erro;
#    screen-list com H1 antes de Warnings é lido corretamente;
#    endpoint com base path /api/v1 não é falso positivo

# 3. Os gates contra o piloto migrado — devem reprovar pelo motivo CERTO
python -m src.shared.checks --project nopcommerce-02-cli-ava --suite speckit_traceability
#    esperado: CHK-SK-013 aponta a chave raiz; CHK-SK-014 aponta as 6 seções ausentes.
#    NÃO esperado: CHK-SK-006 verde sem dados
python -m src.shared.checks --project nopcommerce-02-cli-ava --suite prototype_coverage
#    esperado: CHK-PROTO-001 enxerga as 15 telas; CHK-PROTO-006 sem falsos positivos

# 4. Nenhuma referência órfã ao caminho antigo
Select-String -Path src,tests,docs,specs -Pattern "outputs/speckit" -Recurse
#    sem resultado fora de notas históricas do CHANGELOG

# 5. A F3S deixa de ser um despacho único — nos DOIS runners
python src/shared/tools/ava_pipeline.py run -p nopcommerce-02-cli-ava --phase F3S --dry-run
#    esperado: 11 passos — constitution · 7 specs · plans · tasks · compliance
#    cada um nomeando o agente real e o tamanho do seu próprio prompt
python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('r','ava-pipeline-runner-cli.py'); m=importlib.util.module_from_spec(s); sys.modules['r']=m; s.loader.exec_module(m); print([x['phase'] for x in m.PIPELINE if x['phase'].startswith('F3S')])"
#    esperado: F3S:001-business-rules … F3S:compliance, e NÃO um único 'F3S'
python -m pytest tests/tools/test_pipeline_plan.py -q -k "runner19 or dag"

# 6. Fan-out da F4 volta a ser possível depois da regeração
python src/shared/tools/task_ledger.py -p nopcommerce-02-cli-ava --init
python src/shared/tools/task_ledger.py -p nopcommerce-02-cli-ava --groups
python src/shared/tools/ava_pipeline.py run -p nopcommerce-02-cli-ava --phase F4 --dry-run
#    N passos, um por grupo, cada um com o coder real da stack

# 7. Sem regressão
python -m pytest tests/ -q --ignore=tests/utils/test_mermaid_quality.py
#    22 falhas pré-existentes do HEAD, nenhuma nova
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat
Critério de aceite: --phase F3S --dry-run expande em 11 passos nos dois runners, cada um carregando o corpo do agente real; o gate de saída reprova nomeando a causa real no piloto atual e passa depois da regeração; --phase F4 --dry-run expande em um passo por grupo; nenhuma referência a outputs/speckit fora do histórico.

Ordem de execução
A sequência importa — invertê-la desperdiça uma execução de fase em inferência:

#	Incremento	Por quê nesta posição
1	Layout e caminho (Mudança 1)	Todo o resto referencia os caminhos novos
2	Fan-out da F3S (Mudança 3)	Sem ele, endurecer contrato de agente não muda nada — o corpo não carrega
3	Contratos dos agentes (Mudança 4)	Agora os corpos chegam ao modelo
4	traceability.json e checks (Mudança 2)	Os checks passam a medir o que a regeração vai produzir
5	Consumidores (Mudança 5)	Fecham o ciclo com os caminhos e o schema finais
6	Migração do piloto	Preserva o conteúdo e marca o que regerar
7	Regerar a F3S	Uma execução só, já com tudo corrigido
Add Comment