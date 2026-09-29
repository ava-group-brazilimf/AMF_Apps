# Agent Specification: ava-tobe-orchestrator v2.8.0 — Resilience & Autonomous Execution Consolidation

**Feature Branch**: `028-tobe-orchestrator-v280`
**Created**: 2026-07-23
**Status**: Draft
**Change Type**: `modify-existing` (3 agents)
**Input**: Consolidar as melhorias de resiliência e execução autônoma do pipeline TO-BE em um único agente atualizado: ava-tobe-orchestrator v2.8.0.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## Overview

This spec consolidates **five axes of change** that were introduced across the last 5 commits
into a single coherent update. All axes share one goal: eliminate unnecessary pipeline
interruptions and reduce failure surface from excessive inter-phase coupling.

The changes affect three existing agent files:

| Agent File | Current Version | New Version | Version Bump | Axes |
|---|---|---|---|---|
| `orchestrator-tobe.md` | 2.7.0 | 2.8.0 | MINOR | 1, 2, 3c, 4 |
| `adr-tobe.md` | 1.2.0 | 1.2.1 | PATCH | 3a |
| `test-plan-consolidated-tobe.md` | 2.1.0 | 2.1.1 | PATCH | 5 |

> **Constitution Article X**: MINOR bump is appropriate for orchestrator-tobe.md because
> the AED opt-out flag (`tobe_pipeline.autonomous_execution: false`) makes the behavioral
> change reversible — not a true breaking change. PATCH bumps for the other two files
> because they only refine existing behavior (3a: enforce naming canonical table;
> 5: reduce blocker count, which aligns with an already-declared artifact-only protocol).

---

## 1. Agent Identity

### 1.1 — `ava-tobe-orchestrator` (Primary)

| Field | Value |
|---|---|
| **Agent ID** | `ava-tobe-orchestrator` |
| **Version** | `2.8.0` |
| **Phase** | `F2` |
| **Module** | `tobe-architecture` |
| **Role** | Coordinates the full TO-BE architecture design pipeline — phases 0-Pre through 8 — with non-blocking gate protocol and autonomous execution directive |
| **Skill** | `ava-tobe-orchestrator` |
| **Dispatch** | user-facing via SKILL.md |
| **Existing file** | `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` |

> **Change Type `modify-existing`**: module.yaml entry exists; SKILL.md exists. Category 4 and Category 1.5 tasks are N/A.

### 1.2 — `ava-tobe-adr` (Secondary)

| Field | Value |
|---|---|
| **Agent ID** | `ava-tobe-adr` |
| **Version** | `1.2.1` |
| **Phase** | `F2` |
| **Module** | `tobe-architecture` |
| **Role** | Materializes the 8 mandatory ADRs in Michael Nygard format, enforcing canonical filenames and theme ownership as sole enforcer of ADR naming contract |
| **Skill** | `ava-tobe-adr` |
| **Dispatch** | user-facing via SKILL.md; also dispatched by orchestrator-tobe (Phase 0) |
| **Existing file** | `src/modules/ava-fabric-agents/tobe-architecture/agents/adr-tobe.md` |

### 1.3 — `ava-tobe-test-plan-consolidated` (Secondary)

| Field | Value |
|---|---|
| **Agent ID** | `ava-tobe-test-plan-consolidated` |
| **Version** | `2.1.1` |
| **Phase** | `F2` |
| **Module** | `tobe-architecture` |
| **Role** | Consolidates and enriches TO-BE Test Plan, Test Cases, and Gap Analysis with exactly 1 blocking input and 10 enrichment sources |
| **Skill** | _(no skill — internal, invoked exclusively by orchestrator at Phase 7.8)_ |
| **Dispatch** | internal-only via orchestrator |
| **Existing file** | `src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-consolidated-tobe.md` |

---

## 2. Agent Frontmatter

### 2.1 — `orchestrator-tobe.md`

