#!/usr/bin/env python3
"""
AVA Fabric — Razão de progresso da execução DevOps (F5 · trigger DE)
=====================================================================
Mantém ``projects/{p}/outputs/tobe/devops/task-devops-progress.json``: uma linha
por tarefa de execução DevOps, com o estado persistido em disco e movido por
transição explícita. É a fonte de verdade do laço iterativo (padrão Ralph
Wiggum) que substitui o despacho único da F5.

O defeito que este módulo corrige
---------------------------------
A F5 declarava, em ``src/shared/data/ava-pipeline.yaml``::

    inputs:
      mandatory:
        - path: "outputs/tobe/source-code"     # ← DIRETÓRIO

``context_manifest._expand()`` expande diretório com ``rglob("*")``, e
``_resolve_declared()`` injeta o corpo de cada arquivo encontrado. Com a F4 já
concluída, ``outputs/tobe/source-code`` contém a aplicação inteira — backend,
frontend, lock files, assets. O resultado medido em produção::

    BadRequestError: Error code: 400 — invalid_request_error
    prompt is too long: 3924457 tokens > 1000000 maximum

Nenhuma tarefa de DevOps precisa do código-fonte no prompt: IaC, CI, CD,
containerização, custo e observabilidade são derivados dos **planos**
(``devops-plan.md``, ``environments-plan.md``) e do ``project-config.yaml``.
O que o agente precisa saber do código é o *caminho*, não o *conteúdo*.

O que este módulo troca
-----------------------
Um despacho único, com todo o contexto do projeto, por **N despachos pequenos** —
um por tarefa —, cada um com o contexto mínimo daquela tarefa. O estado vive em
disco, não na memória da conversa: cada iteração recarrega o arquivo, escolhe a
próxima tarefa elegível, executa e persiste antes de seguir.

Contrato do arquivo
-------------------
::

    {
      "schema_version": "1.0.0",
      "project": "Meu-ERP",
      "phase": "F5",
      "agent": "ava-devops-orchestrator",
      "trigger": "DE",
      "created_at": "...", "updated_at": "...",
      "source_plans": ["outputs/tobe/devops/devops-plan.md", ...],
      "iterations": 0,
      "tasks": [ { ...ver `new_task()`... } ]
    }

Status permitidos: ``pending``, ``in_progress``, ``completed``, ``failed``,
``skipped``, ``blocked``. Terminais: ``completed``, ``skipped``, ``blocked``.

Invariantes
-----------
* Escrita **atômica**: tmp no mesmo diretório → ``json.loads`` de validação →
  ``os.replace``. Interrupção no meio da gravação não corrompe o arquivo.
* Tarefa ``completed`` nunca é reexecutada nem recriada.
* Tarefa ``failed`` só é retentada enquanto ``attempts < max_attempts``.
* Nada de segredo entra no arquivo: ``sanitize()`` roda em toda mensagem de erro
  e em todo resumo antes da persistência.
* Caminhos sempre em POSIX (``/``) — inclusive nas constantes Python, para que
  nenhuma sequência como ``\\t`` seja interpretada como tabulação.

Uso
---
    python src/shared/tools/devops_task_ledger.py -p Meu-ERP --init
    python src/shared/tools/devops_task_ledger.py -p Meu-ERP --summary
    python src/shared/tools/devops_task_ledger.py -p Meu-ERP --next

Exit codes
----------
    0 — ok      1 — nada pendente / razão inconsistente      2 — erro de configuração
"""
from __future__ import annotations

import datetime
import fnmatch
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

# SCRIPT_DIR = src/shared/tools → parents: shared, src, repo
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.0.0"

# ─── Constantes de execução ──────────────────────────────────────────────────

#: Teto de tentativas por tarefa. Acima disso a tarefa é **exposta**, não
#: retentada para sempre — retry silencioso esconde o defeito real.
MAX_ATTEMPTS = 3

#: Teto global de iterações do laço. Existe para que o laço NUNCA rode
#: indefinidamente, mesmo com um bug de transição de estado. Dimensionado com
#: folga: ~13 tarefas × 3 tentativas + margem.
MAX_ITERATIONS = 60

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUS_BLOCKED = "blocked"

STATUSES = frozenset({
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED,
    STATUS_FAILED, STATUS_SKIPPED, STATUS_BLOCKED,
})

#: Estados dos quais uma tarefa não volta. `failed` NÃO é terminal enquanto
#: `attempts < max_attempts`.
TERMINAL = frozenset({STATUS_COMPLETED, STATUS_SKIPPED, STATUS_BLOCKED})

# ─── Caminhos (sempre POSIX) ─────────────────────────────────────────────────

DEVOPS_DIR_REL = "outputs/tobe/devops"
PROGRESS_REL = "outputs/tobe/devops/task-devops-progress.json"

#: Insumos iniciais da F5/DE. Lista fechada — é ela que impede o diretório de
#: código-fonte de voltar ao prompt.
PLAN_INPUTS: tuple[str, ...] = (
    "context/project-config.yaml",
    "outputs/tobe/devops/devops-plan.md",
    "outputs/tobe/devops/environments-plan.md",
)

#: Nunca entram no contexto do ava-devops-orchestrator, nem como insumo inicial
#: nem por leitura sob demanda. `context/shared-context.md` e o blueprint estão
#: aqui porque duplicam, em prosa longa, o que os planos de DevOps já decidiram.
FORBIDDEN_INPUTS: tuple[str, ...] = (
    "context/shared-context.md",
    "outputs/tobe/docs/architecture-blueprint.md",
    "outputs/tobe/source-code",
    "outputs/tobe/source-code/frontend",
    "outputs/tobe/source-code/backend",
)

#: Sufixos de texto que podem ser lidos sob demanda de `outputs/tobe/devops/`.
PLAN_SUFFIXES = (".md", ".yaml", ".yml", ".json", ".txt")

# ─── Orçamento de contexto ───────────────────────────────────────────────────

