# Agent Specification: Codegen Dynamic Naming, Output Path & Broken-Dependency Fixes (F4 Tech-Stack)

**Feature Branch**: `019-codegen-dynamic-naming-path-fix`
**Created**: 2026-07-15
**Status**: Implemented
**Change Type**: modify-existing (7 files across `tech-stack`, `shared`, `devops-agents` modules — MAJOR on 4 coder agents, MINOR/PATCH on the rest)
**Input**: "Corrija o problema de hardcoded para um projeto especifico — Corrija os demais pontos de
riscos apontados no documento `docs/analise-codegen-travado-tech-stack.md` — Siga as correções
propostas no arquivo. Requisitos funcionais: o nome do projeto TO-BE deve ser dinâmico a partir de
`project_name`; a estrutura final deve ser `{project_name}/frontend` e `{project_name}/backend`
com Dockerfile na raiz de cada um; os agentes de codificação devem levar em conta a arquitetura
TO-BE e os configs injetados em `project-config.yaml`."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-stack-dotnet-backend` | `tech-stack/agents/coder-dotnet-backend.md` | `1.0.0` → `2.0.0` (MAJOR — Output Contract path changes) |
| `ava-stack-java-backend` | `tech-stack/agents/coder-java-backend.md` | `1.1.0` → `2.0.0` (MAJOR — Output Contract path changes) |
| `ava-stack-go-backend` | `tech-stack/agents/coder-go-backend.md` | `1.0.0` → `2.0.0` (MAJOR — Output Contract path changes) |
| `ava-stack-python-backend` | `tech-stack/agents/coder-python-backend.md` | `1.1.0` → `2.0.0` (MAJOR — Output Contract path changes) |
| `ava-stack-angular-frontend` | `tech-stack/agents/coder-angular-frontend.md` | `1.0.0` → `1.1.0` (MINOR — new input source, dead dependency removed) |
| `ava-devops-containerize` | `devops-agents/agents/containerize-agent.md` | `1.0.0` → `1.0.1` (PATCH — hardcode + self-description fix) |
| `ava-backend-context-protocol` (shared, non-dispatchable) | `shared/backend-context-protocol.md` | no version field (predates versioning convention — scope note widened only, see §9) |

**Phase**: F4. **Module**: `tech-stack` (+ `devops-agents` for containerize). **Data files also
touched** (not agents, no SemVer contract): `src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml`,
`src/modules/ava-fabric-agents/tech-stack/module.yaml` (module registry, version `1.3.0` → `1.3.1` PATCH).

---

## 2. Problem Statement

`docs/analise-codegen-travado-tech-stack.md` (written earlier in this workstream) traced why the
F4 codegen pipeline (`ava-stack-orchestrator`) fails to produce compiling code once dispatched: the
`.NET` scaffold manifest hardcodes the literal project name `MeuERP` in its blocking
file-existence checks. Two further rounds of direct file verification found that bug is only the
most visible symptom of a chain of related defects, all traced to the same root cause — the
canonical `solution_prefix` derivation rule (documented in `shared/backend-context-protocol.md`:
PascalCase of `project_name`, no spaces/hyphens) was **never wired into the generic-mode coder
agents** (`coder-dotnet-backend.md` and siblings) that Meu-ERP-style projects
(`pipeline_mode: "generic"`) actually use — the rule exists, but its own file header scopes it to
`build-cycle-*` agents only.

Confirmed defects (file:line references, all verified by direct read before this spec):

1. **Hardcoded prefix** — `dotnet-scaffold-manifest.yaml` lines 36/67/85 hardcode `MeuERP` in
   `blocking: true` paths. Breaks Step 5.5 (`verify_scaffold.py`) for any project not literally
   named "MeuERP".
