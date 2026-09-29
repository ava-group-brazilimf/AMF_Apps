from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src/modules/ava-fabric-agents/summary/utils"))

from build_summary_comprehensive import parse_coverage_gap_strategy


def _write_gap_report(root: Path) -> None:
    path = root / "tobe/qa/gap-analysis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
# QA Gap Analysis

## Gap 1: Multi-Tenancy Isolation (CRITICAL → RESOLVED)

**AS-IS Gap (TG-001):** Zero integration tests.

**TO-BE Coverage:** 18 dedicated test cases.

**Residual Risk:** LOW

**Automation:** All cases automated as xUnit integration tests.

## Gap 2: LGPD Compliance (HIGH → MEDIUM)

**TO-BE Coverage:** Retention and anonymization tests.

**Residual Risk:** MEDIUM

**Open Items:**
- LGPD Article 37 processing records document (manual — Wave 4)
""",
        encoding="utf-8",
    )


def test_parse_coverage_gap_strategy_accepts_narrative_report(tmp_path):
    _write_gap_report(tmp_path)

    rows = parse_coverage_gap_strategy(tmp_path)

    assert len(rows) == 2
    assert rows[0]["gapId"] == "GAP-001"
    assert rows[0]["complexity"] == "CRITICAL"
    assert rows[0]["status"] == "RESOLVED"
    assert "18 dedicated test cases" in rows[0]["strategy"]
    assert "xUnit" in rows[0]["tools"]
    assert rows[1]["gapId"] == "GAP-002"
    assert rows[1]["status"] == "PARTIAL"
    assert rows[1]["wave"] == "Wave 4"


def test_parse_coverage_gap_strategy_keeps_structured_format(tmp_path):
    path = tmp_path / "tobe/qa/gap-analysis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
### GAP-101: Missing API contract coverage
**Severity**: HIGH
**BC**: BC-01
**Due**: Wave 2
**Mitigation**: Add contract tests.
""",
        encoding="utf-8",
    )

    rows = parse_coverage_gap_strategy(tmp_path)

    assert rows == [{
        "gapId": "GAP-101",
        "title": "Missing API contract coverage",
        "complexity": "HIGH",
        "dimension": "BC-01",
        "strategy": "Add contract tests.",
        "tools": "",
        "wave": "Wave 2",
        "status": "PLANNED",
    }]


def test_parse_coverage_gap_strategy_accepts_qa_gap_inline_metadata(tmp_path):
    path = tmp_path / "tobe/qa/gap-analysis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
### QA-GAP-001: SEFAZ Homologação Environment Required
**Severity:** CRITICAL | **BC:** BC-01, BC-03 | **Wave:** E

**Mitigation:**
- Provision SEFAZ homologação CNPJ before Wave E
- Use Polly + WireMock for SEFAZ simulation in unit/integration tests

**Test Strategy:**
Unit: Mock SEFAZ client
""",
        encoding="utf-8",
    )

    rows = parse_coverage_gap_strategy(tmp_path)

    assert rows == [{
        "gapId": "QA-GAP-001",
        "title": "SEFAZ Homologação Environment Required",
        "complexity": "CRITICAL",
        "dimension": "BC-01, BC-03",
        "strategy": "Provision SEFAZ homologação CNPJ before Wave E Use Polly + WireMock for SEFAZ simulation in unit/integration tests",
        "tools": "",
        "wave": "E",
        "status": "PLANNED",
    }]
