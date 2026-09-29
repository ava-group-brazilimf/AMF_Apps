# Implementation Plan: Client Design Input for Prototype

**Branch**: `039-prototype-design-input` | **Date**: 2026-08-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/039-prototype-design-input/spec.md` and its quality checklist at `specs/039-prototype-design-input/checklists/requirements.md`.

## Summary

Modify the existing `ava-prototype` agent (v1.2.0 → v1.3.0) so it consumes an existing client design source from the configured project-relative design directory, normalizes supported formats into one token model, gives mapped client values strict precedence over generic UX defaults, records unmapped fields and fallback reasons, and never generates a binary `.fig` file. Preserve the mandatory `business-rules.md` pre-flight gate, existing prototype outputs, unmodified `trace_id`, read-only source inputs, and behavior of all other phases.

The implementation remains inside the existing Prototype module. A small internal parser/mapping/sanitization protocol is added to the existing agent instructions; no new agent, skill, or module is created. The Summary integration will be extended only as needed to turn the already-discovered `design-input-traceability.json` file into an explicit Phase 3 source indicator.

## Technical Context

**Language/Version**: Repository-configured agent instruction format and existing Summary Python/HTML generation utilities; no new runtime or technology version is introduced.

**Primary Dependencies**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`, `src/modules/ava-fabric-agents/prototype/module.yaml`, existing `ava-prototype` SKILL.md, `build_summary_comprehensive.py`, Summary HTML template, artifact discovery map, and the repository's existing test tooling.

**Storage**: Project configuration at `projects/{project_name}/context/project-config.yaml`; client design inputs under `projects/{project_name}/inputs/design/`; existing TO-BE design fallback under `projects/{project_name}/outputs/tobe/docs/design-system.md`; Prototype artifacts under `projects/{project_name}/outputs/tobe/prototype/`; Summary artifacts under `projects/{project_name}/outputs/summary/`.

**Testing**: No feature-specific manual verification is required. Preserve existing automated Summary regression tests where present; implementation correctness is governed by the agent contract, deterministic protocol inspection, and repository validation.

**Target Platform**: Offline, file-based execution in the repository's Windows-compatible pipeline tooling. No network access is required for design ingestion.

**Project Type**: Repository-based multi-phase AI-agent pipeline with Markdown agent contracts, generated HTML artifacts, JSON traceability, and Python-based Summary utilities.

**Performance Goals**: Deterministic bounded directory scan and parsing of the selected design file only; no exhaustive project scan beyond the configured design directory and existing prototype inputs. Summary processing continues to use its existing recursive output discovery.

**Constraints**:

- The spec and requirements checklist are authoritative; no behavior outside their scope is introduced.
- `design_input.enabled: false` must prevent scanning the client design directory.
- Discovery without an explicit file follows fixed format priority, then lexical ordering among candidates of equal priority.
- An explicit missing or unsupported file records a configuration gap and does not silently choose another client file.
- Malformed selected input records a parsing limitation and follows the documented fallback.
- Client values override generic/default values only for successfully mapped fields; unmapped categories become traceability gaps.
- Design input is untrusted; executable content and unsafe CSS values are rejected or neutralized before HTML/CSS generation.
- Client input remains byte-for-byte unchanged.
- No binary `.fig` output is produced.
- Existing `business-rules.md` blocking behavior, output paths, `trace_id`, and non-design prototype behavior remain compatible.
- Agent body changes are written in Brazilian Portuguese; this plan is written in English.
- No technology versions, cloud regions, or environment identifiers are hardcoded.

**Scale/Scope**: One existing F3 agent, its existing module metadata, one new Prototype traceability artifact, the design-token generation path, and the Summary's Phase 3 presentation of design provenance. No other phase behavior is changed.

## Constitution Check

_GATE: Must pass before implementation planning and be re-checked after design._

