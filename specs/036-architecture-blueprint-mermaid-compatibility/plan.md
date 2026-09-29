# Implementation Plan: Architecture Blueprint Mermaid Compatibility

**Spec**: `specs/036-architecture-blueprint-mermaid-compatibility/spec.md`
**Type**: Cross-cutting Summary compatibility and publication gate
**Status**: Planned

---

## Summary

| Field                   | Value                                                                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Owner**               | Summary pipeline and architecture-diagram producers                                                                                                          |
| **Phase**               | F8 cross-cutting, with pre-publication validation after F1/F2 artifact production                                                                            |
| **Module**              | `summary` plus shared diagram validation                                                                                                                     |
| **Primary requirement** | Blueprint Mermaid source must be proven renderable by the deployed Mermaid baseline before publication.                                                      |
| **Technical approach**  | Detect dialect, validate statically, render with the exact bundled runtime, compare transport hashes, classify root cause, and make publication fail closed. |

---

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9)._

### Constitution Gates

- [x] **Article I** -- Mermaid baseline is resolved from the Summary bundle/configuration, not duplicated in agent instructions
- [x] **Article II** -- No new user-facing agent is introduced by this feature
- [x] **Article III** -- Runs as a cross-cutting F8 publication gate after F1/F2 artifacts are available
- [x] **Article IV** -- Existing `summary` and shared validation modules are extended; no new phase/module
- [x] **Article V** -- Existing agent instructions remain pt-BR; technical artifacts use repository conventions
- [x] **Article VI** -- Nominal, malformed, unsupported, renderer, transport, and gate scenarios are in `spec.md`
- [x] **Article VII** -- No new security pipeline; source and diagnostics must not expose secrets
- [x] **Article VIII** -- `trace_id` is a required report field and remains unchanged
- [x] **Article IX** -- N/A: validation utility and Summary presentation path, not generated Clean Architecture code
  > ℹ️ **LLM prompt agents**: mark this N/A — Clean Architecture applies to generated _code_ artifacts (F3 codegen), not `.md` instruction files. Complete section 3 with `NO` for all layers and note "agent is an LLM prompt file".
- [x] **Article X** -- PATCH/MINOR impact to existing validation contracts is to be determined during implementation; schema addition is backward-compatible
- [x] **Article XI** -- No new agent or skill; this is an internal cross-cutting capability

### Quality Gate Check

- [x] No unresolved clarification remains for the planning decision; runtime support is resolved by executable compatibility tests
- [x] Diagnostic output follows Summary/quality artifact conventions and never writes directly to project `outputs/` outside the owning pipeline
- [x] Existing downstream Summary publication gate remains the final decision point

---

## 1. Technical Context

| Dimension          | Choice                                                                                                           | Source                                                            |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Renderer           | Local Mermaid bundle resolved from `summary/templates/html/mermaid.min.js`                                       | Summary template and bundle metadata                              |
| Baseline           | Mermaid 11.14.0 acceptance baseline                                                                              | Project requirement/spec; must be verified from effective runtime |
| Runtime path       | Inline bundle, `mermaid.initialize`, `mermaid.render(id, source)`                                                | `summary-template.html`                                           |
| Source path        | `.mmd` artifact → `sanitize_mmd()` → `D.staticDiagrams`/template                                                 | Summary builder                                                   |
| Static validation  | Existing `validate_diagram.py`/`sanitize_diagrams.py`, extended with compatibility checks                        | Shared diagram utilities                                          |
| Dynamic validation | Same Mermaid bundle in headless browser/HTML fixture                                                             | New compatibility runner                                          |
| Reporting          | CamelCase JSON/Markdown contract validated against `contracts/blueprint-compatibility-report.schema.json`        | This feature                                                      |
| Publication        | Fail closed before client-facing HTML write/promotion when required Blueprint lacks PASS at every required stage | Summary validator/publication gate                                |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

Master pipeline sequence (F4 is a sub-phase of F2, not a standalone step):

