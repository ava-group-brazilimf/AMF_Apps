# Agent Development Tasks: ava-prototype (modificação)

**Plan**: `specs/023-prototype-optional-artifacts/plan.md`
**Agent ID**: `ava-prototype` | **Phase**: `F3` | **Module**: `prototype`

> Change Type: **modify-existing** — editing `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`.
> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 1.5 is N/A (SKILL.md unchanged). Category 3 is N/A (no schema changes). Category 4 is partial (agent already registered; only version bump).

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before any other category.

- [x] **1.1** Open `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md` and confirm current frontmatter fields
- [x] **1.2** Bump `version` field from `"1.1.0"` to `"1.2.0"` in the YAML frontmatter block
- [x] **1.3** Replace the `description` field content (after `description: |`) with the updated Portuguese text from spec §2:
  - Keep existing lines about UX heuristics and activation phrases
  - Add the new sentence: `"Utiliza business-rules.md como fonte primária obrigatória; design-system e user-journeys são opcionais — ausência exibe aviso e solicita confirmação do usuário antes de prosseguir com a geração do protótipo."`
- [x] **1.4** Verify `allowed-tools: Read, Write, Edit` is unchanged and no extra frontmatter keys were added
- [x] **1.5** ~~N/A — SKILL.md at `.github/skills/ava-prototype/SKILL.md` is unchanged~~

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1.

- [x] **2.1** Read the full current `## Pre-Execution — Leitura Obrigatória` section in `prototype-agent.md` to understand the exact text being replaced
- [x] **2.2** Rewrite the entire `## Pre-Execução — Leitura Obrigatória` section in **one atomic edit** (do not apply in two passes — the artifact classification and the `╔═══╗` decision box are one contiguous block):
  - Replace the `★`/`○` artifact list with the canonical `╔═══╗` pre-flight table (data-model.md §1, “Canonical Pre-flight Table Format”) written in **Brazilian Portuguese** (Constitution Article V)
  - Use the following artifact classifications:
    - `business-rules.md` → `outputs/asis/docs/business-rules.md` → MANDATORY → Yes (BLOQUEADO)
    - `bounded-context-map.md` → `outputs/tobe/docs/bounded-context-map.md` → MANDATORY → Yes (BLOQUEADO)
    - `design-system.md` → `outputs/tobe/docs/design-system.md` → OPTIONAL → No (AGUARDANDO CONFIRMAÇÃO)
    - `user-journeys.md` → `outputs/tobe/docs/user-journeys.md` → OPTIONAL → No (AGUARDANDO CONFIRMAÇÃO)
    - `api-map.md` → OPTIONAL → No (fallback to openapi-spec.yaml — unchanged from current)
    - `functional-requirements.md` → OPTIONAL → No (enrichment skipped — unchanged from current)
  - Replace all prose blocking rules within the same section; the rewrite spans both the old classification list and the old prose rule in one operation
- [x] ~~**2.3** Replaced by the atomic rewrite in 2.2 — no separate edit required~~
- [x] **2.4** Add the decision logic block immediately after the table (data-model.md §1, "Pre-flight Decision Logic"):
  - IF mandatory missing → `DECISÃO: BLOQUEADO` → stop; write no outputs; log `{event: "end", status: "blocked"}`
  - IF optional missing → `DECISÃO: AGUARDANDO CONFIRMAÇÃO` → show quality impact → prompt `Continue? [yes/no]`
    - IF yes → `DECISÃO: PROSSEGUIR COM AVISOS`
    - IF no → log `{event: "end", status: "cancelled", cancellation_reason: "user declined optional-artifact warning"}`; stop
  - ELSE → `DECISÃO: PROSSEGUIR`
- [x] **2.5** Add quality impact messages for each optional artifact (data-model.md §3):
  - `design-system.md` absent: `"Sem design-system.md, o protótipo utilizará tokens de design genéricos. Cores de marca, biblioteca de componentes e especificações de layout não serão aplicadas."`
  - `user-journeys.md` absent: `"Sem user-journeys.md, as telas serão derivadas apenas das regras de negócio. Fluxos multi-etapa, happy/sad path e navegação entre telas não poderão ser modelados com precisão."`
