"""
Testes do gate de entrada das fases TO-BE (F2).

Regressão do incidente MeuERP-002: o orquestrador F2 declarou ausentes três
artefatos AS-IS que estavam em disco e registrou os 21 agentes TO-BE como
SKIPPED. A causa foi a pré-condição ser prosa (`orchestrator-tobe.md:199` e
`:1722`) citando os artefatos só pelo nome — sem o subdiretório `db/` — e sem
ancoragem em `REPO_ROOT`.

Roda com o Python do repo:
    python -m pytest tests/ava-fabric-agents/tobe-architecture/test_artifact_gate_tobe.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_PY = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
    / "tobe-architecture" / "utils" / "artifact_gate_tobe.py"
)
SPEC_MD = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
    / "tobe-architecture" / "agents" / "orchestrator-tobe.md"
)

#: Projeto real usado na regressão — F1 completa (12/12), F2 nunca executada.
INCIDENT_PROJECT = "MeuERP-002"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load(GATE_PY, "artifact_gate_tobe_under_test")


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE_PY), *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Repo falso em `tmp_path`.

    `check_item` resolve os paths contra o `REPO_ROOT` do módulo **AS-IS**, que é
    o que este gate reusa — por isso os DOIS precisam de monkeypatch. Sem o
    segundo, os testes negativos leriam o repo real e passariam por acidente.
    """
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate.asis_gate, "REPO_ROOT", tmp_path)
    return tmp_path


def _write(root: Path, rel: str, content: str = "conteudo\n") -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _projeto_com_entry_completo(root: Path, project: str = "P1", *, master_report: bool = True):
    """Monta o mínimo que o gate `entry` exige."""
    asis = f"projects/{project}/outputs/asis"
    _write(root, f"{asis}/bounded-context-map.md")
    _write(root, f"{asis}/architecture-blueprint.md")
    _write(root, f"{asis}/db/db-analysis-report.md")
    _write(root, f"projects/{project}/context/project-config.yaml", "project_name: P1\n")
    _write(root, "src/shared/data/reference-architecture.yaml", "styles: []\n")
    if master_report:
        _write(root, f"{asis}/master-report.md")
    return project


# ─── Regressão direta do incidente ───────────────────────────────────────────

