# Implementation Plan: Screen-Flow Batch Protocol + Completude Assertion

**Branch**: `029-screen-flow-batch-protocol` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Tech Stack**: See `src/shared/data/reference-architecture.yaml` — do not hardcode versions.  
**Note**: This is a `modify-existing` bugfix. No new agent is created. The existing `gen_screen_flow.py` tool already implements per-BC batch generation. Work is confined to agent instruction updates in `documentation-asis.md` and awareness in downstream validators.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-asis-documentation` |
| **Version** | `3.0.0` (MAJOR bump — execution model changes from single-pass to chunked BC iteration) |
| **Phase** | `F1` (AS-IS Diagnostic) |
| **Module** | `asis-diagnostic` |
| **Primary Requirement** | Eliminate screen-flow.mmd truncation by enforcing script invocation (`gen_screen_flow.py`) and adding a mandatory post-generation completeness assertion (≥80% of forms from `form-registry.json`) |
| **Technical Approach** | Update agent instructions in `documentation-asis.md` FT section to mandate tool invocation instead of inline generation; add REGRA ABSOLUTA assertion block that emits `screen-flow-completeness.json` with PASS/FAIL metrics |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9).*

### Constitution Gates

- [x] **Article I** -- No technology versions hardcoded in agent body ✅ — script path is relative, no version literals
- [x] **Article II** -- Frontmatter contains ONLY: `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools` ✅ — spec defines updated frontmatter
- [x] **Article II** -- agent `name` matches pattern `^ava-[a-z0-9-]+$` ✅ — `ava-asis-documentation`
- [x] **Article III** -- Phase placement valid ✅ — F1 agent dispatched by `ava-asis-orchestrator`; `ava-summary` runs after F1
- [x] **Article IV** -- Module-level `module.yaml` diff prepared N/A — `modify-existing`; already registered
- [x] **Article V** -- Agent body language is Brazilian Portuguese ✅ — spec mandates pt-BR for body
- [x] **Article VI** -- BDD scenarios in spec section 4 (nominal + edge + gate paths) ✅ — 3 scenarios defined
- [x] **Article VII** -- Security sub-pipeline impact assessed ✅ — screen-flow does not process secrets; no change
- [x] **Article VIII** -- trace_id propagation documented N/A — agent emits `screen-flow-completeness.json` via existing observability pipeline
- [x] **Article IX** -- Clean Architecture layer ordering respected N/A — agent is an LLM prompt file, not generated code
- [x] **Article X** -- Version bump type determined: MAJOR ✅ — execution model changes (single-pass → chunked)
- [x] **Article XI** -- Skill/Agent split declared ✅ — SKILL.md already exists at `.github/skills/ava-asis-documentation/SKILL.md`

### Quality Gate Check

- [x] No [NEEDS CLARIFICATION] markers remain in spec ✅
- [x] All outputs follow `projects/{project_name}/outputs/[phase]/...` ✅ — `asis/docs/`
- [x] Downstream `next_agent` confirmed to exist ✅ — `ava-summary` consumes `.mmd`; assertion JSON consumed by Summary Validator

**Decision**: **PROCEED** — all gates pass.

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| **Agent type** | LLM prompt file (Markdown) | IMFAI Constitution Article II |
| **Existing tool** | `gen_screen_flow.py` (Python 3.11+) | Already in repo; implements batch protocol |
| **Tool invocation** | `Bash` tool | Agent `allowed-tools` includes Bash |
| **Output format** | Mermaid v11+ `.mmd` | Constitution Article VIII |
| **Assertion artifact** | `screen-flow-completeness.json` | New lightweight JSON — consumed downstream |
| **Batch trigger** | 80 forms (informed default) | Spec assumption; below = single-pass, above = chunked |
| **Coverage threshold** | 80% | Spec success criterion |
| **Retry policy** | 3 attempts | Matches project `RetryProtocol` |
| **Testing** | BDD validation via `ava-qa-scenario-generator` (F5) | Constitution Article VI |

**No new runtime dependencies. No external APIs.**

---

## 2. Phase Placement

Master pipeline sequence:
```
F1 (AS-IS) -> ava-summary -> F2 (TO-BE) -> ava-summary -> F3 (Prototype) -> ava-summary
                                                       -> F5 (QA) -> ava-summary
                                                       -> F6 (Deliverables) -> ava-summary
                                                       -> F7 (DevOps) -> ava-summary (FINAL)
