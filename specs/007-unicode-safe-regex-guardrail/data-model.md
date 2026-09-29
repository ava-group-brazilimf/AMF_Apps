# Data Model: Unicode-Safe Regex Guardrail

**Feature**: `007-unicode-safe-regex-guardrail`
**Date**: 2026-07-07

> This feature modifies agent instruction files (`.md`). There are no runtime entities or
> database schemas involved. This document describes the **change model** — what is added
> where, and how each piece relates to others.

---

## Change Map

### File 1 — `coder-dotnet-backend.md`

**Path**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

| Attribute | Value |
|---|---|
| Change type | Append new guardrail block |
| Version | `1.0.0` → `1.0.1` |
| Insertion point | After G9 block, before `## Clean Architecture Template` |
| Approximate line | ~209 |

**Content added** — G10 guardrail block:

```
### G10 — Regex Unicode-safe para campos de texto PT-BR (validação incorreta de caracteres acentuados)

**Problema:** `[RegularExpression(@"^[a-zA-Z\s]+$")]` rejeita acentos e caracteres
especiais do português (ã, ç, é, í, ó, ú, â, ê, ô, à, etc.).
Nomes como "José", "João", "Márcia" falham na validação do modelo.

**Regra:** Para qualquer propriedade de texto livre (Nome, Descrição, Endereço,
Cidade, Observações, etc.):
✅ OBRIGATÓRIO: [RegularExpression(@"^\p{L}[\p{L}\s'-]*$")]
❌ PROIBIDO: qualquer padrão contendo [a-zA-Z] para campos de texto

**Exceções — não alterar estes padrões:**
- Campos numéricos: \d, [0-9]
- CPF: @"^\d{3}\.\d{3}\.\d{3}-\d{2}$"
- CNPJ: @"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"
- CEP: @"^\d{5}-?\d{3}$"
- E-mail: [EmailAddress] (builtin)
- UUID, código alfanumérico estrito (ex: placa veicular)

**Verificação obrigatória:** Antes de emitir qualquer [RegularExpression] para
campo tipo string/text, confirmar que o padrão não contém [a-zA-Z].
Se contiver, substituir pelo equivalente \p{L}.
```

---

### File 2 — `coder-angular-frontend.md`

**Path**: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`

| Attribute | Value |
|---|---|
| Change type | Two insertions |
| Version | `1.0.0` → `1.0.1` (two occurrences: frontmatter + body) |

#### Change 2a — Tech principles list (line ~67)

**Insertion point**: After the existing line `- Pipes monetárias — ...` in the principles list.

**Content added**:
```
- Regex PT-BR Unicode-safe — `Validators.pattern(/^[\p{L}\s\-']+$/u)` obrigatório para campos de texto; `/^[a-zA-Z\s]+$/` é PROIBIDO
```

#### Change 2b — GUARDRAILS DE BUILD section (line ~2955)

**Insertion point**: After the existing build guardrail items in the GUARDRAILS DE BUILD block, before the `║  SEGURANÇA` subsection.

**Content added** — new GUARDRAIL block outside the pre-flight box:
```
⚠️ **GUARDRAIL (Unicode Regex PT-BR)** — `Validators.pattern` para campos de texto DEVE usar
a flag Unicode `u` e a categoria `\p{L}` do ECMAScript 2018.

| Tipo de campo | ✅ Padrão obrigatório | ❌ Padrão proibido |
|---|---|---|
| Nome / texto livre | `/^[\p{L}\s\-']+$/u` | `/^[a-zA-Z\s]+$/` |
| Busca / filtro texto | `/^[\p{L}\d\s\-'.]+$/u` | `/^[a-zA-Z0-9\s]+$/` |

Referência canônica: `src/shared/data/patterns/angular/angular-patterns-reference.md`
→ seção **PT-BR Validation Patterns**
```

---

### File 3 — `angular-patterns-reference.md`

**Path**: `src/shared/data/patterns/angular/angular-patterns-reference.md`

| Attribute | Value |
|---|---|
| Change type | Append new section at end of file |
| Version | `1.0.0` → `1.0.1` (frontmatter) |
| Insertion point | End of file, after the Pipes section |

**Content added** — new section:

```markdown
## PT-BR Validation Patterns

Padrões canônicos de validação para campos de texto em sistemas brasileiros.
Usado por: `ava-stack-dotnet-backend` (G10), `ava-stack-angular-frontend` (GUARDRAIL Unicode Regex PT-BR).

> **Invariant:** NUNCA usar `[a-zA-Z]` para validar campos de texto em domínios PT-BR.
> SEMPRE usar `\p{L}` (categoria Unicode "Letter") com a flag `u` no frontend.

### Angular — Validators.pattern (Reactive Forms)

| Campo | Padrão canônico (`u` flag obrigatória) | Padrão proibido |
|---|---|---|
| Nome / texto livre | `/^[\p{L}\s\-']+$/u` | `/^[a-zA-Z\s]+$/` |
| Busca / filtro texto | `/^[\p{L}\d\s\-'.]+$/u` | `/^[a-zA-Z0-9\s]+$/` |
| CPF | `/^\d{3}\.\d{3}\.\d{3}-\d{2}$/` | — |
| CNPJ | `/^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/` | — |
| CEP | `/^\d{5}-?\d{3}$/` | — |
| Telefone | `/^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/` | — |
| E-mail | usar `Validators.email` (builtin) | — |

### C# — [RegularExpression] attribute (Data Annotations)

| Campo | Padrão canônico | Padrão proibido |
|---|---|---|
| Nome / texto livre | `@"^\p{L}[\p{L}\s'-]*$"` | `@"^[a-zA-Z\s]+$"` |
| Descrição longa | `@"^[\p{L}\p{N}\s\-'.,!?()]+$"` | `@"^[a-zA-Z0-9\s]+$"` |
| CPF | `@"^\d{3}\.\d{3}\.\d{3}-\d{2}$"` | — |
| CEP | `@"^\d{5}-?\d{3}$"` | — |

> **Exemplos de nomes válidos PT-BR:** José, João, Márcia, Renata, André, Ângela,
> Luís, Conceição, Sebastião, Cristóvão.
> Todos devem passar a validação com `\p{L}` e falhar com `[a-zA-Z]`.
```

---

## Dependency Graph

```
angular-patterns-reference.md  ←── referenced by ──→  coder-angular-frontend.md (GUARDRAIL)
                                                    →  coder-dotnet-backend.md (G10 notes)
```

The reference file is a **read-time dependency** (the agent reads it during code generation),
not a pipeline dependency between agents.

---

## Invariants

1. G10 must be numbered sequentially after G9 — never renumber existing guardrails.
2. The `u` flag is mandatory for all Angular `Validators.pattern` calls on text fields — it is not optional.
3. CPF, CNPJ, CEP, phone, and email patterns are **not** changed by this fix.
4. Both occurrences of `version` in `coder-angular-frontend.md` frontmatter must be bumped.
