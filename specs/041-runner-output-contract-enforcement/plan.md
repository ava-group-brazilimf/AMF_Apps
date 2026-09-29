# Plan — Spec 041: Aplicação do contrato de saída no runner da esteira

## Constitution Check

- **Article II/X** — Nenhum contrato de agente muda; não há bump de versão de agente. A mudança é
  de enforcement no executor.
- **Article III** — O gate da F3S continua obrigatório; ganha um gate por-passo **antes** dele.
- **Article V** — Mensagens ao operador e documentação permanecem em pt-BR.
- **Article VIII** — `trace_id` e artefatos não são reescritos; o runner só grava o que o agente
  emitiu, mais o sufixo `.PARTIAL` quando o bloco não fechou.
- **Article XI** — Nenhum agente novo.
- **IV3** — Degradação, nunca quebra: preflight indisponível (manifesto ilegível) não vira falso
  bloqueio; segue para `load_context`, que decide.
- **IV7** — Somente stdlib; nenhuma dependência nova.

## Architecture

O ponto de aplicação é `pipeline_runner 19.py`. A declaração já existia e era descartada; o
trabalho é conduzi-la até dois gates novos, um antes e outro depois do despacho.

```text
pipeline-dag/F3S.yaml
   outputs: [specs/{feature}/plan.md, specs/{feature}/plan-graph.json]
   inputs.mandatory: [...]
            |
            v
pipeline_plan.dag_steps()          já resolvia {feature} e emitia `outputs`/`output_base`
            |
            v
_expand_dag_phases()               [C4] passa a PROPAGAR outputs/output_base
            |
            +--> preflight_step_inputs()      [C6] GATE DE ENTRADA (custo zero)
            |         bloqueado -> aborted + estado salvo + dashboard fechado
            v
        run_step()
            |
            +--> parse_and_write_outputs()    [C1] varredura única; .PARTIAL
            |         retorna (escritos, incompletos)
            |
            +--> validate_phase_artifacts()   [C3] contrato de fase só se não-expandido
            |      + validate_declared_outputs()  [C4] GATE DE SAÍDA por feature
            |
            +--> [C2] truncado ou incompleto -> val_ok=False
                       val_ok=False -> `skipped`, nunca `executed`
```

### Decisões de projeto

**Por que uma varredura única no parser.** Duas varreduras independentes — uma para blocos
fechados, outra para abertos — criaram o bug: a segunda era condicionada ao fracasso total da
primeira. Uma regex com o marcador de fechamento em grupo **opcional** (`_FILE_ANY`) devolve
blocos fechados e abertos na ordem original, e o grupo de captura diz sem ambiguidade se fechou.
Heurística textual (`endswith("-->")`) foi rejeitada: corpo HTML legítimo contém `-->`.

**Por que só o último bloco pode ser tratado como truncado.** Um bloco sem fechamento no meio da
resposta significa que o modelo esqueceu o marcador — o conteúdo está completo, porque o próximo
`<!-- FILE:` começou. Tratar esse caso como truncado descartaria artefato válido. Ele é gravado
normalmente, com aviso `[SEM-/FILE]`.

**Por que fatiar em `.partN` deixou de depender de `truncated`.** Bloco fechado é íntegro por
definição; o corte atingiu outro bloco. O comportamento antigo fatiava o `plan.md` completo de
104 KB só porque a resposta como um todo fora cortada. Mantido apenas o fatiamento de HTML
genuinamente grande (> 80 KB), que existe por outro motivo (limite de renderização).

**Por que o contrato de fase não se aplica a passo expandido.** `PHASE_ARTIFACT_CONTRACT["F3S"]`
exige `traceability.json`, produzido pela wave5b. Aplicá-lo a `F3S:constitution` reprovaria todo
passo anterior à wave5b. Para passo expandido vale o `outputs` do DAG, que é preciso por feature.
Um fallback ingênuo `phase.split(":")[0]` teria sido pior que o bug original.

**Por que o preflight vive no runner.** `ava_pipeline.preflight_inputs` existe e funciona, mas o
CLI declarativo não é o executor desta esteira. A dependência de insumos obrigatórios precisa ser
conferida onde o fluxo é de fato controlado.

**Por que exceção própria em vez de `SystemExit`.** O laço captura `Exception`; `SystemExit`
herda de `BaseException` e escapava, matando o processo antes de `_save_runner_state`,
`_write_status_html(done=True)` e `_finalize_runner_state`. `MissingMandatoryInput(Exception)`
carrega `phase`, `agent` e `missing` para as métricas persistidas.

**Por que o heartbeat vive no laço de streaming.** O auto-refresh do HTML é do navegador; quem
escreve o arquivo é o runner. Entre despachos ele escrevia bem, mas *durante* um passo não havia
nenhum ponto de execução que voltasse ao dashboard — exceto o laço que consome tokens. É o único
lugar que roda continuamente e sabe o quanto já saiu. O estrangulamento de 3 s espelha o intervalo
do `<meta refresh>`: escrever mais rápido que isso não seria visto por ninguém.

**Por que `_RUN_CTX` em vez de passar as listas para `run_step`.** `run_step` não conhece
`active_steps`/`executed`/`skipped`/`aborted`, e alargar sua assinatura para atravessar
observabilidade contamina a função com estado do laço. O dict guarda as **mesmas referências** —
as listas são mutadas no lugar por `append` e por atribuição de fatia — então enxerga cada avanço
sem sincronização. O único ponto que as reatribui (descarte de estado por manifesto divergente)
atualiza `_RUN_CTX` explicitamente.

**Por que artefato de zero byte conta como ausente.** Um bloco `FILE` cortado logo após o
cabeçalho gravava arquivo vazio, que satisfazia qualquer checagem de existência e escondia a
falha do consumidor seguinte.

### Semântica de falha

Insumo obrigatório ausente **aborta a fase**, não apenas o item do fan-out. É deliberado: as waves
5a/5b/6/7 são `blocking: true` e o `speckit_task_compiler` exige `plan-graph.json` **e**
`task-fragment.json` para *todas* as features `codegen`. Continuar com as demais features
produziria um segundo modo de falha, mais tarde e menos legível. A diferença em relação ao
comportamento anterior é que o aborto agora é limpo: estado salvo, dashboard fechado, retomada
possível.

## Trabalho futuro (fora do escopo desta spec)

As correções garantem **detecção no produtor**, não que o truncamento deixe de ocorrer. O
`plan-graph.json` continua disputando os 64k tokens de saída com o `plan.md`. Duas saídas
estruturais, em ordem de preferência:

1. **Derivação determinística** — as seções 3, 4 e 9 do `plan.md` já contêm grupos, arquivos e
   ordem topológica. Um `speckit_plan_graph_builder.py` poderia produzir o JSON sem inferência,
   eliminando a classe inteira de falha e alinhando o grafo ao que a spec 040 chama de
   "determinístico".
2. **Despacho próprio** — separar wave4 em `planning` (markdown) e `plan-graph` (JSON), cada um
   com seu orçamento de saída.
