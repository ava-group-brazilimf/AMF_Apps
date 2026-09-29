# F4S — Git-Backed, Speckit-Driven Code Generation

> Branch: `albert-speckit-update`  
> Target merge: `feat/add-speckit-after-tobe-phase`  
> Related PR: #428

This document describes the refactor of the F4 (Tech Stack) phase into a
**Speckit-driven, git-backed, deterministic code generator**. Instead of a
fleet of per-language coder agents and scaffolders, a single generic codegen
agent (`ava-f4s-codegen-agent`) is dispatched once per SpecKit feature. Each
feature is implemented, verified, remediated if necessary, and committed inside
a per-stack git repository so the exact genesis of every file is traceable.

---

## 1. What changed

| Before | After |
|---|---|
| One coder agent per language (`coder-dotnet`, `coder-java`, `coder-python`, …) plus language-specific scaffolders. | One generic agent: `ava-f4s-codegen-agent`. Stack-specific knowledge is injected as the **first SpecKit feature** (`000-scaffold-{stack}`). |
| F4 ran as a monolithic generation step. | F4 fans out into one task per SpecKit feature, scheduled by the deterministic task ledger. |
| Generated code lived in a plain directory. | Each target stack is a git repo under `projects/{project}/outputs/tobe/source-code/{stack}/`. |
| Build was run once at the end, if at all. | Build verification runs after **every** feature; failures trigger up to 2 automatic remediations. |
| Failures were opaque. | Every attempt is recorded in `GENERATION_LOG.md`; persistent failures produce an embedded Compilation Failure Report; 3 consecutive skips abort F4. |

---

## 2. Orchestration overview

```mermaid
flowchart TD
    subgraph F3S["F3S — SpecKit Planning"]
        A[wave0 entry gate] --> B[wave1 constitution]
        B --> C[wave2 specs / wave3 plans / wave4 tasks]
        C --> D[wave4a f4s-scaffold-inject]
        D --> E[wave4b compile + ledger init + checks]
        E --> F[wave5 compliance]
    end

    F --> G["ava-pipeline.yaml F4 step<br/>foreach: ledger, agent_map routes every stack to ava-f4s-codegen-agent"]

    subgraph RUNNER["Pipeline Runner — ava-pipeline-runner-cli.py"]
        G --> H[_expand_ledger_phase builds one Step per pending task]
        H --> I{For each task in ledger order}
    end

    subgraph TASK["Per-task F4S execution"]
        I --> J[sdk_engine.run_step dispatches ava-f4s-codegen-agent]
        J --> K[Agent writes source files and creates<br/>.f4s/{feature}.done sentinel]
        K --> L[ava_pipeline.verify_task_step → _verify_f4_task]
        L --> M[f4s_deterministic_harness.run_task]
        M --> N[snapshot_before]
        N --> O[run_build_with_remediation]
        O --> P{Build passed?}
        P -->|yes| Q[reset consecutive skips<br/>snapshot_after<br/>git add + commit]
        P -->|no| R[remediation callback re-dispatches agent<br/>with build output in prompt]
        R --> O
        O -->|after 3 attempts| S[skip spec + embed Compilation Failure Report in GENERATION_LOG.md]
        S --> T{3 consecutive skips?}
        T -->|yes| U[abort_needed = true → runner stops]
        T -->|no| V[continue to next task]
    end
```

---

## 3. Agents, tools and files

### 3.1 New agents / modules

| File | Responsibility |
|---|---|
| `src/modules/ava-fabric-agents/tech-stack/agents/f4s-codegen-agent.md` | Generic codegen agent spec. Reads the feature spec/plan/tasks, the tree snapshot, and the existing source tree; writes only the files for that feature; creates a sentinel file. |
| `src/shared/tools/f4s_scaffold_injector.py` | Reads `project-config.yaml`, resolves target stacks, and emits a synthetic SpecKit feature `000-scaffold-{stack}` for each stack, copying the matching language scaffold template. |
| `src/shared/tools/f4s_deterministic_harness.py` | Orchestrates the per-task cycle: git repo, tree snapshots, build loop, remediation callback, skip reporting, and abort logic. |
| `src/shared/tools/f4s_build_runner.py` | Runs the stack-specific build command and captures stdout/stderr/exit code. |
| `src/shared/tools/f4s_git_helper.py` | Thin wrapper around `git init/add/commit/status`. |
| `src/shared/tools/f4s_generation_log.py` | Writes and reads `GENERATION_LOG.md` and `.f4s/f4s-state.json`. |
| `src/shared/tools/f4s_tree_snapshot.py` | Produces a Markdown/JSON snapshot of the source tree. |
| `tests/tools/test_f4s_scaffold_injector.py` | Unit tests for scaffold injection. |
| `tests/tools/test_f4s_deterministic_harness.py` | Unit tests for the build/remediate/skip/abort cycle. |
| `tests/tools/test_ava_pipeline_f4.py` | Tests for F4 integration into `ava_pipeline.py`. |

