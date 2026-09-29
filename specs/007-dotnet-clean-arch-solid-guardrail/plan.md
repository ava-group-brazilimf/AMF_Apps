# Implementation Plan: Clean Architecture & SOLID Guardrail for coder-dotnet-backend

**Branch**: `007-dotnet-clean-arch-solid-guardrail` | **Date**: 2026-07-07
**Spec**: [specs/007-dotnet-clean-arch-solid-guardrail/spec.md](spec.md)
**PBI**: 2274 (child tasks: 2275, 2276, 2277, 2278)

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` — 1 agent file |
| **Target File** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |
| **Primary Requirement** | Add G10 guardrail (Clean Architecture anti-patterns) and post-generation grep verification to `ava-stack-dotnet-backend` so that code violating SRP/DIP is prevented at generation time and caught deterministically if it slips through |
| **Technical Approach** | Four targeted edits to the Markdown agent file: (1) version bump in frontmatter, (2) rule 7 appended to `## Regras Invioláveis`, (3) `### G10` block inserted after G9, (4) `## Verificação Pós-Geração` section inserted before the Security Compliance Gate |
| **Version Bump** | `1.0.0 → 1.0.1` (PATCH — no contract change) |

---

## Constitution Check

- [x] **Article I** — No technology versions hardcoded in G10. Rules reference patterns (`ISender`, `IService`, `ITitleRepository`) resolved at runtime from project context.
- [x] **Article II** — Frontmatter: only `version` changes (`1.0.0 → 1.0.1`). No contract fields (`name`, `allowed-tools`, `description`) change. Output Contract YAML block is unchanged.
- [x] **Article IV** — `module.yaml` entry (`ava-coder-dotnet-backend`) already exists; no registration changes needed.
- [x] **Article V** — All new agent body content written in Brazilian Portuguese, consistent with existing file language.
- [x] **Article IX** — G10 directly enforces the mandatory layer order (Domain → Application → Infrastructure → Presentation); no cross-layer coupling introduced.
- [x] **Article X** — PATCH bump: guardrail additions are hardening, not contract changes.
- [x] **Article XI** — SKILL.md unchanged; no dispatch changes needed.
- [x] No `[NEEDS CLARIFICATION]` markers remain.

---

## Technical Context

**Language/Version**: Markdown (`.md`) — agent instruction file, no runtime language
**Primary Dependencies**: None (text edit only)
**Storage**: N/A
**Testing**: PowerShell `Select-String` validations (see `quickstart.md`)
**Target Platform**: GitHub Copilot / Claude Code agent runtime
**Project Type**: Agent instruction file
**Performance Goals**: N/A
**Constraints**: New content must follow existing G1–G9 guardrail formatting conventions
**Scale/Scope**: 1 file, ~60 lines of new content

---

## Project Structure

### Documentation (this feature)

```text
specs/007-dotnet-clean-arch-solid-guardrail/
├── spec.md          ✅ Created
├── research.md      ✅ Created (Phase 0)
├── data-model.md    ✅ Created (Phase 1)
├── quickstart.md    ✅ Created (Phase 1)
├── plan.md          ✅ This file (Phase 1)
├── checklists/
│   └── requirements.md  ✅ Created
└── tasks.md         — Phase 2 output (/speckit.tasks command)
```

### Source Code (affected file)

```text
src/modules/ava-fabric-agents/tech-stack/agents/
└── coder-dotnet-backend.md    ← sole file being modified
```

---

## Implementation Phases

### Phase 1 — Version Bump

Edit frontmatter `version: "1.0.0"` → `version: "1.0.1"`.

**Insertion**: Line 6, in the YAML frontmatter block.

---

### Phase 2 — Rule 7 in Regras Invioláveis (PBI 2275 + 2276)

Append rule 7 to the numbered list under `## Regras Invioláveis de Código`.

**Current last rule**: `6. Comentários XML em membros públicos`

**New rule**:
```
7. Controllers injetam apenas `ISender` (MediatR) ou `IService` — nunca `DbContext`, Repository concreto ou Service concreto diretamente
```

---

