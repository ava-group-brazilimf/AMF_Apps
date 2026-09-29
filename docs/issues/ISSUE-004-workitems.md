# Work items — ISSUE-004 (F3S / SpecKit)

**Repositório**: `imfai-ava-fabric-apps-agents` · **Branch**: `feat/deterministic-task-dependency-graph`
**Origem**: `docs/issues/ISSUE-004-speckit-plan-graph-perda-silenciosa.md`
**Projeto-piloto**: `nopcommerce-04` · **Data**: 2026-08-19

Importação: `ISSUE-004-workitems.csv` (Boards → Work Items → Import from CSV). Ajuste `Area Path` e `Iteration Path` antes de importar — estão como placeholder.

**26 work items** — 18 resolvidos, 8 abertos.

## Resumo

| # | Tipo | Título | Sev | Estado |
|---|---|---|---|---|
| WI-01 | Bug | F3S: bloco FILE truncado é descartado silenciosamente pelo parser | Critical | Resolved |
| WI-02 | Bug | F3S: stop_reason=max_tokens não reprova o passo | High | Resolved |
| WI-03 | Bug | F3S: validação pós-passo inoperante — contrato nunca casa a fase expandida | High | Resolved |
| WI-04 | Bug | F3S: 'outputs' declarados no DAG são resolvidos e descartados | High | Resolved |
| WI-05 | Bug | F3S: SystemExit escapa do handler e mata o processo sem gravar estado | Critical | Resolved |
| WI-06 | Bug | Dashboard pipeline-status.html não avança durante um passo em execução | Medium | Resolved |
| WI-07 | Bug | Passo reexecutado na retomada fica em 'executed' e 'skipped' ao mesmo tempo | Medium | Resolved |
| WI-08 | Bug | Compilador exige que o fragment recopie verbatim tabela de 90-155 linhas | High | Resolved |
| WI-09 | Bug | Exit gate da F3S reprova os scaffolds gerados pelo passo anterior do próprio DAG | High | Resolved |
| WI-10 | Bug | Scaffold injector sorteia trace_id aleatório a cada execução | High | Resolved |
| WI-11 | Bug | Regra 'exatamente 1 produtor' é incompatível com arquitetura em camadas | Medium | Resolved |
| WI-12 | Bug | Fragment obrigado a recopiar 41% de payload morto, causando subcobertura | Critical | Resolved |
| WI-13 | Bug | Scaffold gera âncora inexistente e spec.md sem as 6 seções do readiness-gate | Medium | Resolved |
| WI-14 | Bug | CHK-SK-006 reprova âncora em formato slug que resolve para heading real | High | Resolved |
| WI-15 | Bug | CHK-SK-008 compara METHOD /path contra operationId — 19/19 falso positivo | High | Resolved |
| WI-16 | Task | Diagnóstico agregado da F3S e gate de plano no produtor | Medium | Closed |
| WI-17 | Task | Trace e causa raiz na saída por erro do runner | Medium | Closed |
| WI-18 | Task | Ferramenta de recuperação de plan-graph incompleto | Low | Closed |
| WI-19 | Bug | Plano da wave W2 usa esquema de âncora inventado (SectionN-Xxx) | High | Active |
| WI-20 | Bug | Planos citam decisões DEC-026, DEC-027 e DEC-028 que não existem na constituição | High | Active |
| WI-21 | Bug | CHK-SK-007: BR-ORDER-005 não é alcançada por nenhuma task | Medium | Active |
| WI-22 | Bug | CHK-SK-009: 40 de 71 casos de teste não são alcançados por task | Medium | Active |
| WI-23 | Bug | Plano da W3 declara produzir operações de API que pertencem à W2 | Low | Active |
| WI-24 | Bug | Raiz de caminho inconsistente entre features do mesmo projeto | Low | Active |
| WI-25 | Task | Specs de W0 (foundation) e W4 (cutover) são geradas e nunca consumidas | Medium | Active |
| WI-26 | Task | Remover resíduos plan.partN e MERGE-INSTRUCTIONS do nopcommerce-04 | Low | Active |

