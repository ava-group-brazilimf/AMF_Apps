---
name: git-patterns-reference
description: "Referência de padrões Git — conventional commits, branch naming e PR standards"
version: "1.0.0"
used_by: [ava-tobe-architecture-technical]
---

# Git Patterns Reference

## Conventional Commits

Toda mensagem de commit DEVE seguir o formato:

```
<tipo>(<escopo>): <descrição curta em inglês>

[corpo opcional — explica o "porquê", não o "o quê"]

[rodapé opcional — referência ao ticket: Refs: US-1057]
```

### Tipos permitidos

| Tipo | Quando usar | Exemplo |
|---|---|---|
| `feat` | Nova funcionalidade | `feat(accounts-payable): add PostPayment command` |
| `fix` | Correção de bug | `fix(party): null reference on TaxId validation` |
| `refactor` | Mudança de estrutura sem alterar comportamento | `refactor(shared-kernel): extract ValueObject base record` |
| `chore` | Tarefas de manutenção (build, deps, config) | `chore(deps): bump MediatR to 12.3.0` |
| `docs` | Documentação apenas | `docs(coding-standards): add reactive forms examples` |
| `test` | Adição ou correção de testes | `test(party): add unit tests for TaxId.Create` |
| `ci` | Mudanças em pipeline CI/CD | `ci: add SonarQube gate to PR pipeline` |
| `perf` | Melhoria de performance sem mudança de comportamento | `perf(query): replace EF tracking query with AsNoTracking` |

### Escopo

O escopo corresponde ao **Bounded Context** ou módulo impactado:

| Escopo | Bounded Context |
|---|---|
| `customer-supplier` | BC CustomerSupplier |
| `accounts-payable` | BC AccountsPayable |
| `accounts-receivable` | BC AccountsReceivable |
| `financial-setup` | BC FinancialSetup |
| `boleto-report` | BC BoletoReport |
| `shared-kernel` | SharedKernel (impacta todos os BCs) |
| `infra` | Infraestrutura transversal |
| `deps` | Dependências / pacotes |

> **Invariants:**
> - Descrição curta em **inglês**, modo imperativo, sem ponto final: `add`, `fix`, `remove`, `update`
> - Máximo 72 caracteres na primeira linha
> - NUNCA usar `update`, `change`, `modify` sem escopo — é genérico demais
> - Commits que quebram compatibilidade de API: adicionar `!` após tipo: `feat(api)!: rename Party endpoint`
> - Referência ao ticket no rodapé: `Refs: US-1057`

```
✅ feat(accounts-payable): add installment late fee calculation
✅ fix(customer-supplier): prevent duplicate TaxId registration
✅ refactor(shared-kernel): replace ValueObject class with abstract record
✅ chore(deps): bump FluentValidation to 11.9.0

❌ update Party              ← sem tipo, sem escopo, em português
❌ fix bug                   ← sem escopo, descrição vaga
❌ feat: various improvements ← múltiplas mudanças num único commit
❌ WIP                        ← nunca commitar WIP para branch principal
```

---

## Branch Naming

### Formato obrigatório

```
<tipo>/<ticket>-<descricao-kebab-case>
```

| Campo | Regra | Exemplo |
|---|---|---|
| `<tipo>` | `feature`, `fix`, `refactor`, `chore`, `docs` | `feature` |
| `<ticket>` | ID da User Story no Azure DevOps — formato `US-XXX` | `US-1057` |
| `<descricao>` | kebab-case, inglês, máximo 5 palavras | `coding-standards-doc` |

### Exemplos por tipo

```
✅ feature/US-1057-coding-standards-doc
✅ feature/US-1120-post-payment-command
✅ fix/US-983-taxid-null-reference
✅ refactor/US-1041-extract-value-object-base
✅ chore/US-1060-bump-mediatr-12
✅ docs/US-1057-angular-patterns-reference

❌ feature/coding-standards          ← sem ticket US-XXX
❌ feature/1057-coding-standards     ← ticket sem prefixo US-
❌ US-1057                           ← sem tipo nem descrição
❌ feature/TASK-42-fix               ← prefixo TASK inválido — usar US-
❌ main, develop, master             ← branches protegidas — nunca commitar direto
```

### Branches protegidas

| Branch | Política |
|---|---|
| `main` | Apenas via PR aprovado + pipeline verde |
| `develop` | Apenas via PR com mínimo 1 review |

---

## Pull Request Standards

### Tamanho

| Métrica | Limite |
|---|---|
| LOC alterados (excluindo gerados) | Máximo 400 |
| Arquivos alterados | Máximo 20 |
| Commits no PR | Máximo 10 (squash se necessário) |

> PRs maiores que 400 LOC devem ser quebrados em PRs menores por bounded context.

### Checklist obrigatório (todo PR)

```
[ ] Testes adicionados ou atualizados para o comportamento novo/corrigido
[ ] Cobertura de linha ≥ 90% (unit) — CI valida automaticamente
[ ] `dotnet format` executado — sem warnings de formatação
[ ] Nenhum `// TODO` ou `// FIXME` deixado em aberto
[ ] Nenhuma secret, connection string ou PII hardcoded
[ ] Título do PR segue formato: feat(escopo): descrição
[ ] Ticket Azure DevOps linkado no PR
```

### Regras de revisão

| Situação | Reviewers mínimos |
|---|---|
| Mudança em qualquer camada | 1 peer review |
| Mudança em `SharedKernel` | 2 reviews (inclui Tech Lead) |
| Mudança em camada `Domain` de qualquer BC | 2 reviews |
| Mudança em pipeline CI/CD | 1 review + aprovação DevOps |
| Alteração de ADR | Tech Lead obrigatório |

> **Invariants:**
> - NUNCA fazer merge sem pipeline verde (build + testes + SonarQube gate)
> - NUNCA aprovar o próprio PR
> - Branch deve partir de `develop` — nunca de `main` diretamente
> - Após merge: deletar branch de feature automaticamente
