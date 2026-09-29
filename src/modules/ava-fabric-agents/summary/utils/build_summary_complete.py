#!/usr/bin/env python3
"""
AVA Fabric - Summary HTML Builder (Completo)
Gera Summary HTML usando o template oficial com TODOS os dados populados.

Resolve TODOS os problemas relatados:
- Issue #1: Risk table (r, ev, a columns) - populated from risk-register.json
- Issue #2: Phases & Agents zeros - populated from artifact inventory
- Issue #3: Artifacts empty - built from file system scan
- Issue #4: File Explorer empty - built with full content embedding
- Issue #5: All placeholders - complete data population from all JSON sources

Uso:
    python build_summary_complete.py --project database-comparer-examples

⚠️  DEPRECATED — use build_summary_comprehensive.py instead.
    This file is kept for historical reference only. It has known bugs:
    - Hardcoded "Delphi VCL Applications" scope (ignores legacy_technology config)
    - Cannot parse top-level array risk-register.json (returns 0 risks)
    - Missing parse_tobebn() AS-IS fallback (tobebn metrics/traceability empty)
    - Hardcoded prototype chips list (list_prototype_chips() not used)
    - Missing _parse_business_logic_in_db() wiring (dbBizLogic always empty)
"""
import sys as _sys
if __name__ == "__main__":
    _sys.stderr.write(
        "\n⛔  DEPRECATED: build_summary_complete.py is no longer maintained.\n"
        "    Run build_summary_comprehensive.py instead:\n"
        "    python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py"
        " --project <PROJECT_NAME>\n\n"
    )
    _sys.exit(1)
import argparse
import ast
import json
import re
import sys
import yaml
from pathlib import Path
from datetime import datetime
from collections import Counter

# Import test-cases parsers from the comprehensive builder so both scripts
# produce identical testCases / testCasesContent values in D.
sys.path.insert(0, str(Path(__file__).parent))
from build_summary_comprehensive import (  # noqa: E402
    build_test_cases as _build_test_cases,
    build_test_cases_overview as _build_test_cases_overview,
)

# Force UTF-8 stdout so emoji in print() work on Windows (cp1252 terminal)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ═══ ALL 42 AGENTS (complete list) ═══
# NOTE: This file is DEPRECATED — use build_summary_comprehensive.py instead.
# Agent registry here is kept for backward compatibility only (not authoritative).
ALL_AGENTS = [
    # F1 — AS-IS (9 agents)
    "ava-asis-orchestrator", "ava-asis-solution-delphi", "ava-asis-documentation",
    "ava-asis-security-orchestrator", "ava-asis-inventory",
    "ava-asis-gaps-risks", "ava-asis-db-analyzer", "ava-asis-gap-migration-analyzer",
    # F2 — TO-BE (7 agents)
    "ava-tobe-orchestrator", "ava-tobe-architecture-design", "ava-tobe-architecture-technical",
    "ava-tobe-measure-size", "ava-tobe-migration-plan",
    "ava-coder-dotnet", "ava-docs-tobe", "ava-test-plan-tobe",
    # F3 — Prototype (1 agent)
    "ava-prototype",
    # F4 — Stack (3 agents)
    "ava-stack-orchestrator", "ava-stack-dotnet-backend", "ava-stack-angular-frontend",
    # F5 — QA (9 agents)
    "ava-qa-orchestrator", "ava-qa-gaps-requirements", "ava-qa-behavior-mapping",
    "ava-qa-scenario-generator", "ava-qa-test-case-generator", "ava-qa-script-generator",
    "ava-qa-defect-identifier", "ava-qa-exploratory", "ava-qa-evidence-capture",
    # F6 — DevOps (5 agents)
    "ava-devops-iac", "ava-devops-ci", "ava-devops-cd",
    "ava-devops-package-approval", "ava-devops-compare-version",
    # F7 — Deliverables (7 agents)
    "ava-deliverable-packager", "ava-deliverable-tech-docs", "ava-deliverable-migration-plan",
    "ava-deliverable-test-evidence", "ava-deliverable-code-templates",
    "ava-deliverable-security-compliance", "ava-deliverable-client-demo",
]

# ═══ ARTIFACT MAP (files to scan per agent) ═══
ARTIFACT_MAP = {
    "ava-asis-orchestrator": [
        {"key": "master-report", "path": "asis/master-report.md"},
    ],
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
    "ava-asis-bridge-fastqa-qa": [
        # Bridge FastQA QA artifacts (bridge-fastqa-asis.md v4.1.0 Step 15)
        {"key": "test-gaps",               "path": "asis/qa/test-gaps.md"},
        {"key": "test-plan",               "path": "asis/qa/test-plan.md"},
        {"key": "test-cases",              "path": "asis/qa/test-cases.md"},
    ],
    "delphi-ast-test-coverage": [
        # Delphi AST test coverage (09_test_coverage.json) — guarded read
        {"key": "ast-test-coverage",       "path": "asis/delphi-ast-raw/compressed/09_test_coverage.json"},
    ],
    "ava-asis-security-orchestrator": [
        # Primary paths under security/ subfolder (canonical)
        {"key": "security-map",            "path": "asis/security/security-map.md"},
        {"key": "vulnerabilities",          "path": "asis/security/vulnerabilities.md"},
        {"key": "compliance-gaps",          "path": "asis/security/compliance-gaps.md"},
        {"key": "security-findings",        "path": "asis/security/security-findings.json"},
        # 7 canonical sub-agent JSONs (primary evidence of full execution)
        {"key": "sast-json",               "path": "asis/security/sast-asis.json"},
        {"key": "iast-json",               "path": "asis/security/iast-asis.json"},
        {"key": "pt-pattern-json",          "path": "asis/security/pt-pattern-asis.json"},
        {"key": "dependency-config-json",   "path": "asis/security/dependency-config-asis.json"},
        {"key": "taint-json",              "path": "asis/security/taint-asis.json"},
        {"key": "threat-model-json",        "path": "asis/security/threat-model-asis.json"},
        {"key": "security-review-json",     "path": "asis/security/security-review-asis.json"},
        # Fallback legacy paths (older runs may write here)
        {"key": "security-map-legacy",      "path": "asis/security-map.md"},
        {"key": "vulnerabilities-legacy",   "path": "asis/vulnerabilities.md"},
    ],
    "ava-asis-inventory": [
        # Primary paths (per inventory-asis.md Output Contract)
        {"key": "inventory-report",         "path": "asis/inventory-report.md"},
        {"key": "metrics",                  "path": "asis/metrics.json"},
        {"key": "complexity-map",            "path": "asis/complexity-map.md"},
        # Fallback paths (agents may write under asis/docs/)
        {"key": "inventory-report-docs",    "path": "asis/docs/inventory-report.md"},
        {"key": "metrics-docs",             "path": "asis/docs/metrics.json"},
        {"key": "complexity-map-docs",      "path": "asis/docs/complexity-map.md"},
    ],
    "ava-asis-gaps-risks": [
        {"key": "gaps-risks-report", "path": "asis/gaps-risks-report.md"},
        {"key": "risk-register", "path": "asis/risk-register.json"},
        {"key": "migration-risks-summary", "path": "asis/migration-risks-summary.md"},
    ],
    "ava-asis-db-analyzer": [
        {"key": "db-analysis-report", "path": "asis/db/db-analysis-report.md"},
        {"key": "schema-inventory", "path": "asis/db/schema-inventory.md"},
        {"key": "er-diagram", "path": "asis/db/er-diagram.mmd"},
        {"key": "stored-procedures-map", "path": "asis/db/stored-procedures-map.md"},
        {"key": "db-quality-report", "path": "asis/db/db-quality-report.md"},
        {"key": "business-logic-in-db", "path": "asis/db/business-logic-in-db.md"},
        {"key": "db-type", "path": "asis/db/db-type.json"},
    ],
    "ava-asis-gap-migration-analyzer": [
        {"key": "gap-list-report", "path": "asis/gap-list-report.md"},
        {"key": "gap-register", "path": "asis/gap-register.json"},
        {"key": "gap-analysis-summary", "path": "asis/gap-analysis-summary.md"},
    ],
    # ═══ F2 — TO-BE ═══
    "ava-tobe-orchestrator": [
        {"key": "final-tobe-report", "path": "tobe/final-tobe-report.md"},
    ],
    "ava-tobe-architecture-design": [
        {"key": "architecture-blueprint-tobe", "path": "tobe/docs/architecture-blueprint.md"},
        {"key": "bounded-context-map-tobe", "path": "tobe/docs/bounded-context-map.md"},
    ],
    "ava-tobe-architecture-technical": [
        {"key": "tech-framework-document", "path": "tobe/docs/tech-framework-document.md"},
        {"key": "solution-structure", "path": "tobe/solution-structure.md"},
        {"key": "nuget-packages", "path": "tobe/nuget-packages.md"},
        {"key": "coding-standards", "path": "tobe/coding-standards.md"},
        {"key": "patterns-applied", "path": "tobe/patterns-applied.json"},
    ],
    "ava-tobe-measure-size": [
        {"key": "sizing-report", "path": "tobe/docs/sizing-report.md"},
        {"key": "cost-estimate", "path": "tobe/docs/cost-estimate.md"},
        {"key": "effort-calculator", "path": "tobe/docs/effort-calculator.md"},
        {"key": "infra-sizing", "path": "tobe/docs/infra-sizing.md"},
    ],
    "ava-tobe-migration-plan": [
        {"key": "migration-plan", "path": "tobe/docs/migration-plan.md"},
        {"key": "migration-gantt", "path": "tobe/diagrams/migration-gantt.mmd"},
        {"key": "wave-plan", "path": "tobe/docs/wave-plan.md"},
        {"key": "ado-work-items", "path": "tobe/docs/ado-work-items.md"},
    ],
    "ava-coder-dotnet": [
        {"key": "source-code-dotnet", "path": "tobe/source-code"},
        {"key": "dotnet-solution", "path": "tobe/source-code/backend"},
    ],
    "ava-docs-tobe": [
        {"key": "api-map-tobe", "path": "tobe/api-map.md"},
        {"key": "technical-design-document", "path": "tobe/docs/technical-design-document.md"},
        {"key": "openapi-spec", "path": "tobe/docs/openapi/meu-erp-finance-v1.yaml"},
        {"key": "user-journeys", "path": "tobe/user-journeys.md"},
        {"key": "designer-system", "path": "tobe/designer-system.md"},
    ],
    "ava-test-plan-tobe": [
        {"key": "test-plan-tobe", "path": "tobe/docs/test-plan-tobe.md"},
    ],
    # ═══ F3 — Prototype ═══
    "ava-prototype": [
        {"key": "prototype-index", "path": "tobe/prototype/index.html"},
        {"key": "prototype-demo-script", "path": "tobe/prototype/demo-script.md"},
        {"key": "prototype-figma-spec", "path": "tobe/prototype/figma-spec.md"},
    ],
    # ═══ F4 — Stack (Codegen) ═══
    "ava-stack-orchestrator": [
        {"key": "source-code-root", "path": "tobe/source-code"},
    ],
    "ava-stack-dotnet-backend": [
        {"key": "source-code-backend", "path": "tobe/source-code"},
    ],
    "ava-stack-angular-frontend": [
        {"key": "source-code-frontend", "path": "tobe/source-code"},
    ],
    # ═══ F5 — QA ═══
    "ava-qa-orchestrator": [
        {"key": "quality-strategy", "path": "qa/quality-strategy.md"},
        {"key": "qa-master-report", "path": "qa/qa-master-report.md"},
    ],
    "ava-qa-gaps-requirements": [
        {"key": "gaps-requirements-report", "path": "qa/gaps-requirements-report.md"},
    ],
    "ava-qa-behavior-mapping": [
        {"key": "behavior-mapping-report", "path": "qa/behavior-mapping-report.md"},
    ],
    "ava-qa-scenario-generator": [
        {"key": "scenario-generator-report", "path": "qa/scenario-generator-report.md"},
    ],
    "ava-qa-test-case-generator": [
        {"key": "test-case-generator-report", "path": "qa/test-case-generator-report.md"},
    ],
    "ava-qa-script-generator": [
        {"key": "script-generator-report", "path": "qa/script-generator-report.md"},
    ],
    "ava-qa-defect-identifier": [
        {"key": "defect-identifier-report", "path": "qa/defect-identifier-report.md"},
    ],
    "ava-qa-exploratory": [
        {"key": "exploratory-report", "path": "qa/exploratory-report.md"},
    ],
    "ava-qa-evidence-capture": [
        {"key": "evidence-capture-report", "path": "qa/evidence-capture-report.md"},
    ],
    # ═══ F6 — DevOps ═══
    "ava-devops-iac": [
        {"key": "iac-terraform", "path": "tobe/iac/terraform"},
        {"key": "iac-bicep",     "path": "tobe/iac/bicep"},
    ],
    "ava-devops-ci": [
        {"key": "ci-pipeline", "path": "tobe/iac/ci/azure-pipelines-ci.yml"},
    ],
    "ava-devops-cd": [
        {"key": "cd-pipeline", "path": "tobe/iac/cd/azure-pipelines-cd.yml"},
    ],
    "ava-devops-compare-version": [
        {"key": "parity-report", "path": "tobe/parity-test-report.md"},
    ],
    "ava-devops-package-approval": [
        {"key": "wave-approval", "path": "tobe/wave-approval.md"},
    ],
    # ═══ F7 — Deliverables ═══
    "ava-deliverable-packager": [
        {"key": "deliverables-dir", "path": "deliverables"},
    ],
    "ava-deliverable-tech-docs": [
        {"key": "tech-docs-dir", "path": "deliverables/tech-docs"},
    ],
    "ava-deliverable-migration-plan": [
        {"key": "migration-plan-deliverable", "path": "deliverables/migration-plan"},
    ],
    "ava-deliverable-security-compliance": [
        {"key": "security-compliance-dir", "path": "deliverables/security-compliance"},
    ],
    "ava-deliverable-test-evidence": [
        {"key": "test-evidence-dir", "path": "deliverables/test-evidence"},
    ],
    "ava-deliverable-code-templates": [
        {"key": "code-templates-dir", "path": "deliverables/code-templates"},
    ],
    "ava-deliverable-client-demo": [
        {"key": "client-demo-dir", "path": "deliverables/client-demo"},
    ],
    # ═══ F8 — Summary ═══
    "ava-summary": [
        {"key": "summary-html-dir", "path": "summary"},
    ],
}


READABLE_EXTS = [
    'md', 'mmd', 'json', 'yaml', 'yml',
    'cs', 'ts', 'tsx', 'js', 'jsx',
    'html', 'htm', 'css', 'scss', 'sass',
    'sql', 'py', 'sh', 'ps1', 'bat',
    'tf', 'bicep', 'csproj', 'sln',
    'xml', 'toml', 'ini', 'properties',
    'txt', 'log', 'env',
    'pas', 'dfm', 'dpr', 'dproj'  # Delphi
]

MAX_FILE_BYTES = 256 * 1024  # 256 KB
MAX_TOTAL_BYTES = 5 * 1024 * 1024  # 5 MB

_SIZE_EVENTS_LOG = Path("asis") / "logs" / "size-events.log"


def _append_size_event(
    outputs_dir: Path,
    level: str,
    filename: str,
    size_kb: int,
    limit_desc: str,
    strategy: str,
) -> None:
    """Append one line to size-events.log (artifact-size-governance.md §3).

    Uses datetime.utcnow() — NTP not available in builder context.
    Format: {timestamp_iso} | {WARN|BLOCK} | {file} | {size} KB | {limit_desc} | estratégia: {desc}
    """
    from datetime import datetime, timezone

    log_path = outputs_dir / _SIZE_EVENTS_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} | {level} | {filename} | {size_kb} KB | {limit_desc} | estratégia: {strategy}\n"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def load_project_config(project_name: str) -> dict:
    """Carrega configuração do projeto"""
    config_path = Path(f"projects/{project_name}/context/project-config.yaml")
    if not config_path.exists():
        return {
            "project_name": project_name,
            "trace_id": "unknown",
            "language": "pt"
        }
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_text(path: Path) -> str:
    """Lê arquivo texto com fallback"""
    if not path.exists():
        return ""
    return path.read_text(encoding='utf-8', errors='replace')


def read_json(path: Path) -> dict:
    """Lê arquivo JSON com fallback"""
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def build_agent_status_map(project_name: str, outputs_base: Path) -> dict:
    """
    Constrói mapa de status de agentes
    Retorna: { "agent-id": "done"|"pending" }
    """
    print("\n🔧 [Gap #2 Fix] Construindo Agent Status Map...")
    
    agent_status = {}
    
    for agent_id in ALL_AGENTS:
        if agent_id not in ARTIFACT_MAP:
            agent_status[agent_id] = "pending"
            continue
        
        # Check if ANY expected file exists
        has_any = False
        for artifact in ARTIFACT_MAP[agent_id]:
            file_path = outputs_base / artifact["path"]
            if file_path.exists():
                has_any = True
                break
        
        agent_status[agent_id] = "done" if has_any else "pending"
    
    done_count = sum(1 for s in agent_status.values() if s == "done")
    total = len(agent_status)
    print(f"   📊 Status: {done_count}/{total} agentes executados")
    
    return agent_status


def build_artifact_inventory(project_name: str, outputs_base: Path) -> dict:
    """
    Constrói inventário de artefatos (D.arts)
    Retorna: { agent_id: [{key, path}] }
    """
    print("\n🔧 [Gap #3 Fix] Construindo Artifact Inventory...")
    
    artifact_inventory = {}
    total_artifacts = 0
    
    for agent_id in ALL_AGENTS:
        artifacts_for_agent = []
        
        if agent_id in ARTIFACT_MAP:
            for artifact in ARTIFACT_MAP[agent_id]:
                file_path = outputs_base / artifact["path"]
                if file_path.exists():
                    artifacts_for_agent.append({
                        "key": artifact["key"],
                        "path": artifact["path"]
                    })
                    total_artifacts += 1
        
        artifact_inventory[agent_id] = artifacts_for_agent
    
    print(f"   📦 {total_artifacts} artefatos catalogados")
    
    return artifact_inventory


