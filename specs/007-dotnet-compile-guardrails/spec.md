# Agent Specification: Dotnet Coder Backend — Guardrails G10 & G11

**Feature Branch**: `007-dotnet-compile-guardrails`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: modify-existing (1 agent file — MINOR version bump)
**Input**: "Adicionar guardrails G10 e G11 ao agente coder-dotnet-backend.md para prevenção de
erros de compilação não cobertos; G10: conflitos de namespace entre BCs; G11: versão mínima do SDK."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (guardrail prose) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field       | Value |
|-------------|-------|
| **Agent ID**   | `ava-stack-dotnet-backend` |
| **Version**    | `1.0.0` → **`1.1.0`** (MINOR: new guardrail sections, backward-compatible) |
| **Phase**      | F3 (Tech Stack — codegen) |
| **Module**     | `tech-stack` |
| **Role**       | Generates production-ready C# code following Clean Architecture + CQRS. Extended with G10/G11 to block compilation failures before code is produced. |
| **Skill**      | `ava-stack-dotnet-backend` (already registered) |
| **Dispatch**   | user-facing via SKILL.md + internal via `ava-stack-orchestrator` |
| **Target file**| `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |

> **`modify-existing` notes:**
> - No new file. Edit the existing agent `.md` only.
> - `module.yaml` entry already exists — Category 4 (module registration) is N/A.
> - `SKILL.md` already exists — Category 1.5 (skill creation) is N/A.

---

## 2. Problem Statement

The `coder-dotnet-backend.md` agent carries guardrails G1–G9 that prevent known
systematic C# compilation errors (Mapster DI, async/await misuse, culture-aware
ops, etc.). Two categories of failure are **not yet covered**:

### G10 — Namespace conflict between Bounded Contexts (CS0104 / CS0234)
When two or more BCs are hosted in the same solution host (multi-BC, single
`Host.API`), root namespaces with a shared prefix produce ambiguous-reference
errors that the compiler reports only after all files are generated. Example:

```
error CS0104: 'Result' is an ambiguous reference between
              'Banking.Titles.Domain.Result' and 'Banking.Payments.Domain.Result'
```

Because this error only manifests at `dotnet build` time (not during generation),
the agent produces a full, broken code base before the problem is detected. The
fix requires a namespace-scan BEFORE any `.cs` file is written.

### G11 — SDK version mismatch (NETSDK1045)
`tobe_stack.backend_version` defines the target TFM. When the installed SDK is
older than the requested version, every generated `.csproj` with
`<TargetFramework>net{N}.0` will fail immediately on `dotnet build`:

```
error NETSDK1045: The current .NET SDK does not support targeting .NET 10.0.
```

Again, this is only caught at build time. A pre-generation SDK version check
(`dotnet --version`) eliminates the entire class of failure.

### Current state — partial implementation with structural corruption
G10 and G11 were added to the file informally (outside the SpecKit workflow).
The current file has **structural corruption**:
- A first copy of the G11 block was inserted in the middle of G10's code fence,
  interrupting the XML comment and the C# using-alias example.
- G11 then appears a second time at the correct position.
- The G10 XML comment is truncated mid-sentence inside the first code fence.

Result: the file has duplicate G11 content and a malformed G10 closing block.
This spec governs the authoritative clean implementation.

---

## 3. Frontmatter Change

Only `version` changes. All other frontmatter fields are unchanged.

```yaml
# BEFORE
version: "1.0.0"

# AFTER
version: "1.1.0"
```

---

## 4. Output Contract

No change to the output contract. The agent writes to:

```yaml
outputs:
  source_code: "projects/{project_name}/outputs/tobe/source-code/{module}/"