### 3.2 Modified agents / files

| File | What changed |
|---|---|
| `src/shared/data/ava-pipeline.yaml` | Removed the standalone F4S step. The F4 step now fans out from the ledger and maps every supported `target_stack` to `ava-f4s-codegen-agent`. |
| `src/shared/data/pipeline-dag/F3S.yaml` | Added `wave4a` (`f4s-scaffold-inject`) before the compiler/ledger waves. |
| `src/shared/tools/speckit_task_compiler.py` | Added `_add_stack_scaffold_edges()` so every non-scaffold task implicitly depends on its stack's `000-scaffold-{stack}` task. |
| `src/shared/tools/pipeline_plan.py` | `Step` now carries `feature`, `target_stack`, `task_id`, and `remediation_context`. `build_prompt()` appends remediation context when present. |
| `src/shared/tools/ava_pipeline.py` | Added `_verify_f4_task()`, `_build_failure_context()`, and `_make_remediation_callback()`. `verify_task_step()` routes F4 tasks through the deterministic harness. |
| `ava-pipeline-runner-cli.py` | Loads runner config, passes `client`/`model`/`cfg` to F4 verification, handles skip vs abort, and stops the pipeline when `abort_needed` is true. |
| `src/shared/tools/f4s_feature_discovery.py` | Normalized traceability v1/v2 reading and deterministic feature ordering. |
| `tests/tools/test_pipeline_plan.py` | Updated expectations and added v2 ordering test. |
| `tests/tools/test_pipeline_config.py` | Updated step count expectations. |
| `tests/tools/test_f4s_phase.py` | Updated expectations for the merged F4/F4S phase. |

---

## 4. Scaffold-first injection

Speckit treats each feature as a self-contained module. To prevent later specs
from ignoring the intended project layout, the **first feature of every stack**
is always the scaffold.

1. `f4s_scaffold_injector.py` reads `project-config.yaml` and resolves
   `tobe_stack.backend_framework` and `tobe_stack.frontend_framework`.
2. For each stack it locates the matching template:
   `src/modules/ava-fabric-agents/tech-stack/scaffolds/{stack}-scaffold.md`
   (falling back to `default-scaffold.md`).
3. It writes a synthetic SpecKit feature to
   `projects/{project}/outputs/tobe/speckit/specs/000-scaffold-{stack}/`:
   - `spec.md` — the scaffold instructions.
   - `plan-graph.json` — declares `artifact:scaffold:{stack}`.
   - `task-fragment.json` — exposes `verify_command` for that stack.
4. `speckit_task_compiler._add_stack_scaffold_edges()` inserts implicit
   `depends_on` edges from every later task of the same `target_stack` to the
   scaffold task, guaranteeing that the layout is created before any
   business-rule or API feature runs.

The scaffold feature is therefore **a normal SpecKit feature**, but its source
is a hand-curated engineering template rather than an LLM-generated spec.

---

## 5. Context injected into each SpecKit feature

The codegen agent does not run in a vacuum. At dispatch time, the runner builds
a rich prompt composed of three layers:

1. **System prompt** (`sdk_engine.build_system_prompt`):
   - Project config and shared context.
   - All mandatory TO-BE artifacts declared in `ava-pipeline.yaml` F4 inputs:
     architecture blueprint, tech framework document, ADRs, OpenAPI specs,
     business rules, API map, security architecture, prototype `index.html`,
     screen list, design tokens, Speckit constitution, and every
     `outputs/tobe/speckit/specs/*/plan.md` / `tasks.md`.
   - The agent skill itself (`f4s-codegen-agent.md`).

2. **User prompt** (`Step.build_prompt(project)`):
   - `@{agent} project: {project} | feature: {feature}`.
   - If this is a remediation run, the prompt is appended with the previous
     build command, exit code, and full stdout/stderr.

3. **Tree snapshot** (generated by the harness):
   - Before verification, the harness writes
     `.f4s/snapshots/{feature}-before.md` inside the stack repo.
   - The agent spec instructs the agent to read this snapshot so it knows
     exactly which files already exist and must be preserved.
   - After a successful build, `.f4s/snapshots/{feature}-after.md` is written
     and committed alongside the source files.

Because `sdk_engine.load_context` also lists files already present under
`outputs/tobe/source-code/{stack}/`, every subsequent feature sees the evolving
tree both through the explicit snapshot and through the general context.

