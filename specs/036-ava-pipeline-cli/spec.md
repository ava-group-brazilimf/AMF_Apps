# Agent Specification: CLI de orquestração da esteira (`ava-pipeline`)

**Feature Branch**: `036-ava-pipeline-cli`
**Created**: 2026-08-05
**Status**: Implemented
**Change Type**: add-new (`ava-pipeline.yaml` · `pipeline_config.py` · `pipeline_plan.py` ·
`sdk_engine.py` · `ava_pipeline.py` · `ava-pipeline.bat` · 2 suítes de teste · guia)
+ modify-existing (`pipeline_runner.py` → shim · `CHANGELOG.md`)
**Input**: "Analise o `pipeline_runner.py`: como funciona, quais dependências, como adapto para usar
o headroom como proxy antes da requisição chegar ao Foundry. Quais configurações são necessárias
para parametrizar o script — passando o nome do projeto, número da fase opcional que desejo
executar, sinalizar todas as fases, modelo de LLM, agente específico caso queira rodar só um agente.
O script deve fazer a orquestração total do pipeline da fábrica de agentes. Transformar o script em
CLI mais robusto para execução do workflow completo. As configurações de modelo, urls, endpoint
devem ficar em um arquivo separado para ser carregado pelo CLI, assim centralizar mudança em uma
única fonte de alteração."

---

## 1. Identidade

Sem agente novo. Muda **como** a esteira é disparada de fora — do menu interativo para um CLI
parametrizável — e **de onde** vêm modelo, endpoint e a ordem de execução.

| Componente | Papel |
|---|---|
| `src/shared/data/ava-pipeline.yaml` | **Novo.** Fonte única de modelo, endpoint, chave, proxy, orçamento de contexto e **a ordem da esteira** |
| `src/shared/tools/pipeline_config.py` | **Novo.** Resolve a configuração efetiva com precedência declarada; nunca levanta |
| `src/shared/tools/pipeline_plan.py` | **Novo.** Expande `pipeline.steps` no plano executável e valida contra o `agent_registry` |
| `src/shared/tools/sdk_engine.py` | **Novo.** Motor SDK Anthropic — skill, contexto, prompt, streaming, extração de artefatos |
| `src/shared/tools/ava_pipeline.py` | **Novo.** O CLI: `run` / `list` / `config` / `doctor` |
| `ava-pipeline.bat` | **Novo.** Atalho de raiz, ao lado de `copilot-cli-headroom.bat` |
| `src/shared/tools/requirements-pipeline.txt` | **Novo.** Documenta a exceção ao stdlib-only, contida em dois módulos |
| `docs/guia-ava-pipeline-cli.md` | **Novo.** Guia passo a passo com referência de todos os parâmetros |
| `tests/tools/test_pipeline_plan.py` | **Novo.** Trava a ordem das 12 etapas e o par planejar/executar |
| `tests/tools/test_pipeline_config.py` | **Novo.** Trava a precedência e proíbe endpoint/modelo/porta hardcoded |
| `pipeline_runner.py` (raiz) | **Existe.** Vira shim de depreciação que delega ao CLI |

**Agentes novos**: nenhum. **Skills novas**: nenhuma. **Specs de agente alteradas**: nenhuma.

**Não tocado por restrição**: `copilot-cli-headroom.bat` e `copilot-cli-v1.bat` — CA02 da spec 033.

---

## 2. Problem Statement

> **Nota sobre as referências de linha desta seção**: os números citados para
> `pipeline_runner.py` são da **versão anterior ao refactor** (597 linhas), que nunca foi
> versionada — o arquivo estava como *untracked* quando esta entrega começou e hoje contém o shim.
> Não é possível conferi-los no histórico do git; estão registrados aqui como evidência do
> diagnóstico. As demais referências (`F1.yaml`, `copilot-cli-headroom.bat`, `agent_runner.py`,
> `headroom_tool.py`) apontam para arquivos versionados e são verificáveis.

### P-1 — O script não roda neste repositório

`pipeline_runner.py:40` fixava `WORKSPACE = Path(r"c:\_info\Projetos\Hub\SRC_Torre_Apps_31_07")` —
**outro checkout**. Todo caminho derivava dali: `.copilot-key`, `projects/`, as specs dos agentes.
Clonar o repo e rodar o script não funcionava, e a falha aparecia só na leitura da chave, depois de
o operador já ter respondido quatro menus.

