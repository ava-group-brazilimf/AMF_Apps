# Agent Specification: Language Normalization Guardrail for API & C# Identifiers

**Feature Branch**: `007-api-language-guardrail`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: modify-existing
**PBI**: #2304 — Guardrail de normalizacao de idioma: endpoints e identificadores C# obrigatoriamente em ingles
**Input**: PBI #2304 + child tasks #2305, #2306, #2307, #2308

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` — two existing agents are patched |
| **Agent 1** | `ava-tobe-spec` — `src/modules/ava-fabric-agents/tobe-architecture/agents/openapi-spec-tobe.md` |
| **Agent 2** | `ava-stack-dotnet-backend` — `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |
| **Version Bump** | MINOR for both (new enforcement rule added; no breaking output-contract change) |
| **Phase** | F2 (openapi-spec-tobe) · F3 (coder-dotnet-backend) |
| **Module** | `tobe-architecture` · `tech-stack` |

> Because this is `modify-existing`:
> - No new agent files are created
> - No new SKILL.md entries are required
> - No new `module.yaml` entries are required
> - Category 1.5 (Skill) and Category 4 (Module registration) tasks are **N/A**

---

## 2. Problem Statement

`openapi-spec-tobe.md` derives `operationIds` and path segments directly from
Command/Query names in `bounded-context-map.md`. Because the bounded-context-map
inherits terminology from the legacy Delphi codebase (PT-BR), the generated OpenAPI
spec can contain mixed-language paths and identifiers:

- `/alunos` and `/students` may coexist in the same project
- `operationId: registrarAluno` may be generated alongside `operationId: getStudentById`
- C# class names in `coder-dotnet-backend.md` may inherit the PT-BR form (e.g., `AlunosController`)

These inconsistencies break downstream contract tests, violate code-review standards,
and produce confusing client SDKs.

---

## 3. Output Contract

> No new output files are produced. Both agents already write to their established
> output paths. This change adds **inline enforcement rules** to each agent body.

The modified agents continue writing to their existing paths:

```yaml
outputs:
  # openapi-spec-tobe.md (unchanged paths)
  openapi_spec: "projects/{project_name}/outputs/tobe/docs/openapi-{bc_name}.yaml"
  # coder-dotnet-backend.md (unchanged paths)
  backend_source: "projects/{project_name}/outputs/tobe/source-code/"
```

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — OpenAPI paths and operationIds are normalized to English (Priority: P1)

**Story**: Como arquiteto de API, quero que o agente `openapi-spec-tobe` rejeite identificadores
PT-BR em paths e operationIds para que a API gerada esteja sempre em inglês e sem mistura de idiomas.

**Why this priority**: Mixed-language APIs break contract tests and SDK generation.

**Acceptance Scenarios**:

1. **Given** a `bounded-context-map.md` with a Command named `RegistrarAlunoCommand`, **When** `openapi-spec-tobe.md` derives the path and operationId, **Then** the path segment is `/students` (not `/alunos`) and the operationId is `registerStudent` (not `registrarAluno`).
2. **Given** the guardrail rule is active, **When** the agent encounters any PT-BR token in a path segment or operationId, **Then** it applies the transliteration table before writing the spec, and logs a `[LANG-NORM]` annotation next to the translated entry.
3. **Given** the openapi spec is complete, **When** no transliteration table entry exists for a term, **Then** the agent flags it as `[NEEDS TRANSLATION: <original-term>]` in the spec comments and does NOT silently omit the endpoint.

---

### Scenario 2 — Transliteration table is documented and consulted (Priority: P1)

**Story**: Como desenvolvedor, quero uma tabela de transliteracao PT-BR → EN documentada no agente
para que a traducao seja deterministica e rastreavel.

**Why this priority**: Without a canonical table, each run may produce different translations.

**Acceptance Scenarios**:

1. **Given** the guardrail is in place, **When** a developer reads `openapi-spec-tobe.md`, **Then** they find a clearly labeled section with a PT-BR → EN transliteration table covering at minimum: common domain nouns (aluno→student, matricula→enrollment, nota→grade, turma→class/group, professor→teacher/instructor, pagamento→payment, fatura→invoice, fornecedor→supplier, cliente→client/customer, pedido→order).
2. **Given** a new PT-BR term not in the table is encountered, **When** the agent runs, **Then** it uses `[NEEDS TRANSLATION: <term>]` as a placeholder rather than guessing.
3. **Given** the transliteration table exists in the agent, **When** two different project runs happen, **Then** the same PT-BR command name always produces the same English identifier.

---

### Scenario 3 — C# identifiers are enforced in English by G10 guardrail (Priority: P1)

**Story**: Como desenvolvedor .NET, quero que o coder-dotnet-backend aplique o guardrail G10 para
garantir que todos os identificadores C# (controllers, commands, queries, handlers) sejam em ingles.

**Why this priority**: PT-BR identifiers in C# code violate Avanade coding standards and fail PR reviews.

**Acceptance Scenarios**:

1. **Given** `coder-dotnet-backend.md` receives an openapi spec that has already been normalized to English by `openapi-spec-tobe.md`, **When** it generates C# code, **Then** all class names, method names, namespaces, and file names are in English (PascalCase or camelCase per C# conventions).
2. **Given** a C# XML doc comment is generated, **When** G10 is active, **Then** XML `<summary>` and `<param>` tags MAY be written in PT-BR — this is explicitly allowed.
3. **Given** G10 is in effect, **When** the agent would produce a PT-BR identifier (e.g., `AlunosController`, `RegistrarAlunoCommand`), **Then** it first applies the same transliteration table referenced from `openapi-spec-tobe.md` and generates `StudentsController`, `RegisterStudentCommand` instead.
4. **Given** G10 is active, **When** the input spec already contains English identifiers (normalized by `openapi-spec-tobe.md`), **Then** G10 is a no-op and does not alter any names.

---

### Scenario 4 — No mixed-language paths in Sophia project (Priority: P2)
<!-- DEFERRED: #2308 — Sophia project not in workspace -->

**Story**: Como QA lead, quero validar com o projeto Sophia que zero mistura de idiomas existe nos
paths, operationIds e nomes de classe gerados apos a aplicacao dos guardrails.

**Why this priority**: Sophia is the reference project; validating against it proves the guardrail works.

**Acceptance Scenarios**:

1. **Given** the Sophia project's `bounded-context-map.md` contains PT-BR command names, **When** `openapi-spec-tobe.md` runs with the new guardrail, **Then** the generated OpenAPI spec has zero PT-BR tokens in path segments and operationIds.
2. **Given** the above OpenAPI spec is consumed by `coder-dotnet-backend.md`, **When** C# files are generated, **Then** a grep for PT-BR common words (aluno, matricula, nota, turma, professor, pagamento, fatura, fornecedor, cliente, pedido) finds zero matches in class names, method names, and file names.

---

## 5. Quality Gate Requirements

- [ ] Agent IDs remain `ava-tobe-spec` and `ava-stack-dotnet-backend` — no renaming (Article II)
- [ ] Frontmatter of both agents retains only `name`, `version`, `description`, `allowed-tools` after patch (Article II)
- [ ] Version bumped to `MINOR` in both agent frontmatter entries (MINOR = new rule, no contract break)
- [ ] Output paths in both agents' `## Output Contract` sections are unchanged (Article II)
- [ ] Transliteration table covers minimum 10 PT-BR → EN domain noun pairs (Scenario 2)
- [ ] G10 guardrail in `coder-dotnet-backend.md` explicitly states XML docs may be PT-BR (Scenario 3)
- [ ] G10 references the same transliteration table location as `openapi-spec-tobe.md` (single source of truth)
- [ ] `[LANG-NORM]` annotation convention documented in `openapi-spec-tobe.md`
- [ ] No technology versions hardcoded (Article I)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent / File | Reason |
|---|---|---|
| `ava-tobe-spec` (current) | `openapi-spec-tobe.md` | Must be read before patching — MINOR version bump from current |
| `ava-stack-dotnet-backend` (current) | `coder-dotnet-backend.md` | Must be read before patching — G10 inserted after G9 |
| Bounded Context Map | `projects/{project_name}/outputs/tobe/docs/bounded-context-map.md` | Source of PT-BR names that trigger transliteration |
| Sophia project config | `projects/Sophia/context/project-config.yaml` _(if exists)_ | Used only for validation scenario 4 — not a hard prerequisite |

---

## 7. Exclusions

- Database column names — handled by `ava-tobe-db-analyzer`; out of scope for this PBI
- Frontend Angular component names — handled by `ava-stack-angular-frontend`; out of scope
- Comments and prose inside agent `.md` files — PT-BR is the required language per Article V; only identifiers must be English
- Delphi source files — read-only AS-IS artifacts; language normalization does not apply to legacy code

---

## 8. Assumptions

- The transliteration table will be embedded directly in `openapi-spec-tobe.md` under a dedicated `### Tabela de Transliteração PT-BR → EN` subsection of the existing Skills section, so it is visible to the agent during execution.
- `coder-dotnet-backend.md`'s G10 will reference the transliteration table by path (`openapi-spec-tobe.md § Tabela de Transliteração PT-BR → EN`) rather than duplicating it, to keep a single source of truth.
- The `[LANG-NORM]` annotation is an inline YAML comment (e.g., `# [LANG-NORM] aluno → student`) and does not alter the spec's validity.
- The Sophia project is in the workspace or can be invoked separately for validation; if absent, Scenario 4 is deferred to the next sprint.
- Both agents are patched in sequence (openapi-spec-tobe first, then coder-dotnet-backend) so that the transliteration table exists before G10 is written.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Language consistency in generated specs | Zero PT-BR tokens in path segments and operationIds of any generated OpenAPI spec |
| Language consistency in generated C# | Zero PT-BR tokens in C# class names, method names, namespaces, or file names |
| Transliteration table completeness | Minimum 10 canonical PT-BR → EN domain noun pairs documented in `openapi-spec-tobe.md` |
| XML doc exemption preserved | G10 explicitly allows PT-BR in XML `<summary>` and `<param>` tags |
| Sophia project validation | After applying guardrails, Sophia project has zero mixed-language identifiers in generated artifacts _(deferred — #2308)_ |
| Version traceability | Both agent files show MINOR version bump in frontmatter |
