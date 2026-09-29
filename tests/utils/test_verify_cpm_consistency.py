import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "src" / "shared" / "utils" / "verify_cpm_consistency.py"


def _run(root: Path, *, quiet: bool = False) -> tuple[int, dict | str]:
    cmd = [sys.executable, str(SCRIPT), "--root", str(root)]
    if quiet:
        cmd.append("--quiet")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if quiet:
        return result.returncode, result.stdout.strip()
    return result.returncode, json.loads(result.stdout)


def test_skipped_when_no_directory_packages_props():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
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
        assert data["status"] == "SKIPPED"
        assert data["cpm_enabled"] is False
        assert data["central_packages_file"] is None
        assert data["missing_versions"] == []


def test_skipped_when_cpm_not_enabled():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Packages.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>false</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="9.*" />
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
        assert data["status"] == "SKIPPED"
        assert data["cpm_enabled"] is False


def test_pass_when_all_package_references_have_version():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Packages.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="9.*" />
    <PackageVersion Include="Serilog" Version="4.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" />
    <PackageReference Include="Serilog" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 0
        assert data["status"] == "PASS"
        assert data["cpm_enabled"] is True
        assert data["projects_checked"] == 1
        assert data["missing_versions"] == []


def test_fail_when_package_reference_missing_version():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Packages.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="9.*" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" />
    <PackageReference Include="Missing.Package" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 1
        assert data["status"] == "FAIL"
        assert data["projects_checked"] == 1
        assert len(data["missing_versions"]) == 1
        missing = data["missing_versions"][0]
        assert missing["package"] == "Missing.Package"
        assert missing["project_file"] == "src/App.csproj"


def test_multiple_projects_aggregate_missing_versions():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Packages.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Shared.Package" Version="1.0.0" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "Domain.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Shared.Package" />
    <PackageReference Include="Domain.Only.Package" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "tests").mkdir()
        (root / "tests" / "Tests.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Shared.Package" />
    <PackageReference Include="Tests.Only.Package" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, data = _run(root)
        assert code == 1
        assert data["status"] == "FAIL"
        assert data["projects_checked"] == 2
        missing_packages = {m["package"] for m in data["missing_versions"]}
        assert missing_packages == {"Domain.Only.Package", "Tests.Only.Package"}


def test_quiet_output():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Directory.Packages.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Existing" Version="1.0.0" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Existing" />
    <PackageReference Include="Missing" />
  </ItemGroup>
</Project>""",
            encoding="utf-8",
        )
        code, output = _run(root, quiet=True)
        assert code == 1
        assert output == "FAIL: 1 missing"


def test_error_when_root_does_not_exist():
    code, data = _run(Path("/nonexistent/path/here"))
    assert code == 2
    assert data["status"] == "ERROR"
    assert "does not exist" in data["error"]
