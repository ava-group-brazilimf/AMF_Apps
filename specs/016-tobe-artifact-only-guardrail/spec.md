# Agent Specification: Artifact-Only Consumption Guardrail + Missing-Artifact Escalation Gate (F2 TO-BE)

**Feature Branch**: `016-tobe-artifact-only-guardrail`
**Created**: 2026-07-12
**Status**: Implemented
**Change Type**: modify-existing (`orchestrator-tobe.md` + 20 dispatched agent files + `module.yaml` + 1 new shared protocol file + `docs/tobe-architecture-io-map.md` + `CHANGELOG.md`, MINOR/PATCH per file — no existing Output Contract field removed anywhere)
**Input**: "Agora analise o documento docs/tobe-architecture-io-map.md sobre a entradas e saidas dos agentes — foi verificado que ao invocar o orquestrator to-be ao ler o project-config, os agentes estão lendo o codigo legado full novamente [...] guardrail específico instruindo o agente/sub agentes invocados para nunca ler o codigo full novamente [...] Os agente devem sempre consumir as informações e arquivos já gerados evitando reler o codigo legado novamente. Em caso dos agentes não encontrar o arquivo necessario, a esteira deve avisar o usuario no log de execução, e solicitar aprovação do usuario para dar seguimento na esteira. Crie o plano de implementação e documente via speckit"

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-tobe-orchestrator` | `tobe-architecture/agents/orchestrator-tobe.md` | `2.3.0` → `2.4.0` (MINOR — new `## Dispatch Protocol` section, 26 dispatch sites hardened, 1 path bugfix, no field removed) |
| _(new)_ `@artifact-only-consumption-protocol` | `shared/artifact-only-consumption-protocol.md` | `1.0.0` (new shared include, not a dispatched agent) |
| 20 dispatched `tobe-architecture` agent files (see §3.3) | `tobe-architecture/agents/*.md` | Each MINOR (or `1.0.0` introduced where `version:` was absent — 9 files) |

**Phase**: F2 — TO-BE Architecture. **Module**: `tobe-architecture`. All files dispatched by
`orchestrator-tobe.md`, which is itself the primary target of this change (unlike `specs/010`,
the orchestrator is explicitly IN scope here, mirroring `specs/013`'s treatment of
`master-orchestrator.md`).

## 2. Problem Statement

`docs/tobe-architecture-io-map.md` (existing audit) documents every agent dispatched by
`orchestrator-tobe.md` v2.3.0. Its §3 ("Full Source Re-Read Flags") concludes that, in the
*static* text of every agent's Input Contract, no TO-BE agent declares reading `repository_path`
or legacy source files directly — all 20 agents are nominally artifact-based. However, its §4
separately documents **15 real path-mismatch bugs**: artifacts referenced at the wrong path, or
referencing files no agent in the pipeline ever produces (e.g. `outputs/tobe/migration-plan.md`
instead of the real `outputs/tobe/docs/migration-plan.md`; `outputs/tobe/docs/architecture-technical.md`,
which no agent's Output Contract produces at all). This means a meaningful share of declared
"required" inputs resolve to "file not found" at runtime.

The user reported that, in practice, invoking `orchestrator-tobe.md` results in dispatched
agents reading the full legacy codebase again — slow and token-expensive — despite the AS-IS
pipeline (F1) already having been optimized (`specs/010-asis-agents-ast-artifact-consumption`)
to produce deterministic, LLM-ready artifacts under `outputs/asis/**` for exactly this purpose.

Root cause, confirmed by direct file reads (not inference):

1. `specs/013-master-orchestrator-mandatory-spec-read` already diagnosed and fixed the identical
   class of bug elsewhere in this repository: `master-orchestrator.md`'s `DISPATCH @agent-id`
   calls had no instruction to `Read()` the target agent's full `.md` spec before invoking it —
   so the LLM sometimes "improvised" the sub-agent's behavior from generic domain knowledge
   instead of the literal spec. In the historical incident that motivated spec 013, this
   improvisation caused an AS-IS sub-agent to skip deterministic AST extraction and fall back to
   manual, full-source reads. Spec 013's own §8 Exclusions explicitly flagged
   `orchestrator-tobe.md` → its own internal sub-dispatches as "the same risk class, not
   reported as broken, left as a possible future PBI" — **never fixed there**.
2. Direct grep of `orchestrator-tobe.md` v2.3.0 confirmed: all 26 `Invocar \`{agent}.md\`` /
   cross-module dispatch sites have **zero** `⛔ Read(...)` prefixes — exactly the same gap spec
   013 closed in `master-orchestrator.md` (24 sites) and `orchestrator-asis.md` (1 site).
3. Combined with finding §4's 15 path bugs, this is the concrete mechanism: when a dispatched
   agent's documented input resolves to "absent" (because the path is wrong, or the producer
   never wrote it), and the agent was never forced to load its own literal Input Contract via a
   mandatory `Read()` step, it has room to improvise — including falling back to reading legacy
   source to compensate, exactly as it did in the historical AS-IS incident.
