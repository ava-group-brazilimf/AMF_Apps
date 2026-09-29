# Implementation Plan: Business Rules Full-Coverage Catalog

**Branch**: `028-business-rules-full-coverage-catalog` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)

## Summary

Move the 100%-coverage guarantee for AS-IS business rules off the LLM agent and onto a
**deterministic post-filter utility** that enumerates every rule from the compressed AST
artifacts into a lossless `business-rules-catalog.json`. The utility runs in the
post-extraction pipeline (mirroring `module_partitioner.py`), asserts count parity, and
fails loudly on mismatch. `business-rules.md` is repositioned as a curated human summary
that points to the catalog; downstream coders read the catalog as the authoritative rule set.

## Technical Context

**Language/Version**: Python 3.13 (stdlib `csv`, `json`, `uuid`, `pathlib`; `pyyaml`)
**Primary Dependencies**: none new — reuses the `utils/` convention of `module_partitioner.py`
**Storage**: files — reads `outputs/asis/delphi-ast-raw/compressed/{01,02}_*.json`; writes `outputs/asis/docs/business-rules-catalog.json`
**Testing**: manual/CLI verification (parity assertion, spot-checks) — no test harness in this module
**Project Type**: CLI utility + agent/contract markdown edits
**Scale/Scope**: ~5k rules per project (processaERP-005: 4254 code rules + 801 form validations)
**Constraints**: deterministic (no `Date.now`/random in logic beyond a generated `trace_id`/timestamp); UTF-8 on Windows

## Constitution Check

- **Art. I (no hardcoded versions)**: PASS — no tech versions embedded.
- **Art. II (agent frontmatter/output contract)**: PASS — `documentation-asis.md` version bumped 2.0.0→3.0.0; new output listed.
- **Art. V (Portuguese agent body)**: PASS — agent edits and utility docstrings/logs in pt-BR.
- **Art. IV (module.yaml)**: N/A — utilities are not registered (consistent with `module_partitioner.py`/`sql_ir_generator.py`).

## Project Structure

```text
src/modules/ava-fabric-agents/asis-diagnostic/
├── utils/
│   ├── business_rules_catalog_generator.py   # NEW — deterministic decoder + catalog + parity
│   └── run_delphi_ast_analysis.py            # MODIFIED — Step 0.7 + --skip-business-rules-catalog
├── agents/
│   └── documentation-asis.md                 # MODIFIED — v3.0.0, RN catalog-first, output contract
└── shared/
    ├── artifact-size-governance.md           # MODIFIED — "Completude vs. Tamanho"
    └── parser-contracts.md                   # MODIFIED — catalog schema + parity invariants

src/modules/ava-fabric-agents/tech-stack/agents/
├── coder-dotnet-backend.md                   # MODIFIED — Input Contract prefers catalog
├── coder-go-backend.md                       # MODIFIED
├── coder-java-backend.md                     # MODIFIED
├── coder-python-backend.md                   # MODIFIED
└── coder-angular-frontend.md                 # MODIFIED

specs/028-business-rules-full-coverage-catalog/
├── spec.md · plan.md · tasks.md              # SpecKit docs
```

**Structure Decision**: Single-utility + markdown-contract edits within the existing
`asis-diagnostic` and `tech-stack` modules. No new module or package.

## Design

### Deterministic utility — `business_rules_catalog_generator.py`
- Decodes `01.payload.rules` (`__buckets:type` → per-`__key` factored CSV; each bucket has its own schema) and `02.payload.forms` (`[N]{schema}` factored CSV; `fields` column is embedded JSON — plain list or `_compaction:table`).
- Uses Python `csv` (RFC-4180) — the encoding matches the module's default dialect; `:json`/`:int` columns coerced per the schema header.
- Emits one rule per `01` record (id = AST id) and one per `02` field with `has_validation` OR non-empty `event_handlers` (id = `FBR-NNNN`); each tagged with `category`, `unit`, `domain_relevant` (UI-noise heuristic, default `{multiedit}`, config-overridable), and a `raw` copy for lossless fidelity.
- **Parity assertions** → exit 1 on mismatch (`from_01 == payload.counts.total`; `from_02 == count(has_validation OR event_handlers)`).

### Pipeline — `run_delphi_ast_analysis.py`
- Step 0.7 after SQL-IR, same `try/except` + `--skip-business-rules-catalog` pattern as Steps 0.5/0.6; lazy import mirrors `sql_ir_generator`.

### Agent — `documentation-asis.md` (RN/BRF)
- RN reworked from "transcribe `payload.rules[]`" to "read `business-rules-catalog.json` as the complete set; curate a domain-relevant summary in `business-rules.md` with a coverage note + catalog pointer". Input/Output contracts, Output Verification, and Pre-Completion checklist updated. Version 3.0.0.

### Contracts
- `artifact-size-governance.md`: new "Completude vs. Tamanho" section — completeness lives in the deterministic JSON catalog, so the LLM `.md` may stay a curated summary under 600 KB.
- `parser-contracts.md`: `business-rules-catalog.json` schema + parity invariants.
- Coder Input Contracts: prefer `business-rules-catalog.json`; `business-rules.md` is fallback-only.

## Complexity Tracking

No constitution violations — no entries required.
