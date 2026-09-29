# ISSUE-003 — Tool-Call Overhead & F1/F2 Dispatch Serialization

**Date**: 2026-07-30
**Projects**: processaERP-10, processaERP-11
**Severity**: HIGH (performance) · MEDIUM (2 path bugs)
**Status**: MEASURED — mitigations below, partially implemented
**Related**: [ISSUE-002](ISSUE-002-agent-stuck-pipeline-performance.md) (RC-2/RC-3/RC-4)

---

## 1. Executive summary

The dominant cost in F1/F2 is **the number of tool calls**, not the work inside them. Every
`Bash:` line in an agent spec is a full LLM inference round-trip carrying the entire context,
plus an interpreter cold start. Process startup was measured at **0.7–2.5 s**; the model
round-trip around it is an order of magnitude larger.

This reframes the optimisation target. The existing
[batch-write-protocol.md](../../src/modules/ava-fabric-agents/asis-diagnostic/shared/batch-write-protocol.md)
attributes "~60 s" to each `Bash` call — that figure is right about the *round-trip*, but it is
not process startup, and the distinction matters: **you cannot fix this by making the scripts
faster. You fix it by calling them fewer times.**

Three findings, in order of payoff:

| # | Finding | Cost today | After |
|---|---|---|---|
| A | Observability: 3 calls/agent × 101 agents | ~300 tool calls | ~101 |
| B | F2 has no wave/DAG model — 24 strictly sequential phases | 3 agents idle behind 10 phases | 3 parallel after Fase 1 |
| C | Per-agent dispatch guard serialises Wave 2 | 5 calls, 6.4 s | 1 call, 1.4 s (**4.6×**) |

Plus two path-mismatch bugs that cause silent re-dispatch and a skipped phase (§6).

---

## 2. Measured baseline

All measurements on the F1 host, Windows 11, 2026-07-30. 10 iterations each unless noted.

### 2.1 Interpreter cold start

| Command | ms/call |
|---|---:|
| `python -c "pass"` | **692** |
| `powershell -NoProfile -ExecutionPolicy Bypass -Command "1"` | **1 810** |
| `pwsh -NoProfile -NoLogo -Command "1"` | **2 178** |

> **PowerShell 5.1 costs 2.6× a Python start; `pwsh` 7 costs 3.1×.** Any logic that could live in
> Python should not be written as a PowerShell one-liner.

### 2.2 Repo utilities

| Invocation | ms |
|---|---:|
| `ntp_time.py` (NTP network query) | **1 466 – 2 549** |
| `context_budget.py --project` | 1 798 |
| `artifact_gate.py --agent` (×5, one per agent) | **6 401** (1 280 each) |
| `artifact_gate.py --wave phase_a_wave2` (×1, all 5 agents) | **1 404** |

### 2.3 Call-site census

Counted across `src/modules/ava-fabric-agents/**`:

| Script | Call sites | Files |
|---|---:|---:|
| `pipeline_observer.py` | **206** | 103 agents call `track` |
| `ntp_time.py` | **125** | 40 |
| `validate_diagram.py` | 17 | — |
| `build_runner.py` | 16 | — |
| `artifact_gate.py` | 4 | — |

---

## 3. How to call PowerShell from an agent

### 3.1 The rule

**Use Python for logic. Use PowerShell only for the batched file write.** PowerShell earns its
1.8 s start exactly once per agent — for the `[ordered]@{}` + here-string batch that writes the
whole output contract. Everything else (parsing, gating, counting, validating) is cheaper and
more testable in Python.

### 3.2 Anti-pattern — inline `-Command` with a large script

```
❌ Bash: powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = @{ 'a.md' = @'
...500 lines...
'@ }; foreach (...) { ... }"
```

Three problems:

1. **Double process** — the `Bash` tool spawns a shell, which spawns `powershell`. Two cold
   starts (~0.7 s + ~1.8 s) before a single byte is written.
2. **Quoting is unrecoverable.** `"` inside `-Command` inside the tool's own quoting has no
   reliable escape. This is the same class of failure as the `for /f` bug fixed in
   `copilot-cli-headroom.bat` — where a mis-quoted command silently fell back to a default value
   because `2>nul` hid the error.
3. **No exit-code fidelity.** A parse error and a write failure both surface as "something went
   wrong", with no structured way for the agent to know which artifacts landed.

### 3.3 Correct pattern — script to disk, then `-File`

