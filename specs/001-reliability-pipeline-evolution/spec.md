# Agent Specification: Reliability Pipeline Evolution

**Feature Branch**: `001-reliability-pipeline-evolution`
**Created**: 2026-07-02
**Status**: Draft
**Change Type**: modify-existing
**Input**: Agent description: "PBI – Evolução do Pipeline de Confiabilidade (Reliability Pipeline)"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

This PBI modifies **four existing components** (no new agents created):

| Component | Type | File | Version Bump |
|---|---|---|---|
| `build_runner.py` | Utility script | `src/shared/utils/build_runner.py` | N/A (not versioned) |
| `ava-stack-build-validator` | Existing agent | `src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md` | MINOR (new config fields + steps) |
| `ava-stack-build-fixer` | Existing agent | `src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md` | MINOR (new output field) |
| `ava-stack-angular-frontend` | Existing agent | `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` | MINOR (new scaffolding steps) |
| `project-config.yaml` template | Config template | `projects/_template/context/project-config.yaml` | N/A (config file) |

> Because all components are **modify-existing**, module.yaml entries already exist.
> Category 4 tasks (module registration) and SKILL.md creation are N/A.
> Version bumps are MINOR across agents — new optional fields and steps added without
> breaking the existing Input/Output contract.

---

## 2. Agent Frontmatter Changes

### `ava-stack-build-validator` — version bump only

```yaml
---
name: "ava-stack-build-validator"
version: "1.1.0"   # was 1.0.0 — MINOR bump: CVE policy, lockfile recovery, ESLint detection, node_version guardrail
description: |
  Valida o build gerado de forma determinística: Toolchain Pre-Gate, Restore, Build por Camada, Lint,
  CVE Scan com política configurável, HintPath Check e recuperação de lockfile.
  Ativa com: "validar build", "build validator", "compilar e validar".
allowed-tools: Read, Write, Edit, Bash, Grep
---
```

### `ava-stack-build-fixer` — version bump only

```yaml
---
name: "ava-stack-build-fixer"
version: "1.1.0"   # was 1.0.0 — MINOR bump: lockfile_updated field in output contract
description: |
  Sub-agente de correção invocado pelo build-validator. Classifica e corrige erros de build por categoria.
  Retorna fix_result com campo lockfile_updated obrigatório quando package.json foi modificado.
  Ativa com: invocado exclusivamente pelo ava-stack-build-validator.
allowed-tools: Read, Write, Edit, Bash, Grep
---
```

### `ava-stack-angular-frontend` — version bump only

```yaml
---
name: "ava-stack-angular-frontend"
version: "1.1.0"   # was 1.0.0 — MINOR bump: ESLint scaffolding (dependencies, angular.json target, .eslintrc.json)
description: |
  Gera projeto Angular production-ready: standalone components, NgRx, MSAL, Playwright e ESLint scaffolding obrigatório.
  Ativa com: "gerar frontend angular", "scaffold angular", "angular frontend".
allowed-tools: Read, Write, Edit, Bash
---
```

---

## 3. Output Contract

All changes are **additive** — no existing output paths change.

### `ava-stack-build-fixer` — new output field

```yaml
## Output Contract (additions)
outputs:
  fix_result: |
    {
      "lockfile_updated": boolean,   # NEW — true if npm install was run after package.json change
      ...existing fields...
    }
```

### `ava-stack-angular-frontend` — new output artifacts

```yaml
## Output Contract (additions)
outputs:
  eslintrc_json:        "projects/{project_name}/outputs/tobe/source-code/frontend/.eslintrc.json"
  # angular.json and package.json already exist — they receive new fields (target lint + devDependencies)
```

### `build_runner.py` — no output contract change (utility script)

### `project-config.yaml` template — new config fields

```yaml
tobe_stack:
  node_version: "20"   # NEW — explicit Node.js version, independent from frontend_version

quality_gates:
  cve_policy:
    mode: "zero_tolerance"   # NEW — zero_tolerance | exceptions_allowed
    accepted_exceptions:     # NEW — list of accepted CVE exceptions (used when mode=exceptions_allowed)
      - cve_id: "CVE-YYYY-NNNNN"
        package: "package-name"
        reason: "reason for exception"
        expiry: "YYYY-MM-DD"   # ISO date — expired entries are treated as blocking
```

