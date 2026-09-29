---
checklist_id: migration-design
version: "1.1.0"
description: |
  Checklist de validação de completude e consistência de TODOS os artefatos
  da Fase F2 (Migration Design) ANTES de iniciar o Build Cycle (F3-F6).
  Utiliza sistema de pesos para priorizar critérios críticos.
applies_to: orchestrator-tobe
trigger: "pós-Fase 8 (Azure Infra Estimator) e pré-Build Cycle"
date: 2026-07-09
author: AVA Fabric Agents Team
---

# Migration Design Checklist — Gate de Qualidade Pré-Build Cycle

> **Instrução**: Este checklist é executado automaticamente pelo `orchestrator-tobe.md` após conclusão da Fase 8.
> O gate valida 60+ artefatos da fase Migration Design antes de autorizar transição para Build Cycle (F3).
>
> **Sistema de Pesos**:
> - 🔴 **BLOQUEADOR ABSOLUTO**: 1 falha → gate: BLOCKED (não negociável)
> - 🟡 **CRÍTICO**: peso 10 cada (acumulam para score)
> - 🟢 **IMPORTANTE**: peso 3 cada (acumulam para score)

---

## Identificação do Projeto

| Campo | Valor |
|-------|-------|
| **Projeto** | `{{PROJECT_NAME}}` |
| **Cliente** | `{{CLIENT_NAME}}` |
| **Data da Validação** | `{{VALIDATION_DATE}}` |
| **Trace ID** | `{{TRACE_ID}}` |
| **Executado por** | orchestrator-tobe v{{ORCHESTRATOR_VERSION}} |

---

## Seção A — ADRs (Fase 0): 9 artefatos

> ⛔ **Categoria**: BLOQUEADOR ABSOLUTO  
> **Pré-requisito**: Fase 0 (ADR Generation) deve estar completa antes de qualquer fase seguinte.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| A1 | ADR-001 Greenfield Rewrite | `outputs/tobe/docs/decisions/ADR-001-greenfield-rewrite.md` | 🔴 | ⬜ | — |
| A2 | ADR-002 Database | `outputs/tobe/docs/decisions/ADR-002-database.md` | 🔴 | ⬜ | — |
| A3 | ADR-003 Security | `outputs/tobe/docs/decisions/ADR-003-security.md` | 🔴 | ⬜ | — |
| A4 | ADR-004 Backend | `outputs/tobe/docs/decisions/ADR-004-backend.md` | 🔴 | ⬜ | — |
| A5 | ADR-005 Frontend | `outputs/tobe/docs/decisions/ADR-005-frontend.md` | 🔴 | ⬜ | — |
| A6 | ADR-006 Integration | `outputs/tobe/docs/decisions/ADR-006-integration.md` | 🔴 | ⬜ | — |
| A7 | ADR-007 Observability | `outputs/tobe/docs/decisions/ADR-007-observability.md` | 🔴 | ⬜ | — |
| A8 | ADR-008 Audit & Compliance | `outputs/tobe/docs/decisions/ADR-008-audit-log.md` | 🔴 | ⬜ | — |
| A9 | INDEX de ADRs | `outputs/tobe/docs/decisions/INDEX.md` | 🔴 | ⬜ | — |

### Validações Adicionais da Seção A

- [ ] 🔴 **A.V1**: Nenhum ADR contém `Status: [INCOMPLETO]` no campo Status
- [ ] 🔴 **A.V2**: Gate ADR × project-config.yaml PASSED (sem contradições arquiteturais)
- [ ] 🔴 **A.V3**: Todos os 8 ADRs têm seção `## Context` com evidências concretas do AS-IS

**Critério de Aprovação Seção A**: TODOS os 9 artefatos existem + 3 validações PASS = ✅  
**Se falhar**: Gate → **BLOCKED** (ADRs são fundação de todas as fases seguintes)

---

## Seção B — Architecture Core (Fase 1): 4 artefatos

