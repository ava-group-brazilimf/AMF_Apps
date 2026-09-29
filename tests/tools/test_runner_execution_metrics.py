"""O relatório de métricas tem contrato fechado e não derruba a esteira.

`pipeline-runner-metrics.json` é lido por consumidores a jusante que não checam
presença de campo, e é o histórico permanente de execução do projeto. Três
propriedades sustentam isso e são o que estes testes travam:

1. A estrutura é IDÊNTICA em todo modo de execução (full, manual, partial,
   resumed) e também quando nenhuma fase rodou — só o conteúdo muda. As chaves
   do topo continuam sendo as da execução corrente; o histórico vem depois.
2. Nenhum dado de entrada corrompido pode virar exceção. `exec_metrics` chega
   de três origens com contratos diferentes — o retorno de `run_step`, os dicts
   sintéticos de degradação e o JSON desserializado de uma retomada — e a
   gravação acontece no fecho de um run que já foi pago em inferência.
3. Gravar NUNCA apaga execução anterior. Uma fase avulsa rodada depois da
   esteira completa acrescenta uma execução ao histórico; a mesma fase rodada
   duas vezes aparece duas vezes, uma sob cada execução.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"

CHAVES_TOPO = ["execution_id", "project_name", "execution_mode",
               "execution_status", "start_time_utc", "end_time_utc",
               "total_duration_seconds", "total_hours",
               "token_metrics", "phase_metrics"]
CHAVES_FASE = ["phase_name", "status", "start_time_utc", "end_time_utc",
               "duration_seconds", "total_hours", "token_usage"]
# Mesmos nomes nos dois níveis: quem agrega lê run e fase com o mesmo código.
CHAVES_TOKEN = ["total_tokens", "token_in", "token_out"]
# O arquivo em disco é a execução corrente (as mesmas chaves, na mesma ordem)
# seguida do consolidado e do histórico de todas as execuções do projeto.
CHAVES_ARQUIVO = CHAVES_TOPO + ["history_summary", "execution_history"]
CHAVES_SUMARIO = ["total_executions", "first_start_time_utc", "last_end_time_utc",
                  "total_duration_seconds", "total_hours", "token_metrics",
                  "phase_history"]

T0 = 1_700_000_000.0


@pytest.fixture(scope="module")
def runner():
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    spec = importlib.util.spec_from_file_location("runner19_metrics", RUNNER_PY)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _fase(inp: int, resp: int, *, start: float = T0, dur: float = 10.0) -> dict:
    """Uma fase como `run_step` a devolve."""
    return {"inp_tokens": inp, "resp_tokens": resp, "elapsed_s": dur,
            "started_ts": start, "ended_ts": start + dur, "val_ok": True}


def _assert_estrutura(doc: dict) -> None:
    assert list(doc.keys()) == CHAVES_TOPO
    assert list(doc["token_metrics"].keys()) == CHAVES_TOKEN
    assert isinstance(doc["phase_metrics"], list)
    for linha in doc["phase_metrics"]:
        assert list(linha.keys()) == CHAVES_FASE
        assert list(linha["token_usage"].keys()) == CHAVES_TOKEN


def _assert_arquivo(doc: dict) -> None:
    """O documento em disco: execução corrente no topo, histórico embaixo."""
    assert list(doc.keys()) == CHAVES_ARQUIVO
    _assert_estrutura({k: doc[k] for k in CHAVES_TOPO})
    assert list(doc["history_summary"].keys()) == CHAVES_SUMARIO
    assert isinstance(doc["execution_history"], list)
    for entrada in doc["execution_history"]:
        _assert_estrutura(entrada)


def _ler(destino) -> dict:
    return json.loads(destino.read_text(encoding="utf-8"))


# ── Estrutura idêntica em todos os modos ────────────────────────────────────

def test_estrutura_identica_em_todos_os_modos(runner):
    """Full, manual, partial e resumed produzem o mesmo esqueleto."""
    modos = [runner.EXEC_MODE_FULL, runner.EXEC_MODE_MANUAL,
             runner.EXEC_MODE_PARTIAL, runner.EXEC_MODE_RESUMED]
    docs = [
        runner.build_execution_metrics(
            execution_id="runner19-1", execution_mode=modo,
            execution_status="completed", start_ts=T0, end_ts=T0 + 60,
            exec_metrics={"F0": _fase(10, 5)}, executed=["F0"])
        for modo in modos
    ]
    for doc, modo in zip(docs, modos):
        _assert_estrutura(doc)
        assert doc["execution_mode"] == modo
    assert len({tuple(d.keys()) for d in docs}) == 1


def test_execucao_sem_nenhuma_fase_mantem_a_estrutura(runner):
    """Nada executado é um relatório zerado, nunca um arquivo ausente ou torto."""
    doc = runner.build_execution_metrics()
    _assert_estrutura(doc)
    assert doc["phase_metrics"] == []
    assert doc["token_metrics"] == {"total_tokens": 0, "token_in": 0,
                                    "token_out": 0}
    assert doc["total_duration_seconds"] == 0


def test_execucao_parcial_traz_apenas_as_fases_executadas(runner):
    """Uma fase nunca alcançada não aparece — só as que passaram pelo runner."""
    doc = runner.build_execution_metrics(
        execution_mode=runner.EXEC_MODE_PARTIAL, start_ts=T0, end_ts=T0 + 30,
        exec_metrics={"F3": _fase(500, 100, dur=30.0)}, executed=["F3"])
    _assert_estrutura(doc)
    assert [linha["phase_name"] for linha in doc["phase_metrics"]] == ["F3"]


# ── Aritmética ──────────────────────────────────────────────────────────────

def test_total_de_tokens_e_a_soma_das_fases(runner):
    doc = runner.build_execution_metrics(
        start_ts=T0, end_ts=T0 + 100,
        exec_metrics={"F0": _fase(1000, 250), "F1": _fase(40000, 8000)},
        executed=["F0", "F1"])
    assert doc["token_metrics"]["token_in"] == 41000
    assert doc["token_metrics"]["token_out"] == 8250
    assert doc["token_metrics"]["total_tokens"] == 49250
    assert doc["token_metrics"]["total_tokens"] == sum(
        linha["token_usage"]["total_tokens"] for linha in doc["phase_metrics"])


def test_duracao_total_vem_do_intervalo_real(runner):
    """Não é a soma das fases: há espera de operador entre um passo e outro."""
    doc = runner.build_execution_metrics(
        start_ts=T0, end_ts=T0 + 3600,
        exec_metrics={"F0": _fase(1, 1, dur=10.0)}, executed=["F0"])
    assert doc["total_duration_seconds"] == 3600.0
    assert doc["phase_metrics"][0]["duration_seconds"] == 10.0


@pytest.mark.parametrize("segundos,esperado", [
    (0,        "00:00:00"),
    (59.9,     "00:00:59"),
    (61,       "00:01:01"),
    (3600,     "01:00:00"),
    (3661.7,   "01:01:01"),
    (96063,    "26:41:03"),   # >24h não pode dar a volta: a esteira passa disso
    (None,     "00:00:00"),
    ("lixo",   "00:00:00"),
])
def test_total_hours_em_hh_mm_ss(runner, segundos, esperado):
    assert runner._hhmmss(segundos) == esperado


def test_total_hours_presente_no_run_e_em_cada_fase(runner):
    doc = runner.build_execution_metrics(
        start_ts=T0, end_ts=T0 + 3661,
        exec_metrics={"F0": _fase(1, 1, dur=61.0)}, executed=["F0"])
    assert doc["total_hours"] == "01:01:01"
    assert doc["phase_metrics"][0]["total_hours"] == "00:01:01"


def test_project_name_vem_do_diretorio_de_destino(runner, monkeypatch, tmp_path):
    """Documento e caminho não podem divergir: saem do mesmo argumento."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    destino = runner.write_execution_metrics("cadastro-funcionario-02",
                                             execution_id="x")
    doc = json.loads(destino.read_text(encoding="utf-8"))
    assert doc["project_name"] == "cadastro-funcionario-02"
    assert destino.parent.parent.parent.name == "cadastro-funcionario-02"