| Gate                                          | Status                               | Evidence / plan                                                                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Configuration-driven (Article I)              | PASS                                 | The design directory and file are resolved from project configuration; no stack, region, or environment value is introduced.                                                                                                                                                                                                                                                              |
| Agent contract standard (Article II)          | PASS                                 | Existing `ava-prototype` identity and output conventions are preserved; `design-input-traceability.json` is the only added output.                                                                                                                                                                                                                                                        |
| Pipeline execution contract (Article III)     | PASS                                 | F3 remains directly dispatched by the master orchestrator; Summary remains the only Summary HTML producer.                                                                                                                                                                                                                                                                                |
| Module registration (Article IV)              | PASS                                 | No new agent/module is created; existing `prototype/module.yaml` is version/output-reviewed and updated consistently.                                                                                                                                                                                                                                                                     |
| Language convention (Article V)               | PASS                                 | Agent frontmatter description and body edits remain pt-BR; this planning artifact is English as required by the template.                                                                                                                                                                                                                                                                 |
| Test-first behavior (Article VI)              | N/A — verification explicitly waived | Per 2026-08-11 decision, no automated test suite (pytest) or manual verification checklist is required for this feature. `ava-prototype` produces a navigable HTML prototype for stakeholder review, not production code; the team explicitly accepted the risk of shipping without a dedicated verification step for this change. This is a deliberate scope decision, not an oversight. |
| Security-first impact (Article VII)           | PASS                                 | No F1 security pipeline is changed; untrusted design input is sanitized, source is read-only, and executable content is excluded.                                                                                                                                                                                                                                                         |
| Observability and traceability (Article VIII) | PASS                                 | `trace_id` remains unchanged and is included in the new traceability artifact and existing execution flow.                                                                                                                                                                                                                                                                                |
| Clean Architecture alignment (Article IX)     | N/A                                  | This is an agent-contract/parser/prototype utility change, not generated application code.                                                                                                                                                                                                                                                                                                |
| Versioning (Article X)                        | PASS                                 | Existing agent version is incremented to v1.3.0 for the optional input and traceability capability; module metadata is synchronized.                                                                                                                                                                                                                                                      |
| Skill/Agent separation (Article XI)           | PASS                                 | Existing SKILL.md routing remains unchanged; behavior changes belong to the existing agent body and Summary implementation.                                                                                                                                                                                                                                                               |

**Gate result**: PASS. No constitutional violation requires a complexity exception.

## Repository Findings and Design Decision

1. `prototype-agent.md` currently treats `outputs/tobe/docs/design-system.md` as an optional input and extracts `design-tokens.json` from it. It has no `design_input` configuration, client input directory scan, supported-format parser, or design provenance artifact.
2. `prototype/module.yaml` is still v1.2.0 and lists the existing five prototype files. It must become v1.3.0 and list `design-input-traceability.json` without removing existing entries.
3. Summary already recursively discovers every file below `outputs/tobe/prototype/` through `build_file_tree()` and `list_prototype_chips()`. Therefore the new JSON will already be visible in the file tree/chip inventory without a new discovery mechanism.
4. Existing `artifact-map.yaml` has fixed prototype entries for `index.html`, `demo-script.md`, and `figma-spec.md`; it is not sufficient by itself to provide the new source label. The plan therefore adds explicit traceability loading in the Summary builder and a small template display field in the F3 section. The recursive discovery remains the source of file inventory; the explicit display consumes the new JSON only when present and shows a documented unavailable/legacy state otherwise.
5. No feature-specific automated or manual verification suite is required; existing repository Summary tests remain unchanged and continue to run where configured.

## Architecture and Data Flow

```text
project-config.yaml
  └─ design_input.enabled/path/file
        │
        ▼
ava-prototype pre-flight
  ├─ mandatory business-rules gate (unchanged)
  └─ client design resolver
       ├─ disabled → fallback resolver
       ├─ explicit file → validate exact file only
       └─ discovery → priority + lexical tie-break
              │
              ▼
       format parser
       ├─ Figma JSON export
       ├─ W3C Design Tokens JSON
       ├─ CSS variables
       ├─ Markdown guide
       └─ SCSS variables
              │
              ▼
       normalized design token model
              │
       sanitization + allow-list
              │
       client precedence merge over generic/default tokens
              │
              ├─ index.html / design-tokens.json / existing prototype artifacts
              └─ design-input-traceability.json
                                               │
                                               ▼
                              Summary recursive discovery + explicit F3 provenance
```

### Internal token model

The parser normalizes supported sources into a single logical model with these categories, matching the spec:

