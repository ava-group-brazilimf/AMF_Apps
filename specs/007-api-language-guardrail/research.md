# Research: Language Normalization Guardrail (#2304)

**Branch**: `007-api-language-guardrail`
**Date**: 2026-07-07

---

## R1 — Current State of `openapi-spec-tobe.md`

**Decision**: The file (agent `ava-tobe-spec`) has no `version` field in frontmatter.  
**Rationale**: Per Article X (SemVer), adding a MINOR change requires a version bump. Since there is no current version, it will be initialized at `"1.1.0"` (baseline 1.0.0 + MINOR bump for this guardrail).  
**Insertion point**: New section `### Guardrail de Idioma — Normalização para Inglês` will be added inside `## Skills`, immediately before the existing `## i18n` section (line ~276). This placement is correct because:
- Skills section is where derivation rules live
- The i18n section at line 276 covers *description prose* language; the new guardrail covers *identifiers* — logically prior
- The transliteration table belongs here so the agent reads it during path/operationId derivation

**File ends at**: ~line 283 (i18n section is the last substantive section).

---

## R2 — Current State of `coder-dotnet-backend.md`

**Decision**: The file has `version: "1.0.0"` in frontmatter → bump to `"1.1.0"`.  
**Rationale**: MINOR bump: new G10 guardrail added; no output contract change, no breaking change.  
**Insertion point**: G10 will be added immediately after the G9 section (which ends at line ~215) and before the `## Clean Architecture Template` section (~line 219). The guardrails block ends at G9 today; G10 follows naturally.  
**Reference mechanism**: G10 will reference the transliteration table by cross-link to `openapi-spec-tobe.md § Guardrail de Idioma — Normalização para Inglês` — avoiding duplication.  
**Cross-reference from docs-research**: The `G1-G9 existing guardrails` check at line 59 mentions `G1-G9` — the routing guard section. After this change, the reference must read `G1-G10`.

---

## R3 — Transliteration Table Design

**Decision**: The canonical table will live in `openapi-spec-tobe.md`. It covers 25+ PT-BR → EN pairs grouped by domain cluster.  
**Rationale**: 
- Single source of truth — `coder-dotnet-backend.md` references it, never copies it
- 10 pairs is the spec minimum; 25+ pairs covers typical ERP domain vocabulary from Delphi legacy codebases (school/finance/inventory domains)
- Table format: Markdown two-column `| PT-BR | EN (singular) |` for clarity during LLM execution

**Groups**:
- **Pessoas/Entidades**: aluno→student, professor→instructor, funcionario→employee, fornecedor→supplier, cliente→customer, socio→partner
- **Transações**: pagamento→payment, fatura→invoice, pedido→order, lancamento→entry, recibo→receipt
- **Académico**: matricula→enrollment, nota→grade, turma→group, curso→course, disciplina→subject
- **Inventário**: produto→product, estoque→stock, categoria→category
- **Sistema**: usuario→user, perfil→profile, permissao→permission, relatorio→report

**Transliteration algorithm** (documented in rules):
1. Tokenize Command/Query name by CamelCase/PascalCase boundaries
2. For each token, look up in table (case-insensitive)
3. If found → replace with English equivalent, preserving original casing style
4. If NOT found → keep original token AND flag path/operationId with `# [NEEDS TRANSLATION: <token>]`
5. Apply path kebab-casing AFTER translation

**Alternatives considered**: External YAML file for the table → rejected (agents must be self-contained `.md` files to work as LLM prompts without filesystem reads for the table itself).

---

## R4 — `[LANG-NORM]` Annotation Convention

**Decision**: Inline YAML comment format: `# [LANG-NORM] <pt-br-token> → <en-token>`.  
**Rationale**: Inline comments in YAML are zero-cost (they don't affect spec validity) and are visible to humans reviewing the generated spec. They provide an audit trail for transliteration decisions.  
**Placement**: On the same line as the translated value or on the line immediately above.

---

## R5 — Sophia Project Availability

**Decision**: The Sophia project does NOT exist in the current workspace (`projects/` contains `_template/`, `Meu-ERP/`, `test-determinism/`, `Test-PBI366/`). Scenario 4 validation is **deferred** to a separate QA task.  
**Rationale**: Spec assumption §8 explicitly states "if absent, Scenario 4 is deferred to the next sprint".  
**Impact**: Tasks for Scenario 4 (child task #2308) will be flagged as `deferred` pending Sophia project availability.

---

## R6 — `G1-G9` Reference Update in Routing Guard

**Decision**: The line `→ PROSSEGUIR com guardrails G1-G9 existentes (non-blocking)` in `coder-dotnet-backend.md` must be updated to `G1-G10` as part of this change.  
**Rationale**: The routing guard explicitly names the guardrail range. After adding G10 it would be misleading to still read G1-G9.  
**Alternatives considered**: Leave as-is → rejected because it would confuse future readers about whether G10 is active when bundle is absent.

---

## R7 — CHANGELOG.md Entry Required

**Decision**: A MINOR bump entry will be added to `CHANGELOG.md` for both agents.  
**Rationale**: Constitution Article X: "Breaking changes require migration notes in CHANGELOG.md" — applies to MINOR bumps as a best practice even if not strictly mandated.  
**Format**: Existing CHANGELOG format will be followed.
