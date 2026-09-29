# Agent Implementation Plan: Headroom Context Compression — Tool + Proxy Interceptor

**Feature Branch**: `031-headroom-context-compression-proxy`
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md) ·
**Tasks**: [tasks.md](./tasks.md) · **Quickstart**: [quickstart.md](./quickstart.md)

## Summary

Internaliza o Headroom como tool do repositório (fork embedded via `git subtree`)
e fecha as três lacunas que a spec 030 deixou do lado da **compressão**: nada
interceptava as chamadas ao LLM, o que já estava comprimido não era lido, e a
economia não era atribuível a agente.

A decisão estrutural é consequência de um fato do repo: **não existe cliente LLM
em Python aqui**. Os agentes são `.md` executados por um host surface. Logo a
interceptação de 100% das requisições só é possível num **proxy local**, e a
integração com os agentes se dá pela mesma diretiva `Bash:` que
`pipeline_observer.py` já usa.

## Constitution Check

### Constitution Gates

| Artigo | Gate | Status |
|---|---|---|
| **I — Configuration-Driven** | Nenhum endpoint/modelo/limiar hardcoded | ✅ `headroom.yaml` (defaults) → `project-config.yaml` bloco `headroom:` → env. `headroom_config.load_config()` é o único resolvedor; nenhum outro módulo lê `os.environ`. |
| **II — Agent Contract** | Frontmatter só `name/version/description/allowed-tools` | ✅ Nenhum agente novo. Nos 5 modificados só `version` mudou. |
| **III — Pipeline Execution** | Não altera o contrato de dispatch | ✅ A tool é invocada por `Bash:` dentro do agente; o DAG e o `AgentResult` não mudam. |
| **IV — Module Registration** | `module.yaml` atualizado se houver agente novo | ✅ N/A — nenhum agente novo. Registro da tool = linha em `src/shared/tools/README.md`. |
| **V — Language Convention** | Corpo/docstrings/logs em pt-BR | ✅ Os 4 módulos Python, os scripts e os blocos de agente em pt-BR. Vendor (terceiros) em inglês, intocado. |
| **VI — Test-First Behavior** | Cenários BDD antes da implementação | ✅ 8 cenários (CA01–CA08) em spec.md §4; 22 testes em `tests/tools/`. |
| **VII — Security-First** | Segredos e superfície de rede | ✅ Proxy em `127.0.0.1` por default (a chave do Foundry trafega por ele). `.copilot-key` e `.env` gitignorados; `.env.example` sem valores. Container roda como UID 10001 e publica só em `127.0.0.1`. |
| **VIII — Observability** | Métricas rastreáveis | ✅ `outputs/observability/headroom-metrics.jsonl` ao lado de `agent-events.jsonl`; timestamps BRZ; `--run-id` aceito para correlação. |
| **IX — Clean Architecture** | Separação de responsabilidades | ✅ config / decodificação / CLI / MCP em módulos distintos; vendor isolado em `vendor/`. |
| **X — Versioning** | Bump correto por tipo de mudança | ✅ MINOR nos 5 agentes (só adições). Consistência tripla verificada. |
| **XI — Skill/Agent Separation** | SKILL.md para agente user-facing | ✅ N/A — é tool, não agente. Entrada de usuário é a CLI e o `.bat`. |

### Quality Gate Check

- [x] `pytest tests/tools/ -q` → 22 passed
- [x] `pytest tests/utils/ -q` → 28 passed (sem regressão nos consumidores)
- [x] `grep -rn "__headroom__" src/ --exclude-dir=vendor` → só `headroom_context.py`
- [x] `grep -rn "AGENT_ARTIFACT_MAP" src/` → vazio
- [x] `python src/shared/tools/headroom/headroom_tool.py doctor` executa sem venv
- [x] `git check-ignore` confirma `.env.example` e `.vscode/mcp.json` versionáveis,
      `.venv/` e `.headroom/` ignorados

## 1. Technical Context

