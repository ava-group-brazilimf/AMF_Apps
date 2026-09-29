# Tasks: Client Design Input for Prototype

**Scope**: Implementation-only change to the existing `ava-prototype` and the planned Summary integration. No feature-specific manual verification suite, sample directory, pytest suite, new agent, skill, module, phase, or technology is required.

## Phase 1 — Configuration and source selection

- [ ] T013 Implement configuration resolution as deterministic pt-BR protocol rules with default enabled discovery at project-relative `inputs/design`, explicit `enabled/path/file` normalization, and no mutation of unrelated project configuration. Esta task deve escrever a seção diretamente em pt-BR e não deve introduzir texto em inglês no corpo de `prototype-agent.md`. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 2.1, 2.2, 2.3, 3.2. **Depends on**: —
- [ ] T015 Implement project-root path validation, traversal rejection, safe configuration-gap reporting, and fallback routing as deterministic pt-BR protocol rules. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 3.1, 3.2, 3.3. **Depends on**: T013
- [ ] T017 Implement format detection as deterministic pt-BR protocol rules in the required order: Figma JSON, W3C Design Tokens, CSS, Markdown, and SCSS; apply lexical ordering only among equal-priority candidates. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 2.1. **Depends on**: T015
- [ ] T018 Implement explicit-file selection as deterministic pt-BR protocol rules; valid files are used directly and missing/unsupported files record a gap without selecting another client candidate. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 2.2, 2.3. **Depends on**: T017
- [ ] T018a Checkpoint de consistência: confirmar que as seções T013–T018 permanecem em pt-BR e não duplicam ou conflitam com o protocolo existente. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 2.1, 2.2, 2.3. **Depends on**: T018

## Phase 2 — Parsers and token normalization

- [ ] T020 Implement the Figma JSON parser as deterministic pt-BR protocol rules for mapped variables/styles/components plus frame/page hierarchy and component position/composition, populating `layout` and mapping frames to business-rule-required screens. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.1, 1.2, 4.3, 6.1, 6.2, 6.3. **Depends on**: T018a
- [ ] T021 Implement the W3C Design Tokens parser with groups, aliases, supported token types, and unresolved-alias gaps. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.1, 1.2, 4.3. **Depends on**: T020
- [ ] T022 Implement the CSS variables parser and semantic classification into `colors`, `typography`, `spacing`, `grid`, and `components`. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.1, 1.2, 4.3. **Depends on**: T021
- [ ] T023 Implement the Markdown guide parser for structured token declarations and explicit gaps for narrative or ambiguous guidance. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.1, 1.2, 4.3. **Depends on**: T022
- [ ] T024 Implement the SCSS variables parser without evaluating imports, expressions, or arbitrary Sass. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.1, 1.2, 4.3, 5.2. **Depends on**: T023
- [ ] T026 Implement the unified six-category token model, adding `layout`; populate it only for Figma JSON and leave it empty by design for W3C Tokens, CSS, Markdown, and SCSS. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.2, 4.3, 6.4. **Depends on**: T024

## Phase 3 — Precedence, security, and integrity

- [ ] T028 Implement strict field-level client precedence over `design-system.md` and generic defaults, including per-screen layout precedence: a matching Figma frame overrides generic layout heuristics while `business-rules.md` remains the minimum functional-completeness floor. A later fallback extraction step must not overwrite mapped Figma values. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.1, 1.3, 6.1, 6.3, 6.4. **Depends on**: T026
- [ ] T028b Implement screen generation from a matching Figma frame, using generic heuristics only to supplement mandatory business-rule elements absent from the frame; record `layout_gap` as medium for missing mandatory elements and low for screens without a matching frame. Frames sem tela correspondente exigida por `business-rules.md` são registrados em `layout_gaps` com `reason: frame_out_of_scope`, `screen_id: null`, severidade `low`. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 6.1, 6.2, 6.3. **Depends on**: T028
- [ ] T030 Implement explicit unmapped category/field gap reporting without presenting fallback values as client mappings. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.2, 4.3. **Depends on**: T028
- [ ] T032 Implement the input-security boundary: data-only parsing, CSS allow-lists, HTML escaping, rejection of executable content, secret-like values as non-mappable gaps, and safe diagnostics. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 5.2, 5.3. **Depends on**: T030
- [ ] T034 Implement pre/post source hashing, `source_integrity`, and read-only input handling as deterministic pt-BR protocol rules; esta task não deve introduzir texto em inglês no corpo de `prototype-agent.md`. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 5.2, 5.3. **Depends on**: T032
- [ ] T034a Checkpoint de consistência: confirmar que as seções T020–T034 permanecem em pt-BR e não duplicam ou conflitam com o protocolo existente. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 5.2, 5.3. **Depends on**: T034

