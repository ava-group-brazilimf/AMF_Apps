# Research Notes: Extending AST-Artifact Consumption Beyond solution-delphi.md

## 1. `compressed/` vs `extraction/` — confirmed by direct diff, not assumed

Before touching any file, `extraction/01_business_rules.json` and
`compressed/01_business_rules.json` were diffed directly (real sample at
`projects/Meu-ERP-006-AST-LLM-AS-IS-Orchestrator/outputs/asis/delphi-ast-raw/`):
`extraction/` is pretty-printed with indentation (95 lines for one file);
`compressed/` is the same content minified to a single line. The
`compressed/manifest.json` confirms a real `headroom`-engine transform
(`router:smart_crusher`) ran, with measured `reduction_pct` per artifact
ranging 5.5%-39.1% and `tokens_in`/`tokens_out` recorded per file. This is
not a no-op mirror in this sample — it's genuine token optimization,
confirming the user's correction that `compressed/` (not `extraction/`) is
the variant meant for LLM context consumption. `solution-delphi.md` and its
2 dependent docs had 17+2 references to the wrong directory, all corrected
in this PBI.

## 2. Every Phase-A-dispatched agent read in full (3 Explore agents)

Rather than guess which agents might benefit from AST consumption, every
agent `orchestrator-asis.md` dispatches was read in full (not excerpted) and
classified by whether it reads Delphi source directly, and if so, exactly
where:

- **`test-qa-asis.md`** (v3.0.0): extensive, literal Glob/Grep/Read
  pseudocode across two skills (`discover_tests()` procedure, Framework
  Classification table) — the clearest, most concrete source-reading logic
  of any agent surveyed. Already has both `## Input Contract` and
  `## Execution Steps` (8 numbered steps) to anchor edits.
- **`inventory-asis.md`** (v1.3.0): sparse — only the `form-registry.json`
  generation procedure has literal Glob/Grep (`class\s+(\w+)\s*\(TForm\)`).
  The LOC/CC/coupling/layer/module/dependency metrics have **no** documented
  extraction procedure in this file at all — described only via output
  schemas. No `## Input Contract`, no `## Execution Steps` section existed;
  both had to be introduced or worked around.
- **`db-analyzer.md`** (v1.3.0) + 4 skill files: the sparsest of all —
  zero literal Glob/Grep blocks anywhere; only prose-level fallback language
  ("SQL inline", "connection string"). The 4 SGBD-specific skill files
  (mysql/mariadb/oracle/sqlserver-agent.md) operate exclusively on SQL
  catalog queries (`information_schema.*`, `sys.tables`, etc.) or
  provided DDL/DML — never on raw `.pas`/`.dfm`, confirmed by reading all 4.
- **`events-pubsub-asis.md`** (v1.0.0): the cleanest single insertion
  point of all 5 — one literal `### Step 1 — Scan & Collect` block with a
  `Glob` line and 5 categorized `Grep` pattern groups, easy to demote to an
  explicit fallback without disturbing anything else.
