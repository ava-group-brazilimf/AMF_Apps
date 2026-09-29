# AVA Fabric — Governance: Artifact Language (i18n)

> **Version:** 1.0.0 — May 2026
> **Applies to:** ALL agents that generate artifacts — every module in `src/modules/ava-fabric-agents/`.
> **Reference this file as:** `@governance-apps`

---

## ABSOLUTE INVARIANT

> ⚠️ **ALL agents that generate artifacts MUST follow every rule in this document. No exceptions.**
> This rule has **priority over all other instructions** in the agent file, including the system prompt language.
> When encountered after other content, it retroactively governs ALL remaining artifact generation in the session.

---

## 1. Config Reading Protocol (MANDATORY — execute before anything else)

Before processing any other instruction, read:

```yaml
# projects/{project_name}/context/project-config.yaml
language: "pt" | "en"   # default when absent or empty: "pt"
```

| Value | Behavior |
|---|---|
| `"en"` | Generate ALL artifact content in **English** — headings, section names, table labels, findings, recommendations, narrative text |
| `"pt"` | Generate in **Portuguese** — default behavior |

**Invariants:**
- File names, YAML keys, JSON field names, and code identifiers remain **unchanged** regardless of language.
- Technical terms without a natural translation (e.g., "Bounded Context", "CQRS", "Wave", "Strangler Fig") may remain in English even when `language: "pt"`.
- If `language` key is absent or empty → default to `"pt"`.

---

## 2. Orchestrator Propagation Mandate (MANDATORY)

> ⚠️ **INVARIANT: `language` MUST appear explicitly in every sub-agent dispatch block. No exceptions.**

Any orchestrator that invokes sub-agents MUST pass `language` in the parameter list:

```
Passar: { trace_id, ..., language, ... }
```

**Applies to ALL forms of dispatch:**
- `Passar explicitamente: { ... }` blocks
- `Passar para cada um: { ... }` blocks
- Any `Invocar {agent}` instruction that accepts parameters

**Sub-agent fallback (when `language` is not received via dispatch):**
Read directly from `projects/{project_name}/context/project-config.yaml`.
⛔ Never assume `"pt"` without first checking the config file.

---

## 3. Template i18n Tables

When filling a report template and `language: "en"`, replace Portuguese section headings and table labels per the tables below.

### asis-solution-report

| PT | EN |
|---|---|
| Sumário da Arquitetura AS-IS | AS-IS Architecture Summary |
| Blueprint Arquitetural | Architecture Blueprint |
| Padrões Identificados | Identified Patterns |
| Padrão dominante | Dominant Pattern |
| Bounded contexts identificados | Identified Bounded Contexts |
| Risco de migração global | Global Migration Risk |
| Forms / telas mapeadas | Mapped Forms / Screens |
| Units / classes identificadas | Identified Units / Classes |
| Padrão | Pattern |
| Ocorrências | Occurrences |
| % do código | % of code |
| Risco | Risk |
| Tamanho estimado | Estimated Size |
| Tecnologia | Technology |
| Escopo | Scope |
| Diagramas | Diagrams |

### inventory-report

| PT | EN |
|---|---|
| Inventário Quantitativo AS-IS | AS-IS Quantitative Inventory |
| Totalizadores Gerais | General Totals |
| Distribuição por Módulo | Module Distribution |
| Métrica | Metric |
| Total | Total |
| Linhas de código (LOC) | Lines of Code (LOC) |
| Linhas de código efetivo (sem comentários/brancos) | Effective LOC (no comments/blanks) |
| Número de arquivos | File Count |
| Número de classes / forms | Class / Form Count |
| Número de métodos / procedures | Method / Procedure Count |
| Número de módulos / packages | Module / Package Count |
| Número de camadas identificadas | Identified Layer Count |
| Stored procedures | Stored Procedures |
| Tabelas no banco | Database Tables |
| Módulo | Module |
| Classes | Classes |
| Métodos | Methods |
| Complexidade Média | Avg Complexity |
| Camadas Identificadas | Identified Layers |
| Camada | Layer |
| Descrição | Description |
| Arquivos | Files |

### gaps-risks-report

| PT | EN |
|---|---|
| Sumário Executivo de Riscos | Executive Risk Summary |
| Risk Register Completo | Full Risk Register |
| Top Riscos Críticos (P0) | Top Critical Risks (P0) |
| Gaps Identificados | Identified Gaps |
| Gaps Funcionais | Functional Gaps |
| Gaps Técnicos | Technical Gaps |
| Severidade | Severity |
| Quantidade | Count |
| Categoria | Category |
| Probabilidade | Probability |
| Impacto | Impact |
| Score de Risco Global | Global Risk Score |
| Mitigação | Mitigation |
| Responsável | Owner |
| Funcionalidade AS-IS | AS-IS Feature |
| Status no TO-BE | TO-BE Status |
| Ação Necessária | Required Action |
| Componente AS-IS | AS-IS Component |
| Equivalente TO-BE | TO-BE Equivalent |
| Complexidade | Complexity |

### bounded-context-map-template

| PT | EN |
|---|---|
| Decisão de Consolidação AS-IS → TO-BE | Consolidation Decision AS-IS → TO-BE |
| Decisão | Decision |
| Responsabilidade | Responsibility |
| O que este contexto É responsável por | What this context IS responsible for |
| O que este contexto NÃO É responsável por | What this context is NOT responsible for |
| Linguagem Ubíqua | Ubiquitous Language |
| Termo | Term |
| Definição | Definition |
| Notas | Notes |
| Relacionamentos | Relationships |
| Parceiro | Partner |
| Tipo de Relação | Relationship Type |
| Padrão DDD | DDD Pattern |
| Repositórios | Repositories |
| Critérios de Aceite | Acceptance Criteria |
| Mudanças críticas AS-IS → TO-BE | Critical Changes AS-IS → TO-BE |

