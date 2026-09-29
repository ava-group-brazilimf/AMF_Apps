# Agent Specification: Unicode-Safe Regex Guardrail (G10 + Angular)

**Feature Branch**: `007-unicode-safe-regex-guardrail`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: `bugfix`
**Input**: Agent description: "Adicionar guardrail de regex Unicode-safe ao coder-dotnet-backend.md e ao coder-angular-frontend.md, e documentar o padrão canônico em angular-patterns-reference.md. Backend C#: [RegularExpression(@"^\p{L}[\p{L}\s'-]*$")] — nunca [a-zA-Z] para campos de texto PT-BR. Frontend Angular: Validators.pattern(/^[\p{L}\s\-']+$/u) com flag Unicode — nunca /^[a-zA-Z\s]+$/"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-dotnet-backend` + `ava-stack-angular-frontend` |
| **Version** | `1.0.0` → `1.0.1` (PATCH — bugfix on both agents) |
| **Phase** | `F3` (Tech Stack) |
| **Module** | `tech-stack` |
| **Role** | Fix: prevent generation of ASCII-only regex patterns (`[a-zA-Z]`) for PT-BR text fields; enforce Unicode-category patterns (`\p{L}`) |
| **Skill** | `ava-stack-dotnet-backend`, `ava-stack-angular-frontend` |
| **Dispatch** | user-facing via SKILL.md (existing) |

> **Change Type `bugfix`**: modifying existing agent files — no new `module.yaml` entry needed (Category 4 tasks are N/A). SKILL.md already exists — Category 1.5 is N/A.
>
> Version bump type: **PATCH** (bug fix — no contract change, no new fields).
>
> Affected files:
> - `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` — add **G10** to the existing G1–G9 guardrail list
> - `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` — add Unicode regex guardrail to the validation patterns section
> - `src/shared/data/patterns/angular/angular-patterns-reference.md` — add section **PT-BR Validation Patterns**

---

## 2. Agent Frontmatter

Version bumped to `1.0.1` on both affected agents. No other frontmatter field changes.

**coder-dotnet-backend.md** (line 10 patch):
```yaml
version: "1.0.1"
```

**coder-angular-frontend.md** (line 3 and line 12 patch):
```yaml
version: "1.0.1"
```

---

## 3. Output Contract

No new output artifacts. Both agents continue writing to the existing codegen output paths:

```yaml
outputs:
  source_code: "projects/{project_name}/outputs/tobe/source-code/"
```

> The `angular-patterns-reference.md` is a **shared data file**, not an agent output artifact — it is an authoritative reference consumed at generation time.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal: .NET Backend generates Unicode-safe validation (Priority: P1)

**Story**: Como o agente `coder-dotnet-backend`, preciso garantir que toda propriedade de texto gerada para domínios PT-BR use `\p{L}` em vez de `[a-zA-Z]` para que nomes como "José", "João", "Márcia" sejam aceitos pelo modelo.

**Why this priority**: Core correctness issue — generated code rejects valid PT-BR names silently.

**Acceptance Scenarios**:

1. **Given** a C# entity with a `Nome` property, **When** the agent generates the `[RegularExpression]` attribute, **Then** the pattern is `@"^\p{L}[\p{L}\s'-]*$"` and never contains the literal sequence `[a-zA-Z]`.
2. **Given** Guardrail G10 is active, **When** the agent reviews any generated regex for text fields, **Then** it rejects patterns containing `[a-zA-Z]` and replaces them with `\p{L}`-based equivalents.
3. **Given** the name "José da Silva" is submitted to the generated validator, **When** the `[RegularExpression]` attribute is evaluated, **Then** validation passes without error.

---

### Scenario 2 — Nominal: Angular Frontend generates Unicode-safe validators (Priority: P1)

**Story**: Como o agente `coder-angular-frontend`, preciso garantir que os `Validators.pattern()` gerados para campos de texto usem a flag `u` (Unicode) para que os formulários PT-BR funcionem corretamente.

**Why this priority**: Core correctness issue — generated Angular forms reject accented characters in reactive form validators.

**Acceptance Scenarios**:

1. **Given** a reactive form field for a name input, **When** the agent generates the `Validators.pattern(...)` call, **Then** the regex literal uses the `u` flag (`/^[\p{L}\s\-']+$/u`) and never uses `/^[a-zA-Z\s]+$/`.
2. **Given** the guardrail is active in `coder-angular-frontend.md`, **When** any regex literal without the `u` flag is detected in generated text-field validators, **Then** the agent corrects it before emitting the file.
3. **Given** a form field accepting the input "João", **When** the Validators.pattern rule is applied at runtime, **Then** the input is accepted (no validation error).

---

### Scenario 3 — Reference: `angular-patterns-reference.md` canonical patterns (Priority: P2)

**Story**: Como membro da equipe, preciso de uma seção canônica em `angular-patterns-reference.md` que documente os padrões corretos PT-BR para que desenvolvedores e agentes consultem um único lugar de verdade.

**Why this priority**: Prevents drift — if the reference exists, future agents and developers can consult it.

**Acceptance Scenarios**:

