# Agent Development Tasks: Language Normalization Guardrail

**Plan**: `specs/007-api-language-guardrail/plan.md`
**Change Type**: `modify-existing` | **Phase**: F2 + F3 | **PBI**: #2304
**Agents patched**: `ava-tobe-spec` · `ava-stack-dotnet-backend`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 1 must finish before Category 2. Categories 4, 5, 6, 7 are N/A or can run
> parallel after Category 2. Category 3 (Schema) is N/A — no shared schema changes.

---

## Category 1 — Frontmatter & Version Bumps

> `modify-existing` — no new file creation. This category updates frontmatter in the two target agent files to record the MINOR version bump before any behavioral changes are written.

- [X] **1.1** Read full current content of `src/modules/ava-fabric-agents/tobe-architecture/agents/openapi-spec-tobe.md` (confirm no `version:` field exists in frontmatter)
- [X] **1.2** Add `version: "1.1.0"` to frontmatter of `openapi-spec-tobe.md`, after the `allowed-tools:` line — do NOT add any other new fields
- [X] **1.3** Read full current content of `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` (confirm `version: "1.0.0"`)
- [X] **1.4** Update `version: "1.0.0"` → `version: "1.1.0"` in frontmatter of `coder-dotnet-backend.md`
- [X] **1.4b** Remove `date: 2026-06-10` key from frontmatter of `coder-dotnet-backend.md` — this field violates Constitution Article II (only `name`, `version`, `description`, `allowed-tools` are permitted)
- [X] **1.5** Verify: frontmatter of both files contains ONLY `name`, `version`, `description`, `allowed-tools` — no other keys (Constitution Article II)

---

## Category 2 — Agent Behavior & Instructions (Child tasks #2305, #2306, #2307)

> Depends on Category 1. Three logical sub-groups, one per PBI child task.
> All content added to agent bodies MUST be written in Brazilian Portuguese (Constitution Article V).

### 2A — Guardrail de Idioma em `openapi-spec-tobe.md` (PBI #2305 + #2306)

- [X] **2.1** Locate the exact insertion point in `openapi-spec-tobe.md`: find the line `## i18n — Idioma dos Artefatos` — new section is inserted immediately before it, still inside `## Skills`
- [X] **2.2** Insert section header `### Guardrail de Idioma — Normalização para Inglês` with a `⚠️` enforcement banner (level: ERROR — bloqueante) and one-paragraph explanation of why PT-BR identifiers in paths and operationIds are forbidden (Scenario 1, Spec §4.1)
- [X] **2.3** Insert transliteration algorithm block (5 numbered steps): strip Command/Query suffix → tokenize by PascalCase → lookup table → reconstruct identifier (camelCase for operationId, kebab-case plural for path) → annotate with `# [LANG-NORM]` — based on `data-model.md §2`. **Nota:** a reconstrução PascalCase para nomes de classe C# é responsabilidade exclusiva do G10 em `coder-dotnet-backend.md`; não incluir essa etapa aqui
- [X] **2.4** Insert `#### Tabela de Transliteração PT-BR → EN` with all 25 canonical pairs from `data-model.md §1`, grouped into 5 domain clusters: Pessoas/Entidades · Transações · Acadêmico · Inventário · Sistema (Spec §4.2, Scenario 2 AC1)
- [X] **2.5** Insert `[LANG-NORM]` annotation convention rule: format `# [LANG-NORM] <pt-br> → <en>` on the same line or immediately above the translated YAML value (Research R4)
- [X] **2.6** Insert `[NEEDS TRANSLATION]` fallback rule: when a token has no table entry, write `# [NEEDS TRANSLATION: <token>]` above the path/operationId — do NOT silently omit the endpoint (Spec §4.1 AC3, Spec §4.2 AC2)
- [X] **2.7** Verify: new section is self-contained (no external file reads required to execute the transliteration); all rule text is in Portuguese; confirm the algorithm is determinístico — mesma entrada sempre produz mesma saída independente da ordem de execução (Spec §4.2 AC3)

### 2B — Guardrail G10 em `coder-dotnet-backend.md` (PBI #2307)

- [X] **2.8** Locate insertion point in `coder-dotnet-backend.md`: find the end of `### G9 — NuGet Package Completeness` block (before `## Clean Architecture Template`)
- [X] **2.9** Insert `### G10 — Language Normalization — Identificadores C# em inglês` with scope list: Controller class names, Command records, Query records, Handler classes, DTO records, file names (.cs), namespace segments (Spec §4.3 AC1)
- [X] **2.10** Insert explicit XML doc exemption paragraph: XML `<summary>`, `<param>`, `<returns>` tags and C# string literals MAY be written in PT-BR — this is the only allowed exception (Spec §4.3 AC2)
- [X] **2.11** Insert 3-step resolution algorithm: (1) if identifier came from openapi-spec normalized output → use as-is (G10 is no-op); (2) if from bounded-context-map directly → apply transliteration from `openapi-spec-tobe.md § Tabela de Transliteração PT-BR → EN`; (3) if no translation available → flag with `// [G10-NEEDS-TRANSLATION: <original>]` and preserve original temporarily (Spec §4.3 AC3, AC4)
- [X] **2.12** Insert `// [G10-NEEDS-TRANSLATION]` annotation convention documentation (mirrors `[LANG-NORM]` from Agent 1)
- [X] **2.13** Verify: G10 cross-reference points to the exact section heading added in task 2.2 — single source of truth, no table duplication

