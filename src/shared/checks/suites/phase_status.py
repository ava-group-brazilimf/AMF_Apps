"""
suites/phase_status.py
======================
Validates phase structure, agent coverage, execution percentage, and derived
data from ``const PHASES = [...]`` and the ``D`` object in the AVA Fabric
HTML summary.

Functional requirements:
  FR-001  No agents defined in PHASES are missing from agentStatus.
  FR-002  No agents present in agentStatus are absent from PHASES.
  FR-003  Agent count matches between PHASES and agentStatus.
  FR-004  D.execPct matches round(done / total * 100).
  FR-005  No agent has status "done" with an empty artifacts list.
  FR-006  Reports whether every phase is complete (all agents done).
  FR-007  No phase N+1 has done/running agents while phase N is incomplete.
  FR-008  If phase 1 is complete, risks / bc / gaps must be non-empty.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter


class PhaseStatusSuite:
    NAME = "phase_status"

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx
        self._phases: list[dict] = []
        self._agent_status: dict = {}
        self._arts: dict = {}
        self._exec_pct: Optional[float] = None

    # ------------------------------------------------------------------ #
    # Phase extraction                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_phases(html: str) -> list[dict]:
        """Two-pass depth-counting extraction of ``const PHASES = [...]``.

        Pass 1
        ------
        Locate ``const PHASES = [``, then depth-count ``[`` and ``]``
        (string-aware, handles ``\\`` escapes) to find the closing ``]``
        and capture the full raw slice including the outer brackets.

        Pass 2
        ------
        Walk the raw slice tracking **all** bracket types (``[``, ``{``,
        ``(``) for depth. When ``depth == 1`` and ``char == '{'`` a new
        phase blob starts; when depth returns to ``1`` after a collecting
        state the blob ends.  From each blob:
          - ``num``       via ``re.search(r'\\bnum\\s*:\\s*(\\d+)', blob)``
          - ``agent_ids`` via ``re.findall(r'\\bid\\s*:\\s*"([^"]+)"', blob)``
        """
        # ── Pass 1 ──────────────────────────────────────────────────────
        start_marker = "const PHASES = ["
        idx = html.find(start_marker)
        if idx == -1:
            return []

        # Position of the opening '[' of the array literal
        pos = idx + len(start_marker) - 1

        depth = 0
        in_string = False
        escape = False
        end_pos = -1

        for i in range(pos, len(html)):
            ch = html[i]
            if escape:
                escape = False
                continue
            if in_string:
                if ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break

        if end_pos == -1:
            return []

        # raw_slice includes the outer '[' and ']'
        raw_slice = html[pos : end_pos + 1]

        # ── Pass 2 ──────────────────────────────────────────────────────
        phases: list[dict] = []
        depth2 = 0
        in_string2 = False
        escape2 = False
        blob_start = -1

        for j, ch in enumerate(raw_slice):
            if escape2:
                escape2 = False
                continue
            if in_string2:
                if ch == "\\":
                    escape2 = True
                elif ch == '"':
                    in_string2 = False
                continue
            if ch == '"':
                in_string2 = True
            elif ch in "[{(":
                # Check BEFORE incrementing: depth==1 and char=='{' → phase start
                if depth2 == 1 and ch == "{" and blob_start == -1:
                    blob_start = j
                depth2 += 1
            elif ch in "]})":
                depth2 -= 1
                # depth returned to 1 → end of phase blob
                if depth2 == 1 and blob_start != -1:
                    blob = raw_slice[blob_start : j + 1]
                    blob_start = -1
                    m_num = re.search(r"\bnum\s*:\s*(\d+)", blob)
                    if m_num:
                        num = int(m_num.group(1))
                        agent_ids = re.findall(r'\bid\s*:\s*"([^"]+)"', blob)
                        phases.append({"num": num, "agent_ids": agent_ids})

        return phases

    # ------------------------------------------------------------------ #
    # D-object field loading                                               #
    # ------------------------------------------------------------------ #

    def _load_d_fields(self) -> None:
        """Load agentStatus, arts, risks, bc, gaps, execPct from D object."""
        html = self.ctx.html

        # agentStatus ── dict: { agent_id: status_string | {status, ...} }
        raw = self.ctx.extract_json_slice("agentStatus")
        if raw is not None:
            parsed = self.ctx.try_json(raw)
            self._agent_status = parsed if isinstance(parsed, dict) else {}

        # arts ── dict: { agent_id: [artifact, ...] }
        raw = self.ctx.extract_json_slice("arts")
        if raw is not None:
            parsed = self.ctx.try_json(raw)
            self._arts = parsed if isinstance(parsed, dict) else {}

        # execPct ── scalar number; extract directly via regex (not JSON object)
        m = re.search(r"execPct\s*:\s*(\d+(?:\.\d+)?)", html)
        if m:
            self._exec_pct = float(m.group(1))

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_status(self, agent_id: str) -> str:
        """Return the status string for *agent_id* from agentStatus."""
        val = self._agent_status.get(agent_id)
        if isinstance(val, dict):
            return str(val.get("status", ""))
        return str(val) if val is not None else ""

    def _get_arts(self, agent_id: str) -> list:
        """Return artifact list for *agent_id* (checks arts dict then agentStatus)."""
        if agent_id in self._arts:
            val = self._arts[agent_id]
            return val if isinstance(val, list) else []
        val = self._agent_status.get(agent_id)
        if isinstance(val, dict):
            arts = val.get("arts", [])
            return arts if isinstance(arts, list) else []
        return []

    def _is_phase_complete(self, phase: dict) -> bool:
        """Return True when every agent in *phase* has status ``'done'``."""
        agent_ids = phase.get("agent_ids", [])
        if not agent_ids:
            return False
        return all(self._get_status(aid) == "done" for aid in agent_ids)

    # ------------------------------------------------------------------ #
    # Check methods                                                        #
    # ------------------------------------------------------------------ #

    def _check_phases_coverage(self, reporter: "Reporter") -> None:
        """FR-001: missing_from_status · FR-002: orphan_agents · FR-003: count."""
        all_phase_agents: set[str] = {
            aid
            for phase in self._phases
            for aid in phase.get("agent_ids", [])
        }
        all_status_agents: set[str] = set(self._agent_status.keys())

        # FR-001 — in PHASES but not in agentStatus
        missing = sorted(all_phase_agents - all_status_agents)
        reporter.record(
            self.NAME,
            "[ERROR] FR-001: no agents missing from agentStatus",
            len(missing) == 0,
            f"missing: {missing}" if missing else "",
        )

        # FR-002 — in agentStatus but not in PHASES
        orphans = sorted(all_status_agents - all_phase_agents)
        reporter.record(
            self.NAME,
            "[WARN] FR-002: no orphan agents in agentStatus",
            len(orphans) == 0,
            f"orphans: {orphans}" if orphans else "",
        )

        # FR-003 — count mismatch
        count_match = len(all_phase_agents) == len(all_status_agents)
        reporter.record(
            self.NAME,
            "[ERROR] FR-003: agent count matches (PHASES vs agentStatus)",
            count_match,
            (
                f"PHASES={len(all_phase_agents)}, agentStatus={len(all_status_agents)}"
                if not count_match
                else f"{len(all_phase_agents)} agents"
            ),
        )

    def _check_exec_pct(self, reporter: "Reporter") -> None:
        """FR-004: expected = round(done_count / total * 100) vs D.execPct."""
        all_agent_ids: list[str] = [
            aid
            for phase in self._phases
            for aid in phase.get("agent_ids", [])
        ]
        total = len(all_agent_ids)

        if total == 0:
            reporter.record(
                self.NAME,
                "[WARN] FR-004: execPct accuracy",
                False,
                "no agents found in PHASES",
            )
            return

        done_count = sum(
            1 for aid in all_agent_ids if self._get_status(aid) == "done"
        )
        expected = round(done_count / total * 100)

        if self._exec_pct is None:
            reporter.record(
                self.NAME,
                "[ERROR] FR-004: execPct present in D",
                False,
                "execPct not found in HTML",
            )
            return

        actual = int(self._exec_pct)
        passed = actual == expected
        reporter.record(
            self.NAME,
            "[ERROR] FR-004: execPct matches done/total*100",
            passed,
            (
                f"expected {expected}% ({done_count}/{total} done), got {actual}%"
                if not passed
                else f"{actual}% ({done_count}/{total} done)"
            ),
        )

    # Coordinator agents that intentionally produce no direct disk artifacts.
    # They delegate all output to sub-agents, so an empty artifact list is
    # expected when their phase is complete.  FR-005 must not flag these.
    # Summary agents are meta-reporters; their "artifact" is the HTML itself
    # which is not tracked in D.arts (it's the output file, not an input).
    _COORDINATOR_AGENTS: frozenset = frozenset({
        "ava-tobe-orchestrator",
        "ava-stack-orchestrator",
        "ava-qa-orchestrator",
        "ava-asis-orchestrator",
        "ava-summary",
        "ava-summary-remediation",
        "ava-summary-validate",
    })

    def _check_artifact_integrity(self, reporter: "Reporter") -> None:
        """FR-005: per-phase agents where status==done but arts==[].

        Coordinator agents (ava-tobe-orchestrator, ava-stack-orchestrator, …)
        are exempted because they delegate all output to sub-agents and are
        not expected to have direct disk artifacts.
        """
        violations: list[str] = []
        for phase in self._phases:
            for aid in phase.get("agent_ids", []):
                if aid in self._COORDINATOR_AGENTS:
                    continue  # coordinators: empty artifact list is expected
                if self._get_status(aid) == "done" and not self._get_arts(aid):
                    violations.append(aid)

        reporter.record(
            self.NAME,
            "[WARN] FR-005: no done-agents with empty artifacts",
            len(violations) == 0,
            f"done with no arts: {violations}" if violations else "",
        )

    def _check_phase_gates(self, reporter: "Reporter") -> None:
        """FR-006: per-phase completeness · FR-007: no premature transitions."""
        if not self._phases:
            reporter.record(
                self.NAME,
                "[WARN] FR-006: phase completeness",
                False,
                "no phases found in HTML",
            )
            return

        sorted_phases = sorted(self._phases, key=lambda p: p["num"])

        # FR-006 — completeness per phase (INFO = purely informational, always passes)
        incomplete = [p["num"] for p in sorted_phases if not self._is_phase_complete(p)]
        complete_nums = [p["num"] for p in sorted_phases if self._is_phase_complete(p)]
        reporter.record(
            self.NAME,
            "[INFO] FR-006: phase completeness report",
            True,  # always passes — informational only
            (
                f"complete: {complete_nums}; incomplete: {incomplete}"
                if incomplete
                else f"{len(sorted_phases)} phase(s) all complete"
            ),
        )

        # FR-007 — phase transition order.
        # Meta phases (num == 0) and the summary phase are exempt:
        # Summary agents may run at any time (they read completed artifacts).
        # Skip any pair where either side is a meta phase (num == 0).
        _META_AGENTS: frozenset = frozenset({
            "ava-summary",
            "ava-summary-remediation",
            "ava-summary-validate",
        })
        violations: list[str] = []
        for i in range(len(sorted_phases) - 1):
            phase_n = sorted_phases[i]
            phase_n1 = sorted_phases[i + 1]
            # Exempt meta phases and summary-only phases from ordering
            if phase_n.get("num", -1) == 0 or phase_n1.get("num", -1) == 0:
                continue
            phase_n1_agents = set(phase_n1.get("agent_ids", []))
            if phase_n1_agents.issubset(_META_AGENTS):
                continue
            if not self._is_phase_complete(phase_n):
                next_active = [
                    aid
                    for aid in phase_n1.get("agent_ids", [])
                    if aid not in _META_AGENTS
                    and self._get_status(aid) in ("done", "running")
                ]
                if next_active:
                    violations.append(
                        f"F{phase_n1['num']} active while F{phase_n['num']} incomplete"
                    )

        reporter.record(
            self.NAME,
            "[ERROR] FR-007: no premature phase transitions",
            len(violations) == 0,
            "; ".join(violations) if violations else "",
        )

    @staticmethod
    def _is_populated(ctx: "CheckContext", key: str) -> bool:
        """Return True when the D.* field *key* is present and non-empty.

        Supports both strict JSON (``{"k":"v"}``) and JS object notation
        (``{k:"v"}`` — unquoted keys used by the build script for kpis,
        risks, bc, gaps, etc.).  Falls back to raw-content inspection when
        ``json.loads`` fails so that the check never produces a false
        negative purely due to notation style.
        """
        raw = ctx.extract_json_slice(key)
        if raw is None:
            return False
        stripped = raw.strip()
        if not stripped or stripped in ("[]", "{}", "null"):
            return False
        # Try strict JSON first (clean path — works for agentStatus, arts, etc.)
        parsed = ctx.try_json(raw)
        if parsed is not None:
            return bool(parsed)
        # JS object notation fallback: non-empty if the slice contains at
        # least one object opening brace after the outer bracket.
        return "{" in stripped

    def _check_derived_data(self, reporter: "Reporter") -> None:
        """FR-008: if F1 complete → risks, bc, gaps must be non-empty."""
        f1_phases = [p for p in self._phases if p.get("num") == 1]

        if not f1_phases:
            reporter.record(
                self.NAME,
                "[WARN] FR-008: F1 derived data (risks/bc/gaps)",
                False,
                "phase 1 not found in PHASES",
            )
            return

        f1 = f1_phases[0]
        if not self._is_phase_complete(f1):
            reporter.record(
                self.NAME,
                "[INFO] FR-008: F1 derived data (risks/bc/gaps)",
                True,
                "F1 not yet complete — derived data check skipped",
            )
            return

        # F1 complete — risks / bc / gaps must be non-empty
        # Use _is_populated() which handles both JSON and JS object notation.
        derived_present = {
            "risks": self._is_populated(self.ctx, "risks"),
            "bc":    self._is_populated(self.ctx, "bc"),
            "gaps":  self._is_populated(self.ctx, "gaps"),
        }
        empty_fields = [k for k, ok in derived_present.items() if not ok]
        passed = len(empty_fields) == 0
        reporter.record(
            self.NAME,
            "[ERROR] FR-008: F1 complete → risks/bc/gaps non-empty",
            passed,
            f"empty or missing: {empty_fields}" if empty_fields else "risks, bc, gaps all present",
        )

    # ------------------------------------------------------------------ #
    # Entry point                                                          #
    # ------------------------------------------------------------------ #

    def run(self, reporter: "Reporter") -> None:
        print(f"\n── Suite: {self.NAME}  [{self.ctx.html_path.name}] ──")
        self._phases = self._extract_phases(self.ctx.html)
        self._load_d_fields()
        self._check_phases_coverage(reporter)
        self._check_exec_pct(reporter)
        self._check_artifact_integrity(reporter)
        self._check_phase_gates(reporter)
        self._check_derived_data(reporter)