### P-2 — Nenhum parâmetro de linha de comando

O script era 100% interativo (`input()` em 7 pontos). Consequências:

- Impossível rodar em CI, cron, ou script de operação
- Impossível repetir uma execução exatamente igual
- Impossível ensaiar: não havia como ver o que aconteceria sem gastar inferência
- Trocar de modelo exigia editar o `.py`

### P-3 — Configuração espalhada e duplicada

Modelo, endpoint, limites de contexto e `max_tokens` viviam como literais no código, e o mesmo
endpoint aparecia em pelo menos quatro lugares: `pipeline_runner.py:43`,
`copilot-cli-headroom.bat:24`, `agent_runner.py:109` e `headroom.yaml`. Mudar de deployment exigia
caçar todos.

O repositório já tinha registrado esse padrão de defeito: a porta do proxy duplicada entre
`headroom.yaml` e o `.bat` fez o launcher sondar 8787 com o proxy em 8788, falhar, e **degradar em
silêncio — rodando a fase inteira sem compressão** (`headroom_config.proxy_url`, docstring).

### P-4 — A tabela `PIPELINE` é o sexto espelho manual

`pipeline_runner.py:54-110` reescrevia à mão fase, agente e trigger de 18 passos. O repo já
identificou esse defeito duas vezes:

- `F1.yaml:10-16` — *"⚠️ RISCO R1 — quarta fonte de verdade. Este arquivo NÃO pode virar mais um
  espelho manual. O repo já tem três que divergem"*
- `copilot-cli-headroom.bat:150-151` — *"Resolve o orquestrador pelo agent_registry, NUNCA por um
  mapa local — um sexto espelho manual de fase→agente é o defeito que originou aquele módulo"*

E a tabela **já havia divergido**: repetia `TPT` na etapa de execução do QA, exatamente o defeito
que a spec 035 descreve como causa de o trigger `RS` nunca executar.

### P-5 — A spec do agente era encontrada por heurística

`pipeline_runner.py:147-168` varria `agents_root.rglob("*.md")`, aceitava qualquer arquivo cujo
*stem* contivesse o slug do agente, e entre os candidatos **escolhia o maior arquivo**. Nenhuma
verificação de identidade. Um agente com nome parecido, ou uma sub-skill grande, seria carregado no
lugar do agente pedido — sem aviso.

O `agent_registry` já entrega o caminho exato dos 107 agentes, com `dispatchable` e `deprecated`.

### P-6 — Nenhuma requisição passava pelo Headroom

O SDK apontava direto para o Foundry (`base_url=ENDPOINT`), então nenhuma execução do runner
aparecia no `.headroom/proxy-requests.jsonl`, nem se beneficiava da compressão de contexto — enquanto
o caminho interativo (`copilot-cli-headroom.bat`) roteava 100% pelo proxy.

### P-7 — Código morto e dependência não declarada

`import requests` na linha 14, nunca usado. `_WRITE_BLOCK` e `_MD_FILE_BLOCK` compilados e nunca
alcançados — `parse_and_write_outputs` retorna antes deles. `anthropic` importado no topo sem
nenhum arquivo de requisitos, contra a convenção stdlib-only do repo (IV7).

---

## 3. Decision

### 3.1 A ordem da esteira é declarada, não derivada

`pipeline.steps` no `ava-pipeline.yaml` é a **fonte de verdade da sequência**. Lista ordenada,
executada de cima para baixo:

| # | `phase` | `group` | Agente | Trigger |
|---|---|---|---|---|
| 1 | `F1` | `F1` | `ava-asis-orchestrator` | `FP` |
| 2 | `F2a` | `F2` | `ava-tobe-orchestrator` | `SD` |
| 3 | `F2b` | `F2` | `ava-devops-orchestrator` | `DP` |
| 4 | `F2c` | `F2` | `ava-qa-orchestrator` | `TPT` |
| 5 | `F3` | `F3` | `ava-prototype` | — |
| 6 | `F4` | `F4` | `ava-stack-orchestrator` | `SG` |
| 7 | `F5` | `F5` | `ava-devops-orchestrator` | `DE` |
| 8 | `F6` | `F6` | `ava-qa-orchestrator` | `QE` |
| 9 | `F8a` | `F8` | `ava-summary` | `SAS` |
| 10 | `F8b` | `F8` | `ava-summary-remediation` | — |
| 11 | `F8c` | `F8` | `ava-summary` | `SV` |
| 12 | `F8d` | `F8` | `ava-summary` | `SAS` |

