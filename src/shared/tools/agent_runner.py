#!/usr/bin/env python3
"""
AVA Fabric — Agent Runner (process-per-agent)
==============================================
Executa os agentes de uma fase como **processos isolados** do GitHub Copilot CLI,
um ``copilot -p`` por agente, cada um com janela de contexto nova.

Substitui o dispatch *in-prompt* (``DISPATCH @agent-id`` + ``AWAIT "↳ ✅"``) que hoje
faz 103 agentes compartilharem uma única janela de 128.000 tokens — causa raiz da
ISSUE-002 (761.376 tokens de payload, chamadas de 62 min, 8 de 19 artefatos F1 nunca
gerados).

O orquestrador de fase continua sendo quem invoca; ele só passa a invocar via::

    Bash: python src/shared/tools/agent_runner.py --project P --phase F1

Fatos de runtime que este código assume (medidos no M0 — ver
``docs/copilot-cli-runtime-facts.md``, Copilot CLI 1.0.77):

===============================  ==========================================
Janela de contexto               128.000 (não 200.000)
Overhead estático (baseline)     29.871 tokens
Overhead com as flags daqui      13.449 tokens  (−55%)
Orçamento útil por processo      ~106.000 tokens
``tools:`` no .agent.md          enforçado de verdade
``version:``/``allowed-tools:``  descartados pelo parser
Tool de shell                    ``powershell`` (não ``bash``)
Exit code                        0 = sucesso · 1 = erro de argumento
===============================  ==========================================

Uso
---
    python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --dry-run
    python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --agent ava-asis-inventory
    python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --wave wave2

Exit codes
----------
    0 — todos os nós completos (ou pulados por artefato já presente)
    1 — ao menos um nó falhou
    2 — erro de configuração (DAG inválido, projeto inexistente, BYOK ausente)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Força UTF-8 no Windows (padrão do repo)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
DAG_DIR = REPO_ROOT / "src" / "shared" / "data" / "pipeline-dag"
ASIS_UTILS = REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "asis-diagnostic" / "utils"

sys.path.insert(0, str(ASIS_UTILS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERRO: pyyaml é obrigatório (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2)

import agent_registry  # noqa: E402
import artifact_gate  # noqa: E402
import context_budget  # noqa: E402
import dependency_graph  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes de runtime — TODAS medidas no M0, não estimadas.
# ---------------------------------------------------------------------------
CONTEXT_WINDOW = 128_000          # events.jsonl: 75/75 ocorrências de tokenLimit
#: Medido em 2026-08-03, DEPOIS de os 102 wrappers passarem a existir.
#: O número do M0 (13.449) foi levantado quando havia 1 agente customizado e ficou
#: obsoleto: o catálogo de agentes entra em `toolDefinitionsTokens` via a tool
#: `task`, e com 102 agentes isso passou de 8.074 para 18.920 (+10.846) — mais que
#: anulando a economia das flags. Excluir `task` devolve o ganho: o nó folha do DAG
#: não delega para ninguém, então a tool é peso morto num processo isolado.
#:
#:   sonda                                            system  toolDefs   total
#:   .bat interativo (102 agentes + AGENTS.md)        23.709    18.920  42.629
#:   + --excluded-tools=task                          22.820     6.526  29.346
#:   flags do runner sem excluir task                  6.042    18.175  24.217
#:   flags do runner + --excluded-tools=skill,task     5.157     5.781  10.938  ← esta
STATIC_OVERHEAD = 10_938
OUTPUT_RESERVE = 8_000

#: Espera antes de RE-verificar o gate, e **so** quando ele deu incompleto depois
#: da execucao. Zero desativa. Existe porque uma sessao do Copilot CLI sugeriu
#: "aguarde 1 turno antes de validar arquivos"; a apuracao nao encontrou nenhum
#: incidente do repo atribuivel a latencia de escrita (o unico falso negativo
#: documentado, ISSUE-003 §6.1, era path errado). Em vez de um sleep cego em todo
#: no, paga-se so no caminho que ja ia falhar — e conta-se quantas vezes resgatou,
#: para decidir com dado se o fenomeno existe.
RECHECK_MS = int(os.environ.get("AVA_GATE_RECHECK_MS", "1500"))
USABLE_CONTEXT = CONTEXT_WINDOW - STATIC_OVERHEAD - OUTPUT_RESERVE   # ~109.062
MIN_AI_CREDITS = 30               # piso imposto pelo CLI: valores menores viram exit 1

# BYOK — mesmos valores de copilot-cli-headroom.bat L24-25
FOUNDRY_ENDPOINT = "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
WIRE_MODEL = "claude-sonnet-4-6"
PROVIDER_MODEL_ID = "claude-sonnet-4"

# Read/Write/Edit/... (frontmatter das specs) -> nomes reais das tools do CLI (M0 §5)
TOOL_NAME_MAP = {
    "Read": "view",
    "Write": "create",
    "Edit": "edit",
    "Glob": "glob",
    "Grep": "grep",
    "Bash": "powershell",
    "WebFetch": "web_fetch",
    "WebSearch": "web_search",
}

# Ruído presente em toda execução, sem impacto funcional (M0 §8).
BENIGN_LOG_PATTERNS = (
    "Request to Copilot Task API failed",
    "GitHub MCP server configured after authentication",
    "could not load remote agents",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str = "", indent: int = 0) -> None:
    print(("  " * indent) + msg, flush=True)


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------
def load_dag(phase: str) -> dict[str, Any]:
    path = DAG_DIR / f"{phase}.yaml"
    if not path.is_file():
        raise SystemExit(f"ERRO: DAG não encontrado: {path.relative_to(REPO_ROOT)}")
    with path.open(encoding="utf-8") as fh:
        dag = yaml.safe_load(fh) or {}
    if dag.get("phase") != phase:
        raise SystemExit(f"ERRO: {path.name} declara phase={dag.get('phase')!r}, esperado {phase!r}")
    return dag


def validate_dag(dag: dict[str, Any], project: str) -> list[str]:
    """
    Mitigação do R1: o DAG não pode virar um quarto espelho manual divergente.

    Todo `id` implementado precisa existir em artifact_gate.ARTIFACT_CONTRACTS
    (o contrato de artefatos) e em agent_registry.catalog() (a spec real).
    Divergência é erro, não warning.
    """
    problems: list[str] = []
    known_agents = {e["agent"] for e in agent_registry.catalog()}
    contracts = set(artifact_gate.ARTIFACT_CONTRACTS)
    phase = str(dag.get("phase") or "")

    try:
        dependency_graph.analyze(dag.get("waves") or [], id_field="id")
    except dependency_graph.DependencyGraphError as exc:
        problems.append(f"waves: {exc}")

    for wave in dag.get("waves", []):
        if not wave.get("implemented", False):
            continue
        for node in wave.get("agents", []):
            aid = resolve_agent_id(node["id"], project)
            if aid is None:
                problems.append(f"{node['id']}: não foi possível resolver (legacy_technology ausente?)")
                continue
            if phase == "F1" and aid not in contracts:
                problems.append(f"{aid}: ausente em artifact_gate.ARTIFACT_CONTRACTS")
            if aid not in known_agents:
                problems.append(f"{aid}: ausente em agent_registry.catalog()")
            if not node.get("slice") and not node.get("inputs"):
                problems.append(f"{aid}: sem `slice` nem `inputs` declarado no DAG")
        for tool in wave.get("tools") or []:
            if not tool.get("id") or not isinstance(tool.get("command"), list) \
                    or not tool.get("command"):
                problems.append(f"{wave.get('id')}: tool inválida: {tool!r}")
    return problems


def resolve_agent_id(raw_id: str, project: str) -> str | None:
    """Resolve `ava-asis-solution-{legacy_technology}` usando o project-config."""
    if "{legacy_technology}" not in raw_id:
        return raw_id
    return artifact_gate.resolve_solution_agent(project)


# ---------------------------------------------------------------------------
# Ambiente BYOK
# ---------------------------------------------------------------------------
def build_child_env(via_proxy: bool) -> tuple[dict[str, str], str]:
    """
    Porta o bloco BYOK de copilot-cli-headroom.bat L73-83.

    Devolve (env, rota). NUNCA degrada em silêncio — hoje o .bat cai para o endpoint
    direto com um aviso que se perde no scroll, e a fase inteira roda sem compressão.
    """
    key_file = REPO_ROOT / ".copilot-key"
    if not key_file.is_file():
        raise SystemExit(f"ERRO: .copilot-key não encontrado em {key_file}")
    api_key = key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise SystemExit("ERRO: .copilot-key está vazio")

    base_url, route = FOUNDRY_ENDPOINT, "direct"
    if via_proxy:
        proxy_url = _proxy_url()
        if proxy_url and _proxy_alive():
            base_url, route = proxy_url, "proxy"
        else:
            raise SystemExit(
                "ERRO: --via-proxy pedido mas o proxy Headroom não respondeu.\n"
                "      Suba com: python src/shared/tools/headroom/headroom_tool.py proxy start\n"
                "      Ou rode sem --via-proxy (rota direta, sem compressão)."
            )

    env = dict(os.environ)
    env.update({
        "COPILOT_PROVIDER_TYPE": "anthropic",
        "COPILOT_PROVIDER_BASE_URL": base_url,
        "COPILOT_PROVIDER_BEARER_TOKEN": api_key,
        "COPILOT_PROVIDER_MODEL_ID": PROVIDER_MODEL_ID,
        "COPILOT_PROVIDER_WIRE_MODEL": WIRE_MODEL,
        "COPILOT_PROVIDER_HEADERS": "anthropic-version: 2023-06-01",
        "ANTHROPIC_TARGET_API_URL": FOUNDRY_ENDPOINT,
    })
    return env, route


def _proxy_url() -> str | None:
    cfg = REPO_ROOT / "src" / "shared" / "tools" / "headroom" / "headroom_config.py"
    if not cfg.is_file():
        return None
    try:
        out = subprocess.run([sys.executable, str(cfg), "--proxy-url"],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or None
    except Exception:
        return None


def _proxy_alive() -> bool:
    tool = REPO_ROOT / "src" / "shared" / "tools" / "headroom" / "headroom_tool.py"
    if not tool.is_file():
        return False
    try:
        return subprocess.run([sys.executable, str(tool), "proxy", "status"],
                              capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Envelope do prompt
# ---------------------------------------------------------------------------
def build_envelope(agent_id: str, project: str, spec_path: Path, node: dict[str, Any],
                   gate: dict[str, Any], cfg: dict[str, Any],
                   compressed_dir: Path | None) -> str:
    missing = ", ".join(m["path"] for m in gate.get("missing", [])) or "(nenhum)"
    lang = str(cfg.get("legacy_technology") or "").strip() or "?"

    if node.get("inputs"):
        input_lines = []
        for tier in ("mandatory", "advisory"):
            for item in node["inputs"].get(tier) or []:
                path = item.get("path") if isinstance(item, dict) else item
                input_lines.append(f"     - [{tier}] {path}")
        return f"""Execute o agente `{agent_id}` para o projeto `{project}`.