- [x] **2.6** [P] Add fallback behaviour prose for each absent optional artifact (research.md R5 and R6):
  - `design-system.md` absent → agent uses inline CSS custom properties already defined in the agent body
  - `user-journeys.md` absent → agent derives screens from `business-rules.md` sections and `bounded-context-map.md` BCs; each top-level BC produces one CRUD screen; navigation is simplified to a flat menu
- [x] **2.7** [P] Add new section `## Registro de Execução` (in Brazilian Portuguese) to the agent body:
  - Instruct agent to write a `start` log entry **immediately upon agent invocation — before any pre-flight check, DECISION output, or file I/O** to `projects/{project_name}/outputs/tobe/prototype/execution-log.json`
  - This ordering guarantee covers all execution paths: the start entry is always the first action, even when the execution is about to be blocked or will be cancelled after user input
  - Instruct agent to write an `end` log entry **after all outputs are produced** (or after blocked/cancelled decision)
  - Include the exact JSON schema from data-model.md §2 for both `start` and `end` entries
  - Specify append-mode: if the file does not exist, create it; if it does exist, append the new entry before the closing `]`
  - Specify that `trace_id` is copied unchanged from the AgentTask context (Constitution Article VIII)
- [x] **2.8** Update the screen-list.md generation instruction (wherever `screen-list.md` content is specified):
  - When one or more optional artifacts were absent and the user confirmed: prepend a `## Warnings` section to `screen-list.md` as defined in data-model.md §4
  - When all artifacts present: no `## Warnings` section

---

## Category 3 — Shared Schema Updates

**N/A** — plan §7 confirms no changes to `agent-task.schema.json` or `agent-result.schema.json`. Skip entirely.

---

## Category 4 — Module Registration

Agent is already registered. Only version sync required.

- [x] **4.1** ~~N/A — agent already registered in `src/modules/ava-fabric-agents/prototype/module.yaml`~~
- [x] **4.2** Bump `version` field in `src/modules/ava-fabric-agents/prototype/module.yaml` from `"1.1.0"` to `"1.2.0"` to stay in sync with the agent frontmatter
- [x] **4.3** Verify `bmad_version: ">=6.0.0"` is preserved in the top-level `module.yaml` (no change expected)

---

## Category 5 — Quality Gate Checklists

- [x] **5.1** Confirm no F3-specific `readiness-gate-checklist.md` exists under `src/modules/ava-fabric-agents/prototype/` (none found — no checklist file to update)
- [x] **5.2** Verify the spec §5 Quality Gate Requirements checklist is fully `[x]` — all 9 items must be checked before marking this category complete
- [x] **5.3** [P] Confirm pre-flight decision table covers all 4 input states: PROCEED / AWAITING CONFIRMATION (design-system absent) / AWAITING CONFIRMATION (user-journeys absent) / BLOCKED

---

## Category 6 — Acceptance Validation & QA Integration

Depends on Category 2.

- [x] **6.1** Confirm all 4 spec scenarios are handled by the modified agent:
  - Scenario 1 (Nominal P1): all artifacts present → `DECISÃO: PROSSEGUIR` → prototype generated → log `status: "success"`
  - Scenario 2 (Optional missing P1): optional absent → `DECISÃO: AGUARDANDO CONFIRMAÇÃO` → prompt → yes path generates prototype + warns; no path cancels + logs `status: "cancelled"`
  - Scenario 3 (Mandatory missing P1): mandatory absent → `DECISÃO: BLOQUEADO` → names `ava-asis-documentation` as prerequisite → log `status: "blocked"`
  - Scenario 4 (Logging P2): both `start` and `end` entries written on all execution paths
- [x] **6.2** [P] Run the modified agent against `projects/Meu-ERP/` (or equivalent test project) to validate:
  - Scenario A (quickstart.md): all 6 artifacts present — pre-flight shows all ✅ and prototype is generated
  - Scenario B (quickstart.md): `design-system.md` absent — prompt is shown, after `yes` prototype generated, `screen-list.md` has `## Warnings`
  - Scenario C (quickstart.md): optional absent, user types `no` — no output files written, log has `status: "cancelled"`, `AgentResult.success` is `false`, and `AgentResult.next_agent` is unset
  - Scenario D (quickstart.md): `business-rules.md` absent — `DECISÃO: BLOQUEADO`, no outputs
