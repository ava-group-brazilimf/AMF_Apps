import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "src" / "shared" / "utils" / "verify_nuget_packages.py"


def _run(root: Path, *, quiet: bool = False) -> tuple[int, dict | str]:
    cmd = [sys.executable, str(SCRIPT), "--root", str(root)]
    if quiet:
        cmd.append("--quiet")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if quiet:
        return result.returncode, result.stdout.strip()
    return result.returncode, json.loads(result.stdout)


def test_pass_no_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Build.props").write_text(
            """<Project>
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 0
        assert data["status"] == "PASS"
        assert data["projects_checked"] == 1
        assert data["duplicates"] == []


def test_fail_duplicate_package_reference():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Build.props").write_text(
            """<Project>
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 1
        assert data["status"] == "FAIL"
        assert len(data["duplicates"]) == 1
        dup = data["duplicates"][0]
        assert dup["package"] == "Microsoft.CodeAnalysis.NetAnalyzers"
        assert dup["central_file"] == "Directory.Build.props"
        assert dup["project_file"] == "src/App.csproj"


def test_cpm_package_version_is_not_duplicate():
    """PackageVersion in central props + PackageReference in csproj is CPM, not a duplicate."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Build.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="9.0.0" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 0
        assert data["status"] == "PASS"


def test_multiple_projects_one_duplicate():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Build.props").write_text(
            """<Project>
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "A.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src" / "B.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 1
        assert len(data["duplicates"]) == 1
        assert data["duplicates"][0]["project_file"] == "src/A.csproj"


def test_quiet_mode():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Build.props").write_text(
            """<Project>
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, output = _run(root, quiet=True)
        assert code == 1
        assert "NUGET PACKAGES FAIL" in output
        assert "Microsoft.CodeAnalysis.NetAnalyzers" in output


def test_missing_root():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "does-not-exist"
        code, data = _run(root)
        assert code == 2
        assert data["status"] == "ERROR"