```text
DesignTokens
├── colors: semantic token → sanitized CSS color value
├── typography: family/size/weight/line-height token → sanitized value
├── spacing: semantic scale/token → sanitized CSS length value
├── grid: columns/gutter/container/breakpoint token → bounded numeric/length value
├── components: semantic component → allow-listed component pattern/properties
└── layout: [Figma JSON only] frame/page → screen mapping; node hierarchy → component composition and relative position; populated only when source format = figma-json. Other formats leave this category empty by design (documented format limitation, not a gap).
```

Each normalized value carries internal provenance (`source_field`, category, raw-format family, and mapping status) during processing. The provenance is serialized only through the traceability artifact and the existing `design-tokens.json` contract; arbitrary raw input is never copied into generated HTML.

## Component Design

### 1. Configuration resolver

**Location**: Existing `prototype-agent.md` execution protocol; use the project configuration already loaded by the skill/orchestrator.

**Responsibilities**:

- Resolve optional `design_input` from `projects/{project_name}/context/project-config.yaml`.
- Default absent configuration to enabled discovery with path `inputs/design` relative to the project root, as specified by the feature assumptions.
- Normalize `enabled`, `path`, and optional `file` without changing unrelated configuration.
- Record the effective configured path and whether scanning was skipped.
- Reject path traversal or paths escaping the project root; record a configuration gap and use fallback.

**Non-responsibilities**: It does not inspect arbitrary project files, change project configuration, or infer a different explicit filename.

### 2. Design source resolver and priority detector

**Location**: New deterministic protocol subsection in `prototype-agent.md`; no separate executable helper, agent, skill, or module is introduced.

**Detection order**:

| Priority | Format            | Candidate rules                                             |
| -------: | ----------------- | ----------------------------------------------------------- |
|        1 | Figma JSON export | `*.figma.json`, `figma-export.json`, `design-export.json`   |
|        2 | W3C Design Tokens | `design-tokens.json`, `tokens.json`, `tokens.w3c.json`      |
|        3 | CSS variables     | `*.css`, `variables.css`, `tokens.css`, `design-system.css` |
|        4 | Markdown guide    | `design-guide.md`, `style-guide.md`, `brand-guide.md`       |
|        5 | SCSS variables    | `*.scss`, `_variables.scss`, `_tokens.scss`                 |

The resolver scans only the effective configured directory when enabled and no exact file is configured. It filters candidates by supported filename/extension, chooses the highest-priority format, and applies lexical path ordering for ties. It records candidate count, selected path, priority, and tie-break decision. An explicit `file` is checked directly for existence and supported format; if invalid, the resolver records `explicit_file_missing` or `explicit_file_unsupported` and does not select another client candidate.

### 3. Format parsers

**Location**: New deterministic parser rules in the existing agent body; no separate executable helper is introduced. The rules are verified by textual inspection and behavioral agent tests.

Each parser must return either a normalized token model plus mapping diagnostics or a parse failure with a bounded reason.

- **Figma JSON export**: Read exported variable/style collections and component metadata mapped to colors, typography, spacing, grid, and components. Additionally, read frame/page structure and component hierarchy/position to populate `layout`: each top-level frame corresponding to a business-rule-required screen supplies that screen's section layout and component composition. Ignore binary/plugin execution payloads; never execute plugin code. List unsupported or ambiguous geometry as gaps. Frames without a corresponding business-rule screen are out of scope and recorded as informational low-severity layout gaps.
- **W3C Design Tokens JSON**: Resolve token groups and semantic aliases; map token types and names to the five model categories. Preserve unresolved aliases as gaps rather than guessing.
- **CSS variables**: Parse declaration blocks for custom properties, classify by semantic name/context, and map recognized color, type, spacing, layout/grid, and component tokens.
- **Markdown guide**: Extract explicitly labeled token tables/code declarations and component/style guidance; map only structured, unambiguous values. Narrative guidance without a safe token mapping becomes a gap.
- **SCSS variables**: Parse variable declarations and semantic names using the same mapping vocabulary as CSS; do not evaluate arbitrary Sass expressions or imports.

No conversion between unsupported formats is performed. Parser diagnostics identify the source field/category and reason for an unmapped value.

### 4. Token mapper and precedence merger

