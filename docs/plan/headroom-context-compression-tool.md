Ready for review
Select text to add comments on the plan
Headroom Context Compression — Tool + Proxy Interceptor
Context
A esteira AVA Fabric queima contexto e tempo por enviar payload não comprimido ao LLM. A ISSUE-002 mediu em processaERP-008: 761.376 tokens comprimidos, três runSubagent de 34/5/62 minutos, 110,6 min de execução e 8 de 19 artefatos F1 ausentes.

O Headroom já roda neste ecossistema, mas fora deste repositório: o analisador externo ava-fabric-delphi-analyzer/src/headroom_precompress.py produz projects/{p}/outputs/asis/ast-raw/{lang}/compressed/*.json + manifest.json + metrics.jsonl (baseline medido 2026-07-28: 6,99 MB → 2,67 MB, 1.194.239 → 761.376 tokens, -36,2%). Este repo apenas consome manifest.artifacts[].tokens_out em context_budget.py.

O objetivo desta entrega é internalizar o Headroom como tool do repositório e fechar as duas lacunas que sobram:

Nada intercepta as chamadas ao LLM. Não existe cliente LLM em Python neste repo — zero imports de openai/anthropic/azure em todo src/. Os ~97 agentes são arquivos .md executados por um host surface (Copilot CLI / Copilot Chat / Claude Code) contra o endpoint Foundry. A única camada onde 100% das requisições passam é um proxy local.
O que já está comprimido não é lido. sql_ir_generator.py:504-508 volta ao raw e build_summary_comprehensive.py:3425-3428 tem um decoder __headroom__ duplicado e frágil.
Duas correções ao prompt de origem (headroom-integration-prompt-v2.md)
Premissa do prompt	Realidade verificada
HeadroomStep como step 0 em cada agente Python, chamando self.foundry_client.call()	Inexequível. Não há classe de agente nem cliente LLM. Substituído por: proxy (interceptação) + tool CLI invocada pelos agentes via a diretiva Bash: já usada por pipeline_observer.py.
AZURE_OPENAI_ENDPOINT + gpt-4o + limite 128K	O endpoint real em copilot-cli-v1.bat é Anthropic-compatible: https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic, wire model claude-sonnet-4-6, COPILOT_PROVIDER_TYPE=anthropic, header anthropic-version: 2023-06-01. Limite = 200.000. O proxy do Headroom cobre /v1/messages além de /v1/chat/completions.
Consequência: o gap L1 do docs/plan/headroom-integration-implementation.md ("comprime para Claude 200K enquanto a inferência roda em Foundry 128K") não procede — 200K é o número certo. A correção real é tornar o limite explícito e configurável, não alterá-lo.

Decisão do usuário registrada
Fork embedded via git subtree (opção escolhida sobre dependência pip). Consequências aceitas: código de terceiros versionado dentro do repo, segundo venv isolado, e git subtree pull entrando no ciclo de manutenção. O repo hoje não tem requirements.txt/pyproject.toml na raiz e é stdlib-only — esta entrega abre essa exceção, contida dentro de src/shared/tools/headroom/.

Estrutura a criar
src/shared/tools/headroom/
├── vendor/                     # git subtree — código upstream, NÃO editar
├── headroom_tool.py            # CLI principal (convenção do repo)
├── headroom_config.py          # resolve headroom.yaml + project-config.yaml + env
├── headroom_context.py         # ÚNICO decoder __headroom__ + build_agent_context
├── mcp_server.py               # MCP server interno (compress / stats / retrieve)
├── headroom.yaml               # defaults da tool
├── requirements.txt            # headroom-ai[proxy,mcp,ml,code,memory,otel]>=0.33.0
├── setup.ps1  / setup.sh       # cria o venv isolado
├── run_standalone.ps1 / .sh    # sobe o proxy sem a esteira (I1)
├── Containerfile
├── podman-compose.yml
└── README.md
Raiz e config:

copilot-cli-headroom.bat        # NOVO — derivado de copilot-cli-v1.bat, aponta p/ localhost:8787
.vscode/mcp.json                # NOVO
.vscode/settings.json           # MERGE (já existe com 4 chaves — não sobrescrever)
.env.example                    # NOVO + negação no .gitignore
projects/_template/context/project-config.yaml   # + bloco headroom:
specs/031-headroom-context-compression-proxy/    # documentação SpecKit
Invariantes de projeto (não negociáveis)
IV1 — Uma única fonte canônica de fatia por agente. AGENT_ARTIFACT_SLICE em context_budget.py:79 já é a fonte canônica (spec 030, em produção). headroom_context.py importa esse dict via importlib.util.spec_from_file_location — não recria o AGENT_ARTIFACT_MAP que o docs/plan/headroom-integration-implementation.md propunha. Duas fontes concorrentes = o bug que esta entrega existe para não criar.

IV2 — Um único decoder __headroom__. Ao final, grep -rn "__headroom__" src/ retorna apenas headroom_context.py.

IV3 — A esteira roda sem o headroom instalado. Import defensivo (HEADROOM_AVAILABLE), fallback silencioso para pass-through. python src/modules/.../context_budget.py continua funcionando num clone sem o venv da tool.

IV4 — Colisão de nome de import. O diretório da tool chama-se headroom/ e o pacote vendorizado também. Nenhum arquivo headroom.py pode existir em src/shared/tools/headroom/, e o acesso ao upstream é sempre sys.path.insert(0, VENDOR_DIR) seguido de import headroom — nunca import relativo.

IV5 — Convenção de tool do repo. Cada .py da tool segue o padrão de pipeline_observer.py: from __future__ import annotations, funções (não classes), SCRIPT_DIR/REPO_ROOT por Path(__file__).resolve(), argparse + dispatch dict, print()/sys.exit (o repo não usa logging em lugar nenhum), guard UTF-8 no __main__, timezone BRZ = timezone(timedelta(hours=-3)).

Implementação
Cat. 0 — Spike de verificação (bloqueia tudo)
Antes de escrever config: headroom proxy --help, headroom doctor --help, headroom wrap --help. O README upstream documenta --port mas não confirma --upstream/--host; o roteamento upstream aparece via ANTHROPIC_BASE_URL / OPENAI_BASE_URL e possivelmente ~/.headroom/config.toml. Registrar a superfície real em research.md — os arquivos de config dependem disso.

Cat. 1 — Subtree + venv isolado
git subtree add --prefix src/shared/tools/headroom/vendor `
  https://github.com/headroomlabs-ai/headroom.git main --squash
setup.ps1: cria src/shared/tools/headroom/.venv (Python ≥3.10; o repo declara 3.10+ no README) e instala requirements.txt. .gitignore: ignorar src/shared/tools/headroom/.venv/.

requirements.txt: headroom-ai[proxy,mcp,ml,code,memory,otel]>=0.33.0 (versão atual no PyPI: 0.33.0, requires_python>=3.10), pyyaml>=6.0, pytest>=8.0. Sem gh (é binário de PATH — documentar no README).

Cat. 2 — headroom_config.py
Precedência, do mais forte para o mais fraco: env HEADROOM_*/AVA_FOUNDRY_* → projects/{project}/context/project-config.yaml bloco headroom: → headroom.yaml (defaults da tool). Segue a convenção já usada por context_budget_inline_threshold (Artigo I).

