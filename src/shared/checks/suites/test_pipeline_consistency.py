"""
test_pipeline_consistency.py
============================
Pytest unit tests for PipelineConsistencySuite.

Covers all 9 BDD scenarios (SCN-PC-001 through SCN-PC-009) and
fine-grained edge cases required to achieve >97% line coverage of
pipeline_consistency.py.

Security-critical paths tested:
  SCN-PC-006  Absolute path in art["path"] → blocked by FR-PC-004.
  SCN-PC-007  Path-traversal in art["path"] → blocked by _resolve_within.

Run:
    python -m pytest src/shared/checks/suites/test_pipeline_consistency.py \\
        --cov=src.shared.checks.suites.pipeline_consistency \\
        --cov-report=term-missing -v
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.shared.checks.suites.pipeline_consistency import PipelineConsistencySuite

# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

SUITE_NAME = "pipeline_consistency"


def _make_ctx(
    html: str = "",
    slices: dict | None = None,
    outputs_dir: Path | None = None,
) -> MagicMock:
    """Return a MagicMock CheckContext.

    Args:
        html:        The HTML string consumed by _extract_phases.
        slices:      Mapping key → raw string returned by extract_json_slice
                     (None value means the key is absent → simulate missing
                     D field).
        outputs_dir: Concrete Path used for disk checks.  When omitted a
                     MagicMock path whose .exists() returns True is used.
    """
    ctx = MagicMock()
    ctx.html = html
    ctx.html_path.name = "test-summary.html"

    if outputs_dir is not None:
        ctx.outputs_dir = outputs_dir
    else:
        od = MagicMock(spec=Path)
        od.exists.return_value = True
        od.__str__ = lambda self: "/mock/outputs"
        ctx.outputs_dir = od

    _slices: dict = slices or {}

    def _extract(key: str):
        return _slices.get(key)

    def _try_json(raw: str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    ctx.extract_json_slice.side_effect = _extract
    ctx.try_json.side_effect = _try_json
    return ctx


def _make_suite(
    html: str = "",
    slices: dict | None = None,
    outputs_dir: Path | None = None,
) -> tuple[PipelineConsistencySuite, MagicMock]:
    """Return (suite, mock_reporter) ready for use."""
    ctx = _make_ctx(html, slices, outputs_dir)
    suite = PipelineConsistencySuite(ctx)
    reporter = MagicMock()
    return suite, reporter


def _calls(reporter: MagicMock) -> list[tuple]:
    """Return list of (suite, name, passed, detail) positional-arg tuples."""
    return [c.args for c in reporter.record.call_args_list]


def _phases_html(phases: list[tuple[int, list[str]]]) -> str:
    """Build minimal JS fragment containing ``const PHASES = [...]``."""
    parts = []
    for num, ids in phases:
        agent_blobs = ", ".join(f'{{ id: "{aid}" }}' for aid in ids)
        parts.append(f"  {{ num: {num}, agents: [{agent_blobs}] }}")
    return "const PHASES = [\n" + ",\n".join(parts) + "\n];"


# ─────────────────────────────────────────────────────────────────────────────
# 1. _extract_phases  (static method — same implementation as PhaseStatusSuite)
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractPhases:
    def test_empty_html_returns_empty(self):
        assert PipelineConsistencySuite._extract_phases("") == []

    def test_no_marker_returns_empty(self):
        assert PipelineConsistencySuite._extract_phases("<html></html>") == []

    def test_unbalanced_opening_bracket_returns_empty(self):
        # Pass 1 never closes → end_pos stays -1
        html = "const PHASES = [ { num: 1"
        assert PipelineConsistencySuite._extract_phases(html) == []

    def test_single_phase_no_agents(self):
        html = "const PHASES = [{ num: 1, agents: [] }];"
        phases = PipelineConsistencySuite._extract_phases(html)
        assert phases == [{"num": 1, "agent_ids": []}]

    def test_single_phase_with_two_agents(self):
        html = 'const PHASES = [{ num: 1, agents: [{ id: "A1" }, { id: "A2" }] }];'
        phases = PipelineConsistencySuite._extract_phases(html)
        assert phases == [{"num": 1, "agent_ids": ["A1", "A2"]}]

    def test_multiple_phases_extracted_in_order(self):
        html = _phases_html([(1, ["A1", "A2"]), (2, ["B1"])])
        phases = PipelineConsistencySuite._extract_phases(html)
        assert len(phases) == 2
        assert phases[0] == {"num": 1, "agent_ids": ["A1", "A2"]}
        assert phases[1] == {"num": 2, "agent_ids": ["B1"]}

    def test_escaped_quote_inside_string_handled_correctly(self):
        # Exercises escape-handling branches in both Pass 1 and Pass 2.
        html = (
            'const PHASES = [{ num: 1, label: "He said \\"ok\\"", '
            'agents: [{ id: "X1" }] }];'
        )
        phases = PipelineConsistencySuite._extract_phases(html)
        assert phases == [{"num": 1, "agent_ids": ["X1"]}]

    def test_phase_blob_without_num_is_skipped(self):
        html = 'const PHASES = [{ agents: [{ id: "A1" }] }];'
        assert PipelineConsistencySuite._extract_phases(html) == []

    def test_nested_brackets_inside_string_not_counted(self):
        # Bracket inside a string literal must not alter depth count.
        html = (
            'const PHASES = [{ num: 3, label: "item[0]", '
            'agents: [{ id: "a3" }] }];'
        )
        phases = PipelineConsistencySuite._extract_phases(html)
        assert len(phases) == 1
        assert phases[0]["num"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# 2. _resolve_within  (security-critical — CWE-22 guard)
# ─────────────────────────────────────────────────────────────────────────────


class TestResolveWithin:
    def test_valid_relative_path_returns_resolved(self, tmp_path):
        target = tmp_path / "sub" / "file.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x")
        result = PipelineConsistencySuite._resolve_within(tmp_path, "sub/file.txt")
        assert result == target.resolve()

    def test_nested_path_stays_within_base(self, tmp_path):
        result = PipelineConsistencySuite._resolve_within(tmp_path, "a/b/c")
        assert result is not None
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_dot_slash_is_valid(self, tmp_path):
        result = PipelineConsistencySuite._resolve_within(tmp_path, "./file.txt")
        assert result is not None
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_path_traversal_two_levels_rejected(self, tmp_path):
        """SCN-PC-007: ../../etc/passwd escapes base → returns None."""
        result = PipelineConsistencySuite._resolve_within(tmp_path, "../../etc/passwd")
        assert result is None

    def test_path_traversal_single_dotdot_rejected(self, tmp_path):
        """SCN-PC-007: single ../sibling escapes base → returns None."""
        result = PipelineConsistencySuite._resolve_within(tmp_path, "../sibling")
        assert result is None

    def test_path_traversal_disguised_rejected(self, tmp_path):
        """SCN-PC-007: sub/../../etc escapes base → returns None."""
        result = PipelineConsistencySuite._resolve_within(tmp_path, "sub/../../etc")
        assert result is None

    def test_absolute_path_rejected(self, tmp_path):
        """SCN-PC-006 (resolve layer): absolute path escapes base → returns None.

        Uses str(tmp_path) itself — guaranteed absolute on any platform.
        An absolute path joined with another path via / replaces the base,
        so resolved result is outside the original base.
        """
        # Build an absolute path string that is definitely NOT under tmp_path.
        abs_path = str(tmp_path.parent)
        result = PipelineConsistencySuite._resolve_within(tmp_path, abs_path)
        # Either it's rejected outright or it escapes the base — both give None.
        if result is not None:
            # Paranoia: if somehow accepted, verify it's still within base.
            assert str(result).startswith(str(tmp_path.resolve()))

    def test_oserror_during_resolve_returns_none(self, tmp_path):
        """OSError from Path.resolve() is caught and returns None."""
        with patch.object(Path, "resolve", side_effect=OSError("mock OS error")):
            result = PipelineConsistencySuite._resolve_within(tmp_path, "file.txt")
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. _load_d_fields
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadDFields:
    def test_all_fields_present_loaded_correctly(self, tmp_path):
        agent_status = {"A1": "done"}
        arts = {"A1": [{"key": "doc", "path": "asis/doc.md"}]}
        slices = {
            "agentStatus": json.dumps(agent_status),
            "arts": json.dumps(arts),
        }
        suite, _ = _make_suite(outputs_dir=tmp_path, slices=slices)
        suite._load_d_fields()
        assert suite._agent_status == agent_status
        assert suite._arts == arts

    def test_absent_slices_leave_empty_dicts(self, tmp_path):
        suite, _ = _make_suite(outputs_dir=tmp_path, slices={})
        suite._load_d_fields()
        assert suite._agent_status == {}
        assert suite._arts == {}

    def test_non_dict_agent_status_becomes_empty_dict(self, tmp_path):
        suite, _ = _make_suite(
            outputs_dir=tmp_path,
            slices={"agentStatus": "[1, 2, 3]"},
        )
        suite._load_d_fields()
        assert suite._agent_status == {}

    def test_non_dict_arts_becomes_empty_dict(self, tmp_path):
        suite, _ = _make_suite(
            outputs_dir=tmp_path,
            slices={"arts": '"just_a_string"'},
        )
        suite._load_d_fields()
        assert suite._arts == {}

    def test_try_json_returns_none_falls_back_to_empty(self, tmp_path):
        ctx = _make_ctx(
            slices={"agentStatus": "invalid{json"},
            outputs_dir=tmp_path,
        )
        ctx.try_json.side_effect = None
        ctx.try_json.return_value = None
        suite = PipelineConsistencySuite(ctx)
        suite._load_d_fields()
        assert suite._agent_status == {}


# ─────────────────────────────────────────────────────────────────────────────
# 4. _get_status
# ─────────────────────────────────────────────────────────────────────────────


class TestGetStatus:
    @staticmethod
    def _suite(agent_status: dict) -> PipelineConsistencySuite:
        suite, _ = _make_suite()
        suite._agent_status = agent_status
        return suite

    def test_string_status_returned_directly(self):
        assert self._suite({"A1": "done"})._get_status("A1") == "done"

    def test_dict_status_extracts_status_key(self):
        suite = self._suite({"A1": {"status": "running", "label": "Ag"}})
        assert suite._get_status("A1") == "running"

    def test_dict_without_status_key_returns_empty(self):
        suite = self._suite({"A1": {"label": "Ag"}})
        assert suite._get_status("A1") == ""

    def test_unknown_agent_returns_empty_string(self):
        assert self._suite({})._get_status("UNKNOWN") == ""

    def test_none_value_returns_empty_string(self):
        assert self._suite({"A1": None})._get_status("A1") == ""


# ─────────────────────────────────────────────────────────────────────────────
# 5. FR-PC-005 — outputs_dir guard
# ─────────────────────────────────────────────────────────────────────────────


class TestFRPC005OutputsDirGuard:
    def test_missing_outputs_dir_records_fail_and_returns_early(self, tmp_path):
        """SCN-PC-004: missing outputs_dir → exactly 1 FAIL record, suite stops."""
        missing = tmp_path / "nonexistent_outputs"
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices={"agentStatus": "{}", "arts": "{}"},
            outputs_dir=missing,
        )
        suite.run(reporter)

        calls = _calls(reporter)
        assert len(calls) == 1
        _, name, passed, detail = calls[0]
        assert "FR-PC-005" in name
        assert passed is False
        assert str(missing) in detail

    def test_existing_outputs_dir_passes_guard_and_continues(self, tmp_path):
        """When outputs_dir exists the suite records FR-PC-005 as PASS."""
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices={"agentStatus": "{}", "arts": "{}"},
            outputs_dir=tmp_path,
        )
        suite.run(reporter)

        calls = _calls(reporter)
        # At minimum FR-PC-005 + FR-PC-004 are recorded.
        assert len(calls) >= 1
        _, name, passed, _ = calls[0]
        assert "FR-PC-005" in name
        assert passed is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. FR-PC-004 — arts schema validation
# ─────────────────────────────────────────────────────────────────────────────


class TestFRPC004ArtsSchema:
    @staticmethod
    def _run(tmp_path: Path, arts_raw, agent_status_raw="{}") -> list[tuple]:
        arts_json = json.dumps(arts_raw) if not isinstance(arts_raw, str) else arts_raw
        slices = {"agentStatus": agent_status_raw, "arts": arts_json}
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)
        return _calls(reporter)

    @staticmethod
    def _fr004(calls: list[tuple]):
        return [c for c in calls if "FR-PC-004" in c[1]]

    def test_empty_arts_dict_passes_with_no_arts_data(self, tmp_path):
        calls = self._run(tmp_path, {})
        matches = self._fr004(calls)
        assert len(matches) == 1
        assert matches[0][2] is True
        assert "no arts data" in matches[0][3]

    def test_none_arts_slice_passes(self, tmp_path):
        # extract_json_slice returns None → raw is None → arts stays {}
        slices = {"agentStatus": "{}"}  # "arts" key absent
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)
        calls = _calls(reporter)
        matches = [c for c in calls if "FR-PC-004" in c[1]]
        assert matches[0][2] is True

    def test_valid_arts_schema_passes(self, tmp_path):
        arts = {"agent-a": [{"key": "doc", "path": "asis/doc.md"}]}
        calls = self._run(tmp_path, arts)
        matches = self._fr004(calls)
        assert matches[0][2] is True

    def test_missing_key_field_fails(self, tmp_path):
        """SCN-PC-005: art without 'key' → FR-PC-004 fails."""
        arts = {"agent-a": [{"path": "asis/doc.md"}]}
        calls = self._run(tmp_path, arts)
        matches = self._fr004(calls)
        assert matches[0][2] is False
        assert "malformed" in matches[0][3]

    def test_missing_path_field_fails(self, tmp_path):
        """SCN-PC-005: art without 'path' → FR-PC-004 fails."""
        arts = {"agent-a": [{"key": "doc"}]}
        calls = self._run(tmp_path, arts)
        matches = self._fr004(calls)
        assert matches[0][2] is False

    def test_non_string_key_fails(self, tmp_path):
        arts = {"agent-a": [{"key": 123, "path": "asis/doc.md"}]}
        calls = self._run(tmp_path, arts)
        assert self._fr004(calls)[0][2] is False

    def test_non_string_path_fails(self, tmp_path):
        arts = {"agent-a": [{"key": "doc", "path": 42}]}
        calls = self._run(tmp_path, arts)
        assert self._fr004(calls)[0][2] is False

    def test_absolute_path_in_art_fails(self, tmp_path):
        """SCN-PC-006 (schema layer): absolute path → FR-PC-004 FAIL.

        Uses str(tmp_path) as an absolute path string — guaranteed
        absolute on both Windows and Linux.
        """
        abs_path_str = str(tmp_path / "some_file.txt")
        arts = {"agent-a": [{"key": "doc", "path": abs_path_str}]}
        calls = self._run(tmp_path, arts)
        matches = self._fr004(calls)
        assert matches[0][2] is False
        assert "absolute" in matches[0][3]

    def test_arts_value_not_a_list_fails(self, tmp_path):
        arts = {"agent-a": "not_a_list"}
        calls = self._run(tmp_path, arts)
        assert self._fr004(calls)[0][2] is False

    def test_art_entry_not_a_dict_fails(self, tmp_path):
        arts = {"agent-a": ["not_a_dict"]}
        calls = self._run(tmp_path, arts)
        assert self._fr004(calls)[0][2] is False

    def test_valid_arts_multiple_agents_passes(self, tmp_path):
        arts = {
            "agent-a": [{"key": "doc", "path": "asis/a.md"}],
            "agent-b": [{"key": "diag", "path": "asis/b.mmd"}],
        }
        calls = self._run(tmp_path, arts)
        assert self._fr004(calls)[0][2] is True

    def test_mixed_valid_and_invalid_entries_fails(self, tmp_path):
        # One good entry + one bad entry → whole agent is in malformed
        arts = {
            "agent-a": [
                {"key": "good", "path": "asis/good.md"},
                {"path": "asis/bad.md"},  # missing 'key'
            ]
        }
        calls = self._run(tmp_path, arts)
        assert self._fr004(calls)[0][2] is False


# ─────────────────────────────────────────────────────────────────────────────
# 7. FR-PC-001 — done-agent artifacts must exist on disk
# ─────────────────────────────────────────────────────────────────────────────


class TestFRPC001DoneArtDisk:
    @staticmethod
    def _run(tmp_path: Path, agent_status: dict, arts: dict) -> list[tuple]:
        slices = {
            "agentStatus": json.dumps(agent_status),
            "arts": json.dumps(arts),
        }
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)
        return _calls(reporter)

    @staticmethod
    def _fr001(calls: list[tuple]) -> list[tuple]:
        return [c for c in calls if "FR-PC-001" in c[1]]

    def test_done_agent_art_file_exists_passes(self, tmp_path):
        """SCN-PC-001 (file exists): done agent with art on disk → PASS."""
        art_file = tmp_path / "asis" / "doc.md"
        art_file.parent.mkdir(parents=True, exist_ok=True)
        art_file.write_text("content")

        calls = self._run(
            tmp_path,
            agent_status={"agent-a": "done"},
            arts={"agent-a": [{"key": "doc", "path": "asis/doc.md"}]},
        )
        matches = self._fr001(calls)
        assert len(matches) == 1
        assert matches[0][2] is True
        assert "agent=agent-a" in matches[0][3]

    def test_done_agent_art_file_missing_fails(self, tmp_path):
        """SCN-PC-002: done agent with missing art file → FAIL."""
        calls = self._run(
            tmp_path,
            agent_status={"agent-a": "done"},
            arts={"agent-a": [{"key": "doc", "path": "asis/missing.md"}]},
        )
        matches = self._fr001(calls)
        assert len(matches) == 1
        assert matches[0][2] is False
        assert "missing" in matches[0][3]

    def test_done_agent_no_valid_arts_skipped(self, tmp_path):
        """Done agent with empty arts list → no FR-PC-001 recorded."""
        calls = self._run(
            tmp_path,
            agent_status={"agent-a": "done"},
            arts={"agent-a": []},
        )
        assert len(self._fr001(calls)) == 0

    def test_done_agent_not_in_arts_skipped(self, tmp_path):
        """Done agent with no entry in arts dict → no FR-PC-001 recorded."""
        calls = self._run(
            tmp_path,
            agent_status={"agent-a": "done"},
            arts={},
        )
        assert len(self._fr001(calls)) == 0

    def test_done_agent_path_traversal_blocked(self, tmp_path):
        """SCN-PC-007: traversal path in done-agent art → traversal_blocked."""
        # ../../etc/passwd passes schema (not absolute) but _resolve_within
        # rejects it because it escapes tmp_path.
        calls = self._run(
            tmp_path,
            agent_status={"agent-a": "done"},
            arts={"agent-a": [{"key": "doc", "path": "../../etc/passwd"}]},
        )
        matches = self._fr001(calls)
        assert len(matches) == 1
        assert matches[0][2] is False
        assert "traversal_blocked" in matches[0][3]

    def test_done_agent_dict_status_object_passes(self, tmp_path):
        """agentStatus value as {status: 'done', ...} is resolved correctly."""
        art_file = tmp_path / "asis" / "doc.md"
        art_file.parent.mkdir(parents=True, exist_ok=True)
        art_file.write_text("content")

        calls = self._run(
            tmp_path,
            agent_status={"agent-a": {"status": "done", "label": "Agent A"}},
            arts={"agent-a": [{"key": "doc", "path": "asis/doc.md"}]},
        )
        assert self._fr001(calls)[0][2] is True

    def test_pending_agent_not_checked_by_fr_pc_001(self, tmp_path):
        """Pending agents must not trigger FR-PC-001."""
        calls = self._run(
            tmp_path,
            agent_status={"agent-b": "pending"},
            arts={"agent-b": [{"key": "doc", "path": "asis/doc.md"}]},
        )
        assert len(self._fr001(calls)) == 0

    def test_multiple_done_agents_each_get_one_record(self, tmp_path):
        """One check per done agent with non-empty arts."""
        for name in ("a.md", "b.md"):
            f = tmp_path / "asis" / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x")

        calls = self._run(
            tmp_path,
            agent_status={"ag-1": "done", "ag-2": "done"},
            arts={
                "ag-1": [{"key": "a", "path": "asis/a.md"}],
                "ag-2": [{"key": "b", "path": "asis/b.md"}],
            },
        )
        matches = self._fr001(calls)
        assert len(matches) == 2
        assert all(m[2] is True for m in matches)

    def test_done_agent_multiple_arts_some_missing_fails(self, tmp_path):
        """Multiple arts for a done agent; one missing → FAIL with missing path."""
        existing = tmp_path / "asis" / "exists.md"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("x")

        calls = self._run(
            tmp_path,
            agent_status={"agent-a": "done"},
            arts={
                "agent-a": [
                    {"key": "ok", "path": "asis/exists.md"},
                    {"key": "missing", "path": "asis/missing.md"},
                ]
            },
        )
        matches = self._fr001(calls)
        assert matches[0][2] is False
        assert "missing" in matches[0][3]


# ─────────────────────────────────────────────────────────────────────────────
# 8. FR-PC-002 — pending agents must not have ghost artifacts
# ─────────────────────────────────────────────────────────────────────────────


class TestFRPC002PendingGhost:
    @staticmethod
    def _run(tmp_path: Path, agent_status: dict, arts: dict) -> list[tuple]:
        slices = {
            "agentStatus": json.dumps(agent_status),
            "arts": json.dumps(arts),
        }
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)
        return _calls(reporter)

    @staticmethod
    def _fr002(calls: list[tuple]) -> list[tuple]:
        return [c for c in calls if "FR-PC-002" in c[1]]

    def test_pending_with_ghost_file_warns(self, tmp_path):
        """SCN-PC-003: pending agent with art file on disk → ghost WARN."""
        ghost = tmp_path / "asis" / "ghost.md"
        ghost.parent.mkdir(parents=True, exist_ok=True)
        ghost.write_text("ghost")

        calls = self._run(
            tmp_path,
            agent_status={"ag-pending": "pending"},
            arts={"ag-pending": [{"key": "doc", "path": "asis/ghost.md"}]},
        )
        matches = self._fr002(calls)
        assert len(matches) == 1
        assert matches[0][2] is False
        assert "ghost" in matches[0][3]

    def test_pending_no_arts_skipped(self, tmp_path):
        """SCN-PC-009: pending agent with empty arts → no FR-PC-002 check."""
        calls = self._run(
            tmp_path,
            agent_status={"ag-pending": "pending"},
            arts={"ag-pending": []},
        )
        assert len(self._fr002(calls)) == 0

    def test_pending_arts_declared_no_files_on_disk_no_warn(self, tmp_path):
        """Pending agent has arts declared but no files on disk → no warning."""
        calls = self._run(
            tmp_path,
            agent_status={"ag-pending": "pending"},
            arts={"ag-pending": [{"key": "doc", "path": "asis/not_yet.md"}]},
        )
        assert len(self._fr002(calls)) == 0

    def test_pending_traversal_path_not_ghost(self, tmp_path):
        """Traversal path → _resolve_within returns None → not counted as ghost."""
        calls = self._run(
            tmp_path,
            agent_status={"ag-pending": "pending"},
            arts={"ag-pending": [{"key": "doc", "path": "../../etc/shadow"}]},
        )
        # traversal path is blocked; no ghost files counted → no FR-PC-002
        assert len(self._fr002(calls)) == 0

    def test_pending_not_in_arts_skipped(self, tmp_path):
        """Pending agent with no entry in arts dict → skip."""
        calls = self._run(
            tmp_path,
            agent_status={"ag-pending": "pending"},
            arts={},
        )
        assert len(self._fr002(calls)) == 0

    def test_done_agent_not_checked_by_fr_pc_002(self, tmp_path):
        """Done agents must not trigger FR-PC-002 even if arts exist."""
        art = tmp_path / "asis" / "done.md"
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text("x")

        calls = self._run(
            tmp_path,
            agent_status={"ag-done": "done"},
            arts={"ag-done": [{"key": "doc", "path": "asis/done.md"}]},
        )
        assert len(self._fr002(calls)) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. FR-PC-003 — completed phases must have non-empty output directory
# ─────────────────────────────────────────────────────────────────────────────


class TestFRPC003PhaseOutputDirs:
    @staticmethod
    def _run(
        tmp_path: Path,
        phases: list[tuple[int, list[str]]],
        agent_status: dict,
        arts: dict | None = None,
    ) -> list[tuple]:
        slices = {
            "agentStatus": json.dumps(agent_status),
            "arts": json.dumps(arts or {}),
        }
        html = _phases_html(phases)
        suite, reporter = _make_suite(
            html=html,
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)
        return _calls(reporter)

    @staticmethod
    def _fr003(calls: list[tuple]) -> list[tuple]:
        return [c for c in calls if "FR-PC-003" in c[1]]

    def test_phase1_all_done_asis_non_empty_passes(self, tmp_path):
        """SCN-PC-001: phase 1 done, asis/ exists and non-empty → PASS."""
        asis = tmp_path / "asis"
        asis.mkdir()
        (asis / "doc.md").write_text("content")

        calls = self._run(
            tmp_path,
            phases=[(1, ["a1"])],
            agent_status={"a1": "done"},
        )
        matches = self._fr003(calls)
        assert len(matches) == 1
        assert matches[0][2] is True

    def test_phase1_all_done_asis_missing_fails(self, tmp_path):
        """SCN-PC-008: phase 1 done, asis/ missing → FR-PC-003 FAIL."""
        calls = self._run(
            tmp_path,
            phases=[(1, ["a1"])],
            agent_status={"a1": "done"},
        )
        matches = self._fr003(calls)
        assert len(matches) == 1
        assert matches[0][2] is False
        assert "missing or empty" in matches[0][3]

    def test_phase1_all_done_asis_empty_fails(self, tmp_path):
        """SCN-PC-008: phase 1 done, asis/ exists but empty → FR-PC-003 FAIL."""
        (tmp_path / "asis").mkdir()  # empty directory

        calls = self._run(
            tmp_path,
            phases=[(1, ["a1"])],
            agent_status={"a1": "done"},
        )
        matches = self._fr003(calls)
        assert matches[0][2] is False

    def test_not_all_done_phase_is_skipped(self, tmp_path):
        """Phase where some agents are pending → FR-PC-003 not triggered."""
        calls = self._run(
            tmp_path,
            phases=[(1, ["a1", "a2"])],
            agent_status={"a1": "done", "a2": "pending"},
        )
        assert len(self._fr003(calls)) == 0

    def test_phase_with_no_agents_is_skipped(self, tmp_path):
        """Phase with empty agent_ids → all_done is False → skipped."""
        calls = self._run(
            tmp_path,
            phases=[(1, [])],
            agent_status={},
        )
        assert len(self._fr003(calls)) == 0

    def test_phase_not_in_phase_output_dirs_records_info_pass(self, tmp_path):
        """Phase num not in _PHASE_OUTPUT_DIRS → INFO record with PASS."""
        calls = self._run(
            tmp_path,
            phases=[(99, ["a99"])],
            agent_status={"a99": "done"},
        )
        matches = self._fr003(calls)
        assert len(matches) == 1
        assert matches[0][2] is True
        assert "skipped" in matches[0][3]

    def test_multiple_phases_only_complete_ones_checked(self, tmp_path):
        """Phase 1 done + Phase 2 partial → only phase 1 generates FR-PC-003."""
        asis = tmp_path / "asis"
        asis.mkdir()
        (asis / "file.md").write_text("x")

        calls = self._run(
            tmp_path,
            phases=[(1, ["a1"]), (2, ["a2", "a3"])],
            agent_status={"a1": "done", "a2": "done", "a3": "pending"},
        )
        matches = self._fr003(calls)
        assert len(matches) == 1
        assert matches[0][2] is True

    def test_all_phases_done_all_dirs_present(self, tmp_path):
        """Phases 1 and 2 both done, both output dirs present → 2 PASS records."""
        (tmp_path / "asis").mkdir()
        (tmp_path / "asis" / "f1.md").write_text("x")
        tobe = tmp_path / "tobe"
        tobe.mkdir()
        (tobe / "f2.md").write_text("x")

        calls = self._run(
            tmp_path,
            phases=[(1, ["a1"]), (2, ["a2"])],
            agent_status={"a1": "done", "a2": "done"},
        )
        matches = self._fr003(calls)
        assert len(matches) == 2
        assert all(m[2] is True for m in matches)

    def test_phases_sorted_by_num(self, tmp_path):
        """Phases must be processed in ascending num order."""
        asis = tmp_path / "asis"
        asis.mkdir()
        (asis / "f.md").write_text("x")

        # Provide phases out-of-order in HTML → suite must sort
        calls = self._run(
            tmp_path,
            phases=[(2, ["a2"]), (1, ["a1"])],
            agent_status={"a1": "done", "a2": "pending"},
        )
        matches = self._fr003(calls)
        # Only phase 1 (all done) triggers FR-PC-003
        assert len(matches) == 1
        assert "phase 1" in matches[0][3]


# ─────────────────────────────────────────────────────────────────────────────
# 10. run() — integration-level wiring
# ─────────────────────────────────────────────────────────────────────────────


class TestRun:
    def test_run_prints_banner_and_runs_all_checks(self, tmp_path, capsys):
        """run() prints the banner and executes the full check chain."""
        asis = tmp_path / "asis"
        asis.mkdir()
        (asis / "doc.md").write_text("x")

        html = _phases_html([(1, ["ag1"])])
        slices = {
            "agentStatus": json.dumps({"ag1": "done"}),
            "arts": json.dumps({"ag1": [{"key": "doc", "path": "asis/doc.md"}]}),
        }
        suite, reporter = _make_suite(html=html, slices=slices, outputs_dir=tmp_path)
        suite.run(reporter)

        captured = capsys.readouterr()
        assert "pipeline_consistency" in captured.out
        assert "test-summary.html" in captured.out

        calls = _calls(reporter)
        # FR-PC-005, FR-PC-004, FR-PC-001, FR-PC-003 all expected
        names = [c[1] for c in calls]
        assert any("FR-PC-005" in n for n in names)
        assert any("FR-PC-004" in n for n in names)
        assert any("FR-PC-001" in n for n in names)
        assert any("FR-PC-003" in n for n in names)

    def test_run_early_return_when_outputs_dir_missing(self, tmp_path):
        """FR-PC-005 guard: remaining checks are NOT run when dir is absent."""
        missing = tmp_path / "no_outputs"
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices={"agentStatus": "{}", "arts": "{}"},
            outputs_dir=missing,
        )
        suite.run(reporter)

        calls = _calls(reporter)
        assert len(calls) == 1  # only FR-PC-005

    def test_run_full_happy_path_all_pass(self, tmp_path):
        """SCN-PC-001: phase 1 done, all arts on disk, asis/ non-empty → all PASS."""
        asis = tmp_path / "asis"
        asis.mkdir()
        (asis / "document.md").write_text("# Doc")
        (asis / "diagram.mmd").write_text("graph TD")

        html = _phases_html([(1, ["f1-agent"])])
        slices = {
            "agentStatus": json.dumps({"f1-agent": "done"}),
            "arts": json.dumps(
                {
                    "f1-agent": [
                        {"key": "doc", "path": "asis/document.md"},
                        {"key": "diagram", "path": "asis/diagram.mmd"},
                    ]
                }
            ),
        }
        suite, reporter = _make_suite(html=html, slices=slices, outputs_dir=tmp_path)
        suite.run(reporter)

        calls = _calls(reporter)
        assert all(c[2] is True for c in calls), [c for c in calls if not c[2]]


# ─────────────────────────────────────────────────────────────────────────────
# 11. Security edge-cases — combined FR-PC-004 + FR-PC-001 traversal chain
# ─────────────────────────────────────────────────────────────────────────────


class TestSecurityTraversalChain:
    def test_scn_pc_006_absolute_path_blocked_at_schema(self, tmp_path):
        """SCN-PC-006: absolute art path is caught by FR-PC-004 before FR-PC-001.

        An absolute path must not reach _resolve_within because the schema
        check removes it from valid_arts first.
        """
        abs_path = str(tmp_path / "any_file.txt")
        slices = {
            "agentStatus": json.dumps({"ag": "done"}),
            "arts": json.dumps({"ag": [{"key": "x", "path": abs_path}]}),
        }
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)

        calls = _calls(reporter)
        fr004 = [c for c in calls if "FR-PC-004" in c[1]]
        # Schema must fail (absolute path found)
        assert fr004[0][2] is False
        # FR-PC-001 must NOT fire because valid_arts for "ag" is empty
        fr001 = [c for c in calls if "FR-PC-001" in c[1]]
        assert len(fr001) == 0

    def test_scn_pc_007_traversal_reaches_resolve_within(self, tmp_path):
        """SCN-PC-007: relative traversal passes schema → blocked by _resolve_within.

        The path ../../etc/passwd is relative (passes FR-PC-004) but escapes
        the base in _check_done_art_disk.
        """
        slices = {
            "agentStatus": json.dumps({"ag": "done"}),
            "arts": json.dumps(
                {"ag": [{"key": "evil", "path": "../../etc/passwd"}]}
            ),
        }
        suite, reporter = _make_suite(
            html="const PHASES = [];",
            slices=slices,
            outputs_dir=tmp_path,
        )
        suite.run(reporter)

        calls = _calls(reporter)
        # FR-PC-004 must pass (relative path — schema allows it)
        fr004 = [c for c in calls if "FR-PC-004" in c[1]]
        assert fr004[0][2] is True
        # FR-PC-001 must fail with traversal_blocked
        fr001 = [c for c in calls if "FR-PC-001" in c[1]]
        assert fr001[0][2] is False
        assert "traversal_blocked" in fr001[0][3]