#: Chars por token na estimativa. 4 é a média de prosa; aqui usamos 3 de
#: propósito. O payload que estourou em produção media ~2,3 chars/token (YAML,
#: lock files e código minificado tokenizam muito pior que prosa), e uma
#: estimativa otimista é exatamente o que deixa passar o request que falha.
CHARS_PER_TOKEN = 3

#: Fração da janela utilizável como INPUT. O restante é margem de segurança:
#: instruções, resposta do modelo, uso de ferramenta e metadados de execução.
CTX_INPUT_SAFETY = 0.80

#: Reserva fixa, além da saída, para overhead que não medimos aqui.
CTX_RESERVE_TOKENS = 32_000

#: Tetos por peça do contexto mínimo de uma tarefa.
TASK_CONFIG_CHARS = 20_000
TASK_PLAN_CHARS = 40_000
TASK_DEP_CHARS = 4_000
DERIVATION_PLAN_CHARS = 80_000

#: Mensagens de erro que significam "o request não coube". Comparadas em
#: minúsculas contra `str(exc)`.
CONTEXT_LIMIT_MARKERS: tuple[str, ...] = (
    "prompt is too long",
    "context length exceeded",
    "maximum context length",
    "input tokens exceed",
    "input length and `max_tokens` exceed",
    "request too large",
    "too many total text bytes",
)


class ContextBudgetExceeded(Exception):
    """O contexto montado não cabe no orçamento — o request não é enviado.

    Levantada ANTES de `client.messages.stream`. É o guard que transforma um
    400 pago da API num erro local de custo zero.
    """

    def __init__(self, message: str, *, estimated: int, budget: int) -> None:
        super().__init__(message)
        self.estimated = int(estimated)
        self.budget = int(budget)


class DevOpsLedgerError(Exception):
    """Erro de uso do razão. O CLI converte em exit 2."""


# ─── Espinha de tarefas da execução DevOps (Momento 2 · DE) ──────────────────
# Derivada da tabela `## Agent Team Gerenciado` e da sequência 2.2–2.10 de
# `devops-agents/agents/orchestrator-devops.md`. Cada linha vira UMA chamada ao
# modelo, com o spec do sub-agente como skill — 3,5KB a 59KB, contra os 19KB do
# orquestrador MAIS todo o contexto do projeto no despacho único de antes.
_SPEC_DIR = "src/modules/ava-fabric-agents/devops-agents/agents"

TASK_BACKBONE: tuple[dict[str, Any], ...] = (
    {
        "id": "DEVOPS-001",
        "title": "IaC base — sizing de infraestrutura e esqueleto de provisionamento",
        "description": ("Executar o agente de IaC: derivar o sizing a partir do "
                        "devops-plan e do environments-plan e gravar os artefatos "
                        "de infraestrutura base."),
        "agent": "ava-devops-iac",
        "spec": f"{_SPEC_DIR}/iac-agent.md",
        "dependencies": [],
        "keywords": ("iac", "infra", "infraestrutura", "terraform", "bicep", "sizing"),
        "output_globs": ("outputs/tobe/iac/**", "outputs/tobe/infra/**",
                         "outputs/tobe/docs/infra-sizing.md"),
    },
    {
        "id": "DEVOPS-002",
        "title": "CI — pipeline de integração contínua",
        "description": ("Executar o agente de CI: gerar o pipeline de build, teste "
                        "e análise estática conforme a estratégia do devops-plan."),
        "agent": "ava-devops-ci",
        "spec": f"{_SPEC_DIR}/ci-agent.md",
        "dependencies": ["DEVOPS-001"],
        "keywords": ("ci", "build", "integração contínua", "continuous integration",
                     "pipeline", "sonar"),
        "output_globs": ("outputs/tobe/iac/ci/**", "outputs/tobe/devops/ci/**",
                         "outputs/tobe/source-code/.github/workflows/*.yml",
                         "outputs/tobe/source-code/azure-pipelines.yml",
                         "outputs/tobe/source-code/sonar-project.properties"),
    },
    {
        "id": "DEVOPS-003",
        "title": "CD — pipeline de entrega e validação pós-deploy",
        "description": ("Executar o agente de CD: gerar o pipeline de deploy por "
                        "ambiente e a validação pós-deploy descritos no "
                        "environments-plan."),
        "agent": "ava-devops-cd",
        "spec": f"{_SPEC_DIR}/cd-agent.md",
        "dependencies": ["DEVOPS-002"],
        "keywords": ("cd", "deploy", "entrega contínua", "continuous delivery",
                     "release", "ambiente", "environment"),
        "output_globs": ("outputs/tobe/iac/cd/**", "outputs/tobe/devops/cd/**"),
    },
    {
        "id": "DEVOPS-004",
        "title": "Containerização — Dockerfiles e composição de serviços",
        "description": ("Executar o agente de containerização: gerar Dockerfiles, "
                        ".dockerignore e docker-compose por ambiente. Trabalhar a "
                        "partir dos serviços declarados nos planos — NÃO carregar o "
                        "código-fonte no contexto."),
        "agent": "ava-devops-containerize",
        "spec": f"{_SPEC_DIR}/containerize-agent.md",
        "dependencies": ["DEVOPS-001"],
        "keywords": ("container", "docker", "dockerfile", "compose", "imagem", "image"),
        "output_globs": ("outputs/tobe/devops/Dockerfile*",
                         "outputs/tobe/devops/docker/**",
                         "outputs/tobe/source-code/**/Dockerfile",
                         "outputs/tobe/source-code/docker-compose*.yml"),
    },
    {
        "id": "DEVOPS-005",
        "title": "IaC específico de nuvem — provisionamento do cloud provider",
        "description": ("Executar o agente de IaC do provedor declarado em "
                        "project-config.yaml (cloud_provider). Gera os módulos de "
                        "provisionamento em outputs/tobe/infra/."),
        "agent": "ava-devops-iac-azure",
        "spec": f"{_SPEC_DIR}/iac-azure-agent.md",
        "dependencies": ["DEVOPS-001"],
        "keywords": ("azure", "aws", "gcp", "kubernetes", "k8s", "cloud", "provider"),
        "output_globs": ("outputs/tobe/infra/**",),
        "cloud_specific": True,
    },
    {
        "id": "DEVOPS-006",
        "title": "Estimativa de custo da infraestrutura",
        "description": ("Executar o agente de estimativa de custo sobre o sizing e "
                        "os módulos de provisionamento já gerados."),
        "agent": "ava-devops-cost-estimate",
        "spec": f"{_SPEC_DIR}/cost-estimate-agent.md",
        "dependencies": ["DEVOPS-005"],
        "keywords": ("custo", "cost", "estimativa", "budget", "finops", "pricing"),
        "output_globs": ("outputs/tobe/docs/cost-estimate.md",),
    },
    {
        "id": "DEVOPS-007",
        "title": "Monitoramento e observabilidade",
        "description": ("Executar o agente de observabilidade: alertas, dashboards, "
                        "health checks e consultas conforme os SLOs dos planos."),
        "agent": "ava-devops-monitoring-observability",
        "spec": f"{_SPEC_DIR}/monitoring-observability-agent.md",
        "dependencies": ["DEVOPS-005"],
        "keywords": ("monitor", "observabilidade", "observability", "alerta", "alert",
                     "dashboard", "slo", "health check", "telemetria"),
        "output_globs": ("outputs/tobe/observability/**",),
    },
    {
        "id": "DEVOPS-008",
        "title": "Comparação de versões — relatório de paridade",
        "description": ("Executar o agente de comparação de versões sobre os "
                        "resultados de execução disponíveis."),
        "agent": "ava-devops-compare-version",
        "spec": f"{_SPEC_DIR}/compare-version-agent.md",
        "dependencies": ["DEVOPS-003"],
        "keywords": ("paridade", "parity", "comparação", "compare", "versão", "version"),
        "output_globs": ("outputs/tobe/parity/**",
                         "outputs/tobe/wave-comparison-report.md",
                         "outputs/tobe/parity-test-report.md"),
    },
    {
        "id": "DEVOPS-009",
        "title": "Pacote de aprovação de release",
        "description": ("Executar o agente de package approval: consolidar o pacote "
                        "de aprovação da wave com os artefatos de CI/CD e paridade."),
        "agent": "ava-devops-package-approval",
        "spec": f"{_SPEC_DIR}/package-approval-agent.md",
        "dependencies": ["DEVOPS-003", "DEVOPS-004"],
        "keywords": ("aprovação", "approval", "pacote", "package", "release", "wave"),
        "output_globs": ("outputs/tobe/wave-*-package-approval.md",),
    },
    {
        "id": "DEVOPS-010",
        "title": "Build-cycle IaC — esqueleto incremental por wave",
        "description": ("Executar o agente de build-cycle IaC. Só se aplica quando "
                        "project-config.yaml declara pipeline_mode: build-cycle."),
        "agent": "ava-build-cycle-iac",
        "spec": f"{_SPEC_DIR}/build-cycle-iac-agent.md",
        "dependencies": ["DEVOPS-001"],
        "keywords": ("build-cycle", "wave", "incremental"),
        "output_globs": ("outputs/tobe/iac/wave-*/**",),
        "build_cycle_only": True,
    },
)

