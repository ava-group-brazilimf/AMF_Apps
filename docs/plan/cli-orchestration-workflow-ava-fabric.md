Ready for review
Select text to add comments on the plan
CLI de orquestração da esteira AVA Fabric (ava-pipeline)
Context
O que o pipeline_runner.py faz hoje
pipeline_runner.py é um runner interativo, sem argumentos de linha de comando:

Patch de DNS (pipeline_runner.py:25-36) — monkeypatch em socket.getaddrinfo mapeando os hosts do Foundry para IPs de private endpoint (10.26.2.x), para ambientes sem split-DNS na VPN.
Config hardcoded (pipeline_runner.py:40-50) — WORKSPACE aponta para outro checkout (c:\_info\Projetos\Hub\SRC_Torre_Apps_31_07), endpoint, deployment claude-sonnet-4-6, MAX_TOKENS=32768, limites de contexto.
Tabela PIPELINE (pipeline_runner.py:54-110) — 18 passos escritos à mão.
Menus via input() — projeto → full/por fase → manual/auto → seleção de grupos.
Por passo: load_skill() acha o .md do agente por heurística de substring sobre rglob("*.md"), escolhendo o maior arquivo candidato; load_context() injeta project-config.yaml, shared-context.md e o conteúdo de até 30 artefatos de outputs/; o system prompt proíbe tools e exige blocos <!-- FILE: path -->…<!-- /FILE -->.
Chamada client.messages.stream() do SDK Anthropic direto no Foundry, com streaming no terminal.
Pós-processamento — extrai os blocos FILE: por regex, grava em disco, salva um log .md por passo em outputs/pipeline_runner/.
Dependências e pré-requisitos atuais
Item	Estado
Python	3.13.3 ✔
anthropic	0.116.0 instalado ✔ (fora da convenção stdlib-only do repo)
requests	importado na linha 14 e nunca usado — remover
pyyaml	disponível ✔
VPN vnet-core-brs-001	obrigatória (endpoint é private endpoint)
.copilot-key	lido de WORKSPACE/.copilot-key; neste repo o arquivo fica na raiz
WORKSPACE	aponta para outro checkout → hoje o script não roda neste repo
Comparação com o caminho Headroom-como-proxy
copilot-cli-headroom.bat roteia tudo por 127.0.0.1:8787 antes do Foundry:

pipeline_runner.py	copilot-cli-headroom.bat
base_url	Foundry direto	headroom_config.py --proxy-url (nunca hardcoded)
liveness	—	headroom_tool.py proxy status (exit 0 = no ar)
queda do proxy	—	degrada para endpoint direto com aviso
upstream	—	ANTHROPIC_TARGET_API_URL no ambiente do proxy
compressão / métricas	nenhuma	.headroom/proxy-requests.jsonl (tokens, latência)
A adaptação é de uma linha: o proxy registra POST /v1/messages (proxy_routes.py:207), encaminha o header de auth verbatim (o x-api-key do SDK passa direto) e faz passthrough de SSE. Basta base_url="http://127.0.0.1:8787" — sem sufixo de path. ANTHROPIC_TARGET_API_URL já tem o valor certo por default em headroom.yaml. O anthropic-version: 2023-06-01 continua necessário — além do Foundry, participa do roteamento (_is_anthropic_auth).

Os 404 documentados em agent_runner.py:683 vêm de /v1/models/{id}, rota que só o Copilot CLI chama. O SDK Anthropic em messages.stream() não a toca — a rota via proxy é limpa para o motor SDK.

Defeitos que o plano corrige
load_skill() por heurística — pode carregar o agente errado. O agent_registry entrega o path exato de cada um dos 107 agentes.
WORKSPACE de outro checkout — substituído por REPO_ROOT derivado de __file__.
Sem CLI, sem --dry-run, sem proxy, sem exit codes, requests morto.
Decisões tomadas
Motor híbrido (sdk + copilot) · proxy ligado por default com degradação avisada · config em ava-pipeline.yaml novo com precedência · ordem da esteira declarada explicitamente (abaixo), com o agent_registry usado para validação e resolução de spec_path, não para derivar a sequência.

A ordem da esteira — fonte de verdade
Esta é a sequência canônica, na ordem exata de execução. --all roda os 12 passos nesta ordem.

