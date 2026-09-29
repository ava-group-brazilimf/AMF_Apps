"""Tests for f4s_scaffold_injector — deterministic scaffold spec generation."""
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

import f4s_scaffold_injector as injector  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_project(tmp_path: Path, *, backend: str, frontend: str | None = None,
                  trace_id: str = "trace-test", project_name: str = "P") -> Path:
    config = {
        "project_name": project_name,
        "trace_id": trace_id,
        "tobe_stack": {"backend_framework": backend},
    }
    if frontend:
        config["tobe_stack"]["frontend_framework"] = frontend
    project_root = tmp_path / "projects" / project_name
    _write(project_root / "context" / "project-config.yaml",
           json.dumps(config, ensure_ascii=False))
    speckit = project_root / "outputs" / "tobe" / "speckit"
    foundation = speckit / "specs" / "001-w0-foundation"
    _write(speckit / "wave-spec-manifest.json", json.dumps({
        "schema_version": "1.0.0", "project": project_name,
        "trace_id": trace_id,
        "features": [{
            "feature": "001-w0-foundation", "wave_id": "W0",
            "wave_type": "foundation", "migration_wave_order": 0,
            "codegen": True, "depends_on": [],
        }],
    }))
    _write(foundation / "spec.md", "# Foundation\n")
    _write(foundation / "plan.md", "# Foundation Plan\n")
    _write(foundation / "plan-graph.json", json.dumps({
        "schema_version": "3.0.0", "project": project_name, "trace_id": trace_id,
        "feature": "001-w0-foundation", "spec_id": "SPEC-W0",
        "plan_id": "PLAN-W0", "migration_wave_id": "W0",
        "migration_wave_order": 0, "groups": [], "files": [],
    }))
    _write(foundation / "task-fragment.json", json.dumps({
        "schema_version": "3.0.0", "project": project_name, "trace_id": trace_id,
        "feature": "001-w0-foundation", "spec_id": "SPEC-W0",
        "plan_id": "PLAN-W0", "migration_wave_id": "W0",
        "migration_wave_order": 0, "entries": [],
    }))
    return tmp_path


def test_injector_creates_scaffold_spec_for_backend(tmp_path: Path):
    root = _make_project(tmp_path, backend="dotnet")

    generated = injector.inject_scaffold_specs("P", repo_root=root)

    assert len(generated) == 1
    assert generated[0]["stack"] == "dotnet"
    feature_dir = root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "specs" / "001-w0-foundation"
    assert (feature_dir / "plan-graph.json").exists()
    assert (feature_dir / "task-fragment.json").exists()
    assert (feature_dir / "spec.md").exists()


def test_injector_creates_scaffold_for_backend_and_frontend(tmp_path: Path):
    root = _make_project(tmp_path, backend="fastapi", frontend="angular")

    generated = injector.inject_scaffold_specs("P", repo_root=root)

    stacks = {g["stack"] for g in generated}
    assert stacks == {"fastapi", "angular"}


def test_scaffold_task_is_first_in_stack(tmp_path: Path):
    root = _make_project(tmp_path, backend="dotnet")
    injector.inject_scaffold_specs("P", repo_root=root)

    foundation = root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "specs" / "001-w0-foundation"
    plan = json.loads((foundation / "plan-graph.json").read_text(encoding="utf-8"))
    fragment = json.loads((foundation / "task-fragment.json").read_text(encoding="utf-8"))

    assert plan["schema_version"] == "3.0.0"
    assert plan["feature"] == "001-w0-foundation"
    assert plan["migration_wave_id"] == "W0"
    assert plan["migration_wave_order"] == 0
    assert plan["files"][0]["task_type"] == "backend"
    assert fragment["schema_version"] == "3.0.0"
    assert fragment["entries"][0]["target_stack"] == "dotnet"
    assert fragment["entries"][0]["task_type"] == "backend"
    assert "artifact:scaffold:backend" in fragment["entries"][0]["produces"]


