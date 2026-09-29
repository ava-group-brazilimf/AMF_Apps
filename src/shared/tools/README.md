# Agent Observability Tools

Deterministic tooling for tracking and reporting AVA Fabric agent pipeline execution metrics.

> ⚠️ **Environment requirement**: the CLI tools below are ordinary Python
> scripts — they work correctly whenever *anything* invokes them via a real
> shell (verified directly, see `specs/002`-`specs/005` under `specs/`). The
> part that depends on the environment is **who invokes them**: each
> AVA Fabric agent (`src/modules/ava-fabric-agents/**/agents/*.md`) is
> instructed to call `pipeline_observer.py track` on itself via a `Bash:`
> directive in its own markdown. That directive only executes if the surface
> running the agent supports live tool-calling — e.g. GitHub Copilot Chat in
> **Agent Mode** with terminal auto-approval, or **Claude Code** with Bash
> permission granted. A read-only/narrative chat surface (Ask mode, or an LLM
> simply asked to "describe" the agent) will silently produce zero tool
> calls — no wording inside an agent `.md` file can force that. If you run an
> agent and no `outputs/observability/` folder appears, check your
> invocation mode before assuming the agent or this tool is broken.

## Files

| File | Purpose |
|------|---------|
| `pipeline_observer.py` | **Primary tool** — High-level pipeline observability (track, dashboard, report, compare, import) |
| `agent_observability.py` | Low-level CLI — init/start/end/finalize/status/export |
| `generate_observability_report.py` | Report generator — export existing or baseline catalog |
| `_populate_pipeline_agents.py` | Helper — populate all pipeline agents in run state |
| `agent_registry.py` | **Canonical agent source** — scans `**/agents/**/*.md`, reads frontmatter and derives each agent's phase from the Constitution (v1.4.0). Both `AGENT_CATALOG`s are derived from it; the literal lists are fallback only. See `specs/032`. |
| `headroom/` | **Context compression tool** — decodes pre-compressed AST artifacts, resolves each agent's artifact slice, and runs the interceptor proxy in front of the Foundry endpoint. Embedded fork (git subtree) with its own isolated venv. See [headroom/README.md](headroom/README.md) and `specs/031-headroom-context-compression-proxy`. |

| `merge_html_parts.py` | **Remontagem de HTML fragmentado** — reagrupa `*.partN.html` num arquivo único, valida e loga. Wrapper PowerShell: `Merge-HtmlParts.ps1`. Ver seção abaixo. |
| `merge_html_documents.py` | **Fusão de documentos HTML completos** — mesmo caso de uso, quando cada `*.partN.html` é um documento independente (head/nav/main/script próprios). Ver seção abaixo. |

> `gen_er_diagram.py` and `gen_screen_flow.py` also live here (Mermaid generators)
> and are documented in their own module docstrings.

## `merge_html_parts.py` / `Merge-HtmlParts.ps1` — HTML fragmentado

Agentes que emitem HTML grande (`ava-summary` / F8, `ava-prototype` / F3) estouram o
limite de tokens de saída por resposta e gravam o artefato em fragmentos
`*.partN.html`. **Nenhum fragmento abre corretamente no browser** — um tem o
`<head>`/CSS mas não tem o JavaScript, outro tem o JavaScript mas não tem o CSS.

Esta ferramenta recebe a pasta, remonta o documento único, **valida** o resultado e
loga cada decisão. Duas modalidades de quebra são detectadas automaticamente:

| Modalidade | Quando | Remontagem |
|------------|--------|------------|
| `sequential` | Só o último fragmento fecha o documento (corte limpo) | Concatenação na ordem das partes |
| `splice` | Dois ou mais fragmentos fecham o documento (`</main>`, `</body>`) e o conteúdo está trocado de lugar | Costura cirúrgica: seções reinseridas dentro do container, `<script>` realocado para o fim do `<body>`, tags duplicadas descartadas |

A validação reprova o arquivo (exit 1, **não grava**) quando encontra: aninhamento de
tags quebrado, `<html>`/`<head>`/`<body>`/`<main>` duplicados, `id` duplicado, handler
inline chamando função inexistente, ou alvo de navegação (`href="#x"`, `nav('x')`,
`showView('x')`) sem elemento correspondente — exatamente os sintomas de um merge malfeito.

```powershell
# PowerShell (wrapper — valida argumentos, resolve o Python, traduz o exit code)
.\src\shared\tools\Merge-HtmlParts.ps1 -InputDir projects\<proj>\outputs\summary

# Varre todas as subpastas de outputs\ e grava um relatório JSON
.\src\shared\tools\Merge-HtmlParts.ps1 -InputDir projects\<proj>\outputs `
    -Recursive -Report merge-report.json

