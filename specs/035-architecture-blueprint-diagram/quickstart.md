# Quickstart — Architecture Blueprint Diagram

## Goal

Validate that Architecture Blueprint generation, discovery, rendering, and publication gating are independent and traceable.

## Preconditions

- Repository root is the current working directory.
- A project fixture has `project-config.yaml`, shared context, and sufficient architecture inputs.
- The appropriate upstream phase is selected:
  - AS-IS Delphi: `ava-asis-solution-delphi` → `outputs/asis/diagrams/architecture-blueprint.mmd`.
  - TO-BE: `ava-tobe-architecture-design` trigger `CB` → `outputs/tobe/diagrams/architecture-blueprint.mmd`.
- Mermaid validation dependencies available through the repository's existing utilities.

## Validation scenarios

1. **Successful AS-IS generation**
   - Run the AS-IS architecture workflow for a Delphi fixture.
   - Verify the expected `.mmd` artifact exists and is non-empty.
   - Run the Summary builder.
   - Verify `D.staticDiagrams.asisArchBlueprint` contains Mermaid source and the Blueprint section renders it.
   - Verify the quality report records the generating agent and `generationStatus=SUCCEEDED`, `renderingStatus=SUCCEEDED`, `gateStatus=PASS`.

2. **Successful TO-BE generation**
   - Run the TO-BE architecture trigger `CB`.
   - Verify `outputs/tobe/docs/architecture-blueprint.md`, `outputs/tobe/diagrams/architecture-blueprint.mmd`, and the companion HTML are produced according to the existing contract.
   - Run Summary and verify `D.staticDiagrams.tobeArchBlueprint` is consumed by `renderAllDiagrams()` and `renderStaticDiagrams()`.

3. **Missing agent execution**
   - Use a fixture whose architecture inputs exist but whose shared execution state does not show the responsible agent as executed.
   - Verify the report emits `AGENT_NOT_EXECUTED`, not `RENDERING_FAILED`.
   - Verify publication is blocked.

4. **Missing artifact after execution**
   - Mark the responsible agent as executed but remove the canonical `.mmd` artifact.
   - Verify `MISSING_ARTIFACT` identifies expected path, null discovered path, and generating agent.
   - Verify publication is blocked.

5. **Generation failure**
   - Provide an empty, placeholder-only, or invalid Mermaid artifact.
   - Verify `GENERATION_FAILED`/invalid artifact status is reported before rendering.
   - Verify no localized unavailable-diagram placeholder is treated as a valid result.

6. **Rendering failure**
   - Provide a valid Mermaid source while making the configured renderer unavailable or incompatible.
   - Verify `RENDERING_FAILED` is reported separately and the source artifact is preserved.
   - Verify publication is blocked.

## Expected outputs

- Canonical Blueprint `.mmd` artifact owned by the architecture agent.
- Summary HTML with a rendered Blueprint diagram on success.
- Canonical quality JSON and Markdown report containing expected path, discovered path, generating agent, generation status, rendering status, findings, and publication gate.
- No published report containing `(diagrama não disponível — execute o agente correspondente)` when a valid artifact exists.

## Cross-checks

- Validate the report against `contracts/blueprint-quality-report.schema.json`.
- Confirm the legacy repository remains unchanged.
- Confirm `traceId` remains unchanged between workflow input, artifact metadata, quality report, and Summary.
- Run existing Mermaid and Summary regression suites after implementation.
