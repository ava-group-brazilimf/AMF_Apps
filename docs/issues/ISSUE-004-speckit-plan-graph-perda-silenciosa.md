# ISSUE-004 — Perda silenciosa de `plan-graph.json` e travamento da F3S (nopcommerce-04)

**Date**: 2026-08-18
**Project**: nopcommerce-04 (reincidente em `my-nop-ecommerce`)
**Branch**: `feat/deterministic-task-dependency-graph`
**Severity**: HIGH — bloqueia a F3S por completo e derruba o processo sem gravar estado
**Status**: ROOT CAUSE IDENTIFIED — correções aplicadas em `ava-pipeline-runner-cli.py`
**Reported by**: Rafael Almeida (PM)
**Spec**: `specs/041-runner-output-contract-enforcement/`

---

## 1. Sintoma

Ao executar a esteira do `nopcommerce-04`, a F3S termina com:

```
insumo obrigatório ausente no passo F3S:tasks:003-w2-medium-complexity-bcs
(ava-speckit-tasks), projeto nopcommerce-04:

  - outputs/tobe/speckit/specs/003-w2-medium-complexity-bcs/plan-graph.json
      esperado em:   projects/nopcommerce-04/outputs/tobe/speckit/specs/003-w2-medium-complexity-bcs/plan-graph.json

  O passo não foi despachado — nenhuma inferência foi gasta.
```

E o processo **morre em seguida**, sem relatório final, sem atualizar o dashboard e sem gravar o
estado de retomada. O `pipeline-status.html` fica congelado em
`▶ F3S:tasks:003-w2-medium-complexity-bcs — Executando…` indefinidamente.

A mensagem está **correta** — o insumo realmente não existe. Mas ela é o sintoma de uma falha
ocorrida **8 horas antes**, em outro passo, e o travamento é um defeito independente.

---

## 2. Evidência

### 2.1 Estado em disco

`projects/nopcommerce-04/outputs/tobe/speckit/specs/`

| Feature | codegen | spec.md | plan.md | **plan-graph.json** | task-fragment.json |
| --- | --- | --- | --- | --- | --- |
| 001-w0-foundation | false | ✅ | n/a | n/a | n/a |
| 002-w1-low-complexity-bcs | true | ✅ | ✅ | ✅ | ✅ |
| **003-w2-medium-complexity-bcs** | true | ✅ | ✅ | ❌ **ausente** | ❌ ausente |
| 004-w3-high-complexity-bcs | true | ✅ | ✅ | ✅ | ❌ ausente |
| 005-w4-cutover | false | ✅ | n/a | n/a | n/a |

### 2.2 Linha do tempo (de `outputs/pipeline_runner/runner-state.json` + relatórios `.md`)

| Hora | Passo | Resultado |
| --- | --- | --- |
| 14:33 | `F3S:planning:002` | `plan.md` ✅ · `plan-graph.json` **perdido** |
| 14:45 | `F3S:planning:003` | `plan.md` ✅ · `plan-graph.json` **perdido** |
| 14:57 | `F3S:planning:004` | `plan.md` ✅ · `plan-graph.json` **perdido** |
| 16:49 | `F3S:planning:002` (re-run) | ambos ✅ |
| 22:30 | `F3S:planning:004` (re-run) | ambos ✅ |
| — | `F3S:planning:003` | **pulado pelo operador** — nunca re-executado |
| 22:41 | `F3S:tasks:003` | preflight bloqueia → processo morre |

Nos três despachos das 14h o passo foi registrado como **executado, com `val_ok: true`**, apesar
de ter produzido metade do contrato de saída.

### 2.3 Estrutura dos blocos `FILE` na resposta do agente

```
F3S:planning:003 (14:45)         F3S:planning:004 (22:30, re-run OK)
L38   <!-- FILE: plan.md -->     L44   <!-- FILE: plan.md -->
L806  <!-- /FILE -->    fechado  L584  <!-- /FILE -->          fechado
L808  <!-- FILE: plan-graph -->  L586  <!-- FILE: plan-graph -->
      (EOF — nunca fecha)        L2024 <!-- /FILE -->          fechado
```

O arquivo termina literalmente em `"task_type":`, no meio do JSON. **82.103 caracteres** do grafo
haviam sido gerados e foram descartados.

---

## 3. Causa raiz

Cinco defeitos encadeados. O primeiro é o que perde o artefato; os demais explicam por que a
perda passou despercebida por três features e por que o pipeline morre em vez de falhar.

### D1 — Bloco truncado descartado em silêncio *(defeito central)*

`ava-pipeline-runner-cli.py`, `parse_and_write_outputs` (antes da correção):

```python
for m in _FILE_BLOCK.finditer(response):   # só blocos FECHADOS
    ...
if written:
    _merge_any_parts_in_written(written, project)
    return written                          # ← early return
# Formato 2: bloco aberto sem <!-- /FILE --> (resposta truncada)
```

O parser de bloco aberto só rodava se o de bloco fechado não encontrasse **nada**. Como o
`plan.md` fechou, `written` ficou não-vazio, a função retornou, e o bloco do `plan-graph.json` —
aberto porque foi cortado por `max_tokens` — nunca foi processado. Nenhum aviso, nenhum registro.

Defeito secundário no mesmo trecho: `if (truncated and not _is_already_part)` fatiava em `.partN`
**todos** os blocos, inclusive os fechados e íntegros. Foi assim que o `plan.md` de 003 (104 KB,
completo) virou `plan.part1.md` + `plan.part2.md` + `plan.MERGE-INSTRUCTIONS.md` sem necessidade.

### D2 — Truncamento não reprova o passo

`stop_reason == "max_tokens"` apenas imprimia um aviso amarelo. Não virava falha, não gerava
retry, não era gravado no estado nem no relatório. O passo seguia como executado.

### D3 — Validação pós-passo inoperante na F3S

```python
contract = PHASE_ARTIFACT_CONTRACT.get(phase, {"required": [], "optional": []})
```

Em runtime a fase é `F3S:planning:003-w2-medium-complexity-bcs`; a chave do dicionário é `"F3S"`.
Nunca casa → contrato vazio → `ok = True` sempre. Daí o `val_ok: true` em todos os passos da F3S.

O `PHASE_MAX_TOKENS`, logo acima no mesmo arquivo, já recebera o fallback correto
(`phase.split(":", 1)[0]`) no commit `6acaba04`; o `validate_phase_artifacts` ficou de fora.

### D4 — `outputs` declarados no DAG são descartados

`src/shared/data/pipeline-dag/F3S.yaml:161-163` declara, para `ava-speckit-planning`:

```yaml
outputs:
  - "specs/{feature}/plan.md"
  - "specs/{feature}/plan-graph.json"
```

`pipeline_plan._resolver_outputs` resolve o `{feature}` corretamente e grava a chave no dict do
passo (`pipeline_plan.py:222`). Em seguida ela é **perdida**: o dataclass `Step` não tem campo
`outputs`, e `_expand_dag_phases` (`ava-pipeline-runner-cli.py:303-311`) não copiava a chave. O único
consumidor no repositório era `agent_runner.py:806`, no motor copilot — que não é o caminho em uso.

