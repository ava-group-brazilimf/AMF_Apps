# Agent Specification: Date Format Guardrails

**Feature Branch**: `007-date-format-guardrails`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: modify-existing (2 agent files + 1 shared reference document)
**Input**: "O sistema modernizado exibia datas no formato americano MM/DD/YYYY em vez do brasileiro DD/MM/YYYY. O `coder-angular-frontend.md` nao tem guardrail que force o uso de `DatePipe` com formato `dd/MM/yyyy` nem a configuracao de `LOCALE_ID=pt-BR`. O backend serializa `DateTime` sem garantia de formato ISO 8601."

---

## 1. Problem Statement

The modernized system outputs dates in American format (`MM/DD/YYYY`) instead
of the Brazilian standard (`DD/MM/YYYY`). Two root causes have been identified:

1. **`coder-angular-frontend.md`** — missing guardrail enforcing:
   - `LOCALE_ID = 'pt-BR'` registration in `app.config.ts`
   - `DatePipe` called with the explicit format `'dd/MM/yyyy'`
   - `MAT_DATE_LOCALE = 'pt-BR'` for Angular Material date pickers

2. **`coder-dotnet-backend.md`** — missing guardrail enforcing:
   - `DateTime` values serialized as ISO 8601 (`DateTimeKind.Utc`, format specifier `"o"`)
   - `DateTimeKind.Local` explicitly prohibited in API response DTOs

Without these guardrails the generated code is globally incorrect for any
Brazilian client: dates appearing as `07/06/2026` instead of `06/07/2026`
cause data-entry errors, integration failures with downstream systems, and
potential legal/regulatory issues when dealing with financial or health records.

`angular-patterns-reference.md` also has no dedicated "Padrões de Data e Hora"
section, so developers lack authoritative guidance on correct vs incorrect patterns.

---

## 2. Decision

Add one new numbered guardrail to each coder agent, and add a reference section
to the shared patterns document:

| Target File | Change | Guardrail ID |
| --- | --- | --- |
| `coder-dotnet-backend.md` | Add **G10 — DateTime Serialization** guardrail | G10 |
| `coder-angular-frontend.md` | Add **date format** guardrail (locale + pipe + Material) | G-DATE |
| `angular-patterns-reference.md` | Add **Padrões de Data e Hora** section with ✅/❌ examples | N/A |

Version bumps: both agent files receive a **MINOR** bump to formally record guardrail
content added as hotfix before this spec was formalized (new behavior, no contract-breaking change).

---

## 3. Scope

### 3.1 `coder-dotnet-backend.md`

**Path**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

**Guardrail G10 — DateTime Serialization** to be added in the guardrails
section (after the last existing G-numbered guardrail):

- APIs MUST return `DateTime` as ISO 8601 using `DateTimeKind.Utc` and format
  specifier `"o"` (e.g., `2026-07-06T00:00:00Z`).
- `DateTimeKind.Local` is **prohibited** in API response DTOs.
- `DateTimeKind.Unspecified` is prohibited in API response DTOs; `Utc` must
  be enforced via `DateTime.SpecifyKind(value, DateTimeKind.Utc)` or
  `ToUniversalTime()` before serialization.
- Where `DateTimeOffset` is available, prefer it over `DateTime` for API
  response types — it carries time-zone offset explicitly.

### 3.2 `coder-angular-frontend.md`

