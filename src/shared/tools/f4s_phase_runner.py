#!/usr/bin/env python3
"""F4S Phase Runner — git-backed, SpecKit-driven incremental codegen.

Entry: python src/shared/tools/f4s_phase_runner.py \
         --project-name <name> \
         --target-stack <stack> \
         [--dry-run]

Responsibilities:
  1. Discover features (scaffold first, then specs from F3S / traceability).
  2. git init/add/commit inside outputs/tobe/source-code/{component_type}.
  3. For each feature: run codegen agent, run build, remediate if needed
     (max 3 attempts), commit on success.
  4. Maintain GENERATION_LOG.md and .f4s/f4s-state.json.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Local helpers (function APIs)
import f4s_feature_discovery
from f4s_feature_discovery import discover_features
from f4s_generation_log import init_log, append_log, load_state, save_state
from f4s_git_helper import (
    git_init,
    git_add_all,
    git_commit,
    git_status_is_clean,
)
from f4s_tree_snapshot import snapshot
from scaffold_frontmatter import FrontMatterError, scaffold_definition_for_stack
from scaffold_paths import (COMPONENT_TYPES, component_type_for_stack,
                            resolve_source_code_path)
from scaffold_state import is_approved, load_state as load_task_state
from f4s_build_runner import run_build

# Reuse BYOK environment builder from agent_runner.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from agent_runner import build_child_env, PROVIDER_MODEL_ID  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_ROOT = REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
OUTPUTS_ROOT = REPO_ROOT / "projects"
SCAFFOLDS_DIR = MODULE_ROOT / "tech-stack" / "scaffolds"


def _ensure_directory(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _run_scaffold_path_check(
    project_name: str, tobe_outputs: Path, target_stack: str
) -> dict[str, Any]:
    """Run deterministic scaffold output-path guardrail.

    Detects code written outside the canonical ``source-code/frontend/`` or
    ``source-code/backend/`` locations (e.g. ``source-code/angular/`` or
    ``source-code/<name>-spa/``). O diretório vem da responsabilidade
    arquitetural do componente, nunca da tecnologia.
    """
    result: dict[str, Any] = {
        "passed": True,
        "violations": [],
        "error": None,
    }
    script_path = REPO_ROOT / "src" / "shared" / "utils" / "verify_scaffold_paths.py"
    if not script_path.is_file():
        result["passed"] = False
        result["error"] = f"Script not found: {script_path}"
        return result

    # Só os dois diretórios canônicos são aceitos. Antes a lista incluía o nome
    # da própria stack (`angular`, `dotnet`), então o guardrail que existe para
    # impedir caminho por tecnologia aprovava exatamente esse caminho.
    allowed_stacks = set(COMPONENT_TYPES)
    cmd = [
        sys.executable,
        str(script_path),
        "--project",
        project_name,
        "--workspace",
        str(REPO_ROOT),
        "--allowed-stacks",
        ",".join(sorted(allowed_stacks)),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}

    result["violations"] = payload.get("violations", [])
    if proc.returncode != 0 or result["violations"]:
        result["passed"] = False
        result["error"] = "; ".join(
            f"{v['type']}: {v['path']} ({v['reason']})"
            for v in result["violations"]
        )
    return result


_UTILS_DIR = REPO_ROOT / "src" / "shared" / "utils"


def _stack_check_scripts(repo_root: Path, target_stack: str) -> list[tuple[str, Path, list[str]]]:
    """Verificadores determinísticos por stack, executados antes do build.

    Cada entrada é (nome, script, argumentos). Stack sem entradas passa direto —
    o gate é aditivo, nunca bloqueia uma stack que ainda não tem verificador.

    O gate é deliberadamente barato: confere *estrutura*, não compila. Para Angular,
    a compilação de verdade é feita por `verify_angular_app.py`, invocado como o
    próprio comando de build (ver `f4s_build_runner.STACK_VERIFIERS`) — rodá-lo aqui
    também significaria dois `npm ci` + dois `ng build` por feature.
    """
    if target_stack == "dotnet":
        return [
            ("scaffold-manifest-dotnet", _UTILS_DIR / "verify_scaffold.py",
             ["--manifest", "dotnet", "--root", str(repo_root)]),
            ("nuget-duplicate", _UTILS_DIR / "verify_nuget_packages.py",
             ["--root", str(repo_root)]),
            ("cpm-consistency", _UTILS_DIR / "verify_cpm_consistency.py",
             ["--root", str(repo_root)]),
        ]
    if target_stack in {"angular", "react", "blazor"}:
        return [
            (f"scaffold-manifest-{target_stack}", _UTILS_DIR / "verify_scaffold.py",
             ["--manifest", target_stack, "--root", str(repo_root)]),
        ]
    return []


def _run_stack_checks(repo_root: Path, target_stack: str) -> dict[str, Any]:
    """Run deterministic per-stack structural checks before building.

    Returns a dict with keys:
      - passed: bool
      - checks: list of {name, status, details}
      - error: optional error message
    """
    result: dict[str, Any] = {
        "passed": True,
        "checks": [],
        "error": None,
    }
    check_scripts = _stack_check_scripts(repo_root, target_stack)
    if not check_scripts:
        return result

    for check_name, script_path, script_args in check_scripts:
        check_result = {"name": check_name, "status": "PASS", "details": None}
        if not script_path.is_file():
            check_result["status"] = "ERROR"
            check_result["details"] = f"Script not found: {script_path}"
            result["checks"].append(check_result)
            result["passed"] = False
            continue

        cmd = [sys.executable, str(script_path), *script_args]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            payload = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}

        status = payload.get("status", "ERROR")
        if proc.returncode != 0 and status in ("FAIL", "ERROR"):
            check_result["status"] = status
            check_result["details"] = payload
            result["checks"].append(check_result)
            result["passed"] = False
        else:
            check_result["status"] = status
            check_result["details"] = payload
            result["checks"].append(check_result)

    if not result["passed"]:
        messages = []
        for check in result["checks"]:
            if check["status"] in ("FAIL", "ERROR"):
                details = check.get("details") or {}
                if check["name"] == "nuget-duplicate":
                    duplicates = details.get("duplicates", [])
                    messages.append(
                        f"NuGet duplicate PackageReference: {duplicates}"
                    )
                elif check["name"] == "cpm-consistency":
                    missing = details.get("missing_versions", [])
                    messages.append(
                        f"CPM missing PackageVersion: {missing}"
                    )
                elif check["name"].startswith("scaffold-manifest-"):
                    missing = details.get("missing", [])
                    messages.append(
                        f"Scaffold incompleto — arquivos obrigatórios ausentes: {missing}"
                    )
                else:
                    messages.append(f"{check['name']}: {details}")
        result["error"] = "; ".join(messages)

    return result


#: Onde existe um generator declarado no front-matter, a estrutura base deixa de
#: ser escrita por um agente LLM a partir de prosa e passa a ser renderizada de
#: templates versionados. O agente segue responsável pelas features de cada
#: bounded context — mas só depois que o scaffold passou no gate de compilação.
#:
#: Não existe mais mapa stack→generator em código: a fonte é
#: `src/modules/ava-fabric-agents/tech-stack/scaffolds/{stack}-scaffold.md`.


def _bootstrap_stack_scaffold(repo_root: Path, project_name: str,
                              target_stack: str, *,
                              component_type: str = "") -> dict[str, Any]:
    """Gera o scaffold determinístico da stack e o valida ANTES do commit inicial.

    Ordem importa: até a spec 042 o commit inicial acontecia num diretório vazio,
    então o repositório nunca teve um ponto de retorno que compilasse. Agora o commit
    só ocorre depois de `generated` e `verified`.

    Devolve {"applicable", "generated", "verified", "error", "files_written"}.
    Stack sem gerador devolve applicable=False e a esteira segue como antes.
    """
    outcome: dict[str, Any] = {
        "applicable": False,
        "generated": False,
        "verified": False,
        "error": None,
        "files_written": 0,
    }
    # generator/verifier vêm do front-matter do `{stack}-scaffold.md`, validado
    # por allowlist. O dicionário fixo STACK_SCAFFOLD_GENERATORS foi removido:
    # declarar `generator:` no Markdown e resolvê-lo por dict em Python fazia a
    # configuração parecer a fonte da verdade sem ser (o Angular declarava
    # generator E verifier desde a spec 042, e nada os lia).
    try:
        definition = scaffold_definition_for_stack(target_stack, SCAFFOLDS_DIR,
                                                   repo_root=REPO_ROOT)
    except FrontMatterError as exc:
        outcome["error"] = str(exc)
        return outcome
    generator = Path(definition.generator)
    outcome["applicable"] = True

    if not generator.is_file():
        outcome["error"] = f"gerador ausente: {generator}"
        return outcome

    gen = subprocess.run(
        [sys.executable, str(generator), "--project", project_name,
         "--workspace", str(OUTPUTS_ROOT.parent),
         "--output-path", str(repo_root), "--json"],
        capture_output=True, text=True, check=False,
    )
    try:
        gen_payload = json.loads(gen.stdout) if gen.stdout.strip() else {}
    except json.JSONDecodeError:
        gen_payload = {"raw_stdout": gen.stdout, "raw_stderr": gen.stderr}

    if gen.returncode != 0 or gen_payload.get("status") != "PASS":
        outcome["error"] = (
            f"geração do scaffold {target_stack} falhou: "
            f"{gen_payload.get('error') or gen.stderr.strip()}"
        )
        return outcome

    outcome["generated"] = True
    outcome["files_written"] = len(gen_payload.get("files_written", []))

    verifier = Path(definition.verifier)
    if not verifier.is_file():
        # Sem verificador, geramos mas não afirmamos que compila.
        outcome["error"] = f"verificador ausente: {verifier}"
        return outcome

    ver = subprocess.run(
        [sys.executable, str(verifier), "--root", str(repo_root), "--json", "--quiet"],
        capture_output=True, text=True, check=False,
    )
    try:
        ver_payload = json.loads(ver.stdout) if ver.stdout.strip() else {}
    except json.JSONDecodeError:
        ver_payload = {"raw_stdout": ver.stdout, "raw_stderr": ver.stderr}

    if ver.returncode != 0 or ver_payload.get("status") != "PASS":
        outcome["error"] = (
            f"scaffold {target_stack} gerado mas não validado: "
            f"{ver_payload.get('error') or ver.stderr.strip()}"
        )
        return outcome

    outcome["verified"] = True
    return outcome


def _build_envelope(feature: dict[str, Any], project_name: str,
                    target_stack: str, repo_root: Path,
                    constitution_path: Path | None,
                    tree_snapshot_path: Path,
                    remediation_context: str | None) -> str:
    """Constrói o envelope textual para o Copilot CLI executar o codegen."""
    feature_id = feature["id"]
    lines = [
        f"Execute o agente `ava-f4s-codegen-agent` para a feature `{feature_id}`.",
        "",
        "1. Leia a spec do agente em "
        f"`src/modules/ava-fabric-agents/tech-stack/agents/f4s-codegen-agent.md` "
        "e siga os Execution Steps literalmente.",
        "",
        "2. Variáveis de contexto (também disponíveis em variáveis de ambiente F4S_*):",
        f"     project_name    = {project_name}",
        f"     target_stack    = {target_stack}",
        f"     feature_id      = {feature_id}",
        f"     feature_name    = {feature.get('name', feature_id)}",
        f"     repo_root       = {repo_root.as_posix()}",
        f"     spec_path       = {feature.get('spec_path')}",
        f"     plan_path       = {feature.get('plan_path') or '(nenhum)'}",
        f"     tasks_path      = {feature.get('tasks_path') or '(nenhum)'}",
        f"     tree_snapshot   = {tree_snapshot_path.as_posix()}",
        f"     constitution    = {constitution_path.as_posix() if constitution_path and constitution_path.exists() else '(nenhum)'}",
        "",
        "3. Regras de integridade:",
        "   - Nunca escreva fora de `repo_root`.",
        "   - Preserve código de features anteriores.",
        "   - Crie o arquivo sentinel `.f4s/{feature_id}.done` ao concluir.",
        "",
    ]
    if remediation_context:
        lines.extend([
            "4. CONTEXTO DE REMEDIAÇÃO — o build anterior falhou. Corrija os erros "
            "abaixo sem alterar o escopo da feature:",
            "```",
            remediation_context,
            "```",
            "",
        ])
    return "\n".join(lines)


def _run_copilot_codegen(
    feature: dict[str, Any],
    project_name: str,
    target_stack: str,
    repo_root: Path,
    constitution_path: Path | None,
    tree_snapshot_path: Path,
    remediation_context: str | None,
    dry_run: bool,
) -> bool:
    """Invoca o Copilot CLI diretamente com o agente F4S.

    Em dry-run apenas imprime o que seria executado.
    """
    feature_id = feature["id"]
    agent_id = "ava-f4s-codegen-agent"
    envelope = _build_envelope(
        feature, project_name, target_stack, repo_root,
        constitution_path, tree_snapshot_path, remediation_context,
    )

    if dry_run:
        print(f"[DRY-RUN] copilot codegen feature={feature_id}")
        print(f"  envelope={len(envelope)} chars")
        return True

    env, route = build_child_env(via_proxy=False)
    env["F4S_PROJECT_NAME"] = project_name
    env["F4S_TARGET_STACK"] = target_stack
    env["F4S_FEATURE_ID"] = feature_id
    env["F4S_FEATURE_NAME"] = feature.get("name", feature_id)
    env["F4S_REPO_ROOT"] = str(repo_root)
    env["F4S_SPEC_PATH"] = feature.get("spec_path") or ""
    env["F4S_PLAN_PATH"] = feature.get("plan_path") or ""
    env["F4S_TASKS_PATH"] = feature.get("tasks_path") or ""
    env["F4S_SENTINEL_PATH"] = str(repo_root / ".f4s" / f"{feature_id}.done")
    if constitution_path and constitution_path.exists():
        env["F4S_CONSTITUTION_PATH"] = str(constitution_path)
    env["F4S_TREE_SNAPSHOT_PATH"] = str(tree_snapshot_path)
    if remediation_context:
        env["F4S_REMEDIATION_CONTEXT"] = remediation_context

    session_id = str(uuid.uuid4())
    log_dir = repo_root / ".f4s" / "logs" / feature_id
    transcript = repo_root / ".f4s" / "transcripts" / f"{feature_id}.md"
    _ensure_directory(log_dir)
    _ensure_directory(transcript.parent)

    argv = [
        "copilot",
        "-p", envelope,
        "--agent", agent_id,
        "-C", str(REPO_ROOT),
        "--model", PROVIDER_MODEL_ID,
        "--allow-all-tools",
        "--no-ask-user",
        "--no-custom-instructions",
        "--disable-builtin-mcps",
        "--excluded-tools=skill,task",
        "--output-format", "json",
        "--session-id", session_id,
        "--log-level", "error",
        "--log-dir", str(log_dir),
        "--share", str(transcript),
        "--secret-env-vars=COPILOT_PROVIDER_BEARER_TOKEN",
        "--no-auto-update",
        "--no-remote", "--no-remote-export",
    ]

    print(f"[RUN] copilot codegen feature={feature_id} route={route}")
    start = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            check=False,
        )
    except FileNotFoundError:
        print("[ERROR] comando 'copilot' não encontrado no PATH", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print(f"[ERROR] codegen timeout para feature={feature_id}", file=sys.stderr)
        return False

    duration = int((time.monotonic() - start) * 1000)
    (log_dir / "stdout.jsonl").write_text(result.stdout or "", encoding="utf-8")
    if result.stderr:
        (log_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    sentinel_path = repo_root / ".f4s" / f"{feature_id}.done"
    success = result.returncode == 0 and sentinel_path.exists()
    print(
        f"[DONE] feature={feature_id} exit={result.returncode} "
        f"sentinel={sentinel_path.exists()} duration={duration}ms"
    )
    return success


def _resolve_scaffold_spec(target_stack: str) -> Path:
    """Retorna o scaffold específico da stack ou o fallback genérico."""
    specific = SCAFFOLDS_DIR / f"{target_stack}-scaffold.md"
    return specific if specific.exists() else SCAFFOLDS_DIR / "default-scaffold.md"


def _prepare_feature_spec(
    target_stack: str,
    feature: dict[str, Any],
    dry_run: bool,
) -> bool:
    """Garante que `feature` tenha `spec_path` resolvido.

    Para 000-scaffold usa o scaffold da stack. Para demais, espera que F3S já
    tenha gerado spec/plan/tasks em `outputs/tobe/speckit/specs/{feature_id}/`.
    """
    feature_id = feature["id"]
    if feature_id == "000-scaffold":
        feature["spec_path"] = str(_resolve_scaffold_spec(target_stack).as_posix())
        feature.setdefault("plan_path", None)
        feature.setdefault("tasks_path", None)
        return True

    if dry_run:
        print(f"[DRY-RUN] prepare feature={feature_id}")
        return True

    spec_path = feature.get("spec_path")
    if not spec_path or not Path(spec_path).exists():
        print(
            f"[WARN] spec ausente para feature={feature_id}: {spec_path}. "
            "Certifique-se de que o F3S gerou os specs antes de executar F4S.",
            file=sys.stderr,
        )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run F4S codegen phase.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--target-stack", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    project_name: str = args.project_name
    target_stack: str = args.target_stack
    dry_run: bool = args.dry_run

    # ── Gate de aprovação (RF-001) ──────────────────────────────────────────
    # Este runner despacha o `ava-f4s-codegen-agent`, que escreve código de
    # feature. Nada disso pode acontecer antes de o baseline ter sido gerado,
    # compilado e APROVADO explicitamente. Ausência de decisão é bloqueio, não
    # permissão — e a verificação vive aqui, no código, e não numa instrução de
    # prompt que o modelo pode ignorar.
    if not dry_run:
        estado = load_task_state(OUTPUTS_ROOT / project_name, project_name)
        if not is_approved(estado):
            situacao = (estado.get("approval") or {}).get("status") or "não iniciado"
            print(
                "\n[F4S] BLOQUEADO — o baseline de scaffold não está aprovado.\n"
                f"  Estado do gate: {situacao}\n"
                "  Nenhum agente coder será executado.\n\n"
                "  Como destravar:\n"
                f"    python src/shared/tools/scaffold_runner.py "
                f"--project {project_name}\n"
                f"    python src/shared/tools/scaffold_runner.py "
                f"--project {project_name} --approve\n",
                file=sys.stderr,
            )
            return 3

    project_outputs = OUTPUTS_ROOT / project_name / "outputs"
    tobe_outputs = project_outputs / "tobe"
    # O repo de código é resolvido pela RESPONSABILIDADE do componente, não pela
    # stack: `source-code/frontend` ou `source-code/backend`. Era
    # `source-code/{target_stack}`, a segunda convenção viva no repo — a mesma
    # que fazia o ava-stack-orchestrator e este runner gravarem em lugares
    # diferentes para o mesmo projeto.
    component_type = component_type_for_stack(target_stack)
    repo_root = tobe_outputs / resolve_source_code_path(component_type)
    speckit_root = tobe_outputs / "speckit"
    constitution_path = speckit_root / "constitution.md"
    context_dir = repo_root / ".f4s"
    config_path = OUTPUTS_ROOT / project_name / "context" / "project-config.yaml"

    _ensure_directory(repo_root)
    _ensure_directory(context_dir)

    if not (repo_root / "GENERATION_LOG.md").exists():
        init_log(repo_root)

    if not dry_run:
        git_init(repo_root)

        # Spec 042 — ensure_repo -> gerar -> validar -> commit.
        # O commit inicial só acontece depois de o scaffold ser gerado E validado,
        # para que o primeiro ponto de retorno do repositório seja uma estrutura
        # comprovadamente compilando.
        bootstrap = _bootstrap_stack_scaffold(repo_root, project_name, target_stack,
                                              component_type=component_type)
        if bootstrap["applicable"]:
            if bootstrap["verified"]:
                commit_msg = (
                    f"feat(scaffold): {target_stack} workspace compilando e validado"
                )
                print(f"[SCAFFOLD] {target_stack}: "
                      f"{bootstrap['files_written']} arquivos gerados e validados")
            else:
                # Sem veredito de compilação não afirmamos que compila: registramos a
                # falha e deixamos a feature 000-scaffold tentar remediar. Nada de
                # commit alegando algo que não foi verificado.
                commit_msg = None
                print(f"[SCAFFOLD] {target_stack}: FALHA — {bootstrap['error']}")
                append_log(
                    repo_root,
                    spec="(f4s-scaffold-bootstrap)",
                    attempt=0,
                    build_command="scaffold-bootstrap",
                    exit_code=1,
                    notes=f"Scaffold determinístico não validado: {bootstrap['error']}",
                )
        else:
            commit_msg = "chore(f4s): initial commit"

        if commit_msg and not git_status_is_clean(repo_root, cached=False):
            git_add_all(repo_root)
            git_commit(repo_root, commit_msg)

    append_log(
        repo_root,
        spec="(f4s-start)",
        attempt=0,
        build_command="-",
        exit_code=0,
        notes=f"F4S started project={project_name} stack={target_stack} dry_run={dry_run}",
    )

    features = discover_features(
        stack=target_stack,
        tobe_outputs=tobe_outputs,
        project_config_path=config_path,
    )

    if not features:
        append_log(
            repo_root,
            spec="(f4s-error)",
            attempt=0,
            build_command="-",
            exit_code=-1,
            notes="No features discovered. Aborting F4S.",
        )
        return 1

    print(f"[F4S] Discovered {len(features)} features for {target_stack}:")
    for f in features:
        print(f"  - {f['id']}: {f.get('name', '')}")

    state = load_state(repo_root)
    state["initialized"] = True
    state["target_stack"] = target_stack
    state["features"] = [f["id"] for f in features]
    save_state(repo_root, state)

    for feature in features:
        feature_id = feature["id"]
        sentinel_path = context_dir / f"{feature_id}.done"

        if sentinel_path.exists() and not dry_run:
            append_log(
                repo_root,
                spec=feature_id,
                attempt=0,
                build_command="-",
                exit_code=0,
                notes="Feature already completed; skipping.",
            )
            continue

        _prepare_feature_spec(target_stack, feature, dry_run)

        snapshot_md = context_dir / "snapshots" / f"{feature_id}-tree.md"
        snapshot_json = context_dir / "snapshots" / f"{feature_id}-tree.json"
        _ensure_directory(snapshot_md.parent)
        snapshot(repo_root, output_md=snapshot_md, output_json=snapshot_json)

        remediation_context: str | None = None
        success = False
        max_attempts = 3
        commit_hash = "-"
        for attempt in range(1, max_attempts + 1):
            append_log(
                repo_root,
                spec=feature_id,
                attempt=attempt,
                build_command="-",
                exit_code=0,
                notes=f"codegen attempt {attempt}/{max_attempts}",
            )

            ok = _run_copilot_codegen(
                feature=feature,
                project_name=project_name,
                target_stack=target_stack,
                repo_root=repo_root,
                constitution_path=constitution_path,
                tree_snapshot_path=snapshot_md,
                remediation_context=remediation_context,
                dry_run=dry_run,
            )

            if not ok:
                append_log(
                    repo_root,
                    spec=feature_id,
                    attempt=attempt,
                    build_command="copilot",
                    exit_code=-1,
                    notes="Codegen agent failed (no sentinel).",
                )
                break

            if dry_run:
                append_log(
                    repo_root,
                    spec=feature_id,
                    attempt=attempt,
                    build_command="-",
                    exit_code=0,
                    notes="dry-run: build and commit skipped",
                )
                success = True
                break

            path_check = _run_scaffold_path_check(project_name, tobe_outputs, target_stack)
            if not path_check["passed"]:
                append_log(
                    repo_root,
                    spec=feature_id,
                    attempt=attempt,
                    build_command="scaffold-path-check",
                    exit_code=1,
                    notes=f"Deterministic scaffold path check failed: {path_check['error']}",
                )
                remediation_context = (
                    "Deterministic scaffold output-path check failed. "
                    "Generated code was written outside the canonical "
                    f"`source-code/{target_stack}/` location:\n"
                    f"{path_check['error']}"
                )
                print(f"[REMEDIATE] feature={feature_id} attempt={attempt} scaffold-path-check")
                continue

            stack_check = _run_stack_checks(repo_root, target_stack)
            if not stack_check["passed"]:
                append_log(
                    repo_root,
                    spec=feature_id,
                    attempt=attempt,
                    build_command="stack-check",
                    exit_code=1,
                    notes=f"Deterministic {target_stack} check failed: {stack_check['error']}",
                )
                remediation_context = (
                    f"Deterministic {target_stack} structural check failed. "
                    "Fix it before retrying the build:\n"
                    f"{stack_check['error']}"
                )
                print(f"[REMEDIATE] feature={feature_id} attempt={attempt} stack-check")
                continue

            build_result = run_build(
                repo_root=repo_root,
                stack=target_stack,
                command_override=None,
                timeout=600,
            )
            append_log(
                repo_root,
                spec=feature_id,
                attempt=attempt,
                build_command=build_result["command"],
                exit_code=build_result["exit_code"],
                notes=(
                    f"build timeout={build_result['timed_out']}; "
                    f"stderr_tail={build_result['stderr'][-200:]}"
                ),
            )

            if build_result["exit_code"] == 0:
                success = True
                break

            remediation_context = (
                f"Build failed (exit_code={build_result['exit_code']}, "
                f"timed_out={build_result['timed_out']}).\n"
                f"Command: {build_result['command']}\n"
                f"STDERR:\n{build_result['stderr'][-4000:]}\n"
                f"STDOUT:\n{build_result['stdout'][-2000:]}"
            )
            print(f"[REMEDIATE] feature={feature_id} attempt={attempt}")

        if dry_run:
            continue

        if success:
            git_add_all(repo_root)
            commit_msg = f"feat(f4s): {feature_id} — {feature.get('name', feature_id)}"
            commit_hash = git_commit(repo_root, commit_msg) or "-"
            append_log(
                repo_root,
                spec=feature_id,
                attempt=0,
                build_command="-",
                exit_code=0,
                notes=f"committed {commit_hash}",
            )
            state = load_state(repo_root)
            state["last_commit"] = commit_hash
            state["last_feature"] = feature_id
            save_state(repo_root, state)
        else:
            append_log(
                repo_root,
                spec=feature_id,
                attempt=0,
                build_command="-",
                exit_code=-1,
                notes=f"Feature failed after {max_attempts} attempts.",
            )
            state = load_state(repo_root)
            state["failed_feature"] = feature_id
            save_state(repo_root, state)
            return 1

    append_log(
        repo_root,
        spec="(f4s-done)",
        attempt=0,
        build_command="-",
        exit_code=0,
        notes="F4S completed successfully.",
    )
    state = load_state(repo_root)
    state["completed"] = True
    save_state(repo_root, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
