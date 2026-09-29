"""
Testes de `src/shared/tools/speckit_compliance_gate.py`.

Protege o gate de aprovação humana da F3S, criado a partir do que foi medido em
`nopcommerce-04` (2026-08-21): a F4 foi liberada com `verdict:
APPROVED_WITH_FINDINGS` carregando dois blockers CRITICAL — CMK do Always
Encrypted (EDGE-W0-002) e tecnologia de feature flags (EDGE-W0-005) — porque o
gate de saída conferia PRESENÇA de arquivo, não conteúdo. Tudo estava registrado
no JSON; nada levou aquilo até uma pessoa.

Roda com o Python do repo:
    python -m pytest tests/ava-fabric-agents/speckit/test_speckit_compliance_gate.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_PY = REPO_ROOT / "src" / "shared" / "tools" / "speckit_compliance_gate.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load(TOOL_PY, "speckit_compliance_gate_under_test")


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch):
    """Nenhum teste depende da rede.

    Sem isto, cada gravação tentaria 8 servidores NTP a 3s de timeout — 24s por
    teste numa máquina sem saída. O caminho do NTP bem-sucedido é exercitado por
    `test_timestamp_de_ntp_registra_o_servidor`, com o resolvedor substituído.
    """
    monkeypatch.setenv("AVA_NTP_FORCE_FAIL", "1")


def _projeto(tmp_path: Path, status: dict, *, project: str = "acme",
             graph_checksum: str = "abc123") -> Path:
    speckit = tmp_path / "projects" / project / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True, exist_ok=True)
    (speckit / "compliance-status.json").write_text(
        json.dumps(status), encoding="utf-8")
    (speckit / "traceability.json").write_text(
        json.dumps({"trace_id": "TR-1", "graph_checksum": graph_checksum}),
        encoding="utf-8")
    return speckit


def _status(verdict="APPROVED", findings=None, rule_consistent=True) -> dict:
    return {
        "schema_version": "1.0.0",
        "verdict": verdict,
        "constitution_items": 10,
        "items_honored": 10,
        "findings": findings or [],
        "_verdict_rule_check": {"consistent": rule_consistent, "note": "nota"},
    }


def _finding(fid: str, severity: str) -> dict:
    return {"id": fid, "severity": severity, "summary": f"achado {fid}",
            "evidence": "spec.md § 9", "remediation": "corrigir"}


# ── Critério de disparo ──────────────────────────────────────────────────────

def test_projeto_limpo_nao_exige_aprovacao(tmp_path: Path):
    _projeto(tmp_path, _status())

    estado = gate.gate_status("acme", tmp_path)

    assert estado["state"] == "not_required"
    assert estado["requires_approval"] is False


def test_verdict_blocked_dispara(tmp_path: Path):
    _projeto(tmp_path, _status(verdict="BLOCKED"))

    estado = gate.gate_status("acme", tmp_path)

    assert estado["requires_approval"] is True
    assert [t["code"] for t in estado["triggers"]] == ["VERDICT_BLOCKED"]


def test_finding_critical_dispara_mesmo_com_veredito_favoravel(tmp_path: Path):
    """O gatilho que o incidente de 2026-08-21 exigiu.

    O agente reportou `APPROVED_WITH_FINDINGS` sobre dois blockers CRITICAL.
    Confiar só no veredito é exatamente o que deixou aquilo passar.
    """
    _projeto(tmp_path, _status(
        verdict="APPROVED_WITH_FINDINGS",
        findings=[_finding("NORM-001", "critical"), _finding("NORM-002", "low")]))

    estado = gate.gate_status("acme", tmp_path)

    assert estado["requires_approval"] is True
    assert "HIGH_SEVERITY_FINDINGS" in [t["code"] for t in estado["triggers"]]
    assert [b["id"] for b in estado["blockers"]] == ["NORM-001"]


def test_veredito_incoerente_dispara(tmp_path: Path):
    _projeto(tmp_path, _status(rule_consistent=False))

    estado = gate.gate_status("acme", tmp_path)

    assert "VERDICT_RULE_INCONSISTENT" in [t["code"] for t in estado["triggers"]]


def test_status_ausente_fica_pendente(tmp_path: Path):
    (tmp_path / "projects" / "acme" / "outputs" / "tobe" / "speckit").mkdir(parents=True)

    estado = gate.gate_status("acme", tmp_path)

    assert estado["state"] == "pending"
    assert "ausente" in estado["detail"]


# ── Fingerprint ──────────────────────────────────────────────────────────────

def test_fingerprint_e_estavel_entre_leituras(tmp_path: Path):
    speckit = _projeto(tmp_path, _status(findings=[_finding("F-1", "high")]))
    status = json.loads((speckit / "compliance-status.json").read_text(encoding="utf-8"))

    assert gate.fingerprint(status, speckit) == gate.fingerprint(status, speckit)


def test_fingerprint_muda_com_achado_e_com_grafo(tmp_path: Path):
    speckit = _projeto(tmp_path, _status(findings=[_finding("F-1", "high")]))
    base = json.loads((speckit / "compliance-status.json").read_text(encoding="utf-8"))
    original = gate.fingerprint(base, speckit)

    outro = {**base, "findings": [_finding("F-2", "high")]}
    assert gate.fingerprint(outro, speckit) != original

    # Mesmo conteúdo de achados, grafo diferente: as tasks mudaram sob a
    # aprovação, então a assinatura não pode continuar valendo.
    (speckit / "traceability.json").write_text(
        json.dumps({"graph_checksum": "outro"}), encoding="utf-8")
    assert gate.fingerprint(base, speckit) != original


# ── Registro da decisão ──────────────────────────────────────────────────────

def test_aprovacao_nominal_grava_quem_papel_e_quando(tmp_path: Path):
    speckit = _projeto(tmp_path, _status(findings=[_finding("F-1", "critical")]))

    resultado = gate.record("acme", "approved", name="Rafael Almeida",
                            role="Tech Lead", repo_root=tmp_path)

    assert resultado["status"] == "OK"
    aprovacao = json.loads(
        (speckit / "compliance-status.json").read_text(encoding="utf-8"))["approval"]
    assert aprovacao["status"] == "approved"
    assert aprovacao["reviewer"] == "Rafael Almeida"
    assert aprovacao["reviewer_role"] == "Tech Lead"
    assert aprovacao["approved_at"]
    assert aprovacao["blockers_acknowledged"] == ["F-1"]
    assert gate.gate_status("acme", tmp_path)["state"] == "approved"


@pytest.mark.parametrize("nome,papel", [("", "Tech Lead"), ("Rafael", ""), ("", "")])
def test_aprovacao_anonima_e_recusada(tmp_path: Path, nome: str, papel: str):
    """Assinatura sem identificação não registra responsabilidade.

    É o único motivo de o gate existir — deixar passar aqui tornaria o resto
    cerimônia.
    """
    _projeto(tmp_path, _status(verdict="BLOCKED"))

    resultado = gate.record("acme", "approved", name=nome, role=papel,
                            repo_root=tmp_path)

    assert resultado["status"] == "REFUSED"
    assert gate.gate_status("acme", tmp_path)["state"] == "pending"


def test_acknowledge_auto_nao_inventa_revisor(tmp_path: Path):
    """`auto_acknowledged` é estado próprio, não `approved` com nome falso."""
    speckit = _projeto(tmp_path, _status(verdict="BLOCKED"))

    resultado = gate.record("acme", "auto_acknowledged", runner_mode="auto",
                            repo_root=tmp_path)

    assert resultado["status"] == "OK"
    aprovacao = json.loads(
        (speckit / "compliance-status.json").read_text(encoding="utf-8"))["approval"]
    assert aprovacao["status"] == "auto_acknowledged"
    assert aprovacao["reviewer"] == ""
    assert "sem revisão humana" in aprovacao["note"]
    # Libera a F4 — em automático a esteira não trava —, mas o arquivo diz que
    # ninguém revisou.
    assert gate.gate_status("acme", tmp_path)["state"] == "auto_acknowledged"


def test_recusa_bloqueia_e_nomeia_quem_recusou(tmp_path: Path):
    _projeto(tmp_path, _status(verdict="BLOCKED"))

    gate.record("acme", "rejected", name="Rafael", role="Tech Lead",
                repo_root=tmp_path)

    estado = gate.gate_status("acme", tmp_path)
    assert estado["state"] == "rejected"
    assert "Rafael" in estado["detail"]


def test_decisao_com_fingerprint_divergente_e_recusada(tmp_path: Path):
    """Guarda contra assinar às cegas.

    O operador leu um conjunto de achados; entre ver e decidir, o conteúdo
    mudou. Assinar registraria ciência de algo que a pessoa não leu.
    """
    _projeto(tmp_path, _status(verdict="BLOCKED"))

    resultado = gate.record("acme", "approved", name="Rafael", role="TL",
                            expect_fingerprint="sha256:outra-coisa",
                            repo_root=tmp_path)

    assert resultado["status"] == "REFUSED"
    assert "mudaram" in resultado["detail"]


# ── Expiração ────────────────────────────────────────────────────────────────

def test_assinatura_expira_quando_os_achados_mudam(tmp_path: Path):
    speckit = _projeto(tmp_path, _status(findings=[_finding("F-1", "critical")]))
    gate.record("acme", "approved", name="Rafael", role="TL", repo_root=tmp_path)
    assert gate.gate_status("acme", tmp_path)["state"] == "approved"

    status = json.loads((speckit / "compliance-status.json").read_text(encoding="utf-8"))
    status["findings"] = [_finding("F-1", "critical"), _finding("F-9", "critical")]
    (speckit / "compliance-status.json").write_text(
        json.dumps(status), encoding="utf-8")

    estado = gate.gate_status("acme", tmp_path)
    assert estado["state"] == "expired"
    assert "não cobre o conteúdo atual" in estado["detail"]


def test_recusa_sobre_outros_achados_volta_a_pendente(tmp_path: Path):
    """Recusar não pode congelar o projeto para sempre.

    Corrigido o que foi recusado, os achados mudam e a decisão anterior deixa de
    ser sobre este conteúdo — reavaliar é o comportamento correto, sem exigir
    que alguém desfaça a recusa à mão.
    """
    speckit = _projeto(tmp_path, _status(verdict="BLOCKED",
                                         findings=[_finding("F-1", "critical")]))
    gate.record("acme", "rejected", name="Rafael", role="TL", repo_root=tmp_path)

    status = json.loads((speckit / "compliance-status.json").read_text(encoding="utf-8"))
    status["findings"] = [_finding("F-2", "critical")]
    (speckit / "compliance-status.json").write_text(json.dumps(status), encoding="utf-8")

    estado = gate.gate_status("acme", tmp_path)
    assert estado["state"] == "pending"
    assert "outros achados" in estado["detail"]


# ── Auditoria ────────────────────────────────────────────────────────────────

def test_log_e_append_only(tmp_path: Path):
    """Uma reaprovação não pode apagar a assinatura anterior."""
    speckit = _projeto(tmp_path, _status(verdict="BLOCKED"))

    gate.record("acme", "rejected", name="Ana", role="QA", repo_root=tmp_path)
    gate.record("acme", "approved", name="Rafael", role="TL", repo_root=tmp_path)

    linhas = [json.loads(l) for l in
              (speckit / "approval-log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [l["status"] for l in linhas] == ["rejected", "approved"]
    assert [l["reviewer"] for l in linhas] == ["Ana", "Rafael"]


def test_fallback_de_ntp_e_registrado_como_tal(tmp_path: Path):
    """Um timestamp de relógio local não pode se passar por hora NTP."""
    _projeto(tmp_path, _status(verdict="BLOCKED"))

    resultado = gate.record("acme", "approved", name="Rafael", role="TL",
                            repo_root=tmp_path)

    assert resultado["ntp_fallback"] is True
    assert "NTP indisponível" in resultado["approved_at_source"]


def test_timestamp_de_ntp_registra_o_servidor(tmp_path: Path, monkeypatch):
    _projeto(tmp_path, _status(verdict="BLOCKED"))
    monkeypatch.setattr(gate, "_trusted_timestamp",
                        lambda: ("2026-08-21T11:40:00-03:00", False, "a.st1.ntp.br"))

    resultado = gate.record("acme", "approved", name="Rafael", role="TL",
                            repo_root=tmp_path)

    assert resultado["ntp_fallback"] is False
    assert resultado["approved_at_source"] == "a.st1.ntp.br"
    assert resultado["approved_at"] == "2026-08-21T11:40:00-03:00"


# ── Avaliação (wave6c) ───────────────────────────────────────────────────────

def test_evaluate_grava_relatorio_e_nunca_reprova(tmp_path: Path, monkeypatch):
    """`--evaluate` sempre sai com 0: avaliar não é reprovar.

    Quem bloqueia é o gate de saída, ao ler o estado. Reprovar aqui devolveria a
    fase ao rótulo "⏭ pulado" que a política do pipeline eliminou.
    """
    speckit = _projeto(tmp_path, _status(verdict="BLOCKED"))
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv",
                        ["gate", "-p", "acme", "--evaluate", "--json"])

    assert gate.main() == 0

    payload = json.loads((speckit / "compliance-gate.json").read_text(encoding="utf-8"))
    assert payload["requires_approval"] is True
    assert payload["decision_pending"] is True
    assert payload["fingerprint"].startswith("sha256:")


def test_evaluate_em_projeto_limpo_nao_pede_decisao(tmp_path: Path, monkeypatch):
    speckit = _projeto(tmp_path, _status())
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["gate", "-p", "acme", "--evaluate", "--json"])

    assert gate.main() == 0

    payload = json.loads((speckit / "compliance-gate.json").read_text(encoding="utf-8"))
    assert payload["decision_pending"] is False
    assert payload["state"] == "not_required"