**Por que declarada e não derivada do registry**: a ordem da esteira é decisão de processo. O
registry sabe *que agentes existem e a que módulo pertencem*, não *em que ordem o negócio quer
rodá-los*. Derivar a sequência do registry acoplaria a ordem de execução à organização dos módulos —
que é justamente onde os dois eixos divergem (§3.2).

**Por que não é um sexto espelho (P-4)**: o YAML declara apenas `phase`, `group`, `agent`, `trigger`
e `label`. Tudo o mais — caminho da spec, versão, módulo, despachabilidade — vem do
`agent_registry` em runtime, e `validate_plan()` reprova qualquer agente inexistente, deprecado ou
não-despachável com exit 2.

### 3.2 Etapa da esteira ≠ fase do módulo — divergência intencional

| | Esteira (`--phase`) | `agent_registry.PHASE_BY_MODULE` |
|---|---|---|
| `F5` | DevOps Execute | módulo `qa-agents` |
| `F6` | QA Quality Execute | módulo `devops-agents` |

São **dois eixos distintos**: a etapa é ordem de execução; a fase do registry é a que módulo o agente
pertence. `validate_plan()` **nunca** compara `step.phase` com `registry.phase` — valida só a
identidade do agente.

Sem isso registrado, alguém "alinharia" os dois eixos achando que é bug. O teste
`test_divergencia_de_fase_e_intencional` afirma explicitamente as duas metades e denuncia a mudança
de semântica.

### 3.3 O par planejar/executar dos orquestradores de dois momentos

DevOps e QA aparecem duas vezes, com **triggers diferentes**:

```
F2b  @ava-devops-orchestrator | DP    F2c  @ava-qa-orchestrator | TPT
F5   @ava-devops-orchestrator | DE    F6   @ava-qa-orchestrator | QE
```

A tabela do runner antigo repetia `TPT` na F6 — o defeito da spec 035. O gate do `QE` exige F4 Stack
**e** DevOps `DE` concluídos, satisfeitos pela ordem F4 → F5 → F6.

`test_orquestradores_de_dois_momentos_nao_repetem_o_trigger` trava os dois pares;
`test_execucao_vem_depois_do_planejamento` trava a ordem relativa e o pré-requisito do `QE`.

### 3.4 Uma fonte de configuração, com precedência declarada

```
1. flags do CLI            --model, --engine, --via-proxy
2. variáveis de ambiente   AVA_PIPELINE_* / AVA_FOUNDRY_*
3. project-config.yaml     bloco `pipeline:`
4. ava-pipeline.yaml
5. _FALLBACK_DEFAULTS      só se o YAML sumir ou faltar pyyaml
```

Porte fiel de `headroom_config.py`: mesmo `_deep_merge`, mesmo `_ENV_MAP`, mesma degradação. YAML
ilegível ou env malformada emitem aviso em stderr e **mantêm a camada de baixo** — a esteira não para
por causa de configuração ruim (IV3).

Dicionários fazem merge recursivo; **listas são substituídas por inteiro**, o que permite a um
projeto declarar sua própria `steps:` sem herdar posições da esteira padrão.

`_FALLBACK_DEFAULTS` traz `steps: []` de propósito: sem o YAML, o CLI **falha alto** em vez de rodar
uma esteira inventada de dentro do código.

### 3.5 O proxy Headroom é a rota padrão, e a degradação é ruidosa

A URL vem de `headroom_config.py --proxy-url` e o liveness de `headroom_tool.py proxy status` —
**nunca hardcoded**, ambos pelo venv isolado da tool (`prefer_tool_venv`), porque com o `python` do
PATH um interpretador ausente devolve exit ≠ 0 e o CLI concluiria "proxy fora do ar", rodando sem
compressão. É o defeito corrigido em `copilot-cli-headroom.bat:39-45`.

| Modo | Proxy no ar | Proxy fora do ar |
|---|---|---|
| `auto` *(padrão)* | usa o proxy | rota direta **com aviso alto** |
| `require` (`--via-proxy`) | usa o proxy | **aborta**, exit 2 |
| `off` (`--no-proxy`) | rota direta | rota direta |