> ⛔ **Categoria**: BLOQUEADOR ABSOLUTO (B1-B3) + CRÍTICO (B4)  
> **Pré-requisito**: Fase 1 (Blueprint + Bounded Contexts + Diagramas) completa.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| B1 | Architecture Blueprint | `outputs/tobe/docs/architecture-blueprint.md` | 🔴 | ⬜ | — |
| B2 | Bounded Context Map | `outputs/tobe/docs/bounded-context-map.md` | 🔴 | ⬜ | — |
| B3 | Solution Structure | `outputs/tobe/solution-structure.md` | 🔴 | ⬜ | — |
| B4 | Diagramas C4 (5 arquivos Mermaid) | `outputs/tobe/diagrams/c4-*.mmd` | 🟡 | ⬜ | — |

### Validações Adicionais da Seção B

- [ ] 🔴 **B.V1**: Architecture Blueprint tem 10 seções obrigatórias completas
- [ ] 🔴 **B.V2**: Bounded Context Map: N BCs têm campo `ddd_approval: true` (aprovado por Squad Owner)
- [ ] 🔴 **B.V3**: Solution Structure define todos os layers (API, Application, Domain, Infrastructure)
- [ ] 🟡 **B.V4**: Diagramas C4 renderizam sem erros (c4-context, c4-container, c4-component, class-diagram, seq-arquitetural)

**Critério de Aprovação Seção B**: B1-B3 existem + B.V1-B.V3 PASS = ✅ (B4 é 🟡 — impacta score mas não bloqueia)

---

## Seção C — Database (Fase 1.4 + 1.5): 6 artefatos

> 🟡 **Categoria**: CRÍTICO  
> **Pré-requisito**: Fase 1.4 (SQL Strategy) + Fase 1.5 (DB Design) completas.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| C1 | SQL Strategy | `outputs/tobe/db/sql-strategy.md` | 🟡 | ⬜ | — |
| C2 | SQL Strategy Manifest | `outputs/tobe/db/sql-strategy.manifest.json` | 🟡 | ⬜ | — |
| C3 | SQL Strategy Backup | `outputs/tobe/db/.history/sql-strategy-*-*.md` | 🟡 | ⬜ | — |
| C4 | DB Design Report | `outputs/tobe/docs/db-design-report.md` | 🟡 | ⬜ | — |
| C5 | MER Diagram (Mermaid) | `outputs/tobe/diagrams/mer-diagram-tobe.mmd` | 🟡 | ⬜ | — |
| C6 | DB Design HTML | `outputs/tobe/docs/db-design-report.html` | 🟡 | ⬜ | — |

### Validações Adicionais da Seção C

- [ ] 🟡 **C.V1**: SQL Strategy manifest: `architecture_open_items == false`
- [ ] 🟡 **C.V2**: SQL Strategy manifest: `policy_version == template_version` (sincronizado)
- [ ] 🟡 **C.V3**: DB Design Report tem §1-§10 completos (Executive Summary … Approval)
- [ ] 🟡 **C.V4**: MER Diagram renderiza sem erros e cobre todos os BCs

**Critério de Aprovação Seção C**: 4/6 artefatos + 3/4 validações = ✅ (não bloqueia, mas score alto requerido)

---

## Seção D — Security (Fase 1.6): 2 artefatos

> 🟡 **Categoria**: CRÍTICO  
> **Pré-requisito**: Fase 1.6 (Security Architecture Design) completa.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| D1 | Security Architecture Doc | `outputs/tobe/docs/security-architecture.md` | 🟡 | ⬜ | — |
| D2 | Security Diagram (Mermaid) | `outputs/tobe/diagrams/security-architecture.mmd` | 🟡 | ⬜ | — |

### Validações Adicionais da Seção D

- [ ] 🟡 **D.V1**: Security Architecture tem 15 seções obrigatórias completas
- [ ] 🟡 **D.V2**: Threat model integrado (seção §5 do security-architecture.md)
- [ ] 🟡 **D.V3**: Security controls mapeados para ADR-003 (consistência)

**Critério de Aprovação Seção D**: 2/2 artefatos + 2/3 validações = ✅

