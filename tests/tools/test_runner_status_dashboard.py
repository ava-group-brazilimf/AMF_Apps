"""O dashboard `pipeline-status.html` é acumulativo e atualizado por bloco.

O HTML era desenhado só a partir do run EM CURSO. Numa retomada — ou numa
execução a partir de uma fase específica — `steps` traz apenas as fases
selecionadas e as listas de veredicto chegam vazias na largada, então o arquivo
era regravado do zero e o histórico das fases já rodadas sumia da tela: sobrava
a etapa em execução.

Estes testes travam as quatro propriedades que sustentam a correção:

1. O estado de cada fase vive em `pipeline-status-state.json` e é carregado
   antes de cada gravação — nenhuma fase já registrada desaparece.
2. Estado terminal (OK/Aviso/Pulado/Abortado/Val-Fail) não é rebaixado para
   pendente por uma chamada que não conhece aquela fase.
3. Há sempre no máximo UMA etapa marcada como em execução, e ela é a atual.
4. A atualização é incremental: a estrutura da página e as linhas das fases
   inalteradas não são reconstruídas.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"

PROJETO = "proj-dashboard"
T0 = 1_700_000_000.0


@pytest.fixture(scope="module")
def runner():
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    spec = importlib.util.spec_from_file_location("runner19_status", RUNNER_PY)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def sandbox(runner, tmp_path, monkeypatch):
    """Isola WORKSPACE: o dashboard grava em projects/<proj>/outputs/."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    return tmp_path


def _passo(fase: str, agente: str = "ava-x") -> dict:
    return {"phase": fase, "agent": agente}


def _metricas(**extra) -> dict:
    base = {"elapsed_s": 12.0, "artifacts": 3, "inp_tokens": 1000,
            "resp_tokens": 500, "val_ok": True}
    base.update(extra)
    return base


def _blocos(runner, html: str) -> dict:
    return {m.group(1): m.group(2) for m in runner._MARCA_RE.finditer(html)}


def _fases_no_html(runner, html: str) -> list:
    return [c[4:] for c in _blocos(runner, html) if c.startswith("ROW:")]


def _rotulo(runner, html: str, fase: str) -> str:
    """Texto da coluna Status da fase — 'OK', 'Executando…', '—'…"""
    linha = _blocos(runner, html)[f"ROW:{fase}"]
    # 3ª <td> da linha principal é a do rótulo.
    celulas = linha.split("</td>")
    return celulas[2].split(">")[-1]


# ── 1. Histórico preservado entre execuções ─────────────────────────────────

def test_retomada_preserva_fases_do_run_anterior(runner, sandbox):
    """Retomada seletiva não pode apagar as fases já executadas."""
    esteira = [_passo("F0"), _passo("F1"), _passo("F2")]
    metricas = {"F0": _metricas(), "F1": _metricas()}
    runner._write_status_html(PROJETO, esteira, ["F0", "F1"], [], [],
                              current_phase="F2", start_ts=T0,
                              exec_metrics=metricas)

    # Retomada: só a F2 está na esteira ativa e as listas chegam vazias.
    html_path = runner._write_status_html(PROJETO, [_passo("F2")], [], [], [],
                                          current_phase="F2", start_ts=T0)
    html = html_path.read_text(encoding="utf-8")

    assert _fases_no_html(runner, html) == ["F0", "F1", "F2"]
    assert _rotulo(runner, html, "F0") == "OK"
    assert _rotulo(runner, html, "F1") == "OK"
    assert _rotulo(runner, html, "F2") == "Executando…"


def test_largada_com_listas_vazias_nao_zera_historico(runner, sandbox):
    """`_write_status_html(proj, steps, [], [], [])` é a largada de todo run."""
    esteira = [_passo("F0"), _passo("F1")]
    runner._write_status_html(PROJETO, esteira, ["F0"], [], [],
                              start_ts=T0, exec_metrics={"F0": _metricas()})

    html_path = runner._write_status_html(PROJETO, esteira, [], [], [],
                                          start_ts=T0)
    html = html_path.read_text(encoding="utf-8")

    assert _rotulo(runner, html, "F0") == "OK", "veredicto rebaixado para pendente"
    assert _rotulo(runner, html, "F1") == "—"


@pytest.mark.parametrize("listas,rotulo", [
    (("skipped", {"val_ok": False, "risk_accepted": True}), "Aviso"),
    (("skipped", {}), "Pulado"),
    (("aborted", {}), "Abortado"),
    (("val_fail", {}), "Val-Fail"),
])
def test_todo_estado_terminal_sobrevive_a_uma_retomada(runner, sandbox,
                                                       listas, rotulo):
    campo, extra = listas
    esteira = [_passo("F0"), _passo("F1")]
    m = _metricas(**extra)
    args = {"executed": [], "skipped": [], "aborted": [], "val_failed": None}
    if campo == "val_fail":
        args["executed"] = ["F0"]
        args["val_failed"] = ["F0"]
    else:
        args[campo] = ["F0"]
    runner._write_status_html(PROJETO, esteira, args["executed"],
                              args["skipped"], args["aborted"], start_ts=T0,
                              exec_metrics={"F0": m},
                              val_failed=args["val_failed"])

    html = runner._write_status_html(
        PROJETO, [_passo("F1")], [], [], [], current_phase="F1",
        start_ts=T0).read_text(encoding="utf-8")
    assert _rotulo(runner, html, "F0") == rotulo


