# Agent Development Tasks: Podman Local Runner (Windows)

**Plan**: `specs/029-podman-local-runner/plan.md`
**Agent ID**: `ava-devops-podman-run` | **Phase**: `F6` | **Module**: `devops-agents`

> Complete categories sequentially. `[P]` marks tasks parallelizable within a category.

---

## Category 1 -- Agent Frontmatter & Contract Definition

- [x] **1.1** Create `src/modules/ava-fabric-agents/devops-agents/agents/podman-run-agent.md`
- [x] **1.2** Write YAML frontmatter (Article II):
  - `name: "ava-devops-podman-run"`
  - `version: "1.0.0"`
  - `description: |` in PT-BR ending with `Ativa com: "..."` phrases
  - `allowed-tools: Read, Write, Edit, Glob, Grep, Bash`
  - No `phase` / `module` / `inputs` / `outputs` / `dependencies` keys
- [x] **1.3** Write `## Contrato de Saída` block with lowercase `{project_name}` paths
- [x] **1.4** Verify F6 folder: `outputs/tobe/iac/containers/` (same folder as `containerization-report.md`); `.env` goes to `outputs/tobe/source-code/`
- [x] **1.5** Dispatch = user-facing → create `.github/skills/ava-devops-podman-run/SKILL.md`
      resolving `project_name`, reading `shared-context.md`, delegating to the agent file

---

## Category 2 -- Agent Behavior & Instructions

- [x] **2.1** Write `## Papel & Persona` — Platform Engineer for local Windows execution
- [x] **2.2** Write `## Contrato de Entrada` — every field with type, discovery source and default
- [x] **2.3** Write the deterministic numbered steps:
  - **Passo 0** — parameter resolution using the 3-tier rule (discover → fallback → ask)
  - **Passo 1** — dependency pre-flight matrix (blocking vs. warning) + remediation output
  - **Passo 2** — Podman Machine provisioning (`init` / `start`, resource sizing, `DOCKER_HOST`)
  - **Passo 3** — `.env` resolution from compose `${VAR}` references + `.env.example`
  - **Passo 4** — environment selection menu (dev / full / staging / prod-validate)
  - **Passo 5** — `podman compose up -d --build` + bounded health polling
  - **Passo 6** — smoke validation and URL discovery from compose `ports:`
  - **Passo 7** — failure classification against the guide's troubleshooting table
  - **Passo 8** — write both reports
  - **Passo 9** — observability tracking via `pipeline_observer.py`
- [x] **2.4** Write the output format for `podman-preflight.md` and `podman-run-report.md`
- [x] **2.5** Add `## Notas de Segurança` — no secret echo, no `.env` commit, no unattended
      elevated commands, explicit confirmation for `down -v` / `machine rm`
- [x] **2.6** Write `## Lógica de Gate de Qualidade` — risk scoring and `human_gate_required`

---

## Category 3 -- Shared Schema Updates

**SKIPPED** — plan section 7 records no schema changes.

---

## Category 4 -- Module Registration

- [x] **4.1** Add entry to `src/modules/ava-fabric-agents/devops-agents/module.yaml`:
      `{ id: ava-devops-podman-run, file: agents/podman-run-agent.md, skill: ava-devops-podman-run, depends_on: ava-devops-containerize }`
- [x] **4.2** Bump module `version` `1.0.1 → 1.1.0` (new user-facing agent = MINOR)
- [x] **4.3** Top-level `module.yaml` untouched — no new phase/module created

---

## Category 5 -- Quality Gate Checklists

- [x] **5.1** Gate is inline in the agent body (`## Lógica de Gate de Qualidade`) — F6 has no
      shared checklist file equivalent to F1/F2 `readiness-gate-checklist.md`
- [x] **5.2** Items covered: pre-flight blocking failures, unhealthy services, unresolved
      env vars, missing compose files
- [x] **5.3** Checklist rendered in `podman-run-report.md` using `- [ ]` / `- [x]` format

---

## Category 6 -- Acceptance Validation & QA Integration

- [ ] **6.1** Confirm spec section 4 scenarios are complete and unambiguous (4 scenarios:
      nominal, missing dependency, missing parameters, unhealthy stack)
- [ ] **6.2** [P] Run the agent against a project that has `outputs/tobe/source-code/docker-compose.yml`
      and verify both reports are produced and non-empty
- [ ] **6.3** [P] Run the agent on a host with Podman uninstalled (or with `PATH` masked) and
      verify it stops at the pre-flight with remediation instead of failing later
- [ ] **6.4** [P] Run with `PC` (check-only) trigger and verify no machine/state mutation occurs
- [ ] **6.5** Verify no secret value appears in either report or in the chat transcript

---

## Category 7 -- Documentation & Catalog Update

- [x] **7.1** [P] Add `ava-devops-podman-run` to `docs/agents-catalog.md` (F6 section)
- [x] **7.2** [P] Add `CHANGELOG.md` entry (MINOR — new agent + module bump)
- [x] **7.3** [P] `docs/full-pipeline-guide.md` — no change needed (optional, non-blocking agent)
- [x] **7.4** [P] Cross-link `docs/podman-windows-guide.md` as the agent's source of truth

---

## Completion Checklist

- [x] Categories 1, 2, 4, 5, 7 complete (Category 3 skipped by design)
- [ ] Category 6 acceptance run executed on a real Windows host
- [x] SKILL.md created (user-facing, Article XI)
- [x] Agent `.md` frontmatter validated against Article II
- [x] `module.yaml` updated and version-bumped
- [x] `docs/agents-catalog.md` updated
- [x] `CHANGELOG.md` entry added
