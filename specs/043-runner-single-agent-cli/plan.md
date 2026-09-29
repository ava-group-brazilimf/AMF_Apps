# Plan — Spec 043: Execução de um agente avulso pelo runner

## Constitution Check

- **Article II/X** — Nenhum contrato de agente muda; não há bump de versão de agente. A entrega é
  de entrada do executor.
- **Article III** — Os gates da esteira não são afetados: o despacho avulso não os aciona nem os
  contorna.
- **Article V** — Mensagens ao operador e documentação em pt-BR.
- **Article XI** — Nenhum agente novo.
- **IV3** — Degradação, nunca quebra: `agent_registry` indisponível derruba só o tier 2; proxy
  headroom ausente cai no endpoint direto; `spec_path` inválido volta para a heurística com aviso.
- **IV7** — Somente stdlib (`argparse`, `difflib`); nenhuma dependência nova.

## Architecture

```text
                    python "pipeline_runner 19.py" [flags]
                                   |
                          _parse_cli()  [E1,E8]
                                   |
            +----------------------+----------------------+
            |                      |                      |
      --list-agents            --agent               (sem flags)
            |                      |                      |
   _listar_agentes_cli    _despachar_agente_unico     main(project_preselecionado)
            |                      |                      |
            |                      |               fluxo interativo intacto
            |                      |
            |             runner_agent_cli.resolver_passo()   [C1]
            |                      |
            |         +------------+------------+
            |         |            |            |
            |      tier 1       tier 2       tier 3
            |    PIPELINE do   agent_        AgentCLIError
            |     runner       registry      + difflib
            |         |            |
            |         +-----+------+
            |               |
            |         validar_passo()  ->  detectar_fanout()  [C2]
            |               |
            |         preflight_step_inputs()  (recusa, nao degrada)  [C3]
            |               |
            |         run_step(client, passo, project, output_dir)
            |               |
            |         load_skill(agent, spec_path=...)   [C4]
            |               |
            |         explain_failure() em qualquer excecao  [C5]
```

### Decisões de projeto

**Por que a esteira do runner é a fonte, e não `pipeline_plan.build_plan`.** Foi a suposição
inicial e estava errada. Os namespaces divergem e `run_step` faz curto-circuito por string exata
de fase (`3462`, `3471`, `3491`, `3502`). Resolver `ava-summary` pelo YAML devolveria `F8a`,
`run_step` não casaria `("S1","S4")`, pularia `_run_summary_generate_standalone` e gastaria uma
inferência de 128k tokens no lugar de um script Python. O teste
`test_resolver_preserva_a_fase_do_runner` existe para impedir a "simplificação" que reintroduz
isso.

**Por que um módulo separado.** O runner importa `msvcrt` no topo e monta estado global no import
(`_INPUTS_APLICADOS = _apply_declared_inputs(PIPELINE)`, linha 429). Nada dele é importável sem
extração por AST, que custa caro por função. `runner_agent_cli.resolver_passo` recebe `pipeline`
como **parâmetro** — o runner passa seu `PIPELINE`, os testes passam uma lista sintética. As 33
asserções do módulo rodam por import direto; só as 18 do runner precisam de AST.

**Por que `_despachar_agente_unico` não chama `main()`.** Enfiar nove condicionais numa função de
750 linhas — a de maior densidade de defeito do arquivo — é o caminho para regredir o modo
interativo. A função nova replica apenas o setup que `run_step` exige: `output_dir.mkdir`, a API
key, o client, e os globais `DEPLOYMENT`/`PROVIDER`.

**Por que `PROVIDER` é recalculado sempre.** O global só era corrigido dentro de
`_select_model_interactive`. Pulado o menu, `run_step` tomaria o ramo errado e mandaria payload
Anthropic para endpoint OpenAI — falha silenciosa e cara. `resolver_provider` espelha o teste que
o runner já faz, e o valor é impresso em toda execução.

**Por que o estado da esteira fica de fora.** Um `_save_runner_state` com `active_steps` de um
passo só sobrescreveria o `runner-state.json` de um run real, e a próxima execução ofereceria
retomar uma esteira de um passo. Corrupção silenciosa. O teste
`test_despacho_avulso_nao_grava_estado_da_esteira` conta as chamadas e exige zero.

**Por que insumo ausente recusa em vez de degradar.** Na esteira, `_degrade_phase` existe para não
travar as fases sucessoras. No despacho avulso não há sucessora, e despachar sem insumo produz
alucinação cara. A divergência é deliberada e está comentada no código.

