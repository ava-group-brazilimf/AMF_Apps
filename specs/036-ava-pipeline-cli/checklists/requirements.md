# Requirements Checklist — Spec 036

## Requisitos Funcionais

- [x] RF-001: O CLI expõe os subcomandos `run`, `list`, `config` e `doctor`.
- [x] RF-002: `run` aceita `-p/--project` como parâmetro obrigatório; projeto inexistente sai com código 2 listando os disponíveis.
- [x] RF-003: `--phase` seleciona por etapa (`F2b`) **ou** por grupo (`F2`), é repetível e aceita lista separada por vírgula (`F1,F2`).
- [x] RF-004: `--all` executa as 12 etapas na ordem declarada em `pipeline.steps`.
- [x] RF-005: `--model` aceita wire model ou alias e vence todas as demais camadas de configuração.
- [x] RF-006: `--agent` roda um agente da esteira (com o trigger da etapa) ou um agente avulso do `agent_registry` (sem trigger).
- [x] RF-007: `--agent` de um agente presente em duas etapas planeja ambas, cada uma com seu trigger; combinar com `--phase` fixa um momento.
- [x] RF-008: `--from` corta o prefixo do plano, permitindo retomar do meio da esteira.
- [x] RF-009: `--dry-run` imprime plano, rota e tamanho estimado do prompt, sai 0 e **não emite nenhuma requisição de rede**.
- [x] RF-010: Sem `--phase`, `--all` e `--agent`, o `run` abre menu interativo de grupos.
- [x] RF-011: `--yes` suprime a confirmação por passo; sem ele, o prompt oferece `[S]im / [P]ular / [V]er skill / [A]bortar`.
- [x] RF-012: `--engine sdk` chama o Foundry pelo SDK Anthropic; `--engine copilot` delega ao `agent_runner.py`.
- [x] RF-013: `list --phases` emite a ordem da esteira; `list --agents [--phase F1]` emite o catálogo do `agent_registry`.
- [x] RF-014: `config [-p PROJ]` emite a configuração efetiva em JSON.
- [x] RF-015: `doctor [-p PROJ]` verifica config, API key, SDK, proxy, plano e projeto.
- [x] RF-016: O prompt enviado é `@{agente} | {trigger} | project: {P}`, ou `@{agente} project: {P}` quando não há trigger.
- [x] RF-017: Cada passo executado grava log `.md` em `outputs/pipeline_runner/` e o run grava `outputs/.runs/{run_id}/run.json`.
- [x] RF-018: Exit codes — `0` ok, `1` etapa falhou, `2` erro de configuração, `130` abortado.

## Ordem da Esteira

- [x] ORD-001: A sequência é declarada em `src/shared/data/ava-pipeline.yaml` → `pipeline.steps`, executada de cima para baixo.
- [x] ORD-002: `F1` → `ava-asis-orchestrator | FP`.
- [x] ORD-003: `F2a` → `ava-tobe-orchestrator | SD`.
- [x] ORD-004: `F2b` → `ava-devops-orchestrator | DP`.
- [x] ORD-005: `F2c` → `ava-qa-orchestrator | TPT`.
- [x] ORD-006: `F3` → `ava-prototype` (sem trigger).
- [x] ORD-007: `F4` → `ava-stack-orchestrator | SG`.
- [x] ORD-008: `F5` → `ava-devops-orchestrator | DE`.
- [x] ORD-009: `F6` → `ava-qa-orchestrator | QE` — **não `TPT`**, que é o Momento 1.
- [x] ORD-010: `F8a`→`SAS`, `F8b`→(sem trigger), `F8c`→`SV`, `F8d`→`SAS`.
- [x] ORD-011: Não há F7 na esteira.
- [x] ORD-012: `--phase` preserva a ordem do YAML, não a ordem de digitação.
- [x] ORD-013: Nenhum orquestrador de dois momentos repete o mesmo trigger nas duas etapas.
- [x] ORD-014: F2b precede F5; F2c precede F6; F4 e F5 precedem F6 (pré-requisito do gate `QE`).

## Configuração

- [x] CFG-001: Modelo, endpoint, chave, proxy, orçamento de contexto e ordem da esteira vivem em `ava-pipeline.yaml`.
- [x] CFG-002: Precedência efetiva — flags do CLI > env (`AVA_PIPELINE_*` / `AVA_FOUNDRY_*`) > `project-config.yaml` → bloco `pipeline:` > `ava-pipeline.yaml` > `_FALLBACK_DEFAULTS`.
- [x] CFG-003: 10 variáveis de ambiente mapeadas para caminhos pontilhados da config.
- [x] CFG-004: Dicionários fazem merge recursivo; listas são substituídas por inteiro.
- [x] CFG-005: `_FALLBACK_DEFAULTS` traz `steps: []` — sem o YAML o CLI falha alto em vez de rodar uma esteira inventada.
- [x] CFG-006: Um projeto pode sobrescrever qualquer chave, inclusive `steps:`, pelo bloco `pipeline:` do seu `project-config.yaml`.
- [x] CFG-007: `pipeline_config.py --model` e `--endpoint` emitem linha crua, consumível por `.bat`.

