# Quickstart: Validating Solution Delphi Test Coverage Artifact Mapping

> This is a prose instruction file, not executable code — verification is
> structural/documentary, consistent with specs/007.

## CA01/CA02 — Existence-check-before-invoke logic present

```bash
grep -n "verifique se os 9 artefatos já existem\|SE os 9 arquivos já existem\|SE qualquer um estiver ausente" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if all three phrases are found in Step 0, confirming the agent
checks for existence before deciding whether to invoke the tool, and that
invocation remains mandatory when any file is missing.

```bash
grep -n "na sequência" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if found, confirming the note that the tool produces all 9 files
in one sequenced call (not 9 separate invocations).

## Input Contract has the 9th artifact

```bash
grep -n "09_test_coverage.json" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if this returns 5 matches: the Input Contract table row, two
mentions in Step 0 (existence check + degraded-mode note), and two in the
Step 3 `TestCoverageProfile` subsection.

```bash
grep -c "Todos os 9 acima\|Carregar os 9 artefatos" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if both phrases are found (no leftover "8" references).

## CA03 — New risk flag wired into Migration Readiness

```bash
grep -n "NO_AUTOMATED_TEST_COVERAGE" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md \
  src/modules/ava-fabric-agents/asis-diagnostic/shared/delphi-patterns.md
```

**PASS** if found in both files — `solution-delphi.md` (Step 3, defining
when it's raised) and `delphi-patterns.md` (Migration Readiness flags
list, confirming it reduces the score like every other flag).

## CA04 — Degraded mode is honest (no false negatives)

```bash
grep -n "não reconstruir via Grep\|TestCoverageProfile: indisponível\|omitir o risco" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if found in Step 0's failure branch and/or Step 3's
`TestCoverageProfile` subsection, confirming the agent does not assume
"no tests" just because the AST artifact is unavailable.

## Structural integrity

```bash
python -c "
import re
text = open('src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md', encoding='utf-8').read()
fences = len(re.findall(r'^\`\`\`', text, re.MULTILINE))
print('fences:', fences, '-> balanced' if fences % 2 == 0 else '-> UNBALANCED')
"
```

**PASS** if `balanced`.

## Cross-file version consistency

```bash
grep -n "2.1.0" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
grep -n "ava-asis-solution-delphi" src/shared/tools/pipeline_observer.py src/shared/tools/generate_observability_report.py
```

**PASS** if `solution-delphi.md`'s frontmatter, its FASE OBRIGATÓRIA
`--version` literal, and both tool catalogs all agree on `2.1.0`.

## Tools compile

```bash
python -m py_compile src/shared/tools/pipeline_observer.py src/shared/tools/generate_observability_report.py
```

**PASS** if no output.