---

## Seção E — Tech Framework (Fase 2): 1 artefato

> ⛔ **Categoria**: BLOQUEADOR ABSOLUTO  
> **Pré-requisito**: Fase 2 (Tech Framework) completa.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| E1 | Tech Framework Document | `outputs/tobe/docs/tech-framework-document.md` | 🔴 | ⬜ | — |

### Validações Adicionais da Seção E

- [ ] 🔴 **E.V1**: Tech Framework consolida 6 triggers (SS + NP + CS + QG + TF + PA)
- [ ] 🔴 **E.V2**: Stack versões definidas para backend + frontend (ex: .NET 10, Angular 18)
- [ ] 🔴 **E.V3**: Decisões técnicas consistentes com ADR-004 (backend) e ADR-005 (frontend)

**Critério de Aprovação Seção E**: E1 existe + 3 validações PASS = ✅  
**Se falhar**: Gate → **BLOCKED** (Build Cycle depende do tech framework)

---

## Seção F — Planning (Fase 3 + 4 + 4.5): 3 artefatos

> ⛔ **Categoria**: BLOQUEADOR ABSOLUTO (F1-F2) + CRÍTICO (F3)  
> **Pré-requisito**: Fase 3 (Sizing), Fase 4 (Migration Plan), Fase 4.5 (Risk Mitigation) completas.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| F1 | Sizing Report | `outputs/tobe/docs/sizing-report.md` | 🔴 | ⬜ | — |
| F2 | Migration Plan | `outputs/tobe/docs/migration-plan.md` | 🔴 | ⬜ | — |
| F3 | Risk Mitigation Plan | `outputs/tobe/risk-mitigation-plan.md` | 🟡 | ⬜ | — |

### Validações Adicionais da Seção F

- [ ] 🔴 **F.V1**: Sizing Report: Story Points + Function Points calculados por BC
- [ ] 🔴 **F.V2**: Migration Plan: Waves definidas com dependências + Gantt chart
- [ ] 🔴 **F.V3**: Migration Plan: Critérios de aceite e rollback por wave
- [ ] 🟡 **F.V4**: Risk Mitigation Plan: Mitigações para riscos P0-P3 do AS-IS

**Critério de Aprovação Seção F**: F1-F2 existem + F.V1-F.V3 PASS = ✅  
**Se falhar**: Gate → **BLOCKED** (Build Cycle sem plano de waves = caos)

---

## Seção G — OpenAPI & Code (Fase 4.61 + 4.7): variável por projeto

> 🟡 **Categoria**: CRÍTICO  
> **Pré-requisito**: Fase 4.61 (OpenAPI Spec) + Fase 4.7 (Coder .NET) + Gate 5.5 (Build & Security) completos.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| G1 | OpenAPI Specs por BC (N specs) | `outputs/tobe/docs/openapi/BC-{N}-openapi.yaml` | 🟡 | ⬜ | — |
| G2 | Código .NET gerado por BC (N BCs) | `outputs/tobe/source-code/` | 🟡 | ⬜ | — |
| G3 | Build Logs (sem erros) | `outputs/tobe/code/{BC}/build.log` | 🟡 | ⬜ | — |
| G4 | CVE Scan Report (ZERO CVEs) | `outputs/tobe/code/cve-scan-report.json` | 🟡 | ⬜ | — |

### Validações Adicionais da Seção G

- [ ] 🟡 **G.V1**: OpenAPI specs: 1 spec por BC (N specs = N BCs do bounded-context-map)
- [ ] 🟡 **G.V2**: OpenAPI specs validam com Swagger Editor / Redoc (sem erros)
- [ ] 🟡 **G.V3**: Código .NET: Build retorna ZERO errors (apenas warnings tolerados)
- [ ] 🟡 **G.V4**: Gate 5.5 (Build & Security): status = PASSED
- [ ] 🟡 **G.V5**: Namespace consistency check: todos os namespaces seguem padrão `{CompanyName}.{ProjectName}.{BC}`
- [ ] 🟡 **G.V6**: Size limits: nenhum arquivo gerado > threshold configurado (ex: 500 LOC)