**Path**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`

**Date Format Guardrail** to be added in the guardrails section:

- `provideLocaleId('pt-BR')` (or the equivalent `{ provide: LOCALE_ID, useValue: 'pt-BR' }`)
  MUST appear in `app.config.ts` application providers.
- `@angular/common/locales/pt` MUST be registered via `registerLocaleData` in
  the app bootstrap (before `bootstrapApplication`).
- `DatePipe` MUST always be called with the explicit format `'dd/MM/yyyy'` — relying
  on the locale default is insufficient (locale pipes are environment-dependent).
- `MAT_DATE_LOCALE` MUST be set to `'pt-BR'` for any feature using Angular
  Material date pickers (`MatDatepickerModule`).
- Displaying raw ISO strings (`2026-07-06T00:00:00Z`) directly in templates without
  the pipe is **prohibited**.

### 3.3 `angular-patterns-reference.md`

**Path**: `src/shared/data/patterns/angular/angular-patterns-reference.md`

A new top-level section **Padrões de Data e Hora** is appended. It must contain:

- Rationale (why `pt-BR` locale + explicit pipe format)
- `app.config.ts` bootstrap snippet (correct)
- `DatePipe` usage ✅ correct and ❌ incorrect examples
- Angular Material `MAT_DATE_LOCALE` snippet
- Backend contract reminder: ISO 8601 input → `dd/MM/yyyy` display

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Backend returns ISO 8601 (Priority: P1)

**Story**: Como o time de migração, quero que o backend serialize datas em ISO 8601
com `DateTimeKind.Utc` para que o frontend possa exibir `06/07/2026`
a partir de `2026-07-06T00:00:00Z`.

**Acceptance Scenarios**:

1. **Given** `coder-dotnet-backend.md` has guardrail G10, **When** the coder agent
   generates a DTO with a `DateTime` property, **Then** the generated code uses
   `DateTimeKind.Utc` and the serialization format is `"o"` (ISO 8601 round-trip).
2. **Given** the above, **When** the generated DTO contains `DateTimeKind.Local`,
   **Then** the guardrail marks the code as non-compliant and the agent rejects the pattern.

---

### Scenario 2 — Frontend displays dates as DD/MM/YYYY (Priority: P1)

**Story**: Como usuário do sistema gerado, quero ver datas no padrão brasileiro
`DD/MM/YYYY` em todos os formulários e listagens.

**Acceptance Scenarios**:

1. **Given** `coder-angular-frontend.md` has the date guardrail, **When** the
   agent generates `app.config.ts`, **Then** `LOCALE_ID = 'pt-BR'` is present
   in the providers array and `registerLocaleData(localePt)` is called at bootstrap.
2. **Given** the above, **When** a date is rendered in a template, **Then** the
   generated template code uses `{{ value | date:'dd/MM/yyyy' }}` — never a raw
   ISO string interpolation.
3. **Given** a feature using `MatDatepickerModule`, **When** the agent generates
   the feature module, **Then** `MAT_DATE_LOCALE = 'pt-BR'` is present in providers.

---

### Scenario 3 — Quality Gate: Non-compliant pattern detected (Priority: P2)

**Story**: Como revisor de código, quero que a geração de código falhe
imediatamente ao encontrar um padrão de data não conforme.

**Acceptance Scenarios**:

1. **Given** a generated template contains `{{ event.date }}` (no pipe), **When**
   the guardrail evaluates the output, **Then** the agent flags the pattern as
   `❌ PROIBIDO` and replaces it with `{{ event.date | date:'dd/MM/yyyy' }}`.
2. **Given** a generated DTO contains `DateTimeKind.Local`, **When** G10 runs,
   **Then** the agent emits a guardrail violation message and corrects the kind
   to `DateTimeKind.Utc`.

> **Nota de validação**: Os cenários 1–2 desta seção descrevem comportamento em tempo de
> execução do agente LLM — verificável apenas executando o agente e inspecionando o código
> gerado. A validação estática do `quickstart.md` confirma a pré-condição (guardrail presente),
> não o comportamento em tempo de execução.

---

### Scenario 4 — Reference documentation serves as authoritative guide (Priority: P2)

**Story**: Como desenvolvedor do time do cliente, quero consultar
`angular-patterns-reference.md` para entender os padrões corretos de data.

**Acceptance Scenarios**:

1. **Given** `angular-patterns-reference.md` has the **Padrões de Data e Hora**
   section, **When** a developer reads it, **Then** they find both a ✅ correct
   `app.config.ts` snippet and a ❌ incorrect example with an explanation.
2. **Given** the above, **Then** the section explicitly states the contract:
   "Backend → ISO 8601 (`2026-07-06T00:00:00Z`) → Frontend displays `06/07/2026`".

---

## 5. Quality Gate Requirements

- [ ] Agent ID pattern unaffected — only guardrail sections modified (Article II)
- [ ] No frontmatter fields changed — MINOR version bump only (Article X)
- [ ] Generated code follows Clean Architecture layer order (Article IX)
- [ ] No technology versions hardcoded in guardrail text (Article I)
- [ ] `angular-patterns-reference.md` section uses ✅/❌ pattern consistent with
      existing sections in that file
- [ ] All BDD scenarios have measurable, implementation-agnostic success criteria
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | File | Reason |
| --- | --- | --- |
| Existing guardrail list | `coder-dotnet-backend.md` | G10 must follow last current G-number without collision |
| Existing guardrail list | `coder-angular-frontend.md` | Date guardrail must be inserted consistently |
| Existing sections | `angular-patterns-reference.md` | New section must match existing formatting conventions |

---

## 7. Exclusions

- Time-zone conversion logic — handled by the application business layer, not
  the coder agents.
- `DateOnly` / `TimeOnly` types — out of scope for this spec; follow-up if needed.
- COBOL / VB6 / PowerBuilder legacy date handling — this spec targets the TO-BE
  generated stack only.
- i18n for other languages (English, Spanish) — existing locale infra is unaffected.
- Teste end-to-end (`SC-008`: renderização `06/07/2026` na aplicação em execução) — requer
  execução do agente + build da aplicação gerada; escopo de um ciclo de QA separado.

---

## 8. Assumptions

- The existing `coder-dotnet-backend.md` already has a numbered guardrail list
  (G01–G09 or similar); G10 will follow the last existing number.
- The existing `coder-angular-frontend.md` already has a guardrail section where
  the date guardrail can be appended.
- `angular-patterns-reference.md` exists at the path above; if absent, it will
  be created with the "Padrões de Data e Hora" section as its first content.
- Angular version is resolved at runtime from `tobe_stack.frontend_version` in
  `project-config.yaml` — no hardcoding (Article I).
- `@angular/material` is an optional dependency; the `MAT_DATE_LOCALE` guardrail
  applies only when Material date pickers are present.
- **Pré-condição descoberta durante planejamento**: todo o conteúdo dos guardrails (G10,
  G-DATE, seção "Padrões de Data e Hora") já existia nos arquivos alvo como hotfix aplicado
  antes desta spec. A spec formaliza o registro e aplica os bumps de versão correspondentes.

---

## Success Criteria

| Criterion | Measure |
| --- | --- |
| G10 present in backend agent | Guardrail text present in `coder-dotnet-backend.md`; version bumped |
| Date guardrail present in frontend agent | Guardrail text present in `coder-angular-frontend.md`; version bumped |
| Reference doc updated | "Padrões de Data e Hora" section exists in `angular-patterns-reference.md` with ✅/❌ examples |
| ISO 8601 contract enforced | Generated backend DTOs use `DateTimeKind.Utc` and format `"o"` |
| Locale config enforced | Generated `app.config.ts` contains `LOCALE_ID = 'pt-BR'` and `registerLocaleData` |
| Pipe format enforced | Generated templates use `date:'dd/MM/yyyy'` — never raw ISO string interpolation |
| Material locale enforced | Generated Material date picker features include `MAT_DATE_LOCALE = 'pt-BR'` |
| End-to-end display *(fora do escopo desta fase — ver §7 Exclusões)* | API value `2026-07-06T00:00:00Z` renders as `06/07/2026` — verificável via execução do agente + build da aplicação gerada |