```

G10 and G11 are **pre-generation gates** — they block output, they do not
produce additional output files.

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — G10 nominal: single BC, no conflict (Priority: P2)

**Story**: Dado um projeto com um único BC gerado, quando o agente executa G10,
então nenhum conflito é detectado e a geração prossegue normalmente.

**Acceptance Scenarios**:

1. **Given** a solution with a single BC (`Banking.Titles`) and no other `.csproj`
   files in scope, **When** G10 runs, **Then** `existing_namespaces` is populated
   with one entry and the agent proceeds to code generation.
2. **Given** the above, **Then** no `⛔ G10 VIOLATION` message is emitted.

---

### Scenario 2 — G10 blocking: two BCs with shared namespace prefix (Priority: P1)

**Story**: Dado dois BCs com prefixo de namespace compartilhado no mesmo host,
quando o agente executa G10, então a geração é bloqueada com mensagem clara.

**Acceptance Scenarios**:

1. **Given** two BCs `Banking.Titles` and `Banking.Payments` both present as
   `.csproj` files in the solution, **When** G10 scans root namespaces and detects
   that neither is a strict prefix of the other but they share the `Banking.*`
   prefix at type level, **Then** the agent emits `⛔ G10 VIOLATION` and halts.
2. **Given** the violation message is emitted, **Then** it lists the conflicting
   namespace, the path to the conflicting `.csproj`, the compiler error codes
   (CS0104/CS0234), and two remediation options (rename namespace OR separate host).
3. **Given** the user resolves the conflict (e.g., renames namespace), **When** the
   agent is re-invoked, **Then** it proceeds to generation without re-emitting G10.

---

### Scenario 3 — G11 blocking: installed SDK older than target TFM (Priority: P1)

**Story**: Dado um SDK instalado inferior à versão alvo, quando o agente executa G11,
então a geração é bloqueada com mensagem de bloqueio e link de instalação.

**Acceptance Scenarios**:

1. **Given** `tobe_stack.backend_version: "10.0"` in `project-config.yaml` and
   `dotnet --version` returns `8.0.404`, **When** G11 runs, **Then** the agent
   emits `⛔ G11 VIOLATION` and does **not** write any file.
2. **Given** the violation message, **Then** it shows the required version, the
   installed version, the NETSDK1045 root cause, a download URL, and a `global.json`
   canonical fix template.

---

### Scenario 4 — G11 passing: SDK >= target TFM (Priority: P2)

**Story**: Dado um SDK compatível com a versão alvo, quando o agente executa G11,
então o check é registrado como OK e a geração prossegue.

**Acceptance Scenarios**:

1. **Given** `tobe_stack.backend_version: "10.0"` and `dotnet --version` returns
   `10.0.100`, **When** G11 runs, **Then** the agent logs
   `SDK 10.0.100 ✅ compatível com alvo 10.0` and proceeds.
2. **Given** a newer-than-required SDK (e.g., `11.0.100` with target `10.0`),
   **Then** G11 also passes — `>=` comparison, not exact match.

---

### Scenario 5 — G10 + G11 in sequence: both gates pass (Priority: P1)

**Story**: Quando ambos os guardrails G10 e G11 passam, a geração prossegue
normalmente sem interrupção.

**Acceptance Scenarios**:

1. **Given** a compatible SDK and non-conflicting namespaces, **When** the agent
   runs through G11 → G10 (in that order, see §6 Execution Order), **Then** both
   checks pass, code is generated, and `dotnet build` exits with 0 errors.

---

## 6. G10 — Authoritative Specification

### Trigger
Execute **before generating any `.cs` file**, whenever the agent targets a host
solution that may already contain other BCs (i.e., always, unless the host
directory is empty and no `.csproj` files exist).

### Execution Order in Agent
G10 runs **after** G11. Rationale: if the SDK is incompatible (G11 hard-block),
scanning namespaces is wasteful. Sequence:

```
[Pipeline mode check] → [Docs research bundle check]
  → G11 (SDK version)
    → G10 (namespace scan)
      → code generation
```

### Procedure (authoritative)
```
1. GLOB: src/**/*.csproj  (ou outputs/tobe/source-code/**/*.csproj)
   → Para cada .csproj encontrado:
     a. LER o arquivo e extrair o valor de <RootNamespace> (se presente)
     b. SE <RootNamespace> ausente → inferir pelo nome da pasta pai do .csproj
   → Montar lista: existing_namespaces = [ "BC1.RootNs", "BC2.RootNs", ... ]

2. Determinar o namespace raiz do novo BC a ser gerado:
     new_namespace = "{CompanyName}.{BCName}"  (conforme tobe_architecture.md)

3. PARA CADA ns EM existing_namespaces:
     SE new_namespace.StartsWith(ns)
        OU ns.StartsWith(new_namespace)
        OU new_namespace.Split('.')[0] = ns.Split('.')[0]:
       → HARD STOP — emitir mensagem G10 e NÃO gerar nenhum arquivo
   Nota: a terceira condição detecta BCs sibling com mesmo segmento raiz (empresa),
   prevenindo CS0104 (ambiguous reference). As duas primeiras previnem CS0234
   (namespace-pai aninhado, ex: 'Banking' vs 'Banking.Titles').

4. SE nenhum conflito detectado:
   → registrar new_namespace em existing_namespaces (estado da sessão)
   → prosseguir com a geração
```

### Blocking message (emit literally)
```
⛔ G10 VIOLATION — Namespace Conflict Detected
  Novo BC:      {new_namespace}
  Conflito com: {conflicting_namespace}  ({path/to/conflicting.csproj})
  Motivo:       namespace-pai aninhado (um é prefixo do outro) → CS0234;
                prefixo raiz compartilhado (mesmo segmento raiz) → CS0104
                (ambiguous reference em arquivos que referenciem tipos de ambos os BCs).
  Ação requerida (escolha uma):
    A) Renomear o namespace raiz do novo BC:
         ex: "{CompanyName}.{BCName}.Core" em vez de "{CompanyName}.{BCName}"
    B) Mover o BC conflitante para um projeto host separado.
  Não retomar a geração até que o conflito seja resolvido.
