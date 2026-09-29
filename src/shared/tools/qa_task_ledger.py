#!/usr/bin/env python3
"""
AVA Fabric — Razão de progresso da execução de QA (F6 · trigger QE)
====================================================================
Mantém ``projects/{p}/outputs/tobe/qa/task-qa-progress.json``: uma linha por
tarefa da cadeia QE, com o estado persistido em disco e movido por transição
explícita. É a fonte de verdade do laço iterativo (padrão Ralph Wiggum) que
substitui o despacho único da F6.

O defeito que este módulo corrige
---------------------------------
A F6 declarava ``outputs/tobe/source-code`` — um DIRETÓRIO — como insumo
obrigatório. Medido em ``meu-erp-03`` (40.468 arquivos / 379 MB):

    BadRequestError: Error code: 400 — invalid_request_error
    prompt is too long: 3958957 tokens > 1000000 maximum

Havia **dois** amplificadores, não um:

1. a expansão do diretório injetava corpos até esgotar os 2 MB de orçamento;
2. esgotado o orçamento, ``context_manifest`` anexava **um aviso por arquivo
   recusado** — 40.097 linhas, 7,5 MB. O guard de orçamento produzia 3,8× mais
   texto que os corpos que ele protegia.

O (2) foi corrigido globalmente em ``context_manifest`` (agregação por motivo).
Este módulo trata o (1): dos 14 passos da cadeia QE, **três** precisam de código
— e nenhum precisa da árvore inteira, apenas de globs estreitos que os próprios
specs dos sub-agentes já declaram.

Dois momentos, não um
---------------------
* **Momento 1 — planejamento.** Lê os artefatos de QA produzidos pelo `TPT`
  (F2c) e materializa a lista de tarefas em ``task-qa-progress.json``. Não
  executa teste nenhum.
* **Momento 2 — execução.** Percorre a lista, uma chamada por tarefa, com o
  contexto mínimo daquela tarefa. Só as tarefas marcadas ``requiresRuntime``
  exigem a aplicação no ar.

Gerar documentação ou script **não** é evidência de que o teste rodou. Uma
tarefa só vira ``passed`` com artefato em disco; sem isso ela é
``completed_with_warning`` — nunca sucesso silencioso.

Reúso
-----
As primitivas genéricas (escrita atômica, sanitização, orçamento de contexto,
detecção de estouro, digest de request) vêm de ``devops_task_ledger``, onde já
estão cobertas por testes. Aqui fica só o que é específico de QA: o esquema das
tarefas, os estados, a espinha da cadeia QE e os globs por sub-agente.

Uso
---
    python src/shared/tools/qa_task_ledger.py -p Meu-ERP --plan
    python src/shared/tools/qa_task_ledger.py -p Meu-ERP --summary
    python src/shared/tools/qa_task_ledger.py -p Meu-ERP --next

Exit codes
----------
    0 — ok      1 — nada pendente / razão inconsistente      2 — erro de configuração
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

# Reúso deliberado: estas primitivas já rodam na F5/DE e têm cobertura própria.
# Reimplementá-las aqui criaria duas escritas atômicas e dois sanitizadores, e a
# de menos uso divergiria em silêncio.
from devops_task_ledger import (          # noqa: E402
    ContextBudgetExceeded,
    atomic_write_json,
    context_budget_tokens,
    enforce_context_budget,
    estimate_tokens,
    is_context_limit_error,
    now_iso,
    request_digest,
    sanitize,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.0.0"

# ─── Constantes de execução ──────────────────────────────────────────────────

MAX_RETRIES = 2
MAX_ITERATIONS = 80

STATUS_PENDING = "pending"
STATUS_READY = "ready"
STATUS_IN_PROGRESS = "in_progress"
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_BLOCKED = "blocked"
STATUS_SKIPPED = "skipped"
STATUS_WARNING = "completed_with_warning"

STATUSES = frozenset({
    STATUS_PENDING, STATUS_READY, STATUS_IN_PROGRESS, STATUS_PASSED,
    STATUS_FAILED, STATUS_BLOCKED, STATUS_SKIPPED, STATUS_WARNING,
})

#: Estados dos quais uma tarefa não volta. `failed` NÃO é terminal enquanto
#: `retryCount < maxRetries`.
TERMINAL = frozenset({STATUS_PASSED, STATUS_SKIPPED, STATUS_WARNING, STATUS_BLOCKED})

#: Conclusões que satisfazem uma dependência. `completed_with_warning` conta:
#: o passo entregou, com ressalva registrada — travar a cadeia inteira por causa
#: de uma ressalva é o oposto de continuar de forma controlada.
SATISFIES_DEPENDENCY = frozenset({STATUS_PASSED, STATUS_SKIPPED, STATUS_WARNING})

# ─── Caminhos (sempre POSIX) ─────────────────────────────────────────────────

QA_DIR_REL = "outputs/tobe/qa"
PROGRESS_REL = "outputs/tobe/qa/task-qa-progress.json"
BACKUP_REL = "outputs/tobe/qa/task-qa-progress.json.bak"

SOURCE_ROOT_REL = "outputs/tobe/source-code"
BACKEND_ROOT_REL = "outputs/tobe/source-code/backend"
FRONTEND_ROOT_REL = "outputs/tobe/source-code/frontend"

#: Precondição da F6: conferida por EXISTÊNCIA e população, nunca injetada.
#: `**` significa "diretório existe e tem ao menos um arquivo não-build".
PRECONDITION_EXISTS: tuple[str, ...] = (
    "outputs/tobe/source-code/README.md",
    "outputs/tobe/source-code/backend/**",
    "outputs/tobe/source-code/frontend/**",
)

#: Artefatos de planejamento lidos no Momento 1. Lista fechada, só arquivos.
PLANNING_INPUTS: tuple[str, ...] = (
    "context/project-config.yaml",
    "outputs/tobe/docs/bounded-context-map.md",
    "outputs/tobe/qa/test-plan.md",
    "outputs/tobe/qa/test-cases.md",
    "outputs/tobe/qa/functional-test-matrix.md",
    "outputs/tobe/tests/functional-test-matrix.md",
    "outputs/tobe/qa/gap-analysis.md",
    "outputs/asis/docs/business-rules.json",
    "outputs/asis/docs/behavior-catalog.json",
    "outputs/asis/docs/schema-inventory.md",
    "outputs/tobe/parity-test-report.md",
)

#: Ausente gera WARNING, nunca bloqueio (Passo 4b do gate QE).
ADVISORY_ONLY: tuple[str, ...] = (
    "outputs/tobe/parity-test-report.md",
)

#: Nunca entram no contexto do ava-qa-orchestrator como conteúdo.
FORBIDDEN_INPUTS: tuple[str, ...] = (
    "context/shared-context.md",
    "outputs/tobe/source-code",
    "outputs/tobe/source-code/frontend",
    "outputs/tobe/source-code/backend",
)

#: Tetos por peça do contexto mínimo de uma tarefa.
TASK_CONFIG_CHARS = 20_000
TASK_PLAN_CHARS = 40_000
TASK_DEP_CHARS = 4_000
TASK_CODE_CHARS = 60_000
TASK_CODE_FILES = 30
PLANNING_ARTIFACT_CHARS = 60_000

_SPEC_DIR = "src/modules/ava-fabric-agents/qa-agents/agents"


class QALedgerError(Exception):
    """Erro de uso do razão. O CLI converte em exit 2."""


# ─── Espinha da cadeia QE ────────────────────────────────────────────────────
# Ordem canônica GR → BM → FTM → TS → TC → AS → DBI → CT → FT → FQ → ET + EC
# → PT → RS, da tabela `## Agent Team QA` e da §Routing do
# `qa-agents/agents/qa-orchestrator-agent.md`.
#
# `sourceCodeGlobs` reproduz o escopo que o PRÓPRIO spec do sub-agente declara —
# não um escopo inventado aqui. Onde o spec usa o layout antigo
# (`source-code/src/**`) e o contrato atual usa `backend/src/**`, ambos entram:
# o que existir em disco casa, e nenhum dos dois é a árvore inteira.

TASK_BACKBONE: tuple[dict[str, Any], ...] = (
    {
        "id": "QA-001", "sequence": 1, "category": "requisitos",
        "title": "GR — Análise de gaps de requisitos",
        "description": ("Levantar gaps entre requisitos TO-BE e cobertura de teste "
                        "planejada. Consome artefatos funcionais; NÃO lê código."),
        "subAgent": "ava-qa-gaps-requirements",
        "spec": f"{_SPEC_DIR}/gaps-requirements-agent.md",
        "dependencies": [],
        "inputArtifacts": ["outputs/tobe/qa/test-plan.md",
                           "outputs/tobe/docs/bounded-context-map.md"],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/gap-analysis.md", "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-002", "sequence": 2, "category": "requisitos",
        "title": "BM — Mapeamento de comportamento",
        "description": ("Mapear o catálogo de comportamento AS-IS contra o escopo "
                        "TO-BE. Consome `behavior-catalog.json`; NÃO lê código."),
        "subAgent": "ava-qa-behavior-mapping",
        "spec": f"{_SPEC_DIR}/behavior-mapping-agent.md",
        "dependencies": ["QA-001"],
        "inputArtifacts": ["outputs/asis/docs/behavior-catalog.json",
                           "outputs/asis/docs/business-rules.json"],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/**"],
    },
    {
        "id": "QA-003", "sequence": 3, "category": "requisitos",
        "title": "FTM — Matriz funcional de testes",
        "description": ("Gerar/atualizar a matriz funcional a partir de spec e "
                        "regras de negócio. NÃO lê código."),
        "subAgent": "ava-qa-test-case-generator",
        "spec": f"{_SPEC_DIR}/test-case-generator-agent.md",
        "dependencies": ["QA-002"],
        "inputArtifacts": ["outputs/asis/docs/business-rules.json",
                           "outputs/tobe/qa/test-plan.md"],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/functional-test-matrix.md",
                        "outputs/tobe/tests/functional-test-matrix.md"],
    },
    {
        "id": "QA-004", "sequence": 4, "category": "design",
        "title": "TS — Cenários BDD (bridge FastQA, Momento 1)",
        "description": ("Gerar cenários `.feature` a partir da matriz funcional. "
                        "NÃO lê código."),
        "subAgent": "ava-qa-bridge-fastqa-tobe",
        "spec": f"{_SPEC_DIR}/bridge-fastqa-tobe.md",
        "dependencies": ["QA-003"],
        "inputArtifacts": ["outputs/tobe/qa/functional-test-matrix.md"],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/**", "outputs/tobe/tests/**"],
    },
    {
        "id": "QA-005", "sequence": 5, "category": "design",
        "title": "TC — Casos de teste detalhados",
        "description": ("Detalhar casos de teste a partir dos cenários. NÃO lê código."),
        "subAgent": "ava-qa-test-case-generator",
        "spec": f"{_SPEC_DIR}/test-case-generator-agent.md",
        "dependencies": ["QA-004"],
        "inputArtifacts": ["outputs/tobe/qa/test-cases.md"],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/test-cases.md", "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-006", "sequence": 6, "category": "automacao",
        "title": "AS — Scripts de automação",
        "description": ("Gerar scripts de automação a partir dos casos de teste e "
                        "contratos. Recebe casos e cenários — NUNCA o repositório."),
        "subAgent": "ava-qa-script-generator",
        "spec": f"{_SPEC_DIR}/script-generator-agent.md",
        "dependencies": ["QA-005"],
        "inputArtifacts": ["outputs/tobe/qa/test-cases.md"],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/tests/**", "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-007", "sequence": 7, "category": "automacao",
        "title": "DBI — Testes de integridade de banco",
        "description": ("Gerar testes de integridade sobre as migrations. Recebe "
                        "SOMENTE os arquivos de migration, por glob estreito."),
        "subAgent": "ava-qa-db-integrity-test",
        "spec": f"{_SPEC_DIR}/db-integrity-test-agent.md",
        "dependencies": ["QA-006"],
        "inputArtifacts": ["outputs/asis/docs/schema-inventory.md"],
        "sourceCodeGlobs": [
            "outputs/tobe/source-code/backend/src/**/Migrations/*.cs",
            "outputs/tobe/source-code/src/**/Migrations/*.cs",
            "outputs/tobe/source-code/backend/**/migrations/**",
        ],
        "outputGlobs": ["outputs/tobe/qa/db-integrity/**", "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-008", "sequence": 8, "category": "automacao",
        "title": "CT — Testes de contrato",
        "description": ("Gerar testes de contrato a partir dos controllers e das "
                        "specs OpenAPI. Globs estreitos — nunca o backend inteiro."),
        "subAgent": "ava-qa-contract-test-generator",
        "spec": f"{_SPEC_DIR}/contract-test-generator-agent.md",
        "dependencies": ["QA-006"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [
            "outputs/tobe/source-code/backend/src/**/Controllers/**",
            "outputs/tobe/source-code/src/**/Controllers/**",
            "outputs/tobe/source-code/backend/**/controllers/**",
            "outputs/tobe/docs/openapi/*.yaml",
            "outputs/tobe/docs/openapi/*.json",
        ],
        "outputGlobs": ["outputs/tobe/qa/contract/**", "outputs/tobe/tests/**",
                        "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-009", "sequence": 9, "category": "automacao",
        "title": "FT — Testes de frontend",
        "description": ("Gerar testes dos componentes de frontend. Globs estreitos "
                        "de componente — nunca o frontend inteiro."),
        "subAgent": "ava-qa-frontend-test-generator",
        "spec": f"{_SPEC_DIR}/frontend-test-generator-agent.md",
        "dependencies": ["QA-006"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [
            "outputs/tobe/source-code/frontend/src/app/**/*.component.ts",
            "outputs/tobe/source-code/frontend/src/**/*.tsx",
            "outputs/tobe/source-code/frontend/src/**/*.jsx",
            "outputs/tobe/source-code/frontend/src/**/*.vue",
        ],
        "outputGlobs": ["outputs/tobe/qa/frontend/**", "outputs/tobe/tests/**",
                        "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-010", "sequence": 10, "category": "execucao",
        "title": "FQ — FastQA black-box (bridge, Momento 2)",
        "description": ("Executar validações black-box de API sobre a aplicação em "
                        "execução, reusando os `.feature` do Momento 1."),
        "subAgent": "ava-qa-bridge-fastqa-tobe",
        "spec": f"{_SPEC_DIR}/bridge-fastqa-tobe.md",
        "dependencies": ["QA-007", "QA-008", "QA-009"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [],
        "requiresRuntime": ["backend"],
        "outputGlobs": ["outputs/tobe/qa/**"],
    },
    {
        "id": "QA-011", "sequence": 11, "category": "execucao",
        "title": "ET — Teste exploratório",
        "description": ("Exploração autônoma sobre a aplicação em execução."),
        "subAgent": "ava-qa-exploratory",
        "spec": f"{_SPEC_DIR}/exploratory-agent.md",
        "dependencies": ["QA-010"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [],
        "requiresRuntime": ["backend", "frontend"],
        "outputGlobs": ["outputs/tobe/qa/**"],
    },
    {
        "id": "QA-012", "sequence": 12, "category": "execucao",
        "title": "EC — Captura de evidências",
        "description": ("Consolidar logs, screenshots e relatórios das execuções."),
        "subAgent": "ava-qa-evidence-capture",
        "spec": f"{_SPEC_DIR}/evidence-capture-agent.md",
        "dependencies": ["QA-011"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [],
        "requiresRuntime": ["backend"],
        "outputGlobs": ["outputs/tobe/qa/evidence/**", "outputs/tobe/qa/logs/**",
                        "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-013", "sequence": 13, "category": "analise",
        "title": "DI — Identificação de defeitos",
        "description": ("Consolidar defeitos a partir dos resultados, logs e "
                        "evidências. NÃO lê código."),
        "subAgent": "ava-qa-defect-identifier",
        "spec": f"{_SPEC_DIR}/defect-identifier-agent.md",
        "dependencies": ["QA-012"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/defects.json", "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-014", "sequence": 14, "category": "terminal",
        "title": "PT — Relatório de paridade",
        "description": ("Passo terminal obrigatório: consolidar paridade entre "
                        "legado e TO-BE a partir dos resultados de execução."),
        "subAgent": "ava-qa-orchestrator",
        "spec": f"{_SPEC_DIR}/qa-orchestrator-agent.md",
        "dependencies": ["QA-013"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/parity-test-report.md",
                        "outputs/tobe/qa/test-execution-summary.md",
                        "outputs/tobe/qa/**"],
    },
    {
        "id": "QA-015", "sequence": 15, "category": "terminal",
        "title": "RS — Suíte de regressão",
        "description": ("Passo terminal obrigatório: consolidar a suíte de "
                        "regressão marcada a partir dos testes aprovados."),
        "subAgent": "ava-qa-script-generator",
        "spec": f"{_SPEC_DIR}/script-generator-agent.md",
        "dependencies": ["QA-014"],
        "inputArtifacts": [],
        "sourceCodeGlobs": [],
        "outputGlobs": ["outputs/tobe/qa/regression-suite.md", "outputs/tobe/qa/**"],
    },
)


# ─── Caminhos ────────────────────────────────────────────────────────────────

def project_dir(project: str, repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / "projects" / project


def progress_path(project: str, repo_root: Path | None = None) -> Path:
    return project_dir(project, repo_root) / PROGRESS_REL


def backup_path(project: str, repo_root: Path | None = None) -> Path:
    return project_dir(project, repo_root) / BACKUP_REL


# ─── Leitura / escrita com backup e recuperação ──────────────────────────────

def read_progress(path: Path, *, allow_backup: bool = True) -> dict[str, Any] | None:
    """Lê a razão. Cai para o `.bak` quando o principal está corrompido.

    JSON corrompido não é hipótese teórica: uma queda de energia entre o
    `write` e o `fsync` de uma gravação não atômica deixa exatamente isso. A
    escrita aqui é atômica, mas o `.bak` cobre o arquivo que já estava quebrado
    em disco antes desta versão do código existir.
    """
    if path.is_file():
        try:
            dados = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(dados, dict) and isinstance(dados.get("tasks"), list):
                return dados
        except (json.JSONDecodeError, OSError):
            pass
    if not allow_backup:
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    if bak.is_file():
        try:
            dados = json.loads(bak.read_text(encoding="utf-8"))
            if isinstance(dados, dict) and isinstance(dados.get("tasks"), list):
                dados["recovered_from_backup"] = True
                return dados
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_progress(path: Path, progress: dict[str, Any]) -> Path:
    """Backup da versão anterior + escrita atômica da nova.

    O backup é feito ANTES de tocar no principal: se a gravação nova falhar por
    qualquer razão, existe uma cópia válida do estado imediatamente anterior.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            anterior = path.read_text(encoding="utf-8")
            json.loads(anterior)                       # só versiona JSON válido
            bak = path.with_suffix(path.suffix + ".bak")
            bak.write_text(anterior, encoding="utf-8", newline="\n")
        except (json.JSONDecodeError, OSError):
            pass
    progress["updatedAt"] = now_iso()
    return atomic_write_json(path, progress)