- [x] **6.3** [P] Map spec section 4 acceptance scenarios to F5 QA pipeline inputs:
  - Provide spec §4 scenario text as input to `ava-qa-behavior-mapping` when the QA phase runs
  - Verify traceability references use `BR-NNN` / `FR-NNN` format where applicable
- [x] **6.4** [P] Verify `execution-log.json` after each validation run:
  - Contains exactly two entries per run: `event: "start"` and `event: "end"`
  - `status` value matches the execution path: `"success"` / `"warning"` / `"blocked"` / `"cancelled"`
  - `trace_id` is present in both entries and identical to the input context value
  - `missing_optional` array is populated when optional artifacts were absent
- [x] **6.5** [P] Confirm `AgentResult` produced by the modified agent passes JSON Schema validation against `src/shared/schemas/agent-result.schema.json`:
  - No schema changes were made (plan §7) — the existing agent result structure must remain conformant
  - Verify `cancellation_reason` does **not** appear in `AgentResult` JSON (it lives only in `execution-log.json`)
  - Verify `AgentResult.success` is `false` on both `blocked` and `cancelled` paths

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6.

- [x] **7.1** [P] Update `docs/agents-catalog.md`: change `ava-prototype` version from `1.1.0` to `1.2.0` and update the role summary to note that optional artifact handling and execution logging were added
- [x] **7.2** [P] Add `CHANGELOG.md` entry for version `1.2.0` (research.md R7):

  ```markdown
  ## [1.2.0] — 2026-07-21

  ### Changed

  - `ava-prototype`: `design-system.md` and `user-journeys.md` reclassified as optional inputs.
  - `ava-prototype`: `outputs/asis/docs/business-rules.md` added as mandatory primary input.
  - `ava-prototype`: Pre-flight replaced with canonical table format (MANDATORY/OPTIONAL/MISSING/DECISION).
  - `ava-prototype`: Confirmation prompt added when optional artifacts are absent.
  - `ava-prototype`: Start/end execution log entries written to `outputs/tobe/prototype/execution-log.json`.
  ```

- [x] **7.3** [P] No pipeline flow change — `docs/full-pipeline-guide.md` does not require update (F3 position unchanged)
- [x] **7.4** [P] Verify module diagram reflects updated version; no structural changes to `module.yaml` agents list

---

## Completion Checklist

- [x] All 7 categories complete (Category 3 skipped per N/A)
- [x] SKILL.md unchanged and functional (user-facing dispatch confirmed)
- [x] `specify self check` — no SpecKit updates pending
- [x] Agent `.md` frontmatter validated: `version: "1.2.0"`, correct description, no extra keys
- [x] `module.yaml` version bumped to `"1.2.0"` and committed
- [x] Agent validated against test project — all 4 quickstart scenarios pass and AgentResult schema validated (Category 6, tasks 6.2 + 6.5)
- [x] `docs/agents-catalog.md` updated
- [x] `CHANGELOG.md` entry committed

---

## Dependencies (task order)

```
Category 1 (1.1 → 1.2 → 1.3 → 1.4)
  └─ Category 2 (2.1 → 2.2 → 2.3 → 2.4 → 2.5)
       ├─ [P] 2.6 (fallback prose)
       ├─ [P] 2.7 (execution logging section)
       └─ 2.8 (screen-list warnings)
            ├─ Category 4 (4.2, 4.3) ─── [P] ───┐
            ├─ Category 5 (5.1 → 5.2 → 5.3) ────┤
            ├─ Category 6 (6.1 → 6.2 → 6.3 → 6.4) ──┤
            └─ Category 7 (7.1, 7.2, 7.3, 7.4) ─ [P] ┘
```

**Parallelizable after Category 2 completes**: Categories 4, 5, 6, and 7 can all start in parallel.
**MVP scope**: Categories 1 + 2 deliver the functional change. Categories 4–7 are registration/validation work.