---

## WI-01 · F3S: bloco FILE truncado é descartado silenciosamente pelo parser

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 1 - Critical |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, perda-de-dados |

**Sintoma**

O agente ava-speckit-planning emitiu plan.md (fechado) e plan-graph.json (cortado por max_tokens). O runner gravou apenas o plan.md e reportou 'Artefatos gerados: 4' com val_ok=true. 82.103 caracteres do grafo foram perdidos sem nenhum aviso. Reincidente em 3 features do nopcommerce-04 e em my-nop-ecommerce/002-w1-core-read.

**Causa raiz**

Em parse_and_write_outputs havia duas varreduras: a primeira para blocos fechados (<!-- FILE --> ... <!-- /FILE -->), a segunda para o bloco aberto deixado por truncamento. A segunda era guardada por 'if written: return written' — só rodava se a primeira não achasse NADA. Com plan.md fechado, a função retornava antes de processar o bloco cortado. Defeito secundário no mesmo trecho: truncated=True fatiava em .partN TODOS os blocos, inclusive os íntegros.

**Correção aplicada**

Varredura única com _FILE_ANY (marcador de fechamento em grupo de captura opcional). Bloco cortado é gravado como .PARTIAL e devolvido em 'incompletos'. Fatiamento .partN restrito a HTML grande. Verificado contra os logs reais de planning:003 e planning:004.

**Arquivos**

- `ava-pipeline-runner-cli.py`

---

## WI-02 · F3S: stop_reason=max_tokens não reprova o passo

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, observabilidade |

**Sintoma**

Resposta cortada pelo teto de saída gerava apenas um aviso amarelo no terminal. O passo era contabilizado como executado e o pipeline seguia com artefato incompleto.

**Causa raiz**

Em run_step, truncated = (stop_reason == 'max_tokens') alimentava só um print. Não virava falha, não gerava retry, não era gravado no estado nem no relatório da fase.

**Correção aplicada**

Truncamento e artefato incompleto passam a definir val_ok=False, que já encaminhava o passo para 'skipped' em vez de 'executed'. stop_reason, incomplete e detail passam a constar nas métricas persistidas.

**Arquivos**

- `ava-pipeline-runner-cli.py`

---

## WI-03 · F3S: validação pós-passo inoperante — contrato nunca casa a fase expandida

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, validacao |

**Sintoma**

Todos os passos da F3S eram aprovados por omissão, com val_ok=true, mesmo produzindo metade do contrato de saída.

**Causa raiz**

validate_phase_artifacts fazia PHASE_ARTIFACT_CONTRACT.get(phase). Em runtime a fase é 'F3S:planning:003-w2-medium-complexity-bcs'; a chave do dicionário é 'F3S'. O lookup nunca casava, o contrato vinha vazio e required_missing era sempre lista vazia. O PHASE_MAX_TOKENS, no mesmo arquivo, já recebera o fallback correto no commit 6acaba04; esta função ficou de fora.

**Correção aplicada**

Seleção de contrato corrigida. O contrato por-fase é de FIM DE FASE (exige traceability.json, produzido na wave5b) e por isso NÃO se aplica a passo intermediário expandido — para esses vale o 'outputs' do DAG. Um fallback ingênuo phase.split(':')[0] teria sido pior que o bug original.

**Arquivos**

- `ava-pipeline-runner-cli.py`

---

## WI-04 · F3S: 'outputs' declarados no DAG são resolvidos e descartados

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, contrato |

**Sintoma**

plan-graph.json é declarado como saída esperada em três lugares — speckit/module.yaml, pipeline-dag/F3S.yaml e planning-agent.md — e nenhum é aplicado por código executável. O artefato só se torna load-bearing como inputs.mandatory do consumidor seguinte, o que faz a falha aflorar um passo tarde demais e atribuída ao agente errado.