#: Spec do IaC de nuvem por provedor. Chave em minúsculas.
CLOUD_SPEC = {
    "azure": ("ava-devops-iac-azure", f"{_SPEC_DIR}/iac-azure-agent.md"),
    "aws": ("ava-devops-iac-aws", f"{_SPEC_DIR}/iac-aws-agent.md"),
    "gcp": ("ava-devops-iac-gcp", f"{_SPEC_DIR}/iac-gcp-agent.md"),
    "k8s-native": ("ava-devops-iac-k8s-native", f"{_SPEC_DIR}/iac-k8s-native-agent.md"),
}


# ─── Sanitização ─────────────────────────────────────────────────────────────

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # chave=valor com nome sensível (yaml, env, querystring, json)
    (re.compile(r'(?i)\b(pass(?:word|wd)?|pwd|secret|token|api[_-]?key|'
                r'client[_-]?secret|access[_-]?key|private[_-]?key|'
                r'connection[_-]?string|conn[_-]?str|sas[_-]?token)\b'
                r'(\s*[:=]\s*)(?:"[^"]*"|\'[^\']*\'|[^\s,;}\]]+)'),
     r'\1\2***REDACTED***'),
    # connection strings ADO.NET / Azure Storage
    (re.compile(r'(?i)\b(AccountKey|SharedAccessSignature|Password|Pwd|'
                r'User\s*ID|UID)\s*=\s*[^;\s"\']+'),
     r'\1=***REDACTED***'),
    (re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/\-]{8,}=*'), 'Bearer ***REDACTED***'),
    # JWT
    (re.compile(r'\beyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{4,}\b'),
     '***REDACTED-JWT***'),
    # tokens de provedor conhecidos
    (re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{16,}\b'),
     '***REDACTED-TOKEN***'),
    (re.compile(r'\bxox[abposr]-[A-Za-z0-9\-]{10,}\b'), '***REDACTED-TOKEN***'),
    # URL com credencial embutida
    (re.compile(r'\b([a-z][a-z0-9+.\-]*://)[^/\s:@]+:[^/\s@]+@'), r'\1***REDACTED***@'),
)

#: Teto de uma mensagem persistida. Erro longo vira ruído no arquivo de estado.
SANITIZE_LIMIT = 2_000


def sanitize(text: Any, limit: int = SANITIZE_LIMIT) -> str:
    """Remove segredo conhecido e corta no limite. Nunca levanta.

    Aplicada a TODA mensagem de erro e a TODO resumo antes de encostar no
    arquivo de progresso ou no log.
    """
    if text is None:
        return ""
    out = str(text)
    for pattern, replacement in _SECRET_PATTERNS:
        try:
            out = pattern.sub(replacement, out)
        except re.error:  # pragma: no cover — regex fixa, mas nunca derrubar
            continue
    out = out.replace("\r\n", "\n").strip()
    if len(out) > limit:
        out = out[:limit] + " […]"
    return out