4. `orchestrator-tobe.md` already demonstrates the *correct* target behavior in one place — its
   "Gate 0→1 — Validação de Consistência ADR × project-config.yaml" section: a `🚫 PROIBIÇÃO
   ABSOLUTA` block, a structured conflict report (`trace_id`, table, Opção A/B/C), ending in
   "aguardar ação do usuário." `coder-dotnet.md`'s guardrail `G-9` ("Se `bounded-context-map.md`
   TO-BE estiver ausente → alertar e interromper... aguardar confirmação. Nunca inventar bounded
   contexts") is the same pattern at single-agent scale. But most other agents — e.g.
   `test-plan-tobe.md`'s `[MISSING INPUT: x]` convention — either silently degrade ("continuar
   com...") or hard-stop without a structured report or an explicit wait-for-approval step. No
   existing mechanism generalizes the Gate 0→1 pattern across the whole pipeline.

## 3. Decision

### 3.1 New shared protocol file: `shared/artifact-only-consumption-protocol.md` (NEW, v1.0.0)

Follows the existing `shared/`-include convention (`governance-apps.md`,
`backend-context-protocol.md`), referenced as `[@artifact-only-consumption-protocol](../../shared/artifact-only-consumption-protocol.md)`
from every consuming file. Two sections:

1. **Proibição de Releitura de Código Legado** — explicit prohibition on `Read`/`Glob`/`Grep`
   over any file under `repository_path` or legacy extensions (`.pas`/`.dfm`/`.dpr`); explicit
   prohibition on bulk-reading `outputs/tobe/source-code/**`; the 3 legitimate exceptions already
   in use (writing `Directory.Packages.props`, writing per-module `README.md`, existence-only
   check of `docker-compose.yml`, plus compiler/CVE CLI gates) are preserved, not newly
   forbidden; positive rule that all context comes from `outputs/asis/**` / `outputs/tobe/**`
   artifacts already declared in each agent's own Input Contract.
2. **Procedimento de Escalonamento — Artefato Obrigatório Ausente** — generalizes the existing
   `[MISSING INPUT: x]` / `[FONTE AUSENTE]` + `CONFIDENCE: LOW` vocabulary (no new terms
   invented): non-blocking inputs keep today's soft-degrade behavior, now standardized; blocking
   inputs get a new `⛔ [ARTIFACT GATE FAILED]` structured report (trace_id, projeto, fase,
   agente afetado, artefato ausente, path esperado, produzido por) with Opção A (fornecer
   manualmente) / B (pular com confiança degradada — não disponível para inputs estruturalmente
   fundamentais) / C (abortar), ending in an explicit wait for user approval. Cross-references
   Gate 0→1 and `coder-dotnet.md` G-9 as pre-existing compliant examples, not replaced by this
   protocol.

### 3.2 `orchestrator-tobe.md` hardening (2.3.0 → 2.4.0, MINOR)

- New `## Dispatch Protocol` section (adapted from `master-orchestrator.md`'s own, lines
  201-227): mandatory `Read()` of the full target agent spec before any dispatch, covering the
  25 in-module `Invocar` sites plus the 2 cross-module dispatches (`@ava-asis-gaps-risks`,
  `@ava-stack-docs-researcher`) and the dynamically-resolved `{resolved_coder_agent}`; explicit
  log-visibility clause mirroring spec 013's fix.
- All 26 dispatch sites prefixed with `⛔ Read({path}) OBRIGATÓRIO (ver § Dispatch Protocol) →`
  — same convention as spec 013, one line touched per site, no renumbering.