## Phase 4 — Fallback and traceability

- [ ] T036 Implement the ordered fallback resolver and source classification (`fallback-design-system` or `fallback-generic`) as deterministic pt-BR protocol rules. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 3.1, 3.2, 3.3. **Depends on**: T034a
- [ ] T038 Define deterministic severity rules: `high` only for failed integrity or total sanitizer rejection without valid `design-system.md`; `high` maps to `gate_impact: "warns"` and never blocks the pipeline. Define `medium`, `low`, `none`, and short safe `limitation_code` values according to `plan.md`. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 5.3. **Depends on**: T036
- [ ] T040 Implement `design-input-traceability.json` generation as deterministic pt-BR protocol rules with source, selection, mapped categories, layout source, client-layout screens, generic-layout screens, `layout_gaps`, fallback reason, parse status, integrity, unchanged `trace_id`, severity fields, and the three invariants. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.3, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4. **Depends on**: T038, T028b
- [ ] T040a Checkpoint de consistência: confirmar que as seções T036–T040 permanecem em pt-BR e não duplicam ou conflitam com o protocolo existente. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 4.3, 5.3. **Depends on**: T040

## Phase 5 — Agent and module contracts

- [ ] T042 Review `prototype-agent.md` in full, confirm pt-BR consistency, resolve duplicate/conflicting sections, and maintain frontmatter v1.3.0. **Files**: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`. **Scenarios**: 5.1, 5.2, 5.3. **Depends on**: T040a
- [ ] T043 Update `prototype/module.yaml` to v1.3.0 and include `design-input-traceability.json` without removing existing outputs. **Files**: `src/modules/ava-fabric-agents/prototype/module.yaml`. **Scenarios**: 1.2, 4.1, 4.2. **Depends on**: T042
- [ ] T044 Keep the v1.3.0 behavior-change entry in `CHANGELOG.md`. **Files**: `CHANGELOG.md`. **Depends on**: T043
- [ ] T045 Confirm `.github/skills/ava-prototype/SKILL.md` routing remains unchanged and does not assume `.fig` output. **Files**: `.github/skills/ava-prototype/SKILL.md`. **Depends on**: T043

## Phase 6 — Summary integration

- [ ] T047 Keep `design-input-traceability.json` in the fixed `ava-prototype` artifact candidates while preserving recursive prototype discovery. **Files**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`. **Scenarios**: 4.1, 4.2. **Depends on**: T043
- [ ] T048 Keep the tolerant Summary loader for valid client/fallback, malformed, and absent/legacy traceability files; expose only compact safe provenance metadata. **Files**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`. **Scenarios**: 4.1, 4.2, 4.3. **Depends on**: T047
- [ ] T049 Keep the explicit F3 provenance display for client versus fallback without raw design content. **Files**: `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`. **Scenarios**: 4.1, 4.2, 4.3. **Depends on**: T048

## Definition of Done

- [ ] All implementation tasks complete.
- [ ] Existing `business-rules.md` gate, `trace_id`, and `design-tokens.json` compatibility remain intact.
- [ ] Summary displays client/fallback provenance without raw design content.
- [ ] No `.fig` file is generated or claimed.
- [ ] No new agent, skill, module, phase, or technology is introduced.
