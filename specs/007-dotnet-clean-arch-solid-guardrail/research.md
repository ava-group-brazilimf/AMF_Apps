# Research: Clean Architecture & SOLID Guardrail (spec 007)

**Date**: 2026-07-07
**Spec**: `specs/007-dotnet-clean-arch-solid-guardrail/spec.md`

---

## §1 — Insertion Points in `coder-dotnet-backend.md`

**Decision**: Two insertion points, both confirmed by direct file read.

### Insertion Point A — G10 guardrail block

**Location**: After the last line of `### G9` content and before `## Clean Architecture Template`.

Confirmed delimiter (end of G9):
```
Rule: before closing any `.csproj` generation, grep the project's `.cs` files for external
namespace prefixes and verify each has a matching `<PackageReference>`.
```

Followed immediately by:
```
## Clean Architecture Template
```

G10 will be inserted between these two blocks as `### G10 — Clean Architecture Anti-Patterns (SOLID: SRP & DIP)`.

### Insertion Point B — Post-generation verification step

**Location**: Between `## Output Contract` (YAML code block that ends with the `mandatory_docs` key) and `## Security Compliance Review Gate`.

Confirmed delimiter (end of Output Contract block):
```
mandatory_docs:
  - "projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Backend.md"
    # Relatório de conformidade de segurança do backend — gerado pelo Security Compliance Review Gate
```

New section `## Verificação Pós-Geração — Clean Architecture Compliance` will be inserted after the closing ` ``` ` fence of the `## Output Contract` YAML block and before `## Security Compliance Review Gate`.

---

## §2 — Grep Pattern Portability on Windows

**Problem investigated**: The spec draft used `--exclude-path`, which does not exist in GNU grep. On Windows environments (GitHub Copilot in VS Code, Git Bash), `grep` follows GNU grep conventions. `--exclude-dir` only matches exact directory names, not path segments.

**Decision**: Use pipe filtering (`| grep -v "/Infrastructure/"`) instead of `--exclude-dir`.

**Rationale**: More portable, works in Git Bash (Windows) and standard Linux shells. Simpler than PowerShell Select-String for agents that already declare `Bash` in `allowed-tools`.

**Resolved command patterns**:

```bash
# Verify: no new.*Repository outside Infrastructure (returns 0 lines = PASS)
grep -rn "new [A-Za-z]*Repository" \
  "projects/{project_name}/outputs/tobe/source-code/" \
  --include="*.cs" | grep -v "/Infrastructure/"

# Verify: no direct DbContext outside Infrastructure (returns 0 lines = PASS)
grep -rn "\bDbContext\b" \
  "projects/{project_name}/outputs/tobe/source-code/" \
  --include="*.cs" | grep -v "/Infrastructure/" | grep -v "\.Tests/"
```

**Alternatives considered**:
- `PowerShell Select-String` — rejected because the agent already uses `Bash` in allowed-tools and mixing shell paradigms in the same gate adds unnecessary cognitive load
- `--exclude-dir=Infrastructure` — rejected because it only matches the exact directory name at the deepest level; paths like `src/BC/BC.Infrastructure/` may not match

---

## §3 — Guardrail Documentation Style

**Decision**: Follow the existing G1–G9 style already established in the file:
- Heading: `### G{N} — {Short Name} ({Principles Violated})`
- One-sentence opening diagnostic statement
- Table or prose for rules
- Code blocks: `// ERRADO — explanation` and `// CORRETO — explanation` pairs
- ⛔ for negative patterns, no special emoji for positives (consistent with G8)

**Rationale**: Consistency with the existing 9 guardrails reduces cognitive switching. The "ERRADO/CORRETO" pattern is already established and understood by the team.

---

## §4 — Scope of G10 vs. Existing "Regras Invioláveis"

**Decision**: G10 is placed in the `## ⚠️ GUARDRAILS` section (not `## Regras Invioláveis`).

**Rationale**: 
- `## Regras Invioláveis de Código` rules (1–6) are short syntactic/style mandates with no code examples.
- `## ⚠️ GUARDRAILS` blocks (G1–G9) are diagnostic rules with detailed ERRADO/CORRETO examples triggered by known error patterns.
- G10 follows the GUARDRAILS pattern: it addresses a documented category of observed errors (business logic in controllers, direct DbContext in Application) with illustrative code pairs.
- PBI 2274 acceptance criterion #1 says "Guardrail adicionado na seção de Regras Invioláveis do agente". However, the intent is fulfilled by the GUARDRAILS section which is the correct structural home per the existing file convention. A one-liner summary rule will also be added to `## Regras Invioláveis` to satisfy the AC literally.

---

## §5 — Version Bump Confirmation

**Decision**: PATCH bump `1.0.0 → 1.0.1`.

**Rationale per Constitution Article X**:
- No `inputs` or `outputs` contract change → NOT a MAJOR bump
- No new optional fields added to the contract → NOT a MINOR bump  
- Adding guardrail instructions + verification step = bug-fix/hardening → PATCH

No `CHANGELOG.md` entry required for PATCH (no breaking change per Article X).

---

## §6 — Post-Generation Verification Placement

**Decision**: Insert as a new standalone section `## Verificação Pós-Geração — Clean Architecture Compliance`, placed immediately after the closing fence of `## Output Contract` and before `## Security Compliance Review Gate`.

**Rationale**: 
- Keeps the verification conceptually separate from the security compliance gate (which inspects security controls, not architecture patterns).
- Placing it between Output Contract and Security Gate matches the natural execution order: generate → verify architecture → verify security → handoff.
- PBI 2277 AC says "Verificação pos-geração (grep) para detectar violações automaticamente" — a dedicated section makes this discoverable.