- Reference line to `@artifact-only-consumption-protocol` near `## Canonical Inputs`.
- Path fix: Fase 4.5 input table, `outputs/tobe/migration-plan.md` → `outputs/tobe/docs/migration-plan.md`
  (io-map §4.4).
- Existing `HARD STOP` / `[GATE FAILED]` blocks (Fase 1.4, 1.5, 2.5→3, and others found by
  direct search) each gain one appended line pointing to the shared protocol's §2.2 escalation
  format — their existing custom report bodies are preserved verbatim, not replaced.

### 3.3 Twenty agents wired to the shared protocol (each MINOR, or `1.0.0` introduced where absent)

`architecture-decision-matrix-tobe.md`, `adr-tobe.md`, `architecture-design-tobe.md`,
`database-policy-tobe.md`, `database-design-tobe.md`, `security-design-tobe.md`,
`architecture-technical-tobe.md`, `migration-plan-tobe.md`, `measure-size-tobe.md`,
`coexistence-strategy-tobe.md`, `risk-mitigation-tobe.md`, `openapi-spec-tobe.md`,
`coder-dotnet.md`, `docs-tobe.md`, `developer-guide-tobe.md`, `test-plan-tobe.md`,
`user-journeys-tobe.md`, `designer-system-tobe.md`, `test-plan-consolidated-tobe.md`,
`azure-infra-estimator-tobe.md`.

Each gets: (a) one reference line to `@artifact-only-consumption-protocol` near its Input
Contract; (b) an appended pointer to the shared escalation format on each existing
blocking-input clause; (c) `version: "1.0.0"` introduced on the 9 files that had no `version:`
field at all (`database-policy-tobe.md`, `database-design-tobe.md`, `architecture-technical-tobe.md`,
`risk-mitigation-tobe.md`, `openapi-spec-tobe.md`, `coder-dotnet.md`, `docs-tobe.md`,
`user-journeys-tobe.md`, `designer-system-tobe.md`) — a pre-existing Article II gap, fixed as
cheap collateral since these files are touched anyway.

Four of these files carry one additional, distinct fix, all confirmed via `docs/tobe-architecture-io-map.md` §4:
- `risk-mitigation-tobe.md` — same path fix as §3.2 (§4.4), applied to its own Input Sources table.
- `azure-infra-estimator-tobe.md` — Read Priority path `outputs/tobe/sizing-report.md` →
  `outputs/tobe/docs/sizing-report.md` (§4.8, partial — the second dead reference in that same
  list is left unresolved, see §7 Exclusions).
- `test-plan-tobe.md` — `architecture-technical.md` input reclassified from ✅ obrigatório to ❌
  non-blocking (§4.6 — no agent produces this file; the label now matches its pre-existing
  soft-degrade behavior).
- `designer-system-tobe.md` — `outputs/asis/docs/screen-flow.md` input reviewed against §4.7;
  found already non-blocking in the file's current state (enrichment-only, priority 5 in
  `## Input Sources`, outside the agent's `## Gate`) — no reclassification needed, the file's
  wording already matched the desired behavior.

### 3.4 `module.yaml` registration fix (1.3.0 → 1.3.1, PATCH)

6 agents already live in `tobe-architecture/agents/` but never registered in
`tobe-architecture/module.yaml`'s `agents:` list — an Article IV gap, same class as spec 013's
collateral fix to `devops-agents/module.yaml`. 5 of the 6 (`adr-tobe.md`,
`coexistence-strategy-tobe.md`, `risk-mitigation-tobe.md`, `coder-dotnet.md`,
`designer-system-tobe.md`) are confirmed dispatched via a direct `Invocar` grep hit. The 6th,
`user-journeys-tobe.md`, is registered too even though it has **no literal `Invocar` line** in
`orchestrator-tobe.md` today — it's a real, activation-phrase-bearing agent listed in the "Agent
Team Gerenciado" table and produces artifacts consumed downstream, but Fase 7 has no dedicated
`### Fase N —` body (a pre-existing gap already tracked in `docs/tobe-architecture-io-map.md`
§4.3 and explicitly deferred, not fixed, by this PBI — see §7 Exclusions). The Article IV
registration gap is independent of that separate dispatch-wiring gap, so it's closed here
regardless. `dotnet-nuget-policy.md` deliberately excluded (a `shared/`-style include, never
dispatched via `Invocar`, not a top-level agent).

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal: artifact present, no legacy read (P1)