**Causa raiz**

pipeline_plan._resolver_outputs resolve o {feature} corretamente e grava a chave no dict do passo (pipeline_plan.py:222). Em seguida ela é perdida: o dataclass Step não tem campo 'outputs' e _expand_dag_phases não copiava a chave. O único consumidor no repositório era agent_runner.py:806, no motor copilot, que não é o caminho em uso.

**Correção aplicada**

_expand_dag_phases propaga outputs e output_base. Novo validate_declared_outputs confere os caminhos exatos por feature; artefato de tamanho zero conta como ausente.

**Arquivos**

- `ava-pipeline-runner-cli.py`
- `src/shared/tools/pipeline_plan.py`

---

## WI-05 · F3S: SystemExit escapa do handler e mata o processo sem gravar estado

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 1 - Critical |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, retomada |

**Sintoma**

Insumo obrigatório ausente derrubava o processo inteiro. Sem relatório final, sem prompt de retry, sem estado de retomada. O pipeline-status.html ficava congelado em 'Executando…' indefinidamente. Ao retomar, o runner voltava ao mesmo passo e morria igual — loop de travamento.

**Causa raiz**

load_context levantava SystemExit, que herda de BaseException e não de Exception. O handler do laço principal captura Exception e não o pegava. Em cascata: _save_runner_state, _write_status_html(done=True) e _finalize_runner_state ficavam inalcançáveis, e o proxy headroom não era encerrado.

**Correção aplicada**

Nova exceção MissingMandatoryInput(Exception) com phase, agent e missing. Handler dedicado grava métricas, salva estado e fecha o dashboard antes de abortar. Adicionado também preflight_step_inputs, que confere inputs.mandatory antes do despacho com custo zero de inferência — dependência que só existia no CLI ava_pipeline, não usado nesta esteira.

**Arquivos**

- `ava-pipeline-runner-cli.py`
- `src/shared/tools/context_manifest.py`

---

## WI-06 · Dashboard pipeline-status.html não avança durante um passo em execução

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 3 - Medium |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, observabilidade |

**Sintoma**

Durante os ~700s de um passo de planning o dashboard ficava estático — relógio parado, sem indicação de avanço, indistinguível de um processo travado. Na retomada, a varredura dos passos já concluídos também não atualizava.

**Causa raiz**

O HTML pede recarga ao navegador a cada 3s via <meta http-equiv='refresh'>, mas quem escreve o arquivo é o runner, e ele só escrevia ENTRE passos. Durante o passo não havia nenhum ponto de execução que voltasse ao dashboard.

**Correção aplicada**

_RUN_CTX + status_heartbeat() chamado de dentro dos dois laços de streaming (Anthropic e OpenAI), estrangulado em 3s para espelhar o meta refresh. Também dispara antes do 1º token (TTFT e retries levam minutos), após a expansão do DAG e na varredura de retomada. Verificado: 50.000 chamadas em 2,87s produzem 2 escritas.

**Arquivos**

- `ava-pipeline-runner-cli.py`

---

## WI-07 · Passo reexecutado na retomada fica em 'executed' e 'skipped' ao mesmo tempo

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 3 - Medium |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, retomada |

**Sintoma**

F3S:planning:003 rodou com sucesso na retomada e continuou exibido como 'Pulado' no dashboard, contado nos dois totalizadores (12/20 fases · 1 pulada, com 12+1 > 12 passos).

**Causa raiz**

As listas de veredicto só recebiam append; nada removia o resultado da tentativa anterior. O renderizador testa na ordem aborted → skipped → executed, então o veredicto antigo vencia.

**Correção aplicada**

_mark_executed() remove a fase de skipped/aborted ao registrar execução e evita duplicata em executed. O runner-state.json do nopcommerce-04 foi saneado com a mesma regra.

