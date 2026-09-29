# Plan — Spec 029: Unificar `ava-test-plan-tobe`

## Constitution Check

- Altera behavior de agente existente → sim, requer version bump (4.0.0 → 5.0.0).
- Remove agente e skill wrapper → sim, requer atualização de referências cruzadas.
- Afeta orchestrator TO-BE → sim, requer ajuste na DAG e no registry.
- Afeta docs e specs cruzadas → sim, necessário sincronização.

## Technical Context

O agente `ava-test-plan-tobe` v4.0.0 reside em `src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-tobe.md` e produz quatro artefatos. O agente `ava-tobe-test-plan-consolidated` reside em `src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-consolidated-tobe.md` e produz/sobrescreve `test-plan.md`, além de `test-cases.md` e `gap-analysis.md`. O merge elimina a duplicidade e a fase extra do orquestrador.

## Implementation Phases

### Phase 1 — Spec Artifacts
- Criar `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`.

### Phase 2 — Refactor `test-plan-tobe.md`
- Atualizar Input Contract (promover/demover/adicionar artefatos).
- Expandir Output Contract com `test-cases.md` e `gap-analysis.md`.
- Inserir Step 1f (carregar `gap-list-report.md`).
- Inserir Step 5b.2 (materializar `test-cases.md`) e Step 5c (materializar `gap-analysis.md`).
- Atualizar template canônico com §10 Coexistence Tests e §11 Risk-Based Tests.
- Bump version 4.0.0 → 5.0.0 e atualizar date.

### Phase 3 — Eliminate Consolidated
- Deletar `test-plan-consolidated-tobe.md`.
- Deletar `.github/skills/ava-tobe-test-plan-consolidated/SKILL.md`.
- Remover diretório vazio, se aplicável.

### Phase 4 — Update Orchestrator & Module
- Remover Fase 7.8 de `orchestrator-tobe.md`.
- Atualizar `module.yaml` (remover entrada, bump versão).

### Phase 5 — Update QA Agents
- `qa-orchestrator-agent.md`: alterar FQ pre-condition para `@ava-test-plan-tobe` trigger `TP`.
- `bridge-fastqa-tobe.md`: apontar upstream de `test-cases.md` para `ava-test-plan-tobe`.

### Phase 6 — Sync Docs & Specs
- Atualizar `docs/tobe-architecture-io-map.md`.
- Atualizar `docs/tobe-input-artifacts-existence-check.md`.
- Atualizar `docs/plan/guarail-artifact-only-tobe-orchestrator.md`.
- Atualizar `CHANGELOG.md`.
- Atualizar `specs/016-tobe-artifact-only-guardrail`.
- Documentar obsolescência em `specs/028-tobe-orchestrator-v280`.

### Phase 7 — Verify
- Grep por referências residuais.
- Validar YAML de `module.yaml`.
- Revisão manual de coerência.

## Complexity

Média-alta. Vários arquivos cruzados, mas mudanças mecânicas e bem delimitadas.
