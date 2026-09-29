# Tasks — Spec 035: QA Orchestrator em dois momentos

## 1. Análise & Planejamento
- [x] Mapear a esteira F1..F7 e os dois momentos do `ava-devops-orchestrator`.
- [x] Identificar o produtor real de `parity-test-report.md` (`ava-devops-compare-version`).
- [x] Levantar as referências pendentes `§Routing — Trigger PT` / `§Routing — Trigger RS`.
- [x] Confirmar decisões de design com o usuário (código `QE`, destino do `QS`, escopo, gate).
- [x] Criar `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`.

## 2. Frontmatter, Cabeçalho e Menu
- [x] Bump `version: 1.3.0 → 2.0.0` e `date` no frontmatter.
- [x] Ampliar `description` com os gatilhos do Momento 2.
- [x] Ajustar a linha `Step` do cabeçalho para os dois momentos.
- [x] Acrescentar coluna **Momento** em `## Agent Team QA`.
- [x] Adicionar `QE` ao `## Triggers / Menu`.
- [x] Marcar `TPT` como Momento 1 — Planejamento.
- [x] Marcar `QS` como ⚠️ DEPRECADO (alias de `QE`).
- [x] Adicionar `PT` e `RS` ao menu.
- [x] Atualizar a nota do invariante PT→RS abaixo do menu.

## 3. Pre-condition Gate (QE)
- [x] Criar `## Pre-condition Gate (QE)` com os 4 passos bloqueantes.
- [x] Passo 1 — `bounded-context-map.md` com ≥1 BC (reusa o critério do gate `QS`).
- [x] Passo 2 — `test-plan.md` + `test-cases.md` (planejamento `TPT`).
- [x] Passo 3 — sentinela `source-code/README.md` + backend/frontend (esteira de código F4).
- [x] Passo 4 — `iac/ci/`, `iac/cd/azure-pipelines-cd.yml`, `infra/` (DevOps `DE`).
- [x] Passo 4b — `parity-test-report.md` como WARN não-bloqueante.
- [x] Criar `### Mensagem de Bloqueio QE` com ação requerida por motivo.
- [x] Emitir o sinal `↳ ✅ [ava-qa-orchestrator] QE DEFERRED` no bloqueio.

## 4. Routings
- [x] Criar `## Routing — Trigger QE` movendo o corpo do Routing `QS`.
- [x] Preservar ET VERIFICATION GATE (9b) e FQ COMPLETION GATE (9c) sem alteração.
- [x] Preservar a execução do `qa_test_runner.py` e a geração do `qa-master-report.md`.
- [x] Inserir o passo `FTM` após o `BM`, condicional ao `behavior-catalog.json`.
- [x] Reduzir `## Routing — Trigger QS` a stub de depreciação.
- [x] Criar `## Routing — Trigger PT` (verificação, não dispatch).
- [x] Criar `## Routing — Trigger RS` (dispatch `mode: regression`).

## 5. Seções Terminais e Tabelas
- [x] Atualizar a lista do invariante em `## Terminal Mandatory Steps (PT → RS)` (inclui `QE` e `FQ`).
- [x] Adicionar a linha `QE` em `### Resumo de cobertura por trigger`.
- [x] Marcar `QS` como deprecado na tabela de cobertura.
- [x] Bump `--version 2.0.0` no bloco `pipeline_observer.py`.

## 6. Documentação
- [x] Entrada MAJOR no `CHANGELOG.md`.

## 7. Verificação & Qualidade
- [x] Grep confirma que `§Routing — Trigger PT` e `§Routing — Trigger RS` existem como seções.
- [x] Grep confirma que todo código do menu aparece na tabela de cobertura.
- [x] Versão do frontmatter bate com a do bloco de observabilidade.
- [x] Paths do gate conferidos contra os agentes produtores.
- [x] Revisão manual de coerência.

## Completion Checklist
- [x] Todos os itens acima concluídos.
- [x] Sem erros de lint/YAML.
- [ ] Execução end-to-end validada em `projects/MeuERP-002/`.
- [ ] User aprovou mudanças.
