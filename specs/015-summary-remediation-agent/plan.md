# Agent Implementation Plan: ava-summary-remediation

**Spec**: `specs/015-summary-remediation-agent/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-summary-remediation` |
| **Phase** | `F8` (Summary, cross-cutting) |
| **Module** | `summary` |
| **Primary Requirement** | Independent, idempotent post-pipeline repair of the Summary HTML: fix display/data issues without re-running upstream agents. |
| **Technical Approach** | Reuse the `FS — Fix Summary` phase design already drafted by the requester (`summary (1).md`), generalized into a standalone agent + `remediate_summary.py` script; pair it with **permanent** fixes to `summary-template.html`, `build_summary_comprehensive.py`, and a new `C11` category in `validate_summary.py` so newly generated summaries need no repair at all. |

---

## Constitution Check

- [x] **Article I** — No technology versions hardcoded; all fixes are data-driven (empty/zero detection), not stack-specific
- [x] **Article II** — Frontmatter contains ONLY `name`, `version`, `description`, `allowed-tools`; `name` matches `^ava-[a-z0-9-]+$`
- [x] **Article III** — Phase placement valid: runs after `ava-summary` (F8, cross-cutting), standalone, not part of F1→F7 chain
- [x] **Article IV** — `module.yaml` diff prepared (section 5 below)
- [x] **Article V** — Agent body written in Brazilian Portuguese
- [x] **Article VI** — BDD scenarios in spec section 4 (nominal + edge + gate)
- [x] **Article VII** — Security impact: reuses the existing Phase 4 (Security Reconciliation) design from the `FS` draft; no new attack surface — only reads/writes within `projects/{project_name}/outputs/`
- [x] **Article VIII** — N/A: this agent is an LLM prompt file; trace context flows through `shared-context.md` like all other agents
- [x] **Article IX** — N/A for this agent's own body (LLM prompt, not generated code); the summary **template's** JS is not subject to Clean Architecture layering
- [x] **Article X** — Version bump: N/A (new agent, `1.0.0`). `build_summary_comprehensive.py`/`validate_summary.py`/`summary-template.html` are internal module files without independent semver — bump `summary/module.yaml` version `1.0.0` → `1.1.0` (MINOR: new agent + new checks, no breaking contract change)
- [x] **Article XI** — Skill/Agent split: `.github/skills/ava-summary-remediation/SKILL.md` (user-facing)

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec
- [x] All outputs follow `projects/{project_name}/outputs/summary/...`
- [x] Downstream: no `next_agent` — this is a terminal, standalone repair agent

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime | Python 3 (matches `build_summary_comprehensive.py` / `validate_summary.py`) | Existing `summary/utils/` scripts |
| Agent host | Claude Code / GitHub Copilot via SKILL.md routing | `.github/skills/ava-summary/SKILL.md` pattern |
| Template | Static HTML + inline JS (no framework) | `summary-template.html` |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

```
F1 -> ava-summary -> F2 -> ava-summary -> F3 -> ava-summary
                                       -> F5 -> ava-summary
                                       -> F7 -> ava-summary
                                       -> F6 -> ava-summary (FINAL)
```

`ava-summary-remediation` sits **outside** this chain, invoked independently, at any point, by the user (or by whoever needs to repair a given summary):

```
[master-orchestrator run] -----\
[individual orchestrator run]---+--> user (or automation) invokes
[ava-summary run] --------------/     @ava-summary-remediation {project_name}
                                       -> reads current outputs/ + current Summary HTML
                                       -> audits, resolves, synthesizes (bounded), sanitizes
                                       -> rebuilds via build_summary_comprehensive.py
                                       -> re-validates via validate_summary.py (incl. C11)
                                       -> writes remediation-report.md/.json
```