**Por que `load_skill` ganha precedência 0.5 em vez de perder a heurística.** A heurística é o
caminho do modo interativo e de todo passo expandido; removê-la seria mudança de risco alto para
ganho nenhum nesta entrega. Ela fica em 0.5 e não em 0 porque `AGENT_SKILL_OVERRIDE` é curadoria
explícita multi-arquivo — para esses agentes a spec única do registry é mais pobre.

### Semântica de falha

| Situação | Exit | Comportamento |
| --- | --- | --- |
| `--agent` sem `-p` | 2 | recusa com exemplo |
| projeto inexistente | 2 | lista + sugestão por similaridade |
| agente desconhecido | 2 | sugestão sobre esteira ∪ registry (115 ids) |
| agente ambíguo | 2 | tabela fase/trigger + comando com `--phase` |
| agente não despachável ou spec ausente | 2 | problemas de `validar_passo` |
| fan-out sem escopo | 2 | evidência medida + escopos disponíveis + `--force-single` |
| insumo obrigatório ausente | 1 | `format_missing`, que já nomeia o `produced_by` |
| exceção em `run_step` | 1 | `explain_failure` — traceback + causa raiz + próximo passo |
| `val_ok` falso | 1 | detalhe do que não foi gravado |
| Ctrl+C | 130 | encerra limpo |

## Implementation Phases

### Phase 1 — Pré-requisito
`agent_registry.py` passa a ler com `utf-8-sig`. Um BOM de 3 bytes desligava cinco controles.
Efeito colateral esperado e verificado: a divergência de versão de `ava-summary-remediation`
(frontmatter 1.7.0 × bloco 1.4.1), até então invisível, apareceu — foi alinhada e o BOM removido,
devolvendo a contagem de violações ao patamar anterior.

### Phase 2 — `load_skill(spec_path=...)`
Precedência 0.5, sem chamador novo. No-op comprovável: nenhum passo de `PIPELINE` tem a chave.

### Phase 3 — `runner_agent_cli.py`
Resolução em três tiers, validação, detecção de fan-out e construtores de mensagem. Fechado com
33 testes verdes antes de qualquer alteração no runner.

### Phase 4 — Enxertos no runner
`import argparse`, `_parse_cli`, `_agent_cli`, `_listar_agentes_cli`,
`_despachar_agente_unico`, `main(project_preselecionado=...)` e o roteamento do entrypoint.

## Complexity Tracking

| Decisão | Justificativa |
| --- | --- |
| Módulo novo em vez de tudo no runner | testabilidade: 33 de 51 asserções rodam por import direto |
| Três tiers em vez de reusar `build_plan` | os namespaces de fase divergem e `run_step` ramifica por string |
| `--force-single` | recusar por default sem escape vira parede; a saída é explícita e nomeada |
| `--trigger` e `--model` opcionais | o modo não-interativo pula os menus que os definiriam |

## Verification

```powershell
python -m pytest tests/tools/test_agent_registry.py -q
python -m pytest tests/tools/test_runner_agent_cli.py -q
python -m pytest tests/tools/test_runner_agent_flag.py -q
python -m pytest tests/tools/test_runner_approval_gate.py tests/tools/test_pipeline_plan.py -q

python "pipeline_runner 19.py" --list-agents
python "pipeline_runner 19.py" --agent ava-tobe-migration-plan -p meu-erp-03 --dry-run
python "pipeline_runner 19.py" --agent ava-tobe-migration-plna -p meu-erp-03
python "pipeline_runner 19.py" --agent ava-devops-orchestrator -p meu-erp-03
python "pipeline_runner 19.py" --agent ava-speckit-specification -p nopcommerce-04
python "pipeline_runner 19.py"        # REGRESSÃO — interativo intacto
```

## Trabalho futuro (fora do escopo desta spec)

- `--task-id` para agentes F4, com integração ao `task_ledger` e à verificação de build.
- Propagar `spec_path` em `_expand_dag_phases` e `_expand_ledger_phase`, eliminando a heurística
  de `load_skill` da esteira inteira.
- As 19 violações de observabilidade que `test_esteira_sem_violacoes` acusa — pré-existentes,
  falham antes e depois desta entrega.
- O guard de exit code do `on_fail: confirm` sumiu numa reescrita recente do runner: o bloco hoje
  testa só `on_fail == "confirm"`, sem consultar o `returncode`, o que permite aceitar risco sobre
  falha estrutural. Registrado, não corrigido aqui.
