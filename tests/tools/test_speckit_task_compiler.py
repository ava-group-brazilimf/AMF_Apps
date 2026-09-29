"""Tests for the deterministic two-pass SpecKit task compiler."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import speckit_task_compiler as compiler  # noqa: E402


def _write_feature(root: Path, feature: str, group: str, task_id: str, target: str,
                   *, task_type="backend", group_dependencies=None, produces=None,
                   consumes=None, source_refs=None):
    directory = root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "specs" / feature
    directory.mkdir(parents=True)
    references = source_refs or [{"artifact": "outputs/source.md", "anchor": "ANCHOR"}]
    wave_order = int(feature[:3]) - 1
    plan = {
        "schema_version": "3.0.0", "project": "P", "trace_id": "trace-1",
        "feature": feature, "spec_id": f"SPEC-{group[2:]}-001",
        "plan_id": f"PLAN-{group[2:]}-001",
        "migration_wave_id": f"W{wave_order}", "migration_wave_order": wave_order,
        "groups": [{
            "group": group, "target_stack": "dotnet", "scope": feature,
            "depends_on": group_dependencies or [], "verify_command": "dotnet build",
        }],
        "files": [{
            "path": target, "action": "create", "group": group,
            "task_type": task_type,
            "responsibility": feature, "source_refs": references,
            "produces": produces or [], "consumes": consumes or [],
        }],
    }
    fragment = {
        "schema_version": "3.0.0", "project": "P", "trace_id": "trace-1",
        "feature": feature, "spec_id": plan["spec_id"], "plan_id": plan["plan_id"],
        "migration_wave_id": plan["migration_wave_id"],
        "migration_wave_order": plan["migration_wave_order"],
        "entries": [{
            "task_id": task_id, "title": f"Implementar {feature}", "group": group,
            "task_type": task_type, "target_stack": "dotnet",
            "source_refs": references, "target_file": target, "action": "create",
            "depends_on": [], "depends_on_groups": [], "produces": produces or [],
            "consumes": consumes or [], "acceptance": ["dotnet build sem erro"],
            "verify_command": "dotnet build", "priority": "P2", "story_points": 1,
        }],
    }
    (directory / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")
    (directory / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")
    speckit = directory.parents[1]
    manifest_path = speckit / "wave-spec-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.is_file() else {
            "schema_version": "1.0.0", "project": "P", "features": [],
        }
    manifest["features"] = [
        item for item in manifest["features"] if item["feature"] != feature
    ]
    manifest["features"].append({
        "feature": feature, "wave_id": plan["migration_wave_id"],
        "migration_wave_order": plan["migration_wave_order"], "codegen": True,
        "depends_on": [],
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_extract_scaffold_structure_pulls_body_until_next_heading():
    spec_md = (
        "# Scaffold\n\n"
        "## Objetivo\n\ntexto\n\n"
        "## Estrutura a gerar\n\n"
        "```\nangular.json\npackage.json\n```\n\n"
        "## Restrições\n\ntexto\n"
    )
    assert compiler._extract_scaffold_structure(spec_md) == (
        "```\nangular.json\npackage.json\n```"
    )


def test_extract_scaffold_structure_missing_heading_returns_empty():
    assert compiler._extract_scaffold_structure("# Scaffold\n\nsem secao\n") == ""


def test_compiler_resolves_cross_feature_producer_consumer(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs",
                   produces=["contract:cart"])
    _write_feature(tmp_path, "002-api", "G-API", "T-API-001", "Api/CartEndpoint.cs",
                   group_dependencies=["G-DOMAIN"], consumes=["contract:cart"])

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["execution_order"] == ["T-DOMAIN-001", "T-API-001"]
    assert output["execution_waves"] == [["T-DOMAIN-001"], ["T-API-001"]]
    assert output["entries"][1]["depends_on"] == ["T-DOMAIN-001"]
    assert output["dependency_edges"][0]["reason"] == "producer_consumer"


def test_frontend_api_consumer_exposes_direct_backend_dependency(tmp_path: Path):
    _write_feature(
        tmp_path, "001-api", "G-API", "T-API-001", "backend/Api/CartEndpoint.cs",
        task_type="backend", produces=["api:getCart"],
    )
    _write_feature(
        tmp_path, "002-cart-screen", "G-CART-UI", "T-CART-UI-001",
        "frontend/src/cart/cart.page.ts", task_type="frontend",
        consumes=["api:getCart"],
    )

    output = compiler.compile_project("P", tmp_path, write=True)
    entries = {entry["task_id"]: entry for entry in output["entries"]}
    frontend_tasks = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "specs" / "002-cart-screen" / "tasks.md"
    ).read_text(encoding="utf-8")

    assert output["schema_version"] == "4.0.0"
    assert entries["T-API-001"]["task_type"] == "backend"
    assert entries["T-API-001"]["backend_dependencies"] == []
    assert entries["T-CART-UI-001"]["task_type"] == "frontend"
    assert entries["T-CART-UI-001"]["depends_on"] == ["T-API-001"]
    assert entries["T-CART-UI-001"]["backend_dependencies"] == ["T-API-001"]
    assert "| frontend |" in frontend_tasks
    assert "| T-API-001 |" in frontend_tasks
    assert output["dependency_edges"] == [{
        "from": "T-API-001", "to": "T-CART-UI-001",
        "reason": "producer_consumer", "source": "api:getCart",
    }]


def test_compiler_preserves_multiple_verified_source_references(tmp_path: Path):
    references = [
        {"artifact": "outputs/asis/docs/business-rules.md", "anchor": "BR-CART-001"},
        {"artifact": "outputs/tobe/docs/openapi/orders.yaml", "anchor": "GetCart"},
        {"artifact": "outputs/tobe/qa/test-cases.md", "anchor": "TC-CART-001"},
    ]
    _write_feature(
        tmp_path, "001-cart", "G-CART", "T-CART-001", "Domain/Cart.cs",
        source_refs=references,
    )

    output = compiler.compile_project("P", tmp_path, write=False)
    entry = output["entries"][0]

    assert entry["source_refs"] == references
    assert entry["migration_wave_id"] == "W0"
    assert entry["migration_wave_order"] == 0


def test_compiled_traceability_conforms_to_v4_schema(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    _write_feature(tmp_path, "001-cart", "G-CART", "T-CART-001", "Domain/Cart.cs")
    output = compiler.compile_project("P", tmp_path, write=False)
    schema = json.loads((
        REPO_ROOT / "src" / "shared" / "schemas" / "speckit-traceability-v4.schema.json"
    ).read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator(schema).validate(output)


def test_compiler_writes_json_before_human_views(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")

    output = compiler.compile_project("P", tmp_path)
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"

    persisted = json.loads((speckit / "traceability.json").read_text(encoding="utf-8"))
    tasks = (speckit / "specs" / "001-domain" / "tasks.md").read_text(encoding="utf-8")
    assert persisted["graph_checksum"] == output["graph_checksum"]
    assert "T-DOMAIN-001" in tasks


def test_scaffold_tasks_md_embeds_estrutura_a_gerar(tmp_path: Path):
    """Feature de scaffold sem plan.md — tasks.md carrega a árvore do spec.md."""
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")

    feature = "000-scaffold-frontend"
    directory = (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
                / "specs" / feature)
    directory.mkdir(parents=True)
    references = [{"artifact": f"outputs/tobe/speckit/specs/{feature}/spec.md",
                  "anchor": "Estrutura a gerar"}]
    plan = {
        "schema_version": "3.0.0", "project": "P", "trace_id": "trace-1",
        "feature": feature, "spec_id": "SPEC-SCAFFOLD-FRONTEND-001",
        "plan_id": "PLAN-SCAFFOLD-FRONTEND-001",
        "migration_wave_id": "W0", "migration_wave_order": 0,
        "groups": [{
            "group": "G-SCAFFOLD-FRONTEND", "target_stack": "angular",
            "scope": "scaffold", "depends_on": [], "verify_command": "ng build",
        }],
        "files": [{
            "path": ".scaffold/000-scaffold-frontend.md", "action": "create",
            "group": "G-SCAFFOLD-FRONTEND", "task_type": "frontend",
            "responsibility": feature, "source_refs": references,
            "produces": ["artifact:scaffold:frontend"], "consumes": [],
        }],
    }
    fragment = {
        "schema_version": "3.0.0", "project": "P", "trace_id": "trace-1",
        "feature": feature, "spec_id": plan["spec_id"], "plan_id": plan["plan_id"],
        "migration_wave_id": "W0", "migration_wave_order": 0,
        "entries": [{
            "task_id": "T-SCAFFOLD-FRONTEND-001", "title": "Scaffold Angular Frontend",
            "group": "G-SCAFFOLD-FRONTEND", "task_type": "frontend",
            "target_stack": "angular", "source_refs": references,
            "target_file": ".scaffold/000-scaffold-frontend.md", "action": "create",
            "depends_on": [], "depends_on_groups": [],
            "produces": ["artifact:scaffold:frontend"], "consumes": [],
            "acceptance": ["ng build sem erro"], "verify_command": "ng build",
            "priority": "P1", "story_points": 1,
        }],
    }
    (directory / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")
    (directory / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")
    (directory / "spec.md").write_text(
        "# Scaffold\n\n## Estrutura a gerar\n\n```\nangular.json\npackage.json\n```\n\n"
        "## Restrições\n\ntexto\n", encoding="utf-8")

    compiler.compile_project("P", tmp_path)

    scaffold_tasks = (directory / "tasks.md").read_text(encoding="utf-8")
    domain_tasks = (directory.parents[0] / "001-domain" / "tasks.md").read_text(encoding="utf-8")
    assert "## Estrutura Esperada (redundância — ver spec.md)" in scaffold_tasks
    assert "angular.json" in scaffold_tasks
    assert "## Estrutura Esperada" not in domain_tasks


def test_consumer_without_producer_degrada_sem_travar(tmp_path: Path):
    """Consumo órfão vira aviso, não CompilerError.

    Travar aqui custava a F3S inteira por um arquivo esquecido na seção 4 de um
    único plano — e derrubava junto `traceability.json` e todos os `tasks.md`,
    que já estavam corretos. Sem produtor não há aresta a criar: a ordenação
    segue válida, só menos restrita, e a pendência fica registrada.
    """
    _write_feature(tmp_path, "001-api", "G-API", "T-API-001", "Api/CartEndpoint.cs",
                   consumes=["contract:missing"])

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["total_tasks"] == 1
    assert output["orphan_consumes"] == ["T-API-001 → contract:missing"]
    assert not [edge for edge in output["dependency_edges"]
                if edge["source"] == "contract:missing"]
    orfaos = [w for w in output["warnings"] if w["code"] == "C004"]
    assert len(orfaos) == 1
    assert "contract:missing" in orfaos[0]["message"]
    assert orfaos[0]["fix"]


def test_dotfile_target_e_arquivo_nao_diretorio(tmp_path: Path):
    """`.gitkeep` não tem sufixo, mas é arquivo.

    `PurePosixPath('.gitkeep').suffix` é '', e testar só o sufixo classificava
    todo placeholder como diretório — foi o que reprovou a compilação de
    nopcommerce-04 em 2026-08-21.
    """
    _write_feature(tmp_path, "001-infra", "G-INFRA", "T-INFRA-001",
                   "Infra/Persistence/Migrations/.gitkeep")

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["total_tasks"] == 1
    assert output["entries"][0]["target_files"] == [
        "Infra/Persistence/Migrations/.gitkeep"]
    assert not [w for w in output["warnings"] if w["code"] == "C002"]


def test_target_com_barra_final_vira_placeholder(tmp_path: Path):
    """`.../Migrations/` é como o agente de planning diz "crie a pasta"."""
    _write_feature(tmp_path, "001-infra", "G-INFRA", "T-INFRA-001",
                   "Infra/Persistence/Migrations/")

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["entries"][0]["target_files"] == [
        "Infra/Persistence/Migrations/.gitkeep"]
    assert [w["code"] for w in output["warnings"] if w["code"] == "C001"]


def test_shared_traceability_ids_do_not_create_spurious_edges(tmp_path: Path):
    _write_feature(tmp_path, "001-left", "G-LEFT", "T-LEFT-001", "Left/Item.cs")
    _write_feature(tmp_path, "002-right", "G-RIGHT", "T-RIGHT-001", "Right/Item.cs")

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["dependency_edges"] == []
    assert output["execution_waves"] == [["T-LEFT-001", "T-RIGHT-001"]]


def test_group_dependency_connects_predecessor_terminal_to_successor_root(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")
    _write_feature(tmp_path, "002-api", "G-API", "T-API-001", "Api/CartEndpoint.cs",
                   group_dependencies=["G-DOMAIN"])

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["entries"][1]["depends_on"] == ["T-DOMAIN-001"]
    assert output["dependency_edges"] == [{
        "from": "T-DOMAIN-001", "to": "T-API-001",
        "reason": "group_dependency", "source": "G-API depends_on G-DOMAIN",
    }]


def test_migration_wave_dependency_connects_wave_terminal_to_successor_root(tmp_path: Path):
    _write_feature(tmp_path, "001-catalog", "G-CATALOG", "T-CATALOG-001", "Catalog/Item.cs")
    _write_feature(tmp_path, "002-orders", "G-ORDERS", "T-ORDERS-001", "Orders/Order.cs")
    path = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "wave-spec-manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["features"][1]["depends_on"] = ["W0"]
    path.write_text(json.dumps(manifest), encoding="utf-8")

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["entries"][1]["depends_on"] == ["T-CATALOG-001"]
    assert output["dependency_edges"] == [{
        "from": "T-CATALOG-001", "to": "T-ORDERS-001",
        "reason": "migration_wave_dependency", "source": "W1 depends_on W0",
    }]


def test_same_file_create_precedes_update_across_features(tmp_path: Path):
    target = "Shared/DependencyInjection.cs"
    _write_feature(tmp_path, "001-base", "G-BASE", "T-BASE-001", target)
    _write_feature(tmp_path, "002-extension", "G-EXT", "T-EXT-001", target)
    extension = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "specs" / "002-extension"
    )
    plan = json.loads((extension / "plan-graph.json").read_text(encoding="utf-8"))
    fragment = json.loads((extension / "task-fragment.json").read_text(encoding="utf-8"))
    plan["files"][0]["action"] = "update"
    fragment["entries"][0]["action"] = "update"
    (extension / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")
    (extension / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["execution_order"] == ["T-BASE-001", "T-EXT-001"]
    assert output["dependency_edges"][0]["reason"] == "same_file"


def test_multiple_create_owners_for_same_file_are_reported_not_rejected(tmp_path: Path):
    """Regra invertida de propósito: ownership disputado NÃO descarta as tasks.

    Antes esta checagem levantava `CompilerError` no primeiro conflito. Medido em
    `cadastro-funcionarios-04`: 31 conflitos derrubavam 218 tasks íntegras, e a
    F3S entregava placeholder em vez de artefato. O conflito continua sendo
    reportado — em `ownership_conflicts`, nas entries e em compile-warnings.json —
    mas a consolidação segue. Ver tests/tools/test_speckit_best_effort.py.
    """
    target = "Shared/DependencyInjection.cs"
    _write_feature(tmp_path, "001-left", "G-LEFT", "T-LEFT-001", target)
    _write_feature(tmp_path, "002-right", "G-RIGHT", "T-RIGHT-001", target)

    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["total_tasks"] == 2, "task descartada por causa do conflito"
    conflitos = output["ownership_conflicts"]
    assert len(conflitos) == 1
    assert conflitos[0]["target_file"] == target
    assert sorted(conflitos[0]["task_ids"]) == ["T-LEFT-001", "T-RIGHT-001"]
    # Um único dono de criação; o outro vira update, marcado como CONFLICT.
    acoes = sorted(e["action"] for e in output["entries"])
    assert acoes == ["create", "update"]
    assert "CONFLICT" in {e["ownership_status"] for e in output["entries"]}


def test_windows_or_parent_traversal_paths_are_rejected(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")
    feature = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "specs" / "001-domain"
    )
    plan = json.loads((feature / "plan-graph.json").read_text(encoding="utf-8"))
    fragment = json.loads((feature / "task-fragment.json").read_text(encoding="utf-8"))
    plan["files"][0]["path"] = "../Domain/Cart.cs"
    fragment["entries"][0]["target_file"] = "../Domain/Cart.cs"
    (feature / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")
    (feature / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")

    with pytest.raises(compiler.CompilerError, match="path não normalizado"):
        compiler.compile_project("P", tmp_path, write=False)


def test_incomplete_fragment_is_rejected_before_output(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")
    feature = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "specs" / "001-domain"
    )
    fragment = json.loads((feature / "task-fragment.json").read_text(encoding="utf-8"))
    del fragment["entries"][0]["verify_command"]
    (feature / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")

    with pytest.raises(compiler.CompilerError, match="verify_command"):
        compiler.compile_project("P", tmp_path, write=True)

    assert not (feature.parent.parent / "traceability.json").exists()


def test_plan_file_without_task_is_reported_not_rejected(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")
    feature = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "specs" / "001-domain"
    )
    plan = json.loads((feature / "plan-graph.json").read_text(encoding="utf-8"))
    plan["files"].append({
        "path": "Domain/CartItem.cs", "action": "create", "group": "G-DOMAIN",
        "responsibility": "item", "source_refs": ["SPEC-DOMAIN-001"],
        "produces": [], "consumes": [],
    })
    (feature / "plan-graph.json").write_text(json.dumps(plan), encoding="utf-8")

    # Cobertura incompleta é lacuna de qualidade, não falha técnica: o arquivo
    # sem task vira aviso e as tasks que existem continuam sendo consolidadas.
    output = compiler.compile_project("P", tmp_path, write=False)

    assert output["total_tasks"] == 1
    assert any("arquivos do plano sem task" in w["message"]
               for w in output["warnings"]), "a lacuna sumiu do relatório"


def test_fragment_cannot_change_plan_integration_contract(tmp_path: Path):
    """O plano é a autoridade sobre `produces`; o fragment é reconciliado.

    Antes isto levantava CompilerError. Exigir que a LLM recopiasse verbatim uma
    tabela de 90-150 linhas era o mesmo modo de falha da ISSUE-004, então o campo
    passou a ser LIDO DO PLANO. O que muda aqui é só o canal: a divergência não
    some — ela é contabilizada em `reconciled_from_plan`.
    """
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs",
                   produces=["contract:cart"])
    feature = (
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
        / "specs" / "001-domain"
    )
    fragment = json.loads((feature / "task-fragment.json").read_text(encoding="utf-8"))
    fragment["entries"][0]["produces"] = ["contract:invented"]
    (feature / "task-fragment.json").write_text(json.dumps(fragment), encoding="utf-8")

    output = compiler.compile_project("P", tmp_path, write=False)

    assert any("T-DOMAIN-001.produces" in item
               for item in output["reconciled_from_plan"])
    # `contract:invented` não pode ter virado aresta nem consumo órfão: o token
    # do fragment foi descartado em favor do plano, não propagado.
    assert not any("contract:invented" in item
                   for item in output["orphan_consumes"])
    assert not [edge for edge in output["dependency_edges"]
                if edge["source"] == "contract:invented"]


def test_compile_writes_csv_export(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")

    compiler.compile_project("P", tmp_path)
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    csv_path = speckit / "traceability.csv"

    assert csv_path.exists()
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    text = csv_path.read_text(encoding="utf-8-sig")
    assert text.startswith("task_id,")
    assert "T-DOMAIN-001" in text
    assert "Domain/Cart.cs" in text


def test_export_csv_from_existing_traceability(tmp_path: Path):
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")
    compiler.compile_project("P", tmp_path)

    output = json.loads((
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit" / "traceability.json"
    ).read_text(encoding="utf-8"))
    target = tmp_path / "exports"
    written = compiler.export_traceability(output, target, formats=["csv"])

    assert "csv" in written
    assert (target / "traceability.csv").exists()


def test_export_xlsx_from_existing_traceability(tmp_path: Path):
    openpyxl = pytest.importorskip("openpyxl")
    _write_feature(tmp_path, "001-domain", "G-DOMAIN", "T-DOMAIN-001", "Domain/Cart.cs")
    compiler.compile_project("P", tmp_path)

    output = json.loads((
        tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit" / "traceability.json"
    ).read_text(encoding="utf-8"))
    target = tmp_path / "exports"
    written = compiler.export_traceability(output, target, formats=["xlsx"])

    assert "xlsx" in written
    wb = openpyxl.load_workbook(written["xlsx"])
    assert {"tasks", "dependencies", "execution_waves"}.issubset(wb.sheetnames)
    ws = wb["tasks"]
    header = [cell.value for cell in ws[1]]
    assert "task_id" in header
    assert any(row[header.index("task_id")].value == "T-DOMAIN-001" for row in ws.iter_rows(min_row=2))