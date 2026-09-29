# Quickstart: Validating Agent Self-Observability

All commands run from the repo root.

---

## CA01 — Standalone invocation fallback (manual read-through)

```bash
grep -n -A5 "## 2. Standalone" src/modules/ava-fabric-agents/shared/observability-self-report.md
```

**PASS** if the fallback (`init --run-type standalone` then retry `track`
once) is documented.

---

## CA02 — Nested-dispatch coverage (security sub-agents)

```bash
grep -l "observability-self-report" src/modules/ava-fabric-agents/asis-diagnostic/agents/security/*.md | wc -l
```

**PASS** if this returns `8` (all security sub-agents instrumented, even
though neither `ava-asis-security-orchestrator` nor `ava-asis-orchestrator`
tracks them externally).

---

## CA03 — Per-agent isolation

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init --run-type standalone --model "Claude Opus 4.6"
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-asis-solution-delphi --phase F1 --version 1.4.0 --status completed --tokens-in 12000 --tokens-out 8000 --duration-ms 45000
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-devops-ci --phase F7 --version 1.2.0 --status completed --tokens-in 5000 --tokens-out 3000 --duration-ms 20000

cat projects/Meu-ERP-001/outputs/observability/ava-asis-solution-delphi/metrics.json
cat projects/Meu-ERP-001/outputs/observability/ava-devops-ci/metrics.json
```

**PASS** if each file contains only its own agent's data (`"agent":
"ava-asis-solution-delphi"` vs `"agent": "ava-devops-ci"`), with no
cross-contamination.

---

## CA04 — Backward compatibility with existing master-orchestrator tracking

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 status
```

**PASS** if `state.agents` still contains both agents tracked above under the
shared aggregate state — i.e., the pre-existing PBI-002 behavior (shared
state file) is unchanged, and the new per-agent files (CA03) exist
*alongside* it, not instead of it.

---

## CA05 — Failure isolation (manual read-through)

```bash
grep -n -A5 "## 3. Failure Isolation" src/modules/ava-fabric-agents/shared/observability-self-report.md
```

**PASS** if it explicitly states observability failures must never block or
fail the agent's own task.

---

## CA06 — Exclusion correctness (db-analyzer skills)

```bash
grep -L "observability-self-report" src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/skills/*.md
```

**PASS** if this lists all 4 files (i.e., `grep -L` = "files NOT containing
the pattern" — none of the 4 skill files should have the reference).

```bash
grep -l "observability-self-report" src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md
```

**PASS** if this returns the file itself — the parent `db-analyzer.md` IS
instrumented even though its 4 skill sub-files are not.

---

## Whole-suite coverage and link-integrity check

```bash
python -c "
import re
from pathlib import Path

agents_root = Path('src/modules/ava-fabric-agents')
shared_file = agents_root / 'shared' / 'observability-self-report.md'
count = 0
broken = []
for f in agents_root.glob('**/agents/**/*.md'):
    text = f.read_text(encoding='utf-8')
    m = re.search(r'observability-self-report\]\(([^)]+)\)', text)
    if not m:
        continue
    count += 1
    target = (f.parent / m.group(1)).resolve()
    if target != shared_file.resolve():
        broken.append(str(f))

print('files referencing @observability-self-report:', count)
print('broken references:', len(broken))
for b in broken:
    print(' -', b)
"
```

**PASS** if it prints `files referencing @observability-self-report: 97` and
`broken references: 0`.

---

## Tool-level regression check (re-run PBI 002's own scenarios)

```bash
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report
python -c "
from openpyxl import load_workbook
import glob
f = sorted(glob.glob('docs/optimization/agent-observability-Meu-ERP-001-*.xlsx'))[-1]
wb = load_workbook(f)
print(wb.sheetnames)
"
```

**PASS** if this still prints the same 4 sheets as PBI 002
(`["Agent Metrics", "Pipeline Summary", "Phase Breakdown", "Token Analytics"]`)
— confirming the `cmd_track` extension did not regress the existing Excel
export path.