def test_gate_entry_aprova_o_projeto_do_incidente():
    """Os 3 artefatos existiam o tempo todo — o gate tem de enxergá-los."""
    proc = _run("--project", INCIDENT_PROJECT, "--gate", "entry", "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["passed"] is True
    assert payload["missing"] == []


def test_gate_entry_e_imune_ao_cwd():
    """A ancoragem em REPO_ROOT é o que impede o falso negativo por checkout errado."""
    de_outro_lugar = _run(
        "--project", INCIDENT_PROJECT, "--gate", "entry",
        cwd=REPO_ROOT / "projects" / INCIDENT_PROJECT,
    )
    assert de_outro_lugar.returncode == 0, de_outro_lugar.stdout + de_outro_lugar.stderr


def test_db_analysis_report_exige_o_subdiretorio_db():
    """ISSUE-003 §6.1: o path na raiz de `asis/` nunca existiu em disco."""
    paths = {item["path"] for item in gate.GATES["entry"]["items"]}
    assert "db/db-analysis-report.md" in paths
    assert "db-analysis-report.md" not in paths


# ─── Contrato anti-cascata (kind=root) ───────────────────────────────────────

def test_gate_entry_e_de_raiz_e_nao_expande_em_skips(fake_repo):
    """Reprovar a raiz = a F2 não começou. Nunca 21 eventos independentes."""
    assert gate.GATES["entry"]["kind"] == "root"
    assert gate.GATES["entry"]["on_fail"] == "abort_f2"

    _write(fake_repo, "projects/VAZIO/context/.keep", "")
    res = gate.check_gate("VAZIO", "entry")
    assert res["passed"] is False
    assert res["action"] == "abort_f2"
    assert res["skip_scope"] == "pipeline"
    assert res["blocks"] == ["f2_pipeline"]
    assert len(res["missing"]) <= len(gate.GATES["entry"]["items"])
    assert len(res["missing"]) < 21


def test_gate_de_fase_reprovado_pula_apenas_os_agentes_declarados(fake_repo):
    _projeto_com_entry_completo(fake_repo)
    res = gate.check_gate("P1", "phase_6")
    assert res["kind"] == "phase"
    assert res["action"] == "skip_phase"
    assert res["skip_scope"] == "phase"
    assert res["blocks"] == ["ava-tobe-user-journeys"]


def test_gate_phase_5_oa_reprovado_sem_specs_por_bc(fake_repo):
    """Sem bcNN-*.yaml a Fase 5 deve ser marcada como skip — não invocada sem inputs."""
    _projeto_com_entry_completo(fake_repo)
    # nenhum bc*.yaml presente → gate falha
    res = gate.check_gate("P1", "phase_5_oa")
    assert res["kind"] == "phase"
    assert res["action"] == "skip_phase"
    assert res["blocks"] == ["ava-docs-tobe"]
    assert any("openapi" in m["path"] for m in res["missing"])


def test_gate_phase_5_oa_aprovado_com_spec_por_bc_e_bc_map(fake_repo):
    """Com ≥1 bcNN-*.yaml e o bounded-context-map, o gate aprova."""
    _projeto_com_entry_completo(fake_repo)
    tobe = fake_repo / "projects" / "P1" / "outputs" / "tobe"
    _write(fake_repo, "projects/P1/outputs/tobe/docs/openapi/bc01-customer-supplier.yaml",
           "openapi: '3.1.0'\n")
    _write(fake_repo, "projects/P1/outputs/tobe/docs/bounded-context-map.md")
    res = gate.check_gate("P1", "phase_5_oa")
    assert res["passed"] is True


def test_todo_gate_declara_produtor_de_cada_item():
    """A ação corretiva do log sai daqui — sem `produced_by` ela vira chute."""
    sem_produtor = [
        (gid, item["path"])
        for gid, spec in gate.GATES.items()
        for item in spec["items"]
        if not item.get("produced_by")
    ]
    assert not sem_produtor, f"itens sem produtor declarado: {sem_produtor}"


# ─── Semântica advisory (specs/022) ──────────────────────────────────────────

def test_master_report_e_advisory_e_nao_reprova(fake_repo):
    _projeto_com_entry_completo(fake_repo, master_report=False)
    res = gate.check_gate("P1", "entry")
    assert res["passed"] is True
    ausentes = {m["path"]: m for m in res["missing"]}
    assert ausentes["master-report.md"]["advisory"] is True


def test_bloqueante_ausente_reprova_mesmo_com_advisory_presente(fake_repo):
    project = _projeto_com_entry_completo(fake_repo)
    (fake_repo / f"projects/{project}/outputs/asis/db/db-analysis-report.md").unlink()
    res = gate.check_gate(project, "entry")
    assert res["passed"] is False
    assert [m["path"] for m in res["missing"]] == ["db/db-analysis-report.md"]


# ─── Uso / exit codes ────────────────────────────────────────────────────────

def test_projeto_inexistente_retorna_2():
    proc = _run("--project", "nao-existe-mesmo", "--gate", "entry")
    assert proc.returncode == 2


def test_recheck_ms_e_proibido_no_gate_entry():
    """Um sleep cego esconderia path errado em vez de expor — ISSUE-003 §6.1."""
    proc = _run("--project", INCIDENT_PROJECT, "--gate", "entry", "--recheck-ms", "500")
    assert proc.returncode == 2


def test_all_agrega_todos_os_gates_e_o_contrato_f2():
    proc = _run("--project", INCIDENT_PROJECT, "--all", "--json")
    payload = json.loads(proc.stdout)
    assert set(payload["gates"]) == set(gate.GATES)
    assert payload["root_failed"] is False  # `entry` passa neste projeto
    assert "entry" in payload["passed"]
    assert payload["f2_output_contract"]["total"] == len(gate.F2_OUTPUT_CONTRACT)


# ─── Consistência spec × contrato ────────────────────────────────────────────

_PREFIXO_POR_BASE = {
    "asis": "outputs/asis/",
    "tobe": "outputs/tobe/",
    "context": "context/",
    "workspace": "",
}

_PATH_RE = re.compile(r"projects/\{project_name\}/((?:outputs|context)/[\w\-./{}*]*)")


def _path_na_spec(item: dict) -> str:
    """Path do item na forma como a spec o escreve (sem o prefixo do projeto)."""
    return _PREFIXO_POR_BASE[item.get("base", "asis")] + item["path"]


def test_todo_path_do_contrato_aparece_na_spec():
    """Direção contrato → spec.

    Um path que o gate verifica mas que a spec não menciona é contrato inventado:
    ou o gate está errado, ou a spec está desatualizada. Nos dois casos alguém
    precisa olhar. Globs (`ADR-*.md`) ficam de fora — a spec os escreve
    concretamente (`ADR-001-*.md`, `ADR-002-database.md`).
    """
    texto = SPEC_MD.read_text(encoding="utf-8")
    ausentes = sorted(
        {
            _path_na_spec(item)
            for spec in gate.GATES.values()
            for item in spec["items"]
            if "*" not in item["path"] and _path_na_spec(item) not in texto
        }
        | {rel for rel in gate.F2_OUTPUT_CONTRACT if f"outputs/tobe/{rel}" not in texto}
    )
    assert not ausentes, (
        "o gate verifica paths que a spec não declara em lugar nenhum:\n  "
        + "\n  ".join(ausentes)
    )


def test_gate_de_entrada_da_spec_lista_exatamente_os_bloqueantes_do_contrato():
    """Direção spec → contrato, restrita à seção onde o incidente aconteceu.

    A pré-condição de entrada da F2 é o único gate cuja falha derruba a fase
    inteira, e foi exatamente ali que a prosa divergiu do disco: os três
    artefatos eram citados só pelo nome, sem o subdiretório `db/`.

    Este teste ancora a seção `## Gate de Entrada F2` ao contrato: os paths
    bloqueantes escritos lá têm de ser, literalmente, os itens não-advisory de
    `GATES["entry"]`. Teria pegado o `db/` faltando antes do incidente.
    """
    texto = SPEC_MD.read_text(encoding="utf-8")
    inicio = texto.find("## Gate de Entrada F2")
    assert inicio != -1, "seção `## Gate de Entrada F2` ausente da spec"
    fim = texto.find("\n## ", inicio + 1)
    secao = texto[inicio : fim if fim != -1 else len(texto)]

    na_spec = {p for p in _PATH_RE.findall(secao) if not p.endswith("/")}
    # `workspace` fica de fora: `reference-architecture.yaml` não mora sob
    # `projects/{project_name}/`, então o regex não o alcança.
    no_contrato = {
        _path_na_spec(item)
        for item in gate.GATES["entry"]["items"]
        if item.get("base") != "workspace"
    }
    assert na_spec == no_contrato, (
        f"seção § Gate de Entrada F2 divergente do contrato\n"
        f"  só na spec     : {sorted(na_spec - no_contrato)}\n"
        f"  só no contrato : {sorted(no_contrato - na_spec)}"
    )


def test_orquestrador_invoca_todos_os_gates_declarados():
    """Um gate que existe no contrato mas não é chamado na spec volta a ser prosa."""
    texto = SPEC_MD.read_text(encoding="utf-8")
    nao_invocados = [gid for gid in gate.GATES if f"--gate {gid}" not in texto]
    assert not nao_invocados, f"gates nunca invocados pela spec: {nao_invocados}"


def test_wave_model_usa_sempre_o_path_canonico():
    """ISSUE-003 §6.2 — o escritor grava em `migration/`; a Fase 7 lia da raiz."""
    texto = SPEC_MD.read_text(encoding="utf-8")
    assert "outputs/tobe/wave-model.json" not in texto
    assert "outputs/tobe/migration/wave-model.json" in texto


def test_referencia_pendurada_gate_sd_foi_removida():
    """`Gate SD` nunca existiu como seção — era o ponteiro quebrado da pré-condição.

    Proíbe o **ponteiro** (`ver Gate SD`), não a menção: a nota histórica na seção
    `## Gate de Entrada F2` cita o nome de propósito, para que ninguém o recrie.
    """
    texto = SPEC_MD.read_text(encoding="utf-8")
    assert "ver Gate SD" not in texto
    assert "ver **Gate SD**" not in texto
    assert "## Gate de Entrada F2" in texto
