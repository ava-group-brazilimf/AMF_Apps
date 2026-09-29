# Agent Development Tasks: Agent Pipeline Observability

**Plan**: `specs/002-agent-pipeline-observability/plan.md`
**Agent ID**: `ava-master-orchestrator` (metadata-only) | **Phase**: cross-cutting | **Module**: `master-orchestrator`

> This PBI is retrospective documentation of an already-shipped feature.
> Category 2 has exactly one real task (a metadata fix); everything else
> already implemented. Categories 3 and 4 are SKIP (no schema or module.yaml
> changes). Complete categories sequentially. Mark [P] for tasks
> parallelizable within a category.

---

## Category 1 — Version & Contract Verification

- [ ] **1.1** Confirm current frontmatter/Changelog drift in `master-orchestrator.md`
  File: `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md`
  ```bash
  head -6 src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  grep -n "^| 1\.2\.0" src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  ```
  **Expected (before fix)**: frontmatter shows `version: "1.1.0"`; Changelog row shows `1.2.0 | 2026-07-02 | ...`.

- [ ] **1.2** [P] Confirm both tools' CLI surfaces match `README.md`
  ```bash
  python src/shared/tools/pipeline_observer.py --help
  python src/shared/tools/agent_observability.py --help
  ```

- [ ] **1.3** [P] Confirm `openpyxl` import guard exists in both exporters
  ```bash
  grep -n "openpyxl not installed" src/shared/tools/pipeline_observer.py src/shared/tools/agent_observability.py
  ```

- [ ] **1.4** [P] Confirm `AGENT_CATALOG` row count matches between the two files that embed it
  ```bash
  grep -c '{"agent":' src/shared/tools/pipeline_observer.py
  grep -c '{"agent":' src/shared/tools/generate_observability_report.py
  ```
  **Expected**: both counts equal (currently 54); if they diverge, the duplication noted in plan.md Complexity Tracking has drifted — flag for a follow-up PBI.

---

## Category 2 — Implementation

Only one real gap exists after Phase 0 research (plan.md). Everything else in
the tool suite is already implemented and verified in Category 1/6.

- [ ] **2.1** Bump `master-orchestrator.md` frontmatter `version` from `"1.1.0"` to `"1.2.0"`
  File: `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md`, line 3.
  **Criterio de aceite**:
  ```bash
  grep -n '^version' src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  ```
  returns `version: "1.2.0"`, matching the existing Changelog entry.

---

## Category 3 — Shared Schema Updates

**SKIP** — plan.md §7 confirms: `agent-task.schema.json` NO, `agent-result.schema.json` NO.
Observability metrics live entirely outside the AgentTask/AgentResult contract.

---

## Category 4 — Module Registration

**SKIP** — plan.md §5 confirms no `module.yaml` exists under
`src/modules/ava-fabric-agents/master-orchestrator/`. Nothing to register.

---

## Category 5 — Quality Gate Checklists

- [ ] **5.1** Confirm the Article VIII characterization is accurate — no OpenTelemetry/trace_id wiring exists in the observability code path
  ```bash
  grep -in "opentelemetry\|trace_id\|w3c" src/shared/tools/pipeline_observer.py src/shared/tools/agent_observability.py
  ```
  **PASS** if zero matches — confirms the "partial compliance" framing in plan.md's Constitution Check is accurate, not understated.

- [ ] **5.2** [P] Confirm the Article V body-prose finding and decide fix-or-defer
  ```bash
  sed -n '812,820p' src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  ```
  If confirmed English prose (as documented in research.md §4), either (a) leave as-is per this PBI's "document only" scope decision, or (b) open a follow-up PATCH task to translate the appendix body to pt-BR — do not silently fix inline as part of this documentation pass.

- [ ] **5.3** [P] Confirm no existing quality gate was touched by this feature
  ```bash
  grep -c "human_gate_required" src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  ```
  **Expected**: count unchanged from before this PBI (feature is additive/documentation-only, not gate logic).

---

## Category 6 — Acceptance Validation

Run each quickstart scenario from [quickstart.md](./quickstart.md) and record pass/fail.

