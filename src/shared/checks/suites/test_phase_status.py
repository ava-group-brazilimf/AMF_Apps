"""
test_phase_status.py
====================
Pytest unit tests for PhaseStatusSuite.

Covers all 9 BDD scenarios (SCN-001 through SCN-009) and fine-grained
edge cases required to achieve >97% line coverage of phase_status.py.

Run:
    py -m pytest src/shared/checks/suites/test_phase_status.py \
        --cov=src.shared.checks.suites.phase_status \
        --cov-report=term-missing -v
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.shared.checks.suites.phase_status import PhaseStatusSuite

# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

SUITE_NAME = "phase_status"


def _make_ctx(html: str = "", slices: dict | None = None) -> MagicMock:
    """Return a MagicMock CheckContext.

    Args:
        html:   the HTML string consumed by _extract_phases and execPct regex.
        slices: mapping key → raw string returned by extract_json_slice
                (None means the key is absent → simulate missing D field).
    """
    ctx = MagicMock()
    ctx.html = html
    ctx.html_path.name = "test-summary.html"

    _slices: dict = slices or {}

    def _extract(key: str):
        return _slices.get(key)  # returns None when key absent

    def _try_json(raw: str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    ctx.extract_json_slice.side_effect = _extract
    ctx.try_json.side_effect = _try_json
    return ctx


def _make_suite(
    html: str = "", slices: dict | None = None
) -> tuple[PhaseStatusSuite, MagicMock]:
    """Return (suite, mock_reporter) ready for use."""
    ctx = _make_ctx(html, slices)
    suite = PhaseStatusSuite(ctx)
    reporter = MagicMock()
    return suite, reporter


def _calls(reporter: MagicMock) -> list[tuple]:
    """Return list of (suite, name, passed, detail) positional-arg tuples."""
    return [c.args for c in reporter.record.call_args_list]


def _phases_html(
    phases: list[tuple[int, list[str]]],
    exec_pct: int | float | None = None,
) -> str:
    """Build minimal JS fragment containing ``const PHASES = [...]``.

    Optionally embeds an ``execPct`` field in a ``const D = {...}`` object.
    """
    parts = []
    for num, ids in phases:
        agent_blobs = ", ".join(f'{{ id: "{aid}" }}' for aid in ids)
        parts.append(f"  {{ num: {num}, agents: [{agent_blobs}] }}")

    phases_block = "const PHASES = [\n" + ",\n".join(parts) + "\n];"
    exec_line = f"\n  execPct: {exec_pct}," if exec_pct is not None else ""
    return f"<script>\n{phases_block}\nconst D = {{{exec_line}\n}};\n</script>"


# ─────────────────────────────────────────────────────────────────────────────
# 1. _extract_phases  (static method — no context required)
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractPhases:
    def test_no_marker_returns_empty(self):
        assert PhaseStatusSuite._extract_phases("<html></html>") == []

    def test_unbalanced_opening_bracket_returns_empty(self):
        # Pass 1 never finds the closing ']' → end_pos stays -1
        html = "const PHASES = [ { num: 1"
        assert PhaseStatusSuite._extract_phases(html) == []

    def test_single_phase_two_agents(self):
        html = 'const PHASES = [{ num: 1, agents: [{ id: "A1" }, { id: "A2" }] }];'
        phases = PhaseStatusSuite._extract_phases(html)
        assert phases == [{"num": 1, "agent_ids": ["A1", "A2"]}]

    def test_multiple_phases_extracted_in_order(self):
        html = _phases_html([(1, ["A1", "A2"]), (2, ["B1"])])
        phases = PhaseStatusSuite._extract_phases(html)
        assert len(phases) == 2
        assert phases[0] == {"num": 1, "agent_ids": ["A1", "A2"]}
        assert phases[1] == {"num": 2, "agent_ids": ["B1"]}

    def test_escaped_quote_inside_string_handled_correctly(self):
        # Exercises the escape-handling branches in BOTH Pass 1 and Pass 2.
        # A backslash-escaped quote inside a string literal must not confuse
        # the depth counter.
        html = (
            'const PHASES = [{ num: 1, label: "He said \\"ok\\"", '
            'agents: [{ id: "X1" }] }];'
        )
        phases = PhaseStatusSuite._extract_phases(html)
        assert phases == [{"num": 1, "agent_ids": ["X1"]}]

    def test_phase_blob_without_num_is_skipped(self):
        # No 'num' key → regex fails → phase not appended
        html = 'const PHASES = [{ agents: [{ id: "A1" }] }];'
        assert PhaseStatusSuite._extract_phases(html) == []

    def test_empty_agents_list_yields_phase_with_empty_ids(self):
        html = "const PHASES = [{ num: 1, agents: [] }];"
        phases = PhaseStatusSuite._extract_phases(html)
        assert phases == [{"num": 1, "agent_ids": []}]


# ─────────────────────────────────────────────────────────────────────────────
# 2. _load_d_fields
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadDFields:
    def test_all_fields_present_and_loaded(self):
        agent_status = {"A1": "done"}
        arts = {"A1": ["a.md"]}
        html = "execPct: 100,"
        slices = {
            "agentStatus": json.dumps(agent_status),
            "arts": json.dumps(arts),
        }
        suite, _ = _make_suite(html, slices)
        suite._load_d_fields()

        assert suite._agent_status == agent_status
        assert suite._arts == arts
        assert suite._exec_pct == 100.0

    def test_absent_slices_leave_defaults(self):
        # extract_json_slice returns None for all keys; no execPct in HTML
        suite, _ = _make_suite("no exec pct here", {})
        suite._load_d_fields()

        assert suite._agent_status == {}
        assert suite._arts == {}
        assert suite._exec_pct is None

    def test_non_dict_agent_status_becomes_empty_dict(self):
        # try_json returns a list → not a dict → fallback to {}
        suite, _ = _make_suite("", {"agentStatus": "[1, 2, 3]"})
        suite._load_d_fields()
        assert suite._agent_status == {}

    def test_non_dict_arts_becomes_empty_dict(self):
        suite, _ = _make_suite("", {"arts": "[1, 2]"})
        suite._load_d_fields()
        assert suite._arts == {}

    def test_exec_pct_decimal_parsed_correctly(self):
        suite, _ = _make_suite("execPct: 21.95,", {})
        suite._load_d_fields()
        assert suite._exec_pct == pytest.approx(21.95)


# ─────────────────────────────────────────────────────────────────────────────
# 3. _get_status
# ─────────────────────────────────────────────────────────────────────────────


class TestGetStatus:
    @staticmethod
    def _suite(agent_status: dict) -> PhaseStatusSuite:
        suite, _ = _make_suite()
        suite._agent_status = agent_status
        return suite

    def test_string_status_returned_directly(self):
        assert self._suite({"A1": "done"})._get_status("A1") == "done"

    def test_dict_status_extracts_status_key(self):
        suite = self._suite({"A1": {"status": "running", "arts": []}})
        assert suite._get_status("A1") == "running"

    def test_dict_without_status_key_returns_empty(self):
        suite = self._suite({"A1": {"arts": []}})
        assert suite._get_status("A1") == ""

    def test_unknown_agent_returns_empty(self):
        assert self._suite({})._get_status("UNKNOWN") == ""


# ─────────────────────────────────────────────────────────────────────────────
# 4. _get_arts
# ─────────────────────────────────────────────────────────────────────────────


class TestGetArts:
    @staticmethod
    def _suite(arts: dict, agent_status: dict) -> PhaseStatusSuite:
        suite, _ = _make_suite()
        suite._arts = arts
        suite._agent_status = agent_status
        return suite

    def test_list_from_arts_dict(self):
        assert self._suite({"A1": ["file.md"]}, {})._get_arts("A1") == ["file.md"]

    def test_non_list_value_in_arts_returns_empty(self):
        # arts dict has a string instead of list → []
        assert self._suite({"A1": "file.md"}, {})._get_arts("A1") == []

    def test_arts_from_nested_agent_status_dict(self):
        suite = self._suite({}, {"A1": {"status": "done", "arts": ["a.md"]}})
        assert suite._get_arts("A1") == ["a.md"]

    def test_non_list_arts_inside_agent_status_returns_empty(self):
        suite = self._suite({}, {"A1": {"status": "done", "arts": "a.md"}})
        assert suite._get_arts("A1") == []

    def test_string_agent_status_returns_empty(self):
        # agentStatus val is a plain string (not dict) and not in arts
        assert self._suite({}, {"A1": "done"})._get_arts("A1") == []

    def test_fully_unknown_agent_returns_empty(self):
        assert self._suite({}, {})._get_arts("UNKNOWN") == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. _is_phase_complete
# ─────────────────────────────────────────────────────────────────────────────


class TestIsPhaseComplete:
    @staticmethod
    def _suite(agent_status: dict) -> PhaseStatusSuite:
        suite, _ = _make_suite()
        suite._agent_status = agent_status
        return suite

    def test_empty_agent_ids_returns_false(self):
        suite = self._suite({})
        assert suite._is_phase_complete({"num": 1, "agent_ids": []}) is False

    def test_all_done_returns_true(self):
        suite = self._suite({"A1": "done", "A2": "done"})
        assert suite._is_phase_complete({"num": 1, "agent_ids": ["A1", "A2"]}) is True

    def test_some_pending_returns_false(self):
        suite = self._suite({"A1": "done", "A2": "pending"})
        assert suite._is_phase_complete({"num": 1, "agent_ids": ["A1", "A2"]}) is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. _is_populated  (static method — takes ctx + key)
# ─────────────────────────────────────────────────────────────────────────────


class TestIsPopulated:
    def test_none_raw_returns_false(self):
        ctx = _make_ctx("", {})  # "risks" absent → extract returns None
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False

    def test_whitespace_only_returns_false(self):
        ctx = MagicMock()
        ctx.extract_json_slice.return_value = "   "
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False

    def test_empty_array_literal_returns_false(self):
        ctx = _make_ctx("", {"risks": "[]"})
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False

    def test_empty_object_literal_returns_false(self):
        ctx = _make_ctx("", {"risks": "{}"})
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False

    def test_null_literal_returns_false(self):
        ctx = _make_ctx("", {"risks": "null"})
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False

    def test_populated_json_array_returns_true(self):
        ctx = _make_ctx("", {"risks": json.dumps([{"id": "R1"}])})
        assert PhaseStatusSuite._is_populated(ctx, "risks") is True

    def test_falsy_parsed_json_returns_false(self):
        # json.loads("false") = False  →  bool(False) = False
        ctx = MagicMock()
        ctx.extract_json_slice.return_value = "false"
        ctx.try_json.return_value = False
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False

    def test_js_object_notation_fallback_returns_true(self):
        # try_json fails on unquoted-key JS syntax; '{' present → True
        ctx = MagicMock()
        ctx.extract_json_slice.return_value = '[{id:"R1", label:"test"}]'
        ctx.try_json.return_value = None
        assert PhaseStatusSuite._is_populated(ctx, "risks") is True

    def test_invalid_non_json_without_brace_returns_false(self):
        # try_json fails; no '{' in the slice → False
        ctx = MagicMock()
        ctx.extract_json_slice.return_value = "[invalid"
        ctx.try_json.return_value = None
        assert PhaseStatusSuite._is_populated(ctx, "risks") is False


# ─────────────────────────────────────────────────────────────────────────────
# 7. _check_phases_coverage  (FR-001 · FR-002 · FR-003)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckPhasesCoverage:
    @staticmethod
    def _run(phases: list[dict], agent_status: dict) -> list[tuple]:
        suite, reporter = _make_suite()
        suite._phases = phases
        suite._agent_status = agent_status
        suite._check_phases_coverage(reporter)
        return _calls(reporter)

    def test_all_pass_no_missing_no_orphans(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1", "A2"]}],
            {"A1": "done", "A2": "done"},
        )
        assert calls[0][2] is True   # FR-001
        assert calls[1][2] is True   # FR-002
        assert calls[2][2] is True   # FR-003
        assert "2 agents" in calls[2][3]

    def test_missing_agent_fails_fr001(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1", "A2", "A3"]}],
            {"A1": "done", "A2": "done"},  # A3 absent from agentStatus
        )
        assert calls[0][2] is False
        assert "A3" in calls[0][3]

    def test_orphan_agent_fails_fr002(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1"]}],
            {"A1": "done", "EXTRA": "pending"},  # EXTRA not in PHASES
        )
        assert calls[1][2] is False
        assert "EXTRA" in calls[1][3]

    def test_count_mismatch_fails_fr003(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1", "A2", "A3"]}],
            {"A1": "done", "A2": "done"},
        )
        assert calls[2][2] is False
        assert "PHASES=3" in calls[2][3]
        assert "agentStatus=2" in calls[2][3]


# ─────────────────────────────────────────────────────────────────────────────
# 8. _check_exec_pct  (FR-004)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckExecPct:
    @staticmethod
    def _run(
        phases: list[dict], agent_status: dict, exec_pct: float | None
    ) -> list[tuple]:
        suite, reporter = _make_suite()
        suite._phases = phases
        suite._agent_status = agent_status
        suite._exec_pct = exec_pct
        suite._check_exec_pct(reporter)
        return _calls(reporter)

    def test_no_agents_records_warn_false(self):
        calls = self._run([], {}, None)
        assert calls[0][1] == "[WARN] FR-004: execPct accuracy"
        assert calls[0][2] is False
        assert "no agents" in calls[0][3]

    def test_exec_pct_absent_records_error_false(self):
        calls = self._run([{"num": 1, "agent_ids": ["A1"]}], {"A1": "done"}, None)
        assert calls[0][1] == "[ERROR] FR-004: execPct present in D"
        assert calls[0][2] is False

    def test_correct_exec_pct_passes(self):
        # 3/5 done = 60 %
        phases = [{"num": 1, "agent_ids": ["A1", "A2", "A3", "A4", "A5"]}]
        status = {
            "A1": "done", "A2": "done", "A3": "done",
            "A4": "pending", "A5": "pending",
        }
        calls = self._run(phases, status, 60.0)
        assert calls[0][2] is True
        assert "60%" in calls[0][3]

    def test_wrong_exec_pct_fails_with_detail(self):
        # 9/41 done → round(21.951) = 22; HTML says 21 → fail
        phases = [{"num": 1, "agent_ids": [f"A{i}" for i in range(41)]}]
        status = {f"A{i}": ("done" if i < 9 else "pending") for i in range(41)}
        calls = self._run(phases, status, 21.0)
        assert calls[0][2] is False
        assert "expected 22%" in calls[0][3]

    def test_correct_rounding_22_percent_passes(self):
        # SCN-005: 9/41 = 21.951% → round = 22; HTML says 22 → pass
        phases = [{"num": 1, "agent_ids": [f"A{i}" for i in range(41)]}]
        status = {f"A{i}": ("done" if i < 9 else "pending") for i in range(41)}
        calls = self._run(phases, status, 22.0)
        assert calls[0][2] is True
        assert "22%" in calls[0][3]


# ─────────────────────────────────────────────────────────────────────────────
# 9. _check_artifact_integrity  (FR-005)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckArtifactIntegrity:
    @staticmethod
    def _run(
        phases: list[dict], agent_status: dict, arts: dict
    ) -> list[tuple]:
        suite, reporter = _make_suite()
        suite._phases = phases
        suite._agent_status = agent_status
        suite._arts = arts
        suite._check_artifact_integrity(reporter)
        return _calls(reporter)

    def test_no_violations_passes(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1"]}],
            {"A1": "done"},
            {"A1": ["file.md"]},
        )
        assert calls[0][2] is True

    def test_done_agent_with_empty_arts_fails(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1", "A2"]}],
            {"A1": "done", "A2": "done"},
            {"A1": [], "A2": ["file.md"]},  # A1 done but empty arts
        )
        assert calls[0][2] is False
        assert "A1" in calls[0][3]

    def test_pending_agent_with_empty_arts_does_not_fail(self):
        calls = self._run(
            [{"num": 1, "agent_ids": ["A1"]}],
            {"A1": "pending"},
            {"A1": []},
        )
        assert calls[0][2] is True


# ─────────────────────────────────────────────────────────────────────────────
# 10. _check_phase_gates  (FR-006 · FR-007)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckPhaseGates:
    @staticmethod
    def _run(phases: list[dict], agent_status: dict) -> list[tuple]:
        suite, reporter = _make_suite()
        suite._phases = phases
        suite._agent_status = agent_status
        suite._check_phase_gates(reporter)
        return _calls(reporter)

    def test_no_phases_records_only_fr006_warn(self):
        calls = self._run([], {})
        assert len(calls) == 1
        assert "FR-006" in calls[0][1]
        assert calls[0][2] is False
        assert "no phases found" in calls[0][3]

    def test_all_phases_complete_fr006_detail_says_all_complete(self):
        phases = [
            {"num": 1, "agent_ids": ["A1", "A2"]},
            {"num": 2, "agent_ids": ["B1"]},
        ]
        calls = self._run(phases, {"A1": "done", "A2": "done", "B1": "done"})
        assert calls[0][2] is True            # FR-006 always passes
        assert "all complete" in calls[0][3]
        assert calls[1][2] is True            # FR-007 no violations

    def test_some_incomplete_fr006_detail_lists_both(self):
        phases = [
            {"num": 1, "agent_ids": ["A1"]},
            {"num": 2, "agent_ids": ["B1"]},
        ]
        calls = self._run(phases, {"A1": "done", "B1": "pending"})
        assert calls[0][2] is True
        assert "complete: [1]" in calls[0][3]
        assert "incomplete: [2]" in calls[0][3]

    def test_premature_transition_fails_fr007(self):
        # SCN-006: F2 has a "running" agent while F1 has a pending agent
        phases = [
            {"num": 1, "agent_ids": ["A1", "A2"]},
            {"num": 2, "agent_ids": ["B1"]},
        ]
        calls = self._run(phases, {"A1": "done", "A2": "pending", "B1": "running"})
        assert calls[1][2] is False
        assert "F2 active while F1 incomplete" in calls[1][3]

    def test_single_phase_fr007_passes_vacuously(self):
        # Only one phase → no i+1 pair to check → no violations
        phases = [{"num": 1, "agent_ids": ["A1"]}]
        calls = self._run(phases, {"A1": "done"})
        assert calls[1][2] is True

    def test_f2_all_pending_no_fr007_violation(self):
        # F1 incomplete but F2 agents are all "pending" (not done/running)
        phases = [
            {"num": 1, "agent_ids": ["A1", "A2"]},
            {"num": 2, "agent_ids": ["B1"]},
        ]
        calls = self._run(phases, {"A1": "done", "A2": "pending", "B1": "pending"})
        assert calls[1][2] is True


# ─────────────────────────────────────────────────────────────────────────────
# 11. _check_derived_data  (FR-008)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckDerivedData:
    @staticmethod
    def _run(phases: list[dict], agent_status: dict, slices: dict) -> list[tuple]:
        suite, reporter = _make_suite("", slices)
        suite._phases = phases
        suite._agent_status = agent_status
        suite._check_derived_data(reporter)
        return _calls(reporter)

    def test_no_f1_phase_records_warn(self):
        calls = self._run(
            [{"num": 2, "agent_ids": ["B1"]}],
            {"B1": "done"},
            {},
        )
        assert calls[0][2] is False
        assert "phase 1 not found" in calls[0][3]

    def test_f1_not_complete_records_info_passing(self):
        phases = [{"num": 1, "agent_ids": ["A1", "A2"]}]
        calls = self._run(phases, {"A1": "done", "A2": "pending"}, {})
        assert calls[0][2] is True
        assert "not yet complete" in calls[0][3]

    def test_f1_complete_all_derived_present_passes(self):
        phases = [{"num": 1, "agent_ids": ["A1"]}]
        slices = {
            "risks": json.dumps([{"id": "R1"}]),
            "bc":    json.dumps([{"id": "BC1"}]),
            "gaps":  json.dumps([{"id": "G1"}]),
        }
        calls = self._run(phases, {"A1": "done"}, slices)
        assert calls[0][2] is True
        assert "risks, bc, gaps all present" in calls[0][3]

    def test_f1_complete_all_empty_fails_fr008(self):
        # SCN-007: all three derived fields are empty arrays
        phases = [{"num": 1, "agent_ids": ["A1"]}]
        calls = self._run(
            phases, {"A1": "done"},
            {"risks": "[]", "bc": "[]", "gaps": "[]"},
        )
        assert calls[0][2] is False
        assert "risks" in calls[0][3]

    def test_f1_complete_partial_empty_fails_with_detail(self):
        # Only risks missing
        phases = [{"num": 1, "agent_ids": ["A1"]}]
        slices = {
            "risks": "[]",
            "bc":    json.dumps([{"id": "BC1"}]),
            "gaps":  json.dumps([{"id": "G1"}]),
        }
        calls = self._run(phases, {"A1": "done"}, slices)
        assert calls[0][2] is False
        assert "risks" in calls[0][3]


# ─────────────────────────────────────────────────────────────────────────────
# 12. BDD Scenarios — full suite.run() integration
# ─────────────────────────────────────────────────────────────────────────────


class TestBDDScenarios:
    """End-to-end tests that exercise suite.run() for each BDD scenario."""

    @staticmethod
    def _run_full(
        phases_def: list[tuple[int, list[str]]],
        agent_status: dict,
        arts: dict | None = None,
        exec_pct: int | float | None = None,
        risks: str | None = None,
        bc: str | None = None,
        gaps: str | None = None,
    ) -> list[tuple]:
        html = _phases_html(phases_def, exec_pct)
        slices: dict = {}
        slices["agentStatus"] = json.dumps(agent_status)
        if arts is not None:
            slices["arts"] = json.dumps(arts)
        if risks is not None:
            slices["risks"] = risks
        if bc is not None:
            slices["bc"] = bc
        if gaps is not None:
            slices["gaps"] = gaps

        suite, reporter = _make_suite(html, slices)
        suite.run(reporter)
        return _calls(reporter)

    # ── SCN-001 ───────────────────────────────────────────────────────────────

    def test_scn001_happy_path_all_checks_pass(self):
        """F1 done (3 agents), F2 pending (2 agents), execPct=60,
        arts present for all done agents, derived data non-empty."""
        phases_def = [(1, ["A1", "A2", "A3"]), (2, ["B1", "B2"])]
        status = {
            "A1": "done", "A2": "done", "A3": "done",
            "B1": "pending", "B2": "pending",
        }
        arts = {"A1": ["a.md"], "A2": ["b.md"], "A3": ["c.md"]}
        calls = self._run_full(
            phases_def, status, arts, exec_pct=60,
            risks=json.dumps([{"id": "R1"}]),
            bc=json.dumps([{"id": "BC1"}]),
            gaps=json.dumps([{"id": "G1"}]),
        )
        failed = [c for c in calls if not c[2]]
        assert failed == [], f"Unexpected failures: {failed}"

    # ── SCN-002 ───────────────────────────────────────────────────────────────

    def test_scn002_orphan_agent_fr002_fails(self):
        """Extra entry in agentStatus not present in PHASES → FR-002 WARN."""
        phases_def = [(1, ["A1", "A2"])]
        status = {"A1": "done", "A2": "done", "ORPHAN": "pending"}
        calls = self._run_full(phases_def, status, exec_pct=100)
        fr002 = next(c for c in calls if "FR-002" in c[1])
        assert fr002[2] is False
        assert "ORPHAN" in fr002[3]

    # ── SCN-003 ───────────────────────────────────────────────────────────────

    def test_scn003_missing_agent_fr001_fails(self):
        """Agent in PHASES but absent from agentStatus → FR-001 ERROR."""
        phases_def = [(1, ["A1", "A2", "A3"])]
        status = {"A1": "done", "A2": "done"}  # A3 missing
        calls = self._run_full(phases_def, status, {}, exec_pct=67)
        fr001 = next(c for c in calls if "FR-001" in c[1])
        assert fr001[2] is False
        assert "A3" in fr001[3]

    # ── SCN-004 ───────────────────────────────────────────────────────────────

    def test_scn004_done_agent_empty_arts_fr005_fails(self):
        """Agent with status 'done' but empty artifact list → FR-005 WARN."""
        phases_def = [(1, ["A1", "A2"])]
        status = {"A1": "done", "A2": "done"}
        arts = {"A1": [], "A2": ["b.md"]}   # A1 done but no arts
        calls = self._run_full(phases_def, status, arts, exec_pct=100)
        fr005 = next(c for c in calls if "FR-005" in c[1])
        assert fr005[2] is False
        assert "A1" in fr005[3]

    # ── SCN-005a ──────────────────────────────────────────────────────────────

    def test_scn005a_exec_pct_22_passes(self):
        """9/41 done = 21.95% → round(22). HTML says 22 → FR-004 passes."""
        agents = [f"A{i}" for i in range(41)]
        phases_def = [(1, agents)]
        status = {a: ("done" if i < 9 else "pending") for i, a in enumerate(agents)}
        arts = {a: ["f.md"] for a in agents[:9]}
        calls = self._run_full(phases_def, status, arts, exec_pct=22)
        fr004 = next(
            c for c in calls if "FR-004" in c[1] and "execPct matches" in c[1]
        )
        assert fr004[2] is True

    # ── SCN-005b ──────────────────────────────────────────────────────────────

    def test_scn005b_exec_pct_21_fails(self):
        """9/41 done = 21.95% → round(22). HTML says 21 → FR-004 fails."""
        agents = [f"A{i}" for i in range(41)]
        phases_def = [(1, agents)]
        status = {a: ("done" if i < 9 else "pending") for i, a in enumerate(agents)}
        arts = {a: ["f.md"] for a in agents[:9]}
        calls = self._run_full(phases_def, status, arts, exec_pct=21)
        fr004 = next(
            c for c in calls if "FR-004" in c[1] and "execPct matches" in c[1]
        )
        assert fr004[2] is False
        assert "expected 22%" in fr004[3]
        assert "got 21%" in fr004[3]

    # ── SCN-006 ───────────────────────────────────────────────────────────────

    def test_scn006_premature_transition_fr007_fails(self):
        """F2 agent 'running' while F1 has a pending agent → FR-007 ERROR."""
        phases_def = [(1, ["A1", "A2"]), (2, ["B1"])]
        status = {"A1": "done", "A2": "pending", "B1": "running"}
        calls = self._run_full(phases_def, status, {}, exec_pct=33)
        fr007 = next(c for c in calls if "FR-007" in c[1])
        assert fr007[2] is False
        assert "F2 active while F1 incomplete" in fr007[3]

    # ── SCN-007 ───────────────────────────────────────────────────────────────

    def test_scn007_f1_complete_empty_derived_fr008_fails(self):
        """F1 complete but risks/bc/gaps are empty → FR-008 ERROR."""
        phases_def = [(1, ["A1"])]
        calls = self._run_full(
            phases_def, {"A1": "done"}, {"A1": ["a.md"]}, exec_pct=100,
            risks="[]", bc="[]", gaps="[]",
        )
        fr008 = next(c for c in calls if "FR-008" in c[1] and "ERROR" in c[1])
        assert fr008[2] is False

    # ── SCN-008 ───────────────────────────────────────────────────────────────

    def test_scn008_agent_count_mismatch_fr003_fails(self):
        """PHASES declares 3 agents, agentStatus has 2 → FR-003 ERROR."""
        phases_def = [(1, ["A1", "A2", "A3"])]
        status = {"A1": "done", "A2": "done"}   # A3 missing → 2 vs 3
        calls = self._run_full(phases_def, status, {}, exec_pct=67)
        fr003 = next(c for c in calls if "FR-003" in c[1])
        assert fr003[2] is False
        assert "PHASES=3" in fr003[3]
        assert "agentStatus=2" in fr003[3]

    # ── SCN-009 ───────────────────────────────────────────────────────────────

    def test_scn009_no_phases_marker_in_html(self):
        """No ``const PHASES = [...]`` in HTML → _extract_phases returns [].

        Expected outcomes:
          FR-001, FR-002, FR-003: vacuously pass (both agent sets empty).
          FR-004: WARN False (no agents in PHASES).
          FR-005: passes (no done-agents to inspect).
          FR-006: WARN False ('no phases found in HTML').
          FR-007: not recorded (early return after FR-006).
          FR-008: WARN False (phase 1 not found).
        """
        suite, reporter = _make_suite("<html>no phases here</html>", {})
        suite.run(reporter)
        calls = _calls(reporter)

        # Checks that must pass vacuously
        fr001 = next(c for c in calls if "FR-001" in c[1])
        fr002 = next(c for c in calls if "FR-002" in c[1])
        fr003 = next(c for c in calls if "FR-003" in c[1])
        assert fr001[2] is True
        assert fr002[2] is True
        assert fr003[2] is True

        # FR-006 must report 'no phases found'
        fr006 = next(c for c in calls if "FR-006" in c[1])
        assert fr006[2] is False
        assert "no phases found" in fr006[3]

        # FR-007 must NOT be recorded (early return)
        fr007_calls = [c for c in calls if "FR-007" in c[1]]
        assert fr007_calls == []