Resultado: `plan-graph.json` é declarado como saída esperada em **três** lugares —
`speckit/module.yaml`, `pipeline-dag/F3S.yaml` e `planning-agent.md` — e nenhum dos três era
aplicado por código executável. Ele só se tornava load-bearing como `inputs.mandatory` do
consumidor seguinte, o que faz a falha aflorar um passo tarde demais.

### D5 — `SystemExit` escapa do handler e mata o processo *(o "travamento")*

```python
# load_context
if res.blocked:
    raise SystemExit(_ctx_manifest.format_missing(...))

# laço principal
except Exception as e:
    ...
    retry = safe_input("  Tentar novamente? [S/N]: ")
```

`SystemExit` herda de `BaseException`, **não** de `Exception`. Não é capturado. Em cascata:

- não há prompt de retry/pular;
- `_save_runner_state()` não roda → estado congelado no índice anterior;
- `_write_status_html(..., done=True)` não roda → dashboard eternamente em "Executando…"
  (o HTML de "em execução" é escrito *antes* do despacho);
- `_finalize_runner_state()` não roda → nunca vira `runner-state-done.json`;
- o proxy headroom não é encerrado.

Ao retomar, o runner volta ao mesmo passo e morre igual — o loop de "trava" relatado.

### D6 — Dashboard congelado durante o passo

Reportado ao re-executar a fase: `pipeline-status.html` não mostra progresso em tempo real.

O HTML carrega `<meta http-equiv="refresh" content="3">`, então o **navegador** recarrega a cada
3 s. Mas quem escreve o arquivo é o runner, e ele só escrevia em pontos discretos do laço: antes
do despacho (com `current_phase` marcado) e depois que o passo termina. Durante os ~700 s de um
`F3S:planning`, o navegador relia byte a byte o mesmo conteúdo — relógio parado, sem indicação de
avanço, indistinguível de um processo travado. Que é justamente o que D5 produzia de verdade,
tornando os dois sintomas impossíveis de separar a olho.

Dois agravantes na retomada:

- o caminho `[RESUME] … já executado — pulando` não escrevia o HTML, então durante a varredura
  dos passos já concluídos — na retomada, a maioria — o dashboard permanecia na foto inicial;
- a foto inicial é escrita **antes** da expansão do DAG, com a F3S como passo único; a lista
  expandida de 20 passos só aparecia no primeiro despacho.

### D7 — Veredicto duplicado após retomada

Descoberto ao inspecionar o estado depois da re-execução bem-sucedida de `F3S:planning:003`: a
fase ficou simultaneamente em `executed` **e** em `skipped`. As listas só recebiam `append`;
nada removia o veredicto da tentativa anterior.

O laço de renderização testa na ordem `aborted` → `skipped` → `executed`, então um passo que
rodou com sucesso na retomada continuava exibido como "⏭ Pulado", e era contado nos dois
totalizadores ao mesmo tempo (`12/20 fases · 1 pulada`, com 12 + 1 > 12 passos distintos).

### Contribuinte: orçamento de saída disputado

`PHASE_MAX_TOKENS["F3S"] = 64_000`. O agente `ava-speckit-planning` precisa emitir, num único
turno, um `plan.md` de ~100 KB **e** um `plan-graph.json` de ~100 KB. Não cabe. O commit
`6acaba04` ("seção 9 compacta no planning") já era uma tentativa de mitigar isso por economia de
tokens. Os re-runs de 002 e 004 couberam por sorte de dimensionamento, não por garantia.

### Origem

O commit `a29c256b` ("grafo determinístico de dependências de tarefas") adicionou, no mesmo diff,
`plan-graph.json` como `outputs` da wave4 **e** como `inputs.mandatory` das waves 5 e 6 — sem
produtor determinístico e sem gate de saída. A spec correspondente
(`specs/040-speckit-task-dependency-graph/tasks.md`) declara-se "implementação concluída; piloto
real pendente", com a única task aberta sendo `T-053 — Executar piloto F3S/F4`. O
`nopcommerce-04` **é** esse piloto.

---

## 4. Correções aplicadas

Todas em `ava-pipeline-runner-cli.py`, que é o executor real da esteira. O CLI declarativo
`ava_pipeline.py` não participa desta execução e não foi alterado.

| # | Defeito | Correção |
| --- | --- | --- |
| C1 | D1 | `parse_and_write_outputs` reescrito com varredura única (`_FILE_ANY`): blocos fechados e o eventual bloco aberto final saem do mesmo passe, em ordem. O bloco cortado é gravado como `.PARTIAL` e devolvido em `incompletos`. Fatiamento em `.partN` agora só para HTML genuinamente grande — bloco fechado é íntegro por definição. |
| C2 | D2 | `run_step` reprova o passo quando `stop_reason == "max_tokens"` ou quando há incompletos; `val_ok=False` leva o passo a `skipped` em vez de `executed`, e `stop_reason`/`incomplete`/`detail` passam a constar nas métricas persistidas. |
| C3 | D3 | Seleção de contrato corrigida em `validate_phase_artifacts`. O contrato por-fase é de **fim de fase** (exige `traceability.json`, que só nasce na wave5b) e por isso **não** é aplicado a passo intermediário expandido — para esses vale o `outputs` do DAG. |
| C4 | D4 | `_expand_dag_phases` propaga `outputs` e `output_base`. Novo `validate_declared_outputs` confere os caminhos exatos por feature; artefato de tamanho zero conta como ausente. |
| C5 | D5 | Nova exceção `MissingMandatoryInput(Exception)` substitui o `SystemExit`. Handler dedicado no laço grava métricas, salva estado e atualiza o dashboard antes de abortar. |
| C6 | — | Novo `preflight_step_inputs`: o runner passa a conferir `inputs.mandatory` **antes** do despacho, com custo zero de inferência — dependência que só existia no CLI `ava_pipeline`, que não é usado aqui. |
| C7 | — | `_abort_pipeline` inicializado antes do laço: os ramos de pulo/aborto alcançavam `if _abort_pipeline:` sem passar pela atribuição, levantando `NameError` no primeiro passo pulado. |
| C8 | D6 | Heartbeat do dashboard: `_RUN_CTX` + `status_heartbeat()`, chamado de dentro dos dois laços de streaming (Anthropic e OpenAI) e estrangulado em 3 s. O passo em voo passa a exibir relógio corrente e saída acumulada (`~12.000 out`). Heartbeat também após a expansão do DAG e na varredura de retomada. |
| C9 | D7 | `_mark_executed()` remove a fase de `skipped`/`aborted` ao registrar execução bem-sucedida, e evita duplicata em `executed`. O `runner-state.json` do `nopcommerce-04` foi saneado com a mesma regra. |

### Verificação do parser contra os logs reais

| Caso | `plan.md` | `plan-graph.json` | Veredito |
| --- | --- | --- | --- |
| 003 (14:45, truncado) | fechado, 102.533 chars → gravado íntegro | aberto+último, 82.103 chars → `.PARTIAL` | passo **reprovado** |
| 004 (22:30, completo) | fechado, 73.652 chars | fechado, 72.241 chars | passo **aprovado** |
| sintético, corpo com `-->` | fechado | aberto | classificação correta |

