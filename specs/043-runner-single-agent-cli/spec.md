# Agent Specification: Execução de um agente avulso pelo runner

**Feature Branch**: `043-runner-single-agent-cli`
**Created**: 2026-08-22
**Status**: Implemented
**Change Type**: modify-existing (`pipeline_runner 19.py`, `agent_registry.py`) + add-new (`runner_agent_cli.py`)
**Origem**: pedido do operador — "o script não possui a opção de executar apenas um agente para projeto específico, apenas a fase inteira"

## Problem Statement

O `pipeline_runner 19.py` é 100% interativo: nenhum `argparse`, nove prompts em sequência, e
`safe_input` usa `msvcrt.getwch()`, que lê do console e **ignora stdin** — nem por pipe dá para
automatizar. Para reexecutar um único agente, o operador navega o menu, escolhe a fase inteira e
responde `P` (pular) em cada passo já pronto.

Isso apareceu de forma concreta várias vezes na investigação da ISSUE-004: regerar só o
`F3S:planning:003`, ou rodar só o `ava-tobe-migration-plan` num projeto sem `wave-model.json`,
exigiu percorrer o menu dezenas de vezes. As próprias mensagens de erro do runner instruem o
operador a "rodar a fase produtora" porque não havia forma de rodar o agente produtor.

Três defeitos tornam o despacho avulso não-trivial:

**P-1 — Namespaces de fase divergentes.** `pipeline_plan.build_plan()` lê o `ava-pipeline.yaml`,
cuja numeração diverge da do runner (`ava-summary` é `S1`/`S4` no runner e `F8a`/`F8c`/`F8d` no
YAML; `F0`, `FC` e `FP` nem existem lá). `run_step` faz curto-circuito por **string exata** de
fase, então resolver pelo YAML pularia o builder determinístico do Summary e queimaria 128k
tokens para produzir o que um script Python produz de graça.

**P-2 — `load_skill` acha o agente por heurística.** Busca por substring em `rglob("*.md")` e
escolhe o **maior arquivo candidato**. Verificado: para `ava-tobe-migration-plan` ela carrega
`summary/utils/node_modules/playwright-core/.../references/migration.md` — documentação do
Playwright, 4.736 chars — em vez da spec real de 70.765.

**P-3 — Um BOM UTF-8 apaga um agente do catálogo.** `agent_registry` lia com `encoding="utf-8"` e
o frontmatter é casado com âncora de início absoluto. O único arquivo do repo com BOM,
`summary-remediation-agent.md`, sumia de `catalog()`, `load()` e `validate()` — derrubando
`validate_plan`, o verificador de observabilidade, as regras AT-00x, a geração de wrapper e a
resolução de `spec_path`.

## User Stories

### US1 — Rodar um agente sem percorrer o menu

Como operador, quero `--agent ava-tobe-migration-plan -p meu-erp-03` e nada mais, para regerar
um artefato sem gastar inferência nos passos já prontos.

### US2 — Errar o nome e ser corrigido

Como operador, quero que um id digitado errado devolva a sugestão certa e o comando para listar
o catálogo, em vez de um traceback.

### US3 — Não rodar o passo errado por omissão

Como operador, quero que um agente presente em mais de uma etapa recuse o despacho e me mostre as
opções, porque escolher por mim rodaria o trigger errado em silêncio.

### US4 — Não repetir um modo de falha conhecido

Como operador, quero que um agente com fan-out recuse o despacho avulso e liste as features/tasks
disponíveis, porque despachá-lo como passo único já produziu 26 artefatos numa resposta com o
contrato de seis agentes violado.

### US5 — Saber quando o contexto está degradado

Como operador, quero ser avisado quando o agente é avulso e não tem manifesto de insumos
declarado, para não tomar `val_ok=True` como evidência de nada.

### US6 — Não perder o modo interativo

Como operador, quero que rodar sem argumentos continue exatamente como antes.