**Given** `bounded-context-map.md` TO-BE exists at its documented path, **When**
`orchestrator-tobe.md` dispatches `coder-dotnet.md` for a bounded context, **Then** the agent
reads only the artifacts declared in its own Input Contract (`bounded-context-map.md`,
`project-config.yaml`, `tech-framework-document.md`, the per-BC OpenAPI spec), never touches
`repository_path` or bulk-reads `outputs/tobe/source-code/`.

### Scenario 2 — Missing blocking artifact: gate fires and waits for approval (P1)

**Given** `wave-model.json` is absent when Fase 4.3 (`coexistence-strategy-tobe.md`) is reached,
**When** the orchestrator evaluates that phase's entry gate, **Then** it emits the `⛔ [ARTIFACT
GATE FAILED]` structured report (trace_id, fase, artefato ausente, path esperado, agente
afetado), presents Opções A/B/C, and halts — no silent estimate, no fallback read of legacy
source, no automatic progression.

### Scenario 3 — Dispatch Protocol: spec read before every dispatch (P1)

**Given** the orchestrator reaches any of its 26 dispatch sites, **When** it executes that
`Invocar`/dispatch instruction, **Then** it has already `Read()`'d the full target `.md` spec per
`## Dispatch Protocol`, and any output/log emitted by the dispatched agent (including its own
internal sub-dispatches) remains visible in the session rather than summarized away — mirrors
`specs/013` Scenario 2/3, scoped to `orchestrator-tobe.md`'s own dispatch tree.

### Scenario 4 — Non-blocking/optional input absent: warn but continue (P2)

**Given** `outputs/asis/qa/test-strategy-asis.md` is absent (already documented elsewhere as an
unresolved upstream dependency) and the consuming agent's Input Contract marks the equivalent
class of input as non-blocking, **When** the agent reaches that input, **Then** it logs
`[FONTE AUSENTE] {arquivo} — CONFIDENCE: LOW` visibly in the execution output and proceeds with
its documented fallback (default thresholds, omitted section, etc.) — no approval-wait, no hard
stop.

### Scenario 5 — Module registration: previously-unregistered agents resolve correctly (P2)

**Given** `orchestrator-tobe.md` dispatches one of the 6 previously-unregistered agents (e.g.
`coder-dotnet.md`), **When** any tooling resolves the agent's spec path via `module.yaml`,
**Then** it now resolves correctly instead of the agent being absent from the module's own
registry.

## 5. Quality Gate Requirements

- [x] Agent IDs unchanged; frontmatter fields unchanged except `version`/`date` (Article II)
- [x] Version bumps correctly scoped: MINOR for `orchestrator-tobe.md` and the 20 dispatched
      agents (additive, no Input/Output Contract shape change), PATCH for `module.yaml`
      (registration completeness only), `1.0.0` new for the shared protocol file (Article X)
- [x] BDD scenarios cover nominal artifact-present path, blocking-missing-artifact escalation,
      the Dispatch Protocol Read-before-dispatch fix, non-blocking degrade, and the collateral
      module registration fix (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] pt-BR preserved in all agent body content (Article V)
- [x] `module.yaml` diff included in this spec (§3.4) (Article IV)
- [x] No `[NEEDS CLARIFICATION]` markers — scope (Dispatch Protocol inclusion, path-bug scope,
      collateral fixes) confirmed with the user via `AskUserQuestion` before implementation

## 6. Dependencies

- `specs/010-asis-agents-ast-artifact-consumption` — the AS-IS optimization this PBI extends the
  same discipline to on the TO-BE side; the artifacts this protocol tells TO-BE agents to consume
  are exactly the ones that PBI made deterministic.
- `specs/013-master-orchestrator-mandatory-spec-read` — direct precedent and template for the
  `## Dispatch Protocol` / `⛔ Read(...)` mechanism; this PBI is the follow-up its own §8
  Exclusions named as a future PBI.
- `docs/tobe-architecture-io-map.md` — the audit that surfaced the 15 path bugs this PBI
  partially remediates (4 of 15) and fully documents (all 15, via updated §3/§4 status notes).
- `.specify/memory/constitution.md` — Articles I, II, IV, V, VI, X govern all changes made here.

## 7. Exclusions

