Ready for review
Select text to add comments on the plan
SpecKit Planning Layer — AVA Fabric Agents
Context
The F4 code-generation agents (.NET, Angular, React) produce code with architectural inconsistencies, incomplete implementations and compilation failures. The audit of projects/nopcommerce-02-cli-ava measured: prototype fidelity 13%, business rules 17%, test coverage vs test-cases.md 7%, OpenAPI conformance 14%, ADR adherence 38%, and dotnet build FAILED (1 + 35 + 8 cascading errors) while the pipeline's own report declared Build Status: ✅ PASS (Simulated).

The hypothesis under evaluation is that inserting SpecKit (Constitution → Specification → Plan → Tasks) between design and codegen will fix this.

It will not — not on its own. Investigation found a mechanical defect upstream of any prompt-quality concern, and a second one in how F4 is dispatched. SpecKit is the right layer, but it only pays off once those two are fixed. Both fixes are in scope here.

Finding 1 — the TO-BE artifacts never reached the code generator
load_context() ("ava-pipeline-runner-cli.py":743-779 and sdk_engine.py:135-176) injects artifact bodies by walking sorted(outputs.rglob("*")) and taking the first N with suffix in (.md, .mmd, .yaml, .json) — N = 60 in the production runner, 30 in the CLI engine. Alphabetically, asis/ precedes tobe/. Measured against the real project:

Injected into every step after F1	Count
asis/ast-raw/** (raw AST dumps)	30
other asis/**	30
tobe/** — anything at all	0
The window closes exactly at asis/docs/screen-flow-manifest.json. Everything F4 needed sits past it:

Artifact the coders require	Position	Injected?
tobe/docs/api-map.md	116	✗
tobe/docs/architecture-blueprint.md	117	✗
tobe/docs/architecture-decision-matrix.md	118	✗
tobe/docs/backlog-tobe.md	119	✗
tobe/docs/openapi/openapi-spec.yaml	144	✗
tobe/docs/regras-negocio.md	145	✗
tobe/docs/tech-framework-document.md	151	✗
tobe/docs/wave-plan.md	154	✗
tobe/prototype/design-tokens.json	164	✗
tobe/prototype/screen-list.md	167	✗
tobe/qa/test-cases.md	169	✗
tobe/prototype/index.html	—	✗ never eligible (.html not in the suffix allowlist)
asis/docs/business-rules.md landed at #57 — the only reason business rules scored 17% instead of 0%. This single defect explains every audit axis, and it independently confirms audit root causes RC-04, RC-05 and RC-07. The P2C protocol is well written and was never dishonoured by the model — the files simply never arrived.

Consequence for this work: SpecKit artifacts written to outputs/speckit/ sort after asis/ too. Without Phase 0 they would be exactly as invisible as the TO-BE artifacts are today, and the whole layer would measure zero improvement.

Finding 2 — F4 is one call, not a pipeline
execution-report_20260811_193456.md records F4 as a single dispatch: 624,278 input tokens, 82,878 output tokens against a 128,000 cap, 14.9 min, 140 files (77 .cs + 40 .ts) in one response. The SDK engine loads only the orchestrator's spec_path and forbids tools, so the 13 coder agents and the 13 build_cycle_templates declared in tech-stack/module.yaml — including the 4955-line coder-angular-frontend.md that carries the P2C rules — never loaded and never ran. pipeline_mode: "build-cycle" in project-config had no effect.

Generating a full solution inside one output budget is what produced the "vertical slice" truncation (audit RC-01) and the simulated build reports (RC-02).

Finding 3 — a SpecKit consumer already exists with no producer
shared/readiness-gate.md criterion C2 (HARD, blocks every Build Cycle wave) globs outputs/tobe/docs/spec-kit/*.md, checks six mandatory sections, and reads signoffs.spec_kit_approved. Nothing in the repo produces that file. The nopcommerce-02 readiness gate nevertheless returned APPROVED at 92.5% with "spec_kit_approved": true — a gate passing on a signature for an artifact that does not exist. This layer becomes its producer, and C2 gets repointed at the real path.

Approach
Five increments. Phase 0 is a hard prerequisite — shipping Phases 1-2 without it produces documents nobody reads.

Phase 0 — Deterministic context delivery
Replace "first N alphabetically" with an explicit, declared, fail-fast input manifest.

Create src/shared/tools/context_manifest.py as the single implementation, imported by both runners (the repo's documented failure mode is duplicated sources of truth — agent_registry.py, artifact_gate_tobe.py and pipeline-dag/F1.yaml all carry warnings about it, so this must not become a mirror):

def resolve(project: str, step_inputs: dict, cfg: dict) -> tuple[str, list[str]]
# returns (context_block, missing_mandatory)
Semantics, borrowed from the tier vocabulary already used in the coder Input Contracts (CRÍTICOS / IMPORTANTES / OPCIONAIS) and from slice: in pipeline-dag/F1.yaml:

mandatory: — missing ⇒ the step does not run, exit code 2. Never silently degraded.
advisory: — missing ⇒ WARN, recorded in the step log, execution continues.
Globs allowed (tobe/docs/openapi/*.yaml); ordering follows declaration order, not the filesystem; per-file char budget stays configurable.
Suffix allowlist gains .html, .ts, .cs, .scss, .sql, .props, .csproj.
When nothing is declared for a step, fall back to today's behaviour so untouched steps keep working.
Wire-up:

pipeline.steps[] in ava-pipeline.yaml gains an optional inputs: {mandatory: [...], advisory: [...]} block; Step in pipeline_plan.py:43-54 gains the field.
sdk_engine.load_context() and run_step() take the step and delegate.
"ava-pipeline-runner-cli.py" imports the same module — its hardcoded PIPELINE list gains the same inputs key per entry.
Declare inputs for the existing F2a/F3/F4/F5/F6 steps too. F4's mandatory set is the gap this whole investigation exposed.
Phase 1 — The speckit module (7 agents)
New module src/modules/ava-fabric-agents/speckit/, executing as pipeline group F3S between F3 Prototype and F4 Stack Generation. ava-tobe-spec and outputs/tobe/docs/spec/ are already taken, hence the ava-speckit-* namespace.

Agents live in speckit/agents/ (the registry only globs */agents/**/*.md), bodies in pt-BR, frontmatter per Constitution §II with comma-separated allowed-tools (rule AT-001 rejects the space-separated form the constitution text shows).

