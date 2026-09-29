# Agent Development Tasks: Reliability Pipeline Evolution

**Plan**: `specs/001-reliability-pipeline-evolution/plan.md`
**Agent ID**: `modify-existing` | **Phase**: `F3 — Tech Stack` | **Module**: `tech-stack`

> Change type is **modify-existing** — no new agent files, no new SKILL.md, no module.yaml changes.
> Categories 1 and 4 are scoped to verification only (implementations already deployed).
> Category 3 is skipped — plan section 7 confirms no schema changes.
> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.

---

## Category 1 — Version & Contract Verification

Verify all existing agent frontmatter and output contracts match the spec before proceeding.

- [ ] **1.1** Verify `build-validator-agent.md` frontmatter: `name: "ava-stack-build-validator"`, `version` ≥ `1.1.0`, `allowed-tools` includes `Bash, Grep`
  File: `src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md`
  ```bash
  head -8 src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md
  ```

- [ ] **1.2** Verify `build-fixer-agent.md` frontmatter: `name: "ava-stack-build-fixer"`, `version` ≥ `1.1.0`, output contract contains `lockfile_updated: boolean`
  File: `src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md`
  ```bash
  grep -n "^version\|lockfile_updated" src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md | head -5
  ```

- [ ] **1.3** [P] Verify `coder-angular-frontend.md` frontmatter: `name: "ava-stack-angular-frontend"`, output contract references `.eslintrc.json`
  File: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`
  ```bash
  grep -n "^version\|eslintrc" src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md | head -5
  ```

- [ ] **1.4** [P] Verify `build_runner.py` exposes all required flags: `--runtime`, `--normalize-path`, `--node-version`, `--detect-runtime`, `--image`
  File: `src/shared/utils/build_runner.py`
  ```bash
  python src/shared/utils/build_runner.py --help 2>&1 | head -30
  ```

- [ ] **1.5** Verify `project-config.yaml` template has both new fields: `tobe_stack.node_version` and `quality_gates.cve_policy`
  File: `projects/_template/context/project-config.yaml`
  ```bash
  grep -n "node_version\|cve_policy\|accepted_exceptions" projects/_template/context/project-config.yaml
  ```

---

## Category 2 — Implementation: Config Template

Only one implementation gap remains after Phase 0 research. Task 2.1 was applied during plan generation — verify and mark complete.

- [ ] **2.1** Confirm `cve_policy` block is present in `projects/_template/context/project-config.yaml` under `quality_gates`
  ```bash
  grep -A 10 "cve_policy:" projects/_template/context/project-config.yaml | head -12
  ```
  **Expected**: `mode: "zero_tolerance"`, `accepted_exceptions: []`, and comment block with example exception.

- [ ] **2.2** Verify `projects/Meu-ERP/context/project-config.yaml` already contains `cve_policy` (identified as present at line 333)
  ```bash
  sed -n '330,345p' projects/Meu-ERP/context/project-config.yaml
  ```
  If the Meu-ERP block is missing `mode:` or `accepted_exceptions:` fields, sync from the template.

- [ ] **2.3** Verify `build-validator-agent.md` Step F3.5 reads `quality_gates.cve_policy` correctly — mode, accepted_exceptions, expiry comparison
  ```bash
  grep -n "cve_policy\|CVE_POLICY_MODE\|expiry\|zero_tolerance\|exceptions_allowed" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -15
  ```

- [ ] **2.4** Verify `build-validator-agent.md` Step B0.3 enforces `node_version` guardrail — never uses `frontend_version` for `NODE_IMAGE`
  ```bash
  grep -n "GUARDRAIL\|NUNCA usar\|NODE_IMAGE\|node_version\|frontend_version" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -12
  ```

- [ ] **2.5** Verify `build-validator-agent.md` Step F3 lockfile recovery — dispatches new fixer cycle when `lockfile_updated: false`
  ```bash
  grep -n "lockfile_updated\|out of sync\|novo ciclo\|new.*fixer" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -8
  ```

- [ ] **2.6** Verify `build-validator-agent.md` Step F3 ESLint detection — flat config + legacy + SKIP with WARN
  ```bash
  grep -n "eslint.config.js\|eslintrc\|No ESLint\|SKIP lint" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -8
  ```

- [ ] **2.7** Verify `build-fixer-agent.md` lockfile protocol — `npm install` required after `package.json` change + `lockfile_updated: boolean` in output
  ```bash
  grep -n "lockfile_updated\|npm install\|PROIBIDO.*lockfile" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md | head -10
  ```

- [ ] **2.8** Verify `coder-angular-frontend.md` generates all 7 ESLint devDependencies, lint target in `angular.json`, and Step 2.2.1 (`.eslintrc.json`)
  ```bash
  grep -n "angular-eslint\|typescript-eslint\|\"eslint\"\|builder:lint\|2\.2\.1\|eslintrc.json" \
    src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md | head -12
  ```

- [ ] **2.9** Verify `build_runner.py` Podman path normalization produces `C:/...` format on MSYS2
  ```bash
  python src/shared/utils/build_runner.py --normalize-path "C:\\Users\\dev\\project" --runtime podman
  # Expected: C:/Users/dev/project
  python src/shared/utils/build_runner.py --normalize-path "C:\\Users\\dev\\project"
  # Expected: //c/Users/dev/project  (Docker/default)
  ```

- [ ] **2.10** Verify `build_runner.py` emits warning when `--node-version` differs from framework-implied version
  ```bash
  python src/shared/utils/build_runner.py --image angular 17 --node-version 22 2>&1
  # Expected: WARNING about version discrepancy + image: node:22-alpine
  ```

---

## Category 3 — Shared Schema Updates

**SKIP** — plan section 7 confirms: `agent-task.schema.json` NO, `agent-result.schema.json` NO.
`lockfile_updated` is internal to `fix_result`, not an AgentResult-level field.

---

## Category 4 — Module Registration

**SKIP** — plan section 5 confirms all three agents already registered in
`src/modules/ava-fabric-agents/tech-stack/module.yaml`. No new agents created.

---

## Category 5 — Quality Gate Checklists

- [ ] **5.1** Verify `ava-stack-orchestrator` Step 0.9 correctly reads `build_runner.mode` and routes to `--runtime {CONTAINER_CLI}` in `build_runner.py` calls
  ```bash
  grep -n "build_runner.mode\|CONTAINER_CLI\|runtime.*podman\|runtime.*docker" \
    src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md | head -10
  ```

- [ ] **5.2** [P] Verify the orchestrator Steps 6a and 8 pass `CONTAINER_CLI` when invoking `build_runner.py --normalize-path`
  ```bash
  grep -n "normalize-path\|runtime.*CONTAINER_CLI" \
    src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md | head -8
  ```

- [ ] **5.3** [P] Confirm CVE policy gate is non-bypassable: `zero_tolerance` mode blocks regardless of `accepted_exceptions` list
  ```bash
  grep -n "zero_tolerance\|CVE_POLICY_MODE.*zero" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -5
  ```

- [ ] **5.4** [P] Confirm `build-validator-agent.md` HARD STOP for `TOOLCHAIN_UNAVAILABLE` is wired to the orchestrator
  (Invocation Invariant — build validator must return terminal status to orchestrator)
  ```bash
  grep -n "TOOLCHAIN_UNAVAILABLE\|HARD STOP" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -5
  ```

---

## Category 6 — Acceptance Validation

Run each quickstart scenario from [quickstart.md](./quickstart.md) and record pass/fail.

- [ ] **6.1** **CA01/CA02 — Podman path normalization**
  ```bash
  python src/shared/utils/build_runner.py --normalize-path "C:\\test" --runtime podman
  # PASS if output starts with C:/
  python src/shared/utils/build_runner.py --normalize-path "C:\\test"
  # PASS if output starts with //c/
  ```

- [ ] **6.2** **CA03/CA04 — Node image guardrail** — inspect agent body for explicit blocking guardrail
  ```bash
  grep -n "NUNCA usar.*frontend_version\|frontend_version.*NODE_IMAGE\|GUARDRAIL" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -5
  # PASS if guardrail text present
  ```

- [ ] **6.3** [P] **CA05/CA17 — CVE policy config presence**
  ```bash
  grep -c "cve_policy" projects/_template/context/project-config.yaml
  # PASS if output >= 1
  grep -c "zero_tolerance" projects/_template/context/project-config.yaml
  # PASS if output >= 1
  ```

- [ ] **6.4** [P] **CA06 — Expired exception blocking** — inspect expiry comparison logic in agent
  ```bash
  grep -n "expiry\|hoje.*expiry\|expired\|bloqueante" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -8
  # PASS if comparison logic present
  ```

- [ ] **6.5** [P] **CA07 — Valid exception allowed** — inspect `remaining_blocking` logic
  ```bash
  grep -n "remaining_blocking\|active.*exception\|CVE_ACTIVE_EXCEPTIONS" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -5
  # PASS if allowed-exception filtering present
  ```

- [ ] **6.6** [P] **CA08/CA09/CA10 — Lockfile recovery** — validator dispatches new fixer when `lockfile_updated: false`
  ```bash
  grep -n "lockfile_updated.*false\|novo ciclo\|regenerar.*lockfile" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -5
  # PASS if recovery dispatch documented
  grep -c "lockfile_updated" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md
  # PASS if count >= 1
  ```

- [ ] **6.7** [P] **CA11/CA12/CA13 — ESLint detection + skip**
  ```bash
  grep -n "eslint.config.js" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -3
  grep -n "eslintrc\.\*\|\.eslintrc" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -3
  grep -n "No ESLint config\|SKIP lint" \
    src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -3
  # PASS if all 3 patterns found
  ```

- [ ] **6.8** [P] **CA14/CA15/CA16 — Angular ESLint scaffold** — 7 deps + lint target + `.eslintrc.json` step
  ```bash
  grep -c "@angular-eslint\|@typescript-eslint\|\"eslint\"" \
    src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md
  # PASS if count >= 7
  grep -n "builder:lint\|2\.2\.1" \
    src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md | head -5
  # PASS if both patterns found
  ```

- [ ] **6.9** Run full quickstart validation script
  ```bash
  echo "=== CA02: Podman ===" && \
    python src/shared/utils/build_runner.py --normalize-path "C:\\test" --runtime podman && \
  echo "=== CA03: node warning ===" && \
    python src/shared/utils/build_runner.py --image angular 17 --node-version 22 2>&1 | head -2 && \
  echo "=== CA05: cve_policy template ===" && \
    grep -c "cve_policy" projects/_template/context/project-config.yaml && \
  echo "=== CA10: lockfile_updated fixer ===" && \
    grep -c "lockfile_updated" src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md && \
  echo "=== CA12: eslint detection ===" && \
    grep -c "eslint" src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md && \
  echo "=== CA14: angular eslint deps ===" && \
    grep -c "eslint" src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md && \
  echo "=== ALL PASS ==="
  ```

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Category 6.

- [ ] **7.1** [P] Verify `docs/agents-catalog.md` entries for `ava-stack-build-validator`, `ava-stack-build-fixer`, and `ava-stack-angular-frontend` reflect current versions and capabilities
  ```bash
  grep -n "build-validator\|build-fixer\|angular-frontend" docs/agents-catalog.md | head -10
  ```

- [ ] **7.2** [P] Verify `.github/copilot-instructions.md` SPECKIT block points to `specs/001-reliability-pipeline-evolution/plan.md`
  ```bash
  grep -A 3 "SPECKIT START" .github/copilot-instructions.md
  ```

- [ ] **7.3** Update `CHANGELOG.md` entry for `[2026-07-01]` — the heading mentions "(staged)"; confirm that label is accurate or remove it now that `cve_policy` template gap is resolved
  File: `CHANGELOG.md` — line 8 section header

- [ ] **7.4** [P] Verify `docs/full-pipeline-guide.md` references `build_runner.mode` if applicable
  ```bash
  grep -n "build_runner\|container_runtime\|podman" docs/full-pipeline-guide.md 2>/dev/null | head -5
  ```

---

## Completion Checklist

- [ ] All Category 1 verifications pass (existing agent frontmatter confirmed)
- [ ] Task 2.1 confirmed: `cve_policy` present in `projects/_template/context/project-config.yaml`
- [ ] Task 2.2 confirmed: `projects/Meu-ERP/context/project-config.yaml` has `cve_policy`
- [ ] Category 3 skipped (no schema changes)
- [ ] Category 4 skipped (no module.yaml changes)
- [ ] All 8 Category 6 acceptance scenarios pass
- [ ] `docs/agents-catalog.md` entries verified (Category 7.1)
- [ ] `CHANGELOG.md` (staged) label reviewed (Category 7.3)
- [ ] `copilot-instructions.md` SPECKIT block confirmed (Category 7.2)

---

## Dependency Graph

```
Category 1 (Verify contracts)
    │
    ├─► Category 2 (Config template)     — blocks Category 5 + 6.3 (CVE policy tests)
    │       │
    │       └─► Category 5 (Gates)       ─┐
    │       └─► Category 6 (Acceptance)  ─┤─► Category 7 (Docs) — all can run in parallel
    │                                     ┘
    └─► [Category 3 SKIP]
    └─► [Category 4 SKIP]
```

## Parallel Execution Opportunities

Tasks marked **[P]** within each category can run concurrently:
- **Category 1**: 1.3 and 1.4 parallel with 1.1 and 1.2
- **Category 2**: Tasks 2.3–2.10 can run concurrently after 2.1/2.2 confirm config presence
- **Category 6**: Tasks 6.3–6.8 all independent and parallel after 6.1/6.2
- **Category 7**: All 4 tasks fully parallel