2. **Output Contract path mismatch (more severe than #1)** — `coder-dotnet-backend.md`'s Output
   Contract (lines 417-424) declares `source_code: ".../source-code/{module}/"` where `{module}`
   resolves to a bounded-context name (per Guardrail G2), never `backend`. `verify_scaffold.py`
   is invoked against `.../source-code/backend/` (orchestrator Step 5.5) — a root that never gets
   created. Same defect in `coder-java-backend.md`, `coder-go-backend.md`,
   `coder-python-backend.md`. `coder-angular-frontend.md` is the one coder that already writes to
   the correct `.../source-code/frontend/` root.
3. **Missing Execution Steps** — `coder-dotnet-backend.md` has no step-by-step generation
   procedure (unlike Angular's 3135-line Step 1→2.17), jumping from guardrails straight to a
   6-line generic template — the agent has no deterministic instruction for `.sln`/
   `Directory.Packages.props`/project naming.
4. **Dead dependency, no fallback (most severe — unconditional break)** — `coder-angular-frontend.md`
   Step 1.2 (~line 326) hard-reads `docs/architecture/ConfigStackDotNet.yaml`, a file that does not
   exist anywhere in the repository (confirmed via `Glob`) — a leftover reference to a config
   convention superseded by inlining `tobe_stack.*`/`auth.*` directly into `project-config.yaml`.
   Unlike the other two reads in the same step, this one has no `SE ausente:` fallback — Angular
   frontend codegen is broken today for every project, independent of naming.
5. **`containerize-agent.md` self-description is false** — claims to be "Automatically invoked by
   `ava-stack-orchestrator` Step 7b"; no such step exists in `orchestrator-stack.md`. The real,
   correct wiring already exists in `master-orchestrator.md` (F6, blocking, `FP` trigger). Also
   hardcodes `COPY ["MeuERP.sln", ...]` (line ~135) — same defect class as #1.
6. **`module.yaml` (tech-stack) stale metadata** — marks `java/python/go` backend coders
   `status: stub`, contradicting `orchestrator-stack.md`'s own routing table and
   `stub-registry.yaml` (`status: COMPLETE`).
7. **Duplicate guardrail** — `coder-dotnet-backend.md` has two `### G11 — SDK Version Validation`
   headers (lines ~270, ~338). `specs/007-dotnet-compile-guardrails` targeted this exact
   corruption but was never actually applied (frontmatter still reads `1.0.0`, not the `1.1.0`
   that spec intended).

---

## 3. Decision

### 3.1 `shared/backend-context-protocol.md`
Widen the declared scope ("Referenciado por: ...") to include the generic-mode backend coders
(`coder-dotnet-backend`, `coder-java-backend`, `coder-go-backend`, `coder-python-backend`), not
only the `build-cycle-*` agents. The `solution_prefix` derivation rule becomes the single source
of truth for both `pipeline_mode` values.

### 3.2 `coder-dotnet-backend.md`
- New **Step 0 — Resolução de Contexto**: read `project_name`, derive `solution_prefix` per
  §3.1, before any generation.
- New **Execution Steps** section: deterministic procedure for `.sln`, `Directory.Packages.props`,
  `Directory.Build.props`, `src/Shared/`, `src/{BC}/`, `src/Api/`, all named with
  `{solution_prefix}` — aligned 1:1 with the corrected manifest (§3.4).
- **Output Contract fix**: `source_code` → `.../source-code/backend/{module}/` (adds the missing
  `backend/` root).
- Deduplicate `G11` (single canonical block, completing `specs/007`'s original intent).

### 3.3 `coder-java-backend.md` / `coder-go-backend.md` / `coder-python-backend.md`
Same Output Contract root fix as §3.2 (`.../source-code/backend/{module|bc}/`).

### 3.4 `src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml`
Replace the 3 hardcoded `MeuERP` blocking paths with generic glob patterns
(`src/Shared/*.Shared.Domain/*.Shared.Domain.csproj`, etc.) — `verify_scaffold.py` already
supports `glob: true`; **no change to `verify_scaffold.py` or the orchestrator's Step 5.5 call**
(smallest blast-radius option; a `--solution-prefix` CLI argument was considered and rejected —
it would require touching 3 files for the same outcome).

### 3.5 `coder-angular-frontend.md`
Replace the dead `ConfigStackDotNet.yaml` read with a direct read of
`projects/{project_name}/context/project-config.yaml` → `tobe_stack.frontend_version` and
`auth.provider` (both already present there), using the same `SE ausente:` fallback pattern as
the step's other two reads. Also fix the duplicate `version:` key in frontmatter (lines 3 and 12
both declare a version — Article II allows exactly one).

### 3.6 `devops-agents/agents/containerize-agent.md`
- Replace `COPY ["MeuERP.sln", ...]` with dynamic `.sln` detection (mirrors the correct pattern
  already used in `qa-agents/agents/db-integrity-test-agent.md` line ~295).
- Correct the self-description: invoked by `master-orchestrator.md` F6 (real, confirmed wiring),
  not by a nonexistent `ava-stack-orchestrator` Step 7b.
- **Decision, not a defect**: `ava-stack-orchestrator trigger: SG` run standalone will continue
  to not produce a Dockerfile — that is expected, by design (Article III phase separation between
  F4 codegen and F6 DevOps). Documented as an Assumption (§9), not fixed here.

### 3.7 `src/modules/ava-fabric-agents/tech-stack/module.yaml`
Correct `status: stub` → remove/`COMPLETE` for java/python/go backend coders; add the 3 missing
cross-cutting entries (`ava-stack-docs-researcher`, `ava-stack-build-validator`,
`ava-stack-build-fixer`).

---

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `shared/backend-context-protocol.md` | Scope widened to generic-mode coders |
| `coder-dotnet-backend.md` | Step 0 (solution_prefix) + Execution Steps + Output Contract path fix + G11 dedup |
| `coder-java-backend.md` | Output Contract path fix |
| `coder-go-backend.md` | Output Contract path fix |
| `coder-python-backend.md` | Output Contract path fix |
| `coder-angular-frontend.md` | Dead-file read replaced with `project-config.yaml` read; duplicate frontmatter key fixed |
| `dotnet-scaffold-manifest.yaml` | 3 hardcoded paths → glob patterns |
| `devops-agents/agents/containerize-agent.md` | Hardcoded `.sln` name → dynamic detection; false self-description corrected |
| `tech-stack/module.yaml` | Stub status corrected; 3 missing agents registered |

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Non-"MeuERP" project name no longer blocks scaffold verification (CA01)
**Given** a project named `Meu-ERP-001-AST-AS-IS-Orchestrator` (`solution_prefix` derives to
`MeuERP001ASTASISOrchestrator`), **When** `ava-stack-dotnet-backend` generates the backend and
Step 5.5 runs `verify_scaffold.py --manifest dotnet --root .../source-code/backend`, **Then** the
glob-based blocking checks match the generated `{solution_prefix}.Shared.Domain.csproj` etc.
regardless of the literal prefix, and Step 5.5 returns `PASS`.

### Scenario 2 — Backend actually writes under `source-code/backend/` (CA02)
**Given** the corrected Output Contract, **When** `ava-stack-dotnet-backend` completes generation,
**Then** `projects/{project_name}/outputs/tobe/source-code/backend/` exists and contains the
`.sln` and per-BC project folders — the root `verify_scaffold.py` checks actually exists.

### Scenario 3 — Angular frontend generation no longer hard-fails on a missing file (CA03)
**Given** no `docs/architecture/ConfigStackDotNet.yaml` exists anywhere (true today and after this
fix), **When** `ava-stack-angular-frontend` runs Step 1.2, **Then** `frontend_version` and
`auth.provider` are read from `project-config.yaml` directly and generation proceeds without a
missing-file error.

### Scenario 4 — `module.yaml` no longer contradicts the orchestrator (CA04)
**Given** `tobe_stack.backend_framework: "spring-boot"`, **When** any tooling reads
`tech-stack/module.yaml` to check readiness, **Then** it reports the java backend coder as
implemented, consistent with `orchestrator-stack.md`'s own routing table.

---

## 6. Quality Gate Requirements

- [x] Agent IDs unchanged for all 5 touched coder agents (Article II)
- [x] Frontmatter unchanged except `version`/`date`/`description` (Article II)
- [x] MAJOR bump on the 4 backend coders (Output Contract/path changes — Article X); MINOR on
  Angular (new input source, no removal); PATCH on `containerize-agent.md` and `module.yaml`
- [x] No technology versions hardcoded introduced by this spec (Article I)
- [x] BDD scenarios cover the 4 confirmed-broken paths (CA01-CA04) (Article VI)
- [x] No `[NEEDS CLARIFICATION]` markers remain in the fixed scope — the one open architectural
  question (dual codegen invocation path, `orchestrator-tobe.md` Fase 4.7 vs.
  `ava-stack-orchestrator`) is explicitly out of scope, see §8

---

## 7. Dependencies

- `docs/analise-codegen-travado-tech-stack.md` — source analysis this spec formalizes and fixes.
- `docs/tech-stack-io-map.md` — per-agent input/output map used to cross-check the Output
  Contract path claims in §3.2/3.3.
- `specs/007-dotnet-compile-guardrails` — the G10/G11 dedup (§3.2) completes this prior spec's
  unmerged intent; no conflict, this spec supersedes it for that one guardrail pair.
- `specs/019` is itself a dependency of `specs/020` and `specs/021` — both touch the same coder
  agents' Execution Steps sections added here.

---

## 8. Exclusions

- **Dual codegen invocation path** (`orchestrator-tobe.md` Fase 4.7 dispatching
  `tobe-architecture/agents/coder-dotnet.md` directly, bypassing `ava-stack-build-validator`,
  versus `ava-stack-orchestrator` dispatching `coder-dotnet-backend.md` with the full reliability
  pipeline) — **not resolved here**. This is a team architecture decision (which path is
  production-authoritative), not a mechanical bug fix. Flagged as `[NEEDS CLARIFICATION]` for a
  future spec.
- **`orchestrator-stack.md` Steps 4 and 6** (OpenAPI contract generation/validation) — left as-is
  in this spec; addressed in `specs/021`.
- **Business rules consumption** — left as-is in this spec; addressed in `specs/020`.
- **`coder-node-backend.md`, `coder-react-frontend.md`, `coder-blazor-frontend.md`,
  `coder-vue-frontend.md`** (genuine stubs) — out of scope; no functional code to fix.
- **`verify_scaffold.py` / `build_runner.py`** — no changes; the glob-only manifest fix (§3.4)
  was deliberately chosen to avoid touching these scripts.

---

## 9. Assumptions

- `ava-stack-orchestrator trigger: SG` run standalone (not via `master-orchestrator FP`) will
  continue to not produce a Dockerfile — this is the existing, correct phase boundary (F4 vs F6),
  not a regression introduced or left by this spec.
- `shared/backend-context-protocol.md` has no `version:` field in its frontmatter today (it is an
  internal shared doc, not a dispatchable `ava-{phase}-{role}` agent) — this spec does not
  retrofit one, to avoid scope creep unrelated to the reported defects.
- The glob patterns chosen for §3.4 (`src/Shared/*.Shared.Domain/*.Shared.Domain.csproj`) are
  permissive enough to match any `{SolutionPrefix}` the coder derives per §3.1/§3.2, without
  requiring the manifest to know the prefix value itself.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Hardcoded `MeuERP` removed from blocking manifest paths | `grep -n "MeuERP" dotnet-scaffold-manifest.yaml` → 0 matches outside comments |
| Backend coders write under `source-code/backend/` | `grep -n "source-code/backend/" coder-{dotnet,java,go,python}-backend.md` → present in each Output Contract |
| Angular no longer reads the dead config file | `grep -n "ConfigStackDotNet"` in `coder-angular-frontend.md` → 0 matches |
| `solution_prefix` rule wired into generic coders | `grep -n "solution_prefix"` in `coder-dotnet-backend.md` → present |
| `containerize-agent.md` hardcode removed | `grep -n "MeuERP.sln"` → 0 matches |
| `containerize-agent.md` self-description corrected | `grep -n "Step 7b"` → 0 matches; `grep -n "master-orchestrator"` → present |
| G11 deduplicated | `grep -c "### G11 — SDK Version Validation"` in `coder-dotnet-backend.md` → exactly 1 |
| Versions bumped consistently | Per §1 table |