**Arquivos**

- `ava-pipeline-runner-cli.py`

---

## WI-08 · Compilador exige que o fragment recopie verbatim tabela de 90-155 linhas

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, compilador |

**Sintoma**

speckit-task-compile abortava com 'T-MED-014: source_refs diverge do plano'. Medição no nopcommerce-04: 26 divergências de source_refs e 17 de produces/consumes em 302 entries.

**Causa raiz**

planning-agent.md declara o plan-graph.json como 'autoridade para grupos, ownership de arquivos, produces, consumes e dependências', e tasks-agent.md manda o agente RECOPIAR esses campos. O compilador exigia igualdade exata da cópia — source_refs inclusive por ORDEM — enquanto produces/consumes já eram comparados como conjunto. Incoerência interna, e na prática pedia reprodução verbatim de tabela grande num turno com teto de saída.

**Correção aplicada**

Campos de arquivo (action, task_type, source_refs, produces, consumes) passam a ser lidos do plano. A cópia do fragment é reconciliada e contabilizada em traceability.json.reconciled_from_plan — nunca silenciada. 'group' segue erro duro por definir escalonamento e cobertura.

**Arquivos**

- `src/shared/tools/speckit_task_compiler.py`

---

## WI-09 · Exit gate da F3S reprova os scaffolds gerados pelo passo anterior do próprio DAG

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, gate |

**Sintoma**

Exit gate falhava com 'pastas fora do manifesto: 000-scaffold-angular, 000-scaffold-dotnet', bloqueando a F4.

**Causa raiz**

f4s_scaffold_injector (wave5a) cria 000-scaffold-{stack} como features transversais de W0 e não altera o wave-spec-manifest.json. O gate (wave7) computa extra = actual - expected sobre as pastas de specs/ e não tinha isenção. O compilador já trazia a isenção; o gate não.

**Correção aplicada**

Isenção espelhada no gate, mais exigência de spec.md + plan-graph.json + task-fragment.json não vazios em cada scaffold presente. Suíte sintética verifica que pasta estranha, scaffold incompleto e feature não-codegen sem spec.md continuam reprovando.

**Arquivos**

- `src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py`

---

## WI-10 · Scaffold injector sorteia trace_id aleatório a cada execução

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, determinismo |

**Sintoma**

Os 4 artefatos de scaffold divergiam dos 6 de domínio, e o compilador exige um único trace_id em todo o conjunto. Além disso, a saída de um passo declaradamente determinístico era irreprodutível entre execuções.

**Causa raiz**

f4s_scaffold_injector.py:164 fazia trace_id = project_config.get('trace_id') or f'trace-{uuid.uuid4().hex[:12]}'. O project-config.yaml normalmente não declara trace_id, então o ramo do UUID era o caminho normal, não a exceção.

**Correção aplicada**

_inherit_trace_id() herda, em ordem: plan-graphs de domínio já em disco → manifesto de waves → project-config → derivação estável por hash do nome do projeto. Nunca sorteia. Verificado: reexecução do injector produz o mesmo resultado.

**Arquivos**

- `src/shared/tools/f4s_scaffold_injector.py`

---

## WI-11 · Regra 'exatamente 1 produtor' é incompatível com arquitetura em camadas

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 3 - Medium |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, compilador |

**Sintoma**

Compilador abortava com "consume 'api:calculateTax' com 2 produtores; esperado exatamente 1". Dos 11 casos multi-produtor do nopcommerce-04, 9 são o par legítimo Service + Controller.

**Causa raiz**

Em camadas, api:X é produzido legitimamente por dois arquivos: o Service (Application/Services) implementa a operação e o Controller (API/Controllers) a expõe. A regra não admitia esse desenho.

**Correção aplicada**

Consumidor passa a depender de TODOS os produtores — ordenação conservadora, nunca menos restritiva. Zero produtores continua erro duro. Multi-produtor sai em traceability.json.multi_producer_tokens e como achado P003/P005 do diagnóstico.

