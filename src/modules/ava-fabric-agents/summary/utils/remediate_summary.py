#!/usr/bin/env python3
"""Post-pipeline repair for the AVA Fabric Summary HTML (ava-summary-remediation).

Runs Phase 0-7 (audit, artifact resolution, diagram synthesis, Mermaid
sanitization, security reconciliation, content/UI guard verification,
rebuild, re-validate) against a project's outputs/ directory, then writes
remediation-report.md/.json. Never overwrites an existing outputs/ artifact
other than the Summary HTML and its own report files.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

UTILS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(UTILS_DIR))
from build_summary_comprehensive import sanitize_mmd  # noqa: E402
import validate_summary  # noqa: E402

BASE_DIR = Path('.')
SYNTH_TAG = "# synthesized-by-FS — replace with output from @{agent}\n"


def _mmd_with_tag(agent: str, content: str) -> str:
    """Mermaid does not support '#' comments and requires the diagram-type
    keyword (flowchart/sequenceDiagram/C4Context/...) to be the first
    significant token — prepending SYNTH_TAG as a leading '#' line (fine for
    .md files) breaks diagram-type auto-detection ('No diagram type
    detected'). Mermaid does support trailing '%%' line comments, so the
    provenance tag is appended there instead."""
    return content.rstrip("\n") + f"\n%% synthesized-by-FS - replace with output from @{agent}\n"

DIAGRAM_NAME_PATTERN = re.compile(
    r"(c4-context|c4-container|c4-component|"
    r"component-diagram|architecture-blueprint|seq-|sequen)",
    re.IGNORECASE,
)

def write_if_absent(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def run_script(script_name: str, project_name: str, extra_args=None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(UTILS_DIR / script_name), "--project", project_name]
    if extra_args:
        args.extend(extra_args)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(args, cwd=str(BASE_DIR.resolve()), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env)


def _run_validator(
    project_name: str,
    auto_fix: bool = False,
    max_fix_passes: int = 2,
    language_target: str = "en",
    deep: bool = False,
) -> dict | None:
    """Run the validator in-process and return the result dict.

    When ``deep=True``, also runs DEEP_CHECKS (C12.1–C12.7) and writes
    ``deep-audit-report.json`` so that ``phase8_deep_audit_triage`` always
    has a fresh report regardless of whether ``phase6_rebuild`` ran.
    """
    try:
        ctx = validate_summary._load_ctx(project_name)
    except FileNotFoundError:
        return None
    ctx.language_target = language_target
    results = validate_summary._run_checks(ctx)
    applied_fixes: list[str] = []
    if auto_fix:
        for _ in range(max_fix_passes):
            err_before = sum(1 for c, r in results if not r.ok and c.level == "error")
            if err_before == 0:
                break
            fixed, changed = validate_summary._try_auto_fix(ctx, results)
            if not changed:
                break
            applied_fixes.extend(fixed)
            ctx.html_path.write_text(ctx.html, encoding="utf-8")
            results = validate_summary._run_checks(ctx)
    if deep:
        try:
            deep_results = validate_summary._run_deep_checks(ctx)
            validate_summary._write_deep_audit_json(ctx, deep_results)
        except Exception as _exc:
            pass  # deep audit is non-blocking; standard results still returned
    return validate_summary._format_json(results, ctx, applied_fixes=applied_fixes)


def phase0_audit(project_name: str, log: list[str], language_target: str = "en") -> tuple[bool, list[dict]]:
    log.append("## Fase 0 — Pré-voo & Auditoria")
    template_path = BASE_DIR / "src/modules/ava-fabric-agents/summary/templates/html/summary-template.html"
    if not template_path.exists():
        log.append(f"❌ BLOCKED: template ausente em {template_path}")
        return False, []

    config_path = BASE_DIR / f"projects/{project_name}/context/project-config.yaml"
    if not config_path.exists():
        log.append(f"⚠️ project-config.yaml ausente em {config_path} — algumas fases podem ficar limitadas")

    jb = _run_validator(project_name, language_target=language_target)
    if jb is None:
        log.append("⏭️ Nenhum Summary HTML existente ainda — pulando baseline (primeira execução)")
        return True, []
    failures_before = [c for c in jb["checks"] if c["status"] == "fail"]
    log.append(f"Validador baseline: {len(failures_before)} falhas antes da remediação")
    return True, failures_before


def phase1_artifact_resolution(project_name: str, log: list[str]) -> list[str]:
    log.append("## Fase 1 — Resolução de Artefatos")
    synthesized: list[str] = []
    asis = BASE_DIR / f"projects/{project_name}/outputs/asis"
    tobe = BASE_DIR / f"projects/{project_name}/outputs/tobe"

    # `test-cases-overview.md` is a derived Summary artifact.  It belongs to
    # the same phase as its source: AS-IS under asis/qa and TO-BE under
    # tobe/qa.  Never copy or synthesize a TO-BE overview into AS-IS during
    # remediation; the official builder regenerates both locations safely.
    stale_asis_overview = asis / "qa/test-cases-overview.md"
    asis_test_cases = asis / "qa/test-cases.md"
    tobe_test_cases = tobe / "qa/test-cases.md"
    if stale_asis_overview.exists() and not asis_test_cases.exists() and tobe_test_cases.exists():
        log.append(
            "⚠️ test-cases-overview.md em asis/qa é órfão em relação ao contrato atual; "
            "será ignorado pelo Summary. O overview TO-BE será gerado em tobe/qa/"
        )

    # Rule A — Screen Navigation Map
    screen_flow = asis / "docs/screen-flow.mmd"
    screen_nav = asis / "docs/screen-navigation-map.md"
    if screen_flow.exists() and not screen_nav.exists():
        content = (
            SYNTH_TAG.replace("{agent}", "ava-asis-documentation")
            + "## Screen Navigation Flow\n\n```mermaid\n"
            + screen_flow.read_text(encoding="utf-8")
            + "\n```\n\n## Screen Inventory\n\n"
              "| Screen | Module | Type | Primary Action |\n"
              "|--------|--------|------|----------------|\n"
              "| See screen-rules.md for full inventory | — | — | — |\n"
        )
        if write_if_absent(screen_nav, content):
            synthesized.append(str(screen_nav))

    # Rule B — Security Map
    security_map = asis / "security-map.md"
    if not security_map.exists():
        for candidate in ("security-summary.md", "security/security-review.md"):
            src = asis / candidate
            if src.exists():
                content = (
                    SYNTH_TAG.replace("{agent}", "ava-asis-security-orchestrator")
                    + "## OWASP Mapping\n\n"
                      "| OWASP | Category | Status | Evidence |\n"
                      "|-------|----------|--------|----------|\n"
                )
                for owasp_id in [f"A{n:02d}" for n in range(1, 11)]:
                    content += f"| {owasp_id} | — | N/A | (ver {candidate}) |\n"
                if write_if_absent(security_map, content):
                    synthesized.append(str(security_map))
                break

    # Rule C — Test files. `test-qa-asis.md`'s real Output Contract location is
    # Rule C — Test Gaps AS-IS (bridge-fastqa-asis v4.1.0 Step 15)
    # test-gaps.md is produced by ava-asis-bridge-fastqa Step 15.
    # For Delphi projects, coverage data comes from 09_test_coverage.json.
    # Only synthesize placeholder when test-gaps.md is absent AND AST reports zero tests.
    qa_dir = asis / "qa"
    test_gaps_qa = qa_dir / "test-gaps.md"
    ast_test_coverage = asis / "delphi-ast-raw" / "compressed" / "09_test_coverage.json"

    def _has_real_ast_tests() -> bool:
        if not ast_test_coverage.exists():
            return False
        try:
            data = json.loads(ast_test_coverage.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        counts = (data.get("payload") or {}).get("counts") or {}
        return bool((counts.get("test_units") or 0) > 0 or (counts.get("test_methods") or 0) > 0)

    if not test_gaps_qa.exists() and not _has_real_ast_tests():
        if write_if_absent(
            test_gaps_qa,
            SYNTH_TAG.replace("{agent}", "ava-asis-bridge-fastqa")
            + "## Test Gaps\n\n"
              "| ID | Descrição | Categoria | Módulo | Risco | Recomendação |\n"
              "|----|-----------|-----------|--------|-------|--------------|\n"
              "| TG-001 | Nenhum gap de teste identificado | — | All | P2 | — |\n",
        ):
            synthesized.append(str(test_gaps_qa))

    # Rule D — Bounded Context Map (AS-IS)
    blueprint = asis / "architecture-blueprint.md"
    bc_map = asis / "bounded-context-map.md"
    if blueprint.exists() and not bc_map.exists():
        text = blueprint.read_text(encoding="utf-8")
        sections = re.findall(r"(## (?:Bounded Context|BC-\d+|Module:).*?)(?=\n## |\Z)", text, re.DOTALL)
        if sections:
            content = SYNTH_TAG.replace("{agent}", "ava-asis-solution-delphi") + "\n\n".join(sections)
            if write_if_absent(bc_map, content):
                synthesized.append(str(bc_map))

    # Rule E — OpenAPI path fix
    openapi_src = tobe / "openapi"
    openapi_dst = tobe / "docs/openapi"
    if openapi_src.is_dir() and any(openapi_src.glob("*.yaml")) and not (
        openapi_dst.is_dir() and any(openapi_dst.glob("*.yaml"))
    ):
        openapi_dst.mkdir(parents=True, exist_ok=True)
        for f in openapi_src.glob("*.yaml"):
            dst = openapi_dst / f.name
            if not dst.exists():
                dst.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                synthesized.append(str(dst))

    # Rule F — Context Map fallback
    context_map = tobe / "diagrams/context-map.mmd"
    arch_blueprint_mmd = tobe / "diagrams/architecture-blueprint.mmd"
    if arch_blueprint_mmd.exists() and not context_map.exists():
        if write_if_absent(context_map, arch_blueprint_mmd.read_text(encoding="utf-8")):
            synthesized.append(str(context_map))

    # Rule G — Create asis/diagrams/
    diagrams_dir = asis / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    # Rule H — Misplaced diagram recovery
    for wrong_dir in (asis / "db", asis / "docs", asis):
        if not wrong_dir.is_dir():
            continue
        for mmd in wrong_dir.glob("*.mmd"):
            if wrong_dir == asis and mmd.parent != asis:
                continue
            if not DIAGRAM_NAME_PATTERN.search(mmd.name):
                continue
            dst = diagrams_dir / mmd.name
            if not dst.exists():
                dst.write_text(mmd.read_text(encoding="utf-8"), encoding="utf-8")
                synthesized.append(str(dst))
                log.append(f"✅ Rule H: {mmd.name} recuperado de {wrong_dir}/ → asis/diagrams/")

    # Rule I — Business Logic in DB (Banco de Dados AS-IS section). Mirrors
    # Guardrail 8's principle: only ever synthesize a placeholder when it is
    # provably safe (confirmed zero stored procedures in
    # stored-procedures-map.md, so "no business logic in SPs" is trivially
    # true), never when SPs exist but business-logic-in-db.md is simply
    # absent — that is a genuine upstream gap (db-analyzer.md's Business
    # Logic Detector step didn't run or produce output), not something to
    # fabricate. The card/KPI legitimately showing 0/hidden in that case is
    # honest, not a bug to paper over.
    biz_logic = asis / "db/business-logic-in-db.md"
    sp_map_for_biz = asis / "db/stored-procedures-map.md"
    if not biz_logic.exists() and sp_map_for_biz.exists():
        sp_text_for_biz = sp_map_for_biz.read_text(encoding="utf-8")
        m_sp_count = re.search(r'^\|\s*Stored Procedures\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|',
                                sp_text_for_biz, re.MULTILINE)
        if m_sp_count and m_sp_count.group(1) == "0":
            if write_if_absent(
                biz_logic,
                SYNTH_TAG.replace("{agent}", "ava-asis-db-analyzer")
                + "No stored procedures exist in the legacy database — business logic "
                  "detection in stored procedures is not applicable.\n",
            ):
                synthesized.append(str(biz_logic))

    # Rule J — Test Cases AS-IS (ava-asis-bridge-fastqa Step 17b)
    # Only synthesize a placeholder when test-cases.md is absent AND there is no
    # evidence that FastQA has been run (fastqa/manual_test/ absent).
    # When fastqa/manual_test/ exists but Step 17b hasn't consolidated yet,
    # the gap is upstream — do not fabricate synthetic test cases.
    tc_path_j = qa_dir / "test-cases.md"
    if not tc_path_j.exists():
        has_fastqa_manual = (BASE_DIR / "fastqa" / "manual_test").exists()
        if not has_fastqa_manual:
            if write_if_absent(
                tc_path_j,
                SYNTH_TAG.replace("{agent}", "ava-asis-bridge-fastqa")
                + "# Test Cases AS-IS\n\n"
                  "> No test cases available. "
                  "Run @ava-asis-bridge-fastqa (Step 17b) to consolidate "
                  "test cases from fastqa/manual_test/test_cases/.\n",
            ):
                synthesized.append(str(tc_path_j))
                log.append("✅ Rule J: synthesized placeholder test-cases.md")

    log.append(f"{len(synthesized)} artefato(s) sintetizado(s)")
    return synthesized


ASIS_DIAGRAM_TEMPLATES = {
    "c4-context.mmd": (
        "ava-asis-solution-delphi",
        "C4Context\n  title Context — {project_name} AS-IS\n"
        '  System(sys, "{legacy_technology} Application", "Sistema legado")\n'
        '  Person(user, "Usuário", "Operador do sistema")\n'
        "  Rel(user, sys, \"Utiliza\")\n",
    ),
    "c4-container.mmd": (
        "ava-asis-solution-delphi",
        "C4Container\n  title Containers — {project_name} AS-IS\n"
        '  System_Boundary(sys, "{legacy_technology}") {{\n'
        '    Container(ui, "Interface {legacy_technology}", "Forms/VCL", "Telas e lógica de negócio")\n'
        '    ContainerDb(db, "Banco de Dados", "SGBD legado", "Dados persistidos")\n'
        "  }}\n",
    ),
    "c4-component.mmd": (
        "ava-asis-solution-delphi",
        "C4Component\n  title Components — {project_name} AS-IS\n"
        '  Container_Boundary(app, "{legacy_technology}") {{\n'
        '    Component(c1, "Módulo Principal", "TForm", "Módulo de negócio")\n'
        "  }}\n",
    ),
    "component-diagram.mmd": (
        "ava-asis-solution-delphi",
        'flowchart TB\n  subgraph AS_IS["{project_name} AS-IS"]\n'
        '    UI["Interface {legacy_technology}"]\n'
        '    DB["Banco de Dados"]\n'
        "    UI --> DB\n  end\n",
    ),
    "seq-baixa-cp.mmd": (
        "ava-asis-solution-delphi",
        'sequenceDiagram\n  actor Usu as "Usuário"\n'
        '  participant Form as "Tela Baixa CP"\n'
        '  participant DB as "Banco de Dados"\n'
        "  Usu->>Form: Selecionar título\n"
        "  Form->>DB: Buscar conta a pagar\n"
        "  DB-->>Form: Dados do título\n"
        "  Usu->>Form: Confirmar baixa\n"
        "  Form->>DB: Atualizar status = pago\n"
        "  DB-->>Form: Confirmação\n"
        "  Form-->>Usu: Baixa registrada\n",
    ),
    "seq-cadastro-cp.mmd": (
        "ava-asis-solution-delphi",
        'sequenceDiagram\n  actor Usu as "Usuário"\n'
        '  participant Form as "Tela Cadastro CP"\n'
        '  participant DB as "Banco de Dados"\n'
        "  Usu->>Form: Preencher dados\n"
        "  Form->>DB: Validar fornecedor\n"
        "  DB-->>Form: Fornecedor válido\n"
        "  Usu->>Form: Confirmar cadastro\n"
        "  Form->>DB: INSERT conta a pagar\n"
        "  DB-->>Form: Registro criado\n"
        "  Form-->>Usu: CP cadastrada\n",
    ),
}

TOBE_DIAGRAM_TEMPLATES = {
    "clean-architecture.mmd": (
        "ava-tobe-architecture-design",
        'flowchart TB\n  subgraph Domain["Domain Layer"]\n'
        '    E["Entities"]\n    VO["Value Objects"]\n    DE["Domain Events"]\n  end\n'
        '  subgraph Application["Application Layer"]\n'
        '    UC["Use Cases"]\n    CMD["Commands / Queries"]\n    PORT["Ports"]\n  end\n'
        '  subgraph Infrastructure["Infrastructure Layer"]\n'
        '    REPO["Repositories"]\n    EXT["External Services"]\n    DB2["DB Adapters"]\n  end\n'
        '  subgraph Presentation["Presentation Layer"]\n'
        '    API["REST API"]\n    CTRL["Controllers"]\n  end\n'
        "  Presentation --> Application\n  Application --> Domain\n"
        "  Infrastructure --> Application\n  Infrastructure --> Domain\n",
    ),
    "solution-structure.mmd": (
        "ava-tobe-architecture-technical",
        'flowchart TB\n  subgraph Solution["{project_name}"]\n'
        '    API["{backend_framework} API"]\n'
        '    FE["{frontend_framework} Frontend"]\n'
        '    DB3["Database"]\n  end\n'
        "  FE -->|HTTP REST| API\n  API --> DB3\n",
    ),
    "migration-gantt.mmd": (
        "ava-tobe-migration-plan",
        "gantt\n  title Migration Plan — {project_name}\n"
        "  dateFormat YYYY-MM-DD\n  axisFormat %b %Y\n"
        "  section Wave 1\n    Setup & Foundation :w1, 2024-01-01, 30d\n"
        "  section Wave 2\n    Core Migration :w2, after w1, 45d\n"
        "  section Wave 3\n    Cutover & Decommission :w3, after w2, 30d\n",
    ),
}


def _yaml_scalar(raw: str) -> str:
    """Extract a single-line YAML scalar value, stripping a trailing '# ...'
    comment. A quoted value (e.g. `"X"  # Ex: "Y", "Z"`) is matched explicitly
    first so an unrelated '#' inside the comment never leaks into the value —
    a plain `.strip('#', 1)[0]` would still be correct here since the value
    itself is quoted, but matching the quoted token directly is more robust
    if the value ever contains a literal '#' of its own."""
    raw = raw.strip()
    qm = re.match(r'^(".*?"|\'.*?\')', raw)
    if qm:
        return qm.group(1).strip('"\'')
    return raw.split('#', 1)[0].strip().strip('"\'')


def _read_project_config(project_name: str) -> dict:
    config_path = BASE_DIR / f"projects/{project_name}/context/project-config.yaml"
    if not config_path.exists():
        return {}
    text = config_path.read_text(encoding="utf-8")
    result = {}
    for key in ("project_name", "legacy_technology"):
        m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
        if m:
            result[key] = _yaml_scalar(m.group(1))
    for key, target in (("backend_framework", "backend_framework"), ("frontend_framework", "frontend_framework")):
        m = re.search(rf"{key}:\s*(.+)$", text, re.MULTILINE)
        if m:
            result[target] = _yaml_scalar(m.group(1))
    return result


def phase2_diagram_synthesis(project_name: str, log: list[str]) -> list[str]:
    log.append("## Fase 2 — Síntese de Diagramas Ausentes")
    synthesized: list[str] = []
    cfg = _read_project_config(project_name)
    fmt = {
        "project_name": cfg.get("project_name", project_name),
        "legacy_technology": cfg.get("legacy_technology", "Legacy"),
        "backend_framework": cfg.get("backend_framework", "Backend"),
        "frontend_framework": cfg.get("frontend_framework", "Frontend"),
    }

    diagrams_dir = BASE_DIR / f"projects/{project_name}/outputs/asis/diagrams"
    for filename, (agent, template) in ASIS_DIAGRAM_TEMPLATES.items():
        target = diagrams_dir / filename
        content = _mmd_with_tag(agent, template.format(**fmt))
        if write_if_absent(target, content):
            synthesized.append(str(target))

    er_target = BASE_DIR / f"projects/{project_name}/outputs/asis/db/er-diagram.mmd"
    if write_if_absent(
        er_target,
        _mmd_with_tag("ava-asis-db-analyzer", "erDiagram"),
    ):
        synthesized.append(str(er_target))

    tobe_diagrams_dir = BASE_DIR / f"projects/{project_name}/outputs/tobe/diagrams"
    for filename, (agent, template) in TOBE_DIAGRAM_TEMPLATES.items():
        target = tobe_diagrams_dir / filename
        if write_if_absent(target, _mmd_with_tag(agent, template.format(**fmt))):
            synthesized.append(str(target))

    log.append(f"{len(synthesized)} diagrama(s) sintetizado(s)")
    return synthesized


_LEGACY_LEADING_TAG_RE = re.compile(r'^#\s*synthesized-by-FS[^\n]*\n')
_LEAKED_YAML_COMMENT_RE = re.compile(r'\s*#\s*Ex:\s*"[^"\n]*"(?:\s*,\s*"[^"\n]*")*')


def _repair_leaked_yaml_comment(content: str) -> str:
    """Self-heal .mmd files synthesized by an earlier (buggy) version of this
    script, which read project_name from project-config.yaml with a regex
    that captured the value's trailing YAML comment too (e.g. `key: "X"  #
    Ex: "Meu-ERP", "Projeto-X"`), leaking `# Ex: "..."` literally into a
    diagram node/subgraph label and breaking the Mermaid parser."""
    return _LEAKED_YAML_COMMENT_RE.sub('', content)


def _repair_legacy_leading_tag(content: str) -> str:
    """Self-heal .mmd files written by an earlier (buggy) version of this
    script, which prepended '# synthesized-by-FS ...' as a literal first
    line — Mermaid requires the diagram-type keyword to be the first
    significant token, so this broke rendering ('No diagram type detected').
    Moves the tag to a trailing '%%' comment, matching _mmd_with_tag()."""
    m = _LEGACY_LEADING_TAG_RE.match(content)
    if not m:
        return content
    tag_text = m.group(0).strip().lstrip('#').strip()
    rest = content[m.end():]
    return rest.rstrip("\n") + f"\n%% {tag_text}\n"


def phase3_mermaid_sanitization(project_name: str, log: list[str]) -> int:
    log.append("## Fase 3 — Sanitização Mermaid")
    outputs_dir = BASE_DIR / f"projects/{project_name}/outputs"
    modified = 0
    for mmd in outputs_dir.rglob("*.mmd"):
        original = mmd.read_text(encoding="utf-8")
        repaired = _repair_leaked_yaml_comment(_repair_legacy_leading_tag(original))
        sanitized = sanitize_mmd(repaired)
        if sanitized != original:
            mmd.write_text(sanitized, encoding="utf-8")
            modified += 1
    log.append(f"{modified} arquivo(s) .mmd sanitizado(s)")
    return modified


CAT_TO_TYPE = {
    "a03": "Injection", "a01": "BrokenAccessControl", "a07": "AuthFailure",
    "a02": "CryptoFailure", "a06": "VulnerableComponents",
}
CWE_MAP = {"a03": "CWE-89", "a01": "CWE-284", "a07": "CWE-306", "a02": "CWE-327", "a06": "CWE-1035"}


def phase35_playwright_gate(
    project_name: str,
    log: list[str],
    skip_mermaid_gate: bool = False,
    mermaid_guardrails_path: str | None = None,
    mermaid_gate_max_attempts: int = 3,
):
    """Phase 3.5 — Playwright Mermaid Validation & Auto-Fix Gate.

    Runs the gate on the most recently generated Summary HTML.
    Returns the MermaidGateResult object (or None if no HTML was found / gate disabled).
    Never writes outside projects/{project_name}/outputs/summary/ (RF8 isolation).
    """
    log.append("## Fase 3.5 — Playwright Mermaid Validation & Auto-Fix Gate")

    if skip_mermaid_gate:
        log.append("ℹ️ Gate DISABLED (--skip-mermaid-gate) — nenhum browser iniciado")
        # Still write the DISABLED report for audit consistency
        summary_dir = BASE_DIR / f"projects/{project_name}/outputs/summary"
        html_candidates = sorted(
            summary_dir.glob("AVA-FABRIC-SUMMARY-*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if summary_dir.exists() else []
        try:
            import importlib.util as _ilu
            import sys as _sys_2
            _gate_spec = _ilu.spec_from_file_location(
                "mermaid_playwright_gate",
                UTILS_DIR / "mermaid_playwright_gate.py",
            )
            _gate_mod = _ilu.module_from_spec(_gate_spec)
            _sys_2.modules["mermaid_playwright_gate"] = _gate_mod
            _gate_spec.loader.exec_module(_gate_mod)
            _html = html_candidates[0] if html_candidates else (summary_dir / "summary.html")
            return _gate_mod.write_disabled_report(_html)
        except Exception as _e:
            log.append(f"⚠️ Gate (DISABLED) report write error: {_e}")
        return None

    # Locate the latest HTML
    summary_dir = BASE_DIR / f"projects/{project_name}/outputs/summary"
    html_candidates = sorted(
        summary_dir.glob("AVA-FABRIC-SUMMARY-*.html"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if summary_dir.exists() else []

    if not html_candidates:
        log.append("⏭️ Nenhum HTML encontrado em outputs/summary/ — gate pulado")
        return None

    html_path = html_candidates[0]
    log.append(f"Gate rodando sobre: {html_path.name}")

    try:
        import importlib.util as _ilu
        import sys as _sys
        _gate_spec = _ilu.spec_from_file_location(
            "mermaid_playwright_gate",
            UTILS_DIR / "mermaid_playwright_gate.py",
        )
        _gate_mod = _ilu.module_from_spec(_gate_spec)
        # Python 3.14 fix: dataclasses accesses sys.modules[module_name].__dict__
        # during exec_module. We must pre-register in sys.modules so the
        # dataclass decorator finds the namespace.
        _sys.modules["mermaid_playwright_gate"] = _gate_mod
        _gate_spec.loader.exec_module(_gate_mod)

        _guardrails = Path(mermaid_guardrails_path) if mermaid_guardrails_path else None
        gate_result = _gate_mod.run_playwright_mermaid_gate(
            html_path       = html_path,
            guardrails_path = _guardrails,
            max_attempts    = mermaid_gate_max_attempts,
        )
        status = gate_result.overall_status
        if status == "PASS":
            log.append(f"✅ Gate PASS — {gate_result.total_diagrams} diagrama(s) OK")
        elif status == "PASS_WITH_FIXES":
            log.append(
                f"✅ Gate PASS_WITH_FIXES — {gate_result.total_fixed} corrigido(s), "
                f"{gate_result.total_valid} válido(s)"
            )
        elif status == "SKIPPED":
            log.append("⚠️ Gate SKIPPED — Chromium indisponível (ver stderr)")
        elif status == "FAIL":
            log.append(
                f"⚠️ Gate FAIL — {gate_result.total_unresolved} diagrama(s) não resolvido(s) "
                f"após {mermaid_gate_max_attempts} tentativa(s). "
                f"Ver mermaid-validation-report.json."
            )
        return gate_result
    except Exception as _e:
        log.append(f"⚠️ Gate error (não-fatal): {_e}")
        return None


def _load_authoritative_gate_result(project_name: str):
    """Reload the mermaid-validation-report.json written by the Phase G
    gate INSIDE build_summary_comprehensive.py's subprocess (Phase 6
    rebuild), which reflects the FINAL published HTML — not the
    pre-rebuild HTML probed by Phase 3.5. Returns a lightweight object
    exposing the same attributes as MermaidGateResult (overall_status,
    total_diagrams, total_valid, total_fixed, total_unresolved,
    generated_at), or None if the report is missing/unreadable.

    This closes the gap where remediation-report.json's `mermaid_gate`
    section could diverge from the actual mermaid-validation-report.json
    of the same run (Round 2 analysis, I5).
    """
    report_path = (
        BASE_DIR / f"projects/{project_name}/outputs/summary/mermaid-validation-report.json"
    )
    if not report_path.exists():
        return None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    from types import SimpleNamespace
    return SimpleNamespace(
        overall_status   = data.get("overall_status", "FAIL"),
        total_diagrams   = data.get("total_diagrams", 0),
        total_valid      = data.get("total_valid", 0),
        total_fixed      = data.get("total_fixed", 0),
        total_unresolved = data.get("total_unresolved", 0),
        generated_at     = data.get("generated_at", ""),
    )


def phase4_security_reconciliation(project_name: str, log: list[str]) -> bool:
    log.append("## Fase 4 — Reconciliação de Dados de Segurança")
    findings_path = BASE_DIR / f"projects/{project_name}/outputs/asis/security/security-findings.json"
    risk_path = BASE_DIR / f"projects/{project_name}/outputs/asis/risk-register.json"

    try:
        findings = json.loads(findings_path.read_text(encoding="utf-8")) if findings_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        findings = {}
    review = findings.get("securityReview", []) if isinstance(findings, dict) else []
    if review:
        log.append(f"⏭️ {len(review)} findings já presentes — pulando")
        return False

    if not risk_path.exists():
        log.append("⏭️ risk-register.json ausente — nada a reconciliar")
        return False
    try:
        risks_raw = json.loads(risk_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    risks = risks_raw.get("risks", risks_raw) if isinstance(risks_raw, dict) else risks_raw
    if not isinstance(risks, list):
        return False

    filtered = [r for r in risks if r.get("priority") in ("P0", "P1") and r.get("owasp")]
    if not filtered:
        log.append("⏭️ nenhum risco P0/P1 com campo owasp preenchido")
        return False

    reconciled = []
    owasp_seen = set()
    for i, risk in enumerate(filtered):
        owasp_raw = str(risk.get("owasp", "")).upper()
        owasp_key = owasp_raw.split(":")[0].lower()
        owasp_seen.add(owasp_raw if ":" in owasp_raw else f"{owasp_raw}:2021")
        evidence = risk.get("evidence")
        evidences = evidence if isinstance(evidence, list) else [risk.get("description", "")]
        reconciled.append({
            "id": f"SF-{i + 1:03d}",
            "type": CAT_TO_TYPE.get(owasp_key, risk.get("category", "Other")),
            "severity": "CRITICAL" if risk.get("priority") == "P0" else "HIGH",
            "finding": risk.get("title", risk.get("description", "")),
            "evidences": evidences,
            "owasp": owasp_raw if ":" in owasp_raw else f"{owasp_raw}:2021",
            "cwe": risk.get("cwe", CWE_MAP.get(owasp_key, "")),
            "source": "risk-register.json (reconciled-by-remediation)",
            "count": len(evidences) if isinstance(evidences, list) else 1,
        })

    findings["securityReview"] = reconciled
    findings["owasp"] = sorted(owasp_seen)
    findings_path.parent.mkdir(parents=True, exist_ok=True)
    findings_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    log.append(f"✅ {len(reconciled)} findings de segurança reconciliados a partir de risk-register.json")
    return True


def phase5_content_ui_guard_check(project_name: str, log: list[str]) -> list[str]:
    """Reuses the validator's own C11.* checks (the same ones that guard the
    22-item traceability table) instead of a separate regex dict, so this
    phase can never drift out of sync with what validate_summary.py actually
    considers fixed."""
    log.append("## Fase 5 — Guardas de Conteúdo/UI (verificação)")
    jb = _run_validator(project_name)
    if jb is None:
        log.append("⏭️ HTML ainda não existe — verificado após a Fase 6 (rebuild)")
        return []
    found = [f"{c['id']} ({c['detail']})" for c in jb["checks"]
             if c["category"] == "Content Completeness" and c["status"] == "fail"]
    template_path = BASE_DIR / "src/modules/ava-fabric-agents/summary/templates/html/summary-template.html"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8", errors="replace")
        if 'id="et-kpi-strip"' in template and 'class="et-kpi-grid"' not in template:
            found.append("ET-KPI-CSS (Findings Overview uses unscoped legacy KPI classes)")
    # Automation Scripts is evidence-driven: the Summary must expose every
    # script-generator contract path that exists, but remediation must not
    # synthesize reports/scripts when the upstream agent has not run.
    outputs = BASE_DIR / f"projects/{project_name}/outputs"
    script_contract = [
        "qa/script-generator-report.md", "qa/scripts", "qa/scripts/run-instructions.md",
        "qa/scripts/unit/unit-tests-overview.md", "qa/scripts/unit/shared-kernel-tests.md",
        "qa/scripts/unit/domain-aggregate-tests.md", "qa/scripts/integration/integration-tests-overview.md",
        "qa/parity-suite-plan.md", "qa/parity-evidence", "qa/regression-suite",
    ]
    existing_script_artifacts = [p for p in script_contract if (outputs / p).exists()]
    log.append(
        f"ℹ️ Automation Scripts: {len(existing_script_artifacts)}/{len(script_contract)} "
        "artefatos do contrato presentes; nenhum artefato será sintetizado."
    )
    # Architecture patterns are builder-owned derived content. Audit the
    # current HTML when the source exists, but never synthesize or mutate the
    # source JSON here; the official rebuild is the repair mechanism.
    patterns_path = outputs / "tobe" / "patterns-applied.json"
    if patterns_path.exists():
        try:
            patterns_data = json.loads(patterns_path.read_text(encoding="utf-8"))
            pattern_count = len(patterns_data.get("patterns", [])) if isinstance(patterns_data, dict) else len(patterns_data)
        except (json.JSONDecodeError, OSError, TypeError):
            pattern_count = 0
        html_candidates = sorted(
            (outputs / "summary").glob("AVA-FABRIC-SUMMARY-*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if (outputs / "summary").exists() else []
        if pattern_count and html_candidates:
            html = html_candidates[0].read_text(encoding="utf-8", errors="replace")
            marker = '<tbody id="tb-tobe-patterns">'
            start = html.find(marker)
            end = html.find("</tbody>", start) if start >= 0 else -1
            fragment = html[start:end] if start >= 0 and end > start else ""
            # Empty optional trade-off/ADR cells are valid in the legacy
            # schema. A render is broken only when the identity/content cells
            # (pattern name and justification) are empty for every source row.
            data_rows = re.findall(r"<tr>(.*?)</tr>", fragment, re.S)
            populated_rows = [
                row for row in data_rows
                if re.search(r"<td>\s*[^<]+\s*</td>", row)
                and len(re.findall(r"<td>\s*[^<]+\s*</td>", row)) >= 3
            ]
            if pattern_count and len(populated_rows) < pattern_count:
                found.append("TOBE-PATTERNS-EMPTY (source patterns-applied.json exists but rendered cells are empty)")
            log.append(f"ℹ️ TO-BE Architecture Patterns: {pattern_count} source patterns; rebuild verification enabled.")
    if found:
        log.append(
            "⚠️ Guardas C11 ainda falhando após rebuild: " + "; ".join(found)
            + " — o template/builder deste branch pode não incluir todos os fixes permanentes desta feature."
        )
    else:
        log.append("✅ Todas as guardas C11 (Content Completeness) passam")

    # The TO-BE test-plan page is evidence-driven.  If the contractual test
    # artifacts exist but the generated payload is empty, report it as a
    # remediation finding instead of silently accepting a hidden card.
    test_plan_sources = [
        outputs / "tobe/qa/test-plan.md",
        outputs / "tobe/tests/functional-test-matrix.md",
    ]
    if any(p.exists() and p.stat().st_size > 0 for p in test_plan_sources):
        html_candidates = sorted(
            (outputs / "summary").glob("AVA-FABRIC-SUMMARY-*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if (outputs / "summary").exists() else []
        if html_candidates:
            html = html_candidates[0].read_text(encoding="utf-8", errors="replace")
            payload_match = re.search(r"testPlan:\s*(\[[^;]*\])", html, re.S)
            if payload_match and payload_match.group(1).strip() == "[]":
                finding = "TOBE-TESTPLAN-EMPTY (test-plan artifacts exist but TESTPLAN_JSON is empty)"
                found.append(finding)
                log.append(f"⚠️ {finding}")

    # Coverage Gap Strategy is also evidence-driven.  The remediation must
    # catch both the legacy structured and the current narrative gap report
    # when the source is populated but the builder published an empty payload.
    gap_source = outputs / "tobe/qa/gap-analysis.md"
    if gap_source.exists() and gap_source.stat().st_size > 0:
        html_candidates = sorted(
            (outputs / "summary").glob("AVA-FABRIC-SUMMARY-*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if (outputs / "summary").exists() else []
        if html_candidates:
            html = html_candidates[0].read_text(encoding="utf-8", errors="replace")
            payload_match = re.search(r"coverageGapStrategy:\s*(\[[^;]*?\])\s*,", html, re.S)
            if payload_match and payload_match.group(1).strip() == "[]":
                finding = "TOBE-GAP-STRATEGY-EMPTY (gap-analysis.md exists but coverageGapStrategy is empty)"
                found.append(finding)
                log.append(f"⚠️ {finding}")
    return found


def phase6_rebuild(
    project_name: str,
    log: list[str],
    skip_mermaid_gate: bool = False,
    mermaid_guardrails_path: str | None = None,
    mermaid_gate_max_attempts: int = 3,
) -> bool:
    log.append("## Fase 6 — Rebuild")
    before = {p: p.stat().st_mtime for p in
              (BASE_DIR / f"projects/{project_name}/outputs/summary").glob("AVA-FABRIC-SUMMARY-*.html")} \
        if (BASE_DIR / f"projects/{project_name}/outputs/summary").exists() else {}
    extra: list[str] = []
    if skip_mermaid_gate:
        extra.append("--skip-mermaid-gate")
    if mermaid_guardrails_path:
        extra.extend(["--mermaid-guardrails-path", mermaid_guardrails_path])
    if mermaid_gate_max_attempts != 3:
        extra.extend(["--mermaid-gate-max-attempts", str(mermaid_gate_max_attempts)])
    result = run_script("build_summary_comprehensive.py", project_name, extra_args=extra or None)
    summary_dir = BASE_DIR / f"projects/{project_name}/outputs/summary"
    candidates = sorted(summary_dir.glob("AVA-FABRIC-SUMMARY-*.html"), key=lambda p: p.stat().st_mtime, reverse=True) \
        if summary_dir.exists() else []
    ok = bool(candidates) and (candidates[0] not in before or candidates[0].stat().st_mtime > before[candidates[0]])
    log.append("✅ Rebuild concluído" if ok else f"❌ Rebuild falhou:\n{(result.stdout + result.stderr)[-2000:]}")
    return ok


def phase7_revalidate(project_name: str, failures_before: list[dict], log: list[str], language_target: str = "en") -> dict:
    log.append("## Fase 7 — Revalidação + Relatório")
    # deep=True: ensures deep-audit-report.json is refreshed here even if
    # phase6_rebuild was skipped or the builder's step [7/6] did not run.
    # Targeted PT remediation must expose language failures directly. Do not
    # auto-fix unrelated minimal-fixture checks before accounting for C8.PT.
    jb = _run_validator(project_name, auto_fix=language_target != "pt", language_target=language_target, deep=True)
    failures_after = [c for c in jb["checks"] if c["status"] == "fail"] if jb else []

    ids_before = {f["id"] for f in failures_before}
    ids_after = {f["id"] for f in failures_after}
    errors_before = sum(1 for f in failures_before if f.get("level") == "error")
    errors_after = sum(1 for f in failures_after if f.get("level") == "error")
    fixed = sorted(ids_before - ids_after)
    remaining = sorted(ids_after)
    improvement = round(len(fixed) / max(len(ids_before), 1) * 100)

    log.append(f"Errors antes: {errors_before} | depois: {errors_after} | melhoria: {improvement}%")
    return {
        "errors_before": errors_before,
        "errors_after": errors_after,
        "improvement_pct": improvement,
        "fixed": fixed,
        "remaining": remaining,
    }


def phase8_deep_audit_triage(project_name: str, log: list) -> list:
    """Process deep-audit-report.json findings that require non-auto-correctable triage.

    Handles two non-dispatchable finding types (spec 042 §4.5):
      - **parser_gap** (branch f): Re-runs build_summary_comprehensive.py and
        captures its stdout+stderr output as a diagnostic excerpt appended to
        ``finding["suggested_fix"]``. No upstream agent is dispatched (the
        artifact already exists; the problem is in the parser, not the agent).
      - **render_gap** (branch g): Adds the finding directly to
        ``unresolved_triage_items`` with no rebuild or dispatch. The issue is
        purely in the HTML template JS render function; data is already present.

    Findings with ``auto_correctable: True`` are skipped here (handled by earlier
    phases via dispatch to the responsible upstream agent).

    Returns:
        list[dict]: Items requiring manual intervention (parser_gap and render_gap
        findings, with parser_gap entries augmented with a build output excerpt).
        Returns [] if deep-audit-report.json does not exist (guard for runs where
        --deep was not used beforehand).

    NOTE: Called directly from `main()` until `run_remediation_loop` (spec 041,
    `cat3-remediation-loop-041`) is implemented. At that point, this function
    becomes the non-dispatchable branch handler inside the loop — do NOT delete
    or replace; update the call site from `main()` to `run_remediation_loop`.
    """
    deep_audit_path = BASE_DIR / f"projects/{project_name}/outputs/summary/deep-audit-report.json"
    if not deep_audit_path.exists():
        log.append(
            "## Fase 8 — Deep Audit Triage\n"
            "Skipped: deep-audit-report.json not found. "
            "Run validate_summary.py with --deep first."
        )
        return []

    try:
        deep_audit = json.loads(deep_audit_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.append(f"## Fase 8 — Deep Audit Triage\nERROR reading deep-audit-report.json: {exc}")
        return []

    unresolved_triage_items: list = []

    for finding in deep_audit.get("findings", []):
        if finding.get("auto_correctable"):
            # Handled by earlier phases via dispatch
            continue

        finding_type = finding.get("finding_type", "")

        if finding_type == "parser_gap":
            # Branch f: re-run builder, capture output, annotate suggested_fix
            result = run_script("build_summary_comprehensive.py", project_name)
            combined_output = (result.stdout or "") + (result.stderr or "")
            excerpt = combined_output[-2000:] if combined_output.strip() else (
                "Sem output capturado — inspecionar build_summary_comprehensive.py manualmente."
            )
            annotated = dict(finding)
            annotated["suggested_fix"] = (
                finding.get("suggested_fix", "") + "\n[Build output excerpt]:\n" + excerpt
            )
            unresolved_triage_items.append(annotated)

        elif finding_type == "render_gap":
            # Branch g: add directly — no dispatch, no rebuild
            unresolved_triage_items.append(dict(finding))

    return unresolved_triage_items


def write_report(
    project_name: str,
    log: list[str],
    synthesized: list[str],
    ui_guard_findings: list[str],
    validation: dict,
    mermaid_gate_result=None,   # MermaidGateResult | None
    triage_items=None,          # list[dict] | None  (spec 042 §task 3.2)
) -> None:
    summary_dir = BASE_DIR / f"projects/{project_name}/outputs/summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    md_lines = [f"# Remediation Report — {project_name}", ""]
    md_lines.extend(log)
    md_lines.append("")
    md_lines.append(f"**Errors antes**: {validation['errors_before']}")
    md_lines.append(f"**Errors after default-language validation**: {validation['errors_after']}")
    md_lines.append(f"**Melhoria**: {validation['improvement_pct']}%")
    if validation["fixed"]:
        md_lines.append("\n## Corrigidos\n" + "\n".join(f"- ✅ {i}" for i in validation["fixed"]))
    if validation["remaining"]:
        md_lines.append("\n## Pendentes\n" + "\n".join(f"- ❌ {i}" for i in validation["remaining"]))
    if synthesized:
        md_lines.append(
            "\n## Artefatos sintetizados (tag `# synthesized-by-FS`)\n"
            + "\n".join(f"- {s}" for s in synthesized)
        )
    if ui_guard_findings:
        md_lines.append(
            "\n## Sinais de UI legada remanescentes\n"
            + "\n".join(f"- ⚠️ {f}" for f in ui_guard_findings)
        )
    if mermaid_gate_result is not None:
        md_lines.append(
            f"\n## Mermaid Gate\n"
            f"**overall_status**: `{mermaid_gate_result.overall_status}`  \n"
            f"**total_diagrams**: {mermaid_gate_result.total_diagrams} | "
            f"**fixed**: {mermaid_gate_result.total_fixed} | "
            f"**unresolved**: {mermaid_gate_result.total_unresolved}"
        )

    if triage_items:
        md_lines.append(
            f"\n## Fase 8 — Deep Audit Triage\n\n"
            f"{len(triage_items)} item(s) requerem intervenç\u00e3o manual."
        )
    (summary_dir / "remediation-report.md").write_text("\n".join(md_lines), encoding="utf-8")

    # Build the mermaid_gate section for the JSON (append-only — existing schema preserved)
    mermaid_gate_section: dict | None = None
    if mermaid_gate_result is not None:
        mermaid_gate_section = {
            "overall_status":   mermaid_gate_result.overall_status,
            "total_diagrams":   mermaid_gate_result.total_diagrams,
            "total_valid":      mermaid_gate_result.total_valid,
            "total_fixed":      mermaid_gate_result.total_fixed,
            "total_unresolved": mermaid_gate_result.total_unresolved,
            "generated_at":     mermaid_gate_result.generated_at,
        }

    json_payload: dict = {
        "project_name": project_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "synthesized_artifacts": synthesized,
        "ui_guard_findings": ui_guard_findings,
        **validation,
    }
    if mermaid_gate_section is not None:
        json_payload["mermaid_gate"] = mermaid_gate_section
    if triage_items:
        json_payload["deep_audit_triage"] = triage_items

    (summary_dir / "remediation-report.json").write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Post-pipeline repair for the AVA Fabric Summary HTML.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--language-target", choices=("en", "pt"), default="en")
    ap.add_argument(
        "--skip-mermaid-gate",
        action="store_true",
        default=False,
        help=(
            "Disable the Playwright Mermaid Validation & Auto-Fix Gate (Phase 3.5). "
            "No browser is launched; overall_status will be DISABLED. "
            "No WARNING is emitted — DISABLED is an intentional opt-out, not an error."
        ),
    )
    ap.add_argument(
        "--mermaid-guardrails-path",
        default=None,
        metavar="PATH",
        help=(
            "Override the path to mermaid-guardrails.md. "
            "Default: src/modules/ava-fabric-agents/shared/mermaid-guardrails.md."
        ),
    )
    ap.add_argument(
        "--mermaid-gate-max-attempts",
        type=int,
        default=3,
        metavar="N",
        help="Maximum probe→fix→re-probe cycles per failing diagram (default: 3).",
    )
    args = ap.parse_args()
    project_name = args.project

    log: list[str] = []
    ok, failures_before = phase0_audit(project_name, log, args.language_target)
    if not ok:
        print("\n".join(log))
        return 1

    synthesized = []
    synthesized.extend(phase1_artifact_resolution(project_name, log))
    synthesized.extend(phase2_diagram_synthesis(project_name, log))
    phase3_mermaid_sanitization(project_name, log)

    # Phase 3.5 — Playwright Mermaid Validation & Auto-Fix Gate
    mermaid_gate_result = phase35_playwright_gate(
        project_name,
        log,
        skip_mermaid_gate=args.skip_mermaid_gate,
        mermaid_guardrails_path=args.mermaid_guardrails_path,
        mermaid_gate_max_attempts=args.mermaid_gate_max_attempts,
    )

    phase4_security_reconciliation(project_name, log)

    ui_guard_findings = phase5_content_ui_guard_check(project_name, log)

    rebuilt = phase6_rebuild(
        project_name,
        log,
        skip_mermaid_gate=args.skip_mermaid_gate,
        mermaid_guardrails_path=args.mermaid_guardrails_path,
        mermaid_gate_max_attempts=args.mermaid_gate_max_attempts,
    )
    if rebuilt:
        ui_guard_findings = phase5_content_ui_guard_check(project_name, log)
        # I5 fix (Round 2 / Alternative 1): the Phase 3.5 gate result is now
        # STALE — build_summary_comprehensive.py's own Phase G already
        # re-ran the gate against the freshly rebuilt HTML and overwrote
        # mermaid-validation-report.json. Reload THAT result so
        # remediation-report.json's `mermaid_gate` section matches the
        # actually published artifact, not the pre-rebuild probe.
        fresh_result = _load_authoritative_gate_result(project_name)
        if fresh_result is not None:
            mermaid_gate_result = fresh_result
            log.append(
                f"ℹ️ Mermaid gate result atualizado pós-rebuild: "
                f"{fresh_result.overall_status} "
                f"({fresh_result.total_fixed} corrigido(s), "
                f"{fresh_result.total_unresolved} pendente(s))"
            )

    validation = phase7_revalidate(project_name, failures_before, log, args.language_target)
    # Phase 8 — Deep Audit Triage (spec 042): processes parser_gap / render_gap findings
    # from a prior --deep run. Guard in phase8_deep_audit_triage() ensures no crash
    # if deep-audit-report.json does not exist (returns [] silently).
    triage_items = phase8_deep_audit_triage(project_name, log)
    write_report(
        project_name, log, synthesized, ui_guard_findings, validation,
        mermaid_gate_result=mermaid_gate_result,
        triage_items=triage_items,
    )

    # Incorporate deep audit promotable status into the final exit decision.
    # deep-audit-report.json was written by phase7_revalidate (deep=True) or
    # by phase6_rebuild's builder subprocess — whichever ran last.
    deep_promotable = True
    deep_high_count = 0
    deep_audit_path = BASE_DIR / f"projects/{project_name}/outputs/summary/deep-audit-report.json"
    if deep_audit_path.exists():
        try:
            _da = json.loads(deep_audit_path.read_text(encoding="utf-8"))
            _summ = _da.get("summary", {})
            deep_high_count = _summ.get("critical", 0) + _summ.get("high", 0)
            deep_promotable = _summ.get("promotable", True)
        except Exception:
            pass

    has_errors = validation["errors_after"] > 0 or not deep_promotable

    print("\n".join(log))
    if not has_errors:
        print(
            f"\n✅ [ava-summary-remediation] Concluído — {len(validation['fixed'])} corrigidos, "
            f"{len(validation['remaining'])} pendentes (nenhuma error-level) — {project_name}"
        )
    else:
        # Garantia de credibilidade: nunca declarar sucesso com erros pendentes
        # (menus/diagramas ainda incorretos para o cliente final).
        reasons = []
        if validation["errors_after"] > 0:
            reasons.append(f"{validation['errors_after']} erro(s) padrão pendente(s)")
        if not deep_promotable:
            reasons.append(f"{deep_high_count} finding(s) CRITICAL/HIGH no deep audit")
        print(
            f"\n⚠️ [ava-summary-remediation] Concluído COM PENDÊNCIAS — "
            f"{len(validation['fixed'])} corrigidos — {project_name}"
        )
        print(f"   Razão: {'; '.join(reasons)}")
        if validation["remaining"]:
            print("   Pendências standard (revisar manualmente ou re-executar o agente upstream indicado):")
            for rid in validation["remaining"]:
                print(f"   - {rid}")
        if not deep_promotable:
            print(f"   Deep audit: {deep_high_count} HIGH/CRITICAL finding(s) — ver deep-audit-report.json")
    return 0 if not has_errors else 1


if __name__ == "__main__":
    sys.exit(main())
