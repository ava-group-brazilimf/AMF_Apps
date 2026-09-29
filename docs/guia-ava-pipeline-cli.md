# Guia do CLI da Esteira (`ava-pipeline`)

> **Escopo**: orquestração ponta a ponta da esteira de agentes AVA Fabric
>
> **Executável**: `src/shared/tools/ava_pipeline.py` · atalho de raiz: `ava-pipeline.bat`
> **Configuração**: `src/shared/data/ava-pipeline.yaml`
> **Substitui**: `pipeline_runner.py` (deprecado, mantido como shim)

---

## Índice

1. [O que é](#1-o-que-é)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Início rápido](#3-início-rápido)
4. [A ordem da esteira](#4-a-ordem-da-esteira)
5. [Subcomandos](#5-subcomandos)
6. [Referência de parâmetros — `run`](#6-referência-de-parâmetros--run)
7. [Como escolher o que rodar](#7-como-escolher-o-que-rodar)
8. [Rota e proxy Headroom](#8-rota-e-proxy-headroom)
9. [Motores: `sdk` e `copilot`](#9-motores-sdk-e-copilot)
10. [Configuração e precedência](#10-configuração-e-precedência)
11. [Modo interativo](#11-modo-interativo)
12. [Onde ficam as saídas](#12-onde-ficam-as-saídas)
13. [Exit codes](#13-exit-codes)
14. [Receitas](#14-receitas)
15. [Solução de problemas](#15-solução-de-problemas)
16. [Migração do `pipeline_runner.py`](#16-migração-do-pipeline_runnerpy)

---

## 1. O que é

O `ava-pipeline` executa a esteira de modernização — do diagnóstico AS-IS ao
summary executivo — **uma etapa por vez, cada uma em contexto isolado**. Cada
etapa invoca um agente (normalmente o orquestrador da fase) com um trigger, e o
CLI cuida de montar o prompt, escolher a rota até o Foundry, gravar os artefatos
e registrar o estado do run.

Ele resolve três coisas que o runner anterior não resolvia:

|                | Antes (`pipeline_runner.py`)  | Agora (`ava-pipeline`)                |
| -------------- | ------------------------------- | --------------------------------------- |
| Invocação    | só menu interativo             | CLI parametrizável e scriptável       |
| Configuração | hardcoded no`.py`             | `ava-pipeline.yaml`, uma fonte só    |
| Rota           | Foundry direto                  | proxy Headroom com degradação avisada |
| Spec do agente | heurística por nome de arquivo | caminho exato do`agent_registry`      |
| Ensaio         | não existia                    | `--dry-run` com custo zero            |

---

## 2. Pré-requisitos

| Item                       | Como verificar                                                | Obrigatório para      |
| -------------------------- | ------------------------------------------------------------- | ---------------------- |
| Python 3.10+               | `python --version`                                          | tudo                   |
| VPN`vnet-core-brs-001`   | o endpoint é*private endpoint*                             | execução real        |
| `.copilot-key` na raiz   | arquivo com a API Key do Foundry,**sem newline**        | execução real        |
| `anthropic` + `pyyaml` | `pip install -r src/shared/tools/requirements-pipeline.txt` | `--engine sdk`       |
| Proxy Headroom             | `.\src\shared\tools\headroom\run_standalone.ps1`            | opcional (compressão) |

O `doctor` confere tudo isso de uma vez:

```powershell
python src/shared/tools/ava_pipeline.py doctor -p MeuERP-002
```

```
  ✅ config                 src\shared\data\ava-pipeline.yaml
  ✅ API key                .copilot-key
  ✅ SDK anthropic          0.116.0
  ✅ proxy Headroom         http://127.0.0.1:8787 no ar
  ✅ plano da esteira       12 passos
  ✅ projeto                MeuERP-002
  ✅ project-config.yaml    ok

  modelo=claude-sonnet-4-6 · endpoint=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
```

> O proxy fora do ar **não** reprova o `doctor` (exit 0): é degradação prevista,
> não erro de configuração. Os demais itens em ❌ dão exit 2.

---

## 3. Início rápido

```powershell
# 1. O que existe e em que ordem
.\ava-pipeline.bat list --phases

# 2. Diagnóstico do ambiente
.\ava-pipeline.bat doctor -p MeuERP-002

# 3. Ensaio da esteira inteira — NÃO gasta inferência
.\ava-pipeline.bat run -p MeuERP-002 --all --dry-run

# 4. Execução real de uma etapa só, confirmando cada passo
.\ava-pipeline.bat run -p MeuERP-002 --phase F1
```

As três formas de chamar são equivalentes:

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all             # atalho de raiz
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --all
python pipeline_runner.py run -p MeuERP-002 --all      # shim deprecado
```

---

## 4. A ordem da esteira

Declarada em `src/shared/data/ava-pipeline.yaml` → `pipeline.steps`. É a **fonte
de verdade da sequência**: `--all` executa exatamente estes 12 passos, de cima
para baixo.

| #  | `--phase` | Grupo  | Agente                      | Trigger | Etapa                                 |
| -- | ----------- | ------ | --------------------------- | ------- | ------------------------------------- |
| 1  | `F1`      | `F1` | `ava-asis-orchestrator`   | `FP`  | AS-IS Diagnostic — Full Pipeline     |
| 2  | `F2a`     | `F2` | `ava-tobe-orchestrator`   | `SD`  | TO-BE Architecture — Solution Design |
| 3  | `F2b`     | `F2` | `ava-devops-orchestrator` | `DP`  | DevOps Plan                           |
| 4  | `F2c`     | `F2` | `ava-qa-orchestrator`     | `TPT` | QA — Test Plan & Strategy            |
| 5  | `F3`      | `F3` | `ava-prototype`           | —      | Prototype                             |
| 6  | `F4`      | `F4` | `ava-stack-orchestrator`  | `SG`  | Tech Stack — Stack Generation        |
| 7  | `F5`      | `F5` | `ava-devops-orchestrator` | `DE`  | DevOps Execute                        |
| 8  | `F6`      | `F6` | `ava-qa-orchestrator`     | `QE`  | QA — Quality Execute                 |
| 9  | `F8a`     | `F8` | `ava-summary`             | `SAS` | Summary — Generate                   |
| 10 | `F8b`     | `F8` | `ava-summary-remediation` | —      | Summary — Remediation                |
| 11 | `F8c`     | `F8` | `ava-summary`             | `SV`  | Summary — Validate                   |
| 12 | `F8d`     | `F8` | `ava-summary`             | `SAS` | Summary — Final                      |

O prompt enviado em cada passo é:

```
@{agente} | {trigger} | project: {PROJETO}      # com trigger
@{agente} project: {PROJETO}                    # sem trigger (F3, F8b)
```

### Dois orquestradores rodam duas vezes

DevOps e QA aparecem em dois momentos, com **triggers diferentes** — planejar
antes, executar depois:

```
F2b  @ava-devops-orchestrator | DP   →  planeja
F5   @ava-devops-orchestrator | DE   →  executa (depois da F4 Stack)

F2c  @ava-qa-orchestrator     | TPT  →  planeja
F6   @ava-qa-orchestrator     | QE   →  executa (depois da F4 e da F5)
```

O gate do `QE` exige F4 Stack **e** DevOps `DE` concluídos — por isso a F6 vem
depois da F5. Repetir `TPT` na F6 rodaria o planejamento de novo e a esteira de
execução do QA (`GR→BM→…→PT→RS`) nunca dispararia.

### ⚠️ As etapas não são os módulos do `agent_registry`

Isto é intencional e **não deve ser "corrigido"**:

|        | Esteira (`--phase`) | `agent_registry` (módulo) |
| ------ | --------------------- | ---------------------------- |
| `F5` | DevOps Execute        | módulo`qa-agents`         |
| `F6` | QA Quality Execute    | módulo`devops-agents`     |

São dois eixos diferentes: a etapa é **ordem de execução**, a fase do registry é
**a que módulo o agente pertence**. O validador do plano confere só que o agente
existe, é despachável e não está deprecado — nunca compara os dois eixos.
`tests/tools/test_pipeline_plan.py` trava esse contrato.

**Não há F7 na esteira.** O módulo F7 (deliverables) não é executado pelo CLI.

---

## 5. Subcomandos

```
ava-pipeline {run,list,config,doctor} [opções]
```

### `run` — executa a esteira

O subcomando principal. Detalhado na [seção 6](#6-referência-de-parâmetros--run).

### `list` — mostra a esteira ou o catálogo

| Parâmetro        | Descrição                                            |
| ----------------- | ------------------------------------------------------ |
| `--phases`      | Ordem da esteira (padrão quando nenhum flag é dado)  |
| `--agents`      | Catálogo completo do`agent_registry` (~107 agentes) |
| `--phase F1`    | Filtra`--agents` pela fase **do módulo**      |
| `-p, --project` | Aplica o bloco`pipeline:` do `project-config.yaml` |

```powershell
.\ava-pipeline.bat list --phases
.\ava-pipeline.bat list --agents
.\ava-pipeline.bat list --agents --phase F1
```

```
  F1   ava-asis-bridge-fastqa                    v4.1.0
  F1   ava-asis-db-analyzer                      v1.6.1
  F1   ava-asis-documentation                    v3.1.1
  ...
```

> `list --phases` sai com código 2 se o plano divergir do `agent_registry` —
> serve como gate barato antes de qualquer execução.

### `config` — mostra a configuração efetiva

Emite JSON com todas as camadas já resolvidas.

```powershell
.\ava-pipeline.bat config                      # defaults + ambiente
.\ava-pipeline.bat config -p MeuERP-002        # + bloco pipeline: do projeto
```

Para consumo em script, o módulo de config tem saídas de uma linha:

```powershell
python src/shared/tools/pipeline_config.py --model      # claude-sonnet-4-6
python src/shared/tools/pipeline_config.py --endpoint   # https://...
```

### `doctor` — diagnostica o ambiente

Confere config, API key, SDK, proxy, plano e (com `-p`) o projeto. Ver
[seção 2](#2-pré-requisitos).

---

## 6. Referência de parâmetros — `run`

```
ava-pipeline run -p PROJETO [--phase ID | --all] [--agent ID]
                 [--model MODEL] [--engine {sdk,copilot}] [--from ID]
                 [--via-proxy | --no-proxy] [--yes] [--dry-run] [--json]
```

### Projeto

| Parâmetro            | Obrigatório  | Descrição                                        |
| --------------------- | ------------- | -------------------------------------------------- |
| `-p`, `--project` | **sim** | Nome da pasta em`projects/`. Ex.: `MeuERP-002` |

Projeto inexistente sai com código 2 e lista os disponíveis.

### Seleção de etapas

`--phase` e `--all` são **mutuamente exclusivos**.

| Parâmetro     | Descrição                                                                              |
| -------------- | ---------------------------------------------------------------------------------------- |
| `--phase ID` | Etapa (`F2b`) **ou** grupo (`F2`). Repetível; aceita lista: `--phase F1,F2` |
| `--all`      | Todas as 12 etapas, na ordem da esteira                                                  |
| `--agent ID` | Roda só este agente — da esteira ou avulso do`agent_registry`                        |
| `--from ID`  | Começa nesta etapa, descartando o prefixo                                               |

Sem `--phase`, sem `--all` e sem `--agent`, o CLI abre um **menu interativo** de
grupos.

> `--phase` sempre preserva a **ordem do YAML**, não a ordem de digitação:
> `--phase F8 --phase F1` executa F1 antes de F8.

### Modelo

| Parâmetro        | Descrição                                              |
| ----------------- | -------------------------------------------------------- |
| `--model MODEL` | Wire model (`claude-sonnet-4-6`) ou alias (`sonnet`) |

Vence qualquer outra camada de configuração. Aliases ficam em
`ava-pipeline.yaml` → `models.aliases`.

### Motor

| Parâmetro           | Descrição                                                             |
| -------------------- | ----------------------------------------------------------------------- |
| `--engine sdk`     | SDK Anthropic direto (padrão). Ver[seção 9](#9-motores-sdk-e-copilot) |
| `--engine copilot` | Delega ao`agent_runner.py` (processo isolado por agente)              |

### Rota

`--via-proxy` e `--no-proxy` são **mutuamente exclusivos**.

| Parâmetro      | Efeito                                                                             |
| --------------- | ---------------------------------------------------------------------------------- |
| *(nenhum)*    | `mode: auto` — usa o proxy se estiver no ar, senão degrada **com aviso** |
| `--via-proxy` | Exige o proxy;**aborta** (exit 2) se estiver fora do ar                      |
| `--no-proxy`  | Força a rota direta, sem compressão                                              |

### Execução

| Parâmetro        | Descrição                                                       |
| ----------------- | ----------------------------------------------------------------- |
| `--yes`, `-y` | Não pergunta a cada passo                                        |
| `--dry-run`     | Mostra plano, rota e tamanho do prompt.**Zero inferência** |
| `--json`        | Emite o resultado consolidado em JSON no final                    |

---

## 7. Como escolher o que rodar

### Esteira inteira

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all --yes
```

### Um grupo de fase

`--phase F2` roda os três passos da F2 (`F2a` → `F2b` → `F2c`):

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --phase F2
```

### Uma etapa específica

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --phase F2b     # só o DevOps Plan (DP)
.\ava-pipeline.bat run -p MeuERP-002 --phase F8c     # só o Summary Validate (SV)
```

### Várias etapas

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --phase F1 --phase F2
.\ava-pipeline.bat run -p MeuERP-002 --phase F1,F2,F4      # equivalente
```

### Retomar do meio

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all --from F4
# executa F4 · F5 · F6 · F8a · F8b · F8c · F8d
```

### Um agente só

Três comportamentos, conforme o agente:

```powershell
# 1. Agente que aparece UMA vez na esteira → aquela etapa, com seu trigger
.\ava-pipeline.bat run -p MeuERP-002 --agent ava-stack-orchestrator
#    → F4  | SG

# 2. Agente que aparece DUAS vezes → ambas as etapas, cada uma com seu trigger
.\ava-pipeline.bat run -p MeuERP-002 --agent ava-devops-orchestrator
#    → F2b | DP
#    → F5  | DE

#    Para fixar um momento só, combine com --phase:
.\ava-pipeline.bat run -p MeuERP-002 --agent ava-devops-orchestrator --phase F5

# 3. Agente FORA da esteira → passo avulso, sem trigger
.\ava-pipeline.bat run -p MeuERP-002 --agent ava-asis-inventory
#    → @ava-asis-inventory project: MeuERP-002
```

Agente que não existe nem na esteira nem no `agent_registry` sai com código 2 e
lista os da esteira.

---

## 8. Rota e proxy Headroom

O proxy Headroom comprime o contexto antes de a requisição chegar ao Foundry e
registra tokens e latência por requisição.

### Como o CLI resolve a rota

1. Pergunta a URL efetiva a `headroom_config.py --proxy-url` — **nunca hardcoded**
2. Testa liveness com `headroom_tool.py proxy status` (exit 0 = no ar)
3. Decide conforme o modo:

| Modo                          | Proxy no ar | Proxy fora do ar                    |
| ----------------------------- | ----------- | ----------------------------------- |
| `auto` *(padrão)*        | usa o proxy | rota direta**com aviso alto** |
| `require` (`--via-proxy`) | usa o proxy | **aborta**, exit 2            |
| `off` (`--no-proxy`)      | rota direta | rota direta                         |

A rota aparece no banner de todo `run`:

```
  Rota     : proxy (Headroom) → http://127.0.0.1:8787
  Rota     : direta → https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
```

E a degradação nunca é silenciosa:

```
  ⚠️  Headroom proxy não respondeu em http://127.0.0.1:8787.
      Degradando para o endpoint direto — SEM compressão de contexto.
      Para ativar: .\src\shared\tools\headroom\run_standalone.ps1
```

### Subir o proxy

```powershell
.\src\shared\tools\headroom\setup.ps1            # uma vez
.\src\shared\tools\headroom\run_standalone.ps1   # noutra aba, mantém em foreground

# ou, em background:
python src/shared/tools/headroom/headroom_tool.py proxy start
python src/shared/tools/headroom/headroom_tool.py proxy status
```

### Conferir que passou pelo proxy

O JSONL só ganha linha quando há tráfego real:

```powershell
Get-Content .headroom/proxy-requests.jsonl -Tail 1 | ConvertFrom-Json |
  Select-Object model, input_tokens_original, input_tokens_optimized, total_latency_ms
```

> **Por que o `base_url` do proxy não leva `/anthropic`**: o SDK acrescenta
> `/v1/messages`, que é rota registrada no proxy. O sufixo `/anthropic` pertence
> ao **upstream** (`ANTHROPIC_TARGET_API_URL`), não ao proxy local.

---

## 9. Motores: `sdk` e `copilot`

|                                | `--engine sdk` *(padrão)*          | `--engine copilot`                      |
| ------------------------------ | --------------------------------------- | ----------------------------------------- |
| Como chama                     | SDK Anthropic → Foundry                | `agent_runner.py` → `copilot -p`     |
| Tools do agente                | **nenhuma**                       | tools reais (view/create/edit/powershell) |
| Como grava artefatos           | blocos`<!-- FILE: … -->` na resposta | o próprio agente escreve                 |
| Gate de artefato               | não                                    | sim (`artifact_gate`)                   |
| Telemetria                     | log`.md` por passo                    | `pipeline_observer`                     |
| Streaming no terminal          | sim                                     | não                                      |
| Precisa do pacote`anthropic` | sim                                     | não                                      |

### Duas limitações reais do motor `copilot`

**1. Só existe DAG para a F1.** `src/shared/data/pipeline-dag/` tem apenas
`F1.yaml`. Nas outras etapas o CLI avisa e não executa:

```
  F1   ✅          agent_runner.py --project MeuERP-002 --phase F1
  F2a  ⚠️  sem F2.yaml  agent_runner.py --project MeuERP-002 --phase F2
```

**2. O trigger não é propagado.** O `agent_runner` monta o envelope a partir do
DAG e não conhece `DP`/`DE`/`TPT`/`QE` — as etapas F2b e F5 colapsam no mesmo
comando. O CLI avisa e recomenda `--engine sdk` naquela etapa:

```
  ⚠️  trigger 'DP' NÃO é propagado pelo motor copilot — o agent_runner monta o envelope pelo DAG.
      Para honrar o trigger, use --engine sdk nesta etapa.
```

> Quando a etapa aponta para o **orquestrador da fase**, o motor `copilot` roda o
> DAG inteiro (sem `--agent`): "F1 = @ava-asis-orchestrator | FP" significa
> "execute a fase F1 completa".

---

## 10. Configuração e precedência

Tudo vive em **`src/shared/data/ava-pipeline.yaml`**. Não há endpoint, modelo ou
porta hardcoded no código — há teste que reprova isso.

```
1. flags do CLI            --model, --engine, --via-proxy
2. variáveis de ambiente   AVA_PIPELINE_* / AVA_FOUNDRY_*
3. projects/{p}/context/project-config.yaml → bloco `pipeline:`
4. src/shared/data/ava-pipeline.yaml
5. _FALLBACK_DEFAULTS      (só se o YAML sumir ou faltar pyyaml)
```

### Blocos do YAML

| Bloco             | Contém                                                                                              |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| `foundry`       | `endpoint`, `api_key_file`, `anthropic_version`, `max_tokens`                                |
| `models`        | `default` (wire model), `provider_model_id`, `aliases`                                         |
| `proxy`         | `mode`, `url_command`, `status_command`, `prefer_tool_venv`                                  |
| `execution`     | `engine`, `confirm`, `timeout_s`, `output_subdir`                                            |
| `context`       | `skill_chars`, `file_chars`, `max_artifacts`, `max_artifact_bodies`, `artifact_body_chars` |
| `dns_overrides` | `enabled`, `hosts` — patch de DNS para ambientes sem split-DNS                                  |
| `steps`         | **a ordem da esteira**                                                                         |

### Variáveis de ambiente

| Variável                          | Sobrescreve                  |
| ---------------------------------- | ---------------------------- |
| `AVA_FOUNDRY_ENDPOINT`           | `foundry.endpoint`         |
| `AVA_FOUNDRY_MODEL`              | `models.default`           |
| `AVA_FOUNDRY_API_KEY_FILE`       | `foundry.api_key_file`     |
| `AVA_PIPELINE_MAX_TOKENS`        | `foundry.max_tokens`       |
| `AVA_PIPELINE_PROVIDER_MODEL_ID` | `models.provider_model_id` |
| `AVA_PIPELINE_PROXY_MODE`        | `proxy.mode`               |
| `AVA_PIPELINE_ENGINE`            | `execution.engine`         |
| `AVA_PIPELINE_CONFIRM`           | `execution.confirm`        |
| `AVA_PIPELINE_TIMEOUT_S`         | `execution.timeout_s`      |
| `AVA_PIPELINE_DNS_OVERRIDES`     | `dns_overrides.enabled`    |

```powershell
$env:AVA_FOUNDRY_MODEL = "claude-opus-4-6"
python src/shared/tools/pipeline_config.py --model      # claude-opus-4-6
Remove-Item Env:\AVA_FOUNDRY_MODEL
```

Valor malformado (`AVA_PIPELINE_MAX_TOKENS=abc`) **não derruba o CLI**: emite
aviso em stderr e mantém a camada de baixo.

### Sobrescrever por projeto

Em `projects/{PROJETO}/context/project-config.yaml`:

```yaml
pipeline:
  models:
    default: "claude-opus-4-6"
  proxy:
    mode: "require"
  steps:                      # substituição TOTAL da esteira, não merge
    - { phase: "F1", group: "F1", agent: "ava-asis-orchestrator", trigger: "FP", label: "AS-IS" }
    - { phase: "F8a", group: "F8", agent: "ava-summary", trigger: "SAS", label: "Summary" }
```

> Dicionários fazem merge recursivo; **listas são substituídas por inteiro**. É o
> que permite um projeto declarar uma esteira reduzida sem herdar posições.

---

## 11. Modo interativo

Sem `--yes`, cada passo pede confirmação:

```
════════════════════════════════════════════════════════════════════
  Passo 3/12 — F2b
  DevOps Plan
  Agente : @ava-devops-orchestrator (v1.0.0)
  Trigger: DP
════════════════════════════════════════════════════════════════════
  ✅F1  ✅F2a  ▶F2b  ○F2c  ○F3  ○F4  ○F5  ○F6  ○F8a  ○F8b  ○F8c  ○F8d

  Executar? [S]im / [P]ular / [V]er skill / [A]bortar:
```

| Tecla            | Ação                                                          |
| ---------------- | --------------------------------------------------------------- |
| `S` ou Enter   | Executa o passo                                                 |
| `P` (ou `N`) | Pula, seguindo para o próximo                                  |
| `V`            | Mostra os primeiros 2.000 caracteres da spec e pergunta de novo |
| `A`            | Aborta a esteira (exit 130)                                     |

Se um passo falhar, o CLI oferece retentativa antes de seguir.

Para desligar as perguntas de forma permanente, use `execution.confirm: auto` no
YAML em vez de digitar `--yes` sempre.

---

## 12. Onde ficam as saídas

```
projects/{PROJETO}/outputs/
├── pipeline_runner/                       # log .md por passo executado
│   └── F2b_ava-devops-orchestrator_20260805_143022.md
├── .runs/{run_id}/
│   └── run.json                           # plano, rota, modelo, status por etapa
└── ...                                    # artefatos gerados pelos agentes
```

O log de cada passo traz agente, trigger, modelo, data, lista de arquivos
escritos, o prompt enviado e a resposta completa.

O `run.json` é o estado consolidado — útil para saber o que foi executado,
pulado ou falhou, e por qual rota.

> Artefatos com caminho que escape de `projects/{PROJETO}/` são **recusados**: o
> caminho vem do modelo, então nada garante que seja bem-comportado.

---

## 13. Exit codes

| Código | Significado                                                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0`   | Todas as etapas executadas ou puladas                                                                                                                   |
| `1`   | Ao menos uma etapa falhou                                                                                                                               |
| `2`   | Erro de configuração — projeto inexistente,`.copilot-key` ausente, agente fora do registry, plano divergente, `--via-proxy` com proxy fora do ar |
| `130` | Abortado pelo usuário (`A` no prompt, ou Ctrl+C)                                                                                                     |

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all --yes
if ($LASTEXITCODE -ne 0) { throw "esteira falhou (exit $LASTEXITCODE)" }
```

---

## 14. Receitas

### Ensaiar tudo antes de gastar inferência

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all --dry-run
```

```
  F1   prompt ≈   391,056 chars (~97,764 tokens)  | @ava-asis-orchestrator | FP | project: MeuERP-002
  F2a  prompt ≈   399,091 chars (~99,772 tokens)  | @ava-tobe-orchestrator | SD | project: MeuERP-002
  ...
```

Serve para dimensionar o contexto por etapa e conferir os triggers antes de rodar.

### Rodar a noite inteira, sem interação, exigindo compressão

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all --yes --via-proxy --json > run.json
```

### Regerar só o ciclo de summary

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --phase F8 --yes
# F8a (SAS) → F8b (remediation) → F8c (SV) → F8d (SAS)
```

### Refazer a partir da geração de código

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --all --from F4 --yes
```

### Testar um agente isolado com outro modelo

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --agent ava-asis-inventory --model claude-opus-4-6
```

### Rodar a F1 com processo isolado por agente

```powershell
.\ava-pipeline.bat run -p MeuERP-002 --phase F1 --engine copilot --yes
```

### Gate barato em CI

```powershell
.\ava-pipeline.bat list --phases                        # exit 2 se divergir do registry
.\ava-pipeline.bat doctor -p MeuERP-002                 # exit 2 se faltar config
.\ava-pipeline.bat run -p MeuERP-002 --all --dry-run    # exit 0, sem rede
python -m pytest tests/tools/test_pipeline_plan.py tests/tools/test_pipeline_config.py -q
```

---

## 15. Solução de problemas

| Sintoma                                         | Causa provável                                   | Ação                                                                                       |
| ----------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `ERRO: projeto não encontrado`               | nome errado ou projeto não criado                | O erro lista os disponíveis; confira`projects/`                                           |
| `ERRO: .copilot-key não encontrado`          | chave ausente na raiz                             | Crie o arquivo com a API Key,**sem newline**                                           |
| `ERRO: o pacote anthropic é necessário`     | dependência do motor`sdk`                      | `pip install -r src/shared/tools/requirements-pipeline.txt` — ou use `--engine copilot` |
| `❌ Falha na conexão` no `[Auth]`          | VPN desconectada ou chave inválida               | Conecte a VPN; teste`doctor`; o endpoint é *private endpoint*                           |
| `⚠️ Headroom proxy não respondeu`          | proxy fora do ar                                  | Suba com`run_standalone.ps1`, ou aceite a rota direta                                      |
| `--via-proxy` sai com 2                       | proxy exigido e fora do ar                        | Suba o proxy ou remova a flag                                                                |
| `⚠️ Nenhum bloco FILE: encontrado`          | o modelo não seguiu o formato de saída          | Confira o log em`outputs/pipeline_runner/`; o system prompt exige `<!-- FILE: … -->`    |
| `⚠️ caminho recusado (fora do projeto)`     | o modelo propôs caminho fora de`projects/{p}/` | Comportamento correto — o artefato foi descartado de propósito                             |
| `⚠️ sem F2.yaml` no motor copilot           | só existe DAG da F1                              | Use`--engine sdk` nessa etapa                                                              |
| `⚠️ trigger 'DP' NÃO é propagado`         | limitação do motor copilot                      | Use`--engine sdk` para honrar o trigger                                                    |
| `ERRO: plano incoerente com o agent_registry` | agente renomeado, deprecado ou virou stub         | Rode`list --agents` e corrija `pipeline.steps` no YAML                                   |
| Modelo diferente do esperado                    | env var sobrescrevendo                            | `config -p PROJ` mostra o valor efetivo; confira `AVA_FOUNDRY_MODEL`                     |

---

## 16. Migração do `pipeline_runner.py`

O arquivo da raiz continua funcionando como shim — avisa da depreciação, oferece
o seletor de projeto e delega ao CLI.

| Antes                                 | Agora                                                                              |
| ------------------------------------- | ---------------------------------------------------------------------------------- |
| `python pipeline_runner.py` + menus | `ava-pipeline run -p PROJ`                                                       |
| menu "Full Pipeline"                  | `--all`                                                                          |
| menu "Por Fase"                       | `--phase F2` (grupo) ou `--phase F2b` (etapa)                                  |
| menu "Automático"                    | `--yes`                                                                          |
| —                                    | `--dry-run`, `--model`, `--agent`, `--engine`, `--from`, `--via-proxy` |

### O que mudou de comportamento

- **`WORKSPACE` não é mais hardcoded.** Apontava para outro checkout
  (`c:\_info\Projetos\Hub\SRC_Torre_Apps_31_07`), então o script não rodava neste
  repo. Agora o caminho vem de `__file__`.
- **A spec do agente vem do `agent_registry`.** O runner antigo procurava por
  substring em `rglob("*.md")` e escolhia o maior arquivo candidato — podia
  carregar o agente errado sem avisar.
- **A F6 usa `QE`, não `TPT`.** A tabela antiga repetia o trigger de planejamento
  na etapa de execução do QA; ver [seção 4](#dois-orquestradores-rodam-duas-vezes).
- **Modelo, endpoint e ordem da esteira saíram do código** para o YAML.

---

## Referências

| Assunto                           | Onde                                                                           |
| --------------------------------- | ------------------------------------------------------------------------------ |
| Configuração e ordem da esteira | `src/shared/data/ava-pipeline.yaml`                                          |
| Catálogo canônico de agentes    | `src/shared/tools/agent_registry.py`                                         |
| Proxy Headroom                    | `src/shared/tools/headroom/README.md`                                        |
| Execução por processo isolado   | `src/shared/tools/agent_runner.py`                                           |
| Sessão interativa do Copilot CLI | `copilot-cli-headroom.bat`                                                   |
| Catálogo de agentes (prosa)      | `docs/agents-catalog.md`                                                     |
| Testes do contrato                | `tests/tools/test_pipeline_plan.py`, `tests/tools/test_pipeline_config.py` |

Analise o escript a seguir

C:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\pipeline_runner.py

- Como funciona o  script
- Quais configurações/depencias  são necessarias para rodar o script
- Compara com  o script que adiciona o headroom como proxy antes da requisição checar no foundry, como adapto esse script para ter o mesmo resultado, utilizando o headroom como proxy
- Quais configurações são necessarias para  parametrizar o script

  - passando o nome do projeto,
  - numero da fase opcional que desejo executar,
  - sinalizar todas as fases,
  - modelo de llm
  - agente especifico caso queira somente rodar uma agente pelo script
- O script deve fazer o orquestração total do pipeline da fabruca de agentes
- Transformar  o script em CLI mais robusto para execução da workflow completo
- As configurações de modelo, urls, endpoint devem ficar um arquivo separado para ser carregado pelo CLI,  assim centralizar  mudança em uma unica fonte de alteração
  Show less
  I'll start by exploring the relevant files to understand the current implementation.

Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\pipeline_runner.py
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\copilot-cli-headroom.bat
Now let me explore the supporting infrastructure in parallel.

Agent:Explore headroom proxy tool
IN
Explore the Headroom proxy tooling in the repo at c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents.

Focus on `src/shared/tools/headroom/` — I need to understand, thoroughly:

1. `headroom_config.py` — what CLI flags it exposes (e.g. `--proxy-url`), how config is resolved (env vars, headroom.yaml, project-config.yaml precedence), what keys exist in headroom.yaml, where the yaml file lives, and what the effective host/port resolution logic is. Show the actual function/CLI-arg names.
2. `headroom_tool.py` — the subcommands (`proxy start`, `proxy status`, etc.), how `proxy status` signals up/down (exit code), how the proxy is started programmatically if possible.
3. The proxy itself — what HTTP paths it accepts (does it proxy `/v1/messages`? does it expect the base_url to include a path suffix?), how it forwards upstream (the `ANTHROPIC_TARGET_API_URL` env var — where is it read?), whether it supports streaming (SSE) passthrough, whether it needs the `anthropic-version` header, and how auth/bearer token is forwarded.
4. Any JSONL metrics/telemetry output (tokens_before/tokens_after/latency_ms) — where it's written and configured.
5. `setup.ps1` and `run_standalone.ps1` — what they do and what the venv path is.
6. Whether there is any existing Python client code in the repo that calls the proxy via the `anthropic` SDK (search for `base_url`, `anthropic.Anthropic(`, `ANTHROPIC_TARGET_API_URL`).

Report file paths with line numbers and concrete code excerpts for the key parts. Be very thorough.
Agent:Explore agent registry and phases
IN
Explore the agent/phase registry infrastructure in c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents.

I need to understand:

1. `src/shared/tools/agent_registry.py` — its full CLI interface (flags like `--orchestrator`, and any others), the data source it reads from (a YAML? module.yaml files?), how phases (F1..F8) map to orchestrators and to specialized agents, and what functions it exposes for programmatic import (not just CLI).
2. The canonical source of truth for the phase → agent mapping. Where does it live? Is there a registry YAML/JSON? Show its structure. Are the triggers (like "FP", "SD", "DP", "TPT", "SG", "DE", "SAS", "SV") registered anywhere canonical, or only hardcoded in scripts?
3. `src/modules/ava-fabric-agents/` — the module layout: how modules are organized (module.yaml files?), where agent .md skill files live, naming conventions. List the module directories and a sample module.yaml content.
4. `src/shared/tools/generate_agent_wrappers.py` — what it does, the `--check` flag semantics.
5. The projects folder structure: `projects/<name>/context/project-config.yaml` and `outputs/`. Show a sample project-config.yaml (e.g. from projects/Meu-ERP or projects/MeuERP-002) — what keys it holds (model? phases? stack?).
6. Any existing Python CLI in the repo that uses argparse and could serve as a style/pattern reference for building a robust CLI (list a few, with paths). Also note if the repo uses `click`/`typer` anywhere, and check for a requirements.txt / pyproject.toml listing dependencies.

Report with file paths + line numbers and concrete excerpts. Be very thorough.
Bash List repo root and projects
IN
ls /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/ && echo "--- projects ---" && ls /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/projects/

OUT
AGENTS.md
automated_test
CHANGELOG.md
check_pbi1520.py
copilot-cli-headroom.bat
copilot-cli-v1.bat
debug_schema.py
docs
fastqa
fix_p1.py
fix_p2.py
module.yaml
pipeline_runner.py
projects
r0_preflight.ps1
r4_bnk_fc.ps1
README.md
specs
src
tests
validate_events_pubsub.py
verify_waves.py
--- projects ---
_template
Meu-ERP
MeuERP-002
Bash List shared tools
IN
ls src/shared/tools/ && echo "--- headroom ---" && ls src/shared/tools/headroom/ 2>/dev/null

OUT
__init__.py
__pycache__
_populate_pipeline_agents.py
agent_observability.py
agent_registry.py
agent_runner.py
check_session_health.py
gen_er_diagram.py
gen_screen_flow.py
generate_agent_wrappers.py
generate_observability_report.py
headroom
pipeline_observer.py
README.md
--- headroom ---
__pycache__
Containerfile
docs
headroom.yaml
headroom_config.py
headroom_context.py
headroom_tool.py
mcp_server.py
podman-compose.yml
README.md
requirements.txt
run_standalone.ps1
run_standalone.sh
setup.ps1
setup.sh
vendor
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\agent_runner.py
Bash List pipeline DAG files
IN
ls src/shared/data/pipeline-dag/ 2>/dev/null; echo "--- data ---"; ls src/shared/data/ | head -40

OUT
F1.yaml
--- data ---
architecture-backlog.yaml
compliance
patterns
pipeline-dag
policies
reference-architecture.yaml
scaffold-manifests
stub-registry.yaml
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\data\pipeline-dag\F1.yaml
Bash List specs directories
IN
ls specs/ && echo "--- 033 ---" && ls specs/033*/ 2>/dev/null

OUT
001-reliability-pipeline-evolution
002-agent-pipeline-observability
002-qa-local-pipeline
003-agent-self-observability
004-observability-self-report-activation-fix
005-observability-mandatory-phase
006-model-aware-observability
007-api-language-guardrail
007-date-format-guardrails
007-dotnet-clean-arch-solid-guardrail
007-dotnet-compile-guardrails
007-dotnet-global-exception-handler
007-multitenant-db-isolation
007-solution-delphi-ast-consumption
007-summary-artifact-integrity
007-unicode-safe-regex-guardrail
008-angular-test-scaffolder
008-coder-react-frontend
008-design-tokens-propagation
008-lgpd-pii-guardrail
008-partial-modernization-support
008-pipeline-phase-order-correction
008-react-frontend-build-cycle
009-solution-delphi-test-coverage-artifact
009-vue-frontend-agent
010-asis-agents-ast-artifact-consumption
011-asis-orchestrator-solution-first-dispatch
012-solution-delphi-ast-analyzer-config-path
013-master-orchestrator-mandatory-spec-read
014-remover-geracao-drawio-tobe
015-summary-remediation-agent
016-sql-ir-mer-generation
016-tobe-artifact-only-guardrail
017-tobe-path-corrections
018-solution-delphi-ast-step0-verification-gate
019-codegen-dynamic-naming-path-fix
020-codegen-business-rules-architecture-config
021-frontend-backend-api-contract-integration
022-asis-orchestrator-summary-template-fix
022-db-analyzer-script-enforcement
022-remove-asis-class-diagram-refs
022-tobe-master-report-optional
023-bridge-fastqa-ast-simplification
023-prototype-optional-artifacts
024-remove-test-qa-baseline-golden-agents
025-summary-asis-test-cases-menu
026-unified-business-rules-artifact
027-tobe-readiness-gate-wave1
028-business-rules-full-coverage-catalog
028-test-cases-overview-extractor
028-tobe-orchestrator-v280
029-consolidate-test-plan-artifacts
029-podman-local-runner
029-screen-flow-batch-protocol
029-unify-test-plan-tobe
030-asis-pipeline-context-budget-dispatch-guard
031-headroom-context-compression-proxy
032-headroom-pipeline-wide-attribution
033-agent-isolation-context-engineering
034-prototype-to-component-conversion
--- 033 ---
checklists
contracts
plan.md
quickstart.md
research.md
spec.md
tasks.md
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\specs\033-agent-isolation-context-engineering\quickstart.md
Bash Check context_pack and asis utils
IN
ls src/shared/tools/context_pack.py 2>/dev/null && echo EXISTS || echo "context_pack.py MISSING"; ls src/modules/ava-fabric-agents/asis-diagnostic/utils/ 2>/dev/null

OUT
context_pack.py MISSING
__pycache__
artifact_gate.py
business_rules_catalog_generator.py
context_budget.py
generate_fallback_artifacts.py
generate_test_cases_overview.py
module_partitioner.py
run_ast_analysis.py
run_delphi_ast_analysis.py
sql_ir_generator.py
Bash Check python dependencies files
IN
cat src/shared/tools/headroom/requirements.txt 2>/dev/null; echo "--- root reqs ---"; ls requirements*.txt pyproject.toml setup.py 2>/dev/null

OUT
Exit code 2

# AVA Fabric — Headroom Tool (venv isolado: src/shared/tools/headroom/.venv)

# Instalado por setup.ps1 / setup.sh. NÃO instalar no venv principal do repo —

# o repo é stdlib-only por convenção (invariante IV7).

# O fork embedded vive em ./vendor (git subtree, headroom-ai 0.33.0). O build

# backend do vendor é maturin, que exige toolchain Rust. Quando `cargo` existe,

# setup.* instala o fork em modo editável; senão cai para o wheel PyPI da MESMA

# versão. Ver README.md § Instalação.

headroom-ai[proxy,mcp,ml,code,memory,otel]==0.33.0

# Leitura de project-config.yaml (mesma dependência já usada por

# context_budget.py / module_partitioner.py no venv principal)

pyyaml>=6.0

# Testes da tool

pytest>=8.0
--- root reqs ---
Bash Find stdlib-only convention references
IN
grep -rn "stdlib-only\|IV7" --include=*.md --include=*.py src/ docs/ specs/ 2>/dev/null | head -20

OUT
src/shared/tools/headroom/README.md:66:stdlib-only e nunca ganha `headroom-ai`.
docs/plan/headroom-context-compression-tool.md:20:Fork embedded via git subtree (opção escolhida sobre dependência pip). Consequências aceitas: código de terceiros versionado dentro do repo, segundo venv isolado, e git subtree pull entrando no ciclo de manutenção. O repo hoje não tem requirements.txt/pyproject.toml na raiz e é stdlib-only — esta entrega abre essa exceção, contida dentro de src/shared/tools/headroom/.
docs/plan/headroom-context-compression-tool.md:198:Fork embedded via git subtree (opção escolhida sobre dependência pip). Consequências aceitas: código de terceiros versionado dentro do repo, segundo venv isolado, e git subtree pull entrando no ciclo de manutenção. O repo hoje não tem requirements.txt/pyproject.toml na raiz e é stdlib-only — esta entrega abre essa exceção, contida dentro de src/shared/tools/headroom/.
specs/012-solution-delphi-ast-analyzer-config-path/spec.md:185:- `threading.Timer`-based timeout enforcement is an acceptable stdlib-only substitute
specs/031-headroom-context-compression-proxy/plan.md:61:e é stdlib-only. Esta entrega abre a exceção **contida** em
specs/031-headroom-context-compression-proxy/plan.md:163:| Segundo venv | `headroom-ai` puxa fastapi/uvicorn/onnxruntime/(torch); contaminaria o venv stdlib-only do repo (I7) | Instalar no venv principal |
specs/031-headroom-context-compression-proxy/research.md:189:| Repo é stdlib-only | Sem `requirements.txt`/`pyproject.toml` na raiz; `yaml` importado com `try/except` | Venv isolado; consumidores importam a tool defensivamente |
specs/031-headroom-context-compression-proxy/spec.md:93:do repo continua stdlib-only.
Bash Find header preparation helpers
IN
grep -n "def prepare_.*header\|def build_.*header\|def _forward_headers\|def filter_headers\|HOP_BY_HOP\|def prepare_upstream" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/proxy/helpers.py" | head -30; echo "=== usage in anthropic.py ==="; grep -n "prepare_headers\|upstream_headers\s*=\|headers=.*upstream" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/proxy/handlers/anthropic.py" | head -30

OUT
=== usage in anthropic.py ===
Bash Inspect checks/cli.py argparse structure
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && grep -n "add_argument\|ArgumentParser\|add_subparsers\|def main" src/shared/checks/cli.py | head -60

OUT
14:def main() -> None:
15:    parser = argparse.ArgumentParser(
19:    parser.add_argument(
24:    parser.add_argument(
30:    parser.add_argument(
Bash Grep headers usage in anthropic handler
IN
grep -n "headers" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/proxy/handlers/anthropic.py" | sed -n '1,60p'

OUT
32:from headroom.proxy.forwarded_headers import resolve_client_ip
116:                headers=dict(request.headers),
118:                base_user_id=request.headers.get("x-headroom-user-id", ""),
551:        auth_mode = classify_auth_mode(request.headers)
662:            content_length = request.headers.get("content-length")
761:                request.headers.get("x-headroom-bypass", "").lower() == "true"
762:                or request.headers.get("x-headroom-mode", "").lower() == "passthrough"
780:            # Extract headers and tags
781:            headers = dict(request.headers.items())
782:            headers.pop("host", None)
783:            headers.pop("content-length", None)
789:            headers.pop("content-encoding", None)
790:            headers.pop("transfer-encoding", None)
795:            headers.pop("accept-encoding", None)
796:            tags = extract_tags(headers)
800:            client = classify_client(headers, default="claude")
802:            # headers AFTER `_extract_tags` reads them. Inbound bypass gating
803:            # uses `request.headers.get(...)` directly above; memory user-id
804:            # is read from `request.headers` below if needed. From this
805:            # point on, `headers` is the upstream-bound copy.
807:                _strip_internal_headers,
808:                log_outbound_headers,
809:                merge_extra_headers,
812:            _pre_strip_count = sum(1 for k in headers if k.lower().startswith("x-headroom-"))
813:            headers = _strip_internal_headers(headers)
814:            headers = merge_extra_headers(headers, self.config.anthropic_extra_headers)
815:            log_outbound_headers(
818:                - sum(1 for k in headers if k.lower().startswith("x-headroom-")),
823:            _auth_header = headers.get("authorization", "")
837:                api_key = headers.get("x-api-key", "")
839:                    auth = headers.get("authorization", "")
846:                # rate-limit buckets by forging headers.
859:                        headers={"Retry-After": str(int(wait_seconds) + 1)},
875:            # Reads `request.headers` directly because the local `headers` dict was
880:                memory_user_id = request.headers.get(
887:                # cwd headers → CLI override → system prompt env block.
896:                    headers=dict(request.headers),
904:            # Canonical memory-injection gate. Reads `request.headers`
906:            # `headers` dict was stripped of x-headroom-* above).
914:                headers=request.headers,
995:                    # Remove compression headers from cached response
996:                    response_headers = dict(cached.response_headers)
997:                    response_headers.pop("content-encoding", None)
998:                    response_headers.pop("content-length", None)
1005:                        headers=response_headers,
1024:                            "user_id": headers.get("x-api-key", "")[:16],
1074:            # session id (and its sticky CCR/memory tools, beta headers, and
1172:            _client_beta_value = headers.get("anthropic-beta")
1189:                headers["anthropic-beta"] = _sticky_beta_value
1190:            elif not _sticky_beta_value and "anthropic-beta" in headers:
1216:                headers=request.headers, config=self.config, messages=messages
1250:                headers=request.headers,
1821:                            anthropic_beta=request.headers.get("anthropic-beta"),
2185:                    # Add beta headers for native memory tool. PR-A6
2193:                    beta_headers = self.memory_handler.get_beta_headers()
2194:                    if beta_headers:
2202:                        for key, value in beta_headers.items():
2208:                                headers[key] = value
2210:                            existing_value = headers.get(key, "")
2222:                            headers[key] = merged
Bash Inspect project template structure
IN
find projects/_template -type f | head -30; echo "--- MeuERP-002 ---"; find projects/MeuERP-002 -maxdepth 3 -type f | head -30

OUT
projects/_template/.gitkeep
projects/_template/context/.project-config-exemple-.yaml
projects/_template/context/project-config.yaml
projects/_template/context/shared-context.md
--- MeuERP-002 ---
projects/MeuERP-002/context/project-config.yaml
projects/MeuERP-002/context/shared-context.md
projects/MeuERP-002/outputs/asis/api-map.md
projects/MeuERP-002/outputs/asis/architecture-blueprint.md
projects/MeuERP-002/outputs/asis/bounded-context-map.md
projects/MeuERP-002/outputs/asis/code-usage-analysis.md
projects/MeuERP-002/outputs/asis/complexity-map.md
projects/MeuERP-002/outputs/asis/data-access-profile.md
projects/MeuERP-002/outputs/asis/events-pubsub-grid.json
projects/MeuERP-002/outputs/asis/events-pubsub-inventory.md
projects/MeuERP-002/outputs/asis/events-pubsub-risks.md
projects/MeuERP-002/outputs/asis/external-dependencies.md
projects/MeuERP-002/outputs/asis/file-export-dependencies.md
projects/MeuERP-002/outputs/asis/file-import-dependencies.md
projects/MeuERP-002/outputs/asis/gap-analysis-summary.md
projects/MeuERP-002/outputs/asis/gap-list-report.md
projects/MeuERP-002/outputs/asis/gap-register.json
projects/MeuERP-002/outputs/asis/gaps-risks-report.md
projects/MeuERP-002/outputs/asis/inventory-report.md
projects/MeuERP-002/outputs/asis/master-report.md
projects/MeuERP-002/outputs/asis/metrics.json
projects/MeuERP-002/outputs/asis/migration-risks-summary.md
projects/MeuERP-002/outputs/asis/pattern-classifications.json
projects/MeuERP-002/outputs/asis/risk-register.json
projects/MeuERP-002/outputs/asis/vcl-lifecycle-map.md
projects/MeuERP-002/outputs/observability/agent-events.jsonl
projects/MeuERP-002/outputs/observability/headroom-metrics.jsonl
projects/MeuERP-002/outputs/observability/pipeline-run-state.json
projects/MeuERP-002/outputs/summary/AVA-FABRIC-SUMMARY-MeuERP-002-2026-08-03.html
projects/MeuERP-002/outputs/summary/index.md
Bash Inspect argparse in agent_runner and pipeline_observer
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && grep -n "ArgumentParser\|add_subparsers\|add_argument\|add_parser" src/shared/tools/agent_runner.py | head -60; echo "=== pipeline_observer ==="; grep -n "ArgumentParser\|add_subparsers\|add_argument\|add_parser" src/shared/tools/pipeline_observer.py | head -60

OUT
676:    ap = argparse.ArgumentParser(description="Executa os agentes de uma fase como processos isolados.")
677:    ap.add_argument("--project", required=True)
678:    ap.add_argument("--phase", required=True, help="F1..F8")
679:    ap.add_argument("--wave", default=None, help="Executa só esta wave")
680:    ap.add_argument("--agent", default=None, help="Executa só este agente")
681:    ap.add_argument("--dry-run", action="store_true", help="Imprime os comandos, sem inferência")
682:    ap.add_argument("--via-proxy", action="store_true",
685:    ap.add_argument("--json", action="store_true", help="Emite o resultado em JSON")
=== pipeline_observer ===
1105:    parser = argparse.ArgumentParser(
1133:    parser.add_argument("--project", "-p", default=None, help="Project name")
1135:    subs = parser.add_subparsers(dest="command", required=True)
1138:    p_init = subs.add_parser("init", help="Initialize a new pipeline run")
1139:    p_init.add_argument("--run-type", default="full-pipeline")
1140:    p_init.add_argument("--model", default=DEFAULT_MODEL)
1143:    p_track = subs.add_parser("track", help="Track agent execution (atomic start+end)")
1144:    p_track.add_argument("--agent", required=True, help="Agent name")
1145:    p_track.add_argument("--phase", default="", help="Pipeline phase (F1..F8)")
1146:    p_track.add_argument("--version", default="", help="Agent version")
1147:    p_track.add_argument("--status", default="completed", choices=["completed", "failed", "skipped", "running"])
1148:    p_track.add_argument("--tokens-in", type=int, default=0)
1149:    p_track.add_argument("--tokens-out", type=int, default=0)
1150:    p_track.add_argument("--duration-ms", type=int, default=0)
1151:    p_track.add_argument("--start-time", default=None, help="ISO 8601 start time")
1152:    p_track.add_argument("--end-time", default=None, help="ISO 8601 end time")
1153:    p_track.add_argument("--model", default=None)
1154:    p_track.add_argument("--error-detail", default="", help="Error message if failed")
1157:    p_fin = subs.add_parser("finalize", help="Finalize pipeline run")
1158:    p_fin.add_argument("--auto-report", action="store_true", help="Auto-generate all reports")
1161:    subs.add_parser("dashboard", help="Show formatted dashboard")
1164:    subs.add_parser("status", help="Show raw JSON status")
1167:    p_report = subs.add_parser("report", help="Generate reports")
1168:    p_report.add_argument("--format", default="all", choices=["all", "xlsx", "json", "md"])
1169:    p_report.add_argument("--output-dir", default=None, help="Custom output directory")
1172:    p_import = subs.add_parser("import-json", help="Import metrics from external JSON")
1173:    p_import.add_argument("--input", required=True, help="Path to JSON file")
1176:    p_compare = subs.add_parser("compare", help="Compare two pipeline runs")
1177:    p_compare.add_argument("--run-a", required=True, help="Path to run A state JSON")
1178:    p_compare.add_argument("--run-b", required=True, help="Path to run B state JSON")
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\headroom\docs\01-standalone.md
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\projects\MeuERP-002\context\project-config.yaml
Bash Inspect docs/agents-catalog.md
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && grep -n "FP\b\|TPT\|SAS" docs/agents-catalog.md | head -30; echo "=== head of agents-catalog ==="; head -60 docs/agents-catalog.md

OUT
1087:- Configura SonarQube, SAST e gate de cobertura
1316:| `SAS`   | Summary AS-IS Only — gera com dados da F1 apenas      |
=== head of agents-catalog ===

# AVA Fabric Agents — Catálogo de Agentes

**Versão:** 1.5**Data:** 2026-07-07**Total de agentes:** 53

> Catálogo completo de todos os agentes do AVA Fabric, organizados por fase da esteira de migração.
> Cada agente é um arquivo `.md` em `src/modules/ava-fabric-agents/` que pode ser invocado diretamente pelo Claude Code.

---

## Índice

- [Visão Geral da Esteira](#visão-geral-da-esteira)
- [F1 — AS-IS Diagnostic](#f1--as-is-diagnostic)
- [F2 — TO-BE Architecture](#f2--to-be-architecture)
- [F3 — Prototype](#f3--prototype)
- [F4 — Tech Stack](#f4--tech-stack)
- [F5 — QA Agents](#f5--qa-agents)
- [F6 — DevOps](#f6--devops)
- [F7 — Deliverables](#f7--deliverables)
- [F8 — Summary (cross-cutting, executado após cada fase)](#f8--summary)
- [Convenções e Contratos](#convenções-e-contratos)

---

## Visão Geral da Esteira

```
projects/{PROJECT_NAME}/inputs/
  └─ código-fonte legado (Delphi, COBOL, VB6...)

F1 ─── AS-IS Diagnostic        ─── 8 agentes  →  projects/{PROJECT_NAME}/outputs/asis/
F2 ─── TO-BE Architecture       ─── 12 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/
F3 ─── Prototype                ─── 1 agente   →  projects/{PROJECT_NAME}/outputs/tobe/prototype/
F4 ─── Tech Stack               ─── 3 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/source-code/
F5 ─── QA Agents                ─── 10 agentes  →  projects/{PROJECT_NAME}/outputs/qa/
F6 ─── DevOps                   ─── 5 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/iac/
F7 ─── Deliverables             ─── 7 agentes  →  projects/{PROJECT_NAME}/outputs/deliverables/
F8 ─── Summary (cross-cutting)  ─── 2 agentes  →  projects/{PROJECT_NAME}/outputs/summary/
```

---

## F1 — AS-IS Diagnostic

Fase de diagnóstico completo do sistema legado. O orchestrator coordena os sub-agentes em duas waves — Wave 1 (agente de solução + segurança, imediato) → Solution Agent Gate → Wave 2 (6 agentes, dependentes dos artefatos do agente de solução) — e consolida os resultados no Master Report.

### `ava-asis-orchestrator`

| Campo             | Valor                                                                         |
| ----------------- | ----------------------------------------------------------------------------- |
| **Arquivo** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` |
| **Papel**   | Coordenador da esteira de diagnóstico AS-IS                                  |
| **Trigger** | Ponto de entrada da fase F1                                                   |

**Responsabilidades:**

- Valida o repositório legado de entrada
- Detecta tecnologia (Delphi, COBOL, VB6)
  Aguardando os agentes de exploração. Enquanto isso, vou verificar as dependências instaladas.

Bash Check python and package availability
IN
python --version 2>&1; python -c "import anthropic; print('anthropic', anthropic.__version__)" 2>&1 | tail -2; python -c "import yaml; print('pyyaml ok')" 2>&1 | tail -1; python -c "import requests; print('requests ok')" 2>&1 | tail -1

OUT
Python 3.13.3
anthropic 0.116.0
pyyaml ok
requests ok
Bash Check settings.json and .env.example headroom vars
IN
grep -n "ANTHROPIC_TARGET_API_URL\|HEADROOM_\|COPILOT_PROVIDER" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.vscode/settings.json" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example" | head -50

OUT
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.vscode/settings.json:33:        "HEADROOM_HOST": "127.0.0.1",
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.vscode/settings.json:34:        "HEADROOM_PORT": "8787",
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.vscode/settings.json:35:        "HEADROOM_BACKEND": "anthropic",
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.vscode/settings.json:36:        "HEADROOM_TELEMETRY": "off",
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.vscode/settings.json:37:        "ANTHROPIC_TARGET_API_URL": "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic",
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:18:# real vem de ANTHROPIC_TARGET_API_URL (equivalente a --anthropic-api-url).
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:19:ANTHROPIC_TARGET_API_URL=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:32:HEADROOM_ENABLED=true
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:35:HEADROOM_HOST=127.0.0.1
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:36:HEADROOM_PORT=8787
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:37:HEADROOM_BACKEND=anthropic
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:39:HEADROOM_MODE=token
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:40:HEADROOM_TELEMETRY=off
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:41:HEADROOM_LOG_FILE=.headroom/proxy-requests.jsonl
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:42:HEADROOM_REQUEST_TIMEOUT=600
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:45:HEADROOM_OUTPUT_SHAPER=1
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:47:HEADROOM_OUTPUT_HOLDOUT=0.0
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:52:# HEADROOM_DETECT_BACKEND=rust
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:56:# HEADROOM_TARGET_RATIO=
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/.env.example:60:HEADROOM_METRICS_FILE=outputs/observability/headroom-metrics.jsonl
Bash Find trigger shortcodes in agent specs
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && grep -rn '`FP`\|`SD`\|`DP`\|`TPT`\|`SG`\|`DE`\|`SAS`\|`SV`\|"FP"\|"SD"\|"TPT"' src/modules/ava-fabric-agents --include=*.md | head -40

OUT
src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md:56:A ÚLTIMA coisa emitida em qualquer trigger (`SA`, `FP`, `MR`, `SR`) SERÍ o bloco `## ⏱ Execução Concluída`:
src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md:1428:| `FP`        | full-pipeline        | **Full Pipeline**: SA DAG + validação de artefatos + fallbacks + Summary HTML                                                                       |
src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md:2169:   Registrar `resolved_solution_agent` no contexto de execução para uso em Phase A dispatch e evaluate_phase_a_all(); inicializar todos os agentes no Agent Completion Registry com `status: pending`; **deletar `projects/{project_name}/outputs/asis/risk-register.json`** se existir (reset obrigatório — redundante quando flag `FULL` usada, mas sempre executar para `SA` e `FP`); **registrar `backup_files_removed: {N}` no `shared-context.md`** (valor do Step 0.5, ou 0 se não-Delphi); **→ Emitir `TodoWrite` com 9 items (ver Â§ Progress Tracker — incluindo item 5b `bridge-fastqa`)**: marcar `reset` como `completed` (se não-FULL ou se reset já executou), marcar `validate` como `completed`, marcar `decompose` como `in-progress`; ao final deste step → marcar `decompose` como `completed`
src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md:2562:| `FP`  | Ao final do pipeline (após Summary ou fallback) | Todos os valores reais disponíveis                              |
src/modules/ava-fabric-agents/devops-agents/agents/containerize-agent.md:24:> after `ava-devops-ci`, `FP` trigger). Can also be invoked standalone. **Not** invoked by
src/modules/ava-fabric-agents/devops-agents/agents/containerize-agent.md:25:> `ava-stack-orchestrator` — F4's own `SG` trigger, run standalone (without the full `master-orchestrator FP`
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:34:>   - `DP` — DevOps Plan (Momento 1, após F2)
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:35:>   - `DE` — DevOps Execute (Momento 2, após F4)
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:45:A ÚLTIMA coisa emitida em qualquer trigger (`DP`, `DE`) SERÁ o bloco `## ⏱ Execução Concluída`:
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:49:  - **(2)** tabela MACRO — 1 linha por momento: `DP` (Planejamento) / `DE` (Execução) — colunas: Momento, Orquestrador, Início, Fim, Duração, Status
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:59:| `DP` | devops-plan | **Momento 1 — Planejamento** (após F2 TO-BE). Decide estratégia e gera planos. Não executa deploy nem gera código de aplicação. |
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:60:| `DE` | devops-execute | **Momento 2 — Execução** (após F4 Stack). Despacha os 13 agentes DevOps seguindo o plano do Momento 1. |
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:154:### Momento 1 — Trigger `DP` (DevOps Plan)
src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md:220:### Momento 2 — Trigger `DE` (DevOps Execute)
src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md:169:| F2 | TO-BE Orchestrator | `ava-tobe-orchestrator` | trigger: `SD` — bloqueante | `tobe-architecture/agents/orchestrator-tobe.md` |
src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md:171:| F2.5 | DevOps Orchestrator (Momento 1) | `ava-devops-orchestrator` | trigger: `DP` — não-bloqueante | `devops-agents/agents/orchestrator-devops.md` |
src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md:175:| F4 | Stack Orchestrator | `ava-stack-orchestrator` | trigger: `SG` — bloqueante | `tech-stack/agents/orchestrator-stack.md` |
src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md:179:| F6 | DevOps Orchestrator (Momento 2) | `ava-devops-orchestrator` | trigger: `DE` — bloqueante (delegado) | `devops-agents/agents/orchestrator-devops.md` |
src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md:224:| `FP` | full-pipeline | **Full Pipeline**: executa todas as fases F1→F2→F3→F4→F5→F6→F7 em sequência |
src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md:711:> O orquestrador `ava-devops-orchestrator` já deve ter sido acionado com trigger `DP` em Step 2.5
src/modules/ava-fabric-agents/qa-agents/agents/gaps-requirements-agent.md:126:> 1. Execute o `ava-tobe-orchestrator` trigger `SD` para completar F2
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:39:| ava-test-plan-tobe | Test Plan TO-BE | Acionado via trigger `TPT` — transferido do `ava-tobe-orchestrator` (Fase 6) |
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:52:| `TPT` | **Test Plan TO-BE** — geração de plano de testes consolidado e artefatos previstos pelo `ava-test-plan-tobe` ⛔ Pre-condition Gate — ver §Pre-condition Gate (TPT) |
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:129:> 1. Execute o trigger `SD` no `ava-tobe-orchestrator` para completar a fase F2
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:139:> **INVARIANTE**: Execute este gate ANTES de qualquer ação do trigger `TPT`. Não prossiga sem PASS.
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:173:> 1. Execute `@ava-tobe-orchestrator` (trigger `SD`) para completar a fase F2 e gerar `bounded-context-map.md`
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:175:> 3. Re-execute o trigger `TPT` após a conclusão dos pré-requisitos
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:518:| `TPT`   | Test Plan TO-BE    | ❌ | ❌ |
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:526:> **Note**: O trigger `TPT` NÃO executa os passos terminais PT/RS. Ele transfere o fluxo de execução para o `ava-test-plan-tobe` e **interrompe** o fluxo do `ava-qa-orchestrator` imediatamente após o dispatch, conforme §Routing — Trigger TPT.
src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md:584:Quando trigger = `TPT`:
src/modules/ava-fabric-agents/summary/agents/summary-agent.md:24:A ÚLTIMA coisa emitida em qualquer trigger (`GS`, `SAS`, `STO`, `SI`, `UP`) SERÁ o bloco `## ⏱ Execução Concluída`:
src/modules/ava-fabric-agents/summary/agents/summary-agent.md:145:Executado com `SAS` — gera summary parcial com as seções F1 preenchidas
src/modules/ava-fabric-agents/summary/agents/summary-agent.md:321:| `SAS`  | summary-asis-only | Summary parcial — apenas fase AS-IS                    |
src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md:27:A ÚLTIMA coisa emitida em qualquer trigger (`SG`, `BG`, `FG`) SERÝ o bloco `## ❱ Execução Concluída`:
src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md:781:| `SG`  | Start full stack generation |
src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md:823:> NUNCA encerrar o pipeline `SG` com apenas o backend concluído.
src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md:39:A ÚLTIMA coisa emitida em qualquer trigger (`SD`, `FR`) SERÁ o bloco `## ❱ Execução Concluída`:
src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md:1625:| `SD`  | Start TO-BE design (inclui Value Chain por padrão)                                                  |
src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md:1631:> ⚠️ **[SD] Verificação Opcional — AS-IS Master Report**: Antes de executar o trigger `SD`, verificar se `projects/{project_name}/outputs/asis/master-report.md` existe. Se não existir → emitir **aviso não-bloqueante**:
src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md:1636:> **Nota:** O Value Chain (`value-chain.mmd`, `value-chain.drawio`, `value-chain-mapping.md`) é gerado automaticamente como parte do fluxo `SD` pelo Architecture Design TO-BE Agent. O trigger `VC` existe apenas para **re-gerar** isoladamente se necessário.
Bash Check project-config headroom blocks
IN
grep -n -A 25 "^headroom:" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/projects/_template/context/project-config.yaml"; echo "=== Meu-ERP ==="; grep -rn -A 25 "^headroom:" "C:/Desenv/factory_apps/ava-fabric-apps-agents/projects/Meu-ERP/context/project-config.yaml" 2>/dev/null | head -40

OUT
=== Meu-ERP ===
Bash Check headroom venv and yaml head
IN
ls src/shared/tools/headroom/.venv/Scripts/python.exe 2>/dev/null && echo "VENV OK" || echo "VENV AUSENTE"; cat src/shared/tools/headroom/headroom.yaml 2>/dev/null | head -60

OUT
src/shared/tools/headroom/.venv/Scripts/python.exe
VENV OK

# AVA Fabric — Headroom Tool · defaults

# =====================================================================

# Camada MAIS FRACA da configuração. Precedência efetiva (forte → fraco):

# 1. variáveis de ambiente (HEADROOM_* / AVA_FOUNDRY_* / ANTHROPIC_TARGET_API_URL)

# 2. projects//context/project-config.yaml → bloco `headroom:`

# 3. este arquivo

# Artigo I da Constituição: nada de limiar/endpoint hardcoded em código.

# Quem resolve a precedência é headroom_config.py::load_config().

# ---------------------------------------------------------------------

headroom:

# ── Feature flags ─────────────────────────────────────────────────

  enabled: true

# Modelo e limite de contexto do endpoint Foundry.

# ATENÇÃO: o endpoint da esteira é Anthropic-compatible (…/anthropic),

# não Azure OpenAI. Ver copilot-cli-v1.bat na raiz do repo.

  model: "claude-sonnet-4-6"
  context_limit: 200000

# rust = detector nativo (Magika/ONNX). No Windows o headroom recusa o

# backend nativo por padrão e cai para o detector puro-Python; manter

# "auto" evita o aviso a cada chamada. Use "rust" em Linux/container.

  detect_backend: auto

# Compressão inline (headroom.compress) usada por `headroom_tool.py compress`.

  compress:
    # None = deixa o Kompress decidir pelo próprio limiar (conservador).
    target_ratio: null
    min_tokens_to_compress: 250
    compress_user_messages: true
    protect_recent: 0

# ── Proxy interceptor ─────────────────────────────────────────────

  proxy:
    enabled: true
    # 127.0.0.1 por padrão (Artigo VII — o proxy carrega a chave do Foundry
    # em trânsito; NÃO expor em 0.0.0.0 fora de container).
    host: "127.0.0.1"
    port: 8787
    # Upstream real. No headroom isto NÃO é uma flag --upstream: é
    # `--anthropic-api-url` / env ANTHROPIC_TARGET_API_URL.
    upstream: "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
    backend: "anthropic"
    # JSONL nativo do proxy (timestamp, model, tokens_before, tokens_after,
    # latency_ms). Relativo à raiz do repo.
    log_file: ".headroom/proxy-requests.jsonl"
    mode: "token"          # token = máxima compressão | cache = prefix-cache
    http2: false           # HTTP/1.1 evita corrupção TLS em stream cancelado
    request_timeout_seconds: 600

# ── Observabilidade ───────────────────────────────────────────────

  observability:
    # Relativo a projects/{project}/ — fica ao lado de agent-events.jsonl
    # e pipeline-run-state.json, escritos por pipeline_observer.py.
    metrics_file: "outputs/observability/headroom-metrics.jsonl"

# ── Degradação ────────────────────────────────────────────────────

Bash Find tests and consumers of agent_registry
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && ls tests/ 2>/dev/null | head -30; echo "=== registry tests ==="; grep -rln "agent_registry" tests/ specs/ src/ --include=*.py | head -20

OUT
ava-fabric-agents
tools
utils
=== registry tests ===
tests/tools/test_agent_registry.py
tests/tools/test_agent_wrappers.py
src/shared/tools/agent_registry.py
src/shared/tools/agent_runner.py
src/shared/tools/generate_agent_wrappers.py
src/shared/tools/generate_observability_report.py
src/shared/tools/pipeline_observer.py
src/shared/utils/verify_agent_observability.py
Bash Find headroom block in template project config
IN
grep -n -B2 -A 20 "headroom:" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/projects/_template/context/project-config.yaml" | head -50

OUT
441-#
442-# TODO O BLOCO É OPCIONAL — omitido, valem os defaults da tool. Declare apenas
443:# o que quiser desviar; o merge é recursivo, então `headroom: {proxy: {port: 8788}}`
444-# altera só a porta e preserva o resto.
445-#
446-# ATENÇÃO ao modelo: o endpoint da esteira é Anthropic-compatible
447-# (…services.ai.azure.com/anthropic), NÃO Azure OpenAI. Ver copilot-cli-v1.bat.
448-#
449-# Diagnóstico (não altera nada, só mede):
450-#   python src/shared/tools/headroom/headroom_config.py -p {PROJECT}
451-#   python src/shared/tools/headroom/headroom_tool.py -p {PROJECT} doctor
452-#   python src/shared/tools/headroom/headroom_tool.py -p {PROJECT} stats
453-#
454-# Referências: src/shared/tools/headroom/README.md ·
455-#              specs/031-headroom-context-compression-proxy
456-# ─────────────────────────────────────────────────────────────────────────────
457:# headroom:
458-#   enabled: true                       # false = desliga a tool neste projeto
459-#   model: "claude-sonnet-4-6"          # modelo do deployment Foundry
460-#   context_limit: 200000               # janela do modelo, em tokens
461-#   proxy:
462-#     port: 8787
463-#     upstream: "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
464-#   observability:
465-#     metrics_file: "outputs/observability/headroom-metrics.jsonl"
466-
467-# Migration Design Gate Configuration
468-# Gate de qualidade que valida completude e consistência de TODOS os artefatos
469-# da fase F2 (Migration Design) ANTES de autorizar transição para Build Cycle (F3).
470-# Referência: src/shared/checklists/migration-design-checklist.md
471-# ─────────────────────────────────────────────────────────────────────────────
472-migration_design_gate:
473-  enabled: true                           # true = gate executa automaticamente após Fase 8
474-                                          # false = gate desabilitado (não recomendado)
475-
476-  threshold_pct: 85                       # Score mínimo (%) para APPROVED_WITH_MINOR_GAPS
477-                                          # 100% = apenas APPROVED (todos os critérios atendidos)
Bash Read rest of headroom.yaml
IN
sed -n '60,140p' src/shared/tools/headroom/headroom.yaml

OUT

# ── Degradação ────────────────────────────────────────────────────

# true = qualquer falha do headroom devolve o conteúdo original sem

# comprimir. A esteira nunca para por causa desta tool (IV3).

  fallback_on_error: true
Bash Outline agents catalog
IN
grep -n "^## \|^### \|^| F[0-9]" docs/agents-catalog.md | head -60

OUT
12:## Índice
27:## Visão Geral da Esteira
45:## F1 — AS-IS Diagnostic
49:### `ava-asis-orchestrator`
84:### `ava-asis-solution-delphi`
112:### `ava-asis-db-analyzer`
147:### `ava-asis-security-review`
171:### `ava-asis-documentation` (v3.0.0)
198:### `ava-asis-inventory`
222:### `ava-asis-gaps-risks`
246:## F2 — TO-BE Architecture
250:### `ava-tobe-orchestrator`
268:### `ava-tobe-adr`
290:### `ava-tobe-adr`
312:### `ava-tobe-architecture-design`
336:### `ava-tobe-database-design`
360:### `ava-tobe-architecture-technical`
383:### `ava-tobe-user-journeys`
407:### `ava-tobe-measure-size`
430:### `ava-tobe-migration-plan`
454:### `ava-coder-dotnet`
476:### `ava-docs-tobe`
499:### `ava-test-plan-tobe`
529:## F3 — Prototype
534:### `ava-prototype`
567:## F4 — Tech Stack
571:### `ava-stack-orchestrator`
582:### `ava-stack-dotnet-backend`
610:### `ava-stack-angular-frontend`
641:### `ava-stack-react-frontend`
677:### `ava-build-cycle-react-scaffold`
709:### `ava-stack-vue-frontend`
742:## F4 — Prototype
744:### `ava-prototype`
767:### `ava-stack-react-frontend`
796:## F4 — Prototype
798:### `ava-prototype`
824:## F5 — QA Agents
828:### `ava-qa-orchestrator`
844:### `ava-qa-gaps-requirements`
855:### `ava-qa-behavior-mapping`
866:### `ava-qa-scenario-generator`
877:### `ava-qa-test-case-generator`
888:### `ava-qa-script-generator`
899:### `ava-qa-exploratory`
910:### `ava-qa-evidence-capture`
931:### `ava-qa-defect-identifier`
942:### `ava-qa-db-integrity-test`
977:### `ava-qa-contract-test-generator`
999:### `ava-qa-frontend-test-generator`
1020:### `ava-qa-bridge-fastqa-tobe`
1050:## F6 — DevOps
1054:### `ava-devops-iac`
1077:### `ava-devops-ci`
1100:### `ava-devops-cd`
1117:### `ava-devops-compare-version`
1140:### `ava-devops-package-approval`
1154:### `ava-devops-podman-run`
1193:## F7 — Deliverables
1197:### `ava-deliverable-packager`
Bash Check tokens_before field name across vendor and docs
IN
grep -rn "tokens_before" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/" 2>/dev/null | head -20; echo "=== docs claim ==="; grep -rn "tokens_before\|input_tokens_original" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/README.md" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/docs/" | head -20

OUT
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cache/anthropic.py:186:            tokens_before=total_tokens,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cache/base.py:183:    tokens_before: int = 0
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cache/google.py:342:            tokens_before=total_tokens,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cache/openai.py:294:        tokens_before = self._estimate_total_tokens(messages)
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cache/openai.py:333:            tokens_before=tokens_before,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/ccr/mcp_server.py:416:        input_tokens = result.tokens_before
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/ccr/mcp_server.py:790:            tokens_before=before,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cli/agent_savings.py:177:        before = sum(int(getattr(record, "tokens_before", 0)) for record in agent_records)
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cli/perf.py:79:                "tokens_before",
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cli/perf.py:97:                f"before={r.tokens_before} after={r.tokens_after} saved={r.tokens_saved} "
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cli/proxy.py:507:        "tokens_before, tokens_after, latency_ms, etc. "
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/cli/savings.py:40:    before = int(window.get("tokens_before", 0) or 0)
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:429:        tokens_before = tokenizer.count_messages(messages)
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:538:                    "tokens_before": tokens_before,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:552:            tokens_after = tokens_before
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:576:            tokens_input_before=tokens_before,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:597:            tokens_before=tokens_before,
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:770:        tokens_before = tokenizer.count_messages(messages)
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:789:        tokens_saved = tokens_before - result.tokens_after
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/client.py:793:        cost_before = estimate_cost(tokens_before, output_buffer, model, provider=self._provider)
=== docs claim ===
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/docs/02-esteira-github-cli.md:22:│    comprime o contexto · registra tokens_before/after/latency_ms     │
c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/docs/README.md:35:| **Proxy** | 100% das requisições | model, tokens_before/after, latency_ms | qual agente originou | `~/.headroom/logs/proxy.log` + `.headroom/proxy-requests.jsonl` |
Bash Read pipeline overview section
IN
sed -n '27,48p' docs/agents-catalog.md; echo "=== F8 ==="; grep -n "^## F8" -A 20 docs/agents-catalog.md | head -30

OUT

## Visão Geral da Esteira

```
projects/{PROJECT_NAME}/inputs/
  └─ código-fonte legado (Delphi, COBOL, VB6...)

F1 ─── AS-IS Diagnostic        ─── 8 agentes  →  projects/{PROJECT_NAME}/outputs/asis/
F2 ─── TO-BE Architecture       ─── 12 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/
F3 ─── Prototype                ─── 1 agente   →  projects/{PROJECT_NAME}/outputs/tobe/prototype/
F4 ─── Tech Stack               ─── 3 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/source-code/
F5 ─── QA Agents                ─── 10 agentes  →  projects/{PROJECT_NAME}/outputs/qa/
F6 ─── DevOps                   ─── 5 agentes  →  projects/{PROJECT_NAME}/outputs/tobe/iac/
F7 ─── Deliverables             ─── 7 agentes  →  projects/{PROJECT_NAME}/outputs/deliverables/
F8 ─── Summary (cross-cutting)  ─── 2 agentes  →  projects/{PROJECT_NAME}/outputs/summary/
```

---

## F1 — AS-IS Diagnostic

Fase de diagnóstico completo do sistema legado. O orchestrator coordena os sub-agentes em duas waves — Wave 1 (agente de solução + segurança, imediato) → Solution Agent Gate → Wave 2 (6 agentes, dependentes dos artefatos do agente de solução) — e consolida os resultados no Master Report.

=== F8 ===
1300:## F8 — Summary
1301-
1302-### `ava-summary` (v1.1.0)
1303-
1304-| Campo        | Valor                                                                                                                                                                                               |
1305-| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
1306-| **Arquivo**  | `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`                                                                                                                                     |
1307-| **Papel**    | Consolidação de todos os outputs em HTML executivo autocontido                                                                                                                                      |
1308-| **Template** | `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`                                                                                                                        |
1309-| **v1.1.0**   | Step 0.5: verificação de integridade de artefatos (existência + tamanho > 0) antes de gerar HTML; emite `[ARTIFACT-MISSING]`/`[ARTIFACT-EMPTY]` por artefato ausente e omite a seção correspondente |
1310-
1311-**Modos de invocação:**
1312-
1313-| Comando | Descrição                                             |
1314-| ------- | ----------------------------------------------------- |
1315-| `SI`    | Summary Independente — solicita o caminho dos outputs |
1316-| `SAS`   | Summary AS-IS Only — gera com dados da F1 apenas      |
1317-| `STOBE` | Summary TO-BE Only — gera com dados da F2 apenas      |
1318-| `SFull` | Summary Completo — todas as fases disponíveis         |
1319-
1320-**Input:**
Bash Confirm RequestLogger wiring to log_file
IN
grep -rn "RequestLogger(" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/proxy/server.py" | head; echo "=== log_file consumers ==="; grep -rn "config.log_file\|log_file=config" "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents/src/shared/tools/headroom/vendor/headroom/proxy/server.py" | head

OUT
1006:            RequestLogger(
=== log_file consumers ===
1007:                log_file=config.log_file,
Bash Show agent_registry CLI help
IN
python src/shared/tools/agent_registry.py --help 2>&1 | head -40

OUT
usage: agent_registry.py [-h] [--json] [--catalog] [--agent AGENT]
                         [--orchestrator FASE] [--validate]

Fonte canônica dos agentes da esteira (id, fase, versão)

options:
  -h, --help           show this help message and exit
  --json               Emite todos os registros em JSON
  --catalog            Emite no formato AGENT_CATALOG
  --agent AGENT        Mostra apenas este agent_id
  --orchestrator FASE  Imprime o id do orquestrador da fase (ex.: F1); exit 1
                       se não houver
  --validate           Reprova frontmatters que impedem persistência de
                       artefatos (exit 1)

Exemplos:
  agent_registry.py
  agent_registry.py --json
  agent_registry.py --catalog
  agent_registry.py --agent ava-qa-exploratory
Bash List orchestrator per phase
IN
for f in F1 F2 F3 F4 F5 F6 F7 F8; do printf "%s -> " $f; python src/shared/tools/agent_registry.py --orchestrator $f 2>&1 | head -1; done

OUT
F1 -> ava-asis-orchestrator
F2 -> ava-tobe-orchestrator
F3 -> sem orquestrador registrado para a fase F3
F4 -> ava-stack-orchestrator
F5 -> ava-qa-orchestrator
F6 -> ava-devops-orchestrator
F7 -> sem orquestrador registrado para a fase F7
F8 -> sem orquestrador registrado para a fase F8
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\docs\issues\GUIDE-headroom-foundry-endpoint.md
I have a complete picture. Here is the thorough report.

Headroom proxy tooling — full map
Root: c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\headroom\

Layout: headroom_config.py (config resolution), headroom_tool.py (CLI/orchestration), headroom_context.py, mcp_server.py, headroom.yaml (defaults), setup.ps1/setup.sh, run_standalone.ps1/.sh, Containerfile, podman-compose.yml, docs/, .venv/, and vendor/ — a git subtree of the full upstream headroom-ai 0.33.0 repo (that's where the actual proxy lives).

1. headroom_config.py
   File: ...\src\shared\tools\headroom\headroom_config.py (291 lines)

CLI flags (lines 274–290, if __name__ == "__main__")

ap.add_argument("-p", "--project", help="Projeto para aplicar o bloco headroom: do project-config.yaml")
ap.add_argument("--env", action="store_true",
                help="Emite só as variáveis de ambiente do proxy (consumido por run_standalone.*)")
ap.add_argument("--proxy-url", action="store_true",
                help="Emite só a URL do proxy, sem JSON (consumido por copilot-cli-headroom.bat)")
no flags → pretty-printed JSON of the whole effective config
--env → JSON dict of only the proxy env vars (proxy_env())
--proxy-url → plain single line http://host:port, no JSON (deliberately, so for /f in .bat can consume it — comment at L287)
Precedence (docstring L9–13, implemented in load_config, L172–196)
Strong → weak:

Environment — HEADROOM_*, AVA_FOUNDRY_*, ANTHROPIC_TARGET_API_URL
Project — projects/{project}/context/project-config.yaml → headroom: block
Tool defaults — src/shared/tools/headroom/headroom.yaml → headroom: block
(hard floor) _FALLBACK_DEFAULTS dict at L57–83, used if pyyaml missing or YAML unreadable — load_config never raises (_read_yaml L150–158 swallows everything).
Merge is recursive (_deep_merge, L130–138), so a project may override just headroom: {proxy: {port: 8788}}.

Env → config-path map (_ENV_MAP, L87–100)
env var	dotted config path	type
HEADROOM_ENABLED	enabled	bool
AVA_FOUNDRY_MODEL	model	str
AVA_FOUNDRY_CONTEXT_LIMIT	context_limit	int
HEADROOM_DETECT_BACKEND	detect_backend	str
HEADROOM_TARGET_RATIO	compress.target_ratio	float
HEADROOM_HOST	proxy.host	str
HEADROOM_PORT	proxy.port	int
ANTHROPIC_TARGET_API_URL	proxy.upstream	str
HEADROOM_BACKEND	proxy.backend	str
HEADROOM_LOG_FILE	proxy.log_file	str
HEADROOM_MODE	proxy.mode	str
HEADROOM_METRICS_FILE	observability.metrics_file	str
Malformed env values print a warning to stderr and are ignored (L189–194) — they never kill the tool.

Paths (L47–52)

SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPT_DIR.parents[3]          # …/imfai-ava-fabric-apps-agents
VENDOR_DIR   = SCRIPT_DIR / "vendor"
VENV_DIR     = SCRIPT_DIR / ".venv"
TOOL_CONFIG  = SCRIPT_DIR / "headroom.yaml"
headroom.yaml — location and keys
Location: ...\src\shared\tools\headroom\headroom.yaml (single top-level key headroom:)

headroom:
  enabled: true
  model: "claude-sonnet-4-6"
  context_limit: 200000
  detect_backend: auto            # auto | rust  (rust = Magika/ONNX, Linux/container)
  compress:
    target_ratio: null
    min_tokens_to_compress: 250
    compress_user_messages: true
    protect_recent: 0
  proxy:
    enabled: true
    host: "127.0.0.1"
    port: 8787
    upstream: "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
    backend: "anthropic"
    log_file: ".headroom/proxy-requests.jsonl"     # relative to repo root
    mode: "token"                                  # token = max compression | cache = prefix-cache
    http2: false                                   # HTTP/1.1 avoids TLS corruption on cancelled streams
    request_timeout_seconds: 600
  observability:
    metrics_file: "outputs/observability/headroom-metrics.jsonl"   # relative to projects/{p}/
  fallback_on_error: true
Note proxy.enabled and compress.* and fallback_on_error have no env override — only YAML.

Effective host/port resolution — proxy_url() (L245–255)

def proxy_url(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or load_config()
    proxy = cfg.get("proxy", {})
    return f"http://{proxy.get('host', '127.0.0.1')}:{proxy.get('port', 8787)}"
The docstring explains why it exists: the port was duplicated between headroom.yaml and copilot-cli-headroom.bat, so starting the proxy on 8788 made the .bat probe 8787, fail, and silently degrade to the direct endpoint — running a whole phase without compression.

proxy_env() (L220–242) — the env handed to headroom proxy

env = {
    "HEADROOM_HOST":             str(proxy.get("host", "127.0.0.1")),
    "HEADROOM_PORT":             str(proxy.get("port", 8787)),
    "HEADROOM_BACKEND":          str(proxy.get("backend", "anthropic")),
    "ANTHROPIC_TARGET_API_URL":  str(proxy.get("upstream", "")),
    "HEADROOM_MODE":             str(proxy.get("mode", "token")),
    "HEADROOM_LOG_FILE":         str(proxy_log_path(cfg)),      # absolutized
    "HEADROOM_REQUEST_TIMEOUT":  str(proxy.get("request_timeout_seconds", 600)),
    "HEADROOM_TELEMETRY":        "off",
}
Plus HEADROOM_DETECT_BACKEND only when detect_backend != "auto". Empty values are filtered out. Docstring explicitly states: headroom has no --upstream flag — upstream is --anthropic-api-url / ANTHROPIC_TARGET_API_URL (verified against headroom proxy --help, v0.33.0).

Other public functions
project_config_path(project_name) L163 → REPO_ROOT/projects/{p}/context/project-config.yaml
metrics_path(project_name, cfg) L199 → REPO_ROOT/projects/{p}/{observability.metrics_file}, mkdir parents
proxy_log_path(cfg) L209 → absolutizes proxy.log_file against REPO_ROOT, mkdir parents
venv_python() L258 → .venv/Scripts/python.exe or .venv/bin/python, else None
venv_headroom() L266 → .venv/Scripts/headroom.exe or .venv/bin/headroom, else None
⚠️ Latent bug at L119–122: _coerce(raw, "float") calls low_is_none(raw) but references an undefined local low → the branch is None if low_is_none(raw) else float(raw) — actually that's fine; but low is only defined in the bool branch. Re-reading: line 121 is return None if low_is_none(raw) else float(raw) — correct. No bug. (The low variable at L112 is scoped to the bool branch only, and is not referenced in the float branch.)

2. headroom_tool.py
   File: ...\src\shared\tools\headroom\headroom_tool.py (851 lines)

Global args (L776–778)
-p/--project, --language, then a required subcommand.

Subcommands (L780–825)
subcommand	args	notes
slice	--agent (req), --json, --with-payloads	needs -p
decode	--input (req), -o/--out
compress	--input (req), -o, --model, --limit, --agent, --phase
metrics	--agent, --phase, --original, --compressed (all req), --latency-ms, --model, --run-id, --proxy-used, --error, --json	needs -p
attribute	--phase, --dry-run, --json	needs -p
stats	--json	needs -p
doctor	--json
proxy	positional action ∈ {start, stop, status}, --json
needs_project = {"slice", "metrics", "stats", "attribute"} (L829).

Exit codes (module docstring L36–40)
0 OK · 1 degraded (engine missing, proxy down, artifact missing) · 2 usage/exec error.

proxy status — how up/down is signalled (cmd_proxy, L696–713)

if args.action == "status":
    up = _port_open(host, port)
    detail = {"running": up, "host": host, "port": port,
              "upstream": proxy.get("upstream"),
              "pid": PID_FILE.read_text(encoding="utf-8").strip()
                     if PID_FILE.is_file() else None}
    if args.json:
        print(json.dumps(detail, indent=2, ensure_ascii=False))
    else:
        print(f"{'🟢' if up else '🔴'} proxy {host}:{port} "
              f"{'no ar' if up else 'fora do ar'} → {proxy.get('upstream')}")
    sys.exit(0 if up else 1)
Exit 0 = up, exit 1 = down. The check is a plain TCP connect (_port_open, L85–91), 1.0 s timeout, with 0.0.0.0/"" remapped to 127.0.0.1 for probing. It does not do an HTTP health check (/livez exists upstream but is unused here).

PID_FILE = REPO_ROOT / ".headroom" / "proxy.pid" (L65).

proxy start — programmatic startup (L715–739)

if args.action == "start":
    if _port_open(host, port):
        print(f"ℹ️  proxy já está no ar em {host}:{port}")
        sys.exit(0)
    env = {**os.environ, **hcfg.proxy_env(cfg)}
    cmd = [_headroom_exe(), "proxy", "--host", host, "--port", str(port)]
    if not proxy.get("http2", False):
        cmd.append("--no-http2")
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        detach = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    else:
        detach = {"start_new_session": True}
    process = subprocess.Popen(cmd, env=env, cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detach)
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
_headroom_exe() (L79–82) prefers the venv headroom.exe, falls back to bare "headroom" on PATH. FileNotFoundError → _fail(...) exit 2.

Programmatic startup from Python — three options, in increasing directness:

subprocess.run([sys.executable, "…/headroom_tool.py", "proxy", "start"]) — the pattern agent_runner.py uses.
Replicate cmd_proxy yourself: env = {**os.environ, **hcfg.proxy_env(cfg)} then Popen([venv_headroom(), "proxy", "--host", h, "--port", p, "--no-http2"], env=env).
In-process (venv only): from headroom.proxy.server import ProxyConfig, run_server; run_server(config) — see vendor/headroom/cli/proxy.py:1174 for how ProxyConfig is built and :1584 for run_server(config, print_banner=False).
proxy stop (L741–755): reads the pid file, taskkill /PID <pid></pid> /F /T on Windows or os.kill(pid, 15) elsewhere, then unlinks the pid file. Exit 1 if no pid file.

doctor (L649–693)
Checks: config, vendor/pyproject.toml present, venv python, venv headroom CLI, import headroom, agent slices, proxy port open, upstream configured, and copilot → proxy (_copilot_routing, L626–646, which checks COPILOT_PROVIDER_BASE_URL matches hcfg.proxy_url(cfg) — designed to make silent proxy bypass visible). Exit 2 only if the vendor fork is missing; else 0 if all green, 1 otherwise.

3. The proxy itself (vendor)
   HTTP paths accepted
   Registered in ...\vendor\headroom\providers\proxy_routes.py:

# L207

@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    custom_base = request.headers.get("x-headroom-base-url", "").strip()
    if custom_base:
        return await proxy.handle_anthropic_messages(request, upstream_base_url=custom_base.rstrip("/"))
    return await proxy.handle_anthropic_messages(request)

# L220

@app.post("/anthropic/v1/messages")
async def foundry_anthropic_messages(request: Request):
    normalize_request_path(request, "/v1/messages")
    return await proxy.handle_anthropic_messages(request, _api_target(proxy, "anthropic"))
Yes, it proxies /v1/messages. It also accepts /anthropic/v1/messages (the Foundry-shaped path).

More Anthropic routes in ...\vendor\headroom\providers\route_specs.py:

L29 POST /v1/messages/count_tokens (passthrough)
L78 POST /v1/messages → handle_anthropic_messages
L83–99 /v1/messages/batches family (create / list / get / results / cancel)
Other surfaces: /v1/chat/completions, /v1/responses (HTTP + WebSocket), Gemini/Vertex publisher paths, Bedrock /model/{id}/invoke* (only when --bedrock-api-url set), plus a catch-all passthrough. Ops endpoints in vendor\headroom\proxy\server.py: /livez L3199, /readyz L3216, /health L3222, /stats L4178, /stats-history L4246, /metrics L4374 (Prometheus), /dashboard L3327.

The startup banner (vendor\headroom\cli\proxy.py:1499–1508) prints exactly:

Routing:
  /v1/messages                    → {anthropic_url}
  ...
Usage:
  Claude Code:   ANTHROPIC_BASE_URL=http://{host}:{port} claude
  Codex / OpenAI: OPENAI_BASE_URL=http://{host}:{port}/v1 your-app
Does base_url need a path suffix?
No. Point the Anthropic SDK at the bare http://127.0.0.1:8787 — the SDK appends /v1/messages, which is a registered route. run_standalone.ps1:71 says exactly that: ANTHROPIC_BASE_URL=http://host:port.

http://127.0.0.1:8787/anthropic also works (mirrors the Foundry URL shape). The upstream helper documenting this is vendor\headroom\cli\wrap.py:1128–1138:

def _foundry_proxy_url(proxy_url: str) -> str:
    """ANTHROPIC_FOUNDRY_BASE_URL is the full base URL the Anthropic SDK appends
    /v1/messages to, so it must include the /anthropic path component to match
    the Azure AI Foundry endpoint structure."""
    return proxy_url.rstrip("/") + "/anthropic"
That /anthropic suffix requirement applies to the upstream (ANTHROPIC_TARGET_API_URL must be https://<res></res>.services.ai.azure.com/anthropic), not to the local proxy base_url.

Where ANTHROPIC_TARGET_API_URL is read
...\vendor\headroom\providers\registry.py:112–131:

def resolve_api_overrides(*, anthropic_api_url, openai_api_url, gemini_api_url,
                          cloudcode_api_url, vertex_api_url=None, environ=None):
    env = environ or os.environ
    return ProviderApiOverrides(
        anthropic=anthropic_api_url
        or env.get("ANTHROPIC_TARGET_API_URL")
        or env.get("ANTHROPIC_FOUNDRY_BASE_URL"),
        ...
    )
Precedence: --anthropic-api-url CLI flag > ANTHROPIC_TARGET_API_URL > ANTHROPIC_FOUNDRY_BASE_URL > default https://api.anthropic.com.

Called from vendor\headroom\cli\proxy.py:1108–1115, then normalized by resolve_api_targets → _normalize_api_url (registry.py:87–94), which strips a trailing / and a trailing /v1. So .../anthropic stays intact.

Forwarding (...\vendor\headroom\proxy\handlers\anthropic.py:2807–2814):

url = (
    build_copilot_upstream_url(upstream_base_url, request.url.path)
    if upstream_base_url
    else f"{self.ANTHROPIC_API_URL}/v1/messages"
)
if upstream_base_url and request.url.query:
    url = f"{url}?{request.url.query}"
So the effective upstream is https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic + /v1/messages.

The --anthropic-api-url flag is declared at vendor\headroom\cli\proxy.py:810–814:

@click.option("--anthropic-api-url", default=None,
    help="Custom Anthropic API URL for passthrough endpoints (env: ANTHROPIC_TARGET_API_URL)")
Streaming (SSE) passthrough — yes
...\vendor\headroom\proxy\handlers\anthropic.py returns StreamingResponse(..., media_type="text/event-stream") at L3585, L3605, L3616; the streaming engine ...\vendor\headroom\proxy\handlers\streaming.py does so at L1277, L1659, L1881, L2097. Handler signature is -> Response | StreamingResponse (anthropic.py:519).

One caveat worth knowing: if CCR is active and the request carries the injected headroom_retrieve tool, streaming may be buffered (buffered_stream_ccr, anthropic.py:~2818–2830, sets body["stream"] = False and re-emits as SSE via _BufferedCCRResponse(media_type="text/event-stream") at L3751). Pass --no-ccr / HEADROOM_NO_CCR=1 to keep true streaming — the flag help at cli/proxy.py:314–323 explicitly recommends it for "streaming / non-MCP clients that can't resolve an injected tool".

HTTP/2 to upstream is disabled by this repo (--no-http2) to avoid SSLV3_ALERT_BAD_RECORD_MAC on cancelled concurrent streams (headroom.yaml:51, headroom_tool.py:721–722, run_standalone.ps1:78–79).

anthropic-version header — needed?
The proxy does not synthesize it. It copies the inbound header set through, so whatever your client sends is what Foundry receives. ...\vendor\headroom\proxy\handlers\anthropic.py:780–814:

headers = dict(request.headers.items())
headers.pop("host", None)
headers.pop("content-length", None)
headers.pop("content-encoding", None)
headers.pop("transfer-encoding", None)
headers.pop("accept-encoding", None)
tags = extract_tags(headers)
...
headers = _strip_internal_headers(headers)          # drops x-headroom-*
headers = merge_extra_headers(headers, self.config.anthropic_extra_headers)
anthropic-version also matters for routing: registry.py:388–396 _is_anthropic_auth() treats a request as Anthropic if it has x-api-key, anthropic-version, Authorization: Bearer sk-ant-…, or a Claude Code/CLI user-agent. That decides the upstream for catch-all passthrough. The Anthropic Python SDK sends anthropic-version: 2023-06-01 automatically. Everything else in this repo sets it explicitly:

copilot-cli-headroom.bat:79 → COPILOT_PROVIDER_HEADERS=anthropic-version: 2023-06-01
src\shared\tools\agent_runner.py:227 → same
pipeline_runner.py:531–532 → default_headers={"anthropic-version": "2023-06-01"}
Recommendation: send it.

Auth / bearer forwarding
The proxy forwards the client's credential verbatim and injects none of its own. docs\01-standalone.md:230–232 states it plainly:

Autenticação: o proxy encaminha o header de auth do cliente para o upstream. Ele não injeta credencial própria — a chave continua vindo de quem chama.

So x-api-key (what anthropic.Anthropic(api_key=…) sends) and Authorization: Bearer … (what the Copilot CLI sends via COPILOT_PROVIDER_BEARER_TOKEN) both pass straight through to Foundry.

Extras / related:

--anthropic-extra-headers / ANTHROPIC_TARGET_API_HEADERS (cli/proxy.py:902–909, resolved by registry.py:134–157) — a JSON object merged into and overriding forwarded headers. Useful if Foundry needed e.g. {"Api-Key": "..."}.
Inbound auth on the proxy itself: HEADROOM_PROXY_TOKEN (cli/proxy.py:1274). Unset + loopback bind = unauthenticated /v1/*, which is the current posture (headroom.yaml:39–41 — 127.0.0.1 only, "NÃO expor em 0.0.0.0 fora de container").
x-headroom-base-url request header overrides the upstream per-request (proxy_routes.py:213–217).
4. JSONL metrics / telemetry
There are two separate trails — docs\01-standalone.md:249–253 and docs\README.md:35 both flag this:

trail	path	writer	configured by
headroom-internal (headroom perf reads this)	~/.headroom/logs/proxy.log	vendor internal	—
per-request JSONL	.headroom/proxy-requests.jsonl (repo root)	RequestLogger	HEADROOM_LOG_FILE / proxy.log_file
per-agent AVA metrics	projects/{p}/outputs/observability/headroom-metrics.jsonl	headroom_tool._append_metric	HEADROOM_METRICS_FILE / observability.metrics_file
The proxy JSONL
Configured by --log-file / HEADROOM_LOG_FILE (vendor\headroom\cli\proxy.py:500–510), wired to ProxyConfig(log_file=None if is_stateless else log_file) at cli/proxy.py:1251, consumed at vendor\headroom\proxy\server.py:1006–1007 → RequestLogger(log_file=config.log_file, ...).

Writer — ...\vendor\headroom\proxy\request_logger.py:134–144:

if self.log_file:
    try:
        with open(self.log_file, "a") as f:
            log_dict = asdict(entry)
            if not self.log_full_messages:
                log_dict.pop("request_messages", None)
                log_dict.pop("compressed_messages", None)
                log_dict.pop("response_content", None)
            f.write(json.dumps(log_dict) + "\n")
    except OSError:
        pass  # Graceful degradation: memory-only logging continues
⚠️ Field-name mismatch — likely a real bug
The --log-file help text (cli/proxy.py:505–508) promises:

"Each line is a JSON object with fields: timestamp, request_id, model, tokens_before, tokens_after, latency_ms, etc."

But the actual dataclass serialized by asdict() is RequestLog in ...\vendor\headroom\proxy\models.py:48–98, whose fields are:

request_id: str
timestamp: str
provider: str
model: str
input_tokens_original: int        # <- not "tokens_before"
input_tokens_optimized: int       # <- not "tokens_after"
output_tokens: int | None
tokens_saved: int
savings_percent: float
optimization_latency_ms: float
total_latency_ms: float | None    # <- not "latency_ms"
tags: dict[str, str]
cache_hit: bool
transforms_applied: list[str]
cache_read_tokens / cache_write_tokens / uncached_input_tokens: int = 0
waste_signals / request_messages / compressed_messages / response_content / error / turn_id
Now compare headroom_tool.py:127–131, the aliases cmd_attribute tolerates:

_TS_KEYS      = ("timestamp", "ts", "time", "created_at")
_BEFORE_KEYS  = ("tokens_before", "input_tokens_before", "tokens_in", "prompt_tokens_before")
_AFTER_KEYS   = ("tokens_after", "input_tokens_after", "tokens_out", "prompt_tokens_after")
_LATENCY_KEYS = ("latency_ms", "duration_ms", "elapsed_ms")
timestamp matches, but none of the before/after/latency aliases match input_tokens_original / input_tokens_optimized / total_latency_ms. _read_proxy_log (L162–193) drops any line where before or after is None (L180–181), so every line would be discarded and headroom_tool.py -p X attribute would report "nenhuma requisição no log do proxy" and exit 1 even with a fully populated JSONL. Also tokens_saved and savings_percent are already in the JSONL and go unread.

I could not empirically confirm — .headroom/ exists (created 2026-08-02) but proxy-requests.jsonl has never been written, i.e. no traffic has yet gone through the proxy in this checkout. Worth verifying with one real request before acting on it.

The AVA metrics JSONL
Written by _append_metric (headroom_tool.py:94–99) to hcfg.metrics_path(project, cfg). Three source values distinguish provenance:

"manual" — cmd_metrics (L436, agent self-report via --original/--compressed)
"proxy" — cmd_attribute (L491, credited from the proxy log by time-window overlap)
"self-report" — from the pipeline_observer track hook (read at cmd_stats L605)
cmd_attribute (L458–552) joins proxy requests to agent execution windows read from projects/{p}/outputs/observability/pipeline-run-state.json (_agent_windows, L196–231). Overlapping windows split a request 1/N and mark it attribution: "ambiguous" (attribute_requests, L234–285).

5. setup.ps1 and run_standalone.ps1
   setup.ps1 (113 lines)
   Params: -SkipML, -Force.

L37–40: resolves $ToolDir, $VenvDir = $ToolDir\.venv, $Vendor = $ToolDir\vendor.
L48–50: hard-errors if vendor\pyproject.toml is missing, with the recovery command: git subtree add --prefix src/shared/tools/headroom/vendor https://github.com/headroomlabs-ai/headroom.git main --squash
L53–57: requires Python ≥ 3.10.
L60–67: -Force wipes the venv; creates it with python -m venv $VenvDir.
L69–70: $VenvPy = .venv\Scripts\python.exe, falling back to .venv/bin/python.
L73: upgrades pip/setuptools/wheel.
L76: extras = proxy,mcp,ml,code,memory,otel, or proxy,mcp,code,memory,otel with -SkipML (skips torch, ~3 GB).
L84–95: if cargo on PATH → pip install -e "$Vendor[$extras]" (editable fork, maturin/Rust build, local patches take effect immediately). Else → reads version = "…" out of vendor\pyproject.toml and installs the matching PyPI wheel headroom-ai[$extras]==$vendorVersion; the vendor tree then serves only as reference/patch source.
L97: pip install pyyaml>=6.0 pytest>=8.0.
L102–105: verifies import headroom and runs headroom.exe --version.
Venv path: src\shared\tools\headroom\.venv — deliberately isolated so it doesn't contaminate the repo's main venv (invariant IV7: "o repo é stdlib-only").

run_standalone.ps1 (79 lines)
Params: -Project <name></name>, -Port <int></int>.

L34–46: resolves $VenvPy (.venv\Scripts\python.exe → .venv/bin/python) and $VenvHeadroom (.venv\Scripts\headroom.exe → .venv/bin/headroom); errors telling you to run setup.ps1 (or -Force) if either is missing.
L49–56: shells out to headroom_config.py --env (with -p $Project if given), parses the JSON, and sets every key as a process env var.
L57: -Port overrides $env:HEADROOM_PORT after the fact.
L62–76: prints the effective listen URL / upstream / backend / mode / log path, plus the two client-wiring hints (ANTHROPIC_BASE_URL=… for Claude Code, COPILOT_PROVIDER_BASE_URL=… for Copilot CLI).
L79: & $VenvHeadroom proxy --host $listenHost --port $listenPort --no-http2 — foreground, Ctrl+C stops it.
Note: it does not pass --anthropic-api-url; upstream flows purely through the ANTHROPIC_TARGET_API_URL env var set in step 2. POSIX twins: setup.sh (--skip-ml) and run_standalone.sh (--port).

6. Existing Python client code that calls the proxy via the anthropic SDK
   The only anthropic.Anthropic(...) in the repo — and it does not use the proxy
   c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\pipeline_runner.py

Constants (L40–48):

WORKSPACE   = Path(r"c:\_info\Projetos\Hub\SRC_Torre_Apps_31_07")

# Foundry — endpoint Anthropic-compatible validado via VPN (2026-08-04)

# Resolve para 10.26.2.12 (private endpoint) | path /v1/messages usado pelo SDK

ENDPOINT    = "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
DEPLOYMENT  = "claude-sonnet-4-6"
API_KEY_FILE = WORKSPACE / ".copilot-key"
MAX_TOKENS  = 32768
Client construction (L529–540):

api_key = API_KEY_FILE.read_text(encoding="utf-8").strip()
client = anthropic.Anthropic(
    api_key=api_key,
    base_url=ENDPOINT,
    default_headers={"anthropic-version": "2023-06-01"},
)
with client.messages.stream(
    model=DEPLOYMENT,
    messages=[{"role": "user", "content": "ping"}],
    max_tokens=5,
) as _s:
    _s.get_final_message()
It points straight at Foundry, bypassing the proxy entirely, and uses client.messages.stream(...) (SSE). Note WORKSPACE is a hardcoded absolute path to a different checkout — this script is not repo-relative.

To route it through the proxy, the only change needed is base_url="http://127.0.0.1:8787" (with ANTHROPIC_TARGET_API_URL set to the current ENDPOINT in the proxy's environment — headroom.yaml already defaults to exactly that value, so it works out of the box).

Everything else calls the proxy indirectly (env var, not SDK)
src\shared\tools\agent_runner.py:194–253 — closest thing to a programmatic client. build_child_env(via_proxy) (L194) resolves the proxy URL by shelling out to headroom_config.py --proxy-url (_proxy_url, L233–242) and checks liveness via headroom_tool.py proxy status returncode (_proxy_alive, L245–253). Sets COPILOT_PROVIDER_BASE_URL to the proxy and ANTHROPIC_TARGET_API_URL to FOUNDRY_ENDPOINT (L221–229). Unlike the .bat, it hard-fails rather than degrading silently when --via-proxy is requested and the proxy is down (L214–218).
copilot-cli-headroom.bat — L52–53 resolve PROXY_URL from headroom_config.py --proxy-url; L58–71 probe with headroom_tool.py proxy status and fall back to the direct endpoint with a warning; L74–83 set COPILOT_PROVIDER_* + ANTHROPIC_TARGET_API_URL. Uses the venv python explicitly (L44–45) because a bare python was returning errorlevel 1 and silently disabling compression.
.vscode\settings.json:33–37 — injects HEADROOM_HOST/PORT/BACKEND/TELEMETRY and ANTHROPIC_TARGET_API_URL into every integrated terminal, but not COPILOT_PROVIDER_BASE_URL. _copilot_routing in headroom_tool.py:626–646 exists specifically to surface that gap.
.env.example:18–60 — the container/compose env template.
.vscode\mcp.json, podman-compose.yml, Containerfile — also carry ANTHROPIC_TARGET_API_URL.
No repo code (outside vendor/) constructs an anthropic SDK client pointed at the Headroom proxy today. docs\issues\GUIDE-headroom-foundry-endpoint.md sketches integration patterns but uses the OpenAI/AzureOpenAI SDK and HeadroomClient wrapping — it predates the proxy approach and is stale relative to the current .../anthropic Anthropic-compatible endpoint.

Quick reference for pointing a Python anthropic client at the proxy

import subprocess, sys, anthropic
CFG = r"...\src\shared\tools\headroom\headroom_config.py"
base = subprocess.run([sys.executable, CFG, "--proxy-url"],
                      capture_output=True, text=True).stdout.strip()   # "http://127.0.0.1:8787"

client = anthropic.Anthropic(
    api_key=open(".copilot-key").read().strip(),   # forwarded verbatim as x-api-key
    base_url=base,                                  # NO path suffix needed
    default_headers={"anthropic-version": "2023-06-01"},
)
Proxy env must carry ANTHROPIC_TARGET_API_URL=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic (already the headroom.yaml default). Streaming works. Consider HEADROOM_NO_CCR=1 if you want unbuffered SSE.

Bash List registry tests
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && grep -n "def test_\|orchestrator_of\|import" tests/tools/test_agent_registry.py | head -40

OUT
7:from __future__ import annotations
9:import importlib.util
10:import re
11:import sys
12:from pathlib import Path
14:import pytest
20:import agent_registry as reg  # noqa: E402
24:    spec = importlib.util.spec_from_file_location(name, path)
25:    module = importlib.util.module_from_spec(spec)
32:def test_varredura_encontra_a_esteira_inteira():
38:def test_nenhuma_fase_indefinida():
44:def test_sub_skills_nao_sao_despachaveis():
53:def test_fases_seguem_a_constituicao_v140():
66:def test_frontmatter_parseado_com_e_sem_aspas():
74:def test_catalogo_exclui_depreciados():
86:def test_catalogo_nao_tem_entradas_sinteticas():
94:def test_catalogo_ordenado_por_fase():
101:def test_catalog_or_cai_para_o_fallback(monkeypatch):
108:def test_sem_ids_duplicados_vivos():
115:def test_ambos_os_catalogos_derivam_do_registry():
125:def test_f8_reconhecido_pelo_observer():
134:def test_esteira_sem_violacoes():
144:def test_orquestradores_consolidam_a_economia():
156:def test_agentes_comuns_nao_reportam_metrics_a_mao():
Bash Inspect agent registry JSON
IN
python src/shared/tools/agent_registry.py --json 2>&1 | python -c "
import json,sys,collections
d=json.load(sys.stdin)
print(type(d), len(d))
if isinstance(d,list):
    print(json.dumps(d[0], ensure_ascii=False, indent=2))
    c=collections.Counter(e.get('phase') for e in d)
    print(dict(sorted(c.items(), key=lambda x:str(x[0]))))
"

OUT
<class 'list'> 107
{
  "agent": "ava-asis-bridge-fastqa",
  "version": "4.1.0",
  "phase": "F1",
  "module": "asis-diagnostic",
  "path": "src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md",
  "dispatchable": true,
  "deprecated": false,
  "stub": false,
  "orchestrator": false,
  "has_track": true,
  "track_agent": "ava-asis-bridge-fastqa",
  "track_phase": "F1",
  "track_version": "4.1.0",
  "tools": [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash"
  ],
  "tools_raw": "Read, Write, Edit, Glob, Grep, Bash",
  "batch_write": true,
  "output_contract": true
}
{'': 1, 'F1': 28, 'F2': 22, 'F3': 1, 'F4': 13, 'F5': 14, 'F6': 15, 'F7': 10, 'F8': 3}
Bash Resolve orchestrator per phase
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && for p in F1 F2 F3 F4 F5 F6 F7 F8; do echo -n "$p -> "; python src/shared/tools/agent_registry.py --orchestrator $p 2>&1; done

OUT
Exit code 1
F1 -> ava-asis-orchestrator
F2 -> ava-tobe-orchestrator
F3 -> sem orquestrador registrado para a fase F3
F4 -> ava-stack-orchestrator
F5 -> ava-qa-orchestrator
F6 -> ava-devops-orchestrator
F7 -> sem orquestrador registrado para a fase F7
F8 -> sem orquestrador registrado para a fase F8
Bash Show headroom_config CLI help and proxy url
IN
src/shared/tools/headroom/.venv/Scripts/python.exe src/shared/tools/headroom/headroom_config.py --help 2>&1 | head -30; echo "=== proxy-url ==="; src/shared/tools/headroom/.venv/Scripts/python.exe src/shared/tools/headroom/headroom_config.py --proxy-url 2>&1 | head -3

OUT
usage: headroom_config.py [-h] [-p PROJECT] [--env] [--proxy-url]

Mostra a configuração efetiva da tool Headroom

options:
  -h, --help            show this help message and exit
  -p, --project PROJECT
                        Projeto para aplicar o bloco headroom: do project-
                        config.yaml
  --env                 Emite só as variáveis de ambiente do proxy (consumido
                        por run_standalone.*)
  --proxy-url           Emite só a URL do proxy, sem JSON (consumido por
                        copilot-cli-headroom.bat)
=== proxy-url ===
http://127.0.0.1:8787
Bash Check headroom proxy status
IN
src/shared/tools/headroom/.venv/Scripts/python.exe src/shared/tools/headroom/headroom_tool.py proxy status 2>&1 | head -10; echo "exit=$?"

OUT
🟢 proxy 127.0.0.1:8787 no ar → https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
exit=0
Bash Sample --agent JSON record
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && python src/shared/tools/agent_registry.py --agent ava-asis-orchestrator 2>&1

OUT
{
  "agent": "ava-asis-orchestrator",
  "version": "2.22.0",
  "phase": "F1",
  "module": "asis-diagnostic",
  "path": "src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md",
  "dispatchable": true,
  "deprecated": false,
  "stub": false,
  "orchestrator": true,
  "has_track": true,
  "track_agent": "ava-asis-orchestrator",
  "track_phase": "F1",
  "track_version": "2.22.0",
  "tools": [
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "TodoWrite"
  ],
  "tools_raw": "Read, Write, Edit, Bash, Glob, Grep, TodoWrite",
  "batch_write": true,
  "output_contract": true
}
Já tenho um quadro claro. Vou confirmar as decisões de arquitetura antes de fechar o plano.

AskUserQuestion
OUT
Your questions have been answered: "Qual motor de execução o CLI deve usar para rodar os agentes?"="Híbrido: SDK + copilot -p (Recomendado)", "Como o Headroom deve entrar no CLI?"="Default ligado, degrada com aviso (Recomendado)", "Onde fica a configuração centralizada (modelo, endpoint, URLs)?"="Novo ava-pipeline.yaml + precedência (Recomendado)", "O mapa de fases (F1..F8) do pipeline_runner.py está invertido em relação ao catálogo canônico — F5 é QA e F6 é DevOps no agent_registry, mas o script tem o contrário. Como tratar?"="Derivar tudo do agent_registry (Recomendado)". You can now continue with these answers in mind.
Bash Template project-config head
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && sed -n '1,45p' projects/_template/context/project-config.yaml

OUT

# project-config.yaml — Template para novo projeto AVA Fabric

# Copie este arquivo para projects//context/project-config.yaml

# e preencha os valores antes de iniciar a esteira.

project_name: ""                        # Ex: "Meu-ERP", "Projeto-X"
repository_path: ""                     # Caminho absoluto do repo legado
legacy_technology: "delphi"             # delphi | dotnet | java | cobol | vb6 | vbnet | powerbuilder

# ─── AST Analyzers ─────────────────────────────────────────────────────────

# Mapeia o analisador AST de cada linguagem legada suportada.

# Se omitido, os utilitários tentam resolver via variáveis de ambiente ou

# repositórios irmãos (fallback). A chave `ava_ast_analyzer_path` continua

# disponível para compatibilidade legada (Delphi apenas).

ava_ast_analyzers:
  delphi: ""
  dotnet: ""
  java: ""
ava_ast_analyzer_path: ""          # DEPRECATED: mantido apenas para compatibilidade legada Delphi
trace_id: ""                            # Gerado automaticamente pelo orchestrator
scope_modules: "all"                    # "all" ou lista: ["financeiro", "cadastro"]
module_partitioner_resolution: null     # Optional: Override resolução Leiden (ex: 1.5). Omitir para auto-tune.
module_override_file: ""                # Optional: Caminho para module-override.json (bypassa detecção auto)

# ── SQL IR & MER Generation ───────────────────────────────────────────────

sql_ir_generator:
  enabled: true                       # false = pula geração do sql-ir.json
  infer_relationships: true           # inferir FKs por convenção de nome
  include_external_refs: true         # incluir referências a entidades fora do escopo
  min_confidence: "medium"            # low | medium | high — filtro de confiança para inferências

# ─────────────────────────────────────────────────────────────────────────────

# Modernização Parcial (Strangler Fig Pattern)

# Controla se o pipeline moderniza todos os BCs ou apenas um subconjunto.

# ─────────────────────────────────────────────────────────────────────────────

# modernization_scope: Escopo da modernização.

# "full"    → Pipeline completo F1→F2→F3→F5→F7→F6 (padrão).

# Todos os bounded contexts em scope_modules são processados.

# "partial" → Modernização incremental via Strangler Fig pattern.

# Apenas os BCs em target_modules são migrados.

# Ativa: coexistence-strategy ANTES de F2 (passo 0.5).

modernization_scope: "full"

# target_modules: Lista de BCs a modernizar (usado quando modernization_scope = "partial").

# Formato: lista YAML de strings com os IDs dos BCs (devem estar em scope_modules).

Bash pipeline_runner arg handling
IN
cd "c:/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents" && grep -n "sys.argv\|PROJECT\|input(\|def main" pipeline_runner.py | head -30

OUT
352:        resp = input(f"\n  {BOLD}Executar? [S]im / [P]ular / [V]er skill / [A]bortar: {RESET}").strip().upper()
444:def main():
459:    raw = input(f"\n{BOLD}Selecione o projeto [número ou nome]: {RESET}").strip()
463:            project = input("  Nome do projeto: ").strip()
478:    mode_raw = input(f"\n{BOLD}Escolha [1/2]: {RESET}").strip()
484:    auto_raw = input(f"\n{BOLD}Escolha [1/2]: {RESET}").strip()
496:        sel_raw = input(f"\n{BOLD}Números das fases (ex: 1 2 3): {RESET}").strip()
577:                    retry = input("  Tentar novamente? [S/N]: ").strip().upper()

1. src/shared/tools/agent_registry.py
   Path: c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\agent_registry.py (464 lines)

Data source — filesystem scan, NOT a YAML
Lines 53‑55, 187:

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
AGENTS_ROOT  = PROJECT_ROOT / "src" / "modules" / "ava-fabric-agents"
...
for path in sorted(AGENTS_ROOT.glob("*/agents/**/*.md")):
It globs src/modules/ava-fabric-agents/*/agents/**/*.md, parses the YAML frontmatter with regexes (no pyyaml dependency) — _FRONTMATTER_RE, _NAME_RE, _VERSION_RE, _ALLOWED_TOOLS_RE (lines 95‑98) — and derives phase from the directory name (the module). module.yaml files are explicitly NOT read (see module docstring lines 11‑18: "O module.yaml da raiz ficou com a numeração pré‑1.4.0 nos comentários e não é autoridade").

Phase → module map (lines 60‑83)

PHASE_BY_MODULE: dict[str, str] = {
    "asis-diagnostic": "F1",   "tobe-architecture": "F2",
    "prototype": "F3",         "tech-stack": "F4",
    "qa-agents": "F5",         "devops-agents": "F6",
    "deliverables": "F7",      "summary": "F8",
    "master-orchestrator": "",     # "" = transversal
}
PHASE_ORDER = ["F1".."F8"]
PHASE_NAMES = {"F1":"AS-IS Diagnostic","F2":"TO-BE Architecture","F3":"Prototype",
               "F4":"Stack / Codegen","F5":"QA","F6":"DevOps",
               "F7":"Deliverables","F8":"Summary"}
Orchestrators (lines 86‑93) — a hardcoded set of 6

PHASE_ORCHESTRATORS = {
    "ava-master-orchestrator", "ava-asis-orchestrator", "ava-tobe-orchestrator",
    "ava-stack-orchestrator",  "ava-qa-orchestrator",   "ava-devops-orchestrator",
}
orchestrator_of(phase) (lines 334‑349) resolves phase→orchestrator by intersecting this set with the scanned records. Verified live output:

F1 -> ava-asis-orchestrator      F5 -> ava-qa-orchestrator
F2 -> ava-tobe-orchestrator      F6 -> ava-devops-orchestrator
F3 -> (none, exit 1)             F7 -> (none, exit 1)
F4 -> ava-stack-orchestrator     F8 -> (none, exit 1)
F3/F7/F8 have no orchestrator (docstring line 340 says so explicitly).

Record shape (lines 199‑217) — per agent .md
agent, version, phase, module, path, dispatchable, deprecated, stub, orchestrator, has_track, track_agent, track_phase, track_version, tools, tools_raw, batch_write, output_contract

Live example (--agent ava-asis-orchestrator):

{ "agent":"ava-asis-orchestrator", "version":"2.22.0", "phase":"F1",
  "module":"asis-diagnostic",
  "path":"src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md",
  "dispatchable":true, "orchestrator":true, "has_track":true,
  "tools":["Read","Write","Edit","Bash","Glob","Grep","TodoWrite"], ... }
Public/importable API (documented at lines 31‑37)
Function	Line	Purpose
load(refresh=False)	223	All records, memoized in _CACHE (line 113)
get(agent_id)	231	Single record, prefers non-deprecated
duplicates()	242	{agent_id: [paths]} for live-duplicated ids
catalog()	258	[{"agent","phase","version"}] — dispatchable, no deprecated, sorted by phase then id
validate()	282	Rules AT-001 (space-separated allowed-tools), AT-002 (BatchWriteProtocol without Bash), AT-003 (## Output Contract without Write/Bash)
orchestrator_of(phase)	334	"F1" → ava-asis-orchestrator, else None
catalog_or(fallback)	352	Never-throws wrapper used by observer tools
Constants	60‑93	PHASE_BY_MODULE, PHASE_ORDER, PHASE_NAMES, PHASE_ORCHESTRATORS
Full CLI (lines 367‑456)

--json              # all records as JSON
--catalog           # AGENT_CATALOG-format JSON
--agent AGENT_ID    # single record JSON; exit 1 if not found
--orchestrator FASE # prints orchestrator id for phase; exit 1 if none
--validate          # exit 1 + AT-001/2/3 report on stderr
(no flags)          # human-readable table grouped by phase, flags "T/O/D/S"
Notable: UTF‑8 reconfigure at lines 49‑51 and again at 460‑462 (Windows). argparse.RawDescriptionHelpFormatter + epilog with examples.

Live totals: 107 arquivos (103 despacháveis) — F1:24, F2:22, F3:1, F4:13, F5:14, F6:15, F7:10, F8:3, transversal:1.

Consumers of agent_registry
src/shared/tools/agent_runner.py:74, 164, 178, 474
src/shared/tools/generate_agent_wrappers.py:60, 393, 397
src/shared/tools/pipeline_observer.py, src/shared/tools/generate_observability_report.py, src/shared/utils/verify_agent_observability.py
copilot-cli-headroom.bat:154 (shells out to --orchestrator %~1)
Tests: tests/tools/test_agent_registry.py, tests/tools/test_agent_wrappers.py
2. Canonical source of truth for phase → agent
There is no registry YAML/JSON for phase→agent. The chain is:

Constitution — .specify/memory/constitution.md § Project Reference (amendment v1.4.0) is declared the authority for phase numbering (agent_registry.py:11-18).
Executable source of truth — agent_registry.py PHASE_BY_MODULE + directory layout. Root module.yaml:11-12 defers to it explicitly:

# Fonte executável desta tabela: src/shared/tools/agent_registry.py (PHASE_BY_MODULE).

Per-module rosters — src/modules/ava-fabric-agents/<module></module>/module.yaml (agents: list with id/file/skill/status/routing_key). These are descriptive; the registry does not read them.
Execution DAG (F1 only) — src/shared/data/pipeline-dag/F1.yaml, consumed by agent_runner.py:145. Its own header (lines 3, 10‑16) calls itself "FONTE DE VERDADE do despacho de F1" but flags RISCO R1 — quarta fonte de verdade, and the runner cross-validates every id against artifact_gate.ARTIFACT_CONTRACTS and agent_registry.catalog() (agent_runner.py:160-178).
src/shared/data/pipeline-dag/ contains only F1.yaml — F2..F8 have no DAG file.

F1.yaml structure (excerpt, lines 21‑72)

version: 1
phase: F1
module: asis-diagnostic
orchestrator: ava-asis-orchestrator
max_parallel: 1
defaults:
  timeout_s: 900
  max_attempts: 1
  model: claude-sonnet-4     # nunca 'auto' — R4: subagentes caíam em gpt-5.4 e davam 404
waves:

- id: wave1
  blocking: true
  implemented: false
  agents:
  - id: "ava-asis-solution-{legacy_technology}"   # resolvido em runtime
    slice: all
    timeout_s: 3600
    max_ai_credits: 80
    large_artifact_protocol: true
- id: wave2
  depends_on: [wave1]
  implemented: true
  agents:
  - id: ava-asis-inventory
    slice: [08_code_overview, 02_form_business_rules]
    timeout_s: 900
    max_ai_credits: 30
  - id: ava-asis-db-analyzer
    slice: [03_database_rules, 04_database_schemas, 05_procedures]
    timeout_s: 1800
  - id: ava-asis-events-pubsub
    slice: [06_integrations]
    timeout_s: 600
    Triggers (FP, SD, DP, TPT, SG, DE, SAS, SV) — NOT registered canonically
    No YAML/JSON anywhere declares them. They live in exactly three kinds of places:

(a) Hardcoded Python list — pipeline_runner.py:54-110 (the only machine-readable phase→agent→trigger table in the repo):

PIPELINE = [
  {"phase":"F1",  "label":"AS-IS Diagnostic — Full Pipeline", "agent":"ava-asis-orchestrator",   "trigger":"FP"},
  {"phase":"F1a", ... "agent":"ava-asis-inventory",           "trigger":None},
  {"phase":"F1b", ... "agent":"ava-asis-solution-delphi",     "trigger":None},
  {"phase":"F1c", ... "agent":"ava-asis-db-analyzer",         "trigger":None},
  {"phase":"F1d", ... "agent":"ava-asis-documentation",       "trigger":None},
  {"phase":"F1e", ... "agent":"ava-asis-security-review",     "trigger":None},
  {"phase":"F1f", ... "agent":"ava-asis-gaps-risks",          "trigger":None},
  {"phase":"F2a", ... "agent":"ava-tobe-orchestrator",        "trigger":"SD"},
  {"phase":"F2b", ... "agent":"ava-devops-orchestrator",      "trigger":"DP"},
  {"phase":"F2c", ... "agent":"ava-qa-orchestrator",          "trigger":"TPT"},
  {"phase":"F3",  ... "agent":"ava-prototype",                "trigger":None},
  {"phase":"F4",  ... "agent":"ava-stack-orchestrator",       "trigger":"SG"},
  {"phase":"F5",  ... "agent":"ava-devops-orchestrator",      "trigger":"DE"},
  {"phase":"F6",  ... "agent":"ava-qa-orchestrator",          "trigger":"TPT"},
  {"phase":"S1",  ... "agent":"ava-summary",                  "trigger":"SAS"},
  {"phase":"S2",  ... "agent":"ava-summary-remediation",      "trigger":None},
  {"phase":"S3",  ... "agent":"ava-summary",                  "trigger":"SV"},
  {"phase":"S4",  ... "agent":"ava-summary",                  "trigger":"SAS"},
]
Note this list's phase numbering disagrees with the constitution/registry (here F5=DevOps Execute, F6=QA Test Execution — inverted vs PHASE_BY_MODULE F5=qa-agents, F6=devops-agents).

(b) Markdown tables inside each orchestrator spec (prose, not parseable canon):

master-orchestrator/agents/master-orchestrator.md:169,171,175,179,224 — | F2 | ... trigger: \SD` — bloqueante |, | FP | full-pipeline | ... |`
asis-diagnostic/agents/orchestrator-asis.md:1428 — | \FP` | full-pipeline | ... |`
tobe-architecture/agents/orchestrator-tobe.md:1625 — | \SD` | Start TO-BE design ... |`
devops-agents/agents/orchestrator-devops.md:59-60 — DP / DE
qa-agents/agents/qa-orchestrator-agent.md:52 — TPT
tech-stack/agents/orchestrator-stack.md:781 — | \SG` | Start full stack generation |`
summary/agents/summary-agent.md:321 — | \SAS` | summary-asis-only | ... | (alsoGS, STO, SI, UP` at line 24)
(c) Docs — docs/agents-catalog.md:93 (FP, SR, RS) and :1316 (SI/SAS/STOBE/SFull). Doc header says "Total de agentes: 53" — stale vs the registry's 103.

The frontmatter field that is structured is description: with Ativa com: "..." natural-language phrases (e.g. master-orchestrator.md:12, devops-agents/agents/orchestrator-devops.md:19), consumed by generate_agent_wrappers.py:200 — but those are NL phrases, not the short codes.

Conclusion: the short trigger codes are hardcoded in pipeline_runner.py and duplicated in prose. Adding a canonical triggers registry would be net-new.

3. src/modules/ava-fabric-agents/ layout

src/modules/ava-fabric-agents/
├── asis-diagnostic/     module.yaml  agents/ checklists/ shared/ templates/ utils/ workflows/
├── tobe-architecture/   module.yaml  agents/ checklists/ templates/ utils/ workflows/
├── prototype/           module.yaml  agents/
├── tech-stack/          module.yaml  agents/ templates/
├── qa-agents/           module.yaml  agents/
├── devops-agents/       module.yaml  agents/ templates/
├── deliverables/        module.yaml  agents/
├── summary/             module.yaml  agents/ data/ templates/ utils/ workflows/
├── master-orchestrator/ (NO module.yaml)  agents/
└── shared/              (NO module.yaml)  templates/   ← no agents/, not scanned
Module	agents/*.md (top level)	module.yaml	Registry phase
asis-diagnostic	15 (+ subdirs security/, db-analyzer/ → 49 total incl. skills)	yes	F1
tobe-architecture	22	yes	F2
prototype	1	yes	F3
tech-stack	13	yes	F4
qa-agents	14	yes	F5
devops-agents	15	yes	F6
deliverables	10	yes	F7
summary	3	yes	F8
master-orchestrator	1	no	"" (transversal)
shared	—	no	n/a
Naming conventions
File names are role-descriptive kebab-case, not the agent id: orchestrator-asis.md, solution-delphi.md, coder-dotnet-backend.md, db-analyzer/db-analyzer.md.
Agent ids (frontmatter name:) are ava-<phase-prefix></phase>-<role></role>: ava-asis-orchestrator, ava-tobe-migration-plan, ava-stack-react-frontend, ava-qa-exploratory, ava-devops-iac-azure, ava-deliverable-packager, ava-summary.
Sub-skills live at agents/<parent></parent>/skills/*.md and are excluded from dispatch by _is_dispatchable (agent_registry.py:169-176) — e.g. asis-diagnostic/agents/db-analyzer/skills/{mysql,mariadb,oracle,sqlserver}-agent.md.
Security sub-agents are a nested folder that IS dispatchable: asis-diagnostic/agents/security/*.md.
Sample module.yaml — src/modules/ava-fabric-agents/tech-stack/module.yaml

name: tech-stack
display_name: "Stack Tecnológica"
version: "1.5.0"
description: "Agentes de geração de código. Stack resolvida em runtime de
  tobe_stack.backend_framework e tobe_stack.frontend_framework em ConfigStack.yaml..."
agents:

- id: ava-stack-orchestrator
  file: agents/orchestrator-stack.md
- id: ava-stack-dotnet-backend
  file: agents/coder-dotnet-backend.md
  routing_key: "dotnet"
- id: ava-stack-node-backend
  file: agents/coder-node-backend.md
  routing_key: "nestjs"
  status: stub
  build_cycle_templates:
- id: ava-build-cycle-dotnet-scaffold
  file: templates/build-cycle-dotnet-scaffold-agent.md
  routing_key: "pipeline_mode == 'build-cycle' AND backend_framework == 'dotnet'"
  sequence: 1
  asis-diagnostic/module.yaml adds two more shapes — skill: (skill id) and nested skills: lists, plus a large outputs: block:
- id: ava-asis-db-analyzer
  file: agents/db-analyzer/db-analyzer.md
  skill: ava-asis-db-analyzer
  skills:

  - id: mysql-agent
    file: agents/db-analyzer/skills/mysql-agent.md
    outputs:
    base_path: "projects/{project_name}/outputs/asis"
    artifacts:
  - master-report.md
  - diagrams/c4-context.mmd
  - db/schema-inventory.md
    ...
    Root module.yaml (repo root)

name: ava-fabric-agents
version: "1.0.0"
bmad_version: ">=6.0.0"

# Fonte executável desta tabela: src/shared/tools/agent_registry.py (PHASE_BY_MODULE).

modules:

- asis-diagnostic     # F1: 21 agentes
- tobe-architecture   # F2: 22 agentes
- prototype           # F3: 1 agente
- tech-stack          # F4: 13 agentes
- qa-agents           # F5: 14 agentes
- devops-agents       # F6: 15 agentes
- deliverables        # F7: 10 agentes
- summary             # F8: 3 agentes
  shared:
  templates: src/shared/templates
  data: src/shared/data
  schemas: src/shared/schemas
  checklists: src/shared/checklists

4. src/shared/tools/generate_agent_wrappers.py
   Path: ...\src\shared\tools\generate_agent_wrappers.py (500 lines)

What it does: derives .github/agents/<agent-id></agent>.agent.md GitHub Copilot CLI custom-agent wrappers from agent_registry.catalog(). Currently 112 files in .github/agents/ (includes ~10 Spec Kit agents that are not ava-*).

Key mechanics:

Line 60: import agent_registry after sys.path.insert(0, str(SCRIPT_DIR)).
Lines 62‑64: AGENTS_MD = REPO_ROOT/"AGENTS.md", OUT_DIR = REPO_ROOT/".github"/"agents", USER_AGENTS_DIR = Path.home()/".copilot"/"agents".
Line 67: BODY_CHAR_CAP = 30_000 — hard fail, never truncate.
Lines 70‑71: extracts the  …  block from AGENTS.md (read_agents_core(), 117‑135) and inlines it into every wrapper, because the runner uses --no-custom-instructions.
Lines 75‑100: TOOL_NAME_MAP — spec tool names → Copilot CLI names: Read→view, Write→create, Edit→edit, Glob→glob, Grep→grep, Bash→powershell, WebFetch→web_fetch, WebSearch→web_search, Run→powershell, fetch_webpage→web_fetch; dropped to "": github_text_search, TodoWrite, Task, NotebookEdit.
Line 104: DEFAULT_TOOLS = ["view","glob","grep"] (read-only fallback).
Line 108: DEFAULT_MODEL = "claude-sonnet-4" — pinned; unpinned falls to gpt-5.4 → 404 on BYOK.
Lines 177‑211: _LEAD_CHAR_CAP=260 / _TRIGGER_CHAR_CAP=220; _condense_description preserves the Ativa com: "..." clause.
Lines 226‑251: optional import of context_budget.AGENT_ARTIFACT_SLICE and artifact_gate.ARTIFACT_CONTRACTS from asis-diagnostic/utils, used to emit an "Estratégia de contexto" section.
Lines 361‑381: preflight() — fails exit 2 if ~/.copilot/agents/ shadows any project agent name.
--check semantics (lines 436‑453, 477‑489)
check() returns three problem classes, comparing disk to the freshly-rendered content:

if not target.is_file():                                  → "ausente: <path></path>"
elif target.read_text(...) != content:                    → "divergente: <path></path>"
for path in OUT_DIR.glob("ava-*.agent.md") not expected:  → "órfão: <path></path>"
--check writes nothing and skips preflight(). Exit 0 with ✅ N wrapper(s) em dia com o registry, or exit 1 listing problems + the remediation command. Exit code contract in the docstring (line 42): 0 OK · 1 drift/erro de geração · 2 erro de uso ou preflight.

Other flags: --phase F1..F8 (filters via entry["phase"] != phase, line 395), --dry-run (computes + reports but write_all(..., dry_run=True) skips the write, lines 420‑433).

Consumed by copilot-cli-headroom.bat:118:

python "%~dp0src\shared\tools\generate_agent_wrappers.py" --check >nul 2>&1
if errorlevel 1 goto :agents_drift
and line 154 uses the registry for phase startup:

for /f "usebackq delims=" %%A in (`python "%~dp0src\shared\tools\agent_registry.py" --orchestrator %~1 2^>nul`) do set "START_AGENT=%%A"
5. Projects folder structure

projects/
├── _template/
│   ├── .gitkeep
│   └── context/
│       ├── project-config.yaml
│       ├── .project-config-exemple-.yaml
│       └── shared-context.md
├── Meu-ERP/
│   └── context/project-config.yaml        ← only context/, no outputs/
└── MeuERP-002/
    ├── context/{project-config.yaml, shared-context.md}
    └── outputs/
        ├── asis/            (api-map.md, architecture-blueprint.md, master-report.md,
        │                     metrics.json, risk-register.json, gap-register.json, ...)
        ├── tobe/            (coding-standards.md, nuget-packages.md, solution-structure.md,
        │                     value-chain-mapping.md)
        ├── observability/   (agent-events.jsonl, headroom-metrics.jsonl, pipeline-run-state.json)
        └── summary/         (AVA-FABRIC-SUMMARY-MeuERP-002-2026-08-03.html, index.md)
(A second, non-repo root also exists: C:\Desenv\factory_apps\ava-fabric-apps-agents\projects\ with Meu-ERP, awesome-delphi, example-vcl-login, database-comparer-examples — same context/project-config.yaml convention, plus one context/agent-task-config.yaml.)

Sample — projects/Meu-ERP/context/project-config.yaml (45 lines, the minimal shape)

project_name: "MEU-ERP"
repository_path: "C://_git//Examples//Meu-ERP"
legacy_technology: "delphi"
trace_id: "test-pbi366-agent-fix-verification"
scope_modules: "all"
client_name: "Avanade"
pm_name: "Test PM"
tech_lead_name: "Test TL"
language: "pt"
pipeline_mode: "generic"

tobe_stack:
  backend_framework: "dotnet"
  backend_version: "8.0"
  frontend_framework: "angular"
  frontend_version: "17"
  persistence: {type: "sqlserver", orm: "entity-framework-core", micro_orm: "dapper"}
  auth: {provider: "azure-ad", library: "microsoft-identity-web"}
  architecture_patterns: {cqrs: true, mediator: "mediatr", clean_architecture: true}
  observability: {provider: "azure-application-insights", logging: "serilog", tracing: "opentelemetry"}
  infrastructure: {cloud: "azure", hosting: "azure-app-service"}

quality_gates:
  coverage_minimum: 80
  build_warnings_as_errors: true

outputs_base_path: "projects/{project_name}/outputs"
context_base_path:  "projects/{project_name}/context"
inputs_base_path:   "projects/{project_name}/inputs"
projects/MeuERP-002/context/project-config.yaml — the full 367-line shape
Top-level keys, in order:
project_name, repository_path, ava_ast_analyzer_path, legacy_technology (delphi|cobol|vb6|vbnet|powerbuilder), trace_id, client_name, pm_name, tech_lead_name, language (pt|en), pipeline_mode (build-cycle|generic), context_budget_inline_threshold (400000), context_budget_bc_scoped_threshold (700000), sql_ir_generator, reference_architecture_file, architecture_backlog_file, overrides, copyright, copyright_suffix, outputs_base_path/context_base_path/inputs_base_path, context_stack_base_path (DEPRECATED), tobe_stack, build_runner, cloud_provider, architecture_patterns, solution_layers, persistence, auth, observability, infrastructure, quality_gates (declared twice — lines 226 and 332; the second wins in YAML), security_enabled_asis, timing_benchmark_enabled, signoffs, wave_approval.

There is no model: key and no phases: key in project-config.yaml. Model pinning lives in code: pipeline-dag/F1.yaml:32 (model: claude-sonnet-4), generate_agent_wrappers.py:108 (DEFAULT_MODEL), pipeline_runner.py:44 (DEPLOYMENT = "claude-sonnet-4-6"), copilot-cli-headroom.bat:25,77.

_template/context/project-config.yaml additionally documents ava_ast_analyzers: {delphi, dotnet, java}, module_partitioner_resolution, module_override_file, modernization_scope (full|partial) and target_modules (Strangler Fig).

6. Python CLI style/pattern references
   The repo is stdlib-only by convention — src/shared/tools/headroom/requirements.txt states it verbatim:

# NÃO instalar no venv principal do repo — o repo é stdlib-only por convenção (invariante IV7).

click / typer
Not used anywhere in first-party code. All hits are inside the vendored third-party subtree src/shared/tools/headroom/vendor/ (headroom-ai 0.33.0, a git subtree). Everything first-party uses argparse.

requirements.txt / pyproject.toml
There is no root requirements.txt and no root pyproject.toml. Existing manifests:

Path	Content
src/shared/tools/headroom/requirements.txt	headroom-ai[proxy,mcp,ml,code,memory,otel]==0.33.0, pyyaml>=6.0, pytest>=8.0 — isolated venv at src/shared/tools/headroom/.venv
src/shared/tools/headroom/vendor/pyproject.toml	vendored (maturin backend)
src/shared/tools/headroom/vendor/plugins/headroom-oauth2/pyproject.toml	vendored plugin
fastqa/template/web/playwright/python/qa-test-automation/requirements.txt	generated-project template
fastqa/template/web/robot/python/requirements.txt	generated-project template
De-facto third-party deps in first-party code: pyyaml (defensive try: import yaml in agent_runner.py:69, headroom_config.py:38, qa_preflight.py:29, verify_scaffold.py:77; hard import in render_sql_strategy.py:32), and anthropic + requests in pipeline_runner.py:14,16.

argparse CLIs worth copying (47 files use argparse; best exemplars)
src/shared/tools/agent_registry.py:367-456 — flat flags, RawDescriptionHelpFormatter + epilog examples, UTF‑8 reconfigure, exit 1 on validate/not-found. Best small-CLI template in the repo.
src/shared/tools/pipeline_observer.py:1105-1178 — the only subcommand CLI (add_subparsers(dest="command", required=True)) with init | track | finalize | dashboard | status | report | import-json | compare, global --project/-p, choices=/type=int on options. Best subcommand template.
src/shared/tools/agent_runner.py:676-685 — --project (required), --phase F1..F8, --wave, --agent, --dry-run, --via-proxy, --json; rigorous docstring with an explicit exit-code table (0 ok · 1 falha de nó · 2 erro de configuração, lines 40‑44).
src/shared/tools/generate_agent_wrappers.py:458-495 — the --check / --dry-run / --phase CI pattern with documented exit codes.
src/shared/checks/cli.py (45 lines) — python -m src.shared.checks package entry (__main__.py present), --project required, --suite with a long choices=[...], --verbose, sys.exit(0 if ok else 1). Cleanest minimal example.
Others: src/shared/tools/check_session_health.py, src/shared/tools/generate_observability_report.py, src/shared/utils/verify_agent_observability.py, src/shared/utils/qa_test_runner.py, src/shared/utils/build_runner.py, src/shared/tools/headroom/headroom_tool.py.
Anti-pattern to avoid: pipeline_runner.py (repo root) takes no CLI args at all — it's fully interactive (input() at lines 352, 459, 463, 478, 484, 496, 577) and monkeypatches socket.getaddrinfo (lines 25‑36). Yet it holds the only structured trigger table.

Repo-wide CLI conventions observed
#!/usr/bin/env python3 + from __future__ import annotations
Windows UTF‑8 guard: if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
Path anchoring: REPO_ROOT = Path(__file__).resolve().parents[3] (or .parent.parent.parent)
sys.path.insert(0, ...) + bare import agent_registry for cross-tool imports (no package installs)
Emoji status prefixes on stdout (✅/❌/⚠️), errors to stderr, sys.exit(1) / raise SystemExit(2)
Portuguese docstrings/help text with a "Por que isto existe" rationale section
Tenho o quadro completo. Vou escrever o plano.

Write C:\Users\r.b.almeida\.claude\plans\analise-o-escript-a-iterative-lightning.md
256 lines
Análise concluída e plano escrito. Resumo do que encontrei:

Como o script funciona hoje — pipeline_runner.py é interativo puro (zero argumentos): patcha DNS via socket.getaddrinfo, lê menus com input(), e para cada um dos 18 passos hardcoded em pipeline_runner.py:54-110 monta um system prompt que proíbe tools e exige blocos , chama client.messages.stream() direto no Foundry, e extrai os arquivos da resposta por regex.

Dependências — Python 3.13.3 ✔, anthropic 0.116.0 ✔, VPN obrigatória, .copilot-key. Dois bloqueadores: WORKSPACE aponta para outro checkout (c:\_info\Projetos\Hub\...), e requests é importado mas nunca usado.

Headroom como proxy — a adaptação é literalmente uma linha. O proxy registra POST /v1/messages, encaminha o header de auth verbatim e faz passthrough de SSE; basta base_url="http://127.0.0.1:8787" sem sufixo de path. Os 404 documentados no --via-proxy do agent_runner.py vêm de /v1/models/{id}, rota que só o Copilot CLI chama — o SDK Anthropic não toca nela. O proxy está no ar agora e o ANTHROPIC_TARGET_API_URL já tem o valor certo por default.

Três achados que mudam o plano:

Mapa de fases invertido — o script tem F5=DevOps/F6=QA; o canônico (confirmado rodando agent_registry.py --orchestrator) é F5=QA, F6=DevOps, F7=Deliverables, F8=Summary.
Já existe agent_runner.py com --project/--phase/--agent/--via-proxy/--dry-run, gate de artefato e telemetria. O CLI reusa em vez de reimplementar.
load_skill() acha o agente por heurística de substring e escolhe o maior arquivo candidato — pode carregar o agente errado. O agent_registry entrega o path exato dos 107 agentes.
O plano cria ava-pipeline.yaml como fonte única (modelo/endpoint/proxy/triggers, com a mesma precedência do headroom.yaml), deriva fases e agentes do registry, e entrega o CLI com run/list/config/doctor — cobrindo -p, --phase repetível, --all, --model, --agent, mais --engine, --via-proxy/--no-proxy, --dry-run e exit codes.

Duas limitações que deixei explícitas em vez de mascarar: --engine copilot só tem DAG para F1 (só existe F1.yaml), então nas demais fases despacha só o orquestrador — e avisa; e encontrei um provável bug de nomes de campo no headroom_tool.py attribute, ainda não confirmado porque o JSONL do proxy nunca foi escrito neste checkout.

Claude’s Plan C:\Users\r.b.almeida\.claude\plans\analise-o-escript-a-iterative-lightning.md
Stayed in plan mode
Entendido — a ordem da esteira passa a ser declarada explicitamente, não derivada do registry. Dois pontos da sua lista precisam de decisão antes de eu reescrever o plano.

AskUserQuestion
OUT
Your questions have been answered: "Na sua lista, o passo F2 do DevOps veio com o trigger vazio (`@ava-devops-orchestrator || project:`). O script atual usa `DP` (DevOps Plan) nesse ponto, e `DE` (DevOps Execute) na F5. Qual vale?"="DP — DevOps Plan (Recomendado)", "A F2 tem três passos (tobe/devops/qa). Como o `--phase` deve endereçá-los?"="F2 = grupo, com sub-ids opcionais (Recomendado)". You can now continue with these answers in mind.
Decisões registradas. Reescrevendo o plano com a ordem da esteira como fonte declarada.

Write C:\Users\r.b.almeida\.claude\plans\analise-o-escript-a-iterative-lightning.md
295 lines
Plano ajustado. Mudanças principais em relação à versão anterior:

A ordem da esteira virou a fonte de verdade declarada — 12 passos em pipeline.steps: no ava-pipeline.yaml, executados de cima para baixo. O agent_registry deixa de derivar a sequência e passa a servir só para validar que o agente existe/é despachável e para resolver o spec_path exato (o que mata a heurística do load_skill()).

F2 tem três passos (F2a SD → F2b DP → F2c TPT), e --phase F2 roda o grupo enquanto --phase F2b roda só o DevOps Plan. Mesma mecânica no F8 (F8a…F8d). Não há F7 na esteira.

Registrei a divergência de numeração como intencional — na esteira F5 é DevOps Execute e F6 é QA Execution, enquanto no agent_registry F5 é o módulo qa-agents e F6 é devops-agents. O validador do plano não compara step.phase com registry.phase, e isso vai como comentário no YAML e docstring do teste, para ninguém "corrigir" depois achando que é bug.

--agent ava-devops-orchestrator resolve para os dois passos (F2b com DP e F5 com DE), cada um com seu trigger; --phase F5 fixa um só. Um agente fora da esteira (ex.: ava-asis-inventory) roda como passo avulso.

Claude’s Plan C:\Users\r.b.almeida\.claude\plans\analise-o-escript-a-iterative-lightning.md
User approved the plan
Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
I'll read the reference implementations I'm porting from, to match their contracts exactly.

Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\headroom\headroom_config.py
Bash Inspect tests layout
IN
ls tests/ && echo "--- tools ---" && ls tests/tools/ 2>/dev/null | head -20; echo "--- conftest ---"; cat tests/conftest.py 2>/dev/null | head -30

OUT
ava-fabric-agents
tools
utils
--- tools ---
test_agent_registry.py
test_agent_wrappers.py
test_artifact_gate.py
test_headroom_attribution.py
test_headroom_context.py
test_session_health.py
--- conftest ---
Read c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_agent_registry.py
Now I'll write the config YAML — the single source of truth.

Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\data\ava-pipeline.yaml
181 lines
Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\pipeline_config.py
329 lines
Bash Smoke test pipeline_config
IN
python src/shared/tools/pipeline_config.py --model && python src/shared/tools/pipeline_config.py --endpoint && python src/shared/tools/pipeline_config.py --show 2>&1 | head -30

OUT
claude-sonnet-4-6
https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
{
  "foundry": {
    "endpoint": "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic",
    "api_key_file": ".copilot-key",
    "anthropic_version": "2023-06-01",
    "max_tokens": 32768
  },
  "models": {
    "default": "claude-sonnet-4-6",
    "provider_model_id": "claude-sonnet-4",
    "aliases": {
      "sonnet": "claude-sonnet-4-6"
    }
  },
  "proxy": {
    "mode": "auto",
    "url_command": [
      "src/shared/tools/headroom/headroom_config.py",
      "--proxy-url"
    ],
    "status_command": [
      "src/shared/tools/headroom/headroom_tool.py",
      "proxy",
      "status"
    ],
    "prefer_tool_venv": true
  },
  "execution": {
    "engine": "sdk",
    "confirm": "manual",
Config funcionando. Agora o plano da esteira.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\pipeline_plan.py
254 lines
Bash Smoke test pipeline_plan
IN
python src/shared/tools/pipeline_plan.py; echo "exit=$?"; echo "=== F2 ==="; python src/shared/tools/pipeline_plan.py --phase F2; echo "=== agent devops ==="; python src/shared/tools/pipeline_plan.py --agent ava-devops-orchestrator

OUT
Exit code 2
ERRO: nenhum passo declarado em `pipeline.steps` — confira src/shared/data/ava-pipeline.yaml (e se pyyaml está instalado)
exit=2
=== F2 ===
ERRO: nenhum passo declarado em `pipeline.steps` — confira src/shared/data/ava-pipeline.yaml (e se pyyaml está instalado)
=== agent devops ===
ERRO: nenhum passo declarado em `pipeline.steps` — confira src/shared/data/ava-pipeline.yaml (e se pyyaml está instalado)
Bash Parse ava-pipeline.yaml directly
IN
python -c "
import yaml,json
d=yaml.safe_load(open('src/shared/data/ava-pipeline.yaml',encoding='utf-8'))
print(type(d), list(d.keys()) if isinstance(d,dict) else d)
print('steps:', len((d.get('pipeline') or {}).get('steps') or []))
"

OUT
<class 'dict'> ['pipeline']
steps: 12
REPO_ROOT está um nível acima do certo — SCRIPT_DIR já é o diretório, então parents[3] sai do repo. Corrigindo nos dois arquivos.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\pipeline_config.py
Modified
Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\pipeline_plan.py
Added 1 line
Bash Smoke test plan selectors
IN
echo "=== esteira completa ==="; python src/shared/tools/pipeline_plan.py; echo "exit=$?"; echo; echo "=== --phase F2 ==="; python src/shared/tools/pipeline_plan.py --phase F2; echo; echo "=== --phase F2b ==="; python src/shared/tools/pipeline_plan.py --phase F2b; echo; echo "=== --agent ava-devops-orchestrator ==="; python src/shared/tools/pipeline_plan.py --agent ava-devops-orchestrator

OUT
=== esteira completa ===

1. F1   ava-asis-orchestrator    FP   AS-IS Diagnostic — Full Pipeline
2. F2a  ava-tobe-orchestrator    SD   TO-BE Architecture — Solution Design
3. F2b  ava-devops-orchestrator  DP   DevOps Plan
4. F2c  ava-qa-orchestrator      TPT  QA — Test Plan & Strategy
5. F3   ava-prototype            —    Prototype
6. F4   ava-stack-orchestrator   SG   Tech Stack — Stack Generation
7. F5   ava-devops-orchestrator  DE   DevOps Execute
8. F6   ava-qa-orchestrator      TPT  QA — Test Execution
9. F8a  ava-summary              SAS  Summary — Generate
10. F8b  ava-summary-remediation  —    Summary — Remediation
11. F8c  ava-summary              SV   Summary — Validate
12. F8d  ava-summary              SAS  Summary — Final
    exit=0

=== --phase F2 ===

1. F2a  ava-tobe-orchestrator    SD   TO-BE Architecture — Solution Design
2. F2b  ava-devops-orchestrator  DP   DevOps Plan
3. F2c  ava-qa-orchestrator      TPT  QA — Test Plan & Strategy

=== --phase F2b ===

1. F2b  ava-devops-orchestrator  DP  DevOps Plan

=== --agent ava-devops-orchestrator ===

1. F2b  ava-devops-orchestrator  DP  DevOps Plan
2. F5   ava-devops-orchestrator  DE  DevOps Execute
   Esteira completa na ordem exata. Agora o motor SDK.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\sdk_engine.py
330 lines
Agora o CLI.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\ava_pipeline.py
591 lines
Bash Test list --phases
IN
python src/shared/tools/ava_pipeline.py list --phases; echo "exit=$?"

OUT
Ordem da esteira (src/shared/data/ava-pipeline.yaml → pipeline.steps)

1. F1   ava-asis-orchestrator    FP   AS-IS Diagnostic — Full Pipeline
2. F2a  ava-tobe-orchestrator    SD   TO-BE Architecture — Solution Design
3. F2b  ava-devops-orchestrator  DP   DevOps Plan
4. F2c  ava-qa-orchestrator      TPT  QA — Test Plan & Strategy
5. F3   ava-prototype            —    Prototype
6. F4   ava-stack-orchestrator   SG   Tech Stack — Stack Generation
7. F5   ava-devops-orchestrator  DE   DevOps Execute
8. F6   ava-qa-orchestrator      TPT  QA — Test Execution
9. F8a  ava-summary              SAS  Summary — Generate
10. F8b  ava-summary-remediation  —    Summary — Remediation
11. F8c  ava-summary              SV   Summary — Validate
12. F8d  ava-summary              SAS  Summary — Final

  --phase aceita a etapa (F2b) ou o grupo (F2). Grupos: F1, F2, F3, F4, F5, F6, F8
  As etapas são a ORDEM DA ESTEIRA, não os módulos do agent_registry: aqui F5=DevOps e F6=QA.

exit=0
Bash Dry-run full pipeline
IN
echo "=== dry-run --all ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --all --dry-run 2>&1 | tail -30; echo "exit=$?"

OUT
=== dry-run --all ===
  Outputs  : projects/MeuERP-002/outputs/pipeline_runner

1. F1   ava-asis-orchestrator    FP   AS-IS Diagnostic — Full Pipeline
2. F2a  ava-tobe-orchestrator    SD   TO-BE Architecture — Solution Design
3. F2b  ava-devops-orchestrator  DP   DevOps Plan
4. F2c  ava-qa-orchestrator      TPT  QA — Test Plan & Strategy
5. F3   ava-prototype            —    Prototype
6. F4   ava-stack-orchestrator   SG   Tech Stack — Stack Generation
7. F5   ava-devops-orchestrator  DE   DevOps Execute
8. F6   ava-qa-orchestrator      TPT  QA — Test Execution
9. F8a  ava-summary              SAS  Summary — Generate
10. F8b  ava-summary-remediation  —    Summary — Remediation
11. F8c  ava-summary              SV   Summary — Validate
12. F8d  ava-summary              SAS  Summary — Final

────────────────────────────────────────────────────────────────────
  DRY RUN — nenhuma inferência executada
────────────────────────────────────────────────────────────────────
  F1   prompt ≈   391,056 chars (~97,764 tokens)  | @ava-asis-orchestrator | FP | project: MeuERP-002
  F2a  prompt ≈   399,091 chars (~99,772 tokens)  | @ava-tobe-orchestrator | SD | project: MeuERP-002
  F2b  prompt ≈   234,196 chars (~58,549 tokens)  | @ava-devops-orchestrator | DP | project: MeuERP-002
  F2c  prompt ≈   267,924 chars (~66,981 tokens)  | @ava-qa-orchestrator | TPT | project: MeuERP-002
  F3   prompt ≈   250,041 chars (~62,510 tokens)  | @ava-prototype project: MeuERP-002
  F4   prompt ≈   272,482 chars (~68,120 tokens)  | @ava-stack-orchestrator | SG | project: MeuERP-002
  F5   prompt ≈   234,198 chars (~58,549 tokens)  | @ava-devops-orchestrator | DE | project: MeuERP-002
  F6   prompt ≈   267,917 chars (~66,979 tokens)  | @ava-qa-orchestrator | TPT | project: MeuERP-002
  F8a  prompt ≈   276,520 chars (~69,130 tokens)  | @ava-summary | SAS | project: MeuERP-002
  F8b  prompt ≈   233,376 chars (~58,344 tokens)  | @ava-summary-remediation project: MeuERP-002
  F8c  prompt ≈   276,519 chars (~69,129 tokens)  | @ava-summary | SV | project: MeuERP-002
  F8d  prompt ≈   276,517 chars (~69,129 tokens)  | @ava-summary | SAS | project: MeuERP-002
exit=0
Triggers corretos (DP na F2b, DE na F5). Testando os demais seletores.

Bash Test remaining CLI selectors
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== --agent avulso ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --agent ava-asis-inventory --dry-run 2>&1 | grep -E "prompt ≈|^  [0-9]+\." ; echo "exit=$?"
echo; echo "=== --from F4 ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --all --from F4 --dry-run 2>&1 | grep "prompt ≈" | head -3
echo; echo "=== engine copilot ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F1 --engine copilot --dry-run 2>&1 | tail -4
echo; echo "=== projeto inexistente ==="; python src/shared/tools/ava_pipeline.py run -p NaoExiste --all --dry-run; echo "exit=$?"
echo; echo "=== agente inexistente ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --agent ava-nao-existe --dry-run; echo "exit=$?"

OUT
=== --agent avulso ===
  F1   prompt ≈   243,739 chars (~60,934 tokens)  | @ava-asis-inventory project: MeuERP-002
exit=0

=== --from F4 ===
  F4   prompt ≈   272,560 chars (~68,140 tokens)  | @ava-stack-orchestrator | SG | project: MeuERP-002
  F5   prompt ≈   234,276 chars (~58,569 tokens)  | @ava-devops-orchestrator | DE | project: MeuERP-002
  F6   prompt ≈   267,995 chars (~66,998 tokens)  | @ava-qa-orchestrator | TPT | project: MeuERP-002

=== engine copilot ===
────────────────────────────────────────────────────────────────────
  DRY RUN — nenhuma inferência executada
────────────────────────────────────────────────────────────────────
  F1   ✅  agent_runner.py --phase F1 --agent ava-asis-orchestrator

=== projeto inexistente ===
ERRO: projeto não encontrado: projects/NaoExiste
      Disponíveis: Meu-ERP, MeuERP-002
exit=2

=== agente inexistente ===
ERRO: agente desconhecido: 'ava-nao-existe'
      Não está na esteira nem no agent_registry.
      Agentes da esteira: ava-asis-orchestrator, ava-devops-orchestrator, ava-prototype, ava-qa-orchestrator, ava-stack-orchestrator, ava-summary, ava-summary-remediation, ava-tobe-orchestrator
      Lista completa: python src/shared/tools/agent_registry.py
exit=2
O motor copilot está mapeando errado: agent_runner --agent ava-asis-orchestrator filtraria zero nós, porque o orquestrador não é nó do DAG. A etapa "F1 = orquestrador" significa rodar o DAG inteiro da fase.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\ava_pipeline.py
Added 23 lines
Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\ava_pipeline.py
Modified
Bash Verify copilot engine argv mapping
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== engine copilot, esteira toda ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --all --engine copilot --dry-run 2>&1 | tail -14
echo; echo "=== engine copilot, agente avulso do DAG F1 ==="; python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --agent ava-asis-inventory --engine copilot --dry-run 2>&1 | tail -2

OUT
=== engine copilot, esteira toda ===
  DRY RUN — nenhuma inferência executada
────────────────────────────────────────────────────────────────────
  F1   ✅          agent_runner.py --project MeuERP-002 --phase F1 --via-proxy
  F2a  ⚠️  sem F2.yaml  agent_runner.py --project MeuERP-002 --phase F2 --via-proxy
  F2b  ⚠️  sem F6.yaml  agent_runner.py --project MeuERP-002 --phase F6 --via-proxy
  F2c  ⚠️  sem F5.yaml  agent_runner.py --project MeuERP-002 --phase F5 --via-proxy
  F3   ⚠️  sem F3.yaml  agent_runner.py --project MeuERP-002 --phase F3 --agent ava-prototype --via-proxy
  F4   ⚠️  sem F4.yaml  agent_runner.py --project MeuERP-002 --phase F4 --via-proxy
  F5   ⚠️  sem F6.yaml  agent_runner.py --project MeuERP-002 --phase F6 --via-proxy
  F6   ⚠️  sem F5.yaml  agent_runner.py --project MeuERP-002 --phase F5 --via-proxy
  F8a  ⚠️  sem F8.yaml  agent_runner.py --project MeuERP-002 --phase F8 --agent ava-summary --via-proxy
  F8b  ⚠️  sem F8.yaml  agent_runner.py --project MeuERP-002 --phase F8 --agent ava-summary-remediation --via-proxy
  F8c  ⚠️  sem F8.yaml  agent_runner.py --project MeuERP-002 --phase F8 --agent ava-summary --via-proxy
  F8d  ⚠️  sem F8.yaml  agent_runner.py --project MeuERP-002 --phase F8 --agent ava-summary --via-proxy

=== engine copilot, agente avulso do DAG F1 ===
────────────────────────────────────────────────────────────────────
  F1   ✅          agent_runner.py --project MeuERP-002 --phase F1 --agent ava-asis-inventory --via-proxy
Um vazamento semântico real ficou visível: no motor copilot, F2b (DP) e F5 (DE) colapsam no mesmo comando — o agent_runner não conhece triggers. Vou avisar explicitamente.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\ava_pipeline.py
Added 9 lines
Bash Run doctor
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== doctor ==="; python src/shared/tools/ava_pipeline.py doctor -p MeuERP-002; echo "exit=$?"

OUT
=== doctor ===

  ✅ config                 src\shared\data\ava-pipeline.yaml
  ✅ API key                .copilot-key
  ✅ SDK anthropic          0.116.0
  ✅ proxy Headroom         http://127.0.0.1:8787 no ar
  ✅ plano da esteira       12 passos
  ✅ projeto                MeuERP-002
  ✅ project-config.yaml    ok

  modelo=claude-sonnet-4-6 · endpoint=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic

exit=0
Tudo verde. Agora os arquivos de apoio e o shim.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\tools\requirements-pipeline.txt
17 lines
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\ava-pipeline.bat
29 lines
Agora o shim do pipeline_runner.py.

Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\pipeline_runner.py
53 lines
O shim promete menu interativo, mas run exige -p. Vou fazer o shim honrar isso, preservando o seletor de projeto do script antigo.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\pipeline_runner.py
Added 33 lines
Bash Test deprecation shim
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== shim: subcomando explicito ==="; python pipeline_runner.py list --phases 2>&1 | head -6
echo; echo "=== shim: menu de projeto (2 = MeuERP-002, depois todas, dry-run nao aplicavel) ==="
printf '2\n' | python pipeline_runner.py run --all --dry-run 2>&1 | tail -6

OUT
=== shim: subcomando explicito ===
AVISO: pipeline_runner.py está deprecado.
       Use: python src/shared/tools/ava_pipeline.py run -p <PROJETO></projeto>
       ou:  ava-pipeline.bat run -p <PROJETO></projeto> --all

Ordem da esteira (src/shared/data/ava-pipeline.yaml → pipeline.steps)

=== shim: menu de projeto (2 = MeuERP-002, depois todas, dry-run nao aplicavel) ===
  F5   prompt ≈   237,977 chars (~59,494 tokens)  | @ava-devops-orchestrator | DE | project: MeuERP-002
  F6   prompt ≈   271,696 chars (~67,924 tokens)  | @ava-qa-orchestrator | TPT | project: MeuERP-002
  F8a  prompt ≈   280,299 chars (~70,074 tokens)  | @ava-summary | SAS | project: MeuERP-002
  F8b  prompt ≈   237,155 chars (~59,288 tokens)  | @ava-summary-remediation project: MeuERP-002
  F8c  prompt ≈   280,298 chars (~70,074 tokens)  | @ava-summary | SV | project: MeuERP-002
  F8d  prompt ≈   280,296 chars (~70,074 tokens)  | @ava-summary | SAS | project: MeuERP-002
Shim funcionando. Agora os testes.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_pipeline_plan.py
194 lines
Bash Run plan tests
IN
python -m pytest tests/tools/test_pipeline_plan.py -q 2>&1 | tail -25

OUT
..................                                                       [100%]
18 passed in 0.35s
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_pipeline_config.py
180 lines
Bash Run config tests
IN
python -m pytest tests/tools/test_pipeline_config.py -q 2>&1 | tail -30

OUT
..................F.                                                     [100%]
================================== FAILURES ===================================
________________________ test_proxy_nunca_e_hardcoded _________________________

    def test_proxy_nunca_e_hardcoded():
        """Host/porta v�m de headroom_config.py, nunca de literal neste m�dulo.

    Porta duplicada foi o defeito que fez o launcher sondar 8787 com o proxy em
        8788 e degradar em sil�ncio, rodando a fase inteira sem compress�o.
        """
        fonte = (TOOLS_DIR / "pipeline_config.py").read_text(encoding="utf-8")

> assert "8787" not in fonte
> E       assert '8787' not in '#!/usr/bin/...ii=False))\n'
> E
> E         '8787' is contained here:
> E           LI sondar 8787, falhar e degradar em sil�ncio.
> E         ?           ++++
> E               """
> E               out = _run_tool(cfg, "url_command")
> E               if out is None or out.returncode != 0:...
> E
> E         ...Full output truncated (40 lines hidden), use '-vv' to show

tests\tools\test_pipeline_config.py:168: AssertionError
=========================== short test summary info ===========================
FAILED tests/tools/test_pipeline_config.py::test_proxy_nunca_e_hardcoded - as...
1 failed, 19 passed in 0.58s
O literal 8787 só aparece em comentário. Vou tornar o teste preciso — verifica constantes no AST, ignorando docstrings e comentários.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_pipeline_config.py
Added 29 lines
Bash Run both new test files
IN
python -m pytest tests/tools/test_pipeline_config.py tests/tools/test_pipeline_plan.py -q 2>&1 | tail -20

OUT
.......................................                                  [100%]
39 passed in 0.49s
39 testes passando. Rodando a suíte completa e a verificação end-to-end.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Bash Full test suite and CA02 check
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
python -m pytest tests/ -q 2>&1 | tail -20
echo "=== CA02: os dois .bat intactos ==="
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat && echo "OK - sem alteracao"

OUT
tests\tools\test_agent_wrappers.py:260: AssertionError
____ TestAnalyzerHomeResolution.test_sibling_discovery_finds_java_analyzer ____

self = <test_run_ast_analysis.TestAnalyzerHomeResolution testMethod=test_sibling_discovery_finds_java_analyzer>

    def test_sibling_discovery_finds_java_analyzer(self):
        # The real workspace has a sibling imfai-ava-tools repo for java.
        home = raa._get_analyzer_home({}, "java")
        expected = Path("C:/_git/imfai-ava-tools/ava-fabric-java-analyzer")

> self.assertEqual(home, expected)
> E       AssertionError: None != WindowsPath('C:/_git/imfai-ava-tools/ava-fabric-java-analyzer')

tests\utils\test_run_ast_analysis.py:84: AssertionError
=========================== short test summary info ===========================
FAILED tests/tools/test_agent_registry.py::test_esteira_sem_violacoes - Asser...
FAILED tests/tools/test_agent_wrappers.py::test_metadata_version_bate_com_o_frontmatter_canonico
FAILED tests/tools/test_agent_wrappers.py::test_disco_em_dia_com_o_registry
FAILED tests/utils/test_run_ast_analysis.py::TestAnalyzerHomeResolution::test_sibling_discovery_finds_java_analyzer
4 failed, 202 passed, 6 skipped in 13.45s
=== CA02: os dois .bat intactos ===
OK - sem alteracao
4 falhas. Preciso confirmar se são pré-existentes ou minhas — vou rodar essas mesmas provas numa worktree limpa do HEAD.

Bash Inspect failing test details
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
python -m pytest tests/tools/test_agent_registry.py::test_esteira_sem_violacoes tests/tools/test_agent_wrappers.py -q 2>&1 | grep -E "^E |AssertionError|divergente|ausente|órfão" | head -20

OUT
E       AssertionError:
E       assert not [{'check': 'E1', 'label': '--agent diverge do frontmatter name', 'agent': 'ava-asis-solution-dotnet', 'path': 'src/mod...': 'ava-asis-solution-dotnet', 'path': 'src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-dotnet.md', ...}]
tests\tools\test_agent_registry.py:141: AssertionError
E           assert '1.3.0' == '2.0.0'
E
E             - 2.0.0
E             + 1.3.0
tests\tools\test_agent_wrappers.py:212: AssertionError
E       assert not ['divergente: .github/agents/ava-qa-orchestrator.agent.md', 'divergente: .github/agents/ava-stack-angular-frontend.agent.md', 'divergente: .github/agents/ava-stack-react-frontend.agent.md']
tests\tools\test_agent_wrappers.py:260: AssertionError
Binary file (standard input) matches
Bash Run failing tests against clean HEAD
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
WT="$TMPDIR/head-check"
git worktree add --detach "$WT" HEAD >/dev/null 2>&1 && echo "worktree criada" || echo "falhou"
cd "$WT" && python -m pytest tests/tools/test_agent_registry.py tests/tools/test_agent_wrappers.py tests/utils/test_run_ast_analysis.py -q 2>&1 | tail -8

OUT
worktree criada

> self.assertEqual(home, expected)
> E       AssertionError: None != WindowsPath('C:/_git/imfai-ava-tools/ava-fabric-java-analyzer')

tests\utils\test_run_ast_analysis.py:84: AssertionError
=========================== short test summary info ===========================
FAILED tests/tools/test_agent_registry.py::test_esteira_sem_violacoes - Asser...
FAILED tests/utils/test_run_ast_analysis.py::TestAnalyzerHomeResolution::test_sibling_discovery_finds_java_analyzer
2 failed, 63 passed in 14.29s
Shell cwd was reset to c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents
Bash Clean up worktree and confirm drift source
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
git worktree remove --force "$TMPDIR/head-check" 2>&1 && echo "worktree removida"
echo "=== arquivos que causam o drift dos wrappers (nao sao meus) ==="
git status --porcelain -- src/modules/ava-fabric-agents/ | head

OUT
worktree removida
=== arquivos que causam o drift dos wrappers (nao sao meus) ===
 M src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md
 M src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md
 M src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md
 M src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md
 M src/modules/ava-fabric-agents/tech-stack/module.yaml
?? src/modules/ava-fabric-agents/shared/prototype-conversion-protocol.md
As 4 falhas são pré-existentes: 2 já falham no HEAD limpo, e as outras 2 vêm dos .md de agentes já modificados na árvore antes do meu trabalho. Nenhuma toca meus arquivos.

Vou cobrir a lógica de rota/degradação com teste determinístico em vez de derrubar o proxy que está rodando na sua máquina.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_pipeline_config.py
Added 53 lines
Bash Run tests including route logic
IN
python -m pytest tests/tools/test_pipeline_config.py tests/tools/test_pipeline_plan.py -q 2>&1 | tail -20

OUT
............................................                             [100%]
44 passed in 0.64s
Bash Verify precedence, route flags and bat wrapper
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== precedencia: env vence o YAML ==="
AVA_FOUNDRY_MODEL="claude-opus-4-6" python src/shared/tools/pipeline_config.py --model
python src/shared/tools/pipeline_config.py --model
echo; echo "=== --no-proxy forca rota direta ==="
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F8a --no-proxy --dry-run 2>&1 | grep -E "Rota|Modelo"
echo; echo "=== --model alias ==="
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F8a --model sonnet --dry-run 2>&1 | grep "Modelo"
echo; echo "=== rota default (proxy no ar) ==="
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F8a --dry-run 2>&1 | grep "Rota"
echo; echo "=== .bat de raiz ==="
cmd //c "ava-pipeline.bat list --phases" 2>&1 | head -4

OUT
=== precedencia: env vence o YAML ===
claude-opus-4-6
claude-sonnet-4-6

=== --no-proxy forca rota direta ===
  Rota     : direta → https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
  Modelo   : claude-sonnet-4-6

=== --model alias ===
  Modelo   : claude-sonnet-4-6

=== rota default (proxy no ar) ===
  Rota     : proxy (Headroom) → http://127.0.0.1:8787

=== .bat de raiz ===
'ava-pipeline.bat' is not recognized as an internal or external command,
operable program or batch file.
PowerShell Test root bat wrapper
IN
.\ava-pipeline.bat list --phases | Select-Object -First 6; "exit=$LASTEXITCODE"

OUT
Ordem da esteira (src/shared/data/ava-pipeline.yaml → pipeline.steps)

1. F1   ava-asis-orchestrator    FP   AS-IS Diagnostic — Full Pipeline
2. F2a  ava-tobe-orchestrator    SD   TO-BE Architecture — Solution Design
3. F2b  ava-devops-orchestrator  DP   DevOps Plan
   exit=
   Tudo verificado sem custo de inferência. Atualizando o CHANGELOG.

Bash Inspect CHANGELOG format
IN
head -40 CHANGELOG.md

OUT

# Changelog

## [2026-08-05] — QA Orchestrator em dois momentos (035-qa-orchestrator-two-moments)

### 💥 MAJOR — `ava-qa-orchestrator` v1.3.0 → v2.0.0

- **A esteira QA passa a ter dois momentos explícitos**, espelhando o padrão que o
  `ava-devops-orchestrator` já adota (`DP` Plano / `DE` Execução). **Momento 1 = `TPT`**
  (Test Plan TO-BE, após F2), **Momento 2 = `QE`** (novo — Quality Execute, após a esteira de
  código F4 Stack e a esteira DevOps Momento 2 `DE`).
- **Novo trigger `QE`** com `## Pre-condition Gate (QE)` de 4 passos bloqueantes: F2 concluída
  (`bounded-context-map.md` com ≥1 BC), planejamento `TPT` concluído (`test-plan.md` +
  `test-cases.md`), esteira de código concluída (sentinela `source-code/README.md` + backend ou
  frontend), e DevOps Momento 2 concluído (`infra/`, `iac/ci/`, `iac/cd/azure-pipelines-cd.yml`).
  Um Passo 4b não-bloqueante avisa quando `parity-test-report.md` está ausente.
- **🐛 Corrige o bug em que `RS` nunca executava.** O trigger `RS` consome
  `outputs/tobe/parity-test-report.md`, produzido pelo `ava-devops-compare-version` — agente #11
  da esteira DevOps Momento 2. Como o QA rodava em F5 e o `DE` em F6, o Passo T2 caía
  permanentemente em `RS | SKIPPED (parity-test-report.md ausente)`. Com o gate do `QE`, o
  artefato existe quando `RS` é alcançado.
- **`QS` está DEPRECADO** — vira alias que emite aviso e delega integralmente a
  §Routing — Trigger QE, incluindo o gate. Mantido por compatibilidade com o
  `master-orchestrator.md` (Step 5.1). O `## Pre-condition Gate (QS)` foi marcado como
  SUPERSEDIDO, preservado apenas como fonte do critério de detecção de bounded contexts.
- **Criadas `## Routing — Trigger PT` e `## Routing — Trigger RS`** — eram referências pendentes
  citadas 3× no arquivo sem seção correspondente, em caminho de execução ativo. `PT` é
  documentado como **verificação de disponibilidade, não dispatch**: não existe agente de parity
  test no módulo QA, o executor real é o `ava-devops-compare-version`. `RS` despacha
  `ava-qa-script-generator` em `mode: regression`.
- **`PT` e `RS` adicionados ao `## Triggers / Menu`**, de onde estavam ausentes apesar de
  aparecerem na tabela "Resumo de cobertura por trigger".
- **`FTM` entra no escopo do `QE`** (passo 3b, após `BM`, condicional ao `behavior-catalog.json`).
  Não pertence ao `TPT`: produz `outputs/qa/functional-test-matrix.md`, enquanto o `TPT` produz
  `outputs/tobe/tests/functional-test-matrix.md`.
- **`FQ` incluído no invariante terminal PT→RS**, corrigindo divergência entre a nota do menu, a
  tabela de cobertura e a lista do §Terminal Mandatory Steps. `DBI`, `CT` e `FT` também ganharam
  linha na tabela de cobertura.
- **Novo sinal `↳ ✅ [ava-qa-orchestrator] QE DEFERRED`** emitido junto à mensagem de bloqueio.
  Sem ele, o `master-orchestrator.md` (Step 5.2) executaria 4 retentativas idênticas antes de
  registrar WARN, já que a causa do bloqueio é a ordem das fases e não uma falha transitória.
  O CHANGELOG desta branch traz algo que conflita com a esteira que você especificou. Vou confirmar na spec do agente.

Bash Check QA orchestrator triggers
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
grep -nE "^\| \`?(TPT|QE|QS|RS|PT)\`?" src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md | head -20
echo "=== version ==="; grep -nE "^version:|^name:" src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md | head -4
echo "=== devops DP/DE ==="; grep -nE "^\| \`?(DP|DE)\`?" src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md | head

OUT
56:| `TPT` | **1 — Planejamento** | **Test Plan TO-BE** — geração de plano de testes consolidado e artefatos previstos pelo `ava-test-plan-tobe` ⛔ Pre-condition Gate — ver §Pre-condition Gate (TPT) |
57:| `QE` | **2 — Execução** | **Quality Execute** — executa toda a esteira QA fora do escopo do `TPT` (`GR→BM→FTM→TS→TC→AS→DBI→CT→FT→ET→EC→FQ`, encerrando em `PT→RS`). Só pode rodar depois da esteira de código (F4 Stack) **e** da esteira DevOps Momento 2 (`DE`) ⛔ Pre-condition Gate — ver §Pre-condition Gate (QE) |
58:| `QS` | 2 — Execução | ⚠️ **DEPRECADO — alias de `QE`**. Mantido por compatibilidade com o `master-orchestrator.md` (Step 5.1). Emite aviso e delega a §Routing — Trigger QE, incluindo o gate. |
76:| `PT` | **Parity Test** — verificação de disponibilidade do `parity-test-report.md`. Não é um dispatch do QA: o artefato é produzido pelo `ava-devops-compare-version` na esteira DevOps Momento 2. Ver §Routing — Trigger PT |
77:| `RS` | **Regression Suite** — gera a suíte de regressão derivada da paridade, via `ava-qa-script-generator` em `mode: regression`. Ver §Routing — Trigger RS |
728:| `QE`    | GR→BM→FTM→TS→TC→AS→DBI→CT→FT→ET→EC→FQ | ✅ | ✅ |
729:| `QS`    | ⚠️ deprecado — delega a `QE` | ✅ | ✅ |
738:| `TPT`   | Test Plan TO-BE (Momento 1 — planejamento) | ❌ | ❌ |
741:| `PT`    | Parity test (standalone) | — | ✅ |
742:| `RS`    | Regression suite (standalone) | — | — |
=== version ===
2:name: ava-qa-orchestrator
13:version: 2.0.0
=== devops DP/DE ===
59:| `DP` | devops-plan | **Momento 1 — Planejamento** (após F2 TO-BE). Decide estratégia e gera planos. Não executa deploy nem gera código de aplicação. |
60:| `DE` | devops-execute | **Momento 2 — Execução** (após F4 Stack). Despacha os 13 agentes DevOps seguindo o plano do Momento 1. |
Achei um conflito material que preciso resolver com você antes de fechar.

AskUserQuestion
OUT
Your questions have been answered: "O `ava-qa-orchestrator` foi para v2.0.0 nesta branch (CHANGELOG de hoje) e agora tem dois momentos: `TPT` = planejamento e `QE` = execução. Sua lista pede `TPT` nas duas etapas (F2c e F6). O CHANGELOG identifica exatamente isso como o bug que fazia o `RS` nunca executar. Mantenho `TPT` na F6 ou uso `QE`?"="QE na F6 (Recomendado)". You can now continue with these answers in mind.
Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\src\shared\data\ava-pipeline.yaml
Added 6 lines
Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_pipeline_plan.py
Modified
Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\tests\tools\test_pipeline_plan.py
Added 27 lines
Bash Re-run tests and show final pipeline
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
python -m pytest tests/tools/test_pipeline_plan.py tests/tools/test_pipeline_config.py -q 2>&1 | tail -8
echo "=== esteira final ==="
python src/shared/tools/ava_pipeline.py list --phases 2>&1 | sed -n '3,16p'

OUT
..............................................                           [100%]
46 passed in 0.90s
=== esteira final ===

1. F1   ava-asis-orchestrator    FP   AS-IS Diagnostic — Full Pipeline
2. F2a  ava-tobe-orchestrator    SD   TO-BE Architecture — Solution Design
3. F2b  ava-devops-orchestrator  DP   DevOps Plan
4. F2c  ava-qa-orchestrator      TPT  QA — Test Plan & Strategy
5. F3   ava-prototype            —    Prototype
6. F4   ava-stack-orchestrator   SG   Tech Stack — Stack Generation
7. F5   ava-devops-orchestrator  DE   DevOps Execute
8. F6   ava-qa-orchestrator      QE   QA — Quality Execute
9. F8a  ava-summary              SAS  Summary — Generate
10. F8b  ava-summary-remediation  —    Summary — Remediation
11. F8c  ava-summary              SV   Summary — Validate
12. F8d  ava-summary              SAS  Summary — Final
    Agora o CHANGELOG.

Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\CHANGELOG.md
Added 64 lines
Bash Final full verification
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== suite completa ==="
python -m pytest tests/ -q 2>&1 | tail -7
echo; echo "=== CA02 ==="
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat && echo "OK - .bat intactos"
echo; echo "=== doctor ==="
python src/shared/tools/ava_pipeline.py doctor -p MeuERP-002 2>&1 | sed 's/\x1b\[[0-9;]*m//g'

OUT
=== suite completa ===
tests\utils\test_run_ast_analysis.py:84: AssertionError
=========================== short test summary info ===========================
FAILED tests/tools/test_agent_registry.py::test_esteira_sem_violacoes - Asser...
FAILED tests/tools/test_agent_wrappers.py::test_metadata_version_bate_com_o_frontmatter_canonico
FAILED tests/tools/test_agent_wrappers.py::test_disco_em_dia_com_o_registry
FAILED tests/utils/test_run_ast_analysis.py::TestAnalyzerHomeResolution::test_sibling_discovery_finds_java_analyzer
4 failed, 209 passed, 6 skipped in 11.44s

=== CA02 ===
OK - .bat intactos

=== doctor ===

  ✅ config                 src\shared\data\ava-pipeline.yaml
  ✅ API key                .copilot-key
  ✅ SDK anthropic          0.116.0
  ✅ proxy Headroom         http://127.0.0.1:8787 no ar
  ✅ plano da esteira       12 passos
  ✅ projeto                MeuERP-002
  ✅ project-config.yaml    ok

  modelo=claude-sonnet-4-6 · endpoint=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
Update Todos

Criar src/shared/data/ava-pipeline.yaml (config central + ordem da esteira)

Criar src/shared/tools/pipeline_config.py (loader com precedência)

Criar src/shared/tools/pipeline_plan.py (expansão + validação vs agent_registry)

Criar src/shared/tools/sdk_engine.py (motor SDK Anthropic)

Criar src/shared/tools/ava_pipeline.py (CLI com run/list/config/doctor)

Criar ava-pipeline.bat e requirements-pipeline.txt

Converter pipeline_runner.py em shim de depreciação

Criar testes tests/tools/test_pipeline_config.py e test_pipeline_plan.py

Rodar verificação (dry-run, list, config, doctor, pytest, git diff dos .bat)

Atualizar CHANGELOG.md
Implementação concluída.

O que foi entregue
Configuração centralizada — src/shared/data/ava-pipeline.yaml concentra modelo, endpoint, chave, proxy, orçamento de contexto e a ordem da esteira. Precedência idêntica à do headroom.yaml: flags > env > project-config.yaml → bloco pipeline: > YAML > fallback. pipeline_config.py nunca levanta — env malformada degrada com aviso e mantém a camada de baixo.

CLI — ava_pipeline.py com run / list / config / doctor, mais ava-pipeline.bat na raiz. Cobre tudo que você pediu: -p, --phase (etapa F2b ou grupo F2, repetível), --all, --model (com aliases), --agent; e ainda --engine, --from, --via-proxy/--no-proxy, --yes, --dry-run, --json, com exit codes 0/1/2/130.

Headroom como proxy — URL de headroom_config.py --proxy-url e liveness de proxy status, ambos pelo venv isolado da tool. Nada hardcoded (há teste por AST que reprova 8787 e 127.0.0.1 no código). auto degrada com aviso alto; --via-proxy aborta em vez de rodar sem compressão.

Três coisas que mudaram em relação ao que você especificou
F6 usa QE, não TPT — você aprovou depois que apontei; o ava-qa-orchestrator foi para v2.0.0 nesta branch separando TPT (planeja) de QE (executa).

O motor copilot não propaga triggers. O agent_runner monta o envelope pelo DAG e não conhece DP/DE/TPT/QE, então F2b e F5 colapsariam no mesmo comando. O CLI avisa isso em voz alta e recomenda --engine sdk na etapa. Distinguir de verdade exigiria um DAG por etapa.

--engine copilot só cobre F1 — é o único .yaml em pipeline-dag/. O --dry-run marca ⚠️ sem F2.yaml etapa a etapa em vez de fingir cobertura.

Verificação
46 testes novos passando; suíte completa em 209 passed. As 4 falhas são pré-existentes — confirmei numa worktree do HEAD limpo: 2 já falham lá (test_esteira_sem_violacoes e um teste de path específico da máquina), e as outras 2 vêm dos .md de agentes já modificados na sua árvore antes deste trabalho (qa-orchestrator-agent.md, coder-*-frontend.md, orchestrator-stack.md). doctor todo verde, e git diff --exit-code nos dois .bat confirma que seguem intactos.

O que não rodei: a execução real com inferência (run --phase F8a --via-proxy --yes). Ela gasta tokens no seu Foundry e escreve artefatos em projects/MeuERP-002/outputs/ — prefiro que você decida. É também o que produziria a primeira linha em .headroom/proxy-requests.jsonl, permitindo confirmar aquele provável bug de nomes de campo no headroom_tool.py attribute que registrei como fora de escopo. Se quiser, disparo.

c#14-14
gere um documentação detalhada passa a passo de como utilizar o CLI, documente cada parametro  e de exemplos claros de uso  o arquivo deve ser criado na pasata docs
Bash Inspect docs folder
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
ls docs/ | head -40; echo "--- subdirs ---"; find docs -maxdepth 1 -type d

OUT
agents-catalog.md
analise-codegen-travado-tech-stack.md
architecture
asis-diagnostic-io-map.md
azure-devops-workitems-revisao-agentes.csv
azure-devops-workitems-revisao-agentes.md
azure-devops-workitems-revisao-agentes_all.csv
copilot-cli-runtime-facts.md
data.csv
full-pipeline-guide.md
functional
guia-execucao-fluxo-agentes.md
guia-repositorios-legados-grandes.md
inventory
issues
module-partitioner-guide.md
plan
podman-windows-guide.md
qa-orchestrator-io-map.md
repo-structure.html
required-secrets.md
speckit-guia.md
sql-ir-mer-plan.md
stack-split-impacto-po.md
summary-io-map.md
summary-validator-guide.md
tech-stack-io-map.md
tobe-architecture-io-map.md
tobe-architecture-io-map-compressed.md
tobe-input-artifacts-existence-check.md
--- subdirs ---
docs
docs/architecture
docs/functional
docs/inventory
docs/issues
docs/plan
Bash Check guide style
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
head -30 docs/module-partitioner-guide.md

OUT

# Guia do Particionador de Módulos (Module Partitioner)

> **Escopo**: AS-IS Diagnostic — Delphi (extensível a VB6/COBOL na Fase 2)
>
> **Artefatos gerados**: `module-partition.json`, `scope-filter-manifest.json`
> **Local**: `projects/{proj}/outputs/asis/ast-raw/{language}/compressed/` (`{language}` = e.g. `delphi`)

---

## O que é?

O **Module Partitioner** é um motor de inferência de módulos / bounded contexts que executa **após** a extração AST do repositório Delphi. Ele analisa o grafo de dependências entre units (cláusulas `uses`) e aplica o algoritmo **Leiden** (detecção de comunidades em grafos) para agrupar unidades fortemente acopladas em módulos lógicos.

**Decisão arquitetural**: a ferramenta AST externa (`ava-fabric-delphi-analyzer`) **não é modificada**. O particionador opera como *post-filter* sobre os 9 JSONs monolíticos já extraídos.

---

## Como funciona o fluxo

```
┌────────────────────────────────────────────┐
│ 1. Extração AST (run_ast_analysis)         │
│    gera 9 JSONs monolíticos                │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│ 2. Module Partitioner (ESTE DOCUMENTO)     │
│    lê 08_code_overview.json + fontes .pas  │
│    constrói grafo de dependências          │
Vou verificar a saída real de cada comando antes de documentar, para não escrever nada que não seja verdade.

Bash Capture CLI help output
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
python src/shared/tools/ava_pipeline.py --help 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
echo "=============== RUN ==============="
python src/shared/tools/ava_pipeline.py run --help 2>&1 | sed 's/\x1b\[[0-9;]*m//g'

OUT
usage: ava-pipeline [-h] {run,list,config,doctor} ...

Orquestra a esteira de agentes AVA Fabric

positional arguments:
  {run,list,config,doctor}
    run                 Executa a esteira (ou parte dela)
    list                Lista a ordem da esteira ou o catálogo de agentes
    config              Mostra a configuração efetiva
    doctor              Diagnostica config, chave, SDK, proxy e plano

options:
  -h, --help            show this help message and exit

Exemplos:
  ava-pipeline run -p MeuERP-002 --all
  ava-pipeline run -p MeuERP-002 --phase F2 --dry-run
  ava-pipeline run -p MeuERP-002 --phase F2b --model sonnet --yes
  ava-pipeline run -p MeuERP-002 --agent ava-asis-inventory
  ava-pipeline run -p MeuERP-002 --all --from F4 --via-proxy
  ava-pipeline list --phases
  ava-pipeline doctor -p MeuERP-002

Exit codes: 0 ok · 1 etapa falhou · 2 erro de configuração · 130 abortado
=============== RUN ===============
usage: ava-pipeline run [-h] -p PROJECT [--phase ID | --all] [--agent ID]
                        [--model MODEL] [--engine {sdk,copilot}] [--from ID]
                        [--via-proxy | --no-proxy] [--yes] [--dry-run]
                        [--json]

options:
  -h, --help            show this help message and exit
  -p, --project PROJECT
                        Nome do projeto em projects/
  --phase ID            Etapa (F2b) ou grupo (F2). Repetível; aceita F1,F2
  --all                 Todas as etapas da esteira, em ordem
  --agent ID            Roda só este agente (da esteira ou avulso do
                        agent_registry)
  --model MODEL         Wire model ou alias (ex: sonnet)
  --engine {sdk,copilot}
                        sdk (SDK Anthropic) | copilot (agent_runner.py)
  --from ID             Começa nesta etapa, cortando o prefixo
  --via-proxy           Exige o proxy Headroom; aborta se estiver fora do ar
  --no-proxy            Força a rota direta, sem compressão
  --yes, -y             Não pergunta a cada passo
  --dry-run             Mostra o plano e a rota sem gastar inferência
  --json                Emite o resultado em JSON no final
Bash Capture subcommand help
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
for c in list config doctor; do echo "=============== $c ==============="; python src/shared/tools/ava_pipeline.py $c --help 2>&1 | sed 's/\x1b\[[0-9;]*m//g'; done

OUT
=============== list ===============
usage: ava-pipeline list [-h] [-p PROJECT] [--phases] [--agents]
                         [--phase PHASE]

options:
  -h, --help            show this help message and exit
  -p, --project PROJECT
  --phases              Ordem da esteira (default)
  --agents              Catálogo do agent_registry
  --phase PHASE         Filtra --agents por fase do módulo
=============== config ===============
usage: ava-pipeline config [-h] [-p PROJECT] [--json]

options:
  -h, --help            show this help message and exit
  -p, --project PROJECT
  --json                (saída já é JSON)
=============== doctor ===============
usage: ava-pipeline doctor [-h] [-p PROJECT]

options:
  -h, --help            show this help message and exit
  -p, --project PROJECT
Bash Capture list agents and run banner
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== list --agents --phase F1 (amostra) ==="
python src/shared/tools/ava_pipeline.py list --agents --phase F1 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | head -6
echo "=== banner completo do run --dry-run ==="
python src/shared/tools/ava_pipeline.py run -p MeuERP-002 --phase F2b --dry-run 2>&1 | sed 's/\x1b\[[0-9;]*m//g'

OUT
=== list --agents --phase F1 (amostra) ===
  F1   ava-asis-bridge-fastqa                    v4.1.0
  F1   ava-asis-db-analyzer                      v1.6.1
  F1   ava-asis-documentation                    v3.1.1
  F1   ava-asis-events-pubsub                    v1.2.1
  F1   ava-asis-gap-migration-analyzer           v1.1.0
  F1   ava-asis-gaps-risks                       v1.4.0
=== banner completo do run --dry-run ===

════════════════════════════════════════════════════════════════════
  AVA Fabric — Pipeline Runner
════════════════════════════════════════════════════════════════════
  Projeto  : MeuERP-002
  Rota     : proxy (Headroom) → http://127.0.0.1:8787
  Modelo   : claude-sonnet-4-6
  Motor    : sdk
  Passos   : 1
  Outputs  : projects/MeuERP-002/outputs/pipeline_runner

   1. F2b  ava-devops-orchestrator  DP  DevOps Plan

────────────────────────────────────────────────────────────────────
  DRY RUN — nenhuma inferência executada
────────────────────────────────────────────────────────────────────
  F2b  prompt ≈   275,760 chars (~68,940 tokens)  | @ava-devops-orchestrator | DP | project: MeuERP-002
Tenho as saídas reais. Escrevendo a documentação.

Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\docs\guia-ava-pipeline-cli.md
712 lines
Vou conferir os fatos que afirmei no documento.

Bash Verify doc facts
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== versao real do devops-orchestrator ==="
python src/shared/tools/agent_registry.py --agent ava-devops-orchestrator 2>&1 | python -c "import json,sys; d=json.load(sys.stdin); print(d['agent'], 'v'+d['version'])"
echo "=== headers do doc ==="
grep -n "^## " docs/guia-ava-pipeline-cli.md
echo "=== headroom README existe? ==="
ls src/shared/tools/headroom/README.md >/dev/null 2>&1 && echo OK || echo AUSENTE

OUT
=== versao real do devops-orchestrator ===
ava-devops-orchestrator v1.0.0
=== headers do doc ===
11:## Índice
32:## 1. O que é
52:## 2. Pré-requisitos
85:## 3. Início rápido
111:## 4. A ordem da esteira
174:## 5. Subcomandos
232:## 6. Referência de parâmetros — `run`
301:## 7. Como escolher o que rodar
365:## 8. Rota e proxy Headroom
423:## 9. Motores: `sdk` e `copilot`
460:## 10. Configuração e precedência
529:## 11. Modo interativo
559:## 12. Onde ficam as saídas
581:## 13. Exit codes
597:## 14. Receitas
655:## 15. Solução de problemas
674:## 16. Migração do `pipeline_runner.py`
701:## Referências
=== headroom README existe? ===
OK
A versão que usei no exemplo do prompt interativo está errada — é v1.0.0, não v2.1.0.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\docs\guia-ava-pipeline-cli.md
Modified
Vou validar o exemplo do prompt interativo executando a função de verdade.

Bash Render real interactive prompt
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
printf 'A\n' | python -c "
import sys
sys.path.insert(0,'src/shared/tools')
import pipeline_config, pipeline_plan, ava_pipeline
cfg = pipeline_config.load_config('MeuERP-002')
steps = pipeline_plan.build_plan(cfg)
ava_pipeline.ask_permission(steps[2], 2, steps, False, ['F1','F2a'], [])
" 2>&1 | sed 's/\x1b\[[0-9;]*m//g'

OUT
════════════════════════════════════════════════════════════════════
  Passo 3/12 — F2b
  DevOps Plan
  Agente : @ava-devops-orchestrator (v1.0.0)
  Trigger: DP
════════════════════════════════════════════════════════════════════
  ✅F1  ✅F2a  ▶F2b  ○F2c  ○F3  ○F4  ○F5  ○F6  ○F8a  ○F8b  ○F8c  ○F8d

  Executar? [S]im / [P]ular / [V]er skill / [A]bortar:
O exemplo do prompt bate byte a byte com a saída real. Rodando a suíte uma última vez.

Bash Final check and file inventory
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
python -m pytest tests/tools/test_pipeline_plan.py tests/tools/test_pipeline_config.py -q 2>&1 | tail -3
echo "=== arquivos entregues ==="
git status --porcelain -- docs/guia-ava-pipeline-cli.md src/shared/data/ava-pipeline.yaml src/shared/tools/pipeline_config.py src/shared/tools/pipeline_plan.py src/shared/tools/sdk_engine.py src/shared/tools/ava_pipeline.py src/shared/tools/requirements-pipeline.txt ava-pipeline.bat tests/tools/test_pipeline_plan.py tests/tools/test_pipeline_config.py pipeline_runner.py CHANGELOG.md
echo "=== tamanho do guia ==="
wc -l docs/guia-ava-pipeline-cli.md

OUT
..............................................                           [100%]
46 passed in 1.34s
=== arquivos entregues ===
 M CHANGELOG.md
?? ava-pipeline.bat
?? docs/guia-ava-pipeline-cli.md
?? pipeline_runner.py
?? src/shared/data/ava-pipeline.yaml
?? src/shared/tools/ava_pipeline.py
?? src/shared/tools/pipeline_config.py
?? src/shared/tools/pipeline_plan.py
?? src/shared/tools/requirements-pipeline.txt
?? src/shared/tools/sdk_engine.py
?? tests/tools/test_pipeline_config.py
?? tests/tools/test_pipeline_plan.py
=== tamanho do guia ===
711 docs/guia-ava-pipeline-cli.md
Documentação criada em docs/guia-ava-pipeline-cli.md — 711 linhas, seguindo a convenção guia-*.md da pasta.

Estrutura
16 seções com índice navegável: O que é → Pré-requisitos → Início rápido → A ordem da esteira → Subcomandos → Referência de parâmetros → Como escolher o que rodar → Rota e proxy → Motores → Configuração e precedência → Modo interativo → Saídas → Exit codes → Receitas → Solução de problemas → Migração.

Cobertura dos parâmetros
Cada flag documentada em tabela com descrição e obrigatoriedade, agrupada por finalidade (projeto / seleção / modelo / motor / rota / execução), incluindo os pares mutuamente exclusivos (--phase vs --all, --via-proxy vs --no-proxy). Os quatro subcomandos têm seção própria; as 10 variáveis de ambiente estão mapeadas para o caminho que sobrescrevem.

Exemplos
Todos executáveis, cobrindo os três comportamentos distintos de --agent (agente que aparece uma vez na esteira, duas vezes, ou fora dela), seleção por grupo vs etapa, retomada com --from, e sete receitas prontas — ensaio, execução noturna sem interação, regeneração do ciclo de summary, gate barato em CI.

Precisão
Verifiquei cada saída citada rodando os comandos de verdade, em vez de escrever de memória. O bloco do prompt interativo foi renderizado chamando ask_permission diretamente e bate byte a byte. Corrigi uma versão de agente que eu tinha escrito errada no exemplo (ava-devops-orchestrator é v1.0.0, não v2.1.0).

As duas limitações reais do motor copilot — só existe DAG da F1, e o trigger não é propagado — estão documentadas com a saída de aviso literal, não escondidas. A divergência intencional entre etapa da esteira e fase do módulo (F5/F6 trocados) tem seção própria com aviso de "não corrigir", já que é o tipo de coisa que alguém tentaria alinhar achando que é bug.

Os 46 testes seguem passando.

c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\projects\MeuERP-003\outputs\asis\diagrams\architecture-blueprint.mmd
crie um speckit documentando a criação do CLI
Bash Find spec numbering and templates
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
ls specs/ | sort | tail -8
echo "=== .specify ==="; find .specify -maxdepth 2 -type d 2>/dev/null | head -20
echo "=== templates ==="; ls .specify/templates/ 2>/dev/null

OUT
029-screen-flow-batch-protocol
029-unify-test-plan-tobe
030-asis-pipeline-context-budget-dispatch-guard
031-headroom-context-compression-proxy
032-headroom-pipeline-wide-attribution
033-agent-isolation-context-engineering
034-prototype-to-component-conversion
035-qa-orchestrator-two-moments
=== .specify ===
.specify
.specify/extensions
.specify/extensions/agent-context
.specify/integrations
.specify/memory
.specify/scripts
.specify/scripts/powershell
.specify/templates
.specify/templates/overrides
.specify/workflows
.specify/workflows/speckit
=== templates ===
checklist-template.md
constitution-template.md
overrides
plan-template.md
spec-template.md
tasks-template.md
Bash Read spec template and 035 layout
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
ls specs/035-qa-orchestrator-two-moments/
echo "=== spec-template ==="; cat .specify/templates/spec-template.md

OUT
checklists
plan.md
spec.md
tasks.md
=== spec-template ===
# Agent Specification: [AGENT_NAME]

**Feature Branch**: `[###-agent-role]`
**Created**: [DATE]
**Status**: Draft
**Change Type**: [new-agent | modify-existing | bugfix]
**Input**: Agent description: "$ARGUMENTS"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-[PHASE]-[ROLE]` |
| **Version** | `1.0.0` |
| **Phase** | `F[N]` |
| **Module** | `[MODULE_ID]` |
| **Role** | [One-sentence description of what this agent does] |
| **Skill** | `ava-[PHASE]-[ROLE]` <!-- or: _(no skill -- internal)_ if dispatched only by orchestrator --> |
| **Dispatch** | [user-facing via SKILL.md \| internal-only via orchestrator] |

> **If Change Type is `modify-existing` or `bugfix`**:
> - Reference the existing agent file path (do not create a new file)
> - Determine version bump type: MAJOR (contract change) / MINOR (new field) / PATCH (fix)
> - The module.yaml entry already exists — Category 4 tasks are N/A
> - The SKILL.md already exists (if user-facing) — Category 1.5 is N/A

---

## 2. Agent Frontmatter

The agent `.md` file opens with YAML frontmatter (Constitution Article II):

```yaml
---
name: "ava-[PHASE]-[ROLE]"   # e.g. ava-asis-gdpr-check
version: "1.0.0"
description: |
  [1-2 sentences in Portuguese describing the agent's responsibility.]
  Ativa com: "[activation phrase 1]", "[activation phrase 2]", "[activation phrase 3]".
allowed-tools: Read, Write, Edit   # Claude Code tools: Read Write Edit Glob Grep Bash
---
```

Do NOT include `phase`, `module`, `inputs`, `outputs`, or `dependencies` in frontmatter.
These are not valid frontmatter fields in IMFAI agents.

---

## 3. Output Contract

The `## Output Contract` YAML block in the agent body (Constitution Article II):

```yaml
## Output Contract
```yaml
outputs:
  [artifact_name]:  "projects/{project_name}/outputs/[phase]/[filename].md"
  [metrics_file]:   "projects/{project_name}/outputs/[phase]/[filename].json"
  # Add one entry per artifact. Use lowercase {project_name} (not {PROJECT_NAME}).
```

```

> **New file vs. append decision**: Before listing artifacts, check whether this agent
> writes to a *new* file or *appends to an existing* one (e.g., `risk-register.json`).
> Appending to an existing contract file preserves downstream parser compatibility
> (e.g., `build_summary_comprehensive.py` — check `src/modules/ava-fabric-agents/summary/utils/`
> before creating a separate output file).

Path conventions:
| Phase | Output folder |
|---|---|
| F1 (AS-IS) | `projects/{project_name}/outputs/asis/` |
| F2 (TO-BE arch) | `projects/{project_name}/outputs/tobe/docs/` |
| F3 (codegen) | `projects/{project_name}/outputs/tobe/source-code/` |
| F5 (QA) | `projects/{project_name}/outputs/qa/` |
| F7 (DevOps) | `projects/{project_name}/outputs/tobe/devops/` |
| F6 (Deliverables) | `projects/{project_name}/outputs/deliverables/` |

---

## 4. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions (`**Story**:`) may be written in
> Brazilian Portuguese — IMFAI developers and client stakeholders read them.
> Acceptance scenarios (Given/When/Then) MUST be in English for BDD traceability
> with F5 QA agents (`ava-qa-behavior-mapping`, `ava-qa-scenario-generator`).

### Scenario 1 - Nominal Path (Priority: P1)

**Story**: As the migration orchestrator, I want [AGENT_NAME] to [PRIMARY_BEHAVIOR] so that [BUSINESS_OUTCOME].

**Why this priority**: [Value delivered]

**Acceptance Scenarios**:

1. **Given** a [LEGACY_TECHNOLOGY] project with a valid AgentTask, **When** the agent executes, **Then** it produces [PRIMARY_ARTIFACT] and `AgentResult.success` is true.
2. **Given** the above, **When** execution completes, **Then** `AgentResult.artifacts` lists all files and `AgentResult.next_agent` is set.

---

### Scenario 2 - Edge Case: Empty Codebase (Priority: P2)

**Why this priority**: Defensive handling of incomplete inputs.

**Acceptance Scenarios**:

1. **Given** a codebase with no [RELEVANT_CONTENT], **When** the agent executes, **Then** it produces an artifact noting absence and `AgentResult.success` is true.
2. **Given** the above, **Then** `AgentResult.risk.level` is 'low'.

---

### Scenario 3 - Quality Gate: High-Risk Finding (Priority: P1)

**Why this priority**: Safety gate -- must never be skipped.

**Acceptance Scenarios**:

1. **Given** analysis reveals [HIGH_RISK_CONDITION], **When** the agent executes, **Then** `AgentResult.risk.level` is 'high' or 'critical' and `AgentResult.human_gate_required` is true.
2. **Given** the above, **Then** `AgentResult.risk.findings` has severity >= 'high' and orchestrator pauses.

---

## 5. Quality Gate Requirements

- [ ] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [ ] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] Agent registered in module-level `module.yaml` diff included in plan (Article IV)
- [ ] All output paths use lowercase `{project_name}` and correct phase folder (Article II)
- [ ] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [ ] Security sub-pipeline impact assessed (Article VII)
- [ ] No technology versions hardcoded (Article I)
- [ ] Skill/Agent split declared: SKILL.md or internal-only with justification (Article XI)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Phase orchestrator | `ava-[PHASE]-orchestrator` | Must complete before this agent runs |
| [OTHER_DEPENDENCY] | `ava-[PHASE]-[ROLE]` | [Why this output is needed] |

---

## 7. Exclusions

- [EXCLUSION_1] -- handled by `ava-[OTHER_AGENT]`
- [EXCLUSION_2] -- out of scope

---

## 8. Assumptions

- [ASSUMPTION_1] -- e.g. 'The legacy repo is cloned at repository_path'
- [ASSUMPTION_2] -- e.g. 'project-config.yaml exists at `projects/{project_name}/context/`'

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Artifacts produced | All paths in section 3 exist after execution |
| Contract compliance | AgentResult validates against agent-result.schema.json |
| Gate accuracy | human_gate_required correctly set when risk >= high |
| No regression | Existing agents in module are unaffected |
O template padrão é para agentes; o CLI é tooling. Vou seguir o modelo das specs 031/033, que são de ferramenta.

Bash Inspect tooling spec structure
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== 033 spec.md headers ==="; grep -n "^#\{1,3\} " specs/033-agent-isolation-context-engineering/spec.md | head -40
echo; echo "=== 033 spec.md head ==="; head -35 specs/033-agent-isolation-context-engineering/spec.md

OUT
=== 033 spec.md headers ===
1:# Agent Specification: Isolamento de Janela por Agente + Context Engineering (GitHub Copilot CLI)
18:## 1. Identidade
37:## 2. Problem Statement
39:### P-1 — Uma janela para 102 agentes
54:### P-2 — O orçamento real é metade do que a esteira assume
71:### P-2.1 — Os 102 wrappers mudam o orçamento (re-medido em 2026-08-03)
94:### P-3 — Ingestão exaustiva por design
104:### P-4 — O formato `.agent.md` não está sendo usado
123:### P-5 — Dois bugs de runtime que hoje passam por "problema de contexto"
136:### P-6 — Regra em prosa não é enforcement
145:## 3. Decision
147:### 3.1 Isolamento híbrido — um formato de agente, dois modos de entrada
173:### 3.2 `AGENTS.md` é a fonte única, entregue por dois caminhos
205:### 3.3 Os 102 wrappers são gerados, não escritos
229:### 3.4 O "shared context com memória" é um context pack determinístico em disco
255:### 3.5 O hook `preToolUse` é o primeiro enforcement executável
268:### 3.6 O DAG é A fonte, com teste anti-divergência
284:### 3.7 O orquestrador de fase encolhe para o que só ele pode fazer
299:### 3.9 Feedback de execução — 4 recomendações apuradas (2026-08-03)
341:### 3.10 Segunda rodada de feedback (2026-08-04) — 3 recomendações
366:### 3.8 O que esta spec deliberadamente NÃO faz
374:## 4. User Scenarios (Given-When-Then)
376:### Scenario 1 — Isolamento real de janela (CA01, P1)
387:### Scenario 2 — O modo de execução do usuário não muda (CA02, P1)
396:### Scenario 3 — Todo agente é invocável nativamente (CA03, P1)
404:### Scenario 4 — Guardrails herdados de uma fonte única (CA04, P1)
412:### Scenario 5 — `AGENTS.md` serve qualquer linguagem legada (CA05, P1)
422:### Scenario 6 — Nenhum agente recebe pack maior que a janela (CA06, P1)
430:### Scenario 7 — Leitura de AST cru é negada, não desencorajada (CA07, P1)
437:### Scenario 8 — O DAG não vira a quarta fonte divergente (CA08, P1)
443:### Scenario 9 — Falha de configuração não é retentada (CA09, P2)
451:### Scenario 10 — Artefato ausente é falha, mesmo com `exit 0` (CA10, P1)
458:### Scenario 11 — Degradar, nunca quebrar (CA11, P2)
467:## 5. Quality Gate Requirements
488:## 6. Dependencies
507:## 7. Exclusions
538:## 8. Assumptions
559:## Success Criteria

=== 033 spec.md head ===
# Agent Specification: Isolamento de Janela por Agente + Context Engineering (GitHub Copilot CLI)

**Feature Branch**: `033-agent-isolation-context-engineering`
**Created**: 2026-08-02
**Status**: Draft
**Change Type**: add-new (`AGENTS.md` · gerador de wrappers · context pack · hook de enforcement)
+ modify-existing (`agent_runner.py` · `F1.yaml` · `orchestrator-asis.md` MAJOR · 3 utils PATCH)
**Input**: "Todo agente chamado pelo orquestrador da fase executa em uma janela isolada, usando com
mais eficiência a feature do GitHub Copilot CLI; todos os agentes customizados em
`.github/agents/*.agent.md`. O `AGENTS.md` deve ser criado com as regras/guardrails gerais para o
GitHub Copilot carregar — nada específico de linguagem legada, serve para java, delphi, .net e
outras; todos os agentes herdam. O shared context deve ser trabalhado de maneira eficiente com um
contexto de memória. **O modo de execução via GitHub CLI permanece o mesmo** — a diferença é que, ao
executar o orquestrador, os agentes invocados atuam na própria janela de contexto."

---

## 1. Identidade

Sem agente novo. Muda **como** os 102 agentes despacháveis existentes são invocados e **o que** cada um enxerga.

| Componente | Papel |
|---|---|
| `AGENTS.md` (raiz) | **Novo.** Fonte única dos guardrails gerais, 100% language-agnostic. Carregado nativamente no fluxo humano; injetado nos wrappers no fluxo do runner |
| `src/shared/tools/generate_agent_wrappers.py` | **Novo.** Gera os 102 `.github/agents/*.agent.md` a partir do `agent_registry.py` |
| `src/shared/tools/context_pack.py` | **Novo.** Materializa o contexto de cada agente em disco, dentro do orçamento — o "shared context com memória" |
| `src/shared/tools/hooks/pretooluse_guard.py` + `.github/hooks/ava-guardrails.json` | **Novos.** Transformam o LARGE ARTIFACT PROTOCOL de prosa em regra executável |
| `src/shared/tools/agent_runner.py` | **Existe (M1).** Ganha context pack, paralelismo, escada de retry e `execution_backend` |
| `src/shared/data/pipeline-dag/F1.yaml` | **Existe (parcial).** Passa de 3 nós para o DAG F1 completo |
| `orchestrator-asis.md` | 193.848 → ~15 KB. Deixa de despachar in-prompt e passa a invocar o runner |
| `src/shared/utils/validate_language_agnostic.py` | **Novo.** Lint por allowlist sobre `AGENTS.md` + wrappers |

**Agentes novos**: nenhum. **Skills novas**: nenhuma (os 75 `SKILL.md` continuam sendo a entrada humana).

---
Bash Inspect 035 plan and tasks structure
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== 035 plan.md headers ==="; grep -n "^#\{1,3\} " specs/035-qa-orchestrator-two-moments/plan.md | head -25
echo; echo "=== 035 plan head ==="; head -22 specs/035-qa-orchestrator-two-moments/plan.md
echo; echo "=== 035 tasks headers ==="; grep -n "^#\{1,3\} " specs/035-qa-orchestrator-two-moments/tasks.md | head -20
echo; echo "=== 035 checklists ==="; ls specs/035-qa-orchestrator-two-moments/checklists/

OUT
=== 035 plan.md headers ===
1:# Plan — Spec 035: QA Orchestrator em dois momentos
3:## Constitution Check
20:## Technical Context
48:## Implementation Phases
50:### Phase 1 — Spec Artifacts
53:### Phase 2 — Frontmatter, cabeçalho e menu
61:### Phase 3 — Pre-condition Gate (QE)
66:### Phase 4 — Routings
73:### Phase 5 — Seções terminais e tabelas
79:### Phase 6 — CHANGELOG
82:### Phase 7 — Verify
87:## Complexity

=== 035 plan head ===
# Plan — Spec 035: QA Orchestrator em dois momentos

## Constitution Check

- **Altera o contrato de triggers e a semântica do `QS`** (caller-visible: o `QS` passa a ter um
  gate que pode bloquear) → **MAJOR bump 1.3.0 → 2.0.0** (Article X,
  `.specify/memory/constitution.md:177`).
- **`## Output Contract` não muda** — os 12 artefatos declarados permanecem idênticos. Nenhum
  parser downstream (`build_summary_comprehensive.py`, `artifact-map.yaml`) é afetado.
- **`module.yaml` não muda** — nenhum agente é adicionado ou removido; o arquivo lista apenas
  `id` + `file` por agente, sem triggers. Category 4 = N/A.
- **`SKILL.md` não muda** — `.github/skills/ava-qa-orchestrator/SKILL.md` é genérico e apenas
  aponta para o arquivo do agente. Category 1.5 = N/A.
- **MAJOR bump → entrada em `CHANGELOG.md` obrigatória** (Article X).
- **Corpo do agente em português brasileiro** (Article V) — mantido; esta spec é o documento de
  planejamento.
- **Nenhuma versão de tecnologia hardcoded** (Article I) — os paths verificados no gate são
  artefatos de projeto, não versões de stack.

## Technical Context

O `ava-qa-orchestrator` reside em

=== 035 tasks headers ===
1:# Tasks — Spec 035: QA Orchestrator em dois momentos
3:## 1. Análise & Planejamento
10:## 2. Frontmatter, Cabeçalho e Menu
21:## 3. Pre-condition Gate (QE)
31:## 4. Routings
40:## 5. Seções Terminais e Tabelas
46:## 6. Documentação
49:## 7. Verificação & Qualidade
56:## Completion Checklist

=== 035 checklists ===
requirements.md
Bash List constitution articles and checklist sample
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
grep -nE "^### Article|^## Article" .specify/memory/constitution.md | head -20
echo "=== 035 checklist sample ==="; head -25 specs/035-qa-orchestrator-two-moments/checklists/requirements.md

OUT
=== 035 checklist sample ===
# Requirements Checklist — Spec 035

## Requisitos Funcionais
- [x] RF-001: O trigger `QE` existe no `## Triggers / Menu` e executa todos os triggers fora do escopo do `TPT`.
- [x] RF-002: `## Pre-condition Gate (QE)` bloqueia quando a esteira de código F4 não está concluída.
- [x] RF-003: `## Pre-condition Gate (QE)` bloqueia quando o DevOps Momento 2 (`DE`) não está concluído.
- [x] RF-004: `## Pre-condition Gate (QE)` bloqueia quando o planejamento `TPT` não produziu `test-plan.md` e `test-cases.md`.
- [x] RF-005: Ao bloquear, o gate emite o sinal `↳ ✅ [ava-qa-orchestrator] QE DEFERRED — {motivo}`.
- [x] RF-006: `TPT` está reclassificado como Momento 1 — Planejamento, sem alteração de comportamento.
- [x] RF-007: `QS` é um alias deprecado que emite aviso e delega ao `§Routing — Trigger QE`.
- [x] RF-008: `## Routing — Trigger PT` documenta que o executor real é o `ava-devops-compare-version`.
- [x] RF-009: `## Routing — Trigger RS` despacha `ava-qa-script-generator` em `mode: regression`.
- [x] RF-010: `FTM` é executado dentro do `QE`, após o `BM`, condicional ao `behavior-catalog.json`.

## Requisitos Não-Funcionais
- [x] RNF-001: O corpo do Routing `QS` é **movido** para o `QE`, não reescrito — ET VERIFICATION GATE, FQ COMPLETION GATE, `qa_test_runner.py` e `qa-master-report.md` preservados literalmente.
- [x] RNF-002: Os paths verificados pelo gate correspondem aos produtores reais, não aos paths do gate F6 do master (que estão errados).
- [x] RNF-003: O `## Output Contract` permanece inalterado — nenhum parser downstream é afetado.
- [x] RNF-004: Nenhuma fase nova é inventada na taxonomia do `pipeline_observer.py` (`--phase F5` mantido).
- [x] RNF-005: Version bump MAJOR (1.3.0 → 2.0.0) conforme Article X da constituição.

## Integridade
- [x] INT-001: Zero referências `§Routing — Trigger X` sem seção correspondente no arquivo.
- [x] INT-002: Todo código do `## Triggers / Menu` aparece na tabela "Resumo de cobertura por trigger".
- [x] INT-003: `FQ` consta da lista do invariante em `## Terminal Mandatory Steps`.
Bash Find constitution article headings
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
grep -nE "^\|?\s*\*{0,2}(Article|Artigo)\s+[IVX]+" .specify/memory/constitution.md | head -20

OUT
(Bash completed with no output)
Bash Locate article references in constitution
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
grep -niE "article|artigo" .specify/memory/constitution.md | head -20

OUT
213:- [ ] Agent body language is Brazilian Portuguese (Article V)
214:- [ ] BDD scenarios written for nominal, edge, and gate paths (Article VI)
215:- [ ] Security sub-pipeline impact assessed (Article VII)
216:- [ ] No technology versions hardcoded in agent body (Article I)
220:- [ ] Clean Architecture layer ordering respected (Article IX)
221:- [ ] `trace_id` propagation documented (Article VIII)
222:- [ ] Module-level `module.yaml` diff included in plan (Article IV)
223:- [ ] `CHANGELOG.md` entry prepared if MAJOR/MINOR bump (Article X)
224:- [ ] Skill/Agent split declared: SKILL.md or internal-only, with justification (Article XI)
268:> This reconciles Article III, the Phase → Module Mapping table, and the
Bash List constitution sections
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
grep -nE "^#{1,3} " .specify/memory/constitution.md | head -30

OUT
1:# AVA Fabric Agents — IMFAI Constitution
11:## Core Principles
13:### I. Configuration-Driven (NON-NEGOTIABLE)
25:### II. Agent Contract Standard (NON-NEGOTIABLE)
48:## Output Contract
60:### III. Pipeline Execution Contract
95:### IV. Module Registration (NON-NEGOTIABLE)
118:### V. Language Convention
132:### VI. Test-First Agent Behavior
143:### VII. Security-First (F1 Mandatory)
150:### VIII. Observability & Traceability
158:### IX. Clean Architecture Alignment
174:### X. Versioning & Breaking Changes
182:### XI. Skill/Agent Separation (NON-NEGOTIABLE)
204:## Quality Gate Requirements
206:### Pre-implementation Gates (checked by `/speckit.plan`)
218:### Architecture Gates (checked by `/speckit.plan`)
228:## Technology Reference
248:## Governance
274:## Project Reference
280:### Phase → Module Mapping
293:### Output Path Conventions
307:### `allowed-tools` Guidelines by Phase
319:### Resolving `project_name` at Runtime
330:### Key Shared Resource Paths
343:### Existing Agent Counts (as of v1.3.0)
Bash Read key constitution articles
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
sed -n '13,24p;60,70p;274,295p' .specify/memory/constitution.md

OUT
### I. Configuration-Driven (NON-NEGOTIABLE)

No agent may hardcode technology versions, cloud regions, stack choices, or
environment identifiers. All such values are resolved at runtime from:

- `projects/{PROJECT_NAME}/context/project-config.yaml` — per-project overrides
- `src/shared/data/reference-architecture.yaml` — canonical technology reference
- `docs/architecture/ConfigStackDotNet.yaml` — stack-specific defaults

Agents MUST reference these sources by documented key paths, never by literal
values.

### III. Pipeline Execution Contract

The master-orchestrator executes phases in the following strict sequence:

```

F1 → ava-summary → F2 → ava-summary → F3 → ava-summary → F4 → ava-summary
                                   → F5 → ava-summary
                                   → F6 → ava-summary
                                   → F7 → ava-summary (FINAL)

```

## Project Reference

> This section is a concrete lookup table for use when filling in spec, plan, and task
> templates. It does not introduce new principles — it maps the abstractions above to
> real paths in this repository.

### Phase → Module Mapping

| Phase | Module ID | Module folder | Orchestrator agent |
|---|---|---|---|
| F1 — AS-IS Diagnostic | `asis-diagnostic` | `src/modules/ava-fabric-agents/asis-diagnostic/` | `ava-asis-orchestrator` |
| F2 — TO-BE Architecture | `tobe-architecture` | `src/modules/ava-fabric-agents/tobe-architecture/` | `ava-tobe-orchestrator` |
| F3 — Prototype | `prototype` | `src/modules/ava-fabric-agents/prototype/` | _(dispatched directly by master-orchestrator)_ |
| F4 — Stack / Codegen | `tech-stack` | `src/modules/ava-fabric-agents/tech-stack/` | `ava-stack-orchestrator` |
| F5 — QA | `qa-agents` | `src/modules/ava-fabric-agents/qa-agents/` | `ava-qa-orchestrator` |
| F6 — DevOps | `devops-agents` | `src/modules/ava-fabric-agents/devops-agents/` | _(sequential)_ |
| F7 — Deliverables | `deliverables` | `src/modules/ava-fabric-agents/deliverables/` | _(sequential)_ |
| F8 — Summary (cross-cutting) | `summary` | `src/modules/ava-fabric-agents/summary/` | `ava-summary` |

### Output Path Conventions

| Phase | Output folder (relative to project root) |
Vou criar a spec 036 seguindo o modelo das specs de tooling.

Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\specs\036-ava-pipeline-cli\spec.md
420 lines
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\specs\036-ava-pipeline-cli\plan.md
122 lines
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\specs\036-ava-pipeline-cli\tasks.md
150 lines
Write c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\specs\036-ava-pipeline-cli\checklists\requirements.md
103 lines
Vou validar as afirmações verificáveis que fiz na spec, para não deixar nada só plausível.

Bash Verify spec citations
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== spec 036 nao duplica numero ==="; ls -d specs/036* 2>/dev/null
echo "=== estrutura ==="; find specs/036-ava-pipeline-cli -type f
echo; echo "=== conferindo citacoes de linha usadas na spec ==="
echo "-- F1.yaml:10-16 --"; sed -n '10,16p' src/shared/data/pipeline-dag/F1.yaml | head -3
echo "-- copilot-cli-headroom.bat:150-151 --"; sed -n '150,151p' copilot-cli-headroom.bat
echo "-- headroom_tool.py:127-131 --"; sed -n '127,131p' src/shared/tools/headroom/headroom_tool.py
echo "-- agent_runner.py:683 --"; sed -n '682,684p' src/shared/tools/agent_runner.py

OUT
=== spec 036 nao duplica numero ===
specs/036-ava-pipeline-cli
=== estrutura ===
specs/036-ava-pipeline-cli/checklists/requirements.md
specs/036-ava-pipeline-cli/plan.md
specs/036-ava-pipeline-cli/spec.md
specs/036-ava-pipeline-cli/tasks.md

=== conferindo citacoes de linha usadas na spec ===
-- F1.yaml:10-16 --
# ⚠️ RISCO R1 — quarta fonte de verdade.
#    Este arquivo NÃO pode virar mais um espelho manual. O repo já tem três que divergem
#    (ARTIFACT_CONTRACTS, AGENT_ARTIFACT_SLICE, AGENT_CATALOG — este último existe justamente
-- copilot-cli-headroom.bat:150-151 --
REM Resolve o orquestrador pelo agent_registry, NUNCA por um mapa local -- um
REM sexto espelho manual de fase->agente e o defeito que originou aquele modulo.
-- headroom_tool.py:127-131 --
#: Aliases tolerados no JSONL do proxy — o esquema não é contratual.
_TS_KEYS = ("timestamp", "ts", "time", "created_at")
_BEFORE_KEYS = ("tokens_before", "input_tokens_before", "tokens_in", "prompt_tokens_before")
_AFTER_KEYS = ("tokens_after", "input_tokens_after", "tokens_out", "prompt_tokens_after")
_LATENCY_KEYS = ("latency_ms", "duration_ms", "elapsed_ms")
-- agent_runner.py:683 --
    ap.add_argument("--via-proxy", action="store_true",
                    help="Roteia pelo proxy Headroom. M0: 71 dos 87 erros 404 vieram dessa rota "
                         "(falta o shim de /v1/models/{id}). Default é rota direta.")
As citações ao repositório conferem. Mas há um problema honesto: as linhas que citei do pipeline_runner.py são da versão anterior, que foi substituída pelo shim e nunca esteve em git (era arquivo não rastreado). Vou deixar isso explícito.

Edit c:\Desenv\repo\branch_develop_bugfix_02.08\imfai-ava-fabric-apps-agents\specs\036-ava-pipeline-cli\spec.md
Added 7 lines
Bash Final verification of spec and tests
IN
cd /c/Desenv/repo/branch_develop_bugfix_02.08/imfai-ava-fabric-apps-agents
echo "=== testes seguem verdes ==="
python -m pytest tests/tools/test_pipeline_plan.py tests/tools/test_pipeline_config.py -q 2>&1 | tail -3
echo; echo "=== spec 036: headers ==="
grep -c "" specs/036-ava-pipeline-cli/*.md specs/036-ava-pipeline-cli/checklists/*.md
echo; echo "=== CA02 ==="; git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat && echo "OK"

OUT
=== testes seguem verdes ===
..............................................                           [100%]
46 passed in 0.63s

=== spec 036: headers ===
specs/036-ava-pipeline-cli/plan.md:121
specs/036-ava-pipeline-cli/spec.md:426
specs/036-ava-pipeline-cli/tasks.md:149
specs/036-ava-pipeline-cli/checklists/requirements.md:102

=== CA02 ===
OK
Spec Kit criado em specs/036-ava-pipeline-cli/, seguindo a estrutura das specs de tooling (031/033/035) em vez do spec-template.md, que é orientado a agente.

Os quatro artefatos
spec.md — identidade dos componentes, 7 problemas numerados (P-1 a P-7) com evidência de código, 9 decisões (§3.1–3.9) incluindo o que a spec deliberadamente não faz, 10 cenários BDD com IDs de aceite (CA01–CA10), quality gates, dependências, exclusões e critérios de sucesso.

plan.md — Constitution Check artigo por artigo, contexto técnico, 9 fases de implementação e tabela de riscos com mitigação.

tasks.md — 96 tarefas em 10 categorias, todas marcadas concluídas, mais uma pendente explícita (T-110, a execução real com inferência que você ainda não autorizou).

checklists/requirements.md — 18 RF, 14 ORD (ordem da esteira), 7 CFG, 9 PXY, 11 INT, 8 RNF, 4 LIM e 6 DOC.

Duas coisas que a spec registra sem suavizar
As limitações viraram requisito rastreável. A seção LIM documenta os quatro limites reais — DAG só da F1, trigger não propagado no motor copilot, o bug do attribute não confirmado, e a ausência de registro canônico de triggers — em vez de deixá-los implícitos.

Corrigi uma fraqueza da própria spec. Citei linhas do pipeline_runner.py original como evidência do diagnóstico, mas aquele arquivo era untracked e foi substituído pelo shim — ninguém consegue conferir essas linhas no git. Adicionei nota explicando isso e separando as referências verificáveis (F1.yaml, copilot-cli-headroom.bat, agent_runner.py, headroom_tool.py, todas conferidas agora) das que não são.

Os 46 testes seguem verdes e os dois .bat continuam intactos.

```