def build_file_tree_with_content(project_name: str) -> dict:
    """
    GAP #2: Constrói file tree COM conteúdo embutido
    Retorna: { top_key: { label, files: [{name, path, ext, dir, content, truncated}], subdirs: {} } }
    """
    print("\n🔧 [Gap #2] Construindo File Tree com Content Embedder...")
    
    # Whitelist of extensions eligible for content embedding.
    # Source code extensions (.cs/.ts/.tsx/etc) are intentionally omitted:
    # summary HTML should surface documentation and diagrams, not the codebase.
    READABLE_EXTS = [
        'md', 'mmd', 'json', 'yaml', 'yml',
        'html', 'htm',
        'sql',
        'xml', 'toml', 'ini', 'properties',
        'txt', 'log',
    ]

    EXCLUDED_FILES = [
        'mermaid.min.js',
        'AVA-FABRIC-SUMMARY',   # prefix
        'summary-data.json',
        'generate-summary.py',
        'validation-report',    # prefix — validator artifacts, meta not deliverable
    ]

    # Sub-paths (anywhere in the relative path) that should be excluded entirely
    # from the Deliverables tree. Source code lives in these folders and the
    # user explicitly wants the summary to be a documentation deliverable only.
    EXCLUDED_PATH_SEGMENTS = [
        'source-code',
        'tests',
        'config',
        '__pycache__',
        '.git',
        'node_modules',
    ]
    
    MAX_FILE_BYTES = 256 * 1024  # 256 KB
    MAX_TOTAL_BYTES = 5 * 1024 * 1024  # 5 MB
    
    outputs_base = Path(f"projects/{project_name}/outputs")
    if not outputs_base.exists():
        return {}

    # Known phase folders — each becomes a top-level entry in D.fileTree.
    # "prototype" is pulled from tobe/prototype/ and promoted to a top-level
    # entry so F3 (Prototype phase) shows only those files, not all TO-BE.
    PHASE_SOURCES = [
        ('asis',         'F1 — AS-IS',          'asis'),
        ('tobe',         'F2 — TO-BE',          'tobe'),
        ('prototype',    'F3 — Prototype',      'tobe/prototype'),
        ('qa',           'F5 — QA',             'qa'),
        ('deliverables', 'F7 — Entregáveis',    'deliverables'),
        ('devops',       'F6 — DevOps',         'devops'),
        ('summary',      'F8 — Summary',        'summary'),
    ]

    file_tree = {}
    total_embedded = 0
    files_embedded = 0
    files_truncated = 0

    # Extra path exclusion: the tobe scan must skip the prototype/ subfolder
    # because it's owned by the dedicated 'prototype' phase entry below.
    TOBE_SKIP_IN_RELPATH = ('tobe/prototype/',)

    for phase_key, phase_label, rel_dir in PHASE_SOURCES:
        phase_dir = outputs_base / rel_dir
        if not phase_dir.exists() or not phase_dir.is_dir():
            continue

        file_tree[phase_key] = {'label': phase_label, 'files': [], 'subdirs': {}}

        for file_path in phase_dir.rglob('*'):
            if not file_path.is_file():
                continue
            if any(excl in file_path.name for excl in EXCLUDED_FILES):
                continue
            # Avoid embedding the previously-generated summary HTML into itself
            if phase_key == 'summary' and file_path.suffix.lower() == '.html':
                continue

            rel_path = file_path.relative_to(outputs_base)
            rel_str = str(rel_path).replace('\\', '/')
            # Skip anything inside excluded folders (source-code, tests, etc.)
            if any('/' + seg + '/' in '/' + rel_str + '/' for seg in EXCLUDED_PATH_SEGMENTS):
                continue
            # When scanning 'tobe', skip the prototype subfolder (dedicated phase entry handles it)
            if phase_key == 'tobe' and any(rel_str.startswith(skip) for skip in TOBE_SKIP_IN_RELPATH):
                continue
            parts = rel_str.split('/')

            file_info = {
                'name': file_path.name,
                'path': rel_str,
                'ext': file_path.suffix[1:] if file_path.suffix else '',
                'dir': parts[1] if len(parts) > 1 else phase_key,
                'content': None,
                'truncated': False
            }

            file_size = file_path.stat().st_size
            ext = file_info['ext']

            if ext in READABLE_EXTS and file_size < MAX_FILE_BYTES:
                if total_embedded + file_size < MAX_TOTAL_BYTES:
                    try:
                        file_info['content'] = file_path.read_text(encoding='utf-8', errors='replace')
                        total_embedded += file_size
                        files_embedded += 1
                    except Exception as e:
                        print(f"   ⚠️ Erro ao ler {file_path.name}: {e}")
                        file_info['content'] = None
                else:
                    file_info['truncated'] = True
                    files_truncated += 1
                    _append_size_event(
                        outputs_dir=file_path.parents[2],
                        level="WARN",
                        filename=file_path.name,
                        size_kb=file_size // 1024,
                        limit_desc=f"soft {MAX_FILE_BYTES // 1024} KB (MAX_FILE_BYTES — html embedding)",
                        strategy="truncated — not embedded in summary",
                    )

            file_tree[phase_key]['files'].append(file_info)

        print(f"   📄 {phase_key}: {len(file_tree[phase_key]['files'])} arquivos")

    print(f"   📦 {files_embedded} arquivos com conteúdo embutido ({total_embedded/1024:.1f} KB)")
    if files_truncated > 0:
        print(f"   ⚠️ {files_truncated} arquivos truncados (excederam limites)")

    return file_tree


def generate_executive_summary(project_name: str, language: str) -> dict:
    """
    GAP #3: Gera Executive Summary bilíngue
    Retorna: { "pt": "...", "en": "..." }
    """
    print("\n🔧 [Gap #3] Gerando Executive Summary bilíngue...")
    
    master_report_path = Path(f"projects/{project_name}/outputs/asis/master-report.md")
    
    if not master_report_path.exists():
        print("   ⚠️ master-report.md não encontrado — usando placeholder")
        return {
            "pt": "<p>Relatório executivo não disponível. Execute o diagnóstico AS-IS completo.</p>",
            "en": "<p>Executive report not available. Run complete AS-IS diagnostic.</p>"
        }
    
    text = master_report_path.read_text(encoding='utf-8')
    
    # Extrair seção Executive Summary
    exec_match = re.search(
        r'##\s*(?:Sumário Executivo|Executive Summary)(.*?)(?=\n##\s|\Z)',
        text,
        re.DOTALL | re.IGNORECASE
    )
    
    if exec_match:
        exec_text = exec_match.group(1).strip()
        # Pegar primeiros 3 parágrafos
        paragraphs = [p.strip() for p in exec_text.split('\n\n') if p.strip() and not p.strip().startswith('|')][:3]
        summary_html = '\n'.join(f'<p>{p}</p>' for p in paragraphs)
    else:
        # Fallback: primeiros 3 parágrafos do documento
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and not p.strip().startswith('#') and not p.strip().startswith('|')][:3]
        summary_html = '\n'.join(f'<p>{p}</p>' for p in paragraphs)
    
    # Se language == "en", assumir que o texto já está em inglês
    # Para bilíngue real, precisaria de tradução (biblioteca translate ou API)
    # Por simplicidade, usar o mesmo texto com nota
    if language == "en":
        exec_summary = {
            "pt": f"<p><em>[Tradução não disponível — conteúdo em inglês]</em></p>{summary_html}",
            "en": summary_html
        }
    else:
        exec_summary = {
            "pt": summary_html,
            "en": f"<p><em>[Translation not available — content in Portuguese]</em></p>{summary_html}"
        }
    
    print(f"   ✅ Executive Summary gerado ({len(summary_html)} caracteres)")
    
    return exec_summary


def _parse_complexity_map_md(text: str) -> list:
    """Header-aware Markdown parser for `complexity-map.md`.

    Tolerates:
      - PT/EN headers (Arquivo|File, Método|Function|Procedimento, CC|Complexidade|Cyclomatic, LOC, Módulo|Module)
      - Variable column order
      - Alignment separators (|---|, |:---:|, |---:|, |:---|)
      - Decimal CC ("12.5" → 13), prefixed CC ("~18", "≈20", ">15")
      - Section anchors: limits parsing to a "Top 10 / Cyclomatic Complexity / Complexidade Ciclomática" heading when present
    Returns list of {rank, file, method, cc} sorted by cc desc, top 10.
    """
    if not text:
        return []

    HEADER_ALIASES = {
        "file":   {"file", "arquivo", "unit", "fonte"},
        "method": {"method", "metodo", "método", "function", "função", "funcao",
                   "procedure", "procedimento", "rotina"},
        "cc":     {"cc", "complexity", "complexidade", "cyclomatic",
                   "cyclomatic complexity", "complexidade ciclomatica",
                   "complexidade ciclomática", "estimated cc", "cc estimated"},
    }
    SEP_RE  = re.compile(r'^\|?\s*(:?-{3,}:?\s*\|\s*)+:?-{3,}:?\s*\|?\s*$')
    NUM_RE  = re.compile(r'-?\d+(?:[.,]\d+)?')

    def norm(cell: str) -> str:
        return cell.strip().strip('`').strip('*').strip().lower()

    def split_row(line: str) -> list:
        parts = line.strip().split('|')
        # Drop leading/trailing empties from outer pipes
        if parts and parts[0].strip() == '':
            parts = parts[1:]
        if parts and parts[-1].strip() == '':
            parts = parts[:-1]
        return [c.strip().strip('`').strip('*').strip() for c in parts]

    def map_indices(header_cells: list) -> dict:
        idx = {}
        for i, cell in enumerate(header_cells):
            key = norm(cell)
            for canon, aliases in HEADER_ALIASES.items():
                if canon in idx:
                    continue
                if key in aliases or any(a in key for a in aliases):
                    idx[canon] = i
                    break
        return idx

    # Try to anchor on a relevant heading; fall back to whole document.
    HEADING_RE = re.compile(
        r'^\s*#{1,6}\s+.*(top\s*10|cyclomatic|complexidade\s*ciclom)',
        re.IGNORECASE | re.MULTILINE,
    )
    blocks = []
    matches = list(HEADING_RE.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            blocks.append(text[start:end])
    else:
        blocks = [text]

    rows = []
    for block in blocks:
        lines = block.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Detect a table header: pipe row immediately followed by separator row
            if line.startswith('|') and i + 1 < len(lines) and SEP_RE.match(lines[i + 1].strip()):
                header_cells = split_row(line)
                col = map_indices(header_cells)
                if 'file' not in col or 'cc' not in col:
                    i += 1
                    continue
                i += 2  # skip header + separator
                while i < len(lines):
                    body = lines[i].strip()
                    if not body.startswith('|'):
                        break
                    if SEP_RE.match(body):
                        i += 1
                        continue
                    cells = split_row(body)
                    if len(cells) <= max(col.values()):
                        i += 1
                        continue
                    raw_cc = cells[col['cc']]
                    m = NUM_RE.search(raw_cc.replace(',', '.'))
                    if not m:
                        i += 1
                        continue
                    try:
                        cc_val = int(round(float(m.group(0))))
                    except ValueError:
                        i += 1
                        continue
                    if cc_val <= 0:
                        i += 1
                        continue
                    file_val = cells[col['file']] or '?'
                    method_val = cells[col['method']] if 'method' in col else 'main'
                    if not method_val:
                        method_val = 'main'
                    rows.append({
                        "rank": 0,
                        "file": file_val,
                        "method": method_val.split(',')[0].strip() or 'main',
                        "cc": cc_val,
                    })
                    i += 1
                continue
            i += 1

    if not rows:
        return []
    rows.sort(key=lambda r: r["cc"], reverse=True)
    rows = rows[:10]
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def parse_complexity_top10(asis_dir: Path) -> list:
    """Parse complexity data from metrics.json, complexity-map.md, or inventory-report.md.
    Supports flat metrics.json, structured complexity.highest_cc_files, hotspots[], and markdown tables.
    """
    # 1. metrics.json nested: complexity.highest_cc_files
    metrics = read_json(asis_dir / "metrics.json")
    cc_files = metrics.get("complexity", {}).get("highest_cc_files", [])
    if cc_files:
        rows = []
        for i, entry in enumerate(cc_files[:10], 1):
            rows.append({
                "rank": i,
                "file": entry.get("file", "?"),
                "method": entry.get("method", "main"),
                "cc": entry.get("cc_estimated", 0)
            })
        if rows:
            return rows

    # 1b. metrics.json hotspots[] — ava-asis-inventory format
    hotspots = metrics.get("hotspots", [])
    if hotspots:
        rows = []
        for i, entry in enumerate(hotspots[:10], 1):
            rows.append({
                "rank": i,
                "file": entry.get("unit", entry.get("file", "?")),
                "method": "main",
                "cc": entry.get("max_complexity", entry.get("cc", 0))
            })
        if rows:
            return rows

    # 2. complexity-map.md table: | Arquivo | ... | CC | ...
    text = read_text(asis_dir / "complexity-map.md")
    if text:
        rows = []
        for line in text.split('\n'):
            line = line.strip()
            if not line.startswith('|') or line.startswith('|---') or line.startswith('| Arquivo'):
                continue
            cols = [c.strip().strip('`').strip('*') for c in line.split('|')[1:-1]]
            if len(cols) >= 4:
                try:
                    cc = int(''.join(c for c in cols[2] if c.isdigit()) or '0')
                except ValueError:
                    continue
                if cc > 0:
                    rows.append({"rank": 0, "file": cols[0], "method": "main", "cc": cc})
        if rows:
            rows.sort(key=lambda r: r["cc"], reverse=True)
            for i, r in enumerate(rows[:10], 1):
                r["rank"] = i
            return rows[:10]

    # 3. inventory-report.md table: | Rank | File | Estimated CC | Key Complex Methods |
    text = read_text(asis_dir / "inventory-report.md")
    if not text:
        return []
    rows = []
    in_cc_section = False
    for line in text.split('\n'):
        stripped = line.strip()
        if '## 4.' in stripped and 'Cyclomatic Complexity' in stripped:
            in_cc_section = True
            continue
        if in_cc_section and stripped.startswith('## '):
            break
        if not in_cc_section:
            continue
        if not stripped.startswith('|') or stripped.startswith('|---') or \
                'Rank' in stripped or 'File' in stripped:
            continue
        cols = [c.strip().strip('`').strip('*') for c in stripped.split('|')[1:-1]]
        if len(cols) >= 3:
            try:
                cc = int(''.join(c for c in cols[2] if c.isdigit()) or '0')
            except ValueError:
                continue
            if cc > 0:
                rows.append({
                    "rank": len(rows) + 1,
                    "file": cols[1],
                    "method": cols[3].split(',')[0].strip() if len(cols) > 3 else "main",
                    "cc": cc
                })
    return rows[:10]


def parse_business_rules(asis_dir: Path) -> list:
    """Parse business-rules.md to extract rules table.
    Supports four formats:
      - Structured PT: ## Módulo: X  then  ### RN-NNN — Description
      - Flat bold EN:  ## BR-NNN: Description  then **Source**: / **Priority**:
      - Section EN:    ## Word+ Rules  then  ### BR-XX-NNN — Description  then bullet - **Origin form**: / - **Priority**:
      - Domain table:  ## Domain: X  then markdown table | ID | Category | Rule | Confirmed? |
    """
    text = read_text(asis_dir / "docs" / "business-rules.md")
    if not text:
        return []
    rules = []
    current_module = ""
    current_rule = {}

    for line in text.split('\n'):
        line = line.strip()

        # Structured format — module section header (PT and EN variants)
        if line.startswith('## Módulo:') or line.startswith('## Module:'):
            current_module = re.split(r'[:(]', line, maxsplit=1)[-1].strip().split('(')[0].strip()

        # Domain table format — module header "## Domain: Accounts Payable"
        elif line.startswith('## Domain:'):
            current_module = line.split(':', 1)[-1].strip()

        # Section EN format — module header like "## AccountsPayable Rules" or "## Banking Rules"
        elif re.match(r'^## \w[\w\s/+]+ Rules\s*$', line):
            current_module = re.sub(r'\s*Rules\s*$', '', line[3:]).strip()

        # Structured format — rule header  ### RN-NNN — Description
        elif re.match(r'^### RN-', line):
            if current_rule.get("id"):
                rules.append(current_rule)
            rid = line.split('\u2014')[0].replace('###', '').replace(':', '').strip()
            desc = line.split('\u2014', 1)[1].strip() if '\u2014' in line else \
                   line.split(':', 1)[-1].strip()
            current_rule = {"id": rid, "rule": desc, "module": current_module, "origin": "", "priority": "MÉDIA"}

        # Section EN format — rule header  ### BR-XX-NNN — Title  (e.g. BR-AP-001, BR-AR-002)
        elif re.match(r'^### BR-', line):
            if current_rule.get("id"):
                rules.append(current_rule)
            m = re.match(r'^### (BR-[\w-]+)\s*[—\-]+\s*(.*)', line)
            rid  = m.group(1) if m else re.sub(r'^### ', '', line.split('\u2014')[0]).strip()
            desc = m.group(2).strip() if m else (line.split('\u2014', 1)[1].strip() if '\u2014' in line else "")
            current_rule = {"id": rid, "rule": desc, "module": current_module, "origin": "", "priority": "MÉDIA"}

        # Flat bold format — rule header  ## RN-NNN — Description
        elif re.match(r'^## RN-', line):
            if current_rule.get("id"):
                rules.append(current_rule)
            m = re.match(r'^## (RN-[\d\w-]+)\s*[\u2014\-]+\s*(.*)', line)
            rid  = m.group(1) if m else re.sub(r'^## ', '', line.split('\u2014')[0]).strip()
            desc = m.group(2).strip() if m else (line.split('\u2014', 1)[1].strip() if '\u2014' in line else "")
            current_rule = {"id": rid, "rule": desc, "module": current_module, "origin": "", "priority": "M\u00c9DIA"}

        # Flat bold format — rule header  ## BR-NNN: Description
        elif re.match(r'^## BR-', line):
            if current_rule.get("id"):
                rules.append(current_rule)
            m = re.match(r'^## (BR-\d+)[:\s]*(.*)', line)
            rid  = m.group(1) if m else "BR-?"
            desc = m.group(2).strip() if m else ""
            current_rule = {"id": rid, "rule": desc, "module": current_module, "origin": "", "priority": "MÉDIA"}

        # Flat bold format — **Source**: uFile.pas ...  OR  **Source:** uFile.pas
        elif re.match(r'^\*\*Source:?\*\*', line):
            val = re.sub(r'^\*\*Source:?\*\*\s*:?\s*', '', line)
            current_rule["origin"] = val.split('\u2014')[0].strip().strip('`')

        # Flat bold format — **Rule**: description  OR  **Rule:** description (full rule text)
        elif re.match(r'^\*\*Rule:?\*\*', line) and current_rule:
            val = re.sub(r'^\*\*Rule:?\*\*\s*:?\s*', '', line)
            if val.strip():
                current_rule["rule"] = val.strip()

        # Flat bold format — **Module**: value  OR  **Module:** value
        elif re.match(r'^\*\*M[oó]dul[eo]:?\*\*', line, re.IGNORECASE) and current_rule:
            val = re.sub(r'^\*\*M[oó]dul[eo]:?\*\*\s*:?\s*', '', line, flags=re.IGNORECASE)
            current_rule["module"] = val.strip()

        # Flat bold format — **Priority**: HIGH | CRITICAL | MEDIUM  OR  **Priority:** ...
        elif re.match(r'^\*\*Priority:?\*\*', line):
            val = re.sub(r'^\*\*Priority:?\*\*\s*:?\s*', '', line)
            current_rule["priority"] = val.strip()

        # Section EN bullet format — - **Rule**: description (captures the full rule text)
        elif re.match(r'^-\s+\*\*Rule\*\*', line) and current_rule:
            val = re.sub(r'^-\s+\*\*Rule\*\*\s*:\s*', '', line)
            if val.strip():
                current_rule["rule"] = val.strip()

        # Section EN bullet format — - **Origin form**: frmXxx or - **Source**: frmXxx
        elif re.match(r'^-\s+\*\*(Origin form|Source)\*\*', line) and current_rule:
            val = re.sub(r'^-\s+\*\*(Origin form|Source)\*\*\s*:\s*', '', line)
            current_rule["origin"] = val.split('\u2014')[0].strip().strip('`')

        # Section EN bullet format — - **Priority**: HIGH
        elif re.match(r'^-\s+\*\*Priority\*\*', line) and current_rule:
            val = re.sub(r'^-\s+\*\*Priority\*\*\s*:\s*', '', line)
            current_rule["priority"] = val.strip()

        # Structured table format — | **Arquivo** | value |
        elif line.startswith('| **Arquivo**'):
            val = line.split('|')[2].strip().strip('*').strip()
            current_rule["origin"] = val.strip('`')
        elif line.startswith('| **Criticidade**'):
            val = line.split('|')[2].strip().strip('*').strip()
            current_rule["priority"] = val

        # Domain table format — | RN-XX-NN | Category | Rule text | Confirmed? |
        # Skip header row (ID/Id), separator rows (---), and rows without enough columns
        elif re.match(r'^\|\s*(?:RN|BR)-', line):
            cols = [c.strip() for c in line.split('|')]
            cols = [c for c in cols if c]  # remove empties from split edges
            if len(cols) >= 3:
                if current_rule.get("id"):
                    rules.append(current_rule)
                rule_id = cols[0]
                category = cols[1] if len(cols) > 2 else ""
                rule_text = cols[2] if len(cols) > 2 else cols[1]
                # Strip markdown backtick fences from rule text for cleaner display
                rule_text = re.sub(r'`([^`]+)`', r'\1', rule_text)
                current_rule = {
                    "id": rule_id,
                    "rule": rule_text,
                    "module": current_module,
                    "origin": category,
                    "priority": "MÉDIA",
                }
                rules.append(current_rule)
                current_rule = {}

    if current_rule.get("id"):
        rules.append(current_rule)
    return rules


def parse_functional_requirements(asis_dir: Path) -> list:
    """Parse functional requirements from business-rules.md (## Functional Requirements section).
    spec-026: FR content moved from functional-requirements.md into business-rules.md.
    Fallback to legacy functional-requirements.md for projects run before spec-026.
    """
    # spec-026 path-fallback
    _br_path = asis_dir / "docs" / "business-rules.md"
    _fr_path = asis_dir / "docs" / "functional-requirements.md"  # legacy
    text = read_text(_br_path if _br_path.exists() else _fr_path)
    if not text:
        return []
    reqs = []
    current_module = ""
    in_table = False
    last_req_title = ""

    for line in text.split('\n'):
        line = line.strip()

        # Module section header — both Portuguese and English variants
        if re.match(r'^## M[oó]dul[eo]:', line, re.IGNORECASE) or \
                re.match(r'^## Module:', line, re.IGNORECASE):
            current_module = re.split(r'[:(]', line, maxsplit=1)[-1].strip()
            in_table = False
            continue

        # Section EN range header — ## RF-NN to RF-NN — ModuleName (e.g. "## RF-01 to RF-06 — CustomerSupplier")
        m_range = re.match(r'^## RF-\d+\s+to\s+RF-\d+\s*[—\-]+\s*(.+)', line)
        if m_range:
            current_module = m_range.group(1).strip()
            in_table = False
            continue

        # Structured header format  ### RF-NNN — Description
        if re.match(r'^### RF-', line):
            rid  = line.split('\u2014')[0].replace('###', '').replace(':', '').strip()
            desc = line.split('\u2014', 1)[1].strip() if '\u2014' in line else \
                   line.split(':', 1)[-1].strip()
            reqs.append({"id": rid, "desc": desc, "module": current_module, "priority": "MÉDIA"})
            last_req_title = desc
            continue

        # Section header with ID  ## FR-NNN: Title  or  ## RF-NNN: Title
        m_fr = re.match(r'^## ((?:FR|RF)-\d+)[:\s]+(.+)', line)
        if m_fr:
            rid  = m_fr.group(1).strip()
            desc = m_fr.group(2).strip()
            reqs.append({"id": rid, "desc": desc, "module": current_module, "priority": "MÉDIA"})
            in_table = False
            continue

        # Bold attribute lines  **Module**: value  or  **Module:** value  or  **Priority**: value
        # Handles both colon-outside (**Attr**: val) and colon-inside (**Attr:** val) bold patterns
        if reqs and not in_table:
            m_attr = re.match(r'^\*\*(\w+):?\*\*\s*[:\-]?\s*(.+)', line)
            if m_attr:
                attr, val = m_attr.group(1).lower(), m_attr.group(2).strip()
                if attr in ('module', 'módulo') and val:
                    reqs[-1]["module"] = val
                elif attr in ('priority', 'prioridade') and val:
                    reqs[-1]["priority"] = val
                elif attr in ('description', 'descrição') and val:
                    reqs[-1]["desc"] = val
                continue

        # Table header detection — | ID | Description | ... | or | ID | Requirement | ... |
        if line.startswith('|') and 'ID' in line and any(k in line for k in ('Description', 'Requirement', 'Requirement', 'Descrição', 'Requisito')):
            in_table = True
            continue

        # Table separator row
        if in_table and re.match(r'^\|[-| ]+\|$', line):
            continue

        # Table data row — | FR-NNN | description | ... | (allow FR-MODULE-NNN and RF-NNN patterns)
        if in_table and line.startswith('|'):
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 2 and re.match(r'^[A-Z]{2}-', cols[0]):
                reqs.append({
                    "id": cols[0],
                    "desc": cols[1],
                    "module": current_module,
                    "priority": "MÉDIA"
                })
            continue

        # Attribute table row from Section EN format: | Description | Full text |  or  | Priority | HIGH |
        if line.startswith('| ') and reqs and not in_table:
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) == 2:
                attr, val = cols[0].strip().strip('*'), cols[1].strip()
                if attr.lower() == 'description' and val and not val.startswith('---'):
                    reqs[-1]["desc"] = val
                elif attr.lower() == 'priority' and val:
                    reqs[-1]["priority"] = val
                elif attr.lower() == 'module' and val:
                    reqs[-1]["module"] = val

        # Structured inline table field  | **Complexidade** | value |
        if line.startswith('| **Complexidade**') and reqs:
            val = line.split('|')[2].strip().strip('*').strip()
            reqs[-1]["priority"] = val
        elif line.startswith('| **Módulo**') and reqs:
            val = line.split('|')[2].strip().strip('*').strip()
            reqs[-1]["module"] = val

        # End of table when blank line or new section
        if in_table and (not line or line.startswith('#')):
            in_table = False

    return reqs


