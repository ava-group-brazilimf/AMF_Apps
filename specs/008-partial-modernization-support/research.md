# Research: Partial Modernization Support — Strangler Fig Pattern

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-09

---

## R1 — `modernization_scope` field placement in project-config.yaml

**Decision**: Insert `modernization_scope` and `target_modules` immediately after the
existing `scope_modules` field (line ~10 of the template). Rationale: both fields are
semantically related — `scope_modules` selects the full set of modules in scope;
`modernization_scope` and `target_modules` narrow that set for the partial path.
No conflicts with any existing key.

**Current anchor** (line ~10):
```yaml
scope_modules: "all"                    # "all" ou lista: ["financeiro", "cadastro"]
```

**New fields go immediately after** `scope_modules`.

---

## R2 — Master-orchestrator insertion point for Step 0.5

**Decision**: Insert the partial-mode block in **two** places inside
`master-orchestrator.md`:

1. **Step 0 (Pre-flight)** — add `modernization_scope` reading and validation
   logic after the existing step `0.3`:
   ```
   0.4  READ modernization_scope (default: "full")
   0.4a If scope == "partial": validate target_modules non-empty → HARD STOP if empty
   0.4b If scope == "full" and target_modules non-empty: WARN and continue
   ```

2. **Execution Pipeline diagram** — add a conditional box between the
   pre-flight comment and `FASE 1`:
   ```
   IF modernization_scope == "partial":
   ┌─── PASSO 0.5 — Coexistence Strategy ───┐
   │  ▶ @ava-tobe-coexistence-strategy       │
   └────────────────────────────────────────┘
   │ on(coexistence-strategy ✓)
   FASE 1 ...
   ```

3. **Agent Team table** — add a row for the conditional step 0.5 agent:
   ```
   | F2 (pre) | Coexistence Strategy | `ava-tobe-coexistence-strategy` | partial-only |
   ```

4. **Input Contract** — add `modernization_scope` and `target_modules` fields.

5. **Frontmatter version**: `1.2.0` → `1.3.0`.

---

## R3 — Stack-orchestrator `target_modules` guard insertion point

**Decision**: The guard is inserted in **Step 0 pre-flight** of
`orchestrator-stack.md`, after the existing field extraction block (step 0.1),
as a new `0.4` block:

```
0.4  READ modernization_scope and target_modules from project-config.yaml
     If scope == "partial" AND target_modules is non-empty:
       → Store filtered_bcs = target_modules
     Else:
       → filtered_bcs = ALL BCs (no filtering)
```

Then, immediately before the backend codegen dispatch (currently first in the
sequence), add:

```
BC FILTER CHECK (runs only when modernization_scope == "partial"):
  For each bc_id in codegen queue:
    IF bc_id NOT IN filtered_bcs → log skip; remove from queue
```

**Version bump**: `1.7.1` → `1.8.0` (new guard behavior, MINOR).

---

## R4 — `full-pipeline-guide.md` insertion point

**Decision**: Add a new top-level section `## 🌿 Modernização Parcial (Strangler Fig Pattern)`
**before** the existing `## 🆚 Comparação: SA vs FP` section (line 271).
This keeps the document flow: full pipeline details → partial variant → comparison → references.

---

## R5 — `README.md` insertion point

**Decision**: Add a one-line entry in the **Getting Started / Usage** area of
`README.md`. The README currently has a KPI table followed by "Stack — Totalmente
Configurável" section. The link goes into whatever "Usage" or "Pipeline" section
exists, or as a callout after the KPI table if no dedicated usage section exists.

**Scope**: single sentence + markdown link — no structural changes to README.

---

## R6 — `ava-tobe-coexistence-strategy` standalone invocation

**Decision**: The existing `coexistence-strategy-tobe.md` agent already handles
being invoked standalone (it is an F2 sub-agent that reads `project-config.yaml`
directly). **No changes needed** to that agent file.

---

## R7 — CHANGELOG.md format

**Decision**: Two separate entries under a `## [Unreleased]` block:
- `ava-master-orchestrator 1.3.0` — MINOR: partial modernization routing branch
- `ava-stack-orchestrator 1.8.0` — MINOR: target_modules BC filter guard

---

## Summary of NEEDS CLARIFICATION resolved

| # | Question | Resolution |
|---|----------|------------|
| R1 | Where exactly in project-config.yaml? | After `scope_modules` — same block |
| R2 | Where in master-orchestrator? | Steps 0.4/0.4a/0.4b + pipeline diagram + agent team table + input contract |
| R3 | Where in stack-orchestrator? | New step 0.4 in pre-flight + BC filter before dispatch |
| R4 | Where in full-pipeline-guide? | Before `## 🆚 Comparação` section |
| R5 | Where in README? | After KPI table or in dedicated usage area |
| R6 | Does coexistence-strategy need changes? | No — existing agent handles standalone invocation |