Antes da correção, o caso 003 produzia "4 artefatos, `val_ok: true`".

### Verificação do preflight contra o estado real

```
F3S:planning:003-w2-medium-complexity-bcs   plan.md, plan-graph.json     ok
F3S:tasks:003-w2-medium-complexity-bcs      task-fragment.json           BLOQUEADO: plan-graph.json
F3S:compliance                              compliance-report.md, …      BLOQUEADO: tasks.md, traceability.json
```

Bloqueio exatamente nos passos esperados, com estado salvo e dashboard fechado.

### Verificação do heartbeat

Simulando `F3S:planning:003` em voo, com 9 passos já executados:

| Decorrido | Saída acumulada | Linha do passo |
| --- | --- | --- |
| 12 s | 3.000 chars | `Executando… · 12s · ~750 out` |
| 254 s | 48.000 chars | `Executando… · 4.2m · ~12.000 out` |
| 700 s | 190.000 chars | `Executando… · 11.7m · ~47.500 out` |

Estrangulamento: 50.000 chamadas em 2,87 s produziram **2** escritas em disco. Sem `_RUN_CTX`
registrado, a função é no-op absoluto — o dashboard nunca pode derrubar a execução (IV3).

---

## 5. Desbloqueio do `nopcommerce-04` — RESOLVIDO

`F3S:planning:003-w2-medium-complexity-bcs` foi re-executado em **2026-08-18 23:46** e concluiu
corretamente:

| Evidência | Valor |
| --- | --- |
| `plan-graph.json` | 102.091 bytes, ambos os blocos `FILE` fechados (L595→L2711) |
| `plan.md` | 88.701 bytes, bloco fechado (L26→L593), **sem** split em `.partN` |
| Artefatos no relatório | 2 (contra 4 na rodada defeituosa das 14:45) |
| `.PARTIAL` em disco | nenhum |

Estado atual: **12/20 passos**, 0 pulados. Próximo passo pendente: `F3S:tasks:003`.

⚠️ **Não** rodar `src/shared/tools/reconstruct_runner_state.py`: ele reconstrói o estado a partir
dos relatórios `.md` e não distingue a rodada defeituosa das 14:45 da correta das 23:46.

Limpeza ainda pendente: os resíduos `plan.part1.md`, `plan.part2.md` e
`plan.MERGE-INSTRUCTIONS.md` das features 002, 003 e 004 continuam em disco. Não são lidos por
nada — os `plan.md` unificados estão corretos — mas confundem inspeção futura.

---

## 6. Risco residual

O `plan-graph.json` continua sendo produzido por LLM, disputando o mesmo orçamento de 64k tokens
com o `plan.md`. As correções garantem que a falha seja **detectada no produtor**, não que ela
deixe de ocorrer. Mitigações estruturais estão registradas como trabalho futuro na spec 041:
separar a emissão do grafo em despacho próprio, ou derivá-lo deterministicamente das seções 3, 4
e 9 do `plan.md`.

---

## 7. Desdobramento — bloqueio no compilador e no exit gate (2026-08-19)

Com o `plan-graph.json` da 003 regenerado, a F3S avançou até
`F3S:tool:speckit-task-compile`, que **abortou**. A investigação revelou dois
defeitos adicionais e uma classe de dados quebrados.

### D8 — Compilador exigia cópia verbatim de tabela grande

```
ERRO: T-MED-014: source_refs diverge do plano para
      backend/src/Modules/Media/Media.Application/DTOs/UploadPictureResponse.cs
```

`planning-agent.md:64` declara o `plan-graph.json` como *"autoridade para grupos,
ownership de arquivos, produces, consumes e dependências"*, e `tasks-agent.md:211-215`
manda o agente de tasks **recopiar** esses campos para o `task-fragment.json`. O
compilador então exigia igualdade exata dessa cópia — `source_refs` inclusive por
**ordem** (`speckit_task_compiler.py:219`), enquanto `produces`/`consumes` já eram
comparados como conjunto: incoerência interna.

Na prática isso pedia que a LLM reproduzisse verbatim uma tabela de 90 a 155 linhas
num turno com teto de saída. É o mesmo modo de falha da ISSUE-004: tabela
determinística grande gerada por inferência.

Medição em `nopcommerce-04`, 302 entries:

| Divergência | Qtd |
| --- | --- |
| `source_refs` (conjunto, não só ordem) | 26 |
| `produces` / `consumes` | 17 |
| `action` / `task_type` | 0 |

### D9 — Exit gate reprovava os scaffolds da própria esteira

`f4s_scaffold_injector.py` (wave5a) cria `000-scaffold-{stack}` como features
transversais de W0 e **não** altera o `wave-spec-manifest.json`. O exit gate
(wave7) computa `extra = actual - expected` sobre as pastas de `specs/` e não tinha
isenção, então reprovava a saída do passo imediatamente anterior do mesmo DAG:

```
"pastas fora do manifesto: 000-scaffold-angular, 000-scaffold-dotnet"
```

O compilador já trazia a isenção (`speckit_task_compiler.py:150-155`); o gate não.

### Dados quebrados — irredutível por código

Não é defeito de ferramenta; exige regerar artefato:

| Feature | Defeito | Produtor a regerar |
| --- | --- | --- |
| 002-w1-low-complexity-bcs | `G-SECURITY-APP` declarado na seção 3 sem **nenhum** arquivo na seção 4; fragment inventou 15 arquivos em 5 grupos | `ava-speckit-planning`, depois `ava-speckit-tasks` |
| 003-w2-medium-complexity-bcs | plano tem 154 arquivos, fragment cobre **87** — 67 sem task, espalhados pelos 12 grupos | `ava-speckit-tasks` |
| 004-w3-high-complexity-bcs | fragment traz 41 arquivos ausentes do plano, em 9 grupos | `ava-speckit-planning` ou `ava-speckit-tasks` |

Observação adicional: a 004 usa raiz `src/`, `frontend/`, `tests/`, enquanto 002 e
003 usam `backend/`. Inconsistência de layout entre features do mesmo projeto,
produzida pelo mesmo agente.

### Correções aplicadas

| # | Defeito | Correção |
| --- | --- | --- |
| C10 | D8 | Campos de arquivo (`action`, `task_type`, `source_refs`, `produces`, `consumes`) passam a ser **lidos do plano**, que o contrato já declara autoridade. A cópia do fragment é reconciliada e contabilizada em `traceability.json.reconciled_from_plan` — nunca silenciada. `group` continua erro duro: define escalonamento e cobertura. |
| C11 | — | Nova checagem de coerência interna do plano: grupo declarado sem nenhum arquivo falha no **produtor**, com mensagem nomeando a feature e o agente. Não é restrição nova — tal grupo já falharia depois em `grupos do plano sem task`, só que com mensagem inútil. |
| C12 | — | `target_file fora do plano` e `arquivos do plano sem task` passam a informar a contagem total, o resumo por feature e **qual agente regerar**. |
| C13 | D9 | Exit gate isenta `000-scaffold-*` de `extra`, espelhando a isenção que o compilador já tinha, e passa a exigir `spec.md` + `plan-graph.json` + `task-fragment.json` não vazios em cada scaffold presente. |