```yaml
---
name: "ava-tobe-orchestrator"
version: "2.8.0"
date: 2026-07-23
description: |
  Coordena a esteira de design da arquitetura TO-BE com Non-Blocking Gate Protocol (NBGP)
  e Autonomous Execution Directive (AED) — o pipeline nunca para por artefato ausente ou
  gate condicional. Recebe o AS-IS Master Report e orquestra os agentes de design, sizing,
  plano de migração, geração de atividades, wave cycle refinement e geração de código.
  Stack e versão lidos de `tobe_stack.*` em project-config.yaml.
  Ativa com: "iniciar design TO-BE", "design arquitetura .NET",
  "start TO-BE design", "arquitetura alvo".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---
```

### 2.2 — `adr-tobe.md`

```yaml
---
name: "ava-tobe-adr"
version: "1.2.1"
date: 2026-07-23
description: |
  Materializa os 8 ADRs obrigatórios do projeto em formato Michael Nygard.
  Único enforcer do contrato de nomes ADR — valida filename canônico (Step 4a)
  antes de validar evidências AS-IS (Step 4b). Status `completed` garante
  8 arquivos, nomes canônicos, temas corretos, sem [INCOMPLETO] e INDEX.md válido.
  Ativa como Fase 0 da esteira TO-BE — sempre antes do Blueprint e do Tech Framework.
  Ativa com: "gerar ADRs", "decisões arquiteturais", "architecture decision records".
allowed-tools: Read, Write, Edit, Glob
---
```

### 2.3 — `test-plan-consolidated-tobe.md`

```yaml
---
name: "ava-tobe-test-plan-consolidated"
version: "2.1.1"
date: 2026-07-23
description: |
  Consolida o Test Plan TO-BE com cenários detalhados do AS-IS e artefatos enriquecedores.
  Exatamente 1 artefato bloqueante e 10 enriquecedores — sem referências a ADRs,
  DB Design, architecture-blueprint, security-test-strategy, coverage-gap-strategy,
  traceability-matrix, coexistence-matrix ou risk-register-residual nos steps ativos.
  Ativa com: "consolidar test plan", "enriquecer test plan", "test plan consolidado",
  "consolidar test cases", "consolidar gap analysis".
allowed-tools: Read, Write, Edit, Glob, Grep
---
```

---

## 3. Output Contract

No output contract changes in this spec. All three agents continue to write the same
artifacts to the same paths. The modifications affect **gate logic**, **execution steps**,
and **internal protocol** — not the set of produced artifacts.

| Agent | Artifact(s) Produced | Path(s) | Unchanged? |
|---|---|---|---|
| orchestrator-tobe | Agent Completion Registry (in-memory + log) | _(runtime state)_ | Schema extended: adds `status: skipped` |
| adr-tobe | 8 ADR files + INDEX.md | `projects/{project_name}/outputs/tobe/docs/decisions/` | ✅ unchanged |
| test-plan-consolidated | test-plan.md, test-cases.md, gap-analysis.md | `projects/{project_name}/outputs/tobe/qa/` | ✅ unchanged |

### 3.1 — Agent Completion Registry schema extension

The following schema addition is required for Eixo 1 (NBGP):

```yaml
# Agent Completion Registry — extended schema (orchestrator-tobe.md §Agent Completion Registry)
agent_completion_registry:
  - agent_id: string
    status: "completed" | "skipped" | "partial" | "running"   # NEW: skipped
    reason: string          # Required when status == "skipped" or "partial"
    recommended_action: string  # Required when status == "skipped"
    timestamp: ISO8601
```

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal: Full Pipeline Completes Without Interruption (Priority: P1)

**Story**: Como o orquestrador TO-BE, quero que o pipeline execute do início ao fim sem
parar em nenhum gate condicional, para que artefatos F2 sejam sempre entregues ao cliente.

**Why this priority**: Core value proposition of this spec — pipeline resilience is P1.

**Acceptance Scenarios**:

1. **Given** a project with `tobe_pipeline.autonomous_execution: true` (default) in project-config.yaml,
   **When** orchestrator-tobe executes and encounters a conditional gate (e.g., Requestor Inspection, Strategy Align),
   **Then** it emits `⚠️ [GATE WARN]`, records the agent as `status: skipped` in the Agent Completion Registry with `reason` and `recommended_action` populated, and immediately continues to the next independent phase.