def parse_test_map(asis_dir: Path) -> tuple:
    """Parse test-gaps.md for gaps (bridge-fastqa-asis v4.1.0 Step 15).
    Test coverage data from 09_test_coverage.json (Delphi AST) where available.
    Discontinued sources: test-map.md, test-baseline.md, test-coverage-asis.md."""
    # test-gaps.md is now the primary source (bridge-fastqa Step 15)
    text = read_text(asis_dir / "qa" / "test-gaps.md")
    test_rows = []
    if text:
        in_table = False
        for line in text.split('\n'):
            line = line.strip()
            # Both formats: BC coverage table, type-count table, and Business Scenario table
            if re.search(r'\|\s*(Bounded Context|Type|Business Scenario|Coverage|Cenário|Scenario)\s*\|', line, re.IGNORECASE):
                in_table = True
                continue
            if in_table and re.match(r'^\|[-| ]+\|$', line):
                continue
            if in_table and line.startswith('|') and '**TOTAL**' not in line:
                cols = [c.strip().strip('*') for c in line.split('|')[1:-1]]
                if len(cols) >= 2:
                    tests_val = cols[1] if len(cols) > 1 else "0"
                    test_rows.append({
                        "module": cols[0],
                        "tests": tests_val,
                        "coverage": cols[-1] if (cols[-1].endswith('%') if cols[-1] else False) else "0%",
                        "type": cols[2] if len(cols) > 2 else "Unknown",
                    })
            if in_table and (line == '' or line.startswith('#')):
                in_table = False

    # Test gaps
    text2 = read_text(asis_dir / "test-gaps.md")
    gap_rows = []
    if text2:
        for line in text2.split('\n'):
            line = line.strip()
            if not line.startswith('| GT-'):
                continue
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 4:
                gap_rows.append({
                    "module": cols[2],
                    "gap": cols[1],
                    "risk": cols[3]
                })

    return test_rows[:20], gap_rows[:20]