import yaml lazy com try/except, igual a context_budget.py:54-57. Não há loader canônico no repo — a forma mais próxima é load_project_config() em qa_preflight.py:64; replicar essa assinatura.

Bloco a acrescentar em projects/_template/context/project-config.yaml:

headroom:
  enabled: true
  model: "claude-sonnet-4-6"
  context_limit: 200000
  detect_backend: rust
  proxy:
    enabled: true
    host: localhost
    port: 8787
    upstream: "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
  output_shaper: true
  output_holdout: 0.0
  fallback_on_error: true       # IV3
  metrics_file: "outputs/observability/headroom-metrics.jsonl"
Cat. 3 — headroom_context.py (o núcleo)
Funções públicas:

Função	Responsabilidade
decode_headroom(payload)	único decoder do envelope __headroom__ (IV2)
read_artifact(project, name)	lê compressed/{name}.json, decodifica, cai para raw se ausente
build_agent_context(project, agent_id)	monta o contexto do agente usando a fatia importada de context_budget.AGENT_ARTIFACT_SLICE (IV1)
read_compression_metrics(project)	lê o metrics.jsonl produzido pelo analisador externo
estimate_agent_tokens(project, agent_id)	soma tokens_out da fatia
HEADROOM_AVAILABLE	flag do import defensivo (IV3)
Cat. 4 — headroom_tool.py (CLI)
argparse com subcomandos + dispatch dict, espelhando pipeline_observer.py:main():

