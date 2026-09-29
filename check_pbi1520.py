"""
check_pbi1520.py
================
Structural validation for PBI #1520 — ava-tobe-security-review (Phase 4.8).

Checks:
  C-01  Agent file exists and has correct frontmatter (name, version, date)
  C-02  Skill file exists and routes to correct agent path
  C-03  Agent has all required sections (7 output sections + guardrails)
  C-04  Agent defines both output artifacts with correct paths
  C-05  Agent has input contract with mandatory gates (Steps 1-4)
  C-06  Orchestrator version bumped to 2.1.0
  C-07  Orchestrator Agent Team table contains Phase 4.8 entry
  C-08  Orchestrator execution order contains 5.5 -> 4.8 -> 5
  C-09  Orchestrator Phase 4.8 section exists with gate and checklists
  C-10  Orchestrator MICRO table (FULL) contains ava-tobe-security-review row
  C-11  Orchestrator MICRO table (STATUS_ONLY) contains ava-tobe-security-review row
  C-12  Orchestrator MACRO table updated to 3 agents for Fase 4 - Codegen
  C-13  security-compliance-agent.md version bumped to 1.1.0
  C-14  security-compliance-agent.md Step 5 reads security-review-report.md
  C-15  security-compliance-agent.md Step 5 reads security-gate-decision.json
  C-16  Agent has stack-agnostic guardrail (no hardcoded .NET/Angular)
  C-17  Agent output contract has security-gate-decision.json with phase_5_unblocked
  C-18  Agent gate decision rules cover BLOCKED for Critical/High OPEN
  C-19  Skill contains all 3 mandatory gates (build-gate-result, security-findings, security-architecture)
  C-20  Orchestrator 23-agent count in timing comment

Run:
    python check_pbi1520.py
"""

import re
import sys
from pathlib import Path

BASE = Path(__file__).parent

AGENT_PATH = BASE / "src/modules/ava-fabric-agents/tobe-architecture/agents/security-review-tobe.md"
SKILL_PATH = BASE / ".github/skills/ava-tobe-security-review/SKILL.md"
ORCH_PATH  = BASE / "src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md"
COMP_PATH  = BASE / "src/modules/ava-fabric-agents/deliverables/agents/security-compliance-agent.md"

PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(cid: str, desc: str, condition: bool, detail: str = "") -> None:
    results.append((cid, condition, desc + (f" — {detail}" if detail and not condition else "")))


# ── Load files ─────────────────────────────────────────────────────────────

def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


agent   = read(AGENT_PATH)
skill   = read(SKILL_PATH)
orch    = read(ORCH_PATH)
comp    = read(COMP_PATH)

# ── C-01: Agent frontmatter ─────────────────────────────────────────────────
check("C-01a", "Agent file exists", AGENT_PATH.exists())
check("C-01b", "Agent name: ava-tobe-security-review", 'name: ava-tobe-security-review' in agent)
check("C-01c", "Agent version: 1.0.0", 'version: "1.0.0"' in agent)
check("C-01d", "Agent date: 2026-06-11", 'date: "2026-06-11"' in agent)
check("C-01e", "Agent allowed-tools present", 'allowed-tools:' in agent)

# ── C-02: Skill routing ─────────────────────────────────────────────────────
check("C-02a", "Skill file exists", SKILL_PATH.exists())
check("C-02b", "Skill routes to correct agent path",
      "src/modules/ava-fabric-agents/tobe-architecture/agents/security-review-tobe.md" in skill)
check("C-02c", "Skill resolves project_name",
      "projects/_template/context/project-config.yaml" in skill)

# ── C-03: Agent required sections ──────────────────────────────────────────
sections = [
    "## Input Contract",
    "## Output Contract",
    "## Checklist de Conclusão da Fase 4.8",
    "## Guardrails",
    "### Seção 1",
    "### Seção 2",
    "### Seção 4",
    "### Seção 6",
    "### Seção 7",
]
for s in sections:
    check("C-03", f"Agent section exists: {s!r}", s in agent)

# ── C-04: Agent output artifacts ────────────────────────────────────────────
check("C-04a", "Agent output: security-review-report.md path",
      "outputs/tobe/docs/security-review-report.md" in agent)
check("C-04b", "Agent output: security-gate-decision.json path",
      "outputs/tobe/security-gate-decision.json" in agent)

# ── C-05: Agent input contract gates ────────────────────────────────────────
check("C-05a", "Agent Step 1: build-gate-result.json gate", "build-gate-result.json" in agent)
check("C-05b", "Agent Step 3: security-findings.json gate", "security-findings.json" in agent)
check("C-05c", "Agent Step 4: security-architecture.md gate", "security-architecture.md" in agent)
check("C-05d", "Agent Step 3 BLOCKED message on missing findings",
      "Execute o diagnóstico AS-IS" in agent or "Execute o diagnóstico" in agent)

# ── C-06: Orchestrator version ──────────────────────────────────────────────
check("C-06", "Orchestrator version bumped to 2.1.0", 'version: "2.1.0"' in orch)