---

## 6. Build-verify-remediate-skip-abort loop

For each task the harness executes:

```text
build (attempt 1)
  ├─ passed → snapshot_after → git commit
  └─ failed → remediation callback (attempt 1) → build (attempt 2)
        ├─ passed → snapshot_after → git commit
        └─ failed → remediation callback (attempt 2) → build (attempt 3)
              ├─ passed → snapshot_after → git commit
              └─ failed → skip spec + Compilation Failure Report in GENERATION_LOG.md
```

Rules:

- **Maximum 3 build attempts** = 1 initial + 2 remediations.
- **Remediation callback** re-dispatches `ava-f4s-codegen-agent` via
  `sdk_engine.run_step()` with the failing build output appended to the prompt.
- **On persistent failure** the spec is skipped, a warning is emitted, and a
  `Compilation Failure Report` section is appended to `GENERATION_LOG.md`. The
  report includes each attempt's command/exit code, the remediation hypothesis,
  and the last build output.
- **Abort gate**: if 3 specs are skipped **consecutively**, the harness sets
  `abort_needed = true`; `ava-pipeline-runner-cli.py` stops F4 and reports that
  human intervention is required.
- A successful spec resets the consecutive-skip counter.

---

## 7. Git history and changelog

Each target stack has its own repo:

```text
projects/{project}/outputs/tobe/source-code/{stack}/
├── .git/
├── .gitignore          # excludes build artifacts, node_modules, f4s-state.json, …
├── .f4s/
│   ├── f4s-state.json
│   ├── snapshots/
│   │   ├── 000-scaffold-{stack}-before.md
│   │   ├── 000-scaffold-{stack}-after.md
│   │   ├── 001-business-rules-before.md
│   │   └── …
│   └── {feature}.done  # sentinel written by the agent
└── GENERATION_LOG.md   # human-readable chronological log
```

- Git is initialized by `f4s_deterministic_harness.ensure_repo()` on the first
  task of the stack.
- An initial `.gitignore` is committed automatically.
- **Commits only happen when the build passes.** Each successful feature is
  committed with a message such as `feat(dotnet): implement 001-business-rules`.
- Skipped specs are **not** committed; their trace is kept in
  `GENERATION_LOG.md` and `f4s-state.json`.

---

## 8. Testing and verification

### 8.1 Unit tests

```bash
python -m pytest tests/tools/test_f4s_scaffold_injector.py \
                 tests/tools/test_f4s_deterministic_harness.py \
                 tests/tools/test_ava_pipeline_f4.py -v
```

These cover:

- Scaffold spec generation for every supported stack.
- Implicit scaffold dependency edges in the task compiler.
- Build loop logic, including pass, single remediation, multiple remediation,
  skip, consecutive-skip counting, and abort.
- `ava_pipeline.py` routing of F4 steps into `_verify_f4_task()`.

### 8.2 Pipeline-level tests

```bash
python -m pytest tests/tools/test_pipeline_plan.py \
                 tests/tools/test_pipeline_config.py \
                 tests/tools/test_f4s_phase.py -v
```

These verify:

- Step count after removing the standalone F4S phase.
- Ledger fan-out produces one `Step` per pending task.
- `feature` and `target_stack` are propagated correctly.

### 8.3 Current results

- 69 focused F4S tests pass.
- Full `tests/tools` suite: **249 passed, 1 pre-existing failure** in
  `test_agent_registry.py::test_esteira_sem_violacoes` listing version/module
  mismatches in unrelated agents.

### 8.4 Manual smoke test checklist

1. Run F3S for a project with `tobe_stack.backend_framework = dotnet`.
2. Confirm `outputs/tobe/speckit/specs/000-scaffold-dotnet/` exists.
3. Run F4 and verify `outputs/tobe/source-code/dotnet/.git/` was created.
4. Check `GENERATION_LOG.md` for one entry per feature, ending with a commit
   hash for successful features.
5. Inspect `git log --oneline` inside the stack repo to see one commit per
   successful spec.

---

## 9. References

- SpecKit planning layer: `src/shared/data/pipeline-dag/F3S.yaml`
- Pipeline order: `src/shared/data/ava-pipeline.yaml`
- Generic codegen agent: `src/modules/ava-fabric-agents/tech-stack/agents/f4s-codegen-agent.md`
- Deterministic harness: `src/shared/tools/f4s_deterministic_harness.py`
- Scaffold injector: `src/shared/tools/f4s_scaffold_injector.py`
- Runner integration: `src/shared/tools/ava_pipeline.py`, `ava-pipeline-runner-cli.py`