def test_scaffold_ids_are_upper_case_and_schema_valid(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    root = _make_project(tmp_path, backend="dotnet", frontend="angular")
    injector.inject_scaffold_specs("P", repo_root=root)

    plan_schema = json.loads((REPO_ROOT / "src" / "shared" / "schemas" / "speckit-plan-graph.schema.json").read_text(encoding="utf-8"))
    fragment_schema = json.loads((REPO_ROOT / "src" / "shared" / "schemas" / "speckit-task-fragment.schema.json").read_text(encoding="utf-8"))

    feature_dir = root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "specs" / "001-w0-foundation"
    plan = json.loads((feature_dir / "plan-graph.json").read_text(encoding="utf-8"))
    fragment = json.loads((feature_dir / "task-fragment.json").read_text(encoding="utf-8"))
    jsonschema.validate(plan, plan_schema)
    jsonschema.validate(fragment, fragment_schema)
    assert {g["group"] for g in plan["groups"]} == {
        "G-SCAFFOLD-BACKEND", "G-SCAFFOLD-FRONTEND",
    }
    assert {e["task_id"] for e in fragment["entries"]} == {
        "T-SCAFFOLD-BACKEND-001", "T-SCAFFOLD-FRONTEND-001",
    }


def test_compiler_adds_scaffold_edges(tmp_path: Path):
    import speckit_task_compiler as compiler  # noqa: PLC0415,E402

    root = _make_project(tmp_path, backend="dotnet")
    injector.inject_scaffold_specs("P", repo_root=root)
    manifest_path = root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "wave-spec-manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["features"].append({
        "feature": "002-w1-domain", "wave_id": "W1",
        "migration_wave_order": 1, "codegen": True, "depends_on": ["W0"],
    })
    _write(manifest_path, json.dumps(manifest_data, ensure_ascii=False))
    _write(root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "specs" / "002-w1-domain" / "plan-graph.json",
           json.dumps({
               "schema_version": "3.0.0", "project": "P", "trace_id": "trace-test",
               "feature": "002-w1-domain", "spec_id": "SPEC-D", "plan_id": "PLAN-D",
               "migration_wave_id": "W1", "migration_wave_order": 1,
               "groups": [{"group": "G-D", "target_stack": "dotnet", "scope": "d",
                           "depends_on": [], "verify_command": "dotnet build"}],
               "files": [{"path": "Domain/Cart.cs", "action": "create", "group": "G-D",
                          "task_type": "backend", "responsibility": "d",
                          "source_refs": [{"artifact": "a.md", "anchor": "A"}],
                          "produces": [], "consumes": []}],
           }))
    _write(root / "projects" / "P" / "outputs" / "tobe" / "speckit" / "specs" / "002-w1-domain" / "task-fragment.json",
           json.dumps({
               "schema_version": "3.0.0", "project": "P", "trace_id": "trace-test",
               "feature": "002-w1-domain", "spec_id": "SPEC-D", "plan_id": "PLAN-D",
               "migration_wave_id": "W1", "migration_wave_order": 1,
               "entries": [{
                   "task_id": "T-D-001", "title": "Domain", "group": "G-D",
                   "task_type": "backend", "target_stack": "dotnet",
                   "source_refs": [{"artifact": "a.md", "anchor": "A"}],
                   "target_file": "Domain/Cart.cs",
                   "action": "create", "depends_on": [], "depends_on_groups": [],
                   "produces": [], "consumes": [],
                   "acceptance": ["ok"], "verify_command": "dotnet build",
                   "priority": "P2", "story_points": 1,
               }],
           }))

    output = compiler.compile_project("P", root, write=False)
    entry = next(e for e in output["entries"] if e["task_id"] == "T-D-001")
    scaffold_id = "T-SCAFFOLD-BACKEND-001"
    assert scaffold_id in entry["depends_on"]


def test_scaffold_edge_applies_inside_foundation_feature():
    import speckit_task_compiler as compiler  # noqa: PLC0415,E402

    calls = []
    tasks = [
        {"feature": "001-w0-foundation", "task_id": "T-SCAFFOLD-BACKEND-001",
         "target_stack": "dotnet", "produces": ["artifact:scaffold:backend"]},
        {"feature": "001-w0-foundation", "task_id": "T-W0-SHARED-001",
         "target_stack": "dotnet", "produces": []},
    ]

    compiler._add_scaffold_edges(
        tasks, {}, lambda predecessor, successor, reason, source:
        calls.append((predecessor, successor, reason, source)),
    )

    assert calls == [
        ("T-SCAFFOLD-BACKEND-001", "T-W0-SHARED-001",
         "scaffold_dependency", "depends on scaffold for dotnet"),
    ]


def test_injector_respects_project_name_override(tmp_path: Path):
    _make_project(tmp_path, backend="dotnet", project_name="ConfiguredName")
    config = {"project_name": "ConfiguredName", "tobe_stack": {"backend_framework": "dotnet"}}
    # Also create legacy P project dir to ensure injector uses config value
    _write(tmp_path / "projects" / "P" / "context" / "project-config.yaml",
           json.dumps(config, ensure_ascii=False))

    generated = injector.inject_scaffold_specs("P", repo_root=tmp_path)

    feature_path = Path(generated[0]["feature_dir"]).as_posix()
    assert feature_path.startswith("projects/ConfiguredName")