#	--phase	Agente	Trigger	Label
1	F1	ava-asis-orchestrator	FP	AS-IS Diagnostic — Full Pipeline
2	F2a	ava-tobe-orchestrator	SD	TO-BE Architecture — Solution Design
3	F2b	ava-devops-orchestrator	DP	DevOps Plan
4	F2c	ava-qa-orchestrator	TPT	QA — Test Plan & Strategy
5	F3	ava-prototype	—	Prototype
6	F4	ava-stack-orchestrator	SG	Tech Stack — Stack Generation
7	F5	ava-devops-orchestrator	DE	DevOps Execute
8	F6	ava-qa-orchestrator	TPT	QA — Test Execution
9	F8a	ava-summary	SAS	Summary — Generate
10	F8b	ava-summary-remediation	—	Summary — Remediation
11	F8c	ava-summary	SV	Summary — Validate
12	F8d	ava-summary	SAS	Summary — Final
--phase F2 é o grupo (passos 2–4); --phase F2b roda só o DevOps Plan. Mesma regra para F8. Não há F7 na esteira. O prompt enviado é @{agent} | {trigger} | project: {P}, ou @{agent} project: {P} quando não há trigger — idêntico a build_prompt().

⚠️ Divergência intencional, não corrigir. As etiquetas da esteira são etapas de sequência, não os módulos do agent_registry. Aqui F5 = DevOps Execute e F6 = QA Execution; em agent_registry.PHASE_BY_MODULE F5 é o módulo qa-agents e F6 é devops-agents. O CLI não valida step.phase == registry.phase — valida apenas que o agent existe, é despachável e não está deprecado, e usa o registry para obter spec_path. Isso vai como comentário no YAML e como docstring do teste, para ninguém "consertar" depois.

Arquivos
Novos

Caminho	Papel
src/shared/data/ava-pipeline.yaml	Fonte única: modelo, endpoints, URLs, proxy, e a ordem da esteira
src/shared/tools/pipeline_config.py	Loader com precedência + --show / --endpoint / --model
src/shared/tools/pipeline_plan.py	Expande steps: → plano executável, validando contra o agent_registry
src/shared/tools/sdk_engine.py	Motor SDK (skill/contexto/prompt/stream/parse), extraído do script atual
src/shared/tools/ava_pipeline.py	O CLI
ava-pipeline.bat	Atalho de raiz, ao lado de copilot-cli-headroom.bat
src/shared/tools/requirements-pipeline.txt	anthropic>=0.60, pyyaml>=6.0 — documenta a exceção ao stdlib-only
tests/tools/test_pipeline_config.py	Precedência env > project-config > yaml > fallback
tests/tools/test_pipeline_plan.py	Ordem dos 12 passos byte a byte; todo agente existe no registry
Alterados

Caminho	Mudança
pipeline_runner.py	Vira shim de ~15 linhas: aviso de deprecação + delega para ava_pipeline.main()
CHANGELOG.md	Entrada da spec
Não tocar: copilot-cli-headroom.bat e copilot-cli-v1.bat — restrição CA02 de specs/033; git diff --exit-code neles faz parte da verificação.

1. src/shared/data/ava-pipeline.yaml
Espelha a estrutura e o cabeçalho de precedência de headroom.yaml.