A rota é a **única** diferença entre os dois caminhos: `base_url` = URL do proxy ou endpoint. O proxy
registra `POST /v1/messages`, encaminha o header de auth verbatim e faz passthrough de SSE, então
o SDK aponta para `http://host:port` **sem sufixo de path** — o `/anthropic` pertence ao upstream
(`ANTHROPIC_TARGET_API_URL`), não ao proxy local.

> Os 404 documentados em `agent_runner.py:683` para a rota via proxy vêm de `/v1/models/{id}`, rota
> que **só o Copilot CLI chama**. `messages.stream()` não a toca — a rota via proxy é limpa para o
> motor SDK.

### 3.6 Dois motores, com os limites ditos em voz alta

| | `--engine sdk` *(padrão)* | `--engine copilot` |
|---|---|---|
| Chamada | SDK Anthropic → Foundry | `agent_runner.py` → `copilot -p` |
| Tools do agente | nenhuma | tools reais |
| Artefatos | blocos `<!-- FILE: … -->` | o próprio agente escreve |
| Gate de artefato | não | sim (`artifact_gate`) |

Quando a etapa aponta para o **orquestrador da fase**, o motor `copilot` roda o DAG inteiro (sem
`--agent`): "F1 = @ava-asis-orchestrator | FP" significa "execute a fase F1 completa". Passar
`--agent ava-asis-orchestrator` filtraria zero nós — o orquestrador não é nó do DAG, é quem despacha.

**Duas limitações reais, sinalizadas em vez de mascaradas:**

1. **Só existe DAG para a F1.** O CLI avisa `⚠️ sem F2.yaml` por etapa e não executa.
2. **O trigger não é propagado.** O `agent_runner` monta o envelope pelo DAG e não conhece
   `DP`/`DE`/`TPT`/`QE`, então F2b e F5 colapsariam no mesmo comando. O CLI avisa e recomenda
   `--engine sdk` naquela etapa.

### 3.7 Seletores que cobrem os cinco pedidos

| Pedido | Flag | Comportamento |
|---|---|---|
| nome do projeto | `-p/--project` | obrigatório em `run`; projeto inexistente → exit 2 listando os disponíveis |
| fase opcional | `--phase ID` | casa `phase` (`F2b`) **ou** `group` (`F2`); repetível; aceita `F1,F2` |
| todas as fases | `--all` | os 12 passos, na ordem declarada |
| modelo de LLM | `--model` | wire model ou alias; vence toda a configuração |
| agente específico | `--agent ID` | da esteira (com trigger) ou avulso do registry (sem trigger) |

`--phase` sempre preserva a **ordem do YAML**, não a de digitação. `--agent` de um agente que aparece
duas vezes traz as duas etapas, cada uma com seu trigger; combinar com `--phase` fixa um momento.

### 3.8 O `.copilot-key` continua fora do repositório

O caminho é configurável (`foundry.api_key_file`), resolvido a partir de `REPO_ROOT`, e a leitura
falha com instrução acionável (exit 2) quando o arquivo falta ou está vazio. O CLI nunca imprime a
chave; o `doctor` reporta só o nome do arquivo.

Artefatos com caminho que escape de `projects/{PROJETO}/` são **recusados** na escrita: o caminho vem
do modelo, então nada garante que seja bem-comportado.

### 3.9 O que esta spec deliberadamente NÃO faz

- **Não cria `F2..F8.yaml`** em `pipeline-dag/`. Sem eles `--engine copilot` só cobre a F1 de verdade.
- **Não altera nenhuma spec de agente.** Nenhum `.md` de agente, `module.yaml` ou `SKILL.md` é tocado.
- **Não altera os dois `.bat` de sessão interativa** (CA02 da spec 033).
- **Não cria registro canônico de triggers.** Os códigos seguem em prosa nos `.md` dos
  orquestradores; o `ava-pipeline.yaml` é o primeiro lugar estruturado, não a unificação.
- **Não corrige o `headroom_tool.py attribute`.** Ver §7.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Ensaio sem custo (CA01, P1)

**Story**: Como operador da esteira, quero ver exatamente o que será executado antes de gastar
inferência.

1. **Given** a valid project, **When** `run -p PROJ --all --dry-run` executes, **Then** it prints the
   12 steps in declared order, the resolved route, and the estimated prompt size per step, and exits 0.
2. **Given** the above, **Then** no network request is issued and no artifact is written.