2. **Given** the above,
   **When** execution completes,
   **Then** `## ❱ Execução Concluída` is emitted with the MICRO table listing all agent statuses (including `skipped` entries), and no `HARD STOP` text appears anywhere in the output.

3. **Given** the above,
   **When** the Build Gate (Phase 5.5) encounters a compile/CVE error,
   **Then** the orchestrator retries up to 15 iterations; after 15 iterations it marks Phases 4.8/5 as `partial` and continues to Phases 6–8.

---

### Scenario 2 — AED Opt-Out: Legacy Blocking Behavior Preserved (Priority: P1)

**Story**: Como engenheiro de migração, quero poder desativar o AED para projetos
que requerem aprovação humana explícita em cada gate.

**Why this priority**: BREAKING CHANGE reversibility guarantee per Constitution Article X.

**Acceptance Scenarios**:

1. **Given** `tobe_pipeline.autonomous_execution: false` in project-config.yaml,
   **When** orchestrator-tobe encounters a human coordination gate (Requestor Inspection, Strategy Align, Package Approval),
   **Then** it uses the original §2.2 blocking behavior (wait for user decision) instead of NBGP.

2. **Given** AED is disabled,
   **When** a Readiness Gate returns `CONDITIONAL`,
   **Then** the orchestrator waits for explicit PM confirmation before proceeding.

---

### Scenario 3 — ADR Canonical Name Enforcement (Priority: P2)

**Story**: Como o agente adr-tobe, quero garantir que todos os 8 ADRs sejam gravados
com filenames canônicos antes de qualquer validação de evidências.

**Why this priority**: Prevents downstream agents (phases 1, 1.4, 1.5, 1.6, 7.5) from failing
due to ADR filename mismatches.

**Acceptance Scenarios**:

1. **Given** adr-tobe is invoked with a project that has an existing `ADR-008-api-contracts.md` (wrong theme),
   **When** Step 4a (Filename Enforcement) executes,
   **Then** the file is renamed/regenerated to match canonical slot 8 (`ADR-008-audit-lgpd.md`) and a counter-example note is written to the agent log.

2. **Given** all 8 ADRs are written with canonical names and correct themes,
   **When** Step 4b (AS-IS Evidence Validation) executes,
   **Then** `ava-tobe-adr.status == "completed"` is set in the Agent Completion Registry.

3. **Given** orchestrator-tobe is executing Phase 0 gate validation,
   **When** it checks whether ADRs are ready,
   **Then** it reads only `ava-tobe-adr.status` from the Agent Completion Registry — it does NOT check individual ADR filenames directly.

---

### Scenario 4 — Prerequisites Gate 4.7-B Blocks Codegen (Priority: P1)

**Story**: Como o orquestrador, quero que o codegen seja suspenso se artefatos F2
obrigatórios estiverem ausentes, sem parar o pipeline inteiro.

**Why this priority**: Prevents generating code against incomplete architecture specs.

**Acceptance Scenarios**:

1. **Given** orchestrator-tobe is at Phase 4.7-B (after tech-framework gate 4.7-A, before coder invocation),
   **When** `verify_tobe_prereqs_gate.py --project {project_name}` exits with code 1,
   **Then** the coder agent is recorded as `status: skipped` in the Agent Completion Registry with `reason: "F2 prerequisite artifacts missing"` and `recommended_action: "Re-run after completing missing F2 phases"`, and the pipeline continues to Phase 4.8 and beyond.

2. **Given** the script exits with code 0,
   **When** Phase 4.7-B gate completes,
   **Then** the coder agent proceeds normally.

3. **Given** Phase 4.7-B skips the coder,
   **When** Phases 6–8 execute,
   **Then** they run normally — `skipped` coder status does not block downstream phases.

---

### Scenario 5 — Test Plan Consolidated: Exactly 1 Blocker + 10 Enrichers (Priority: P2)

**Story**: Como o agente test-plan-consolidated, quero uma lista mínima e clara de
dependências para reduzir falsos bloqueios em ambientes com pipeline incompleto.

**Why this priority**: Reduces false positives on the Dependency Gate in typical Wave 1 scenarios.

**Acceptance Scenarios**:

1. **Given** `outputs/asis/qa/test-cases.md` exists and is non-empty,
   **When** test-plan-consolidated-tobe validates its input contract,
   **Then** the Dependency Gate returns OK regardless of whether ADRs, DB Design, or architecture-blueprint are present.

2. **Given** one of the 10 enrichers (e.g., `openapi/bc*.yaml`) is absent,
   **When** test-plan-consolidated-tobe executes,
   **Then** it records `[FONTE AUSENTE: {path}]` and continues enrichment from remaining available sources.

3. **Given** test-plan-consolidated-tobe processes Steps 1–10,
   **When** examining active steps for references to removed artifacts,
   **Then** no active step references ADRs, DB Design, architecture-blueprint, security-test-strategy, coverage-gap-strategy, traceability-matrix, coexistence-matrix, or risk-register-residual.

---

## 5. Quality Gate Requirements

### 5.1 — Constitution Compliance

- [ ] All three agent IDs follow `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [ ] Frontmatter contains only `name`, `version`, `description`, `allowed-tools`, `date` (Article II)
- [ ] No technology versions hardcoded in agent bodies (Article I)
- [ ] All output paths use lowercase `{project_name}` and correct phase folder (Article II)
- [ ] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [ ] Skill/Agent split unchanged: orchestrator + adr have SKILL.md; consolidated is internal-only (Article XI)
- [ ] Module.yaml entries exist for all three agents — no new entries needed (Article IV)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

### 5.2 — Eixo-Specific Acceptance Criteria

- [ ] No `HARD STOP` or `PARAR IMEDIATAMENTE` text remains in `orchestrator-tobe.md` outside of Build Gate Phase 5.5
- [ ] `⚠️ [GATE WARN]` replaces `⛔ [GATE FAILED]` in all 22 locations listed in Eixo 1
- [ ] `## Autonomous Execution Directive (AED)` section present in `orchestrator-tobe.md` with exactly 5 numbered principles
- [ ] `tobe_pipeline.autonomous_execution` flag documented with `false` value as opt-out in project-config.yaml reference
- [ ] All 11 §2.2 blockquotes replaced with AED-active markers in `orchestrator-tobe.md`
- [ ] Agent Completion Registry schema in `orchestrator-tobe.md` includes `status: skipped` with `reason` and `recommended_action` fields
- [ ] `adr-tobe.md` Execution Order has Step 4a (Filename Enforcement) with canonical 8-slot table + counter-examples, executing BEFORE Step 4b (AS-IS Evidence Validation)
- [ ] ADR Ownership guardrail present in `adr-tobe.md`: "este agente é o único enforcer do contrato de nomes ADR"
- [ ] All 6 ADR filename gate checks in `orchestrator-tobe.md` (Phases 0, 1, 1.4, 1.5, 1.6, 7.5) replaced by `ava-tobe-adr.status == "completed"` registry check
- [ ] Gate 4.7-B present in `orchestrator-tobe.md` after Gate 4.7-A (tech-framework) and before coder invocation
- [ ] Gate 4.7-B invokes `verify_tobe_prereqs_gate.py --project {project_name}` via `run_in_terminal` (Bash tool)
- [ ] Gate 4.7-B exit code 1 → NBGP skip (not HARD STOP)
- [ ] `test-plan-consolidated-tobe.md` Dependency Gate uses exactly 1 blocking artifact: `outputs/asis/qa/test-cases.md`
- [ ] `test-plan-consolidated-tobe.md` enrichers list contains exactly 10 entries (no ADRs, DB Design, architecture-blueprint, security-test-strategy, coverage-gap-strategy, traceability-matrix, coexistence-matrix, or risk-register-residual)
- [ ] Steps 1–10 in `test-plan-consolidated-tobe.md` contain no references to removed enricher artifacts

---

## 6. Detailed Change Specification

### 6.1 — Eixo 1: Non-Blocking Gate Protocol (NBGP) — `orchestrator-tobe.md`

**Replace in 22 locations** (Phases 0-Pre, 0→1, 1 ADR prereq, 1 BC→TD, 1.4, 1.5, 2.5→3, 4.3, 4.5, 4.61, 4.7, 4.8, 5.5-post-15-iter, 7.8, 8.1, Gate F2→F3, Migration Design Gate):

