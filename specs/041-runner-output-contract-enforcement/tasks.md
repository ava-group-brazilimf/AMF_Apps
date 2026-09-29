# Tasks — Spec 041: Aplicação do contrato de saída no runner da esteira

> Status: **correções aplicadas e verificadas contra os logs reais do `nopcommerce-04`**.
> Pendente: re-execução do `F3S:planning:003` (consome inferência; requer decisão do operador).
> Ordem causal: a propagação da declaração precede os gates que a consomem.

## 1. Governança

- [x] T-001 — Registrar `docs/issues/ISSUE-004-speckit-plan-graph-perda-silenciosa.md` com
      linha do tempo, evidência dos blocos `FILE` e os cinco defeitos
- [x] T-002 — Criar `spec.md` com BDD nominal, truncamento, edges e retomada
- [x] T-003 — Criar `plan.md` com Constitution Check, decisões de projeto e trabalho futuro

## 2. Propagação da declaração

- [x] T-010 — `_expand_dag_phases`: copiar `outputs` e `output_base` do `dag_steps` para o passo
- [x] T-011 — Verificar que `pipeline_plan.dag_steps` já resolve `{feature}` nos outputs
      (nenhuma alteração necessária em `pipeline_plan.py`)

## 3. Gate de entrada

- [x] T-020 — Criar `MissingMandatoryInput(Exception)` com `phase`, `agent` e `missing`
- [x] T-021 — Trocar o `raise SystemExit` de `load_context` pela nova exceção
- [x] T-022 — Criar `preflight_step_inputs`: confere `inputs.mandatory` sem gastar inferência;
      degrada para `ok=True` se o manifesto estiver indisponível (IV3)
- [x] T-023 — Chamar o preflight no laço principal, antes do despacho, gravando métricas,
      estado e dashboard antes de encerrar
- [x] T-024 — Adicionar handler dedicado de `MissingMandatoryInput` no laço, antes do
      `except Exception`, como rede de segurança

## 4. Parser de artefatos

- [x] T-030 — Criar `_FILE_ANY` com marcador de fechamento em grupo de captura opcional
- [x] T-031 — Reescrever `parse_and_write_outputs` em varredura única, retornando
      `(escritos, incompletos)`
- [x] T-032 — Gravar bloco cortado como `.PARTIAL` em vez de descartá-lo
- [x] T-033 — Restringir o fatiamento `.partN` a HTML grande; bloco fechado nunca é fatiado
- [x] T-034 — Avisar `[SEM-/FILE]` para bloco sem fechamento no meio da resposta, gravando-o

## 5. Gate de saída

- [x] T-040 — Criar `validate_declared_outputs`; artefato de zero byte conta como ausente
- [x] T-041 — Corrigir a seleção de contrato em `validate_phase_artifacts`: contrato de fim de
      fase não se aplica a passo expandido
- [x] T-042 — Integrar `declared_missing` ao resultado da validação
- [x] T-043 — `run_step`: reprovar em truncamento/incompletos e expor
      `stop_reason`, `incomplete` e `detail` nas métricas persistidas

## 6. Robustez do laço

- [x] T-050 — Inicializar `_abort_pipeline` antes do laço (`NameError` latente no primeiro
      passo pulado pelo operador)

## 6a. Observabilidade em tempo real

- [x] T-055 — Criar `_RUN_CTX` e `status_heartbeat()` com estrangulamento de 3 s e no-op
      quando o contexto não está registrado
- [x] T-056 — Adicionar `live` a `_write_status_html`: relógio corrente e saída acumulada na
      linha do passo em voo, e no badge do topo
- [x] T-057 — Chamar o heartbeat no laço de streaming Anthropic
- [x] T-058 — Propagar `on_chunk` para `_stream_openai` e chamar o heartbeat no caminho OpenAI
- [x] T-059 — Heartbeat forçado antes do 1º token (TTFT e retries podem levar minutos)
- [x] T-05A — Heartbeat após a expansão do DAG e na varredura de retomada
- [x] T-05B — `_mark_executed()`: execução bem-sucedida remove a fase de `skipped`/`aborted`
      (passo reexecutado na retomada ficava nas duas listas e exibia "Pulado")