| Item | Valor |
|---|---|
| Linguagem | Python 3.10+ (repo roda 3.13.3) |
| Dependências novas | `headroom-ai[proxy,mcp,ml,code,memory,otel]==0.33.0`, `pyyaml`, `pytest` — **todas confinadas ao venv da tool** |
| Endpoint alvo | `https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic` (Anthropic-compatible, **não** Azure OpenAI) |
| Modelo / janela | `claude-sonnet-4-6` / 200.000 tokens |
| Porta do proxy | 8787, bind `127.0.0.1` |
| Plataforma primária | Windows (PowerShell + `.bat`); paridade `.sh` entregue |
| Build do fork | maturin (Rust) — opcional em host, obrigatório no container |

**Restrição herdada**: o repo não tem `requirements.txt`/`pyproject.toml` na raiz
e é stdlib-only. Esta entrega abre a exceção **contida** em
`src/shared/tools/headroom/` — nada fora dessa pasta ganha dependência nova. Os
dois consumidores modificados importam a tool com `try/except ImportError` e um
`decode_headroom` no-op de fallback.

## 2. Phase Placement

Fase **F1 (AS-IS)** para a instrumentação de agentes, mas a tool é
**transversal**: o proxy intercepta qualquer fase, e `headroom_tool.py` aceita
`--phase` livre. A escolha de instrumentar só F1 agora segue o fato de que os
artefatos AST comprimidos só existem em F1.

## 3. Clean Architecture Alignment

```
┌─ interface ────────────────────────────────────────────────┐
│ headroom_tool.py (CLI)  ·  mcp_server.py (MCP)             │
│ run_standalone.*  ·  copilot-cli-headroom.bat              │
└───────────────────────┬────────────────────────────────────┘
┌─ domínio ─────────────▼────────────────────────────────────┐
│ headroom_context.py — decodificação + fatia por agente     │
│   importa AGENT_ARTIFACT_SLICE de context_budget.py        │
└───────────────────────┬────────────────────────────────────┘
┌─ configuração ────────▼────────────────────────────────────┐
│ headroom_config.py — env > project-config.yaml > headroom.yaml │
└───────────────────────┬────────────────────────────────────┘
┌─ infraestrutura ──────▼────────────────────────────────────┐
│ vendor/ (fork headroom-ai) · .venv/ · proxy 8787           │
└────────────────────────────────────────────────────────────┘
```

Dependências apontam sempre para dentro. `headroom_context` não conhece a CLI;
`headroom_config` não conhece o domínio; o vendor não conhece nada do AVA Fabric.

## 4. Agent File Structure

Nenhum agente novo. Nos 5 modificados, insere-se uma seção após o Step 1:

```markdown
### Step 1.1 — Registro de Compressão Headroom (OBRIGATÓRIO)
⛔ EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.
Bash: python src/shared/tools/headroom/headroom_tool.py -p {project_name} metrics \
  --agent <agent_id> --phase F1 --model {modelo_atual} \
  --original {tokens_sem_compressao} --compressed {tokens_in_estimados} \
  --latency-ms {duracao_medida_ms}
```

Comando **literal e inline**, com o `agent_id` já substituído — nunca por
`@referência`. `observability-self-report.md` v2.2.0 documenta que a indireção
era lida pelos LLMs executores como texto descritivo, não como instrução.

## 5. module.yaml Impact

Nenhum. A tool não é agente e não entra em `module.yaml`. O registro no repo é:
(a) linha na tabela `## Files` de `src/shared/tools/README.md`; (b) o comando
literal dentro de cada agente consumidor.

## 6. Observability & Trace Propagation

Duas camadas complementares, por necessidade:

| Camada | Cobertura | O que sabe | O que **não** sabe |
|---|---|---|---|
| Proxy (`HEADROOM_LOG_FILE`) | 100% das requisições | model, tokens_before/after, latency_ms | qual agente originou |
| `headroom_tool.py metrics` | só agentes instrumentados | agent_id, phase, run_id | nada além do auto-reporte |

Nenhuma das duas basta sozinha: o proxy não consegue atribuir a economia a um
agente, e o auto-reporte não cobre chamadas fora dos agentes instrumentados.
`--run-id` permite correlacionar com `pipeline-run-state.json`.

Trace ID W3C (Artigo VIII) permanece o gap aberto herdado das specs/002 e 006 —
não regride, mas também não é fechado aqui.