## Rota e Proxy

- [x] PXY-001: A URL do proxy vem de `headroom_config.py --proxy-url`, nunca hardcoded.
- [x] PXY-002: O liveness vem de `headroom_tool.py proxy status` (exit 0 = no ar).
- [x] PXY-003: Ambos os comandos são resolvidos pelo venv isolado da tool (`prefer_tool_venv`), não pelo `python` do PATH.
- [x] PXY-004: `mode: auto` degrada para a rota direta **imprimindo aviso explícito de "SEM compressão"**.
- [x] PXY-005: `--via-proxy` aborta com código 2 quando o proxy não responde — nunca roda sem compressão silenciosamente.
- [x] PXY-006: `--no-proxy` não sonda o proxy.
- [x] PXY-007: O `base_url` do proxy não leva sufixo de path — o SDK acrescenta `/v1/messages`.
- [x] PXY-008: A rota efetiva aparece no banner de todo `run`.
- [x] PXY-009: O proxy fora do ar não reprova o `doctor` — é degradação prevista, não erro de configuração.

## Integridade & Anti-Regressão

- [x] INT-001: Nenhuma constante `8787` ou `127.0.0.1` em código no `pipeline_config.py` (verificado por AST, ignorando comentários e docstrings).
- [x] INT-002: Nenhum endpoint do Foundry ou id de modelo em código no `ava_pipeline.py` (verificado por AST).
- [x] INT-003: `spec_path` de todo passo vem de `agent_registry.get(agent)["path"]` e o arquivo existe.
- [x] INT-004: `validate_plan` reprova agente ausente, deprecado ou não-despachável, com exit 2.
- [x] INT-005: `validate_plan` **não** compara `step.phase` com `registry.phase` — a divergência de eixos é intencional.
- [x] INT-006: A divergência está registrada em quatro lugares: comentário do YAML, docstring do módulo, spec §3.2 e teste dedicado.
- [x] INT-007: `phase` duplicada em `steps` é reprovada — tornaria `--phase` ambíguo.
- [x] INT-008: Artefatos com caminho fora de `projects/{PROJETO}/` são recusados na escrita.
- [x] INT-009: `copilot-cli-headroom.bat` e `copilot-cli-v1.bat` inalterados (`git diff --exit-code` vazio) — CA02 da spec 033.
- [x] INT-010: Nenhuma spec de agente, `module.yaml` ou `SKILL.md` alterado.
- [x] INT-011: `pipeline_runner.py` continua executável como shim, com aviso de depreciação.

## Requisitos Não-Funcionais

- [x] RNF-001: `load_config` nunca levanta — YAML ilegível e env malformada degradam com aviso mantendo a camada de baixo (IV3).
- [x] RNF-002: `anthropic` é importado dentro de `make_client()`; `--engine copilot` não paga a dependência.
- [x] RNF-003: A exceção ao stdlib-only (IV7) está contida em dois módulos e declarada em `requirements-pipeline.txt`.
- [x] RNF-004: `REPO_ROOT` é derivado de `__file__`; nenhum caminho absoluto de checkout no código.
- [x] RNF-005: Código morto do runner anterior removido (`import requests`, `_WRITE_BLOCK`, `_MD_FILE_BLOCK`).
- [x] RNF-006: A chave da API nunca é impressa; o `doctor` reporta apenas o nome do arquivo.
- [x] RNF-007: Documentação, comentários e mensagens de erro em português brasileiro (Article V); cenários BDD em inglês.
- [x] RNF-008: O patch de DNS é opt-in (`dns_overrides.enabled: false`), porque o endpoint resolve nativamente sob VPN.

## Limitações Declaradas

- [x] LIM-001: `--engine copilot` só cobre a F1 — é o único DAG em `pipeline-dag/`. O CLI avisa por etapa em vez de fingir cobertura.
- [x] LIM-002: O motor `copilot` não propaga triggers; F2b e F5 colapsariam no mesmo comando. O CLI avisa e recomenda `--engine sdk`.
- [x] LIM-003: O bug em `headroom_tool.py attribute` (aliases de campo divergentes do JSONL real) está registrado como fora de escopo e **não confirmado empiricamente**.
- [x] LIM-004: Não há registro canônico de triggers; o `ava-pipeline.yaml` é o primeiro lugar estruturado, não a unificação com os `.md`.

## Documentação

- [x] DOC-001: `docs/guia-ava-pipeline-cli.md` com índice navegável e 16 seções.
- [x] DOC-002: Todos os parâmetros documentados em tabela, agrupados por finalidade, com os pares mutuamente exclusivos marcados.
- [x] DOC-003: Exemplos executáveis para cada seletor, incluindo os três comportamentos de `--agent`.
- [x] DOC-004: Receitas, tabela de solução de problemas e guia de migração do `pipeline_runner.py`.
- [x] DOC-005: Toda saída citada no guia foi capturada de execução real, não escrita de memória.
- [x] DOC-006: Entrada em `CHANGELOG.md`.