```
F1 -> ava-summary -> F2 -> ava-summary -> F3 -> ava-summary
                                       -> F5 -> ava-summary
                                       -> F7 -> ava-summary
                                       -> F6 -> ava-summary (FINAL)
```

This capability's position:

```
F1/F2 artifact producer -> compatibility validation -> ava-summary publication gate
ava-summary -> injects validated source -> exact runtime render -> final gate
```

**Quality gate at this phase**: `summary-validator` after every phase, strengthened with mandatory Blueprint render evidence.

Conditions for `human_gate_required: true`: none; this is an automated blocking gate. Human review may occur after a blocked diagnostic report.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO -- no domain model or business behavior changed
Application    -> NO -- no application use case changed
Infrastructure -> NO -- no persistence or external integration changed
Presentation   -> YES -- Summary renderer, diagnostic report, and publication gate are affected
```

Cross-layer coupling: source producers, shared validation, Summary transport, browser renderer, and publication validator are coupled by the artifact contract; hashes and stage-specific diagnostics control the boundary.

---

## 4. Implementation Surface

No new Skill/Agent two-layer split is required. Planned implementation surface:

```
src/modules/ava-fabric-agents/summary/utils/
+-- blueprint_compatibility.py       <- detection, static rules, report, gate adapter
+-- render_blueprint_compatibility.* <- exact-bundle dynamic runner/fixture integration
src/modules/ava-fabric-agents/summary/templates/html/
+-- summary-template.html             <- expose render/config/transport diagnostics
tests/
+-- Summary compatibility fixtures and publication-gate regression tests
```

**Agent frontmatter** (correct fields — see Constitution Article II):

```yaml
---
name: "ava-[PHASE]-[ROLE]"
version: "1.0.0"
description: |
  [Portuguese description + "Ativa com: ..."]
allowed-tools: Read, Write, Edit
---
```

**Dispatch mode**: internal Summary/build validation; no user-facing agent is added.

**Shared resources**: `mermaid-guardrails.md`, existing diagram sanitizer, Summary template, compatibility report schema.

---

## 5. module.yaml Impact

No new agent is registered. If implementation adds a utility entry point, update only existing Summary module metadata if that registry records utilities; do not create a new phase or skill. Preserve `bmad_version`.

```
src/modules/ava-fabric-agents/[MODULE_FOLDER]/module.yaml
```

Expected registration: none.

The **top-level** `module.yaml` at the project root only needs updating when
creating an entirely new phase/module. Do NOT update it for agents added to
an existing phase.

---

## 6. Observability & Trace Propagation

```
Input: project/shared context trace_id -> compatibility report -> Summary quality report
                         copied unchanged at every stage
