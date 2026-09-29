# Gate de aprovação humana da F3S — AVA Fabric Agents

## Context

Em 21 de agosto de 2026, a F3S do projeto `nopcommerce-04` terminou com sucesso e
liberou a F4. O relatório de conformidade que ela produziu dizia, em suas
próprias palavras, que dois itens **bloqueavam** a wave W0:

| id | achado | declarado pelo agente como |
|---|---|---|
| `EDGE-W0-002` | estratégia de CMK para Always Encrypted não definida | `BLOCKER for Always Encrypted configuration` |
| `EDGE-W0-005` | tecnologia de feature flags não selecionada | `BLOCKER for coexistence gateway implementation` |

O veredito registrado foi `APPROVED_WITH_FINDINGS`. A regra na spec do próprio
agente (`compliance-agent.md`) diz: *"Ao menos um achado alto → `BLOCKED`"*. O
campo `_verdict_rule_check` registrou a contradição:

> o agente reportou APPROVED_WITH_FINDINGS carregando 3 achado(s) de severidade
> alta/crítica (NORM-001, NORM-002, NORM-003). O veredito do agente foi
> preservado; revise antes de liberar a F4.

E o gate de saída retornou **PASS**.

Nada estava escondido. Os 731.728 tokens de análise estavam em disco, o
contraditório estava anotado, e o mecanismo que decidia a liberação da F4
conferia outra coisa: se o arquivo `compliance-status.json` existia e tinha mais
de 1 byte.

## O que tornou isto possível

Três decisões corretas isoladamente, que juntas deixaram um vão.

**1. O gate de saída confere artefatos, e isso é proposital.** Ele existe para
garantir integridade estrutural — que a F4 não seja despachada sem constituição,
sem specs, sem grafo de tasks. Julgamento de conteúdo não era papel dele, e
continua não sendo. O que faltava era alguém fazendo esse papel.

**2. "Erro nunca trava fase" foi estabelecido horas antes.** As correções do
mesmo dia eliminaram o pior comportamento do runner: falhas viravam ✅ em
silêncio e reapareciam passos adiante atribuídas ao agente errado. A política
nova — degrada, marca como executada, registra em `remediation-report.json` — é
melhor. Mas ela vale para **erro**, e não tinha nada a dizer sobre um achado
válido que ninguém leu.

**3. O veredito é do agente, e não foi sobrescrito.** Quando o normalizador
detectou a incoerência, a escolha foi registrar e preservar, não corrigir. Um
veredito é julgamento; trocá-lo por um cálculo mecânico substituiria a análise
por uma regra que não sabe o que está em jogo. A decisão continua certa — só
precisava de um destinatário.

O vão, então, não era um bug em nenhuma das três. Era a ausência de um passo:
**ninguém era perguntado**.

## Decisão

Um gate entre a normalização (wave6b) e o gate de saída (wave7). Quando há
achado crítico ou relevante, o operador vê os achados e decide. Ao seguir, ficam
gravados no próprio `compliance-status.json` quem aprovou, em que papel e
quando.

### Os quatro caminhos

| Modo | Operador | Resultado | F4 |
|---|---|---|---|
| Manual | responde "S", informa Nome e Papel | `approved` | liberada |
| Manual | responde "N" | `rejected` | **bloqueada, esteira para** |
| Automático | informa Nome e Papel em até 30s | `approved` (`runner_mode: auto`) | liberada |
| Automático | silêncio, prazo estoura | `auto_acknowledged` | liberada |

A assimetria é deliberada. Em manual há uma pessoa a quem perguntar, e a decisão
dela vale — inclusive para parar a esteira. Em automático não há: perguntar é
cortesia com prazo, e o silêncio é registrado como silêncio.

### O limite honesto

**Rodando sempre em modo automático, este gate é aviso e registro de auditoria,
não barreira.** Ele torna impossível que um achado crítico passe sem ser
impresso no terminal e sem ficar anotado no arquivo. Não torna impossível que
passe.

Quem depende da barreira roda em manual. Isso precisa estar escrito, porque um
gate lido como garantia que ele não dá é pior que gate nenhum — cria confiança
sem lastro.

## Mecanismo

### Por que `auto_acknowledged` é estado próprio

A alternativa considerada era `approved` com `reviewer: "AUTO"`. Foi descartada.

Um campo de nome carrega convenção; um campo de estado carrega significado.
Quem consome `compliance-status.json` seis meses depois — auditoria, retrospectiva,
outra ferramenta — filtra por `status`, não inspeciona strings de `reviewer` à
procura de um sentinela. Colapsar os dois casos em `approved` significa que a
distinção entre *uma pessoa revisou* e *passou batido* sobrevive apenas na
intenção de quem escreveu o código, e não na leitura do dado.

O bloco `auto_acknowledged` carrega, além disso, uma `note` em texto corrido:

> execução automática — nenhuma pessoa informou aprovação; os blockers listados
> seguiram para a F4 sem revisão humana

### Por que o timestamp vem do NTP

`datetime.now()` num registro de auditoria é indistinguível de um relógio
desajustado — ou ajustado de propósito. O repositório já tinha
`src/shared/utils/ntp_time.py`, escrito exatamente para tornar esse fallback
**audível**: ele devolve `(timestamp, houve_fallback, servidor)` e sinaliza por
exit code quando degradou para o relógio local.

A assinatura grava os três:

```json
"approved_at": "2026-08-21T15:34:14-03:00",
"approved_at_source": "a.st1.ntp.br",
"ntp_fallback": false
```