1. Read `{spec_path.as_posix()}` e siga LITERALMENTE os Execution Steps.

2. Escopo deste despacho:
     feature          = {node.get('feature') or '(unica)'}
     project_name     = {project}
     trace_id         = {cfg.get('trace_id') or '(vazio)'}

3. Leia somente os insumos declarados para este despacho:
{chr(10).join(input_lines)}

4. Artefatos que faltam no output contract:
     {missing}

5. Nao execute `pipeline_observer.py track`; o runner registra este processo.

6. `project-config.yaml -> overrides` vence qualquer default. Nunca escreva fora do projeto.
"""

    slice_names = node.get("slice") or []
    if slice_names == "all":
        slice_block = "TODOS os artefatos AST (LARGE ARTIFACT PROTOCOL obrigatorio)"
    elif compressed_dir is not None:
        rel = compressed_dir.relative_to(REPO_ROOT).as_posix()
        slice_block = "\n".join(f"     - {rel}/{n}.json" for n in slice_names)
    else:
        slice_block = "     (extracao AST ausente — degrade e reporte, nao invente numeros)"

    return f"""Execute o agente `{agent_id}` para o projeto `{project}`.

1. Read `{spec_path.as_posix()}` e siga LITERALMENTE os Execution Steps. Nao improvise.

