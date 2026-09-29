# Research: Mermaid Diagram Quality

## Decision 1: Reuse the existing pre-write validation gate

- **Decision**: Extend `src/shared/utils/validate_diagram.py` and `src/shared/utils/sanitize_diagrams.py` rather than introducing a parallel Mermaid validator.
- **Rationale**: These utilities already define the repository's single write gate, sanitization protocol, prohibited diagram types, structural checks, and exit-code contract. Reuse avoids divergent behavior across agents.
- **Alternatives considered**: A new validator per agent was rejected because it would duplicate policy and allow inconsistent publication behavior.

## Decision 2: Keep Mermaid compatibility configuration-driven

- **Decision**: Resolve the compatibility target from project/reference configuration and pass it into validation/report metadata; retain the currently documented viewer target as the acceptance baseline without embedding it as an agent-body constant.
- **Rationale**: Constitution Article I prohibits hardcoded technology versions in agent instructions. Existing utilities already document a Mermaid compatibility baseline, but the final implementation must centralize and resolve it through configuration.
- **Alternatives considered**: Hardcoding the version in every generator was rejected because it would drift and violate configuration-driven governance.

## Decision 3: Use a two-level validation strategy

- **Decision**: Use deterministic source validation and sanitization for every artifact, then use rendered geometry only when a renderer is available for visual overlap analysis. If geometry is unavailable, emit a limitation and apply structural heuristics; never claim visual PASS without evidence.
- **Rationale**: Source validation can guarantee many syntax and safety rules, but label/container overlap is a rendered-layout property. The current environment has no Python Mermaid parser or browser automation package, so the design must support an explicit unavailable-renderer outcome.
- **Alternatives considered**: Treating source heuristics as proof of visual quality was rejected because it cannot reliably detect SVG/text collisions.

## Decision 4: Correct only deterministic defects automatically

- **Decision**: Continue the existing sanitizer's safe corrections for fences, invisible characters, prohibited characters, emojis, newlines, node IDs, self-loops, and structural issues. Every correction is followed by validation. Ambiguous architecture redesign remains a blocking finding requiring regeneration or human review.
- **Rationale**: Automatic rewriting is safe only when semantics are preserved. Layout redesign and edge routing can change architectural meaning.
- **Alternatives considered**: Broad regex rewriting of arbitrary Mermaid syntax was rejected as unsafe and difficult to audit.

## Decision 5: Produce one canonical diagnostic model

- **Decision**: Add a stable JSON diagnostic schema and a Markdown report generated from it, with per-artifact status, syntax findings, visual findings, correction attempts, evidence, trace ID, and gate decision.
- **Rationale**: JSON supports validators and Summary ingestion; Markdown supports human review. A canonical model prevents duplicated parsers and preserves downstream compatibility.
- **Alternatives considered**: Markdown-only output was rejected because machine-readable gate decisions and evidence are required.

## Decision 6: Integrate publication blocking at the owning generator boundary

- **Decision**: Diagram-producing agents must route writes through the shared gate. A batch auditor validates all existing Mermaid artifacts before publication and emits `BLOCKED` when any artifact remains invalid or unreadable.
- **Rationale**: Pre-write enforcement prevents invalid files from being created, while batch auditing catches legacy or externally produced artifacts.
- **Alternatives considered**: Validating only the Summary HTML was rejected because invalid source Markdown could already have been published or consumed upstream.

## Decision 7: C4 Container readability uses explicit authoring rules plus evidence

- **Decision**: Add C4-specific rules for short relationship labels, explicit direction/layout, spacing, controlled grouping, and segmentation thresholds resolved from configuration. Rendered checks report label/node/boundary intersections and congestion when geometry is available.
- **Rationale**: Mermaid does not provide a universal source-level guarantee against label overlap. Authoring constraints reduce risk, and rendered evidence provides the actual gate.
- **Alternatives considered**: Relying exclusively on a fixed layout directive was rejected because Mermaid layout behavior varies by diagram density and renderer.

## Decision 8: Testing approach

- **Decision**: Add unit tests for sanitizer and diagnostic schema, CLI tests for pass/fix/block exit codes, fixture tests for all supported diagram types, and renderer-backed integration tests when the configured renderer is available. Existing unified Mermaid and Summary checks remain regression gates.
- **Rationale**: The feature spans pure transformations, filesystem publication, and optional rendering; each layer needs a focused test boundary.
- **Alternatives considered**: Only end-to-end browser tests were rejected because they would be slow, environment-dependent, and unable to isolate sanitization defects.