**Arquivos**

- `src/shared/tools/speckit_task_compiler.py`

---

## WI-12 · Fragment obrigado a recopiar 41% de payload morto, causando subcobertura

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 1 - Critical |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, contrato-de-agente |

**Sintoma**

F3S:tasks:003 produziu 87 entries para um plano de 154 arquivos. Não foi truncamento: stop_reason=end_turn e apenas 38.417 dos 64.000 tokens de saída usados. Comparação: tasks:002 usou 61.910 para 139 entries; tasks:004 usou 56.092 para 132.

**Causa raiz**

A correção do WI de recópia verbatim fez o compilador ler os campos de arquivo do plano, mas _validate_task continuava EXIGINDO esses campos no fragment e tasks-agent.md continuava mandando copiá-los. Medição no fragment da 003: 38.910 de 94.749 chars (41%) eram recópia. Sem ela, 154 entries cabem em ~24.7k tokens, o mesmo custo que 87 tinham.

**Correção aplicada**

_validate_task exige só o que o fragment é autoridade. Os cinco campos de arquivo são aceitos se vierem (fragments antigos seguem válidos) e reconciliados. tasks-agent.md ganhou 'Cobertura total é contada, não estimada' e 'Não recopie o que o plano já declara'. Resultado: a regeração produziu 154/154 arquivos cobertos.

**Arquivos**

- `src/shared/tools/speckit_task_compiler.py`
- `src/modules/ava-fabric-agents/speckit/agents/tasks-agent.md`

---

## WI-13 · Scaffold gera âncora inexistente e spec.md sem as 6 seções do readiness-gate

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 3 - Medium |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, scaffold |

**Sintoma**

CHK-SK-006 e CHK-SK-014 reprovavam as duas features de scaffold — checks que elas mesmas introduziam no conjunto.

**Causa raiz**

O injector declarava source_refs apontando para architecture-blueprint.md com a âncora literal 'SCAFFOLD', que nunca existiu naquele arquivo. E copiava o template do scaffold como spec.md, sem as 6 seções literais em inglês (Context, Input, Processing, Output, Examples, Failure Modes) que o readiness-gate C2 confere por glob.

**Correção aplicada**

SCAFFOLD_ANCHOR aponta para um heading do próprio spec.md do scaffold, que o injector grava — sempre existente. _secoes_readiness() acrescenta as 6 seções ao spec.md gerado.

**Arquivos**

- `src/shared/tools/f4s_scaffold_injector.py`

---

## WI-14 · CHK-SK-006 reprova âncora em formato slug que resolve para heading real

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, checks, falso-positivo |

**Sintoma**

121 referências reprovadas no nopcommerce-04. Das 121, 118 eram falso negativo: 56 são slug de heading e 62 são slug parcial de heading real.

**Causa raiz**

O check fazia busca por substring: _norm(anchor) in _norm(conteudo). Uma âncora em slug ('3-modelo-de-domínio') tem hífen onde o heading tem espaço e ponto ('## 3. Modelo de Domínio') e nunca casa literalmente. Uma âncora parcial ('4.1-calcular-imposto') endereça '### 4.1 Calcular Imposto (Tax)' omitindo o parêntese.

**Correção aplicada**

_ancora_resolve() aceita prosa literal, slug de heading, ou slug parcial cortado em fronteira de segmento. Calibrado, não permissivo: 'Section3-CatalogDomain', que não prefixa heading nenhum, continua reprovando.

**Arquivos**

- `src/shared/checks/suites/speckit_traceability.py`

---

## WI-15 · CHK-SK-008 compara METHOD /path contra operationId — 19/19 falso positivo

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Resolved |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, checks, falso-positivo |

**Sintoma**

Todas as 19 operações do OpenAPI apareciam 'sem task' estando todas cobertas.

**Causa raiz**

