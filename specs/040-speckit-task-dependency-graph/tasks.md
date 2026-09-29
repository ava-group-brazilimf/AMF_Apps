# Tasks — Spec 040: Grafo de dependências das tasks SpecKit

> Status: **implementação concluída; piloto real pendente**. A ordem abaixo é causal; nenhuma
> integração de runner precede os contratos, compilador e checks determinísticos.

## 1. Governança

- [x] T-001 — Criar `spec.md` com BDD nominal, edge, quality gate e retomada
- [x] T-002 — Criar `plan.md` com Constitution Check e arquitetura
- [x] T-003 — Criar `tasks.md` ordenado por dependências

## 2. Núcleo determinístico

- [x] T-010 — Criar testes de cadeia, branch/join, desempate, referência inválida e ciclo
- [x] T-011 — Implementar `dependency_graph.py` stdlib-only
- [x] T-012 — Integrar validação, rank e ondas ao `task_ledger.py`
- [x] T-013 — Adicionar diagnóstico status-aware ao ledger

## 3. Contratos e produtores

- [x] T-020 — Criar schema `speckit-plan-graph`
- [x] T-021 — Criar schema `speckit-task-fragment`
- [x] T-022 — Criar contrato traceability v2 e loader compatível v1/v2
- [x] T-023 — Atualizar `ava-speckit-planning` e `plan-template.md`
- [x] T-024 — Atualizar `ava-speckit-tasks` e `tasks-template.md`
- [x] T-025 — Atualizar compliance e corrigir layout dos globs

## 4. Compilador e checks

- [x] T-030 — Implementar `speckit_task_compiler.py` em duas passagens
- [x] T-031 — Testar ownership, producer/consumer, create/update e fallback de grupo
- [x] T-032 — Adicionar CHK-SK-016 de integridade de referências
- [x] T-033 — Adicionar CHK-SK-017 de ciclos
- [x] T-034 — Adicionar CHK-SK-018 de ordem persistida
- [x] T-035 — Integrar os checks ao gate de saída F3S

## 5. Scheduler F4

- [x] T-040 — Adicionar task exata ao `Step` e ao preâmbulo de iteração
- [x] T-041 — Implementar seleção incremental de tasks prontas
- [x] T-042 — Executar `verify_command` e registrar exit code real
- [x] T-043 — Diagnosticar complete/waiting/blocked/dangling/cycle
- [x] T-044 — Integrar `ava_pipeline.py`, `agent_runner.py` e `pipeline_runner 19.py`

## 6. Migração e documentação

- [x] T-050 — Atualizar `F3S.yaml` com compile/init/check/gates determinísticos
- [x] T-051 — Bump de versão e migração no `CHANGELOG.md`
- [x] T-052 — Regenerar e validar os 4 wrappers alterados; `--check` global permanece bloqueado
	pelos órfãos preexistentes `ava-summary.agent.md` e `ava-summary-validate.agent.md`
- [ ] T-053 — Executar piloto F3S/F4 e registrar evidências

## 7. Classificação frontend/backend

- [x] T-060 — Exigir `task_type` em plan-graph v2, fragment v2, traceability v3 e ledger v2
- [x] T-061 — Derivar `backend_dependencies` das predecessoras diretas no compilador
- [x] T-062 — Padronizar integração UI/API com tokens `api:{operationId}`
- [x] T-063 — Expor tipo e dependência backend em `tasks.md`
- [x] T-064 — Bloquear projeção frontend → backend inconsistente no CHK-SK-016
- [x] T-065 — Cobrir tela consumidora de endpoint e corrupção da projeção com testes
- [x] T-066 — Atualizar agents/templates, aplicar bump major e regenerar wrappers

## 8. Especificações por migration wave

- [x] T-070 — Criar builder e schema de `wave-spec-manifest.json`
- [x] T-071 — Substituir as sete features estáticas por fan-out dirigido por wave
- [x] T-072 — Validar cardinalidade e artefatos do gate contra o manifesto
- [x] T-073 — Adicionar `source_refs[]` e validar todas as âncoras
- [x] T-074 — Persistir identidade e ordem da migration wave em traceability/ledger
- [x] T-075 — Derivar arestas entre migration waves no compilador
- [x] T-076 — Distribuir cobertura de protótipo entre specs verticais
- [x] T-077 — Atualizar agentes, templates, coders frontend e wrappers
- [x] T-078 — Cobrir builder, fallback, gates e DAG entre waves com testes
- [x] T-079 — Bloquear BR, operationId, US e TC sem associação determinística a uma wave
