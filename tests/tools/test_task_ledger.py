"""
Testes do razão de progresso — `src/shared/tools/task_ledger.py`.

O invariante que estes testes existem para proteger é o mais caro do repositório:
**status não pode ser afirmado, só comprovado.**

Na auditoria de `nopcommerce-02-cli-ava`, a esteira entregou relatórios com
`Build Status: ✅ PASS (Simulated — toolchain validation pending)` enquanto o
`dotnet build` real falhava com 1 + 35 + 8 erros, e uma matriz de rastreabilidade
marcando 15/15 linhas ✅ para classes que não existiam. RC-02 e RC-03.

O padrão de harness para agentes de execução longa deixa o próprio agente virar
o `passes` da feature depois de testar. Aqui isso não pode acontecer: quem grava
é a ferramenta, a partir de exit code real. `test_agente_nao_pode_marcar_verified`
é a linha que separa este razão de um relatório otimista.

Roda com o Python do repo:
    python -m pytest tests/tools/test_task_ledger.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PY = REPO_ROOT / "src" / "shared" / "tools" / "task_ledger.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tl = _load(MODULE_PY, "task_ledger_under_test")


# ─── Fixture ─────────────────────────────────────────────────────────────────

def _entry(task_id: str, group: str = "G-A", stack: str = "dotnet",
           depends_on: list[str] | None = None) -> dict:
    task_type = "frontend" if stack in {"angular", "react", "vue"} else "backend"
    dependencies = depends_on or []
    return {
        "task_id": task_id,
        "spec_id": "SPEC-BR-014",
        "plan_id": "PLAN-BR-001",
        "group": group,
        "task_type": task_type,
        "target_stack": stack,
        "migration_wave_id": "W1",
        "migration_wave_order": 1,
        "source_refs": [{
            "artifact": "outputs/asis/docs/business-rules.md",
            "anchor": "BR-CART-001",
        }],
        "target_files": [f"backend/src/{task_id}.cs"],
        "depends_on": dependencies,
        "backend_dependencies": dependencies if task_type == "frontend" else [],
        "acceptance": ["dotnet build sem erro"],
        "verify_command": "pwsh verify.ps1",
    }


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    sk = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    sk.mkdir(parents=True)
    (sk / "traceability.json").write_text(json.dumps({
        "schema_version": "4.0.0", "project": "P", "trace_id": "t-1",
        "generated_at": "2026-08-12T00:00:00Z",
        "entries": [
            _entry("T-CART-001"),
            _entry("T-CART-002", depends_on=["T-CART-001"]),
            _entry("T-UI-001", group="G-UI", stack="angular"),
        ],
    }), encoding="utf-8")
    return tmp_path


# ─── Inicialização ───────────────────────────────────────────────────────────

def test_init_cria_toda_task_como_pending(projeto: Path):
    ledger = tl.init("P", repo_root=projeto)
    assert [t["status"] for t in ledger["tasks"]] == ["pending"] * 3
    assert all(t["attempts"] == 0 for t in ledger["tasks"])
    assert all(t["evidence"] is None for t in ledger["tasks"])


def test_init_grava_checksum_do_traceability(projeto: Path):
    """A espinha é imutável depois da F3S; o checksum é como se prova isso."""
    ledger = tl.init("P", repo_root=projeto)
    assert len(ledger["traceability_checksum"]) == 64


def test_init_persiste_rank_wave_e_comando_de_verificacao(projeto: Path):
    ledger = tl.init("P", repo_root=projeto)
    por_id = {t["task_id"]: t for t in ledger["tasks"]}

    assert por_id["T-CART-001"]["topological_rank"] == 0
    assert por_id["T-CART-002"]["topological_rank"] == 1
    assert por_id["T-CART-002"]["execution_wave"] == 1
    assert por_id["T-CART-002"]["verify_command"] == "pwsh verify.ps1"
    assert por_id["T-CART-001"]["task_type"] == "backend"
    assert por_id["T-UI-001"]["task_type"] == "frontend"
    assert por_id["T-UI-001"]["backend_dependencies"] == []
    assert por_id["T-CART-001"]["migration_wave_id"] == "W1"
    assert por_id["T-CART-001"]["migration_wave_order"] == 1


@pytest.mark.parametrize(
    "entries",
    [
        [_entry("T-CART-001", depends_on=["T-MISSING-001"])],
        [
            _entry("T-CART-001", depends_on=["T-CART-002"]),
            _entry("T-CART-002", depends_on=["T-CART-001"]),
        ],
    ],
)
def test_init_degrada_grafo_inexecutavel_sem_recusar(tmp_path: Path,
                                                     entries: list[dict]):
    """Regra invertida de propósito: grafo inválido não impede o razão.

    Antes isto levantava `LedgerError`, e a F4 ficava sem `tasks-progress.json`
    por causa de uma dependência quebrada num plano — o mesmo padrão de
    all-or-nothing que descartava 218 tasks no consolidador. Agora a ordem
    topológica degrada para 0, o problema vira aviso, e o razão existe.
    """
    sk = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    sk.mkdir(parents=True)
    (sk / "traceability.json").write_text(json.dumps({
        "schema_version": "4.0.0", "project": "P", "trace_id": "t-1",
        "generated_at": "2026-08-14T00:00:00Z", "entries": entries,
    }), encoding="utf-8")

    ledger = tl.init("P", repo_root=tmp_path)

    assert len(ledger["tasks"]) == len(entries), "task perdida por grafo inválido"
    assert ledger["recovery_placeholder"] is False
    assert ledger["status"] == "COMPLETE_WITH_WARNINGS"
    assert any("grafo de dependências inválido" in a for a in ledger["warnings"])
    assert all(t["topological_rank"] == 0 for t in ledger["tasks"])


def test_checksum_denuncia_traceability_alterado(projeto: Path):
    tl.init("P", repo_root=projeto)
    trace = projeto / "projects" / "P" / "outputs" / "tobe" / "speckit" / "traceability.json"
    data = json.loads(trace.read_text(encoding="utf-8"))
    data["entries"].append(_entry("T-CART-999"))
    trace.write_text(json.dumps(data), encoding="utf-8")
    assert tl.checksum_matches("P", repo_root=projeto) is False


def test_init_sem_traceability_falha_com_mensagem_acionavel(tmp_path: Path):
    (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit").mkdir(parents=True)
    with pytest.raises(tl.LedgerError) as exc:
        tl.init("P", repo_root=tmp_path)
    assert "traceability.json" in str(exc.value)


def test_init_rejeita_traceability_anterior_ao_v4(tmp_path: Path):
    sk = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    sk.mkdir(parents=True)
    (sk / "traceability.json").write_text(json.dumps({
        "schema_version": "3.0.0", "project": "P", "trace_id": "t-1",
        "entries": [_entry("T-CART-001")],
    }), encoding="utf-8")

    with pytest.raises(tl.LedgerError, match="traceability.json v4 obrigatório"):
        tl.init("P", repo_root=tmp_path)


def test_init_e_idempotente_e_preserva_progresso(projeto: Path):
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    tl.record_result("P", "T-CART-001", command="pwsh verify.ps1", exit_code=0,
                     repo_root=projeto)
    depois = tl.init("P", repo_root=projeto)
    concluida = next(t for t in depois["tasks"] if t["task_id"] == "T-CART-001")
    assert concluida["status"] == "verified", "re-init não pode zerar progresso real"


# ─── Transições ──────────────────────────────────────────────────────────────

def test_exit_code_zero_leva_a_verified(projeto: Path):
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    t = tl.record_result("P", "T-CART-001", command="pwsh verify.ps1", exit_code=0,
                         repo_root=projeto)
    assert t["status"] == "verified"
    assert t["evidence"]["exit_code"] == 0
    assert t["evidence"]["recorded_by"] == "task_ledger"


def test_exit_code_diferente_de_zero_leva_a_failed(projeto: Path):
    """Arquivos escritos com verificação reprovada é `failed`, nunca `verified`."""
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    t = tl.record_result("P", "T-CART-001", command="dotnet build", exit_code=1,
                         files_written=["backend/src/T-CART-001.cs"], repo_root=projeto)
    assert t["status"] == "failed"
    assert t["files_written"] == ["backend/src/T-CART-001.cs"]


def test_falha_incrementa_attempts_e_volta_para_a_fila(projeto: Path):
    tl.init("P", repo_root=projeto)
    for _ in range(2):
        tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
        tl.record_result("P", "T-CART-001", command="dotnet build", exit_code=1,
                         repo_root=projeto)
    t = tl.get("P", "T-CART-001", repo_root=projeto)
    assert t["attempts"] == 2


def test_teto_de_tentativas_bloqueia_em_vez_de_retentar_para_sempre(projeto: Path):
    tl.init("P", repo_root=projeto)
    for _ in range(tl.MAX_ATTEMPTS):
        tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
        tl.record_result("P", "T-CART-001", command="dotnet build", exit_code=1,
                         repo_root=projeto)
    t = tl.get("P", "T-CART-001", repo_root=projeto)
    assert t["status"] == "blocked"
    assert t["blocked_reason"]
    assert "T-CART-001" not in [x["task_id"] for x in tl.next_tasks("P", repo_root=projeto)]


def test_agente_nao_pode_marcar_verified(projeto: Path):
    """O desvio deliberado em relação ao padrão do artigo de harness.

    Lá o agente vira o `passes` depois de testar. Aqui não: um agente que se
    auto-declara concluído é exatamente a RC-02 desta esteira.
    """
    tl.init("P", repo_root=projeto)
    with pytest.raises(tl.LedgerError) as exc:
        tl.record_result("P", "T-CART-001", command="acredite em mim", exit_code=0,
                         recorded_by="ava-stack-dotnet-backend", repo_root=projeto)
    assert "agente" in str(exc.value).lower()


def test_verified_sem_evidencia_e_impossivel_pela_api(projeto: Path):
    tl.init("P", repo_root=projeto)
    with pytest.raises(TypeError):
        tl.record_result("P", "T-CART-001", repo_root=projeto)  # sem command/exit_code


# ─── Seleção e retomada ──────────────────────────────────────────────────────

def test_next_tasks_respeita_dependencia(projeto: Path):
    tl.init("P", repo_root=projeto)
    ids = [t["task_id"] for t in tl.next_tasks("P", repo_root=projeto)]
    assert "T-CART-001" in ids
    assert "T-CART-002" not in ids, "depende de T-CART-001, que ainda está pending"


def test_execution_order_reflete_o_dag_completo(projeto: Path):
    tl.init("P", repo_root=projeto)
    ids = [t["task_id"] for t in tl.execution_order("P", repo_root=projeto)]

    assert ids.index("T-CART-001") < ids.index("T-CART-002")


def test_dependencia_satisfeita_libera_a_proxima(projeto: Path):
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    tl.record_result("P", "T-CART-001", command="ok", exit_code=0, repo_root=projeto)
    ids = [t["task_id"] for t in tl.next_tasks("P", repo_root=projeto)]
    assert "T-CART-002" in ids


def test_start_recusa_task_cuja_dependencia_nao_foi_verificada(projeto: Path):
    tl.init("P", repo_root=projeto)

    with pytest.raises(tl.LedgerError, match="não está pronta"):
        tl.start("P", "T-CART-002", run_id="r1", repo_root=projeto)


def test_retomada_nao_regera_o_que_ja_foi_verificado(projeto: Path):
    """Interromper a F4 e reinvocar tem de continuar, não recomeçar."""
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    tl.record_result("P", "T-CART-001", command="ok", exit_code=0, repo_root=projeto)
    ids = [t["task_id"] for t in tl.next_tasks("P", repo_root=projeto)]
    assert "T-CART-001" not in ids


def test_in_progress_interrompido_volta_para_a_fila(projeto: Path):
    """Run morto no meio deixa a task em `in_progress`; ela não pode sumir."""
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    ids = [t["task_id"] for t in tl.next_tasks("P", repo_root=projeto)]
    assert "T-CART-001" in ids


def test_next_tasks_filtra_por_grupo_e_por_stack(projeto: Path):
    tl.init("P", repo_root=projeto)
    assert [t["task_id"] for t in tl.next_tasks("P", group="G-UI", repo_root=projeto)] \
        == ["T-UI-001"]
    assert [t["task_id"] for t in tl.next_tasks("P", target_stack="angular",
                                                repo_root=projeto)] == ["T-UI-001"]


def test_groups_agrupa_por_grupo_e_stack(projeto: Path):
    """A base do fan-out da F4: um despacho por grupo, com o coder da stack."""
    tl.init("P", repo_root=projeto)
    grupos = tl.groups("P", repo_root=projeto)
    assert {g["group"] for g in grupos} == {"G-A", "G-UI"}
    ui = next(g for g in grupos if g["group"] == "G-UI")
    assert ui["target_stack"] == "angular"
    assert ui["pending"] == 1


def test_summary_conta_por_status(projeto: Path):
    tl.init("P", repo_root=projeto)
    tl.start("P", "T-CART-001", run_id="r1", repo_root=projeto)
    tl.record_result("P", "T-CART-001", command="ok", exit_code=0, repo_root=projeto)
    s = tl.summary("P", repo_root=projeto)
    assert s["verified"] == 1 and s["pending"] == 2 and s["total"] == 3


def test_diagnose_distingue_ready_complete_e_bloqueio(projeto: Path):
    tl.init("P", repo_root=projeto)
    assert tl.diagnose("P", repo_root=projeto)["status"] == "ready"

    tl.skip("P", "T-CART-001", "não aplicável", repo_root=projeto)
    diagnosis = tl.diagnose("P", repo_root=projeto)
    blocked = {item["task_id"]: item for item in diagnosis["blocked"]}
    assert diagnosis["status"] == "ready", "a branch G-UI ainda pode avançar"
    assert blocked == {}, "diagnóstico ready lista somente a fila executável"

    tl.start("P", "T-UI-001", run_id="r1", repo_root=projeto)
    tl.record_result("P", "T-UI-001", command="ok", exit_code=0, repo_root=projeto)
    diagnosis = tl.diagnose("P", repo_root=projeto)
    assert diagnosis["status"] == "blocked_by_terminal"
    assert diagnosis["blocked"][0]["blocked_by"] == ["T-CART-001"]


# ─── Integridade do arquivo ──────────────────────────────────────────────────

def test_ledger_e_json_valido_contra_o_schema(projeto: Path):
    tl.init("P", repo_root=projeto)
    path = projeto / "projects" / "P" / "outputs" / "tobe" / "speckit" / "tasks-progress.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "3.0.0"
    for t in data["tasks"]:
        assert set(t) >= {"task_id", "spec_id", "group", "target_stack", "status", "attempts"}


def test_task_desconhecida_falha_em_vez_de_criar_linha(projeto: Path):
    tl.init("P", repo_root=projeto)
    with pytest.raises(tl.LedgerError):
        tl.start("P", "T-NAO-EXISTE-001", run_id="r1", repo_root=projeto)
