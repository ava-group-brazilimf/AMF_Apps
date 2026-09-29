# Tasks — Spec 043: Execução de um agente avulso pelo runner

> Status: **implementado e verificado**. A ordem abaixo é causal: o pré-requisito do registry
> destrava a resolução, a resolução é fechada e testada isoladamente, e só então o runner é
> tocado. Nada dentro do laço principal da esteira foi alterado.

## 1. Governança

- [x] T-001 — Criar `spec.md` com problema, US1–US6 e BDD (nominal, fase divergente, ambíguo,
      fan-out, typo, estado, regressão do interativo)
- [x] T-002 — Criar `plan.md` com Constitution Check, decisões de projeto e semântica de falha
- [x] T-003 — Criar `tasks.md` em ordem causal

## 2. Pré-requisito — registry

- [x] T-010 — `agent_registry.py` lê com `utf-8-sig`; um BOM de 3 bytes escondia um agente e
      desligava cinco controles
- [x] T-011 — Alinhar a versão do bloco de observabilidade de `ava-summary-remediation`
      (1.4.1 → 1.7.0), divergência que só apareceu quando o agente voltou ao catálogo
- [x] T-012 — Remover o BOM do arquivo — era o único do repositório
- [x] T-013 — Testes: BOM sintético entra no catálogo, o agente real resolve, e nenhum arquivo
      do repo tem BOM

## 3. Skill determinística

- [x] T-020 — `load_skill(agent_name, spec_path=None)` com precedência 0.5
- [x] T-021 — `run_step` e o ramo `V` (ver skill) passam `step.get("spec_path")`
- [x] T-022 — Verificar que nenhum passo de `PIPELINE` tem a chave — modo interativo bit-idêntico
- [x] T-023 — Verificar que os 19 agentes da esteira continuam resolvendo o mesmo arquivo

## 4. Módulo de resolução

- [x] T-030 — Criar `src/shared/tools/runner_agent_cli.py` com `_main(argv) -> int`
- [x] T-031 — `resolver_provider` — antídoto do `PROVIDER` velho
- [x] T-032 — `resolver_passo` em três tiers, com a esteira do runner primeiro
- [x] T-033 — `validar_passo` — campos que `run_step` acessa por colchete, deprecado,
      não-despachável, spec ausente em disco
- [x] T-034 — `detectar_fanout` e `escopos_disponiveis`
- [x] T-035 — Construtores de mensagem: projeto inexistente, agente desconhecido, ambíguo,
      fase inválida, passo inválido, fan-out avulso
- [x] T-036 — `listar_agentes` marcando os ambíguos
- [x] T-037 — 33 testes por import direto, verdes antes de tocar no runner

## 5. Enxertos no runner

- [x] T-040 — `import argparse`
- [x] T-041 — `_parse_cli` com 11 flags; `argv` vazio devolve tudo None/False
- [x] T-042 — `_agent_cli` e `_listar_agentes_cli`
- [x] T-043 — `_despachar_agente_unico`, sem chamar `main()`
- [x] T-044 — `main(project_preselecionado=None)`; nome inválido cai no menu, não aborta
- [x] T-045 — Roteamento do entrypoint

## 6. Verificação

- [x] T-050 — 18 testes por extração AST, incluindo os três que travam o estado da esteira
- [x] T-051 — `_parse_cli([])` devolve tudo None/False — o guardião do modo interativo
- [x] T-052 — Ramos de erro manuais: typo, ambíguo, fan-out, projeto inexistente, sem `-p`
- [x] T-053 — `--dry-run` resolve sem despachar; prompt sai
      `@ava-tobe-migration-plan project: meu-erp-03`
- [x] T-054 — Fan-out com `--feature` produz `| feature: 002-w1-low-complexity-bcs`
- [x] T-055 — Suíte completa: 140 passaram, 1 falha pré-existente e não relacionada

## 7. Documentação

- [x] T-060 — `docs/guia-execucao-agente-avulso.md`
- [x] T-061 — Entrada no `CHANGELOG.md`

## 8. Trabalho futuro

- [ ] T-070 — `--task-id` para agentes F4, com `task_ledger` e verificação de build
- [ ] T-071 — Propagar `spec_path` em `_expand_dag_phases` e `_expand_ledger_phase`,
      eliminando a heurística de `load_skill` da esteira inteira
- [ ] T-072 — Restaurar o guard de exit code do `on_fail: confirm`, perdido numa reescrita
      recente: hoje aceita risco sobre falha estrutural, não só sobre lacuna de cobertura
- [ ] T-073 — As 19 violações de observabilidade pré-existentes