**Critério de Aprovação Seção G**: N OpenAPI specs + N códigos BC + Build ZERO errors + CVE ZERO = ✅  
**Observação**: Se Gate 5.5 = BLOCKED → esta seção automaticamente FAIL

---

## Seção H — Docs & Tests (Fase 5 + 6): 2 artefatos

> ⛔ **Categoria**: BLOQUEADOR ABSOLUTO (H1) + CRÍTICO (H2)  
> **Pré-requisito**: Fase 5 (Docs) + Fase 6 (Test Plan) completas.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| H1 | Test Plan TO-BE | `outputs/tobe/docs/test-plan-tobe.md` | 🔴 | ⬜ | — |
| H2 | TDD (Test Design Document) | `outputs/tobe/docs/tdd.md` | 🟡 | ⬜ | — |

### Validações Adicionais da Seção H

- [ ] 🔴 **H.V1**: Test Plan cobre: smoke + functional + load + security tests
- [ ] 🔴 **H.V2**: Test Plan mapeia cenários BDD para cada BC crítico
- [ ] 🟡 **H.V3**: TDD define test strategy e ferramentas (xUnit, Playwright, k6, etc)

**Critério de Aprovação Seção H**: H1 existe + H.V1-H.V2 PASS = ✅  
**Se falhar H1**: Gate → **BLOCKED** (Build Cycle sem plano de testes = risco alto)

---

## Seção I — User Experience (Fase 7 + 7.5 + 7.6): 4 artefatos

> 🟢 **Categoria**: IMPORTANTE (não bloqueia, mas impacta score)  
> **Pré-requisito**: Fase 7 (User Journeys), Fase 7.5 (Design System), Fase 7.6 (Prototype) completas.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| I1 | User Journeys TO-BE | `outputs/tobe/docs/user-journeys-tobe.md` | 🟢 | ⬜ | — |
| I2 | Design System Catalog | `outputs/tobe/docs/design-system-catalog.md` | 🟢 | ⬜ | — |
| I3 | Prototype HTML | `outputs/tobe/prototype/index.html` | 🟢 | ⬜ | — |
| I4 | Figma Spec | `outputs/tobe/prototype/figma-spec.md` | 🟢 | ⬜ | — |

### Validações Adicionais da Seção I

- [ ] 🟢 **I.V1**: User Journeys: N personas com cenários BDD (Given-When-Then)
- [ ] 🟢 **I.V2**: Design System: Angular components reutilizáveis catalogados
- [ ] 🟢 **I.V3**: Prototype: navegável + demo script + aprovado pelo cliente

**Critério de Aprovação Seção I**: 3/4 artefatos = ✅ (flexível — não bloqueia gate)

---

## Seção J — Infrastructure (Fase 8): 1 artefato

> 🟢 **Categoria**: IMPORTANTE (não bloqueia, mas impacta score)  
> **Pré-requisito**: Fase 8 (Azure Infra Estimator) completa.

| # | Critério | Path Esperado | Peso | Status | Evidência |
|---|----------|---------------|:----:|:------:|-----------|
| J1 | Azure Infra Estimate | `outputs/tobe/docs/azure-infra-estimate.md` | 🟢 | ⬜ | — |

### Validações Adicionais da Seção J

- [ ] 🟢 **J.V1**: Costing por SKU + ambiente (dev, staging, prod)
- [ ] 🟢 **J.V2**: Estimativa alinhada com sizing-report (Fase 3)

**Critério de Aprovação Seção J**: J1 existe + J.V1 PASS = ✅

---

## Seção K — Aprovações & Sign-offs

> ⛔ **Categoria**: BLOQUEADOR ABSOLUTO  
> **Pré-requisito**: Aprovações formais registradas em `project-config.yaml` (seção `signoffs`).

