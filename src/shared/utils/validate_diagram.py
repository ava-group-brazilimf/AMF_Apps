#!/usr/bin/env python3
"""
validate_diagram.py — Pre-write validation gate for Mermaid (.mmd) and Draw.io (.drawio) artifacts.

This utility MUST be called by agents BEFORE writing any .mmd or .drawio file to disk.
It reads content from stdin, validates + sanitizes, and writes the clean version to the
target file ONLY if validation passes. If validation fails and cannot auto-fix, it exits
with code 1 and prints the errors — the agent MUST NOT write the file manually.

This is the SINGLE POINT OF WRITE for all diagram artifacts. Agents MUST NOT use
Write/save/persist directly for .mmd or .drawio files — they MUST pipe through this gate.

Implements:
  - "Protocolo de Sanitização Obrigatório" from mermaid-guardrails.md v1.4.0
  - "Protocolo de Sanitização Draw.io" from drawio-governance.md
  - Mermaid v11.14.0 syntax validation

Usage by agents (in Bash blocks):
    # Mermaid file — pipe content, gate writes to disk
    Bash: cat <<'MERMAID_EOF' | python src/shared/utils/validate_diagram.py --output projects/{project}/outputs/tobe/diagrams/architecture-blueprint.mmd
    flowchart TB
        A["Node A"] --> B["Node B"]
    MERMAID_EOF

    # Draw.io file — pipe content, gate writes to disk
    Bash: cat <<'DRAWIO_EOF' | python src/shared/utils/validate_diagram.py --output projects/{project}/outputs/tobe/diagrams/architecture-blueprint.drawio
    <?xml version="1.0" encoding="UTF-8"?>
    <mxfile>...</mxfile>
    DRAWIO_EOF

    # Validate only (no write) — useful for pre-check
    Bash: cat <<'EOF' | python src/shared/utils/validate_diagram.py --type mmd
    flowchart TB
        A --> B
    EOF

Exit codes:
    0 — PASS: content is valid (and written to disk if --output provided)
    1 — FAIL: content has unfixable errors (file NOT written)
    2 — FIXED: content had issues that were auto-corrected (file written with fixes)
"""

import os
import sys
from pathlib import Path

# Import sanitization functions from sanitize_diagrams.py (sibling module)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanitize_diagrams import (  # noqa: E402
    Finding,
    SanitizationReport,
    sanitize_mermaid,
    sanitize_drawio,
    _detect_diagram_type,
    PROHIBITED_DIAGRAM_TYPES,
)


def _detect_type_from_path(filepath: str) -> str:
    """Detect file type from extension."""
    if filepath.endswith(".mmd"):
        return "mmd"
    elif filepath.endswith(".drawio"):
        return "drawio"
    return "unknown"


