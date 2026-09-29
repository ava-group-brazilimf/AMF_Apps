"""Roteamento e diretórios canônicos da F4 — `src/shared/tools/f4_routing.py`.

Dois invariantes, e os dois vieram de defeito real:

1. **Sem fallback genérico.** O `agent_map` do YAML mandava as nove stacks para
   o mesmo `ava-f4s-codegen-agent`; os coders declarados em
   `tech-stack/module.yaml` nunca eram carregados. Aqui, stack sem agente
   especializado FALHA — não vira despacho genérico.
2. **Sem caminho por stack.** `source-code/dotnet` e `source-code/angular` são
   proibidos. O destino sai de `task_type`, nunca de `target_stack`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_routing


def _task(**campos) -> dict:
    base = {
        "task_id": "T-001",
        "task_type": "backend",
        "target_stack": "dotnet",
        "verify_command": "dotnet build",
        "feature": "001-domain",
    }
    base.update(campos)
    return base


# ─── A. Roteamento ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("stack,esperado", [
    ("dotnet", "ava-stack-dotnet-backend"),
    ("spring-boot", "ava-stack-java-backend"),
    ("java", "ava-stack-java-backend"),
    ("fastapi", "ava-stack-python-backend"),
    ("gin", "ava-stack-go-backend"),
    ("nestjs", "ava-stack-node-backend"),
])
def test_backend_roteia_para_o_coder_da_stack(stack: str, esperado: str) -> None:
    rota = f4_routing.resolve_route(_task(target_stack=stack, verify_command=""), "P")
    assert rota.agent == esperado
    assert rota.component_type == "backend"


@pytest.mark.parametrize("stack,esperado", [
    ("angular", "ava-stack-angular-frontend"),
    ("react", "ava-stack-react-frontend"),
    ("vue", "ava-stack-vue-frontend"),
    ("blazor", "ava-stack-blazor-frontend"),
])
def test_frontend_roteia_para_o_coder_da_stack(stack: str, esperado: str) -> None:
    rota = f4_routing.resolve_route(
        _task(task_type="frontend", target_stack=stack, verify_command=""), "P")
    assert rota.agent == esperado
    assert rota.component_type == "frontend"


def test_stack_desconhecida_falha_sem_agente_generico() -> None:
    with pytest.raises(f4_routing.RoutingError) as exc:
        f4_routing.resolve_route(_task(target_stack="cobol", task_type=""), "P")
    assert "ava-f4s-codegen-agent" not in str(exc.value)


def test_nenhuma_rota_aponta_para_o_agente_generico() -> None:
    alvos = {item["agent"] for item in f4_routing.routing_table()}
    assert not (alvos & f4_routing.FORBIDDEN_ROUTE_TARGETS)


def test_agente_ausente_no_registry_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(f4_routing.STACK_AGENTS["backend"], "dotnet",
                        "ava-stack-inexistente")
    with pytest.raises(f4_routing.RoutingError) as exc:
        f4_routing.resolve_route(_task(), "P")
    assert exc.value.code in {"ROUTE009", "ROUTE010"}


def test_tabela_de_roteamento_coerente_com_o_repositorio() -> None:
    assert f4_routing.validate_routing_table() == []


def test_task_type_conflitante_com_a_stack_falha() -> None:
    """`frontend` com `dotnet` é defeito de planejamento — não escolha de caminho."""
    with pytest.raises(f4_routing.RoutingError) as exc:
        f4_routing.resolve_route(_task(task_type="frontend", target_stack="dotnet"), "P")
    assert exc.value.code == "ROUTE003"


def test_component_type_derivado_da_stack_quando_ausente() -> None:
    assert f4_routing.component_type_for_task(
        _task(task_type="", target_stack="angular")) == "frontend"


# ─── B. Diretórios ───────────────────────────────────────────────────────────

def test_backend_sempre_resolve_source_code_backend(tmp_path: Path) -> None:
    rota = f4_routing.resolve_route(_task(), "P", tmp_path)
    assert rota.canonical_source_rel == "source-code/backend"
    assert rota.canonical_source_dir.as_posix().endswith(
        "projects/P/outputs/tobe/source-code/backend")


def test_frontend_sempre_resolve_source_code_frontend(tmp_path: Path) -> None:
    rota = f4_routing.resolve_route(
        _task(task_type="frontend", target_stack="angular", verify_command=""),
        "P", tmp_path)
    assert rota.canonical_source_rel == "source-code/frontend"


@pytest.mark.parametrize("stack", ["dotnet", "spring-boot", "fastapi", "gin"])
def test_target_stack_nao_altera_o_caminho(stack: str, tmp_path: Path) -> None:
    rota = f4_routing.resolve_route(
        _task(target_stack=stack, verify_command=""), "P", tmp_path)
    assert rota.canonical_source_rel == "source-code/backend"
    assert stack not in rota.canonical_source_dir.as_posix()


def test_harness_e_scaffold_usam_a_mesma_resolucao(tmp_path: Path) -> None:
    import f4s_deterministic_harness as harness
    import scaffold_paths

    tobe = tmp_path / "projects" / "P" / "outputs" / "tobe"
    tobe.mkdir(parents=True)
    do_scaffold = scaffold_paths.resolve_output_dir(tobe, "backend")
    do_harness = harness.component_source_dir("P", "backend", tmp_path)
    da_rota = f4_routing.resolve_route(_task(), "P", tmp_path).canonical_source_dir
    assert do_scaffold == do_harness == da_rota


def test_stack_source_dir_nao_devolve_mais_caminho_por_stack(tmp_path: Path) -> None:
    """Regressão direta: era `source-code/dotnet`, virou `source-code/backend`."""
    import f4s_deterministic_harness as harness
    destino = harness.stack_source_dir("P", "dotnet", tmp_path).as_posix()
    assert destino.endswith("source-code/backend")
    assert "source-code/dotnet" not in destino


def test_nenhum_modulo_da_f4_reintroduz_caminho_por_stack() -> None:
    """Varre o código-fonte atrás dos antipadrões que `scaffold_paths` proíbe."""
    import scaffold_paths
    alvos = [
        "f4_routing.py", "f4_loop.py", "f4_task_context.py",
        "f4s_deterministic_harness.py", "f4s_build_runner.py",
        "f4s_git_helper.py", "ava_pipeline.py",
    ]
    achados: dict[str, list[str]] = {}
    for nome in alvos:
        texto = (TOOLS_DIR / nome).read_text(encoding="utf-8")
        rotulos = scaffold_paths.find_stack_path_antipatterns(texto)
        if rotulos:
            achados[nome] = rotulos
    assert achados == {}, f"caminho derivado da stack reintroduzido: {achados}"


def test_tabela_concorda_com_o_module_yaml() -> None:
    """Duas listas da mesma verdade precisam concordar — ou uma delas mente."""
    yaml = pytest.importorskip("yaml")
    modulo = yaml.safe_load(
        (REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "tech-stack"
         / "module.yaml").read_text(encoding="utf-8"))
    declarados = {
        (a["component_type"], a["routing_key"]): a["id"]
        for a in modulo["agents"]
        if a.get("routing_key") and a.get("component_type")
    }
    for (componente, stack), agente in declarados.items():
        assert f4_routing.STACK_AGENTS[componente][stack] == agente, (
            f"module.yaml roteia {componente}/{stack} para {agente}, "
            f"f4_routing discorda")


def test_specs_dos_coders_declaram_o_contrato_por_task() -> None:
    """Sem o contrato na spec, o agente não sabe que é uma task por despacho."""
    agentes = REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "tech-stack" / "agents"
    for item in f4_routing.routing_table():
        spec = REPO_ROOT / f4_routing.spec_path_for(item["agent"])
        texto = spec.read_text(encoding="utf-8")
        assert "<!-- F4_RESULT -->" in texto, f"{spec.name} sem contrato de resultado"
        assert "source-code/frontend" in texto and "source-code/backend" in texto, (
            f"{spec.name} não nomeia os diretórios canônicos")
    assert agentes.is_dir()


def test_repo_de_commit_e_o_baseline_da_f4s(tmp_path: Path) -> None:
    """A F4 commita em `source-code/`, o mesmo repo que a F4S inaugurou."""
    rota = f4_routing.resolve_route(_task(), "P", tmp_path)
    assert rota.repo_dir.as_posix().endswith("outputs/tobe/source-code")
    assert rota.canonical_source_dir.parent == rota.repo_dir


def test_specs_proibem_recriar_o_scaffold() -> None:
    """Cenários 1 e 2: a proibição precisa estar escrita onde o agente lê."""
    proibicoes = ("dotnet new", "npm create", "reutilize, nunca recrie")
    for item in f4_routing.routing_table():
        texto = (REPO_ROOT / f4_routing.spec_path_for(item["agent"])).read_text(
            encoding="utf-8")
        for termo in proibicoes:
            assert termo in texto, f"{item['agent']} nao proibe `{termo}`"
        assert "source-code/infra" in texto, (
            f"{item['agent']} nao documenta o destino de tasks de infraestrutura")


def test_agente_de_infra_tem_o_contrato_da_f4() -> None:
    spec = REPO_ROOT / f4_routing.spec_path_for(f4_routing.INFRA_AGENT)
    texto = spec.read_text(encoding="utf-8")
    assert "<!-- F4_RESULT -->" in texto
    assert "source-code/infra" in texto