## 7. Schema Changes

Nenhum schema em `src/shared/schemas/` foi alterado. O formato do JSONL de
métricas é novo e documentado em spec.md §3.6 e no README da tool. O bloco
`headroom:` do `project-config.yaml` é **inteiramente opcional** — omitido,
valem os defaults da tool, então projetos existentes não precisam de migração.

## 8. Implementation Phases

| # | Fase | Entrega | Bloqueia |
|---|---|---|---|
| 0 | Spike da CLI | Superfície real de `headroom proxy/wrap/doctor` → `research.md` | tudo |
| 1 | Subtree + venv | `vendor/`, `requirements.txt`, `setup.ps1/.sh`, `.gitignore` | 2–7 |
| 2 | Configuração | `headroom.yaml`, `headroom_config.py`, bloco no `_template` | 3–5 |
| 3 | Domínio | `headroom_context.py` + roundtrip validado | 4, 6 |
| 4 | Interface | `headroom_tool.py`, `mcp_server.py` | 5, 7 |
| 5 | Interceptação | `.bat`, `run_standalone.*`, `mcp.json`, `settings.json`, `.env.example`, Podman | — |
| 6 | Consumidores | `sql_ir_generator.py`, `build_summary_comprehensive.py` | — |
| 7 | Agentes | Step 1.1 nos 5 agentes + bumps + 2 catálogos | — |
| 8 | Documentação | `specs/031-*`, READMEs | — |

Caminho crítico: **0 → 1 → 3**. A fase 0 é bloqueante porque o prompt de origem
assumia flags (`--upstream`) e comandos (`headroom stats`) que **não existem**.

## 9. Complexity Tracking

| Complexidade | Justificativa | Alternativa descartada |
|---|---|---|
| 60,5 MB de terceiros versionados | Decisão explícita do usuário por fork embedded (I4), para poder patchear o motor | Dependência pip pura — recomendada mas recusada |
| Segundo venv | `headroom-ai` puxa fastapi/uvicorn/onnxruntime/(torch); contaminaria o venv stdlib-only do repo (I7) | Instalar no venv principal |
| Dois formatos de decodificação | A pré-compressão escolhe o motor em runtime conforme `headroom-ai` esteja ou não instalado; ambos aparecem em produção | Suportar só o motor real — quebraria projetos comprimidos pelo fallback |
| `importlib` para ler `context_budget.py` | `src/modules/...` não é pacote importável e não há `__init__.py` na cadeia | Duplicar o dict — é exatamente o bug que IV1 previne |
| Fallback wheel-PyPI no setup | Build do fork exige Rust, ausente na máquina alvo | Exigir Rust de todo desenvolvedor |

## 10. Test Strategy

**Automatizado** — `tests/tools/test_headroom_context.py`, 22 testes, roda com o
Python do repo (não exige o venv da tool):

- decodificação [A]: tipos, CSV RFC 4180 (vírgula/aspas/newline), nullable, `json`,
  recusa de não-tabular, célula fora do tipo preservada
- decodificação [B]: `factored_array`, `decode_report` sinalizando `rows_dropped`
- propriedades: recursão, idempotência, passthrough
- IV1: fatia vem de `context_budget`, guarda contra `AGENT_ARTIFACT_MAP`
- config: defaults, override por env, env malformada, merge recursivo,
  `ANTHROPIC_TARGET_API_URL` (e ausência de `HEADROOM_UPSTREAM`)
- IV3: decodificação independe do motor; projeto inexistente devolve vazio
- métricas: caminho e formato da linha

**Regressão** — `pytest tests/utils/` (28 testes) cobre `sql_ir_generator`, o
consumidor de maior risco.

**Validação empírica** — roundtrip `compress()` → `decode_headroom()` com 520
linhas contra o motor real. É a única forma de garantir que o formato tabular,
que não é documentado publicamente, está sendo revertido corretamente. **Repetir
após todo `git subtree pull`.**

**Manual** — `quickstart.md`, 10 passos, do mais barato ao mais caro, incluindo o
teste de degradação (derrubar o proxy e confirmar que a sessão ainda inicia).
