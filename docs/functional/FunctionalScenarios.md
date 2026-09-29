# Functional Scenarios — Pre-Execution Phase Status Validator

**Trace ID**: a1b2c3d4-7e8f-4a9b-bc10-d11e12f13a14  
**Feature**: Phase Status Validator (`PhaseStatusSuite`)  
**Date**: 2026-05-26

---

## SCN-001 — Happy Path: All Phases Consistent

**Given** a Summary HTML with `PHASES[]` declaring 41 agents across 7 phases  
**And** `agentStatus` contains exactly the same 41 agent IDs  
**And** all F1 agents (9) have status `"done"` with ≥ 1 artifact each in `D.arts`  
**And** `D.risks`, `D.bc`, `D.gaps` are non-empty arrays  
**And** `execPct` = 22 (= round(9 / 41 * 100))  
**When** I run `python -m src.shared.checks --project Meu-ERP --suite phase_status`  
**Then** all checks pass (no `[FAIL]` lines)  
**And** the suite exits with code 0

**Covers**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-008, FR-010

---

## SCN-002 — Orphan Agent in agentStatus

**Given** `agentStatus` contains the key `"ava-asis-gap-migration-analyzer"`  
**And** `"ava-asis-gap-migration-analyzer"` does NOT appear in any `PHASES[i].agents` array  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"orphan agent in agentStatus: ava-asis-gap-migration-analyzer (not in any PHASES phase)"`  
**And** the suite exits with code 1

**Covers**: FR-002

---

## SCN-003 — Agent Declared in PHASES but Missing from agentStatus

**Given** `PHASES[0].agents` declares `"ava-asis-security-review"`  
**And** `agentStatus` does NOT contain the key `"ava-asis-security-review"`  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"agent in PHASES not in agentStatus: ava-asis-security-review (F1)"`  
**And** the suite exits with code 1

**Covers**: FR-001

---

## SCN-004 — Done Agent Has No Artifacts

**Given** `agentStatus["ava-asis-security-review"] == "done"`  
**And** `D.arts["ava-asis-security-review"]` is `[]` (empty array)  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"done agent has no artifacts: ava-asis-security-review (F1)"`  
**And** the suite exits with code 1

**Covers**: FR-005

---

## SCN-005 — execPct Computed with floor() Instead of round()

**Given** 9 agents are done out of 41 (F1 complete)  
**And** the HTML shows `execPct: 21`  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"execPct mismatch: HTML=21, expected=22 (round(9/41*100)=22)"`  
**And** the suite exits with code 1

**Covers**: FR-004

---

## SCN-006 — Phase Transition Gate Violation (F2 Started While F1 Incomplete)

**Given** F1 has 8 of 9 agents done (`"ava-asis-db-analyzer"` is still `"pending"`)  
**And** F2 has at least one agent that is NOT `"pending"` (e.g., `"ava-tobe-orchestrator": "done"`)  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"phase transition violation: F2 has active agents while F1 is incomplete (8/9 done)"`  
**And** the suite exits with code 1

**Covers**: FR-007

---

## SCN-007 — F1 Complete but Derived Data Empty

**Given** all 9 F1 agents have status `"done"`  
**And** `D.risks` is `[]` (empty array)  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"F1 done but D.risks is empty (ava-asis-gaps-risks output not registered)"`  
**And** similarly for `D.bc` and `D.gaps` if also empty  
**And** the suite exits with code 1

**Covers**: FR-008

---

## SCN-008 — PHASES Agent Count Mismatch vs agentStatus

**Given** `PHASES[]` declares 41 agents in total  
**And** `agentStatus` has 40 keys (one agent missing)  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"agent count mismatch: PHASES declares 41, agentStatus has 40"`  
**And** FR-001 check subsequently identifies the missing agent ID  
**And** the suite exits with code 1

**Covers**: FR-003, FR-001

---

## SCN-009 — D.agentStatus Field Missing Entirely

**Given** the HTML does not contain the `agentStatus:` key in the `D` object  
**When** I run `--suite phase_status`  
**Then** a `[FAIL]` is reported:  
  `"agentStatus field not found in D object — cannot run phase checks"`  
**And** all subsequent phase checks are skipped (early exit)  
**And** the suite exits with code 1

**Covers**: FR-009 (notification surface), NFR-04 (graceful degradation)

---

## Scenario Coverage Matrix

| Scenario | FR-001 | FR-002 | FR-003 | FR-004 | FR-005 | FR-006 | FR-007 | FR-008 | FR-009 | FR-010 |
|----------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| SCN-001  | ✓      | ✓      | ✓      | ✓      | ✓      |        |        | ✓      |        | ✓      |
| SCN-002  |        | ✓      |        |        |        |        |        |        |        |        |
| SCN-003  | ✓      |        |        |        |        |        |        |        |        |        |
| SCN-004  |        |        |        |        | ✓      |        |        |        |        |        |
| SCN-005  |        |        |        | ✓      |        |        |        |        |        |        |
| SCN-006  |        |        |        |        |        |        | ✓      |        |        |        |
| SCN-007  |        |        |        |        |        |        |        | ✓      |        |        |
| SCN-008  | ✓      |        | ✓      |        |        |        |        |        |        |        |
| SCN-009  |        |        |        |        |        |        |        |        | ✓      |        |