_operacoes_do_openapi devolvia 'METHOD /path' (ex.: 'GET /orders'). As tasks referenciam operationId (ex.: 'PlaceOrder'), que é a convenção declarada nos guardrails de ava-speckit-planning e ava-speckit-tasks (token api:{operationId}) e o que speckit_wave_manifest.py extrai do contrato. Notações incompatíveis, nunca casavam.

**Correção aplicada**

O extrator devolve operationId quando existe; METHOD /path só como fallback para operação sem id, que aí é de fato irreferenciável por token.

**Arquivos**

- `src/shared/checks/suites/speckit_traceability.py`

---

## WI-16 · Diagnóstico agregado da F3S e gate de plano no produtor

| Campo | Valor |
|---|---|
| Work Item Type | Task |
| State | Closed |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, prevencao |

**Sintoma**

compile_project para no primeiro erro, o que obriga a descobrir os bloqueios um por execução — foram necessárias quatro sondas para chegar ao fundo no nopcommerce-04. E toda validação semântica só rodava na wave5b, três passos depois do produtor.

**Causa raiz**

Não havia modo de coleta agregada, e as checagens de coerência do plano viviam apenas no consumidor. Um plano incoerente condenava os despachos da wave5 antes de qualquer reprovação.

**Correção aplicada**

Comando 'diagnose' (com --plans-only e --json) roda todas as checagens sem parar, cada achado com code, severity, root_cause e fix. Nova wave4a no DAG (speckit-plan-validate, blocking) entre planning e tasks. Códigos: P001 grupo sem arquivos, P002 consumo sem produtor, P004 produces contaminado, P006 grupo duplicado, P009 raiz inconsistente, P010 âncora inexistente, F001/F002 plano×fragment, X001 trace_id.

**Arquivos**

- `src/shared/tools/speckit_task_compiler.py`
- `src/shared/data/pipeline-dag/F3S.yaml`

---

## WI-17 · Trace e causa raiz na saída por erro do runner

| Campo | Valor |
|---|---|
| Work Item Type | Task |
| State | Closed |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, pipeline-runner, observabilidade |

**Sintoma**

Um passo que falhava imprimia apenas '❌ Erro no passo X: <msg>'. Sem traceback não dava para localizar o ponto da falha, e sem tradução da causa o operador tinha de inferir qual agente ou ferramenta regerar.

**Causa raiz**

Não havia mapeamento entre a exceção e a causa raiz característica de cada tool, nem impressão do traceback.

**Correção aplicada**

explain_failure() imprime traceback completo, bloco CAUSA RAIZ traduzido e PRÓXIMO PASSO com o comando exato. Nove tools mapeadas; erros de rede e timeout reconhecidos; default acionável apontando o diagnose. Falha de tool passa a gravar runner-state.json antes de abortar.

**Arquivos**

- `ava-pipeline-runner-cli.py`

---

## WI-18 · Ferramenta de recuperação de plan-graph incompleto

| Campo | Valor |
|---|---|
| Work Item Type | Task |
| State | Closed |
| Priority | 3 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, recuperacao |

**Sintoma**

Planos de 002 e 004 declaravam grupos sem arquivos e consumos sem produtor; os fragments correspondentes tinham 56 arquivos que os planos não declaravam.

**Causa raiz**

Sem ferramenta de recuperação, o único caminho para dado já corrompido era regerar por inferência. A evidência mostrava que o fragment estava certo: os consumos órfãos do plano eram produzidos exatamente pelos arquivos ausentes.

**Correção aplicada**

speckit_plan_repair.py, dry-run por padrão, injeta no plano os arquivos que só o fragment tem. Nunca remove nem altera linha existente. Aplicado: 56 arquivos em 2 features, levando o diagnose de 13 erros para 1.

**Arquivos**

- `src/shared/tools/speckit_plan_repair.py`

---