**Responsibilities**:

- Normalize aliases and semantic naming into the internal categories.
- Merge client values over the agent's existing internal fallback tokens/defaults.
- Apply precedence per mapped field, not by replacing the entire model when only one category is available.
- Preserve existing UX heuristics for behavioral/accessibility guidance, while preventing those heuristics from overriding client visual tokens/components.
- Mark every expected but unavailable category as an explicit gap; do not silently fill a missing client category and claim it was client-sourced.
- Emit source metadata for each mapped category.
- Layout precedence: when a Figma frame maps to a business-rule-required screen, that frame's section layout/component composition takes precedence over the generic layout heuristic for that screen. `business-rules.md` remains authoritative for functional completeness; if the frame omits a required element, add only that element generically and record a `layout_gap` with medium severity. Screens without a corresponding frame use the fully generic heuristic and record a low-severity informational `layout_gap`.
- Source precedence is strict and field-level: mapped Figma client values and layout take precedence over `design-system.md`; `design-system.md` fills only fields absent from Figma; generic defaults fill only fields absent from both. A later fallback extraction step MUST NOT overwrite a mapped Figma value.

The existing `design-tokens.json` output remains the normalized token artifact consumed by the prototype. Its existing fields remain compatible; where the current schema requires defaults for absent fields, the traceability artifact must distinguish `client`, `fallback-design-system`, and `fallback-generic` values so a default is not represented as a successful client mapping.

### 5. Sanitizer and input security boundary

All extracted values cross a sanitizer before use in HTML/CSS or JSON output.

Rules:

- Parse input as data only; never execute JavaScript, Sass, plugin code, expressions, imports, or embedded markup from design files.
- Escape text for HTML contexts and JSON-serialize values rather than concatenating raw fragments.
- Allow-list CSS properties and value grammars by category: colors, font families/sizes/weights, lengths, line heights, grid counts, and bounded component style values.
- Reject or neutralize `url()` where it can load untrusted content, `@import`, CSS expression syntax, event-handler attributes, `<script>`, HTML/SVG executable content, and control characters.
- Validate color/length/font/grid values against bounded syntax and retain the field as an unmapped gap when validation fails.
- Do not include secrets or arbitrary source content in logs, traceability, or Summary display; record only path, format, field/category, and safe diagnostic reason.
- Compute a source hash before parsing and verify it after parsing/output generation; if changed, record an integrity failure and do not claim byte-preserving consumption. The agent never writes to the source path.

### 6. Deterministic fallback resolver

Fallback is a single ordered decision:

1. `design_input.enabled: false` → skip scan and use `outputs/tobe/docs/design-system.md`.
2. Enabled but no compatible candidate → use `design-system.md`.
3. Explicit file missing/unsupported → use `design-system.md`, with an explicit configuration gap.
4. Selected client file malformed or unsafe → use `design-system.md`, with parse/security limitation.
5. If `design-system.md` is unavailable or cannot be parsed safely → use generic CSS tokens already defined by the agent.

The fallback source is serialized as `fallback-design-system` or `fallback-generic`. The reason is mandatory whenever the selected source is not a valid client file. Fallback must not generate a `.fig` file and must not block the pipeline solely because optional design input is absent or malformed.

### 7. Traceability writer

**Output**: `projects/{project_name}/outputs/tobe/prototype/design-input-traceability.json`.

**Implementation mode**: The parser, mapper, sanitizer, integrity hasher, and traceability writer are implemented as deterministic rules in the Brazilian Portuguese protocol of the existing `prototype-agent.md`; no separate executable helper is introduced.

Minimum schema:

