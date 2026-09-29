# Data Model: Language Normalization Guardrail (#2304)

**Branch**: `007-api-language-guardrail`
**Date**: 2026-07-07

> This feature modifies two LLM prompt files (`.md` agents). There are no runtime
> data models, database entities, or API schemas to create. This document describes
> the **rule structures** embedded in the agent bodies.

---

## 1. Transliteration Table — Canonical PT-BR → EN Mapping

**Lives in**: `openapi-spec-tobe.md` § `Guardrail de Idioma — Normalização para Inglês`  
**Referenced by**: `coder-dotnet-backend.md` G10

### Structure

```
| PT-BR token (singular) | EN token (singular) | Notes |
|------------------------|---------------------|-------|
| aluno                  | student             |       |
| ...                    | ...                 |       |
```

### Full Canonical Table (25 pairs)

| PT-BR (singular) | EN (singular) | Notes |
|------------------|---------------|-------|
| aluno | student | |
| professor | instructor | not "teacher" — instructor is the domain term |
| funcionario | employee | |
| fornecedor | supplier | |
| cliente | customer | use "client" only when context is legal/B2B |
| socio | partner | |
| pagamento | payment | |
| fatura | invoice | |
| pedido | order | |
| lancamento | entry | accounting context |
| recibo | receipt | |
| matricula | enrollment | |
| nota | grade | academic context; use "note" only for free-text notes |
| turma | group | not "class" (reserved C# keyword) |
| curso | course | |
| disciplina | subject | |
| produto | product | |
| estoque | stock | |
| categoria | category | |
| usuario | user | |
| perfil | profile | |
| permissao | permission | |
| relatorio | report | |
| contrato | contract | |
| empresa | company | |

---

## 2. Transliteration Algorithm (embedded in openapi-spec-tobe.md)

```
INPUT:  Command or Query name from bounded-context-map.md
        e.g., "RegistrarAlunoCommand"

STEPS:
  1. Strip suffix: remove "Command" | "Query" | "Handler" suffix
     → "RegistrarAluno"
  2. Tokenize by PascalCase boundaries
     → ["Registrar", "Aluno"]
  3. For each token (case-insensitive lookup):
     a. token in transliteration_table → replace with EN equivalent
     b. token NOT in table → keep original + append flag [NEEDS TRANSLATION: <token>]
     → ["Register", "Student"]
  4. Reconstruct identifier:
     - operationId: lowerCamelCase of verb+noun → "registerStudent"
     - path segment: kebab-case of noun plural → "students"
     - C# class: PascalCase → "RegisterStudentCommand"
  5. Annotate: add YAML comment # [LANG-NORM] <original> → <translated>

OUTPUT: Normalized identifier + optional [NEEDS TRANSLATION] flag
```

---

## 3. G10 Guardrail — Rule Structure (embedded in coder-dotnet-backend.md)

```
RULE ID:  G10
TITLE:    Language Normalization — C# Identifiers em inglês
SEVERITY: ERROR (blocking — same enforcement level as G1-G9)

APPLIES TO:
  - Controller class names  (e.g., StudentsController not AlunosController)
  - Command record names    (e.g., RegisterStudentCommand not RegistrarAlunoCommand)
  - Query record names      (e.g., GetStudentByIdQuery not ObterAlunoPorIdQuery)
  - Handler class names     (e.g., RegisterStudentCommandHandler)
  - DTO record names        (e.g., StudentResponse not AlunoResponse)
  - File names              (e.g., RegisterStudentCommand.cs)
  - Namespace segments      (e.g., Students not Alunos)

EXEMPT:
  - XML doc <summary> tags  → MAY be in PT-BR
  - XML doc <param> tags    → MAY be in PT-BR
  - XML doc <returns> tags  → MAY be in PT-BR
  - String literals in code → MAY be in PT-BR (display text, error messages)

RESOLUTION:
  1. Check if identifier was derived from openapi-spec-tobe normalized output
     → If YES: use the already-normalized identifier from the spec (G10 is a no-op)
  2. If identifier comes from bounded-context-map directly:
     → Apply transliteration table from openapi-spec-tobe.md § Guardrail de Idioma
     → Follow transliteration algorithm (steps 1-5)
  3. If no translation available:
     → Flag as // [G10-NEEDS-TRANSLATION: <original>] inline comment
     → Use original name temporarily but mark for human review
```

---

## 4. Annotation Conventions

| Annotation | Context | Meaning |
|---|---|---|
| `# [LANG-NORM] <pt> → <en>` | YAML comment in generated OpenAPI spec | Normal successful transliteration — audit trail |
| `# [NEEDS TRANSLATION: <term>]` | YAML comment in generated OpenAPI spec | PT-BR term not in table — human review required |
| `// [G10-NEEDS-TRANSLATION: <term>]` | C# inline comment | Identifier not translatable — human review required |

---

## 5. Version Bumps

| File | Old Version | New Version | Bump Type | Reason |
|---|---|---|---|---|
| `openapi-spec-tobe.md` | _(none — unversioned)_ | `"1.1.0"` | MINOR | New guardrail rule + transliteration table added |
| `coder-dotnet-backend.md` | `"1.0.0"` | `"1.1.0"` | MINOR | G10 guardrail added; G1-G9 reference updated to G1-G10 |