---

## 4. Functional Changes by Component

### 4.1 `build_runner.py` — Podman Support & Node Version Override

**Changes**:
- Add `--runtime podman` flag to support Podman container engine.
- Update `--normalize-path` to emit runtime-aware paths:
  - Docker Desktop → MSYS2 format (`//c/...`)
  - Podman → native Windows format (`C:/...`)
- Add `--node-version` parameter to `resolve_image()` so frontend frameworks pass `tobe_stack.node_version` explicitly.
- Emit warning when `--node-version` value differs from the value implied by `frontend_version`.

### 4.2 `ava-stack-build-validator` — Four New Behaviors

#### Step F0.5 (existing) — node_version Guardrail
- **Guardrail**: forbid using `frontend_version` to resolve the Node image.
- Node image MUST be `node:{tobe_stack.node_version}-alpine` (read from `project-config.yaml`).

#### Step F3.5 — CVE Policy Resolution (new step)
- Read `quality_gates.cve_policy` from `project-config.yaml`.
- Support two modes:
  - `zero_tolerance` (default): any CVE finding is blocking.
  - `exceptions_allowed`: CVEs listed under `accepted_exceptions` with a future `expiry` date are allowed.
- Expired exceptions (past `expiry` ISO date) are treated as blocking regardless of mode.

#### Step F3 — Lockfile Recovery
- When `npm ci` fails with "package.json and package-lock.json are out of sync":
  - Check `fix_result.lockfile_updated` from the build-fixer.
  - If `false` → dispatch a new fixer cycle explicitly requesting lockfile regeneration (`npm install`).

#### Step F3 — ESLint Detection
- Detect flat config: `eslint.config.js`
- Detect legacy config: `.eslintrc.*`
- If neither exists → SKIP lint step + emit `WARN "No ESLint config found"` (non-blocking).

### 4.3 `ava-stack-build-fixer` — Lockfile Protocol

- Any fix cycle that modifies `package.json` (install/remove/update) MUST run `npm install` in the container before returning `fix_result`.
- New required output field: `lockfile_updated: boolean`
  - `true` if `npm install` was executed to regenerate `package-lock.json`.
  - `false` if `package.json` was not modified.
- **Guardrail**: PROHIBITED to return without regenerating lockfile if `package.json` was modified.

### 4.4 `ava-stack-angular-frontend` — ESLint Scaffolding

#### Step 2.x — ESLint Dependencies in `package.json`

Add to `devDependencies`:

```json
{
  "@angular-eslint/builder": "^{frontend_version}.0.0",
  "@angular-eslint/eslint-plugin": "^{frontend_version}.0.0",
  "@angular-eslint/eslint-plugin-template": "^{frontend_version}.0.0",
  "@angular-eslint/schematics": "^{frontend_version}.0.0",
  "@typescript-eslint/eslint-plugin": "^7.2.0",
  "@typescript-eslint/parser": "^7.2.0",
  "eslint": "^8.57.0"
}
```

#### Step 2.x — Lint Target in `angular.json`

Add `lint` target under the project architect section:

```json
"lint": {
  "builder": "@angular-eslint/builder:lint",
  "options": {
    "lintFilePatterns": ["src/**/*.ts", "src/**/*.html"]
  }
}
```

#### Step 2.2.1 — Generate `.eslintrc.json` (new mandatory step)

```json
{
  "root": true,
  "ignorePatterns": ["projects/**/*"],
  "overrides": [
    {
      "files": ["*.ts"],
      "extends": [
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended",
        "plugin:@angular-eslint/recommended",
        "plugin:@angular-eslint/template/process-inline-templates"
      ],
      "rules": {}
    },
    {
      "files": ["*.html"],
      "extends": ["plugin:@angular-eslint/template/recommended"],
      "rules": {}
    }
  ]
}
```

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Podman Runtime Path Normalization (CA01, CA02)