```
⛔ [GATE FAILED] — {agent}
HARD STOP / PARAR IMEDIATAMENTE
```

Replace with:

```
⚠️ [GATE WARN] — {agent}
Registrar status: skipped no Agent Completion Registry
  reason: "{reason}"
  recommended_action: "{action}"
Continuar para próxima fase independente.
```

**Exception**: Build Gate Phase 5.5 retains up to 15 retry iterations for active compile/CVE errors.
After 15 iterations: mark Phases 4.8 and 5 as `partial`; Phases 6–8 continue normally.

**Agent Completion Registry schema extension** (add to existing registry definition section):

```yaml
# New status value
status: "completed" | "skipped" | "partial" | "running"
# New fields (required when status is skipped or partial)
reason: string
recommended_action: string
```

### 6.2 — Eixo 2: Autonomous Execution Directive (AED) — `orchestrator-tobe.md`

**Add new section** `## Autonomous Execution Directive (AED)` (placement: after `## Role & Persona`, before `## Agent Team Gerenciado`):

```markdown
## Autonomous Execution Directive (AED)

> **Flag de controle**: `tobe_pipeline.autonomous_execution` em project-config.yaml
> Valor padrão: `true`. Para desativar: `autonomous_execution: false` (restaura comportamento bloqueante §2.2).

Quando `autonomous_execution: true` (padrão), os seguintes 5 princípios estão ativos:

1. **Pipeline nunca para** — nenhum gate ou artefato ausente interrompe a execução. Toda condição de parada é convertida em NBGP (`status: skipped`).
2. **Override universal §2.2** — todos os "aguardar decisão do usuário" do protocolo §2.2 são substituídos por NBGP: prosseguir com fases independentes.
3. **Gates de coordenação humana não-bloqueantes** — Requestor Inspection, Strategy Align e Package Approval geram seus artefatos e continuam imediatamente sem aguardar aprovação.
4. **Readiness Gate CONDITIONAL auto-aprovado** — sem necessidade de confirmação explícita do PM; orquestrador registra `status: skipped` com `reason: "CONDITIONAL auto-approved by AED"` e continua.
5. **Security Review BLOCKED avança** — resultado BLOCKED do Security Review não impede Fases 6, 7, 7.5, 7.8 e 8; registrar `recommended_action: "Address security findings before production deployment"`.
```

**Replace all 11 identical §2.2 blockquotes** (pattern: `> Ver procedimento de escalonamento em @artifact-only-consumption-protocol §2.2`) with:

```markdown
> **[AED ATIVO]** Artefato ausente registrado como `status: skipped`. Pipeline continua. Ver AED §2.
```

### 6.3 — Eixo 3a: ADR Canonical Name Enforcement — `adr-tobe.md`

**Expand Execution Order Step 4** into 4a + 4b:

**Step 4a — Filename Enforcement (executes FIRST)**:

Add the following canonical 8-slot table and enforcement logic before any evidence validation:

```markdown
### Step 4a — Filename Enforcement (OBRIGATÓRIO — executa ANTES de 4b)

Verificar que os 8 arquivos gerados correspondem EXATAMENTE à tabela canônica:

| Slot | Filename Canônico | Tema Canônico | Counter-Example (ERRADO) |
|------|------------------|---------------|--------------------------|
| ADR-001 | `ADR-001-architecture-style.md` | Estilo arquitetural (monolito → microsserviços) | `ADR-001-tech-stack.md` |
| ADR-002 | `ADR-002-persistence-strategy.md` | ORM, banco de dados, estratégia de persistência | `ADR-002-database.md` |
| ADR-003 | `ADR-003-authentication-authorization.md` | Auth/AuthN/AuthZ (MSAL, JWT, RBAC) | `ADR-003-security.md` |
| ADR-004 | `ADR-004-api-design.md` | Design de API REST/GraphQL, contratos | `ADR-004-integration.md` |
| ADR-005 | `ADR-005-frontend-architecture.md` | Stack e arquitetura frontend (Angular/React/Vue) | `ADR-005-ui-framework.md` |
| ADR-006 | `ADR-006-cqrs-event-sourcing.md` | CQRS, MediatR, Event Sourcing | `ADR-006-patterns.md` |
| ADR-007 | `ADR-007-infrastructure-cloud.md` | IaC, cloud provider, containerização | `ADR-007-devops.md` |
| ADR-008 | `ADR-008-audit-lgpd.md` | Auditoria, LGPD/GDPR, trilha de auditoria | `ADR-008-api-contracts.md` ⚠️ |

> ⚠️ **Slot 8 é o mais frequentemente violado**: o tema correto é **Audit/LGPD** — nunca "API Contracts" (que pertence ao ADR-004).

**SE** qualquer arquivo tiver nome incorreto ou tema errado:
1. Reger (sobrescrever) o arquivo com nome canônico e tema correto
2. Remover arquivo com nome incorreto (se diferente do canônico)
3. Registrar no log: `[ADR-RENAME] {wrong_name} → {canonical_name}`
4. NÃO prosseguir para Step 4b até todos os 8 filenames estarem corretos
```