## Acceptance Scenarios (BDD)

### Nominal

```gherkin
Cenário: despacho de um agente avulso
  Dado que o projeto meu-erp-03 existe
  E que ava-tobe-migration-plan está no agent_registry
  Quando executo --agent ava-tobe-migration-plan -p meu-erp-03
  Então nenhum prompt é exibido
  E o prompt enviado é "@ava-tobe-migration-plan project: meu-erp-03"
  E o skill carregado é a spec declarada no registry, não a da heurística
  E o exit code é 0
```

### Edge — fase do runner, nunca a do YAML

```gherkin
Cenário: agente cuja fase diverge entre runner e ava-pipeline.yaml
  Dado que ava-summary é S1/S4 no runner e F8a/F8c/F8d no ava-pipeline.yaml
  Quando resolvo o passo com --phase S1
  Então a fase do passo é S1
  E run_step encontra o curto-circuito que chama o builder determinístico
```

### Edge — agente ambíguo

```gherkin
Cenário: agente presente em duas etapas
  Dado que ava-devops-orchestrator aparece em F2b (DP) e F5 (DE)
  Quando executo --agent ava-devops-orchestrator -p meu-erp-03 sem --phase
  Então o despacho é recusado com exit 2
  E a mensagem lista as duas etapas com seus triggers
  E oferece o comando pronto com --phase
```

### Edge — agente com fan-out

```gherkin
Cenário: agente que roda uma vez por feature
  Dado que ava-speckit-specification é expandido por feature na esteira
  Quando executo --agent ava-speckit-specification -p nopcommerce-04 sem --feature
  Então o despacho é recusado com exit 2
  E a mensagem cita a evidência medida (26 artefatos, 68.170 tokens)
  E lista as features disponíveis no manifesto
  E oferece --force-single como saída explícita
```

### Edge — nome digitado errado

```gherkin
Cenário: typo no id do agente
  Quando executo --agent ava-tobe-migration-plna -p meu-erp-03
  Então o exit code é 2
  E a mensagem sugere ava-tobe-migration-plan
  E nenhuma inferência é gasta
```

### Quality gate — o estado da esteira não é tocado

```gherkin
Cenário: despacho avulso não corrompe a retomada
  Dado um runner-state.json de uma execução real da esteira
  Quando despacho um agente avulso
  Então _save_runner_state não é chamado
  E _write_status_html não é chamado
  E _write_remediation_report não é chamado
```

### Retomada — modo interativo intacto

```gherkin
Cenário: execução sem argumentos
  Quando executo o runner sem nenhum argumento
  Então _parse_cli devolve agent=None e project=None
  E o fluxo interativo de nove prompts roda como antes
```

## Quality Gate

- Rodar sem argumentos é indistinguível do comportamento anterior.
- Nenhum caminho novo usa `safe_input` — `msvcrt.getwch()` trava para sempre num pipe.
- Nenhum caminho novo grava estado da esteira.
- Insumo obrigatório ausente **recusa** (exit 1) em vez de degradar: sem passo sucessor a
  proteger, despachar sem insumo só produz alucinação.
- Toda mensagem de erro traz CAUSA RAIZ e um comando executável.

## Out of Scope

- `--task-id` — arrasta `task_ledger.start`, `verify_task_step` e o ramo de verificação de build,
  superfície maior que a feature. Sem ele, agente F4 cai na recusa de fan-out, que é o
  comportamento correto.
- `--phase` como seletor de fase inteira, `--yes`, `--from`, subcomandos — decisão de manter o
  escopo estrito. `--phase` existe apenas para desempatar agente ambíguo.
- Propagar `spec_path` em `_expand_dag_phases` / `_expand_ledger_phase`, o que eliminaria a
  heurística da esteira inteira.
- Corrigir as 19 violações de observabilidade pré-existentes que `test_esteira_sem_violacoes`
  acusa — falham antes e depois desta entrega.