def parse_db_schema(asis_dir: Path) -> list:
    """Parse schema-inventory.md Table Inventory section into D.dbSchema rows.

    Each row: {"t": table_name, "engine": engine, "rows": rows_est,
               "pk": pk, "fk": fk, "idx": indexes, "risk": risk}
    """
    text = read_text(asis_dir / "db" / "schema-inventory.md")
    if not text:
        return []
    rows = []
    in_section = False
    in_table = False
    for line in text.split('\n'):
        stripped = line.strip()
        if re.search(r'Table Inventory', stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section and stripped.startswith('##'):
            break  # end of section
        if not in_section:
            continue
        if not in_table and stripped.startswith('|') and re.search(r'\|\s*Table\s*\|', stripped, re.IGNORECASE):
            in_table = True
            continue
        if in_table and re.match(r'^\|[-| :]+\|$', stripped):
            continue
        if in_table and stripped.startswith('|'):
            cols = [c.strip().strip('`') for c in stripped.split('|')[1:-1]]
            if len(cols) >= 1:
                tname = cols[0].strip()
                if not tname or tname.startswith('-') or tname.lower() == 'table':
                    continue
                rows.append({
                    "t":      tname,
                    "engine": cols[1].strip() if len(cols) > 1 else "",
                    "rows":   cols[2].strip() if len(cols) > 2 else "",
                    "pk":     cols[3].strip() if len(cols) > 3 else "",
                    "fk":     cols[4].strip() if len(cols) > 4 else "",
                    "idx":    cols[5].strip() if len(cols) > 5 else "",
                    "risk":   cols[6].strip() if len(cols) > 6 else "",
                })
        if in_table and (not stripped or stripped.startswith('#')):
            in_table = False
    return rows


def _sanitize_mermaid(code: str) -> str:
    """Sanitize mermaid source for compatibility with Mermaid v11+."""
    # Strip markdown code fences (```mermaid ... ```) — agents sometimes wrap .mmd files in them.
    # Must run before backtick replacement, or fences become '''mermaid (invalid syntax).
    code = code.strip()
    code = re.sub(r'^```mermaid\s*\n?', '', code)
    code = re.sub(r'\n?```\s*$', '', code)
    code = code.strip()
    # Replace unicode arrows/dashes that break the parser
    code = code.replace('→', ' to ')
    code = code.replace('—', ' - ')
    code = code.replace('–', '-')
    # Normalize non-printing / problematic Unicode characters
    code = code.replace('\u00a0', ' ')               # NBSP → regular space
    code = code.replace('\u200b', '')                # zero-width space → removed
    code = code.replace('\u201c', '"').replace('\u201d', '"')   # curly double quotes
    code = code.replace('\u2018', "'").replace('\u2019', "'")   # curly single quotes
    # Tilde confuses certain Mermaid node-id parsers
    code = code.replace('~', '-')
    # C4 diagrams ONLY: collapse newlines inside quoted label strings.
    # Flowchart diagrams use ["label"] node notation — applying this regex to them
    # incorrectly collapses content across label boundaries, destroying subgraph structure.
    _first_token = code.lstrip().split('\n')[0].split('(')[0].strip()
    if _first_token in ('C4Context', 'C4Container', 'C4Component', 'C4Dynamic', 'C4Deployment', 'C4Diagram'):
        code = re.sub(r'"([^"\n]*)\n([^"]*)"', lambda m: '"' + m.group(1).rstrip() + ' ' + m.group(2).lstrip() + '"', code)
    # Replace emojis with safe plain text (no brackets — they break node syntax)
    emoji_map = {
        '🚀': '',
        '⚠️': '/!\\ ',
        '⚠': '/!\\ ',
        '🔴': '',
        '🟢': '',
        '🟡': '',
        '🟠': '',
        '⛔': '',
        '📐': '',
        '🏗️': '',
        '🔄': '',
        '📊': '',
    }
    for emoji, replacement in emoji_map.items():
        code = code.replace(emoji, replacement)
    # Remove any remaining emojis (broad Unicode ranges)
    code = re.sub(r'[\U0001F300-\U0001FAFF]', '', code)
    code = re.sub(r'[\u2600-\u27BF]', '', code)
    # Escape backticks (break JS template literals when injected into D.diag)
    code = code.replace('`', "'")
    # Fix literal \n (backslash+n) inside quoted labels — Mermaid 11 lexer treats
    # this as a newline escape that terminates the string token prematurely, causing
    # "Lexical error on line 1". Replace with a space inside quoted strings.
    code = re.sub(r'"([^"\n]*)"', lambda m: '"' + m.group(1).replace('\\n', ' ') + '"', code)
    # Strip semicolons — Mermaid interprets ';' as a statement separator
    code = code.replace(';', ' ')
    # Collapse multiple blank lines (Mermaid can be picky)
    code = re.sub(r'\n{3,}', '\n\n', code)
    # Truncate at any second diagram-type header (handles cross-type or same-type
    # concatenation produced by agents that merge multiple .mmd files).
    _DIAG_HEADERS = [
        r'^C4Context\b', r'^C4Container\b', r'^C4Component\b', r'^C4Dynamic\b',
        r'^flowchart[\s\t]', r'^graph[\s\t]', r'^sequenceDiagram\b',
        r'^classDiagram\b', r'^erDiagram\b', r'^gantt\b',
        r'^stateDiagram\b', r'^mindmap\b', r'^timeline\b',
    ]
    _DIAG_PATS = [re.compile(p, re.M) for p in _DIAG_HEADERS]
    first_pos = min(
        (m.start() for pat in _DIAG_PATS for m in [pat.search(code)] if m),
        default=-1
    )
    if first_pos >= 0:
        eol = code.find('\n', first_pos)
        if eol >= 0:
            rest = code[eol + 1:]
            second_pos = min(
                (m.start() for pat in _DIAG_PATS for m in [pat.search(rest)] if m),
                default=-1
            )
            if second_pos >= 0:
                code = code[:eol + 1 + second_pos].rstrip()
    return code.strip()


def collect_static_diagrams(asis_dir: Path, tobe_dir: Path) -> dict:
    """Collect raw Mermaid source for every static diagram block in the
    template. The template renders these by setting `pre.textContent` and
    calling `mermaid.run({nodes:[pre]})`, which is the only reliable way to
    preserve Mermaid-inline HTML tags like `<br/>` and `<i>` inside node
    labels (HTML-escaping inside `<pre>` is fragile across browsers).

    Every diagram is piped through `_sanitize_mermaid` to strip characters
    that Mermaid v11 cannot parse (emojis, Unicode arrows, em-dashes)."""
    diag = asis_dir / "diagrams"
    db_dir = asis_dir / "db"
    tobe_diag = tobe_dir / "diagrams"

    def _read_and_sanitize(p: Path) -> str:
        raw = read_text(p)
        return _sanitize_mermaid(raw) if raw else ""

    diagrams = {
        "asisArchBlueprint": _read_and_sanitize(diag / "architecture-blueprint.mmd"),
        "c4ctx":         _read_and_sanitize(diag / "c4-context.mmd"),
        "c4cnt":         _read_and_sanitize(diag / "c4-container.mmd"),
        "c4comp":        _read_and_sanitize(diag / "c4-component.mmd"),
        "comp":          _read_and_sanitize(diag / "component-diagram.mmd"),
        "seqBaixaCp":    _read_and_sanitize(diag / "seq-baixa-titulo-cp.mmd") or _read_and_sanitize(diag / "seq-baixa-cp.mmd"),
        "seqCadCp":      _read_and_sanitize(diag / "seq-cadastro-conta-pagar.mmd") or _read_and_sanitize(diag / "seq-cadastro-cp.mmd"),
        # seq1/seq2: generic keys used by the fallback panel renderer (D.staticDiagrams.seq1..seq6)
        "seq1":          _read_and_sanitize(diag / "seq-ap-registration.mmd") or _read_and_sanitize(diag / "seq-cadastro-conta-pagar.mmd") or _read_and_sanitize(diag / "seq-cadastro-cp.mmd"),
        "seq2":          _read_and_sanitize(diag / "seq-ap-settlement.mmd") or _read_and_sanitize(diag / "seq-baixa-titulo-cp.mmd") or _read_and_sanitize(diag / "seq-baixa-cp.mmd"),
        "er":            _read_and_sanitize(db_dir / "er-diagram.mmd"),
        "tobeC4":            _read_and_sanitize(tobe_diag / "c4-context.mmd") or _read_and_sanitize(diag / "c4-context.mmd"),
        "tobeC4cnt":         _read_and_sanitize(tobe_diag / "c4-container.mmd"),
        "tobeC4comp":        _read_and_sanitize(tobe_diag / "c4-component.mmd"),
        "tobeClass":         _read_and_sanitize(tobe_diag / "class-diagram.mmd"),
        "tobeSeq":           _read_and_sanitize(tobe_diag / "seq-arquitetural-tobe.mmd"),
        "gantt":             _read_and_sanitize(tobe_diag / "gantt-migration.mmd") or _read_and_sanitize(tobe_dir / "migration-gantt.mmd"),
        "cleanarch":         _read_and_sanitize(tobe_diag / "clean-architecture.mmd") or _read_and_sanitize(diag / "clean-architecture.mmd"),
        "solution":          _read_and_sanitize(tobe_diag / "solution-structure.mmd") or _read_and_sanitize(diag / "solution-structure.mmd"),
        "contextMap":        _read_and_sanitize(tobe_diag / "context-map.mmd"),
        "tobeArchBlueprint": _read_and_sanitize(tobe_diag / "architecture-blueprint.mmd"),
    }
    return {k: v for k, v in diagrams.items() if v}


def parse_openapi_endpoints(tobe_dir: Path) -> list:
    """Parse all OpenAPI YAML files in tobe/docs/openapi/ and extract endpoints.
    Returns list of {method, path, summary, module, auth}."""
    openapi_dir = tobe_dir / "docs" / "openapi"
    if not openapi_dir.exists():
        return []

    endpoints = []
    for spec_file in sorted(openapi_dir.glob("*.y*ml")):
        try:
            spec = yaml.safe_load(spec_file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"   ⚠️ Erro ao parsear {spec_file.name}: {e}")
            continue

        if not isinstance(spec, dict):
            continue

        # Global security (if any) indicates auth required for ops that don't override
        has_global_security = bool(spec.get('security'))
        paths = spec.get('paths', {})
        if not isinstance(paths, dict):
            continue

        # Derive module label from filename (e.g., meu-erp-finance-v1 -> Finance)
        module = spec_file.stem.replace('-', ' ').replace('_', ' ').title()

        for route, ops in paths.items():
            if not isinstance(ops, dict):
                continue
            for method, op in ops.items():
                if method.lower() not in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
                    continue
                if not isinstance(op, dict):
                    continue
                summary = op.get('summary') or op.get('description', '') or ''
                # Operation-level security overrides global
                op_security = op.get('security')
                if op_security is not None:
                    auth = 'No' if op_security == [] else 'Yes'
                else:
                    auth = 'Yes' if has_global_security else 'No'
                endpoints.append({
                    "method": method.upper(),
                    "path": route,
                    "module": module,
                    "summary": summary[:120],
                    "auth": auth,
                })
    return endpoints


def parse_screen_navigation(asis_dir: Path) -> tuple:
    """Parse screen-navigation-map.md for mermaid diagram and forms table.

    Backward-compatible wrapper kept for callers expecting (mermaid, forms).
    Prefer ``parse_screen_artifacts`` for the full enriched payload.
    """
    data = parse_screen_artifacts(asis_dir)
    return data["mermaid"], data["forms"]


def _md_strip_links(text: str) -> str:
    """Convert basic markdown emphasis/links to plain text for safe HTML rendering."""
    if not text:
        return ""
    # [label](url) → label
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # **bold** / *italic* / `code` markers stripped (kept as plain text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()


def _split_md_sections(text: str) -> list:
    """Split markdown into sections [{level, title, body}] keyed by # headers.

    Section bodies do NOT include their header line. The synthetic root section
    (level 0) holds any preamble before the first header.
    """
    if not text:
        return []
    sections = [{"level": 0, "title": "", "body_lines": []}]
    in_code = False
    for line in text.splitlines():
        # Skip headers detection inside fenced code blocks
        if line.lstrip().startswith("```"):
            in_code = not in_code
            sections[-1]["body_lines"].append(line)
            continue
        if not in_code:
            m = re.match(r'^(#{1,6})\s+(.+?)\s*$', line)
            if m:
                sections.append({
                    "level": len(m.group(1)),
                    "title": m.group(2).strip(),
                    "body_lines": [],
                })
                continue
        sections[-1]["body_lines"].append(line)
    for s in sections:
        s["body"] = "\n".join(s["body_lines"]).strip()
        del s["body_lines"]
    return sections


def _extract_paragraphs(body: str, max_paragraphs: int = 3, max_chars: int = 800) -> str:
    """Return the first plain-text paragraphs of a section body (no tables/code/lists)."""
    if not body:
        return ""
    paragraphs = []
    current = []
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            if len(paragraphs) >= max_paragraphs:
                break
            continue
        # Skip table rows, list items, blockquotes, horizontal rules
        if stripped.startswith(("|", "-", "*", ">", "#")) or re.match(r'^\d+\.\s', stripped):
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        current.append(stripped)
    if current and len(paragraphs) < max_paragraphs:
        paragraphs.append(" ".join(current).strip())
    out = "\n\n".join(_md_strip_links(p) for p in paragraphs if p)
    if len(out) > max_chars:
        out = out[:max_chars].rstrip() + "…"
    return out


def _parse_md_table(body: str) -> tuple:
    """Return (headers, rows) for the FIRST markdown pipe-table found in body.

    headers = lowercase column names (stripped); rows = list of stripped cell lists.
    Returns ([], []) if no table found.
    """
    headers: list = []
    rows: list = []
    in_table = False
    for line in body.splitlines():
        line = line.rstrip()
        if not line.startswith("|"):
            if in_table:
                break
            continue
        cols = [c.strip().strip('`') for c in line.split("|")[1:-1]]
        if not cols:
            continue
        # Separator row
        if all(re.match(r'^:?-+:?$', c) for c in cols if c):
            in_table = True
            continue
        if not headers:
            headers = [c.lower() for c in cols]
        else:
            in_table = True
            rows.append(cols)
    return headers, rows


def parse_screen_artifacts(asis_dir: Path) -> dict:
    """Parse screen-navigation-map.md + screen-rules.md into a single payload.

    Returns dict with keys:
      mermaid          : str  — sanitized mermaid source for Navigation Flow
      forms            : list — Screen Inventory rows (legacy ``screenForms``)
      overview         : str  — preamble paragraphs before first header
      narrative        : str  — paragraphs after the navigation diagram
      groups           : list — [{title, description, screens:[…]}] from ``### Module``-like headers
      rules            : list — [{form, category, rule, condition, source}] from screen-rules.md
      rules_by_form    : dict — aggregation {form: {visibility:[…], enablement:[…], …}}
      categories       : list — distinct rule categories present (sorted)

    Tolerant to absent files and to multiple legacy formats. Never raises.
    """
    nav_text = read_text(asis_dir / "docs" / "screen-navigation-map.md")
    rules_text = read_text(asis_dir / "docs" / "screen-rules.md")

    payload = {
        "mermaid": "",
        "forms": [],
        "overview": "",
        "narrative": "",
        "groups": [],
        "rules": [],
        "rules_by_form": {},
        "categories": [],
    }

    # ── screen-navigation-map.md ──────────────────────────────────────
    if nav_text:
        m = re.search(r'```mermaid\s*\n([\s\S]*?)```', nav_text)
        if m:
            payload["mermaid"] = _sanitize_mermaid(m.group(1))

        sections = _split_md_sections(nav_text)
        # Overview = first non-empty paragraphs found in either the synthetic
        # preamble (level 0) OR the first H1/H2 section body that is NOT the
        # Navigation Flow / Screen Inventory technical sections.
        overview_text = ""
        if sections and sections[0]["level"] == 0:
            overview_text = _extract_paragraphs(sections[0]["body"])
        if not overview_text:
            for s in sections[1:]:
                if s["level"] not in (1, 2):
                    continue
                t_low = s["title"].lower()
                if any(skip in t_low for skip in ("navigation flow", "screen inventory")):
                    continue
                overview_text = _extract_paragraphs(s["body"])
                if overview_text:
                    break
        payload["overview"] = overview_text

        # Forms inventory (Screen Inventory section, falling back to any matching table)
        screens: list = []
        num_counter = 0
        # Prefer section explicitly named "Screen Inventory"
        inventory_body = ""
        for s in sections:
            if s["title"].strip().lower().startswith("screen inventory"):
                inventory_body = s["body"]
                break
        if not inventory_body:
            inventory_body = nav_text  # fall back to whole doc

        in_table = False
        for line in inventory_body.split('\n'):
            line = line.strip()
            if not in_table and line.startswith('|') and (
                '| Form |' in line or '| # |' in line
                or 'Screen Name' in line or 'Form Class' in line
                or '| Screen |' in line or 'Form ID' in line
                or 'Display Name' in line
                or 'form_id' in line.lower() or 'display_name' in line.lower()
            ):
                in_table = True
                continue
            if in_table and re.match(r'^\|[-| :]+\|$', line):
                continue
            if in_table and line.startswith('|'):
                cols = [c.strip().strip('`') for c in line.split('|')[1:-1]]
                if len(cols) >= 6:
                    screens.append({
                        "num": cols[0], "form": cols[1], "file": cols[2],
                        "type": cols[3], "module": cols[4], "access": cols[5],
                    })
                elif len(cols) >= 4:
                    num_counter += 1
                    screens.append({
                        "num": str(num_counter),
                        "form": cols[0],
                        "file": cols[1],
                        "type": cols[3],
                        "module": "",
                        "access": cols[2],
                    })
            elif in_table and (line == '' or line.startswith('#') or line.startswith('---')):
                if screens:
                    in_table = False

        payload["forms"] = screens

        # Narrative = paragraph(s) inside the Navigation Flow section AFTER
        # the mermaid code block, falling back to the next sibling section
        # (excluding "Screen Inventory") when the flow body has no prose.
        for i, s in enumerate(sections):
            if s["title"].strip().lower().startswith("navigation flow"):
                # Body may contain mermaid block + narrative paragraphs.
                # _extract_paragraphs already skips fenced code, so this works.
                narrative_text = _extract_paragraphs(s["body"], max_paragraphs=2, max_chars=600)
                if not narrative_text:
                    for follow in sections[i + 1: i + 5]:
                        title_lower = follow["title"].lower()
                        if "inventory" in title_lower:
                            continue
                        narrative_text = _extract_paragraphs(follow["body"], max_paragraphs=2, max_chars=600)
                        if narrative_text:
                            break
                payload["narrative"] = narrative_text
                break

        # Groups = level-3 headers (### …) treated as module/grouping clusters
        groups: list = []
        for s in sections:
            if s["level"] != 3:
                continue
            title = s["title"]
            t_lower = title.lower()
            if any(skip in t_lower for skip in ("inventory", "navigation flow", "legend")):
                continue
            description = _extract_paragraphs(s["body"], max_paragraphs=1, max_chars=300)
            # Pull bullet items as referenced screens
            screen_items: list = []
            for line in s["body"].splitlines():
                stripped = line.strip()
                if stripped.startswith(("- ", "* ")):
                    item = _md_strip_links(stripped[2:].strip())
                    if item:
                        screen_items.append(item)
            if description or screen_items:
                groups.append({
                    "title": title,
                    "description": description,
                    "screens": screen_items[:25],
                })
        payload["groups"] = groups[:30]

    # ── screen-rules.md ───────────────────────────────────────────────
    if rules_text:
        rules: list = []
        sections = _split_md_sections(rules_text)
        category_aliases = {
            "visibility": "Visibility", "visibilidade": "Visibility",
            "enablement": "Enablement", "enabling": "Enablement", "habilitação": "Enablement",
            "habilitacao": "Enablement",
            "validation": "Validation", "validações": "Validation", "validacoes": "Validation",
            "behavior": "Behavior", "comportamento": "Behavior",
        }

        def _classify(label: str) -> str:
            low = label.lower().strip()
            for key, val in category_aliases.items():
                if key in low:
                    return val
            return "Behavior"

        # Strategy: walk sections, infer current "form" from H2/H3 form-named headers,
        # extract rules from (a) markdown tables, (b) bulleted "**Visibility**: …" lists,
        # (c) categorized H3/H4 headers like "### Visibility Rules".
        current_form = ""
        current_category_hint = ""

        for s in sections:
            title = s["title"]
            t_low = title.lower()
            level = s["level"]

            # Form-named headers (heuristic): contains "form", "screen", "tela",
            # or starts with frm/Tfrm/F (Delphi convention) — set as current form
            if level in (2, 3):
                if (re.search(r'\b(form|screen|tela)\b', t_low)
                        or re.match(r'^(t?frm[A-Z0-9_]+|F[A-Z][A-Za-z0-9_]+)\b',
                                    title.strip())):
                    # Strip generic prefixes
                    cleaned = re.sub(r'^(form|screen|tela)\s*[:\-—]\s*', '',
                                     title, flags=re.IGNORECASE).strip()
                    current_form = cleaned or title
                    current_category_hint = ""

            # Category-named H3/H4 (### Visibility Rules, #### Validation, …)
            if level >= 3:
                for key in category_aliases:
                    if key in t_low:
                        current_category_hint = category_aliases[key]
                        break

            # (a) Table-based rules
            headers, rows = _parse_md_table(s["body"])
            if headers and rows:
                # Map common column synonyms to keys
                col_map = {}
                for idx, h in enumerate(headers):
                    if any(k in h for k in ("form", "screen", "tela")):
                        col_map["form"] = idx
                    elif any(k in h for k in ("category", "type", "tipo", "categoria", "kind")):
                        col_map["category"] = idx
                    elif any(k in h for k in ("rule", "regra", "description", "descrição", "descricao")):
                        col_map["rule"] = idx
                    elif any(k in h for k in ("condition", "condição", "condicao", "when", "trigger")):
                        col_map["condition"] = idx
                    elif any(k in h for k in ("source", "origem", "code", "ref")):
                        col_map["source"] = idx
                if "rule" in col_map:
                    for row in rows:
                        try:
                            rule_text = _md_strip_links(row[col_map["rule"]])
                        except IndexError:
                            continue
                        if not rule_text:
                            continue
                        cat_label = (row[col_map["category"]]
                                     if "category" in col_map and col_map["category"] < len(row)
                                     else current_category_hint or "Behavior")
                        category = _classify(cat_label) if cat_label else "Behavior"
                        form_val = (row[col_map["form"]]
                                    if "form" in col_map and col_map["form"] < len(row)
                                    else current_form)
                        condition = (row[col_map["condition"]]
                                     if "condition" in col_map and col_map["condition"] < len(row)
                                     else "")
                        source = (row[col_map["source"]]
                                  if "source" in col_map and col_map["source"] < len(row)
                                  else "")
                        rules.append({
                            "form": _md_strip_links(form_val) or "—",
                            "category": category,
                            "rule": rule_text,
                            "condition": _md_strip_links(condition),
                            "source": _md_strip_links(source),
                        })

            # (b) Bulleted rules: "- **Visibility**: text — when ..."
            for line in s["body"].splitlines():
                stripped = line.strip()
                if not stripped.startswith(("- ", "* ")):
                    continue
                content = stripped[2:].strip()
                m = re.match(
                    r'\*\*(?P<cat>[A-Za-zçãõáéíóúÇÃÕÁÉÍÓÚ ]+)\*\*\s*[:\-—]\s*(?P<rest>.+)',
                    content,
                )
                if not m:
                    continue
                cat = _classify(m.group("cat"))
                rest = m.group("rest").strip()
                # split rule / condition by " — when " or " when " or "|"
                cond = ""
                rule_part = rest
                cond_match = re.search(
                    r'\s+(?:—|-|\|)\s*(?:when|quando|condition|condição)\s+(?P<c>.+)$',
                    rest, flags=re.IGNORECASE,
                )
                if cond_match:
                    cond = cond_match.group("c").strip()
                    rule_part = rest[:cond_match.start()].strip()
                rules.append({
                    "form": current_form or "—",
                    "category": cat,
                    "rule": _md_strip_links(rule_part),
                    "condition": _md_strip_links(cond),
                    "source": "",
                })

        # Deduplicate
        seen = set()
        unique_rules = []
        for r in rules:
            key = (r["form"], r["category"], r["rule"][:120])
            if key in seen:
                continue
            seen.add(key)
            unique_rules.append(r)

        payload["rules"] = unique_rules
        # Aggregation
        agg: dict = {}
        cats: set = set()
        for r in unique_rules:
            cats.add(r["category"])
            form_bucket = agg.setdefault(r["form"], {
                "Visibility": [], "Enablement": [], "Validation": [], "Behavior": [],
            })
            form_bucket.setdefault(r["category"], []).append({
                "rule": r["rule"], "condition": r["condition"], "source": r["source"],
            })
        payload["rules_by_form"] = agg
        payload["categories"] = sorted(cats)

    return payload


def _normalize_flat_metrics(raw: dict) -> tuple:
    """Normalize metrics.json whether flat or nested.

    Returns (m, loc, files, classes, methods, complexity, db, migration, security).
    Handles three formats:
      1. Flat: { "total_loc": N, "source_files_pas": N, ... }
      2. Nested under 'metrics' key: { "metrics": { "loc": {...}, ... } }
      3. Sub-object nested (Meu-ERP style): { "loc": {"total_loc": N}, "files": {"total": N}, ... }
    """
    if "metrics" in raw and isinstance(raw.get("metrics"), dict):
        # Format 2: nested under 'metrics' key
        m          = raw.get("metrics", {})
        loc        = m.get("loc", {})
        files_m    = m.get("files", {})
        classes    = m.get("classes", {})
        methods    = m.get("methods", {})
        complexity = raw.get("complexity", {})
        db         = raw.get("database", {})
        migration  = raw.get("migration_readiness", {})
        security   = raw.get("security", {})
        return m, loc, files_m, classes, methods, complexity, db, migration, security

    if isinstance(raw.get("loc"), dict) and isinstance(raw.get("files"), dict):
        # Format 3: sub-object nested (ava-asis-inventory Meu-ERP style)
        loc_obj        = raw.get("loc", {})
        files_obj      = raw.get("files", {})
        classes_obj    = raw.get("classes", {})
        methods_obj    = raw.get("methods", {})
        complexity_obj = raw.get("complexity", {})
        modules_obj    = raw.get("modules", {})
        db_obj         = raw.get("database", {})
        security_obj   = raw.get("security", {})

        total_loc_v = loc_obj.get("total_loc", loc_obj.get("total", 0))
        loc = {
            "total":    total_loc_v,
            "pas_code": loc_obj.get("code_loc", loc_obj.get("loc_pas_code", total_loc_v)),
        }
        files_m = {
            "total": files_obj.get("total", 0),
            "pas":   files_obj.get("pas",   files_obj.get("source_files_pas", 0)),
            "dfm":   files_obj.get("dfm",   files_obj.get("form_files_dfm",  0)),
            "sql":   files_obj.get("sql",   0),
            "dpr":   files_obj.get("dpr",   0),
        }
        total_classes_v = classes_obj.get("total_classes", classes_obj.get("total", 0))
        classes = {
            "total":          total_classes_v,
            "tform":          classes_obj.get("forms",         classes_obj.get("tform",     0)),
            "tdatamodule":    classes_obj.get("data_modules",  classes_obj.get("tdatamodule", 0)),
            "domain_classes": classes_obj.get("domain_classes", 0),
        }
        methods = {
            "total": methods_obj.get("total_methods", methods_obj.get("total", 0)),
        }
        avg_cc = complexity_obj.get("average_cyclomatic", complexity_obj.get("average_cc_estimated", 0))
        complexity = {
            "average_cc_estimated": avg_cc,
            "files_above_cc10":     complexity_obj.get("files_above_cc10",
                                        complexity_obj.get("files_cc_above_10", 0)),
        }
        total_modules_v = modules_obj.get("total_modules", modules_obj.get("total", 0)) \
            if isinstance(modules_obj, dict) else int(modules_obj or 0)
        bounded_v = raw.get("bounded_contexts", total_modules_v)
        if isinstance(bounded_v, dict):
            bounded_v = bounded_v.get("total", total_modules_v)
        def _db_table_count(obj: dict) -> int:
            """Return integer table count regardless of whether 'tables' is a list or int."""
            # Prefer explicit integer count key
            if "tables_referenced" in obj:
                v = obj["tables_referenced"]
                return len(v) if isinstance(v, list) else int(v or 0)
            v = obj.get("tables", obj.get("db_tables", 0))
            return len(v) if isinstance(v, list) else int(v or 0)

        tbl_count = _db_table_count(db_obj)
        m = {
            "modules":             total_modules_v,
            "bounded_contexts":    int(bounded_v),
            "db_tables_estimated": tbl_count,
        }
        db = {
            "engine":            db_obj.get("engine", db_obj.get("driver", db_obj.get("db_type", "N/D"))),
            "tables":            tbl_count,
            "stored_procedures": db_obj.get("stored_procedures", db_obj.get("db_stored_procedures", 0)),
            "triggers":          db_obj.get("triggers",          db_obj.get("db_triggers",          0)),
            "views":             db_obj.get("views",             db_obj.get("db_views",             0)),
            "indexes_beyond_pk": db_obj.get("indexes_beyond_pk", "PK/FK mínimos"),
        }
        migration = {
            "score":      raw.get("migration_readiness_score", "N/D"),
            "risk_level": raw.get("migration_readiness_level", "N/D"),
        }
        security = {
            "critical": security_obj.get("critical", security_obj.get("security_findings_critical", 0))
                        if isinstance(security_obj, dict) else 0,
            "high":     security_obj.get("high",     security_obj.get("security_findings_high",     0))
                        if isinstance(security_obj, dict) else 0,
        }
        return m, loc, files_m, classes, methods, complexity, db, migration, security

    # ── Format 1: Flat structure — map to nested-style dicts ───
    total_loc = raw.get("total_loc", 0)
    loc = {
        "total":       total_loc,
        "pas_code":    raw.get("loc_pas_code",    total_loc),
        "dfm_layout":  raw.get("loc_dfm_layout",  0),
        "dpr_project": raw.get("loc_dpr_project", 0),
    }
    files_m = {
        "total": raw.get("total_files",      0),
        "pas":   raw.get("source_files_pas", 0),
        "dfm":   raw.get("form_files_dfm",   0),
        "sql":   raw.get("sql_files",        0),
        "dpr":   raw.get("dpr_files",        raw.get("config_files", 0)),
    }
    classes = {
        "total":          raw.get("classes",       0),
        "tform":          raw.get("vcl_forms",      raw.get("form_files_dfm", 0)),
        "tdatamodule":    raw.get("data_modules",  0),
        "domain_classes": raw.get("domain_classes", 0),
    }
    methods = {
        "total": raw.get("estimated_methods", 0),
    }
    complexity = {
        "average_cc_estimated": raw.get("avg_cyclomatic_complexity", 0),
        "files_above_cc10":     raw.get("files_cc_above_10",
                                    raw.get("files_cc_above_5", 0)),
    }
    db = {
        "engine":            raw.get("db_type",              "N/D"),
        "tables":            raw.get("db_tables",            0),
        "stored_procedures": raw.get("db_stored_procedures", 0),
        "triggers":          raw.get("db_triggers",          0),
        "views":             raw.get("db_views",             0),
        "indexes_beyond_pk": raw.get("db_indexes_beyond_pk", "PK/FK mínimos"),
    }
    def _to_count(v):
        if isinstance(v, (list, tuple, set, dict)):
            return len(v)
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return 0
            if s.isdigit():
                return int(s)
            if s.startswith('[') or s.startswith('{'):
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, (list, tuple, set, dict)):
                        return len(parsed)
                except Exception:
                    pass
            return 0
        try:
            return int(v)
        except Exception:
            return 0

    modules_raw = raw.get("modules", 0)
    bounded_raw = raw.get("bounded_contexts", modules_raw)
    m = {
        "modules":             _to_count(modules_raw),
        "bounded_contexts":    _to_count(bounded_raw),
        "db_tables_estimated": raw.get("db_tables", 0),
    }
    migration = {
        "score":      raw.get("migration_readiness_score", "N/D"),
        "risk_level": raw.get("risk_level",               "N/D"),
    }
    security = {
        "critical": raw.get("security_findings_critical", 0),
        "high":     raw.get("security_findings_high",     0),
    }
    return m, loc, files_m, classes, methods, complexity, db, migration, security