**Step 4b — AS-IS Evidence Validation (existing content, unchanged)**

**Add Ownership Guardrail** (after Execution Order section):

```markdown
## ADR Ownership Guardrail

Este agente (`ava-tobe-adr`) é o **único enforcer** do contrato de nomes ADR em todo o pipeline.

O orchestrator-tobe e outros agentes NÃO devem validar filenames ADR diretamente.
Eles devem verificar apenas `ava-tobe-adr.status == "completed"` no Agent Completion Registry.

`status: completed` garante:
- ✅ Exatamente 8 arquivos ADR presentes
- ✅ Todos os filenames correspondem à tabela canônica de 8 slots
- ✅ Nenhum arquivo contém `[INCOMPLETO]`
- ✅ `INDEX.md` atualizado e válido
```

### 6.4 — Eixo 3c: ADR Filename Gates in orchestrator-tobe.md

**Replace 6 ADR filename gate checks** (Phases 0, 1, 1.4, 1.5, 1.6, 7.5) that explicitly check filenames like `ADR-001-*.md`, `ADR-008-*.md` etc. with:

```markdown
# Gate: ADR readiness
IF agent_completion_registry["ava-tobe-adr"]["status"] != "completed":
  ⚠️ [GATE WARN] — ava-tobe-adr não concluído
  Registrar dependente como status: skipped
  Continuar com fases independentes
```

### 6.5 — Eixo 4: Prerequisites Gate 4.7-B — `orchestrator-tobe.md`

**Insert after Gate 4.7-A (tech-framework gate) and before coder invocation**:

```markdown
### Gate 4.7-B — Prerequisites Gate (F2 Artifacts)

**Posição**: Após Gate 4.7-A (tech-framework OK), antes de invocar qualquer coder agent.

**Execução**:
```bash
# Verificar pré-requisitos F2 para codegen
python verify_tobe_prereqs_gate.py --project {project_name}
```

**Exit code 0** → Pré-requisitos OK → prosseguir para coder agent.

**Exit code 1** → Pré-requisitos ausentes → NBGP:
  - Registrar coder agent como `status: skipped`
  - `reason: "F2 prerequisite artifacts missing — see verify_tobe_prereqs_gate.py output"`
  - `recommended_action: "Complete missing F2 phases before re-running codegen"`
  - Continuar para Phase 4.8 e seguintes

> **Princípio**: A lógica de validação permanece exclusivamente em `verify_tobe_prereqs_gate.py`.
> O orquestrador apenas invoca o script e trata o exit code.
```

### 6.6 — Eixo 5: Input Contract Simplification — `test-plan-consolidated-tobe.md`

**Blocking artifacts**: Keep exactly 1:
- `outputs/asis/qa/test-cases.md` (F1, bridge-fastqa)

**Remove from blocking list** (if present): Any references beyond the single blocking artifact above.

**Enrichment sources**: Keep exactly 10 (numbered 2–11):

