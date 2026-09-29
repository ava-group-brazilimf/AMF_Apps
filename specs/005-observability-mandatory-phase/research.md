# Research Notes: Observability Mandatory Phase

## 1. Diagnostic question that changed the whole approach

Asked the user directly: did other Bash-invoked behaviors in `orchestrator-asis.md`
(NTP timing, Summary HTML generation) fire when they tested it? Answer:
**no — nothing fired at all.** This ruled out "just a phrasing/placement
issue within one file" as the complete explanation and triggered a fresh
investigation into the actual invocation mechanism.

## 2. No enforced tool-calling wiring exists for ava-fabric-agents

- `README.md`, `docs/full-pipeline-guide.md`, and `docs/guia-execucao-fluxo-agentes.md`
  are mutually inconsistent about invocation syntax (`@mention` vs `/slash`),
  and none specify Ask-mode vs Agent-mode in VS Code Copilot Chat.
- `.github/agents/speckit.*.agent.md` + `.github/prompts/speckit.*.prompt.md`
  is GitHub Copilot's real, wired custom-agent/prompt-file feature — proven
  to invoke Bash reliably (backed by `.vscode/settings.json`'s
  `chat.tools.terminal.autoApprove`). It does **not** use `allowed-tools:`
  frontmatter at all.
- `.specify/memory/constitution.md` calls `allowed-tools:` "Claude Code tool
  names," but there is no `.claude/` directory or Claude Code agent
  registration anywhere in this repo — the field is inert metadata.
- `.github/skills/*/SKILL.md` files use the Anthropic Agent-Skills shape
  (`name` + `description` only) but nothing in the repo registers
  `.github/skills/` as a real skills directory for any concrete harness.
- No runner/wrapper script exists anywhere (`scripts/`, `tools/`, root
  `package.json`/Makefile-equivalent) that would invoke these agents outside
  an LLM chat conversation.

**Conclusion**: "paste the `.md` into an LLM chat and have it follow the
instructions" is genuinely the entire invocation mechanism. Bash-call
reliability has always been an implicit assumption, never a verified,
enforced guarantee — regardless of how the instruction is worded.

## 3. Anchor survey (10 sampled + 91-file scan)

No single heading name is universal. Five vocabularies found in use:
`Handoff`, `Completion Signal`, `Validation Gate`/`Verification Protocol`/
`Integrity Check`, `Execution Steps`/`Execution Algorithm`/`Core Workflow`/
`Method`, or no dedicated heading at all (checklist-style or protocol-style
endings). Regexes were iteratively broadened during dry-run review (adding
`checklist de conclusão`, `validation checklist`, `critério de aceite`,
`acceptance criteria`, `execution steps`/`passos de execução` substrings,
`regras de execução`) to reduce the Tier-5 fallback count from 18 → 12,
verified by direct inspection of each newly-caught file before accepting the
broadened pattern.

Final Tier-5 fallback list (12 files) was individually reviewed: 9 are
genuine stub/unimplemented agents (`0.1.0-stub` version) with no real
procedure yet; 3 (`defect-identifier-agent.md`, `developer-guide-tobe.md`,
`user-journeys-tobe.md`) are short, simple agents confirmed by direct read to
have no stronger anchor available — falling back to the pre-i18n position is
the correct, not-lazy, choice for these.

## 4. Verifying the 3 severely-misplaced files

Prior investigation (specs/004) flagged 3 files where the existing (broken)
self-report section sat near the very top of the file, disconnected by
hundreds/thousands of lines from the real end. The new script's
remove-then-detect approach (compute the anchor on the *cleaned* line list,
after excising the old section from wherever it was) handled all 3 correctly
without bespoke code:

| File | Old (wrong) position | New (correct) position |
|---|---|---|
| `baseline-test-generator-asis.md` | line 42 of 616 (6%) | after `## Completion Signal` (~line 583 of 622) |
| `behavior-mapping-agent.md` | line 38 of 436 (8%) | after `### STEP 6 — COMPLETION-SIGNAL` (~line 420 of 461) |
| `coder-angular-frontend.md` | line 166 of 3107 (5%) | after the `#### 10.4 — Handoff` block (~line 3104 of 3117) |

Verified by direct read after the batch run, per the plan's commitment not
to assume these cases were fixed just because the general mechanism ran
without errors.

## 5. Two unrelated regressions found and fixed in `orchestrator-tobe.md`

While re-strengthening this file's phase content (a manual edit, not the
batch script), a full-file fence-balance check revealed an **unclosed
```yaml** fence opened at the `## Output Contract` block (originally
opened correctly and closed in git `HEAD`, but the closing fence had been
dropped by an earlier, unrelated editor-driven pass in this same working
session — confirmed by diffing against `git show HEAD`). This caused every
heading between that point and the next `` ``` `` occurrence to be
mis-detected as "inside a fence," which — had the anchor detector run on
this file via the batch script rather than a manual edit — could have
caused a wrong or skipped insertion. Fixed by restoring the missing closing
fence at the same position `HEAD` has it (immediately before
`## Execution Timing Output`). This is unrelated to observability but was
directly adjacent to the work and low-risk to fix while already in the file.

## 6. Tool genericity re-confirmed

`pipeline_observer.py` was exercised against two different project names in
the same session (`Meu-ERP-001` and a never-before-seen
`Another-Random-Project-XYZ`) — both produced correctly isolated
`outputs/observability/{agent}/metrics.json` files and shared state, with no
code changes needed. This confirms the "must work independent of source
code/project" requirement was already satisfied by the tool; the actual gap
was entirely on the agent-instruction side.

## 7. Real project data corroborates the diagnosis

A search across the user's actual, substantial project output directories
(`Meu-ERP-002`, `Meu-ERP-003`, `Meu-ERP-004` — real pipeline run artifacts,
not test data) for any `observability` folder found exactly one match:
`Meu-ERP-003/outputs/tobe/docs/decisions/ADR-007-observability.md` — an
architecture decision record *about* observability for the client's target
system, unrelated to this pipeline's own metrics tracking. Zero real
`outputs/observability/` tracking data exists anywhere, consistent with the
conclusion that the mechanism has never fired in any real run to date.
