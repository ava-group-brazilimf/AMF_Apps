from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src/modules/ava-fabric-agents/summary/utils"))

from build_summary_comprehensive import _parse_test_plan


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_test_plan_accepts_current_framework_scope_execution_contract(tmp_path):
    outputs = tmp_path / "outputs"
    _write(
        outputs / "tobe/qa/test-plan.md",
        """
| Type | Framework | Scope | Execution |
|------|-----------|-------|-----------|
| Unit — Domain | xUnit + Moq | Entities and value objects | CI — every commit |
| Integration — API | WebApplicationFactory | REST endpoints | CI — every PR |
""",
    )

    rows = _parse_test_plan(outputs)

    assert rows[:2] == [
        {
            "t": "Unit — Domain",
            "tool": "xUnit + Moq",
            "alvo": "Entities and value objects",
            "crit": "CI — every commit",
            "cov": "—",
        },
        {
            "t": "Integration — API",
            "tool": "WebApplicationFactory",
            "alvo": "REST endpoints",
            "crit": "CI — every PR",
            "cov": "—",
        },
    ]


def test_parse_test_plan_adds_functional_matrix_coverage_row(tmp_path):
    outputs = tmp_path / "outputs"
    _write(
        outputs / "tobe/tests/functional-test-matrix.md",
        """
| BC | FRs | BRs | TCs Mapped | Coverage |
|----|-----|-----|------------|----------|
| BC-01 IAM | 5 | 3 | 40 | 100% |
| BC-02 Organization | 5 | 1 | 25 | 95% |
| **TOTAL** | **10** | **4** | **65** | **98%** |
""",
    )

    rows = _parse_test_plan(outputs)

    assert rows == [
        {
            "t": "Functional Matrix",
            "tool": "Functional Test Matrix",
            "alvo": "2 BCs / coverage by bounded context",
            "crit": "FR/BR/TC traceability",
            "cov": "BC-01 IAM: 100%; BC-02 Organization: 95%",
        }
    ]
