"""
suites/ftm_traceability.py
==========================
Validates the Functional Test Matrix (FTM) against the AS-IS Behavior Catalog,
ensuring the traceability claim in the matrix header is always the real value.

Checks applied:
  CHK-FTM-001  FTM file exists          — outputs/qa/functional-test-matrix.md
  CHK-FTM-002  Behavior catalog exists  — outputs/qa/behavior-mapping/behavior-catalog.json
  CHK-FTM-003  Header TC count matches actual TC rows in the matrix
  CHK-FTM-004  Header BH coverage claim matches actual covered BHs / catalog total
  CHK-FTM-005  Every BH-ID in the catalog appears in at least one TC row
  CHK-FTM-006  Every RF in the catalog fr_to_bh_index has at least one TC row
  CHK-FTM-007  Integration TCs that reference a BH with a known "defect" field
               carry an AS-IS divergence footnote marker (¹)

Usage (standalone):
    python -m src.shared.checks --project Meu-ERP --suite ftm_traceability

Usage (programmatic):
    from src.shared.checks.suites.ftm_traceability import FtmTraceabilitySuite
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

# ── Regex helpers ─────────────────────────────────────────────────────────────

# Matches a TC table row and captures the "AS-IS Behavior Ref" column (column 7)
# Row format: | RF | Name | TC-ID | Scenario | Prio | Type | BH-refs | Status |
_TC_ROW = re.compile(
    r"^\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*([^|]+?)\s*\|\s*[^|]+\|",
    re.MULTILINE,
)

# Extracts individual BH-IDs from the "AS-IS Behavior Ref" cell
# Supports both simple (BH-001) and compound (BH-CS-001, BH-AP-002) ID formats
_BH_ID = re.compile(r"BH-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE)

# Matches the header line claiming total scenarios
# Example: > Total de cenários mapeados: 42
_HEADER_TC_COUNT = re.compile(r"Total de cen[aá]rios mapeados:\s*(\d+)")

# Matches the header line claiming BH coverage
# Example: 30/30 behaviors (100%)  or  26/30 behaviors (86,7%)
_HEADER_BH_COVERAGE = re.compile(r"(\d+)/(\d+)\s+behaviors")

# TC row: captures TC-ID (column 3) and test type (column 6)
# Supports both TC-001 and TC-CS-001 compound TC-ID formats
_TC_ROW_DETAIL = re.compile(
    r"^\|[^|]+\|[^|]+\|\s*(TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*\|[^|]+\|[^|]+\|\s*(\w+)\s*\|\s*([^|]+?)\s*\|\s*[^|]+\|",
    re.MULTILINE,
)

# Footnote divergence marker on a TC row
_FOOTNOTE_MARKER = re.compile(r"¹")

# Full TC row: captures RF-ID (col 1), TC-ID (col 3), priority (col 5),
# test type (col 6) and BH-refs cell (col 7)
# Supports compound FR-IDs (FR-CF-001) and TC-IDs (TC-CS-001)
_TC_ROW_FULL = re.compile(
    r"^\|\s*(FR-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)\s*\|[^|]*\|\s*(TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*\|[^|]*\|\s*(P[0-3])\s*\|\s*([\w/][\w\s/]*?)\s*\|\s*([^|]+?)\s*\|\s*[^|]+\|",
    re.MULTILINE,
)

# RF-ID in matrix column 1 **only on TC rows** (col3 must start with TC-).
# Deliberately excludes Gaps/other tables whose rows have fewer columns.
# Supports compound FR-IDs (FR-CF-001) and TC-IDs (TC-CS-001)
_RF_ID_IN_TC_ROW = re.compile(
    r"^\|\s*(FR-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)\s*\|[^|\n]*\|\s*TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\s*\|",
    re.MULTILINE,
)

_VALID_TEST_TYPES: frozenset[str] = frozenset(
    {"acceptance", "integration", "unit", "e2e", "smoke"}
)
_VALID_PRIORITIES: frozenset[str] = frozenset({"P0", "P1", "P2", "P3"})


class FtmTraceabilitySuite:
    NAME = "ftm_traceability"

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx
        self.ftm_path: Path = ctx.outputs_dir / "qa" / "functional-test-matrix.md"
        self.catalog_path: Path = (
            ctx.outputs_dir / "qa" / "behavior-mapping" / "behavior-catalog.json"
        )
        self.spec_docs_dir: Path = ctx.outputs_dir / "tobe" / "docs"

    # ------------------------------------------------------------------ #
    def run(self, reporter: "Reporter") -> None:
        print(f"\n-- Suite: {self.NAME} --")

        # CHK-FTM-001: FTM must exist — hard stop if missing
        if not self.ftm_path.exists():
            reporter.record(
                self.NAME, "CHK-FTM-001 FTM file exists", False,
                f"missing: {self.ftm_path.relative_to(self.ctx.REPO_ROOT)}",
            )
            return
        reporter.record(self.NAME, "CHK-FTM-001 FTM file exists", True)

        ftm_text = self.ftm_path.read_text(encoding="utf-8", errors="replace")

        # CHK-FTM-002: catalog existence — non-fatal; catalog-dependent checks
        # (005, 006, 007) are skipped when missing, but 003/008/009/010 still run.
        catalog_ok = self.catalog_path.exists()
        if not catalog_ok:
            reporter.record(
                self.NAME, "CHK-FTM-002 behavior catalog exists", False,
                f"missing: {self.catalog_path.relative_to(self.ctx.REPO_ROOT)}"
                " — CHK-FTM-005/006/007 skipped",
            )
        else:
            reporter.record(self.NAME, "CHK-FTM-002 behavior catalog exists", True)

        catalog = self._load_catalog(reporter) if catalog_ok else None

        # Derived values from FTM (always available)
        bh_refs_in_matrix: set[str] = self._extract_bh_refs(ftm_text)
        actual_tc_count = self._count_tc_rows(ftm_text)
        tc_details: list[tuple[str, str, set[str]]] = self._extract_tc_details(ftm_text)
        tc_full = self._extract_tc_full(ftm_text)

        # CHK-FTM-003: header TC count (always)
        self._check_header_tc_count(reporter, ftm_text, actual_tc_count)

        if catalog is not None:
            # Derived values from catalog
            all_bh_ids: set[str] = {b["id"] for b in catalog.get("behaviors", [])}
            catalog_total_bh = len(all_bh_ids)
            fr_to_bh: dict[str, list[str]] = catalog.get("fr_to_bh_index", {})
            defect_bh_ids: set[str] = {
                d["bh_id"]
                for d in catalog.get("known_defects", [])
            }
            covered_bh = all_bh_ids & bh_refs_in_matrix

            # CHK-FTM-004: header BH coverage claim
            self._check_header_bh_coverage(
                reporter, ftm_text, len(covered_bh), catalog_total_bh
            )

            # CHK-FTM-005: every BH in catalog is covered
            self._check_all_bh_covered(reporter, all_bh_ids, bh_refs_in_matrix)

            # CHK-FTM-006: every RF has at least one TC
            self._check_rf_coverage(reporter, fr_to_bh, bh_refs_in_matrix, ftm_text)

            # CHK-FTM-007: integration TCs with defect BH refs carry a footnote
            self._check_defect_footnotes(reporter, tc_details, defect_bh_ids, ftm_text)

        # CHK-FTM-008: every RF in spec.md appears in the matrix (catalog-independent)
        self._check_spec_rf_completeness(reporter, ftm_text)

        # CHK-FTM-009: priority column values are valid; P0 RFs have ≥1 Smoke TC
        self._check_priority_rules(reporter, tc_full)

        # CHK-FTM-010: test type column values match the allowed enum
        self._check_test_type_enum(reporter, tc_full)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _load_catalog(self, reporter: "Reporter"):
        try:
            data = json.loads(
                self.catalog_path.read_text(encoding="utf-8", errors="replace")
            )
            reporter.record(self.NAME, "CHK-FTM-002 behavior catalog is valid JSON", True)
            return data
        except json.JSONDecodeError as exc:
            reporter.record(
                self.NAME, "CHK-FTM-002 behavior catalog is valid JSON", False,
                str(exc),
            )
            return None

    def _extract_bh_refs(self, text: str) -> set[str]:
        """Collect every BH-ID mentioned in TC table rows (column 7)."""
        found: set[str] = set()
        for m in _TC_ROW.finditer(text):
            cell = m.group(1)
            found.update(_BH_ID.findall(cell))
        return found

    def _count_tc_rows(self, text: str) -> int:
        """Count distinct TC-IDs in the matrix body.
        Supports both TC-001 and TC-CS-001 compound TC-ID formats.
        """
        return len(set(re.findall(r"\|\s*(TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*\|", text)))

    def _extract_tc_details(
        self, text: str
    ) -> list[tuple[str, str, set[str]]]:
        """Return list of (tc_id, test_type, {bh_ids}) for each TC row."""
        rows = []
        for m in _TC_ROW_DETAIL.finditer(text):
            tc_id = m.group(1)
            test_type = m.group(2).strip()
            bh_ids = set(_BH_ID.findall(m.group(3)))
            rows.append((tc_id, test_type, bh_ids))
        return rows

    def _check_header_tc_count(
        self, reporter: "Reporter", text: str, actual: int
    ) -> None:
        m = _HEADER_TC_COUNT.search(text)
        if not m:
            reporter.record(
                self.NAME, "CHK-FTM-003 header TC count present", False,
                "Line 'Total de cenários mapeados: N' not found in header",
            )
            return
        declared = int(m.group(1))
        ok = declared == actual
        reporter.record(
            self.NAME,
            "CHK-FTM-003 header TC count matches actual",
            ok,
            f"declared={declared}, actual={actual}"
            if not ok
            else f"{actual} TCs",
        )

    def _check_header_bh_coverage(
        self,
        reporter: "Reporter",
        text: str,
        covered: int,
        total: int,
    ) -> None:
        m = _HEADER_BH_COVERAGE.search(text)
        if not m:
            reporter.record(
                self.NAME, "CHK-FTM-004 header BH coverage claim present", False,
                "Pattern 'N/M behaviors' not found in header",
            )
            return
        declared_covered = int(m.group(1))
        declared_total = int(m.group(2))
        ok = declared_covered == covered and declared_total == total
        reporter.record(
            self.NAME,
            "CHK-FTM-004 header BH coverage claim is accurate",
            ok,
            f"declared={declared_covered}/{declared_total}, "
            f"actual={covered}/{total}"
            if not ok
            else f"{covered}/{total} behaviors covered",
        )

    def _check_all_bh_covered(
        self,
        reporter: "Reporter",
        all_bh: set[str],
        covered: set[str],
    ) -> None:
        missing = sorted(all_bh - covered)
        ok = not missing
        reporter.record(
            self.NAME,
            "CHK-FTM-005 every catalog BH-ID appears in at least one TC",
            ok,
            f"uncovered behaviors: {', '.join(missing)}" if not ok else "",
        )

    def _check_rf_coverage(
        self,
        reporter: "Reporter",
        fr_to_bh: dict[str, list[str]],
        bh_refs_in_matrix: set[str],
        text: str,
    ) -> None:
        """Each RF must have at least one TC row in the matrix.

        A RF is considered covered if:
          - at least one of its BH-IDs appears in the matrix BH refs, OR
          - the RF-ID appears directly in a TC row (column 1).
        """
        rf_ids_in_tc_rows = set(_RF_ID_IN_TC_ROW.findall(text))
        uncovered = []
        for rf, bh_list in fr_to_bh.items():
            bh_covered = bool(set(bh_list) & bh_refs_in_matrix)
            rf_covered = rf in rf_ids_in_tc_rows
            if not bh_covered and not rf_covered:
                uncovered.append(rf)
        ok = not uncovered
        reporter.record(
            self.NAME,
            "CHK-FTM-006 every RF has at least one TC",
            ok,
            f"RFs without TC: {', '.join(sorted(uncovered))}" if not ok else "",
        )

    def _check_defect_footnotes(
        self,
        reporter: "Reporter",
        tc_details: list[tuple[str, str, set[str]]],
        defect_bh_ids: set[str],
        text: str,
    ) -> None:
        """Integration TCs that reference a BH with a known defect must carry ¹."""
        violations = []
        for tc_id, test_type, bh_ids in tc_details:
            if test_type.lower() not in {"integration", "e2e"}:
                continue
            if not bh_ids & defect_bh_ids:
                continue
            # Find the TC row line in text and check for ¹
            # TC-ID is in column 3 (after RF ID and RF Nome), so skip 2 columns
            tc_row_pattern = re.compile(
                r"^\|[^|]+\|[^|]+\|\s*" + re.escape(tc_id) + r"\s*\|[^\n]*$",
                re.MULTILINE,
            )
            row_match = tc_row_pattern.search(text)
            if row_match and not _FOOTNOTE_MARKER.search(row_match.group(0)):
                violations.append(tc_id)

        ok = not violations
        reporter.record(
            self.NAME,
            "CHK-FTM-007 integration/e2e TCs with defect BH carry ¹ footnote",
            ok,
            f"missing footnote on: {', '.join(violations)}" if not ok else "",
        )

    # ------------------------------------------------------------------ #
    # New helpers — CHK-FTM-008/009/010                                   #
    # ------------------------------------------------------------------ #

    def _extract_tc_full(
        self, text: str
    ) -> list[tuple[str, str, str, str, set[str]]]:
        """Return (rf_id, tc_id, priority, test_type, {bh_ids}) for each TC row."""
        rows = []
        for m in _TC_ROW_FULL.finditer(text):
            rows.append((
                m.group(1).strip(),
                m.group(2).strip(),
                m.group(3).strip(),
                m.group(4).strip(),
                set(_BH_ID.findall(m.group(5))),
            ))
        return rows

    def _find_spec_path(self) -> "Path | None":
        """Locate spec.md with the same fallback chain as the generator (STEP 1)."""
        for name in ("spec.md", "functional-spec.md"):
            p = self.spec_docs_dir / name
            if p.exists():
                return p
        spec_kit = self.spec_docs_dir / "spec-kit"
        if spec_kit.is_dir() and any(spec_kit.glob("*.md")):
            return spec_kit
        return None

    def _check_spec_rf_completeness(
        self, reporter: "Reporter", ftm_text: str
    ) -> None:
        """CHK-FTM-008: every RF-ID defined in spec.md must appear in the matrix.

        This check is independent of the behavior catalog, closing the gap where
        a RF exists in spec.md but is absent from fr_to_bh_index.
        """
        spec_path = self._find_spec_path()
        if spec_path is None:
            reporter.record(
                self.NAME, "CHK-FTM-008 spec.md RF completeness", False,
                "spec.md / functional-spec.md / spec-kit/ not found — "
                "cannot verify RF completeness independently of catalog",
            )
            return

        if spec_path.is_dir():
            spec_text = "\n".join(
                p.read_text(encoding="utf-8", errors="replace")
                for p in sorted(spec_path.glob("*.md"))
            )
        else:
            spec_text = spec_path.read_text(encoding="utf-8", errors="replace")

        spec_rf_ids: set[str] = set(re.findall(r"\bFR-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*\b", spec_text))
        if not spec_rf_ids:
            reporter.record(
                self.NAME, "CHK-FTM-008 spec.md RF completeness", False,
                "No RF-IDs (pattern FR-xx or FR-xx.x) found in spec.md",
            )
            return

        matrix_rf_ids: set[str] = set(_RF_ID_IN_TC_ROW.findall(ftm_text))
        missing = sorted(spec_rf_ids - matrix_rf_ids)
        ok = not missing
        reporter.record(
            self.NAME,
            "CHK-FTM-008 all spec.md RFs present in matrix",
            ok,
            f"RFs defined in spec.md but absent from matrix: {', '.join(missing)}"
            if not ok
            else f"{len(spec_rf_ids)} RFs from spec.md all present",
        )

    def _check_priority_rules(
        self,
        reporter: "Reporter",
        tc_full: list[tuple[str, str, str, str, set[str]]],
    ) -> None:
        """CHK-FTM-009: priority values are P0–P3; every P0 RF has ≥1 Smoke TC."""
        invalid_prio = sorted(
            {prio for _, _, prio, _, _ in tc_full if prio not in _VALID_PRIORITIES}
        )
        ok_values = not invalid_prio
        reporter.record(
            self.NAME,
            "CHK-FTM-009a priority values are valid (P0–P3)",
            ok_values,
            f"invalid priority values found: {', '.join(invalid_prio)}"
            if not ok_values
            else "",
        )

        p0_rfs: set[str] = {rf for rf, _, prio, _, _ in tc_full if prio == "P0"}
        p0_with_smoke: set[str] = {
            rf
            for rf, _, prio, ttype, _ in tc_full
            if prio == "P0" and ttype.lower() == "smoke"
        }
        missing_smoke = sorted(p0_rfs - p0_with_smoke)
        ok_smoke = not missing_smoke
        reporter.record(
            self.NAME,
            "CHK-FTM-009b P0 RFs have ≥1 Smoke TC",
            ok_smoke,
            f"P0 RFs missing a Smoke TC: {', '.join(missing_smoke)}"
            if not ok_smoke
            else "",
        )

    def _check_test_type_enum(
        self,
        reporter: "Reporter",
        tc_full: list[tuple[str, str, str, str, set[str]]],
    ) -> None:
        """CHK-FTM-010: test type column values match the allowed enum."""
        invalid = sorted(
            {ttype for _, _, _, ttype, _ in tc_full
             if ttype.lower() not in _VALID_TEST_TYPES}
        )
        ok = not invalid
        reporter.record(
            self.NAME,
            "CHK-FTM-010 test type values are valid "
            "{Acceptance|Integration|Unit|E2E|Smoke}",
            ok,
            f"invalid test type values: {', '.join(invalid)}" if not ok else "",
        )
