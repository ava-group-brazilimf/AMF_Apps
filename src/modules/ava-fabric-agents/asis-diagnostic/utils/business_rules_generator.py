#!/usr/bin/env python3
"""Prepare and render business-rule documentation without loading a full artifact into an LLM."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GENERIC_TITLE = re.compile(r"^\s*caso\s+sc-[0-9a-f]+\s*$", re.IGNORECASE)
VALID_PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-") or "sem-contexto"


def artifact_data(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    document = read_json(path)
    if document.get("artifact") != "10_business_rule_cases":
        raise ValueError("Input must be the 10_business_rule_cases artifact")
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Missing $.payload object")
    catalog = payload.get("catalog")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("rules"), list):
        raise ValueError("Missing $.payload.catalog.rules[]; run the BRS LLM catalog stage first")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Missing $.payload.cases[]")
    case_map = {case["case_id"]: case for case in cases if isinstance(case, dict) and case.get("case_id")}
    rules = [rule for rule in catalog["rules"] if isinstance(rule, dict)]
    return document, rules, case_map


def chunks(values: list[Any], size: int) -> Iterable[list[Any]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def compact_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        key: case.get(key)
        for key in (
            "case_id",
            "classification",
            "business_score",
            "domain_candidates",
            "affected_fields",
            "evidence_ids",
            "atomic_rules",
            "source",
            "source_context",
        )
    }


def prepare(input_path: Path, work_dir: Path, batch_size: int) -> None:
    document, rules, case_map = artifact_data(input_path)
    packets_dir = work_dir / "packets"
    reset_directory(packets_dir)

    # When case_map is empty (e.g. Java extractor produces catalog-only artifacts),
    # skip the cross-reference check — rules are self-contained.
    if case_map:
        missing_cases = [rule.get("rule_key") for rule in rules if rule.get("case_id") not in case_map]
        if missing_cases:
            raise ValueError(f"Catalog rules without a matching case: {missing_cases[:10]}")

    packet_names: list[str] = []
    indexed_rules = list(enumerate(rules))
    for packet_number, batch in enumerate(chunks(indexed_rules, batch_size), start=1):
        packet_id = f"packet-{packet_number:04d}"
        packet_names.append(f"{packet_id}.json")
        entries = []
        for catalog_index, rule in batch:
            entries.append({
                "catalog_index": catalog_index,
                "rule": rule,
                "case": compact_case(case_map.get(rule["case_id"], {})),
            })
        write_json(
            packets_dir / f"{packet_id}.json",
            {
                "packet_id": packet_id,
                "instructions": "Create one semantic decision for every rule; use the case only as supporting evidence.",
                "entries": entries,
            },
        )

    reset_directory(work_dir / "decisions")
    reset_directory(work_dir / "context-packets")
    reset_directory(work_dir / "requirement-candidates")
    reset_directory(work_dir / "requirement-consolidation")
    reset_directory(work_dir / "requirements-final")
    write_json(
        work_dir / "manifest.json",
        {
            "input": str(input_path.resolve()),
            "project": document.get("project", {}),
            "schema_version": document.get("schema_version"),
            "rule_count": len(rules),
            "case_count": len(case_map),
            "generic_title_count": sum(bool(GENERIC_TITLE.match(str(rule.get("title", "")))) for rule in rules),
            "batch_size": batch_size,
            "packets": packet_names,
        },
    )
    print(f"Prepared {len(rules)} rules in {len(packet_names)} packets at {work_dir}")


def load_decisions(work_dir: Path, rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    expected = {rule.get("rule_key") for rule in rules}
    decisions: dict[str, dict[str, Any]] = {}
    for path in sorted((work_dir / "decisions").glob("*.json")):
        document = read_json(path)
        for decision in document.get("rules", []):
            key = decision.get("rule_key")
            if key in decisions:
                raise ValueError(f"Duplicate decision for {key}")
            decisions[key] = decision
    missing = sorted(expected - decisions.keys())
    extra = sorted(decisions.keys() - expected)
    if missing or extra:
        raise ValueError(f"Decision coverage mismatch: missing={missing[:10]}, extra={extra[:10]}")
    return decisions


def selected_rule(rule: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    title = str(decision.get("title") or rule.get("title") or "").strip()
    bounded_context = str(decision.get("bounded_context") or "").strip()
    if not title or GENERIC_TITLE.match(title):
        raise ValueError(f"Included rule {rule.get('rule_key')} has a generic or empty title")
    if not bounded_context:
        raise ValueError(f"Included rule {rule.get('rule_key')} has no bounded_context")
    priority = str(decision.get("priority", "MEDIUM")).upper()
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority for {rule.get('rule_key')}: {priority}")
    result = dict(rule)
    for field in ("statement", "trigger", "inputs", "outputs"):
        if field in decision:
            result[field] = decision[field]
    result.update({
        "title": title,
        "bounded_context": bounded_context,
        "bounded_context_slug": slugify(bounded_context),
        "priority": priority,
        "confirmed": str(decision.get("confirmed", "NEEDS VALIDATION")).upper(),
        "decision_rationale": decision.get("rationale", ""),
    })
    return result


def build_context_packets(input_path: Path, work_dir: Path, batch_size: int) -> None:
    _, rules, _ = artifact_data(input_path)
    decisions = load_decisions(work_dir, rules)
    selected = [selected_rule(rule, decisions[rule["rule_key"]]) for rule in rules if decisions[rule["rule_key"]].get("include") is True]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rule in selected:
        grouped.setdefault(rule["bounded_context_slug"], []).append(rule)
    reset_directory(work_dir / "context-packets")
    packet_count = 0
    for context_slug in sorted(grouped):
        context_rules = sorted(grouped[context_slug], key=rule_sort_key)
        for part, batch in enumerate(chunks(context_rules, batch_size), start=1):
            packet_count += 1
            packet_id = f"bc-{context_slug}-{part:04d}"
            write_json(
                work_dir / "context-packets" / f"{packet_id}.json",
                {
                    "packet_id": packet_id,
                    "bounded_context": batch[0]["bounded_context"],
                    "bounded_context_slug": context_slug,
                    "rules": [
                        {
                            key: rule.get(key)
                            for key in ("rule_key", "title", "statement", "trigger", "inputs", "outputs", "priority", "source")
                        }
                        for rule in batch
                    ],
                },
            )
    print(f"Prepared {len(selected)} included rules in {packet_count} bounded-context packets")


def build_requirement_consolidation(work_dir: Path) -> None:
    grouped: dict[str, dict[str, Any]] = {}
    for path in sorted((work_dir / "requirement-candidates").glob("*.json")):
        document = read_json(path)
        context_slug = str(document.get("bounded_context_slug") or "")
        if not context_slug:
            raise ValueError(f"Missing bounded_context_slug in {path}")
        target = grouped.setdefault(
            context_slug,
            {"bounded_context": document.get("bounded_context"), "bounded_context_slug": context_slug, "candidates": []},
        )
        target["candidates"].extend(document.get("requirements", []))
    reset_directory(work_dir / "requirement-consolidation")
    for context_slug, document in sorted(grouped.items()):
        write_json(work_dir / "requirement-consolidation" / f"{context_slug}.json", document)
    print(f"Prepared requirement consolidation for {len(grouped)} bounded contexts")


def rule_sort_key(rule: dict[str, Any]) -> tuple[Any, ...]:
    source = rule.get("source") or {}
    line_range = source.get("line_range") or [0]
    return (
        rule.get("bounded_context_slug", ""),
        str(source.get("file", "")).casefold(),
        int(line_range[0] or 0),
        str(rule.get("rule_key", "")),
    )


def load_requirements(work_dir: Path, known_rule_keys: set[str]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for path in sorted((work_dir / "requirements-final").glob("*.json")):
        document = read_json(path)
        bounded_context = str(document.get("bounded_context") or "").strip()
        for requirement in document.get("requirements", []):
            source_keys = requirement.get("source_rule_keys", [])
            unknown = sorted(set(source_keys) - known_rule_keys)
            if unknown:
                raise ValueError(f"Requirement in {path} references unknown or excluded rules: {unknown}")
            if not source_keys:
                raise ValueError(f"Requirement in {path} has no source_rule_keys")
            priority = str(requirement.get("priority", "MEDIUM")).upper()
            if priority not in VALID_PRIORITIES:
                raise ValueError(f"Invalid requirement priority in {path}: {priority}")
            requirements.append({
                **requirement,
                "bounded_context": bounded_context,
                "bounded_context_slug": slugify(bounded_context),
                "priority": priority,
            })
    return requirements


def escape_cell(value: Any) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_document(
    project: Any,
    trace_id: str,
    generated: str,
    rules: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    derive_requirements: bool,
    title_suffix: str = "",
) -> str:
    project_name = project.get("name") if isinstance(project, dict) else project
    lines = [
        f"# Business Rules \u2014 {project_name or 'unknown'} AS-IS{title_suffix}",
        f"**trace_id**: {trace_id}",
        f"**Generated**: {generated}",
        "",
        "---",
        "",
        "## Metadata",
        f"- **Project**: {project_name or 'unknown'}",
        f"- **Functional requirements enabled**: {'YES' if derive_requirements else 'NO'}",
        f"- **Business rules**: {len(rules)}",
        "- **Source**: 10_business_rule_cases.json (`payload.catalog.rules[]` enriched by `payload.cases[]`)",
        "",
    ]
    if derive_requirements:
        lines.extend(["## Functional Requirements", ""])
        for requirement in requirements:
            lines.extend([
                f"### {requirement['id']}: {requirement['title']}",
                f"**Module**: {requirement['bounded_context']}",
                f"**Description**: {escape_cell(requirement['statement'])}",
                f"**Priority**: {requirement['priority']}",
                f"**Derived From**: {', '.join(requirement['source_rule_ids'])}",
                "",
            ])
    lines.extend(["## Business Rules", ""])
    contexts: dict[str, list[dict[str, Any]]] = {}
    for rule in rules:
        contexts.setdefault(rule["bounded_context"], []).append(rule)
    for context in sorted(contexts, key=lambda value: slugify(value)):
        lines.extend([f"### Bounded Context: {context}", ""])
        for rule in contexts[context]:
            impact = escape_cell(rule.get("decision_rationale")) or "Impacto nao detalhado na curadoria."
            lines.extend([
                f"### {rule['id']}: {rule['title']}",
                f"**Rule**: {escape_cell(rule.get('statement'))}",
                f"**Impact**: {impact}",
                f"**Priority**: {rule['priority']}",
                f"**Trigger**: {escape_cell(rule.get('trigger'))}",
                f"**Inputs**: {escape_cell(rule.get('inputs'))}",
                f"**Outputs**: {escape_cell(rule.get('outputs'))}",
                f"**Module**: {rule['bounded_context']}",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def rule_to_json(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rule["id"],
        "title": rule["title"],
        "bounded_context": rule["bounded_context"],
        "statement": rule.get("statement"),
        "impact": rule.get("decision_rationale") or "Impacto nao detalhado na curadoria.",
        "priority": rule["priority"],
        "trigger": rule.get("trigger"),
        "inputs": rule.get("inputs"),
        "outputs": rule.get("outputs"),
        "module": rule["bounded_context"],
    }


def requirement_to_json(requirement: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": requirement["id"],
        "title": requirement["title"],
        "module": requirement["bounded_context"],
        "description": requirement.get("statement"),
        "priority": requirement["priority"],
        "derived_from": requirement["source_rule_ids"],
    }


def render_json_document(
    project: Any,
    trace_id: str,
    generated: str,
    rules: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    derive_requirements: bool,
) -> dict[str, Any]:
    """Build the JSON mirror of render_document(): same rules/requirements, machine-readable."""
    project_name = project.get("name") if isinstance(project, dict) else project
    return {
        "project": project_name or "unknown",
        "trace_id": trace_id,
        "generated": generated,
        "functional_requirements_enabled": derive_requirements,
        "business_rules_count": len(rules),
        "functional_requirements_count": len(requirements) if derive_requirements else 0,
        "source": "10_business_rule_cases.json (payload.catalog.rules[] enriched by payload.cases[])",
        "functional_requirements": [requirement_to_json(item) for item in requirements] if derive_requirements else [],
        "business_rules": [rule_to_json(rule) for rule in rules],
    }


def render(
    input_path: Path,
    work_dir: Path,
    output_dir: Path,
    split_by_context: bool,
    derive_requirements: bool,
) -> None:
    document, catalog_rules, _ = artifact_data(input_path)
    decisions = load_decisions(work_dir, catalog_rules)
    rules = [
        selected_rule(rule, decisions[rule["rule_key"]])
        for rule in catalog_rules
        if decisions[rule["rule_key"]].get("include") is True
    ]
    rules.sort(key=rule_sort_key)
    for index, rule in enumerate(rules, start=1):
        rule["id"] = f"BR-{index:04d}"
    key_to_id = {rule["rule_key"]: rule["id"] for rule in rules}

    requirements = load_requirements(work_dir, set(key_to_id)) if derive_requirements else []
    if derive_requirements:
        context_by_key = {rule["rule_key"]: rule["bounded_context_slug"] for rule in rules}
        covered_keys: set[str] = set()
        for requirement in requirements:
            source_keys = set(requirement["source_rule_keys"])
            covered_keys.update(source_keys)
            source_contexts = {context_by_key[key] for key in source_keys}
            if source_contexts != {requirement["bounded_context_slug"]}:
                raise ValueError(f"Functional requirement crosses bounded contexts: {requirement.get('title')}")
        uncovered = sorted(set(key_to_id) - covered_keys)
        if uncovered:
            raise ValueError(f"Included rules without a functional requirement: {uncovered[:10]}")
    requirements.sort(key=lambda item: (item["bounded_context_slug"], str(item.get("title", "")).casefold(), tuple(sorted(item["source_rule_keys"]))))
    for index, requirement in enumerate(requirements, start=1):
        requirement["id"] = f"FR-{index:04d}"
        requirement["source_rule_ids"] = sorted(key_to_id[key] for key in requirement["source_rule_keys"])

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("business-rules*.md"):
        stale.unlink()
    for stale in output_dir.glob("business-rules*.json"):
        stale.unlink()
    project = document.get("project", {})
    trace_id = str(document.get("trace_id") or uuid.uuid4())
    generated = str(document.get("generated_at") or datetime.now(timezone.utc).date().isoformat())[:10]
    if split_by_context:
        context_slugs = sorted({rule["bounded_context_slug"] for rule in rules})
        for context_slug in context_slugs:
            context_rules = [rule for rule in rules if rule["bounded_context_slug"] == context_slug]
            context_requirements = [item for item in requirements if item["bounded_context_slug"] == context_slug]
            content = render_document(
                project, trace_id, generated, context_rules, context_requirements, derive_requirements,
                f" - {context_rules[0]['bounded_context']}",
            )
            (output_dir / f"business-rules-{context_slug}.md").write_text(content, encoding="utf-8", newline="\n")
    else:
        content = render_document(project, trace_id, generated, rules, requirements, derive_requirements)
        (output_dir / "business-rules.md").write_text(content, encoding="utf-8", newline="\n")

    # JSON mirror: always the full (non-split) rule/requirement set, regardless of
    # --split-by-bounded-context, so business-rules.json always contains the same
    # data as the consolidated business-rules.md.
    json_document = render_json_document(project, trace_id, generated, rules, requirements, derive_requirements)
    write_json(output_dir / "business-rules.json", json_document)
    print(
        f"Rendered {len(rules)} business rules and {len(requirements)} functional requirements "
        f"at {output_dir} (business-rules.json mirror included)"
    )


def cleanup(work_dir: Path) -> None:
    """Remove the temporary work_dir after final artifacts have been rendered."""
    if work_dir.exists():
        shutil.rmtree(work_dir)
        print(f"Removed temporary work directory {work_dir}")
    else:
        print(f"Work directory {work_dir} does not exist — nothing to clean")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    prepare_parser = commands.add_parser("prepare", help="Create bounded LLM input packets")
    prepare_parser.add_argument("input", type=Path)
    prepare_parser.add_argument("--work-dir", type=Path, required=True)
    prepare_parser.add_argument("--batch-size", type=int, default=20)

    contexts_parser = commands.add_parser("build-contexts", help="Validate decisions and group included rules")
    contexts_parser.add_argument("input", type=Path)
    contexts_parser.add_argument("--work-dir", type=Path, required=True)
    contexts_parser.add_argument("--batch-size", type=int, default=40)

    requirements_parser = commands.add_parser("build-requirement-consolidation", help="Group requirement candidates by context")
    requirements_parser.add_argument("--work-dir", type=Path, required=True)

    render_parser = commands.add_parser("render", help="Validate semantic outputs and render Markdown")
    render_parser.add_argument("input", type=Path)
    render_parser.add_argument("--work-dir", type=Path, required=True)
    render_parser.add_argument("--output-dir", type=Path, required=True)
    render_parser.add_argument("--split-by-bounded-context", action=argparse.BooleanOptionalAction, default=False)
    render_parser.add_argument("--derive-functional-requirements", action=argparse.BooleanOptionalAction, default=True)

    cleanup_parser = commands.add_parser("cleanup", help="Remove the temporary work directory after a successful render")
    cleanup_parser.add_argument("--work-dir", type=Path, required=True)
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "prepare":
        if args.batch_size < 1:
            raise ValueError("--batch-size must be positive")
        prepare(args.input, args.work_dir, args.batch_size)
    elif args.command == "build-contexts":
        if args.batch_size < 1:
            raise ValueError("--batch-size must be positive")
        build_context_packets(args.input, args.work_dir, args.batch_size)
    elif args.command == "build-requirement-consolidation":
        build_requirement_consolidation(args.work_dir)
    elif args.command == "render":
        render(args.input, args.work_dir, args.output_dir, args.split_by_bounded_context, args.derive_functional_requirements)
    elif args.command == "cleanup":
        cleanup(args.work_dir)


if __name__ == "__main__":
    main()