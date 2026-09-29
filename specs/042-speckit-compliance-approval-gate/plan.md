# Plan — Spec 042: Gate de aprovação humana da conformidade F3S

## Constitution Check

### A regra que esta spec excepciona

As correções de 2026-08-21 estabeleceram, no cabeçalho de
`src/shared/data/pipeline-dag/F3S.yaml`, que **erro não trava fase**: um passo
que falha é degradado, marcado como executado-com-aviso, e o motivo vai para
`remediation-report.json`. A regra nasceu de um defeito medido — o runner tinha
três destinos para um erro (abortar, "⏭ pulado", ou ✅ silencioso) e o pior era
o terceiro, porque o defeito reaparecia passos adiante atribuído ao agente
errado.

Esta spec introduz **o único caminho que volta a travar a esteira**: a recusa
explícita do operador em modo manual.

Não é violação da regra. A regra fala de **erro**, e um "Não" humano é
**decisão**. O que ela proíbe é que uma falha técnica — tool que reprova, insumo
ausente, resposta cortada — decida sozinha interromper o trabalho. Uma pessoa
olhando dois blockers CRITICAL e concluindo que a F4 não deve rodar é
exatamente o contrário disso: é o julgamento que a automação não tem.

O registro dessa exceção está em três lugares, de propósito, porque quem a
encontrar isolada vai lê-la como regressão e "consertar":

1. o cabeçalho de política do `F3S.yaml`;
2. o comentário de `_abort_pipeline` em `pipeline_runner 19.py`;
3. este documento.

### A regra que esta spec NÃO excepciona

Em modo automático nada trava. O gate pergunta com prazo e segue. A consequência
tem de ser dita com todas as letras: **rodando sempre em automático, o gate é
aviso e registro de auditoria, não barreira.** Quem depende da barreira roda em
manual.

Isso é uma decisão do usuário, tomada explicitamente, e não um efeito colateral.

### Fontes de verdade

Nenhuma lista nova é espelhada. O gate deriva do que já existe:

- os achados vêm de `compliance-status.json`, produzido pela wave6 e
  normalizado pela wave6b;
- o vocabulário da assinatura vem de
  `src/shared/schemas/wave-approval.schema.json`, que o repositório já usa para
  aprovação humana de wave;
- o timestamp vem de `src/shared/utils/ntp_time.py`;
- o gate de saída **importa** `speckit_compliance_gate.gate_status()` em vez de
  reimplementar o cálculo do fingerprint.

Este último ponto é o que impede o defeito clássico deste repositório: o
`agent_registry.py` existe porque dois catálogos escritos à mão divergiram em 52
agentes, e o cabeçalho do `pipeline-dag/F1.yaml` avisa contra virar "a quarta
fonte de verdade". Um fingerprint calculado em dois lugares divergiria em
silêncio, e o modo de falha seria o pior possível: uma assinatura considerada
válida por um lado e inválida pelo outro.

## Architecture

### Divisão tool / runner

```
wave6b  speckit-compliance-normalize   normaliza  → compliance-status.json
wave6c  speckit-compliance-gate        avalia     → compliance-gate.json
        └── runner: lê o arquivo, PERGUNTA, e invoca a tool para gravar
wave7   speckit-exit-gate              confere a decisão → libera ou bloqueia a F4
```

A tool **nunca pergunta nada**. Três razões:

1. **Ela não sabe o modo.** `auto_mode` é escolhido no menu do runner e nunca
   chega ao subprocesso. Uma tool que perguntasse penduraria toda execução
   agendada.
2. **O runner tem o console.** `safe_input` lê via `msvcrt.getwch()`,
   contornando o buffer de linha do PowerShell. Duplicar isso num subprocesso
   seria uma segunda implementação da parte mais frágil da interação.
3. **Arquivo em vez de stdout.** `run_tool_step` não captura a saída do
   subprocesso. Fazer o runner depender de parsear stdout do filho recriaria a
   fragilidade que `checks-report.json` e `compile-warnings.json` já eliminaram
   nas outras tools: o achado tem de sobreviver ao log.

### Entrada com prazo

`safe_input_timeout` é irmã de `safe_input`, com o laço de `msvcrt.kbhit()`
contra um deadline de `time.monotonic()`.

O detalhe que decide se a função é usável: **o prazo vale só até a primeira
tecla**. Um cronômetro que corta no meio da digitação produziria assinaturas
truncadas — pior que assinatura nenhuma, porque parecem válidas. Depois do
primeiro caractere, o comportamento é o de `safe_input`.

`None` (ninguém digitou) e `""` (apertou Enter) são retornos distintos: o
primeiro é silêncio, o segundo é resposta.

O laço de caracteres foi extraído para `_consumir_linha`, compartilhado pelas
duas funções. O tratamento de Enter, Backspace, Ctrl+C e teclas especiais de
dois bytes é sutil o bastante para que duas cópias divirjam.

### Fingerprint

`sha256` sobre `{verdict, findings[(id, severity, summary)], graph_checksum}`,
canonicalizado com `sort_keys`.

Cobre **todos** os achados, não só os graves: o usuário pediu que a aprovação
expire "quando os achados mudam", e um achado `low` que aparece ou some é uma
mudança do que foi lido.

Usa `graph_checksum` e não o hash do arquivo `traceability.json`: o arquivo
carrega `generated_at`, então uma recompilação idêntica mudaria o hash e
expiraria uma assinatura ainda válida. O `graph_checksum` acompanha o conteúdo
do grafo, que é o que a pessoa aprovou.

(O gate de saída tem uma checagem **separada** — `task_ledger.checksum_matches`
— que compara os bytes e reprova se o `traceability.json` mudou depois do
`--init` do razão. As duas coexistem porque respondem a perguntas diferentes:
"a pessoa aprovou este conteúdo?" e "a espinha continua imutável desde o
razão?".)

### Preservação da assinatura

`normalize()` reescreve `compliance-status.json` inteiro, em três caminhos:
canônico já válido (no-op), reconstruído a partir de fonte desviante, e
fallback determinístico. `_carry_approval` é aplicado nos três.

O caminho no-op precisou deixar de ser estritamente no-op: se o
`traceability.json` mudou, a assinatura armazenada ficou obsoleta e o arquivo
diria `approved` para um conteúdo que já não cobre. Ele passa a reescrever
**apenas** quando há rebaixamento a fazer, e reporta `action:
"approval_expired"` — o retorno não mente sobre ter escrito.

A assinatura expirada é **rebaixada, não descartada**: `previous_status`,
`reviewer` e `expired_reason` permanecem. Quem auditar precisa ver que houve
uma decisão e por que ela deixou de valer.

## Trabalho futuro (fora do escopo desta spec)

- **Autenticação do aprovador.** Hoje o gate registra quem a pessoa afirmou ser.
  Amarrar a identidade corporativa (Entra ID) transformaria registro em prova,
  mas exige credencial no runner e está fora desta camada.
- **`--redo <fase>` no runner.** Uma fase degradada conta como executada e a
  retomada a pula; hoje repeti-la exige responder `[N]` e recomeçar. O banner de
  retomada já nomeia as degradadas, o que torna a lacuna visível — mas não a
  fecha.
- **Aprovação assíncrona.** A decisão é síncrona, no terminal. Um fluxo em que a
  esteira pausa e retoma via notificação externa é outro desenho.
