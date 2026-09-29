# Agent Specification: Architecture Blueprint Mermaid Compatibility

**Feature Branch**: `036-architecture-blueprint-mermaid-compatibility`  
**Created**: 2026-08-05  
**Status**: Draft  
**Change Type**: bugfix  
**Input**: Architecture Blueprint artifacts are discovered and injected successfully, but Summary shows `Syntax error in text` with Mermaid 11.14.0 instead of rendering the diagram.

> This specification defines the required behavior and quality outcomes. Implementation details are deferred to planning.

---

## 1. Feature Overview

Architecture Blueprint diagrams produced by the AS-IS and TO-BE architecture agents must be compatible with the Mermaid 11.14.0 renderer used by Summary. The pipeline must identify the generated Mermaid dialect, validate the source before publication, diagnose unsupported C4 constructs or renderer configuration issues, and block publication when the diagram cannot be rendered.

The feature covers the complete compatibility path: agent output, dialect detection, Mermaid validation, Summary transport, renderer configuration, browser rendering, diagnostics, and publication gating.

## 2. User Scenarios & Testing

### Scenario 1 — Compatible Blueprint renders successfully (Priority: P1)

**Story**: As an architect reviewing the Summary, I want the Architecture Blueprint to render as a diagram so that I can inspect the architecture visually without parsing Mermaid source.

**Why this priority**: A syntax error makes a primary architecture deliverable unusable even when the artifact was generated correctly.

**Acceptance Scenarios**:

1. **Given** a valid AS-IS or TO-BE Blueprint artifact, **When** Summary renders it with Mermaid 11.14.0, **Then** the Architecture Blueprint is displayed as a rendered diagram.
2. **Given** a successful rendering, **When** the Summary is inspected, **Then** it contains neither `Syntax error in text` nor `mermaid version 11.14.0` as a visible rendering error.
3. **Given** a successful rendering, **When** the quality report is inspected, **Then** it identifies the renderer version, diagram type, dialect, validation result, compatibility result, and root cause as successful.

### Scenario 2 — Invalid or unsupported Mermaid source is diagnosed (Priority: P1)

**Story**: As a pipeline maintainer, I want invalid and unsupported diagram constructs to be classified explicitly so that generation defects are not confused with renderer failures.

**Acceptance Scenarios**:

1. **Given** an artifact containing invalid Mermaid syntax, **When** compatibility validation runs, **Then** it reports `INVALID_MERMAID` before publication and identifies the source location where possible.
2. **Given** an artifact using an unsupported Mermaid dialect or unsupported C4 syntax, **When** compatibility validation runs, **Then** it reports `UNSUPPORTED_DIALECT` or `UNSUPPORTED_C4_SYNTAX` with the detected dialect and construct.
3. **Given** an artifact containing unsupported directives, extensions, or diagram types, **When** validation runs, **Then** it reports the exact unsupported construct and recommended supported alternative or regeneration action.

### Scenario 3 — Renderer and configuration failures are separated (Priority: P1)

**Story**: As a quality reviewer, I want renderer configuration failures separated from source incompatibility so that the correct component can be fixed.

**Acceptance Scenarios**:

1. **Given** valid Mermaid source and a configured Mermaid 11.14.0 renderer, **When** the Summary receives the source unchanged, **Then** compatibility validation passes before rendering.
2. **Given** valid source but missing or incompatible renderer configuration, **When** rendering starts, **Then** the report classifies the issue as `RENDERER_CONFIGURATION_FAILURE`, not invalid Mermaid.
3. **Given** valid source but a renderer rejection, **When** rendering fails, **Then** the report classifies it as `RENDERING_FAILURE` and preserves the original source and validation evidence.

### Scenario 4 — C4 compatibility is explicit (Priority: P1)

**Story**: As an architecture agent maintainer, I want C4 syntax support verified against the deployed renderer so that generated `C4Container` diagrams are not silently published when unsupported.

**Acceptance Scenarios**:

1. **Given** a `C4Container` artifact, **When** compatibility validation runs, **Then** the result explicitly states whether `C4Container` is supported by the deployed Mermaid 11.14.0 environment.
2. **Given** `C4Container` is unsupported in the deployed environment, **When** the pipeline runs, **Then** it either converts/regenerates the diagram into a supported format or blocks publication with `UNSUPPORTED_C4_SYNTAX`.
3. **Given** C4 syntax is supported, **When** the artifact is rendered, **Then** declarations such as `Person`, `Container`, `ContainerDb`, `System_Ext`, and `Rel` are validated and rendered successfully or reported with a precise construct-level failure.

### Scenario 5 — Publication gate (Priority: P1)

**Story**: As a delivery owner, I want publication blocked when a Blueprint cannot render so that the client never receives an architecture report containing a visible Mermaid error.

**Acceptance Scenarios**:

1. **Given** invalid, unsupported, or unrenderable Blueprint source, **When** the publication gate runs, **Then** publication fails with a blocking compatibility finding.
2. **Given** a renderer configuration failure, **When** the publication gate runs, **Then** publication fails and identifies the renderer environment as the remediation owner.
3. **Given** all compatibility and rendering checks pass, **When** publication runs, **Then** the Blueprint diagram is published and the quality gate passes.

