"""Os cenários de aceite da correção da F4, ponta a ponta, sem SDK e sem rede.

Cada teste aqui corresponde a um cenário do pedido de correção, e cada um veio
de comportamento observado em `cadastro-funcionario-03`:

1/2 — scaffold existente é REUSADO, nunca recriado;
3   — task falha e passa após remediação: integra e fica `completed`;
4   — task falha depois do limite: branch preservado, `failed_after_remediation`,
      e o laço **continua**;
6   — validação de infraestrutura falha: artefatos preservados,
      `completed_with_warnings`, laço continua;
7   — três tasks consecutivas falhando não interrompem a fase;
9   — só a dependente explícita vira `blocked_by_dependency`;
10  — todas as tasks planejadas terminam em estado terminal (zero `pending`);
12  — scaffold que já não compilava: baseline diferencia erro preexistente de
      erro introduzido pela task.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import ava_pipeline
import f4_baseline
import f4_loop
import f4s_build_runner
import f4s_git_helper as git
import task_ledger
from pipeline_plan import Step


# ─── Projeto de teste ────────────────────────────────────────────────────────

def _entry(task_id: str, **campos) -> dict:
    base = {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "feature": "001-w0-foundation",
        "spec_id": "SPEC-W0-001",
        "group": "G-A",
        "task_type": "backend",
        "target_stack": "dotnet",
        "migration_wave_id": "W0",
        "migration_wave_order": 0,
        "priority": "P1",
        "depends_on": [],
        "backend_dependencies": [],
        "verify_command": "dotnet build",
        "acceptance": ["compila"],
        "target_files": [f"backend/{task_id}.cs"],
    }
    base.update(campos)
    return base


def _projeto(tmp_path: Path, entries: list[dict]) -> Path:
    task_ledger.REPO_ROOT = tmp_path
    tobe = tmp_path / "projects" / "P" / "outputs" / "tobe"
    (tobe / "speckit").mkdir(parents=True)
    (tobe / "speckit" / "traceability.json").write_text(json.dumps(
        {"schema_version": "4.0.0", "project": "P", "trace_id": "t",
         "entries": entries}), encoding="utf-8")
    task_ledger.init("P", repo_root=tmp_path)

    # Scaffold da F4S — arquivos reais, para que `scaffoldReused` signifique algo.
    for componente, arquivo in (("frontend", "package.json"),
                                ("backend", "App.csproj")):
        destino = tobe / "source-code" / componente
        destino.mkdir(parents=True)
        (destino / arquivo).write_text("{}", encoding="utf-8")

    repo = tobe / "source-code"
    git.git_init(repo)
    git.git_add_all(repo)
    base = git.git_commit(repo, "feat(scaffold): baseline compilavel")
    estado = {"status": "completed", "build_status": "succeeded",
              "verification_status": "succeeded", "commit_sha": base}
    (tobe / "tasks-progress.json").write_text(json.dumps(
        {"schema_version": "1.0.0", "project": "P",
         "tasks": {"T-SCAFFOLD-FRONTEND-001": dict(estado),
                   "T-SCAFFOLD-BACKEND-001": dict(estado)},
         "approval": {"status": "approved"}, "artifacts": {}}), encoding="utf-8")
    return tmp_path


def _repo(tmp_path: Path) -> Path:
    return tmp_path / "projects" / "P" / "outputs" / "tobe" / "source-code"


def _runner(tmp_path: Path, *, builds: dict[str, list[int]] | None = None,
            escreve: dict[str, list[str]] | None = None):
    """`dispatch`/`verify` reais (harness + git), com o build mockado."""
    builds = builds or {}
    escreve = escreve or {}
    chamadas: list[str] = []
    contador: dict[str, int] = {}

    def fake_build(repo_root, stack, **kwargs):
        atual = kwargs.get("_task") or _runner.task_corrente
        sequencia = builds.get(atual, [0])
        indice = min(contador.get(atual, 0), len(sequencia) - 1)
        contador[atual] = contador.get(atual, 0) + 1
        codigo = sequencia[indice]
        return {"command": "dotnet build", "exit_code": codigo,
                "stdout": "", "stderr": ("error CS0246: nao encontrado"
                                         if codigo else ""),
                "timed_out": False}

    f4s_build_runner.run_build = fake_build

    def dispatch(ctx):
        task_id = ctx["task_id"]
        _runner.task_corrente = task_id
        chamadas.append(task_id)
        destino = ctx["route"].canonical_source_dir
        destino.mkdir(parents=True, exist_ok=True)
        for rel in escreve.get(task_id, [f"{task_id}.cs"]):
            alvo = ctx["route"].repo_dir / rel if "/" in rel else destino / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(f"// {task_id} v{ctx['attempt']}", encoding="utf-8")
        return {"artifacts": [], "agent_result": {}}

    def verify(ctx):
        task = ctx["task"]
        _runner.task_corrente = ctx["task_id"]
        step = Step(phase=f"F4:{ctx['task_id']}", group="F4",
                    agent=ctx["route"].agent, trigger="SG", label="F4",
                    task_id=ctx["task_id"], target_stack=ctx["route"].target_stack,
                    feature=task.get("feature", ""), inputs={})
        return ava_pipeline.verify_task_step(
            step, ctx["project"], {"artifacts": []}, ctx["repo_root"] / "logs",
            timeout_s=60, route=ctx["route"],
            branch_context=ctx.get("branch_context"), repo_root=ctx["repo_root"])

    return dispatch, verify, chamadas


_runner.task_corrente = ""


@pytest.fixture(autouse=True)
def _restaura_build():
    original = f4s_build_runner.run_build
    yield
    f4s_build_runner.run_build = original


# ─── Cenários 1 e 2 — scaffold reutilizado, nunca recriado ───────────────────

def test_cenario_1_2_scaffold_existente_e_reutilizado(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    antes = (_repo(tmp_path) / "backend" / "App.csproj").read_text(encoding="utf-8")
    dispatch, verify, _ = _runner(tmp_path)

    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                repo_root=tmp_path)

    task = task_ledger.get("P", "T-001", tmp_path)
    assert task["scaffoldReused"] is True
    assert task["scaffoldRecreated"] is False
    assert task["scaffoldPath"].endswith("source-code/backend")
    assert (_repo(tmp_path) / "backend" / "App.csproj").read_text(
        encoding="utf-8") == antes, "o scaffold não pode ser reescrito"
    baseline = f4_baseline.load(_repo(tmp_path), "backend")
    assert baseline["scaffoldPresent"] is True
    assert baseline["status"] == "green"


def test_scaffold_ausente_vira_review_e_nao_recria(tmp_path: Path) -> None:
    """Scaffold sumiu depois do gate: erro estrutural por task, sem recriar.

    O gate de fase (`f4_gate`) já reprova um projeto que chega sem scaffold —
    por isso aqui ele é dispensado: o cenário é o scaffold desaparecer *entre* a
    aprovação e a execução, e o que se testa é a política da task, não a do gate.
    """
    _projeto(tmp_path, [_entry("T-FE", task_type="frontend",
                               target_stack="angular", verify_command="",
                               target_files=["frontend/app.ts"])])
    for item in (_repo(tmp_path) / "frontend").iterdir():
        item.unlink()
    dispatch, verify, chamadas = _runner(tmp_path)

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path, check_gate=False)

    task = task_ledger.get("P", "T-FE", tmp_path)
    assert task["executionStatus"] == task_ledger.EXEC_REVIEW
    assert "scaffold" in task["reviewReason"]
    assert task["scaffoldRecreated"] is False
    assert chamadas == [], "nenhum agente é despachado para recriar scaffold"
    assert resultado.execution_complete is True


# ─── Cenário 3 — falha, remedia, integra ─────────────────────────────────────

def test_cenario_3_task_falha_e_passa_apos_remediacao(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    # 1ª tentativa do build falha; a remediação do harness roda e a 2ª passa.
    dispatch, verify, _ = _runner(tmp_path, builds={"T-001": [1, 0]})

    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                repo_root=tmp_path)

    task = task_ledger.get("P", "T-001", tmp_path)
    assert task["executionStatus"] == task_ledger.EXEC_COMPLETED
    assert task["status"] == "verified"
    assert task["branchName"].startswith("task/t-001")
    assert task["mergedToMain"] is True
    log = subprocess.run(["git", "log", "--oneline"], cwd=str(_repo(tmp_path)),
                         capture_output=True, text=True).stdout
    assert "implement T-001" in log


# ─── Cenário 4 — falha após o limite, branch preservado, laço continua ───────

def test_cenario_4_falha_apos_limite_preserva_branch_e_continua(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-RUIM"), _entry("T-BOA")])
    dispatch, verify, chamadas = _runner(tmp_path, builds={"T-RUIM": [1]})

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    ruim = task_ledger.get("P", "T-RUIM", tmp_path)
    boa = task_ledger.get("P", "T-BOA", tmp_path)
    assert ruim["executionStatus"] == task_ledger.EXEC_FAILED_AFTER_REMEDIATION
    assert ruim["reviewRequired"] is True
    assert ruim["mergedToMain"] is False
    assert git.branch_exists(_repo(tmp_path), ruim["branchName"]), (
        "o branch da task falhada é preservado como evidência")
    assert boa["executionStatus"] == task_ledger.EXEC_COMPLETED, (
        "a falha de uma task não impede a seguinte")
    assert "T-BOA" in chamadas
    assert resultado.execution_complete is True
    assert resultado.functional_success is False


# ─── Cenário 6 — infraestrutura com validação reprovada ──────────────────────

def test_cenario_6_infra_com_validacao_falha_preserva_artefatos(tmp_path: Path) -> None:
    _projeto(tmp_path, [
        _entry("T-TF-001", title="Criar infra/terraform/main.tf",
               verify_command="terraform validate infra/terraform",
               target_files=["infra/terraform/main.tf"]),
        _entry("T-BE-001"),
    ])
    dispatch, verify, chamadas = _runner(
        tmp_path,
        escreve={"T-TF-001": ["infra/terraform/main.tf",
                              "infra/terraform/variables.tf",
                              "infra/terraform/modules/app-service/main.tf"]})

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    task = task_ledger.get("P", "T-TF-001", tmp_path)
    # `terraform` não existe no ambiente de teste: validação reprova, artefatos
    # continuam de pé e a task NÃO bloqueia a esteira.
    assert task["executionStatus"] == task_ledger.EXEC_COMPLETED_WARN
    assert task["taskType"] == "infra"
    assert (_repo(tmp_path) / "infra" / "terraform" / "main.tf").is_file()
    assert any("infra/terraform/main.tf" in item
               for item in task["generatedArtifacts"])
    assert task["excludedFromCommit"] == [], (
        "arquivo de infraestrutura não pode ser excluído do commit")
    assert task["validationResults"]["exit_code"] != 0
    assert "T-BE-001" in chamadas, "a esteira continua depois da infra"
    assert resultado.execution_complete is True


def test_infra_e_roteada_para_o_agente_de_iac(tmp_path: Path) -> None:
    import f4_routing
    rota = f4_routing.resolve_route(
        _entry("T-TF", verify_command="terraform validate",
               target_files=["infra/terraform/main.tf"]), "P", tmp_path)
    assert rota.agent == "ava-devops-iac"
    assert rota.canonical_source_rel == "source-code/infra"


# ─── Cenário 7 — três falhas consecutivas não param a fase ───────────────────

def test_cenario_7_tres_falhas_consecutivas_nao_interrompem(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-A"), _entry("T-B"), _entry("T-C"),
                        _entry("T-D"), _entry("T-E")])
    dispatch, verify, chamadas = _runner(
        tmp_path, builds={"T-A": [1], "T-B": [1], "T-C": [1]})

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    assert {"T-D", "T-E"} <= set(chamadas), (
        "o circuit breaker de 3 specs consecutivas não pode existir")
    assert task_ledger.get("P", "T-D", tmp_path)["executionStatus"] == \
        task_ledger.EXEC_COMPLETED
    assert task_ledger.get("P", "T-E", tmp_path)["executionStatus"] == \
        task_ledger.EXEC_COMPLETED
    assert resultado.execution_complete is True
    assert resultado.summary["still_pending"] == 0


# ─── Cenário 9 — só a dependente explícita é bloqueada ───────────────────────

def test_cenario_9_apenas_a_dependente_explicita_e_bloqueada(tmp_path: Path) -> None:
    _projeto(tmp_path, [
        _entry("T-BASE"),
        _entry("T-DEP", depends_on=["T-BASE"]),
        _entry("T-LIVRE"),
    ])
    dispatch, verify, chamadas = _runner(tmp_path, builds={"T-BASE": [1]})

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    dep = task_ledger.get("P", "T-DEP", tmp_path)
    livre = task_ledger.get("P", "T-LIVRE", tmp_path)
    assert dep["executionStatus"] == task_ledger.EXEC_BLOCKED_BY_DEPENDENCY
    assert dep["blockedByTaskIds"] == ["T-BASE"]
    assert dep["dependencyType"] == "explicit"
    assert dep["evaluatedAt"]
    assert livre["executionStatus"] == task_ledger.EXEC_COMPLETED, (
        "falha de uma task não é bloqueio implícito das independentes")
    assert "T-LIVRE" in chamadas
    assert resultado.execution_complete is True


# ─── Cenário 10 — nenhuma task fica pendente ─────────────────────────────────

def test_cenario_10_todas_as_tasks_terminam_em_estado_terminal(tmp_path: Path) -> None:
    entradas = [_entry(f"T-{i:03d}") for i in range(1, 31)]
    entradas.append(_entry("T-DEP", depends_on=["T-005"]))
    entradas.append(_entry("T-TF", verify_command="terraform validate",
                           target_files=["infra/terraform/main.tf"]))
    _projeto(tmp_path, entradas)
    dispatch, verify, _ = _runner(
        tmp_path, builds={"T-005": [1], "T-010": [1]},
        escreve={"T-TF": ["infra/terraform/main.tf"]})

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    tasks = task_ledger.load("P", tmp_path)["tasks"]
    assert len(tasks) == 32
    nao_terminais = [t["task_id"] for t in tasks
                     if task_ledger.execution_status_of(t)
                     not in task_ledger.EXECUTION_TERMINAL]
    assert nao_terminais == [], f"tasks sem estado terminal: {nao_terminais}"
    assert resultado.summary["still_pending"] == 0
    assert resultado.summary["planned"] == 32
    assert resultado.status == task_ledger.COMPLETION_WITH_REVIEW
    assert resultado.ok is True, "encerramento controlado não é falha da fase"


# ─── Cenário 12 — baseline diferencia erro preexistente ──────────────────────

def test_cenario_12_erro_preexistente_nao_e_culpa_da_task(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    # O scaffold já não compila ANTES da task: o baseline registra isso, e a
    # task que não piorou o quadro é integrada com aviso.
    dispatch, verify, _ = _runner(tmp_path, builds={"T-001": [1]})
    f4s_build_runner.run_build = lambda repo_root, stack, **kw: {
        "command": "dotnet build", "exit_code": 1, "stdout": "",
        "stderr": "error CS0246: preexistente", "timed_out": False}

    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                repo_root=tmp_path)

    task = task_ledger.get("P", "T-001", tmp_path)
    baseline = task["baselineBuild"]
    assert baseline["status"] == "red"
    assert baseline["baselineErrors"] >= 1
    comparacao = task["buildComparison"]
    assert comparacao["errorsBefore"] >= 1
    # A task NÃO é culpada pelo erro preexistente, e o trabalho é integrado…
    assert comparacao["introducedNewErrors"] is False
    assert comparacao["samePreexistingFailure"] is True
    assert comparacao["integrable"] is True
    assert task["mergedToMain"] is True
    # …mas o componente não compila, e isso não pode virar conclusão: sem exit 0
    # não existe `completed`. Era este atalho que integrava task após task como
    # sucesso sobre um backend que nunca compilou.
    assert task["executionStatus"] == task_ledger.EXEC_REVIEW
    assert task["status"] != "verified"
    assert task["evidence"]["exit_code"] == 1, "o exit code registrado é o real"
    assert "NAO compila" in task["reviewReason"]


def test_baseline_detecta_erro_introduzido_pela_task(tmp_path: Path) -> None:
    baseline = {"status": "green", "baselineErrors": 0}
    resultado = f4_baseline.compare(
        baseline, {"exit_code": 1, "stdout": "", "stderr": "error CS1002: ;"})
    assert resultado["introducedNewErrors"] is True
    assert resultado["integrable"] is False


# ─── Regressões de `cadastro-funcionario-03` (2ª rodada) ─────────────────────
#
# O log real mostrou 18 tasks integradas como `completed_with_warnings` sem um
# único build verde, um aviso falso de "arquivo fora do canônico" em toda task,
# e um merge em conflito por branch reaproveitado entre execuções.

def test_falha_estrutural_nao_passa_por_erro_preexistente(tmp_path: Path) -> None:
    """Exit != 0 com ZERO linhas de erro não é 'não introduziu erro novo'.

    `verify_dotnet_solution.py` reprova por prerequisito/estrutura com exit
    10/20 e nenhuma linha `error CSxxxx`. A comparação por CONTAGEM via 0 antes
    e 0 depois e concluía 'igual ao baseline' — 18 tasks foram integradas como
    sucesso sem build verde. Agora a comparação é por ASSINATURA.
    """
    baseline_vermelho = {"status": "red", "baselineErrors": 0,
                         "baselineFailureSignature": "20:aaaaaaaaaaaa"}
    outra_falha = {"exit_code": 10, "stdout": "", "stderr": "prereq: dotnet ausente"}
    resultado = f4_baseline.compare(baseline_vermelho, outra_falha)
    assert resultado["samePreexistingFailure"] is False
    assert resultado["introducedNewErrors"] is True
    assert resultado["integrable"] is False


def test_mesma_falha_do_baseline_integra_mas_nao_verifica(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    falha = {"command": "verify", "exit_code": 20, "stdout": '{"phase":"structure"}',
             "stderr": "", "timed_out": False}
    f4s_build_runner.run_build = lambda repo_root, stack, **kw: dict(falha)
    dispatch, verify, _ = _runner(tmp_path)
    f4s_build_runner.run_build = lambda repo_root, stack, **kw: dict(falha)

    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1", repo_root=tmp_path)

    task = task_ledger.get("P", "T-001", tmp_path)
    assert task["executionStatus"] == task_ledger.EXEC_REVIEW
    assert task["status"] != "verified", "sem build verde nao existe `verified`"
    assert task["evidence"]["exit_code"] == 20, "o exit code registrado e o real"
    assert "NAO compila" in task["reviewReason"]
    assert task["buildComparison"]["samePreexistingFailure"] is True
    assert task["mergedToMain"] is True, "o trabalho e integrado, nao descartado"


def test_caminho_repo_relativo_nao_e_falso_positivo(tmp_path: Path) -> None:
    """`backend/Directory.Packages.props` É canônico — o aviso era falso."""
    import f4_agent_result
    import f4_routing
    tarefa = _entry("T-001", target_files=["backend/Directory.Packages.props"])
    rota = f4_routing.resolve_route(tarefa, "P", tmp_path)
    payload = {
        "schema_version": "1.0.0", "task_id": "T-001",
        "implementation_status": "completed",
        "files_created": ["backend/Directory.Packages.props",
                          "backend/src/App/App.csproj"],
        "files_modified": [],
    }
    resultado = f4_agent_result.validate(payload, task=tarefa, route=rota,
                                         project="P")
    assert resultado.files_outside_canonical == []


def test_arquivo_realmente_fora_do_escopo_ainda_e_sinalizado(tmp_path: Path) -> None:
    import f4_agent_result
    import f4_routing
    tarefa = _entry("T-001")
    rota = f4_routing.resolve_route(tarefa, "P", tmp_path)
    payload = {"schema_version": "1.0.0", "task_id": "T-001",
               "implementation_status": "completed",
               "files_created": ["frontend/src/app.ts"], "files_modified": []}
    resultado = f4_agent_result.validate(payload, task=tarefa, route=rota,
                                         project="P")
    assert resultado.files_outside_canonical == ["frontend/src/app.ts"]


def test_branch_obsoleto_de_run_anterior_nao_e_reaproveitado(tmp_path: Path) -> None:
    """Reusar o branch antigo colocava o trabalho sobre um `main` velho."""
    _projeto(tmp_path, [_entry("T-A"), _entry("T-B")])
    repo = _repo(tmp_path)
    # Simula um run anterior: branch da T-B criado ANTES de a T-A entrar no main.
    branch_antigo = git.task_branch_name("T-B", "Task T-B")
    git.checkout_branch(repo, branch_antigo, create=True, base="main")
    (repo / "backend" / "antigo.cs").write_text("// run anterior", encoding="utf-8")
    git.git_add_paths(repo, ["backend/antigo.cs"])
    git.git_commit(repo, "work de run anterior", stage_all=False)
    git.checkout_branch(repo, "main")

    dispatch, verify, _ = _runner(tmp_path)
    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r2", repo_root=tmp_path)

    task_b = task_ledger.get("P", "T-B", tmp_path)
    assert task_b["branchName"] != branch_antigo, (
        "branch obsoleto precisa ser preservado, não reaproveitado")
    assert task_b["branchName"].endswith("--r2")
    assert git.branch_exists(repo, branch_antigo), "o branch antigo é evidência"
    assert task_b["mergeStatus"] == "merged", "sem conflito de merge"
    assert task_b["executionStatus"] == task_ledger.EXEC_COMPLETED
