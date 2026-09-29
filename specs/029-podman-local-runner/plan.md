# Implementation Plan: Podman Local Runner (Windows)

**Branch**: `029-podman-local-runner` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/029-podman-local-runner/spec.md`

## Summary

Add a single user-facing F6 agent, `ava-devops-podman-run`, that turns
`docs/podman-windows-guide.md` from a manual 580-line runbook into an executable,
interactive workflow. The agent performs a blocking dependency pre-flight (Windows build,
virtualization, WSL2, winget, Podman, Podman Machine, RAM, disk), prints copy-pasteable
remediation for anything missing, auto-discovers every runtime parameter from the repository
and the host, asks the user only for what could not be discovered, materializes `.env`,
runs `podman compose up`, waits for health, classifies failures against the guide's
troubleshooting table, and writes two reports.

## Technical Context

**Language/Version**: LLM prompt agent (Markdown), body in PT-BR — no compiled code
**Primary Dependencies**: `podman`, `podman compose`, `wsl`, `winget` (host tools);
`ava-devops-containerize` artifacts (compose files, `.env.example`)
**Storage**: Filesystem only — reports under `projects/{project_name}/outputs/tobe/iac/containers/`, `.env` under `outputs/tobe/source-code/`
**Testing**: Manual acceptance run per spec section 4; `projects/test-determinism/` for the
parameter-discovery path
**Target Platform**: Windows 10 (2004+) / Windows 11 with WSL2
**Project Type**: Agent prompt file + SKILL.md
**Constraints**: Never runs elevated installers unattended; never echoes secret values;
no hardcoded versions or ports — all read from the host and from the generated compose files
**Scale/Scope**: One agent file, one SKILL.md, one module.yaml entry, catalog + CHANGELOG

## Constitution Check

| Article | Rule | Status |
|---|---|---|
| I | No hardcoded technology versions | ✅ Podman/WSL/.NET/Node versions and all ports are read at runtime from `podman --version`, `wsl -l -v` and the compose `ports:`/`image:` fields |
| II | Frontmatter only `name`, `version`, `description` (PT), `allowed-tools` | ✅ |
| III | Pipeline sequence F1→…→F7 with `ava-summary` between phases | ✅ N/A — additive F6 agent; runs after `ava-devops-containerize`, does not alter phase order |
| IV | Registration in the **module-level** `module.yaml` | ✅ `src/modules/ava-fabric-agents/devops-agents/module.yaml`, MINOR bump `1.0.1 → 1.1.0` |
| V | Agent body in Brazilian Portuguese | ✅ |
| VI | Mandatory BDD scenarios: nominal, edge, quality gate | ✅ spec section 4 — 4 scenarios |
| VII | F1 always includes the security sub-pipeline | ✅ N/A for F6; secret-handling invariants declared instead (no echo, no commit, no report) |
| VIII | `trace_id` propagated unmodified | ✅ read from `project-config.yaml`, echoed in both reports |
| IX | Clean Architecture | ✅ N/A — LLM prompt agent |
| X | SemVer | ✅ new agent `1.0.0`; module MINOR bump |
| XI | SKILL.md / agent `.md` separation | ✅ user-facing skill `ava-devops-podman-run` delegating to the agent file |

**Result**: PASS — no violations, Complexity Tracking not required.

## 2. Phase Placement

```
F6 DevOps:
  ava-devops-ci
    → ava-devops-containerize        (produces Dockerfiles + docker-compose*.yml + .env.example)
      → ava-devops-podman-run        ← NEW — local execution / validation gate (optional, non-blocking)
        → ava-devops-iac-azure       (cloud provisioning)