1. **Given** the `angular-patterns-reference.md` file, **When** reading the **PT-BR Validation Patterns** section, **Then** it lists the canonical regex for name fields (`/^[\p{L}\s\-']+$/u`), phone fields, and CPF — each with a forbidden-pattern counterpart.
2. **Given** the section is present, **When** both coder agents reference it, **Then** their guardrail descriptions cite this file as the authoritative source.

---

### Scenario 4 — Edge Case: Regex inside non-text fields unchanged (Priority: P3)

**Why this priority**: Prevents over-correction — numeric, date, CPF, CEP, and phone patterns must not be altered.

**Acceptance Scenarios**:

1. **Given** a `CPF` property using `@"^\d{11}$"` or `@"^\d{3}\.\d{3}\.\d{3}-\d{2}$"`, **When** Guardrail G10 runs, **Then** the pattern is **not** modified (it contains no `[a-zA-Z]`).
2. **Given** a `DataNascimento` property using a date regex, **When** Guardrail G10 runs, **Then** the pattern is unchanged.

---

## 5. Quality Gate Requirements

- [x] Agent IDs follow `ava-{phase}-{role}` pattern (existing, unchanged)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (existing, PATCH bump only)
- [x] No new `module.yaml` entry needed (modify-existing — Article IV N/A)
- [x] No new output paths — existing codegen path reused (Article II)
- [x] BDD scenarios cover nominal (S1, S2), reference (S3), and edge (S4) paths (Article VI)
- [x] No technology versions hardcoded in the guardrail text (Article I) — versions remain in config
- [x] Skill/Agent split unchanged (modify-existing, Article XI N/A)
- [x] No `[NEEDS CLARIFICATION]` markers remain

**Security impact (Article VII)**: The fix reduces a correctness defect — no security surface change. Input validation patterns becoming more permissive for Unicode is expected and correct for PT-BR context.

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| None | — | Guardrails are self-contained additions within each agent file |

**Reference file**: `src/shared/data/patterns/angular/angular-patterns-reference.md` — consumed at generation time but not an agent dependency in the pipeline sense.

---

## 7. Implementation Notes

### G10 — coder-dotnet-backend.md

Add after the existing `G9` section (line ~193+), before any closing section:

```markdown
### G10 — Regex Unicode-safe para campos de texto PT-BR (validação incorreta de caracteres acentuados)

**Problema:** `[RegularExpression(@"^[a-zA-Z\s]+$")]` rejeita acentos e ç/ã/õ do português.

**Regra:** Para qualquer propriedade de texto livre (nome, descrição, endereço, cidade etc.):
- ✅ OBRIGATÓRIO: `[RegularExpression(@"^\p{L}[\p{L}\s'-]*$")]`
- ❌ PROIBIDO: qualquer padrão contendo `[a-zA-Z]` em campos de texto

**Exceções** (não alterar):
- Campos numéricos: `\d`, `[0-9]`
- Formatos fixos: CPF (`\d{3}\.\d{3}\.\d{3}-\d{2}`), CEP (`\d{5}-\d{3}`), CNPJ
- E-mail, UUID, código alfanumérico estrito

**Verificação obrigatória:** Antes de emitir qualquer `[RegularExpression]` para campo tipo string/text,
confirmar que o padrão não contém `[a-zA-Z]`. Se contiver, substituir por equivalente `\p{L}`.
```

### coder-angular-frontend.md

> **Formato canônico**: ver tasks.md 2.5 (tabela). O bloco abaixo reflete esse formato.

```markdown
⚠️ **GUARDRAIL (Unicode Regex PT-BR)** — `Validators.pattern` para campos de texto DEVE usar
a flag Unicode `u` e a categoria `\p{L}` do ECMAScript 2018.

| Tipo de campo | ✅ Padrão obrigatório | ❌ Padrão proibido |
|---|---|---|
| Nome / texto livre | `/^[\p{L}\s\-']+$/u` | `/^[a-zA-Z\s]+$/` |
| Busca / filtro texto | `/^[\p{L}\d\s\-'.]+$/u` | `/^[a-zA-Z0-9\s]+$/` |

Referência canônica: `src/shared/data/patterns/angular/angular-patterns-reference.md`
→ seção **PT-BR Validation Patterns**
```

### angular-patterns-reference.md

Add a new section **PT-BR Validation Patterns** with a table of canonical patterns:

| Campo | Padrão Canônico | Padrão Proibido |
|---|---|---|
| Nome / texto livre | `/^[\p{L}\s\-']+$/u` | `/^[a-zA-Z\s]+$/` |
| E-mail | (usar built-in `Validators.email`) | — |
| CPF | `/^\d{3}\.\d{3}\.\d{3}-\d{2}$/` | — |
| CEP | `/^\d{5}-?\d{3}$/` | — |
| Telefone | `/^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/` | — |

---

## 8. Assumptions

1. Both coder agents are invoked for projects whose locale is PT-BR by default (standard for IMFAI clients migrating Brazilian Delphi systems). The guardrails apply to **all** IMFAI projects without a locale exception.
2. G10 applies only to text/string fields. The guardrail must not alter numeric or fixed-format patterns.
3. The frontend Angular guardrail uses the ECMAScript `\p{L}` Unicode property escape with the `u` flag — supported in all modern browsers and Node.js ≥ 10.
4. No new NuGet packages or npm packages are required.