| # | Artefato | Path |
|---|---|---|
| 2 | Test Plan TO-BE (base) | `outputs/tobe/qa/test-plan.md` |
| 3 | Test Plan AS-IS | `outputs/asis/qa/test-plan.md` |
| 4 | Wave Test Plan | `outputs/tobe/docs/wave-test-plan.md` |
| 5 | Gap Analysis AS-IS | `outputs/asis/qa/gap_analysis.md` |
| 6 | OpenAPI Specs por BC | `outputs/tobe/docs/openapi/bc*.yaml` |
| 7 | Regras de Negócio TO-BE | `outputs/tobe/docs/regras-negocio.md` |
| 8 | Coexistence Strategy | `outputs/tobe/docs/coexistence-strategy.md` |
| 9 | User Journeys | `outputs/tobe/user-journeys/user-journeys-report.md` |
| 10 | Risk Mitigation Plan | `outputs/tobe/risk-mitigation-plan.md` |
| 11 | Security Architecture | `outputs/tobe/docs/security-architecture.md` |

**Remove from enrichers and from all active steps** any references to:
- ADRs (any `outputs/tobe/docs/decisions/ADR-*.md`)
- DB Design (`outputs/tobe/docs/db-design*.md` or similar)
- Architecture Blueprint (`outputs/tobe/docs/architecture-blueprint.md`)
- Security Test Strategy (`outputs/tobe/docs/security-test-strategy.md`)
- Coverage Gap Strategy (`outputs/tobe/docs/coverage-gap-strategy.md`)
- Traceability Matrix (`outputs/tobe/docs/traceability-matrix.md`)
- Coexistence Matrix (`outputs/tobe/docs/coexistence-matrix.md`)
- Risk Register Residual (`outputs/tobe/risk-register-residual.json`)

**Update Dependency Gate** to align with single blocking artifact (remove multi-artifact loop):

```python
PROCEDURE validate_inputs(project_name):
  blocking = ["projects/{project_name}/outputs/asis/qa/test-cases.md"]
  missing = [f for f in blocking if NOT file_exists(f) OR file_size(f) == 0]
  IF missing is NOT empty:
    Emitir ⛔ BLOCKED com lista de missing
    PARAR.
  RETURN OK
```

---

## 7. project-config.yaml Reference

The following key must be documented in `project-config.yaml` schema reference (within the `tobe_pipeline` section):

```yaml
tobe_pipeline:
  autonomous_execution: true    # default: true
  # Set to false to restore blocking gate behavior (§2.2 protocol).
  # When false: human coordination gates (Requestor Inspection, Strategy Align,
  # Package Approval, Readiness Gate CONDITIONAL, Security Review BLOCKED)
  # revert to their original wait-for-user behavior.
  # BREAKING CHANGE: false disables AED; pipeline may pause at any gate.
```

---

## 8. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| AS-IS Master Report | `ava-asis-orchestrator` | Must complete F1 before any TO-BE phase starts |
| ADR TO-BE (for orchestrator gates) | `ava-tobe-adr` | Status `completed` required before Blueprint, DB Policy, DB Design, Security Design, and Deliverables phases |
| verify_tobe_prereqs_gate.py | _(script)_ | Must exist at project root; Bash tool must be in allowed-tools for orchestrator |
| F2 prerequisite artifacts | various F2 agents | Consumed by verify_tobe_prereqs_gate.py script |
| AS-IS Test Cases | `ava-asis-bridge-fastqa` | Only blocking input for test-plan-consolidated |

---

## 9. Assumptions

1. `verify_tobe_prereqs_gate.py` already exists or will be created as part of this spec's implementation tasks.
2. The 22 HARD STOP locations in `orchestrator-tobe.md` are identifiable by searching for `⛔ [GATE FAILED]`, `HARD STOP`, and `PARAR IMEDIATAMENTE` patterns.
3. The 11 §2.2 blockquotes are all structurally identical; a single find-and-replace pattern covers all occurrences.
4. The 6 ADR filename gate checks are located by searching for `ADR-001`, `ADR-008`, or explicit filename patterns in orchestrator-tobe.md gate logic.
5. `test-plan-consolidated-tobe.md` currently already has 1 blocker and 10 enrichers (based on file inspection); Eixo 5 tasks verify and lock this state, removing any stale references from active steps.
6. The Build Gate Phase 5.5 currently implements a retry loop; the 15-iteration cap and `partial` state transition are additions to the existing loop logic.