# ─── Tarefas ─────────────────────────────────────────────────────────────────

def new_task(spec: dict[str, Any], *, max_retries: int = MAX_RETRIES) -> dict[str, Any]:
    """Uma tarefa no estado inicial. A forma é o contrato do arquivo."""
    return {
        "id": str(spec["id"]),
        "sequence": int(spec.get("sequence", 0)),
        "title": str(spec.get("title", "")),
        "description": str(spec.get("description", "")),
        "category": str(spec.get("category", "")),
        "subAgent": str(spec.get("subAgent", "")),
        "status": STATUS_PENDING,
        "priority": str(spec.get("priority", "normal")),
        "mandatory": bool(spec.get("mandatory", True)),
        "blocking": bool(spec.get("blocking", False)),
        "dependencies": list(spec.get("dependencies", [])),
        "inputArtifacts": list(spec.get("inputArtifacts", [])),
        "sourceCodeGlobs": list(spec.get("sourceCodeGlobs", [])),
        "executionCommand": spec.get("executionCommand"),
        "expectedResult": str(spec.get("expectedResult")
                              or "artefatos do contrato do sub-agente gravados em disco"),
        "actualResult": None,
        "retryCount": 0,
        "maxRetries": int(spec.get("maxRetries", max_retries)),
        "startedAt": None,
        "completedAt": None,
        "lastUpdatedAt": now_iso(),
        "error": None,
        "errorType": None,
        "evidence": [],
        "outputArtifacts": [],
        "warning": None,
        "nextAction": None,
        # Operacionais — fora do mínimo exigido, usados pelo laço.
        "spec": str(spec.get("spec", "")),
        "requiresRuntime": list(spec.get("requiresRuntime", [])),
        "outputGlobs": list(spec.get("outputGlobs", [])),
        "contextLevel": 0,
        "lastRequestDigest": None,
    }


