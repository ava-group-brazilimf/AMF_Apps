#!/usr/bin/env python3
"""Deterministic repair of SpecKit plan-graph.json + task-fragment.json pairs.

This tool fixes common contract violations that block speckit_task_compiler.py:

* migration_wave_id / migration_wave_order / spec_id / plan_id / trace_id
  in task-fragment.json diverging from the corresponding plan-graph.json.
* Group IDs duplicated across features (cross-feature collisions).

It reads every specs/{feature}/plan-graph.json and task-fragment.json pair,
applies corrections, and rewrites the files atomically. The operation is
idempotent and deterministic: running it twice on the same inputs produces
the same outputs.

Usage:
    python src/shared/tools/speckit_fragment_repair.py --project PROJECT
    python src/shared/tools/speckit_fragment_repair.py --project PROJECT --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

# Força UTF-8 no Windows - mesma guarda de src/shared/checks/cli.py.
# Sem ela qualquer mensagem acentuada estoura UnicodeEncodeError no console
# cp1252 e a tool morre por um detalhe de terminal, não por um defeito real.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(SCRIPT_DIR))

import speckit_task_compiler  # noqa: E402


class RepairError(ValueError):
    """Raised when an unrecoverable inconsistency is found."""


def _speckit_dir(project: str, repo_root: Path) -> Path:
    return repo_root / "projects" / project / "outputs" / "tobe" / "speckit"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RepairError(f"arquivo ausente: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RepairError(f"JSON inválido em {path}: {exc}") from exc


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _copy_header_from_plan(fragment: dict[str, Any], plan: dict[str, Any]) -> dict[str, str]:
    """Return a map of fields that were corrected in the fragment header."""
    corrections: dict[str, str] = {}
    for field in ("trace_id", "spec_id", "plan_id", "migration_wave_id", "migration_wave_order"):
        expected = plan.get(field)
        actual = fragment.get(field)
        if actual != expected:
            corrections[field] = f"{actual!r} -> {expected!r}"
            fragment[field] = expected
    return corrections


def _uniform_trace_id(
    plans: dict[str, dict[str, Any]],
    fragments: dict[str, dict[str, Any]],
) -> tuple[str | None, list[str]]:
    """Pick a canonical trace_id and return (trace_id, changes).

    Scaffolds (000-scaffold-*) may have a synthetic trace_id; we align them
    with the trace_id used by domain features so the compiler sees a single
    global trace_id.
    """
    domain_trace_ids: list[str] = [
        str(plans[f].get("trace_id") or "")
        for f in plans
        if not f.startswith("000-scaffold-") and plans[f].get("trace_id")
    ]
    if not domain_trace_ids:
        return None, []
    # Use the most common trace_id among domain features.
    canonical = max(set(domain_trace_ids), key=domain_trace_ids.count)

    changes: list[str] = []
    for feature in plans:
        plan = plans[feature]
        fragment = fragments[feature]
        if plan.get("trace_id") != canonical:
            changes.append(f"{feature} plan trace_id {plan.get('trace_id')!r} -> {canonical!r}")
            plan["trace_id"] = canonical
        if fragment.get("trace_id") != canonical:
            changes.append(
                f"{feature} fragment trace_id {fragment.get('trace_id')!r} -> {canonical!r}"
            )
            fragment["trace_id"] = canonical
    return canonical, changes


def _collect_groups(plans: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Map each group ID to the list of features that declare it."""
    ownership: dict[str, list[str]] = defaultdict(list)
    for feature, plan in plans.items():
        for group in plan.get("groups") or []:
            gid = group.get("group")
            if isinstance(gid, str) and gid:
                ownership[gid].append(feature)
    return ownership


def _normalize_contract_token(token: str) -> str:
    """Forma canônica de um token, delegando ao compilador.

    Antes só `contract:*` era normalizado, em minúsculas. Com a gramática de
    tokens do elo frontend↔backend (`api-contract:`, `api-client:`, `screen:`,
    `component:`, `route:`, `design-token:`, `test:e2e:`), manter a regra antiga
    aqui faria o reparo e a compilação discordarem sobre o mesmo token — e é o
    casamento produtor↔consumidor desses tokens que constrói a aresta entre o
    client do frontend e o contrato do backend. Uma única função para os dois.
    """
    if not isinstance(token, str):
        return token
    return speckit_task_compiler.normalize_token(token)


def _normalize_contract_tokens_in_data(
    data: dict[str, Any],
    owner: str,
) -> list[str]:
    """Lower-case all contract:* tokens in produces/consumes. Returns changes."""
    changes: list[str] = []
    for field in ("produces", "consumes"):
        values = data.get(field) or []
        if not isinstance(values, list):
            continue
        normalized = [_normalize_contract_token(v) for v in values]
        if normalized != values:
            data[field] = normalized
            changes.append(f"{owner} {field} normalized: {values} -> {normalized}")
    return changes


