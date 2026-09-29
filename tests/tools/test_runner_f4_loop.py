"""Integração da F4 no runner de produção — `ava-pipeline-runner-cli.py`.

Três coisas precisam ser verdade no runner, e as três eram falsas:

1. a F4 é **um** passo, não N passos estáticos expandidos no início da fase;
2. o manifesto de contexto dela é fechado e vazio (contexto é por task);
3. o despacho vai para `_run_f4_codegen_step`, que roda o laço — e o laço não
   pode ser importado "com degradação": se `f4_loop` não importa, a fase falha
   em vez de virar despacho único.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

RUNNER_19 = REPO_ROOT / "ava-pipeline-runner-cli.py"


def _load_module(path: Path, name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner19():
    if not RUNNER_19.is_file():
        pytest.skip("ava-pipeline-runner-cli.py ausente neste checkout")
    pytest.importorskip("anthropic", reason="motor SDK do runner de produção")
    return _load_module(RUNNER_19, "runner19_f4_sob_teste")


def test_f4_e_um_unico_passo_no_pipeline(runner19) -> None:
    passos = [s for s in runner19.PIPELINE if s["phase"].split(":")[0] == "F4"]
    assert len(passos) == 1
    assert passos[0]["agent"] == runner19.F4_ORCHESTRATOR
    assert passos[0]["trigger"] == runner19.F4_TRIGGER


def test_expansao_estatica_da_f4_foi_removida(runner19) -> None:
    """`_expand_ledger_phase` virou identidade — a fila é recalculada no laço."""
    pipeline = [{"phase": "F4", "agent": "ava-stack-orchestrator", "trigger": "SG"}]
    assert runner19._expand_ledger_phase(pipeline, "qualquer-projeto") == pipeline


def test_manifesto_da_f4_e_fechado_e_vazio(runner19) -> None:
    f4 = next(s for s in runner19.PIPELINE if s["phase"] == "F4")
    assert f4["inputs"]["mandatory"] == []
    assert f4["inputs"]["advisory"] == []
    assert f4["inputs"]["floor"] == []


def test_identidade_da_fase_reconhece_so_o_passo_certo(runner19) -> None:
    assert runner19._is_f4_codegen_step(
        {"phase": "F4", "agent": "ava-stack-orchestrator", "trigger": "SG"})
    assert not runner19._is_f4_codegen_step(
        {"phase": "F4S", "agent": "scaffold-runner", "trigger": None})
    assert not runner19._is_f4_codegen_step(
        {"phase": "F4", "agent": "outro-agente", "trigger": "SG"})
    assert not runner19._is_f4_codegen_step(None)


def test_teto_de_saida_por_task_e_menor_que_o_da_fase(runner19) -> None:
    """128k de saída era o orçamento de 140 arquivos numa resposta só."""
    assert runner19.F4_TASK_MAX_TOKENS < runner19.PHASE_MAX_TOKENS["F4"]


def test_f4_falha_fechado_sem_os_modulos_do_laco(runner19, tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner19, "_f4_loop", None)
    monkeypatch.setattr(runner19, "_F4_IMPORT_ERROR", "simulado", raising=False)
    resultado = runner19._run_f4_codegen_step(
        None, {"phase": "F4", "agent": "ava-stack-orchestrator", "trigger": "SG"},
        "P", tmp_path, skill_content="", out_tokens=1000, esperados=[],
        headroom_active=False)
    assert resultado["val_ok"] is False
    assert "despacho unico" in resultado["detail"]


def _projeto_pronto(tmp_path: Path) -> None:
    """Projeto com F4S aprovada, baseline git real e razão de duas tasks."""
    import json
    import f4s_git_helper
    import task_ledger

    task_ledger.REPO_ROOT = tmp_path
    tobe = tmp_path / "projects" / "P" / "outputs" / "tobe"
    (tobe / "speckit").mkdir(parents=True)

    def entry(task_id: str, depends_on=None) -> dict:
        return {"task_id": task_id, "title": f"Task {task_id}",
                "feature": "001-domain", "spec_id": "S1", "group": "G-A",
                "task_type": "backend", "target_stack": "dotnet", "priority": "P1",
                "migration_wave_id": "W0", "migration_wave_order": 0,
                "depends_on": depends_on or [], "backend_dependencies": [],
                "verify_command": "dotnet build", "acceptance": ["compila"],
                "target_files": [f"backend/{task_id}.cs"]}

    (tobe / "speckit" / "traceability.json").write_text(json.dumps(
        {"schema_version": "4.0.0", "project": "P", "trace_id": "t",
         "entries": [entry("T-001"), entry("T-002", ["T-001"])]}), encoding="utf-8")
    task_ledger.init("P", repo_root=tmp_path)

    for componente, arquivo in (("frontend", "package.json"),
                                ("backend", "App.csproj")):
        destino = tobe / "source-code" / componente
        destino.mkdir(parents=True)
        (destino / arquivo).write_text("{}", encoding="utf-8")
    f4s_git_helper.git_init(tobe / "source-code")
    f4s_git_helper.git_add_all(tobe / "source-code")
    base = f4s_git_helper.git_commit(tobe / "source-code", "feat(scaffold): baseline")
    task = {"status": "completed", "build_status": "succeeded",
            "verification_status": "succeeded", "commit_sha": base}
    (tobe / "tasks-progress.json").write_text(json.dumps(
        {"schema_version": "1.0.0", "project": "P",
         "tasks": {"T-SCAFFOLD-FRONTEND-001": dict(task),
                   "T-SCAFFOLD-BACKEND-001": dict(task)},
         "approval": {"status": "approved"}, "artifacts": {}}), encoding="utf-8")


def test_runner_executa_o_laco_ponta_a_ponta(runner19, tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """Caminho feliz completo, sem rede: prompt por task, build real mockado, commit."""
    import f4s_build_runner
    import task_ledger

    _projeto_pronto(tmp_path)
    monkeypatch.setattr(runner19, "WORKSPACE", tmp_path)
    monkeypatch.setattr(f4s_build_runner, "run_build",
                        lambda repo, stack, **kwargs: {
                            "command": "dotnet build", "exit_code": 0,
                            "stdout": "ok", "stderr": "", "timed_out": False})

    prompts: list[str] = []

    def fake_dispatch_model(client, *, system_prompt, user_prompt, out_tokens,
                            phase, ts_start, stream_guard, **kwargs):
        prompts.append(user_prompt)
        task_id = user_prompt.split("| task: ")[1].split(" |")[0].strip()
        destino = (tmp_path / "projects" / "P" / "outputs" / "tobe"
                   / "source-code" / "backend" / f"{task_id}.cs")
        resposta = (
            f"<!-- FILE: projects/P/outputs/tobe/source-code/backend/{task_id}.cs -->\n"
            f"// {task_id}\n<!-- /FILE -->\n"
            '<!-- F4_RESULT -->\n```json\n'
            + __import__("json").dumps({
                "schema_version": "1.0.0", "task_id": task_id,
                "task_type": "backend", "target_stack": "dotnet",
                "agent": "ava-stack-dotnet-backend",
                "canonical_source_dir": "source-code/backend",
                "implementation_status": "completed",
                "files_created": [str(destino)], "files_modified": [],
                "local_checks": [], "acceptance_results": []})
            + "\n```\n<!-- /F4_RESULT -->\n")
        return resposta, "end_turn", 1000, 200

    monkeypatch.setattr(runner19, "_dispatch_model", fake_dispatch_model)

    resultado = runner19._run_f4_codegen_step(
        object(), {"phase": "F4", "agent": "ava-stack-orchestrator", "trigger": "SG"},
        "P", tmp_path / "logs", skill_content="", out_tokens=128_000,
        esperados=[], headroom_active=False)

    assert resultado["val_ok"] is True
    assert resultado["f4_status"] == task_ledger.COMPLETION_SUCCESS
    assert resultado["f4_execution_complete"] is True
    assert resultado["f4_functional_success"] is True
    assert resultado["f4_counts"]["verified"] == 2

    # Um prompt por task, e cada um nomeia a SUA task — o defeito original era
    # N despachos com o mesmo texto.
    assert len(prompts) == 2
    assert "task: T-001" in prompts[0] and "task: T-002" in prompts[1]
    assert prompts[0] != prompts[1]
    assert all("ava-stack-dotnet-backend" in p for p in prompts)

    # Observabilidade e commits reais.
    linhas = resultado["f4_tasks"]
    assert [item["agent"] for item in linhas] == ["ava-stack-dotnet-backend"] * 2
    assert all(item["canonical_source_dir"] == "source-code/backend" for item in linhas)
    assert all(item["commit_hash"] for item in linhas)

    import subprocess
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(tmp_path / "projects" / "P" / "outputs" / "tobe" / "source-code"),
        capture_output=True, text=True).stdout
    assert "feat(backend/dotnet): implement T-001 001-domain" in log
    assert "feat(backend/dotnet): implement T-002 001-domain" in log


def test_gate_reprovado_impede_o_despacho_no_runner(runner19, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem F4S aprovada, a fase termina sem chamar o modelo."""
    monkeypatch.setattr(runner19, "WORKSPACE", tmp_path)
    (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit").mkdir(parents=True)
    chamadas: list[str] = []
    monkeypatch.setattr(runner19, "_dispatch_model",
                        lambda *a, **k: chamadas.append("despachou"))

    resultado = runner19._run_f4_codegen_step(
        None, {"phase": "F4", "agent": "ava-stack-orchestrator", "trigger": "SG"},
        "P", tmp_path / "logs", skill_content="", out_tokens=1000, esperados=[],
        headroom_active=False)

    assert resultado["val_ok"] is False
    assert chamadas == []
