# Requirements Checklist — Spec 029

## Requisitos Funcionais
- [ ] RF-001: `ava-test-plan-tobe` unificado gera `test-plan.md`, `test-cases.md`, `gap-analysis.md`, `functional-test-matrix.md`, `traceability-matrix.md` e `automatable-test-cases.md`.
- [ ] RF-002: Input Contract refletir artefatos obrigatórios promovidos e opcionais rebaixados conforme decisões do plano.
- [ ] RF-003: Step 1f carrega `gap-list-report.md` opcional para alimentar Seção 16 e `gap-analysis.md`.
- [ ] RF-004: Step 5b.2 materializa `test-cases.md` com grupos canônicos e tags de origem.
- [ ] RF-005: Step 5c materializa `gap-analysis.md` com reclassificação AS-IS e identificação TO-BE.
- [ ] RF-006: Template canônico inclui §10 Coexistence Tests e §11 Risk-Based Tests.

## Requisitos Não-Funcionais
- [ ] RNF-001: Nenhum invento de cenário sem evidência (`BR-NNN` ou `FR-NNN`).
- [ ] RNF-002: Pirâmide 70/20/10 mantida e rastreável.
- [ ] RNF-003: Trigger único `TP`; sem trigger `TC` separado.

## Integridade
- [x] INT-001: `test-plan-consolidated-tobe.md` e skill wrapper excluídos.
- [x] INT-002: Fase 7.8 removida de `orchestrator-tobe.md`.
- [x] INT-003: `module.yaml` sem entrada `ava-tobe-test-plan-consolidated`.
- [x] INT-004: Docs e specs cruzadas sincronizadas.