### Verificação

Suíte sintética do gate (projeto de teste isolado):

| Cenário | Veredicto |
| --- | --- |
| scaffold + pasta estranha | reprova, citando só `zz-pasta-estranha` |
| só scaffold | **aprova** |
| scaffold com artefato vazio | reprova, citando `000-scaffold-dotnet/plan-graph.json` |
| feature não-codegen sem `spec.md` | reprova |

Compilador em `nopcommerce-04`: a classe `source_refs`/`produces`/`consumes`
deixou de bloquear; o erro agora é `grupos declarados sem arquivos na seção 4 do
plano: G-SECURITY-APP. Regere o plano (ava-speckit-planning) de:
002-w1-low-complexity-bcs` — que é o defeito real, apontando o produtor certo.

---

## 8. Diagnóstico completo, prevenção e reparo (2026-08-19)

### O problema de descobrir um bloqueio por execução

`compile_project` para no primeiro erro. Cada correção revelava o próximo, e foram
necessárias quatro sondas para chegar ao fundo: `source_refs` → grupo sem arquivos →
`trace_id` divergente → múltiplos produtores. Isso é caro e dá a impressão falsa de
que cada erro é o último.

### D10 — `trace_id` sorteado pelo scaffold injector

`f4s_scaffold_injector.py:164`:

```python
trace_id = project_config.get("trace_id") or f"trace-{uuid.uuid4().hex[:12]}"
```

O `project-config.yaml` não declara `trace_id`, então o injetor **sorteava um UUID novo
a cada execução**. Duas consequências: os 4 artefatos de scaffold divergiam dos 6 de
domínio, e o compilador exige um único `trace_id` em todo o conjunto; e a saída de um
passo declaradamente determinístico era irreprodutível.

### D11 — "exatamente 1 produtor" incompatível com arquitetura em camadas

O compilador exigia exatamente um produtor por token consumido. Em camadas, `api:X` é
produzido legitimamente por dois arquivos: o Service (`Application/Services`) implementa
e o Controller (`API/Controllers`) expõe. Dos 11 casos multi-produtor do `nopcommerce-04`,
9 são desse tipo.

### Correções aplicadas

| # | Defeito | Correção |
| --- | --- | --- |
| C14 | — | Comando `diagnose` no compilador: roda todas as checagens **sem parar**, cada achado com `code`, `severity`, `message`, `root_cause` e `fix`. `--plans-only` limita ao que depende só dos planos. |
| C15 | — | **Gate do produtor**: nova wave4a no DAG (`speckit-plan-validate`, `blocking: true`) entre planning e tasks. Um plano incoerente falha ali, com custo zero de inferência, em vez de condenar os despachos da wave5. |
| C16 | D10 | `_inherit_trace_id()`: herda dos plan-graphs de domínio → manifesto → project-config → derivação estável por hash. Nunca sorteia. O passo voltou a ser idempotente. |
| C17 | D11 | Consumidor passa a depender de **todos** os produtores (ordenação conservadora) em vez de exigir exatamente um. Zero produtores continua erro duro. Multi-produtor sai em `traceability.json.multi_producer_tokens` e como achado `P003`/`P005`. |
| C18 | — | `explain_failure()` no runner: ao falhar um passo, imprime traceback completo, **CAUSA RAIZ** traduzida e **PRÓXIMO PASSO** com o comando exato. Nove tools têm causa mapeada; erros de rede e timeout são reconhecidos; o resto cai num default que aponta o `diagnose`. Falha de tool agora também grava estado. |
| C19 | — | `speckit_plan_repair.py`: ferramenta de recuperação (dry-run por padrão) que injeta no plano os arquivos que só o fragment tem. Nunca remove nem altera linha existente. |
| C20 | — | Guardrails do `planning-agent.md`: cinco regras novas correspondendo a P001, P002, P004 e P009, com a nota de que a wave4a as verifica antes da wave5. |

### Códigos do diagnóstico

| Código | Severidade | Significado |
| --- | --- | --- |
| `P001` | erro | grupo declarado sem nenhum arquivo na seção 4 |
| `P002` | erro | `consumes` sem nenhum produtor no conjunto de planos |
| `P003` | aviso | token produzido pelo par legítimo Service + Controller |
| `P004` | erro | `produces` contaminado — `contract:Foo` fora do arquivo `Foo.*` |
| `P005` | aviso | múltiplos produtores sem correspondência de nome |
| `P006` | erro | id de grupo duplicado entre planos |
| `P009` | aviso | raiz de caminho inconsistente entre features |
| `F001` | erro | `target_file` do fragment fora do plano |
| `F002` | erro | arquivo do plano sem task |
| `F004` | erro | `task_id` duplicado entre fragments |
| `F005` | erro | `depends_on` para task inexistente |
| `F006` | erro | `spec_id`/`plan_id`/wave divergentes entre plano e fragment |
| `X001` | erro | `trace_id` divergente no conjunto |

### Resultado no `nopcommerce-04`

| Momento | Erros | Avisos |
| --- | --- | --- |
| antes | 13 | 12 |
| após `trace_id` unificado + regra multi-produtor | 13 | 12 |
| após `speckit_plan_repair --apply` (56 arquivos em 002 e 004) | **1** | 14 |

O único erro restante é `F002`: o fragment da `003-w2-medium-complexity-bcs` cobre 87 dos
154 arquivos do plano. Subcobertura do agente de tasks — exige regeração por inferência,
não há reparo determinístico possível (task carrega `task_id`, `title`, `acceptance` e
`verify_command`, que o plano não tem).

O gate da wave4a passa: **0 erros** nos planos.

Backups dos planos originais de 002 e 004 ficaram no scratchpad da sessão
(`bkp-002-plan-graph.json`, `bkp-004-plan-graph.json`).

### Avisos que permanecem (não bloqueiam)

- `P005` ×2 — `OrdersController.cs` (004) declara produzir `api:CapturePayment` e
  `api:RefundPayment`, que pertencem ao Payments (003). Contaminação cross-feature real,
  mas agora não fatal. Vale limpar ao regerar o plano da 004.
- `P009` ×1 — a 004 usa raiz `src/`, enquanto 002 e 003 usam `backend/`.

---

## 9. Por que a 003 subcobriu — e o que muda antes de regerar (2026-08-19)

Antes de reexecutar `ava-speckit-tasks` para a `003`, as métricas persistidas
descartaram a hipótese óbvia:

| Passo | tokens de saída | teto | entries | `stop_reason` |
| --- | --- | --- | --- | --- |
| `tasks:002` | 61.910 | 64.000 | 139 | end_turn |
| `tasks:004` | 56.092 | 64.000 | 132 | end_turn |
| **`tasks:003`** | **38.417** | 64.000 | **87** de 154 | end_turn |