def test_fase_expandida_entra_depois_da_antecessora(runner, sandbox):
    """A expansão do F3S descobre sub-fases em tempo de execução."""
    runner._write_status_html(PROJETO, [_passo("F3"), _passo("F4")], ["F3"], [],
                              [], start_ts=T0, exec_metrics={"F3": _metricas()})
    html = runner._write_status_html(
        PROJETO,
        [_passo("F3"), _passo("F3S-spec"), _passo("F3S-plan"), _passo("F4")],
        ["F3"], [], [], current_phase="F3S-spec", start_ts=T0,
        exec_metrics={"F3": _metricas()}).read_text(encoding="utf-8")

    assert _fases_no_html(runner, html) == ["F3", "F3S-spec", "F3S-plan", "F4"]


# ── 2. Etapa em execução ────────────────────────────────────────────────────

def test_apenas_a_fase_atual_fica_em_execucao(runner, sandbox):
    esteira = [_passo("F0"), _passo("F1"), _passo("F2")]
    runner._write_status_html(PROJETO, esteira, [], [], [], current_phase="F0",
                              start_ts=T0)
    html = runner._write_status_html(PROJETO, esteira, ["F0"], [], [],
                                     current_phase="F1", start_ts=T0,
                                     exec_metrics={"F0": _metricas()}
                                     ).read_text(encoding="utf-8")

    assert _rotulo(runner, html, "F0") == "OK"
    assert _rotulo(runner, html, "F1") == "Executando…"
    assert html.count('class="run"') == 1


def test_execucao_interrompida_vira_interrompido_e_nao_some(runner, sandbox):
    """Run que morre em voo deixa a fase registrada, não 'Executando…' eterno."""
    esteira = [_passo("F0"), _passo("F1")]
    runner._write_status_html(PROJETO, esteira, [], [], [], current_phase="F1",
                              start_ts=T0)

    # Novo run, outra fase em voo.
    html = runner._write_status_html(PROJETO, [_passo("F0")], [], [], [],
                                     current_phase="F0", start_ts=T0
                                     ).read_text(encoding="utf-8")

    assert _fases_no_html(runner, html) == ["F0", "F1"]
    assert _rotulo(runner, html, "F1") == "Interrompido"
    assert _rotulo(runner, html, "F0") == "Executando…"


def test_reexecucao_de_fase_concluida_volta_para_em_execucao(runner, sandbox):
    esteira = [_passo("F0")]
    runner._write_status_html(PROJETO, esteira, ["F0"], [], [], start_ts=T0,
                              exec_metrics={"F0": _metricas()})
    html = runner._write_status_html(PROJETO, esteira, [], [], [],
                                     current_phase="F0", start_ts=T0
                                     ).read_text(encoding="utf-8")
    assert _rotulo(runner, html, "F0") == "Executando…"


# ── 3. Atualização incremental ──────────────────────────────────────────────

def test_linha_inalterada_nao_e_reconstruida(runner, sandbox):
    esteira = [_passo("F0"), _passo("F1")]
    p = runner._write_status_html(PROJETO, esteira, ["F0"], [], [],
                                  current_phase="F1", start_ts=T0,
                                  exec_metrics={"F0": _metricas()})
    antes = p.read_text(encoding="utf-8")

    p = runner._write_status_html(PROJETO, esteira, ["F0", "F1"], [], [],
                                  start_ts=T0, done=True,
                                  exec_metrics={"F0": _metricas(),
                                                "F1": _metricas()})
    depois = p.read_text(encoding="utf-8")

    b_antes, b_depois = _blocos(runner, antes), _blocos(runner, depois)
    assert b_antes["ROW:F0"] == b_depois["ROW:F0"], "linha estável foi regravada"
    assert b_antes["ROW:F1"] != b_depois["ROW:F1"]
    # Folha de estilo e esqueleto da tabela intocados.
    assert (antes.split("<style>")[1].split("</style>")[0]
            == depois.split("<style>")[1].split("</style>")[0])
    assert (antes.split("<thead>")[1].split("</thead>")[0]
            == depois.split("<thead>")[1].split("</thead>")[0])


def test_gravacao_sem_mudanca_nao_reescreve_o_arquivo(runner, sandbox,
                                                      monkeypatch):
    esteira = [_passo("F0")]
    kwargs = dict(current_phase="F0", start_ts=T0)
    p = runner._write_status_html(PROJETO, esteira, [], [], [], **kwargs)

    # Congela relógio e cronômetro: sem isso o cabeçalho muda a cada segundo e
    # a comparação testaria o horário, não a atualização incremental.
    monkeypatch.setattr(runner.time, "time", lambda: T0)

    class _Relogio(runner.datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, 10, 30, 0)

    monkeypatch.setattr(runner.datetime, "datetime", _Relogio)

    primeiro = runner._write_status_html(PROJETO, esteira, [], [], [],
                                         **kwargs).read_text(encoding="utf-8")
    marca = p.stat().st_mtime_ns
    segundo = runner._write_status_html(PROJETO, esteira, [], [], [],
                                        **kwargs).read_text(encoding="utf-8")

    assert primeiro == segundo
    assert p.stat().st_mtime_ns == marca, "arquivo reescrito sem nada ter mudado"


