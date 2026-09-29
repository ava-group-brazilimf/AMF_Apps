---
description: "Task list for Business Rules Full-Coverage Catalog"
---

# Tasks: Business Rules Full-Coverage Catalog

**Input**: Design documents from `/specs/028-business-rules-full-coverage-catalog/`

**Prerequisites**: plan.md, spec.md

**Tests**: No automated test harness exists in this module; verification is CLI/manual
(parity assertion + spot-checks), captured in Phase 5.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = 100% coverage; US2 = missing/empty AST; US3 = parity gate

---

## Phase 1: Foundational (Deterministic Utility) 🎯 MVP-critical

**Purpose**: The lossless enumerator that all downstream value depends on.

- [x] T001 [US1] Create `src/modules/ava-fabric-agents/asis-diagnostic/utils/business_rules_catalog_generator.py` — class `BusinessRulesCatalogGenerator` mirroring `module_partitioner.py` (CLI `--project`/`--compressed-dir`/`--docs-dir`, UTF-8 stdout, pt-BR logs).
- [x] T002 [US1] Implement decoder for `01.payload.rules` — `__buckets:type` → per-`__key` factored CSV blocks (per-bucket schema; `:json`/`:int` coercion).
- [x] T003 [US1] Implement decoder for `02.payload.forms` — `[N]{schema}` factored CSV; normalize `fields` (plain list AND `_compaction:table`); detect `has_validation` OR non-empty `event_handlers` (incl. flattened `event_handlers.OnClick`).
- [x] T004 [US1] Emit catalog rules — `id`/`ast_ref`/`category`/`unit`/`method`/`target`/`expression`/`source`/`domain_relevant`/`raw`; `FBR-NNNN` ids for form validations; UI-noise heuristic (`_DEFAULT_UI_UNITS`, config override `business_rules_ui_units`).
- [x] T003b [US3] Implement parity assertions (`from_01 == payload.counts.total`; `from_02 == expected`) → exit 1 with `❌ PARIDADE` log on mismatch.
- [x] T005 [US1] Write `business-rules-catalog.json` (`generated_at`, `project`, `trace_id`, `source_artifacts`, `counts{total,from_01,from_02_validations,by_category,domain_relevant,ui_component}`, `rules[]`).

**Checkpoint**: `python business_rules_catalog_generator.py --project processaERP-005` → exit 0, 5055 rules.

---

## Phase 2: Pipeline Integration (US1)

- [x] T006 [US1] `run_delphi_ast_analysis.py` — add `skip_business_rules_catalog` param, Step 0.7 (lazy import + `try/except`, after SQL-IR), and `--skip-business-rules-catalog` CLI flag; thread through `main()`.

**Checkpoint**: `--help` shows the flag; catalog produced automatically after partitioner/SQL-IR.

---

## Phase 3: Agent Reposition (US1 / US3)

- [x] T007 [US1] `documentation-asis.md` — bump frontmatter to `3.0.0`; update `description`.
- [x] T008 [US1] Rewrite § "Trigger RN" to **Catalog-first Protocol** (read catalog; defensive re-invoke; curated summary with mandatory coverage note + catalog link).
- [x] T009 [US1] Add catalog to Input Contract + Output Contract; update the RN "Catalog-first" note.
- [x] T010 [US3] Update Output Verification + Pre-Completion checklist to assert catalog existence/parity and the coverage-note invariant (remove the old "transcribe all `payload.rules[]`" item).

---

## Phase 4: Contracts & Downstream Consumers (US1)

- [x] T011 [P] [US1] `artifact-size-governance.md` — add "Completude vs. Tamanho" (completeness in deterministic JSON; curated `.md` under 600 KB).
- [x] T012 [P] [US1] `parser-contracts.md` — document `business-rules-catalog.json` schema + parity invariants.
- [x] T013 [P] [US1] Coder Input Contracts prefer the catalog: `coder-dotnet-backend.md`, `coder-go-backend.md`, `coder-java-backend.md`, `coder-python-backend.md`, `coder-angular-frontend.md`.

---

## Phase 5: Verification & Docs

- [x] T014 [US1] Run generator on processaERP-005; confirm `counts.from_01 == 4254`, `total == 5055`, unique ids.
- [x] T015 [US1] Spot-check BR-0730 (GetEstqDspn), BR-0739 (GetSitTrb), BR-0743 (GetVlrCub) present with correct `source`/`expression`; MultiEdit rules `domain_relevant: false`.
- [x] T016 [US3] Corrupt `payload.counts.total` and confirm generator exits 1.
- [x] T017 [US1] Regression: `parse_biz_rules()` from `build_summary_comprehensive.py` parses `business-rules.md` (8 curated BRs) with no error — no Summary regression.
- [x] T018 [US1] Author SpecKit docs (`spec.md`, `plan.md`, `tasks.md`).

---

## Phase 6: Domain-Rules Markdown Enumeration (follow-up — US1)

**Context**: User requested the domain rules also enumerated in Markdown (not only JSON).

- [x] T019 [US1] Extend `business_rules_catalog_generator.py` — `_write_domain_markdown()`: emit the `domain_relevant == true` rules (Formato B, `## Domain: <unit>` tables) as `business-rules-part{N}.md`, partitioned under a 500 KB/part budget; UI-noise rules stay in the catalog only.
- [x] T020 [US1] Verify on processaERP-005 — 4912 domain rows across 292 `## Domain` sections in `business-rules-part1.md` (472 KB, single part); BR-0730/0739/0743 present.
- [x] T021 [US1] Document part files — `documentation-asis.md` (Output Contract 2c + coverage-note template), `parser-contracts.md` (part-file format), coverage note in the generated `business-rules.md` points to `business-rules-part1.md`.

---

## Dependencies & Execution Order

- Phase 1 (utility) blocks everything.
- Phase 2 (pipeline) depends on Phase 1.
- Phase 3 (agent) depends on the artifact contract from Phase 1.
- Phase 4 tasks are parallel `[P]` (different files) once Phase 1 defines the schema.
- Phase 5 verifies end-to-end.

## Notes

- Utility is deterministic — no LLM in the enumeration path. This is the core fix.
- `module.yaml` unchanged (utilities are not registered — consistent with `module_partitioner.py`).
- T017 remains open: run the Summary build to confirm no downstream `.md` parsing regression.