**Não foi truncamento.** O agente encerrou por conta própria com 40% do orçamento
sobrando. Aumentar `PHASE_MAX_TOKENS` não teria efeito, e uma reexecução sem mudança
de contrato repetiria o comportamento.

### D12 — Fragment obrigado a recopiar 41% de payload morto

A correção C10 fez o compilador ler `action`, `task_type`, `source_refs`, `produces` e
`consumes` do `plan-graph.json`. Mas `_validate_task` continuava **exigindo** esses
campos no fragment, e o `tasks-agent.md` continuava mandando copiá-los — incoerência
introduzida pela própria C10.

Medição no fragment da 003:

| Métrica | Valor |
| --- | --- |
| entries | 87 |
| JSON total | 94.749 chars (~23.7k tokens) |
| campos recopiados | 38.910 chars (~9.7k tokens) — **41%** |
| por entry | 1.089 chars, dos quais 447 de recópia |

Sem a recópia, as 154 entries caberiam em ~98.7k chars (~24.7k tokens) — praticamente
o mesmo custo que as 87 têm hoje.

### Correções

| # | Defeito | Correção |
| --- | --- | --- |
| C21 | D12 | `_validate_task` passa a exigir só o que o fragment é autoridade: `task_id`, `title`, `group`, `target_stack`, `target_file`, `acceptance`, `verify_command`, `priority`, `story_points`, `depends_on`, `depends_on_groups`. Os cinco campos de arquivo são aceitos se vierem (fragments antigos seguem válidos) e reconciliados a partir do plano. |
| C22 | — | `tasks-agent.md`: seção "Cobertura total é contada, não estimada" — contar `files[]` do plano, declarar o número, emitir exatamente essa quantidade e conferir antes de fechar, com o caso da W2 citado nominalmente. E seção "Não recopie o que o plano já declara", listando os campos a omitir. |

Regressão verificada: fragments existentes (que ainda recopiam) continuam válidos; entry
enxuta sem os cinco campos é aceita; `acceptance` vazio continua reprovando.

### Limitação operacional

