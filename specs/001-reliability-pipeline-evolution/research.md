# Research: Reliability Pipeline Evolution

**Phase**: 0 — Pre-design research
**Date**: 2026-07-02
**Spec**: [spec.md](./spec.md)

---

## Summary of Findings

All five components named in the spec were inspected against the live repository.
The implementation state is **substantially complete**. The only gap is one missing
configuration section in the project template.

---

## Decision 1 — `build_runner.py` Podman Support

**Decision**: Already implemented (no new work required).

**Rationale**: `build_runner.py` (516 lines, `src/shared/utils/build_runner.py`)
exposes all flags required by RF01–RF04:
- `--runtime podman` flag accepted
- `--normalize-path --runtime podman` emits native Windows paths (`C:/...`) on MSYS2
- `--normalize-path` without `--runtime podman` emits MSYS2 paths (`//c/...`)
- `--image angular {frontend_version} --node-version {node_version}` — explicit node version override
- Warning emitted when `node_version` differs from the version implied by `frontend_version`
- `--detect-runtime`, `--runtime-info` helpers for orchestrator Step 0.9

**Alternatives considered**: Rewrite in a new `podman_utils.py` — rejected, logic already
correctly colocated in `build_runner.py`.

---

## Decision 2 — `ava-stack-build-validator` Multi-Feature Update

**Decision**: Already implemented at v2.3.0 (date: 2026-07-01) — no new work required.

**Rationale**: Inspection of `build-validator-agent.md` confirmed all spec requirements present:

| Requirement | Status | Location in file |
|---|---|---|
| RF05 — `node_version` guardrail | ✅ Implemented | Step B0.3 — explicit guardrail block |
| RF06/RF07 — CVE policy modes | ✅ Implemented | Step F3.5 — reads `quality_gates.cve_policy` |
| RF08 — Expired exception blocking | ✅ Implemented | CVE policy expiry check in Step F3.5 |
| RF09/RF10 — Lockfile recovery | ✅ Implemented | Step F3 — `fix_result.lockfile_updated` check |
| RF11/RF12 — ESLint detection + skip | ✅ Implemented | Step F3 — flat + legacy config detection |

Version v2.3.0 already surpasses the `1.1.0` target in the spec. No version bump required.

**Alternatives considered**: Cherry-pick individual steps — not needed, all steps present.

---

## Decision 3 — `ava-stack-build-fixer` Lockfile Protocol

**Decision**: Already implemented at v1.1.0 (date: 2026-07-01) — no new work required.

**Rationale**: Inspection of `build-fixer-agent.md` confirmed:
- Lockfile regeneration protocol (RF13): any `package.json` modification triggers `npm install`
- `lockfile_updated: boolean` field (RF14) present in output contract
- Guardrail: `⛔ PROIBIDO retornar fix_result sem regenerar o lockfile quando package.json foi modificado`

**Alternatives considered**: None.

---

## Decision 4 — `ava-stack-angular-frontend` ESLint Scaffolding

**Decision**: Already implemented at v1.0.0 (date: 2026-06-01) — no new work required.

**Rationale**: Inspection of `coder-angular-frontend.md` confirmed:
- All 7 ESLint devDependencies in `package.json` template (RF15)
- `@angular-eslint/builder:lint` target in `angular.json` (RF16)
- `.eslintrc.json` generation in Step 2.2.1 (RF17)
- ESLint version table with compatibility constraints for Angular ≤17

**Alternatives considered**: None.

---

## Decision 5 — `project-config.yaml` Template — `cve_policy` Section

**Decision**: **MISSING — implementation required.** (RF18 — partial)

**Rationale**: The template at `projects/_template/context/project-config.yaml` already
contains `tobe_stack.node_version: "22"` (RF18, field 1 — DONE), but is **missing** the
`cve_policy` sub-section under `quality_gates` (RF18, field 2 — MISSING).

The `build-validator-agent.md` (Step F3.5) reads:
```yaml
quality_gates:
  cve_policy:
    accepted_exceptions: [...]
```
...from `project-config.yaml`. If this key is absent, the agent defaults to
`CVE_POLICY_MODE = "zero_tolerance"` — which is correct default behaviour.
However, the template must document the key so project teams know how to configure it.

**What must be added** to `quality_gates` in the template:
```yaml
  # ── CVE Policy ─────────────────────────────────────────────────────────────
  cve_policy:
    # Modo de tratamento de CVEs detectadas pelo npm audit / dotnet-outdated.
    # zero_tolerance  : qualquer CVE high/critical bloqueia o build (padrão).
    # exceptions_allowed : CVEs listadas em accepted_exceptions são permitidas
    #                      até a data de expiração.
    mode: "zero_tolerance"             # zero_tolerance | exceptions_allowed
    accepted_exceptions: []
    # Exemplo de exceção (usar apenas quando mode: exceptions_allowed):
    # accepted_exceptions:
    #   - cve_id: "CVE-2024-XXXXX"
    #     package: "nome-do-pacote"
    #     reason:  "upstream fix não disponível — mitigado via WAF"
    #     expiry:  "2026-12-31"         # ISO date; exceção expirada = bloqueante
```

**Alternatives considered**: Leave template without `cve_policy` and rely on agent
default — rejected because it leaves teams without a discoverable configuration path.
Adding inline documentation (comments) to the template is the standard practice in this
codebase (see `build_runner:`, `quality_gates:` sections).

---

## Remaining Work Summary

| Task | File | Type | Effort |
|---|---|---|---|
| Add `cve_policy` section to template | `projects/_template/context/project-config.yaml` | Config addition | XS |
| Update `CHANGELOG.md` — mark staged changes complete | `CHANGELOG.md` | Doc update | XS |
| Verify `projects/Meu-ERP/context/project-config.yaml` | `projects/Meu-ERP/context/project-config.yaml` | Config sync | XS |

No agent `.md` files require modification.