### Scenario 2 — Uma única fonte de configuração (CA02, P1)

1. **Given** `ava-pipeline.yaml` declares `models.default`, **When** `config` runs, **Then** the
   effective model reflects the YAML.
2. **Given** `AVA_FOUNDRY_MODEL` is set, **When** `config` runs, **Then** the env value wins over the YAML.
3. **Given** `--model` is passed, **Then** it wins over both.
4. **Given** the source of `pipeline_config.py`, **Then** no code constant contains `8787` or
   `127.0.0.1`, and `ava_pipeline.py` contains no endpoint or model literal.

### Scenario 3 — A ordem da esteira é honrada (CA03, P1)

1. **Given** the declared steps, **When** `list --phases` runs, **Then** it emits exactly the 12 steps
   in the table order of §3.1.
2. **Given** `--phase F8 --phase F1`, **Then** F1 executes before F8 — YAML order, not typing order.
3. **Given** step F2b, **Then** the prompt is `@ava-devops-orchestrator | DP | project: {P}`.

### Scenario 4 — Planejar antes de executar (CA04, P1)

1. **Given** the plan, **Then** `ava-devops-orchestrator` appears with triggers `["DP", "DE"]` and
   `ava-qa-orchestrator` with `["TPT", "QE"]` — never the same trigger twice.
2. **Given** the plan, **Then** F2b precedes F5, F2c precedes F6, and both F4 and F5 precede F6.

### Scenario 5 — Rota via proxy, degradação avisada (CA05, P1)

1. **Given** the Headroom proxy is up, **When** a run starts in `auto`, **Then** the route is the
   proxy URL resolved by `headroom_config.py`, with no path suffix.
2. **Given** the proxy is down and mode is `auto`, **Then** the run proceeds on the direct endpoint
   **and prints an explicit "SEM compressão" warning**.
3. **Given** the proxy is down and `--via-proxy` was passed, **Then** the run aborts with exit 2 and
   never issues an uncompressed request.
4. **Given** `--no-proxy`, **Then** the proxy is not probed at all.

### Scenario 6 — A spec certa do agente (CA06, P1)

1. **Given** any step, **Then** `spec_path` equals `REPO_ROOT / agent_registry.get(agent)["path"]`
   and the file exists.
2. **Given** an agent absent, deprecated, or non-dispatchable in the registry, **Then**
   `validate_plan` reports it and the CLI exits 2 without executing anything.

### Scenario 7 — Rodar um agente isolado (CA07, P2)

1. **Given** `--agent ava-asis-inventory` (not in the pipeline), **Then** the plan has one ad-hoc
   step with no trigger and the spec path from the registry.
2. **Given** `--agent ava-devops-orchestrator`, **Then** both F2b (`DP`) and F5 (`DE`) are planned.
3. **Given** an unknown agent id, **Then** the CLI exits 2 listing the pipeline agents.

### Scenario 8 — Degradar, nunca quebrar (CA08, P2)

1. **Given** a malformed env var, **When** config loads, **Then** a warning goes to stderr and the
   lower layer value is preserved.
2. **Given** an unreadable YAML, **Then** `load_config` returns the fallback without raising.
3. **Given** `pipeline.steps` is empty, **Then** the CLI fails loudly rather than running an
   invented pipeline.

### Scenario 9 — Compatibilidade do ponto de entrada antigo (CA09, P2)

1. **Given** `python pipeline_runner.py`, **Then** a deprecation warning is printed, the project
   picker is offered, and execution delegates to the CLI.
2. **Given** `git diff` on `copilot-cli-headroom.bat` and `copilot-cli-v1.bat`, **Then** there is no
   output — the interactive session path is untouched.

### Scenario 10 — Artefato fora do projeto é recusado (CA10, P1)

1. **Given** a model response with a `FILE:` path escaping `projects/{P}/`, **Then** the file is not
   written and a warning is printed.

---

## 5. Quality Gate Requirements

- [x] Nenhuma versão de tecnologia, endpoint ou modelo hardcoded em código (Article I) — verificado
      por AST em `test_pipeline_config.py`
- [x] Nenhuma spec de agente, `module.yaml` ou `SKILL.md` alterado — Categories 4 e 1.5 = N/A
      (Articles IV, XI)
- [x] Sequência da esteira compatível com o contrato de execução do pipeline (Article III), com a
      divergência de eixos documentada em §3.2
