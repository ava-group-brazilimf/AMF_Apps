# Agent Development Tasks: Unicode-Safe Regex Guardrail

**Plan**: `specs/007-unicode-safe-regex-guardrail/plan.md`
**Agent IDs**: `ava-stack-dotnet-backend`, `ava-stack-angular-frontend` | **Phase**: `F3` | **Module**: `tech-stack`

> Change type: `bugfix` / modify-existing. Complete categories sequentially.
> Mark [P] indicates tasks parallelizable within a category (independent files).
> Categories 1, 3, and 4 are reduced/N/A for modify-existing.

---

## Category 1 — Pré-condições (modify-existing)

Verificar estado atual antes de qualquer edição.

- [X] **1.1** Confirmar que `version` em `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` (linha 10) é `"1.0.0"` — pré-condição para o bump em 2.1
- [X] **1.2** [P] Confirmar que `version` em `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (linhas 3 e 12) é `1.0.0` e `"1.0.0"` — pré-condição para o bump em 2.3
- [X] **1.3** [P] Confirmar que a última seção de `src/shared/data/patterns/angular/angular-patterns-reference.md` é `## Pipes — Formatação Monetária` (sem seção PT-BR Validation Patterns ainda) — pré-condição para 2.7

---

## Category 2 — Edições nos Agentes e Referência (corpo principal)

Depende da Category 1. Tarefas que tocam arquivos diferentes podem ser executadas em paralelo.

### Agente Backend .NET — `coder-dotnet-backend.md`
*(Cenário S1 — Nominal P1)*

- [X] **2.1** Bumpar `version: "1.0.0"` → `version: "1.0.1"` na linha 10 de `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

- [X] **2.2** Inserir o bloco **G10** em `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` imediatamente após o final da seção G9 (após a linha que começa com `Rule: before closing any`) e antes do heading `## Clean Architecture Template`. O bloco a inserir é:

  ```markdown
  ### G10 — Regex Unicode-safe para campos de texto PT-BR (validação incorreta de caracteres acentuados)

  **Problema:** `[RegularExpression(@"^[a-zA-Z\s]+$")]` rejeita acentos e caracteres especiais do
  português (ã, ç, é, í, ó, ú, â, ê, ô, à, etc.). Nomes como "José", "João", "Márcia" falham na
  validação do modelo.

  **Regra:** Para qualquer propriedade de texto livre (Nome, Descrição, Endereço, Cidade, Observações, etc.):
  - ✅ OBRIGATÓRIO: `[RegularExpression(@"^\p{L}[\p{L}\s'-]*$")]`
  - ❌ PROIBIDO: qualquer padrão contendo `[a-zA-Z]` em campos de texto

  **Exceções — não alterar estes padrões** *(Cenário S4 — campos não-texto permanecem intactos)*:
  - Campos numéricos: `\d`, `[0-9]`
  - CPF: `@"^\d{3}\.\d{3}\.\d{3}-\d{2}$"`
  - CNPJ: `@"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"`
  - CEP: `@"^\d{5}-?\d{3}$"`
  - E-mail: `[EmailAddress]` (builtin)
  - UUID, código alfanumérico estrito (ex: placa veicular)

  **Verificação obrigatória:** Antes de emitir qualquer `[RegularExpression]` para campo tipo
  `string`/`text`, confirmar que o padrão não contém `[a-zA-Z]`. Se contiver, substituir pelo
  equivalente `\p{L}`.
  ```

### Agente Frontend Angular — `coder-angular-frontend.md`
*(Cenário S2 — Nominal P1)*

- [X] **2.3** [P] Bumpar as duas ocorrências de `version` em `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`:
  - Linha 3: `version: 1.0.0` → `version: 1.0.1`
  - Linha 12: `version: "1.0.0"` → `version: "1.0.1"`

