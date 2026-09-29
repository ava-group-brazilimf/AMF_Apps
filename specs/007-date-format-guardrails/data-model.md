# Data Model: Date Format Guardrails

**Feature**: `007-date-format-guardrails`
**Date**: 2026-07-07
**Change Type**: `modify-existing` — no new entities, no new output contracts

---

## Delta Spec

This feature adds no new agent entities, output artifacts, or pipeline contracts.
It modifies the **instruction content** of two existing agents and adds a documentation
section to one shared reference file.

### Agent Version Delta

| Agent File | Field | Before | After |
| --- | --- | --- | --- |
| `coder-dotnet-backend.md` | `version` | `"1.0.0"` | `"1.1.0"` |
| `coder-dotnet-backend.md` | Guardrails section | G1–G9 | G1–G10 ← already present |
| `coder-angular-frontend.md` | `version` (primary) | `"1.0.0"` | `"1.1.0"` |
| `coder-angular-frontend.md` | `date` (primary) | `2026-06-10` | `2026-07-07` |
| `coder-angular-frontend.md` | Frontmatter keys | 2× `version`, 2× `date` | 1× `version`, 1× `date` |
| `coder-angular-frontend.md` | Guardrails section | (none) | G-DATE ← already present |

> `angular-patterns-reference.md` is not a versioned agent file — no version delta applies.

---

## Guardrail Content Specification (reference — already implemented)

### G10 — `coder-dotnet-backend.md`

Inserted after G9 (NuGet Package Completeness). Full text captured in:
`src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` lines 210–253.

Key invariants encoded by G10:

| Rule | Enforcement |
| --- | --- |
| `DateTime` properties in API DTOs → `DateTimeKind.Utc` | Blocking: agent must not generate `DateTime.Now` in DTO |
| Format specifier `"o"` for round-trip ISO 8601 | Blocking: `JsonSerializerOptions` must not override with date-only format |
| `DateTimeKind.Local` prohibited in API surface | Blocking: agent must emit `❌ PROIBIDO` comment when Local is detected |
| `DateTimeKind.Unspecified` prohibited in API surface | Blocking |
| `DateTime.Now` / `DateTime.Today` prohibited in domain/API logic | Blocking: must use `DateTime.UtcNow` |
| `DateOnly` serialized as `"yyyy-MM-dd"` | Informational |
| Audit fields (`CreatedAt`, `UpdatedAt`) → `DateTime.UtcNow` | Blocking |

### G-DATE — `coder-angular-frontend.md`

Inserted as first guardrail. Full text captured in:
`src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` lines 113–155.

Key invariants encoded by G-DATE:

| Rule | Enforcement |
| --- | --- |
| `LOCALE_ID = 'pt-BR'` in `app.config.ts` providers | Blocking: generated `appConfig` must include the provider |
| `registerLocaleData(localePtBr)` before app config | Blocking: must appear in bootstrap sequence |
| `MAT_DATE_LOCALE = 'pt-BR'` when Material is present | Blocking (conditional on `@angular/material` presence) |
| `DatePipe` always called with `'dd/MM/yyyy'` | Blocking: `{{ x | date }}` without format arg is prohibited |
| No raw ISO string interpolation in templates | Blocking: `{{ x.isoDate }}` for date fields is prohibited |

---

## Frontmatter Fix: `coder-angular-frontend.md`

The current frontmatter (lines 1–13) contains duplicate keys, which violates YAML spec and
Constitution Article II (which requires a single well-formed block):

```yaml
# BEFORE (duplicate keys — INVALID)
---
name: ava-stack-angular-frontend
version: 1.0.0        # ← first occurrence (unquoted)
date: 2026-06-01      # ← first occurrence
description: |
  ...
allowed-tools: Read, Write, Edit, Glob
version: "1.0.0"      # ← duplicate (quoted)
date: 2026-06-10      # ← duplicate
---

# AFTER (clean single-occurrence block)
---
name: ava-stack-angular-frontend
version: "1.1.0"
date: 2026-07-07
description: |
  Gera código Angular production-ready com boas práticas: standalone
  components, signals, lazy loading, MSAL para auth, NgRx para state.
  Versão lida de `tobe_stack.frontend_version` em project-config.yaml.
  Ativa com: "gerar componente Angular", "criar tela", "Angular frontend",
  "NgRx store", "MSAL authentication".
allowed-tools: Read, Write, Edit, Glob
---
```

---

## Output Contract: No Change

Neither agent's `## Output Contract` section is modified. The guardrails affect the
**instructions the agent follows during execution**, not the set of files the agent produces.

---

## CHANGELOG Entry

Both version bumps must be recorded in `CHANGELOG.md` (Constitution Article X):

```markdown
## [Unreleased]

### Changed
- `coder-dotnet-backend` 1.0.0 → 1.1.0: Added G10 — DateTime Serialization guardrail
  enforcing ISO 8601 UTC (`DateTimeKind.Utc`, format `"o"`); `DateTimeKind.Local` prohibited
  in API response types.
- `coder-angular-frontend` 1.0.0 → 1.1.0: Added G-DATE guardrail enforcing `LOCALE_ID=pt-BR`,
  `registerLocaleData`, `MAT_DATE_LOCALE=pt-BR`, and explicit `DatePipe:'dd/MM/yyyy'` format
  in all generated Angular projects. Fixed duplicate `version`/`date` frontmatter keys.
```