## 3. Functional Requirements

### Compatibility detection

- **FR-001**: The pipeline MUST identify the Mermaid dialect and diagram type generated for every AS-IS and TO-BE Architecture Blueprint artifact.
- **FR-002**: The pipeline MUST validate every generated Blueprint artifact against Mermaid 11.14.0 compatibility before publication.
- **FR-003**: The pipeline MUST detect invalid Mermaid syntax, unsupported dialects, unsupported C4 syntax, unsupported extensions, unsupported directives, and unsupported diagram types.
- **FR-004**: The pipeline MUST explicitly verify whether `C4Container` syntax and its declarations are supported by the deployed Summary renderer.

### Agent generation

- **FR-005**: The compatibility pipeline MUST validate Mermaid syntax produced by the AS-IS and TO-BE architecture agents against the Summary renderer; it MUST NOT modify those generation agents as part of this feature.
- **FR-006**: Compatibility reports MUST identify the responsible producing agent, artifact path, diagram type, dialect, source contract, artifact contract, generation phase, and source validation result. If metadata is unavailable, the documented pipeline mapping MUST be used with `confidence: MEDIUM`.
- **FR-007**: The pipeline MUST not silently transform an unsupported architecture dialect into a different diagram type without recording the transformation and its compatibility result.

### Summary transport and rendering

- **FR-008**: Summary MUST preserve the generated Mermaid content unchanged between artifact discovery and compatibility validation, except for documented deterministic sanitization.
- **FR-009**: Summary MUST record whether the content injected into `D.staticDiagrams` matches the validated artifact source.
- **FR-010**: `renderAllDiagrams()` and `renderStaticDiagrams()` MUST expose distinct diagnostics for source incompatibility, renderer configuration failure, and renderer execution failure.
- **FR-011**: A rendering failure MUST preserve the original source, detected dialect, renderer version, and construct-level evidence where available.

### Quality reporting and publication

- **FR-012**: Public JSON and Markdown quality reports MUST use the canonical camelCase contract: `traceId`, `projectName`, `artifactPath`, `diagramId`, `rendererVersion`, `rendererSource`, `detectedDialect`, `c4Detected`, `c4SupportedByRenderer`, `staticValidationStatus`, `runtimeRenderStatus`, `rootCause`, `stage`, `confidence`, `construct`, `diagnosticEvidence`, `hashes`, `exactErrorMessage`, `recommendedFix`, and `publicationAllowed`.
- **FR-013**: The pipeline MUST distinguish `VALID_MERMAID`, `INVALID_MERMAID`, `UNSUPPORTED_DIALECT`, `UNSUPPORTED_C4_SYNTAX`, `RENDERER_CONFIGURATION_FAILURE`, `MERMAID_VERSION_INCOMPATIBILITY`, `RENDERING_FAILURE`, `SOURCE_INTEGRITY_MISMATCH`, and `EVIDENCE_UNAVAILABLE` through the public `rootCause` field.
- **FR-014**: Summary publication MUST fail when any required Architecture Blueprint cannot be validated and rendered by Mermaid 11.14.0.
- **FR-015**: The visible error strings `Syntax error in text` and `mermaid version 11.14.0` MUST NOT appear in a successfully published Blueprint section.
- **FR-016**: Compatibility and publication results MUST preserve `projectName` and `traceId` without exposing secrets or modifying the legacy repository. Internal `trace_id` values, if used, MUST be transformed to public `traceId`.

### Runtime and publication ordering

- **FR-017**: The runtime probe MUST load the exact Summary Mermaid bundle, use the Summary initialization configuration, read `mermaid.version` or an equivalent runtime API, and fail closed if the version cannot be read.
- **FR-018**: A runtime version probe failure MUST produce `rootCause: RENDERER_CONFIGURATION_FAILURE`, `stage: RUNTIME_VERSION_PROBE`, and `publicationAllowed: false`; a mismatch with the Mermaid baseline MUST produce `MERMAID_VERSION_INCOMPATIBILITY` at the same stage and block publication.
- **FR-019**: C4 support MUST be proven by a runtime capability probe and an actual `mermaid.render()` test. Textual presence of C4 tokens in the bundle is insufficient.
- **FR-020**: Publication MUST execute in this order: read artifact; compute raw hash; detect dialect/constructs; probe renderer version; probe C4 capability; run static validation; run `mermaid.render()`; compute renderer input hash; compare all integrity hashes; generate JSON report; generate Markdown report; evaluate `publicationAllowed`; only then write or promote client-facing Summary HTML.
- **FR-021**: When `publicationAllowed` is false, client-facing Summary HTML MUST NOT be written or promoted. Diagnostic/test artifacts may be generated only as explicitly non-published outputs.

## 4. Key Entities

