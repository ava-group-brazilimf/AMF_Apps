# Agent Implementation Plan: Business-Rule Traceability & TO-BE Architecture Config Consumption

**Spec**: `specs/020-codegen-business-rules-architecture-config/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (6 files, no new agents) |
| **Primary Requirement** | No coder agent consumes business rules today; the TO-BE mapping doc is generated after codegen, not before. Several `project-config.yaml` sections (`architecture_patterns.*`, `persistence.*`, `quality_gates.*`, `observability.*`) are fully populated but never read. |
| **Technical Approach** | Coders read AS-IS business-rules artifacts directly (guaranteed to exist by F4 time) instead of waiting on the post-codegen TO-BE mapping doc; each coder emits a new traceability report; `docs-tobe.md`'s Fase 5.2 becomes a reconciliation step against those reports. Config consumption is added as an explicit table mapping config values to code decisions, anchored to the real `cqrs: false` override already present in Meu-ERP-001's config. |
| **Implementation Status** | Complete. |

## Constitution Check
- [x] Article I — no hardcoded tech versions.
- [x] Article II — frontmatter unchanged except version/date.
- [x] Article VI — BDD scenarios cover traceability, reconciliation, config-driven codegen.
- [x] Article X — MINOR bump on all 6 files (additive, non-breaking).

## Technical Context
Pure prompt edits; no new scripts or schemas.

## Implementation Phases

### Phase 1 — Business rules in the 5 coder agents ✅ CONCLUÍDO
Added a new mandatory input block reading `outputs/asis/docs/business-rules.md` +
`outputs/asis/code-business-rules.md`, a traceability-marker instruction, and a new
`business-rules-implementation-{backend|frontend}.md` Output Contract entry.

### Phase 2 — `docs-tobe.md` reconciliation ✅ CONCLUÍDO
Added the new input + "Reconciliação com Codegen" section spec to the RN generator.

### Phase 3 — Architecture config consumption (dotnet + angular) ✅ CONCLUÍDO
Added the config → code-decision mapping table, anchored to the real `cqrs: false` Meu-ERP-001
override as the worked example.

### Phase 4 — Verification ✅ CONCLUÍDO
Structural greps — see Test Strategy.

## Complexity Tracking

| Item | Status |
|---|---|
| Consume AS-IS `business-rules.md` vs waiting for TO-BE `regras-negocio.md` | Chose AS-IS-direct — matches existing precedent (many other TO-BE phases already read AS-IS `business-rules.md` directly) and is the only artifact guaranteed to exist before F4 runs |
| Scope of frontend business-rule coverage | Explicitly scoped to UI-visible rules only — a backend-only settlement rule has no frontend representation, this is not a gap (spec §8) |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| Business rules read | `grep -n "code-business-rules.md"` in each of the 5 coder agents | Present |
| Traceability artifact declared | `grep -n "business-rules-implementation"` in each coder's Output Contract | Present |
| Reconciliation wired | `grep -n "Reconciliação com Codegen"` in `docs-tobe.md` | Present |
| Config consumption | `grep -n "architecture_patterns\."` in `coder-dotnet-backend.md` | Present |
