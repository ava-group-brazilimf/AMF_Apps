# Agent Specification: Extend AST-Artifact Consumption to Other orchestrator-asis Agents + Fix compressed/ Path

**Feature Branch**: `010-asis-agents-ast-artifact-consumption`
**Created**: 2026-07-08
**Status**: Implemented
**Change Type**: modify-existing (6 agent files + 2 shared docs + 2 observability tool catalogs, MINOR/PATCH per file — no existing Output Contract fields removed anywhere)
**Input**: "Agora analise o documento docs/asis-diagnostic-io-map.md sobre a entradas e saidas dos agentes — solution-delphi é o agente responsável por invocar a tool determinística... verifique os demais agentes... caso esteja lendo o source code diretamente, adicione uma regra de verificação da existência dos artefatos... os agentes devem fazer a leitura de modo obrigatório e interpretação via LLM... os artefatos prontos para o contexto do Copilot são sempre {PROJECT_NAME}/outputs/asis/delphi-ast-raw/compressed/. IMPORTANT: o ajuste deve ser feito apenas nos agentes invocados por esse orchestrador."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-asis-solution-delphi` | `agents/solution-delphi.md` | `2.1.0` → `2.1.1` (PATCH — path bugfix only) |
| `ava-asis-test-qa` | `agents/test-qa-asis.md` | `3.0.0` → `3.1.0` (MINOR) |
| `ava-asis-inventory` | `agents/inventory-asis.md` | `1.3.0` → `1.4.0` (MINOR) |
| `ava-asis-db-analyzer` | `agents/db-analyzer/db-analyzer.md` | `1.3.0` → `1.4.0` (MINOR) |
| `ava-asis-events-pubsub` | `agents/events-pubsub-asis.md` | `1.0.0` → `1.1.0` (MINOR) |
| `ava-asis-documentation` | `agents/documentation-asis.md` | `1.5.9` → `1.6.0` (MINOR) |

**Phase**: F1. **Module**: `asis-diagnostic`. All 6 files dispatched by
`orchestrator-asis.md`, which itself is **explicitly out of scope** per the
user's instruction.

## 2. Problem Statement

`docs/asis-diagnostic-io-map.md` (created in an earlier PBI) documents every
agent `orchestrator-asis.md` dispatches. Reviewing it surfaced two distinct
issues:

1. **Wrong path**: `ava-asis-solution-delphi` (and its dependent docs)
   referenced the 9 deterministic AST JSON artifacts under
   `delphi-ast-raw/extraction/` — the pretty-printed, raw-fidelity variant.
   The user clarified the artifacts actually "ready for Copilot context" are
   always under `delphi-ast-raw/compressed/`. Confirmed by direct diff: the
   `compressed/` variant is a real, minified, `headroom`-engine-compressed
   JSON (5-39% token reduction per a real sample's `manifest.json`), while
   `extraction/` is pretty-printed only — the correct choice for feeding an
   LLM's context window, and the wrong one was in use everywhere.
2. **Missed opportunity**: `ava-asis-solution-delphi` is the only agent in
   the entire `orchestrator-asis.md` dispatch tree with AST-artifact
   consumption wired in (per `specs/007`/`specs/009`). Every other agent
   that reads Delphi source directly was still doing so unconditionally,
   even where a deterministic AST artifact — already sitting on disk by the
   time these agents run — covers exactly the same ground.

## 3. Decision

### 3.1 Path correction (PATCH)

`solution-delphi.md`'s 17 references to `delphi-ast-raw/extraction/`
corrected to `delphi-ast-raw/compressed/`, plus the 2 dependent docs
(`shared/output-paths.md`, `docs/asis-diagnostic-io-map.md`). Pure bugfix —
no Input/Output Contract change, since `compressed/` mirrors `extraction/`
1:1 in structure.

### 3.2 Five agents wired to check-and-read (not invoke) the relevant compressed/ artifact (MINOR each)

For each agent below: a new/extended `## Input Contract` row documents the
relevant `compressed/*.json` artifact; a new existence-check step ("SE o
artefato já existe → ler como fonte primária; SENÃO → prosseguir com o
comportamento original") is added; the agent's pre-existing Glob/Grep
procedure is demoted to an explicit "Fallback" branch (kept verbatim, never
deleted). None of these 5 agents invoke `run_delphi_ast_analysis.py` — only
`ava-asis-solution-delphi` does that (confirmed unchanged from `specs/007`).

| Agent | New primary source | Coverage |
|---|---|---|
| `test-qa-asis.md` | `09_test_coverage.json` | Full — the external analyzer tool's own design doc names this agent as its intended consumer |
| `inventory-asis.md` | `08_code_overview.json` + `02_form_business_rules.json` | Full for LOC/class/complexity totals and form_id extraction; `orphan_dfm` detection has no AST equivalent, stays Glob-based always (narrow exception, same framing as solution-delphi's `.dpr` exception) |
| `db-analyzer.md` | `03_database_rules.json` + `04_database_schemas.json` | Full for Table Inventory and write-operation detection; DB **vendor** detection (MySQL/Oracle/etc.) has no AST equivalent, stays connection-string/config-based always |
| `events-pubsub-asis.md` | `06_integrations.json` | **Partial** — covers only "Queues" and "DB Queue" categories; "Events", "PubSub", "IPC" categories have no AST equivalent, stay 100% Grep always |
| `documentation-asis.md` (VC, FT, RT, RF skills) | VC/RF: `01_business_rules.json` + `08_code_overview.json`; FT/RT: `02_form_business_rules.json` | **Partial** for FT — form inventory and per-field validation are covered, but inter-screen navigation targets are not clearly encoded in the schema, so edge-building may still need light source reading. RN and PR skills unchanged (see Exclusions) |

### 3.3 Known, honestly-documented limitation: Phase A race condition

`orchestrator-asis.md`'s `dispatch_schedule.phase_a` (`mode: immediate`)
dispatches `solution-delphi`, `test-qa`, `inventory`, `db-analyzer`,
`events-pubsub`, and `doc:FT`/`doc:VC` **in parallel**. Since only
`solution-delphi.md` invokes the AST tool (a ~30-40s Bash call per a real
sample run), these 6 agents' new "check compressed/, read if present" logic
may race against `solution-delphi.md`'s own extraction and find the files
absent on a fresh full-pipeline run — falling back safely to existing
behavior. It reliably engages on **resumed/re-entrant** runs. `RT` and `RF`
(Phase B, `on_event`, gated behind the Phase A completion gate) are **not**
subject to this race — by the time they run, the artifacts are guaranteed
to exist (or guaranteed to be honestly absent if `solution-delphi.md`
failed). Fixing the Phase A race would require reordering
`orchestrator-asis.md`'s own dispatch phases — **explicitly out of scope**
per the user's instruction to touch only the dispatched agents, not the
orchestrator itself.

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Resumed run: all 5 agents use AST as primary source (CA01)

**Given** `ava-asis-solution-delphi` already completed successfully in a
prior pass (all 9 `compressed/*.json` files exist), **When** any of the 5
newly-wired agents runs, **Then** each checks for its relevant artifact(s),
finds them present, and derives its primary analysis from the JSON instead
of re-reading raw Delphi source — with the honestly-scoped exceptions
(`orphan_dfm`, DB vendor detection, events/pubsub/IPC categories, FT
navigation edges) still using their original methods.

### Scenario 2 — Fresh run, race unfavorable: safe fallback (CA02)

**Given** a fresh full-pipeline run where Phase A agents race and the AST
extraction hasn't finished when e.g. `test-qa-asis.md` checks for
`09_test_coverage.json`, **When** the check finds the file absent, **Then**
the agent proceeds with its original Glob/Grep/Read procedure, unchanged
and unblocked — no error, no wait, no degraded-confidence flag beyond what
already existed.

### Scenario 3 — Non-Delphi project: no AST checks fire (CA03)

**Given** `legacy_technology != "delphi"`, **When** any of the 5 agents
runs, **Then** it skips the AST-artifact existence check entirely (no AST
tool exists for other legacy technologies) and behaves exactly as before
this PBI.

### Scenario 4 — Path correction verified (CA04)

**Given** `solution-delphi.md` and its 2 dependent docs, **When** grepped
for `delphi-ast-raw/extraction`, **Then** zero matches remain; grepping for
`delphi-ast-raw/compressed` returns the same count that `extraction` used
to.

## 5. Quality Gate Requirements

- [x] Agent IDs unchanged, frontmatter unchanged except version bumps (Article II)
- [x] Version bumps correctly scoped: PATCH for the pure path fix, MINOR for the 5 additive wirings (Article X)
- [x] BDD scenarios cover resumed-run success, race-condition fallback, non-Delphi no-op, and the path fix (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain

## 6. Dependencies

- `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py` — unchanged; still invoked only by `ava-asis-solution-delphi`
- `ava-asis-solution-delphi` (Step 0) — the sole producer of all 9 `compressed/*.json` artifacts these 5 agents now check for

## 7. Exclusions

- `orchestrator-asis.md` itself — explicitly out of scope per the user's instruction; the Phase A race condition (§3.3) cannot be fixed without touching it, and is documented as a known limitation instead.
- 7 security sub-agents + `security-orchestrator-asis.md` — confirmed no natural overlap with the 9 AST artifacts' business/structural content (different domain: vulnerability-pattern detection); the orchestrator itself forbids direct source reading.
- `solution-{vb,cobol,vbnet,powerbuilder}.md` — no AST tool exists for non-Delphi legacy technologies.
- `gap-migration-analyzer.md`, `gaps-risks-asis.md`, `golden-dataset-capture-asis.md`, `bridge-fastqa-asis.md` — confirmed pure consolidation agents reading other agents' markdown outputs, never raw repository source.
- `documentation-asis.md`'s **RN** skill — deliberately kept as pure doc-mining, distinct from the code-mined `asis/code-business-rules.md` per `specs/007`'s own naming decision; may optionally cross-reference that file but is not redirected to `01_business_rules.json` as primary source.
- `documentation-asis.md`'s **PR** skill — no documented source-reading procedure exists in this file to replace.
- `inventory-asis.md`'s `orphan_dfm` detection — no AST artifact enumerates `.dfm` files without a matching `.pas`; stays Glob-based always.
- `db-analyzer.md`'s DB **vendor** detection — no AST artifact identifies the target RDBMS; stays connection-string/config-based always.
- `events-pubsub-asis.md`'s "Events"/"PubSub"/"IPC" categories — no AST equivalent exists for VCL event handlers, hand-rolled pub/sub patterns, or Windows IPC primitives; stay 100% Grep always.

## 8. Assumptions

- The wrapper script's all-or-nothing success gate (all 9 files or none) means a realistic partial-file state (some `compressed/*.json` present, others missing) is not expected in practice — each agent's existence check is still written defensively per-artifact.
- `04_database_schemas.json`'s `payload.tables[]`/`payload.inferred_tables[]` carry enough structure (columns, FKs, operations) to populate `db-analyzer.md`'s Table Inventory template — not independently re-verified against a schema with real FK data in this PBI, consistent with the same level of verification applied to `03_database_rules.json`/`04_database_schemas.json` in `specs/007`.
- `02_form_business_rules.json`'s `payload.forms[].fields[].event_handlers` may or may not encode inter-screen navigation targets — stated honestly as unconfirmed/partial rather than assumed complete.

## Success Criteria

| Criterion | Measure |
|---|---|
| Path corrected everywhere | `grep -c "delphi-ast-raw/extraction"` → 0 in `solution-delphi.md`, `output-paths.md`, `docs/asis-diagnostic-io-map.md` |
| All 5 agents have existence-check logic | Each file's `## Input Contract` documents the relevant artifact(s) + a "SE existir/SE não existir" branch |
| Original behavior fully preserved as fallback | `grep -c "Fallback"` > 0 in each of the 5 files; nothing deleted, only demoted |
| Partial-coverage cases stated honestly | `events-pubsub-asis.md` and `documentation-asis.md` (FT) explicitly document what their AST artifact does *not* cover |
| Version/observability consistency | Frontmatter version == FASE OBRIGATÓRIA `--version` literal == `pipeline_observer.py`/`generate_observability_report.py` catalog entry, per file (where catalogued) |
| Race condition documented, not silently ignored | `research.md`/`plan.md` explicitly name the Phase A race and why it's out of scope to fix |
