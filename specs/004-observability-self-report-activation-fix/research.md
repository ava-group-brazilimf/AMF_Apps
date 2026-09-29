# Research Notes: Observability Self-Report Activation Fix

## 1. Confirming the feature had never fired (not a hypothesis)

Searched the entire accessible filesystem for `observability` directories
across every project folder (`Meu-ERP`, `Meu-ERP-001`, `Meu-ERP-002`, and
others) and the repo itself: **zero results, anywhere**, including the flat
aggregate `pipeline-run-state.json`/`agent-events.jsonl` that even
`ava-master-orchestrator`'s own PBI-002 integration would have produced by
itself. This ruled out "it's firing for some agents but not others" — the
mechanism was completely inert.

## 2. Why the appendix placement never worked

Five sampled leaf-agent files (one per module) were checked for where their
own instructions place the terminal/handoff instruction relative to the
inserted `## Observability Self-Report` heading. In all five, the section sat
after a `##`-level heading boundary and a `---` divider from the file's
actual last actionable instruction (a numbered final step, a `## Handoff`
section, or a `### Step N — Completion Gate`), with no textual bridge
connecting "I am done" to "now also run this Bash command." None of the five
even contained the literal `↳ ✅` completion token in their own body — that
string is emitted generically per an inherited convention, not scripted
inline.

`SKILL.md` routing was checked and ruled out as the cause: sampled files
(`ava-asis-gaps-risks`, `ava-devops-ci`, `ava-stack-python-backend`) all say
generically "read and follow the agent's instructions" with no section
carve-out.

## 3. The proven counter-pattern already exists in these same files

`ntp_time.py` calls for timing benchmarks are written as literal inline
sub-steps inside the numbered `Step 0`–`Step 7` sequence in
`master-orchestrator.md` (e.g. step `0.4`'s body directly contains
`NTP_START = Bash: python src/shared/utils/ntp_time.py`) and fire reliably.
This is direct, in-file evidence that inline placement works and appendix
placement doesn't — not an assumption imported from general LLM-prompting
theory.

## 4. Each of the 4 phase orchestrators lacks its own explicit completion signal

Grepped all 4 for a literal `↳ ✅ [ava-{phase}-orchestrator]` line or a
`## Completion Signal` section of their own: **none exists**. The signal is
only referenced from the caller's side (`master-orchestrator.md`'s `AWAIT`
lines) and treated as an implicit, inherited convention — stated once,
generically, inside `orchestrator-asis.md` ("cada agente emite `↳ ✅
[{agent_id}]` como última linha da resposta"), not scripted as a concrete
step in any of the 4 files themselves.

Rather than inventing a new, generic completion-signal section in each file
(which would be disconnected from each file's own established structure —
repeating the exact mistake being fixed), each file's own pre-existing
"mandatory before closing" gate was located and reused:

| File | Genuine final gate found |
|---|---|
| `orchestrator-asis.md` | `## Orchestration Completion Gate` — explicitly says "Exibir Completion Banner... Encerrar com `## ⏱ Execução Concluída`" |
| `orchestrator-tobe.md` | `## Execution Timing Output`, marked `⛔ MANDATORY... este bloco é OBRIGATÓRIO`, referenced elsewhere in the file as "Step 6" |
| `orchestrator-stack.md` | Same pattern, referenced elsewhere as "Step 10" |
| `qa-orchestrator-agent.md` | `## Terminal Mandatory Steps (PT → RS)`, an explicit "INVARIANTE GLOBAL... sempre são executados como etapa terminal" |

## 5. Incidental discoveries while editing `orchestrator-tobe.md`

Two regressions, unrelated to observability and pre-dating this specific
fix, were found directly adjacent to the edit region and corrected since they
were touched anyway:

1. Both `## ❱ Execução Concluída — TO-BE` template headings (`true`/`false`
   timing variants) had lost their `{project_name}` placeholder compared to
   the git-committed `HEAD` version. Restored.
2. A stray, orphaned closing code fence at the very end of the file (absent
   in `HEAD`). Removed.
3. The file's line endings had drifted from the repo's native LF (per `HEAD`)
   to CRLF, and every markdown table in the file had been re-padded for
   column alignment by an editor auto-format pass — confirmed byte-for-byte
   identical text content via direct table-by-table comparison, so this is
   cosmetic only. Line endings were normalized back to LF; the table padding
   was left as-is since reverting it cheaply wasn't practical and it causes
   no functional harm.

## 6. Verification performed

- Grepped all 5 files for `pipeline_observer.py -p {project_name} track`:
  exactly one match each, located inside the genuine completion-gate block
  identified above (confirmed by line-number proximity to that gate's other
  content), not past a `---`/`##` boundary into old appendix territory.
- Confirmed code-fence balance (even count of `` ``` `` lines) in all 5 files
  after editing.
- Live dry run: `init` → `track --agent ava-master-orchestrator` →
  `finalize --auto-report` against `Meu-ERP-001` produced
  `outputs/observability/pipeline-run-state.json`,
  `outputs/observability/ava-master-orchestrator/metrics.json`, and a
  4-sheet Excel report — the first time this has ever happened in this repo.
  Test artifacts were cleaned up afterward.