- **`documentation-asis.md`** (v1.5.9): the most fragmented — no
  `## Input Contract`, no `## Execution Steps` at all. Only 2 of its 6
  skills (VC, FT) are explicitly stated to read source directly; FT's only
  concrete signal is itself a fallback (glob `.dfm`/`.pas`, used only when
  `form-registry.json` isn't ready). RT/RF/RN/PR have no documented
  extraction procedure in this file — their logic is implicit/inherited
  from the LLM's own reasoning, not spelled out as Glob/Grep steps.
- **8 security agents** (`security-orchestrator-asis.md` + 7 sub-agents):
  checked individually. 5 read source directly but exclusively for
  vulnerability-pattern detection (SQL/XSS/command injection entry points,
  hardcoded secrets, taint flows, STRIDE threat modeling) — a domain with
  no natural overlap with the 9 AST artifacts' business/structural content.
  2 don't read source at all (runtime logs, pentest reports). The
  orchestrator's own Guardrail explicitly forbids it analyzing source
  directly. All 8 confirmed out of scope.
- **`gap-migration-analyzer.md`, `gaps-risks-asis.md`,
  `golden-dataset-capture-asis.md`, `bridge-fastqa-asis.md`**: confirmed
  pure consolidation agents — their own `## Input Contract`/consolidation
  algorithms read exclusively from *other agents'* markdown/JSON outputs,
  never raw repository source. Nothing to wire.

## 3. Initial scope decision reversed mid-plan — a real correction, not a stylistic one

The first draft of this plan excluded `documentation-asis.md` entirely,
reasoning that its lack of `## Input Contract`/`## Execution Steps` and the
fact that only FT has a *concrete* (fallback-only) source-reading signal
made it a poor fit relative to the other 4 candidates. The user explicitly
rejected this exclusion via `ExitPlanMode`, stating: "O agente de
documentation-asis.md deve ler os artefatos gerados na analise AST caso eles
existam e fazer a interpretação para gerar os outputs." The plan was revised
before implementation began to include `documentation-asis.md` (VC, FT, RT,
RF skills), with RN and PR still excluded on their own separate, narrower
grounds (RN's deliberate distinctness from code-mined content per
`specs/007`; PR's total absence of a documented extraction procedure to
replace) — this narrower exclusion was not challenged.

## 4. Dispatch-order verification — the Phase A race is real, not hypothetical

Before finalizing the plan, `orchestrator-asis.md`'s own
`dispatch_schedule` was read directly (not inferred). Confirmed:

```yaml
phase_a:
  mode: immediate
  ...
    - test-qa            # blocking | deps: source code
    ...
    - db-analyzer        # blocking | deps: source code + DB schema
    - events-pubsub      # blocking | deps: source code
```

and the `phase_a_agents` array explicitly includes `"doc:FT"`, `"doc:VC"`
alongside the solution agent, `test-qa`, `inventory`, `db-analyzer`, and
`events-pubsub`. The ASCII diagram at line 79 labels this "PHASE A (immediate
— 8 dispatches, all read source code directly)". Since only
`solution-delphi.md` invokes the AST tool, and a real sample run's
`metrics.jsonl` shows `extraction_duration_ms: 30438` +
`precompress_duration_ms: 5689` (≈36s total for a 30-file project — larger
projects would take longer), the other 6 Phase-A agents' new existence
checks may find the artifacts still being written when they run. This is
documented as a known, accepted limitation rather than silently ignored or
glossed over — consistent with every other honestly-scoped limitation in
this session's prior PBIs (`AST_UNAVAILABLE_DEGRADED_ANALYSIS`, the
`test-qa-asis.md` race the external tool's own design doc already flagged
and deferred).

`RT` and `RF` (documentation-asis.md's Phase B skills, `dispatch_schedule.phase_b`,
`mode: on_event`, gated on `phase_a_gate == OPEN`) are **not** subject to
this race — `evaluate_phase_a_all()` only returns `OPEN` after every Phase A
agent (including `solution-delphi`) reaches a terminal state, so by the time
RT/RF run, `solution-delphi`'s AST artifacts are guaranteed to exist (or
guaranteed to be genuinely absent, if `solution-delphi` itself failed — in
which case RT/RF correctly fall back too, no different from today).

## 5. Per-agent artifact-fit mapping — reusing specs/007's schema documentation

No new JSON schema exploration was needed — `specs/007-solution-delphi-ast-consumption/data-model.md`
already documents all 9 artifacts' `payload` structures in full (verified
against a real sample run in that PBI). This PBI's job was purely to map
existing, already-documented fields to each of the 5 candidate agents'
existing needs:

- `09_test_coverage.json` → `test-qa-asis.md`: 1:1 exact match, already
  identified as the intended consumer by the external analyzer's own design
  doc (found in `specs/009`'s research).
- `08_code_overview.json.payload.classes` (`{name, parent, file, line}`) →
  `inventory-asis.md`: identical shape to the `ClassRegistry[]` pattern
  `solution-delphi.md` already uses for its own Step 1/Step 3 — same
  parent-chain classification technique reused, not reinvented.
- `03_database_rules.json` + `04_database_schemas.json` →
  `db-analyzer.md`: the exact same 2 files `solution-delphi.md` already
  consumes for its own Step 4 Analysis #6 (Data Access Profiling) — a
  natural, low-risk reuse rather than a new integration pattern.
- `06_integrations.json` → `events-pubsub-asis.md`: partial fit, honestly
  scoped (Queues/DB-Queue categories only; Events/PubSub/IPC have no AST
  equivalent, confirmed by the artifact's own description — "DLL, COM,
  sockets, e-mail, arquivos, filas" does not mention component-level events,
  hand-rolled pub/sub, or Windows IPC primitives).
- `01_business_rules.json` + `08_code_overview.json` (VC, RF) and
  `02_form_business_rules.json` (FT, RT) → `documentation-asis.md`: same
  files already validated in `specs/007`/this PBI's other agents, reused
  again — no new schema risk introduced.

## 6. Version bump rationale

`solution-delphi.md`: **PATCH** (`2.1.0` → `2.1.1`) — pure path correction,
zero Input/Output Contract change (the artifacts named are identical, only
the directory they're read from changed). The other 5 files: **MINOR** —
each gains new Input Contract rows and new conditional logic, but nothing
existing is removed, renamed, or made incompatible; every prior behavior
remains reachable via the (renamed, not deleted) "Fallback" branch.