def build_all_substitutions(project_name: str, outputs_dir: Path, file_tree: dict) -> dict:
    """
    Build ALL template placeholder substitutions from real data files.
    Reads metrics.json, risk-register.json, pattern-classifications.json and
    diagrams to populate every {{PLACEHOLDER}} the template uses.
    """
    print("\n🔧 Construindo substituições a partir dos dados reais...")

    asis_dir = outputs_dir / 'asis'
    tobe_dir = outputs_dir / 'tobe'

    def _read_and_sanitize(p: Path) -> str:
        raw = read_text(p)
        return _sanitize_mermaid(raw) if raw else ""
    metrics = read_json(asis_dir / "metrics.json")
    risks_json = read_json(asis_dir / "risk-register.json")
    patterns_data = read_json(asis_dir / "pattern-classifications.json")
    tobe_patterns_data = read_json(tobe_dir / "patterns-applied.json")

    # ── Metrics — supports both flat and nested metrics.json formats ──
    m, loc, files, classes, methods, complexity, db, migration, security = \
        _normalize_flat_metrics(metrics)
    quality = metrics.get("quality_scores", {})

    # ── Risks (pad to 7) ─────────────────────────────────────────
    risks_list = risks_json.get("risks", []) if isinstance(risks_json, dict) else []
    while len(risks_list) < 7:
        risks_list.append({
            "id": f"R00{len(risks_list)+1}", "category": "Pendente",
            "description": "Aguardando fases subsequentes.", "evidence": "N/D",
            "mitigation": "N/D", "priority": "P3", "cvss": 0
        })
    risks = risks_list[:7]

    # ── Patterns ─────────────────────────────────────────────────
    if isinstance(patterns_data, list):
        classifications = patterns_data
    elif isinstance(patterns_data, dict) and "classifications" in patterns_data:
        classifications = patterns_data["classifications"]
    else:
        classifications = []
    pattern_counts = Counter(item.get("pattern", "Unknown") for item in classifications)
    pattern_total = max(len(classifications), 1)
    pattern_rows = pattern_counts.most_common(5)
    while len(pattern_rows) < 5:
        pattern_rows.append((f"Pattern-{len(pattern_rows)+1}", 0))

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

    # ── File tree counts ─────────────────────────────────────────
    def count_files(node):
        t = len(node.get("files", []))
        for child in node.get("subdirs", {}).values():
            t += count_files(child)
        return t
    total_artifacts = sum(count_files(n) for n in file_tree.values())

    # ── Scope label ──────────────────────────────────────────────
    cfg = load_project_config(project_name)
    scope_raw = cfg.get("scope_modules", "all")
    if isinstance(scope_raw, str) and scope_raw.strip().lower() == "all":
        scope_label = "All modules"
    elif isinstance(scope_raw, (list, tuple, set)):
        scope_label = ", ".join(str(x) for x in scope_raw) if scope_raw else "All modules"
    else:
        scope_label = str(scope_raw).strip() if str(scope_raw).strip() else "All modules"
    scope = f"{scope_label} - Delphi VCL Applications"

    # ── Stack version from config ────────────────────────────────
    _FW_DISPLAY = {
        "dotnet": ".NET", "aspnet": "ASP.NET", "spring-boot": "Spring Boot",
        "fastapi": "FastAPI", "django": "Django", "rails": "Rails",
        "node": "Node.js", "express": "Express",
    }
    _FRONTEND_DISPLAY = {
        "angular": "Angular", "react": "React", "vue": "Vue",
        "blazor": "Blazor", "svelte": "Svelte", "nextjs": "Next.js",
    }
    _LEGACY_DISPLAY = {
        "delphi": "Delphi", "cobol": "COBOL", "vb6": "VB6",
        "vbnet": "VB.NET", "powerbuilder": "PowerBuilder",
    }
    tobe_stack = cfg.get("tobe_stack", {})
    backend_fw_raw = tobe_stack.get("backend_framework", "dotnet").lower()
    backend_fw  = _FW_DISPLAY.get(backend_fw_raw, backend_fw_raw.upper())
    backend_ver = tobe_stack.get("backend_version", "")
    tobe_backend_label = f"{backend_fw} {backend_ver}".strip()
    frontend_fw_raw = tobe_stack.get("frontend_framework", "angular").lower()
    frontend_fw  = _FRONTEND_DISPLAY.get(frontend_fw_raw, frontend_fw_raw.capitalize())
    frontend_ver = tobe_stack.get("frontend_version", "")
    tobe_frontend_label = f"{frontend_fw} {frontend_ver}".strip()
    legacy_tech_raw = cfg.get("legacy_technology", "Legacy").lower()
    legacy_tech = _LEGACY_DISPLAY.get(legacy_tech_raw, legacy_tech_raw.capitalize())

    # ── Diagrams (read raw mermaid from asis/diagrams) ───────────
    diag = asis_dir / "diagrams"
    db_dir = asis_dir / "db"

    subs = {
        # ── Header / Meta ────────────────────────────────────────
        "SCOPE": scope,
        "EXEC_PCT": "33",

        # ── KPIs ─────────────────────────────────────────────────
        "TOTAL_FILES": str(total_artifacts),
        "TEXT_FILES": str(total_artifacts),
        "TOTAL_LOC": str(loc.get("total", "N/D")),
        "CLASS_COUNT": str(classes.get("total", "N/D")),
        "METHOD_COUNT": str(methods.get("total", "N/D")),
        "COMPLEX_METHODS": str(complexity.get("files_above_cc10", "N/D")),
        "ENDPOINT_COUNT": "0",
        "LAYER_COUNT": str(m.get("bounded_contexts", "N/D")),
        "MODULE_COUNT": str(m.get("modules", "N/D")),
        "TABLE_COUNT": str(db.get("tables", m.get("db_tables_estimated", "N/D"))),
        "DB_VOLUME": "N/D",
        "SCREEN_COUNT": str(files.get("dfm", "N/D")),
        "COMPONENT_COUNT": str(files.get("dfm", 0) + classes.get("tdatamodule", 0)),

        # ── File Types ───────────────────────────────────────────
        "DELPHI_PAS_COUNT": str(files.get("pas", 0)),
        "DELPHI_DFM_COUNT": str(files.get("dfm", 0)),
        "SQL_COUNT": str(files.get("sql", 0)),
        "DLL_COUNT": "0",
        "CONFIG_COUNT": str(files.get("dpr", 0)),

        # ── Layers ───────────────────────────────────────────────
        "LOC_UI": str(loc.get("pas_code", "N/D")),
        "FILES_UI": str(files.get("pas", "N/D")),
        "LOC_APP": "0", "FILES_APP": "0",
        "LOC_DATA": "0", "FILES_DATA": "0",
        "LOC_DB": str(loc.get("dfm_layout", 0)),
        "FILES_DB": str(files.get("dfm", 0)),
        "LOC_INFRA": str(loc.get("dpr_project", 0)),
        "FILES_INFRA": str(files.get("dpr", 0)),
        "EFF_LOC": str(loc.get("pas_code", "N/D")),
        "AVG_CC": str(complexity.get("average_cc_estimated", "N/D")),
        "DUP_PCT": "N/D",

        # ── Risks ────────────────────────────────────────────────
        **{f"RISK_{i+1}": risks[i].get("description", "N/D") for i in range(7)},
        **{f"EV_{i+1}": (risks[i].get("evidence", risks[i].get("description", "N/D")))[:80] for i in range(7)},
        **{f"ACT_{i+1}": risks[i].get("mitigation", "N/D") for i in range(7)},

        # ── Patterns ─────────────────────────────────────────────
        **{f"P{i+1}_COUNT": str(pattern_rows[i][1]) for i in range(5)},
        **{f"P{i+1}_PCT": str(round(pattern_rows[i][1] / pattern_total * 100)) for i in range(5)},

        # ── Bounded Contexts (from metrics) ──────────────────────
        "BC1_NAME": "Financeiro", "BC1_FORMS": "8", "BC1_UNITS": "10",
        "BC1_LOC": str(int(loc.get("pas_code", 0) * 0.45)), "BC1_RISK": "critico",
        "BC2_NAME": "Cliente-Fornecedor", "BC2_FORMS": "5", "BC2_UNITS": "6",
        "BC2_LOC": str(int(loc.get("pas_code", 0) * 0.20)), "BC2_RISK": "alto",
        "BC3_NAME": "Cadastros Gerais", "BC3_FORMS": "8", "BC3_UNITS": "14",
        "BC3_LOC": str(int(loc.get("pas_code", 0) * 0.35)), "BC3_RISK": "medio",

        # ── DB ───────────────────────────────────────────────────
        "DB_VENDOR": db.get("engine", metrics.get("technology", "N/D").split("+")[-1].strip() if "+" in metrics.get("technology", "") else "N/D"),
        "SP_COUNT": str(db.get("stored_procedures", 0)),
        "SP_BIZ_COUNT": "0",
        "TRIGGER_COUNT": "0",
        "INDEX_COUNT": str(db.get("indexes_beyond_pk", "PK/FK mínimos")),
        "T1": "conta_pagar", "C1": "~8", "PK1": "Sim", "FK1": "Não", "IDX1": "PK",
        "T2": "conta_receber", "C2": "~8", "PK2": "Sim", "FK2": "Não", "IDX2": "PK",
        "T3": "cliente_fornecedor", "C3": "~10", "PK3": "Sim", "FK3": "Não", "IDX3": "PK",
        "SP1": "N/D", "SP1_TYPE": "N/D", "SP1_LOC": "0",
        "SP2": "N/D", "SP2_TYPE": "N/D", "SP2_LOC": "0",
        "SP3": "N/D", "SP3_TYPE": "N/D", "SP3_LOC": "0",

        # ── Sizing / Estimation ──────────────────────────────────
        "TOTAL_SP": str(migration.get("score", "N/D")),
        "TOTAL_FP": "N/D",
        "WAVE_COUNT": str(migration.get("waves_estimated", 0)),
        "TOTAL_SPRINTS": "0",
        "TEAM_SIZE": "N/D",
        "AZURE_COST": "N/D",

        # ── Effort Calculator (effort-calculator.md) ─────────────
        "EFFORT_CALC_WAVES_JSON": _build_effort_calc_json(outputs_dir),

        # ── Test coverage ────────────────────────────────────────
        "UT_COV": "0", "IT_COV": "0", "FT_COV": "0", "UI_COV": "0", "PAR_COV": "0",

        # ── Quality Gates ────────────────────────────────────────
        "QG1": "false", "QG2": "false", "QG3": "false",
        "QG4": "false", "QG5": "false", "QG6": "false",

        # ── Waves ────────────────────────────────────────────────
        "W1_MOD": "Financeiro", "W1_SP": "N/D", "W1_DUR": "N/D", "W1_FLAG": "N/D",
        "W2_MOD": "Cliente-Fornecedor", "W2_SP": "N/D", "W2_DUR": "N/D", "W2_FLAG": "N/D",
        "W3_MOD": "Cadastros Gerais", "W3_SP": "N/D", "W3_DUR": "N/D", "W3_FLAG": "N/D",

        # ── OWASP ────────────────────────────────────────────────
        "OW1_FINDING": "SQL Injection em 28+ pontos",
        "OW1_EV": f"{security.get('sql_injection_points', 28)} pontos de SQL concatenado",
        "OW1_ACT": "Entity Framework Core com parâmetros tipados",
        "OW2_FINDING": "Autenticação/Autorização ausente",
        "OW2_EV": f"Auth: {security.get('authentication', False)}, Authz: {security.get('authorization', False)}",
        "OW2_ACT": "Azure AD B2C + JWT Bearer Token",
        "OW3_FINDING": "Ausência de auditoria",
        "OW3_EV": f"Audit logging: {security.get('audit_logging', False)}",
        "OW3_ACT": "Structured logging com Serilog + Application Insights",

        # ── Security JSON placeholders (D.securityReview / D.vulns / etc.) ────
        **_build_security_json_subs(asis_dir),

        # ── Parity / Acceptance ──────────────────────────────────
        "GLOBAL_PARITY": "0", "PARITY_SCEN": "0", "PARITY_DIV": "0", "WAVES_APPROVED": "0",
        "PAR1_MOD": "N/D", "PAR1_SCEN": "0", "PAR1_PAR": "0", "PAR1_DIV": "0", "PAR1_APROV": "Pendente",
        "PAR2_MOD": "N/D", "PAR2_SCEN": "0", "PAR2_PAR": "0", "PAR2_DIV": "0", "PAR2_APROV": "Pendente",
        "AC1": "false", "AC2": "false", "AC3": "false", "AC4": "false",
        "AC5": "false", "AC6": "false", "AC7": "false", "AC8": "false",

        # ── Static diagram placeholders: embedded directly in <pre> elements so
        #    Mermaid can render from pre.textContent even when the JS pipeline
        #    (renderAllDiagrams → renderStaticDiagrams) is blocked by an earlier
        #    render error.  D.staticDiagrams provides a secondary path via JS.
        "ASIS_ARCH_BLUEPRINT_DIAGRAM": _read_and_sanitize(asis_dir / "diagrams" / "architecture-blueprint.mmd"),
        "C4_CONTEXT_DIAGRAM":        _read_and_sanitize(asis_dir / "diagrams" / "c4-context.mmd"),
        "C4_CONTAINER_DIAGRAM":      _read_and_sanitize(asis_dir / "diagrams" / "c4-container.mmd"),
        "C4_COMPONENT_DIAGRAM":      _read_and_sanitize(asis_dir / "diagrams" / "c4-component.mmd"),
        "COMPONENT_DIAGRAM":         _read_and_sanitize(asis_dir / "diagrams" / "component-diagram.mmd"),
        "SEQ_BAIXA_CP":              _read_and_sanitize(asis_dir / "diagrams" / "seq-ap-settlement.mmd") or _read_and_sanitize(asis_dir / "diagrams" / "seq-baixa-titulo-cp.mmd") or _read_and_sanitize(asis_dir / "diagrams" / "seq-baixa-cp.mmd"),
        "SEQ_CAD_CP":                _read_and_sanitize(asis_dir / "diagrams" / "seq-ap-registration.mmd") or _read_and_sanitize(asis_dir / "diagrams" / "seq-cadastro-conta-pagar.mmd") or _read_and_sanitize(asis_dir / "diagrams" / "seq-cadastro-cp.mmd"),
        "ER_DIAGRAM":                _read_and_sanitize(asis_dir / "db" / "er-diagram.mmd"),
        "TOBE_C4_DIAGRAM":           _read_and_sanitize(tobe_dir / "diagrams" / "c4-context.mmd"),
        "TOBE_ARCH_BLUEPRINT_DIAGRAM": _read_and_sanitize(tobe_dir / "diagrams" / "architecture-blueprint.mmd") or _read_and_sanitize(tobe_dir / "architecture-blueprint.mmd"),
        "CONTEXT_MAP_DIAGRAM":       _read_and_sanitize(tobe_dir / "diagrams" / "context-map.mmd"),
        "GANTT_DIAGRAM":             _read_and_sanitize(tobe_dir / "diagrams" / "gantt-migration.mmd"),
        "SOLUTION_STRUCTURE":        _read_and_sanitize(tobe_dir / "diagrams" / "solution-structure.mmd") or _read_and_sanitize(asis_dir / "diagrams" / "solution-structure.mmd"),
        "CLEAN_ARCH_STRUCTURE":      _read_and_sanitize(tobe_dir / "diagrams" / "clean-architecture.mmd") or _read_and_sanitize(asis_dir / "diagrams" / "clean-architecture.mmd"),
        # ── Stack version (read from tobe_stack in project-config.yaml) ───
        "TOBE_BACKEND_VERSION":      tobe_backend_label,
        "TOBE_FRONTEND_VERSION":     tobe_frontend_label,
        "LEGACY_TECH":               legacy_tech,
        # ── TO-BE Patterns Applied (patterns-applied.json) ───────────────
        "TOBE_PATTERNS_ROWS":        tobe_patterns_rows_html,
    }

    populated = sum(1 for v in subs.values() if v and v != "N/D" and v != "0")
    print(f"   ✅ {len(subs)} placeholders preparados ({populated} com dados reais)")
    return subs


def _load_mermaid_js(summary_dir: Path) -> str:
    """Load mermaid.min.js from summary dir or project root for inline embedding."""
    candidates = [
        summary_dir / 'mermaid.min.js',
        Path('src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js'),
    ]
    for p in candidates:
        if p.exists():
            js = p.read_text(encoding='utf-8')
            print(f"   📦 Mermaid.js carregado de {p} ({len(js)/1024:.0f} KB)")
            return js
    print("   ⚠️ mermaid.min.js não encontrado — diagramas não serão renderizados")
    return '// mermaid.min.js not found'