```json
{
  "schema_version": "1.0",
  "agent": "ava-prototype",
  "trace_id": "<unchanged AgentTask.trace_id>",
  "project_name": "<project>",
  "source": "client|fallback-design-system|fallback-generic",
  "configured_path": "inputs/design",
  "detected_file": "<relative path or null>",
  "used_file": "<relative path or null>",
  "format": "figma-json|w3c-design-tokens|css|markdown|scss|none",
  "selection": {
    "mode": "discovery|explicit|disabled|fallback",
    "priority": 1,
    "tie_break": "lexical|not-applicable"
  },
  "mapped_categories": ["colors", "typography"],
  "unmapped_fields": [
    {
      "field": "<safe field name>",
      "category": "grid",
      "reason": "unsupported mapping"
    }
  ],
  "fallback_reason": null,
  "parse_status": "success|not-attempted|failed",
  "source_integrity": "unchanged|not-applicable|failed",
  "layout_source": "client-figma|generic",
  "screens_from_client_layout": ["<screen_id>"],
  "screens_generic_layout": ["<screen_id>"],
  "layout_gaps": [
    {
      "screen_id": "<id or null>",
      "reason": "no_matching_frame|frame_missing_required_element|frame_out_of_scope",
      "severity": "low|medium"
    }
  ],
  "limitation_severity": "high|medium|low|none",
  "limitation_code": "<short safe code or null>",
  "gate_impact": "blocks|warns|none"
}
```

The exact serialized field names should be implemented consistently with this contract. Paths are project-relative and diagnostics are safe summaries, not raw source dumps.

Mandatory severity rules:

- `high` when (a) `source_integrity = "failed"`, or (b) all selected-file content is rejected by the sanitizer and no valid `design-system.md` fallback exists. `high` uses `gate_impact = "warns"`: it is reported in the phase result but does not block the pipeline; the only mandatory block remains missing `business-rules.md`.
- `medium` when the selected file is malformed but a valid `design-system.md` or generic fallback is available, or when one of `colors`, `typography`, `spacing`, `grid`, or `components` is unmapped while the others are mapped. `gate_impact = "none"`.
- `low` when an optional or non-visual parser field is unsupported. `gate_impact = "none"`.
- `none` for successful client ingestion without material limitation or fallback without any condition above. `gate_impact = "none"`.

Mandatory traceability invariants:

- If `source` starts with `fallback-`, `fallback_reason` MUST be non-null.
- If `source = "client"`, `used_file` MUST be non-null.
- If a file was detected but rejected, `detected_file` remains populated and `used_file` MUST be null.

### 8. Summary integration decision

**Decision: modify Summary minimally; do not rely on discovery alone.**

The current Summary already discovers all files in `outputs/tobe/prototype/` recursively, so the new artifact will appear in the F3 file tree/chips without changes to the recursive scanner. However, the existing artifact map and template do not explicitly interpret its JSON content or display “client vs fallback” provenance. Therefore implementation must:

- Add the new traceability artifact to the fixed `ava-prototype` artifact candidates where fixed presence/contract checks are used, without replacing recursive discovery.
- Add a small builder-side loader that reads the traceability JSON only if present, validates the expected shape, masks unsafe values, and exposes a compact `PROTOTYPE_DESIGN_SOURCE`/equivalent template value.
- Add an explicit F3 Summary display showing source class, file/format when client-provided, or fallback reason otherwise.
- Preserve legacy behavior when the artifact is absent: show an unavailable/legacy provenance state, do not fail Summary generation solely because older prototype runs lack the new file.
- Add Summary tests for client source, fallback source, malformed traceability, and legacy absence.

This resolves the open assumption in `spec.md`: discovery is already present, but explicit source visibility requires a targeted Summary builder/template change.

## File Change Map

