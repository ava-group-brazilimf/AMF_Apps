# Research Notes: Solution Delphi Test Coverage Artifact Mapping

## 1. The wrapper script and external tool already implemented this — confirmed, not assumed

Before making any edits, `run_delphi_ast_analysis.py` (this repo) was read
in full. Its `expected` list (used to gate success/failure of the
extraction) already read:

```python
expected = [f"{i:02d}_{name}.json" for i, name in enumerate(
    ["business_rules", "form_business_rules", "database_rules", "database_schemas",
     "procedures", "integrations", "apis", "code_overview", "test_coverage"], start=1)]
```

— i.e., `09_test_coverage.json` was already part of the wrapper's own
success gate. This meant no change to the wrapper script itself was needed
for this PBI; the gap was entirely in `solution-delphi.md`'s own `##
Input Contract`, which still only documented 8 rows.

## 2. External tool's own design doc found and read in full

`C:\Desenv\repo\tool\ava-fabric-delphi-analyzer\docs\plan_novo_aterfato_test_coverage-json.md`
documents the exact, already-implemented design of `09_test_coverage.json`:

- **Detection strategy**: AST-first (via `DelphiAST`'s XML output — class
  attributes `[TestFixture]`/`[Test]`, method visibility `published`, class
  inheritance from `TTestCase`/`TDUnitXTestFixture`), falling back to regex
  only where AST doesn't cover (e.g., `uses TestFramework`/`DUnitX` framework
  detection, filename patterns like `*Test*.pas`).
- **Auxiliary indicators** (never AST — always regex/glob, since they are
  not Delphi code): manual test docs (`*test*.txt`, `*roteiro*.md`), runner
  configs (`*.dunitx`, `TestInsight*.ini`), CI test stages (`*.yml` gated by
  content containing "test"/"dunit"), test data files (`*fixture*.*`,
  `*mock*.*`).
- **Schema**: `payload.counts` (`test_units`, `test_methods`,
  `test_fixtures`, `manual_test_docs`, `runner_configs`, `ci_test_stages`,
  `test_data_files`, `mode`), `payload.test_findings[]` (`id: "TST-NNN"`,
  `kind`, `detected_via: ast|regex|filename`, `source_ref`),
  `payload.auxiliary_indicators[]` (`id: "TSTX-NNN"`, `category`, `label`,
  `source_ref`).
- **Explicitly identified intended consumer**: the design doc's own author
  found that `ava-asis-test-qa` (`test-qa-asis.md`, v3.0.0, in this repo)
  already implements near-identical test-discovery detection tables
  (field-by-field matches for filename patterns and auxiliary categories),
  confirming `09_test_coverage.json` is the deterministic raw material
  meant to feed that agent's "Test Discovery"/"Test Approach Detection"
  skills — analogous to how `08_code_overview.json.payload.classes` became
  `solution-delphi.md`'s own `ClassRegistry[]`.
- **Explicitly deferred**: integrating with `test-qa-asis.md` was flagged as
  a real risk (both `ava-asis-solution-delphi` and `ava-asis-test-qa` are
  dispatched in parallel/immediate mode from the same orchestrator phase —
  duplicating a "Step 0" tool-invocation in both would race on the same
  output files) and the user of that other repo's session explicitly
  decided **not** to resolve it in that round. This PBI (scoped to
  `solution-delphi.md` only, in this repo) does not touch `test-qa-asis.md`
  and does not need to resolve that race, since `solution-delphi.md`
  already had sole ownership of the Step 0 tool invocation for this agent's
  own purposes before this PBI, unchanged.

## 3. Real sample verified before writing schema documentation

`projects/Meu-ERP-006-AST-LLM-AS-IS-Orchestrator/outputs/asis/delphi-ast-raw/extraction/09_test_coverage.json`
was read directly — a real, already-executed sample (empty
`test_findings`/`auxiliary_indicators` arrays, since that sample project
has no DUnit tests), confirming the envelope structure
(`artifact`/`schema_version`/`project`/`description`/`payload`/`_volatile`)
matches the other 8 artifacts exactly, and that `payload.counts.mode`
(`"ast+regex-fallback"`) follows the same self-reporting convention as the
other files.

## 4. No Grep-based fallback attempted for this artifact — a deliberate, honest scope limit

Every other AST-covered analysis in `solution-delphi.md` has a documented
Grep-based fallback for when Step 0 is unavailable (e.g., `ClassRegistry[]`
falls back to regex class-declaration matching; `BusinessRuleRegistry[]`
falls back to Grep for calculation/validation patterns). For
`TestCoverageProfile`, no such fallback was written — the external tool's
own detection logic (positional XML sibling-attribute association,
propagated visibility down the AST tree, combined with content-gated file
globbing for auxiliary indicators) is materially more involved than a
simple Grep pattern, and reimplementing it inside `solution-delphi.md`
would risk producing a false negative (silently reporting "no tests found"
when tests exist but weren't detected by a cruder regex). The decision was
to state this limitation honestly: in degraded mode, `TestCoverageProfile`
is marked unavailable and the `NO_AUTOMATED_TEST_COVERAGE` risk is
explicitly omitted rather than asserted.

## 5. Check-existence-before-invoke — confirmed safe given the wrapper's all-or-nothing gate

The wrapper script's own success gate (`missing = [name for name in expected
if not (extraction_dir / name).exists()]`) already treats the 9 files (plus
`manifest.json`/`metrics.jsonl` in `compressed/`) as an atomic set — it
only returns exit 0 when all are present. This means `solution-delphi.md`'s
new existence-check ("if all 9 already exist, skip re-invocation") cannot
encounter a realistic partial state (e.g., 8 files present, 1 missing) that
the wrapper itself wouldn't have already flagged as a failure. The check is
still written per-file for clarity, but this is a defensive convention, not
a scenario expected to occur in practice.

## 6. Version bump rationale

MINOR (`2.0.0` → `2.1.0`), not MAJOR: no existing Output Contract artifact
was removed, renamed, or had its schema changed. This is purely additive —
a new input, a new internal derived object (`TestCoverageProfile`), and a
new risk flag enriching an existing output file's content. Consistent with
the SemVer precedent already established in this repo's constitution
(Article X) and applied identically in `specs/007` (that PBI's `.drawio`
removal was correctly MAJOR since it removed existing output files; this
PBI removes nothing).
