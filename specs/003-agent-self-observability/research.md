# Research Notes: Agent Self-Observability

This PBI required real research before implementation, since a mechanical
batch edit across 101 files needed a reliable, verified insertion strategy —
unlike PBI 002 (pure documentation), this one had to get file-structure facts
right before writing any code or touching any file.

---

## 1. Total agent-file inventory (verified via `Glob`, cross-checked twice)

101 agent `.md` files under `src/modules/ava-fabric-agents/**/agents/`:

| Module | Count |
|---|---:|
| `asis-diagnostic` (incl. `db-analyzer/` + `security/` subfolders) | 29 |
| `tobe-architecture` | 22 |
| `tech-stack` | 13 |
| `devops-agents` | 13 |
| `qa-agents` | 10 |
| `deliverables` | 10 |
| `summary` | 2 |
| `prototype` | 1 |
| `master-orchestrator` | 1 |
| **Total** | **101** |

## 2. Why no single universal insertion anchor exists

- Frontmatter is inconsistent: ~20/101 files lack a `version:` field entirely,
  and field order (`name`/`version`/`date`/`description`/`allowed-tools`) is
  not fixed across files. **Conclusion: never anchor edits on frontmatter
  position.**
- `## Output Contract` exists in 84/101 files but with heading-text variants
  (`(when implemented)`, `(4 artefatos)`) and wildly varying line position
  (line 20 to line 1922) — not a reliable universal anchor either, though
  useful as a lookup target for future, different edits.
- `## Changelog` and `## Completion Signal` exist in only 10/101 files (mostly
  the security-agent cluster + master-orchestrator) — far too sparse to be a
  primary anchor.
- **`## i18n — Idioma dos Artefatos` is the closest thing to a universal
  terminal section — present in 79/101 files, always confirmed as the literal
  last content in the file.** Still not 100% — 22 files lack it.

**Decision**: 3-tier fallback anchor — before `## i18n` (majority) → before
`## Changelog` (files with neither i18n nor need it) → end-of-file (final,
always-safe fallback). This was implemented and verified with 0 errors across
96 files (see §4 below).

## 3. Existing shared-governance-doc convention confirmed reusable

`@governance-apps` (`src/modules/ava-fabric-agents/shared/governance-apps.md`)
is already applied via `> Apply: [@governance-apps](../../shared/governance-apps.md)`
inside the `## i18n` section of 79 files. This is not a rendered link for
humans — it is an LLM-instruction convention: "this agent's behavior is
governed by the file at this path; read and follow it." This is the exact
mechanism reused for `@observability-self-report`, keeping the new feature
consistent with an established pattern rather than inventing a new one.

Cross-module reuse is already established: `src/modules/ava-fabric-agents/shared/`
is referenced via relative paths (`../../shared/...`, `../shared/...`,
`../../../shared/...` for one-level-deeper files) from agents across every
module — tobe-architecture, qa-agents, devops-agents, deliverables,
asis-diagnostic, prototype. This confirmed the new shared doc could live in
the same folder and be referenced the same way from all modules, without
needing a per-module copy.

## 4. Batch-script execution results (ground truth, not projected)

A Python script (see `specs/003-agent-self-observability/quickstart.md` for
the verification commands used to confirm this) processed all 101 candidate
files:

- **96 modified successfully, 0 errors, 0 skips** (idempotency check —
  `observability-self-report` marker string not already present — never
  triggered, confirming this was a clean first run).
- **5 excluded**: 4 `db-analyzer/skills/*.md` (by design) + `master-orchestrator.md`
  (handled by a separate, more substantial manual edit).
- Anchor distribution: majority landed on "before `## i18n`"; the remainder
  ("end of file") were files lacking that section — spot-checked several
  (`database-policy-tobe.md`, `bridge-fastqa-asis.md`, `coder-java-backend.md`)
  and confirmed clean insertion with no corruption, correct relative paths,
  and (for the one file lacking a trailing newline) a benign
  "no newline at end of file" diff artifact, not data loss.
- **Post-run link-integrity check**: every one of the 97 inserted references
  (96 batch + 1 manual) was independently resolved via `Path.resolve().exists()`
  against the real shared-doc path — **97/97 resolved correctly, 0 broken.**

## 5. Confirming the 3 ambiguous "policy-style" files are real dispatch targets

Research for PBI 002 flagged `database-policy-tobe.md`, `dotnet-nuget-policy.md`,
and `database-design-tobe.md` as possibly being reference docs rather than
independently dispatched agents (they lack `## i18n`/`## Changelog`, ending
instead in content/anti-pattern tables). Grepped `orchestrator-tobe.md` for
explicit invocation:

```
374:Invocar `database-policy-tobe.md` com trigger `DBP`.
413:Invocar `database-design-tobe.md` com trigger `DB`.
```

Both **are** explicitly invoked (`Invocar ... com trigger ...`) by the F2
orchestrator — confirming they are real dispatch targets, just triggered
differently (named trigger, not a DISPATCH/AWAIT DAG cycle) than most other
F2 agents. `dotnet-nuget-policy.md` is referenced by name from
`coder-dotnet.md`, `architecture-technical-tobe.md`, and
`coder-dotnet-backend.md` as a policy document they consult — its own
dispatch/execution status is less clear-cut, but instrumenting it is harmless
even if it turns out to be read-only reference material (the self-report
instruction simply never fires in that case). All 3 were included in the
batch rollout rather than excluded.

## 6. Master-orchestrator version drift, now resolved

PBI 002's research already found `master-orchestrator.md`'s frontmatter
(`version: "1.1.0"`) didn't match its own Changelog's latest row (`1.2.0`),
and PBI 002 deliberately deferred fixing it ("document only" scope decision).
Since this PBI substantively edits the same file anyway (adding the
self-reference + a new Changelog row for the self-reporting feature itself),
it was the natural point to resolve the drift: frontmatter now reads `1.3.0`,
correctly reflecting both the previously-undocumented `1.2.0` jump and this
PBI's own `1.3.0` addition, backed by a Changelog row for each.
