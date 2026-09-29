# Guia — Esteira AS-IS em Repositórios Legados Grandes

> **Padrão conhecido.** Aplica-se a repositórios legados com **> 200 units** ou **> 100.000 LOC**,
> ou a qualquer projeto cujo `manifest.json` de compressão acuse **> 400.000 tokens**.
>
> Origem: `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md` · Implementação: `specs/030-asis-pipeline-context-budget-dispatch-guard`

---

## 1. O sintoma

A esteira **parece travada**. Não há erro, não há timeout, não há log novo — apenas silêncio
por 30 a 60 minutos, seguido de uma rajada de arquivos gravados, seguida de mais silêncio.
No fim, a esteira encerra (ou morre) com parte dos artefatos F1 ausentes.

Caso de referência — `processaERP-008` (363 units, 174.375 LOC, 4.254 regras de negócio):

| Métrica                   | Valor                                   |
| -------------------------- | --------------------------------------- |
| Wall time total            | 110,6 min                               |
| Extração AST (normal)    | 4m 14s                                  |
| Payload comprimido         | **761.376 tokens**                |
| Maior chamada de subagente | **3.700s (~62 min)**              |
| Artefatos F1 concluídos   | 11 / 19 (58%)                           |
| Rajada de retry            | 3 dispatches em 16s para o mesmo agente |

## 2. A causa

Não é lentidão de I/O nem falha de ferramenta. São quatro causas somadas:

1. **Sobrecarga de contexto (RC-1)** — cada `runSubagent` carregava os 9 artefatos comprimidos
   inteiros, mais o spec do agente, mais os resultados de tool. 800.000+ tokens por turno
   produzem latência de inferência de dezenas de minutos, e cada restart de subagente
   **reconstrói o mesmo contexto do zero**, sem ganho de conhecimento.
2. **Retry sem guard (RC-2)** — chamadas que retornavam cedo não eram detectadas; o
   orquestrador redespachava imediatamente, multiplicando o custo por 3×.
3. **Serialização indevida (RC-3)** — agentes sem dependência entre si (inventory, db-analyzer,
   documentation) foram despachados um após o outro em vez de em sequência de dispatch.
4. **Perda de continuação (RC-4)** — quando a chamada longa retornava, a sessão pai já havia
   perdido o contexto de continuação; os artefatos restantes nunca foram escritos, e nada
   reaproveitava os 11 já produzidos.

## 3. O que a esteira faz hoje (v2.22 do orquestrador)

| Mitigação                                  | Onde                                                                           | Efeito                                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| **M-1 · Slicing por agente**          | `§ Context Budget Gate` + `AGENT_ARTIFACT_SLICE` em `context_budget.py` | Cada agente recebe só os artefatos que consome — 60–90% menos contexto por dispatch            |
| **M-2 · Execução inline**           | `execution_mode: inline` acima de 400K tokens                                | Elimina a penalidade de reconstrução de contexto por subagente                                  |
| **M-3 · Recorte por bounded context** | `execution_mode: bc_scoped` acima de 700K tokens                             | 1 dispatch por BC via`module-partition.json` — cada chamada abaixo de 100K tokens              |
| **M-4 · Dispatch Guard**              | `§ Dispatch Guard` + `artifact_gate.py`                                   | Nenhum subagente é gasto por artefato que já existe; máx. 1 dispatch por agente por iteração |
| **M-5 · Dispatch paralelo**           | `dispatch_schedule.phase_a_wave2`                                            | Os 5 agentes da Wave 2 vão todos antes de processar qualquer output                              |
| **Resume**                             | Step 0.3 do orquestrador + Step 0.6 do`solution-delphi`                      | Uma esteira interrompida retoma só o que falta                                                   |

## 4. Antes de rodar — checklist do PM

```bash
# 1. Qual o volume real? (só funciona depois que a extração AST rodou)
python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project {PROJECT}

# 2. O que já existe em disco? (retomada / diagnóstico de esteira interrompida)
python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py --project {PROJECT} --all

# 3. Onde a esteira gastou o tempo? (reconstrói fases por mtime, aponta os gaps)
python docs/issues/perf_pipeline_ntp.py --project {PROJECT}
```