def test_timestamps_sao_iso8601_utc(runner):
    doc = runner.build_execution_metrics(
        start_ts=T0, end_ts=T0 + 300,
        exec_metrics={"F0": _fase(1, 1)}, executed=["F0"])
    assert doc["start_time_utc"] == "2023-11-14T22:13:20Z"
    assert doc["end_time_utc"] == "2023-11-14T22:18:20Z"
    assert doc["phase_metrics"][0]["start_time_utc"].endswith("Z")


def test_fase_sem_horario_cai_para_elapsed_s(runner):
    """Degradação e task bloqueada montam o dict à mão, sem `started_ts`."""
    doc = runner.build_execution_metrics(
        start_ts=T0, end_ts=T0 + 10,
        exec_metrics={"F2": {"inp_tokens": 0, "resp_tokens": 0, "elapsed_s": 7.5,
                             "val_ok": False, "degraded": True}},
        executed=["F2"])
    linha = doc["phase_metrics"][0]
    assert linha["start_time_utc"] == ""
    assert linha["end_time_utc"] == ""
    assert linha["duration_seconds"] == 7.5


# ── Status ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metrics,listas,esperado", [
    ({"val_ok": True},                    {"executed": ["X"]},   "executed"),
    ({"val_ok": False, "degraded": True}, {"executed": ["X"]},   "degraded"),
    ({"val_ok": False},                   {"val_failed": ["X"]}, "validation_failed"),
    ({},                                  {"skipped": ["X"]},    "skipped"),
    ({},                                  {"aborted": ["X"]},    "aborted"),
    ({},                                  {},                    "not_executed"),
])
def test_status_por_fase(runner, metrics, listas, esperado):
    doc = runner.build_execution_metrics(
        exec_metrics={"X": {**metrics, "inp_tokens": 1, "resp_tokens": 1}}, **listas)
    assert doc["phase_metrics"][0]["status"] == esperado