| # | Stakeholder | Campo em project-config.yaml | Peso | Status | Data | Evidência |
|---|-------------|------------------------------|:----:|:------:|------|-----------|
| K1 | Cliente/Sponsor | `signoffs.architecture_approved_by_client` | 🔴 | ⬜ | — | — |
| K2 | Sponsor / Tech Lead | `signoffs.sponsor_signoff` | 🔴 | ⬜ | — | — |
| K3 | PM/PO (Spec Kit) | `signoffs.spec_kit_approved` | 🔴 | ⬜ | — | — |
| K4 | Squad Owners (DDD) | `bounded-context-map.md` → campo `ddd_approval` por BC | 🟡 | ⬜ | — | — |
| K5 | Security Lead (se aplicável) | `signoffs.security_approval` | 🟡 | ⬜ | — | — |

### Validações Adicionais da Seção K

- [ ] 🔴 **K.V1**: Todas as aprovações obrigatórias (K1-K3) têm valor `true` no config
- [ ] 🟢 **K.V2**: Sign-off registrado com data no project-config.yaml (recomendado para auditoria)
- [ ] 🟡 **K.V3**: Todos os BCs no bounded-context-map têm `ddd_approval: true`

**Critério de Aprovação Seção K**: K1-K3 = true + K.V1-K.V2 PASS = ✅  
**Se falhar**: Gate → **BLOCKED** (Build Cycle sem aprovação formal = não autorizado)

---

## Scoring e Veredicto Final

### Fórmula de Score

```
Pesos:
  🔴 BLOQUEADOR ABSOLUTO: 1 falha → gate: BLOCKED (não calcula score)
  🟡 CRÍTICO: 10 pontos cada
  🟢 IMPORTANTE: 3 pontos cada

Score = (Σ critérios PASS × peso) / (Σ critérios totais × peso) × 100

Exemplo:
  - 20 critérios 🟡 PASS de 25 total → (20 × 10) / (25 × 10) = 80%
  - 8 critérios 🟢 PASS de 10 total → (8 × 3) / (10 × 3) = 80%
  - Score final = média ponderada das seções
```

### Thresholds de Decisão

| Score | Bloqueadores 🔴 | Veredicto | Significado |
|:-----:|:---------------:|-----------|-------------|
| 100% | 0 | ✅ **APPROVED** | Todos os critérios PASS — Build Cycle autorizado |
| 85-99% | 0 | ✅ **APPROVED_WITH_MINOR_GAPS** | Apenas 🟢 faltando — Build Cycle autorizado com alertas |
| 70-84% | 0 | ⚠️ **NEEDS_REMEDIATION** | 🟡 faltando — Build Cycle BLOQUEADO até remediar |
| <70% | 0 | ❌ **BLOCKED** | Score insuficiente — débitos críticos |
| — | ≥1 | ❌ **BLOCKED** | Bloqueadores presentes — Build Cycle NÃO autorizado |

### Relatório de Veredicto

