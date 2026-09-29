# Quickstart: Validating Pipeline Phase Order Correction

> These agents are prose instruction files (not executable code) — no live
> pipeline run is possible in this session. Verification is structural
> (grep sweeps) and functional-in-isolation (direct CLI tests of the
> observability tools), consistent with every prior PBI in this session.

## CA01 — Phases appear in the correct order everywhere

```bash
cd imfai-ava-fabric-apps-agents
grep -rEln "F3 ?[—–-] ?(Stack|Tech Stack)|F4 ?[—–-] ?(Prot[oó]tipo|Prototype)|F6 ?[—–-] ?(Entreg[aá]veis|Deliverables)|F7 ?[—–-] ?(DevOps)|F4 ?[—–-] ?QA|F5 ?[—–-] ?Prot" \
  --include="*.md" --include="*.html" --include="*.py" \
  docs .github .specify src 2>/dev/null | grep -v "/specs/"
```

**PASS** if this returns nothing. (`/specs/` is excluded because prior specs'
historical PBI descriptions legitimately quote the old order when describing
what changed.)

```bash
grep -n "F1→F2→F3→F5→F7→F6\|F1, F2, F3, F5, F7, F6" \
  src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
```

**PASS** if the only matches are inside `## Changelog` entries for versions
`1.0.0`/`1.1.0` (historical record, correctly left untouched).

## CA02 — Master-orchestrator dispatches Prototype directly, exactly once

```bash
grep -c "DISPATCH @ava-prototype" src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
grep -c "ava-prototype\|prototype-agent" src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md
```

**PASS** if the first returns `1` and the second returns matches only in
explanatory prose (the note added in § Agent Team and § Fase 7.8's
justification), never in a `DISPATCH`/`Invocar` instruction.

```bash
grep -n "### Step 3 — FASE 3: Protótipo" src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
```

**PASS** if found, confirming Prototype is a real top-level step between F2 and F4/Stack.

## CA03 — Summary "Phases & Agents" menu reflects the correct order

```bash
grep -n "num:3\|num:4\|num:6\|num:7" src/modules/ava-fabric-agents/summary/templates/html/summary-template.html | grep "label:"
```

**PASS** if `num:3` shows `"F3 — Protótipo"`, `num:4` shows `"F4 — Stack Tecnológica"`,
`num:6` shows `"F6 — DevOps"`, `num:7` shows `"F7 — Entregáveis"`.

```bash
grep -o "nav('s-f[0-9][a-z-]*'" src/modules/ava-fabric-agents/summary/templates/html/summary-template.html | sort -u > /tmp/nav_targets.txt
grep -o 'id="s-f[0-9][a-z-]*"' src/modules/ava-fabric-agents/summary/templates/html/summary-template.html | sort -u > /tmp/section_ids.txt
diff <(sed "s/nav('//;s/'//" /tmp/nav_targets.txt) <(sed 's/id="//;s/"//' /tmp/section_ids.txt)
```

**PASS** if `diff` produces no output — every sidebar nav target resolves to
an existing section id (no orphaned links after the `f3f4` split and `f6`/`f7` swap).

## Mechanical leaf-agent fixes (37 files)

```bash
grep -rl -- '--phase F3' src/modules/ava-fabric-agents/tech-stack/agents/*.md
grep -rl -- '--phase F7' src/modules/ava-fabric-agents/devops-agents/agents/*.md
grep -rl -- '--phase F6' src/modules/ava-fabric-agents/deliverables/agents/*.md
grep -rl -- '--phase F2' src/modules/ava-fabric-agents/prototype/agents/*.md
```

**PASS** if all four return nothing (old tags fully replaced).

```bash
grep -cl -- '--phase F4' src/modules/ava-fabric-agents/tech-stack/agents/*.md | grep -c ':1'
grep -cl -- '--phase F6' src/modules/ava-fabric-agents/devops-agents/agents/*.md | grep -c ':1'
grep -cl -- '--phase F7' src/modules/ava-fabric-agents/deliverables/agents/*.md | grep -c ':1'
```

**PASS** if these return `13`, `13`, `10` respectively.

## QA prose self-contradiction fixed

```bash
grep -c "F4 QA\|F4 depende\|F4 não pode" src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md
```

**PASS** if `0`.

## Tools compile and resolve all 7 phases correctly

```bash
python -m py_compile \
  src/shared/tools/pipeline_observer.py \
  src/shared/tools/agent_observability.py \
  src/shared/tools/generate_observability_report.py \
  src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py \
  src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py \
  docs/inventory/generate-inventory.py
```

**PASS** if no output (all compile cleanly).

```bash
rm -rf projects/Phase-Order-Test
python src/shared/tools/pipeline_observer.py -p Phase-Order-Test init --run-type full-pipeline --model "Claude Sonnet 4.6"
for p in F1 F2 F3 F4 F5 F6 F7; do
  python src/shared/tools/pipeline_observer.py -p Phase-Order-Test track --agent test-agent-$p --phase $p --version 1.0.0 --status completed --tokens-in 1000 --tokens-out 1000 --duration-ms 100
done
python src/shared/tools/pipeline_observer.py -p Phase-Order-Test dashboard
rm -rf projects/Phase-Order-Test docs/optimization/*Phase-Order-Test*
```

**PASS** if the phase-breakdown table shows, in order: F1 AS-IS Diagnostic,
F2 TO-BE Architecture, F3 Prototype, F4 Stack / Codegen, F5 QA, F6 DevOps,
F7 Deliverables — no `KeyError`, no missing phase.

## Azure DevOps work-items doc integrity

```bash
grep -oE "^[0-9]+\." docs/azure-devops-workitems-revisao-agentes.md | tr -d '.' | tr '\n' ' '
```

**PASS** if output is exactly `1 2 3 ... 42` (sequential, no gaps, no
duplicates — confirms moving Prototype's item earlier didn't corrupt the
numbering).
