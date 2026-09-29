"""mermaid_playwright_gate.py — Playwright Mermaid Auto-Fix Quality Gate.

Public API
----------
    run_playwright_mermaid_gate(
        html_path:       Path,
        guardrails_path: Path | None = None,   # default: shared/mermaid-guardrails.md
        max_attempts:    int  = 3,
        timeout_ms:      int  = 15_000,
    ) -> MermaidGateResult

Spec: specs/040-mermaid-playwright-autofix/spec.md
      Sections 4–8, Clarifications Q1 (option B) + Q2 (option C).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default guardrails path: resolved from __file__ location
# mermaid_playwright_gate.py lives in:
#   src/modules/ava-fabric-agents/summary/utils/
# mermaid-guardrails.md lives in:
#   src/modules/ava-fabric-agents/shared/
# So: parents[1]=summary, parents[2]=ava-fabric-agents, then shared/
_DEFAULT_GUARDRAILS_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent / "shared" / "mermaid-guardrails.md"
)

# ---------------------------------------------------------------------------
# DOM element id → D.staticDiagrams key mapping
# (derived from renderAllDiagrams() in summary-template.html)
# ---------------------------------------------------------------------------
_ELEM_ID_TO_SD_KEY: dict[str, str] = {
    "diag-asis-arch-blueprint":  "asisArchBlueprint",
    "diag-c4ctx":                "c4ctx",
    "diag-c4cnt":                "c4cnt",
    "diag-c4comp":               "c4comp",
    "diag-class":                "class",
    "diag-comp":                 "comp",
    "diag-er":                   "er",
    "diag-tobe-c4":              "tobeC4",
    "diag-tobe-arch-blueprint":  "tobeArchBlueprint",
    # diag-tobe-c4ctx-detail shares source with diag-tobe-c4 (sd.tobeC4)
    "diag-tobe-c4ctx-detail":    "tobeC4",
    "diag-tobe-c4cnt":           "tobeC4cnt",
    "diag-tobe-c4comp":          "tobeC4comp",
    "diag-tobe-class":           "tobeClass",
    "diag-tobe-er":              "tobeEr",
    "diag-tobe-seq":             "tobeSeq",
    "diag-gantt":                "gantt",
    "diag-solution":             "solution",
    "diag-cleanarch":            "cleanarch",
    "diag-context-map":          "contextMap",
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FixRecord:
    """Audit trail entry for a single auto-correction applied to a diagram source."""
    guardrail_rule_violated: str
    before: str
    after: str
    timestamp: str   # ISO 8601


@dataclass
class DiagramResult:
    """Per-diagram probe + fix result."""
    diagram_id: str
    section: str | None
    source_file: str | None
    rendered: bool
    # status: "PASS" | "FIXED" | "FAIL_UNRESOLVED" | "EMPTY" | "TIMEOUT"
    status: str
    error_message: str | None
    fixes_applied: list[FixRecord] = field(default_factory=list)
    attempt_count: int = 0


@dataclass
class MermaidGateResult:
    """Aggregate result of the Mermaid Playwright gate run."""
    # overall_status: "PASS" | "PASS_WITH_FIXES" | "FAIL" | "SKIPPED" | "DISABLED"
    overall_status: str
    total_diagrams: int
    total_valid: int
    total_fixed: int
    total_unresolved: int
    diagrams: list[DiagramResult]
    generated_at: str   # ISO 8601
    schema_version: str = "1.0"
    html_path: str = ""


# ---------------------------------------------------------------------------
# Browser discovery (delegates to render_blueprint_compatibility when available)
# ---------------------------------------------------------------------------


def _discover_browser_executable() -> str | None:
    """Return a path to a usable Chromium executable, or None.

    Imports ``discover_browser_executable`` from ``render_blueprint_compatibility``
    to reuse the exact same discovery logic (no duplication).  Falls back to an
    inline copy if that module is not importable (e.g. in isolated tests).
    """
    try:
        from render_blueprint_compatibility import discover_browser_executable  # type: ignore
        return discover_browser_executable()
    except ImportError:
        pass

    # Inline fallback (mirrors render_blueprint_compatibility.discover_browser_executable)
    executable: str | None = shutil.which("playwright")
    if not executable:
        ms_playwright = Path.home() / "AppData/Local/ms-playwright"
        for chrome_exe in sorted(ms_playwright.glob("chromium-*/chrome-win64/chrome.exe"), reverse=True):
            if chrome_exe.is_file():
                return str(chrome_exe)
    if not executable:
        _repo_root = Path(__file__).resolve().parents[5]
        for candidate in [
            _repo_root / "fastqa" / "node_modules" / ".bin" / "playwright",
            _repo_root / "fastqa" / "node_modules" / ".bin" / "playwright.cmd",
            _repo_root / "node_modules" / ".bin" / "playwright",
            _repo_root / "node_modules" / ".bin" / "playwright.cmd",
        ]:
            if candidate.is_file():
                return str(candidate)
    return executable or None


# ---------------------------------------------------------------------------
# D.staticDiagrams extraction and patching
# ---------------------------------------------------------------------------

# Matches the staticDiagrams JSON blob inside the HTML <script> block.
# The blob is followed by either "drawioFiles" or "diag" (both separators seen
# across template versions).
_SD_PATTERN = re.compile(
    r"(staticDiagrams:\s*)(\{.*?\})(\s*,\s*(?:drawioFiles|diag)\b)",
    re.DOTALL,
)


def _extract_static_diagrams(html: str) -> dict[str, Any]:
    """Extract D.staticDiagrams JSON dict from the HTML string.  Returns {} on failure."""
    m = _SD_PATTERN.search(html)
    if not m:
        return {}
    try:
        return json.loads(m.group(2))
    except (json.JSONDecodeError, ValueError):
        return {}


def _patch_static_diagrams(html: str, sd: dict[str, Any]) -> str:
    """Replace D.staticDiagrams in the HTML with the updated dict.

    Preserves the surrounding template syntax (the prefix and trailing separator).
    """
    def _replacer(m: re.Match) -> str:
        return m.group(1) + json.dumps(sd, ensure_ascii=False) + m.group(3)

    return _SD_PATTERN.sub(_replacer, html, count=1)


# ---------------------------------------------------------------------------
# Correction rules GR-001 to GR-012
# ---------------------------------------------------------------------------

_GRAPH_BARE      = re.compile(r"^(\s*)graph\s*$",                     re.MULTILINE)
_GRAPH_DIRECTION = re.compile(r"^(\s*)graph\s+(TD|LR|RL|BT|TB|UD)\b", re.MULTILINE)
_MULTI_LINE_LABEL = re.compile(r'(\[")(.*?)("\])',                     re.DOTALL)
_SUBGRAPH_LINE   = re.compile(r"^\s*subgraph\b",                       re.MULTILINE)
_END_LINE        = re.compile(r"^\s*end\b",                            re.MULTILINE)
_CURLY_QUOTES    = re.compile(r"[\u2018\u2019\u201c\u201d\u00ab\u00bb]")
# Chars not allowed inside node IDs (not inside labels/quotes)
_BAD_ID_CHARS    = re.compile(r"[~\u2192\u2014\u2013\u00a0\u200b\u200c\u200d`;\U0001F000-\U0001FFFF]")
# Node-ID at the start of a line followed by a bracket (declaration).
# \w is Unicode-aware in Python 3 (matches accented letters too), and
# hyphen is included so hyphenated/accented IDs are captured as a single
# token instead of silently failing to match (GR-005 gap, Round 1 I2a/I2b).
_NODE_DECL_RE    = re.compile(r"^[ \t]*([A-Za-z_][\w\-]*)[ \t]*[\[\(\{>]", re.MULTILINE)
# Node-ID in an edge: sequences of word chars separated by arrows.
# Supports an OPTIONAL edge label between the arrow and the destination
# node (e.g. `A -->|"Usa"| B`), which is the guardrails-recommended
# syntax for labelled edges and was previously invisible to this regex
# (Round 1 I3 gap — destination node silently excluded from
# `referenced`, allowing undeclared-node violations to escape GR-007).
_EDGE_RE         = re.compile(
    r"([A-Za-z_][A-Za-z0-9_\-]*)[ \t]*"
    r"(?:--+>?|==+>?|-\.-?>|o--|--o|<--+|x--+|--+x)"
    r"(?:\s*\|[^|]*\|)?"
    r"[ \t]*([A-Za-z_][A-Za-z0-9_\-]*)"
)
_SEQ_PARTICIPANT = re.compile(
    r"(^[ \t]*(?:participant|actor)[ \t]+)(.+?)(?=[ \t]*(?:as\b|$|\n))", re.MULTILINE
)
_STATE_WRONG_ARR = re.compile(r"(?<![=-])->(?!>)")   # single arrow -> (not -->) in stateDiagram_PK_FK_RE = re.compile(r"\bPK_FK\b")                  # invalid composite key modifier in erDiagram (GR-014)

def _apply_gr001(src: str) -> tuple[str, bool]:
    """GR-001: bare 'graph' keyword without direction → 'flowchart TD'."""
    new, n = _GRAPH_BARE.subn(r"\1flowchart TD", src)
    return new, n > 0


def _apply_gr002(src: str) -> tuple[str, bool]:
    """GR-002: 'graph TD/LR/RL/BT/TB' → 'flowchart <direction>'."""
    new, n = _GRAPH_DIRECTION.subn(r"\1flowchart \2", src)
    return new, n > 0


def _apply_gr003(src: str) -> tuple[str, bool]:
    """GR-003: multi-line labels inside [\\"...\\"] → join lines with <br/>."""
    def _join(m: re.Match) -> str:
        inner = m.group(2).replace("\n", "<br/>")
        return m.group(1) + inner + m.group(3)
    new, n = _MULTI_LINE_LABEL.subn(_join, src)
    return new, n > 0


def _apply_gr004(src: str) -> tuple[str, bool]:
    """GR-004: missing 'end' closing a subgraph — append as many 'end' lines as needed."""
    n_subgraph = len(_SUBGRAPH_LINE.findall(src))
    n_end      = len(_END_LINE.findall(src))
    if n_subgraph <= n_end:
        return src, False
    missing = n_subgraph - n_end
    new = src.rstrip("\n") + "\n" + ("end\n" * missing)
    return new, True


def _sanitize_node_id(raw_id: str) -> str:
    """ASCII-fold accented characters (á→a, ç→c, ã→a, ...), then replace
    any remaining character outside [A-Za-z0-9_] — including hyphen,
    space, and any other special character — with an underscore.
    Implements the guardrails rule: 'IDs de nós: somente [A-Za-z0-9_] —
    sem espaços, hífens, acentos ou caracteres especiais.'
    """
    folded = unicodedata.normalize("NFKD", raw_id)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9_]", "_", folded)


def _apply_gr005(src: str) -> tuple[str, bool]:
    """GR-005: prohibited characters in node IDs (hyphen, space, accents,
    and any other non [A-Za-z0-9_] character) → replaced with underscore
    or ASCII-folded. Only rewrites bare node IDs at the start of a
    non-quoted context.
    """
    changed = False

    def _fix_id(m: re.Match) -> str:
        nonlocal changed
        old_id = m.group(1)
        new_id = _sanitize_node_id(old_id)
        if new_id != old_id:
            changed = True
        prefix = src[m.start(): m.start(1)]
        suffix = src[m.end(1): m.end()]
        return prefix + new_id + suffix

    new = _NODE_DECL_RE.sub(_fix_id, src)
    return new, changed


def _apply_gr006(src: str) -> tuple[str, bool]:
    """GR-006: typographic / curly quotes → straight double-quote."""
    new = _CURLY_QUOTES.sub('"', src)
    return new, new != src


def _apply_gr007(src: str) -> tuple[str, bool]:
    """GR-007: node ID referenced in an edge before any declaration — insert declarations.

    This is a best-effort heuristic limited to flowchart/graph diagram types.
    Inserts a plain ``ID[ID]`` declaration line immediately after the first line
    (the diagram-type declaration).
    """
    first_line = src.strip().split("\n")[0].strip()
    if not first_line.startswith(("flowchart", "graph")):
        return src, False

    declared:   set[str] = set()
    referenced: set[str] = set()

    for m in _NODE_DECL_RE.finditer(src):
        declared.add(m.group(1))

    for m in _EDGE_RE.finditer(src):
        referenced.add(m.group(1))
        referenced.add(m.group(2))

    # Remove the diagram-type keyword itself from the set
    diagram_kw = first_line.split()[0]
    referenced.discard(diagram_kw)

    undeclared = referenced - declared
    if not undeclared:
        return src, False

    decl_block = "\n".join(f"    {nid}[{nid}]" for nid in sorted(undeclared))
    parts = src.split("\n", 1)
    new = parts[0] + "\n" + decl_block + "\n" + (parts[1] if len(parts) > 1 else "")
    return new, True


def _apply_gr008(src: str) -> tuple[str, bool]:
    """GR-008: more than 2 levels of nested subgraphs — flatten 3rd+ levels.

    Replaces deeply nested 'subgraph' keyword with a comment prefix and
    suppresses the corresponding 'end', effectively flattening to depth 2.
    """
    lines   = src.splitlines(keepends=True)
    depth   = 0
    result  = []
    changed = False
    suppressed_ends = 0

    for line in lines:
        stripped = line.strip()
        if re.match(r"subgraph\b", stripped):
            depth += 1
            if depth > 2:
                changed = True
                suppressed_ends += 1
                result.append(re.sub(r"(subgraph\b)", r"%% [FLATTENED] \1", line, count=1))
                continue
        elif re.match(r"end\b", stripped):
            if suppressed_ends > 0:
                suppressed_ends -= 1
                changed = True
                continue
            depth = max(0, depth - 1)
        result.append(line)

    return "".join(result), changed


def _apply_gr009(src: str) -> tuple[str, bool]:
    """GR-009: C4 macro calls inside a graph/flowchart diagram — add review flag.

    Detects when C4 macros (Person, System, Container, …) are used inside a
    graph/flowchart, indicating the diagram type should be C4Context/C4Container.
    Adds a leading review comment; the diagram may still fail to render.
    """
    first = src.strip().split("\n")[0].strip()
    c4_macros = any(
        kw in src
        for kw in ("Person(", "System(", "SystemDb(", "Container(", "Component(", "C4Context", "C4Container")
    )
    uses_graph = first.startswith(("graph ", "flowchart "))
    if c4_macros and uses_graph:
        flag = "%% [NEEDS REVIEW: use C4Context/C4Container/C4Component macros instead of graph/flowchart]\n"
        if flag not in src:
            return flag + src, True
    return src, False


def _apply_gr010(src: str) -> tuple[str, bool]:
    """GR-010: sequenceDiagram participant names with prohibited characters — sanitize."""
    lines = src.split("\n", 1)
    if not lines[0].strip().startswith("sequenceDiagram"):
        return src, False

    changed = [False]
    name_map: dict[str, str] = {}

    def _sanitize(m: re.Match) -> str:
        kw   = m.group(1)
        name = m.group(2).strip()
        safe = re.sub(r"[^A-Za-z0-9_\- ]", "_", name)
        if safe != name:
            name_map[name] = safe
            changed[0] = True
            return f"{kw}{safe}"
        return m.group(0)

    new = _SEQ_PARTICIPANT.sub(_sanitize, src)
    for old, safe in name_map.items():
        new = new.replace(old, safe)
    return new, changed[0]


def _apply_gr011(src: str) -> tuple[str, bool]:
    """GR-011: single-arrow '->' in stateDiagram-v2 → double-arrow '-->'."""
    first = src.strip().split("\n")[0].strip()
    if "stateDiagram" not in first:
        return src, False
    new = _STATE_WRONG_ARR.sub("-->", src)
    return new, new != src

_ER_BLOCK_JOIN = re.compile(r"^\}\n(?=\w+\s*\{)", re.MULTILINE)


def _apply_gr012(src: str) -> tuple[str, bool]:
    """GR-012: empty or whitespace-only diagram source → placeholder."""
    if not src or not src.strip():
        return "flowchart LR\n    A[No diagram data]", True
    return src, False


def _apply_gr013(src: str) -> tuple[str, bool]:
    """GR-013: erDiagram — entity blocks must be separated by blank line.

    Mermaid v11+ requires ``}ENTITY {`` → ``}\n\nENTITY {``.
    When entity blocks are concatenated without a blank line the parser
    emits ``Expecting 'ATTRIBUTE_WORD', got 'BLOCK_STOP'``.
    """
    first = src.strip().split("\n")[0].strip()
    if "erDiagram" not in first:
        return src, False
    new = _ER_BLOCK_JOIN.sub("}\n\n", src)
    return new, new != src


def _apply_gr014(src: str) -> tuple[str, bool]:
    """GR-014: erDiagram — replace invalid PK_FK modifier with PK.

    Mermaid v11 erDiagram grammar only recognises ``PK`` and ``FK`` as
    standalone attribute modifiers.  ``PK_FK`` is rejected by the lexer,
    causing a cascade parse error that hides the underlying problem.
    """
    first = src.strip().split("\n")[0].strip()
    if "erDiagram" not in first:
        return src, False
    new, count = _PK_FK_RE.subn("PK", src)
    return new, count > 0


# Ordered correction rules (applied in this sequence per spec Section 6)
_CORRECTION_RULES: list[tuple[str, Any]] = [
    ("GR-012", _apply_gr012),
    ("GR-006", _apply_gr006),
    ("GR-014", _apply_gr014),   # must run before GR-013 on first pass
    ("GR-013", _apply_gr013),   # structural erDiagram fix (before syntax rules)
    ("GR-001", _apply_gr001),
    ("GR-002", _apply_gr002),
    ("GR-003", _apply_gr003),
    ("GR-004", _apply_gr004),
    ("GR-005", _apply_gr005),
    ("GR-007", _apply_gr007),
    ("GR-008", _apply_gr008),
    ("GR-009", _apply_gr009),
    ("GR-010", _apply_gr010),
    ("GR-011", _apply_gr011),
]


def _apply_corrections(source: str) -> tuple[str, list[FixRecord]]:
    """Apply all correction rules in priority order.

    Returns ``(corrected_source, [FixRecord, …])``.
    Each FixRecord records the rule that triggered, plus before/after/timestamp.
    """
    current = source
    fixes: list[FixRecord] = []
    for rule_id, fn in _CORRECTION_RULES:
        new, changed = fn(current)
        if changed:
            fixes.append(FixRecord(
                guardrail_rule_violated=rule_id,
                before=current,
                after=new,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
            current = new
    return current, fixes


# ---------------------------------------------------------------------------
# Browser probe runner
# ---------------------------------------------------------------------------


def _run_gate_probe(html_path: Path, browser_exe: str, timeout_ms: int) -> list[dict]:
    """Run gate_mermaid_probe.js and return its 'diagrams' list.

    Returns an empty list on any failure (node missing, script missing, timeout,
    JSON parse error).  Callers treat an empty list as "no diagrams found / PASS".
    """
    node = shutil.which("node")
    gate_script = Path(__file__).with_name("gate_mermaid_probe.js")
    if not node or not gate_script.is_file():
        return []

    output_path = html_path.with_suffix(".gate-probe.json")
    probe_timeout_s = max(timeout_ms // 1000 + 30, 60)

    try:
        completed = subprocess.run(
            [node, str(gate_script), str(html_path), str(output_path), browser_exe, str(timeout_ms)],
            capture_output=True,
            text=True,
            check=False,
            timeout=probe_timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return []

    # Parse the JSON emitted on stdout (last non-empty line that starts with '{')
    for line in reversed(completed.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line).get("diagrams", [])
            except (json.JSONDecodeError, ValueError):
                pass

    # Fall back to the output file
    try:
        if output_path.is_file():
            return json.loads(output_path.read_text(encoding="utf-8")).get("diagrams", [])
    except (json.JSONDecodeError, OSError):
        pass

    return []


# ---------------------------------------------------------------------------
# Report serialisation helpers
# ---------------------------------------------------------------------------


def _result_as_dict(result: MermaidGateResult) -> dict:
    return {
        "schema_version":   result.schema_version,
        "generated_at":     result.generated_at,
        "html_path":        result.html_path,
        "overall_status":   result.overall_status,
        "total_diagrams":   result.total_diagrams,
        "total_valid":      result.total_valid,
        "total_fixed":      result.total_fixed,
        "total_unresolved": result.total_unresolved,
        "diagrams": [
            {
                "diagram_id":    d.diagram_id,
                "section":       d.section,
                "source_file":   d.source_file,
                "rendered":      d.rendered,
                "status":        d.status,
                "error_message": d.error_message,
                "attempt_count": d.attempt_count,
                "fixes_applied": [
                    {
                        "guardrail_rule_violated": f.guardrail_rule_violated,
                        "before":    f.before,
                        "after":     f.after,
                        "timestamp": f.timestamp,
                    }
                    for f in d.fixes_applied
                ],
            }
            for d in result.diagrams
        ],
    }


def _write_report_json(result: MermaidGateResult, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "mermaid-validation-report.json").write_text(
        json.dumps(_result_as_dict(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_report_md(result: MermaidGateResult, report_dir: Path) -> None:
    STATUS_ICON = {
        "PASS":           "✅",
        "FIXED":          "✅",
        "FAIL_UNRESOLVED":"❌",
        "EMPTY":          "⬜",
        "TIMEOUT":        "⚠️",
        "FAIL":           "❌",
    }
    lines = [
        "# Mermaid Validation Report",
        "",
        f"**Status**: `{result.overall_status}`  ",
        f"**Generated**: {result.generated_at}  ",
        f"**HTML**: `{result.html_path}`  ",
        f"**Diagrams total**: {result.total_diagrams} | "
        f"**Valid**: {result.total_valid} | "
        f"**Fixed**: {result.total_fixed} | "
        f"**Unresolved**: {result.total_unresolved}",
        "",
    ]

    if result.overall_status == "DISABLED":
        lines.append(
            "> Gate was disabled via `--skip-mermaid-gate`. No diagrams were probed."
        )
    elif result.overall_status == "SKIPPED":
        lines.append(
            "> Gate was skipped because Chromium is unavailable in this environment."
        )
    else:
        for d in result.diagrams:
            icon = STATUS_ICON.get(d.status, "❓")
            lines.append(f"## {icon} `{d.diagram_id}` — {d.status}")
            if d.error_message:
                lines.append(f"> **Error**: {d.error_message}")
            if d.attempt_count:
                lines.append(f"> Attempts: {d.attempt_count}")
            for fx in d.fixes_applied:
                lines.append(f"")
                lines.append(f"### Fix: {fx.guardrail_rule_violated} at {fx.timestamp}")
                before_snip = fx.before[:300] + "…" if len(fx.before) > 300 else fx.before
                after_snip  = fx.after[:300]  + "…" if len(fx.after)  > 300 else fx.after
                lines.append(f"**Before**:\n```\n{before_snip}\n```")
                lines.append(f"**After**:\n```\n{after_snip}\n```")
            lines.append("")

    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "mermaid-validation-report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Helper: DISABLED / SKIPPED sentinel results
# ---------------------------------------------------------------------------


def _make_disabled_result(html_path: Path) -> MermaidGateResult:
    return MermaidGateResult(
        overall_status="DISABLED",
        total_diagrams=0,
        total_valid=0,
        total_fixed=0,
        total_unresolved=0,
        diagrams=[],
        generated_at=datetime.now(timezone.utc).isoformat(),
        html_path=str(html_path),
    )


def _make_skipped_result(html_path: Path) -> MermaidGateResult:
    return MermaidGateResult(
        overall_status="SKIPPED",
        total_diagrams=0,
        total_valid=0,
        total_fixed=0,
        total_unresolved=0,
        diagrams=[],
        generated_at=datetime.now(timezone.utc).isoformat(),
        html_path=str(html_path),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_playwright_mermaid_gate(
    html_path: Path,
    guardrails_path: Path | None = None,
    max_attempts: int = 3,
    timeout_ms: int = 15_000,
) -> MermaidGateResult:
    """Run the Playwright Mermaid gate on a Summary HTML file.

    Parameters
    ----------
    html_path:
        Absolute path to the Summary HTML file to validate.
    guardrails_path:
        Path to ``mermaid-guardrails.md`` (currently INFORMATIONAL ONLY — accepted for
        forward-compatibility and testability, but not read or parsed at runtime; the
        correction ruleset is hardcoded in the ``_apply_grXXX`` functions below and must
        be kept manually in sync with ``mermaid-guardrails.md``). Defaults to
        ``src/modules/ava-fabric-agents/shared/mermaid-guardrails.md`` (Clarification Q1,
        Option B).
    max_attempts:
        Maximum number of probe→fix→re-probe cycles before marking a diagram
        ``FAIL_UNRESOLVED``.
    timeout_ms:
        Browser rendering timeout in milliseconds (default 15 000).

    Returns
    -------
    MermaidGateResult with ``overall_status`` one of:
        ``"PASS"``           — all diagrams rendered without intervention.
        ``"PASS_WITH_FIXES"``— all diagrams OK after auto-correction.
        ``"FAIL"``           — ≥1 diagram unresolved after *max_attempts*.
        ``"SKIPPED"``        — Chromium unavailable; WARNING emitted to stderr.
        ``"DISABLED"``       — caller opted out (should not call this function;
                               use the *skip_mermaid_gate* flag on callers).

    Isolation guarantee (RF8 / Scenario 5)
    ----------------------------------------
    Writes ONLY to ``<html_path.parent>/mermaid-validation-report.{json,md}``
    and to the *html_path* itself (only when fixes are applied).  Never writes
    outside ``projects/{project_name}/outputs/summary/``.  Source ``.mmd`` files
    and all other outputs directories remain read-only throughout.
    """
    if guardrails_path is None:
        guardrails_path = _DEFAULT_GUARDRAILS_PATH

    html_path  = Path(html_path).resolve()
    report_dir = html_path.parent

    # ── 1. Discover browser ─────────────────────────────────────────────────
    browser_exe = _discover_browser_executable()
    if not browser_exe:
        result = _make_skipped_result(html_path)
        _write_report_json(result, report_dir)
        _write_report_md(result, report_dir)
        # WARNING is reserved for Scenario 4 (Chromium absent), never for DISABLED
        print(
            "WARNING: playwright-gate skipped (chromium unavailable)",
            file=sys.stderr,
        )
        return result

    # ── 2. Initial probe ────────────────────────────────────────────────────
    probe_results = _run_gate_probe(html_path, browser_exe, timeout_ms)

    if not probe_results:
        # Probe ran but returned no diagram elements (empty page or no mermaid blocks)
        result = MermaidGateResult(
            overall_status="PASS",
            total_diagrams=0,
            total_valid=0,
            total_fixed=0,
            total_unresolved=0,
            diagrams=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
            html_path=str(html_path),
        )
        _write_report_json(result, report_dir)
        _write_report_md(result, report_dir)
        return result

    # ── 3. Build initial DiagramResult objects ──────────────────────────────
    diagram_results: dict[str, DiagramResult] = {}
    for p in probe_results:
        diag_id  = p.get("diagram_id") or ""
        rendered = bool(p.get("rendered"))
        raw_status = p.get("status", "")

        if raw_status == "EMPTY":
            status = "EMPTY"
        elif rendered:
            status = "PASS"
        else:
            status = "FAIL"

        dr = DiagramResult(
            diagram_id    = diag_id,
            section       = p.get("section"),
            source_file   = p.get("data_src"),
            rendered      = rendered,
            status        = status,
            error_message = p.get("error_message"),
            attempt_count = 1,
        )
        diagram_results[diag_id] = dr

    # ── 4. Load HTML + extract D.staticDiagrams ─────────────────────────────
    html_content = html_path.read_text(encoding="utf-8")
    sd           = _extract_static_diagrams(html_content)

    # ── 5. Auto-correction loop ──────────────────────────────────────────────
    failing_ids = [did for did, dr in diagram_results.items() if dr.status == "FAIL"]

    if failing_ids and sd:
        attempt = 1
        while attempt <= max_attempts and failing_ids:
            corrected_any  = False
            corrected_keys: set[str] = set()
            # I4 fix (Round 1/2): track which diagram_id "owns" each sd_key
            # fix in this pass, so sibling diagram_ids sharing the same
            # sd_key (e.g. diag-tobe-c4 / diag-tobe-c4ctx-detail → tobeC4)
            # get the SAME FixRecord list propagated into their own
            # fixes_applied, instead of being left with an empty audit trail
            # despite ending up with status == "FIXED".
            corrected_owner: dict[str, str] = {}

            for diag_id in list(failing_ids):
                sd_key = _ELEM_ID_TO_SD_KEY.get(diag_id)

                if not sd_key or sd_key not in sd:
                    # No known mapping to D.staticDiagrams → cannot auto-correct
                    diagram_results[diag_id].status = "FAIL_UNRESOLVED"
                    failing_ids.remove(diag_id)
                    continue

                if sd_key in corrected_keys:
                    # Already patched in this pass by a sibling diagram_id —
                    # propagate its audit trail here so this diagram's
                    # fixes_applied is never left empty when it later ends
                    # up FIXED.
                    owner_id = corrected_owner.get(sd_key)
                    if owner_id and owner_id in diagram_results:
                        diagram_results[diag_id].fixes_applied.extend(
                            diagram_results[owner_id].fixes_applied
                        )
                        diagram_results[diag_id].attempt_count = attempt
                    continue

                original_src   = sd[sd_key]
                corrected_src, fixes = _apply_corrections(original_src)

                if fixes and corrected_src != original_src:
                    sd[sd_key] = corrected_src
                    corrected_keys.add(sd_key)
                    corrected_owner[sd_key] = diag_id
                    corrected_any = True
                    dr = diagram_results[diag_id]
                    dr.fixes_applied.extend(fixes)
                    dr.attempt_count = attempt
                else:
                    # No rule produced a change → diagram cannot be auto-corrected
                    diagram_results[diag_id].status = "FAIL_UNRESOLVED"
                    failing_ids.remove(diag_id)

            if corrected_any:
                # Patch HTML and persist before re-probing
                html_content = _patch_static_diagrams(html_content, sd)
                html_path.write_text(html_content, encoding="utf-8")

                attempt += 1
                re_probe     = _run_gate_probe(html_path, browser_exe, timeout_ms)
                re_probe_map = {p.get("diagram_id", ""): p for p in (re_probe or [])}

                still_failing: list[str] = []
                for diag_id in list(failing_ids):
                    probe_entry = re_probe_map.get(diag_id)
                    if probe_entry and probe_entry.get("rendered"):
                        diagram_results[diag_id].status   = "FIXED"
                        diagram_results[diag_id].rendered = True
                    else:
                        still_failing.append(diag_id)
                failing_ids = still_failing
            else:
                # Nothing correctable remains → exit loop
                break

    # ── 6. After max_attempts — mark remaining failures as FAIL_UNRESOLVED ──
    for diag_id in failing_ids:
        dr = diagram_results[diag_id]
        dr.status        = "FAIL_UNRESOLVED"
        dr.attempt_count = max(dr.attempt_count, max_attempts)
        # Replace source with a visible placeholder so the report renders
        sd_key = _ELEM_ID_TO_SD_KEY.get(diag_id)
        if sd_key and sd_key in sd:
            placeholder = (
                f'flowchart LR\n    A["[INCOMPLETE - needs review: {diag_id}]"]'
            )
            sd[sd_key] = placeholder
            html_content = _patch_static_diagrams(html_content, sd)
            html_path.write_text(html_content, encoding="utf-8")

    # ── 7. Compute aggregate status ─────────────────────────────────────────
    diag_list       = list(diagram_results.values())
    total_valid     = sum(1 for d in diag_list if d.status in ("PASS", "FIXED", "EMPTY"))
    total_fixed     = sum(1 for d in diag_list if d.status == "FIXED")
    total_unresolved = sum(1 for d in diag_list if d.status == "FAIL_UNRESOLVED")

    if total_unresolved > 0:
        overall = "FAIL"
    elif total_fixed > 0:
        overall = "PASS_WITH_FIXES"
    else:
        overall = "PASS"

    result = MermaidGateResult(
        overall_status   = overall,
        total_diagrams   = len(diag_list),
        total_valid      = total_valid,
        total_fixed      = total_fixed,
        total_unresolved = total_unresolved,
        diagrams         = diag_list,
        generated_at     = datetime.now(timezone.utc).isoformat(),
        html_path        = str(html_path),
    )

    _write_report_json(result, report_dir)
    _write_report_md(result, report_dir)
    return result


# ---------------------------------------------------------------------------
# Helper for callers: write a DISABLED report without invoking Playwright
# ---------------------------------------------------------------------------


def write_disabled_report(html_path: Path) -> MermaidGateResult:
    """Write the mermaid-validation-report.{json,md} for a DISABLED gate run.

    Called by build_summary_comprehensive and remediate_summary when
    ``--skip-mermaid-gate`` is active.  Per spec (Q2=C): no WARNING, no browser
    launch; only informational record that the gate was opted-out.
    """
    result = _make_disabled_result(html_path)
    report_dir = Path(html_path).resolve().parent
    _write_report_json(result, report_dir)
    _write_report_md(result, report_dir)
    return result