def test_status_do_run(runner):
    runner._DEGRADATIONS.clear()
    assert runner.execution_status_label([], [], [], [], completed=True) == "completed"
    assert runner.execution_status_label(["F0"], [], [], [], completed=False) == "interrupted"
    assert runner.execution_status_label([], [], ["F3"], [], completed=True) == "aborted"
    assert runner.execution_status_label(["F0"], ["F1"], [], [],
                                         completed=True) == "completed_with_warnings"


# ── Resiliência ─────────────────────────────────────────────────────────────

def test_dados_corrompidos_nao_levantam(runner):
    """Todo campo com o tipo errado de uma vez — o relatório ainda sai válido."""
    doc = runner.build_execution_metrics(
        execution_id=None, execution_mode=None, execution_status=None,
        start_ts="nao-e-numero", end_ts=None,
        exec_metrics={
            "A": {"inp_tokens": None, "resp_tokens": "abc", "elapsed_s": None},
            "B": "isto nem sequer é um dict",
            "C": {"inp_tokens": -5, "resp_tokens": 3.7,
                  "started_ts": "x", "ended_ts": 0},
        },
        executed=None, skipped=None, aborted=None, val_failed=None)
    _assert_estrutura(doc)
    assert doc["token_metrics"]["total_tokens"] == 3   # -5 → 0, "abc" → 0, 3.7 → 3
    assert json.dumps(doc)                              # serializável


def test_escrita_nunca_propaga_excecao(runner, monkeypatch):
    """Disco cheio, permissão negada, caminho inválido: aviso, não stacktrace."""
    def _explode(*_a, **_kw):
        raise OSError("disco cheio")

    monkeypatch.setattr(Path, "write_text", _explode)
    assert runner.write_execution_metrics("qualquer-projeto", execution_id="x") is None


def test_montagem_quebrada_ainda_grava_documento_vazio(runner, monkeypatch, tmp_path):
    """Um relatório zerado é informação; um arquivo ausente é ambiguidade."""
    original = runner.build_execution_metrics
    chamadas = {"n": 0}

    def _falha_na_primeira(**kwargs):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("estado do run inutilizável")
        return original(**kwargs)

    monkeypatch.setattr(runner, "build_execution_metrics", _falha_na_primeira)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    destino = runner.write_execution_metrics("proj", execution_id="x")
    assert destino is not None and destino.exists()
    _assert_arquivo(json.loads(destino.read_text(encoding="utf-8")))