- [X] **2.4** [P] Inserir o item abaixo na lista de princípios técnicos de `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`, imediatamente após a linha `- \`changeDetection: ChangeDetectionStrategy.OnPush\` obrigatório em **todos** os componentes gerados`:

  ```
  - Regex PT-BR Unicode-safe — `Validators.pattern(/^[\p{L}\s\-']+$/u)` obrigatório para campos de texto; `/^[a-zA-Z\s]+$/` é PROIBIDO
  ```

- [X] **2.5** [P] Inserir o bloco **GUARDRAIL (Unicode Regex PT-BR)** em `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`, imediatamente após o GUARDRAIL de `msal.config.ts` (linha ~868 — texto âncora: `⚠️ **GUARDRAIL** — apenas placeholders \`REPLACE_WITH_*\`. NUNCA hardcodar Client ID, Tenant ID ou URLs reais.`) e antes do próximo heading de seção. O bloco a inserir é:

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

### Referência de Padrões Angular — `angular-patterns-reference.md`
*(Cenário S3 — Referência Canônica P2)*

- [X] **2.6** [P] Bumpar `version: "1.0.0"` → `version: "1.0.1"` na linha 4 do frontmatter de `src/shared/data/patterns/angular/angular-patterns-reference.md`

- [X] **2.7** [P] Acrescentar ao final de `src/shared/data/patterns/angular/angular-patterns-reference.md` (após a última linha da seção `## Pipes — Formatação Monetária`) a nova seção:

  ```markdown
  ---

  ## PT-BR Validation Patterns

  Padrões canônicos de validação para campos de texto em sistemas brasileiros.
  Consumido por: `ava-stack-dotnet-backend` (G10), `ava-stack-angular-frontend` (GUARDRAIL Unicode Regex PT-BR).

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

  ### C# — [RegularExpression] (System.ComponentModel.DataAnnotations)

  | Campo | Padrão canônico | Padrão proibido |
  |---|---|---|
  | Nome / texto livre | `@"^\p{L}[\p{L}\s'-]*$"` | `@"^[a-zA-Z\s]+$"` |
  | Descrição longa | `@"^[\p{L}\p{N}\s\-'.,!?()]+$"` | `@"^[a-zA-Z0-9\s]+$"` |
  | CPF | `@"^\d{3}\.\d{3}\.\d{3}-\d{2}$"` | — |
  | CEP | `@"^\d{5}-?\d{3}$"` | — |

  > **Exemplos de nomes válidos PT-BR que DEVEM ser aceitos:**
  > José, João, Márcia, Renata, André, Ângela, Luís, Conceição, Sebastião, Cristóvão.
  ```

---

## Category 3 — Schema Updates

**N/A** — plan section 7 confirma que nenhum schema (`agent-task.schema.json` / `agent-result.schema.json`) é alterado nesta feature.

---

## Category 4 — Registro em module.yaml

**N/A** — change type `modify-existing`. Ambos os agentes já estão registrados em `src/modules/ava-fabric-agents/tech-stack/module.yaml`. Nenhuma nova entrada necessária.

---

## Category 5 — Quality Gate Checklists

Executar após completar Category 2.

- [X] **5.1** Executar Scenario D do quickstart: confirmar que nenhum padrão `[a-zA-Z]` não-comentado permanece nos arquivos de agente:

  ```powershell
  # Backend
  Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-dotnet-backend.md" -Pattern "\[a-zA-Z\]" |
    Where-Object { $_.Line -notmatch "PROIBIDO|proibido|forbidden|G10" }
  # Resultado esperado: nenhuma linha (0 matches)

  # Frontend
  Select-String -Path "src\modules\ava-fabric-agents\tech-stack\agents\coder-angular-frontend.md" -Pattern "\[a-zA-Z" |
    Where-Object { $_.Line -notmatch "PROIBIDO|proibido|forbidden|GUARDRAIL" }
  # Resultado esperado: nenhuma linha (0 matches)
  ```

- [X] **5.2** [P] Verificar os 7 critérios de aceite do quickstart.md:

  | Critério | Comando | Resultado esperado |
  |---|---|---|
  | G10 presente | `Select-String ... -Pattern "G10"` em `coder-dotnet-backend.md` | 1 match |
  | Versão backend | `Select-String ... -Pattern 'version: "1.0.1"'` | 1 match |
  | GUARDRAIL Angular | `Select-String ... -Pattern "Unicode Regex PT-BR"` em `coder-angular-frontend.md` | 1 match |
  | One-liner princípios | `Select-String ... -Pattern "Regex PT-BR Unicode-safe"` | 1 match |
  | Versão frontend (×2) | `Select-String ... -Pattern "1.0.1"` | 2 matches |
  | Seção PT-BR | `Select-String ... -Pattern "PT-BR Validation Patterns"` | 1 match |
  | Sem padrões proibidos | Scenario D (task 5.1) | 0 matches |

---

## Category 6 — Validação de Aceite

Pode executar em paralelo com Category 7 após Category 5.

- [X] **6.1** [P] Executar Scenario A (quickstart.md): verificar G10 e versão `1.0.1` em `coder-dotnet-backend.md`
- [X] **6.2** [P] Executar Scenario B (quickstart.md): verificar GUARDRAIL e one-liner em `coder-angular-frontend.md`
- [X] **6.3** [P] Executar Scenario C (quickstart.md): verificar `## PT-BR Validation Patterns` em `angular-patterns-reference.md`
- [X] **6.4** Executar Scenario D (quickstart.md): confirmar 0 padrões `[a-zA-Z]` não-comentados em ambos os agentes — gate blocking para release
- [X] **6.5** Executar Scenario E (quickstart.md): smoke test com invocação real do agente em `projects/Meu-ERP/` ou `projects/test-determinism/`; verificar que campos `Nome` gerados usam `\p{L}` no `.cs` e `/^[\p{L}\s\-']+$/u` no `.ts` — **obrigatório na primeira execução pós-implementação**

---

## Category 7 — Documentação e Catálogo

Pode executar em paralelo com Category 6.

- [X] **7.1** [P] Adicionar entrada no `CHANGELOG.md` com a seguinte estrutura:

  ```markdown
  ## [Unreleased]

  ### Fixed
  - `ava-stack-dotnet-backend` v1.0.1 — Guardrail G10: `[a-zA-Z]` proibido para campos de texto PT-BR; padrão `\p{L}` obrigatório em `[RegularExpression]`
  - `ava-stack-angular-frontend` v1.0.1 — GUARDRAIL Unicode Regex PT-BR: `/^[a-zA-Z\s]+$/` proibido; `/^[\p{L}\s\-']+$/u` obrigatório em `Validators.pattern`

  ### Added
  - `angular-patterns-reference.md` v1.0.1 — Nova seção **PT-BR Validation Patterns** com tabela de padrões canônicos para Angular e C#
  ```

- [X] **7.2** [P] Atualizar `docs/agents-catalog.md` — bumpar campo `version` dos dois agentes:
  - `ava-stack-dotnet-backend`: `1.0.0` → `1.0.1`
  - `ava-stack-angular-frontend`: `1.0.0` → `1.0.1`

---

## Completion Checklist

- [X] Category 1 (pré-condições) verificada
- [X] Category 2 (todas as 7 edições): 2.1 ✓, 2.2 ✓, 2.3 ✓, 2.4 ✓, 2.5 ✓, 2.6 ✓, 2.7 ✓
- [X] Category 3 N/A (sem schema changes)
- [X] Category 4 N/A (sem module.yaml changes)
- [X] Category 5 (quality gates): Scenario D retorna 0 matches
- [X] Category 6 (validação de aceite): Scenarios A–D aprovados
- [X] Category 7 (docs): CHANGELOG.md e agents-catalog.md atualizados
- [X] Nenhum `[NEEDS CLARIFICATION]` restante