```

This agent's position:
```
ava-asis-orchestrator -> dispatches ava-asis-documentation (FT sub-skill runs within this agent)
F1 -> ava-asis-documentation -> ava-asis-inventory (parallel or dependency)
   -> emits next_agent: ava-asis-security-orchestrator (or next F1 sub-agent)
F1 -> ava-summary (invoked after F1 completes)
```

**Quality gate at this phase**: `summary-validator` (after every phase) + F1 Consistency Gate C4 (SCREEN-INVENTORY)

Conditions for `human_gate_required: true`:
- Completeness assertion FAILs after 3 retries
- `screen-flow-completeness.json` reports `status: "FAIL"` with `coverage_pct < 80`

---

## 3. Clean Architecture Alignment

```
Domain         -> N/A -- agent is an LLM prompt file, not generated code
Application    -> N/A -- agent is an LLM prompt file
Infrastructure -> N/A -- agent is an LLM prompt file
Presentation   -> N/A -- agent is an LLM prompt file
```

Cross-layer coupling: NONE — this is an instruction-level modification.

---

## 4. Agent File Structure

**Modify-existing** — no new agent file created.

File to modify:
```
src/modules/ava-fabric-agents/asis-diagnostic/agents/
└── documentation-asis.md          <- frontmatter + FT section update
```

**Dispatch mode**: user-facing via existing `ava-asis-documentation` SKILL.md

**Shared resources**:
- `src/shared/templates/diagrams/mermaid-guardrails.md` — Mermaid syntax rules
- `src/shared/tools/gen_screen_flow.py` — batch generation tool
- `form-registry.json` — canonical form list (from `ava-asis-inventory`)
- `bounded-context-map.md` — BC classification (from `ava-asis-solution-delphi`)

---

## 5. module.yaml Impact

**N/A** — `modify-existing`. The agent `ava-asis-documentation` is already registered in:
```
src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
```

No module.yaml changes required.

---

## 6. Observability & Trace Propagation

The agent does not handle `trace_id` explicitly in its body. The existing `pipeline_observer.py` invocation at the end of `documentation-asis.md` (existing step) will include `screen-flow-completeness.json` in its artifact list.

The new `screen-flow-completeness.json` carries its own `generated_at` (NTP time via `src/shared/utils/ntp_time.py`) and is discoverable by the Summary Validator.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | No new input fields |
| `agent-result.schema.json` | NO | No new output contract fields — `screen-flow-completeness.json` is an artifact file, not a schema field |

No schema version bump needed.

---

## 8. Implementation Phases

**Phase 0** — Frontmatter update in `documentation-asis.md`: bump version to `3.0.0`, update `description` to mention batch protocol + assertion.

**Phase 1** — FT section rewrite:
1. Add REGRA ABSOLUTA: "FT DEVE invocar `Bash: python src/shared/tools/gen_screen_flow.py` — geração inline é PROIBIDA"
2. Add batch protocol activation condition (`N_registry > 80`)
3. Add per-BC generation steps using `--bc-filter` (or rely on tool's internal batching)
4. Add assertion block: count nodes in merged `screen-flow.mmd`, compare to 80% of registry, write `screen-flow-completeness.json`
5. Add retry loop (max 3) on assertion FAIL
6. Add `human_gate_required = true` on persistent FAIL

**Phase 2** — Gate Logic: add `screen-flow-completeness.json` to Pre-Completion Validation Checklist

**Phase 3** — BDD: confirm spec section 4, map to F5 QA scenarios in `ava-qa-scenario-generator`

**Phase 4** — Registration: N/A (modify-existing)

---

## 9. Complexity Tracking

No constitution violations requiring justification. All gates pass cleanly.

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Nominal BDD | manual / xUnit fixture | Spec Scenario 1: 665-form ERP produces ≥80% coverage |
| Edge case BDD | manual / xUnit fixture | Spec Scenario 2: LLM skips script → `[FT-INLINE-GENERATION-DETECTED]` |
| Gate trigger BDD | manual / xUnit fixture | Spec Scenario 3: assertion FAIL after 3 retries → `human_gate_required = true` |
| Regression | existing IMFAI pipeline | Small projects (≤80 forms) still work with single-pass |
| Tool contract | `pytest` on `gen_screen_flow.py` | Verify `--project`, `--input`, `--output`, `--bc-map` args |

---

## Phase 1 Design Artifacts

- [research.md](research.md) — Root cause analysis + tool evaluation
- [data-model.md](data-model.md) — `screen-flow-completeness.json` schema
- [quickstart.md](quickstart.md) — Validation guide for coverage assertion