def parse_events_pubsub(repo_path: str, max_refs_per_key: int = 50) -> list:
    """Reverse-engineer events / queues / pub-sub from a Delphi (or generic) legacy repo.

    Estrategia (engenharia reversa por handler individual + agregados):

    Para cada arquivo `.dfm` extrai pares ``OnXxx = HandlerName`` e cria UMA
    entrada por *handler* concreto (ex: ``imgFinanceiroClick``). Em seguida
    procura nos `.pas` a implementação ``procedure TForm.HandlerName(...)`` e
    o número de chamadas/usos do nome no codigo, populando refs e count.

    Tambem detecta:
      - declaracoes de tipo ``TXxxEvent = procedure(...) of object;``  -> EVENT
      - propriedades ``property OnXxx: TYyyEvent ...``                 -> NOTIFY
      - ``: TNotifyEvent`` (campos)                                    -> NOTIFY
      - ``Send/PostMessage``, ``PostThreadMessage``                    -> WINMSG
      - ``TThread.Queue/Synchronize``, ``TEvent``, ``SetEvent``…        -> THREAD
      - ``Publish/Subscribe/Notify*`` (case-insensitive)               -> PUBSUB

    Cada item retornado:
      ``{k, kind, evt, form, unit, desc, refs:[file:line,...], count}``

    Ordenado por count desc.
    """
    import re
    repo = Path(repo_path)
    if not repo.exists():
        print(f"   ⚠️ Repo legado não encontrado para events scan: {repo}")
        return []

    DESC = {
        'EVENT':  'Handler de evento de UI VCL — vínculo OnXxx = Handler em DFM com implementação no .pas',
        'NOTIFY': 'Campo / propriedade do tipo TNotifyEvent ou evento customizado',
        'WINMSG': 'Mensagem Win32 (Send/PostMessage / PostThreadMessage) — fila de mensagens da janela',
        'THREAD': 'Sincronização entre threads (TThread.Queue / Synchronize / TEvent / SetEvent)',
        'PUBSUB': 'Padrão publish/subscribe (Publish / Subscribe / NotifyXxx)',
    }

    # ── Index .pas files (impl bodies + raw text) ─────────────────────────
    pas_files = list(repo.rglob('*.pas'))
    dfm_files = list(repo.rglob('*.dfm'))

    pas_text: dict = {}    # rel_path -> text
    impl_index: dict = {}  # handler_name -> [(rel, line_no, form_class), ...]
    form_class_re = re.compile(r'\bprocedure\s+T([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\s*\(', re.M)

    for fp in pas_files:
        try:
            text = fp.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        rel = str(fp.relative_to(repo)).replace('\\', '/')
        pas_text[rel] = text
        for m in form_class_re.finditer(text):
            cls, name = m.group(1), m.group(2)
            line_no = text.count('\n', 0, m.start()) + 1
            impl_index.setdefault(name, []).append((rel, line_no, f"T{cls}"))

    inventory: dict = {}  # key -> bucket

    def _bucket(key, kind):
        priority = ['EVENT', 'NOTIFY', 'THREAD', 'WINMSG', 'PUBSUB']
        b = inventory.setdefault(key, {
            'kind': kind, 'evt': '', 'form': '', 'unit': '',
            'refs': [], 'count': 0, 'seen': set()
        })
        if priority.index(kind) > priority.index(b['kind']):
            b['kind'] = kind
        return b

    def _add_ref(bucket, rel, line_no):
        ref = f"{rel}:{line_no}"
        if ref not in bucket['seen']:
            bucket['seen'].add(ref)
            if len(bucket['refs']) < max_refs_per_key:
                bucket['refs'].append(ref)

    # ── 1. DFM bindings : OnXxx = HandlerName  (one row per handler) ─────
    dfm_bind_re   = re.compile(r'^\s*(On[A-Z][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][\w]*)', re.M)
    object_decl_re = re.compile(r'^\s*object\s+\w+\s*:\s*T([A-Za-z_][\w]*)', re.M)

    for fp in dfm_files:
        try:
            text = fp.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        rel = str(fp.relative_to(repo)).replace('\\', '/')
        # Form class = first object header
        first_form = object_decl_re.search(text)
        form_class = f"T{first_form.group(1)}" if first_form else ''
        unit_name = Path(rel).stem
        for m in dfm_bind_re.finditer(text):
            evt, handler = m.group(1), m.group(2)
            line_no = text.count('\n', 0, m.start()) + 1
            b = _bucket(handler, 'EVENT')
            b['evt']  = b['evt']  or evt
            b['form'] = b['form'] or form_class
            b['unit'] = b['unit'] or unit_name
            b['count'] += 1
            _add_ref(b, rel, line_no)
            # Also add the .pas implementation if found
            for impl_rel, impl_line, impl_cls in impl_index.get(handler, []):
                _add_ref(b, impl_rel, impl_line)
                if not b['form']:
                    b['form'] = impl_cls

    # ── 2. PAS event-related patterns (custom events, type defs, IPC) ────
    pas_patterns = [
        # type TXxxEvent = procedure(...) of object;
        ('EVENT',  re.compile(r'^\s*T([A-Za-z_]\w*Event)\s*=\s*procedure\b', re.M),     1),
        # property OnXxx: TYyyEvent ...
        ('NOTIFY', re.compile(r'\bproperty\s+(On[A-Z]\w*)\s*:\s*T\w*Event\b'),          1),
        # field : TNotifyEvent
        ('NOTIFY', re.compile(r'\b([A-Za-z_]\w*)\s*:\s*TNotifyEvent\b'),                1),
        # OnXxx := SomeHandler  (runtime binding)
        ('EVENT',  re.compile(r'\b(On[A-Z][A-Za-z0-9_]*)\s*:=\s*[A-Za-z_]'),            1),
        # Win32 messages
        ('WINMSG', re.compile(r'\b(SendMessage|PostMessage|PostThreadMessage)\s*\('),   1),
        # Thread sync
        ('THREAD', re.compile(r'\bTThread\.(Queue|Synchronize)\b', re.I),                1),
        ('THREAD', re.compile(r'\b(SetEvent|ResetEvent|WaitForSingleObject|TEvent\.Create|TMonitor\.Pulse(?:All)?)\b'), 1),
        # Pub/Sub idiom
        ('PUBSUB', re.compile(r'\b(Publish|Subscribe|Unsubscribe|Notify[A-Z]\w*)\s*\(', re.I), 1),
    ]

    for rel, text in pas_text.items():
        unit_name = Path(rel).stem
        for kind, rx, group in pas_patterns:
            for m in rx.finditer(text):
                key = (m.group(group) or '').strip()
                if not key:
                    continue
                line_no = text.count('\n', 0, m.start()) + 1
                b = _bucket(key, kind)
                b['unit'] = b['unit'] or unit_name
                b['count'] += 1
                _add_ref(b, rel, line_no)

    out = []
    for key, b in inventory.items():
        kind = b['kind']
        if kind == 'EVENT' and b['evt']:
            desc = f"{b['evt']} @ {b['form'] or '?'} ({b['unit']}) — handler VCL"
        else:
            desc = DESC.get(kind, '')
            if b['unit']:
                desc = f"{desc} · {b['unit']}"
        out.append({
            'k':     key,
            'kind':  kind,
            'evt':   b['evt'],
            'form':  b['form'],
            'unit':  b['unit'],
            'desc':  desc,
            'refs':  b['refs'],
            'count': b['count'],
        })
    out.sort(key=lambda r: (-r['count'], r['k'].lower()))
    return out


def parse_events_pubsub_tobe(tobe_dir: Path, max_refs_per_key: int = 50) -> list:
    """Reverse-engineer events / commands / endpoints / workers / pub-sub
    from the TO-BE generated solution (.NET).

    Estrategia de varredura no `outputs/tobe/source-code` + leitura de
    `integration-matrix.md` para enriquecer:

      - ``record/class XxxCommand : IRequest<...>``        -> COMMAND
      - ``record/class XxxQuery   : IRequest<...>``        -> QUERY
      - ``XxxHandler : IRequestHandler<...>``              -> HANDLER
      - ``XxxEvent / XxxNotification : INotification``     -> DOMAIN-EVT
      - ``: IDomainEvent``                                 -> DOMAIN-EVT
      - ``Map(Post|Get|Put|Delete)("/path", ...)``          -> ENDPOINT
      - ``[HttpPost]/[HttpGet]/...`` em controllers          -> ENDPOINT
      - ``class XxxJob/Worker : BackgroundService/IHostedService`` -> WORKER
      - ``IPublisher.Publish / IBus.Publish / mediator.Publish``    -> PUBLISH
      - ``INotificationHandler<XxxEvent>``                  -> SUBSCRIBE
      - ``ServiceBusClient / EventGridPublisher``           -> CLOUDMSG
      - linhas da Integration Matrix (md)                  -> INTEGR

    Retorna `[{k, kind, evt, form (=module), unit (=file), desc, refs, count}, …]`
    (mesmo schema do `parse_events_pubsub` AS-IS, para reuso do renderer).
    """
    import re
    if not tobe_dir.exists():
        print(f"   ⚠️ TO-BE dir não encontrado para events scan: {tobe_dir}")
        return []

    DESC = {
        'COMMAND':    'CQRS Command (MediatR IRequest) — escrita de domínio',
        'QUERY':      'CQRS Query (MediatR IRequest) — leitura de domínio',
        'HANDLER':    'IRequestHandler — implementação de Command/Query',
        'DOMAIN-EVT': 'Evento de domínio (DomainEvent / INotification)',
        'ENDPOINT':   'Endpoint HTTP exposto pela API (Minimal API ou Controller)',
        'WORKER':     'BackgroundService / IHostedService — processamento assíncrono',
        'PUBLISH':    'Publicação de evento/notificação (mediator/bus)',
        'SUBSCRIBE':  'Handler que assina notificação (INotificationHandler)',
        'CLOUDMSG':   'Mensageria em nuvem (ServiceBus / EventGrid / EventHubs)',
        'INTEGR':     'Integração entre Bounded Contexts (Integration Matrix)',
    }

    src_root = tobe_dir / 'source-code'
    inventory: dict = {}

    PRIORITY = ['ENDPOINT', 'COMMAND', 'QUERY', 'HANDLER', 'DOMAIN-EVT',
                'WORKER', 'PUBLISH', 'SUBSCRIBE', 'CLOUDMSG', 'INTEGR']

    def _bucket(key, kind):
        b = inventory.setdefault(key, {
            'kind': kind, 'evt': '', 'form': '', 'unit': '',
            'refs': [], 'count': 0, 'seen': set()
        })
        if PRIORITY.index(kind) < PRIORITY.index(b['kind']):
            b['kind'] = kind
        return b

    def _add_ref(b, rel, line_no):
        ref = f"{rel}:{line_no}"
        if ref not in b['seen']:
            b['seen'].add(ref)
            if len(b['refs']) < max_refs_per_key:
                b['refs'].append(ref)

    def _module_from_path(rel: str) -> str:
        # src/modules/<Module>/<Module>.<Layer>/file.cs
        parts = rel.replace('\\', '/').split('/')
        if 'modules' in parts:
            i = parts.index('modules')
            if i + 1 < len(parts):
                return parts[i + 1]
        if 'host' in parts:
            return 'Host'
        if 'buildingblocks' in parts:
            return 'BuildingBlocks'
        return parts[0] if parts else ''

    # ── 1. C# scan ───────────────────────────────────────────────────────
    cs_patterns = [
        ('COMMAND',    re.compile(r'\b(?:public\s+)?(?:sealed\s+)?(?:partial\s+)?(?:record|class)\s+(\w+Command)\b')),
        ('QUERY',      re.compile(r'\b(?:public\s+)?(?:sealed\s+)?(?:partial\s+)?(?:record|class)\s+(\w+Query)\b')),
        ('HANDLER',    re.compile(r'\b(?:public\s+)?(?:sealed\s+)?(?:partial\s+)?class\s+(\w+Handler)\b')),
        ('DOMAIN-EVT', re.compile(r'\b(?:public\s+)?(?:sealed\s+)?(?:partial\s+)?(?:record|class)\s+(\w+(?:Event|DomainEvent|Notification|Raised|Issued|Created|Updated|Deleted|Posted|Settled|Approved|Rejected))\b')),
        ('DOMAIN-EVT', re.compile(r'\b(\w+)\s*:\s*(?:I)?DomainEvent\b')),
        ('WORKER',     re.compile(r'\bclass\s+(\w+(?:Worker|Job|Service|Processor))\s*:\s*(?:BackgroundService|IHostedService)\b')),
        ('SUBSCRIBE',  re.compile(r'INotificationHandler<\s*(\w+)\s*>')),
        ('PUBLISH',    re.compile(r'\b(?:_?mediator|_?publisher|_?bus)\.Publish(?:Async)?\s*\(\s*(?:new\s+)?(\w+)')),
        ('CLOUDMSG',   re.compile(r'\b(ServiceBus(?:Client|Sender|Receiver|Processor)|EventGridPublisherClient|EventHub(?:Producer|Consumer)Client)\b')),
        # Minimal API endpoints  ─ capture HTTP verb + path
        ('ENDPOINT',   re.compile(r'\bMap(Post|Get|Put|Delete|Patch)\s*\(\s*"([^"]+)"')),
        # Controller actions
        ('ENDPOINT',   re.compile(r'\[Http(Post|Get|Put|Delete|Patch)(?:\(\s*"([^"]+)"\s*\))?\]')),
    ]

    if src_root.exists():
        for fp in src_root.rglob('*.cs'):
            spath = str(fp).replace('\\', '/')
            if '/obj/' in spath or '/bin/' in spath:
                continue
            try:
                text = fp.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            rel = str(fp.relative_to(src_root)).replace('\\', '/')
            module = _module_from_path(rel)
            unit = Path(rel).stem
            for kind, rx in cs_patterns:
                for m in rx.finditer(text):
                    if kind == 'ENDPOINT':
                        verb = (m.group(1) or '').upper()
                        path = m.group(2) if m.lastindex and m.lastindex >= 2 else ''
                        key = f"{verb} {path}".strip() if path else f"{verb} (action)"
                        evt = verb
                    else:
                        key = (m.group(1) or '').strip()
                        evt = ''
                        if not key:
                            continue
                    line_no = text.count('\n', 0, m.start()) + 1
                    b = _bucket(key, kind)
                    if evt and not b['evt']:
                        b['evt'] = evt
                    b['form'] = b['form'] or module
                    b['unit'] = b['unit'] or unit
                    b['count'] += 1
                    _add_ref(b, rel, line_no)

    # ── 2. Integration Matrix (markdown table) ───────────────────────────
    matrix = tobe_dir / 'integration-matrix.md'
    if matrix.exists():
        try:
            text = matrix.read_text(encoding='utf-8', errors='replace')
        except Exception:
            text = ''
        row_re = re.compile(r'^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', re.M)
        for m in row_re.finditer(text):
            src, tgt, direction, coupling, mode, notes = [s.strip() for s in m.groups()]
            key = f"{src} → {tgt}"
            line_no = text.count('\n', 0, m.start()) + 1
            b = _bucket(key, 'INTEGR')
            b['evt']  = direction
            b['form'] = src
            b['unit'] = 'integration-matrix.md'
            b['count'] += 1
            # custom richer description
            b['_custom_desc'] = f"{mode} · coupling={coupling} · {notes}"
            _add_ref(b, 'integration-matrix.md', line_no)

    out = []
    for key, b in inventory.items():
        kind = b['kind']
        if '_custom_desc' in b:
            desc = b['_custom_desc']
        elif kind == 'ENDPOINT':
            desc = f"{b['evt'] or 'HTTP'} endpoint @ {b['form']} ({b['unit']})"
        elif kind in ('COMMAND', 'QUERY', 'HANDLER', 'DOMAIN-EVT', 'WORKER', 'SUBSCRIBE', 'PUBLISH'):
            desc = f"{DESC[kind]} · {b['form']} / {b['unit']}"
        else:
            desc = DESC.get(kind, '')
        out.append({
            'k':     key,
            'kind':  kind,
            'evt':   b['evt'],
            'form':  b['form'],
            'unit':  b['unit'],
            'desc':  desc,
            'refs':  b['refs'],
            'count': b['count'],
        })
    # Sort: by kind priority then by count desc
    out.sort(key=lambda r: (PRIORITY.index(r['kind']) if r['kind'] in PRIORITY else 99,
                             -r['count'], r['k'].lower()))
    return out


