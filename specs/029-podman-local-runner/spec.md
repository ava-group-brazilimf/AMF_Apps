# Agent Specification: Podman Local Runner (Windows)

**Feature Branch**: `029-podman-local-runner`
**Created**: 2026-07-25
**Status**: Draft
**Change Type**: new-agent
**Input**: Agent description: "Criar um agente que executa todos os passos do guia `docs/podman-windows-guide.md`: verifica dependências (WSL2, Podman, virtualização), instrui o usuário sobre como resolver o que estiver faltando, coleta interativamente os parâmetros necessários (nome do projeto, diretório de código-fonte), auto-descobre toda informação dinâmica e sobe os contêineres da solução gerada."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-devops-podman-run` |
| **Version** | `1.0.0` |
| **Phase** | `F6` |
| **Module** | `devops-agents` |
| **Role** | Executes the full Podman-on-Windows workflow — dependency pre-flight, machine provisioning, `.env` resolution and `podman compose up` — for the containerized solution produced by `ava-devops-containerize`. |
| **Skill** | `ava-devops-podman-run` |
| **Dispatch** | user-facing via SKILL.md (also invocable by `ava-devops-orchestrator`) |

**Source of truth**: `docs/podman-windows-guide.md`. Every command, remediation and
troubleshooting rule the agent executes must trace back to a section of that guide.

---

## 2. Agent Frontmatter

```yaml
---
name: "ava-devops-podman-run"
version: "1.0.0"
description: |
  Executa a solução containerizada no Podman/Windows — verifica dependências (WSL2,
  Podman, virtualização, recursos), provisiona a Podman Machine, resolve o .env e
  sobe os contêineres com podman compose.
  Ativa com: "rodar no podman", "subir os containers", "executar a aplicação localmente",
  "podman run", "iniciar solução no windows", "verificar dependências do podman".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---
```

No `phase`, `module`, `inputs`, `outputs` or `dependencies` keys in frontmatter.

---

## 3. Output Contract

```yaml
outputs:
  podman_run_report:      "projects/{project_name}/outputs/tobe/iac/containers/podman-run-report.md"
  podman_preflight_report:"projects/{project_name}/outputs/tobe/iac/containers/podman-preflight.md"
  runtime_env_file:       "projects/{project_name}/outputs/tobe/source-code/.env"
