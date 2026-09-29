"""Contract tests for the deterministic SpecKit wave manifest builder."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import speckit_wave_manifest as manifest  # noqa: E402


def _write_project(root: Path, *, include_model: bool = True) -> Path:
    project = root / "projects" / "P"
    outputs = project / "outputs"
    (outputs / "tobe" / "migration").mkdir(parents=True)
    (outputs / "tobe" / "docs" / "openapi").mkdir(parents=True)
    (outputs / "tobe" / "qa").mkdir(parents=True)
    (outputs / "tobe" / "prototype").mkdir(parents=True)
    (outputs / "asis" / "docs").mkdir(parents=True)

    if include_model:
        model = {
            "schema_version": "1.0.0",
            "project": "P",
            "trace_id": "trace-wave",
            "waves": [
                {
                    "wave_id": "W0", "wave_name": "Foundation",
                    "wave_type": "foundation", "description": "Base platform",
                    "bounded_contexts": [{"bc_id": "BC-10", "bc_name": "Infrastructure"}],
                    "dependencies": [], "acceptance_criteria": ["Platform ready"],
                },
                {
                    "wave_id": "W1", "wave_name": "Core Orders",
                    "wave_type": "domain_core", "description": "Orders vertical slice",
                    "bounded_contexts": [{"bc_id": "BC-02", "bc_name": "Orders"}],
                    "dependencies": ["W0"], "acceptance_criteria": ["Checkout works"],
                },
            ],
        }
        (outputs / "tobe" / "migration" / "wave-model.json").write_text(
            json.dumps(model), encoding="utf-8"
        )

    (outputs / "tobe" / "docs" / "wave-plan.md").write_text(
        "# Wave Plan\n\n## W0 — Foundation\n\n### Scope\n- Platform\n\n"
        "## W1 — Core Orders\n\n### Scope\n- BC-02 Orders\n",
        encoding="utf-8",
    )
    (outputs / "tobe" / "docs" / "backlog-tobe.md").write_text(
        "## BC-02: Orders\n\n| ID | Story | Trace |\n|---|---|---|\n"
        "| US-ORD-001 | Checkout | FR-ORD-001, BR-CHECKOUT-001 |\n",
        encoding="utf-8",
    )
    (outputs / "tobe" / "qa" / "test-cases.md").write_text(
        "## BC-02: Orders\n\n### TC-ORD-001: Place order\n"
        "**Traceability**: FR-ORD-001, BR-CHECKOUT-001\n",
        encoding="utf-8",
    )
    (outputs / "asis" / "docs" / "business-rules.md").write_text(
        "### Module: Orders\n\n**FR-ORD-001**: Checkout.\n\n"
        "### BR-CHECKOUT-001: Validate checkout\n",
        encoding="utf-8",
    )
    (outputs / "tobe" / "docs" / "openapi" / "orders.yaml").write_text(
        "openapi: 3.1.0\ninfo:\n  title: Orders\n  x-source-bc: BC-02\n"
        "paths:\n  /orders:\n    post:\n      operationId: PlaceOrder\n",
        encoding="utf-8",
    )
    (outputs / "tobe" / "docs" / "api-map.md").write_text(
        "| Flow | Component | Method | Path | BC |\n|---|---|---|---|---|\n"
        "| Checkout | CheckoutPage | POST | /api/v1/orders | BC-02 |\n",
        encoding="utf-8",
    )
    (outputs / "tobe" / "prototype" / "screen-list.md").write_text(
        "| Screen | Bounded Context | API Endpoint | Status |\n|---|---|---|---|\n"
        "| Checkout | Orders | POST /api/v1/orders | included |\n",
        encoding="utf-8",
    )
    return project


def test_manifest_creates_one_vertical_feature_per_wave(tmp_path: Path):
    _write_project(tmp_path)

    output = manifest.build_manifest("P", tmp_path)

    assert [item["wave_id"] for item in output["features"]] == ["W0", "W1"]
    assert [item["feature"] for item in output["features"]] == [
        "001-w0-foundation", "002-w1-core-orders",
    ]
    assert output["features"][0]["codegen"] is True
    orders = output["features"][1]
    assert orders["depends_on"] == ["W0"]
    assert orders["bounded_contexts"] == [
        {"bc_id": "BC-02", "bc_name": "Orders"},
    ]
    assert orders["codegen"] is True


def test_wave_slice_combines_api_rules_tests_backlog_and_prototype(tmp_path: Path):
    _write_project(tmp_path)

    output = manifest.build_manifest("P", tmp_path)
    orders = output["features"][1]
    sources = {source["source_id"]: source for source in orders["sources"]}

    assert sources["business-rules"]["anchors"] == ["BR-CHECKOUT-001", "FR-ORD-001"]
    assert sources["api"]["anchors"] == ["PlaceOrder"]
    assert sources["backlog"]["anchors"] == ["US-ORD-001"]
    assert sources["test-cases"]["anchors"] == ["TC-ORD-001"]
    assert sources["prototype"]["anchors"] == ["Checkout"]


def test_wave_plan_is_fallback_when_model_is_missing(tmp_path: Path):
    _write_project(tmp_path, include_model=False)

    output = manifest.build_manifest("P", tmp_path)

    assert output["wave_source"] == "outputs/tobe/docs/wave-plan.md"
    assert [item["wave_id"] for item in output["features"]] == ["W0", "W1"]
    assert output["warnings"]


def test_model_project_mismatch_is_a_hard_failure(tmp_path: Path):
    project = _write_project(tmp_path)
    path = project / "outputs" / "tobe" / "migration" / "wave-model.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["project"] = "OTHER"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(manifest.ManifestError, match="project"):
        manifest.build_manifest("P", tmp_path)


def test_canonical_v2_wave_model_fields_are_normalized(tmp_path: Path):
    project = _write_project(tmp_path)
    path = project / "outputs" / "tobe" / "migration" / "wave-model.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    canonical_waves = []
    for index, wave in enumerate(data["waves"]):
        canonical_waves.append({
            "wave_number": index,
            "wave_name": f"W{index} — {wave['wave_name']}",
            "wave_type": wave["wave_type"],
            "scope_description": wave["description"],
            "bounded_contexts": wave["bounded_contexts"],
            "depends_on_waves": [int(item.removeprefix("W")) for item in wave["dependencies"]],
            "acceptance_criteria": wave["acceptance_criteria"],
        })
    path.write_text(json.dumps({
        "$version": "2.0.0",
        "metadata": {"project_name": "P", "trace_id": "trace-wave"},
        "waves": canonical_waves,
    }), encoding="utf-8")

    output = manifest.build_manifest("P", tmp_path)

    assert [item["wave_id"] for item in output["features"]] == ["W0", "W1"]
    assert output["features"][1]["feature"] == "002-w1-core-orders"
    assert output["features"][1]["depends_on"] == ["W0"]
    assert output["features"][1]["description"] == "Orders vertical slice"


def test_legacy_string_contexts_are_resolved_from_bc_details(tmp_path: Path):
    project = _write_project(tmp_path)
    path = project / "outputs" / "tobe" / "migration" / "wave-model.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["waves"][1]["bounded_contexts"] = ["BC-02"]
    data["waves"][1]["bc_details"] = [
        {"bc_id": "BC-02", "bc_name": "Orders"},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")

    output = manifest.build_manifest("P", tmp_path)

    assert output["features"][1]["bounded_contexts"] == [
        {"bc_id": "BC-02", "bc_name": "Orders"},
    ]


def test_non_object_wave_reports_manifest_error_instead_of_attribute_error(tmp_path: Path):
    project = _write_project(tmp_path)
    path = project / "outputs" / "tobe" / "migration" / "wave-model.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["waves"] = ["W1"]
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(manifest.ManifestError, match=r"waves\[0\].*objeto"):
        manifest.build_manifest("P", tmp_path)


def test_generated_manifest_conforms_to_schema(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    _write_project(tmp_path)
    output = manifest.build_manifest("P", tmp_path)
    schema = json.loads((
        REPO_ROOT / "src" / "shared" / "schemas" / "speckit-wave-manifest.schema.json"
    ).read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator(schema).validate(output)


def test_cross_reference_in_prose_is_not_read_as_wave_composition(tmp_path: Path):
    project = _write_project(tmp_path)
    (project / "outputs" / "tobe" / "docs" / "wave-plan.md").write_text(
        "# Wave Plan\n\n## W0 — Foundation (BC-10)\n\n### Scope\n"
        "- **BC-10 Infrastructure**: base platform\n\n"
        "## W1 — Core Orders (BC-02)\n\n### 1. Visão Geral\n"
        "BC-10 é pré-requisito e BC-99 depende desta wave.\n\n"
        "### 2. Escopo\n- **BC-02 Orders**: checkout\n\n"
        "### 6. Dependências\n- W0 concluída (BC-10 disponível)\n",
        encoding="utf-8",
    )

    output = manifest.build_manifest("P", tmp_path)

    assert [item["bc_id"] for item in output["features"][1]["bounded_contexts"]] == ["BC-02"]


def test_trailing_sections_do_not_leak_bcs_into_the_last_wave(tmp_path: Path):
    project = _write_project(tmp_path)
    (project / "outputs" / "tobe" / "docs" / "wave-plan.md").write_text(
        "# Wave Plan\n\n## W0 — Foundation\n\n### Scope\n- **BC-10 Infrastructure**\n\n"
        "## W1 — Core Orders\n\n### Scope\n- **BC-02 Orders**\n\n"
        "## Mapa de Dependências\n\n```mermaid\nflowchart LR\n"
        "    BC10[BC-10 Infrastructure] --> BC02[BC-02 Orders]\n"
        "    BC02 --> BC77[BC-77 Billing]\n```\n",
        encoding="utf-8",
    )

    output = manifest.build_manifest("P", tmp_path)

    assert [item["bc_id"] for item in output["features"][1]["bounded_contexts"]] == ["BC-02"]


def test_real_bc_divergence_between_plan_and_model_still_aborts(tmp_path: Path):
    project = _write_project(tmp_path)
    (project / "outputs" / "tobe" / "docs" / "wave-plan.md").write_text(
        "# Wave Plan\n\n## W0 — Foundation\n\n### Scope\n- **BC-10 Infrastructure**\n\n"
        "## W1 — Core Orders\n\n### Scope\n- **BC-02 Orders**\n- **BC-03 Billing**\n",
        encoding="utf-8",
    )

    with pytest.raises(manifest.ManifestError, match="BC-03"):
        manifest.build_manifest("P", tmp_path)


def test_formal_anchor_without_wave_is_a_structured_warning(tmp_path: Path):
    """Âncora formal sem wave AVISA; não aborta.

    Este teste exigia `ManifestError` e já falhava antes da camada de protótipo:
    o `raise` virou `warnings.append` quando a POLÍTICA DE ERRO do `F3S.yaml`
    passou a valer também para o manifesto ("erro NÃO trava fase"). Uma regra de
    negócio transversal, que legitimamente não pertence a nenhuma wave, derrubava
    a F3S inteira — e a fase não produzia artefato nenhum.

    O que o contrato exige hoje, e o que este teste trava: o achado continua
    existindo, nomeado e com a âncora, em `warnings[]`.
    """
    project = _write_project(tmp_path)
    rules = project / "outputs" / "asis" / "docs" / "business-rules.md"
    rules.write_text(
        rules.read_text(encoding="utf-8") + "\n### BR-ORPHAN-001: Unassigned\n",
        encoding="utf-8",
    )

    result = manifest.build_manifest("P", tmp_path)
    assert any("BR-ORPHAN-001" in warning for warning in result["warnings"])
    assert result["features"], "a fase continua produzindo o manifesto"