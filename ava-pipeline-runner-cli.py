"""
AVA Fabric Pipeline Runner
Executa os agentes da esteira AVA Fabric em sequência via Foundry (Claude Sonnet 4.6).
Cada passo roda em contexto isolado. Pede permissão antes de cada etapa.

Pré-requisitos:
  - Python 3.11+  (pip install anthropic requests)
  - VPN vnet-core-brs-001 conectada  (endpoints privados do Foundry IMF)
  - Arquivo .copilot-key na raiz do repositório com a API Key do Foundry

Portabilidade:
  WORKSPACE é auto-detectado a partir da localização deste script.
  Funciona em qualquer máquina/caminho sem edição manual.
"""
import os
import re
import fnmatch
import argparse
import sys
import json
# Aliasado de propósito: `_write_status_html` tem uma variável local chamada
# `html`, o que torna o nome local em todo o corpo da função — um `import html`
# simples levantaria UnboundLocalError justamente onde o escape é necessário.
import html as _html
import msvcrt
import socket
import datetime
import textwrap
import subprocess
import time
import traceback
import requests as _requests
from pathlib import Path
import anthropic

# Opção 1: rich para dashboard no terminal (opcional — fallback para ANSI puro)
try:
    from rich.console import Console as _RichConsole
    from rich.panel import Panel as _RichPanel
    _RICH_CONSOLE = _RichConsole(highlight=False)
    _RICH_OK = True
except ImportError:
    _RICH_OK = False


def safe_input(prompt: str) -> str:
    """Lê uma linha do teclado caractere a caractere via msvcrt.getwch().
    Evita completamente o buffer de linha do stdin do PowerShell,
    garantindo que cada prompt aguarda o usuário digitar antes de retornar.
    Suporta: Enter (\\r/\\n), Backspace, caracteres normais, Ctrl+C.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        return _consumir_linha(msvcrt.getwch())
    except KeyboardInterrupt:
        print()
        raise


def _consumir_linha(primeira: str) -> str:
    """Completa a leitura de uma linha a partir de um caractere já lido.

    Extraído de ``safe_input`` para ser compartilhado com
    ``safe_input_timeout``: o tratamento de Enter, Backspace, Ctrl+C e teclas
    especiais de dois bytes é sutil o bastante para que duas cópias divirjam.
    """
    chars: list[str] = []
    ch = primeira
    while True:
        if ch in ('\r', '\n'):              # Enter — fim da linha
            sys.stdout.write('\n')
            sys.stdout.flush()
            break
        if ch == '\x03':                    # Ctrl+C
            sys.stdout.write('\n')
            sys.stdout.flush()
            raise KeyboardInterrupt
        if ch == '\x08':                    # Backspace
            if chars:
                chars.pop()
                sys.stdout.write('\b \b')
                sys.stdout.flush()
        elif ch in ('\x00', '\xe0'):        # tecla especial (setas, F-keys) — 2 chars
            msvcrt.getwch()                 # descarta o segundo byte
        elif ch >= ' ':                     # caractere imprimível
            chars.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
        ch = msvcrt.getwch()
    return ''.join(chars)


def safe_input_timeout(prompt: str, timeout_s: int) -> "str | None":
    """Como ``safe_input``, mas desiste se ninguém COMEÇAR a digitar a tempo.

    O prazo vale só até a primeira tecla. Quem começou a digitar não pode ter o
    nome cortado no meio por um cronômetro — passado o primeiro caractere, o
    comportamento é idêntico ao de ``safe_input``.

    Existe para o gate de aprovação em modo automático, onde perguntar não pode
    pendurar a esteira: ``safe_input`` bloqueia para sempre, e numa execução
    agendada não há ninguém para responder.

    Devolve ``None`` no estouro ou quando não há console — distinto de ``""``,
    que é alguém apertando Enter sem digitar, ou seja, uma resposta.
    """
    deadline = time.monotonic() + timeout_s
    sufixo = ""
    sys.stdout.write(prompt)
    sys.stdout.flush()

    def _apagar_sufixo() -> None:
        nonlocal sufixo
        if sufixo:
            sys.stdout.write("\b" * len(sufixo) + " " * len(sufixo) + "\b" * len(sufixo))
            sys.stdout.flush()
            sufixo = ""

    try:
        while True:
            if msvcrt.kbhit():
                primeira = msvcrt.getwch()
                _apagar_sufixo()
                return _consumir_linha(primeira)
            restante = int(deadline - time.monotonic()) + 1
            if restante <= 0:
                _apagar_sufixo()
                sys.stdout.write("\n")
                sys.stdout.flush()
                return None
            novo = f"[{restante}s] "
            if novo != sufixo:
                _apagar_sufixo()
                sys.stdout.write(novo)
                sys.stdout.flush()
                sufixo = novo
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
        raise
    except OSError:
        # Sem console alocado (serviço, pipe puro): não há a quem perguntar.
        print()
        return None

# ── DNS patch (private endpoints via VPN) ───────────────────────────────────
# IPs validados por resolução DNS nativa com VPN ativa (2026-08-04):
#   aif-imf-apps-prd-eus2-001.services.ai.azure.com      -> 10.26.2.12
#   aif-imf-apps-prd-eus2-001.openai.azure.com           -> 10.26.2.11
#   aif-imf-premium-models-prd-eus2-001.services.ai.azure.com -> 10.26.2.27
# O endpoint /anthropic resolve nativamente via VPN — DNS patch é fallback
# para ambientes sem DNS privado configurado (ex: laptop sem VPN split-DNS).
_DNS = {
    "aif-imf-agents-prd-eus2-001.services.ai.azure.com":                   "10.26.2.6",
    "aif-imf-agents-prd-eus2-001.privatelink.services.ai.azure.com":       "10.26.2.6",
    "aif-imf-apps-prd-eus2-001.openai.azure.com":                          "10.26.2.11",
    "aif-imf-apps-prd-eus2-001.services.ai.azure.com":                     "10.26.2.12",
    "aif-imf-premium-models-prd-eus2-001.services.ai.azure.com":           "10.26.2.27",  # IP real validado via VPN
    "aif-imf-premium-models-prd-eus2-001.privatelink.services.ai.azure.com": "10.26.2.27",
}
_orig_gai = socket.getaddrinfo
def _patch_gai(host, port, *a, **kw):
    return _orig_gai(_DNS.get(host, host), port, *a, **kw)
socket.getaddrinfo = _patch_gai
# ────────────────────────────────────────────────────────────────────────────

# ── Configuração Foundry ─────────────────────────────────────────────────────
# WORKSPACE é auto-detectado: funciona em qualquer máquina sem edição manual.
# O script detecta sua própria localização e assume que está na raiz do repo.
WORKSPACE         = Path(__file__).resolve().parent
ENDPOINT          = "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"
ENDPOINT_OPENAI   = "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/openai"
OPENAI_API_VERSION = "2024-12-01-preview"
DEPLOYMENT       = "claude-sonnet-4-6"
PROVIDER          = "anthropic"  # "anthropic" | "openai" — atualizado após seleção de modelo
API_KEY_FILE = WORKSPACE / ".copilot-key"  # API Key do Foundry — não commitar
SKILLS_PATH = WORKSPACE / ".github" / "skills"
MAX_TOKENS  = 128_000        # output tokens por passo
TEMPERATURE = 0.0            # temperatura fixa — respostas determinísticas
API_MAX_RETRIES = 3          # retries para erros transitórios de API (api_error vazio, timeout)
API_RETRY_DELAY_S = 5        # delay base entre retries (com jitter interno)
# ── Limites de contexto injetado no system prompt ────────────────────────────
# Validado em 2026-08-05 via test_context_limit.py:
#   Deployment IMF aceita 1,000,000 tokens input (mesma janela do Copilot Chat)
#   Skill maior (orchestrator-asis.md) = 189KB = 47K tokens
#   project-config + shared-context    = 18KB  =  4.5K tokens
#   30 artefatos × 80KB cap            = 2.4MB = 600K tokens disponíveis
#   TOTAL INPUT seguro                 = ~800K tokens (80% da janela de 1M)
CTX_WINDOW  = 1_000_000      # janela real confirmada pelo deployment IMF
CTX_OUT_MAX =   128_000      # limite real de output tokens (claude-sonnet-4-6 no IMF, validado 2026-08-05)
CTX_SKILL   = 2_000_000      # chars máx de skill — sem cap efetivo (skill max=189KB)
CTX_FILE    = 2_000_000      # chars máx por config — sem cap efetivo (config max=18KB)
CTX_ARTS    = 500            # max artefatos listados no índice (apenas nomes)
ART_INJECT_MAX   = 60        # max artefatos com conteúdo injetado (dobrado — 1M permite)
ART_INJECT_CHARS = 80_000    # chars máx por artefato (80KB = 20K tokens cada)

# ── Manifesto de contexto por passo (spec 039, Fase 0) ───────────────────────
# ART_INJECT_MAX acima é uma heurística de ORDEM ALFABÉTICA, e ela nunca alcança
# `outputs/tobe/`. Medido em nopcommerce-02-cli-ava: dos 60 artefatos injetados,
# 60 eram de `asis/` e ZERO de `tobe/` — o gerador de código da F4 rodou sem o
# blueprint, os ADRs, o OpenAPI, as regras de negócio nem o protótipo, e
# `index.html` sequer era elegível (`.html` fora da allowlist de sufixos).
# Passos com a chave `inputs` em PIPELINE usam a allowlist declarada; os demais
# continuam no caminho legado abaixo, sem mudança de comportamento.
sys.path.insert(0, str(WORKSPACE / "src" / "shared" / "tools"))
try:
    import context_manifest as _ctx_manifest
except ImportError:  # degrada, nunca quebra (IV3)
    _ctx_manifest = None

# ── Razão de progresso da F5 (DevOps Execute) ────────────────────────────────
# A F5 deixou de ser um despacho único com todo o contexto do projeto e virou um
# laço iterativo (padrão Ralph Wiggum) sobre
# `outputs/tobe/devops/task-devops-progress.json`: uma chamada por tarefa, com o
# contexto mínimo daquela tarefa. Ver `devops_task_ledger.py`.
try:
    import devops_task_ledger as _devops_ledger
except ImportError:  # degrada, nunca quebra (IV3)
    _devops_ledger = None

# ── Razão de progresso da F6 (QA Execute) ────────────────────────────────────
# Mesmo tratamento da F5, pelo mesmo defeito: a F6 declarava
# `outputs/tobe/source-code` (40.468 arquivos) como conteúdo obrigatório e
# estourou com `prompt is too long: 3958957 tokens`. Agora a fase tem dois
# momentos — planejamento e execução — e itera sobre
# `outputs/tobe/qa/task-qa-progress.json`. Ver `qa_task_ledger.py`.
try:
    import qa_task_ledger as _qa_ledger
except ImportError:  # degrada, nunca quebra (IV3)
    _qa_ledger = None

# ── Razão de progresso da F4 (Tech Stack Code Generation) ────────────────────
# Mesmo padrão da F5/F6, pelo defeito mais caro dos três: a F4 expandia N passos
# ESTÁTICOS no início da fase, cada um com o manifesto global (659 KB medidos em
# `cadastro-funcionarios-04`) e o MESMO prompt — `task_id` e `feature` nunca
# chegavam ao modelo. Agora a fase é um laço que relê
# `outputs/tobe/speckit/tasks-progress.json` a cada volta, roteia a task para o
# coder especializado da stack e monta contexto mínimo por task.
# Ver `f4_loop.py`, `f4_routing.py`, `f4_task_context.py`, `f4_gate.py`.
#
# Ao contrário de F5/F6, aqui a importação **não pode degradar em silêncio**: um
# `except ImportError` que segue em frente devolveria a F4 ao despacho único.
try:
    import f4_loop as _f4_loop
    import f4_routing as _f4_routing
    import f4_agent_result as _f4_contract
    import f4_gate as _f4_gate
except ImportError as _exc_f4:  # o passo F4 falha explicitamente lá embaixo
    _f4_loop = None
    _f4_routing = None
    _f4_contract = None
    _f4_gate = None
    _F4_IMPORT_ERROR = str(_exc_f4)
else:
    _F4_IMPORT_ERROR = ""
# Override de MAX_TOKENS por fase (None = usa MAX_TOKENS global)
PHASE_MAX_TOKENS: dict[str, int] = {
    # Deployment IMF: limite real confirmado = 128.000 output tokens para claude-sonnet-4-6
    # Erro 400 em F3: 'max_tokens: 131072 > 128000' — corrigido 2026-08-05
    "F3S": 128_000,   # SpecKit planning/spec/tasks — reduz risco de respostas prolixas
    "F3":  128_000,  # Prototype HTML — máximo output real do deployment IMF
    "F4":  128_000,  # Stack — código .NET/Angular extenso
    "S1":  128_000,  # Summary — HTML executivo completo
    "S4":  128_000,  # Summary Final
    "S2":  128_000,  # Summary Remediation — output menor
    "S3":  128_000,  # Summary Validate — output menor
}

# ── Headroom proxy ────────────────────────────────────────────────────────────
HEADROOM_TOOL   = WORKSPACE / "src" / "shared" / "tools" / "headroom" / "headroom_tool.py"
HEADROOM_VENV_PY = WORKSPACE / "src" / "shared" / "tools" / "headroom" / ".venv" / "Scripts" / "python.exe"
HEADROOM_EXE    = WORKSPACE / "src" / "shared" / "tools" / "headroom" / ".venv" / "Scripts" / "headroom.exe"
HEADROOM_CFG    = WORKSPACE / "src" / "shared" / "tools" / "headroom" / "headroom_config.py"
HEADROOM_DEFAULT_URL = "http://127.0.0.1:8787"
# ────────────────────────────────────────────────────────────────────────────

# ── Pipeline — sequência de passos ───────────────────────────────────────────
PIPELINE = [
    # F0 — Deterministic AST Extraction (pré-requisito obrigatório dos agentes F1)
    # Executa run_ast_analysis.py via subprocess ANTES de qualquer agente LLM.
    # Não é um agente LLM — é tratado especialmente por run_step() / run_ast_step().
    # Pular (P) não bloqueia: agentes F1 degradam para análise pattern-based.
    {"phase": "F0",  "label": "AST Extraction — Deterministic (run_ast_analysis.py)",
     "agent": "_ast_extractor",         "trigger": None},

    # F1 — Orchestrator
    {"phase": "F1",  "label": "AS-IS Diagnostic — Full Pipeline",
     "agent": "ava-asis-orchestrator",  "trigger": "FP"},

    # F1 — Specialized agents (Wave 1)
    {"phase": "F1a", "label": "AS-IS Inventory",
     "agent": "ava-asis-inventory",     "trigger": None},
    {"phase": "F1b", "label": "AS-IS Architecture & Bounded Contexts",
     "agent": "ava-asis-solution-delphi", "trigger": None},

    # F1 — Specialized agents (Wave 2)
    {"phase": "F1c", "label": "AS-IS Database Analysis",
     "agent": "ava-asis-db-analyzer",   "trigger": None},
    {"phase": "F1d", "label": "AS-IS Documentation (Business Rules & Requirements)",
     "agent": "ava-asis-documentation", "trigger": None},
    {"phase": "F1e", "label": "AS-IS Security Review",
     "agent": "ava-asis-security-review", "trigger": None},

    # F1 — Specialized agents (Wave 3 — consolidation)
    {"phase": "F1f", "label": "AS-IS Gaps & Risks",
     "agent": "ava-asis-gaps-risks",    "trigger": None},

    # F2
    {"phase": "F2a", "label": "TO-BE Architecture — Solution Design",
     "agent": "ava-tobe-orchestrator",  "trigger": "SD"},
    {"phase": "F2b", "label": "DevOps Plan",
     "agent": "ava-devops-orchestrator","trigger": "DP"},
    {"phase": "F2c", "label": "QA — Test Plan & Strategy",
     "agent": "ava-qa-orchestrator",    "trigger": "TPT"},

    # F2d — Reconciliação determinística dos artefatos de waves. É um passo
    # TOOL, não um agente: normalizar `bounded_contexts[]` para a forma
    # canônica, resolver `bc_name` a partir do bounded-context-map e conferir a
    # composição contra o wave-plan.md são operações mecânicas, e deixá-las na
    # interpretação de um LLM é exatamente o que produziu o defeito medido em
    # cadastro-funcionarios (2026-08-26): o wave-model.json declarava
    # `bounded_contexts: ["BC-02"]` sem o `bc_details[]` que nomeia o BC, e a
    # F3S abortou a expansão — com TODOS os artefatos do gate de entrada
    # presentes. Roda no fim da F2 porque o wave-model nasce na F2a e é
    # atualizado pelo sizing; o veredito final é o `build_manifest()` real da
    # F3S, então passar aqui significa que a F3S expande.
    # `on_fail: warn` pela política da esteira — erro não trava fase; o achado
    # fica visível no console e persistido em
    # outputs/tobe/migration/wave-model-consistency.json.
    {"phase": "F2d", "label": "TO-BE — Coerência do wave model "
                              "(normaliza + valida contra wave-plan/BC map)",
     "agent": "wave-model-consistency", "kind": "tool", "trigger": None,
     "on_fail": "warn",
     "command": ["{python}", "src/shared/tools/wave_model_consistency.py",
                 "--project", "{project}", "--fix", "--json"]},

    # F3
    {"phase": "F3",  "label": "Prototype",
     "agent": "ava-prototype",          "trigger": None},

    # F3S — Camada de planejamento SpecKit (spec 039). Entre o protótipo e a
    # geração de código: constitution → specs por artefato-fonte → plans → tasks
    # → compliance, com gate de entrada e gate de saída determinísticos.
    # A ordem interna e as fatias de contexto por agente ficam em
    # src/shared/data/pipeline-dag/F3S.yaml — fonte única.
    {"phase": "F3S", "label": "SpecKit — Constitution, Specs, Plans & Tasks",
     "agent": "ava-speckit-orchestrator", "trigger": "SK"},

    # F4
    # F4S — scaffold determinístico. É um passo TOOL, não um agente: a ordem
    # frontend→backend, o caminho de saída e o gate de aprovação são decisões
    # determinísticas, e deixá-las na interpretação de um LLM foi exatamente o
    # que produziu dois caminhos de scaffold divergentes. Roda ANTES da F4;
    # `ava-stack-orchestrator` só despacha coder se este passo tiver registrado
    # aprovação explícita em tasks-progress.json.
    {"phase": "F4S", "label": "Stack — Scaffold determinístico "
                              "(frontend → backend → baseline → aprovação)",
     "agent": "scaffold-runner", "kind": "tool", "trigger": None,
     # Teto do passo INTEIRO: geração dos dois componentes (com até 3
     # tentativas cada) mais o verifier, que roda `dotnet restore/build/test`
     # sobre a solution recém-nascida. Os 900s embutidos no runner mataram a
     # F4S de `nopcommerce-02` aos 835s de trabalho real — 79/79 csproj no
     # disco, solution montada, verifier nunca iniciado — e o passo morreu sem
     # veredito. NÃO é uma conta por bounded context: é o limite de segurança
     # acima do qual o processo é dado como travado. Ver
     # `pipeline_plan.DEFAULT_TOOL_TIMEOUT_S`.
     "timeout_s": 3600,
     "command": ["{python}", "src/shared/tools/scaffold_runner.py",
                 "--project", "{project}", "--json"]},

    {"phase": "F4",  "label": "Tech Stack — Stack Generation",
     "agent": "ava-stack-orchestrator", "trigger": "SG"},

    # F5
    {"phase": "F5",  "label": "DevOps Execute",
     "agent": "ava-devops-orchestrator","trigger": "DE"},

    # F6 — QE (Quality Execute): cadeia completa GR→BM→FTM→TS→TC→AS→...→PT→RS
    # TPT seria errado aqui: TPT interrompe após ava-test-plan-tobe (Momento 1 já rodou em F2c)
    {"phase": "F6",  "label": "QA — Test Execution",
     "agent": "ava-qa-orchestrator",    "trigger": "QE"},

    # Summary cycle
    # S1 → gera o HTML (pode sair em partes — merge automático pós-S1)
    # S2 → remediation: só roda após S1 unificado confirmado
    # S3 → validate: só roda sobre o HTML unificado (nunca sobre partes)
    # S4 → final: regeneração limpa após remediação
    {"phase": "S1",  "label": "Summary — Generate",
     "agent": "ava-summary",            "trigger": "SAS"},
    {"phase": "S2",  "label": "Summary — Remediation (requer HTML unificado de S1)",
     "agent": "ava-summary-remediation","trigger": None},
    {"phase": "S3",  "label": "Summary — Validate (requer HTML unificado de S1/S2)",
     "agent": "ava-summary-validate",   "trigger": None},
    {"phase": "S4",  "label": "Summary — Final (regeneração limpa)",
     "agent": "ava-summary",            "trigger": "SAS"},

    # FC — Containerização (pré-requisito do Podman Run)
    {"phase": "FC",  "label": "DevOps — Containerize (Dockerfiles + docker-compose)",
     "agent": "ava-devops-containerize",  "trigger": None},

    # FP — Execução local com Podman (depende de FC)
    {"phase": "FP",  "label": "DevOps — Podman Run (execução local)",
     "agent": "ava-devops-podman-run",   "trigger": None},
]


def _dag_da_fase(phase: str) -> dict | None:
    """O `pipeline-dag/{phase}.yaml` da fase, ou `None` quando ela não tem um.

    Fase com DAG próprio é autossuficiente: agentes, ordem, gate de entrada e
    gate de saída vivem lá. Ler daqui é o que impede a fase de herdar contrato
    de outra fonte.
    """
    caminho = WORKSPACE / "src" / "shared" / "data" / "pipeline-dag" / f"{phase}.yaml"
    if not caminho.is_file():
        return None
    try:
        import yaml as _yaml
        dados = _yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — degradar, nunca derrubar o runner (IV3)
        return None
    return dados if isinstance(dados, dict) else None


def _inputs_do_entry_gate(dag: dict) -> dict | None:
    """`entry_gate` do DAG traduzido para o formato de manifesto `inputs`."""
    itens = ((dag.get("entry_gate") or {}).get("items")) or []
    obrigatorios = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        # `kind: any_file` declara ALTERNATIVAS em `paths[]` — nenhuma delas é
        # obrigatória sozinha, então o preflight de caminho único não se aplica.
        if item.get("kind") == "any_file" or not item.get("path"):
            continue
        obrigatorios.append({"path": str(item["path"]),
                             "produced_by": str(item.get("produced_by") or "")})
    return {"mandatory": obrigatorios} if obrigatorios else None


# ── F5 · DevOps Execute — identidade e manifesto fechado ─────────────────────
# Escopo cirúrgico: só a tripla (F5, ava-devops-orchestrator, DE). O MESMO
# agente roda em F2b com trigger DP, e o planejamento continua no caminho comum.
F5_DEVOPS_PHASE = "F5"
F5_DEVOPS_AGENT = "ava-devops-orchestrator"
F5_DEVOPS_TRIGGER = "DE"

#: Insumos iniciais da F5/DE, em POSIX. Três arquivos, nenhum diretório.
#: A barra `/` é literal de propósito: `"outputs\tobe\..."` num literal Python
#: viraria TAB + `obe`, e o caminho deixaria de existir sem erro visível.
F5_DEVOPS_INPUT_PATHS: tuple[str, ...] = (
    "context/project-config.yaml",
    "outputs/tobe/devops/devops-plan.md",
    "outputs/tobe/devops/environments-plan.md",
)

#: Nunca entram no contexto deste passo — nem no manifesto, nem sob demanda.
F5_DEVOPS_FORBIDDEN: tuple[str, ...] = (
    "context/shared-context.md",
    "outputs/tobe/docs/architecture-blueprint.md",
    "outputs/tobe/source-code",
    "outputs/tobe/source-code/frontend",
    "outputs/tobe/source-code/backend",
)

_F5_DEVOPS_PRODUCERS = {
    "context/project-config.yaml": "operador (setup do projeto)",
    "outputs/tobe/devops/devops-plan.md":
        "ava-devops-orchestrator (F2b, trigger DP)",
    "outputs/tobe/devops/environments-plan.md":
        "ava-devops-orchestrator (F2b, trigger DP)",
}


# ── F4 · Tech Stack Code Generation — identidade da fase ─────────────────────
F4_PHASE = "F4"
F4_ORCHESTRATOR = "ava-stack-orchestrator"
F4_TRIGGER = "SG"

#: Teto de saída por task. Uma task implementa UMA fatia — não 140 arquivos.
F4_TASK_MAX_TOKENS = 32_000


def _is_f4_codegen_step(step: "dict | None") -> bool:
    """True só para o passo F4 / ava-stack-orchestrator / SG."""
    if not step:
        return False
    return (str(step.get("phase") or "") == F4_PHASE
            and str(step.get("agent") or "") == F4_ORCHESTRATOR
            and str(step.get("trigger") or "") == F4_TRIGGER)


def _f4_inputs() -> dict:
    """Manifesto FECHADO da F4: vazio, e é proposital.

    O contexto da F4 é montado **por task** em `f4_task_context.build()`. Um
    manifesto de fase aqui voltaria a injetar `specs/*/spec.md` de todas as
    features em todos os despachos — os 659 KB medidos em
    `cadastro-funcionarios-04` multiplicados por 218 tasks. `floor: []` também
    tira `context/shared-context.md`, que a task não usa.
    """
    return {"floor": [], "mandatory": [], "advisory": []}


def _is_f5_devops_step(step: "dict | None") -> bool:
    """True só para o passo F5 / ava-devops-orchestrator / DE."""
    if not step:
        return False
    return (str(step.get("phase") or "") == F5_DEVOPS_PHASE
            and str(step.get("agent") or "") == F5_DEVOPS_AGENT
            and str(step.get("trigger") or "") == F5_DEVOPS_TRIGGER)


def _f5_devops_inputs() -> dict:
    """Manifesto da F5/DE: três arquivos, sem piso, sem diretório.

    `floor: []` remove `context/shared-context.md` do piso do
    `context_manifest`; `project-config.yaml` volta como insumo declarado, o que
    o mantém no contexto sem duplicá-lo.
    """
    return {
        "floor": [],
        "mandatory": [{"path": p, "produced_by": _F5_DEVOPS_PRODUCERS.get(p, "")}
                      for p in F5_DEVOPS_INPUT_PATHS],
    }


# ── F6 · QA Execute — identidade e manifesto fechado ─────────────────────────
# Mesmo escopo cirúrgico da F5: só a tripla (F6, ava-qa-orchestrator, QE). O
# MESMO agente roda em F2c com trigger TPT, e o planejamento de testes continua
# no caminho comum.
F6_QA_PHASE = "F6"
F6_QA_AGENT = "ava-qa-orchestrator"
F6_QA_TRIGGER = "QE"

#: Precondição conferida por EXISTÊNCIA e população — nunca injetada.
F6_QA_EXISTS: tuple[str, ...] = (
    "outputs/tobe/source-code/README.md",
    "outputs/tobe/source-code/backend/**",
    "outputs/tobe/source-code/frontend/**",
)

#: Insumos com conteúdo injetado no Momento 1 (planejamento). Só arquivos.
F6_QA_MANDATORY: tuple[str, ...] = (
    "outputs/tobe/docs/bounded-context-map.md",
    "outputs/tobe/qa/test-plan.md",
    "outputs/tobe/qa/test-cases.md",
)

F6_QA_ADVISORY: tuple[str, ...] = (
    "outputs/tobe/qa/functional-test-matrix.md",
    "outputs/tobe/tests/functional-test-matrix.md",
    "outputs/tobe/qa/gap-analysis.md",
    "outputs/tobe/parity-test-report.md",
    "outputs/asis/docs/business-rules.json",
    "outputs/asis/docs/behavior-catalog.json",
    "outputs/asis/docs/schema-inventory.md",
)

#: Nunca entram como conteúdo — nem no manifesto, nem sob demanda.
F6_QA_FORBIDDEN: tuple[str, ...] = (
    "context/shared-context.md",
    "outputs/tobe/source-code",
    "outputs/tobe/source-code/frontend",
    "outputs/tobe/source-code/backend",
)

_F6_QA_PRODUCERS = {
    "outputs/tobe/source-code/README.md": "ava-stack-orchestrator (F4)",
    "outputs/tobe/source-code/backend/**": "ava-stack-orchestrator (F4)",
    "outputs/tobe/source-code/frontend/**": "ava-stack-orchestrator (F4)",
    "outputs/tobe/docs/bounded-context-map.md":
        "ava-tobe-orchestrator (F2a, trigger SD)",
    "outputs/tobe/qa/test-plan.md": "ava-qa-orchestrator (F2c, trigger TPT)",
    "outputs/tobe/qa/test-cases.md": "ava-qa-orchestrator (F2c, trigger TPT)",
}


def _is_f6_qa_step(step: "dict | None") -> bool:
    """True só para o passo F6 / ava-qa-orchestrator / QE."""
    if not step:
        return False
    return (str(step.get("phase") or "") == F6_QA_PHASE
            and str(step.get("agent") or "") == F6_QA_AGENT
            and str(step.get("trigger") or "") == F6_QA_TRIGGER)


def _f6_qa_inputs() -> dict:
    """Manifesto da F6/QE: existência separada de injeção, sem diretório.

    `exists` responde ao gate ("a F4 rodou?") sem custo de contexto; `mandatory`
    e `advisory` trazem só os artefatos de planejamento de QA. `floor` fica
    apenas com o `project-config.yaml` — `shared-context.md` é prosa longa que
    repete o que os artefatos de QA já dizem.
    """
    return {
        "floor": ["context/project-config.yaml"],
        "exists": [{"path": p, "produced_by": _F6_QA_PRODUCERS.get(p, "")}
                   for p in F6_QA_EXISTS],
        "mandatory": [{"path": p, "produced_by": _F6_QA_PRODUCERS.get(p, "")}
                      for p in F6_QA_MANDATORY],
        "advisory": list(F6_QA_ADVISORY),
    }


def _assert_no_directory_inputs(project: str, step: dict,
                                forbidden: "tuple[str, ...] | None" = None) -> list[str]:
    """Rede final: nenhum insumo INJETADO deste passo pode ser diretório.

    Roda antes do despacho. Um diretório em `mandatory`/`advisory` significa que
    a expansão `rglob("*")` do `context_manifest` voltaria a despejar a árvore no
    prompt — exatamente o defeito que F5 e F6 foram reescritas para eliminar.

    O tier `exists` é conferido de propósito: ele NÃO injeta corpo, e é
    justamente onde um diretório é a declaração correta.

    Devolve os caminhos recusados (lista vazia = tudo certo).
    """
    raiz = WORKSPACE / "projects" / project
    proibidos = forbidden if forbidden is not None else F5_DEVOPS_FORBIDDEN
    recusados: list[str] = []
    declarado = (step or {}).get("inputs") or {}
    for tier in ("mandatory", "advisory"):
        for item in declarado.get(tier) or []:
            caminho = item["path"] if isinstance(item, dict) else str(item)
            caminho = str(caminho).replace("\\", "/")
            if any(caminho == proibido or caminho.startswith(proibido + "/")
                   for proibido in proibidos):
                recusados.append(caminho)
                continue
            if any(ch in caminho for ch in "*?["):
                continue                      # glob explícito: escopo é do autor
            if (raiz / caminho).is_dir():
                recusados.append(caminho)
    return recusados


def _apply_declared_inputs(pipeline: list[dict]) -> int:
    """Anexa o manifesto `inputs` de cada passo, do DAG da fase quando ele existe.

    Precedência: `pipeline-dag/{phase}.yaml → entry_gate` vence
    `src/shared/data/ava-pipeline.yaml`. Uma fase com DAG próprio declara ali o
    que exige para começar, e deixar o `ava-pipeline.yaml` sobrepor isso criava
    duas fontes de verdade para a mesma pergunta — com a agravante de que só uma
    delas é a que o gate determinístico da fase consulta em runtime. Fase sem
    DAG continua no `ava-pipeline.yaml`; ausência dos dois degrada sem quebrar
    (IV3).
    """
    try:
        import pipeline_config
        declarados = {str(s.get("phase")): s.get("inputs")
                      for s in (pipeline_config.load_config().get("steps") or [])
                      if s.get("inputs")}
    except Exception:  # noqa: BLE001 — nunca derrubar o runner por causa disto
        declarados = {}

    aplicados = 0
    for step in pipeline:
        phase = str(step.get("phase") or "")
        manifesto = None
        dag = _dag_da_fase(phase)
        if dag is not None:
            manifesto = _inputs_do_entry_gate(dag)
        if manifesto is None:
            manifesto = declarados.get(phase)
        # A F5/DE tem manifesto FECHADO, no código, e ele vence qualquer fonte
        # externa. Não é desconfiança do YAML: é que uma única linha errada lá
        # (`path: outputs/tobe/source-code`) custou um 400 de 3.924.457 tokens, e
        # o custo de reintroduzi-la por descuido é alto demais para depender só
        # de revisão de arquivo de dados.
        # A F4 tem manifesto FECHADO e VAZIO, no código: o contexto dela é por
        # task (`f4_task_context`). Deixar o YAML mandar aqui reintroduz
        # `specs/*/spec.md` de todas as features em todo despacho.
        if _is_f4_codegen_step(step):
            manifesto = _f4_inputs()
        if _is_f5_devops_step(step):
            manifesto = _f5_devops_inputs()
        # Mesmo raciocínio para a F6/QE: `outputs/tobe/source-code` no YAML
        # custou um 400 de 3.958.957 tokens. O manifesto fechado vence.
        if _is_f6_qa_step(step):
            manifesto = _f6_qa_inputs()
        if manifesto:
            step["inputs"] = manifesto
            aplicados += 1
    return aplicados


#: Tentativas de remediação automática do wave model antes de degradar.
F3S_REMEDIACAO_TENTATIVAS = 3


def _remediar_e_expandir_f3s(fase: str, project: str, erro: Exception,
                             step: dict) -> list[dict]:
    """Conserta o wave model e devolve os passos da F3S. Nunca levanta.

    Três camadas, nesta ordem, e a fase só para se todas falharem:

    1. **Remediação mecânica** — `wave_model_consistency` até
       ``F3S_REMEDIACAO_TENTATIVAS`` vezes. Converte ID textual em objeto
       canônico, resolve `bc_name` pelo bounded-context-map, preenche
       `wave_number`/`tshirt`/`depends_on_waves`. É o que resolve o caso comum.
    2. **Expansão em modo degradado** — se o modelo ainda não expande, o
       manifesto é construído com ``strict=False``: BC sem nome vira o próprio
       id. Rótulo provisório, mas os artefatos do SpecKit são gerados.
    3. **Devolver vazio** — só quando nem o modo degradado produz feature, o que
       significa que não há `waves[]` algum para expandir.

    O que muda em relação ao comportamento anterior: incoerência de wave model
    deixou de impedir a geração dos artefatos da F3S. Ela vira aviso, fica
    registrada, e a esteira segue — que é o contrário de degradar a fase inteira
    e entregar `outputs/tobe/speckit/` vazio para as fases seguintes.
    """
    import pipeline_plan
    import wave_model_consistency as coerencia

    print(f"\n{YELLOW}  ⚠️  {fase}: wave model incoerente — "
          f"tentando remediação automática antes de degradar.{RESET}")
    print(f"  {DIM}     {str(erro)[:160]}{RESET}")

    aplicados: list[str] = []
    pendentes: list[str] = []
    try:
        historico = coerencia.remediate(project, WORKSPACE,
                                        attempts=F3S_REMEDIACAO_TENTATIVAS)
    except Exception as falha:  # noqa: BLE001 — remediação jamais derruba a fase
        historico = []
        pendentes = [f"remediação indisponível: {type(falha).__name__}: {falha}"]

    for relatorio in historico:
        for item in relatorio.get("fixes") or []:
            aplicados.append(item)
        pendentes = list(relatorio.get("errors") or [])

    for item in aplicados[:12]:
        print(f"  {GREEN}     [corrigido] {item}{RESET}")
    if len(aplicados) > 12:
        print(f"  {DIM}     (+{len(aplicados) - 12} correções não listadas){RESET}")

    # Nova tentativa em modo estrito: se a remediação bastou, a F3S segue com o
    # manifesto de verdade, sem degradação alguma.
    try:
        declarados = pipeline_plan.dag_steps(fase, WORKSPACE, project=project)
        if declarados:
            print(f"  {GREEN}  ✅ {fase}: wave model remediado — "
                  f"expansão normal, sem degradação.{RESET}")
            return declarados
    except Exception:  # noqa: BLE001 — segue para o modo degradado
        pass

    for item in pendentes[:6]:
        print(f"  {YELLOW}     [pendente] {item}{RESET}")

    # Modo degradado: o que sobrou exige julgamento humano (BC em duas waves,
    # BC sem definição no mapa). Isso NÃO é motivo para não gerar os artefatos.
    try:
        import speckit_wave_manifest as manifesto
        # Persistir o manifesto degradado é parte do contrato: o `exit_gate` da
        # F3S confere `wave-spec-manifest.json`, e os agentes a jusante o leem.
        resultado = manifesto.write_manifest(project, WORKSPACE, strict=False)
        declarados = pipeline_plan.dag_steps(fase, WORKSPACE, project=project,
                                             strict=False)
    except Exception as falha:  # noqa: BLE001
        print(f"  {RED}  ✖ {fase}: nem em modo degradado foi possível expandir "
              f"({type(falha).__name__}: {falha}).{RESET}")
        return []

    if not declarados:
        return []
    step["wave_model_degradado"] = True
    _record_degradation(
        fase, project,
        f"wave model expandido em modo degradado após {len(historico)} "
        f"tentativa(s) de remediação; pendências: "
        + ("; ".join(pendentes[:3]) or "nenhuma"),
        "revise outputs/tobe/migration/wave-model.json — os artefatos da F3S "
        "foram gerados assim mesmo e a esteira prosseguiu",
    )
    print(f"  {YELLOW}  ⚠️  {fase}: expandido em MODO DEGRADADO "
          f"({resultado.get('total_waves', 0)} wave(s)). Os artefatos do SpecKit "
          f"serão gerados; revise o wave model depois.{RESET}")
    return declarados


def _expand_dag_phases(pipeline: list[dict], project: str | None = None) -> int:
    """Expande fases multi-agente em um despacho por agente da wave.

    Uma fase com vários agentes despachada como passo único vira teatro: o motor
    SDK carrega **apenas** o `spec_path` do orquestrador e proíbe tools, então os
    corpos dos sub-agentes — onde moram os contratos de formato — nunca entram em
    contexto.

    Medido na primeira execução real da F3S por este runner: skill de 8KB (só o
    orquestrador), 92.830 tokens de entrada, 68.170 de saída, 26 artefatos numa
    resposta. A saída divergiu de todos os contratos dos seis agentes que não
    foram carregados.

    A ordem vem de `pipeline-dag/{fase}.yaml`, lida pela mesma função que o CLI
    usa. Sem o DAG, a fase é mantida como passo único (IV3).
    """
    try:
        import pipeline_plan
    except Exception:  # noqa: BLE001
        return 0

    expandidos: list[dict] = []
    total = 0
    for step in pipeline:
        fase = step.get("phase", "")
        try:
            declarados = pipeline_plan.dag_steps(
                fase, WORKSPACE, project=project
            ) if fase == "F3S" else []
        except Exception as exc:  # noqa: BLE001
            # Wave model incoerente NÃO trava mais a F3S. Antes o `PlanError`
            # devolvia 0 e a fase inteira era degradada — nenhum artefato do
            # SpecKit era gerado, e as fases seguintes herdavam o vazio. Só que
            # a incoerência é quase sempre mecânica (ID textual sem bc_details,
            # `wave_number` ausente), e existe tool determinística que a conserta.
            # Aqui ela é chamada, e se ainda assim o modelo não expandir, a
            # expansão sai em modo degradado — com aviso, nunca com bloqueio.
            declarados = _remediar_e_expandir_f3s(fase or "F3S", project, exc, step)
            if not declarados:
                step["dag_expansion_error"] = f"{type(exc).__name__}: {exc}"
                print(explicar_fase_nao_expandida(fase or "F3S", project, exc))
                return 0
        if not declarados:
            expandidos.append(step)
            continue
        for d in declarados:
            novo = dict(step)
            novo.update({"phase": d["phase"], "agent": d["agent"],
                         "trigger": d["trigger"], "label": d["label"],
                         "feature": d["feature"], "inputs": d["inputs"],
                         "kind": d.get("kind", "agent"),
                         "command": list(d.get("command") or []),
                         # `outputs`/`output_base` vinham sendo descartados aqui:
                         # o DAG declarava specs/{feature}/plan-graph.json e nada
                         # no runner enxergava a declaração (ISSUE-004).
                         "outputs": list(d.get("outputs") or []),
                         "output_base": d.get("output_base", ""),
                         "on_fail": d.get("on_fail", ""),
                         # Sem propagar `spec_path`, `load_skill` cai na busca
                         # heurística e escolhe o MAIOR arquivo que casa por
                         # substring. Foi assim que `ava-speckit-compliance`
                         # carregou o agente de segurança da F7 e gravou em
                         # `outputs/deliverables/` — ver `pipeline_plan.
                         # _spec_path_do_registry`. A chave era montada lá e
                         # descartada aqui.
                         "spec_path": ((WORKSPACE / d["spec_path"]).as_posix()
                                       if d.get("spec_path") else None),
                         "requires_approval": bool(d.get("requires_approval")),
                         "wave": d.get("wave", "")})
            expandidos.append(novo)
            total += 1
    if total:
        pipeline[:] = expandidos
    return total


def _expand_ledger_phase(pipeline: list[dict], project: str) -> list[dict]:
    """A F4 **não** é mais expandida em passos estáticos. Devolve o plano intacto.

    Por que a expansão saiu daqui
    -----------------------------
    Ela montava N passos de uma vez, no início da fase, a partir de um retrato
    do razão daquele instante. Três consequências medidas:

    1. a conclusão da task 7 não fazia a 41 aparecer — a 41 já tinha sido
       classificada como "não pronta" e só voltava num `--resume`;
    2. cada passo herdava o manifesto GLOBAL da fase (659 KB em
       `cadastro-funcionarios-04`), multiplicado por 218 tasks;
    3. `feature` não era copiado para o passo e `task_id` não entrava no
       prompt — os N despachos eram textualmente idênticos.

    Hoje a fase é um passo só, e `_run_f4_codegen_step` roda o laço que relê o
    razão a cada volta. O `--phase F4` e o `--resume` continuam valendo: quem
    guarda o progresso é `tasks-progress.json`, não a lista de passos.
    """
    return pipeline


_INPUTS_APLICADOS = _apply_declared_inputs(PIPELINE)
_DAG_EXPANDIDOS = 0

# ── Cores ANSI ───────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
MAGENTA= "\033[95m"


def banner(text: str, color: str = CYAN):
    if _RICH_OK:
        _cmap = {CYAN: "cyan", GREEN: "green", YELLOW: "yellow", RED: "red", MAGENTA: "magenta"}
        _RICH_CONSOLE.print(_RichPanel(text, style=f"bold {_cmap.get(color, 'cyan')}", expand=False))
        return
    line = "─" * 60
    print(f"\n{color}{BOLD}{line}{RESET}")
    print(f"{color}{BOLD}  {text}{RESET}")
    print(f"{color}{BOLD}{line}{RESET}")


def _safe_filename_component(value: str) -> str:
    """Normaliza um componente de nome de arquivo para plataformas Windows.

    Mantém o identificador lógico intacto em memória e só sanitiza o valor
    usado no path físico de logs/relatórios.
    """
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '-', value).strip(' .')
    return safe or "unnamed"


def _phase_log_path(output_dir: Path, phase: str, agent: str, ts: str) -> Path:
    """Retorna o path físico do log do passo com componentes compatíveis com Windows."""
    safe_phase = _safe_filename_component(phase)
    safe_agent = _safe_filename_component(agent)
    return output_dir / f"{safe_phase}_{safe_agent}_{ts}.md"


# ── Persistência de estado para retomada ─────────────────────────────────────
# O runner salva um arquivo JSON com os passos já executados/pulados/abortados
# e as métricas de execução. Isso permite retomar uma execução interrompida
# (ex.: falha na F3S) sem reexecutar sub-agentes que já geraram artefatos.

_RUNNER_STATE_FILE = "runner-state.json"
_RUNNER_STATE_DONE = "runner-state-done.json"


def _runner_state_path(project: str, done: bool = False) -> Path:
    """Path do arquivo de estado do runner para um projeto."""
    name = _RUNNER_STATE_DONE if done else _RUNNER_STATE_FILE
    return WORKSPACE / "projects" / project / "outputs" / "pipeline_runner" / name


def _mark_executed(phase: str, executed: list, skipped: list, aborted: list,
                   val_failed: "list | None" = None) -> None:
    """Registra execução bem-sucedida, limpando veredictos anteriores da fase.

    Um passo pulado ou abortado numa tentativa anterior e reexecutado com sucesso
    na retomada ficava nas DUAS listas. O dashboard testa `skipped` antes de
    `executed`, então ele continuava aparecendo como "⏭ Pulado" depois de ter
    rodado, e era contado nos dois totalizadores ao mesmo tempo.
    """
    while phase in skipped:
        skipped.remove(phase)
    while phase in aborted:
        aborted.remove(phase)
    if val_failed is not None:
        while phase in val_failed:
            val_failed.remove(phase)
    if phase not in executed:
        executed.append(phase)


# ── Degradações: o pipeline nunca trava, mas nada some ───────────────────────
# Política: erro NÃO bloqueia fase. A fase segue como executada, o operador é
# avisado no terminal e o motivo + o caminho de correção ficam registrados em
# outputs/pipeline_runner/remediation-report.json.
#
# A regra vem do que foi medido em nopcommerce-04 (2026-08-21): o runner tinha
# três destinos para um erro — abortar, marcar "⏭ pulado", ou marcar ✅ em
# silêncio — e o pior dos três era o terceiro, porque o defeito reaparecia
# passos adiante atribuído ao agente errado. O registro abaixo elimina esse
# terceiro caso: continuar sim, em silêncio nunca.
_DEGRADATIONS: list[dict] = []


# ── SpecKit: camada em evolução, non-blocking por decisão ────────────────────
# Enquanto a F3S está sendo estabilizada, uma reprovação dela não pode:
#   · derrubar a esteira,
#   · virar exit code != 0,
#   · contar como FAILED no veredito global,
#   · aparecer no dashboard como falha bloqueadora.
#
# Ela CONTINUA rodando, gerando artefato e métrica, e registrando o achado —
# como aviso rastreável, em `remediation-report.json` e nos relatórios das
# próprias tools (`{gate}-gate-status.json`, `checks-report.json`).
#
# Isto NÃO é "erro nunca trava fase" (que já valia para a esteira inteira): é um
# grau a mais, restrito à F3S, que também tira a fase da contabilidade de
# reprovação. Reverter = apagar este bloco e as três chamadas a
# `_is_speckit_nonblocking`.
SPECKIT_PHASE_PREFIX = "F3S"
SPECKIT_AGENT_PREFIXES = ("ava-speckit-", "speckit-")


def _is_speckit_nonblocking(phase: str = "", agent: str = "") -> bool:
    """True para qualquer passo da camada SpecKit (fase F3S ou agente speckit)."""
    fase = str(phase or "")
    if fase == SPECKIT_PHASE_PREFIX or fase.startswith(SPECKIT_PHASE_PREFIX + ":"):
        return True
    return str(agent or "").startswith(SPECKIT_AGENT_PREFIXES)


def _speckit_nonblocking_step(step: "dict | None") -> bool:
    if not step:
        return False
    return _is_speckit_nonblocking(str(step.get("phase") or ""),
                                   str(step.get("agent") or ""))


def _record_degradation(phase: str, agent: str, reason: str, fix: str,
                        *, severity: str = "warning") -> None:
    _DEGRADATIONS.append({
        "phase": phase, "agent": agent, "severity": severity,
        "reason": reason, "fix": fix,
    })


def _print_degradation(phase: str, reason: str, fix: str,
                       *, informativo: bool = False) -> None:
    if informativo:
        # Fase non-blocking: o texto não pode sugerir reprovação, porque não há.
        print(f"\n{CYAN}{'─' * 68}{RESET}")
        print(f"{CYAN}ℹ️  FASE INFORMATIVA (SpecKit em evolução — não bloqueia "
              f"nem reprova): {phase}{RESET}")
        print(f"{CYAN}   Achado: {reason}{RESET}")
        print(f"{CYAN}   Sugestão: {fix}{RESET}")
        print(f"{CYAN}   O pipeline segue e o exit code não muda. Registro: "
              f"outputs/pipeline_runner/remediation-report.json{RESET}")
        print(f"{CYAN}{'─' * 68}{RESET}")
        return
    print(f"\n{YELLOW}{'─' * 68}{RESET}")
    print(f"{YELLOW}⚠️  FASE DEGRADADA (não bloqueada): {phase}{RESET}")
    print(f"{YELLOW}   Motivo: {reason}{RESET}")
    print(f"{YELLOW}   CORREÇÃO: {fix}{RESET}")
    print(f"{YELLOW}   A esteira continua. Registro: "
          f"outputs/pipeline_runner/remediation-report.json{RESET}")
    print(f"{YELLOW}{'─' * 68}{RESET}")


def _degrade_phase(step: dict, reason: str, fix: str,
                   executed: list, skipped: list, aborted: list,
                   exec_metrics: dict, *, val_failed: "list | None" = None) -> None:
    """Marca a fase como executada-com-aviso e registra o caminho de correção.

    `val_ok=False` + `degraded=True` preservam a verdade para o relatório; a
    fase entra em `executed` para que nenhuma sucessora seja bloqueada.
    """
    phase, agent = step["phase"], step.get("agent", "")
    # A camada SpecKit é non-blocking enquanto está em evolução: o achado é
    # registrado e mostrado, mas entra como INFO e não conta como reprovação no
    # veredito global. Ver `_is_speckit_nonblocking`.
    speckit = _speckit_nonblocking_step(step)
    _print_degradation(phase, reason, fix, informativo=speckit)
    _record_degradation(phase, agent, reason, fix,
                        severity="info" if speckit else "warning")
    metrics = exec_metrics.setdefault(phase, {
        "phase": phase, "agent": agent, "skill_kb": 0, "inp_tokens": 0,
        "out_max": 0, "resp_tokens": 0, "ctx_pct": 0, "elapsed_s": 0,
        "artifacts": 0,
    })
    metrics.update({"val_ok": False, "degraded": True,
                    "detail": reason, "fix": fix,
                    "non_blocking": speckit})
    _mark_executed(phase, executed, skipped, aborted, val_failed=val_failed)


def _degrade_unexpandable_f3s(step: dict, error: Exception,
                               executed: list, skipped: list, aborted: list,
                               exec_metrics: dict, val_failed: list) -> None:
    """Registra um manifesto inválido sem interromper a esteira inteira."""
    reason = (
        "não foi possível expandir o manifesto de waves da F3S: "
        f"{type(error).__name__}: {error}"
    )
    fix = (
        "corrija outputs/tobe/migration/wave-model.json ou wave-plan.md e "
        "reexecute F3S com --resume; o pipeline prossegue com esta pendência registrada"
    )
    _degrade_phase(step, reason, fix, executed, skipped, aborted, exec_metrics,
                   val_failed=val_failed)
    # A F3S é non-blocking: entrar em `val_failed` a faria contar como
    # reprovação no veredito global e aparecer como "❌ Val-Fail" no dashboard.
    # O achado continua registrado como degradação informativa.
    if (not _speckit_nonblocking_step(step)
            and step["phase"] not in val_failed):
        val_failed.append(step["phase"])


def _write_remediation_report(project: str) -> "Path | None":
    """Materializa as degradações do run. Sempre gravado, inclusive vazio."""
    try:
        out_dir = Path("projects") / project / "outputs" / "pipeline_runner"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "remediation-report.json"
        target.write_text(json.dumps({
            "project": project,
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "total": len(_DEGRADATIONS),
            "degradations": _DEGRADATIONS,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target
    except OSError:
        # Persistir o aviso nunca pode ser o motivo de uma falha adicional.
        return None


def _print_remediation_summary(project: str) -> None:
    if not _DEGRADATIONS:
        return
    print(f"\n{YELLOW}{BOLD}{'═' * 68}{RESET}")
    print(f"{YELLOW}{BOLD}  ⚠️  {len(_DEGRADATIONS)} FASE(S) DEGRADADA(S) — "
          f"executadas, mas com pendência{RESET}")
    print(f"{YELLOW}{'═' * 68}{RESET}")
    for item in _DEGRADATIONS:
        print(f"{YELLOW}  • {item['phase']}{RESET}")
        print(f"      motivo:   {item['reason']}")
        print(f"      correção: {item['fix']}")
    print(f"{YELLOW}{'═' * 68}{RESET}")
    print(f"{DIM}  Detalhe: projects/{project}/outputs/pipeline_runner/"
          f"remediation-report.json{RESET}\n")


def _phase_identity(step: dict) -> str:
    """Retorna identificador único e estável para um passo.

    Para passos expandidos do DAG (F3S) e do ledger (F4), o 'phase' já é
    suficientemente específico (inclui papel, feature e task_id quando aplicável).
    """
    return str(step.get("phase") or step.get("agent") or "unknown")


def _serialize_metrics(metrics: dict) -> dict:
    """Remove campos não serializáveis (ex.: Path) antes de salvar em JSON."""
    result: dict = {}
    for key, value in metrics.items():
        if isinstance(value, Path):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = _serialize_metrics(value)
        elif isinstance(value, list):
            result[key] = [
                str(v) if isinstance(v, Path) else
                _serialize_metrics(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[key] = value
    return result


# ── Métricas de execução (pipeline-runner-metrics.json) ─────────────────────
# Contrato fechado: o arquivo sai com as MESMAS chaves, na mesma ordem, em
# qualquer modo de execução e mesmo quando uma única fase rodou. Quem consome a
# jusante lê sem checar presença de campo — por isso nada aqui é condicional.
#
# A fonte é o `exec_metrics` que a esteira já mantém (fase → retorno de
# `run_step`); este módulo só normaliza e serializa. Nenhum caminho aqui pode
# levantar: instrumentação não derruba execução que já foi paga em inferência.
METRICS_FILENAME = "pipeline-runner-metrics.json"

# Um valor por caminho de entrada real do runner.
EXEC_MODE_FULL    = "full"      # PIPELINE inteiro
EXEC_MODE_PARTIAL = "partial"   # subconjunto escolhido no menu "Por Fase"
EXEC_MODE_RESUMED = "resumed"   # retomada sobre runner-state.json
EXEC_MODE_MANUAL  = "manual"    # despacho avulso via --agent


def _utc_iso(ts: "float | None") -> str:
    """Epoch → ISO 8601 em UTC (sufixo Z). Vazio quando não há horário."""
    if not ts:
        return ""
    try:
        return (datetime.datetime
                .fromtimestamp(float(ts), datetime.timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"))
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _metric_epoch(value) -> "float | None":
    """Lê um timestamp epoch de origem não confiável; None se não for utilizável."""
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    return ts if ts > 0 else None


def _metric_int(value) -> int:
    """Coerção defensiva para contadores de token.

    `exec_metrics` chega de três origens com contratos diferentes: o retorno de
    `run_step`, os dicts sintéticos de degradação e o JSON desserializado de uma
    retomada. Um ``None`` ou uma string em qualquer uma delas não pode virar
    ``TypeError`` no fecho do run.
    """
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _metric_float(value) -> float:
    try:
        return round(max(0.0, float(value or 0.0)), 3)
    except (TypeError, ValueError):
        return 0.0


def _hhmmss(seconds) -> str:
    """Segundos → HH:MM:SS. Acompanha `duration_seconds` em todo bloco.

    Sem truncar em 24h: uma esteira completa passa de um dia com folga, e
    `26:41:03` é legível — `02:41:03` seria mentira.
    """
    try:
        total = int(max(0.0, float(seconds or 0.0)))
    except (TypeError, ValueError):
        total = 0
    horas, resto = divmod(total, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def _phase_metric_status(phase: str, metrics: dict, executed: list,
                         skipped: list, aborted: list, val_failed: list) -> str:
    """Traduz o estado interno da fase para o vocabulário do relatório.

    A ordem dos testes é a precedência: uma fase degradada está em `executed`,
    e uma abortada pode estar em `val_failed` — o rótulo mais específico ganha.
    """
    if phase in aborted:
        return "aborted"
    if metrics.get("degraded"):
        return "degraded"
    if phase in val_failed:
        return "validation_failed"
    if phase in skipped:
        return "skipped"
    if phase in executed:
        return "executed" if metrics.get("val_ok", True) else "degraded"
    return "not_executed"


def execution_status_label(executed: list, skipped: list, aborted: list,
                           val_failed: list, *, completed: bool) -> str:
    """Veredito do run inteiro, na mesma escala usada por fase."""
    if aborted:
        return "aborted"
    if not completed:
        return "interrupted"
    if val_failed or skipped or _DEGRADATIONS:
        return "completed_with_warnings"
    return "completed"


def build_execution_metrics(
    *,
    execution_id: str = "",
    project_name: str = "",
    execution_mode: str = "",
    execution_status: str = "",
    start_ts: "float | None" = None,
    end_ts: "float | None" = None,
    exec_metrics: "dict | None" = None,
    executed: "list | None" = None,
    skipped: "list | None" = None,
    aborted: "list | None" = None,
    val_failed: "list | None" = None,
) -> dict:
    """Monta o documento de métricas. Função pura: não toca disco.

    Todos os parâmetros têm default justamente para que `build_execution_metrics()`
    sem argumento nenhum produza o documento vazio — é o fallback que garante o
    arquivo mesmo quando o estado do run é inutilizável.

    `token_in`/`token_out`/`total_tokens` e `total_hours` aparecem com os mesmos
    nomes no bloco do run e no de cada fase: quem soma ou agrega lê os dois
    níveis com o mesmo código.
    """
    executed   = [str(p) for p in (executed or [])]
    skipped    = [str(p) for p in (skipped or [])]
    aborted    = [str(p) for p in (aborted or [])]
    val_failed = [str(p) for p in (val_failed or [])]

    phase_rows: list[dict] = []
    total_in = 0
    total_out = 0

    for phase, raw in (exec_metrics or {}).items():
        metrics = raw if isinstance(raw, dict) else {}
        token_in  = _metric_int(metrics.get("inp_tokens"))
        token_out = _metric_int(metrics.get("resp_tokens"))
        total_in  += token_in
        total_out += token_out

        # `started_ts`/`ended_ts` só existem para fases que passaram por
        # `run_step`. Degradação e task bloqueada montam o dict à mão, sem
        # horário: aí o único dado real é `elapsed_s`, e o timestamp fica vazio.
        phase_start = _metric_epoch(metrics.get("started_ts"))
        phase_end   = _metric_epoch(metrics.get("ended_ts"))
        if phase_start and phase_end:
            duration = _metric_float(phase_end - phase_start)
        else:
            duration = _metric_float(metrics.get("elapsed_s"))

        phase_rows.append({
            "phase_name": str(phase),
            "status": _phase_metric_status(str(phase), metrics, executed,
                                           skipped, aborted, val_failed),
            "start_time_utc": _utc_iso(phase_start),
            "end_time_utc": _utc_iso(phase_end),
            "duration_seconds": duration,
            "total_hours": _hhmmss(duration),
            "token_usage": {
                "total_tokens": token_in + token_out,
                "token_in": token_in,
                "token_out": token_out,
            },
        })

    _start = _metric_epoch(start_ts)
    _end   = _metric_epoch(end_ts)
    if _start and _end:
        total_duration = _metric_float(_end - _start)
    else:
        # Sem os dois extremos, a soma das fases é a melhor aproximação
        # disponível — melhor que zerar um run que de fato consumiu tempo.
        total_duration = _metric_float(sum(r["duration_seconds"] for r in phase_rows))

    return {
        "execution_id": str(execution_id or ""),
        "project_name": str(project_name or ""),
        "execution_mode": str(execution_mode or ""),
        "execution_status": str(execution_status or ""),
        "start_time_utc": _utc_iso(_start),
        "end_time_utc": _utc_iso(_end),
        "total_duration_seconds": total_duration,
        "total_hours": _hhmmss(total_duration),
        "token_metrics": {
            "total_tokens": total_in + total_out,
            "token_in": total_in,
            "token_out": total_out,
        },
        "phase_metrics": phase_rows,
    }


# ── Histórico acumulado ─────────────────────────────────────────────────────
# O arquivo é o registro PERMANENTE de todas as execuções do projeto — esteira
# completa, fase avulsa, retomada e despacho por `--agent`. Iniciar uma
# execução nunca apaga o que já está lá: a execução corrente entra como uma
# entrada nova em `execution_history`, e a mesma fase rodada duas vezes aparece
# duas vezes, uma sob cada execução.
#
# As chaves do topo continuam sendo as da execução CORRENTE, na mesma ordem de
# sempre, para quem já lê o arquivo sem checar campo novo. O histórico e o
# consolidado do projeto entram depois.
HISTORY_KEY = "execution_history"
SUMMARY_KEY = "history_summary"


def _metrics_file_path(project: str) -> "Path":
    return (WORKSPACE / "projects" / str(project) / "outputs" / "pipeline_runner"
            / METRICS_FILENAME)


def _execution_view(document: dict) -> dict:
    """O bloco da execução sem o histórico — é o que vira entrada do histórico."""
    return {k: v for k, v in document.items() if k not in (HISTORY_KEY, SUMMARY_KEY)}


def _read_metrics_history(target: "Path") -> list:
    """Lê as execuções já registradas. Nunca levanta e nunca descarta calado.

    Três formatos podem estar em disco:

    * o formato atual, com `execution_history` — devolvido como está;
    * o formato antigo, com uma execução única no topo — promovido à primeira
      entrada do histórico, para que atualizar o runner não custe o passado;
    * um arquivo ilegível — renomeado para `.corrupted-<epoch>` antes de
      recomeçar, porque perder histórico em silêncio é exatamente o defeito que
      este código existe para não repetir.
    """
    try:
        if not target.exists():
            return []
        bruto = target.read_text(encoding="utf-8")
    except Exception:                                         # noqa: BLE001
        return []

    try:
        doc = json.loads(bruto)
    except Exception:                                         # noqa: BLE001
        try:
            target.replace(target.with_name(
                f"{target.stem}.corrupted-{int(time.time())}{target.suffix}"))
        except Exception:                                     # noqa: BLE001
            pass
        return []

    if not isinstance(doc, dict):
        return []
    historico = doc.get(HISTORY_KEY)
    if isinstance(historico, list):
        return [e for e in historico if isinstance(e, dict)]

    anterior = _execution_view(doc)
    if anterior.get("execution_id") or anterior.get("phase_metrics"):
        return [anterior]
    return []


def _merge_execution_history(anteriores: list, atual: dict) -> list:
    """Insere ou atualiza a execução corrente sem tocar nas anteriores.

    A chave é `execution_id`. Um mesmo run grava várias vezes — na largada, a
    cada fase pelo flush, e no fecho — e todas essas gravações são A MESMA
    execução, que só evolui de `running` para o veredito final; por isso a
    entrada é substituída no lugar. Execuções distintas têm id distinto, e é
    isto que faz a fase rodada avulsa depois da esteira completa somar ao
    histórico em vez de substituí-lo.

    Sem `execution_id` não há como identificar a entrada, então ela é anexada:
    duplicar uma linha é menos grave que sobrescrever a errada.
    """
    exec_id = str(atual.get("execution_id") or "")
    historico = [dict(e) for e in anteriores]
    if exec_id:
        for i, entrada in enumerate(historico):
            if str(entrada.get("execution_id") or "") == exec_id:
                historico[i] = atual
                return historico
    historico.append(atual)
    return historico


def _summarize_history(historico: list) -> dict:
    """Consolidado do projeto: o custo total e quantas vezes cada fase rodou.

    `phase_history` é a leitura que o histórico existe para permitir — uma
    linha por fase, com a contagem de execuções e o acumulado de tempo e token
    somados por todas elas.
    """
    token_in = token_out = 0
    duracao_total = 0.0
    inicios: "list[str]" = []
    fins: "list[str]" = []
    fases: "dict[str, dict]" = {}

    for entrada in historico:
        tokens = entrada.get("token_metrics") or {}
        token_in  += _metric_int(tokens.get("token_in"))
        token_out += _metric_int(tokens.get("token_out"))
        duracao_total += _metric_float(entrada.get("total_duration_seconds"))
        if entrada.get("start_time_utc"):
            inicios.append(str(entrada["start_time_utc"]))
        if entrada.get("end_time_utc"):
            fins.append(str(entrada["end_time_utc"]))

        for linha in entrada.get("phase_metrics") or []:
            if not isinstance(linha, dict):
                continue
            nome = str(linha.get("phase_name") or "")
            uso = linha.get("token_usage") or {}
            acc = fases.setdefault(nome, {
                "phase_name": nome,
                "executions": 0,
                "last_status": "",
                "total_duration_seconds": 0.0,
                "total_hours": "00:00:00",
                "token_usage": {"total_tokens": 0, "token_in": 0, "token_out": 0},
            })
            acc["executions"] += 1
            acc["last_status"] = str(linha.get("status") or "")
            acc["total_duration_seconds"] = _metric_float(
                acc["total_duration_seconds"]
                + _metric_float(linha.get("duration_seconds")))
            acc["total_hours"] = _hhmmss(acc["total_duration_seconds"])
            acc["token_usage"]["token_in"]  += _metric_int(uso.get("token_in"))
            acc["token_usage"]["token_out"] += _metric_int(uso.get("token_out"))
            acc["token_usage"]["total_tokens"] = (acc["token_usage"]["token_in"]
                                                  + acc["token_usage"]["token_out"])

    duracao_total = _metric_float(duracao_total)
    return {
        "total_executions": len(historico),
        "first_start_time_utc": min(inicios) if inicios else "",
        "last_end_time_utc": max(fins) if fins else "",
        "total_duration_seconds": duracao_total,
        "total_hours": _hhmmss(duracao_total),
        "token_metrics": {
            "total_tokens": token_in + token_out,
            "token_in": token_in,
            "token_out": token_out,
        },
        "phase_history": list(fases.values()),
    }


def write_execution_metrics(project: str, **kwargs) -> "Path | None":
    """Atualiza `pipeline-runner-metrics.json`. Nunca apaga, nunca propaga exceção.

    O arquivo é criado na primeira execução do projeto e daí em diante só é
    ATUALIZADO: a execução corrente é inserida no histórico (ou atualizada no
    lugar, quando é a mesma que já está registrada) e nenhuma execução anterior
    é removida — vale para os quatro modos, inclusive a fase avulsa iniciada
    depois de uma esteira completa.

    Se a montagem falhar, ainda assim grava o documento vazio: o critério é que
    o arquivo exista com a estrutura certa em toda execução, e um relatório
    zerado é informação — um arquivo ausente é ambiguidade.
    """
    # `project_name` sai do mesmo argumento que decide o diretório de destino:
    # documento e caminho não têm como divergir.
    kwargs.setdefault("project_name", str(project or ""))
    try:
        document = build_execution_metrics(**kwargs)
    except Exception as exc:                                  # noqa: BLE001
        print(f"{YELLOW}  [METRICS-WARN] Métricas incompletas ({type(exc).__name__}: "
              f"{exc}); gravando documento vazio.{RESET}")
        try:
            document = build_execution_metrics(project_name=str(project or ""))
        except Exception:                                     # noqa: BLE001
            return None

    try:
        target = _metrics_file_path(project)
        target.parent.mkdir(parents=True, exist_ok=True)

        historico = _merge_execution_history(_read_metrics_history(target), document)
        arquivo = dict(document)
        arquivo[SUMMARY_KEY] = _summarize_history(historico)
        arquivo[HISTORY_KEY] = historico

        # Grava em arquivo temporário e renomeia: o rename é atômico, então uma
        # queda no meio da escrita deixa o histórico anterior intacto em vez de
        # um JSON truncado que a próxima leitura teria de descartar.
        parcial = target.with_name(target.name + ".tmp")
        parcial.write_text(
            json.dumps(arquivo, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        parcial.replace(target)
        return target
    except Exception as exc:                                  # noqa: BLE001
        print(f"{YELLOW}  [METRICS-WARN] Não foi possível gravar "
              f"{METRICS_FILENAME}: {type(exc).__name__}: {exc}{RESET}")
        return None


def flush_execution_metrics(project: str, executed: list, skipped: list,
                            aborted: list, exec_metrics: dict,
                            val_failed: "list | None" = None,
                            *, status: str = "running") -> "Path | None":
    """Atualiza o relatório no meio do run, para acompanhamento.

    Chamada de dentro de `_save_runner_state`: aquele é o ponto que a esteira
    já usa para marcar todo avanço — fase concluída, degradada, pulada, tool
    reprovada — então as métricas herdam a cadência do estado sem espalhar
    chamadas por doze call sites.

    `execution_id`, `execution_mode` e `start_ts` vêm de `_RUN_CTX` porque
    `_save_runner_state` não os recebe; os contadores vêm dos argumentos, que
    são as referências vivas do laço.
    """
    if _RUN_CTX.get("finalized"):
        return None
    return write_execution_metrics(
        project,
        execution_id=_RUN_CTX.get("execution_id", ""),
        execution_mode=_RUN_CTX.get("execution_mode", ""),
        execution_status=status,
        start_ts=_RUN_CTX.get("start_ts"),
        end_ts=time.time(),
        exec_metrics=exec_metrics,
        executed=executed, skipped=skipped, aborted=aborted,
        val_failed=val_failed,
    )


def write_metrics_from_run_ctx(status: str) -> "Path | None":
    """Grava as métricas quando o runner termina fora do caminho feliz.

    `_RUN_CTX` guarda as MESMAS referências de lista e dict que o laço muta, de
    modo que aqui está o estado real do ponto de interrupção. Sem isto, um
    Ctrl+C descartava todo o consumo de token já pago no run.

    Não faz nada se o caminho feliz já gravou (`finalized`) ou se a interrupção
    veio antes de a esteira começar (sem `project` no contexto).
    """
    try:
        if _RUN_CTX.get("finalized"):
            return None
        project = _RUN_CTX.get("project")
        if not project:
            return None
        return write_execution_metrics(
            project,
            execution_id=_RUN_CTX.get("execution_id", ""),
            execution_mode=_RUN_CTX.get("execution_mode", ""),
            execution_status=status,
            start_ts=_RUN_CTX.get("start_ts"),
            end_ts=time.time(),
            exec_metrics=_RUN_CTX.get("metrics"),
            executed=_RUN_CTX.get("executed"),
            skipped=_RUN_CTX.get("skipped"),
            aborted=_RUN_CTX.get("aborted"),
            val_failed=_RUN_CTX.get("val_failed"),
        )
    except Exception:                                         # noqa: BLE001
        return None


def _load_runner_state(project: str) -> "dict | None":
    """Carrega estado anterior de execução, se existir e for válido."""
    path = _runner_state_path(project)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"{YELLOW}  [RESUME-WARN] Estado anterior corrompido ({exc}); ignorando.{RESET}")
        return None

    required = {"project", "active_phases", "executed", "skipped", "aborted",
                "exec_metrics", "last_index"}
    if not required.issubset(data.keys()):
        print(f"{YELLOW}  [RESUME-WARN] Estado anterior incompleto; ignorando.{RESET}")
        return None
    if data.get("project") != project:
        print(f"{YELLOW}  [RESUME-WARN] Estado anterior pertence a outro projeto; ignorando.{RESET}")
        return None
    # val_failed é campo opcional — estados gravados antes desta versão não o têm.
    data.setdefault("val_failed", [])
    return data


def _save_runner_state(
    project: str,
    active_steps: list[dict],
    executed: list[str],
    skipped: list[str],
    aborted: list[str],
    exec_metrics: dict,
    idx: int,
    val_failed: "list[str] | None" = None,
) -> None:
    """Persiste o estado atual da execução em runner-state.json."""
    path = _runner_state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "project": project,
        "run_id": f"runner19-{int(time.time())}",
        "active_phases": [_phase_identity(s) for s in active_steps],
        "executed": list(executed),
        "skipped": list(skipped),
        "aborted": list(aborted),
        "val_failed": list(val_failed or []),
        # Fases que rodaram e ficaram como executadas apesar de um problema.
        # Sem isto a retomada não teria como avisar que há pendência: o estado
        # só guardava executado/pulado/abortado, e uma degradação é executada.
        "degraded": list(_DEGRADATIONS),
        "exec_metrics": _serialize_metrics(exec_metrics),
        "last_index": idx,
        "saved_at": datetime.datetime.now().isoformat(),
    }
    try:
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"{YELLOW}  [RESUME-WARN] Não foi possível salvar estado: {exc}{RESET}")

    # Acompanhamento: o relatório de métricas segue o mesmo passo do estado.
    # Fica FORA do try acima de propósito — falhar ao gravar o estado não é
    # motivo para deixar o consumo do run sem registro, e vice-versa.
    flush_execution_metrics(project, executed, skipped, aborted,
                            exec_metrics, val_failed)


def _finalize_runner_state(project: str, success: bool) -> None:
    """Renomeia o estado para '-done.json' ao concluir com sucesso.

    Em aborto (``success=False``) o arquivo permanece como ``runner-state.json``
    — é dele que ``_load_runner_state`` lê na próxima invocação para oferecer
    retomada. Antes desta correção, a linha abaixo movia o arquivo para
    ``-done.json`` incondicionalmente: uma execução abortada (ex.: exit gate da
    F3S reprovado) ficava sem estado de retomada, e o próximo `pipeline_runner`
    não encontrava nada para oferecer — a mensagem "Re-execução via --resume
    irá repetir este passo" era falsa, e o operador via forçado a recomeçar a
    esteira inteira do zero.
    """
    if not success:
        return
    src = _runner_state_path(project)
    dst = _runner_state_path(project, done=True)
    if not src.exists():
        return
    try:
        import shutil
        shutil.move(str(src), str(dst))
        print(f"{DIM}  [RESUME] Estado arquivado: {dst.name}{RESET}")
    except Exception as exc:
        print(f"{YELLOW}  [RESUME-WARN] Não foi possível arquivar estado: {exc}{RESET}")


def _headroom_py() -> str:
    """Retorna o Python do venv do headroom ou 'python' como fallback."""
    return str(HEADROOM_VENV_PY) if HEADROOM_VENV_PY.exists() else "python"


def headroom_proxy_url() -> str:
    """Obtém a URL efetiva do proxy headroom via headroom_config.py."""
    try:
        result = subprocess.run(
            [_headroom_py(), str(HEADROOM_CFG), "--proxy-url"],
            capture_output=True, text=True, timeout=5
        )
        url = result.stdout.strip()
        return url if url.startswith("http") else HEADROOM_DEFAULT_URL
    except Exception:
        return HEADROOM_DEFAULT_URL


def headroom_proxy_alive(proxy_url: str) -> bool:
    """Verifica se o proxy headroom está respondendo.
    KeyboardInterrupt nunca é capturado aqui — propaga normalmente.
    """
    try:
        r = _requests.get(proxy_url.rstrip("/"), timeout=3)
        return r.status_code < 500
    except KeyboardInterrupt:
        raise
    except Exception:
        pass
    # Fallback: usa headroom_tool.py proxy status — só se o exe existir
    if not HEADROOM_TOOL.exists():
        return False
    try:
        result = subprocess.run(
            [_headroom_py(), str(HEADROOM_TOOL), "proxy", "status"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except KeyboardInterrupt:
        raise
    except Exception:
        return False


def headroom_install() -> bool:
    """Instala o headroom via setup.ps1 se o exe não existir.
    Retorna True se a instalação foi bem-sucedida.
    """
    setup_ps1 = WORKSPACE / "src" / "shared" / "tools" / "headroom" / "setup.ps1"
    if not setup_ps1.exists():
        print(f"  {RED}❌  setup.ps1 não encontrado em {setup_ps1}{RESET}")
        return False
    print(f"  {CYAN}⚙️  Instalando headroom via setup.ps1 (pode levar 1–2 min)...{RESET}")
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(setup_ps1), "-SkipML"],
            cwd=str(WORKSPACE),
            timeout=300,
        )
        if result.returncode == 0 and HEADROOM_EXE.exists():
            print(f"  {GREEN}✅  headroom instalado com sucesso.{RESET}")
            return True
        print(f"  {RED}❌  setup.ps1 retornou {result.returncode} ou exe não foi criado.{RESET}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  {RED}❌  Timeout na instalação do headroom (>5 min).{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}❌  Erro ao instalar headroom: {e}{RESET}")
        return False


def headroom_start_proxy(proxy_url: str) -> "subprocess.Popen | None":
    """Sobe o proxy headroom em background.
    Se o exe não existir, tenta instalar via setup.ps1 primeiro.
    Se o proxy já estiver respondendo na porta (de uma sessão anterior),
    retorna um sentinel sem lançar novo processo.
    Retorna o processo (ou _HEADROOM_ALREADY_RUNNING) ou None se falhar.
    """
    # ── Verificação rápida: proxy já está na porta? ───────────────
    # (pode ter ficado de uma sessão anterior — usar sem lançar novo)
    if headroom_proxy_alive(proxy_url):
        print(f"  {GREEN}✅  Proxy já respondia na porta — reutilizando.{RESET}")
        return _HEADROOM_ALREADY_RUNNING  # type: ignore[return-value]

    # ── Instala se necessário ─────────────────────────────────────
    if not HEADROOM_EXE.exists():
        print(f"  {YELLOW}⚠️  headroom.exe não encontrado — iniciando instalação automática...{RESET}")
        if not headroom_install():
            return None

    # ── Inicia o proxy (até 3 tentativas) ────────────────────────
    from urllib.parse import urlparse
    parsed = urlparse(proxy_url)
    host   = parsed.hostname or "127.0.0.1"
    port   = parsed.port or 8787

    MAX_ATTEMPTS = 3
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            print(f"  {YELLOW}  ↩  Tentativa {attempt}/{MAX_ATTEMPTS} de subir o proxy...{RESET}")
        proc: "subprocess.Popen | None" = None
        try:
            proc = subprocess.Popen(
                [str(HEADROOM_EXE), "proxy", "--host", host, "--port", str(port), "--no-http2"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(WORKSPACE),
            )
            print(f"  {DIM}  Aguardando proxy subir (até 60s)...{RESET}")
            alive = False
            for i in range(120):
                time.sleep(0.5)
                # Aborta cedo se o processo crashou — não espera 
                # s à toa
                if proc.poll() is not None:
                    print(f"  {RED}  ❌  Processo encerrou inesperadamente "
                          f"(rc={proc.returncode}, tentativa {attempt}/{MAX_ATTEMPTS}).{RESET}")
                    break
                if headroom_proxy_alive(proxy_url):
                    alive = True
                    break
                if i > 0 and i % 20 == 0:
                    print(f"  {DIM}  ... {i // 2}s aguardando...{RESET}")
            if alive:
                return proc
            print(f"  {YELLOW}  ⚠️  Proxy não respondeu (tentativa {attempt}/{MAX_ATTEMPTS}).{RESET}")
        except FileNotFoundError:
            # Exe sumiu entre o exists() e o Popen — não adianta tentar de novo
            print(f"  {RED}❌  headroom.exe não encontrado: {HEADROOM_EXE}{RESET}")
            return None
        except Exception as e:
            print(f"  {RED}❌  Erro ao iniciar proxy (tentativa {attempt}/{MAX_ATTEMPTS}): {e}{RESET}")
        finally:
            # Garante que o processo é encerrado e a porta liberada antes do próximo retry
            if proc is not None and alive is False:  # type: ignore[possibly-undefined]
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    pass
        if attempt < MAX_ATTEMPTS:
            time.sleep(2)  # pausa para SO liberar a porta antes de retentar

    print(f"  {RED}❌  Proxy não iniciou após {MAX_ATTEMPTS} tentativas.{RESET}")
    return None


# Sentinel usado quando o proxy já estava rodando antes de ser lançado
_HEADROOM_ALREADY_RUNNING = object()


def _headroom_client_url(proxy_url: str) -> str:
    """Retorna a base URL do cliente para a rota do provider selecionado.
    OpenAI usa /v1 (Chat Completions); Anthropic usa a root do proxy.
    """
    if PROVIDER == "openai":
        return f"{proxy_url.rstrip('/')}/v1"
    return proxy_url.rstrip("/")


def _headroom_proxy_env() -> dict:
    """Monta o ambiente do proxy com o upstream correto para o provider."""
    env = os.environ.copy()
    env["AVA_FOUNDRY_MODEL"] = DEPLOYMENT
    if PROVIDER == "openai":
        env["OPENAI_TARGET_API_URL"] = ENDPOINT_OPENAI
    else:
        env["ANTHROPIC_TARGET_API_URL"] = ENDPOINT
    return env


def foundry_tcp_probe(host: str = "", port: int = 443,
                      timeout_s: float = 5.0) -> "tuple[bool, str]":
    """Testa alcance TCP real ao endpoint do Foundry.

    DNS resolvendo não prova nada. Com o túnel VPN zumbi — interface up, rotas
    10.x instaladas, split-DNS respondendo — o nome resolve para o IP privado,
    o SYN sai e nada volta. O preflight antigo parava no ``gethostbyname`` e
    imprimia "VPN ativa" enquanto a esteira morria 90s depois num timeout do
    SDK que não apontava para lugar nenhum. Só o ``connect()`` revela.

    Usa ``socket.getaddrinfo`` já com o DNS patch aplicado, então testa
    exatamente o IP que o SDK vai usar.

    Devolve ``(ok, detalhe)``: no sucesso o detalhe é o IP; na falha, o motivo.
    """
    host = host or "aif-imf-apps-prd-eus2-001.services.ai.azure.com"
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        ip = infos[0][4][0]
    except Exception as e:                                    # noqa: BLE001
        return False, f"DNS falhou ({type(e).__name__}: {e})"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_s)
    try:
        sock.connect((ip, port))
        return True, ip
    except socket.timeout:
        return False, (f"{ip}:{port} não respondeu em {timeout_s:.0f}s — "
                       f"SYN sem resposta (túnel VPN caído ou Private Endpoint bloqueado)")
    except OSError as e:                                      # ConnectionRefused, no route...
        return False, f"{ip}:{port} {type(e).__name__}: {e}"
    finally:
        sock.close()


def explain_foundry_unreachable(detalhe: str) -> str:
    """Mensagem de remediação para quando o endpoint privado não responde.

    Centralizada porque três pontos falham pelo mesmo motivo (listagem de
    modelos, ping de auth via headroom, ping de auth direto) e antes cada um
    contava uma história diferente do mesmo problema.
    """
    return (
        f"{RED}  ❌ Endpoint do Foundry inalcançável — {detalhe}{RESET}\n"
        f"  {DIM}O DNS privado pode estar OK e mesmo assim o túnel estar morto:{RESET}\n"
        f"  {DIM}interface e rotas ficam instaladas depois que a sessão VPN cai.{RESET}\n"
        f"\n"
        f"  {BOLD}Verifique, nesta ordem:{RESET}\n"
        f"  {DIM}1. Feche o Azure VPN Client e mate instâncias órfãs:{RESET}\n"
        f"     {CYAN}Get-Process AzVpnAppx | Stop-Process -Force{RESET}\n"
        f"  {DIM}2. Conecte a VPN corporativa (GlobalProtect) antes da P2S da Azure.{RESET}\n"
        f"  {DIM}3. Reconecte vnet-core-eus2-001 e valide o plano de dados:{RESET}\n"
        f"     {CYAN}Test-NetConnection 10.26.2.12 -Port 443{RESET}\n"
        f"  {DIM}Se o TCP continuar falhando com a VPN recém-conectada, o problema{RESET}\n"
        f"  {DIM}é do lado Azure (Private Endpoint / NSG da vnet-core), não da máquina.{RESET}"
    )


# Motivos das falhas de listagem de modelos — preenchido por
# `_fetch_foundry_models`, consumido por `_select_model_interactive`.
# Existe porque os `except Exception: pass` abaixo transformavam um timeout de
# rede num lacônico "não foi possível confirmar modelos", sem causa nenhuma.
_FOUNDRY_PROBE_ERRORS: list[str] = []


def _fetch_foundry_models(api_key: str) -> list[dict]:
    """Lista deployments realmente disponíveis no Foundry do tenant.

    Fonte de verdade: GET /openai/deployments?api-version=2023-03-15-preview
    (retorna deployments do recurso, ex.: Kimi/Luna/GLM/MiniMax/Claude).

    Fallback: se a listagem falhar, tenta ping por Anthropic em alguns Claude
    conhecidos para manter compatibilidade com ambientes restritos.
    """
    base = "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com"
    _FOUNDRY_PROBE_ERRORS.clear()

    try:
        r = _requests.get(
            f"{base}/openai/deployments",
            headers={"api-key": api_key},
            params={"api-version": "2023-03-15-preview"},
            timeout=12,
        )
        if r.status_code != 200:
            _FOUNDRY_PROBE_ERRORS.append(
                f"GET /openai/deployments → HTTP {r.status_code} {r.reason}")
        if r.status_code == 200:
            payload = r.json() if "application/json" in r.headers.get("content-type", "") else {}
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            if isinstance(rows, list):
                found: list[dict] = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    status = str(row.get("status", "")).lower()
                    # Mostra apenas deployments prontos para uso.
                    if status and status not in ("succeeded", "ready", "running"):
                        continue

                    dep_id = str(row.get("id") or "").strip()
                    model = str(row.get("model") or dep_id).strip()
                    if not dep_id:
                        continue

                    is_claude = "claude" in dep_id.lower() or "claude" in model.lower()
                    found.append({
                        "id": dep_id,
                        "model": model,
                        "provider": "anthropic" if is_claude else "openai",
                        "lifecycle_status": "generally-available" if status == "succeeded" else "preview",
                        "headroom_ok": True,  # headroom suporta todos os providers (anthropic + openai)
                    })

                if found:
                    return found
                _FOUNDRY_PROBE_ERRORS.append(
                    "GET /openai/deployments → 200, mas nenhum deployment pronto na resposta")
    except Exception as e:                                    # noqa: BLE001
        _FOUNDRY_PROBE_ERRORS.append(
            f"GET /openai/deployments → {type(e).__name__}: {e}")

    # Fallback conservador (mantém comportamento anterior para Claude).
    candidates = ["claude-sonnet-4-6", "claude-opus-4-6"]
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    base_payload = {"max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}

    fallback: list[dict] = []
    for model_id in candidates:
        try:
            r = _requests.post(
                f"{base}/anthropic/v1/messages",
                headers=headers,
                json={**base_payload, "model": model_id},
                timeout=8,
            )
            if r.status_code == 200:
                fallback.append({
                    "id": model_id,
                    "model": model_id,
                    "provider": "anthropic",
                    "lifecycle_status": "generally-available",
                    "headroom_ok": True,
                })
            else:
                _FOUNDRY_PROBE_ERRORS.append(
                    f"ping {model_id} → HTTP {r.status_code} {r.reason}")
        except Exception as e:                                # noqa: BLE001
            _FOUNDRY_PROBE_ERRORS.append(f"ping {model_id} → {type(e).__name__}: {e}")

    return fallback


def _select_model_interactive(api_key: str) -> str:
    """Exibe menu de modelos do Foundry, retorna o id escolhido e seta PROVIDER global."""
    global PROVIDER

    print(f"\n{BOLD}[Foundry]{RESET} Buscando modelos disponíveis...", end="", flush=True)

    # Sonda TCP antes das chamadas HTTP: com o endpoint inalcançável, a
    # listagem e os dois pings de fallback custam 28s de timeouts para chegar
    # à mesma conclusão que um connect() entrega em 5.
    _ok, _detalhe = foundry_tcp_probe(timeout_s=5.0)
    if not _ok:
        print(f"\n  {YELLOW}⚠️  Não foi possível confirmar modelos — usando padrão: {DEPLOYMENT}{RESET}")
        print()
        print(explain_foundry_unreachable(_detalhe))
        return DEPLOYMENT

    models = _fetch_foundry_models(api_key)

    if not models:
        print(f"\n  {YELLOW}⚠️  Não foi possível confirmar modelos — usando padrão: {DEPLOYMENT}{RESET}")
        for _motivo in _FOUNDRY_PROBE_ERRORS:
            _txt = _motivo if len(_motivo) <= 180 else _motivo[:177] + "..."
            print(f"  {DIM}     ↳ {_txt}{RESET}")
        # TCP responde mas a listagem falhou: é credencial ou permissão, não rede.
        print(f"  {DIM}     TCP 443 OK — provável falta de permissão da API Key "
              f"para listar deployments.{RESET}")
        return DEPLOYMENT

    print(f" {len(models)} modelo(s) confirmado(s) no seu Foundry.")

    # Com apenas 1 modelo disponível, não há escolha — usa direto
    if len(models) == 1:
        print(f"  {GREEN}✅ Único modelo disponível: {models[0]['id']}{RESET}")
        PROVIDER = models[0]["provider"]
        return models[0]["id"]

    print(f"\n{BOLD}Modelos disponíveis no seu Foundry:{RESET}")

    for i, m in enumerate(models, 1):
        prov_tag    = f"{CYAN}[Anthropic]{RESET}" if m["provider"] == "anthropic" else f"{YELLOW}[OpenAI]   {RESET}"
        hr_tag      = f"  {GREEN}[Headroom ✅]{RESET}" if m["headroom_ok"] else f"  {YELLOW}[Headroom ❌]{RESET}"
        life_tag    = f"  {DIM}preview{RESET}" if m["lifecycle_status"] == "preview" else ""
        default_tag = f"  {GREEN}← padrão{RESET}" if m["id"] == DEPLOYMENT else ""
        base_hint   = f" {DIM}({m['model']}){RESET}" if m["model"] != m["id"] else ""
        print(f"  {CYAN}{i:>3}.{RESET} {prov_tag} {m['id']:<35}{base_hint}{hr_tag}{life_tag}{default_tag}")

    default_idx = next((i + 1 for i, m in enumerate(models) if m["id"] == DEPLOYMENT), 1)

    while True:
        raw = safe_input(f"\n{BOLD}Selecione o modelo [1-{len(models)}, Enter={default_idx}={DEPLOYMENT}]: {RESET}").strip()
        if raw == "":
            chosen = models[default_idx - 1]
        elif raw.isdigit() and 1 <= int(raw) <= len(models):
            chosen = models[int(raw) - 1]
        else:
            print(f"  {RED}Opção inválida. Digite 1-{len(models)} ou Enter para o padrão.{RESET}")
            continue
        PROVIDER = chosen["provider"]
        print(f"  {DIM}  Provider detectado: {PROVIDER}{RESET}")
        return chosen["id"]


def setup_headroom_mode(project: str) -> "tuple[str, subprocess.Popen | None]":
    """
    Sobe o proxy headroom automaticamente (sem perguntar ao usuário).
    Funciona tanto para Claude (Anthropic) quanto para Luna/GPT (OpenAI).
    O proxy é configurado com o upstream correto via _headroom_proxy_env().
    Retorna (base_url_a_usar, processo_proxy_ou_None).
    """
    proxy_url = headroom_proxy_url()
    print(f"\n{BOLD}[Headroom]{RESET} Iniciando proxy em {proxy_url}...")
    print(f"  {DIM}  Provider: {PROVIDER} | Deployment: {DEPLOYMENT}{RESET}")

    # Inicia o proxy passando o ambiente correto para o provider
    if headroom_proxy_alive(proxy_url):
        print(f"  {GREEN}✅  Proxy já respondia na porta — reutilizando.{RESET}")
        proc = None  # não gerenciamos ciclo de vida de proxy externo
    else:
        if not HEADROOM_EXE.exists():
            print(f"  {YELLOW}⚠️  headroom.exe não encontrado — iniciando instalação automática...{RESET}")
            if not headroom_install():
                _fallback = ENDPOINT if PROVIDER == "anthropic" else ENDPOINT_OPENAI
                print(f"  {YELLOW}  ⚠️  Headroom indisponível — continuando com endpoint direto.{RESET}")
                return _fallback, None
        try:
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            proc = subprocess.Popen(
                [str(HEADROOM_EXE), "proxy",
                 "--host", parsed.hostname or "127.0.0.1",
                 "--port", str(parsed.port or 8787),
                 "--no-http2"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(WORKSPACE),
                env=_headroom_proxy_env(),
            )
            print(f"  {DIM}  Aguardando proxy subir (até 60s)...{RESET}")
            alive = False
            for i in range(120):
                time.sleep(0.5)
                if headroom_proxy_alive(proxy_url):
                    alive = True
                    break
            if not alive:
                proc.terminate()
                _fallback = ENDPOINT if PROVIDER == "anthropic" else ENDPOINT_OPENAI
                print(f"  {YELLOW}  ⚠️  Proxy não respondeu — continuando com endpoint direto.{RESET}")
                return _fallback, None
        except Exception as e:
            _fallback = ENDPOINT if PROVIDER == "anthropic" else ENDPOINT_OPENAI
            print(f"  {RED}❌  Erro ao iniciar proxy: {e} — continuando com endpoint direto.{RESET}")
            return _fallback, None

    if proc is not None:
        print(f"{GREEN}  ✅ Proxy iniciado (PID {proc.pid}) em {proxy_url}{RESET}")
    else:
        print(f"{GREEN}  ✅ Proxy ativo em {proxy_url}{RESET}")

    client_url = _headroom_client_url(proxy_url)
    upstream = ENDPOINT if PROVIDER == "anthropic" else ENDPOINT_OPENAI
    print(f"  {DIM}  Modo: headroom comprime contexto → {client_url} → {upstream}{RESET}")
    return client_url, proc


# ── Mapa de skill override para agentes com workflow multi-arquivo ───────────
# Agentes cujo "agente real" é composto por vários arquivos (workflow + steps)
# precisam de override explícito, pois a busca genérica por maior .md pega
# o arquivo errado (ex: ava-summary pega summary-validate-agent.md em vez do
# workflow de geração).
#
# Formato: agent_name → lista de paths relativos ao WORKSPACE, em ordem.
# Os arquivos são concatenados e entregues ao modelo como skill completo.
AGENT_SKILL_OVERRIDE: dict[str, list[str]] = {
    # ava-summary: workflow multi-arquivo (CLI usa Read() encadeado; runner injeta diretamente)
    # summary-agent.md vem primeiro: carrega os schemas D.*, mapeamento de fontes por fase e
    # instruções de timing NTP — essencial quando o LLM fallback é ativado (builder falhou).
    # Sem ele, o LLM improvisa o HTML sem seguir o protocolo do builder.
    "ava-summary": [
        "src/modules/ava-fabric-agents/summary/agents/summary-agent.md",
        "src/modules/ava-fabric-agents/summary/workflows/generate-summary/workflow.md",
        "src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-01-discover.md",
        "src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-02-extract.md",
        "src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-03-build-html.md",
        "src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-04-validate-deliver.md",
    ],
    # ava-summary-remediation: stub de 716 bytes aponta para o agente real via Read()
    "ava-summary-remediation": [
        "src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md",
    ],
    # ava-summary-validate: agente de validação — usa skill dedicado (não o workflow de geração)
    "ava-summary-validate": [
        "src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md",
    ],
}
# ────────────────────────────────────────────────────────────────────────────


def _load_summary_html_template() -> str:
    """Carrega o template HTML do Summary Avanade para injeção no system prompt.
    Retorna string vazia se o arquivo não existir (degradação segura).
    O template é necessário para que o modelo gere o HTML no formato correto —
    sem ele, o modelo produz HTML genérico sem o design Avanade.
    """
    template_path = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                     / "summary" / "templates" / "html" / "summary-template.html")
    if not template_path.exists():
        print(f"  {YELLOW}  [summary] Template HTML não encontrado: {template_path.relative_to(WORKSPACE)}{RESET}")
        return ""
    content = template_path.read_text(encoding="utf-8", errors="ignore")
    kb = len(content) // 1024
    print(f"  {DIM}  [summary] Template HTML carregado: {kb}KB{RESET}")
    return content


def load_skill(agent_name: str, spec_path: "str | Path | None" = None) -> str:
    """Lê o SKILL.md do agente.
    Precedência:
      0.  AGENT_SKILL_OVERRIDE — lista explícita de arquivos (workflow multi-parte)
      0.5 spec_path resolvido pelo agent_registry — só quando o CHAMADOR já
          identificou o agente (caminho --agent). O modo interativo passa None
          e a precedência abaixo fica idêntica à original.
      1. .github/skills/{agent}/SKILL.md  — se tiver > 2 KB (não é stub)
      2. src/modules/ava-fabric-agents/** — busca recursiva pelo agent_name
      3. .github/skills stub              — fallback (mesmo que pequeno)
    """
    STUB_THRESHOLD = 2_000  # bytes — stubs têm ~600-1900 bytes

    # 0) Override explícito — agentes com workflow multi-arquivo
    if agent_name in AGENT_SKILL_OVERRIDE:
        parts_content: list[str] = []
        for rel_path in AGENT_SKILL_OVERRIDE[agent_name]:
            fpath = WORKSPACE / rel_path
            if fpath.exists():
                parts_content.append(
                    f"## {fpath.name}\n\n"
                    + fpath.read_text(encoding="utf-8", errors="ignore")
                )
                print(f"  {DIM}  [skill] {fpath.name}  ({fpath.stat().st_size//1024}KB){RESET}")
            else:
                print(f"  {YELLOW}  [skill] MISSING: {rel_path}{RESET}")
        if parts_content:
            combined = "\n\n---\n\n".join(parts_content)
            if len(combined) > CTX_SKILL:
                combined = combined[:CTX_SKILL] + "\n\n[... skill truncado no limite de contexto ...]"
            return combined

    # 0.5) Spec canônica resolvida pelo chamador.
    #
    # A precedência 2 abaixo acha o agente por HEURÍSTICA de substring e escolhe
    # o maior arquivo candidato — defeito documentado em
    # docs/guia-ava-pipeline-cli.md:2734 ("pode carregar o agente errado"). Para
    # o despacho por --agent isso seria fatal: resolveríamos o agente certo pelo
    # registry e carregaríamos o skill de outro.
    #
    # Fica em 0.5, e não em 0, porque AGENT_SKILL_OVERRIDE é curadoria explícita
    # multi-arquivo: para esses agentes a spec única do registry é mais pobre.
    if spec_path:
        _spec = Path(spec_path)
        if _spec.is_file():
            content = _spec.read_text(encoding="utf-8", errors="ignore")
            if len(content) > CTX_SKILL:
                content = content[:CTX_SKILL] + "\n\n[... skill truncado ...]"
            print(f"  {DIM}  [skill] registry: {_spec.name} "
                  f"({_spec.stat().st_size // 1024}KB){RESET}")
            return content
        print(f"  {YELLOW}  [skill] spec_path inexistente: {spec_path} — "
              f"caindo na busca heurística{RESET}")

    # 1) SKILL wrapper
    skill_file = SKILLS_PATH / agent_name / "SKILL.md"
    if skill_file.exists() and skill_file.stat().st_size >= STUB_THRESHOLD:
        content = skill_file.read_text(encoding="utf-8", errors="ignore")
        if len(content) > CTX_SKILL:
            content = content[:CTX_SKILL] + "\n\n[... skill truncado ...]"
        return content

    # 2) Agente real em src/modules/ava-fabric-agents/
    agents_root = WORKSPACE / "src" / "modules" / "ava-fabric-agents"
    slug       = agent_name.replace("ava-", "")   # ex: devops-containerize
    slug_parts = slug.split("-")                   # ex: ['devops','containerize']
    # Segmentos "funcionais" = sem prefixos de namespace comuns (devops, asis, tobe, qa, stack)
    _NAMESPACE_PREFIXES = {"devops", "asis", "tobe", "qa", "stack", "ava"}
    functional_parts = [p for p in slug_parts if p not in _NAMESPACE_PREFIXES]
    # Último segmento funcional (ex: 'containerize', 'podman') — suficiente para encontrar o agente
    last_part = slug_parts[-1] if slug_parts else slug

    # Exclui APENAS stems que são variantes do summary (validate/remediation)
    # para evitar que 'summary' pague 'summary-validate-agent' / 'summary-remediation-agent'.
    # A exclusão genérica de '-agent' foi removida: excluía 52 agentes reais.
    EXCLUSION_SUFFIXES = ("-validate-agent", "-remediation-agent")

    # Scoring de match: candidatos com match mais específico têm prioridade sobre tamanho.
    # Nível 4 (melhor) = slug exato no stem / stem no slug
    # Nível 3          = todos slug_parts presentes no stem
    # Nível 2          = todos functional_parts presentes no stem (sem namespace)
    # Nível 1 (mínimo) = last_part presente no stem (≥5 chars para evitar falsos positivos)
    # Ordenação: (nível DESC, tamanho DESC) → melhor match semântico primeiro
    candidates: list[tuple[int, int, "Path"]] = []
    if agents_root.exists():
        for md in agents_root.rglob("*.md"):
            stem = md.stem.lower()
            if any(stem.endswith(s) for s in EXCLUSION_SUFFIXES):
                continue
            level = 0
            if slug in stem or stem in slug:
                level = 4
            elif len(slug_parts) > 1 and all(p in stem for p in slug_parts):
                level = 3
            elif functional_parts and len(functional_parts) > 1 and all(p in stem for p in functional_parts):
                level = 2
            elif last_part and len(last_part) >= 5 and last_part in stem:
                level = 1
            if level > 0:
                candidates.append((level, md.stat().st_size, md))

    if candidates:
        # Ordena por (nível DESC, tamanho DESC): match semântico tem prioridade sobre tamanho
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best = candidates[0][2]   # tupla (level, size, path)
        content = best.read_text(encoding="utf-8", errors="ignore")
        if len(content) > CTX_SKILL:
            content = content[:CTX_SKILL] + "\n\n[... skill truncado no limite de contexto ...]"
        print(f"  {DIM}  [skill] Usando agente real: {best.relative_to(WORKSPACE)}{RESET}")
        return content

    # 3) Fallback: stub do .github/skills
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8", errors="ignore")

    return f"[SKILL.md não encontrado para {agent_name}]"


class MissingMandatoryInput(Exception):
    """Insumo obrigatório declarado no DAG não encontrado em disco.

    Exceção própria — e deliberadamente **não** ``SystemExit``. O laço principal
    captura ``Exception``; ``SystemExit`` herda de ``BaseException`` e escapava do
    handler, derrubando o processo sem gravar `runner-state.json`, sem fechar o
    dashboard e sem oferecer retry/pulo ao operador (ISSUE-004).
    """

    def __init__(self, message: str, phase: str = "", agent: str = "",
                 missing: "list[str] | None" = None):
        super().__init__(message)
        self.phase   = phase
        self.agent   = agent
        self.missing = missing or []


class TruncatedResponse(Exception):
    """Resposta cortada por ``max_tokens`` deixando artefato incompleto."""


# ── Diagnóstico de falha de passo ────────────────────────────────────────────
# Antes, um passo que falhava imprimia só `❌ Erro no passo X: <str(exc)>`. Sem
# traceback não dava para localizar o ponto da falha, e sem tradução da causa o
# operador tinha de inferir qual agente ou ferramenta regerar. Cada tool tem uma
# causa raiz característica; mapeá-la aqui evita uma rodada de investigação.
_ROOT_CAUSES: list[tuple[str, str, str]] = [
    # (fragmento procurado na fase/erro, causa raiz, próximo passo concreto)
    ("não foi possível derivar nenhum bounded context",
     "O architecture-blueprint.md não contém um formato de bounded contexts "
     "reconhecido pelo scaffold. Regere a F2 e confirme o mapa de contexts "
     "antes de repetir a F4S.",
     "python src/shared/tools/scaffold_runner.py --project {project} --json"),
    ("nao foi possivel derivar bounded contexts",
     "O architecture-blueprint.md não contém um formato de bounded contexts "
     "reconhecido pelo scaffold. Regere a F2 e confirme o mapa de contexts "
     "antes de repetir a F4S.",
     "python src/shared/tools/scaffold_runner.py --project {project} --json"),
    ("speckit-plan-validate",
     "Um ou mais plan-graph.json estão semanticamente incoerentes — grupo sem "
     "arquivos, consumo sem produtor ou produces contaminado. O relatório acima "
     "lista cada achado com sua causa.",
     "python src/shared/tools/speckit_task_compiler.py diagnose "
     "-p {project} --plans-only"),
    ("speckit-task-compile",
     "Plano e fragment não fecham: arquivo sem task, task fora do plano, ou "
     "cabeçalhos divergentes. O compilador para no primeiro erro; o diagnóstico "
     "lista todos de uma vez.",
     "python src/shared/tools/speckit_task_compiler.py diagnose -p {project}"),
    ("speckit-entry-gate",
     "Artefatos exigidos para ENTRAR na F3S não existem — a fase anterior (F2/F3) "
     "não completou seu contrato de saída.",
     "python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py "
     "-p {project} --gate entry --json"),
    ("speckit-exit-gate",
     "A F3S não fechou seu contrato de saída; a F4 fica bloqueada.",
     "python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py "
     "-p {project} --gate exit --json"),
    ("speckit-dependency-checks",
     "O grafo de tasks tem referência inválida, ciclo ou rastreabilidade "
     "incompleta.",
     "python -m src.shared.checks -p {project} --suite speckit_traceability"),
    ("f4s-scaffold-inject",
     "Não foi possível derivar os scaffolds: target_stack ausente em "
     "project-config.yaml → tobe_stack, ou spec de scaffold inexistente.",
     "python src/shared/tools/f4s_scaffold_injector.py -p {project} --json"),
    ("speckit-fragment-repair",
     "O reparador determinístico de fragments não pôde normalizar os pares "
     "plan-graph.json/task-fragment.json — diretório ausente, JSON inválido "
     "ou inconsistência não recuperável.",
     "python src/shared/tools/speckit_fragment_repair.py -p {project} --json "
     "--allow-orphans"),
    ("speckit-wave-manifest",
     "O wave-model.json / wave-plan.md não produz um manifesto válido — waves "
     "duplicadas, BCs divergentes ou dependência para wave inexistente.",
     "python src/shared/tools/speckit_wave_manifest.py -p {project} --json"),
    ("speckit-ledger-init",
     "O ledger não pôde ser inicializado a partir do traceability.json.",
     "python src/shared/tools/task_ledger.py -p {project} --init --json"),
    ("speckit-compliance-normalize",
     "ava-speckit-compliance não gravou compliance-status.json no schema "
     "canônico (viu-se escrever compliance-summary.json com o schema da F7) e "
     "nenhum arquivo compliance-*.json reconhecível existe para normalizar. "
     "O wave7 (exit gate) vai reprovar em seguida por este mesmo motivo.",
     "python src/shared/tools/speckit_compliance_normalize.py -p {project} --json"),
]


#: Exit code que uma tool usa para dizer "reprovei, mas só por lacuna de
#: qualidade". Espelha `Reporter.SOFT_FAIL_EXIT` em src/shared/checks/reporter.py.
#: Qualquer outro código não-zero é falha estrutural e aborta a fase.
SOFT_FAIL_EXIT = 3


# ── Gate de aprovação humana (F3S wave6c) ────────────────────────────────────
# Prazo do prompt opcional em modo automático. Curto o bastante para não atrasar
# uma execução agendada, longo o bastante para quem está olhando o terminal
# conseguir assinar.
_APROVACAO_TIMEOUT_S = 30


def _ler_gate_aprovacao(project: str) -> "dict | None":
    """Lê `compliance-gate.json`, o relatório que a wave6c acabou de gravar."""
    caminho = (Path("projects") / project / "outputs" / "tobe" / "speckit"
               / "compliance-gate.json")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dados if isinstance(dados, dict) else None


def _registrar_decisao(project: str, decisao: str, *, nome: str = "",
                       papel: str = "", modo: str = "manual",
                       fingerprint: str = "") -> bool:
    """Invoca a tool de gate para gravar a decisão. True quando registrou."""
    comando = [
        sys.executable, "src/shared/tools/speckit_compliance_gate.py",
        "--project", project, f"--{decisao}", "--mode", modo, "--json",
    ]
    if nome:
        comando += ["--name", nome]
    if papel:
        comando += ["--role", papel]
    if fingerprint:
        comando += ["--fingerprint", fingerprint]
    try:
        proc = subprocess.run(comando, cwd=str(WORKSPACE), timeout=120, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"  {RED}Não foi possível registrar a decisão: {exc}{RESET}")
        return False
    return proc.returncode == 0


def _painel_aprovacao(gate: dict) -> None:
    """Mostra os achados. Impresso nos DOIS modos — dar ciência é o ponto."""
    print(f"\n{YELLOW}{BOLD}{'═' * 72}{RESET}")
    print(f"{YELLOW}{BOLD}  ⚠️  CIÊNCIA NECESSÁRIA ANTES DE LIBERAR A F4{RESET}")
    print(f"{YELLOW}  Veredito do agente de conformidade: "
          f"{gate.get('verdict')}{RESET}")
    print(f"{YELLOW}{BOLD}{'═' * 72}{RESET}")
    print(f"\n  {BOLD}Motivos:{RESET}")
    for motivo in gate.get("triggers") or []:
        print(f"    • [{motivo.get('code')}] {motivo.get('detail')}")
    blockers = gate.get("blockers") or []
    if blockers:
        print(f"\n  {BOLD}Achados de severidade alta/crítica "
              f"({len(blockers)}):{RESET}")
        for item in blockers:
            print(f"    {RED}─ {item.get('id')} [{item.get('severity')}]{RESET} "
                  f"{item.get('summary')}")
            if item.get("evidence"):
                print(f"{DIM}        evidência: {item['evidence']}{RESET}")
            if item.get("remediation"):
                print(f"{DIM}        correção:  {item['remediation']}{RESET}")
    print(f"\n  {DIM}Relatório completo: "
          f"outputs/tobe/speckit/compliance-report.md{RESET}")


def _coletar_identidade(timeout_s: "int | None") -> "tuple[str, str] | None":
    """Coleta Nome e Papel. ``None`` quando não vieram.

    Com ``timeout_s``, cada campo é opcional e o estouro devolve ``None`` — é o
    caminho do modo automático, onde a esteira não pode ficar pendurada. Sem
    prazo, os campos são obrigatórios e o prompt insiste: uma assinatura anônima
    não registra responsabilidade, que é o único motivo de o gate existir.
    """
    def _perguntar(rotulo: str) -> "str | None":
        while True:
            if timeout_s is not None:
                valor = safe_input_timeout(
                    f"  {BOLD}{rotulo}{RESET} {DIM}(opcional){RESET}: ", timeout_s)
                return valor.strip() if valor else None
            valor = safe_input(f"  {BOLD}{rotulo}{RESET}: ").strip()
            if len(valor) >= 2:
                return valor
            print(f"  {DIM}Informe ao menos 2 caracteres.{RESET}")

    try:
        nome = _perguntar("Nome")
        if not nome:
            return None
        papel = _perguntar("Papel/Função")
        if not papel:
            return None
    except (EOFError, KeyboardInterrupt):
        return None
    return nome, papel


def _solicitar_aprovacao(project: str, gate: dict, auto_mode: bool) -> bool:
    """Conduz a decisão sobre os achados. True para seguir, False para parar.

    A assimetria entre os modos é deliberada. Em MANUAL há uma pessoa a quem
    perguntar e a decisão dela vale — inclusive para parar a esteira. Em
    AUTOMÁTICO não há: perguntar é uma cortesia com prazo, e o silêncio vira
    `auto_acknowledged`, que registra honestamente que ninguém revisou em vez de
    inventar um aprovador.
    """
    _painel_aprovacao(gate)
    fingerprint = str(gate.get("fingerprint") or "")

    if auto_mode:
        print(f"\n{YELLOW}  [AUTO] Execução automática — a esteira NÃO será "
              f"bloqueada.{RESET}")
        print(f"  {DIM}Se quiser assinar esta liberação, informe Nome e Papel "
              f"em até {_APROVACAO_TIMEOUT_S}s. Em branco, segue sem "
              f"revisor nomeado.{RESET}\n")
        identidade = _coletar_identidade(_APROVACAO_TIMEOUT_S)
        if identidade:
            nome, papel = identidade
            if _registrar_decisao(project, "approve", nome=nome, papel=papel,
                                  modo="auto", fingerprint=fingerprint):
                print(f"  {GREEN}✅ Liberação assinada por {nome} ({papel}).{RESET}")
                return True
            print(f"  {YELLOW}Registro nominal falhou — seguindo como "
                  f"reconhecimento automático.{RESET}")
        _registrar_decisao(project, "acknowledge", modo="auto",
                           fingerprint=fingerprint)
        print(f"  {YELLOW}⚠️  Seguindo sem revisão humana. O compliance registra "
              f"`auto_acknowledged`.{RESET}")
        return True

    print(f"\n  {BOLD}Seguindo, você assume estes achados{RESET} e sua "
          f"identificação fica gravada em compliance-status.json.")
    print(f"  {DIM}Recusando, a esteira para aqui, o estado é salvo e a F4 "
          f"permanece bloqueada.{RESET}")
    while True:
        try:
            resp = safe_input(
                f"\n{BOLD}  Aprovar e liberar a F4? [S]im / [N]ão: {RESET}"
            ).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{RED}  Entrada interrompida — não aprovado.{RESET}")
            return False

        if resp in ("S", "SIM"):
            identidade = _coletar_identidade(None)
            if not identidade:
                print(f"  {YELLOW}Identificação não informada — nada foi "
                      f"aprovado.{RESET}")
                return False
            nome, papel = identidade
            if not _registrar_decisao(project, "approve", nome=nome, papel=papel,
                                      modo="manual", fingerprint=fingerprint):
                print(f"  {RED}A decisão não pôde ser registrada; por segurança, "
                      f"a F4 permanece bloqueada.{RESET}")
                return False
            print(f"  {GREEN}✅ Aprovado por {nome} ({papel}). F4 liberada.{RESET}")
            return True

        if resp in ("N", "NAO", "NÃO"):
            identidade = _coletar_identidade(None)
            if identidade:
                nome, papel = identidade
                _registrar_decisao(project, "reject", nome=nome, papel=papel,
                                   modo="manual", fingerprint=fingerprint)
                print(f"  {CYAN}Recusado por {nome} ({papel}). "
                      f"Corrija os achados e reexecute.{RESET}")
            else:
                print(f"  {CYAN}Recusa sem identificação — nada foi gravado, "
                      f"mas a F4 continua bloqueada.{RESET}")
            return False

        print(f"  {DIM}Responda S ou N.{RESET}")


def _confirmar_risco(step: dict, auto_mode: bool) -> bool:
    """Pergunta ao operador se segue apesar da tool ter reprovado.

    Só é chamada para tool marcada com ``on_fail: confirm`` no DAG — aquela cuja
    reprovação é informação de qualidade do que foi gerado, não corrupção de
    artefato. O relatório completo da tool já foi impresso pelo subprocess, e o
    bloco de causa raiz veio logo antes; aqui só resta a decisão.

    Devolve True para seguir assumindo o risco, False para cancelar e corrigir.
    Em modo automático não há a quem perguntar: segue, mas grita, e a aceitação
    fica registrada no estado como automática.
    """
    fase = str(step.get("phase") or "?")
    print(f"\n{YELLOW}{'─' * 72}{RESET}")
    print(f"{YELLOW}{BOLD}  {fase} REPROVOU — decisão do operador{RESET}")
    print(f"{YELLOW}{'─' * 72}{RESET}")
    print(f"  Esta verificação é {BOLD}não-bloqueante por configuração{RESET} "
          f"(on_fail: confirm no DAG).")
    print(f"  O relatório completo está acima. Ela reprova por lacuna de "
          f"qualidade —")
    print(f"  não impede a fase seguinte de executar, mas o que faltou "
          f"continuará faltando.")
    print(f"\n  {BOLD}Seguindo, você assume o risco{RESET} e a aceitação fica "
          f"registrada em runner-state.json.")
    print(f"  {DIM}Cancelando, a esteira para aqui e você corrige antes de "
          f"reexecutar.{RESET}")

    if auto_mode:
        print(f"\n{YELLOW}  [AUTO] Modo automático — seguindo com o risco "
              f"aceito automaticamente.{RESET}")
        return True

    while True:
        try:
            resp = safe_input(
                f"\n{BOLD}  Seguir assumindo o risco? "
                f"[S]im / [N]ão (cancelar para corrigir): {RESET}").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{RED}  Entrada interrompida — cancelando por segurança.{RESET}")
            return False
        if resp in ("S", "SIM"):
            print(f"  {YELLOW}⚠️  Risco aceito. Prosseguindo com a lacuna "
                  f"registrada.{RESET}")
            return True
        if resp in ("N", "NAO", "NÃO"):
            print(f"  {CYAN}Cancelado. Corrija os itens acima e reexecute a "
                  f"fase.{RESET}")
            return False
        print(f"  {DIM}Responda S ou N.{RESET}")


# ── Gate de artefatos OPCIONAIS ausentes ─────────────────────────────────────
# Vários agentes declaram um pre-flight com artefatos OPCIONAIS e mandam pedir
# confirmação quando algum falta. Dentro de uma chamada single-shot isso não
# funciona: o modelo pergunta, ninguém pode responder, e a fase encerra sem
# gerar nada — foi exatamente a F3 do nopcommerce-02 (12,5 s, 636 tokens, 0
# artefatos, e ainda assim `val_ok=True`). A decisão passa a ser tomada AQUI,
# antes do despacho, por quem tem console: pergunta-se com prazo, e o silêncio
# aprova. O agente recebe a decisão pronta e nunca chega a perguntar.
_OPCIONAIS_TIMEOUT_S = 60

#: agente -> [(caminho relativo ao projeto, impacto de gerar sem ele)].
#: Espelha o pre-flight declarado no corpo do agente. Só artefato OPCIONAL
#: entra aqui: obrigatório ausente é bloqueio, e quem confere isso é
#: `preflight_step_inputs` — este gate nunca deixa passar o que aquele barra.
_ARTEFATOS_OPCIONAIS: dict[str, list[tuple[str, str]]] = {
    "ava-prototype": [
        ("outputs/tobe/docs/bounded-context-map.md",
         "Módulos derivados direto das seções de business-rules.md; "
         "navegação simplificada para menu plano."),
        ("outputs/tobe/docs/design-system.md",
         "Tokens de design genéricos; cores de marca e biblioteca de "
         "componentes não aplicadas."),
        ("outputs/tobe/docs/user-journeys.md",
         "Telas derivadas apenas das regras de negócio; fluxos multi-etapa, "
         "happy/sad path e navegação não modelados com precisão."),
        ("outputs/tobe/docs/api-map.md",
         "Mapeamento tela→endpoint derivado de openapi/*.yaml quando existir."),
    ],
}

#: Injetado no prompt quando a confirmação foi concedida. Sem este bloco o
#: agente reexecuta o pre-flight do próprio corpo e volta a perguntar.
_DIRETRIZ_OPCIONAIS = """## PRE-FLIGHT JÁ RESOLVIDO PELO RUNNER — NÃO PERGUNTE NADA

O runner conferiu os artefatos no disco antes deste despacho. Os OPCIONAIS
abaixo estão ausentes:

{lista}

A confirmação exigida pelo pre-flight do seu corpo **JÁ FOI CONCEDIDA** ({modo}).

DECISÃO: **PROSSEGUIR COM AVISOS** — execute a geração completa agora.

- ❌ NÃO exiba a pergunta "Continuar mesmo sem os artefatos opcionais? [sim/não]"
- ❌ NÃO encerre a resposta aguardando confirmação — não existe segundo turno
- ✅ Aplique, para cada ausente, o fallback declarado no seu corpo
- ✅ Gere TODOS os artefatos do Output Contract em blocos <!-- FILE: ... -->
- ✅ Registre a degradação nos artefatos de saída (ex.: `design-input-traceability.json`)
"""


def _opcionais_ausentes(agent: str, project: str) -> list[tuple[str, str]]:
    """Os opcionais declarados do agente que não estão no disco.

    Arquivo vazio conta como ausente pelo mesmo motivo de
    `validate_declared_outputs`: bloco truncado grava arquivo inútil.
    """
    raiz = WORKSPACE / "projects" / project
    ausentes: list[tuple[str, str]] = []
    for rel, impacto in _ARTEFATOS_OPCIONAIS.get(agent, []):
        alvo = raiz / rel
        try:
            presente = alvo.is_file() and alvo.stat().st_size > 0
        except OSError:
            presente = False
        if not presente:
            ausentes.append((rel, impacto))
    return ausentes


def _painel_opcionais(agent: str, phase: str,
                      ausentes: list[tuple[str, str]]) -> None:
    """Mostra o que falta e o que isso custa. Impresso sempre — dar ciência
    é o ponto, inclusive quando o prazo expira e ninguém leu."""
    print(f"\n{YELLOW}{BOLD}{'═' * 72}{RESET}")
    print(f"{YELLOW}{BOLD}  ⚠️  PRE-FLIGHT {phase} — {len(ausentes)} artefato(s) "
          f"OPCIONAL(is) ausente(s){RESET}")
    print(f"{YELLOW}  Agente: {agent}{RESET}")
    print(f"{YELLOW}{BOLD}{'═' * 72}{RESET}")
    for rel, impacto in ausentes:
        print(f"    {YELLOW}⚠️  {rel}{RESET}")
        print(f"{DIM}        impacto: {impacto}{RESET}")
    print(f"\n  {BOLD}Seguindo{RESET}, a fase gera com os fallbacks do agente "
          f"— qualidade reduzida, entrega completa.")
    print(f"  {DIM}Recusando, a fase é cancelada e nada é gerado; regere os "
          f"artefatos acima e reexecute.{RESET}")


def confirmar_opcionais_ausentes(agent: str, project: str,
                                 phase: str) -> "tuple[bool, str]":
    """Decide, ANTES do despacho, se a fase roda sem os artefatos opcionais.

    Devolve `(prosseguir, diretriz)`. `diretriz` é o bloco que entra no prompt
    para o agente não repetir a pergunta; vem vazio quando não falta nada.

    O prazo de `_OPCIONAIS_TIMEOUT_S` vale nos dois modos de confirmação. Em
    manual há alguém para responder; em automático perguntar é cortesia com
    cronômetro. Nos dois, o silêncio aprova: a alternativa é a esteira parar
    esperando uma resposta que, numa chamada single-shot, nunca poderia chegar.
    """
    ausentes = _opcionais_ausentes(agent, project)
    if not ausentes:
        return True, ""

    _painel_opcionais(agent, phase, ausentes)
    print(f"  {DIM}Sem resposta em {_OPCIONAIS_TIMEOUT_S}s, a aprovação é "
          f"automática e a esteira segue gerando.{RESET}")

    try:
        resposta = safe_input_timeout(
            f"\n{BOLD}  Continuar sem os artefatos opcionais? "
            f"[S]im / [N]ão: {RESET}", _OPCIONAIS_TIMEOUT_S)
    except EOFError:
        resposta = None                      # sem console: ninguém a quem perguntar
    except KeyboardInterrupt:
        print(f"\n{RED}  Interrompido pelo operador — fase cancelada.{RESET}")
        return False, ""

    if resposta is None:
        modo = "aprovação automática por decurso de prazo — ninguém respondeu "
        modo += f"em {_OPCIONAIS_TIMEOUT_S}s"
        print(f"  {YELLOW}⏱️  [AUTO] Sem resposta em {_OPCIONAIS_TIMEOUT_S}s — "
              f"aprovado automaticamente. Gerando com os fallbacks.{RESET}")
    elif resposta.strip().upper() in ("N", "NAO", "NÃO"):
        print(f"  {CYAN}Cancelado pelo operador. Regere os artefatos acima e "
              f"reexecute {phase}.{RESET}")
        return False, ""
    else:
        modo = "confirmado pelo operador no console"
        print(f"  {GREEN}✅ Confirmado — gerando com os fallbacks do agente.{RESET}")

    lista = "\n".join(f"- `{rel}` — {impacto}" for rel, impacto in ausentes)
    return True, _DIRETRIZ_OPCIONAIS.format(lista=lista, modo=modo)



def _numero_no_menu(fase: str) -> str:
    """Posição da fase no menu 'Por Fase', para instruir sem o operador adivinhar."""
    base = fase.split(":", 1)[0]
    for indice, chave in enumerate(PHASE_GROUPS, start=1):
        if base == chave or base in (PHASE_GROUPS[chave].get("phases") or []):
            return f"{indice}   ({PHASE_GROUPS[chave]['label']})"
    return f"(fase {base} — não listada no menu)"


def _produtor_declarado(caminho: str) -> str:
    """Quem produz este artefato, segundo os DAGs e o `ava-pipeline.yaml`.

    O `produced_by` **já existe** — declarado nos itens de gate de
    `pipeline-dag/*.yaml` e nos `inputs.mandatory` do `ava-pipeline.yaml`. Nunca
    havia sido usado para responder ao operador na hora do erro.
    """
    alvo = caminho.replace("\\", "/").strip()
    if not alvo:
        return ""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return ""

    def _varre(node) -> str:
        if isinstance(node, dict):
            candidatos = [str(node.get("path") or "")]
            candidatos += [str(p) for p in (node.get("paths") or [])]
            # O alvo pode chegar como caminho completo (vindo de um item de gate)
            # ou só como nome de arquivo (extraído do texto de uma exceção). Casa
            # nos dois sentidos, sempre em fronteira de segmento para que
            # `plan.md` não case com `wave-plan.md`.
            def _casa(declarado: str) -> bool:
                d = declarado.replace("\\", "/")
                if not d:
                    return False
                return (d == alvo
                        or alvo.endswith("/" + d) or d.endswith("/" + alvo))

            if node.get("produced_by") and any(_casa(p) for p in candidatos):
                return str(node["produced_by"])
            for valor in node.values():
                achado = _varre(valor)
                if achado:
                    return achado
        elif isinstance(node, list):
            for item in node:
                achado = _varre(item)
                if achado:
                    return achado
        return ""

    fontes = [WORKSPACE / "src" / "shared" / "data" / "ava-pipeline.yaml"]
    fontes += sorted((WORKSPACE / "src" / "shared" / "data" / "pipeline-dag").glob("*.yaml"))
    for fonte in fontes:
        try:
            achado = _varre(yaml.safe_load(fonte.read_text(encoding="utf-8")) or {})
        except Exception:  # noqa: BLE001 — diagnóstico jamais derruba a execução
            continue
        if achado:
            return achado
    return ""


def explicar_fase_nao_expandida(fase: str, project: str, exc: BaseException) -> str:
    """Erro tratado para fase que não pôde ser expandida por falta de insumo.

    Antes, `PlanError` subia cru até o topo: o operador via duas páginas de
    traceback terminando em "wave-model.json ausente", sem saber quem produz o
    arquivo, qual fase rodar, nem como conferir depois.

    As duas metades da resposta já existiam separadas — o gate de entrada sabe
    QUAIS itens faltam, o DAG declara QUEM produz cada um. Aqui elas se juntam.
    """
    faltantes: list[tuple[str, list[str], str]] = []
    L: list[str] = []
    try:
        _utils = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                  / "speckit" / "utils")
        if str(_utils) not in sys.path:
            sys.path.insert(0, str(_utils))
        import artifact_gate_speckit as _gate  # noqa: PLC0415
        _dag = _gate.load_dag()
        for item in _gate.gate_items("entry", _dag):
            if _gate.check_item(item, project, WORKSPACE)["present"]:
                continue
            caminhos = [str(p) for p in (item.get("paths") or [])] or [str(item.get("path"))]
            faltantes.append((str(item.get("path")), caminhos,
                              str(item.get("produced_by") or "")))
    except Exception as diag:  # noqa: BLE001
        L.append(f"  {DIM}(gate de entrada indisponível para detalhar: {diag}){RESET}")

    # Duas classes bem diferentes, que exigem instruções diferentes:
    #   ausente      — o artefato não existe; rode a fase que o produz;
    #   incoerente   — os artefatos existem e se contradizem; regere o artefato.
    ausente = bool(faltantes)
    titulo = ("insumo de fase anterior ausente" if ausente
              else "artefatos existem, mas são incoerentes entre si")
    L.insert(0, f"  motivo  : {exc}")
    L.insert(0, f"  projeto : {project}")
    L.insert(0, f"{RED}{'═' * 74}{RESET}")
    L.insert(0, f"{RED}{BOLD}  {fase} NÃO PÔDE SER EXPANDIDA — {titulo}{RESET}")
    L.insert(0, f"{RED}{'═' * 74}{RESET}")

    L.append("")
    L.append(f"{YELLOW}{BOLD}  CAUSA RAIZ{RESET}")
    citados: list[str] = []
    if ausente:
        L.append(f"{YELLOW}    A {fase} monta seus passos a partir de artefatos que fases")
        L.append(f"    anteriores deveriam ter produzido. Estes não existem em disco:{RESET}")
        for rotulo, caminhos, _p in faltantes:
            L.append(f"{YELLOW}      • {rotulo}{RESET}")
            # Rótulo igual ao único caminho é o caso comum; repetir vira ruído.
            if caminhos != [rotulo]:
                for c in caminhos:
                    L.append(f"{DIM}            {c}{RESET}")
    else:
        # Nada falta: o gate de entrada passou. O defeito é de CONTEÚDO, e os
        # arquivos envolvidos costumam estar nomeados na própria exceção.
        citados = sorted({n for n in re.findall(r"[\w./-]+\.(?:json|md|ya?ml)", str(exc))})
        L.append(f"{YELLOW}    Todos os artefatos exigidos pelo gate de entrada existem.")
        L.append(f"    O que falha é a COERÊNCIA entre eles — dois artefatos da mesma")
        L.append(f"    fase afirmam coisas diferentes:{RESET}")
        L.append(f"{YELLOW}      {exc}{RESET}")
        if citados:
            L.append(f"{DIM}      artefatos envolvidos: {', '.join(citados)}{RESET}")

    por_produtor: dict[str, list[str]] = {}
    for rotulo, caminhos, prod in faltantes:
        produtor = (prod or _produtor_declarado(caminhos[0])
                    or "(produtor não declarado no DAG)")
        por_produtor.setdefault(produtor, []).append(rotulo)
    for nome in citados:
        produtor = _produtor_declarado(nome) or "(produtor não declarado no DAG)"
        por_produtor.setdefault(produtor, []).append(nome)

    if por_produtor:
        L.append("")
        L.append(f"{CYAN}{BOLD}  QUEM PRODUZ (declarado no DAG){RESET}")
        for produtor, artefatos in sorted(por_produtor.items()):
            L.append(f"{CYAN}    {produtor}{RESET}")
            L.append(f"{DIM}          → {', '.join(artefatos)}{RESET}")

    # A fase produtora sai do próprio texto do `produced_by`: "… (F2, trigger CB)".
    fases = sorted({m for p in por_produtor for m in re.findall(r"\((F\d[A-Za-z]?)\b", p)})
    L.append("")
    L.append(f"{GREEN}{BOLD}  COMO CORRIGIR{RESET}")
    if fases:
        acao = ("Rode a(s) fase(s) produtora(s)" if ausente
                else "Regere o artefato divergente rodando a fase que o produz")
        L.append(f"{GREEN}    {acao}, e repita a {fase}:{RESET}")
        L.append("")
        numeros = [_numero_no_menu(f) for f in fases]
        # O menu aceita múltipla seleção ("ex: 1 3 5") — uma execução resolve todas.
        selecao = " ".join(n.split()[0] for n in numeros)
        L.append(f"{GREEN}      python \"ava-pipeline-runner-cli.py\"{RESET}")
        L.append(f"{DIM}        Selecione o projeto ... {project}{RESET}")
        L.append(f"{DIM}        Modo de execução ...... 2   (Por Fase){RESET}")
        L.append(f"{DIM}        Números das fases ..... {selecao}{RESET}")
        for n in numeros:
            L.append(f"{DIM}              {n}{RESET}")
        if not ausente:
            L.append("")
            L.append(f"{DIM}        Mais barato que regerar: editar à mão o artefato divergente")
            L.append(f"        para concordar com o outro. A incoerência é pontual.{RESET}")
    else:
        L.append(f"{GREEN}    Produza os artefatos listados acima e repita a {fase}.{RESET}")

    L.append("")
    L.append(f"{CYAN}{BOLD}  CONFERIR DEPOIS, SEM GASTAR INFERÊNCIA{RESET}")
    L.append(f"{CYAN}      python src/modules/ava-fabric-agents/speckit/utils/"
             f"artifact_gate_speckit.py \\{RESET}")
    L.append(f"{CYAN}             --project {project} --gate entry{RESET}")
    L.append(f"{RED}{'═' * 74}{RESET}")
    return "\n".join(L)


def explain_failure(step: dict, exc: BaseException, project: str) -> str:
    """Monta o bloco de erro: traceback completo + causa raiz + próximo passo."""
    fase = str(step.get("phase") or "?")
    agente = str(step.get("agent") or "?")
    partes: list[str] = []
    partes.append(f"{RED}{'═' * 72}{RESET}")
    partes.append(f"{RED}{BOLD}  FALHA EM {fase}{RESET}")
    partes.append(f"{RED}{'═' * 72}{RESET}")
    partes.append(f"  agente/tool : {agente}")
    partes.append(f"  exceção     : {type(exc).__name__}: {exc}")

    partes.append("")
    partes.append(f"{DIM}  ── trace ──{RESET}")
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
    partes.extend(f"{DIM}  {linha}{RESET}" for linha in tb.splitlines())

    alvo = f"{fase} {agente} {exc}".lower()
    causa = proximo = ""
    for chave, texto_causa, comando in _ROOT_CAUSES:
        if chave.lower() in alvo:
            causa, proximo = texto_causa, comando.format(project=project)
            break
    if not causa:
        if isinstance(exc, MissingMandatoryInput):
            causa = ("Insumo obrigatório declarado no DAG não existe em disco; o "
                     "passo produtor não rodou ou não gravou sua saída.")
            proximo = (f"python src/shared/tools/context_manifest.py -p {project} "
                       f"--phase {fase}")
        elif isinstance(exc, subprocess.TimeoutExpired):
            teto = getattr(exc, "timeout_s", None) or exc.timeout
            causa = (
                f"A etapa {fase} excedeu o teto de {int(float(teto))}s aplicado à "
                f"execução COMPLETA da tool — o processo e seus filhos foram "
                f"encerrados, e por isso o verifier não chegou a rodar. O teto "
                f"não é calculado por bounded context: é um limite fixo de "
                f"segurança. Os logs da tool já foram exibidos acima, ao vivo; "
                f"a última operação registrada mostra onde o processo parou.")
            proximo = (
                f"Ajuste \"timeout_s\" no nó {fase} do DAG (default global: "
                f"pipeline_plan.DEFAULT_TOOL_TIMEOUT_S) e re-execute; a "
                f"re-execução reaproveita o que já está em disco.")
            cauda = str(getattr(exc, "tail", "") or "")
            if cauda:
                causa += "\n\nÚltimas linhas da tool:\n" + cauda
        elif any(t in alvo for t in ("connection", "timeout", "overloaded",
                                     "rate limit", "502", "503", "504")):
            causa = ("Falha transitória de rede/API — as tentativas automáticas "
                     "se esgotaram.")
            proximo = "Reexecute o passo; se persistir, verifique o proxy headroom."
        else:
            causa = ("Sem causa raiz mapeada para este erro. O trace acima indica "
                     "o ponto exato da falha.")
            proximo = (f"Reexecute o passo. Se for da F3S, "
                       f"`speckit_task_compiler.py diagnose -p {project}` "
                       f"mostra o estado dos artefatos.")

    partes.append("")
    partes.append(f"{YELLOW}{BOLD}  CAUSA RAIZ{RESET}")
    for linha in textwrap.wrap(causa, width=68):
        partes.append(f"{YELLOW}    {linha}{RESET}")
    partes.append("")
    partes.append(f"{CYAN}{BOLD}  PRÓXIMO PASSO{RESET}")
    partes.append(f"{CYAN}    {proximo}{RESET}")
    partes.append(f"{RED}{'═' * 72}{RESET}")
    return "\n".join(partes)


def preflight_step_inputs(project: str, step: dict) -> "tuple[bool, str, list[str]]":
    """Confere `inputs.mandatory` do passo ANTES de gastar inferência.

    Este runner é o executor real da esteira; o preflight do CLI declarativo
    (`ava_pipeline.preflight_inputs`) nunca roda aqui. Sem esta checagem, a
    ausência só era descoberta dentro de `load_context`, já com o passo em
    despacho.

    Retorna ``(ok, mensagem, faltantes)``. Nunca levanta: falha de infraestrutura
    do manifesto degrada para ``ok=True`` e deixa `load_context` decidir (IV3).
    """
    declarado = (step or {}).get("inputs")
    if not declarado or _ctx_manifest is None:
        return True, "", []
    cfg = {"context": {"file_chars": CTX_FILE,
                       "declared_body_chars": ART_INJECT_CHARS * 5,
                       "declared_total_chars": 2_000_000},
           "execution": {"output_subdir": "outputs/pipeline_runner"}}
    try:
        res = _ctx_manifest.resolve(project, declarado, cfg, repo_root=WORKSPACE)
    except Exception as exc:  # noqa: BLE001 — manifesto quebrado não vira falso bloqueio
        print(f"  {YELLOW}⚠️  preflight indisponível para {step.get('phase','?')}: {exc}{RESET}")
        return True, "", []
    if not res.blocked:
        return True, "", []
    return (False,
            _ctx_manifest.format_missing(res, step.get("phase", "?"),
                                         step.get("agent", "?"), project),
            [m.pattern for m in res.missing_mandatory])


def load_context(project: str, step: dict | None = None) -> str:
    """Monta o contexto do passo.

    Com `inputs` declarado no passo, delega ao `context_manifest` — allowlist
    explícita, ordem de declaração, `.html` elegível, e insumo obrigatório
    ausente encerrando o passo antes de gastar inferência. Sem declaração, cai
    no caminho legado abaixo, preservado byte a byte.
    """
    declarado = (step or {}).get("inputs")
    if declarado and _ctx_manifest is not None:
        cfg = {"context": {"file_chars": CTX_FILE,
                           "declared_body_chars": ART_INJECT_CHARS * 5,
                           "declared_total_chars": 2_000_000},
               "execution": {"output_subdir": "outputs/pipeline_runner"}}
        res = _ctx_manifest.resolve(project, declarado, cfg, repo_root=WORKSPACE)
        if res.blocked:
            raise MissingMandatoryInput(
                _ctx_manifest.format_missing(
                    res, step.get("phase", "?"), step.get("agent", "?"), project),
                phase=str(step.get("phase", "")),
                agent=str(step.get("agent", "")),
                missing=[m.pattern for m in res.missing_mandatory])
        return _ctx_manifest.render(res)

    parts: list[str] = []
    proj_path = WORKSPACE / "projects" / project

    for fname in ("context/project-config.yaml", "context/shared-context.md"):
        fpath = proj_path / fname
        if fpath.exists():
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if len(text) > CTX_FILE:
                text = text[:CTX_FILE] + "\n[... truncado no limite de contexto ...]"
            parts.append(f"### {fname}\n```\n{text}\n```")

    # Injeta conteúdo dos artefatos AS-IS já gerados para enriquecer o contexto
    out_root = proj_path / "outputs"
    if out_root.exists():
        existing = []
        artifact_contents: list[str] = []
        for p in sorted(out_root.rglob("*")):
            if p.is_file() and "pipeline_runner" not in str(p):
                existing.append(str(p.relative_to(WORKSPACE)))
                # Injeta conteúdo de artefatos markdown/mmd para contexto rico
                if p.suffix in (".md", ".mmd", ".yaml", ".json"):
                    try:
                        art_text = p.read_text(encoding="utf-8", errors="ignore")
                        if art_text.strip():
                            artifact_contents.append(
                                f"### {p.relative_to(WORKSPACE)}\n```\n{art_text[:ART_INJECT_CHARS]}\n```"
                            )
                    except Exception:
                        pass
        if existing:
            parts.append("### Artefatos já existentes em outputs/\n" + "\n".join(existing[:CTX_ARTS]))
        if artifact_contents:
            parts.append("## Conteúdo dos Artefatos Gerados\n\n" + "\n\n".join(artifact_contents[:ART_INJECT_MAX]))

    return "\n\n".join(parts) if parts else "[Sem contexto disponível]"


_FILE_BLOCK = re.compile(
    r'<!--\s*FILE:\s*([^\n\r]+?)\s*-->\r?\n(.*?)<!--\s*/FILE\s*-->',
    re.DOTALL
)
# Captura WriteAllText("path", $content) do powershell gerado pelo agente
_WRITE_BLOCK = re.compile(
    r'WriteAllText\("([^"]+)",\s*(?:\$\w+|@\'.*?\'),',
    re.DOTALL
)
# Captura blocos de código markdown com caminho no comentário anterior
_MD_FILE_BLOCK = re.compile(
    r'```(?:json|yaml|markdown|md|text|[a-z]*)\s*\n# ([^\n]+\.(?:md|json|yaml|mmd))\n(.*?)```',
    re.DOTALL
)


def _resolve_path(rel_path: str, project: str):
    """Resolve um caminho relativo para Path absoluto dentro do projeto."""
    rp = rel_path.replace("\\\\", "/").replace("\\", "/")
    if rp.startswith("projects/"):
        return WORKSPACE / rp
    return WORKSPACE / "projects" / project / rp


def _is_safe_output_path(target: "Path", project: str) -> bool:
    """Garante que o path de saída está dentro de projects/{project}/.
    Impede crash por PermissionError/OSError se o modelo gerar paths
    fora do workspace (ex: src/modules/..., C:/Windows/..., /etc/...).
    Retorna False e imprime aviso se o path for inseguro.
    """
    safe_root = (WORKSPACE / "projects" / project).resolve()
    try:
        resolved = target.resolve()
        resolved.relative_to(safe_root)   # lança ValueError se fora
        return True
    except (ValueError, OSError):
        print(f"  {YELLOW}  [SKIP]  Path fora de projects/{project}/ — ignorado: {target}{RESET}")
        return False


def _write_output_body(target: Path, body: str, project: str) -> bool:
    """Write an extracted agent artifact, enforcing the Mermaid pre-write gate."""
    if not _is_safe_output_path(target, project):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() != ".mmd":
        target.write_text(body, encoding="utf-8")
        return True

    validator = WORKSPACE / "src" / "shared" / "utils" / "validate_diagram.py"
    if not validator.exists():
        print(f"  {RED}  [DIAGRAM-GATE] validator ausente — rejeitado: {target}{RESET}")
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(validator), "--output", str(target), "--type", "mmd"],
            input=body,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(WORKSPACE),
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        print(f"  {RED}  [DIAGRAM-GATE] execução falhou para {target}: {exc}{RESET}")
        return False
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    if proc.returncode not in (0, 2):
        print(f"  {RED}  [DIAGRAM-GATE] rejeitado: {target}{RESET}")
        return False
    return True


# ── Contrato de artefatos esperados por fase ─────────────────────────
# Cada entrada define padrões de path (glob-style) esperados na fase.
# Arquivos opcionais ficam em "optional"; obrigatórios em "required".
PHASE_ARTIFACT_CONTRACT: dict[str, dict] = {
    "F0":  {"required": [],
            "optional": ["asis/ast-raw"]},
    "F1":  {"required": ["asis/master-report.md", "asis/architecture-blueprint.md"],
            "optional": ["asis/inventory-report.md", "asis/metrics.json", "asis/bounded-context-map.md"]},
    "F1a": {"required": ["asis/inventory-report.md", "asis/metrics.json"],
            "optional": ["asis/complexity-map.md"]},
    "F1b": {"required": ["asis/architecture-blueprint.md", "asis/bounded-context-map.md"],
            "optional": ["asis/diagrams/c4-context.mmd", "asis/diagrams/c4-container.mmd"]},
    "F1c": {"required": ["asis/db/schema-inventory.md"],
            "optional": ["asis/db/er-diagram.mmd", "asis/db/stored-procedures-map.md", "asis/db-analysis-report.md"]},
    "F1d": {"required": ["asis/docs/business-rules.md"],
            "optional": ["asis/docs/functional-requirements.md", "asis/docs/requirements.md",
                         "asis/docs/screen-navigation-map.md", "asis/docs/screen-flow.mmd",
                         "asis/docs/value-chain.md", "asis/docs/screen-rules.md"]},
    "F1e": {"required": [],
            "optional": ["asis/security-map.md", "asis/vulnerabilities.md", "asis/compliance-gaps.md"]},
    "F1f": {"required": ["asis/gaps-risks-report.md"],
            "optional": ["asis/risk-register.json"]},
    "F2a": {"required": ["tobe/docs/architecture-blueprint.md", "tobe/docs/bounded-context-map.md"],
            "optional": ["tobe/diagrams/c4-context.mmd", "tobe/docs/decisions"]},
    "F2b": {"required": [],
            "optional": ["tobe/devops"]},
    "F2c": {"required": [],
            "optional": ["tobe/qa/test-plan.md"]},
    # F2d é passo TOOL: run_step() devolve contract_total=0 e este contrato
    # não é consultado. Fica declarado para que o relatório de execução nomeie
    # o artefato de veredito em vez de deixar a fase sem rastro.
    "F2d": {"required": [],
            "optional": ["tobe/migration/wave-model.json",
                         "tobe/migration/wave-model-consistency.json"]},
    "F3":  {"required": ["prototype"],
            "optional": []},
    # F3S — o gate de saída (artifact_gate_speckit.py) confere estes mesmos
    # artefatos com min_count e ainda roda as duas suítes de check. Aqui é só a
    # validação pós-passo do runner, para o relatório de execução.
    # Layout SpecKit: specs/NNN-slug/{spec,plan,tasks}.md — plans/ e tasks/ não
    # existem mais como diretórios próprios.
    # F3S — DERIVADO do `pipeline-dag/F3S.yaml → exit_gate` em `_derivar_contrato_f3s()`,
    # nunca escrito à mão. A lista fixa que vivia aqui era um espelho manual do DAG e
    # divergiu dele: exigia `checks-report.json` e `ava-agents-progress.txt`, que o
    # exit_gate da fase NÃO exige, e reprovava a F3S (`val_ok=False`) por ausência de
    # artefato que não é condição de saída. Placeholder vazio de propósito.
    "F3S": {"required": [], "optional": []},
    "F4":  {"required": ["tobe/source-code/backend"],
            "optional": ["tobe/source-code/frontend"]},
    "F5":  {"required": [],
            "optional": ["tobe/iac", "tobe/devops/ci", "tobe/devops/cd", "tobe/devops/docker"]},
    "F6":  {"required": [],
            "optional": ["tobe/qa/test-cases.md", "tobe/tests"]},
    "S1":  {"required": [],
            "optional": ["summary"]},
    "S2":  {"required": [],
            "optional": ["summary/remediation-report.md"]},
    "S3":  {"required": [],
            "optional": []},
    "S4":  {"required": [],
            "optional": ["summary"]},
    "FC":  {"required": ["tobe/devops/Dockerfile"],   # agente gera em tobe/devops/
            "optional": ["tobe/source-code/frontend/Dockerfile",
                         "tobe/source-code/docker-compose.yml",
                         "tobe/source-code/docker-compose.staging.yml",
                         "tobe/source-code/docker-compose.prod.yml",
                         "tobe/source-code/.env.example",
                         "tobe/devops/ci-pipeline.yml",
                         "tobe/devops/cd-pipeline.yml",
                         "tobe/devops/containerization-guide.md"]},
    "FP":  {"required": [],
            "optional": ["tobe/iac/containers/podman-preflight.md",
                         "tobe/iac/containers/podman-run-report.md",
                         "tobe/source-code/.env"]},
}


def _derivar_contrato_f3s() -> None:
    """Preenche `PHASE_ARTIFACT_CONTRACT["F3S"]` a partir do DAG da própria fase.

    O `pipeline-dag/F3S.yaml` abre dizendo que o gate LÊ aquele arquivo em runtime
    e que não há segunda cópia a manter. A lista fixa que vivia no dicionário acima
    era exatamente essa segunda cópia, e divergiu: exigia `checks-report.json`
    (produzido com `on_fail: warn`, legitimamente ausente quando a suíte degrada) e
    `ava-agents-progress.txt` (log narrativo, não condição de saída). Nenhum dos
    dois está no `exit_gate` — e a fase era reprovada por eles.

    `kind: human_approval` fica de fora: é decisão de operador registrada dentro de
    um artefato que já consta na lista, não um arquivo à parte.

    Degradar para lista vazia quando o YAML não é legível é deliberado: quem bloqueia
    a F4 é o gate determinístico da wave7, não esta validação, que é relatório de fim
    de passo. Herdar a lista velha seria manter o defeito.
    """
    dag = _dag_da_fase("F3S")
    if dag is None:
        return
    obrigatorios: list[str] = []
    for item in ((dag.get("exit_gate") or {}).get("items")) or []:
        if not isinstance(item, dict):
            continue
        if item.get("kind") == "human_approval":
            continue
        caminho = str(item.get("path") or "").strip()
        if not caminho:
            continue
        # Esta tabela é relativa a `outputs/`; o DAG declara da raiz do projeto.
        relativo = caminho[len("outputs/"):] if caminho.startswith("outputs/") else caminho
        if relativo not in obrigatorios:
            obrigatorios.append(relativo)
    PHASE_ARTIFACT_CONTRACT["F3S"]["required"] = obrigatorios


_derivar_contrato_f3s()


# -- Contrato de SAIDA DO AGENTE - denominador da barra de progresso ---------
# `PHASE_ARTIFACT_CONTRACT` e o gate de REPROVACAO da fase: lista curta, so o
# que bloqueia a fase seguinte. Usa-la como denominador da barra fazia o
# dashboard exibir "1/1 - 100%" para o `ava-asis-db-analyzer`, que promete 7
# artefatos e entregou 9 - a barra media o gate, nao a entrega, e por isso toda
# fase aparecia cheia assim que o unico obrigatorio caia em disco.
#
# O denominador honesto e o Output Contract que o proprio agente declara no seu
# skill (`## Output Contract`), unido ao `outputs` que o DAG declara para o
# passo e ao contrato de fase (required + optional). Quando nenhuma dessas
# fontes sabe dizer, a lista fica vazia e o dashboard segue mostrando
# "sem contrato" - nunca 0% nem 100% inventado.
# O heading precisa COMEÇAR com "Output Contract" (aceitando numeração e
# sufixo). `### Artifact Output Contract per Agent` do orchestrator-asis.md é
# uma tabela de lookup com o contrato dos OUTROS agentes, em paths relativos a
# `outputs/asis/` — casá-la punha 30 artefatos alheios e mal normalizados
# (`outputs/db/schema-inventory.md`) no denominador da F1, que então nunca
# fecharia. `## Output Verification` também fica de fora: descreve a conferência,
# não a entrega.
_SECAO_OUTPUT_CONTRACT = re.compile(
    r'^#{2,6}[ \t]*(?:[\dA-Z]{1,3}[.)][ \t]*)?Output Contract\b[^\n]*\n(.*?)(?=^#{2,6}[ \t]|\Z)',
    re.DOTALL | re.MULTILINE | re.IGNORECASE,
)
_FENCE_YAML = re.compile(r'```(?:yaml|yml)?\s*\n(.*?)```', re.DOTALL)
# Path entre crases — como `documentation-asis.md` declara seu contrato: tabela
# markdown com paths relativos a `outputs/` (`asis/docs/value-chain.md`). Sem
# isto o agente com contrato em tabela caía no contrato de fase e a barra media
# de novo o gate, não a entrega.
_PATH_CRASE = re.compile(r'`([^`\n]+?)`')
# Path solto em prosa, no dialeto absoluto — `db-analyzer.md § Mandatory Write Step`.
_PATH_SOLTO = re.compile(
    r'(?:projects/[^\s`"|]*?/)?outputs/[A-Za-z0-9_@{}\-./*]+\.[A-Za-z0-9]{2,5}'
)
_EXT_ARTEFATO = re.compile(
    r'\.(?:md|mmd|json|ya?ml|html?|csv|txt|puml|sql|drawio)$', re.IGNORECASE)
# Prefixos que são código do REPOSITÓRIO, nunca saída do agente. Sem este filtro
# a varredura por crases levaria `src/shared/utils/ntp_time.py` para o contrato.
_PREFIXO_NAO_SAIDA = ("src/", "tests/", ".github/", "docs/guia", "http")
_FILE_ABERTURA   = re.compile(r'<!--\s*FILE:\s*([^\n\r]+?)\s*-->', re.IGNORECASE)
_FILE_FECHAMENTO = re.compile(r'<!--\s*/FILE\s*-->', re.IGNORECASE)

_EXPECTED_CACHE: dict[str, list[str]] = {}


def _norm_saida(caminho: str) -> str:
    """Reduz um path declarado a forma comparavel `outputs/...`.

    As tres fontes falam dialetos diferentes do mesmo path:
    `projects/{project_name}/outputs/asis/db/x.md` (skill do agente),
    `asis/db/x.md` (contrato de fase, relativo a `outputs/`) e
    `specs/{feature}/plan.md` sob um `output_base` (DAG). Sem esta normalizacao
    o mesmo artefato entrava tres vezes no denominador.
    """
    p = str(caminho or "").strip().strip('`"\'').replace("\\", "/")
    if not p:
        return ""
    i = p.find("outputs/")
    if i >= 0:
        p = p[i:]
    else:
        p = "outputs/" + p.lstrip("./")
    return p.rstrip("/")


def _paths_de_yaml(texto: str) -> list[str]:
    """Todo valor string com cara de path dentro de um bloco YAML."""
    try:
        import yaml as _yaml
        dados = _yaml.safe_load(texto)
    except Exception:  # noqa: BLE001 - contrato mal formado degrada, nao derruba
        return []
    achados: list[str] = []

    def _varre(no) -> None:
        if isinstance(no, str):
            cauda = no.rsplit("/", 1)[-1]
            if "/" in no and "." in cauda:
                achados.append(no)
        elif isinstance(no, dict):
            for v in no.values():
                _varre(v)
        elif isinstance(no, list):
            for v in no:
                _varre(v)

    _varre(dados)
    return achados


def _parece_path_de_saida(texto: str) -> bool:
    """True se o trecho tem cara de artefato de saída, e não de prosa ou de
    caminho do repositório."""
    t = str(texto or "").strip()
    if not t or " " in t or "\n" in t:
        return False
    # A barra FINAL não vale como separador: `prototype-asis/` é o nome curto na
    # coluna "Artefato" da tabela, não o path — o path está na coluna ao lado.
    # Sem esta distinção o contrato ganhava `outputs/prototype-asis`, que nunca
    # existe em disco e segurava a barra abaixo de 100% para sempre.
    if "/" not in t.rstrip("/"):
        return False
    if t.lower().startswith(_PREFIXO_NAO_SAIDA):
        return False
    # Diretório declarado como entrega (`asis/docs/prototype-asis/`) conta.
    return t.endswith("/") or bool(_EXT_ARTEFATO.search(t))


def _contrato_declarado_no_skill(skill_content: str) -> list[str]:
    """Paths que o agente promete no seu proprio `## Output Contract`.

    Fonte mais rica das tres: e a unica que enumera os artefatos que o agente
    considera sua entrega completa. `db-analyzer.md` declara 7 saidas ali; o
    contrato de fase conhece 1 delas.

    Os agentes declaram em tres dialetos, e todos precisam ser lidos: bloco YAML
    (`db-analyzer.md`), tabela markdown com paths entre crases relativos a
    `outputs/` (`documentation-asis.md`) e prosa com o path absoluto.
    """
    if not skill_content:
        return []
    achados: list[str] = []
    for corpo in _SECAO_OUTPUT_CONTRACT.findall(skill_content):
        for fence in _FENCE_YAML.findall(corpo):
            achados.extend(_paths_de_yaml(fence))
        achados.extend(p for p in _PATH_CRASE.findall(corpo)
                       if _parece_path_de_saida(p))
        achados.extend(_PATH_SOLTO.findall(corpo))
    return achados


def expected_artifacts(phase: str, step: "dict | None",
                       skill_content: str = "") -> list[str]:
    """Artefatos que o passo DEVE entregar - denominador da barra de progresso.

    Uniao, da fonte mais rica para a mais pobre:
      1. `## Output Contract` do skill do agente - o que ele promete entregar;
      2. `outputs` declarados no DAG para o passo - precisos por feature;
      3. `PHASE_ARTIFACT_CONTRACT[fase]` - required + optional.

    O contrato de FASE fica de fora dos passos expandidos (`F3S:planning:003-`)
    pela mesma razao que `validate_phase_artifacts` o ignora neles: e contrato
    de FIM de fase, e cobra-lo de um passo intermediario mediria o denominador
    errado.
    """
    step = step or {}
    chave = (f"{phase}|{step.get('agent', '')}|{step.get('feature', '')}"
             f"|{step.get('output_base', '')}|{len(skill_content)}")
    if chave in _EXPECTED_CACHE:
        return _EXPECTED_CACHE[chave]

    do_skill = _contrato_declarado_no_skill(skill_content)
    brutos: list[str] = list(do_skill)

    base = str(step.get("output_base") or "").replace("\\", "/").strip("/")
    for rel in (step.get("outputs") or []):
        rel = str(rel).strip()
        if rel:
            brutos.append(f"{base}/{rel}" if base else rel)

    if ":" not in phase:
        contrato_fase = PHASE_ARTIFACT_CONTRACT.get(phase) or {}
        brutos.extend(contrato_fase.get("required", []))
        # O `optional` da fase é PALPITE do runner sobre o que o agente talvez
        # produza, e envelhece: a F1d lista `functional-requirements.md` E
        # `requirements.md`, que são o mesmo artefato sob dois nomes — somar os
        # dois travaria a barra em 85% para sempre. Quando o agente declara o
        # próprio contrato, ele é a autoridade e o palpite sai do denominador;
        # o `required` fica em ambos os casos, porque é gate.
        if not do_skill:
            brutos.extend(contrato_fase.get("optional", []))

    saida: list[str] = []
    vistos: set[str] = set()
    nomes: set[str] = set()
    for b in brutos:
        norm = _norm_saida(b)
        if not norm or norm in vistos:
            continue
        # `outputs` puro é a RAIZ, não um artefato: vem de frases como "paths
        # relativos a `projects/{project_name}/outputs/`" dentro da seção.
        if "/" not in norm:
            continue
        # Saída de nome variável (`screen-flow-*.mmd`, `ADR-*.md`) não é item
        # contável de contrato — o próprio orchestrator-asis.md diz que outputs
        # de nome variável não entram na lista de obrigatórios, porque o número
        # deles depende do projeto. Deixá-los no denominador travaria a barra
        # abaixo de 100% em todo projeto que não dispara o caso. Quem confere
        # esses é o Consistency Gate, não a barra.
        if "*" in norm or "?" in norm:
            continue
        # Dedup por nome de arquivo: `_casa_contrato` já trata dois paths de
        # mesmo basename como o MESMO artefato (o agente pode ter errado a
        # pasta), então mantê-los separados só inflaria o denominador com uma
        # linha que nunca falha nem passa sozinha — foi o que fez a F1c pedir
        # `db/db-analysis-report.md` e `db-analysis-report.md` como dois.
        nome = norm.rsplit("/", 1)[-1]
        tem_glob = ("*" in nome or "?" in nome)
        if not tem_glob and nome in nomes:
            continue
        vistos.add(norm)
        if not tem_glob:
            nomes.add(nome)
        saida.append(norm)
    _EXPECTED_CACHE[chave] = saida
    return saida


def _casa_contrato(entregue: str, esperado: str) -> bool:
    """True se o artefato entregue satisfaz esta entrada do contrato."""
    e = _norm_saida(entregue)
    if not e:
        return False
    if e == esperado:
        return True
    if "*" in esperado or "?" in esperado:
        return fnmatch.fnmatch(e, esperado)
    # Mesmo arquivo em diretorio vizinho conta como entregue: a BARRA mede
    # entrega, o GATE (`required_missing`) e quem mede o lugar certo. Sem isto,
    # um agente que grava `asis/db-analysis-report.md` em vez de
    # `asis/db/db-analysis-report.md` ficaria com a barra em 0% tendo escrito
    # tudo - e o defeito real (path errado) ja e reportado pelo gate.
    return e.rsplit("/", 1)[-1] == esperado.rsplit("/", 1)[-1]


def _extras_fora_do_contrato(entregues: "list[str]",
                             esperados: "list[str]") -> "tuple[set[str], int]":
    """`(itens do contrato cobertos, nº de entregas que não estão no contrato)`.

    O artefato fora do contrato NÃO é ruído a descartar: o `ava-tobe-orchestrator`
    declara 1 saída própria e grava dezenas, porque quem produz o resto são os
    sub-agentes que ele despacha dentro do MESMO passo. Se o extra ficasse de
    fora, a barra da F2a passaria meia hora em 0/3 e saltaria no fim — que é o
    defeito de origem com outro rosto.
    """
    cobertos: set[str] = set()
    extras = 0
    vistos: set[str] = set()
    for ent in entregues:
        norm = _norm_saida(ent)
        if not norm or norm in vistos:
            continue
        vistos.add(norm)
        alvo = next((esp for esp in esperados if _casa_contrato(norm, esp)), None)
        if alvo is None:
            extras += 1
        else:
            cobertos.add(alvo)
    return cobertos, extras


def progresso_contrato(entregues: "list[str]",
                       esperados: "list[str]") -> "tuple[int, int]":
    """`(artefatos concluídos, total esperado)` para a barra de progresso.

    Total = itens do contrato + entregas fora dele já concluídas. Somar o extra
    nos DOIS lados é o que mantém a fração honesta: ela sobe a cada artefato que
    fecha e só chega a 100% quando o contrato inteiro está entregue, sem que um
    agente generoso "estoure" a barra nem que um orquestrador fique parado nela.

    Devolve `(0, 0)` quando nao ha contrato conhecido - o chamador traduz isso
    em "sem contrato", nao em 0%.
    """
    if not esperados:
        return 0, 0
    cobertos, extras = _extras_fora_do_contrato(entregues, esperados)
    return len(cobertos) + extras, len(esperados) + extras


def artefatos_concluidos_no_stream(resposta: str) -> list[str]:
    """Paths dos blocos `FILE:` ja CONCLUIDOS no texto recebido ate agora.

    Existe porque os artefatos so vao para o disco depois que o stream inteiro
    termina (`parse_and_write_outputs`): durante os ~10 min de um passo nao ha
    nada em disco para contar, e a barra so sabia mostrar uma faixa deslizante
    indeterminada. O texto acumulado, porem, ja diz quantos artefatos fecharam.

    Concluido = o bloco fechou com `<!-- /FILE -->` ou um `FILE:` seguinte
    comecou. O ultimo bloco ainda aberto NAO conta: ele esta sendo escrito neste
    instante, e conta-lo faria a barra saltar para 100% no comeco do ultimo
    artefato em vez de no fim.
    """
    if not resposta:
        return []
    marcas = list(_FILE_ABERTURA.finditer(resposta))
    prontos: list[str] = []
    for i, m in enumerate(marcas):
        ultimo = (i + 1 == len(marcas))
        fim = len(resposta) if ultimo else marcas[i + 1].start()
        if ultimo and not _FILE_FECHAMENTO.search(resposta[m.end():fim]):
            continue
        caminho = m.group(1).strip()
        if caminho:
            prontos.append(caminho)
    return prontos


def _contrato_presente_no_disco(proj_root: "Path", esperado: str,
                                escritos: "list[str]") -> bool:
    """True se o item do contrato existe em disco ou foi escrito nesta execucao."""
    if any(_casa_contrato(w, esperado) for w in escritos):
        return True
    alvo = proj_root / esperado
    try:
        if "*" in esperado or "?" in esperado:
            pai = alvo.parent
            return pai.is_dir() and any(
                p.is_file() and p.stat().st_size > 0 for p in pai.glob(alvo.name))
        if alvo.is_file():
            return alvo.stat().st_size > 0
        if alvo.is_dir():
            return any(p.is_file() for p in alvo.rglob("*"))
    except OSError:
        return False
    return False


def validate_declared_outputs(step: dict, project: str) -> "tuple[list[str], list[str]]":
    """Confere os `outputs` que o DAG declara para o passo, já com `{feature}` resolvido.

    O contrato por-fase (`PHASE_ARTIFACT_CONTRACT`) é global demais para o fan-out
    da F3S: ele não sabe distinguir a feature 002 da 003. O DAG sabe —
    `pipeline-dag/F3S.yaml` declara `specs/{feature}/plan-graph.json` — e essa
    informação vinha sendo descartada. Aqui ela vira gate.

    Retorna ``(presentes, ausentes)`` em caminhos relativos ao projeto.
    """
    declared = [str(o) for o in (step.get("outputs") or []) if str(o).strip()]
    if not declared:
        return [], []
    base = WORKSPACE / "projects" / project / str(step.get("output_base") or "")
    presentes: list[str] = []
    ausentes:  list[str] = []
    for rel in declared:
        alvo = base / rel.replace("\\", "/")
        # Artefato vazio conta como ausente: bloco truncado grava arquivo inútil.
        if alvo.is_file() and alvo.stat().st_size > 0:
            presentes.append(rel)
        else:
            ausentes.append(rel)
    return presentes, ausentes


def validate_phase_artifacts(phase: str, project: str, written: list[str],
                             step: dict | None = None,
                             expected: "list[str] | None" = None) -> dict:
    """Valida os artefatos gerados na fase contra o contrato esperado.
    Retorna dict com: ok (bool), required_ok, required_missing, optional_found, warnings.

    ``expected`` e o contrato de ENTREGA do agente (`expected_artifacts`), que
    e mais largo que o de reprovacao: alimenta so os campos `expected_*`, que
    o dashboard usa como denominador da barra. `ok` continua decidido apenas
    por `required_missing` - alargar o gate junto com a barra reprovaria fase
    por artefato opcional ausente.
    """
    # Seleção do contrato. Passos expandidos chegam como "F3S:planning:003-w2-…",
    # nunca como "F3S", e o lookup falhava sempre — contrato vazio, tudo aprovado
    # por omissão (ISSUE-004). O contrato por-fase é de FIM DE FASE (exige, p.ex.,
    # traceability.json, que só nasce na wave5b), então NÃO pode ser aplicado a um
    # passo intermediário: para esses, quem vale é o `outputs` do DAG, conferido
    # em `validate_declared_outputs`.
    contract = PHASE_ARTIFACT_CONTRACT.get(phase)
    if contract is None:
        contract = ({"required": [], "optional": []} if ":" in phase
                    else PHASE_ARTIFACT_CONTRACT.get(phase, {"required": [], "optional": []}))
    req_paths = contract.get("required", [])
    opt_paths = contract.get("optional", [])
    proj_out  = WORKSPACE / "projects" / project / "outputs"

    # Normaliza caminhos escritos para forward-slash
    written_norm = [w.replace("\\", "/") for w in written]

    # Checa required: verifica se algum arquivo escrito OU ja existente cobre o padrao
    required_ok:      list[str] = []
    required_missing: list[str] = []
    for pattern in req_paths:
        # Verifica em arquivos escritos nesta execucao
        found_written = any(pattern in w for w in written_norm)
        # Verifica em disco (ja existia de execucao anterior)
        found_disk = any(True for _ in proj_out.rglob("*")
                         if pattern.replace("/","\\") in str(_) or pattern in str(_).replace("\\", "/"))
        if found_written or found_disk:
            required_ok.append(pattern)
        else:
            required_missing.append(pattern)

    # Checa optional: apenas informa o que foi encontrado
    optional_found: list[str] = []
    for pattern in opt_paths:
        found = any(pattern in w for w in written_norm) or \
                any(True for _ in proj_out.rglob("*")
                    if pattern in str(_).replace("\\", "/"))
        if found:
            optional_found.append(pattern)

    # Gate por-passo vindo do DAG (preciso por feature) — soma ao contrato de fase.
    declared_ok, declared_missing = validate_declared_outputs(step or {}, project)
    required_ok.extend(declared_ok)
    required_missing.extend(declared_missing)

    # Progresso de ENTREGA - denominador da barra do dashboard.
    # Conferido em disco (e nao so no que foi escrito nesta execucao) porque
    # uma retomada reexecuta o passo com metade do contrato ja gravada, e a
    # barra tem de refletir o que existe, nao o que este turno produziu.
    esperados = [e for e in (expected or []) if e]
    proj_root = WORKSPACE / "projects" / project
    expected_ok:      list[str] = []
    expected_missing: list[str] = []
    for esp in esperados:
        if _contrato_presente_no_disco(proj_root, esp, written_norm):
            expected_ok.append(esp)
        else:
            expected_missing.append(esp)
    # Mesma regra da barra em voo: o que o passo entregou além do contrato
    # entra nos dois lados da fração, para que o número final case com o que
    # o operador viu subir durante a execução.
    _, expected_extra = _extras_fora_do_contrato(written_norm, esperados)

    ok = len(required_missing) == 0
    return {
        "ok":               ok,
        "required_ok":      required_ok,
        "required_missing": required_missing,
        "declared_missing": declared_missing,
        "optional_found":   optional_found,
        "expected_total":   len(esperados),
        "expected_ok":      len(expected_ok),
        "expected_extra":   expected_extra,
        "expected_missing": expected_missing,
        "written_count":    len(written),
        "warnings":         [] if ok else [f"Artefato obrigatório ausente: {p}" for p in required_missing],
    }


def print_validation_report(phase: str, result: dict):
    """Exibe o relatório de validação de artefatos de forma visual."""
    status_icon = f"{GREEN}✅ PASS{RESET}" if result["ok"] else f"{RED}❌ FAIL{RESET}"
    print(f"\n{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}  📊 Validação de Artefatos — {phase}  [{status_icon}{BOLD}]{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")
    print(f"  Arquivos escritos nesta execução : {result['written_count']}")

    if result["required_ok"]:
        for r in result["required_ok"]:
            print(f"  {GREEN}✓  Obrigatório OK   :{RESET} {r}")

    if result["required_missing"]:
        for r in result["required_missing"]:
            print(f"  {RED}✗  Obrigatório AUSENTE:{RESET} {r}")

    if result["optional_found"]:
        for o in result["optional_found"]:
            print(f"  {DIM}◦  Opcional OK    : {o}{RESET}")

    if not result["ok"]:
        print(f"\n  {YELLOW}⚠️  Atenção: alguns artefatos obrigatórios não foram gerados.")
        print(f"      Verifique o log e considere reexecutar a fase.{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")


def _html_strip_document_wrapper(chunk: str, is_first: bool) -> str:
    """Remove cabeçalho/rodapé HTML duplicado de uma parte não-primeira.

    Quando o modelo gera cada parte como documento HTML completo
    (com <!DOCTYPE>, <html>, <head>, <body> e </body></html>), a
    concatenação simples produz HTML inválido com múltiplos DOCTYPE.

    Estratégia:
    - Parte 1 (is_first=True)  → preservada integralmente.
    - Parte N (is_first=False) → remove tudo até o primeiro <body> (abre)
      e remove </body>\n</html> (e variações) no final.
    Isso extrai apenas o conteúdo do <body> de cada parte subsequente.
    Se a parte não tiver estrutura de documento completo, é retornada as-is.
    """
    if is_first:
        return chunk

    import re as _re

    # Só aplica se parecer documento completo (tem DOCTYPE ou <html)
    has_doctype = bool(_re.search(r'<!DOCTYPE\s+html', chunk, _re.I))
    has_html_open = bool(_re.search(r'<html[\s>]', chunk, _re.I))
    if not (has_doctype or has_html_open):
        return chunk

    # Localiza abertura do <body>
    body_m = _re.search(r'<body[^>]*>', chunk, _re.I)
    if body_m:
        chunk = chunk[body_m.end():]   # descarta tudo até (e incluindo) <body ...>

    # Remove fechamento do documento no final
    chunk = _re.sub(
        r'\s*</body>\s*</html>\s*$', '', chunk,
        flags=_re.I | _re.DOTALL
    ).rstrip()

    return chunk


def _html_repair_duplicate_documents(html: str) -> str:
    """Repara HTML que contém múltiplos documentos colados (bug de merge).

    Detecta a presença de mais de um <!DOCTYPE html> e re-monta o documento
    preservando o cabeçalho completo da primeira parte e apenas o conteúdo
    <body> das partes subsequentes.
    Retorna o HTML reparado (ou o original se não houver problema).
    """
    import re as _re

    # Identifica ranges de tags <script>…</script> para evitar falsos positivos:
    # DOCTYPE embutido no JSON (ex: conteúdo de index.html no fileTree) não deve
    # ser confundido com um documento HTML real.
    script_ranges: list[tuple[int, int]] = []
    for sm in _re.finditer(r'<script[^>]*>', html, _re.I):
        em = _re.search(r'</script>', html[sm.end():], _re.I)
        if em:
            script_ranges.append((sm.end(), sm.end() + em.start()))

    def _in_script(pos: int) -> bool:
        return any(s <= pos < e for s, e in script_ranges)

    positions = [m.start() for m in _re.finditer(r'<!DOCTYPE\s+html', html, _re.I)
                 if not _in_script(m.start())]
    if len(positions) < 2:
        return html   # sem duplicação — retorna as-is

    # Divide o HTML nos limites de cada DOCTYPE
    parts_raw: list[str] = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(html)
        parts_raw.append(html[pos:end])

    merged_parts: list[str] = []
    for i, raw in enumerate(parts_raw):
        merged_parts.append(_html_strip_document_wrapper(raw, is_first=(i == 0)))

    # Reconstrução: primeiro doc inteiro + conteúdo body dos demais
    # Insere os fragmentos adicionais antes de </body></html> do primeiro doc
    first_doc = merged_parts[0]
    extra_content = "\n".join(merged_parts[1:])

    # Localiza </body> no primeiro doc para inserir o conteúdo extra antes
    close_body_m = _re.search(r'</body>', first_doc, _re.I)
    if close_body_m:
        repaired = (
            first_doc[:close_body_m.start()]
            + "\n" + extra_content + "\n"
            + first_doc[close_body_m.start():]
        )
    else:
        # Sem </body> — apenas appenda
        repaired = first_doc + "\n" + extra_content

    return repaired


def _merge_parts(unified_target: "Path", part_paths: "list[Path]") -> bool:
    """Une partes .part1, .part2... em um arquivo unificado no disco.
    Chamado imediatamente após _split_and_write para que o arquivo final
    exista sem exigir intervenção manual.

    Para arquivos HTML: detecta e repara o caso em que cada parte é um
    documento HTML completo (com DOCTYPE/head/body), evitando a geração
    de HTML com múltiplos DOCTYPE colados.

    Retorna True se a união foi bem-sucedida.
    """
    try:
        is_html = unified_target.suffix.lower() in (".html", ".htm")
        chunks: list[str] = []
        for i, pp in enumerate(part_paths):
            raw = pp.read_text(encoding="utf-8", errors="ignore")
            chunk = _html_strip_document_wrapper(raw, is_first=(i == 0)) if is_html else raw
            chunks.append(chunk)

        content = "".join(chunks)

        # Reparo defensivo: caso partes restantes ainda contenham DOCTYPE
        if is_html:
            content = _html_repair_duplicate_documents(content)

        unified_target.write_text(content, encoding="utf-8")
        kb = len(content) // 1024
        print(f"  {GREEN}  [UNIFIED]  {unified_target.name}  ({kb}KB — {len(part_paths)} partes unidas){RESET}")
        return True
    except Exception as e:
        print(f"  {RED}  [MERGE-ERR]  Falha ao unir partes em {unified_target.name}: {e}{RESET}")
        return False


def _split_and_write(path_str: str, body: str, project: str) -> list[str]:
    """Divide body em partes de ~80KB e salva como .part1.ext, .part2.ext ...
    Tenta dividir em pontos lógicos (tags HTML de fechamento, linhas em branco).
    Após salvar todas as partes, une-as automaticamente no arquivo original.
    Retorna lista de paths escritos (partes + arquivo unificado).
    """
    PART_SIZE = 80_000  # chars por parte (~20K tokens)
    written: list[str] = []

    # Mermaid is never split or merged as an LLM response artifact: the
    # pre-write gate must validate the complete diagram before publication.
    if Path(path_str).suffix.lower() == ".mmd":
        target = _resolve_path(path_str, project)
        if _write_output_body(target, body, project):
            written.append(str(target.relative_to(WORKSPACE)))
        return written

    if len(body) <= PART_SIZE:
        # Não precisa dividir
        target = _resolve_path(path_str, project)
        if not _is_safe_output_path(target, project):
            return written
        target.parent.mkdir(parents=True, exist_ok=True)
        if _write_output_body(target, body, project):
            written.append(str(target.relative_to(WORKSPACE)))
        return written

    # Determina extensão para nomear as partes
    base_path = Path(path_str)
    stem      = base_path.stem   # ex: sophia-prototype
    suffix    = base_path.suffix  # ex: .html
    parent    = base_path.parent  # ex: projects/Sophia/outputs/prototype

    # Divide respeitando quebras naturais
    parts: list[str] = []
    remaining = body
    while remaining:
        if len(remaining) <= PART_SIZE:
            parts.append(remaining)
            break
        # Tenta cortar num ponto lógico: \n\n, </div>, </section>, linha em branco
        cut = PART_SIZE
        for sep in ('\n\n', '</section>', '</div>', '</tr>', '\n'):
            idx = remaining.rfind(sep, PART_SIZE // 2, PART_SIZE)
            if idx > 0:
                cut = idx + len(sep)
                break
        parts.append(remaining[:cut])
        remaining = remaining[cut:]

    part_file_paths: list[Path] = []
    for i, chunk in enumerate(parts, 1):
        part_path_str = str(parent / f"{stem}.part{i}{suffix}")
        target = _resolve_path(part_path_str, project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(chunk, encoding="utf-8")
        written.append(str(target.relative_to(WORKSPACE)))
        part_file_paths.append(target)
        kb = len(chunk) // 1024
        print(f"  {YELLOW}  [PARTE {i}/{len(parts)}]  {part_path_str}  ({kb}KB){RESET}")

    # ── União automática: gera o arquivo final imediatamente ──────
    # Causa raiz corrigida: o arquivo unificado é criado aqui, sem
    # exigir execução manual de PowerShell ou bash pelo usuário.
    unified_path = _resolve_path(path_str, project)
    unified_ok = _merge_parts(unified_path, part_file_paths)
    if unified_ok:
        written.append(str(unified_path.relative_to(WORKSPACE)))
        print(f"  {GREEN}  [MERGE-OK]  Arquivo unificado pronto: {unified_path.name}{RESET}")
    else:
        print(f"  {RED}  [MERGE-FAIL]  Unificação falhou para: {unified_path.name}{RESET}")

    # Gera também o arquivo de instrução de junção (referência / reprocessamento)
    merge_path = _resolve_path(str(parent / f"{stem}.MERGE-INSTRUCTIONS.md"), project)
    merge_path.parent.mkdir(parents=True, exist_ok=True)
    part_names = [f"{stem}.part{i}{suffix}" for i in range(1, len(parts)+1)]
    merge_path.write_text(
        f"# Instruções de Junção — {stem}{suffix}\n\n"
        f"O arquivo foi dividido em **{len(parts)} partes** e unido automaticamente.\n\n"
        f"**Arquivo unificado gerado:** `{base_path.name}` ({'✅ OK' if unified_ok else '❌ FALHOU — execute manualmente'})\n\n"
        f"## Partes geradas\n\n"
        + "\n".join(f"{i}. `{n}`" for i, n in enumerate(part_names, 1)) +
        f"\n\n## Como re-juntar manualmente (PowerShell)\n\n"
        f"```powershell\n"
        f"$parts = @({', '.join(repr(n) for n in part_names)})\n"
        f"$out   = '{stem}{suffix}'\n"
        f"$parts | ForEach-Object {{ Get-Content $_ -Raw }} | Set-Content $out -Encoding UTF8\n"
        f"```\n\n"
        f"## Como re-juntar manualmente (bash)\n\n"
        f"```bash\n"
        f"cat {' '.join(part_names)} > {stem}{suffix}\n"
        f"```\n",
        encoding="utf-8",
    )
    written.append(str(merge_path.relative_to(WORKSPACE)))
    print(f"  {CYAN}  [MERGE-INSTRUCTIONS]  {merge_path.name}  — gerado{RESET}")
    return written


# Regex para identificar arquivos com sufixo .partN (ex: arquivo.part1.html)
_PART_SUFFIX_RE = re.compile(r'^(.+?)\.part(\d+)(\.[^.]+)$')


def _merge_any_parts_in_written(written: list[str], project: str) -> None:
    """Consolida QUALQUER grupo de partes .partN.EXT presentes na lista `written`.

    Chamado ao final de parse_and_write_outputs para garantir que arquivos
    gerados diretamente pelo modelo (ex: prototipo.part1.html, prototipo.part2.html)
    ou por _split_and_write em qualquer fase tenham seu arquivo unificado criado.

    Não reprocessa grupos cujo arquivo unificado já existe e está atualizado
    (tamanho ≥ 90% da soma das partes).

    Opera em memória a partir da lista `written` — não faz glob em disco.
    """
    import collections

    # Agrupa: base_path_sem_partN → lista[(numero_parte, path_abs)]
    groups: dict[str, list[tuple[int, Path]]] = collections.defaultdict(list)
    for rel in written:
        m = _PART_SUFFIX_RE.match(rel.replace("\\", "/"))
        if not m:
            continue
        _base_stem = m.group(1)  # ex: "Prototipo"  OU  "AVA-FABRIC-SUMMARY-...html"
        _part_ext  = m.group(3)  # ex: ".html"
        # Evita dupla extensão: se o stem já termina com a extensão da parte, não adiciona de novo.
        # Caso correto:   Prototipo + .html        → Prototipo.html        ✅
        # Caso summary:   summary.html + .html     → summary.html          ✅ (sem duplicar)
        base_rel = _base_stem if _base_stem.lower().endswith(_part_ext.lower()) else _base_stem + _part_ext
        part_num = int(m.group(2))
        abs_path = WORKSPACE / rel
        groups[base_rel].append((part_num, abs_path))

    for base_rel, part_entries in groups.items():
        # Ordena por número de parte
        part_entries.sort(key=lambda x: x[0])
        part_paths = [p for _, p in part_entries]

        unified_target = WORKSPACE / base_rel
        if not _is_safe_output_path(unified_target, project):
            continue

        # Verifica se unificado já está completo (evita re-merge desnecessário)
        total_parts_size = sum(p.stat().st_size for p in part_paths if p.exists())
        if unified_target.exists():
            existing_size = unified_target.stat().st_size
            if existing_size >= total_parts_size * 0.9:
                print(f"  {DIM}  [MERGE-SKIP]  {unified_target.name} já unificado "
                      f"({existing_size//1024}KB ≥ {total_parts_size//1024}KB){RESET}")
                continue

        # Une as partes
        print(f"\n  {CYAN}  [MERGE-PARTS]  Unificando {len(part_paths)} partes → "
              f"{unified_target.name}{RESET}")
        ok = _merge_parts(unified_target, part_paths)
        if ok:
            print(f"  {GREEN}  [MERGE-OK]  Unificado criado: {unified_target.name}  "
                  f"({unified_target.stat().st_size//1024}KB){RESET}")
            # Adiciona o unificado à lista de escritos para que apareça no relatório
            rel_unified = str(unified_target.relative_to(WORKSPACE))
            if rel_unified not in written:
                written.append(rel_unified)
        else:
            print(f"  {RED}  [MERGE-FAIL]  Falha ao unificar: {unified_target.name}{RESET}")


# Um bloco por match: abertura, corpo, e fechamento OPCIONAL. O corpo para no
# próximo `<!-- FILE:`, no `<!-- /FILE -->` ou no fim da resposta. Assim blocos
# fechados e o eventual bloco aberto final saem da MESMA varredura, em ordem.
# O grupo 3 captura o marcador de fechamento quando ele existe; nas outras duas
# alternativas (lookahead do próximo FILE, fim da resposta) casa string vazia.
# É esse grupo — e não o sufixo do texto — que diz se o bloco fechou: um corpo
# HTML legítimo pode terminar em "-->" e enganar qualquer heurística textual.
_FILE_ANY = re.compile(
    r'<!--\s*FILE:\s*([^\n\r]+?)\s*-->\r?\n'
    r'(.*?)'
    r'(<!--\s*/FILE\s*-->|(?=<!--\s*FILE:)|\Z)',
    re.DOTALL
)


def parse_and_write_outputs(response: str, project: str,
                            truncated: bool = False
                            ) -> "tuple[list[str], list[str]]":
    """Extrai artefatos da resposta e escreve no disco.

    Suporta os 2 formatos numa varredura única:
      1. ``<!-- FILE: path -->…<!-- /FILE -->``  — bloco fechado (completo)
      2. ``<!-- FILE: path -->…<EOF>``           — bloco aberto (cortado por max_tokens)

    Retorna ``(escritos, incompletos)``.

    Correção ISSUE-004 — o comportamento anterior tinha dois defeitos graves:

    * o parser do formato 2 só rodava se o formato 1 não achasse **nada**
      (`if written: return written`). Quando a resposta trazia um bloco fechado
      seguido de um bloco cortado — exatamente o caso `plan.md` + `plan-graph.json`
      — o artefato truncado era **descartado em silêncio**;
    * `truncated=True` fatiava em `.partN` **todos** os blocos, inclusive os
      fechados e íntegros, gerando `plan.part1/part2` + MERGE-INSTRUCTIONS
      desnecessários para um arquivo que nunca esteve incompleto.

    Agora o corte é atribuído a quem de fato foi cortado — o último bloco, e só
    se ele não fechou — e o artefato incompleto é gravado como ``.PARTIAL`` e
    devolvido em ``incompletos`` para que o passo seja REPROVADO.
    """
    written:     list[str] = []
    incompletos: list[str] = []

    matches = list(_FILE_ANY.finditer(response))
    for pos, m in enumerate(matches):
        path_str = m.group(1).strip()
        body     = m.group(2)
        if not path_str:
            print(f"  {YELLOW}  [SKIP]  Bloco FILE com path vazio — ignorado.{RESET}")
            continue

        # Bloco fechado ⇔ o grupo do marcador de fechamento casou algo.
        fechado = bool((m.group(3) or "").strip())
        # Só o ÚLTIMO bloco pode ter sido cortado pelo teto de saída.
        e_ultimo = (pos == len(matches) - 1)

        if not fechado and truncated and e_ultimo:
            body = body.rstrip()
            if len(body) < 50:      # fragmento trivial — nada de útil a preservar
                incompletos.append(path_str)
                print(f"  {RED}  [INCOMPLETO]  {path_str} — bloco cortado sem conteúdo{RESET}")
                continue
            alvo = _resolve_path(path_str + ".PARTIAL", project)
            if _is_safe_output_path(alvo, project):
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_text(body, encoding="utf-8")
                print(f"  {RED}  [INCOMPLETO]  {path_str} — cortado por max_tokens "
                      f"({len(body):,} chars salvos em {alvo.name}){RESET}")
            incompletos.append(path_str)
            continue

        if not fechado and not e_ultimo:
            # Bloco sem fechamento no meio da resposta: o modelo esqueceu o
            # marcador. O conteúdo está completo (o próximo FILE começou), então
            # grava normalmente — mas avisa, porque é desvio de contrato.
            print(f"  {YELLOW}  [SEM-/FILE]  {path_str} — bloco sem marcador de "
                  f"fechamento; gravado assim mesmo{RESET}")

        # Arquivos que o modelo já nomeou como partes (.partN.ext) NÃO devem ser
        # re-divididos — salvar direto evita sub-partes (.part1.part1.html etc.).
        _is_already_part = bool(_PART_SUFFIX_RE.match(Path(path_str).name))
        # Fatiar só o que é grande de verdade. Bloco fechado é íntegro por
        # definição: `truncated` da resposta não o torna incompleto.
        is_large_html = (
            not _is_already_part
            and len(body) > 80_000
            and Path(path_str).suffix.lower() in (".html", ".htm")
        )
        if is_large_html:
            written.extend(_split_and_write(path_str, body, project))
        else:
            target = _resolve_path(path_str, project)
            if not _is_safe_output_path(target, project):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if _write_output_body(target, body, project):
                written.append(str(target.relative_to(WORKSPACE)))
            print(f"  {GREEN}  [FILE]  {path_str}{RESET}")

    # ── Consolidação universal de partes escritas nesta execução ──────────────
    # Garante que QUALQUER conjunto de arquivos .partN.EXT escritos nesta execução
    # (seja pelo modelo diretamente via blocos FILE, seja pelo _split_and_write)
    # tenha seu arquivo unificado criado — independente de fase ou tipo de arquivo.
    # Isso cobre: protótipos HTML, relatórios .md, arquivos .cs, etc.
    _merge_any_parts_in_written(written, project)

    return written, incompletos


def _call_builder_direct(script: Path, project: str,
                         extra_argv: "list[str] | None" = None) -> "tuple[int, float]":
    """Importa um script builder como módulo e chama main() diretamente (sem subprocess).
    Retorna (exit_code, elapsed_seconds). Saída vai ao console em tempo real.

    extra_argv: argumentos adicionais além de "--project {project}", ex: ["--skip-mermaid-gate"]
    O exit_code é capturado via SystemExit OU via valor de retorno de main() (int != 0).
    """
    import importlib.util
    from datetime import datetime as _dt

    if not script.exists():
        print(f"{RED}  ❌  Script não encontrado: {script}{RESET}")
        return -1, 0.0

    utils_dir = str(script.parent)
    _inserted = utils_dir not in sys.path
    if _inserted:
        sys.path.insert(0, utils_dir)

    old_cwd = os.getcwd()
    os.chdir(str(WORKSPACE))
    ts = _dt.now()
    exit_code = 0
    mod_name = script.stem

    try:
        spec = importlib.util.spec_from_file_location(mod_name, str(script))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        old_argv = sys.argv[:]
        sys.argv = [str(script), "--project", project] + list(extra_argv or [])
        try:
            _ret = mod.main()
            # Captura exit code via return value (ex: remediate_summary.py retorna int sem sys.exit)
            if isinstance(_ret, int) and _ret != 0:
                exit_code = _ret
        finally:
            sys.argv = old_argv
    except SystemExit as e:
        exit_code = int(e.code) if e.code is not None else 0
    except Exception as e:
        print(f"{RED}  [BUILDER-ERR]  {type(e).__name__}: {e}{RESET}")
        exit_code = 1
    finally:
        os.chdir(old_cwd)
        if _inserted and utils_dir in sys.path:
            try:
                sys.path.remove(utils_dir)
            except ValueError:
                pass
        sys.modules.pop(mod_name, None)

    return exit_code, (_dt.now() - ts).total_seconds()


def _call_validator_direct(script: Path, project: str, auto_fix: bool = True) -> "tuple[int, float]":
    """Importa validate_summary.py e chama run_all() diretamente (sem subprocess)."""
    import importlib.util
    from datetime import datetime as _dt

    if not script.exists():
        print(f"{RED}  ❌  Script não encontrado: {script}{RESET}")
        return -1, 0.0

    utils_dir = str(script.parent)
    _inserted = utils_dir not in sys.path
    if _inserted:
        sys.path.insert(0, utils_dir)

    old_cwd = os.getcwd()
    os.chdir(str(WORKSPACE))
    ts = _dt.now()
    exit_code = 0
    mod_name = script.stem

    try:
        spec = importlib.util.spec_from_file_location(mod_name, str(script))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        exit_code = mod.run_all(project, strict=True, auto_fix=auto_fix, deep=True)
    except SystemExit as e:
        exit_code = int(e.code) if e.code is not None else 0
    except Exception as e:
        print(f"{RED}  [VALIDATOR-ERR]  {type(e).__name__}: {e}{RESET}")
        exit_code = 1
    finally:
        os.chdir(old_cwd)
        if _inserted and utils_dir in sys.path:
            try:
                sys.path.remove(utils_dir)
            except ValueError:
                pass
        sys.modules.pop(mod_name, None)

    return exit_code, (_dt.now() - ts).total_seconds()


def _find_summary_parts(project: str) -> list[Path]:
    """Encontra partes .partN.html do summary gerado em S1 ainda não unificadas.
    Retorna lista ordenada de paths de partes ou lista vazia se não houver partes."""
    summary_dir = WORKSPACE / "projects" / project / "outputs" / "summary"
    if not summary_dir.exists():
        return []
    parts: list[Path] = []
    for p in sorted(summary_dir.glob("*.part*.html")):
        parts.append(p)
    return parts


def _find_unified_summary(project: str) -> "Path | None":
    """Localiza o HTML unificado do summary (sem sufixo .partN) mais recente.

    Prioridade:
    1. HTML real (>=100KB) — gerado pelo builder determinístico com template oficial.
    2. HTML pequeno (<100KB) apenas como fallback se não há HTML real.

    Importante: usa timestamp de modificação (mtime), não ordem alfabética,
    para evitar selecionar um summary antigo quando coexistem nomes diferentes
    (ex.: "MeuERP-20260807" e "Meu-ERP-2026-08-07").
    """
    summary_dir = WORKSPACE / "projects" / project / "outputs" / "summary"
    if not summary_dir.exists():
        return None
    candidates = [
        p for p in summary_dir.glob("AVA-FABRIC-SUMMARY-*.html")
        if ".part" not in p.name and not p.name.endswith(".html.html")
    ]
    if not candidates:
        return None
    MIN_HTML_SIZE = 100_000  # 100KB — HTMLs < 100KB são LLM fallback sem template real
    real_candidates = [p for p in candidates if p.stat().st_size >= MIN_HTML_SIZE]
    # Prefere HTML real; fallback para qualquer HTML se nenhum real existe
    pool = real_candidates if real_candidates else candidates
    best = max(pool, key=lambda p: p.stat().st_mtime)
    if not real_candidates:
        print(f"  {YELLOW}  [WARN]  HTML encontrado é pequeno ({best.stat().st_size//1024}KB) "
              f"— provável LLM fallback sem template real. S2 irá reconstruir.{RESET}")
    # Escolhe o mais recente do pool selecionado (fonte de verdade para S2/S3/S4).
    return best


def _ensure_summary_unified(project: str) -> "Path | None":
    """Garante que o HTML do summary está unificado após S1.
    Se o unificado já existe e é maior que qualquer parte → OK.
    Se só existem partes → une-as e gera o unificado.
    Retorna o Path do unificado ou None se falhar.
    """
    unified = _find_unified_summary(project)
    parts   = _find_summary_parts(project)

    if not parts and unified:
        # Verifica se o arquivo unificado existente tem DOCTYPE duplicado (bug de merge anterior)
        try:
            existing_html = unified.read_text(encoding="utf-8", errors="replace")
            import re as _re
            dt_count = len(_re.findall(r'<!DOCTYPE\s+html', existing_html, _re.I))
            if dt_count > 1:
                print(f"  {YELLOW}  [SUMMARY-REPAIR]  HTML corrompido detectado: "
                      f"{dt_count}x DOCTYPE em {unified.name} — reparando...{RESET}")
                repaired = _html_repair_duplicate_documents(existing_html)
                unified.write_text(repaired, encoding="utf-8")
                print(f"  {GREEN}  [SUMMARY-REPAIR-OK]  {unified.name} reparado "
                      f"({unified.stat().st_size//1024}KB){RESET}")
        except Exception as _e:
            print(f"  {YELLOW}  [SUMMARY-REPAIR-SKIP]  Não foi possível verificar integridade: {_e}{RESET}")

        print(f"  {GREEN}  [SUMMARY-UNIFIED]  Já unificado: {unified.name}  "
              f"({unified.stat().st_size//1024}KB){RESET}")
        return unified

    if parts:
        # Determina nome-base a partir da primeira parte: stem sem .partN
        import re as _re
        first_stem = _re.sub(r'\.part\d+$', '', parts[0].stem)
        orig_ext   = parts[0].suffix  # ex: ".html"
        # Evita dupla extensão: stem pode já terminar em .html (ex: "summary.html")
        unified_name = first_stem if first_stem.lower().endswith(orig_ext.lower()) else first_stem + orig_ext
        unified_target = parts[0].parent / unified_name

        if unified_target.exists():
            unified_kb = unified_target.stat().st_size // 1024
            parts_kb   = sum(p.stat().st_size for p in parts) // 1024
            if unified_kb >= parts_kb * 0.9:
                # Unificado já tem conteúdo completo — não re-mescla
                print(f"  {GREEN}  [SUMMARY-UNIFIED]  Arquivo unificado OK: {unified_name}  "
                      f"({unified_kb}KB ≥ {parts_kb}KB das partes){RESET}")
                return unified_target
            else:
                print(f"  {YELLOW}  [SUMMARY-MERGE]  Unificado incompleto "
                      f"({unified_kb}KB vs {parts_kb}KB das partes) — re-mesclando...{RESET}")

        print(f"  {CYAN}  [SUMMARY-MERGE]  Unificando {len(parts)} partes → {unified_name}{RESET}")
        ok = _merge_parts(unified_target, parts)
        if ok:
            print(f"  {GREEN}  [SUMMARY-MERGE-OK]  {unified_name}  "
                  f"({unified_target.stat().st_size//1024}KB){RESET}")
            return unified_target
        else:
            print(f"  {RED}  [SUMMARY-MERGE-FAIL]  Não foi possível unificar as partes.{RESET}")
            return None

    print(f"  {YELLOW}  [SUMMARY-UNIFIED]  Nenhum arquivo de summary encontrado em outputs/summary/{RESET}")
    return None


def _run_summary_remediation_standalone(project: str) -> dict:
    """Executa S2 (remediation) via builder determinístico.

    Estratégia:
    - Sempre usa build_summary_comprehensive.py (builder atual com todos os fixes).
    - Se HTML existente < 100KB (gerado por LLM fallback): reconstrói do zero.
    - Se HTML existente >= 100KB (template real): remedia/corrige placeholders pendentes.
    - Aceita exit code 1 (warnings de validação) se HTML real foi gerado.
    """
    import subprocess
    from datetime import datetime

    print(f"\n{BOLD}[S2 Remediação — Build Direto]{RESET}")

    script_comprehensive = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                            / "summary" / "utils" / "build_summary_comprehensive.py")
    # NOTE: build_summary_complete.py is DEPRECATED — never use it here.
    # It has hardcoded "Delphi VCL Applications" scope, cannot parse top-level
    # array risk-register.json, and is missing several parser fixes present in
    # build_summary_comprehensive.py.

    # ── Gate: verificar HTML existente e escolher ação ────────────
    banner("[S2-Gate] Verificando HTML do summary...", CYAN)
    summary_dir = WORKSPACE / "projects" / project / "outputs" / "summary"
    MIN_HTML_SIZE = 100_000  # 100KB — HTMLs < 100KB são gerados pelo LLM fallback

    existing_htmls = [
        h for h in summary_dir.glob("AVA-FABRIC-SUMMARY-*.html")
        if ".part" not in h.name and not h.name.endswith(".html.html")
    ]
    real_htmls = [h for h in existing_htmls if h.stat().st_size >= MIN_HTML_SIZE]
    small_htmls = [h for h in existing_htmls if h.stat().st_size < MIN_HTML_SIZE]

    # Prefere remediate_summary.py (Fases 0–7: auditoria → síntese → rebuild → validate).
    # O script chama build_summary_comprehensive.py internamente na Fase 6 — não chamar os dois.
    # Fallback para build_summary_comprehensive.py somente se remediate_summary.py não existir.
    script_remediate = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                        / "summary" / "utils" / "remediate_summary.py")
    if script_remediate.exists():
        script = script_remediate
        if real_htmls:
            real_htmls.sort(key=lambda h: h.stat().st_mtime, reverse=True)
            best_html = real_htmls[0]
            print(f"  {GREEN}  ✅  [S2] HTML real encontrado: {best_html.name}  "
                  f"({best_html.stat().st_size//1024}KB) — executando remediação completa (Fases 0–7).{RESET}")
        else:
            if small_htmls:
                print(f"  {YELLOW}  [S2-REBUILD]  HTML existente ({small_htmls[0].stat().st_size//1024}KB) "
                      f"gerado por LLM fallback — remediação completa reconstruirá com template real.{RESET}")
            else:
                print(f"  {YELLOW}  [S2-REBUILD]  Nenhum HTML encontrado — remediação completa gerará do zero.{RESET}")
        script_label = "remediate_summary.py (Fases 0–7: auditoria + síntese + rebuild + validate)"
    else:
        # Fallback legado: sem Fases 0–5 de pré-processamento
        print(f"  {YELLOW}  [S2-WARN]  remediate_summary.py não encontrado — usando builder direto "
              f"(Fases 0–5 de pré-processamento serão puladas).{RESET}")
        script = script_comprehensive
        if real_htmls:
            real_htmls.sort(key=lambda h: h.stat().st_mtime, reverse=True)
            best_html = real_htmls[0]
            print(f"  {GREEN}  ✅  [S2] HTML real encontrado: {best_html.name}  "
                  f"({best_html.stat().st_size//1024}KB){RESET}")
            script_label = f"{script.name} (remediar placeholders pendentes)"
        else:
            if small_htmls:
                print(f"  {YELLOW}  [S2-REBUILD]  HTML existente ({small_htmls[0].stat().st_size//1024}KB) "
                      f"é muito pequeno (LLM fallback) — reconstruindo com template real.{RESET}")
            else:
                print(f"  {YELLOW}  [S2-REBUILD]  Nenhum HTML encontrado — executando builder.{RESET}")
            script_label = f"{script.name} (gerar do zero)"

    if not script.exists():
        print(f"{RED}  ❌  Nenhum script de builder encontrado.{RESET}")
        return {"phase": "S2", "agent": "ava-summary-remediation", "val_ok": False, "resp_tokens": 0,
                "skill_kb": 0, "inp_tokens": 0, "out_max": 0, "ctx_pct": 0.0, "elapsed_s": 0.0, "artifacts": 0}

    # playwright gate para S2: remediate_summary.py usa playwright na Fase 3.5.
    # Com --skip-mermaid-gate as Fases 0–5 ainda correm (síntese de artefatos,
    # sanitização Mermaid sem browser, reconciliação de segurança); só o gate
    # de validação Playwright/Mermaid é desativado.  build_summary_comprehensive.py
    # (fallback) não suporta --skip-mermaid-gate, então o flag é usado apenas quando
    # script == script_remediate.
    import importlib.util as _ilu_s2
    _playwright_ok_s2 = _ilu_s2.find_spec("playwright") is not None
    _s2_extra: "list[str]" = []
    if script == script_remediate and not _playwright_ok_s2:
        _s2_extra = ["--skip-mermaid-gate"]
        print(f"  {YELLOW}  [S2-WARN]  playwright não instalado — "
              f"Phase 3.5 (Mermaid gate) será pulada (--skip-mermaid-gate).{RESET}")
        print(f"  {YELLOW}       Instale com: pip install playwright && python -m playwright install{RESET}")

    print(f"{DIM}  Executando: {script_label} --project {project}"
          f"{' --skip-mermaid-gate' if _s2_extra else ''}{RESET}\n")
    ts_start = datetime.now()
    ts_before = ts_start.timestamp()
    try:
        exit_code, elapsed = _call_builder_direct(script, project, _s2_extra)

        new_real_htmls = [
            h for h in summary_dir.glob("AVA-FABRIC-SUMMARY-*.html")
            if ".part" not in h.name
            and not h.name.endswith(".html.html")
            and h.stat().st_size >= MIN_HTML_SIZE
            and h.stat().st_mtime >= ts_before - 5
        ]
        reports = list(summary_dir.glob("remediation-report.*"))
        remediation_ok = bool(new_real_htmls) or len(reports) > 0 or exit_code == 0

        if new_real_htmls:
            new_real_htmls.sort(key=lambda h: h.stat().st_mtime, reverse=True)
            html = new_real_htmls[0]
            print(f"\n{GREEN}  ✅  [S2-OK]  HTML real gerado/atualizado: {html.name}  "
                  f"({html.stat().st_size//1024}KB){RESET}")
        elif remediation_ok:
            print(f"\n{GREEN}  ✅  [S2-OK]  Remediation completa (exit {exit_code}){RESET}")
        else:
            print(f"\n{YELLOW}  ⚠️  [S2-PARTIAL]  Build retornou {exit_code} sem HTML real ou relatório{RESET}")

        artifacts_count = len(new_real_htmls) + len(reports)
        return {
            "phase": "S2",
            "agent": "ava-summary-remediation",
            "skill_kb": 16,
            "inp_tokens": 0,
            "out_max": 0,
            "resp_tokens": 0,
            "ctx_pct": 0.0,
            "elapsed_s": elapsed,
            "artifacts": artifacts_count,
            "val_ok": remediation_ok,
        }
    except Exception as e:
        print(f"{RED}  ❌  Erro: {e}{RESET}")
        return {"phase": "S2", "agent": "ava-summary-remediation", "val_ok": False, "resp_tokens": 0,
                "skill_kb": 0, "inp_tokens": 0, "out_max": 0, "ctx_pct": 0.0, "elapsed_s": 0.0, "artifacts": 0}


def _run_summary_generate_standalone(project: str, phase: str = "S1") -> dict:
    """Executa S1/S4 (geração do Summary HTML) via builder determinístico.

    Sempre usa build_summary_comprehensive.py (builder atual com todos os fixes).
    build_summary_complete.py está DEPRECATED e nunca deve ser chamado aqui.

    O HTML é aceito se existir e tiver tamanho > 100KB (garante que é o template real,
    não um HTML genérico de 40KB gerado pelo LLM).

    Exit code do builder é ignorado para aceitação do HTML — o gate de validação
    não deve impedir a publicação do relatório. Apenas a ausência do arquivo bloqueia.

    Retorna None se o script não existir (sinaliza ao run_step para usar LLM fallback).
    """
    import subprocess
    from datetime import datetime

    script_comprehensive = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                            / "summary" / "utils" / "build_summary_comprehensive.py")
    # NOTE: build_summary_complete.py is DEPRECATED — never use it here.

    if script_comprehensive.exists():
        script = script_comprehensive
        script_label = "build_summary_comprehensive.py (dados completos — risks/bc/owasp/dbSchema/gaps)"
    else:
        return None  # type: ignore[return-value]  # sinaliza fallback para LLM

    # ── Gate: playwright Python package — verificar ANTES de chamar o builder ──────
    # A Phase G do builder (validação Mermaid via Playwright) é a ÚNICA etapa que usa o
    # package Python playwright — e está wrappada em try/except (NÃO-FATAL, linha ~9623 do builder).
    # O compat gate usa discover_browser_executable() (binário Chromium), não o package Python.
    # Logo: se o package Python playwright NÃO estiver instalado, o builder ainda gera HTML;
    # a solução correta é passar --skip-mermaid-gate para desativar a Phase G explicitamente,
    # em vez de bloquear S1/S4 e impedir qualquer geração de summary.
    import importlib.util as _ilu
    _s14_extra: "list[str]" = []
    if _ilu.find_spec("playwright") is None:
        _s14_extra = ["--skip-mermaid-gate"]
        print(f"\n{YELLOW}  ⚠️  [{phase}-WARN]  playwright não instalado — Phase G (Mermaid gate) "
              f"será pulada (--skip-mermaid-gate).{RESET}")
        print(f"  {YELLOW}       Instale para validação Mermaid: pip install playwright && "
              f"python -m playwright install{RESET}")
        print(f"       O HTML será gerado sem validação de renderização dos diagramas.{RESET}")

    banner(f"[{phase}] Gerando Summary HTML — Builder Determinístico", CYAN)
    print(f"  {DIM}  Script: {script_label}{RESET}")
    print(f"  {DIM}  Projeto: {project}{RESET}")
    print(f"  {DIM}  Vantagem: HTML inteiro em um único arquivo, sem partes, sem DOCTYPE duplicado.{RESET}\n")

    # ── Timestamp antes de executar (para detectar HTML novo) ─────
    ts_start = datetime.now()
    ts_before = ts_start.timestamp()

    # Chamada direta via importlib (sem subprocess) — saída em tempo real
    exit_code, elapsed = _call_builder_direct(script, project, _s14_extra)

    # ── Localiza HTML gerado nesta execução ────────────────────
    summary_dir = WORKSPACE / "projects" / project / "outputs" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    all_htmls = [
        h for h in summary_dir.glob("AVA-FABRIC-SUMMARY-*.html")
        if ".part" not in h.name and not h.name.endswith(".html.html")
    ]
    new_htmls = [h for h in all_htmls if h.stat().st_mtime >= ts_before - 5]
    MIN_HTML_SIZE = 100_000  # 100KB
    real_new  = [h for h in new_htmls if h.stat().st_size >= MIN_HTML_SIZE]
    real_all  = [h for h in all_htmls  if h.stat().st_size >= MIN_HTML_SIZE]

    if real_new:
        candidate_list = real_new
    else:
        candidate_list = real_all
    candidate_list.sort(key=lambda h: h.stat().st_mtime, reverse=True)

    if candidate_list:
        html = candidate_list[0]
        content = html.read_text(encoding="utf-8", errors="replace")
        import re as _re
        dt_count = len(_re.findall(r'<!DOCTYPE\s+html', content, _re.I))
        if dt_count > 1:
            print(f"  {YELLOW}  [REPAIR]  HTML com {dt_count}x DOCTYPE — reparando...{RESET}")
            content = _html_repair_duplicate_documents(content)
            html.write_text(content, encoding="utf-8")
        size_kb = html.stat().st_size // 1024
        source = "novo" if html in real_new else "existente"
        print(f"\n{GREEN}  ✅  [{phase}-OK]  HTML gerado ({source}): {html.name}  "
              f"({size_kb}KB) — template real, 1 arquivo.{RESET}")
        if exit_code != 0:
            print(f"  {DIM}  (builder saiu com exit {exit_code} — warnings de validação ignorados){RESET}")
        ok = True
        htmls_found = [html]
    else:
        small_htmls = [h for h in all_htmls if h.stat().st_size < MIN_HTML_SIZE]
        if small_htmls:
            print(f"  {YELLOW}  [WARN]  Encontrado(s) {len(small_htmls)} HTML(s) < 100KB — ignorados "
                  f"(provavelmente gerados pelo LLM fallback em execução anterior).{RESET}")
        print(f"\n{YELLOW}  ⚠️  [{phase}-BLOCKED]  Builder não gerou HTML com template real "
              f"(exit {exit_code}). Motivo no stdout acima.{RESET}")
        # Se chegou aqui com playwright instalado, a falha é por outro motivo (artefatos ausentes,
        # erro de parsing, etc.). O LLM fallback em run_step() pode tentar recuperar nesse caso.
        ok = False
        htmls_found = []

    return {
        "phase":       phase,
        "agent":       "ava-summary",
        "skill_kb":    385,
        "inp_tokens":  0,
        "out_max":     0,
        "resp_tokens": 0,
        "ctx_pct":     0.0,
        "elapsed_s":   elapsed,
        "artifacts":   len(htmls_found),
        "val_ok":      ok,
    }


def _run_summary_validate_standalone(project: str) -> dict:
    """Executa S3 (validação) via subprocess direto em validate_summary.py.
    Não usa LLM — executa o validador Python diretamente.
    Garante que o HTML do summary está unificado ANTES de validar.

    O validador suporta --project, --fix e --strict/--no-fix.
    """
    import subprocess
    from datetime import datetime

    print(f"\n{BOLD}[S3 Validação — Audit Direto]{RESET}")

    # ── Gate: garantir HTML unificado antes de validar ────────────
    banner("[S3-Gate] Verificando HTML unificado do summary...", CYAN)
    unified_html = _ensure_summary_unified(project)
    if unified_html is None:
        print(f"{RED}  ❌  [S3] BLOQUEADO: HTML do summary não encontrado ou não pôde ser unificado.")
        print(f"  Execute S1 primeiro ou verifique outputs/summary/.{RESET}")
        return {"phase": "S3", "agent": "ava-summary-validate", "val_ok": False, "resp_tokens": 0,
                "skill_kb": 0, "inp_tokens": 0, "out_max": 0, "ctx_pct": 0.0, "elapsed_s": 0.0, "artifacts": 0}
    print(f"  {GREEN}  ✅  [S3] HTML unificado confirmado: {unified_html.name}  "
          f"({unified_html.stat().st_size//1024}KB){RESET}")
    print(f"{DIM}  Executando: validate_summary.py --project {project} --fix{RESET}\n")

    script = WORKSPACE / "src" / "modules" / "ava-fabric-agents" / "summary" / "utils" / "validate_summary.py"
    if not script.exists():
        print(f"{RED}  ❌  Script não encontrado: {script.relative_to(WORKSPACE)}{RESET}")
        return {"phase": "S3", "agent": "ava-summary-validate", "val_ok": False, "resp_tokens": 0}

    ts_start = datetime.now()
    try:
        exit_code, elapsed = _call_validator_direct(script, project, auto_fix=True)

        reports = list((WORKSPACE / "projects" / project / "outputs" / "summary").glob("validation-report.*"))
        validation_ok = len(reports) > 0 or exit_code in (0, 1)

        if validation_ok:
            if exit_code == 0:
                print(f"\n{GREEN}  ✅  [S3-PASS]  Validação PASSOU — sem erros críticos{RESET}")
            else:
                print(f"\n{YELLOW}  ⚠️  [S3-WARN]  Validação concluída com warnings "
                      f"(exit {exit_code}) — relatório gerado{RESET}")
        else:
            print(f"\n{YELLOW}  ⚠️  [S3-FAIL]  Validação encontrou erros críticos (exit {exit_code}){RESET}")

        return {
            "phase": "S3",
            "agent": "ava-summary-validate",
            "skill_kb": 22,
            "inp_tokens": 0,
            "out_max": 0,
            "resp_tokens": 0,
            "ctx_pct": 0.0,
            "elapsed_s": elapsed,
            "artifacts": len(reports),
            "val_ok": validation_ok,
        }
    except Exception as e:
        print(f"{RED}  ❌  Erro: {e}{RESET}")
        return {"phase": "S3", "agent": "ava-summary-validate", "val_ok": True, "resp_tokens": 0,
                "skill_kb": 22, "inp_tokens": 0, "out_max": 0, "ctx_pct": 0.0, "elapsed_s": 0.0, "artifacts": 0}


def build_prompt(agent: str, trigger: str | None, project: str,
                 feature: str | None = None) -> str:
    """Monta o comando de invocação do agente.

    `feature:` só aparece em passos vindos do fan-out por DAG — é como o agente
    sabe qual fonte lhe cabe quando o mesmo id é despachado N vezes.
    """
    agent_ref = f"@{agent}"
    sufixo = f" | feature: {feature}" if feature else ""
    if trigger:
        return f"{agent_ref} | {trigger} | project: {project}{sufixo}"
    return f"{agent_ref} project: {project}{sufixo}"


# Fases que usam ava-summary e precisam do template HTML injetado
_SUMMARY_TEMPLATE_PHASES = {"S1", "S4"}


def build_system_prompt(agent: str, skill_content: str, project: str, context: str,
                        out_tokens: int = MAX_TOKENS,
                        phase: str = "") -> str:
    """Cria o system prompt com contexto real do projeto injetado."""
    out_chars_approx = out_tokens * 4   # ~4 chars por token

    # ── Summary template: injeta APENAS os primeiros 20KB do template (cabeçalho + CSS vars)
    # O template completo tem 475KB (≈118K tokens) — injetar tudo esgotaria o input
    # e deixaria apenas ~10K tokens para o contexto do projeto.
    # Estratégia: injeta as primeiras linhas para o modelo conhecer a estrutura,
    # e instrui a usar o template a partir do disco via build_summary_comprehensive.py.
    # NOTA: Se o LLM fallback for acionado (builder falhou), o modelo deve gerar
    # um HTML compacto com os dados do projeto, dividido em partes se necessário.
    summary_template_section = ""
    if phase in _SUMMARY_TEMPLATE_PHASES:
        html_template = _load_summary_html_template()
        if html_template:
            # Injeta apenas os primeiros 15KB do template — suficiente para o modelo
            # entender a estrutura, placeholders e CSS sem consumir a janela de input.
            TEMPLATE_PREVIEW_CHARS = 15_000
            template_preview = html_template[:TEMPLATE_PREVIEW_CHARS]
            template_size_kb = len(html_template) // 1024
            summary_template_section = (
                f"\n\n## TEMPLATE HTML DO SUMMARY (summary-template.html — {template_size_kb}KB total)"
                f"\n\n⚠️ IMPORTANTE: O template completo tem {template_size_kb}KB e NÃO pode ser "
                f"reproduzido integralmente no output (limite de {out_tokens:,} tokens)."
                f"\n\nESTRATÉGIA OBRIGATÓRIA para S1/S4:"
                f"\n1. Use o builder determinístico disponível em:"
                f"\n   `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`"
                f"\n2. Se o builder não puder ser chamado: gere um HTML COMPACTO (máx 3 partes)"
                f"\n   usando a estrutura do template mostrada abaixo como referência."
                f"\n3. O HTML deve ter: navbar lateral, seção KPIs, seção riscos, seção segurança,"
                f"\n   seção artefatos — populados com dados REAIS dos artefatos do projeto."
                f"\n4. Divida em parts (.part1.html, .part2.html) se necessário."
                f"\n\n### Início do template (primeiros {TEMPLATE_PREVIEW_CHARS//1024}KB — apenas referência):\n\n"
                f"```html\n{template_preview}\n[... restante do template omitido — use o builder ...]\n```"
            )

    return f"""Você é o agente AVA Fabric '{agent}' operando no pipeline de modernização de sistemas legados.

PROJETO ATIVO: {project}
WORKSPACE: {WORKSPACE}
PROJETO PATH: {WORKSPACE}/projects/{project}/
JANELA DE CONTEXTO: 1,000,000 tokens input disponíveis — use todo o contexto necessário
LIMITE DE SAÍDA: {out_tokens:,} tokens (≈{out_chars_approx:,} chars) — planeje o tamanho dos artefatos dentro desse limite

## CONTEXTO DO PROJETO (lido do disco)

{context}

## SKILL DO AGENTE

{skill_content}{summary_template_section}

## REGRAS DE EXECUÇÃO — OBRIGATÓRIAS

### FORMATO DE SAÍDA — ÚNICA FORMA ACEITA
Para CADA arquivo que precisar criar, use EXCLUSIVAMENTE este bloco:

<!-- FILE: projects/{project}/outputs/<caminho_relativo> -->
[conteúdo completo do arquivo aqui]
<!-- /FILE -->

### PROIBIÇÕES ABSOLUTAS
- ❌ NÃO use <tool_call>, <tool_response> ou qualquer bloco de ferramenta
- ❌ NÃO use Bash(), Read(), Write() ou funções de shell
- ❌ NÃO use WriteAllText, New-Item ou comandos PowerShell
- ❌ NÃO simule execução de comandos — apenas gere o conteúdo dos arquivos
- ❌ NÃO use placeholder — gere conteúdo REAL e COMPLETO em cada arquivo
- ❌ NÃO gere fora de projects/{project}/outputs/ (ex: src/, tmp/, /etc/)
- ❌ NÃO faça perguntas nem encerre a resposta aguardando confirmação

### MODO NÃO-INTERATIVO — NÃO HÁ SEGUNDO TURNO
Esta é uma chamada única: a sua resposta é o resultado final da fase e ninguém
pode responder a uma pergunta sua. Onde o seu pre-flight mandar pedir
confirmação para artefato OPCIONAL ausente, ela já foi decidida pelo runner
antes deste despacho — siga a diretriz que veio no prompt do usuário. Não
havendo diretriz, considere `DECISÃO: PROSSEGUIR COM AVISOS`: aplique os
fallbacks do seu corpo, gere os artefatos e registre a degradação na saída.
Artefato OBRIGATÓRIO ausente continua sendo bloqueio — aí sim pare e explique.

### OBRIGAÇÕES
- ✅ Gere TODOS os artefatos listados no Output Contract do skill
- ✅ Use SOMENTE blocos <!-- FILE: ... --> / <!-- /FILE -->
- ✅ Caminho deve começar com: projects/{project}/outputs/
- ✅ Ao final, liste os arquivos gerados em tabela Markdown

### ⚠️ REGRA CRÍTICA — LIMITE DE {out_tokens:,} TOKENS
Você tem {out_tokens:,} tokens de saída (≈{out_chars_approx:,} chars). Planeje o tamanho
dos artefatos para caber nesse limite. Prefira comprimir conteúdo a truncar.

O extrator suporta dois modos:
  ✓ IDEAL:   bloco fechado com <!-- /FILE --> — sempre preferível
  ⚠ FALLBACK: sem <!-- /FILE --> — o extrator salva o que existir mas o arquivo pode estar incompleto

Estrutura padrão:
<!-- FILE: projects/{project}/outputs/<caminho> -->
[CONTEÚDO COMPLETO — comprima CSS/JS/comentários se necessário]
<!-- /FILE -->

### ESTRATÉGIA PARA ARQUIVOS GRANDES (HTML, relatórios extensos)
Se um arquivo não couber em {out_tokens:,} tokens, divida-o em partes consecutivas
usando sufixo .part1, .part2, etc. O extrator une as partes automaticamente:

<!-- FILE: projects/{project}/outputs/<pasta>/<nome>.part1.<ext> -->
[primeira parte — corte em ponto lógico: </section>, </div>, </tr> ou linha em branco]
<!-- /FILE -->

<!-- FILE: projects/{project}/outputs/<pasta>/<nome>.part2.<ext> -->
[segunda parte — inclua o fechamento final do arquivo (ex: </body></html>)]
<!-- /FILE -->

REGRAS para split:
- Prefira 1 arquivo compacto a 2 partes — só divida se realmente necessário
- Corte SEMPRE em ponto lógico (entre tags, nunca no meio de uma tag ou atributo)
- A última parte DEVE conter o fechamento completo do arquivo
- SEMPRE feche cada bloco com <!-- /FILE --> antes de abrir o próximo
"""


def _status_bar(active_steps: list, idx: int, executed: list, skipped: list) -> str:
    """Gera linha de status compacta com emoji por fase."""
    parts = []
    for i, s in enumerate(active_steps):
        ph = s["phase"]
        if ph in executed:
            parts.append(f"{GREEN}✅{ph}{RESET}")
        elif ph in skipped:
            parts.append(f"{YELLOW}⏭{ph}{RESET}")
        elif i == idx:
            parts.append(f"{CYAN}{BOLD}▶{ph}{RESET}")
        else:
            parts.append(f"{DIM}○{ph}{RESET}")
    return "  " + "  ".join(parts)


def ask_permission(step: dict, idx: int, total: int, auto: bool = False,
                   executed: list | None = None, skipped: list | None = None,
                   active_steps: list | None = None) -> str:
    """
    Pergunta ao usuário se deve executar o passo.
    Retorna: 'S' (sim), 'N'/'P' (pular), 'A' (abortar), 'V' (ver skill)
    """
    phase  = step["phase"]
    label  = step["label"]
    agent  = step["agent"]
    trigger= step["trigger"]

    print(f"\n{YELLOW}{'═'*60}{RESET}")
    print(f"{YELLOW}{BOLD}  Passo {idx+1}/{total} — {phase}{RESET}")
    print(f"{YELLOW}  {label}{RESET}")
    print(f"{DIM}  Agente : @{agent}{RESET}")
    if trigger:
        print(f"{DIM}  Trigger: {trigger}{RESET}")
    print(f"{YELLOW}{'═'*60}{RESET}")
    if active_steps is not None and executed is not None and skipped is not None:
        print(_status_bar(active_steps, idx, executed or [], skipped or []))

    if auto:
        print(f"  {DIM}[AUTO] Executando automaticamente...{RESET}")
        return "S"

    while True:
        resp = safe_input(f"\n  {BOLD}Executar? [S]im / [P]ular / [V]er skill / [A]bortar: {RESET}").strip().upper()
        if resp in ("S", ""):
            return "S"
        if resp in ("P", "N"):
            return "P"
        if resp == "V":
            return "V"
        if resp == "A":
            return "A"
        print(f"  {RED}Digite S, P, V ou A.{RESET}")


def run_ast_step(step: dict, project: str, output_dir: Path) -> dict:
    """Executa a extração AST determinística via subprocess (sem LLM).

    Regra principal:
      - Se ava_ast_analyzer_path (ou ava_ast_analyzers[lang]) estiver configurado
        E o path existir no disco → executa run_ast_analysis.py.
      - Se o campo estiver vazio/ausente → pula F0 silenciosamente (val_ok=True,
        sem erro) e os agentes F1 usam análise pattern-based normalmente.

    NÃO bloqueia o pipeline em nenhum caso.
    """
    import yaml as _yaml

    phase = step["phase"]
    ts_start = datetime.datetime.now()

    banner("F0 — Extração AST Determinística", CYAN)

    # ── Ler project-config ────────────────────────────────────────
    config_path = WORKSPACE / "projects" / project / "context" / "project-config.yaml"
    try:
        cfg = _yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  {RED}❌  Não foi possível ler project-config.yaml: {e}{RESET}")
        return {"phase": phase, "agent": "_ast_extractor", "skill_kb": 0,
                "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
                "ctx_pct": 0, "elapsed_s": 0, "artifacts": 0, "val_ok": True}

    legacy_tech     = (cfg.get("legacy_technology") or "").strip().lower()
    repository_path = (cfg.get("repository_path") or "").strip()

    # ── Resolver path do analyzer a partir do config ──────────────
    # Precedência (espelha exatamente o _get_analyzer_home() do run_ast_analysis.py):
    #   1. ava_ast_analyzers[legacy_technology]  ← mapa multi-linguagem
    #   2. ava_ast_analyzer_path                 ← alias legado (qualquer linguagem)
    # Se nenhum estiver configurado → SKIP (não tenta env vars nem sibling repo;
    # o runner exige configuração explícita para garantir rastreabilidade).
    analyzers_map    = cfg.get("ava_ast_analyzers") or {}
    analyzer_path_str = ""
    if isinstance(analyzers_map, dict) and legacy_tech:
        analyzer_path_str = (analyzers_map.get(legacy_tech) or "").strip()
    if not analyzer_path_str:
        analyzer_path_str = (cfg.get("ava_ast_analyzer_path") or "").strip()

    # ── Gate: sem path configurado → pular F0 ─────────────────────
    if not analyzer_path_str:
        print(f"  {YELLOW}⏭  ava_ast_analyzer_path não configurado em project-config.yaml.{RESET}")
        print(f"  {DIM}  F0 pulado — agentes F1 usarão análise pattern-based (comportamento normal).{RESET}")
        print(f"  {DIM}  Para ativar AST, adicione ao project-config.yaml:{RESET}")
        print(f"  {DIM}    ava_ast_analyzer_path: \"<path>/ava-fabric-{legacy_tech or 'delphi'}-analyzer\"{RESET}")
        elapsed = (datetime.datetime.now() - ts_start).total_seconds()
        _save_f0_log(output_dir, project, [], legacy_tech, analyzer_path_str,
                 repository_path, True, "SKIPPED — não configurado", 0, ts_start)
        return {"phase": phase, "agent": "_ast_extractor", "skill_kb": 0,
                "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
                "ctx_pct": 0, "elapsed_s": elapsed, "artifacts": 0, "val_ok": True}

    # ── Gate: path configurado mas não existe no disco ────────────
    analyzer_path = Path(analyzer_path_str)
    if not analyzer_path.exists():
        print(f"  {RED}❌  analyzer path configurado mas não encontrado: {analyzer_path_str}{RESET}")
        print(f"  {YELLOW}  ⚠️  F0 pulado — verifique o path em project-config.yaml.{RESET}")
        elapsed = (datetime.datetime.now() - ts_start).total_seconds()
        _save_f0_log(output_dir, project, [], legacy_tech, analyzer_path_str,
                 repository_path, True, f"SKIPPED — path não existe: {analyzer_path_str}", 0, ts_start)
        return {"phase": phase, "agent": "_ast_extractor", "skill_kb": 0,
                "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
                "ctx_pct": 0, "elapsed_s": elapsed, "artifacts": 0, "val_ok": True}

    # ── Gate: run_ast_analysis.py existe? ─────────────────────────
    run_ast_py = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                  / "asis-diagnostic" / "utils" / "run_ast_analysis.py")
    if not run_ast_py.exists():
        print(f"  {RED}❌  run_ast_analysis.py não encontrado em {run_ast_py}{RESET}")
        print(f"  {YELLOW}  ⚠️  F0 pulado — agentes F1 usarão análise pattern-based.{RESET}")
        return {"phase": phase, "agent": "_ast_extractor", "skill_kb": 0,
                "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
                "ctx_pct": 0, "elapsed_s": 0, "artifacts": 0, "val_ok": True}

    # ── Re-entrância: AST já existe? ──────────────────────────────
    lang_key = legacy_tech or "delphi"
    ast_manifest = (WORKSPACE / "projects" / project / "outputs" / "asis"
                    / "ast-raw" / lang_key / "compressed" / "manifest.json")
    if ast_manifest.exists():
        print(f"  {GREEN}✅  AST já extraído ({ast_manifest.relative_to(WORKSPACE)}) — pulando re-extração.{RESET}")
        elapsed = (datetime.datetime.now() - ts_start).total_seconds()
        return {"phase": phase, "agent": "_ast_extractor", "skill_kb": 0,
                "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
                "ctx_pct": 0, "elapsed_s": elapsed, "artifacts": 1, "val_ok": True}

    # ── Tudo OK — montar e executar comando ───────────────────────
    # run_ast_analysis.py lê ava_ast_analyzer_path do project-config.yaml internamente.
    # Passamos apenas --project e --language; o script resolve o analyzer path sozinho.
    # --brs-llm: etapas 5-8 do BRS (interpretação por LLM). run_ast_analysis.py
    # resolve as credenciais Azure OpenAI a partir do .env da raiz do repo.
    brs_llm_enabled = True
    cmd = [sys.executable, str(run_ast_py), "--project", project, "--brs-llm"]
    if legacy_tech:
        cmd += ["--language", legacy_tech]

    print(f"  {DIM}  legacy_technology : {legacy_tech or '(auto-detect)'}{RESET}")
    print(f"  {DIM}  analyzer path     : {analyzer_path_str}{RESET}")
    print(f"  {DIM}  brs_llm           : {'ON (forçado pelo runner F0)' if brs_llm_enabled else 'OFF'}{RESET}")
    if repository_path:
        print(f"  {DIM}  repository_path   : {repository_path}{RESET}")
    print(f"  {DIM}  Comando: {' '.join(cmd)}{RESET}")
    print(f"\n  {CYAN}Executando extração AST (pode levar alguns minutos)...{RESET}\n")
    print(f"{CYAN}{'─'*60}{RESET}")

    # ── Executar com output em tempo real ─────────────────────────
    ast_ok    = False
    n_arts    = 0
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(WORKSPACE),
        )
        log_lines: list[str] = []
        for line in proc.stdout:  # type: ignore[union-attr]
            print(f"  {DIM}{line.rstrip()}{RESET}", flush=True)
            log_lines.append(line)
        proc.wait()

        if proc.returncode == 0:
            ast_ok = True
            print(f"\n  {GREEN}✅  Extração AST concluída (exit 0).{RESET}")
            # Contar JSONs gerados
            ast_out = WORKSPACE / "projects" / project / "outputs" / "asis" / "ast-raw"
            if ast_out.exists():
                n_arts = sum(1 for _ in ast_out.rglob("*.json"))
            print(f"  {GREEN}  {n_arts} artefatos JSON gerados em outputs/asis/ast-raw/{RESET}")
        else:
            print(f"\n  {RED}❌  Extração AST falhou (exit {proc.returncode}).{RESET}")
            print(f"  {YELLOW}  ⚠️  Agentes F1 usarão análise pattern-based (confiança reduzida).{RESET}")

    except Exception as e:
        print(f"\n  {RED}❌  Erro ao executar run_ast_analysis.py: {e}{RESET}")
        print(f"  {YELLOW}  ⚠️  Agentes F1 usarão análise pattern-based (confiança reduzida).{RESET}")

    print(f"{CYAN}{'─'*60}{RESET}")

    status_str = "✅ SUCESSO" if ast_ok else "❌ FALHOU"
    _save_f0_log(output_dir, project, cmd, legacy_tech, analyzer_path_str,
                 repository_path, brs_llm_enabled, status_str, n_arts, ts_start)

    elapsed = (datetime.datetime.now() - ts_start).total_seconds()
    return {
        "phase":       phase,
        "agent":       "_ast_extractor",
        "skill_kb":    0,
        "inp_tokens":  0,
        "out_max":     0,
        "resp_tokens": 0,
        "ctx_pct":     0.0,
        "elapsed_s":   elapsed,
        "artifacts":   n_arts,
        "val_ok":      ast_ok,
    }


def _save_f0_log(output_dir: Path, project: str, cmd: list,
                 legacy_tech: str, analyzer_path: str,
                 repository_path: str, brs_llm_enabled: bool, status_str: str,
                 n_arts: int, ts_start: "datetime.datetime") -> None:
    """Salva o log da execução F0 em pipeline_runner/."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"F0_ast-extractor_{ts}.md"
    cmd_str  = " ".join(cmd) if cmd else "(não executado)"
    out_file.write_text(
        f"# F0 — AST Extraction\n\n"
        f"**Agente:** _ast_extractor (subprocess)  \n"
        f"**Projeto:** {project}  \n"
        f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
        f"**Status:** {status_str}  \n"
        f"**BRS LLM:** {'ON' if brs_llm_enabled else 'OFF'}  \n"
        f"**Artefatos JSON:** {n_arts}  \n\n"
        f"---\n\n"
        f"## Comando executado\n\n```\n{cmd_str}\n```\n\n"
        f"## Config lida\n\n"
        f"- `legacy_technology`: {legacy_tech or '(auto-detect)'}\n"
        f"- `ava_ast_analyzer_path`: {analyzer_path or '(não configurado)'}\n"
        f"- `brs_llm`: {'ON' if brs_llm_enabled else 'OFF'}\n"
        f"- `repository_path`: {repository_path}\n",
        encoding="utf-8",
    )
    print(f"\n  {GREEN}✅ Log salvo: {out_file.relative_to(WORKSPACE)}{RESET}")


def _stream_openai(api_key: str, system_prompt: str, user_prompt: str,
                  out_tokens: int, base_url: str = "",
                  stream_guard=None, on_chunk=None) -> "tuple[str, str, int, int]":
    """Streaming OpenAI via SSE puro (requests) — sem SDK adicional.
    Retorna (full_response, stop_reason, inp_tokens, resp_tokens).
    stop_reason é normalizado para o convênção Anthropic (max_tokens / end_turn).
    base_url: quando fornecido (headroom proxy), usa /chat/completions relativo ao proxy.
    """
    import json

    if base_url:
        # Headroom proxy ativo — base_url já inclui /v1; apenas apenda o path padrão OpenAI
        url = f"{base_url.rstrip('/')}/chat/completions"
    else:
        url = (
            f"https://aif-imf-apps-prd-eus2-001.services.ai.azure.com"
            f"/openai/deployments/{DEPLOYMENT}/chat/completions"
            f"?api-version=2024-12-01-preview"
        )
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        # Compatibilidade: alguns deployments (ex.: gpt-5.6-luna) exigem
        # max_completion_tokens e não aceitam temperature customizado.
        "max_completion_tokens": out_tokens,
        "stream":         True,
        "stream_options": {"include_usage": True},
    }

    full_response = ""
    stop_reason   = "unknown"
    inp_tokens    = (len(system_prompt) + len(user_prompt)) // 4
    resp_tokens   = 0

    _req_headers = (
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if base_url else
        {"api-key": api_key, "Content-Type": "application/json"}
    )
    with _requests.post(
        url,
        headers=_req_headers,
        json=payload,
        stream=True,
        timeout=600,
    ) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except Exception:
                continue
            choices = chunk.get("choices", [])
            if choices:
                text = choices[0].get("delta", {}).get("content") or ""
                if text:
                    full_response += text
                    if stream_guard:
                        stream_guard.write(text)
                    else:
                        print(text, end="", flush=True)
                    if on_chunk:
                        on_chunk(full_response)
                fr = choices[0].get("finish_reason")
                if fr:
                    # normaliza para convenção Anthropic usada pelo resto do pipeline
                    stop_reason = "max_tokens" if fr == "length" else "end_turn"
            usage = chunk.get("usage")
            if usage:
                inp_tokens  = usage.get("prompt_tokens",     inp_tokens)
                resp_tokens = usage.get("completion_tokens", resp_tokens)

    if not resp_tokens:
        resp_tokens = len(full_response) // 4
    return full_response, stop_reason, inp_tokens, resp_tokens


# Movido para o topo do modulo: o laco da F5 precisa da MESMA protecao de
# flood, e duas copias da classe divergiriam. Comportamento identico.
class _StreamFloodGuard:
    """Evita flood visual no terminal por sequências extensas de box-drawing.

    Mantém `full_response` intacto para parse/escrita de artefatos; só reduz ruído
    visual no stdout quando detecta sequências anômalas de caracteres decorativos.
    """

    _BOX_CHARS = set("─━│┃┌┐└┘├┤┬┴┼►▶→")

    def __init__(self, *, run_threshold: int = 160):
        self.run_threshold = run_threshold
        self._decorative_run = 0
        self.suppressed_chars = 0
        self._notice_printed = False

    def _is_decorative(self, ch: str) -> bool:
        return ch in self._BOX_CHARS

    def write(self, text: str) -> None:
        out: list[str] = []
        for ch in text:
            if self._is_decorative(ch):
                self._decorative_run += 1
                if self._decorative_run > self.run_threshold:
                    self.suppressed_chars += 1
                    continue
                out.append(ch)
                continue

            self._decorative_run = 0
            out.append(ch)

        if out:
            print("".join(out), end="", flush=True)

    def flush_notice(self) -> None:
        if self.suppressed_chars > 0 and not self._notice_printed:
            print(
                f"\n{YELLOW}  [STREAM-GUARD] Suprimidos {self.suppressed_chars:,} chars "
                f"decorativos consecutivos (box-drawing) para evitar flood visual.{RESET}"
            )
            self._notice_printed = True


def _dispatch_model(client: "anthropic.Anthropic", *, system_prompt: str,
                    user_prompt: str, out_tokens: int, phase: str,
                    ts_start: "datetime.datetime",
                    stream_guard: "_StreamFloodGuard",
                    inp_tokens_estimate: int = 0,
                    enforce_budget: bool = False,
                    budget_label: str = "") -> "tuple[str, str, int, int]":
    """Envia o prompt ao modelo. Devolve `(resposta, stop_reason, inp, out)`.

    Extraída de `run_step` **sem mudança de comportamento**, para que o laço da
    F5 use exatamente o mesmo caminho de streaming, retry, heartbeat e
    contabilidade de tokens. Duas cópias divergiriam, e a de menos uso
    divergiria em silêncio.

    Orçamento de contexto (ver `devops_task_ledger.context_budget_tokens`):

    * `enforce_budget=False` — padrão, e o que TODAS as fases existentes usam:
      mede o prompt, avisa em amarelo se ele passar do orçamento, e envia. O
      comportamento anterior fica intacto.
    * `enforce_budget=True` — F5/DE: mede e **recusa** o envio, levantando
      `ContextBudgetExceeded`. Um 400 `prompt is too long` custa o upload
      inteiro antes de falhar; a recusa local custa zero.
    """
    if _devops_ledger is not None:
        try:
            _estimado = _devops_ledger.estimate_tokens(system_prompt, user_prompt)
            _orcamento = _devops_ledger.context_budget_tokens(CTX_WINDOW, out_tokens)
        except AttributeError:              # módulo antigo em disco — medir é opcional
            _estimado = _orcamento = 0
        if _orcamento and _estimado > _orcamento:
            print(f"\n{YELLOW}  ⚠️  [CTX-BUDGET] {budget_label or phase}: prompt estimado "
                  f"em {_estimado:,} tokens > orçamento de {_orcamento:,} "
                  f"(janela {CTX_WINDOW:,} · saída {out_tokens:,}).{RESET}")
            if enforce_budget:
                raise _devops_ledger.ContextBudgetExceeded(
                    f"contexto de {budget_label or phase} estimado em {_estimado:,} "
                    f"tokens excede o orçamento de {_orcamento:,}",
                    estimated=_estimado, budget=_orcamento)
            print(f"{YELLOW}      Enviando mesmo assim — comportamento histórico "
                  f"desta fase preservado.{RESET}")

    full_response = ""
    stop_reason = "unknown"
    inp_tokens = int(inp_tokens_estimate)
    resp_tokens = 0

    last_exc: Exception | None = None
    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            if PROVIDER == "anthropic":
                # ── Anthropic path (com suporte a headroom) ───────────────
                with client.messages.stream(
                    model=DEPLOYMENT,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=out_tokens,
                    temperature=TEMPERATURE,
                ) as stream:
                    for text in stream.text_stream:
                        stream_guard.write(text)
                        full_response += text
                        status_heartbeat(phase, ts_start, full_response)
                    final_msg = stream.get_final_message()
                    stop_reason = final_msg.stop_reason or "unknown"
                    _usage = final_msg.usage
                    if _usage:
                        inp_tokens = _usage.input_tokens
                        resp_tokens = _usage.output_tokens
                    else:
                        resp_tokens = len(full_response) // 4
            else:
                # ── OpenAI path (SSE via requests) ────────────────────────
                # Quando headroom ativo, client.base_url é o proxy (/v1 para OpenAI);
                # passamos essa URL para _stream_openai usar em vez do endpoint direto.
                _openai_base = str(client.base_url).rstrip("/")
                full_response, stop_reason, inp_tokens, resp_tokens = _stream_openai(
                    client.api_key, system_prompt, user_prompt, out_tokens,
                    base_url=_openai_base, stream_guard=stream_guard,
                    on_chunk=lambda t: status_heartbeat(phase, ts_start, t),
                )
            last_exc = None
            break
        except Exception as e:
            last_exc = e
            # Estouro de contexto NUNCA é transitório: reenviar o mesmo prompt
            # falha igual, só que três vezes mais caro em latência.
            if _devops_ledger is not None and _devops_ledger.is_context_limit_error(e):
                raise
            if attempt < API_MAX_RETRIES and _is_retryable_api_error(e):
                _jitter = (attempt * 1.5) + (hash(user_prompt) % 1000 / 1000.0)
                _delay = API_RETRY_DELAY_S * _jitter
                print(f"\n{YELLOW}  ⚠️  API error (tentativa {attempt}/{API_MAX_RETRIES}): "
                      f"{e or 'mensagem vazia'}{RESET}")
                print(f"{YELLOW}      Retentando em {_delay:.1f}s...{RESET}")
                time.sleep(_delay)
                continue
            raise
    if last_exc is not None:
        raise last_exc

    if not resp_tokens:
        resp_tokens = len(full_response) // 4
    return full_response, stop_reason, inp_tokens, resp_tokens


def _is_retryable_api_error(exc: Exception) -> bool:
    """True se o erro parece transitório e vale a pena retry."""
    msg = str(exc).lower()
    # Erro vazio da API / proxy (ex.: {'type': 'api_error', 'message': ''})
    if not msg or msg in {"", "api_error", "internal error"}:
        return True
    retry_patterns = ("timeout", "connection", "reset", "refused", "temporarily",
                      "overloaded", "rate limit", "too many requests", "503",
                      "502", "504", "eof occurred")
    return any(p in msg for p in retry_patterns)


# ═════════════════════════════════════════════════════════════════════════════
#  F5 · DevOps Execute — laço iterativo sobre task-devops-progress.json
# ═════════════════════════════════════════════════════════════════════════════
#
# O QUE MUDOU E POR QUÊ
# ---------------------
# Antes: UM despacho de `ava-devops-orchestrator` com o contexto da fase inteira.
# Como a F5 declarava `outputs/tobe/source-code` (um DIRETÓRIO) como insumo
# obrigatório, e o `context_manifest` expande diretório com `rglob("*")`,
# o prompt levava a aplicação gerada inteira:
#
#     BadRequestError 400 — prompt is too long: 3924457 tokens > 1000000 maximum
#
# Depois: N despachos pequenos, um por tarefa de DevOps, cada um com o spec do
# sub-agente (3,5KB–59KB) mais a fatia do plano que aquela tarefa precisa. O
# estado vive em `outputs/tobe/devops/task-devops-progress.json`, não na memória
# da conversa — cada iteração recarrega o arquivo do disco antes de decidir.
#
# NENHUMA das chamadas carrega `outputs/tobe/source-code`, o
# `architecture-blueprint.md` ou o `shared-context.md`. Ver
# `_build_task_context()`: ele monta o contexto a partir de uma lista fechada.

#: Teto de saída por tarefa. Uma tarefa de DevOps entrega manifesto, pipeline ou
#: relatório — não um HTML de 400KB.
DEVOPS_TASK_MAX_TOKENS = 32_000


def _devops_read_plans(project: str) -> "tuple[dict, list[str]]":
    """Lê SOMENTE os três insumos declarados. Devolve `(planos, ausentes)`.

    Nenhum diretório é percorrido e nenhum glob é expandido: a lista é fechada
    em `F5_DEVOPS_INPUT_PATHS`. É esta função — e não `load_context` — a única
    porta de entrada de conteúdo de disco para a F5.
    """
    raiz = WORKSPACE / "projects" / project
    planos: dict[str, str] = {}
    ausentes: list[str] = []
    for rel in F5_DEVOPS_INPUT_PATHS:
        caminho = raiz / rel
        if not caminho.is_file():
            ausentes.append(rel)
            continue
        limite = (_devops_ledger.TASK_CONFIG_CHARS if rel.endswith((".yaml", ".yml"))
                  else _devops_ledger.DERIVATION_PLAN_CHARS)
        try:
            planos[rel] = caminho.read_text(encoding="utf-8", errors="ignore")[:limite]
        except OSError as exc:
            print(f"  {YELLOW}⚠️  {rel}: falha de leitura ({exc}) — tratado como ausente{RESET}")
            ausentes.append(rel)
    return planos, ausentes


def _build_task_context(project: str, task: dict, progress: dict,
                        planos: dict, *, level: int = 0) -> str:
    """Contexto MÍNIMO de uma tarefa. Lista fechada, nível de redução explícito.

    `level` é a estratégia concreta de redução exigida antes de qualquer nova
    tentativa após um estouro de contexto — repetir o mesmo request não é
    retentar, é pagar o mesmo 400 de novo:

    * 0 — config do projeto + fatia dirigida do plano + resumo das dependências
    * 1 — sem corpo de plano: só os cabeçalhos, como índice
    * 2 — só a ficha da tarefa e os caminhos dos artefatos das dependências

    Em nenhum nível entram: `outputs/tobe/source-code`, `architecture-blueprint.md`
    ou `context/shared-context.md`.
    """
    por_id = _devops_ledger.tasks_by_id(progress)
    partes: list[str] = []

    contagem = _devops_ledger.summary_counts(progress)
    partes.append(
        "## ESTADO DA EXECUÇÃO DEVOPS (task-devops-progress.json)\n\n"
        f"- Tarefas: {contagem['total']} · concluídas {contagem['completed']} · "
        f"puladas {contagem['skipped']} · pendentes {contagem['pending']} · "
        f"falhas {contagem['failed']} · bloqueadas {contagem['blocked']}\n"
        f"- Arquivo de controle: `projects/{project}/{_devops_ledger.PROGRESS_REL}`\n"
        "- Você NÃO escolhe a tarefa e NÃO declara conclusão: o harness escolhe "
        "e grava o status a partir dos artefatos realmente escritos."
    )

    partes.append(
        "## SUA TAREFA NESTA EXECUÇÃO\n\n"
        f"- id: `{task.get('id')}`\n"
        f"- título: {task.get('title')}\n"
        f"- descrição: {task.get('description')}\n"
        f"- sub-agente: `{task.get('agent') or '—'}`\n"
        f"- plano de origem: `{task.get('source_plan')}`\n"
        f"- tentativa: {task.get('attempts')}/{task.get('max_attempts')}\n"
        f"- artefatos esperados: {', '.join(task.get('output_globs') or ['—'])}"
    )

    deps = _devops_ledger.dependency_summaries(task, por_id)
    if deps:
        partes.append(
            "## DEPENDÊNCIAS JÁ CONCLUÍDAS (resumo + caminhos, nunca o conteúdo)\n\n"
            + deps)

    if level <= 1:
        config = planos.get(F5_DEVOPS_INPUT_PATHS[0], "")
        if config:
            partes.append(f"### {F5_DEVOPS_INPUT_PATHS[0]}\n```yaml\n"
                          f"{config[:_devops_ledger.TASK_CONFIG_CHARS]}\n```")

    plano_rel = str(task.get("source_plan") or F5_DEVOPS_INPUT_PATHS[1])
    plano_txt = planos.get(plano_rel, "")
    if level == 0 and plano_txt:
        trecho = _devops_ledger.plan_excerpt(task, plano_txt)
        partes.append(f"### {plano_rel} (seções pertinentes a esta tarefa)\n"
                      f"```markdown\n{trecho}\n```")
        outro = next((r for r in F5_DEVOPS_INPUT_PATHS[1:] if r != plano_rel), "")
        if outro and planos.get(outro):
            resumo = _devops_ledger.plan_excerpt(
                task, planos[outro], limit=_devops_ledger.TASK_PLAN_CHARS // 2)
            partes.append(f"### {outro} (seções pertinentes)\n"
                          f"```markdown\n{resumo}\n```")
    elif level == 1 and plano_txt:
        indice = "\n".join(f"- {h}" for h in _devops_ledger.plan_headings(plano_txt))
        partes.append(
            f"### {plano_rel} — ÍNDICE (corpo omitido por orçamento de contexto)\n\n"
            f"{indice}\n\n"
            f"Leia do disco só a seção que precisar: "
            f"`projects/{project}/{plano_rel}`.")
    else:
        partes.append(
            "### Planos não injetados (orçamento de contexto)\n\n"
            "Os planos estão em disco; leia sob demanda apenas a seção necessária:\n"
            + "\n".join(f"- `projects/{project}/{r}`"
                        for r in F5_DEVOPS_INPUT_PATHS[1:]))

    partes.append(
        "## LIMITES DE CONTEXTO DESTA FASE — OBRIGATÓRIOS\n\n"
        "- ❌ NÃO leia `outputs/tobe/source-code/` recursivamente, nem o "
        "`frontend/` nem o `backend/`. Referencie os caminhos; não carregue o código.\n"
        "- ❌ NÃO leia `context/shared-context.md` nem "
        "`outputs/tobe/docs/architecture-blueprint.md`.\n"
        "- ❌ NÃO percorra diretórios inteiros.\n"
        "- ✅ Entregue SOMENTE os artefatos desta tarefa. As demais tarefas têm "
        "execução própria e contexto próprio.")

    return "\n\n".join(partes)


def _devops_task_metrics(task: dict, *, phase: str, agent: str,
                         started: float, ended: float,
                         inp_tokens: int, resp_tokens: int,
                         artifacts: "list[str]", error_type: str = "",
                         error_message: str = "",
                         continuation: str = "") -> dict:
    """Linha de métrica por tarefa. Métrica opcional ausente nunca é fatal."""
    return {
        "phase": phase,
        "agent": agent,
        "task_id": task.get("id"),
        "task_status": task.get("status"),
        "attempt": task.get("attempts"),
        "start_time": _utc_iso(started),
        "end_time": _utc_iso(ended),
        "duration_s": round(max(0.0, ended - started), 2),
        "input_files": list(F5_DEVOPS_INPUT_PATHS),
        "output_artifacts": list(artifacts),
        "estimated_input_tokens": int(inp_tokens),
        "output_tokens": int(resp_tokens),
        "error_type": error_type,
        "error_message": _devops_ledger.sanitize(error_message, 400),
        "continuation_action": continuation,
    }


def _f4_failure_context(build_result: dict, attempt: int) -> str:
    """Saída real do build que falhou — matéria-prima da etapa REFLECT."""
    saida = ((build_result.get("stdout") or "")
             + (build_result.get("stderr") or "")).strip()
    return "\n".join([
        f"Tentativa {attempt} de remediacao. O build da tentativa anterior FALHOU.",
        f"Comando: {build_result.get('command')}",
        f"Exit code: {build_result.get('exit_code')}",
        "",
        "Saida do build (stdout + stderr):",
        "```text",
        saida[-6000:],
        "```",
        "",
        "Instrucoes:",
        "1. Leia o erro acima e a arvore atual antes de escrever qualquer coisa.",
        "2. Aplique a MENOR correcao que faz o build passar.",
        "3. NAO regenere o scaffold nem reescreva arquivos que ja funcionam.",
        "4. O pipeline vai rodar o build de novo assim que voce terminar.",
    ])


def _run_f4_codegen_step(client: "anthropic.Anthropic", step: dict, project: str,
                         output_dir: Path, *, skill_content: str,
                         out_tokens: int, esperados: "list[str]",
                         headroom_active: bool) -> dict:
    """Executa a F4 como laço Ralph Wiggum dirigido por `tasks-progress.json`.

    Uma task por despacho, roteada para o coder especializado da stack, com
    contexto mínimo, build real por task e commit só depois do exit code 0.
    Devolve o mesmo dict que `run_step` — o laço principal aplica as MESMAS
    políticas de degradação das demais fases.
    """
    phase = str(step.get("phase"))
    agent = str(step.get("agent"))
    ts_inicio = time.time()

    def _falha(detalhe: str, elapsed: float = 0.0) -> dict:
        print(f"\n{RED}  ❌ [{phase}][{agent}] {detalhe}{RESET}")
        return {"phase": phase, "agent": agent, "skill_kb": 0, "inp_tokens": 0,
                "out_max": out_tokens, "resp_tokens": 0, "ctx_pct": 0.0,
                "elapsed_s": round(elapsed, 2), "artifacts": 0,
                "artifacts_written": [], "val_ok": False, "detail": detalhe,
                "headroom_used": headroom_active, "contract_ok": 0,
                "contract_total": 0, "contract_missing": [], "contract_pending": []}

    if _f4_loop is None:
        return _falha(
            f"modulos da F4 nao puderam ser importados ({_F4_IMPORT_ERROR}) — "
            f"a fase NAO cai no despacho unico, que e o defeito original")

    banner(f"{phase} · Tech Stack — laço por task (razão: tasks-progress.json)", CYAN)

    # O manifesto da fase é fechado e vazio: contexto é montado por task.
    step["inputs"] = _f4_inputs()

    task_out_tokens = min(F4_TASK_MAX_TOKENS, out_tokens)
    totais = {"inp": 0, "resp": 0}
    artefatos_todos: list[str] = []

    def _despachar(ctx: dict, failure_context: str = "") -> dict:
        """Etapas A–C do laço interno: o agente lê, raciocina e implementa."""
        route = ctx["route"]
        task = ctx["task"]
        task_id = str(task["task_id"])
        feature = str(task.get("feature") or "")
        tentativa = int(ctx.get("attempt", 1))

        spec_path = WORKSPACE / route.spec_path
        skill_task = load_skill(route.agent, spec_path=spec_path)

        nivel = int(ctx.get("context_level", 0))
        contexto = _f4_loop.build_task_context({**ctx, "context_level": nivel},
                                               failure_context=failure_context)
        contrato = _f4_contract.contract_template(project, task, route, tentativa)
        contexto += (
            "\n\n## CONTRATO DE RESPOSTA — OBRIGATORIO\n\n"
            "Alem dos blocos <!-- FILE: ... --> com o codigo, termine a resposta "
            "com este bloco, preenchido com o que voce REALMENTE fez:\n\n"
            "<!-- F4_RESULT -->\n```json\n" + contrato + "\n```\n<!-- /F4_RESULT -->\n\n"
            "`implementation_status: completed` NAO marca a task como concluida: "
            "o pipeline roda o build depois de voce e e o exit code dele que "
            "decide."
        )

        system_prompt = build_system_prompt(route.agent, skill_task, project,
                                            contexto, task_out_tokens, phase)
        user_prompt = (f"@{route.agent} | {F4_TRIGGER} | project: {project} "
                       f"| task: {task_id}"
                       + (f" | feature: {feature}" if feature else ""))

        # Orçamento medido ANTES do envio. Estourou, reduz o contexto da task —
        # nunca some com a task nem manda o prompt de qualquer jeito.
        estimado = (len(system_prompt) + len(user_prompt)) // 4
        orcamento = int(CTX_WINDOW * 0.7) - task_out_tokens
        while estimado > orcamento and nivel < _f4_loop.MAX_CONTEXT_LEVEL:
            nivel += 1
            contexto = _f4_loop.build_task_context({**ctx, "context_level": nivel},
                                                   failure_context=failure_context)
            system_prompt = build_system_prompt(route.agent, skill_task, project,
                                                contexto, task_out_tokens, phase)
            estimado = (len(system_prompt) + len(user_prompt)) // 4
            print(f"  {YELLOW}contexto reduzido para o nivel {nivel} "
                  f"(≈{estimado:,} tokens){RESET}")
        if estimado > orcamento:
            return {"error": f"contexto da task {task_id} nao cabe no orcamento "
                             f"({estimado:,} > {orcamento:,} tokens) mesmo no "
                             f"nivel {nivel}",
                    "context_chars": len(contexto)}

        ts_start = datetime.datetime.now()
        print(f"{DIM}  Enviando: {user_prompt}{RESET}")
        print(f"{DIM}  agente={route.agent} · destino=outputs/tobe/"
              f"{route.canonical_source_rel}/ · input≈{estimado:,} tkns "
              f"out_max={task_out_tokens:,}{RESET}\n")

        stream_guard = _StreamFloodGuard()
        status_heartbeat(phase, ts_start, 0, force=True)
        try:
            resposta, stop_reason, inp_tokens, resp_tokens = _dispatch_model(
                client, system_prompt=system_prompt, user_prompt=user_prompt,
                out_tokens=task_out_tokens, phase=phase, ts_start=ts_start,
                stream_guard=stream_guard, inp_tokens_estimate=estimado,
                enforce_budget=False, budget_label=f"{phase}/{task_id}")
        except Exception as exc:  # noqa: BLE001
            return {"error": f"{type(exc).__name__}: {exc}",
                    "context_chars": len(contexto)}
        stream_guard.flush_notice()

        totais["inp"] += int(inp_tokens or 0)
        totais["resp"] += int(resp_tokens or 0)

        truncado = (stop_reason == "max_tokens")
        escritos, incompletos = parse_and_write_outputs(resposta, project,
                                                        truncated=truncado)
        artefatos_todos.extend(escritos)

        contrato_lido = _f4_contract.parse(resposta, task=task, route=route,
                                           project=project, attempt=tentativa)
        if contrato_lido.parse_error:
            print(f"  {YELLOW}contrato de resposta ausente/invalido "
                  f"({contrato_lido.parse_error}) — segue para o build, que e "
                  f"quem decide{RESET}")
        if contrato_lido.files_outside_canonical:
            print(f"  {RED}⚠️  arquivos fora do diretorio canonico NAO entram no "
                  f"commit: {', '.join(contrato_lido.files_outside_canonical[:5])}"
                  f"{RESET}")

        ts_log = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = _phase_log_path(output_dir, f"{phase}_{task_id}",
                                   route.agent, ts_log)
        try:
            log_path.write_text(
                f"# {phase} · {task_id} — {route.agent}\n\n"
                f"**Rota:** {route.reason}  \n"
                f"**Destino:** outputs/tobe/{route.canonical_source_rel}/  \n"
                f"**Tentativa:** {tentativa}  \n"
                f"**Contexto:** nivel {nivel}, {len(contexto):,} chars  \n"
                f"**Tokens:** input≈{inp_tokens:,} · output {resp_tokens:,}  \n\n"
                f"## Prompt\n\n```\n{user_prompt}\n```\n\n"
                f"## Resposta\n\n{resposta}\n",
                encoding="utf-8")
        except OSError:
            pass

        return {
            "artifacts": escritos,
            "incomplete": incompletos,
            "agent_result": contrato_lido.as_dict(),
            "claims_success": contrato_lido.claims_success,
            "context_chars": len(contexto),
            "context_level": nivel,
            "inp_tokens": int(inp_tokens or 0),
            "resp_tokens": int(resp_tokens or 0),
            "log": str(log_path.relative_to(WORKSPACE)),
        }

    def _verificar(ctx: dict) -> dict:
        """Etapas D–G: build real, remediação pelo MESMO agente, commit, razão."""
        import ava_pipeline as _ava_pipeline
        from pipeline_plan import Step as _PipelineStep

        route = ctx["route"]
        task = ctx["task"]
        despacho = ctx.get("dispatch") or {}
        task_step = _PipelineStep(
            phase=f"{phase}:{task['task_id']}", group=F4_PHASE, agent=route.agent,
            spec_path=WORKSPACE / route.spec_path,
            trigger=F4_TRIGGER, label=f"{phase} — {task['task_id']}",
            task_id=str(task["task_id"]), task_group=str(task.get("group") or ""),
            target_stack=route.target_stack, feature=str(task.get("feature") or ""),
            inputs={},
        )

        def _remediar(tentativa: int, build_result: dict) -> bool:
            """Re-despacha o MESMO coder com o erro real anexado."""
            contexto_falha = _f4_failure_context(build_result, tentativa)
            novo = _despachar({**ctx, "attempt": int(ctx.get("attempt", 1)) + tentativa},
                              failure_context=contexto_falha)
            if novo.get("error"):
                print(f"  {YELLOW}remediacao {tentativa} nao despachada: "
                      f"{novo['error']}{RESET}")
                return False
            escreveu = bool(novo.get("artifacts"))
            if escreveu:
                print(f"  {GREEN}✅ remediacao {tentativa} escreveu "
                      f"{len(novo['artifacts'])} arquivo(s){RESET}")
            return escreveu

        try:
            return _ava_pipeline.verify_task_step(
                task_step, project, {"artifacts": despacho.get("artifacts") or []},
                output_dir, timeout_s=900, client=client, model=DEPLOYMENT,
                cfg={}, route=route, agent_result=despacho.get("agent_result"),
                remediate=_remediar,
                branch_context=ctx.get("branch_context"),
                repo_root=WORKSPACE)
        except Exception as exc:  # noqa: BLE001 — falha de verificação não derruba a fase
            return {"status": "failed", "exit_code": 2,
                    "error": f"{type(exc).__name__}: {exc}",
                    "command": "<verify>", "files_written": []}

    def _evento(nome: str, dados: dict) -> None:
        if nome == "task_start":
            print(f"\n{CYAN}{'─' * 68}{RESET}")
            print(f"{CYAN}  {dados['task_id']} → {dados['agent']} "
                  f"(tentativa {dados['attempt']}){RESET}")
            print(f"{DIM}  roteamento: {dados['routing_reason']}{RESET}")
        elif nome == "task_end":
            cor = GREEN if dados.get("status") == "verified" else RED
            print(f"  {cor}{dados['task_id']}: {dados.get('status')} "
                  f"(exit {dados.get('exit_code')}, "
                  f"{len(dados.get('files_written') or [])} arquivo(s), "
                  f"{dados.get('duration_s', 0)}s){RESET}")
        elif nome == "recovered":
            for item in dados.get("tasks", []):
                print(f"  {YELLOW}↻ {item['task_id']} recuperada: "
                      f"{item['recovery_reason']}{RESET}")

    run_id = f"runner19-{int(ts_inicio)}"
    try:
        resultado = _f4_loop.run(
            project, dispatch=_despachar, verify=_verificar, run_id=run_id,
            repo_root=WORKSPACE, on_event=_evento)
    except _f4_loop.LoopError as exc:
        return _falha(str(exc), time.time() - ts_inicio)

    elapsed = time.time() - ts_inicio
    contagem = resultado.counts or {}
    resumo = resultado.summary or {}
    detalhe = "" if resultado.functional_success else f"{resultado.status}: {resultado.reason}"

    # Relatório final da fase — completude de execução E sucesso funcional.
    print(f"\n{CYAN}{'─' * 68}{RESET}")
    print(f"  {'✅' if resultado.functional_success else '📋'} F4 {resultado.status}"
          f" — {resumo.get('executed', 0)}/{resumo.get('planned', 0)} task(s) processada(s)"
          f" em {resultado.iterations} iteracao(oes)")
    print(f"  {DIM}completed={resumo.get('completed', 0)} · "
          f"completed_with_warnings={resumo.get('completed_with_warnings', 0)} · "
          f"review={resumo.get('review', 0)} · "
          f"failed_after_remediation={resumo.get('failed_after_remediation', 0)} · "
          f"blocked_by_dependency={resumo.get('blocked_by_dependency', 0)} · "
          f"pendentes={resumo.get('still_pending', 0)}{RESET}")
    print(f"  {DIM}branches integrados={len(resumo.get('branches_merged') or [])} · "
          f"preservados para revisao="
          f"{len(resumo.get('branches_preserved_for_review') or [])} · "
          f"artefatos em caminho alternativo="
          f"{len(resumo.get('artifacts_in_alternative_paths') or [])} · "
          f"arquivos fora do commit="
          f"{len(resumo.get('files_excluded_from_commit') or [])}{RESET}")
    if resumo.get("toolchain_missing"):
        print(f"  {YELLOW}toolchain ausente: "
              f"{resumo['toolchain_missing']}{RESET}")
    if not resultado.functional_success:
        print(f"  {YELLOW}{resultado.reason}{RESET}")
        for item in (resumo.get("branches_preserved_for_review") or [])[:10]:
            print(f"    {DIM}branch preservado: {item}{RESET}")

    return {
        "phase": phase, "agent": agent,
        "skill_kb": len(skill_content) // 1024,
        "inp_tokens": totais["inp"], "out_max": task_out_tokens,
        "resp_tokens": totais["resp"],
        "ctx_pct": (totais["inp"] + task_out_tokens) / CTX_WINDOW * 100,
        "elapsed_s": round(elapsed, 2),
        "artifacts": len(artefatos_todos),
        "artifacts_written": artefatos_todos,
        # A fase é "ok" quando ENCERROU de forma controlada: tudo processado e
        # registrado. Task em revisão é resultado da fase, não falha dela —
        # reprovar a F4 inteira por uma task foi o que deixou 162 sem tentativa.
        "val_ok": resultado.ok,
        "detail": detalhe,
        "headroom_used": headroom_active,
        "f4_status": resultado.status,
        "f4_counts": contagem,
        "f4_execution_counts": resultado.execution_counts,
        "f4_execution_complete": resultado.execution_complete,
        "f4_functional_success": resultado.functional_success,
        "f4_summary": resumo,
        "f4_tasks": [item.as_dict() for item in resultado.outcomes],
        "f4_diagnosis": resultado.diagnosis,
        "contract_ok": resumo.get("completed", 0)
        + resumo.get("completed_with_warnings", 0),
        "contract_total": resumo.get("planned", 0),
        "contract_missing": [], "contract_pending": [],
    }


def _run_devops_execute_step(client: "anthropic.Anthropic", step: dict, project: str,
                             output_dir: Path, *, skill_content: str,
                             out_tokens: int, esperados: "list[str]",
                             headroom_active: bool) -> dict:
    """Executa a F5 como laço Ralph Wiggum. Devolve o mesmo dict que `run_step`.

    Nunca levanta por falha de tarefa: devolve `val_ok=False` com `detail`, e o
    laço principal aplica o MESMO `_degrade_phase` das demais fases — nenhuma
    política de continuidade nova é criada aqui.
    """
    phase = str(step.get("phase"))
    agent = str(step.get("agent"))
    trigger = step.get("trigger")
    ts_inicio = time.time()

    if _devops_ledger is None:
        detalhe = ("devops_task_ledger.py não pôde ser importado — a F5 não roda "
                   "no modo iterativo e não será despachada no modo antigo, que é "
                   "o que estourava a janela de contexto")
        print(f"\n{RED}  ❌ [{phase}][{agent}] {detalhe}{RESET}")
        return {"phase": phase, "agent": agent, "skill_kb": 0, "inp_tokens": 0,
                "out_max": out_tokens, "resp_tokens": 0, "ctx_pct": 0.0,
                "elapsed_s": 0.0, "artifacts": 0, "artifacts_written": [],
                "val_ok": False, "detail": detalhe, "headroom_used": headroom_active,
                "contract_ok": 0, "contract_total": 0, "contract_missing": [],
                "contract_pending": []}

    banner(f"{phase} · DevOps Execute — laço iterativo por tarefa", CYAN)

    # ── Guard de contexto: nenhum diretório, nenhum insumo proibido ──────────
    recusados = _assert_no_directory_inputs(project, step)
    if recusados:
        # Não é aviso: é o defeito exato voltando. Corrige em memória e segue.
        print(f"  {RED}⚠️  Insumos recusados para {agent} (diretório ou proibido): "
              f"{', '.join(recusados)}{RESET}")
        print(f"  {YELLOW}   Manifesto substituído pelo fechado de {phase}/DE.{RESET}")
        step["inputs"] = _f5_devops_inputs()

    planos, ausentes = _devops_read_plans(project)
    for rel in ausentes:
        print(f"  {YELLOW}⚠️  insumo ausente: {rel} — a derivação de tarefas segue "
              f"com o que existe{RESET}")
    if F5_DEVOPS_INPUT_PATHS[1] not in planos and F5_DEVOPS_INPUT_PATHS[2] not in planos:
        detalhe = ("nenhum plano de DevOps em disco ("
                   + ", ".join(F5_DEVOPS_INPUT_PATHS[1:])
                   + ") — rode a F2b (trigger DP) antes da F5")
        print(f"\n{RED}  ❌ [{phase}][{agent}] {detalhe}{RESET}")
        return {"phase": phase, "agent": agent, "skill_kb": 0, "inp_tokens": 0,
                "out_max": out_tokens, "resp_tokens": 0, "ctx_pct": 0.0,
                "elapsed_s": round(time.time() - ts_inicio, 2), "artifacts": 0,
                "artifacts_written": [], "val_ok": False, "detail": detalhe,
                "headroom_used": headroom_active, "contract_ok": 0,
                "contract_total": 0, "contract_missing": [], "contract_pending": []}

    config_txt = planos.get(F5_DEVOPS_INPUT_PATHS[0], "")
    caminho_progresso = _devops_ledger.progress_path(project, WORKSPACE)
    progresso, novos = _devops_ledger.load_or_create(
        project, planos, repo_root=WORKSPACE,
        cloud_provider=_devops_ledger.read_config_scalar(config_txt, "cloud_provider", "azure"),
        pipeline_mode=_devops_ledger.read_config_scalar(config_txt, "pipeline_mode"))

    contagem = _devops_ledger.summary_counts(progresso)
    print(f"  {DIM}razão: {caminho_progresso.relative_to(WORKSPACE)}{RESET}")
    print(f"  {DIM}tarefas: {contagem['total']} (novas nesta execução: {len(novos)}) · "
          f"concluídas {contagem['completed']} · pendentes {contagem['pending']} · "
          f"bloqueadas {contagem['blocked']}{RESET}")

    # ── Laço ────────────────────────────────────────────────────────────────
    task_out_tokens = min(DEVOPS_TASK_MAX_TOKENS, out_tokens)
    iteracao = 0
    assinatura_anterior: "str | None" = None
    encerramento = "limite global de iterações atingido"
    todos_artefatos: list[str] = []
    metricas_tarefas: list[dict] = []
    total_inp = total_resp = 0
    ctx_pct_max = 0.0

    while iteracao < _devops_ledger.MAX_ITERATIONS:
        # (1) recarrega SEMPRE do disco: o arquivo é a fonte, não a memória.
        recarregado = _devops_ledger.read_progress(caminho_progresso)
        if recarregado is not None:
            progresso = recarregado
        assinatura = _devops_ledger.progress_signature(progresso)

        if _devops_ledger.all_finished(progresso):
            encerramento = "todas as tarefas concluídas, puladas ou bloqueadas"
            break

        if assinatura == assinatura_anterior:
            encerramento = ("ausência de progresso entre duas iterações "
                            "consecutivas — laço interrompido para não girar em falso")
            print(f"\n  {YELLOW}⚠️  {encerramento}{RESET}")
            _devops_ledger.mark_blocked_tasks(progresso)
            _devops_ledger.save_progress(caminho_progresso, progresso)
            break

        tarefa = _devops_ledger.select_next_task(progresso)
        if tarefa is None:
            bloqueados = _devops_ledger.mark_blocked_tasks(progresso)
            _devops_ledger.save_progress(caminho_progresso, progresso)
            encerramento = ("nenhuma tarefa elegível"
                            + (f" — {len(bloqueados)} bloqueada(s) por dependência "
                               f"definitivamente falha" if bloqueados else ""))
            break

        assinatura_anterior = assinatura
        iteracao += 1
        progresso["iterations"] = int(progresso.get("iterations", 0)) + 1

        # (2) marca em execução e PERSISTE antes de gastar inferência.
        _devops_ledger.mark_in_progress(tarefa)
        nivel = min(2, max(0, int(tarefa.get("context_level") or 0)))
        _devops_ledger.save_progress(caminho_progresso, progresso)

        print(f"\n{CYAN}{'─' * 68}{RESET}")
        print(f"{CYAN}  [{iteracao}/{_devops_ledger.MAX_ITERATIONS}] "
              f"{tarefa['id']} — {tarefa['title']}{RESET}")
        print(f"{DIM}  tentativa {tarefa['attempts']}/{tarefa['max_attempts']} · "
              f"sub-agente {tarefa.get('agent') or '—'} · "
              f"nível de contexto {nivel}{RESET}")

        ts_tarefa = time.time()
        ts_start = datetime.datetime.now()
        artefatos: list[str] = []
        inp_tokens = resp_tokens = 0
        erro_tipo = erro_msg = ""
        continuacao = ""

        try:
            # (3) contexto mínimo desta tarefa — nunca o da fase.
            contexto = _build_task_context(project, tarefa, progresso, planos,
                                           level=nivel)
            skill_tarefa = load_skill(str(tarefa.get("agent") or agent),
                                      spec_path=(WORKSPACE / str(tarefa.get("spec")))
                                      if tarefa.get("spec") else None)
            system_prompt = build_system_prompt(
                str(tarefa.get("agent") or agent), skill_tarefa, project,
                contexto, task_out_tokens, phase)
            user_prompt = (f"@{agent} | {trigger} | project: {project} "
                           f"| task: {tarefa['id']}")

            # (4) nunca repetir EXATAMENTE o request que já falhou.
            digest = _devops_ledger.request_digest(system_prompt, user_prompt)
            if digest == tarefa.get("last_request_digest"):
                if nivel >= 2:
                    raise _devops_ledger.ContextBudgetExceeded(
                        "sem estratégia de redução restante: o contexto mínimo já "
                        "está no nível 2 e o request seria idêntico ao que falhou",
                        estimated=0, budget=0)
                nivel += 1
                tarefa["context_level"] = nivel
                contexto = _build_task_context(project, tarefa, progresso, planos,
                                               level=nivel)
                system_prompt = build_system_prompt(
                    str(tarefa.get("agent") or agent), skill_tarefa, project,
                    contexto, task_out_tokens, phase)
                digest = _devops_ledger.request_digest(system_prompt, user_prompt)
                print(f"  {YELLOW}request idêntico ao anterior — contexto reduzido "
                      f"para o nível {nivel}{RESET}")
            tarefa["last_request_digest"] = digest

            # (5) orçamento medido ANTES do envio; estourou, não envia. O
            # `_dispatch_model` repete a checagem — de propósito: esta é a que
            # vale mesmo se alguém trocar o despachante, e a de lá é a que vale
            # para todo mundo que chama o modelo.
            estimado = _devops_ledger.estimate_tokens(system_prompt, user_prompt)
            orcamento = _devops_ledger.context_budget_tokens(CTX_WINDOW, task_out_tokens)
            print(f"{DIM}  Enviando: {user_prompt}{RESET}")
            print(f"{DIM}  input≈{estimado:,} tkns (orçamento {orcamento:,}) "
                  f"out_max={task_out_tokens:,}  |  Aguardando resposta...{RESET}\n")
            _devops_ledger.enforce_context_budget(
                system_prompt, user_prompt, window=CTX_WINDOW,
                out_tokens=task_out_tokens,
                label=f"{phase}/{tarefa['id']}")

            stream_guard = _StreamFloodGuard()
            status_heartbeat(phase, ts_start, 0, force=True)
            resposta, stop_reason, inp_tokens, resp_tokens = _dispatch_model(
                client, system_prompt=system_prompt, user_prompt=user_prompt,
                out_tokens=task_out_tokens, phase=phase, ts_start=ts_start,
                stream_guard=stream_guard, inp_tokens_estimate=estimado,
                enforce_budget=True,
                budget_label=f"{phase}/{tarefa['id']}")
            stream_guard.flush_notice()

            # (6) valida o que foi realmente escrito — não o que o modelo diz.
            truncado = (stop_reason == "max_tokens")
            escritos, incompletos = parse_and_write_outputs(resposta, project,
                                                            truncated=truncado)
            artefatos = list(escritos)
            ok, casados, motivo = _devops_ledger.validate_task_artifacts(
                tarefa, escritos, project)
            if incompletos:
                ok, motivo = False, ("resposta cortada por max_tokens; artefato(s) "
                                     "incompleto(s): " + ", ".join(incompletos))

            if ok:
                _devops_ledger.mark_completed(
                    tarefa,
                    f"{len(casados)} artefato(s) gravado(s) por {tarefa.get('agent')}",
                    casados)
                todos_artefatos.extend(escritos)
                continuacao = "próxima tarefa"
                print(f"  {GREEN}✅ {tarefa['id']} concluída — "
                      f"{len(casados)} artefato(s){RESET}")
            else:
                erro_tipo, erro_msg = "ArtifactValidationError", motivo
                _devops_ledger.mark_failed(tarefa, error_type=erro_tipo,
                                           message=motivo, recoverable=True,
                                           summary="artefatos não validados")
                continuacao = ("nova tentativa" if _devops_ledger.is_retryable(tarefa)
                               else "tarefa bloqueada após max_attempts")
                print(f"  {RED}❌ {tarefa['id']} — {motivo}{RESET}")

        except _devops_ledger.ContextBudgetExceeded as exc:
            erro_tipo, erro_msg = "ContextBudgetExceeded", str(exc)
            proximo = min(2, nivel + 1)
            tarefa["context_level"] = proximo
            houve_reducao = proximo > nivel
            _devops_ledger.mark_failed(
                tarefa, error_type=erro_tipo, message=erro_msg,
                recoverable=houve_reducao,
                summary=(f"contexto reduzido para o nível {proximo} antes da "
                         f"próxima tentativa" if houve_reducao else
                         "sem estratégia de redução restante"))
            if not houve_reducao and tarefa.get("status") != _devops_ledger.STATUS_BLOCKED:
                # Sem redução possível, retentar é repetir o request que falhou.
                tarefa["status"] = _devops_ledger.STATUS_BLOCKED
            continuacao = (f"reduzir contexto para o nível {proximo}"
                           if houve_reducao else "bloquear tarefa")
            print(f"  {YELLOW}⚠️  {tarefa['id']} — contexto excedido; {continuacao}{RESET}")

        except KeyboardInterrupt:
            tarefa["status"] = _devops_ledger.STATUS_PENDING
            tarefa["started_at"] = None
            _devops_ledger.save_progress(caminho_progresso, progresso)
            print(f"\n{YELLOW}  Interrompido — {tarefa['id']} volta a pending.{RESET}")
            raise

        except Exception as exc:                                   # noqa: BLE001
            erro_tipo, erro_msg = type(exc).__name__, str(exc)
            if _devops_ledger.is_context_limit_error(exc):
                # O 400 da API tem o mesmo tratamento do guard local: reduzir, não
                # repetir. É o `prompt is too long` chegando pelo outro caminho.
                erro_tipo = "ContextLimitError"
                proximo = min(2, nivel + 1)
                tarefa["context_level"] = proximo
                recuperavel = proximo > nivel
            else:
                recuperavel = True
            _devops_ledger.mark_failed(tarefa, error_type=erro_tipo,
                                       message=erro_msg, recoverable=recuperavel,
                                       summary=f"tentativa {tarefa['attempts']} falhou")
            continuacao = ("nova tentativa" if _devops_ledger.is_retryable(tarefa)
                           else "tarefa bloqueada")
            print(f"  {RED}❌ {tarefa['id']} — {erro_tipo}: "
                  f"{_devops_ledger.sanitize(erro_msg, 300)}{RESET}")

        finally:
            # (7) persiste SEMPRE, em qualquer desfecho.
            ts_fim = time.time()
            total_inp += int(inp_tokens or 0)
            total_resp += int(resp_tokens or 0)
            ctx_pct_max = max(ctx_pct_max,
                              (int(inp_tokens or 0) + task_out_tokens) / CTX_WINDOW * 100)
            metricas_tarefas.append(_devops_task_metrics(
                tarefa, phase=phase, agent=str(tarefa.get("agent") or agent),
                started=ts_tarefa, ended=ts_fim, inp_tokens=inp_tokens,
                resp_tokens=resp_tokens, artifacts=artefatos,
                error_type=erro_tipo, error_message=erro_msg,
                continuation=continuacao))
            try:
                _devops_ledger.save_progress(caminho_progresso, progresso)
            except OSError as exc:
                print(f"  {RED}⚠️  falha ao persistir a razão: {exc}{RESET}")

    else:
        print(f"\n  {YELLOW}⚠️  {encerramento} "
              f"({_devops_ledger.MAX_ITERATIONS}){RESET}")

    # ── Fechamento ──────────────────────────────────────────────────────────
    recarregado = _devops_ledger.read_progress(caminho_progresso)
    if recarregado is not None:
        progresso = recarregado
    contagem = _devops_ledger.summary_counts(progresso)
    falhas = [t for t in progresso.get("tasks") or []
              if t.get("status") in (_devops_ledger.STATUS_FAILED,
                                     _devops_ledger.STATUS_BLOCKED)]
    val_ok = not falhas

    print(f"\n{CYAN}{'─' * 68}{RESET}")
    print(f"{CYAN}  {phase} encerrado — {encerramento}{RESET}")
    print(f"  {DIM}iterações: {iteracao} · concluídas {contagem['completed']} · "
          f"puladas {contagem['skipped']} · falhas {contagem['failed']} · "
          f"bloqueadas {contagem['blocked']}{RESET}")

    detalhe = ""
    if falhas:
        primeira = falhas[0]
        detalhe = (f"{len(falhas)} tarefa(s) DevOps não concluída(s): "
                   + ", ".join(str(t.get("id")) for t in falhas[:6]))
        # Mensagem objetiva e sanitizada para quem opera; o traceback fica no log.
        print(f"\n{RED}  [{phase}][{agent}] A tarefa {primeira.get('id')} falhou após "
              f"{primeira.get('attempts')} tentativa(s). Consulte "
              f"{_devops_ledger.PROGRESS_REL} e os logs de execução para obter "
              f"detalhes.{RESET}")

    # Log da fase — mesmo formato e mesmo diretório das demais.
    ts_log = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    linhas_log = [
        f"# {phase} — {step.get('label', 'DevOps Execute')} (laço iterativo)\n",
        f"**Agente:** @{agent}  ",
        f"**Trigger:** {trigger or 'N/A'}  ",
        f"**Projeto:** {project}  ",
        f"**Encerramento:** {encerramento}  ",
        f"**Iterações:** {iteracao}  ",
        f"**Razão de progresso:** `{_devops_ledger.PROGRESS_REL}`  ",
        "",
        "## Insumos carregados (lista fechada — nenhum diretório)",
        "",
    ]
    linhas_log += [f"- `{rel}`" for rel in F5_DEVOPS_INPUT_PATHS]
    linhas_log += ["", "## Tarefas", ""]
    for t in progresso.get("tasks") or []:
        linhas_log.append(
            f"- `{t.get('id')}` **{t.get('status')}** "
            f"(tentativas {t.get('attempts')}/{t.get('max_attempts')}) — {t.get('title')}")
        for artefato in (t.get("output_artifacts") or [])[:10]:
            linhas_log.append(f"    - `{artefato}`")
        if t.get("error"):
            linhas_log.append(f"    - erro: `{t['error'].get('type')}` — "
                              f"{t['error'].get('message')}")
    linhas_log += ["", "## Métricas por tarefa", "",
                   "```json",
                   json.dumps(metricas_tarefas, ensure_ascii=False, indent=2),
                   "```"]
    try:
        destino = _phase_log_path(output_dir, phase, agent, ts_log)
        destino.write_text("\n".join(linhas_log) + "\n", encoding="utf-8")
        print(f"\n{GREEN}  ✅ Log salvo: {destino.relative_to(WORKSPACE)}{RESET}")
    except OSError as exc:
        print(f"  {YELLOW}⚠️  log da fase não gravado: {exc}{RESET}")

    validation = validate_phase_artifacts(phase, project, todos_artefatos,
                                          step=step, expected=esperados)
    print_validation_report(phase, validation)

    ts_final = time.time()
    return {
        "phase": phase,
        "agent": agent,
        "skill_kb": len(skill_content) // 1024,
        "inp_tokens": total_inp,
        "out_max": task_out_tokens,
        "resp_tokens": total_resp,
        "ctx_pct": ctx_pct_max,
        "elapsed_s": round(ts_final - ts_inicio, 2),
        "started_ts": ts_inicio,
        "ended_ts": ts_final,
        "artifacts": len(todos_artefatos),
        "artifacts_written": todos_artefatos,
        "val_ok": val_ok,
        "stop_reason": "loop_end",
        "incomplete": [],
        "detail": detalhe,
        "headroom_used": headroom_active,
        "devops_iterations": iteracao,
        "devops_termination": encerramento,
        "devops_task_counts": contagem,
        "devops_task_metrics": metricas_tarefas,
        "contract_ok": (validation.get("expected_ok", 0)
                        + validation.get("expected_extra", 0)
                        if validation.get("expected_total")
                        else len(validation["required_ok"])),
        "contract_total": (validation.get("expected_total", 0)
                           + validation.get("expected_extra", 0)
                           if validation.get("expected_total")
                           else len(validation["required_ok"])
                           + len(validation["required_missing"])),
        "contract_missing": list(validation["required_missing"]),
        "contract_pending": list(validation.get("expected_missing") or []),
    }


class _QASkip(Exception):
    """Sinaliza tarefa pulada sem passar pelos handlers de erro do laco da F6."""


# ═════════════════════════════════════════════════════════════════════════════
#  F6 · QA Execute — dois momentos sobre task-qa-progress.json
# ═════════════════════════════════════════════════════════════════════════════
#
# Momento 1 (planejamento): lê os artefatos de QA do `TPT` e materializa a lista
# de tarefas. Momento 2 (execução): percorre a lista, uma chamada por tarefa.
#
# O que mudou em relação ao despacho único:
#   antes  — 1 chamada, contexto da fase inteira, 40.468 arquivos expandidos,
#            9.574.025 chars renderizados → 400 prompt is too long
#   depois — 15 chamadas, contexto mínimo por tarefa; só DBI, CT e FT recebem
#            código, por glob estreito do próprio spec do sub-agente.

#: Teto de saída por tarefa de QA. Cenários, casos e scripts — não um HTML.
QA_TASK_MAX_TOKENS = 32_000

#: Portas sondadas para decidir se um componente está no ar. Sem chute: se
#: `project-config.yaml` declarar a porta, ela vence.
QA_DEFAULT_PORTS = {"backend": (5000, 5001, 8080, 8000), "frontend": (4200, 3000, 5173)}


def _qa_precondition_gate(project: str) -> "tuple[bool, list[str], list[str]]":
    """Gate QE determinístico. Devolve `(ok, bloqueios, avisos)`.

    Reproduz os Passos 1–4b de `qa-orchestrator-agent.md` §Pre-condition Gate
    (QE). O Passo 3 confere **existência e população** de `source-code/` — é o
    que o gate sempre quis saber. Responder isso injetando 379 MB no prompt foi
    o defeito; aqui custa um `iterdir()`.
    """
    raiz = WORKSPACE / "projects" / project
    bloqueios: list[str] = []
    avisos: list[str] = []

    def _populado(rel: str) -> bool:
        alvo = raiz / rel
        if not alvo.is_dir():
            return False
        ignorar = getattr(_ctx_manifest, "_BUILD_DIRS", frozenset())
        for caminho in alvo.rglob("*"):
            if caminho.is_file() and not any(parte in ignorar
                                             for parte in caminho.parts):
                return True
        return False

    # Passo 1 — bounded-context-map.md com ≥1 bounded context
    bcm = raiz / "outputs/tobe/docs/bounded-context-map.md"
    if not bcm.is_file():
        bloqueios.append("outputs/tobe/docs/bounded-context-map.md ausente — "
                         "F2a (ava-tobe-orchestrator, SD) não foi executada")
    else:
        texto = bcm.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"(?im)^\s*#{1,6}\s*BC-|\bbounded[\s-]?context\b", texto):
            bloqueios.append("bounded-context-map.md não declara nenhum bounded "
                             "context — o mapa está vazio")

    # Passo 2 — planejamento (TPT) concluído
    if not (raiz / "outputs/tobe/qa/test-plan.md").is_file():
        bloqueios.append("outputs/tobe/qa/test-plan.md ausente — rode a F2c "
                         "(ava-qa-orchestrator, trigger TPT) antes da F6")
    matriz = [rel for rel in ("outputs/tobe/qa/functional-test-matrix.md",
                              "outputs/tobe/tests/functional-test-matrix.md")
              if (raiz / rel).is_file()]
    if not matriz:
        bloqueios.append("functional-test-matrix.md ausente em outputs/tobe/qa/ e "
                         "em outputs/tobe/tests/ — planejamento (TPT) incompleto")

    # Passo 3 — esteira de código (F4). EXISTÊNCIA, não conteúdo.
    if not (raiz / "outputs/tobe/source-code/README.md").is_file():
        bloqueios.append("outputs/tobe/source-code/README.md ausente — a esteira "
                         "de código (F4 Stack) não foi executada")
    for rel in ("outputs/tobe/source-code/backend",
                "outputs/tobe/source-code/frontend"):
        if not _populado(rel):
            bloqueios.append(f"{rel}/ ausente ou vazio — a geração de código "
                             f"concluiu com falha silenciosa")

    # Passo 4 — DevOps DE concluído (artefatos ou razão de progresso da F5)
    devops_ok = (raiz / "outputs/tobe/devops/task-devops-progress.json").is_file()
    if not devops_ok:
        devops_ok = any((raiz / rel).exists() for rel in
                        ("outputs/tobe/iac", "outputs/tobe/infra",
                         "outputs/tobe/devops/ci", "outputs/tobe/devops/cd"))
    if not devops_ok:
        bloqueios.append("nenhum artefato da esteira DevOps (F5, trigger DE) em "
                         "disco — rode a F5 antes da F6")

    # Passo 4b — parity-test-report.md: WARNING, nunca bloqueio
    if not (raiz / "outputs/tobe/parity-test-report.md").is_file():
        avisos.append("outputs/tobe/parity-test-report.md ausente — PT e RS serão "
                      "registrados com ressalva; a execução continua (Passo 4b)")

    return (not bloqueios), bloqueios, avisos


def _qa_runtime_state(project: str, required: "list[str]") -> dict:
    """Estado real dos componentes exigidos por uma tarefa. Nunca chuta.

    Sonda TCP nas portas declaradas em `project-config.yaml` (ou nos defaults
    conhecidos). Não inventa comando de subida: se a aplicação não está no ar, o
    estado é `indisponível` e a tarefa que depende dela é pulada com motivo —
    marcar como aprovada um teste que nunca rodou seria pior que não rodar.
    """
    estado: dict = {}
    if not required:
        return estado

    config = WORKSPACE / "projects" / project / "context" / "project-config.yaml"
    texto = (config.read_text(encoding="utf-8", errors="ignore")
             if config.is_file() else "")

    for componente in required:
        declarada = re.search(rf"(?im)^\s*{componente}_port\s*:\s*(\d+)\s*$", texto)
        portas = ((int(declarada.group(1)),) if declarada
                  else QA_DEFAULT_PORTS.get(componente, ()))
        viva = None
        for porta in portas:
            try:
                with socket.create_connection(("127.0.0.1", porta), timeout=1.5):
                    viva = porta
                    break
            except OSError:
                continue
        estado[componente] = (f"em execução (127.0.0.1:{viva})" if viva
                              else f"indisponível (portas sondadas: "
                                   f"{', '.join(map(str, portas)) or 'nenhuma'})")
    return estado


def _qa_read_planning(project: str) -> "tuple[dict, list[str], list[str]]":
    """Lê SOMENTE os artefatos de planejamento. Devolve `(conteúdos, presentes, ausentes)`.

    Nenhum diretório é percorrido. É esta função — e não `load_context` — a
    única porta de entrada de conteúdo de disco no Momento 1 da F6.
    """
    raiz = WORKSPACE / "projects" / project
    conteudos: dict = {}
    presentes: list[str] = []
    ausentes: list[str] = []
    for rel in _qa_ledger.PLANNING_INPUTS:
        caminho = raiz / rel
        if not caminho.is_file():
            ausentes.append(rel)
            continue
        presentes.append(rel)
        limite = (_qa_ledger.TASK_CONFIG_CHARS if rel.endswith((".yaml", ".yml"))
                  else _qa_ledger.PLANNING_ARTIFACT_CHARS)
        try:
            conteudos[rel] = caminho.read_text(encoding="utf-8",
                                               errors="ignore")[:limite]
        except OSError as exc:
            print(f"  {YELLOW}⚠️  {rel}: falha de leitura ({exc}){RESET}")
            ausentes.append(rel)
            presentes.pop()
    return conteudos, presentes, ausentes


def _qa_read_code_slice(project: str, task: dict) -> "tuple[str, dict]":
    """Fatia estreita de código para a tarefa. `("", census)` quando não precisa.

    Só as três tarefas cujo spec declara necessidade de código chegam aqui, e
    ainda assim por glob: `**/Migrations/*.cs`, `**/Controllers/**`,
    `frontend/src/**/*.component.ts`. Nunca `source-code/**`.
    """
    globs = list(task.get("sourceCodeGlobs") or [])
    censo = {"files_matched": 0, "files_injected": 0, "chars": 0}
    if not globs:
        return "", censo

    raiz = WORKSPACE / "projects" / project
    ignorar = getattr(_ctx_manifest, "_BUILD_DIRS", frozenset())
    vistos: set = set()
    escolhidos: list = []
    for padrao in globs:
        for caminho in sorted(raiz.glob(padrao)):
            if not caminho.is_file():
                continue
            if any(parte in ignorar for parte in caminho.parts):
                continue
            rel = caminho.relative_to(raiz).as_posix()
            if rel in vistos:
                continue
            vistos.add(rel)
            escolhidos.append((rel, caminho))
    censo["files_matched"] = len(escolhidos)

    blocos: list = []
    usado = 0
    for rel, caminho in escolhidos[:_qa_ledger.TASK_CODE_FILES]:
        if usado >= _qa_ledger.TASK_CODE_CHARS:
            break
        try:
            corpo = caminho.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        corpo = corpo[: _qa_ledger.TASK_CODE_CHARS - usado]
        usado += len(corpo)
        blocos.append(f"#### {rel}\n```\n{corpo}\n```")
    censo["files_injected"] = len(blocos)
    censo["chars"] = usado

    if not blocos:
        return ("", censo)
    cabecalho = (f"### Fatia de código desta tarefa "
                 f"({len(blocos)} de {len(escolhidos)} arquivo(s) casados)\n\n"
                 f"Globs aplicados: {', '.join(globs)}\n"
                 f"Nenhum outro arquivo de `outputs/tobe/source-code/` foi lido.\n\n")
    return cabecalho + "\n\n".join(blocos), censo


def _build_qa_task_context(project: str, task: dict, progress: dict,
                           planos: dict, *, level: int = 0) -> "tuple[str, dict]":
    """Contexto MÍNIMO de uma tarefa de QA. Devolve `(texto, métricas)`.

    Níveis de redução, aplicados antes de qualquer nova tentativa após estouro:
      0 — planejamento dirigido + resumo das dependências + fatia de código
      1 — sem fatia de código: só os globs, para leitura sob demanda
      2 — só a ficha da tarefa e os caminhos dos artefatos das dependências

    Em nenhum nível entram `outputs/tobe/source-code` inteiro nem
    `context/shared-context.md`.
    """
    por_id = _qa_ledger.tasks_by_id(progress)
    partes: list = []
    censo = {"code_files_matched": 0, "code_files_injected": 0, "code_chars": 0}

    contagem = _qa_ledger.summary_counts(progress)
    runtime = progress.get("runtime") or {}
    partes.append(
        "## ESTADO DA EXECUÇÃO QA (task-qa-progress.json)\n\n"
        f"- Tarefas: {contagem['total']} · aprovadas {contagem['passed']} · "
        f"ressalva {contagem['completed_with_warning']} · falhas {contagem['failed']} · "
        f"bloqueadas {contagem['blocked']} · pendentes "
        f"{contagem['pending'] + contagem['ready']}\n"
        f"- Arquivo de controle: `projects/{project}/{_qa_ledger.PROGRESS_REL}`\n"
        + (f"- Aplicação: " + "; ".join(f"{k}={v}" for k, v in sorted(runtime.items()))
           + "\n" if runtime else "")
        + "- Você NÃO escolhe a tarefa e NÃO declara conclusão: o harness escolhe "
          "e grava o status a partir dos artefatos realmente escritos."
    )

    partes.append(
        "## SUA TAREFA NESTA EXECUÇÃO\n\n"
        f"- id: `{task.get('id')}` (sequência {task.get('sequence')})\n"
        f"- título: {task.get('title')}\n"
        f"- descrição: {task.get('description')}\n"
        f"- categoria: {task.get('category')}\n"
        f"- sub-agente: `{task.get('subAgent') or '—'}`\n"
        f"- tentativa: {int(task.get('retryCount', 0)) + 1}/"
        f"{task.get('maxRetries')}\n"
        f"- resultado esperado: {task.get('expectedResult')}\n"
        f"- artefatos esperados: {', '.join(task.get('outputGlobs') or ['—'])}"
        + (f"\n- ⚠️ {task.get('warning')}" if task.get("warning") else "")
    )

    deps = []
    for dep_id in task.get("dependencies") or []:
        dep = por_id.get(str(dep_id))
        if dep is None:
            continue
        deps.append(f"- {dep_id} [{dep.get('status')}] "
                    f"{_qa_ledger.sanitize(dep.get('actualResult') or '', 200)}")
        for artefato in (dep.get("outputArtifacts") or [])[:10]:
            deps.append(f"    · {artefato}")
    if deps:
        partes.append("## DEPENDÊNCIAS CONCLUÍDAS (resumo + caminhos, nunca o conteúdo)\n\n"
                      + "\n".join(deps)[:_qa_ledger.TASK_DEP_CHARS])

    if level <= 1:
        for rel in task.get("inputArtifacts") or []:
            corpo = planos.get(rel)
            if corpo:
                partes.append(f"### {rel}\n```\n{corpo[:_qa_ledger.TASK_PLAN_CHARS]}\n```")
        plano = planos.get("outputs/tobe/qa/test-plan.md")
        if level == 0 and plano and not (task.get("inputArtifacts") or []):
            partes.append(f"### outputs/tobe/qa/test-plan.md\n```\n"
                          f"{plano[:_qa_ledger.TASK_PLAN_CHARS]}\n```")

    if level == 0 and task.get("sourceCodeGlobs"):
        fatia, censo_codigo = _qa_read_code_slice(project, task)
        censo.update({"code_files_matched": censo_codigo["files_matched"],
                      "code_files_injected": censo_codigo["files_injected"],
                      "code_chars": censo_codigo["chars"]})
        partes.append(fatia if fatia else
                      ("### Código desta tarefa\n\nNenhum arquivo casou com os globs "
                       + ", ".join(task["sourceCodeGlobs"])
                       + " — registre a degradação, não invente o conteúdo."))
    elif task.get("sourceCodeGlobs"):
        partes.append(
            "### Código desta tarefa (não injetado — orçamento de contexto)\n\n"
            "Leia sob demanda APENAS estes globs:\n"
            + "\n".join(f"- `projects/{project}/{g}`" for g in task["sourceCodeGlobs"]))

    partes.append(
        "## LIMITES DE CONTEXTO DESTA FASE — OBRIGATÓRIOS\n\n"
        "- ❌ NÃO leia `outputs/tobe/source-code/` recursivamente. Use os globs acima.\n"
        "- ❌ NÃO leia `bin/`, `obj/`, `node_modules/`, `dist/`, `build/`, `coverage/`.\n"
        "- ❌ NÃO leia `context/shared-context.md`.\n"
        "- ❌ NÃO percorra diretórios inteiros.\n"
        "- ✅ Entregue SOMENTE os artefatos desta tarefa.\n"
        "- ✅ Se um teste não pôde ser executado, registre-o como NÃO EXECUTADO. "
        "Documento ou script gerado não é evidência de teste executado.")

    return "\n\n".join(partes), censo


def _qa_task_metrics(task: dict, *, started: float, ended: float,
                     inp_tokens: int, resp_tokens: int, artifacts: "list[str]",
                     context_census: dict, error_type: str = "",
                     error_message: str = "", continuation: str = "") -> dict:
    """Linha de métrica por tarefa, incluindo o censo de contexto."""
    metrica = {
        "phase": F6_QA_PHASE,
        "agent": task.get("subAgent") or F6_QA_AGENT,
        "task_id": task.get("id"),
        "task_status": task.get("status"),
        "attempt": task.get("retryCount"),
        "start_time": _utc_iso(started),
        "end_time": _utc_iso(ended),
        "duration_s": round(max(0.0, ended - started), 2),
        "input_files": list(task.get("inputArtifacts") or []),
        "source_code_globs": list(task.get("sourceCodeGlobs") or []),
        "output_artifacts": list(artifacts),
        "estimated_input_tokens": int(inp_tokens),
        "output_tokens": int(resp_tokens),
        "error_type": error_type,
        "error_message": _qa_ledger.sanitize(error_message, 400),
        "continuation_action": continuation,
    }
    metrica.update({f"ctx_{k}": v for k, v in (context_census or {}).items()})
    return metrica


def _run_qa_execute_step(client: "anthropic.Anthropic", step: dict, project: str,
                         output_dir: Path, *, skill_content: str, out_tokens: int,
                         esperados: "list[str]", headroom_active: bool) -> dict:
    """F6 em dois momentos. Devolve o mesmo dict que `run_step`.

    Nunca levanta por falha de tarefa: devolve `val_ok=False` com `detail`, e o
    laço principal aplica o MESMO `_degrade_phase` das demais fases.
    """
    phase = str(step.get("phase"))
    agent = str(step.get("agent"))
    trigger = step.get("trigger")
    ts_inicio = time.time()

    def _saida(detalhe: str, *, val_ok: bool = False, **extra) -> dict:
        base = {
            "phase": phase, "agent": agent, "skill_kb": len(skill_content) // 1024,
            "inp_tokens": 0, "out_max": out_tokens, "resp_tokens": 0, "ctx_pct": 0.0,
            "elapsed_s": round(time.time() - ts_inicio, 2),
            "started_ts": ts_inicio, "ended_ts": time.time(),
            "artifacts": 0, "artifacts_written": [], "val_ok": val_ok,
            "detail": detalhe, "headroom_used": headroom_active,
            "contract_ok": 0, "contract_total": 0, "contract_missing": [],
            "contract_pending": [],
        }
        base.update(extra)
        return base

    if _qa_ledger is None:
        detalhe = ("qa_task_ledger.py não pôde ser importado — a F6 não roda no "
                   "modo iterativo e não será despachada no modo antigo, que é o "
                   "que estourava a janela de contexto")
        print(f"\n{RED}  ❌ [{phase}][{agent}] {detalhe}{RESET}")
        return _saida(detalhe)

    banner(f"{phase} · QA Execute — planejamento + laço iterativo por tarefa", CYAN)

    # ── Guard de contexto ───────────────────────────────────────────────────
    recusados = _assert_no_directory_inputs(project, step, F6_QA_FORBIDDEN)
    if recusados:
        print(f"  {RED}⚠️  Insumos recusados para {agent} (diretório ou proibido): "
              f"{', '.join(recusados)}{RESET}")
        print(f"  {YELLOW}   Manifesto substituído pelo fechado de {phase}/QE.{RESET}")
        step["inputs"] = _f6_qa_inputs()

    # ── Pre-condition Gate (QE) ─────────────────────────────────────────────
    gate_ok, bloqueios, avisos_gate = _qa_precondition_gate(project)
    for aviso in avisos_gate:
        print(f"  {YELLOW}⚠️  [GATE QE] {aviso}{RESET}")
    if not gate_ok:
        print(f"\n{RED}  ⛔ [{phase}][{agent}] PRE-CONDITION GATE: BLOCKED{RESET}")
        for motivo in bloqueios:
            print(f"  {RED}     • {motivo}{RESET}")
        detalhe = "gate QE bloqueou: " + "; ".join(bloqueios[:3])
        return _saida(detalhe, qa_gate_blockers=list(bloqueios))
    print(f"  {GREEN}✅ [GATE QE] PASS — código presente, planejamento concluído{RESET}")

    # ══ MOMENTO 1 — planejamento ════════════════════════════════════════════
    planos, presentes, ausentes = _qa_read_planning(project)
    for rel in ausentes:
        # `ADVISORY_ONLY` é ausência prevista (Passo 4b do gate) — nota, não alerta.
        if rel in _qa_ledger.ADVISORY_ONLY:
            print(f"  {DIM}ℹ️  artefato complementar ausente (previsto): {rel}{RESET}")
        else:
            print(f"  {YELLOW}⚠️  artefato de planejamento ausente: {rel}{RESET}")

    caminho_progresso = _qa_ledger.progress_path(project, WORKSPACE)
    progresso, novos = _qa_ledger.load_or_plan(project, presentes, repo_root=WORKSPACE)
    if progresso.get("recovered_from_backup"):
        print(f"  {YELLOW}⚠️  task-qa-progress.json estava corrompido — estado "
              f"recuperado do backup .bak{RESET}")
        progresso.pop("recovered_from_backup", None)

    ciclos = _qa_ledger.find_cycles(progresso)
    if ciclos:
        detalhe = ("dependência circular no plano de QA: "
                   + " → ".join(ciclos[0]))
        print(f"\n{RED}  ❌ [{phase}][{agent}] {detalhe}{RESET}")
        progresso["terminationReason"] = detalhe
        _qa_ledger.save_progress(caminho_progresso, progresso)
        return _saida(detalhe)

    contagem = _qa_ledger.summary_counts(progresso)
    print(f"  {DIM}razão: {caminho_progresso.relative_to(WORKSPACE)}{RESET}")
    print(f"  {DIM}Momento 1 concluído — {contagem['total']} tarefa(s) planejada(s) "
          f"(novas: {len(novos)}) · aprovadas {contagem['passed']} · "
          f"pendentes {contagem['pending'] + contagem['ready']}{RESET}")

    # ══ MOMENTO 2 — execução ════════════════════════════════════════════════
    task_out_tokens = min(QA_TASK_MAX_TOKENS, out_tokens)
    iteracao = 0
    assinatura_anterior = None
    encerramento = f"limite global de iterações atingido ({_qa_ledger.MAX_ITERATIONS})"
    todos_artefatos: list = []
    metricas_tarefas: list = []
    total_inp = total_resp = 0
    ctx_pct_max = 0.0
    runtime_cache: dict = {}

    while iteracao < _qa_ledger.MAX_ITERATIONS:
        recarregado = _qa_ledger.read_progress(caminho_progresso)
        if recarregado is not None:
            recarregado.pop("recovered_from_backup", None)
            progresso = recarregado
        assinatura = _qa_ledger.progress_signature(progresso)

        if _qa_ledger.all_finished(progresso):
            encerramento = "todas as tarefas concluídas, puladas ou bloqueadas"
            break

        if assinatura == assinatura_anterior:
            encerramento = ("ausência de progresso entre duas iterações consecutivas "
                            "— laço interrompido para não girar em falso")
            print(f"\n  {YELLOW}⚠️  {encerramento}{RESET}")
            _qa_ledger.mark_blocked_tasks(progresso)
            break

        tarefa = _qa_ledger.select_next_task(progresso)
        if tarefa is None:
            bloqueados = _qa_ledger.mark_blocked_tasks(progresso)
            encerramento = ("nenhuma tarefa elegível"
                            + (f" — {len(bloqueados)} bloqueada(s) por dependência "
                               f"definitivamente falha" if bloqueados else ""))
            break

        assinatura_anterior = assinatura
        iteracao += 1
        progresso["iterations"] = int(progresso.get("iterations", 0)) + 1
        progresso["lastTaskId"] = tarefa["id"]

        _qa_ledger.mark_in_progress(tarefa)
        nivel = min(2, max(0, int(tarefa.get("contextLevel") or 0)))
        _qa_ledger.save_progress(caminho_progresso, progresso)

        print(f"\n{CYAN}{'─' * 68}{RESET}")
        print(f"{CYAN}  [{iteracao}/{_qa_ledger.MAX_ITERATIONS}] "
              f"{tarefa['id']} — {tarefa['title']}{RESET}")
        print(f"{DIM}  tentativa {int(tarefa.get('retryCount', 0)) + 1}/"
              f"{tarefa['maxRetries']} · sub-agente {tarefa.get('subAgent') or '—'} · "
              f"nível de contexto {nivel}{RESET}")

        ts_tarefa = time.time()
        ts_start = datetime.datetime.now()
        artefatos: list = []
        censo: dict = {}
        inp_tokens = resp_tokens = 0
        erro_tipo = erro_msg = ""
        continuacao = ""

        try:
            # ── Runtime: só as tarefas que exigem a aplicação no ar ─────────
            exigidos = list(tarefa.get("requiresRuntime") or [])
            if exigidos:
                chave = ",".join(sorted(exigidos))
                if chave not in runtime_cache:
                    runtime_cache[chave] = _qa_runtime_state(project, exigidos)
                estado = runtime_cache[chave]
                progresso.setdefault("runtime", {}).update(estado)
                indisponiveis = [c for c, v in estado.items()
                                 if not v.startswith("em execução")]
                if indisponiveis:
                    # Não inventamos comando de subida. Pular com motivo é a
                    # verdade; marcar como aprovado um teste que nunca rodou não.
                    motivo = ("componente(s) exigido(s) fora do ar: "
                              + ", ".join(f"{c} ({estado[c]})" for c in indisponiveis)
                              + " — teste NÃO executado")
                    _qa_ledger.mark_skipped(tarefa, motivo)
                    tarefa["nextAction"] = (
                        "suba a aplicação com os comandos declarados no projeto "
                        "(README.md / docker-compose / package.json) e reexecute a F6")
                    continuacao = "tarefa pulada — aplicação indisponível"
                    print(f"  {YELLOW}⏭  {tarefa['id']} — {motivo}{RESET}")
                    raise _QASkip()

            contexto, censo = _build_qa_task_context(project, tarefa, progresso,
                                                     planos, level=nivel)
            spec_rel = str(tarefa.get("spec") or "")
            skill_tarefa = load_skill(
                str(tarefa.get("subAgent") or agent),
                spec_path=(WORKSPACE / spec_rel) if spec_rel else None)
            system_prompt = build_system_prompt(
                str(tarefa.get("subAgent") or agent), skill_tarefa, project,
                contexto, task_out_tokens, phase)
            user_prompt = (f"@{agent} | {trigger} | project: {project} "
                           f"| task: {tarefa['id']}")

            digest = _qa_ledger.request_digest(system_prompt, user_prompt)
            if digest == tarefa.get("lastRequestDigest"):
                if nivel >= 2:
                    raise _qa_ledger.ContextBudgetExceeded(
                        "sem estratégia de redução restante: o contexto já está no "
                        "nível 2 e o request seria idêntico ao que falhou",
                        estimated=0, budget=0)
                nivel += 1
                tarefa["contextLevel"] = nivel
                contexto, censo = _build_qa_task_context(project, tarefa, progresso,
                                                         planos, level=nivel)
                system_prompt = build_system_prompt(
                    str(tarefa.get("subAgent") or agent), skill_tarefa, project,
                    contexto, task_out_tokens, phase)
                digest = _qa_ledger.request_digest(system_prompt, user_prompt)
                print(f"  {YELLOW}request idêntico ao anterior — contexto reduzido "
                      f"para o nível {nivel}{RESET}")
            tarefa["lastRequestDigest"] = digest

            estimado = _qa_ledger.estimate_tokens(system_prompt, user_prompt)
            orcamento = _qa_ledger.context_budget_tokens(CTX_WINDOW, task_out_tokens)
            censo["prompt_chars"] = len(system_prompt) + len(user_prompt)
            censo["estimated_tokens"] = estimado
            print(f"{DIM}  Enviando: {user_prompt}{RESET}")
            print(f"{DIM}  input≈{estimado:,} tkns (orçamento {orcamento:,}) "
                  f"out_max={task_out_tokens:,}  |  Aguardando resposta...{RESET}\n")
            _qa_ledger.enforce_context_budget(
                system_prompt, user_prompt, window=CTX_WINDOW,
                out_tokens=task_out_tokens, label=f"{phase}/{tarefa['id']}")

            stream_guard = _StreamFloodGuard()
            status_heartbeat(phase, ts_start, 0, force=True)
            resposta, stop_reason, inp_tokens, resp_tokens = _dispatch_model(
                client, system_prompt=system_prompt, user_prompt=user_prompt,
                out_tokens=task_out_tokens, phase=phase, ts_start=ts_start,
                stream_guard=stream_guard, inp_tokens_estimate=estimado,
                enforce_budget=True, budget_label=f"{phase}/{tarefa['id']}")
            stream_guard.flush_notice()

            truncado = (stop_reason == "max_tokens")
            escritos, incompletos = parse_and_write_outputs(resposta, project,
                                                            truncated=truncado)
            artefatos = list(escritos)
            ok, casados, motivo = _qa_ledger.validate_task_result(
                tarefa, escritos, project)
            if incompletos:
                ok, motivo = False, ("resposta cortada por max_tokens; artefato(s) "
                                     "incompleto(s): " + ", ".join(incompletos))

            evidencias = [c for c in casados
                          if "/evidence/" in c or "/logs/" in c]
            if ok:
                _qa_ledger.mark_passed(
                    tarefa,
                    actual=f"{len(casados)} artefato(s) gravado(s) por "
                           f"{tarefa.get('subAgent')}",
                    artifacts=casados, evidence=evidencias)
                todos_artefatos.extend(escritos)
                continuacao = "próxima tarefa"
                print(f"  {GREEN}✅ {tarefa['id']} — {len(casados)} artefato(s){RESET}")
            else:
                erro_tipo, erro_msg = "ArtifactValidationError", motivo
                _qa_ledger.mark_failed(tarefa, error_type=erro_tipo, error=motivo,
                                       actual="nenhum artefato validado")
                continuacao = ("nova tentativa" if _qa_ledger.is_retryable(tarefa)
                               else f"desfecho {tarefa['status']}")
                print(f"  {RED}❌ {tarefa['id']} — {motivo}{RESET}")

        except _QASkip:
            # Pular nao e erro: o `finally` persiste o estado e o laco segue.
            pass

        except _qa_ledger.ContextBudgetExceeded as exc:
            erro_tipo, erro_msg = "ContextBudgetExceeded", str(exc)
            proximo = min(2, nivel + 1)
            tarefa["contextLevel"] = proximo
            houve_reducao = proximo > nivel
            _qa_ledger.mark_failed(
                tarefa, error_type=erro_tipo, error=erro_msg,
                next_action=(f"contexto reduzido para o nível {proximo} antes da "
                             f"próxima tentativa" if houve_reducao else
                             "sem estratégia de redução restante — tarefa exposta"))
            if not houve_reducao and tarefa.get("status") not in _qa_ledger.TERMINAL:
                tarefa["status"] = _qa_ledger.STATUS_BLOCKED
                tarefa["completedAt"] = _qa_ledger.now_iso()
            continuacao = (f"reduzir contexto para o nível {proximo}"
                           if houve_reducao else "bloquear tarefa")
            print(f"  {YELLOW}⚠️  {tarefa['id']} — contexto excedido; {continuacao}{RESET}")

        except KeyboardInterrupt:
            tarefa["status"] = _qa_ledger.STATUS_READY
            tarefa["startedAt"] = None
            tarefa["nextAction"] = "interrompida pelo operador — retomável"
            _qa_ledger.save_progress(caminho_progresso, progresso)
            print(f"\n{YELLOW}  Interrompido — {tarefa['id']} volta a ready.{RESET}")
            raise

        except Exception as exc:                                   # noqa: BLE001
            erro_tipo, erro_msg = type(exc).__name__, str(exc)
            if _qa_ledger.is_context_limit_error(exc):
                erro_tipo = "ContextLimitError"
                tarefa["contextLevel"] = min(2, nivel + 1)
            _qa_ledger.mark_failed(tarefa, error_type=erro_tipo, error=erro_msg)
            continuacao = ("nova tentativa" if _qa_ledger.is_retryable(tarefa)
                           else f"desfecho {tarefa['status']}")
            print(f"  {RED}❌ {tarefa['id']} — {erro_tipo}: "
                  f"{_qa_ledger.sanitize(erro_msg, 300)}{RESET}")
            # Alerta ao usuário SEM encerrar a pipeline (política da esteira).
            print(f"  {YELLOW}     [{phase}][{agent}] A tarefa {tarefa['id']} falhou. "
                  f"As tarefas independentes continuam. Consulte "
                  f"{_qa_ledger.PROGRESS_REL}.{RESET}")

        finally:
            ts_fim = time.time()
            total_inp += int(inp_tokens or 0)
            total_resp += int(resp_tokens or 0)
            ctx_pct_max = max(ctx_pct_max,
                              (int(inp_tokens or 0) + task_out_tokens) / CTX_WINDOW * 100)
            metricas_tarefas.append(_qa_task_metrics(
                tarefa, started=ts_tarefa, ended=ts_fim, inp_tokens=inp_tokens,
                resp_tokens=resp_tokens, artifacts=artefatos, context_census=censo,
                error_type=erro_tipo, error_message=erro_msg,
                continuation=continuacao))
            try:
                _qa_ledger.save_progress(caminho_progresso, progresso)
            except OSError as exc:
                print(f"  {RED}⚠️  falha ao persistir a razão: {exc}{RESET}")

        # Bloqueante que falhou em definitivo encerra a fase — e só ela.
        if (tarefa.get("blocking")
                and tarefa.get("status") == _qa_ledger.STATUS_FAILED):
            encerramento = (f"tarefa bloqueante {tarefa['id']} falhou em definitivo")
            print(f"\n{RED}  ⛔ {encerramento} — laço encerrado.{RESET}")
            _qa_ledger.mark_blocked_tasks(progresso)
            _qa_ledger.save_progress(caminho_progresso, progresso)
            break

    # ── Fechamento ──────────────────────────────────────────────────────────
    progresso["terminationReason"] = encerramento
    _qa_ledger.mark_blocked_tasks(progresso)
    try:
        _qa_ledger.save_progress(caminho_progresso, progresso)
    except OSError:
        pass

    contagem = _qa_ledger.summary_counts(progresso)
    falhas = [t for t in progresso.get("tasks") or []
              if t.get("status") in (_qa_ledger.STATUS_FAILED, _qa_ledger.STATUS_BLOCKED)]
    val_ok = not falhas

    # Relatórios consolidados — sempre gravados, inclusive em execução parcial.
    qa_dir = WORKSPACE / "projects" / project / _qa_ledger.QA_DIR_REL
    try:
        qa_dir.mkdir(parents=True, exist_ok=True)
        resumo_md = _qa_ledger.execution_summary(progresso, project=project)
        (qa_dir / "test-execution-summary.md").write_text(resumo_md, encoding="utf-8")
        _devops_ledger.atomic_write_json(
            qa_dir / "test-results.json",
            _qa_ledger.results_json(progresso, project=project))
        todos_artefatos += [
            f"projects/{project}/{_qa_ledger.QA_DIR_REL}/test-execution-summary.md",
            f"projects/{project}/{_qa_ledger.QA_DIR_REL}/test-results.json",
        ]
    except OSError as exc:
        print(f"  {YELLOW}⚠️  relatórios de QA não gravados: {exc}{RESET}")

    print(f"\n{CYAN}{'─' * 68}{RESET}")
    print(f"{CYAN}  {phase} encerrado — {encerramento}{RESET}")
    print(f"  {DIM}iterações: {iteracao} · aprovadas {contagem['passed']} · "
          f"ressalva {contagem['completed_with_warning']} · falhas {contagem['failed']} · "
          f"bloqueadas {contagem['blocked']} · puladas {contagem['skipped']}{RESET}")

    detalhe = ""
    if falhas:
        primeira = falhas[0]
        detalhe = (f"{len(falhas)} tarefa(s) de QA não concluída(s): "
                   + ", ".join(str(t.get("id")) for t in falhas[:6]))
        print(f"\n{RED}  [{phase}][{agent}] A tarefa {primeira.get('id')} terminou como "
              f"{primeira.get('status')} após {primeira.get('retryCount')} tentativa(s). "
              f"Consulte {_qa_ledger.PROGRESS_REL} e "
              f"{_qa_ledger.QA_DIR_REL}/test-execution-summary.md.{RESET}")
        print(f"  {YELLOW}  {_qa_ledger.recommended_action(progresso)}{RESET}")

    ts_log = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    linhas_log = [
        f"# {phase} — {step.get('label', 'QA Execute')} (dois momentos)\n",
        f"**Agente:** @{agent}  ", f"**Trigger:** {trigger or 'N/A'}  ",
        f"**Projeto:** {project}  ", f"**Encerramento:** {encerramento}  ",
        f"**Iterações:** {iteracao}  ",
        f"**Razão de progresso:** `{_qa_ledger.PROGRESS_REL}`  ", "",
        "## Insumos carregados (lista fechada — nenhum diretório)", "",
    ]
    linhas_log += [f"- `{rel}`" for rel in presentes]
    linhas_log += ["", "## Conferidos por existência (sem injeção)", ""]
    linhas_log += [f"- `{rel}`" for rel in F6_QA_EXISTS]
    linhas_log += ["", "## Tarefas", ""]
    for t in sorted(progresso.get("tasks") or [],
                    key=lambda t: int(t.get("sequence") or 0)):
        linhas_log.append(
            f"- `{t.get('id')}` **{t.get('status')}** "
            f"(tentativas {t.get('retryCount')}/{t.get('maxRetries')}) — {t.get('title')}")
        for artefato in (t.get("outputArtifacts") or [])[:10]:
            linhas_log.append(f"    - `{artefato}`")
        if t.get("error"):
            linhas_log.append(f"    - erro: `{t.get('errorType')}` — {t.get('error')}")
    linhas_log += ["", "## Métricas por tarefa", "", "```json",
                   json.dumps(metricas_tarefas, ensure_ascii=False, indent=2), "```"]
    try:
        destino = _phase_log_path(output_dir, phase, agent, ts_log)
        destino.write_text("\n".join(linhas_log) + "\n", encoding="utf-8")
        print(f"\n{GREEN}  ✅ Log salvo: {destino.relative_to(WORKSPACE)}{RESET}")
    except OSError as exc:
        print(f"  {YELLOW}⚠️  log da fase não gravado: {exc}{RESET}")

    validation = validate_phase_artifacts(phase, project, todos_artefatos,
                                          step=step, expected=esperados)
    print_validation_report(phase, validation)

    ts_final = time.time()
    return {
        "phase": phase, "agent": agent,
        "skill_kb": len(skill_content) // 1024,
        "inp_tokens": total_inp, "out_max": task_out_tokens,
        "resp_tokens": total_resp, "ctx_pct": ctx_pct_max,
        "elapsed_s": round(ts_final - ts_inicio, 2),
        "started_ts": ts_inicio, "ended_ts": ts_final,
        "artifacts": len(todos_artefatos), "artifacts_written": todos_artefatos,
        "val_ok": val_ok, "stop_reason": "loop_end", "incomplete": [],
        "detail": detalhe, "headroom_used": headroom_active,
        "qa_iterations": iteracao,
        "qa_termination": encerramento,
        "qa_task_counts": contagem,
        "qa_runtime": progresso.get("runtime") or {},
        "qa_task_metrics": metricas_tarefas,
        "contract_ok": (validation.get("expected_ok", 0)
                        + validation.get("expected_extra", 0)
                        if validation.get("expected_total")
                        else len(validation["required_ok"])),
        "contract_total": (validation.get("expected_total", 0)
                           + validation.get("expected_extra", 0)
                           if validation.get("expected_total")
                           else len(validation["required_ok"])
                           + len(validation["required_missing"])),
        "contract_missing": list(validation["required_missing"]),
        "contract_pending": list(validation.get("expected_missing") or []),
    }


def run_step(client: anthropic.Anthropic, step: dict, project: str, output_dir: Path) -> dict:
    """Executa um passo em contexto isolado (fresh history) com streaming.
    A cada fase verifica se o headroom ficou disponível — se sim, recria
    o cliente apontando para o proxy sem interromper o pipeline.
    Retorna dict com dados reais da execução para o quadro de contexto."""
    agent      = step["agent"]
    trigger    = step["trigger"]
    phase      = step["phase"]
    out_tokens = PHASE_MAX_TOKENS.get(phase, PHASE_MAX_TOKENS.get(phase.split(":", 1)[0], MAX_TOKENS))

    # ── Nós determinísticos declarados no DAG ───────────────────
    # A implementação vive em ava_pipeline.py; este runner apenas adapta o
    # formato dict legado para Step, sem duplicar resolução ou subprocess.
    if step.get("kind") == "tool":
        import ava_pipeline as _ava_pipeline
        from pipeline_plan import Step as _PipelineStep

        tool_step = _PipelineStep(
            phase=phase, group="F3S", agent=agent, trigger=None,
            label=step.get("label", agent), kind="tool",
            command=list(step.get("command") or []), wave=step.get("wave", ""),
            on_fail=str(step.get("on_fail") or ""),
            # Sem esta linha o teto do nó no DAG não chega a lugar nenhum: era
            # o `timeout_s=900` logo abaixo que decidia, calado, por todas as
            # tools da esteira.
            timeout_s=step.get("timeout_s"),
        )
        result = _ava_pipeline.run_tool_step(tool_step, project)
        continued = result.get("status") in {"completed", "warning"}
        return {
            "phase": phase, "agent": agent, "skill_kb": 0,
            "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
            "ctx_pct": 0, "elapsed_s": 0, "artifacts": 0,
            "val_ok": continued, "headroom_used": False,
            "kind": "tool", "command": result["command"],
            "tool_exit_code": result["exit_code"],
            "tool_status": "OK" if result.get("status") == "completed" else "FAILED",
            "tool_timeout_s": result.get("timeout_s"),
            "tool_elapsed_s": result.get("elapsed_s"),
            "detail": ("" if result.get("status") == "completed" else
                       f"aviso determinístico aceito (exit {result['exit_code']})"),
            # Tool não passa pelo contrato de artefatos da fase: o dashboard
            # renderiza a barra de progresso como "sem contrato", não como 0%.
            "contract_ok": 0, "contract_total": 0, "contract_missing": [],
        }

    # ── Desvio para F0 — extração AST determinística (não-LLM) ───
    if agent == "_ast_extractor":
        _r = run_ast_step(step, project, output_dir)
        _r.setdefault("headroom_used", False)   # subprocess não usa proxy
        return _r

    # ── Desvio para S1/S2/S3/S4 — execução standalone via subprocess (não-LLM) ───
    # S1/S4 (geração): builder determinístico; fallback para LLM quando builder
    #   falha (ex: blueprint compat gate) OU quando o script não existe.
    # S2/S3: sempre standalone; logs escritos abaixo antes do return.
    if phase in ("S1", "S4"):
        _result = _run_summary_generate_standalone(project, phase=phase)
        if _result is not None and _result.get("val_ok", False):
            # Builder OK — grava log mínimo e retorna
            _result.setdefault("headroom_used", False)
            _ts2 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            _phase_log_path(output_dir, phase, "ava-summary", _ts2).write_text(
                f"# {phase} — Summary Generate (Builder Standalone)\n\n"
                f"**Status:** ✅ OK  \n"
                f"**HTMLs gerados:** {_result.get('artifacts', 0)}  \n"
                f"**Tempo:** {_result.get('elapsed_s', 0):.1f}s  \n",
                encoding="utf-8")
            return _result
        if _result is not None:
            # NÃO cair no LLM em nenhum caso de falha do builder determinístico.
            # Motivos:
            #   (a) "playwright_missing": o builder passará --skip-mermaid-gate; se chegou aqui
            #       é porque o próprio builder falhou por razão diferente de playwright.
            #   (b) compat gate bloqueou (blueprint .mmd ausentes): builder retornou sem HTML;
            #       exit_code=0 (main() retorna None); LLM produziria HTML de ~40KB inválido.
            #   (c) qualquer outro erro interno do builder (parse, template ausente, etc.).
            # Em todos os casos, o LLM fallback piora — gera artefato sem template real que
            # dificulta a recuperação em S2 (remediate_summary.py rejeita HTMLs < 100KB como
            # "small_html" e tenta reconstruir, mas sem builder disponível fica em loop).
            # Retornar val_ok=False sem LLM é o comportamento correto: informa o usuário e
            # permite que S2 (remediation) resolva via Fases 0–7 com os artefatos existentes.
            _blocked_reason = _result.get("blocked_reason", "builder_failed")
            _result.setdefault("blocked_reason", "builder_failed")
            _result.setdefault("headroom_used", False)
            _ts2 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            _cause_map = {
                "playwright_missing": "playwright não instalado (Phase G pulada com --skip-mermaid-gate, builder falhou por outra razão)",
                "builder_failed":     "builder retornou sem HTML (compat gate ou erro interno — ver stdout acima)",
            }
            _cause_str = _cause_map.get(_blocked_reason, _blocked_reason)
            _phase_log_path(output_dir, phase, "ava-summary", _ts2).write_text(
                f"# {phase} — Summary Generate (BLOQUEADO)\n\n"
                f"**Status:** ❌ BLOQUEADO  \n"
                f"**Causa:** {_cause_str}  \n"
                f"**Próximo passo:** S2 (remediation) tentará reconstruir via remediate_summary.py Fases 0–7  \n",
                encoding="utf-8")
            return _result
        else:
            # _result is None → build_summary_comprehensive.py não encontrado.
            # LLM fallback produziria HTML de ~40KB sem template — pior que nenhum arquivo.
            # Retornar um dict de falha explícito permite que S2 tente via remediate_summary.py.
            _ts2 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            _fail_result = {
                "phase": phase, "agent": "ava-summary", "skill_kb": 0,
                "inp_tokens": 0, "out_max": 0, "resp_tokens": 0,
                "ctx_pct": 0.0, "elapsed_s": 0.0, "artifacts": 0,
                "val_ok": False, "blocked_reason": "builder_not_found",
                "headroom_used": False,
            }
            _phase_log_path(output_dir, phase, "ava-summary", _ts2).write_text(
                f"# {phase} — Summary Generate (BLOQUEADO — builder ausente)\n\n"
                f"**Status:** ❌ BLOQUEADO  \n"
                f"**Causa:** build_summary_comprehensive.py não encontrado  \n"
                f"**Próximo passo:** S2 tentará via remediate_summary.py  \n",
                encoding="utf-8")
            print(f"{RED}  ❌  [{phase}-BLOCKED]  build_summary_comprehensive.py não encontrado. "
                  f"Verifique src/modules/ava-fabric-agents/summary/utils/.{RESET}")
            return _fail_result
    elif phase == "S2":
        _r2 = _run_summary_remediation_standalone(project)
        _r2.setdefault("headroom_used", False)
        _ts2 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        (output_dir / f"S2_ava-summary-remediation_{_ts2}.md").write_text(
            f"# S2 — Summary Remediation (Standalone)\n\n"
            f"**Status:** {'✅ OK' if _r2.get('val_ok') else '❌ FALHOU'}  \n"
            f"**Artefatos:** {_r2.get('artifacts', 0)}  \n"
            f"**Tempo:** {_r2.get('elapsed_s', 0):.1f}s  \n",
            encoding="utf-8")
        return _r2
    elif phase == "S3":
        _r3 = _run_summary_validate_standalone(project)
        _r3.setdefault("headroom_used", False)
        _ts3 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        (output_dir / f"S3_ava-summary-validate_{_ts3}.md").write_text(
            f"# S3 — Summary Validate (Standalone)\n\n"
            f"**Status:** {'✅ OK' if _r3.get('val_ok') else '❌ FALHOU'}  \n"
            f"**Artefatos:** {_r3.get('artifacts', 0)}  \n"
            f"**Tempo:** {_r3.get('elapsed_s', 0):.1f}s  \n",
            encoding="utf-8")
        return _r3

    # ── Ativação dinâmica do headroom por fase ────────────────────
    # Se o cliente atual aponta para o endpoint direto mas o headroom
    # ficou disponível (subiu em background), recria o cliente apontando
    # para o proxy. Funciona para Claude (Anthropic) e Luna/GPT (OpenAI).
    _direct_endpoints = (ENDPOINT, ENDPOINT_OPENAI)
    _current_url = str(client.base_url)
    if any(ep in _current_url for ep in _direct_endpoints):
        _hr_url = headroom_proxy_url()
        if headroom_proxy_alive(_hr_url):
            try:
                _client_url = _headroom_client_url(_hr_url)
                client = anthropic.Anthropic(
                    api_key=client.api_key,
                    base_url=_client_url,
                    default_headers={"anthropic-version": "2023-06-01"},
                )
                print(f"  {CYAN}[Headroom] ✅ Ativado em {_client_url} — compressão ON a partir de {phase}{RESET}")
            except Exception:
                pass  # continua com cliente original se falhar

    # Registra se o proxy headroom está efetivamente sendo usado nesta fase
    _headroom_active = not any(ep in str(client.base_url) for ep in _direct_endpoints)

    skill_content  = load_skill(agent, spec_path=step.get("spec_path"))

    # Denominador da barra de progresso: o que ESTE agente promete entregar.
    # Vive num dicionário próprio, e não no `_RUN_CTX`, porque quem desenha a
    # barra durante o streaming é o heartbeat, que roda fora daqui e só
    # conhece a fase. Pendurá-lo no `_RUN_CTX` fazia esse dict deixar de ser
    # vazio no despacho avulso (`--agent`), onde ele nunca é populado: o guard
    # `if not _RUN_CTX` do heartbeat parava de valer e cada batida varria a
    # resposta inteira por regex só para morrer num KeyError engolido.
    _esperados = expected_artifacts(phase, step, skill_content)
    _CONTRATO_EM_VOO.clear()
    _CONTRATO_EM_VOO.update({"phase": phase, "paths": _esperados})
    if _esperados:
        print(f"{DIM}  Contrato de saida: {len(_esperados)} artefato(s) "
              f"esperado(s) para {agent}{RESET}")
    else:
        print(f"{DIM}  Contrato de saida: nao declarado - barra do dashboard "
              f"fica em 'sem contrato'{RESET}")

    # ── F4 · Tech Stack — laço Ralph Wiggum por task do razão ───────────────
    # Antes de `load_context` pelo mesmo motivo da F5/F6: o manifesto de fase da
    # F4 injetava `specs/*/spec.md` de TODAS as features (659 KB medidos) em
    # cada despacho. Aqui o contexto é montado por task, em `f4_task_context`.
    if _is_f4_codegen_step(step):
        return _run_f4_codegen_step(
            client, step, project, output_dir,
            skill_content=skill_content, out_tokens=out_tokens,
            esperados=_esperados, headroom_active=_headroom_active)

    # ── F5 · DevOps Execute — laço Ralph Wiggum, contexto mínimo por tarefa ──
    # Fica ANTES de `load_context` de propósito: é justamente `load_context`
    # que expandia `outputs/tobe/source-code` e produzia o
    # `prompt is too long: 3924457 tokens > 1000000 maximum`. Este passo nunca
    # monta um contexto de fase; ele monta um contexto por TAREFA.
    if _is_f5_devops_step(step):
        return _run_devops_execute_step(
            client, step, project, output_dir,
            skill_content=skill_content, out_tokens=out_tokens,
            esperados=_esperados, headroom_active=_headroom_active)

    # ── F6 · QA Execute — dois momentos + laço Ralph Wiggum por tarefa ──────
    # Mesmo motivo da F5: `load_context` expandia `outputs/tobe/source-code`
    # (40.468 arquivos) e produzia `prompt is too long: 3958957 tokens`.
    if _is_f6_qa_step(step):
        return _run_qa_execute_step(
            client, step, project, output_dir,
            skill_content=skill_content, out_tokens=out_tokens,
            esperados=_esperados, headroom_active=_headroom_active)

    context        = load_context(project, step)
    system_prompt  = build_system_prompt(agent, skill_content, project, context, out_tokens, phase)
    skill_kb_pre   = len(skill_content) // 1024

    user_prompt    = build_prompt(agent, trigger, project, step.get("feature"))

    # ── Artefatos opcionais ausentes: decidir AQUI, nunca dentro do modelo ──
    # O pre-flight de alguns agentes manda pedir confirmação. Numa chamada
    # single-shot a pergunta é o fim da resposta: o agente encerra sem gerar
    # nada e a fase é contabilizada como executada. Quem tem console decide
    # antes, com prazo, e a decisão viaja no prompt.
    _prosseguir, _diretriz = confirmar_opcionais_ausentes(agent, project, phase)
    if not _prosseguir:
        _detalhe = ("cancelado no pre-flight: operador recusou gerar sem os "
                    "artefatos opcionais")
        _agora = datetime.datetime.now().timestamp()
        return {
            "phase": phase, "agent": agent, "skill_kb": skill_kb_pre,
            "inp_tokens": 0, "out_max": out_tokens, "resp_tokens": 0,
            "ctx_pct": 0.0, "elapsed_s": 0.0,
            "started_ts": _agora, "ended_ts": _agora,
            "artifacts": 0, "artifacts_written": [],
            "val_ok": False, "stop_reason": "preflight_cancelled",
            "incomplete": [], "detail": _detalhe,
            "headroom_used": _headroom_active,
            "contract_ok": 0, "contract_total": len(_esperados),
            "contract_missing": [], "contract_pending": list(_esperados),
        }
    if _diretriz:
        user_prompt = user_prompt + "\n\n" + _diretriz

    # Métricas reais de contexto (antes de enviar)
    inp_chars  = len(system_prompt) + len(user_prompt)
    inp_tokens = inp_chars // 4
    skill_kb   = len(skill_content) // 1024

    ctx_pct = (inp_tokens + out_tokens) / CTX_WINDOW * 100
    print(f"\n{DIM}  Enviando: {user_prompt}{RESET}")
    print(f"{DIM}  input≈{inp_tokens:,} tkns  out_max={out_tokens:,}  janela={ctx_pct:.1f}%  |  Aguardando resposta...{RESET}\n")
    print(f"{CYAN}{'─'*60}{RESET}")

    full_response = ""
    stop_reason   = "unknown"
    ts_start = datetime.datetime.now()
    stream_guard = _StreamFloodGuard()
    # Marca o passo como em voo antes do 1º token: TTFT + retries podem levar
    # minutos, e é justamente aí que o dashboard parecia parado.
    status_heartbeat(phase, ts_start, 0, force=True)

    full_response, stop_reason, inp_tokens, resp_tokens = _dispatch_model(
        client, system_prompt=system_prompt, user_prompt=user_prompt,
        out_tokens=out_tokens, phase=phase, ts_start=ts_start,
        stream_guard=stream_guard, inp_tokens_estimate=inp_tokens,
        budget_label=f"{phase}/{agent}")
    ts_end = datetime.datetime.now()
    elapsed_s = (ts_end - ts_start).total_seconds()
    stream_guard.flush_notice()

    print(f"\n{CYAN}{'─'*60}{RESET}")

    # Avisa se o modelo foi cortado por max_tokens
    truncated = (stop_reason == "max_tokens")
    if truncated:
        print(f"\n{YELLOW}  ⚠️  RESPOSTA TRUNCADA (stop_reason=max_tokens, teto={out_tokens:,})."
              f"  O último bloco FILE pode estar incompleto.{RESET}")

    # Extrair e escrever artefatos gerados pelo modelo
    written, incompletos = parse_and_write_outputs(full_response, project,
                                                   truncated=truncated)
    if written:
        print(f"\n{GREEN}  📄 Artefatos escritos ({len(written)}):{RESET}")
        for w in written:
            print(f"  {GREEN}     {w}{RESET}")

        # Avisa quando um agente grava fora do output_base declarado no DAG.
        # Causa clássica: confusão de identidade entre dois agentes com nomes
        # similares (ex: ava-speckit-compliance vs ava-deliverable-security-compliance).
        expected_base = (step or {}).get("output_base", "")
        if expected_base:
            proj_prefix = f"projects/{project}/{expected_base}".replace("\\", "/")
            fora_do_base = [
                w for w in written
                if not w.replace("\\", "/").startswith(proj_prefix)
            ]
            if fora_do_base:
                print(f"\n{RED}  ⚠️  ALERTA: {len(fora_do_base)} artefato(s) gravado(s) fora de '{proj_prefix}':{RESET}")
                for w in fora_do_base:
                    print(f"  {RED}     {w}{RESET}")
                print(f"  {RED}  Os artefatos declarados no DAG não serão encontrados no exit gate.{RESET}")
                print(f"  {RED}  Verifique se o agente confundiu sua identidade com outro agente.{RESET}")
    else:
        print(f"\n{YELLOW}  ⚠️  Nenhum bloco FILE: encontrado na resposta.{RESET}")

    # Salvar log da execução
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = _phase_log_path(output_dir, phase, agent, ts)
    out_file.write_text(
        f"# {phase} — {step['label']}\n\n"
        f"**Agente:** @{agent}  \n"
        f"**Trigger:** {trigger or 'N/A'}  \n"
        f"**Projeto:** {project}  \n"
        f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
        f"**Artefatos gerados:** {len(written)}  \n\n"
        f"---\n\n"
        f"## Arquivos escritos\n\n" +
        ("\n".join(f"- `{w}`" for w in written) if written else "_Nenhum_") +
        f"\n\n## Prompt enviado\n\n```\n{user_prompt}\n```\n\n"
        f"## Resposta\n\n{full_response}\n",
        encoding="utf-8",
    )
    print(f"\n{GREEN}  ✅ Log salvo: {out_file.relative_to(WORKSPACE)}{RESET}")

    # Valida artefatos gerados contra o contrato da fase E contra os `outputs`
    # declarados no DAG para este passo (precisos por feature).
    validation = validate_phase_artifacts(phase, project, written, step=step,
                                          expected=_esperados)
    print_validation_report(phase, validation)

    # Truncamento é REPROVAÇÃO, não aviso. Antes, `stop_reason == max_tokens`
    # só imprimia um alerta amarelo e o passo seguia como executado, deixando o
    # furo para estourar um passo adiante, no consumidor (ISSUE-004).
    detail = ""
    if incompletos:
        validation["ok"] = False
        detail = ("resposta cortada por max_tokens; artefato(s) incompleto(s): "
                  + ", ".join(incompletos))
        print(f"\n{RED}  ❌ {phase} reprovado — {detail}{RESET}")
        print(f"{YELLOW}     Reexecute o passo. Se reincidir, eleve PHASE_MAX_TOKENS "
              f"para {phase.split(':', 1)[0]} ou divida o contrato de saída do agente.{RESET}")
    elif truncated:
        validation["ok"] = False
        detail = "resposta cortada por max_tokens (stop_reason=max_tokens)"
        print(f"\n{RED}  ❌ {phase} reprovado — {detail}{RESET}")
    elif validation.get("declared_missing"):
        detail = ("outputs declarados no DAG não gravados: "
                  + ", ".join(validation["declared_missing"]))
        print(f"\n{RED}  ❌ {phase} reprovado — {detail}{RESET}")

    # Retorna métricas reais da execução
    return {
        "phase":         phase,
        "agent":         agent,
        "skill_kb":      skill_kb,
        "inp_tokens":    inp_tokens,
        "out_max":       out_tokens,
        "resp_tokens":   resp_tokens,
        "ctx_pct":       (inp_tokens + out_tokens) / CTX_WINDOW * 100,
        "elapsed_s":     elapsed_s,
        # Epoch: `elapsed_s` sozinho não diz QUANDO a fase rodou, e o relatório
        # de métricas precisa do intervalo. Serializa como número, sobrevive à
        # ida e volta pelo runner-state.json de uma retomada.
        "started_ts":    ts_start.timestamp(),
        "ended_ts":      ts_end.timestamp(),
        "artifacts":     len(written),
        "artifacts_written": written,
        "val_ok":        validation["ok"],
        "stop_reason":   stop_reason,
        "incomplete":    incompletos,
        "detail":        detail,
        "headroom_used": _headroom_active,
        # Denominador da barra de progresso do dashboard: quanto do contrato de
        # ENTREGA do agente (Output Contract do skill + `outputs` do DAG +
        # required/optional da fase) o passo realmente gravou. Antes o
        # denominador era so o `required` da fase - lista de 1 item para a
        # maioria dos agentes -, e por isso a barra vivia em "1/1 - 100%"
        # enquanto o agente entregava 9 artefatos. Cai de volta no `required`
        # quando nenhuma fonte declara contrato, para nao inventar 0%.
        "contract_ok":      (validation.get("expected_ok", 0)
                             + validation.get("expected_extra", 0)
                             if validation.get("expected_total")
                             else len(validation["required_ok"])),
        "contract_total":   (validation.get("expected_total", 0)
                             + validation.get("expected_extra", 0)
                             if validation.get("expected_total")
                             else len(validation["required_ok"])
                             + len(validation["required_missing"])),
        "contract_missing": list(validation["required_missing"]),
        # Itens do contrato de entrega ainda ausentes - nao reprovam a fase,
        # mas explicam por que a barra nao fechou 100%.
        "contract_pending": list(validation.get("expected_missing") or []),
    }


def _compute_phase_row(phase: str, step: dict, metrics: dict,
                       executed: list, skipped: list, aborted: list,
                       val_failed: "list | None" = None) -> dict:
    """Calcula todos os campos de uma linha do quadro de contexto para uma fase.

    Campos retornados:
      status_tag  — "exec" | "skip" | "abort" | "val_fail" | "pending"
      agent       — nome do agente
      skill_kb    — tamanho do skill em KB
      inp         — tokens de input (real)
      out_max     — limite max_tokens configurado
      total       — inp + out_max
      uso_pct     — total / CTX_WINDOW * 100
      resp        — tokens de resposta (estimativa)
      elapsed_s   — tempo em segundos
      artifacts   — artefatos escritos
      val_ok      — validação do contrato
      truncated   — skill foi truncado pelo CTX_SKILL
      headroom_on — proxy headroom estava ativo (inp < baseline estimado)
      compress_pct— % de compressão vs baseline (0 se headroom inativo)
      baseline    — tokens estimados sem headroom
    """
    CTX_PROJ_BASELINE = 57_000  # ctx projeto medido (config + artefatos)
    agent = step["agent"]

    if (val_failed is not None and phase in val_failed) or (
        val_failed is None and phase in skipped
        and (metrics.get(phase) or {}).get("val_ok") is False
        and not (metrics.get(phase) or {}).get("risk_accepted")
    ):
        m = metrics.get(phase) or {}
        if m.get("inp_tokens"):
            # Executou mas falhou na validação: exibe métricas reais
            sk = m.get("skill_kb", 0)
            inp = m.get("inp_tokens", 0)
            out_max = m.get("out_max", 0)
            total = inp + out_max
            uso_pct = total / CTX_WINDOW * 100
            baseline = (sk * 1024 // 4) + CTX_PROJ_BASELINE
            reducao = baseline - inp
            headroom_on = m.get("headroom_used", False)
            compress_pct = reducao / baseline * 100 if headroom_on and baseline > 0 and reducao > 0 else 0.0
            return {
                "status_tag": "val_fail", "agent": agent,
                "skill_kb": sk, "inp": inp, "out_max": out_max, "total": total,
                "uso_pct": uso_pct, "resp": m.get("resp_tokens", 0),
                "elapsed_s": m.get("elapsed_s", 0.0), "artifacts": m.get("artifacts", 0),
                "val_ok": False, "truncated": sk >= CTX_SKILL // 1024,
                "headroom_on": headroom_on, "compress_pct": compress_pct, "baseline": baseline,
            }
        return {"status_tag": "val_fail", "agent": agent, "detail": m.get("detail", "")}
    if phase in skipped:
        return {"status_tag": "skip", "agent": agent}
    if phase in aborted:
        return {"status_tag": "abort", "agent": agent}
    if phase not in executed:
        return {"status_tag": "pending", "agent": agent}

    m = metrics.get(phase)
    if not m:
        return {"status_tag": "exec", "agent": agent,
                "skill_kb": 0, "inp": 0, "out_max": 0, "total": 0,
                "uso_pct": 0.0, "resp": 0, "elapsed_s": 0.0,
                "artifacts": 0, "val_ok": True, "truncated": False,
                "headroom_on": False, "compress_pct": 0.0, "baseline": 0}

    sk      = m["skill_kb"]
    inp     = m["inp_tokens"]
    out_max = m["out_max"]
    total   = inp + out_max
    uso_pct = total / CTX_WINDOW * 100
    # Headroom baseline: tokens estimados sem compressão
    baseline     = (sk * 1024 // 4) + CTX_PROJ_BASELINE
    reducao      = baseline - inp
    # headroom_on: usa valor real gravado por run_step (True = proxy URL em uso)
    headroom_on  = m.get("headroom_used", False)
    compress_pct = reducao / baseline * 100 if headroom_on and baseline > 0 and reducao > 0 else 0.0

    return {
        "status_tag":    "exec",
        "agent":         agent,
        "skill_kb":      sk,
        "inp":           inp,
        "out_max":       out_max,
        "total":         total,
        "uso_pct":       uso_pct,
        "resp":          m["resp_tokens"],
        "elapsed_s":     m["elapsed_s"],
        "artifacts":     m["artifacts"],
        "val_ok":        m["val_ok"],
        "truncated":     sk >= CTX_SKILL // 1024,
        "headroom_on":   headroom_on,
        "compress_pct":  compress_pct,
        "baseline":      baseline,
    }


def print_final_summary(project: str, executed: list[str], skipped: list[str],
                        aborted: list[str], active_steps: list[dict],
                        exec_metrics: "dict[str, dict] | None" = None,
                        val_failed: "list[str] | None" = None):
    """Exibe resumo final com dados REAIS da execução.
    exec_metrics: {phase -> dict retornado por run_step()}
    """
    CTX_LIMIT = CTX_WINDOW  # janela real confirmada (1M tokens)
    proj_path = WORKSPACE / "projects" / project
    metrics   = exec_metrics or {}

    # ── Artefatos em disco ────────────────────────────────────────
    out_root = proj_path / "outputs"
    arts_all: list[Path] = []
    if out_root.exists():
        arts_all = [p for p in out_root.rglob("*")
                    if p.is_file() and "pipeline_runner" not in str(p)]

    by_folder: dict[str, list[Path]] = {}
    for a in sorted(arts_all):
        try:
            rel    = a.relative_to(out_root)
            folder = rel.parts[0] if len(rel.parts) > 1 else "."
        except ValueError:
            folder = "."
        by_folder.setdefault(folder, []).append(a)

    banner("📦 Resumo de Artefatos Gerados", CYAN)
    total_kb = sum(a.stat().st_size for a in arts_all) // 1024
    print(f"\n  Total: {len(arts_all)} arquivos  ({total_kb} KB)  →  {out_root}\n")

    for folder, files in sorted(by_folder.items()):
        folder_kb = sum(f.stat().st_size for f in files) // 1024
        print(f"  {CYAN}📁 {folder}/{RESET}  ({len(files)} arqs, {folder_kb} KB)")
        for f in files[:6]:
            sz = f.stat().st_size
            print(f"     {DIM}{f.name:<45}  {sz//1024:>3}KB{RESET}")
        if len(files) > 6:
            print(f"     {DIM}... e mais {len(files)-6} arquivo(s){RESET}")
    print()

    # ── Quadro de uso de contexto (dados REAIS) ───────────────────
    banner("📊 Quadro de Contexto por Fase — Dados Reais da Execução", CYAN)
    print(f"\n  Modelo: {DEPLOYMENT}  |  Janela: {CTX_LIMIT:,} tokens\n")

    # Cabeçalho do quadro consolidado
    # Colunas: Fase | Agente | Skill | Inp | OutMax | Total | Uso% | Status | Headroom | %Compr
    hdr = (f"  {'Fase':<6}  {'Agente':<28}  {'Skill':>5}  "
           f"{'Inp':>8}  {'OutMax':>7}  {'Total':>8}  "
           f"{'Uso%':>6}  {'Status':>8}  {'Headroom':>8}  {'%Compr':>7}")
    sep = (f"  {'─'*6}  {'─'*28}  {'─'*5}  "
           f"{'─'*8}  {'─'*7}  {'─'*8}  "
           f"{'─'*6}  {'─'*8}  {'─'*8}  {'─'*7}")
    print(hdr)
    print(sep)

    total_inp = total_resp = total_arts = total_s = 0
    total_baseline_acc = 0

    for step in active_steps:
        phase = step["phase"]
        row   = _compute_phase_row(phase, step, metrics, executed, skipped, aborted,
                                   val_failed=val_failed)

        if row["status_tag"] == "skip":
            print(f"  {YELLOW}{phase:<6}  {row['agent']:<28}  "
                  f"{'—':>5}  {'—':>8}  {'—':>7}  {'—':>8}  "
                  f"{'—':>6}  {'⏭ pulado':>8}  {'—':>8}  {'—':>7}{RESET}")
            continue
        if row["status_tag"] == "abort":
            print(f"  {RED}{phase:<6}  {row['agent']:<28}  "
                  f"{'—':>5}  {'—':>8}  {'—':>7}  {'—':>8}  "
                  f"{'—':>6}  {'🛑 abort':>8}  {'—':>8}  {'—':>7}{RESET}")
            continue
        if row["status_tag"] == "val_fail":
            if row.get("inp"):
                # Executou mas falhou validação: exibe tokens/tempo reais e destaca em vermelho
                t_str = (f"{row['elapsed_s']:.0f}s" if row["elapsed_s"] < 60
                         else f"{row['elapsed_s']/60:.1f}m")
                hdr_icon = (f"{GREEN}✅ ativo{RESET}" if row.get("headroom_on")
                            else f"{DIM}— off{RESET}")
                comp_str = f"{DIM}{'—':>6}{RESET}"
                print(f"  {RED}{phase:<6}  {row['agent']:<28}  "
                      f"{row['skill_kb']:>3}K   "
                      f"{row['inp']:>8,}  {row['out_max']:>7,}  {row['total']:>8,}  "
                      f"{row['uso_pct']:>5.1f}%  {'❌ val_fail':>10}  {RESET}"
                      f"{hdr_icon}  {comp_str}")
                total_inp  += row["inp"]
                total_resp += row.get("resp", 0)
                total_arts += row.get("artifacts", 0)
                total_s    += row.get("elapsed_s", 0.0)
                total_baseline_acc += row.get("baseline", 0)
            else:
                print(f"  {RED}{phase:<6}  {row['agent']:<28}  "
                      f"{'—':>5}  {'—':>8}  {'—':>7}  {'—':>8}  "
                      f"{'—':>6}  {'❌ val_fail':>10}  {'—':>8}  {'—':>7}{RESET}")
            continue
        if row["status_tag"] == "pending":
            continue

        inp    = row["inp"]
        out_mx = row["out_max"]
        total  = row["total"]
        uso    = row["uso_pct"]
        sk     = row["skill_kb"]
        trunc  = "T" if row["truncated"] else " "
        t_str  = (f"{row['elapsed_s']:.0f}s" if row["elapsed_s"] < 60
                  else f"{row['elapsed_s']/60:.1f}m")

        # Status: val + truncado
        val_icon  = "✅" if row["val_ok"] else "❌"
        trunc_tag = " ✂T" if row["truncated"] else "   "
        status_str = f"{val_icon}{trunc_tag}"

        # Headroom
        hdr_icon  = f"{GREEN}✅ ativo{RESET}" if row["headroom_on"] else f"{DIM}— off{RESET}"

        # %Compressão
        if row["compress_pct"] > 0:
            comp_color = GREEN if row["compress_pct"] > 30 else YELLOW
            comp_str   = f"{comp_color}{row['compress_pct']:>5.1f}%{RESET}"
        else:
            comp_str   = f"{DIM}{'—':>6}{RESET}"

        # Cor da linha baseada no Uso%
        if uso < 70:
            lcolor = GREEN
        elif uso < 90:
            lcolor = YELLOW
        else:
            lcolor = RED

        total_inp        += inp
        total_resp       += row["resp"]
        total_arts       += row["artifacts"]
        total_s          += row["elapsed_s"]
        total_baseline_acc += row["baseline"]

        print(f"  {lcolor}{phase:<6}  {row['agent']:<28}  {sk:>3}K{trunc}  "
              f"{inp:>8,}  {out_mx:>7,}  {total:>8,}  "
              f"{uso:>5.1f}%  {status_str}  {RESET}"
              f"{hdr_icon}  {comp_str}")

    # Rodapé com totais
    t_total      = f"{total_s:.0f}s" if total_s < 60 else f"{total_s/60:.1f}m"
    total_total  = total_inp + 0   # total = soma dos inp (out_max varia por fase)
    total_compr  = (total_baseline_acc - total_inp) / total_baseline_acc * 100 if total_baseline_acc > 0 else 0.0
    print(sep)
    print(f"  {'TOTAL':<6}  {'':28}  {'':5}  "
          f"{total_inp:>8,}  {'':>7}  {'':>8}  "
          f"{'':>6}  {'':>8}  {'':>8}  "
          f"{GREEN if total_compr > 0 else DIM}{total_compr:>5.1f}%{RESET}")

    print(f"\n  {BOLD}Legenda:{RESET}")
    print(f"  {DIM}  Inp     = tokens enviados ao modelo (skill + ctx + system prompt)")
    print(f"  OutMax  = limite max_tokens configurado por fase")
    print(f"  Total   = Inp + OutMax (janela consumida na chamada)")
    print(f"  Uso%    = Total / {CTX_LIMIT:,} × 100  (uso da janela de contexto)")
    print(f"  Status  = ✅/❌ contrato de artefatos  |  ✂T = skill truncado  |  ❌ val_fail = executou mas gravou no lugar errado")
    print(f"  Headroom= proxy de compressão ativo/inativo na fase")
    print(f"  %Compr  = tokens economizados vs. baseline estimado sem headroom{RESET}")
    vf_list = val_failed or []
    vf_count = len(vf_list)
    print(f"\n  {DIM}{len(arts_all)} artefatos em disco — "
          f"{len(executed)}✅ executados  {len(skipped)}⏭ pulados  "
          + (f"{RED}{vf_count}❌ val_fail  {RESET}{DIM}" if vf_count else "")
          + f"{len(aborted)}🛑 abortados — tempo total: {t_total}{RESET}\n")

    # ── Salva relatórios em disco ──────────────────────────────────────────────
    _save_execution_report(
        project, executed, skipped, aborted, metrics,
        active_steps, arts_all, by_folder, total_kb, t_total,
        val_failed=val_failed,
    )
    _save_headroom_report(project, metrics, active_steps, executed)


def _save_execution_report(
    project: str, executed: list, skipped: list, aborted: list,
    metrics: dict, active_steps: list, arts_all: list, by_folder: dict,
    total_kb: int, t_total: str,
    val_failed: "list | None" = None,
) -> None:
    """Salva execution-report.md na pasta pipeline_runner do projeto."""
    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir  = WORKSPACE / "projects" / project / "outputs" / "pipeline_runner"
    out_dir.mkdir(parents=True, exist_ok=True)
    report   = out_dir / f"execution-report_{ts}.md"

    lines: list[str] = [
        f"# Execution Report — {project}",
        f"",
        f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Modelo:** {DEPLOYMENT}  ",
        f"**Janela:** {CTX_WINDOW:,} tokens  ",
        f"**Tempo total:** {t_total}  ",
        f"",
        f"## Resultado",
        f"",
        f"| Status | Fases |",
        f"|---|---|",
        f"| ✅ Executadas | {len(executed)} — {', '.join(executed) or '—'} |",
        f"| ⏭ Puladas | {len(skipped)} — {', '.join(skipped) or '—'} |",
        f"| ❌ Val-Fail | {len(val_failed or [])} — {', '.join(val_failed or []) or '—'} |",
        f"| 🛑 Abortadas | {len(aborted)} — {', '.join(aborted) or '—'} |",
        f"",
        f"## Artefatos em Disco",
        f"",
        f"**Total:** {len(arts_all)} arquivos ({total_kb} KB)",
        f"",
        f"| Pasta | Arquivos | KB |",
        f"|---|---|---|",
    ]
    for folder, files in sorted(by_folder.items()):
        kb = sum(f.stat().st_size for f in files) // 1024
        lines.append(f"| {folder}/ | {len(files)} | {kb} |")

    lines += [
        f"",
        f"## Uso de Contexto por Fase",
        f"",
        f"| Fase | Agente | Skill | Input | Resp | OutMax | Uso% | Tempo | Arts | Val |",
        f"|---|---|---|---|---|---|---|---|---|---|",
    ]

    total_inp = total_resp = total_arts = total_s = 0
    for step in active_steps:
        phase = step["phase"]
        agent = step["agent"]
        if phase in skipped:
            lines.append(f"| {phase} | {agent} | — | — | — | — | ⏭ | — | — | — |")
            continue
        if phase in (val_failed or []):
            m = metrics.get(phase) or {}
            val_icon = "❌ val_fail"
            if m.get("inp_tokens"):
                pct = m.get("ctx_pct", 0)
                t_str = f"{m['elapsed_s']:.0f}s" if m.get("elapsed_s", 0) < 60 else f"{m['elapsed_s']/60:.1f}m"
                lines.append(
                    f"| {phase} | {agent} | {m.get('skill_kb', 0)}KB | {m.get('inp_tokens', 0):,} | "
                    f"{m.get('resp_tokens', 0):,} | {m.get('out_max', 0):,} | {pct:.1f}% ❌ | "
                    f"{t_str} | {m.get('artifacts', 0)} | {val_icon} |"
                )
            else:
                lines.append(f"| {phase} | {agent} | — | — | — | — | ❌ val_fail | — | — | — |")
            continue
        if phase in aborted:
            lines.append(f"| {phase} | {agent} | — | — | — | — | 🛑 | — | — | — |")
            continue
        if phase not in executed:
            continue
        m = metrics.get(phase)
        if m:
            pct    = m["ctx_pct"]
            t_str  = f"{m['elapsed_s']:.0f}s" if m["elapsed_s"] < 60 else f"{m['elapsed_s']/60:.1f}m"
            icon   = "✅" if pct < 70 else ("⚠️" if pct < 90 else "🔴")
            val    = "✅" if m["val_ok"] else "❌"
            lines.append(
                f"| {phase} | {agent} | {m['skill_kb']}KB | {m['inp_tokens']:,} | "
                f"{m['resp_tokens']:,} | {m['out_max']:,} | {pct:.1f}% {icon} | "
                f"{t_str} | {m['artifacts']} | {val} |"
            )
            total_inp  += m["inp_tokens"]
            total_resp += m["resp_tokens"]
            total_arts += m["artifacts"]
            total_s    += m["elapsed_s"]
        else:
            lines.append(f"| {phase} | {agent} | — | — | — | — | — | — | — | — |")

    t_tot = f"{total_s:.0f}s" if total_s < 60 else f"{total_s/60:.1f}m"
    grand_total = total_inp + total_resp
    lines += [
        f"| **TOTAL** | | | **{total_inp:,}** | **{total_resp:,}** | | | **{t_tot}** | **{total_arts}** | |",
        "",
        "## 🔢 Consumo Total de Tokens na Migração",
        "",
        "| Métrica | Tokens | Escala |",
        "|---|---:|---:|",
        f"| **INPUT total** (enviado ao modelo) | **{total_inp:,}** | {total_inp/1_000_000:.2f} M |",
        f"| **OUTPUT total** (gerado pelo modelo) | **{total_resp:,}** | {total_resp/1_000:.1f} K |",
        f"| **Grand Total** (input + output) | **{grand_total:,}** | {grand_total/1_000_000:.2f} M |",
        f"| Temperatura utilizada | {TEMPERATURE} | determinístico |",
        f"| Modelo | {DEPLOYMENT} | — |",
        f"| Fases executadas | {len(executed)} | — |",
        f"| Artefatos gerados | {total_arts} | — |",
        f"| Tempo total | {t_tot} | — |",
        "",
        "### 💰 Custo Estimado (referência Anthropic pública)",
        "",
        "| Componente | Tokens | Rate | Valor est. |",
        "|---|---:|---|---:|",
        f"| Input  | {total_inp:,} | \\$3.00/M | \\${total_inp * 3.0 / 1_000_000:.2f} |",
        f"| Output | {total_resp:,} | \\$15.00/M | \\${total_resp * 15.0 / 1_000_000:.2f} |",
        f"| **Total** | {grand_total:,} | — | **\\${(total_inp * 3.0 + total_resp * 15.0) / 1_000_000:.2f}** |",
        "",
        "## Legenda",
        "",
        "- **Input** = tokens enviados ao modelo (skill + ctx projeto + system) — valor REAL da API",
        "- **Output** = tokens gerados pelo modelo — valor REAL da API (usage.output_tokens)",
        f"- **OutMax** = limite max_tokens configurado por fase",
        f"- **Uso%** = (Input + OutMax) / {CTX_WINDOW:,} × 100",
        "- **Val** = validação do contrato de artefatos da fase",
        "",
        "---",
        "*Gerado automaticamente pelo ava-pipeline-runner-cli.py — AVA Fabric*",
    ]

    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{GREEN}  📄 Execution report salvo: {report.relative_to(WORKSPACE)}{RESET}")


def _save_headroom_report(
    project: str, metrics: dict, active_steps: list, executed: list
) -> None:
    """Salva headroom-optimization.md com análise de compressão e oportunidades."""
    ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = WORKSPACE / "projects" / project / "outputs" / "pipeline_runner"
    out_dir.mkdir(parents=True, exist_ok=True)
    report  = out_dir / f"headroom-optimization_{ts}.md"

    # Calcula estatísticas de compressão comparando inp_tokens vs baseline estimado
    # Baseline: skill_kb*1024/4 + 57_000 (ctx projeto medido)
    CTX_PROJ_BASELINE = 57_000

    lines: list[str] = [
        f"# Headroom Optimization Report — {project}",
        f"",
        f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Janela deployment IMF:** {CTX_WINDOW:,} tokens (validado 2026-08-05)  ",
        f"**ART_INJECT_MAX:** {ART_INJECT_MAX} artefatos  ",
        f"**ART_INJECT_CHARS:** {ART_INJECT_CHARS:,} chars/artefato  ",
        f"",
        f"## Análise de Uso por Fase",
        f"",
        f"| Fase | Input Real | Baseline Est. | Redução | % Janela Real | % Janela 1M | Margem |",
        f"|---|---|---|---|---|---|---|",
    ]

    total_inp = total_baseline = 0
    savings   = []

    for step in active_steps:
        phase = step["phase"]
        if phase not in executed:
            continue
        m = metrics.get(phase)
        if not m:
            continue

        sk_tokens  = m["skill_kb"] * 1024 // 4
        baseline   = sk_tokens + CTX_PROJ_BASELINE
        inp        = m["inp_tokens"]
        reducao    = baseline - inp
        pct_red    = reducao / baseline * 100 if baseline > 0 else 0
        pct_1m     = inp / CTX_WINDOW * 100
        margem     = CTX_WINDOW - inp - m["out_max"]

        icon = "✅" if pct_red > 30 else ("⚠️" if pct_red > 0 else "➡️")
        lines.append(
            f"| {phase} | {inp:,} | {baseline:,} | "
            f"{reducao:,} ({pct_red:.0f}%) {icon} | "
            f"{m['ctx_pct']:.1f}% | {pct_1m:.1f}% | {margem:,} |"
        )
        total_inp      += inp
        total_baseline += baseline
        savings.append(reducao)

    total_reducao = total_baseline - total_inp
    pct_total     = total_reducao / total_baseline * 100 if total_baseline > 0 else 0

    lines += [
        f"",
        f"## Resumo da Compressão (Headroom)",
        f"",
        f"| Métrica | Valor |",
        f"|---|---|",
        f"| Total input sem headroom (baseline) | {total_baseline:,} tokens |",
        f"| Total input com headroom (real) | {total_inp:,} tokens |",
        f"| **Tokens economizados** | **{total_reducao:,} tokens ({pct_total:.1f}%)** |",
        f"| Fases com redução > 30% | {sum(1 for s in savings if s > 0)} |",
        f"| Janela utilizada média por fase | {total_inp // max(len(savings), 1):,} tokens |",
        f"| Janela disponível (1M) — uso total | {total_inp / CTX_WINDOW * 100:.1f}% |",
        f"",
        f"## Oportunidades de Melhoria",
        f"",
    ]

    # Identifica fases com maior desperdício de janela
    high_margin = []
    low_content = []
    for step in active_steps:
        phase = step["phase"]
        if phase not in executed:
            continue
        m = metrics.get(phase)
        if not m:
            continue
        margem_pct = (CTX_WINDOW - m["inp_tokens"] - m["out_max"]) / CTX_WINDOW * 100
        if margem_pct > 80:
            high_margin.append((phase, margem_pct, m["inp_tokens"]))
        if m["resp_tokens"] < m["out_max"] * 0.2:
            low_content.append((phase, m["resp_tokens"], m["out_max"]))

    if high_margin:
        lines.append(f"### Fases com muita margem livre (> 80% da janela disponível)")
        lines.append(f"")
        lines.append(f"Estas fases poderiam receber mais contexto de artefatos:")
        lines.append(f"")
        for ph, pct, inp in high_margin:
            extra = int((CTX_WINDOW * 0.7 - inp) * 4)  # chars extras disponíveis
            lines.append(f"- **{ph}**: {pct:.0f}% de margem livre — pode injetar mais ~{extra:,} chars")
    else:
        lines.append(f"### ✅ Nenhuma fase com margem excessiva — uso bem distribuído")

    lines.append(f"")

    if low_content:
        lines.append(f"### Fases com resposta pequena vs. OutMax configurado")
        lines.append(f"")
        lines.append(f"Estas fases poderiam ter OutMax reduzido para economizar janela:")
        lines.append(f"")
        for ph, resp, out_max in low_content:
            sugerido = max(int(resp * 1.5), 16_384)
            lines.append(f"- **{ph}**: resp={resp:,} vs OutMax={out_max:,} — "
                         f"sugerido OutMax={sugerido:,}")

    lines += [
        f"",
        f"## Configuração Atual",
        f"",
        f"```python",
        f"CTX_WINDOW       = {CTX_WINDOW:,}   # janela real validada",
        f"ART_INJECT_MAX   = {ART_INJECT_MAX}       # artefatos injetados",
        f"ART_INJECT_CHARS = {ART_INJECT_CHARS:,}   # chars por artefato",
        f"PHASE_MAX_TOKENS = {{",
    ]
    for phase, max_t in PHASE_MAX_TOKENS.items():
        lines.append(f'    "{phase}": {max_t:,},')
    lines += [
        f"}}",
        f"```",
        f"",
        f"---",
        f"*Gerado automaticamente pelo ava-pipeline-runner-cli.py — AVA Fabric*",
    ]

    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"{GREEN}  📊 Headroom report salvo: {report.relative_to(WORKSPACE)}{RESET}")


# ── Requisitos do pipeline ────────────────────────────────────────────────────
# Levantados a partir de src/modules/ava-fabric-agents (2026-08-05)
# Cada entrada: (pacote_pip, import_name, descricao)
PYTHON_REQUIREMENTS: list[tuple[str, str, str]] = [
    ("anthropic",   "anthropic",   "Anthropic SDK — chamadas ao Claude via Foundry IMF"),
    ("requests",    "requests",    "HTTP client — healthcheck do headroom proxy"),
    ("pyyaml",      "yaml",        "Leitura de project-config.yaml e artefatos YAML"),
]

# Ferramentas externas opcionais (não bloqueiam, apenas avisam)
OPTIONAL_TOOLS: list[tuple[str, list[str], str]] = [
    ("dotnet",    ["dotnet", "--version"],          "Necessário apenas para ava-stack-build-validator"),
    ("node",      ["node",   "--version"],          "Necessário apenas para testes frontend Angular"),
    ("docker",    ["docker", "--version"],          "Necessário apenas para containerização (ava-devops-containerize)"),
    ("terraform", ["terraform", "--version"],       "Necessário apenas para IaC Terraform (ava-devops-iac)"),
    ("az",        ["az",    "--version"],            "Necessário apenas para deploys Azure (ava-devops-cd)"),
]


def check_and_install_requirements(auto_install: bool = False) -> bool:
    """
    Valida requisitos Python e ferramentas externas.
    Se auto_install=True, instala pacotes pip faltantes automaticamente.
    Retorna True se todos os requisitos OBRIGATÓRIOS estão OK.
    """
    import importlib, importlib.util

    banner("🔍 Validação de Requisitos", CYAN)
    all_ok = True

    # ── Python packages (obrigatórios) ────────────────────────────
    print(f"\n  {BOLD}Pacotes Python obrigatórios:{RESET}")
    missing_pip: list[tuple[str, str]] = []

    for pkg, import_name, desc in PYTHON_REQUIREMENTS:
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            # Tenta pegar versão instalada
            try:
                mod = importlib.import_module(import_name)
                ver = getattr(mod, "__version__", "?")
            except Exception:
                ver = "?"
            print(f"  {GREEN}✅ {pkg:<20}{RESET}  v{ver:<10}  {DIM}{desc}{RESET}")
        else:
            print(f"  {RED}❌ {pkg:<20}{RESET}  {RED}NÃO INSTALADO{RESET}  {DIM}{desc}{RESET}")
            missing_pip.append((pkg, desc))
            all_ok = False

    if missing_pip:
        print(f"\n  {YELLOW}⚠️  {len(missing_pip)} pacote(s) faltando.{RESET}")
        if auto_install:
            install = "S"
        else:
            install = safe_input(f"  {BOLD}Instalar agora com pip? [S/N]: {RESET}").strip().upper()

        if install == "S":
            for pkg, desc in missing_pip:
                print(f"\n  {DIM}  pip install {pkg}...{RESET}")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    print(f"  {GREEN}✅ {pkg} instalado com sucesso.{RESET}")
                    all_ok = True  # recalcula
                else:
                    print(f"  {RED}❌ Falha ao instalar {pkg}:{RESET}")
                    print(f"  {DIM}{result.stderr[:200]}{RESET}")
        else:
            print(f"\n  {RED}  Execute: pip install {' '.join(p for p, _ in missing_pip)}{RESET}")

    # ── Ferramentas externas (opcionais) ──────────────────────────
    print(f"\n  {BOLD}Ferramentas externas (opcionais):{RESET}")
    for name, cmd, desc in OPTIONAL_TOOLS:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            ver_line = result.stdout.strip().split("\n")[0][:40] if result.stdout else "ok"
            print(f"  {GREEN}✅ {name:<12}{RESET}  {DIM}{ver_line:<40}  {desc}{RESET}")
        except FileNotFoundError:
            print(f"  {YELLOW}⚠️  {name:<12}{RESET}  {YELLOW}não encontrado{RESET}  {DIM}{desc}{RESET}")
        except Exception:
            print(f"  {DIM}○  {name:<12}  (não verificado)  {desc}{RESET}")

    # ── VPN / Conectividade ───────────────────────────────────────
    print(f"\n  {BOLD}Conectividade:{RESET}")
    endpoint_host = "aif-imf-apps-prd-eus2-001.services.ai.azure.com"
    try:
        import socket as _sock
        ip = _sock.gethostbyname(endpoint_host)
        if ip.startswith("10."):
            print(f"  {GREEN}✅ DNS privado OK{RESET}  {DIM}{endpoint_host} → {ip}{RESET}")
        else:
            print(f"  {YELLOW}⚠️  DNS público{RESET}  {DIM}{endpoint_host} → {ip} (VPN pode estar inativa){RESET}")
    except Exception as e:
        print(f"  {RED}❌ DNS falhou{RESET}  {DIM}{e}{RESET}")
        print(f"  {DIM}     O pipeline usa DNS patch interno — pode funcionar mesmo assim.{RESET}")

    # DNS OK não é VPN ativa: o nome resolve para o IP privado mesmo com o
    # túnel morto. Só o handshake TCP diz se o tráfego passa.
    _tcp_ok, _tcp_info = foundry_tcp_probe(endpoint_host, timeout_s=5.0)
    if _tcp_ok:
        print(f"  {GREEN}✅ TCP 443 OK{RESET}      {DIM}{_tcp_info}:443 aceita conexão (VPN ativa){RESET}")
    else:
        print(f"  {RED}❌ TCP 443 falhou{RESET}  {DIM}{_tcp_info}{RESET}")
        print(f"  {DIM}     Nenhuma fase LLM vai funcionar — veja a remediação no [Auth].{RESET}")
        all_ok = False

    # ── .copilot-key ─────────────────────────────────────────────
    print(f"\n  {BOLD}Credenciais:{RESET}")
    if API_KEY_FILE.exists() and API_KEY_FILE.stat().st_size > 10:
        key_preview = API_KEY_FILE.read_text(encoding="utf-8").strip()[:8]
        print(f"  {GREEN}✅ .copilot-key{RESET}  {DIM}encontrado ({key_preview}...){RESET}")
    else:
        print(f"  {RED}❌ .copilot-key{RESET}  {RED}não encontrado em {API_KEY_FILE}{RESET}")
        print(f"  {DIM}     Crie o arquivo com a API Key do Foundry IMF (sem newline).{RESET}")
        all_ok = False

    # ── Estrutura do workspace ────────────────────────────────────
    print(f"\n  {BOLD}Estrutura do workspace:{RESET}")
    required_dirs = [
        (WORKSPACE / "src" / "modules" / "ava-fabric-agents", "Skills dos agentes"),
        (WORKSPACE / "projects",                              "Pasta de projetos"),
        (WORKSPACE / ".github" / "skills",                    "Stubs de skills"),
    ]
    for path, desc in required_dirs:
        if path.exists():
            count = sum(1 for _ in path.rglob("*.md")) if path.is_dir() else 0
            print(f"  {GREEN}✅ {desc:<30}{RESET}  {DIM}{path.relative_to(WORKSPACE)}  ({count} .md){RESET}")
        else:
            print(f"  {RED}❌ {desc:<30}{RESET}  {RED}não encontrado: {path.relative_to(WORKSPACE)}{RESET}")
            all_ok = False

    # ── Resultado ─────────────────────────────────────────────────
    print(f"\n{CYAN}{'─'*60}{RESET}")
    if all_ok:
        print(f"  {GREEN}{BOLD}✅ Todos os requisitos obrigatórios OK — pronto para executar!{RESET}")
    else:
        print(f"  {RED}{BOLD}❌ Requisitos pendentes — resolva os itens acima antes de prosseguir.{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}\n")

    return all_ok


def list_projects() -> list[str]:
    projects_dir = WORKSPACE / "projects"
    return [p.name for p in projects_dir.iterdir() if p.is_dir() and not p.name.startswith("_")]


def validate_ast_prerequisites(project: str) -> dict:
    """Valida pré-requisitos do F0/AST seguindo EXATAMENTE a mesma lógica do run_ast_step().

    Regras (espelham run_ast_step):
      - Sem campo configurado (ava_ast_analyzers[tech] e ava_ast_analyzer_path vazios)
        → skip_ast=True, ready=True (F0 será silencioso, sem validação extra)
      - Campo configurado mas path não existe → skip_ast=False, ready=False (ERRO)
      - Campo configurado e path existe, mas run_ast_analysis.py ausente → ready=False (ERRO)
      - Tudo OK → skip_ast=False, ready=True

    Precedência do analyzer (igual ao run_ast_step):
      1. ava_ast_analyzers[legacy_technology]   ← mapa multi-linguagem
      2. ava_ast_analyzer_path                  ← alias legado (qualquer tecnologia)

    Retorna dict: ready, skip_ast, checks, warnings
    """
    import yaml as _yaml

    checks:   list[dict] = []
    warnings: list[str]  = []

    # ── Lê project-config ────────────────────────────────────────
    cfg_path = WORKSPACE / "projects" / project / "context" / "project-config.yaml"
    if not cfg_path.exists():
        return {"ready": False, "skip_ast": False,
                "checks": [{"label": "project-config.yaml", "ok": False,
                             "detail": str(cfg_path), "note": "Arquivo não encontrado"}],
                "warnings": []}
    try:
        cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ready": False, "skip_ast": False,
                "checks": [{"label": "project-config.yaml", "ok": False,
                             "detail": str(cfg_path), "note": f"Erro ao ler: {e}"}],
                "warnings": []}

    legacy_tech = (cfg.get("legacy_technology") or "").strip().lower()

    # ── Resolver analyzer path (mesma precedência do run_ast_step) ─
    analyzers_map     = cfg.get("ava_ast_analyzers") or {}
    analyzer_path_str = ""
    if isinstance(analyzers_map, dict) and legacy_tech:
        analyzer_path_str = (analyzers_map.get(legacy_tech) or "").strip()
    if not analyzer_path_str:
        analyzer_path_str = (cfg.get("ava_ast_analyzer_path") or "").strip()

    # ── Regra 1: campo vazio → skip silencioso, sem validação ─────
    if not analyzer_path_str:
        return {"ready": True, "skip_ast": True, "checks": [], "warnings": [
            "ava_ast_analyzer_path não configurado — F0 será pulado silenciosamente (comportamento normal)."
        ]}

    # ── Campo preenchido → valida cada pré-requisito ──────────────

    # Check 1: legacy_technology presente
    checks.append({
        "label":  "legacy_technology",
        "ok":     bool(legacy_tech),
        "detail": legacy_tech or "(vazio)",
        "note":   "OK" if legacy_tech else "Campo ausente — necessário para selecionar o analyzer correto",
    })

    # Check 2: resolver qual chave do config foi usada e se o path existe
    source_key = (f"ava_ast_analyzers[{legacy_tech}]"
                  if isinstance(analyzers_map, dict) and analyzers_map.get(legacy_tech)
                  else "ava_ast_analyzer_path")
    analyzer_exists = Path(analyzer_path_str).exists()
    checks.append({
        "label":  source_key,
        "ok":     analyzer_exists,
        "detail": analyzer_path_str,
        "note":   "OK" if analyzer_exists else "Path configurado mas não encontrado no disco",
    })

    # Check 3: run_ast_analysis.py existe no workspace
    run_ast_py = (WORKSPACE / "src" / "modules" / "ava-fabric-agents"
                  / "asis-diagnostic" / "utils" / "run_ast_analysis.py")
    checks.append({
        "label":  "run_ast_analysis.py",
        "ok":     run_ast_py.exists(),
        "detail": str(run_ast_py.relative_to(WORKSPACE)),
        "note":   "OK" if run_ast_py.exists() else "Script não encontrado no workspace",
    })

    # Check 4: repository_path existe (necessário para o analyzer varrer o código)
    repo_path_str = (cfg.get("repository_path") or "").strip()
    repo_exists   = Path(repo_path_str).exists() if repo_path_str else False
    checks.append({
        "label":  "repository_path",
        "ok":     bool(repo_path_str) and repo_exists,
        "detail": repo_path_str or "(não configurado)",
        "note":   ("OK" if repo_exists else
                   "Diretório não encontrado no disco" if repo_path_str else
                   "Campo ausente — o analyzer precisa do repositório legado"),
    })

    # Info: cache hit
    lang_key     = legacy_tech or "delphi"
    ast_manifest = (WORKSPACE / "projects" / project / "outputs" / "asis"
                    / "ast-raw" / lang_key / "compressed" / "manifest.json")
    if ast_manifest.exists():
        warnings.append(
            f"Cache encontrado: {ast_manifest.relative_to(WORKSPACE)} — "
            f"F0 pulará re-extração (manifest já existe)."
        )

    ready = all(c["ok"] for c in checks)
    return {"ready": ready, "skip_ast": False, "checks": checks, "warnings": warnings}


def print_ast_validation(project: str, result: dict):
    """Exibe o relatório de validação de pré-requisitos AST.
    Se skip_ast=True (campo vazio), não exibe nada — comportamento silencioso.
    """
    if result.get("skip_ast"):
        # Campo não configurado: apenas registra em DIM, sem banner
        print(f"  {DIM}[F0/AST] Não configurado — será pulado silenciosamente.{RESET}")
        return

    status = f"{GREEN}✅ PRONTO{RESET}" if result["ready"] else f"{RED}❌ BLOQUEADO{RESET}"
    print(f"\n{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}  🔬 Pré-requisitos F0/AST — {project}  [{status}{BOLD}]{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")
    for c in result["checks"]:
        icon = f"{GREEN}✅{RESET}" if c["ok"] else f"{RED}❌{RESET}"
        note = f"  {DIM}({c['note']}){RESET}" if c["note"] != "OK" else ""
        print(f"  {icon}  {c['label']:<35}  {DIM}{c['detail'][:50]}{RESET}{note}")
    for w in result["warnings"]:
        print(f"\n  {YELLOW}⚠️  {w}{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")


# ── Grupos de fases para seleção interativa ──────────────────────────────────
PHASE_GROUPS: dict[str, dict] = {
    "F0": {"label": "F0  — AST Extraction (run_ast_analysis.py — pré-requisito)","phases": ["F0"]},
    "F1": {"label": "F1  — AS-IS Diagnostic (Orchestrator)",               "phases": ["F1"]},
    "F1S": {"label": "F1S — AS-IS Specialized Agents (Inventory→Gaps)",    "phases": ["F1a","F1b","F1c","F1d","F1e","F1f"]},
    "F2": {"label": "F2  — TO-BE Architecture",                            "phases": ["F2a","F2b","F2c","F2d"]},
    "F3": {"label": "F3  — Prototype",                                     "phases": ["F3"]},
    "F3S":{"label": "F3S — SpecKit (constitution → specs → plans → tasks)","phases": ["F3S"]},
    "F4S":{"label": "F4S — Scaffold determinístico (frontend → backend → baseline → aprovação)", "phases": ["F4S"]},
    "F4": {"label": "F4  — Tech Stack Generation (exige aprovação da F4S)",  "phases": ["F4"]},
    "F5": {"label": "F5  — DevOps Execute",                                "phases": ["F5"]},
    "F6": {"label": "F6  — QA Execution",                                  "phases": ["F6"]},
    "SU": {"label": "SU  — Summary (generate + fix + validate + final)",   "phases": ["S1","S2","S3","S4"]},
    "FC": {"label": "FC  — Containerize (Dockerfiles + docker-compose — pré-requisito do Podman)", "phases": ["FC"]},
    "FP": {"label": "FP  — Podman Run (execução local da solução containerizada — depende de FC)", "phases": ["FP"]},
}


def _sincronizar_grupos_expandidos() -> None:
    """Reconcilia os grupos com as fases realmente presentes no PIPELINE.

    Fases expandidas pelo fan-out por DAG viram `F3S:constitution`,
    `F3S:001-w0-foundation`, … Sem esta reconciliação o menu ofereceria o grupo
    `F3S` apontando para uma fase `F3S` que não existe mais, e a seleção não
    despacharia nada — falha silenciosa, que é o modo de falha que esta entrega
    inteira existe para eliminar.
    """
    for grupo, dados in PHASE_GROUPS.items():
        expandidas = [s["phase"] for s in PIPELINE
                      if s["phase"].split(":")[0] in dados["phases"]]
        if expandidas and expandidas != dados["phases"]:
            dados["phases"] = expandidas


_sincronizar_grupos_expandidos()
# ────────────────────────────────────────────────────────────────────────────


def _dur(seg: float) -> str:
    """Duração legível: segundos abaixo de 1min, minutos acima."""
    return f"{seg:.0f}s" if seg < 60 else f"{seg / 60:.1f}m"


def _esc(valor) -> str:
    """Escapa texto de métrica antes de entrar no HTML do dashboard.

    `detail` carrega mensagem de exceção (`f"{type(e).__name__}: {e}"`), e
    `contract_missing`/`artifacts_written` carregam caminhos. Sem escape, um
    `<` numa mensagem de erro quebra a tabela inteira.
    """
    return _html.escape(str(valor), quote=True)


def _num(valor) -> str:
    """Inteiro com separador de milhar, tolerante a métrica ausente/inválida."""
    try:
        return f"{int(valor):,}"
    except (TypeError, ValueError):
        return "0"


# ── Heartbeat do dashboard ───────────────────────────────────────────────────
# O HTML pede recarga ao navegador a cada 3s, mas quem escreve o arquivo é o
# runner — e ele só escrevia entre passos. Durante um passo de planning (~10min)
# o navegador relia o mesmo byte a byte, e o dashboard parecia congelado em
# "Executando…". Este contexto permite reescrever o arquivo DURANTE o streaming.
_RUN_CTX: dict = {}
# Contrato de saída do passo EM VOO — `{"phase", "paths"}`, escrito por
# `run_step` e lido pelo heartbeat. Separado do `_RUN_CTX` de propósito: ele
# tem ciclo de vida por PASSO, não por execução, e o `_RUN_CTX` é o sinal de
# "esta execução tem dashboard".
_CONTRATO_EM_VOO: dict = {}
_HEARTBEAT_MIN_INTERVAL_S = 3.0
_last_heartbeat = 0.0


def status_heartbeat(phase: str, ts_start: "datetime.datetime | None" = None,
                     chars: "int | str" = 0, force: bool = False) -> None:
    """Reescreve o dashboard com o andamento do passo em voo.

    Estrangulado em `_HEARTBEAT_MIN_INTERVAL_S` para acompanhar o auto-refresh do
    HTML sem gerar escrita por token. Nunca levanta: dashboard é observabilidade,
    jamais pode derrubar a execução (IV3).

    ``chars`` aceita o TEXTO acumulado do stream, e não só o seu tamanho. É o
    que permite contar quantos blocos `FILE:` já fecharam e desenhar a barra
    de entrega real (3/7 · 42%) em vez da faixa deslizante indeterminada: os
    artefatos só chegam ao disco no fim do passo, então durante os ~10 min de
    execução o texto recebido é a única evidência de progresso que existe.
    O int continua aceito para os chamadores que só têm o contador.
    """
    global _last_heartbeat
    if not _RUN_CTX:
        return
    agora = time.time()
    if not force and (agora - _last_heartbeat) < _HEARTBEAT_MIN_INTERVAL_S:
        return
    _last_heartbeat = agora
    decorrido = ((datetime.datetime.now() - ts_start).total_seconds()
                 if ts_start else 0.0)
    # A varredura por regex roda no máximo uma vez a cada 3s (a vazão é
    # estrangulada acima), nunca por token.
    resposta  = chars if isinstance(chars, str) else ""
    n_chars   = len(resposta) if resposta else int(chars or 0)
    # A checagem de fase impede que o contrato do passo anterior pinte a barra
    # de um passo TOOL, que não tem contrato nenhum.
    esperados = (list(_CONTRATO_EM_VOO.get("paths") or [])
                 if _CONTRATO_EM_VOO.get("phase") == phase else [])
    art_ok, art_total = progresso_contrato(
        artefatos_concluidos_no_stream(resposta), esperados)
    try:
        _write_status_html(
            _RUN_CTX["project"], _RUN_CTX["steps"], _RUN_CTX["executed"],
            _RUN_CTX["skipped"], _RUN_CTX["aborted"],
            current_phase=phase, start_ts=_RUN_CTX.get("start_ts", 0.0),
            exec_metrics=_RUN_CTX.get("metrics"),
            val_failed=_RUN_CTX.get("val_failed"),
            live={"phase": phase, "elapsed_s": decorrido, "chars": n_chars,
                  "art_ok": art_ok, "art_total": art_total})
    except Exception:  # noqa: BLE001
        pass


def _sub_row(project: str, m: dict, live: "dict | None" = None) -> str:
    """Monta a sub-linha de métricas detalhadas de uma fase do dashboard.

    Existe porque `run_step` devolve 15 métricas e a tabela principal só tem
    espaço para as de acompanhamento. O resto — custo, saúde do contexto e
    integridade da saída — vivia apenas no `execution-report_*.md`, gerado no
    FIM da esteira: quem acompanhava ao vivo não via truncamento por
    `max_tokens` nem consumo de janela.

    Sub-linha fixa, sem JavaScript: o `<meta refresh>` de 3s zeraria qualquer
    estado de interação. O único `<details>` é o dos artefatos gravados, que só
    tem conteúdo depois que a fase termina.

    Devolve string vazia para fase pendente (sem métricas), para não dobrar a
    altura da tabela com linhas em branco.
    """
    if live:
        _ch = int(live.get("chars") or 0)
        _at = int(live.get("art_total") or 0)
        _bd_live = ['<span class="bd">em voo</span>']
        if _at:
            _bd_live.append(
                f'<span class="bd">{int(live.get("art_ok") or 0)}/{_at} '
                f'artefatos do contrato concluídos</span>')
        _bd_live.append(
            f'<span class="bd">saída acumulada ~{_num(_ch // 4)} tok '
            f'(estimada de chars//4)</span>' if _ch else
            '<span class="bd">aguardando 1º token</span>')
        return "".join(_bd_live)
    if not m:
        return ""

    bd: list[str] = []

    def _add(txt: str, cor: str = "") -> None:
        estilo = f' style="color:{cor}"' if cor else ""
        bd.append(f'<span class="bd"{estilo}>{txt}</span>')

    if m.get("skill_kb"):
        _add(f'skill {_esc(m["skill_kb"])}KB')

    _ctx = float(m.get("ctx_pct") or 0)
    if _ctx:
        # Janela apertada é o que antecede o corte por max_tokens — precisa
        # gritar antes de virar artefato truncado, não depois.
        _cor = "#ef4444" if _ctx > 85 else ("#eab308" if _ctx > 70 else "")
        _add(f'janela {_ctx:.1f}%', _cor)

    if m.get("out_max"):
        _add(f'out máx {_num(m["out_max"])}')

    _stop = str(m.get("stop_reason") or "")
    if _stop:
        _trunc = _stop == "max_tokens"
        _add(f'stop {_esc(_stop)}' + (' ⚠' if _trunc else ''),
             "#ef4444" if _trunc else "")

    if "headroom_used" in m:
        _add('headroom ' + ('✅' if m.get("headroom_used") else '—'))

    _inc = list(m.get("incomplete") or [])
    if _inc:
        _add(f'{len(_inc)} incompleto(s): '
             + _esc(", ".join(str(i) for i in _inc[:4]))
             + ('…' if len(_inc) > 4 else ''), "#ef4444")

    _falta = list(m.get("contract_missing") or [])
    if _falta:
        _add('falta: ' + _esc(", ".join(str(f) for f in _falta[:4]))
             + ('…' if len(_falta) > 4 else ''), "#ef4444")

    _arts = list(m.get("artifacts_written") or [])
    if _arts:
        # Caminhos vêm absolutos-ao-repo e com separador do Windows; o prefixo
        # do projeto se repete em todas as 64 linhas e não informa nada.
        _pref = f"projects{os.sep}{project}{os.sep}"
        _itens = "".join(
            f'<li>{_esc(str(a).replace(_pref, "").replace(chr(92), "/"))}</li>'
            for a in _arts)
        bd.append(f'<details><summary>{len(_arts)} artefatos</summary>'
                  f'<ol class="arts">{_itens}</ol></details>')

    linhas = [" ".join(bd)] if bd else []
    if m.get("detail"):
        # `detail` nem sempre é reprovação: "aviso determinístico aceito
        # (exit 1)" saía com ❌ vermelho, contradizendo o próprio texto e o
        # status OK da linha. O ícone agora segue o veredito, não a existência
        # do campo.
        if m.get("non_blocking") or _is_speckit_nonblocking(m.get("phase", ""),
                                                            m.get("agent", "")):
            icone, cor = "ℹ️", "#38bdf8"
        elif m.get("val_ok", False) or m.get("risk_accepted"):
            icone, cor = "⚠️", "#eab308"
        else:
            icone, cor = "❌", "#ef4444"
        linhas.append(f'<div class="ln" style="color:{cor}">{icone} '
                      f'{_esc(m["detail"])}</div>')
    if m.get("fix"):
        linhas.append(f'<div class="ln" style="color:#eab308">🔧 '
                      f'{_esc(m["fix"])}</div>')
    return "".join(linhas)


# ── Ledger do dashboard: histórico acumulativo entre execuções ────────────────
# O dashboard era desenhado só a partir do run EM CURSO (`steps`, `executed`,
# `skipped`, `aborted`). Numa retomada — ou numa execução a partir de uma fase
# específica — `steps` traz apenas as fases selecionadas e as listas de veredicto
# chegam VAZIAS na largada (`_write_status_html(project, active_steps, [], [], [])`).
# Resultado: o HTML era regravado do zero e o histórico das fases já rodadas
# desaparecia da tela; sobrava só a etapa em execução.
#
# O ledger abaixo guarda em disco o estado de CADA fase já vista pelo projeto.
# Toda gravação do dashboard: (1) carrega o estado existente, (2) aplica apenas
# as mudanças do run atual, (3) renderiza a esteira COMPLETA. Nenhuma fase já
# registrada some da visualização.
_STATUS_LEDGER_FILE = "pipeline-status-state.json"
_STATUS_LEDGER_VERSION = 1

# Estados que já são veredicto. Uma fase nesses estados NÃO volta a "pendente"
# só porque o run atual ainda não a tocou — era exatamente esse rebaixamento que
# apagava o histórico na largada de cada retomada.
_STATUS_TERMINAIS = frozenset(
    {"done", "warn", "skipped", "aborted", "val_fail", "interrupted"})

# cor do texto, cor de fundo da linha
_ST = {
    "done":        ("#22c55e", "#071a07"), "warn":     ("#eab308", "#1a1500"),
    "skipped":     ("#475569", "#0a0a0a"), "aborted":  ("#ef4444", "#1a0505"),
    "running":     ("#ff6900", "#1a0d00"), "pending":  ("#334155", "#0a0a16"),
    "val_fail":    ("#ef4444", "#1a0505"), "interrupted": ("#a78bfa", "#120a1a"),
}
_STATUS_ROTULO = {
    "done":     ("✅", "OK"),           "warn":     ("⚠️", "Aviso"),
    "skipped":  ("⏭",  "Pulado"),      "aborted":  ("🛑", "Abortado"),
    "running":  ("▶",  "Executando…"),  "pending":  ("○",  "—"),
    "val_fail": ("❌", "Val-Fail"),
    # Fase que ficou "Executando…" num run que morreu antes de dar veredicto.
    # Volta a Pendente assim que for reexecutada; até lá fica registrada, em vez
    # de sumir da tela ou mentir que terminou.
    "interrupted": ("⏸", "Interrompido"),
}


def _status_ledger_path(project: str) -> Path:
    """Path do ledger visual do projeto (irmão do runner-state.json)."""
    return (WORKSPACE / "projects" / project / "outputs" / "pipeline_runner"
            / _STATUS_LEDGER_FILE)


def _status_ledger_vazio(project: str) -> dict:
    return {"version": _STATUS_LEDGER_VERSION, "project": project,
            "order": [], "steps": {}}


def _load_status_ledger(project: str) -> dict:
    """Lê o ledger do disco. Nunca levanta: dashboard é observabilidade (IV3).

    Ledger corrompido/parcial cai para vazio — o run atual volta a preenchê-lo.
    """
    path = _status_ledger_path(project)
    if not path.exists():
        return _status_ledger_vazio(project)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return _status_ledger_vazio(project)
    if not isinstance(data, dict) or data.get("project") != project:
        return _status_ledger_vazio(project)
    steps = data.get("steps")
    if not isinstance(steps, dict):
        return _status_ledger_vazio(project)
    # `order` e `steps` podem divergir se uma gravação foi interrompida no meio;
    # a reconciliação abaixo garante que toda fase registrada seja renderizada.
    order = [str(p) for p in (data.get("order") or []) if p in steps]
    for ph in steps:
        if ph not in order:
            order.append(ph)
    return {"version": _STATUS_LEDGER_VERSION, "project": project,
            "order": order, "steps": steps}


def _save_status_ledger(project: str, ledger: dict) -> None:
    """Grava o ledger. Falha de escrita não derruba a esteira."""
    path = _status_ledger_path(project)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _merge_status_order(anterior: "list[str]", atual: "list[str]") -> "list[str]":
    """Funde a ordem já registrada com a ordem da esteira ativa.

    Fase conhecida mantém a posição que já tinha (o histórico não se reordena);
    fase nova entra logo depois da sua antecessora no run atual — que é onde a
    expansão do F3S/F4S coloca as sub-fases descobertas em tempo de execução.
    """
    ordem = list(anterior)
    pos = len(ordem)
    for ph in atual:
        if ph in ordem:
            pos = ordem.index(ph) + 1
        else:
            ordem.insert(pos, ph)
            pos += 1
    return ordem


def _classificar_status(ph: str, m: dict, executed: list, skipped: list,
                        aborted: list, val_failed: list,
                        current_phase: str) -> str:
    """Veredicto visual de UMA fase a partir das listas do run atual."""
    if ph in aborted:
        return "aborted"
    if ph in val_failed:
        return "val_fail"
    if ph in skipped:
        # Reprovação aceita pelo operador não é o mesmo que passo pulado: houve
        # verificação, ela falhou, e alguém assumiu o risco. Mostrar como
        # "Pulado" apagaria justamente o que precisa ficar visível.
        return "warn" if m.get("risk_accepted") else "skipped"
    if ph in executed:
        return "done" if m.get("val_ok", True) else "warn"
    if ph == current_phase:
        return "running"
    return "pending"


def _atualizar_status_ledger(project: str, steps: list, executed: list,
                             skipped: list, aborted: list, val_failed: list,
                             current_phase: str, metrics: dict,
                             reset: bool = False) -> dict:
    """Carrega o estado existente e aplica SOMENTE as mudanças do run atual.

    ``reset=True`` começa um ledger novo — reservado à execução completa a partir
    do zero, a única em que o histórico anterior não descreve mais a esteira em
    curso. Retomada e execução por fase sempre acumulam.
    """
    ledger = _status_ledger_vazio(project) if reset else _load_status_ledger(project)
    entradas = ledger["steps"]
    agora = datetime.datetime.now().isoformat(timespec="seconds")

    # Um "Executando…" herdado de um run que morreu não é o passo atual DESTE
    # run. Roda antes da classificação de propósito: se a fase concluiu agora, a
    # classificação abaixo sobrescreve com o veredicto real.
    for ph, ent in entradas.items():
        if ent.get("status") == "running" and ph != current_phase:
            ent["status"] = "interrupted"

    for step in steps:
        ph = _phase_identity(step)
        m = metrics.get(ph) or {}
        novo = _classificar_status(ph, m, executed, skipped, aborted,
                                   val_failed, current_phase)
        ent = entradas.get(ph)
        anterior = str(ent.get("status")) if ent else "pending"

        # A largada da esteira chama o dashboard com as listas de veredicto
        # vazias — sem esta guarda TODO o histórico voltaria para "○ —" a cada
        # retomada. A fase só sai de um estado terminal quando volta a rodar
        # (vira "running") ou quando recebe veredicto novo.
        if novo == "pending" and anterior in _STATUS_TERMINAIS:
            continue

        if ent is None:
            ent = {"phase": ph, "first_seen": agora}
            entradas[ph] = ent
        # Reexecução: zera as métricas do run passado ao entrar em execução,
        # para a linha não misturar artefatos velhos com o passo em voo.
        if novo == "running" and anterior != "running":
            ent["metrics"] = {}
        ent["agent"] = str(step.get("agent") or ent.get("agent") or "")
        ent["status"] = novo
        ent["executed"] = ph in executed
        ent["updated_at"] = agora
        if m:
            ent["metrics"] = _serialize_metrics(m)

    ledger["order"] = _merge_status_order(
        ledger["order"], [_phase_identity(s) for s in steps])
    # Fase que só existe no ledger (rodou num run anterior, fora da seleção
    # atual) permanece na ordem e é renderizada com o estado que tinha.
    for ph in entradas:
        if ph not in ledger["order"]:
            ledger["order"].append(ph)
    _save_status_ledger(project, ledger)
    return ledger


# ── Atualização incremental do HTML ──────────────────────────────────────────
# O documento é gravado com marcadores em volta de cada bloco que muda
# (meta-refresh, cabeçalho, uma linha por fase, rodapé). Numa atualização, só o
# CONTEÚDO dos blocos que de fato mudaram é trocado no arquivo existente: a
# estrutura da página, o CSS e as linhas das fases inalteradas não são
# reconstruídos. Quando nada muda, o arquivo nem chega a ser reescrito.
_MARCA_RE = re.compile(r"<!--AVA:([^>]+?)-->(.*?)<!--/AVA:\1-->", re.S)


def _bloco(chave: str, conteudo: str) -> str:
    return f"<!--AVA:{chave}-->{conteudo}<!--/AVA:{chave}-->"


def _chaves_marcadas(texto: str) -> "list[str]":
    return [m.group(1) for m in _MARCA_RE.finditer(texto)]


def _aplicar_fragmentos(texto: str, novos: "dict[str, str]") -> str:
    """Troca in-place o conteúdo dos blocos marcados que mudaram."""
    def _sub(m) -> str:
        chave, atual = m.group(1), m.group(2)
        if chave in novos and novos[chave] != atual:
            return _bloco(chave, novos[chave])
        return m.group(0)
    return _MARCA_RE.sub(_sub, texto)


def _write_status_html(project: str, steps: list, executed: list, skipped: list,
                        aborted: list, current_phase: str = "",
                        start_ts: float = 0.0,
                        exec_metrics: "dict | None" = None,
                        done: bool = False,
                        live: "dict | None" = None,
                        val_failed: "list | None" = None,
                        reset: bool = False) -> "Path":
    """Opção 2: gera pipeline-status.html com auto-refresh para o Simple Browser do VS Code.

    O dashboard é ACUMULATIVO: o estado de cada fase vive em
    ``pipeline-status-state.json`` e é carregado antes de qualquer gravação, de
    modo que retomada e execução por fase preservam tudo o que já rodou. Só os
    blocos alterados são reescritos no HTML (ver ``_aplicar_fragmentos``).

    ``live`` traz o andamento do passo EM EXECUÇÃO — ``{"phase", "elapsed_s",
    "chars"}`` — alimentado pelo heartbeat durante o streaming. Sem ele o
    arquivo só era reescrito entre passos: o navegador recarregava a cada 3s,
    mas relia conteúdo idêntico durante os ~10min de um passo de planning, o que
    fazia o dashboard parecer travado.

    ``reset`` descarta o histórico e começa um ledger novo — só para execução
    completa a partir do zero.
    """
    out_dir = WORKSPACE / "projects" / project / "outputs" / "pipeline_runner"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "pipeline-status.html"

    metrics = exec_metrics or {}
    live = live or {}
    # Quando val_failed não é passado (chamadas intermediárias/heartbeat), deriva
    # do exec_metrics: fases com val_ok=False sem risk_accepted são val_fail.
    # NOTA: mais abaixo havia `_vf = val_failed or []`, que descartava esta
    # derivação. Como heartbeat e chamadas intermediárias não passam
    # `val_failed`, a fase reprovada aparecia como "⚠️ Aviso" durante toda a
    # execução e só virava "❌ Val-Fail" na escrita final.
    _vf = val_failed
    if _vf is None:
        _vf = [ph for ph, m in metrics.items()
               if m.get("val_ok") is False and not m.get("risk_accepted")
               and ph not in (aborted or [])]
    _vf = _vf or []
    if live.get("phase") and not current_phase:
        current_phase = str(live["phase"])

    # ── 1) Carrega o histórico e aplica só o delta do run atual ──────────
    ledger = _atualizar_status_ledger(
        project, steps, executed or [], skipped or [], aborted or [], _vf,
        current_phase, metrics, reset=reset)
    entradas = ledger["steps"]
    ordem = ledger["order"]

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    elapsed_s = time.time() - start_ts if start_ts else 0
    elapsed_str = _dur(elapsed_s)
    # Denominadores vêm do ledger, não da seleção do run: numa retomada de 3
    # fases sobre uma esteira de 12 a contagem crua imprimia "12/3 fases · 400%",
    # e o 400% ia direto para a largura da barra, vazando o container.
    total      = len(ordem)
    done_count = sum(1 for ph in ordem
                     if entradas[ph].get("status") in ("done", "warn", "val_fail"))
    skip_count = sum(1 for ph in ordem
                     if entradas[ph].get("status") == "skipped")
    pct = min(100, int(done_count / total * 100)) if total else 0
    status_title = ("✅ Concluído" if done else
                    (f"▶ {current_phase}" if current_phase else "⏳ Aguardando..."))
    if not done and live.get("phase"):
        _lt = _dur(float(live.get("elapsed_s") or 0))
        _lk = int(live.get("chars") or 0) // 4
        status_title += f" · {_lt}" + (f" · ~{_lk:,} tok" if _lk else " · aguardando 1º token")
    refresh_tag = "" if done else '<meta http-equiv="refresh" content="3">'

    # ── 2) Uma linha por fase do LEDGER — histórico completo, não só o run ──
    frag: "dict[str, str]" = {}
    tot_in = tot_out = 0   # acumuladores do rodapé de consumo de tokens
    for ph in ordem:
        ent = entradas[ph]
        ag = str(ent.get("agent") or "").replace("ava-", "")
        m  = ent.get("metrics") or {}
        st = str(ent.get("status") or "pending")
        _foi_executada = bool(ent.get("executed"))
        ic, lb = _STATUS_ROTULO.get(st, _STATUS_ROTULO["pending"])
        fg, bg = _ST.get(st, _ST["pending"])
        _em_voo = (st == "running" and live.get("phase") == ph)
        ep = m.get("elapsed_s", 0)
        ts = (_dur(ep)) if _foi_executada else "—"
        ar = str(m.get("artifacts", 0)) if _foi_executada else "—"

        # ── Tokens: entrada, saída e total ───────────────────────────────
        # `inp_tokens`/`resp_tokens` são os valores REAIS da API
        # (usage.input_tokens / usage.output_tokens), não estimativas.
        _in  = int(m.get("inp_tokens") or 0)
        _out = int(m.get("resp_tokens") or 0)
        if _foi_executada and (_in or _out):
            c_in, c_out, c_tot = _num(_in), _num(_out), _num(_in + _out)
            tot_in += _in
            tot_out += _out
        else:
            c_in = c_out = c_tot = "—"

        # ── Progresso de entrega: artefatos do contrato realmente gravados ──
        # Denominador = contrato da fase + `outputs` declarados no DAG. Passo
        # sem contrato (tool, F0, fase F3S expandida) não vira 0% nem 100%:
        # vira "sem contrato", que é a verdade.
        _c_ok  = int(m.get("contract_ok") or 0)
        _c_tot = int(m.get("contract_total") or 0)
        if _em_voo:
            # Progresso REAL do passo em voo: blocos FILE já fechados no
            # stream contra o contrato de saída do agente. A faixa deslizante
            # indeterminada fica só para quem não tem contrato conhecido —
            # ali o progresso é mesmo desconhecido, e fingir uma fração seria
            # pior do que não mostrar nenhuma.
            _lo = int(live.get("art_ok") or 0)
            _lt = int(live.get("art_total") or 0)
            if _lt > 0:
                _lp = int(_lo / _lt * 100)
                prog = (f'<div class="pbar"><div class="pfx" '
                        f'style="width:{min(100, _lp)}%;background:#ff6900"></div></div>'
                        f'<div class="plab" style="color:#ff6900">'
                        f'{_lo}/{_lt} · {_lp}% · em execução…</div>')
            else:
                prog = ('<div class="pbar"><div class="pind"></div></div>'
                        '<div class="plab">em execução…</div>')
        elif _c_tot > 0:
            _p = int(_c_ok / _c_tot * 100)
            _pc = "#22c55e" if _p >= 100 else ("#eab308" if _p >= 50 else "#ef4444")
            prog = (f'<div class="pbar"><div class="pfx" '
                    f'style="width:{min(100, _p)}%;background:{_pc}"></div></div>'
                    f'<div class="plab" style="color:{_pc}">{_c_ok}/{_c_tot} · {_p}%</div>')
        elif _foi_executada:
            prog = ('<div class="pbar pnone"></div>'
                    f'<div class="plab">sem contrato · {_esc(m.get("artifacts", 0))} arq</div>')
        else:
            prog = '<div class="pbar"></div><div class="plab">—</div>'

        if _em_voo:
            # Passo em voo: tempo decorrido e saída acumulada, atualizados pelo heartbeat.
            ts = _dur(float(live.get("elapsed_s") or 0))
            _chars = int(live.get("chars") or 0)
            c_out = f"~{_num(_chars // 4)}" if _chars else "…"
            c_in = c_tot = "…"
            _lt_ar = int(live.get("art_total") or 0)
            ar = (f'{int(live.get("art_ok") or 0)}/{_lt_ar}' if _lt_ar else "…")

        # Ícone: na linha em execução, robô animado + reticências em cascata,
        # para que se veja de relance QUAL agente está trabalhando agora.
        if st == "running":
            cel_ic = ('<span class="bot">🤖</span><br>'
                      '<span class="dots"><i></i><i></i><i></i></span>')
            cls_tr = ' class="run"'
        else:
            cel_ic = ic
            cls_tr = ""

        linha = (
            f'<tr id="ph-{_esc(ph)}" style="background:{bg}"{cls_tr}>'
            f'<td style="color:{fg};text-align:center;padding:5px 8px">{cel_ic}</td>'
            f'<td style="padding:5px 8px"><span style="color:#475569;font-size:.7em">{_esc(ph)}</span>'
            f'<br><b style="color:#cbd5e1;font-size:.82em">{_esc(ag)}</b></td>'
            f'<td style="color:{fg};padding:5px 8px;font-size:.8em">{lb}</td>'
            f'<td style="color:#475569;padding:5px 8px;font-size:.8em">{ts}</td>'
            f'<td style="color:#475569;padding:5px 8px;font-size:.8em">{ar}</td>'
            f'<td style="padding:5px 8px;min-width:130px">{prog}</td>'
            f'<td class="tk">{c_in}</td>'
            f'<td class="tk">{c_out}</td>'
            f'<td class="tk" style="color:#94a3b8">{c_tot}</td></tr>\n'
        )

        sub = _sub_row(project, m, live if _em_voo else None)
        if sub:
            linha += (f'<tr style="background:{bg}"><td></td>'
                      f'<td colspan="8" class="sub">{sub}</td></tr>\n')
        frag[f"ROW:{ph}"] = linha

    frag["REFRESH"] = refresh_tag
    frag["HEAD"] = (
        '<div class="meta">'
        f'<span class="badge">📁 {_esc(project)}</span>'
        f'<span class="badge">🧠 {_esc(DEPLOYMENT)}</span>'
        f'<span class="badge" style="color:#fb923c">{_esc(status_title)}</span>'
        f'<span style="float:right">{now_str} · {elapsed_str}</span>'
        '</div>\n'
        f'<div class="prog"><div class="pfill" style="width:{pct}%"></div></div>\n'
        f'<div class="lbl">{done_count}/{total} fases · {skip_count} puladas · {pct}%</div>'
    )
    frag["FOOT"] = (
        '<tr>'
        '<td colspan="6" style="text-align:right">TOTAL consumido</td>'
        f'<td class="tk">{_num(tot_in)}</td>'
        f'<td class="tk">{_num(tot_out)}</td>'
        f'<td class="tk" style="color:#cbd5e1">{_num(tot_in + tot_out)}</td>'
        '</tr>'
    )
    frag["AUTOREFRESH"] = "off" if done else "3s"

    # ── 3) Atualização incremental sobre o arquivo já existente ──────────
    # Se o HTML em disco tem a mesma esteira (mesmas fases, mesma ordem), só o
    # conteúdo dos blocos alterados é trocado — a estrutura da página não é
    # reconstruída. Reconstrução completa fica para o 1º write do projeto, para
    # arquivo de versão antiga (sem marcadores) e para quando a esteira ganha
    # fases novas (expansão F3S/F4S).
    anterior_html = ""
    if html_path.exists():
        try:
            anterior_html = html_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            anterior_html = ""
    if anterior_html:
        chaves = _chaves_marcadas(anterior_html)
        rows_em_disco = [k[4:] for k in chaves if k.startswith("ROW:")]
        if rows_em_disco == ordem and "HEAD" in chaves and "FOOT" in chaves:
            patched = _aplicar_fragmentos(anterior_html, frag)
            if patched == anterior_html:
                return html_path   # nada mudou: não há por que reescrever
            html_path.write_text(patched, encoding="utf-8")
            return html_path

    rows = "".join(_bloco(f"ROW:{ph}", frag[f"ROW:{ph}"]) for ph in ordem)
    html = (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n'
        '<meta charset="utf-8">\n'
        f'{_bloco("REFRESH", frag["REFRESH"])}\n'
        f'<title>AVA Fabric — {_esc(project)}</title>\n'
        '<style>\n'
        '*{box-sizing:border-box;margin:0;padding:0}\n'
        'body{background:#070711;color:#e2e8f0;font-family:"Segoe UI",system-ui,sans-serif;'
        'padding:20px;min-width:880px}\n'
        'h1{color:#ff6900;font-size:1.25em;margin-bottom:8px}\n'
        '.meta{color:#475569;font-size:.8em;margin-bottom:10px}\n'
        '.badge{display:inline-block;background:#1e293b;border-radius:3px;'
        'padding:2px 7px;margin-right:5px;font-size:.75em}\n'
        '.prog{background:#1e293b;border-radius:5px;height:5px;margin:8px 0 3px}\n'
        # A largura da barra é atributo da <div>, não do CSS: assim a folha de
        # estilo fica estática e o avanço do run cabe no bloco HEAD, trocado só.
        '.pfill{background:linear-gradient(90deg,#ff6900,#f59e0b);height:100%;'
        'border-radius:5px}\n'
        '.lbl{color:#475569;font-size:.72em;margin-bottom:12px}\n'
        # Só a tabela rola: cabeçalho e badges ficam parados.
        '.wrap{overflow-x:auto}\n'
        'table{width:100%;border-collapse:collapse}\n'
        'th{color:#334155;font-size:.68em;text-transform:uppercase;letter-spacing:.04em;'
        'padding:5px 8px;border-bottom:1px solid #1e293b;text-align:left}\n'
        'th.r,td.tk{text-align:right}\n'
        'td.tk{color:#475569;padding:5px 8px;font-size:.8em;'
        'font-variant-numeric:tabular-nums;white-space:nowrap}\n'
        # ── Barra de progresso de entrega, uma por agente ────────────────
        '.pbar{background:#1e293b;border-radius:4px;height:6px;overflow:hidden;'
        'position:relative}\n'
        '.pfx{height:100%;border-radius:4px}\n'
        # Passo sem contrato de artefatos: hachura, não 0% nem 100%.
        '.pnone{background:repeating-linear-gradient(45deg,#1e293b,#1e293b 4px,'
        '#141c2b 4px,#141c2b 8px)}\n'
        # Passo em voo: faixa deslizante — progresso indeterminado, honesto.
        '.pind{position:absolute;top:0;height:100%;width:40%;border-radius:4px;'
        'background:linear-gradient(90deg,transparent,#ff6900,transparent);'
        'animation:slide 1.4s linear infinite}\n'
        '@keyframes slide{0%{left:-40%}100%{left:100%}}\n'
        '.plab{color:#475569;font-size:.68em;margin-top:3px;'
        'font-variant-numeric:tabular-nums}\n'
        # ── Sub-linha de métricas detalhadas ─────────────────────────────
        '.sub{padding:2px 8px 7px;font-size:.68em;color:#475569;'
        'border-bottom:1px solid #0f172a}\n'
        '.bd{display:inline-block;background:#0f172a;border-radius:3px;'
        'padding:1px 6px;margin:0 4px 2px 0}\n'
        '.ln{margin-top:3px;line-height:1.4}\n'
        '.sub details{display:inline-block;vertical-align:top}\n'
        '.sub summary{display:inline-block;background:#0f172a;border-radius:3px;'
        'padding:1px 6px;cursor:pointer;color:#64748b}\n'
        '.arts{margin:4px 0 2px 20px;color:#334155;max-height:220px;'
        'overflow-y:auto}\n'
        '.arts li{padding:1px 0}\n'
        # ── Agente trabalhando agora ─────────────────────────────────────
        # A opacidade pulsante ficava na <tr> inteira e atrapalhava a leitura
        # justamente dos números que estão mudando. Agora a animação vive no
        # ícone, e a linha é marcada por uma borda lateral que respira.
        '@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}\n'
        '@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}\n'
        '@keyframes glow{0%,100%{box-shadow:inset 3px 0 0 #ff6900}'
        '50%{box-shadow:inset 3px 0 0 #7c3a00}}\n'
        '.bot{display:inline-block;animation:bob .9s ease-in-out infinite;'
        'font-size:1.15em}\n'
        '.dots i{display:inline-block;width:3px;height:3px;border-radius:50%;'
        'background:#ff6900;margin:0 1px;animation:blink 1.2s infinite}\n'
        '.dots i:nth-child(2){animation-delay:.2s}\n'
        '.dots i:nth-child(3){animation-delay:.4s}\n'
        '.run td:first-child{animation:glow 1.4s ease-in-out infinite}\n'
        '@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}\n'
        '.pulse{animation:pulse 1.3s ease-in-out infinite}\n'
        'tfoot td{border-top:1px solid #1e293b;padding:6px 8px;font-size:.75em;'
        'color:#64748b}\n'
        '.foot{margin-top:14px;color:#1e293b;font-size:.7em;'
        'border-top:1px solid #1e293b;padding-top:8px}\n'
        'a{color:#334155}\n'
        '</style>\n</head>\n<body>\n'
        '<h1>🤖 AVA Fabric Pipeline</h1>\n'
        f'{_bloco("HEAD", frag["HEAD"])}\n'
        '<div class="wrap"><table><thead><tr>'
        '<th></th><th>Fase / Agente</th><th>Status</th>'
        '<th>Tempo</th><th>Artefatos</th><th>Progress</th>'
        '<th class="r">In tok</th><th class="r">Out tok</th><th class="r">Total</th>'
        '</tr></thead>\n<tbody>\n'
        f'{rows}'
        '</tbody>\n<tfoot>'
        f'{_bloco("FOOT", frag["FOOT"])}'
        '</tfoot></table></div>\n'
        '<div class="foot">AVA Fabric · auto-refresh: '
        f'{_bloco("AUTOREFRESH", frag["AUTOREFRESH"])} · <a href="">↺ agora</a></div>\n'
        '</body>\n</html>'
    )
    html_path.write_text(html, encoding="utf-8")
    return html_path


# ─── CLI: despacho de um agente avulso ───────────────────────────────────────
# O runner nasceu 100% interativo, e `safe_input` usa `msvcrt.getwch()`, que
# ignora stdin — nem por pipe dava para automatizar. Para reexecutar um único
# agente era preciso navegar o menu e responder "P" dezenas de vezes.
#
# Sem argumento algum, `_parse_cli` devolve tudo None/False e o caminho
# interativo segue idêntico. Nenhum .bat/.ps1 do repo invoca este script, então
# adicionar argparse não quebra wrapper que passe argumento solto.

def _parse_cli(argv: "list[str] | None" = None) -> "argparse.Namespace":
    """Flags opcionais. Sem argumentos, modo interativo de sempre."""
    parser = argparse.ArgumentParser(
        prog="ava-pipeline-runner-cli",
        description="executa a esteira AVA Fabric (interativo) ou um agente avulso",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            sem argumentos  ->  modo interativo (comportamento original)

            exemplos:
              python "ava-pipeline-runner-cli.py"
              python "ava-pipeline-runner-cli.py" --list-agents
              python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03
              python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03 --dry-run
              python "ava-pipeline-runner-cli.py" --agent ava-devops-orchestrator -p meu-erp-03 --phase F5

            exit codes: 0 ok | 1 etapa falhou | 2 erro de configuracao | 130 abortado
        """))
    parser.add_argument("--agent", metavar="ID",
                        help="roda so este agente (da esteira ou avulso do registry)")
    parser.add_argument("-p", "--project", metavar="NOME",
                        help="projeto em projects/ (obrigatorio com --agent)")
    parser.add_argument("--phase", metavar="ID",
                        help="etapa a executar (F4S); com --agent, desempata agente presente em mais de uma etapa")
    parser.add_argument("--trigger", metavar="T",
                        help="trigger do prompt; sem ele sai '@agente project: X'")
    parser.add_argument("--feature", metavar="F",
                        help="feature do SpecKit, para agente que roda por feature")
    parser.add_argument("--model", metavar="ID",
                        help="deployment do Foundry; sem ele usa o default")
    parser.add_argument("--headroom", action="store_true",
                        help="sobe o proxy headroom antes do despacho")
    parser.add_argument("--force-single", action="store_true",
                        help="despacha agente com fan-out como passo unico (nao recomendado)")
    parser.add_argument("--dry-run", action="store_true",
                        help="resolve o passo e mostra o prompt, sem gastar inferencia")
    parser.add_argument("--list-agents", action="store_true",
                        help="lista os agentes despachaveis e sai")
    parser.add_argument("--json", action="store_true",
                        help="emite o resultado do despacho em JSON")
    return parser.parse_args(argv)


def _agent_cli():
    """Importa o módulo de resolução, ou explica por que não dá para seguir."""
    sys.path.insert(0, str(WORKSPACE / "src" / "shared" / "tools"))
    import runner_agent_cli
    return runner_agent_cli


def _listar_agentes_cli(args) -> int:
    print(_agent_cli().listar_agentes(PIPELINE))
    return 0


def _despachar_agente_unico(args) -> int:
    """Executa UM agente, sem prompt algum. Exit 0/1/2/130.

    Não chama `main()` de propósito: enfiar nove condicionais numa função de
    750 linhas — a de maior densidade de defeito do arquivo — é o caminho para
    regredir o modo interativo. Aqui só o setup que `run_step` de fato exige.

    Deliberadamente FORA deste caminho: `_save_runner_state`,
    `_write_status_html`, `_finalize_runner_state` e `_write_remediation_report`.
    Todos são da esteira; gravar estado de um despacho avulso sobrescreveria o
    `runner-state.json` de um run real com uma esteira de um passo só.
    """
    global DEPLOYMENT, PROVIDER

    cli = _agent_cli()

    if not args.project:
        print(f"{RED}--agent exige -p/--project.{RESET}", file=sys.stderr)
        print(f'{DIM}  ex: python "ava-pipeline-runner-cli.py" --agent {args.agent} '
              f'-p meu-erp-03{RESET}', file=sys.stderr)
        return cli.EXIT_CONFIG

    projects = list_projects()
    if args.project not in projects:
        print(cli.explicar_projeto_inexistente(args.project, projects), file=sys.stderr)
        return cli.EXIT_CONFIG
    project = args.project

    # ── Resolução ────────────────────────────────────────────────
    try:
        passo = cli.resolver_passo(PIPELINE, project, args.agent, phase=args.phase,
                                   trigger=args.trigger, feature=args.feature)
    except cli.AgentCLIError as exc:
        print(exc.bloco, file=sys.stderr)
        return exc.exit_code

    problemas = cli.validar_passo(passo)
    if problemas:
        print(cli.explicar_passo_invalido(args.agent, problemas, project),
              file=sys.stderr)
        return cli.EXIT_CONFIG

    # ── Fan-out: recusa sem escopo ───────────────────────────────
    rotulo = cli.detectar_fanout(passo)
    if rotulo and not args.force_single:
        tem_escopo = bool(passo.get("feature") or passo.get("task_id"))
        if not tem_escopo:
            escopos = cli.escopos_disponiveis(project, rotulo, WORKSPACE)
            print(cli.explicar_fanout_avulso(passo, project, escopos, rotulo),
                  file=sys.stderr)
            return cli.EXIT_CONFIG

    # ── Modelo e provider ────────────────────────────────────────
    # O global PROVIDER só é corrigido dentro de `_select_model_interactive`.
    # Pulado o menu, `run_step` tomaria o ramo errado e mandaria payload
    # Anthropic para endpoint OpenAI. Resolver e imprimir sempre.
    if args.model:
        DEPLOYMENT = args.model
    PROVIDER = cli.resolver_provider(DEPLOYMENT)

    banner(f"Agente avulso: {args.agent}  |  projeto {project}", MAGENTA)
    print(f"  {DIM}fase ....... {passo.get('phase')}{RESET}")
    print(f"  {DIM}trigger .... {passo.get('trigger')}{RESET}")
    print(f"  {DIM}modelo ..... {DEPLOYMENT}  (provider={PROVIDER}){RESET}")
    print(f"  {DIM}skill ...... {passo.get('spec_path', '(heuristica)')}{RESET}")
    prompt = build_prompt(passo["agent"], passo.get("trigger"), project,
                          passo.get("feature"))
    print(f"  {DIM}prompt ..... {prompt}{RESET}")

    if passo.get("ad_hoc"):
        print(f"\n  {YELLOW}Agente avulso: sem manifesto de insumos declarado.{RESET}")
        print(f"  {DIM}O contexto sai da heurística legada de load_context, e "
              f"val_ok=True{RESET}")
        print(f"  {DIM}não é evidência — sem contrato, a validação aprova "
              f"qualquer saída.{RESET}")

    # ── Insumos: recusa, não degrada ─────────────────────────────
    # Na esteira, insumo ausente degrada para não travar as sucessoras. Aqui não
    # há sucessora, e despachar sem insumo só produz alucinação cara.
    if passo.get("inputs"):
        ok, mensagem, faltantes = preflight_step_inputs(project, passo)
        if not ok:
            # stdout ja imprimiu o cabecalho do passo; sem flush os dois
            # fluxos intercalam e o erro aparece antes do contexto dele.
            sys.stdout.flush()
            print(f"\n{RED}{'=' * 74}{RESET}", file=sys.stderr)
            print(f"{RED}{mensagem}{RESET}", file=sys.stderr)
            print(f"{RED}{'=' * 74}{RESET}", file=sys.stderr)
            return cli.EXIT_FAILED

    if args.dry_run:
        print(f"\n  {GREEN}--dry-run: passo resolvido, nada despachado.{RESET}")
        if args.json:
            print(json.dumps(passo, ensure_ascii=False, indent=2, default=str))
        return cli.EXIT_OK

    # ── Setup mínimo ─────────────────────────────────────────────
    output_dir = WORKSPACE / "projects" / project / "outputs" / "pipeline_runner"
    output_dir.mkdir(parents=True, exist_ok=True)   # run_step escreve sem criar

    if not API_KEY_FILE.exists():
        print(f"{RED}.copilot-key não encontrado em {API_KEY_FILE}{RESET}",
              file=sys.stderr)
        return cli.EXIT_CONFIG
    api_key = API_KEY_FILE.read_text(encoding="utf-8").strip()
    if not api_key:
        print(f"{RED}.copilot-key está vazio.{RESET}", file=sys.stderr)
        return cli.EXIT_CONFIG

    headroom_proc = None
    if args.headroom:
        base_url, headroom_proc = setup_headroom_mode(project)
    else:
        # Aproveita o proxy se já estiver no ar; senão vai direto. `run_step`
        # reativa sozinho se ele subir no meio.
        _hr = headroom_proxy_url()
        base_url = (_headroom_client_url(_hr) if headroom_proxy_alive(_hr)
                    else (ENDPOINT if PROVIDER == "anthropic" else ENDPOINT_OPENAI))

    client = anthropic.Anthropic(api_key=api_key, base_url=base_url,
                                 default_headers={"anthropic-version": "2023-06-01"})

    # ── Despacho ─────────────────────────────────────────────────
    # `metricas` e `_status` nascem antes do try porque o `finally` grava o
    # relatório nos três desfechos — sucesso, Ctrl+C e falha do agente — e uma
    # execução avulsa consome tanta inferência quanto uma fase da esteira.
    _manual_start_ts = time.time()
    _manual_phase = _phase_identity(passo)
    _manual_id = f"runner19-{int(_manual_start_ts)}"
    metricas: dict = {}
    _manual_status = "failed"
    # Arquivo em disco antes do despacho, pelo mesmo motivo da esteira: quem
    # acompanha precisa ver que a execução começou, não só que terminou.
    write_execution_metrics(
        project, execution_id=_manual_id, execution_mode=EXEC_MODE_MANUAL,
        execution_status="running", start_ts=_manual_start_ts,
        end_ts=_manual_start_ts, exec_metrics={})
    try:
        metricas = run_step(client, passo, project, output_dir)
        _manual_status = ("completed" if metricas.get("val_ok", True)
                          else "completed_with_warnings")
    except KeyboardInterrupt:
        _manual_status = "interrupted"
        print(f"\n{YELLOW}  Interrompido.{RESET}", file=sys.stderr)
        return cli.EXIT_ABORTED
    except Exception as exc:                                  # noqa: BLE001
        _manual_status = "failed"
        print("\n" + explain_failure(passo, exc, project), file=sys.stderr)
        return cli.EXIT_FAILED
    finally:
        _val_ok = bool(metricas.get("val_ok", False))
        _metrics_path = write_execution_metrics(
            project,
            execution_id=_manual_id,
            execution_mode=EXEC_MODE_MANUAL,
            execution_status=_manual_status,
            start_ts=_manual_start_ts,
            end_ts=time.time(),
            # Sempre uma entrada, mesmo vazia: a fase foi despachada, e omiti-la
            # produziria um `phase_metrics: []` indistinguível de "nada rodou".
            exec_metrics={_manual_phase: metricas},
            executed=[_manual_phase] if _val_ok else [],
            val_failed=[] if _val_ok else [_manual_phase],
        )
        if _metrics_path:
            print(f"  {DIM}📈 Métricas: {_metrics_path}{RESET}")
        if headroom_proc and headroom_proc.poll() is None:
            headroom_proc.terminate()

    if args.json:
        print(json.dumps(metricas, ensure_ascii=False, indent=2, default=str))

    if not metricas.get("val_ok", True):
        detalhe = metricas.get("detail") or "artefatos declarados não gravados"
        # Camada SpecKit em evolução: reporta o achado, mas o exit code
        # permanece 0. Um passo non-blocking não pode reprovar quem o chamou —
        # nem a esteira, nem a CI que despacha o agente avulso.
        if _speckit_nonblocking_step(passo):
            print(f"\n{CYAN}  {args.agent} concluído com aviso — {detalhe}{RESET}")
            print(f"{CYAN}  Fase SpecKit é non-blocking: exit code 0.{RESET}")
            return cli.EXIT_OK
        print(f"\n{RED}  {args.agent} reprovado — {detalhe}{RESET}", file=sys.stderr)
        return cli.EXIT_FAILED

    print(f"\n{GREEN}  {args.agent} concluído — "
          f"{metricas.get('artifacts', 0)} artefato(s).{RESET}")
    return cli.EXIT_OK


def _despachar_fase(args) -> int:
    """Executa UMA etapa da esteira pelo id, sem menu. Exit 0/1/2/130.

    `--phase` nasceu aqui só como desempate de `--agent` presente em mais de
    uma etapa, e sem `--agent` era ignorado em silêncio: o operador digitava
    `--phase F4S`, caía no fluxo interativo inteiro (modelo → projeto → modo →
    fases) e concluía que a flag não funciona. Pior, o CLI irmão
    (`ava_pipeline.py`) usa a MESMA flag como seletor de etapa/grupo — mesmo
    nome, duas semânticas, uma delas falhando calada.

    Aqui `--phase` passa a selecionar de fato. O agente sai da tabela PIPELINE,
    então isto vale igual para passo de agente e para passo determinístico
    (`kind: tool`, como F4S e F2d).
    """
    if not args.project:
        print(f"{RED}--phase exige -p/--project.{RESET}", file=sys.stderr)
        print(f'{DIM}  ex: python "ava-pipeline-runner-cli.py" --phase {args.phase} '
              f'-p cadastro-funcionarios{RESET}', file=sys.stderr)
        return 2

    alvo = str(args.phase).strip()
    exatos = [passo for passo in PIPELINE
              if str(passo.get("phase", "")).casefold() == alvo.casefold()]
    if exatos:
        args.phase = exatos[0]["phase"]
        args.agent = exatos[0]["agent"]
        return _despachar_agente_unico(args)

    grupo = PHASE_GROUPS.get(alvo.upper())
    if grupo:
        # Um grupo são N etapas com estado entre elas. Despachá-las por este
        # caminho — que não grava runner-state nem status HTML — daria a
        # impressão de ter rodado a fase inteira sem deixar o rastro que a
        # esteira exige. Melhor nomear as etapas e devolver a escolha.
        print(f"{RED}--phase {alvo} é um GRUPO, não uma etapa.{RESET}",
              file=sys.stderr)
        print(f"{DIM}  {grupo['label']}{RESET}", file=sys.stderr)
        print(f"{DIM}  Rode uma etapa por vez:{RESET}", file=sys.stderr)
        for fase in grupo["phases"]:
            print(f'{DIM}    python "ava-pipeline-runner-cli.py" --phase {fase} '
                  f'-p {args.project}{RESET}', file=sys.stderr)
        print(f"{DIM}  Ou use o menu interativo (sem --phase) e escolha o "
              f"grupo {alvo.upper()}.{RESET}", file=sys.stderr)
        return 2

    print(f"{RED}etapa desconhecida: {alvo!r}{RESET}", file=sys.stderr)
    print(f"{DIM}  etapas: {', '.join(passo['phase'] for passo in PIPELINE)}{RESET}",
          file=sys.stderr)
    print(f"{DIM}  grupos: {', '.join(sorted(PHASE_GROUPS))}{RESET}", file=sys.stderr)
    return 2


def main(project_preselecionado: "str | None" = None):
    import warnings; warnings.filterwarnings("ignore")
    global DEPLOYMENT  # atualizado após seleção interativa de modelo

    print(f"\n{MAGENTA}{'═'*60}{RESET}")
    print(f"{MAGENTA}{BOLD}  AVA Fabric — Pipeline Runner{RESET}")
    print(f"{MAGENTA}{BOLD}  Foundry: {DEPLOYMENT} (IMF) | ctx 1M | out {MAX_TOKENS} tokens{RESET}")
    print(f"{MAGENTA}{'═'*60}{RESET}")

    # ── Validação de requisitos ───────────────────────────────────
    # Verifica pacotes Python, ferramentas externas e credenciais
    # antes de qualquer interação com o usuário ou chamada à API.
    reqs_ok = check_and_install_requirements(auto_install=False)
    if not reqs_ok:
        cont = safe_input(f"\n  {YELLOW}{BOLD}⚠️  Requisitos pendentes. Continuar mesmo assim? [S/N]: {RESET}").strip().upper()
        if cont != "S":
            print(f"  {DIM}Pipeline abortado. Resolva os requisitos e tente novamente.{RESET}")
            sys.exit(1)

    # ── Selecionar modelo Foundry ─────────────────────────────────
    _early_key = ""
    if API_KEY_FILE.exists():
        _early_key = API_KEY_FILE.read_text(encoding="utf-8").strip()
    if _early_key:
        DEPLOYMENT = _select_model_interactive(_early_key)
    else:
        print(f"  {DIM}[Modelo] .copilot-key não encontrado — usando padrão: {DEPLOYMENT}{RESET}")
    print(f"  {GREEN}✅ Modelo ativo: {DEPLOYMENT}{RESET}")

    # ── Selecionar projeto ────────────────────────────────────────
    projects = list_projects()
    # `-p` sem `--agent` apenas pré-preenche: mesma esteira, uma pergunta a
    # menos. Nome inválido cai no menu em vez de abortar — quem digitou errado
    # não perde a sessão.
    if project_preselecionado:
        if project_preselecionado in projects:
            project = project_preselecionado
            print(f"\n{CYAN}  Projeto: {project}   (via -p){RESET}")
            _pular_menu_projeto = True
        else:
            print(f"\n{YELLOW}  Projeto {project_preselecionado!r} não encontrado "
                  f"— escolha na lista.{RESET}")
            _pular_menu_projeto = False
    else:
        _pular_menu_projeto = False

    if not _pular_menu_projeto:
        print(f"\n{BOLD}Projetos disponíveis:{RESET}")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p}")
        print(f"  {len(projects)+1}. Digitar nome manualmente")

        raw = safe_input(f"\n{BOLD}Selecione o projeto [número ou nome]: {RESET}").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if idx == len(projects):
                project = safe_input("  Nome do projeto: ").strip()
            elif 0 <= idx < len(projects):
                project = projects[idx]
            else:
                print(f"{RED}Seleção inválida.{RESET}"); sys.exit(1)
        else:
            project = raw

    if not project:
        print(f"{RED}Nome do projeto não pode ser vazio.{RESET}"); sys.exit(1)

    # ── Verificar estado anterior de execução ────────────────────
    # Antes de montar o pipeline, oferece retomar uma execução anterior.
    previous_state = _load_runner_state(project)
    resume_mode = False
    if previous_state is not None:
        print(f"\n{YELLOW}{'─'*60}{RESET}")
        print(f"{YELLOW}{BOLD}  ⚠️  Execução anterior detectada{RESET}")
        print(f"{YELLOW}  Projeto: {project}{RESET}")
        print(f"{YELLOW}  Último passo: {previous_state.get('last_index', 0)}/{len(previous_state.get('active_phases', []))}{RESET}")
        print(f"{YELLOW}  Executados: {len(previous_state.get('executed', []))}{RESET}")
        print(f"{YELLOW}  Pulados:    {len(previous_state.get('skipped', []))}{RESET}")
        print(f"{YELLOW}  Abortados:  {len(previous_state.get('aborted', []))}{RESET}")
        _degradadas = previous_state.get("degraded") or []
        if _degradadas:
            # Uma fase degradada conta como executada e a retomada vai pulá-la.
            # Nomear aqui é o que permite ao operador decidir por recomeçar.
            print(f"{YELLOW}  Degradadas: {len(_degradadas)} — executadas COM pendência:{RESET}")
            for _item in _degradadas[:5]:
                print(f"{YELLOW}      • {_item.get('phase')}: {_item.get('reason', '')[:70]}{RESET}")
            if len(_degradadas) > 5:
                print(f"{YELLOW}      • (+{len(_degradadas) - 5} não listadas){RESET}")
            print(f"{DIM}      Detalhe: outputs/pipeline_runner/remediation-report.json{RESET}")
            print(f"{DIM}      Para repeti-las, responda [N] e recomece a fase.{RESET}")
        print(f"{YELLOW}{'─'*60}{RESET}")
        resp = safe_input(
            f"\n{BOLD}Deseja retomar de onde parou? [S]im / [N]ão (recomeçar): {RESET}"
        ).strip().upper()
        if resp in ("S", ""):
            resume_mode = True
            print(f"{CYAN}  [RESUME] Retomando execução anterior.{RESET}")
        else:
            print(f"{CYAN}  [RESUME] Descartando estado anterior e recomeçando.{RESET}")
            previous_state = None

    # ── Validação de pré-requisitos do F0/AST ────────────────────
    # Segue a mesma lógica do run_ast_step():
    #   • campo vazio  → skip silencioso, sem perguntar (comportamento normal)
    #   • campo preenchido e pré-requisitos OK → F0 executará o AST
    #   • campo preenchido e algum pré-requisito falhou → ALERTA + pergunta
    ast_result = validate_ast_prerequisites(project)
    print_ast_validation(project, ast_result)

    if not ast_result.get("skip_ast") and not ast_result["ready"]:
        # Analyzer configurado mas com problema: pergunta se deve continuar
        print(f"\n  {RED}{BOLD}⚠️  AST configurado mas com erros — F0 falharia se executado.")
        print(f"  {DIM}  Corrija os itens acima ou continue sem AST (pattern-based).{RESET}")
        cont = safe_input(f"\n  {BOLD}Continuar sem AST? [S]im / [N] abortar: {RESET}").strip().upper()
        if cont != "S":
            print(f"  {DIM}Pipeline abortado. Corrija os itens acima e tente novamente.{RESET}")
            sys.exit(1)
        print(f"  {YELLOW}  Continuando sem AST — agentes F1 usarão análise pattern-based.{RESET}")

    # ── Modo de execução: Full ou Por Fase ────────────────────────
    print(f"\n{BOLD}Modo de execução:{RESET}")
    print(f"  {CYAN}1.{RESET} Full Pipeline  (todas as {len(PIPELINE)} etapas)")
    print(f"  {CYAN}2.{RESET} Por Fase       (selecionar quais fases incluir)")
    mode_raw = safe_input(f"\n{BOLD}Escolha [1/2]: {RESET}").strip()

    # ── Modo auto-execução ───────────────────────────────────────
    print(f"\n{BOLD}Modo de confirmação:{RESET}")
    print(f"  {CYAN}1.{RESET} Manual   (confirmar cada passo com S/P/A)")
    print(f"  {CYAN}2.{RESET} Automático (executar todos sem parar)")
    auto_raw = safe_input(f"\n{BOLD}Escolha [1/2]: {RESET}").strip()
    auto_mode = auto_raw == "2"

    if mode_raw == "2":
        print(f"\n{BOLD}Fases disponíveis (múltipla seleção, ex: 1 3 5):{RESET}")
        group_keys = list(PHASE_GROUPS.keys())
        for i, k in enumerate(group_keys, 1):
            steps_in_group = [s for s in PIPELINE if s["phase"] in PHASE_GROUPS[k]["phases"]]
            agents = ", ".join(f"@{s['agent'].replace('ava-','')}" for s in steps_in_group)
            print(f"  {CYAN}{i}.{RESET} {PHASE_GROUPS[k]['label']}")
            print(f"     {DIM}{agents}{RESET}")

        sel_raw = safe_input(f"\n{BOLD}Números das fases (ex: 1 2 3): {RESET}").strip()
        selected_phases: set[str] = set()
        for tok in sel_raw.split():
            if tok.isdigit():
                idx = int(tok) - 1
                if 0 <= idx < len(group_keys):
                    selected_phases.update(PHASE_GROUPS[group_keys[idx]]["phases"])

        if not selected_phases:
            print(f"{RED}Nenhuma fase selecionada.{RESET}"); sys.exit(1)

        active_steps = [s for s in PIPELINE if s["phase"] in selected_phases]
        mode_label = "Fases selecionadas: " + ", ".join(sorted(selected_phases))
        _partial_selection = True
    else:
        active_steps = PIPELINE
        mode_label = "Full Pipeline"
        _partial_selection = False

    active_steps = _expand_ledger_phase(active_steps, project)

    # ── Criar pasta de outputs ────────────────────────────────────
    output_dir = WORKSPACE / "projects" / project / "outputs" / "pipeline_runner"
    output_dir.mkdir(parents=True, exist_ok=True)
    _pipeline_start_ts = time.time()
    # Mesmo formato do `run_id` do runner-state, para que estado e métricas do
    # mesmo run possam ser correlacionados sem tabela de-para.
    _execution_id = f"runner19-{int(_pipeline_start_ts)}"
    _execution_mode = (EXEC_MODE_RESUMED if resume_mode else
                       EXEC_MODE_PARTIAL if _partial_selection else
                       EXEC_MODE_FULL)

    # ── Métricas: arquivo criado já na largada ────────────────────
    # Antes do dashboard e antes da autenticação, de propósito. Um run que
    # morre no [Auth] também começou, e o arquivo é o que registra isso; deixar
    # a primeira gravação para o fim do primeiro passo abriria uma janela em
    # que a esteira está no ar sem nenhum relatório em disco.
    _metrics_path = write_execution_metrics(
        project,
        execution_id=_execution_id,
        execution_mode=_execution_mode,
        execution_status="running",
        start_ts=_pipeline_start_ts,
        end_ts=_pipeline_start_ts,
        exec_metrics={},
    )
    if _metrics_path:
        print(f"\n  {CYAN}📈 Métricas (atualizadas a cada fase):{RESET}")
        print(f"  {DIM}  {_metrics_path}{RESET}")
    # `reset` só na esteira COMPLETA a partir do zero — a única em que o
    # histórico anterior não descreve mais a execução em curso. Retomada
    # (`--resume`) e execução por fase carregam o ledger e preservam tudo o que
    # já rodou: era exatamente aqui, com as listas de veredicto vazias, que o
    # dashboard era regravado do zero e o histórico sumia da tela.
    _status_html = _write_status_html(project, active_steps, [], [], [],
                                      start_ts=_pipeline_start_ts,
                                      reset=(_execution_mode == EXEC_MODE_FULL))
    print(f"\n  {CYAN}📊 Dashboard visual (auto-refresh 3s — Opção 2):{RESET}")
    print(f"  {DIM}  {_status_html.as_uri()}{RESET}")
    print(f"  {DIM}  VS Code: Ctrl+Shift+P → 'Simple Browser: Show' → cole a URL acima{RESET}")
    if _RICH_OK:
        print(f"  {GREEN}  rich instalado ✅ — banners com painéis visuais (Opção 1){RESET}")

    banner(f"Projeto: {project}  |  {mode_label}  |  {len(active_steps)} passos", MAGENTA)

    # Fases que rodam sem LLM (builders Python determinísticos / subprocess)
    _DETERMINISTIC_PHASES = {"F0", "S1", "S2", "S3", "S4"}
    _needs_llm = any(s["phase"] not in _DETERMINISTIC_PHASES for s in active_steps)

    if not _needs_llm:
        # Todas as fases são determinísticas — pula headroom, proxy e ping de LLM.
        print(f"\n{DIM}[Auth] Fases determinísticas (sem LLM) — headroom e autenticação ignorados.{RESET}")
        base_url, headroom_proc = ENDPOINT, None
        api_key = API_KEY_FILE.read_text(encoding="utf-8").strip() if API_KEY_FILE.exists() else "skip"
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url,
                                     default_headers={"anthropic-version": "2023-06-01"})
    else:
        # ── Alcance do endpoint privado ───────────────────────────────
        # Antes do headroom: subir o proxy custa até 60s de espera, e ele fala
        # com o mesmo upstream. Sem TCP para o Foundry, esse minuto e os dois
        # pings de auth que vêm depois só adiam a mesma falha, trocando a causa
        # real por um APIStatusError seguido de um timeout.
        _net_ok, _net_info = foundry_tcp_probe(timeout_s=5.0)
        if not _net_ok:
            print(f"\n{BOLD}[Auth]{RESET} Verificando alcance do Foundry...")
            print(explain_foundry_unreachable(_net_info))
            sys.exit(1)

        # ── Headroom: sobe automaticamente ───────────────────────────
        base_url, headroom_proc = setup_headroom_mode(project)

        # ── Carregar API Key do Foundry ───────────────────────────────
        print(f"\n{BOLD}[Auth]{RESET} Carregando API Key de {API_KEY_FILE.name}...")
        if not API_KEY_FILE.exists():
            print(f"{RED}  ❌ Arquivo .copilot-key não encontrado em {API_KEY_FILE}{RESET}")
            print(f"  Crie o arquivo com a API Key do Foundry (sem newline).")
            sys.exit(1)
        api_key = API_KEY_FILE.read_text(encoding="utf-8").strip()
        if not api_key:
            print(f"{RED}  ❌ .copilot-key está vazio.{RESET}"); sys.exit(1)
        try:
            client = anthropic.Anthropic(
                api_key=api_key,
                base_url=base_url,
                default_headers={"anthropic-version": "2023-06-01"},
            )
            if DEPLOYMENT.lower().startswith("claude"):
                with client.messages.stream(
                    model=DEPLOYMENT,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                ) as _s:
                    _s.get_final_message()
            else:
                _stream_openai(api_key, "", "ping", out_tokens=5)
            via = "headroom proxy" if base_url != ENDPOINT else "endpoint direto"
            print(f"{GREEN}  ✅ Conectado — {DEPLOYMENT} ({via}).{RESET}")
        except Exception as e:
            _direct = ENDPOINT if PROVIDER == "anthropic" else ENDPOINT_OPENAI
            if base_url != _direct:
                print(f"{YELLOW}  ⚠️  Headroom proxy falhou ({type(e).__name__}) — tentando endpoint direto...{RESET}")
                if headroom_proc and headroom_proc is not _HEADROOM_ALREADY_RUNNING:
                    try: headroom_proc.terminate()
                    except Exception: pass
                try:
                    client = anthropic.Anthropic(
                        api_key=api_key,
                        base_url=_direct,
                        default_headers={"anthropic-version": "2023-06-01"},
                    )
                    if DEPLOYMENT.lower().startswith("claude"):
                        with client.messages.stream(
                            model=DEPLOYMENT,
                            messages=[{"role": "user", "content": "ping"}],
                            max_tokens=5,
                        ) as _s:
                            _s.get_final_message()
                    else:
                        _stream_openai(api_key, "", "ping", out_tokens=5, base_url=_direct)
                    base_url = _direct
                    headroom_proc = None
                    print(f"{GREEN}  ✅ Conectado via endpoint direto — {DEPLOYMENT}.{RESET}")
                except Exception as e2:
                    print(f"{RED}  ❌ Falha também no endpoint direto: {e2}{RESET}")
                    # O túnel pode ter caído entre o preflight e agora — nesse
                    # caso a causa é a rede, não a credencial.
                    _ok2, _info2 = foundry_tcp_probe(timeout_s=5.0)
                    if not _ok2:
                        print()
                        print(explain_foundry_unreachable(_info2))
                    else:
                        print(f"  {DIM}TCP 443 responde ({_info2}) — investigue a API Key "
                              f"ou o deployment '{DEPLOYMENT}'.{RESET}")
                    sys.exit(1)
            else:
                if headroom_proc and headroom_proc is not _HEADROOM_ALREADY_RUNNING:
                    try: headroom_proc.terminate()
                    except Exception: pass
                print(f"{RED}  ❌ Falha na conexão: {e}{RESET}")
                _ok3, _info3 = foundry_tcp_probe(timeout_s=5.0)
                if not _ok3:
                    print()
                    print(explain_foundry_unreachable(_info3))
                else:
                    print(f"  {DIM}TCP 443 responde ({_info3}) — investigue a API Key "
                          f"ou o deployment '{DEPLOYMENT}'.{RESET}")
                sys.exit(1)

    # ── Executar pipeline ─────────────────────────────────────────
    # Inicializa listas de controle. Se estiver retomando, restaura o estado
    # salvo e sincroniza com os passos ativos atuais.
    if resume_mode and previous_state is not None:
        executed = list(previous_state.get("executed", []))
        skipped = list(previous_state.get("skipped", []))
        aborted = list(previous_state.get("aborted", []))
        val_failed = list(previous_state.get("val_failed", []))
        exec_metrics = {
            k: v for k, v in (previous_state.get("exec_metrics") or {}).items()
        }
        print(f"{CYAN}  [RESUME] Restaurados {len(executed)} executados, "
              f"{len(skipped)} pulados, {len(val_failed)} val_fail, "
              f"{len(aborted)} abortados.{RESET}")
    else:
        executed, skipped, aborted, val_failed = [], [], [], []
        exec_metrics: dict[str, dict] = {}   # phase → métricas reais de run_step

    import pipeline_config as _pipeline_config
    _runner_cfg = _pipeline_config.load_config(project)

    # ── Registra o contexto do heartbeat do dashboard ─────────────
    # `steps`/`executed`/`skipped`/`aborted` são mutados no lugar (append e
    # atribuição por fatia), então o dict guarda as MESMAS referências e enxerga
    # cada avanço. O único ponto que as reatribui — descarte de estado por
    # manifesto divergente — atualiza `_RUN_CTX` explicitamente.
    #
    # `execution_id`/`execution_mode` entram aqui pelo mesmo motivo: são o que
    # `write_metrics_from_run_ctx` precisa para gravar o relatório quando o run
    # morre por Ctrl+C ou erro interno, sem passar pelo fecho normal.
    _RUN_CTX.clear()
    _RUN_CTX.update({"project": project, "steps": active_steps,
                     "executed": executed, "skipped": skipped, "aborted": aborted,
                     "val_failed": val_failed,
                     "metrics": exec_metrics, "start_ts": _pipeline_start_ts,
                     "execution_id": _execution_id,
                     "execution_mode": _execution_mode})

    # Numa retomada, `exec_metrics` acabou de ser reidratado do estado anterior:
    # publica o acumulado antes do primeiro despacho, para que o arquivo já
    # reflita as fases herdadas em vez de parecer um run zerado.
    flush_execution_metrics(project, executed, skipped, aborted,
                            exec_metrics, val_failed)

    # Inicializado antes do laço: os ramos de pulo/aborto do operador chegam ao
    # `if _abort_pipeline:` do fim da iteração sem passar pelo bloco de despacho
    # que o atribuía, o que levantava NameError no primeiro passo pulado.
    #
    # Nenhum caminho de ERRO atribui True aqui: erro não trava fase, degrada
    # (ver `_degrade_phase`). Só decisão humana trava, e há exatamente duas:
    #   1. o operador aborta a esteira no prompt do passo (decision == "A");
    #   2. o operador recusa a liberação da F4 no gate de aprovação da F3S
    #      (wave6c, `requires_approval` — ver `_solicitar_aprovacao`).
    # A regra "erro nunca trava fase" fala de erro; um "Não" é decisão. Quem
    # mexer aqui achando que (2) é regressão deve ler antes o cabeçalho de
    # política de src/shared/data/pipeline-dag/F3S.yaml.
    _abort_pipeline = False

    idx = 0
    while idx < len(active_steps):
        step = active_steps[idx]

        # ── Pular passos já executados ao retomar ───────────────────
        # Se a execução foi interrompida e o usuário optou por retomar,
        # evita reprocessar fases que já constam como executadas.
        phase_key = _phase_identity(step)
        if phase_key in executed:
            print(f"{CYAN}  [RESUME] {phase_key} já executado — pulando.{RESET}")
            # Sem isto o dashboard ficava na foto inicial durante toda a varredura
            # dos passos já concluídos, que na retomada são a maioria.
            status_heartbeat("", None, 0)
            idx += 1
            continue

        if step.get("phase") == "F3S":
            expanded = [step]
            if not _expand_dag_phases(expanded, project):
                _degrade_unexpandable_f3s(
                    step,
                    RuntimeError(step.pop(
                        "dag_expansion_error",
                        "manifesto de waves indisponível ou incoerente",
                    )),
                    executed, skipped, aborted, exec_metrics, val_failed,
                )
                _write_status_html(project, active_steps, executed, skipped, aborted,
                                   start_ts=_pipeline_start_ts, exec_metrics=exec_metrics)
                _save_runner_state(project, active_steps, executed, skipped,
                                   aborted, exec_metrics, idx)
                idx += 1
                continue
            active_steps[idx:idx + 1] = expanded

            # ── Consistência de retomada após expansão do DAG ───────
            # Se estiver retomando, garante que a lista de fases ativas não
            # divergiu do manifesto de waves desde a execução anterior.
            if resume_mode and previous_state is not None:
                current_phases = [_phase_identity(s) for s in active_steps]
                saved_phases = previous_state.get("active_phases", [])
                if current_phases != saved_phases:
                    print(f"\n{YELLOW}{BOLD}  ⚠️  Manifesto de waves mudou desde a execução anterior.{RESET}")
                    print(f"{YELLOW}  A lista de passos expandidos não coincide com o estado salvo.{RESET}")
                    print(f"{YELLOW}  Estado será descartado e a execução recomeçará do início.{RESET}")
                    executed, skipped, aborted = [], [], []
                    exec_metrics = {}
                    resume_mode = False
                    previous_state = None
                    # Reatribuição: o heartbeat precisa apontar para as listas novas.
                    # O modo também deixa de ser "resumed" — o estado foi
                    # descartado e este run recomeça do zero.
                    _RUN_CTX.update({"executed": executed, "skipped": skipped,
                                     "aborted": aborted, "val_failed": val_failed,
                                     "metrics": exec_metrics,
                                     "execution_mode": (EXEC_MODE_PARTIAL
                                                        if _partial_selection
                                                        else EXEC_MODE_FULL)})
            # Dashboard reflete a lista já expandida antes do 1º despacho.
            status_heartbeat("", None, 0, force=True)
            continue
        if step.get("task_id"):
            import task_ledger as _task_ledger
            _ready = {task["task_id"] for task in _task_ledger.ready_tasks(project)}
            if step["task_id"] not in _ready:
                _diag = _task_ledger.diagnose(project)
                # Continua `skipped` de propósito: a task não falhou, as
                # dependências dela ainda não ficaram prontas, e é ficar FORA de
                # `executed` que faz `--resume` voltar nela quando ficarem. O
                # registro abaixo garante que ela apareça no relatório de
                # remediação com o caminho de destravamento.
                skipped.append(step["phase"])
                exec_metrics[step["phase"]] = {
                    "phase": step["phase"], "agent": step["agent"],
                    "skill_kb": 0, "inp_tokens": 0, "out_max": 0,
                    "resp_tokens": 0, "ctx_pct": 0, "elapsed_s": 0,
                    "artifacts": 0, "val_ok": False,
                    "detail": f"task não pronta: {_diag['status']}",
                }
                _record_degradation(
                    step["phase"], step.get("agent", ""),
                    f"task não pronta no ledger: {_diag['status']}",
                    "conclua as tasks predecessoras (task_ledger.py --project "
                    f"{project} --diagnose) e re-execute com --resume",
                )
                print(f"  {RED}❌ {step['task_id']} bloqueada: {_diag['status']}{RESET}")
                continue

        # ── Preflight de insumos obrigatórios ────────────────────────
        # Custo zero de inferência. Este runner é o executor real da esteira; o
        # preflight do CLI declarativo (`ava_pipeline.preflight_inputs`) nunca
        # roda por aqui, então a dependência precisa ser conferida neste ponto —
        # antes do despacho, e de forma que o estado seja gravado (ISSUE-004).
        if step.get("kind", "agent") != "tool":
            _ok, _msg, _faltantes = preflight_step_inputs(project, step)
            if not _ok:
                # Insumo ausente NÃO aborta mais a esteira. O agente é pulado
                # (despachá-lo sem o insumo só produziria alucinação), a fase
                # entra como executada-com-aviso e o produtor real do artefato
                # faltante vai para o relatório de remediação.
                print(f"\n{YELLOW}{_msg}{RESET}")
                _degrade_phase(
                    step,
                    "insumo obrigatório ausente: " + ", ".join(_faltantes),
                    f"gere {_faltantes[0]} (verifique a fase que o produz no DAG) "
                    f"e re-execute {step['phase']}; o agente não foi despachado "
                    f"porque sem o insumo a saída seria alucinada",
                    executed, skipped, aborted, exec_metrics, val_failed=val_failed,
                )
                _write_status_html(project, active_steps, executed, skipped, aborted,
                                   start_ts=_pipeline_start_ts, exec_metrics=exec_metrics)
                _save_runner_state(project, active_steps, executed, skipped,
                                   aborted, exec_metrics, idx)
                if step.get("phase", "").startswith("F3S:"):
                    # NÃO entra em `val_failed`: a camada SpecKit é
                    # non-blocking enquanto está em evolução, e um insumo
                    # ausente aqui é informação, não reprovação do run. A
                    # degradação já foi registrada acima.
                    print(f"  {CYAN}Passo F3S não executável nesta tentativa "
                          f"(informativo, não reprova); continuando até a "
                          f"reconciliação obrigatória.{RESET}")
                    idx += 1
                    continue
                print(f"  {RED}Fases sucessoras bloqueadas. Estado salvo para retomada.{RESET}")
                break

        generation_attempt = 0
        max_generation_attempts = 2 if step.get("phase", "").startswith("F3S:") else 1
        while True:
            decision = ask_permission(step, idx, len(active_steps), auto=auto_mode,
                                       executed=executed, skipped=skipped,
                                       active_steps=active_steps)

            if decision == "V":
                if step.get("kind") == "tool":
                    import ava_pipeline as _ava_pipeline
                    from pipeline_plan import Step as _PipelineStep
                    _tool = _PipelineStep(
                        phase=step["phase"], group="F3S", agent=step["agent"],
                        trigger=None, label=step["label"], kind="tool",
                        command=list(step.get("command") or []),
                        on_fail=str(step.get("on_fail") or ""),
                    )
                    print(f"\n{DIM}{' '.join(_ava_pipeline.resolve_tool_command(_tool, project))}{RESET}")
                elif step["agent"] == "_ast_extractor":
                    # F0 não tem skill LLM — exibe info do script
                    print(f"\n{DIM}  F0 — run_ast_analysis.py (subprocess, não-LLM)")
                    print(f"  Extrai 9 JSONs determinísticos do código-fonte legado via")
                    lang = ""
                    try:
                        import yaml as _y
                        _cfg = _y.safe_load((WORKSPACE / "projects" / project / "context" / "project-config.yaml").read_text(encoding="utf-8"))
                        lang = _cfg.get("legacy_technology", "delphi")
                    except Exception:
                        lang = "delphi"
                    print(f"  Extrai 9 JSONs determinísticos do código-fonte legado via")
                    print(f"  ava-fabric-{lang}-analyzer (legacy_technology={lang}).")
                    print(f"  O path do analyzer é lido de project-config.yaml:")
                    print(f"    ava_ast_analyzers.{lang} → ava_ast_analyzer_path (alias Delphi) → env AVA_{lang.upper()}_ANALYZER_HOME")
                    print(f"  Script: src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py{RESET}")
                else:
                    skill = load_skill(step["agent"],
                                       spec_path=step.get("spec_path"))
                    print(f"\n{DIM}{textwrap.fill(skill[:2000], width=80)}{RESET}")
                    if len(skill) > 2000:
                        print(f"{DIM}  [...] (skill truncado — {len(skill)} chars total){RESET}")
                continue  # volta a perguntar

            if decision == "A":
                aborted.append(step["phase"])
                _write_status_html(project, active_steps, executed, skipped, aborted,
                                   start_ts=_pipeline_start_ts, exec_metrics=exec_metrics)
                banner("Pipeline abortado pelo usuário", RED)
                break

            if decision == "P":
                skipped.append(step["phase"])
                print(f"  {YELLOW}⏭  Passo {step['phase']} pulado.{RESET}")
                _write_status_html(project, active_steps, executed, skipped, aborted,
                                   start_ts=_pipeline_start_ts, exec_metrics=exec_metrics)
                break

            if decision == "S":
                generation_attempt += 1
                _write_status_html(project, active_steps, executed, skipped, aborted,
                                   current_phase=step["phase"], start_ts=_pipeline_start_ts,
                                   exec_metrics=exec_metrics)
                try:
                    if step.get("task_id"):
                        import task_ledger as _task_ledger
                        _task_ledger.start(project, step["task_id"],
                                           run_id=f"runner19-{int(_pipeline_start_ts)}")
                    step_metrics = run_step(client, step, project, output_dir)
                    _abort_pipeline = False
                    _retry_step = False

                    if step.get("task_id"):
                        import ava_pipeline as _ava_pipeline
                        from pipeline_plan import Step as _PipelineStep
                        _task_step = _PipelineStep(
                            phase=step["phase"], group="F4", agent=step["agent"],
                            trigger=step.get("trigger"), label=step["label"],
                            task_id=step["task_id"], task_group=step.get("task_group", ""),
                            target_stack=step.get("target_stack", ""),
                            feature=step.get("feature", ""),
                            inputs=step.get("inputs") or {},
                        )
                        _generation = {
                            "artifacts": list(step_metrics.get("artifacts_written") or [])
                        }
                        _verification = _ava_pipeline.verify_task_step(
                            _task_step, project, _generation, output_dir, timeout_s=900,
                            client=client, model=DEPLOYMENT, cfg=_runner_cfg)
                        step_metrics["verification"] = _verification
                        step_metrics["val_ok"] = _verification["status"] == "verified"
                        if step_metrics.get("val_ok", True):
                            _mark_executed(step["phase"], executed, skipped, aborted)
                        else:
                            # Verificação de build reprovada não aborta a F4 nem
                            # some como "skipped": a task fica executada-com-aviso
                            # e o log da verificação vira o caminho de correção.
                            _reason = (_verification.get("abort_reason")
                                       if _verification.get("abort_needed")
                                       else "build verification failed")
                            _degrade_phase(
                                step, f"verificação de build reprovou: {_reason}",
                                f"inspecione {_verification.get('log') or 'o log da verificação'}, "
                                f"corrija o código gerado e re-execute {step['phase']}",
                                executed, skipped, aborted, exec_metrics,
                                val_failed=val_failed,
                            )
                    else:
                        # Fases comuns (sem task_id): registram execução diretamente
                        if step_metrics.get("val_ok", True):
                            _mark_executed(step["phase"], executed, skipped, aborted,
                                           val_failed=val_failed)
                        else:
                            # O passo RODOU — gastou inferência e produziu algo.
                            # Ele só não gravou nos caminhos declarados no DAG,
                            # que é tipicamente o agente escrevendo em outro
                            # diretório (medido: ava-speckit-compliance gravou
                            # em outputs/deliverables/ em vez de speckit/).
                            # Marcar "executado com pendência" e listar onde ele
                            # de fato escreveu dá ao operador o que ele precisa;
                            # `val_failed` some do painel, mas a fase aparece em
                            # `degraded` no estado e no relatório de remediação.
                            detail_msg = step_metrics.get("detail", "val_ok=False")
                            print(f"\n  {RED}❌ {step.get('phase')} val_fail: {detail_msg}{RESET}")
                            print(f"  {YELLOW}     O passo executou mas não gravou os artefatos declarados no DAG.{RESET}")
                            print(f"  {YELLOW}     Verifique se o agente gravou em diretório inesperado.{RESET}")
                            if (step.get("kind", "agent") == "agent"
                                    and generation_attempt < max_generation_attempts):
                                _retry_step = True
                                print(f"  {YELLOW}     Recuperação automática: nova tentativa "
                                      f"{generation_attempt + 1}/{max_generation_attempts} "
                                      f"será executada para os outputs ausentes.{RESET}")
                            else:
                                print(f"  {YELLOW}     Limite de recuperação atingido; o completeness "
                                      f"gate registrará o artefato ausente.{RESET}")
                            if not _retry_step:
                                escritos = step_metrics.get("artifacts_written") or []
                                onde = (" · gravou em: " + ", ".join(map(str, escritos[:4]))
                                        if escritos else
                                        " · nenhum arquivo foi gravado pelo agente")
                                _degrade_phase(
                                    step,
                                    f"artefatos declarados não gravados: {detail_msg}{onde}",
                                    ("mova/regere os artefatos nos caminhos declarados no DAG "
                                     "(as tools determinísticas a jusante tentam recuperar "
                                     "automaticamente); se o conteúdo não existir, recomece "
                                     f"{step['phase']} respondendo [N] na retomada"),
                                    executed, skipped, aborted, exec_metrics,
                                    val_failed=val_failed,
                                )

                    # ── Gate de aprovação humana (F3S wave6c) ──────────────
                    # A tool já classificou e gravou compliance-gate.json; a
                    # DECISÃO é conduzida aqui, no processo que tem o console e
                    # sabe se a execução é manual ou automática.
                    if step.get("requires_approval") and not _abort_pipeline:
                        _gate = _ler_gate_aprovacao(project)
                        if _gate is None:
                            _degrade_phase(
                                step,
                                "compliance-gate.json não foi produzido — não há "
                                "como saber se há achado crítico pendente",
                                f"execute {step['phase']} novamente e confira a "
                                f"saída da tool de gate",
                                executed, skipped, aborted, exec_metrics,
                                val_failed=val_failed,
                            )
                        elif _gate.get("decision_pending"):
                            _aprovado = _solicitar_aprovacao(project, _gate, auto_mode)
                            _quem = _ler_gate_aprovacao(project) or {}
                            _assinatura = (_quem.get("approval") or {})
                            if _aprovado:
                                _record_degradation(
                                    step["phase"], step.get("agent", ""),
                                    f"F4 liberada com {len(_gate.get('blockers') or [])} "
                                    f"achado(s) crítico(s)/alto(s) em aberto "
                                    f"({_assinatura.get('status', '?')})",
                                    "os achados continuam válidos — trate-os antes "
                                    "de confiar no código gerado pela F4",
                                )
                            else:
                                # ÚNICO bloqueio intencional da esteira. Não é
                                # erro: é a decisão de uma pessoa, e a política
                                # "erro nunca trava fase" fala de erro.
                                _record_degradation(
                                    step["phase"], step.get("agent", ""),
                                    "liberação da F4 recusada pelo operador",
                                    "corrija os achados de conformidade e "
                                    "reexecute a F3S a partir da wave6b",
                                    severity="blocking",
                                )
                                # Fica em `aborted` e FORA de `executed` — é essa
                                # ausência que faz a retomada voltar a este passo
                                # (o laço filtra por `executed`, não por
                                # `last_index`, que é apenas informativo). A
                                # gravação de estado é a do fim do passo, logo
                                # abaixo; duplicá-la aqui só criaria duas versões
                                # do mesmo estado.
                                aborted.append(step["phase"])
                                exec_metrics[step["phase"]]["detail"] = (
                                    "aprovação recusada pelo operador")
                                print(f"\n{RED}{'─' * 68}{RESET}")
                                print(f"{RED}  🛑 F3S interrompida: liberação da F4 "
                                      f"não aprovada.{RESET}")
                                print(f"{RED}  Estado salvo — a retomada volta a "
                                      f"este ponto.{RESET}")
                                print(f"{RED}{'─' * 68}{RESET}")
                                _abort_pipeline = True

                    # Merge, não substituição: `_degrade_phase` já pode ter
                    # gravado `degraded`/`detail`/`fix` para esta fase, e um
                    # replace apagaria justamente o caminho de correção.
                    _previous = exec_metrics.get(step["phase"]) or {}
                    _degraded_fields = {k: _previous[k] for k in ("degraded", "fix")
                                        if k in _previous}
                    if _degraded_fields and not step_metrics.get("detail"):
                        step_metrics["detail"] = _previous.get("detail", "")
                    step_metrics.update(_degraded_fields)
                    exec_metrics[step["phase"]] = step_metrics
                    _write_status_html(project, active_steps, executed, skipped, aborted,
                                       start_ts=_pipeline_start_ts, exec_metrics=exec_metrics,
                                       val_failed=val_failed)
                    _save_runner_state(project, active_steps, executed, skipped,
                                       aborted, exec_metrics, idx + 1,
                                       val_failed=val_failed)
                    if _retry_step:
                        continue
                    if _abort_pipeline:
                        break

                    # ── Pós-S1/S4: verificar qualidade do HTML gerado ─────
                    # Builder determinístico gera HTML completo (~4MB com template real).
                    # LLM fallback gera HTML pequeno (<100KB sem template) — S2 irá reconstruir.
                    # Em ambos os casos, avisa sobre a qualidade para que o usuário saiba.
                    if step["phase"] in ("S1", "S4"):
                        unified = _ensure_summary_unified(project)
                        MIN_HTML_SIZE = 100_000  # 100KB
                        if unified:
                            size_kb = unified.stat().st_size // 1024
                            if unified.stat().st_size >= MIN_HTML_SIZE:
                                print(f"  {GREEN}✅  Summary HTML real: {unified.name}  "
                                      f"({size_kb}KB) — template oficial aplicado. ✅{RESET}")
                            else:
                                print(f"  {YELLOW}⚠️  Summary HTML pequeno: {unified.name}  "
                                      f"({size_kb}KB) — gerado por LLM fallback sem template real.")
                                print(f"     S2 (Remediation) irá reconstruir com o template oficial.{RESET}")
                        else:
                            print(f"  {YELLOW}⚠️  Não foi possível confirmar HTML do summary. "
                                  f"S2/S3 serão bloqueados automaticamente se não houver HTML unificado.{RESET}")
                except MissingMandatoryInput as e:
                    # Rede de segurança: o preflight acima já barra o caso normal.
                    # Antes era `SystemExit`, que herda de BaseException, escapava
                    # do `except Exception` abaixo e matava o processo sem gravar
                    # estado — a "trava" relatada na ISSUE-004. Hoje também não
                    # aborta: degrada, registra e segue.
                    print(f"\n{YELLOW}{e}{RESET}")
                    _degrade_phase(
                        step,
                        "insumo obrigatório ausente: " + ", ".join(e.missing),
                        f"gere {e.missing[0]} e re-execute {step['phase']}",
                        executed, skipped, aborted, exec_metrics, val_failed=val_failed,
                    )
                    _write_status_html(project, active_steps, executed, skipped, aborted,
                                       start_ts=_pipeline_start_ts, exec_metrics=exec_metrics)
                    _save_runner_state(project, active_steps, executed, skipped,
                                       aborted, exec_metrics, idx + 1)
                    break
                except Exception as e:
                    print("\n" + explain_failure(step, e, project))
                    exec_metrics.setdefault(step["phase"], {
                        "phase": step["phase"], "agent": step["agent"],
                        "skill_kb": 0, "inp_tokens": 0, "out_max": 0,
                        "resp_tokens": 0, "ctx_pct": 0, "elapsed_s": 0,
                        "artifacts": 0, "val_ok": False,
                    })
                    exec_metrics[step["phase"]]["detail"] = f"{type(e).__name__}: {e}"
                    if step.get("kind") == "tool":
                        # TIMEOUT e FAILED pedem correções diferentes — o
                        # primeiro é configuração ou travamento, o segundo é
                        # defeito no artefato. Colapsar os dois em "reprovou"
                        # mandava o operador ler um relatório que a tool nem
                        # chegou a escrever.
                        _timeout = isinstance(e, subprocess.TimeoutExpired)
                        exec_metrics[step["phase"]]["tool_status"] = (
                            "TIMEOUT" if _timeout else "FAILED")
                        if _timeout:
                            _teto = getattr(e, "timeout_s", None) or e.timeout
                            exec_metrics[step["phase"]]["tool_timeout_s"] = int(float(_teto))
                            _degrade_phase(
                                step,
                                f"tool excedeu o teto de {int(float(_teto))}s "
                                f"(execução completa); processo e filhos encerrados",
                                f"o verifier NÃO rodou — o artefato em disco está "
                                f"sem veredito. Aumente \"timeout_s\" no nó "
                                f"{step['phase']} do DAG (hoje {int(float(_teto))}s) "
                                f"ou investigue o travamento nos logs exibidos "
                                f"acima, e re-execute {step['phase']} ANTES de "
                                f"confiar nas fases seguintes",
                                executed, skipped, aborted, exec_metrics,
                                val_failed=val_failed,
                            )
                            exec_metrics[step["phase"]]["risk_accepted"] = False
                            _write_status_html(project, active_steps, executed, skipped,
                                               aborted, start_ts=_pipeline_start_ts,
                                               exec_metrics=exec_metrics)
                            _save_runner_state(project, active_steps, executed, skipped,
                                               aborted, exec_metrics, idx + 1)
                            break
                        # ── Falha que o operador pode aceitar ────────────────
                        # `on_fail: confirm` no DAG marca a tool cuja reprovação
                        # é informação de qualidade, não corrupção de artefato.
                        # A decisão volta para quem opera, e fica registrada.
                        # Só o código reservado a lacuna de qualidade é
                        # negociável. Falha estrutural — grafo cíclico,
                        # referência quebrada, schema inválido — sai com 1 e
                        # aborta como qualquer outra, mesmo em passo marcado
                        # `on_fail: confirm`. Ninguém aceita risco sobre um
                        # artefato corrompido.
                        _rc = getattr(e, "returncode", None)
                        if (str(step.get("on_fail") or "") == "confirm"
                                and _rc == SOFT_FAIL_EXIT):
                            aceito = _confirmar_risco(step, auto_mode)
                            exec_metrics[step["phase"]].update({
                                "val_ok": False,
                                "risk_accepted": aceito,
                                "detail": ("risco aceito pelo operador: "
                                           if aceito else "cancelado pelo operador: ")
                                          + f"{type(e).__name__}",
                            })
                            if aceito:
                                # Risco aceito é decisão de seguir: a fase entra
                                # como executada-com-aviso, não como "pulada".
                                _degrade_phase(
                                    step,
                                    f"risco aceito pelo operador: {type(e).__name__}: {e}",
                                    f"a reprovação da tool continua válida — "
                                    f"corrija a causa e re-execute {step['phase']}",
                                    executed, skipped, aborted, exec_metrics,
                                    val_failed=val_failed,
                                )
                                exec_metrics[step["phase"]]["risk_accepted"] = True
                                _write_status_html(project, active_steps, executed, skipped,
                                                   aborted, start_ts=_pipeline_start_ts,
                                                   exec_metrics=exec_metrics)
                                _save_runner_state(project, active_steps, executed, skipped,
                                                   aborted, exec_metrics, idx + 1)
                                break
                        # Tool reprovada NUNCA bloqueia a esteira — nem com
                        # on_fail=warn, nem com o default. "⏭ pulado" era rótulo
                        # errado: a tool RODOU e reprovou, e o relatório dela já
                        # está em disco. A fase fica como executada-com-aviso e o
                        # motivo + a correção vão para remediation-report.json.
                        _degrade_phase(
                            step,
                            f"tool reprovou ({type(e).__name__}): {e}",
                            (f"leia o relatório da tool em projects/{project}/"
                             f"outputs/tobe/speckit/ e corrija a origem; "
                             f"depois re-execute {step['phase']}")
                            if str(step.get("on_fail") or "") == "warn" else
                            (f"tool determinística reprovou — corrija a causa e "
                             f"re-execute {step['phase']} ANTES de confiar nas "
                             f"fases seguintes, que rodaram com artefato incompleto"),
                            executed, skipped, aborted, exec_metrics,
                            val_failed=val_failed,
                        )
                        exec_metrics[step["phase"]]["risk_accepted"] = True
                        _write_status_html(project, active_steps, executed, skipped,
                                           aborted, start_ts=_pipeline_start_ts,
                                           exec_metrics=exec_metrics)
                        _save_runner_state(project, active_steps, executed, skipped,
                                           aborted, exec_metrics, idx + 1)
                        break
                    # No modo full (auto), NINGUÉM está no teclado: este prompt
                    # travava a esteira inteira até alguém aparecer — que é
                    # exatamente a "interrupção não controlada" que a política de
                    # continuidade proíbe. Sem operador, a resposta é [N]: a fase
                    # degrada pelo caminho comum abaixo e a esteira segue para a
                    # próxima elegível, respeitando as dependências entre fases.
                    if auto_mode:
                        print(f"  {YELLOW}Modo full: sem retentativa interativa — "
                              f"a fase degrada e a esteira continua.{RESET}")
                        retry = "N"
                    else:
                        retry = safe_input("  Tentar novamente? [S/N]: ").strip().upper()
                    if retry == "S":
                        continue
                    _degrade_phase(
                        step,
                        f"agente falhou ({type(e).__name__}): {e}",
                        f"corrija a causa acima e re-execute {step['phase']}; as "
                        f"fases seguintes rodaram sem o artefato desta",
                        executed, skipped, aborted, exec_metrics, val_failed=val_failed,
                    )
                    _write_status_html(project, active_steps, executed, skipped, aborted,
                                       start_ts=_pipeline_start_ts, exec_metrics=exec_metrics)
                    _save_runner_state(project, active_steps, executed, skipped,
                                       aborted, exec_metrics, idx + 1)
                break

        # Salva estado também após pulo ou aborto explícito do usuário
        if decision == "P":
            _save_runner_state(project, active_steps, executed, skipped,
                               aborted, exec_metrics, idx + 1)
        if decision == "A":
            _save_runner_state(project, active_steps, executed, skipped,
                               aborted, exec_metrics, idx)
            break
        if _abort_pipeline:
            _save_runner_state(project, active_steps, executed, skipped,
                               aborted, exec_metrics, idx + 1)
            break
        idx += 1

    # ── Relatório final ───────────────────────────────────────────
    banner("Execução concluída", GREEN)
    print(f"\n  {GREEN}✅ Executados ({len(executed)}): {', '.join(executed) or '—'}{RESET}")
    print(f"  {YELLOW}⏭  Pulados   ({len(skipped)}): {', '.join(skipped) or '—'}{RESET}")
    if val_failed:
        print(f"  {RED}❌ Val-Fail  ({len(val_failed)}): {', '.join(val_failed)}{RESET}")
    if aborted:
        print(f"  {RED}🛑 Abortado em: {', '.join(aborted)}{RESET}")
    print(f"\n  {DIM}Outputs salvos em: projects/{project}/outputs/pipeline_runner/{RESET}\n")

    # Pendências acumuladas: a esteira nunca travou, então este é o único canal
    # que impede uma degradação de virar silêncio.
    _write_remediation_report(project)
    _print_remediation_summary(project)

    # ── Métricas de execução ──────────────────────────────────────
    # Ponto único de fecho para full, partial e resumed: todo caminho do laço
    # — conclusão, aborto, pulo, degradação, break por insumo ausente — cai
    # aqui. `finalized` impede que o handler de interrupção do __main__
    # sobrescreva este documento com um veredito de interrupção.
    _final_metrics = write_execution_metrics(
        project,
        execution_id=_execution_id,
        execution_mode=_RUN_CTX.get("execution_mode", EXEC_MODE_FULL),
        execution_status=execution_status_label(
            executed, skipped, aborted, val_failed,
            completed=idx >= len(active_steps)),
        start_ts=_pipeline_start_ts,
        end_ts=time.time(),
        exec_metrics=exec_metrics,
        executed=executed, skipped=skipped, aborted=aborted,
        val_failed=val_failed,
    )
    # Só depois do veredito final: `finalized` congela o arquivo contra um
    # flush tardio ou o handler de interrupção do __main__.
    _RUN_CTX["finalized"] = True
    if _final_metrics:
        _tokens = sum(_metric_int(m.get("inp_tokens")) + _metric_int(m.get("resp_tokens"))
                      for m in exec_metrics.values() if isinstance(m, dict))
        print(f"  {CYAN}📈 Métricas: {_final_metrics}{RESET}")
        print(f"  {DIM}   {len(exec_metrics)} fase(s) · {_tokens:,} tokens · "
              f"{_hhmmss(time.time() - _pipeline_start_ts)}{RESET}")

    # ── Resumo de artefatos + quadro de contexto ──────────────────
    print_final_summary(project, executed, skipped, aborted, active_steps, exec_metrics,
                        val_failed=val_failed)

    _write_status_html(project, active_steps, executed, skipped, aborted,
                       start_ts=_pipeline_start_ts, exec_metrics=exec_metrics, done=True,
                       val_failed=val_failed)
    print(f"\n  {GREEN}📊 Dashboard final: {_status_html.as_uri()}{RESET}")

    # ── Arquivar estado de execução ───────────────────────────────
    # Se a execução terminou normalmente (sem aborto), move o runner-state.json
    # para runner-state-done.json. Se houve aborto, mantém o arquivo para retomada.
    all_done = len(aborted) == 0 and idx >= len(active_steps)
    _finalize_runner_state(project, success=all_done)

    # ── Encerra proxy headroom se foi iniciado pelo pipeline ──────
    if headroom_proc and headroom_proc.poll() is None:
        print(f"  {DIM}[Headroom] Encerrando proxy (PID {headroom_proc.pid})...{RESET}")
        headroom_proc.terminate()
        try:
            headroom_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            headroom_proc.kill()
        print(f"  {DIM}[Headroom] Proxy encerrado.{RESET}")


def _abortar_com_mensagem(exc: BaseException) -> int:
    """Último recurso: transforma exceção não tratada em mensagem objetiva.

    Um defeito NO tratamento de erro não pode ser a última coisa que o operador
    lê — foi exatamente isso que aconteceu quando `on_fail` (nome inexistente
    neste escopo) estourou dentro do `except` que degradava uma tool reprovada:
    o `NameError` do handler soterrou a falha real, que já estava explicada na
    tela logo acima. Aqui o traceback vira anexo, não manchete.
    """
    print(f"\n{RED}{'═' * 72}{RESET}")
    print(f"{RED}{BOLD}  ERRO INTERNO DO AVA PIPELINE RUNNER{RESET}")
    print(f"{RED}{'═' * 72}{RESET}")
    print(f"  {type(exc).__name__}: {exc}")
    print("")
    print(f"{YELLOW}{BOLD}  O QUE ISSO SIGNIFICA{RESET}")
    for linha in textwrap.wrap(
        "Falha do próprio runner, não da fase que estava rodando. Se um bloco "
        "de erro (FALHA EM ...) apareceu acima, ELE é o problema de verdade — "
        "resolva-o primeiro. O estado do run foi preservado em disco.", width=68
    ):
        print(f"{YELLOW}    {linha}{RESET}")
    print("")
    print(f"{CYAN}{BOLD}  PRÓXIMO PASSO{RESET}")
    print(f"{CYAN}    Retome de onde parou com --resume; se repetir, reporte o "
          f"trace abaixo.{RESET}")
    print("")
    print(f"{DIM}  ── trace (para quem for corrigir o runner) ──{RESET}")
    tb = "".join(traceback.format_exception(
        type(exc), exc, exc.__traceback__)).rstrip()
    for linha in tb.splitlines():
        print(f"{DIM}  {linha}{RESET}")
    print(f"{RED}{'═' * 72}{RESET}")
    return 1


if __name__ == "__main__":
    _args = _parse_cli()
    if _args.list_agents:
        sys.exit(_listar_agentes_cli(_args))
    if _args.agent:
        sys.exit(_despachar_agente_unico(_args))
    # `--phase` sozinho seleciona etapa. Sem isto ele era aceito pelo parser e
    # ignorado, e o operador caía no menu interativo achando que a flag falhou.
    if _args.phase:
        sys.exit(_despachar_fase(_args))
    try:
        main(project_preselecionado=_args.project)
    except KeyboardInterrupt:
        # Grava antes da mensagem: as fases já concluídas custaram inferência
        # real, e o relatório é o único registro persistente desse consumo.
        _m = write_metrics_from_run_ctx("interrupted")
        print(f"\n{YELLOW}  Interrompido pelo operador. "
              f"Retome com --resume.{RESET}")
        if _m:
            print(f"{DIM}  Métricas parciais: {_m}{RESET}")
        sys.exit(130)
    except Exception as _exc:
        write_metrics_from_run_ctx("failed")
        sys.exit(_abortar_com_mensagem(_exc))