- [ ] **6.1** **CA01/CA02/CA03 — Nominal run, 4-sheet Excel, correct header** — see quickstart.md
- [ ] **6.2** [P] **CA04/CA05 — Failed agent tracked with error_detail** — see quickstart.md
- [ ] **6.3** [P] **CA06 — Cost arithmetic** — see quickstart.md
- [ ] **6.4** [P] **CA07 — Dashboard before finalize** — see quickstart.md
- [ ] **6.5** [P] **CA08 — Import-json happy + malformed** — see quickstart.md
- [ ] **6.6** [P] **CA09 — Compare two runs** — see quickstart.md (uses existing sample files in `docs/optimization/`)
- [ ] **6.7** **CA10 — Negative check: inline wiring absence** — see quickstart.md; **this check is expected to currently show the gap, not pass as "closed"**

- [ ] **6.8** Run the full CA01→CA09 happy-path sequence end-to-end once, back to back, against a fresh `Meu-ERP-001` run to confirm no interaction bugs between commands:
  ```bash
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init --run-type full-pipeline --model "Claude Opus 4.6" && \
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-asis-orchestrator --phase F1 --version 2.18.0 --status completed --tokens-in 50000 --tokens-out 30000 --duration-ms 374000 && \
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track --agent ava-stack-build-validator --phase F3 --version 2.3.0 --status failed --error-detail "TOOLCHAIN_UNAVAILABLE" --tokens-in 8000 --tokens-out 1200 --duration-ms 15000 && \
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 dashboard && \
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report && \
  echo "=== ALL PASS ==="
  ```

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Category 6.

- [ ] **7.1** [P] Confirm `docs/agents-catalog.md` intentionally excludes `ava-master-orchestrator` (catalog is phase-scoped) — record decision, do not add an entry
  ```bash
  grep -in "master-orchestrator" docs/agents-catalog.md
  ```
  **Expected**: zero matches, confirmed intentional per research.md §5 — no catalog change needed.

- [ ] **7.2** [P] Update `.github/copilot-instructions.md` SPECKIT block to point at this feature's plan
  ```bash
  grep -A 3 "SPECKIT START" .github/copilot-instructions.md
  ```
  Update the block to:
  ```markdown
  <!-- SPECKIT START -->
  For additional context about technologies to be used, project structure,
  shell commands, and other important information, read the current plan at
  `specs/002-agent-pipeline-observability/plan.md`
  <!-- SPECKIT END -->
  ```

- [ ] **7.3** Add a `CHANGELOG.md` (repo root) entry documenting this spec-kit documentation pass
  File: `CHANGELOG.md` — new entry dated 2026-07-03, distinct from the internal
  `1.2.0` Changelog row already inside `master-orchestrator.md` itself. Note:
  confirmed no existing root `CHANGELOG.md` entry covers this feature today.

- [ ] **7.4** [P] Confirm `docs/full-pipeline-guide.md` doesn't need updating
  ```bash
  grep -in "observability\|pipeline_observer" docs/full-pipeline-guide.md
  ```
  Decide whether to add a reference to the new tool; not required to close this PBI.

---

## Completion Checklist

- [ ] Category 1 verifications recorded (frontmatter/Changelog drift confirmed before fix)
- [ ] Task 2.1 applied: frontmatter `version` reads `1.2.0`
- [ ] Category 3 skipped (no schema changes)
- [ ] Category 4 skipped (no module.yaml changes)
- [ ] Category 5 quality-gate findings recorded (Article VIII partial, Article V decision made explicit)
- [ ] All 10 CA-ID acceptance scenarios in Category 6 run and recorded, including CA10's expected-gap result
- [ ] `docs/agents-catalog.md` scope decision recorded (Category 7.1)
- [ ] `copilot-instructions.md` SPECKIT block updated (Category 7.2)
- [ ] `CHANGELOG.md` entry added (Category 7.3)

---

## Dependency Graph

```
Category 1 (Verify contracts)
    │
    ├─► Category 2 (Task 2.1 — version bump)     — blocks Category 5.3, 6.8 final re-check
    │       │
    │       └─► Category 5 (Gates)       ─┐
    │       └─► Category 6 (Acceptance)  ─┤─► Category 7 (Docs) — all can run in parallel
    │                                     ┘
    └─► [Category 3 SKIP]
    └─► [Category 4 SKIP]
```

## Parallel Execution Opportunities

Tasks marked **[P]** within each category can run concurrently:
- **Category 1**: 1.2, 1.3, 1.4 parallel with 1.1
- **Category 5**: 5.2, 5.3 parallel with 5.1
- **Category 6**: 6.2–6.6 all independent and parallel after 6.1
- **Category 7**: all 4 tasks parallel with each other and with Category 6