```bash
# 1) Write the script (heredoc — no shell interpolation, no quoting hell)
cat > .tmp/write-artifacts.ps1 <<'PS1'
$ErrorActionPreference = 'Stop'
$base = "projects/processaERP-11/outputs/asis"

$files = [ordered]@{
  "inventory-report.md" = @'
<conteúdo>
'@
  "metrics.json"        = @'
{"total_loc": 4600}
'@
}

$result = @{ ok = @(); failed = @() }
foreach ($e in $files.GetEnumerator()) {
  $path = Join-Path $base $e.Key
  $dir  = Split-Path $path -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  try {
    [System.IO.File]::WriteAllText($path, $e.Value, [System.Text.Encoding]::UTF8)
    $result.ok += @{ path = $e.Key; bytes = (Get-Item $path).Length }
  } catch {
    $result.failed += @{ path = $e.Key; error = "$_" }
  }
}
# Structured receipt — the agent parses this, no scraping
$result | ConvertTo-Json -Depth 4 -Compress
if ($result.failed.Count -gt 0) { exit 1 }
PS1

# 2) Run it — one process, real exit code, JSON receipt on stdout
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .tmp/write-artifacts.ps1
```

Why this is better:

- `-File` takes the script verbatim — **zero quoting interaction** with the calling shell.
- `-NoProfile` skips user profile load; `-NonInteractive` guarantees it can never block on a
  prompt (a hung prompt is indistinguishable from a hung agent).
- `$ErrorActionPreference = 'Stop'` turns silent non-terminating errors into catchable ones.
- The **JSON receipt** is the persistence proof required by Regra 13 — `artifacts_confirmed` is
  measured, never declared.
- Exit code is meaningful, so the retry protocol can branch on it.

### 3.4 Flags reference

| Flag | Why |
|---|---|
| `-NoProfile` | Skips profile load — saves ~200–400 ms and removes user-env variance |
| `-NonInteractive` | Never prompts; a prompt in an agent context is a deadlock |
| `-ExecutionPolicy Bypass` | Script runs from a temp path with no signature |
| `-File` (not `-Command`) | Verbatim script; no nested quoting |

### 3.5 When *not* to use PowerShell at all

If the step reads files, counts things, validates a schema, or decides something — write it as a
Python util under `utils/` and give it a `--json` flag. It starts 2.6× faster, is unit-testable,
and the agent gets a parseable contract instead of console text. `artifact_gate.py` is the model
to copy.

---

## 4. Calling one Python script N times

### 4.1 The anti-pattern

```
❌ for each of 5 agents:  Bash: python artifact_gate.py --agent <id> --json
```

Measured: **6 401 ms** of process time — but worse, **5 LLM round-trips**, and the orchestrator
naturally processes each result before issuing the next call. That interleaving *is* the Wave 2
serialization (ISSUE-002 § RC-3).

### 4.2 The pattern — one process, batch in, batch out

Give the script a batch mode that takes the whole work-list and returns the whole result set:

```
✅ Bash: python artifact_gate.py --project {p} --wave phase_a_wave2 --json
```

Measured: **1 404 ms**, one round-trip. **4.6× faster**, and the orchestrator physically cannot
interleave because there is nothing to interleave with.

Implemented in
[artifact_gate.py](../../src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py)
(`WAVES` + `check_wave()` + `--wave`). Returns a `dispatch_manifest` so the orchestrator can
assert `len(dispatched) == expected_count` before the first COLLECT.

### 4.3 Generalised recipe

When you find yourself calling a script per item:

1. **Accept a manifest** — `--wave <name>`, `--agents a,b,c`, or `--manifest work.json` (stdin
   for large lists).
2. **Return a keyed result object**, never a flat log — `{"agents": {...}, "dispatch": [...]}`.
3. **Aggregate the exit code** — `0` only if the whole batch is clean; make partial failure
   explicit in the payload rather than in the exit code alone.
4. **Never let an empty result read as success.** `check_wave()` emits
   `SOLUTION_AGENT_UNRESOLVED` and exits non-zero rather than returning `dispatch: []`, which the
   orchestrator would have read as "nothing to do" and skipped Wave 1 entirely.
5. **Keep the per-item path** for retries and remediation — batch mode is for the fan-out, not a
   replacement.

### 4.4 The highest-value application: observability (Finding A)

Every agent currently does:

```
Bash: python src/shared/utils/ntp_time.py            # start   ~2.0 s
  ... agent work ...
Bash: python src/shared/utils/ntp_time.py            # end     ~2.0 s
Bash: python src/shared/tools/pipeline_observer.py -p {p} track \
        --agent ... --duration-ms {computed}         # track   ~0.7 s
```

