# Agent Development Tasks: Dotnet Coder Backend — Guardrails G10 & G11

**Plan**: `specs/007-dotnet-compile-guardrails/plan.md`
**Agent ID**: `ava-stack-dotnet-backend` | **Phase**: `F3` | **Module**: `tech-stack`

> Change type: `modify-existing` — MINOR (1.0.0 → 1.1.0)
> Single file target: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Categories 3 and 4 are N/A (no schema changes; module.yaml already registered).
> Plan §8 phase-to-category mapping: Phase 0 = Cat 1; Phases 1+2 = Cat 2; Phase 3 = Cat 6; Phase 4 = Cat 7.

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before Category 2. All other frontmatter fields are unchanged;
only `version` changes. Output contract, allowed-tools, SKILL.md: no change.

- [ ] **1.1** Open `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` and verify existing frontmatter has only the four allowed fields (`name`, `version`, `description`, `allowed-tools`) with no extra keys (`phase`, `module`, `inputs`, etc.)
- [ ] **1.2** Bump `version` field from `"1.0.0"` to `"1.1.0"` in the YAML frontmatter of `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. Execute waves in order (Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 5).

- [ ] **2.1** **[Wave 1 — Structural repair]** Replace the entire corrupted G10+G11 region in `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` — starting from `### G10 — Namespace Conflict Between Bounded Contexts` through the end of the last G11 block (including all duplicated content) — with the clean, authoritative content specified in spec §6 (G10) and §7 (G11). The replacement must produce: **one G10 block followed by one G11 block** (file layout: G10 then G11; runtime execution order: G11 then G10 — see task 2.5 for confirmation). Ensure: no truncated XML comment, no duplicate sections, no orphaned code fences.
- [ ] **2.2** **[Wave 2 — G10 verification]** Read the G10 block written in task 2.1 and verify it exactly matches spec §6: (a) 4-step GLOB procedure is complete; (b) `⛔ G10 VIOLATION` blocking message contains all required fields (`Novo BC`, `Conflito com`, `Motivo`, `Ação requerida` options A and B); (c) canonical fix example includes both the XML `<RootNamespace>` block and the C# `using` alias example; (d) the XML comment is not truncated. If any deviation is found, edit the file to match spec §6.
- [ ] **2.3** **[Wave 3 — G11 verification]** Read the G11 block written in task 2.1 and verify it exactly matches spec §7: (a) 4-step procedure is complete (READ project-config → dotnet --version → compare → block/proceed); (b) `⛔ G11 VIOLATION` blocking message contains `Requerido`, `Instalado`, `Motivo`, and three numbered `Ação requerida` steps with a download URL; (c) canonical fix includes `global.json` with `rollForward: "latestMinor"` and the explanatory note; (d) no duplicate G11 content remains anywhere in the file. If any deviation is found, edit the file to match spec §7.
- [ ] **2.4** **[Wave 4 — Flow reference update]** In the `## Input Adicional — Docs Research Bundle` section of `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`, update the stale reference `→ PROSSEGUIR com guardrails G1-G9 existentes (non-blocking)` to `→ PROSSEGUIR com guardrails G1-G11 (G10-G11: pré-geração bloqueantes; G1-G9: durante geração)`. Then add a one-line category note at the top of the `## ⚠️ GUARDRAILS` section header to distinguish the two guard categories.
- [ ] **2.5** **[Wave 5 — Execution order confirmation]** Read the final file end-to-end and confirm: (a) **file layout** — G10 block appears before G11 block (top-to-bottom in file; this is the correct and intended order); (b) **runtime execution sequence** stated in the `## Input Adicional` section and/or the execution order diagram in G10 matches `[Pipeline mode check] → [Docs research bundle check] → G11 (SDK version) → G10 (namespace scan) → code generation`. File layout G10-then-G11 is intentional — the agent instructions explicitly direct G11 first via the execution order diagram (spec §6), regardless of file order. No file edit required if both (a) and (b) are satisfied.

---

## Category 3 — Shared Schema Updates

**SKIP — N/A.** Plan §7 confirmed: `agent-task.schema.json` and `agent-result.schema.json` require no changes. G10/G11 read from existing input fields; when blocking, no `AgentResult` is emitted.

---

## Category 4 — Module Registration

**SKIP — N/A.** `modify-existing` change type. `ava-stack-dotnet-backend` is already registered in `src/modules/ava-fabric-agents/tech-stack/module.yaml`. No new agent entry. No top-level `module.yaml` change. No SKILL.md change.

---

## Category 5 — Quality Gate Checklists

Can run after Category 2 completes. Tasks 5.1 and 5.2 are independent.

- [ ] **5.1** [P] Perform structural validation of `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`: (a) count G10 sections — exactly 1; (b) count G11 sections — exactly 1; (c) verify no code fence is left open (every triple-backtick opens and closes); (d) confirm the XML comment `<!-- ✅ Tipos com mesmo nome simples...Banking.Payments.Domain.Result  -->` is closed on the same line and not truncated; (e) confirm `⛔ G10 VIOLATION` appears exactly once; (f) confirm `⛔ G11 VIOLATION` appears exactly once.
- [ ] **5.2** [P] Verify all spec §9 Quality Gate Requirements are satisfied: frontmatter version is `"1.1.0"`; `G1-G9` reference updated to `G1-G11` with category note; G11 precedes G10 in the execution flow description; blocking messages match spec §6 and §7 literally; `allowed-tools` still includes `Bash` and `Glob`.

