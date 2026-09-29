"""
suites/pipeline_consistency.py
===============================
Validates consistency between pipeline execution state (agentStatus, arts)
and on-disk artefacts under outputs_dir.

Functional requirements:
  FR-PC-001  Done-agent artifacts exist on disk.
  FR-PC-002  Pending agents have no ghost artifacts on disk.
  FR-PC-003  Completed phases have their output directory non-empty.
  FR-PC-004  Arts schema is valid (each entry has "key" and "path" strings).
  FR-PC-005  outputs_dir exists (guard — return early if not).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter


class PipelineConsistencySuite:
    NAME = "pipeline_consistency"

    # Phase → output subdirectory under outputs_dir
    # F4 = Protótipo (ava-prototype → tobe/prototype)
    # F5 = QA        (ava-qa-*     → qa/)
    _PHASE_OUTPUT_DIRS: dict[int, str] = {
        1: "asis",
        2: "tobe",
        3: "tobe/source-code",
        4: "tobe/prototype",
        5: "qa",
        6: "deliverables",
        7: "tobe/iac",
    }

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx
        self._phases: list[dict] = []
        self._agent_status: dict = {}
        self._arts: dict = {}

    # ------------------------------------------------------------------ #
    # Phase extraction (duplicated from PhaseStatusSuite — ADR-PC-001)    #
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
                if depth2 == 1 and ch == "{" and blob_start == -1:
                    blob_start = j
                depth2 += 1
            elif ch in "]})":
                depth2 -= 1
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
        """Load agentStatus and arts from D object."""
        raw = self.ctx.extract_json_slice("agentStatus")
        if raw is not None:
            parsed = self.ctx.try_json(raw)
            self._agent_status = parsed if isinstance(parsed, dict) else {}

        raw = self.ctx.extract_json_slice("arts")
        if raw is not None:
            parsed = self.ctx.try_json(raw)
            self._arts = parsed if isinstance(parsed, dict) else {}

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_status(self, agent_id: str) -> str:
        """Return the status string for *agent_id* from agentStatus."""
        val = self._agent_status.get(agent_id)
        if isinstance(val, dict):
            return str(val.get("status", ""))
        return str(val) if val is not None else ""

    @staticmethod
    def _resolve_within(base: Path, rel: str) -> "Path | None":
        """Return ``base / rel`` resolved only when it stays within *base*.

        Returns ``None`` when *rel* is absolute or contains ``..`` traversal
        that escapes *base*, guarding FR-PC-001/002 against malicious
        ``art[\"path\"]`` values embedded in HTML data (CWE-22).
        """
        try:
            resolved = (base / rel).resolve()
            resolved.relative_to(base.resolve())
            return resolved
        except (ValueError, OSError):
            return None

    # ------------------------------------------------------------------ #
    # Check methods                                                        #
    # ------------------------------------------------------------------ #

    def _check_outputs_dir(self, reporter: "Reporter") -> bool:
        """FR-PC-005: outputs_dir must exist — guard check."""
        exists = self.ctx.outputs_dir.exists()
        reporter.record(
            self.NAME,
            "[ERROR] FR-PC-005: outputs_dir exists",
            exists,
            str(self.ctx.outputs_dir) if not exists else "",
        )
        return exists

    def _check_arts_schema(self, reporter: "Reporter") -> dict:
        """FR-PC-004: validate arts schema.

        Returns a dict mapping agent_id → list of valid art dicts
        (entries that have both ``"key": str`` and ``"path": str``).
        Malformed entries are collected and reported but do not raise.
        """
        if not self._arts:
            reporter.record(
                self.NAME,
                "[ERROR] FR-PC-004: arts schema is valid",
                True,
                "no arts data",
            )
            return {}

        malformed: list[str] = []
        valid_arts: dict = {}

        for agent_id, arts_list in self._arts.items():
            if not isinstance(arts_list, list):
                malformed.append(f"{agent_id}: arts value is not a list")
                continue
            valid_entries: list[dict] = []
            for i, entry in enumerate(arts_list):
                if not isinstance(entry, dict):
                    malformed.append(f"{agent_id}[{i}]: entry is not a dict")
                    continue
                if not isinstance(entry.get("key"), str) or not isinstance(
                    entry.get("path"), str
                ):
                    malformed.append(
                        f"{agent_id}[{i}]: missing or invalid 'key'/'path' fields"
                    )
                    continue
                if Path(entry["path"]).is_absolute():
                    malformed.append(
                        f"{agent_id}[{i}]: 'path' must be relative (absolute paths disallowed)"
                    )
                    continue
                valid_entries.append(entry)
            valid_arts[agent_id] = valid_entries

        passed = len(malformed) == 0
        reporter.record(
            self.NAME,
            "[ERROR] FR-PC-004: arts schema is valid",
            passed,
            f"malformed entries: {malformed}" if not passed else "",
        )
        return valid_arts

    def _check_done_art_disk(self, reporter: "Reporter", valid_arts: dict) -> None:
        """FR-PC-001: done-agent artifacts must exist on disk.

        Records one check per done-agent that has non-empty valid arts.
        Done-agents with empty arts are skipped (already caught by FR-005
        in PhaseStatusSuite).
        """
        for agent_id in self._agent_status:
            if self._get_status(agent_id) != "done":
                continue
            arts = valid_arts.get(agent_id, [])
            if not arts:
                continue
            missing: list[str] = []
            traversal_blocked: list[str] = []
            for art in arts:
                safe = self._resolve_within(self.ctx.outputs_dir, art["path"])
                if safe is None:
                    traversal_blocked.append(art["path"])
                elif not safe.exists():
                    missing.append(art["path"])
            passed = not missing and not traversal_blocked
            reporter.record(
                self.NAME,
                "[ERROR] FR-PC-001: done-agent artifacts exist on disk",
                passed,
                (
                    f"agent={agent_id} missing={missing} traversal_blocked={traversal_blocked}"
                    if not passed
                    else f"agent={agent_id}"
                ),
            )

    def _check_pending_ghost(self, reporter: "Reporter", valid_arts: dict) -> None:
        """FR-PC-002: pending agents must not have ghost artifacts on disk.

        Only records a check when a pending agent unexpectedly has non-empty
        valid arts AND at least one of those paths exists on disk.
        Pending agents with empty arts (normal) are silently skipped.
        """
        for agent_id in self._agent_status:
            if self._get_status(agent_id) != "pending":
                continue
            arts = valid_arts.get(agent_id, [])
            if not arts:
                continue  # normal — pending with no arts declared
            ghost: list[str] = []
            for art in arts:
                safe = self._resolve_within(self.ctx.outputs_dir, art["path"])
                if safe is not None and safe.exists():
                    ghost.append(art["path"])
            if not ghost:
                continue  # unusual arts declared but none on disk — OK
            reporter.record(
                self.NAME,
                "[WARN] FR-PC-002: pending-agent has ghost artifacts on disk",
                False,
                f"agent={agent_id} ghost={ghost}",
            )

    def _check_phase_output_dirs(self, reporter: "Reporter") -> None:
        """FR-PC-003: completed phases must have their output directory non-empty.

        For phases not in ``_PHASE_OUTPUT_DIRS`` → skip with INFO.
        """
        sorted_phases = sorted(self._phases, key=lambda p: p["num"])
        for phase in sorted_phases:
            phase_num = phase["num"]
            agent_ids = phase.get("agent_ids", [])
            all_done = bool(agent_ids) and all(
                self._get_status(aid) == "done" for aid in agent_ids
            )
            if not all_done:
                continue

            if phase_num not in self._PHASE_OUTPUT_DIRS:
                reporter.record(
                    self.NAME,
                    "[INFO] FR-PC-003: done-phase output directory exists and non-empty",
                    True,
                    f"phase {phase_num} not in _PHASE_OUTPUT_DIRS — skipped",
                )
                continue

            phase_dir = self.ctx.outputs_dir / self._PHASE_OUTPUT_DIRS[phase_num]
            has_entries = phase_dir.exists() and any(phase_dir.iterdir())
            reporter.record(
                self.NAME,
                "[ERROR] FR-PC-003: done-phase output directory exists and non-empty",
                has_entries,
                (
                    f"phase {phase_num} → {phase_dir} (missing or empty)"
                    if not has_entries
                    else f"phase {phase_num} → {self._PHASE_OUTPUT_DIRS[phase_num]}"
                ),
            )

    # ------------------------------------------------------------------ #
    # Entry point                                                          #
    # ------------------------------------------------------------------ #

    def run(self, reporter: "Reporter") -> None:
        print(f"\n── Suite: {self.NAME}  [{self.ctx.html_path.name}] ──")
        self._phases = self._extract_phases(self.ctx.html)
        self._load_d_fields()

        # FR-PC-005 — outputs_dir guard (return early if missing)
        if not self._check_outputs_dir(reporter):
            return

        # FR-PC-004 — arts schema validation (before any disk checks)
        valid_arts = self._check_arts_schema(reporter)

        # FR-PC-001 — done-art disk existence
        self._check_done_art_disk(reporter, valid_arts)

        # FR-PC-002 — pending ghost detection
        self._check_pending_ghost(reporter, valid_arts)

        # FR-PC-003 — phase output directory gate
        self._check_phase_output_dirs(reporter)
