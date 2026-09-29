"""
Testes de `src/shared/tools/speckit_compliance_normalize.py`.

Protege o mecanismo determinístico que fecha a lacuna medida em produção
(`nopcommerce-04-cli-ava`, 2026-08-19): `ava-speckit-compliance` gravou
`compliance-summary.json` com o schema de `ava-deliverable-security-compliance`
em vez de `compliance-status.json` no schema canônico da F3S, e o exit gate
determinístico bloqueou a F4 corretamente porque o arquivo declarado nunca
existiu.

Roda com o Python do repo:
    python -m pytest tests/ava-fabric-agents/speckit/test_speckit_compliance_normalize.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path



REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_PY = REPO_ROOT / "src" / "shared" / "tools" / "speckit_compliance_normalize.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


norm = _load(TOOL_PY, "speckit_compliance_normalize_under_test")


def _speckit_dir(tmp_path: Path, project: str = "acme") -> Path:
    d = tmp_path / "projects" / project / "outputs" / "tobe" / "speckit"
    d.mkdir(parents=True)
    return d


def test_noop_quando_canonico_ja_valido(tmp_path: Path):
    d = _speckit_dir(tmp_path)
    (d / "compliance-status.json").write_text(json.dumps({
        "verdict": "APPROVED", "constitution_items": 10, "findings": [],
    }), encoding="utf-8")

    result = norm.normalize("acme", tmp_path)

    assert result["status"] == "OK"
    assert result["action"] == "none"


def test_normaliza_partir_de_compliance_summary_deviant(tmp_path: Path):
    d = _speckit_dir(tmp_path)
    (d / "compliance-report.md").write_text("# report", encoding="utf-8")
    (d / "compliance-summary.json").write_text(json.dumps({
        "project": "acme",
        "trace_id": "trace-123",
        "result": "COMPLIANT_WITH_WARNINGS",
        "recommendation": "APPROVED_FOR_F4",
        "blocking_issues": 0,
        "warnings": 3,
        "metrics": {
            "architectural_principles_total": 10, "architectural_principles_compliant": 10,
            "binding_decisions_total": 20, "binding_decisions_compliant": 20,
            "constraints_total": 15, "constraints_compliant": 15,
        },
    }), encoding="utf-8")

    result = norm.normalize("acme", tmp_path)

    assert result["status"] == "OK"
    assert result["action"] == "normalized"
    assert result["verdict"] == "APPROVED_WITH_FINDINGS"

    canonical = json.loads((d / "compliance-status.json").read_text(encoding="utf-8"))
    assert canonical["verdict"] == "APPROVED_WITH_FINDINGS"
    assert canonical["constitution_items"] == 45
    assert canonical["items_honored"] == 45
    # Um único finding-ponteiro, não um por warning. O schema desviante trazia
    # só a CONTAGEM (warnings=3) e nenhum texto: emitir três achados idênticos
    # criava volume sem informação. O ponteiro diz onde está o texto original.
    assert len(canonical["findings"]) == 1
    assert "compliance-report.md" in canonical["findings"][0]["artifact"]
    assert "warnings=3" in canonical["findings"][0]["evidence"]
    assert canonical["_normalized_from"].endswith("compliance-summary.json")
    # compliance-summary.json is left in place as audit evidence, not deleted.
    assert (d / "compliance-summary.json").is_file()


def test_mapeia_blocked_com_seguranca_quando_shape_desconhecido(tmp_path: Path):
    d = _speckit_dir(tmp_path)
    (d / "compliance-summary.json").write_text(json.dumps({
        "result": "SOMETHING_UNRECOGNIZED",
    }), encoding="utf-8")

    result = norm.normalize("acme", tmp_path)

    assert result["status"] == "OK"
    assert result["verdict"] == "BLOCKED"


def test_recupera_artefato_escrito_em_deliverables(tmp_path: Path):
    """O agente grava em outputs/deliverables/ apesar da instrução explícita.

    Medido em nopcommerce-04 (2026-08-21): 731k tokens de análise correta foram
    para `outputs/deliverables/speckit-compliance-{report.md,summary.json}`. A
    tool só varria `outputs/tobe/speckit/`, declarou "nada encontrado" e saiu
    com 1 — o trabalho ficou em disco, inutilizável.
    """
    d = _speckit_dir(tmp_path)
    deliverables = tmp_path / "projects" / "acme" / "outputs" / "deliverables"
    deliverables.mkdir(parents=True)
    (deliverables / "speckit-compliance-report.md").write_text(
        "# Relatório do agente\n\nconteúdo real", encoding="utf-8")
    (deliverables / "speckit-compliance-summary.json").write_text(json.dumps({
        "project_name": "acme",
        "compliance_gate": "CONDITIONAL",
        "recommendation": "CONDITIONAL_PROCEED",
        "constitution_compliance": {
            "principles_covered": 10, "principles_total": 10,
            "mandatory_decisions_traced": 20, "mandatory_decisions_total": 20,
            "constraints_enforced": 20, "constraints_total": 20,
            "status": "PASS",
        },
        "edge_cases": {"critical_blocker_details": [
            {"id": "EDGE-W0-002", "description": "CMK não definido",
             "wave_blocked": "W0", "owner": "Tech Lead", "impact": "BLOCKER"},
        ]},
        "conditions_for_approved": ["Resolver EDGE-W0-002"],
    }), encoding="utf-8")

    result = norm.normalize("acme", tmp_path)

    assert result["status"] == "OK"
    assert result["verdict"] == "APPROVED_WITH_FINDINGS"
    # O relatório humano do agente é materializado no caminho canônico.
    assert (d / "compliance-report.md").read_text(encoding="utf-8") == \
        "# Relatório do agente\n\nconteúdo real"

    canonical = json.loads((d / "compliance-status.json").read_text(encoding="utf-8"))
    assert canonical["_agent_output_recovered"] is True
    # `constraints_total` participa de dois pares de contagem; contá-lo duas
    # vezes inflava o denominador (50/70 onde o certo é 50/50).
    assert (canonical["items_honored"], canonical["constitution_items"]) == (50, 50)
    resumos = [f["summary"] for f in canonical["findings"]]
    assert "CMK não definido" in resumos
    assert "Resolver EDGE-W0-002" in resumos


def test_blocker_repetido_em_duas_chaves_nao_duplica(tmp_path: Path):
    """`edge_cases` e `blocked_by` descrevem o mesmo blocker com campos distintos."""
    d = _speckit_dir(tmp_path)
    (d / "compliance-summary.json").write_text(json.dumps({
        "result": "BLOCKED",
        "edge_cases": {"critical_blocker_details": [
            {"id": "EDGE-1", "description": "curto", "owner": "LT"},
        ]},
        "blocked_by": [
            {"id": "EDGE-1", "severity": "CRITICAL", "finding": "texto longo",
             "evidence": "spec.md § 9"},
        ],
    }), encoding="utf-8")

    result = norm.normalize("acme", tmp_path)

    canonical = json.loads((d / "compliance-status.json").read_text(encoding="utf-8"))
    assert result["verdict"] == "BLOCKED"
    assert len(canonical["findings"]) == 1
    achado = canonical["findings"][0]
    # A primeira fonte define o texto; a segunda completa o que faltava.
    assert "EDGE-1" in achado["evidence"] and "spec.md § 9" in achado["evidence"]
    assert achado["remediation"].startswith("responsável: LT")


def test_sempre_grava_os_dois_artefatos_mesmo_sem_nada_do_agente(tmp_path: Path):
    """Requisito explícito: o arquivo tem de existir, aconteça o que acontecer.

    Sair sem gravar deixava o operador sem nada para ler e a fase sem nada a
    mostrar. O fallback é fail-safe, não fail-silent: veredito BLOCKED e
    procedência explícita de que o agente não entregou.
    """
    d = _speckit_dir(tmp_path)
    (d / "checks-report.json").write_text(json.dumps({"results": [
        {"suite": "s", "name": "CHK-SK-007", "passed": False,
         "detail": "1/25 sem task: BR-ORDER-005"},
        {"suite": "s", "name": "CHK-SK-001", "passed": True, "detail": ""},
    ]}), encoding="utf-8")
    (d / "compile-warnings.json").write_text(json.dumps({"warnings": [
        {"code": "C004", "owner": "T-CAT-001", "message": "consume sem produtor",
         "fix": "regere o plano"},
    ]}), encoding="utf-8")

    result = norm.normalize("acme", tmp_path)

    assert result["status"] == "FALLBACK"
    assert (d / "compliance-status.json").is_file()
    assert (d / "compliance-report.md").is_file()

    canonical = json.loads((d / "compliance-status.json").read_text(encoding="utf-8"))
    assert canonical["verdict"] == "BLOCKED"
    assert canonical["_agent_output_recovered"] is False
    assert norm._is_valid_canonical(canonical)
    # A evidência determinística vira achado; o check que PASSOU não vira.
    evidencias = " ".join(f["evidence"] for f in canonical["findings"])
    assert "BR-ORDER-005" in evidencias
    assert not any("CHK-SK-001" in f["summary"] for f in canonical["findings"])
    assert any("consume sem produtor" in f["summary"] for f in canonical["findings"])
    # O relatório diz, em letras, que isto não substitui a análise do agente.
    texto = (d / "compliance-report.md").read_text(encoding="utf-8")
    assert "BLOCKED" in texto and "NÃO substitui" in texto


def test_veredito_do_agente_e_preservado_com_check_de_coerencia(tmp_path: Path):
    """Veredito favorável carregando achado crítico é sinalizado, não sobrescrito."""
    d = _speckit_dir(tmp_path)
    (d / "compliance-summary.json").write_text(json.dumps({
        "result": "COMPLIANT_WITH_WARNINGS",
        "blocked_by": [{"id": "B-1", "severity": "CRITICAL", "finding": "grave"}],
    }), encoding="utf-8")

    norm.normalize("acme", tmp_path)

    canonical = json.loads((d / "compliance-status.json").read_text(encoding="utf-8"))
    check = canonical["_verdict_rule_check"]
    assert canonical["verdict"] == "APPROVED_WITH_FINDINGS"  # não sobrescrito
    assert check["consistent"] is False
    assert check["high_or_critical_findings"] == ["NORM-001"]


def test_idempotente_segunda_execucao_e_noop(tmp_path: Path):
    d = _speckit_dir(tmp_path)
    (d / "compliance-summary.json").write_text(json.dumps({
        "result": "COMPLIANT", "warnings": 0, "blocking_issues": 0,
    }), encoding="utf-8")

    first = norm.normalize("acme", tmp_path)
    second = norm.normalize("acme", tmp_path)

    assert first["action"] == "normalized"
    assert second["action"] == "none"


def test_cli_nunca_bloqueia_a_fase_e_sempre_deixa_artefato(tmp_path: Path, monkeypatch):
    """Exit 0 mesmo no fallback — a tool existe para acabar com fase sem artefato.

    Antes retornava 1 aqui: o runner levantava RuntimeError, a fase virava
    falha e o diretório continuava sem `compliance-status.json` para ler. O
    veredito BLOCKED no arquivo é o canal correto para "não conforme".
    """
    d = _speckit_dir(tmp_path)
    monkeypatch.setattr(norm, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["speckit_compliance_normalize.py", "-p", "acme", "--json"])

    exit_code = norm.main()

    assert exit_code == 0
    assert (d / "compliance-status.json").is_file()
    assert (d / "compliance-report.md").is_file()
    canonical = json.loads((d / "compliance-status.json").read_text(encoding="utf-8"))
    assert canonical["verdict"] == "BLOCKED"


# ── Assinatura humana atravessa a re-normalização ────────────────────────────
# `normalize()` reescreve compliance-status.json INTEIRO. Sem cuidado, rodar a
# wave6b de novo apagaria a decisão gravada na wave6c — o gate viraria teatro:
# assina, e o passo seguinte limpa.

def _com_traceability(d: Path, checksum: str = "abc") -> None:
    (d / "traceability.json").write_text(
        json.dumps({"graph_checksum": checksum}), encoding="utf-8")


def _canonico_assinado(fingerprint: str) -> dict:
    return {
        "verdict": "BLOCKED",
        "constitution_items": 10,
        "items_honored": 5,
        "findings": [{"id": "F-1", "severity": "critical", "summary": "grave"}],
        "approval": {
            "status": "approved",
            "reviewer": "Rafael Almeida",
            "reviewer_role": "Tech Lead",
            "approved_at": "2026-08-21T11:40:00-03:00",
            "approved_fingerprint": fingerprint,
        },
    }


def test_assinatura_sobrevive_a_renormalizacao(tmp_path: Path):
    d = _speckit_dir(tmp_path)
    _com_traceability(d)
    # Origem desviante presente: força o caminho que RE-ESCREVE o canônico.
    (d / "compliance-summary.json").write_text(json.dumps({
        "result": "BLOCKED",
        "blocked_by": [{"id": "F-1", "severity": "CRITICAL", "finding": "grave"}],
    }), encoding="utf-8")
    norm.normalize("acme", tmp_path)

    # Assina o conteúdo que acabou de ser normalizado.
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    import speckit_compliance_gate as gate  # noqa: PLC0415
    gate.record("acme", "approved", name="Rafael Almeida", role="Tech Lead",
                repo_root=tmp_path)

    norm.normalize("acme", tmp_path)  # wave6b roda de novo

    aprovacao = json.loads(
        (d / "compliance-status.json").read_text(encoding="utf-8"))["approval"]
    assert aprovacao["status"] == "approved"
    assert aprovacao["reviewer"] == "Rafael Almeida"


def test_assinatura_de_outro_conteudo_vira_expired(tmp_path: Path):
    """Rebaixada, não descartada: quem auditar precisa ver que houve decisão."""
    d = _speckit_dir(tmp_path)
    _com_traceability(d)
    (d / "compliance-status.json").write_text(
        json.dumps(_canonico_assinado("sha256:de-outro-conteudo")), encoding="utf-8")
    (d / "compliance-summary.json").write_text(json.dumps({
        "result": "BLOCKED",
        "blocked_by": [{"id": "F-9", "severity": "CRITICAL", "finding": "outro"}],
    }), encoding="utf-8")

    norm.normalize("acme", tmp_path)

    aprovacao = json.loads(
        (d / "compliance-status.json").read_text(encoding="utf-8"))["approval"]
    assert aprovacao["status"] == "expired"
    assert aprovacao["previous_status"] == "approved"
    assert aprovacao["reviewer"] == "Rafael Almeida"   # o histórico permanece
    assert "não cobre o conteúdo atual" in aprovacao["expired_reason"]


def test_fallback_tambem_preserva_a_assinatura(tmp_path: Path):
    """O caminho sem artefato do agente também não pode apagar a decisão."""
    d = _speckit_dir(tmp_path)
    _com_traceability(d)
    (d / "compliance-status.json").write_text(
        json.dumps({"approval": {"status": "rejected", "reviewer": "Ana",
                                 "approved_fingerprint": "sha256:antigo"}}),
        encoding="utf-8")

    resultado = norm.normalize("acme", tmp_path)

    assert resultado["status"] == "FALLBACK"
    aprovacao = json.loads(
        (d / "compliance-status.json").read_text(encoding="utf-8"))["approval"]
    assert aprovacao["reviewer"] == "Ana"
    assert aprovacao["status"] == "expired"