**Quality gate at this phase**: summary-validator (re-run as the final step of this agent's own flow).

Conditions for `human_gate_required: true`:
- Base template (`summary-template.html`) missing — hard abort (Scenario 3).
- Post-remediation `validate_summary.py` still reports `error`-level failures that require re-running an upstream agent (data genuinely absent, not a display bug) — reported in the fix report as "Pending", not silently swallowed.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO -- agent is an LLM prompt file + Python utility script, not a Clean Architecture layer
Application    -> NO
Infrastructure -> NO
Presentation   -> NO -- summary-template.html is a static report artifact, not application UI
```

Cross-layer coupling: NONE.

---

## 4. Agent File Structure

```
.github/skills/ava-summary-remediation/
└── SKILL.md                         <- routing wrapper (resolves project_name, delegates)

src/modules/ava-fabric-agents/summary/agents/
└── summary-remediation-agent.md     <- frontmatter + Portuguese body (Phase 0-7)

src/modules/ava-fabric-agents/summary/utils/
└── remediate_summary.py             <- Python implementation of Phase 0-7,
                                         reuses sanitize_mmd()/_try_auto_fix() from
                                         validate_summary.py where possible
```

**Dispatch mode**: user-facing (SKILL.md required). SKILL.md resolves `project_name`, reads `agent-task-config.yaml` + `shared-context.md`, delegates to the agent `.md`.

**Shared resources reused**: `validate_summary.py` (`sanitize_mmd`, `_try_auto_fix`, the full `CHECKS` catalog including new `C11`), `build_summary_comprehensive.py` (called as a subprocess for the rebuild step, not re-implemented).

---

## 5. module.yaml Impact

`src/modules/ava-fabric-agents/summary/module.yaml`:

```yaml
agents:
  - id: ava-summary
    file: agents/summary-agent.md
    skill: ava-summary
  - id: ava-summary-validate
    file: agents/summary-validate-agent.md
  - id: ava-summary-remediation        # [NEW]
    file: agents/summary-remediation-agent.md
    skill: ava-summary-remediation
```

Bump `version: "1.0.0"` → `"1.1.0"` (MINOR — additive agent + additive validator checks, no breaking change to existing contracts).

The top-level `module.yaml` is not touched (existing phase/module, no new phase created).

---

## 6. Observability & Trace Propagation

N/A — standard LLM prompt-file agent. Context flows through `shared-context.md` per the SKILL.md wrapper, same as `ava-summary`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| agent-task.schema.json | NO | Standard `{project_name}` input, no new fields |
| agent-result.schema.json | NO | Standard success/artifacts/risk contract |

---

## 8. Implementation Phases

**Phase 0** — Speckit docs (`spec.md`/`plan.md`/`tasks.md` — this document set).

**Phase 1** — Permanent fixes (column A of the "Functional Changes by Component" table):
1. `summary-template.html`: unconditional removals (items 8, 14b, 14c, 15b, 19, 20, 22) + conditional hide-when-empty logic (`renderKPIs`, `renderPatterns`, `renderBC`, submenu nav visibility) + Risk table ID column removal.
2. `build_summary_comprehensive.py`: `parse_tobebn()` AS-IS fallback (item 21), `value-chain` removed from Deliverables classification (item 18b), root-cause parser checks for items 1-4/10/11/16/17.
3. `validate_summary.py`: new `C11` category (`C11.1`-`C11.16`), regression guards for every item above, `_fix_c11_*` functions where the fix is expressible as an HTML-level patch.

**Phase 2** — New agent (column B): `summary-remediation-agent.md` (Phase 0-7 body, pt-BR), `remediate_summary.py`, `.github/skills/ava-summary-remediation/SKILL.md`.

**Phase 3** — BDD: confirm spec section 4 scenarios map cleanly to Category 6 validation tasks in `tasks.md`.

**Phase 4** — Registration: `module.yaml`, `.github/copilot-instructions.md` (`### F8 — Summary` table), `summary-validate-agent.md` rule-count/category-catalog update, `CHANGELOG.md`.

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| Article IX (Clean Architecture) | Marked N/A | Agent is an LLM prompt + reporting/template tooling, not application code | N/A — no cross-layer coupling introduced |
| Single-PR scope | This feature touches 4 existing files + creates 6 new files | The 22 reported issues are tightly coupled (same template/builder/validator), splitting into multiple PRs would leave the summary inconsistently fixed mid-rollout | Traceability table in `spec.md` gives per-item review granularity even within one PR |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Unit (builder) | `python build_summary_comprehensive.py --project {test_project}` | `✅ SUCESSO!`, HTML matches all 22 fixes visually |
| Validation | `python validate_summary.py --project {test_project}` | Exit 0, all `C1`-`C11` checks pass |
| Remediation (standalone) | `python remediate_summary.py --project {test_project}` / `@ava-summary-remediation` | Idempotent on a clean summary; fixes a deliberately-broken/legacy one |
| Regression | Existing `validate_summary.py` C1-C9 suite | No existing check broken by C11 additions |
| Cross-project | Repeat unit+validation on ≥2 projects with different legacy/target stacks | CA02 — no hardcoded stack/project logic |

---

## Addendum A (2026-07-10) — Console errors, AST extraction wiring

See `spec.md` Addendum A for the full item list (23-33). Implementation-plan notes specific to this addendum:

- **No new agent files, no module.yaml changes.** All items are fixes within the existing `ava-summary`/`ava-summary-remediation` file set (`build_summary_comprehensive.py`, `summary-template.html`, `validate_summary.py`, `remediate_summary.py`).
- **`sanitize_mmd()` idempotency (item 25) is the highest-priority fix** — it lives in a *shared* function called by every summary build, not just this feature's synthesis path, so the bug compounded on every rebuild/remediation cycle across the whole pipeline, not only on `remediate_summary.py`-synthesized files.
- **AST extraction (`delphi-ast-raw/extraction/*.json`) is treated as an optional, additive tier**, never a required input — Constitution Article I (no hardcoded stack) extends here to "no hardcoded pipeline variant": projects without this folder must build identically to before.
- **New Guardrail 7** (spec.md) narrows the "never overwrite `outputs/`" rule specifically for self-repair of the agent's own tagged synthesized `.mmd` files — this is the one deliberate, documented exception beyond the original "only write if absent" rule.
- Version bump: `summary/module.yaml` stays at `1.1.0` (no new agent registered this round, pure bugfix/feature-extension to existing files) — if a future addendum adds a new agent or breaking contract change, bump then.

## Addendum C (2026-07-13) — F1 Test Baseline AS-IS path bug + remediation data-masking fix

See `spec.md` Addendum C for the full item list (48-51) and Guardrail 8. Implementation-plan notes specific to this addendum:

- **Root cause was a directory mismatch, not a missing parser** — `test-qa-asis.md` (asis-diagnostic module) always wrote to `asis/qa/`; `build_test_map()` only ever read `asis/` root. The fix (`_resolve_qa_artifact()`) is a single reusable resolver applied at every read site in `build_test_map()`, with a legacy-root fallback so already-generated projects are not broken by the fix.
- **User's literal instruction named the wrong (root) path** — matching the bug being fixed, not the real producer contract. Corrected to `asis/qa/test-map.md` after verifying `test-qa-asis.md`'s actual `## Output Contract`; flagged explicitly in spec.md Addendum C rather than silently deviating from the literal request.
- **Supersedes Addendum A item 32's Test Baseline claim** — that item recorded the AST JSON fallback as wired, but the call site used the stale `extraction/` path (never `compressed/`, per `specs/010`'s already-established convention). Items 49-50 close this out for real.
- **`remediate_summary.py` Rule C fix is the direct implementation of the user's explicit ask #4** ("if the summary agent doesn't add the test info, the remediation agent must do it") — reframed from "synthesize a placeholder whenever the root path is empty" (which actively masked the real bug) to "only synthesize when confirmed absent from every real/derivable source, including the AST fallback."
- No new agent files, no `module.yaml` changes. `summary-agent.md` 1.5.0→**1.6.0** (MINOR — new mandatory reads), `summary-remediation-agent.md` 1.2.0→**1.3.0** (MINOR — new heuristic + guardrail). `validate_summary.py` total check count (verified via `len(CHECKS)`, not just `C11.*`): 98 → **99**; `C11.*` subfamily: 33 → **34** (`C11.34`).