```

### Canonical fix (include in agent body as documentation)
```xml
<!-- Banking.Titles.Domain.csproj -->
<RootNamespace>Banking.Titles</RootNamespace>

<!-- Banking.Payments.Domain.csproj — namespace diverge no segundo segmento -->
<RootNamespace>Banking.Payments</RootNamespace>

<!-- ✅ Tipos com mesmo nome simples agora são disambiguados pelo namespace completo:
     Banking.Titles.Domain.Result   vs   Banking.Payments.Domain.Result  -->
```

```csharp
// Em arquivos que precisam de ambos — usar alias para eliminar ambiguidade:
using TitlesResult   = Banking.Titles.Domain.Result;
using PaymentsResult = Banking.Payments.Domain.Result;
```

---

## 7. G11 — Authoritative Specification

### Trigger
Execute **before starting any code generation** — immediately after the docs
research bundle check and before G10.

### Procedure (authoritative)
```
1. READ projects/{project_name}/context/project-config.yaml
   → extrair tobe_stack.backend_version  (ex: "10.0" ou "net10.0")
   → normalizar para major.minor numérico: required_version = 10.0

2. Bash: dotnet --version
   → capturar saída  (ex: "10.0.100")
   → extrair major.minor: installed_version = 10.0

3. SE installed_version < required_version:
   → HARD BLOCK — emitir mensagem G11 e NÃO gerar nenhum arquivo

4. SE installed_version >= required_version:
   → registrar "SDK {installed_version} ✅ compatível com alvo {required_version}"
   → prosseguir com a geração
```

### Blocking message (emit literally)
```
⛔ G11 VIOLATION — SDK Version Incompatible
  Requerido (tobe_stack.backend_version): {required_version}
  Instalado  (dotnet --version):          {installed_version}
  Motivo:    SDK instalado não suporta <TargetFramework>net{required_version}.0 —
             todo dotnet build falhará com NETSDK1045.
  Ação requerida:
    1. Instalar .NET SDK >= {required_version}:
         https://dotnet.microsoft.com/download/dotnet/{required_major}
    2. Verificar com: dotnet --version
    3. Confirmar ao agente para retomar a geração.
  Nenhum arquivo será gerado até que a versão do SDK seja confirmada.
```

### Canonical fix (include in agent body as documentation)
```json
// global.json (raiz da solução) — garante que todos os desenvolvedores usem SDK compatível:
{
  "sdk": {
    "version": "10.0.100",
    "rollForward": "latestMinor"
  }
}
```
> `rollForward: "latestMinor"` aceita qualquer patch/minor superior;
> `"major"` seria permissivo demais e poderia mascarar incompatibilidades de TFM.

---

## 8. Implementation Plan — Waves

> The user requested an incremental, wave-based plan for approval before execution.
> Each wave is atomic and reversible independently.

### Wave 1 — Repair structural corruption (file cleanup only)
**Scope**: `coder-dotnet-backend.md`
**What**: The file currently has:
  - A first G11 block interspersed in the middle of G10's XML comment code fence
  - The G10 XML comment truncated mid-sentence
  - A second (correct) G11 block after G10's csharp alias example
  - Result: duplicate G11 + malformed G10 code block

**Action**: Replace the corrupted G10+G11 region (everything from `### G10` to end
of last G11 block) with the clean, authoritative versions specified in §6 and §7.

**Risk**: Low — pure text replacement, no logic changes.
**Validation**: Read the file and confirm single G10 + single G11, no duplication,
no truncated lines.

---

### Wave 2 — Verify G10 completeness and ordering
**Scope**: `coder-dotnet-backend.md`
**What**: Confirm that G10 in the file after Wave 1 matches the authoritative
spec in §6 exactly:
  - Trigger: "before generating any .cs file"
  - Procedure: 4-step GLOB → extract → compare → stop/proceed
  - Blocking message: literal ⛔ G10 VIOLATION block
  - Canonical fix: XML + C# alias examples

**Action**: Edit if any deviation from §6 is found.
**Risk**: Low.
**Validation**: Side-by-side text comparison.

---

### Wave 3 — Verify G11 completeness and ordering
**Scope**: `coder-dotnet-backend.md`
**What**: Confirm that G11 in the file after Wave 1 matches the authoritative
spec in §7 exactly:
  - Trigger: "before starting any code generation"
  - Procedure: 4-step READ → dotnet --version → compare → block/proceed
  - Blocking message: literal ⛔ G11 VIOLATION block with download URL
  - Canonical fix: global.json with `rollForward: "latestMinor"`

