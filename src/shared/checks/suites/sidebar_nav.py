"""
suites/sidebar_nav.py
=====================
Migrates: check2.py (updated to match current template structure)

Checks sidebar navigation calls and validates that renderNavDots
and key dotMap entries are present in the generated HTML.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter


class SidebarNavSuite:
    NAME = "nav"

    # dotMap keys that MUST be present in the HTML (critical nav dot entries)
    _DOTMAP_KEYS = ["f1-arch", "f1-inv", "f2-bc", "f2-bn-tobe"]

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx

    def run(self, reporter: "Reporter") -> None:
        print(f"\n-- Suite: {self.NAME} --")
        html = self.ctx.html

        # -- nav() calls in the sidebar --
        sidebar_end = html.find("</nav>")
        sidebar = html[:sidebar_end] if sidebar_end > 0 else html[:20_000]
        nav_calls = re.findall(r"nav\('[^']*'", sidebar)
        passed = len(nav_calls) > 0
        detail = f"{len(nav_calls)} nav() call(s): {nav_calls[:5]}" if nav_calls else "no nav() calls found in sidebar"
        reporter.record(self.NAME, "sidebar nav() calls present", passed, detail)

        # -- renderNavDots function present --
        passed = "renderNavDots" in html
        reporter.record(self.NAME, "renderNavDots function present", passed,
                        "" if passed else "renderNavDots missing from HTML")

        # -- dotMap key presence --
        for key in self._DOTMAP_KEYS:
            passed = f"'{key}'" in html
            reporter.record(self.NAME, f"dotMap key '{key}' present", passed,
                            "" if passed else f"key '{key}' missing from dotMap")
