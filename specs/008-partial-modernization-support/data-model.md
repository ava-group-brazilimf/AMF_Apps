# Data Model: Partial Modernization Support — Strangler Fig Pattern

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-09

---

## 1. New Config Fields (`project-config.yaml`)

### `modernization_scope`

| Attribute    | Value |
|--------------|-------|
| Type         | `string` enum |
| Values       | `"full"` \| `"partial"` |
| Default      | `"full"` |
| Read by      | `ava-master-orchestrator` (Step 0.4), `ava-stack-orchestrator` (Step 0.4) |
| Validation   | Required when present; must be `"full"` or `"partial"` |
| Backward compat | ✅ Field absence defaults to `"full"` — existing configs unaffected |

### `target_modules`

| Attribute    | Value |
|--------------|-------|
| Type         | `list[string]` |
| Default      | `[]` (empty list) |
| Read by      | `ava-master-orchestrator` (Step 0.4a), `ava-stack-orchestrator` (Step 0.4) |
| Validation   | Must be non-empty when `modernization_scope == "partial"` |
|              | Entries should be a subset of `scope_modules` when `scope_modules ≠ "all"` |
| Ignored when | `modernization_scope == "full"` |

---

## 2. Input Contract Additions — `ava-master-orchestrator`

Two new optional fields added to the Input Contract:

```yaml
inputs:
  # ... existing fields ...
  modernization_scope: "full" | "partial"    # resolved from project-config.yaml; default: "full"
  target_modules: string[]                   # list of BC IDs; used only when scope=partial
```

Resolution order (same as all other inputs):
1. Explicit trigger parameter (highest priority)
2. `projects/{project_name}/context/project-config.yaml`
3. Default value

---

## 3. Derived Runtime State

### `filtered_bcs` (stack-orchestrator runtime variable)

| Attribute    | Value |
|--------------|-------|
| Scope        | Runtime-only (not persisted) |
| Type         | `list[string]` |
| Computed as  | `target_modules` when `scope=partial`; ALL BCs when `scope=full` |
| Consumed by  | BC dispatch loop in `ava-stack-orchestrator` |

---

## 4. Validation Rules (enforced in pre-flight)

| Rule ID | Agent | Condition | Outcome |
|---------|-------|-----------|---------|
| V1 | master-orchestrator | `scope=partial` AND `target_modules` is empty | HARD STOP — `DECISION: BLOCKED` |
| V2 | master-orchestrator | `scope=full` AND `target_modules` is non-empty | WARN — continue with full pipeline |
| V3 | master-orchestrator | `scope=partial` AND `scope_modules ≠ "all"` AND `target_modules` NOT ⊆ `scope_modules` | WARN — entries outside `scope_modules` are silently ignored at F3 |
| V4 | stack-orchestrator  | `scope=partial` AND BC not in `filtered_bcs` | LOG SKIP — `⏭ BC '{bc_id}' fora de target_modules` |

---

## 5. State Transitions

```
project-config.yaml
  modernization_scope: "partial"
  target_modules: ["financeiro"]
         │
         ▼
master-orchestrator Step 0.4 (validate)
  → V1: target_modules non-empty ✅
         │
         ▼
Step 0.5 (partial only)
  → @ava-tobe-coexistence-strategy dispatched
  → coexistence-strategy.md written to outputs/tobe/docs/
         │
         ▼
F1 → F2 (normal)
         │
         ▼
F3: stack-orchestrator Step 0.4
  → filtered_bcs = ["financeiro"]
  → BC "rh" → SKIP (logged)
  → BC "financeiro" → DISPATCH codegen
```

---

## 6. No new output artifacts

This feature does **not** introduce new output files. The only side effect is:
- When `scope=partial`: `coexistence-strategy.md` is written at step 0.5
  (same file the agent would write at F2 step 4.3 in full mode).
- F3 skip log is emitted to stdout (not persisted as a separate file).