- [x] T-05C — Sanear o `runner-state.json` do `nopcommerce-04` com a mesma regra

## 7. Verificação

- [x] T-060 — `py_compile` do runner
- [x] T-061 — Parser contra o log real de `F3S:planning:003` (14:45): `plan.md` fechado íntegro,
      `plan-graph.json` aberto+último com 82.103 chars → `.PARTIAL`, passo reprovado
- [x] T-062 — Parser contra o log real de `F3S:planning:004` (22:30): ambos fechados, aprovado
- [x] T-063 — Caso sintético com `-->` no corpo: classificação de fechamento correta
- [x] T-064 — Preflight contra o estado real do `nopcommerce-04`: bloqueio exatamente em
      `F3S:tasks:003` (plan-graph.json) e `F3S:compliance` (tasks.md, traceability.json)
- [x] T-064a — Heartbeat: linha em voo a 12 s/254 s/700 s renderiza relógio e tokens corretos
- [x] T-064b — Estrangulamento: 50.000 chamadas em 2,87 s → 2 escritas; sem `_RUN_CTX` → no-op
- [x] T-065 — Re-executar `F3S:planning:003-w2-medium-complexity-bcs`: concluído em 23:46 com
      2 artefatos, ambos os blocos fechados, `plan-graph.json` de 102.091 bytes, sem `.PARTIAL`
      e sem split em `.partN`
- [ ] T-066 — Concluir a F3S do `nopcommerce-04` até o exit gate (fecha `040/T-053`)

## 8. Limpeza pendente

- [ ] T-070 — Remover os resíduos `plan.part1.md`, `plan.part2.md` e `plan.MERGE-INSTRUCTIONS.md`
      das features 002, 003 e 004 do `nopcommerce-04` (o `plan.md` unificado está correto).
      Não executado automaticamente: são artefatos de projeto, a remoção é decisão do operador.

## 9. Desdobramento — compilador e exit gate (2026-08-19)

- [x] T-080 — Compilador: campos de arquivo (`action`, `task_type`, `source_refs`,
      `produces`, `consumes`) lidos do plan-graph, que o contrato já declara autoridade;
      cópia divergente do fragment é reconciliada e contabilizada em
      `traceability.json.reconciled_from_plan`, nunca silenciada
- [x] T-081 — `group` mantido como erro duro (define escalonamento e cobertura de grupos)
- [x] T-082 — `_source_refs_or_empty()`: comparação tolerante para diagnóstico
- [x] T-083 — Checagem de coerência interna do plano: grupo declarado sem arquivos falha
      no produtor, nomeando feature e agente
- [x] T-084 — Mensagens de `target_file fora do plano` e `arquivos do plano sem task`
      passam a informar contagem, resumo por feature e qual agente regerar
- [x] T-085 — Exit gate isenta `000-scaffold-*` de `extra` (espelha a isenção que o
      compilador já tinha) e exige os 3 artefatos não vazios de cada scaffold
- [x] T-086 — Suíte sintética do gate: scaffold isento; pasta estranha, scaffold
      incompleto e feature não-codegen sem `spec.md` continuam reprovando

## 10. Dados a regerar (não é defeito de código)

- [ ] T-090 — `002-w1-low-complexity-bcs`: regerar plano (`G-SECURITY-APP` sem arquivos
      na seção 4) e depois o fragment
- [ ] T-091 — `003-w2-medium-complexity-bcs`: regerar fragment (cobre 87 de 154 arquivos)
- [ ] T-092 — `004-w3-high-complexity-bcs`: decidir autoridade e regerar plano ou fragment
      (41 arquivos do fragment ausentes do plano)
- [ ] T-093 — Investigar inconsistência de layout: 004 usa raiz `src/`, 002 e 003 usam
      `backend/`, no mesmo projeto e pelo mesmo agente

