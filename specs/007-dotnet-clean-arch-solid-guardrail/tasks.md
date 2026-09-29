# Agent Development Tasks: ava-stack-dotnet-backend (PATCH 1.0.1)

**Plan**: `specs/007-dotnet-clean-arch-solid-guardrail/plan.md`
**Agent ID**: `ava-stack-dotnet-backend` | **Phase**: `F3` | **Module**: `tech-stack`
**Change Type**: `modify-existing` â€” 1 file: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
**PBI**: 2274 (child tasks: 2275, 2276, 2277, 2278)

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Categories 3 and 4 are **N/A** (no schema changes; module.yaml entry already exists).

---

## Category 1 â€” Agent Frontmatter & Contract Definition

Must complete before any other category.
Category 1.5 (SKILL.md) and Output Contract are **N/A** â€” `modify-existing` PATCH, no contract change.

- [X] **1.1** Open `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
- [X] **1.2** Change frontmatter `version:` from `"1.0.0"` to `"1.0.1"` â€” PATCH bump per Constitution Article X (hardening, no contract change)

---

## Category 2 â€” Agent Behavior & Instructions

Depends on Category 1. Tasks 2.1 and 2.2â€“2.6 target different insertion points and can be done in either order, but the file must be in a consistent state between edits.

- [X] **2.1** Append rule 7 to `## Regras InviolÃ¡veis de CÃ³digo` in `coder-dotnet-backend.md`, immediately after the current rule 6 (`ComentÃ¡rios XML em membros pÃºblicos`):
  ```
  7. Controllers injetam apenas `ISender` (MediatR) ou `IService` â€” nunca `DbContext`, Repository concreto ou Service concreto diretamente
  ```

- [X] **2.2** Insert `### G10` heading, opening diagnostic sentence, and G10-R1â€“R4 rules table after the final line of `### G9` and before `## Clean Architecture Template` in `coder-dotnet-backend.md`. Boundary: G9 ends with `Rule: before closing any .csproj generation, grep...`; next heading is `## Clean Architecture Template`. Content (Brazilian Portuguese, follows G1â€“G9 formatting style):
  ```
  ### G10 â€” Anti-Patterns de Clean Architecture (SOLID: SRP e DIP)

  Casos observados: lÃ³gica de negÃ³cio em controllers; acesso direto ao `DbContext`
  na camada Application ou API; instanciaÃ§Ã£o direta de repositories ou services.

  | Regra  | Camada         | Proibido                                | Alternativa obrigatÃ³ria                      |
  |--------|----------------|-----------------------------------------|----------------------------------------------|
  | G10-R1 | API/Controller | Qualquer lÃ³gica de decisÃ£o no action    | `await _sender.Send(cmd)` exclusivamente     |
  | G10-R2 | Application    | `_dbContext.EntitySet.*` no handler     | `await _repo.MetodoAsync(...)` via interface |
  | G10-R3 | qualquer       | `new ConcreteRepository(...)`           | Injetar `IRepository` via construtor         |
  | G10-R4 | qualquer       | `new ConcreteService(...)`              | Injetar `IService` via construtor            |
  ```

- [X] **2.3** Insert anti-pattern pair 1 (G10-R1 / SRP) immediately after the G10 rules table â€” business logic in controller. Include `// â›” ERRADO` and `// âœ… CORRETO` C# code blocks (spec Â§4.1, pair 1):
  - **ERRADO**: controller action that calls `_dbContext.Titles.Find(titleId)` and contains `if (amount > title.Balance) return BadRequest(...)` inline
  - **CORRETO**: controller action containing only `await _sender.Send(new SettleTitleCommand(titleId, amount), ct)` â€” no DbContext, no business decisions

- [X] **2.4** Insert anti-pattern pair 2 (G10-R2 / DIP) after pair 1 â€” DbContext direct in Application handler. Include `// â›” ERRADO` and `// âœ… CORRETO` C# code blocks (spec Â§4.1, pair 2):
  - **ERRADO**: handler constructor injects `AppDbContext` and uses `_dbContext.Titles.FirstOrDefaultAsync(...)` directly
  - **CORRETO**: handler constructor injects `ITitleRepository` and uses `await _repo.GetByIdAsync(cmd.TitleId, ct)`

- [X] **2.5** Insert anti-pattern pair 3 (G10-R3 / DIP) after pair 2 â€” `new Repository()` in handler. Include `// â›” ERRADO` and `// âœ… CORRETO` C# code blocks (spec Â§4.1, pair 3):
  - **ERRADO**: handler method body creates `var repo = new TitleRepository(new AppDbContext())`
  - **CORRETO**: handler uses constructor-injected `private readonly ITitleRepository _repo`

