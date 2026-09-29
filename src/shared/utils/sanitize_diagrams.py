#!/usr/bin/env python3
"""
sanitize_diagrams.py — Post-generation sanitization for Mermaid (.mmd) and Draw.io (.drawio) artifacts.

Implements the "Protocolo de Sanitização Obrigatório" from mermaid-guardrails.md v1.4.0
and the "Protocolo de Sanitização Draw.io" from drawio-governance.md.

Mermaid target version: v11.14.0

Usage:
    # Validate only (dry-run) — reports issues without modifying files
    python sanitize_diagrams.py --project meu-erp --dry-run

    # Fix mode — applies sanitization and reports changes
    python sanitize_diagrams.py --project meu-erp

    # Specific directory
    python sanitize_diagrams.py --path /path/to/diagrams

    # Single file
    python sanitize_diagrams.py --file /path/to/diagram.mmd
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


# ─── Character Substitution Maps ──────────────────────────────────────────────

INVISIBLE_CHARS = {
    "\ufeff": "",      # BOM
    "\u200b": "",      # Zero-width space
    "\u200c": "",      # Zero-width non-joiner
    "\u200d": "",      # Zero-width joiner
    "\u00a0": " ",     # NBSP → regular space
}

PROHIBITED_SUBSTITUTIONS = {
    "\u2014": " - ",   # Em-dash → space-hyphen-space
    "\u2013": " - ",   # En-dash → space-hyphen-space
    "\u201c": '"',     # Left curly double quote
    "\u201d": '"',     # Right curly double quote
    "\u2018": "'",     # Left curly single quote
    "\u2019": "'",     # Right curly single quote
    "\u2192": " to ",  # Right arrow
    "\u2190": " from ",  # Left arrow
    "\u2194": " <--> ",  # Bidirectional arrow
    "\u21d2": " --> ",   # Double right arrow
    "\u2500": "-",     # Box-drawing horizontal
    "\u2502": "|",     # Box-drawing vertical
    "\u2022": "*",     # Bullet
}

# Box-drawing characters range (U+2500–U+257F)
BOX_DRAWING_RANGE = range(0x2500, 0x2580)

# Emoji ranges to strip
EMOJI_RANGES = [
    (0x1F000, 0x1FAFF),   # Various emoji blocks
    (0x1F600, 0x1F64F),   # Emoticons
    (0x1F300, 0x1F5FF),   # Misc Symbols & Pictographs
    (0x1F680, 0x1F6FF),   # Transport & Map
    (0x1F900, 0x1F9FF),   # Supplemental Symbols
    (0x1FA00, 0x1FA6F),   # Chess Symbols
    (0x1FA70, 0x1FAFF),   # Symbols Extended-A
    (0x2600, 0x27BF),     # Misc Symbols, Dingbats
    (0xFE00, 0xFE0F),     # Variation Selectors
    (0xE0020, 0xE007F),   # Tags
    (0x2702, 0x27B0),     # Dingbats
    (0x231A, 0x231B),     # Watch, Hourglass
    (0x23E9, 0x23F3),     # Various symbols
    (0x23F8, 0x23FA),     # Various symbols
    (0x25AA, 0x25AB),     # Small squares
    (0x25B6, 0x25B6),     # Play button
    (0x25C0, 0x25C0),     # Reverse button
    (0x25FB, 0x25FE),     # Medium squares
    (0x2614, 0x2615),     # Umbrella, Hot Beverage
    (0x2648, 0x2653),     # Zodiac
    (0x267F, 0x267F),     # Wheelchair
    (0x2693, 0x2693),     # Anchor
    (0x26A1, 0x26A1),     # High Voltage
    (0x26AA, 0x26AB),     # Circles
    (0x26BD, 0x26BE),     # Sports
    (0x26C4, 0x26C5),     # Snowman, Sun
    (0x26CE, 0x26CE),     # Ophiuchus
    (0x26D4, 0x26D4),     # No Entry
    (0x26EA, 0x26EA),     # Church
    (0x26F2, 0x26F3),     # Fountain, Golf
    (0x26F5, 0x26F5),     # Sailboat
    (0x26FA, 0x26FA),     # Tent
    (0x26FD, 0x26FD),     # Fuel Pump
    (0x2934, 0x2935),     # Arrows
    (0x2B05, 0x2B07),     # Arrows
    (0x2B1B, 0x2B1C),     # Squares
    (0x2B50, 0x2B50),     # Star
    (0x2B55, 0x2B55),     # Circle
    (0x3030, 0x3030),     # Wavy Dash
    (0x303D, 0x303D),     # Part Alternation Mark
    (0x3297, 0x3297),     # Circled Ideograph Congratulation
    (0x3299, 0x3299),     # Circled Ideograph Secret
]


@dataclass
class Finding:
    """Represents a single sanitization finding."""
    file: str
    line: int
    rule: str
    severity: str  # ERROR, WARNING
    message: str
    original: str = ""
    fixed: str = ""


@dataclass
class SanitizationReport:
    """Aggregated sanitization report."""
    files_scanned: int = 0
    files_with_issues: int = 0
    findings: list = field(default_factory=list)
    files_fixed: int = 0

    def add(self, finding: Finding):
        self.findings.append(finding)

    def has_errors(self) -> bool:
        return any(f.severity == "ERROR" for f in self.findings)

    def summary(self) -> str:
        errors = sum(1 for f in self.findings if f.severity == "ERROR")
        warnings = sum(1 for f in self.findings if f.severity == "WARNING")
        lines = [
            f"\n{'='*70}",
            f"  SANITIZATION REPORT",
            f"{'='*70}",
            f"  Files scanned:      {self.files_scanned}",
            f"  Files with issues:  {self.files_with_issues}",
            f"  Files fixed:        {self.files_fixed}",
            f"  Total findings:     {len(self.findings)}",
            f"    Errors:           {errors}",
            f"    Warnings:         {warnings}",
            f"{'='*70}",
        ]
        if self.findings:
            lines.append("\n  DETAILS:\n")
            for f in self.findings:
                lines.append(f"  [{f.severity}] {f.file}:{f.line} — {f.rule}")
                lines.append(f"    {f.message}")
                if f.original:
                    lines.append(f"    Before: {f.original[:120]}")
                if f.fixed:
                    lines.append(f"    After:  {f.fixed[:120]}")
                lines.append("")
        return "\n".join(lines)


def _is_emoji(char: str) -> bool:
    """Check if a character is an emoji."""
    cp = ord(char)
    for start, end in EMOJI_RANGES:
        if start <= cp <= end:
            return True
    return False


def _is_box_drawing(char: str) -> bool:
    """Check if a character is a box-drawing character."""
    return ord(char) in BOX_DRAWING_RANGE


def _strip_emojis(text: str) -> str:
    """Remove all emoji characters from text."""
    return "".join(c for c in text if not _is_emoji(c))


def _apply_invisible_removal(text: str) -> str:
    """Remove invisible/control characters."""
    for char, replacement in INVISIBLE_CHARS.items():
        text = text.replace(char, replacement)
    return text


def _apply_char_substitutions(text: str) -> str:
    """Apply prohibited character substitutions."""
    for char, replacement in PROHIBITED_SUBSTITUTIONS.items():
        text = text.replace(char, replacement)
    # Remove remaining box-drawing characters
    text = "".join(
        c if not _is_box_drawing(c) else ""
        for c in text
    )
    return text


def _collapse_spaces(text: str) -> str:
    """Collapse multiple consecutive spaces into one (preserving leading indentation)."""
    lines = text.split("\n")
    result = []
    for line in lines:
        # Preserve leading whitespace
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        # Collapse multiple spaces in the content part
        collapsed = re.sub(r"  +", " ", stripped)
        result.append(indent + collapsed)
    return "\n".join(result)


# ─── Mermaid-Specific Sanitization ────────────────────────────────────────────

def _detect_diagram_type(content: str) -> str:
    """Detect the Mermaid diagram type from content."""
    first_line = content.strip().split("\n")[0].strip()
    for dtype in [
        "flowchart", "sequenceDiagram", "classDiagram", "erDiagram",
        "gantt", "pie", "gitGraph", "stateDiagram-v2", "mindmap",
        "timeline", "journey", "quadrantChart",
        "C4Context", "C4Container", "C4Component", "C4Dynamic", "C4Deployment",
    ]:
        if first_line.startswith(dtype):
            return dtype
    return "unknown"


PROHIBITED_DIAGRAM_TYPES = {"graph", "stateDiagram", "xychart-beta", "block-beta",
                            "architecture-beta", "sankey-beta", "packet-beta", "zenuml"}


def _strip_code_fences(content: str) -> tuple:
    """Strip markdown code fences from .mmd content.

    Agents sometimes wrap mermaid content in ```mermaid ... ``` blocks.
    .mmd files MUST contain raw Mermaid syntax — never wrapped in markdown code blocks.

    Returns (stripped_content, was_stripped: bool).
    """
    stripped = content.strip()
    # Match ```mermaid\n...\n``` or ```\n...\n``` (whole content in a single fence)
    fence_pattern = re.compile(r"^```(?:mermaid)?\s*\n(.*?)\n\s*```\s*$", re.DOTALL)
    m = fence_pattern.match(stripped)
    if m:
        return m.group(1).strip(), True
    return content, False


def sanitize_mermaid(filepath: str, content: str, report: SanitizationReport, dry_run: bool) -> str:
    """Apply full Mermaid sanitization protocol."""
    original_content = content
    rel_path = os.path.basename(filepath)

    # Step 0: Strip markdown code fences — agents must never wrap .mmd in ```mermaid```
    content, was_fenced = _strip_code_fences(content)
    if was_fenced:
        report.add(Finding(
            file=rel_path, line=1, rule="CODE_FENCE_STRIPPED",
            severity="ERROR",
            message="File was wrapped in markdown code fence (```mermaid ... ```) — "
                    ".mmd files MUST contain raw Mermaid syntax, never a code block. Fence stripped.",
            original="```mermaid ... ```",
            fixed="(raw Mermaid content)",
        ))

    dtype = _detect_diagram_type(content)

    # Check prohibited diagram types
    if dtype in PROHIBITED_DIAGRAM_TYPES:
        report.add(Finding(
            file=rel_path, line=1, rule="PROHIBITED_TYPE",
            severity="ERROR",
            message=f"Prohibited diagram type '{dtype}' — use allowed equivalent",
        ))

    # Step 1: Remove invisible characters
    content = _apply_invisible_removal(content)

    # Step 2: Apply character substitutions
    content = _apply_char_substitutions(content)

    # Step 3: Remove emojis
    content_no_emoji = _strip_emojis(content)
    if content_no_emoji != content:
        # Find which lines had emojis
        old_lines = content.split("\n")
        new_lines = content_no_emoji.split("\n")
        for i, (old, new) in enumerate(zip(old_lines, new_lines), 1):
            if old != new:
                report.add(Finding(
                    file=rel_path, line=i, rule="EMOJI_REMOVED",
                    severity="ERROR",
                    message="Emoji(s) removed from line",
                    original=old.strip(),
                    fixed=new.strip(),
                ))
        content = content_no_emoji

    # Step 4: Validate \n in labels (flowchart / C4)
    if dtype.startswith("flowchart"):
        content = _fix_flowchart_newlines(content, rel_path, report)
    elif dtype.startswith("C4"):
        content = _fix_c4_newlines(content, rel_path, report)
    elif dtype == "gantt":
        content = _fix_gantt_issues(content, rel_path, report)
    elif dtype == "sequenceDiagram":
        content = _fix_sequence_participant_labels(content, rel_path, report)

    # Step 5: Validate node IDs and subgraph format (flowchart only)
    if dtype.startswith("flowchart"):
        _validate_subgraphs(content, rel_path, report)
        _validate_self_loops(content, rel_path, report)
        _validate_node_ids(content, rel_path, report)

    # Collapse double spaces introduced by emoji/char removal
    content = _collapse_spaces(content)

    # Report changes
    if content != original_content:
        if not dry_run:
            report.files_fixed += 1

    return content


def _fix_flowchart_newlines(content: str, rel_path: str, report: SanitizationReport) -> str:
    """Fix raw \\n in flowchart labels — replace with <br/> and ensure proper quoting."""
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines, 1):
        if "\\n" in line and not line.strip().startswith("%%"):
            # Check if \n is inside a label context (within [...], (...), etc.)
            # Match patterns like ID["label\ntext"] or ID[label\ntext]
            original = line

            # Replace \n with <br/> inside quoted labels ["..."]
            line = re.sub(
                r'(\["[^"]*?)\\n([^"]*?"\])',
                lambda m: m.group(1) + "<br/>" + m.group(2),
                line,
            )
            # Handle multiple \n in same label
            while "\\n" in line and re.search(r'\["[^"]*?\\n', line):
                line = re.sub(
                    r'(\["[^"]*?)\\n([^"]*?"\])',
                    lambda m: m.group(1) + "<br/>" + m.group(2),
                    line,
                )

            # Handle unquoted labels with \n: ID[text\nmore] → ID["text<br/>more"]
            def fix_unquoted_label(m):
                prefix = m.group(1)
                bracket_type = m.group(2)
                label_content = m.group(3)
                close_bracket = m.group(4)
                if "\\n" in label_content:
                    label_content = label_content.replace("\\n", "<br/>")
                    # Wrap in quotes if not already
                    if bracket_type == "[" and close_bracket == "]":
                        return f'{prefix}["{label_content}"]'
                    return f"{prefix}{bracket_type}{label_content}{close_bracket}"
                return m.group(0)

            line = re.sub(
                r'(\w+)(\[)([^\]"]+?\\n[^\]]*?)(\])',
                fix_unquoted_label,
                line,
            )

            if line != original:
                report.add(Finding(
                    file=rel_path, line=i, rule="RAW_NEWLINE_FIXED",
                    severity="ERROR",
                    message="Raw \\n replaced with <br/> in label",
                    original=original.strip(),
                    fixed=line.strip(),
                ))
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def _fix_c4_newlines(content: str, rel_path: str, report: SanitizationReport) -> str:
    """Remove \\n from C4 parameter strings — concatenate into single line."""
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines, 1):
        if "\\n" in line and not line.strip().startswith("%%"):
            original = line
            # In C4 parameters, \n should become " - " or just space
            line = line.replace("\\n", " ")
            if line != original:
                report.add(Finding(
                    file=rel_path, line=i, rule="C4_NEWLINE_REMOVED",
                    severity="ERROR",
                    message="\\n removed from C4 parameter string (causes silent browser failure)",
                    original=original.strip(),
                    fixed=line.strip(),
                ))
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def _fix_gantt_issues(content: str, rel_path: str, report: SanitizationReport) -> str:
    """Fix gantt-specific issues like em-dash in section names."""
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines, 1):
        original = line
        # Section names should not have em-dash (already handled by char substitution)
        # but validate task IDs
        task_match = re.match(r"^\s+\S.*?:(\S+),", line)
        if task_match:
            task_id = task_match.group(1)
            # Remove status prefixes for ID check
            for status in ("done,", "active,", "crit,"):
                if task_id.startswith(status):
                    task_id = task_id[len(status):]
                    break
            if task_id and not re.match(r"^[a-zA-Z0-9_]+$", task_id):
                report.add(Finding(
                    file=rel_path, line=i, rule="GANTT_TASK_ID",
                    severity="WARNING",
                    message=f"Task ID '{task_id}' contains invalid characters — should be [a-zA-Z0-9_]",
                ))
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def _fix_sequence_participant_labels(content: str, rel_path: str, report: SanitizationReport) -> str:
    """Fix invalid participant label syntax in sequenceDiagram.

    Rule: `participant X as LABEL [extra]` — `[extra]` after the label is
    parsed by the Mermaid v11 lexer as a bracket token, not part of the label,
    causing a parse error. Strip the bracket group.

    Also strips (extra) parenthetical suffixes that cause the same issue.
    """
    lines = content.split("\n")
    fixed_lines = []
    # Pattern: participant <id> as <label> followed by [text] or (text)
    participant_re = re.compile(
        r"^(\s*(?:participant|actor)\s+\S+\s+as\s+[^\[\(]+?)\s+([\[\(].+)$"
    )
    for i, line in enumerate(lines, 1):
        m = participant_re.match(line)
        if m:
            fixed = m.group(1).rstrip()
            report.add(Finding(
                file=rel_path, line=i, rule="SEQUENCE_PARTICIPANT_LABEL",
                severity="ERROR",
                message="Participant label has trailing bracket/parenthesis group — Mermaid v11 lexer "
                        "treats it as a syntax token, not label text. Trailing suffix removed.",
                original=line.strip(),
                fixed=fixed.strip(),
            ))
            fixed_lines.append(fixed)
        else:
            fixed_lines.append(line)
    return "\n".join(fixed_lines)


def _validate_subgraphs(content: str, rel_path: str, report: SanitizationReport) -> None:
    """Validate subgraph format and closure."""
    lines = content.split("\n")
    subgraph_stack = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("subgraph "):
            subgraph_stack.append((i, stripped))
            # Check format: subgraph ALIAS["Label"] vs subgraph "Label"
            rest = stripped[len("subgraph "):]
            if rest.startswith('"'):
                report.add(Finding(
                    file=rel_path, line=i, rule="SUBGRAPH_NO_ALIAS",
                    severity="ERROR",
                    message="subgraph without alias — use `subgraph ALIAS[\"Label\"]` format",
                    original=stripped,
                ))
        elif stripped == "end":
            if subgraph_stack:
                subgraph_stack.pop()

    # Check for unclosed subgraphs
    for line_num, sg in subgraph_stack:
        report.add(Finding(
            file=rel_path, line=line_num, rule="SUBGRAPH_UNCLOSED",
            severity="ERROR",
            message="subgraph opened but never closed with 'end'",
            original=sg,
        ))


def _validate_self_loops(content: str, rel_path: str, report: SanitizationReport) -> None:
    """Detect self-loops (A --> A)."""
    lines = content.split("\n")
    # Match patterns: A --> A, A -->|"label"| A, A -.-> A, etc.
    edge_pattern = re.compile(
        r"^\s*(\w+)\s+(?:-->|-.->|==>|--[ox]|-.-)(?:\|[^|]*\|)?\s+(\w+)"
    )
    for i, line in enumerate(lines, 1):
        m = edge_pattern.match(line)
        if m:
            source, target = m.group(1), m.group(2)
            if source == target:
                report.add(Finding(
                    file=rel_path, line=i, rule="SELF_LOOP",
                    severity="ERROR",
                    message=f"Self-loop detected: {source} → {target} — REMOVE this edge",
                    original=line.strip(),
                ))


def _validate_node_ids(content: str, rel_path: str, report: SanitizationReport) -> None:
    """Validate node IDs are [A-Za-z0-9_] only."""
    lines = content.split("\n")
    # Match node declarations: ID[...], ID(...), ID{...}, ID>...], ID(["..."])
    node_decl = re.compile(r"^\s*([A-Za-z0-9_\-]+)\s*[\[\(\{>]")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("%%", "subgraph", "end", "classDef", "class ", "style ",
                                "direction", "click", "linkStyle")):
            continue
        m = node_decl.match(stripped)
        if m:
            node_id = m.group(1)
            if not re.match(r"^[A-Za-z0-9_]+$", node_id):
                report.add(Finding(
                    file=rel_path, line=i, rule="INVALID_NODE_ID",
                    severity="ERROR",
                    message=f"Node ID '{node_id}' contains invalid characters — only [A-Za-z0-9_] allowed",
                    original=stripped[:80],
                ))


# ─── Draw.io-Specific Sanitization ───────────────────────────────────────────

DRAWIO_EDGE_REQUIRED_ATTRS = {
    "edgeStyle": "orthogonalEdgeStyle",
    "rounded": "1",
    "orthogonalLoop": "1",
    "jettySize": "auto",
    "html": "1",
    "jumpStyle": "arc",
}


def sanitize_drawio(filepath: str, content: str, report: SanitizationReport, dry_run: bool) -> str:
    """Apply Draw.io sanitization protocol."""
    original_content = content
    rel_path = os.path.basename(filepath)

    # Step 1: Remove invisible characters
    content = _apply_invisible_removal(content)

    # Step 2: Sanitize diagram name attributes
    content = _sanitize_drawio_names(content, rel_path, report)

    # Step 3: Sanitize value attributes
    content = _sanitize_drawio_values(content, rel_path, report)

    # Step 4: Validate edge governance
    _validate_drawio_edges(content, rel_path, report)

    # Step 5: Validate XML well-formedness
    _validate_xml_wellformedness(content, rel_path, report)

    if content != original_content:
        if not dry_run:
            report.files_fixed += 1

    return content


def _sanitize_drawio_names(content: str, rel_path: str, report: SanitizationReport) -> str:
    """Sanitize <diagram name="..."> attributes."""
    def fix_name(m):
        original_name = m.group(1)
        fixed_name = original_name
        # Apply character substitutions
        for char, replacement in PROHIBITED_SUBSTITUTIONS.items():
            fixed_name = fixed_name.replace(char, replacement)
        fixed_name = _strip_emojis(fixed_name)
        if fixed_name != original_name:
            report.add(Finding(
                file=rel_path, line=0, rule="DRAWIO_NAME_SANITIZED",
                severity="ERROR",
                message="Prohibited characters in <diagram name=\"...\">",
                original=original_name,
                fixed=fixed_name,
            ))
        return f'name="{fixed_name}"'

    content = re.sub(r'name="([^"]*)"', fix_name, content)
    return content


def _sanitize_drawio_values(content: str, rel_path: str, report: SanitizationReport) -> str:
    """Sanitize <mxCell value="..."> attributes — remove emojis and prohibited chars."""
    def fix_value(m):
        original_value = m.group(1)
        fixed_value = original_value
        # Remove emojis
        fixed_value = _strip_emojis(fixed_value)
        # Apply safe substitutions (not HTML-breaking ones)
        for char, replacement in PROHIBITED_SUBSTITUTIONS.items():
            # Skip replacements that would break HTML entities
            if char in ("\u2500", "\u2502"):
                fixed_value = fixed_value.replace(char, "")
            else:
                fixed_value = fixed_value.replace(char, replacement)
        if fixed_value != original_value:
            report.add(Finding(
                file=rel_path, line=0, rule="DRAWIO_VALUE_SANITIZED",
                severity="ERROR",
                message="Prohibited characters in <mxCell value=\"...\">",
                original=original_value[:100],
                fixed=fixed_value[:100],
            ))
        return f'value="{fixed_value}"'

    content = re.sub(r'value="([^"]*)"', fix_value, content)
    return content


def _validate_drawio_edges(content: str, rel_path: str, report: SanitizationReport) -> None:
    """Validate edge governance (Rule 1 from drawio-governance.md)."""
    # Find all edge cells
    edge_pattern = re.compile(r'<mxCell[^>]*edge="1"[^>]*style="([^"]*)"[^>]*/>')
    for m in edge_pattern.finditer(content):
        style = m.group(1)
        style_dict = dict(item.split("=", 1) for item in style.split(";") if "=" in item)

        for attr, expected in DRAWIO_EDGE_REQUIRED_ATTRS.items():
            actual = style_dict.get(attr)
            if actual is None:
                report.add(Finding(
                    file=rel_path, line=0, rule="DRAWIO_EDGE_MISSING_ATTR",
                    severity="WARNING",
                    message=f"Edge missing required attribute: {attr}={expected}",
                ))
            elif actual != expected:
                report.add(Finding(
                    file=rel_path, line=0, rule="DRAWIO_EDGE_WRONG_ATTR",
                    severity="WARNING",
                    message=f"Edge has {attr}={actual}, expected {attr}={expected}",
                ))


def _validate_xml_wellformedness(content: str, rel_path: str, report: SanitizationReport) -> None:
    """Validate that the Draw.io XML is well-formed."""
    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        report.add(Finding(
            file=rel_path, line=0, rule="DRAWIO_XML_INVALID",
            severity="ERROR",
            message=f"XML parse error: {e}",
        ))


# ─── File Discovery ──────────────────────────────────────────────────────────

def discover_files(base_path: str) -> tuple:
    """Discover .mmd and .drawio files under the given path."""
    mmd_files = []
    drawio_files = []

    for root, _, files in os.walk(base_path):
        for f in sorted(files):
            full_path = os.path.join(root, f)
            if f.endswith(".mmd"):
                mmd_files.append(full_path)
            elif f.endswith(".drawio"):
                drawio_files.append(full_path)

    return mmd_files, drawio_files


def resolve_project_path(project_name: str) -> str:
    """Resolve project outputs path from project name."""
    # Navigate from this script's location to the project outputs
    script_dir = Path(__file__).resolve().parent
    # Go up to imfai-ava-fabric-apps-agents root
    repo_root = script_dir.parent.parent.parent
    project_dir = repo_root / "projects" / project_name / "outputs"

    if not project_dir.exists():
        # Try case-insensitive match
        projects_dir = repo_root / "projects"
        if projects_dir.exists():
            for d in projects_dir.iterdir():
                if d.is_dir() and d.name.lower() == project_name.lower():
                    project_dir = d / "outputs"
                    break

    return str(project_dir)


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sanitize Mermaid (.mmd) and Draw.io (.drawio) diagram artifacts"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Project name (e.g., meu-erp, Meu-ERP)")
    group.add_argument("--path", help="Direct path to scan for diagram files")
    group.add_argument("--file", help="Single file to sanitize")

    parser.add_argument("--dry-run", action="store_true",
                        help="Report issues without modifying files")

    args = parser.parse_args()
    report = SanitizationReport()

    # Resolve target path
    if args.file:
        if not os.path.isfile(args.file):
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        if args.file.endswith(".mmd"):
            mmd_files = [args.file]
            drawio_files = []
        elif args.file.endswith(".drawio"):
            mmd_files = []
            drawio_files = [args.file]
        else:
            print(f"ERROR: Unsupported file type: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        if args.project:
            base_path = resolve_project_path(args.project)
        else:
            base_path = args.path

        if not os.path.isdir(base_path):
            print(f"ERROR: Directory not found: {base_path}", file=sys.stderr)
            sys.exit(1)

        mmd_files, drawio_files = discover_files(base_path)

    total_files = len(mmd_files) + len(drawio_files)
    report.files_scanned = total_files

    if total_files == 0:
        print("No .mmd or .drawio files found.")
        sys.exit(0)

    print(f"Found {len(mmd_files)} .mmd and {len(drawio_files)} .drawio files\n")

    # Process Mermaid files
    files_with_issues = set()
    for filepath in mmd_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        before_count = len(report.findings)
        sanitized = sanitize_mermaid(filepath, content, report, args.dry_run)
        after_count = len(report.findings)

        if after_count > before_count:
            files_with_issues.add(filepath)

        if sanitized != content and not args.dry_run:
            with open(filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write(sanitized)
            print(f"  FIXED: {os.path.basename(filepath)}")
        elif sanitized != content:
            print(f"  WOULD FIX: {os.path.basename(filepath)}")
        else:
            print(f"  OK: {os.path.basename(filepath)}")

    # Process Draw.io files
    for filepath in drawio_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        before_count = len(report.findings)
        sanitized = sanitize_drawio(filepath, content, report, args.dry_run)
        after_count = len(report.findings)

        if after_count > before_count:
            files_with_issues.add(filepath)

        if sanitized != content and not args.dry_run:
            with open(filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write(sanitized)
            print(f"  FIXED: {os.path.basename(filepath)}")
        elif sanitized != content:
            print(f"  WOULD FIX: {os.path.basename(filepath)}")
        else:
            print(f"  OK: {os.path.basename(filepath)}")

    report.files_with_issues = len(files_with_issues)
    print(report.summary())

    # Exit code: 1 if errors found (useful for CI)
    sys.exit(1 if report.has_errors() else 0)


if __name__ == "__main__":
    main()