**Story**: Como desenvolvedor em ambiente Windows com Podman, quero que o build_runner.py gere paths corretos para o runtime, para que o build execute sem erros de path inválido.

**Acceptance Scenarios**:

1. **Given** `build_runner.py` is invoked with `--runtime podman --normalize-path` on Windows/MSYS2, **When** it resolves a volume path, **Then** the output format is `C:/path/to/dir` (native Windows) — not `//c/path/to/dir`.
2. **Given** `--runtime docker` (default), **When** `--normalize-path` is invoked, **Then** the output format remains `//c/path/to/dir` (MSYS2).
3. **Given** `--node-version 20` passed alongside `--image angular 17`, **When** a discrepancy is detected, **Then** a WARNING is emitted and execution continues.

### Scenario 2 — Node Version Guardrail in Build Validator (CA03, CA04)

**Story**: Como responsável pela esteira, quero que o validator use exclusivamente `tobe_stack.node_version` para a imagem Node, para evitar builds com versão errada de Node.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `tobe_stack.node_version: "20"` and `tobe_stack.frontend_version: "17"`, **When** the build-validator resolves the Node image, **Then** it uses `node:20-alpine`, never `node:17-alpine`.
2. **Given** the agent attempts to derive `NODE_IMAGE` from `frontend_version`, **When** the guardrail check runs, **Then** the step is BLOCKED with a descriptive error.

### Scenario 3 — CVE Policy: Expired Exception Blocks Build (CA05, CA06)

**Story**: Como responsável por segurança, quero que exceções de CVE expiradas bloqueiem o build, para garantir que vulnerabilidades não fiquem indefinidamente aceitas.

**Acceptance Scenarios**:

1. **Given** `cve_policy.mode: "exceptions_allowed"` and an exception with `expiry: "2026-01-01"` for `CVE-2024-9999`, **When** the CVE scan finds `CVE-2024-9999` on 2026-07-02, **Then** the build FAILS with a `CVE_POLICY_EXPIRED` error.
2. **Given** the same CVE but `expiry: "2026-12-31"`, **When** the scan runs on 2026-07-02, **Then** the build continues (exception is valid).
3. **Given** `cve_policy.mode: "zero_tolerance"` (default), **When** any CVE is found regardless of exceptions list, **Then** the build FAILS.

### Scenario 4 — Lockfile Recovery (CA08, CA09, CA10)

**Story**: Como responsável pelo build, quero que inconsistências entre package.json e package-lock.json sejam recuperadas automaticamente, para evitar falhas silenciosas.

**Acceptance Scenarios**:

1. **Given** `npm ci` fails with "out of sync" error, **When** `fix_result.lockfile_updated` is `false`, **Then** the validator dispatches a new fixer cycle requesting `npm install`.
2. **Given** the fixer modifies `package.json`, **When** it completes, **Then** `fix_result.lockfile_updated: true` and `package-lock.json` exists and is valid.
3. **Given** the fixer does NOT modify `package.json`, **When** it completes, **Then** `fix_result.lockfile_updated: false`.

### Scenario 5 — ESLint Detection and Skip (CA11, CA12, CA13)

**Story**: Como desenvolvedor, quero que a ausência de configuração ESLint não quebre o build, mas emita aviso para que eu possa decidir se adiciono a configuração depois.

**Acceptance Scenarios**:

1. **Given** a frontend project with `eslint.config.js`, **When** Step F3 lint detection runs, **Then** flat config is recognized and lint runs.
2. **Given** a project with `.eslintrc.json`, **When** Step F3 lint detection runs, **Then** legacy config is recognized and lint runs.
3. **Given** no ESLint config file exists, **When** Step F3 runs, **Then** lint is SKIPPED, `WARN "No ESLint config found"` is emitted, and the overall build is NOT failed.

### Scenario 6 — Angular ESLint Scaffolding (CA14, CA15, CA16)

