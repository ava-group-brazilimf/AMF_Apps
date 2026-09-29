"""
suites/html_data.py
===================
Consolidates: check_html.py · check_html2.py · check_final.py · check_mmd2.py (D.staticDiagrams part)

Checks that all expected D.* data fields are present in the generated HTML,
validates their content, and reports debug snippets when a field is missing.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

# Regex for literal \n inside a JSON string value (escaped newline in source)
_INLINE_NEWLINE = re.compile(r'"[^"\n]*\\n[^"\n]*"')


class HtmlDataSuite:
    NAME = "html"

    # (check_name, html_key_or_substring, human_description)
    _PRESENCE_CHECKS = [
        ("ccTop",           "ccTop:",           "ccTop data block"),
        ("bizRules",        "bizRules:",         "bizRules data block"),
        ("funcReqs",        "funcReqs:",         "funcReqs data block"),
        ("testMap",         "testMap:",          "testMap data block"),
        ("apiEndpoints",    "apiEndpoints:",     "apiEndpoints data block"),
        ("staticDiagrams",  "staticDiagrams:",   "staticDiagrams data block"),
        ("agentStatus",     "agentStatus:",      "agentStatus data block"),
        ("fileTree",        "fileTree:",         "fileTree data block"),
        ("c4ctx_key",       '"c4ctx"',           'staticDiagrams "c4ctx" key'),
        # tobeC4comp is the primary TO-BE C4 Component diagram key (current naming)
        ("tobeC4comp_key",  '"tobeC4comp"',      'staticDiagrams "tobeC4comp" key'),
        ("kpi_total_files", "kpi-total-files",   "KPI total-files element"),
        # Unreplaced DRAWIO placeholder means the builder's injection anchor is missing
        ("no_unresolved_tpl", "{{DRAWIO",         "no leftover {{DRAWIO_*}} placeholder", True),
    ]

    # Absence checks — empty: drawio integration is part of the current template by design
    _ABSENCE_CHECKS: list = []

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx

    def run(self, reporter: "Reporter") -> None:
        print(f"\n── Suite: {self.NAME}  [{self.ctx.html_path.name}] ──")
        html = self.ctx.html

        # ── Presence checks ──────────────────────────────────────────
        for entry in self._PRESENCE_CHECKS:
            check_id, needle, desc = entry[0], entry[1], entry[2]
            invert = len(entry) == 4 and entry[3]
            if invert:
                passed = needle not in html
            else:
                passed = needle in html
            detail = "" if passed else f'"{needle}" not found in HTML'
            reporter.record(self.NAME, desc, passed, detail)

        # ── Absence checks ────────────────────────────────────────────
        for check_id, needle, desc in self._ABSENCE_CHECKS:
            present = needle in html
            passed = not present
            detail = f'"{needle}" still present ({html.count(needle)}×)' if present else ""
            reporter.record(self.NAME, desc, passed, detail)

        # ── screenMermaid presence ────────────────────────────────────
        m = re.search(r"screenMermaid:\s*(.{0,150})", html)
        passed = m is not None
        detail = "" if passed else "screenMermaid key not found"
        reporter.record(self.NAME, "screenMermaid present", passed, detail)

        # ── screenForms count > 0 ─────────────────────────────────────
        # JSON may be pretty-printed ("num": "1") or minified ("num":"1")
        forms = re.findall(r'"num":\s*"(\d+)"', html)
        passed = len(forms) > 0
        detail = f"{len(forms)} form(s) found"
        reporter.record(self.NAME, "screenForms count > 0", passed, detail)

        # ── staticDiagrams — no inline \\n in values ──────────────────
        sd_raw = self.ctx.extract_json_slice("staticDiagrams")
        if sd_raw is not None:
            sd = self.ctx.try_json(sd_raw)
            if isinstance(sd, dict):
                bad_keys = []
                for key, val in sd.items():
                    if isinstance(val, str) and _INLINE_NEWLINE.search(val):
                        bad_keys.append(key)
                passed = len(bad_keys) == 0
                detail = f"inline \\n in keys: {bad_keys}" if bad_keys else ""
                reporter.record(self.NAME, "staticDiagrams — no inline \\n", passed, detail)
            else:
                reporter.record(self.NAME, "staticDiagrams — no inline \\n", False,
                                "could not parse staticDiagrams as dict")
        else:
            reporter.record(self.NAME, "staticDiagrams — no inline \\n", False,
                            "staticDiagrams key not found")

        # ── screen-navigation-map has mermaid block ───────────────────
        snm = self.ctx.screen_nav_map_path()
        if snm and snm.exists():
            content = snm.read_text(encoding="utf-8", errors="replace")
            # Accept either: inline ```mermaid block OR companion screen-flow.mmd
            companion_mmd = snm.parent / "screen-flow.mmd"
            has_inline = "```mermaid" in content
            has_companion = companion_mmd.exists()
            passed = has_inline or has_companion
            if has_inline:
                detail = f"{len(content)} chars (inline mermaid block)"
            elif has_companion:
                detail = f"companion {companion_mmd.name} found"
            else:
                detail = "no ```mermaid block found and no companion screen-flow.mmd"
            reporter.record(self.NAME, "screen-navigation-map has mermaid block", passed, detail)
        else:
            reporter.record(self.NAME, "screen-navigation-map has mermaid block", False,
                            "file not found")

        # ── Debug snippets (verbose info, always printed when verbose) ──
        self._print_debug_snippets(html)

    def _print_debug_snippets(self, html: str) -> None:
        for key in ("ccTop", "bizRules", "funcReqs", "agentStatus", "staticDiagrams"):
            raw = self.ctx.extract_json_slice(key)
            if raw:
                snippet = raw[:200].replace("\n", " ")
                print(f"    {key}[:200] = {snippet}")
            else:
                print(f"    {key}: NOT FOUND in HTML")