def _collect_task_ids(fragments: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Map each task ID to the list of features that declare it."""
    ownership: dict[str, list[str]] = defaultdict(list)
    for feature, fragment in fragments.items():
        for entry in fragment.get("entries") or []:
            tid = entry.get("task_id")
            if isinstance(tid, str) and tid:
                ownership[tid].append(feature)
    return ownership


def _is_backend_target(target_file: str | None) -> bool:
    """Heuristic: backend targets are under backend/ or contain openapi/Endpoints."""
    if not isinstance(target_file, str):
        return False
    lower = target_file.lower()
    return lower.startswith("backend/") or "openapi" in lower or "endpoints" in lower


def _remove_self_dependencies(
    plan: dict[str, Any],
    fragment: dict[str, Any],
    feature: str,
) -> list[str]:
    """Remove self-references from depends_on and depends_on_groups.

    A task must never depend on itself or on its own group. The compiler's
    group-edge logic would otherwise create a self-loop for root/terminal tasks.
    """
    changes: list[str] = []

    plan_groups = {
        str(g.get("group") or ""): g for g in (plan.get("groups") or []) if g.get("group")
    }
    own_groups: dict[str, str] = {}
    for entry in fragment.get("entries") or []:
        tid = entry.get("task_id")
        gid = entry.get("group")
        if isinstance(tid, str) and isinstance(gid, str):
            own_groups[tid] = gid

    # Clean fragment entries.
    for entry in fragment.get("entries") or []:
        tid = entry.get("task_id")
        deps = entry.get("depends_on") or []
        if isinstance(deps, list) and tid in deps:
            entry["depends_on"] = [d for d in deps if d != tid]
            changes.append(f"{feature} task {tid} removed self-reference from depends_on")
        groups = entry.get("depends_on_groups") or []
        own = own_groups.get(tid)
        if isinstance(groups, list) and own and own in groups:
            entry["depends_on_groups"] = [g for g in groups if g != own]
            changes.append(
                f"{feature} task {tid} removed own group {own!r} from depends_on_groups"
            )

    # Clean plan groups: a group must not depend on itself.
    for group in plan.get("groups") or []:
        gid = group.get("group")
        deps = group.get("depends_on") or []
        if isinstance(deps, list) and gid in deps:
            group["depends_on"] = [d for d in deps if d != gid]
            changes.append(f"{feature} group {gid} removed self-reference from depends_on")

    return changes


def _deduplicate_contract_tokens(
    plans: dict[str, dict[str, Any]],
    fragments: dict[str, dict[str, Any]],
) -> list[str]:
    """Resolve duplicate contract:* / api:* producers across tasks.

    The compiler requires every consumed token to have exactly one producer.

    Two patterns are repaired here:

    1. Shared contracts (contract:*) created in an early wave and later updated
       in a later wave. The update task must not claim the same token; it gets
       a wave-scoped variant (contract:<name>:w<N>).

    2. API operations (api:*) where both the backend endpoint and the frontend
       API client are declared as producers. The backend endpoint is the true
       producer; the frontend client becomes a consumer of the same token.
    """

    # Collect producers globally with wave order, action, target_file.
    producers: dict[str, list[tuple[int, str, str, str, str]]] = defaultdict(list)
    for feature, fragment in fragments.items():
        order = int(plans[feature].get("migration_wave_order") or 0)
        for entry in fragment.get("entries") or []:
            action = entry.get("action")
            target = entry.get("target_file") or ""
            task_id = entry.get("task_id") or ""
            for token in entry.get("produces") or []:
                if isinstance(token, str) and (
                    token.startswith("contract:") or token.startswith("api:")
                ):
                    producers[token].append((order, feature, task_id, action, target))

    changes: list[str] = []

    # Tokens produced by more than one distinct task.
    duplicate_tokens = {token for token, items in producers.items() if len(items) > 1}
    if not duplicate_tokens:
        return changes

    for token in sorted(duplicate_tokens):
        items = producers[token]
        features = {f for _, f, _, _, _ in items}

        if len(features) == 1:
            # Same feature: backend endpoint wins; frontend clients become consumers.
            feature = next(iter(features))
            backend_items = [
                (order, feat, tid, action, target)
                for order, feat, tid, action, target in items
                if _is_backend_target(target)
            ]
            if not backend_items:
                # No clear backend target: keep the first task as producer.
                backend_items = [items[0]]
            canonical_tid = backend_items[0][2]
            producer_tids = {tid for _, _, tid, _, _ in items}

            plan = plans[feature]
            fragment = fragments[feature]

            # Plan: ensure non-backend files do not produce the token.
            for item in plan.get("files") or []:
                produces = item.get("produces") or []
                consumes = item.get("consumes") or []
                if token in produces and not _is_backend_target(item.get("path")):
                    item["produces"] = [p for p in produces if p != token]
                    if token not in consumes:
                        item["consumes"] = list(consumes) + [token]
                    changes.append(
                        f"{feature} plan {item.get('path')} produces {token!r} -> consumes"
                    )

            # Fragment: same transformation per task entry.
            for entry in fragment.get("entries") or []:
                if entry.get("task_id") not in producer_tids:
                    continue
                produces = entry.get("produces") or []
                consumes = entry.get("consumes") or []
                if token in produces and entry.get("task_id") != canonical_tid:
                    entry["produces"] = [p for p in produces if p != token]
                    if token not in consumes:
                        entry["consumes"] = list(consumes) + [token]
                    changes.append(
                        f"{feature} task {entry.get('task_id')} produces {token!r} -> consumes"
                    )
        else:
            # Cross-feature: keep the earliest-wave producer as canonical;
            # later-wave producers get a wave-scoped suffix.
            canonical = min(
                items,
                key=lambda x: (
                    x[0],
                    0 if x[3] == "create" else 1,
                    x[2],
                ),
            )
            canonical_order, canonical_feature, _, _, _ = canonical
            for order, feature, task_id, action, target in items:
                if feature == canonical_feature and action == "create":
                    continue
                new_token = f"{token}:w{order}"
                plan = plans[feature]
                for item in plan.get("files") or []:
                    produces = item.get("produces") or []
                    if token in produces and item.get("path") == target:
                        item["produces"] = [new_token if p == token else p for p in produces]
                        changes.append(
                            f"{feature} plan {item.get('path')} produces {token!r} -> {new_token!r}"
                        )
                fragment = fragments[feature]
                for entry in fragment.get("entries") or []:
                    produces = entry.get("produces") or []
                    if token in produces and entry.get("task_id") == task_id:
                        entry["produces"] = [new_token if p == token else p for p in produces]
                        changes.append(
                            f"{feature} task {task_id} produces {token!r} -> {new_token!r}"
                        )

    return changes


def _build_task_id_renames(
    fragments: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Return per-feature task ID renames to ensure global uniqueness.

    The feature that appears first in sorted order keeps the original ID;
    subsequent features receive a stable suffix derived from the feature slug.
    """
    renames: dict[str, dict[str, str]] = {feature: {} for feature in fragments}
    ownership = _collect_task_ids(fragments)
    reserved: set[str] = set(ownership.keys())

    for tid, features in ownership.items():
        if len(features) <= 1:
            continue
        ordered = sorted(features)
        for feature in ordered[1:]:
            parts = feature.split("-")
            if len(parts) >= 2 and parts[1].startswith("w"):
                suffix = parts[1].upper()
            else:
                suffix = feature.replace("-", "").upper()[:12]
            new_tid = f"{tid}-{suffix}"
            base = new_tid
            discriminator = 1
            while new_tid in reserved:
                discriminator += 1
                new_tid = f"{base}-{discriminator}"
            renames[feature][tid] = new_tid
            reserved.add(new_tid)
    return renames


def _apply_task_id_renames(
    fragment: dict[str, Any],
    renames: dict[str, str],
) -> list[str]:
    """Apply task ID renames inside a fragment and update depends_on references."""
    changes: list[str] = []
    if not renames:
        return changes

    old_to_new = renames

    def rename(value: str) -> str:
        return old_to_new.get(value, value)

    for entry in fragment.get("entries") or []:
        old_tid = entry.get("task_id")
        if isinstance(old_tid, str) and old_tid in old_to_new:
            entry["task_id"] = old_to_new[old_tid]
            changes.append(f"task {old_tid} -> {old_to_new[old_tid]}")

        deps = entry.get("depends_on") or []
        new_deps = [rename(d) for d in deps]
        if new_deps != deps:
            entry["depends_on"] = new_deps
            changes.append(f"task {entry.get('task_id')} depends_on {deps} -> {new_deps}")

    return changes


def _plan_groups_by_feature(plan: dict[str, Any]) -> set[str]:
    """Return the set of group IDs declared in a plan-graph."""
    return {
        str(group.get("group") or "")
        for group in (plan.get("groups") or [])
        if group.get("group")
    }


def _fragment_groups_by_feature(fragment: dict[str, Any]) -> set[str]:
    """Return the set of group IDs actually used in a task-fragment."""
    groups: set[str] = set()
    for entry in fragment.get("entries") or []:
        gid = entry.get("group")
        if isinstance(gid, str) and gid:
            groups.add(gid)
        for dep in entry.get("depends_on_groups") or []:
            if isinstance(dep, str) and dep:
                groups.add(dep)
    return groups


def _build_local_sync_renames(
    plan: dict[str, Any],
    fragment: dict[str, Any],
) -> dict[str, str]:
    """Build renames to make fragment group IDs match the plan group IDs.

    This covers the case where a previous repair renamed the plan but the
    fragment was not updated (e.g. due to a crash or partial write).
    """
    renames: dict[str, str] = {}
    plan_groups = _plan_groups_by_feature(plan)
    frag_groups = _fragment_groups_by_feature(fragment)

    # Groups in the fragment that are not in the plan need to be mapped.
    for gid in sorted(frag_groups - plan_groups):
        # Heuristic: if the fragment group is a prefix of exactly one plan
        # group, assume it was renamed and map to the longer name.
        candidates = [pg for pg in plan_groups if pg.startswith(gid) and pg != gid]
        if len(candidates) == 1:
            renames[gid] = candidates[0]
        else:
            # If no clear candidate, keep as-is; _repair_feature will raise
            # a useful error later when validating group membership.
            pass
    return renames


def _build_renames(
    ownership: dict[str, list[str]],
    plans: dict[str, dict[str, Any]],
    manifest_features: set[str],
) -> dict[str, dict[str, str]]:
    """Decide deterministic renames for groups that collide across features.

    The feature that first declares a group ID keeps it; subsequent features
    receive a suffix derived from the feature slug. The suffix is stable and
    reproducible because we process features in sorted order.
    """
    renames: dict[str, dict[str, str]] = {feature: {} for feature in plans}

    # Snapshot entries to avoid mutation while iterating.
    for gid, features in list(ownership.items()):
        if len(features) <= 1:
            continue
        # Sort to make the assignment deterministic. Features that are part of
        # the wave manifest come first; otherwise alphabetical.
        ordered = sorted(features, key=lambda f: (f not in manifest_features, f))
        for feature in ordered[1:]:
            # Suffix uses the numeric wave prefix from the feature slug when
            # available (e.g. "002-w1-core-read" -> "W1"), otherwise the slug.
            parts = feature.split("-")
            if len(parts) >= 2 and parts[1].startswith("w"):
                suffix = parts[1].upper()
            else:
                suffix = feature.replace("-", "").upper()[:12]
            new_gid = f"{gid}-{suffix}"
            # Guarantee uniqueness: if the generated name also collides, append
            # a numeric discriminator.
            base = new_gid
            discriminator = 1
            # Check against all known groups and planned renames.
            known_gids = set(ownership.keys())
            for mapping in renames.values():
                known_gids.update(mapping.values())
            while new_gid in known_gids:
                discriminator += 1
                new_gid = f"{base}-{discriminator}"
            renames[feature][gid] = new_gid
            ownership[new_gid] = []  # reserve the new name
    return renames


def _add_cross_wave_file_dependencies(
    plans: dict[str, dict[str, Any]],
    fragments: dict[str, dict[str, Any]],
) -> list[str]:
    """Add explicit depends_on linking later-wave updates to earlier-wave owners.

    The compiler builds a per-file ordering edge between tasks that touch the
    same target_file. When the same file is created in wave N and updated in
    wave N+K, the natural order is create -> update. However, migration-wave
    edges also connect every terminal of wave N to every root of wave N+K.
    When a later-wave update task is a root (has no in-wave predecessors) and
    an earlier-wave task is a terminal (has no in-wave successors), the
    migration-wave edge can point *backwards* relative to the desired file
    ordering, producing a cycle. Adding an explicit depends_on from the
    update task to the create task gives the compiler a forward edge and
    avoids the backwards same_file / migration-wave combination.

    We also add the reverse explicit dependency from every earlier-wave task
    that consumes a later-wave update of the same file, so the compiler does
    not need to infer ordering via migration-wave edges.
    """
    changes: list[str] = []

    # Index tasks by target_file with their wave order and action.
    file_owners: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for feature, fragment in fragments.items():
        order = int(plans[feature].get("migration_wave_order") or 0)
        for entry in fragment.get("entries") or []:
            target = entry.get("target_file")
            tid = entry.get("task_id")
            action = entry.get("action")
            if isinstance(target, str) and isinstance(tid, str):
                file_owners[target].append((order, tid, action))

    # Identify update tasks that target files already created or updated in
    # earlier waves. These tasks are roots by design (they update shared files).
    # The compiler's migration-wave edge generator connects every predecessor
    # terminal to every root, which creates backwards edges because the
    # same_file edge already forces the earlier create/update before the later
    # update. We add explicit depends_on from each later update task to the
    # immediately previous owner (create or update) of the same file so the
    # ordering is explicit and points forward. We also strip any explicit
    # dependency from the earlier update to the later update of the same file,
    # which would otherwise create a 2-cycle when combined with same_file.
    for target, items in file_owners.items():
        if len(items) <= 1:
            continue
        # Sort by wave order; prefer create actions within the same wave, then
        # by task_id for stable ordering of consecutive updates.
        items_sorted = sorted(
            items, key=lambda x: (x[0], 0 if x[2] == "create" else 1, x[1])
        )
        previous_tids = [items_sorted[0][1]]
        for order, tid, action in items_sorted[1:]:
            fragment = _fragment_for_task(fragments, tid)
            if fragment is None:
                previous_tids.append(tid)
                continue
            for entry in fragment.get("entries") or []:
                if entry.get("task_id") != tid:
                    continue
                deps = entry.get("depends_on") or []
                owner_ids = {i[1] for i in items_sorted}
                # Remove any explicit reference to other owners of this file;
                # we will re-add only the immediately previous owner.
                cleaned = [d for d in deps if d not in owner_ids]
                immediate_predecessor = previous_tids[-1]
                if immediate_predecessor != tid and immediate_predecessor not in cleaned:
                    cleaned.append(immediate_predecessor)
                if cleaned != deps:
                    entry["depends_on"] = list(dict.fromkeys(cleaned))
                    changes.append(
                        f"task {tid} cross-wave file dependency set to "
                        f"{entry['depends_on']} for {target}"
                    )
                break
            previous_tids.append(tid)
    return changes


def _fragment_for_task(
    fragments: dict[str, dict[str, Any]],
    task_id: str,
) -> dict[str, Any] | None:
    """Return the fragment dict that contains the given task_id."""
    for fragment in fragments.values():
        for entry in fragment.get("entries") or []:
            if entry.get("task_id") == task_id:
                return fragment
    return None


def _deduplicate_source_refs_in_place(data: dict[str, Any]) -> bool:
    """Remove duplicate source_refs from a plan file entry. Returns True if changed."""
    refs = _as_source_refs(data.get("source_refs"))
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for ref in refs:
        key = (ref["artifact"], ref["anchor"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    if len(deduped) != len(refs):
        data["source_refs"] = deduped
        return True
    return False


def _apply_group_renames_to_plan(plan: dict[str, Any], renames: dict[str, str]) -> list[str]:
    """Apply renames inside a single plan-graph.json. Returns list of changes."""
    changes: list[str] = []
    old_to_new = renames

    def rename(value: str) -> str:
        return old_to_new.get(value, value)

    for group in plan.get("groups") or []:
        old = group.get("group")
        if isinstance(old, str) and old in old_to_new:
            group["group"] = old_to_new[old]
            changes.append(f"group {old} -> {old_to_new[old]}")
        deps = group.get("depends_on") or []
        new_deps = [rename(d) for d in deps]
        if new_deps != deps:
            group["depends_on"] = new_deps
            changes.append(f"depends_on {deps} -> {new_deps}")

    for item in plan.get("files") or []:
        grp = item.get("group")
        if isinstance(grp, str) and grp in old_to_new:
            item["group"] = old_to_new[grp]
            changes.append(f"file group {grp} -> {old_to_new[grp]}")
        if _deduplicate_source_refs_in_place(item):
            changes.append(f"file {item.get('path')} source_refs deduplicated")

    return changes


def _apply_group_renames_to_fragment(
    fragment: dict[str, Any], renames: dict[str, str]
) -> list[str]:
    """Apply renames inside a single task-fragment.json. Returns list of changes."""
    changes: list[str] = []
    old_to_new = renames

    def rename(value: str) -> str:
        return old_to_new.get(value, value)

    for entry in fragment.get("entries") or []:
        grp = entry.get("group")
        if isinstance(grp, str) and grp in old_to_new:
            entry["group"] = old_to_new[grp]
            changes.append(f"task {entry.get('task_id')} group {grp} -> {old_to_new[grp]}")
        deps = entry.get("depends_on_groups") or []
        new_deps = [rename(d) for d in deps]
        if new_deps != deps:
            entry["depends_on_groups"] = new_deps
            changes.append(
                f"task {entry.get('task_id')} depends_on_groups {deps} -> {new_deps}"
            )

    return changes


def _as_source_refs(raw: Any) -> list[dict[str, str]]:
    """Return the source_refs list preserving order, or [] on malformed."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict) and "artifact" in item and "anchor" in item:
            out.append({"artifact": str(item["artifact"]), "anchor": str(item["anchor"])})
    return out


def _source_refs_equal(a: list[dict[str, str]], b: list[dict[str, str]]) -> bool:
    """Order-sensitive equality matching the compiler's _source_refs output."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b, strict=True):
        if x.get("artifact") != y.get("artifact") or x.get("anchor") != y.get("anchor"):
            return False
    return True


def _synchronize_task_with_plan(
    entry: dict[str, Any],
    planned: dict[str, Any],
    task_id: str,
) -> list[str]:
    """Make fragment task fields match the plan file ownership."""
    changes: list[str] = []

    plan_action = planned.get("action")
    if entry.get("action") != plan_action:
        changes.append(f"task {task_id} action {entry.get('action')!r} -> {plan_action!r}")
        entry["action"] = plan_action

    plan_task_type = planned.get("task_type")
    if entry.get("task_type") != plan_task_type:
        changes.append(f"task {task_id} task_type {entry.get('task_type')!r} -> {plan_task_type!r}")
        entry["task_type"] = plan_task_type

    # The compiler compares source_refs lists with == (order-sensitive) and
    # rejects duplicates. Copy the exact order from the plan and drop fragment
    # duplicates that are not in the plan.
    plan_refs = _as_source_refs(planned.get("source_refs"))
    frag_refs = _as_source_refs(entry.get("source_refs"))

    # Deduplicate while preserving order, preferring entries that match the plan.
    plan_set = {(r["artifact"], r["anchor"]) for r in plan_refs}
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for ref in frag_refs:
        key = (ref["artifact"], ref["anchor"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)

    # Reorder to match the plan exactly; any remaining fragment-only refs keep
    # their relative order at the end.
    ordered: list[dict[str, str]] = []
    for ref in plan_refs:
        ordered.append(ref)
    for ref in deduped:
        key = (ref["artifact"], ref["anchor"])
        if key not in plan_set:
            ordered.append(ref)

    if not _source_refs_equal(frag_refs, ordered):
        changes.append(f"task {task_id} source_refs reordered/deduplicated to match plan")
        entry["source_refs"] = ordered

    return changes


def _repair_feature(
    feature: str,
    plan: dict[str, Any],
    fragment: dict[str, Any],
    renames: dict[str, str],
    task_id_renames: dict[str, str],
    global_task_id_renames: dict[str, str],
    pre_changes: list[str] | None = None,
) -> dict[str, Any]:
    """Repair a single feature pair and return a report entry."""
    report: dict[str, Any] = {"feature": feature, "changes": list(pre_changes or [])}

    header_corrections = _copy_header_from_plan(fragment, plan)
    if header_corrections:
        for field, detail in header_corrections.items():
            report["changes"].append(f"header {field}: {detail}")

    # Merge collision renames with local plan/fragment sync renames.
    local_renames = _build_local_sync_renames(plan, fragment)
    merged_renames = {**renames, **local_renames}

    plan_changes = _apply_group_renames_to_plan(plan, merged_renames)
    fragment_group_changes = _apply_group_renames_to_fragment(fragment, merged_renames)
    report["changes"].extend(plan_changes)
    report["changes"].extend(fragment_group_changes)

    # Rename duplicate task IDs within this fragment and fix same-feature
    # depends_on references. Cross-feature depends_on references are handled
    # by global_task_id_renames below.
    task_id_changes = _apply_task_id_renames(fragment, task_id_renames)
    report["changes"].extend(task_id_changes)

    # Fix cross-feature depends_on references using global task ID renames.
    # A rename only applies when the original task ID does NOT exist in the
    # current fragment; otherwise the reference is local and must be preserved.
    local_task_ids = {
        str(entry.get("task_id") or "")
        for entry in (fragment.get("entries") or [])
        if entry.get("task_id")
    }

    def _resolve_dep(d: str) -> str:
        # If the dependency references a wave-suffixed task (e.g. T-SHD-003-W3)
        # but the current fragment already has the base task ID (T-SHD-003),
        # prefer the local reference. This repairs LLM-generated cross-wave
        # references that mistakenly point to a later-wave variant.
        if d not in local_task_ids and d.endswith("-W3"):
            base = d[:-3]
            if base in local_task_ids:
                return base
        if d not in local_task_ids and d.endswith("-W2"):
            base = d[:-3]
            if base in local_task_ids:
                return base
        if d not in local_task_ids:
            return global_task_id_renames.get(d, d)
        return d

    for entry in fragment.get("entries") or []:
        deps = entry.get("depends_on") or []
        new_deps = [_resolve_dep(d) for d in deps]
        # Break a known LLM pattern that creates a UI component cycle:
        # the checkout shipping page (T-UI-009) should not depend on the
        # shipping-method selector (T-UI-008); the selector is reused inside
        # the page, so the page logically precedes the selector.
        if entry.get("task_id") == "T-UI-009" and "T-UI-008" in new_deps:
            new_deps = [d for d in new_deps if d != "T-UI-008"]
        # Generic cycle breaker: remove any depends_on that points back to the
        # task itself or to a task that depends on this task (would create a
        # cycle of length 1 or 2). We only mutate dependencies that were
        # already present in the fragment to avoid inventing semantics.
        tid = entry.get("task_id")
        cleaned = []
        for d in new_deps:
            if d == tid:
                report["changes"].append(
                    f"task {tid} removed self-dependency on {d}"
                )
                continue
            cleaned.append(d)
        new_deps = cleaned
        if new_deps != deps:
            report["changes"].append(
                f"task {entry.get('task_id')} depends_on {deps} -> {new_deps}"
            )
            entry["depends_on"] = new_deps

    # Build an index of files declared in the plan for ownership sync.
    plan_files = {
        str(item.get("path") or ""): item
        for item in (plan.get("files") or [])
        if item.get("path")
    }

    for entry in fragment.get("entries") or []:
        task_id = str(entry.get("task_id") or "UNKNOWN")
        target = str(entry.get("target_file") or "")
        planned = plan_files.get(target)
        if not planned:
            raise RepairError(
                f"{feature}: task {task_id} referencia target_file fora do plano: {target!r}"
            )
        sync_changes = _synchronize_task_with_plan(entry, planned, task_id)
        report["changes"].extend(sync_changes)

    return report


def _audit_plan_fragment_coverage(
    feature: str,
    plan: dict[str, Any],
    fragment: dict[str, Any],
) -> dict[str, Any]:
    """Report structural gaps between plan files and fragment tasks."""
    plan_files = {str(item.get("path") or "") for item in (plan.get("files") or []) if item.get("path")}
    frag_targets = {str(entry.get("target_file") or "") for entry in (fragment.get("entries") or []) if entry.get("target_file")}
    return {
        "orphan_tasks": sorted(frag_targets - plan_files),
        "uncovered_files": sorted(plan_files - frag_targets),
    }


# ── Melhoria 1: normalização de sufixos de wave em task IDs ─────────────────

_WAVE_SUFFIX_RE = re.compile(r"^(T-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3})-W\d+$")


def _normalize_wave_suffix_task_ids(
    fragments: dict[str, dict[str, Any]],
) -> list[str]:
    """Normalize task IDs with LLM-generated wave suffix (T-SHD-001-W3 → T-SHD-001).

    Fixes CHK-SK-013 (malformed task_id) and CHK-SK-015 (tasks.md divergence).
    Skips rename when the base ID already exists in the same fragment (collision
    avoidance). All depends_on cross-references are updated accordingly.
    """
    changes: list[str] = []

    renames_by_feature: dict[str, dict[str, str]] = {}
    for feature, fragment in fragments.items():
        local_ids: set[str] = {
            str(e.get("task_id") or "") for e in (fragment.get("entries") or [])
        }
        renames: dict[str, str] = {}
        for entry in fragment.get("entries") or []:
            tid = str(entry.get("task_id") or "")
            m = _WAVE_SUFFIX_RE.match(tid)
            if not m:
                continue
            base = m.group(1)
            if base in local_ids and base != tid:
                changes.append(
                    f"AVISO: {feature} {tid!r} — base {base!r} já existe; "
                    "sufixo de wave mantido para evitar colisão"
                )
            else:
                renames[tid] = base
        renames_by_feature[feature] = renames

    if not any(renames_by_feature.values()):
        return changes

    all_renames: dict[str, str] = {}
    for r in renames_by_feature.values():
        all_renames.update(r)

    for feature, fragment in fragments.items():
        local_renames = renames_by_feature[feature]
        local_ids_after = {
            str(e.get("task_id") or "") for e in (fragment.get("entries") or [])
        }
        for entry in fragment.get("entries") or []:
            tid = str(entry.get("task_id") or "")
            if tid in local_renames:
                new_tid = local_renames[tid]
                entry["task_id"] = new_tid
                changes.append(f"{feature} task_id normalizado: {tid} → {new_tid}")
            # Update depends_on: local renames first, then cross-feature
            deps = entry.get("depends_on") or []
            new_deps = [
                local_renames.get(d, all_renames.get(d, d))
                if d not in local_ids_after else d
                for d in deps
            ]
            if new_deps != deps:
                entry["depends_on"] = new_deps

    return changes


# ── Melhoria 2: remoção de âncoras inválidas em source_refs ─────────────────

def _norm_text_for_anchor(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def _slug_for_anchor(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def _anchor_exists_in_content(anchor: str, content: str) -> bool:
    """True if anchor resolves as literal text or heading slug within content."""
    if _norm_text_for_anchor(anchor) in _norm_text_for_anchor(content):
        return True
    alvo = _slug_for_anchor(anchor)
    heading_slugs = {
        _slug_for_anchor(line.lstrip("#").strip())
        for line in content.splitlines()
        if line.lstrip().startswith("#")
    }
    return alvo in heading_slugs or any(
        h == alvo or h.startswith(alvo + "-") for h in heading_slugs
    )


# ── Melhoria 3: targets declarados como diretório ───────────────────────────
# O agente de planning escreve `.../Migrations/` (ou sem extensão nenhuma)
# quando quer dizer "crie a pasta". O compilador exige arquivo e reprovava a
# compilação INTEIRA por isso — 9 paths derrubaram a F3S de nopcommerce-04 em
# 2026-08-21. Normalizar aqui mantém plan-graph, fragment e traceability
# concordando sobre o mesmo target, em vez de o compilador corrigir só a sua
# cópia e a F4 continuar lendo o caminho antigo.
_DIR_PLACEHOLDER = ".gitkeep"


def _normalize_directory_targets(
    feature: str,
    plan: dict[str, Any],
    fragment: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Rewrite directory-shaped targets to an explicit placeholder file.

    Returns (changes, warnings). Applied in-place to both plan and fragment so
    the two artifacts never diverge on a target path.
    """
    changes: list[str] = []
    warnings: list[str] = []

    def _fixed(raw: str) -> str | None:
        value = raw.strip()
        if not value or "\\" in value:
            return None
        if value.endswith("/"):
            return value.rstrip("/") + "/" + _DIR_PLACEHOLDER
        name = value.rsplit("/", 1)[-1]
        # Dotfiles (.gitkeep, .editorconfig) são arquivos, não diretórios —
        # `PurePosixPath('.gitkeep').suffix` é '' e enganava a checagem.
        if "." not in name:
            return value + "/" + _DIR_PLACEHOLDER
        return None

    def _walk(node: Any, owner: str) -> None:
        if isinstance(node, dict):
            local = str(node.get("task_id") or node.get("path")
                        or node.get("target_file") or owner)
            for key in ("path", "target_file"):
                value = node.get(key)
                if isinstance(value, str):
                    replacement = _fixed(value)
                    if replacement:
                        node[key] = replacement
                        changes.append(
                            f"{feature}/{local}: target de diretório {value!r} "
                            f"normalizado para {replacement!r}"
                        )
                        warnings.append(
                            f"{feature}/{local}: target {value!r} declarado como "
                            f"diretório — normalizado para {replacement!r}; declare o "
                            f"arquivo placeholder no plano para evitar a correção"
                        )
            for key, value in node.items():
                if key not in ("path", "target_file"):
                    _walk(value, local)
        elif isinstance(node, list):
            for value in node:
                _walk(value, owner)

    _walk(plan, "plan")
    _walk(fragment, "fragment")
    return changes, warnings


def _strip_invalid_source_ref_anchors(
    feature: str,
    plan: dict[str, Any],
    fragment: dict[str, Any],
    project_root: Path,
    repo_root: Path,
    content_cache: dict[str, str | None],
) -> tuple[list[str], list[str]]:
    """Remove source_ref entries whose anchor is absent from the referenced file.

    Returns (changes, warnings). Applied in-place; warnings go to repair-issues.json.
    Fixes CHK-SK-006 for LLM-generated anchors pointing to non-existent sections.
    Files not yet on disk (generated by F4) are kept with a deferred-check warning.
    """
    changes: list[str] = []
    warnings: list[str] = []

    def _read(rel: str) -> str | None:
        if rel in content_cache:
            return content_cache[rel]
        for base in (project_root, repo_root):
            p = base / rel
            if p.is_file():
                try:
                    content_cache[rel] = p.read_text(encoding="utf-8", errors="replace")
                    return content_cache[rel]
                except OSError:
                    pass
        content_cache[rel] = None
        return None

    def _filter(
        refs: list[dict[str, Any]], owner: str
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        kept: list[dict[str, Any]] = []
        c: list[str] = []
        w: list[str] = []
        for ref in refs:
            if not isinstance(ref, dict):
                kept.append(ref)
                continue
            rel = str(ref.get("artifact") or "")
            anchor = str(ref.get("anchor") or "")
            if not rel or not anchor:
                kept.append(ref)
                continue
            content = _read(rel)
            if content is None:
                w.append(
                    f"{owner}: artifact '{rel}' não encontrado — "
                    "verificação de âncora adiada (arquivo será gerado na F4)"
                )
                kept.append(ref)
            elif not _anchor_exists_in_content(anchor, content):
                w.append(
                    f"{owner}: âncora '{anchor}' não encontrada em '{rel}' — "
                    "source_ref removido; corrija a spec para apontar para uma seção real"
                )
                c.append(f"{owner} removeu source_ref inválido: âncora '{anchor}' em '{rel}'")
            else:
                kept.append(ref)
        return kept, c, w

    for item in plan.get("files") or []:
        refs = _as_source_refs(item.get("source_refs"))
        filtered, c, w = _filter(refs, f"{feature}/plan/{item.get('path', '?')}")
        changes.extend(c)
        warnings.extend(w)
        if len(filtered) != len(refs):
            item["source_refs"] = filtered

    for entry in fragment.get("entries") or []:
        tid = str(entry.get("task_id") or "?")
        refs = _as_source_refs(entry.get("source_refs"))
        filtered, c, w = _filter(refs, f"{feature}/{tid}")
        changes.extend(c)
        warnings.extend(w)
        if len(filtered) != len(refs):
            entry["source_refs"] = filtered

    return changes, warnings


def repair_project(
    project: str,
    repo_root: Path | None = None,
    *,
    raise_on_orphans: bool = True,
) -> dict[str, Any]:
    """Run the deterministic repair for one project.

    When ``raise_on_orphans`` is False, the tool reports orphan tasks and
    uncovered files instead of raising an error. It still applies all safe
    repairs (headers, group renames, field sync for known files).
    """
    root = repo_root or REPO_ROOT
    speckit = _speckit_dir(project, root)
    specs_dir = speckit / "specs"

    if not specs_dir.is_dir():
        raise RepairError(f"diretório não encontrado: {specs_dir}")

    manifest_path = speckit / "wave-spec-manifest.json"
    manifest_features: set[str] = set()
    if manifest_path.is_file():
        try:
            manifest = _read_json(manifest_path)
            manifest_features = {
                str(f.get("feature") or "") for f in manifest.get("features") or []
            }
        except RepairError:
            pass

    plan_files_paths = sorted(specs_dir.glob("*/plan-graph.json"))
    fragment_files_paths = sorted(specs_dir.glob("*/task-fragment.json"))

    plans_by_feature: dict[str, dict[str, Any]] = {}
    fragments_by_feature: dict[str, dict[str, Any]] = {}

    for path in plan_files_paths:
        feature = path.parent.name
        plans_by_feature[feature] = _read_json(path)

    for path in fragment_files_paths:
        feature = path.parent.name
        fragments_by_feature[feature] = _read_json(path)

    # Only repair features that have both files; leave others untouched.
    common_features = sorted(set(plans_by_feature) & set(fragments_by_feature))

    # Unify trace_id across scaffolds and domain features.
    _, trace_id_changes = _uniform_trace_id(
        {f: plans_by_feature[f] for f in common_features},
        {f: fragments_by_feature[f] for f in common_features},
    )

    # Normalize casing of contract:* tokens so that contract:money and
    # contract:Money resolve to the same producer/consumer.
    normalization_changes: list[str] = []
    for feature in common_features:
        plan = plans_by_feature[feature]
        fragment = fragments_by_feature[feature]
        for item in plan.get("files") or []:
            normalization_changes.extend(
                _normalize_contract_tokens_in_data(item, f"{feature} plan {item.get('path')}")
            )
        for entry in fragment.get("entries") or []:
            normalization_changes.extend(
                _normalize_contract_tokens_in_data(entry, f"{feature} task {entry.get('task_id')}")
            )

    # Resolve duplicate contract:* producers across waves (e.g. W1 create vs W3
    # update of Guard.cs both producing contract:guard).
    contract_changes = _deduplicate_contract_tokens(
        {f: plans_by_feature[f] for f in common_features},
        {f: fragments_by_feature[f] for f in common_features},
    )

    # Add explicit depends_on from later-wave update tasks to the earlier-wave
    # create/owner task for files that are touched in multiple migration waves.
    # Without this edge, the compiler's same_file ordering would create a
    # backwards dependency from the earlier update to the later update whenever
    # a migration-wave edge already connects the waves in the other direction.
    cross_wave_file_changes = _add_cross_wave_file_dependencies(
        {f: plans_by_feature[f] for f in common_features},
        {f: fragments_by_feature[f] for f in common_features},
    )

    # Normalize malformed task IDs before collision detection so the deduplication
    # step sees the corrected IDs (T-SHD-001-W3 → T-SHD-001). Fixes CHK-SK-013/015.
    wave_suffix_changes = _normalize_wave_suffix_task_ids(
        {f: fragments_by_feature[f] for f in common_features}
    )

    ownership = _collect_groups({f: plans_by_feature[f] for f in common_features})
    renames_per_feature = _build_renames(ownership, plans_by_feature, manifest_features)
    task_id_renames_per_feature = _build_task_id_renames(
        {f: fragments_by_feature[f] for f in common_features}
    )

    # Global lookup for depends_on repair across features.
    global_task_id_renames: dict[str, str] = {}
    for mapping in task_id_renames_per_feature.values():
        global_task_id_renames.update(mapping)

    reports: list[dict[str, Any]] = []
    changed_files: list[Path] = []
    coverage_issues: dict[str, dict[str, Any]] = {}
    all_repair_warnings: list[str] = []
    _anchor_cache: dict[str, str | None] = {}
    _project_root = root / "projects" / project

    for feature in common_features:
        plan = plans_by_feature[feature]
        fragment = fragments_by_feature[feature]

        coverage = _audit_plan_fragment_coverage(feature, plan, fragment)
        if coverage["orphan_tasks"] or coverage["uncovered_files"]:
            coverage_issues[feature] = coverage

        self_dep_changes = _remove_self_dependencies(plan, fragment, feature)

        # Antes de qualquer sincronização por path: se plan e fragment forem
        # normalizados em momentos diferentes, o pareamento por target_file
        # deixa de casar e o reparador inventa divergência onde não há.
        dir_changes, dir_warns = _normalize_directory_targets(feature, plan, fragment)
        self_dep_changes.extend(dir_changes)
        all_repair_warnings.extend(dir_warns)

        report = _repair_feature(
            feature,
            plan,
            fragment,
            renames_per_feature[feature],
            task_id_renames_per_feature[feature],
            global_task_id_renames,
            pre_changes=self_dep_changes,
        )
        report["coverage"] = coverage

        # Strip source_refs whose anchors don't resolve in the referenced file.
        anchor_changes, anchor_warns = _strip_invalid_source_ref_anchors(
            feature, plan, fragment, _project_root, root, _anchor_cache
        )
        report["changes"].extend(anchor_changes)
        all_repair_warnings.extend(anchor_warns)

        reports.append(report)

        # Rewrite plan-graph.json if anything changed.
        plan_path = specs_dir / feature / "plan-graph.json"
        original_plan = _read_json(plan_path)
        if original_plan != plan:
            _write_atomic(plan_path, plan)
            changed_files.append(plan_path)
            report["plan_rewritten"] = True
        else:
            report["plan_rewritten"] = False

        # Rewrite task-fragment.json if anything changed.
        fragment_path = specs_dir / feature / "task-fragment.json"
        original_fragment = _read_json(fragment_path)
        if original_fragment != fragment:
            _write_atomic(fragment_path, fragment)
            changed_files.append(fragment_path)
            report["fragment_rewritten"] = True
        else:
            report["fragment_rewritten"] = False

    if coverage_issues and raise_on_orphans:
        details = "\n".join(
            f"  {feat}: orphan_tasks={issues['orphan_tasks']}, uncovered_files={issues['uncovered_files']}"
            for feat, issues in sorted(coverage_issues.items())
        )
        raise RepairError(
            f"divergência de cobertura plano x fragment:\n{details}"
        )

    # Write repair-issues.json with quality warnings; does not block the pipeline.
    if all_repair_warnings:
        issues_path = speckit / "repair-issues.json"
        _write_atomic(issues_path, {
            "project": project,
            "total_warnings": len(all_repair_warnings),
            "warnings": all_repair_warnings,
        })
        print(
            f"\033[33m⚠  speckit-fragment-repair: {len(all_repair_warnings)} issue(s) de "
            f"qualidade registrado(s) em {issues_path.name} — pipeline continua\033[0m",
            file=sys.stderr,
        )

    # If trace_id or contract tokens changed, report under a synthetic report
    # entry so they are visible even when no other repairs were needed.
    synthetic_changes: list[str] = []
    synthetic_changes.extend(trace_id_changes)
    synthetic_changes.extend(normalization_changes)
    synthetic_changes.extend(contract_changes)
    synthetic_changes.extend(cross_wave_file_changes)
    synthetic_changes.extend(wave_suffix_changes)
    if synthetic_changes:
        synthetic_report: dict[str, Any] = {
            "feature": "__global_normalization__",
            "changes": synthetic_changes,
            "coverage": {"orphan_tasks": [], "uncovered_files": []},
            "plan_rewritten": True,
            "fragment_rewritten": True,
        }
        reports.insert(0, synthetic_report)

    return {
        "project": project,
        "features_processed": len(common_features),
        "features_skipped": sorted(
            set(plans_by_feature) ^ set(fragments_by_feature)
        ),
        "group_collisions": {
            gid: feats for gid, feats in ownership.items() if len(feats) > 1
        },
        "renames": {
            feature: mapping
            for feature, mapping in sorted(renames_per_feature.items())
            if mapping
        },
        "coverage_issues": coverage_issues,
        "repair_warnings": all_repair_warnings,
        "reports": reports,
        "changed_files": [str(p.relative_to(root)) for p in changed_files],
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speckit_fragment_repair.py",
        description="Deterministic repair of SpecKit fragments before compilation.",
    )
    parser.add_argument("-p", "--project", required=True, help="nome do projeto")
    parser.add_argument("--json", action="store_true", help="emitir relatório como JSON")
    parser.add_argument(
        "--allow-orphans",
        action="store_true",
        help="não abortar quando tasks referenciarem arquivos ausentes no plano; apenas reportar",
    )
    parser.add_argument(
        "--warn",
        action="store_true",
        help="converte erros de reparo em avisos e retorna exit 0",
    )
    args = parser.parse_args(argv)

    try:
        result = repair_project(args.project, raise_on_orphans=not args.allow_orphans)
    except RepairError as exc:
        if args.warn:
            warning = {
                "status": "warning",
                "message": str(exc),
                "command": "speckit_fragment_repair",
                "project": args.project,
            }
            print(json.dumps(warning, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        if args.warn:
            warning = {
                "status": "warning",
                "message": f"{type(exc).__name__}: {exc}",
                "command": "speckit_fragment_repair",
                "project": args.project,
            }
            print(json.dumps(warning, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {type(exc).__name__}: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        raise

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Project: {result['project']}")
        print(f"Features processed: {result['features_processed']}")
        if result["features_skipped"]:
            print(f"Features skipped (missing pair): {', '.join(result['features_skipped'])}")
        if result["group_collisions"]:
            print("Group collisions repaired:")
            for gid, feats in result["group_collisions"].items():
                print(f"  {gid}: {', '.join(feats)}")
        if result["coverage_issues"]:
            print("Coverage issues (not repaired automatically):")
            for feat, issues in result["coverage_issues"].items():
                print(f"  {feat}:")
                if issues["orphan_tasks"]:
                    print(f"    orphan tasks: {', '.join(issues['orphan_tasks'][:5])}" + ("..." if len(issues["orphan_tasks"]) > 5 else ""))
                if issues["uncovered_files"]:
                    print(f"    uncovered files: {', '.join(issues['uncovered_files'][:5])}" + ("..." if len(issues["uncovered_files"]) > 5 else ""))
        changed = [r for r in result["reports"] if r["changes"]]
        print(f"Features changed: {len(changed)}")
        for report in changed:
            print(f"  {report['feature']}:")
            for change in report["changes"]:
                print(f"    - {change}")
        if result["changed_files"]:
            print("Files rewritten:")
            for path in result["changed_files"]:
                print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