# Só valida, não grava
.\src\shared\tools\Merge-HtmlParts.ps1 -InputDir .\outputs\tobe\prototype -DryRun
```

```bash
# Python direto (mesma funcionalidade, multiplataforma)
python src/shared/tools/merge_html_parts.py --input-dir projects/<proj>/outputs/summary
python src/shared/tools/merge_html_parts.py -i projects/<proj>/outputs -r --dry-run
```

Exit codes: `0` OK · `1` falha de remontagem ou validação · `2` nenhum `*.partN.html` encontrado.

## `merge_html_documents.py` — fragmentos que são documentos completos

Há uma terceira modalidade de quebra que o `merge_html_parts.py` **não** resolve: cada
`*.partN.html` é um **documento completo e independente** — `<!DOCTYPE>`, `<head>`,
`<style>`, topbar, `<nav>` e `<script>` próprios. É o caso do summary do F8 quando o
agente gera "Parte 1 — AS-IS" e "Parte 2 — TO-BE": o menu da Parte 1 já lista os itens
de F2/F4/F5, mas as seções correspondentes só existem na Parte 2 — **clicar nesses itens
não faz nada**. Concatenar os arquivos também não resolve (gera `<html>`/`<head>`/`<main>`
duplicados e sete `id` repetidos — o `merge_html_parts.py` reprova, corretamente).

| Modalidade | Quando | Remontagem |
|------------|--------|------------|
| `documents` | Todos os fragmentos são documentos completos | `<head>` da parte 1 + regras CSS exclusivas das demais; um `<nav>` só (itens duplicados e links para o outro arquivo removidos); todas as seções deduplicadas por `id` dentro de um `<main>` só; um bloco `<script>` só |
| `legacy` | Qualquer fragmento é parcial | Delega para `sequential` / `splice` do `merge_html_parts.py` |

Além da validação do `merge_html_parts.py`, confere a **cobertura do reagrupamento**:
toda seção de todo fragmento existe no arquivo único, nenhuma referência residual ao
nome dos fragmentos sobrou, e nenhum scaffolding (`<html>`, `<head>`, `<body>`, `<main>`,
`<nav>`, `<title>`) ficou duplicado.

```bash
# Reagrupa e grava na própria pasta
python src/shared/tools/merge_html_documents.py --input-dir projects/<proj>/outputs/summary

# Grava em outra pasta, com log em arquivo e relatório JSON
python src/shared/tools/merge_html_documents.py -i projects/<proj>/outputs/summary \
    -o projects/<proj>/outputs/summary/dist --log-file merge.log --report merge-report.json

# Só valida e loga, sem gravar
python src/shared/tools/merge_html_documents.py -i projects/<proj>/outputs/summary --dry-run
```

Flags úteis: `--mode {auto,documents,legacy}` (padrão `auto`), `--recursive`, `--force`,
`--no-css-dedupe`, `--section-class/--item-class/--group-class` (se o template usar
outras classes que não `sec`/`ni`/`ng`), `--quiet`.

Exit codes: `0` OK · `1` falha de reagrupamento ou validação · `2` nenhum `*.partN.html` encontrado.

## Quick Start — `pipeline_observer.py` (Recommended)

```bash
# 1. Initialize run at pipeline start
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init

# 2. Track each agent (atomic: combines start+end in one call)
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track \
  --agent ava-asis-orchestrator --phase F1 --version 2.18.0 \
  --status completed --tokens-in 50000 --tokens-out 30000 --duration-ms 374000

# 3. View real-time dashboard
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 dashboard

# 4. Finalize and auto-generate all reports (xlsx + json + markdown)
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report

# 5. Generate reports on-demand
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 report --format all

# 6. Import from external JSON
python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 import-json \
  --input docs/optimization/agent-observability-Meu-ERP-001.json

# 7. Compare two runs
python src/shared/tools/pipeline_observer.py compare \
  --run-a projects/Meu-ERP-001/outputs/observability/pipeline-run-state.json \
  --run-b projects/Meu-ERP-002/outputs/observability/pipeline-run-state.json
```

## Reports Generated

| Format | Location | Content |
|--------|----------|---------|
| Excel (.xlsx) | `docs/optimization/` | 4 sheets: Agent Metrics, Pipeline Summary, Phase Breakdown (with chart), Token Analytics |
| JSON | `docs/optimization/` | Full state snapshot |
| Markdown | `docs/optimization/` | Summary + agent table + phase breakdown |

## Integration with Master Orchestrator

The master-orchestrator calls `pipeline_observer.py` at these points:

1. **Pipeline start** → `init`
2. **After each agent completes** → `track --agent <name> --phase <phase> --status <status> --tokens-in <n> --tokens-out <n>`
3. **Pipeline end** → `finalize --auto-report`

## Legacy: `agent_observability.py`

```bash
# 1. Initialize a pipeline run
python src/shared/tools/agent_observability.py -p Meu-ERP-001 init --run-type full-pipeline --model "Claude Sonnet 4.6"

