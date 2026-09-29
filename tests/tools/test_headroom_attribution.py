"""
Testes da atribuição por janela de tempo (specs/032 · D3).

O proxy sabe QUANTO comprimiu; o observer sabe QUANDO cada agente rodou. Estes
testes cobrem a junção dos dois — inclusive os dois casos que mais enganam:
o fuso (proxy em UTC × observer em BRZ) e o dispatch paralelo.

    python -m pytest tests/tools/test_headroom_attribution.py -q
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = REPO_ROOT / "src" / "shared" / "tools" / "headroom"
sys.path.insert(0, str(TOOL_DIR))

import headroom_tool as ht  # noqa: E402

BRZ = timezone(timedelta(hours=-3))


def _window(agent: str, start: float, end: float, phase: str = "F1") -> dict:
    return {"agent_id": agent, "phase": phase, "version": "1.0.0",
            "model": "claude-sonnet-4-6", "start": start, "end": end, "run_id": "R1"}


def _request(epoch: float, before: int, after: int, latency: int = 100) -> dict:
    return {"epoch": epoch, "model": "claude-sonnet-4-6", "before": before,
            "after": after, "latency_ms": latency, "request_id": "x"}


# ─── Fuso horário ────────────────────────────────────────────────────────────

def test_utc_e_brz_convergem_no_mesmo_instante():
    """`10:00Z` (proxy) e `07:00-03:00` (observer) são o MESMO instante.

    Tratar os dois como locais deslocaria as janelas em 3h e a atribuição
    devolveria zero — o bug mais provável desta feature.
    """
    utc = ht._parse_epoch("2026-07-30T10:00:00Z")
    brz = ht._parse_epoch("2026-07-30T07:00:00-03:00")
    assert utc == brz


def test_timestamp_sem_fuso_assume_utc_no_proxy():
    naive = ht._parse_epoch("2026-07-30T10:00:00", assume_utc=True)
    assert naive == ht._parse_epoch("2026-07-30T10:00:00Z")


def test_timestamp_sem_fuso_assume_brz_no_observer():
    naive = ht._parse_epoch("2026-07-30T10:00:00", assume_utc=False)
    assert naive == ht._parse_epoch("2026-07-30T10:00:00-03:00")


def test_parse_epoch_tolera_lixo():
    assert ht._parse_epoch(None) is None
    assert ht._parse_epoch("") is None
    assert ht._parse_epoch("nao-e-data") is None
    assert ht._parse_epoch(1750000000) == 1750000000.0


# ─── Atribuição ──────────────────────────────────────────────────────────────

def test_agente_exclusivo_recebe_tudo():
    windows = [_window("ava-a", 100, 200)]
    buckets, orphans = ht.attribute_requests(windows, [_request(150, 10000, 3000)])
    assert orphans["requests"] == 0
    assert buckets["ava-a"]["before"] == 10000
    assert buckets["ava-a"]["after"] == 3000
    assert buckets["ava-a"]["ambiguous_requests"] == 0


def test_dispatch_paralelo_divide_e_marca_ambiguo():
    """Duas janelas sobrepostas → 1/N para cada, com a ambiguidade explícita."""
    windows = [_window("ava-a", 100, 200), _window("ava-b", 150, 250)]
    buckets, _ = ht.attribute_requests(windows, [_request(175, 10000, 2000)])
    assert buckets["ava-a"]["before"] == 5000
    assert buckets["ava-b"]["before"] == 5000
    assert buckets["ava-a"]["ambiguous_requests"] == 1
    assert buckets["ava-a"]["max_overlap"] == 2


def test_tres_agentes_sobrepostos_dividem_por_tres():
    windows = [_window(f"ava-{i}", 100, 200) for i in "abc"]
    buckets, _ = ht.attribute_requests(windows, [_request(150, 3000, 300)])
    assert all(round(b["before"]) == 1000 for b in buckets.values())
    assert all(b["max_overlap"] == 3 for b in buckets.values())


def test_requisicao_fora_de_janela_vai_para_o_bucket_orfao():
    """Orquestrador entre dispatches, ou agente que não chamou `track`."""
    windows = [_window("ava-a", 100, 200)]
    buckets, orphans = ht.attribute_requests(windows, [_request(500, 9000, 1000)])
    assert buckets == {}
    assert orphans["requests"] == 1
    assert orphans["before"] == 9000


def test_conservacao_de_tokens():
    """Nada some nem é contado duas vezes: atribuído + órfão == total."""
    windows = [_window("ava-a", 0, 100), _window("ava-b", 50, 150)]
    requests = [_request(10, 1000, 100), _request(75, 2000, 200), _request(999, 500, 50)]
    buckets, orphans = ht.attribute_requests(windows, requests)
    total = sum(b["before"] for b in buckets.values()) + orphans["before"]
    assert total == 3500


def test_bordas_da_janela_sao_inclusivas():
    windows = [_window("ava-a", 100, 200)]
    buckets, orphans = ht.attribute_requests(
        windows, [_request(100, 10, 1), _request(200, 10, 1)])
    assert buckets["ava-a"]["requests"] == 2
    assert orphans["requests"] == 0


# ─── Leitura do log do proxy ─────────────────────────────────────────────────

def test_le_o_jsonl_do_proxy(tmp_path):
    log = tmp_path / "proxy.jsonl"
    log.write_text(
        json.dumps({"timestamp": "2026-07-30T10:00:00Z", "model": "m",
                    "tokens_before": 100, "tokens_after": 40, "latency_ms": 12}) + "\n"
        + json.dumps({"timestamp": "2026-07-30T10:00:01Z", "model": "m",
                      "tokens_before": 200, "tokens_after": 80}) + "\n",
        encoding="utf-8")
    requests = ht._read_proxy_log(log)
    assert len(requests) == 2
    assert requests[0]["before"] == 100
    assert requests[1]["latency_ms"] == 0


def test_descarta_linhas_inutilizaveis(tmp_path):
    """Esquema do proxy não é contratual — linha ruim é ignorada, não explode."""
    log = tmp_path / "proxy.jsonl"
    log.write_text("\n".join([
        "nao e json",
        json.dumps({"timestamp": "2026-07-30T10:00:00Z"}),          # sem tokens
        json.dumps({"tokens_before": 1, "tokens_after": 1}),        # sem tempo
        json.dumps([1, 2, 3]),                                       # nem dict
        "",
        json.dumps({"ts": "2026-07-30T10:00:02Z", "tokens_in": 10, "tokens_out": 5}),
    ]) + "\n", encoding="utf-8")
    requests = ht._read_proxy_log(log)
    assert len(requests) == 1, "só a última linha é utilizável (via aliases ts/tokens_in)"
    assert requests[0]["before"] == 10


def test_log_ausente_devolve_vazio(tmp_path):
    assert ht._read_proxy_log(tmp_path / "nao-existe.jsonl") == []


# ─── Janelas a partir do estado ──────────────────────────────────────────────

def _write_state(tmp_path: Path, agents: dict) -> None:
    obs = tmp_path / "projects" / "P" / "outputs" / "observability"
    obs.mkdir(parents=True, exist_ok=True)
    (obs / "pipeline-run-state.json").write_text(
        json.dumps({"run_id": "R1", "agents": agents}), encoding="utf-8")


def test_janela_reconstruida_a_partir_da_duracao(tmp_path, monkeypatch):
    """`cmd_track` grava start == end (os agentes só passam --duration-ms).

    Sem reconstruir `[fim − duração, fim]` toda janela teria largura zero e a
    atribuição devolveria zero para todo mundo.
    """
    monkeypatch.setattr(ht, "REPO_ROOT", tmp_path)
    fim = datetime(2026, 7, 30, 10, 0, 0, tzinfo=BRZ)
    marca = fim.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    _write_state(tmp_path, {"ava-a": {"phase": "F1", "version": "1.0.0",
                                      "start_time": marca, "end_time": marca,
                                      "duration_ms": 60000, "model": "m"}})
    windows = ht._agent_windows("P")
    assert len(windows) == 1
    assert round(windows[0]["end"] - windows[0]["start"]) == 60


def test_janela_respeita_start_time_explicito(tmp_path, monkeypatch):
    monkeypatch.setattr(ht, "REPO_ROOT", tmp_path)
    inicio = datetime(2026, 7, 30, 10, 0, 0, tzinfo=BRZ)
    fim = inicio + timedelta(seconds=300)
    _write_state(tmp_path, {"ava-a": {
        "phase": "F1", "version": "1.0.0",
        "start_time": inicio.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
        "end_time": fim.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
        "duration_ms": 300000, "model": "m"}})
    windows = ht._agent_windows("P")
    assert round(windows[0]["end"] - windows[0]["start"]) == 300


def test_estado_ausente_degrada(tmp_path, monkeypatch):
    monkeypatch.setattr(ht, "REPO_ROOT", tmp_path)
    assert ht._agent_windows("nao-existe") == []


def test_agente_sem_end_time_e_ignorado(tmp_path, monkeypatch):
    monkeypatch.setattr(ht, "REPO_ROOT", tmp_path)
    _write_state(tmp_path, {"ava-a": {"phase": "F1", "duration_ms": 1000}})
    assert ht._agent_windows("P") == []


# ─── Ponta a ponta ───────────────────────────────────────────────────────────

def test_ponta_a_ponta_proxy_utc_para_agentes_brz(tmp_path, monkeypatch):
    """Cenário completo: log em UTC, estado em BRZ, um exclusivo e dois paralelos."""
    monkeypatch.setattr(ht, "REPO_ROOT", tmp_path)
    base_utc = datetime(2026, 7, 30, 13, 0, 0, tzinfo=timezone.utc)

    def marca_brz(offset: int) -> str:
        return (base_utc + timedelta(seconds=offset)).astimezone(BRZ).strftime(
            "%Y-%m-%dT%H:%M:%S-03:00")

    _write_state(tmp_path, {
        "ava-a": {"phase": "F1", "version": "1.0.0", "start_time": marca_brz(60),
                  "end_time": marca_brz(60), "duration_ms": 60000, "model": "m"},
        "ava-b": {"phase": "F1", "version": "1.0.0", "start_time": marca_brz(200),
                  "end_time": marca_brz(200), "duration_ms": 100000, "model": "m"},
        "ava-c": {"phase": "F1", "version": "1.0.0", "start_time": marca_brz(200),
                  "end_time": marca_brz(200), "duration_ms": 100000, "model": "m"},
    })
    log = tmp_path / "proxy.jsonl"
    log.write_text("\n".join(json.dumps({
        "timestamp": (base_utc + timedelta(seconds=off)).isoformat().replace("+00:00", "Z"),
        "tokens_before": before, "tokens_after": after, "latency_ms": 10,
    }) for off, before, after in [(30, 10000, 3000), (150, 40000, 10000), (900, 1, 1)]
    ) + "\n", encoding="utf-8")

    buckets, orphans = ht.attribute_requests(
        ht._agent_windows("P"), ht._read_proxy_log(log))

    assert buckets["ava-a"]["before"] == 10000          # exclusivo
    assert buckets["ava-b"]["before"] == 20000          # metade
    assert buckets["ava-c"]["before"] == 20000          # metade
    assert orphans["requests"] == 1                     # fora de tudo


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
