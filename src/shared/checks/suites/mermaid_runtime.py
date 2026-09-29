"""
suites/mermaid_runtime.py
=========================
Migrates: check_mermaid.py

Verifies that Mermaid is properly embedded in the generated HTML.
Mermaid is now bundled inline (not as a separate file), so we check
for the version string inside the HTML artifact.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter


class MermaidRuntimeSuite:
    NAME = "mermaid_runtime"

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx

    def run(self, reporter: "Reporter") -> None:
        print(f"\n-- Suite: {self.NAME} --")

        # Mermaid is embedded inline in the HTML (not as a separate file).
        # Check for the version string in the generated HTML.
        html = self.ctx.html
        version = None
        for pattern in (
            r'"version":"([0-9.]+)"',
            r'version:"([0-9.]+)"',
            r'mermaid@([0-9]+\.[0-9]+)',
        ):
            m = re.search(pattern, html)
            if m:
                version = m.group(1)
                break

        passed = version is not None
        detail = f"embedded version {version}" if version else "mermaid version string not found in HTML"
        reporter.record(self.NAME, "mermaid runtime embedded in HTML", passed, detail)
