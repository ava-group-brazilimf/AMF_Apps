"""
src.shared.checks
=================
Unified check framework for AVA Fabric HTML + Mermaid outputs.

Usage (programmatic):
    from src.shared.checks import run_checks
    ok = run_checks("Meu-ERP", suite="all")

Usage (CLI):
    python -m src.shared.checks --project Meu-ERP [--suite html|mmd|nav|all] [--verbose]
"""
from pathlib import Path

from .context import CheckContext
from .reporter import Reporter
from .suites.artifact_size import ArtifactSizeSuite
from .suites.html_data import HtmlDataSuite
from .suites.mermaid_files import MermaidFilesSuite
from .suites.mermaid_runtime import MermaidRuntimeSuite
from .suites.phase_status import PhaseStatusSuite
from .suites.pipeline_consistency import PipelineConsistencySuite
from .suites.sidebar_nav import SidebarNavSuite
from .suites.tobe_db_policy import TobeDbPolicySuite
from .suites.tobe_db_type_target import TobeDbTypeTargetSuite
from .suites.gherkin_features import GherkinFeaturesSuite
from .suites.ftm_traceability import FtmTraceabilitySuite
from .suites.evidence_capture import EvidenceCaptureSuite
from .suites.speckit_traceability import SpeckitTraceabilitySuite
from .suites.prototype_coverage import PrototypeCoverageSuite
from .suites.speckit_frontend_integration import SpeckitFrontendIntegrationSuite

_SUITES = {
    "artifact_size": ArtifactSizeSuite,
    "html": HtmlDataSuite,
    "mmd": MermaidFilesSuite,
    "mermaid_runtime": MermaidRuntimeSuite,
    "nav": SidebarNavSuite,
    "phase_status": PhaseStatusSuite,
    "pipeline_consistency": PipelineConsistencySuite,
    "tobe_db_policy": TobeDbPolicySuite,
    "tobe_db_type_target": TobeDbTypeTargetSuite,
    "gherkin": GherkinFeaturesSuite,
    "ftm_traceability": FtmTraceabilitySuite,
    "evidence_capture": EvidenceCaptureSuite,
    # spec 039 — gates da camada de planejamento SpecKit (F3S)
    "speckit_traceability": SpeckitTraceabilitySuite,
    "prototype_coverage": PrototypeCoverageSuite,
    # Cobertura protótipo → tarefas → API → integração → e2e. Distinta de
    # prototype_coverage: aquela valida a SPEC, esta valida o PLANO.
    "speckit_frontend_integration": SpeckitFrontendIntegrationSuite,
}


def run_checks(project: str, suite: str = "all", verbose: bool = False,
              json_out: "str | None" = None) -> bool:
    """Run the requested suite(s) for *project* and return whether they passed."""
    return run_checks_detailed(
        project, suite=suite, verbose=verbose, json_out=json_out
    ).all_passed


def run_checks_detailed(project: str, suite: str = "all", verbose: bool = False,
                        json_out: "str | None" = None) -> Reporter:
    """Run the requested suite(s) for *project* and return the reporter.

    `json_out`, when given, persists the same results to disk (see
    `Reporter.write_json`) so a downstream agent or gate can consume them —
    the CLI alone only ever printed to stdout.
    """
    ctx = CheckContext(project)
    reporter = Reporter(verbose=verbose)

    suites_to_run = list(_SUITES.values()) if suite == "all" else [_SUITES[suite]]

    for Suite in suites_to_run:
        s = Suite(ctx)
        s.run(reporter)

    reporter.print_summary()
    if json_out:
        # Caminho relativo resolve contra o PROJETO, não contra o CWD do
        # processo. O DAG passa `outputs/tobe/speckit/checks-report.json`; com
        # `Path(json_out)` cru o arquivo era gravado na raiz do repositório e o
        # input advisory da wave6 nunca era encontrado (medido em nopcommerce-04,
        # 2026-08-21). Caminho absoluto continua sendo respeitado como veio.
        target = Path(json_out)
        if not target.is_absolute():
            target = ctx.project_dir / target
        reporter.write_json(target)
    return reporter