- [x] Documentação e comentários em português brasileiro (Article V)
- [x] Cenários BDD cobrindo caminho nominal, borda e gate (Article VI)
- [x] Impacto no sub-pipeline de segurança: nenhum — `security_enabled_asis` segue governado pelo
      `project-config.yaml` (Article VII)
- [x] Entrada em `CHANGELOG.md` (Article X)
- [x] Sem marcadores `[NEEDS CLARIFICATION]`

---

## 6. Dependencies

| Dependência | Componente | Razão |
|---|---|---|
| Catálogo canônico | `src/shared/tools/agent_registry.py` | `spec_path`, versão, módulo, despachabilidade |
| Proxy | `src/shared/tools/headroom/headroom_config.py` | URL efetiva do proxy (`--proxy-url`) |
| Proxy | `src/shared/tools/headroom/headroom_tool.py` | Liveness (`proxy status`, exit 0 = no ar) |
| Motor alternativo | `src/shared/tools/agent_runner.py` | `--engine copilot` |
| DAG | `src/shared/data/pipeline-dag/F1.yaml` | Único DAG existente hoje |
| Runtime | `anthropic` ≥ 0.60, `pyyaml` ≥ 6.0 | `requirements-pipeline.txt` |
| Rede | VPN `vnet-core-brs-001` | O endpoint do Foundry é *private endpoint* |
| Credencial | `.copilot-key` na raiz | Não versionado |

---

## 7. Exclusions

- **`F2..F8.yaml` em `pipeline-dag/`** — sem eles `--engine copilot` só cobre a F1.
- **Propagação de trigger no motor `copilot`** — exigiria um DAG por etapa, não por fase.
- **Registro canônico de triggers** — os códigos seguem em prosa nos `.md` dos orquestradores.
- **Bug em `headroom_tool.py attribute`** — os aliases `_BEFORE_KEYS`/`_AFTER_KEYS`/`_LATENCY_KEYS`
  (`headroom_tool.py:127-131`) não batem com os campos reais do JSONL do proxy
  (`input_tokens_original` / `input_tokens_optimized` / `total_latency_ms`), então toda linha seria
  descartada. **Não confirmado empiricamente** — `.headroom/proxy-requests.jsonl` nunca foi escrito
  neste checkout. A primeira execução real via proxy permite confirmar.
- **Paralelismo entre etapas** — a esteira é sequencial por design; `max_parallel: 1` no DAG da F1.
- **Retomada automática (`--resume`)** — o `run.json` registra o estado, mas retomar é manual via
  `--from`.

---

## 8. Assumptions

- O projeto existe em `projects/{PROJECT_NAME}/` com `context/project-config.yaml`.
- O `.copilot-key` está na raiz do repo, com a chave do Foundry e sem newline.
- A VPN está conectada quando há execução real; o `--dry-run` não depende de rede.
- O `agent_registry` reflete o disco — `generate_agent_wrappers.py --check` é o gate desse contrato,
  fora do escopo desta spec.
- Os orquestradores de fase aceitam o formato de prompt `@{agent} | {trigger} | project: {P}`,
  preservado literalmente do runner anterior.
- O modelo respeita o contrato de saída `<!-- FILE: … -->` no motor `sdk`; quando não respeita, o CLI
  avisa que nenhum bloco foi encontrado em vez de falhar em silêncio.

---

## Success Criteria

| Critério | Medida |
|---|---|
| Ordem da esteira | `list --phases` emite os 12 passos da tabela §3.1; `test_pipeline_plan.py` verde |
| Fonte única | `pipeline_config.py` sem `8787`/`127.0.0.1`; `ava_pipeline.py` sem endpoint/modelo — verificado por AST |
| Parametrização | `-p`, `--phase`, `--all`, `--model`, `--agent` cobertos por teste e por `--dry-run` |
| Rota via proxy | `doctor` reporta o proxy; execução real acrescenta linha em `.headroom/proxy-requests.jsonl` |
| Degradação | `auto` com proxy fora do ar imprime "SEM compressão"; `require` sai 2 |
| Custo zero no ensaio | `--dry-run` de todos os seletores sai 0 sem chamada de rede |
| Sem regressão | `copilot-cli-headroom.bat` e `copilot-cli-v1.bat` com `git diff --exit-code` vazio |
| Compatibilidade | `pipeline_runner.py` roda pelo shim, com aviso de depreciação |
