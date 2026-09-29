"""A camada SpecKit é non-blocking enquanto está em evolução.

O que estes testes congelam, medido em `cadastro-funcionarios-04`:

1. **`--warn` dos checks nunca funcionou.** `src/shared/checks/cli.py` fazia
   `if not ok and args.warn:` com `ok` indefinido — `NameError` antes do
   `sys.exit(0)`, e o processo morria com exit 1, que é exatamente o que a flag
   existia para evitar. `speckit-dependency-checks` saía 1 com `--warn` no DAG.

2. **O fan-out do DAG perdia o `spec_path`.** `pipeline_plan.dag_steps()` não
   consultava o registry, então `load_skill` caía na busca heurística por
   substring, que ordena por (nível, TAMANHO) e escolhe o maior candidato:
   `ava-speckit-compliance` carregava
   `deliverables/agents/security-compliance-agent.md` (27KB, o agente de
   segurança da F7) em vez de `speckit/agents/compliance-agent.md` (14KB). O
   passo então gravava `outputs/deliverables/security-compliance-*` e o
   contrato da F3S ficava vazio — "falta: compliance-report.md,
   compliance-status.json" no dashboard.

3. **Insumo de outra fase reprovava a F3S.** `check_external_dependencies`
   retornava `FAIL` e `run_gate` saía antes de conferir um único artefato do
   próprio SpecKit.

4. **Fases F3S entravam em `val_failed`**, contando como reprovação no veredito
   global e aparecendo como "❌ Val-Fail" no dashboard.

Roda com o Python do repo::

    python -m pytest tests/tools/test_speckit_non_blocking.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_19 = REPO_ROOT / "ava-pipeline-runner-cli.py"
TOOLS = REPO_ROOT / "src" / "shared" / "tools"

sys.path.insert(0, str(TOOLS))

import pipeline_plan  # noqa: E402


@pytest.fixture(scope="module")
def runner():
    if not RUNNER_19.is_file():
        pytest.skip("ava-pipeline-runner-cli.py ausente neste checkout")
    spec = importlib.util.spec_from_file_location("runner19_speckit", RUNNER_19)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["runner19_speckit"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ═══════════════════════════════════════════════════════════════════════════
#  1 · `--warn` dos checks
# ═══════════════════════════════════════════════════════════════════════════

def test_cli_dos_checks_define_ok_antes_de_usar():
    """Regressão direta do `NameError` que anulava `--warn`."""
    import symtable
    fonte = (REPO_ROOT / "src" / "shared" / "checks" / "cli.py").read_text(
        encoding="utf-8")
    topo = symtable.symtable(fonte, "cli.py", "exec")
    funcao = next(t for t in topo.get_children() if t.get_name() == "main")
    simbolo = funcao.lookup("ok")
    assert simbolo.is_assigned(), (
        "`ok` é lido em cli.main() sem ser atribuído — `--warn` volta a "
        "levantar NameError e o exit code volta a ser 1")


def test_warn_dos_checks_sai_com_zero(monkeypatch, capsys):
    """Uma suíte reprovada com `--warn` sai 0; sem a flag, continua saindo 1."""
    import src.shared.checks as checks_pkg
    from src.shared.checks import cli as checks_cli

    class _Reporter:
        exit_code = 1          # falha estrutural

    monkeypatch.setattr(checks_pkg, "run_checks_detailed",
                        lambda *a, **k: _Reporter())

    def _rodar(*flags: str) -> int:
        monkeypatch.setattr(sys, "argv",
                            ["x", "--project", "P", "--suite",
                             "speckit_traceability", *flags])
        with pytest.raises(SystemExit) as exc:
            checks_cli.main()
        capsys.readouterr()
        return exc.value.code

    assert _rodar("--warn") == 0
    assert _rodar() == 1, "sem --warn o comportamento tem de ser o antigo"


# ═══════════════════════════════════════════════════════════════════════════
#  2 · spec_path no fan-out do DAG
# ═══════════════════════════════════════════════════════════════════════════

def test_dag_steps_resolve_spec_path_pelo_registry():
    passos = pipeline_plan.dag_steps("F3S", REPO_ROOT, project="cadastro-funcionarios")
    agentes = [p for p in passos if p.get("kind", "agent") == "agent"]
    assert agentes, "a F3S precisa expandir em agentes"
    for passo in agentes:
        assert passo.get("spec_path"), f"{passo['agent']} sem spec_path"
        assert (REPO_ROOT / passo["spec_path"]).is_file()


def test_compliance_carrega_o_agente_do_speckit_e_nao_o_de_seguranca(runner):
    """O defeito exato: o maior arquivo com 'compliance' no nome vencia."""
    passos = pipeline_plan.dag_steps("F3S", REPO_ROOT,
                                     project="cadastro-funcionarios")
    compliance = next(p for p in passos if p["agent"] == "ava-speckit-compliance")
    spec = compliance["spec_path"].replace("\\", "/")

    assert spec.endswith("speckit/agents/compliance-agent.md")
    assert "deliverables" not in spec
    assert "security-compliance" not in spec


def test_expansao_do_runner_propaga_spec_path(runner):
    passos = list(runner.PIPELINE)
    runner._expand_dag_phases(passos, "cadastro-funcionarios")
    agentes = [p for p in passos
               if str(p.get("phase", "")).startswith("F3S:")
               and p.get("kind", "agent") == "agent"]
    assert agentes
    for passo in agentes:
        assert passo.get("spec_path"), (
            f"{passo['agent']} perdeu o spec_path na expansão do runner — "
            f"load_skill volta à heurística por substring")


# ═══════════════════════════════════════════════════════════════════════════
#  3 · Dependências externas viraram aviso
# ═══════════════════════════════════════════════════════════════════════════

def test_dependencias_externas_nao_reprovam():
    gate_py = (REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "speckit"
               / "utils" / "artifact_gate_speckit.py")
    spec = importlib.util.spec_from_file_location("gate_nb", gate_py)
    gate = importlib.util.module_from_spec(spec)
    sys.modules["gate_nb"] = gate
    spec.loader.exec_module(gate)

    resultado = gate.check_external_dependencies("P", Path("/tmp/nao-existe"))
    assert resultado["status"] == "WARN"
    assert resultado["missing"], "o cenário precisa ter insumo ausente"


# ═══════════════════════════════════════════════════════════════════════════
#  4 · Predicado e efeitos no veredito global
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("phase,agent,esperado", [
    ("F3S", "ava-speckit-orchestrator", True),
    ("F3S:compliance", "ava-speckit-compliance", True),
    ("F3S:tool:speckit-exit-gate", "speckit-exit-gate", True),
    ("F3S:tasks:001-w0", "ava-speckit-tasks", True),
    ("F4", "ava-stack-orchestrator", False),
    ("F5", "ava-devops-orchestrator", False),
    ("F6", "ava-qa-orchestrator", False),
    ("F3", "ava-prototype", False),
    ("", "", False),
])
def test_predicado_cobre_so_a_camada_speckit(runner, phase, agent, esperado):
    assert runner._is_speckit_nonblocking(phase, agent) is esperado


def test_fase_speckit_degradada_nao_entra_em_val_failed(runner):
    executed, skipped, aborted, val_failed = [], [], [], []
    metrics: dict = {}
    passo = {"phase": "F3S:compliance", "agent": "ava-speckit-compliance"}

    runner._degrade_phase(passo, "outputs declarados não gravados", "regere",
                          executed, skipped, aborted, metrics,
                          val_failed=val_failed)

    assert val_failed == [], "fase SpecKit entrou na contabilidade de reprovação"
    assert "F3S:compliance" in executed
    assert metrics["F3S:compliance"]["non_blocking"] is True
    # E o veredito global não é falha.
    label = runner.execution_status_label(executed, skipped, aborted, val_failed,
                                          completed=True)
    assert label in ("completed", "completed_with_warnings")
    assert label != "aborted"


def test_fase_nao_speckit_continua_reprovando(runner):
    """Não-regressão: o abrandamento é restrito à F3S."""
    executed, skipped, aborted, val_failed = [], [], [], []
    metrics: dict = {}
    passo = {"phase": "F4", "agent": "ava-stack-orchestrator"}

    runner._degrade_phase(passo, "artefatos não gravados", "regere",
                          executed, skipped, aborted, metrics,
                          val_failed=val_failed)

    assert metrics["F4"]["non_blocking"] is False
    assert metrics["F4"]["val_ok"] is False
    assert metrics["F4"]["degraded"] is True


def test_degradacao_speckit_e_registrada_como_info(runner, monkeypatch):
    monkeypatch.setattr(runner, "_DEGRADATIONS", [])
    runner._degrade_phase({"phase": "F3S:tool:speckit-exit-gate",
                           "agent": "speckit-exit-gate"},
                          "gate reprovou", "revise", [], [], [], {},
                          val_failed=[])
    assert runner._DEGRADATIONS[0]["severity"] == "info"
    assert runner._DEGRADATIONS[0]["reason"] == "gate reprovou"


def test_expansao_invalida_da_f3s_nao_reprova_o_run(runner):
    executed, skipped, aborted, val_failed = [], [], [], []
    runner._degrade_unexpandable_f3s(
        {"phase": "F3S", "agent": "ava-speckit-orchestrator"},
        RuntimeError("wave model incoerente"),
        executed, skipped, aborted, {}, val_failed)
    assert val_failed == []
    assert "F3S" in executed


# ═══════════════════════════════════════════════════════════════════════════
#  5 · Dashboard
# ═══════════════════════════════════════════════════════════════════════════

def test_detalhe_de_aviso_nao_usa_icone_de_reprovacao(runner):
    """"aviso determinístico aceito (exit 1)" saía com ❌ vermelho."""
    aviso = runner._sub_row("P", {"phase": "F3S:tool:speckit-exit-gate",
                                  "agent": "speckit-exit-gate",
                                  "detail": "aviso determinístico aceito (exit 1)",
                                  "val_ok": True})
    assert "❌" not in aviso
    assert "ℹ️" in aviso or "⚠️" in aviso


def test_detalhe_de_falha_real_continua_com_x(runner):
    falha = runner._sub_row("P", {"phase": "F4", "agent": "ava-stack-orchestrator",
                                  "detail": "artefatos não gravados",
                                  "val_ok": False})
    assert "❌" in falha


# ═══════════════════════════════════════════════════════════════════════════
#  6 · Exit code
# ═══════════════════════════════════════════════════════════════════════════

def test_todos_os_nos_de_tool_da_f3s_sao_warn():
    import yaml
    dag = yaml.safe_load(
        (REPO_ROOT / "src/shared/data/pipeline-dag/F3S.yaml").read_text(
            encoding="utf-8"))
    bloqueantes = [t["id"] for w in dag["waves"] for t in (w.get("tools") or [])
                   if t.get("on_fail") != "warn"]
    assert bloqueantes == [], f"tools que ainda bloqueiam a F3S: {bloqueantes}"


def test_gates_da_f3s_passam_warn_na_linha_de_comando():
    import yaml
    dag = yaml.safe_load(
        (REPO_ROOT / "src/shared/data/pipeline-dag/F3S.yaml").read_text(
            encoding="utf-8"))
    gates = {t["id"]: t["command"] for w in dag["waves"]
             for t in (w.get("tools") or []) if t["id"].endswith("-gate")}
    for tool_id in ("speckit-entry-gate", "speckit-exit-gate"):
        assert "--warn" in gates[tool_id], f"{tool_id} pode sair != 0"


def test_suite_de_checks_da_f3s_passa_warn():
    import yaml
    dag = yaml.safe_load(
        (REPO_ROOT / "src/shared/data/pipeline-dag/F3S.yaml").read_text(
            encoding="utf-8"))
    checks = next(t for w in dag["waves"] for t in (w.get("tools") or [])
                  if t["id"] == "speckit-dependency-checks")
    assert "--warn" in checks["command"]
    assert "--json-out" in checks["command"], "o achado precisa ser persistido"
