# Quickstart: Validating Model-Aware Observability

## CA01/CA02/CA03 — Cost varies correctly by model, with safe fallback

```bash
rm -rf projects/Model-Test-Project
for model in "Claude Sonnet 4.6" "Claude Opus 4.6" "GPT-4.1" "Gemini 2.5 Pro" "SomeUnknownModelXYZ" ""; do
  python src/shared/tools/pipeline_observer.py -p Model-Test-Project init --run-type standalone --model "$model" >/dev/null
  python src/shared/tools/pipeline_observer.py -p Model-Test-Project track --agent test-agent --phase F1 --version 1.0.0 --status completed --tokens-in 100000 --tokens-out 100000 --duration-ms 1000 --model "$model"
done
rm -rf projects/Model-Test-Project
```

**PASS** if the resulting `cost_usd` values are, in order:
`1.8, 9.0, 1.25, 0.625, 1.8, 1.8` (the last two fall back to the Sonnet-tier
default rate).

## CA04 — Mixed models within the same pipeline run

```bash
rm -rf projects/Meu-ERP-001/outputs/observability
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init --run-type full-pipeline --model "Claude Sonnet 4.6"
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-asis-orchestrator --phase F1 --version 2.18.1 --model "Claude Sonnet 4.6" --status completed --tokens-in 50000 --tokens-out 30000 --duration-ms 374000
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-tobe-orchestrator --phase F2 --version 2.2.0 --model "Claude Opus 4.6" --status completed --tokens-in 20000 --tokens-out 15000 --duration-ms 120000
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report
python -c "
import json
s = json.load(open('projects/Meu-ERP-001/outputs/observability/pipeline-run-state.json'))
for a, d in s['agents'].items():
    print(a, d['model'], d['cost_usd'])
"
```

**PASS** if `ava-asis-orchestrator` shows `Claude Sonnet 4.6` / `0.6` and
`ava-tobe-orchestrator` shows `Claude Opus 4.6` / `1.425`.

**Cleanup**:
```bash
rm -f docs/optimization/agent-observability-Meu-ERP-001-*.xlsx docs/optimization/agent-observability-Meu-ERP-001-*.json docs/optimization/observability-report-Meu-ERP-001-*.md
rm -rf projects/Meu-ERP-001/outputs/observability
```

## CA05 — No hardcoded model literal remains in any agent file

```bash
grep -rl '\-\-model "Claude Opus 4\.6"' src/modules/ava-fabric-agents --include='*.md'
```

**PASS** if this returns no results.

```bash
grep -rl '{modelo_atual}' src/modules/ava-fabric-agents --include='*.md' | wc -l
```

**PASS** if this returns `97`.

## CA06 — Fence balance across all touched files

```bash
python -c "
import re
from pathlib import Path
agents_root = Path('src/modules/ava-fabric-agents')
bad = []
for f in agents_root.glob('**/agents/**/*.md'):
    text = f.read_text(encoding='utf-8')
    if '{modelo_atual}' not in text:
        continue
    fences = len(re.findall(r'^\`\`\`', text, re.MULTILINE))
    if fences % 2 != 0:
        bad.append((str(f), fences))
print(bad)
"
```

**PASS** if the only result is `solution-vb.md` (pre-existing, unrelated —
confirmed present in git `HEAD`, see `specs/005/research.md` §5).