- 11 of the 15 path/ownership bugs in `docs/tobe-architecture-io-map.md` §4 are explicitly
  **not** fixed here: §4.1 (`.NET` coder agent resolution ambiguity — `coder-dotnet.md` vs.
  `coder-dotnet-backend.md`), §4.2 (Build Validator ownership dispute), §4.3 (Fase 7/8 missing
  dedicated sections), §4.5 (dead TDD Publisher path family, never dispatched), §4.9
  (`user-journeys-tobe.md`'s dead path + AS-IS/TO-BE BC map inconsistency), §4.10
  (`architecture-design-tobe.md`'s Output Contract overlap with downstream agents), §4.11
  (`developer-guide-tobe.md`'s wrong optional test-plan path), §4.12 (Fase 7.8 gate/agent
  Input Contract mismatch), §4.13 (`test-plan-tobe.md`'s two AS-IS QA artifacts with no
  documented upstream producer — an AS-IS-side gap, not fixable from F2), §4.14/§4.15
  (cosmetic table-completeness gaps). Deferred to a future PBI.
- `azure-infra-estimator-tobe.md`'s second Read Priority path (`architecture-design-tobe.md`,
  dead reference) is left unresolved — deciding whether it should point to
  `architecture-blueprint.md` or be dropped is a design call, deferred.
- `{resolved_coder_agent}` ambiguity for `.NET` (§4.1) is not resolved — the new `⛔ Read(...)`
  is only as good as the path the existing `CODER_AGENTS` map already resolves to.
- `dotnet-nuget-policy.md`'s missing `version:` field and non-standard location (agent-style
  frontmatter living outside `shared/` while behaving like a `shared/` include) are noted, not
  fixed.
- No live pipeline run was performed to observe the fix end-to-end — verification is
  structural/grep-based only (prose instruction files, not runnable code), consistent with
  `specs/010`'s and `specs/013`'s own verification approach.

## 8. Assumptions

- Leaving 11 of 15 path bugs unfixed means the new `⛔ [ARTIFACT GATE FAILED]` gate **will**
  start surfacing additional occurrences at those points once live — this is the visibility the
  user explicitly asked for (point 3 of the original request), not a regression to be avoided.
- The "Read-before-dispatch closes the improvisation gap" theory (mirrored from spec 013's own
  root-cause analysis) is plausible and consistent with the one historical incident already
  documented in this repository, but — like spec 013 itself — is not independently verified
  against harness internals; the fix is correct regardless of the exact mechanism, since making
  the requirement explicit is strictly safer than leaving it implicit.
- The 3 `deliverables/`-module dispatch sites (out of primary F2 scope per the io-map) still
  receive the `⛔ Read(...)` prefix for consistency, even though their own Input/Output Contracts
  are not otherwise touched by this PBI.

## Success Criteria

| Criterion | Measure |
|---|---|
| All dispatch sites hardened | `grep -c "⛔ Read("` in `orchestrator-tobe.md` == count of `Invocar`/cross-module dispatch sites found by direct grep |
| No renumbering | Diff shows only the dispatch line changed at each site, no reindexing |
| Shared protocol referenced everywhere | `grep -rl "artifact-only-consumption-protocol" tobe-architecture/agents/` returns `orchestrator-tobe.md` + all 20 dispatched agent files (21 total) |
| Path bugs fixed | `grep -c "outputs/tobe/migration-plan.md"` (old wrong path) → 0 in `orchestrator-tobe.md` and `risk-mitigation-tobe.md`; `grep -c "outputs/tobe/sizing-report.md"` (old wrong path, Read Priority) → 0 in `azure-infra-estimator-tobe.md` |
| Downgrades applied | `test-plan-tobe.md` and `designer-system-tobe.md` no longer mark the 2 target inputs as ✅ obrigatório/blocking |
| Module registration fixed | All 6 previously-missing agent ids present in `tobe-architecture/module.yaml`'s `agents:` list |
| Version fields introduced | The 9 previously-versionless agent files now have `version: "1.0.0"` |
| Version/SemVer consistency | `orchestrator-tobe.md` frontmatter == `2.4.0`; `module.yaml` == `1.3.1`; shared protocol file == `1.0.0` |
| Docs synced | `docs/tobe-architecture-io-map.md` §3 conclusion updated; §4.4/§4.6/§4.7/§4.8 carry a "Status" note referencing this spec |
| CHANGELOG updated | New entry present describing the guardrail + escalation gate |
