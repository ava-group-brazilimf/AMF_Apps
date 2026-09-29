"""
suites/evidence_capture.py
==========================
Validates artifacts produced by ava-qa-evidence-capture (v2.1.0+).

Checks applied:
  CHK-EC-001  evidence-capture-report.md exists and is non-empty
  CHK-EC-002  parity-dashboard.md exists and is non-empty
  CHK-EC-003  compliance-package/ directory exists
  CHK-EC-004  compliance-package/README.md exists and is non-empty
  CHK-EC-005  compliance-package/checklist.md exists and is non-empty
  CHK-EC-006  evidence-capture-package-index.md exists and is non-empty
  CHK-EC-007  At least one diff report (.md) exists in evidence-capture/diffs/
  CHK-EC-008  screenshots/index.md exists and is non-empty
  CHK-EC-009  logs/execution-summary.md exists and is non-empty
  CHK-EC-010  parity-dashboard.md contains a numeric parity score (e.g. "87.5%")
  CHK-EC-011  evidence-capture-report.md contains a compliance recommendation keyword
  CHK-EC-012  evidence-capture-package-index.md contains retention metadata header
  CHK-EC-013  evidence-capture-report.md contains PII scan status
  CHK-EC-014  screenshots/ contains at least one test runner output (.log or -test-summary.md)

Usage (standalone):
    python -m src.shared.checks --project Meu-ERP --suite evidence_capture

Usage (programmatic):
    from src.shared.checks.suites.evidence_capture import EvidenceCaptureSuite
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

# ── Paths (relative to outputs_dir) ─────────────────────────────────────────

_QA = Path("qa")
_EC = _QA / "evidence-capture"

_REPORT           = _QA / "evidence-capture-report.md"
_DASHBOARD        = _QA / "parity-dashboard.md"
_PACKAGE_INDEX    = _QA / "evidence-capture-package-index.md"
_COMPLIANCE_PKG   = _EC / "compliance-package"
_DIFFS_DIR        = _EC / "diffs"
_SCREENSHOTS_IDX  = _EC / "screenshots" / "index.md"
_LOGS_SUMMARY     = _EC / "logs" / "execution-summary.md"

# ── Patterns ─────────────────────────────────────────────────────────────────

# Matches patterns like "87%", "87.5%", "100%", "87,5%"
_PARITY_SCORE_RE = re.compile(r"\b\d{1,3}[.,]?\d*\s*%")

_RECOMMENDATION_KEYWORDS = frozenset({
    "APPROVED_FOR_ACCEPTANCE",
    "CONDITIONAL_APPROVAL",
    "BLOCKED_PENDING_REMEDIATION",
})

# Retention metadata keys that must appear in package-index
_RETENTION_KEYS = ("retention_policy", "expires_at", "created_at")

# PII scan status markers
_PII_STATUS_KEYWORDS = frozenset({
    "pii_scan_status",
    "PII redacted",
    "PII_SCAN_SKIPPED",
    "PII_REDACTED",
    "CLEAN",
})


class EvidenceCaptureSuite:
    NAME = "evidence_capture"

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx

    # ------------------------------------------------------------------ #
    # Public entry point                                                   #
    # ------------------------------------------------------------------ #

    def run(self, reporter: "Reporter") -> None:
        outputs = self.ctx.outputs_dir

        # CHK-EC-001
        self._check_file(reporter, outputs / _REPORT, "CHK-EC-001", "evidence-capture-report.md")

        # CHK-EC-002
        self._check_file(reporter, outputs / _DASHBOARD, "CHK-EC-002", "parity-dashboard.md")

        # CHK-EC-003 — compliance-package/ directory
        pkg_dir = outputs / _COMPLIANCE_PKG
        reporter.record(
            self.NAME,
            "CHK-EC-003 compliance-package/ directory",
            passed=pkg_dir.is_dir(),
            detail="OK" if pkg_dir.is_dir() else "directory not found",
        )

        # CHK-EC-004
        self._check_file(reporter, pkg_dir / "README.md", "CHK-EC-004", "compliance-package/README.md")

        # CHK-EC-005
        self._check_file(reporter, pkg_dir / "checklist.md", "CHK-EC-005", "compliance-package/checklist.md")

        # CHK-EC-006
        self._check_file(reporter, outputs / _PACKAGE_INDEX, "CHK-EC-006", "evidence-capture-package-index.md")

        # CHK-EC-007 — at least one diff report
        diffs_dir = outputs / _DIFFS_DIR
        diff_files = list(diffs_dir.glob("*.md")) if diffs_dir.is_dir() else []
        reporter.record(
            self.NAME,
            "CHK-EC-007 diff reports present",
            passed=len(diff_files) >= 1,
            detail=(
                f"{len(diff_files)} diff report(s) found"
                if diff_files
                else "no .md diff reports found in evidence-capture/diffs/"
            ),
        )

        # CHK-EC-008
        self._check_file(reporter, outputs / _SCREENSHOTS_IDX, "CHK-EC-008", "screenshots/index.md")

        # CHK-EC-009
        self._check_file(reporter, outputs / _LOGS_SUMMARY, "CHK-EC-009", "logs/execution-summary.md")

        # CHK-EC-010 — parity score numeric value in dashboard
        dashboard_path = outputs / _DASHBOARD
        if dashboard_path.exists():
            content = dashboard_path.read_text(encoding="utf-8", errors="replace")
            has_score = bool(_PARITY_SCORE_RE.search(content))
            reporter.record(
                self.NAME,
                "CHK-EC-010 numeric parity score in dashboard",
                passed=has_score,
                detail=(
                    "parity score (%) found"
                    if has_score
                    else "no numeric parity score pattern found in parity-dashboard.md"
                ),
            )

        # CHK-EC-011 — compliance recommendation keyword in report
        report_path = outputs / _REPORT
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8", errors="replace")
            found_kw = any(kw in content for kw in _RECOMMENDATION_KEYWORDS)
            reporter.record(
                self.NAME,
                "CHK-EC-011 compliance recommendation keyword",
                passed=found_kw,
                detail=(
                    "recommendation keyword found"
                    if found_kw
                    else (
                        "none of APPROVED_FOR_ACCEPTANCE | CONDITIONAL_APPROVAL | "
                        "BLOCKED_PENDING_REMEDIATION found in evidence-capture-report.md"
                    )
                ),
            )

        # CHK-EC-012 — retention metadata in package-index
        pkg_index_path = outputs / _PACKAGE_INDEX
        if pkg_index_path.exists():
            content = pkg_index_path.read_text(encoding="utf-8", errors="replace")
            has_retention = all(key in content for key in _RETENTION_KEYS)
            reporter.record(
                self.NAME,
                "CHK-EC-012 retention metadata in package-index",
                passed=has_retention,
                detail=(
                    "retention metadata header found"
                    if has_retention
                    else (
                        f"missing retention keys in evidence-capture-package-index.md "
                        f"(expected: {', '.join(_RETENTION_KEYS)})"
                    )
                ),
            )

        # CHK-EC-013 — PII scan status in report
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8", errors="replace")
            has_pii_status = any(kw in content for kw in _PII_STATUS_KEYWORDS)
            reporter.record(
                self.NAME,
                "CHK-EC-013 PII scan status in report",
                passed=has_pii_status,
                detail=(
                    "PII scan status found"
                    if has_pii_status
                    else "no PII scan status indicator found in evidence-capture-report.md"
                ),
            )

        # CHK-EC-014 — test runner output in screenshots/
        screenshots_dir = outputs / _EC / "screenshots"
        runner_outputs: list[Path] = []
        if screenshots_dir.is_dir():
            runner_outputs = (
                list(screenshots_dir.glob("*-test-output.log"))
                + list(screenshots_dir.glob("*-test-summary.md"))
            )
        reporter.record(
            self.NAME,
            "CHK-EC-014 test runner output in screenshots/",
            passed=len(runner_outputs) >= 1,
            detail=(
                f"{len(runner_outputs)} test runner output(s) found"
                if runner_outputs
                else (
                    "no *-test-output.log or *-test-summary.md found in "
                    "evidence-capture/screenshots/ (test runner may not have been available)"
                )
            ),
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _check_file(
        self,
        reporter: "Reporter",
        path: Path,
        check_id: str,
        label: str,
    ) -> None:
        if not path.exists():
            reporter.record(
                self.NAME,
                f"{check_id} {label}",
                passed=False,
                detail="file not found",
            )
            return
        size = path.stat().st_size
        reporter.record(
            self.NAME,
            f"{check_id} {label}",
            passed=size > 0,
            detail=f"{size} bytes" if size > 0 else "file is empty (0 bytes)",
        )
