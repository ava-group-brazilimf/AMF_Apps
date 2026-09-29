"""
Testes da detecção de subagente morto e do re-check do gate.

Contexto medido em 56 sessões (`~/.copilot/session-state/*/events.jsonl`):

    task            / claude-sonnet-4    950 dispatches   10 sem tool call (1%)
    general-purpose / gpt-5.4             54 dispatches   53 sem tool call (98%)
    explore         / gpt-5.4-mini        24 dispatches   19 sem tool call (79%)

Sob provider BYOK, os tipos embutidos trazem modelo próprio; a troca dispara
validação do wire model, que retorna 404, e o subagente morre antes da primeira
ferramenta — com o orquestrador seguindo como se tivesse recebido resultado.

    python -m pytest tests/tools/test_session_health.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
UTILS_DIR = REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "asis-diagnostic" / "utils"
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(UTILS_DIR))

import agent_runner  # noqa: E402
import artifact_gate  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


health = _load(TOOLS_DIR / "check_session_health.py", "check_session_health")


def _events(tmp_path: Path, *events: dict) -> Path:
    session = tmp_path / "sessao"
    session.mkdir(parents=True, exist_ok=True)
    path = session / "events.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    return path


# ─── check_session_health ────────────────────────────────────────────────────

def test_detecta_subagente_fora_do_modelo_byok(tmp_path):
    path = _events(
        tmp_path,
        {"type": "subagent.started", "data": {"agentName": "general-purpose", "model": "gpt-5.4"}},
        {"type": "session.error", "data": {"statusCode": 404,
         "message": "Model 'claude-sonnet-4-6' not found on provider at http://127.0.0.1:8787"}},
        {"type": "subagent.completed", "data": {"agentName": "general-purpose", "totalToolCalls": 0}},
    )
    report = health.analyze(path, "claude-sonnet-4")
    assert not report["healthy"]
    assert len(report["foreign_model"]) == 1
    assert len(report["empty"]) == 1
    assert report["model_404"][0]["endpoint"] == "proxy Headroom"


def test_sessao_saudavel_passa(tmp_path):
    path = _events(
        tmp_path,
        {"type": "subagent.started", "data": {"agentName": "task", "model": "claude-sonnet-4"}},
        {"type": "subagent.completed", "data": {"agentName": "task", "totalToolCalls": 12}},
    )
    report = health.analyze(path, "claude-sonnet-4")
    assert report["healthy"]
    assert report["foreign_model"] == [] and report["empty"] == []


def test_total_tool_calls_ausente_nao_e_zero(tmp_path):
    """Sem o campo, o resultado é DESCONHECIDO — tratá-lo como 0 acusava 770
    `task` mortos onde havia 10."""
    path = _events(
        tmp_path,
        {"type": "subagent.started", "data": {"agentName": "task", "model": "claude-sonnet-4"}},
        {"type": "subagent.completed", "data": {"agentName": "task"}},
    )
    report = health.analyze(path, "claude-sonnet-4")
    assert report["subagents"][0]["tool_calls"] is None
    assert report["empty"] == []
    assert report["healthy"]


def test_linha_corrompida_nao_derruba_analise(tmp_path):
    session = tmp_path / "s"
    session.mkdir()
    path = session / "events.jsonl"
    path.write_text(
        json.dumps({"type": "subagent.started",
                    "data": {"agentName": "task", "model": "claude-sonnet-4"}})
        + "\n{ json parcial sem fechar",
        encoding="utf-8",
    )
    report = health.analyze(path, "claude-sonnet-4")
    assert report["total"] == 1


def test_endpoint_classifica_rota(tmp_path):
    assert health._endpoint_of("... at http://127.0.0.1:8787 ...") == "proxy Headroom"
    assert health._endpoint_of("... services.ai.azure.com/anthropic ...") == "direto Foundry"
    assert health._endpoint_of("qualquer outra coisa") == "desconhecida"


# ─── agent_runner: subagente vazio vira config_error ─────────────────────────

def test_subagente_fora_do_byok_e_config_error():
    facts = {"subagents": [{"agent": "general-purpose", "model": "gpt-5.4", "tool_calls": 0}]}
    status, detail = agent_runner._classify(0, False, facts, {"complete": True}, "claude-sonnet-4")
    assert status == "config_error"
    assert "gpt-5.4" in detail


def test_subagente_sem_tool_call_e_config_error():
    facts = {"subagents": [{"agent": "task", "model": "claude-sonnet-4", "tool_calls": 0}]}
    status, detail = agent_runner._classify(0, False, facts, {"complete": True}, "claude-sonnet-4")
    assert status == "config_error"
    assert "0 tool calls" in detail


def test_config_error_vem_antes_do_gate_de_artefato():
    """Se o subagente morreu, o artefato ausente é consequência — reportar a causa."""
    facts = {"subagents": [{"agent": "general-purpose", "model": "gpt-5.4", "tool_calls": 0}]}
    status, detail = agent_runner._classify(
        0, False, facts, {"complete": False, "missing": [{"path": "x.md"}]}, "claude-sonnet-4")
    assert status == "config_error"
    assert "artefato" not in detail


def test_subagente_saudavel_nao_interfere():
    facts = {"subagents": [{"agent": "task", "model": "claude-sonnet-4", "tool_calls": 5}]}
    assert agent_runner._classify(0, False, facts, {"complete": True},
                                  "claude-sonnet-4")[0] == "completed"


def test_tool_calls_desconhecido_nao_reprova():
    facts = {"subagents": [{"agent": "task", "model": "claude-sonnet-4", "tool_calls": None}]}
    assert agent_runner._classify(0, False, facts, {"complete": True},
                                  "claude-sonnet-4")[0] == "completed"


def test_read_session_facts_extrai_subagentes(tmp_path, monkeypatch):
    path = _events(
        tmp_path,
        {"type": "subagent.started", "data": {"agentName": "explore", "model": "gpt-5.4-mini"}},
        {"type": "subagent.completed", "data": {"agentName": "explore", "totalToolCalls": 0}},
    )
    monkeypatch.setattr(agent_runner, "session_events_path", lambda _sid: path)
    facts = agent_runner.read_session_facts("qualquer")
    assert facts["subagents"] == [
        {"agent": "explore", "model": "gpt-5.4-mini", "tool_calls": 0}
    ]
    assert agent_runner.subagent_problems(facts, "claude-sonnet-4")


# ─── artifact_gate: re-check só no caminho negativo ──────────────────────────

def _run_gate_cli(monkeypatch, resultados, argv):
    chamadas = {"n": 0}

    def fake_check_agent(_project, _agent):
        chamadas["n"] += 1
        return resultados[min(chamadas["n"] - 1, len(resultados) - 1)]

    monkeypatch.setattr(artifact_gate, "check_agent", fake_check_agent)
    monkeypatch.setattr(artifact_gate.Path, "is_dir", lambda _self: True)
    monkeypatch.setattr(sys, "argv", ["artifact_gate.py", *argv])
    dormiu = {"s": 0.0}
    monkeypatch.setattr(artifact_gate.time, "sleep", lambda s: dormiu.__setitem__("s", s))
    code = artifact_gate.main()
    return code, chamadas["n"], dormiu["s"]


COMPLETO = {"complete": True, "present": [], "missing": [], "should_dispatch": False}
INCOMPLETO = {"complete": False, "present": [], "missing": [{"path": "x.md"}],
              "should_dispatch": True}


def test_gate_completo_nao_recheca(monkeypatch, capsys):
    code, chamadas, dormiu = _run_gate_cli(
        monkeypatch, [COMPLETO],
        ["--project", "P", "--agent", "ava-asis-inventory", "--recheck-ms", "1500", "--json"])
    capsys.readouterr()
    assert code == 0 and chamadas == 1 and dormiu == 0.0


def test_gate_incompleto_sem_flag_nao_recheca(monkeypatch, capsys):
    code, chamadas, dormiu = _run_gate_cli(
        monkeypatch, [INCOMPLETO],
        ["--project", "P", "--agent", "ava-asis-inventory", "--json"])
    capsys.readouterr()
    assert code == 1 and chamadas == 1 and dormiu == 0.0


def test_gate_incompleto_com_flag_recheca_uma_vez_e_resgata(monkeypatch, capsys):
    code, chamadas, dormiu = _run_gate_cli(
        monkeypatch, [INCOMPLETO, COMPLETO],
        ["--project", "P", "--agent", "ava-asis-inventory", "--recheck-ms", "1500", "--json"])
    saida = json.loads(capsys.readouterr().out)
    assert code == 0 and chamadas == 2 and dormiu == 1.5
    assert saida["rescued_on_recheck"] == 1500


def test_gate_recheck_nao_mascara_arquivo_realmente_ausente(monkeypatch, capsys):
    """Bug de path continua reprovando — o re-check não é um sleep que esconde."""
    code, chamadas, _ = _run_gate_cli(
        monkeypatch, [INCOMPLETO, INCOMPLETO],
        ["--project", "P", "--agent", "ava-asis-inventory", "--recheck-ms", "1500", "--json"])
    capsys.readouterr()
    assert code == 1 and chamadas == 2
