# Quickstart: Validating Solution Delphi AST Consumption

> This is a prose instruction file, not executable code — there is no live
> pipeline run to invoke in this session. All checks below are structural/
> documentary, verifying the file's own content and its consistency with
> dependent docs, per the same limitation already stated in specs/002-006.

## CA01 — AST succeeds: JSON is primary, minimal raw-source reading

```bash
grep -n "Fonte primária" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if this returns matches for Step 1 (Repository Inventory), Step 3
(Business Rules Extractor), and Step 4 Analysis #4 (VCL Lifecycle & UI
Coupling) — each pointing at one of the 8 JSON files instead of a raw
`Glob`/`Grep`/`Read` pass.

```bash
grep -n "Exceção estreita e explícita" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if this returns exactly one match (Step 2, the `.dpr` bootstrap
read) — confirming the only remaining direct raw-source read is explicitly
labeled and scoped to a single small file.

## CA02 — Two previously-unwired JSON files now produce real output

```bash
grep -n "01_business_rules.json" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
grep -n "02_form_business_rules.json" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
grep -n "code-business-rules.md" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
grep -n "FIELD_VALIDATION_IN_UI" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if all four return at least one match.

```bash
grep -n "code-business-rules.md\|docs/business-rules.md" src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md
```

**PASS** if both filenames appear, on different rows, under different agent
sections (`Solution Agent` vs. `Documentation Agent`) — confirming no
naming collision.

## CA03 — AST failure is degraded, not blocked

```bash
grep -n "AST_UNAVAILABLE_DEGRADED_ANALYSIS" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if this returns a match in Step 0, confirming a named flag exists
for the degraded path, distinct from silent equal-footing between the two
paths.

```bash
grep -n "Fallback (SE Step 0" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if this returns a match in Step 1 — confirming the `Glob`-based
fallback still exists and delivery is never hard-blocked by AST failure.

## CA04 — No `.drawio` files are produced

```bash
grep -c "drawio" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if this returns exactly `4` — all 4 are explanatory mentions
(pointing to the downstream `generate_drawio_from_mermaid.py` synthesis
script), not generation instructions.

```bash
grep -n "\.drawio" src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if none of the matched lines contain a `Write`/output-path
instruction — all 4 must be prose notes, not template/skeleton content.

```bash
grep -rn "drawio" src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md
```

**PASS** if every `.drawio` row remaining is annotated `(VB6 only)` and none
appear under the Delphi-specific note at the top of the "Solution Agent
(Delphi/VB)" section.

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

```bash
grep -n "^## " src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
```

**PASS** if `## Input Contract` appears before `## ⚙️ Execution Model`, and
`## Draw.io Templates` no longer appears at all.