def plan_tasks(available: Iterable[str] = ()) -> list[dict[str, Any]]:
    """Momento 1 — a lista de tarefas da cadeia QE.

    `available` são os artefatos de planejamento encontrados em disco. Uma
    tarefa cujo `inputArtifacts` obrigatório não existe entra como `pending`
    mesmo assim: quem decide bloquear é o gate e o laço, com motivo registrado,
    não uma omissão silenciosa na lista.
    """
    presentes = {a.replace("\\", "/") for a in available}
    tarefas: list[dict[str, Any]] = []
    for modelo in TASK_BACKBONE:
        tarefa = new_task(modelo)
        faltando = [a for a in tarefa["inputArtifacts"] if a not in presentes]
        if faltando:
            tarefa["warning"] = ("insumo de planejamento ausente em disco: "
                                 + ", ".join(faltando))
            tarefa["nextAction"] = ("o sub-agente deve registrar a degradação no "
                                    "artefato de saída — nunca inventar o conteúdo")
        tarefas.append(tarefa)
    return tarefas


def reconcile(existentes: list[dict[str, Any]],
              planejadas: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Funde o plano com o que já está em disco. Nada de progresso é perdido.

    * tarefa já registrada é **preservada** — status, tentativas, resultado,
      evidências e artefatos vencem qualquer coisa que o plano diga;
    * tarefa nova (id inédito) entra como `pending`;
    * `in_progress` de um run interrompido volta a `ready`, para retomada;
    * nada é removido: uma tarefa que saiu do plano fica com o histórico dela.
    """
    por_id = {str(t.get("id")): t for t in existentes if t.get("id")}
    novos: list[str] = []

    for planejada in planejadas:
        tid = str(planejada["id"])
        atual = por_id.get(tid)
        if atual is None:
            por_id[tid] = planejada
            novos.append(tid)
            continue
        # Metadado de despacho pode ter mudado com o plano; estado não.
        for campo in ("sequence", "title", "description", "category", "subAgent",
                      "spec", "sourceCodeGlobs", "outputGlobs", "inputArtifacts",
                      "requiresRuntime", "expectedResult"):
            if planejada.get(campo) not in (None, "", []):
                atual[campo] = planejada[campo]
        atual.setdefault("dependencies", list(planejada.get("dependencies") or []))
        atual.setdefault("maxRetries", MAX_RETRIES)
        atual.setdefault("retryCount", 0)

    for tarefa in por_id.values():
        if tarefa.get("status") == STATUS_IN_PROGRESS:
            tarefa["status"] = STATUS_READY
            tarefa["startedAt"] = None
            tarefa["nextAction"] = "retomada após interrupção"
        if tarefa.get("status") not in STATUSES:
            tarefa["status"] = STATUS_PENDING

    ordenadas = sorted(por_id.values(),
                       key=lambda t: (int(t.get("sequence") or 0), str(t.get("id"))))
    return ordenadas, novos


def new_progress(project: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    agora = now_iso()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "project": project,
        "phase": "F6",
        "agent": "ava-qa-orchestrator",
        "trigger": "QE",
        "createdAt": agora,
        "updatedAt": agora,
        "planningCompletedAt": agora,
        "iterations": 0,
        "lastTaskId": None,
        "terminationReason": None,
        "runtime": {},
        "tasks": tasks,
    }


def load_or_plan(project: str, available: Iterable[str] = (), *,
                 repo_root: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    """Momento 1: cria ou reconcilia `task-qa-progress.json`. Sempre persiste."""
    caminho = progress_path(project, repo_root)
    planejadas = plan_tasks(available)
    existente = read_progress(caminho)

    if existente is None:
        progresso = new_progress(project, planejadas)
        novos = [t["id"] for t in planejadas]
    else:
        progresso = existente
        progresso.setdefault("schemaVersion", SCHEMA_VERSION)
        progresso.setdefault("project", project)
        progresso.setdefault("phase", "F6")
        progresso.setdefault("agent", "ava-qa-orchestrator")
        progresso.setdefault("trigger", "QE")
        progresso.setdefault("createdAt", now_iso())
        progresso.setdefault("iterations", 0)
        progresso.setdefault("runtime", {})
        progresso["planningCompletedAt"] = now_iso()
        tarefas, novos = reconcile(list(progresso.get("tasks") or []), planejadas)
        progresso["tasks"] = tarefas

    save_progress(caminho, progresso)
    return progresso, novos


# ─── Seleção, dependências e ciclos ──────────────────────────────────────────

def tasks_by_id(progress: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(t.get("id")): t for t in progress.get("tasks") or [] if t.get("id")}


def is_retryable(task: dict[str, Any]) -> bool:
    return (task.get("status") == STATUS_FAILED
            and int(task.get("retryCount", 0)) < int(task.get("maxRetries", MAX_RETRIES)))


def is_finished(task: dict[str, Any]) -> bool:
    if task.get("status") in TERMINAL:
        return True
    return task.get("status") == STATUS_FAILED and not is_retryable(task)


def find_cycles(progress: dict[str, Any]) -> list[list[str]]:
    """Ciclos de dependência, por DFS com pilha. Vazio = grafo acíclico.

    Sem esta checagem, um ciclo A→B→A faz `select_next_task` devolver `None`
    para sempre e o laço encerra por "nenhuma tarefa elegível" — mensagem
    verdadeira e inútil, que esconde a causa real.
    """
    por_id = tasks_by_id(progress)
    estado: dict[str, int] = {}          # 0=novo 1=na pilha 2=fechado
    ciclos: list[list[str]] = []

    def visitar(tid: str, pilha: list[str]) -> None:
        estado[tid] = 1
        pilha.append(tid)
        for dep in (por_id.get(tid, {}).get("dependencies") or []):
            dep = str(dep)
            if dep not in por_id:
                continue
            if estado.get(dep, 0) == 1:
                ciclos.append(pilha[pilha.index(dep):] + [dep])
            elif estado.get(dep, 0) == 0:
                visitar(dep, pilha)
        pilha.pop()
        estado[tid] = 2

    for tid in por_id:
        if estado.get(tid, 0) == 0:
            visitar(tid, [])
    return ciclos


def dependency_state(task: dict[str, Any],
                     por_id: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    """``("ready"|"waiting"|"blocked", [ids que explicam o estado])``."""
    bloqueiam: list[str] = []
    aguardam: list[str] = []
    for dep_id in task.get("dependencies") or []:
        dep = por_id.get(str(dep_id))
        if dep is None:
            bloqueiam.append(str(dep_id))
            continue
        status = dep.get("status")
        if status in SATISFIES_DEPENDENCY:
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
    """Próxima tarefa elegível, na ordem de `sequence`. `None` quando não há."""
    por_id = tasks_by_id(progress)
    elegiveis = (STATUS_PENDING, STATUS_READY)
    for tarefa in sorted(progress.get("tasks") or [],
                         key=lambda t: (int(t.get("sequence") or 0), str(t.get("id")))):
        if tarefa.get("status") in elegiveis or is_retryable(tarefa):
            estado, _ = dependency_state(tarefa, por_id)
            if estado == "ready":
                return tarefa
    return None


def mark_blocked_tasks(progress: dict[str, Any]) -> list[str]:
    """Fecha o que não tem mais como rodar. Devolve os ids bloqueados agora.

    Só bloqueia quem depende DIRETA ou transitivamente de uma falha definitiva.
    Tarefa independente nunca é bloqueada por falha alheia.
    """
    por_id = tasks_by_id(progress)
    bloqueados: list[str] = []
    mudou = True
    while mudou:                     # propaga em cascata até estabilizar
        mudou = False
        for tarefa in progress.get("tasks") or []:
            if is_finished(tarefa) or tarefa.get("status") == STATUS_IN_PROGRESS:
                continue
            estado, culpados = dependency_state(tarefa, por_id)
            if estado == "blocked":
                tarefa["status"] = STATUS_BLOCKED
                tarefa["completedAt"] = now_iso()
                tarefa["lastUpdatedAt"] = now_iso()
                tarefa["errorType"] = "DependencyBlocked"
                tarefa["error"] = sanitize(
                    "dependência não concluída em definitivo: " + ", ".join(culpados))
                tarefa["nextAction"] = (f"corrija {culpados[0]} e reexecute a F6 — "
                                        f"esta tarefa não foi executada")
                bloqueados.append(str(tarefa.get("id")))
                mudou = True
    return bloqueados


def all_finished(progress: dict[str, Any]) -> bool:
    tarefas = progress.get("tasks") or []
    return bool(tarefas) and all(is_finished(t) for t in tarefas)


def progress_signature(progress: dict[str, Any]) -> str:
    """Impressão digital do estado. Igual entre duas iterações = sem progresso."""
    import hashlib
    corpo = "|".join(
        f"{t.get('id')}:{t.get('status')}:{t.get('retryCount', 0)}"
        for t in sorted(progress.get("tasks") or [], key=lambda t: str(t.get("id")))
    )
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def summary_counts(progress: dict[str, Any]) -> dict[str, int]:
    contagem = {"total": 0, "attempts": 0}
    for chave in sorted(STATUSES):
        contagem[chave] = 0
    for tarefa in progress.get("tasks") or []:
        contagem["total"] += 1
        contagem["attempts"] += int(tarefa.get("retryCount", 0))
        status = str(tarefa.get("status"))
        if status in contagem:
            contagem[status] += 1
    return contagem


# ─── Transições ──────────────────────────────────────────────────────────────

def mark_in_progress(task: dict[str, Any]) -> dict[str, Any]:
    task["status"] = STATUS_IN_PROGRESS
    task["startedAt"] = now_iso()
    task["lastUpdatedAt"] = now_iso()
    task["completedAt"] = None
    task["error"] = None
    task["errorType"] = None
    return task


def mark_passed(task: dict[str, Any], *, actual: str,
                artifacts: Iterable[str] = (),
                evidence: Iterable[str] = ()) -> dict[str, Any]:
    """Aprovação. Exige resultado concreto — ver `validate_task_result`."""
    task["status"] = STATUS_PASSED
    task["completedAt"] = now_iso()
    task["lastUpdatedAt"] = now_iso()
    task["actualResult"] = sanitize(actual, 600)
    task["error"] = None
    task["errorType"] = None
    task["outputArtifacts"] = [str(a).replace("\\", "/") for a in artifacts]
    if evidence:
        task["evidence"] = [str(e).replace("\\", "/") for e in evidence]
    task["nextAction"] = None
    return task


def mark_warning(task: dict[str, Any], *, actual: str, warning: str,
                 artifacts: Iterable[str] = ()) -> dict[str, Any]:
    """Entregou, com ressalva registrada. Não é sucesso silencioso."""
    task["status"] = STATUS_WARNING
    task["completedAt"] = now_iso()
    task["lastUpdatedAt"] = now_iso()
    task["actualResult"] = sanitize(actual, 600)
    task["warning"] = sanitize(warning, 600)
    task["outputArtifacts"] = [str(a).replace("\\", "/") for a in artifacts]
    task["nextAction"] = "revise a ressalva antes de confiar no resultado"
    return task


def mark_failed(task: dict[str, Any], *, error_type: str, error: str,
                actual: str = "", evidence: Iterable[str] = (),
                next_action: str = "") -> dict[str, Any]:
    """Registra a falha e decide entre nova tentativa e desfecho terminal.

    Esgotadas as tentativas: `failed` quando a tarefa é obrigatória (o operador
    precisa ver a reprovação), `completed_with_warning` quando não é.
    """
    task["retryCount"] = int(task.get("retryCount", 0)) + 1
    task["lastUpdatedAt"] = now_iso()
    task["errorType"] = sanitize(error_type, 120) or "Exception"
    task["error"] = sanitize(error)
    if actual:
        task["actualResult"] = sanitize(actual, 600)
    if evidence:
        task["evidence"] = sorted({*(task.get("evidence") or []),
                                   *(str(e).replace("\\", "/") for e in evidence)})

    if int(task["retryCount"]) < int(task.get("maxRetries", MAX_RETRIES)):
        task["status"] = STATUS_READY
        task["nextAction"] = next_action or (
            f"nova tentativa {task['retryCount'] + 1}/{task.get('maxRetries')}")
        return task

    task["completedAt"] = now_iso()
    if task.get("mandatory", True):
        task["status"] = STATUS_FAILED
        task["nextAction"] = next_action or (
            "tentativas esgotadas — corrija a causa e reexecute a F6")
    else:
        task["status"] = STATUS_WARNING
        task["warning"] = sanitize(f"não obrigatória; falhou após "
                                   f"{task['retryCount']} tentativa(s)", 600)
        task["nextAction"] = next_action or "opcional — pode ser reexecutada isoladamente"
    return task


def mark_skipped(task: dict[str, Any], reason: str) -> dict[str, Any]:
    task["status"] = STATUS_SKIPPED
    task["completedAt"] = now_iso()
    task["lastUpdatedAt"] = now_iso()
    task["actualResult"] = sanitize(f"não executada: {reason}", 600)
    task["warning"] = sanitize(reason, 600)
    task["nextAction"] = "execute manualmente se o escopo exigir"
    return task


# ─── Validação de resultado ──────────────────────────────────────────────────

def _matches(rel: str, padrao: str) -> bool:
    import fnmatch
    rel = rel.replace("\\", "/")
    padrao = padrao.replace("\\", "/")
    if fnmatch.fnmatch(rel, padrao):
        return True
    return padrao.endswith("/**") and rel.startswith(padrao[:-3] + "/")


def validate_task_result(task: dict[str, Any], written: Iterable[str],
                         project: str) -> tuple[bool, list[str], str]:
    """``(ok, casados, motivo)``. Sem artefato em disco não há aprovação.

    Documento ou script gerado **não** é prova de que o teste rodou; é prova de
    que o artefato foi escrito. A distinção entre `passed` e
    `completed_with_warning` mora em quem chama: aqui só se confere entrega.
    """
    prefixo = f"projects/{project}/"
    relativos = []
    for caminho in written or []:
        rel = str(caminho).replace("\\", "/")
        relativos.append(rel[len(prefixo):] if rel.startswith(prefixo) else rel)

    if not relativos:
        return False, [], "nenhum artefato gravado pela tarefa"

    padroes = list(task.get("outputGlobs") or [])
    if not padroes:
        return True, relativos, ""

    casados = [r for r in relativos if any(_matches(r, p) for p in padroes)]
    if casados:
        return True, casados, ""
    return (False, relativos,
            "artefatos gravados fora dos caminhos esperados da tarefa "
            f"({', '.join(padroes[:3])})")


# ─── Relatório final ─────────────────────────────────────────────────────────

def execution_summary(progress: dict[str, Any], *, project: str) -> str:
    """`test-execution-summary.md`. Nunca apresenta não-executado como sucesso."""
    c = summary_counts(progress)
    runtime = progress.get("runtime") or {}
    executadas = c[STATUS_PASSED] + c[STATUS_FAILED] + c[STATUS_WARNING]

    linhas = [
        f"# QA — Resumo de execução ({project})", "",
        f"- Gerado em: {now_iso()}",
        f"- Encerramento do laço: {progress.get('terminationReason') or '—'}",
        f"- Iterações: {progress.get('iterations', 0)}",
        f"- Última tarefa processada: {progress.get('lastTaskId') or '—'}", "",
        "## Contagem", "",
        f"| métrica | valor |", "|---|---|",
        f"| tarefas planejadas | {c['total']} |",
        f"| executadas | {executadas} |",
        f"| aprovadas (passed) | {c[STATUS_PASSED]} |",
        f"| com falha (failed) | {c[STATUS_FAILED]} |",
        f"| com ressalva (completed_with_warning) | {c[STATUS_WARNING]} |",
        f"| bloqueadas | {c[STATUS_BLOCKED]} |",
        f"| ignoradas (skipped) | {c[STATUS_SKIPPED]} |",
        f"| pendentes | {c[STATUS_PENDING] + c[STATUS_READY]} |",
        f"| tentativas realizadas | {c['attempts']} |", "",
        "## Aplicação", "",
    ]
    if runtime:
        for componente, estado in sorted(runtime.items()):
            linhas.append(f"- {componente}: {estado}")
    else:
        linhas.append("- nenhum componente foi requerido ou verificado")

    linhas += ["", "## Tarefas", "",
               "| id | status | tentativas | artefatos | observação |", "|---|---|---|---|---|"]
    for t in sorted(progress.get("tasks") or [],
                    key=lambda t: int(t.get("sequence") or 0)):
        obs = t.get("error") or t.get("warning") or ""
        linhas.append(
            f"| {t.get('id')} | {t.get('status')} | "
            f"{t.get('retryCount', 0)}/{t.get('maxRetries', MAX_RETRIES)} | "
            f"{len(t.get('outputArtifacts') or [])} | {str(obs)[:120]} |")

    pendentes = [t for t in progress.get("tasks") or []
                 if t.get("status") in (STATUS_PENDING, STATUS_READY,
                                        STATUS_BLOCKED, STATUS_SKIPPED)]
    if pendentes:
        linhas += ["", "## Não executadas", "",
                   "Estas tarefas **não** produziram resultado de teste. "
                   "Nenhuma delas deve ser lida como aprovação.", ""]
        linhas += [f"- `{t.get('id')}` [{t.get('status')}] — "
                   f"{t.get('nextAction') or t.get('warning') or 'sem detalhe'}"
                   for t in pendentes]

    linhas += ["", "## Relatórios", "",
               f"- `{PROGRESS_REL}`",
               f"- `{QA_DIR_REL}/test-results.json`",
               f"- `{QA_DIR_REL}/defects.json`",
               f"- `{QA_DIR_REL}/evidence/`",
               f"- `{QA_DIR_REL}/logs/`", "",
               "## Próxima ação recomendada", "",
               recommended_action(progress)]
    return "\n".join(linhas) + "\n"


def recommended_action(progress: dict[str, Any]) -> str:
    c = summary_counts(progress)
    if c[STATUS_FAILED]:
        primeira = next((t for t in progress.get("tasks") or []
                         if t.get("status") == STATUS_FAILED), {})
        return (f"Corrija a causa de `{primeira.get('id')}` "
                f"({primeira.get('errorType') or 'erro'}) e reexecute a F6 — "
                f"a retomada preserva o que já passou.")
    if c[STATUS_BLOCKED]:
        return ("Destrave as dependências bloqueadas e reexecute a F6; as tarefas "
                "aprovadas não serão reexecutadas.")
    if c[STATUS_WARNING]:
        return ("Revise as ressalvas antes de promover o release; nenhuma delas é "
                "reprovação, mas nenhuma é aprovação plena.")
    if c[STATUS_PENDING] or c[STATUS_READY]:
        return "Reexecute a F6 para processar as tarefas restantes."
    return "Nenhuma ação pendente — a cadeia QE concluiu."


def results_json(progress: dict[str, Any], *, project: str) -> dict[str, Any]:
    """`test-results.json` — o estado em forma consumível por ferramenta."""
    return {
        "project": project,
        "phase": "F6",
        "generatedAt": now_iso(),
        "terminationReason": progress.get("terminationReason"),
        "iterations": progress.get("iterations", 0),
        "runtime": progress.get("runtime") or {},
        "counts": summary_counts(progress),
        "tasks": [
            {k: t.get(k) for k in ("id", "sequence", "title", "category", "subAgent",
                                   "status", "retryCount", "maxRetries", "startedAt",
                                   "completedAt", "actualResult", "error", "errorType",
                                   "warning", "outputArtifacts", "evidence", "nextAction")}
            for t in sorted(progress.get("tasks") or [],
                            key=lambda t: int(t.get("sequence") or 0))
        ],
    }


# ─── CLI de inspeção ─────────────────────────────────────────────────────────

def _artefatos_presentes(project: str, repo_root: Path | None = None) -> list[str]:
    raiz = project_dir(project, repo_root)
    return [rel for rel in PLANNING_INPUTS if (raiz / rel).is_file()]


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/qa_task_ledger.py",
        description="Inspeciona/planeja a razão de progresso da F6 (QA Execute).")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--plan", action="store_true",
                        help="Momento 1: cria ou reconcilia task-qa-progress.json")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--next", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    caminho = progress_path(args.project)

    if args.plan:
        progresso, novos = load_or_plan(args.project, _artefatos_presentes(args.project))
        print(f"{caminho}: {len(progresso['tasks'])} tarefa(s), {len(novos)} nova(s)")
        return 0

    progresso = read_progress(caminho)
    if progresso is None:
        print(f"razão ausente: {caminho}\n"
              f"      Rode: python src/shared/tools/qa_task_ledger.py "
              f"-p {args.project} --plan", file=sys.stderr)
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
        print(json.dumps(results_json(progresso, project=args.project),
                         ensure_ascii=False, indent=2))
    else:
        print(f"projeto: {progresso.get('project')} · "
              f"iterações: {progresso.get('iterations', 0)}")
        for chave, valor in contagem.items():
            print(f"  {chave:24} {valor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
