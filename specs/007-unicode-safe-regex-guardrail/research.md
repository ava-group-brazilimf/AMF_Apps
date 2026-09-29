# Research: Unicode-Safe Regex Guardrail

**Feature**: `007-unicode-safe-regex-guardrail`
**Date**: 2026-07-07

---

## 1. .NET — `\p{L}` support in `[RegularExpression]`

**Decision**: Use `@"^\p{L}[\p{L}\s'-]*$"` for name/text fields in all generated C# entities.

**Rationale**: The .NET `System.Text.RegularExpressions` engine supports Unicode general category escapes (`\p{L}`, `\p{Lu}`, `\p{Ll}`, etc.) since .NET 1.0. The `[RegularExpression]` data annotation attribute in `System.ComponentModel.DataAnnotations` passes the pattern directly to the .NET regex engine — so `\p{L}` works out of the box without any additional packages.

**Alternatives considered**:
- `[a-zA-ZÀ-ÿ\s]` — allows only basic Latin + Latin Supplement. Fails on Vietnamese, Greek, Cyrillic, and even some PT-BR precomposed vs. decomposed codepoints.
- `\w` — includes `_` and digits; unsuitable for name validation.
- `[\p{L}\p{M}]` — Unicode Letter + Mark; technically more correct for combining diacritics, but overkill for PT-BR; `\p{L}` alone covers precomposed PT-BR chars (ã, ç, é, ó, ú, etc.) fully.

**References**: [.NET regex character classes — Unicode category](https://learn.microsoft.com/en-us/dotnet/standard/base-types/character-classes-in-regular-expressions#supported-unicode-general-categories)

---

## 2. Angular/TypeScript — Unicode property escapes with `u` flag

**Decision**: Use `Validators.pattern(/^[\p{L}\s\-']+$/u)` for text-field reactive form validators.

**Rationale**: ECMAScript 2018 introduced Unicode property escapes (`\p{L}`, `\p{Script=Latin}`, etc.) behind the `u` flag. Browser support is:
- Chrome 64+ (released Jan 2018)
- Firefox 79+ (released Jul 2020)
- Safari 12+ (released Sep 2018)
- Node.js 10+ (released Apr 2018)

Angular 17 (the current target per `tobe_stack.frontend_version`) targets ES2022 by default (`target: ES2022` in `tsconfig.json`). All supported browsers for Angular 17 fully support `\p{L}` with the `u` flag. No polyfill needed.

**Alternatives considered**:
- `[À-ÿÀ-ÖØ-öø-ÿ]` — covers only Latin Extended-A/B; does not cover precomposed chars outside that range; error-prone to maintain.
- `[a-zA-ZÀ-ú]` — widely seen in legacy code; misses chars outside the range and is not future-proof.
- `Validators.pattern(/^[\p{L}\p{M}\s\-']+$/u)` — adds `\p{M}` (combining marks) for decomposed NFD text; unnecessary for the current use case (PT-BR text processed by .NET backend is NFC).

**References**: [MDN — Unicode property escapes](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions/Unicode_property_escapes)

---

## 3. Insertion points in `coder-angular-frontend.md`

**Decision**: Add the guardrail in **two** places:
1. **Line ~67 principles list** — one-liner entry alongside existing tech principles.
2. **GUARDRAILS DE BUILD section (line ~2955)** — dedicated `⚠️ GUARDRAIL (Unicode Regex PT-BR)` block visible during the build quality check.

**Rationale**: The principles list sets upfront expectations for all generated code. The GUARDRAILS section is the enforcement checklist seen just before the agent emits final files. Placing the guardrail in both locations maximizes the probability the LLM applies it consistently.

---

## 4. Insertion point in `coder-dotnet-backend.md`

**Decision**: Add **G10** immediately after the existing G9 block (around line 209), before the `## Clean Architecture Template` section.

**Rationale**: G1–G9 are sequential error-prevention rules checked before emitting any `.cs` file. G10 fits this pattern as a rule that prevents an incorrect regex pattern from being emitted. Placing it after G9 (the last existing guardrail) and before the structural template section maintains consistency.

---

## 5. Structure of new `angular-patterns-reference.md` section

**Decision**: Add a new `## PT-BR Validation Patterns` section at the **end** of `angular-patterns-reference.md`.

**Rationale**: The file ends after the Pipes section (~line 180). Appending a new section preserves all existing content and is the least disruptive change. Agents that already consume this file (`ava-tobe-architecture-technical`, `ava-stack-angular-frontend`) will see the new section when they read the full file.

The section will include:
- Canonical pattern table (name, phone, CPF, CEP, email)
- Forbidden-pattern counterpart for each
- Explicit note linking to this section from both coder agents

---

## 6. Version bump strategy

**Decision**: PATCH bump (`1.0.0` → `1.0.1`) on both `coder-dotnet-backend.md` and `coder-angular-frontend.md`.

**Rationale**: No new output artifacts, no new input contract fields, no breaking changes to the agent's observable behavior for well-formed inputs. The change is purely additive — a guardrail that prevents incorrect code generation. PATCH is the correct SemVer classification for bug fixes.

`angular-patterns-reference.md` is a **data reference file** (not an agent), so its `version` field in frontmatter is bumped `1.0.0` → `1.0.1` for audit traceability only.

---

## 7. No-clarifications summary

All items from the spec are resolved:

| Was NEEDS CLARIFICATION | Resolution |
|---|---|
| Exact insertion line in `coder-dotnet-backend.md` | After G9, before `## Clean Architecture Template` |
| Exact insertion location in `coder-angular-frontend.md` | Two locations: principles list + GUARDRAILS DE BUILD |
| Whether `\p{L}` needs polyfill in Angular 17 target | No polyfill needed (ES2022 target, all supported browsers) |
| Whether change affects non-text fields | No — G10 explicitly lists exceptions (numeric, CPF, CEP) |