- [X] **2.6** Insert anti-pattern pair 4 (G10-R4 / DIP) after pair 3 â€” `new Service()` in handler. Include `// â›” ERRADO` and `// âœ… CORRETO` C# code blocks (spec Â§4.1, pair 4):
  - **ERRADO**: handler body creates `var svc = new EmailService()`
  - **CORRETO**: handler uses constructor-injected `private readonly IEmailService _emailSvc`

- [X] **2.7** Insert `## VerificaÃ§Ã£o PÃ³s-GeraÃ§Ã£o â€” Clean Architecture Compliance` section in `coder-dotnet-backend.md` between the closing ` ``` ` fence of `## Output Contract` and the `## Security Compliance Review Gate` heading. Content (Brazilian Portuguese):
  - Timing note: executes AFTER all `.cs` files are generated and BEFORE the Security Compliance Review Gate
  - Two bash grep commands using `| grep -v "/Infrastructure/"` filter (research.md Â§2 â€” `--exclude-path` not valid in GNU grep):
    ```bash
    grep -rn "new [A-Za-z]*Repository" \
      "projects/{project_name}/outputs/tobe/source-code/" \
      --include="*.cs" | grep -v "/Infrastructure/"

    grep -rn "\bDbContext\b" \
      "projects/{project_name}/outputs/tobe/source-code/" \
      --include="*.cs" | grep -v "/Infrastructure/" | grep -v "\.Tests/"
    ```
  - Decision table: zero output lines â†’ `âœ… Clean Architecture compliance verificada`; â‰¥1 line â†’ `â›” VIOLATION DETECTED` with file:line and rule ID (G10-R1..R4)
  - Violation output format block (shows arquivo:linha, padrÃ£o detectado, regra, aÃ§Ã£o)
  - On violation: agent MUST NOT write further output files and MUST NOT proceed to the Security Compliance Review Gate â€” the pipeline halts at the verification step

---

## Category 3 â€” Shared Schema Updates

**N/A** â€” No schema changes. Plan section confirms `agent-task.schema.json` and `agent-result.schema.json` are unaffected.

---

## Category 4 â€” Module Registration

**N/A** â€” `ava-coder-dotnet-backend` is already registered in `src/modules/ava-fabric-agents/tech-stack/module.yaml` with `file: agents/coder-dotnet-backend.md`. No new entry required.

---

## Category 5 â€” Quality Gate Checklists

- [X] **5.1** Verify fence balance after all Category 2 insertions â€” count all ` ``` ` occurrences in `coder-dotnet-backend.md` and confirm the total is even (each opening fence has a closing fence). Use: `(Select-String -Path "...\coder-dotnet-backend.md" -Pattern "^\`\`\`").Count`

- [X] **5.2** Verify section order is correct using line-number comparisons (quickstart.md Validation 7):
  - `G10` line < `## Clean Architecture Template` line
  - `## VerificaÃ§Ã£o PÃ³s-GeraÃ§Ã£o` line < `## Security Compliance Review Gate` line

---

## Category 6 â€” Acceptance Validation & QA Integration

Depends on Category 2. All tasks [P] â€” independent read checks on the same file.

- [X] **6.1** [P] Run Validation 1 â€” version bumped: `Select-String -Path "...\coder-dotnet-backend.md" -Pattern 'version: "1\.0\.1"'` â†’ expect 1 match
- [X] **6.2** [P] Run Validation 2 â€” G10 present: `Select-String ... -Pattern "### G10"` â†’ expect 1 match
- [X] **6.3** [P] Run Validation 3 â€” ERRADO/CORRETO pairs: PowerShell `[regex]::Matches($content, "ERRADO").Count` and `"CORRETO".Count` â†’ expect â‰¥ 4 each
- [X] **6.4** [P] Run Validation 4 â€” post-gen section present: `Select-String ... -Pattern "VerificaÃ§Ã£o PÃ³s-GeraÃ§Ã£o"` â†’ expect 1 match
- [X] **6.5** [P] Run Validation 5 â€” grep command documented: `Select-String ... -Pattern "new \[A-Za-z\]\*Repository"` â†’ expect 1 match
- [X] **6.6** [P] Run Validation 6 â€” rule 7 present: `Select-String ... -Pattern "ISender \(MediatR\)"` â†’ expect â‰¥ 1 match
- [X] **6.7** [P] Run Validation 7 â€” section order correct (line-number comparisons, see quickstart.md Â§Validation 7) â†’ expect `âœ… Section order CORRECT`
- [X] **6.8** [P] Run Validation 8 â€” G1â€“G9 intact: loop `1..9` checking `### G{N}` â†’ expect all 9 present
- [X] **6.9** End-to-end Sophia validation (SC-04): if `projects/sophia/outputs/tobe/source-code/` exists, run the grep scenario from `quickstart.md Â§End-to-End Scenario` against it and confirm zero matches. If the Sophia project does not exist yet, mark as **N/A** and record that SC-04 will be verified on the next Sophia code-generation run.
---

