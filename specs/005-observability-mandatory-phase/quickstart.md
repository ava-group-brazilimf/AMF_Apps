# Quickstart: Validating the Mandatory Phase Rollout

## CA01 — Coverage and structural integrity across all touched files

```bash
python -c "
import re
from pathlib import Path

agents_root = Path('src/modules/ava-fabric-agents')
total = 0
bad_fence = []
no_bash = []
for f in agents_root.glob('**/agents/**/*.md'):
    text = f.read_text(encoding='utf-8')
    if 'FASE OBRIGATÓRIA' not in text:
        continue
    total += 1
    fences = len(re.findall(r'^\`\`\`', text, re.MULTILINE))
    if fences % 2 != 0:
        bad_fence.append((str(f), fences))
    if 'pipeline_observer.py -p {project_name} track' not in text:
        no_bash.append(str(f))

print('total files with FASE OBRIGATÓRIA:', total)
print('unbalanced fences:', bad_fence)
print('missing the actual track command:', no_bash)
"
```

**PASS** if `total == 97`, `no_bash == []`, and `bad_fence` contains only
`solution-vb.md` (pre-existing, unrelated — confirmed in `research.md` §5).

## CA02 — The 3 previously severely-misplaced files now anchor correctly

```bash
grep -n "^## \|FASE OBRIGATÓRIA" src/modules/ava-fabric-agents/asis-diagnostic/agents/baseline-test-generator-asis.md | grep -B2 "FASE OBRIGAT"
grep -n "^### \|FASE OBRIGATÓRIA" src/modules/ava-fabric-agents/qa-agents/agents/behavior-mapping-agent.md | grep -B2 "FASE OBRIGAT"
grep -n "FASE OBRIGATÓRIA" src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md
```

**PASS** if each shows the `FASE OBRIGATÓRIA` heading immediately preceded by
`## Completion Signal` / `### STEP 6 — COMPLETION-SIGNAL` respectively (and,
for the angular file, near line ~3104 of ~3117, not line 166).

## CA03 — Tool genericity (works for any project name)

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init --run-type standalone --model "Claude Opus 4.6"
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-asis-orchestrator --phase F1 --version 2.18.1 --status completed --tokens-in 50000 --tokens-out 30000 --duration-ms 374000
cat projects/Meu-ERP-001/outputs/observability/ava-asis-orchestrator/metrics.json

python src/shared/tools/pipeline_observer.py -p Some-Other-Project-Name init --run-type standalone --model "Claude Opus 4.6"
python src/shared/tools/pipeline_observer.py -p Some-Other-Project-Name track --agent ava-qa-orchestrator --phase F5 --version 1.2.1 --status completed --tokens-in 1000 --tokens-out 500 --duration-ms 5000
ls projects/Some-Other-Project-Name/outputs/observability/
```

**PASS** if both projects produce correctly isolated per-agent output —
confirms the tool is not hardcoded to any specific project.

**Cleanup afterward**:
```bash
rm -rf projects/Meu-ERP-001/outputs/observability
rm -rf projects/Some-Other-Project-Name
```

## CA04 — Honest environmental limitation (documentation check, not a functional test)

```bash
grep -c "live tool execution\|Environment requirement" src/shared/tools/README.md
grep -c "Environment requirement\|Role of this document" src/modules/ava-fabric-agents/shared/observability-self-report.md
```

**PASS** if both are ≥ 1 — confirms the environmental constraint is
documented, not silently omitted.

## The real acceptance test (cannot be run from this session)

The only test that fully closes this out is: invoke an actual agent (e.g.
`ava-asis-orchestrator`) through whatever surface you normally use, in a mode
with live tool-calling active (GitHub Copilot Agent Mode with terminal
auto-approval, or Claude Code with Bash permission granted), and confirm
`projects/{your_project}/outputs/observability/` appears with real content.
If it still doesn't, the next thing to check is the invocation mode itself,
not the agent `.md` files — per the documented environmental constraint.
