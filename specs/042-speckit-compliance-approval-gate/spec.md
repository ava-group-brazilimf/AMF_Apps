# Agent Specification: Gate de aprovação humana da conformidade F3S

**Feature Branch**: `042-speckit-compliance-approval-gate`
**Created**: 2026-08-21
**Status**: Implemented
**Change Type**: modify-existing + new-tool (`speckit_compliance_gate.py`) — sem agente novo, sem mudança no contrato de despacho de agente
**Origem**: run `nopcommerce-04` de 2026-08-21 (`runner19-1787309118` e sucessores)

## Problem Statement

O gate de saída da F3S confere **presença de arquivo**, não conteúdo. Medido em
`nopcommerce-04` em 2026-08-21:

- `ava-speckit-compliance` consumiu 731.728 tokens de entrada (86% da janela) e
  produziu análise correta;
- o veredito registrado foi `APPROVED_WITH_FINDINGS`;
- os achados incluíam **dois blockers CRITICAL** — `EDGE-W0-002` (estratégia de
  CMK para Always Encrypted não definida) e `EDGE-W0-005` (tecnologia de feature
  flags não escolhida) — ambos declarados pelo próprio agente como
  `BLOCKER for W0`;
- `_verdict_rule_check` registrou que esse veredito **contradiz a regra da spec
  do próprio agente** (`compliance-agent.md`: "ao menos um achado alto ⇒
  `BLOCKED`");
- o gate de saída retornou **PASS** e liberou a F4.

Nada disso estava escondido: tudo constava de `compliance-status.json`. O que
faltava era um mecanismo que levasse a informação até uma pessoa e exigisse uma
decisão antes de liberar a fase seguinte.

O contexto agrava o problema. As correções aplicadas horas antes no mesmo dia
estabeleceram a política "erro nunca trava fase": falha degrada, a fase fica como
executada e a pendência vai para `remediation-report.json`. Isso eliminou o
travamento silencioso e criou a ponta solta oposta — um achado crítico atravessa
a esteira inteira sem que ninguém tome ciência.

## User Stories

### US1 — Ciência antes da liberação

Como operador da esteira, quero ser avisado dos achados críticos **antes** de a
F4 ser liberada, para decidir com conhecimento em vez de descobrir o problema no
código gerado.

### US2 — Responsabilidade registrada

Como responsável técnico, quero que minha decisão de seguir fique gravada com meu
**nome**, meu **papel** e a **data** dentro do próprio artefato de conformidade,
para que a autorização seja auditável junto da evidência que a motivou.

### US3 — Execução automática não para

Como operador de execução automática (agendada, CI, lote), quero que a esteira
**nunca** pare por causa deste gate, e que o arquivo diga honestamente que
ninguém revisou — em vez de registrar um aprovador que não existiu.

### US4 — Assinatura não cobre conteúdo novo

Como auditor, quero que uma assinatura deixe de valer quando os artefatos mudam,
para que ela nunca ateste um conteúdo que a pessoa não leu.

## Requirements

### R1 — Critério de disparo

A decisão humana é exigida quando **qualquer** das condições vale:

| Código | Condição |
|---|---|
| `VERDICT_BLOCKED` | `verdict == "BLOCKED"` |
| `HIGH_SEVERITY_FINDINGS` | existe finding com `severity` ∈ {`critical`, `high`} |
| `VERDICT_RULE_INCONSISTENT` | `_verdict_rule_check.consistent == false` |

Os três são independentes. Confiar apenas no veredito do agente é exatamente o
que deixou o incidente passar: ele reportou `APPROVED_WITH_FINDINGS` sobre dois
blockers CRITICAL.

### R2 — Estados da decisão

| `approval.status` | Significado | Libera a F4 |
|---|---|---|
| `approved` | pessoa informou Nome e Papel | sim |
| `auto_acknowledged` | modo automático, ninguém informou | sim |
| `rejected` | pessoa recusou | não |
| `pending` | nenhuma decisão registrada | não |
| `expired` | achados mudaram desde a decisão | não |
| `not_required` | nenhum gatilho ativo | sim (nada a decidir) |

`auto_acknowledged` é estado **próprio**, e não `approved` com
`reviewer: "AUTO"`. A distinção entre "uma pessoa revisou" e "passou batido"
precisa sobreviver na leitura do arquivo, não só na intenção de quem escreveu.

### R3 — Campos da assinatura

`reviewer` e `reviewer_role` são **obrigatórios** para `approved` e `rejected`;
uma assinatura anônima não registra responsabilidade, que é o único motivo de o
gate existir. O vocabulário reusa
`src/shared/schemas/wave-approval.schema.json`, já usado no repositório para
aprovação humana de wave de migração.

`approved_at` vem de `src/shared/utils/ntp_time.py`, e `approved_at_source`
registra o servidor NTP consultado ou declara o fallback para o relógio local.
Um timestamp de auditoria sem procedência é indistinguível de um relógio
desajustado.

### R4 — Expiração por fingerprint

A assinatura é atrelada a `sha256` sobre o veredito, os `(id, severity, summary)`
de **todos** os achados e o `graph_checksum` do `traceability.json`. Divergiu o
fingerprint, a decisão vira `expired`.

O fingerprint acompanha **conteúdo**, não bytes: recompilar sem alterar nada
muda o `generated_at` do `traceability.json` mas não o `graph_checksum`, e a
assinatura sobrevive — como deve.

### R5 — Comportamento por modo

| Modo | Prompt | Silêncio | Recusa |
|---|---|---|---|
| Manual | `[S]im/[N]ão`, sem prazo; Nome e Papel obrigatórios | — | **para a F3S** |
| Automático | Nome e Papel opcionais, prazo de 30s | `auto_acknowledged` e segue | não aplicável |

Em modo automático o prazo vale só até a **primeira tecla**: quem começou a
digitar não pode ter o nome cortado no meio por um cronômetro.

### R6 — A tool nunca pergunta

`speckit_compliance_gate.py --evaluate` classifica e grava
`compliance-gate.json`, sempre com exit 0. A decisão é conduzida pelo runner,
que é quem sabe o modo de execução e tem o console. A comunicação entre os dois
é por arquivo, como nas demais tools da F3S.

### R7 — Auditoria append-only

Cada decisão é acrescentada a `approval-log.jsonl`. Uma reaprovação não pode
apagar a assinatura anterior.

### R8 — A assinatura sobrevive à re-normalização

`speckit_compliance_normalize.py` (wave6b) reescreve `compliance-status.json`
inteiro. Ele deve transportar o bloco `approval` — preservando-o quando o
fingerprint bate, rebaixando-o para `expired` quando não bate. Sem isso o gate
seria teatro: assina, e o passo seguinte limpa.

## Acceptance

| # | Cenário | Esperado |
|---|---|---|
| A1 | `--evaluate` num projeto com blocker CRITICAL | `requires_approval: true`, exit 0, `compliance-gate.json` gravado |
| A2 | Exit gate sem decisão registrada | FAIL, orientando a **decidir** (não a gerar arquivo) |
| A3 | `--approve` com Nome e Papel | grava `approved`, exit gate PASS |
| A4 | `--approve` sem Nome ou sem Papel | recusado, estado segue `pending` |
| A5 | `--acknowledge --mode auto` | grava `auto_acknowledged` sem revisor, exit gate PASS |
| A6 | `--reject` | grava `rejected`, exit gate FAIL |
| A7 | Achado novo após a assinatura | `expired`, exit gate volta a reprovar |
| A8 | Recompilação idêntica | assinatura **preservada** |
| A9 | wave6b após a assinatura | `approval` intacto |
| A10 | Runner em automático sem teclado | prazo estoura, `auto_acknowledged`, esteira segue |
| A11 | Runner em manual, resposta "N" | F3S para, estado salvo, `rejected` gravado |
| A12 | Duas decisões seguidas | ambas em `approval-log.jsonl`, na ordem |

## Fora do escopo

- Aprovação por interface web ou fluxo assíncrono (a decisão é síncrona, no
  terminal do runner, ou por invocação direta da CLI).
- Perfis de autorização — o gate registra quem afirmou ser quem, não autentica.
  Para o caso de uso (rastro de responsabilidade numa esteira operada por
  equipe conhecida), registro é o suficiente; autenticação exigiria identidade
  corporativa e está fora desta camada.