Quando a rede falha, `approved_at_source` diz `"relógio local (NTP
indisponível)"` e `ntp_fallback` fica `true`. A data continua registrada — não
gravar seria pior —, mas quem auditar sabe o que está lendo.

O NTP só é consultado nos modos de **gravação**. `--evaluate` roda em todo
`pipeline_runner` e pagaria até 24 segundos de timeout de rede por uma
informação que não usa.

### Por que a assinatura expira

Uma aprovação atesta um conteúdo específico. Se os achados mudam, ela passa a
atestar algo que a pessoa não leu.

O fingerprint é `sha256` sobre o veredito, os `(id, severity, summary)` de todos
os achados, e o `graph_checksum` do `traceability.json`. Divergiu, o estado vira
`expired` e o gate de saída volta a reprovar.

Duas escolhas sutis:

- **Todos os achados, não só os graves.** Um achado `low` que aparece ou some é
  uma mudança do que foi lido.
- **`graph_checksum`, não o hash do arquivo.** `traceability.json` carrega
  `generated_at`; recompilar sem mudar nada mudaria o hash do arquivo e
  expiraria uma assinatura ainda válida. O `graph_checksum` acompanha o conteúdo
  do grafo, que é o que a pessoa aprovou.

Uma assinatura expirada é **rebaixada, não descartada**: `reviewer`,
`previous_status` e `expired_reason` permanecem no arquivo. Quem auditar precisa
ver que houve uma decisão e por que ela deixou de valer.

### Por que a ferramenta não pergunta

`speckit_compliance_gate.py` classifica e grava `compliance-gate.json`; o prompt
vive no `pipeline_runner`. Três razões, em ordem de peso:

1. **A ferramenta não sabe o modo.** `auto_mode` é escolhido no menu do runner e
   nunca chega ao subprocesso. Uma ferramenta que perguntasse penduraria toda
   execução agendada — o oposto do requisito.
2. **O runner tem o console.** `safe_input` lê via `msvcrt.getwch()`, contornando
   o buffer de linha do PowerShell. Duplicar isso num subprocesso seria uma
   segunda implementação da parte mais frágil da interação.
3. **Arquivo em vez de stdout.** `run_tool_step` não captura a saída do filho.
   Depender de parsear stdout recriaria a fragilidade que `checks-report.json` e
   `compile-warnings.json` já eliminaram nas outras tools da F3S: o achado tem de
   sobreviver ao log.

### O prazo que não corta quem está digitando

`safe_input_timeout` aplica o prazo **só até a primeira tecla**. Depois disso, o
comportamento é o de `safe_input`.

Um cronômetro que interrompesse no meio da digitação produziria assinaturas
truncadas — `"Rafael Alme"`, `"Tech L"` — que parecem válidas e não são. Pior
que não assinar.

`None` (ninguém digitou) e `""` (apertou Enter sem digitar) são retornos
distintos: o primeiro é silêncio, o segundo é resposta.

### A armadilha que quase esvaziou o gate

`speckit_compliance_normalize.py` (wave6b) reescreve `compliance-status.json`
inteiro. Sem cuidado, rodar a wave6b depois da assinatura **apagaria a
decisão** — o gate assinaria, e o passo seguinte limparia.

`_carry_approval` transporta o bloco nos três caminhos de escrita do
normalizador. O caminho "canônico já válido" precisou deixar de ser
estritamente no-op: se o `traceability.json` mudou, a assinatura armazenada
ficou obsoleta e o arquivo diria `approved` sobre conteúdo que já não cobre. Ele
passa a reescrever **apenas** quando há rebaixamento a fazer, e reporta
`action: "approval_expired"` — o retorno não mente sobre ter escrito.

## Verificação

Executada contra `projects/nopcommerce-04`, que estava no estado exato do
incidente.

```
1. sem decisão            evaluate exit=0 · exit gate=1 (bloqueado)
2. --acknowledge auto     auto_acknowledged, sem revisor · exit gate=0
3. --approve nominal      Rafael Almeida (Tech Lead) · fonte a.st1.ntp.br · exit gate=0
4. recompilação idêntica  state: approved  (assinatura preservada)
5. achado novo            state: expired   · exit gate=1 (bloqueado de novo)
```

O log de auditoria, append-only:

```
2026-08-21T18:06:40  approved           Rafael Almeida   manual
2026-08-21T18:34:01  auto_acknowledged  (sem revisor)    auto
2026-08-21T18:34:13  approved           Rafael Almeida   manual
```

Um detalhe do passo 4 vale registro: recompilar reescreveu `traceability.json`
com novo `generated_at`, e o gate de saída reprovou — não pela aprovação, mas
pela checagem separada `task_ledger.checksum_matches`, que exige que a espinha
seja imutável após o `--init` do razão. As duas checagens coexistem porque
respondem a perguntas diferentes: *a pessoa aprovou este conteúdo?* e *a espinha
continua a mesma desde o razão?*. Reinicializar o razão resolveu.

Automatizado: 43 casos novos entre
`tests/ava-fabric-agents/speckit/test_speckit_compliance_gate.py` (21) e
`tests/tools/test_runner_approval_gate.py` (22), mais 9 acrescidos aos testes do
normalizador e do gate de artefatos. O prompt real não é automatizável em CI; os
testes do runner extraem as funções por AST e substituem o teclado.

## Ver também

- `specs/042-speckit-compliance-approval-gate/` — spec, plan e tasks
- `src/shared/data/pipeline-dag/F3S.yaml` — cabeçalho de política e wave6c
- `docs/plan/speckit-planning-layer.md` — a camada de planejamento que este gate
  fecha