def test_marcadores_ausentes_forcam_reconstrucao(runner, sandbox):
    """HTML de versão anterior (sem marcadores) é regravado inteiro."""
    esteira = [_passo("F0")]
    p = runner._write_status_html(PROJETO, esteira, ["F0"], [], [], start_ts=T0,
                                  exec_metrics={"F0": _metricas()})
    p.write_text("<html>versão antiga sem marcadores</html>", encoding="utf-8")

    html = runner._write_status_html(PROJETO, esteira, ["F0"], [], [],
                                     start_ts=T0,
                                     exec_metrics={"F0": _metricas()}
                                     ).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert _rotulo(runner, html, "F0") == "OK"


# ── 4. Ledger em disco ──────────────────────────────────────────────────────

def test_ledger_grava_status_de_cada_fase(runner, sandbox):
    esteira = [_passo("F0", "ava-ast-extractor"), _passo("F1")]
    runner._write_status_html(PROJETO, esteira, ["F0"], [], [],
                              current_phase="F1", start_ts=T0,
                              exec_metrics={"F0": _metricas()})

    dados = json.loads(runner._status_ledger_path(PROJETO)
                       .read_text(encoding="utf-8"))
    assert dados["order"] == ["F0", "F1"]
    assert dados["steps"]["F0"]["status"] == "done"
    assert dados["steps"]["F0"]["agent"] == "ava-ast-extractor"
    assert dados["steps"]["F1"]["status"] == "running"


def test_reset_comeca_um_ledger_novo(runner, sandbox):
    """Esteira completa do zero é o único caso que descarta o histórico."""
    runner._write_status_html(PROJETO, [_passo("F0"), _passo("F1")], ["F0"], [],
                              [], start_ts=T0, exec_metrics={"F0": _metricas()})
    html = runner._write_status_html(PROJETO, [_passo("F0")], [], [], [],
                                     start_ts=T0, reset=True
                                     ).read_text(encoding="utf-8")
    assert _fases_no_html(runner, html) == ["F0"]
    assert _rotulo(runner, html, "F0") == "—"


def test_ledger_de_outro_projeto_e_ignorado(runner, sandbox):
    caminho = runner._status_ledger_path(PROJETO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"project": "outro", "order": ["FX"],
                                   "steps": {"FX": {"status": "done"}}}),
                       encoding="utf-8")
    html = runner._write_status_html(PROJETO, [_passo("F0")], [], [], [],
                                     start_ts=T0).read_text(encoding="utf-8")
    assert _fases_no_html(runner, html) == ["F0"]


def test_ledger_corrompido_nao_derruba_a_esteira(runner, sandbox):
    caminho = runner._status_ledger_path(PROJETO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("{ isto não é json", encoding="utf-8")
    html = runner._write_status_html(PROJETO, [_passo("F0")], ["F0"], [], [],
                                     start_ts=T0,
                                     exec_metrics={"F0": _metricas()}
                                     ).read_text(encoding="utf-8")
    assert _rotulo(runner, html, "F0") == "OK"


def test_ordem_e_steps_divergentes_sao_reconciliados(runner, sandbox):
    """Gravação interrompida no meio não pode esconder fase registrada."""
    caminho = runner._status_ledger_path(PROJETO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({
        "project": PROJETO, "order": ["F0", "FANTASMA"],
        "steps": {"F0": {"status": "done", "executed": True, "agent": "ava-a"},
                  "F9": {"status": "skipped", "executed": False,
                         "agent": "ava-b"}},
    }), encoding="utf-8")

    html = runner._write_status_html(PROJETO, [_passo("F1")], [], [], [],
                                     current_phase="F1", start_ts=T0
                                     ).read_text(encoding="utf-8")
    fases = _fases_no_html(runner, html)
    assert "FANTASMA" not in fases
    assert fases == ["F0", "F9", "F1"]


# ── 5. Totalizadores sobre a esteira acumulada ──────────────────────────────

def test_contadores_usam_o_ledger_e_nao_a_selecao_do_run(runner, sandbox):
    """Antes: 2 executadas sobre 1 fase selecionada imprimia '2/1 · 200%'."""
    esteira = [_passo("F0"), _passo("F1"), _passo("F2"), _passo("F3")]
    runner._write_status_html(PROJETO, esteira, ["F0", "F1"], ["F2"], [],
                              start_ts=T0,
                              exec_metrics={"F0": _metricas(),
                                            "F1": _metricas()})
    html = runner._write_status_html(PROJETO, [_passo("F3")], [], [], [],
                                     current_phase="F3", start_ts=T0
                                     ).read_text(encoding="utf-8")
    assert "2/4 fases · 1 puladas · 50%" in html
    assert 'class="pfill" style="width:50%"' in html