```

`ava-devops-podman-run` is **optional and non-blocking** inside the automated `FP` pipeline:
it is a developer-facing local validation step. It is always available standalone via its
skill. Placing it after `ava-devops-containerize` guarantees its inputs exist.

## 3. Discovery Strategy (the "no silent guesses" rule)

Every parameter follows the same three-tier resolution, in order:

| # | Parameter | Tier 1 — discover | Tier 2 — fallback | Tier 3 — ask user |
|---|---|---|---|---|
| 1 | `project_name` | Glob `projects/*/context/project-config.yaml` → `project_name` | If exactly 1 match, use it | List candidates / ask if 0 or >1 |
| 2 | `source_code_path` | `projects/{project_name}/outputs/tobe/source-code/` | Glob repo for `**/docker-compose.yml` | Ask for the directory |
| 3 | `compose_files` | Glob `{source_code_path}/docker-compose*.yml` | — | Abort with "run trigger CT first" |
| 4 | `environment` | Which compose files exist | Default `docker-compose.yml` | Ask if several and intent unclear |
| 5 | `required_env_vars` | Regex `\$\{([A-Z0-9_]+)` over the selected compose file | Seed from `.env.example` and existing `.env` | Ask only for still-unresolved vars |
| 6 | `service_ports` | Parse `ports:` of the selected compose file | — | Never asked — reported as discovered |
| 7 | `machine_resources` | `podman machine ls` (existing machine) | Host RAM/CPU/disk via PowerShell | Ask (with host-derived defaults) only when creating a machine |
| 8 | `trace_id` | `project-config.yaml` → `trace_id` | Empty | Never asked |

## 4. Pre-flight Matrix

| Check | Command | Blocking | Remediation printed |
|---|---|---|---|
| Windows version | `[Environment]::OSVersion.Version` | yes | "Requer Windows 10 2004+ / Windows 11" |
| Virtualization | `(Get-CimInstance Win32_ComputerSystem).HypervisorPresent` | yes | Enable Intel VT-x / AMD-V in BIOS/UEFI |
| WSL present | `wsl --status` | yes | `wsl --install` (admin) + reboot |
| WSL version 2 | `wsl --list --verbose` | yes | `wsl --set-default-version 2` / `wsl --set-version <distro> 2` |
| winget | `winget --version` | no | Install "App Installer" from Microsoft Store |
| Podman CLI | `podman --version` | yes | `winget install RedHat.Podman` |
| `podman compose` | `podman compose version` | yes | `winget upgrade RedHat.Podman`, fallback `podman-compose` |
| Podman machine | `podman machine ls` | no | Agent provisions it in Step 2 |
| RAM ≥ 8 GB | `Get-CimInstance Win32_ComputerSystem` | no (warn) | Guide's `.wslconfig` memory tuning |
| Free disk ≥ 20 GB | `Get-PSDrive C` | no (warn) | `podman machine set --disk-size` |

Blocking failure ⇒ write `podman-preflight.md`, print the remediation list, **stop**.

## 5. module.yaml Impact

```diff
  name: devops-agents
  display_name: "DevOps Agents"
- version: "1.0.1"
+ version: "1.1.0"

  agents:
    - id: ava-devops-containerize
      file: agents/containerize-agent.md
      skill: ava-devops-containerize
+   - id: ava-devops-podman-run
+     file: agents/podman-run-agent.md
+     skill: ava-devops-podman-run
+     depends_on: ava-devops-containerize
```

## 6. Project Structure

```text
specs/029-podman-local-runner/
├── spec.md
├── plan.md                 # this file
├── tasks.md
└── checklists/
    └── requirements.md

src/modules/ava-fabric-agents/devops-agents/
├── agents/podman-run-agent.md          # NEW
└── module.yaml                         # MODIFIED

.github/skills/ava-devops-podman-run/
└── SKILL.md                            # NEW

docs/
├── podman-windows-guide.md             # source of truth (unchanged)
└── agents-catalog.md                   # MODIFIED
CHANGELOG.md                            # MODIFIED
```

**Structure Decision**: Standard IMFAI agent layout — the agent prompt lives in its phase
module, the user entry point is a skill under `.github/skills/`.

## 7. Shared Schema Impact

None. The agent consumes `project-config.yaml` fields that already exist
(`project_name`, `trace_id`) and produces Markdown reports. Category 3 is skipped.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Agent runs a long-blocking `podman compose up` in the foreground | Always use `-d` (detached) then poll `podman ps` with a bounded wait budget |
| Secret leakage into the report | Report lists variable **names** and a `set/unset` status only — never values |
| Destructive remediation (`machine rm`, `down -v`) executed silently | Both are gated behind explicit user confirmation in the agent body |
| Guide drift | Agent body cites the guide section for each command so both stay reviewable together |

## Complexity Tracking

Not applicable — Constitution Check passed with no violations.
