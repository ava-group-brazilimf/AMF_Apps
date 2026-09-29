# Research: Prototype Optional Artifacts

**Feature**: 023-prototype-optional-artifacts
**Date**: 2026-07-21
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## R1 — Current pre-flight mechanism in `prototype-agent.md`

**Decision**: The current agent uses a symbolic notation in its "Pre-Execution — Leitura Obrigatória" section: `★` marks mandatory inputs and `○` marks optional ones. However, the actual blocking logic is described in prose, not in the canonical pre-flight table format used by other agents (the `╔═══╗` box).

**Findings**:

- `design-system.md` is currently listed as `★` (MANDATORY → blocks).
- `user-journeys.md` is currently listed as `★` (MANDATORY → blocks).
- `api-map.md` is currently listed as `○` (optional).
- `functional-requirements.md` is currently listed as `○` (optional).
- `business-rules.md` is **not referenced at all** in the current agent.
- `bounded-context-map.md` is currently listed as `★` (MANDATORY → blocks) — remains mandatory per this change.

**Change required**: Reclassify `design-system.md` and `user-journeys.md` from `★` to `○`. Add `business-rules.md` from `outputs/asis/docs/` as a new `★` mandatory input. Replace the prose-based blocking description with the canonical pre-flight table.

---

## R2 — Execution log format for LLM agents

**Decision**: No universal `execution-log.json` JSON schema exists yet for the prototype module. The closest reference is `parity/execution-log.md` (compare-version-agent) which is Markdown, not JSON. For this feature, we define a minimal JSON array schema specific to the prototype agent, consistent with the W3C Trace Context / OpenTelemetry conventions cited in Constitution Article VIII.

**Schema defined here** (source of truth for the data-model):

```json
[
  {
    "agent": "ava-prototype",
    "event": "start",
    "timestamp": "<ISO8601>",
    "trace_id": "<uuid>",
    "project_name": "<string>"
  },
  {
    "agent": "ava-prototype",
    "event": "end",
    "status": "success | blocked | warning | cancelled",
    "timestamp": "<ISO8601>",
    "trace_id": "<uuid>",
    "project_name": "<string>",
    "missing_optional": ["<artifact_path>"],
    "cancellation_reason": "<string | null>"
  }
]
```

**File**: `projects/{project_name}/outputs/tobe/prototype/execution-log.json`
**Behavior**: Entries are appended (file is a JSON array grown incrementally). If the file does not exist on `start`, it is created with `[` and the first entry. Each subsequent entry is appended before the closing `]`.

**Rationale**: JSON is machine-readable for future pipeline tooling. Markdown logs (like parity) are read-only human-facing artifacts. Since spec `002` explicitly calls for structured observability data, JSON is the correct format.

---

## R3 — Confirmation prompt behavior vs. automated orchestrator

**Decision**: The confirmation prompt (`Continue? [yes/no]`) is preserved as a hard pause. When dispatched by `ava-master-orchestrator`, the pipeline will pause at this step.

**Rationale**: The user explicitly chose "Exibir prompt de confirmação" during spec authoring (2026-07-21). The implicit assumption in Assumptions §8 of the spec is that this pause is intentional. Future automation can be addressed by a separate feature that introduces a `--non-interactive` flag, which is out of scope here.

**No change to spec required** — the assumption is already documented.

---

## R4 — `bounded-context-map.md` path and mandatory status

**Decision**: Remains `★` mandatory at `projects/{project_name}/outputs/tobe/docs/bounded-context-map.md`. This change does not alter its status.

**Rationale**: Prototype generation requires BC mapping to assign screens to bounded contexts. Without it, the agent cannot produce a structurally valid prototype. This is unchanged from the current agent.

---

## R5 — Fallback behaviour when `design-system.md` is absent

**Decision**: When `design-system.md` is absent (after user confirmation to continue), the agent uses a built-in minimal design token set (already defined inline in the agent body under "Regras de Consistência com o Design System"). No additional fallback logic needs to be authored — the existing CSS custom properties hardcoded in the prototype templates are the natural fallback.

**Quality impact to warn user**: "Without design-system.md, prototype will use generic design tokens. Brand colours, component library and layout specifications will not be applied."

---

## R6 — Fallback behaviour when `user-journeys.md` is absent

**Decision**: When `user-journeys.md` is absent (after user confirmation to continue), the agent derives screens from `business-rules.md` sections and `bounded-context-map.md` BCs. Each top-level BC produces one CRUD screen by default. Navigation flows are simplified to a flat menu.

**Quality impact to warn user**: "Without user-journeys.md, prototype screens will be derived from business rules only. Complex multi-step flows, happy/sad path splits, and screen-to-screen navigation cannot be fully modelled."

---

## R7 — CHANGELOG.md entry required?

**Decision**: Yes. MINOR bump (1.1.0 → 1.2.0) requires a CHANGELOG entry per Constitution Article X.

**Entry**:

```markdown
## [1.2.0] — 2026-07-21

### Changed

- `ava-prototype`: `design-system.md` and `user-journeys.md` reclassified as optional inputs.
- `ava-prototype`: `outputs/asis/docs/business-rules.md` added as mandatory primary input.
- `ava-prototype`: Pre-flight replaced with canonical table format (MANDATORY/OPTIONAL/MISSING/DECISION).
- `ava-prototype`: Confirmation prompt added for optional artifact warnings.
- `ava-prototype`: Start/end execution log entries written to `outputs/tobe/prototype/execution-log.json`.
```
