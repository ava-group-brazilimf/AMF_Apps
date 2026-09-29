# Agent Specification: Model-Aware Observability

**Feature Branch**: `006-model-aware-observability`
**Created**: 2026-07-06
**Status**: Implemented
**Change Type**: modify-existing (97 agent files + 2 tool scripts + 1 shared doc + 1 README)
**Input**: "Todos agentes contem o bloco de execução... O registro de observabilidade deve ser de acordo com o modelo selecionado na execução do GitHub Copilot, a instrução --model "Claude Opus 4.6" não pode ser hardcode. Crie um plano para resolver e para implementar e documentar via speckit."

---

## 1. Problem Statement

Every agent's `## FASE OBRIGATÓRIA — Registro de Observabilidade` block (97
files, per `specs/005`) hardcoded `--model "Claude Opus 4.6"` in its
`init`/`track` calls, regardless of which LLM model actually executed that
agent. The user correctly identified this as wrong: the recorded model
should reflect whichever model is really selected for that GitHub
Copilot/Claude Code session (Sonnet, Opus, GPT, Gemini, etc.), not a fixed
literal.

**Investigation confirmed two things:**

1. **No mechanism exists** anywhere in this repo, VS Code settings, or any
   documented GitHub Copilot/Claude Code convention to let an agent
   introspect "which model am I running as." The only available mechanism
   is **self-report** — the agent, as an LLM, generally knows its own
   identity when asked, so it must state its own model name itself. This is
   a best-effort mechanism (same category as the existing token/duration
   self-estimates), not a guaranteed-accurate one.
2. **An independent, real bug this exposed**: `pipeline_observer.py` and
   `agent_observability.py` computed cost using a single fixed constant
   (Opus-4.6-era pricing, $15/$75 per 1M tokens) regardless of what
   `--model` string was passed — `_calc_cost(tokens_in, tokens_out)` took no
   `model` parameter at all. So even after fixing the agent-side hardcoding,
   cost figures would have stayed silently wrong for any non-Opus model.

## 2. Decision

Per user correction: **the pipeline's default/fallback model is Claude
Sonnet 4.6, not Opus 4.6.** Cost, CLI defaults, and documentation examples
all changed accordingly. When an agent knows it's genuinely running as a
different model, it self-reports that real value instead of the default.

- **Agent-side**: every occurrence of the hardcoded literal replaced with
  `--model {modelo_atual}` / `--model "{modelo_atual}"`, plus one inline
  resolution note per file (no reference-doc indirection — that pattern
  already failed twice in this saga, per `specs/004`/`specs/005`): *"o
  modelo LLM que você é agora nesta execução. Default do pipeline é 'Claude
  Sonnet 4.6'; SE você souber que está rodando como um modelo diferente...,
  informe esse valor real."*
- Also added `--model {modelo_atual}` to the `track` call itself, which
  previously didn't pass `--model` at all (relying only on the run's
  initial `init`-time model — insufficient for pipelines that mix models
  across agents).
- **Tool-side**: `MODEL_PRICING` lookup table added to both scripts, matched
  case-insensitively by substring (`claude sonnet`, `claude opus`, `claude
  haiku`, `gpt-4`, `gpt-3.5`, `gemini`), with the Sonnet-tier rate as the
  explicit fallback for unrecognized/empty model strings. `_calc_cost` now
  takes a `model` parameter. CLI `--model` argparse default changed from
  `"Claude Opus 4.6"` to `"Claude Sonnet 4.6"`.

## 3. Scope

- `src/shared/tools/pipeline_observer.py` — `MODEL_PRICING`, `DEFAULT_MODEL`,
  `_get_pricing_for_model()`, `_calc_cost(tokens_in, tokens_out, model)`,
  CLI default.
- `src/shared/tools/agent_observability.py` — same treatment, for the legacy
  tool.
- 97 agent `.md` files — mechanical substitution (no repositioning needed;
  the `## FASE OBRIGATÓRIA` blocks from `specs/005` were already correctly
  placed).
- `src/modules/ava-fabric-agents/shared/observability-self-report.md` —
  reference command example and standalone-fallback example updated;
  version bumped to 2.1.0.
