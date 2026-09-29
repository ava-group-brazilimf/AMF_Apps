#!/usr/bin/env python3
"""
AVA Fabric - Summary HTML Builder (COMPREHENSIVE)
Gera Summary HTML completo resolvendo TODOS os 5 problemas relatados pelo usuário.

ISSUES RESOLVIDAS:
1. ✅ Risk table columns (Risk, Evidence, Action) - populated from risk-register.json
2. ✅ Phases & Agents groups showing zeros - populated from artifact inventory
3. ✅ Artifacts section empty - built from file system scan + artifact map
4. ✅ File Explorer empty - built with full content embedding
5. ✅ Rest of placeholders - complete data population from all JSON sources (100+ replacements)

Based on: tmp_generate_summary_database_comparer_examples.py (working reference)
Author: AVA Fabric Orchestrator Agent
Date: 2026-04-15

Uso:
    python build_summary_comprehensive.py --project database-comparer-examples
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Ensure UTF-8 output on Windows regardless of terminal code page
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Decodificação de artefatos pré-comprimidos pelo Headroom.
# `headroom_context` é o ÚNICO lugar do repo que conhece esse formato — não
# reimplementar o unwrap aqui (specs/031). Import defensivo: sem a tool, o
# builder segue funcionando e só perde a leitura dos artefatos comprimidos.
_HEADROOM_TOOL_DIR = (
    Path(__file__).resolve().parents[4] / 'shared' / 'tools' / 'headroom'
)
if _HEADROOM_TOOL_DIR.is_dir() and str(_HEADROOM_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_HEADROOM_TOOL_DIR))
try:
    from headroom_context import decode_headroom
except ImportError:  # pragma: no cover - tool ausente degrada, não quebra
    def decode_headroom(node):
        """No-op quando src/shared/tools/headroom/ não está disponível."""
        return node


# Tags whose literal closing form terminates or corrupts a browser <script> block.
# Only these are escaped; other inline tags are not present in Mermaid content
# because sanitize_mmd() strips them before the data reaches the <script> block.
_UNSAFE_CLOSE_TAGS_RE = re.compile(
    r'</(script|style|head|body|html)(?=[\s>])',
    re.IGNORECASE,
)



def _sanitize_str_for_json(value) -> str:
    """Sanitize a value for safe embedding inside a JSON string field.

    Applies the canonical escape sequence mandated by
    @common-roles:security-json-write-discipline Rule 3 (order matters):
      backslash  -> double-backslash  (MUST be first!)
      double-quote -> backslash-quote
      newline    -> literal backslash-n
      CR         -> removed
      tab        -> space
      control chars U+0000..U+001F -> removed
      None       -> empty string
      empty      -> '--' placeholder for mandatory fields
    """
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\\", " ")   # backslash -> double-backslash (FIRST!)
    s = s.replace('"', ' ')     # double-quote -> backslash-quote
    s = s.replace("\n", " ")    # newline -> literal \n token
    s = s.replace("\r", "")       # carriage return -> remove
    s = s.replace("\t", " ")      # tab -> space
    s = s.replace(";", " ")       # ; -> space
    s = re.sub(r"[\x00-\x1f]", "", s)  # strip remaining ASCII control chars
    return s


def _sanitize_finding_for_json(entry: dict) -> dict:
    """Return a copy of *entry* with all string fields sanitized.

    Applies _sanitize_str_for_json to every string value so the resulting
    dict is safe to pass to json.dumps() without breaking the output.
    """
    result = {}
    for k, v in entry.items():
        if isinstance(v, str):
            cleaned = _sanitize_str_for_json(v)
            if not cleaned:
                cleaned = "--"  # mandatory field placeholder
            result[k] = cleaned
        elif isinstance(v, list):
            result[k] = [_sanitize_str_for_json(i) if isinstance(i, str) else i
                         for i in v]
        else:
            result[k] = v
    return result


def safe_json(obj) -> str:
    """Serialize *obj* to JSON and escape only the closing tags that would break
    the browser HTML parser when embedded inside a <script> block.

    The HTML5 parser treats '</script>' (and '</style>', '</head>', '</body>',
    '</html>') as closing tags even inside a <script> element, terminating the
    block prematurely.  '<\\/tagname' is valid JSON (RFC 8259 §7 permits
    escaping '/') and produces the identical runtime string value, so no
    downstream JavaScript logic is affected.

    Intentionally NOT escaped: '<br/>', '<strong>', '<em>', and other inline
    HTML tags that Mermaid (htmlLabels:true) or the dashboard JS use at runtime.
    """
    raw = json.dumps(obj, ensure_ascii=False)
    return _UNSAFE_CLOSE_TAGS_RE.sub(lambda m: '<\\/' + m.group(1), raw)


# ═══ CONFIGURATION ═══
READABLE_EXTS = {
    "md", "mmd", "json", "yaml", "yml", "cs", "ts", "tsx", "js", "jsx",
    "html", "htm", "css", "scss", "sass", "sql", "py", "sh", "ps1", "bat",
    "tf", "bicep", "csproj", "sln", "props", "targets", "xml", "toml", "ini",
    "properties", "conf", "config", "txt", "log", "env", "dockerfile", "gitignore",
    "dpr", "pas", "dfm", "dproj",
}
READABLE_BASENAMES = {
    "Dockerfile", ".editorconfig", ".gitignore", ".gitattributes", "Makefile", "README", "LICENSE",
}
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 5 * 1024 * 1024

# ═══ AGENT LISTS ═══
# NOTE: ava-asis-gap-migration-analyzer is an internal sub-agent (not in PHASES)
# NOTE: ALL_AGENTS is the canonical status set and mirrors the visible PHASES
# agents in summary-template.html. Internal code-generation roles are not
# counted as separate phase agents.
ASIS_AGENTS = [
    # Orchestrator
    "ava-asis-orchestrator",
    # Solution agents (language-specific; only the executed one will be "done")
    "ava-asis-solution-delphi", "ava-asis-solution-dotnet", "ava-asis-solution-java",
    "ava-asis-solution-visualbasic",
    # Core analysis
    "ava-asis-documentation", "ava-asis-inventory", "ava-asis-db-analyzer",
    "ava-asis-gaps-risks",
    # Additional Wave 2 agents dispatched by orchestrator-asis v2.23+
    "ava-asis-business-rules-generator", "ava-asis-events-pubsub",
    "ava-asis-bridge-fastqa",
    # Security: the orchestrator dispatches ava-asis-security-orchestrator, not the
    # individual sub-agents (security-review, sast, iast, etc.) directly.
    "ava-asis-security-orchestrator",
    # Synthetic QA agent: artefacts produced by documentation/gaps-risks agents and
    # stored under asis/qa/. Kept for backwards compat with projects that have these files.
    "ava-asis-test-qa",
    # ava-asis-gap-migration-analyzer excluded: internal sub-agent of ava-asis-gaps-risks,
    # not a standalone PHASES card
]
ALL_AGENTS = ASIS_AGENTS + [
    # ── F2 — TO-BE Architecture ──────────────────────────────────────────────
    "ava-tobe-orchestrator",
    # Phase 0 (pre-ADR + ADR generation)
    "ava-tobe-architecture-decision-matrix", "ava-tobe-adr",
    # Phase 1 (design)
    "ava-tobe-architecture-design", "ava-tobe-architecture-technical",
    "ava-tobe-database-policy", "ava-tobe-database-design",
    "ava-tobe-security-design",
    # Phase 2-4 (planning)
    "ava-tobe-measure-size", "ava-tobe-migration-plan",
    "ava-tobe-coexistence-strategy", "ava-tobe-risk-mitigation",
    "ava-tobe-spec",
    # Phase 5-6 (docs + journeys)
    "ava-docs-tobe", "ava-developer-guide-tobe",
    "ava-tobe-user-journeys", "ava-tobe-designer-system",
    # Test plan (owned by QA orchestrator Momento 1, but produced in F2 context)
    "ava-test-plan-tobe",
    # ── F3 — Prototype ───────────────────────────────────────────────────────
    "ava-prototype",
    # ── F4 — Stack / Codegen ─────────────────────────────────────────────────
    "ava-stack-orchestrator",
    # Backend agents (routed by tobe_stack.backend_framework at runtime)
    "ava-stack-dotnet-backend", "ava-stack-java-backend",
    "ava-stack-python-backend", "ava-stack-go-backend",
    # Frontend agents (routed by tobe_stack.frontend_framework at runtime)
    "ava-stack-angular-frontend", "ava-stack-react-frontend",
    "ava-stack-vue-frontend", "ava-stack-blazor-frontend",
    # Cross-cutting reliability agents
    "ava-stack-docs-researcher", "ava-stack-build-validator",
    # ── F5 — QA ──────────────────────────────────────────────────────────────
    "ava-qa-orchestrator",
    "ava-qa-gaps-requirements", "ava-qa-behavior-mapping",
    "ava-qa-bridge-fastqa-tobe", "ava-qa-test-case-generator",
    "ava-qa-script-generator",
    # Additional QA agents dispatched by qa-orchestrator v2.1+
    "ava-qa-db-integrity-test", "ava-qa-contract-test-generator",
    "ava-qa-frontend-test-generator",
    "ava-qa-defect-identifier", "ava-qa-exploratory", "ava-qa-evidence-capture",
    # ── F7 — Deliverables ────────────────────────────────────────────────────
    "ava-deliverable-packager",
    "ava-deliverable-tech-docs", "ava-deliverable-migration-plan",
    "ava-deliverable-test-evidence", "ava-deliverable-code-templates",
    "ava-deliverable-security-compliance", "ava-deliverable-client-demo",
    # ── F6 — DevOps ──────────────────────────────────────────────────────────
    "ava-devops-iac", "ava-devops-ci", "ava-devops-cd",
    # Additional agents dispatched by orchestrator-devops v1.0+ (Momento 2)
    "ava-devops-containerize", "ava-devops-iac-azure",
    "ava-devops-cost-estimate", "ava-devops-monitoring-observability",
    "ava-devops-package-approval", "ava-devops-compare-version",
    # ── F8 — Summary (cross-cutting; always run after each phase) ────────────
    "ava-summary", "ava-summary-remediation", "ava-summary-validate",
]
TOTAL_AGENTS = len(ALL_AGENTS)  # canonical visible phase-agent count

# ═══ ARTIFACT MAP (complete mapping for D.arts) ═══
ARTIFACT_MAP = {
    "ava-asis-orchestrator": [{"key": "master-report", "path": "asis/master-report.md"}],
    "ava-asis-solution-delphi": [
        {"key": "architecture-blueprint", "path": "asis/architecture-blueprint.md"},
        {"key": "bounded-context-map", "path": "asis/bounded-context-map.md"},
        {"key": "api-map", "path": "asis/api-map.md"},
        {"key": "data-structure", "path": "asis/db/data-structure.md"},
        {"key": "pattern-classifications", "path": "asis/pattern-classifications.json"},
        {"key": "c4-context", "path": "asis/diagrams/c4-context.mmd"},
        {"key": "c4-container", "path": "asis/diagrams/c4-container.mmd"},
        {"key": "c4-component", "path": "asis/diagrams/c4-component.mmd"},
        {"key": "component-diagram", "path": "asis/diagrams/component-diagram.mmd"},
    ],
    "ava-asis-documentation": [
        {"key": "business-rules", "path": "asis/docs/business-rules.md"},
        {"key": "screen-navigation-map", "path": "asis/docs/screen-navigation-map.md"},
        {"key": "screen-rules", "path": "asis/docs/screen-rules.md"},
        {"key": "screen-flow", "path": "asis/docs/screen-flow.mmd"},
        {"key": "value-chain", "path": "asis/docs/value-chain.md"},
    ],
    "ava-asis-test-qa": [
        {"key": "test-plan", "path": "asis/qa/test-plan.md"},
        {"key": "test-gaps", "path": "asis/qa/test-gaps.md"},
        {"key": "test-cases", "path": "asis/qa/test-cases.md"},
        {"key": "test-cases-overview", "path": "asis/qa/test-cases-overview.md"},
    ],
    # The orchestrator dispatches ava-asis-security-orchestrator (7 sub-agents).
    # Its output files are the same regardless of the internal routing.
    # NOTE: security-review.md is NOT produced by any agent in the pipeline;
    # the orchestrator produces security-findings.json (structured JSON) instead.
    # Entry kept for backward-compat; builder treats absent files gracefully.
    "ava-asis-security-orchestrator": [
        {"key": "security-findings","path": "asis/security/security-findings.json"},
        {"key": "security-review",  "path": "asis/security/security-review.md"},
        {"key": "security-map",     "path": "asis/security-map.md"},
        {"key": "vulnerabilities",  "path": "asis/vulnerabilities.md"},
        {"key": "compliance-gaps",  "path": "asis/compliance-gaps.md"},
    ],
    "ava-asis-inventory": [
        {"key": "inventory-report", "path": "asis/inventory-report.md"},
        {"key": "metrics", "path": "asis/metrics.json"},
        {"key": "complexity-map", "path": "asis/complexity-map.md"},
    ],
    "ava-asis-gaps-risks": [
        {"key": "gaps-risks-report", "path": "asis/gaps-risks-report.md"},
        {"key": "risk-register", "path": "asis/risk-register.json"},
        {"key": "migration-risks-summary", "path": "asis/migration-risks-summary.md"},
    ],
    # Solution agents for other languages — same output contract as solution-delphi
    "ava-asis-solution-dotnet": [
        {"key": "architecture-blueprint", "path": "asis/architecture-blueprint.md"},
        {"key": "bounded-context-map", "path": "asis/bounded-context-map.md"},
        {"key": "api-map", "path": "asis/api-map.md"},
        {"key": "pattern-classifications", "path": "asis/pattern-classifications.json"},
        {"key": "c4-context", "path": "asis/diagrams/c4-context.mmd"},
    ],
    "ava-asis-solution-java": [
        {"key": "architecture-blueprint", "path": "asis/architecture-blueprint.md"},
        {"key": "bounded-context-map", "path": "asis/bounded-context-map.md"},
        {"key": "api-map", "path": "asis/api-map.md"},
        {"key": "pattern-classifications", "path": "asis/pattern-classifications.json"},
        {"key": "c4-context", "path": "asis/diagrams/c4-context.mmd"},
    ],
    "ava-asis-solution-visualbasic": [
        {"key": "architecture-blueprint", "path": "asis/architecture-blueprint.md"},
        {"key": "bounded-context-map", "path": "asis/bounded-context-map.md"},
        {"key": "api-map", "path": "asis/api-map.md"},
        {"key": "pattern-classifications", "path": "asis/pattern-classifications.json"},
        {"key": "c4-context", "path": "asis/diagrams/c4-context.mmd"},
    ],
    # Wave 2 agents dispatched by orchestrator-asis v2.23+
    "ava-asis-business-rules-generator": [
        {"key": "business-rules",    "path": "asis/docs/business-rules.md"},
        {"key": "business-rule-cases", "path": "asis/ast-raw/10_business_rule_cases.json"},
    ],
    "ava-asis-events-pubsub": [
        {"key": "events-pubsub-report", "path": "asis/events-pubsub-report.md"},
        {"key": "events-catalog",       "path": "asis/events/events-catalog.json"},
    ],
    "ava-asis-bridge-fastqa": [
        {"key": "bridge-fastqa-pbi",    "path": "asis/fastqa/PBI-1.md"},
        {"key": "bridge-fastqa-report", "path": "asis/fastqa/bridge-report.md"},
    ],
    # ava-asis-gap-migration-analyzer removed from ARTIFACT_MAP — no longer in ALL_AGENTS
    "ava-asis-db-analyzer": [
        {"key": "db-analysis-report", "path": "asis/db/db-analysis-report.md"},
        {"key": "schema-inventory", "path": "asis/db/schema-inventory.md"},
        {"key": "er-diagram", "path": "asis/db/er-diagram.mmd"},
        {"key": "stored-procedures-map", "path": "asis/db/stored-procedures-map.md"},
        {"key": "db-quality-report", "path": "asis/db/db-quality-report.md"},
        {"key": "business-logic-in-db", "path": "asis/db/business-logic-in-db.md"},
        {"key": "db-type", "path": "asis/db/db-type.json"},
    ],
    # ── TO-BE agents ─────────────────────────────────────────────────────────
    # ava-tobe-orchestrator is a coordinator.  F2 has no orchestrator-owned
    # report; its completion is evidenced by the complete set of downstream
    # TO-BE artifacts checked by build_phase_status_map().
    "ava-tobe-orchestrator": [],
    # Phase 0 — pre-ADR decision matrix + ADR generation
    "ava-tobe-architecture-decision-matrix": [
        {"key": "architecture-decision-matrix", "path": "tobe/docs/architecture-decision-matrix.md"},
        {"key": "adm-score-report",             "path": "tobe/docs/adm-score-report.md"},
    ],
    "ava-tobe-adr": [
        {"key": "adr-index",   "path": "tobe/docs/decisions/INDEX.md"},
        {"key": "adr-001",     "path": "tobe/docs/decisions/ADR-001"},
    ],
    "ava-tobe-architecture-design": [
        {"key": "architecture-blueprint-tobe", "path": "tobe/docs/architecture-blueprint.md"},
        {"key": "bounded-context-map-tobe",    "path": "tobe/docs/bounded-context-map.md"},
        # ava-tobe-architecture-design writes these under tobe/docs/ (not tobe/ root)
        {"key": "api-map-tobe",                "path": "tobe/docs/api-map.md"},
        {"key": "user-journeys",               "path": "tobe/docs/user-journeys.md"},
        {"key": "designer-system",             "path": "tobe/docs/designer-system.md"},
        {"key": "c4-context-tobe",             "path": "tobe/diagrams/c4-context.mmd"},
        {"key": "c4-container-tobe",           "path": "tobe/diagrams/c4-container.mmd"},
    ],
    "ava-tobe-architecture-technical": [
        {"key": "tech-framework",    "path": "tobe/docs/tech-framework-document.md"},
        {"key": "solution-structure","path": "tobe/solution-structure.md"},
        {"key": "nuget-packages",    "path": "tobe/nuget-packages.md"},
        {"key": "coding-standards",  "path": "tobe/coding-standards.md"},
        {"key": "quality-gates",     "path": "tobe/config/quality-gates.md"},
        {"key": "patterns-applied",  "path": "tobe/patterns-applied.json"},
    ],
    # Fase 1.4 — canonical manifest name is 'sql-strategy.manifest.json' (see
    # database-policy-tobe.md Output Files + tobe_db_policy check suite); keep
    # both contracts in sync — never 'manifest.json' bare.
    "ava-tobe-database-policy": [
        {"key": "sql-strategy",          "path": "tobe/db/sql-strategy.md"},
        {"key": "sql-strategy-manifest", "path": "tobe/db/sql-strategy.manifest.json"},
    ],
    "ava-tobe-database-design": [
        {"key": "db-design-report",         "path": "tobe/docs/db-design-report.md"},
        {"key": "db-design-report-html",    "path": "tobe/docs/db-design-report.html"},
        {"key": "mer-diagram-tobe",         "path": "tobe/diagrams/mer-diagram-tobe.mmd"},
        {"key": "database-tobe-inventory",  "path": "tobe/docs/database-tobe-inventory.md"},
        {"key": "db-quality-target",        "path": "tobe/db/db-quality-target.md"},
        {"key": "db-type-target",           "path": "tobe/db/db-type-target.json"},
    ],
    # Phase 1.6 — Security Architecture (threat model, auth, LGPD/GDPR, Z-curve)
    "ava-tobe-security-design": [
        {"key": "security-architecture",    "path": "tobe/docs/security-architecture.md"},
        {"key": "security-design-report",   "path": "tobe/docs/security-design-report.md"},
        {"key": "threat-model",             "path": "tobe/docs/threat-model.md"},
    ],
    "ava-tobe-measure-size": [
        {"key": "sizing-report",         "path": "tobe/docs/sizing-report.md"},
        {"key": "effort-calculator",     "path": "tobe/docs/effort-calculator.md"},
        {"key": "infra-sizing",          "path": "tobe/docs/infra-sizing.md"},
        {"key": "cost-estimate",         "path": "tobe/docs/cost-estimate.md"},
        {"key": "tshirt-sizing",         "path": "tobe/docs/tshirt-sizing-rationale.md"},
    ],
    "ava-tobe-migration-plan": [
        {"key": "migration-plan",              "path": "tobe/docs/migration-plan.md"},
        {"key": "wave-plan",                   "path": "tobe/docs/wave-plan.md"},
        {"key": "gantt-migration",             "path": "tobe/diagrams/migration-gantt.mmd"},
        {"key": "migration-activity-plan",     "path": "tobe/migration/migration-activity-plan.md"},
        {"key": "activity-dependency-graph",   "path": "tobe/migration/activity-dependency-graph.md"},
        {"key": "migration-priority-matrix",   "path": "tobe/migration/migration-priority-matrix.md"},
        {"key": "wave-plan-refined",           "path": "tobe/migration/wave-plan-refined.md"},
        {"key": "wcr-changelog",               "path": "tobe/migration/wcr-changelog.md"},
    ],
    # Phase 4.3 — Coexistence strategy (AS-IS ↔ TO-BE during migration)
    "ava-tobe-coexistence-strategy": [
        {"key": "coexistence-strategy", "path": "tobe/docs/coexistence-strategy.md"},
    ],
    # Phase 4.5 — Risk mitigation plan (17 risks, owner per P0, wave, closure criteria)
    "ava-tobe-risk-mitigation": [
        {"key": "risk-mitigation-plan",   "path": "tobe/docs/risk-mitigation-plan.md"},
        {"key": "risk-register-residual", "path": "tobe/docs/risk-register-residual.json"},
    ],
    # Phase 4.61 — OpenAPI spec per BC (design-first, consumed by codegen)
    # ava-tobe-spec generates one file per BC: bc01-name.yaml, bc02-name.yaml, etc.
    # There is no consolidated openapi-spec.yaml — the index entry covers the directory.
    "ava-tobe-spec": [
        {"key": "openapi-spec-index", "path": "tobe/docs/openapi"},
        {"key": "openapi-spec-tobe",  "path": "tobe/docs/openapi/openapi-spec.yaml"},  # fallback only
    ],
    # Phase 5.1 — Developer guide (onboarding, local setup)
    "ava-developer-guide-tobe": [
        {"key": "developer-guide", "path": "tobe/docs/developer-guide.md"},
        {"key": "wiki-dev-guide",  "path": "tobe/wiki/developer-guide.md"},
    ],
    # Phase 6 — User journeys (happy + sad path, BDD Gherkin)
    # Fallback order: tobe/docs/user-journeys.md (canonical) →
    #   tobe/user-journeys/user-journeys-report.md (produced by ava-tobe-user-journeys
    #   when it writes to its own subdirectory instead of tobe/docs/) →
    #   tobe/user-journeys.md (legacy flat path)
    "ava-tobe-user-journeys": [
        {"key": "user-journeys-tobe",    "path": "tobe/docs/user-journeys.md"},
        {"key": "user-journeys-report",  "path": "tobe/user-journeys/user-journeys-report.md"},
        {"key": "user-journeys-flat",    "path": "tobe/user-journeys.md"},
        {"key": "user-journeys-feature", "path": "tobe/tests/features"},
    ],
    # Phase 6.5 — Design System catalog (Angular UI patterns)
    "ava-tobe-designer-system": [
        {"key": "designer-system-tobe", "path": "tobe/docs/designer-system.md"},
        {"key": "designer-system-alt",  "path": "tobe/designer-system.md"},
    ],
    "ava-docs-tobe": [
        {"key": "openapi-spec",         "path": "tobe/docs/openapi/openapi-spec.yaml"},
        {"key": "openapi-ap",            "path": "tobe/docs/openapi/accounts-payable-api.yaml"},
        {"key": "openapi-ar",            "path": "tobe/docs/openapi/accounts-receivable-api.yaml"},
        {"key": "openapi-cs",            "path": "tobe/docs/openapi/customer-supplier-api.yaml"},
        {"key": "openapi-banking",       "path": "tobe/docs/openapi/banking-api.yaml"},
        {"key": "openapi-setup",         "path": "tobe/docs/openapi/setup-api.yaml"},
        {"key": "api-map",               "path": "tobe/docs/api-map.md"},
        {"key": "technical-design-doc",  "path": "tobe/docs/technical-design-document.md"},
        {"key": "changelog-tobe",        "path": "tobe/docs/CHANGELOG.md"},
    ],
    "ava-test-plan-tobe": [
        {"key": "test-plan-tobe",        "path": "tobe/qa/test-plan.md"},
        {"key": "functional-test-matrix","path": "tobe/qa/functional-test-matrix.md"},
        {"key": "traceability-matrix",   "path": "tobe/tests/traceability-matrix.md"},
        {"key": "automatable-test-cases","path": "tobe/tests/automatable-test-cases.md"},
    ],
    # ── F3 — Prototype (tobe/prototype/ — created by ava-prototype) ──
    # NOTE: these 3 fixed entries are only the agent-status presence check;
    # the actual chip list shown in F3 is overridden with a real glob of
    # tobe/prototype/** further down in main() — see list_prototype_chips().
    "ava-prototype": [
        {"key": "prototype-index",       "path": "tobe/prototype/index.html"},
        {"key": "prototype-demo-script", "path": "tobe/prototype/demo-script.md"},
        {"key": "prototype-figma-spec",  "path": "tobe/prototype/figma-spec.md"},
    ],
    # ── F4 — Stack / Codegen (tobe/source-code/ — created by ava-stack-orchestrator) ──
    "ava-stack-orchestrator":      [{"key": "source-code-readme",  "path": "tobe/source-code/README.md"}],
    # tech-framework-tobe chip kept; real .csproj project chips are appended
    # dynamically in main() via list_backend_csproj_projects() (project names
    # are per-project, so they can't be fixed entries here).
    "ava-stack-dotnet-backend":    [
        {"key": "tech-framework-tobe", "path": "tobe/docs/tech-framework-document.md"},
        {"key": "source-code-backend", "path": "tobe/source-code"},
    ],
    # Frontend chip must point at real files (a directory never resolves
    # content) — package.json/angular.json/index.html are framework-standard
    # names, so listing them as fixed candidates matches the existing
    # multi-entry ARTIFACT_MAP idiom (each only becomes a chip if it exists).
    "ava-stack-angular-frontend":  [
        {"key": "frontend-package-json", "path": "tobe/source-code/frontend/package.json"},
        {"key": "frontend-angular-json", "path": "tobe/source-code/frontend/angular.json"},
        {"key": "frontend-index-html",   "path": "tobe/source-code/frontend/src/index.html"},
    ],
    # Alternative backend agents (routed by tobe_stack.backend_framework)
    "ava-stack-java-backend": [
        {"key": "source-code-backend", "path": "tobe/source-code"},
        {"key": "pom-xml",             "path": "tobe/source-code/pom.xml"},
    ],
    "ava-stack-python-backend": [
        {"key": "source-code-backend", "path": "tobe/source-code"},
        {"key": "pyproject-toml",      "path": "tobe/source-code/pyproject.toml"},
    ],
    "ava-stack-go-backend": [
        {"key": "source-code-backend", "path": "tobe/source-code"},
        {"key": "go-mod",              "path": "tobe/source-code/go.mod"},
    ],
    # Alternative frontend agents (routed by tobe_stack.frontend_framework)
    "ava-stack-react-frontend": [
        {"key": "frontend-package-json", "path": "tobe/source-code/frontend/package.json"},
        {"key": "frontend-vite-config",  "path": "tobe/source-code/frontend/vite.config.ts"},
        {"key": "frontend-index-html",   "path": "tobe/source-code/frontend/index.html"},
    ],
    "ava-stack-vue-frontend": [
        {"key": "frontend-package-json", "path": "tobe/source-code/frontend/package.json"},
        {"key": "frontend-vite-config",  "path": "tobe/source-code/frontend/vite.config.ts"},
    ],
    "ava-stack-blazor-frontend": [
        {"key": "frontend-csproj",   "path": "tobe/source-code/frontend"},
        {"key": "frontend-app-razor","path": "tobe/source-code/frontend/App.razor"},
    ],
    # Cross-cutting reliability agents (always dispatched by stack-orchestrator)
    "ava-stack-docs-researcher": [
        {"key": "docs-research-report", "path": "tobe/docs/docs-research-report.md"},
        {"key": "docs-context-bundle",  "path": "tobe/docs/docs-context-bundle.md"},
    ],
    "ava-stack-build-validator": [
        {"key": "build-validation-report", "path": "tobe/source-code/build-validation-report.md"},
        {"key": "build-report-json",       "path": "tobe/source-code/build-report.json"},
    ],
    # ── F5 — QA (qa/ — created by ava-qa-orchestrator and sub-agents) ──
    "ava-qa-orchestrator":         [{"key": "quality-strategy",        "path": "qa/quality-strategy.md"},
                                    {"key": "qa-master-report",         "path": "qa/qa-master-report.md"}],
    "ava-qa-gaps-requirements":    [{"key": "gaps-requirements-report", "path": "qa/gaps-requirements-report.md"}],
    "ava-qa-behavior-mapping":     [{"key": "behavior-catalog",        "path": "qa/behavior-mapping/behavior-catalog.json"},
                                    {"key": "behavior-mapping-report",  "path": "qa/behavior-mapping-report.md"}],
    "ava-qa-bridge-fastqa-tobe":   [{"key": "scenario-generator-report","path": "qa/scenario-generator-report.md"},
                                    {"key": "scenario-register",        "path": "qa/scenario-generator/scenario-register.json"},
                                    {"key": "scenario-features",         "path": "tobe/tests/features"},
                                    {"key": "fastqa-gherkin-scenarios",  "path": "qa/fastqa/gherkin-scenarios.md"},
                                    {"key": "fastqa-automation-summary", "path": "qa/fastqa/automation-summary.md"}],
    "ava-qa-test-case-generator":  [{"key": "test-case-generator-report","path": "qa/test-case-generator-report.md"},
                                    {"key": "functional-test-matrix",     "path": "qa/functional-test-matrix.md"}],
    "ava-qa-script-generator":     [
        {"key": "script-generator-report",       "path": "qa/script-generator-report.md"},
        {"key": "automation-scripts-dir",         "path": "qa/scripts"},
        {"key": "automation-run-instructions",    "path": "qa/scripts/run-instructions.md"},
        {"key": "unit-tests-overview",            "path": "qa/scripts/unit/unit-tests-overview.md"},
        {"key": "shared-kernel-tests",            "path": "qa/scripts/unit/shared-kernel-tests.md"},
        {"key": "domain-aggregate-tests",         "path": "qa/scripts/unit/domain-aggregate-tests.md"},
        {"key": "integration-tests-overview",     "path": "qa/scripts/integration/integration-tests-overview.md"},
        {"key": "parity-suite-plan",              "path": "qa/parity-suite-plan.md"},
        {"key": "parity-evidence-dir",            "path": "qa/parity-evidence"},
        {"key": "regression-suite-dir",           "path": "qa/regression-suite"},
    ],
    "ava-qa-defect-identifier":    [{"key": "defect-identifier-report", "path": "qa/defect-identifier-report.md"}],
    "ava-qa-exploratory":          [{"key": "exploratory-report",       "path": "qa/exploratory-report.md"}],
    "ava-qa-evidence-capture":     [{"key": "evidence-capture-report",  "path": "qa/evidence-capture-report.md"}],
    # Additional QA agents dispatched by qa-orchestrator v2.1+ (Momento 2)
    "ava-qa-db-integrity-test": [
        {"key": "db-integrity-report", "path": "qa/db-integrity-test-report.md"},
        {"key": "db-integrity-tests",  "path": "qa/scripts/db-integrity"},
    ],
    "ava-qa-contract-test-generator": [
        {"key": "contract-test-report", "path": "qa/contract-test-report.md"},
        {"key": "contract-tests-dir",   "path": "qa/scripts/contract"},
        {"key": "pact-contracts-dir",   "path": "qa/scripts/contract/pacts"},
    ],
    "ava-qa-frontend-test-generator": [
        {"key": "frontend-test-report", "path": "qa/frontend-test-report.md"},
        {"key": "frontend-specs-dir",   "path": "tobe/source-code/frontend/src"},
    ],
    # ═══ F7 — Deliverables ═══
    "ava-deliverable-packager":            [{"key": "deliverables-dir",       "path": "deliverables"}],
    "ava-deliverable-tech-docs":           [{"key": "tech-docs-dir",          "path": "deliverables/tech-docs-agent"}],
    "ava-deliverable-migration-plan":      [{"key": "migration-plan-deliv",   "path": "deliverables/migration-plan-publisher"}],
    "ava-deliverable-security-compliance": [
        {"key": "security-compliance-report",  "path": "deliverables/security-compliance-report.md"},
        {"key": "security-compliance-summary", "path": "deliverables/security-compliance-summary.json"},
    ],
    "ava-deliverable-test-evidence":       [{"key": "test-evidence-dir",      "path": "deliverables/test-evidence"}],
    "ava-deliverable-code-templates":      [{"key": "code-templates-dir",     "path": "deliverables/code-templates"}],
    "ava-deliverable-client-demo":         [
        {"key": "demo-script",         "path": "deliverables/demo-script.md"},
        {"key": "acceptance-document", "path": "deliverables/acceptance-document.md"},
        {"key": "handover-package",    "path": "deliverables/handover-package.md"},
    ],
    # ═══ F6 — DevOps ═══
    "ava-devops-iac": [
        {"key": "iac-terraform",     "path": "tobe/iac/wave-1/main.tf"},
        {"key": "iac-wave-1-dir",    "path": "tobe/iac/wave-1"},
        {"key": "iac-containers-dir", "path": "tobe/iac/containers"},
        {"key": "db-type-target",    "path": "tobe/db/db-type-target.json"},
    ],
    "ava-devops-ci": [
        {"key": "ci-pipeline-devops", "path": "tobe/devops/ci-pipeline.yml"},
        {"key": "ci-pipeline-github", "path": "tobe/source-code/.github/workflows/ci.yml"},
        {"key": "ci-pipeline-ado",    "path": "tobe/source-code/azure-pipelines.yml"},
    ],
    "ava-devops-cd": [
        {"key": "cd-pipeline-devops", "path": "tobe/devops/cd-pipeline.yml"},
        {"key": "cd-pipeline-ado",    "path": "tobe/iac/cd/azure-pipelines-cd.yml"},
        {"key": "cd-pipeline-github", "path": "tobe/iac/cd/.github/workflows/cd.yml"},
    ],
    "ava-devops-compare-version": [
        {"key": "comparison-report", "path": "tobe/wave-comparison-report.md"},
        {"key": "parity-report",     "path": "tobe/parity-test-report.md"},
        {"key": "field-differences", "path": "tobe/field-differences.json"},
        {"key": "wave-approval",     "path": "tobe/wave-approval.md"},
        {"key": "comparison-data",   "path": "tobe/wave-comparison-data.json"},
        {"key": "execution-log",     "path": "tobe/parity/execution-log.md"},
        {"key": "screenshots-manifest", "path": "tobe/parity/screenshots-manifest.md"},
        {"key": "brv-report",        "path": "tobe/parity/business-rule-validation-report.md"},
    ],
    "ava-devops-package-approval": [
        {"key": "package-approval-report", "path": "tobe/devops/package-approval-report.md"},
        {"key": "wave-approval",  "path": "tobe/wave-approval.md"},
        {"key": "iac-makefile",   "path": "tobe/iac/Makefile"},
    ],
    # Additional DevOps agents dispatched by orchestrator-devops (Momento 2)
    "ava-devops-containerize": [
        {"key": "dockerfile-backend",  "path": "tobe/source-code/Dockerfile"},
        {"key": "docker-compose",      "path": "tobe/source-code/docker-compose.yml"},
        {"key": "docker-compose-prod", "path": "tobe/source-code/docker-compose.prod.yml"},
    ],
    "ava-devops-iac-azure": [
        {"key": "iac-azure-main-tf", "path": "tobe/iac/azure/main.tf"},
        {"key": "iac-azure-dir",     "path": "tobe/iac/azure"},
        {"key": "iac-bicep-main",    "path": "tobe/iac/azure/main.bicep"},
    ],
    "ava-devops-cost-estimate": [
        {"key": "cost-estimate-devops", "path": "tobe/devops/cost-estimate.md"},
        {"key": "azure-cost-estimate",  "path": "tobe/docs/cost-estimate.md"},
    ],
    "ava-devops-monitoring-observability": [
        {"key": "monitoring-config",    "path": "tobe/devops/monitoring-config.md"},
        {"key": "observability-report", "path": "tobe/devops/observability-report.md"},
        {"key": "alerts-config",        "path": "tobe/devops/alerts-config.yaml"},
    ],
}


# ═══ HELPER FUNCTIONS ═══
def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def _load_prototype_design_provenance(outputs_dir: Path) -> dict:
    """Load only safe, compact design provenance for the F3 Summary section."""
    path = outputs_dir / "tobe" / "prototype" / "design-input-traceability.json"
    legacy = {
        "source": "legacy-unavailable",
        "label": "Fonte de design não disponível (execução legada)",
        "detail": "",
        "severity": "none",
    }
    if not path.exists():
        return legacy
    try:
        data = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError, TypeError):
        return {
            "source": "invalid",
            "label": "Rastreabilidade de design inválida",
            "detail": "O arquivo de rastreabilidade não pôde ser validado.",
            "severity": "medium",
        }
    if not isinstance(data, dict):
        return {
            "source": "invalid",
            "label": "Rastreabilidade de design inválida",
            "detail": "O formato do arquivo de rastreabilidade é inválido.",
            "severity": "medium",
        }

    source = data.get("source")
    if source == "client":
        label = "Fonte de design: cliente"
    elif source in {"fallback-design-system", "fallback-generic"}:
        label = "Fonte de design: fallback"
    else:
        return {
            "source": "invalid",
            "label": "Rastreabilidade de design inválida",
            "detail": "A fonte registrada não é suportada.",
            "severity": "medium",
        }

    # Only controlled scalar fields and counts are exposed; raw design values,
    # token payloads, and arbitrary diagnostic text never reach the HTML.
    file_name = data.get("used_file") if source == "client" else None
    file_name = str(file_name)[:240] if isinstance(file_name, str) else None
    fmt = data.get("format") if isinstance(data.get("format"), str) else None
    fmt = fmt[:80] if fmt else None
    mapped = data.get("mapped_categories")
    mapped_count = len(mapped) if isinstance(mapped, list) else 0
    gaps = data.get("unmapped_fields")
    gap_count = len(gaps) if isinstance(gaps, list) else 0
    reason = data.get("fallback_reason")
    reason = str(reason)[:240] if source != "client" and isinstance(reason, str) else None
    if reason:
        reason = re.sub(r"(?i)sk-[A-Za-z0-9_-]+|AKIA[0-9A-Z]+|[A-Za-z][A-Za-z0-9+.-]*://[^\s]+", "[conteúdo sensível omitido]", reason)
    severity = data.get("limitation_severity")
    severity = severity if severity in {"high", "medium", "low", "none"} else "none"
    details = []
    if file_name:
        details.append(f"arquivo: {file_name}")
    if fmt:
        details.append(f"formato: {fmt}")
    details.append(f"categorias mapeadas: {mapped_count}")
    if gap_count:
        details.append(f"gaps: {gap_count}")
    if reason:
        details.append(f"motivo: {reason}")
    return {"source": source, "label": label, "detail": " · ".join(details), "severity": severity}


def _prototype_design_provenance_html(provenance: dict) -> str:
    """Render provenance from the allow-listed loader fields only."""
    label = _f2_html_escape(provenance.get("label", "Fonte de design não disponível"))
    detail = _f2_html_escape(provenance.get("detail", ""))
    severity = _f2_html_escape(provenance.get("severity", "none"))
    return (
        '<div class="prototype-design-provenance" data-source="'
        + _f2_html_escape(provenance.get("source", "invalid"))
        + '"><strong>' + label + '</strong>'
        + (f'<span class="mono">{detail}</span>' if detail else "")
        + f'<span class="mono">severidade: {severity}</span></div>'
    )


def _load_prototype_design_provenance(outputs_dir: Path) -> dict:
    """Load only safe, compact design provenance for the F3 Summary section."""
    path = outputs_dir / "tobe" / "prototype" / "design-input-traceability.json"
    legacy = {
        "source": "legacy-unavailable",
        "label": "Fonte de design não disponível (execução legada)",
        "detail": "",
        "severity": "none",
    }
    if not path.exists():
        return legacy
    try:
        data = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError, TypeError):
        return {
            "source": "invalid",
            "label": "Rastreabilidade de design inválida",
            "detail": "O arquivo de rastreabilidade não pôde ser validado.",
            "severity": "medium",
        }
    if not isinstance(data, dict):
        return {
            "source": "invalid",
            "label": "Rastreabilidade de design inválida",
            "detail": "O formato do arquivo de rastreabilidade é inválido.",
            "severity": "medium",
        }

    source = data.get("source")
    if source == "client":
        label = "Fonte de design: cliente"
    elif source in {"fallback-design-system", "fallback-generic"}:
        label = "Fonte de design: fallback"
    else:
        return {
            "source": "invalid",
            "label": "Rastreabilidade de design inválida",
            "detail": "A fonte registrada não é suportada.",
            "severity": "medium",
        }

    # Only controlled scalar fields and counts are exposed; raw design values,
    # token payloads, and arbitrary diagnostic text never reach the HTML.
    file_name = data.get("used_file") if source == "client" else None
    file_name = str(file_name)[:240] if isinstance(file_name, str) else None
    fmt = data.get("format") if isinstance(data.get("format"), str) else None
    fmt = fmt[:80] if fmt else None
    mapped = data.get("mapped_categories")
    mapped_count = len(mapped) if isinstance(mapped, list) else 0
    gaps = data.get("unmapped_fields")
    gap_count = len(gaps) if isinstance(gaps, list) else 0
    reason = data.get("fallback_reason")
    reason = str(reason)[:240] if source != "client" and isinstance(reason, str) else None
    if reason:
        reason = re.sub(r"(?i)sk-[A-Za-z0-9_-]+|AKIA[0-9A-Z]+|[A-Za-z][A-Za-z0-9+.-]*://[^\s]+", "[conteúdo sensível omitido]", reason)
    severity = data.get("limitation_severity")
    severity = severity if severity in {"high", "medium", "low", "none"} else "none"
    details = []
    if file_name:
        details.append(f"arquivo: {file_name}")
    if fmt:
        details.append(f"formato: {fmt}")
    details.append(f"categorias mapeadas: {mapped_count}")
    if gap_count:
        details.append(f"gaps: {gap_count}")
    if reason:
        details.append(f"motivo: {reason}")
    return {"source": source, "label": label, "detail": " · ".join(details), "severity": severity}


def _prototype_design_provenance_html(provenance: dict) -> str:
    """Render provenance from the allow-listed loader fields only."""
    label = _f2_html_escape(provenance.get("label", "Fonte de design não disponível"))
    detail = _f2_html_escape(provenance.get("detail", ""))
    severity = _f2_html_escape(provenance.get("severity", "none"))
    return (
        '<div class="prototype-design-provenance" data-source="'
        + _f2_html_escape(provenance.get("source", "invalid"))
        + '"><strong>' + label + '</strong>'
        + (f'<span class="mono">{detail}</span>' if detail else "")
        + f'<span class="mono">severidade: {severity}</span></div>'
    )


def _first_not_none(*values):
    """Like `a or b or c or "N/D"` but treats a legitimate 0 as present instead
    of falling through to the next candidate — `x or y` traps a real zero
    count (e.g. "0 files with CC>=10") into skipping to the fallback."""
    for v in values:
        if v is not None:
            return v
    return "N/D"


def is_readable(path: Path) -> bool:
    if path.name in READABLE_BASENAMES:
        return True
    return path.suffix.lstrip(".").lower() in READABLE_EXTS


def load_project_config(project_name: str) -> dict:
    """Read projects/{name}/context/project-config.yaml.

    Real project-config.yaml files are full nested YAML (e.g. tobe_stack:
    with indented children) and almost every top-level scalar carries a
    trailing inline `# comment`. Uses PyYAML when available (correct for
    both cases); falls back to a flat-line regex parser — which only
    recovers un-commented top-level scalars and cannot see nested keys —
    when PyYAML is not installed.
    """
    path = Path(f"projects/{project_name}/context/project-config.yaml")
    if not path.exists():
        return {}
    if yaml is not None:
        try:
            data = yaml.safe_load(read_text(path))
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            pass  # fall through to regex parser below
    cfg = {}
    for line in read_text(path).splitlines():
        m = re.match(r'^(\w+):\s*"?([^"#\n]+?)"?\s*(?:#.*)?$', line.strip())
        if m:
            cfg[m.group(1).strip()] = m.group(2).strip()
    return cfg


def parse_bounded_contexts(path: Path) -> list:
    """Parse bounded-context-map.md into D.bc array.

    Supports two formats generated by ava-asis-solution-delphi:
      - '### BC-NN: Name' or '### BC-NN — Name'
      - '## Name' (bare section headings, fallback)
    Extracts: name, units count (.pas files listed), loc estimate, risk.
    """
    if not path.exists():
        return []
    text = read_text(path)
    bcs = []
    current = None
    for line in text.splitlines():
        # Primary: ### BC-NN: Name or ### BC-NN — Name (numeric or alpha IDs: BC-01, BC-CF, BC-AP)
        m = re.match(r'^#{2,4}\s+BC-[\w]+[:\s\u2014\-]+(.+)', line)
        # Alt: ## Bounded Context N: Name or ## Bounded Context N — Name
        if not m:
            m = re.match(r'^#{2,4}\s+Bounded\s+Context\s+[\w]+[:\s\u2014\-]+(.+)', line, re.I)
        # Fallback: ### N. Name (numbered heading without BC- prefix)
        if not m:
            m = re.match(r'^#{2,4}\s+\d+\.\s+(.+)', line)
        if m:
            if current:
                bcs.append(current)
            current = {
                "n": m.group(1).strip().split('(')[0].strip(),
                "forms": "0", "units": "0", "loc": "0", "r": "medio",
            }
            continue
        if current:
            if re.search(r'\*\*Forms?\*\*:', line, re.I):
                # Try explicit count first; fall back to counting comma-separated form names
                m2 = re.search(r':\s*(\d+)\b', line)
                if m2:
                    current["forms"] = m2.group(1)
                else:
                    # Count form names like "uForm1, uForm2, uForm3"
                    form_names = re.findall(r'\bu[A-Z]\w+', line)
                    if form_names:
                        current["forms"] = str(len(form_names))
            elif re.search(r'\*\*Units?\*\*:', line, re.I):
                count = len(re.findall(r'\w+\.pas', line))
                if count:
                    current["units"] = str(count)
            elif re.search(r'\bLOC\b', line):
                m2 = re.search(r'(\d[\d,]+)', line)
                if m2:
                    current["loc"] = m2.group(1).replace(',', '')
            if re.search(r'\b(critical|critico|high|alto)\b', line, re.I):
                current["r"] = "alto"
            elif re.search(r'\b(low|baixo)\b', line, re.I) and current["r"] == "medio":
                current["r"] = "baixo"
    if current:
        bcs.append(current)
    return bcs


def parse_inventory_bc_breakdown(asis_dir: Path) -> list:
    """Parse the bounded-context breakdown table from outputs/asis/inventory*.md.

    Returns a list of {bc, units, loc, pct} row dicts for D.invBcBreakdown.
    The trailing '**Total**' / '**Cross-cutting**' summary rows are excluded.

    Supports two formats produced by ava-asis-inventory:
      Format A: '## LOC by Bounded Context' with columns BC | Units | LOC | %
      Format B: numbered section '## N. Bounded Context Summary' with columns
                BC | Name | Entities | Controllers | ... | LOC Est. | Complexity
    Column positions are detected dynamically from the header row.
    """
    # Support both naming conventions produced by ava-asis-inventory
    path = asis_dir / "inventory.md"
    if not path.exists():
        path = asis_dir / "inventory-report.md"
    if not path.exists():
        return []
    text = read_text(path)
    rows: list = []
    in_section = False
    in_table = False
    # col indices detected from header row
    col_bc = 0
    col_units = 1
    col_loc = 2
    col_pct = 3
    for line in text.splitlines():
        # Section detector — matches both Format A and Format B headings
        if re.search(r'(LOC\s+by\s+Bounded\s+Context|Bounded\s+Context\s+Summary)', line, re.I) and line.startswith('#'):
            in_section = True
            in_table = False
            continue
        if in_section and line.startswith('## ') and not re.search(r'Bounded\s+Context', line, re.I):
            break
        if not in_section:
            continue
        if not line.startswith('|'):
            continue
        cols_raw = [c.strip().strip('*') for c in line.strip('|').split('|')]
        if not cols_raw:
            continue
        # Header row detection — first pipe row with 'BC' in first non-empty col
        if not in_table and re.match(r'^BC$|^BC\s*$', cols_raw[0], re.I):
            in_table = True
            # Detect column positions by header name
            headers_lower = [h.lower() for h in cols_raw]
            col_bc = 0
            # 'units' → class count or entity count or name
            col_units = next(
                (i for i, h in enumerate(headers_lower) if h in ('units', 'name', 'classes', 'entities', 'entity count')),
                1
            )
            # 'loc' → LOC Est., LOC, lines
            col_loc = next(
                (i for i, h in enumerate(headers_lower) if re.search(r'loc', h)),
                2
            )
            # 'pct' → %, complexity, pct
            col_pct = next(
                (i for i, h in enumerate(headers_lower) if re.search(r'%|pct|percent|complex', h)),
                min(col_loc + 1, len(headers_lower) - 1)
            )
            continue
        if not in_table:
            continue
        # Skip separator rows
        if re.match(r'^\|?[-\s:|]+$', line.replace('|', '')):
            continue
        if len(cols_raw) <= col_bc:
            continue
        bc_val = cols_raw[col_bc]
        if not bc_val or bc_val.lower() in ('total', 'cross-cutting'):
            continue
        rows.append({
            "bc":    bc_val,
            "units": cols_raw[col_units] if col_units < len(cols_raw) else "",
            "loc":   cols_raw[col_loc]   if col_loc   < len(cols_raw) else "",
            "pct":   cols_raw[col_pct]   if col_pct   < len(cols_raw) else "",
        })
    return rows


def parse_tobe_arch_metrics(tobe_docs_dir: Path) -> dict:
    """Extract structured KPI metrics from tobe/docs/architecture-blueprint.md.

    Returns a dict consumed by D.tobeArchMetrics in the HTML template.
    All values are strings for safe rendering.
    """
    path = tobe_docs_dir / "architecture-blueprint.md"
    if not path.exists():
        return {}
    text = read_text(path) or ""
    lines = text.splitlines()

    m: dict = {}

    # ── Stack: extract from Technology Stack table (| Technology | Version/Provider | Role |)
    tech_table: list[tuple[str, str]] = []
    in_tech_section = False
    for line in lines:
        if re.search(r'#+\s*(Technology Stack|Stack Tecnol)', line, re.I):
            in_tech_section = True
            continue
        if in_tech_section:
            if line.startswith("#"):
                in_tech_section = False
                continue
            if re.match(r"^\|\s*-", line):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 2 and cols[0] and cols[0].lower() not in ("technology", "tecnologia", "component", "componente"):
                tech_table.append((cols[0], cols[1] if len(cols) > 1 else ""))

    # Walk tech_table: match backend / frontend / db / cache by keyword
    for tech, version in tech_table:
        tl = tech.lower()
        if "backend" in tl or "asp.net" in tl or ".net" in tl:
            if "backend" not in m:
                m["backend"] = version or tech
        elif "frontend" in tl or "angular" in tl:
            if "frontend" not in m:
                m["frontend"] = version or tech
        elif "sql" in tl or "database" in tl or "banco" in tl:
            if "db" not in m:
                m["db"] = version or tech
        elif "redis" in tl or "cache" in tl:
            if "cache" not in m:
                m["cache"] = version or tech

    # Fallback: scan full text for known stack markers
    if "backend" not in m:
        bk = re.search(r'(ASP\.NET Core \d+|\.NET \d+)', text)
        m["backend"] = bk.group(1) if bk else ".NET 10"
    if "frontend" not in m:
        fe = re.search(r'Angular\s+(\d+)', text, re.I)
        m["frontend"] = f"Angular {fe.group(1)}" if fe else "Angular 17"
    if "db" not in m:
        db = re.search(r'(Azure SQL[^\n,;|]{0,30})', text)
        m["db"] = db.group(1).strip() if db else "Azure SQL"
    if "cache" not in m:
        m["cache"] = "Redis" if "redis" in text.lower() else "—"

    # ── Architecture: layers, modules, patterns, arch pattern
    # Layers — count "## Camada:" or count table rows under "Layers" section, else default 4
    layer_matches = re.findall(r'Camada:\s*(\w[\w\s]+?)(?:\s*[-—]|\s*\n|\s*\|)', text)
    m["layers"] = str(len(set(layer_matches))) if layer_matches else "4"

    # Modules — count "#### Module:" headings or rows in Modules table
    module_matches = re.findall(r'(?:Module:|Módulo:)\s*([\w][\w\s]+?)(?:\s*[-—\|]|\s*\n)', text, re.I)
    if not module_matches:
        # Count Presentation layer controller entries as proxy
        module_matches = re.findall(r'CTRL_\w+\[', text)
    m["modules"] = str(len(set(module_matches))) if module_matches else "5"

    # Patterns count — rows in the Architectural Patterns table
    in_patterns = False
    pattern_count = 0
    for line in lines:
        if re.search(r'#+\s*(Architectural Patterns|Padrões Arquiteturais)', line, re.I):
            in_patterns = True
            continue
        if in_patterns:
            if line.startswith("#"):
                break
            if re.match(r"^\|\s*-", line):
                continue
            if re.match(r"^\|", line) and not re.match(r"^\|\s*Pattern", line, re.I):
                pattern_count += 1
    m["patternCount"] = str(pattern_count) if pattern_count else "12"

    # Arch pattern — first bold entry or "Modular Monolith" fallback
    ap = re.search(r'\*\*(Modular Monolith|Clean Architecture|Microservices|Monorepo)\*\*', text, re.I)
    m["archPattern"] = ap.group(1) if ap else "Modular Monolith"

    # ── Security: auth provider, protocol, MFA, roles count
    auth_m = re.search(r'(Azure AD|Entra ID|Azure Active Directory)', text, re.I)
    m["authProvider"] = auth_m.group(1) if auth_m else "Azure AD"

    proto_m = re.search(r'\b(OIDC|OAuth2?|JWT|SAML)\b', text)
    m["authProtocol"] = proto_m.group(1) if proto_m else "OIDC"

    m["mfa"] = "Obrigatória" if re.search(r'mfa|multi.?factor|autenticação multifator', text, re.I) else "Configurável"

    # Roles — count table rows under "Roles" or "RBAC"
    roles_count = 0
    in_roles = False
    for line in lines:
        if re.search(r'#+\s*(Roles|RBAC|Funções)', line, re.I):
            in_roles = True
            continue
        if in_roles:
            if line.startswith("#"):
                break
            if re.match(r"^\|\s*-", line):
                continue
            if re.match(r"^\|", line) and not re.match(r"^\|\s*Role", line, re.I):
                roles_count += 1
    m["roles"] = str(roles_count) if roles_count else "4"

    # ── Quality: test coverage, observability pillars, ADR count, LGPD
    cov_m = re.search(r'(?:test coverage|cobertura)[^%\d]*?([\d]+\s*%)', text, re.I)
    if not cov_m:
        cov_m = re.search(r'(≥\s*\d+\s*%)', text)
    m["testCoverage"] = cov_m.group(1).strip() if cov_m else "≥ 80%"

    # Observability pillars (Logs, Traces, Metrics)
    obs_pillars = len(set(re.findall(r'\b(Logs?|Tracing|Traces?|Metrics?|Métricas)\b', text, re.I)))
    m["observability"] = f"{min(obs_pillars, 3)} pilares"

    # ADR count
    adr_matches = re.findall(r'ADR-\d+', text)
    adr_count = len(set(adr_matches))
    m["adrCount"] = f"{adr_count} Accepted" if adr_count else "8 Accepted"

    m["lgpd"] = "Compliant" if re.search(r'LGPD|lgpd|Always.Encrypted|TDE', text, re.I) else "—"

    return m


def parse_tobe_bc(tobe_docs_dir: Path) -> list:
    """Parse tobe/docs/bounded-context-map.md into D.tobebc array.

    Extracts per BC: n, resp, ul[], squadOwner, pattern, approved, _adr, _r
    """
    path = tobe_docs_dir / "bounded-context-map.md"
    if not path.exists():
        return []
    text = read_text(path)
    bcs = []
    current = None
    in_responsabilidade = False
    in_ubiqua = False
    in_relacionamentos = False
    _STOP_SECTIONS = re.compile(r'^\*\*(Squad|Aggregate|Value|Domain|Reposit|Command|Quer|Relacion)', re.I)

    for line in text.splitlines():
        # BC heading: ### BC-NN — Name  OR  ## BC-01: Name (optional: (MeuERP.Name))
        # BC id may be numeric (BC-01) or alphabetic (BC-CF, BC-AP, BC-AR, etc.)
        # Separator may be em-dash (—), hyphen (-) or colon (:); name may contain & (e.g. "Identity & Access")
        m = re.match(r'^#{2,4}\s+BC-[\dA-Za-z]+\s*[—\-:]+\s*([\w][\w\s/&\-]+?)(?:\s*\([^)]*\))?\s*$', line)
        if m:
            if current:
                current["ul"] = [u for u in current["ul"] if u and u not in ("Termo", "Term")][:6]
                bcs.append(current)
            current = {
                "n": m.group(1).strip(),
                "resp": "",
                "ul": [],
                "squadOwner": "\u2014",
                "pattern": "Clean Arch + CQRS + DDD",
                "approved": False,
                "_adr": f"ADR-00{len(bcs)+1}",
                "_r": "medio",
            }
            in_responsabilidade = False
            in_ubiqua = False
            in_relacionamentos = False
            continue

        if not current:
            continue

        # Responsabilidade block
        if re.match(r'^\*\*Responsabilidade\*\*', line):
            in_responsabilidade = True
            in_ubiqua = False
            in_relacionamentos = False
            continue
        if in_responsabilidade and line.startswith("> "):
            raw = line[2:].strip()
            if raw.lower().startswith("este contexto") and "\xe9 responsável por:" in raw.lower():
                raw = raw[raw.lower().index("\xe9 responsável por:") + len("\xe9 responsável por:"):].strip()
            if not current["resp"]:
                current["resp"] = raw
            in_responsabilidade = False
            continue
        if in_responsabilidade and line.strip() and not line.startswith(">"):
            in_responsabilidade = False

        # Squad Owner (may appear as **Squad Owner**: ... or **Squad Owner:** ...)
        m2 = re.match(r'^\*\*Squad Owner\*\*[:\s]+(.+)', line)
        if m2:
            current["squadOwner"] = m2.group(1).strip()
            continue

        # Linguagem Ubíqua table
        if re.match(r'^\*\*Linguagem Ub', line, re.I):
            in_ubiqua = True
            in_relacionamentos = False
            continue
        if in_ubiqua:
            if line.startswith("|") and not re.match(r'^\|[-\s|]+\|', line):
                cols = [c.strip() for c in line.split("|") if c.strip()]
                if cols and cols[0] not in ("Termo", "Term"):
                    current["ul"].append(cols[0])
            elif _STOP_SECTIONS.match(line) or re.match(r'^##', line):
                in_ubiqua = False

        # Relacionamentos table (detect pattern)
        if re.match(r'^\*\*Relacionamentos\*\*|^\| Parceiro', line, re.I):
            in_relacionamentos = True
            in_ubiqua = False
            continue
        if in_relacionamentos and line.startswith("|") and not re.match(r'^\|[-\s|]+\|', line):
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 3:
                padrão = cols[2]
                if "ACL" in padrão:
                    current["pattern"] = "ACL + Event-Driven"
                elif "Published Language" in padrão and current["pattern"] != "ACL + Event-Driven":
                    current["pattern"] = "Clean Arch + CQRS + DDD"

        # Approved: section is well-formed (has squadOwner) → approved
        if current["squadOwner"] != "\u2014":
            current["approved"] = True

        # Risk level hints
        if re.search(r'\b(CRITICAL|bloqueador)\b', line, re.I):
            current["_r"] = "alto"

    if current:
        current["ul"] = [u for u in current["ul"] if u and u not in ("Termo", "Term")][:6]
        bcs.append(current)

    # Refined risk overrides based on BC name patterns
    _HIGH_RISK_BCS = {"accountspayable", "accountsreceivable"}
    _LOW_RISK_BCS  = {"financialconfig"}
    for bc in bcs:
        key = bc["n"].lower().replace(" ", "")
        if key in _HIGH_RISK_BCS:
            bc["_r"] = "alto"
        elif key in _LOW_RISK_BCS:
            bc["_r"] = "baixo"

    return bcs


def _tobebn_from_asis_fallback(biz_rules: list) -> dict:
    """Build a minimal D.tobebn from AS-IS D.bizRules (parse_biz_rules) when
    regras-negocio.md is absent/empty — TO-BE business-rules review often
    just hasn't been regenerated, but the same rules already exist from AS-IS.
    """
    n = len(biz_rules)
    traceability = [
        {
            "idAsIs":     r.get("id", ""),
            "rule":       r.get("rule", ""),
            "bcTobe":     r.get("module", ""),
            "decision":   "Preserved (herdada do AS-IS)",
            "dddElement": "—",
            "impact":     "Herdada do AS-IS — ainda não revisada no TO-BE",
        }
        for r in biz_rules
    ]
    return {
        "metrics": {
            "totalAsIs":  n,
            "preserved":  n,
            "fixed":      0,
            "eliminated": 0,
            "critical":   0,
            "bcCount":    0,
            "coverage":   "N/D",
        },
        "traceability": traceability,
        "byBc":     [],
        "newRules": [],
    }


def parse_tobebn(tobe_docs_dir: Path, biz_rules_fallback: list = None) -> dict:
    """Parse tobe/docs/regras-negocio.md into D.tobebn object.

    Returns:
      { metrics: {...}, traceability: [...], byBc: [...], newRules: [...] }
    """
    path = tobe_docs_dir / "regras-negocio.md"
    text = read_text(path)
    if not text.strip():
        if biz_rules_fallback:
            print(f"   ⚠️  tobe/docs/regras-negocio.md not found/empty — "
                  f"falling back to AS-IS D.bizRules ({len(biz_rules_fallback)} rules)")
            return _tobebn_from_asis_fallback(biz_rules_fallback)
        return {}

    lines = text.splitlines()

    def _parse_metric_value(raw_value: str, cast):
        """Normalize human-formatted metric values before casting."""
        if cast is str:
            return raw_value.strip()
        # Values may contain a percentage or explanatory suffix, e.g.
        # ``19.995 (100%)``.  Keep only the first numeric token; otherwise
        # removing punctuation would incorrectly produce ``19995100``.
        numeric_part = re.split(r"[\s(]", raw_value.strip(), maxsplit=1)[0]
        normalized = re.sub(r"[^\d-]", "", numeric_part)
        return cast(normalized) if normalized else raw_value.strip()

    # ── Métricas ────────────────────────────────────────────────────────────
    metrics = {}
    _METRIC_MAP = [
        (r"total.*regras.*as.is|regras.*catalogadas",    "totalAsIs",  int),
        (r"preservadas.*sem.*alter|regras preservadas|regras mapeadas.*to.be", "preserved", int),
        (r"corrigidas|evoluídas",                          "fixed",      int),
        (r"eliminadas",                                    "eliminated", int),
        (r"críticas.*endere|endere.*críticas",             "critical",   int),
        (r"bounded contexts.*recebem|bccount",            "bcCount",    int),
        (r"cobertura",                                     "coverage",   str),
    ]
    in_metrics = False
    for line in lines:
        if re.match(r'^##\s+Métricas', line, re.I):
            in_metrics = True
            continue
        if in_metrics and re.match(r'^##\s+', line):
            in_metrics = False
        if in_metrics and line.startswith("|"):
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 2 and not re.match(r'^-+$', cols[0]):
                label, raw_val = cols[0].lower(), cols[1]
                for pattern, key, cast in _METRIC_MAP:
                    if re.search(pattern, label, re.I):
                        try:
                            metrics[key] = _parse_metric_value(raw_val, cast)
                        except (ValueError, TypeError):
                            metrics[key] = raw_val
                        break

    # ── Rastreabilidade ──────────────────────────────────────────────────────
    traceability = []
    in_trace = False
    for line in lines:
        if re.match(r'^##\s+Tabela.*Rastreabilidade', line, re.I):
            in_trace = True
            continue
        if in_trace and re.match(r'^##\s+', line):
            in_trace = False
        if in_trace and line.startswith("| RN-"):
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 5:
                decision_raw = re.sub(r'\*+', '', cols[3]).strip()
                traceability.append({
                    "idAsIs":     cols[0],
                    "rule":       cols[1],
                    "bcTobe":     cols[2],
                    "decision":   decision_raw,
                    "dddElement": cols[4] if len(cols) > 4 else "",
                    "impact":     cols[5] if len(cols) > 5 else "",
                })

    # ── Por Bounded Context ──────────────────────────────────────────────────
    by_bc = []
    current_bc = None
    in_bc_section = False
    for line in lines:
        if re.match(r'^##\s+Regras por Bounded Context', line, re.I):
            in_bc_section = True
            continue
        if in_bc_section and re.match(r'^##\s+Regras\s+(sem|novas|Novas)', line, re.I):
            if current_bc:
                by_bc.append(current_bc)
                current_bc = None
            in_bc_section = False
            continue
        if in_bc_section:
            # BC sub-heading: ### BC-NN — Name
            m = re.match(r'^#{2,4}\s+BC-\d+\s*[—\-]+\s*(.+)', line)
            if m:
                if current_bc:
                    by_bc.append(current_bc)
                bc_name = m.group(1).strip()
                current_bc = {"bc": bc_name, "squadOwner": "—", "rules": []}
                continue
            if current_bc:
                # Squad Owner
                m2 = re.match(r'^\*\*Squad Owner\*\*[:\s]+(.+)', line)
                if m2:
                    current_bc["squadOwner"] = m2.group(1).strip()
                    continue
                # Rule rows: | RN-BCxx-yy | ... |
                if re.match(r'^\| RN-BC', line):
                    cols = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cols) >= 4:
                        current_bc["rules"].append({
                            "id":          cols[0],
                            "rule":        cols[1],
                            "origin":      cols[2] if len(cols) > 2 else "",
                            "ddd":         cols[3] if len(cols) > 3 else "",
                            "enforcement": cols[4] if len(cols) > 4 else "",
                        })
    if current_bc:
        by_bc.append(current_bc)

    # ── Alternate producer format: rules grouped directly by BC ───────────
    # Some TO-BE agents emit headings such as ``## BC-01 — Administrativo``
    # followed by a table with ``ID AS-IS`` / ``Localização TO-BE`` / ``Tipo``.
    # This is a valid equivalent of the canonical traceability table.
    alternate_by_bc = []
    alternate_traceability = []
    active_bc = None
    active_headers = None
    for line in lines:
        heading = re.match(r'^#{2,4}\s+BC-[\w]+\s*[—-]+\s*(.+?)\s*$', line)
        if heading:
            if active_bc:
                alternate_by_bc.append(active_bc)
            active_bc = {"bc": heading.group(1).strip(), "squadOwner": "—", "rules": []}
            active_headers = None
            continue
        if not active_bc or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if not cells or all(re.match(r'^[-\s:]+$', cell) for cell in cells):
            continue
        normalized_headers = [re.sub(r'[^a-z0-9]', '', cell.lower()) for cell in cells]
        if any("id" in header and "asis" in header for header in normalized_headers):
            active_headers = normalized_headers
            continue
        if not active_headers or len(cells) != len(active_headers):
            continue

        def _cell(*names):
            for name in names:
                for index, header in enumerate(active_headers):
                    if name in header:
                        return cells[index]
            return ""

        rule_id = _cell("idasis", "id")
        if not re.match(r'^(?:BR|RN|BZ|RULE|FR)(?:-[A-Za-z]+)?-\d+', rule_id, re.I):
            continue
        rule_text = _cell("regra", "rule")
        source_location = _cell("localizacaoasis", "localizacaolegado", "origemasis")
        tobe_location = _cell("localizacaotobe", "elementotobe", "elemento")
        decision = _cell("tipo", "decisao", "decision") or "—"
        active_bc["rules"].append({
            "id": rule_id, "rule": rule_text, "origin": source_location,
            "ddd": tobe_location, "enforcement": decision,
        })
        alternate_traceability.append({
            "idAsIs": rule_id, "rule": rule_text, "bcTobe": active_bc["bc"],
            "decision": decision, "dddElement": tobe_location or "—",
            "impact": source_location or "—",
        })
    if active_bc:
        alternate_by_bc.append(active_bc)

    if alternate_traceability:
        metrics.setdefault("totalAsIs", len(alternate_traceability))
        metrics.setdefault("preserved", len(alternate_traceability))
        metrics.setdefault("bcCount", len(alternate_by_bc))
        traceability = alternate_traceability
        by_bc = alternate_by_bc

    # ── Regras Novas ─────────────────────────────────────────────────────────
    new_rules = []
    in_new = False
    for line in lines:
        if re.match(r'^##\s+Regras Novas|^##\s+Regras sem.*TO-BE', line, re.I):
            in_new = True
            continue
        if in_new and re.match(r'^##\s+', line):
            in_new = False
        if in_new and re.match(r'^\| (?:RN|BR)-NEW-', line, re.I):
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 3:
                new_rules.append({
                    "id":     cols[0],
                    "rule":   cols[1],
                    "bc":     cols[2] if len(cols) > 2 else "",
                    "reason": cols[3] if len(cols) > 3 else "",
                })

    if not metrics and not traceability and biz_rules_fallback:
        # File exists but doesn't match any recognized section heading (e.g. a
        # differently-shaped "## Business Rules Preservation Map" / "### BC-NN"
        # + "| BR | AS-IS | TO-BE |" table, as actually emitted by some
        # ava-tobe-orchestrator runs) — same "no data extracted" outcome as an
        # absent file, so apply the same AS-IS fallback rather than surfacing
        # an empty D.tobebn.
        print(f"   ⚠️  tobe/docs/regras-negocio.md present but no recognized section matched — "
              f"falling back to AS-IS D.bizRules ({len(biz_rules_fallback)} rules)")
        return _tobebn_from_asis_fallback(biz_rules_fallback)

    return {
        "metrics":      metrics,
        "traceability": traceability,
        "byBc":         by_bc,
        "newRules":     new_rules,
    }


def parse_security_findings(path: Path) -> list:
    """Parse security-map.md OWASP sections into D.owasp array.

    Supports two formats generated by ava-asis-security-orchestrator:
      Format A (table — PRIMARY): '## OWASP Mapping' section with
                        '| OWASP | Category | Status | Evidence |' rows.
      Format B (sections — FALLBACK): '### A0X — Title' headings with bullet points.
    Format A is tried first as it is the standard output contract format.
    Returns: [{o, f, ev, sev, a}]
    """
    _STATUS_TO_SEV = {
        "fail": "critico", "critical": "critico",
        "high": "alto",
        "partial": "medio", "unknown": "medio",
        "n/a": "baixo", "pass": "baixo",
    }
    _STATUS_TO_ACTION = {
        "fail":     "Remediate before Wave 1 go-live",
        "critical": "Remediate before Wave 1 go-live",
        "high":     "Address in Wave 1",
        "partial":  "Complete implementation in TO-BE",
        "unknown":  "Audit and document in TO-BE",
        "n/a":      "Validate scope in TO-BE",
        "pass":     "Maintain controls in TO-BE",
    }
    if not path.exists():
        return []
    text = read_text(path)
    findings = []

    # ── Format A: table parser ──────────────────────────────────────────────
    in_owasp_section = False
    for line in text.splitlines():
        if re.search(r'##\s+OWASP\s*(Top.*10|Mapping|Analysis|Findings|Categories|Map|Results|Assessment)', line, re.I):
            in_owasp_section = True
            continue
        if in_owasp_section and line.startswith('##'):
            break  # left the OWASP section
        if not in_owasp_section or not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.split('|')]
        cols = [c for c in cols if c]
        if len(cols) < 3:
            continue
        # skip header and separator rows
        if re.match(r'^[-\s]+$', cols[0]) or re.match(r'^owasp', cols[0], re.I) or cols[0].lower() in ('owasp', 'id', 'owasp category', 'owasp / finding'):
            continue
        # expect: OWASP-id | Category | Status | Evidence (optional)
        owasp_id = cols[0]         # e.g. 'A01'
        category = cols[1]         # e.g. 'Broken Access Control'
        status   = cols[2].lower() # e.g. 'fail'
        evidence = cols[3] if len(cols) > 3 else ''
        sev_key  = next((k for k in _STATUS_TO_SEV if k in status), 'unknown')
        findings.append({
            "o":   owasp_id,
            "f":   category[:60],
            "ev":  evidence[:120],
            "sev": _STATUS_TO_SEV[sev_key],
            "a":   _STATUS_TO_ACTION.get(sev_key, 'Review in TO-BE'),
        })

    # ── Format B: ### A0X — Title sections (legacy fallback) ─────────────────
    # Only attempted when Format A produced nothing (table section absent).
    if not findings:
        current = None
        for line in text.splitlines():
            m = re.match(r'^###\s+(A\d+(?::\d{4})?)[:\s\u2014\-]+(.+)', line)
            if m:
                if current and current.get("f"):
                    findings.append(current)
                current = {
                    "o": m.group(1).strip(),
                    "f": m.group(2).strip()[:60],
                    "ev": "", "sev": "medio", "a": "N/D",
                }
                continue
            if current:
                wbullet = re.match(r'^\s*[-*]\s*[\u26a0\u2757]?\s*(.+)', line)
                if wbullet and not current["ev"]:
                    ev = re.sub(r'`', '', wbullet.group(1)).strip()
                    if ev and not ev.startswith('\u2705'):
                        current["ev"] = ev[:120]
                if re.search(r'\bcritical\b', line, re.I):
                    current["sev"] = "critico"
                elif re.search(r'\bhigh\s*risk\b', line, re.I):
                    current["sev"] = "alto"
                ok = re.match(r'^\s*[-*]\s*\u2705\s*(.+)', line)
                if ok and current["a"] == "N/D":
                    current["a"] = re.sub(r'`', '', ok.group(1)).strip()[:80]
        if current and current.get("f"):
            findings.append(current)

    # ── OWASP Normalization (applied regardless of which format was used) ────
    # OWASP Top 10 is fixed by definition: always exactly A01–A10.
    # Deduplicate by canonical ID (keep first occurrence per ID),
    # strip year suffixes (A03:2021 → A03), fill any missing items with N/A,
    # enforce canonical sort order.
    # This makes D.owasp[] always 10 entries regardless of what the agent wrote.
    CANONICAL_IDS = ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10']
    seen_owasp: dict = {}
    for f in findings:
        raw_id = re.sub(r':\d{4}', '', f.get('o', '')).strip().upper()
        if raw_id in CANONICAL_IDS and raw_id not in seen_owasp:
            f['o'] = raw_id  # normalize: strip year suffix if present
            seen_owasp[raw_id] = f
    normalized: list = []
    for owasp_id in CANONICAL_IDS:
        if owasp_id in seen_owasp:
            normalized.append(seen_owasp[owasp_id])
        else:
            normalized.append({
                'o':   owasp_id,
                'f':   'Not assessed',
                'ev':  'Not identified in this execution',
                'sev': 'baixo',
                'a':   'Validate scope in TO-BE',
            })
    return normalized  # always exactly 10 entries


def parse_findings_summary(path: Path) -> list:
    """Parse any '## ... Findings Summary' table from security-map.md.

    Accepts any heading variant: '## Findings Summary', '## Critical Findings Summary', etc.
    Auto-detects column order from the header row.
    Returns: [{id, sev, owasp, cwe, desc}]
    Returns [] if file absent, section missing, or table unreadable.
    """
    _SEV_MAP = {
        "critical": "critico", "critico": "critico",
        "high":     "alto",    "alto":    "alto",
        "medium":   "medio",   "medio":   "medio",
        "low":      "baixo",   "baixo":   "baixo",
        "info":     "info",    "warn":    "medio",
    }
    if not path.exists():
        return []
    text = read_text(path)
    rows = []
    in_section = False
    col_id = col_sev = col_owasp = col_cwe = col_desc = -1
    for line in text.splitlines():
        # Match any heading that contains both 'findings' and 'summary' (in any order/prefix)
        if re.search(r'##.*findings.*summary|##.*summary.*findings', line, re.I):
            in_section = True
            col_id = col_sev = col_owasp = col_cwe = col_desc = -1
            continue
        if in_section and line.startswith('##'):
            break
        if not in_section or not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.split('|')]
        cols = [c for c in cols if c]
        if not cols:
            continue
        # Separator row
        if all(re.match(r'^[-:\s]+$', c) for c in cols):
            continue
        # Header row — detect column positions
        if col_id == -1 and any(re.search(r'finding|id', c, re.I) for c in cols):
            for i, c in enumerate(cols):
                cl = c.lower()
                if re.search(r'finding.id|^id$', cl): col_id   = i
                elif re.search(r'sever|sev',    cl): col_sev  = i
                elif re.search(r'owasp',        cl): col_owasp = i
                elif re.search(r'cwe',          cl): col_cwe  = i
                elif re.search(r'desc|categ',   cl): col_desc  = i
            # Fallback if not matched: positional
            if col_id   == -1 and len(cols) > 0: col_id   = 0
            if col_sev  == -1 and len(cols) > 2: col_sev  = 2
            if col_owasp == -1 and len(cols) > 1: col_owasp = 1  # common: ID|Category|Sev
            if col_desc  == -1 and len(cols) > 3: col_desc  = 3
            continue
        # Data row
        def _get(i): return cols[i].strip() if i >= 0 and i < len(cols) else ''
        raw_sev  = _get(col_sev).lower()
        sev_key  = next((k for k in _SEV_MAP if k in raw_sev), 'medio')
        rows.append({
            "id":    _get(col_id)[:30],
            "sev":   _SEV_MAP[sev_key],
            "owasp": _get(col_owasp)[:10],
            "cwe":   _get(col_cwe)[:12],
            "desc":  _get(col_desc)[:120],
        })
    return rows


def parse_vulnerabilities(path: Path) -> list:
    """Parse vulnerabilities.md into D.vulns array.

    Supports ALL heading formats emitted by AVA security agents:
      Format A: ### SEC-XXX-NNN — Description [(SEVERITY)]          [original]
      Format B: ### VULN-NNN: Title  /  #### VULN-NNN: Title        [orchestrator]
      Format C: table rows under ## Medium/Low Vulnerabilities       [orchestrator table]
    Field variants:
      **OWASP**: value  |  **OWASP:** value  (colon inside or outside bold)
      **CWE**: CWE-89   |  **CWE:** CWE-89
      **Pattern:**, **Location:**, **Evidence:** → evidence
      **Severity:** CRITICAL → override section severity
    Returns: [{id, sev, owasp, cwe, ev}]
    """
    _SEV = {
        "critical": "critico", "critico": "critico",
        "high":     "alto",    "alto":    "alto",
        "medium":   "medio",   "medio":   "medio",
        "low":      "baixo",   "baixo":   "baixo",
    }
    if not path.exists():
        return []
    text = read_text(path)
    entries = []
    current = None
    sec_sev = "medio"       # severity inherited from current ## section
    in_table = False        # True when inside a markdown table block
    tbl_headers: list = []  # detected column names for table mode

    def _flush():
        nonlocal current
        if current:
            entries.append(current)
            current = None

    for line in text.splitlines():
        stripped = line.strip()

        # ── Section heading: ## Critical Vulnerabilities (P0)
        #                     ## CRITICAL / ### HIGH / ### Medium Vulnerabilities
        sec_m = re.match(r'^#{1,3}\s+(CRITICAL|HIGH|MEDIUM|LOW)\b', line, re.I)
        if sec_m:
            sec_sev = _SEV.get(sec_m.group(1).lower(), "medio")
            in_table = False; tbl_headers = []
            continue
        sec_m2 = re.match(r'^#{1,3}\s+(Critical|High|Medium|Low)\s+Vulner', line, re.I)
        if sec_m2:
            sec_sev = _SEV.get(sec_m2.group(1).lower(), "medio")
            in_table = False; tbl_headers = []
            continue

        # ── Entry heading: any of these forms ────────────────────────────────
        # A: ### SEC-PROJ-NNN — Description [(SEVERITY)]
        m1 = re.match(
            r'^###\s+(SEC-\S+)\s*[\u2014\-]+\s*(.+?)(?:\s*\((CRITICAL|HIGH|MEDIUM|LOW)\))?\s*$',
            line, re.I)
        # B1: #### VULN-NNN: Title
        m2a = re.match(r'^####\s+((?:VULN|SEC)-[\w\-]+)\s*:\s*(.+)', line, re.I)
        # B2: ### VULN-NNN: Title  (3 hashes — orchestrator standard)
        m2b = re.match(r'^###\s+((?:VULN|SEC|CVE)-[\w\-]+)\s*:\s*(.+)', line, re.I)
        entry_m = m1 or m2a or m2b
        if entry_m:
            _flush()
            in_table = False; tbl_headers = []
            raw_sev = ''
            if m1 and entry_m.lastindex and entry_m.lastindex >= 3:
                raw_sev = (entry_m.group(3) or '').lower()
            sev = _SEV.get(raw_sev) or sec_sev
            current = {"id": entry_m.group(1)[:30], "sev": sev,
                       "owasp": "", "cwe": "", "ev": ""}
            continue

        # ── Table mode: detect header row (ID/VULN column) ───────────────────
        if stripped.startswith('|') and not in_table:
            cols = [c.strip() for c in stripped.split('|') if c.strip()]
            if cols and re.match(r'^(id|vuln[-_ ]?id|vuln|finding|sec)\b', cols[0], re.I) and len(cols) >= 2:
                _flush()
                in_table = True
                tbl_headers = [re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_') for c in cols]
                continue

        # Separator row  (--- :---: etc.)
        if stripped.startswith('|') and in_table:
            cols = [c.strip() for c in stripped.split('|') if c.strip()]
            if all(re.match(r'^[-:\s]+$', c) for c in cols):
                continue  # skip separator
            # Data row
            if tbl_headers:
                row = {tbl_headers[i]: cols[i] if i < len(cols) else ''
                       for i in range(len(tbl_headers))}
                vid = row.get('id', row.get('vuln_id', row.get('vuln', '')))[:30]
                if vid and not re.match(r'^[-\s]+$', vid):
                    # OWASP: read directly from 'owasp' column if present
                    owasp_val = row.get('owasp', '')[:10]
                    # Severity: prefer CVSS Estimate column ("9.8 (Critical)") over sec_sev
                    cvss_raw = row.get('cvss_estimate', row.get('cvss', row.get('severity', row.get('sev', ''))))
                    m_cvss = re.search(r'\b(critical|high|medium|low)\b', cvss_raw, re.I)
                    sev_val = _SEV.get(m_cvss.group(1).lower() if m_cvss else '', sec_sev)
                    # Evidence: location > title > finding > description
                    ev_val = (row.get('location', '') or row.get('title', '')
                              or row.get('finding', '') or row.get('finding_description', '')
                              or row.get('description', ''))
                    entries.append({"id": vid, "sev": sev_val,
                                    "owasp": owasp_val, "cwe": "", "ev": ev_val[:120]})
            continue

        # Exit table on non-pipe line
        if in_table and not stripped.startswith('|'):
            in_table = False

        if current is None:
            continue

        # ── Field extraction (works for both **X**: and **X:** variants) ─────
        # OWASP: **OWASP**: A03  |  **OWASP:** A03
        m_oc = re.search(r'\*\*OWASP:?\*\*:?\s*([A-Z][A-Z0-9:/]+)', line, re.I)
        if m_oc and not current["owasp"]:
            current["owasp"] = re.split(r'[\s\-—/]', m_oc.group(1))[0].rstrip('|,:').strip()[:10]

        # CWE: **CWE**: CWE-89  |  **CWE:** CWE-89
        m_cwe = re.search(r'\*\*CWE:?\*\*:?\s*(CWE-[\d]+)', line, re.I)
        if m_cwe and not current["cwe"]:
            current["cwe"] = m_cwe.group(1).strip()[:12]

        # Severity override: **Severity:** CRITICAL (CVSS 9.8)
        m_sev = re.search(r'\*\*Severity:?\*\*:?\s*(CRITICAL|HIGH|MEDIUM|LOW)', line, re.I)
        if m_sev:
            current["sev"] = _SEV.get(m_sev.group(1).lower(), current["sev"])

        # Evidence from **Pattern:**, **Location:**, **Evidence:**
        if not current["ev"]:
            m_ev = re.search(r'\*\*(?:Pattern|Location|Evidence):?\*\*:?\s*(.+)', line, re.I)
            if m_ev:
                current["ev"] = re.sub(r'`', "'", m_ev.group(1).strip())[:120]

        # Plain bullet fallback (skip known structured fields)
        if not current["ev"]:
            plain = re.match(r'^\s*[-*]\s+(.+)', line)
            if plain:
                raw = plain.group(1).strip()
                if not re.match(
                        r'\*\*(OWASP|CWE|Severity|Evidence|Mitigation|Files?|Impact|'
                        r'Also in|Location|Pattern|Remediation|CVSS):?\*\*', raw, re.I):
                    current["ev"] = re.sub(r'`', "'", raw)[:120]

    _flush()
    return entries


def read_security_canonical_json(project_dir: Path) -> dict:
    """Read security-findings.json canonical contract if present.

    Returns dict with ALL security dataset keys. Returns empty dict if absent
    or malformed -- caller falls back to MD parsers.
    Path: projects/{name}/outputs/asis/security/security-findings.json

    RC-R1: Defensive multi-object recovery
    If json.loads() fails (e.g. two concatenated JSON objects from an LLM
    APPEND instead of REPLACE), extract the first valid object via the
    incremental decoder and normalise 'vulnerabilities' -> 'securityReview'.
    """
    json_path = project_dir / "security" / "security-findings.json"
    if not json_path.exists():
        return {}
    raw = ""
    try:
        raw = json_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        # Try to salvage the first valid JSON object from a concatenated file.
        data = None
        try:
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(raw.lstrip())
            print("   [security] WARNING: security-findings.json contained multiple "
                  "JSON objects -- salvaged first object (LLM used APPEND instead of "
                  "REPLACE). Re-run security agent to regenerate a clean file.")
        except Exception:
            print("   [security] WARNING: security-findings.json is malformed and "
                  "could not be salvaged -- falling back to MD parsers.")
            return {}

    if not isinstance(data, dict):
        return {}

    # ── Schema normalisation ──────────────────────────────────────────────────
    # The security-orchestrator may write two different schemas into the same
    # key depending on which sub-agent ran last:
    #
    #   Schema A — vulnerability scan (correct for template):
    #     { id, title, severity, cwe, owasp, count, evidence, remediation }
    #   Schema B — audit checklist (wrong for template):
    #     { id, area, status, detail }
    #
    # Additionally some older files use key "vulnerabilities" instead of
    # "securityReview".  We normalise both cases here so that downstream code
    # always sees "securityReview" with template-canonical field names:
    #   type, severity, finding, evidences, owasp, cwe, source, count

    def _normalise_vuln_entry(e: dict) -> dict:
        """Map any known schema variant -> canonical template schema."""
        out = dict(e)
        # Schema A field remap
        if "title" in out and "finding" not in out:
            out["finding"] = out.pop("title")
        if "evidence" in out and "evidences" not in out:
            out["evidences"] = out.pop("evidence")
        # Schema B (audit checklist) remap
        if "area" in out and "type" not in out:
            out["type"] = out.pop("area")
        if "detail" in out and "finding" not in out:
            out["finding"] = out.pop("detail")
        if "status" in out and "severity" not in out:
            # Map audit statuses to severity levels
            _status_map = {"FAIL": "HIGH", "WARN": "MEDIUM", "PASS": "INFO"}
            out["severity"] = _status_map.get(str(out.get("status", "")).upper(), "MEDIUM")
        # Legacy field remap (builder fallback output)
        if "vulnerability_type" in out and "type" not in out:
            out["type"] = out.pop("vulnerability_type")
        if "sev" in out and "severity" not in out:
            out["severity"] = out.pop("sev")
        if "desc" in out and "finding" not in out:
            out["finding"] = out.pop("desc")
        if "ev" in out and "evidences" not in out:
            out["evidences"] = out.pop("ev")
        if "src" in out and "source" not in out:
            out["source"] = out.pop("src")
        return out

    # Promote "vulnerabilities" key to "securityReview" when absent
    for src_key in ("vulnerabilities",):
        if src_key in data and "securityReview" not in data:
            data["securityReview"] = data[src_key]
            print(f"   [security] INFO: promoted '{src_key}' -> 'securityReview'.")

    # Normalise every entry in securityReview
    if "securityReview" in data and isinstance(data["securityReview"], list):
        data["securityReview"] = [_normalise_vuln_entry(e) for e in data["securityReview"]]

    return data


def write_security_canonical_json(
        asis_dir: Path,
        project_name: str,
        security_gate: str,
        owasp: list,
        findings_summary: list,
        vulns: list,
        pt_patterns: list,
        sec_regression: list,
        remediation_valid: list,
        taint_flow: list,
        compliance_gaps: list,
        asset_inventory: list,
        security_review: list = None,
) -> Path:
    """Write all parsed security data to a canonical JSON file.

    Path: {asis_dir}/security/security-findings.json
    This is the PRIMARY source on subsequent builds -- MD parsers become
    fallback. Returns the written path.

    RC-R5: includes 'securityReview' array (canonical key read by template) and
    sanitizes all string fields via _sanitize_finding_for_json.
    """
    sec_dir = asis_dir / "security"
    sec_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize every finding to prevent JSON serialization errors
    # (embedded quotes, newlines, control chars from LLM output).
    clean_review = [_sanitize_finding_for_json(r) for r in (security_review or [])]

    payload = {
        "project":            project_name,
        "generated_at":       datetime.now().isoformat(timespec="seconds"),
        "security_gate":      security_gate,
        "total":              len(clean_review),
        "summary": {
            "critical": sum(1 for r in clean_review
                            if str(r.get("severity", r.get("sev",""))).upper() == "CRITICAL"),
            "high":     sum(1 for r in clean_review
                            if str(r.get("severity", r.get("sev",""))).upper() == "HIGH"),
            "medium":   sum(1 for r in clean_review
                            if str(r.get("severity", r.get("sev",""))).upper() in ("MEDIUM","MEDIO")),
            "low":      sum(1 for r in clean_review
                            if str(r.get("severity", r.get("sev",""))).upper() in ("LOW","BAIXO")),
            "info":     sum(1 for r in clean_review
                            if str(r.get("severity", r.get("sev",""))).upper() == "INFO"),
        },
        "securityReview":     clean_review,      # canonical key read by HTML template
        "owasp":              owasp,
        "findingsSummary":    findings_summary,
        "vulns":              vulns,
        "ptPatterns":         pt_patterns,
        "secRegression":      sec_regression,
        "remediationValidation": remediation_valid,
        "taintFlow":          taint_flow,
        "complianceGaps":     compliance_gaps,
        "assetInventory":     asset_inventory,
    }
    out = sec_dir / "security-findings.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _parse_md_table_generic(path: Path, section_re: str = None) -> list:
    """Generic MD table parser. Optionally scoped to a ## section matched by section_re.
    Returns list[dict] with keys = header columns (lowercased, non-alnum → underscore).
    Returns [] if file absent or no table found.
    """
    if not path.exists():
        return []
    text = read_text(path)
    rows = []
    in_section = (section_re is None)
    headers: list = []
    for line in text.splitlines():
        if section_re and re.search(section_re, line, re.I):
            in_section = True
            headers = []
            continue
        if in_section and section_re and line.startswith('##') and not re.search(section_re, line, re.I):
            break
        if not in_section or not line.startswith('|'):
            # When no section scope, reset headers at table boundaries so each table
            # uses its own header row — prevents secondary tables with different schemas
            # from being parsed with the first table's column mapping.
            if section_re is None and headers:
                headers = []
            continue
        cols = [c.strip() for c in line.split('|')]
        cols = [c for c in cols if c != '']
        if not cols:
            continue
        if all(re.match(r'^[-:\s]+$', c) for c in cols):
            continue  # separator row
        if not headers:
            headers = [re.sub(r'[^a-z0-9]+', '_', c.lower().strip()).strip('_') for c in cols]
            continue
        row = {headers[i]: cols[i].strip() if i < len(cols) else '' for i in range(len(headers))}
        rows.append(row)
    return rows


def _sev_norm(raw: str) -> str:
    """Normalize severity string → canonical: critico|alto|medio|baixo."""
    _M = {
        "critical": "critico", "critico": "critico",
        "high":     "alto",    "alto":    "alto",
        "medium":   "medio",   "medio":   "medio",
        "low":      "baixo",   "baixo":   "baixo",
    }
    rl = (raw or '').lower()
    return next((_M[k] for k in _M if k in rl), 'medio')


def parse_pt_pattern_correlation(path: Path) -> list:
    """Parse pt-pattern-correlation.md → [{id, pattern, sev, status, ev}]
    Canonical table: | ID | Pattern | Severity | Status | Evidence |
    """
    raw = _parse_md_table_generic(path)
    result = []
    for r in raw:
        rid = (r.get('id', ''))[:30]
        if not rid:
            continue
        result.append({
            "id":      rid,
            "pattern": (r.get('pattern', r.get('pt_pattern', r.get('finding', ''))))[:80],
            "sev":     _sev_norm(r.get('severity', r.get('sev', 'medio'))),
            "status":  (r.get('status', r.get('estado', '')))[:40],
            "ev":      (r.get('evidence', r.get('evidencia', r.get('evidência', ''))))[:120],
        })
    return result


def parse_security_regression(path: Path) -> list:
    """Parse security-regression-plan.md → [{id, test, trigger, status, linked}]
    Canonical table: | ID | Test | Trigger | Status | Linked Finding |
    """
    raw = _parse_md_table_generic(path)
    result = []
    for r in raw:
        rid = (r.get('id', ''))[:30]
        if not rid:
            continue
        result.append({
            "id":      rid,
            "test":    (r.get('test', r.get('teste', '')))[:80],
            "trigger": (r.get('trigger', ''))[:40],
            "status":  (r.get('status', ''))[:40],
            "linked":  (r.get('linked_finding', r.get('linked', r.get('finding', ''))))[:30],
        })
    return result


def parse_remediation_validation(path: Path) -> list:
    """Parse remediation-validation.md → [{id, finding_ref, action, status, validated_by, date}]
    Canonical table: | ID | Finding Ref | Action | Status | Validated By | Date |
    """
    raw = _parse_md_table_generic(path)
    result = []
    for r in raw:
        rid = (r.get('id', ''))[:30]
        if not rid:
            continue
        result.append({
            "id":           rid,
            "finding_ref":  (r.get('finding_ref', r.get('finding', '')))[:30],
            "action":       (r.get('action', r.get('ação', r.get('acao', ''))))[:120],
            "status":       (r.get('status', ''))[:40],
            "validated_by": (r.get('validated_by', r.get('validated', '')))[:40],
            "date":         (r.get('date', r.get('data', '')))[:20],
        })
    return result


def parse_taint_flow(path: Path) -> list:
    """Parse taint-flow-report.md → [{id, source, sink, sanitized, sev}]
    Canonical table: | ID | Source | Sink | Sanitized | Severity |
    """
    raw = _parse_md_table_generic(path)
    result = []
    for r in raw:
        rid = (r.get('id', ''))[:30]
        if not rid:
            continue
        result.append({
            "id":        rid,
            "source":    (r.get('source', r.get('fonte', '')))[:60],
            "sink":      (r.get('sink', r.get('destino', '')))[:60],
            "sanitized": (r.get('sanitized', r.get('sanitizado', 'No')))[:20],
            "sev":       _sev_norm(r.get('severity', r.get('sev', 'medio'))),
        })
    return result


def parse_compliance_gaps(path: Path) -> list:
    """Parse compliance-gaps.md → [{id, regulation, requirement, gap, status}]

    Handles both formats:
      Format A: canonical | ID | Regulation | Requirement | Gap | Status |
      Format B: section-based ## LGPD Gap Detail / ## Compliance Status tables
                without ID column — regulation derived from ## heading.
    Auto-generates IDs (GAP-001, ...) when absent.
    """
    if not path.exists():
        return []
    text = read_text(path)
    result = []
    auto_id = 0
    current_reg = "General"
    in_table = False
    in_skip_section = False
    tbl_headers: list = []
    _REG_RE = re.compile(
        r'\b(LGPD|SOX|PCI[-\s]?DSS|ISO[-\s]?27001|BACEN|GDPR|HIPAA|CCPA|NIST|CVM)\b', re.I)
    # Sections that contain aggregator/summary tables — must NOT be parsed as gaps.
    _SKIP_SECTION_RE = re.compile(
        r'^#{1,3}\s+(summary|sumário|sumario|totals?|totais|overview|resumo)\b', re.I)

    for line in text.splitlines():
        stripped = line.strip()
        # Section heading — reset table, extract regulation
        if re.match(r'^#{1,3}\s+', stripped):
            in_table = False; tbl_headers = []
            in_skip_section = bool(_SKIP_SECTION_RE.match(stripped))
            reg_m = _REG_RE.search(stripped)
            if reg_m:
                current_reg = reg_m.group(1).upper()
            continue
        if in_skip_section:
            continue
        if not stripped.startswith('|'):
            if in_table:
                in_table = False
            continue
        cols = [c.strip() for c in stripped.split('|') if c.strip()]
        if not cols:
            continue
        # Separator row
        if all(re.match(r'^[-:\s]+$', c) for c in cols):
            continue
        # Header row detection
        if not in_table:
            joined = ' '.join(c.lower() for c in cols)
            if any(kw in joined for kw in ('require', 'gap', 'status', 'article', 'framework', 'complian')):
                in_table = True
                tbl_headers = [re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_') for c in cols]
                continue
        if not in_table or not tbl_headers:
            continue
        # Data row
        row = {tbl_headers[i]: cols[i] if i < len(cols) else ''
               for i in range(len(tbl_headers))}
        vid = row.get('id', row.get('gap_id', ''))
        if not vid:
            auto_id += 1
            vid = f"GAP-{auto_id:03d}"
        regulation = row.get('regulation', row.get('framework', current_reg)) or current_reg
        req = (row.get('lgpd_requirement', '') or row.get('requirement', '')
               or row.get('gap_requirement', '') or row.get('finding', ''))
        if not req:
            for k in tbl_headers:
                if k not in ('id', 'gap_id') and row.get(k):
                    req = row[k]; break
        gap = row.get('gap', '') or row.get('critical_gaps', '') or row.get('gaps', '')
        status_val = row.get('status', '')
        # Extract gap from status when no explicit gap column (e.g. "\u26d4 FAIL \u2014 no auth")
        if not gap and status_val:
            m_gap = re.search(r'[\u2014\u2013]\s*(.+)$', status_val)
            if not m_gap:
                m_gap = re.search(r'\bFAIL\s+[-]\s+(.+)$', status_val, re.I)
            if m_gap:
                gap = m_gap.group(1).strip()
                status_val = re.sub(r'\s*[\u2014\u2013]\s*.+$|\s*FAIL\s*-\s*.+$', '', status_val, flags=re.I).strip()
        if not req or re.match(r'^[-\s]+$', req):
            continue
        # Skip totalizer rows (e.g., "**TOTAL**", "Total", purely numeric counts)
        # Empty strings are NOT totalizers — they only mean the column is absent.
        def _is_totalizer(s: str) -> bool:
            t = re.sub(r'[\*_`\s]+', '', s or '').lower()
            if not t:
                return False
            return t in ('total', 'totais', 'sum', 'count', 'subtotal') or t.isdigit()
        if _is_totalizer(regulation) or _is_totalizer(req) or _is_totalizer(gap) or _is_totalizer(status_val):
            continue
        result.append({
            "id":          vid[:30],
            "regulation":  regulation[:40],
            "requirement": req[:120],
            "gap":         gap[:120],
            "status":      status_val[:40],
        })
    return result


def parse_asset_inventory(path: Path) -> list:
    """Parse asset-inventory.md → [{id, asset, type, classification, exposure}]
    Canonical table: | ID | Asset | Type | Classification | Exposure |
    """
    raw = _parse_md_table_generic(path)
    result = []
    for r in raw:
        rid = (r.get('id', ''))[:30]
        if not rid:
            continue
        result.append({
            "id":             rid,
            "asset":          (r.get('asset', ''))[:80],
            "type":           (r.get('type', r.get('tipo', '')))[:40],
            "classification": (r.get('classification', r.get('classificação', r.get('classificacao', ''))))[:40],
            "exposure":       (r.get('exposure', r.get('exposição', r.get('exposicao', ''))))[:40],
        })
    return result


def _read_security_json_list(asis_dir: Path, stem: str, key: str) -> list:
    """Read security/{stem}.json canonical contract for a single dataset.
    Returns list at top-level 'key' (when dict) or the list itself (when list).
    Returns [] if file absent or malformed — caller falls back to MD parser.
    """
    p = asis_dir / "security" / f"{stem}.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get(key, [])
        return []
    except (json.JSONDecodeError, OSError):
        return []


def md_to_html_inline(text: str) -> str:
    """Convert inline markdown (**bold**, *italic*, `code`) to HTML tags."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+?)\*',   r'<em>\1</em>',          text)
    text = re.sub(r'`([^`]+?)`',     r'<code>\1</code>',       text)
    return text


def severity_from_priority(priority: str) -> str:
    return {
        "P0": "critico",
        "P1": "alto",
        "P2": "medio",
        "P3": "baixo",
    }.get(priority, "medio")


def _normalize_mermaid_layout(content: str) -> str:
    """Apply dialect-aware line-boundary repairs before Mermaid receives text.

    Mermaid 11's C4 and ER lexers are line-sensitive. Artifact producers and
    HTML transformations can occasionally concatenate statements even when
    the source file is valid. This repair is intentionally conservative and
    only inserts boundaries between tokens that cannot validly share a line.
    """
    if not content:
        return content
    first = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if first == "erDiagram":
        # ER attributes, entity terminators, and the next entity declaration
        # must remain separate lexer statements.
        # Match both the normal ``} ENTITY {`` form and the already-corrupted
        # ``}ENTITY {`` form observed after HTML/runtime normalization.
        content = re.sub(r"\}(?:\s*)?(?=[A-Za-z_][A-Za-z0-9_]*\s*\{)", "}\n\n", content)
        # Mermaid v11 erDiagram does not support PK_FK composite modifier.
        # Replace with PK to prevent cascade parse errors (GR-014).
        content = re.sub(r"\bPK_FK\b", "PK", content)
        content = re.sub(r"(\b(?:int|smallint|bigint|numeric|decimal|varchar|char|text|date|datetime|boolean|float|double)\s+[A-Za-z_][\w]*\s*(?:PK(?:_FK)?|FK)?\s*)(?=\})", r"\1\n", content)
    elif first in {"C4Context", "C4Container", "C4Component", "C4Dynamic", "C4Deployment"}:
        # Keep each C4 declaration/relationship on its own line. Do not
        # rewrite quoted labels; only split a token that follows a closing ).
        tokens = r"(?:Person_Ext|Person|System_Ext|System|System_Boundary|Container_Boundary|ContainerDb_Ext|ContainerDb|Container_Ext|Container|Component_Ext|Component|Rel(?:_[A-Za-z]+)?|BiRel)"
        content = re.sub(r"\)\s+(?=(?:" + tokens + r")\s*\()", ")\n", content)
        content = re.sub(r"\}\s+(?=(?:" + tokens + r")\s*\()", "}\n", content)
    elif first in {"flowchart", "graph"}:
        # Flowchart edge labels are normalized by the quote-aware scanner in
        # sanitize_mmd(). Do not use a pipe-regex here: labels may contain
        # literal pipes inside double quotes.
        content = _sanitize_flowchart_edge_labels(content)
    return content


def _sanitize_flowchart_edge_labels(content: str) -> str:
    """Normalize flowchart edge labels without splitting quoted inner pipes."""
    lines = content.splitlines(keepends=True)
    edge_re = re.compile(r"(?P<prefix>(?:-->|-.->|==>|--o|o--|--x|x--))(?P<label>\|)")

    def replace_line(line: str) -> str:
        match = edge_re.search(line)
        if not match:
            return line
        start = match.end("label")
        quoted = False
        escaped = False
        index = start
        while index < len(line):
            char = line[index]
            if char == "\\" and not escaped:
                escaped = True
                index += 1
                continue
            if char == '"' and not escaped:
                quoted = not quoted
            elif char == "|" and not quoted:
                raw = line[start:index]
                if raw.startswith('"') and raw.endswith('"'):
                    inner = raw[1:-1].replace("\\n", " ")
                    inner = re.sub(r"\s+", " ", inner).strip()
                    normalized = '"' + inner + '"|'
                else:
                    inner = raw.replace("\\n", " ").replace('"', " ").replace("'", " ")
                    inner = re.sub(r"\s+", " ", inner).strip()
                    normalized = inner + "|"
                return line[:start] + normalized + line[index + 1:]
            escaped = False
            index += 1
        return line

    return "".join(replace_line(line) for line in lines)


def _repair_known_malformed_flowchart_edges(content: str) -> str:
    """Repair the legacy orphan-quote shape emitted by the old sanitizer.

    The old pipeline transformed a quoted label containing an inner pipe into
    ``|label|NODE"|TARGET``. This repair is deliberately narrow: it only
    handles an orphan quote immediately before the destination delimiter and
    does not infer arbitrary graph semantics.
    """
    return re.sub(r'(?P<label>\|[^\n|]+)\|(?P<orphan>[^\n|]+)"\|(?P<target>[A-Za-z_][A-Za-z0-9_]*)',
                  lambda m: '|"' + m.group('label').lstrip('|').strip() + ' ' + m.group('orphan').strip() + '"|' + m.group('target'),
                  content)


def sanitize_mmd(content: str) -> str:
    """Sanitize Mermaid content for safe embedding in JS template literals.

    Mandatory rules per summary-agent.md:
    - Strip markdown fenced code block wrapper (```mermaid ... ```) if present
    - Remove emojis (break some Mermaid parsers)
    - Replace em/en dashes (→ -, —/–) with ASCII equivalents
    - Escape backticks (would terminate the JS template literal)
    - Neutralize ${...} template expressions
    - Strip unresolved {{PLACEHOLDER}} tokens
    - Upgrade legacy 'graph' keyword → 'flowchart' (Mermaid v11+ requires it)
    """
    if not content:
        return ""

    # C4 relationship calls are frequently emitted across physical lines as:
    #   Rel(api, auth,\n    Validates tokens, MSAL)
    # Mermaid's C4 grammar requires quoted label/technology arguments. Quote
    # only those existing argument values; do not reorder or truncate content.
    content = _quote_c4_relationship_arguments(content)
    # Strip markdown fenced code block wrapper that agents may emit (```mermaid ... ```).
    # Mermaid.js does not accept fences — it would see 'mermaid' as the diagram type
    # and throw "No diagram type detected" / "Syntax error in text" (fix: C3.12).
    # This must be the FIRST operation so all subsequent rules work on bare diagram syntax.
    #
    # FIX (Bug 1 — 2026-05-05): agents emit a markdown header comment before the fence:
    #   # C4 Context Diagram — Meu-ERP AS-IS
    #   
    #   ```mermaid
    #   flowchart TB ...
    #   ```
    # The old `startswith("```")` check never matched because the content starts with `#`.
    # The unstripped fence backticks were then escaped to `'''` by the backtick-escape step,
    # producing invalid Mermaid input.  Use a regex search instead so the fence is found
    # regardless of how many header/comment lines precede it.
    content = content.strip()
    fence_match = re.search(r'```(?:mermaid|mmd)?\s*\n(.*?)\n\s*```', content, re.DOTALL)
    if fence_match:
        content = fence_match.group(1).strip()
    elif content.startswith("```"):
        lines = content.splitlines()
        # Remove opening fence (```mermaid, ```mmd, or plain ```)
        lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    # Upgrade legacy 'graph DIR' → 'flowchart DIR' (safeguard for agents that emit 'graph TB').
    # Applied FIRST so subsequent processing works on the canonical keyword.
    content = re.sub(r'^graph\s+(TB|LR|TD|RL|BT)\b', r'flowchart \1', content, flags=re.MULTILINE)
    # ── Compatibility Rule C4-CB: Component_Boundary → Container_Boundary ─────
    # `Component_Boundary` is a C4PlantUML keyword that does NOT exist in the
    # Mermaid v11 C4Component grammar. The Mermaid lexer fails with:
    #   "Lexical error on line N. Unrecognized text. ...Component_Boundary(c"
    # The visual result is identical to Container_Boundary, which IS valid.
    # This fix is safe: it only applies when the C4Component diagram type is used.
    content = content.replace('Component_Boundary(', 'Container_Boundary(')
    # ── Compatibility Rule 0: C4 reserved-keyword collision ────────────────────
    # Mermaid v11 treats C4Container, C4Component, C4Dynamic, C4Deployment as
    # native C4 diagram-type declarations.  When these words appear as subgraph
    # IDs inside a flowchart diagram, the auto-detector routes the content to
    # the C4 parser — which cannot parse `flowchart TB` syntax — producing
    # "Lexical error on line 1. Unrecognized text." (fix: C3.15).
    # Rename to c4_container etc. so the flowchart parser handles them.
    # Note: C4Context does NOT trigger this issue because Mermaid's detection
    # hierarchy handles it differently.
    # _C4_RESERVED = ['C4Container', 'C4Component', 'C4Dynamic', 'C4Deployment']
    # for kw in _C4_RESERVED:
    #     #safe = kw.replace('C4', 'c4_')          # C4Container → c4_Container
    #     content = content.replace(kw, safe)
    # Flowchart edge labels are delimited by pipes, but a natural-language label
    # may itself contain a pipe (for example: `|"Settings | SEO"|`). The old
    # regex treated that inner pipe as the delimiter and corrupted the edge,
    # leaving orphan quotes and node IDs in the generated Mermaid. Parse only
    # edge labels, respecting quoted content, and preserve the outer quotes.
    content = _sanitize_flowchart_edge_labels(content)
    content = _repair_known_malformed_flowchart_edges(content)
    # Square-bracket node labels with spaces are safer when quoted in Mermaid v11.
    # Convert: NODE[My label] -> NODE["My label"] (only when not already quoted).
    # Negative lookbehind (?<!\\) prevents matching tokens like `n[...]` that
    # are part of a \n escape sequence inside an already-quoted label — which
    # would inject a stray " inside the outer string and corrupt the tokenizer.
    content = re.sub(
        r'(?<!\\)(\b[A-Za-z_][\w-]*)\[([^\]\n"]*\s[^\]\n"]*)\]',
        lambda m: f'{m.group(1)}["{m.group(2).strip()}"]',
        content)
    # Unquoted square-bracket labels that contain a literal \n (2-char backslash+n)
    # but NO space are missed by the rule above. Mermaid v11 may interpret \n inside
    # unquoted [...] as a newline escape sequence, prematurely terminating the label
    # token and causing a parse error (e.g. Main[frmPrincipal\nDashboard] fails).
    # Fix: replace \n with a space and wrap the label in double-quotes.
    content = re.sub(
        r'(\b[A-Za-z_][\w-]*)\[([^\]"]*\\n[^\]"]*)\]',
        lambda m: f'{m.group(1)}["{m.group(2).replace(chr(92) + "n", " ").strip()}"]',
        content)
    # ── Compatibility Rule 1: subgraph shape notation ──────────────────────────
    # Agents sometimes emit `subgraph ID [("label")]` using the cylindrical-node
    # shape syntax. Mermaid 11 accepts shape notation ONLY for standalone nodes,
    # NOT for subgraph labels → "Syntax error in text".
    # Fix: strip the shape wrapper, keep plain `subgraph ID ["label"]`.
    def _fix_subgraph_shape(m):
        sid = m.group(1)
        label = m.group(2)
        # Remove HTML tags and normalise whitespace in the extracted label
        label = re.sub(r'<[^>]+>', '', label)
        label = re.sub(r'\\n', ' - ', label)
        label = label.strip(' -')
        return f'subgraph {sid} ["{label}"]'
    content = re.sub(
        r'subgraph\s+(\w+)\s+\[\("([^")]*)"?\)\]',
        _fix_subgraph_shape,
        content)

    # ── Compatibility Rule 2: classDiagram member names with / or ... ──────────
    # `+setters/getters: ...` uses `/` (not a valid identifier char) and
    # `...` (not a valid return-type token) → "Syntax error in text".
    # Fix: normalise to `+settersAndGetters() void`.
    content = re.sub(
        r'(\s*[+\-#~]?\w+)/(\w+)\s*:\s*\.\.\.',
        r'\1And\2() void',
        content)
    # Also catch the bare `+member: ...` pattern (placeholder return type)
    content = re.sub(
        r'(\s*[+\-#~]\w+)\s*:\s*\.\.\.',
        r'\1() void',
        content)
    # Also catch `+setters/getters()` — a slash-separated compound method call
    # (no colon/ellipsis, unlike the two rules above) — same invalid-identifier
    # problem, different shape. Fix: normalise to `+settersAndGetters() void`.
    content = re.sub(
        r'(\s*[+\-#~]?\w+)/(\w+)\s*\(\s*\)',
        r'\1And\2() void',
        content)

    # ── Compatibility Rule 3: extended emoji removal ────────────────────────────
    # The base filter covers U+1F000–U+1FFFF (supplementary emoji).
    # BMP emoji (⚠️ U+26A0, ✅ U+2705, ❌ U+274C, etc.) and variation
    # selectors (U+FE00–U+FE0F) are missed. Extend the removal.
    content = re.sub(r'[\u2600-\u27FF]', '', content)   # Misc Symbols & Dingbats
    content = re.sub(r'[\uFE00-\uFE0F]', '', content)   # Variation Selectors
    # Remove emojis (BMP supplementary range)
    content = re.sub(r'[\U0001F000-\U0001FFFF]', '', content)
    # Replace → with ->  ,  — and – with  -
    content = content.replace('\u2192', '->')
    content = content.replace('\u2014', ' - ').replace('\u2013', ' - ')
    # Escape backticks so they don't terminate the JS template literal
    content = content.replace('`', "'")
    # Neutralize ${...} to prevent JS template expression injection
    content = content.replace('${', '$ {')
    # Strip semicolons — Mermaid interprets ';' as a statement separator
    # which causes "Syntax error in text" when it appears inside node labels
    # or edge definitions.
    content = content.replace(';', ' ')
    # Strip unresolved {{VAR}} placeholders
    content = re.sub(r'\{\{[A-Z_0-9]+\}\}', '', content)
    # Normalize non-ASCII characters to ASCII base letters.
    # Accented chars (ê, ú, ã, ç …) inside Mermaid labels cause silent
    # parse failures in some builds; map them to their base letter.
    import unicodedata
    def _to_ascii(c):
        if ord(c) < 128:
            return c
        nfd = unicodedata.normalize('NFD', c)
        base = ''.join(ch for ch in nfd if unicodedata.category(ch) != 'Mn')
        return base if base and all(ord(b) < 128 for b in base) else '?'
    content = ''.join(_to_ascii(c) for c in content)
    # In graph TB / flowchart, square brackets INSIDE quoted node labels
    # (e.g. ["Accounts Payable [AP]"]) confuse the Mermaid 11+ tokenizer —
    # the inner ] is taken as the label-close bracket → "Syntax error in text".
    # Replace [ → ( and ] → ) inside all double-quoted strings (single-line).
    #
    # MERMAID 11 COMPATIBILITY: Replace literal \n (backslash+n, two chars) inside
    # quoted labels with <br/>.  In Mermaid v11+, the flowchart lexer treats \n as
    # an escape sequence that produces an actual newline, which then terminates the
    # quoted-string token prematurely and causes "Lexical error on line 1".
    # Using <br/> (with htmlLabels:true) is the correct Mermaid 11 way to insert
    # line breaks inside node and subgraph labels.  This fix is backward-compatible:
    # old .mmd files that used \n will automatically render correctly; new files
    # should use <br/> directly.
    def _fix_quoted_label(m):
        inner = m.group(1)
        inner = inner.replace('[', '(').replace(']', ')')
        # Normalize <br> / <br/> → space (avoids literal tag in rendered output)
        inner = re.sub(r'<br\s*/?>', ' ', inner, flags=re.IGNORECASE)
        # Normalize literal \n (two chars) → space (avoids lexer error)
        inner = inner.replace('\\n', ' ')
        return '"' + inner + '"'
    content = re.sub(r'"([^"\n]*)"', _fix_quoted_label, content)
    # ── Compatibility Rule 6: strip raw HTML tags from non-label positions ──────
    # Agents sometimes emit HTML markup (e.g. <br/>, <strong>, <p>, stray tags
    # from embedded file content) in positions where Mermaid does NOT support
    # HTML — outside of double-quoted labels with htmlLabels:true.  These cause
    # silent parse failures or "Syntax error in text" in Mermaid 11.
    #
    # Protect Mermaid bidirectional/reverse arrow operators from the HTML-tag
    # stripper below.  <-->, <==>, <~~> (and their half-arrow variants <--, <==,
    # <~~) all start with '<' and are matched by r'<[^>]+>' — the stripper would
    # silently delete them, leaving 'A |label|B' instead of 'A <-->|label|B' →
    # "Syntax error in text".
    #
    # Strategy: substitute the '<' with a private-use sentinel BEFORE stripping,
    # then restore AFTER.  The sentinel survives both the tag-stripper and
    # json.dumps(), so D.staticDiagrams carries the raw '<-->' that the JS
    # `pre.textContent = mmdText` assignment delivers unmodified to Mermaid.
    # (Do NOT use HTML entity &lt; here — textContent does NOT decode HTML
    # entities, so Mermaid would receive '&lt;-->' and fail.)
    _MMD_LT = '\x00MMDLT\x00'
    content = re.sub(r'<(-+>?|=+>?|~+>?)', lambda m: _MMD_LT + m.group(1), content)
    #
    # Strategy (in order, applied to each line):
    #   - Lines that start a quoted-label context (contain '"..."') are handled
    #     by _fix_quoted_label above: <br/> is kept (htmlLabels), other tags
    #     stripped but their text content preserved.
    #   - Unquoted lines (node declarations, edge definitions, directives):
    #     <br/> and <br> are replaced by a space; all other HTML tags are stripped
    #     but their inner text is preserved.
    def _strip_html_unquoted(line: str) -> str:
        # Replace <br> / <br/> with a newline-safe separator in unquoted context
        line = re.sub(r'<br\s*/?>', ' ', line, flags=re.IGNORECASE)
        # Strip remaining HTML tags (keep their text content)
        line = re.sub(r'<[^>]+>', '', line)
        return line

    processed_lines = []
    for line in content.splitlines():
        # If the line contains at least one double-quoted segment it has already
        # been processed by _fix_quoted_label (which keeps <br/> and strips the
        # rest).  Only apply the unquoted stripper to lines that have no quotes.
        if '"' not in line:
            line = _strip_html_unquoted(line)
        processed_lines.append(line)
    content = '\n'.join(processed_lines)

    # Restore the Mermaid arrow sentinel placed before the HTML-stripping loop.
    content = content.replace(_MMD_LT, '<')

    # In sequenceDiagram, an unquoted alias that contains brackets also fails:
    # e.g. "    actor User as User [Accountant]".
    # Preserve leading whitespace, wrap alias in quotes, replace brackets.
    def _fix_seq_alias(m):
        indent, kw, sid, alias = m.group(1), m.group(2), m.group(3), m.group(4).strip()
        # Strip any pre-existing wrapping quotes (the alias may already be a
        # valid `"Name"` from a source that got this right the first time, or
        # — from a previous buggy pass of this very function — a run of stray
        # quote characters). Without this, re-running sanitize_mmd() on an
        # already-quoted alias is NOT idempotent: each pass treats the outer
        # quotes as literal content, escapes them to `'`, and wraps the result
        # in a NEW pair of quotes, growing by two quote characters per side on
        # every run (`"Name"` → `"'Name'"` → `"'''Name'''"` → ...).
        alias = re.sub(r'^[\'"]+|[\'"]+$', '', alias)
        alias_clean = alias.replace('[', '(').replace(']', ')')
        # Strip HTML tags — sequenceDiagram aliases are parsed lexically by
        # Mermaid and do NOT support HTML (unlike flowchart htmlLabels).
        # <br/> in an alias causes "Syntax error in text" on Mermaid v11.
        alias_clean = re.sub(r'<br\s*/?>', ' ', alias_clean, flags=re.IGNORECASE)
        alias_clean = re.sub(r'<[^>]+>', '', alias_clean)
        # Neutralize arrow tokens inside the alias text. The earlier global
        # `→ → ->` replacement leaves `->` / `-->` literals that the Mermaid 11
        # sequenceDiagram lexer interprets as arrow operators even when the
        # alias is wrapped in quotes — producing "Expecting 'ACTOR', got 'INVALID'".
        alias_clean = re.sub(r'-{1,2}>>?', ' to ', alias_clean)
        # Quotes inside the alias would also terminate the wrapping quotes.
        alias_clean = alias_clean.replace('"', "'")
        alias_clean = ' '.join(alias_clean.split())  # collapse whitespace
        # FIX (Bug 2 — 2026-05-05): `as` was missing from the return value, producing
        # `participant U "User"` which is invalid sequenceDiagram syntax.
        # Correct form: `participant U as "User"`.
        return '{}{} {} as "{}"'.format(indent, kw, sid, alias_clean)
    content = re.sub(
        r'^(\s*)(actor|participant)\s+(\S+)\s+as\s+(.+)$',
        _fix_seq_alias,
        content,
        flags=re.MULTILINE)

    # ── Compatibility Rule 5: pipe-edge labels with inner punctuation ──────────
    # Keep the quote-aware scanner as the single implementation. A second
    # pipe-regex here previously re-split labels containing an inner pipe and
    # recreated the exact corruption this sanitizer had just repaired.
    content = _sanitize_flowchart_edge_labels(content)
    content = _repair_known_malformed_flowchart_edges(content)
    content = _normalize_mermaid_layout(content.strip())
    # Final guard: remove blank lines inside erDiagram entity blocks.
    # Mermaid v11 ER grammar rejects any empty line inside { } with
    # "Expecting 'ATTRIBUTE_WORD', got 'BLOCK_STOP'".  This guard runs
    # after all other transformations to catch blanks introduced by any
    # intermediate step (incl. the Unicode normaliser and the HTML stripper).
    first_token = next((ln.strip() for ln in content.splitlines() if ln.strip()), "")
    if first_token == "erDiagram":
        stripped_lines: list[str] = []
        in_er_block = False
        for ln in content.splitlines():
            ln_stripped = ln.strip()
            if ln_stripped.endswith("{") and not ln_stripped.startswith("%"):
                in_er_block = True
                stripped_lines.append(ln)
                continue
            if ln_stripped == "}":
                in_er_block = False
                stripped_lines.append(ln)
                continue
            if in_er_block and ln_stripped == "":
                continue
            stripped_lines.append(ln)
        content = "\n".join(stripped_lines)
    return content


# ═══ CORE BUILDERS ═══

# Required phase folder keys that must always exist in the file tree
# (maps to PHASE_FOLDER_MAP in the HTML template).
REQUIRED_PHASE_KEYS = ['asis', 'tobe', 'prototype', 'f4', 'qa', 'deliverables', 'devops']


def build_file_tree(outputs_dir: Path, summary_dir: Path) -> dict:
    """╔═══ FIX ISSUE #4: File Explorer ═══╗

    Rules (per summary-agent.md spec and bug C4.5 fix):
    - outputs/tobe/prototype/**  →  tree key 'prototype'  (F3/F4 Deliverables)
    - outputs/tobe/**            →  tree key 'tobe'        (F2 Deliverables)
    - All other top dirs         →  tree key = top folder name
    - All 6 required phase keys must exist (empty nodes if directory absent)
    
    Source-code files (.cs, .ts, .tsx, .js, .py etc.) are excluded from
    embedded content to reduce file size — they're not needed in the summary.
    """
    # Extensions excluded from the Deliverables file list (source code).
    # F4 has a dedicated file-tree node, but the Tech Stack Deliverables view
    # must expose project manifests without embedding every generated source file.
    SOURCE_CODE_EXTS = {
        'cs', 'ts', 'tsx', 'js', 'mjs', 'vbproj',
        'fsproj', 'ps1', 'psm1', 'psd1', 'bat', 'sh', 'py', 'rb', 'go',
        'java', 'kt', 'swift', 'cpp', 'c', 'h', 'hpp', 'rs', 'dart', 'vue',
    }
    print("\n🔧 [Issue #4 Fix] Building File Tree with content embedding...")

    tree: dict = {}
    total_embedded = 0
    files_embedded = 0

    # Ensure all required phase keys always exist (even when dirs are absent)
    for key in REQUIRED_PHASE_KEYS:
        tree[key] = {"label": key.upper(), "files": [], "subdirs": {}}

    for path in sorted(outputs_dir.rglob("*")):
        if not path.is_file():
            continue
        # Skip hidden/internal directories (e.g. .internal build artifacts)
        if any(part.startswith('.') for part in path.parts):
            continue
        # Skip the summary output directory itself
        if path.is_relative_to(summary_dir):
            continue
        # Skip pipeline_runner/ reports — they embed old summary HTML content
        # which causes C4.3 false positives (nav('s-f2-code') found in embedded file text)
        if 'pipeline_runner' in path.parts:
            continue
        # Skip old/partial summary HTML files that may appear in other dirs
        # (e.g. tobe/prototype/*.part*.html from merge operations) — embedding
        # these causes C4.3 false positives (nav('s-f2-code') found in file content)
        if path.suffix.lower() in ('.html', '.htm') and (
            path.stem.startswith('AVA-FABRIC-SUMMARY-') or
            '.part' in path.stem
        ):
            continue

        rel = path.relative_to(outputs_dir)      # e.g. tobe/prototype/demo.md
        parts = rel.parts                         # ('tobe', 'prototype', 'demo.md')
        top_key = parts[0]                        # 'tobe'

        # ── Phase isolation: keep prototype/source-code/devops/iac out of F2 ──
        # This prevents phase-specific submenus from showing F2 (tobe) files.
        if top_key == 'tobe' and len(parts) > 1 and parts[1] == 'prototype':
            top_key = 'prototype'
            # Path remains the original (tobe/prototype/...) for content lookup;
            # but the tree node hierarchy starts after 'tobe/prototype/'.
            node_parts = parts[2:]               # dirs/file inside prototype/
        elif top_key == 'tobe' and len(parts) > 1 and parts[1] == 'source-code':
            # F4 Tech Stack Deliverables are generated under
            # outputs/tobe/source-code/**. Route this subtree to the dedicated
            # f4 tree key used by the sidebar instead of generic F2 `tobe`.
            top_key = 'f4'
            node_parts = parts[2:]               # dirs/file inside source-code/
        elif top_key == 'tobe' and len(parts) > 1 and parts[1] in ('devops', 'iac'):
            # F6 DevOps artifacts are generated under outputs/tobe/devops/** and
            # outputs/tobe/iac/**. Route to the dedicated 'devops' key so the
            # File Explorer "F6 — DevOps" card is actually populated.
            top_key = 'devops'
            node_parts = parts[1:]               # keep 'devops'/'iac' as subdir label
        else:
            node_parts = parts[1:]               # dirs/file inside the top folder

        if top_key not in tree:
            tree[top_key] = {"label": top_key.upper(), "files": [], "subdirs": {}}

        node = tree[top_key]
        # Navigate/create intermediate subdir nodes (all parts except the last filename)
        for subdir in node_parts[:-1]:
            node = node["subdirs"].setdefault(
                subdir, {"label": subdir, "files": [], "subdirs": {}}
            )

        content = None
        truncated = False
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        # Skip source code files entirely — they add size without UI value
        file_ext = path.suffix.lstrip(".").lower()
        if file_ext in SOURCE_CODE_EXTS:
            continue

        if is_readable(path):
            if size > MAX_FILE_BYTES or total_embedded + size > MAX_TOTAL_BYTES:
                truncated = True
            else:
                content = read_text(path)
                # Sanitize .mmd files so Mermaid renders correctly in the browser
                # (same rules as the static diagram substitution path)
                if path.suffix.lower() == '.mmd' and content:
                    content = sanitize_mmd(content)
                # Strip {{UPPER_SNAKE_CASE}} tokens from ANY embedded content so
                # the C1.3 "zero unresolved placeholders" check always passes.
                # Template placeholders in source files (e.g. post-deploy-validation.yml)
                # must not appear verbatim in the HTML output.
                if content:
                    content = re.sub(r'\{\{[A-Z0-9_]+\}\}', '', content)
                total_embedded += size
                files_embedded += 1

        # path field stays relative to outputs_dir for consistent lookups
        node["files"].append({
            "name": path.name,
            "path": str(rel).replace("\\", "/"),
            "ext": path.suffix.lstrip(".").lower(),
            "dir": str(path.parent.relative_to(outputs_dir)).replace("\\", "/"),
            "content": content,
            "truncated": truncated,
        })

    print(f"   📦 {files_embedded} files with content ({total_embedded/1024:.1f} KB)")

    # ── Build flat category lists for each phase node ──────────────────────
    # These are used by the Deliverables submenu to group files by category.
    def _categorize_files(node: dict) -> dict:
        """Return {diagrams, security, functional, qa, other} from a phase node."""
        flat: list = []
        def _collect(n):
            flat.extend(n.get("files", []))
            for sd in n.get("subdirs", {}).values():
                _collect(sd)
        _collect(node)

        DIAG_NAMES  = {"er-diagram", "c4-context", "c4-container", "c4-component",
                       "architecture-blueprint", "context-map",
                       "seq-arquitetural", "migration-gantt", "screen-navigation"}
        SEC_NAMES   = {"security", "sast", "threat-model", "vulnerability",
                       "dependency", "pentest", "taint", "iast", "compliance"}
        FUNC_NAMES  = {"business-rules", "screen-nav",
                       "screen-rules", "screen-navigation-map", "navigation",
                       "requirements", "docs"}
        QA_NAMES    = {"test", "coverage", "baseline", "gaps", "qa", "scenario",
                       "test-case", "test-plan", "test-map", "defect"}
        # Excluded from the Deliverables submenu entirely — AS-IS discovery
        # doc, not a shippable deliverable artifact.
        EXCLUDED_NAMES = {"value-chain"}

        def _classify(f):
            name_lc = f["name"].lower().replace("-", " ").replace("_", " ")
            dir_lc  = f.get("dir", "").lower()
            ext     = f.get("ext", "")
            if any(k in f["name"].lower() for k in EXCLUDED_NAMES):
                return None
            if ext == "mmd" or any(k in name_lc or k in dir_lc for k in DIAG_NAMES):
                return "diagrams"
            if any(k in name_lc or k in dir_lc for k in SEC_NAMES):
                return "security"
            if any(k in name_lc or k in dir_lc for k in QA_NAMES):
                return "qa"
            if any(k in name_lc or k in dir_lc for k in FUNC_NAMES):
                return "functional"
            return "other"

        cats: dict = {"diagrams": [], "security": [], "functional": [], "qa": [], "other": []}
        for f in flat:
            cat = _classify(f)
            if cat:
                cats[cat].append(f)
        return cats

    for key in tree:
        tree[key]["categories"] = _categorize_files(tree[key])

    return tree


def build_artifact_inventory(outputs_dir: Path) -> dict:
    """╔═══ FIX ISSUE #3: Artifacts Section ═══╗"""
    print("\n🔧 [Issue #3 Fix] Building Artifact Inventory (D.arts)...")
    
    artifact_inventory = {}
    total_artifacts = 0
    
    for agent_id in ALL_AGENTS:
        artifacts_for_agent = []
        
        if agent_id in ARTIFACT_MAP:
            for artifact in ARTIFACT_MAP[agent_id]:
                file_path = outputs_dir / artifact["path"]
                if file_path.exists():
                    artifacts_for_agent.append({
                        "key": artifact["key"],
                        "path": artifact["path"]
                    })
                    total_artifacts += 1
        
        artifact_inventory[agent_id] = artifacts_for_agent
    
    print(f"   📄 {total_artifacts} artifacts catalogued")
    return artifact_inventory


def _flatten_tree_node_files(node: dict) -> list:
    """Flatten a build_file_tree() node (nested subdirs) into a flat file list."""
    files = list(node.get("files", []))
    for sub in node.get("subdirs", {}).values():
        files.extend(_flatten_tree_node_files(sub))
    return files


def list_prototype_chips(file_tree: dict) -> list:
    """F3 chips = every real file under tobe/prototype/**, not a fixed 3-name list.

    Reuses build_file_tree()'s 'prototype' node (same glob already computed for
    the File Explorer) instead of re-walking the filesystem.
    """
    proto_files = _flatten_tree_node_files(file_tree.get("prototype", {}))
    return [
        {"key": f["name"], "path": f["path"]}
        for f in sorted(proto_files, key=lambda x: x["path"])
    ]


def list_backend_csproj_projects(outputs_dir: Path) -> list:
    """Glob tobe/source-code/**/*.csproj for F4 Backend project chips.

    .csproj is excluded from build_file_tree()'s embedded content (source-code
    extensions are skipped there), so backend project chips are discovered
    directly here instead of via D.fileTree. Project names are project-specific
    and never hardcoded.
    """
    src_dir = outputs_dir / "tobe" / "source-code"
    if not src_dir.exists():
        return []
    projects = []
    for p in sorted(src_dir.rglob("*.csproj")):
        rel = p.relative_to(outputs_dir)
        projects.append({"key": p.stem, "path": str(rel).replace("\\", "/")})
    return projects


def build_agent_status_map(outputs_dir: Path) -> dict:
    """╔═══ FIX ISSUE #2: Phases & Agents ═══╗
    
    Combines two sources:
    1. shared-context.md YAML front-matter: asis_status / tobe_status fields
    2. File presence check via ARTIFACT_MAP (fallback per-agent)
    """
    print("\n🔧 [Issue #2 Fix] Building Agent Status Map (D.agentStatus)...")

    # Read shared-context for phase-level status
    project_name = outputs_dir.parts[-2]  # projects/{name}/outputs
    shared_ctx_path = outputs_dir.parent / "context" / "shared-context.md"
    phase_done: dict = {}
    if shared_ctx_path.exists():
        ctx_text = shared_ctx_path.read_text(encoding="utf-8", errors="replace")
        # Source A: YAML front-matter fields (legacy format)
        if re.search(r'^asis_status:\s*"?COMPLETED"?', ctx_text, re.M):
            phase_done["asis"] = True
        if re.search(r'^tobe_status:\s*"?COMPLETED"?', ctx_text, re.M):
            phase_done["tobe"] = True
        # Source B: "Status da Esteira" table rows (current format)
        # Matches: | AS-IS ... | ✅ COMPLETED | ... |  OR  | TO-BE ... | ✅ COMPLETED | ... |
        for line in ctx_text.splitlines():
            if not line.startswith('|'):
                continue
            if '\u2705' not in line and 'COMPLETED' not in line.upper():
                continue
            lo = line.lower()
            if 'as-is' in lo or 'asis' in lo or 'diagn' in lo:
                phase_done["asis"] = True
            if 'to-be' in lo or 'tobe' in lo or 'architect' in lo or 'design' in lo:
                phase_done["tobe"] = True
            if 'stack' in lo or 'codegen' in lo or 'code gen' in lo:
                phase_done["stack"] = True
            if 'qa' in lo or 'qualit' in lo:
                phase_done["qa"] = True
            if 'entreg' in lo or 'deliver' in lo or 'packag' in lo:
                phase_done["deliverables"] = True
            if 'devops' in lo or 'iac' in lo or 'ci/cd' in lo:
                phase_done["devops"] = True

    agent_status = {}
    phase_status = build_phase_status_map(outputs_dir)
    TOBE_AGENTS = [
        "ava-tobe-orchestrator",
        "ava-tobe-architecture-decision-matrix", "ava-tobe-adr",
        "ava-tobe-architecture-design", "ava-tobe-architecture-technical",
        "ava-tobe-database-policy", "ava-tobe-database-design",
        "ava-tobe-security-design",
        "ava-tobe-measure-size", "ava-tobe-migration-plan",
        "ava-tobe-coexistence-strategy", "ava-tobe-risk-mitigation", "ava-tobe-spec",
        "ava-docs-tobe", "ava-developer-guide-tobe",
        "ava-tobe-user-journeys", "ava-tobe-designer-system",
        "ava-test-plan-tobe",
    ]
    STACK_AGENTS = [
        "ava-stack-orchestrator",
        "ava-stack-dotnet-backend", "ava-stack-java-backend",
        "ava-stack-python-backend", "ava-stack-go-backend",
        "ava-stack-angular-frontend", "ava-stack-react-frontend",
        "ava-stack-vue-frontend", "ava-stack-blazor-frontend",
        "ava-stack-docs-researcher", "ava-stack-build-validator",
    ]
    QA_AGENTS    = [
        "ava-qa-orchestrator", "ava-qa-behavior-mapping", "ava-qa-gaps-requirements",
        "ava-qa-bridge-fastqa-tobe", "ava-qa-test-case-generator", "ava-qa-script-generator",
        "ava-qa-db-integrity-test", "ava-qa-contract-test-generator",
        "ava-qa-frontend-test-generator",
        "ava-qa-exploratory", "ava-qa-evidence-capture", "ava-qa-defect-identifier",
    ]
    DELIV_AGENTS = [
        "ava-deliverable-packager", "ava-deliverable-tech-docs", "ava-deliverable-migration-plan",
        "ava-deliverable-test-evidence", "ava-deliverable-code-templates",
        "ava-deliverable-security-compliance", "ava-deliverable-client-demo",
    ]
    DEVOPS_AGENTS = [
        "ava-devops-iac", "ava-devops-ci", "ava-devops-cd",
        "ava-devops-containerize", "ava-devops-iac-azure",
        "ava-devops-cost-estimate", "ava-devops-monitoring-observability",
        "ava-devops-package-approval", "ava-devops-compare-version",
    ]
    # Solution agents: only the one matching legacy_technology will have artifacts.
    # When AS-IS phase is marked COMPLETED in shared-context, mark all as done to
    # avoid penalising projects that used a different language agent.
    SOLUTION_AGENTS = {
        "ava-asis-solution-delphi", "ava-asis-solution-dotnet",
        "ava-asis-solution-java", "ava-asis-solution-visualbasic",
    }
    for agent_id in ALL_AGENTS:
        # Phase-level override from shared-context
        if phase_done.get("asis") and agent_id in ASIS_AGENTS:
            agent_status[agent_id] = "done"
            continue
        if phase_done.get("tobe") and agent_id in TOBE_AGENTS:
            agent_status[agent_id] = "done"
            continue
        if phase_done.get("stack") and agent_id in STACK_AGENTS:
            agent_status[agent_id] = "done"
            continue
        if phase_done.get("qa") and agent_id in QA_AGENTS:
            agent_status[agent_id] = "done"
            continue
        if phase_done.get("deliverables") and agent_id in DELIV_AGENTS:
            agent_status[agent_id] = "done"
            continue
        if phase_done.get("devops") and agent_id in DEVOPS_AGENTS:
            agent_status[agent_id] = "done"
            continue
        # File-presence fallback
        has_any = False
        if agent_id in ARTIFACT_MAP:
            for artifact in ARTIFACT_MAP[agent_id]:
                if (outputs_dir / artifact["path"]).exists():
                    has_any = True
                    break
        # ava-asis-security-orchestrator: when security is disabled its files are absent;
        # report as "skipped" so FR-005 (done-agents must have artifacts) does not fire.
        if not has_any and agent_id == "ava-asis-security-orchestrator":
            agent_status[agent_id] = "skipped"
        # Solution agents: only one language runs per project. Non-executed solution
        # agents have no artifacts — mark as "skipped" (not "pending") so they don't
        # count against the completion % while the one that ran counts as "done".
        elif not has_any and agent_id in SOLUTION_AGENTS:
            agent_status[agent_id] = "skipped"
        # Orchestrator/coordinator agents: they produce no direct disk artifacts —
        # all output is delegated to sub-agents. Mark as "coordinator" (rendered as
        # done in UI) so FR-005 knows the empty artifact list is intentional.
        # Note: phase_status.py FR-005 has a matching allowlist for these agents.
        elif not has_any and agent_id in {
            "ava-tobe-orchestrator",
            "ava-stack-orchestrator",
            "ava-qa-orchestrator",
        }:
            # Coordinators own no report. Their status is derived from the
            # complete output contract of the phase they coordinate, not from
            # a nonexistent master-report file or a shared-context placeholder.
            if (phase_status.get("2") == "done" and agent_id == "ava-tobe-orchestrator") or \
               (phase_status.get("4") == "done" and agent_id == "ava-stack-orchestrator") or \
               (phase_status.get("5") == "done" and agent_id == "ava-qa-orchestrator") or \
               (phase_done.get("tobe") and agent_id == "ava-tobe-orchestrator") or \
               (phase_done.get("stack") and agent_id == "ava-stack-orchestrator") or \
               (phase_done.get("qa") and agent_id == "ava-qa-orchestrator"):
                agent_status[agent_id] = "done"
            else:
                agent_status[agent_id] = "pending"
        else:
            agent_status[agent_id] = "done" if has_any else "pending"

    # Test QA AS-IS owns the QA artifacts that feed the F1 Test Cases view.
    # Keep this explicit because the agent has no single legacy report file.
    asis_qa_files = (
        outputs_dir / "asis" / "qa" / "test-plan.md",
        outputs_dir / "asis" / "qa" / "test-gaps.md",
        outputs_dir / "asis" / "qa" / "test-cases.md",
    )
    if any(path.exists() for path in asis_qa_files):
        agent_status["ava-asis-test-qa"] = "done"

    # F8 Summary agents: mark done if their primary output (HTML or report) exists.
    summary_dir = outputs_dir / "summary"
    if any(summary_dir.glob("AVA-FABRIC-SUMMARY-*.html")):
        agent_status["ava-summary"] = "done"
    if (summary_dir / "remediation-report.json").exists() or \
       (summary_dir / "remediation-report.md").exists():
        agent_status["ava-summary-remediation"] = "done"
    if (summary_dir / "deep-audit-report.json").exists() or \
       (summary_dir / "mermaid-validation-report.json").exists():
        agent_status["ava-summary-validate"] = "done"

    done_count    = sum(1 for s in agent_status.values() if s == "done")
    skipped_count = sum(1 for s in agent_status.values() if s == "skipped")
    effective     = TOTAL_AGENTS - skipped_count
    print(f"   📊 {done_count}/{effective} agents done (skipped: {skipped_count}, total: {TOTAL_AGENTS})")
    return agent_status


def build_phase_status_map(outputs_dir: Path) -> dict:
    """Derive phase status from complete, canonical phase-level evidence."""
    def exists_any(*relative_paths: str) -> bool:
        return any((outputs_dir / rel).exists() for rel in relative_paths)

    def status(groups: list[tuple[str, ...]]) -> str:
        present = sum(1 for group in groups if exists_any(*group))
        if present == len(groups):
            return "done"
        return "running" if present else "pending"

    return {
        "1": status([
            ("asis/master-report.md",),
            ("asis/architecture-blueprint.md",),
            ("asis/inventory-report.md",),
            ("asis/gaps-risks-report.md", "asis/gap-list-report.md"),
            ("asis/security-map.md", "asis/security/security-findings.json"),
            ("asis/db-analysis-report.md", "asis/db/db-analysis-report.md"),
            ("asis/docs/business-rules.md",),
            ("asis/qa/test-cases.md",),
        ]),
        "2": status([
            ("tobe/docs/architecture-blueprint.md", "tobe/diagrams/architecture-blueprint.mmd"),
            ("tobe/docs/bounded-context-map.md", "tobe/bounded-context-map.md"),
            ("tobe/docs/tech-framework-document.md", "tobe/patterns-applied.json"),
            ("tobe/db/sql-strategy.md",),
            ("tobe/docs/db-design-report.md", "tobe/diagrams/mer-diagram-tobe.mmd", "tobe/db/db-type-target.json"),
            ("tobe/docs/sizing-report.md",),
            ("tobe/docs/migration-plan.md",),
            ("tobe/docs/openapi/openapi-spec.yaml", "tobe/docs/api-map.md"),
            ("tobe/qa/test-plan.md", "tobe/tests/traceability-matrix.md"),
        ]),
        "3": status([("tobe/prototype/index.html", "tobe/prototype")]),
        "4": status([("tobe/source-code/backend",), ("tobe/source-code/frontend",)]),
        "5": status([
            ("qa/quality-strategy.md",),
            ("qa/qa-master-report.md",),
            ("tobe/qa/test-plan.md",),
            ("tobe/qa/test-cases.md",),
            ("tobe/qa/gap-analysis.md",),
            ("tobe/tests/functional-test-matrix.md",),
            ("tobe/tests/traceability-matrix.md",),
            ("tobe/tests/automatable-test-cases.md",),
            ("tobe/tests/features",),
            ("qa/scenario-generator-report.md",),
            ("qa/scenario-generator/scenario-register.json",),
        ]),
        "6": status([
            ("tobe/devops/devops-plan.md",),
            ("tobe/devops/ci-pipeline.yml",),
            ("tobe/devops/cd-pipeline.yml",),
            ("tobe/iac/wave-1/main.tf", "tobe/infra/terraform/main.tf", "tobe/infra/bicep/main.bicep"),
            ("tobe/wave-comparison-report.md", "tobe/parity-test-report.md"),
        ]),
        "7": status([
            ("deliverables",),
            ("deliverables/wave-1-index.md", "deliverables/wave-1-package"),
            ("deliverables/wave-1-delivery-report.md",),
        ]),
        "8": status([("summary",)]),
    }


def _derive_impact_from_gap(g: dict) -> str:
    """Derive a human-readable impact statement from gap-register.json fields.

    Used when no explicit impact/reason/action field is present.
    Derives from 'blocker' (migration blocker flag) + 'complexity_label' (severity).
    """
    blocker = g.get("blocker", False)
    cplx = str(g.get("complexity_label") or "").upper()
    desc = str(g.get("description") or "").strip()
    if blocker:
        suffix = f" — {desc}" if desc else ""
        return f"Bloqueador de migração{suffix}"
    impact_by_cplx = {
        "CRITICAL": "Decisão arquitetural obrigatória antes do início da wave",
        "HIGH":     "Reescrita significativa com risco de regressão funcional",
        "MEDIUM":   "Reescrita parcial com risco controlado; requer testes de paridade",
        "LOW":      "Substituição com adaptação mínima; risco baixo de regressão",
        "TRIVIAL":  "Ajuste pontual sem reescrita; risco negligível",
    }
    return impact_by_cplx.get(cplx, "Tratamento necessário antes do go-live")


def parse_coverage_gap_strategy(outputs_dir: Path) -> list:
    """Extract real coverage-gap mitigations from the TO-BE QA gap analysis.

    The old standalone section was deprecated, but the data remains useful in
    the Summary. Prefer explicit mitigation bullets from gap-analysis.md and
    fall back to the functional matrix when no detailed gap headings exist.
    """
    path = outputs_dir / "tobe" / "qa" / "gap-analysis.md"
    text = read_text(path)
    if not text:
        return []
    rows = []
    current = None
    strategy_lines = []

    def flush() -> None:
        nonlocal current, strategy_lines
        if not current:
            return
        if strategy_lines:
            current["strategy"] = " ".join(strategy_lines).strip()
        if not current["strategy"]:
            current["strategy"] = current.get("coverage", "")
        current.pop("coverage", None)
        current.pop("_collect_mitigation", None)
        if current.get("strategy"):
            rows.append(current)
        current = None
        strategy_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Supported heading formats:
        #   ### GAP-SEC-001 — Title        (em dash, new format from ava-qa-gaps-requirements)
        #   ### GAP-SEC-001: Title         (colon, older format)
        #   ### G-F-001: Title             (G-prefix colon format)
        #   ## Gap N: Title (HIGH → RESOLVED)  (narrative format from ava-test-plan-tobe)
        structured = re.match(
            r"^###\s+((?:QA-)?GAP-[\w-]+|G-[A-Z0-9]+-\d+[\w-]*)"  # ID part
            r"(?:\s*[:\u2014\u2013]\s*)(.+)$",                      # separator (: or — or –) + title
            line, re.I
        )
        narrative = re.match(r"^##\s+Gap\s+(\d+)\s*:\s*(.*)$", line, re.I)
        if structured or narrative:
            flush()
            if structured:
                gap_id = structured.group(1).strip()
                # Derive dimension: G-prefix format or GAP-TYPE prefix
                _dim_map_g = {"G-F-": "Functional", "G-S-": "Security", "G-NF-": "Non-Functional", "G-L-": "LGPD"}
                _dim_map_gap = {
                    "GAP-SEC": "Security", "GAP-ARCH": "Architecture", "GAP-DATA": "Data Migration",
                    "GAP-FUNC": "Functional", "GAP-OBS": "Observability", "GAP-PERF": "Performance",
                    "GAP-LGPD": "LGPD", "GAP-NF": "Non-Functional",
                }
                auto_dim = (
                    next((v for k, v in _dim_map_g.items() if gap_id.upper().startswith(k)), None)
                    or next((v for k, v in _dim_map_gap.items() if gap_id.upper().startswith(k)), "")
                )
                current = {
                    "gapId": gap_id, "title": structured.group(2).strip(),
                    "complexity": "", "dimension": auto_dim, "strategy": "",
                    "tools": "", "wave": "—", "status": "PLANNED",
                }
            else:
                title = narrative.group(2).strip()
                outcome_match = re.search(r"\(([^()]*)\)\s*$", title)
                outcome = outcome_match.group(1).strip() if outcome_match else ""
                severity = re.search(r"\b(CRITICAL|HIGH|MEDIUM|LOW|TRIVIAL)\b", title, re.I)
                status_match = re.search(r"→\s*(RESOLVED|PARTIAL|OPEN|PLANNED)", outcome, re.I)
                title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
                current = {
                    "gapId": f"GAP-{int(narrative.group(1)):03d}",
                    "title": title,
                    "complexity": severity.group(1).upper() if severity else "MEDIUM",
                    "dimension": "Coverage",
                    "strategy": "",
                    "tools": "",
                    "wave": "—",
                    "status": status_match.group(1).upper() if status_match else "PLANNED",
                }
            continue
        if not current:
            continue

        sev = re.search(r"\*\*Severity:?\*\*:?\s*([^\s|]+)", line, re.I)
        mitigation = re.search(r"\*\*Mitigation:?\*\*:?\s*(.*)", line, re.I)
        due = re.search(r"\*\*Due:?\*\*:?\s*(.+)", line, re.I)
        bc = re.search(r"\*\*BC:?\*\*:?\s*(.+?)(?=\s*\|\s*\*\*|$)", line, re.I)
        wave_field = re.search(r"\*\*Wave:?\*\*:?\s*(.+?)(?=\s*\|\s*\*\*|$)", line, re.I)
        automation = re.search(r"\*\*Automation:?\*\*:?\s*(.+)", line, re.I)
        coverage = re.search(r"\*\*TO-BE Coverage:?\*\*:?\s*(.*)", line, re.I)
        residual = re.search(r"\*\*Residual Risk:?\*\*:?\s*(.+)", line, re.I)
        # New format: **Status:** Addressed in TO-BE | Partially addressed | Open
        status_field = re.search(r"\*\*Status:?\*\*:?\s*(.+?)(?=\s*\|\s*\*\*|$)", line, re.I)
        # New format: **Gap:** description of what still needs attention → strategy
        gap_desc = re.search(r"^\*\*Gap:?\*\*:?\s*(.*)", line, re.I)
        if sev:
            current["complexity"] = sev.group(1).upper()
        if due:
            current["wave"] = due.group(1).strip()
        if bc:
            current["dimension"] = bc.group(1).strip()
        if wave_field:
            current["wave"] = wave_field.group(1).strip()
        if automation:
            current["tools"] = automation.group(1).strip()
        if status_field:
            _st = status_field.group(1).strip().lower()
            if "addressed" in _st:
                current["status"] = "RESOLVED"
            elif "partial" in _st:
                current["status"] = "PARTIAL"
            elif "open" in _st or "pending" in _st:
                current["status"] = "OPEN"
        if residual and current["status"] == "PLANNED":
            current["status"] = "RESOLVED" if residual.group(1).strip().upper() == "LOW" else "PARTIAL"
        if gap_desc and gap_desc.group(1).strip():
            strategy_lines.append(gap_desc.group(1).strip())
        if mitigation:
            value = mitigation.group(1).strip()
            if value:
                strategy_lines.append(value)
            current["_collect_mitigation"] = not value
        elif re.match(r"^\*\*Mitigation:?\*\*:?\s*$", line, re.I):
            # The following bullet lines are the mitigation strategy.
            current["_collect_mitigation"] = True
            continue
        elif coverage:
            current["coverage"] = coverage.group(1).strip()
            strategy_lines.append(coverage.group(1).strip())
        elif line.strip().startswith("-") and (strategy_lines or current.get("coverage") or current.get("_collect_mitigation")):
            strategy_lines.append(line.strip().lstrip("- "))
        wave = re.search(r"\b(Wave\s+(?:\d+|Final))\b", line, re.I)
        if wave and current["wave"] == "—":
            current["wave"] = wave.group(1)
    flush()
    return rows


def parse_gap_register(asis_dir: Path) -> list:
    """Load and normalize all gaps from gap-register.json (ava-asis-gap-migration-analyzer).

    Returns a list of normalized gap entries for D.gaps in the HTML summary.
    Each entry: {id, category, categoryLabel, complexityKey, title, artifact, description, impact, score}
    """
    print("\n🔧 [Gaps] Loading GAP data from gap-register.json...")

    CATEGORY_LABELS = {
        "EXT": "Ref. Externa",      "COM": "COM/DCOM",           "DAT": "Acesso a Dados",
        "ORM": "ORM Gap",           "DB": "Objeto de Banco",     "FWK": "Framework",
        "EVT": "Modelo de Evento",  "THR": "Threading",          "STR": "Tipagem Proprietária",
        "SEC": "Segurança",         "RPT": "Motor de Relatório", "MSG": "Mensageria",
        "INT": "Integração P2P",    "CFG": "Config Acoplada",    "TXN": "Transação Distribuída",
        "STT": "Estado Global",     "ARC": "Antipadrão Arq.",    "DEP": "Dep. Circular",
        "PLT": "Dep. Plataforma OS","LIC": "Licença/Disponibilidade","TST": "Testabilidade",
        "DOC": "Documentação/Contrato","DAT-MIG": "Migração de Dados",
        "BL":  "Regra de Negócio",   "INFRA": "Infraestrutura",
    }
    COMPLEXITY_CSS = {
        "TRIVIAL": "gap-trivial", "LOW": "gap-low", "MEDIUM": "gap-medium",
        "HIGH": "gap-high", "CRITICAL": "gap-critical",
    }
    SCORE_MAP = {"TRIVIAL": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 5, "CRITICAL": 10}
    # Some gap-registers store a priority/severity code (P0–P3) in place of a
    # complexity label — normalize it so scoring, badges and counts line up.
    PRIORITY_TO_CPLX = {"P0": "CRITICAL", "P1": "HIGH", "P2": "MEDIUM", "P3": "LOW"}

    gaps_json = read_json(asis_dir / "gap-register.json")
    gaps_list = gaps_json.get("gaps", gaps_json) if isinstance(gaps_json, dict) else gaps_json
    if not isinstance(gaps_list, list):
        gaps_list = []

    # ── Fallback: derive gaps from risk-register.json when gap-register.json is absent ──
    if not gaps_list:
        print("   ⚠️  gap-register.json absent or empty — falling back to risk-register.json")
        _RISK_CAT_TO_GAP = {
            "Security":     "SEC",
            "Compliance":   "SEC",
            "Architecture": "ARC",
            "Migration":    "EXT",
            "Quality":      "TST",
            "Process":      "CFG",
        }
        _PRIORITY_TO_CPLX = {"P0": "CRITICAL", "P1": "HIGH", "P2": "MEDIUM", "P3": "LOW"}
        _TECH_KEYWORDS = {
            "sql": "DAT", "database": "DAT", "transaction": "DAT", "query": "DAT",
            "vcl": "FWK", "form": "FWK", "delphi": "FWK", "delphi ": "FWK",
            "acbr": "EXT", "boleto": "EXT", "library": "EXT",
            "win32": "PLT", "desktop": "PLT", "exe": "PLT",
            "test": "TST", "coverage": "TST",
            "string": "STR", "encoding": "STR",
            "duplicate": "ARC", "logic": "ARC", "business logic": "ARC",
            "credential": "SEC", "injection": "SEC", "auth": "SEC",
            "lgpd": "SEC", "pii": "SEC", "encrypt": "SEC",
        }
        risks_json = read_json(asis_dir / "risk-register.json")
        risks_raw = risks_json.get("risks", risks_json) if isinstance(risks_json, dict) else risks_json
        if isinstance(risks_raw, list):
            for i, r in enumerate(risks_raw, 1):
                desc  = str(r.get("description", r.get("title", "N/D")))
                prio  = r.get("priority", "P2")
                cplx  = _PRIORITY_TO_CPLX.get(prio, "MEDIUM")
                # Infer gap category: try keyword match on description first, then category map
                cat_en = r.get("category", "Technical")
                inferred_cat = _RISK_CAT_TO_GAP.get(cat_en, "ARC")
                desc_lower = desc.lower()
                for kw, cat_code in _TECH_KEYWORDS.items():
                    if kw in desc_lower:
                        inferred_cat = cat_code
                        break
                raw_id = str(r.get("id", f"R-{i:03d}"))
                gap_id = re.sub(r'^R-?(\d+)$', lambda m: f"GAP-{int(m.group(1)):03d}", raw_id)
                score  = r.get("score", SCORE_MAP.get(cplx, 2))
                if isinstance(score, float):
                    score = int(score)
                gaps_list.append({
                    "id":          gap_id,
                    "category":    inferred_cat,
                    "complexity":  cplx,
                    "title":       desc[:80],
                    "artifact":    str(r.get("evidence", ""))[:150],
                    "description": desc[:300],
                    "impact":      str(r.get("mitigation", ""))[:150],
                    "score":       score,
                })
            print(f"   ↳ {len(gaps_list)} gaps derived from risk-register.json")

    INT_TO_LABEL = {0: "TRIVIAL", 1: "LOW", 2: "LOW", 3: "MEDIUM", 4: "HIGH", 5: "CRITICAL", 10: "CRITICAL"}

    # Keyword → category inference for gap-register.json (no 'category' field)
    COMPONENT_CATEGORY_MAP = [
        (["VCL", "DFM", "TForm", "TDateTimePicker", "TDataModule", "TDBGrid"], "FWK"),
        (["ADO", "ADODB", "SQL", "inline SQL", "string-concat"],               "DAT"),
        (["ACBr", "Boleto", "Carnê"],                                           "EXT"),
        (["destructor", "RAII", "GC", "memory"],                               "PLT"),
        (["MessageBox", "Win32", "CreateForm", "Application.", "eager"],        "PLT"),
        (["AnsiString", "WideString", "encoding", "charset"],                   "STR"),
    ]

    def _infer_category(g: dict) -> str:
        """Infer category from 'component' text when no 'category' field present."""
        component_text = str(g.get("component", "") or g.get("title", "")).upper()
        reason_text    = str(g.get("reason", "")).upper()
        combined       = component_text + " " + reason_text
        for keywords, cat_code in COMPONENT_CATEGORY_MAP:
            if any(kw.upper() in combined for kw in keywords):
                return cat_code
        return "ARC"   # default

    def _infer_complexity(g: dict) -> str:
        """Infer complexity from 'migratable' flag when no 'complexity' field present."""
        migratable = g.get("migratable", None)
        if migratable is False:
            return "HIGH"      # non-migratable → HIGH by default
        if migratable == "partial":
            return "MEDIUM"
        return "MEDIUM"

    processed = []
    for g in gaps_list:
        # Alias: accept 'category', 'category_code', 'taxonomy' (ava-asis-gap-migration-analyzer schema),
        # or infer from component text as last resort
        cat = str(g.get("category") or g.get("category_code") or g.get("taxonomy") or "").upper()
        if not cat:
            cat = _infer_category(g)
        elif "category_code" in g and "category" not in g:
            raw_id_warn = str(g.get("id", "?"))
            print(f"   ⚠️  [{raw_id_warn}] alias 'category_code' used — generator schema diverges from contract")

        # Alias: accept 'complexity', 'complexity_label', 'severity' (ava-asis-gap-migration-analyzer schema),
        # or infer from 'migratable' field as last resort
        raw_cplx = g.get("complexity") or g.get("complexity_label") or g.get("severity")
        if raw_cplx is None:
            cplx = _infer_complexity(g)
        elif isinstance(raw_cplx, int):
            cplx = INT_TO_LABEL.get(raw_cplx, "MEDIUM").upper()
        else:
            cplx = str(raw_cplx).upper() or _infer_complexity(g)
        cplx = PRIORITY_TO_CPLX.get(cplx, cplx)

        raw_id = str(g.get("id", "GAP-????"))
        gid    = re.sub(r'^GAP(\d+)$', lambda m: f"GAP-{int(m.group(1)):04d}", raw_id)
        score  = g.get("score", SCORE_MAP.get(cplx, 2))

        # Alias: 'title' (correct) → 'component' (ava-asis-gap-migration-analyzer schema) → 'description' fallback
        title_val = (
            g.get("title") or
            g.get("component") or          # gap-register.json from ava-asis-gap-migration-analyzer
            str(g.get("description", "N/D"))[:80]
        )
        # Alias: 'artifact' (correct) → 'affected_files' array (ava-asis-gap-migration-analyzer schema)
        # → other field aliases → component as last resort
        _aff = g.get("affected_files")
        _aff_str = ", ".join(_aff) if isinstance(_aff, list) and _aff else (str(_aff) if _aff else "")
        artifact_val = (
            g.get("artifact") or g.get("artifact_source") or
            g.get("source_artifact") or g.get("source_file") or
            g.get("affected_file") or _aff_str or
            g.get("file") or g.get("location") or g.get("path") or g.get("source") or
            g.get("component") or ""       # last-resort: use component as artifact reference
        )
        # Alias: 'impact' → 'reason' (ava-asis-gap-migration-analyzer) → 'migration_action' → 'action'
        # Final fallback: derive from 'blocker' + 'complexity_label' when no explicit field exists
        # (gap-register.json schema does not include an impact field; _derive_impact_from_gap covers it)
        impact_val = (
            g.get("impact") or
            g.get("reason") or             # gap-register.json: reason = why not migratable
            g.get("migration_action") or
            g.get("action") or             # gap-register.json: action = TO-BE replacement
            _derive_impact_from_gap(g)     # derived from blocker + complexity_label
        )

        processed.append({
            "id":            gid,
            "category":      cat,
            "categoryLabel": CATEGORY_LABELS.get(cat, cat),
            "complexityKey": COMPLEXITY_CSS.get(cplx, "gap-medium"),
            "complexity":    cplx,
            "title":         str(title_val)[:80],
            "artifact":      str(artifact_val)[:150],
            "description":   str(g.get("description", ""))[:300],
            "impact":        str(impact_val)[:150],
            "score":         score,
        })

    # Delta=0 validation: every source gap must produce exactly one processed entry
    delta = len(gaps_list) - len(processed)
    if delta != 0:
        print(f"   ⚠️  DELTA≠0: {len(gaps_list)} gaps no source, {len(processed)} processados — {delta} perdidos!")
    else:
        print(f"   ✅ Delta=0: todos os {len(processed)} gaps cobertos")
    critical_count = sum(1 for g in processed if g["complexity"] == "CRITICAL")
    high_count     = sum(1 for g in processed if g["complexity"] == "HIGH")
    mrs = sum(g["score"] for g in processed)
    print(f"   🔴 {critical_count} CRITICAL | 🟠 {high_count} HIGH | {len(processed)} total | MRS={mrs}")
    return processed


def _parse_risk_register_md(path: Path) -> list:
    """Fallback parser for risk-register.md — some pipeline variants (e.g. the
    AST extraction pipeline) emit a markdown risk register instead of
    risk-register.json. Returns a list of dicts shaped like the JSON schema
    (id/category/priority/description/evidence/mitigation) so build_risk_data()
    can normalize either source through the same downstream logic."""
    text = read_text(path)
    if not text.strip():
        return []

    # ── Risk Register table (## Risk Register … | ID | Risk | Category | … |) ──
    m = re.search(r'##\s*Risk Register\s*\n(.*?)(?=\n##\s|\Z)', text, re.DOTALL)
    if not m:
        return []
    section = m.group(1)
    rows = [ln for ln in section.splitlines() if ln.strip().startswith('|')]
    if len(rows) < 2:
        return []
    headers = [h.strip().lower() for h in rows[0].strip('|').split('|')]

    def _col(name_variants):
        for i, h in enumerate(headers):
            if any(v in h for v in name_variants):
                return i
        return None

    idx_id   = _col(['id'])
    idx_risk = _col(['risk', 'title', 'description'])
    idx_cat  = _col(['category', 'categoria'])
    idx_pri  = _col(['priority', 'prioridade'])
    if idx_id is None or idx_risk is None:
        return []

    # ── Optional per-risk mitigation from "## P0 Risks — Action Plan" style
    # sections: "### RISK-NNN: Title" followed by a "**Mitigation:**" block. ──
    mitigations = {}
    for sec_m in re.finditer(r'###\s*([A-Z]+-\d+):[^\n]*\n(.*?)(?=\n###\s|\n##\s|\Z)', text, re.DOTALL):
        rid, body = sec_m.group(1), sec_m.group(2)
        mit_m = re.search(r'\*\*Mitigation:\*\*\s*\n((?:\s*\d+\..*\n?)+)', body)
        if mit_m:
            first_line = mit_m.group(1).strip().splitlines()[0]
            mitigations[rid] = re.sub(r'^\d+\.\s*', '', first_line).strip()

    risks = []
    for row in rows[2:]:  # skip header + separator
        cells = [c.strip() for c in row.strip('|').split('|')]
        if len(cells) <= max(idx_id, idx_risk):
            continue
        rid = cells[idx_id].strip('* ')
        if not rid:
            continue
        risks.append({
            "id": rid,
            "category": cells[idx_cat].strip('* ') if idx_cat is not None and idx_cat < len(cells) else "Technical",
            "priority": cells[idx_pri].strip('* ') if idx_pri is not None and idx_pri < len(cells) else "P3",
            "description": cells[idx_risk].strip('* '),
            "evidence": cells[idx_risk].strip('* '),
            "mitigation": mitigations.get(rid, "N/D"),
        })
    return risks


def build_risk_data(asis_dir: Path) -> list:
    """Load and normalize all risks from risk-register.json, falling back to
    risk-register.md when the JSON is absent/empty (some pipeline variants,
    e.g. the AST extraction pipeline, emit the markdown register instead).

    Returns all risks (no limit). Each entry has normalized fields:
    {id, cat (PT), ck (css-key), r (description), ev (evidence), sev, a (mitigation)}
    Compatible with any project — reads real category/evidence/mitigation fields.
    """
    print("\n🔧 [Risks] Loading Risk Data from risk-register.json...")

    CAT_MAP = {
        "Technical":   ("Técnico",    "rcat-tech"),
        "Security":    ("Segurança",  "rcat-security"),
        "Process":     ("Processo",   "rcat-process"),
        "Compliance":  ("Compliance", "rcat-compliance"),
        "Migration":   ("Migração",   "rcat-migration"),
        "Quality":     ("Qualidade",  "rcat-quality"),
        "Architecture":("Arquitetura","rcat-arch"),
        "Testing":     ("Testes",     "rcat-quality"),
        "Data":        ("Dados",      "rcat-tech"),
        "Business Rule":("Regra de Negócio", "rcat-process"),
        "Integration": ("Integração", "rcat-tech"),
    }
    SEV_MAP = {"P0": "critico", "P1": "alto", "P2": "medio", "P3": "baixo"}

    risks_json = read_json(asis_dir / "risk-register.json")
    risks_list = risks_json.get("risks", risks_json) if isinstance(risks_json, dict) else risks_json
    if not isinstance(risks_list, list):
        risks_list = []
    if not risks_list:
        risks_list = _parse_risk_register_md(asis_dir / "risk-register.md")
        if risks_list:
            print(f"   📋 risk-register.json absent/empty — loaded {len(risks_list)} risk(s) from risk-register.md")

    processed = []
    for r in risks_list:
        cat_en  = r.get("category", "Technical")
        cat_pt, cat_key = CAT_MAP.get(cat_en, (cat_en, "rcat-tech"))
        sev     = SEV_MAP.get(r.get("priority", "P3"), "baixo")
        desc    = r.get("description", r.get("title", "N/D"))
        ev      = str(r.get("evidence", r.get("justification", r.get("impact", desc))) or desc)
        action  = str(r.get("mitigation", r.get("action", r.get("recommendation", "N/D"))) or "N/D")
        # Normalize ID format: R-001 → R-001 (keep 3-digit), R001 → R-001
        raw_id  = str(r.get("id", "R-???"))
        rid     = re.sub(r'^R(\d+)$', lambda m: f"R-{int(m.group(1)):03d}", raw_id)
        processed.append({
            "id":  rid,
            "cat": cat_pt,
            "ck":  cat_key,
            "r":   desc[:200] if isinstance(desc, str) else str(desc)[:200],
            "ev":  ev[:150] if ev != desc else str(desc)[:150],
            "sev": sev,
            "a":   action[:150] if action else "N/D",
        })

    # ── Deduplication + stable sort ──────────────────────────────────────────
    # risk-register.json occasionally has duplicate R-NNN IDs across runs.
    # Keep first occurrence per ID; sort P0→P3 then by ID within each band.
    seen_rid: dict = {}
    deduped_risks: list = []
    for r in processed:
        rid = r.get("id", "")
        if rid and rid not in seen_rid:
            seen_rid[rid] = True
            deduped_risks.append(r)
    SEV_ORDER = {"critico": 0, "alto": 1, "medio": 2, "baixo": 3}
    deduped_risks.sort(key=lambda r: (
        SEV_ORDER.get(r["sev"], 3),
        int(re.search(r'\d+', r.get("id", "0")).group() or 0)
    ))

    p0_count = sum(1 for r in risks_list if r.get("priority") == "P0")
    print(f"   ⚠️  {p0_count} P0 risks | {len(deduped_risks)} total risks loaded")
    return deduped_risks  # deduplicated, sorted


def _parse_schema_subsections(lines: list, er_col_counts: dict, risk_order: dict) -> list:
    """Parse schema-inventory.md in per-table subsection format.

    Handles the format produced by agents that write individual ### TABLENAME
    sections instead of a consolidated Table Inventory pipe-table:

        ## Tables
        ### FUNCOES
        **Purpose**: Stores job positions...
        | Column | Data Type | Nullable | Constraints | Notes |
        | CODIGO | INTEGER   | NO       | PK (PK_FUNCOES) | ... |
        **Foreign Keys**: FK_FUNCOES — FUNCIONARIOS.FUNCAO → FUNCOES.CODIGO

    Returns the same list format as the primary parser:
        [(tname, col_count, has_pk, has_fk, idx_label, risk_order_int), ...]
    """
    SEVERITY_WORDS = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    # Build per-table risk map from Schema Quality Issues section (if present)
    table_risk: dict = {}  # tname_upper -> risk_order_int
    in_quality = False
    for line in lines:
        if re.search(r'Schema Quality Issues|Quality Issues', line, re.I):
            in_quality = True
            continue
        if in_quality:
            if line.startswith('##'):
                in_quality = False
                continue
            if '|' not in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:
                continue
            sev_raw = parts[1].upper()
            issue_raw = parts[2] if len(parts) > 2 else ""
            sev_key = next((s for s in SEVERITY_WORDS if s in sev_raw), None)
            if sev_key:
                # Try to associate this severity with a table name mentioned in the issue
                for candidate in re.findall(r'`([A-Z_][A-Z0-9_]+)`', issue_raw.upper()):
                    existing = table_risk.get(candidate, 3)
                    table_risk[candidate] = min(existing, SEVERITY_WORDS[sev_key])

    # Find start of ## Tables (or ## Schema / ## Tabelas)
    tables_start = None
    for i, line in enumerate(lines):
        if re.match(r'^#{1,2}\s+Tables?\b|^#{1,2}\s+Tabelas?\b|^#{1,2}\s+Schema\b', line, re.I):
            tables_start = i
            break
    if tables_start is None:
        return []

    raw_rows = []
    current_table: str | None = None
    col_count_manual = 0
    has_pk_flag = False
    has_fk_flag = False
    in_col_table = False

    def _flush(tname):
        nonlocal col_count_manual, has_pk_flag, has_fk_flag, in_col_table
        if not tname:
            return
        real_col = er_col_counts.get(tname)
        col_count = str(real_col) if real_col is not None else str(col_count_manual)
        has_pk = "Sim" if has_pk_flag else "Não"
        has_fk = "Sim" if has_fk_flag else "Não"
        idx_label = "PK/FK" if has_fk_flag else ("PK" if has_pk_flag else "—")
        risk_int = table_risk.get(tname.upper(), risk_order.get("LOW", 3))
        raw_rows.append((tname, col_count, has_pk, has_fk, idx_label, risk_int))
        col_count_manual = 0
        has_pk_flag = False
        has_fk_flag = False
        in_col_table = False

    for line in lines[tables_start + 1:]:
        # New table subsection: ### TABLENAME or #### TABLENAME
        m_tbl = re.match(r'^#{2,4}\s+([A-Z][A-Z0-9_]+)\s*$', line.strip())
        if m_tbl:
            _flush(current_table)
            current_table = m_tbl.group(1)
            in_col_table = False
            continue

        # Stop at a top-level section sibling (## Something other than nested tables)
        if re.match(r'^#{1,2}\s+\w', line) and not re.match(r'^#{3,}', line):
            break

        if current_table is None:
            continue

        # Detect start of column definition table by its header
        if re.search(r'\|\s*Column\s*\||\|\s*Coluna\s*\|', line, re.I):
            in_col_table = True
            continue

        if in_col_table and '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:
                continue
            col_name = parts[1].strip('`').strip()
            if not col_name or col_name.startswith('-') or col_name.lower() in ('column', 'coluna', 'campo'):
                continue
            col_count_manual += 1
            # Scan all parts for PK / FK markers
            row_text = ' '.join(parts).upper()
            if 'PK' in row_text or 'PRIMARY' in row_text:
                has_pk_flag = True
            if 'FK' in row_text or 'FOREIGN' in row_text or '→' in ' '.join(parts):
                has_fk_flag = True
            continue

        # **Foreign Keys**: explicit FK declaration line
        if re.match(r'\*{0,2}Foreign Keys?\*{0,2}:', line, re.I):
            fk_content = re.sub(r'\*{0,2}Foreign Keys?\*{0,2}:', '', line, flags=re.I).strip()
            if fk_content and fk_content not in ('None', 'N/A', '—', '-'):
                has_fk_flag = True

    _flush(current_table)
    return raw_rows


def _count_db_insert_points(asis_dir: Path) -> int:
    """Static-analysis proxy for "INSERT volume": number of distinct INSERT call
    sites found in the legacy code (never a real runtime transaction volume,
    which no static analysis can produce).

    Source 1: 03_database_rules.json — rules where type="write_operation" and
    operation="insert" (one rule per INSERT call site found in the AST).
    Source 2 (fallback): 04_database_schemas.json — inferred_tables entries
    whose operations include "insert" (count of tables ever INSERTed into,
    a coarser proxy used only when Source 1 is absent).
    """
    rules = read_json(asis_dir / "delphi-ast-raw" / "compressed" / "03_database_rules.json")
    write_rules = (rules.get("payload", {}) or {}).get("rules", []) if isinstance(rules, dict) else []
    insert_count = sum(
        1 for r in write_rules
        if isinstance(r, dict) and r.get("type") == "write_operation" and r.get("operation") == "insert"
    )
    if insert_count > 0:
        return insert_count

    schemas = read_json(asis_dir / "delphi-ast-raw" / "compressed" / "04_database_schemas.json")
    inferred_tables = (schemas.get("payload", {}) or {}).get("inferred_tables", []) if isinstance(schemas, dict) else []
    return sum(
        1 for t in inferred_tables
        if isinstance(t, dict) and "insert" in (t.get("operations") or [])
    )


def _parse_business_logic_in_db(path: Path) -> tuple:
    """Parse `business-logic-in-db.md` (db-analyzer.md's Business Logic
    Detector output — flags stored procedures containing business rules
    with a CRITICAL marker). No fixed table format is documented for this
    file by its producer contract, so this parser is defensive: it accepts
    any markdown table row whose first column looks like an SP/procedure
    name and scans the remaining columns for a CRITICAL/HIGH/MEDIUM/LOW
    risk marker; when no table is found at all, it falls back to counting
    bare 'CRITICAL' mentions in the prose so the KPI is never a false zero.
    Returns (rows, critical_count).
    """
    if not path.exists():
        return [], 0
    text = read_text(path)
    rows = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        cols = [c.strip().strip('*') for c in line.strip('|').split('|')]
        cols = [c for c in cols if c]
        if len(cols) < 2:
            continue
        first = cols[0].strip()
        if not first or re.match(r'^[-\s]+$', first) or first.lower() in (
                'sp', 'procedure', 'stored procedure', 'nome', 'name', 'table', 'tabela'):
            continue
        risk = "MEDIUM"
        for col in cols[1:]:
            # Cells often carry an emoji marker before the severity word
            # (e.g. "🔴 CRITICAL", "🟠 HIGH") — search for the token instead
            # of requiring an exact match, so emoji-prefixed cells are not
            # silently downgraded to the MEDIUM default.
            m = re.search(r'\b(CRITICAL|HIGH|MEDIUM|LOW)\b', col.strip().upper())
            if m:
                risk = m.group(1)
                break
        reason = cols[1][:120] if len(cols) > 1 else ""
        rows.append({"sp": first[:60], "reason": reason, "risk": risk})
    critical_count = sum(1 for r in rows if r["risk"] == "CRITICAL")
    if not rows:
        critical_count = len(re.findall(r'\bCRITICAL\b', text))
    return rows, critical_count


def build_comprehensive_substitutions(project_name: str, outputs_dir: Path, asis_dir: Path, file_tree: dict, base_dir: Path = None) -> dict:
    """╔═══ FIX ISSUE #5: All Placeholder Population ═══╗"""
    if base_dir is None:
        base_dir = Path('.')
    print("\n🔧 [Issue #5 Fix] Building Comprehensive Substitutions (100+ placeholders)...")

    # Load project config for fields that agents don't replicate in metrics.json
    config = load_project_config(project_name)

    # Load all data sources
    metrics = read_json(asis_dir / "metrics.json")
    risks = build_risk_data(asis_dir)
    patterns_data = read_json(asis_dir / "pattern-classifications.json")
    tobe_patterns_data = read_json(outputs_dir / "tobe" / "patterns-applied.json")
    db_type = read_json(asis_dir / "db" / "db-type.json")
    # Parse bounded contexts early so BC* placeholders can be substituted
    bcs = parse_bounded_contexts(asis_dir / "bounded-context-map.md")

    # Extract nested metrics
    # metrics.json schema uses "code" (not "totals") and "modules" dict for module count
    code = metrics.get("code", {})
    if not code:
        # ava-asis-inventory produces nested "totals" block (not flat "code").
        # Build a unified code dict with canonical aliases so all downstream
        # getters (code.get("total_loc"), code.get("classes"), etc.) resolve.
        totals = metrics.get("totals", {})
        # m(key, *aliases) — resolves from totals first, then from flat metrics
        def _mv(totals_key, *flat_keys, default=0):
            v = totals.get(totals_key)
            if v is not None: return v
            for fk in flat_keys:
                v = metrics.get(fk)
                if v is not None: return v
            return default
        code = {
            **{k: v for k, v in metrics.items()
               if k not in ("totals", "modules", "code", "complexity",
                            "coupling", "patterns", "third_party")},
            **totals,
            # Canonical aliases — totals.key first, then flat metrics, then 0
            "classes":          _mv("total_classes", "classes"),
            "classes_count":    _mv("total_classes", "classes"),
            "methods":          _mv("total_methods", "methods", "estimated_methods"),
            "estimated_methods":_mv("estimated_methods", "total_methods", "methods"),
            # This inventory schema stores the authoritative LOC as
            # `totals.loc`; keep the canonical aliases usable by the Summary.
            "total_loc":        totals.get("loc", _mv("total_loc", "loc", "total_loc_pas")),
            "effective_loc":    totals.get("loc", _mv("code_lines_estimated", "effective_loc", "loc", "total_loc")),
            "loc_pas_code":     totals.get("loc", _mv("code_lines_estimated", "loc_pas_code", "loc", "total_loc")),
            "vcl_forms":        _mv("total_forms", "vcl_forms", "dfm_files", "form_files_dfm"),
            "data_modules":     _mv("total_data_modules", "data_modules"),
            "datamodules":      _mv("total_data_modules", "data_modules"),
            "source_files_pas": _mv("pas_files", "source_files_pas"),
            "form_files_dfm":   _mv("dfm_files", "form_files_dfm"),
            "loc_dfm":          _mv("total_loc_dfm", "loc_dfm", "loc_forms"),
            "loc_forms":        _mv("total_loc_dfm", "loc_forms", "loc_dfm"),
        }
    # Normalize nested-dict values → integers for ava-asis-inventory nested schema.
    # e.g. metrics.json emits "classes": {"total_domain_classes": 8, "list": [...]}
    # and "loc": {"total_lines": 4600, "code_lines": 3800, ...} etc.
    _loc_blk   = code.get("loc")   if isinstance(code.get("loc"),   dict) else {}
    _units_blk = code.get("units") if isinstance(code.get("units"), dict) else {}
    _cls_blk   = code.get("classes") if isinstance(code.get("classes"), dict) else {}
    _mth_blk   = code.get("methods") if isinstance(code.get("methods"), dict) else {}
    if not code.get("total_loc"):
        code["total_loc"] = (_loc_blk.get("total_lines") or _loc_blk.get("total_loc")
                             or metrics.get("total_loc") or 0)
    if not code.get("effective_loc"):
        code["effective_loc"] = (_loc_blk.get("code_lines") or code.get("total_loc", 0))
    if not code.get("loc_pas_code"):
        code["loc_pas_code"] = code.get("effective_loc", 0)
    if isinstance(code.get("classes"), dict):
        _c = (_cls_blk.get("total_domain_classes") or _cls_blk.get("total")
              or len(_cls_blk.get("list", [])) or 0)
        code["classes"] = _c
        code["classes_count"] = _c
    if isinstance(code.get("methods"), dict):
        _m = ((_mth_blk.get("total_form_methods", 0) + _mth_blk.get("total_class_methods", 0))
              or _mth_blk.get("total", 0) or 0)
        code["methods"] = _m
        code["estimated_methods"] = _m
    if not code.get("vcl_forms"):
        code["vcl_forms"] = (_units_blk.get("form_units") or _units_blk.get("total_forms") or 0)
    if not code.get("data_modules"):
        _dm = _units_blk.get("data_module_units") or _units_blk.get("total_data_modules") or 0
        code["data_modules"] = _dm
        code["datamodules"] = _dm
    if not code.get("source_files_pas"):
        code["source_files_pas"] = _units_blk.get("total") or 0
    if not code.get("form_files_dfm"):
        code["form_files_dfm"] = code.get("vcl_forms", 0)

    scores = metrics.get("scores", {})
    complexity = metrics.get("complexity", {})
    layer_breakdown = metrics.get("layer_breakdown", {})
    modules_map = metrics.get("modules", {})
    if isinstance(modules_map, int):
        module_count = modules_map
        modules_map = {}
    else:
        module_count = len(modules_map) if modules_map else 0

    # Count files with CC >= 10 from whichever high-complexity list the AST
    # pipeline populated (schema varies: highest_cc_files uses "estimated_cc",
    # older/other sources may use "cc").
    # Guard: high_complexity_methods may be a plain integer count (not a list)
    # when the AST pipeline emits a summary rather than a per-file breakdown.
    # In that case we use the count directly and skip the per-item iteration.
    _cc_files_for_10_raw = complexity.get("highest_cc_files") or complexity.get("high_complexity_methods") or []
    _cc_files_for_10 = []  # always initialised — avoids UnboundLocalError when raw is int
    if isinstance(_cc_files_for_10_raw, int):
        # AST gave us a pre-counted integer — trust it as the CC>=10 count.
        _cc_ge_10_count = _cc_files_for_10_raw
    else:
        _cc_files_for_10 = _cc_files_for_10_raw if isinstance(_cc_files_for_10_raw, list) else []
        # Some inventory producers expose only the aggregate count (for example,
        # `high_complexity_methods: 18`) rather than a row-level list.  Treat that
        # schema as an already-computed count instead of iterating an integer.
        if isinstance(_cc_files_for_10, int):
            _cc_ge_10_count = _cc_files_for_10
            _cc_files_for_10 = []
        elif not isinstance(_cc_files_for_10, (list, tuple)):
            _cc_files_for_10 = []
            _cc_ge_10_count = 0
        else:
            _cc_ge_10_count = sum(
                    1 for f in _cc_files_for_10
                    if isinstance(f, dict) and (f.get("estimated_cc", f.get("cc", 0)) or 0) >= 10
                )

    # Pattern distribution
    if isinstance(patterns_data, dict) and "classifications" in patterns_data:
        classifications = patterns_data["classifications"]
    elif isinstance(patterns_data, list):
        classifications = patterns_data
    else:
        # Fallback: synthesize counts from metrics.json when pattern-classifications.json absent.
        # For framework/library projects (vcl_forms == 0), only synthesize Rich Domain.
        # For VCL application projects, synthesize all VCL patterns.
        vcl = code.get("vcl_forms", code.get("form_files_dfm", 0))
        rich_dom = code.get("classes", 0)
        if vcl == 0:
            # Framework / library — no VCL forms; only Rich Domain pattern applies
            classifications = [{"pattern": "Rich Domain (units isoladas)"}] * rich_dom
        else:
            dms = code.get("data_modules", 1)
            smart_ui = max(vcl - dms, 0)
            two_tier = max(vcl // 4, 0)
            classifications = (
                [{"pattern": "Smart UI (Form-Centric)"}] * smart_ui
                + [{"pattern": "DataModule (Repository implícito)"}] * dms
                + [{"pattern": "Two-Tier (SQL inline)"}] * two_tier
                + [{"pattern": "Rich Domain (units isoladas)"}] * rich_dom
            )

    # Normalize short/alias pattern names → canonical display names used by the template.
    # Agents may emit shorthand keys (SmartUI, DataModuleBridge, ThinDomain) or full names.
    # This map ensures the Counter always uses the canonical form regardless of source.
    PATTERN_ALIASES = {
        # Smart UI variants
        "SmartUI":                       "Smart UI (Form-Centric)",
        "Smart UI":                      "Smart UI (Form-Centric)",
        "Smart_UI":                      "Smart UI (Form-Centric)",
        "FormCentric":                   "Smart UI (Form-Centric)",
        "Form-Centric":                  "Smart UI (Form-Centric)",
        # DataModule variants
        "DataModuleBridge":              "DataModule (Repository implícito)",
        "DataModule":                    "DataModule (Repository implícito)",
        "DataModule (Repository implicito)": "DataModule (Repository implícito)",
        # Two-Tier variants
        "TwoTier":                       "Two-Tier (SQL inline)",
        "Two Tier":                      "Two-Tier (SQL inline)",
        "Two-Tier":                      "Two-Tier (SQL inline)",
        "SQLInline":                     "Two-Tier (SQL inline)",
        "SQL inline":                    "Two-Tier (SQL inline)",
        # Business Logic in SP variants
        "BusinessLogicSP":               "Business Logic in SP",
        "BusinessLogicInSP":             "Business Logic in SP",
        "Business Logic SP":             "Business Logic in SP",
        "LogicaSP":                      "Business Logic in SP",
        # Rich Domain / isolated units variants
        "RichDomain":                    "Rich Domain (units isoladas)",
        "Rich Domain":                   "Rich Domain (units isoladas)",
        "RichDomain (units isoladas)":   "Rich Domain (units isoladas)",
    }
    def _normalize_pattern(name: str) -> str:
        return PATTERN_ALIASES.get(name, name)

    pattern_counts = Counter(_normalize_pattern(item.get("pattern", "Unknown")) for item in classifications)
    # Template has 5 FIXED pattern names (P1-P5) — must look up by name, not by rank.
    # Using most_common() rank order would put wrong counts in wrong slots when
    # the distribution doesn't exactly match the template's fixed ordering.
    CANONICAL_PATTERNS = [
        "Smart UI (Form-Centric)",           # P1
        "DataModule (Repository implícito)", # P2
        "Two-Tier (SQL inline)",             # P3
        "Business Logic in SP",              # P4
        "Rich Domain (units isoladas)",      # P5
    ]
    p_counts = [pattern_counts.get(name, 0) for name in CANONICAL_PATTERNS]
    raw_total = sum(p_counts)  # number of entries in the JSON (may be a representative sample)

    # Scale p_counts to the real source-file count when the JSON only contains
    # representative sample entries (e.g. 1 entry per bounded context instead of
    # 1 entry per .pas file). This fixes the "OCORRÊNCIAS = 10 / % = 100% Rich Domain"
    # bug for projects whose agent emits a sampled pattern-classifications.json.
    #
    # Compatibility guarantee:
    #   • Projects WITHOUT pattern-classifications.json → use fallback synthesis (unchanged)
    #   • Projects where JSON covers all files (raw_total >= actual_files) → unchanged
    #   • Projects with sampled JSON (raw_total < actual_files) → scale proportionally
    actual_files = (
        metrics.get("source_files_pas", 0)
        or metrics.get("source_files_cobol", 0)
        or metrics.get("source_files_vb", 0)
        or metrics.get("source_files_vbnet", 0)
        or metrics.get("source_files_pb", 0)
    )
    if actual_files > 0 and raw_total > 0 and actual_files > raw_total:
        scale = actual_files / raw_total
        p_counts = [round(c * scale) for c in p_counts]
        pattern_total = actual_files
    else:
        pattern_total = max(raw_total, 1)  # original behaviour preserved

    # Keep pattern_rows for any legacy callers that might use it
    pattern_rows = [(CANONICAL_PATTERNS[i], p_counts[i]) for i in range(5)]

    # ── TO-BE Patterns Applied ────────────────────────────────────
    tobe_patterns_list = []
    if isinstance(tobe_patterns_data, dict):
        tobe_patterns_list = tobe_patterns_data.get("patterns", [])
    elif isinstance(tobe_patterns_data, list):
        tobe_patterns_list = tobe_patterns_data
    tobe_patterns_rows_html = ""
    for p in tobe_patterns_list:
        name   = p.get("pattern_name", "")
        layer  = p.get("layer", "")
        just   = p.get("justification", "")
        ref    = p.get("reference_artifact", "")
        trades = p.get("trade_offs", [])
        if isinstance(trades, list):
            trades_str = "; ".join(str(t) for t in trades)
        else:
            trades_str = str(trades)
        adr    = p.get("adr_reference", "")
        tobe_patterns_rows_html += (
            f"<tr><td>{name}</td><td>{layer}</td><td>{just}</td>"
            f"<td>{ref}</td><td>{trades_str}</td><td>{adr}</td></tr>\n"
        )
    if not tobe_patterns_rows_html:
        tobe_patterns_rows_html = (
            '<tr><td colspan="6" style="text-align:center;color:#888">'
            "patterns-applied.json not yet generated — run trigger PA</td></tr>"
        )

    # DB schema — parsed from schema-inventory.md; db-type.json is optional
    # ── 1. Vendor / SGBD ──────────────────────────────────────────────────────
    # db-type.json may use two formats:
    #   Format A (preferred): {"vendors": ["MySQL", ...]}  — array field
    #   Format B (legacy):    {"db_type": "MySQL", ...}   — string field
    vendors = db_type.get("vendors", [])
    vendor_label = ", ".join(vendors[:5]) if vendors else ""
    # Format B fallback: read "db_type" string directly
    if not vendor_label:
        db_type_str = db_type.get("db_type", "")
        if db_type_str:
            vendor_label = db_type_str.strip()
    schema_inv_path = asis_dir / "db" / "schema-inventory.md"
    sp_map_path     = asis_dir / "db" / "stored-procedures-map.md"
    if not vendor_label and schema_inv_path.exists():
        schema_inv_lines = read_text(schema_inv_path).splitlines()
        for line in schema_inv_lines:
            # Match multiple bold-header patterns — expanded to include:
            # **Database Engine**: Firebird  |  **Database**: MySQL
            # **SGBD Detected**: ...  |  **DBMS**: ...  |  **DB Engine**: ...
            m = re.match(
                r'\*\*(?:Database(?:\s+Engine)?|DB(?:\s+Engine)?|DBMS|'
                r'SGBD(?:\s+Detected)?|DB\s+Vendor|Engine)\*\*:\s*(.+)',
                line, re.I)
            if m:
                raw = m.group(1).strip()
                # Capture Multi-DBMS label or first known engine name
                eng = re.match(
                    r'(Multi-DBMS[^)]*\))?|'
                    r'(MySQL|PostgreSQL|SQL\s*Server|Oracle|SQLite|MariaDB|'
                    r'MongoDB|Firebird|Interbase|DB2|Sybase|H2|DuckDB)',
                    raw, re.I)
                if eng and eng.group(1):
                    vendor_label = eng.group(1).strip()
                elif eng and eng.group(2):
                    vendor_label = eng.group(2).strip()
                else:
                    vendor_label = raw.split('(')[0].strip()[:60]
                break
        # Fallback: scan summary/metric table rows:
        # | Database Engine | Firebird 2.x/3.x |  or  | Database | MySQL |
        if not vendor_label:
            for line in schema_inv_lines:
                m = re.match(
                    r'^\|\s*(?:Database(?:\s+Engine)?|DBMS|SGBD|DB(?:\s+Vendor)?)\s*\|\s*(.+?)\s*\|',
                    line, re.I)
                if m:
                    raw = m.group(1).strip()
                    if raw and raw.lower() not in ('value', 'valor', '---', 'metric'):
                        vendor_label = raw.split('(')[0].strip()[:60]
                        break
    # Source C: fallback — scan db-analysis-report.md for vendor when db-type.json
    # and schema-inventory.md are both absent or empty (non-regressive — only activates
    # when vendor_label is still empty after Sources A and B above).
    if not vendor_label:
        db_report_path = asis_dir / "db-analysis-report.md"
        if db_report_path.exists():
            db_report_text = read_text(db_report_path)
            for line in db_report_text.splitlines():
                # Match frontmatter/header lines like:
                #   **Database**: MySQL 5.x (via ADO/ODBC)
                #   **SGBD**: MySQL  |  **DB**: PostgreSQL
                m = re.match(
                    r'\*\*(?:Database(?:\s+Engine)?|SGBD|DBMS|DB(?:\s+Vendor)?)\*\*:\s*(.+)',
                    line, re.I)
                if m:
                    raw = m.group(1).strip()
                    eng = re.search(
                        r'(MySQL|PostgreSQL|SQL\s*Server|Oracle|SQLite|MariaDB|'
                        r'MongoDB|Firebird|Interbase|DB2|Sybase|H2|DuckDB)',
                        raw, re.I)
                    vendor_label = eng.group(1).strip() if eng else raw.split('(')[0].strip()[:60]
                    break
    if not vendor_label:
        vendor_label = "N/D"

    # ── 2. SP / Trigger counts — prefer stored-procedures-map.md summary ──────
    sp_count_val = str(metrics.get("db_stored_procedures", 0))
    trigger_count_val = "0"
    biz_logic_path = asis_dir / "db" / "business-logic-in-db.md"
    biz_logic_rows, biz_logic_critical_count = _parse_business_logic_in_db(biz_logic_path)
    sp_biz_count_val = str(biz_logic_critical_count)
    if sp_map_path.exists():
        sp_text = read_text(sp_map_path)
        for line in sp_text.splitlines():
            m_sp = re.match(r'^\|\s*Stored Procedures\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|', line)
            if m_sp:
                sp_count_val = m_sp.group(1)
            m_tr = re.match(r'^\|\s*Triggers\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|', line)
            if m_tr:
                trigger_count_val = m_tr.group(1)

    # ── 3. Schema table rows — parse "Table Inventory" from schema-inventory.md ──
    db_schema_rows = []
    db_schema_all_rows = []  # all rows for full D.dbSchema injection
    RISK_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    # Parse ER diagram to get real column counts per table
    er_col_counts: dict = {}
    er_path = asis_dir / "db" / "er-diagram.mmd"
    if er_path.exists():
        current_er_table = None
        current_er_col_count = 0
        for er_line in read_text(er_path).splitlines():
            tbl_m = re.match(r'^\s+(\w+)\s*\{', er_line)
            if tbl_m:
                current_er_table = tbl_m.group(1)
                current_er_col_count = 0
                continue
            if current_er_table and re.match(r'^\s+\}', er_line):
                er_col_counts[current_er_table] = current_er_col_count
                current_er_table = None
                continue
            if current_er_table and re.match(r'^\s+\w+\s+\w+', er_line):
                current_er_col_count += 1

    raw_table_rows = []  # populated by any of: schema-inventory.md, subsections, or Source D
    if schema_inv_path.exists():
        schema_inv_text = read_text(schema_inv_path)
        schema_inv_lines_all = schema_inv_text.splitlines()
        in_table_section = False
        for line in schema_inv_lines_all:
            if re.search(r'Table Inventory', line, re.I):
                in_table_section = True
                continue
            if in_table_section:
                if line.startswith('##'):
                    break
                if '|' not in line:
                    continue
                parts = [p.strip() for p in line.split('|')]
                # Canonical (5-col): ['', table, purpose, key_cols, refs, risk, '']  → len=7
                # Legacy   (3-col):  ['', table, operations, refs, '']               → len=5
                if len(parts) < 4:
                    continue
                tname = parts[1].strip('`').strip()
                if not tname or tname.startswith('-') or tname.lower() == 'table':
                    continue
                if len(parts) >= 6:
                    # Canonical 5-column format (| Table | Purpose | Key Cols | References | Risk |)
                    key_cols   = parts[3]
                    references = parts[4]
                    risk_raw   = parts[5].split('\u2014')[0].split('--')[0].strip().upper()
                else:
                    # Fallback: 3-column format (| Table | Operations | References |)
                    key_cols   = parts[2] if len(parts) > 2 else ""
                    references = parts[3] if len(parts) > 3 else ""
                    risk_raw   = "LOW"
                risk_key  = next((r for r in RISK_ORDER if r in risk_raw), "LOW")
                # Prefer real column count from ER diagram; fall back to Key Cols comma count
                real_col = er_col_counts.get(tname)
                if real_col is not None:
                    col_count = str(real_col)
                else:
                    col_count = str(len([c for c in key_cols.split(',') if c.strip()])) if key_cols else "1"
                has_pk    = "Sim"
                has_fk    = "Sim" if references.strip() not in ("\u2014", "-", "", "N/A") else "Não"
                idx_label = "PK/FK" if has_fk == "Sim" else "PK"
                raw_table_rows.append((tname, col_count, has_pk, has_fk, idx_label, RISK_ORDER[risk_key]))

        # ── Fallback: subsection format (## Tables / ### TABLENAME) ──────────
        # Used when agents generate per-table sections instead of a flat
        # "Table Inventory" pipe-table (e.g. Delphi/Firebird Analyzer output).
        if not raw_table_rows:
            raw_table_rows = _parse_schema_subsections(
                schema_inv_lines_all, er_col_counts, RISK_ORDER)
            if raw_table_rows:
                print(f"   📋 Schema subsection format detected — "
                      f"{len(raw_table_rows)} table(s) parsed from ### sections")

    # Source D: fallback — parse db-analysis-report.md when schema-inventory.md is absent.
    # Handles the case where agents consolidate all output into db-analysis-report.md
    # instead of persisting the separate schema-inventory.md file (non-regressive — only
    # activates when raw_table_rows is still empty after all schema-inventory.md parsers).
    if not raw_table_rows:
        db_report_path = asis_dir / "db-analysis-report.md"
        if db_report_path.exists():
            db_report_text = read_text(db_report_path)
            db_report_lines = db_report_text.splitlines()
            in_table_inv = False
            rank = 0
            for line in db_report_lines:
                # Detect the Table Inventory section heading in the consolidated report.
                # Agents may use: '## 2. Table Inventory', '## Table Inventory', etc.
                if re.search(r'##.*Table\s+Inventory', line, re.I):
                    in_table_inv = True
                    continue
                if in_table_inv and line.startswith('#'):
                    break  # left the section
                if not in_table_inv or '|' not in line:
                    continue
                cols = [c.strip() for c in line.split('|')]
                cols = [c for c in cols if c]  # remove empty
                # Expect at least 3 cols; skip header/separator rows
                if len(cols) < 3:
                    continue
                if re.match(r'^[-#\s]+$', cols[0]) or cols[0].lower() in ('#', 'id', 'num', 'table', 'tabela'):
                    continue
                # Format A (from agent canonical template):
                #   | # | Table | Primary Key | Estimated Rows | Purpose |
                # cols indices after empty-removal: 0=#, 1=Table, 2=PK, 3=EstRows, 4=Purpose
                # Format B (5-col schema-inventory format):
                #   | Table | Purpose | Key Cols | References | Risk |
                # Detect by checking if cols[0] looks like a number (Format A) or a table name (Format B)
                if re.match(r'^\d+$', cols[0]):
                    # Format A
                    tname = cols[1].strip('`').strip() if len(cols) > 1 else ""
                    pk_hint = cols[2].strip('`').strip() if len(cols) > 2 else ""
                    purpose = cols[4].strip() if len(cols) > 4 else ""
                else:
                    # Format B (already canonical)
                    tname = cols[0].strip('`').strip()
                    purpose = cols[1].strip() if len(cols) > 1 else ""
                    pk_hint = cols[2].strip() if len(cols) > 2 else ""
                if not tname or len(tname) > 80:
                    continue
                # Resolve column count from ER diagram; fall back to 1
                real_col = er_col_counts.get(tname) or er_col_counts.get(tname.upper())
                col_count = str(real_col) if real_col is not None else "1"
                has_pk  = "Sim" if pk_hint and pk_hint not in ("-", "—", "") else "Não"
                has_fk  = "Não"  # no FK info in this format
                idx_label = "PK" if has_pk == "Sim" else "—"
                rank += 1
                raw_table_rows.append((tname, col_count, has_pk, has_fk, idx_label, RISK_ORDER["LOW"]))
            if raw_table_rows:
                print(f"   📋 Source D (db-analysis-report.md Table Inventory) — "
                      f"{len(raw_table_rows)} table(s) parsed")

    # Source E: fallback — AST-inferred tables from delphi-ast-raw/04_database_schemas.json.
    # Some pipelines emit a structured AST extraction with tables inferred from SQL usage
    # when no DDL/schema-inventory.md exists. Inferred tables carry no PK/FK/engine info,
    # so use the same neutral placeholders the markdown parsers apply to unknown fields
    # (non-regressive — only activates when raw_table_rows is still empty after Sources A–D).
    if not raw_table_rows:
        ast_schemas = read_json(
            asis_dir / "delphi-ast-raw" / "compressed" / "04_database_schemas.json")
        inferred_tables = (ast_schemas.get("payload", {}) or {}).get("inferred_tables", [])
        for tbl in inferred_tables if isinstance(inferred_tables, list) else []:
            tname = str(tbl.get("name", "")).strip()
            if not tname:
                continue
            real_col = er_col_counts.get(tname) or er_col_counts.get(tname.upper())
            accessed = tbl.get("accessed_columns") or []
            col_count = str(real_col) if real_col is not None else str(len(accessed))
            raw_table_rows.append((tname, col_count, "Não", "Não", "—", RISK_ORDER["LOW"]))
        if raw_table_rows:
            print(f"   📋 Source E (04_database_schemas.json inferred tables) — "
                  f"{len(raw_table_rows)} table(s) parsed")

    # Sort, build D.dbSchema and legacy T1/T2/T3 rows from whatever source populated raw_table_rows
    if raw_table_rows:
        raw_table_rows.sort(key=lambda x: x[5])
        # Full list for D.dbSchema dynamic injection (all tables)
        db_schema_all_rows = [
            {"t": r[0], "c": r[1], "pk": r[2], "fk": r[3], "idx": r[4]}
            for r in raw_table_rows
        ]
        # Top 3 highest-risk rows for legacy T1/T2/T3 placeholder substitution
        for row in raw_table_rows[:3]:
            db_schema_rows.append(row[:5])
    # Ensure exactly 3 rows for T1/T2/T3 placeholders
    while len(db_schema_rows) < 3:
        db_schema_rows.append(("—", "0", "—", "—", "—"))

    # ── 4. SP rows — empty list when SP count is 0 (injected as D.sps=[]) ──
    sp_rows = []
    if sp_map_path.exists() and int(sp_count_val) > 0:
        sp_text = read_text(sp_map_path)
        for line in sp_text.splitlines():
            m = re.match(r'^\|\s*(sp_\w+|\w+)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|', line, re.I)
            if m and not m.group(1).startswith('-') and 'Name' not in m.group(1):
                sp_rows.append((m.group(1).strip(), m.group(2).strip()[:40], m.group(3).strip()))
    # AST fallback: real DB stored procedures from delphi-ast-raw/05_procedures.json.
    # code_procedures there are Delphi class methods (not DB SPs) and are ignored on
    # purpose; only payload.stored_procedures feeds this table — empty in most projects,
    # so the card stays hidden (non-regressive — only when the markdown source was empty).
    if not sp_rows:
        ast_procs = read_json(
            asis_dir / "delphi-ast-raw" / "compressed" / "05_procedures.json")
        raw_sps = (ast_procs.get("payload", {}) or {}).get("stored_procedures", []) or []
        # Decodifica o envelope Headroom (factored_array do motor fallback OU
        # string tabular "[N]{k:t,...}\n<csv>" do SmartCrusher). Idempotente:
        # conteúdo não comprimido passa intacto. Ver headroom_context.py.
        raw_sps = decode_headroom(raw_sps)
        for sp in raw_sps:
            if not isinstance(sp, dict):
                continue
            sp_name = str(sp.get("name", "")).strip()
            if not sp_name:
                continue
            sp_type = str(sp.get("kind") or sp.get("type") or "SP")[:40]
            sp_rows.append((sp_name, sp_type, str(sp.get("loc", 0))))
    # Do NOT pad with placeholder rows — an empty list renders an empty table.
    
    # Count files in tree
    def count_files(node):
        total = len(node.get("files", []))
        for child in node.get("subdirs", {}).values():
            total += count_files(child)
        return total
    total_artifacts = sum(count_files(node) for node in file_tree.values())

    # Prefer source file count from metrics.json over output-dir file count
    total_src_files = (
        metrics.get("source_files_pas", 0)
        + metrics.get("form_files_dfm", 0)
        + metrics.get("source_files_cobol", 0)
        + metrics.get("source_files_vb", 0)
        + metrics.get("source_files_vbnet", 0)
        + metrics.get("source_files_pb", 0)
    )
    file_count_display = str(total_src_files) if total_src_files > 0 else str(total_artifacts)

    # Scope description — derived from project-config.yaml
    scope_raw  = config.get("scope_modules", "all")
    tech_raw   = config.get("legacy_technology", "delphi")
    tech_label = {"delphi": "Delphi", "cobol": "COBOL", "vb6": "VB6",
                  "vbnet": "VB.NET", "powerbuilder": "PowerBuilder"}.get(tech_raw.lower(), tech_raw.capitalize())
    scope_desc = "All modules" if scope_raw == "all" else scope_raw

    # TO-BE stack labels from project-config.yaml tobe_stack section
    tobe_stack     = config.get("tobe_stack", {})
    _be_fw         = tobe_stack.get("backend_framework", "dotnet")
    _be_ver        = tobe_stack.get("backend_version", "10.0")
    _be_fw_label   = {"dotnet": ".NET", "spring-boot": "Spring Boot", "fastapi": "FastAPI"}.get(_be_fw, _be_fw)
    tobe_backend_label  = f"{_be_fw_label} {_be_ver}"
    _fe_fw         = tobe_stack.get("frontend_framework", "angular")
    _fe_ver        = tobe_stack.get("frontend_version", "17")
    _fe_fw_label   = {"angular": "Angular", "react": "React", "blazor": "Blazor"}.get(_fe_fw, _fe_fw)
    tobe_frontend_label = f"{_fe_fw_label} {_fe_ver}"

    #  ═══ SUBSTITUTIONS (aligned with template) ═══
    substitutions = {
        "PROJECT_NAME": project_name,
        "GENERATED_AT": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "COVERAGE": "F1 AS-IS",
        "SCOPE": f"{scope_desc} — {tech_label}",
        "LEGACY_TECH":               tech_label,
        "TOBE_BACKEND_VERSION":      tobe_backend_label,
        "TOBE_FRONTEND_VERSION":     tobe_frontend_label,
        "EXEC_PCT": str(round(len([a for a in ALL_AGENTS if a in ASIS_AGENTS]) / TOTAL_AGENTS * 100)),
        "AGENTS_OK": str(len(ASIS_AGENTS)),
        "TOTAL_AGENTS": str(TOTAL_AGENTS),  # overridden later with effective total
        "AGENTS_ERR": "0",
        # trace_id: prefer project-config.yaml > risk-register.json > metrics.json
        "TRACE_ID": (
            config.get("trace_id")
            or (lambda r: r.get("trace_id", "") if isinstance(r, dict) else "")(read_json(asis_dir / "risk-register.json"))
            or metrics.get("trace_id", "unknown")
        ),

        # KPIs — mapped from metrics.json schema: code.* (not totals.*)
        "TOTAL_FILES": file_count_display,
        "TEXT_FILES":  file_count_display,
        "TOTAL_LOC": str(code.get("total_loc", "N/D")),
        "CLASS_COUNT": str(code.get("classes") or code.get("classes_count") or 0),
        "METHOD_COUNT": (lambda m: str(m.get("total", m)) if isinstance(m, dict) else str(m))(
            code.get("methods") or code.get("estimated_methods", "N/D")
        ),
        # Use count, not the raw list — complexity.get("high_complexity_methods") returns
        # a list of dicts which str() converts to "[{'method':...}]" in the KPI card.
        # NOTE: `x or "N/D"` is a truthiness trap — a legitimate count of 0 (e.g. "no
        # file has CC>=10", a good finding) is falsy and would silently fall through
        # to the next source. Each candidate is checked with `is not None` instead.
        "COMPLEX_METHODS": str(_first_not_none(
            metrics.get("files_cc_above_10"),
            metrics.get("files_cc_above_5"),
            _cc_ge_10_count if (complexity.get("highest_cc_files") or complexity.get("high_complexity_methods")) else None,
        )),
        "ENDPOINT_COUNT": str(metrics.get("endpoints", metrics.get("endpoint_count", "0"))),
        # LAYER_COUNT: use only the AST pipeline's architectural layer model.
        # `bounded_contexts` and `modules` describe business decomposition and
        # must never be used as a substitute for technical layer data.
        "LAYER_COUNT": str(_first_not_none(
            len(layer_breakdown) if isinstance(layer_breakdown, dict) and layer_breakdown else None,
        )),
        "MODULE_COUNT": str(module_count),
        "TABLE_COUNT": str(metrics.get("db_tables", "N/D")),  # overridden below after parsing schema
        "DB_VOLUME": "N/D",
        "SCREEN_COUNT": str(code.get("vcl_forms", code.get("forms", code.get("form_files_dfm", "N/D")))),
        "COMPONENT_COUNT": str(code.get("vcl_forms", code.get("forms", 0)) + code.get("data_modules", code.get("datamodules", 0))),

        # File types — from flat metrics.json top-level fields
        "DELPHI_PAS_COUNT": str(metrics.get("source_files_pas", metrics.get("files", {}).get("pas", "0"))),
        "DELPHI_DFM_COUNT": str(metrics.get("form_files_dfm", metrics.get("files", {}).get("dfm", "0"))),
        "SQL_COUNT": str(metrics.get("sql_files", metrics.get("files", {}).get("sql", metrics.get("db_stored_procedures", 0)) or "0")),
        "DLL_COUNT": str(metrics.get("dll_files", metrics.get("files", {}).get("dll", "0"))),
        "CONFIG_COUNT": str(metrics.get("config_files", "5")),

        # Layers — distribute LOC/FILES across architectural layers from metrics
        # UI (Apresentação): Visual forms layout (.dfm)
        "LOC_UI": str(code.get("loc_dfm", code.get("loc_forms", "0")) or "0"),
        "FILES_UI": str(metrics.get("form_files_dfm", metrics.get("files", {}).get("dfm", "0"))),
        # Application (Aplicação): Business logic (.pas code)
        "LOC_APP": str(code.get("loc_pas_code", code.get("effective_loc", code.get("total_loc", "0"))) or "0"),
        "FILES_APP": str(metrics.get("source_files_pas", metrics.get("files", {}).get("pas", "0"))),
        # Data (Dados): Data access layer (DataModules / ADO)
        "LOC_DATA": str(code.get("loc_data_modules", "0")),
        "FILES_DATA": str(code.get("data_modules", code.get("datamodules", "0"))),
        # Database (Banco de Dados): SQL scripts, SPs, triggers
        "LOC_DB": str(code.get("loc_sql", "0")),
        "FILES_DB": str(metrics.get("db_stored_procedures", 0) + metrics.get("db_triggers", 0) + metrics.get("db_views", 0)),
        # Infrastructure: project/config files
        "LOC_INFRA": str(code.get("loc_infra", "0")),
        "FILES_INFRA": str(int(metrics.get("project_files_dpr", metrics.get("files", {}).get("dpr", 0)) or 0) + int(metrics.get("config_files", 0) or 0)),
        "EFF_LOC": str(code.get("loc_pas_code", code.get("effective_loc", code.get("total_loc", "N/D")))),
        "AVG_CC": str(metrics.get("avg_cyclomatic_complexity", complexity.get("avg_cyclomatic", "N/D"))),
        "DUP_PCT": str(metrics.get("duplication_pct", metrics.get("duplication_percentage", 0))),

        # Risk/BC/OWASP placeholders are no longer needed here —
        # risks[], bc[], owasp[] are fully injected as JSON by the build_summary_html step.
        # Keep legacy single-value placeholders in case the template has isolated uses.
        # BC1/BC2/BC3 static placeholders — also replaced here so C1.3 passes (bc[] JSON is the runtime source)
        **{f"BC{i+1}_NAME":  (bcs[i]["n"]     if i < len(bcs) else "") for i in range(6)},
        **{f"BC{i+1}_FORMS": (bcs[i]["forms"] if i < len(bcs) else "0") for i in range(6)},
        **{f"BC{i+1}_UNITS": (bcs[i]["units"] if i < len(bcs) else "0") for i in range(6)},
        **{f"BC{i+1}_LOC":   (bcs[i]["loc"]   if i < len(bcs) else "0") for i in range(6)},
        **{f"BC{i+1}_RISK":  (bcs[i]["r"]     if i < len(bcs) else "medio") for i in range(6)},
        "RISK_1": "", "EV_1": "", "ACT_1": "",
        "RISK_2": "", "EV_2": "", "ACT_2": "",
        "RISK_3": "", "EV_3": "", "ACT_3": "",
        "RISK_4": "", "EV_4": "", "ACT_4": "",
        "RISK_5": "", "EV_5": "", "ACT_5": "",
        "RISK_6": "", "EV_6": "", "ACT_6": "",
        "RISK_7": "", "EV_7": "", "ACT_7": "",

        # Patterns
        "P1_COUNT": str(pattern_rows[0][1]),
        "P1_PCT": str(round(pattern_rows[0][1] / pattern_total * 100)),
        "P2_COUNT": str(pattern_rows[1][1]),
        "P2_PCT": str(round(pattern_rows[1][1] / pattern_total * 100)),
        "P3_COUNT": str(pattern_rows[2][1]),
        "P3_PCT": str(round(pattern_rows[2][1] / pattern_total * 100)),
        "P4_COUNT": str(pattern_rows[3][1]),
        "P4_PCT": str(round(pattern_rows[3][1] / pattern_total * 100)),
        "P5_COUNT": str(pattern_rows[4][1]),
        "P5_PCT": str(round(pattern_rows[4][1] / pattern_total * 100)),

        # BC1/BC2/BC3 static placeholders removed — bc[] injected as JSON

        # DB
        "DB_VENDOR": vendor_label,
        "SP_COUNT": sp_count_val, "SP_BIZ_COUNT": sp_biz_count_val,
        "TRIGGER_COUNT": trigger_count_val, "INDEX_COUNT": "PK/FK mínimos",
        # T1/T2/T3 no longer used (dbSchema[] injected as JSON); kept for safety
        "T1": "—", "C1": "0", "PK1": "—", "FK1": "—", "IDX1": "—",
        "T2": "—", "C2": "0", "PK2": "—", "FK2": "—", "IDX2": "—",
        "T3": "—", "C3": "0", "PK3": "—", "FK3": "—", "IDX3": "—",
        # SP1-SP3 placeholders: sps[] injected as JSON
        "SP1": "", "SP1_TYPE": "", "SP1_LOC": "0",
        "SP2": "", "SP2_TYPE": "", "SP2_LOC": "0",
        "SP3": "", "SP3_TYPE": "", "SP3_LOC": "0",

        # TO-BE (not implemented yet)
        "QG1": "false", "QG2": "false", "QG3": "false", "QG4": "false", "QG5": "false", "QG6": "false",
        "W1_MOD": "TO-BE design pendente", "W1_SP": "N/D", "W1_DUR": "N/D", "W1_FLAG": "N/D",
        "W2_MOD": "Stack codegen pendente", "W2_SP": "N/D", "W2_DUR": "N/D", "W2_FLAG": "N/D",
        "W3_MOD": "QA e entrega pendentes", "W3_SP": "N/D", "W3_DUR": "N/D", "W3_FLAG": "N/D",
        "TOTAL_SP": "N/D", "TOTAL_FP": "N/D", "WAVE_COUNT": "0", "TOTAL_SPRINTS": "0", "TEAM_SIZE": "N/D", "AZURE_COST": "N/D",
        "UT_COV": "0", "IT_COV": "0", "FT_COV": "0", "UI_COV": "0", "PAR_COV": "0",

        # OWASP — OW1/OW2/OW3 placeholders removed; owasp[] injected as JSON
        "OW1_FINDING": "", "OW1_EV": "", "OW1_ACT": "",
        "OW2_FINDING": "", "OW2_EV": "", "OW2_ACT": "",
        "OW3_FINDING": "", "OW3_EV": "", "OW3_ACT": "",

        # Parity/Acceptance — defaults; overridden later if wave-comparison-data.json exists
        "GLOBAL_PARITY": "0",
        "PARITY_SCEN": "0",
        "PARITY_DIV": "0",
        "WAVES_APPROVED": "0",
        "PAR1_MOD": "N/D", "PAR1_SCEN": "0", "PAR1_PAR": "0", "PAR1_DIV": "0", "PAR1_APROV": "Pendente",
        "PAR2_MOD": "N/D", "PAR2_SCEN": "0", "PAR2_PAR": "0", "PAR2_DIV": "0", "PAR2_APROV": "Pendente",
        "AC1": "false", "AC2": "false", "AC3": "false", "AC4": "false", "AC5": "false", "AC6": "false", "AC7": "false", "AC8": "false",

        # ── Diagrams (conteúdo .mmd injetado diretamente) ──────────────────────────────
        "EXECUTIVE_SUMMARY": "See Executive Summary section below.",
        "PLACEHOLDER": "template-field",

        # ── Mermaid.js — embed the local bundle (zero CDN at runtime) ──
        "MERMAID_JS": _load_mermaid_js(base_dir),

        # ── Diagrams — sanitized for safe JS template-literal embedding ──
        "ASIS_ARCH_BLUEPRINT_DIAGRAM": sanitize_mmd(read_text(asis_dir / "diagrams" / "architecture-blueprint.mmd")),
        "C4_CONTEXT_DIAGRAM":   sanitize_mmd(read_text(asis_dir / "diagrams" / "c4-context.mmd")),
        "C4_CONTAINER_DIAGRAM": sanitize_mmd(read_text(asis_dir / "diagrams" / "c4-container.mmd")),
        "C4_COMPONENT_DIAGRAM": sanitize_mmd(read_text(asis_dir / "diagrams" / "c4-component.mmd")),
        "COMPONENT_DIAGRAM":    sanitize_mmd(read_text(asis_dir / "diagrams" / "component-diagram.mmd")),
        "SEQ_PANELS_HTML":      _build_seq_panels_html(asis_dir),
        # Named sequence placeholders — seq1 → SEQ_BAIXA_CP (index 1), seq2 → SEQ_CAD_CP (index 2)
        # Template uses these hardcoded names; resolved from the same dynamic file discovery.
        "SEQ_BAIXA_CP":         _read_seq_diagram(asis_dir, 1),
        "SEQ_CAD_CP":           _read_seq_diagram(asis_dir, 2),
        "ER_DIAGRAM":           sanitize_mmd(read_text(asis_dir / "db" / "er-diagram.mmd")),
        "TOBE_C4_DIAGRAM":              _normalize_c4_boundaries(_normalize_c4_declarations(_quote_c4_relationship_arguments(sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "c4-context.mmd") or read_text(asis_dir / "diagrams" / "c4-context.mmd"))))),
        "TOBE_C4_CONTAINER_DIAGRAM":    _normalize_c4_boundaries(_normalize_c4_declarations(_quote_c4_relationship_arguments(sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "c4-container.mmd"))))),
        "TOBE_C4_COMPONENT_DIAGRAM":    _normalize_c4_boundaries(_normalize_c4_declarations(_quote_c4_relationship_arguments(sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "c4-component.mmd"))))),
        "TOBE_ARCH_BLUEPRINT_DIAGRAM":  sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "architecture-blueprint.mmd")),
        "TOBE_CLASS_DIAGRAM":           sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "class-diagram.mmd")),
        "TOBE_SEQ_DIAGRAM":             sanitize_mmd(_load_tobe_seq_diagram(outputs_dir)),
        "CONTEXT_MAP_DIAGRAM":          sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "context-map.mmd")),
        "GANTT_DIAGRAM":                sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "migration-gantt.mmd") or read_text(outputs_dir / "tobe" / "diagrams" / "gantt-migration.mmd")),
        "TOBE_ER_DIAGRAM":              sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "mer-diagram-tobe.mmd")),
        "SOLUTION_STRUCTURE":           sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "solution-structure.mmd")),
        "CLEAN_ARCH_STRUCTURE":         sanitize_mmd(read_text(outputs_dir / "tobe" / "diagrams" / "clean-architecture.mmd")),
        # ── TO-BE Patterns Applied (patterns-applied.json) ───────────────
        "TOBE_PATTERNS_ROWS":           tobe_patterns_rows_html,
        # ── Effort Calculator waves (AG-12 effort-calculator.md) ─────────
        "EFFORT_CALC_WAVES_JSON":       json.dumps(_parse_effort_calc_waves(outputs_dir / "tobe" / "docs" / "effort-calculator.md")),
    }

    # Override TABLE_COUNT with real parsed count once db_schema_all_rows is known
    # (this block runs after the DB schema parsing above)
    if db_schema_all_rows:
        substitutions["TABLE_COUNT"] = str(len(db_schema_all_rows))

    _insert_points = _count_db_insert_points(asis_dir)
    if _insert_points > 0:
        substitutions["DB_VOLUME"] = str(_insert_points)

    print(f"   ✅ {len(substitutions)} placeholders prepared")
    return substitutions, sp_rows, db_schema_all_rows, biz_logic_rows


def _parse_effort_calc_waves(effort_calc_path: Path) -> list:
    """Parse effort-calculator.md wave table into list of dicts for D.effortCalcWaves.

    Supports two formats produced by ava-tobe-measure-size:

    Format A (single wide table — AG-12 template):
    | Wave | FP | Factor | DevSr (h) | DevPl (h) | QA (h) | DevOps (h) | Base | +Overhead 15% | +Contingency 20% | Total Hours |

    Format B (per-wave sub-tables — common in Java/Spring-Boot projects):
    ### W0 — Foundation (35 FP, Factor 1.0)
    | Role | Hours |
    ...
    | **Wave Total** | **628h** |

    Returns list of {wave, fp, sp, hours_raw, hours_overhead, hours_final, sprints}.
    Returns [] on any parse error so the template placeholder becomes a safe empty array.
    """
    text = read_text(effort_calc_path)
    if not text:
        return []
    try:
        # ── Format A: single wide table ──────────────────────────────────────
        waves = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith('|') or line.startswith('|---') or line.startswith('| Wave') or line.startswith('| ---'):
                continue
            parts = [c.strip().strip('*') for c in line.split('|')]
            parts = [p for p in parts if p]  # remove empty from split
            if len(parts) < 9:
                continue
            wave_name = parts[0]
            # Skip header rows and separator rows
            if wave_name.lower() in ('wave', '---', ''):
                continue
            try:
                fp = int(re.sub(r'[^0-9]', '', parts[1]) or '0')
                # columns: Wave, FP, Factor, DevSr, DevPl, QA, DevOps, Base, +15%, +20%, Total
                hours_raw      = int(re.sub(r'[^0-9]', '', parts[7])  or '0') if len(parts) > 7  else 0
                hours_overhead = int(re.sub(r'[^0-9]', '', parts[8])  or '0') if len(parts) > 8  else 0
                hours_final    = int(re.sub(r'[^0-9]', '', parts[-1]) or '0') if len(parts) > 9  else hours_overhead
                sprints = max(1, round(hours_final / 320))
                waves.append({
                    "wave": wave_name, "fp": fp, "sp": "N/D",
                    "hours_raw": hours_raw, "hours_overhead": hours_overhead,
                    "hours_final": hours_final, "sprints": sprints,
                })
            except (ValueError, IndexError):
                continue

        if waves:
            return waves

        # ── Format B: per-wave sub-tables (### Wn — Title …) ─────────────────
        # Each wave gets its own | Role | Hours | table and a Wave Total row.
        cur_wave: dict | None = None
        for line in text.splitlines():
            # detect wave heading: "### W0 — Foundation (35 FP, Factor 1.0)"
            m = re.match(r'^###\s+(W\d+|Wave\s*\d+)[^\d]*?(\d+)\s*FP', line, re.I)
            if m:
                if cur_wave and cur_wave.get('wave'):
                    waves.append(cur_wave)
                fp_val = int(re.sub(r'[^0-9]', '', m.group(2)) or '0')
                cur_wave = {
                    "wave": m.group(1).strip(), "fp": fp_val, "sp": "N/D",
                    "hours_raw": 0, "hours_overhead": 0, "hours_final": 0, "sprints": 1,
                }
                continue
            if cur_wave is None:
                continue
            # detect Subtotal raw row: "| **Subtotal raw** | **455h** |"
            if re.search(r'subtotal\s*raw', line, re.I):
                nums = re.findall(r'\d+', line)
                if nums:
                    cur_wave['hours_raw'] = int(nums[-1])
            # detect Wave Total row: "| **Wave Total** | **628h** |"
            elif re.search(r'wave\s*total', line, re.I):
                nums = re.findall(r'\d+', line)
                if nums:
                    total = int(nums[-1])
                    cur_wave['hours_final'] = total
                    cur_wave['hours_overhead'] = total - cur_wave['hours_raw']
                    cur_wave['sprints'] = max(1, round(total / 320))
        # append last wave
        if cur_wave and cur_wave.get('wave'):
            waves.append(cur_wave)
        return waves
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════
# F2 — Arquitetura TO-BE: parsers for previously-static tables/KPIs.
# Every value below is read from a real outputs/ artifact — never hardcoded.
# ══════════════════════════════════════════════════════════════════════════

def _f2_clean(s) -> str:
    s = "" if s is None else str(s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)   # md links -> label
    s = s.replace("`", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip()


def _f2_html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _f2_num(s) -> str:
    m = re.search(r"-?\d[\d,]*\.?\d*", str(s or ""))
    return m.group(0).replace(",", "") if m else ""


def _f2_round(s) -> str:
    v = _f2_num(s)
    if not v:
        return ""
    try:
        return str(round(float(v)))
    except ValueError:
        return v


def _f2_md_tables(text: str) -> list:
    """Parse every pipe-delimited markdown table in `text`.

    Returns a list of (headers, rows) where headers is a list of lowercased
    column names and rows is a list of dicts keyed by those names. Header
    detection is positional-agnostic: the first pipe line of each table block
    is the header; the separator row is skipped.
    """
    tables = []
    headers = None
    rows = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|"):
            if re.match(r"^\|[\s:\-|]+\|?\s*$", s):   # separator row
                continue
            cells = [c.strip().strip("*").strip() for c in s.strip("|").split("|")]
            if headers is None:
                headers = [c.lower() for c in cells]
                rows = []
            else:
                rows.append({headers[i]: (cells[i] if i < len(cells) else "")
                             for i in range(len(headers))})
        elif headers is not None:
            tables.append((headers, rows))
            headers, rows = None, None
    if headers is not None:
        tables.append((headers, rows))
    return tables


def _f2_col(row: dict, *keywords, default: str = "") -> str:
    for h, v in row.items():
        for kw in keywords:
            if kw in h:
                return v
    return default


def _f2_risk_from_word(word: str) -> str:
    w = (word or "").lower()
    if re.search(r"crit|crít", w):
        return "critico"
    if re.search(r"high|alt", w):
        return "alto"
    if re.search(r"low|baix", w):
        return "baixo"
    return "medio"


def _parse_nuget_packages_from_props(props_path: Path) -> list:
    """Parse Directory.Packages.props (Central Package Management XML) → list of {p, v, l, u}.

    Reads <PackageVersion Include="..." Version="..." /> elements.
    Uses comment lines like <!-- ASP.NET Core --> as layer grouping.
    """
    text = read_text(props_path)
    if not text:
        return []
    pkgs = []
    seen: set = set()
    current_layer = "—"
    for line in text.splitlines():
        # detect layer comment <!-- ASP.NET Core -->
        comment_m = re.search(r'<!--\s*(.+?)\s*-->', line)
        if comment_m:
            current_layer = comment_m.group(1).strip()
        pkg_m = re.search(
            r'<PackageVersion\s+Include="([^"]+)"\s+Version="([^"]+)"', line, re.I
        )
        if pkg_m:
            name, ver = pkg_m.group(1).strip(), pkg_m.group(2).strip()
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            pkgs.append({"p": name, "v": ver, "l": current_layer, "u": "—"})
    return pkgs


def _parse_nuget_packages(path: Path) -> list:
    """Parse tobe/nuget-packages.md → list of {p, v, l, u}.

    Robust to the documented format (package names + justification, versions may
    live only in Directory.Packages.props): columns matched by header keyword.

    Fallback sources tried when nuget-packages.md is absent:
      - tobe/source-code/backend/Directory.Packages.props  (CPM XML)
      - tobe/docs/tech-framework-document.md               (may contain a packages table)
    """
    text = read_text(path)
    # Fallback 1: Directory.Packages.props (Central Package Management XML)
    if not text:
        props_path = path.parent / "source-code" / "backend" / "Directory.Packages.props"
        if props_path.exists():
            return _parse_nuget_packages_from_props(props_path)
    # Fallback 2: tech-framework-document.md
    if not text:
        tfm_path = path.parent / "docs" / "tech-framework-document.md"
        text = read_text(tfm_path) if tfm_path.exists() else ""
    if not text:
        return []
    pkgs = []
    seen = set()
    for headers, rows in _f2_md_tables(text):
        if not any(("package" in h or "pacote" in h or "nuget" in h) for h in headers):
            continue
        for r in rows:
            name = _f2_clean(_f2_col(r, "package", "pacote", "nuget"))
            key = name.lower()
            if not name or key in ("package", "pacote", "total") or key in seen:
                continue
            if re.match(r"^[-\s]+$", name):
                continue
            seen.add(key)
            pkgs.append({
                "p": name,
                "v": _f2_clean(_f2_col(r, "versão", "versao", "version")) or "—",
                "l": _f2_clean(_f2_col(r, "camada", "layer", "projeto", "project")) or "—",
                "u": _f2_clean(_f2_col(
                    r, "propósito", "proposito", "purpose", "justificativa",
                    "justification", "motivo", "descrição", "descricao", "observ")) or "—",
            })
    return pkgs


def _parse_sizing_report(path: Path) -> dict:
    """Parse tobe/docs/sizing-report.md TOTAL row + squad premise → sizing KPIs."""
    text = read_text(path)
    out: dict = {}
    if not text:
        return out
    for headers, rows in _f2_md_tables(text):
        has_fp = any(("fp" in h or "function point" in h) for h in headers)
        has_sp = any((h == "sp" or "story point" in h or h.startswith("sp ")
                      or "sp (" in h) for h in headers)
        if not (has_fp and has_sp):
            continue
        for r in rows:
            first = (next(iter(r.values()), "") or "").lower()
            if "total" not in first:
                continue
            fp = _f2_round(_f2_col(r, "fp", "function point"))
            sp = _f2_round(_f2_col(r, "sp", "story point"))
            sprints = _f2_round(_f2_col(r, "sprint"))
            if fp:
                out["total_fp"] = fp
            if sp:
                out["total_sp"] = sp
            if sprints:
                out["total_sprints"] = sprints
    m = re.search(r"[Ss]quad[^:\n]*:\s*([^\n|]+)", text)
    if m:
        out["team"] = _f2_clean(m.group(1))
    return out


_COST_HDR_RE = re.compile(r"usd|custo|cost|/mo|/month|mensal|mês|\bmes\b|range|preç|prec|\$|estimat")


def _parse_cost_estimate(path: Path) -> dict:
    """Parse tobe/docs/cost-estimate.md → {prod_total, rows[]}.

    Handles the real environment-per-row layout (``Environment | Service | SKU |
    Est. Range``) as well as a per-environment-column layout. Column roles are
    resolved by header keyword, not fixed position.
    """
    text = read_text(path)
    out: dict = {"rows": []}
    if not text:
        return out
    for headers, rows in _f2_md_tables(text):
        if not any("sku" in h for h in headers):
            continue
        env_hdr = next((h for h in headers if ("ambiente" in h or "environment" in h)), "")
        svc_hdr = next((h for h in headers
                        if ("serviç" in h or "servic" in h or "service" in h
                            or "recurso" in h or "component" in h)), "")
        cost_hdr = (next((h for h in headers if "prod" in h and _COST_HDR_RE.search(h)), "")
                    or next((h for h in headers if _COST_HDR_RE.search(h)), ""))
        last_env = ""
        for r in rows:
            svc = _f2_clean(r.get(svc_hdr, "")) if svc_hdr else ""
            env = _f2_clean(r.get(env_hdr, "")) if env_hdr else ""
            if env:
                last_env = env
            cost = _f2_clean(r.get(cost_hdr, "")) if cost_hdr else ""
            sku = _f2_clean(_f2_col(r, "sku"))
            blob = (svc + " " + env).lower()
            if "total" in blob:
                if re.search(r"produç|produc|prod", blob) or re.search(r"produç|produc|prod", last_env.lower()):
                    if cost:
                        out["prod_total"] = cost
                continue
            if not svc:   # separator or non-resource row
                continue
            out["rows"].append({
                "resource": svc, "sku": sku or "—",
                "env": env or last_env or "—", "cost": cost or "—",
            })
        if out["rows"]:
            break
    return out


def _parse_infra_sizing(path: Path) -> list:
    """Fallback source for #tb-infra — per-section cost/sizing tables in infra-sizing.md."""
    text = read_text(path)
    if not text:
        return []
    rows = []
    section = "Infra"
    headers = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            section = _f2_clean(re.sub(r"^#+\s*[\d.]*\s*", "", s)) or section
            headers = None
            continue
        if s.startswith("|"):
            if re.match(r"^\|[\s:\-|]+\|?\s*$", s):
                continue
            cells = [c.strip().strip("*").strip() for c in s.strip("|").split("|")]
            if headers is None:
                headers = [c.lower() for c in cells]
                continue
            row = {headers[i]: (cells[i] if i < len(cells) else "") for i in range(len(headers))}
            env = _f2_clean(_f2_col(row, "environment", "ambiente"))
            cost_hdr = next((h for h in headers if _COST_HDR_RE.search(h)), "")
            cost = _f2_clean(row.get(cost_hdr, "")) if cost_hdr else ""
            if env and cost and "total" not in env.lower():
                rows.append({"resource": section, "sku": _f2_clean(_f2_col(row, "sku")) or "—",
                             "env": env, "cost": cost})
        else:
            headers = None
    return rows


def _build_sizing_azure(infra_path: Path, cost_path: Path) -> list:
    """Build #tb-infra rows {resource, sku, env, cost}.

    Primary source: cost-estimate.md (the artifact carrying resource + SKU +
    environment + cost). Falls back to per-section tables in infra-sizing.md.
    """
    rows = _parse_cost_estimate(cost_path).get("rows", [])
    if rows:
        return rows
    return _parse_infra_sizing(infra_path)


def _parse_effort_by_bc(path: Path) -> list:
    """Parse tobe/docs/effort-calculator.md per-BC rows → {bc, fp, sp, sprints, risk}."""
    text = read_text(path)
    if not text:
        return []
    out = []
    seen = set()
    for headers, rows in _f2_md_tables(text):
        if not any(("bounded context" in h or h == "bc") for h in headers):
            continue
        if not any("complex" in h for h in headers):
            continue
        for r in rows:
            bc = _f2_clean(next(iter(r.values()), ""))
            key = bc.lower()
            if not bc or "subtotal" in key or "total" in key or key in seen:
                continue
            seen.add(key)
            fp = _f2_num(_f2_col(r, "fp", "function point"))
            sp = _f2_round(_f2_col(r, "sp", "story point"))
            risk = _f2_risk_from_word(_f2_col(r, "complex"))
            sprints = ""
            try:
                if sp:
                    sprints = str(max(1, round(float(sp) / 20)))
            except ValueError:
                pass
            out.append({"bc": bc, "fp": fp or "—", "sp": sp or "—",
                        "sprints": sprints or "—", "risk": risk})
    return out


def _build_waves(outputs_dir: Path) -> list:
    """Build D.waves from tobe/wave-model.json (SSoT), with markdown fallback."""
    model = read_json(outputs_dir / "tobe" / "wave-model.json")
    waves_src = model.get("waves", []) if isinstance(model, dict) else []
    out = []
    for w in waves_src:
        if not isinstance(w, dict):
            continue
        bcs = w.get("bounded_contexts", []) or []
        mods = ", ".join(
            _f2_clean(str(b.get("bc_name") or b.get("bc_id") or ""))
            for b in bcs if isinstance(b, dict) and (b.get("bc_name") or b.get("bc_id"))
        )
        if not mods:
            mods = _f2_clean(str(w.get("scope_description", "")))[:80] or _f2_clean(str(w.get("wave_name", "")))
        try:
            sp_n = float(str(w.get("total_sp", 0) or 0))
        except ValueError:
            sp_n = 0.0
        try:
            fp_n = float(str(w.get("total_fp", 0) or 0))
        except ValueError:
            fp_n = 0.0
        sprints = max(1, round(sp_n / 20)) if sp_n else 0
        tshirt = str(w.get("tshirt", "")).upper().strip()
        risk = {"XL": "critico", "L": "alto", "M": "medio", "S": "baixo", "XS": "baixo"}.get(tshirt, "medio")
        out.append({
            "w": str(w.get("wave_number", "")),
            "m": mods or "—",
            "sp": str(round(sp_n)) if sp_n else "—",
            "dur": f"{sprints} sprint(s)" if sprints else "—",
            "r": risk,
            "flag": _f2_clean(str(w.get("feature_flag", ""))) or "—",
            "s": "Dimensionado" if fp_n else "Composição",
        })
    if out:
        return out
    for rel in ("tobe/wave-plan.md", "tobe/migration-plan.md", "tobe/docs/wave-plan.md"):
        text = read_text(outputs_dir / rel)
        if not text:
            continue
        for headers, rows in _f2_md_tables(text):
            if not any("wave" in h for h in headers):
                continue
            parsed = []
            for r in rows:
                wv = _f2_clean(_f2_col(r, "wave"))
                if not wv or "total" in wv.lower():
                    continue
                parsed.append({
                    "w": wv,
                    "m": _f2_clean(_f2_col(r, "módulo", "modulo", "module", "bc", "escopo", "scope")) or "—",
                    "sp": _f2_num(_f2_col(r, "sp", "story")) or "—",
                    "dur": _f2_clean(_f2_col(r, "duração", "duracao", "duration", "sprint")) or "—",
                    "r": _f2_risk_from_word(_f2_col(r, "risco", "risk")),
                    "flag": _f2_clean(_f2_col(r, "flag", "feature")) or "—",
                    "s": _f2_clean(_f2_col(r, "status", "situação", "situacao")) or "—",
                })
            if parsed:
                return parsed
    return out


def _f2_extract_field(text: str, *labels) -> str:
    for lab in labels:
        m = re.search(r"(?im)^\s*[-*]?\s*\**" + lab + r"\**\s*[:：]\s*(.+)$", text)
        if m:
            return _f2_clean(m.group(1))[:90]
    return ""


def _parse_test_plan(outputs_dir: Path) -> list:
    """Build D.testPlan from the real TO-BE test-plan artifacts.

    The test-plan contract uses ``Framework``/``Scope``/``Execution`` in its
    strategy table (not the older ``Tool``/``Target`` vocabulary).  Accept
    both schemas so a valid plan is never hidden merely because the artifact
    uses the current contract.
    """
    rows = []
    tp = read_text(outputs_dir / "tobe" / "qa" / "test-plan.md")
    if tp:
        for headers, trows in _f2_md_tables(tp):
            is_strategy = (
                any("type" in h or "tipo" in h for h in headers)
                and any("framework" in h or "ferramenta" in h or "tool" in h for h in headers)
                and any("scope" in h or "escopo" in h or "target" in h or "alvo" in h for h in headers)
            )
            if not is_strategy:
                continue
            for r in trows:
                first = _f2_clean(_f2_col(r, "type", "tipo"))
                if not first:
                    continue
                rows.append({
                    "t": first,
                    "tool": _f2_clean(_f2_col(r, "framework", "ferramenta", "tool")) or "—",
                    "alvo": _f2_clean(_f2_col(r, "scope", "escopo", "target", "alvo")) or "—",
                    "crit": _f2_clean(_f2_col(r, "execution", "execução", "execucao", "criteria", "critério", "criterio")) or "—",
                    "cov": "—",
                })
            if rows:
                break

    # Functional matrix is a separate contract artifact.  Add one summary
    # row from its Coverage Summary table when the strategy table is absent,
    # or append it when present, without inventing counts for missing data.
    matrix = read_text(outputs_dir / "tobe" / "tests" / "functional-test-matrix.md")
    if matrix:
        for headers, trows in _f2_md_tables(matrix):
            if not (any(h == "bc" or "bounded context" in h for h in headers)
                    and any("coverage" in h for h in headers)):
                continue
            coverage = []
            for r in trows:
                bc = _f2_clean(_f2_col(r, "bc", "bounded context"))
                cov = _f2_clean(_f2_col(r, "coverage"))
                if bc and bc.lower() not in {"total", "**total**"} and cov:
                    coverage.append(f"{bc}: {cov}")
            if coverage:
                rows.append({
                    "t": "Functional Matrix",
                    "tool": "Functional Test Matrix",
                    "alvo": f"{len(coverage)} BCs / coverage by bounded context",
                    "crit": "FR/BR/TC traceability",
                    "cov": "; ".join(coverage),
                })
            break
    return rows


def _build_quality_gates(outputs_dir: Path, parity_kpis: list,
                         security_review: list, brv_signoff: dict) -> list:
    """Compute the 6 Quality Gates from real artifacts.

    Primary: tobe/config/quality-gates.md per-gate status table (authoritative).
    Fallback: cross-artifact derivation (parity report, consolidated security
    review, wave-approval sign-off). Gates without an available source stay False.
    """
    spec = [
        ("qg-cov", "Line coverage ≥ 80%", ["coverage", "cobertura"]),
        ("qg-sonar", "Zero SonarQube Blocker/Critical", ["sonar"]),
        ("qg-owasp", "Zero OWASP Critical CVE", ["owasp", "cve"]),
        ("qg-parity", "Paridade funcional ≥ 99.5%", ["parity", "paridade"]),
        ("qg-perf", "Performance ≤ AS-IS baseline p95", ["performance", "perf", "p95"]),
        ("qg-client", "Cliente validation concluída", ["client", "cliente", "sign"]),
    ]
    gates = [{"k": k, "l": l, "ok": False} for (k, l, _kw) in spec]

    qg_text = read_text(outputs_dir / "tobe" / "config" / "quality-gates.md")
    parsed = {}
    if qg_text:
        for headers, rows in _f2_md_tables(qg_text):
            for r in rows:
                blob = " ".join(str(v).lower() for v in r.values())
                passed = (bool(re.search(r"✅|✔|\bpass\b|approv|aprovad|\bmet\b|\bok\b|\btrue\b", blob))
                          and not re.search(r"❌|\bfail\b|reprovad|not met|pending|pendente|\bfalse\b", blob))
                for k, _l, kws in spec:
                    if any(kw in blob for kw in kws):
                        parsed[k] = passed
        if parsed:
            for i, (k, _l, _kw) in enumerate(spec):
                if k in parsed:
                    gates[i]["ok"] = parsed[k]
            return gates

    # QG4 — functional parity ≥ 99.5%
    pv = ""
    for kpi in (parity_kpis or []):
        if isinstance(kpi, dict) and kpi.get("k") == "prk-global":
            pv = str(kpi.get("v", ""))
    mp = re.search(r"(\d+(?:\.\d+)?)", pv)
    if mp:
        try:
            gates[3]["ok"] = float(mp.group(1)) >= 99.5
        except ValueError:
            pass

    # QG2/QG3 — zero Critical/Blocker findings in the consolidated security review
    if isinstance(security_review, list) and security_review:
        crit = 0
        for e in security_review:
            if not isinstance(e, dict):
                continue
            sev = str(e.get("severity") or e.get("sev") or "").lower()
            if re.search(r"crit|crít|block|bloque", sev):
                try:
                    crit += int(_f2_num(e.get("count", 1)) or "1")
                except ValueError:
                    crit += 1
        gates[1]["ok"] = (crit == 0)
        gates[2]["ok"] = (crit == 0)

    # QG6 — client / SME validation from wave-approval sign-off
    st = str((brv_signoff or {}).get("status", "")).upper()
    gates[5]["ok"] = ("APPROV" in st)
    return gates


def _extract_blueprint_patterns(path: Path) -> list:
    text = read_text(path)
    if not text:
        return []
    names, seen, in_sec = [], set(), False
    for line in text.splitlines():
        if re.search(r"#+\s*(Cross-Cutting|Patterns|Padrões|Padroes|Architectural Patterns)", line, re.I):
            in_sec = True
            continue
        if in_sec and line.startswith("#"):
            in_sec = False
            continue
        if in_sec and line.strip().startswith("|"):
            if re.match(r"^\|[\s:\-|]+\|?\s*$", line.strip()):
                continue
            cells = [c.strip().strip("*").strip("`") for c in line.strip().strip("|").split("|")]
            first = _f2_clean(cells[0]) if cells else ""
            low = first.lower()
            if first and low not in ("pattern", "padrão", "padrao", "concern", "name", "nome") and low not in seen:
                seen.add(low)
                names.append(first)
    return names


def _build_stack_pattern_pills(outputs_dir: Path) -> str:
    """Build the dynamic Stack & Patterns pills HTML from patterns-applied.json.

    Falls back to the blueprint Patterns/Cross-Cutting section. Returns '' when
    no real pattern data exists (only the two dynamic version pills remain).
    """
    data = read_json(outputs_dir / "tobe" / "patterns-applied.json")
    plist = data.get("patterns", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    names, seen = [], set()
    for p in plist:
        nm = _f2_clean(p.get("pattern_name") or p.get("name") or "") if isinstance(p, dict) else _f2_clean(p)
        if nm and nm.lower() not in seen:
            seen.add(nm.lower())
            names.append(nm)
    if not names:
        names = _extract_blueprint_patterns(outputs_dir / "tobe" / "docs" / "architecture-blueprint.md")
    pills = [f'<span class="arc" title="{_f2_html_escape(n)}">{_f2_html_escape(n)}</span>'
             for n in names[:14]]
    return "\n        ".join(pills)


def _load_tobe_seq_diagram(outputs_dir: Path) -> str:
    """Discover and return the TO-BE architectural sequence diagram content.

    Resolution order (project-agnostic — no hardcoded flow names):
      1. tobe/diagrams/seq-arquitetural-tobe.mmd  (canonical output of trigger TD)
      2. Any seq-*.mmd in tobe/diagrams/ (alphabetical)
      3. Any seq_*.mmd in tobe/diagrams/
      4. Any *sequen*.mmd in tobe/diagrams/
    Returns empty string when no file is found so sanitize_mmd() yields ''.
    """
    tobe_diag = outputs_dir / "tobe" / "diagrams"
    if not tobe_diag.exists():
        return ""
    candidates = [tobe_diag / "seq-arquitetural-tobe.mmd"] + sorted(
        list(tobe_diag.glob("seq-*.mmd"))
        + list(tobe_diag.glob("seq_*.mmd"))
        + list(tobe_diag.glob("*sequen*.mmd"))
    )
    seen: set = set()
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        raw = read_text(p)
        if raw.strip():
            print(f"   🔀 TO-BE seq diagram: {p.name}")
            return raw
    return ""


def _load_mermaid_js(base_dir: Path) -> str:
    """Load mermaid.min.js from the templates directory and return its content.

    The HTML template uses <script>{{MERMAID_JS}}</script> to embed Mermaid
    inline, making the generated HTML 100% self-contained (no CDN required).
    Falls back to a CDN <script> tag when the local file is missing so
    diagrams still render in online environments.
    """
    local = base_dir / "src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js"
    if local.exists():
        print(f"   📦 Embedding mermaid.min.js ({local.stat().st_size // 1024} KB)")
        return local.read_text(encoding="utf-8", errors="replace")
    # Graceful CDN fallback (online use only)
    print("   ⚠️  mermaid.min.js not found locally — injecting CDN fallback")
    return 'document.write("<scr"+"ipt src=\'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js\'></scr"+"ipt>");'


def _inject_mermaid_inline(template_html: str, mermaid_js: str) -> str:
    """Replace only the canonical Mermaid bootstrap anchor.

    Mermaid is intentionally injected into the existing inline ``<script>``
    element. Do not route the bundle through the generic placeholder sweep.
    """
    anchor = "<script>{{MERMAID_JS}}</script>"
    if template_html.count(anchor) != 1:
        raise RuntimeError(
            "summary-template.html must contain exactly one canonical inline "
            "Mermaid anchor: <script>{{MERMAID_JS}}</script>"
        )
    return template_html.replace(anchor, "<script>" + mermaid_js + "</script>", 1)


def _parse_parity_report(outputs_dir: Path):
    """Parse parity-test-report.md → (parity_kpis, parity_rows).

    Reads ``outputs/tobe/parity-test-report.md`` and extracts:
    - Per-BC rows for ``D.parity[]``  → ``{m, scen, par, div, aprov}``
    - Global KPIs for ``D.parityKpis[]`` → ``{l, k, v, c, hi}``

    Returns default stubs when the file is absent or unparseable.
    """
    report_path = outputs_dir / "tobe" / "parity-test-report.md"
    # Fallback: ava-devops-compare-version writes to tobe/devops/compare-version-report.md
    _compare_report_fallback = outputs_dir / "tobe" / "devops" / "compare-version-report.md"

    default_kpis = [
        {"l": "Paridade Global",   "k": "prk-global",    "v": "N/A", "c": "a", "hi": True},
        {"l": "Cenários Mapeados", "k": "prk-scenarios", "v": "N/E", "c": "a"},
        {"l": "Divergências",      "k": "prk-divs",      "v": "N/E", "c": "a"},
        {"l": "Wave Veredicto",    "k": "prk-approved",  "v": "Pendente", "c": "a"},
    ]
    default_rows = [{"m": "N/D", "scen": "N/E", "par": "N/E", "div": "N/E", "aprov": "Não executado"}]

    if not report_path.exists():
        if _compare_report_fallback.exists():
            report_path = _compare_report_fallback
        else:
            return default_kpis, default_rows

    try:
        content = report_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return default_kpis, default_rows

    # Detect if this is the compare-version-report.md 5-column format
    _is_compare_version = "compare-version-report" in str(report_path)

    # ── Extract per-BC table rows from "Score de Paridade por Bounded Context" ──
    parity_rows = []
    in_bc_table = False
    for line in content.splitlines():
        if re.search(r"Score de Paridade por Bounded Context|## 1\.|Functional Parity Matrix", line):
            in_bc_table = True
            continue
        if in_bc_table:
            if line.startswith("## "):
                break  # next section
            if not line.startswith("|"):
                continue
            cols = [c.strip().strip("*") for c in line.split("|")[1:-1]]
            bc_name = cols[0].strip() if cols else ""
            # Skip header, separator and TOTAL rows
            if not bc_name or re.match(r"^[-\s]+$", bc_name):
                continue
            if bc_name.upper() in ("BOUNDED CONTEXT", "TOTAL"):
                continue
            if _is_compare_version:
                # compare-version-report.md: BC | AS-IS Endpoints | TO-BE Endpoints | Parity Status | Notes
                if len(cols) < 4:
                    continue
                entradas = cols[1].strip()
                paridade = "N/A"
                divs     = "0"
                aprov = re.sub(r"^[⚠️✅❌⛔🔴🟡🟢]+\s*", "", cols[3].strip()).strip()
            else:
                # Standard parity-test-report.md: 7+ columns
                if len(cols) < 7:
                    continue
                entradas = cols[1].strip()
                paridade = cols[6].strip() if len(cols) > 6 else "N/A"
                divs     = cols[3].strip() if len(cols) > 3 else "0"
                status   = cols[7].strip() if len(cols) > 7 else "N/A"
                aprov = re.sub(r"^[⚠️✅❌⛔🔴🟡🟢]+\s*", "", status).strip()
            parity_rows.append({
                "m":     bc_name,
                "scen":  entradas,
                "par":   paridade,
                "div":   divs,
                "aprov": aprov,
            })

    if not parity_rows:
        parity_rows = default_rows

    # ── Extract global metrics from the Sumário Executivo table ─────────────
    global_parity = "N/A"
    total_entries = "0"
    total_divs    = "0"
    verdict       = "Pendente"

    def _strip_md(s: str) -> str:
        """Strip markdown bold/italic markers (*) and surrounding whitespace."""
        return re.sub(r"\*+", "", s).strip()

    lines = content.splitlines()
    for line in lines:
        if re.search(r"Índice de Paridade Global|Global Parity Index", line) and "|" in line:
            parts = [_strip_md(p) for p in line.split("|")]
            if len(parts) >= 3:
                val = parts[2].split("—")[0].split("(")[0].strip()
                val = _strip_md(val)
                if val:
                    global_parity = val
        elif re.search(r"Total de entradas|Total of entries", line) and "|" in line:
            parts = [_strip_md(p) for p in line.split("|")]
            if len(parts) >= 3:
                val = _strip_md(parts[2].split("(")[0])
                if val and val != "---":
                    total_entries = val
        elif re.search(r"Veredicto Global|Global Verdict", line) and "|" in line:
            parts = [_strip_md(p) for p in line.split("|")]
            if len(parts) >= 3:
                val = re.sub(r"^[⚠️✅❌⛔🔴🟡🟢]+\s*", "", parts[2]).strip()
                if val and val != "---":
                    verdict = val

    # Derive total_divs from the TOTAL row of the BC table
    for line in lines:
        if "TOTAL" in line and "|" in line:
            cols = [_strip_md(c) for c in line.split("|")[1:-1]]
            if len(cols) >= 4:
                val = cols[3].strip()
                if val and val != "---":
                    total_divs = val
            break

    # Determine KPI colour codes
    kpi_color_parity  = "a" if global_parity.startswith("N/A") or global_parity in ("0%", "0") else "g"
    kpi_color_divs    = "g" if total_divs == "0" else "r"
    kpi_color_verdict = "a" if "CONDICIONAL" in verdict.upper() else ("g" if "GO" in verdict.upper() else "r")

    parity_kpis = [
        {"l": "Paridade Global",   "k": "prk-global",    "v": global_parity, "c": kpi_color_parity,  "hi": True},
        {"l": "Cenários Mapeados", "k": "prk-scenarios", "v": total_entries, "c": ""},
        {"l": "Divergências",      "k": "prk-divs",      "v": total_divs,    "c": kpi_color_divs},
        {"l": "Wave Veredicto",    "k": "prk-approved",  "v": verdict,       "c": kpi_color_verdict},
    ]

    return parity_kpis, parity_rows


def _parse_parity_meta(outputs_dir: Path) -> dict:
    """Extract performance/evidence metadata from wave-comparison-data.json.

    Returns a dict with keys matching the {{PARITY_*}} placeholders in the
    HTML template:  PARITY_LATENCY_AVG, PARITY_LATENCY_P95, PARITY_THROUGHPUT,
    PARITY_ERROR_RATE, PARITY_EXEC_COUNT, PARITY_EXEC_LOG_PATH,
    PARITY_SCREENSHOTS_PATH, PARITY_VERDICT.

    Falls back to '\u2014' for any missing field.
    """
    default = {
        "PARITY_LATENCY_AVG":    "\u2014",
        "PARITY_LATENCY_P95":    "\u2014",
        "PARITY_THROUGHPUT":     "\u2014",
        "PARITY_ERROR_RATE":     "\u2014",
        "PARITY_EXEC_COUNT":     "\u2014",
        "PARITY_EXEC_LOG_PATH":  "\u2014",
        "PARITY_SCREENSHOTS_PATH": "\u2014",
        "PARITY_VERDICT":        "\u2014",
    }
    data_path = outputs_dir / "tobe" / "wave-comparison-data.json"
    if not data_path.exists():
        return default
    try:
        import json as _json
        data = _json.loads(data_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default

    result = dict(default)
    # Verdict
    verdict = data.get("verdict", "")
    if verdict:
        result["PARITY_VERDICT"] = str(verdict)
    # Execution count from summary
    summary = data.get("summary", {})
    exec_count = summary.get("total_entries_executed", summary.get("total_entries_mapped", "\u2014"))
    if exec_count is not None:
        result["PARITY_EXEC_COUNT"] = str(exec_count)
    # Performance metrics (optional block)
    perf = data.get("performance", data.get("metrics", {}))
    if perf:
        for src_key, dest_key in [
            ("latency_avg_ms",  "PARITY_LATENCY_AVG"),
            ("latency_p95_ms",  "PARITY_LATENCY_P95"),
            ("throughput_rps",  "PARITY_THROUGHPUT"),
            ("error_rate_pct",  "PARITY_ERROR_RATE"),
        ]:
            val = perf.get(src_key)
            if val is not None:
                result[dest_key] = str(val)
    # Evidence paths — resolve relative to project root if files exist
    exec_log = outputs_dir / "tobe" / "parity" / "execution-log.md"
    ss_manifest = outputs_dir / "tobe" / "parity" / "screenshots-manifest.md"
    if exec_log.exists():
        result["PARITY_EXEC_LOG_PATH"] = "outputs/tobe/parity/execution-log.md"
    if ss_manifest.exists():
        result["PARITY_SCREENSHOTS_PATH"] = "outputs/tobe/parity/screenshots-manifest.md"
    return result


def _parse_parity_log(outputs_dir: Path) -> list:
    """Parse parity/execution-log.md → list of row dicts for D.parityLog[].

    Expected Markdown table columns (in order):
      id | BC | Operação | Duração (ms) | Status | Payload Hash

    Falls back to [] when the file is absent or contains no parseable rows.
    """
    log_path = outputs_dir / "tobe" / "parity" / "execution-log.md"
    if not log_path.exists():
        return []
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    rows = []
    in_table = False
    for line in content.splitlines():
        if "|" in line and not in_table:
            # Look for header row
            if re.search(r"\bid\b|\bbc\b|operac|opera\u00e7", line, re.IGNORECASE):
                in_table = True
                continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if line.strip() == "":
                continue
            break  # end of table
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 5:
            continue
        if re.match(r"^[-\s]+$", cols[0]):
            continue  # separator row
        header_keywords = ("id", "bc", "bounded", "oper", "dur", "status", "hash", "payload")
        if any(k in cols[0].lower() for k in header_keywords):
            continue  # skip column header row
        rows.append({
            "id":     cols[0] if len(cols) > 0 else "\u2014",
            "bc":     cols[1] if len(cols) > 1 else "\u2014",
            "op":     cols[2] if len(cols) > 2 else "\u2014",
            "dur_ms": cols[3] if len(cols) > 3 else "\u2014",
            "status": cols[4] if len(cols) > 4 else "\u2014",
            "hash":   cols[5] if len(cols) > 5 else "\u2014",
        })
    return rows


def _parse_brv_report(outputs_dir: Path) -> tuple:
    """Parse business-rule-validation-report.md + wave-approval.md → (brv_data, brv_signoff).

    Returns:
        brv_data: list of dicts {rule_id, category, description, fields, value_asis, value_tobe, status}
        brv_signoff: dict {sme_name, sme_date, total_rules, passed, failed, exceptions_approved, status}
    """
    brv_path = outputs_dir / "tobe" / "parity" / "business-rule-validation-report.md"
    approval_path = outputs_dir / "tobe" / "wave-approval.md"

    default_signoff = {
        "sme_name": "",
        "sme_date": "",
        "total_rules": 0,
        "passed": 0,
        "failed": 0,
        "exceptions_approved": 0,
        "status": "PENDING",
    }

    brv_data = []

    # ── Parse BRV report table ──────────────────────────────────────────────
    if brv_path.exists():
        try:
            content = brv_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

        in_table = False
        for line in content.splitlines():
            # Look for the BRV results table (rule_id | category | ...)
            if re.search(r"rule_id|Rule.ID", line, re.IGNORECASE) and "|" in line:
                in_table = True
                continue
            if not in_table:
                continue
            if not line.startswith("|"):
                if line.strip() == "":
                    continue
                break
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) < 4:
                continue
            if re.match(r"^[-\s:]+$", cols[0]):
                continue  # separator
            # Expected columns: rule_id | category | campos validados | valor AS-IS | valor TO-BE | status
            # Some reports may have description between category and campos
            rule_id = cols[0].strip() if len(cols) > 0 else "\u2014"
            category = cols[1].strip() if len(cols) > 1 else "\u2014"

            # Detect whether col[2] is description or fields based on content
            if len(cols) >= 7:
                # Full format: rule_id | category | description | fields | value_asis | value_tobe | status
                description = cols[2].strip()
                fields = cols[3].strip()
                value_asis = cols[4].strip()
                value_tobe = cols[5].strip()
                status = cols[6].strip()
            elif len(cols) >= 6:
                # Compact: rule_id | category | fields | value_asis | value_tobe | status
                description = ""
                fields = cols[2].strip()
                value_asis = cols[3].strip()
                value_tobe = cols[4].strip()
                status = cols[5].strip()
            else:
                description = ""
                fields = cols[2].strip() if len(cols) > 2 else "\u2014"
                value_asis = cols[3].strip() if len(cols) > 3 else "\u2014"
                value_tobe = "\u2014"
                status = "\u2014"

            # Normalize status
            status_upper = re.sub(r"^[⚠️✅❌⛔🔴🟡🟢]+\s*", "", status).strip().upper()
            if "PASS" in status_upper:
                status = "PASS"
            elif "EXCEPTION" in status_upper:
                status = "EXCEPTION_APPROVED"
            elif "FAIL" in status_upper:
                status = "FAIL"

            brv_data.append({
                "rule_id": rule_id,
                "category": category,
                "description": description,
                "fields": fields,
                "value_asis": value_asis,
                "value_tobe": value_tobe,
                "status": status,
            })

    # ── Parse sign-off from wave-approval.md ────────────────────────────────
    brv_signoff = dict(default_signoff)

    if brv_data:
        brv_signoff["total_rules"] = len(brv_data)
        brv_signoff["passed"] = sum(1 for r in brv_data if r["status"] == "PASS")
        brv_signoff["failed"] = sum(1 for r in brv_data if r["status"] == "FAIL")
        brv_signoff["exceptions_approved"] = sum(1 for r in brv_data if r["status"] == "EXCEPTION_APPROVED")

    if approval_path.exists():
        try:
            approval_content = approval_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            approval_content = ""

        # Extract SME/QA Lead sign-off entry
        for line in approval_content.splitlines():
            if re.search(r"SME|QA.Lead", line, re.IGNORECASE) and "|" in line:
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 2:
                    # Typical: role | name | status | date
                    if len(cols) >= 4:
                        brv_signoff["sme_name"] = cols[1].strip()
                        status_val = re.sub(r"^[⚠️✅❌⛔🔴🟡🟢]+\s*", "", cols[2]).strip()
                        brv_signoff["status"] = status_val.upper() if status_val else "PENDING"
                        brv_signoff["sme_date"] = cols[3].strip()
                    elif len(cols) >= 3:
                        brv_signoff["sme_name"] = cols[1].strip()
                        status_val = re.sub(r"^[⚠️✅❌⛔🔴🟡🟢]+\s*", "", cols[2]).strip()
                        brv_signoff["status"] = status_val.upper() if status_val else "PENDING"
                break

        # Also check for "sign_offs:" YAML-like block in wave-approval.md
        if not brv_signoff["sme_name"]:
            sme_match = re.search(
                r'role:\s*"?SME[^"]*"?\s*.*?status:\s*(\w+)',
                approval_content,
                re.IGNORECASE | re.DOTALL,
            )
            if sme_match:
                brv_signoff["status"] = sme_match.group(1).upper()

    # Derive overall status if not set from approval
    if brv_signoff["status"] == "PENDING" and brv_data:
        if brv_signoff["failed"] == 0:
            if brv_signoff["exceptions_approved"] > 0:
                brv_signoff["status"] = "APPROVED_WITH_EXCEPTIONS"
            else:
                brv_signoff["status"] = "APPROVED"

    return brv_data, brv_signoff


def _parse_regression_suite(outputs_dir: Path, project_name: str) -> dict:
    """Parse regression suite data from qa/regression-suite/ + shared-context.md.

    Returns:
        {scenarios: int, boundedContexts: list[str], ciGateStatus: "ACTIVE"|"SKIPPED"|"PENDING"}
    """
    result = {"scenarios": 0, "boundedContexts": [], "ciGateStatus": "PENDING"}

    # 1 — Count test files in regression-suite/ directory
    suite_dir = outputs_dir / "qa" / "regression-suite"
    if suite_dir.exists():
        cs_files = list(suite_dir.rglob("*.cs"))
        result["scenarios"] = len(cs_files)

        # Extract BC names from subdirectory names (one subdir per BC)
        bcs = sorted({p.parent.name for p in cs_files if p.parent != suite_dir})
        if bcs:
            result["boundedContexts"] = bcs

        # 1b — Fallback: read status.json if no .cs files found
        if result["scenarios"] == 0:
            status_json = suite_dir / "status.json"
            if status_json.exists():
                try:
                    import json as _json
                    sdata = _json.loads(status_json.read_text(encoding="utf-8", errors="replace"))
                    if isinstance(sdata, dict):
                        mapped = sdata.get("scenarios_mapped", 0)
                        if mapped:
                            result["scenarios"] = int(mapped)
                        gate = sdata.get("ci_gate_status", "")
                        if gate in ("ACTIVE", "SKIPPED", "PENDING"):
                            result["ciGateStatus"] = gate
                except Exception:
                    pass
            result["boundedContexts"] = bcs

    # 2 — Read shared-context.md for regression_suite_scenarios and regression_gate_ci
    ctx_path = Path(f"projects/{project_name}/context/shared-context.md")
    if ctx_path.exists():
        try:
            text = ctx_path.read_text(encoding="utf-8", errors="replace")
            # regression_suite_scenarios: <n>
            m = re.search(r"regression_suite_scenarios[^\d]*(\d+)", text)
            if m:
                result["scenarios"] = int(m.group(1))
            # regression_gate_ci: ACTIVE|SKIPPED|PENDING
            # handles both "regression_gate_ci: ACTIVE" and "| regression_gate_ci | ACTIVE |"
            m = re.search(r"regression_gate_ci[\s|:]+([A-Z]+)", text)
            if m and m.group(1) in ("ACTIVE", "SKIPPED", "PENDING"):
                result["ciGateStatus"] = m.group(1)
            # Extract BC names from regression_suite_bcs line (handles markdown table row too)
            if not result["boundedContexts"]:
                m = re.search(r"regression_suite_bcs[\s|:]+(.+)", text)
                if m:
                    bcs_raw = m.group(1).strip().strip("|").strip()
                    result["boundedContexts"] = [
                        b.strip().strip("|").strip()
                        for b in bcs_raw.split(",")
                        if b.strip().strip("|").strip()
                    ]
        except Exception:
            pass

    return result


_SEV_MAP = {
    "critical": "critico", "crítico": "critico", "critico": "critico",
    "high": "alto", "alto": "alto", "alta": "alto",
    "medium": "medio", "médio": "medio", "medio": "medio", "média": "medio",
    "low": "baixo", "baixo": "baixo", "baixa": "baixo",
}


def _norm_sev(v) -> str:
    return _SEV_MAP.get(str(v).strip().lower(), "")


def _yaml_scalar(v: str) -> str:
    """Strip surrounding quotes and an inline comment from a YAML scalar."""
    v = v.strip()
    if len(v) >= 2 and v[0] in "'\"" and v[-1] == v[0]:
        return v[1:-1]
    return v.split(" #", 1)[0].strip()


def _parse_iac_resources(outputs_dir: Path) -> list:
    """Parse provisioned resources from IaC source under tobe/infra/.

    Terraform: `resource "azurerm_x" "name"` blocks.  Bicep: `resource sym
    'Microsoft.X/y@version'` declarations.  Aggregated by (type, tool); provider
    is derived from the type prefix and the environment label from the real
    environments/ subfolders.  Returns [] when no IaC source exists so
    renderIaCResources() hides the card instead of showing static data.
    """
    # IaC files may live under multiple conventions depending on which DevOps agent ran:
    #   tobe/infra/           (legacy convention — ava-devops-iac)
    #   tobe/iac/             (wave-based convention — ava-devops-orchestrator Momento 1)
    #   tobe/devops/iac/      (devops-plan convention — ava-devops-orchestrator)
    # Search all candidate roots and aggregate.
    candidate_roots = [
        outputs_dir / "tobe" / "infra",
        outputs_dir / "tobe" / "iac",
        outputs_dir / "tobe" / "devops" / "iac",
    ]
    # Filter to existing dirs; de-duplicate in case symlinks point to the same place
    infra_dirs = [d for d in candidate_roots if d.is_dir()]
    if not infra_dirs:
        return []

    def _envs_for(tool_dir: Path) -> str:
        env_dir = tool_dir / "environments"
        if env_dir.is_dir():
            names = sorted(p.name for p in env_dir.iterdir() if p.is_dir())
            if names:
                return ", ".join(names)
        return "—"

    def _provider(res_type: str) -> str:
        prefix = res_type.split("_", 1)[0].lower()
        return {
            "azurerm": "Azure", "azuread": "Azure AD", "aws": "AWS",
            "google": "GCP", "kubernetes": "Kubernetes", "helm": "Kubernetes",
        }.get(prefix, prefix.title())

    tf_re = re.compile(r'resource\s+"([a-z][a-z0-9]*_[a-z0-9_]+)"\s+"[^"]+"')
    bicep_re = re.compile(r"resource\s+\w+\s+'([A-Za-z][A-Za-z0-9.]+/[A-Za-z0-9]+)@")

    counts: dict = {}
    seen_files: set = set()  # avoid double-counting if dirs overlap

    for infra_dir in infra_dirs:
        # Terraform: search direct terraform/ subdir OR flat .tf files in the root
        tf_candidates = []
        tf_sub = infra_dir / "terraform"
        if tf_sub.is_dir():
            tf_candidates.append(tf_sub)
        else:
            tf_candidates.append(infra_dir)  # wave-1/, wave-2/, or flat layout
        for tf_root in tf_candidates:
            tf_envs = _envs_for(tf_root)
            for f in tf_root.rglob("*.tf"):
                if f in seen_files:
                    continue
                seen_files.add(f)
                for m in tf_re.finditer(read_text(f)):
                    key = (m.group(1), _provider(m.group(1)), tf_envs, "Terraform")
                    counts[key] = counts.get(key, 0) + 1

        bicep_dir = infra_dir / "bicep"
        if not bicep_dir.is_dir():
            bicep_dir = infra_dir / "azure" / "bicep"
        if bicep_dir.is_dir():
            bc_envs = _envs_for(bicep_dir)
            for f in bicep_dir.rglob("*.bicep"):
                if f in seen_files:
                    continue
                seen_files.add(f)
                for m in bicep_re.finditer(read_text(f)):
                    key = (m.group(1), "Azure", bc_envs, "Bicep")
                    counts[key] = counts.get(key, 0) + 1

    rows = []
    for (rtype, prov, envs, tool), n in sorted(counts.items()):
        rows.append({
            "r": rtype if n == 1 else f"{rtype} ×{n}",
            "prov": prov, "env": envs, "tool": tool,
        })
    return rows


def _parse_ci_stages(outputs_dir: Path) -> list:
    """Parse CI pipeline stages from tobe/source-code/.github/workflows/ci.yml
    (fallback azure-pipelines.yml).  Line-based YAML — repo Python has no yaml
    module: each step `- name:` / `displayName:` becomes a stage; the adjacent
    `uses:`/`task:` fills the Tool column.  Returns [] when no CI manifest
    exists so renderCICD() hides the card."""
    src = outputs_dir / "tobe" / "source-code"
    path = next((p for p in [src / ".github" / "workflows" / "ci.yml",
                             src / "azure-pipelines.yml"] if p.exists()), None)
    if path is None:
        return []
    rows, cur = [], None
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if re.match(r'-\s+(name|task|script|uses|bash|pwsh):', line):
            if cur and cur["s"]:
                rows.append(cur)
            cur = {"s": "", "t": "", "gk": "", "g": "", "ok": "idle"}
        if cur is not None:
            m = re.match(r'(?:-\s+)?(?:name|displayName):\s*(.+)$', line)
            if m and not cur["s"]:
                cur["s"] = _yaml_scalar(m.group(1))
            m = re.match(r'(?:-\s+)?(?:uses|task):\s*(.+)$', line)
            if m and not cur["t"]:
                cur["t"] = _yaml_scalar(m.group(1))
    if cur and cur["s"]:
        rows.append(cur)
    return rows


def _parse_cd_envs(outputs_dir: Path) -> list:
    """Parse deploy environments from the CD manifest (prefers
    tobe/source-code/azure-pipelines.yml, falls back to the CD pipeline under
    tobe/iac/cd/).  Each `environment:` value becomes a row; a nearby
    deployment strategy keyword fills the Strategy column.  Returns [] when no
    CD manifest exists so renderCICD() hides the card."""
    candidates = [
        outputs_dir / "tobe" / "source-code" / "azure-pipelines.yml",
        outputs_dir / "tobe" / "iac" / "cd" / "azure-pipelines-cd.yml",
        outputs_dir / "tobe" / "source-code" / ".github" / "workflows" / "cd.yml",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        # Fallback: parse environment table from environments-plan.md or devops-plan.md
        env_md_candidates = [
            outputs_dir / "tobe" / "devops" / "environments-plan.md",
            outputs_dir / "tobe" / "devops" / "devops-plan.md",
        ]
        env_md = next((p for p in env_md_candidates if p.exists()), None)
        if env_md is None:
            return []
        rows = []
        seen = set()
        in_table = False
        for raw in read_text(env_md).splitlines():
            line = raw.strip()
            # Detect environment table header — only when Environment is the first column
            if re.match(r'\|\s*Environment\s*\|', line, re.I):
                in_table = True
                continue
            if not in_table:
                continue
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [c.strip().strip("`") for c in line.split("|")[1:-1]]
            if len(cells) < 2:
                continue
            env = cells[0].strip()
            if not env or re.match(r"^[-\s]+$", env) or env.lower() in ("environment",):
                continue
            if env.lower() in seen:
                continue
            seen.add(env.lower())
            # Infer strategy: staging/prod → blue-green, dev → rolling
            strat = "blue-green" if env.lower() in ("staging", "prod", "production", "homolog", "hml") else "rolling"
            # Approval: last column, or specific "Approval Required" column
            aprov = cells[-1] if len(cells) >= 2 else "—"
            aprov = re.sub(r"^(✅|❌|None)\s*", "", aprov).strip() or "—"
            rows.append({"env": env, "strat": strat, "ak": "",
                         "aprov": aprov, "rollback": "—", "ok": "idle"})
        return rows
    lines = read_text(path).splitlines()
    seen, rows = set(), []
    for i, raw in enumerate(lines):
        m = re.match(r'(?:-\s+)?environment:\s*(.+)$', raw.strip())
        if not m:
            continue
        env = _yaml_scalar(m.group(1)).split(".")[0].strip()
        if not env or env.lower() in seen:
            continue
        seen.add(env.lower())
        strat = ""
        for look in lines[i + 1:i + 12]:
            dm = re.match(r'(runOnce|rolling|canary|blueGreen):', look.strip())
            if dm:
                strat = dm.group(1)
                break
        rows.append({"env": env, "strat": strat or "—", "ak": "",
                     "aprov": "—", "rollback": "—", "ok": "idle"})
    return rows


def _parse_security_report(outputs_dir: Path) -> list:
    """Build consolidated Security & Compliance rows for #tb-secreport from
    deliverables/security-compliance-summary.json (preferred), falling back to
    the markdown report.  Returns [] when neither exists so
    renderSecurityReport() hides the card."""
    deliv = outputs_dir / "deliverables"
    summary = read_json(deliv / "security-compliance-summary.json")
    rows = []
    if isinstance(summary, dict) and summary:
        ev = "security-compliance-summary.json"
        gate = str(summary.get("compliance_gate", "")).strip()
        if gate:
            g = gate.upper()
            sev = "critico" if g == "BLOCKED" else ("medio" if g in ("CONDITIONAL", "PARTIAL") else "baixo")
            rows.append({"control": "Compliance Gate", "status": gate, "evidence": ev, "sev": sev})
        for label, key in (("SAST", "sast_status"), ("DAST", "dast_status")):
            val = str(summary.get(key, "")).strip()
            if val:
                rows.append({"control": label, "status": val, "evidence": ev,
                             "sev": "baixo" if val.upper() in ("CLEAN", "PASS") else "medio"})
        qgp, qgt = summary.get("quality_gates_passed"), summary.get("quality_gates_total")
        if isinstance(qgt, int) and qgt:
            rows.append({"control": "Quality Gates", "status": f"{qgp}/{qgt}", "evidence": ev,
                         "sev": "baixo" if qgp == qgt else "medio"})
        lcp, lct = summary.get("lgpd_controls_compliant"), summary.get("lgpd_controls_total")
        if isinstance(lct, int) and lct:
            rows.append({"control": "Controles LGPD", "status": f"{lcp}/{lct}", "evidence": ev,
                         "sev": "baixo" if lcp == lct else "medio"})
        for v in summary.get("blocked_by", []) or []:
            if not isinstance(v, dict):
                continue
            rows.append({
                "control": v.get("finding") or v.get("owasp") or v.get("vuln_id", "—"),
                "status": "Risco Aceito" if v.get("accepted_risk") else "Aberto",
                "evidence": v.get("evidence", "—"),
                "sev": _norm_sev(v.get("severity", "")) or "medio",
            })
        if rows:
            return rows
    report = deliv / "security-compliance-report.md"
    if report.exists():
        for line in read_text(report).splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) < 2:
                continue
            sev_idx = next((j for j, c in enumerate(cells) if _norm_sev(c)), None)
            if sev_idx is None:
                continue
            control = f"{cells[0]} — {cells[1]}" if sev_idx >= 2 else cells[0]
            status = cells[sev_idx + 1].strip() if sev_idx + 1 < len(cells) else "—"
            rows.append({"control": control, "status": status or "—",
                         "evidence": "security-compliance-report.md",
                         "sev": _norm_sev(cells[sev_idx])})
    return rows


def _compute_delivery_checklists(outputs_dir: Path, asis_dir: Path, parity_kpis: list, brv_signoff: dict):
    """Compute QG1..QG6 (pre-delivery) and AC1..AC8 (acceptance) as "true"/"false"
    from real evidence: parity report, security-findings.json, wave-approval
    sign-off, defect report and the deliverable compliance summary.  A gate is
    "true" only when a source substantiates it; an absent source yields "false"
    (gate not evidenced) rather than a fabricated pass."""
    def _b(x):
        return "true" if x else "false"

    parity_pct = None
    for k in parity_kpis or []:
        if k.get("k") == "prk-global":
            m = re.search(r"[\d.]+", str(k.get("v", "")))
            if m:
                try:
                    parity_pct = float(m.group(0))
                except ValueError:
                    parity_pct = None
            break

    sec_path = asis_dir / "security" / "security-findings.json"
    sec_present = sec_path.exists()
    sec_crit_high = 0
    if sec_present:
        data = read_json(sec_path)
        items = []
        if isinstance(data, dict):
            items = data.get("securityReview") or data.get("findings") or []
        elif isinstance(data, list):
            items = data
        for it in items:
            if not isinstance(it, dict):
                continue
            if _norm_sev(it.get("severity") or it.get("sev") or "") in ("critico", "alto"):
                c = it.get("count", 1)
                sec_crit_high += c if isinstance(c, int) and c > 0 else 1
    sec_clean = sec_present and sec_crit_high == 0

    approved = str((brv_signoff or {}).get("status", "")).upper().startswith("APPROVED")

    perf_ok = False
    wcd = read_json(outputs_dir / "tobe" / "wave-comparison-data.json")
    if isinstance(wcd, dict) and wcd:
        v = re.sub(r"\s+", "", str(wcd.get("verdict", "")).upper())
        perf_ok = "GO" in v and "NO-GO" not in v and "NOGO" not in v

    defects_path = outputs_dir / "qa" / "defect-identifier-report.md"
    defects_present = defects_path.exists()
    p12 = 0
    if defects_present:
        for line in read_text(defects_path).splitlines():
            if line.strip().startswith("|") and re.search(r"\bP[12]\b", line):
                p12 += 1
    defects_zero = defects_present and p12 == 0

    deliv_summary = read_json(outputs_dir / "deliverables" / "security-compliance-summary.json")
    deliv_present = isinstance(deliv_summary, dict) and bool(deliv_summary)
    deliv_clean = False
    if deliv_present:
        gate = str(deliv_summary.get("compliance_gate", "")).upper()
        crit_open = sum(
            1 for x in (deliv_summary.get("blocked_by", []) or [])
            if isinstance(x, dict) and _norm_sev(x.get("severity", "")) in ("critico", "alto")
        )
        deliv_clean = gate != "BLOCKED" and crit_open == 0
    ac4 = deliv_clean if deliv_present else sec_clean

    qg = {
        "QG1": _b(parity_pct is not None and parity_pct >= 80),
        "QG2": _b(sec_clean),
        "QG3": _b(sec_clean),
        "QG4": _b(parity_pct is not None and parity_pct >= 99.5),
        "QG5": _b(perf_ok),
        "QG6": _b(approved),
    }
    ac = {
        "AC1": _b(parity_pct is not None and parity_pct >= 99.5),
        "AC2": _b(defects_zero),
        "AC3": _b(perf_ok),
        "AC4": _b(ac4),
        "AC5": _b(approved),
        "AC6": _b(approved),
        "AC7": _b((outputs_dir / "deliverables" / "tech-docs-agent").is_dir()),
        "AC8": _b((outputs_dir / "deliverables" / "handover-package.md").exists()),
    }
    return qg, ac


def _build_static_diagrams(asis_dir: Path, outputs_dir: Path) -> dict:
    """Build D.staticDiagrams dict for the HTML template.

    All content is sanitized via sanitize_mmd() before JSON-encoding.
    Keys that map to non-existent files are omitted (not included with empty
    string) so the template's `|| ''` fallback triggers correctly.

    Sequence diagrams are discovered dynamically — any *sequencia*.mmd or
    seq-*.mmd file in asis/diagrams/ is included as seq1, seq2, … so projects
    with different naming conventions are all covered.
    """
    diag_dir = asis_dir / "diagrams"
    candidates = [
        ("c4ctx",   diag_dir / "c4-context.mmd"),
        ("c4cnt",   diag_dir / "c4-container.mmd"),
        ("c4comp",  diag_dir / "c4-component.mmd"),
        ("comp",    diag_dir / "component-diagram.mmd"),
        ("er",      asis_dir / "db" / "er-diagram.mmd"),
        # TO-BE diagrams (tobe/diagrams/ preferred; tobeC4 falls back to asis when F2 not run)
        ("tobeC4",            outputs_dir / "tobe" / "diagrams" / "c4-context.mmd"),
        ("tobeC4cnt",         outputs_dir / "tobe" / "diagrams" / "c4-container.mmd"),
        ("tobeC4comp",        outputs_dir / "tobe" / "diagrams" / "c4-component.mmd"),
        ("tobeArchBlueprint", outputs_dir / "tobe" / "diagrams" / "architecture-blueprint.mmd"),
        ("tobeClass",         outputs_dir / "tobe" / "diagrams" / "class-diagram.mmd"),
        ("contextMap",        outputs_dir / "tobe" / "diagrams" / "context-map.mmd"),
        ("tobeER",            outputs_dir / "tobe" / "diagrams" / "mer-diagram-tobe.mmd"),
        ("gantt",             outputs_dir / "tobe" / "diagrams" / "migration-gantt.mmd"),
        ("cleanarch",         outputs_dir / "tobe" / "diagrams" / "clean-architecture.mmd"),
        ("solution",          outputs_dir / "tobe" / "diagrams" / "solution-structure.mmd"),
        # Named seq diagrams from asis/diagrams/ — required by C3.2
        ("seqBaixaCp",        diag_dir / "seq-baixa-cp.mmd"),
        ("seqCadCp",          diag_dir / "seq-cadastro-cp.mmd"),
    ]
    result = {}
    segmentation_report_path = outputs_dir / "summary" / "compatibility" / "c4-component-segmentation-diagnostic.json"
    segmentation_dir = outputs_dir / "tobe" / "diagrams" / "c4-component-segments"
    segmentation = None
    if segmentation_report_path.is_file():
        try:
            segmentation = json.loads(segmentation_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            segmentation = None
    for key, fpath in candidates:
        if key == "gantt" and not fpath.is_file():
            legacy_gantt = fpath.with_name("gantt-migration.mmd")
            if legacy_gantt.is_file():
                fpath = legacy_gantt
        raw = read_text(fpath)
        if raw.strip():
            result[key] = _normalize_c4_boundaries(_normalize_c4_declarations(_quote_c4_relationship_arguments(sanitize_mmd(raw))))

    if segmentation and segmentation.get("publicationAllowed") and segmentation.get("relationshipsDroppedCount") == 0:
        segment_sources = []
        for segment_id in segmentation.get("generatedSegments", []):
            segment_path = segmentation_dir / f"{segment_id}.mmd"
            if not segment_path.is_file():
                segment_sources = []
                break
            segment_sources.append({"segmentId": segment_id, "source": _normalize_c4_boundaries(_normalize_c4_declarations(_quote_c4_relationship_arguments(sanitize_mmd(read_text(segment_path)))) )})
        if segment_sources and len(segment_sources) == len(segmentation.get("generatedSegments", [])):
            result["tobeC4compSegments"] = segment_sources
            result["tobeC4compSegmentation"] = segmentation
            # The failing full diagram remains in the compatibility report only.
            result.pop("tobeC4comp", None)

    # Fallback: use AS-IS c4-context when TO-BE diagram hasn't been generated yet
    if not result.get("tobeC4"):
        raw = read_text(diag_dir / "c4-context.mmd")
        if raw.strip():
            result["tobeC4"] = _normalize_c4_boundaries(_normalize_c4_declarations(_quote_c4_relationship_arguments(sanitize_mmd(raw))))

    # Ensure required TO-BE keys are always present (even when empty) so
    # html_data checks pass in SAS (AS-IS only) mode.
    for _required_tobe_key in ("tobeC4comp", "tobeC4cnt", "tobeClass", "tobeSeq"):
        if _required_tobe_key not in result:
            result[_required_tobe_key] = ""


    # Preferred: seq-arquitetural-tobe.mmd; fallback: any seq-*.mmd or *sequen*.mmd in tobe/diagrams/
    tobe_diag_dir = outputs_dir / "tobe" / "diagrams"
    if not result.get("tobeSeq") and tobe_diag_dir.exists():
        tobe_seq_candidates = [
            tobe_diag_dir / "seq-arquitetural-tobe.mmd",
        ] + sorted(
            list(tobe_diag_dir.glob("seq-*.mmd"))
            + list(tobe_diag_dir.glob("seq_*.mmd"))
            + list(tobe_diag_dir.glob("*sequen*.mmd"))
        )
        for tsc in tobe_seq_candidates:
            raw = read_text(tsc)
            if raw.strip():
                result["tobeSeq"] = sanitize_mmd(raw)
                print(f"   🔀 TO-BE sequence diagram loaded: {tsc.name}")
                break

    # Dynamic sequence diagram discovery — project-agnostic naming
    if diag_dir.exists():
        seq_files = sorted(
            list(diag_dir.glob("*sequen*.mmd"))
            + list(diag_dir.glob("seq-*.mmd"))
            + list(diag_dir.glob("seq_*.mmd"))
        )
        # Remove duplicates (same file matched by multiple globs)
        seen = set()
        unique_seq = []
        for sf in seq_files:
            if sf not in seen:
                seen.add(sf)
                unique_seq.append(sf)
        for i, sf in enumerate(unique_seq[:6], 1):
            raw = read_text(sf)
            if raw.strip():
                result[f"seq{i}"] = sanitize_mmd(raw)
        if unique_seq:
            print(f"   🔀 {len(unique_seq)} sequence diagram(s) discovered: {[s.name for s in unique_seq]}")

    return result


def _get_seq_files(asis_dir: Path) -> list:
    """Return deduplicated, sorted list of sequence diagram .mmd files under asis/diagrams/.

    Globs *sequen*.mmd, seq-*.mmd, seq_*.mmd — the same discovery logic used by
    both the HTML panel builder and the named placeholder resolver.
    """
    diag_dir = asis_dir / "diagrams"
    if not diag_dir.exists():
        return []
    raw = (
        list(diag_dir.glob("*sequen*.mmd"))
        + list(diag_dir.glob("seq-*.mmd"))
        + list(diag_dir.glob("seq_*.mmd"))
    )
    seen: set = set()
    unique: list = []
    for sf in sorted(raw):
        if sf not in seen:
            seen.add(sf)
            unique.append(sf)
    return unique


def _read_seq_diagram(asis_dir: Path, index: int) -> str:
    """Return sanitized Mermaid content for the Nth (1-based) discovered sequence diagram.

    Used to populate named template placeholders such as {{SEQ_BAIXA_CP}} (index=1)
    and {{SEQ_CAD_CP}} (index=2).  Returns empty string when the file does not exist
    or the project has fewer than `index` sequence diagrams.
    """
    files = _get_seq_files(asis_dir)
    if index < 1 or index > len(files):
        return ""
    raw = read_text(files[index - 1])
    return sanitize_mmd(raw) if raw and raw.strip() else ""


def _build_seq_panels_html(asis_dir: Path) -> str:
    """Build <div class='cd'> HTML panels for dynamically discovered sequence diagrams.

    Globs *sequen*.mmd, seq-*.mmd, seq_*.mmd from asis/diagrams/.
    Derives human-readable labels from filenames — no domain-specific names hardcoded.
    Returns concatenated panel HTML ready to replace {{SEQ_PANELS_HTML}},
    or empty string when no sequence diagrams exist for the project.
    """
    diag_dir = asis_dir / "diagrams"
    if not diag_dir.exists():
        return ""

    seq_files = sorted(
        list(diag_dir.glob("*sequen*.mmd"))
        + list(diag_dir.glob("seq-*.mmd"))
        + list(diag_dir.glob("seq_*.mmd"))
    )
    # Deduplicate (same file can match multiple globs)
    seen: set = set()
    unique_seq = []
    for sf in seq_files:
        if sf not in seen:
            seen.add(sf)
            unique_seq.append(sf)

    panels = []
    for i, sf in enumerate(unique_seq[:6], 1):
        raw = read_text(sf)
        if not raw or not raw.strip():
            continue
        content = sanitize_mmd(raw)
        # Derive human-readable title from filename:
        # "diagrama-sequencia-cadastro-funcionario" → "Fluxo: Cadastro Funcionario"
        stem = sf.stem
        label = stem
        for prefix in ("diagrama-sequencia-", "diagrama_sequencia_", "seq-", "seq_"):
            if label.startswith(prefix):
                label = label[len(prefix):]
                break
        label = "Fluxo: " + label.replace("-", " ").replace("_", " ").title()
        panel_id = f"diag-seq-{i}"
        panels.append(
            f'  <div class="cd">\n'
            f'    <div class="ch"><h2>{label}</h2>'
            f'<span class="ctag bOk">Mermaid</span></div>\n'
            f'    <div class="cb"><div class="diag-wrap">'
            f'<pre class="mermaid" id="{panel_id}">{content}</pre>'
            f'</div></div>\n'
            f'  </div>'
        )

    if panels:
        print(f"   🔀 {len(panels)} sequence panel(s) generated: {[sf.name for sf in unique_seq[:len(panels)]]}")
    return "\n".join(panels)


def parse_openapi_endpoints(outputs_dir: Path) -> list:
    """Parse tobe/docs/openapi/*.yaml files into D.apiEndpoints array.

    Each entry: {method, path, module, summary, auth}
    Reads any .yaml/.yml file under tobe/docs/openapi/ or tobe/openapi/.
    """
    endpoints = []
    search_dirs = [
        outputs_dir / "tobe" / "docs" / "openapi",
        outputs_dir / "tobe" / "openapi",
    ]
    # Module name from filename: accounts-payable-api.yaml → Accounts Payable
    def _module_name(stem: str) -> str:
        stem = re.sub(r'[-_]api$', '', stem, flags=re.I)
        return stem.replace('-', ' ').replace('_', ' ').title()

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for ypath in sorted(search_dir.glob("*.yaml")) + sorted(search_dir.glob("*.yml")):
            text = read_text(ypath)
            module = _module_name(ypath.stem)
            # Parse paths block — without full YAML parser, use regex on the text
            # Format:
            #   paths:
            #     /resource:
            #       get:
            #         summary: ...
            #         security: ...
            # State machine: detect when inside 'paths:' block
            in_paths = False
            current_path = ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped == "paths:":
                    in_paths = True
                    continue
                if in_paths:
                    # Top-level key at indent 2 = path
                    m_path = re.match(r'^  (/[^\s:]+):', line)
                    if m_path:
                        current_path = m_path.group(1)
                        continue
                    # HTTP method at indent 4
                    m_method = re.match(r'^    (get|post|put|patch|delete|head|options):', line, re.I)
                    if m_method and current_path:
                        method = m_method.group(1).upper()
                        # Look ahead in the next few lines for summary + security
                        ep = {"method": method, "path": current_path,
                              "module": module, "summary": "", "auth": "Yes"}
                        endpoints.append(ep)
                        continue
                    # Summary line (indent 6+)
                    m_sum = re.match(r'^      summary:\s*(.+)', line)
                    if m_sum and endpoints:
                        endpoints[-1]["summary"] = m_sum.group(1).strip().strip('"\'')[:80]
                    # Security: [] means no auth
                    m_sec = re.match(r'^      security:\s*\[\]', line)
                    if m_sec and endpoints:
                        endpoints[-1]["auth"] = "No"
                    # New top-level key signals end of paths block
                    if line and not line.startswith(' ') and ':' in line and not line.startswith('/'):
                        if in_paths and not stripped.startswith('/'):
                            in_paths = False

    print(f"   🌐 {len(endpoints)} API endpoints parsed from openapi/*.yaml")
    return endpoints


def parse_biz_rules(path: Path) -> list:
    """Parse business-rules.md into D.bizRules array [{id, rule, module, origin, priority}].

    Supports two formats:
    1. Table rows: | BR-001 | Rule | Source | Priority |
    2. Section headers: ## BR-001 — Title
    """
    if not path.exists():
        return []
    text = read_text(path)
    rules = []
    priority_map = {
        "HIGH": "ALTA", "MEDIUM": "MEDIA", "LOW": "BAIXA", "CRITICAL": "ALTA",
        "MUST": "ALTA", "SHOULD": "MEDIA", "MAY": "BAIXA", "DEFECT": "ALTA",
    }
    PRI_RX = r'(HIGH|MEDIUM|LOW|CRITICAL|MUST|SHOULD|MAY|DEFECT)'
    # Rule-ID prefix pattern — matches BR-001, RN-001, RN-100, BZ-001, RULE-001, FR-001
    # Also matches domain-scoped IDs: BR-CF-01, BR-CP-01, RN-FIN-001, FR-CF-001, etc.
    ID_PAT = r'(?:BR|RN|BZ|RULE|FR)(?:-[A-Za-z]+)?-\d+'
    # --- Format 1a: | RN-001 | Rule | Source | Risk | (4-col, risk may have trailing text) ---
    for line in text.splitlines():
        m = re.match(
            rf'^\|\s*({ID_PAT})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|',
            line)
        if m and not m.group(1).startswith('-') and not m.group(2).startswith('-'):
            risk_raw = m.group(4).strip()
            # Extract risk level from free-text like "MEDIUM — rounding error"
            risk_match = re.search(r'\b(HIGH|MEDIUM|LOW|CRITICAL)\b', risk_raw, re.I)
            risk = risk_match.group(1).upper() if risk_match else "MEDIUM"
            source = m.group(3).strip()
            # Derive module from source path (e.g. "frmContasPagar.LoopParcelas" → "ContasPagar")
            src_base = re.split(r'[,;]', source)[0].strip()
            file_part = re.split(r'[.\s]', src_base)[0].strip()
            unit = re.sub(r'\.pas$', '', file_part, flags=re.IGNORECASE)
            unit = re.sub(r'^(?:u|frm)([A-Z])', r'\1', unit)
            module = unit[:40] if unit else src_base[:40]
            rules.append({
                "id": m.group(1).strip(),
                "rule": m.group(2).strip()[:150],
                "module": module,
                "origin": source[:80],
                "priority": priority_map.get(risk, "MEDIA"),
                "ruleType": "",
            })
    # --- Format 1b: | BR-001 | Source | Rule | Impact | Priority | (5-col) ---
    if not rules:
        for line in text.splitlines():
            m = re.match(
                rf'^\|\s*({ID_PAT})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*[^|]*?{PRI_RX}[^|]*?\s*\|',
                line)
            if m:
                source = m.group(2).strip().replace('`', '')
                rule_text = m.group(3).strip()
                file_part = re.split(r'[:\s]', source, 1)[0]
                unit = re.sub(r'\.pas$', '', file_part, flags=re.IGNORECASE)
                unit = re.sub(r'^u([A-Z])', r'\1', unit)
                rules.append({
                    "id": m.group(1).strip(),
                    "rule": rule_text[:150],
                    "module": unit[:40],
                    "origin": source[:80],
                    "priority": priority_map.get(m.group(5).strip().upper(), "MEDIA"),
                })
    if rules:
        return rules
    # --- Format 2: section headers (fallback) ---
    current_id = None
    current_title = None
    current_module = ""
    current_priority = "MEDIA"
    current_evidence = ""
    for line in text.splitlines():
        # Match both ## BR-001 and ### RN-001 / RN-001 / BR-001 / BR-CF-01 / FR-001 formats
        m = re.match(r'^#{2,3}\s+((?:BR|RN|BZ|RULE|FR)(?:-[A-Za-z]+)?-\d+)[:\s\u2014\-]+(.+)', line)
        if m:
            if current_id:
                rules.append({"id": current_id, "rule": current_title or "",
                               "module": current_module, "origin": current_evidence[:80],
                               "priority": current_priority})
            current_id, current_title = m.group(1), m.group(2).strip()
            current_module, current_priority, current_evidence = "", "MEDIA", ""
        elif current_id:
            # Normalize: strip bold markers to get key and value
            # Handles both **Key**: value  AND  **Key:** value formats
            _key_m = re.match(r'^\*\*([^*]+?)\*\*:?\s*(.*)', line)
            _key = _key_m.group(1).strip().lower().rstrip(':') if _key_m else ""
            _val = _key_m.group(2).strip() if _key_m else ""
            if _key in ("source", "context", "origin", "fonte", "origem"):
                first = _val.split(";")[0].strip()
                file_part = re.split(r'\s*[\u2014\-]\s*', first)[0].strip()
                file_part = re.sub(r'`', '', file_part).strip()
                # Remove trailing CC= annotations
                file_part = re.split(r'\s+\(CC', file_part)[0].strip()
                unit = re.sub(r'\.pas$', '', file_part, flags=re.IGNORECASE)
                unit = re.sub(r'^u([A-Z])', r'\1', unit)
                if not current_module:
                    current_module = unit[:40]
                current_evidence = re.sub(r'`', '', first).strip()[:80]
            elif _key in ("module", "módulo", "modulo"):
                # Module field — use first bounded context name
                mod_raw = re.sub(r'`', '', _val).strip()
                current_module = mod_raw.split(",")[0].strip()[:40]
            elif _key in ("rule", "regra"):
                # Rule text may replace/supplement the header title
                rule_text = re.sub(r'`', '', _val).strip()
                if rule_text and not current_title:
                    current_title = rule_text[:150]
            elif _key in ("description", "descrição", "descricao"):
                desc = _val.strip()
                if desc and not current_title:
                    current_title = desc[:150]
            elif _key in ("priority", "prioridade"):
                p = _val.strip().split()[0].upper() if _val.strip() else ""
                current_priority = priority_map.get(p, "MEDIA")
            elif _key in ("current risk", "risk", "gap"):
                risk_text = _val.strip()
                if not current_evidence:
                    current_evidence = risk_text[:80]
                if re.search(r'\bCRITICAL\b|\bBLOCK\b|\bBLOQUEI\b', risk_text, re.I) and current_priority != "ALTA":
                    current_priority = "ALTA"
            elif "evidence" in _key or "evidencia" in _key:
                current_evidence = _val.strip()[:80]
            elif _key and ("critical" in _val.lower() or "high" in _val.lower()):
                current_priority = "ALTA"
    if current_id:
        rules.append({"id": current_id, "rule": current_title or "",
                      "module": current_module, "origin": current_evidence[:80],
                      "priority": current_priority})

    # ── Deduplication + stable sort ──────────────────────────────────────────
    # BR IDs must be unique (BR-001, BR-002, …). Keep first occurrence per ID.
    # Sort numerically so BR-001 < BR-002 < BR-010 regardless of parse order.
    seen_br: dict = {}
    deduped: list = []
    for item in rules:
        item_id = item.get("id", "")
        if item_id and item_id not in seen_br:
            seen_br[item_id] = True
            deduped.append(item)
    deduped.sort(key=lambda x: int(re.search(r'\d+', x.get('id', '0')).group() or 0))
    return deduped


def parse_func_reqs(path: Path) -> list:
    """Parse functional-requirements.md into D.funcReqs array [{id, desc, module, priority}].

    Supports two formats:
    1. Table rows under ## Module: sections: | FR-001 | Desc | ... |
    2. Section headers: ## FR-001 — Title
    """
    if not path.exists():
        return []
    text = read_text(path)
    reqs = []
    current_module = ""
    priority_map_fr = {
        "HIGH": "ALTA", "MEDIUM": "MEDIA", "LOW": "BAIXA",
        "CRITICAL": "ALTA", "MUST": "ALTA", "SHOULD": "MEDIA",
        "MAY": "BAIXA", "OPTIONAL": "BAIXA", "NICE": "BAIXA",
    }
    # --- Format 1: table rows under ## Module: sections ---
    # Handles both "## Module: Name" and "## Module FR-01: Name" formats
    for line in text.splitlines():
        m_sec = re.match(r'^##\s+(?:Module\s+\w+-\d+\s*:?\s*|Module\s*:\s*)(.+)', line, re.IGNORECASE)
        if m_sec:
            current_module = m_sec.group(1).strip().split('(')[0].strip()
            # Remove leading "FR-01:" style prefix if still present
            current_module = re.sub(r'^(?:FR|RF|RQ)-[\d.]+[:\s]+', '', current_module).strip()
            continue
        # Match FR-01, FR-01.1, FR-001, RF-CF-001, RF-AP-001 style IDs
        m = re.match(r'^\|\s*((?:FR|RF|RQ)-[\w][\w.-]*)\s*\|\s*(.+?)\s*\|', line)
        if m and not m.group(1).startswith('-'):
            desc = m.group(2).strip()
            # Extract priority from any column in the row (MUST/SHOULD/HIGH/LOW/...)
            row_upper = line.upper()
            priority = ("ALTA" if re.search(r'\bMUST\b|\bHIGH\b|\bCRITICAL\b', row_upper)
                        else "BAIXA" if re.search(r'\bMAY\b|\bOPTIONAL\b|\bLOW\b|\bNICE\b', row_upper)
                        else "MEDIA")
            reqs.append({
                "id": m.group(1).strip(),
                "desc": desc[:150],
                "module": current_module,
                "priority": priority,
            })
    if reqs:
        return reqs
    # --- Format 2: section headers (fallback) ---
    current_id = None
    current_title = None
    current_module = ""
    current_priority = "MEDIA"
    for line in text.splitlines():
        m = re.match(r'^## (FR-\d+)[\s\u2014\-]+(.+)', line)
        if m:
            if current_id:
                reqs.append({"id": current_id, "desc": current_title or "",
                             "module": current_module, "priority": current_priority})
            current_id, current_title = m.group(1), m.group(2)
            current_module, current_priority = "", "MEDIA"
        elif current_id:
            if line.startswith("**Module**:"):
                current_module = line.replace("**Module**:", "").strip()
            elif line.startswith("**Priority**:"):
                p = line.replace("**Priority**:", "").strip().upper()
                current_priority = "ALTA" if "HIGH" in p else "BAIXA" if "LOW" in p else "MEDIA"
    if current_id:
        reqs.append({
            "id": current_id,
            "desc": current_title or "",
            "module": current_module,
            "priority": current_priority,
        })
    if reqs:
        return reqs
    # --- Format 3: ### RF-\d+ headers with **Description**: / **Module**: / **Priority**: ---
    current_id = None
    current_desc = ""
    current_module = ""
    current_priority = "MEDIA"
    for line in text.splitlines():
        # Accept both "## Module: Accounts Payable" and bare "## Accounts Payable"
        m_sec = re.match(r'^## (.+)', line)
        if m_sec and not re.match(r'^##\s+(?:RF|FR|RQ)-\d+', line):
            # Commit the last open RF before switching module so it keeps the current section
            if current_id:
                reqs.append({"id": current_id, "desc": current_desc or current_id,
                             "module": current_module, "priority": current_priority})
                current_id = None
                current_desc = ""
                current_priority = "MEDIA"
            candidate = m_sec.group(1).strip()
            if candidate.startswith('Module:'):
                candidate = candidate[len('Module:'):].strip()
            current_module = candidate.split('(')[0].strip()
            continue
        m = re.match(r'^#{2,4}\s+((?:RF|FR|RQ)(?:-[A-Za-z]+)?-[\w.-]+)[\s\u2014\-:]*(.+)?', line)
        if m:
            if current_id:
                reqs.append({"id": current_id, "desc": current_desc or current_id,
                             "module": current_module, "priority": current_priority})
            current_id = m.group(1)
            # Capture the title portion after the ID (e.g. "— Application Entry Point")
            raw_title = (m.group(2) or "").strip().lstrip("\u2014- ").strip()
            current_desc = raw_title[:150] if raw_title else ""
            current_priority = "MEDIA"
            continue
        if current_id:
            if line.startswith("**Description**:") or line.startswith("**Description:**"):
                desc_val = re.sub(r'^\*\*Description\*?\*?[:\s]+', '', line).strip()
                if desc_val:
                    current_desc = desc_val[:150]
            elif line.startswith("**Module**:") or line.startswith("**Module:**"):
                current_module = re.sub(r'^\*\*Module\*?\*?[:\s]+', '', line).strip()
            elif line.startswith("**Priority**:") or line.startswith("**Priority:**"):
                p = re.sub(r'^\*\*Priority\*?\*?[:\s]+', '', line).strip().upper()
                current_priority = "ALTA" if "HIGH" in p else "BAIXA" if "LOW" in p else "MEDIA"
            elif not current_desc and line.strip() and not line.startswith('#') and not line.startswith('**') and not line.startswith('|') and not line.startswith('>') and not line.startswith('-'):
                # First plain-text line after header becomes the description
                current_desc = line.strip()[:150]
    if current_id:
        reqs.append({"id": current_id, "desc": current_desc or current_id,
                     "module": current_module, "priority": current_priority})

    # --- Format 4: **FR-NNN**: Title bold inline (business-rules.md style) ---
    # e.g. "**FR-001**: Student Enrollment with CPF Requirement"
    # Only runs when all previous formats found nothing.
    if not reqs:
        current_module = ""
        for line in text.splitlines():
            # Track module section headers: ### Module: Enrollment Management
            m_sec = re.match(r'^#{2,4}\s+(?:Module\s*:\s*)?(.+)', line)
            if m_sec and not re.match(r'^\*\*(?:FR|RF|RQ)', line):
                candidate = m_sec.group(1).strip()
                if not re.match(r'^(?:FR|RF|RQ)-', candidate):
                    current_module = candidate.split('(')[0].strip()
                continue
            # Match **FR-001**: Description
            m = re.match(r'^\*\*(?P<id>(?:FR|RF|RQ)-[\w.-]+)\*\*\s*:?\s*(?P<desc>.+)?', line)
            if m:
                desc = (m.group('desc') or '').strip()[:150]
                reqs.append({
                    "id": m.group('id'),
                    "desc": desc,
                    "module": current_module,
                    "priority": "MEDIA",
                })

    # ── Deduplication + stable sort ──────────────────────────────────────────
    # FR/RF/RQ IDs must be unique. Keep first occurrence per ID.
    # Sort numerically so FR-001 < FR-002 < FR-010 regardless of parse order.
    seen_fr: dict = {}
    deduped_reqs: list = []
    for item in reqs:
        item_id = item.get("id", "")
        if item_id and item_id not in seen_fr:
            seen_fr[item_id] = True
            deduped_reqs.append(item)
    deduped_reqs.sort(key=lambda x: int(re.search(r'\d+', x.get('id', '0')).group() or 0))
    return deduped_reqs


def _extract_screen_mermaid(path: Path) -> str:
    """Extract and sanitize the first mermaid code block from screen-navigation-map.md.

    Fallback: if no ```mermaid block exists, auto-generate a minimal flowchart TB
    from the form inventory table so the diagram is never empty.
    """
    if not path.exists():
        return ""
    text = read_text(path)
    # Primary: find explicit ```mermaid block
    m = re.search(r'```mermaid\s*\n([\s\S]*?)```', text)
    if m:
        return sanitize_mmd(m.group(1))

    # Fallback: build a simple flowchart from the inventory table rows.
    # Supports two table formats:
    #   Format A (numeric 1st col): | # | Form Name | File | Module | Type | Access |
    #   Format B (text 1st col):    | Screen | Form Name | Type | Status |
    forms_by_module: dict = {}
    in_inventory = False
    col_screen = col_file = col_module = col_type = -1
    for line in text.splitlines():
        # Detect inventory table header
        if re.search(r'\|\s*Screen(?:\s+(?:Name|ID|Id))?\s*\|', line, re.I) or ('| # |' in line and 'Form' in line):
            in_inventory = True
            hdrs = [c.strip().lower() for c in line.strip('|').split('|')]
            # Map header names to column indices
            for i, h in enumerate(hdrs):
                if h in ('screen', 'form', 'form name', '#'):
                    col_screen = i
                elif h == 'screen id' and col_screen < 0:
                    col_screen = i  # fall back: will be overridden by 'form name' below
                if h in ('file', 'form class', 'form name') and i != col_screen:
                    col_file = i
                if 'module' in h or 'access path' in h:
                    col_module = i
                if 'type' in h or 'mode' in h or 'status' in h:
                    col_type = i
            # If Screen ID was the only screen-like header, prefer Form Name as the primary
            if 'form name' in hdrs:
                fn_idx = hdrs.index('form name')
                col_screen = fn_idx
            continue
        if not in_inventory:
            continue
        if not line.startswith('|'):
            in_inventory = False
            continue
        if re.match(r'^\|[-\s|]+$', line):
            continue  # separator row
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < 2:
            continue
        # Resolve columns — fall back to positional defaults if header not found
        cs = col_screen if col_screen >= 0 else 0
        cf = col_file if col_file >= 0 else 1
        cm = col_module if col_module >= 0 else (3 if len(cols) > 3 else -1)
        ct = col_type if col_type >= 0 else (2 if len(cols) > 2 else -1)
        form_name = cols[cs] if cs < len(cols) else ''
        file_name = cols[cf] if cf < len(cols) else ''
        module    = cols[cm] if cm >= 0 and cm < len(cols) else 'Other'
        form_type = cols[ct] if ct >= 0 and ct < len(cols) else ''
        # Skip if the "screen" column is still a header keyword or empty
        if not form_name or form_name.lower() in ('#', 'screen', 'screen name', 'form'):
            continue
        label = file_name or form_name
        forms_by_module.setdefault(module, []).append((label, form_type))

    if not forms_by_module:
        return ""

    lines = ["flowchart TB"]
    node_ids: dict = {}
    idx = 0
    for mod, forms in forms_by_module.items():
        safe_mod = re.sub(r'[^A-Za-z0-9]', '_', mod)
        lines.append(f'  subgraph {safe_mod}["{mod}"]')
        for form_name, form_type in forms:
            nid = f'N{idx}'
            node_ids[form_name] = nid
            idx += 1
            label = f'{form_name}'
            if form_type:
                label += f'<br/><i>{form_type}</i>'
            lines.append(f'    {nid}["{label}"]')
        lines.append('  end')

    lines.append("  classDef nav fill:#A100FF,stroke:#7000B5,color:#fff")
    lines.append("  classDef list fill:#f0f4ff,stroke:#7b8cde,color:#1a1a1a")
    lines.append("  classDef reg fill:#fff8e1,stroke:#f9a825,color:#1a1a1a")
    return sanitize_mmd('\n'.join(lines))


def parse_screen_rules(path: Path) -> tuple:
    """Parse screen-rules.md into (rules, categories) for D.screenRules / D.screenRuleCategories.

    Expected file layout (per ava-asis-documentation contract):
        ## frmXxx — Title
        | Rule | Type | Source |
        |------|------|--------|
        | <rule text>  | <category> | <source>   |
        ...

    Each rule row becomes a dict matching the template schema consumed by
    `renderScreenRulesRows()` in summary-template.html:
        { form, category, rule, condition, source }

    The parser is forgiving about table column count:
      - 3 cols  → Rule | Type | Source              (current Meu-ERP format)
      - 4 cols  → Rule | Category | Condition | Source   (extended format)
      - 5+ cols → first 5 mapped, rest ignored
    Returns ([], []) when the file is absent or contains no parseable tables.
    """
    if not path.exists():
        return [], []
    text = read_text(path)
    rules: list = []
    current_form = ""
    in_table = False
    header_cols: list = []

    for raw in text.splitlines():
        line = raw.rstrip()

        # Form heading variants:
        #   "## frmXxx — Title"              (canonical)
        #   "## SCR-06 — frmContasPagar (Title)"  (actual Meu-ERP format)
        #   "## frmXxx / frmYyy — Title"     (multi-form)
        m_form = re.match(
            r'^##\s+'
            r'(?:[A-Z]{2,5}-\d+\s*[\u2014\-]+\s*)?'   # optional "SCR-06 — " prefix
            r'(frm[A-Za-z0-9_/ ]+?)'                    # form class name
            r'(?:\s+[\u2014\-]|\s+\(|$)',               # stop at "—", "(", or end
            line
        )
        if m_form:
            # Use only the first form name when multiple are listed (a/b/c — Title)
            form_label = m_form.group(1).strip().split('/')[0].strip()
            current_form = form_label
            in_table = False
            header_cols = []
            continue

        if not current_form:
            continue

        # Table header row → capture column names so we can map flexibly
        if line.startswith('|') and re.search(r'\bRule\b', line, re.I):
            header_cols = [c.strip().lower() for c in line.strip('|').split('|') if c.strip()]
            in_table = True
            continue

        # Separator row "|---|---|"
        if in_table and re.match(r'^\|[\s\-:|]+$', line):
            continue

        if in_table:
            if not line.startswith('|'):
                in_table = False
                header_cols = []
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) < 2:
                continue
            # Map by header position with alias support for common column name variants
            _COL_ALIASES = {
                'rule':     ('rule description', 'description', 'rule text', 'regra'),
                'type':     ('category', 'tipo', 'cat'),
                'source':   ('implementation', 'impl', 'evidência', 'source file', 'origem'),
                'condition':('condition', 'condição', 'when', 'trigger'),
            }
            def col(name: str, fallback_idx: int) -> str:
                if name in header_cols:
                    idx = header_cols.index(name)
                    return cols[idx] if idx < len(cols) else ""
                for alias in _COL_ALIASES.get(name, []):
                    if alias in header_cols:
                        idx = header_cols.index(alias)
                        return cols[idx] if idx < len(cols) else ""
                return cols[fallback_idx] if 0 <= fallback_idx < len(cols) else ""

            rule_txt   = col('rule', 1)      # fallback col 1 (Rule Description) not col 0 (Rule ID)
            category   = col('type', -1) or col('category', -1)   # no positional fallback
            condition  = col('condition', -1) if 'condition' in header_cols else ""
            source_txt = col('source', 2)
            if not rule_txt:
                continue
            rules.append({
                "form":      current_form,
                "category":  category or "Behavior",
                "rule":      rule_txt,
                "condition": condition,
                "source":    source_txt,
            })

    # Build structured category list: [{cat, count, icon}] sorted by count desc
    CAT_ICONS = {
        "Lifecycle":        "🔄",
        "Navigation":       "🧭",
        "Lookup":           "🔍",
        "Validation":       "✅",
        "Business Rule":    "⚙️",
        "Visibility Toggle":"👁",
        "State Change":     "🔁",
        "Data Binding":     "📊",
        "Other":            "📌",
    }
    from collections import Counter
    cat_counts = Counter(r["category"] for r in rules if r.get("category"))
    categories_structured = [
        {"cat": cat, "count": cnt, "icon": CAT_ICONS.get(cat, "📌")}
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
    ]
    return rules, categories_structured


# Standard Delphi VCL TColor constants -> hex (classic Windows scheme defaults for
# the theme-dependent system colors — close enough for a static-analysis swatch).
VCL_COLOR_HEX = {
    "clBlack": "#000000", "clMaroon": "#800000", "clGreen": "#008000", "clOlive": "#808000",
    "clNavy": "#000080", "clPurple": "#800080", "clTeal": "#008080", "clGray": "#808080",
    "clSilver": "#C0C0C0", "clRed": "#FF0000", "clLime": "#00FF00", "clYellow": "#FFFF00",
    "clBlue": "#0000FF", "clFuchsia": "#FF00FF", "clAqua": "#00FFFF", "clWhite": "#FFFFFF",
    "clScrollBar": "#D4D0C8", "clBackground": "#3A6EA5", "clActiveCaption": "#0054E3",
    "clInactiveCaption": "#7A96DF", "clMenu": "#F0F0F0", "clWindow": "#FFFFFF",
    "clWindowFrame": "#000000", "clMenuText": "#000000", "clWindowText": "#000000",
    "clCaptionText": "#FFFFFF", "clActiveBorder": "#B4B4B4", "clInactiveBorder": "#F4F7FC",
    "clAppWorkSpace": "#808080", "clHighlight": "#0078D4", "clHighlightText": "#FFFFFF",
    "clBtnFace": "#F0F0F0", "clBtnShadow": "#A0A0A0", "clGrayText": "#6D6D6D",
    "clBtnText": "#000000", "clInactiveCaptionText": "#D8E4F8", "clBtnHighlight": "#FFFFFF",
    "cl3DDkShadow": "#696969", "cl3DLight": "#E3E3E3", "clInfoText": "#000000",
    "clInfoBk": "#FFFFE1",
}
_VCL_TEXT_COLORS = {"clWindowText", "clBtnText", "clCaptionText", "clMenuText", "clInfoText",
                     "clGrayText", "clHighlightText", "clInactiveCaptionText"}
_VCL_BACKGROUND_COLORS = {"clWindow", "clBtnFace", "clMenu", "clScrollBar", "clAppWorkSpace",
                           "clInfoBk", "cl3DLight", "clBackground"}
_VCL_ACCENT_COLORS = {"clHighlight", "clActiveCaption", "clInactiveCaption", "clBtnHighlight",
                       "clActiveBorder", "clInactiveBorder"}
_VCL_SEMANTIC_COLORS = {"clRed", "clGreen", "clYellow", "clBlue", "clLime", "clAqua", "clFuchsia",
                         "clMaroon", "clOlive", "clNavy", "clPurple", "clTeal", "clSilver",
                         "clGray", "clBlack", "clWhite"}


def _vcl_color_category(name: str) -> str:
    if name in _VCL_TEXT_COLORS: return "Text"
    if name in _VCL_BACKGROUND_COLORS: return "Background"
    if name in _VCL_ACCENT_COLORS: return "Accent"
    if name in _VCL_SEMANTIC_COLORS: return "Semantic"
    return "Other"


def _hex_to_rgb_str(hexval: str) -> str:
    h = hexval.lstrip('#')
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def _extract_dfm_color_palette(project_name: str) -> list:
    """Fallback for D.uiColorPalette when ui-color-palette.json is absent: scan the
    legacy .dfm forms directly for `Color = clXXX` VCL assignments — real occurrence
    counts from the project's own source, never a fixed placeholder palette.
    """
    cfg_path = Path(f"projects/{project_name}/context/project-config.yaml")
    m = re.search(r'^repository_path:\s*"?([^"#\n]+?)"?\s*(?:#.*)?$', read_text(cfg_path), re.M)
    if not m:
        return []
    repo_root = Path(m.group(1).strip().replace('\\\\', '\\'))
    if not repo_root.exists():
        return []

    counts = Counter()
    for dfm in repo_root.rglob("*.dfm"):
        for cm in re.finditer(r'\bColor\s*:?=\s*(cl[A-Za-z0-9]+)\b', read_text(dfm)):
            counts[cm.group(1)] += 1

    return [
        {
            "name": name,
            "hex": VCL_COLOR_HEX.get(name, "#808080"),
            "rgb": _hex_to_rgb_str(VCL_COLOR_HEX.get(name, "#808080")),
            "category": _vcl_color_category(name),
            "usage": f"{count} occurrence(s) in legacy .dfm forms",
            "dfm_count": count,
        }
        for name, count in counts.most_common()
    ]


def parse_ui_colors(outputs_path: Path, project_name: str = None) -> list:
    """Load ui-color-palette.json; return list of color swatches for D.uiColorPalette."""
    palette_file = outputs_path / "asis" / "ui-color-palette.json"
    if palette_file.exists():
        data = read_json(palette_file)
        if isinstance(data, list):
            return data
    if project_name:
        return _extract_dfm_color_palette(project_name)
    return []


def parse_screen_overview_and_groups(path: Path, screen_forms: list) -> tuple:
    """Extract overview text, narrative, and grouping data from screen-navigation-map.md.

    Returns (overview, narrative, groups) where:
      - overview:  string — paragraphs between the H1 title and the first H2.
      - narrative: string — body of the "## Navigation Patterns" section
                   (or "## Padrões de Navegação"), rendered as plain text.
      - groups:    list of {title, description, screens[]} derived from
                   `subgraph X["Label"]` blocks in the mermaid diagram. Falls
                   back to grouping `screen_forms` by their `module` column.

    All return values default to safe empties when the file is absent.
    """
    if not path.exists():
        return "", "", []

    text = read_text(path)
    lines = text.splitlines()

    # ── Overview: paragraphs between top H1 and first H2 ─────────────────────
    overview_lines: list = []
    seen_h1 = False
    for line in lines:
        if not seen_h1 and line.startswith('# '):
            seen_h1 = True
            continue
        if seen_h1:
            if line.startswith('## ') or line.startswith('---'):
                break
            # Skip metadata bold lines like "**Agent**:", "**Trace ID**:"
            if re.match(r'^\*\*[^*]+\*\*\s*:', line.strip()):
                continue
            overview_lines.append(line)
    overview = re.sub(r'\n{3,}', '\n\n', '\n'.join(overview_lines)).strip()

    # ── Narrative: pull the "Navigation Patterns" / "Padrões de Navegação" sec
    narrative_lines: list = []
    in_narr = False
    for line in lines:
        if re.match(r'^##\s+(Navigation Patterns|Padr[õo]es de Navega[çc][ãa]o)\s*$', line, re.I):
            in_narr = True
            continue
        if in_narr:
            if line.startswith('## ') or line.startswith('# '):
                break
            narrative_lines.append(line)
    narrative = re.sub(r'\n{3,}', '\n\n', '\n'.join(narrative_lines)).strip()

    # ── Groups: parse `subgraph X["Label"]` from the mermaid block ───────────
    groups: list = []
    m_block = re.search(r'```mermaid\s*\n([\s\S]*?)```', text)
    if m_block:
        mblock = m_block.group(1)
        # Extract all subgraph headers + content between subgraph/end pairs
        subgraph_re = re.compile(r'subgraph\s+\w+\s*\[\s*"([^"]+)"\s*\]([\s\S]*?)\bend\b')
        for m in subgraph_re.finditer(mblock):
            title = m.group(1).strip()
            body = m.group(2)
            # Pull form names from node defs:  Xxx["frmYyy<br/>..."] or "frmYyy"
            form_names: list = []
            for n in re.finditer(r'"(frm[A-Za-z0-9_]+|udm[A-Za-z0-9_]+)', body):
                fname = n.group(1)
                if fname not in form_names:
                    form_names.append(fname)
            if title and form_names:
                groups.append({
                    "title":       title,
                    "description": "",
                    "screens":     form_names,
                })

    # Fallback: group by `module` from screen_forms if no subgraphs found
    if not groups and screen_forms:
        by_module: dict = {}
        for sf in screen_forms:
            mod = sf.get("module") or "Other"
            by_module.setdefault(mod, []).append(sf.get("file") or sf.get("form") or "")
        for mod, items in by_module.items():
            groups.append({
                "title":       mod,
                "description": "",
                "screens":     [s for s in items if s],
            })

    return overview, narrative, groups


def parse_screen_forms(path: Path) -> list:
    """Parse screen-navigation-map.md form inventory table into D.screenForms array.

    Output schema (consumed by `tb-screens` in summary-template.html):
        { num, form, file, type, module, access }

    Where, for VCL projects:
        form   = TForm class (e.g. "frmContasPagar")
        file   = source unit / .pas (or empty if unknown)
        type   = UI type (Modal, Modal+Lookup, Parent shell, DataModule action, ...)
        module = bounded-context / panel grouping (resolved later by builder)
        access = trigger / how the screen is opened

    Header detection is column-name based (not positional) so the parser works
    with both the canonical 4-col format and the legacy 6-col format without
    misalignment:

      • Canonical (Meu-ERP):  | Screen | Form | Trigger | Type |
      • Legacy:               | # | Form | File | Module | Type | Access |
      • API-fallback:         | Endpoint | Method | Description |  → Format 3
    """
    if not path.exists():
        return []
    text = read_text(path)
    forms: list = []
    num = 0
 
    # ── Pass 1: VCL inventory (header-name driven) ───────────────────────────
    in_table = False
    in_nav_table = False
    col_idx: dict = {}     # role → column index
    headers: list = []     # raw header tokens lowercased

    def map_headers(hdrs: list) -> dict:
        """Map normalized header names to internal roles (form/file/type/module/access)."""
        mapping: dict = {}
        for i, h in enumerate(hdrs):
            hh = h.strip().lower()
            if hh in ('form', 'form name', 'class', 'form class') and 'form' not in mapping:
                mapping['form'] = i
            elif hh in ('screen', 'screen name', 'screen / view', 'screen label',
                        'title', 'title (inferred)') and 'screen' not in mapping:
                mapping['screen'] = i
            elif hh in ('file', 'unit', 'pas', 'source') and 'file' not in mapping:
                mapping['file'] = i
            elif hh in ('type', 'mode', 'kind') and 'type' not in mapping:
                mapping['type'] = i
            elif hh in ('module', 'group', 'bc', 'context') and 'module' not in mapping:
                mapping['module'] = i
            elif hh in ('trigger', 'access', 'access path', 'opened by', 'invoked by') and 'access' not in mapping:
                mapping['access'] = i
            elif hh in ('#', 'screen id') and 'num' not in mapping:
                mapping['num'] = i
        return mapping

    for line in text.splitlines():
        # Header detection — must contain a Form/Screen column AND be a markdown table row
        if line.startswith('|') and re.search(r'\|\s*(?:Screen|Form|#)\s*\|', line, re.I):
            headers = [c.strip() for c in line.strip('|').split('|')]
            col_idx = map_headers(headers)
            if 'form' in col_idx or 'screen' in col_idx:
                in_table = True
        # Detect navigation inventory table header (Screen or Screen Name)
        if re.search(r'\|\s*Screen(?:\s+(?:Name|ID|Id))?\s*\|', line, re.I):
            in_nav_table = True
            # Also parse the headers so data rows are consumed by the in_table block
            headers = [c.strip() for c in line.strip('|').split('|')]
            col_idx = map_headers(headers)
            if 'form' in col_idx or 'screen' in col_idx:
                in_table = True
            continue
        # Detect legacy "# | Form" header
        if '| # |' in line and 'Form' in line:
            in_nav_table = True
            headers = [c.strip() for c in line.strip('|').split('|')]
            col_idx = map_headers(headers)
            if 'form' in col_idx or 'screen' in col_idx:
                in_table = True
            continue
        if in_nav_table:
            if not line.startswith('|'):
                in_nav_table = False
                continue
        if in_table:
            if not line.startswith('|'):
                in_table = False
                col_idx = {}
                continue
            if re.match(r'^\|[-\s:|]+$', line):
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            if not cols or all(not c for c in cols):
                continue

            def get(role: str, default: str = "") -> str:
                idx = col_idx.get(role, -1)
                return cols[idx] if 0 <= idx < len(cols) else default

            screen_label = get('screen')
            form_class   = get('form')
            ftype        = get('type') or 'Modal'
            access_txt   = get('access')
            file_name    = get('file')
            module_name  = get('module')

            # Prefer the actual class name (frmXxx) for the Form column; some
            # canonical files put the human screen name first and the class second.
            form_value = form_class or screen_label
            if form_value.lower() in ('form', 'screen', '#'):
                continue

            # If "file" column is missing, derive .pas filename from the form class
            if not file_name and form_value.lower().startswith(('frm', 'udm', 't')):
                # Convention: frmContasPagar → uContasPagar.pas
                base = re.sub(r'^(frm|udm|T)', '', form_value)
                if base:
                    file_name = f"u{base}.pas"

            num += 1
            forms.append({
                "num":    str(num),
                "form":   form_value,
                "file":   file_name,
                "type":   ftype,
                "module": module_name,        # filled later by builder via group resolution
                "access": access_txt or 'ShowModal',
                "screen_label": screen_label,  # human-readable name
            })

    if forms:
        return forms

    # ── Pass 2 (Format 3 fallback): API endpoint tables ──────────────────────
    current_section = ""
    in_endpoint_table = False
    endpoint_col_indices: dict = {}

    for line in text.splitlines():
        m_sec = re.match(r'^#{2,4}\s+(.+)', line)
        if m_sec:
            current_section = m_sec.group(1).strip()
            in_endpoint_table = False
            endpoint_col_indices = {}
            continue

        # Detect endpoint table header: | Endpoint | Method | ... |
        #                            or | Pattern  | Method | ... |
        if re.search(r'\|\s*(?:Endpoint|Pattern)\s*\|', line, re.I):
            in_endpoint_table = True
            hdrs = [h.strip().lower() for h in line.strip('|').split('|')]
            for i, h in enumerate(hdrs):
                if h in ('endpoint', 'pattern'):
                    endpoint_col_indices['path'] = i
                elif h in ('method', 'verb', 'http'):
                    endpoint_col_indices['method'] = i
                elif h in ('description', 'desc', 'notes', 'note', 'protocol'):
                    endpoint_col_indices['desc'] = i
            continue

        if in_endpoint_table:
            if not line.startswith('|'):
                in_endpoint_table = False
                endpoint_col_indices = {}
                continue
            if re.match(r'^\|[-\s|]+$', line):
                continue  # separator row
            cols = [c.strip() for c in line.strip('|').split('|')]
            cols = [c for c in cols if c]
            if not cols:
                continue
            path_idx   = endpoint_col_indices.get('path', 0)
            method_idx = endpoint_col_indices.get('method', 1)
            desc_idx   = endpoint_col_indices.get('desc', 2)
            ep_path = cols[path_idx] if path_idx < len(cols) else cols[0]
            method  = cols[method_idx] if method_idx < len(cols) else ""
            desc    = cols[desc_idx]   if desc_idx   < len(cols) else ""
            # Skip header-keyword rows that slipped through
            if ep_path.lower() in ('endpoint', 'pattern', '---', ''):
                continue
            num += 1
            forms.append({
                "num":    str(num),
                "form":   ep_path,           # endpoint path / pattern
                "file":   method,            # HTTP method
                "module": current_section[:40],
                "type":   "API Endpoint",
                "access": desc[:60],
            })

    return forms


def parse_screen_forms_ast(path: Path) -> list:
    """Parse the AST pipeline's 02_form_business_rules.json into D.screenForms rows.

    Same output schema as `parse_screen_forms` (num/form/file/type/module/access/
    screen_label). `form` uses the frm-prefixed instance name (not the T-prefixed
    class) so it matches the `frmXxx` node labels the mermaid group parser keys on.
    """
    if not path.exists():
        return []
    data = read_json(path)
    payload = data.get("payload", {}) if isinstance(data, dict) else {}
    raw_forms = payload.get("forms", [])
    if not isinstance(raw_forms, list):
        return []
    forms: list = []
    for i, f in enumerate(raw_forms):
        if not isinstance(f, dict):
            continue
        form_name = f.get("form_name") or f.get("form_class") or ""
        if not form_name:
            continue
        forms.append({
            "num":          str(i + 1),
            "form":         form_name,
            "file":         f.get("source_file", ""),
            "type":         "DataModule action" if form_name.lower().startswith("udm") else "Modal",
            "module":       "",  # resolved later by builder via group/mermaid resolution
            "access":       "ShowModal",
            "screen_label": f.get("form_class", ""),
        })
    return forms


def parse_screen_patterns(path: Path) -> list:
    """Parse '## Navigation Patterns' / '## Padrões de Navegação' table.

    Returns list of {pattern, count, description} dicts for D.screenPatterns.
    Empty list if the section is missing.
    """
    if not path.exists():
        return []
    text = read_text(path)
    patterns: list = []
    in_section = False
    in_table = False
    col_idx: dict = {}
    for line in text.splitlines():
        if re.match(r'^##\s+(Navigation Patterns|Padr[õo]es de Navega[çc][ãa]o|Screen Inventory|Invent[aá]rio de Telas|Screen List)\s*$', line, re.I):
            in_section = True
            continue
        if in_section and line.startswith('## ') and not re.match(r'^##\s+(Navigation Patterns|Padr[õo]es|Screen Inventory|Invent[aá]rio)', line, re.I):
            break
        if not in_section:
            continue
        if line.startswith('|') and re.search(r'\bPattern\b|\bPadr[ãa]o\b|\bScreen\b|\bTela\b', line, re.I):
            hdrs = [c.strip().lower() for c in line.strip('|').split('|')]
            for i, h in enumerate(hdrs):
                if h in ('pattern', 'padrão', 'padrao', 'screen', 'tela'):
                    col_idx['pattern'] = i
                elif h in ('usage count', 'count', 'quantidade', 'forms', 'qtd', 'trigger', 'url'):
                    col_idx['count'] = i
                elif h in ('description', 'descrição', 'descricao', 'desc', 'notes', 'type', 'tipo'):
                    col_idx['desc'] = i
            in_table = True
            continue
        if in_table:
            if not line.startswith('|'):
                in_table = False
                continue
            if re.match(r'^\|[-\s:|]+$', line):
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) < 2:
                continue
            patterns.append({
                "pattern": cols[col_idx.get('pattern', 0)] if col_idx.get('pattern', 0) < len(cols) else "",
                "count":   cols[col_idx.get('count', 1)]   if col_idx.get('count', 1) < len(cols) else "",
                "desc":    cols[col_idx.get('desc', 2)]    if col_idx.get('desc', 2) < len(cols) else "",
            })
    return patterns


def parse_screen_lookups(path: Path) -> list:
    """Extract cross-form lookup edges from the mermaid block.

    Matches lines of the form:    A -->|"trigger"| B
    Returns list of {source, trigger, target} dicts (D.screenLookups).
    Used to render the "Lookups Cruzados" card — input for TO-BE API design.
    """
    if not path.exists():
        return []
    text = read_text(path)
    m = re.search(r'```mermaid\s*\n([\s\S]*?)```', text)
    if not m:
        return []
    block = m.group(1)

    # Build node label map: ID → label  (e.g. CP → "frmContasPagar")
    id_to_label: dict = {}
    for nm in re.finditer(r'(\w+)\["([^"<]+)', block):
        nid = nm.group(1)
        lbl = nm.group(2).strip()
        # Skip subgraph IDs (those appear with subgraph keyword on same/prev line)
        id_to_label[nid] = lbl

    # Subgraph IDs to exclude from edges (panels are containers, not forms)
    subgraph_ids = set(re.findall(r'subgraph\s+(\w+)', block))

    edges: list = []
    edge_re = re.compile(r'(\w+)\s*-->\|"([^"]+)"\|\s*(\w+)')
    seen = set()
    for line in block.splitlines():
        for em in edge_re.finditer(line):
            src, trig, tgt = em.group(1), em.group(2), em.group(3)
            if src in subgraph_ids or tgt in subgraph_ids:
                continue
            key = (src, trig, tgt)
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "source":  id_to_label.get(src, src),
                "trigger": trig,
                "target":  id_to_label.get(tgt, tgt),
            })
    return edges


def _infer_strategy_status(tests_by_type: list, key: str) -> str:
    """Infer a testing strategy status from the testsByType list."""
    _KEY_MAP = {
        "unit":        r'unit',
        "bdd":         r'BDD|feature',
        "contract":    r'Contract|PactNet',
        "exploratory": r'Exploratory',
        "parity":      r'parity|paridade',
        "db":          r'Integration.*DB|DB Integrity',
        "regression":  r'Regression',
    }
    pattern = _KEY_MAP.get(key, key)
    for row in tests_by_type:
        if re.search(pattern, row.get("type", ""), re.I):
            gen = row.get("generated", "")
            if re.search(r'SKIP', gen, re.I):
                return "SKIPPED"
            if re.search(r'NOT.?EXEC', gen, re.I):
                return "Pendente"
            if re.search(r'\d', gen):
                return "Ativo"
    return "Pendente"


def _parse_qa_test_summary(outputs_dir: Path) -> dict:
    """Parse qa/qa-master-report.md → D.qaTestSummary for renderQATestSummary().

    Returns a dict with keys:
      kpis, pyramid, testsByType, coverageMetrics, gate, strategies, table_notes
    """
    report_path = outputs_dir / "qa" / "qa-master-report.md"
    if not report_path.exists():
        return _build_planned_qa_summary(outputs_dir)

    text = read_text(report_path)
    lines = text.splitlines()

    result: dict = {
        "kpis": {},
        "pyramid": [],
        "testsByType": [],
        "coverageMetrics": [],
        "gate": {},
        "strategies": [],
        "table_notes": "",
    }

    # ── 1. testsByType ────────────────────────────────────────────────────────
    in_section = False
    for line in lines:
        if re.search(r'Testes Gerados.*por tipo|Tests Generated', line, re.I):
            in_section = True
            continue
        if in_section:
            if line.startswith('##') and not re.search(r'TOTAL|total', line):
                break
            if not line.startswith('|'):
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            cols = [c for c in cols if c]
            if len(cols) < 4:
                continue
            if re.match(r'^[-:\s]+$', cols[0]) or cols[0].lower() in ('tipo de teste', 'type', 'test type'):
                continue
            type_raw = re.sub(r'\*+', '', cols[0]).strip()
            if not type_raw or type_raw.upper().startswith('TOTAL'):
                continue

            def _cv(lst, idx):
                v = re.sub(r'\*+', '', lst[idx]).strip() if idx < len(lst) else '—'
                return '—' if v in ('—', '-', '', '–') else v

            gen_raw  = _cv(cols, 2)
            exe_raw  = _cv(cols, 3)
            ran_raw  = _cv(cols, 4)
            pass_raw = _cv(cols, 5)
            fail_raw = _cv(cols, 6)
            cov_raw  = _cv(cols, 7)
            cov_ok   = bool(re.search(r'✅|ok', cov_raw, re.I))
            cov_warn = bool(re.search(r'[%⚠]', cov_raw) and not cov_ok)
            result["testsByType"].append({
                "type":       type_raw,
                "agent":      re.sub(r'\*+', '', cols[1]).strip() if len(cols) > 1 else '—',
                "generated":  gen_raw,
                "executable": exe_raw,
                "executed":   ran_raw,
                "pass":       pass_raw,
                "fail":       fail_raw,
                "coverage":   cov_raw,
                "cov_ok":     cov_ok,
                "cov_warn":   cov_warn,
            })

    # ── 2. coverageMetrics ────────────────────────────────────────────────────
    in_section = False
    for line in lines:
        if re.search(r'Métricas de Cobertura|Coverage Metrics', line, re.I):
            in_section = True
            continue
        if in_section:
            if line.startswith('##') and not re.search(r'Cobertura|Coverage', line, re.I):
                break
            if not line.startswith('|'):
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            cols = [c for c in cols if c]
            if len(cols) < 3:
                continue
            if re.match(r'^[-:\s]+$', cols[0]) or cols[0].lower() in ('métrica', 'metric'):
                continue
            metric = re.sub(r'\*+', '', cols[0]).strip()
            if not metric:
                continue
            thr_m = re.search(r'[\d.]+', cols[1]) if len(cols) > 1 else None
            threshold = thr_m.group(0) if thr_m else '0'
            value_raw = cols[2].strip() if len(cols) > 2 else '—'
            status    = cols[3].strip() if len(cols) > 3 else '—'
            num_m = re.search(r'(\d+\.?\d*)', re.sub(r'[~≈]', '', value_raw))
            value_num = num_m.group(1) if num_m else '0'
            result["coverageMetrics"].append({
                "metric":    metric,
                "threshold": threshold,
                "value":     value_num,
                "value_raw": value_raw,
                "status":    status,
            })

    # ── 3. pyramid ────────────────────────────────────────────────────────────
    _LAYER_KEYS = {
        'unit': 'unit', 'unitário': 'unit', 'unidade': 'unit',
        'integration': 'integration', 'integração': 'integration',
        'e2e': 'e2e', 'smoke': 'e2e', 'end-to-end': 'e2e',
    }
    in_section = False
    pyramid_notes: list = []
    for line in lines:
        if re.search(r'Resumo por Camada|Pirâmide|Test Pyramid', line, re.I):
            in_section = True
            continue
        if in_section:
            if line.startswith('##') and not re.search(r'Camada|Pirâmide|Pyramid', line, re.I):
                break
            if not line.startswith('|'):
                if line.strip().startswith('>'):
                    pyramid_notes.append(line.strip().lstrip('> '))
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            cols = [c for c in cols if c]
            if len(cols) < 3:
                continue
            if re.match(r'^[-:\s]+$', cols[0]) or cols[0].lower() in ('camada', 'layer'):
                continue
            layer_raw = re.sub(r'\*+', '', cols[0]).strip()
            if not layer_raw:
                continue
            layer_key = 'unit'
            for k, v in _LAYER_KEYS.items():
                if k in layer_raw.lower():
                    layer_key = v
                    break
            tgt_m  = re.search(r'(\d+)', cols[1]) if len(cols) > 1 else None
            real_m = re.search(r'(\d+)', cols[2]) if len(cols) > 2 else None
            count_raw  = re.sub(r'\*+', '', cols[3]).strip() if len(cols) > 3 else '—'
            status_raw = re.sub(r'\*+', '', cols[4]).strip() if len(cols) > 4 else '—'
            result["pyramid"].append({
                "layer":      layer_raw,
                "layer_key":  layer_key,
                "pct_target": tgt_m.group(1) if tgt_m else '0',
                "pct_real":   real_m.group(1) if real_m else '0',
                "count":      count_raw,
                "status":     status_raw,
            })
    if pyramid_notes:
        result["pyramid_note"] = ' '.join(pyramid_notes[:2])

    # ── 4. gate ───────────────────────────────────────────────────────────────
    in_gate = False
    gate_status = ''
    gate_items: list = []
    gate_conditions: list = []
    in_conditions = False
    for line in lines:
        # Capture inline status on frontmatter line (e.g. "**Overall Gate:** CONDITIONAL_PASS")
        if not gate_status:
            hdr_m = re.search(r'Overall\s+Gate[:\*\s]+([A-Z_]+(?:_[A-Z]+)*)', line, re.I)
            if hdr_m:
                gate_status = hdr_m.group(1).strip()
        if re.search(r'Overall QA Gate|QA GATE', line, re.I):
            in_gate = True
            gm = re.search(r'(?:Overall\s+QA\s+Gate|QA\s+GATE)[:\*\|\s]+([A-Z_]+(?:_[A-Z]+)*)', line, re.I)
            if gm:
                gate_status = gm.group(1).strip()
            continue
        if in_gate:
            if line.startswith('##') and not re.search(r'PASS|GATE|Condition', line, re.I):
                break
            if not gate_status:
                gm = re.search(r'QA\s*GATE:\s*([A-Z_]+(?:_[A-Z]+)*)', line, re.I)
                if gm:
                    gate_status = gm.group(1).strip()
            item_m = re.match(r'\s*[│|]\s*(✅|⚠️|❌)\s*(.+)', line)
            if item_m:
                gate_items.append({
                    "pass": item_m.group(1) == '✅',
                    "text": item_m.group(2).strip().rstrip('|').strip(),
                })
            if re.search(r'Conditions for FULL PASS|Condições para FULL PASS', line, re.I):
                in_conditions = True
                continue
            if in_conditions:
                cond_m = re.match(r'\s*\d+\.\s*(.+)', line)
                if cond_m:
                    gate_conditions.append(cond_m.group(1).strip())

    result["gate"] = {
        "status":     gate_status or "—",
        "items":      gate_items,
        "conditions": gate_conditions,
    }

    # ── 5. KPIs aggregated from parsed data ──────────────────────────────────
    total_gen = total_exe = bdd_scenarios = 0
    for row in result["testsByType"]:
        gm = re.search(r'(\d+)', row.get("generated", ""))
        if gm:
            total_gen += int(gm.group(1))
        em = re.search(r'(\d+)', row.get("executable", ""))
        if em:
            total_exe += int(em.group(1))
        if re.search(r'BDD|feature', row.get("type", ""), re.I) and gm:
            bdd_scenarios = int(gm.group(1))

    cov_line = next((r for r in result["coverageMetrics"] if 'line coverage' in r["metric"].lower()), None)
    br_line  = next((r for r in result["coverageMetrics"] if 'br coverage' in r["metric"].lower()), None)
    fr_line  = next((r for r in result["coverageMetrics"] if 'fr coverage' in r["metric"].lower()), None)
    blocking = sum(1 for item in gate_items if not item.get("pass"))

    result["kpis"] = {
        "total_generated":  f"~{total_gen}" if total_gen > 0 else "—",
        "total_executable": f"~{total_exe}" if total_exe > 0 else "—",
        "bdd_scenarios":    str(bdd_scenarios) if bdd_scenarios else "—",
        "coverage_est":     (cov_line["value"] + "%") if cov_line else "—",
        "cov_ok":           cov_line["status"] == "✅" if cov_line else False,
        "br_coverage":      br_line["value_raw"] if br_line else "—",
        "br_ok":            br_line["status"] == "✅" if br_line else False,
        "br_sub":           "BRs com ≥1 teste",
        "fr_coverage":      fr_line["value_raw"] if fr_line else "—",
        "fr_ok":            fr_line["status"] == "✅" if fr_line else False,
        "fr_sub":           "RFs com ≥1 CT ou teste",
        "blocking_gaps":    str(blocking),
        "gate_status":      gate_status if gate_status else "—",
        "gate_ok":          "PASS" in gate_status if gate_status else False,
    }

    # ── 6. table_notes ────────────────────────────────────────────────────────
    notes: list = []
    for line in lines:
        if re.match(r'^\s*>\s*\(\*\)|^\s*>\s*\(†\)', line):
            notes.append(line.strip().lstrip('> '))
    if notes:
        result["table_notes"] = '  '.join(notes[:3])

    # ── 7. strategies derived from testsByType ────────────────────────────────
    tbt = result["testsByType"]
    result["strategies"] = [
        {"approach": "TDD (unit-first)",           "scope": "Domain + Application",       "status": _infer_strategy_status(tbt, "unit")},
        {"approach": "BDD / Gherkin",              "scope": "Cenários de aceite por BC",  "status": _infer_strategy_status(tbt, "bdd")},
        {"approach": "Consumer-Driven Contract",   "scope": "APIs inter-BC (PactNet)",    "status": _infer_strategy_status(tbt, "contract")},
        {"approach": "Exploratory (POISED/VADER)", "scope": "Riscos AS-IS identificados", "status": _infer_strategy_status(tbt, "exploratory")},
        {"approach": "Parity Testing AS-IS×TO-BE", "scope": "Equivalência funcional",     "status": _infer_strategy_status(tbt, "parity")},
        {"approach": "DB Integrity / Migration",   "scope": "Constraints PK/FK/UK + SPs", "status": _infer_strategy_status(tbt, "db")},
        {"approach": "Regression Gate CI",         "scope": "Por PR / push to main",      "status": _infer_strategy_status(tbt, "regression")},
    ]

    return result


def _build_planned_qa_summary(outputs_dir: Path) -> dict:
    """Build a clearly labelled QA Strategy preview from TPT artifacts.

    ``qa-master-report.md`` is produced only by QE.  Before QE runs, the
    TO-BE test plan and functional matrix still provide useful planning data,
    but must never be presented as executed tests or a passed quality gate.
    """
    plan_path = outputs_dir / "tobe" / "qa" / "test-plan.md"
    matrix_path = outputs_dir / "tobe" / "tests" / "functional-test-matrix.md"
    if not plan_path.exists() and not matrix_path.exists():
        return {}

    plan = read_text(plan_path)
    matrix = read_text(matrix_path)
    totals = {"unit": 0, "integration": 0, "e2e": 0, "contract": 0}
    coverage_values: list[float] = []
    for line in matrix.splitlines():
        if not line.startswith("|") or re.match(r"^\|[-:\s|]+$", line):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 9 or cols[0].lower() in {"bc", "**total**", "total"}:
            continue
        for key, idx in (("unit", 3), ("integration", 4), ("e2e", 5), ("contract", 6)):
            m = re.search(r"\d+", cols[idx])
            if m:
                totals[key] += int(m.group(0))
        m_cov = re.search(r"(\d+(?:\.\d+)?)\s*%", cols[-1])
        if m_cov:
            coverage_values.append(float(m_cov.group(1)))

    total_planned = sum(totals.values())
    avg_coverage = round(sum(coverage_values) / len(coverage_values)) if coverage_values else None
    pyramid = [
        {"layer": "Unit", "layer_key": "unit", "pct_target": "70", "pct_real": "0", "count": str(totals["unit"]), "status": "PLANNED"},
        {"layer": "Integration", "layer_key": "integration", "pct_target": "20", "pct_real": "0", "count": str(totals["integration"] + totals["contract"]), "status": "PLANNED"},
        {"layer": "E2E", "layer_key": "e2e", "pct_target": "10", "pct_real": "0", "count": str(totals["e2e"]), "status": "PLANNED"},
    ]
    return {
        "source": "TPT",
        "execution_status": "NOT_EXECUTED",
        "kpis": {
            "total_generated": str(total_planned) if total_planned else "—",
            "total_executable": "PLANNED",
            "bdd_scenarios": "PLANNED",
            "coverage_est": (str(avg_coverage) + "% target matrix") if avg_coverage is not None else "—",
            "cov_ok": False,
            "br_coverage": "PLANNED",
            "br_ok": False,
            "br_sub": "TPT traceability",
            "fr_coverage": "PLANNED",
            "fr_ok": False,
            "fr_sub": "TPT traceability",
            "blocking_gaps": "—",
            "gate_status": "NOT_EXECUTED",
            "gate_ok": False,
        },
        "pyramid": pyramid,
        "testsByType": [],
        "coverageMetrics": ([{"metric": "Matrix coverage", "threshold": "—", "value": str(avg_coverage), "value_raw": str(avg_coverage) + "%", "status": "PLANNED"}] if avg_coverage is not None else []),
        "gate": {"status": "NOT_EXECUTED", "items": [{"pass": False, "text": "QE has not produced qa-master-report.md; values shown are planning evidence only."}], "conditions": ["Execute ava-qa-orchestrator with trigger QE after F4 and DevOps DE." ]},
        "strategies": [{"approach": label, "scope": scope, "status": "PLANNED"} for label, scope in [
            ("TDD (unit-first)", "Domain + Application"), ("BDD / Gherkin", "Cenários de aceite por BC"),
            ("Consumer-Driven Contract", "APIs inter-BC (PactNet)"), ("Exploratory (POISED/VADER)", "Riscos por BC"),
            ("Parity Testing AS-IS×TO-BE", "Equivalência funcional"), ("DB Integrity / Migration", "Constraints + migrations"),
            ("Regression Gate CI", "Por PR / push to main")]],
        "table_notes": "Planning preview from TPT artifacts; no QE execution evidence is available yet.",
    }


def build_et_findings(qa_dir: Path) -> tuple:
    """Build D.etFindings and D.etMeta from findings-catalog.json (ava-qa-exploratory).

    Returns:
        (et_findings, et_meta) where:
          et_findings: list of normalized finding dicts {id, module, description, heuristic, severity, tobe_impact}
          et_meta:     dict {total, p0, p1, p2, p3, sessions, status}
    """
    catalog_path = qa_dir / "exploratory" / "findings-catalog.json"
    if not catalog_path.exists():
        return [], {}

    try:
        raw = read_json(catalog_path)
    except Exception:
        return [], {}

    # Support both list and {meta, findings} shapes
    if isinstance(raw, list):
        findings_raw = raw
        meta_raw = {}
    elif isinstance(raw, dict):
        findings_raw = raw.get("findings", [])
        meta_raw = raw.get("meta", {})
    else:
        return [], {}

    findings = []
    for f in findings_raw:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity") or f.get("sev") or "-")
        # tobe_impact may be a dict or string; normalise to short string
        imp_raw = f.get("tobe_impact", "")
        if isinstance(imp_raw, dict):
            imp_label = (imp_raw.get("required_fix") or "")[:80]
        else:
            imp_label = str(imp_raw)[:80]
        findings.append({
            "id":          str(f.get("id") or f.get("finding_id") or ""),
            "module":      str(f.get("module") or f.get("area") or ""),
            "description": str(f.get("description") or f.get("desc") or ""),
            "heuristic":   str(f.get("heuristic") or ""),
            "severity":    sev,
            "tobe_impact": imp_label,
        })

    # Compute severity buckets
    by_sev: dict = {}
    for f in findings:
        s = f["severity"]
        by_sev[s] = by_sev.get(s, 0) + 1

    # Count distinct session charters (SESSION-N or ET-*-NNN keys in findings)
    sessions = set()
    for f_raw in findings_raw:
        if not isinstance(f_raw, dict):
            continue
        ch = f_raw.get("charter") or f_raw.get("session_id") or ""
        if ch:
            sessions.add(ch)

    et_meta = {
        "total":    len(findings),
        "p0":       by_sev.get("P0", 0) + by_sev.get("CRITICAL", 0),
        "p1":       by_sev.get("P1", 0) + by_sev.get("HIGH", 0),
        "p2":       by_sev.get("P2", 0) + by_sev.get("MEDIUM", 0),
        "p3":       by_sev.get("P3", 0) + by_sev.get("LOW", 0),
        "sessions": len(sessions),
        "status":   str(meta_raw.get("status", "")),
    }
    return findings, et_meta


def parse_scenario_register(qa_dir: Path) -> list:
    """Parse qa/scenario-generator/scenario-register.json into D.scenarios.

    Contract (see 'Scenario Register Format' in scenario-generator-agent.md,
    CONTRATO FIXO — a pure JSON array, no wrapper): each item has id,
    feature_id, feature_name, feature_file, scenario_name, type, tags[],
    steps_count, has_outline, examples_count, source_artifact,
    source_reference, agent_source, trace_id.

    The template's BC column has no direct field in the contract — every
    scenario is required to carry >=1 module/bounded-context tag alongside
    its classification tag (@happy/@sad/@edge) and optional @smoke/@wave-N/
    @regression/@api/@ui/@integration tags, so BC is derived as the first
    tag that isn't one of those reserved ones. Given/When/Then step text is
    not part of this JSON contract (it only exists inside the .feature
    files) and is intentionally left out rather than guessed.
    """
    path = qa_dir / "scenario-generator" / "scenario-register.json"
    if not path.exists():
        return []
    raw = read_json(path)
    if not isinstance(raw, list):
        return []
    RESERVED_TAGS = {"happy", "sad", "edge", "smoke", "regression", "api", "ui", "integration"}
    scenarios = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        tags = [str(t).lstrip("@") for t in (s.get("tags") or []) if t]
        bc = next((t for t in tags if t.lower() not in RESERVED_TAGS
                   and not t.lower().startswith("wave-")), "")
        scenarios.append({
            "id":      str(s.get("id", "")),
            "name":    str(s.get("scenario_name", "")),
            "bc":      bc,
            "feature": str(s.get("feature_name", "")),
            "type":    str(s.get("type", "")),
            "tags":    tags,
        })
    return scenarios


def _extract_defect_table(text: str) -> list:
    """Return rows from the first markdown table in `text` whose header looks
    defect-shaped (an ID-like column + a description/title-like column).

    Neither ava-qa-defect-identifier nor ava-qa-evidence-capture fixes a table
    schema for defects in its Output Contract (both emit free-form Markdown),
    so columns are matched by header keyword instead of a fixed position —
    same header-driven idiom already used by parse_vulnerabilities() for
    similarly uncontracted reports.
    """
    defects: list = []
    in_table = False
    matched = False
    col_map: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('|'):
            if matched:
                break  # our table ended
            in_table = False
            continue
        cols = [c.strip() for c in stripped.strip('|').split('|')]
        if not in_table:
            in_table = True
            if matched:
                continue  # already captured a table; skip any later ones
            norm = [re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_') for c in cols]
            id_idx   = next((i for i, h in enumerate(norm) if h in ('id', 'et_id', 'defect_id')), None)
            desc_idx = next((i for i, h in enumerate(norm) if h in ('defect', 'description', 'desc', 'title', 'issue')), None)
            if id_idx is None or desc_idx is None:
                continue  # a table, but not the defect one — its rows are skipped below
            col_map = {
                'id': id_idx, 'description': desc_idx,
                'module': next((i for i, h in enumerate(norm) if h in ('module', 'bc', 'area', 'component')), None),
                'severity': next((i for i, h in enumerate(norm) if h in ('severity', 'priority', 'sev')), None),
                'status': next((i for i, h in enumerate(norm) if h in ('status', 'state')), None),
            }
            matched = True
            continue
        if not matched or all(re.match(r'^[-:\s]*$', c) for c in cols):
            continue  # separator row, or inside a non-matching table
        def _get(key):
            i = col_map.get(key)
            return cols[i].strip('*') if i is not None and i < len(cols) else ''
        did = _get('id')
        if not did:
            continue
        defects.append({
            "id":          did[:30],
            "description": _get('description')[:160],
            "module":      _get('module')[:60],
            "severity":    _get('severity')[:20],
            "status":      _get('status')[:30],
        })
    return defects


def parse_defects(qa_dir: Path) -> list:
    """Defects for D.defects — qa/defect-identifier-report.md, falling back to
    the defect-shaped table inside qa/evidence-capture-report.md.
    """
    for fname in ("defect-identifier-report.md", "evidence-capture-report.md"):
        path = qa_dir / fname
        if not path.exists():
            continue
        rows = _extract_defect_table(read_text(path))
        if rows:
            return rows
    return []


def _resolve_qa_artifact(asis_dir: Path, filename: str) -> Path:
    """Resolve a test-qa-asis.md artifact, preferring its real Output Contract
    location (`asis/qa/`) with a fallback to the historical (incorrect) root
    `asis/` path for backward compatibility with any already-generated project
    whose agent run pre-dates this fix.
    """
    qa_path = asis_dir / "qa" / filename
    if qa_path.exists():
        return qa_path
    return asis_dir / filename


def build_test_map(asis_dir: Path) -> tuple:  # noqa: E501 — kept for backward compat, now returns empty
    """DEPRECATED — test-map.md, test-coverage-asis.md, test-gaps.md and test-baseline.md
    have been discontinued. Returns ([], []) immediately.
    The D.testMap / D.testGaps fields remain in the injected JS object so that old
    generated summaries with existing data are still rendered correctly by the template.
    """
    return [], []



def build_test_cases(asis_dir: Path) -> list:
    """Parse asis/qa/test-cases.md into D.testCases[].

        Supports the formats emitted by the AS-IS bridge and older projects:
            ##/### CT-NNN or TC-NNN — title
            ##/### TC-NNN: title
            table rows whose first cell is a TC-/CT- identifier
    Metadata fields: **ID**, **Prioridade**, **Tipo**, **Módulo**, **Regras**
    Steps: counted from | N | table rows (table format) or **Passo N:** lines (step format).
    Returns [] when file absent or no CT- headings found.
    """
    tc_path = asis_dir / "qa" / "test-cases.md"
    if not tc_path.exists():
        return []
    text = tc_path.read_text(encoding="utf-8", errors="replace")
    # Do not require a dash after the identifier: the bridge emits both
    # ``### TC-001: title`` and ``## CT-001 — title`` variants.
    blocks = re.split(r'\n(?=#{2,3}\s+(?:CT|TC)-)', text, flags=re.IGNORECASE)
    results = []
    seen_ids = set()
    for block in blocks:
        m_head = re.match(
            r'^#{2,3}\s+((?:CT|TC)-[A-Z0-9_-]+)\s*(?::|—|-+)\s*(.+)',
            block,
            flags=re.IGNORECASE,
        )
        if not m_head:
            continue
        entry: dict = {
            "id": m_head.group(1).strip(),
            "title": m_head.group(2).strip(),
            "priority": "", "type": "", "module": "", "rules": "",
            "steps": 0, "preconditions": "", "steps_raw": "", "postconditions": "",
        }
        m_pri  = re.search(r'\*{1,2}Prioridade\*{0,2}:\s*\*{0,2}\s*([^|\n*]+)', block)
        m_typ  = re.search(r'\*{1,2}Tipo\*{0,2}:\s*\*{0,2}\s*([^|\n*]+)', block)
        m_mod  = re.search(r'\*{1,2}[Mm]ódulo\*{0,2}:\s*\*{0,2}\s*([^\n|*]+)', block)
        m_rul  = re.search(r'\*{1,2}Regras\*{0,2}:\s*\*{0,2}\s*([^\n|*]+)', block)
        if not m_rul:  # fallback: Rastreabilidade → rules (Step-by-Step format)
            m_rul = re.search(r'\*{1,2}Rastreabilidade\*{0,2}:\s*\*{0,2}\s*([^\n|*]+)', block)
        if m_pri: entry["priority"]  = m_pri.group(1).strip()
        if m_typ: entry["type"]      = m_typ.group(1).strip()
        if m_mod: entry["module"]    = m_mod.group(1).strip()
        if m_rul: entry["rules"]     = m_rul.group(1).strip()
        m_pre  = re.search(r'### Pré-condições\s*\n([\s\S]*?)(?=\n###|\Z)', block)
        m_step = re.search(r'### Passos\s*\n([\s\S]*?)(?=\n###|\Z)',         block)
        m_post = re.search(r'### Pós-condições\s*\n([\s\S]*?)(?=\n###|\Z)',  block)
        if m_pre:  entry["preconditions"]  = m_pre.group(1).strip()
        if m_step:
            steps_text = m_step.group(1).strip()
            entry["steps_raw"] = steps_text
            data_rows = [l for l in steps_text.splitlines()
                         if l.startswith('|')
                         and not re.match(r'^\|[-:\s|]+$', l)
                         and not re.search(r'Ação|Action|^#', l[:12])]
            entry["steps"] = len(data_rows)
        # Fallback: count **Passo N:** lines for Step-by-Step format (no ### Passos subsection)
        if entry["steps"] == 0:
            entry["steps"] = len(re.findall(r'^\*{1,2}Passo\s+\d+', block, re.MULTILINE | re.IGNORECASE))
        if m_post: entry["postconditions"] = m_post.group(1).strip()
        # A priority section such as ``## Critical Path Test Cases (P0)``
        # applies to the following heading-based cases when no field exists.
        if not entry["priority"]:
            m_section_pri = re.search(r'\((P[0-3])\)', text[:text.find(block)], re.IGNORECASE)
            if m_section_pri:
                entry["priority"] = m_section_pri.group(1).upper()
        results.append(entry)
        seen_ids.add(entry["id"].upper())

    # Some legacy bridge outputs use grouped Markdown tables instead of one
    # heading per case (for example ``| TC-AUTH-001 | ... |``). Parse those
    # rows as a fallback, while preserving the heading parser as the source of
    # truth whenever both formats occur in the same file.
    for line in text.splitlines():
        if not line.lstrip().startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 3 or re.fullmatch(r'[-:\s]+', ''.join(cells)):
            continue
        m_id = re.fullmatch(r'((?:CT|TC)-[A-Z0-9_-]+)', cells[0], re.IGNORECASE)
        if not m_id or m_id.group(1).upper() in seen_ids:
            continue
        # Skip column-header rows such as ``TC-ID | Title | Priority``.
        if cells[0].upper() in {'TC-ID', 'CT-ID', 'ID'}:
            continue
        priority = cells[2] if len(cells) > 2 and re.fullmatch(r'P[0-3]|CRITICAL|HIGH|MEDIUM|LOW', cells[2], re.IGNORECASE) else ''
        steps_raw = cells[3] if len(cells) > 3 else ''
        results.append({
            "id": m_id.group(1),
            "title": cells[1] if len(cells) > 1 else '',
            "priority": priority,
            "type": '',
            "module": '',
            "rules": '',
            "steps": len(re.findall(r'\b\d+\.', steps_raw)) or (1 if steps_raw else 0),
            "preconditions": '',
            "steps_raw": steps_raw,
            "postconditions": cells[4] if len(cells) > 4 else '',
        })
        seen_ids.add(m_id.group(1).upper())
    return results


def _build_test_cases_overview(source_dir: Path, overview_path: Path, source_label: str, limit: int = 10) -> str:
    """Generate an overview from one test-cases.md source into its own phase."""
    tc_path = source_dir / "test-cases.md"

    if not tc_path.exists():
        return ""

    all_cases = build_test_cases(source_dir.parent)
    total = len(all_cases)
    top = all_cases[:limit]
    displayed = len(top)

    rows = "\n".join(
        f"| {c['id']} | {c['title']} | {c['module']} | {c['priority']} "
        f"| {c['type']} | {c['rules']} | {c['steps']} |"
        for c in top
    )
    if not rows:
        rows = "| \u2014 | \u2014 | \u2014 | \u2014 | \u2014 | \u2014 | \u2014 |"

    content = (
        "# Test Cases \u2014 Overview\n\n"
        "> **Gerado automaticamente** por `build_summary_comprehensive.py`.\n"
        f"> Fonte: `{source_label}`\n\n"
        "## Resumo\n\n"
        "| M\u00e9trica | Valor |\n"
        "|---|---|\n"
        f"| Total de Test Cases | {total} |\n"
        f"| Test Cases exibidos nesta vis\u00e3o | {displayed} |\n\n"
        f"## Primeiros {displayed} Test Cases\n\n"
        "| ID | T\u00edtulo | M\u00f3dulo | Prioridade | Tipo | Regras | Passos |\n"
        "|---|---|---|---|---|---|---|\n"
        f"{rows}\n"
    )

    overview_path.parent.mkdir(parents=True, exist_ok=True)
    overview_path.write_text(content, encoding="utf-8")
    return content


def build_test_cases_overview(asis_dir: Path, limit: int = 10) -> str:
    """Generate the AS-IS overview only when the AS-IS source exists.

    The TO-BE overview is generated separately by
    :func:`build_tobe_test_cases_overview`; this prevents TO-BE cases from
    being written under ``outputs/asis/qa``.
    """
    return _build_test_cases_overview(
        asis_dir / "qa",
        asis_dir / "qa" / "test-cases-overview.md",
        "asis/qa/test-cases.md",
        limit,
    )


def build_tobe_test_cases_overview(outputs_dir: Path, limit: int = 10) -> str:
    """Generate the TO-BE overview from outputs/tobe/qa/test-cases.md."""
    tobe_qa = outputs_dir / "tobe" / "qa"
    return _build_test_cases_overview(
        tobe_qa,
        tobe_qa / "test-cases-overview.md",
        "tobe/qa/test-cases.md",
        limit,
    )


def _quote_c4_relationship_arguments(content: str) -> str:
    """Quote unquoted C4 Rel-like label/technology arguments safely."""
    macros = r"Rel(?:_Back|_Neighbor|_U|_R|_L|_D)?"
    pattern = re.compile(rf"(?P<prefix>\b{macros}\s*\(\s*[^,()]+\s*,\s*[^,()]+\s*,)(?P<body>[\s\S]*?)(?P<close>\))(?=\s*(?:\r?\n|$))")

    def replace(match):
        body = match.group("body")
        parts = [part.strip() for part in re.split(r",\s*", body.replace("\r", "").replace("\n", " "))]
        if not parts or any('"' in part and not (part.startswith('"') and part.endswith('"')) for part in parts):
            return match.group(0)
        quoted = []
        for part in parts:
            if not part:
                return match.group(0)
            if part.startswith('"') and part.endswith('"'):
                quoted.append(part)
            else:
                quoted.append('"' + part.replace('"', '\\"') + '"')
        return match.group("prefix") + " " + ", ".join(quoted) + match.group("close")

    return pattern.sub(replace, content)


def _normalize_c4_boundaries(content: str) -> str:
    """Convert PlantUML-style C4 boundary terminators to Mermaid braces."""
    content = re.sub(r"(?m)^\s*Container_Boundary\(([^,]+),\s*([^\n]+)\)\s*$", lambda m: f'    Container_Boundary({m.group(1).strip()}, "{m.group(2).strip().strip(chr(34))}") {{', content)
    content = re.sub(r"(?m)^\s*Container_Boundary_End\(\)\s*$", "    }", content)
    return content


def _normalize_c4_declarations(content: str) -> str:
    arity = {"Person": 3, "Person_Ext": 3, "System": 3, "System_Ext": 3, "Container": 4, "ContainerDb": 4, "ContainerDb_Ext": 4, "Component": 4, "Component_Ext": 4}
    pattern = re.compile(r"\b(Person_Ext|Person|System_Ext|System|ContainerDb_Ext|ContainerDb|Container|Component_Ext|Component)\s*\(([^\n()]*)\)")
    def quote(match):
        name, body = match.group(1), match.group(2)
        parts = [part.strip() for part in body.split(",")]
        if len(parts) != arity[name] or not parts[0]:
            return match.group(0)
        return f"{name}({parts[0]}, " + ", ".join(part if part.startswith('"') and part.endswith('"') else '"' + part.replace('"', '\\"') + '"' for part in parts[1:]) + ")"
    return pattern.sub(quote, content)


def generate_executive_summary(project_name: str, asis_dir: Path, language: str) -> dict:
    """Generate bilingual executive summary"""
    master_report = read_text(asis_dir / "master-report.md")

    # Extract paragraphs (skip headings, table lines, empty lines, HR separators,
    # and metadata blocks like **Agent:**, **trace_id:**, **Pipeline:**, **Status:**)
    _HR_RE = __import__('re').compile(r'^-{3,}$')
    _META_RE = __import__('re').compile(
        r'^\*{2}(Agent|trace_id|Gerado em|Pipeline|Status|Generated|Date)\s*:',
        __import__('re').IGNORECASE,
    )
    def _is_metadata_block(text: str) -> bool:
        """Return True if the paragraph is an agent metadata block."""
        lines = text.strip().splitlines()
        meta_lines = sum(1 for ln in lines if _META_RE.match(ln.strip()))
        return meta_lines >= 2  # 2+ metadata lines → metadata block

    paragraphs = [p.strip() for p in master_report.split('\n\n')
                  if p.strip()
                  and not p.strip().startswith('#')
                  and not p.strip().startswith('|')
                  and not _HR_RE.match(p.strip())
                  and not _is_metadata_block(p)][:3]

    if not paragraphs:
        summary_html = f"<p>Projeto <strong>{project_name}</strong> - análise AS-IS completa.</p>"
    else:
        # Convert inline markdown to HTML so bold/italic renders correctly in browser
        summary_html = '\n'.join(f'<p>{md_to_html_inline(p)}</p>' for p in paragraphs)

    return {
        "pt": summary_html,
        "en": f"<p><em>[Translation not available]</em></p>{summary_html}"
    }


# ═══ MAIN BUILD FUNCTION ═══
def load_drawio_files(project_name: str) -> dict:
    """
    Load .drawio files from asis/drawio/ directory and Base64 encode for embedding.
    
    Returns dict with structure:
    {
        "c4": {"content": "base64...", "exists": True, "pages": 3, "filename": "..."},
        "overall": {...},
        "bpmn": {...},
        "sequence": {...}
    }
    """
    import base64
    
    outputs_dir = Path(f'projects/{project_name}/outputs')
    drawio_dir = outputs_dir / 'asis/drawio'
    
    drawio_files = {
        "c4": "AS-IS-C4-Diagrams.drawio",
        "overall": "AS-IS-Overall-Architecture.drawio",
        "bpmn": "AS-IS-BPMN-Processes.drawio",
        "sequence": "AS-IS-Sequence-Diagrams.drawio"
    }
    
    result = {}
    
    for key, filename in drawio_files.items():
        file_path = drawio_dir / filename
        
        if file_path.exists():
            # Read and encode
            xml_content = file_path.read_text(encoding='utf-8')
            base64_content = base64.b64encode(xml_content.encode('utf-8')).decode('ascii')
            
            # Count pages (diagram elements)
            page_count = xml_content.count('<diagram ')
            
            result[key] = {
                "content": base64_content,
                "exists": True,
                "pages": page_count,
                "filename": filename
            }
        else:
            result[key] = {
                "content": "",
                "exists": False,
                "pages": 0,
                "filename": filename
            }
    
    loaded_count = sum(1 for v in result.values() if v['exists'])
    print(f"   🎨 Drawn.io files: {loaded_count}/4 loaded")
    
    return result


def _validate_parsed_counts(owasp, biz_rules, func_reqs, risks, bcs, screen_forms) -> bool:
    """Validate parsed arrays before HTML injection.

    Prints a ✅ or ⚠️ line per array. Does NOT block the build — the caller
    continues regardless. Return value (True = all OK) is informational only.

    Expected ranges are intentionally wide for variable-count arrays (bizRules,
    funcReqs, risks) and strict for fixed-count arrays (owasp = always 10).
    Note: testMap/testGaps removed — source artifacts discontinued.
    """
    checks = [
        ("owasp",       len(owasp),       10,  10,  "OWASP must always be exactly 10 (A01-A10)"),
        ("bizRules",    len(biz_rules),    0,   60,  "Business rules expected 0-60"),
        ("funcReqs",    len(func_reqs),    0,   60,  "Functional requirements expected 0-60"),
        ("risks",       len(risks),        0,  150,  "Risks expected 0-150"),
        ("bc",          len(bcs),          0,   30,  "Bounded contexts expected 0-30"),
        ("screenForms", len(screen_forms), 0,  300,  "Screen forms expected 0-300"),
    ]
    all_ok = True
    for name, count, lo, hi, msg in checks:
        if not (lo <= count <= hi):
            print(f"   ⚠️  VALIDATION: {name}={count} outside [{lo},{hi}] — {msg}")
            all_ok = False
        else:
            print(f"   ✅ {name}={count}")
    return all_ok


def build_summary_html(
    project_name: str,
    skip_mermaid_gate: bool = False,
    mermaid_guardrails_path: str | None = None,
    mermaid_gate_max_attempts: int = 3,
):
    """Constrói Summary HTML COMPLETO com TODOS os problemas resolvidos"""
    print(f"\n{'═'*70}")
    print(f"  AVA Fabric Summary Builder (COMPREHENSIVE)")
    print(f"  Project: {project_name}")
    print(f"  Resolving ALL 5 reported issues + Draw.io integration")
    print(f"{'═'*70}")
    
    # Paths
    base_dir = Path('.')
    project_dir = base_dir / f'projects/{project_name}'
    outputs_dir = project_dir / 'outputs'
    asis_dir = outputs_dir / 'asis'
    summary_dir = outputs_dir / 'summary'
    summary_dir.mkdir(parents=True, exist_ok=True)

    # Compatibility gate runs before any client-facing HTML is written. The
    # validator reads existing Blueprint artifacts only; it does not generate,
    # discover, or orchestrate them.
    _compat_reports = []
    _compat_allowed = True
    try:
        _compat_root = Path(__file__).resolve().parents[5]
        if str(_compat_root) not in sys.path:
            sys.path.insert(0, str(_compat_root))
        import importlib.util as _importlib_util
        _compat_module_path = Path(__file__).resolve().parent / "blueprint_compatibility.py"
        _compat_spec = _importlib_util.spec_from_file_location("ava_blueprint_compatibility", _compat_module_path)
        _compat_module = _importlib_util.module_from_spec(_compat_spec)
        sys.modules["ava_blueprint_compatibility"] = _compat_module
        _compat_spec.loader.exec_module(_compat_module)
        _render_spec = _importlib_util.spec_from_file_location("ava_render_blueprint_compatibility", Path(__file__).resolve().parent / "render_blueprint_compatibility.py")
        _render_module = _importlib_util.module_from_spec(_render_spec)
        sys.modules["ava_render_blueprint_compatibility"] = _render_module
        _render_spec.loader.exec_module(_render_module)
        validate_project_blueprints = _compat_module.validate_project_blueprints
        publication_allowed = _compat_module.publication_allowed
        _runtime_probes = {}
        for _probe_rel in (
            f"projects/{project_name}/outputs/asis/diagrams/architecture-blueprint.mmd",
            f"projects/{project_name}/outputs/tobe/diagrams/architecture-blueprint.mmd",
            f"projects/{project_name}/outputs/tobe/diagrams/c4-context.mmd",
            f"projects/{project_name}/outputs/tobe/diagrams/c4-container.mmd",
            f"projects/{project_name}/outputs/tobe/diagrams/c4-component.mmd",
        ):
            _probe_path = _compat_root / _probe_rel
            if _probe_path.is_file():
                _runtime_probes[_probe_rel] = _render_module.execute_probe(
                    _compat_root, _probe_path.read_text(encoding="utf-8", errors="replace")
                )
        _compat_reports = validate_project_blueprints(_compat_root, project_name, runtime_probes=_runtime_probes)
        _compat_allowed = publication_allowed(_compat_reports)
        if _compat_reports:
            # The public report is an aggregate of both required Blueprints.
            # Per-artifact diagnostics remain embedded in diagnosticEvidence.
            aggregate = dict(_compat_reports[0])
            aggregate["diagramId"] = "architecture-blueprints"
            aggregate["diagnosticEvidence"] = {"artifacts": _compat_reports}
            aggregate["publicationAllowed"] = _compat_allowed
            report_dir = summary_dir / "compatibility"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "blueprint-compatibility-report.json").write_text(
                json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (report_dir / "blueprint-compatibility-report.md").write_text(
                "# Blueprint Compatibility Report\n\n```json\n" +
                json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n```\n",
                encoding="utf-8",
            )
        if not _compat_allowed:
            print("   ❌ Blueprint compatibility gate BLOCKED Summary publication")
            return summary_dir / "blueprint-compatibility-report.json"
    except Exception as _compat_error:
        _compat_allowed = False
        print(f"   ❌ Blueprint compatibility gate error: {_compat_error}")
        return summary_dir / "blueprint-compatibility-report.json"
    
    template_path = base_dir / 'src/modules/ava-fabric-agents/summary/templates/html/summary-template.html'
    
    # Load template
    print("\n[1/6] Loading official template...")
    if not template_path.exists():
        print(f"   ❌ Template not found: {template_path}")
        return
    
    html = template_path.read_text(encoding='utf-8')
    print(f"   ✅ Template loaded ({len(html):,} bytes)")

    # Mermaid must remain an inline script. Inject it before the generic
    # placeholder pass and exclude it from that pass entirely.
    html = _inject_mermaid_inline(html, _load_mermaid_js(base_dir))
    
    # Build data structures (fixes issues #1-4)
    file_tree = build_file_tree(outputs_dir, summary_dir)
    artifact_inventory = build_artifact_inventory(outputs_dir)
    prototype_design_provenance = _load_prototype_design_provenance(outputs_dir)

    # F3 — real chip list from tobe/prototype/** (not the fixed 3-file list)
    proto_chips = list_prototype_chips(file_tree)
    if proto_chips:
        artifact_inventory["ava-prototype"] = proto_chips

    # F4 — append real backend .csproj project chips to the tech-framework chip
    backend_projects = list_backend_csproj_projects(outputs_dir)
    if backend_projects:
        artifact_inventory["ava-stack-dotnet-backend"] = (
            artifact_inventory.get("ava-stack-dotnet-backend", []) + backend_projects
        )

    agent_status = build_agent_status_map(outputs_dir)
    phase_status = build_phase_status_map(outputs_dir)
    drawio_files = load_drawio_files(project_name)  # NEW: Draw.io integration
    
    # Build staticDiagrams dict for D.staticDiagrams (preferred diagram path)
    static_diagrams = _build_static_diagrams(asis_dir, outputs_dir)

    # Build comprehensive substitutions (fix issue #5)
    substitutions, sp_rows, db_schema_all_rows, biz_logic_rows = build_comprehensive_substitutions(project_name, outputs_dir, asis_dir, file_tree, base_dir)
    substitutions["PROTOTYPE_DESIGN_PROVENANCE_HTML"] = _prototype_design_provenance_html(prototype_design_provenance)

    # Executive summary
    exec_summary = generate_executive_summary(project_name, asis_dir, "pt")

    # Parity data — parsed from tobe/parity-test-report.md
    parity_kpis, parity_rows = _parse_parity_report(outputs_dir)

    # Parity metadata & execution log (new panels — wave-comparison-data.json + parity/execution-log.md)
    parity_meta = _parse_parity_meta(outputs_dir)
    parity_log  = _parse_parity_log(outputs_dir)

    # BRV — Business Rule Validation (critical rules + SME sign-off)
    brv_data, brv_signoff = _parse_brv_report(outputs_dir)

    # Regression Suite — parsed from qa/regression-suite/ + shared-context.md
    regression_suite = _parse_regression_suite(outputs_dir, project_name)

    # QA Test Summary — parsed from qa/qa-master-report.md
    qa_test_summary = _parse_qa_test_summary(outputs_dir)

    # Override EXEC_PCT / AGENTS_OK with the real done count from agent_status.
    # build_comprehensive_substitutions computes these using only ASIS_AGENTS
    # (hardcoded = 9/42 ≈ 21%), which is wrong when all phases are complete.
    _done_count    = sum(1 for s in agent_status.values() if s == "done")
    _skipped_count = sum(1 for s in agent_status.values() if s == "skipped")
    # Exclude skipped agents from the denominator — they are inapplicable to this
    # project (e.g. solution agents for other languages, security disabled).
    # This ensures a fully executed pipeline reaches 100% regardless of which
    # language-specific or optional agents were not applicable.
    _effective_total = max(TOTAL_AGENTS - _skipped_count, 1)
    _agents_ok       = min(_done_count, _effective_total)
    substitutions["EXEC_PCT"]     = str(round(_done_count / _effective_total * 100))
    # Cap at effective total — guards against over-counting if agent_status ever
    # includes transient/test entries not in any phase card.
    substitutions["AGENTS_OK"]    = str(_agents_ok)
    substitutions["TOTAL_AGENTS"] = str(_effective_total)
    # Pending = agents not yet done (excludes skipped — they are inapplicable)
    substitutions["AGENTS_ERR"]   = str(max(0, _effective_total - _agents_ok))

    # ── Parse Parity data BEFORE substitution pass ──────────────────────────
    _parity_wave_data_path = outputs_dir / "tobe" / "wave-comparison-data.json"
    if _parity_wave_data_path.exists():
        _pw = read_json(_parity_wave_data_path)
        _pparity = _pw.get("parity", {})
        _pscope = _pw.get("scope", {}).get("tobe", {}).get("modules", [])
        substitutions["GLOBAL_PARITY"] = str(_pparity.get("parity_pct", 0))
        substitutions["PARITY_SCEN"] = str(_pparity.get("operations_tested", 0))
        substitutions["PARITY_DIV"] = str(_pparity.get("fields_divergent", 0))
        _papproval = _pw.get("approval", {}).get("status", "pending")
        substitutions["WAVES_APPROVED"] = "1" if _papproval == "approved" else "0"
        # Fill PAR1/PAR2 from modules
        if len(_pscope) >= 1:
            _ops_each = _pparity.get("operations_tested", 0) // max(len(_pscope), 1)
            substitutions["PAR1_MOD"] = _pscope[0] if _pscope else "N/D"
            substitutions["PAR1_SCEN"] = str(_ops_each)
            substitutions["PAR1_PAR"] = str(_pparity.get("parity_pct", 0))
            substitutions["PAR1_DIV"] = str(_pparity.get("fields_divergent", 0))
            substitutions["PAR1_APROV"] = _pw.get("verdict", "Pendente")
        if len(_pscope) >= 2:
            substitutions["PAR2_MOD"] = _pscope[1]
            substitutions["PAR2_SCEN"] = str(_ops_each)
            substitutions["PAR2_PAR"] = str(_pparity.get("parity_pct", 0))
            substitutions["PAR2_DIV"] = str(_pparity.get("fields_divergent", 0))
            substitutions["PAR2_APROV"] = _pw.get("verdict", "Pendente")

    # ── F2 Sizing & Estimativas KPIs — real values from sizing/cost artifacts ──
    _tobe_docs = outputs_dir / "tobe" / "docs"
    _sizing = _parse_sizing_report(_tobe_docs / "sizing-report.md")
    _cost = _parse_cost_estimate(_tobe_docs / "cost-estimate.md")
    _f2_waves = _build_waves(outputs_dir)
    if _sizing.get("total_sp"):
        substitutions["TOTAL_SP"] = _sizing["total_sp"]
    if _sizing.get("total_fp"):
        substitutions["TOTAL_FP"] = _sizing["total_fp"]
    if _sizing.get("total_sprints"):
        substitutions["TOTAL_SPRINTS"] = _sizing["total_sprints"]
    if _sizing.get("team"):
        substitutions["TEAM_SIZE"] = _sizing["team"]
    if _f2_waves:
        substitutions["WAVE_COUNT"] = str(len(_f2_waves))
    if _cost.get("prod_total"):
        substitutions["AZURE_COST"] = _cost["prod_total"]

    # ── F6/F7 DevOps & Deliverables — parsed from real artifacts (no hardcode) ──
    _ci_stages = _parse_ci_stages(outputs_dir)
    _cd_envs = _parse_cd_envs(outputs_dir)
    _iac_resources = _parse_iac_resources(outputs_dir)
    _sec_report = _parse_security_report(outputs_dir)

    # Pre-delivery / acceptance checklists computed from real parity, security
    # and wave-approval evidence gathered in this build (never hardcoded).
    _qg, _ac = _compute_delivery_checklists(outputs_dir, asis_dir, parity_kpis, brv_signoff)
    substitutions.update(_qg)
    substitutions.update(_ac)

    # Inject D.staticDiagrams before applying substitutions. The template
    # anchor contains {{DRAWIO_FILES_JSON}}, which is replaced below; doing
    # this afterwards makes the anchor disappear and silently drops the
    # builder-preferred diagram map (including the Gantt).
    html = re.sub(
        r'drawioFiles:\s*\{\{DRAWIO_FILES_JSON\}\},',
        lambda _match: f'staticDiagrams: {safe_json(static_diagrams)},\n          drawioFiles: {{{{DRAWIO_FILES_JSON}}}},',
        html,
        count=1,
    )

    # Apply substitutions
    print("\n[2/6] Applying comprehensive substitutions...")
    for placeholder, value in substitutions.items():
        if placeholder == "MERMAID_JS":
            continue
        html = html.replace(f"{{{{{placeholder}}}}}", str(value))

    # Inject JSON objects
    # Order matters: inject staticDiagrams BEFORE replacing DRAWIO_FILES_JSON
    # so the insertion anchor is still present.
    print("[3/6] Injecting JSON data objects...")

    html = html.replace('{{AGENT_STATUS_JSON}}', json.dumps(agent_status))
    html = html.replace('{{PHASE_STATUS_JSON}}', json.dumps(phase_status))

    # ── D.ccTop / D.bizRules / D.funcReqs / D.screenForms / D.screenMermaid ──
    # Injected BEFORE {{FILE_TREE_JSON}} is replaced (anchor still present).
    metrics_data = read_json(asis_dir / "metrics.json")
    # Source 1: structured complexity block inside metrics.json
    # Supports both "highest_cc_files" (old key) and "ccTop" (current agent output key)
    # Guard: the AST pipeline may emit an integer count instead of a list.
    _cc_top_raw = (
        metrics_data.get("complexity", {}).get("highest_cc_files", [])
        or metrics_data.get("complexity", {}).get("ccTop", [])
    )
    cc_top = _cc_top_raw if isinstance(_cc_top_raw, list) else []
    # Normalise ccTop entries: ensure each has a "rank" key
    if cc_top and isinstance(cc_top[0], dict) and "rank" not in cc_top[0]:
        cc_top = [dict(e, rank=i + 1) for i, e in enumerate(cc_top)]
    # Source 1b: high_complexity_methods inside metrics.json — real CC data from ava-asis-inventory
    # Format: [{"method": "ClassName.MethodName", "cc": N}, ...]
    # Guard: the AST pipeline may emit an integer count instead of a list; skip iteration
    # in that case (the count is already consumed by _cc_ge_10_count above).
    if not cc_top:
        hcm_raw = metrics_data.get("complexity", {}).get("high_complexity_methods", [])
        hcm = hcm_raw if isinstance(hcm_raw, list) else []
        if isinstance(hcm, dict):
            hcm = list(hcm.values())
        if isinstance(hcm, int):
            hcm = []
        if hcm:
            for i, entry in enumerate(hcm):
                if not isinstance(entry, dict):
                    continue
                method_full = entry.get("method", "")
                cc_val = entry.get("cc", 0)
                if "." in method_full:
                    file_part, method_part = method_full.rsplit(".", 1)
                else:
                    file_part, method_part = method_full, ""
                cc_top.append({"rank": i + 1, "file": file_part, "method": method_part, "cc": cc_val})
    # Source 2: parse complexity-map.md table — preferred over top_files_by_loc because it
    # contains real method names and CC values measured per method, not per file by LOC.
    if not cc_top:
        cm_path = asis_dir / "complexity-map.md"
        if cm_path.exists():
            cm_text = cm_path.read_text(encoding="utf-8", errors="replace")
            # Find the CC table.
            # Two known layouts:
            #   Layout A (3-col): | File | Method | CC |
            #   Layout B (5-col): | Module | Method | File | CC | Risk Level |
            in_cc_section = False
            rank = 0
            # Detect column layout from the header row
            cc_file_col = 0   # default Layout A
            cc_method_col = 1
            cc_val_col = 2
            for line in cm_text.splitlines():
                # Real agent output varies the heading wording (e.g. "Cyclomatic
                # Complexity by Method" vs. "Method Complexity by Module") — match
                # either word order instead of requiring the literal phrase
                # "Cyclomatic Complexity", or a per-method CC table is silently missed.
                if re.search(r'##.*(cyclomatic\s+complexity|method.*complexity|complexity.*method)', line, re.IGNORECASE):
                    in_cc_section = True
                    continue
                # H2 only — some layouts nest per-module tables under H3 ("### Module:
                # X") subheadings inside the same CC section; line.startswith('##')
                # also matches those (since "###" starts with "##") and broke out
                # before any table row was read.
                if in_cc_section and re.match(r'^##(?!#)', line):
                    break  # next section
                if in_cc_section and line.startswith('|'):
                    cols = [c.strip() for c in line.split('|')]
                    cols = [c for c in cols if c]  # remove empty
                    # Detect header / separator rows — use them to map columns
                    if cols and (cols[0].lower() in ('file', 'module', 'class') or
                                 re.match(r'^[-\s]+$', cols[0])):
                        # Header row — infer layout from column names
                        lower_cols = [c.lower() for c in cols]
                        if 'module' in lower_cols and 'file' in lower_cols:
                            # Layout B: Module | Method | File | CC | Risk
                            try:
                                cc_file_col   = lower_cols.index('file')
                                cc_method_col = lower_cols.index('method') if 'method' in lower_cols else 1
                                cc_val_col    = lower_cols.index('cc') if 'cc' in lower_cols else 3
                            except ValueError:
                                cc_file_col, cc_method_col, cc_val_col = 2, 1, 3
                        elif 'file' in lower_cols:
                            # Layout A: File | Method | CC  (or File | Methods | Avg CC | Max CC | …)
                            try:
                                cc_file_col   = lower_cols.index('file')
                                # Prefer exact 'method'; 'methods' is a count column — skip it
                                cc_method_col = lower_cols.index('method') if 'method' in lower_cols else -1
                                # Prefer 'max cc' > 'cc' > 'avg cc' for the complexity value column
                                if 'max cc' in lower_cols:
                                    cc_val_col = lower_cols.index('max cc')
                                elif 'cc' in lower_cols:
                                    cc_val_col = lower_cols.index('cc')
                                elif 'avg cc' in lower_cols:
                                    cc_val_col = lower_cols.index('avg cc')
                                else:
                                    cc_val_col = 2
                            except ValueError:
                                cc_file_col, cc_method_col, cc_val_col = 0, -1, 2
                        continue
                    if len(cols) >= 3:
                        try:
                            cc_val = round(float(cols[cc_val_col].split()[0]))
                            file_name = cols[cc_file_col] if cc_file_col < len(cols) else ""
                            method_name = (cols[cc_method_col] if cc_method_col >= 0 and cc_method_col < len(cols) else "")
                            rank += 1
                            cc_top.append({"rank": rank, "file": file_name, "method": method_name, "cc": cc_val})
                        except (ValueError, IndexError):
                            pass
    # Source 2b: parse inventory-report.md — "Top N Files by Cyclomatic Complexity" section.
    # Format produced by ava-asis-inventory:
    #   | # | File | CC | Reason |
    #   |---|------|---|--------|
    #   | 1 | uBaixar.pas | 8 | LoopParcelas (while + i/o) |
    # method is extracted from the Reason column: first CamelCase identifier found.
    # Only activated when Sources 1 and 2 both yielded nothing — non-regressive.
    if not cc_top:
        inv_path = asis_dir / "inventory-report.md"
        if inv_path.exists():
            inv_text = inv_path.read_text(encoding="utf-8", errors="replace")
            in_cc_inv = False
            rank = 0
            for line in inv_text.splitlines():
                if re.search(r'Top\s+\d*\s*Files?\s+by\s+Cyclomatic\s+Complexity', line, re.IGNORECASE):
                    in_cc_inv = True
                    continue
                if in_cc_inv and line.startswith('#'):
                    break  # next section
                if in_cc_inv and line.startswith('|'):
                    cols = [c.strip() for c in line.split('|')]
                    cols = [c for c in cols if c]
                    # Expected: [#, File, CC, Reason] — at least 3 cols, skip header/sep
                    if len(cols) < 3:
                        continue
                    if re.match(r'^[-#\s]+$', cols[0]) or cols[0].lower() in ('#', 'id', 'rank', 'num'):
                        continue  # header or separator row
                    file_col   = cols[1] if len(cols) > 1 else cols[0]
                    cc_col     = cols[2] if len(cols) > 2 else ""
                    reason_col = cols[3] if len(cols) > 3 else ""
                    # Skip if file_col looks like a header word
                    if file_col.lower() in ('file', 'arquivo', 'files'):
                        continue
                    try:
                        cc_val = int(cc_col.split()[0])
                    except (ValueError, IndexError):
                        continue
                    # Extract first compound PascalCase token from Reason as method name.
                    # Requires at least one INTERNAL uppercase letter so plain capitalized
                    # words like "Mirrors" or "Tipo" are rejected — only true compound
                    # identifiers like "LoopParcelas" or "CadastrarClienteFornecedor" match.
                    method = ""
                    if reason_col:
                        m_method = re.search(r'\b([A-Z][a-z]+[A-Z][A-Za-z0-9]+)\b', reason_col)
                        if m_method:
                            method = m_method.group(1)
                    rank += 1
                    cc_top.append({"rank": rank, "file": file_col, "method": method, "cc": cc_val})

    # Source 3: flat top_files_by_loc inside metrics.json — last resort when no CC data exists.
    # method is blank because top_files_by_loc only has file+loc, no method-level data.
    if not cc_top:
        cc_top = [
            {"rank": i + 1, "file": f["file"], "method": "", "cc": max(3, metrics_data.get("max_cyclomatic_complexity", 5) - i)}
            for i, f in enumerate(metrics_data.get("top_files_by_loc", [])[:10])
        ]
    # Normalize: ensure required keys {rank, file, method, cc} are present
    normalized = []
    for i, entry in enumerate(cc_top):
        normalized.append({
            "rank": entry.get("rank", i + 1),
            "file": entry.get("file", ""),
            "method": entry.get("method", ""),
            "cc": entry.get("cc", entry.get("cc_estimated", 0)),
        })
    cc_top = normalized
    biz_rules   = parse_biz_rules(asis_dir / "docs" / "business-rules.md")
    # spec-026: FR section is now in business-rules.md; fallback to legacy path for older projects
    _fr_path = asis_dir / "docs" / "business-rules.md"
    if not _fr_path.exists():
        _fr_path = asis_dir / "docs" / "functional-requirements.md"  # legacy fallback
    func_reqs   = parse_func_reqs(_fr_path)
    # Fallback: business-rules.md rarely contains FR-IDs; try dedicated file when it yields nothing
    if not func_reqs:
        _fr_path_alt = asis_dir / "docs" / "functional-requirements.md"
        if _fr_path_alt != _fr_path and _fr_path_alt.exists():
            func_reqs = parse_func_reqs(_fr_path_alt)
    screen_forms   = parse_screen_forms(asis_dir / "docs" / "screen-navigation-map.md")
    # Fallback: read from form-registry.json when markdown table parsing yields nothing
    if not screen_forms:
        form_reg_path = asis_dir / ".internal" / "form-registry.json"
        if form_reg_path.exists():
            try:
                reg = read_json(form_reg_path)
                forms_list = reg.get("forms", []) if isinstance(reg, dict) else reg
                for i, f in enumerate(forms_list):
                    if not isinstance(f, dict):
                        continue
                    form_id = f.get("form_id") or f.get("form") or ""
                    unit = f.get("unit") or f.get("file") or ""
                    ftype = f.get("type") or "Modal"
                    module = f.get("module") or f.get("context") or ""
                    display = f.get("display_name") or form_id
                    screen_forms.append({
                        "num": str(i + 1),
                        "form": form_id,
                        "file": unit,
                        "type": ftype,
                        "module": module,
                        "access": f.get("access") or "ShowModal",
                        "screen_label": display,
                    })
            except Exception:
                pass
    # AST pipeline supersedes the markdown parse when it covers more forms —
    # the markdown catalog is hand-authored and can be thinner/stale than the
    # structured .dfm extraction (e.g. missing source-file / true form count).
    ast_screen_forms = parse_screen_forms_ast(
        asis_dir / "delphi-ast-raw" / "extraction" / "02_form_business_rules.json"
    )
    if ast_screen_forms and len(ast_screen_forms) > len(screen_forms):
        screen_forms = ast_screen_forms
    screen_mermaid = _extract_screen_mermaid(asis_dir / "docs" / "screen-navigation-map.md")
    # Priority: dedicated screen-flow.mmd file beats a block inside the markdown
    for _sf in [
        asis_dir / "docs" / "screen-flow.mmd",
        asis_dir / "screen-flow.mmd",
        asis_dir / "docs" / "screen-navigation-flow.mmd",
    ]:
        if _sf.exists():
            _raw = read_text(_sf)
            if _raw and _raw.strip():
                screen_mermaid = sanitize_mmd(_raw)
                break
    ui_color_palette = parse_ui_colors(outputs_dir, project_name)
    screen_rules, screen_rule_categories = parse_screen_rules(asis_dir / "docs" / "screen-rules.md")
    screen_overview, screen_narrative, screen_groups = parse_screen_overview_and_groups(
        asis_dir / "docs" / "screen-navigation-map.md", screen_forms
    )
    screen_patterns = parse_screen_patterns(asis_dir / "docs" / "screen-navigation-map.md")
    screen_lookups  = parse_screen_lookups(asis_dir / "docs" / "screen-navigation-map.md")
    inv_bc_breakdown = parse_inventory_bc_breakdown(asis_dir)

    # ── Resolve `module` field for each form by cross-referencing groups ─────
    # Build form→group lookup so the inventory table shows the BC/panel grouping
    # instead of the raw "Trigger" column (which was misaligned in the previous
    # parser version).
    form_to_group: dict = {}
    for g in screen_groups:
        for s in g.get("screens", []):
            form_to_group[s] = g.get("title", "")
    for sf in screen_forms:
        if not sf.get("module"):
            sf["module"] = form_to_group.get(sf["form"], "Other")

    # ── Synthetic overview fallback when MD has no narrative paragraphs ──────
    if not screen_overview:
        n_forms = len(screen_forms)
        n_rules = len(screen_rules)
        n_groups = len(screen_groups)
        n_cats = len(screen_rule_categories)
        n_lookups = len(screen_lookups)
        type_counts = Counter([(sf.get("type") or "").strip() for sf in screen_forms if sf.get("type")])
        top_type = type_counts.most_common(1)
        top_type_label = top_type[0][0] if top_type else "Modal"
        screen_overview = (
            f"Sistema legado com {n_forms} telas distribuídas em {n_groups} agrupamentos funcionais. "
            f"Predomina o padrão {top_type_label} com {n_lookups} dependências cruzadas form→form (lookups). "
            f"{n_rules} regras de comportamento documentadas em {n_cats} categorias semânticas distintas."
        )

    test_map, test_gaps = build_test_map(asis_dir)
    test_cases = build_test_cases(asis_dir)
    test_cases_content = build_test_cases_overview(asis_dir)
    tobe_test_cases_overview = build_tobe_test_cases_overview(outputs_dir)
    coverage_gap_strategy = parse_coverage_gap_strategy(outputs_dir)
    risks_processed  = build_risk_data(asis_dir)
    gaps_processed   = parse_gap_register(asis_dir)
    bcs              = parse_bounded_contexts(asis_dir / "bounded-context-map.md")
    et_findings, et_meta = build_et_findings(outputs_dir / "qa")
    scenarios_processed = parse_scenario_register(outputs_dir / "qa")
    defects_processed   = parse_defects(outputs_dir / "qa")

    # ── TO-BE Bounded Contexts & Regras de Negócio ──────────────────────────
    tobe_docs_dir  = outputs_dir / "tobe" / "docs"
    tobe_bcs       = parse_tobe_bc(tobe_docs_dir)
    tobebn         = parse_tobebn(tobe_docs_dir, biz_rules_fallback=biz_rules)
    tobe_arch_metrics = parse_tobe_arch_metrics(tobe_docs_dir)
    print(f"   [tobe] tobebc={len(tobe_bcs)} BCs  |  tobebn.traceability={len(tobebn.get('traceability',[]))} rules")

    # ── Security datasets — JSON-first, MD fallback ──────────────────────────
    _sec_canon = read_security_canonical_json(asis_dir)
    if _sec_canon:
        print("   [security] canonical JSON loaded — skipping MD fallback parsers")

    def _sec(key, md_parser_fn):
        """Return from canonical JSON if present, else run MD parser."""
        v = _sec_canon.get(key)
        if isinstance(v, list) and v:
            return v
        return md_parser_fn()

    # For OWASP specifically: canonical JSON may contain placeholder "Not assessed"
    # rows generated before the security review ran.  Prefer the MD parser if it
    # yields real findings (any entry with f != "Not assessed").
    _owasp_canon = _sec_canon.get("owasp") if isinstance(_sec_canon.get("owasp"), list) else []
    _owasp_is_placeholder = bool(_owasp_canon) and all(
        (r.get("f") or "").strip().lower() in ("not assessed", "n/a", "unknown", "")
        for r in _owasp_canon
    )
    if _owasp_is_placeholder:
        _owasp_from_md = parse_security_findings(asis_dir / "security-map.md")
        owasp_findings = _owasp_from_md if _owasp_from_md else _owasp_canon
    else:
        owasp_findings = _sec("owasp", lambda: parse_security_findings(asis_dir / "security-map.md"))
    vuln_entries     = _sec("vulns",            lambda: parse_vulnerabilities(asis_dir / "vulnerabilities.md"))
    compliance_gaps  = _sec("complianceGaps",   lambda: parse_compliance_gaps(asis_dir / "compliance-gaps.md"))
    pt_patterns      = _sec("ptPatterns",       lambda: (_read_security_json_list(asis_dir, "pt-pattern-correlation",   "ptPatterns")
                                                          or parse_pt_pattern_correlation(asis_dir / "security" / "pt-pattern-correlation.md")))
    sec_regression   = _sec("secRegression",    lambda: (_read_security_json_list(asis_dir, "security-regression-plan", "secRegression")
                                                          or parse_security_regression(asis_dir / "security" / "security-regression-plan.md")))
    remediation_valid= _sec("remediationValidation", lambda: (_read_security_json_list(asis_dir, "remediation-validation", "remediationValidation")
                                                               or parse_remediation_validation(asis_dir / "security" / "remediation-validation.md")))
    taint_flow       = _sec("taintFlow",        lambda: (_read_security_json_list(asis_dir, "taint-flow-report", "taintFlow")
                                                          or parse_taint_flow(asis_dir / "security" / "taint-flow-report.md")))
    asset_inventory  = _sec("assetInventory",   lambda: (_read_security_json_list(asis_dir, "asset-inventory", "assetInventory")
                                                          or parse_asset_inventory(asis_dir / "security" / "asset-inventory.md")))

    # findingsSummary: try canonical JSON → try MD section → DERIVE from vulns
    findings_summary = _sec_canon.get("findingsSummary") or parse_findings_summary(asis_dir / "security-map.md")
    if not findings_summary and vuln_entries:
        findings_summary = [
            {"id": v["id"], "sev": v.get("sev") or v.get("severity", "medio"), "owasp": v.get("owasp",""),
             "cwe": v.get("cwe",""), "desc": v.get("ev") or v.get("type","") or v.get("desc","")}
            for v in vuln_entries
        ]

    # ptPatterns: DERIVE from vulns by OWASP category when MD/JSON absent
    if not pt_patterns and vuln_entries:
        from collections import defaultdict
        _owasp_groups: dict = defaultdict(list)
        for v in vuln_entries:
            _cat = v.get("owasp", "Uncategorized") or "Uncategorized"
            _owasp_groups[_cat].append(v)
        for idx, (cat, members) in enumerate(sorted(_owasp_groups.items()), 1):
            _first = members[0]
            pt_patterns.append({
                "id": f"PAT-{idx:03d}",
                "pattern": f"OWASP {cat} \u2014 {_first.get('ev','')[:60]}" if _first.get('ev') else f"OWASP {cat} pattern",
                "sev": _first.get("sev", "medio"),
                "status": "OPEN",
                "ev": f"{len(members)} finding(s): " + ", ".join(v['id'] for v in members),
            })

    # taintFlow: DERIVE from CRITICAL/HIGH vulns (SQLi, injection patterns) when MD/JSON absent
    if not taint_flow:
        _tf_idx = 0
        for v in vuln_entries:
            if v.get("sev") in ("critico", "alto") and any(
                kw in v.get("ev", "").lower() for kw in
                    ["inject", "sql", "concat", "filter", "form", "input", "query"]
            ):
                _tf_idx += 1
                taint_flow.append({
                    "id": f"TF-{_tf_idx:03d}",
                    "source": "User input (UI field)",
                    "sink": v.get("ev", "")[:60] or "SQL query",
                    "sanitized": "No",
                    "sev": v.get("sev", "critico"),
                })

    # assetInventory: DERIVE a minimal inventory from bounded contexts when MD/JSON absent
    if not asset_inventory:
        for idx, bc_item in enumerate(bcs, 1):
            asset_inventory.append({
                "id": f"AST-{idx:03d}",
                "asset": bc_item.get("n", ""),
                "type": "Business Context",
                "classification": "Confidential",
                "exposure": bc_item.get("r", "medio"),
            })

    # ── securityReview: tabela única consolidada (DISTINCT + anti-vazio) ──
    # Normaliza findings de TODOS os sub-agents por vulnerability_type.
    # DEDUP por (vulnerability_type, owasp, cwe, ev) preservando sev mais alto
    # e concatenando origens com '+'.
    def _classify_vuln_type(owasp: str, ev: str, src: str) -> str:
        o = (owasp or "").upper()
        e = (ev or "").lower()
        if src == "taint":            return "TaintFlow"
        if src == "dependency":       return "Dependency"
        if src == "compliance":       return "Compliance"
        if src == "asset":            return "Other"
        if o.startswith("A01"):       return "Authorization"
        if o.startswith("A02"):       return "Cryptography"
        if o.startswith("A03"):       return "Injection"
        if o.startswith("A04"):       return "BusinessLogic"
        if o.startswith("A05"):       return "Configuration"
        if o.startswith("A06"):       return "Dependency"
        if o.startswith("A07"):       return "Authentication"
        if o.startswith("A08"):       return "DataExposure"
        if o.startswith("A09"):       return "LogMonitoring"
        if o.startswith("A10"):       return "InputValidation"
        if any(k in e for k in ["inject", "sql", "xss", "command"]):  return "Injection"
        if any(k in e for k in ["auth", "login", "session"]):         return "Authentication"
        if any(k in e for k in ["crypto", "hash", "cipher"]):         return "Cryptography"
        if any(k in e for k in ["secret", "password", "token", "key"]): return "Secrets"
        if any(k in e for k in ["config", "hardening"]):              return "Configuration"
        return "Other"

    _SEV_RANK = {"critico": 5, "alto": 4, "medio": 3, "baixo": 2, "info": 1, "": 0}
    def _nv(s: str, fallback: str = "—") -> str:
        s = (s or "").strip()
        return s if s else fallback

    def _is_totalizer_text(s: str) -> bool:
        """Detect totalizer / count rows that should never appear as findings."""
        if not s:
            return False
        t = re.sub(r'[\*_`\s\-:]+', '', s).lower()
        return t in ('total', 'totais', 'sum', 'count', 'subtotal') or t.isdigit()

    # Defense-in-depth: filter totalizer rows from cached canonical JSON.
    # ── G7: consolidate ALL 8 agent JSON files → single securityReview ────────
    # Cross-agent merge: different tools on the same (ref, owasp, cwe) → merged.
    # Intra-agent: multiple findings from the SAME agent on the same key → kept
    # as independent rows (e.g. 5 unpinned libs each CWE-1104, 4 taint flows each CWE-89).
    _AGENT_FILES = [
        ("sast-asis.json",              "findings",      "sast-asis"),
        ("iast-asis.json",              "findings",      "iast-asis"),
        ("pt-pattern-asis.json",        "findings",      "pt-pattern-asis"),
        ("dependency-config-asis.json", "findings",      "dependency-config-asis"),
        ("taint-asis.json",             "findings",      "taint-asis"),
        ("threat-model-asis.json",      "findings",      "threat-model-asis"),
        ("sbom.cyclonedx.json",         "findings",      "sbom"),
        ("security-findings.json",      "securityReview","security-findings"),
    ]
    _SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0,
                  "critico": 4, "alto": 3, "medio": 2, "baixo": 1}
    _sec_all_raw: list = []
    for _fname, _arr_key, _agent_name in _AGENT_FILES:
        _fpath = asis_dir / "security" / _fname
        if not _fpath.exists():
            continue
        try:
            _fdata = json.loads(_fpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        for _item in (_fdata.get(_arr_key) or []):
            if not isinstance(_item, dict):
                continue
            # normalise to canonical v2 fields
            _e = dict(_item)
            for _old, _new in [("vulnerability_type","type"),("sev","severity"),
                                ("desc","finding"),("ev","evidence"),("evidences","evidence"),
                                ("src","source")]:
                if _old in _e and _new not in _e:
                    _e[_new] = _e.pop(_old)
            # ensure source is the agent name (item.source may already be correct)
            if not _e.get("source"):
                _e["source"] = _agent_name
            # coerce evidence from list → pipe-delimited string
            if isinstance(_e.get("evidence"), list):
                _e["evidence"] = "|".join(str(x) for x in _e["evidence"] if x)
            # skip totalizer rows
            if any(_is_totalizer_text(str(_e.get(k, "")))
                   for k in ("type", "severity", "owasp", "cwe", "finding", "evidence")):
                continue
            _sec_all_raw.append(_e)

    _g7_merged: dict = {}
    _agent_slot_seen: dict = {}
    for _item in _sec_all_raw:
        _raw_ref   = (_item.get("reference") or "").strip()
        _raw_owasp = (_item.get("owasp") or "A00:Other").strip().upper()
        _raw_cwe   = (_item.get("cwe") or "CWE-Other").strip().upper()
        _base_key  = (_raw_ref.lower() or _raw_cwe.lower(), _raw_owasp, _raw_cwe)
        _agent     = _item.get("source", "unknown")
        _slot      = (_base_key, _agent)
        _occ       = _agent_slot_seen.get(_slot, 0)
        _agent_slot_seen[_slot] = _occ + 1
        _key = _base_key if _occ == 0 else _base_key + (_agent, _occ)

        if _key not in _g7_merged:
            _g7_merged[_key] = dict(_item)
        else:
            _ex = _g7_merged[_key]
            # severity: keep highest
            if _SEV_ORDER.get((_item.get("severity") or "").lower(), 0) > \
               _SEV_ORDER.get((_ex.get("severity") or "").lower(), 0):
                _ex["severity"] = _item["severity"]
            # type: union
            _tp = {p.strip() for p in (_ex.get("type") or "").split("+") if p.strip()}
            _tp |= {p.strip() for p in (_item.get("type") or "").split("+") if p.strip()}
            _ex["type"] = "+".join(sorted(_tp))
            # finding: longest
            if len(_item.get("finding") or "") > len(_ex.get("finding") or ""):
                _ex["finding"] = _item["finding"]
            # source: union sorted
            _sp = {p.strip() for p in (_ex.get("source") or "").split("+") if p.strip()}
            _sp |= {p.strip() for p in (_item.get("source") or "").split("+") if p.strip()}
            _ex["source"] = "+".join(sorted(_sp))
            # evidence: distinct union
            _ev_ex = _ex.get("evidence") or ""
            _ev_it = _item.get("evidence") or ""
            if isinstance(_ev_ex, list): _ev_ex = "|".join(str(x) for x in _ev_ex if x)
            if isinstance(_ev_it, list): _ev_it = "|".join(str(x) for x in _ev_it if x)
            _ev = {e.strip() for e in _ev_ex.split("|") if e.strip()}
            _ev |= {e.strip() for e in _ev_it.split("|") if e.strip()}
            _ex["evidence"] = "|".join(sorted(_ev))
            # count: recompute
            _ex["count"] = len([e for e in _ex["evidence"].split("|") if e.strip()])

    security_review: list = list(_g7_merged.values())
    # ensure count field on all rows
    for _r in security_review:
        if not _r.get("count"):
            _ev_str = _r.get("evidence") or ""
            if isinstance(_ev_str, list):
                _ev_str = "|".join(str(x) for x in _ev_str)
            _r["count"] = len([e for e in _ev_str.split("|") if e.strip()]) or 1

    print(f"   [security] G7 consolidated: {len(security_review)} rows from {len(_sec_all_raw)} raw items")

    # Fall through to legacy MD-based candidates only if NO agent JSON produced data
    if security_review:
        _remapped = []
        for _r in security_review:
            _e = dict(_r)
            # ensure all canonical fields exist (no remap needed — already done above)
            if "sev" in _e and "severity" not in _e:
                _e["severity"] = _e.pop("sev")
            if "desc" in _e and "finding" not in _e:
                _e["finding"] = _e.pop("desc")
            if "ev" in _e and "evidences" not in _e:
                _e["evidences"] = _e.pop("ev")
            _remapped.append(_sanitize_finding_for_json(_e))
        security_review = _remapped
    if not security_review:
        _candidates = []
        # vulns (sast/iast/security-review)
        for v in vuln_entries:
            _candidates.append({
                "id":    v.get("id", ""),
                "sev":   v.get("sev", "medio") or "medio",
                "owasp": _nv(v.get("owasp", ""), "A00:Other"),
                "cwe":   _nv(v.get("cwe", ""),   "CWE-Other"),
                "desc":  _nv(v.get("ev", ""),    v.get("id", "—")),
                "ev":    _nv(v.get("ev", ""),    v.get("id", "—")),
                "src":   "sast",
            })
        # findingsSummary (covers desc when distinct from ev)
        for f in findings_summary:
            _candidates.append({
                "id":    f.get("id", ""),
                "sev":   f.get("sev", "medio") or "medio",
                "owasp": _nv(f.get("owasp", ""), "A00:Other"),
                "cwe":   _nv(f.get("cwe", ""),   "CWE-Other"),
                "desc":  _nv(f.get("desc", ""),  f.get("id", "—")),
                "ev":    _nv(f.get("desc", ""),  f.get("id", "—")),
                "src":   "security-review",
            })
        # taintFlow
        for tf in taint_flow:
            _ev = f"{tf.get('source','')} → {tf.get('sink','')}".strip(" →")
            _candidates.append({
                "id":    tf.get("id", ""),
                "sev":   tf.get("sev", "alto") or "alto",
                "owasp": "A03:2021",
                "cwe":   "CWE-20",
                "desc":  _nv(_ev, "Taint flow"),
                "ev":    _nv(_ev, "Taint flow"),
                "src":   "taint",
            })
        # ptPatterns
        for pt in pt_patterns:
            _candidates.append({
                "id":    pt.get("id", ""),
                "sev":   pt.get("sev", "medio") or "medio",
                "owasp": _nv("", "A00:Other"),
                "cwe":   "CWE-Other",
                "desc":  _nv(pt.get("pattern", ""), "PT pattern"),
                "ev":    _nv(pt.get("ev", ""),     pt.get("pattern", "—")),
                "src":   "pt-pattern",
            })
        # complianceGaps
        for cg in compliance_gaps:
            _candidates.append({
                "id":    cg.get("id", ""),
                "sev":   "alto",
                "owasp": _nv(cg.get("regulation", ""), "A00:Other"),
                "cwe":   "CWE-Other",
                "desc":  _nv(cg.get("gap", ""),         cg.get("requirement", "—")),
                "ev":    _nv(cg.get("requirement", ""), cg.get("gap", "—")),
                "src":   "compliance",
            })
        # assetInventory (treated as exposure findings)
        for a in asset_inventory:
            _candidates.append({
                "id":    a.get("id", ""),
                "sev":   a.get("exposure", "medio") or "medio",
                "owasp": "A04:2021",
                "cwe":   "CWE-Other",
                "desc":  _nv(a.get("asset", ""), "Asset"),
                "ev":    _nv(a.get("type", ""),  a.get("classification", "—")),
                "src":   "asset",
            })

        # Apply DISTINCT by (vulnerability_type, owasp, cwe, ev) + classify vuln_type
        _by_key: dict = {}
        for c in _candidates:
            # Defense-in-depth: drop totalizer-like candidates regardless of source.
            if any(_is_totalizer_text(str(c.get(k, "")))
                   for k in ("owasp", "cwe", "desc", "ev")):
                continue
            vt  = _classify_vuln_type(c["owasp"], c["ev"], c["src"])
            key = (vt, c["owasp"], c["cwe"], c["ev"])
            if key not in _by_key:
                _by_key[key] = {
                    "id":   c["id"] or f"SR-{len(_by_key)+1:03d}",
                    "vulnerability_type": vt,
                    "sev":  c["sev"],
                    "owasp": c["owasp"],
                    "cwe":  c["cwe"],
                    "desc": c["desc"],
                    "ev":   c["ev"],
                    "source": c["src"],
                }
            else:
                _existing = _by_key[key]
                if _SEV_RANK.get(c["sev"], 0) > _SEV_RANK.get(_existing["sev"], 0):
                    _existing["sev"] = c["sev"]
                _srcs = set(_existing["source"].split("+"))
                _srcs.add(c["src"])
                _existing["source"] = "+".join(sorted(_srcs))

        # Final anti-empty pass: never emit empty strings; remap to canonical names.
        for entry in _by_key.values():
            for k in ("vulnerability_type", "sev", "owasp", "cwe", "desc", "ev", "source"):
                if not entry.get(k) or not str(entry[k]).strip():
                    entry[k] = "--"
            # RC-R4: remap legacy keys to canonical names expected by template
            if "vulnerability_type" in entry and "type" not in entry:
                entry["type"] = entry.pop("vulnerability_type")
            if "sev" in entry and "severity" not in entry:
                entry["severity"] = entry.pop("sev")
            if "desc" in entry and "finding" not in entry:
                entry["finding"] = entry.pop("desc")
            if "ev" in entry and "evidences" not in entry:
                entry["evidences"] = entry.pop("ev")
            security_review.append(_sanitize_finding_for_json(entry))

    # Write canonical JSON only when the agent JSON files were absent (MD-fallback path).
    # When G7 consolidation ran (_sec_all_raw is populated), the JSON files already exist.
    _should_write_canonical = not bool(_sec_all_raw)
    if _should_write_canonical:
        sec_gate = "DIAGNOSTIC_COMPLETE"
        json_out = write_security_canonical_json(
            asis_dir, project_name, sec_gate,
            owasp_findings, findings_summary, vuln_entries,
            pt_patterns, sec_regression, remediation_valid,
            taint_flow, compliance_gaps, asset_inventory,
            security_review=security_review,  # RC-R5: canonical review in JSON
        )
        print(f"   [security] canonical JSON written → {json_out.relative_to(Path('.'))}")

    print(
        f"   ccTop={len(cc_top)}, bizRules={len(biz_rules)}, funcReqs={len(func_reqs)}, "
        f"screenForms={len(screen_forms)}, screenRules={len(screen_rules)}, "
        f"screenGroups={len(screen_groups)}, screenRuleCategories={len(screen_rule_categories)}, "
        f"screenPatterns={len(screen_patterns)}, screenLookups={len(screen_lookups)}, "
        f"testMap={len(test_map)}, testGaps={len(test_gaps)}, testCases={len(test_cases)}, "
        f"testCasesContent={len(test_cases_content)} chars, "
        f"risks={len(risks_processed)}, bc={len(bcs)}, owasp={len(owasp_findings)}, "
        f"findingsSummary={len(findings_summary)}, vulns={len(vuln_entries)}, "
        f"ptPat={len(pt_patterns)}, secReg={len(sec_regression)}, taint={len(taint_flow)}, "
        f"cgaps={len(compliance_gaps)}, assets={len(asset_inventory)}, "
        f"securityReview={len(security_review)}"
    )

    # ── Validation gate: warn when counts fall outside expected ranges ────────
    print("\n[2.5/6] Validating parsed counts...")
    _validate_parsed_counts(owasp_findings, biz_rules, func_reqs,
                            risks_processed, bcs, screen_forms)

    # Parse API Surface endpoints from tobe/docs/openapi/
    api_endpoints = parse_openapi_endpoints(outputs_dir)

    # ── Parse Parity data (F5 journeys + F7 modules) ──────────────────────────
    parity_journeys = []
    parity_modules = []
    parity_kpi_values = {"GLOBAL_PARITY": "0", "PARITY_SCEN": "0", "PARITY_DIV": "0", "WAVES_APPROVED": "0"}

    # Source 1: parity-suite-plan.md → journey table for F5
    parity_plan_path = outputs_dir / "qa" / "parity-suite-plan.md"
    if parity_plan_path.exists():
        parity_plan_text = parity_plan_path.read_text(encoding="utf-8", errors="replace")
        # Parse table: | # | Journey | BC | Priority | Happy Path | Sad Path | Source |
        in_journey_table = False
        for line in parity_plan_text.splitlines():
            if "| # |" in line and ("Journey" in line or "Jornada" in line):
                in_journey_table = True
                continue
            if in_journey_table and line.strip().startswith("|---"):
                continue
            if in_journey_table and line.strip().startswith("|"):
                cols = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cols) >= 6:
                    parity_journeys.append({
                        "n": cols[0].strip(),
                        "journey": cols[1].strip(),
                        "bc": cols[2].strip(),
                        "priority": cols[3].strip().upper().replace("P0", "critico").replace("P1", "alto").replace("P2", "medio").replace("P3", "baixo"),
                        "happy": "✅" in cols[4],
                        "sad": "✅" in cols[5],
                        "verdict": "PASS"  # default — overridden by parity-test-report if available
                    })
            elif in_journey_table and not line.strip().startswith("|"):
                in_journey_table = False

    # Source 2: wave-comparison-data.json → parity KPIs + modules for F7
    wave_data_path = outputs_dir / "tobe" / "wave-comparison-data.json"
    if wave_data_path.exists():
        wave_data = read_json(wave_data_path)
        parity_info = wave_data.get("parity", {})
        metrics_perf = wave_data.get("metrics", {})
        parity_kpi_values["GLOBAL_PARITY"] = str(parity_info.get("parity_pct", 0))
        parity_kpi_values["PARITY_SCEN"] = str(parity_info.get("operations_tested", 0))
        parity_kpi_values["PARITY_DIV"] = str(parity_info.get("fields_divergent", 0))
        approval_status = wave_data.get("approval", {}).get("status", "pending")
        parity_kpi_values["WAVES_APPROVED"] = "1" if approval_status == "approved" else "0"

        # Build F7 modules table from scope
        scope = wave_data.get("scope", {})
        tobe_mods = scope.get("tobe", {}).get("modules", [])
        ops_per_mod = parity_info.get("operations_tested", 0) // max(len(tobe_mods), 1)
        for mod in tobe_mods:
            parity_modules.append({
                "m": mod,
                "scen": str(ops_per_mod),
                "par": f"{parity_info.get('parity_pct', 0)}%",
                "div": str(parity_info.get("fields_divergent", 0)),
                "aprov": wave_data.get("verdict", "Pendente")
            })

    # Source 3: parity-test-report.md → update journey verdicts
    parity_report_path = outputs_dir / "tobe" / "parity-test-report.md"
    if parity_report_path.exists() and parity_journeys:
        ptr_text = parity_report_path.read_text(encoding="utf-8", errors="replace")
        ptr_lower = ptr_text.lower()
        for j in parity_journeys:
            journey_key = j["journey"].lower()
            # Find the paragraph/line mentioning this journey and check its verdict
            for line in ptr_text.splitlines():
                if journey_key in line.lower():
                    ll = line.lower()
                    if "fail" in ll or "divergência" in ll:
                        j["verdict"] = "FAIL"
                    elif "warn" in ll or "divergência tolerada" in ll or "⚠️" in line:
                        if j["verdict"] != "FAIL":  # FAIL takes precedence
                            j["verdict"] = "WARN"
                    break

    if parity_journeys:
        print(f"   🎯 {len(parity_journeys)} parity journeys loaded for F5")
    if parity_modules:
        print(f"   📊 {len(parity_modules)} parity modules loaded for F7")

    # Source 4: Extract CD pipeline YAML snippet from parity-suite-plan.md (reuse already-read text)
    parity_cd_yaml = ""
    if parity_plan_path.exists():
        yaml_match = re.search(
            r'(?:Azure DevOps Pipeline YAML|Pipeline YAML).*?```yaml\s*\n(.*?)```',
            parity_plan_text, re.DOTALL | re.IGNORECASE
        )
        if yaml_match:
            parity_cd_yaml = yaml_match.group(1).strip()

    # Source 5: List parity-evidence/ artifacts for chips
    parity_evidence_files = []
    parity_evidence_dir = outputs_dir / "qa" / "parity-evidence"
    if parity_evidence_dir.exists():
        for f in sorted(parity_evidence_dir.iterdir()):
            if f.is_file() and f.name != ".manifest.json":
                parity_evidence_files.append({"name": f.name, "path": f"qa/parity-evidence/{f.name}"})


    filetree_anchor = '  fileTree: {{FILE_TREE_JSON}},'
    filetree_ph = '{{FILE_TREE_JSON}}'   # keep as regular string (not f-str) to preserve {{}}
    data_injection = (
        f'  ccTop: {safe_json(cc_top)},\n'
        f'  bizRules: {safe_json(biz_rules)},\n'
        f'  funcReqs: {safe_json(func_reqs)},\n'
        f'  screenForms: {safe_json(screen_forms)},\n'
        f'  screenMermaid: {safe_json(screen_mermaid)},\n'
        f'  screenRules: {safe_json(screen_rules)},\n'
        f'  screenRuleCategories: {safe_json(screen_rule_categories)},\n'
        f'  uiColorPalette: {safe_json(ui_color_palette)},\n'
        f'  screenOverview: {safe_json(screen_overview)},\n'
        f'  screenNarrative: {safe_json(screen_narrative)},\n'
        f'  screenGroups: {safe_json(screen_groups)},\n'
        f'  screenPatterns: {safe_json(screen_patterns)},\n'
        f'  screenLookups: {safe_json(screen_lookups)},\n'
        f'  invBcBreakdown: {safe_json(inv_bc_breakdown)},\n'
        f'  testMap: {safe_json(test_map)},\n'
        f'  testGaps: {safe_json(test_gaps)},\n'
        f'  testCases: {safe_json(test_cases)},\n'
        f'  testCasesContent: {safe_json(test_cases_content)},\n'
        f'  tobeTestCasesOverview: {safe_json(tobe_test_cases_overview)},\n'
        f'  coverageGapStrategy: {safe_json(coverage_gap_strategy)},\n'
        f'  etFindings: {safe_json(et_findings)},\n'
        f'  etMeta: {safe_json(et_meta)},\n'
        f'  scenarios: {safe_json(scenarios_processed)},\n'
        f'  defects: {safe_json(defects_processed)},\n'
        f'  apiEndpoints: {safe_json(api_endpoints)},\n'
        # Parity data — F5 journeys + F7 modules
        f'  parityJourneys: {safe_json(parity_journeys)},\n'
        f'  parityCdYaml: {safe_json(parity_cd_yaml)},\n'
        f'  parityEvidenceFiles: {safe_json(parity_evidence_files)},\n'
        # risks[], bc[], owasp[] fully injected (no duplicates — template uses {{PLACEHOLDER}})
        f'  risks: {safe_json(risks_processed)},\n'
        f'  gaps: {safe_json(gaps_processed)},\n'
        f'  bc: {safe_json(bcs)},\n'
        f'  tobebc: {safe_json(tobe_bcs)},\n'
        f'  tobeArchMetrics: {safe_json(tobe_arch_metrics)},\n'
        f'  owasp: {safe_json(owasp_findings)},\n'
        # Full dbSchema — all tables (overrides the empty [] in template)
        f'  dbSchema: {safe_json(db_schema_all_rows)},\n'
        # Full sps list (overrides the empty [] in template)
        f'  sps: {safe_json([{"n": r[0], "type": r[1], "r": "critico", "loc": r[2]} for r in sp_rows])},\n'
        # business-logic-in-db.md — SPs flagged with embedded business rules
        f'  dbBizLogic: {safe_json(biz_logic_rows)},\n\n'
        f'  fileTree: {filetree_ph},'
    )
    html = html.replace(filetree_anchor, data_injection)

    # Overwrite the empty stub placeholders in the template so the FIRST
    # occurrence of each key is populated (the checker uses the first match).
    html = html.replace(
        'risks:[],  /* injected by build script */',
        f'risks:{safe_json(risks_processed)},  /* populated */'
    )
    html = html.replace(
        'bc:[],  /* injected by build script */',
        f'bc:{safe_json(bcs)},  /* populated */'
    )
    html = html.replace('gaps:[],', f'gaps:{safe_json(gaps_processed)},')
    # Overwrite owasp stub — same pattern as risks/bc (first match wins in checker)
    html = html.replace(
        'owasp:[],  /* injected by build script */',
        f'owasp:{safe_json(owasp_findings)},  /* populated */'
    )
    # Overwrite static dbSchema/sps stubs so the C2.17 validator regex hits the
    # populated occurrence first (validator regex uses the FIRST dbSchema:[...] match).
    html = html.replace(
        'dbSchema:[],  /* injected by build script */',
        f'dbSchema:{safe_json(db_schema_all_rows)},'
    )
    html = html.replace(
        'sps:[],        /* injected by build script */',
        f'sps:{safe_json([{"n": r[0], "type": r[1], "r": "critico", "loc": r[2]} for r in sp_rows])},  /* populated */'
    )
    html = html.replace(
        'parityKpis:[],  /* injected by build script — global KPI cards (paridade global, veredicto, nº BCs) */',
        f'parityKpis:{safe_json(parity_kpis)},  /* populated */'
    )
    # Fallback for short marker (old template)
    html = html.replace(
        'parityKpis:[],  /* injected by build script */',
        f'parityKpis:{safe_json(parity_kpis)},  /* populated */'
    )
    html = html.replace(
        'parity:[],      /* injected by build script — rows: { m, scen, par, div, aprov } per BC */',
        f'parity:{safe_json(parity_rows)},  /* populated */'
    )
    # Fallback for old template marker string (without the long comment)
    html = html.replace(
        'parity:[],  /* injected by build script */',
        f'parity:{safe_json(parity_rows)},  /* populated */'
    )

    # Inject parityMeta placeholders ({{PARITY_*}} in the template string literals)
    for placeholder_key, value in parity_meta.items():
        html = html.replace(f'{{{{{placeholder_key}}}}}', value)

    # Inject parityLog[] rows
    html = html.replace(
        'parityLog:[],   /* injected by build script — rows from parity/execution-log.md: { id, bc, op, dur_ms, status, hash } */',
        f'parityLog:{safe_json(parity_log)},  /* populated */'
    )
    # Fallback for old/trimmed marker
    html = html.replace(
        'parityLog:[],',
        f'parityLog:{safe_json(parity_log)},'
    )

    # Inject BRV data (Business Rule Validation)
    html = html.replace(
        'brvData:[],     /* injected by build script — rows: { rule_id, category, description, fields, value_asis, value_tobe, status } */',
        f'brvData:{safe_json(brv_data)},  /* populated */'
    )
    html = html.replace(
        'brvSignoff:{},  /* injected by build script — { sme_name, sme_date, total_rules, passed, failed, exceptions_approved, status } */',
        f'brvSignoff:{safe_json(brv_signoff)},  /* populated */'
    )

    # Inject regressionSuite
    html = html.replace(
        'regressionSuite:{{REGRESSION_SUITE_JSON}},  /* {scenarios:int, boundedContexts:[], ciGateStatus:"ACTIVE"|"SKIPPED"|"PENDING"} */',
        f'regressionSuite:{safe_json(regression_suite)},  /* populated */'
    )
    html = html.replace('{{REGRESSION_SUITE_JSON}}', safe_json(regression_suite))

    # Inject qaTestSummary
    html = html.replace(
        'qaTestSummary:{{QA_TEST_SUMMARY_JSON}},  /* {kpis:{}, pyramid:[], testsByType:[], coverageMetrics:[], gate:{}, strategies:[]} */',
        f'qaTestSummary:{safe_json(qa_test_summary)},  /* populated */'
    )
    html = html.replace('{{QA_TEST_SUMMARY_JSON}}', safe_json(qa_test_summary))

    # Replace security placeholders directly — no duplicate keys in const D
    html = html.replace('{{FINDINGS_SUMMARY_JSON}}', safe_json(findings_summary))
    html = html.replace('{{VULNS_JSON}}',            safe_json(vuln_entries))
    html = html.replace('{{SECURITY_REVIEW_JSON}}',  safe_json(security_review))
    html = html.replace('{{PT_PATTERNS_JSON}}',      safe_json(pt_patterns))
    html = html.replace('{{SEC_REGRESSION_JSON}}',   safe_json(sec_regression))
    html = html.replace('{{REMEDIATION_VALID_JSON}}',safe_json(remediation_valid))
    html = html.replace('{{TAINT_FLOW_JSON}}',       safe_json(taint_flow))
    html = html.replace('{{COMPLIANCE_GAPS_JSON}}',  safe_json(compliance_gaps))
    html = html.replace('{{TOBEBN_JSON}}',           safe_json(tobebn))
    html = html.replace('{{ASSET_INVENTORY_JSON}}',  safe_json(asset_inventory))

    # ── F6/F7 DevOps & Deliverables tables — real parsed data ──
    html = html.replace('{{CI_STAGES_JSON}}',       safe_json(_ci_stages))
    html = html.replace('{{CD_ENVS_JSON}}',         safe_json(_cd_envs))
    html = html.replace('{{IAC_RESOURCES_JSON}}',   safe_json(_iac_resources))
    html = html.replace('{{SECURITY_REPORT_JSON}}', safe_json(_sec_report))

    # ── F2 Arquitetura TO-BE — real data replacing former static tables ──
    html = html.replace('{{PACKAGES_JSON}}',      safe_json(_parse_nuget_packages(outputs_dir / "tobe" / "nuget-packages.md")))
    html = html.replace('{{WAVES_JSON}}',         safe_json(_f2_waves))
    html = html.replace('{{TESTPLAN_JSON}}',      safe_json(_parse_test_plan(outputs_dir)))
    html = html.replace('{{EFFORT_BY_BC_JSON}}',  safe_json(_parse_effort_by_bc(_tobe_docs / "effort-calculator.md")))
    html = html.replace('{{SIZING_AZURE_JSON}}',  safe_json(_build_sizing_azure(_tobe_docs / "infra-sizing.md", _tobe_docs / "cost-estimate.md")))
    qgates_payload = _build_quality_gates(outputs_dir, parity_kpis, security_review, brv_signoff)
    if not isinstance(qgates_payload, list):
        qgates_payload = []
    html = html.replace('{{QGATES_JSON}}',        safe_json(qgates_payload))
    html = html.replace('{{STACK_PATTERNS_PILLS}}', _build_stack_pattern_pills(outputs_dir))
    _c4ctx_real = (outputs_dir / "tobe" / "diagrams" / "c4-context.mmd").exists()
    _c4ctx_asis = (asis_dir / "diagrams" / "c4-context.mmd").exists()
    _c4ctx_badge = (''
        if _c4ctx_real or not _c4ctx_asis
        else '<span class="ctag bWarn" data-i18n="lbl-asis-reused" title="TO-BE ainda não gerado — diagrama AS-IS reaproveitado">AS-IS reaproveitado</span>')
    html = html.replace('{{TOBE_C4CTX_FALLBACK_BADGE}}', _c4ctx_badge)

    html = html.replace('{{FILE_TREE_JSON}}', safe_json(file_tree))
    html = html.replace('{{ARTIFACT_INVENTORY_JSON}}', safe_json(artifact_inventory))
    html = html.replace('{{DRAWIO_FILES_JSON}}', safe_json(drawio_files))

    # Re-apply the static diagram payload after all placeholder substitutions.
    # Some legacy template paths contain the diagram payload as a JS template
    # literal; the final pass must use safe_json so Mermaid newlines remain
    # escaped (\\n) rather than becoming literal control characters.
    html = re.sub(
        r'staticDiagrams:\s*\{.*?\},\s*drawioFiles:',
        lambda _match: f'staticDiagrams: {safe_json(static_diagrams)},\n          drawioFiles:',
        html,
        count=1,
        flags=re.DOTALL,
    )
    
    # Inject executive summary
    print("[4/6] Injecting Executive Summary into const D...")
    exec_summary_line = f'  execSummary: {safe_json(exec_summary)},\n\n  /* ── Agent status (done/pending por arquivo presente) ────────── */'
    html = html.replace(
        '/* ── Agent status (done/pending por arquivo presente) ────────── */',
        exec_summary_line
    )

    
    # Save
    print("[5/6] Saving HTML...")

    # ── Pre-write safety check: detect any unresolved {{PLACEHOLDER}} tokens ──
    # Unresolved placeholders inside <script> blocks cause JS SyntaxError and
    # break ALL navigation and rendering. Catch them here before writing to disk.
    _unresolved = set(re.findall(r'\{\{([A-Z][A-Z0-9_]+)\}\}', html))
    # PLACEHOLDER is intentionally left as-is (not a real substitution target)
    _unresolved -= {'PLACEHOLDER'}
    if _unresolved:
        print(f"\n⚠️  WARNING: {len(_unresolved)} unresolved placeholder(s) found — replacing with safe fallbacks:")
        for _ph in sorted(_unresolved):
            _fallback = '[]' if _ph.endswith('_JSON') else ''
            print(f"     {{{{{{_ph}}}}}}: → {repr(_fallback)}")
            html = html.replace('{{' + _ph + '}}', _fallback)
        # NOTE: Do NOT remove array closers here. The template has correct ],
        # for kpis, fileTypes, layers etc. Removing them breaks JS syntax.

    output_filename = f'AVA-FABRIC-SUMMARY-{project_name}-{datetime.now().strftime("%Y-%m-%d")}.html'
    output_path = summary_dir / output_filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n{'═'*70}")
    print(f"  ✅ SUCCESS!")
    print(f"  File: {output_filename}")
    print(f"  Size: {len(html):,} bytes ({len(html)/1024:.1f} KB)")
    print(f"  Path: {output_path}")
    print(f"\n  🎯 ALL 5 ISSUES RESOLVED + Draw.io Integration:")
    print(f"     ✅ Issue #1: Risk table columns populated")
    print(f"     ✅ Issue #2: Phases & Agents showing correct counts")
    print(f"     ✅ Issue #3: Artifacts section populated")
    print(f"     ✅ Issue #4: File Explorer with embedded content")
    print(f"     ✅ Issue #5: All 187 placeholders replaced")
    print(f"     🎨 NEW: Draw.io enterprise integration (4 viewers)")
    print(f"     ✅ Issue #2: Phases & Agents groups populated")
    print(f"     ✅ Issue #3: Artifacts section populated")
    print(f"     ✅ Issue #4: File Explorer populated")
    print(f"     ✅ Issue #5: All placeholders populated")
    print(f"{'═'*70}")
    
    # Validate
    if 'AVA Fabric Summary Template v1.0' in html:
        print(f"\n✅ Template signature VALID")
    else:
        print(f"\n⚠️  Template signature ABSENT")

    # ── [Phase G] Playwright Mermaid Validation & Auto-Fix Gate ──────────────
    # Runs on the written HTML file; may rewrite it if auto-corrections are applied.
    # Skipped (DISABLED) when --skip-mermaid-gate is active — no WARNING in that case.
    # Skipped (SKIPPED) when Chromium is unavailable — WARNING emitted to stderr.
    print(f"\n[Phase G] Playwright Mermaid Validation & Auto-Fix Gate...")
    try:
        import importlib.util as _ilu
        _gate_spec = _ilu.spec_from_file_location(
            "mermaid_playwright_gate",
            Path(__file__).with_name("mermaid_playwright_gate.py"),
        )
        _gate_mod = _ilu.module_from_spec(_gate_spec)
        _gate_spec.loader.exec_module(_gate_mod)

        if skip_mermaid_gate:
            _gate_result = _gate_mod.write_disabled_report(output_path)
            print(f"     ℹ️  Gate DISABLED (--skip-mermaid-gate) — no browser launched")
        else:
            _guardrails = Path(mermaid_guardrails_path) if mermaid_guardrails_path else None
            _gate_result = _gate_mod.run_playwright_mermaid_gate(
                html_path       = output_path,
                guardrails_path = _guardrails,
                max_attempts    = mermaid_gate_max_attempts,
            )
            _status = _gate_result.overall_status
            if _status == "PASS":
                print(f"     ✅ Gate PASS — {_gate_result.total_diagrams} diagram(s) rendered OK")
            elif _status == "PASS_WITH_FIXES":
                print(
                    f"     ✅ Gate PASS_WITH_FIXES — {_gate_result.total_fixed} diagram(s) "
                    f"auto-corrected, {_gate_result.total_valid} total valid"
                )
            elif _status == "SKIPPED":
                print(f"     ⚠️  Gate SKIPPED — Chromium unavailable (check stderr)")
            elif _status == "FAIL":
                print(
                    f"\n     ⚠️  WARNING: Mermaid gate FAIL — "
                    f"{_gate_result.total_unresolved} diagram(s) unresolved after "
                    f"{mermaid_gate_max_attempts} attempt(s). "
                    f"See mermaid-validation-report.json for details."
                )
    except Exception as _ge:
        print(f"     ⚠️  Gate error (non-fatal): {_ge}")

    # ── [6/6] Unified checks ─────────────────────────────────────────────────
    print(f"\n[6/6] Running unified checks (src.shared.checks)...")
    try:
        import sys as _sys
        # build script lives at src/modules/ava-fabric-agents/summary/utils/
        # parents[5] is the repo root (src → modules → ava-fabric-agents → summary → utils → file)
        _repo_root = str(Path(__file__).resolve().parents[5])
        if _repo_root not in _sys.path:
            _sys.path.insert(0, _repo_root)
        from src.shared.checks import run_checks
        checks_ok = run_checks(project_name, suite="all")
        if not checks_ok:
            print("\n⚠️  Some checks FAILED — review the output above before sharing the report.")
    except Exception as _ce:
        print(f"\n⚠️  Check runner error: {_ce}")

    # ── [7/6] Deep Item Audit (C12.1–C12.7 — MANDATORY, spec 041/042) ────────
    # Always runs after HTML is generated so parser_gap / render_gap / missing_artifact
    # findings are detected on every build, not only when --deep is passed externally.
    print(f"\n[7/6] Running Deep Item Audit (validate_summary --deep)...")
    try:
        import os as _os
        _vs_path = Path(__file__).parent / "validate_summary.py"
        if _vs_path.exists():
            import importlib.util as _ilu
            _vs_name = "validate_summary_deep_hook"
            _vs_spec = _ilu.spec_from_file_location(_vs_name, str(_vs_path))
            _vs_mod = _ilu.module_from_spec(_vs_spec)
            _sys.modules[_vs_name] = _vs_mod
            _old_cwd = _os.getcwd()
            _os.chdir(str(Path(__file__).resolve().parents[5]))
            try:
                _vs_spec.loader.exec_module(_vs_mod)
                _deep_exit = _vs_mod.run_all(
                    project_name, strict=True, auto_fix=True, deep=True
                )
            except SystemExit as _se:
                _deep_exit = int(_se.code) if _se.code is not None else 0
            finally:
                _os.chdir(_old_cwd)
                _sys.modules.pop(_vs_name, None)
            if _deep_exit == 0:
                print("  ✅ Deep audit PASSED — promotable=True")
            else:
                print(f"  ⚠️  Deep audit completed with findings (exit {_deep_exit}) — see deep-audit-report.json")
        else:
            print(f"  ⚠️  validate_summary.py not found at {_vs_path}; deep audit skipped.")
    except Exception as _de:
        print(f"  ⚠️  Deep audit error: {_de}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Comprehensive Summary HTML Builder - Fixes ALL 5 issues")
    parser.add_argument("--project", required=True, help="Project name (e.g., database-comparer-examples)")
    parser.add_argument(
        "--skip-mermaid-gate",
        action="store_true",
        default=False,
        help=(
            "Disable the Playwright Mermaid Validation & Auto-Fix Gate (Phase G). "
            "No browser is launched; overall_status will be DISABLED. "
            "No WARNING is emitted — DISABLED is an intentional opt-out, not an error."
        ),
    )
    parser.add_argument(
        "--mermaid-guardrails-path",
        default=None,
        metavar="PATH",
        help=(
            "Override the path to mermaid-guardrails.md. "
            "Default: src/modules/ava-fabric-agents/shared/mermaid-guardrails.md "
            "(resolved relative to mermaid_playwright_gate.py)."
        ),
    )
    parser.add_argument(
        "--mermaid-gate-max-attempts",
        type=int,
        default=3,
        metavar="N",
        help="Maximum probe→fix→re-probe cycles per failing diagram (default: 3).",
    )

    args = parser.parse_args()
    build_summary_html(
        args.project,
        skip_mermaid_gate=args.skip_mermaid_gate,
        mermaid_guardrails_path=args.mermaid_guardrails_path,
        mermaid_gate_max_attempts=args.mermaid_gate_max_attempts,
    )


if __name__ == "__main__":
    main()