**Story**: Como gerador do projeto Angular, quero que o ESLint seja scaffolded automaticamente, para que o build-validator encontre a configuração e execute o lint corretamente.

**Acceptance Scenarios**:

1. **Given** `ava-stack-angular-frontend` generates a new project, **When** Step 2.x runs, **Then** `package.json` contains all 7 ESLint-related devDependencies.
2. **Given** the above, **When** `angular.json` is written, **Then** it contains a `lint` target using `@angular-eslint/builder:lint` with patterns `src/**/*.ts` and `src/**/*.html`.
3. **Given** the above, **When** Step 2.2.1 runs, **Then** `.eslintrc.json` is created with extends for TS and HTML rules.
4. **Given** the generated project is passed to `ava-stack-build-validator`, **When** Step F3 ESLint detection runs, **Then** `.eslintrc.json` is found and lint executes without SKIP.

---

## 6. Quality Gate Requirements

- [x] All components are **modify-existing** — no new module.yaml registrations needed (Article IV)
- [x] No technology versions hardcoded — ESLint versions use `^{frontend_version}.0.0` pattern; node_version from config (Article I)
- [x] All version bumps are MINOR — output contracts are additive, not breaking (Article X)
- [x] No SKILL.md changes — routing is unchanged for all three agents (Article XI)
- [x] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [x] Security sub-pipeline not impacted — changes are in build validation layer, not F1 security flow (Article VII)
- [x] `build_runner.py` has no frontmatter (utility script, not an agent) — no Article II violation
- [x] All output paths use lowercase `{project_name}` where applicable (Article II)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Component | Reason |
|---|---|---|
| `project-config.yaml` schema | Config template | `tobe_stack.node_version` and `cve_policy` fields must exist before agents read them |
| `ava-stack-build-validator` | Build validator | Must be updated before `ava-stack-build-fixer` lockfile contract change has any effect |
| `ava-stack-angular-frontend` | Angular coder | Must generate `.eslintrc.json` before build-validator Step F3 can detect it |

---

## 8. Exclusions

- **New agent creation** — all changes are modifications to existing components.
- **Java / Python / Go stacks** — lockfile and ESLint changes are Angular/npm-only; these stacks are unaffected.
- **F1 AS-IS agents** — no changes to the diagnostic pipeline.
- **Summary HTML template** — no changes to `summary-template.html` or `build_summary_comprehensive.py`.
- **CI/CD pipeline definitions** — `ava-devops-ci` pipeline YAML changes are out of scope for this PBI.

---

## 9. Assumptions

- `build_runner.py` is a utility script (not an agent) — it has no frontmatter, module.yaml entry, or SKILL.md.
- The `project-config.yaml` template at `projects/_template/context/project-config.yaml` is the canonical source — all new Meu-ERP or Test-PBI366 projects copy from this template.
- ESLint version constraints (`^7.2.0` for typescript-eslint, `^8.57.0` for eslint) are fixed at these values because Angular 17 is not compatible with ESLint v9 flat config.
- The `frontend_version` field in `project-config.yaml` stores the Angular major version (e.g., `17`), not the Node.js version.
- CVE expiry dates are evaluated against the wall clock at the time the build-validator runs (using `ntp_time.py` for NTP-accurate timestamps).
- Podman path normalization applies only to Windows environments; Linux/macOS paths are unaffected.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Podman runtime supported | `build_runner.py --runtime podman` executes without errors on Windows/MSYS2 |
| Node image guardrail enforced | Build-validator blocks if `frontend_version` is used instead of `node_version` for the Node image |
| CVE expired exception blocks | Build fails when an exception's `expiry` is in the past |
| Lockfile auto-recovery | Build-validator dispatches new fixer cycle when `lockfile_updated: false` after `npm ci` sync error |
| ESLint absent = WARN not fail | Build completes with warning when no ESLint config is found |
| Angular ESLint scaffold complete | Generated project passes Step F3 lint detection without SKIP |
| Version bumps documented | All three agent `.md` files updated to MINOR version |
| `project-config.yaml` template updated | Template contains `node_version` and `cve_policy` fields |
