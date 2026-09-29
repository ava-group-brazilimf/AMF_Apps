# Agent Development Tasks: Business-Rule Traceability & TO-BE Architecture Config Consumption

**Plan**: `specs/020-codegen-business-rules-architecture-config/plan.md`
**Status**: Implementation complete; verification passed.

## Category 1 — Version & Contract Verification

- [x] **1.1** `coder-dotnet-backend.md` → `2.1.0`
- [x] **1.2** `coder-java-backend.md` → `2.1.0`
- [x] **1.3** `coder-go-backend.md` → `2.1.0`
- [x] **1.4** `coder-python-backend.md` → `2.1.0`
- [x] **1.5** `coder-angular-frontend.md` → `1.2.0`
- [x] **1.6** `docs-tobe.md` → `1.1.0`

## Category 2 — Implementation

- [x] **2.1** `coder-dotnet-backend.md`: Step 0.5 — business rules (AS-IS direct) + traceability marker + architecture-config mapping table (cqrs/soft_delete/audit_fields/multi_tenancy/connection_resiliency/coverage/tracing/logging) — DONE
- [x] **2.2** `coder-dotnet-backend.md`: Output Contract + Handoff — `business-rules-implementation-backend.md` + `business_rules_implemented` field — DONE
- [x] **2.3** `coder-java-backend.md`: business rules block + Output Contract/Handoff fields — DONE
- [x] **2.4** `coder-go-backend.md`: business rules block + Output Contract/Handoff fields — DONE
- [x] **2.5** `coder-python-backend.md`: business rules block + Output Contract/Handoff fields — DONE
- [x] **2.6** `coder-angular-frontend.md`: Step 1.2b — business rules (UI-visible subset) + architecture-config (cqrs → Signal Store) + Output Contract/Handoff fields — DONE
- [x] **2.7** `docs-tobe.md`: new inputs (`business-rules-implementation-{backend,frontend}.md`) + "Reconciliação com Codegen" section (§7 of the RN artifact structure) — DONE

## Category 3 — Schema Updates — SKIP

New artifact (`business-rules-implementation-{backend|frontend}.md`) follows the same
Markdown-table convention as `SecurityComplianceReport-{Backend,Frontend}.md` — no JSON schema
change.

## Category 4 — Module Registration

N/A — no new agents, no module.yaml changes (all 6 touched agents already registered).

## Category 5 — Quality Gate Checklists

- [x] **5.1** `grep -l "code-business-rules.md"` → present in all 5 coder agents (verified)
- [x] **5.2** `grep -l "business-rules-implementation"` → present in all 5 coder agents (verified)
- [x] **5.3** `grep -n "Reconciliação com Codegen"` in `docs-tobe.md` → present (verified)
- [x] **5.4** `grep -n "architecture_patterns\."` in `coder-dotnet-backend.md` → present, with mapping table (verified)

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — business rules traceability wired into all 5 coder agents' Output Contract + Handoff
- [x] **6.2** CA02 — `docs-tobe.md` Fase 5.2 reconciles against codegen reports instead of being the sole source
- [x] **6.3** CA03 — `architecture_patterns.cqrs: false` → Application Services mapping documented with the real Meu-ERP-001 override as the worked example

## Category 7 — Documentation

- [x] **7.1** This spec-kit documentation (spec.md, plan.md, tasks.md) — DONE

## Completion Checklist

- [x] Business rules consumed from AS-IS directly (not the post-codegen TO-BE doc) — sequencing
  gap closed without reordering `orchestrator-tobe.md`'s phases
- [x] Frontend business-rule scope explicitly limited to UI-visible rules (not a gap — spec §8)
- [x] Real `project-config.yaml` `cqrs: false` override used as the concrete acceptance scenario,
  not a hypothetical
- [x] `docs-tobe.md`'s reconciliation is non-blocking (⚠️ Divergente, not a HARD STOP) — codegen
  already ran by the time Fase 5.2 executes; this is a QA signal, not a retroactive gate