```

Diagnostics must redact secrets, include source/bundle hashes, and never modify the legacy repository.

---

## 7. Schema Changes

| Schema                                       | Change Required | Description                                                  |
| -------------------------------------------- | --------------- | ------------------------------------------------------------ |
| `blueprint-compatibility-report.schema.json` | YES             | New report contract under this spec; versioned independently |
| `agent-task.schema.json`                     | NO              | No new agent task fields                                     |
| `agent-result.schema.json`                   | NO              | Existing agent result contract remains unchanged             |

> Schema change = MINOR or MAJOR version bump (Constitution Article IX).

---

## 8. Implementation Phases

### Phase 0 — Evidence and dialect resolution

1. Extract the first directive and classify `flowchart`, `C4Container` and other types.
2. Load the exact Summary bundle with the Summary initialization and read `mermaid.version` or an equivalent runtime API.
3. Build minimal fixtures for native C4, plugin-required C4, disabled C4, unsupported keyword, and malformed C4.
4. Run the exact bundle with `mermaid.render()` and record whether C4 is native, unavailable, disabled, plugin-dependent, or construct-limited.

### Phase 1 — Compatibility service and report

1. Add static rules for dialect, prohibited/unknown constructs, C4 grammar shape, source locations, and sanitization provenance.
2. Add dynamic execution using the same `mermaid.initialize` and `mermaid.render` path as Summary.
3. Capture parser/init/SVG/transport failures and emit the camelCase report defined in `data-model.md` and `contracts/`.
4. Add an HTML/headless fixture that confirms the SVG exists and no visible Mermaid error is present.

### Phase 2 — Summary integration and publication gate

1. Read the Blueprint artifact and compute `hashes.rawArtifact`.
2. Detect dialect/constructs, probe renderer version, probe C4 capability, and run static validation.
3. Run runtime `mermaid.render()` and compute all renderer input hash checkpoints.
4. Compare integrity hashes and generate JSON then Markdown compatibility reports.
5. Evaluate `publicationAllowed`; only a true result may write/promote client-facing Summary HTML.
6. Preserve explicit records for any non-silent conversion/regeneration; missing artifact is only an upstream boundary diagnostic.

### Phase 3 — Regression and rollout

1. Run existing Summary tests and all compatibility fixtures.
2. Run the historical C4 reproduction and read the actual Sophia file at runtime, recording both results separately.
3. Verify flowchart AS-IS and compatible C4 fixtures render in Mermaid 11.14.0.
4. Update guardrails/agent generation instructions only after the failing construct is proven.

---

## 9. Complexity Tracking

| Gate                       | Failure Reason                                            | Justification                                                                               | Mitigating Controls                                                         |
| -------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Dynamic browser validation | Adds headless/runtime execution beyond regex validation   | Required because parser-only checks cannot prove Summary rendering or expose actual version | Use the exact local bundle and Summary initialization                       |
| Cross-stage hash tracking  | Adds report fields and transport checks                   | Required to separate source defects from Summary corruption                                 | SHA-256 and explicit transformation records                                 |
| No silent C4 downgrade     | May block projects instead of producing a partial diagram | Preserves architecture fidelity and publication safety                                      | Regenerate with supported dialect or obtain an explicit reviewed conversion |

---

## 10. Test Strategy

| Test Type             | Tool                             | Target                                                                                               |
| --------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Static unit           | Python test suite                | Dialect detection, source locations, C4 constructs, sanitization provenance                          |
| Dynamic compatibility | Headless browser/JS runner       | Mermaid 11.14.0 bundle, `mermaid.render`, SVG output                                                 |
| Contract              | JSON Schema                      | CamelCase `BlueprintCompatibilityReport`, rootCause/stage, producer provenance, and hash checkpoints |
| Transport             | Summary HTML fixture             | Artifact hash equals injected/render input hash unless recorded transformation exists                |
| Root-cause matrix     | Fixture suite                    | Invalid syntax, unsupported dialect, unsupported C4, configuration, version mismatch, render failure |
| Publication gate      | Python integration test          | Every non-PASS required Blueprint returns `BLOCK`                                                    |
| Regression            | Existing Summary validator suite | No unrelated Summary pipeline regression                                                             |

## 11. Root-cause decision matrix

| Observable result                                   | Classification                    | Publication |
| --------------------------------------------------- | --------------------------------- | ----------- |
| First directive unknown                             | `UNSUPPORTED_DIALECT`             | BLOCK       |
| Known type, static grammar invalid                  | `INVALID_MERMAID`                 | BLOCK       |
| C4 type known, named construct rejected             | `UNSUPPORTED_C4_SYNTAX`           | BLOCK       |
| Bundle/version/API/init missing or divergent        | `RENDERER_CONFIGURATION_FAILURE`  | BLOCK       |
| Source passes in another runtime but fails baseline | `MERMAID_VERSION_INCOMPATIBILITY` | BLOCK       |
| Parser passes but SVG/DOM render fails              | `RENDERING_FAILURE`               | BLOCK       |
| All checks pass and SVG exists                      | `VALID_MERMAID`                   | ALLOW       |
