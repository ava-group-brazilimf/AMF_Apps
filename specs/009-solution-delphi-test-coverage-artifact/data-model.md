# Data Model: `09_test_coverage.json`

Verified against a real sample at
`projects/Meu-ERP-006-AST-LLM-AS-IS-Orchestrator/outputs/asis/delphi-ast-raw/extraction/09_test_coverage.json`
and the external analyzer's own design doc
(`ava-fabric-delphi-analyzer/docs/plan_novo_aterfato_test_coverage-json.md`).

## Common Envelope

Same envelope as artifacts 01-08 (see `specs/007-solution-delphi-ast-consumption/data-model.md`):

```json
{
  "artifact": "09_test_coverage",
  "schema_version": "0.1.0",
  "project": "AVA Fabric - Legacy Delphi Migration",
  "description": "Cobertura de testes (frameworks DUnit/DUnitX, fixtures, testes e indicadores auxiliares de teste)",
  "payload": { "...": "see below" },
  "_volatile": {
    "generated_at": "<ISO8601>",
    "run_id": "<hex>",
    "analyzer": "delphi_ast_analyzer/0.1.0",
    "source_root": "<absolute path to Delphi repo>"
  }
}
```

## `payload`

### `payload.counts`

| Field | Type | Description |
|---|---|---|
| `test_units` | int | Distinct `.pas` files with at least one test finding (deduplicated by file) |
| `test_methods` | int | Distinct `(file, method_name)` pairs identified as test methods (deduplicated — a method with both `[Test]` attribute and a `published` section is counted once, but both findings remain in `test_findings[]` for traceability) |
| `test_fixtures` | int | Count of `fixture_class` findings (classes inheriting `TTestCase`/`TDUnitXTestFixture` or tagged `[TestFixture]`) |
| `manual_test_docs` | int | Count of `auxiliary_indicators` with `category: "manual_doc"` |
| `runner_configs` | int | Count of `auxiliary_indicators` with `category: "runner_config"` |
| `ci_test_stages` | int | Count of `auxiliary_indicators` with `category: "ci_test_stage"` |
| `test_data_files` | int | Count of `auxiliary_indicators` with `category: "test_data"` |
| `mode` | string | `"ast+regex-fallback"` (or equivalent self-reported mode string, same convention as artifacts 01-08) |

### `payload.test_findings[]`

One entry per detected test signal in actual Delphi source (`.pas`):

| Field | Type | Description |
|---|---|---|
| `id` | string | `"TST-NNNN"` |
| `kind` | enum | `fixture_class` \| `published_test_method` \| `attribute` \| `framework_uses` \| `filename_pattern` |
| `name` | string | Class name, method qualified name, framework unit name, or filename, depending on `kind` |
| `detected_via` | enum | `ast` \| `regex` \| `filename` |
| `source_ref` | object | `{file, line}` (`line` may be `null` for filename-pattern-only findings) |

### `payload.auxiliary_indicators[]`

One entry per non-Delphi test-related file found (never AST — always
glob/regex, since these are not `.pas` source):

| Field | Type | Description |
|---|---|---|
| `id` | string | `"TSTX-NNNN"` |
| `category` | enum | `manual_doc` \| `runner_config` \| `ci_test_stage` \| `test_data` |
| `label` | string | Human-readable label (`"Manual — Documented"`, `"Runner Config"`, `"CI Test Stage"`, `"Test Data"`) |
| `source_ref` | object | `{file, path, line: null}` (`path` relative to `source_root`) |

## Consumption in `solution-delphi.md`

Built into `TestCoverageProfile` in Step 3 (see agent file). Drives a
single derived signal consumed by this agent:

- **Risk `NO_AUTOMATED_TEST_COVERAGE`** — raised when
  `payload.counts.test_units == 0 AND payload.counts.test_methods == 0`.
  Feeds the Migration Readiness Score (`shared/delphi-patterns.md` §"Flags
  de Risco"). No dedicated output file — enriches `architecture-blueprint.md`'s
  existing risk narrative.

Not currently consumed for anything beyond this single risk signal in this
agent — full test-finding/auxiliary-indicator enumeration (e.g., a
dedicated `test-coverage-report.md`) is explicitly out of scope here and
identified (in the external tool's own design doc) as material for
`ava-asis-test-qa` instead.