Agent	Trigger	Mandatory inputs	Outputs
ava-speckit-orchestrator	SK	—	dispatch + execution-log.json
ava-speckit-constitution	GC	project-config.yaml, tobe/docs/architecture-blueprint.md, tech-framework-document.md, architecture-decision-matrix.md, decisions/ADR-*.md	constitution.md
ava-speckit-specification	GS	constitution.md + one source artifact per spec	specs/spec-*.md
ava-speckit-prototype-spec	GP	constitution.md, prototype/index.html, screen-list.md, design-tokens.json, openapi/*.yaml, figma-spec.md (advisory)	specs/spec-prototype.md
ava-speckit-planning	GL	constitution.md, one specs/spec-*.md	plans/plan-*.md
ava-speckit-tasks	GT	constitution.md, one plans/plan-*.md	tasks/tasks-*.md + traceability rows
ava-speckit-compliance	AC	constitution.md, all specs/plans/tasks, traceability.json	compliance-report.md, compliance-status.json
Output tree — projects/{project_name}/outputs/speckit/:

constitution.md
specs/    spec-business-rules.md · spec-api.md · spec-api-map.md · spec-backlog.md
          spec-waves.md · spec-test-cases.md · spec-prototype.md
plans/    plan-<spec>.md          (1:1 with specs/)
tasks/    tasks-<spec>.md         (1:1 with plans/)
traceability.json                 ← machine-readable spine (immutable after F3S)
tasks-progress.json                  ← progress ledger, runner-owned (see Phase 3 harness)
ava-agents-progress.txt           ← append-only narrative log
compliance-report.md · compliance-status.json
execution-log.json
One specification per consumed artifact, as required — the Specification Agent is dispatched once per source, not once overall, so each call carries only its own source in context:

Source	Spec
asis/docs/business-rules.md + .json + tobe/docs/regras-negocio.md	spec-business-rules.md
tobe/docs/openapi/*.yaml	spec-api.md
tobe/docs/api-map.md	spec-api-map.md
tobe/docs/backlog-tobe.md	spec-backlog.md
tobe/docs/wave-plan.md + migration/wave-model.json	spec-waves.md
tobe/qa/test-cases.md	spec-test-cases.md
tobe/prototype/*	spec-prototype.md
Every spec carries the ten mandatory sections (Functional Objectives, Business Rules, Domain Model, Application Flows, Acceptance Criteria, Error Handling, Security Requirements, Dependencies, Edge Cases, Test Scenarios) plus the six sections readiness-gate C2 checks for (## Context, ## Input, ## Processing, ## Output, ## Examples, ## Failure Modes), so one artifact satisfies both contracts.

spec-prototype.md additionally carries the ten prototype sections (Overview, Screen Inventory, Navigation Flow, Component Spec, Form & Validation, API Integration Mapping, Frontend Architecture Mapping, UX & Accessibility, Test Scenarios, Implementation Tasks Input). Its extraction procedure is not invented — it reuses the parsing rules already specified in prototype-conversion-protocol.md §2 (header-indexed screen-list.md parse, the per-screen <!-- Prototype metadata --> trailer carrying Screen/BC/API/AS-IS ref/UX rules, showScreen() call-graph for navigation, :root custom properties for tokens). P2C stops being advisory prose read by an agent and becomes the documented input procedure of a phase that has a deterministic gate behind it.

Phase 2 — Traceability spine and deterministic gates
traceability.json is the load-bearing artifact, not the prose matrices. The audit found the existing traceability-matrix.md marked all 15 rows ✅ for classes that do not exist — "a matriz é um falso positivo integral". Machine-checkable schema, one row per task:

{ "task_id": "T-PROTO-004", "spec_id": "SPEC-PROTO-007",
  "source_artifact": "tobe/prototype/screen-list.md", "source_anchor": "Carrinho de Compras",
  "screen_id": "screen-cart", "plan_id": "PLAN-PROTO-002",
  "rule_ids": ["BR-CHECKOUT-001"], "api_ops": ["POST /api/v1/cart/items"],
  "test_ids": ["TC-CART-003"], "target_files": ["frontend/src/app/cart/cart.component.ts"] }
New suite src/shared/checks/suites/speckit_traceability.py, following the CHK-ID convention of ftm_traceability.py:

Check	Rule
CHK-SK-001..003	constitution / every spec / every plan exists and is non-trivial
CHK-SK-004	every specs/spec-*.md has a plans/plan-*.md and a tasks/tasks-*.md
CHK-SK-005	every task in tasks/*.md has a row in traceability.json
CHK-SK-006	every row resolves to a real source_artifact + anchor found in that file
CHK-SK-007	every BR-* in business-rules.json reaches ≥1 task
CHK-SK-008	every OpenAPI operation reaches ≥1 task
CHK-SK-009	every TC-* in test-cases.md reaches ≥1 task
CHK-SK-010	every task has acceptance criteria and declared target_files
CHK-SK-011	tasks-progress.json is 1:1 with traceability.json by task_id — no orphans, no phantoms
CHK-SK-012	every verified entry carries evidence with a real exit code and an existing log path
New suite prototype_coverage.py — the gate audit RC-04 says was missing:

Check	Rule
CHK-PROTO-001	every included row of screen-list.md has a screen in spec-prototype.md
CHK-PROTO-002	every <section class="screen" id="screen-*"> in index.html is inventoried
CHK-PROTO-003	every screen has a route, ≥1 task and ≥1 test scenario
CHK-PROTO-004	every form in the prototype has a validation spec and a task
CHK-PROTO-005	every design-tokens.json key is mapped to a target-stack token
CHK-PROTO-006	every declared API endpoint exists in the OpenAPI contract
CHK-PROTO-007	source_warnings[] from screen-list.md are propagated, not dropped
Note: CheckContext.__init__ currently loads the summary HTML eagerly and raises when it is absent (context.py:50-55). SpecKit gates run long before any summary exists — make html/html_path lazy properties. Small, contained, no behaviour change for existing suites.

Gate wiring. speckit/utils/artifact_gate_speckit.py follows the GATES shape of artifact_gate_tobe.py (kind, items[{path, base, produced_by, advisory}], blocks, on_fail) with base: "speckit" added, and derives its items from pipeline-dag/F3S.yaml rather than mirroring them — F1.yaml's own header warns against becoming another hand-maintained mirror. Entry gate blocks F3S if the TO-BE set is incomplete; exit gate blocks F4 unless both check suites are green.

Phase 3 — F4 fan-out driven by tasks
Add optional foreach: to the step schema:

- phase: "F4"
  group: "F4"
  agent: "ava-stack-orchestrator"
  trigger: "SG"
  foreach:
    source: "outputs/speckit/tasks/*.md"
    group_by: "task_group"
    agent_from: "target_stack"      # dotnet → ava-stack-dotnet-backend, angular → …
  inputs:
    mandatory: [ "outputs/speckit/constitution.md",
                 "outputs/speckit/plans/plan-{spec}.md",
                 "outputs/speckit/tasks/tasks-{spec}.md" ]
The runner loop at ava_pipeline.py:347-398 expands one declared step into N executions, each dispatching the real coder agent (whose 4955-line prompt finally loads) with only its own slice in context. This is what takes the output budget off the critical path: N bounded responses instead of one 82,878-token response against a 128,000-token ceiling.

Where pipeline-dag/F4.yaml is present and --engine copilot is selected, the same task groups feed the existing DAG runner — the two engines share the decomposition, not the mechanism.

Long-running-agent harness
Once F4 is N calls instead of one, it becomes a long-running agent problem: each call starts with a fresh context window and must know what has already been built. Anthropic's effective harnesses for long-running agents describes the pattern — an initializer context that produces the durable artifacts, then iteration contexts that each advance one feature and leave structured updates behind. The SpecKit layer already is the initializer; it just has to emit the harness artifacts too.

Article artifact	This pipeline
initializer agent (first context window)	ava-speckit-orchestrator — F3S produces constitution, specs, plans, tasks
feature_list.json — 200+ entries, all "passes": false	outputs/speckit/tasks-progress.json — one entry per task, all "status": "pending"
claude-progress.txt	outputs/speckit/ava-agents-progress.txt — append-only ledger, newest last
init.sh	outputs/tobe/source-code/verify.ps1 — restore, build, test, lint; the one command every iteration runs
git history	outputs/.runs/{run_id}/run.json plus one commit per completed task group
one feature per session	one task group per foreach expansion
tasks-progress.json — JSON, not Markdown, for exactly the reason the article gives: the model is far less likely to rewrite or quietly reshape a JSON file. Entries mirror traceability.json by task_id and stay 1:1 with it:

{ "task_id": "T-PROTO-004", "spec_id": "SPEC-PROTO-007", "group": "frontend-angular",
  "priority": "P1", "depends_on": ["T-PROTO-001"],
  "status": "pending",
  "acceptance": ["route /cart resolves", "CHK-PROTO-003 green for screen-cart"],
  "evidence": null, "run_id": null, "attempts": 0 }
Two files, two lifetimes, deliberately not merged: traceability.json is immutable once F3S completes (checksummed by the exit gate — a task cannot lose its provenance mid-run), tasks-progress.json is the mutable ledger.

The one deliberate departure from the article. There, the agent flips passes after testing. Here it may not. Audit RC-02 found the pipeline declaring Build Status: ✅ PASS (Simulated — toolchain validation pending) while dotnet build actually failed, and the traceability matrix marking all 15 rows ✅ for classes that do not exist. An agent that self-reports completion is precisely the failure this project already has. So:

Agents never write tasks-progress.json. The step wrapper does, after running verify.ps1 and the check suites, from real exit codes. status moves pending → in_progress → verified | failed and evidence records the command, exit code and log path.
A task whose files were written but whose verification failed lands on failed, not verified, and is re-queued with attempts + 1 — capped, then surfaced rather than retried forever.
ava-agents-progress.txt is agent-written prose (what was built, what was learned, what surprised it) and carries no status claims. Plain text, not Markdown — it is a log, and the extension keeps it from being mistaken for a deliverable by the summary and artifact-size suites. Narrative and state are separated so a confident narrative cannot contaminate the ledger.
Iteration preamble. context_manifest.py prepends a fixed block to every fan-out step, so the "read the progress notes and pick the next feature" routine is harness-enforced rather than remembered:

outputs/speckit/constitution.md — the governing rules, every call, no exceptions
outputs/speckit/ava-agents-progress.txt — last N entries
tasks-progress.json filtered to this group: what is verified, what this task depends on
plans/plan-{spec}.md + tasks/tasks-{spec}.md — only the slice for this task group
the target files already on disk that this task will touch
The agent is told which task it owns; it does not choose. Selection is foreach expansion over dependency-ordered pending entries — deterministic, resumable, and it survives a crashed run, because a re-invocation reads the ledger and picks up exactly where the previous one stopped.

Phase 4 — Close the loop on the consumers
readiness-gate.md C2 — repoint the glob from outputs/tobe/docs/spec-kit/*.md to outputs/speckit/specs/*.md, keeping the six-section check. First time the criterion has a real producer.
Coder Input Contracts — in coder-dotnet-backend.md, coder-angular-frontend.md, coder-react-frontend.md: promote prototype_index / prototype_screens / design_tokens from OPCIONAIS (WARN) to CRÍTICOS (HARD STOP) for frontend coders, and add constitution.md / plan-*.md / tasks-*.md as CRÍTICOS. Degrading silently on a missing prototype is how a B2C catalogue became an admin CRUD table.
summary/data/artifact-map.yaml — register the seven agents and their outputs so the layer renders in the summary HTML; add rules to validate_summary.py.
Registry — add "speckit": "F3S" to PHASE_BY_MODULE, insert F3S into PHASE_ORDER after F3, add PHASE_NAMES["F3S"]. Check every consumer of these three constants (pipeline_observer.py, generate_observability_report.py, tests/tools/test_agent_registry.py) before landing.
Regenerate wrappers: python src/shared/tools/generate_agent_wrappers.py, verify with --check.
Files
New

Path	Role
src/shared/tools/context_manifest.py	Explicit input resolution — single implementation
src/modules/ava-fabric-agents/speckit/module.yaml	Module + agent registration
src/modules/ava-fabric-agents/speckit/agents/*.md	7 agent bodies
src/modules/ava-fabric-agents/speckit/templates/*.md	constitution / spec / prototype-spec / plan / tasks templates
src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py	Entry/exit gates, derived from F3S.yaml
src/shared/data/pipeline-dag/F3S.yaml	SpecKit DAG + per-agent input slices (source of truth)
src/shared/schemas/speckit-traceability.schema.json	traceability.json contract
src/shared/schemas/speckit-task-state.schema.json	tasks-progress.json contract
src/shared/tools/task_ledger.py	Ledger read/write + status transitions — runner-owned, never agent-owned
src/modules/ava-fabric-agents/speckit/templates/verify.ps1.tmpl	Per-stack restore/build/test/lint script emitted into source-code/
src/shared/checks/suites/speckit_traceability.py	CHK-SK-001..010
src/shared/checks/suites/prototype_coverage.py	CHK-PROTO-001..007
tests/tools/test_context_manifest.py	Mandatory-missing ⇒ exit 2; declaration order; glob expansion
tests/tools/test_task_ledger.py	Status transitions only from real exit codes; resume picks the right next task; agent-written state rejected
tests/ava-fabric-agents/speckit/test_artifact_gate_speckit.py	Gate ↔ F3S.yaml coherence
specs/039-speckit-planning-layer/{spec,plan,tasks}.md	This work, documented via SpecKit
docs/plan/speckit-to-be-tak.md	Architecture dossier — the 12 deliverables
Modified

Path	Change
src/shared/data/ava-pipeline.yaml	inputs: + foreach: schema; F3S steps between F3 and F4
src/shared/tools/pipeline_plan.py	Step.inputs, Step.foreach, expansion
src/shared/tools/sdk_engine.py	Delegate context to context_manifest; .html eligible
src/shared/tools/ava_pipeline.py	foreach expansion in the run loop
ava-pipeline-runner-cli.py	Import context_manifest; PIPELINE + PHASE_GROUPS + PHASE_ARTIFACT_CONTRACT gain F3S
src/shared/tools/agent_registry.py	PHASE_BY_MODULE / PHASE_ORDER / PHASE_NAMES
src/shared/checks/context.py	Lazy html / html_path
src/shared/checks/__init__.py	Register the two suites in _SUITES
src/modules/ava-fabric-agents/shared/readiness-gate.md	C2 glob → outputs/speckit/specs/*.md
src/modules/ava-fabric-agents/tech-stack/agents/coder-{dotnet,angular,react}-*.md	Input Contract tiers
src/modules/ava-fabric-agents/summary/data/artifact-map.yaml	F3S artifacts → HTML sections
module.yaml (root)	Register the speckit module
CHANGELOG.md	Spec 039 entry
Audit correlation
#	Category	Root cause (evidence)	Mitigation	Residual risk
1	Missing Architecture Guidance	ADRs, decision matrix, tech-framework at positions 118/151 — never injected (RC-06)	Phase 0 mandatory inputs; constitution.md as the single governing document; ava-speckit-compliance + CHK-SK gates	Constitution can still restate a decision imprecisely; compliance agent is LLM-judged for prose rules
2	Missing Business Context	regras-negocio.md at 145 never injected; business-rules.md at 57 barely made it — 17% (RC-07)	spec-business-rules.md per rule with acceptance criteria; CHK-SK-007 forces every BR-* to reach a task	A rule mis-transcribed into the spec propagates downstream — mitigated by anchor verification, not eliminated
3	Missing Specifications	No intermediate contract existed between TO-BE prose and codegen	7 specs, ten mandatory sections, one per source artifact	Spec quality bounded by source quality; screen-list.md already ships with degradation warnings
4	Missing Task Decomposition	140 files in one 82,878-token response against a 128k cap (RC-01)	Atomic tasks + Phase 3 foreach fan-out	Cross-file consistency across N calls needs the constitution to hold it together
5	LLM Coding Limitations	8 real C# errors (OwnsMany over IReadOnlyCollection, Swashbuckle × OpenApi 2.0.0)	Not a SpecKit problem — ava-stack-build-validator / build-fixer must run for real	Highest residual. Requires real dotnet build execution, which is orthogonal to this work
6	Pipeline Orchestration	Sub-agents and build-cycle chain never dispatched under --engine sdk; build gate accepted PASS (Simulated) (RC-02)	Phase 3 fan-out dispatches real coders; deterministic gates replace narrative ✅	Simulated-build acceptance is a separate defect — flagged, not fixed here
Not in scope, but must be said: the audit reports the two high-severity CVEs, the unpersisted password hash in RegisterCustomerHandler.cs:27-29, and plaintext credentials committed in outputs/tobe/source-code/.env. No planning layer retroactively fixes those. The .env credentials need rotating regardless of what happens to this plan.

Decision framework — what the evidence supports
Dimension	Expected effect	Basis
Compilation success	High, from Phases 0+3, not from SpecKit documents	Errors came from a single truncated response; smaller scoped calls plus real build validation address it directly
Architectural compliance	High	Blueprint/ADRs go from 0% delivered to mandatory; the compliance agent gets a machine-checkable spine
Functional completeness	High	15/21 missing API operations and 7/15 missing screens were never specified as work items; CHK-SK-008 and CHK-PROTO-001 make omission a gate failure
Test coverage	Medium-high	CHK-SK-009 forces all 46 TCs into tasks; whether the generated tests are good remains an LLM limit
Security compliance	Medium	LGPD/Argon2id/multi-store become traced tasks; correct crypto implementation is still LLM-dependent
Code quality	Medium	Better inputs raise the floor; they do not make the model a senior engineer
Honest framing: roughly 60-70% of the expected gain comes from Phase 0 and Phase 3 — delivering the artifacts and decomposing the work. SpecKit's specific contribution is traceability, gate-ability and completeness accounting: it is what makes the improvement verifiable and repeatable rather than incidental. Shipping SpecKit without Phases 0 and 3 would produce a beautiful document set with unchanged audit numbers, and would discredit the approach.

Roadmap
Increment	Contents	Exit criterion
0	context_manifest.py, inputs: schema, both runners, inputs for F2a/F3/F4/F5/F6	--dry-run prints the resolved input set per step; a missing mandatory input exits 2
1	Module, 7 agents, templates, F3S.yaml, registry + wrappers	ava-pipeline list --phases shows F3S; a real F3S run emits the full tree
2	traceability.json schema, both check suites, gates, lazy CheckContext	python -m src.shared.checks --project P --suite speckit_traceability green; exit gate blocks F4 when red
3	foreach: in schema/plan/loop; F4 fan-out; task_ledger.py, tasks-progress.json, ava-agents-progress.txt, verify.ps1, iteration preamble	F4 runs as N steps, each dispatching a real coder agent; killing the run mid-way and re-invoking resumes at the next pending task
4	readiness-gate C2, coder Input Contracts, artifact-map, summary	Full run on nopcommerce-02; audit axes re-measured
The same harness discipline applies to building this feature, one level up: specs/039-…/tasks.md uses the repo's existing - [ ] T001 [P] [US1] checkbox format as its feature list, and each increment ends with a commit plus a progress note. The pattern is identical whether the long-running agent is generating a customer's ERP or implementing spec 039 — durable state on disk, one unit of work per context, verification before status.

Documentation (specs/039-… + docs/plan/speckit-to-be-tak.md) is written first and updated at each increment, using the repo's own .specify/templates/ — the 12 requested deliverables map as: Current State Assessment / Gap Analysis / Audit Findings Correlation / Risk Assessment / ROI to the dossier; Future State Architecture / Integration Architecture / Agent Design Specs / Orchestration Flow / Artifact Dependency Matrix / Traceability Matrix to spec.md + plan.md; Implementation Roadmap to tasks.md.

Verification
# Phase 0 — the defect that started this, proven fixed
python src/shared/tools/ava_pipeline.py run -p nopcommerce-02-cli-ava --phase F4 --dry-run
#   expect: resolved input list contains tobe/docs/architecture-blueprint.md,
#           openapi/*.yaml, regras-negocio.md, prototype/index.html, screen-list.md
python -m pytest tests/tools/test_context_manifest.py -q

# Regression on the declared order — 12 steps become 12 + F3S
python src/shared/tools/ava_pipeline.py list --phases
python -m pytest tests/tools/test_pipeline_plan.py tests/tools/test_agent_registry.py -q

# Phase 1 — agents discoverable, wrappers in sync
python src/shared/tools/agent_registry.py --agent ava-speckit-constitution
python src/shared/tools/generate_agent_wrappers.py --check

# Phase 2 — gates fail loudly on today's artifacts, pass after a real F3S run
python -m src.shared.checks --project nopcommerce-02-cli-ava --suite prototype_coverage
python -m src.shared.checks --project nopcommerce-02-cli-ava --suite speckit_traceability
python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py `
  --project nopcommerce-02-cli-ava --gate exit --json     # exit 0 only when both suites green

# Phase 3 — F4 expands instead of running once
python src/shared/tools/ava_pipeline.py run -p nopcommerce-02-cli-ava --phase F4 --dry-run
#   expect: N steps, one per task group, each naming a real coder agent

# Phase 3 — the harness: resumability and an unfakeable ledger
python src/shared/tools/task_ledger.py -p nopcommerce-03-speckit --summary
#   expect: pending / in_progress / verified / failed counts, all pending after F3S
python src/shared/tools/ava_pipeline.py run -p nopcommerce-03-speckit --phase F4 --yes
#   ...interrupt with Ctrl-C partway through...
python src/shared/tools/ava_pipeline.py run -p nopcommerce-03-speckit --phase F4 --yes
#   expect: resumes at the first pending task; verified tasks are not regenerated
python -m pytest tests/tools/test_task_ledger.py -q
#   proves a task cannot reach `verified` without a real exit code — the RC-02 guard

# End to end, then re-measure the audit axes
python src/shared/tools/ava_pipeline.py run -p nopcommerce-03-speckit --all --yes
cd projects/nopcommerce-03-speckit/outputs/tobe/source-code/backend && dotnet build
python -m pytest tests/ -q
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat   # CA02, specs/033
Acceptance for the pilot, measured against the same seven axes as auditoria-codigo-gerado.md: dotnet build reaches 0 errors; screens present ≥ 14/15; business rules implemented ≥ 15/18; OpenAPI operations ≥ 19/21; both check suites green with zero orphan tasks and zero unreferenced sources.