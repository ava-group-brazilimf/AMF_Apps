"""Tests for the deterministic SpecKit dependency graph."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dependency_graph  # noqa: E402


def _node(
    task_id: str,
    dependencies: list[str] | None = None,
    *,
    priority: str = "P2",
    group: str = "G-A",
) -> dict:
    return {
        "task_id": task_id,
        "depends_on": dependencies or [],
        "priority": priority,
        "group": group,
    }


def test_chain_is_ordered_before_its_dependents():
    plan = dependency_graph.analyze([
        _node("T-A-003", ["T-A-002"]),
        _node("T-A-001"),
        _node("T-A-002", ["T-A-001"]),
    ])

    assert plan.order == ("T-A-001", "T-A-002", "T-A-003")
    assert plan.waves == (("T-A-001",), ("T-A-002",), ("T-A-003",))
    assert plan.ranks == {"T-A-001": 0, "T-A-002": 1, "T-A-003": 2}


def test_branch_and_join_share_execution_waves():
    plan = dependency_graph.analyze([
        _node("T-JOIN-001", ["T-LEFT-001", "T-RIGHT-001"]),
        _node("T-RIGHT-001", ["T-ROOT-001"]),
        _node("T-LEFT-001", ["T-ROOT-001"]),
        _node("T-ROOT-001"),
    ])

    assert plan.waves == (
        ("T-ROOT-001",),
        ("T-LEFT-001", "T-RIGHT-001"),
        ("T-JOIN-001",),
    )


def test_ready_nodes_use_priority_group_and_id_as_stable_tie_breakers():
    plan = dependency_graph.analyze([
        _node("T-Z-001", priority="P2", group="G-Z"),
        _node("T-B-001", priority="P1", group="G-B"),
        _node("T-A-002", priority="P1", group="G-A"),
        _node("T-A-001", priority="P1", group="G-A"),
    ])

    assert plan.order == ("T-A-001", "T-A-002", "T-B-001", "T-Z-001")


@pytest.mark.parametrize(
    ("nodes", "code"),
    [
        ([_node("T-A-001"), _node("T-A-001")], "duplicate_id"),
        ([_node("T-A-001", ["T-MISSING-001"])], "missing_dependency"),
        ([_node("T-A-001", ["T-A-001"])], "self_dependency"),
        ([_node("T-A-001", ["T-B-001", "T-B-001"]), _node("T-B-001")],
         "duplicate_dependency"),
    ],
)
def test_invalid_references_are_rejected(nodes: list[dict], code: str):
    with pytest.raises(dependency_graph.DependencyGraphError) as exc:
        dependency_graph.analyze(nodes)

    assert code in {issue.code for issue in exc.value.issues}


def test_cycle_reports_a_reproducible_path():
    with pytest.raises(dependency_graph.DependencyGraphError) as exc:
        dependency_graph.analyze([
            _node("T-A-001", ["T-B-001"]),
            _node("T-B-001", ["T-C-001"]),
            _node("T-C-001", ["T-A-001"]),
        ])

    issue = exc.value.issues[0]
    assert issue.code == "cycle"
    assert issue.message == (
        "dependency cycle detected: T-A-001 -> T-B-001 -> T-C-001 -> T-A-001"
    )


def test_custom_fields_support_pipeline_wave_graphs():
    plan = dependency_graph.analyze([
        {"id": "wave2", "requires": ["wave1"]},
        {"id": "wave1", "requires": []},
    ], id_field="id", dependencies_field="requires")

    assert plan.order == ("wave1", "wave2")