O runner não pode ser dirigido por script: `safe_input` usa `msvcrt.getwch()`, que lê do
buffer do console e **ignora o stdin** por desenho ("Evita completamente o buffer de linha
do stdin do PowerShell"). Despachar a wave5 via `ava_pipeline`/`sdk_engine` seria pior: esse
caminho usa `foundry.max_tokens` = 32.768, metade do teto da F3S. A regeração precisa ser
disparada pelo operador no console.

---

## 10. Compilação destravada e checks determinísticos (2026-08-19)

A regeração do fragment da `003` com o contrato C21/C22 produziu **156 entries cobrindo
os 154 arquivos do plano** — contra 87 antes. A mudança funcionou.

Sobraram 2 entries a mais: `ICustomerReader.cs` e `IPasswordHasher.cs` em caminhos locais
de módulo. **Não eram arquivos faltantes — eram duplicatas.** O plano já declara ambos os
contratos em `Shared/Shared.Application/Interfaces/`, com tasks `T-W2S-001` e `T-W2S-004`.
Reparo: remover as 2 entries e redirecionar `depends_on` de 4 tasks para os ids canônicos.

Resultado: `diagnose` **0 erros**, compilador **427 tasks**, ledger inicializado, 5 `tasks.md`
gerados, exit gate aprovando 5 dos 6 itens.

### D13 — Scaffold com âncora fabricada e spec sem as 6 seções

`f4s_scaffold_injector.py` declarava `source_refs: [{artifact: architecture-blueprint.md,
anchor: "SCAFFOLD"}]` — âncora que nunca existiu naquele arquivo. E copiava o template do
scaffold como `spec.md`, sem as 6 seções literais que o readiness-gate C2 e o `CHK-SK-014`
exigem. As duas features de scaffold reprovavam checks que elas mesmas introduziam.

### D14 — `CHK-SK-006` rejeitava âncora em forma de slug

O check fazia busca por substring: `_norm(anchor) in _norm(conteudo)`. Uma âncora escrita
como slug (`3-modelo-de-domínio`) tem hífen onde o heading tem espaço e ponto
(`## 3. Modelo de Domínio`) e **nunca** casa literalmente. Das 121 referências reprovadas,
**56 eram falso negativo** — resolviam para um heading real.

### D15 — `CHK-SK-008` comparava notações diferentes

O check extraía `METHOD /path` do OpenAPI; as tasks referenciam `operationId`, que é a
convenção declarada nos guardrails de ambos os agentes (`api:{operationId}`) e o que o
`speckit_wave_manifest.py` extrai. As 19 operações do projeto apareciam **19/19 sem task**
estando todas cobertas.

### Correções

| # | Defeito | Correção |
| --- | --- | --- |
| C23 | D13 | `SCAFFOLD_ANCHOR` aponta para um heading do próprio `spec.md` do scaffold, que o injetor grava — sempre existente. `_secoes_readiness()` acrescenta as 6 seções em inglês ao `spec.md` gerado. |
| C24 | D14 | `_slug()` + `_headings_slug()`: o check aceita âncora literal **ou** slug de heading real. Slug inexistente continua reprovando. |
| C25 | D15 | `_operacoes_do_openapi()` devolve `operationId` quando existe; `METHOD /path` só como fallback para operação sem id, que aí é de fato irreferenciável. |

### Placar dos checks

| Momento | Falhas |
| --- | --- |
| primeira execução | 5/18 |
| após C23 (scaffold) | 4/18 |
| após C24 (slug) e C25 (operationId) | **3/18** |

### As 3 falhas restantes são conteúdo, não ferramenta

Deliberadamente **não** relaxadas — são exatamente o que esta camada existe para pegar:

| Check | Falha | Origem |
| --- | --- | --- |
| `CHK-SK-006` | 65 âncoras genuinamente inexistentes: `Section3-CatalogDomain`, `Section8-CrossBC`, `4.2-upload-de-imagem`, `DEC-027` | o planning inventou um esquema de nomes que não corresponde aos headings da spec |
| `CHK-SK-007` | `BR-ORDER-005` sem task | lacuna de cobertura |
| `CHK-SK-009` | 40 de 71 casos de teste sem task | lacuna de cobertura (formato dos `test_ids` confere; é lacuna real) |

`speckit-dependency-checks` é `blocking: true` na wave5b, então essas 3 ainda barram
compliance e exit gate. Exigem regerar os planos de 002/003 com âncoras reais e cobertura
de BR/TC — trabalho de inferência, sem reparo determinístico possível.

---

## 11. Âncoras: o que era falso negativo e o que é invenção real (2026-08-19)

Antes de regerar os planos, valia separar quanto do `CHK-SK-006` era defeito de conteúdo e
quanto era rigor indevido do matcher. Das 121 referências originalmente reprovadas:

| Classe | Qtd | Natureza |
| --- | --- | --- |
| slug de heading (`3-modelo-de-domínio` → `## 3. Modelo de Domínio`) | 56 | falso negativo |
| slug parcial (`4.1-calcular-imposto` → `### 4.1 Calcular Imposto (Tax)`) | 62 | falso negativo |
| esquema inventado (`Section3-CatalogDomain`, `Section8-CrossBC`) | ~26 | **real** |
| decisão inexistente (`DEC-026`, `DEC-027`, `DEC-028`) | ~10 | **real** |

A constituição do `nopcommerce-04` declara `DEC-001`..`DEC-025`. Os planos das três waves
citam `DEC-026`, `DEC-027` e `DEC-028` — decisões que nunca foram tomadas. Rastreabilidade
falsa, exatamente o defeito que a camada existe para impedir.

### D16 — Matcher de âncora rejeitava referência parcial legítima

`4.1-calcular-imposto` endereça `### 4.1 Calcular Imposto (Tax)`: a âncora cita a seção e
omite o sufixo entre parênteses. O matcher exigia igualdade de slug e reprovava.

### Correções

| # | Defeito | Correção |
| --- | --- | --- |
| C26 | D16 | `_ancora_resolve()`: aceita prosa literal, slug de heading, ou slug parcial cortado **em fronteira de segmento**. `Section3-CatalogDomain`, que não prefixa heading nenhum, continua reprovando — o corte é calibrado, não permissivo. |
| C27 | — | **`P010` no gate do produtor**: a verificação de âncora, que só existia no `CHK-SK-006` da wave5b, roda agora em `diagnose --plans-only` na wave4a. Âncora inventada reprova o plano que a criou, antes dos despachos de tasks. Implementação espelhada nos dois lados para garantir veredicto idêntico. |
| C28 | — | `planning-agent.md`: seção "Âncora é endereço, não rótulo" — as três formas aceitas, com os casos `Section*` e `DEC-026+` citados nominalmente. |

### Escopo real da regeração

Com o matcher calibrado, o `P010` isola o defeito por feature:

| Feature | Refs inválidas | Âncoras distintas |
| --- | --- | --- |
| 002-w1-low-complexity-bcs | 5 | `DEC-027`, `DEC-028` |
| 003-w2-medium-complexity-bcs | 30 | `DEC-026/027`, `Section2-Examples`, `Section3-{Catalog,Customers,Messages,Payments}Domain`, `Section6-ErrorHandling`, `Section8-*` |
| 004-w3-high-complexity-bcs | 1 | `DEC-027` |

A 003 concentra o problema: o agente cunhou um esquema `SectionN-Xxx` inteiro. A 002 e a 004
têm apenas citações a decisões inexistentes.

Estado que compila (427 tasks, `diagnose` 0 erros) preservado no scratchpad da sessão em
`estado-ok-427tasks/` antes de qualquer regeração.

---

## 12. Rodada de 19/08 03:00-03:30 — o que avançou e o que quebrou

O operador regerou os planos e os três fragments. Resultado por artefato:

| Passo | Hora | Resultado |
| --- | --- | --- |
| `planning:002` | 02:30 | **truncado** — `.PARTIAL` de 109 KB salvo, `plan-graph.json` preservado na versão de 01:04 |
| `planning:003` | 02:49 | **truncado** — `.PARTIAL` salvo |
| `planning:003` | 03:04 | OK — 121 arquivos (era 154) |
| `tasks:002` | 03:13 | OK — 139/139 |
| `tasks:003` | 03:21 | OK — 121/121 |
| `tasks:004` | 03:29 | OK — 132/132 |

Os dois `.PARTIAL` são a correção C1 funcionando em produção: antes, esses truncamentos
seriam descartados em silêncio e o `plan-graph.json` ficaria desatualizado sem aviso.
Cobertura plano×fragment ficou em **100% nas três features**, contra 87/154 antes de C21/C22.

⚠️ Efeito colateral a observar: `planning:002` truncou **depois** de gravar `plan.md` (02:30) e
**antes** de gravar `plan-graph.json`, que permaneceu na versão de 01:04. Os dois arquivos da
002 estão dessincronizados — o markdown é mais novo que o grafo.

### D17 — `task_id` colide entre features

`speckit-task-compile` abortou com `task_id duplicado entre fragments`. Treze colisões entre
`002-w1` e `003-w2`: `T-TST-001`..`T-TST-012` e `T-HOST-001`.

O agente de tasks usa prefixo escopado por bounded context para trabalho de domínio
(`T-CAT-*`, `T-MED-*`), mas prefixo **genérico** para trabalho transversal (`T-TST-*` para
testes de infraestrutura, `T-HOST-*` para hosted services). Cada wave reinicia a numeração
por conta própria, e o `task_id` é a chave do ledger e do grafo global.

### D18 — Serviço não declara o próprio contrato

Sete achados `P002` na 003: `ProductsController.cs` consome `contract:CatalogService`, e
`CatalogService.cs` **está** no plano mas declara produzir apenas seus `api:*` — não o
contrato da própria classe. Consumo órfão com produtor presente.

### Correções

| # | Defeito | Correção |
| --- | --- | --- |
| C29 | D17 | Reparo `--mode duplicate-task-ids`: mantém o id na feature de menor ordem e insere o id da wave como discriminador na seguinte (`T-TST-001` da W2 → `T-W2-TST-001`), reescrevendo os `depends_on` junto. Mensagem do compilador passa a listar quantos, quais e em que features, com o comando de reparo. Guardrail novo em `tasks-agent.md`: "`task_id` é único no PROJETO, não na feature". |
| C30 | D18 | Reparo `--mode orphan-contracts`: declara `contract:X` no arquivo cujo stem é `X`, quando alguém o consome e ninguém o produz. Só age quando existe **exatamente um** arquivo com aquele stem — havendo ambiguidade, recusa e reporta. |

### Estado após os reparos

```
diagnose  : 3 erros, 22 avisos   (era 23 erros)
compilador: 394 tasks
ledger    : 394 tasks
checks    : 15/18 verdes
```

Os 3 erros e as 3 falhas de check são a mesma coisa: **12 referências com âncora inventada**,
concentradas e nominalmente identificadas:

| Âncora | Refs | Onde |
| --- | --- | --- |
| `DEC-027` | 5 | 002: `QueuedEmailRetentionJob.cs`, `CommonModuleExtensions.cs`, `ActivityLogRetentionJob.cs` · 004: `RecurringOrderRenewalJob.cs` |
| `DEC-028` | 2 | 002: `GlobalExceptionHandler.cs`, `ProblemDetailsExtensions.cs` |
| `7-mudanças-de-banco` | 6 | 003: os 3 `DbContext.cs` e as 3 `*Configuration.cs` |

A constituição declara `DEC-001`..`DEC-025`. A spec 003 tem `## 7. Requisitos de Segurança`,
não uma seção de mudanças de banco. Nenhuma dessas 12 tem reparo determinístico: remapear
para outra decisão ou remover a referência é decisão de conteúdo, e inventar o alvo seria
produzir a rastreabilidade falsa que o `CHK-SK-006` existe para barrar.

Mais `CHK-SK-007` (`BR-ORDER-005` sem task) e `CHK-SK-009` (41 de 71 casos de teste sem task),
que são lacunas de cobertura já registradas.

---

## 13. task-compile destravado (2026-08-19 03:45)

### C31 — Reparo `--mode dead-refs`

As 12 âncoras inventadas (`DEC-027`, `DEC-028`, `7-mudanças-de-banco`) tinham reparo
determinístico que eu havia descartado cedo demais: em **todos** os 12 arquivos restava ao
menos uma referência válida depois de remover a inválida.

Remover uma âncora que não resolve não é maquiar o check — é o contrário. A citação aponta
para o vazio; apagá-la **aumenta** a exatidão da rastreabilidade, e o que sobra passa a ser
inteiramente verificável. Fabricação seria remapear para uma decisão arbitrária ou inventar
`DEC-026`..`DEC-028` na constituição.

Guarda-corpo: só remove se restar pelo menos UMA referência válida. Se a inválida for a
única, o arquivo ficaria sem rastreabilidade alguma — aí é decisão de conteúdo (a decisão
citada faltou na constituição, ou a citação está errada?) e a ferramenta recusa e reporta.
Nenhum dos 12 caiu nesse caso.

### Cadeia determinística da F3S, ponta a ponta

| Passo do DAG | Status |
| --- | --- |
| wave4a `speckit-plan-validate` | **OK** |
| wave5a `f4s-scaffold-inject` | **OK** |
| wave5b `speckit-task-compile` | **OK** — 394 tasks |
| wave5b `speckit-ledger-init` | **OK** — 394 tasks |
| wave5b `speckit-dependency-checks` | FAIL — 2 de 18 |
| wave7 `speckit-exit-gate` | 5 de 6 itens OK; falta `compliance-status.json` (passo de LLM) |

`diagnose`: **0 erros**, 22 avisos.

### Evolução

| Momento | diagnose | checks |
| --- | --- | --- |
| primeira execução | 13 erros | 5/18 falhas |
| após C10-C13 | 1 erro | 5/18 |
| após rodada 03:00-03:30 do operador | 23 erros | — |
| após C29/C30 (task_id, orphan contracts) | 3 erros | 3/18 |
| após C31 (dead-refs) | **0 erros** | **2/18** |

### As 2 falhas restantes

`CHK-SK-007` (`BR-ORDER-005` sem task) e `CHK-SK-009` (41 de 71 casos de teste sem task) são
lacunas de cobertura reais — os ids existem no catálogo e nenhuma task os referencia.
Cobri-las exige regerar plano/fragment com instrução explícita, ou decidir que a cobertura
parcial é aceitável no piloto. Preencher `rule_ids`/`test_ids` em tasks arbitrárias para
calar o check seria fabricar rastreabilidade — o oposto do que C31 faz.

---

## 14. Reprovação de qualidade passa a ser decisão do operador (2026-08-19)

### Problema

`speckit-dependency-checks` reprova por lacuna de **cobertura** — regra de negócio ou caso
de teste sem task. Isso é informação sobre a qualidade do que foi gerado, não corrupção de
artefato: o grafo compila, o ledger inicializa, a F4 consegue executar. Ainda assim a tool
abortava a esteira inteira, sem alternativa, por algo que o operador pode legitimamente
aceitar num piloto.

### C32 — `on_fail: confirm`

Política de falha declarada no DAG, seguindo o idioma `on_fail` que já existia nos gates
(`abort_f3s`, `block_f4`). Aplicada **apenas** a `speckit-dependency-checks`; todas as outras
tools mantêm o aborto como padrão, porque reprovam por corrupção de artefato.

Fluxo quando a tool marcada reprova:

1. o relatório completo da tool já saiu no terminal (o subprocess não é capturado);
2. `explain_failure()` imprime traceback, causa raiz e próximo passo;
3. `_confirmar_risco()` explica que a verificação é não-bloqueante por configuração, que a
   lacuna vai persistir, e pergunta: **seguir assumindo o risco, ou cancelar para corrigir?**
4. seguindo, a fase entra em `skipped` com `risk_accepted: true` e o motivo no
   `runner-state.json`; cancelando, a esteira para como antes.

Decisões de projeto:

- **A aceitação é registrada, não silenciosa.** Risco assumido sem rastro seria pior que o
  aborto: `risk_accepted` e `detail` ficam no estado persistido.
- **O dashboard distingue.** A fase aparece como `⚠️ Risco aceito`, não como `⏭ Pulado` —
  mostrar "Pulado" apagaria justamente o que precisa ficar visível.
- **`EOF`/`Ctrl+C` cancela.** Entrada interrompida não pode ser lida como consentimento.
- **Modo automático segue**, mas avisa e registra a aceitação como automática. Sem operador
  não há a quem perguntar, e o requisito é não bloquear.

Cobertura de teste do fluxo: `S`/`sim` → segue · `N`/`não` → cancela · resposta inválida →
repergunta · `EOF` → cancela · `auto_mode` → segue.

### Estado da F3S

| Passo | Resultado |
| --- | --- |
| wave4a `speckit-plan-validate` | OK |
| wave5a `f4s-scaffold-inject` | OK |
| wave5b `speckit-task-compile` | OK — 394 tasks |
| wave5b `speckit-ledger-init` | OK — 394 tasks |
| wave5b `speckit-dependency-checks` | 16/18 · **decisão do operador** |
| wave6 `compliance` | pendente (passo de LLM) |
| wave7 `speckit-exit-gate` | 5 de 6; falta `compliance-status.json` |

As 2 lacunas que restam — `CHK-SK-007` (`BR-ORDER-005`) e `CHK-SK-009` (41 de 71 casos de
teste) — continuam registradas como WI-21 e WI-22. Aceitá-las no piloto não as resolve; o
que muda é que a decisão fica explícita, registrada e visível no dashboard.

---

## 15. Compliance e graduação do aceite de risco (2026-08-19 04:18)

### D19 — Agente de compliance grava o nome e o schema do agente irmão

`F3S:compliance` rodou, emitiu os dois blocos `FILE` fechados, sem truncamento — mas gravou
`compliance-summary.json` em vez de `compliance-status.json`. O gate de saída (C4) reprovou o
passo com "outputs declarados no DAG não gravados".

`compliance-status.json` é o nome correto, concordado em cinco lugares, inclusive no **próprio
contrato do agente** (`compliance-agent.md:130,133,175,186,188`). O agente violou o que ele
mesmo declara.

Origem: contaminação pelo `security-compliance-agent` do módulo *deliverables*, que
legitimamente usa `security-compliance-summary.json`. Não veio só o nome — veio o schema:
o arquivo saiu com `compliance_gate`, `score`, `blockers`, `checks`, `metrics`,
`pending_decisions`, quando o contrato do speckit pede `verdict`, `constitution_items`,
`items_honored`, `findings[]`, `contradictions[]`.

Nenhum código lê os campos deste artefato — o gate confere existência e tamanho, e o
`artifact-map.yaml` o mapeia para a seção de summary. Renomear destravou; a divergência de
schema fica registrada.

### D20 — "Aceitar o risco" era grosso demais

A implementação inicial de `on_fail: confirm` marcava **toda** falha do
`speckit-dependency-checks` como confirmável. Mas a suíte também reprova por integridade de
referência (`CHK-SK-016`), ciclo no grafo (`CHK-SK-017`) e schema inválido (`CHK-SK-013`) —
nada disso alguém deveria poder aceitar. Um aceite indiscriminado teria deixado a F4 começar
sobre um grafo quebrado, que é precisamente o cenário que a spec 040 existe para impedir.

### Correções

| # | Defeito | Correção |
| --- | --- | --- |
| C33 | D19 | Artefato renomeado para `compliance-status.json`. `compliance-agent.md` ganha aviso nomeando a confusão: `*-summary.json` é do agente de segurança, com outro schema; não copie campos dele. |
| C34 | D20 | **Severidade por check.** `Reporter.record(..., blocking=False)` marca o check cuja reprovação é lacuna de qualidade. `Reporter.exit_code`: `0` tudo passou · `3` só lacunas · `1` há falha estrutural. Apenas `CHK-SK-007/008/009` (cobertura de BR, API e casos de teste) são não-bloqueantes. |
| C35 | — | `run_checks_detailed()` devolve o Reporter; `run_checks()` mantém o `bool` para os chamadores existentes (`build_summary_comprehensive.py`). `cli.main` passa a sair com `reporter.exit_code`. |
| C36 | — | `ava_pipeline.run_tool_step` anexa `returncode` à exceção — ler o código da mensagem seria frágil. O runner só oferece o aceite quando `on_fail: confirm` **e** o código é 3. |
| C37 | — | Exit gate propaga a graduação: suíte com exit 3 vira `SOFT_FAIL`, e o gate só devolve 3 se **não** houver artefato ausente, suíte estrutural reprovada nem checksum divergente. Artefato faltando continua sendo `FAIL` duro. |

Sem C34, o aceite de risco seria um cheque em branco. Com ela, o operador só pode aceitar
"faltou cobrir" — nunca "o grafo está quebrado".

### Estado da F3S

| Passo | Exit | Resultado |
| --- | --- | --- |
| wave4a `speckit-plan-validate` | 0 | OK |
| wave5a `f4s-scaffold-inject` | 0 | OK |
| wave5b `speckit-task-compile` | 0 | OK — 394 tasks |
| wave5b `speckit-ledger-init` | 0 | OK — 394 tasks |
| wave5b `speckit-dependency-checks` | **3** | 16/18 · só cobertura · **operador decide** |
| wave6 `compliance` | 0 | OK após renomear o artefato |
| wave7 `speckit-exit-gate` | **1** | 6/6 artefatos OK · `prototype_coverage` reprova |

### O bloqueio que resta

`CHK-PROTO-000`: **nenhuma spec de wave referencia o protótipo**. O projeto tem protótipo em
`outputs/tobe/prototype/`, o manifesto de waves inclui `screen-list.md` nas `sources` de cada
feature, e mesmo assim nenhuma das cinco `spec.md` cita tela alguma.

Não marquei como não-bloqueante. O aceite autorizado foi sobre cobertura de BR e casos de
teste; este é outro escopo, e a mensagem do check é específica sobre o que aconteceu da
última vez que passou batido: *"7 telas faltando e 13% de fidelidade"*. Numa migração com
frontend, gerar código sem que nenhuma tela tenha virado especificação é um risco de outra
ordem — e a decisão é do operador, não minha.

---

## 16. `PlanError` cru na expansão da F3S (2026-08-19)

### D21 — Traceback em vez de resposta

Rodar a F3S num projeto que ainda não passou pela F2 produzia duas páginas de traceback
terminando em:

```
pipeline_plan.PlanError: F3S sem manifesto de waves válido:
  wave-model.json ausente e wave-plan.md não contém waves parseáveis
```

`_expand_dag_phases` só capturava `ImportError`; `PlanError` subia até `main()` e matava o
processo. O operador ficava sem saber **quem produz** o `wave-model.json`, **qual fase**
rodar, nem **como conferir** depois.

Afeta 6 dos 7 projetos do repositório.

### A resposta já existia, separada em dois lugares

- O **gate de entrada** sabe QUAIS itens faltam (`artifact_gate_speckit.check_item`);
- O **DAG** declara QUEM produz cada um (`produced_by` em `pipeline-dag/*.yaml` e
  `ava-pipeline.yaml`) — 12 declarações que nunca haviam sido usadas para responder ao
  operador na hora do erro.

### Correções

| # | Correção |
| --- | --- |
| C38 | `_expand_dag_phases` captura a exceção e devolve 0 — o chamador já tratava esse retorno abortando a fase com dignidade. |
| C39 | `explicar_fase_nao_expandida()`: cruza o gate de entrada com o `produced_by` do DAG e devolve **causa raiz, agente produtor, comando e verificação**. |
| C40 | `_produtor_declarado()`: resolve artefato → agente varrendo os YAMLs. Casa caminho completo **ou** nome de arquivo, em fronteira de segmento — `plan.md` não casa com `wave-plan.md`. |
| C41 | `_numero_no_menu()`: converte a fase produtora no número do menu "Por Fase", e agrupa numa seleção única (`2 4 5`), que o menu aceita. |

### Duas classes distintas, instruções distintas

| Classe | Detecção | Instrução |
| --- | --- | --- |
| **ausente** | gate de entrada acusa itens faltando | rode a(s) fase(s) produtora(s) |
| **incoerente** | gate passa; artefatos existem e se contradizem | regere o artefato divergente — ou edite à mão, que é mais barato |

A segunda classe foi descoberta na verificação: `meu-erp-03` e `my-nop-ecommerce` **têm**
`wave-model.json` e `wave-plan.md`, e falham porque discordam entre si
(`W3: model=['BC-03'], plan=['BC-03','BC-04']`). Dizer "insumo ausente" ali seria mentira.

### Verificação

| Projeto | Resultado | Classe | Fases indicadas |
| --- | --- | --- | --- |
| nopcommerce-04 | **OK — 24 passos** | — | — |
| my-nop-ecommerce | tratado | incoerente | 4 |
| meu-erp-03 | tratado | incoerente | 4 |
| Meu-ERP | tratado | ausente | 2 4 5 |
| MeuERP-002 | tratado | ausente | 2 4 5 |
| nopcommerce | tratado | ausente | 2 4 5 |
| nopcommerce-03 | tratado | ausente | 4 5 |

Nenhum falso positivo: o projeto saudável continua expandindo.

### Regressão detectada em código de terceiros

Ao editar o runner (agora com 5.345 linhas, ~1.000 a mais que na sessão anterior), notei que
o guard de exit code do `on_fail: confirm` (C36) **desapareceu**. O bloco em ~5217 hoje testa
apenas `on_fail == "confirm"`, sem consultar o `returncode`. O efeito é o que C34 existia
para impedir: falha estrutural — grafo cíclico, referência quebrada — volta a ser aceitável
pelo operador. O exit code graduado continua funcionando do lado dos checks; falta o guard
no runner. Não reverti a alteração de terceiros; registro para decisão.