Leitura dos exit codes de `context_budget.py`: `0` = subagent (normal) · `1` = inline ·
`2` = bc_scoped · `3` = manifest ausente (Step 0 não rodou).

## 5. Ajuste fino por projeto

Os limiares são configuráveis em `projects/{PROJECT}/context/project-config.yaml` — nunca
hardcoded no agente (Art. I da Constituição):

```yaml
context_budget_inline_threshold: 400000     # acima disto → execução inline
context_budget_bc_scoped_threshold: 700000  # acima disto → 1 dispatch por bounded context
```

Reduzir o escopo também resolve — `scope_modules` restringe a análise a um subconjunto de
módulos e derruba o payload proporcionalmente:

```yaml
scope_modules: ["Financeiro", "Vendas"]     # em vez de "all"
```

## 6. Se a esteira parou no meio

1. **Não reexecute com `SA|FULL`** — isso apaga os outputs e joga fora o que já foi pago.
2. Rode `artifact_gate.py --project {PROJECT} --all` para ver o contrato F1 e o que falta.
3. Redispare o trigger normal (`SA` ou `FP`). O Step 0.3 (Resume Detection) pré-registra como
   `completed` tudo que já está em disco e a esteira despacha apenas os agentes pendentes.
4. Se um agente específico está faltando, o guard passa `artifacts_missing[]` no prompt — ele
   regenera só esses arquivos.

## 7. Sinais de que algo ainda está errado

| Sinal                                                    | Diagnóstico provável                                                                                            |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Bloco`🧮 CONTEXT BUDGET` não apareceu antes da Wave 2 | O orquestrador pulou o`evaluate_context_budget()` — violação da Regra Fundamental 10                         |
| Banner `🧮 Context Budget` não apareceu dentro do `solution-delphi` | Step 0.6 não rodou — o agente processará o payload completo sem escrita incremental; é simétrico ao sinal acima, mas ocorre **dentro** do agente de solução |
| Mesmo agente despachado 2× na mesma iteração          | Dispatch Guard não foi chamado — violação da Regra Fundamental 11                                             |
| `execution_mode: subagent` com total > 400K            | Limiares sobrescritos no`project-config.yaml`, ou `manifest.json` desatualizado                               |
| Gap > 30 min sem arquivo novo                            | Agente recebeu payload completo em vez da fatia — verificar se o prompt de dispatch trazia`ast_artifact_slice` |

## 8. Limitações conhecidas (v2.22)

As mitigações M-1 a M-5 estão implementadas, mas dois itens permanecem **em aberto** e podem
causar comportamento inesperado em cenários extremos:

| Limitação | Impacto prático | Plano |
| --------- | --------------- | ----- |
| **`bc_scoped` sem loop numerado em `solution-delphi`** — Step 0.6 instrui o agente a "percorrer os Steps 3-13 um BC por vez", mas esses steps não foram decompostos em sub-iterações numeradas | O agente interpreta a instrução corretamente na maioria dos casos, mas o loop não é auditável passo a passo; uma falha no meio de um BC não tem um ponto de retomada granular | Decompor em PBI seguinte após a primeira execução `bc_scoped` real fornecer dados de calibração |
| **Step 0.6 apenas para Delphi** — `solution-{vb,cobol,vbnet,powerbuilder}.md` não têm o Step 0.6 | Projetos não-Delphi sempre usam `execution_mode: subagent`, independentemente do volume de tokens comprimidos | Os demais agentes herdam a fatia via `AGENT_ARTIFACT_SLICE` (preparados para quando ganharem extração AST), mas inline/bc_scoped não ativam |

## 9. Referências

- `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md` — análise de causa raiz completa
- `specs/030-asis-pipeline-context-budget-dispatch-guard/` — spec, plan e tasks da correção
- `docs/module-partitioner-guide.md` — como o `module-partition.json` é produzido (base do M-3)
- `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` — `§ Context Budget Gate`, `§ Dispatch Guard`
