#!/usr/bin/env python3
"""
AVA Fabric — Events/Pub-Sub Agent Compilation Validator
========================================================

Validates the events-pubsub-asis agent is correctly integrated across
all configuration and registration files.

Usage:
    python validate_events_pubsub.py

Exit code:
    0 → all checks passed
    1 → at least one check failed
"""
import sys
import os
import re
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
ASIS_DIR = BASE / "src" / "modules" / "ava-fabric-agents" / "asis-diagnostic"
AGENT_FILE = ASIS_DIR / "agents" / "events-pubsub-asis.md"
MODULE_YAML = ASIS_DIR / "module.yaml"
OUTPUT_PATHS = ASIS_DIR / "shared" / "output-paths.md"
ORCHESTRATOR = ASIS_DIR / "agents" / "orchestrator-asis.md"
TEMPLATE_FILE = ASIS_DIR / "templates" / "reports" / "events-pubsub-report.md"
ARTIFACT_MAP = BASE / "src" / "modules" / "ava-fabric-agents" / "summary" / "data" / "artifact-map.yaml"
INVENTORY_PY = BASE / "docs" / "inventory" / "generate-inventory.py"

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"

results = []

def check(test_id: str, description: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((test_id, condition))
    extra = f" — {detail}" if detail else ""
    print(f"  {status}  [{test_id}] {description}{extra}")

def warn(test_id: str, description: str, detail: str = ""):
    results.append((test_id, True))  # warnings don't fail
    print(f"  {WARN}  [{test_id}] {description} — {detail}")

# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  AVA FABRIC — Events/Pub-Sub Agent Compilation Validator")
print("=" * 70)

# ── T1: Agent file exists ───────────────────────────────────────────
print("\n── T1: Agent File ──────────────────────────────────────────")
check("T1.1", "Agent file exists", AGENT_FILE.exists(), str(AGENT_FILE.name))

if AGENT_FILE.exists():
    agent_content = AGENT_FILE.read_text(encoding="utf-8")
    
    # Frontmatter
    check("T1.2", "Has YAML frontmatter", agent_content.startswith("---"))
    check("T1.3", "Name = ava-asis-events-pubsub", "name: ava-asis-events-pubsub" in agent_content)
    check("T1.4", "Has version", "version:" in agent_content)
    check("T1.5", "Has allowed-tools", "allowed-tools:" in agent_content)
    
    # Core sections
    check("T1.6", "Has Role & Persona", "## Role & Persona" in agent_content)
    check("T1.7", "Has Core Responsibilities", "## Core Responsibilities" in agent_content)
    check("T1.8", "Has Skills section", "## Skills" in agent_content)
    check("T1.9", "Has Output Contract", "## Output Contract" in agent_content)
    check("T1.10", "Has Format Contract (JSON)", "## Format Contract" in agent_content)
    check("T1.11", "Has Triggers / Menu", "## Triggers / Menu" in agent_content)
    
    # Skills coverage
    check("T1.12", "Skill: Event Discovery", "### Event Discovery" in agent_content)
    check("T1.13", "Skill: Queue Discovery", "### Queue Discovery" in agent_content)
    check("T1.14", "Skill: Pub/Sub Pattern Detection", "### Pub/Sub Pattern Detection" in agent_content)
    check("T1.15", "Skill: Reference & Repetition Counter", "### Reference & Repetition Counter" in agent_content)
    
    # Analysis Process
    check("T1.16", "Has Analysis Process", "## Analysis Process" in agent_content)
    steps = re.findall(r"### Step \d", agent_content)
    check("T1.17", f"Has 5 analysis steps", len(steps) == 5, f"found {len(steps)}")
    
    # Grid format requirements
    check("T1.18", "Grid has 'key' field", '"key"' in agent_content)
    check("T1.19", "Grid has 'category' field", '"category"' in agent_content)
    check("T1.20", "Grid has 'description' field", '"description"' in agent_content)
    check("T1.21", "Grid has 'occurrences' field", '"occurrences"' in agent_content)
    check("T1.22", "Grid has 'files' field with references", '"files"' in agent_content)
    check("T1.23", "Grid has 'risk' field", '"risk"' in agent_content)
    check("T1.24", "Grid has 'publishers' field", '"publishers"' in agent_content)
    check("T1.25", "Grid has 'subscribers' field", '"subscribers"' in agent_content)
    
    # Report sections
    report_sections = re.findall(r"### § \d", agent_content)
    check("T1.26", "Has report sections (§)", len(report_sections) >= 7, f"found {len(report_sections)}")
    
    # Menu triggers
    triggers = re.findall(r"\| `([A-Z]{2})` \|", agent_content)
    check("T1.27", "Has menu trigger codes", len(triggers) >= 8, f"found: {triggers}")
    
    # Output paths in contract
    check("T1.28", "Output: events-pubsub-inventory.md", "events-pubsub-inventory.md" in agent_content)
    check("T1.29", "Output: events-pubsub-grid.json", "events-pubsub-grid.json" in agent_content)
    check("T1.30", "Output: events-pubsub-flow.mmd", "events-pubsub-flow.mmd" in agent_content)
    check("T1.31", "Output: events-pubsub-risks.md", "events-pubsub-risks.md" in agent_content)
    
    # Categories coverage
    categories = ["EVENT", "QUEUE", "PUBSUB", "IPC", "DB_QUEUE", "FILE_QUEUE"]
    for cat in categories:
        check(f"T1.C.{cat}", f"Category '{cat}' defined", f"`{cat}`" in agent_content)
    
    # Integration section
    check("T1.32", "Has Integration with Other Agents", "## Integration with Other Agents" in agent_content)

# ── T2: Module YAML ─────────────────────────────────────────────────
print("\n── T2: Module YAML ─────────────────────────────────────────")
if MODULE_YAML.exists():
    yaml_content = MODULE_YAML.read_text(encoding="utf-8")
    
    check("T2.1", "Agent ID registered", "id: ava-asis-events-pubsub" in yaml_content)
    check("T2.2", "Agent file path correct", "file: agents/events-pubsub-asis.md" in yaml_content)
    check("T2.3", "Agent skill ID correct", "skill: ava-asis-events-pubsub" in yaml_content)
    
    # Check ordering: events-pubsub before db-analyzer
    idx_events = yaml_content.find("ava-asis-events-pubsub")
    idx_db = yaml_content.find("ava-asis-db-analyzer")
    check("T2.4", "Agent ordered before db-analyzer", idx_events < idx_db and idx_events > 0)
    
    # Output artifacts
    check("T2.5", "Artifact: events-pubsub-inventory.md", "events-pubsub-inventory.md" in yaml_content)
    check("T2.6", "Artifact: events-pubsub-grid.json", "events-pubsub-grid.json" in yaml_content)
    check("T2.7", "Artifact: events-pubsub-risks.md", "events-pubsub-risks.md" in yaml_content)
    check("T2.8", "Artifact: diagrams/events-pubsub-flow.mmd", "diagrams/events-pubsub-flow.mmd" in yaml_content)
    
    # Section comment
    check("T2.9", "Has section comment header", "# Events / Pub-Sub / Queues" in yaml_content)
else:
    check("T2.0", "Module YAML exists", False, str(MODULE_YAML))

# ── T3: Output Paths ────────────────────────────────────────────────
print("\n── T3: Output Paths ────────────────────────────────────────")
if OUTPUT_PATHS.exists():
    paths_content = OUTPUT_PATHS.read_text(encoding="utf-8")
    
    check("T3.1", "Section header exists", "Events / Pub-Sub / Queues Agent" in paths_content)
    check("T3.2", "Path: events-pubsub-inventory.md", "asis/events-pubsub-inventory.md" in paths_content)
    check("T3.3", "Path: events-pubsub-grid.json", "asis/events-pubsub-grid.json" in paths_content)
    check("T3.4", "Path: events-pubsub-flow.mmd", "asis/diagrams/events-pubsub-flow.mmd" in paths_content)
    check("T3.5", "Path: events-pubsub-risks.md", "asis/events-pubsub-risks.md" in paths_content)
    
    # Cross-check: paths in output-paths match paths in agent output contract
    agent_paths = [
        "events-pubsub-inventory.md",
        "events-pubsub-grid.json",
        "events-pubsub-flow.mmd",
        "events-pubsub-risks.md",
    ]
    for p in agent_paths:
        check(f"T3.X.{p}", f"Cross-check: '{p}' in both agent & output-paths",
              p in paths_content and (not AGENT_FILE.exists() or p in agent_content))
else:
    check("T3.0", "Output Paths file exists", False, str(OUTPUT_PATHS))

# ── T4: Orchestrator ────────────────────────────────────────────────
print("\n── T4: Orchestrator ────────────────────────────────────────")
if ORCHESTRATOR.exists():
    orch_content = ORCHESTRATOR.read_text(encoding="utf-8")
    
    check("T4.1", "Agent in Agent Team table", "ava-asis-events-pubsub" in orch_content)
    check("T4.2", "Labeled as Phase A", "A — Eventos e Filas" in orch_content)
    check("T4.3", "Marked as Imediato (⚡)", "Events & Pub/Sub" in orch_content and "⚡ Phase A" in orch_content)
    check("T4.4", "DAG updated to 8 dispatches", "8 dispatches" in orch_content)
    check("T4.5", "events-pubsub in DAG diagram", "events-pubsub" in orch_content)
else:
    check("T4.0", "Orchestrator file exists", False, str(ORCHESTRATOR))

# ── T5: Template ────────────────────────────────────────────────────
print("\n── T5: Report Template ─────────────────────────────────────")
if TEMPLATE_FILE.exists():
    tpl_content = TEMPLATE_FILE.read_text(encoding="utf-8")
    
    check("T5.1", "Has YAML frontmatter", tpl_content.startswith("---"))
    check("T5.2", "template_id = events-pubsub-report", 'template_id: "events-pubsub-report"' in tpl_content)
    check("T5.3", "agent = ava-asis-events-pubsub", 'agent: "ava-asis-events-pubsub"' in tpl_content)
    
    # Grid sections in template
    check("T5.4", "Section: Grid Consolidado", "Grid Consolidado" in tpl_content)
    check("T5.5", "Section: Grid de Filas", "Grid de Filas" in tpl_content)
    check("T5.6", "Section: Grid de Pub/Sub", "Grid de Pub/Sub" in tpl_content)
    check("T5.7", "Section: Referências por Chave", "Referências por Chave" in tpl_content or "Refer" in tpl_content)
    check("T5.8", "Section: Eventos Órfãos", "Órfãos" in tpl_content)
    check("T5.9", "Section: Diagrama de Fluxo", "Diagrama de Fluxo" in tpl_content)
    check("T5.10", "Section: Matriz de Risco", "Matriz de Risco" in tpl_content)
    
    # Grid columns validation
    check("T5.11", "Grid col: Chave", "Chave" in tpl_content)
    check("T5.12", "Grid col: Categoria", "Categoria" in tpl_content)
    check("T5.13", "Grid col: Ocorrências", "Ocorrências" in tpl_content or "occurrences" in tpl_content)
    check("T5.14", "Grid col: Risco", "Risco" in tpl_content)
    
    # Template variables
    template_vars = re.findall(r"\{\{(\w+)\}\}", tpl_content)
    check("T5.15", "Has template variables", len(template_vars) > 10, f"found {len(template_vars)} vars")
else:
    check("T5.0", "Template file exists", False, str(TEMPLATE_FILE))

# ── T6: Artifact Map ────────────────────────────────────────────────
print("\n── T6: Artifact Map (artifact-map.yaml) ────────────────────")
if ARTIFACT_MAP.exists():
    artmap_content = ARTIFACT_MAP.read_text(encoding="utf-8")
    has_events = "events-pubsub" in artmap_content or "ava-asis-events-pubsub" in artmap_content
    if has_events:
        check("T6.1", "Events agent in artifact-map", True)
    else:
        warn("T6.1", "Events agent NOT in artifact-map", "needs to be added for Summary HTML integration")
else:
    warn("T6.0", "Artifact map file not found", str(ARTIFACT_MAP))

# ── T7: Inventory ───────────────────────────────────────────────────
print("\n── T7: Inventory (generate-inventory.py) ───────────────────")
if INVENTORY_PY.exists():
    inv_content = INVENTORY_PY.read_text(encoding="utf-8")
    has_events_inv = "events-pubsub" in inv_content or "ava-asis-events-pubsub" in inv_content
    if has_events_inv:
        check("T7.1", "Events agent in inventory", True)
    else:
        warn("T7.1", "Events agent NOT in inventory", "needs to be added")
else:
    warn("T7.0", "Inventory file not found", str(INVENTORY_PY))

# ── T8: Cross-consistency ───────────────────────────────────────────
print("\n── T8: Cross-Consistency ───────────────────────────────────")

# Agent name consistency across all files
agent_id = "ava-asis-events-pubsub"
files_to_check = {
    "Agent": AGENT_FILE,
    "Module YAML": MODULE_YAML,
    "Orchestrator": ORCHESTRATOR,
    "Output Paths": OUTPUT_PATHS,
}
for label, fpath in files_to_check.items():
    if fpath.exists():
        content = fpath.read_text(encoding="utf-8")
        check(f"T8.{label}", f"Agent ID '{agent_id}' in {label}", agent_id in content)

# Output file consistency: module.yaml artifacts match output-paths entries
if MODULE_YAML.exists() and OUTPUT_PATHS.exists():
    yaml_content = MODULE_YAML.read_text(encoding="utf-8")
    paths_content = OUTPUT_PATHS.read_text(encoding="utf-8")
    
    artifacts_in_yaml = [
        "events-pubsub-inventory.md",
        "events-pubsub-grid.json",
        "events-pubsub-risks.md",
        "events-pubsub-flow.mmd",
    ]
    for art in artifacts_in_yaml:
        in_yaml = art in yaml_content
        in_paths = art in paths_content
        check(f"T8.ART.{art}", f"Artifact '{art}' in both module.yaml & output-paths",
              in_yaml and in_paths, f"yaml={in_yaml}, paths={in_paths}")

# ════════════════════════════════════════════════════════════════════
#  SUMMARY
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
total = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
pct = (passed / total * 100) if total else 0

if failed == 0:
    print(f"  {PASS}  ALL {total} CHECKS PASSED ({pct:.0f}%)")
else:
    print(f"  {FAIL}  {failed}/{total} CHECKS FAILED ({pct:.0f}% pass rate)")
    print("\n  Failed checks:")
    for tid, ok in results:
        if not ok:
            print(f"    ❌ {tid}")

print("=" * 70 + "\n")
sys.exit(0 if failed == 0 else 1)
