"""
context.py — resolves project paths and loads the HTML artifact.
No hardcoded project names or dates.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

_SAFE_PROJECT_NAME = re.compile(r'^[A-Za-z0-9_\-\.]{1,128}$')


class CheckContext:
    """Lightweight context for a single project's outputs.

    Resolves the newest AVA-FABRIC-SUMMARY-*.html automatically.
    """

    # Root of the repository (two levels up from src/shared/checks/)
    REPO_ROOT: Path = Path(__file__).resolve().parents[3]

    def __init__(self, project: str) -> None:
        if not _SAFE_PROJECT_NAME.match(project):
            raise ValueError(
                f"Invalid project name {project!r}. "
                "Only letters, digits, hyphens, underscores, and dots are allowed."
            )
        self.project = project
        self.project_dir: Path = self.REPO_ROOT / "projects" / project
        self.outputs_dir: Path = self.project_dir / "outputs"
        self.summary_dir: Path = self.outputs_dir / "summary"
        self.asis_dir: Path = self.outputs_dir / "asis"
        self.tobe_dir: Path = self.outputs_dir / "tobe"
        self.speckit_dir: Path = self.outputs_dir / "tobe" / "speckit"

        self._html_path: Optional[Path] = None
        self._html: Optional[str] = None

        # Add validate_summary to sys.path once, lazily
        self._validator_path = (
            self.REPO_ROOT
            / "src/modules/ava-fabric-agents/summary/utils"
        )

    # ------------------------------------------------------------------ #
    # Summary HTML — carregado sob demanda                                 #
    # ------------------------------------------------------------------ #
    # Antes o HTML era lido no __init__ e a ausência levantava, o que impedia
    # qualquer suíte de rodar antes da F8 existir. Os gates da F3S rodam muito
    # antes de haver summary. As 12 suítes que usam `ctx.html` continuam vendo o
    # mesmo objeto e o mesmo erro — só que no primeiro acesso, não na construção.

    @property
    def html_path(self) -> Path:
        if self._html_path is None:
            self._html_path = self._find_html()
        return self._html_path

    @property
    def html(self) -> str:
        if self._html is None:
            self._html = self.html_path.read_text(encoding="utf-8", errors="replace")
        return self._html

    def has_summary_html(self) -> bool:
        """Permite a uma suíte pular com elegância em vez de estourar."""
        return bool(sorted(self.summary_dir.glob("AVA-FABRIC-SUMMARY-*.html")))

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _find_html(self) -> Path:
        candidates = sorted(self.summary_dir.glob("AVA-FABRIC-SUMMARY-*.html"))
        if not candidates:
            raise FileNotFoundError(
                f"No AVA-FABRIC-SUMMARY-*.html found in {self.summary_dir}"
            )
        return candidates[-1]  # newest by name (ISO date suffix)

    def find_mmd_files(self) -> list[Path]:
        """Return all .mmd files under outputs/asis/."""
        return sorted(self.asis_dir.rglob("*.mmd"))

    def mermaid_js_path(self) -> Optional[Path]:
        p = self.summary_dir / "mermaid.min.js"
        return p if p.exists() else None

    def screen_nav_map_path(self) -> Optional[Path]:
        p = self.asis_dir / "docs" / "screen-navigation-map.md"
        return p if p.exists() else None

    def import_validator(self):
        """Import validate_summary from the summary utils, suppressing its
        module-level print side-effects."""
        import builtins

        if str(self._validator_path) not in sys.path:
            sys.path.insert(0, str(self._validator_path))

        orig = builtins.print
        builtins.print = lambda *a, **k: None
        try:
            import validate_summary
        finally:
            builtins.print = orig
        return validate_summary

    def extract_json_slice(self, key: str) -> Optional[str]:
        """Delegate to validate_summary._extract_json_slice."""
        vs = self.import_validator()
        return vs._extract_json_slice(self.html, key)

    def try_json(self, raw: str):
        """Delegate to validate_summary._try_json."""
        vs = self.import_validator()
        return vs._try_json(raw)