| File / area                                                                  | Change                                                                                                                                                                                                                    |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`          | Update frontmatter to v1.3.0 and Portuguese description; add configuration resolution, client source discovery, parser/mapping, sanitizer, fallback, traceability, no-`.fig` rule, and preserve existing gates/contracts. |
| `src/modules/ava-fabric-agents/prototype/module.yaml`                        | Update module version to v1.3.0, role/description if needed, and add `design-input-traceability.json` to outputs while preserving existing files.                                                                         |
| `.github/skills/ava-prototype/SKILL.md`                                      | No behavioral change expected; verify routing remains valid and does not generate or assume `.fig` output.                                                                                                                |
| `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`               | Add `design-input-traceability.json` to fixed prototype artifact candidates if used by presence/status logic.                                                                                                             |
| `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` | Load and validate compact traceability metadata and pass explicit Phase 3 source data to the template; preserve tolerant legacy behavior.                                                                                 |
| `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` | Render explicit client/fallback design provenance in the F3 Summary section without exposing unsafe raw input.                                                                                                            |
| `tests/prototype/`                                                           | Add focused parser/resolver/mapper/sanitizer/fallback/traceability fixtures and tests, including source hash checks and no-`.fig` assertions.                                                                             |
| `tests/summary/`                                                             | Add targeted provenance-loading and rendering regression tests; keep existing Summary tests unchanged except for shared fixture support if necessary.                                                                     |
| `CHANGELOG.md`                                                               | Add the required v1.3.0 agent behavior change entry because Article X requires migration notes for a MINOR bump.                                                                                                          |

No new agent `.md`, SKILL.md, module, cloud resource, or phase is created.

## Test Strategy and Fixtures

All fixtures are isolated under the test suite and must not write to real project outputs or modify source files. Each fixture includes the minimum valid `business-rules.md` and project configuration needed to exercise the existing prototype path.

### Fixture set

| Fixture                            | Purpose                                                                                                                                                  |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client-figma-conflict/`           | Valid Figma JSON with client colors, typography, spacing, grid, and component values deliberately conflicting with generic defaults.                     |
| `no-client-design/`                | Empty/missing design directory with valid internal `design-system.md`; verifies first fallback and no `.fig`.                                            |
| `disabled-client-design/`          | Client file present but `design_input.enabled: false`; verifies no directory scan and fallback provenance.                                               |
| `malformed-client-design/`         | Candidate file with invalid JSON/CSS/SCSS/Markdown structure; verifies parse limitation and fallback.                                                    |
| `multiple-priority-candidates/`    | Candidates across all five supported format families; verifies highest format priority.                                                                  |
| `multiple-same-priority/`          | Two or more same-priority candidates with no explicit file; verifies lexical selection and recorded tie-break.                                           |
| `explicit-selection/`              | Valid explicit file plus competing higher-priority candidate; verifies explicit file wins.                                                               |
| `explicit-missing-or-unsupported/` | Configured exact filename absent or unsupported; verifies gap and no silent alternate client selection.                                                  |
| `unsafe-design-values/`            | Design source containing script tags, event attributes, imports, unsafe URLs, invalid CSS, or executable expressions; verifies rejection/neutralization. |
| `summary-provenance/`              | Prototype output with client and fallback traceability artifacts plus malformed/absent legacy variants.                                                  |

### Scenario matrix

| Spec scenario                    | Test assertions                                                                                                                                          |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1–1.3 client Figma precedence  | Parsed categories map; generated tokens use client values; conflicting generic values do not override; traceability identifies source/path/format/gaps.  |
| 2.1 priority + lexical tie-break | Highest supported format selected; same-priority candidate selected by lexical path; selection metadata is deterministic across repeated runs.           |
| 2.2 explicit valid file          | Exact file consumed despite competing candidates; `selection.mode=explicit`.                                                                             |
| 2.3 explicit missing/unsupported | No alternate explicit file chosen; configuration gap recorded; documented fallback selected.                                                             |
| 3.1 absent input                 | No `.fig`; `fallback-design-system` selected; fallback reason recorded.                                                                                  |
| 3.2 disabled input               | Directory scan is not invoked; fallback selected; disabled reason recorded.                                                                              |
| 3.3 malformed input              | Parse error is captured safely; fallback continues; traceability records limitation.                                                                     |
| 4.1–4.3 Summary                  | Client/fallback source is visible; format/path/reason are shown; unmapped gaps are represented; malformed/absent legacy metadata does not break Summary. |
| 5.1 mandatory gate               | Missing `business-rules.md` remains blocked; no prototype or traceability output is falsely claimed.                                                     |
| 5.2 integrity                    | Source bytes/hash unchanged; `trace_id` exactly matches input.                                                                                           |
| 5.3 high-severity limitation     | Limitation is surfaced and existing gate/status semantics remain intact.                                                                                 |

### Required regression assertions

- Existing prototype artifact names and paths remain present.
- Existing `design-tokens.json` remains consumable by downstream stack agents.
- Existing design-system fallback and generic CSS token behavior remains deterministic.
- No `.fig` file is created in any fixture.
- Repeated runs with identical inputs produce stable selection and traceability metadata.
- Summary's recursive prototype file inventory still includes every real prototype file.
- No F1–F7 non-Prototype behavior changes.