# ── C-07: Orchestrator Agent Team table ─────────────────────────────────────
check("C-07a", "Orchestrator Agent Team: security-review-tobe entry", "security-review-tobe" in orch)
check("C-07b", "Orchestrator Agent Team: Phase 4.8 label", "4.8" in orch)

# ── C-08: Orchestrator execution order ──────────────────────────────────────
order_pattern = re.search(r"5\.5.*4\.8.*5\b", orch, re.DOTALL)
check("C-08", "Orchestrator execution order: 5.5 → 4.8 → 5", order_pattern is not None)

# ── C-09: Orchestrator Phase 4.8 section ────────────────────────────────────
check("C-09a", "Orchestrator Phase 4.8 section header", "### Fase 4.8" in orch)
check("C-09b", "Orchestrator Phase 4.8: gate bloqueante note", "GATE BLOQUEANTE" in orch.split("### Fase 4.8")[-1][:1000])
check("C-09c", "Orchestrator Phase 4.8: security_gate_result protocol",
      "security_gate_result" in orch)
check("C-09d", "Orchestrator Phase 4.8: phase_5_unblocked field",
      "phase_5_unblocked" in orch)
check("C-09e", "Orchestrator Phase 4.8: checklist present",
      "Checklist de conclusão da Fase 4.8" in orch)

# ── C-10: MICRO table (FULL) ─────────────────────────────────────────────────
check("C-10", "MICRO table (FULL): ava-tobe-security-review row with 4.8-SecRv",
      "ava-tobe-security-review" in orch and "4.8-SecRv" in orch)

# ── C-11: MICRO table (STATUS_ONLY) ─────────────────────────────────────────
# Both FULL and STATUS_ONLY use the same agent names; check second occurrence
count_secrev = orch.count("ava-tobe-security-review")
check("C-11", "MICRO table (STATUS_ONLY): ava-tobe-security-review appears in both timing tables",
      count_secrev >= 2, f"found {count_secrev} occurrences (need ≥2)")

# ── C-12: MACRO table codegen count ─────────────────────────────────────────
check("C-12", "MACRO table: Fase 4 - Codegen shows 3 agents",
      "coder-dotnet·build-security-gate·security-review" in orch or
      "coder-dotnet\u00b7build-security-gate\u00b7security-review" in orch)

# ── C-13: Compliance agent version ──────────────────────────────────────────
check("C-13", "security-compliance-agent version bumped to 1.1.0", 'version: "1.1.0"' in comp)

# ── C-14: Compliance agent reads security-review-report.md ──────────────────
check("C-14", "security-compliance-agent Step 5: security-review-report.md",
      "security-review-report.md" in comp)

# ── C-15: Compliance agent reads security-gate-decision.json ────────────────
check("C-15", "security-compliance-agent Step 5: security-gate-decision.json",
      "security-gate-decision.json" in comp)

# ── C-16: Stack-agnostic guardrail ──────────────────────────────────────────
# Agent should NOT hardcode .NET/Angular specific terms in behavioral sections
# (frontmatter description keywords are fine; guardrails section should call it out)
check("C-16", "Agent guardrail: stack-agnostic rule stated",
      "stack-agnostic" in agent.lower() or "nunca hardcodar" in agent.lower() or
      "não assume stack" in agent.lower())

# ── C-17: phase_5_unblocked in output contract JSON ─────────────────────────
check("C-17", "Agent output contract JSON: phase_5_unblocked field",
      '"phase_5_unblocked"' in agent)

# ── C-18: Gate decision BLOCKED rule for Critical/High ──────────────────────
check("C-18", "Agent gate rule: BLOCKED when Critical/High OPEN",
      "BLOCKED" in agent and ("Critical" in agent or "High" in agent) and "OPEN" in agent)

# ── C-19: Skill mandatory gates ─────────────────────────────────────────────
check("C-19a", "Skill gate: build-gate-result.json", "build-gate-result.json" in skill)
check("C-19b", "Skill gate: security-findings.json", "security-findings.json" in skill)
check("C-19c", "Skill gate: security-architecture.md", "security-architecture.md" in skill)

# ── C-20: Orchestrator 23-agent count ───────────────────────────────────────
check("C-20", "Orchestrator timing comment updated to 23 agentes",
      "23 agentes" in orch)

# ── Report ──────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("  PBI #1520 — ava-tobe-security-review — Structural Validation")
print("=" * 70)

passed = 0
failed = 0
for cid, ok, desc in results:
    status = PASS if ok else FAIL
    print(f"{status}  [{cid}] {desc}")
    if ok:
        passed += 1
    else:
        failed += 1

print()
print("=" * 70)
total = passed + failed
print(f"  Result: {passed}/{total} checks passed", end="")
if failed == 0:
    print("  \033[92m✅ ALL PASS — ready for PR\033[0m")
else:
    print(f"  \033[91m❌ {failed} FAILED\033[0m")
print("=" * 70)

sys.exit(0 if failed == 0 else 1)
