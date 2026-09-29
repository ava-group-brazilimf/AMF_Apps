# Quickstart: Validating the Activation Fix

## CA01 — Each of the 5 files has exactly one correctly-placed `track` call

```bash
for f in \
  src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md \
  src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md \
  src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md \
  src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md ; do
  echo "=== $f ==="
  grep -c "pipeline_observer.py -p {project_name} track" "$f"
done
```

**PASS** if every file prints `1`.

## CA02 — Fence balance (no orphaned code blocks introduced)

```bash
for f in \
  src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md \
  src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md \
  src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md \
  src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md ; do
  n=$(grep -c '^```' "$f")
  echo "$f: $n fences ($([ $((n % 2)) -eq 0 ] && echo balanced || echo UNBALANCED))"
done
```

**PASS** if every file reports an even fence count.

## CA03 — End-to-end dry run produces real output for the first time

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init --run-type full-pipeline --model "Claude Opus 4.6"
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-master-orchestrator --status completed --tokens-in 400000 --tokens-out 250000 --duration-ms 3540000
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report

cat projects/Meu-ERP-001/outputs/observability/ava-master-orchestrator/metrics.json
python -c "
from openpyxl import load_workbook
import glob
f = sorted(glob.glob('docs/optimization/agent-observability-Meu-ERP-001-*.xlsx'), key=lambda p: __import__('os').path.getmtime(p))[-1]
print(load_workbook(f).sheetnames)
"
```

**PASS** if the per-agent `metrics.json` exists with the right agent name,
and the sheet list is
`["Agent Metrics", "Pipeline Summary", "Phase Breakdown", "Token Analytics"]`.

**Cleanup afterward** (these are test artifacts, not real project data):
```bash
rm -f docs/optimization/agent-observability-Meu-ERP-001-*.xlsx docs/optimization/agent-observability-Meu-ERP-001-*.json docs/optimization/observability-report-Meu-ERP-001-*.md
rm -rf projects/Meu-ERP-001/outputs/observability
```

## CA04 — Negative check: the 92 leaf files are still unfixed (documents the known gap, doesn't pass as "closed")

```bash
grep -c "observability-self-report" src/modules/ava-fabric-agents/qa-agents/agents/scenario-generator-agent.md
```

**Expected**: the reference is still present but still in the old, appendix
location (not fixed by this PBI) — confirming the scope boundary is accurate.