python src/shared/tools/headroom/headroom_tool.py -p <PROJECT> <cmd>
  compress --input <path> [--model M] [--limit N]   # comprime um arquivo/dir
  decode   --input <path>                           # decodifica envelope __headroom__
  slice    --agent <agent_id> [--json]              # fatia + tokens estimados (usa IV1)
  metrics  --agent A --phase F1 --original N --compressed M [--latency-ms T]
  stats    [--json]                                 # agregado do JSONL do projeto
  doctor                                            # venv + vendor + proxy + endpoint
  proxy    {start|stop|status}                      # gerencia o proxy 8787
metrics faz append em projects/{project}/outputs/observability/headroom-metrics.jsonl, ao lado de agent-events.jsonl e pipeline-run-state.json. Reusar verbatim o idioma de append de _write_agent_metrics() em pipeline_observer.py:196.

Linha do JSONL (timestamp em BRZ, %Y-%m-%dT%H:%M:%S-03:00, como o resto do repo):

{"ts":"2026-07-30T12:00:00-03:00","run_id":"...","agent_id":"ava-asis-inventory","phase":"F1",
 "model":"claude-sonnet-4-6","original_tokens":12400,"compressed_tokens":1860,
 "tokens_saved":10540,"savings_pct":85.0,"compression_applied":true,
 "detect_backend":"rust","proxy_used":true,"latency_ms":320,"context_limit":200000,"error":null}
Cat. 5 — Proxy + interceptação (invariante I3 do prompt)
copilot-cli-headroom.bat — cópia de copilot-cli-v1.bat com uma linha alterada; todo o resto (leitura de .copilot-key, COPILOT_PROVIDER_TYPE=anthropic, COPILOT_PROVIDER_HEADERS, --autopilot --no-ask-user) preservado:

set REAL_ENDPOINT=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
set "COPILOT_PROVIDER_BASE_URL=http://localhost:8787"
O .bat verifica se 8787 está de pé (headroom proxy status) e degrada para o endpoint direto com aviso se não estiver — nunca bloqueia a sessão (IV3, mesma filosofia "degrada e continua" de context_budget.py exit 3).

run_standalone.ps1 sobe o proxy sem nenhuma dependência da esteira (I1).

.vscode/settings.json: merge, preservando as 4 chaves existentes (chat.tools.terminal.autoApprove com 3 regex matchCommandLine, livePreview.defaultPreviewPath, chat.mcp.autostart, files.associations). Acrescentar github.copilot.advanced.debug.overrideProxyUrl e terminal.integrated.env.windows.

.vscode/mcp.json: novo, apontando para .venv/Scripts/python.exe (Windows — não bin/python). Atenção: .gitignore tem uma linha .vscode solta; settings.json está trackeado por ter sido commitado antes. Os arquivos novos precisam de git add -f ou de negações explícitas (!.vscode/mcp.json) — preferir as negações.

.env.example: o .gitignore bloqueia .env.*, que casa com .env.example. Adicionar !.env.example.

Cat. 6 — Reconexão dos consumidores (gaps L3 / L4)
Arquivo	Mudança
build_summary_comprehensive.py:3425-3428	remove o decoder __headroom__ duplicado → from headroom_context import decode_headroom (IV2)
sql_ir_generator.py:504-508	deixa de forçar o raw → read_artifact(), com fallback para raw se compressed/ não existir
Ambos têm teste em tests/utils/ (test_sql_ir_generator.py existe) — rodar antes e depois.

Cat. 7 — Instrumentação dos agentes
Escopo contido: apenas os agentes já presentes em AGENT_ARTIFACT_SLICE (F1 Wave 1/2 + Phase B/C), não os ~97. Cada um recebe, no bloco ## FASE OBRIGATÓRIA — Registro de Observabilidade que já existe, uma linha Bash: adicional chamando headroom_tool.py metrics.

O padrão está documentado em src/modules/ava-fabric-agents/shared/observability-self-report.md (v2.2.0), que registra explicitamente por que a indireção não funciona: "uma referência como see @observability-self-report era lida pelos LLMs executores como texto descritivo, não como instrução". Portanto o comando literal vai inline em cada .md — sem @referência.

Version bump MINOR em cada agente tocado, com a tríplice consistência que a spec 030 exige: frontmatter version == literal --version da FASE OBRIGATÓRIA == catálogo em pipeline_observer.py:102 AGENT_CATALOG e generate_observability_report.py:24 (o catálogo é duplicado nos dois arquivos).