### migration-plan-report

| PT | EN |
|---|---|
| Sumário do Plano | Plan Summary |
| Cronograma de Waves (Gantt) | Wave Schedule (Gantt) |
| Detalhamento das Waves | Wave Details |
| Estratégia | Strategy |
| Módulos a migrar | Modules to migrate |
| Total de waves | Total waves |
| Story points estimados | Estimated story points |
| Duração total | Total duration |
| Team size recomendado | Recommended team size |
| Módulos | Modules |
| Duração | Duration |
| Risco | Risk |
| Bounded Contexts Incluídos | Included Bounded Contexts |
| Dependências | Dependencies |
| Sem dependências de waves anteriores | No dependencies on previous waves |
| Critérios de Aceite (go/no-go) | Acceptance Criteria (go/no-go) |
| Paridade funcional ≥ | Functional parity ≥ |
| Cliente validação funcional concluída | Client functional validation completed |
| Human go/no-go gate aprovado | Human go/no-go gate approved |

### docs-tobe

> ⛔ **Parser-lock exception**: The headings `## Métricas`, `## Tabela de Rastreabilidade`,
> and `## Regras por Bounded Context` in `regras-negocio.md` are matched via literal regex
> by `build_summary_comprehensive.py`. They MUST NOT be translated even when `language: "en"`.
> All other content in the tables below IS translatable.

#### regras-negocio.md (body content only — headings locked above)

| PT | EN |
|---|---|
| Regras de Negócio TO-BE | Business Rules TO-BE |
| Total de regras AS-IS catalogadas | Total AS-IS rules catalogued |
| Regras preservadas sem alteração | Rules preserved unchanged |
| Regras corrigidas / evoluídas | Rules corrected / evolved |
| Regras eliminadas | Eliminated rules |
| Regras críticas endereçadas | Critical rules addressed |
| Bounded contexts que recebem regras | Bounded contexts receiving rules |
| Cobertura | Coverage |
| Regra | Rule |
| Decisão | Decision |
| Elemento DDD | DDD Element |
| Impacto | Impact |
| Reconciliação com Codegen | Codegen Reconciliation |
| Implementada | Implemented |
| Divergente | Divergent |
| Não aplicável a codegen | Not applicable to codegen |
| Reconciliação não disponível | Reconciliation unavailable |
| Gap List — Regras sem BC Mapeado | Gap List — Rules without Mapped BC |
| Regras Novas Introduzidas no TO-BE | New Rules Introduced in TO-BE |

#### functional-requirements-tobe.md

| PT | EN |
|---|---|
| Cabeçalho | Header |
| Tabela de métricas | Metrics table |
| Requisitos Funcionais AS-IS → TO-BE | Functional Requirements AS-IS → TO-BE |
| Requisitos Não Funcionais AS-IS → TO-BE | Non-Functional Requirements AS-IS → TO-BE |
| Novos Requisitos TO-BE | New TO-BE Requirements |
| Gap List | Gap List |
| Pendente Aprovação | Pending Approval |
| Aprovado (PO) | Approved (PO) |
| Aprovado (Stakeholder) | Approved (Stakeholder) |
| Total de FRs AS-IS | Total AS-IS FRs |
| % preservados | % preserved |
| Total de NFRs AS-IS | Total AS-IS NFRs |
| Novos requisitos adicionados por grupo | New requirements added per group |
| Descrição | Description |
| Decisão | Decision |
| Prioridade | Priority |
| Observação | Note |
| Categoria | Category |
| Fonte | Source |
| Status Aprovação | Approval Status |
| BC NÃO DEFINIDO | BC NOT DEFINED |

#### technical-design-document.md

| PT | EN |
|---|---|
| Visão Geral | Overview |
| Sumário de Arquitetura | Architecture Summary |
| Decisões de Design por Bounded Context | Module Design Decisions per Bounded Context |
| Modelo de Dados | Data Model |
| Arquitetura de Segurança | Security Architecture |
| Design de Observabilidade | Observability Design |
| Padrões de API | API Standards |
| Fluxos Técnicos Críticos | Critical Technical Flows |
| Diagramas de Sequência e Rastreabilidade | Sequence Diagrams & Traceability |
| Configuração de Ambientes | Environment Configuration |
| Guia de Resolução de Problemas | Troubleshooting Guide |
| Referência Rápida de Onboarding | Onboarding Quick Reference |
| Índice de ADRs | ADR Index |
| Índice de Diagramas | Diagram Index |
| Glossário | Glossary |
| PENDENTE — artefato ainda não gerado | PENDING — artifact not yet generated |

#### api-map.md

| PT | EN |
|---|---|
| Tela | Screen |
| sem tela mapeada | no screen mapped |

---

## 4. Summary HTML i18n

The Summary HTML agent (`ava-summary`) uses a JavaScript i18n dictionary. When `language: "en"`:

- All section titles, KPI labels, and navigation items MUST render in English.
- The i18n dictionary key `"lang"` MUST be set to `"en"` in the generated HTML.
- PT fallback labels MUST NOT appear in the final HTML when `language: "en"`.

---

*AVA Fabric — `@governance-apps` v1.0.0 — May 2026*