**3 tool calls × 101 dispatchable agents ≈ 300 round-trips per full pipeline run**, of which ~200
exist only to fetch a timestamp.

`pipeline_observer.py track` already accepts `--duration-ms`, `--start-time` and `--end-time`
([pipeline_observer.py:1150-1152](../../src/shared/tools/pipeline_observer.py#L1150-L1152)), and
`ntp_time.py` is a repo module it can import directly.

**Proposed:** add `--stamp-start` / `--stamp-end` so `track` resolves NTP time *in-process*:

```
Bash: python src/shared/tools/pipeline_observer.py -p {p} track --agent X --stamp-start
  ... agent work ...
Bash: python src/shared/tools/pipeline_observer.py -p {p} track --agent X --stamp-end --status completed
```

→ 3 calls become 2, and the 2 NTP round-trips collapse into the calls that already had to happen.
Storing the start marker in the run state removes the third entirely for agents that don't need a
mid-run checkpoint. **Estimated saving: ~100–200 tool calls per full-pipeline run.**

> Not yet implemented — requires a change to `cmd_track` and a coordinated edit across 103 agent
> specs. Recommend doing it with a scripted rewrite plus `agent_registry.py --validate` as the
> guard, not by hand.

---

## 5. F1 → F2 cross-phase analysis

### 5.1 F1 — event-driven, mostly correct

F1 has a real DAG (`dispatch_schedule` in
[orchestrator-asis.md](../../src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md)):
Wave 1 → gate → Wave 2 (5 parallel) → Phase B → Phase C. The declared parallelism was already
right; the defect was runtime serialization caused by the per-agent guard (§4.1). Fixed by
`--wave` + Regra 14.

Remaining F1 opportunity: `doc:FT` and `doc:VC` both run in Wave 2 and both belong to
`ava-asis-documentation`. Phase B then dispatches `doc:RT` (needs FT) and `doc:BRF` (needs VC) as
two more separate dispatches of the *same agent*. That is 4 dispatches of one agent, each paying
full context reconstruction. Worth evaluating a single `documentation` dispatch with an internal
FT→RT / VC→BRF sequence, since the dependencies are internal to that agent's own outputs.

### 5.2 F2 — no wave model at all (Finding B)

`orchestrator-tobe.md` has **24 sequential phases** (0-Pre, 0, 1, 1.4, 1.5, 1.6, 2, 2.5, 2.7, 3,
4, 4.2, 4.3, 4.5, 4.6, 4.61, 5, 5.2, 5.1, 6, 6.5, 7, 7.1, 8) and **no `dispatch_schedule`, no
wave, no trigger/event protocol**. Each phase is "Invocar → aguardar → próxima fase".

Some of that chain is genuine — `wave-model.json` is written in Fase 2.7, updated with FP/SP in
Fase 3, and read in Fase 4. That is a real data dependency and must stay serial.

But several late phases gate **only on Fase 1** artifacts:

| Phase | Declared entry gate | Actually waits for |
|---|---|---|
| 5.2 — Regras de Negócio | `bounded-context-map.md` + `architecture-blueprint.md` (Fase 1) | Fases 2 → 5 |
| 6 — User Journeys | `architecture-blueprint.md` + `bounded-context-map.md` (Fase 1) | Fases 2 → 5.1 |
| 6.5 — Design System | `ava-tobe-adr` completed (Fase 0) | Fases 1 → 6 |

**All three could dispatch in parallel immediately after Fase 1**, yet they sit behind ten
intervening phases (2, 2.5, 2.7, 3, 4, 4.2, 4.3, 4.5, 4.6, 4.61). Fase 6.5 only needs Fase 0.

Similarly in the design block: Fase 1.5 depends on 1.4 (`sql-strategy`), but **Fase 1.6
(Security Design) depends only on Fase 1** — it can run parallel to the 1.4 → 1.5 chain.

**Recommendation:** port F1's `dispatch_schedule` + Wave Guard to F2:

```yaml
dispatch_schedule:
  wave_design:            # after Fase 1 ✓
    mode: on_event
    rules:
      - { trigger: "fase1✓", dispatch: [db-policy, security-design, docs:RN, user-journeys], blocking: true }
      - { trigger: "adr✓",   dispatch: [design-system], blocking: false }
  wave_planning:          # genuinely serial — wave-model.json chain
    mode: sequential
    rules:
      - { trigger: "db-policy✓", dispatch: db-design }
      - { trigger: "fase2.5✓",   dispatch: wave-composition }   # 2.7
      - { trigger: "2.7✓",       dispatch: measure-size }       # 3
      - { trigger: "3✓",         dispatch: migration-plan }     # 4
```

Then add `WAVES["wave_design"]` to a `tobe-architecture/utils/artifact_gate.py` (F2 has no
equivalent util today — F1's is module-local) so F2 gets the same one-call batched guard.

### 5.3 Shared: the F1→F2 handoff

F2's entry gate (`orchestrator-tobe.md:199`) requires `bounded-context-map.md`,
`architecture-blueprint.md` and `db-analysis-report.md`. The last one was affected by the path
bug in §6.1 — F2 could have been reading a "missing" F1 artifact that was present all along.

---

## 6. Path-mismatch bugs found during this analysis

### 6.1 `db-analysis-report.md` — FIXED

`artifact_gate.py` checked `asis/db-analysis-report.md` (root). Every other source —
[output-paths.md:109](../../src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md#L109),
`db-analyzer.md:258`, `module.yaml:169`, `build_summary_comprehensive.py:210`, `solution-delphi.md:1177`
— writes it to `asis/db/db-analysis-report.md`.

**Effect:** the Dispatch Guard could never confirm `ava-asis-db-analyzer`, so it was re-dispatched
on every COLLECT iteration — the RC-2 retry-storm pattern, on every run. Verified: after the fix,
`processaERP-11` reports `✅ ava-asis-db-analyzer → SKIP (artefatos presentes)`; the 3 files were
on disk the whole time.

**Status:** fixed in `artifact_gate.py` (`ARTIFACT_CONTRACTS` + `F1_OUTPUT_CONTRACT`).

### 6.2 `wave-model.json` — OPEN

Across F2, **19 references** use `outputs/tobe/migration/wave-model.json` (including the writer,
`migration-plan-tobe.md:298`). **One** uses `outputs/tobe/wave-model.json`:

- [orchestrator-tobe.md:1312](../../src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md#L1312)
  — Fase 7 (Azure Infra Estimator) input table, priority 4.

**Effect:** Fase 7 looks for the wave model at a path nothing writes, so it degrades or skips with
a missing-input warning while the file exists one directory down.

**Fix:** change `outputs/tobe/wave-model.json` → `outputs/tobe/migration/wave-model.json` at
`orchestrator-tobe.md:1312`.

---

## 7. Prioritised backlog

| # | Action | Effort | Payoff | Status |
|---|---|---|---|---|
| 1 | `artifact_gate.py --wave` + Regra 14 (F1) | done | 4.6× on wave guard, kills RC-3 | ✅ |
| 2 | `db-analysis-report.md` path fix | done | ends db-analyzer retry storm | ✅ |
| 3 | `wave-model.json` path fix (§6.2) | 1 line | unblocks Fase 7 | ⬜ |
| 4 | `track --stamp-start/--stamp-end` (§4.4) | M | ~100–200 fewer calls/run | ⬜ |
| 5 | F2 `dispatch_schedule` + wave guard (§5.2) | L | 3 phases off the critical path | ⬜ |
| 6 | `-File` + JSON receipt in batch-write-protocol (§3.3) | S | removes quoting-failure class | ⬜ |
| 7 | Consolidate 4× `documentation` dispatches (§5.1) | M | 3 fewer context rebuilds | ⬜ |

---

## 8. Verification

```powershell
# Batched guard — must be ~1 call, not 5
python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py `
  --project processaERP-11 --wave phase_a_wave2 --json

# db-analyzer must report SKIP, not DISPATCH
python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py `
  --project processaERP-11 --all | Select-String db-analyzer

# Frontmatter guard (AT-001/002/003)
python src/shared/tools/agent_registry.py --validate

# Full suite
python -m pytest tests/ -q
```

On the next full F1 run, `master-report.md` must contain **no** `DISPATCH_SERIALIZATION` entry and
the Wave 2 manifest must show all eligible agents with dispatch timestamps clustered *before* the
first completion event.

---

## 9. Measurement caveats

- Startup timings are single-host, cold-cache, and include Windows Defender inspection; treat the
  **ratios** (PowerShell ≈ 2.6× Python) as the stable signal, not the absolute ms.
- The tool-call round-trip cost was **not** directly measured here — it is inferred from ISSUE-002's
  observed 34/5/62-minute subagent calls. The claim "round-trip dominates startup" is well
  supported by that evidence, but the specific per-call figure is not established.
- Findings A and B are **analysis, not yet validated by a run**. The estimated savings are derived
  from call-site counts and declared dependency gates, not from an instrumented before/after.