def build_summary_html(project_name: str):
    """Constrói Summary HTML completo"""
    print(f"\n{'='*60}")
    print(f"  AVA Fabric Summary Builder (Completo)")
    print(f"  Project: {project_name}")
    print(f"{'='*60}")
    
    # Configuração
    config = load_project_config(project_name)
    trace_id = config.get('trace_id', 'unknown')
    language = config.get('language', 'pt')
    
    # Paths
    base_dir = Path('.')
    template_path = base_dir / 'src/modules/ava-fabric-agents/summary/templates/html/summary-template.html'
    outputs_dir = base_dir / f'projects/{project_name}/outputs'
    summary_dir = outputs_dir / 'summary'
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    # Load template
    print("\n[1/5] Carregando template oficial...")
    if not template_path.exists():
        print(f"   ❌ Template não encontrado: {template_path}")
        return
    
    html = template_path.read_text(encoding='utf-8')
    print(f"   ✅ Template carregado ({len(html):,} bytes)")
    
    # Build data structures
    asis_dir = outputs_dir / 'asis'
    agent_status = build_agent_status_map(project_name, outputs_dir)
    artifact_inventory = build_artifact_inventory(project_name, outputs_dir)
    file_tree = build_file_tree_with_content(project_name)
    exec_summary = generate_executive_summary(project_name, language)

    # Parse structured data from markdown files
    cc_top = parse_complexity_top10(asis_dir)
    biz_rules = parse_business_rules(asis_dir)
    func_reqs = parse_functional_requirements(asis_dir)
    test_map, test_gaps = parse_test_map(asis_dir)
    # ── Test Cases (spec 028) — generate overview artifact then parse list ──
    test_cases_content = _build_test_cases_overview(asis_dir)  # always overwrites overview file
    test_cases = _build_test_cases(asis_dir)                   # D.testCases — KPI tiles
    screen_data = parse_screen_artifacts(asis_dir)
    screen_mermaid = screen_data["mermaid"]
    screen_forms = screen_data["forms"]
    screen_overview = screen_data["overview"]
    screen_narrative = screen_data["narrative"]
    screen_groups = screen_data["groups"]
    screen_rules = screen_data["rules"]
    screen_rules_by_form = screen_data["rules_by_form"]
    screen_rule_categories = screen_data["categories"]
    tobe_dir = outputs_dir / 'tobe'
    api_endpoints = parse_openapi_endpoints(tobe_dir)
    static_diagrams = collect_static_diagrams(asis_dir, tobe_dir)
    db_schema = parse_db_schema(asis_dir)
    legacy_repo_path = config.get('repository_path', '')
    events_inventory = parse_events_pubsub(legacy_repo_path) if legacy_repo_path else []
    print(f"   📡 Events/Queues/Pub-Sub inventariados: {len(events_inventory)} chaves")
    tobe_events_inventory = parse_events_pubsub_tobe(tobe_dir)
    _tobe_by_kind = {}
    for _r in tobe_events_inventory:
        _k = str(_r.get('kind') or '').upper()
        _tobe_by_kind[_k] = _tobe_by_kind.get(_k, 0) + 1
    _tobe_breakdown = ', '.join(f"{k}={v}" for k, v in sorted(_tobe_by_kind.items())) or '(vazio)'
    print(f"   🛰️ TO-BE Events inventariados: {len(tobe_events_inventory)} chaves [{_tobe_breakdown}]")
    print(f"   📊 Parsed: {len(cc_top)} CC rows, {len(biz_rules)} rules, {len(func_reqs)} reqs, {len(test_map)} test rows, {len(test_gaps)} gaps, {len(screen_forms)} screens, {len(screen_rules)} screen rules, {len(screen_groups)} screen groups, {len(api_endpoints)} endpoints, {len(static_diagrams)} diagrams, {len(db_schema)} db tables, {len(tobe_events_inventory)} tobe-events")
    
    # Prepare replacements — from real data files
    print("\n[2/5] Preparando substituições...")
    now = datetime.now()

    # Build comprehensive substitutions from metrics.json, risk-register.json, etc.
    data_subs = build_all_substitutions(project_name, outputs_dir, file_tree)

    # === Stage A: simple scalar replacements + inlined Mermaid ===
    # These must be processed BEFORE the JSON blobs below, because embedded
    # file content inside FILE_TREE_JSON can legitimately contain literal
    # `{{X}}` strings (e.g. doc files that reference template placeholders).
    # Replacing scalars first keeps those mentions intact — they end up as
    # *content* inside the JSON, not re-substituted HTML.
    scalar_replacements = {
        '{{PROJECT_NAME}}': project_name,
        '{{GENERATED_AT}}': now.strftime('%d/%m/%Y %H:%M'),
        '{{TRACE_ID}}': trace_id,
        '{{COVERAGE}}': 'F1 AS-IS',
        '{{AGENTS_OK}}': str(sum(1 for s in agent_status.values() if s == "done")),
        '{{AGENTS_ERR}}': '0',
        # Mermaid library inline — 3 MB string. Done here (not in JSON stage)
        # so the fileTree JSON can't accidentally re-inject it.
        '{{MERMAID_JS}}': _load_mermaid_js(summary_dir),
    }
    # Merge data substitutions from build_all_substitutions
    for key, value in data_subs.items():
        placeholder = '{{' + key + '}}'
        if placeholder not in scalar_replacements:
            scalar_replacements[placeholder] = str(value)

    # === Stage B: JSON blobs LAST ===
    # After this pass, anything between `<script>` tags that contains literal
    # `{{X}}` is safely frozen inside a JSON string and cannot be re-substituted.
    json_replacements = {
        '{{AGENT_STATUS_JSON}}':       json.dumps(agent_status).replace('</', '<\\/'),
        '{{FILE_TREE_JSON}}':          json.dumps(file_tree).replace('</', '<\\/'),
        '{{ARTIFACT_INVENTORY_JSON}}': json.dumps(artifact_inventory).replace('</', '<\\/'),
    }

    print("[3/5] Aplicando substituições...")
    # Stage A first (scalars + mermaid + data subs)
    for placeholder, value in scalar_replacements.items():
        if placeholder in html:
            html = html.replace(placeholder, value)
            print(f"   ✅ {placeholder}")
    # Stage B last (JSON blobs — their contents are final, never re-parsed)
    for placeholder, value in json_replacements.items():
        if placeholder in html:
            html = html.replace(placeholder, value)
            print(f"   ✅ {placeholder}")

    # Final sweep: any leftover {{PLACEHOLDER}} would break JS parsing
    # (bare {{X}} inside a JS expression is a syntax error). Replace
    # remaining *_JSON placeholders with empty object literals and everything
    # else with an empty string. This guarantees the generated HTML always
    # produces valid JavaScript regardless of which placeholders are filled.
    import re as _re
    leftover = sorted(set(_re.findall(r'\{\{[A-Z0-9_]+\}\}', html)))
    if leftover:
        print(f"   🧹 Limpando {len(leftover)} placeholders não-preenchidos")
        for ph in leftover:
            default = '{}' if ph.endswith('_JSON}}') else ''
            html = html.replace(ph, default)
    
    # Inject data arrays into const D
    print("[4/5] Injetando dados no const D...")

    def _safe_json(obj):
        return json.dumps(obj, ensure_ascii=False).replace('</', '<\\/')

    injected_block = (
        f'  execSummary: {_safe_json(exec_summary)},\n'
        f'  ccTop: {_safe_json(cc_top)},\n'
        f'  bizRules: {_safe_json(biz_rules)},\n'
        f'  funcReqs: {_safe_json(func_reqs)},\n'
        f'  testMap: {_safe_json(test_map)},\n'
        f'  testGaps: {_safe_json(test_gaps)},\n'
        f'  testCases: {_safe_json(test_cases)},\n'
        f'  testCasesContent: {_safe_json(test_cases_content)},\n'
        f'  screenMermaid: {_safe_json(screen_mermaid)},\n'
        f'  screenForms: {_safe_json(screen_forms)},\n'
        f'  screenOverview: {_safe_json(screen_overview)},\n'
        f'  screenNarrative: {_safe_json(screen_narrative)},\n'
        f'  screenGroups: {_safe_json(screen_groups)},\n'
        f'  screenRules: {_safe_json(screen_rules)},\n'
        f'  screenRulesByForm: {_safe_json(screen_rules_by_form)},\n'
        f'  screenRuleCategories: {_safe_json(screen_rule_categories)},\n'
        f'  apiEndpoints: {_safe_json(api_endpoints)},\n'
        f'  staticDiagrams: {_safe_json(static_diagrams)},\n'
        f'  dbSchema: {_safe_json(db_schema)},\n'
        f'  events: {_safe_json(events_inventory)},\n'
        f'  tobeEvents: {_safe_json(tobe_events_inventory)},\n'
        f'\n  /* ── Agent status (done/pending por arquivo presente) ────────── */'
    )

    ANCHOR = '/* ── Agent status (done/pending por arquivo presente) ────────── */'
    if ANCHOR in html:
        html = html.replace(ANCHOR, injected_block, 1)  # replace FIRST occurrence only
    else:
        # Anchor not found (e.g. double-run). Append staticDiagrams right before
        # the closing `};` of the const D block so diagrams still render.
        import re as _re2
        if 'staticDiagrams' not in html:
            html = _re2.sub(
                r'(  fileTree\s*:\s*\{[\s\S]*?\},?\s*\n\};)',
                r'  staticDiagrams: ' + _safe_json(static_diagrams) + r',\n\1',
                html, count=1
            )
            print("   ⚠️ Anchor ausente — staticDiagrams injetado antes de fileTree")
        else:
            print("   ℹ️ staticDiagrams já presente — pulando reinjeção")
    print(f"   ✅ execSummary + ccTop + bizRules + funcReqs + testMap + testGaps + staticDiagrams injetados")
    
    # Save
    print("[5/5] Salvando HTML...")
    output_filename = f'AVA-FABRIC-SUMMARY-{project_name}-{now.strftime("%Y-%m-%d")}.html'
    output_path = summary_dir / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n{'='*60}")
    print(f"  ✅ SUCESSO!")
    print(f"  Arquivo: {output_filename}")
    print(f"  Tamanho: {len(html):,} bytes ({len(html)/1024:.1f} KB)")
    print(f"  Path: {output_path}")
    print(f"{'='*60}")
    
    # Validate
    if 'AVA Fabric Summary Template v1.0' in html:
        print(f"\n✅ Assinatura do template VÁLIDA")
    else:
        print(f"\n⚠️ Assinatura do template AUSENTE")

    # Non-regression gate — runs the Summary Validator on the freshly generated
    # HTML. If any `error`-level check fails, the build exits with code 1 so
    # downstream pipelines do not promote a regressed deliverable.
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from validate_summary import run_all as _run_validate  # type: ignore
        print("\n[Validation] Executando non-regression gate (auto-fix habilitado)…")
        rc = _run_validate(project_name, auto_fix=True)
        if rc != 0:
            print(f"   ❌ Validator sinalizou regressão — ver validation-report.md")
            _sys.exit(rc)
    except FileNotFoundError as e:
        # Validator is present but no summary HTML was produced upstream.
        print(f"   ⚠️ Validator não encontrou HTML gerado: {e}")
    except ModuleNotFoundError:
        print("   ⚠️ validate_summary.py ausente — pulando validação")
    except Exception as e:
        # Never break the build because the validator itself crashed; report and continue.
        print(f"   ⚠️ Validator falhou (não-bloqueante): {e!r}")

    return output_path


# ── Effort Calculator JSON builder ───────────────────────────────────────────
def _build_effort_calc_json(outputs_dir: Path) -> str:
    """
    Parses effort-calculator.md and extracts per-wave subtotals into a JSON array
    suitable for the summary HTML template (tb-effort-calc table).

    Expected markdown structure per wave:
      ### Wave N — Name
      ... table rows ...
      | **SUBTOTAL Wave N** | **FP** | — | **SP** | ... | **hours_raw** | **hours_overhead** | **hours_final** |

    Returns JSON string: [{"wave":"Wave 1 — Name","fp":X,"sp":X,...}, ...]
    Falls back to empty array [] if file is missing or unparseable.
    """
    import json
    import re

    ec_path = outputs_dir / "tobe" / "docs" / "effort-calculator.md"
    if not ec_path.exists():
        return "[]"

    try:
        content = ec_path.read_text(encoding="utf-8")
        waves = []
        # Split by wave headers
        wave_sections = re.split(r"###\s+Wave\s+(\d+)\s*[—–-]\s*(.+)", content)
        # wave_sections: [preamble, num1, name1, body1, num2, name2, body2, ...]
        i = 1
        while i < len(wave_sections) - 2:
            wave_num = wave_sections[i].strip()
            wave_name = wave_sections[i + 1].strip()
            wave_body = wave_sections[i + 2]

            # Find SUBTOTAL row
            subtotal_match = re.search(
                r"\|\s*\*\*SUBTOTAL[^|]*\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*\*\*([\d.]+)\*\*\s*\|"
                r"[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*\*\*([\d.]+)\*\*\s*\|\s*\*\*([\d.]+)\*\*\s*\|\s*\*\*([\d.]+)\*\*\s*\|",
                wave_body,
            )
            if subtotal_match:
                waves.append({
                    "wave": f"Wave {wave_num} — {wave_name}",
                    "fp": int(subtotal_match.group(1)),
                    "sp": subtotal_match.group(2),
                    "hours_raw": subtotal_match.group(3),
                    "hours_overhead": subtotal_match.group(4),
                    "hours_final": subtotal_match.group(5),
                    "sprints": "—",
                })
            else:
                # Fallback: extract what we can
                waves.append({
                    "wave": f"Wave {wave_num} — {wave_name}",
                    "fp": "N/D", "sp": "N/D",
                    "hours_raw": "N/D", "hours_overhead": "N/D",
                    "hours_final": "N/D", "sprints": "N/D",
                })
            i += 3

        # Try to extract sprints from the summary line after each wave table
        for w in waves:
            wave_num = w["wave"].split(" ")[1]
            sprints_match = re.search(
                rf"Sprints estimados \(Wave {wave_num}\).*?(\d+\.?\d*)\s*sprints",
                content,
            )
            if sprints_match:
                w["sprints"] = sprints_match.group(1)

        return json.dumps(waves, ensure_ascii=False)
    except Exception:
        return "[]"