- `src/shared/tools/README.md` — new "Cost Calculation (model-aware)"
  section documenting the pricing table and fallback behavior.

## 4. Functional Changes

### 4.1 `pipeline_observer.py` / `agent_observability.py`

| Model family (substring match) | $/1M in | $/1M out |
|---|---|---|
| `claude sonnet` (**default**) | $3.00 | $15.00 |
| `claude opus` | $15.00 | $75.00 |
| `claude haiku` | $1.00 | $5.00 |
| `gpt-4` | $2.50 | $10.00 |
| `gpt-3.5` | $0.50 | $1.50 |
| `gemini` | $1.25 | $5.00 |

Matching is case-insensitive substring search against the full `--model`
string (e.g. `"GPT-4.1"` matches `gpt-4`; `"Gemini 2.5 Pro"` matches
`gemini`). Unrecognized/empty strings fall back to the Sonnet-tier rate.

### 4.2 Agent files

Each `## FASE OBRIGATÓRIA` block now reads (leaf-agent example):

```markdown
`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do
pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um
modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"),
informe esse valor real em vez do default.

​```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent {agent_id} --phase {phase} --version {version} \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
​```
```

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Default model produces default (Sonnet) pricing (CA01)

**Given** no model override, **When** an agent self-reports without
specifying a different model (or explicitly passes `"Claude Sonnet 4.6"`),
**Then** cost is computed at the Sonnet-tier rate ($3/$15 per 1M) — verified
directly: 100k in / 100k out → $1.80.

### Scenario 2 — Different self-reported model produces different, correct cost (CA02)

**Given** an agent that knows it's running as a different model (e.g.
`"Claude Opus 4.6"`, `"GPT-4.1"`, `"Gemini 2.5 Pro"`), **When** it self-reports
that value, **Then** cost is computed at that model's own rate — verified
directly: Opus → $9.00, GPT-4.1 → $1.25, Gemini → $0.625 for the same 100k/100k
token pair.

### Scenario 3 — Unrecognized model falls back safely (CA03)

**Given** an unrecognized or empty `--model` string, **When** cost is
computed, **Then** it falls back to the Sonnet-tier rate rather than
crashing or defaulting to the old Opus rate — verified directly.

### Scenario 4 — Mixed models within the same pipeline run (CA04)

**Given** two agents in the same run self-report different models, **When**
`finalize --auto-report` generates the Excel report, **Then** each agent's
own row shows its own model and correspondingly different cost — verified
directly end-to-end (`ava-asis-orchestrator` as Sonnet → $0.60,
`ava-tobe-orchestrator` as Opus → $1.425, same run).

## 6. Quality Gate Requirements

- [x] No agent contract fields (`name`/`description`/`allowed-tools`) changed
- [x] BDD scenarios cover default, override, fallback, and mixed-model cases, each verified directly (not just asserted)
- [x] No `[NEEDS CLARIFICATION]` markers remain

## 7. Dependencies

- `specs/005-observability-mandatory-phase` (the `## FASE OBRIGATÓRIA` block
  this PBI edits already exists and is correctly placed in all 97 files).

## 8. Exclusions

- No change to the anchor/placement logic from specs/005 — this PBI is a
  pure content edit within already-correctly-positioned blocks.
- No attempt to detect the active model automatically — confirmed
  impossible from within this repo's `.md` files (see research.md).
- The pre-existing, unrelated fence imbalance in `solution-vb.md` remains
  out of scope (same as specs/005's finding).

## 9. Assumptions

- Self-reported model accuracy depends on the LLM's own self-knowledge,
  which varies by provider/version — this is disclosed, not oversold.
- The pricing table is a small, maintained-by-hand set of common model
  families; new/renamed models will fall back to the Sonnet-tier rate until
  the table is updated.

## Success Criteria

| Criterion | Measure |
|---|---|
| Zero hardcoded `--model "Claude Opus 4.6"` arguments remain | Verified via grep across all agent `.md` files |
| Cost varies correctly by model | Verified directly for 6 different model strings, including empty/unknown |
| Mixed-model runs report correctly | Verified end-to-end with 2 different models in one pipeline run |
| Default is Sonnet-tier, not Opus-tier | CLI defaults and pricing fallback both changed accordingly |
