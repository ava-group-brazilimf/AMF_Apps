# Requirements Checklist: `ava-devops-podman-run`

**Spec**: `specs/029-podman-local-runner/spec.md`

## Constitutional compliance

- [x] Agent ID matches `^ava-[a-z0-9-]+$` and the `ava-{fase}-{papel}` convention (Art. II)
- [x] Frontmatter limited to `name`, `version`, `description`, `allowed-tools` (Art. II)
- [x] Agent body written in Brazilian Portuguese (Art. V)
- [x] Registered in the **module-level** `module.yaml`, not the root one (Art. IV)
- [x] Module version bumped MINOR for a new user-facing agent (Art. X)
- [x] Output paths use lowercase `{project_name}` (Art. II)
- [x] BDD scenarios cover nominal + edge + quality gate (Art. VI)
- [x] `trace_id` read and propagated unmodified (Art. VIII)
- [x] SKILL.md exists for user-facing dispatch (Art. XI)
- [x] No hardcoded tool/runtime versions — all read from the host or compose files (Art. I)

## Functional requirements

- [x] Verifies every prerequisite listed in `docs/podman-windows-guide.md` § Pré-requisitos
- [x] Distinguishes **blocking** from **warning** pre-flight failures
- [x] Prints copy-pasteable remediation for each failed check and stops before proceeding
- [x] Provisions the Podman Machine (`init` with host-derived sizing, `start`, `DOCKER_HOST`)
- [x] Discovers `project_name`, `source_code_path`, compose files, services, ports and
      required env vars without asking when they are discoverable
- [x] Asks the user only for values that discovery could not resolve
- [x] Materializes `.env` from `.env.example` + compose `${VAR}` references
- [x] Supports dev / full / staging / prod-validate compose targets
- [x] Waits for health with a bounded budget instead of blocking indefinitely
- [x] Classifies failures against the guide's troubleshooting section
- [x] Reports reachable URLs derived from the compose `ports:` mappings
- [x] Writes `podman-preflight.md` and `podman-run-report.md`
- [x] Emits an observability `track` record (`pipeline_observer.py`)

## Security requirements

- [x] Secret **values** never printed to chat, logs or reports — only names + set/unset state
- [x] `.env` never committed; agent verifies `.gitignore`/`.dockerignore` coverage
- [x] No unattended elevated/administrator command — the agent instructs, the user executes
- [x] Destructive operations (`down -v`, `machine rm`, `Stop-Process`) require explicit
      user confirmation naming the exact resource to be destroyed

## Open items

- [ ] Category 6 acceptance run on a real Windows host (see `tasks.md`)
- [ ] Decide in a future MINOR whether `ava-devops-orchestrator` should auto-dispatch this
      agent as a non-blocking step of the `DE` execution moment
