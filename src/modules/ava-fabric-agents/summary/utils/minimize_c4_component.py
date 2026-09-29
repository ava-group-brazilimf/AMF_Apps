"""Progressive and bisection harness for Mermaid C4 component layout failures."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from render_blueprint_compatibility import execute_probe, sanitize_c4_source, validate_c4_graph

DECL_RE = re.compile(r"(?m)^\s*(?:Person_Ext|Person|System_Ext|System|ContainerDb_Ext|ContainerDb|Container|Component_Ext|Component|Container_Boundary|System_Boundary|Boundary).*?$")
REL_RE = re.compile(r"(?m)^\s*(Rel(?:_Back|_Neighbor|_U|_R|_L|_D)?|BiRel)\s*\(.*?\)\s*$")


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relationship_metadata(source: str) -> list[dict[str, Any]]:
    graph = validate_c4_graph(source)
    by_alias = {item["alias"]: item for item in graph["declaredAliases"]}
    rows = []
    for endpoint in graph["relationshipEndpoints"]:
        line = source.splitlines()[endpoint["line"] - 1]
        values = re.split(r",\s*", line[line.find("(") + 1:line.rfind(")")])
        source_node, target_node = by_alias.get(endpoint["sourceAlias"]), by_alias.get(endpoint["targetAlias"])
        rows.append({**endpoint, "label": values[2].strip(' "') if len(values) > 2 else "", "technology": values[3].strip(' "') if len(values) > 3 else "", "sourceBoundary": source_node.get("boundary") if source_node else None, "targetBoundary": target_node.get("boundary") if target_node else None, "crossBoundary": bool(source_node and target_node and source_node.get("boundary") != target_node.get("boundary"))})
    return rows


def build_attempts(source: str) -> list[dict[str, Any]]:
    lines = source.splitlines()
    first_rel = next((index for index, line in enumerate(lines) if REL_RE.match(line)), len(lines))
    declarations = lines[1:first_rel]
    relationships = [line for line in lines if REL_RE.match(line)]
    attempts = []
    groups = [("declarations-only", declarations, []), ("first-relationship", declarations, relationships[:1])]
    for count in range(2, len(relationships) + 1):
        groups.append((f"incremental-{count}", declarations, relationships[:count]))
    for label, decls, rels in groups:
        text = "\n".join([lines[0]] + decls + rels) + "\n"
        attempts.append({"attemptId": label, "includedDeclarations": decls, "includedRelationships": rels, "relationshipCount": len(rels), "lastAddedRelationship": rels[-1] if rels else None, "sourceHash": sha(text), "source": text})
    return attempts


def run(repo_root: str | Path, source_path: str | Path) -> dict[str, Any]:
    source = sanitize_c4_source(Path(source_path).read_text(encoding="utf-8", errors="replace"))
    attempts = []
    for attempt in build_attempts(source):
        result = execute_probe(repo_root, attempt["source"])
        attempt.update({key: result.get(key) for key in ("renderStatus", "error", "stack", "rootCause", "stage")})
        attempt["failingRelationshipCandidate"] = attempt["lastAddedRelationship"] if attempt.get("renderStatus") != "PASS" else None
        attempt.pop("source", None)
        attempts.append(attempt)
    failing = next((attempt for attempt in attempts if attempt.get("renderStatus") != "PASS"), None)
    return {"artifactPath": str(source_path), "attempts": attempts, "minimalFailingSubset": failing, "failingRelationshipCandidates": relationship_metadata(source), "graphIntegrity": validate_c4_graph(source)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.repo_root, args.source)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