## WI-19 · Plano da wave W2 usa esquema de âncora inventado (SectionN-Xxx)

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Active |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, conteudo, nopcommerce-04 |

**Sintoma**

P010 e CHK-SK-006 reprovam 30 referências da 003-w2-medium-complexity-bcs. Âncoras distintas: Section2-Examples, Section3-CatalogDomain, Section3-CustomersDomain, Section3-MessagesDomain, Section3-PaymentsDomain, Section6-ErrorHandling, Section8-CrossBC, Section8-Conflicts-CF-W2-001.

**Causa raiz**

O agente ava-speckit-planning cunhou um esquema de nomes próprio em vez de citar headings reais da spec. A spec 003 tem '## 3. Modelo de Domínio' e '### BC-01 — Catalog'; nenhum slug razoável mapeia para 'Section3-CatalogDomain'.

**Critério de aceite**

regerar plan-graph.json da 003 e obter 0 achados P010 em `speckit_task_compiler.py diagnose -p nopcommerce-04 --plans-only`. O guardrail 'Âncora é endereço, não rótulo' já foi adicionado ao planning-agent.md. ATENÇÃO: regerar o plano invalida o fragment da 003, que hoje cobre 154/154 — prever a cascata.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/speckit/specs/003-w2-medium-complexity-bcs/plan-graph.json`

---

## WI-20 · Planos citam decisões DEC-026, DEC-027 e DEC-028 que não existem na constituição

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Active |
| Severity | 2 - High |
| Priority | 1 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, conteudo, nopcommerce-04 |

**Sintoma**

A constituição do nopcommerce-04 declara DEC-001 a DEC-025. Os planos das três waves de codegen citam DEC-026, DEC-027 e DEC-028. Refs afetadas: 002 (5), 003 (parte das 30), 004 (1).

**Causa raiz**

O agente de planning citou ids de decisão que nunca foram tomadas. Rastreabilidade falsa — o defeito que a camada de checks existe para impedir.

**Critério de aceite**

nenhuma referência a DEC-0NN acima do maior id presente em constitution.md. Correção pode ser determinística (trocar pela decisão existente aplicável ou remover a referência) sem regerar o plano inteiro.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/speckit/specs/*/plan-graph.json`

---

## WI-21 · CHK-SK-007: BR-ORDER-005 não é alcançada por nenhuma task

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Active |
| Severity | 3 - Medium |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, cobertura, nopcommerce-04 |

**Sintoma**

1 de 25 regras de negócio do catálogo sem task correspondente.

**Causa raiz**

Lacuna de cobertura na geração do plano/fragment da wave que contém o BC de Orders. O formato dos rule_ids confere; é lacuna real, não incompatibilidade.

**Critério de aceite**

CHK-SK-007 verde em `python -m src.shared.checks -p nopcommerce-04 --suite speckit_traceability`.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/speckit/traceability.json`

---

## WI-22 · CHK-SK-009: 40 de 71 casos de teste não são alcançados por task

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Active |
| Severity | 3 - Medium |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, cobertura, nopcommerce-04 |

**Sintoma**

Casos TC-API-CAT-001..005, TC-API-CUS-001..002, TC-API-ORD-001..003 e outros 30 sem task.

**Causa raiz**

Lacuna de cobertura. Verificado que não é incompatibilidade de formato: os test_ids das tasks estão na mesma notação TC-XXX-NNN do catálogo.

**Critério de aceite**

CHK-SK-009 verde. Avaliar se os casos de teste de API devem gerar tasks próprias ou ser cobertos pelas tasks de controller.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/qa/test-cases.md`

---

## WI-23 · Plano da W3 declara produzir operações de API que pertencem à W2

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Active |
| Severity | 4 - Low |
| Priority | 3 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, conteudo, nopcommerce-04 |

**Sintoma**

Achado P005: OrdersController.cs (004-w3) declara produces api:CapturePayment e api:RefundPayment, que pertencem ao BC Payments da 003-w2. Não bloqueia — o compilador passou a criar aresta para todos os produtores.

