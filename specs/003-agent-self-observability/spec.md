# Agent Specification: Agent Self-Observability

**Feature Branch**: `003-agent-self-observability`
**Created**: 2026-07-03
**Status**: Implemented

> ⚠️ **Update 2026-07-04**: this feature's rollout never actually fired —
> see `specs/004-observability-self-report-activation-fix/` for the first
> root-cause attempt (appendix-style placement) and
> `specs/005-observability-mandatory-phase/` for the final fix: the
> reference-doc indirection (`@observability-self-report`) itself was part
> of the problem, and a deeper environmental gap (no enforced tool-calling
> harness in this repo) was discovered. All 97 agent files were redone with
> a self-contained mandatory phase in specs/005.
**Change Type**: modify-existing (bulk, 97 agent files) + new shared governance doc + tool enhancement
**Input**: Agent description: "Observabilidade individual por agente — cada agente deve adicionar a sua especificação a chamada para a tool de observabilidade e gerar arquivos de observabilidade em outputs/observability/{agent_name}."

> **Language note**: This spec is a planning document written in **English**.
> The new shared instruction file (`observability-self-report.md`) and the
> single-line reference added to each agent body are in **Brazilian
> Portuguese** where prose, per Constitution Article V — mirroring the
> existing `@governance-apps` convention. Frontmatter is unchanged in 96 of
> the 97 files (see §9 Assumptions on why no per-file version bump was applied).

---

## Context: why this feature exists

`specs/002-agent-pipeline-observability/` documented that `pipeline_observer.py`
is fully built, but only `ava-master-orchestrator` calls it — and only for the
~21 agents it directly dispatches. That PBI's Scenario 7 (CA10) recorded, as a
known gap, that phase orchestrators and leaf agents (~35 of the 54-row
`AGENT_CATALOG`) have zero observability coverage, and that even
master-orchestrator's own calls are documented in an appendix rather than
inlined into its Execution Steps. It also noted that any agent invoked
**standalone** (not via master-orchestrator) produces no metrics at all.

This PBI closes that gap by inverting the model: instead of a caller
externally tracking agents it dispatches, **every agent tracks itself**,
using the exact same `pipeline_observer.py track` command, regardless of who
dispatched it or whether it was invoked standalone.

---

## 1. Agent Identity

This PBI touches **97 of the 101** agent `.md` files in
`src/modules/ava-fabric-agents/**/agents/`, plus one new shared governance
document and one utility script enhancement:

| Component | Type | Change |
|---|---|---|
| `src/modules/ava-fabric-agents/shared/observability-self-report.md` | **New** shared governance doc | Defines the self-reporting convention every agent applies (mirrors `@governance-apps`) |
| `src/shared/tools/pipeline_observer.py` | Existing utility script | `cmd_track` now also writes a per-agent snapshot to `outputs/observability/{agent_name}/` (see §4.1) |
| `src/shared/tools/README.md` | Documentation | Updated "Data Storage" section to document the new per-agent output |
| `ava-master-orchestrator` | Existing agent | Frontmatter `version: "1.1.0"` → `"1.3.0"` (closes the drift already found in PBI 002, plus this PBI's own change); body gets a dedicated "Agent Self-Reporting" note and a new Changelog row |
| **96 other agent `.md` files** (all modules: asis-diagnostic, tobe-architecture, tech-stack, qa-agents, deliverables, devops-agents, summary, prototype) | Existing agents | Each gets a one-line `> Apply: [@observability-self-report](...)` reference inserted — no frontmatter version bump (see §9) |

**Excluded (4 files)** — inlined, not independently dispatched, so "self"
tracking would be meaningless (they have no completion signal of their own):
`asis-diagnostic/agents/db-analyzer/skills/{mariadb,mysql,oracle,sqlserver}-agent.md`.
`db-analyzer.md` itself (the parent that selects one of these 4 skills at
runtime) **is** instrumented.

Full per-module counts (101 total agent files, 97 instrumented, 4 excluded):

| Module | Total agent files | Instrumented | Excluded |
|---|---:|---:|---:|
| `asis-diagnostic` (F1) | 29 | 25 | 4 (db-analyzer skills) |
| `tobe-architecture` (F2) | 22 | 22 | 0 |
| `tech-stack` (F3) | 13 | 13 | 0 |
| `qa-agents` (F5) | 10 | 10 | 0 |
| `devops-agents` (F7) | 13 | 13 | 0 |
| `deliverables` (F6) | 10 | 10 | 0 |
| `summary` (F8) | 2 | 2 | 0 |
| `prototype` | 1 | 1 | 0 |
| `master-orchestrator` | 1 | 1 | 0 |
| **Total** | **101** | **97** | **4** |

> No `module.yaml` registration is required — no new agents are created, only
> existing ones are extended with an additional instruction reference.

---

## 2. Agent Frontmatter Changes

### `ava-master-orchestrator` — version bump

```yaml
---
name: ava-master-orchestrator
version: "1.3.0"   # was "1.1.0" (stale — see specs/002/research.md); now correctly
                   # reflects both the pipeline_observer.py integration (should have
                   # been 1.2.0) and this PBI's self-reporting addition
date: 2026-06-12
description: |
  ...unchanged...
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---
```

### All other 96 agents — no frontmatter change

Applying a shared governance reference (the same mechanism already used for
`@governance-apps` across 79 files) is treated as a **documentation/governance
patch**, not a functional contract change to the agent's own `name`/
`description`/`allowed-tools`/inputs/outputs — consistent with how
`@governance-apps` was rolled out without per-file version bumps. See §9 for
the explicit reasoning and the counter-argument this spec does **not** adopt.

---

## 3. Output Contract

### New: per-agent self-report output (every instrumented agent)

```yaml
## Output Contract (additions — applies to all 97 instrumented agents)
outputs:
  self_report_metrics: "projects/{project_name}/outputs/observability/{agent_name}/metrics.json"
  self_report_events:  "projects/{project_name}/outputs/observability/{agent_name}/events.jsonl"
```

These are **not** added to each individual agent's own formal
`## Output Contract` YAML block (that would mean editing the same block 97
times with a per-agent-name path) — instead, they are declared once, centrally,
in `observability-self-report.md`, which every agent applies. This mirrors how
`@governance-apps` centrally declares i18n behavior rather than repeating it
in every agent's own contract.

### Unchanged: shared aggregate output (already existed per PBI 002)

```yaml
outputs:
  observability_state:  "projects/{project_name}/outputs/observability/pipeline-run-state.json"
  observability_events: "projects/{project_name}/outputs/observability/agent-events.jsonl"
```

`pipeline_observer.py track` writes **both** the shared aggregate state and
the new per-agent files in the same call — see §4.1.

---

## 4. Functional Changes by Component

### 4.1 `pipeline_observer.py` — `cmd_track` enhancement (implemented)

Added three new functions and one call site (verified by direct code read and
by running the tool end-to-end):

- `_sanitize_agent_name(agent_name)` — replaces any character that isn't
  alphanumeric/`-`/`_` with `-`, so agent names are always safe directory names.
- `_get_agent_dir(project_name, agent_name)` — resolves and creates
  `projects/{project_name}/outputs/observability/{sanitized_agent_name}/`.
- `_write_agent_metrics(project_name, agent_name, run_id, agent_data)` — writes
  `metrics.json` (a self-contained snapshot: `run_id` + `agent` + the same
  fields already tracked centrally — see `data-model.md`) and appends the same
  payload as one line to `events.jsonl` in the per-agent directory.
- `cmd_track` now calls `_write_agent_metrics(...)` immediately after saving
  the shared state, before appending to the shared event log.

This is **fully backward compatible**: existing callers of `track` (i.e.
`ava-master-orchestrator`'s own tracking of the agents it directly dispatches)
automatically get per-agent files too, with no change to their own call
syntax.

### 4.2 `observability-self-report.md` — new shared governance doc (implemented)

Located at `src/modules/ava-fabric-agents/shared/observability-self-report.md`,
styled after `governance-apps.md` (same header block: Version/Applies
to/Reference-as, an ABSOLUTE INVARIANT box, numbered sections). Content:

1. **§1 When to Self-Report** — call `pipeline_observer.py track` for
   yourself immediately before emitting your own completion signal, resolving
   `{project_name}`, `{seu_agent_id}`, `{sua_versao}` from your own frontmatter
   and a phase-lookup table keyed by `name:` prefix (`ava-asis-*`→F1,
   `ava-tobe-*`/`ava-prototype*`→F2, `ava-stack-*`→F3, `ava-qa-*`→F5,
   `ava-devops-*`→F7, `ava-deliverable-*`→F6, `ava-summary*`→F8).
2. **§2 Standalone Invocation Fallback** — if `track` errors with "No active
   run," call `init --run-type standalone` once, then retry `track` once.
   Never retry more than once.
3. **§3 Failure Isolation** — observability failures MUST NEVER block or fail
   the agent's own task; log a warning and continue.
4. **§4 Output** — documents both write targets (shared state + per-agent
   folder).

### 4.3 `ava-master-orchestrator.md` — self-reference + version fix (implemented)

Added an "Agent Self-Reporting" note (after the existing "Output Files" table,
before the Changelog) that applies `@observability-self-report`, explicitly
stating this is **independent of** the orchestrator's own pre-existing
`init`/`track`/`finalize` calls documented in PBI 002. Frontmatter version
corrected to `1.3.0`; a new Changelog row added.

### 4.4 96 other agent files — mechanical one-line insertion (implemented)

A batch script inserted, into each file:

```markdown
## Observability Self-Report

> Apply: [@observability-self-report](<relative-path-to-shared-file>)
```

**Insertion anchor, in priority order** (verified across all 96 files, zero
errors, zero broken relative-path references — see `quickstart.md` for the
verification command):
1. Immediately before `## i18n — Idioma dos Artefatos`, if present (this
   applied to the majority of files, since 79/101 files in the pre-existing
   catalog had this terminal section).
2. Immediately before `## Changelog`, if present and no i18n section exists.
3. Appended at the end of the file, if neither anchor exists.

Relative path depth was computed per file (e.g. `../../shared/...` for
`{module}/agents/*.md`, `../../../shared/...` for nested
`asis-diagnostic/agents/security/*.md` and `db-analyzer/db-analyzer.md`).

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Standalone Leaf-Agent Invocation Now Produces Metrics (CA01)

**Story**: Como QA que invoca `ava-qa-scenario-generator` diretamente (sem
passar pelo `ava-master-orchestrator`), quero que minhas métricas de execução
sejam registradas mesmo assim, para auditar custo/tempo de invocações avulsas.

**Acceptance Scenarios**:

1. **Given** no pipeline run has been `init`ed for the project, **When**
   `ava-qa-scenario-generator` completes and follows its applied
   `@observability-self-report` instructions, **Then** it calls `init
   --run-type standalone` followed by `track`, and
   `projects/{project}/outputs/observability/ava-qa-scenario-generator/metrics.json`
   is created.

### Scenario 2 — Nested Dispatch Chain Is Now Covered (CA02)

**Story**: Como auditor de segurança, quero que sub-agentes de segurança
despachados por `ava-asis-security-orchestrator` (que por sua vez é
despachado por `ava-asis-orchestrator`) também registrem suas próprias
métricas, mesmo que nenhum orchestrator na cadeia os rastreie externamente.

**Acceptance Scenarios**:

1. **Given** `ava-asis-sast` (one of the 8 security sub-agents) completes,
   **When** it applies `@observability-self-report`, **Then** its own
   `track` call fires regardless of whether `ava-asis-security-orchestrator`
   or `ava-asis-orchestrator` ever calls `pipeline_observer.py` themselves.

### Scenario 3 — Per-Agent Output Is Isolated From Other Agents (CA03)

**Story**: Como responsável por otimização, quero conseguir inspecionar
somente as execuções de um agente específico ao longo de várias rodadas, sem
precisar filtrar o estado agregado do pipeline inteiro.

**Acceptance Scenarios**:

1. **Given** two different agents are `track`ed within the same run,
   **When** both calls complete, **Then**
   `outputs/observability/{agent_a}/` contains only `agent_a`'s own
   `metrics.json`/`events.jsonl`, and `outputs/observability/{agent_b}/`
   contains only `agent_b`'s.

### Scenario 4 — Backward Compatibility With Existing Master-Orchestrator Tracking (CA04)

**Story**: Como mantenedor da PBI 002, quero que a integração existente do
`ava-master-orchestrator` continue funcionando sem alteração de sintaxe.

**Acceptance Scenarios**:

1. **Given** `ava-master-orchestrator` calls `track --agent
   ava-devops-ci ...` exactly as it did before this PBI, **When** the call
   completes, **Then** both the shared `pipeline-run-state.json` (existing
   behavior) AND the new `outputs/observability/ava-devops-ci/metrics.json`
   (new behavior) are written, with no change required to
   `master-orchestrator.md`'s own pre-existing integration syntax.

### Scenario 5 — Observability Failure Does Not Block the Agent's Task (CA05)

**Story**: Como qualquer agente da esteira, não quero que uma falha na tool
de observabilidade impeça a entrega do meu artefato principal.

**Acceptance Scenarios**:

1. **Given** `pipeline_observer.py` is unavailable or the `track` call errors
   for any reason, **When** the agent evaluates
   `@observability-self-report` §3, **Then** it logs a one-line warning and
   proceeds to emit its own completion signal — self-reporting failure is
   never a gate.

### Scenario 6 — Excluded Files Are Correctly Not Instrumented (CA06)

**Story**: Como mantenedor, quero que agentes inlined (não despachados
independentemente) não recebam uma instrução de self-report sem sentido.

**Acceptance Scenarios**:

1. **Given** `db-analyzer/skills/oracle-agent.md` (a skill inlined and
   selected by `db-analyzer.md`, not independently dispatched), **When** the
   repo is grepped for `observability-self-report`, **Then** none of the 4
   `db-analyzer/skills/*.md` files contain the reference, while
   `db-analyzer.md` itself does.

---

## 6. Quality Gate Requirements

- [x] Agent ID pattern unaffected — no agent `name:` fields were changed (Article II)
- [x] Frontmatter unaffected in 96/97 files; `ava-master-orchestrator`'s frontmatter still contains only the 4 allowed keys plus the pre-existing, out-of-scope `date` field (Article II)
- [ ] N/A — Module registration (Article IV): no new agents created
- [x] All new/changed output paths use lowercase `{project_name}` (Article II) — verified in §3
- [x] The new shared doc's body and every inserted one-line reference are in Portuguese; the reference syntax itself (`> Apply: [@x](path)`) is the pre-existing, established convention (Article V)
- [x] BDD scenarios cover nominal, nested-dispatch, isolation, backward-compatibility, failure-isolation, and exclusion-correctness paths (Article VI)
- [x] Security sub-pipeline impact assessed — the 8 security sub-agents are now instrumented (a net observability *improvement* for Article VII's domain), no other change to F1 security orchestration (Article VII)
- [x] No technology versions hardcoded by this change (Article I)
- [x] **Article VIII (Observability & Traceability) — materially improved, still partial.** This PBI closes the "which agents are covered" gap from PBI 002 (now ~97 of ~101 vs. ~21 of 101 before). It does **not** close the OpenTelemetry/W3C Trace Context gap already flagged in PBI 002 — that remains a separate, unaddressed sub-requirement of Article VIII.
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Component | Reason |
|---|---|---|
| `specs/002-agent-pipeline-observability` | This PBI | `pipeline_observer.py` and its schema must already exist — this PBI extends, not replaces, it |
| `src/shared/utils/ntp_time.py` | Every self-reporting agent | Already the established mechanism for measuring elapsed time (used elsewhere in the pipeline for timing benchmarks); reused here for `--duration-ms` estimation |
| `src/modules/ava-fabric-agents/shared/observability-self-report.md` | All 97 instrumented agents | Must exist and remain at this path — every agent's one-line reference is a relative path into it |

---

## 8. Exclusions

- **The 4 `db-analyzer/skills/*.md` files** — not independently dispatched, excluded by design (see §1, Scenario 6).
- **No per-file version bump** across the 96 non-master-orchestrator files — see §9 for the explicit reasoning.
- **No OpenTelemetry/W3C Trace Context implementation** — Article VIII's APM-grade requirement remains unaddressed, exactly as scoped out in PBI 002.
- **No change to how `--tokens-in`/`--tokens-out` are estimated** — still LLM best-effort estimates, not automatic token counting.
- **No dependency manifest added for `openpyxl`** — same pre-existing gap noted in PBI 002, untouched here.
- **No change to the aggregate Excel/JSON/Markdown report format** in `docs/optimization/` — those remain exactly as PBI 002 left them; this PBI only adds the new per-agent output alongside them.

---

## 9. Assumptions

- **Applying a shared governance reference does not itself warrant a per-agent version bump.** This mirrors the established, pre-existing rollout of `@governance-apps` to 79 files. The counter-argument — that adding a new *mandatory behavior* (a Bash call before completion) is a functional change, not merely documentation, and should trigger a MINOR bump per Article X — is real and not fully resolved by this assumption; it is recorded here explicitly rather than silently decided, and flagged as a candidate follow-up in `tasks.md` if the team disagrees with this PBI's choice.
- `ntp_time.py` is available and sufficiently precise for the millisecond-level duration estimates self-reporting agents produce.
- Agents can read their own frontmatter reliably at execution time to resolve `{seu_agent_id}`/`{sua_versao}` — this is the same assumption every other shared-governance doc (e.g. `@governance-apps`) already makes.
- The phase-lookup-by-prefix table in `observability-self-report.md` §1 is complete for all current agent name prefixes; a new phase prefix introduced in the future would need a table update.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Coverage | 97 of 101 agent files reference `@observability-self-report`; the 4 excluded files correctly do not |
| Correctness | All 97 relative-path references resolve to the actual shared file (verified programmatically, zero broken links) |
| Tool correctness | `pipeline_observer.py track` writes both the shared state and the new per-agent `metrics.json`/`events.jsonl`, verified by direct execution |
| Backward compatibility | Existing `master-orchestrator.md` `track` calls require no syntax change |
| Isolation | Two different agents tracked in the same run produce independent per-agent folders |
| Failure isolation | Self-report failures are documented as non-blocking in the shared instruction file |
| Version integrity | `ava-master-orchestrator` frontmatter (`1.3.0`) matches its own latest Changelog row |