```
════════════════════════════════════════════════════════════════════
                   MIGRATION DESIGN GATE — VEREDICTO
════════════════════════════════════════════════════════════════════

Projeto    : {{PROJECT_NAME}}
Data       : {{VALIDATION_DATE}}
Trace ID   : {{TRACE_ID}}
Executado  : orchestrator-tobe v{{VERSION}}

────────────────────────────────────────────────────────────────────
RESULTADO POR SEÇÃO
────────────────────────────────────────────────────────────────────

Seção A — ADRs (Fase 0)                 [🔴 BLOQUEADOR]  {{STATUS_A}}
  Artefatos: {{A_PASS}}/{{A_TOTAL}}
  Validações: {{A_VAL_PASS}}/{{A_VAL_TOTAL}}
  
Seção B — Architecture Core (Fase 1)    [🔴 BLOQUEADOR]  {{STATUS_B}}
  Artefatos: {{B_PASS}}/{{B_TOTAL}}
  Validações: {{B_VAL_PASS}}/{{B_VAL_TOTAL}}

Seção C — Database (Fase 1.4 + 1.5)     [🟡 CRÍTICO]     {{STATUS_C}}
  Artefatos: {{C_PASS}}/{{C_TOTAL}}
  Validações: {{C_VAL_PASS}}/{{C_VAL_TOTAL}}

Seção D — Security (Fase 1.6)           [🟡 CRÍTICO]     {{STATUS_D}}
  Artefatos: {{D_PASS}}/{{D_TOTAL}}
  Validações: {{D_VAL_PASS}}/{{D_VAL_TOTAL}}

Seção E — Tech Framework (Fase 2)       [🔴 BLOQUEADOR]  {{STATUS_E}}
  Artefatos: {{E_PASS}}/{{E_TOTAL}}
  Validações: {{E_VAL_PASS}}/{{E_VAL_TOTAL}}

Seção F — Planning (Fase 3 + 4 + 4.5)   [🔴 BLOQUEADOR]  {{STATUS_F}}
  Artefatos: {{F_PASS}}/{{F_TOTAL}}
  Validações: {{F_VAL_PASS}}/{{F_VAL_TOTAL}}

Seção G — OpenAPI & Code (Fase 4.61 + 4.7) [🟡 CRÍTICO] {{STATUS_G}}
  Artefatos: {{G_PASS}}/{{G_TOTAL}}
  Validações: {{G_VAL_PASS}}/{{G_VAL_TOTAL}}

Seção H — Docs & Tests (Fase 5 + 6)     [🔴 BLOQUEADOR]  {{STATUS_H}}
  Artefatos: {{H_PASS}}/{{H_TOTAL}}
  Validações: {{H_VAL_PASS}}/{{H_VAL_TOTAL}}

Seção I — User Experience (Fase 7 + 7.5 + 7.6) [🟢 IMPORTANTE] {{STATUS_I}}
  Artefatos: {{I_PASS}}/{{I_TOTAL}}
  Validações: {{I_VAL_PASS}}/{{I_VAL_TOTAL}}

Seção J — Infrastructure (Fase 8)       [🟢 IMPORTANTE]  {{STATUS_J}}
  Artefatos: {{J_PASS}}/{{J_TOTAL}}
  Validações: {{J_VAL_PASS}}/{{J_VAL_TOTAL}}

Seção K — Aprovações & Sign-offs        [🔴 BLOQUEADOR]  {{STATUS_K}}
  Aprovações: {{K_PASS}}/{{K_TOTAL}}
  Validações: {{K_VAL_PASS}}/{{K_VAL_TOTAL}}

────────────────────────────────────────────────────────────────────
SCORE CONSOLIDADO
────────────────────────────────────────────────────────────────────

Bloqueadores 🔴: {{BLOCKERS_COUNT}} detectados
Críticos 🟡:     {{CRITICALS_PASS}}/{{CRITICALS_TOTAL}} ({{CRITICALS_PCT}}%)
Importantes 🟢:  {{IMPORTANTS_PASS}}/{{IMPORTANTS_TOTAL}} ({{IMPORTANTS_PCT}}%)

Score Final: {{FINAL_SCORE}}%

────────────────────────────────────────────────────────────────────
VEREDICTO
────────────────────────────────────────────────────────────────────

{{VERDICT_ICON}} {{VERDICT_TEXT}}

{{#if BLOCKED}}
⛔ Build Cycle NÃO autorizado. Ações corretivas necessárias:

{{#each BLOCKING_ISSUES}}
  ❌ {{this.section}} — {{this.criterion}}: {{this.issue}}
     Ação: {{this.action}}
     Path esperado: {{this.expected_path}}
{{/each}}

→ Após remediar os bloqueadores, re-executar o gate:
  @ava-tobe-orchestrator
  projeto: {{PROJECT_NAME}}
  trigger: Gate 8→Build Cycle — Migration Design Checklist
{{/if}}

{{#if NEEDS_REMEDIATION}}
⚠️ Build Cycle BLOQUEADO até remediar critérios 🟡 CRÍTICOS:

{{#each CRITICAL_ISSUES}}
  ⚠️ {{this.section}} — {{this.criterion}}: {{this.issue}}
     Impacto: {{this.impact}}
     Ação: {{this.action}}
{{/each}}

→ Score atual ({{FINAL_SCORE}}%) abaixo do threshold de 85%.
{{/if}}

{{#if APPROVED_WITH_MINOR_GAPS}}
✅ Build Cycle AUTORIZADO com alertas:

{{#each IMPORTANT_ISSUES}}
  ℹ️ {{this.section}} — {{this.criterion}}: {{this.issue}}
     Recomendação: {{this.recommendation}}
{{/each}}

→ Alertas não bloqueiam, mas recomenda-se completar antes do final da wave.
{{/if}}

{{#if APPROVED}}
✅ Migration Design completo e consistente.
   Build Cycle (F3-F6) autorizado para início.
   
   Próximo passo:
   @ava-stack-orchestrator
   projeto: {{PROJECT_NAME}}
   stack: {{TOBE_STACK}}
{{/if}}

════════════════════════════════════════════════════════════════════
                            FIM DO RELATÓRIO
════════════════════════════════════════════════════════════════════

Evidências detalhadas: {{EVIDENCE_JSON_PATH}}
```