# Precedência (forte → fraco):
#   1. flags do CLI  2. env AVA_PIPELINE_* / AVA_FOUNDRY_*
#   3. projects/{p}/context/project-config.yaml -> bloco `pipeline:`
#   4. este arquivo  5. _FALLBACK_DEFAULTS em pipeline_config.py
pipeline:
  foundry:
    endpoint: "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
    api_key_file: ".copilot-key"          # relativo à raiz do repo
    anthropic_version: "2023-06-01"
    max_tokens: 32768
  models:
    default: "claude-sonnet-4-6"          # wire model (SDK / COPILOT_PROVIDER_WIRE_MODEL)
    provider_model_id: "claude-sonnet-4"  # id lógico do Copilot CLI — nunca 'auto' (R4)
    aliases: { sonnet: "claude-sonnet-4-6" }
  proxy:
    mode: "auto"                          # auto = degrada com aviso | require | off
    url_command:    ["src/shared/tools/headroom/headroom_config.py", "--proxy-url"]
    status_command: ["src/shared/tools/headroom/headroom_tool.py", "proxy", "status"]
    prefer_tool_venv: true                # .venv/Scripts/python.exe, nunca o python do PATH
  execution:
    engine: "sdk"                         # sdk | copilot
    confirm: "manual"                     # manual | auto
    timeout_s: 900
    output_subdir: "outputs/pipeline_runner"
  context: { skill_chars: 500000, file_chars: 500000, max_artifacts: 500, max_artifact_bodies: 30 }
  dns_overrides:
    enabled: false                        # o /anthropic resolve nativo sob VPN
    hosts: { "aif-imf-apps-prd-eus2-001.services.ai.azure.com": "10.26.2.12", ... }

  # ORDEM DA ESTEIRA — fonte de verdade da sequência. Lista ordenada, executada
  # de cima para baixo. `phase` aqui é ETAPA DA ESTEIRA, não o módulo do
  # agent_registry: F5=DevOps Execute e F6=QA Execution por decisão do processo.
  # Não alinhar com PHASE_BY_MODULE — a divergência é intencional.
  steps:
    - { phase: "F1",  group: "F1", agent: "ava-asis-orchestrator",     trigger: "FP",  label: "AS-IS Diagnostic — Full Pipeline" }
    - { phase: "F2a", group: "F2", agent: "ava-tobe-orchestrator",     trigger: "SD",  label: "TO-BE Architecture — Solution Design" }
    - { phase: "F2b", group: "F2", agent: "ava-devops-orchestrator",   trigger: "DP",  label: "DevOps Plan" }
    - { phase: "F2c", group: "F2", agent: "ava-qa-orchestrator",       trigger: "TPT", label: "QA — Test Plan & Strategy" }
    - { phase: "F3",  group: "F3", agent: "ava-prototype",             trigger: null,  label: "Prototype" }
    - { phase: "F4",  group: "F4", agent: "ava-stack-orchestrator",    trigger: "SG",  label: "Tech Stack — Stack Generation" }
    - { phase: "F5",  group: "F5", agent: "ava-devops-orchestrator",   trigger: "DE",  label: "DevOps Execute" }
    - { phase: "F6",  group: "F6", agent: "ava-qa-orchestrator",       trigger: "TPT", label: "QA — Test Execution" }
    - { phase: "F8a", group: "F8", agent: "ava-summary",               trigger: "SAS", label: "Summary — Generate" }
    - { phase: "F8b", group: "F8", agent: "ava-summary-remediation",   trigger: null,  label: "Summary — Remediation" }
    - { phase: "F8c", group: "F8", agent: "ava-summary",               trigger: "SV",  label: "Summary — Validate" }
    - { phase: "F8d", group: "F8", agent: "ava-summary",               trigger: "SAS", label: "Summary — Final" }
Um bloco pipeline: opcional em project-config.yaml sobrescreve por projeto — inclusive steps:, para um projeto com esteira reduzida (o arquivo hoje não tem nenhuma chave model:, verificado em MeuERP-002). Substituição de steps: é total, não merge por índice.

2. pipeline_config.py
Porte fiel de headroom_config.py — mesmas funções, mesmo contrato:

load_config(project=None) — _deep_merge de fallback → YAML → project-config.yaml → env; nunca levanta (YAML ilegível cai no fallback com aviso em stderr).
_ENV_MAP — AVA_FOUNDRY_ENDPOINT→foundry.endpoint, AVA_FOUNDRY_MODEL→models.default, AVA_PIPELINE_ENGINE, AVA_PIPELINE_PROXY_MODE, AVA_PIPELINE_MAX_TOKENS. Valor malformado → warning + ignora.
resolve_model(cfg, cli_model) — resolve alias; --model vence tudo.
api_key(cfg) — lê foundry.api_key_file a partir de REPO_ROOT.
proxy_url(cfg) / proxy_alive(cfg) — reusam os comandos do bloco proxy: com o venv da tool, como agent_runner.py:233-253.
CLI: --show [-p PROJ] [--json], --endpoint, --model (linha crua, consumível por .bat).
REPO_ROOT = Path(__file__).resolve().parents[3] — mata o WORKSPACE hardcoded.

