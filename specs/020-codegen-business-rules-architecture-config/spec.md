# Agent Specification: Business-Rule Traceability & TO-BE Architecture Config Consumption in Codegen

**Feature Branch**: `020-codegen-business-rules-architecture-config`
**Created**: 2026-07-15
**Status**: Implemented
**Change Type**: modify-existing (6 files across `tech-stack` and `tobe-architecture` modules — MINOR each)
**Input**: "As regras de negócio devem ser consumidas durante a codificação, todas as regras de
negócio devem ser implementadas na fase geração de código. Os agentes de codificação devem levar
em consideração arquitetura to-be projetada, os arquivos de configuração da arquitetura, arquivo
de configuração da tech-stack que são injetados no project-config."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-stack-dotnet-backend` | `tech-stack/agents/coder-dotnet-backend.md` | `2.0.0` → `2.1.0` (MINOR — new mandatory input + output artifact) |
| `ava-stack-java-backend` | `tech-stack/agents/coder-java-backend.md` | `2.0.0` → `2.1.0` (MINOR) |
| `ava-stack-go-backend` | `tech-stack/agents/coder-go-backend.md` | `2.0.0` → `2.1.0` (MINOR) |
| `ava-stack-python-backend` | `tech-stack/agents/coder-python-backend.md` | `2.0.0` → `2.1.0` (MINOR) |
| `ava-stack-angular-frontend` | `tech-stack/agents/coder-angular-frontend.md` | `1.1.0` → `1.2.0` (MINOR) |
| `ava-docs-tobe` | `tobe-architecture/agents/docs-tobe.md` | `1.0.0` → `1.1.0` (MINOR — RN generator cross-checks new artifact) |

**Phase**: F4 (coders) + F2 (`docs-tobe.md` RN trigger). **Depends on**: `specs/019` (same
Execution Steps sections touched there).

---

## 2. Problem Statement

Direct verification (grep across `coder-dotnet-backend.md` and `coder-angular-frontend.md`)
confirmed **zero references** to any business-rule artifact in either coder. No coder agent in
the `tech-stack` module reads `BR-XXXX`-tagged business rules, and none produces a
rule-to-code traceability record.

The TO-BE-side business-rules mapping document (`outputs/tobe/docs/regras-negocio.md`) exists
in principle — but it is produced by `docs-tobe.md`'s `RN` trigger at **Fase 5.2** of
`orchestrator-tobe.md`, which runs **after** Fase 4.7 (codegen) and after Fase 5.5 (build
validator gate). Even if a coder wanted to consume it, it would not exist yet at codegen time.

Separately, `project-config.yaml` carries several sections that are fully populated (with real,
project-specific decisions — e.g. `architecture_patterns.cqrs: false` in the actual Meu-ERP-001
config, with the comment "Decided: no CQRS for Meu-ERP — use Application Services pattern") but
are never read by any coder agent: `architecture_patterns.*`, `persistence.*` (beyond
`connection_source`), `quality_gates.*`, `observability.*`. Confirmed by grep: zero occurrences
of `architecture_patterns.` in `coder-dotnet-backend.md`.

---

## 3. Decision

### 3.1 Business rules — direct AS-IS consumption (bypassing the sequencing gap)
All 5 coder agents (dotnet, java, go, python, angular) gain a new **mandatory, blocking**
pre-generation input, at the same tier as `architecture-blueprint.md`:
`projects/{project_name}/outputs/asis/docs/business-rules.md` +
`projects/{project_name}/outputs/asis/code-business-rules.md` (the AST-derived rules, more
precise for Delphi-origin projects). This is the AS-IS source, not the TO-BE
`regras-negocio.md` — deliberately, because the AS-IS artifact is guaranteed to exist by the
time F4 runs (F1 always completes before F4 per Article III), while the TO-BE one does not.

Each backend coder must, for every `BR-XXXX` rule scoped to a bounded context it generates:
implement it, and record a traceability marker (XML doc comment referencing the rule ID) at the
point of implementation. Each coder produces a new artifact,
`outputs/tobe/docs/business-rules-implementation-{backend|frontend}.md`, mapping
`BR-ID → file:method/class`. A rule with no implementation is a gate failure — the coder cannot
report `COMPLETED` with unmapped rules remaining.

### 3.2 `docs-tobe.md` (`RN` trigger, Fase 5.2) — reconciliation, not sole source
Gains a new input: the `business-rules-implementation-{backend|frontend}.md` artifacts from
§3.1. Fase 5.2 continues to produce `regras-negocio.md` as before, but now **cross-references**
it against what the coders actually reported as implemented, flagging any `BR-XXXX` present in
`regras-negocio.md`'s TO-BE mapping but absent from the coders' implementation reports (and vice
versa) in a new "Reconciliação com Codegen" section. This closes the sequencing gap without
reordering `orchestrator-tobe.md`'s phases: Fase 5.2 becomes a post-hoc QA cross-check, not the
sole source of truth for what should be implemented.