# ── Gravação em disco ───────────────────────────────────────────────────────

def test_grava_no_lugar_certo_com_indentacao_de_dois_espacos(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    destino = runner.write_execution_metrics(
        "meu-projeto", execution_id="runner19-1",
        execution_mode=runner.EXEC_MODE_FULL, execution_status="completed",
        start_ts=T0, end_ts=T0 + 5,
        exec_metrics={"F0": _fase(7, 3, dur=5.0)}, executed=["F0"])

    assert destino == (tmp_path / "projects" / "meu-projeto" / "outputs"
                       / "pipeline_runner" / "pipeline-runner-metrics.json")
    bruto = destino.read_text(encoding="utf-8")
    assert bruto.splitlines()[1].startswith('  "')
    assert json.loads(bruto)["token_metrics"]["total_tokens"] == 10


def test_topo_traz_a_execucao_corrente_sem_residuo_da_anterior(runner, monkeypatch,
                                                              tmp_path):
    """Quem lê só o topo continua vendo a execução corrente, e nada além dela."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner.write_execution_metrics(
        "p", execution_id="runner19-1", exec_metrics={"F0": _fase(9, 9)},
        executed=["F0"])
    destino = runner.write_execution_metrics(
        "p", execution_id="runner19-2", exec_metrics={})

    doc = _ler(destino)
    _assert_arquivo(doc)
    assert doc["execution_id"] == "runner19-2"
    assert doc["phase_metrics"] == []          # sem resíduo do run anterior


# ── Histórico: o arquivo nunca perde execução ───────────────────────────────

def test_execucao_nova_nao_apaga_a_anterior(runner, monkeypatch, tmp_path):
    """O defeito de origem: iniciar uma execução zerava o histórico do projeto."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner.write_execution_metrics(
        "p", execution_id="runner19-1", execution_mode=runner.EXEC_MODE_FULL,
        execution_status="completed", exec_metrics={"F0": _fase(9, 9)},
        executed=["F0"])
    destino = runner.write_execution_metrics(
        "p", execution_id="runner19-2", execution_mode=runner.EXEC_MODE_PARTIAL,
        execution_status="running", exec_metrics={})

    doc = _ler(destino)
    assert [e["execution_id"] for e in doc["execution_history"]] == [
        "runner19-1", "runner19-2"]
    # A esteira completa continua inteira dentro do histórico.
    anterior = doc["execution_history"][0]
    assert anterior["execution_mode"] == runner.EXEC_MODE_FULL
    assert [linha["phase_name"] for linha in anterior["phase_metrics"]] == ["F0"]
    assert anterior["token_metrics"]["total_tokens"] == 18


def test_full_e_depois_a_mesma_fase_avulsa_registram_as_duas_execucoes(
        runner, monkeypatch, tmp_path):
    """Cenário do relato: F0 na esteira completa e F0 de novo, sozinha."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner.write_execution_metrics(
        "p", execution_id="runner19-1", execution_mode=runner.EXEC_MODE_FULL,
        execution_status="completed", start_ts=T0, end_ts=T0 + 10,
        exec_metrics={"F0": _fase(100, 10, start=T0)}, executed=["F0"])
    destino = runner.write_execution_metrics(
        "p", execution_id="runner19-2", execution_mode=runner.EXEC_MODE_MANUAL,
        execution_status="completed", start_ts=T0 + 500, end_ts=T0 + 510,
        exec_metrics={"F0": _fase(50, 5, start=T0 + 500)}, executed=["F0"])

    doc = _ler(destino)
    execucoes_de_f0 = [(e["execution_id"], e["execution_mode"], linha["start_time_utc"])
                       for e in doc["execution_history"]
                       for linha in e["phase_metrics"] if linha["phase_name"] == "F0"]
    assert execucoes_de_f0 == [
        ("runner19-1", runner.EXEC_MODE_FULL, "2023-11-14T22:13:20Z"),
        ("runner19-2", runner.EXEC_MODE_MANUAL, "2023-11-14T22:21:40Z"),
    ]
    # E o consolidado conta as duas passagens da fase, somando tempo e token.
    (f0,) = doc["history_summary"]["phase_history"]
    assert f0["executions"] == 2
    assert f0["token_usage"]["total_tokens"] == 165
    assert doc["history_summary"]["total_executions"] == 2
    assert doc["history_summary"]["token_metrics"]["total_tokens"] == 165


def test_gravacoes_do_mesmo_run_atualizam_a_mesma_entrada(runner, monkeypatch,
                                                          tmp_path):
    """Largada, flush por fase e fecho são A MESMA execução — não três."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    for status, metricas in (("running", {}),
                             ("running", {"F0": _fase(10, 1)}),
                             ("completed", {"F0": _fase(10, 1), "F1": _fase(20, 2)})):
        destino = runner.write_execution_metrics(
            "p", execution_id="runner19-1", execution_status=status,
            exec_metrics=metricas, executed=list(metricas))

    doc = _ler(destino)
    assert len(doc["execution_history"]) == 1
    entrada = doc["execution_history"][0]
    assert entrada["execution_status"] == "completed"
    assert [linha["phase_name"] for linha in entrada["phase_metrics"]] == ["F0", "F1"]