# ─── Caminhos ────────────────────────────────────────────────────────────────

def project_dir(project: str, repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / "projects" / project


def devops_dir(project: str, repo_root: Path | None = None) -> Path:
    return project_dir(project, repo_root) / DEVOPS_DIR_REL


def progress_path(project: str, repo_root: Path | None = None) -> Path:
    return project_dir(project, repo_root) / PROGRESS_REL


def now_iso() -> str:
    """Timestamp ISO 8601 em UTC, com segundos — o formato do restante da esteira."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# ─── Escrita atômica ─────────────────────────────────────────────────────────

#: `os.replace` no Windows pode falhar transitoriamente (antivirus,
#: indexador). Poucas tentativas curtas resolvem sem abrir mao da atomicidade.
_REPLACE_RETRIES = 5
_REPLACE_BACKOFF_S = 0.05


def atomic_write_json(path: Path, payload: dict[str, Any]) -> Path:
    """Grava JSON de forma resistente a interrupção.

    tmp no MESMO diretório (``os.replace`` só é atômico dentro do mesmo volume)
    → serializa → relê e valida → ``os.replace``. Se o processo morrer no meio,
    o arquivo original continua íntegro e o tmp fica órfão, nunca meio-escrito.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    # Validação antes de tocar no original: JSON inválido nunca substitui um válido.
    json.loads(texto)

    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp",
                                    dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto)
            fh.flush()
            os.fsync(fh.fileno())
        json.loads(tmp.read_text(encoding="utf-8"))   # relê o que foi para o disco
        # `os.replace` no Windows falha com WinError 5 quando antivírus, indexador
        # ou o próprio explorer ainda seguram o destino por alguns milissegundos.
        # A troca continua atômica; só precisa de paciência.
        for tentativa in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if tentativa == _REPLACE_RETRIES - 1:
                    raise
                time.sleep(_REPLACE_BACKOFF_S * (tentativa + 1))
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return path


def read_progress(path: Path) -> dict[str, Any] | None:
    """Lê o arquivo de progresso. ``None`` quando ausente ou ilegível."""
    if not path.is_file():
        return None
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return dados if isinstance(dados, dict) else None


def save_progress(path: Path, progress: dict[str, Any]) -> Path:
    progress["updated_at"] = now_iso()
    return atomic_write_json(path, progress)


# ─── Tarefas ─────────────────────────────────────────────────────────────────

def new_task(task_id: str, title: str, description: str, *,
             source_plan: str, agent: str = "", spec: str = "",
             dependencies: Iterable[str] = (),
             output_globs: Iterable[str] = (),
             max_attempts: int = MAX_ATTEMPTS) -> dict[str, Any]:
    """Uma tarefa no estado inicial. A forma é o contrato do arquivo."""
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "source_plan": source_plan,
        "dependencies": list(dependencies),
        "status": STATUS_PENDING,
        "attempts": 0,
        "max_attempts": int(max_attempts),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "output_artifacts": [],
        # Campos operacionais — fora do mínimo exigido, usados pelo laço.
        "agent": agent,
        "spec": spec,
        "output_globs": list(output_globs),
        "context_level": 0,
        "last_request_digest": None,
    }


def _yaml_scalar(text: str, key: str, default: str = "") -> str:
    """Lê um escalar de topo do project-config sem exigir PyYAML.

    Deliberadamente ingênuo: só precisamos de `cloud_provider` e
    `pipeline_mode`, ambos escalares simples. Falha silenciosa devolve o default.
    """
    match = re.search(rf'(?im)^\s*{re.escape(key)}\s*:\s*["\']?([A-Za-z0-9_.\-]+)["\']?\s*$',
                      text or "")
    return match.group(1).strip() if match else default


#: Nome publico: o runner le `cloud_provider` e `pipeline_mode` por aqui.
read_config_scalar = _yaml_scalar


_HEADING = re.compile(r'(?m)^(#{2,4})\s+(.+?)\s*$')

#: Cabeçalho de plano que descreve trabalho a executar. Sem isso, "Contexto",
#: "Glossário" e "Referências" virariam tarefa.
_ACTIONABLE_HEADING = re.compile(
    r'(?i)\b(pipeline|ci|cd|deploy|deployment|infra|infraestrutura|iac|terraform|'
    r'bicep|container|docker|kubernetes|k8s|ambiente|environment|observabilidade|'
    r'observability|monitor|alerta|alert|backup|dr|disaster|secret|segredo|'
    r'rollback|scaling|escalabilidade|custo|cost|rede|network|gateway|'
    r'provisionamento|provisioning|runbook|release)\b')


def plan_headings(text: str) -> list[str]:
    """Cabeçalhos H2–H4 do plano, na ordem do documento."""
    return [m.group(2).strip() for m in _HEADING.finditer(text or "")]


def tasks_from_plan(rel_path: str, text: str, *, start_index: int,
                    known_titles: Iterable[str] = (),
                    covered_keywords: Iterable[str] = ()) -> list[dict[str, Any]]:
    """Tarefas extras derivadas dos cabeçalhos acionáveis de um plano.

    A espinha (`TASK_BACKBONE`) cobre a sequência canônica do trigger DE. Esta
    função é o que faz o arquivo refletir **este** projeto: um plano que decidiu
    algo fora da sequência canônica (ex.: "Estratégia de backup e DR") vira uma
    tarefa própria em vez de sumir.

    `covered_keywords` traz as palavras-chave das tarefas de espinha já
    incluídas. Um cabeçalho «Pipeline de CI» descreve trabalho que DEVOPS-002 já
    faz; virar tarefa também seria agendar a mesma execução duas vezes.
    """
    ja_visto = {t.strip().casefold() for t in known_titles}
    cobertas = {k.casefold() for k in covered_keywords}
    tarefas: list[dict[str, Any]] = []
    indice = start_index
    for titulo in plan_headings(text):
        if not _ACTIONABLE_HEADING.search(titulo):
            continue
        chave = titulo.casefold()
        if chave in ja_visto:
            continue
        if any(k in chave for k in cobertas):
            continue                      # já coberto pela espinha
        ja_visto.add(chave)
        indice += 1
        tarefas.append(new_task(
            f"DEVOPS-{indice:03d}",
            titulo,
            (f"Implementar o que a seção «{titulo}» de {rel_path} decide. "
             f"Ler apenas essa seção do plano; não carregar o plano inteiro "
             f"nem o código-fonte."),
            source_plan=rel_path,
            agent="ava-devops-orchestrator",
            spec=f"{_SPEC_DIR}/orchestrator-devops.md",
            dependencies=[],
            output_globs=("outputs/tobe/devops/**", "outputs/tobe/iac/**"),
        ))
    return tarefas