## Implementation Sequence

1. Add fixture scaffolding and focused test contracts before changing agent behavior.
2. Update `prototype-agent.md` frontmatter/version and document the configuration resolver, source priority, explicit-file behavior, parser normalization, sanitizer, fallback, traceability writer, and no-`.fig` restriction in Portuguese.
3. Implement/encode the internal parser and mapping model using the repository-supported execution mechanism, keeping the agent's public contract unchanged except for the new JSON artifact.
4. Add source hash/integrity checks and negative security tests.
5. Update `prototype/module.yaml` and `CHANGELOG.md` for v1.3.0.
6. Add Summary artifact-map candidate, builder loader, and template provenance display with tolerant legacy handling.
7. Run focused prototype tests, Summary provenance tests, and the existing Summary regression suite.
8. Run repository validation for frontmatter, module registration, output paths, no `.fig` references in generated-output instructions, and unchanged `trace_id` semantics.

## Risks and Mitigations

| Risk                                                         | Mitigation                                                                                          |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Parser accepts arbitrary executable design content           | Data-only parsing, CSS/property allow-lists, script/import/event rejection, and malicious fixtures. |
| Client tokens are silently overridden by existing heuristics | Per-field precedence tests with deliberately conflicting values.                                    |
| Missing client categories appear as client-complete          | Explicit unmapped category/field gaps and source metadata per category.                             |
| Explicit file falls through to a different candidate         | Dedicated missing/unsupported explicit-file tests and resolver rule.                                |
| Non-deterministic candidate selection                        | Fixed priority and lexical sort before selection; repeated-run test.                                |
| Source file mutation                                         | Pre/post byte comparison and source hash recorded in traceability.                                  |
| Summary breaks on old prototype outputs                      | Optional/tolerant traceability loader and legacy absence test.                                      |
| Existing business-rules gate regresses                       | Preserve pre-flight section and add blocked-path regression test.                                   |
| Summary exposes unsafe raw values                            | Compact safe metadata only; never embed raw design file content.                                    |
| Agent contract drift                                         | Module metadata/output checks and changelog entry in the validation phase.                          |

## Definition of Done

- `ava-prototype` is v1.3.0 with a Portuguese description and no new agent/module/skill.
- Supported client design formats are selected in the specified order with lexical tie-breaks.
- Explicit file selection is deterministic and records missing/unsupported gaps without silently choosing another file.
- Normalized client values override generic/default visual tokens; unmapped fields/categories are traceable.
- Unsafe design content is rejected or sanitized before HTML/CSS generation.
- Disabled, absent, and malformed client input follow the documented deterministic fallback.
- `design-input-traceability.json` is generated with source, configured path, detected/used file, format, mapped categories, gaps, fallback reason, parse status, integrity status, and unchanged `trace_id`.
- No `.fig` file is generated.
- Summary explicitly displays client versus fallback provenance while remaining compatible with legacy prototype outputs.
- Mandatory `business-rules.md` blocking behavior, existing output paths, input immutability, trace propagation, and other phases remain unchanged.
- Focused feature tests and existing Summary regression tests pass.

## Project Structure

```text
specs/039-prototype-design-input/
├── spec.md
├── checklists/requirements.md
└── plan.md

src/modules/ava-fabric-agents/prototype/
├── agents/prototype-agent.md
└── module.yaml

src/modules/ava-fabric-agents/summary/
├── data/artifact-map.yaml
├── utils/build_summary_comprehensive.py
└── templates/html/summary-template.html

tests/prototype/
└── design_input/  # isolated fixtures and parser/resolver/mapper/security tests

tests/summary/
└── design_provenance/  # Summary loader/template regression tests
```

**Structure Decision**: Modify the existing Prototype and Summary modules in place. The design parser is an internal capability of `ava-prototype`, not a user-facing agent or new module. Summary changes are limited to consuming the new traceability artifact and presenting a compact provenance indicator.

## Complexity Tracking

No constitutional violations. The only cross-module change is the explicitly required Summary visibility integration: recursive discovery already finds the artifact, but an explicit client/fallback label requires a small loader/template addition. This is bounded, backward-compatible, and directly tied to Scenario 4.