## 11. Diagnóstico, prevenção e reparo (2026-08-19)

- [x] T-100 — `diagnose_project()` + `render_diagnosis()`: todas as checagens sem parar
      no primeiro erro; achados com `code`/`severity`/`root_cause`/`fix`
- [x] T-101 — Comando `diagnose` no CLI do compilador, com `--plans-only` e `--json`
- [x] T-102 — **Gate do produtor**: wave4a (`speckit-plan-validate`, blocking) entre
      planning e tasks em `pipeline-dag/F3S.yaml`
- [x] T-103 — `_inherit_trace_id()` no scaffold injector: herda em vez de sortear UUID;
      passo volta a ser idempotente
- [x] T-104 — Consumidor depende de todos os produtores; zero produtores segue erro duro;
      multi-produtor exposto em `traceability.json.multi_producer_tokens`
- [x] T-105 — `explain_failure()` no runner: traceback + CAUSA RAIZ + PRÓXIMO PASSO;
      9 tools mapeadas, mais rede/timeout e default acionável
- [x] T-106 — Falha de tool passa a gravar `runner-state.json` antes de abortar
- [x] T-107 — `speckit_plan_repair.py` (dry-run por padrão) para o dado já corrompido
- [x] T-108 — Guardrails novos em `planning-agent.md` (P001, P002, P004, P009)

## 12. Verificação (2026-08-19)

- [x] T-110 — `diagnose` no `nopcommerce-04`: 13 erros / 12 avisos, agrupados por feature
- [x] T-111 — Após reparo: **1 erro** / 14 avisos; gate `--plans-only` com **0 erros**
- [x] T-112 — `explain_failure` em 4 cenários: tool mapeada, gate do plano, erro de rede
      e exceção desconhecida — todos com causa e comando corretos
- [x] T-113 — DAG expande 21 passos com `F3S:tool:speckit-plan-validate` na posição certa
- [x] T-114 — Injector reexecutado: `trace_id` único nos 10 artefatos
- [ ] T-115 — Regerar fragment da `003-w2-medium-complexity-bcs` (87 de 154 arquivos);
      único bloqueio restante, exige inferência

## 13. Cobertura do fragment (2026-08-19)

- [x] T-120 — Descartar hipótese de truncamento na 003 via métricas persistidas
      (38.417 de 64.000 tokens, `stop_reason=end_turn`)
- [x] T-121 — Medir payload redundante: 41% dos bytes por entry
- [x] T-122 — `_validate_task` exige só campos de autoria do fragment; os cinco campos
      de arquivo viram opcionais e reconciliados
- [x] T-123 — `tasks-agent.md`: cobertura contada + não recopiar campos do plano
- [x] T-124 — Regressão: fragments antigos válidos; entry enxuta aceita; acceptance
      vazio ainda reprova
- [ ] T-125 — Regerar fragment da 003 no console (não automatizável: `msvcrt.getwch`)

## 14. Destrave da compilação (2026-08-19)

- [x] T-130 — Fragment da 003 regerado: 156 entries cobrindo 154/154 arquivos (era 87)
- [x] T-131 — Remover 2 entries duplicadas e redirecionar `depends_on` de 4 tasks
      para os ids canônicos `T-W2S-001` / `T-W2S-004`
- [x] T-132 — `diagnose` 0 erros; compilador 427 tasks; ledger inicializado
- [x] T-133 — Injector: âncora real no próprio spec do scaffold + 6 seções do
      readiness-gate no `spec.md` gerado
- [x] T-134 — `CHK-SK-006` aceita âncora em forma de slug de heading (56 falso negativos)
- [x] T-135 — `CHK-SK-008` compara por `operationId`, a convenção da esteira
- [x] T-136 — Checks: 5 falhas → 3; exit gate aprova 5 de 6 itens
- [ ] T-137 — Regerar planos de 002/003 com âncoras reais (65 inventadas — `CHK-SK-006`)
- [ ] T-138 — Cobrir `BR-ORDER-005` (`CHK-SK-007`) e 40 casos de teste (`CHK-SK-009`)
- [ ] T-139 — Executar `F3S:compliance` e fechar o exit gate

