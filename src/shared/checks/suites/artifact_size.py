"""
suites/artifact_size.py
=======================
Validates that artifact size events were recorded and surfaces them in CI.

Reads ``outputs/asis/logs/size-events.log`` — produced by LLM agents that
follow ``asis-diagnostic/shared/artifact-size-governance.md`` §3.

Functional requirements:
  FR-AS-001  Log absent → single OK (no size events occurred — valid state).
  FR-AS-002  Each WARN entry  → record as passed=True  (informational).
  FR-AS-003  Each BLOCK entry → record as passed=False (hard limit hit).
  FR-AS-004  Malformed lines  → record as passed=False (log integrity issue).
  FR-AS-005  Summary check: total WARN + BLOCK counts surfaced regardless of verbosity.

Log line format (defined in artifact-size-governance.md §3):
  {timestamp_iso} | {WARN|BLOCK} | {filename} | {size} KB | {soft|hard} {limit} KB | estratégia: {desc}
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

# Regex matching the log line format from governance §3
_LINE_RE = re.compile(
    r"^(?P<ts>\S+)\s*\|\s*(?P<level>WARN|BLOCK)\s*\|\s*(?P<file>[^|]+?)\s*\|"
    r"\s*(?P<size>[\d.]+)\s*KB\s*\|\s*(?P<threshold_desc>[^|]+?)\s*\|"
    r"\s*estrat[eé]gia:\s*(?P<strategy>.+)$",
    re.IGNORECASE,
)

_LOG_RELATIVE = Path("asis") / "logs" / "size-events.log"


class ArtifactSizeSuite:
    NAME = "artifact_size"

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx

    # ------------------------------------------------------------------ #
    # Public entry point                                                   #
    # ------------------------------------------------------------------ #

    def run(self, reporter: "Reporter") -> None:
        log_path = self.ctx.outputs_dir / _LOG_RELATIVE

        # FR-AS-001 — log absent is valid (no limits were hit)
        if not log_path.exists():
            reporter.record(
                self.NAME,
                "size-events.log",
                passed=True,
                detail="absent — no artifact size events recorded (all artifacts within limits)",
            )
            return

        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        warn_count = 0
        block_count = 0
        malformed_count = 0

        for lineno, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue  # skip blank lines

            m = _LINE_RE.match(line)

            if not m:
                # FR-AS-004 — malformed line
                malformed_count += 1
                reporter.record(
                    self.NAME,
                    f"size-events.log line {lineno}",
                    passed=False,
                    detail=f"malformed log entry — expected format: timestamp | WARN|BLOCK | file | size KB | threshold | estratégia: desc",
                )
                continue

            level = m.group("level").upper()
            filename = m.group("file").strip()
            size_kb = m.group("size").strip()
            threshold_desc = m.group("threshold_desc").strip()
            strategy = m.group("strategy").strip()
            detail = (
                f"{size_kb} KB > {threshold_desc} — estratégia: {strategy}"
            )

            if level == "WARN":
                # FR-AS-002 — soft limit informational
                warn_count += 1
                reporter.record(
                    self.NAME,
                    f"SIZE-WARN: {filename}",
                    passed=True,
                    detail=detail,
                )
            else:
                # FR-AS-003 — hard limit BLOCK
                block_count += 1
                reporter.record(
                    self.NAME,
                    f"SIZE-BLOCK: {filename}",
                    passed=False,
                    detail=detail,
                )

        # FR-AS-005 — summary always visible (passed only if zero BLOCKs and zero malformed)
        clean = block_count == 0 and malformed_count == 0
        reporter.record(
            self.NAME,
            "size-events summary",
            passed=clean,
            detail=(
                f"{warn_count} WARN (soft limit, handled) · "
                f"{block_count} BLOCK (hard limit, strategy applied) · "
                f"{malformed_count} malformed"
            ),
        )