def test_arquivo_no_formato_antigo_vira_a_primeira_entrada(runner, monkeypatch,
                                                           tmp_path):
    """Atualizar o runner não pode custar o histórico já gravado em disco."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    destino = (tmp_path / "projects" / "p" / "outputs" / "pipeline_runner"
               / runner.METRICS_FILENAME)
    destino.parent.mkdir(parents=True)
    antigo = runner.build_execution_metrics(
        execution_id="runner19-antigo", project_name="p",
        execution_mode=runner.EXEC_MODE_FULL, execution_status="completed",
        exec_metrics={"F0": _fase(3, 3)}, executed=["F0"])
    destino.write_text(json.dumps(antigo, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    runner.write_execution_metrics("p", execution_id="runner19-novo",
                                   exec_metrics={})
    doc = _ler(destino)
    assert [e["execution_id"] for e in doc["execution_history"]] == [
        "runner19-antigo", "runner19-novo"]


def test_arquivo_ilegivel_e_preservado_em_vez_de_descartado(runner, monkeypatch,
                                                            tmp_path):
    """JSON quebrado não some: fica ao lado, para inspeção."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    destino = (tmp_path / "projects" / "p" / "outputs" / "pipeline_runner"
               / runner.METRICS_FILENAME)
    destino.parent.mkdir(parents=True)
    destino.write_text("{ isto nao e json", encoding="utf-8")

    runner.write_execution_metrics("p", execution_id="runner19-1", exec_metrics={})
    doc = _ler(destino)
    assert [e["execution_id"] for e in doc["execution_history"]] == ["runner19-1"]
    salvos = list(destino.parent.glob("pipeline-runner-metrics.corrupted-*.json"))
    assert len(salvos) == 1
    assert salvos[0].read_text(encoding="utf-8") == "{ isto nao e json"


def test_nenhum_temporario_sobra_apos_a_gravacao(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    destino = runner.write_execution_metrics("p", execution_id="x", exec_metrics={})
    assert list(destino.parent.iterdir()) == [destino]


# ── Interrupção ─────────────────────────────────────────────────────────────

def test_interrupcao_preserva_o_consumo_ja_pago(runner, monkeypatch, tmp_path):
    """Ctrl+C no meio da esteira não pode descartar os tokens já gastos."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({
        "project": "p", "execution_id": "runner19-9",
        "execution_mode": runner.EXEC_MODE_FULL, "start_ts": T0,
        "metrics": {"F0": _fase(11, 2)}, "executed": ["F0"],
        "skipped": [], "aborted": [], "val_failed": [],
    })
    destino = runner.write_metrics_from_run_ctx("interrupted")
    assert destino is not None
    doc = json.loads(destino.read_text(encoding="utf-8"))
    assert doc["execution_status"] == "interrupted"
    assert doc["token_metrics"]["total_tokens"] == 13


def test_interrupcao_antes_da_esteira_nao_grava_nada(runner):
    runner._RUN_CTX.clear()
    assert runner.write_metrics_from_run_ctx("interrupted") is None


def test_fecho_normal_nao_e_sobrescrito_pelo_handler(runner, monkeypatch, tmp_path):
    """`finalized` protege o veredito real de um Ctrl+C tardio."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({"project": "p", "start_ts": T0, "metrics": {},
                            "finalized": True})
    assert runner.write_metrics_from_run_ctx("interrupted") is None


