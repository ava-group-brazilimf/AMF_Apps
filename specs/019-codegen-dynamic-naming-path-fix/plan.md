# Agent Implementation Plan: Codegen Dynamic Naming, Output Path & Broken-Dependency Fixes

**Spec**: `specs/019-codegen-dynamic-naming-path-fix/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (7 agent/data files, no new agents) |
| **Primary Requirement** | `coder-dotnet-backend.md` (generic pipeline mode) never wires the already-documented `solution_prefix` derivation rule, causing a chain of failures: hardcoded manifest paths, an Output Contract that never writes under `source-code/backend/`, and no Execution Steps procedure at all. `coder-angular-frontend.md` separately hard-depends on a config file that does not exist anywhere in the repo, with no fallback — frontend codegen fails unconditionally today. |
| **Technical Approach** | Wire the existing `backend-context-protocol.md` naming rule into the 4 generic-mode backend coders; correct their Output Contract paths to match what `verify_scaffold.py`/`build-validator` already expect; replace the dead Angular config read with the equivalent fields already present in `project-config.yaml`; fix 2 hardcode instances (manifest, containerize) via glob/dynamic-detection instead of new script arguments (smallest blast radius); correct stale metadata (`module.yaml`, duplicate G11). |
| **Implementation Status** | Complete. Structural greps below. |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded introduced.
- [x] **Article II** — frontmatter unchanged except `version`/`date`/`description`; Angular's pre-existing duplicate `version:` key collapsed to one.
- [x] **Article IV** — `tech-stack/module.yaml` diff included (§3.7 of spec).
- [x] **Article VI** — BDD scenarios cover all 4 confirmed-broken paths.
- [x] **Article IX** — Clean Architecture layer order unaffected (path root changes, not layer semantics).
- [x] **Article X (SemVer)** — MAJOR for the 4 backend coders (Output Contract changes), MINOR for Angular, PATCH for containerize/module.yaml/manifest.
- [x] No `[NEEDS CLARIFICATION]` markers in the fixed scope — the one open question (dual codegen path) is an explicit Exclusion, not left ambiguous.

## Technical Context

Pure Markdown/prompt edits to 5 agent files + 1 YAML data manifest + 1 module registry. No
executable code changes (`verify_scaffold.py`/`build_runner.py` deliberately untouched — the
glob-pattern fix in the manifest achieves the same outcome without expanding the script's
surface area).

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
Direct reads confirmed: (a) `coder-dotnet-backend.md` frontmatter is still `1.0.0`, not the
`1.1.0` that `specs/007` intended — that spec's G10/G11 cleanup was never merged, duplication
confirmed still present at lines ~270/338; (b) `Glob **/ConfigStackDotNet.yaml` → 0 results,
confirming the Angular dead-dependency claim; (c) `master-orchestrator.md` line ~127 confirms
`ava-devops-containerize` IS correctly wired at F6 (`bloqueante sequencial`, trigger `FP`) — so
`containerize-agent.md`'s own "Step 7b" claim is simply false text, not a missing integration to
build; (d) `dotnet-scaffold-manifest.yaml` header explicitly promises `{SolutionPrefix}`
resolution that never happens in `verify_scaffold.py` (pure literal/glob matching, zero
substitution logic).

### Phase 1 — Naming Foundation (spec §3.1, §3.2 Step 0) ✅ CONCLUÍDO
Widened `backend-context-protocol.md`'s declared scope; added Step 0 to
`coder-dotnet-backend.md` resolving `project_name` → `solution_prefix`.

### Phase 2 — Output Path + Manifest + Execution Steps (spec §3.2-§3.4) ✅ CONCLUÍDO
Corrected Output Contract in all 4 generic backend coders to root under `source-code/backend/`;
added the missing Execution Steps section to `coder-dotnet-backend.md`; replaced the 3 hardcoded
manifest paths with glob patterns; deduplicated G11.

### Phase 3 — Angular Dead Dependency (spec §3.5) ✅ CONCLUÍDO
Replaced the `ConfigStackDotNet.yaml` read with `project-config.yaml`'s own `tobe_stack.frontend_version`/`auth.provider` fields, matching the fallback style of the step's other reads; collapsed the duplicate frontmatter `version:` key.

### Phase 4 — Containerize + Module Registry (spec §3.6-§3.7) ✅ CONCLUÍDO
Fixed the `MeuERP.sln` hardcode via dynamic `.sln` detection; corrected the false "Step 7b"
self-description to point at the real `master-orchestrator.md` F6 wiring; corrected
`tech-stack/module.yaml` stub statuses and registered the 3 missing cross-cutting agents.

### Phase 5 — Verification (this session) ✅ CONCLUÍDO
Structural greps confirming all hardcoded strings removed, new patterns present, and version
numbers consistent — see Test Strategy below.

## Complexity Tracking

| Item | Status |
|---|---|
| Two candidate fixes for the manifest hardcode (glob-in-manifest vs. new `--solution-prefix` CLI arg to `verify_scaffold.py`) | Chose glob-in-manifest — zero changes to `verify_scaffold.py` or the orchestrator's Step 5.5 invocation, smaller blast radius for equivalent outcome |
| `containerize-agent.md`'s false "Step 7b" claim could have been "fixed" by adding a real Step 7b to `orchestrator-stack.md` instead | Rejected — would duplicate F6 responsibility inside F4, violating Article III's phase separation; the real wiring already exists correctly at `master-orchestrator.md` F6, only the agent's own prose was wrong |
| Scope creep risk: retrofitting a `version:` field onto `backend-context-protocol.md` | Explicitly declined (see spec §9 Assumptions) — unrelated to the reported defects |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| Manifest hardcode removed | `grep -n "MeuERP" dotnet-scaffold-manifest.yaml` | 0 matches outside comments |
| Backend Output Contracts corrected | `grep -n "source-code/backend/"` in each of the 4 backend coder files | Present |
| `solution_prefix` wired | `grep -n "solution_prefix"` in `coder-dotnet-backend.md` | Present, in a new Step 0 |
| Angular dead file removed | `grep -n "ConfigStackDotNet"` in `coder-angular-frontend.md` | 0 matches |
| Angular reads project-config directly | `grep -n "tobe_stack.frontend_version"` in `coder-angular-frontend.md` | Present |
| Containerize hardcode removed | `grep -n "MeuERP.sln"` in `containerize-agent.md` | 0 matches |
| Containerize self-description corrected | `grep -n "Step 7b"` in `containerize-agent.md` | 0 matches |
| G11 deduplicated | `grep -c "### G11 — SDK Version Validation"` in `coder-dotnet-backend.md` | Exactly 1 |
| `module.yaml` stub statuses corrected | `grep -n "status: stub"` in `tech-stack/module.yaml` | Only node/react/blazor/vue frontend/backend stubs remain |
| Frontmatter versions consistent | Per spec §1 table | All match |
