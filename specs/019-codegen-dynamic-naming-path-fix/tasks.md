# Agent Development Tasks: Codegen Dynamic Naming, Output Path & Broken-Dependency Fixes

**Plan**: `specs/019-codegen-dynamic-naming-path-fix/plan.md`
**Status**: Implementation complete; verification passed.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm `coder-dotnet-backend.md` frontmatter version (`2.0.0`)
- [x] **1.2** Confirm `coder-java-backend.md` frontmatter version (`2.0.0`)
- [x] **1.3** Confirm `coder-go-backend.md` frontmatter version (`2.0.0`)
- [x] **1.4** Confirm `coder-python-backend.md` frontmatter version (`2.0.0`)
- [x] **1.5** Confirm `coder-angular-frontend.md` frontmatter version (`1.1.0`), single `version:` key
- [x] **1.6** Confirm `containerize-agent.md` frontmatter version (`1.0.1`)
- [x] **1.7** Confirm `tech-stack/module.yaml` version (`1.3.1`)

## Category 2 — Implementation

- [x] **2.1** `shared/backend-context-protocol.md`: widen "Referenciado por" scope — DONE
- [x] **2.2** `coder-dotnet-backend.md`: new Step 0 (solution_prefix resolution) — DONE
- [x] **2.3** `coder-dotnet-backend.md`: new Execution Steps section (.sln, Directory.Packages.props, src/Shared, src/{BC}, src/Api, tests) — DONE
- [x] **2.4** `coder-dotnet-backend.md`: Output Contract → `source-code/backend/` (+ Security Gate inspection path + observer version) — DONE
- [x] **2.5** `coder-dotnet-backend.md`: deduplicate G11 (repaired truncated G10 XML comment) — DONE
- [x] **2.6** `coder-java-backend.md`: Output Contract → `source-code/backend/{module}/` (+ Security Gate path + observer version) — DONE
- [x] **2.7** `coder-go-backend.md`: Output Contract → `source-code/backend/{bc}/` (+ entity read path, Security Gate path, observer version) — DONE
- [x] **2.8** `coder-python-backend.md`: Output Contract → `source-code/backend/{module}/` (+ Security Gate path + observer version) — DONE
- [x] **2.9** `dotnet-scaffold-manifest.yaml`: all hardcoded `MeuERP` paths (incl. 2 non-blocking test entries) → glob patterns; version `1.0.0` → `1.0.1` — DONE
- [x] **2.10** `coder-angular-frontend.md`: replace `ConfigStackDotNet.yaml` read with `project-config.yaml` fields (3 sites: Step 1.2, Input Contract table, variable-derivation table) — DONE
- [x] **2.11** `coder-angular-frontend.md`: collapse duplicate `version:`/`date:` frontmatter keys — DONE
- [x] **2.12** `containerize-agent.md`: `MeuERP.sln` hardcode → `{prefix}.sln` (matches the variable already used everywhere else in the same template) — DONE
- [x] **2.13** `containerize-agent.md`: correct false "Step 7b" self-description → real `master-orchestrator.md` F6 wiring; also corrected stale "F7 DevOps" → "F6 DevOps" label — DONE
- [x] **2.14** `tech-stack/module.yaml`: corrected stub statuses for java/python/go; registered 3 missing cross-cutting agents; corrected `ava-coder-*` ids to match actual agent frontmatter `name:` (`ava-stack-dotnet-backend`, `ava-stack-angular-frontend`) — DONE

## Category 3 — Schema Updates — SKIP

No new JSON/YAML artifact schema introduced; reuses existing manifest/Output Contract shapes
with corrected paths only.

## Category 4 — Module Registration

- [x] **4.1** `tech-stack/module.yaml` version `1.3.0` → `1.3.1` (PATCH) — DONE

## Category 5 — Quality Gate Checklists

- [x] **5.1** `grep -n "MeuERP"` in `dotnet-scaffold-manifest.yaml` → 1 match, inside a comment explaining the fix (verified)
- [x] **5.2** `grep -l "source-code/backend/"` → present in all 4 backend coder files (verified)
- [x] **5.3** `grep -n "ConfigStackDotNet"` in `coder-angular-frontend.md` → 0 matches (verified)
- [x] **5.4** `grep -n "solution_prefix"` in `coder-dotnet-backend.md` → present, in Step 0 and Execution Steps (verified)
- [x] **5.5** `grep -n "MeuERP.sln"` in `containerize-agent.md` → 0 matches (verified)
- [x] **5.6** `grep -c "^### G11"` in `coder-dotnet-backend.md` → exactly 1 (verified)
- [x] **5.7** (added) `grep -n "status: stub"` in `tech-stack/module.yaml` → only node-backend/react/blazor/vue-frontend remain (the genuine stubs) (verified)

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — non-"MeuERP" project name no longer blocks scaffold verification (manifest now glob-based against any `{SolutionPrefix}`)
- [x] **6.2** CA02 — backend Output Contract now roots under `source-code/backend/` in all 4 backend coders
- [x] **6.3** CA03 — Angular frontend Step 1.2 no longer reads a nonexistent file; reads `project-config.yaml` directly with fallback defaults
- [x] **6.4** CA04 — `module.yaml` no longer contradicts `orchestrator-stack.md`'s routing table or `stub-registry.yaml`

## Category 7 — Documentation

- [x] **7.1** This spec-kit documentation (spec.md, plan.md, tasks.md) — DONE

## Completion Checklist

- [x] Root cause identified via direct file reads (not delegated) — confirmed `solution_prefix`
  rule exists but was never wired into generic-mode coders
- [x] `specs/007-dotnet-compile-guardrails`'s unmerged G11 dedup completed here
- [x] No new scripts/schemas introduced — glob-only manifest fix chosen over CLI-arg approach
- [x] `master-orchestrator.md` F6 wiring verified real — `containerize-agent.md`'s self-description corrected to match, no new orchestrator step added
- [x] Dual codegen invocation path (`orchestrator-tobe.md` vs `ava-stack-orchestrator`) explicitly excluded, not silently ignored (see spec §8)