3. pipeline_plan.py
def build_plan(cfg, phases=None, agent=None, start_at=None) -> list[Step]
Lê pipeline.steps na ordem declarada — sem ordenação, sem derivação.
--phase casa contra phase ou group (F2 → os três; F2b → um). Vários --phase preservam a ordem do YAML, não a de digitação.
--agent X → todos os passos da esteira com esse agente (ava-devops-orchestrator → F2b e F5, cada um com seu trigger). Combinado com --phase F5, fixa um. Se X não está na esteira (ex.: ava-asis-inventory), monta um passo avulso sem trigger, com fase e spec_path vindos do registry — é assim que se roda um agente isolado.
--from F4 corta o prefixo pela posição na lista.
Enriquece cada passo com spec_path, module e version de agent_registry.get(agent) — fim da heurística de load_skill().
validate_plan() — todo agent tem de existir no registry, ser despachável e não estar deprecado. Divergência é SystemExit(2), não warning. Não compara phase com registry.phase (divergência intencional, ver acima).
4. sdk_engine.py
Extrai de pipeline_runner.py, preservando o que funciona:

load_skill(step, cfg) — lê step.spec_path direto; trunca em context.skill_chars.
load_context(project, cfg) — mantido, com limites vindos da config.
build_system_prompt / parse_and_write_outputs — regex _FILE_BLOCK mantida. Remover _WRITE_BLOCK e _MD_FILE_BLOCK (mortas: parse_and_write_outputs retorna antes de usá-las).
make_client(cfg, route) — anthropic.Anthropic(api_key=…, base_url=route.base_url, default_headers={"anthropic-version": …}). route.base_url é a URL do proxy ou o endpoint — a única diferença entre as duas rotas.
import anthropic dentro da função, com mensagem apontando requirements-pipeline.txt se faltar (o motor copilot não precisa dele).
Patch de DNS aplicado só se dns_overrides.enabled.
5. ava_pipeline.py — o CLI
Padrão de subcomandos de pipeline_observer.py:1105-1178; guard UTF-8 do Windows; docstring com tabela de exit codes.

ava-pipeline run     -p PROJ [--phase F1 --phase F2b | --all] [--agent ID]
                     [--model M] [--engine sdk|copilot] [--from F4]
                     [--via-proxy | --no-proxy] [--yes] [--dry-run] [--json]
ava-pipeline list    [--phases] [--agents [--phase F1]]
ava-pipeline config  [-p PROJ] [--json]
ava-pipeline doctor  [-p PROJ]
Pedido	Flag
nome do projeto	-p/--project (obrigatório em run)
fase opcional	--phase F2b repetível, aceita F1,F2; sem --phase e sem --all → menu interativo (fluxo atual preservado)
todas as fases	--all — os 12 passos na ordem da tabela
modelo de LLM	--model (alias ou wire model)
agente único	--agent ava-asis-inventory
Ordem de execução do run:

Carrega config → resolve modelo → valida projects/{p}/context/project-config.yaml.
Resolve a rota (_resolve_route): mode=off → direto; require → SystemExit(2) se o proxy não responder; auto → proxy se vivo, senão endpoint direto com banner de aviso (⚠️ SEM compressão). --via-proxy ⇒ require, --no-proxy ⇒ off.
Monta e valida o plano.
Banner: projeto · rota · modelo · engine · nº de passos · destino em outputs/.
--dry-run imprime plano + rota + tamanho do prompt de cada passo e sai 0, sem gastar inferência.
Por passo: engine=sdk → sdk_engine.run_step() (streaming, parse dos blocos FILE, log por passo); engine=copilot → subprocess de agent_runner.py --project P --phase F --agent A [--via-proxy], reaproveitando gate de artefato, telemetria e taskkill /T /F.
Sem --yes, mantém o prompt [S]im/[P]ular/[V]er skill/[A]bortar e a _status_bar com emoji (já existem e funcionam bem).
Escreve outputs/.runs/{run_id}/run.json com o status de cada passo; relatório final igual ao de hoje.
Exit codes (contrato de agent_runner.py:37-41): 0 tudo ok/pulado · 1 ao menos um passo falhou · 2 erro de configuração (projeto inexistente, .copilot-key ausente, --via-proxy sem proxy, agente fora do registry) · 130 abortado.

