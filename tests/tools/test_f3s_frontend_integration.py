"""Cenários 1, 2, 5, 6, 7 e 12 da correção da F3S.

O que estes testes protegem, em uma frase: o protótipo e o contrato de API viram
tarefas ligadas por um grafo, na stack que o projeto declarou — e o gate reprova
quando esse elo não existe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import prototype_manifest as pm  # noqa: E402
import speckit_task_compiler as compiler  # noqa: E402
import speckit_wave_manifest as waves  # noqa: E402
import verify_profiles as vp  # noqa: E402

from tests.tools.test_prototype_manifest import INDEX_HTML, SCREEN_LIST  # noqa: E402

OPENAPI = """openapi: "3.1.0"
info:
  title: "Employees API"
  version: "1.0.0"
  x-source-bc: "BC-01"
servers:
  - url: "https://example.test/api/v1"
paths:
  /employees:
    get:
      operationId: "GetAllEmployees"
      responses: {"200": {"description": "ok"}}
    post:
      operationId: "CreateEmployee"
      responses: {"201": {"description": "created"}}
"""

WAVE_MODEL = {
    "schema_version": "1.0.0",
    "project": "P",
    "trace_id": "trace-f3s",
    "waves": [
        {"wave_id": "W0", "wave_name": "Foundation", "wave_type": "foundation",
         "description": "Base", "bounded_contexts": [
             {"bc_id": "BC-09", "bc_name": "Cross-Cutting"}],
         "dependencies": [], "acceptance_criteria": []},
        {"wave_id": "W1", "wave_name": "Employees", "wave_type": "domain_core",
         "description": "CRUD", "bounded_contexts": [
             {"bc_id": "BC-01", "bc_name": "Employees"}],
         "dependencies": ["W0"], "acceptance_criteria": []},
    ],
}


def _config(frontend: str, backend: str) -> str:
    return (
        'project_name: "P"\n'
        "tobe_stack:\n"
        f'  frontend_framework: "{frontend}"\n'
        '  frontend_language: "typescript"\n'
        f'  backend_framework: "{backend}"\n'
        '  backend_language: "csharp"\n'
    )


def build_project(root: Path, *, frontend: str = "react",
                  backend: str = "dotnet") -> Path:
    project = root / "projects" / "P"
    outputs = project / "outputs"
    (project / "context").mkdir(parents=True)
    (outputs / "tobe" / "migration").mkdir(parents=True)
    (outputs / "tobe" / "docs" / "openapi").mkdir(parents=True)
    (outputs / "tobe" / "qa").mkdir(parents=True)
    (outputs / "tobe" / "prototype").mkdir(parents=True)
    (outputs / "tobe" / "speckit" / "specs").mkdir(parents=True)
    (outputs / "asis" / "docs").mkdir(parents=True)

    (project / "context" / "project-config.yaml").write_text(
        _config(frontend, backend), encoding="utf-8")
    (outputs / "tobe" / "prototype" / "index.html").write_text(
        INDEX_HTML, encoding="utf-8")
    (outputs / "tobe" / "prototype" / "screen-list.md").write_text(
        SCREEN_LIST, encoding="utf-8")
    (outputs / "tobe" / "migration" / "wave-model.json").write_text(
        json.dumps(WAVE_MODEL), encoding="utf-8")
    (outputs / "tobe" / "docs" / "wave-plan.md").write_text(
        "# Wave Plan\n\n## W0 — Foundation\n\n- BC-09 Cross-Cutting\n\n"
        "## W1 — Employees\n\n- BC-01 Employees\n", encoding="utf-8")
    (outputs / "tobe" / "docs" / "openapi" / "employees.yaml").write_text(
        OPENAPI, encoding="utf-8")
    (outputs / "tobe" / "docs" / "api-map.md").write_text(
        "| Flow | BC |\n|---|---|\n| listEmployees | BC-01 |\n", encoding="utf-8")
    (outputs / "tobe" / "docs" / "backlog-tobe.md").write_text(
        "## BC-01: Employees\n\n| ID | Story | Trace |\n|---|---|---|\n"
        "| US-EMP-001 | CRUD | BR-EMP-001 |\n", encoding="utf-8")
    (outputs / "tobe" / "qa" / "test-cases.md").write_text(
        "## BC-01: Employees\n\n### TC-EMP-001: List\n"
        "**Traceability**: BR-EMP-001\n", encoding="utf-8")
    (outputs / "asis" / "docs" / "business-rules.md").write_text(
        "### BR-EMP-001: Employee name is mandatory\n", encoding="utf-8")
    (outputs / "tobe" / "speckit" / "constitution.md").write_text(
        "# Constitution\n\n## 3.2 Frontend\nStack declarada.\n", encoding="utf-8")
    return project


# ─── Construtores de plano/fragmento ─────────────────────────────────────────

def _header(feature: str, wave: str, order: int) -> dict:
    return {
        "schema_version": "3.1.0", "project": "P", "trace_id": "trace-f3s",
        "feature": feature, "spec_id": f"SPEC-{wave}", "plan_id": f"PLAN-{wave}",
        "migration_wave_id": wave, "migration_wave_order": order,
    }


def _file(path: str, group: str, task_type: str, work_kind: str, **extra) -> dict:
    entry = {
        "path": path, "action": "create", "group": group, "task_type": task_type,
        "work_kind": work_kind, "responsibility": f"{work_kind} de {path}",
        "source_refs": [{"artifact": "outputs/tobe/speckit/constitution.md",
                         "anchor": "3.2 Frontend"}],
        "produces": [], "consumes": [],
    }
    entry.update(extra)
    return entry


def _task(task_id: str, group: str, path: str, task_type: str, stack: str,
          work_kind: str, **extra) -> dict:
    entry = {
        "task_id": task_id, "title": f"{work_kind}: {path}", "group": group,
        "task_type": task_type, "target_stack": stack,
        "source_refs": [{"artifact": "outputs/tobe/speckit/constitution.md",
                         "anchor": "3.2 Frontend"}],
        "target_file": path, "action": "create", "depends_on": [],
        "depends_on_groups": [], "produces": [], "consumes": [],
        "acceptance": [f"{path} existe e compila"], "verify_profile": "none",
        "priority": "P2", "story_points": 1, "work_kind": work_kind,
    }
    entry.update(extra)
    return entry


def write_feature(project: Path, feature: str, wave: str, order: int,
                  groups: list[dict], files: list[dict],
                  entries: list[dict]) -> None:
    directory = project / "outputs" / "tobe" / "speckit" / "specs" / feature
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "spec.md").write_text(f"# Spec {feature}\n", encoding="utf-8")
    (directory / "plan-graph.json").write_text(
        json.dumps({**_header(feature, wave, order), "groups": groups,
                    "files": files, "prototype_checksum": None}), encoding="utf-8")
    (directory / "task-fragment.json").write_text(
        json.dumps({**_header(feature, wave, order), "entries": entries}),
        encoding="utf-8")


def _group(name: str, stack: str, profile: str, depends_on=()) -> dict:
    return {"group": name, "target_stack": stack, "scope": name,
            "depends_on": list(depends_on), "verify_profile": profile}


def seed_full_plan(project: Path, *, frontend_stack: str,
                   backend_stack: str, with_integration: bool = True) -> None:
    """Plano completo: foundation com Design System + wave de domínio ligada."""
    manifest = json.loads(
        (project / "outputs" / "tobe" / "speckit"
         / "prototype-implementation-manifest.json").read_text(encoding="utf-8"))
    tokens = sorted({token["token_id"]
                     for key in ("colors", "typography", "spacing", "other_tokens")
                     for token in manifest["design_system"][key]})
    shared = sorted(component["component_id"]
                    for component in manifest["shared_components"]
                    if component.get("required"))
    by_id = {screen["screen_id"]: screen for screen in manifest["screens"]}
    w1_screens = [sid for sid, screen in by_id.items()
                  if screen["bounded_context"] == "BC-01"]
    w0_screens = [sid for sid, screen in by_id.items()
                  if screen["bounded_context"] == "BC-09"]
    w1_components = sorted({component["component_id"]
                            for sid in w1_screens
                            for component in by_id[sid]["components"]
                            if component.get("required")})
    w0_components = sorted({component["component_id"]
                            for sid in w0_screens
                            for component in by_id[sid]["components"]
                            if component.get("required")})
    w1_routes = sorted(by_id[sid]["route_id"] for sid in w1_screens)
    w0_routes = sorted(by_id[sid]["route_id"] for sid in w0_screens)
    flows = sorted(flow["flow_id"] for flow in manifest["flows"]
                   if flow["critical"]
                   and all(sid in by_id for sid in flow["screens"]))

    # ── W0: Design System + componentes compartilhados + telas estáticas ──
    write_feature(
        project, "001-w0-foundation", "W0", 0,
        [_group("G-DS", frontend_stack, "frontend-build")],
        [_file("frontend/src/styles/tokens.css", "G-DS", "frontend", "design_system",
               design_tokens=tokens,
               produces=[f"design-token:{token}" for token in tokens]),
         _file("frontend/src/shared/index.ts", "G-DS", "frontend",
               "frontend_component", component_ids=shared + w0_components,
               screen_ids=w0_screens, route_ids=w0_routes,
               produces=[f"component:{cid}" for cid in shared + w0_components]
                        + [f"screen:{sid}" for sid in w0_screens]
                        + [f"route:{rid}" for rid in w0_routes])],
        [_task("T-DS-001", "G-DS", "frontend/src/styles/tokens.css", "frontend",
               frontend_stack, "design_system", verify_profile="frontend-build"),
         _task("T-DS-002", "G-DS", "frontend/src/shared/index.ts", "frontend",
               frontend_stack, "frontend_component",
               verify_profile="frontend-unit-test")])

    # ── W1: contrato → implementação → client → integração → e2e ──
    integration_files = []
    integration_tasks = []
    if with_integration:
        integration_files = [
            _file("frontend/src/api/employees.client.ts", "G-FE", "frontend",
                  "frontend_api_client", api_ops=["GetAllEmployees", "CreateEmployee"],
                  screen_ids=w1_screens,
                  consumes=["api-contract:GetAllEmployees", "api-contract:CreateEmployee"],
                  produces=["api-client:GetAllEmployees", "api-client:CreateEmployee"]),
            _file("frontend/src/pages/employees.integration.ts", "G-FE", "frontend",
                  "frontend_integration", screen_ids=w1_screens,
                  api_ops=["GetAllEmployees", "CreateEmployee"],
                  consumes=["api-client:GetAllEmployees",
                            "api-implementation:GetAllEmployees"],
                  produces=["screen:" + w1_screens[0]]),
        ]
        integration_tasks = [
            _task("T-FE-003", "G-FE", "frontend/src/api/employees.client.ts",
                  "frontend", frontend_stack, "frontend_api_client",
                  verify_profile="frontend-unit-test"),
            _task("T-FE-004", "G-FE", "frontend/src/pages/employees.integration.ts",
                  "frontend", frontend_stack, "frontend_integration",
                  verify_profile="integration-test"),
        ]

    write_feature(
        project, "002-w1-employees", "W1", 1,
        [_group("G-API", backend_stack, "backend-unit-test"),
         _group("G-FE", frontend_stack, "frontend-unit-test", ["G-API"])],
        [_file("backend/Contracts/Employees.cs", "G-API", "backend",
               "backend_api_contract", api_ops=["GetAllEmployees", "CreateEmployee"],
               produces=["api-contract:GetAllEmployees", "api-contract:CreateEmployee"]),
         _file("backend/Controllers/EmployeesController.cs", "G-API", "backend",
               "backend_api_implementation",
               api_ops=["GetAllEmployees", "CreateEmployee"],
               rule_ids=["BR-EMP-001"], test_ids=["TC-EMP-001"],
               consumes=["api-contract:GetAllEmployees"],
               produces=["api-implementation:GetAllEmployees",
                         "api-implementation:CreateEmployee"]),
         _file("frontend/src/pages/employees-list.page.tsx", "G-FE", "frontend",
               "frontend_page", screen_ids=w1_screens, route_ids=w1_routes,
               component_ids=w1_components, design_tokens=tokens,
               produces=[f"route:{rid}" for rid in w1_routes]
                        + [f"component:{cid}" for cid in w1_components]
                        + [f"screen:{sid}" for sid in w1_screens]),
         *integration_files,
         _file("frontend/e2e/employees.spec.ts", "G-FE", "frontend",
               "end_to_end_test", flow_ids=flows, screen_ids=w1_screens,
               consumes=["api-implementation:GetAllEmployees"]
                        + (["api-client:GetAllEmployees"] if with_integration else []),
               produces=[f"test:e2e:{flow}" for flow in flows])],
        [_task("T-API-001", "G-API", "backend/Contracts/Employees.cs", "backend",
               backend_stack, "backend_api_contract", verify_profile="backend-build"),
         _task("T-API-002", "G-API", "backend/Controllers/EmployeesController.cs",
               "backend", backend_stack, "backend_api_implementation",
               verify_profile="backend-unit-test"),
         _task("T-FE-001", "G-FE", "frontend/src/pages/employees-list.page.tsx",
               "frontend", frontend_stack, "frontend_page",
               verify_profile="frontend-unit-test"),
         *integration_tasks,
         _task("T-E2E-001", "G-FE", "frontend/e2e/employees.spec.ts", "frontend",
               frontend_stack, "end_to_end_test", verify_profile="e2e-test")])


@pytest.fixture()
def react_dotnet(tmp_path: Path) -> Path:
    project = build_project(tmp_path, frontend="react", backend="dotnet")
    pm.write_manifest("P", tmp_path)
    waves.write_manifest("P", tmp_path)
    seed_full_plan(project, frontend_stack="react", backend_stack="dotnet")
    return tmp_path


# ─── Manifesto de waves ──────────────────────────────────────────────────────

def test_wave_manifest_liga_tela_a_operationid(react_dotnet: Path) -> None:
    """A junção que faltava: `GET /api/v1/employees` → `GetAllEmployees`."""
    manifest = json.loads(
        (react_dotnet / "projects/P/outputs/tobe/speckit/wave-spec-manifest.json")
        .read_text(encoding="utf-8"))
    w1 = next(item for item in manifest["features"] if item["wave_id"] == "W1")
    assert w1["prototype"]["api_ops"] == ["CreateEmployee", "GetAllEmployees"]
    screen = next(item for item in w1["prototype"]["screens"]
                  if item["screen_id"] == "SCR-EMPLOYEES-LIST")
    assert screen["api_ops"] == ["GetAllEmployees"]
    assert screen["api_endpoints"][0]["operation_id"] == "GetAllEmployees"


def test_wave_manifest_da_o_design_system_a_uma_unica_wave(react_dotnet: Path) -> None:
    """Ownership único do compartilhado — a prevenção de SINGLE-CREATE-OWNER."""
    manifest = json.loads(
        (react_dotnet / "projects/P/outputs/tobe/speckit/wave-spec-manifest.json")
        .read_text(encoding="utf-8"))
    owners = [item["feature"] for item in manifest["features"]
              if (item.get("prototype") or {}).get("owns_shared_components")]
    assert owners == ["001-w0-foundation"]
    w0 = next(item for item in manifest["features"] if item["wave_id"] == "W0")
    assert w0["prototype"]["design_system"]["colors"]
    w1 = next(item for item in manifest["features"] if item["wave_id"] == "W1")
    assert w1["prototype"]["design_system"] == {}


def test_wave_manifest_nao_vaza_telas_de_outra_wave(react_dotnet: Path) -> None:
    manifest = json.loads(
        (react_dotnet / "projects/P/outputs/tobe/speckit/wave-spec-manifest.json")
        .read_text(encoding="utf-8"))
    w1 = next(item for item in manifest["features"] if item["wave_id"] == "W1")
    assert [item["screen_id"] for item in w1["prototype"]["screens"]] == [
        "SCR-EMPLOYEES-FORM", "SCR-EMPLOYEES-LIST"]
    anchors = {source["source_id"]: source["anchors"] for source in w1["sources"]}
    assert "SCR-ABOUT" not in anchors["prototype-manifest"]
    assert anchors["prototype-html"] == ["screen-employees-form",
                                         "screen-employees-list"]


def test_cenario_5_operacao_orfa_do_openapi_vira_warning(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    (project / "outputs/tobe/docs/openapi/orphan.yaml").write_text(
        'openapi: "3.1.0"\ninfo:\n  x-source-bc: "BC-77"\npaths:\n'
        "  /orphan:\n    get:\n      operationId: \"GetOrphan\"\n", encoding="utf-8")
    pm.write_manifest("P", tmp_path)
    manifest = waves.build_manifest("P", tmp_path)
    assert any("GetOrphan" in warning for warning in manifest["warnings"])


# ─── Grafo compilado ─────────────────────────────────────────────────────────

def test_cenario_1_grafo_liga_frontend_ao_backend(react_dotnet: Path) -> None:
    output = compiler.compile_project("P", react_dotnet)
    edges = {(edge["from"], edge["to"]) for edge in output["dependency_edges"]}
    # contrato → client → integração → e2e, e implementação → integração
    assert ("T-API-001", "T-FE-003") in edges
    assert ("T-FE-003", "T-FE-004") in edges
    assert ("T-API-002", "T-FE-004") in edges
    assert ("T-API-002", "T-E2E-001") in edges
    assert ("T-FE-003", "T-E2E-001") in edges
    assert not [item for item in output["integration_findings"]
                if item["severity"] == "error"]


def test_cenario_1_rastreabilidade_chega_a_tela_e_ao_token(react_dotnet: Path) -> None:
    output = compiler.compile_project("P", react_dotnet)
    by_id = {entry["task_id"]: entry for entry in output["entries"]}
    page = by_id["T-FE-001"]
    assert "SCR-EMPLOYEES-LIST" in page["screen_ids"]
    assert page["route_ids"] == ["RTE-EMPLOYEES-FORM", "RTE-EMPLOYEES-LIST"]
    assert page["work_kind"] == "frontend_page"
    assert "TOK-COLOR-PRIMARY" in by_id["T-DS-001"]["design_tokens"]
    # A ordem vem do plano e é preservada: o compilador não reordena o que o
    # plano declarou, só garante que o conjunto é o mesmo.
    assert sorted(by_id["T-API-002"]["api_ops"]) == ["CreateEmployee",
                                                     "GetAllEmployees"]
    assert output["prototype_checksum"].startswith("sha256:")


def test_cenario_12_sem_task_de_integracao_o_gate_reprova(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    pm.write_manifest("P", tmp_path)
    waves.write_manifest("P", tmp_path)
    seed_full_plan(project, frontend_stack="react", backend_stack="dotnet",
                   with_integration=False)
    output = compiler.compile_project("P", tmp_path)
    codes = {item["check_id"] for item in output["integration_findings"]}
    assert "FRONTEND-BACKEND-INTEGRATION" in codes
    finding = next(item for item in output["integration_findings"]
                   if item["check_id"] == "FRONTEND-BACKEND-INTEGRATION")
    assert finding["severity"] == "error"
    assert "SCR-EMPLOYEES-LIST" in finding["affected_items"]
    # ...e nenhuma task íntegra foi descartada por causa disso.
    assert output["total_tasks"] == 6


def test_api_e_tela_inventadas_sao_reprovadas(react_dotnet: Path) -> None:
    """A proibição de inventar é implementada, não só pedida no prompt."""
    specs = react_dotnet / "projects/P/outputs/tobe/speckit/specs/002-w1-employees"
    plan = json.loads((specs / "plan-graph.json").read_text(encoding="utf-8"))
    for item in plan["files"]:
        if item["work_kind"] == "frontend_page":
            item["screen_ids"] = item["screen_ids"] + ["SCR-INEXISTENTE"]
            item["api_ops"] = ["OperacaoQueNaoExiste"]
    (specs / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")

    output = compiler.compile_project("P", react_dotnet, write=False)
    codes = {item["check_id"] for item in output["integration_findings"]}
    assert {"PROTOTYPE-REF-INTEGRITY", "API-REF-INTEGRITY"} <= codes
    invented = next(item for item in output["integration_findings"]
                    if item["check_id"] == "PROTOTYPE-REF-INTEGRITY")
    assert invented["affected_items"] == ["SCR-INEXISTENTE"]


def test_cenario_6_duas_waves_criam_o_mesmo_componente(tmp_path: Path) -> None:
    """Owner determinístico, sem perder nenhuma task íntegra."""
    project = build_project(tmp_path)
    pm.write_manifest("P", tmp_path)
    waves.write_manifest("P", tmp_path)
    seed_full_plan(project, frontend_stack="react", backend_stack="dotnet")
    disputed = "frontend/src/shared/index.ts"
    specs = project / "outputs/tobe/speckit/specs/002-w1-employees"
    plan = json.loads((specs / "plan-graph.json").read_text(encoding="utf-8"))
    plan["files"].append(_file(disputed, "G-FE", "frontend", "frontend_component"))
    (specs / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")
    fragment = json.loads((specs / "task-fragment.json").read_text(encoding="utf-8"))
    fragment["entries"].append(
        _task("T-FE-099", "G-FE", disputed, "frontend", "react",
              "frontend_component"))
    (specs / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")

    first = compiler.compile_project("P", tmp_path, write=False)
    second = compiler.compile_project("P", tmp_path, write=False)

    conflicts = [item for item in first["ownership_conflicts"]
                 if item["target_file"] == disputed]
    assert conflicts, "conflito de create precisa ser registrado"
    owners = [entry for entry in first["entries"]
              if entry["target_file"] == disputed and entry["action"] == "create"]
    assert len(owners) == 1, "exatamente um dono de create"
    # Nenhuma task removida: as duas continuam no grafo, uma virou update.
    touching = [entry for entry in first["entries"]
                if entry["target_file"] == disputed]
    assert {entry["task_id"] for entry in touching} == {"T-DS-002", "T-FE-099"}
    # Determinístico entre execuções (cenário 10).
    assert first["graph_checksum"] == second["graph_checksum"]
    assert [entry["task_id"] for entry in first["entries"]] == \
        [entry["task_id"] for entry in second["entries"]]


# ─── Comandos de verificação ─────────────────────────────────────────────────

def test_cenario_7_verify_command_incompativel_e_normalizado(react_dotnet: Path) -> None:
    specs = react_dotnet / "projects/P/outputs/tobe/speckit/specs/002-w1-employees"
    fragment = json.loads((specs / "task-fragment.json").read_text(encoding="utf-8"))
    for entry in fragment["entries"]:
        if entry["task_id"] == "T-FE-001":
            entry.pop("verify_profile")
            entry["verify_command"] = "ng build --configuration=production"
    (specs / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")

    output = compiler.compile_project("P", react_dotnet, write=False)
    task = next(entry for entry in output["entries"] if entry["task_id"] == "T-FE-001")
    # O perfil declarado pelo GRUPO no plano vence a prosa da LLM — o plano é a
    # autoridade, e o comando escrito à mão nunca é aceito como veio.
    assert task["verify_profile"] == "frontend-unit-test"
    assert "ng build" not in (task["verify_command"] or "")
    replaced = {item["task_id"] for item in output["incompatible_verify_commands"]}
    assert "T-FE-001" in replaced


def test_cenario_7_sem_perfil_declarado_o_comando_e_inferido(
        react_dotnet: Path) -> None:
    """Sem perfil no plano nem no grupo, o perfil sai do comando — e o comando,
    da stack. É o caminho de migração dos planos 3.0.0."""
    specs = react_dotnet / "projects/P/outputs/tobe/speckit/specs/002-w1-employees"
    for name, mutate in (("plan-graph.json", "groups"),
                         ("task-fragment.json", "entries")):
        data = json.loads((specs / name).read_text(encoding="utf-8"))
        for item in data[mutate]:
            item.pop("verify_profile", None)
        if mutate == "entries":
            for item in data[mutate]:
                item["verify_command"] = ("ng build --configuration=production"
                                          if item["task_type"] == "frontend"
                                          else "dotnet build")
        (specs / name).write_text(json.dumps(data), encoding="utf-8")

    output = compiler.compile_project("P", react_dotnet, write=False)
    page = next(entry for entry in output["entries"]
                if entry["task_id"] == "T-FE-001")
    assert page["verify_profile"] == "frontend-build"
    assert page["verify_command"].startswith("npm")
    api = next(entry for entry in output["entries"]
               if entry["task_id"] == "T-API-002")
    assert api["verify_profile"] == "backend-build"
    assert "verify_dotnet_solution.py" in api["verify_command"]


@pytest.mark.parametrize(
    "stack,profile,expected_head",
    [("dotnet", "backend-unit-test", "dotnet"),
     ("spring-boot", "backend-build", "mvn"),
     ("fastapi", "backend-unit-test", "python"),
     ("react", "frontend-build", "npm"),
     ("gin", "backend-build", "go")],
)
def test_perfil_resolve_para_a_toolchain_da_stack(stack, profile, expected_head,
                                                  tmp_path: Path) -> None:
    result = vp.resolve(profile, stack=stack, project_dir=tmp_path,
                        repo_root=REPO_ROOT)
    assert result["command"][0] == expected_head


def test_stack_com_verificador_deterministico_vence_a_llm(tmp_path: Path) -> None:
    """Angular e .NET têm harness próprio; ele é a autoridade de 'compila e roda'."""
    for stack, verifier in (("angular", "verify_angular_app.py"),
                            ("dotnet", "verify_dotnet_solution.py")):
        profile = "frontend-build" if stack == "angular" else "backend-build"
        result = vp.resolve(profile, stack=stack, project_dir=tmp_path,
                            repo_root=REPO_ROOT)
        assert result["resolved_from"] == "stack-verifier"
        assert verifier in " ".join(result["command"])
        # `{python}` e não um caminho absoluto: o comando vai para um artefato.
        assert result["command"][0] == "{python}"


def test_perfil_de_familia_errada_e_corrigido_pela_stack() -> None:
    result = vp.normalize("dotnet build", stack="react", task_type="frontend")
    assert result["verify_profile"] == "frontend-build"
    assert result["compatible"] is False
    assert any("não pertence à stack" in warning for warning in result["warnings"])


def test_tokens_sao_normalizados_para_a_forma_canonica() -> None:
    assert compiler.normalize_token("API-Contract:GetAll") == "api-contract:GetAll"
    assert compiler.normalize_token("Screen:scr-x") == "screen:SCR-X"
    assert compiler.normalize_token("Contract:BaseEntity") == "contract:baseentity"
    assert compiler.token_parts("api-client:GetAll") == ("api-client", "GetAll")


# ─── Cenário 2: outra stack, nenhum vazamento da anterior ────────────────────

def test_cenario_2_angular_spring_nao_referencia_react_nem_dotnet(
        tmp_path: Path) -> None:
    project = build_project(tmp_path, frontend="angular", backend="spring-boot")
    pm.write_manifest("P", tmp_path)
    waves.write_manifest("P", tmp_path)
    seed_full_plan(project, frontend_stack="angular", backend_stack="spring-boot")
    output = compiler.compile_project("P", tmp_path, write=False)

    stacks = {entry["target_stack"] for entry in output["entries"]}
    assert stacks == {"angular", "spring-boot"}
    commands = " ".join(entry["verify_command"] or "" for entry in output["entries"])
    assert "dotnet" not in commands
    assert "verify_angular_app.py" in commands   # harness da stack frontend
    assert "mvn" in commands                     # toolchain da stack backend

    manifest = json.loads(
        (tmp_path / "projects/P/outputs/tobe/speckit"
         / "prototype-implementation-manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_stack"]["frontend_framework"] == "angular"
    assert manifest["target_stack"]["backend_framework"] == "spring-boot"


# ─── Suíte de checks ─────────────────────────────────────────────────────────

def _run_suite(root: Path, monkeypatch) -> dict:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter
    from src.shared.checks.suites import speckit_frontend_integration as suite

    monkeypatch.setattr(CheckContext, "REPO_ROOT", root)
    monkeypatch.setattr(suite, "REPO_ROOT", root)
    reporter = Reporter()
    suite.SpeckitFrontendIntegrationSuite(CheckContext("P")).run(reporter)
    return {result.name.split()[0]: result.passed for result in reporter._results}


def test_plano_completo_passa_todos_os_doze_checks(react_dotnet: Path,
                                                   monkeypatch) -> None:
    compiler.compile_project("P", react_dotnet)
    results = _run_suite(react_dotnet, monkeypatch)
    assert len(results) == 12
    failed = sorted(name for name, passed in results.items() if not passed)
    assert failed == [], f"checks reprovados num plano completo: {failed}"


def test_cenario_12_check_de_integracao_reprova_sem_a_task(tmp_path: Path,
                                                           monkeypatch) -> None:
    project = build_project(tmp_path)
    pm.write_manifest("P", tmp_path)
    waves.write_manifest("P", tmp_path)
    seed_full_plan(project, frontend_stack="react", backend_stack="dotnet",
                   with_integration=False)
    compiler.compile_project("P", tmp_path)
    results = _run_suite(tmp_path, monkeypatch)
    assert results["FRONTEND-BACKEND-INTEGRATION"] is False
    assert results["FRONTEND-API-CLIENT-COVERAGE"] is False
    # Cobertura de tela e de backend continuam OK: a lacuna é localizada.
    assert results["PROTOTYPE-SCREEN-COVERAGE"] is True
    assert results["API-OPERATION-COVERAGE"] is True


def test_cenario_9_check_de_checksum_reprova_prototipo_alterado(
        react_dotnet: Path, monkeypatch) -> None:
    compiler.compile_project("P", react_dotnet)
    prototype = react_dotnet / "projects/P" / pm.PROTOTYPE_REL
    prototype.write_text(INDEX_HTML + "<!-- mudou -->", encoding="utf-8")
    results = _run_suite(react_dotnet, monkeypatch)
    assert results["PROTOTYPE-CHECKSUM-CONSISTENCY"] is False


def test_relatorio_estruturado_e_persistido(react_dotnet: Path, monkeypatch) -> None:
    compiler.compile_project("P", react_dotnet)
    _run_suite(react_dotnet, monkeypatch)
    from src.shared.checks.suites import speckit_frontend_integration as suite

    report = json.loads(
        (react_dotnet / "projects/P" / suite.REPORT_REL).read_text(encoding="utf-8"))
    assert report["total"] == 12
    for finding in report["findings"]:
        assert set(finding) >= {"check_id", "status", "severity", "feature", "wave",
                                "task_ids", "affected_items", "evidence",
                                "recommended_action"}
