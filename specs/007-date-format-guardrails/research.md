# Research: Date Format Guardrails

**Feature**: `007-date-format-guardrails`
**Date**: 2026-07-07

---

## Finding 1 — All three primary changes already exist

**Investigation method**: grep + read across the three target files.

| File | What was sought | Status |
| --- | --- | --- |
| `coder-dotnet-backend.md` | Guardrail G10 — DateTime/ISO 8601 | ✅ Already present (line 210) |
| `coder-angular-frontend.md` | Guardrail G-DATE — pt-BR locale + DatePipe + MAT_DATE_LOCALE | ✅ Already present (line 113) |
| `angular-patterns-reference.md` | Section "Padrões de Data e Hora" | ✅ Already present (line 174) |

The guardrails and documentation were added directly to the agent files before this spec was formalized — likely as a hotfix to address the date display defect in the Sophia system.

---

## Finding 2 — Version numbers not bumped

Both agent files are still at version `1.0.0` despite carrying new guardrail content added after their
initial publish. Per Constitution Article X:

> Adding optional fields = MINOR bump.  
> New behavior added, no contract-breaking change → MINOR bump.

Required version changes:

| File | Current Version | Required Version |
| --- | --- | --- |
| `coder-dotnet-backend.md` | `1.0.0` | `1.1.0` |
| `coder-angular-frontend.md` | `1.0.0` | `1.1.0` |

The shared reference document (`angular-patterns-reference.md`) is not a versioned agent file —
no frontmatter version bump applies.

---

## Finding 3 — Duplicate YAML frontmatter in `coder-angular-frontend.md`

The file has duplicate keys in its frontmatter block:

```yaml
---
name: ava-stack-angular-frontend
version: 1.0.0          # ← line 3 (no quotes, date 2026-06-01)
date: 2026-06-01
description: |
  ...
allowed-tools: Read, Write, Edit, Glob
version: "1.0.0"        # ← line 12 (quoted, date 2026-06-10)
date: 2026-06-10
---
```

YAML's behavior for duplicate keys is technically undefined (last-write-wins in most parsers).
The canonical state should be: single `version: "1.1.0"`, single `date: 2026-07-07`, matching
the Constitution Article II pattern used in `coder-dotnet-backend.md`.

**Decision**: consolidate to single `version` and `date` fields, bumped to `1.1.0` / `2026-07-07`.

---

## Finding 4 — Content completeness audit

The existing guardrail and reference content is complete and matches the spec's acceptance criteria:

| Acceptance Criterion | Fulfilled? | Evidence |
| --- | --- | --- |
| G10 in backend: `DateTimeKind.Utc`, format `"o"`, `Local` prohibited | ✅ | `coder-dotnet-backend.md` lines 210-253 |
| G-DATE in frontend: `LOCALE_ID='pt-BR'`, `DatePipe:'dd/MM/yyyy'`, `MAT_DATE_LOCALE` | ✅ | `coder-angular-frontend.md` lines 113-155 |
| Angular reference: ✅/❌ examples for locale config + DatePipe + Material | ✅ | `angular-patterns-reference.md` lines 174-230 |
| ISO-8601 → DD/MM/YYYY contract documented | ✅ | `angular-patterns-reference.md` lines 214-223 |

---

## Decision

The spec-007 implementation is **structurally complete**. The remaining implementation
work is administrative hygiene required by the Constitution:

1. Bump `coder-dotnet-backend.md` version `1.0.0` → `1.1.0`
2. Bump and consolidate `coder-angular-frontend.md` frontmatter: fix duplicate
   `version`/`date` keys, set `version: "1.1.0"`, `date: 2026-07-07`
3. Update `CHANGELOG.md` with the two version bumps

No new code, no new sections, no structural changes to either agent.

---

## Alternatives Considered

| Alternative | Why Rejected |
| --- | --- |
| Skip version bumps entirely | Violates Constitution Article X — observable behavior changed; callers relying on version-pinned agent behavior would silently get upgraded content |
| Create a new G11/G12 for Angular | Unnecessary — G-DATE already covers all Angular date concerns comprehensively |
| Move content out of agent and into shared doc only | No — guardrails must be co-located with the agent to be enforced at code-generation time |