## Addendum D (2026-07-13) — F1 Banco de Dados AS-IS: consolidated view + 4 stale AST paths

See `spec.md` Addendum D for the full item list (52-55), Guardrail 9, and CA11/CA12. Implementation-plan notes specific to this addendum:

- **Narrower bug class than Addendum C** — the 4 primary `.md` sources (`schema-inventory.md`, `er-diagram.mmd`, `stored-procedures-map.md`) were already read from the correct `asis/db/` path; no root-vs-subdirectory mismatch here. Only the AST *fallback* tier (4 call sites) and one entire artifact (`business-logic-in-db.md`) were broken.
- **"Consolidada" satisfied without a new mega-widget** — the fix keeps the single existing `#s-f1-db` section as the one consolidation point; `business-logic-in-db.md` gets a new card inside that same section, alongside Schema/ER/SPs, not a separate page/section.
- **New `C11.35` is a source-code guard, not an output guard** — modeled on the `C11.22+` family (`_read_template_source()`), but reads `build_summary_comprehensive.py`'s own checked-in source (`_read_builder_source()`, new helper) instead of the template, since "a wrong path string reappeared in the code" can only be caught by inspecting the source, not generated HTML (the path is already baked in by build time).
- **Rule I (remediation) is intentionally conservative** — unlike Test Baseline's Rule C (which had a real masking bug to fix), there was no pre-existing DB-specific remediation rule at all. Rule I only ever synthesizes when the "no business logic" claim is provably true (0 SPs) — it does not attempt to guess or partially reconstruct `business-logic-in-db.md` content when SPs exist, since that content requires actual code analysis this script cannot perform.
- Version bumps: `summary-agent.md` 1.6.0→**1.7.0** (MINOR — new mandatory reads + business-logic-in-db.md), `summary-remediation-agent.md` 1.3.0→**1.4.0** (MINOR — Rule I + Guardrail 9). `validate_summary.py` total check count: 99 → **101** (`C11.35`, `C11.36`).
