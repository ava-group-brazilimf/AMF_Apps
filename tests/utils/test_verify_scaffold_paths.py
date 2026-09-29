"""Tests for verify_scaffold_paths.py."""

from pathlib import Path

import pytest

from src.shared.utils.verify_scaffold_paths import _apply_fix, _detect_violations, main


def _make_tobe(tmp_path: Path) -> Path:
    tobe = tmp_path / "projects" / "demo" / "outputs" / "tobe"
    tobe.mkdir(parents=True)
    return tobe


def test_no_violations_when_only_allowed_stacks_exist(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "source-code" / "dotnet").mkdir(parents=True)
    (tobe / "source-code" / "angular").mkdir(parents=True)

    violations = _detect_violations(
        tobe,
        allowed_stacks={"dotnet", "angular", "frontend", "backend"},
        forbidden_root_names={"frontend", "backend"},
        project_named_patterns=[r"-(spa|app|ui)$"],
    )
    assert violations == []


def test_detects_legacy_frontend_folder(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "frontend" / "nopcommerce-spa").mkdir(parents=True)

    violations = _detect_violations(
        tobe,
        allowed_stacks={"dotnet", "angular", "frontend", "backend"},
        forbidden_root_names={"frontend", "backend"},
        project_named_patterns=[r"-(spa|app|ui)$"],
    )
    assert len(violations) == 1
    assert violations[0]["type"] == "forbidden_top_level_directory"
    assert "frontend" in violations[0]["path"]


def test_detects_project_named_folder_inside_source_code(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "source-code" / "nopcommerce-spa").mkdir(parents=True)

    violations = _detect_violations(
        tobe,
        allowed_stacks={"dotnet", "angular", "frontend", "backend"},
        forbidden_root_names={"frontend", "backend"},
        project_named_patterns=[r"-(spa|app|ui)$"],
    )
    assert len(violations) == 1
    assert violations[0]["type"] == "project_named_source_code_folder"


def test_detects_project_named_folder_at_top_level(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "myproject-spa").mkdir(parents=True)

    violations = _detect_violations(
        tobe,
        allowed_stacks={"dotnet", "angular", "frontend", "backend"},
        forbidden_root_names={"frontend", "backend"},
        project_named_patterns=[r"-(spa|app|ui)$"],
    )
    assert len(violations) == 1
    assert violations[0]["type"] == "project_named_top_level_folder"


def test_fix_moves_legacy_frontend_to_canonical_location(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    legacy = tobe / "frontend" / "nopcommerce-spa"
    legacy.mkdir(parents=True)
    (legacy / "package.json").write_text("{}")

    violations = _detect_violations(
        tobe,
        allowed_stacks={"dotnet", "angular", "frontend", "backend"},
        forbidden_root_names={"frontend", "backend"},
        project_named_patterns=[r"-(spa|app|ui)$"],
    )
    fixed = _apply_fix(violations)

    assert fixed[0]["fix_status"] == "moved"
    assert not (tobe / "frontend").exists()
    assert (tobe / "source-code" / "frontend" / "nopcommerce-spa" / "package.json").exists()


def test_check_mode_returns_nonzero_on_violations(tmp_path: Path, capsys) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "frontend").mkdir()

    code = main(
        [
            "--project",
            "demo",
            "--workspace",
            str(tmp_path),
            "--allowed-stacks",
            "dotnet,angular,frontend,backend",
        ]
    )
    assert code == 1
    captured = capsys.readouterr()
    assert "forbidden_top_level_directory" in captured.out


def test_check_mode_returns_zero_when_clean(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "source-code" / "angular").mkdir(parents=True)

    code = main(
        [
            "--project",
            "demo",
            "--workspace",
            str(tmp_path),
            "--allowed-stacks",
            "dotnet,angular,frontend,backend",
        ]
    )
    assert code == 0


def test_json_output(tmp_path: Path, capsys) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "frontend").mkdir()

    main(
        [
            "--project",
            "demo",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert '"violations"' in captured.out
    assert "forbidden_top_level_directory" in captured.out


def test_ignores_unrelated_top_level_folders(tmp_path: Path) -> None:
    tobe = _make_tobe(tmp_path)
    (tobe / "docs").mkdir()
    (tobe / "diagrams").mkdir()

    violations = _detect_violations(
        tobe,
        allowed_stacks={"dotnet", "angular", "frontend", "backend"},
        forbidden_root_names={"frontend", "backend"},
        project_named_patterns=[r"-(spa|app|ui)$"],
    )
    assert violations == []