# 2. Record agent start
python src/shared/tools/agent_observability.py -p Meu-ERP-001 start \
  --agent ava-asis-orchestrator --phase F1 --version 2.18.0

# 3. Record agent end (with token counts)
python src/shared/tools/agent_observability.py -p Meu-ERP-001 end \
  --agent ava-asis-orchestrator --status completed \
  --tokens-in 15000 --tokens-out 8500

# 4. Finalize pipeline
python src/shared/tools/agent_observability.py -p Meu-ERP-001 finalize

# 5. Export Excel report
python src/shared/tools/agent_observability.py -p Meu-ERP-001 export --format xlsx
```

## CLI Commands

### `init` — Initialize pipeline run
```bash
python agent_observability.py -p <PROJECT> init [--run-type full-pipeline] [--model "Claude Sonnet 4.6"]
```

### `start` — Record agent start event
```bash
python agent_observability.py -p <PROJECT> start --agent <AGENT_NAME> [--phase F1] [--version 1.0.0]
```

### `end` — Record agent completion
```bash
python agent_observability.py -p <PROJECT> end --agent <AGENT_NAME> \
  [--status completed|failed|skipped] [--tokens-in N] [--tokens-out N] [--model "..."]
```

### `finalize` — Close the pipeline run
```bash
python agent_observability.py -p <PROJECT> finalize
```

### `status` — Show current run state (JSON)
```bash
python agent_observability.py -p <PROJECT> status
```

### `export` — Generate report
```bash
python agent_observability.py -p <PROJECT> export [--format xlsx|json] [--output path]
```

## Excel Report Structure

The generated `.xlsx` contains 3 sheets:

| Sheet | Content |
|-------|---------|
| **Agent Metrics** | Per-agent row: Run ID, Date/Time, Agent Name, Phase, Version, Tokens IN/OUT/Total, Duration (ms), Cost (USD), Status, Model, Run Type |
| **Pipeline Summary** | Aggregated totals: run ID, project, model, status, agent counts |
| **Phase Breakdown** | Per-phase summary: agents, completed, failed, duration, cost |

## Data Storage

- **State**: `projects/{PROJECT}/outputs/observability/pipeline-run-state.json`
- **Events (JSONL)**: `projects/{PROJECT}/outputs/observability/agent-events.jsonl`
- **Per-agent self-report** (written by `pipeline_observer.py track`, in addition to the shared state above): `projects/{PROJECT}/outputs/observability/{agent_name}/metrics.json` + `projects/{PROJECT}/outputs/observability/{agent_name}/events.jsonl` — see `src/modules/ava-fabric-agents/shared/observability-self-report.md` for the self-reporting convention every agent's own `.md` file applies.
- **Excel**: `docs/optimization/agent-observability-{PROJECT}-{RUN_ID}.xlsx`

## Integration with Pipeline

Add these calls around each agent dispatch in the master-orchestrator:

```
# Before dispatching agent
Bash: python src/shared/tools/agent_observability.py -p {project_name} start \
  --agent {agent_id} --phase {phase} --version {version}

# After agent completes
Bash: python src/shared/tools/agent_observability.py -p {project_name} end \
  --agent {agent_id} --status {completed|failed} \
  --tokens-in {estimated_tokens_in} --tokens-out {estimated_tokens_out}
```

## Cost Calculation (model-aware)

Cost is computed from whichever `--model` string is actually passed to
`track`/`end`, matched case-insensitively by substring against a small
pricing table (`MODEL_PRICING` in `pipeline_observer.py` and
`agent_observability.py`):

| Model family (substring match) | Input $/1M tokens | Output $/1M tokens |
|---|---|---|
| `claude sonnet` (**default** — used when `--model` is omitted or unrecognized) | $3.00 | $15.00 |
| `claude opus` | $15.00 | $75.00 |
| `claude haiku` | $1.00 | $5.00 |
| `gpt-4` | $2.50 | $10.00 |
| `gpt-3.5` | $0.50 | $1.50 |
| `gemini` | $1.25 | $5.00 |

Agents self-report `--model` per `@observability-self-report`
(`src/modules/ava-fabric-agents/shared/observability-self-report.md`) — the
default assumes this pipeline's standard model (Claude Sonnet 4.6); an agent
that knows it's actually running as a different model should pass that real
value instead of the default. There is no way for this tool (or any agent
`.md` file) to detect the active model automatically — it is always
self-reported.