def derive_tasks(plans: dict[str, str], *, cloud_provider: str = "azure",
                 pipeline_mode: str = "") -> list[dict[str, Any]]:
    """Lista de tarefas a partir dos planos de DevOps.

    Espinha canônica (sequência 2.2–2.10 do orquestrador), condicionada pelo
    `cloud_provider` e pelo `pipeline_mode` do project-config, mais os
    cabeçalhos acionáveis que os planos trouxerem além dela.
    """
    provider = (cloud_provider or "azure").strip().lower()
    build_cycle = (pipeline_mode or "").strip().lower() == "build-cycle"

    plano_principal = next(
        (rel for rel in PLAN_INPUTS if rel.endswith("devops-plan.md") and rel in plans),
        PLAN_INPUTS[1])
    texto_total = "\n".join(plans.values()).casefold()

    tarefas: list[dict[str, Any]] = []
    for modelo in TASK_BACKBONE:
        if modelo.get("build_cycle_only") and not build_cycle:
            continue

        agent = str(modelo["agent"])
        spec = str(modelo["spec"])
        if modelo.get("cloud_specific"):
            if provider not in CLOUD_SPEC:
                # Provedor não suportado não vira tarefa fantasma: some da lista
                # e o motivo fica no `source_plan` das demais.
                continue
            agent, spec = CLOUD_SPEC[provider]

        # O plano é quem manda: uma tarefa cuja palavra-chave não aparece em
        # nenhum plano entra como `skipped`, não como trabalho inventado.
        relevante = any(k in texto_total for k in modelo.get("keywords", ()))
        tarefa = new_task(
            str(modelo["id"]), str(modelo["title"]), str(modelo["description"]),
            source_plan=plano_principal,
            agent=agent, spec=spec,
            dependencies=modelo.get("dependencies", ()),
            output_globs=modelo.get("output_globs", ()),
        )
        if not relevante:
            tarefa["status"] = STATUS_SKIPPED
            tarefa["completed_at"] = now_iso()
            tarefa["result"] = {
                "success": True,
                "summary": ("nenhum plano de DevOps menciona este escopo — "
                            "pulada em vez de executada sem fonte"),
            }
        tarefas.append(tarefa)

    conhecidos = [t["title"] for t in tarefas]
    ids_incluidos = {t["id"] for t in tarefas}
    cobertas = tuple(k for modelo in TASK_BACKBONE if modelo["id"] in ids_incluidos
                     for k in modelo.get("keywords", ()))
    proximo = max((int(t["id"].rsplit("-", 1)[1]) for t in tarefas), default=0)
    for rel, texto in plans.items():
        if rel.endswith(".yaml") or rel.endswith(".yml"):
            continue                      # project-config não é plano
        extras = tasks_from_plan(rel, texto, start_index=proximo,
                                 known_titles=conhecidos,
                                 covered_keywords=cobertas)
        tarefas.extend(extras)
        conhecidos.extend(t["title"] for t in extras)
        proximo += len(extras)

    return tarefas