2. Sua fatia AST — leia APENAS estes arquivos:
{slice_block}
   NAO leia nenhum outro arquivo sob outputs/asis/ast-raw/. Para artefatos >= 200 KB use
   extracao seletiva via powershell/python, nunca `view` no arquivo inteiro.

3. Variaveis:
     project_name    = {project}
     legacy_technology = {lang}
     trace_id        = {cfg.get('trace_id') or '(vazio)'}
     scope_modules   = {cfg.get('scope_modules') or 'all'}

4. Artefatos que faltam (do artifact_gate — grave EXATAMENTE estes):
     {missing}

5. NAO execute blocos `pipeline_observer.py ... track`. O runner ja registra a
   observabilidade deste processo. Pular esse passo e o comportamento correto.

6. Grave TODO o output contract em UMA UNICA chamada de shell, conforme
   `src/modules/ava-fabric-agents/asis-diagnostic/shared/batch-write-protocol.md`.

REGRAS DE INTEGRIDADE (nao negociaveis):
   - Nunca escreva em outputs/ fora do batch do passo 6.
   - Leia a spec inteira antes de agir.
   - `project-config.yaml -> overrides` vence qualquer default do agente.
"""


# ---------------------------------------------------------------------------
# events.jsonl
# ---------------------------------------------------------------------------
def session_events_path(session_id: str) -> Path:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / ".copilot" / "session-state" / session_id / "events.jsonl"


def read_session_facts(session_id: str) -> dict[str, Any]:
    """
    Fonte de verdade da execução — NÃO parsear stdout.
    O runner escolhe o --session-id, então este caminho é determinístico.
    """
    path = session_events_path(session_id)
    facts: dict[str, Any] = {"events_found": path.is_file(), "events_path": str(path),
                             "context_overflow": False, "tool_failures": [],
                             "subagents": []}
    if not path.is_file():
        return facts

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype, data = ev.get("type"), ev.get("data") or {}

        if etype == "session.start":
            facts["context_tier"] = data.get("contextTier")
        elif etype in ("session.compaction_start", "session.truncation"):
            # Assinatura exata da ISSUE-002: o nó estourou a janela mesmo que "passe".
            facts["context_overflow"] = True
            facts["token_limit"] = data.get("tokenLimit", facts.get("token_limit"))
        elif etype == "session.warning":
            facts["warning"] = data.get("warningType")
        elif etype == "session.error":
            facts["error_type"] = data.get("errorType")
            facts["error_message"] = data.get("message")
            facts["status_code"] = data.get("statusCode")
        elif etype == "session.task_complete":
            facts["summary"] = data.get("summary")
        elif etype == "session.shutdown":
            facts["system_tokens"] = data.get("systemTokens")
            facts["tool_definition_tokens"] = data.get("toolDefinitionsTokens")
            facts["current_tokens"] = data.get("currentTokens")
            facts["api_duration_ms"] = data.get("totalApiDurationMs")
            facts["files_modified"] = (data.get("codeChanges") or {}).get("filesModified", [])
            for model, m in (data.get("modelMetrics") or {}).items():
                usage = m.get("usage") or {}
                facts["used_model"] = model
                facts["tokens_in"] = usage.get("inputTokens", 0)
                facts["tokens_out"] = usage.get("outputTokens", 0)
        elif etype == "subagent.started":
            # Nao deveria acontecer: o runner roda com `--excluded-tools=skill,task`,
            # entao o no folha nao tem como abrir subagente. Se aparecer, e sinal de
            # que a flag caiu — e ai vale a pena saber, porque `general-purpose` e
            # `explore` trazem modelo proprio e sob BYOK falham 100% das vezes
            # (54/54 e 19/24 nas 56 sessoes medidas).
            facts["subagents"].append({
                "agent": data.get("agentName"),
                "model": data.get("model"),
                "tool_calls": None,
            })
        elif etype in ("subagent.completed", "subagent.failed"):
            # SEM default em totalToolCalls: ausente e DESCONHECIDO, nunca zero.
            for entry in reversed(facts["subagents"]):
                if entry["agent"] == data.get("agentName") and entry["tool_calls"] is None:
                    entry["tool_calls"] = data.get("totalToolCalls")
                    break
        elif etype == "tool.execution_complete" and data.get("success") is False:
            facts["tool_failures"].append({
                "tool": data.get("toolName"),
                "error": (data.get("error") or {}).get("message"),
            })
    return facts


def subagent_problems(facts: dict[str, Any], expected_model: str) -> list[str]:
    """Subagentes fora do modelo BYOK ou que nao fizeram nenhuma tool call.

    Ambos os casos sao **configuracao**, nao transporte: retentar nao ajuda. A
    sequencia medida em 56 sessoes e sempre a mesma — `subagent.started` com
    `model=gpt-5.4`, `session.error` 404 do wire model, `subagent.completed` com
    `totalToolCalls=0`. O subagente morre antes da primeira ferramenta e o
    orquestrador segue como se tivesse recebido resultado.
    """
    problems: list[str] = []
    for entry in facts.get("subagents") or []:
        model = entry.get("model")
        if model and model != expected_model:
            problems.append(
                f"subagente '{entry.get('agent')}' rodou em '{model}' "
                f"(esperado '{expected_model}') — fora do provider BYOK"
            )
        elif entry.get("tool_calls") == 0:
            problems.append(
                f"subagente '{entry.get('agent')}' terminou com 0 tool calls — nao produziu nada"
            )
    return problems


# ---------------------------------------------------------------------------
# Execução de um nó
# ---------------------------------------------------------------------------
def build_argv(agent_id: str, envelope: str, node: dict[str, Any], defaults: dict[str, Any],
               run_dir: Path, session_id: str, extra_dirs: list[str]) -> list[str]:
    """
    argv como LISTA (shell=False). O envelope tem quebras de linha, crases e chaves —
    montar string de comando quebraria o parse.
    """
    argv = [
        "copilot",
        "-p", envelope,
        "--agent", agent_id,
        "-C", str(REPO_ROOT),          # repo root, NAO o dir do projeto: as specs usam paths repo-relativos
        "--model", node.get("model") or defaults.get("model") or PROVIDER_MODEL_ID,
        "--allow-all-tools",
        "--no-ask-user",
        # M0: -11.372 tokens. As Output Integrity Rules foram para o envelope e o wrapper.
        "--no-custom-instructions",
        "--disable-builtin-mcps",      # M0: -619
        # skill: -4.400 — o agente recebe a spec por `view`, nao precisa da tool.
        # task:  -12.394 — carrega o catalogo dos 102 agentes customizados nas
        #        toolDefinitions. Um no folha do DAG nao delega para ninguem; num
        #        processo isolado isso e peso morto. Medido 2026-08-03.
        # Se algum dia um no PRECISAR delegar nativamente, o DAG tera de permitir
        # sobrescrever esta flag por no — hoje nenhum precisa.
        "--excluded-tools=skill,task",
        "--output-format", "json",
        "--session-id", session_id,
        "--log-level", "error",
        "--log-dir", str(run_dir / "logs" / agent_id),
        "--share", str(run_dir / "transcripts" / f"{agent_id}.md"),
        "--secret-env-vars=COPILOT_PROVIDER_BEARER_TOKEN",
        "--no-auto-update",
        "--no-remote", "--no-remote-export",
    ]
    for d in extra_dirs:
        argv += ["--add-dir", d]
    credits = node.get("max_ai_credits")
    if credits:
        # O CLI recusa valores < 30 ("Use at least 30 AI credits") e mata o nó com exit 1
        # antes de qualquer inferência. Clampar aqui evita que um valor errado no DAG
        # derrube a wave inteira.
        argv += ["--max-ai-credits", str(max(MIN_AI_CREDITS, int(credits)))]
    return argv


def redact(argv: list[str]) -> str:
    """Render legível para --dry-run, com o envelope colapsado."""
    parts = []
    for a in argv:
        if "\n" in a:
            parts.append(f'"<envelope {len(a)} chars>"')
        elif " " in a:
            parts.append(f'"{a}"')
        else:
            parts.append(a)
    return " ".join(parts)


def run_node(agent_id: str, node: dict[str, Any], dag: dict[str, Any], project: str,
             env: dict[str, str], run_dir: Path, cfg: dict[str, Any],
             compressed_dir: Path | None, budget: dict[str, Any],
             dry_run: bool) -> dict[str, Any]:
    defaults = dag.get("defaults") or {}
    entry = agent_registry.get(agent_id) or {}
    spec_path = REPO_ROOT / entry.get("path", "")

    # ---- 1. Gate (pré-dispatch) -------------------------------------------
    gate = _node_gate(project, agent_id, node)
    if gate.get("complete"):
        log(f"⏭  SKIP — artefatos já presentes ({len(gate.get('present', []))})", 1)
        # O skip também é telemetria: sem ele o relatório de fase mostra um buraco
        # onde na verdade houve reaproveitamento.
        if not dry_run:
            _track(project, agent_id, entry, "skipped", {}, 0, _now_iso(), "artifacts_present")
        return {"agent": agent_id, "status": "skipped", "detail": "artifacts_present"}

    # ---- 2. Budget ---------------------------------------------------------
    slice_info = (budget.get("agents") or {}).get(agent_id, {})
    slice_tokens = slice_info.get("tokens", 0)
    if slice_tokens > USABLE_CONTEXT:
        log(f"⚠  fatia de {slice_tokens:,} tokens > {USABLE_CONTEXT:,} úteis — "
            f"risco de compaction (context pack chega no M3)", 1)

    # ---- 3. Envelope -------------------------------------------------------
    envelope = build_envelope(agent_id, project, spec_path, node, gate, cfg, compressed_dir)

    extra_dirs: list[str] = []
    repo_path = str(cfg.get("repository_path") or "").strip()
    if repo_path and not Path(repo_path).is_relative_to(REPO_ROOT):
        extra_dirs.append(repo_path)

    session_id = str(uuid.uuid4())
    argv = build_argv(agent_id, envelope, node, defaults, run_dir, session_id, extra_dirs)

    if dry_run:
        log(f"envelope: {len(envelope)} chars | fatia: {slice_tokens:,} tokens "
            f"| faltam {len(gate.get('missing', []))} artefatos", 1)
        log(f"$ {redact(argv)}", 1)
        return {"agent": agent_id, "status": "dry_run", "envelope_chars": len(envelope),
                "slice_tokens": slice_tokens}

    # ---- 4. Spawn ----------------------------------------------------------
    (run_dir / "logs" / agent_id).mkdir(parents=True, exist_ok=True)
    (run_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    timeout_s = node.get("timeout_s") or defaults.get("timeout_s") or 900
    start = time.monotonic()
    start_iso = _now_iso()

    proc = subprocess.Popen(argv, env=env, cwd=str(REPO_ROOT), shell=False,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    timed_out = False
    try:
        stdout, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc.pid)
        stdout, _ = proc.communicate()
    duration_ms = int((time.monotonic() - start) * 1000)

    (run_dir / "logs" / agent_id / "stdout.jsonl").write_text(stdout or "", encoding="utf-8")

    # ---- 5. Verificação — artefato é a autoridade --------------------------
    facts = read_session_facts(session_id)
    gate_after = _node_gate(project, agent_id, node)

    # Re-check APENAS no caminho negativo. O gate de skip (passo 1) nunca re-checa:
    # ali "incompleto" e o estado normal (o artefato ainda nao foi produzido), e
    # re-checar atrasaria todo no. Aqui "incompleto" significa falha, entao uma
    # segunda leitura custa pouco e so paga quem ja ia falhar.
    # O contador existe para responder, com dado, se a latencia de escrita e real
    # neste ambiente — hoje e hipotese nao verificada.
    rescued = False
    if not gate_after.get("complete") and RECHECK_MS > 0:
        time.sleep(RECHECK_MS / 1000.0)
        segunda = _node_gate(project, agent_id, node)
        if segunda.get("complete"):
            rescued = True
            gate_after = segunda
            log(f"↻  artefatos confirmados no 2º check (+{RECHECK_MS}ms) — "
                f"latencia de escrita real", 1)

    expected_model = node.get("model") or defaults.get("model") or PROVIDER_MODEL_ID
    status, detail = _classify(proc.returncode, timed_out, facts, gate_after, expected_model)

    # ---- 6. Telemetria -----------------------------------------------------
    _track(project, agent_id, entry, status, facts, duration_ms, start_iso, detail)

    result = {
        "agent": agent_id, "status": status, "detail": detail,
        "exit_code": proc.returncode, "timed_out": timed_out,
        "gate_rescued_on_recheck": rescued,
        "subagents": facts.get("subagents") or [],
        "duration_ms": duration_ms, "session_id": session_id,
        "tokens_in": facts.get("tokens_in"), "tokens_out": facts.get("tokens_out"),
        "context_overflow": facts.get("context_overflow"),
        "artifacts_missing": [m["path"] for m in gate_after.get("missing", [])],
        "events_path": facts.get("events_path"),
    }
    _render_node_result(result, facts)
    return result


def _node_gate(project: str, agent_id: str, node: dict[str, Any]) -> dict[str, Any]:
    gate = artifact_gate.check_agent(project, agent_id)
    if gate.get("status") != "no_contract" or not node.get("declared_outputs"):
        return gate
    base = REPO_ROOT / "projects" / project / str(node.get("output_base") or "")
    present, missing = [], []
    for relative in node["declared_outputs"]:
        target = base / str(relative)
        item = {"path": str(target.relative_to(REPO_ROOT)), "advisory": False}
        if target.is_file() and target.stat().st_size > 0:
            present.append(item["path"])
        else:
            item["reason"] = "arquivo ausente ou vazio"
            missing.append(item)
    return {
        "agent": agent_id,
        "status": "complete" if not missing else "incomplete",
        "complete": not missing,
        "should_dispatch": bool(missing),
        "present": present,
        "missing": missing,
    }


def _classify(exit_code: int, timed_out: bool, facts: dict[str, Any],
              gate_after: dict[str, Any],
              expected_model: str = PROVIDER_MODEL_ID) -> tuple[str, str]:
    if timed_out:
        return "failed", "timeout"
    # 404 de modelo = falha de CONFIGURAÇÃO. Não adianta retentar (R4).
    if facts.get("status_code") == 404 and "not found on provider" in (facts.get("error_message") or ""):
        return "config_error", f"modelo não encontrado no provider: {facts.get('error_message')}"
    # Subagente fora do BYOK ou sem nenhuma tool call — também é configuração.
    # Vem ANTES do gate de artefato de propósito: se um subagente morreu, o
    # artefato ausente é consequência, e reportar a causa vale mais que o sintoma.
    problemas = subagent_problems(facts, expected_model)
    if problemas:
        return "config_error", "; ".join(problemas[:3])
    if facts.get("error_message"):
        return "failed", f"[{facts.get('status_code')}] {facts.get('error_message')}"
    if not gate_after.get("complete"):
        n = len(gate_after.get("missing", []))
        return "failed", f"{n} artefato(s) do output contract ausente(s) após execução"
    if exit_code != 0:
        return "failed", f"exit code {exit_code}"
    return "completed", "artifacts_confirmed"


def _kill_tree(pid: int) -> None:
    """Popen.terminate() deixa o filho `node` órfão no Windows (R10).

    Delega para `proc_stream`, que é a implementação única de execução e
    encerramento de processo da esteira — manter duas cópias era como o
    caminho de tool ficou sem kill de árvore nenhum.
    """
    import proc_stream  # noqa: PLC0415
    proc_stream.kill_process_tree(pid)


def ensure_observer_run(project: str, phase: str, dry_run: bool) -> None:
    """
    ``pipeline_observer track`` recusa gravar sem um run ativo ("No active run.
    Call 'init' first."). No fluxo interativo quem chamava ``init`` era o
    orquestrador; com o runner, é ele. Idempotente: se já houver run ativo,
    o init falha e nós ignoramos.
    """
    if dry_run:
        return
    observer = REPO_ROOT / "src" / "shared" / "tools" / "pipeline_observer.py"
    try:
        subprocess.run(
            [sys.executable, str(observer), "-p", project, "init",
             "--run-type", f"agent_runner:{phase}", "--model", WIRE_MODEL],
            cwd=str(REPO_ROOT), capture_output=True, timeout=120, check=False)
    except Exception as exc:  # noqa: BLE001
        log(f"⚠  não foi possível inicializar a observabilidade: {exc}")


def _track(project: str, agent_id: str, entry: dict[str, Any], status: str,
           facts: dict[str, Any], duration_ms: int, start_iso: str, detail: str) -> None:
    """Registra a observabilidade que hoje cada agente emite à mão em 206 lugares."""
    observer = REPO_ROOT / "src" / "shared" / "tools" / "pipeline_observer.py"
    argv = [
        sys.executable, str(observer), "-p", project, "track",
        "--agent", agent_id,
        "--phase", entry.get("phase") or "F1",
        "--version", entry.get("version") or "0.0.0",
        "--status", "completed" if status == "completed" else ("skipped" if status == "skipped" else "failed"),
        "--tokens-in", str(facts.get("tokens_in") or 0),
        "--tokens-out", str(facts.get("tokens_out") or 0),
        "--duration-ms", str(duration_ms),
        "--start-time", start_iso,
        "--end-time", _now_iso(),
        "--model", facts.get("used_model") or WIRE_MODEL,
    ]
    if status != "completed":
        argv += ["--error-detail", detail[:500]]
    try:
        out = subprocess.run(argv, cwd=str(REPO_ROOT), capture_output=True,
                             text=True, timeout=120, check=False)
        # Não engolir: foi exatamente assim que o track falhou em silêncio na
        # primeira execução do M1 ("No active run") e o agent-events.jsonl ficou vazio.
        if out.returncode != 0:
            log(f"⚠  telemetria NÃO gravada (exit {out.returncode}): "
                f"{(out.stdout or out.stderr or '').strip()[:200]}", 1)
    except Exception as exc:  # noqa: BLE001 — telemetria nunca derruba a execução
        log(f"⚠  falha ao registrar telemetria: {exc}", 1)


def _render_node_result(r: dict[str, Any], facts: dict[str, Any]) -> None:
    icon = {"completed": "✅", "skipped": "⏭", "failed": "❌", "config_error": "⛔"}.get(r["status"], "•")
    log(f"{icon} {r['status']} — {r['detail']}", 1)
    log(f"exit={r['exit_code']} dur={r['duration_ms']}ms "
        f"tokens={r.get('tokens_in') or 0}→{r.get('tokens_out') or 0} "
        f"static={facts.get('system_tokens') or '?'}+{facts.get('tool_definition_tokens') or '?'}", 1)
    if r.get("context_overflow"):
        log("⚠  CONTEXT OVERFLOW (compaction/truncation) — assinatura da ISSUE-002", 1)
    if r.get("artifacts_missing"):
        log(f"faltando: {', '.join(r['artifacts_missing'])}", 1)
    for tf in facts.get("tool_failures", [])[-3:]:
        log(f"tool falhou: {tf['tool']} — {tf['error']}", 1)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Executa os agentes de uma fase como processos isolados.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--phase", required=True, help="F1..F8")
    ap.add_argument("--wave", default=None, help="Executa só esta wave")
    ap.add_argument("--agent", default=None, help="Executa só este agente")
    ap.add_argument("--feature", default=None, help="Executa só esta feature do fan-out")
    ap.add_argument("--dry-run", action="store_true", help="Imprime os comandos, sem inferência")
    ap.add_argument("--via-proxy", action="store_true",
                    help="Roteia pelo proxy Headroom. M0: 71 dos 87 erros 404 vieram dessa rota "
                         "(falta o shim de /v1/models/{id}). Default é rota direta.")
    ap.add_argument("--json", action="store_true", help="Emite o resultado em JSON")
    args = ap.parse_args()

    project_dir = REPO_ROOT / "projects" / args.project
    if not project_dir.is_dir():
        print(f"ERRO: projeto não encontrado: {project_dir.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 2

    dag = load_dag(args.phase)
    problems = validate_dag(dag, args.project)
    if problems:
        print("ERRO: DAG incoerente com as fontes de verdade existentes (R1):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2

    cfg = context_budget.load_project_config(args.project)
    lang = str(cfg.get("legacy_technology") or "").strip().lower() or None
    compressed_dir = context_budget.resolve_compressed_dir(args.project, lang)
    budget = context_budget.build_budget(args.project, language=lang)

    env, route = ({}, "dry-run") if args.dry_run else build_child_env(args.via_proxy)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = project_dir / "outputs" / ".runs" / run_id

    log("─" * 78)
    log(f"🏃 Agent Runner — {args.project} · {args.phase}" + (" · DRY RUN" if args.dry_run else ""))
    log("─" * 78)
    log(f"orquestrador : {dag.get('orchestrator')}")
    log(f"rota         : {route}" + ("  (sem compressão Headroom)" if route == "direct" else ""))
    log(f"budget AST   : {budget.get('status')}"
        + (f" · {budget.get('total_tokens', 0):,} tokens · modo {budget.get('execution_mode')}"
           if budget.get("status") == "ok" else f" · {budget.get('detail', '')[:80]}"))
    log(f"janela útil  : {USABLE_CONTEXT:,} tokens ({CONTEXT_WINDOW:,} − {STATIC_OVERHEAD:,} estáticos "
        f"− {OUTPUT_RESERVE:,} de saída)")
    log(f"run_dir      : {run_dir.relative_to(REPO_ROOT)}")

    ensure_observer_run(args.project, args.phase, args.dry_run)

    if args.phase != "F1":
        import pipeline_plan  # noqa: PLC0415
        flattened = pipeline_plan.dag_steps(args.phase, REPO_ROOT, project=args.project)
        synthetic_waves = []
        previous = None
        for index, item in enumerate(flattened, 1):
            wave_id = f"step-{index:03d}"
            wave: dict[str, Any] = {
                "id": wave_id,
                "source_wave": item.get("wave", ""),
                "depends_on": [previous] if previous else [],
                "implemented": True,
            }
            if item.get("kind") == "tool":
                wave["tools"] = [{"id": item["agent"], "command": item["command"]}]
            else:
                wave["agents"] = [{
                    "id": item["agent"], "inputs": item.get("inputs") or {},
                    "feature": item.get("feature", ""),
                    "declared_outputs": item.get("outputs") or [],
                    "output_base": item.get("output_base", ""),
                }]
            synthetic_waves.append(wave)
            previous = wave_id
        dag = {**dag, "waves": synthetic_waves}

    results: list[dict[str, Any]] = []
    wave_plan = dependency_graph.analyze(dag.get("waves") or [], id_field="id")
    waves_by_id = {str(wave["id"]): wave for wave in dag.get("waves", [])}
    for wave_id in wave_plan.order:
        wave = waves_by_id[wave_id]
        wid = wave.get("id")
        source_wave = wave.get("source_wave") or wid
        if args.wave and source_wave != args.wave:
            continue
        if not wave.get("implemented", False):
            log("")
            log(f"⏸  {wid} — não implementada neste milestone; pulando explicitamente.")
            continue

        log("")
        log(f"▶ {wid}")
        for node in wave.get("agents", []):
            aid = resolve_agent_id(node["id"], args.project)
            if args.agent and aid != args.agent:
                continue
            if args.feature and node.get("feature") != args.feature:
                continue
            log("")
            log(f"● {aid}")
            results.append(run_node(aid, node, dag, args.project, env, run_dir,
                                    cfg, compressed_dir, budget, args.dry_run))
        for tool in wave.get("tools") or []:
            tool_id = str(tool["id"])
            if args.agent and tool_id != args.agent:
                continue
            log("")
            log(f"◆ {tool_id} (determinístico)")
            import ava_pipeline  # noqa: PLC0415
            from pipeline_plan import Step  # noqa: PLC0415
            step = Step(
                phase=f"{args.phase}:tool:{tool_id}", group=args.phase,
                agent=tool_id, trigger=None, label=tool_id, kind="tool",
                command=[str(part) for part in tool["command"]], wave=str(wid),
                on_fail=str(tool.get("on_fail") or ""),
                # O teto viaja no Step, como em qualquer outro caminho de tool;
                # `run_tool_step` resolve nó → defaults → default global.
                timeout_s=(tool.get("timeout_s")
                           or dag.get("defaults", {}).get("timeout_s")),
            )
            if args.dry_run:
                command = ava_pipeline.resolve_tool_command(step, args.project)
                log(f"$ {' '.join(command)}", 1)
                results.append({"agent": tool_id, "status": "dry_run", "kind": "tool"})
            else:
                try:
                    result = ava_pipeline.run_tool_step(step, args.project)
                except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                    log(f"❌ {exc}", 1)
                    results.append({"agent": tool_id, "status": "failed",
                                    "kind": "tool", "detail": str(exc)})
                    break
                results.append({"agent": tool_id, "status": result["status"], "kind": "tool",
                                "exit_code": result["exit_code"]})
        if results and results[-1].get("status") == "failed" \
                and results[-1].get("kind") == "tool":
            break

    log("")
    log("─" * 78)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    log("RESUMO: " + (" · ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nenhum nó executado"))
    log("─" * 78)

    if args.json:
        print(json.dumps({"project": args.project, "phase": args.phase, "run_id": run_id,
                          "route": route, "results": results}, ensure_ascii=False, indent=2))

    if not results:
        return 2
    return 1 if any(r["status"] in ("failed", "config_error") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
