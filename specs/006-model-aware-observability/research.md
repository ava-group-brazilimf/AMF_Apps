# Research Notes: Model-Aware Observability

## 1. No mechanism exists to detect the active model automatically

Grepped the entire repo for any trace of a model-name variable: `model_name`,
`selected_model`, `COPILOT_MODEL`, `active model`, `current model`,
`COPILOT_CHAT`, `VSCODE_MODEL`, `GITHUB_COPILOT`, `copilot.chat`,
`chatModel` — zero matches anywhere. `.vscode/settings.json` (full content
inspected) contains only `chat.tools.terminal.autoApprove`,
`livePreview.defaultPreviewPath`, `chat.mcp.autostart`, `files.associations`
— nothing model-related. `.github/` (copilot-instructions.md, agents/,
instructions/, prompts/, skills/, workflows/) has no such mechanism either.

**Conclusion**: the `"model"` value recorded in observability state has
always been, and remains, a string literal supplied by whichever agent
markdown calls the tool — never derived from any runtime signal. Making it
dynamic can only mean making the *agent* self-report accurately, not adding
environment detection that doesn't exist to detect.

## 2. The cost-calculation bug this exposed

Before this fix, both `pipeline_observer.py` (`_calc_cost`, line 227-228 at
the time) and `agent_observability.py` (`cmd_end`, lines 200-203) computed
cost from fixed module-level constants (`COST_PER_TOKEN_IN`/`OUT` and
`DEFAULT_COST_PER_TOKEN_IN`/`OUT` respectively), both hardcoded to
Opus-4.6-era pricing ($15/$75 per 1M tokens). Neither function took a
`model` parameter — the `--model` string was stored as metadata only, never
read by the cost formula. This meant that even if the agent-side hardcoding
were fixed to pass a genuinely different model name, the recorded cost would
still have silently used Opus pricing for every run, regardless of what
model actually did the work.

**Fix**: introduced `MODEL_PRICING` (a small dict keyed by lowercase model-family
substrings) and `_get_pricing_for_model()` (case-insensitive substring
match, falling back to the Sonnet-tier rate) in both files; `_calc_cost` now
threads `model` through to this lookup.

## 3. Default model correction

The initial plan draft kept Opus 4.6 as the fallback (matching the
pre-existing constants). The user corrected this: **the actual default
model used by these agents is Claude Sonnet 4.6**, so the fallback pricing,
CLI `--model` argparse default, and documentation examples should all use
Sonnet-tier values as the baseline — Opus remains available as one normal
table entry, used only when an agent actively self-reports running it.

## 4. Verification performed

- Ran `pipeline_observer.py track` six times against identical token counts
  (100k in / 100k out) with `--model` set to `"Claude Sonnet 4.6"`,
  `"Claude Opus 4.6"`, `"GPT-4.1"`, `"Gemini 2.5 Pro"`,
  `"SomeUnknownModelXYZ"`, and empty string — got `$1.80`, `$9.00`, `$1.25`,
  `$0.625`, `$1.80` (fallback), `$1.80` (fallback) respectively. Confirms
  both the per-model rates and the fallback behavior work as designed.
- Ran a full `init` → `track` (×2, different agents/models) → `finalize
  --auto-report` sequence in one pipeline run: `ava-asis-orchestrator` as
  Sonnet cost `$0.60` for 80k tokens, `ava-tobe-orchestrator` as Opus cost
  `$1.425` for 35k tokens — both correct at their respective rates, in the
  same run, same Excel report, confirming mixed-model pipelines are handled
  correctly.
- Verified via grep: zero remaining `--model "Claude Opus 4.6"` hardcoded
  arguments across all agent `.md` files; 97/97 files now reference
  `{modelo_atual}`; every file has `--model {modelo_atual}` wired into both
  its `track` call and its standalone-`init` fallback.

## 5. Incidental finding: recurring external-edit artifact in `orchestrator-tobe.md`

While applying this fix, `orchestrator-tobe.md` was found to be missing its
`## FASE OBRIGATÓRIA` heading (present in all other 96 files) and to have
the *same* dropped-closing-fence regression in its `## Output Contract` YAML
block that was found and fixed once already during `specs/005`. Both were
restored (heading re-added, fence closed) while applying this fix, since the
file needed individual handling anyway (the batch script correctly skipped
it for lacking the heading, avoiding a wrong-anchor insertion). This appears
to be a recurring artifact of an external editor/formatting pass this file
is repeatedly subjected to outside of this session's own edits — worth
flagging to the user as something to watch for if it recurs again.