**Action**: Edit if any deviation from §7 is found.
**Risk**: Low.
**Validation**: Side-by-side text comparison.

---

### Wave 4 — Integrate G10/G11 into execution flow reference
**Scope**: `coder-dotnet-backend.md`
**What**: The "Docs Research Bundle" section currently ends with:
  `→ PROSSEGUIR com guardrails G1-G9 existentes (non-blocking)`

This reference is now stale. It must be updated to reference G1-G11.

Additionally, the header section of `## ⚠️ GUARDRAILS` should note that
G10 and G11 are **pre-generation blocking gates**, whereas G1-G9 are
**generation-time guards** — to help readers understand the execution model.

**Action**: 
  1. Update `G1-G9 existentes` → `G1-G11 (G10-G11: pre-geração bloqueantes; G1-G9: durante geração)`
  2. Add one-line note to `## ⚠️ GUARDRAILS` header distinguishing the two categories.

**Risk**: Very low — cosmetic/reference updates.
**Validation**: Read updated section and confirm no broken cross-references.

---

### Wave 5 — Version bump + final validation
**Scope**: `coder-dotnet-backend.md` frontmatter
**What**: Bump `version: "1.0.0"` → `version: "1.1.0"`.
**Action**: Edit frontmatter.
**Risk**: Negligible.
**Validation**:
  1. Confirm single G10 + single G11 blocks, no duplication.
  2. Confirm correct version in frontmatter.
  3. Confirm no truncated code fences.
  4. Confirm runtime execution order G11 (SDK check) → G10 (namespace scan) is stated
     in the `## Input Adicional` section; file layout G10-then-G11 is the correct and
     intended order (consistent with existing structure — do NOT reorder in file).

---

## 9. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern — existing, unchanged
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` — existing, unchanged except version
- [x] Agent registered in module-level `module.yaml` — existing entry, no change needed
- [x] Output paths unchanged — G10/G11 are gates, not producers
- [ ] BDD scenarios cover nominal, edge, and gate paths — **covered in §5 (5 scenarios)**
- [ ] No structural corruption in file — **target of Wave 1**
- [ ] Runtime execution order G11→G10 stated in `## Input Adicional` section; file layout G10-then-G11 confirmed — **verified in Wave 5**
- [ ] `PROSSEGUIR com guardrails G1-G9` reference updated to G1-G11 — **Wave 4**
- [ ] Version bumped to 1.1.0 — **Wave 5**
- [ ] No `[NEEDS CLARIFICATION]` markers — **none in this spec**

---

## 10. Dependencies

| Dependency | Reason |
|------------|--------|
| `ava-stack-docs-researcher` (Step 1.5) | Produces docs-research-bundle that this agent reads before G11. Bundle check precedes G11 check. |
| `project-config.yaml` | G11 reads `tobe_stack.backend_version` from it. |
| `dotnet` CLI | G11 calls `dotnet --version` via Bash. |

---

## 11. Exclusions

- **G12+ guardrails** — out of scope for this spec.
- **Other agents** — only `coder-dotnet-backend.md` is modified.
- **`ava-stack-build-validator`** — separate agent; G10/G11 are pre-generation gates inside the coder agent, not post-generation validators.
- **`docs-research-bundle`** — no change to research bundle format or content.

---

## 12. Assumptions

- `project-config.yaml` always contains `tobe_stack.backend_version` when this agent runs (enforced by Pre-Flight check in orchestrator).
- `dotnet` CLI is available in the execution environment (Bash tool accessible).
- A `.csproj` with `<RootNamespace>` absent uses the folder name as its implicit namespace (standard MSBuild convention).
- The user accepts that G10/G11 are **HARD STOP** gates — they do not warn and continue; they fully halt code generation.

---

## Success Criteria

| Criterion | Measure |
|-----------|---------|
| File structure repaired | Single G10 + single G11 block in file; zero duplication; no truncated code fences |
| G10 blocking verified | Manual trace of procedure matches §6 spec exactly |
| G11 blocking verified | Manual trace of procedure matches §7 spec exactly |
| Execution order correct | Runtime sequence G11→G10 stated in `## Input Adicional` section; file layout G10-then-G11 confirmed |
| Flow reference updated | `G1-G9` reference replaced with `G1-G11` with category note |
| Version bumped | Frontmatter shows `version: "1.1.0"` |
| Zero dotnet build errors | Post-deploy acceptance criterion — not executable during prompt-file editing; proxy coverage via tasks 2.2 + 6.1 (G10 manual trace with corrected algorithm) |
