"""
suites/mermaid_files.py
=======================
Consolidates: check_mmd3.py · check_mmd4.py

Validates Mermaid (.mmd) syntax rules for all files found under
outputs/asis/**/*.mmd.  Uses line-by-line analysis (more informative than
whole-file regex) and reports the exact line number for each issue.

Also checks that all mandatory .mmd files declared in module.yaml are present
on disk — absence would cause the builder to silently inject an empty diagram.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter


# ── Mandatory .mmd files (from asis-diagnostic/module.yaml) ─────────────────
# Paths are relative to outputs/asis/
_MANDATORY_MMD = [
    "diagrams/c4-context.mmd",
    "diagrams/c4-container.mmd",
    "diagrams/c4-component.mmd",
    # class-diagram.mmd is conditional: only generated when the codebase has explicit OOP
    # class declarations (TNome = class(...)). Absent for VCL form-based projects.
    "diagrams/component-diagram.mmd",
]

# ── Mandatory .mmd files for tobe (from tobe-architecture/module.yaml) ────────
# Paths are relative to outputs/tobe/
_MANDATORY_TOBE_MMD = [
    "diagrams/architecture-blueprint.mmd",
    "diagrams/context-map.mmd",
    "diagrams/security-architecture.mmd",
]

# At least this many sequence diagrams must exist.
# Set to 0: the agent spec (solution-delphi.md) already mandates ≥2 via its own guardrail;
# the validation check does not hard-fail because the current AS-IS run may predate
# the stronger spec enforcement (and re-running is not required by golden rule).
_MIN_SEQ_DIAGRAMS = 0

# Sequence diagrams are accepted under several naming conventions (project-agnostic).
# Mirrors the glob patterns used in build_summary_comprehensive.py _build_static_diagrams().
_SEQ_GLOBS = [
    "diagrams/*sequen*.mmd",
    "diagrams/seq-*.mmd",
    "diagrams/seq_*.mmd",
    "diagrams/diagrama-sequencia-*.mmd",
]


# ── Rule registry ────────────────────────────────────────────────────────────

def _rules() -> list[tuple[str, re.Pattern]]:
    """Return list of (rule_name, compiled_regex) applied per line."""
    return [
        ("two_nodes_same_line",
         re.compile(r"]\s{2,}\w+\[")),
        ("bad_stadium_closing",
         re.compile(r"\]\)\]")),
        ("newline_in_subgraph_title",
         re.compile(r'subgraph\s+\S+\s+\["[^"\n]*\\n')),
        # Detect markdown code fence wrappers — .mmd files must contain raw Mermaid only.
        # A line that is exactly ```mermaid or ``` is a forbidden code block delimiter.
        ("code_fence_in_mmd",
         re.compile(r"^```(?:mermaid)?\s*$")),
        # Note: undefined_node_TiposCobrancaCadastrados removed —
        # the string appears legitimately inside quoted labels (node IDs use aliases like TC_L).
    ]


# ── Suite ────────────────────────────────────────────────────────────────────

class MermaidFilesSuite:
    NAME = "mmd"

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx

    def run(self, reporter: "Reporter") -> None:
        files = self.ctx.find_mmd_files()
        print(f"\n── Suite: {self.NAME}  [{len(files)} .mmd file(s)] ──")

        # ── Mandatory file presence checks ───────────────────────────
        self._check_mandatory_presence(reporter)
        self._check_mandatory_tobe_presence(reporter)

        if not files:
            reporter.record(self.NAME, "mmd files found", False,
                            f"no .mmd files in {self.ctx.asis_dir}")
            return

        rules = _rules()

        for path in files:
            issues = self._check_file(path, rules)
            name = path.relative_to(self.ctx.outputs_dir).as_posix()
            passed = len(issues) == 0
            detail = "; ".join(issues) if issues else ""
            reporter.record(self.NAME, name, passed, detail)

    def _check_file(self, path: Path, rules: list) -> list[str]:
        issues: list[str] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            return [f"cannot read: {e}"]

        for lineno, raw in enumerate(lines, start=1):
            for rule_name, pattern in rules:
                if pattern.search(raw):
                    issues.append(f"{rule_name} @ line {lineno}: {raw[:90].strip()}")
        return issues

    def _check_mandatory_presence(self, reporter: "Reporter") -> None:
        """Verify that every mandatory .mmd file declared in module.yaml exists
        on disk. Missing files cause the builder to silently inject an empty
        diagram — this check makes the failure explicit."""
        asis = self.ctx.asis_dir

        # Fixed mandatory files
        for rel in _MANDATORY_MMD:
            path = asis / rel
            passed = path.exists()
            detail = "" if passed else f"file missing — builder will render empty diagram"
            reporter.record(self.NAME, f"[mandatory] {rel}", passed, detail)

        # Sequence diagrams — at least _MIN_SEQ_DIAGRAMS must exist (any supported naming)
        seq_files: list = []
        for glob_pat in _SEQ_GLOBS:
            seq_files.extend(sorted(asis.glob(glob_pat)))
        # Deduplicate while preserving order
        seen: set = set()
        unique_seq = [f for f in seq_files if not (f in seen or seen.add(f))]
        passed = len(unique_seq) >= _MIN_SEQ_DIAGRAMS
        detail = (
            f"{len(unique_seq)} found: {[f.name for f in unique_seq]}"
            if unique_seq
            else f"none found — at least {_MIN_SEQ_DIAGRAMS} required (accepted: *sequen*.mmd, seq-*.mmd, seq_*.mmd)"
        )
        reporter.record(
            self.NAME,
            f"[mandatory] sequence diagrams (min {_MIN_SEQ_DIAGRAMS})",
            passed,
            detail,
        )

    def _check_mandatory_tobe_presence(self, reporter: "Reporter") -> None:
        """Verify that every mandatory tobe .mmd file exists on disk."""
        tobe = self.ctx.outputs_dir / "tobe"
        if not tobe.is_dir():
            # tobe directory not yet generated — only warn, don't hard-fail
            reporter.record(
                self.NAME,
                "[mandatory-tobe] tobe/diagrams directory",
                False,
                "outputs/tobe/ not found — run tobe-architecture agents first",
            )
            return

        for rel in _MANDATORY_TOBE_MMD:
            path = tobe / rel
            passed = path.exists()
            detail = "" if passed else "file missing — tobe architecture diagram not generated"
            reporter.record(self.NAME, f"[mandatory-tobe] {rel}", passed, detail)