## Category 7 â€” Documentation & Catalog Update

Can run parallel with Category 6.

- [X] **7.1** [P] Update `docs/agents-catalog.md` â€” add `| **VersÃ£o** | \`1.0.1\` |` row to the `ava-stack-dotnet-backend` table (currently at line ~568), and append a note: `Guardrail G10 (Clean Architecture anti-patterns SRP/DIP) e verificaÃ§Ã£o pÃ³s-geraÃ§Ã£o adicionados.`

- [X] **7.2** [P] Add entry to `CHANGELOG.md` under a new `## [2026-07-07]` heading (or prepend to the existing most recent section if the date matches), describing:
  ```
  ### ðŸ”§ Changed â€” `ava-stack-dotnet-backend` (coder-dotnet-backend.md) v1.0.0 â†’ v1.0.1

  - **`### G10` â€” Anti-Patterns de Clean Architecture (SOLID: SRP e DIP) [NOVO]**: guardrail com
    4 regras (G10-R1 SRP, G10-R2/R3/R4 DIP) e 4 pares de exemplos ERRADO/CORRETO em C#.
    Previne: lÃ³gica de negÃ³cio em controllers, DbContext direto na camada Application,
    `new Repository()` e `new Service()` fora de Infrastructure.
  - **`## VerificaÃ§Ã£o PÃ³s-GeraÃ§Ã£o â€” Clean Architecture Compliance` [NOVO]**: gate determinÃ­stico
    pÃ³s-geraÃ§Ã£o com dois comandos grep que verificam `new.*Repository` e `DbContext` fora de
    Infrastructure. Zero resultados = PASS; â‰¥1 resultado = VIOLATION DETECTED (com arquivo:linha).
  - **Regra 7 em `## Regras InviolÃ¡veis` [NOVO]**: controllers injetam apenas `ISender` (MediatR)
    ou `IService` â€” nunca DbContext, Repository concreto ou Service concreto diretamente.
  - PBI 2274 | Child tasks: 2275, 2276, 2277, 2278
  ```

---

## Completion Checklist

- [X] Category 1 complete â€” version bumped to `1.0.1`
- [X] Category 2 complete â€” rule 7, G10 (4 pairs), and `## VerificaÃ§Ã£o PÃ³s-GeraÃ§Ã£o` inserted
- [X] Category 3 â€” N/A
- [X] Category 4 â€” N/A
- [X] Category 5 complete â€” fence balance verified; section order verified
- [X] Category 6 complete â€” all 8 quickstart validations pass; 6.9 verified or marked N/A
- [X] Category 7 complete â€” `docs/agents-catalog.md` and `CHANGELOG.md` updated
- [X] Agent `.md` frontmatter validated (`version: "1.0.1"`, all other fields unchanged)
- [X] No existing guardrails G1â€“G9 modified or removed

---

## Dependency Graph

```
Category 1 (version bump)
    â†“
Category 2 (behavior edits) â”€â”€â”€ tasks 2.1..2.7 must be applied to the file sequentially
    â†“
Category 5 (quality gates) â”€â”€â”€â”€ fence balance + section order checks
    â†“
Category 6 (validation) â”€â”€â”€â”€â”€â”€â”€â”€ 6.1..6.8 [P] all independent
Category 7 (docs) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ [P] parallel with Category 6
```

## Parallel Execution

All of Category 6 tasks (6.1â€“6.8) can run simultaneously after Category 5 passes.
Tasks 7.1 and 7.2 can run simultaneously with Category 6.

## MVP Scope

Category 1 + Category 2 (tasks 2.1â€“2.7) = minimum deliverable satisfying PBI ACs 1â€“3.
Category 6 = satisfies AC #4 (Sophia zero violations â€” via Validation 8 equivalent).