Cat. 8 — Documentação SpecKit
specs/031-headroom-context-compression-proxy/ — 031 é o próximo número (Get-HighestNumberFromSpecs sobre ^(\d{3,})-; atual máximo = 030).

Usar os templates de .specify/templates/overrides/ (a camada de projeto autoritativa) e não os de .specify/templates/ na raiz, que ainda são os stock do spec-kit para plan-template.md e tasks-template.md.

Arquivo	Base
spec.md	overrides/spec-template.md, adaptado ao padrão da spec 030 para features não-agente (## 2. Problem Statement + ## 3. Decision no lugar do bloco Agent Identity puro). Spec em inglês, cenários BDD Given/When/Then em inglês (Art. V)
plan.md	overrides/plan-template.md — 10 seções, incluindo ## Constitution Check
tasks.md	overrides/tasks-template.md — 7 categorias, numeração 1.1, 1.2…, [P] para paralelo
research.md	saída da Cat. 0 (superfície real da CLI) + baseline de compressão
quickstart.md	passos de verificação manual (é a convenção de teste do repo — só existem 3 arquivos em tests/)
## Constitution Check do plan.md precisa endereçar: Art. I (config-driven — nada hardcoded, tudo em project-config.yaml), Art. V (corpo/docstrings em pt-BR), Art. VII (security-first — .copilot-key e chaves nunca versionados; o proxy é local-only, --host localhost, não 0.0.0.0 como o prompt sugeria), Art. VIII (observabilidade), Art. X (versionamento dos agentes tocados).

Atualizar também: src/shared/tools/README.md (tabela ## Files — é como uma tool é "registrada" neste repo) e .github/copilot-instructions.md.

Verificação
Ordem de execução, do mais barato ao mais caro:

Isolamento — python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project Meu-ERP --json funciona sem o venv da tool ativado (IV3).
Fonte única — grep -rn "__headroom__" src/ retorna só headroom_context.py (IV2); grep -rn "AGENT_ARTIFACT_MAP" src/ retorna vazio (IV1).
Doctor — .\src\shared\tools\headroom\setup.ps1; headroom doctor → OK; depois python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP doctor.
Slice — ... headroom_tool.py -p processaERP-008 slice --agent ava-asis-db-analyzer --json deve bater com o número da spec 030 (db-analyzer = 559.144 tokens, 73,4% do payload).
Regressão dos consumidores — pytest tests/utils/test_sql_ir_generator.py e python src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py --project Meu-ERP.
Proxy standalone (I1) — .\src\shared\tools\headroom\run_standalone.ps1, depois headroom doctor noutra aba confirma o roteamento; headroom perf mostra savings.
Interceptação end-to-end (I3) — copilot-cli-headroom.bat, uma pergunta qualquer, e headroom perf / headroom_tool.py stats registram a chamada. Depois derrubar o proxy e confirmar que o .bat degrada com aviso em vez de falhar (IV3).
Métricas — projects/Meu-ERP/outputs/observability/headroom-metrics.jsonl recebe uma linha por chamada, e pipeline_observer.py -p Meu-ERP report continua gerando o relatório.
MCP — MCP: List Servers no VSCode lista ava-headroom.
Manutenção do fork — git subtree pull --prefix src/shared/tools/headroom/vendor ... main --squash num branch descartável, repetindo os passos 3–5.
Rollback (3 níveis independentes)
headroom.enabled: false no project-config.yaml · COPILOT_PROVIDER_BASE_URL de volta ao endpoint direto (usar copilot-cli-v1.bat, que fica intacto) · git subtree removido sem tocar em context_budget.py.

Fora de escopo
Alterar headroom_precompress.py no repositório externo ava-fabric-delphi-analyzer (gap F2 do plano antigo) — exige PR em outro repo. O limite 200K já está correto para o endpoint Anthropic.
Instrumentar os ~97 agentes; só os que constam em AGENT_ARTIFACT_SLICE (Cat. 7).
Resolver o conflito de mapa de fases entre module.yaml (F3=tech-stack, F7=devops) e .specify/memory/constitution.md:280 (F3=prototype, F6=devops). Esta entrega segue a constituição, que é o que os templates de spec usam.
podman-compose como caminho de execução padrão — entregue e documentado, mas o fluxo suportado é o venv + run_standalone.ps1.Ready for review
Select text to add comments on the plan
Headroom Context Compression — Tool + Proxy Interceptor
Context
A esteira AVA Fabric queima contexto e tempo por enviar payload não comprimido ao LLM. A ISSUE-002 mediu em processaERP-008: 761.376 tokens comprimidos, três runSubagent de 34/5/62 minutos, 110,6 min de execução e 8 de 19 artefatos F1 ausentes.

O Headroom já roda neste ecossistema, mas fora deste repositório: o analisador externo ava-fabric-delphi-analyzer/src/headroom_precompress.py produz projects/{p}/outputs/asis/ast-raw/{lang}/compressed/*.json + manifest.json + metrics.jsonl (baseline medido 2026-07-28: 6,99 MB → 2,67 MB, 1.194.239 → 761.376 tokens, -36,2%). Este repo apenas consome manifest.artifacts[].tokens_out em context_budget.py.

O objetivo desta entrega é internalizar o Headroom como tool do repositório e fechar as duas lacunas que sobram:

Nada intercepta as chamadas ao LLM. Não existe cliente LLM em Python neste repo — zero imports de openai/anthropic/azure em todo src/. Os ~97 agentes são arquivos .md executados por um host surface (Copilot CLI / Copilot Chat / Claude Code) contra o endpoint Foundry. A única camada onde 100% das requisições passam é um proxy local.
O que já está comprimido não é lido. sql_ir_generator.py:504-508 volta ao raw e build_summary_comprehensive.py:3425-3428 tem um decoder __headroom__ duplicado e frágil.
Duas correções ao prompt de origem (headroom-integration-prompt-v2.md)
Premissa do prompt	Realidade verificada
HeadroomStep como step 0 em cada agente Python, chamando self.foundry_client.call()	Inexequível. Não há classe de agente nem cliente LLM. Substituído por: proxy (interceptação) + tool CLI invocada pelos agentes via a diretiva Bash: já usada por pipeline_observer.py.
AZURE_OPENAI_ENDPOINT + gpt-4o + limite 128K	O endpoint real em copilot-cli-v1.bat é Anthropic-compatible: https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic, wire model claude-sonnet-4-6, COPILOT_PROVIDER_TYPE=anthropic, header anthropic-version: 2023-06-01. Limite = 200.000. O proxy do Headroom cobre /v1/messages além de /v1/chat/completions.
Consequência: o gap L1 do docs/plan/headroom-integration-implementation.md ("comprime para Claude 200K enquanto a inferência roda em Foundry 128K") não procede — 200K é o número certo. A correção real é tornar o limite explícito e configurável, não alterá-lo.

Decisão do usuário registrada
Fork embedded via git subtree (opção escolhida sobre dependência pip). Consequências aceitas: código de terceiros versionado dentro do repo, segundo venv isolado, e git subtree pull entrando no ciclo de manutenção. O repo hoje não tem requirements.txt/pyproject.toml na raiz e é stdlib-only — esta entrega abre essa exceção, contida dentro de src/shared/tools/headroom/.

Estrutura a criar
src/shared/tools/headroom/
├── vendor/                     # git subtree — código upstream, NÃO editar
├── headroom_tool.py            # CLI principal (convenção do repo)
├── headroom_config.py          # resolve headroom.yaml + project-config.yaml + env
├── headroom_context.py         # ÚNICO decoder __headroom__ + build_agent_context
├── mcp_server.py               # MCP server interno (compress / stats / retrieve)
├── headroom.yaml               # defaults da tool
├── requirements.txt            # headroom-ai[proxy,mcp,ml,code,memory,otel]>=0.33.0
├── setup.ps1  / setup.sh       # cria o venv isolado
├── run_standalone.ps1 / .sh    # sobe o proxy sem a esteira (I1)
├── Containerfile
├── podman-compose.yml
└── README.md
Raiz e config:

copilot-cli-headroom.bat        # NOVO — derivado de copilot-cli-v1.bat, aponta p/ localhost:8787
.vscode/mcp.json                # NOVO
.vscode/settings.json           # MERGE (já existe com 4 chaves — não sobrescrever)
.env.example                    # NOVO + negação no .gitignore
projects/_template/context/project-config.yaml   # + bloco headroom:
specs/031-headroom-context-compression-proxy/    # documentação SpecKit
Invariantes de projeto (não negociáveis)
IV1 — Uma única fonte canônica de fatia por agente. AGENT_ARTIFACT_SLICE em context_budget.py:79 já é a fonte canônica (spec 030, em produção). headroom_context.py importa esse dict via importlib.util.spec_from_file_location — não recria o AGENT_ARTIFACT_MAP que o docs/plan/headroom-integration-implementation.md propunha. Duas fontes concorrentes = o bug que esta entrega existe para não criar.

IV2 — Um único decoder __headroom__. Ao final, grep -rn "__headroom__" src/ retorna apenas headroom_context.py.

IV3 — A esteira roda sem o headroom instalado. Import defensivo (HEADROOM_AVAILABLE), fallback silencioso para pass-through. python src/modules/.../context_budget.py continua funcionando num clone sem o venv da tool.

IV4 — Colisão de nome de import. O diretório da tool chama-se headroom/ e o pacote vendorizado também. Nenhum arquivo headroom.py pode existir em src/shared/tools/headroom/, e o acesso ao upstream é sempre sys.path.insert(0, VENDOR_DIR) seguido de import headroom — nunca import relativo.

IV5 — Convenção de tool do repo. Cada .py da tool segue o padrão de pipeline_observer.py: from __future__ import annotations, funções (não classes), SCRIPT_DIR/REPO_ROOT por Path(__file__).resolve(), argparse + dispatch dict, print()/sys.exit (o repo não usa logging em lugar nenhum), guard UTF-8 no __main__, timezone BRZ = timezone(timedelta(hours=-3)).

Implementação
Cat. 0 — Spike de verificação (bloqueia tudo)
Antes de escrever config: headroom proxy --help, headroom doctor --help, headroom wrap --help. O README upstream documenta --port mas não confirma --upstream/--host; o roteamento upstream aparece via ANTHROPIC_BASE_URL / OPENAI_BASE_URL e possivelmente ~/.headroom/config.toml. Registrar a superfície real em research.md — os arquivos de config dependem disso.

Cat. 1 — Subtree + venv isolado
git subtree add --prefix src/shared/tools/headroom/vendor `
  https://github.com/headroomlabs-ai/headroom.git main --squash
setup.ps1: cria src/shared/tools/headroom/.venv (Python ≥3.10; o repo declara 3.10+ no README) e instala requirements.txt. .gitignore: ignorar src/shared/tools/headroom/.venv/.

requirements.txt: headroom-ai[proxy,mcp,ml,code,memory,otel]>=0.33.0 (versão atual no PyPI: 0.33.0, requires_python>=3.10), pyyaml>=6.0, pytest>=8.0. Sem gh (é binário de PATH — documentar no README).

Cat. 2 — headroom_config.py
Precedência, do mais forte para o mais fraco: env HEADROOM_*/AVA_FOUNDRY_* → projects/{project}/context/project-config.yaml bloco headroom: → headroom.yaml (defaults da tool). Segue a convenção já usada por context_budget_inline_threshold (Artigo I).

import yaml lazy com try/except, igual a context_budget.py:54-57. Não há loader canônico no repo — a forma mais próxima é load_project_config() em qa_preflight.py:64; replicar essa assinatura.

Bloco a acrescentar em projects/_template/context/project-config.yaml:

headroom:
  enabled: true
  model: "claude-sonnet-4-6"
  context_limit: 200000
  detect_backend: rust
  proxy:
    enabled: true
    host: localhost
    port: 8787
    upstream: "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
  output_shaper: true
  output_holdout: 0.0
  fallback_on_error: true       # IV3
  metrics_file: "outputs/observability/headroom-metrics.jsonl"
Cat. 3 — headroom_context.py (o núcleo)
Funções públicas:

Função	Responsabilidade
decode_headroom(payload)	único decoder do envelope __headroom__ (IV2)
read_artifact(project, name)	lê compressed/{name}.json, decodifica, cai para raw se ausente
build_agent_context(project, agent_id)	monta o contexto do agente usando a fatia importada de context_budget.AGENT_ARTIFACT_SLICE (IV1)
read_compression_metrics(project)	lê o metrics.jsonl produzido pelo analisador externo
estimate_agent_tokens(project, agent_id)	soma tokens_out da fatia
HEADROOM_AVAILABLE	flag do import defensivo (IV3)
Cat. 4 — headroom_tool.py (CLI)
argparse com subcomandos + dispatch dict, espelhando pipeline_observer.py:main():

python src/shared/tools/headroom/headroom_tool.py -p <PROJECT> <cmd>
  compress --input <path> [--model M] [--limit N]   # comprime um arquivo/dir
  decode   --input <path>                           # decodifica envelope __headroom__
  slice    --agent <agent_id> [--json]              # fatia + tokens estimados (usa IV1)
  metrics  --agent A --phase F1 --original N --compressed M [--latency-ms T]
  stats    [--json]                                 # agregado do JSONL do projeto
  doctor                                            # venv + vendor + proxy + endpoint
  proxy    {start|stop|status}                      # gerencia o proxy 8787
metrics faz append em projects/{project}/outputs/observability/headroom-metrics.jsonl, ao lado de agent-events.jsonl e pipeline-run-state.json. Reusar verbatim o idioma de append de _write_agent_metrics() em pipeline_observer.py:196.

Linha do JSONL (timestamp em BRZ, %Y-%m-%dT%H:%M:%S-03:00, como o resto do repo):

{"ts":"2026-07-30T12:00:00-03:00","run_id":"...","agent_id":"ava-asis-inventory","phase":"F1",
 "model":"claude-sonnet-4-6","original_tokens":12400,"compressed_tokens":1860,
 "tokens_saved":10540,"savings_pct":85.0,"compression_applied":true,
 "detect_backend":"rust","proxy_used":true,"latency_ms":320,"context_limit":200000,"error":null}
Cat. 5 — Proxy + interceptação (invariante I3 do prompt)
copilot-cli-headroom.bat — cópia de copilot-cli-v1.bat com uma linha alterada; todo o resto (leitura de .copilot-key, COPILOT_PROVIDER_TYPE=anthropic, COPILOT_PROVIDER_HEADERS, --autopilot --no-ask-user) preservado:

set REAL_ENDPOINT=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
set "COPILOT_PROVIDER_BASE_URL=http://localhost:8787"
O .bat verifica se 8787 está de pé (headroom proxy status) e degrada para o endpoint direto com aviso se não estiver — nunca bloqueia a sessão (IV3, mesma filosofia "degrada e continua" de context_budget.py exit 3).

run_standalone.ps1 sobe o proxy sem nenhuma dependência da esteira (I1).

.vscode/settings.json: merge, preservando as 4 chaves existentes (chat.tools.terminal.autoApprove com 3 regex matchCommandLine, livePreview.defaultPreviewPath, chat.mcp.autostart, files.associations). Acrescentar github.copilot.advanced.debug.overrideProxyUrl e terminal.integrated.env.windows.

.vscode/mcp.json: novo, apontando para .venv/Scripts/python.exe (Windows — não bin/python). Atenção: .gitignore tem uma linha .vscode solta; settings.json está trackeado por ter sido commitado antes. Os arquivos novos precisam de git add -f ou de negações explícitas (!.vscode/mcp.json) — preferir as negações.

.env.example: o .gitignore bloqueia .env.*, que casa com .env.example. Adicionar !.env.example.

Cat. 6 — Reconexão dos consumidores (gaps L3 / L4)
Arquivo	Mudança
build_summary_comprehensive.py:3425-3428	remove o decoder __headroom__ duplicado → from headroom_context import decode_headroom (IV2)
sql_ir_generator.py:504-508	deixa de forçar o raw → read_artifact(), com fallback para raw se compressed/ não existir
Ambos têm teste em tests/utils/ (test_sql_ir_generator.py existe) — rodar antes e depois.

Cat. 7 — Instrumentação dos agentes
Escopo contido: apenas os agentes já presentes em AGENT_ARTIFACT_SLICE (F1 Wave 1/2 + Phase B/C), não os ~97. Cada um recebe, no bloco ## FASE OBRIGATÓRIA — Registro de Observabilidade que já existe, uma linha Bash: adicional chamando headroom_tool.py metrics.

O padrão está documentado em src/modules/ava-fabric-agents/shared/observability-self-report.md (v2.2.0), que registra explicitamente por que a indireção não funciona: "uma referência como see @observability-self-report era lida pelos LLMs executores como texto descritivo, não como instrução". Portanto o comando literal vai inline em cada .md — sem @referência.

Version bump MINOR em cada agente tocado, com a tríplice consistência que a spec 030 exige: frontmatter version == literal --version da FASE OBRIGATÓRIA == catálogo em pipeline_observer.py:102 AGENT_CATALOG e generate_observability_report.py:24 (o catálogo é duplicado nos dois arquivos).

Cat. 8 — Documentação SpecKit
specs/031-headroom-context-compression-proxy/ — 031 é o próximo número (Get-HighestNumberFromSpecs sobre ^(\d{3,})-; atual máximo = 030).

Usar os templates de .specify/templates/overrides/ (a camada de projeto autoritativa) e não os de .specify/templates/ na raiz, que ainda são os stock do spec-kit para plan-template.md e tasks-template.md.

Arquivo	Base
spec.md	overrides/spec-template.md, adaptado ao padrão da spec 030 para features não-agente (## 2. Problem Statement + ## 3. Decision no lugar do bloco Agent Identity puro). Spec em inglês, cenários BDD Given/When/Then em inglês (Art. V)
plan.md	overrides/plan-template.md — 10 seções, incluindo ## Constitution Check
tasks.md	overrides/tasks-template.md — 7 categorias, numeração 1.1, 1.2…, [P] para paralelo
research.md	saída da Cat. 0 (superfície real da CLI) + baseline de compressão
quickstart.md	passos de verificação manual (é a convenção de teste do repo — só existem 3 arquivos em tests/)
## Constitution Check do plan.md precisa endereçar: Art. I (config-driven — nada hardcoded, tudo em project-config.yaml), Art. V (corpo/docstrings em pt-BR), Art. VII (security-first — .copilot-key e chaves nunca versionados; o proxy é local-only, --host localhost, não 0.0.0.0 como o prompt sugeria), Art. VIII (observabilidade), Art. X (versionamento dos agentes tocados).

Atualizar também: src/shared/tools/README.md (tabela ## Files — é como uma tool é "registrada" neste repo) e .github/copilot-instructions.md.

Verificação
Ordem de execução, do mais barato ao mais caro:

Isolamento — python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project Meu-ERP --json funciona sem o venv da tool ativado (IV3).
Fonte única — grep -rn "__headroom__" src/ retorna só headroom_context.py (IV2); grep -rn "AGENT_ARTIFACT_MAP" src/ retorna vazio (IV1).
Doctor — .\src\shared\tools\headroom\setup.ps1; headroom doctor → OK; depois python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP doctor.
Slice — ... headroom_tool.py -p processaERP-008 slice --agent ava-asis-db-analyzer --json deve bater com o número da spec 030 (db-analyzer = 559.144 tokens, 73,4% do payload).
Regressão dos consumidores — pytest tests/utils/test_sql_ir_generator.py e python src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py --project Meu-ERP.
Proxy standalone (I1) — .\src\shared\tools\headroom\run_standalone.ps1, depois headroom doctor noutra aba confirma o roteamento; headroom perf mostra savings.
Interceptação end-to-end (I3) — copilot-cli-headroom.bat, uma pergunta qualquer, e headroom perf / headroom_tool.py stats registram a chamada. Depois derrubar o proxy e confirmar que o .bat degrada com aviso em vez de falhar (IV3).
Métricas — projects/Meu-ERP/outputs/observability/headroom-metrics.jsonl recebe uma linha por chamada, e pipeline_observer.py -p Meu-ERP report continua gerando o relatório.
MCP — MCP: List Servers no VSCode lista ava-headroom.
Manutenção do fork — git subtree pull --prefix src/shared/tools/headroom/vendor ... main --squash num branch descartável, repetindo os passos 3–5.
Rollback (3 níveis independentes)
headroom.enabled: false no project-config.yaml · COPILOT_PROVIDER_BASE_URL de volta ao endpoint direto (usar copilot-cli-v1.bat, que fica intacto) · git subtree removido sem tocar em context_budget.py.

Fora de escopo
Alterar headroom_precompress.py no repositório externo ava-fabric-delphi-analyzer (gap F2 do plano antigo) — exige PR em outro repo. O limite 200K já está correto para o endpoint Anthropic.
Instrumentar os ~97 agentes; só os que constam em AGENT_ARTIFACT_SLICE (Cat. 7).
Resolver o conflito de mapa de fases entre module.yaml (F3=tech-stack, F7=devops) e .specify/memory/constitution.md:280 (F3=prototype, F6=devops). Esta entrega segue a constituição, que é o que os templates de spec usam.
podman-compose como caminho de execução padrão — entregue e documentado, mas o fluxo suportado é o venv + run_standalone.ps1.