---

## Category 6 — Acceptance Validation & QA Integration

Can run in parallel with Categories 5 and 7 after Category 2 completes.

- [ ] **6.1** [P] Manually trace **Scenario 2** (G10 blocking — Priority P1) through the G10 procedure in the file: simulate two BCs `Banking.Titles` and `Banking.Payments` — confirm step 3 triggers HARD STOP via the root-segment check: `"Banking.Payments".Split('.')[0] == "Banking.Titles".Split('.')[0]` → `"Banking" == "Banking"` → **true** → HARD STOP. Confirm the `⛔ G10 VIOLATION` message includes the conflicting `.csproj` path, both `CS0104`/`CS0234` error codes in the Motivo, and both remediation options (A: rename namespace, B: separate host).
- [ ] **6.2** [P] Manually trace **Scenario 3** (G11 blocking — Priority P1) through the G11 procedure in the file: simulate `tobe_stack.backend_version: "10.0"` and `dotnet --version` output `8.0.404` — confirm `installed_version (8.0) < required_version (10.0)` triggers HARD BLOCK, confirm `⛔ G11 VIOLATION` message shows both version values, the NETSDK1045 root cause, and the download URL.
- [ ] **6.3** [P] Manually trace **Scenario 5** (both gates pass — Priority P1) and **Scenario 1** (G10 nominal, P2 — implicit): simulate `dotnet --version` = `10.0.100` and single BC `Banking.Titles` — confirm G11 passes (logs `SDK 10.0.100 ✅ compatível com alvo 10.0`), then G10 passes (`existing_namespaces` has only `Banking.Titles`; no root-segment conflict with itself), then generation proceeds. Confirm no VIOLATION messages are emitted in this path. This trace also implicitly satisfies Scenario 1 (single BC, no conflict).
- [ ] **6.4** [P] Map scenarios 1–5 to F5 QA pipeline traceability: confirm each scenario from spec §5 is traceable to a behavior rule (BR) that `ava-qa-behavior-mapping` can catalogue. Note: BDD format in spec §5 is already in Given/When/Then; no format conversion required.
- [ ] **6.5** [P] Document SC-7 scope boundary: spec §12 Success Criterion "zero dotnet build errors in a multi-BC scenario" is a **post-deploy acceptance criterion** — it requires a live environment, a real .NET project, and an actual `dotnet build` run, none of which are executable during prompt-file editing. Confirm in the completion checklist that SC-7 proxy coverage is tasks 2.2 (G10 procedure verified against corrected algorithm) + 6.1 (G10 manual trace). No edits to the agent `.md` are required for this task.

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Categories 5 and 6 after Category 2 completes.

- [ ] **7.1** [P] Add `CHANGELOG.md` entry for version `1.1.0` of `ava-stack-dotnet-backend`: change type MINOR; description: "Added pre-generation guardrails G10 (namespace conflict scan between BCs, HARD STOP on CS0104/CS0234 risk) and G11 (SDK version validation against tobe_stack.backend_version, HARD BLOCK on NETSDK1045). Repaired structural corruption (duplicate G11 block, truncated G10 XML comment) introduced during informal implementation. Updated flow reference from G1-G9 to G1-G11 with pre-generation vs. generation-time categorisation."
- [ ] **7.2** [P] Update `docs/agents-catalog.md` entry for `ava-stack-dotnet-backend`: bump version from `1.0.0` to `1.1.0`; add note to role summary: "Pre-generation gates: G11 validates SDK version ≥ tobe_stack.backend_version; G10 scans existing .csproj namespaces for conflicts before any .cs file is written."

---

## Completion Checklist

- [ ] All 5 active categories (1, 2, 5, 6, 7) complete
- [ ] Structural validation passed (task 5.1) — single G10, single G11, no open fences
- [ ] Quality gate requirements all satisfied (task 5.2)
- [ ] Scenarios 2, 3, and 5 manually traced and confirmed (tasks 6.1–6.3); SC-7 scope documented (task 6.5)
- [ ] `version: "1.1.0"` in frontmatter
- [ ] `G1-G11` reference in Docs Research Bundle section with category note
- [ ] `docs/agents-catalog.md` updated (task 7.2)
- [ ] `CHANGELOG.md` entry committed (task 7.1)

---

## Dependencies

```
Category 1 ─┬─► Category 2 ─┬─► Category 5 (parallel)
             │               ├─► Category 6 (parallel)
             │               └─► Category 7 (parallel)
             │
Categories 3, 4: SKIP (N/A)
```

## Parallel Execution Within Category 2

Tasks **2.1 → 2.2 → 2.3 → 2.4 → 2.5** must be executed **sequentially** (each wave depends on the previous wave completing).

## Parallel Execution After Category 2

Tasks **5.1, 5.2, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2** can all run in parallel once task 2.5 completes.

## MVP Scope

The minimum viable implementation is **Category 1 + Category 2** (tasks 1.1–2.5). Categories 5–7 are validation and documentation and can follow in a second pass if needed. However, given the single-file scope (15 total tasks), full execution in one pass is recommended.