### 2C — Routing Guard Reference Update

- [X] **2.14** In `coder-dotnet-backend.md`, find the line containing `PROSSEGUIR com guardrails G1-G9 existentes (non-blocking)` and update to `G1-G10 existentes (non-blocking)` (Research R6)
- [X] **2.15** Verify: no other references to `G1-G9` remain in `coder-dotnet-backend.md` (run grep before and after)

---

## Category 3 — Shared Schema Updates

> **N/A** — This feature adds inline rule text to agent `.md` files only. No `agent-task.schema.json` or `agent-result.schema.json` fields are added or changed. Skip this category entirely.

---

## Category 4 — Module Registration

> **N/A** — `modify-existing` change type. Both agents are already registered in their respective module-level `module.yaml` files. No new entries needed. Top-level `module.yaml` is unchanged. Skip this category entirely.

---

## Category 5 — Quality Gate Checklists

- [X] **5.1** Open `specs/007-api-language-guardrail/checklists/requirements.md` and mark any previously unchecked items as complete now that implementation is done
- [X] **5.2** [P] Verify `openapi-spec-tobe.md` passes the F2 readiness gate: check that `## Output Contract` section is unchanged (paths still use lowercase `{project_name}`, format `openapi-{bc_name}.yaml`)
- [X] **5.3** [P] Verify `coder-dotnet-backend.md` passes the F3 readiness gate: check that `## Output Contract` section is unchanged (`source-code/{module}/` paths unmodified)

---

## Category 6 — Acceptance Validation & QA Integration

Depends on Category 2.

- [X] **6.1** Run PowerShell validation for Scenario 1 (openapi-spec-tobe.md guardrail present): `Select-String -Path "src\modules\ava-fabric-agents\tobe-architecture\agents\openapi-spec-tobe.md" -Pattern "Guardrail de Idioma"` — expect 1 match (quickstart.md Validation 1)
- [X] **6.2** [P] Run PowerShell validation for transliteration table size: count `| <pt-br> | <en>` rows — expect ≥ 10 (quickstart.md Validation 1)
- [X] **6.3** [P] Run PowerShell validation for version field in `openapi-spec-tobe.md`: `Select-String -Pattern "^version:" -CaseSensitive` — expect `version: "1.1.0"` (quickstart.md Validation 1)
- [X] **6.4** [P] Run PowerShell validation for G10 section: `Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "### G10"` — expect 1 match (quickstart.md Validation 3)
- [X] **6.5** [P] Run PowerShell validation for G10 XML doc exemption and cross-reference: verify lines near G10 mention `XML`, `summary`, and `openapi-spec-tobe` (quickstart.md Validation 3)
- [X] **6.6** [P] Run PowerShell validation for G1-G10 routing guard: `Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "G1-G10"` — expect 1 match; confirm no remaining `G1-G9` reference (quickstart.md Validation 3)
- [X] **6.7** Confirm Scenario 4 (Sophia validation, PBI #2308) is formally deferred: (a) add comment `<!-- DEFERRED: #2308 — Sophia project not in workspace -->` immediately after the Scenario 4 heading in `specs/007-api-language-guardrail/spec.md`; (b) append `_(deferred — #2308)_` to the SC5 row in the Success Criteria table of `spec.md` (Research R5)

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6.

- [X] **7.1** [P] Add entry to `CHANGELOG.md` for `ava-tobe-spec` version `1.1.0` (MINOR): "Adicionado guardrail de normalização de idioma e tabela de transliteração PT-BR → EN (PBI #2304, #2305, #2306)" (Research R7)
- [X] **7.2** [P] Add entry to `CHANGELOG.md` for `ava-stack-dotnet-backend` version `1.1.0` (MINOR): "Adicionado guardrail G10 — identificadores C# obrigatoriamente em inglês; referência à tabela de transliteração de openapi-spec-tobe.md (PBI #2304, #2307)"
- [X] **7.3** [P] Update `docs/agents-catalog.md`: bump version for `ava-tobe-spec` (→ 1.1.0) and `ava-stack-dotnet-backend` (→ 1.1.0) with a note about the language guardrail

---

## Completion Checklist

- [X] Category 1: version bumps applied to both agent frontmatter files
- [X] Category 2A (tasks 2.1–2.7): transliteration table + guardrail section added to `openapi-spec-tobe.md`
- [X] Category 2B (tasks 2.8–2.13): G10 guardrail added to `coder-dotnet-backend.md`
- [X] Category 2C (tasks 2.14–2.15): G1-G9 → G1-G10 routing guard updated
- [X] Category 3: skipped (N/A)
- [X] Category 4: skipped (N/A)
- [X] Category 5: readiness gate checks passed for both agents
- [X] Category 6: all 7 PowerShell validation checks pass; Scenario 4 deferred with comment
- [X] Category 7: CHANGELOG.md entries for both agents; agents-catalog.md updated
- [X] No PT-BR tokens remain in `version:` fields (both agents show `"1.1.0"`)
- [X] Single source of truth preserved: transliteration table lives only in `openapi-spec-tobe.md`
