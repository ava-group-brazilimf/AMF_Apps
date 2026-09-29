# Quickstart: Validating AST-Artifact Consumption Extension + compressed/ Path Fix

> Prose instruction files, not executable code — verification is
> structural/documentary, consistent with every prior PBI this session.

## CA04 — Path correction (verify first, foundation for everything else)

```bash
grep -c "delphi-ast-raw/extraction" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md \
  src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md \
  docs/asis-diagnostic-io-map.md
```
**PASS** if all three return `0`.

```bash
grep -c "delphi-ast-raw/compressed" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```
**PASS** if this returns `17`.

## CA01 — Each of the 5 agents has a working existence-check + primary-source path

```bash
grep -n "SE.*existir.*→ ler\|ast_test_coverage_available\|ast_integrations_available" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/test-qa-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/inventory-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/events-pubsub-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md
```
**PASS** if each file has at least one match describing its existence-check logic.

```bash
for f in test-qa-asis inventory-asis events-pubsub-asis documentation-asis; do
  echo "=== $f ==="; grep -c "Fallback" "src/modules/ava-fabric-agents/asis-diagnostic/agents/$f.md"
done
grep -c "Fallback" src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md
```
**PASS** if every count is > 0 — confirms the pre-existing Glob/Grep procedures were demoted, not deleted.

## CA02 — Fallback is safe and complete (nothing lost)

For each of the 5 files, manually diff the "Fallback" section content
against the pre-PBI original (via `git diff`) — **PASS** if the only
changes inside each Fallback block are heading/indentation, never content
removal.

```bash
git diff --stat src/modules/ava-fabric-agents/asis-diagnostic/agents/test-qa-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/inventory-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/events-pubsub-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md
```
**PASS** if every file shows only additions (`+`) with no unexpected large deletion counts.

## CA03 — Partial-coverage cases stated honestly (not oversold)

```bash
grep -n "Limitação honesta" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/inventory-asis.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/events-pubsub-asis.md
grep -n "Limitação honesta (FT)" src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md
```
**PASS** if each of the 4 files has an explicit limitation note for its
partial-coverage case (`orphan_dfm`, vendor detection, Events/PubSub/IPC
categories, FT navigation edges respectively).

## Fence balance (all 6 touched agent files)

```bash
python -c "
import re
files = [
  'src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md',
  'src/modules/ava-fabric-agents/asis-diagnostic/agents/test-qa-asis.md',
  'src/modules/ava-fabric-agents/asis-diagnostic/agents/inventory-asis.md',
  'src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md',
  'src/modules/ava-fabric-agents/asis-diagnostic/agents/events-pubsub-asis.md',
  'src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md',
]
for f in files:
    text = open(f, encoding='utf-8').read()
    fences = len(re.findall(r'^\`\`\`', text, re.MULTILINE))
    print(f, fences, 'balanced' if fences % 2 == 0 else 'UNBALANCED')
"
```
**PASS** if all 6 report `balanced`.

## Version consistency (all 6 files + 2 observability tool catalogs)

```bash
for f in test-qa-asis inventory-asis events-pubsub-asis documentation-asis solution-delphi; do
  echo "--- $f ---"
  grep "^version:" "src/modules/ava-fabric-agents/asis-diagnostic/agents/$f.md"
  grep -- "--version" "src/modules/ava-fabric-agents/asis-diagnostic/agents/$f.md"
done
grep "^version:" src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md
grep -- "--version" src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md
grep -E "ava-asis-(test-qa|inventory|db-analyzer|documentation)" \
  src/shared/tools/pipeline_observer.py src/shared/tools/generate_observability_report.py
```
**PASS** if every frontmatter `version:` matches its own `--version` literal,
and both tool catalogs agree with the frontmatter versions.

## Tools compile

```bash
python -m py_compile src/shared/tools/pipeline_observer.py src/shared/tools/generate_observability_report.py
```
**PASS** if no output.