- **Blueprint Mermaid artifact**: AS-IS or TO-BE Mermaid source produced by the responsible architecture agent.
- **Mermaid dialect**: Detected diagram language/type, such as `flowchart`, `C4Context`, `C4Container`, `C4Component`, or another supported type.
- **C4 construct**: A declaration or relationship such as `Person`, `Container`, `ContainerDb`, `System_Ext`, or `Rel`.
- **Compatibility result**: The result of comparing artifact syntax and dialect with the deployed Mermaid 11.14.0 renderer.
- **Renderer configuration record**: Renderer version, enabled features, security level, initialization, and environment status.
- **Rendering result**: Browser/rendering outcome and any construct-level error evidence.
- **Publication gate result**: Blocking or passing decision for Summary publication.

## 5. Edge Cases

- The artifact begins with `C4Container` but the deployed Mermaid build lacks C4 support.
- The artifact uses valid C4 declarations but contains a malformed relationship or unsupported directive.
- Sanitization alters the source before rendering; the report must identify the transformation and compare the sanitized source with the validated source.
- The renderer receives a truncated, escaped, or template-corrupted string even though the file is valid.
- The browser renderer is unavailable while static validation succeeds.
- AS-IS uses `flowchart TB` while TO-BE uses a C4 dialect; each must be validated independently.
- A valid diagram is rendered in one Summary path but fails in another due to differing Mermaid initialization or configuration.
- The renderer emits a generic syntax error without a line number; the report must still identify the artifact, dialect, version, and stage.
- The historical incident fixture begins with `C4Container`, while the current Sophia runtime artifact may begin with `flowchart TB`; both must be reported separately.
- C4 support is native, plugin-dependent but unavailable, disabled by initialization, or keyword-limited; each case has a distinct root-cause mapping.
- The current Sophia artifact is absent; this is an upstream boundary failure, not an artifact-generation responsibility of this feature.

## 6. Assumptions

- Mermaid 11.14.0 is the acceptance baseline for the Summary environment.
- Existing AS-IS and TO-BE architecture agents remain responsible for diagram generation.
- Existing artifact paths and `D.staticDiagrams` keys remain unchanged unless planning proves a contract correction necessary.
- Mermaid source may be deterministically sanitized only when the transformation is recorded and the resulting source is revalidated.
- The publication gate may produce diagnostic reports even when it blocks the client-facing HTML.

## 7. Dependencies

- AS-IS architecture agents and their Mermaid output contracts.
- TO-BE architecture agent and `CB` orchestration chain.
- `src/shared/utils/validate_diagram.py` and Mermaid sanitization utilities.
- Summary builder and `D.staticDiagrams` injection.
- `renderAllDiagrams()` and `renderStaticDiagrams()` in the Summary template.
- Existing Summary validation and publication gates.

## 8. Non-Goals

- Redesigning the business architecture.
- Replacing Mermaid as the Summary diagram technology.
- Silently downgrading a C4 diagram to a generic flowchart without traceable evidence.
- Re-running unrelated migration phases.
- Hiding renderer errors with a static image or placeholder.

## Success Criteria

| Criterion                | Measure                                                                                                                                   |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Rendering success        | 100% of valid AS-IS and TO-BE Blueprint fixtures render successfully with Mermaid 11.14.0.                                                |
| Compatibility validation | 100% of generated Blueprint artifacts receive a dialect, syntax, and compatibility result before publication.                             |
| C4 support transparency  | 100% of `C4Container` fixtures report explicit supported/unsupported status in quality output.                                            |
| Failure classification   | 100% of invalid syntax, unsupported dialect/C4, renderer configuration, and renderer execution fixtures receive distinct classifications. |
| Publication safety       | 100% of non-renderable required Blueprints block publication.                                                                             |
| Error elimination        | 0 successfully published Blueprint sections contain `Syntax error in text` or `mermaid version 11.14.0`.                                  |
| Traceability             | 100% of quality reports identify renderer version, diagram type, dialect, root cause, recommended fix, and unchanged `trace_id`.          |
| Public contract          | 100% of JSON and Markdown reports use the canonical camelCase fields and complete hash object.                                            |
| Runtime evidence         | 100% of reports record the version extracted from the loaded Summary runtime or block publication when unavailable.                       |
| Producer provenance      | 100% of Blueprint reports identify the producing agent or use the documented mapping with medium confidence.                              |
| Publication ordering     | 0 client-facing Summary HTML files are written or promoted before a passing compatibility decision.                                       |

## Quality Gate Checklist

- [ ] Mermaid dialect and diagram type are detected for AS-IS and TO-BE artifacts.
- [ ] C4Container support is verified in the deployed Mermaid 11.14.0 environment.
- [ ] Source is validated before Summary publication.
- [ ] Summary transport integrity into `D.staticDiagrams` is verified.
- [ ] `renderAllDiagrams()` and `renderStaticDiagrams()` failures are separated.
- [ ] Publication blocks invalid, unsupported, or unrenderable Blueprint diagrams.
- [ ] Successful output contains no visible Mermaid syntax error strings.
- [ ] Public reports use camelCase and contain all required hash checkpoints and traceability fields.
- [ ] Runtime version and C4 capability are proven by the exact Summary bundle and `mermaid.render()`.
- [ ] Client-facing HTML is not written or promoted after a blocked compatibility decision.