**Causa raiz**

Contaminação cross-feature na lista produces do plano da W3.

**Critério de aceite**

nenhum achado P005 cross-feature no diagnose. Remover os dois tokens do produces de OrdersController.cs no plano da 004.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/speckit/specs/004-w3-high-complexity-bcs/plan-graph.json`

---

## WI-24 · Raiz de caminho inconsistente entre features do mesmo projeto

| Campo | Valor |
|---|---|
| Work Item Type | Bug |
| State | Active |
| Severity | 4 - Low |
| Priority | 3 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, conteudo, nopcommerce-04 |

**Sintoma**

Achado P009: a 004-w3 usa raiz src/, frontend/ e tests/, enquanto 002-w1 e 003-w2 usam backend/. Mesmo projeto, mesmo agente, layouts diferentes. A F4 geraria código em árvores distintas por wave.

**Causa raiz**

O agente de planning não recebe nem infere uma raiz canônica; cada despacho decide a sua.

**Critério de aceite**

nenhum achado P009 no diagnose. Definir a raiz no constitution.md ou no project-config.yaml e referenciá-la no guardrail do planning-agent.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/speckit/specs/*/plan-graph.json`

---

## WI-25 · Specs de W0 (foundation) e W4 (cutover) são geradas e nunca consumidas

| Campo | Valor |
|---|---|
| Work Item Type | Task |
| State | Active |
| Priority | 2 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, speckit, arquitetura |

**Sintoma**

As specs 001-w0-foundation e 005-w4-cutover consomem ~242s de inferência cada e produzem ~80 KB com 10 seções completas. Nenhuma fase posterior as lê: a F4 recebe specs/*/plan.md e specs/*/tasks.md (globs que W0/W4 não satisfazem) e nunca referencia specs/*/spec.md. O único leitor é ava-speckit-compliance, que audita e não gera trabalho.

**Causa raiz**

Por desenho, speckit_wave_manifest.py:312 marca codegen=false para wave_type foundation e cutover, e as waves 4 e 5 do DAG filtram por codegen_only. O trabalho de W0 chega à F4 por caminho separado (f4s_scaffold_injector, que nunca lê a spec da W0). Atenuante: o conteúdo substantivo da W0 (Shared Kernel) já está no constitution.md, que é consumido. A W4 não tem esse atenuante — cutover não está representado em nenhum artefato executável.

**Critério de aceite**

decidir e documentar — (a) manter como entregável documental para humanos, (b) deixar de gerar a W0 por redundância com a constituição, ou (c) definir consumidor para a spec de cutover nas fases F5/Deliverables.

**Arquivos**

- `src/shared/data/pipeline-dag/F3S.yaml`
- `src/shared/tools/speckit_wave_manifest.py`

---

## WI-26 · Remover resíduos plan.partN e MERGE-INSTRUCTIONS do nopcommerce-04

| Campo | Valor |
|---|---|
| Work Item Type | Task |
| State | Active |
| Priority | 4 |
| Area Path | `{AreaPath}\AVA Fabric\F3S` |
| Tags | F3S, limpeza, nopcommerce-04 |

**Sintoma**

As features 002, 003 e 004 mantêm plan.part1.md, plan.part2.md e plan.MERGE-INSTRUCTIONS.md das rodadas defeituosas de 18/08 14h. Nada os lê; os plan.md unificados estão corretos.

**Causa raiz**

Efeito colateral do fatiamento indevido em .partN quando a resposta era truncada — causa já corrigida no parser.

**Critério de aceite**

nenhum arquivo plan.part*.md ou plan.MERGE-INSTRUCTIONS.md em projects/nopcommerce-04/outputs/tobe/speckit/specs/.

**Arquivos**

- `projects/nopcommerce-04/outputs/tobe/speckit/specs/*/`

---