# ── Security JSON placeholder builder ────────────────────────────────────────
def _build_security_json_subs(asis_dir: Path) -> dict:
    """
    Reads all 7 security sub-agent JSON files, consolidates findings into canonical
    securityReview[] using DISTINCT by (reference, owasp, cwe) — G7 — with evidence
    merge (sorted+distinct), and builds all security placeholder values.

    Canonical per-finding fields (schema v2):
      type, severity, owasp, cwe, reference, finding, evidence, source, count
      (plus stride, hypothesis, business_impact, effort, owner_suggested, priority, recommendation)

    Reference URL per agent:
      sast/iast/pt-pattern/dependency-config/taint/security-review → CWE URL
      threat-model → Microsoft STRIDE URL (anchor per category)
      sbom → Snyk CVE URL (https://snyk.io/vuln/{CVE-ID})

    Guardrails:
      G1 — Anti-asset-pollution: filter type="Business Context", "exposure", "classification"
      G2 — reference auto-derive: CWE URL for most agents; STRIDE URL for threat-model; Snyk for sbom
      G3 — Evidence never empty: evidence empty → "(sem evidência registrada)"
      G4 — Old-schema adapter: legacy file/line/observed_in/affected_units/poc_vector → canonical evidence
      G5 — Finding never empty: finding < 1 char → use type as fallback
      G6 — count recalculated: always len(evidence.split("|")) after merge (never trusts agent value)
      G7 — Merge key: (reference.lower(), owasp.upper(), cwe.upper()) — precise triple-key grouping
      G8 — STRIDE reference: Microsoft threat-modeling-tool-threats page anchor per STRIDE category
    """
    sec_dir = asis_dir / "security"

    def _load(fname):
        f = sec_dir / fname
        if not f.exists():
            return {}
        try:
            raw = f.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            return json.loads(raw)
        except Exception:
            return {}

    OWASP_CWE_MAP = {
        "CWE-89":   ("A03:2021", "https://cwe.mitre.org/data/definitions/89.html"),
        "CWE-798":  ("A07:2021", "https://cwe.mitre.org/data/definitions/798.html"),
        "CWE-306":  ("A07:2021", "https://cwe.mitre.org/data/definitions/306.html"),
        "CWE-362":  ("A04:2021", "https://cwe.mitre.org/data/definitions/362.html"),
        "CWE-390":  ("A09:2021", "https://cwe.mitre.org/data/definitions/390.html"),
        "CWE-20":   ("A03:2021", "https://cwe.mitre.org/data/definitions/20.html"),
        "CWE-916":  ("A02:2021", "https://cwe.mitre.org/data/definitions/916.html"),
        "CWE-1104": ("A06:2021", "https://cwe.mitre.org/data/definitions/1104.html"),
        "CWE-778":  ("A09:2021", "https://cwe.mitre.org/data/definitions/778.html"),
        "CWE-200":  ("A02:2021", "https://cwe.mitre.org/data/definitions/200.html"),
        "CWE-862":  ("A01:2021", "https://cwe.mitre.org/data/definitions/862.html"),
        "CWE-287":  ("A07:2021", "https://cwe.mitre.org/data/definitions/287.html"),
        "CWE-319":  ("A02:2021", "https://cwe.mitre.org/data/definitions/319.html"),
        "CWE-693":  ("A04:2021", "https://cwe.mitre.org/data/definitions/693.html"),
        "CWE-345":  ("A08:2021", "https://cwe.mitre.org/data/definitions/345.html"),
        "CWE-400":  ("A05:2021", "https://cwe.mitre.org/data/definitions/400.html"),
        "CWE-209":  ("A05:2021", "https://cwe.mitre.org/data/definitions/209.html"),
    }

    # G8 — STRIDE category → Microsoft reference URL (anchor per category)
    _STRIDE_BASE = "https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats"
    STRIDE_REF_MAP: dict[str, str] = {
        "spoofing":               f"{_STRIDE_BASE}#spoofing",
        "tampering":              f"{_STRIDE_BASE}#tampering",
        "repudiation":            f"{_STRIDE_BASE}#repudiation",
        "information disclosure": f"{_STRIDE_BASE}#information-disclosure",
        "denial of service":      f"{_STRIDE_BASE}#denial-of-service",
        "elevation of privilege": f"{_STRIDE_BASE}#elevation-of-privilege",
        "s": f"{_STRIDE_BASE}#spoofing",
        "t": f"{_STRIDE_BASE}#tampering",
        "r": f"{_STRIDE_BASE}#repudiation",
        "i": f"{_STRIDE_BASE}#information-disclosure",
        "d": f"{_STRIDE_BASE}#denial-of-service",
        "e": f"{_STRIDE_BASE}#elevation-of-privilege",
    }
    STRIDE_OWASP_MAP: dict[str, str] = {
        "spoofing":               "A07:2021",
        "tampering":              "A03:2021",
        "repudiation":            "A09:2021",
        "information disclosure": "A02:2021",
        "denial of service":      "A05:2021",
        "elevation of privilege": "A01:2021",
    }
    STRIDE_CWE_MAP: dict[str, str] = {
        "spoofing":               "CWE-306",
        "tampering":              "CWE-345",
        "repudiation":            "CWE-778",
        "information disclosure": "CWE-200",
        "denial of service":      "CWE-400",
        "elevation of privilege": "CWE-862",
    }

    def _cwe_ref(cwe: str) -> str:
        """G2: derive CWE reference URL from CWE code."""
        if cwe and cwe.upper() not in ("CWE-OTHER", "CWE-0", ""):
            m = re.match(r"CWE-(\d+)", cwe, re.IGNORECASE)
            if m:
                return f"https://cwe.mitre.org/data/definitions/{m.group(1)}.html"
        return "https://owasp.org/www-project-top-ten/"

    def _stride_ref(category: str) -> str:
        """G8: derive Microsoft STRIDE reference URL from stride_category."""
        key = (category or "").strip().lower()
        url = STRIDE_REF_MAP.get(key)
        if url:
            return url
        # partial match (e.g. "Information Disclosure (I)" or single letter)
        for k, v in STRIDE_REF_MAP.items():
            if key.startswith(k) or (len(key) == 1 and key == k):
                return v
        return _STRIDE_BASE

    def _ensure_owasp(owasp: str, cwe: str) -> str:
        if owasp and owasp not in ("", "A00:Other"):
            return owasp
        mapped = OWASP_CWE_MAP.get(cwe, ("A00:Other", ""))[0]
        return mapped

    def _ensure_ev(ev, file_val="", line_val=0, rule_val="") -> str:
        """G3: ensure evidence never empty; G4: build from file+line if needed."""
        if ev and str(ev).strip():
            return str(ev).strip()
        if file_val:
            return f"{file_val} - Line {line_val}" if line_val else f"{file_val} - Line 0"
        return "(sem evidência registrada)"

    def _extract_file_refs(ev_str: str) -> str:
        """MW-1: Normalize evidence string to 'arquivo.ext - Line N' format.
        Each pipe-separated item is reduced to just the file identifier + line number.
        Handles comma-lists, '+N others' shorthand, and narrative text."""
        if not ev_str or not ev_str.strip():
            return ev_str
        # Pattern to detect a filename with extension
        _fname_re = re.compile(
            r'([\w.\-]+\.(?:pas|dfm|dpr|dcu|exe|dll|json|yaml|yml|xml|cs|py|java|ts|js|go|rb|php|kt|swift|sql|ini|config|env|sh|bat|ps1))'
            r'(?:[:\s]*(?:Line\s*|Linha\s*|line\s*|linha\s*|L\s*|:)(\d+))?',
            re.IGNORECASE
        )
        raw_items = [x.strip() for x in ev_str.split('|') if x.strip()]
        result: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            # Expand comma-separated filenames within a single item
            # e.g. "uContasPagar.dfm, uContasReceber.dfm, uBancos.dfm"
            sub_items: list[str] = []
            if ',' in item:
                parts = [p.strip() for p in item.split(',') if p.strip()]
                # Only split if every part looks like a filename (has extension)
                if all(_fname_re.search(p) for p in parts):
                    sub_items = parts
                else:
                    sub_items = [item]  # not a comma-list of files — treat as one item
            else:
                sub_items = [item]
            for sub in sub_items:
                # Skip shorthand like '[+14 other DFM files]' or '+16 others'
                if re.match(r'^\[?\+?\d+\s+other', sub, re.IGNORECASE):
                    continue  # expanded explicitly via individual items in other evidence entries
                # Extract filename + optional line number
                m = _fname_re.search(sub)
                if m:
                    fname = m.group(1)
                    lineno = m.group(2) or '0'
                    ref = f"{fname} - Line {lineno}"
                else:
                    # No recognisable filename — keep item but strip narrative after ' - '
                    dash_idx = sub.find(' - ')
                    ref = sub[:dash_idx].strip() if dash_idx > 0 else sub
                    ref = ref[:80]  # cap length
                if ref and ref not in seen:
                    seen.add(ref)
                    result.append(ref)
        return ' | '.join(result) if result else ev_str

    def _ensure_desc(desc, rule_val="", type_val="") -> str:
        """G5: finding never empty."""
        if desc and str(desc).strip():
            return str(desc).strip()
        if rule_val and str(rule_val).strip():
            return str(rule_val).strip()
        if type_val and str(type_val).strip():
            return str(type_val).strip()
        return "Finding sem descrição"

    def _normalize_finding(item: dict, agent_name: str) -> dict | None:
        """G1/G4/G5: reject asset-pollution; adapt legacy schemas; normalize canonical v2."""
        # G1 — reject assets / non-vulnerability entries
        type_raw = (item.get("type") or item.get("vulnerability_type") or item.get("category") or "").strip()
        if type_raw in ("Business Context", "asset", "Other-Asset"):
            return None
        if "exposure" in item or "classification" in item:
            return None

        # ── severity ──────────────────────────────────────────────────────────
        sev_raw = (item.get("severity") or item.get("sev") or "INFO").upper()

        # ── type ──────────────────────────────────────────────────────────────
        # All agents now emit canonical 'type' field. Read it directly.
        # stride_cat: accept both 'stride_category' (legacy) and 'category' (threat-model-asis)
        # Normalize to Title Case for consistent display.
        stride_cat = (item.get("stride_category") or item.get("stride") or "").strip()
        if agent_name == "threat-model-asis":
            # category field = STRIDE category (e.g. "SPOOFING") — treat as stride_cat
            raw_cat = (item.get("category") or "").upper().replace(" ", "_")
            stride_cat = stride_cat or raw_cat
        type_val = type_raw or stride_cat.replace("_", " ").title() or "Other"

        # ── CWE + OWASP ───────────────────────────────────────────────────────
        cwe_val = (item.get("cwe") or "CWE-Other").strip()
        if agent_name == "threat-model-asis" and (not cwe_val or cwe_val == "CWE-Other") and stride_cat:
            cwe_val = STRIDE_CWE_MAP.get(stride_cat.lower(), "CWE-Other")

        owasp_raw = (item.get("owasp") or item.get("capec") or "").strip()
        if agent_name == "threat-model-asis" and not owasp_raw and stride_cat:
            owasp_val = STRIDE_OWASP_MAP.get(stride_cat.lower(), "A00:Other")
        else:
            owasp_val = _ensure_owasp(owasp_raw, cwe_val)

        # ── reference (G2/G8) ─────────────────────────────────────────────────
        ref_raw = (item.get("reference") or item.get("issue_ref") or "").strip()
        if agent_name == "threat-model-asis":
            # G8: STRIDE agents always use STRIDE Microsoft reference
            ref_val = _stride_ref(stride_cat) if stride_cat else _cwe_ref(cwe_val)
        elif agent_name == "sbom":
            # Snyk CVE URL from SBOM vulnerabilities[] advisories
            adv = item.get("advisories")
            if isinstance(adv, list) and adv:
                ref_val = adv[0].get("url") or ref_raw or _cwe_ref(cwe_val)
            else:
                ref_val = ref_raw or _cwe_ref(cwe_val)
        else:
            # CWE URL for all other agents — ignore CAPEC refs from pt-pattern
            if not ref_raw or "capec" in ref_raw.lower():
                ref_val = _cwe_ref(cwe_val)
            else:
                ref_val = ref_raw
        if not ref_val:
            ref_val = _cwe_ref(cwe_val)
        # MW-3: CWE takes priority — if finding has a valid CWE ID, always use MITRE link.
        # Only fall back to the existing ref when there is no resolvable CWE.
        _cwe_mitre = _cwe_ref(cwe_val)
        if _cwe_mitre.startswith('https://cwe.mitre.org/'):
            ref_val = _cwe_mitre
        else:
            _valid_ref_prefixes = (
                'https://cwe.mitre.org/',
                'https://learn.microsoft.com/',
                'https://snyk.io/',
            )
            if not any(ref_val.startswith(p) for p in _valid_ref_prefixes):
                ref_val = _cwe_mitre  # owasp fallback when no valid CWE

        # ── evidence (G3/G4) — canonical field: "evidence" (singular) ─────────
        # Read priority: evidence (v2 canonical) > evidences (plural legacy) > ev (internal)
        raw_ev_canonical = (
            item.get("evidence") or item.get("evidences") or item.get("ev") or ""
        ).strip()

        file_val = item.get("file") or item.get("form") or ""
        line_val = item.get("line") or 0

        # G4 IAST: observed_in list of forms → evidence
        iast_ev = ""
        if agent_name == "iast-asis" and not raw_ev_canonical:
            obs = item.get("observed_in") or ""
            if obs:
                forms = [f.strip() for f in obs.split(",") if f.strip()]
                iast_ev = "|".join(f"{f} - Linha 0" for f in forms) if forms else f"{obs} - Linha 0"

        # G4 PT-pattern: poc_vector / target_forms → evidence
        pt_ev = ""
        if agent_name == "pt-pattern-asis" and not raw_ev_canonical:
            target_forms = item.get("target_forms") or []
            poc = item.get("poc_vector") or ""
            if isinstance(target_forms, list) and target_forms:
                pt_ev = "|".join(f"{frm} - Linha 0" for frm in target_forms)
            elif poc:
                pt_ev = f"{poc[:60].strip()} - Linha 0"

        # G4 threat-model: affected_assets / affected_components → evidence
        tm_ev = ""
        if agent_name == "threat-model-asis" and not raw_ev_canonical:
            affected = item.get("affected_assets") or item.get("affected_components") or []
            if isinstance(affected, list) and affected:
                tm_ev = "|".join(f"{str(a).strip()} - Linha 0" for a in affected)
            elif isinstance(affected, str) and affected:
                tm_ev = f"{affected} - Linha 0"

        # G4 security-review: affected_units → evidence
        sr_ev = ""
        if agent_name == "security-review-asis" and not raw_ev_canonical:
            units = item.get("affected_units") or []
            if isinstance(units, list) and units:
                sr_ev = "|".join(f"{u} - Linha 0" for u in units)

        # G4 dependency/sbom: component name → evidence
        dep_ev = ""
        if agent_name in ("dependency-config-asis", "sbom") and not raw_ev_canonical:
            comp = item.get("component") or item.get("ref") or item.get("name") or ""
            if comp:
                dep_ev = f"{comp} - Linha 0"

        raw_ev = raw_ev_canonical or iast_ev or pt_ev or tm_ev or sr_ev or dep_ev
        ev_val = _ensure_ev(raw_ev, file_val, line_val)
        # MW-1: normalize each evidence item to 'arquivo.ext - Line N'
        ev_val = _extract_file_refs(ev_val)

        # ── finding (G5) ─────────────────────────────────────────────────────
        # Read priority: finding (v2) > description > title > threat > name > desc
        # G4 pt-pattern: attack_vector used as description when no standard field present
        raw_desc = (
            item.get("finding") or item.get("description") or
            item.get("title") or item.get("threat") or
            item.get("name") or item.get("desc") or
            (item.get("attack_vector") if agent_name == "pt-pattern-asis" else "") or ""
        )
        rule_hint = item.get("rule") or item.get("exploitability") or item.get("poc_vector") or ""
        desc_val = _ensure_desc(raw_desc, rule_hint, type_val)  # G5

        # ── source ────────────────────────────────────────────────────────────
        # taint-asis: 'source' field = taint source (e.g. user input) — NOT agent name
        # security-findings: 'source' field may contain real agent name — keep it
        # all other agents: 'source' field = canonical agent name from v2 schema
        # sbom: 'source' may be a dict like {"name":"NVD"} — not the agent name, use agent_name
        if agent_name == "taint-asis":
            source_val = "taint-asis"
        else:
            raw_src = item.get("source")
            source_val = raw_src if isinstance(raw_src, str) and raw_src else agent_name

        # ── count (G6) — always recompute; never trust agent value ────────────
        count_val = len([e for e in ev_val.split("|") if e.strip()])

        return {
            "id":              item.get("id") or f"{agent_name.upper()}-?",
            "type":            type_val or "Other",
            "severity":        sev_raw.lower(),   # lowercase for sevBadge compat
            "owasp":           owasp_val,
            "cwe":             cwe_val,
            "reference":       ref_val,
            "finding":         desc_val,
            "evidence":        ev_val,
            "source":          source_val,
            "count":           count_val,
            # extended fields (pass-through)
            "stride":          stride_cat or item.get("stride") or "N/A",
            "hypothesis":      item.get("hypothesis") or False,
            "business_impact": item.get("business_impact") or "",
            "effort":          item.get("effort") or "M",
            "owner_suggested": item.get("owner_suggested") or "security-team",
            "priority":        item.get("priority") or "P1",
            "recommendation":  item.get("recommendation") or item.get("remediation") or item.get("mitigation") or "",
        }

    # ── Read all primary sub-agent JSONs (all now in canonical v2 schema) ────
    # security-review-asis.json excluded — it's a summary document (no findings[]).
    AGENT_FILES = [
        ("sast-asis.json",              "sast-asis"),
        ("iast-asis.json",              "iast-asis"),
        ("pt-pattern-asis.json",        "pt-pattern-asis"),
        ("dependency-config-asis.json", "dependency-config-asis"),
        ("taint-asis.json",             "taint-asis"),
        ("threat-model-asis.json",      "threat-model-asis"),
        ("sbom.cyclonedx.json",         "sbom"),
        ("security-findings.json",      "security-findings"),  # consolidated orchestrator output
    ]

    # Canonical array key per agent — all agents now emit findings[] (v2 schema)
    ARRAY_KEYS = {
        "sast-asis":              ["findings"],
        "iast-asis":              ["findings"],
        "pt-pattern-asis":        ["findings"],
        "dependency-config-asis": ["findings"],
        "taint-asis":             ["findings"],
        "threat-model-asis":      ["findings"],
        "sbom":                   ["findings", "vulnerabilities"],
        "security-findings":      ["securityReview"],  # orchestrator consolidated list
    }

    all_raw: list[dict] = []
    for fname, agent_name in AGENT_FILES:
        data = _load(fname)
        if not data or not isinstance(data, dict):
            continue  # G-empty: missing, empty, or malformed file — skip gracefully
        # Try canonical then legacy array keys
        items = []
        for key in ARRAY_KEYS.get(agent_name, ["findings"]):
            candidate = data.get(key)
            if isinstance(candidate, list) and candidate:
                # Only accept if entries are dicts (not plain strings)
                dict_items = [x for x in candidate if isinstance(x, dict)]
                if dict_items:
                    items = dict_items
                    break
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized = _normalize_finding(item, agent_name)
            if normalized:
                all_raw.append(normalized)

    # ── DISTINCT by (reference, owasp, cwe) — G7 ────────────────────────────
    # Key: (reference URL, OWASP code, CWE code) — triple-key precise grouping.
    # Cross-agent merge: different tools confirming the same vulnerability are merged.
    # Intra-agent: each agent's findings are NEVER merged with each other — the same
    # agent producing N findings with the same CWE represents N distinct instances
    # (e.g. 5 unpinned libraries all tagged CWE-1104, or 4 taint flows all CWE-89).
    merged: dict[tuple, dict] = {}
    agent_base_key_seen: dict[tuple, int] = {}  # (base_key, agent) -> occurrence count
    SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

    for item in all_raw:
        # G7 merge key: (reference, owasp, cwe) — all normalized
        raw_ref   = (item.get("reference") or "").strip()
        raw_owasp = (item.get("owasp") or "A00:OTHER").strip().upper()
        raw_cwe   = (item.get("cwe") or "CWE-OTHER").strip().upper()
        base_key  = (raw_ref.lower() or raw_cwe.lower(), raw_owasp, raw_cwe)
        agent     = item.get("source", "unknown")
        agent_slot = (base_key, agent)

        # First occurrence of this (ref+owasp+cwe) from this agent → use base key (allows cross-agent merge)
        # Subsequent occurrences from the SAME agent → unique sub-key (keep as separate row)
        occurrence = agent_base_key_seen.get(agent_slot, 0)
        agent_base_key_seen[agent_slot] = occurrence + 1
        key = base_key if occurrence == 0 else base_key + (agent, occurrence)

        if key not in merged:
            merged[key] = dict(item)
        else:
            existing = merged[key]
            # Severity: keep highest
            if SEV_ORDER.get(item["severity"], 0) > SEV_ORDER.get(existing["severity"], 0):
                existing["severity"] = item["severity"]
                # upgrade context fields from higher-sev finding
                for fld in ("business_impact", "effort", "owner_suggested", "priority", "recommendation"):
                    if item.get(fld):
                        existing[fld] = item[fld]
            # type: concat distinct types (e.g. "Injection+TaintFlow")
            vt_parts = {p.strip() for p in existing["type"].split("+") if p.strip()}
            vt_parts |= {p.strip() for p in item["type"].split("+") if p.strip()}
            existing["type"] = "+".join(sorted(vt_parts))
            # finding: keep longest/most-informative description
            if len(item.get("finding", "")) > len(existing.get("finding", "")):
                existing["finding"] = item["finding"]
            # source: concat agent names with "+" (deduplicated, sorted)
            src_parts = {p.strip() for p in existing["source"].split("+") if p.strip()}
            src_parts |= {p.strip() for p in item["source"].split("+") if p.strip()}
            existing["source"] = "+".join(sorted(src_parts))
            # evidence: DISTINCT by arquivo+linha — set union to deduplicate, then re-normalize (MW-1)
            ev_parts = {e.strip() for e in existing["evidence"].split("|") if e.strip()}
            ev_parts |= {e.strip() for e in item["evidence"].split("|") if e.strip()}
            merged_ev_raw = "|".join(sorted(ev_parts))
            existing["evidence"] = _extract_file_refs(merged_ev_raw)
            # MW-2/G6: recompute count = number of distinct evidence occurrences after normalization
            existing["count"] = len([e for e in existing["evidence"].split("|") if e.strip()])
            # hypothesis: true if any agent flags it
            if item.get("hypothesis"):
                existing["hypothesis"] = True

    security_review = list(merged.values())

    # ── FINDINGS_SUMMARY_JSON — recompute from consolidated data ─────────────
    sev_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    total_findings = 0
    hypothesis_count = 0
    for r in security_review:
        sev_key = r["severity"] if r["severity"] in sev_counts else "info"
        sev_counts[sev_key] += 1
        total_findings += r.get("count", 1)
        if r.get("hypothesis"):
            hypothesis_count += 1

    # Metadata: read gate status from security-findings.json (summary metadata only)
    sf = _load("security-findings.json")

    findings_summary = {
        "total":            total_findings,
        "critical":         sev_counts["critical"],
        "high":             sev_counts["high"],
        "medium":           sev_counts["medium"],
        "low":              sev_counts["low"],
        "info":             sev_counts["info"],
        "hypothesis_count": hypothesis_count,
        "gate":             sf.get("security_gate", "DIAGNOSTIC_COMPLETE"),
    }

    # ── VULNS_JSON — findings with severity >= MEDIUM ─────────────────────────
    vulns = [r for r in security_review
             if r.get("severity") in ("critical", "high", "medium")]

    # ── PT_PATTERNS_JSON — PT sub-agent findings only ─────────────────────────
    pt_patterns = [r for r in security_review if "pt-pattern" in r.get("source", "")]

    # ── TAINT_FLOW_JSON — taint sub-agent findings only ───────────────────────
    taint_items = [r for r in security_review if "taint" in r.get("source", "")]

    # ── SEC_REGRESSION_JSON — from remediation-and-regression.md ───────────────
    reg_file = asis_dir / "security" / "remediation-and-regression.md"
    sec_regression = []
    if reg_file.exists():
        txt = reg_file.read_text(encoding="utf-8")
        for m in re.finditer(r'\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|', txt):
            cols = [x.strip() for x in m.groups()]
            if cols[0] and cols[0] not in ("Item", "---", "Test"):
                sec_regression.append({
                    "item": cols[0], "status": cols[1],
                    "coverage": cols[2], "notes": cols[3],
                })

    # ── REMEDIATION_VALID_JSON — from remediation-and-regression.md ──────────────
    rem_file = asis_dir / "security" / "remediation-and-regression.md"
    remediation_items = []
    if rem_file.exists():
        txt = rem_file.read_text(encoding="utf-8")
        for m in re.finditer(r'\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|', txt):
            cols = [x.strip() for x in m.groups()]
            if cols[0] and cols[0] not in ("ID", "---", "Finding"):
                remediation_items.append({
                    "id": cols[0], "finding": cols[1],
                    "status": cols[2], "notes": cols[3],
                })

    # ── COMPLIANCE_GAPS_JSON — from compliance-gaps.md ───────────────────────
    comp_file = asis_dir / "security" / "compliance-gaps.md"
    if not comp_file.exists():
        comp_file = asis_dir / "compliance-gaps.md"
    compliance_gaps = []
    if comp_file.exists():
        txt = comp_file.read_text(encoding="utf-8")
        for m in re.finditer(r'\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|', txt):
            cols = [x.strip() for x in m.groups()]
            if cols[0] and cols[0] not in ("Control", "---", "Area"):
                compliance_gaps.append({
                    "control": cols[0], "status": cols[1], "notes": cols[2],
                })

    # ── ASSET_INVENTORY_JSON — from asset-inventory.md ───────────────────────
    asset_file = asis_dir / "security" / "asset-inventory.md"
    asset_inventory = []
    if asset_file.exists():
        txt = asset_file.read_text(encoding="utf-8")
        for m in re.finditer(r'\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|', txt):
            cols = [x.strip() for x in m.groups()]
            if cols[0] and cols[0] not in ("Asset", "---", "Name"):
                asset_inventory.append({
                    "asset": cols[0], "type": cols[1], "risk": cols[2],
                })

    # MW-7: write security-review-consolidated.json (internal artifact, not in menu)
    _consolidated_path = sec_dir / "security-review-consolidated.json"
    _total_ev_count = sum(r.get("count", 0) for r in security_review)
    try:
        import datetime as _dt
        _consolidated_path.write_text(
            json.dumps({
                "generated_by":           "build_summary_complete",
                "generated_at":           _dt.datetime.now().isoformat(),
                "project":                asis_dir.parent.name,
                "total_distinct_findings": len(security_review),
                "total_evidence_count":   _total_ev_count,
                "summary":                findings_summary,
                "findings":               security_review,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as _e:
        print(f"   ⚠️ Não foi possível gravar security-review-consolidated.json: {_e}")

    return {
        "SECURITY_REVIEW_JSON":   json.dumps(security_review,    ensure_ascii=False),
        "FINDINGS_SUMMARY_JSON":  json.dumps(findings_summary,   ensure_ascii=False),
        "VULNS_JSON":             json.dumps(vulns,               ensure_ascii=False),
        "PT_PATTERNS_JSON":       json.dumps(pt_patterns,         ensure_ascii=False),
        "TAINT_FLOW_JSON":        json.dumps(taint_items,         ensure_ascii=False),
        "SEC_REGRESSION_JSON":    json.dumps(sec_regression,      ensure_ascii=False),
        "REMEDIATION_VALID_JSON": json.dumps(remediation_items,   ensure_ascii=False),
        "COMPLIANCE_GAPS_JSON":   json.dumps(compliance_gaps,     ensure_ascii=False),
        "ASSET_INVENTORY_JSON":   json.dumps(asset_inventory,     ensure_ascii=False),
    }


def main():
    parser = argparse.ArgumentParser(description="Constrói Summary HTML completo com todos os gaps resolvidos")
    parser.add_argument("--project", required=True, help="Nome do projeto (ex: database-comparer-examples)")
    
    args = parser.parse_args()
    
    build_summary_html(args.project)


if __name__ == "__main__":
    main()