### Phase 3 — G10 Guardrail Block (PBI 2275 + 2276)

Insert `### G10` after G9's final line and before `## Clean Architecture Template`.

**Boundary markers** (confirmed in research.md §1):
- End of G9: `Rule: before closing any .csproj generation, grep the project's .cs files...`
- Start of next section: `## Clean Architecture Template`

**G10 content** (Brazilian Portuguese, following G1–G9 style — ERRADO/CORRETO pairs):

```
### G10 — Anti-Patterns de Clean Architecture (SOLID: SRP e DIP)

Casos observados: lógica de negócio em controllers; acesso direto ao `DbContext`
na camada Application ou API; instanciação direta de repositories ou services.

| Regra  | Camada        | Proibido                               | Alternativa obrigatória                         |
|--------|---------------|----------------------------------------|-------------------------------------------------|
| G10-R1 | API/Controller | Qualquer lógica de decisão no action  | `await _sender.Send(cmd)` exclusivamente        |
| G10-R2 | Application    | `_dbContext.EntitySet.*` no handler   | `await _repo.MetodoAsync(...)` via interface    |
| G10-R3 | qualquer       | `new ConcreteRepository(...)`         | Injetar `IRepository` via construtor            |
| G10-R4 | qualquer       | `new ConcreteService(...)`            | Injetar `IService` via construtor               |
```

Four ERRADO/CORRETO code pairs covering SRP × 1, DIP × 3.
See spec.md §4.1 for the exact C# code for each pair.

---

### Phase 4 — Post-Generation Verification Section (PBI 2277)

Insert `## Verificação Pós-Geração — Clean Architecture Compliance` between the
closing fence of `## Output Contract` and the `## Security Compliance Review Gate` heading.

**Boundary markers** (confirmed in research.md §1):
- End of Output Contract: closing ` ``` ` after the `mandatory_docs` YAML key
- Start of Security Gate: `## Security Compliance Review Gate`

**Section content** includes:
- Execution timing note (after code generation, before Security Gate)
- Two grep commands (with `| grep -v "/Infrastructure/"` filter per research.md §2)
- Decision table: zero lines = PASS; ≥1 line = VIOLATION DETECTED with file:line output format

---

### Phase 5 — Validation (PBI 2278)

Run all 8 validations from `quickstart.md`.

---

## Complexity Tracking

| Item | Decision |
|---|---|
| `--exclude-path` not in GNU grep | Use `pipe \| grep -v "/Infrastructure/"` — portable across Git Bash and Linux (research.md §2) |
| SRP violations (business logic in controller) not grep-detectable | Documented in G10-R1 as a generation-time rule; grep gates cover mechanically detectable DIP violations (R2/R3/R4) |
| Fence balance | Implementation must verify total ` ``` ` count remains even after inserting new code blocks |
| Rule 7 vs. GUARDRAILS placement | Rule 7 added to both `## Regras Invioláveis` (to satisfy PBI AC #1 literally) and G10 in GUARDRAILS (for detailed documentation per file convention) |

---

## Test Strategy

| Validation | Command | Expected |
|---|---|---|
| Version bump | `Select-String ... 'version: "1\.0\.1"'` | 1 match |
| G10 heading | `Select-String ... "### G10"` | 1 match |
| ERRADO/CORRETO pairs (≥4 each) | PowerShell regex match count | ≥4 each |
| Post-gen section | `Select-String ... "Verificação Pós-Geração"` | 1 match |
| Grep command documented | `Select-String ... "new \[A-Za-z\]\*Repository"` | 1 match |
| Rule 7 present | `Select-String ... "ISender \(MediatR\)"` | ≥1 match |
| Section order | LineNumber comparisons | G10 < CA Template; VerifGate < SecGate |
| G1–G9 intact | `1..9` loop checking `### G{N}` | All 9 present |

Full commands: [quickstart.md](quickstart.md)

---

## 9. Complexity Tracking

N/A — covered in the **Complexity Tracking** section above.

---

## 10. Test Strategy

N/A — covered in the **Test Strategy** section above. Validation commands are in [quickstart.md](quickstart.md).