```

Notes:
- `.env` is written **into the generated solution**, next to the compose files, because
  `podman compose` resolves `${VAR}` from the working directory. It is never committed
  (already covered by `.dockerignore` / `.gitignore` produced by `ava-devops-containerize`).
- Reports live under `outputs/tobe/iac/containers/`, the same folder
  `ava-devops-containerize` uses for `containerization-report.md`, so the DevOps
  container artifacts stay co-located.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 - Nominal Path (Priority: P1)

**Story**: Como desenvolvedor que acabou de rodar a esteira AVA, quero um único agente que
verifique meu ambiente Windows, configure o Podman e suba a solução gerada, para que eu
consiga validar a aplicação localmente sem seguir manualmente o guia de 580 linhas.

**Why this priority**: This is the agent's reason to exist — one command from "generated
code" to "running application".

**Acceptance Scenarios**:

1. **Given** a Windows host with WSL2 and Podman installed and a project whose
   `outputs/tobe/source-code/docker-compose.yml` exists, **When** the agent executes with
   trigger `PR`, **Then** the Podman machine is running, `.env` is present with every
   variable referenced by the compose file resolved, all services report `healthy` or
   `running` in `podman ps`, and `podman-run-report.md` is written.
2. **Given** the above, **When** execution completes, **Then** the agent prints the reachable
   URLs (frontend / backend / health) read from the compose `ports:` mappings — never
   hardcoded — and `AgentResult.success` is true.

---

### Scenario 2 - Edge Case: Missing Dependency (Priority: P1)

**Why this priority**: The user explicitly asked that missing tools produce actionable
instructions instead of a failed run.

**Acceptance Scenarios**:

1. **Given** a host where `podman --version` fails, **When** the agent executes the
   pre-flight, **Then** it does NOT attempt `podman machine init`, writes
   `podman-preflight.md` with the `❌` row for Podman, prints the exact remediation
   (`winget install RedHat.Podman`) plus the "re-run after fixing" instruction, and stops.
2. **Given** a host where `wsl --list --verbose` shows a distro at version 1 (or no distro),
   **When** the pre-flight runs, **Then** the agent reports WSL2 as blocking, prints
   `wsl --install` + "reboot required", and stops before touching Podman.
3. **Given** a host where virtualization is disabled in BIOS/UEFI, **When** the pre-flight
   runs, **Then** the agent reports it as blocking and instructs enabling
   Intel VT-x / AMD-V, because no remediation is possible from the shell.

---

### Scenario 3 - Edge Case: Missing / Ambiguous Parameters (Priority: P1)

**Why this priority**: Requirement "all dynamic information must be discovered by the agent;
only ask the user when discovery fails".

**Acceptance Scenarios**:

1. **Given** exactly one `projects/*/context/project-config.yaml` with a non-empty
   `project_name`, **When** the agent starts, **Then** it uses that value WITHOUT asking.
2. **Given** several projects, **When** the agent starts, **Then** it lists the discovered
   names and asks the user to pick one.
3. **Given** no `docker-compose*.yml` under the resolved `source-code/` path, **When** the
   agent starts, **Then** it globs the repository for compose files, and only if that also
   fails does it ask the user for the source-code directory — never guessing a path.
4. **Given** compose files that reference `${SQL_SA_PASSWORD}` and no `.env`, **When** the
   agent runs, **Then** it parses every `${VAR}` from the compose files, seeds known values
   from `.env.example`, and asks the user only for the still-unresolved variables.

---

### Scenario 4 - Quality Gate: Unhealthy Stack (Priority: P1)

**Why this priority**: Safety gate — a container that starts but never becomes healthy must
not be reported as a success.

**Acceptance Scenarios**:

1. **Given** the SQL Server container never reaches `healthy` within the wait budget,
   **When** the agent polls the stack, **Then** `AgentResult.risk.level` is `high`,
   `human_gate_required` is true, the report contains the last 100 log lines of the failing
   service and the matching remediation from the guide's troubleshooting section.
2. **Given** any service exits with a non-zero code, **When** the agent polls,
   **Then** it classifies the symptom (port in use / OOM / no space / ICU / nginx port 80)
   against the guide's troubleshooting table and prints that specific fix.

---

## 5. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] Agent registered in module-level `module.yaml` — diff in plan (Article IV)
- [x] Output paths use lowercase `{project_name}` and the F6 container folder (Article II)
- [x] BDD scenarios cover nominal, edge and gate paths (Article VI)
- [x] Security impact assessed: agent handles secrets (`.env`) — never echoes them, never
      commits them, never writes them to the report (Article VII)
- [x] No technology versions hardcoded — Podman/WSL/.NET/Node versions are read from the
      host and from the generated compose files (Article I)
- [x] Skill/Agent split declared: user-facing `SKILL.md` (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Containerization | `ava-devops-containerize` | Produces the Dockerfiles, `docker-compose*.yml` and `.env.example` this agent consumes |
| DevOps orchestrator | `ava-devops-orchestrator` | May dispatch this agent as the local-validation step of F6 |
| Reference guide | `docs/podman-windows-guide.md` | Canonical source for commands, remediations and troubleshooting |

---

## 7. Exclusions

- Building or fixing the Dockerfiles / compose files — owned by `ava-devops-containerize`
- Provisioning cloud infrastructure — owned by `ava-devops-iac-azure`
- Pushing images to ACR or deploying — owned by `ava-devops-cd`
- Installing WSL2 or Podman silently — the agent **instructs**, it never runs installers or
  elevated/administrator commands on the user's machine without explicit confirmation
- Linux/macOS hosts — out of scope for v1.0.0 (guide is Windows-specific)

---

## 8. Assumptions

- The host is Windows 10 (2004+) or Windows 11, 64-bit.
- `ava-devops-containerize` has already run, or the user points the agent at a directory
  that contains at least one `docker-compose*.yml`.
- `project-config.yaml` exists at `projects/{project_name}/context/` for at least one project;
  if not, the agent asks for the project name.
- The user has administrator rights available for the remediation steps the agent prints
  (the agent itself does not require them).

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Dependency coverage | Every prerequisite row of the guide's "Pré-requisitos" table is checked and reported |
| Zero silent guesses | Every parameter is either discovered from a file/host command or explicitly asked |
| Artifacts produced | Both reports exist after execution; `.env` exists before any `compose up` |
| Gate accuracy | `human_gate_required` is true whenever any service fails to reach healthy |
| Secret hygiene | No secret value appears in the reports, logs or chat output |
| Idempotence | Re-running the agent on an already-running stack reports state and does not duplicate containers |
