# Research / Reconciliation Notes: Agent Pipeline Observability

> Unlike a greenfield feature, this PBI documents an already-shipped
> implementation. "Research" here means reconciling two independent code
> read-throughs against each other and against the spec's claims, and closing
> any apparent discrepancies with a definitive answer rather than leaving them
> open. Two passes were performed: (1) a direct read of every file involved,
> (2) an independent background-agent read of the same files. Both converged
> on the same facts below.

---

## 1. Is the "3 sheets vs 4 sheets" difference a bug?

**No.** These are two independently implemented Excel exporters:

- `pipeline_observer.py._generate_xlsx` (verified directly, lines ~607–853)
  produces 4 sheets: `Agent Metrics`, `Pipeline Summary`, `Phase Breakdown`
  (with an embedded `BarChart`), `Token Analytics`.
- `agent_observability.py._export_xlsx` (verified directly, lines 292–472)
  produces 3 sheets: `Agent Metrics`, `Pipeline Summary`, `Phase Breakdown`
  (no chart, no Token Analytics sheet).

`ava-master-orchestrator.md` only ever calls `pipeline_observer.py` (confirmed
by grep — the only file referencing either tool). Its Changelog claim of "4
sheets... Phase Breakdown com chart, Token Analytics" is accurate **for the
tool it actually calls**. `agent_observability.py` is explicitly labeled
"Legacy" in `README.md`, which recommends `pipeline_observer.py` for new
work. `generate_observability_report.py` imports its Excel writer from the
*legacy* module, so its own outputs are 3-sheet, not 4-sheet — worth knowing
if someone runs `generate_observability_report.py --mode baseline` expecting
parity with `pipeline_observer.py report --format all`.

**Conclusion**: not a discrepancy to fix. Three tools, two different
exporters, correctly attributed in spec.md §4.

---

## 2. What is the one concrete implementation gap?

`ava-master-orchestrator.md` frontmatter (line 3): `version: "1.1.0"`.

The same file's own Changelog table (line 870):
`1.2.0 | 2026-07-02 | Adicionada integração com pipeline_observer.py para observabilidade determinística; Excel com 4 sheets (...)`

The Changelog entry describes exactly the feature this spec documents, but
the frontmatter version field was never bumped to match. Per Constitution
Article X (SemVer bumps for MINOR changes), this is a one-line, low-risk fix
— captured as `tasks.md` Category 2, Task 2.1.

No other version/frontmatter drift was found in any of the 4 utility scripts
(none carry version fields — they are plain Python CLI scripts, not agents,
so Article II's frontmatter mandate does not apply to them).

---

## 3. Is the appendix-only wiring a real gap, or just how this repo documents integrations?

Checked against the 001 precedent and against every other section of
`master-orchestrator.md` itself: every other cross-cutting concern in the file
(timing/NTP, TodoWrite progress tracking, the Agent Completion Registry) is
either inlined directly into the numbered steps or referenced by an explicit
step number pointing back into the step body (e.g. `7.5 Emitir ## ⏱ Execução
Concluída (ver § Timing Output)` — note this one *does* cross-reference from
inside Step 7). The observability section, by contrast, introduces step
labels (`0.4b`, `7.0b`) that do not exist anywhere in the actual `### Step 0`
/ `### Step 7` bodies, and no DISPATCH/AWAIT cycle in Steps 1–6 references a
`track` call at all.

**Conclusion**: this is a real, if minor, structural gap — not house style.
Confirmed by direct re-read of Steps 0 and 7 at documentation time (not just
the earlier exploration pass), so the finding is current, not stale.

---

## 4. Is the Article V English-body-prose item a real violation or an established pattern?

Checked every `## `/`### ` header in the file: all are English (`Role &
Persona`, `Execution Pipeline`, `Agent Team`, `Input Contract`, `Output
Contract`, `Guardrails`, etc.) — so English *headers* are consistent house
style throughout, and the new section's header is not an outlier.

However, comparing *body* prose: the `Role & Persona` section's body reads
"Você é o Coordenador-Chefe da AVA Fabric..." (Portuguese), and every other
section's instructional body text is likewise Portuguese. The new
observability section's body opens with "Deterministic observability tool
for tracking agent execution metrics during the pipeline. Called by the
master-orchestrator at lifecycle points to record timing, tokens, and cost."
— English prose, inconsistent with the rest of the file's body-language
convention.

**Conclusion**: a genuine, if minor, Article V inconsistency — not a
pre-existing pattern. Recorded as an optional PATCH-level fix
(`tasks.md` Category 5), not blocking.

---

## 5. Is `docs/agents-catalog.md`'s silence on `ava-master-orchestrator` an oversight?

Grepped the catalog file (case-insensitive) for "master-orchestrator" —
zero matches. The catalog is structured around phase agents (F1 through F8);
`ava-master-orchestrator` sits one level above all phases as the top-level
entry point and is not itself a phase agent.

**Conclusion**: intentional scope, not an oversight. Recorded in spec.md §8
Exclusions and `tasks.md` Category 7 as "confirmed out of scope," not a gap
to fix.

---

## 6. Is there a naming collision with any other "observability" agent?

Yes — `ava-devops-monitoring-observability` (F7 DevOps,
`src/modules/ava-fabric-agents/devops-agents/agents/monitoring-observability-agent.md`)
is a completely different feature: it generates **application-level**
monitoring artifacts (Azure Monitor alerts, Application Insights dashboards,
KQL queries, SLO/SLI definitions, health checks, OpenTelemetry/Serilog
config) for the *client's modernized target system* being migrated — driven
by a `project-config.yaml` `observability` section. It has no relationship to
this PBI's subject, which is tracking the **AVA pipeline's own** agent
execution metrics (tokens/cost/duration). Explicitly distinguished in
spec.md §8 to prevent confusion.

---

## Summary of open items carried into tasks.md

| # | Item | Disposition |
|---|---|---|
| 1 | Frontmatter version 1.1.0 → 1.2.0 | Fix now — `tasks.md` Category 2, Task 2.1 |
| 2 | Output Contract backfill (5 observability paths) | Optional, deferred — `tasks.md` Category 7 |
| 3 | Appendix-only wiring (Step 0.4b/track/7.0b) | Documented, not remediated — `tasks.md` Category 5/6 verification only |
| 4 | Article V English body-prose | Optional PATCH fix, deferred — `tasks.md` Category 5 |
| 5 | `docs/agents-catalog.md` scope | Confirmed intentional, no action — `tasks.md` Category 7 |
| 6 | `AGENT_CATALOG` duplication across 2 files | Recorded in plan.md Complexity Tracking, no action this PBI |
