# Agent Development Tasks: [AGENT_NAME]

**Plan**: `specs/[SPEC_BRANCH]/plan.md`
**Agent ID**: `ava-[PHASE]-[ROLE]` | **Phase**: `F[N]` | **Module**: `[MODULE_ID]`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.

<!--
  IMFAI STRUCTURE OVERRIDE
  ========================
  This project uses the IMFAI 7-category agent development structure instead of
  the standard SpecKit user-story/phase layout. When generating tasks.md:

  - USE these 7 categories as the task structure (not Phase 1/2/3 by user story)
  - USE the 1.1, 1.2... numbering format (not T001, T002...)
  - DO NOT add [US1]/[US2] user-story labels — use [P] for parallelizable tasks only
  - Fill each category with concrete tasks derived from plan.md and spec.md
  - Category 1 (frontmatter) always comes first — it unblocks all other categories
  - Categories 4, 5, 6, and 7 can all run in parallel after Category 2 completes

  The user stories from spec.md section 4 (Scenarios 1-3) map to:
  - Scenario 1 (Nominal P1) → drives Category 2 behavior and Category 6 BDD tasks
  - Scenario 2 (Edge P2) → drives additional Category 6 edge test stubs
  - Scenario 3 (Gate P1) → drives Category 2 quality gate logic and Category 5 checklist items
-->

---

## Category 1 -- Agent Frontmatter & Contract Definition

Must complete before any other category.

- [ ] **1.1** Create or locate `src/modules/ava-fabric-agents/[MODULE_FOLDER]/[agent-role].md`
- [ ] **1.2** Write YAML frontmatter with the correct fields (Article II):
  - `name: "ava-[PHASE]-[ROLE]"` — pattern `^ava-[a-z0-9-]+$`
  - `version: "1.0.0"`
  - `description: |` — Portuguese, ends with `Ativa com: "..."` phrases
  - `allowed-tools: Read, Write, Edit` — only valid Claude Code tool names
  - Do NOT add phase, module, inputs, outputs, or dependencies to frontmatter
- [ ] **1.3** Write `## Output Contract` YAML block in agent body using lowercase `{project_name}` paths
- [ ] **1.4** Verify output paths use correct phase folder:
  - F1: `outputs/asis/` | F2: `outputs/tobe/docs/` | F3: `outputs/tobe/source-code/`
  - F5: `outputs/qa/` | F7: `outputs/tobe/devops/` | F6: `outputs/deliverables/`
- [ ] **1.5** Declare dispatch mode (Constitution Article XI):
  - **User-facing**: create `.github/skills/ava-[PHASE]-[ROLE]/SKILL.md` that (1) resolves `project_name`, (2) reads `agent-task-config.yaml` + `shared-context.md`, (3) delegates to the agent `.md`
  - **Internal-only**: document dispatch method in agent header comment; confirm orchestrator `agents:` list references this agent

---

## Category 2 -- Agent Behavior & Instructions

Depends on Category 1.

- [ ] **2.1** Write **Responsibility** section (1-2 paragraphs)
- [ ] **2.2** Write **Input Contract** section (each field with type and example)
- [ ] **2.3** Write numbered, deterministic step-by-step instructions
  - Reference `src/shared/data/reference-architecture.yaml` for tech stack choices
  - Reference `src/shared/templates/diagrams/mermaid-guardrails.md` if generating diagrams
- [ ] **2.4** Write **Output Format** spec for each artifact
- [ ] **2.5** Add **Security Compliance** note (Constitution Article VII)
- [ ] **2.6** Write **Quality Gate Logic**: risk scoring, human_gate_required, next_agent

---

## Category 3 -- Shared Schema Updates

Skip if plan section 7 shows no schema changes.

- [ ] **3.1** Add fields to `src/shared/schemas/agent-task.schema.json`
- [ ] **3.2** Add fields to `src/shared/schemas/agent-result.schema.json`
- [ ] **3.3** [P] Validate: `python debug_schema.py`
- [ ] **3.4** [P] Update version comment with date and reason

---

## Category 4 -- Module Registration

Depends on Category 1.

- [ ] **4.1** Add agent entry to the **module-level** `module.yaml` (NOT the top-level one):
  - File: `src/modules/ava-fabric-agents/[MODULE_FOLDER]/module.yaml`
  - Add: `{ id: ava-[PHASE]-[ROLE], file: agents/[role].md, skill: ava-[PHASE]-[ROLE] }`
  - Omit `skill:` key if internal-only dispatch
- [ ] **4.2** Only update the top-level `module.yaml` if creating a brand-new phase/module
- [ ] **4.3** Verify `bmad_version: ">=6.0.0"` preserved in top-level `module.yaml`

---

## Category 5 -- Quality Gate Checklists

- [ ] **5.1** Identify checklist: F1/F2 `readiness-gate-checklist.md` | F5 `scenario-generator-checklist.md` | F7 `wave-gonogo-checklist.md`
- [ ] **5.2** Add items: artifact presence, completeness, gate correctness
- [ ] **5.3** [P] Verify `- [ ]` format

---

## Category 6 -- Acceptance Validation & QA Integration

Depends on Category 2.

> IMFAI agents are LLM prompt files, not compiled code. Validation is done by
> running the agent against a controlled test project, not by writing xUnit tests.

- [ ] **6.1** Confirm spec section 4 acceptance scenarios are complete and unambiguous:
  - Scenario 1 (Nominal P1): agent produces all expected artifacts
  - Scenario 2 (Edge P2): agent handles empty/missing inputs gracefully
  - Scenario 3 (Gate P1): agent correctly triggers `human_gate_required` when risk is high
- [ ] **6.2** [P] Run the agent against `projects/test-determinism/` to validate:
  - All output artifacts listed in `## Output Contract` are produced
  - Output files are non-empty and follow the correct format
  - No existing artifacts from other agents are modified or deleted
- [ ] **6.3** [P] Map acceptance scenarios to F5 QA pipeline inputs:
  - Copy or reference spec section 4 scenarios as input to `ava-qa-behavior-mapping`
  - Verify scenarios use the standard `BR-NNN` / `FR-NNN` traceability format
- [ ] **6.4** [P] Run any applicable validation scripts:
  - `python validate_events_pubsub.py` — if agent produces event/pub-sub diagrams
  - `python check_diag.py` — if agent produces Mermaid diagrams
  - `python debug_schema.py` — if agent modifies shared schemas
- [ ] **6.5** Confirm agent output passes the `readiness-gate-checklist.md` items added in Category 5

---

## Category 7 -- Documentation & Catalog Update

Can run parallel with Category 6.

- [ ] **7.1** [P] Update `docs/agents-catalog.md` (ID, version, phase, module, role summary, output artifacts)
- [ ] **7.2** [P] Add `CHANGELOG.md` entry (version bump type, description, schema changes)
- [ ] **7.3** [P] Update `docs/full-pipeline-guide.md` if phase flow changes
- [ ] **7.4** [P] Verify agent in module diagram (update if module.yaml changed)

---

## Completion Checklist

- [ ] All 7 categories complete
- [ ] SKILL.md created (if user-facing) or dispatch method documented in agent header (Article XI)
- [ ] `specify self check` -- no SpecKit updates pending
- [ ] Agent `.md` frontmatter validated
- [ ] `module.yaml` committed
- [ ] Agent validated against `projects/test-determinism/` — all output artifacts produced (Category 6)
- [ ] `docs/agents-catalog.md` updated
- [ ] `CHANGELOG.md` entry committed
