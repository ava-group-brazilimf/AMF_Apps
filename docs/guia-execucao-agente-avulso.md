# Guia — Executar um agente avulso (`--agent`)

> **Escopo**: rodar UM agente, num projeto, sem percorrer o menu interativo nem executar a fase inteira
>
> **Executável**: `ava-pipeline-runner-cli.py` (raiz do repositório)
> **Resolução**: `src/shared/tools/runner_agent_cli.py` · **Catálogo**: `src/shared/tools/agent_registry.py`
> **Spec**: `specs/043-runner-single-agent-cli/`
> **Não substitui**: o modo interativo, que continua sendo o caminho para rodar fases

---

## Índice

1. [Para que serve](#1-para-que-serve)
2. [Uso básico](#2-uso-básico)
3. [Parâmetros](#3-parâmetros)
4. [Descobrir o nome do agente](#4-descobrir-o-nome-do-agente)
5. [Quando o runner recusa — e por quê](#5-quando-o-runner-recusa--e-por-quê)
6. [Limitações honestas](#6-limitações-honestas)
7. [Exit codes](#7-exit-codes)

---

## 1. Para que serve

Reexecutar um agente específico depois de corrigir um insumo, sem gastar inferência nos passos que
já produziram artefato. Antes, a única saída era escolher a fase inteira no menu e responder `P`
(pular) em cada passo pronto.

Rodar **sem argumentos** continua exatamente como antes — o menu de nove perguntas está intacto.

---

## 2. Uso básico

```powershell
# 1. Descobrir o nome exato do agente
python "ava-pipeline-runner-cli.py" --list-agents

# 2. Ensaiar: resolve o passo, mostra o prompt, NÃO gasta inferência
python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03 --dry-run

# 3. Executar de verdade
python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03
```

O prompt enviado ao agente:

```
@ava-tobe-migration-plan project: meu-erp-03
```

Com trigger e feature, quando aplicáveis:

```
@ava-speckit-specification | GS project: nopcommerce-04 | feature: 002-w1-low-complexity-bcs
```

---

## 3. Parâmetros

| Parâmetro                 | Obrigatório             | Descrição                                                                |
| -------------------------- | ------------------------ | -------------------------------------------------------------------------- |
| `--agent ID`             | —                       | id do agente, da esteira ou do`agent_registry`. Aciona o modo avulso     |
| `-p`, `--project NOME` | com`--agent`           | projeto em`projects/`. Sem `--agent`, apenas pré-preenche o menu      |
| `--phase ID`             | quando ambíguo          | desempata agente presente em mais de uma etapa (ex.:`F5`)                |
| `--trigger T`            | não                     | trigger do prompt. Sem ele, sai`@agente project: X`                      |
| `--feature F`            | para agentes por feature | pasta de feature do SpecKit (ex.:`002-w1-core-read`)                     |
| `--model ID`             | não                     | deployment do Foundry. Sem ele, usa o default do runner                    |
| `--headroom`             | não                     | sobe o proxy headroom antes do despacho                                    |
| `--force-single`         | não                     | despacha agente com fan-out como passo único —**não recomendado** |
| `--dry-run`              | não                     | resolve e mostra o prompt, sem gastar inferência                          |
| `--list-agents`          | não                     | lista os agentes e sai                                                     |
| `--json`                 | não                     | emite o resultado em JSON                                                  |

> `--phase` aqui **não** seleciona uma fase para executar: ele existe apenas para desempatar um id
> de agente que aparece em mais de uma etapa. Para rodar fases, use o modo interativo.

---

## 4. Descobrir o nome do agente

```powershell
python "ava-pipeline-runner-cli.py" --list-agents
```

A saída separa dois grupos:

```
Agentes da esteira (fase e trigger próprios):

  ava-asis-orchestrator                  F1/FP
  ava-devops-orchestrator                F2b/DP, F5/DE   [ambíguo]
  ava-summary                            S1/SAS, S4/SAS  [ambíguo]
  ...

Avulsos do agent_registry (96) — sem trigger, contexto pelo caminho legado:

  ava-tobe-migration-plan
  ava-tobe-architecture-design
  ...
```

Errar o nome não custa nada — a mensagem sugere o parecido:

```
  VOCÊ QUIS DIZER
    --agent ava-tobe-migration-plan
    --agent ava-deliverable-migration-plan
```

---

## 5. Quando o runner recusa — e por quê

Toda recusa sai com **CAUSA RAIZ** e um comando pronto. Nenhuma delas gasta inferência.

### Agente ambíguo

Três agentes aparecem em duas etapas, com trigger diferente em cada uma:

| Agente                      | Etapas                     |
| --------------------------- | -------------------------- |
| `ava-devops-orchestrator` | F2b (`DP`), F5 (`DE`)  |
| `ava-qa-orchestrator`     | F2c (`TPT`), F6 (`QE`) |
| `ava-summary`             | S1, S4                     |

Escolher por você rodaria o trigger errado em silêncio. Informe `--phase`.

### Agente com fan-out

Agentes de F3S rodam **uma vez por feature**; os de F4, **uma vez por task**. Despachá-los como
passo único é modo de falha medido: a F3S assim gerou 26 artefatos numa resposta de 68.170 tokens
com skill de 8 KB, violando o contrato de seis agentes.

A recusa lista as features disponíveis e monta o comando:

```powershell
python "ava-pipeline-runner-cli.py" --agent ava-speckit-specification -p nopcommerce-04 --feature 001-w0-foundation
```

`--force-single` despacha mesmo assim, assumindo o risco.

### Insumo obrigatório ausente

Para agentes da esteira, os insumos declarados são conferidos **antes** do despacho. Faltando
algum, o runner recusa e nomeia quem produz o artefato.

> Isto diverge da esteira de propósito: lá, insumo ausente degrada o passo para não travar as
> fases sucessoras. Num despacho avulso não há sucessora, e rodar sem o insumo só produz
> alucinação.

---

## 6. Limitações honestas

**Agente avulso roda com contexto degradado.** Os 19 agentes da esteira têm manifesto de insumos
declarado no `ava-pipeline.yaml`; os outros 96 não. Para estes, o contexto é montado pela
heurística legada de `load_context`, e o runner avisa:

```
  Agente avulso: sem manifesto de insumos declarado.
  O contexto sai da heurística legada de load_context, e val_ok=True
  não é evidência — sem contrato, a validação aprova qualquer saída.
```

**Sem trigger, o agente pode não saber qual protocolo seguir.** Vários agentes têm mais de um modo
de operação selecionado por trigger (`ava-tobe-migration-plan` tem `WM`, `backlog-tobe`, `WCR`).
O despacho avulso envia sem trigger salvo se você passar `--trigger`.

**O estado da esteira não é tocado.** `runner-state.json`, `pipeline-status.html` e o relatório de
remediação ficam intocados — gravá-los com um passo só corromperia a retomada de uma execução
real. Em compensação, um despacho avulso **não** aparece no dashboard nem conta como progresso.

**`--task-id` não existe ainda.** Agentes F4 caem na recusa de fan-out.

---

## 7. Exit codes

| Código | Significado                                                                      |
| ------- | -------------------------------------------------------------------------------- |
| `0`   | agente executado, artefatos validados                                            |
| `1`   | execução falhou, ou insumo obrigatório ausente, ou`val_ok` falso            |
| `2`   | erro de configuração: agente/projeto inexistente, ambíguo, fan-out sem escopo |
| `130` | interrompido com Ctrl+C                                                          |

---

## Ver também

- `docs/guia-ava-pipeline-cli.md` — o CLI declarativo `ava_pipeline.py`, que tem seu próprio
  `run --agent` sobre o motor SDK
- `docs/issues/ISSUE-004-speckit-plan-graph-perda-silenciosa.md` — as falhas de esteira que
  motivaram esta entrega
- `specs/043-runner-single-agent-cli/` — spec, plano e tasks