def merge_tasks(existentes: list[dict[str, Any]],
                derivadas: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Funde a lista derivada dos planos com a que já está em disco.

    Regras, nesta ordem:
      * tarefa já registrada é **preservada** — status, tentativas, resultado e
        artefatos vencem qualquer coisa que a derivação diga;
      * tarefa nova (id inédito) é acrescentada como `pending`;
      * `in_progress` de um run interrompido volta a `pending`, para que o laço
        a retome em vez de deixá-la parada para sempre;
      * nada é removido: uma tarefa que sumiu dos planos continua no arquivo com
        o histórico dela.
    """
    por_id = {str(t.get("id")): t for t in existentes if t.get("id")}
    novos: list[str] = []

    for derivada in derivadas:
        tid = str(derivada["id"])
        atual = por_id.get(tid)
        if atual is None:
            por_id[tid] = derivada
            novos.append(tid)
            continue
        # Preserva o que é estado; atualiza só metadado de despacho, que pode
        # ter mudado com o project-config (ex.: troca de cloud_provider).
        for campo in ("agent", "spec", "output_globs", "source_plan"):
            if derivada.get(campo):
                atual[campo] = derivada[campo]
        atual.setdefault("max_attempts", MAX_ATTEMPTS)
        atual.setdefault("dependencies", list(derivada.get("dependencies") or []))

    for tarefa in por_id.values():
        if tarefa.get("status") == STATUS_IN_PROGRESS:
            tarefa["status"] = STATUS_PENDING
            tarefa["started_at"] = None
        if tarefa.get("status") not in STATUSES:
            tarefa["status"] = STATUS_PENDING

    ordenadas = sorted(por_id.values(), key=lambda t: str(t.get("id")))
    return ordenadas, novos


def new_progress(project: str, tasks: list[dict[str, Any]], *,
                 source_plans: Iterable[str] = PLAN_INPUTS) -> dict[str, Any]:
    agora = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "phase": "F5",
        "agent": "ava-devops-orchestrator",
        "trigger": "DE",
        "created_at": agora,
        "updated_at": agora,
        "source_plans": list(source_plans),
        "iterations": 0,
        "tasks": tasks,
    }


def load_or_create(project: str, plans: dict[str, str], *,
                   repo_root: Path | None = None,
                   cloud_provider: str = "azure",
                   pipeline_mode: str = "") -> tuple[dict[str, Any], list[str]]:
    """Carrega o arquivo de progresso, criando-o na primeira execução.

    Devolve ``(progress, ids_novos)``. Sempre persiste — a retomada precisa que
    o arquivo exista em disco mesmo que nenhuma tarefa tenha rodado ainda.
    """
    caminho = progress_path(project, repo_root)
    derivadas = derive_tasks(plans, cloud_provider=cloud_provider,
                             pipeline_mode=pipeline_mode)

    existente = read_progress(caminho)
    if existente is None:
        progresso = new_progress(project, derivadas)
        novos = [str(t["id"]) for t in derivadas]
    else:
        progresso = existente
        progresso.setdefault("schema_version", SCHEMA_VERSION)
        progresso.setdefault("project", project)
        progresso.setdefault("phase", "F5")
        progresso.setdefault("agent", "ava-devops-orchestrator")
        progresso.setdefault("trigger", "DE")
        progresso.setdefault("created_at", now_iso())
        progresso.setdefault("iterations", 0)
        progresso["source_plans"] = list(PLAN_INPUTS)
        tarefas, novos = merge_tasks(list(progresso.get("tasks") or []), derivadas)
        progresso["tasks"] = tarefas

    save_progress(caminho, progresso)
    return progresso, novos


# ─── Seleção e dependências ──────────────────────────────────────────────────

def tasks_by_id(progress: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(t.get("id")): t for t in progress.get("tasks") or [] if t.get("id")}


def is_retryable(task: dict[str, Any]) -> bool:
    """`failed` só volta à fila enquanto ainda há tentativa disponível."""
    return (task.get("status") == STATUS_FAILED
            and int(task.get("attempts", 0)) < int(task.get("max_attempts", MAX_ATTEMPTS)))


def is_finished(task: dict[str, Any]) -> bool:
    """Terminou de vez: terminal, ou `failed` sem tentativa restante."""
    status = task.get("status")
    if status in TERMINAL:
        return True
    return status == STATUS_FAILED and not is_retryable(task)


def dependency_state(task: dict[str, Any],
                     por_id: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    """``("ready"|"waiting"|"blocked", [ids que explicam o estado])``.

    * ``blocked`` — alguma dependência é `blocked`, `failed` sem tentativa
      restante, ou não existe no arquivo.
    * ``waiting`` — alguma dependência ainda pode concluir.
    * ``ready``   — todas `completed` (ou `skipped`, que é uma conclusão
      deliberada e não impede a sucessora).
    """
    bloqueiam: list[str] = []
    aguardam: list[str] = []
    for dep_id in task.get("dependencies") or []:
        dep = por_id.get(str(dep_id))
        if dep is None:
            bloqueiam.append(str(dep_id))
            continue
        status = dep.get("status")
        if status in (STATUS_COMPLETED, STATUS_SKIPPED):
            continue
        if status == STATUS_BLOCKED or (status == STATUS_FAILED and not is_retryable(dep)):
            bloqueiam.append(str(dep_id))
        else:
            aguardam.append(str(dep_id))
    if bloqueiam:
        return "blocked", bloqueiam
    if aguardam:
        return "waiting", aguardam
    return "ready", []


def select_next_task(progress: dict[str, Any]) -> dict[str, Any] | None:
    """Próxima tarefa elegível, na ordem do arquivo. ``None`` quando não há.

    Elegível = `pending`, ou `failed` com tentativa restante, com todas as
    dependências concluídas. `completed` nunca é reexecutada.
    """
    por_id = tasks_by_id(progress)
    for tarefa in progress.get("tasks") or []:
        status = tarefa.get("status")
        if status == STATUS_PENDING or is_retryable(tarefa):
            estado, _ = dependency_state(tarefa, por_id)
            if estado == "ready":
                return tarefa
    return None


def mark_blocked_tasks(progress: dict[str, Any]) -> list[str]:
    """Fecha o que não tem mais como rodar. Devolve os ids bloqueados agora.

    Chamada quando o laço não encontra tarefa elegível: sem isso, uma tarefa
    cuja dependência falhou em definitivo ficaria `pending` para sempre e o
    arquivo mentiria sobre o estado da fase.
    """
    por_id = tasks_by_id(progress)
    bloqueados: list[str] = []
    for tarefa in progress.get("tasks") or []:
        if is_finished(tarefa) or tarefa.get("status") == STATUS_IN_PROGRESS:
            continue
        estado, culpados = dependency_state(tarefa, por_id)
        if estado == "blocked":
            tarefa["status"] = STATUS_BLOCKED
            tarefa["completed_at"] = now_iso()
            tarefa["error"] = {
                "type": "DependencyBlocked",
                "message": sanitize("dependência não concluída em definitivo: "
                                    + ", ".join(culpados)),
                "recoverable": False,
            }
            bloqueados.append(str(tarefa.get("id")))
    return bloqueados


def all_finished(progress: dict[str, Any]) -> bool:
    tarefas = progress.get("tasks") or []
    return bool(tarefas) and all(is_finished(t) for t in tarefas)


def progress_signature(progress: dict[str, Any]) -> str:
    """Impressão digital do estado. Igual entre duas iterações = sem progresso."""
    corpo = "|".join(
        f"{t.get('id')}:{t.get('status')}:{t.get('attempts', 0)}"
        for t in progress.get("tasks") or []
    )
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def summary_counts(progress: dict[str, Any]) -> dict[str, int]:
    contagem = {"total": 0, STATUS_PENDING: 0, STATUS_IN_PROGRESS: 0,
                STATUS_COMPLETED: 0, STATUS_FAILED: 0,
                STATUS_SKIPPED: 0, STATUS_BLOCKED: 0}
    for tarefa in progress.get("tasks") or []:
        contagem["total"] += 1
        status = str(tarefa.get("status"))
        if status in contagem:
            contagem[status] += 1
    return contagem


# ─── Transições ──────────────────────────────────────────────────────────────

def mark_in_progress(task: dict[str, Any]) -> dict[str, Any]:
    task["status"] = STATUS_IN_PROGRESS
    task["started_at"] = now_iso()
    task["completed_at"] = None
    task["attempts"] = int(task.get("attempts", 0)) + 1
    task["error"] = None
    return task


def mark_completed(task: dict[str, Any], summary: str,
                   artifacts: Iterable[str] = ()) -> dict[str, Any]:
    task["status"] = STATUS_COMPLETED
    task["completed_at"] = now_iso()
    task["result"] = {"success": True, "summary": sanitize(summary, 600)}
    task["error"] = None
    task["output_artifacts"] = [str(a).replace("\\", "/") for a in artifacts]
    return task


def mark_failed(task: dict[str, Any], *, error_type: str, message: str,
                recoverable: bool = True, summary: str = "") -> dict[str, Any]:
    """Registra a falha. Vira `blocked` quando esgota as tentativas."""
    esgotou = int(task.get("attempts", 0)) >= int(task.get("max_attempts", MAX_ATTEMPTS))
    task["status"] = STATUS_BLOCKED if esgotou else STATUS_FAILED
    task["completed_at"] = now_iso()
    task["result"] = {
        "success": False,
        "summary": sanitize(summary or f"tentativa {task.get('attempts', 0)} falhou", 600),
    }
    task["error"] = {
        "type": sanitize(error_type, 120) or "Exception",
        "message": sanitize(message),
        "recoverable": bool(recoverable) and not esgotou,
    }
    return task


def mark_skipped(task: dict[str, Any], reason: str) -> dict[str, Any]:
    task["status"] = STATUS_SKIPPED
    task["completed_at"] = now_iso()
    task["result"] = {"success": True, "summary": sanitize(reason, 600)}
    task["error"] = None
    return task


# ─── Contexto mínimo por tarefa ──────────────────────────────────────────────

def dependency_summaries(task: dict[str, Any], por_id: dict[str, dict[str, Any]],
                         limit: int = TASK_DEP_CHARS) -> str:
    """Resumo curto das dependências — nunca a resposta inteira delas.

    É isto que preserva continuidade entre tarefas sem acumular contexto: o que
    passa adiante é o resumo de uma linha e os CAMINHOS dos artefatos, não o
    conteúdo deles.
    """
    linhas: list[str] = []
    for dep_id in task.get("dependencies") or []:
        dep = por_id.get(str(dep_id))
        if dep is None:
            continue
        resultado = dep.get("result") or {}
        resumo = sanitize(resultado.get("summary") or dep.get("status") or "", 240)
        linhas.append(f"- {dep_id} [{dep.get('status')}] {resumo}")
        for artefato in (dep.get("output_artifacts") or [])[:12]:
            linhas.append(f"    · {artefato}")
    texto = "\n".join(linhas)
    return texto[:limit]


def plan_excerpt(task: dict[str, Any], plan_text: str,
                 limit: int = TASK_PLAN_CHARS) -> str:
    """Extração direcionada: só as seções do plano que a tarefa precisa.

    Um plano de DevOps de projeto grande passa de 100KB. Injetá-lo inteiro em
    cada uma das N tarefas é a mesma falha do despacho único, só que N vezes.
    Aqui o plano é fatiado por cabeçalho e só entram as seções cuja pontuação
    contra o título/palavras-chave da tarefa é positiva; sem nenhuma, entra o
    início do documento como último recurso.
    """
    if not plan_text:
        return ""
    if len(plan_text) <= limit:
        return plan_text

    posicoes = [(m.start(), m.group(2).strip()) for m in _HEADING.finditer(plan_text)]
    if not posicoes:
        return plan_text[:limit]

    secoes: list[tuple[str, str]] = []
    for i, (inicio, titulo) in enumerate(posicoes):
        fim = posicoes[i + 1][0] if i + 1 < len(posicoes) else len(plan_text)
        secoes.append((titulo, plan_text[inicio:fim]))

    termos = {p for p in re.split(r'[^\wÀ-ÿ]+',
                                  f"{task.get('title', '')} {task.get('agent', '')}")
              if len(p) >= 4}
    termos |= {p for p in re.split(r'[^\wÀ-ÿ]+', str(task.get("id", ""))) if len(p) >= 4}

    def pontua(titulo: str, corpo: str) -> int:
        alvo = f"{titulo}\n{corpo[:2000]}".casefold()
        return sum(3 if t.casefold() in titulo.casefold() else
                   (1 if t.casefold() in alvo else 0) for t in termos)

    ranqueadas = sorted(((pontua(t, c), i, t, c) for i, (t, c) in enumerate(secoes)),
                        key=lambda x: (-x[0], x[1]))
    escolhidas = [(i, t, c) for score, i, t, c in ranqueadas if score > 0]
    if not escolhidas:
        return (plan_text[:limit]
                + "\n\n[... plano truncado — nenhuma seção casou com a tarefa ...]")

    escolhidas.sort(key=lambda x: x[0])          # de volta à ordem do documento
    partes: list[str] = []
    usado = 0
    for _, titulo, corpo in escolhidas:
        if usado >= limit:
            partes.append(f"\n[... seção «{titulo}» omitida — orçamento de contexto ...]")
            break
        fatia = corpo[: max(0, limit - usado)]
        partes.append(fatia)
        usado += len(fatia)
    return "".join(partes)


# ─── Orçamento de contexto ───────────────────────────────────────────────────

def estimate_tokens(*textos: str) -> int:
    """Estimativa conservadora de tokens. Ver `CHARS_PER_TOKEN`."""
    total = sum(len(t or "") for t in textos)
    return (total + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def context_budget_tokens(window: int, out_tokens: int, *,
                          safety: float = CTX_INPUT_SAFETY,
                          reserve: int = CTX_RESERVE_TOKENS) -> int:
    """Teto de INPUT para uma chamada. Nunca a janela inteira.

    O limite do modelo não é orçamento: dele saem ainda a resposta
    (``out_tokens``), instruções, uso de ferramenta e metadados. Sobra o que
    esta função devolve.
    """
    return max(1, int(window * safety) - int(out_tokens) - int(reserve))


def enforce_context_budget(*textos: str, window: int, out_tokens: int,
                           label: str = "") -> int:
    """Mede o prompt e recusa o envio se ele não couber. Devolve a estimativa.

    Chamada ANTES de `client.messages.stream`. Levantar aqui custa zero; deixar
    a API responder 400 custa a latência do upload de milhões de tokens.
    """
    estimado = estimate_tokens(*textos)
    orcamento = context_budget_tokens(window, out_tokens)
    if estimado > orcamento:
        raise ContextBudgetExceeded(
            f"contexto de {label or 'passo'} estimado em {estimado:,} tokens "
            f"excede o orçamento de {orcamento:,} "
            f"(janela {window:,} · saída {out_tokens:,} · margem de segurança "
            f"{int((1 - CTX_INPUT_SAFETY) * 100)}% + {CTX_RESERVE_TOKENS:,})",
            estimated=estimado, budget=orcamento)
    return estimado


def is_context_limit_error(exc: BaseException) -> bool:
    """True quando o erro é «o prompt não coube», em qualquer das redações."""
    if isinstance(exc, ContextBudgetExceeded):
        return True
    msg = str(exc).casefold()
    return any(marcador in msg for marcador in CONTEXT_LIMIT_MARKERS)


def request_digest(*textos: str) -> str:
    """Digest do request. Igual ao anterior = mesmo request que já falhou."""
    h = hashlib.sha256()
    for texto in textos:
        h.update((texto or "").encode("utf-8", errors="ignore"))
        h.update(b"\x00")
    return h.hexdigest()


# ─── Validação de artefatos ──────────────────────────────────────────────────

def _matches(rel: str, padrao: str) -> bool:
    rel = rel.replace("\\", "/")
    padrao = padrao.replace("\\", "/")
    if fnmatch.fnmatch(rel, padrao):
        return True
    # `a/**` deve casar `a/b/c` e também `a/b`
    if padrao.endswith("/**") and rel.startswith(padrao[:-3] + "/"):
        return True
    return False


def validate_task_artifacts(task: dict[str, Any], written: Iterable[str],
                            project: str) -> tuple[bool, list[str], str]:
    """Confere o que a tarefa gravou. ``(ok, casados, motivo)``.

    Uma tarefa não é dada por concluída porque o modelo disse que concluiu: ela
    precisa ter gravado arquivo. Quando há `output_globs`, pelo menos um
    arquivo tem de casar; sem globs, qualquer gravação serve.
    """
    prefixo = f"projects/{project}/"
    relativos = []
    for caminho in written or []:
        rel = str(caminho).replace("\\", "/")
        relativos.append(rel[len(prefixo):] if rel.startswith(prefixo) else rel)

    if not relativos:
        return False, [], "nenhum artefato gravado pela tarefa"

    padroes = list(task.get("output_globs") or [])
    if not padroes:
        return True, relativos, ""

    casados = [r for r in relativos if any(_matches(r, p) for p in padroes)]
    if casados:
        return True, casados, ""
    return (False, relativos,
            "artefatos gravados fora dos caminhos esperados da tarefa "
            f"({', '.join(padroes[:4])})")


# ─── CLI de inspeção ─────────────────────────────────────────────────────────

def _read_plans(project: str, repo_root: Path | None = None) -> dict[str, str]:
    """Lê SOMENTE os insumos declarados. Nenhum diretório é percorrido."""
    raiz = project_dir(project, repo_root)
    planos: dict[str, str] = {}
    for rel in PLAN_INPUTS:
        caminho = raiz / rel
        if caminho.is_file():
            limite = (TASK_CONFIG_CHARS if rel.endswith((".yaml", ".yml"))
                      else DERIVATION_PLAN_CHARS)
            planos[rel] = caminho.read_text(encoding="utf-8", errors="ignore")[:limite]
    return planos


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/devops_task_ledger.py",
        description="Inspeciona/inicializa a razão de progresso da F5 (DevOps Execute).")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--init", action="store_true",
                        help="cria ou reconcilia task-devops-progress.json")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--next", action="store_true",
                        help="imprime a próxima tarefa elegível")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    caminho = progress_path(args.project)

    if args.init:
        planos = _read_plans(args.project)
        faltando = [rel for rel in PLAN_INPUTS if rel not in planos]
        if faltando:
            print(f"insumo obrigatório ausente: {', '.join(faltando)}", file=sys.stderr)
            return 2
        config = planos.get(PLAN_INPUTS[0], "")
        progresso, novos = load_or_create(
            args.project, planos,
            cloud_provider=_yaml_scalar(config, "cloud_provider", "azure"),
            pipeline_mode=_yaml_scalar(config, "pipeline_mode"))
        print(f"{caminho}: {len(progresso['tasks'])} tarefa(s), "
              f"{len(novos)} nova(s)")
        return 0

    progresso = read_progress(caminho)
    if progresso is None:
        print(f"razão ausente: {caminho}\n"
              f"      Rode: python src/shared/tools/devops_task_ledger.py "
              f"-p {args.project} --init", file=sys.stderr)
        return 1

    if args.next:
        tarefa = select_next_task(progresso)
        if tarefa is None:
            print("nenhuma tarefa elegível")
            return 1
        print(json.dumps(tarefa, ensure_ascii=False, indent=2) if args.json
              else f"{tarefa['id']}  {tarefa['title']}")
        return 0

    contagem = summary_counts(progresso)
    if args.json:
        print(json.dumps(contagem, ensure_ascii=False, indent=2))
    else:
        print(f"projeto: {progresso.get('project')} · "
              f"iterações: {progresso.get('iterations', 0)}")
        for chave, valor in contagem.items():
            print(f"  {chave:12} {valor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
