# AVA Fabric — Governance: Agent Self-Observability

> **Version:** 2.2.0 — July 2026
> **Applies to:** ALL dispatchable agents that generate artifacts — every module in `src/modules/ava-fabric-agents/`.
> **Reference this file as:** `@observability-self-report`

---

## ⚠️ Role of this document (read this first)

Earlier versions of this feature pointed every agent at this shared doc as
the primary place to look up the actionable `track` command. **That did not
work reliably in practice** — a reference like "see `@observability-self-report`"
was read by executing LLMs as descriptive/citation text, not as an instruction
to actually invoke a tool. As of v2.0.0, every agent that needs to self-report
carries its own **self-contained, fully inline** `## FASE OBRIGATÓRIA —
Registro de Observabilidade` section with the concrete command already
written out (no indirection). **This document is now reference/rationale
material** — useful when authoring a *new* agent, or when auditing/debugging
an existing one — not something an executing agent is expected to fetch and
resolve placeholders from at runtime.

## ⚠️ Environment requirement (read this too)

**This mechanism only works if the surface invoking the agent supports live
tool execution** — e.g. GitHub Copilot Chat in Agent Mode with terminal
auto-approval enabled, or Claude Code with Bash permission granted. A
read-only/narrative chat surface (Ask mode, plain completion, or an LLM asked
to "describe" what an agent would do) will silently produce **zero** tool
calls, no matter how the instruction is worded. No prompt engineering inside
this repo's `.md` files can force that — it is a property of the invoking
environment, not of the agent text. If you run an agent and see no
`outputs/observability/` folder appear, verify your invocation mode/tooling
before assuming the agent instructions are at fault. See
`src/shared/tools/README.md` for more detail.

---

## ABSOLUTE INVARIANT

> ⚠️ **Every agent that reaches a terminal state (completed, failed, or skipped)
> MUST record its own execution metrics before emitting its completion signal.**
> This applies regardless of who dispatched the agent — a phase orchestrator,
> `ava-master-orchestrator`, or a standalone/manual invocation. Self-reporting
> is **never** the responsibility of the caller.
> Observability failures **MUST NEVER** block or fail the agent's primary task.
> The actual command each agent runs is written **inline in that agent's own
> `## FASE OBRIGATÓRIA — Registro de Observabilidade` section** — this
> document describes the pattern those sections follow, it is not itself
> where the command is looked up at runtime.

---

## 1. When to Self-Report (MANDATORY)

Immediately **before** emitting your completion signal (the `↳ ✅ [{agent_id}]`
/ `↳ ❌ [{agent_id}]` string, or your own `## Completion Signal` section if you
have one), call the deterministic observability tool for yourself:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent {seu_agent_id} --phase {sua_fase} --version {sua_versao} \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

Resolve each placeholder from your **own** file, not from the caller:

| Placeholder                                            | How to resolve                                                                                                                             |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `{project_name}`                                     | Same resolution you already use for your own output paths (`projects/{project_name}/outputs/...`)                                        |
| `{seu_agent_id}`                                     | Your own frontmatter`name:` field                                                                                                        |
| `{sua_versao}`                                       | Your own frontmatter`version:` field (if absent, use `"1.0.0"`)                                                                        |
| `{sua_fase}`                                         | Derive from your own`name:` prefix using the table below                                                                                 |
| `{modelo_atual}`                                     | **Self-reported, not hardcoded.** The LLM model you are running as right now. Default for this pipeline is `"Claude Sonnet 4.6"` — if you know you're actually a different model (e.g. `"Claude Opus 4.6"`, `"GPT-4.1"`, `"Gemini 2.5 Pro"`), report that real value instead. There is no environment variable or config file that exposes this — it can only be self-reported (see §4 for why). |
| `--status`                                           | `completed` on success, `failed` on a terminal error, `skipped` if you exit early by design (e.g. precondition not met)              |
| `{tokens_in_estimados}` / `{tokens_out_estimados}` | Best-effort estimate of your own input/output token usage for this invocation                                                              |
| `{duracao_medida_ms}`                                | Measure via`python src/shared/utils/ntp_time.py` at the start and end of your own Execution Steps; report the difference in milliseconds |

### Phase lookup by agent-id prefix

| `name:` prefix            | Phase                                             |
| --------------------------- | ------------------------------------------------- |
| `ava-asis-*`              | `F1`                                            |
| `ava-tobe-*`              | `F2`                                            |
| `ava-prototype*`          | `F3` (dispatched directly by master-orchestrator, after F2) |
| `ava-stack-*`             | `F4`                                            |
| `ava-qa-*`                | `F5`                                            |
| `ava-devops-*`            | `F6`                                            |
| `ava-deliverable-*`       | `F7`                                            |
| `ava-summary*`            | `F8`                                            |
| `ava-master-orchestrator` | _(no phase — top-level; pass `--phase ""` )_ |

---

## 2. Standalone / Direct Invocation Fallback (MANDATORY)

You may be invoked directly (not via `ava-master-orchestrator`), in which case
no pipeline run may have been `init`ed yet. If `track` fails with
`ERROR: No active run. Call 'init' first.`:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init \
  --run-type standalone --model "{modelo_atual}"
```

Then retry the `track` call once. Never retry more than once, and never treat
a second failure as blocking (see §3).

---

## 3. Failure Isolation (MANDATORY)

Observability is best-effort instrumentation, not a functional dependency:

- If the `track` (or fallback `init`) call errors for any reason (tool
  missing, malformed arguments, filesystem issue), **log a one-line warning
  and continue** — do not retry beyond §2, do not fail your own task, do not
  surface this as a gate failure.
- Token/duration values are estimates. Do not spend additional turns trying to
  compute them precisely.

---

## 4. Output

A successful `track` call writes to **both**:

- The shared, aggregate pipeline state: `projects/{project_name}/outputs/observability/pipeline-run-state.json` + `agent-events.jsonl` (used by `ava-master-orchestrator` for the cross-agent Excel/JSON/Markdown reports in `projects/{project_name}/outputs/observability/report`).
- Your own per-agent folder: `projects/{project_name}/outputs/observability/{seu_agent_id}/metrics.json` + `events.jsonl` (self-contained record of only your own runs, independent of any other agent's activity in the same pipeline run).

You do not need to create these paths yourself — `pipeline_observer.py track`
creates them.

---

*AVA Fabric — `@observability-self-report` v2.1.0 — July 2026*
