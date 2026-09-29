# AVA Fabric Agents — GitHub Copilot Instructions

## Project Overview

This repository contains **specialized agents** for migrating legacy applications (Delphi, COBOL, VB6, VB.NET, PowerBuilder) to modern stacks. Target stack is resolved at runtime from `tobe_stack.*` in `ConfigStack.yaml`.

Agents are organized into 7 sequential phases (F1→F7), plus a cross-cutting Summary step that runs after every phase: AS-IS diagnosis → TO-BE architecture → prototype → code generation → QA → DevOps → deliverables → (summary report after each phase).

A **Master Orchestrator** (`@ava-master-orchestrator`) runs the full pipeline end-to-end with a single command.

---

## Developing Agents (SpecKit Workflow)

This project uses **Spec-Driven Development** via [spec-kit](https://github.com/github/spec-kit) for all agent and module development.

Use these slash commands to add or modify agents with governed, traceable specs:

| Command              | Purpose                                                        |
| -------------------- | -------------------------------------------------------------- |
| `/speckit.specify`   | Define a new agent or describe a change to an existing one     |
| `/speckit.plan`      | Generate the implementation plan with constitution gate checks |
| `/speckit.tasks`     | Break the plan into the 7-category IMFAI task checklist        |
| `/speckit.implement` | Execute the tasks                                              |
| `/speckit.clarify`   | De-risk ambiguous requirements before planning                 |
| `/speckit.checklist` | Generate a quality checklist from the spec                     |
| Command              | Purpose                                                        |
| -------------------- | -------------------------------------------------------------- |
| `/speckit.specify`   | Define a new agent or describe a change to an existing one     |
| `/speckit.plan`      | Generate the implementation plan with constitution gate checks |
| `/speckit.tasks`     | Break the plan into the 7-category IMFAI task checklist        |
| `/speckit.implement` | Execute the tasks                                              |
| `/speckit.clarify`   | De-risk ambiguous requirements before planning                 |
| `/speckit.checklist` | Generate a quality checklist from the spec                     |

**When to use SpecKit:**

- Adding a new agent to any phase (F1–F8, or the cross-cutting Summary step)
- Modifying an existing agent's behavior or output contract
- Adding a new module/phase
- Any change requiring a version bump in an agent `.md` file

**Specs live in** `specs/NNN-agent-name/` and are committed alongside code.

**Governing principles** are in `.specify/memory/constitution.md` (Articles I–XI + Project Reference).  
**Phase → module mapping**, output path conventions, and `allowed-tools` guidelines are in the constitution's _Project Reference_ section.
**Phase → module mapping**, output path conventions, and `allowed-tools` guidelines are in the constitution's _Project Reference_ section.

---

## Setting Up a New Project

### Step 1 — Copy the template

```bash
cp -r projects/_template projects/{PROJECT-NAME}
```

### Step 2 — Fill in the configuration

Edit `projects/{PROJECT-NAME}/context/project-config.yaml`:

```yaml
project_name: "My-ERP" # Project name (no spaces, use kebab-case)
repository_path: "/path/to/legacy" # Absolute path to legacy repository
legacy_technology: "delphi" # delphi | cobol | vb6 | vbnet | powerbuilder
scope_modules: "all" # "all" or list: ["finance", "register"]
client_name: "Client Name"
```

### Step 3 — Start the pipeline

Use a skill to trigger the first phase:

```
@ava-asis-orchestrator
```

Or run the **complete pipeline** with a single command:

```
@ava-master-orchestrator
```

---

## Available Skills (44 agents)

### Master Orchestrator

| Skill                      | Description                                                                                                                                                                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `@ava-master-orchestrator` | **Runs the full end-to-end pipeline** — F1 AS-IS → F2 TO-BE → F3 Prototype → F4 Stack → F5 QA → F6 DevOps → F7 Deliverables. Each phase gated by `@ava-summary`. Triggers: `FP` (full pipeline), `SR` (status), `RS` (resume from phase). |

### F1 — AS-IS Diagnostic

| Skill                       | Description                                                          |
| --------------------------- | -------------------------------------------------------------------- |
| `@ava-asis-orchestrator`    | **Coordinates all F1 agents** — runs full legacy diagnosis           |
| `@ava-asis-solution-delphi` | Analyzes Delphi forms, units, and DFM structure                      |
| `@ava-asis-db-analyzer`     | Maps database tables, procedures, views, and generates ERD           |
| `@ava-asis-documentation`   | Generates functional docs: requirements, business rules, navigation  |
| `@ava-asis-inventory`       | Quantitative inventory: LOC, classes, methods, cyclomatic complexity |
| `@ava-asis-security-review` | Identifies security vulnerabilities in legacy code                   |
| `@ava-asis-gaps-risks`      | Identifies technical risks and migration gaps                        |

### F2 — TO-BE Architecture

| Skill                            | Description                                                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| @ava-tobe-orchestrator           | **Coordinates all F2 agents**                                                                                    |
| @ava-tobe-adr                    | ADR generation (Phase 0) — 8 ADRs in Michael Nygard format                                                       |
| @ava-tobe-architecture-design    | C4 architecture design: context, containers, components                                                          |
| @ava-tobe-database-design        | Database Design TO-BE: DDL, ERD Mermaid, bilingual HTML report                                                   |
| @ava-tobe-security-design        | Phase 1.6 — Security Architecture: threat model, auth, authz, LGPD/GDPR, V-01..V-13 mapping, Z-curve remediation |
| @ava-tobe-architecture-technical | Technical framework document, patterns, NuGet packages                                                           |
| @ava-tobe-measure-size           | Size estimation and complexity of the target solution                                                            |
| @ava-tobe-migration-plan         | Migration plan by waves and prioritization                                                                       |
| @ava-tobe-risk-mitigation        | Risk mitigation plan — 17 risks, owner per P0, wave per action, closure criteria, residual risk tracking         |
| @ava-coder-dotnet                | .NET 10 code generation (base structure, entities, handlers)                                                     |
| @ava-docs-tobe                   | Technical TO-BE docs: OpenAPI specs, ADRs, runbooks                                                              |
| @ava-test-plan-tobe              | Test plan for the migrated solution                                                                              |
| @ava-tobe-user-journeys          | User journeys (happy + sad path) mapped to BDD Gherkin scenarios — quantity derived from system analysis         |
| @ava-tobe-azure-infra-estimator  | Azure infra sizing with live retail prices API — SKU matrix, cost tables, TCO, provisioning plan                 |

### F3 — Prototype

| Skill                              | Description                                                                                                      |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `@ava-tobe-orchestrator`           | **Coordinates all F2 agents**                                                                                    |
| `@ava-tobe-adr`                    | ADR generation (Phase 0) — 8 ADRs in Michael Nygard format                                                       |
| `@ava-tobe-architecture-design`    | C4 architecture design: context, containers, components                                                          |
| `@ava-tobe-database-design`        | Database Design TO-BE: DDL, ERD Mermaid, bilingual HTML report                                                   |
| `@ava-tobe-security-design`        | Phase 1.6 — Security Architecture: threat model, auth, authz, LGPD/GDPR, V-01..V-13 mapping, Z-curve remediation |
| `@ava-tobe-architecture-technical` | Technical framework document, patterns, NuGet packages                                                           |
| `@ava-tobe-measure-size`           | Size estimation and complexity of the target solution                                                            |
| `@ava-tobe-migration-plan`         | Migration plan by waves and prioritization                                                                       |
| `@ava-tobe-risk-mitigation`        | Risk mitigation plan — 17 risks, owner per P0, wave per action, closure criteria, residual risk tracking         |
| `@ava-coder-dotnet`                | .NET 10 code generation (base structure, entities, handlers)                                                     |
| `@ava-docs-tobe`                   | Technical TO-BE docs: OpenAPI specs, ADRs, runbooks                                                              |
| `@ava-test-plan-tobe`              | Test plan for the migrated solution                                                                              |
| `@ava-tobe-user-journeys`          | User journeys (happy + sad path) mapped to BDD Gherkin scenarios — quantity derived from system analysis         |

### F3 — Prototype

| Skill            | Description                                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `@ava-prototype` | Generates navigable HTML prototype for client demo — dispatched directly by `@ava-master-orchestrator` right after F2/TO-BE completes |

### F4 — Tech Stack

| Skill                               | Description                                                                                                                                                                                                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `@ava-stack-orchestrator`           | **Coordinates code generation by stack** — resolves backend/frontend agents from `tobe_stack.*` in ConfigStack.yaml                                                                                                                                                |
| `@ava-stack-dotnet-backend`         | .NET backend scaffolding (Clean Architecture, CQRS, EF Core) — routed when `backend_framework == "dotnet"`                                                                                                                                                         |
| `@ava-stack-angular-frontend`       | Angular frontend scaffolding (NgRx, MSAL, lazy loading) — routed when `frontend_framework == "angular"`                                                                                                                                                            |
| `@ava-stack-java-backend`           | Java/Spring Boot backend — routed when `backend_framework == "spring-boot"`                                                                                                                                                                                        |
| `@ava-stack-python-backend`         | Python/FastAPI backend — routed when `backend_framework == "fastapi"`                                                                                                                                                                                              |
| `@ava-stack-go-backend`             | Go 1.22/Gin backend — routed when `backend_framework == "gin"`                                                                                                                                                                                                     |
| `@ava-stack-docs-researcher`        | Researches updated documentation for packages/frameworks before codegen — cross-cutting (Step 1.5)                                                                                                                                                                 |
| `@ava-stack-build-validator`        | Deterministic build validation post-codegen: compilation + lint + CVE scan — cross-cutting (Steps 6a/8a)                                                                                                                                                           |
| `@ava-stack-react-frontend`         | React 18 frontend (Vite + Zustand + MSAL React + React Router v6) — routed when `frontend_framework == "react"`                                                                                                                                                    |
| `@ava-build-cycle-java-scaffold`    | Java/Spring Boot build-cycle scaffold — routed when `pipeline_mode == "build-cycle"` AND `backend_framework == "spring-boot"` — generates Maven multi-module (parent BOM, SharedKernel, domain/application/infrastructure/api per BC, host, tests, docker-compose) |
| `@ava-build-cycle-java-persistence` | Java/Spring Boot build-cycle persistence — routed when `pipeline_mode == "build-cycle"` AND `backend_framework == "spring-boot"` — generates JPA entities, Spring Data repositories, Flyway migrations, read model via JdbcClient                                  |
| `@ava-build-cycle-python-scaffold`  | Python/FastAPI build-cycle scaffold — routed when `pipeline_mode == "build-cycle"` AND `backend_framework == "fastapi"` — generates pyproject.toml, shared/, per-BC Clean Architecture (domain/application/infrastructure/api), conftest.py, docker-compose        |

### F5 — QA Agents

| Skill                             | Description                                                                                                                                                                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `@ava-qa-orchestrator`            | **Coordinates full QA strategy**                                                                                                                                                                                                        |
| `@ava-qa-behavior-mapping`        | AS-IS behavior catalog: maps all legacy business behaviors (calculations, validations, flows, implicit rules) from Delphi source (.pas/.dfm, SPs, triggers, views) by bounded context â€” preserving critical rules for TO-BE migration |
| `@ava-qa-gaps-requirements`       | Requirements vs implementation gaps                                                                                                                                                                                                     |
| `@ava-qa-scenario-generator`      | BDD scenario generation                                                                                                                                                                                                                 |
| `@ava-qa-test-case-generator`     | Detailed test case generation                                                                                                                                                                                                           |
| `@ava-qa-script-generator`        | Test automation scripts                                                                                                                                                                                                                 |
| `@ava-qa-exploratory`             | Exploratory testing guides                                                                                                                                                                                                              |
| `@ava-qa-evidence-capture`        | Test evidence capture and organization                                                                                                                                                                                                  |
| `@ava-qa-defect-identifier`       | Defect identification and classification                                                                                                                                                                                                |
| `@ava-qa-contract-test-generator` | Consumer-driven contract tests (PactNet) — validates API contracts between frontend↔backend and inter-BC                                                                                                                                |
| `@ava-qa-frontend-test-generator` | Angular unit tests (Jest + Angular Testing Library) — components, services, NgRx stores                                                                                                                                                 |

### F6 — DevOps

| Skill                          | Description                                                                                             |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `@ava-devops-iac`              | Infrastructure as Code (Terraform/Bicep)                                                                |
| `@ava-devops-ci`               | CI pipeline (GitHub Actions / Azure DevOps)                                                             |
| `@ava-devops-cd`               | CD pipeline with deployment strategy                                                                    |
| `@ava-devops-compare-version`  | Legacy vs migrated version comparison                                                                   |
| `@ava-devops-package-approval` | Package and release approval flow                                                                       |
| `@ava-devops-containerize`     | Multi-stage Dockerfiles + docker-compose (dev/staging/prod)                                             |
| `@ava-devops-iac-azure`        | Azure IaC — Terraform + Bicep (AKS/App Service, SQL, Redis, KV, AppInsights, ACR)                       |
| `@ava-devops-iac-aws`          | AWS IaC — Terraform + CDK (ECS/EKS, RDS, Secrets Manager, ElastiCache, CloudWatch, Cognito, CloudFront) |

### F7 — Deliverables

| Skill                                  | Description                         |
| -------------------------------------- | ----------------------------------- |
| `@ava-deliverable-packager`            | **Packages all final deliverables** |
| `@ava-deliverable-tech-docs`           | Final technical documentation       |
| `@ava-deliverable-migration-plan`      | Publishable migration plan          |
| `@ava-deliverable-security-compliance` | Security and compliance report      |
| `@ava-deliverable-test-evidence`       | Test evidence package               |
| `@ava-deliverable-code-templates`      | Reusable code templates             |
| `@ava-deliverable-client-demo`         | Client presentation materials       |

### F8 — Summary

| Skill                      | Description                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `@ava-summary`             | Generates interactive HTML report consolidating all artifacts                                               |
| `@ava-summary-remediation` | Repairs display/data issues in an already-generated Summary, independently, without re-running the pipeline |

---

## How Skills Work

Each skill in `.github/skills/{agent-name}/SKILL.md` is a lightweight wrapper that:

1. Reads `projects/_template/context/project-config.yaml` to determine `project_name`
2. Reads `projects/{PROJECT_NAME}/context/agent-task-config.yaml` for project context
3. Loads and follows the agent implementation from `src/modules/ava-fabric-agents/`

The actual agent logic lives in `src/modules/ava-fabric-agents/{module}/agents/{agent}.md`.

---

## Output Structure

```
projects/{PROJECT_NAME}/
├── context/
│   ├── project-config.yaml    ← project configuration
│   └── shared-context.md      ← shared state between agents (auto-updated)
└── outputs/
    ├── asis/                  ← F1 artifacts
    ├── tobe/                  ← F2, F3 (prototype), F4 (source-code) artifacts
    ├── qa/                    ← F5 artifacts
    ├── deliverables/          ← F7 final deliverables
    └── summary/               ← F8 HTML report (cross-cutting, generated after each phase)
```

---

## Conventions

- **project_name**: kebab-case, no spaces (e.g., `My-ERP`, `Project-X`)
- **Each project is isolated**: outputs from different projects never overlap
- **shared-context.md**: auto-updated by orchestrators — do not edit manually
- **Multiple projects**: run in parallel by creating separate `projects/{NAME}/` directories
- **FastQA**: on `@fastqa:*` or `@fastqa_code:*`, first read
  `.github/instructions/00-fastqa-index.instructions.md` and follow its routing table.
  That index is scoped to `fastqa/**` on purpose — loading it globally cost **6.815 tokens
  of system prompt in every session** (measured 2026-08-04), including F1 runs that never
  touch QA. This one line replaces it at ~30 tokens.

---

## ⛔ Output Integrity Rules (MANDATORY — applies to every agent invocation)

These rules are **non-negotiable** and override any implicit tendency to generate code inline.

### Rule 1 — Never write to `outputs/` manually

Only agents may write files under `projects/{PROJECT_NAME}/outputs/`.
GitHub Copilot acting as a conversational assistant **must NOT** create or edit files
inside `outputs/` directly. Every output file must be produced by following the
corresponding agent's full Execution Steps as defined in its `.md` spec.

### Rule 2 — Read the full agent spec before generating anything

Before producing any output, every agent invocation MUST:

1. `READ` the full agent `.md` file (all sections, not just the first 100 lines)
2. `READ` every file listed in the agent's **Input Contract**
3. Display a **Pre-Flight Summary** (see Rule 3) before writing a single file

### Rule 3 — Pre-flight check is mandatory; missing prerequisites = HARD STOP

Before executing any Execution Step that writes files, the agent MUST emit:

```
╔══════════════════════════════════════════════════════════════╗
║  PRE-FLIGHT CHECK — {agent-name}                            ║
╠══════════════════════════════════════════════════════════════╣
║  Input Contract                                              ║
║  ─────────────────────────────────────────────────────────  ║
║  [✅|❌] {input_field}: {resolved_value | MISSING}          ║
║  ...                                                         ║
╠══════════════════════════════════════════════════════════════╣
║  Prerequisite Artifacts                                      ║
║  ─────────────────────────────────────────────────────────  ║
║  [✅|❌] {artifact_path}  ({producing_agent})               ║
║  ...                                                         ║
╠══════════════════════════════════════════════════════════════╣
║  DECISION: [PROCEED | BLOCKED]                               ║
╚══════════════════════════════════════════════════════════════╝
```

If **any** prerequisite is ❌ MISSING → set `DECISION: BLOCKED` and **STOP**.
Do NOT generate any output. Report which agent must run first.

### Rule 4 — Override resolution (project-config.yaml wins)

When reading `ConfigStackDotNet.yaml`, agents MUST first check
`project-config.yaml → overrides`. Any key present under `overrides`
takes precedence over the same key in `ConfigStackDotNet.yaml`.

Resolution order (highest to lowest priority):

1. `project-config.yaml → overrides`
2. `docs/architecture/ConfigStackDotNet.yaml`
3. Agent internal defaults

Example — if `project-config.yaml` has:

```yaml
overrides:
  architecture_patterns:
    cqrs: false
```

then `architecture_patterns.cqrs = false` regardless of what ConfigStackDotNet.yaml says.
The `ava-build-cycle-cqrs` agent becomes a **no-op** and must be skipped.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/043-summary-self-correction/plan.md
<!-- SPECKIT END -->