Limite conhecido, sinalizado em voz alta: --engine copilot só tem DAG para F1 — pipeline-dag/ tem apenas F1.yaml. Nas demais etapas o CLI avisa que vai despachar só o orquestrador via copilot -p, em vez de fingir cobertura. Criar F2..F8.yaml fica fora deste escopo.

Verification
# 1. Config centralizada — uma fonte, precedência funcionando
python src/shared/tools/pipeline_config.py --show -p MeuERP-002
$env:AVA_FOUNDRY_MODEL="claude-opus-4-6"
python src/shared/tools/pipeline_config.py --model      # deve refletir o env
Remove-Item Env:\AVA_FOUNDRY_MODEL

# 2. A ordem da esteira — os 12 passos, exatamente nesta sequência
python src/shared/tools/ava_pipeline.py list --phases
#  F1 · F2a · F2b · F2c · F3 · F4 · F5 · F6 · F8a · F8b · F8c · F8d
#  F5 -> ava-devops-orchestrator | DE      (NÃO é o módulo F5 do registry)
#  F6 -> ava-qa-orchestrator     | TPT     (NÃO é o módulo F6 do registry)
python -m pytest tests/tools/test_pipeline_plan.py -q   # trava a ordem no CI

# 3. Seletores — custo zero de inferência
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --all --dry-run
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F2 --dry-run   # 3 passos
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F2b --dry-run  # 1 passo, DP
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --agent ava-devops-orchestrator --dry-run  # F2b + F5
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --agent ava-asis-inventory --dry-run       # avulso
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --all --from F4 --dry-run                  # F4..F8d
#  conferir no output: "@ava-devops-orchestrator | DP | project: MeuERP-002"

# 4. Rota via proxy (o proxy responde hoje em 127.0.0.1:8787)
python src/shared/tools/headroom/headroom_tool.py proxy status     # exit 0 = no ar
python src/shared/tools/ava_pipeline.py doctor -p MeuERP-002       # rota=proxy, chave ok, anthropic ok
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F8a --via-proxy --yes
#  prova de que passou pelo proxy — o JSONL só é escrito quando há tráfego:
Get-Content .headroom/proxy-requests.jsonl -Tail 1 | ConvertFrom-Json |
  Select-Object model, input_tokens_original, input_tokens_optimized, total_latency_ms

# 5. Degradação avisada
python src/shared/tools/headroom/headroom_tool.py proxy stop
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F8a --dry-run   # banner "SEM compressão", exit 0
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F8a --via-proxy # exit 2
python src/shared/tools/headroom/headroom_tool.py proxy start

# 6. Motor copilot e ausência de regressão
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F1 --engine copilot --dry-run
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --dry-run

# 7. Testes e restrição CA02
python -m pytest tests/ -q
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat   # sem saída = OK
Critério de aceite: list --phases emite os 12 passos na ordem da tabela, com F5=DevOps|DE e F6=QA|TPT; --dry-run de todos os seletores sai 0 sem chamada de rede; uma execução real via proxy acrescenta linha em .headroom/proxy-requests.jsonl e artefatos em projects/{p}/outputs/; pipeline_runner.py legado ainda roda pelo shim; os dois .bat intactos.

Fora de escopo (registrado)
F2..F8.yaml em pipeline-dag/ — sem eles --engine copilot só cobre F1 de verdade.
Bug em headroom_tool.py attribute: os aliases _BEFORE_KEYS/_AFTER_KEYS/_LATENCY_KEYS (headroom_tool.py:127-131) não batem com os campos reais do JSONL (input_tokens_original / input_tokens_optimized / total_latency_ms), então toda linha é descartada e o comando reporta "nenhuma requisição". Ainda não confirmado empiricamente — .headroom/proxy-requests.jsonl nunca foi escrito neste checkout; o passo 4 da verificação gera o primeiro tráfego real e permite confirmar.
Registro canônico de triggers — os códigos (FP, SD, DP, SG, DE, TPT, SAS, SV) só existem em prosa nos .md dos orquestradores e no PIPELINE hardcoded. O ava-pipeline.yaml passa a ser o primeiro lugar estruturado; unificar com os .md é trabalho separado.
Alinhar a numeração de fases entre esteira e agent_registry — divergência intencional e documentada; qualquer mudança é decisão de processo, não de código.