### 3.3 TO-BE architecture config consumption
`coder-dotnet-backend.md` and `coder-angular-frontend.md` gain explicit instructions to read and
act on `project-config.yaml` sections currently dead: `architecture_patterns.*`,
`persistence.*` (full section, not just `connection_source`), `quality_gates.*`,
`observability.*`. A concrete config → code-decision mapping table is added (e.g.
`architecture_patterns.cqrs: false` → Application Services instead of MediatR;
`persistence.soft_delete: true` → `ISoftDelete`; `persistence.audit_fields: true` →
`AuditableEntity` base type; `observability.tracing: opentelemetry` → OpenTelemetry
instrumentation). The real Meu-ERP-001 `cqrs: false` override is used as the concrete
acceptance scenario (§5).

---

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `coder-dotnet-backend.md` | New business-rules input + traceability gate; new architecture-config consumption table |
| `coder-java-backend.md`, `coder-go-backend.md`, `coder-python-backend.md` | New business-rules input + traceability gate |
| `coder-angular-frontend.md` | New business-rules input + traceability gate (UI-visible rules only); architecture-config consumption table |
| `docs-tobe.md` | New reconciliation input + "Reconciliação com Codegen" section in `regras-negocio.md` |

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — All AS-IS business rules implemented and traceable (CA01)
**Given** `outputs/asis/docs/code-business-rules.md` lists `BR-0001..BR-0006` for the
"ContasPagar" and "ContasReceber" BCs, **When** `ava-stack-dotnet-backend` generates those BCs,
**Then** each `BR-000N` appears as an XML doc comment on the handler/method implementing it, and
`outputs/tobe/docs/business-rules-implementation-backend.md` lists all 6 with file:method
references — none omitted.

### Scenario 2 — `docs-tobe.md` reconciles, doesn't duplicate authority (CA02)
**Given** `business-rules-implementation-backend.md` and `-frontend.md` exist, **When**
`docs-tobe.md` runs `RN` at Fase 5.2, **Then** `regras-negocio.md` includes a "Reconciliação com
Codegen" section confirming 100% match, or listing any discrepancy explicitly.

### Scenario 3 — `cqrs: false` override reflected in generated code (CA03)
**Given** `project-config.yaml` has `architecture_patterns.cqrs: false` (the real Meu-ERP-001
override, with rationale "use Application Services pattern"), **When**
`ava-stack-dotnet-backend` generates the Application layer, **Then** it generates Application
Services (not MediatR Commands/Queries/Handlers), consistent with the override.

---

## 6. Quality Gate Requirements

- [x] Agent IDs unchanged (Article II)
- [x] MINOR bump on all 6 touched files — new inputs/outputs added, nothing removed (Article X)
- [x] BDD scenarios cover business-rule traceability, reconciliation, and config-driven codegen (Article VI)
- [x] No technology versions hardcoded (Article I)

## 7. Dependencies
- `specs/019` — same Execution Steps sections in the 5 coder agents.
- AS-IS artifacts `business-rules.md` / `code-business-rules.md` — pre-existing, unmodified.

## 8. Exclusions
- `orchestrator-tobe.md`'s Fase ordering is **not** changed — Fase 5.2 remains after Fase 4.7.
- Frontend business-rule implementation is scoped to UI-visible/validation rules only (a rule
  about server-side settlement logic has no frontend representation) — the frontend
  traceability report may legitimately be a subset of the backend one; this is not a gap.
- Full architecture-config consumption (persistence engine choice, infra/observability
  provisioning) remains primarily a backend concern in this spec; `infrastructure.*` (IaC-level)
  is explicitly out of scope — that's `devops-agents`' domain, not F4 codegen's.

## 9. Assumptions
- `code-business-rules.md` (AST-derived) is preferred over `business-rules.md` (doc-derived)
  when both exist, for precision; both are read, and `code-business-rules.md`'s `BR-XXXX` IDs
  are treated as authoritative when they conflict.

## Success Criteria

| Criterion | Measure |
|---|---|
| Business rules read | `grep -n "code-business-rules.md"` present in all 5 coder agents |
| Traceability artifact | `grep -n "business-rules-implementation"` present in all 5 coder agents' Output Contract |
| Reconciliation wired | `grep -n "Reconciliação com Codegen"` present in `docs-tobe.md` |
| Config consumption | `grep -n "architecture_patterns\."` present in `coder-dotnet-backend.md` |
| Versions bumped | Per §1 table |