def _detect_type_from_content(content: str) -> str:
    """Detect file type from content."""
    stripped = content.strip()
    if stripped.startswith("<?xml") or stripped.startswith("<mxfile") or stripped.startswith("<mxGraphModel"):
        return "drawio"
    # Check if it looks like a mermaid diagram
    first_line = stripped.split("\n")[0].strip() if stripped else ""
    dtype = _detect_diagram_type(content)
    if dtype != "unknown":
        return "mmd"
    return "unknown"


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Pre-write validation gate for diagram artifacts. Reads from stdin."
    )
    parser.add_argument(
        "--output", "-o",
        help="Target file path to write validated content. If omitted, validates only (no write)."
    )
    parser.add_argument(
        "--type", "-t",
        choices=["mmd", "drawio"],
        help="Force file type detection (inferred from --output extension if not provided)."
    )

    args = parser.parse_args()

    # Read content from stdin
    if sys.stdin.isatty():
        print("ERROR: No input on stdin. Pipe diagram content to this script.", file=sys.stderr)
        print("Usage: cat diagram.mmd | python validate_diagram.py --output path/to/output.mmd", file=sys.stderr)
        sys.exit(1)

    content = sys.stdin.read()

    if not content.strip():
        print("ERROR: Empty input received on stdin.", file=sys.stderr)
        sys.exit(1)

    # Determine file type
    file_type = args.type
    if not file_type and args.output:
        file_type = _detect_type_from_path(args.output)
    if not file_type:
        file_type = _detect_type_from_content(content)
    if file_type == "unknown":
        print("ERROR: Cannot determine file type. Use --type mmd|drawio or provide --output with extension.", file=sys.stderr)
        sys.exit(1)

    # Create report
    report = SanitizationReport()
    report.files_scanned = 1
    source_name = args.output if args.output else "<stdin>"

    # Run sanitization + validation
    if file_type == "mmd":
        sanitized = sanitize_mermaid(source_name, content, report, dry_run=False)
    else:
        sanitized = sanitize_drawio(source_name, content, report, dry_run=False)

    # Determine outcome
    has_errors = report.has_errors()
    was_modified = sanitized != content
    unfixable = False

    # Check for unfixable errors (prohibited diagram types, structural issues)
    for finding in report.findings:
        if finding.severity == "ERROR" and finding.rule in (
            "PROHIBITED_TYPE", "DRAWIO_XML_INVALID", "SUBGRAPH_UNCLOSED", "SELF_LOOP"
        ):
            # These are structural issues — auto-sanitization may not fully fix them
            if finding.rule == "SELF_LOOP":
                # Self-loops need the agent to redesign the edge — we can't just remove it safely
                unfixable = True
            elif finding.rule == "PROHIBITED_TYPE":
                unfixable = True
            elif finding.rule == "DRAWIO_XML_INVALID":
                unfixable = True

    # Print report if there were findings
    if report.findings:
        error_count = sum(1 for f in report.findings if f.severity == "ERROR")
        warning_count = sum(1 for f in report.findings if f.severity == "WARNING")

        print(f"{'='*60}", file=sys.stderr)
        print(f"  DIAGRAM VALIDATION GATE — {source_name}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        print(f"  Type:      {file_type}", file=sys.stderr)
        print(f"  Errors:    {error_count}", file=sys.stderr)
        print(f"  Warnings:  {warning_count}", file=sys.stderr)
        print(f"  Modified:  {'YES — auto-corrected' if was_modified else 'NO'}", file=sys.stderr)
        print(f"  Unfixable: {'YES — agent must regenerate' if unfixable else 'NO'}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        for f in report.findings:
            print(f"  [{f.severity}] {f.rule} (line {f.line})", file=sys.stderr)
            print(f"    {f.message}", file=sys.stderr)
            if f.original:
                print(f"    Before: {f.original[:100]}", file=sys.stderr)
            if f.fixed:
                print(f"    After:  {f.fixed[:100]}", file=sys.stderr)
            print(file=sys.stderr)

    # Decision: write or reject
    if unfixable:
        print(f"FAIL: {source_name} — unfixable errors detected. Agent MUST regenerate content.", file=sys.stderr)
        # Still output the sanitized content to stdout so agent can see what was attempted
        print(sanitized)
        sys.exit(1)

    if args.output:
        # Ensure output directory exists
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write sanitized content
        out_path.write_text(sanitized, encoding="utf-8", newline="\n" if file_type == "mmd" else None)

        if was_modified:
            print(f"FIXED: {args.output} — auto-corrected {len(report.findings)} issue(s) and written to disk.", file=sys.stderr)
            sys.exit(2)
        else:
            print(f"PASS: {args.output} — clean, written to disk.", file=sys.stderr)
            sys.exit(0)
    else:
        # Validate-only mode — output sanitized content to stdout
        print(sanitized)
        if was_modified:
            print(f"FIXED: content had {len(report.findings)} issue(s) — auto-corrected version printed above.", file=sys.stderr)
            sys.exit(2)
        elif report.findings:
            print(f"WARN: content has {len(report.findings)} warning(s) but is valid.", file=sys.stderr)
            sys.exit(0)
        else:
            print("PASS: content is clean.", file=sys.stderr)
            sys.exit(0)


if __name__ == "__main__":
    main()