---

## Anexo: Mapeamento de Dependências

```
Fase 0  → ADRs                             → Seção A
Fase 1  → Blueprint + BC Map + Diagramas   → Seção B
Fase 1.4 → SQL Strategy                    → Seção C (parte 1)
Fase 1.5 → DB Design                       → Seção C (parte 2)
Fase 1.6 → Security Architecture           → Seção D
Fase 2  → Tech Framework                   → Seção E
Fase 3  → Sizing                           → Seção F (parte 1)
Fase 4  → Migration Plan                   → Seção F (parte 2)
Fase 4.5 → Risk Mitigation                 → Seção F (parte 3)
Fase 4.61 → OpenAPI Spec                   → Seção G (parte 1)
Fase 4.7 → Coder .NET                      → Seção G (parte 2)
Gate 5.5 → Build & Security Gate           → Seção G (validação)
Fase 5  → Docs TO-BE                       → Seção H (parte 1)
Fase 6  → Test Plan                        → Seção H (parte 2)
Fase 7  → User Journeys                    → Seção I (parte 1)
Fase 7.5 → Design System                   → Seção I (parte 2)
Fase 7.6 → Prototype                       → Seção I (parte 3)
Fase 8  → Azure Infra                      → Seção J

project-config.yaml (signoffs)             → Seção K
```

---

## Anexo: Ações Corretivas por Tipo de Falha

| Falha | Seção | Ação Corretiva |
|-------|-------|----------------|
| ADR ausente | A | Re-executar Fase 0: `@ava-tobe-adr projeto: {name}` |
| ADR com Status: [INCOMPLETO] | A | Enriquecer Context do ADR com evidências concretas do AS-IS |
| Contradição ADR × config | A | Corrigir `project-config.yaml` OU re-executar Fase 0 com config atualizado |
| Blueprint ausente | B | Re-executar Fase 1: `@ava-architecture-design-tobe trigger: CB` |
| BC Map sem DDD Approval | B | Convocar Squad Owners para aprovação formal de cada BC |
| Diagrama não renderiza | B/C/D | Corrigir sintaxe Mermaid e re-gerar |
| SQL Strategy desatualizada | C | Re-executar Fase 1.4 com policy version correta |
| Tech Framework ausente | E | Re-executar Fase 2: todos os triggers SS→NP→CS→QG→TF→PA |
| Migration Plan sem waves | F | Re-executar Fase 4 com bounded-context-map completo |
| Build errors no código | G | Re-executar Fase 4.7: corrigir erros e rodar build novamente |
| CVE detectado | G | Atualizar pacotes NuGet vulneráveis e re-scan |
| Test Plan incompleto | H | Re-executar Fase 6 com functional-requirements completos |
| Sign-off pendente | K | Convocar stakeholder para aprovação formal |

---

**Versão**: 1.0.0  
**Última Atualização**: 2026-05-28  
**Próxima Revisão**: Após 10 execuções do gate (coletar feedback e ajustar thresholds)
