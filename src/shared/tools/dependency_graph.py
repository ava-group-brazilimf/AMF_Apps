#!/usr/bin/env python3
"""Deterministic dependency graph for SpecKit tasks and pipeline waves."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}


@dataclass(frozen=True)
class GraphIssue:
    """One structural problem that prevents safe graph execution."""

    code: str
    message: str
    node_id: str | None = None
    dependency_id: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "dependency_id": self.dependency_id,
        }


class DependencyGraphError(ValueError):
    """Raised when a dependency graph cannot be executed safely."""

    def __init__(self, issues: Sequence[GraphIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in self.issues))


@dataclass(frozen=True)
class DependencyPlan:
    """Stable topological order and the graph used to derive it."""

    order: tuple[str, ...]
    waves: tuple[tuple[str, ...], ...]
    ranks: Mapping[str, int]
    predecessors: Mapping[str, tuple[str, ...]]
    successors: Mapping[str, tuple[str, ...]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "order": list(self.order),
            "waves": [list(wave) for wave in self.waves],
            "ranks": dict(self.ranks),
            "predecessors": {
                node_id: list(dependencies)
                for node_id, dependencies in self.predecessors.items()
            },
            "successors": {
                node_id: list(dependents)
                for node_id, dependents in self.successors.items()
            },
        }


def analyze(
    nodes: Sequence[Mapping[str, Any]],
    *,
    id_field: str = "task_id",
    dependencies_field: str = "depends_on",
) -> DependencyPlan:
    """Validate ``nodes`` and return a stable topological execution plan."""
    indexed, issues = _index_nodes(nodes, id_field, dependencies_field)
    if issues:
        raise DependencyGraphError(issues)

    sort_key = _sort_key_factory(indexed)
    predecessors = {
        node_id: tuple(sorted(_dependencies(node, dependencies_field), key=sort_key))
        for node_id, node in indexed.items()
    }
    successors_mutable: dict[str, list[str]] = {node_id: [] for node_id in indexed}
    for node_id, dependencies in predecessors.items():
        for dependency_id in dependencies:
            successors_mutable[dependency_id].append(node_id)
    successors = {
        node_id: tuple(sorted(dependents, key=sort_key))
        for node_id, dependents in successors_mutable.items()
    }

    remaining = {node_id: len(dependencies) for node_id, dependencies in predecessors.items()}
    ready = sorted(
        (node_id for node_id, count in remaining.items() if count == 0),
        key=sort_key,
    )
    waves: list[tuple[str, ...]] = []
    order: list[str] = []

    while ready:
        wave = tuple(ready)
        waves.append(wave)
        order.extend(wave)
        next_ready: list[str] = []
        for node_id in wave:
            for dependent_id in successors[node_id]:
                remaining[dependent_id] -= 1
                if remaining[dependent_id] == 0:
                    next_ready.append(dependent_id)
        ready = sorted(next_ready, key=sort_key)

    if len(order) != len(indexed):
        unresolved = {node_id for node_id, count in remaining.items() if count > 0}
        cycle = _find_cycle(predecessors, unresolved, sort_key)
        rendered = " -> ".join(cycle)
        raise DependencyGraphError((GraphIssue(
            code="cycle",
            message=f"dependency cycle detected: {rendered}",
            node_id=cycle[0] if cycle else None,
            dependency_id=cycle[1] if len(cycle) > 1 else None,
        ),))

    ranks = {
        node_id: rank
        for rank, wave in enumerate(waves)
        for node_id in wave
    }
    return DependencyPlan(
        order=tuple(order),
        waves=tuple(waves),
        ranks=ranks,
        predecessors=predecessors,
        successors=successors,
    )


def _index_nodes(
    nodes: Sequence[Mapping[str, Any]],
    id_field: str,
    dependencies_field: str,
) -> tuple[dict[str, Mapping[str, Any]], list[GraphIssue]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    issues: list[GraphIssue] = []

    for position, node in enumerate(nodes):
        raw_id = node.get(id_field)
        if not isinstance(raw_id, str) or not raw_id.strip():
            issues.append(GraphIssue(
                code="missing_id",
                message=f"node at position {position} has no valid {id_field}",
            ))
            continue
        node_id = raw_id.strip()
        if node_id in indexed:
            issues.append(GraphIssue(
                code="duplicate_id",
                message=f"duplicate node id: {node_id}",
                node_id=node_id,
            ))
            continue
        indexed[node_id] = node

    known_ids = set(indexed)
    for node_id, node in indexed.items():
        raw_dependencies = node.get(dependencies_field, [])
        if raw_dependencies is None:
            raw_dependencies = []
        if not isinstance(raw_dependencies, list):
            issues.append(GraphIssue(
                code="invalid_dependencies",
                message=f"{node_id}.{dependencies_field} must be an array",
                node_id=node_id,
            ))
            continue

        seen: set[str] = set()
        for dependency in raw_dependencies:
            if not isinstance(dependency, str) or not dependency.strip():
                issues.append(GraphIssue(
                    code="invalid_dependency_id",
                    message=f"{node_id} has an invalid dependency id",
                    node_id=node_id,
                ))
                continue
            dependency_id = dependency.strip()
            if dependency_id in seen:
                issues.append(GraphIssue(
                    code="duplicate_dependency",
                    message=f"{node_id} repeats dependency {dependency_id}",
                    node_id=node_id,
                    dependency_id=dependency_id,
                ))
                continue
            seen.add(dependency_id)
            if dependency_id == node_id:
                issues.append(GraphIssue(
                    code="self_dependency",
                    message=f"{node_id} depends on itself",
                    node_id=node_id,
                    dependency_id=dependency_id,
                ))
            elif dependency_id not in known_ids:
                issues.append(GraphIssue(
                    code="missing_dependency",
                    message=f"{node_id} depends on unknown node {dependency_id}",
                    node_id=node_id,
                    dependency_id=dependency_id,
                ))

    return indexed, issues


def _dependencies(node: Mapping[str, Any], field: str) -> list[str]:
    return [str(item).strip() for item in (node.get(field) or [])]


def _sort_key_factory(indexed: Mapping[str, Mapping[str, Any]]):
    def sort_key(node_id: str) -> tuple[int, str, str]:
        node = indexed[node_id]
        priority = str(node.get("priority") or "P2")
        group = str(node.get("group") or "")
        return (_PRIORITY_ORDER.get(priority, _PRIORITY_ORDER["P2"]), group, node_id)

    return sort_key


def _find_cycle(
    predecessors: Mapping[str, tuple[str, ...]],
    unresolved: set[str],
    sort_key,
) -> tuple[str, ...]:
    state: dict[str, int] = {}
    stack: list[str] = []
    positions: dict[str, int] = {}

    def visit(node_id: str) -> tuple[str, ...] | None:
        state[node_id] = 1
        positions[node_id] = len(stack)
        stack.append(node_id)

        for dependency_id in sorted(predecessors[node_id], key=sort_key):
            if dependency_id not in unresolved:
                continue
            dependency_state = state.get(dependency_id, 0)
            if dependency_state == 0:
                cycle = visit(dependency_id)
                if cycle:
                    return cycle
            elif dependency_state == 1:
                start = positions[dependency_id]
                return tuple(stack[start:] + [dependency_id])

        stack.pop()
        positions.pop(node_id, None)
        state[node_id] = 2
        return None

    for node_id in sorted(unresolved, key=sort_key):
        if state.get(node_id, 0) == 0:
            cycle = visit(node_id)
            if cycle:
                return cycle
    return ()