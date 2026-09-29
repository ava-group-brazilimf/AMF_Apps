"""
Testes da fase F4S — helpers determinísticos e runner.

Roda com:
    python -m pytest tests/tools/test_f4s_phase.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
SCAFFOLDS_DIR = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "tech-stack" / "scaffolds"
)
sys.path.insert(0, str(TOOLS_DIR))

import f4s_build_runner as build  # noqa: E402
import f4s_feature_discovery as discovery  # noqa: E402
import f4s_generation_log as log  # noqa: E402
import f4s_git_helper as git  # noqa: E402
import f4s_phase_runner as runner  # noqa: E402
import f4s_tree_snapshot as tree  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ─── Git helper ──────────────────────────────────────────────────────────────

def test_git_init_e_commit(tmp_path: Path):
    repo = tmp_path / "repo"
    git.git_init(repo)
    assert (repo / ".git").is_dir()

    _write(repo / "a.txt", "hello")
    h = git.git_commit(repo, "feat: add a")
    assert len(h) >= 7
    assert git.git_status_is_clean(repo)


def test_git_commit_vazio_retorna_string_vazia(tmp_path: Path):
    repo = tmp_path / "repo"
    git.git_init(repo)
    assert git.git_commit(repo, "empty") == ""


# ─── Tree snapshot ───────────────────────────────────────────────────────────

def test_snapshot_ignora_artifact_dirs(tmp_path: Path):
    repo = tmp_path / "repo"
    _write(repo / "src" / "Program.cs", "x")
    _write(repo / "node_modules" / "x" / "package.json", "{}")
    _write(repo / "bin" / "Debug" / "app.dll", "bytes")

    result = tree.snapshot(repo)
    paths = {f["path"] for f in result["files"]}
    assert "src/Program.cs" in paths
    assert not any("node_modules" in p for p in paths)
    assert not any(p.startswith("bin") for p in paths)


def test_snapshot_grava_arquivos(tmp_path: Path):
    repo = tmp_path / "repo"
    _write(repo / "file.txt", "x")
    md = tmp_path / "TREE.md"
    js = tmp_path / "TREE.json"
    tree.snapshot(repo, output_md=md, output_json=js)
    assert md.exists()
    assert js.exists()
    assert "file.txt" in md.read_text(encoding="utf-8")


# ─── Build runner ────────────────────────────────────────────────────────────

def test_resolve_command_default_por_stack():
    dotnet = build.resolve_command("dotnet")
    assert dotnet[0] == sys.executable
    assert dotnet[1].endswith("verify_dotnet_solution.py")
    assert dotnet[2:] == ["--root", ".", "--json"]
    # Stacks node sem verificador dedicado usam `npm install`, não `npm ci`:
    # `npm ci` exige lockfile e falha num scaffold recém-gerado (spec 042).
    assert build.resolve_command("react") == ["npm", "install", "&&", "npm", "run", "build"]


def test_resolve_command_angular_delega_ao_verificador():
    """Spec 042: para Angular, "build" é o harness completo, não `npm run build`.

    O verificador cobre install -> build -> boot -> health e é a autoridade sobre
    "compila e roda" — a fase health captura defeitos que passam no `ng build` e só
    quebram no browser.
    """
    cmd = build.resolve_command("angular")
    assert cmd[0] == sys.executable
    assert cmd[1].endswith("verify_angular_app.py")
    assert cmd[2:] == ["--root", ".", "--json"]


def test_dotnet_stack_checks_incluem_manifest():
    names = [item[0] for item in runner._stack_check_scripts(Path("."), "dotnet")]
    assert names == ["scaffold-manifest-dotnet", "nuget-duplicate", "cpm-consistency"]


def test_resolve_command_override_string():
    """Override vale para stack SEM verificador determinístico próprio."""
    assert build.resolve_command("fastapi", "echo ok") == ["echo", "ok"]


def test_verificador_da_stack_vence_o_override():
    """Precedência invertida: o harness da stack é a autoridade de build.

    Antes, `override` era testado primeiro e desligava o verificador. Em
    `cadastro-funcionario-03` isso fez o `verify_command` da task
    (`ng build ...`, escrito em prosa pelo SpecKit) substituir o
    `verify_angular_app.py` — e `ng` não existe no PATH: exit 127, três
    tentativas, seis remediações de LLM, 251s e a fase derrubada.
    """
    for stack, verificador in (("dotnet", "verify_dotnet_solution.py"),
                               ("angular", "verify_angular_app.py")):
        comando = build.resolve_command(stack, "echo ok")
        assert verificador in " ".join(comando)
        assert comando[:2] != ["echo", "ok"]


def test_resolve_command_unknown_stack_reprova():
    with pytest.raises(build.BuildRunnerError, match="stack 'foo' sem comando"):
        build.resolve_command("foo")


def test_run_build_executa_override_e_captura_saida(tmp_path: Path):
    result = build.run_build(tmp_path, "any", command_override=[sys.executable, "-c", "print('ok')"])
    assert result["exit_code"] == 0
    assert "ok" in result["stdout"]


def test_run_build_falha_comando_inexistente(tmp_path: Path):
    """Exit 127 continua, agora classificado como falha de AMBIENTE."""
    result = build.run_build(tmp_path, "fastapi", command_override=["nao_existe_42"])
    assert result["exit_code"] == 127
    assert result["toolchain_missing"] == "nao_existe_42"


# ─── Generation log ──────────────────────────────────────────────────────────

def test_init_log_cria_cabecalho(tmp_path: Path):
    log.init_log(tmp_path)
    text = (tmp_path / "GENERATION_LOG.md").read_text(encoding="utf-8")
    assert "F4S Generation Log" in text
    assert "Spec" in text


def test_append_log_adiciona_linha(tmp_path: Path):
    log.append_log(tmp_path, "spec-1", 1, "cmd", 0, notes="ok")
    text = (tmp_path / "GENERATION_LOG.md").read_text(encoding="utf-8")
    assert "spec-1" in text
    assert "ok" in text


def test_state_redondo(tmp_path: Path):
    state = log.load_state(tmp_path)
    assert state["initialized"] is False
    state["initialized"] = True
    log.save_state(tmp_path, state)
    assert log.load_state(tmp_path)["initialized"] is True


# ─── Feature discovery ───────────────────────────────────────────────────────

def test_discover_features_scaffold_first(tmp_path: Path):
    tobe = tmp_path / "tobe"
    _write(tobe / "speckit" / "specs" / "clientes" / "spec.md", "x")

    feats = discovery.discover_features("dotnet", tobe)
    assert feats[0]["id"] == "000-scaffold"
    ids = [f["id"] for f in feats]
    assert "clientes" in ids


def test_discover_features_via_traceability(tmp_path: Path):
    tobe = tmp_path / "tobe"
    _write(
        tobe / "speckit" / "traceability.json",
        json.dumps([
            {"group": "Pedidos", "target_stack": "dotnet"},
            {"group": "Clientes", "target_stack": "angular"},
        ]),
    )
    _write(tobe / "speckit" / "specs" / "pedidos" / "spec.md", "x")

    feats = discovery.discover_features("dotnet", tobe)
    ids = [f["id"] for f in feats]
    assert ids[0] == "000-scaffold"
    assert "pedidos" in ids
    assert "clientes" not in ids


# ─── Phase runner utilities ──────────────────────────────────────────────────

def test_discover_features_respects_v2_execution_order(tmp_path: Path):
    tobe = tmp_path / "tobe"
    v2 = {
        "schema_version": "2.0.0",
        "project": "p",
        "trace_id": "t",
        "generated_at": "2026-08-14T00:00:00Z",
        "constitution": "c.md",
        "total_tasks": 3,
        "graph_checksum": "a" * 64,
        "dependency_edges": [],
        "execution_order": ["T-PAG-002", "T-CLI-001", "T-REL-003"],
        "execution_waves": [["T-PAG-002"], ["T-CLI-001"], ["T-REL-003"]],
        "entries": [
            {"task_id": "T-CLI-001", "feature": "clientes", "target_stack": "dotnet"},
            {"task_id": "T-PAG-002", "feature": "pagamentos", "target_stack": "dotnet"},
            {"task_id": "T-REL-003", "feature": "relatorios", "target_stack": "dotnet"},
        ],
    }
    _write(tobe / "speckit" / "traceability.json", json.dumps(v2))
    _write(tobe / "speckit" / "specs" / "clientes" / "spec.md", "x")
    _write(tobe / "speckit" / "specs" / "pagamentos" / "spec.md", "x")
    _write(tobe / "speckit" / "specs" / "relatorios" / "spec.md", "x")

    feats = discovery.discover_features("dotnet", tobe)
    ids = [f["id"] for f in feats]
    assert ids[0] == "000-scaffold"
    assert ids[1:] == ["pagamentos", "clientes", "relatorios"]


def test_resolve_scaffold_stack_specific():
    assert runner._resolve_scaffold_spec("dotnet").name == "dotnet-scaffold.md"
    assert runner._resolve_scaffold_spec("spring-boot").name == "spring-boot-scaffold.md"
    assert runner._resolve_scaffold_spec("nuxt").name == "default-scaffold.md"


def test_scaffold_files_exist_for_supported_stacks():
    for stack in ["dotnet", "spring-boot", "fastapi", "angular", "react", "vue"]:
        spec = runner._resolve_scaffold_spec(stack)
        assert spec.exists(), f"scaffold ausente para {stack}: {spec}"


def test_phase_runner_dry_run(tmp_path: Path, monkeypatch, capsys):
    project = "testproj"
    outputs = tmp_path / "projects" / project / "outputs"
    tobe = outputs / "tobe"
    _write(tobe / "speckit" / "specs" / "clientes" / "spec.md", "x")
    _write(
        tobe / "speckit" / "traceability.json",
        json.dumps([{"group": "Clientes", "target_stack": "dotnet"}]),
    )

    monkeypatch.setattr(runner, "OUTPUTS_ROOT", tmp_path / "projects")
    rc = runner.main(["--project-name", project, "--target-stack", "dotnet", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Discovered 2 features" in out
    assert "000-scaffold" in out
    assert "clientes" in out
    # `source-code/backend/`, não `source-code/dotnet/`: o diretório é definido
    # pela responsabilidade arquitetural do componente, nunca pela stack. A
    # stack (`dotnet`) segue registrada como metadado em tasks-progress.json.
    assert "dry-run: build and commit skipped" in (
        outputs / "tobe" / "source-code" / "backend" / "GENERATION_LOG.md"
    ).read_text(encoding="utf-8")
