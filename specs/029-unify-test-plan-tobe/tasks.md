# Tasks — Spec 029: Unificar `ava-test-plan-tobe`

## 1. Análise & Planejamento
- [x] Mapear inputs/outputs de ambos os agentes.
- [x] Mapear referências cruzadas no workspace.
- [x] Levantar decisões de design com usuário.
- [x] Criar spec, plan e checklists.

## 2. Implementação do Agente Unificado
- [x] Atualizar Input Contract de `test-plan-tobe.md`.
- [x] Atualizar Output Contract de `test-plan-tobe.md`.
- [x] Inserir Steps 1f, 5b.2, 5c.
- [x] Atualizar template canônico com Coexistence e Risk-Based.
- [x] Bump version/date.

## 3. Eliminação do Consolidado
- [x] Deletar `test-plan-consolidated-tobe.md`.
- [x] Deletar `.github/skills/ava-tobe-test-plan-consolidated/SKILL.md`.
- [x] Remover diretório skill vazio.

## 4. Orquestrador & Módulo
- [x] Remover Fase 7.8 de `orchestrator-tobe.md`.
- [x] Remover entrada de `module.yaml`.
- [x] Bump versão de `module.yaml`.

## 5. QA Downstream
- [x] Atualizar `qa-orchestrator-agent.md`.
- [x] Atualizar `bridge-fastqa-tobe.md`.

## 6. Documentação & Specs
- [x] Atualizar `docs/tobe-architecture-io-map.md`.
- [x] Atualizar `docs/tobe-input-artifacts-existence-check.md`.
- [x] Atualizar `docs/plan/guarail-artifact-only-tobe-orchestrator.md`.
- [x] Atualizar `CHANGELOG.md`.
- [x] Atualizar `specs/016-tobe-artifact-only-guardrail`.
- [x] Documentar obsolescência em `specs/028-tobe-orchestrator-v280`.

## 7. Verificação & Qualidade
- [x] Grep confirma zero ocorrências ativas do agente eliminado.
- [x] Grep confirma outputs em `test-plan-tobe.md`.
- [x] `module.yaml` parseável e IDs únicos.
- [x] Revisão manual de coerência.

## Completion Checklist
- [x] Todos os itens acima concluídos.
- [x] Sem erros de lint/YAML.
- [ ] User aprovou mudanças.
