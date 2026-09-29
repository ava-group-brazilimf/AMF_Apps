# Quickstart: Validating Agent Pipeline Observability

> This is NOT a CLI reference — see `src/shared/tools/README.md` for full
> command syntax. This file maps each acceptance scenario (spec.md §5) to one
> concrete command and its PASS/FAIL criterion, for validating the
> already-shipped implementation.

All commands run from the repo root. Examples use the real on-disk sample
project `Meu-ERP-001` (not `Meu-ERP`, which does not exist).

---

## CA01/CA02/CA03 — Nominal run produces a 4-sheet Excel with the correct schema

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init --run-type full-pipeline --model "Claude Opus 4.6"

python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track \
  --agent ava-asis-orchestrator --phase F1 --version 2.18.0 \
  --status completed --tokens-in 50000 --tokens-out 30000 --duration-ms 374000

python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report
```

```bash
python -c "
from openpyxl import load_workbook
import glob
f = sorted(glob.glob('docs/optimization/agent-observability-Meu-ERP-001-*.xlsx'))[-1]
wb = load_workbook(f)
print(wb.sheetnames)
print([c.value for c in wb['Agent Metrics'][1]])
"
```

**PASS** if `sheetnames == ["Agent Metrics", "Pipeline Summary", "Phase Breakdown", "Token Analytics"]`
and the header row equals `["Run ID", "Data/Hora", "Agent Name", "Phase", "Versão", "Tokens IN", "Tokens OUT", "Tokens Total", "Duration (ms)", "Cost (USD)", "Status", "Model", "Run Type"]`.

---

## CA04/CA05 — Failed agent is still tracked

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track \
  --agent ava-stack-build-validator --phase F3 --version 2.3.0 \
  --status failed --error-detail "TOOLCHAIN_UNAVAILABLE" \
  --tokens-in 8000 --tokens-out 1200 --duration-ms 15000

python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 status
```

**PASS** if the printed state's `agents["ava-stack-build-validator"]` has
`"status": "failed"` and `"error_detail": "TOOLCHAIN_UNAVAILABLE"`, and after
re-running `finalize --auto-report`, the Excel row for that agent is
red-filled and still contributes to the `TOTAL` row.

---

## CA06 — Cost calculation correctness

```bash
python -c "
tokens_in, tokens_out = 50000, 30000
expected = round(tokens_in * 15/1_000_000 + tokens_out * 75/1_000_000, 6)
print('expected:', expected)
"
```

**PASS** if `expected == 3.0` and matches the `cost_usd` value from the CA01
run above for the same token counts.

---

## CA07 — On-demand dashboard before finalization

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 dashboard
```

**PASS** if this prints a progress view (no error) even though `finalize` was
not called yet in this run, showing tracked agents by status and remaining
`AGENT_CATALOG` entries as pending.

---

## CA08 — Import from external JSON (happy path + malformed)

```bash
# Happy path — reuse an existing sample artifact already on disk
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 import-json \
  --input docs/optimization/agent-observability-Meu-ERP-001-9D61EA92.json
```

**PASS** if it prints `{"imported": true, "run_id": "9D61EA92", ...}`.

```bash
# Malformed — missing required keys
echo '{"foo": "bar"}' > /tmp/bad.json
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 import-json --input /tmp/bad.json
```

**PASS** if it exits non-zero and prints
`ERROR: Invalid JSON structure. Expected 'run_id' and 'agents' keys.`

---

## CA09 — Compare two runs

```bash
python src/shared/tools/pipeline_observer.py compare \
  --run-a docs/optimization/agent-observability-Meu-ERP-001-9D61EA92.json \
  --run-b docs/optimization/agent-observability-Meu-ERP-001-B8D6B8DD.json
```

**PASS** if a side-by-side comparison prints without error, showing totals
for both runs and per-agent cost deltas.

---

## CA10 — Known gap: inline wiring absence (negative check)

```bash
grep -n "0\.4b\|7\.0b" src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
```

**PASS (documents the gap correctly) if this returns matches ONLY inside the
`## ⚙️ Pipeline Observability Integration` appendix (around lines 812–863),
and NOT inside `### Step 0 — Pre-flight` (lines 259–304) or `### Step 7 —
Pipeline Completion Gate` (lines 645–674).** This confirms the integration is
documented but not inlined into the executable steps — see research.md §3.

```bash
grep -n "pipeline_observer\|agent_observability" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/*.md \
  src/modules/ava-fabric-agents/tobe-architecture/agents/*.md \
  src/modules/ava-fabric-agents/tech-stack/agents/*.md \
  src/modules/ava-fabric-agents/qa-agents/agents/*.md 2>/dev/null
```

**PASS (documents the gap correctly) if this returns zero matches** —
confirming no phase orchestrator or leaf agent references the observability
tool.