# ── Acompanhamento durante o run ────────────────────────────────────────────

def test_flush_publica_o_acumulado_com_status_running(runner, monkeypatch, tmp_path):
    """Enquanto a esteira roda o arquivo já traz o consumo até ali."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({"execution_id": "runner19-7",
                            "execution_mode": runner.EXEC_MODE_FULL,
                            "start_ts": T0})
    destino = runner.flush_execution_metrics(
        "p", ["F0"], [], [], {"F0": _fase(120, 30)}, [])
    doc = json.loads(destino.read_text(encoding="utf-8"))
    assert doc["execution_status"] == "running"
    assert doc["execution_id"] == "runner19-7"
    assert doc["token_metrics"]["total_tokens"] == 150
    assert [linha["phase_name"] for linha in doc["phase_metrics"]] == ["F0"]


def test_flush_acompanha_o_avanco_fase_a_fase(runner, monkeypatch, tmp_path):
    """Cada chamada atualiza a entrada do run com uma fase a mais."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({"execution_id": "x", "execution_mode": "full",
                            "start_ts": T0})
    acumulado: dict = {}
    executadas: list[str] = []
    totais = []
    for i, fase in enumerate(["F0", "F1", "F2"]):
        acumulado[fase] = _fase(100, 10, start=T0 + i * 60)
        executadas.append(fase)
        destino = runner.flush_execution_metrics(
            "p", executadas, [], [], acumulado, [])
        doc = json.loads(destino.read_text(encoding="utf-8"))
        totais.append((len(doc["phase_metrics"]), doc["token_metrics"]["total_tokens"]))

    assert totais == [(1, 110), (2, 220), (3, 330)]


def test_flush_para_apos_o_fecho_do_run(runner, monkeypatch, tmp_path):
    """`finalized` congela o veredito final contra um flush tardio."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({"start_ts": T0, "finalized": True})
    assert runner.flush_execution_metrics("p", [], [], [], {}, []) is None


def test_save_runner_state_atualiza_as_metricas(runner, monkeypatch, tmp_path):
    """O gancho real: métricas herdam a cadência do estado, sem call site novo."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    monkeypatch.setattr(runner, "_runner_state_path",
                        lambda proj: tmp_path / "state" / "runner-state.json")
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({"execution_id": "runner19-3",
                            "execution_mode": runner.EXEC_MODE_PARTIAL,
                            "start_ts": T0})
    runner._save_runner_state(
        "p", [{"phase": "F0"}], ["F0"], [], [], {"F0": _fase(80, 20)}, 1)

    destino = (tmp_path / "projects" / "p" / "outputs" / "pipeline_runner"
               / runner.METRICS_FILENAME)
    assert destino.exists(), "salvar o estado não atualizou as métricas"
    doc = json.loads(destino.read_text(encoding="utf-8"))
    assert doc["execution_status"] == "running"
    assert doc["token_metrics"]["total_tokens"] == 100


def test_falha_ao_salvar_estado_nao_impede_as_metricas(runner, monkeypatch, tmp_path):
    """Os dois registros são independentes — um quebrado não leva o outro."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)

    class _PathQueFalha:
        parent = type("P", (), {"mkdir": staticmethod(lambda **kw: None)})()

        def write_text(self, *a, **kw):
            raise OSError("estado ilegível")

    monkeypatch.setattr(runner, "_runner_state_path", lambda proj: _PathQueFalha())
    runner._RUN_CTX.clear()
    runner._RUN_CTX.update({"execution_id": "x", "execution_mode": "full",
                            "start_ts": T0})
    runner._save_runner_state("p", [], ["F0"], [], [], {"F0": _fase(5, 5)}, 1)

    destino = (tmp_path / "projects" / "p" / "outputs" / "pipeline_runner"
               / runner.METRICS_FILENAME)
    assert destino.exists()
    assert json.loads(destino.read_text(encoding="utf-8"))[
        "token_metrics"]["total_tokens"] == 10