## 15. Âncoras (2026-08-19)

- [x] T-140 — Separar falso negativo de invenção real: 118 dos 121 eram matcher
- [x] T-141 — `_ancora_resolve()`: prosa, slug, ou slug parcial em fronteira de segmento
- [x] T-142 — `P010` no gate do produtor (wave4a), espelhando o `CHK-SK-006`
- [x] T-143 — `planning-agent.md`: "Âncora é endereço, não rótulo"
- [x] T-144 — Backup do estado que compila em `estado-ok-427tasks/`
- [ ] T-145 — Regerar plano da 003 (esquema `SectionN-Xxx` inventado, 30 refs)
- [ ] T-146 — Corrigir citações a `DEC-026/027/028` em 002, 003 e 004

## 16. Destrave do task-compile (2026-08-19 03:45)

- [x] T-150 — `--mode orphan-contracts`: declara `contract:X` no arquivo que é o X (7)
- [x] T-151 — `--mode duplicate-task-ids`: discrimina por wave e reescreve depends_on (13)
- [x] T-152 — `--mode dead-refs`: remove âncora que não resolve, exigindo que sobre ao
      menos uma referência válida (12)
- [x] T-153 — Mensagem do compilador para task_id duplicado passa a listar quantos,
      quais, em que features, e o comando de reparo
- [x] T-154 — Guardrail `task_id` único no projeto em `tasks-agent.md`
- [x] T-155 — Cadeia determinística verde: plan-validate, scaffold-inject, task-compile
      (394 tasks), ledger-init; diagnose 0 erros
- [ ] T-156 — `CHK-SK-007`: cobrir `BR-ORDER-005`
- [ ] T-157 — `CHK-SK-009`: cobrir 41 de 71 casos de teste
- [ ] T-158 — Executar `F3S:compliance` e fechar o exit gate

## 17. Falha não-bloqueante com aceite de risco (2026-08-19)

- [x] T-160 — `on_fail` propagado de `pipeline-dag/*.yaml` → `pipeline_plan.dag_steps`
      → `_expand_dag_phases`
- [x] T-161 — `on_fail: confirm` em `speckit-dependency-checks`; demais tools mantêm aborto
- [x] T-162 — `_confirmar_risco()`: explica o risco e devolve a decisão ao operador
- [x] T-163 — Aceitação registrada em `runner-state.json` (`risk_accepted` + `detail`)
- [x] T-164 — Dashboard distingue `⚠️ Risco aceito` de `⏭ Pulado`
- [x] T-165 — EOF/Ctrl+C cancela; modo automático segue e registra
- [x] T-166 — Teste dos 7 caminhos de resposta

## 18. Compliance e graduação do risco (2026-08-19 04:18)

- [x] T-170 — Renomear `compliance-summary.json` → `compliance-status.json`
- [x] T-171 — `compliance-agent.md`: aviso nomeando a confusão com o agente de segurança
- [x] T-172 — `Reporter`: `blocking` por check, `hard_failures`/`soft_failures`, `exit_code`
- [x] T-173 — `CHK-SK-007/008/009` marcados não-bloqueantes; demais seguem bloqueando
- [x] T-174 — `run_checks_detailed()`; `run_checks()` mantém o contrato bool
- [x] T-175 — `run_tool_step` anexa `returncode`; runner só confirma no código 3
- [x] T-176 — Exit gate propaga `SOFT_FAIL`; artefato ausente segue FAIL duro
- [ ] T-177 — `CHK-PROTO-000`: nenhuma spec referencia o protótipo — decisão pendente
- [ ] T-178 — Schema do `compliance-status.json` diverge do contrato (campos do agente
      de segurança); nada lê os campos hoje, mas o artefato está fora do formato
