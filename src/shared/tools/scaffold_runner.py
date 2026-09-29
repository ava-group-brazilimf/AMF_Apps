#!/usr/bin/env python3
"""Fluxo único e determinístico da fase de scaffold.

Substitui os DOIS caminhos que coexistiam: o `ava-stack-orchestrator`
despachando agentes coder que escreviam a estrutura por prosa em
`source-code/backend|frontend`, e o `f4s_phase_runner.py` — mais maduro, com
git incremental e validação — que gravava em `source-code/{stack}` e não era
chamado por DAG nenhum. Um projeto podia acabar com código nos dois lugares e
nenhum verificador olhava os dois.

Ordem obrigatória, codificada aqui e não interpretada por LLM:

    frontend scaffold → frontend verify → backend scaffold → backend verify
    → git baseline → gate humano → agentes coder

Invariantes que o código garante:
  - o destino sai de `scaffold_paths`, nunca da stack e nunca do front-matter;
  - generator e verifier saem do front-matter, validados por allowlist;
  - falha do frontend impede o backend (não adianta compilar metade);
  - nenhum commit acontece antes de os dois compilarem;
  - sem aprovação explícita registrada, coder algum roda.

Uso:
    python src/shared/tools/scaffold_runner.py --project meu-erp-03 --json
    python src/shared/tools/scaffold_runner.py --project meu-erp-03 --approve
    python src/shared/tools/scaffold_runner.py --project meu-erp-03 --reject
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

import proc_stream  # noqa: E402
import scaffold_readme  # noqa: E402
from scaffold_approval import (  # noqa: E402
    DEFAULT_APPROVAL_TIMEOUT_S,
    OVERRIDE_CONTINUED,
    build_summary,
    request_approval,
    request_failure_override,
)
from scaffold_frontmatter import (  # noqa: E402
    FrontMatterError,
    ScaffoldDefinition,
    scaffold_definition_for_stack,
)
from scaffold_paths import (  # noqa: E402
    COMPONENT_TYPES,
    ScaffoldPathError,
    detect_legacy_output_dirs,
    files_outside_canonical,
    resolve_output_dir,
    resolve_source_code_path,
)
from scaffold_state import (  # noqa: E402
    APPROVED,
    StateError,
    AWAITING_USER_APPROVAL,
    COMPLETED,
    FAILED,
    GENERATED,
    REJECTED,
    RUNNING,
    VERIFYING,
    blocked_by_gate,
    is_approved,
    load_state,
    save_state,
    scaffold_task,
    set_approval,
    task_is_reusable,
    update_scaffold_task,
)

SCAFFOLDS_DIR = (REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
                 / "tech-stack" / "scaffolds")

#: Teto de tentativas por componente (generator + verifier). Depois disso a
#: falha é controlada: não avança para o gate e não chama coder.
MAX_ATTEMPTS = 3

#: Teto por INVOCAÇÃO (generator, depois verifier). Tem de caber dentro do
#: `timeout_s` do nó F4S no DAG — hoje 3600s. Enquanto foi maior que o teto do
#: passo (1800 contra 900), o `except TimeoutExpired` logo abaixo nunca chegou a
#: rodar: o pai era morto primeiro e a tarefa ficava presa em `running`, sem
#: veredito e sem log. Ver `pipeline_plan.DEFAULT_TOOL_TIMEOUT_S`.
DEFAULT_TIMEOUT = 1800

RESET, BOLD, GREEN, YELLOW, RED, CYAN, DIM = (
    "\033[0m", "\033[1m", "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[2m")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _rel(caminho: Path | str) -> str:
    """Caminho relativo ao repo quando possível; absoluto quando não.

    Um scaffold pode viver fora da árvore do repo (bancada de teste, workspace
    montado). `relative_to` cru estourava ValueError e derrubava a fase por um
    detalhe de apresentação.
    """
    alvo = Path(caminho)
    try:
        return alvo.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return alvo.as_posix()


class ScaffoldRunnerError(RuntimeError):
    """Falha de configuração da fase — sempre antes de escrever arquivo."""


# ── Configuração ───────────────────────────────────────────────────────────

def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ScaffoldRunnerError("pyyaml não está instalado")
    if not path.is_file():
        raise ScaffoldRunnerError(f"arquivo ausente: {path}")
    dados = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dados if isinstance(dados, dict) else {}


def resolve_bounded_contexts(project_dir: Path) -> list[str]:
    """Bounded contexts do blueprint, resolvidos UMA vez para os dois generators.

    Os dois extratores nasceram separados e divergiram: o do Angular exige uma
    tabela sob o heading "Bounded Context Map" com a coluna "TO-BE Module"; o do
    .NET lê qualquer linha `| BC-01 | Nome |`. Num blueprint real isso significa
    o backend gerar cinco BCs e o frontend abortar por não achar nenhum — foi
    exatamente o que aconteceu.

    Resolver aqui e passar `--bcs` para ambos elimina a divergência: os dois
    componentes passam a modelar o mesmo domínio, por construção. Cada generator
    ainda normaliza o nome à sua convenção (kebab no Angular, Pascal no .NET).

    Devolve `[]` quando nada é reconhecido — aí cada generator tenta sozinho e
    reprova com a própria mensagem, que é mais específica.
    """
    import f4s_angular_scaffold as angular
    import f4s_dotnet_scaffold as dotnet

    candidatos = [
        project_dir / "outputs" / "tobe" / "docs" / "architecture-blueprint.md",
        project_dir / "outputs" / "tobe" / "architecture-blueprint.md",
        project_dir / "outputs" / "tobe" / "docs" / "bounded-context-map.md",
    ]
    for caminho in candidatos:
        if not caminho.is_file():
            continue
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        project_match = re.search(r"\*\*Project\*\*:\s*([^|*\r\n]+)", texto,
                                  re.IGNORECASE)
        if project_match:
            artifact_project = project_match.group(1).strip()
            if artifact_project.casefold() != project_dir.name.casefold():
                raise ScaffoldRunnerError(
                    f"{_rel(caminho)} declara Project '{artifact_project}', mas a "
                    f"execução é do projeto '{project_dir.name}'. Regere a F2 para "
                    "evitar usar artefatos de outro projeto.")
        for extrair in (angular.extract_bcs, dotnet.extract_bcs):
            try:
                achados = [item for item in extrair(texto) if item]
            except Exception:  # noqa: BLE001 — extrator é heurística, não contrato
                continue
            if achados:
                return achados
    return []


def resolve_stacks(project_config: dict[str, Any]) -> dict[str, str]:
    """`{component_type: stack}` a partir de `tobe_stack`.

    A ordem do dicionário é a ordem de execução: frontend primeiro (RF-002).
    """
    tobe = project_config.get("tobe_stack") or {}
    stacks = {
        "frontend": str(tobe.get("frontend_framework") or "").strip().lower(),
        "backend": str(tobe.get("backend_framework") or "").strip().lower(),
    }
    faltando = [k for k, v in stacks.items() if not v]
    if faltando:
        raise ScaffoldRunnerError(
            "project-config.yaml → tobe_stack não declara "
            + " nem ".join(f"{k}_framework" for k in faltando)
            + ". A fase de scaffold não adivinha stack.")
    return {item: stacks[item] for item in COMPONENT_TYPES}


# ── Execução de generator e verifier ───────────────────────────────────────

def _echo(texto: str, cor: str = "") -> None:
    """Repassa a saída de uma tool filha para o console do runner, indentada.

    `capture_output=True` é necessário — o contrato do generator é devolver JSON
    no stdout, e ele precisa ser parseado. Mas capturar sem reemitir tornava o
    runner cego: o operador via `generator falhou: <200 primeiros chars>` e
    nada mais. Traceback, caminho do config lido, comando executado — tudo
    ficava dentro do processo filho e morria com ele. Reemitir aqui é o que faz
    a janela do pipeline_runner mostrar o que de fato aconteceu.
    """
    for linha in texto.rstrip().splitlines():
        print(f"    {cor}{linha}{RESET}" if cor else f"    {linha}")


def _run_json(script: Path, argv: list[str], timeout: int) -> dict[str, Any]:
    """Executa uma tool do repo e devolve seu JSON estruturado.

    Nunca via shell e nunca com string composta: o caminho vem de allowlist e
    os argumentos vão como argv.
    """
    comando = [sys.executable, str(script), *argv]
    print(f"  {DIM}$ {' '.join(comando)}{RESET}")
    sys.stdout.flush()
    try:
        # stdout é CONTRATO (o JSON) e continua capturado; stderr é log humano
        # — do generator, do verifier e do `dotnet` que eles disparam — e vai
        # para a tela enquanto acontece. Antes, um `dotnet build` de 10 minutos
        # era 10 minutos de console mudo, e o timeout descartava tudo.
        proc = proc_stream.run(comando, cwd=REPO_ROOT, timeout_s=timeout,
                               echo_stdout=False, echo_stderr=True,
                               prefix=f"    {DIM}│{RESET} ", stream=sys.stdout)
    except subprocess.TimeoutExpired:
        print(f"  {RED}timeout após {timeout}s{RESET}")
        return {"success": False, "status": "ERROR", "exit_code": 124,
                "errors": [{"code": "TIMEOUT", "message": f"excedeu {timeout}s"}],
                "warnings": [], "command": comando, "error": f"timeout após {timeout}s"}
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    # stdout que não é JSON é log humano ou traceback — nos dois casos é o que
    # o operador precisa ler. stdout que É JSON já vira o resumo impresso pelo
    # chamador; despejá-lo aqui só polui.
    if proc.stdout.strip() and not payload:
        _echo(proc.stdout)
    # stderr NÃO é reemitido aqui: já saiu ao vivo, linha a linha, durante a
    # execução. Reemitir agora só duplicaria o log inteiro na tela.
    if not payload:
        payload = {
            "success": proc.returncode == 0,
            "status": "PASS" if proc.returncode == 0 else "ERROR",
            "errors": [] if proc.returncode == 0 else [
                {"code": "TOOL001", "message": (proc.stderr or proc.stdout or "")[-800:]}],
            "warnings": [],
            "error": None if proc.returncode == 0 else (proc.stderr or "")[-800:],
        }
    payload.setdefault("success", payload.get("status") == "PASS")
    payload["exit_code"] = proc.returncode
    payload["command"] = comando
    return payload


def _generator_argv(definition: ScaffoldDefinition, project: str, workspace: Path,
                    output_dir: Path, bcs: str | None, force: bool) -> list[str]:
    """Argumentos do generator. O destino resolvido SEMPRE é passado."""
    argv = ["--project", project, "--workspace", str(workspace), "--json"]
    # Os dois generators nomeiam a flag de destino de formas diferentes por
    # história; ambos a validam contra o canônico.
    argv += (["--output-path", str(output_dir)]
             if definition.component_type == "backend"
             else ["--root", str(output_dir)])
    if bcs:
        argv += ["--bcs", bcs]
    if force:
        argv.append("--force")
    return argv


def _verifier_argv(definition: ScaffoldDefinition, output_dir: Path,
                   skip_build: bool) -> list[str]:
    argv = ["--root", str(output_dir), "--json"]
    if skip_build:
        # `verify_angular_app.py` não tem --skip-build; tem --skip-serve.
        argv.append("--skip-build" if definition.component_type == "backend"
                    else "--skip-serve")
    return argv


def run_component(project: str, project_dir: Path, workspace: Path,
                  state: dict[str, Any], *, component_type: str, stack: str,
                  bcs: str | None = None, force: bool = False,
                  skip_build: bool = False, timeout: int = DEFAULT_TIMEOUT,
                  reuse: bool = True) -> dict[str, Any]:
    """Gera e verifica um componente. Devolve o resultado estruturado."""
    tobe_root = project_dir / "outputs" / "tobe"
    definition = scaffold_definition_for_stack(stack, SCAFFOLDS_DIR, repo_root=REPO_ROOT)
    if definition.component_type != component_type:
        raise ScaffoldRunnerError(
            f"{definition.source_path.name} declara component_type="
            f"{definition.component_type}, mas a esteira o usa como "
            f"{component_type}")

    output_dir = resolve_output_dir(tobe_root, component_type)
    rel = resolve_source_code_path(component_type)

    if reuse and task_is_reusable(state, component_type, tobe_root):
        registro = scaffold_task(state, component_type) or {}
        print(f"  {DIM}[{component_type}] já concluído e presente em {rel}/ "
              f"— reaproveitado.{RESET}")
        return {"success": True, "reused": True, "component_type": component_type,
                "stack": stack, "output_path": rel, "task": registro,
                "errors": [], "warnings": []}

    comuns = {
        "stack": stack,
        "generator": _rel(definition.generator),
        "verifier": _rel(definition.verifier),
        "source_path": _rel(definition.source_path),
    }

    ultimo: dict[str, Any] = {}
    for tentativa in range(1, MAX_ATTEMPTS + 1):
        print(f"\n{CYAN}▶ [{component_type}/{stack}] tentativa {tentativa}/"
              f"{MAX_ATTEMPTS} → {rel}/{RESET}")
        update_scaffold_task(project_dir, state, component_type=component_type,
                            status=RUNNING, attempts=tentativa, **comuns)

        geracao = _run_json(
            Path(definition.generator),
            _generator_argv(definition, project, workspace, output_dir,
                            bcs, force or tentativa > 1),
            timeout)
        if not geracao.get("success"):
            ultimo = geracao
            resumo = geracao.get("error") or "generator falhou"
            print(f"  {RED}generator falhou: {str(resumo)[:200]}{RESET}")
            # `errors[]` carrega o diagnóstico estruturado (code + message) que
            # o `error` de uma linha resume. Sem imprimi-lo, o operador recebia
            # o sintoma truncado e nunca o código do erro.
            for item in geracao.get("errors") or []:
                if isinstance(item, dict):
                    codigo = str(item.get("code") or "").strip()
                    _echo(f"[{codigo}] {item.get('message', '')}" if codigo
                          else str(item.get("message", "")), RED)
                else:
                    _echo(str(item), RED)
            update_scaffold_task(project_dir, state, component_type=component_type,
                                 status=FAILED, attempts=tentativa,
                                 error_summary=str(resumo)[:2000],
                                 build_status="not_reached",
                                 verification_status="not_reached", **comuns)
            continue

        update_scaffold_task(project_dir, state, component_type=component_type,
                             status=GENERATED, attempts=tentativa,
                             evidence=[{"step": "generation",
                                        "files_written": len(geracao.get("files_written") or []),
                                        "files_skipped": len(geracao.get("files_skipped") or [])}],
                             **comuns)
        print(f"  {DIM}gerado: {len(geracao.get('files_written') or [])} arquivos "
              f"({len(geracao.get('files_skipped') or [])} preservados){RESET}")

        update_scaffold_task(project_dir, state, component_type=component_type,
                             status=VERIFYING, attempts=tentativa, **comuns)
        verificacao = _run_json(
            Path(definition.verifier),
            _verifier_argv(definition, output_dir, skip_build), timeout)
        ultimo = verificacao

        avisos = verificacao.get("warnings") or []
        if verificacao.get("success"):
            update_scaffold_task(
                project_dir, state, component_type=component_type, status=COMPLETED,
                attempts=tentativa,
                restore_status=verificacao.get("restore_status"),
                build_status=verificacao.get("build_status") or "succeeded",
                verification_status="succeeded",
                warning_count=len(avisos),
                error_summary=None,
                evidence=[{"step": "verification",
                           "exit_code": verificacao.get("exit_code"),
                           "warnings": len(avisos)}],
                **comuns)
            print(f"  {GREEN}verificado: build OK, {len(avisos)} warning(s){RESET}")
            return {"success": True, "reused": False, "component_type": component_type,
                    "stack": stack, "output_path": rel,
                    "generation": geracao, "verification": verificacao,
                    "errors": [], "warnings": avisos, "attempt": tentativa}

        erros = verificacao.get("errors") or []
        resumo = verificacao.get("error") or (erros[0].get("message") if erros else "verificação falhou")
        print(f"  {RED}verificação falhou: {str(resumo)[:200]}{RESET}")
        update_scaffold_task(
            project_dir, state, component_type=component_type, status=FAILED,
            attempts=tentativa,
            restore_status=verificacao.get("restore_status"),
            build_status=verificacao.get("build_status") or "failed",
            verification_status="failed",
            warning_count=len(avisos),
            error_summary=str(resumo)[:2000],
            evidence=[{"step": "verification", "exit_code": verificacao.get("exit_code"),
                       "errors": len(erros)}],
            **comuns)

    return {"success": False, "reused": False, "component_type": component_type,
            "stack": stack, "output_path": rel,
            "errors": ultimo.get("errors") or [],
            "warnings": ultimo.get("warnings") or [],
            "error": ultimo.get("error"),
            "attempt": MAX_ATTEMPTS}


# ── Baseline git ───────────────────────────────────────────────────────────

def create_baseline(project_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Commit do baseline em `source-code/`, com os DOIS componentes dentro.

    Antes cada stack tinha seu próprio repo (`source-code/{stack}/.git`), então
    não existia um commit que representasse "o sistema compila" — só "esta
    metade compila". Um repo em `source-code/` dá esse ponto de retorno.

    Repo já existente preserva histórico: `git init` só roda quando não há um.
    """
    import f4s_git_helper as git

    tobe_root = project_dir / "outputs" / "tobe"
    raiz = tobe_root / "source-code"
    resultado: dict[str, Any] = {"created": False, "commit_sha": None,
                                 "existing_repo": False, "error": None,
                                 "violations": []}

    faltando = [c for c in COMPONENT_TYPES
                if not (tobe_root / resolve_source_code_path(c)).is_dir()]
    if faltando:
        resultado["error"] = f"componentes ausentes em disco: {', '.join(faltando)}"
        return resultado

    intrusos = files_outside_canonical(tobe_root)
    if intrusos:
        # Commitar com `source-code/angular/` ao lado de `frontend/` congelaria
        # a duplicidade que esta mudança existe para eliminar.
        resultado["violations"] = intrusos
        resultado["error"] = (
            "existe código em diretório derivado de tecnologia: "
            + ", ".join(intrusos)
            + ". Migre-o para o caminho canônico antes do baseline.")
        return resultado

    for componente in COMPONENT_TYPES:
        registro = scaffold_task(state, componente) or {}
        if registro.get("status") != COMPLETED:
            resultado["error"] = (
                f"{componente} não está `completed` — nenhum commit de baseline "
                f"é criado sobre scaffold que não compilou.")
            return resultado

    resultado["existing_repo"] = (raiz / ".git").is_dir()
    try:
        if not resultado["existing_repo"]:
            git.git_init(raiz)
        git.git_add_all(raiz)
        if git.git_status_is_clean(raiz, cached=True):
            # Nada a commitar não é erro: numa retomada o baseline já existe.
            resultado["created"] = False
            resultado["commit_sha"] = _head_sha(raiz)
            return resultado
        mensagem = (
            "feat(scaffold): baseline compilável de frontend e backend\n\n"
            f"frontend: {(scaffold_task(state, 'frontend') or {}).get('stack')} "
            f"→ source-code/frontend\n"
            f"backend: {(scaffold_task(state, 'backend') or {}).get('stack')} "
            f"→ source-code/backend\n\n"
            "Gerado deterministicamente e validado por build real antes deste commit."
        )
        resultado["commit_sha"] = git.git_commit(raiz, mensagem)
        resultado["created"] = True
    except Exception as exc:  # noqa: BLE001 — git é limite externo
        resultado["error"] = f"{type(exc).__name__}: {exc}"
    return resultado


def _head_sha(raiz: Path) -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(raiz),
                              capture_output=True, text=True, check=False)
        return proc.stdout.strip() or None
    except OSError:
        return None


# ── Fase completa ──────────────────────────────────────────────────────────

def run_scaffold_phase(project: str, workspace: Path = REPO_ROOT, *,
                       decision: str | None = None, bcs: str | None = None,
                       force: bool = False, skip_build: bool = False,
                       timeout: int = DEFAULT_TIMEOUT, reuse: bool = True,
                       interactive: bool | None = None,
                       approval_timeout_s: int | None = None,
                       failure_decision: str | None = None,
                       run_id: str | None = None) -> dict[str, Any]:
    """Executa a fase inteira e devolve o resultado consolidado."""
    project_dir = Path(workspace) / "projects" / project
    if not project_dir.is_dir():
        raise ScaffoldRunnerError(f"projeto não encontrado: {project_dir}")
    tobe_root = project_dir / "outputs" / "tobe"

    config = _read_yaml(project_dir / "context" / "project-config.yaml")
    stacks = resolve_stacks(config)
    # Um único conjunto de BCs para os dois componentes: frontend e backend
    # precisam modelar o mesmo domínio, e cada generator resolvendo por conta
    # própria já produziu backend com 5 BCs e frontend com zero.
    if not bcs:
        derivados = resolve_bounded_contexts(project_dir)
        if derivados:
            bcs = ",".join(derivados)
            print(f"  {DIM}bounded contexts do blueprint: "
                  f"{', '.join(derivados)}{RESET}")
    run_id = run_id or f"scaffold-{uuid.uuid5(uuid.NAMESPACE_URL, project).hex[:12]}"

    state = load_state(project_dir, project)
    state["project"] = project
    state["run_id"] = run_id
    save_state(project_dir, state)

    saida: dict[str, Any] = {
        "success": False,
        "project": project,
        "run_id": run_id,
        "stacks": stacks,
        "components": {},
        "legacy_dirs": detect_legacy_output_dirs(tobe_root),
        "baseline": None,
        "approval": None,
        "coders_released": False,
        "errors": [],
    }

    if saida["legacy_dirs"]:
        # Só reporta. Mover código existente exige rotina explícita.
        for item in saida["legacy_dirs"]:
            print(f"  {YELLOW}⚠ diretório legado detectado: "
                  f"source-code/{item['name']}/ "
                  f"(canônico: {item['canonical'] or '—'}). "
                  f"Nada foi movido.{RESET}")

    # Retomada: gate pendente é reapresentado sem refazer scaffold válido.
    ja_aprovado = is_approved(state)

    for component_type in COMPONENT_TYPES:
        try:
            resultado = run_component(
                project, project_dir, workspace, state,
                component_type=component_type, stack=stacks[component_type],
                bcs=bcs, force=force, skip_build=skip_build, timeout=timeout,
                reuse=reuse)
        except (FrontMatterError, ScaffoldPathError, ScaffoldRunnerError) as exc:
            resultado = {"success": False, "component_type": component_type,
                         "stack": stacks[component_type],
                         "errors": [{"code": "CONFIG001", "message": str(exc)}],
                         "warnings": [], "error": str(exc)}
            update_scaffold_task(project_dir, state, component_type=component_type,
                                 status=RUNNING, stack=stacks[component_type])
            update_scaffold_task(project_dir, state, component_type=component_type,
                                 status=FAILED, error_summary=str(exc)[:2000])
        saida["components"][component_type] = resultado
        if not resultado.get("success"):
            saida["errors"].append(
                f"{component_type}: {resultado.get('error') or 'falhou'}")
            # O diagnóstico inteiro, não o resumo de uma linha: é o que decide
            # se o operador consegue avaliar o risco de prosseguir.
            print(f"\n{RED}✖ {component_type} falhou.{RESET}")
            _echo(str(resultado.get("error") or "falhou"), RED)

            # RF-011 (frontend reprovado impede o backend; não há valor em
            # compilar metade do sistema) continua sendo o DEFAULT — mas
            # aplicá-la calada tirava do operador uma escolha que é dele.
            # Agora ela é apresentada. Ausência de resposta mantém o bloqueio.
            override = request_failure_override(
                project_dir, state, component_type=component_type,
                resultado=resultado, decision=failure_decision,
                interactive=interactive, timeout_s=approval_timeout_s)
            saida.setdefault("failure_overrides", []).append(override)

            if override.get("status") != OVERRIDE_CONTINUED:
                print(f"{RED}  os componentes seguintes não serão gerados e "
                      f"nenhum agente coder será executado.{RESET}")
                return saida

            print(f"{YELLOW}  prosseguindo com {component_type} reprovado — "
                  f"risco registrado em scaffold-state.{RESET}")
            continue

    # Prosseguir com componente reprovado libera as FASES seguintes, nunca os
    # coders: eles escrevem features sobre o baseline, e um baseline que não
    # compila transforma cada feature gerada em retrabalho. O operador aceitou
    # o risco de seguir, não o de gerar código sobre escombros.
    houve_override = bool(saida.get("failure_overrides"))

    # `build_command` vive no front-matter do scaffold; sem ele o README cai
    # nos comandos padrão por stack. Definição ilegível não impede o arquivo.
    definicoes = {}
    for _ct in COMPONENT_TYPES:
        try:
            definicoes[_ct] = scaffold_definition_for_stack(
                stacks[_ct], SCAFFOLDS_DIR, repo_root=REPO_ROOT)
        except (FrontMatterError, ScaffoldPathError, OSError):
            definicoes[_ct] = None

    # Folha de rosto da árvore gerada. Escrita AQUI, e não depois do baseline,
    # porque `create_baseline` faz `git add -A` em `source-code/`: nesta ordem o
    # README entra no commit que representa "o sistema compila". Depois dele, o
    # arquivo nasceria fora do baseline e deixaria a árvore suja logo após o
    # commit. Falhar ao escrevê-lo não derruba a fase — é documentação, não
    # artefato de contrato.
    try:
        readme = scaffold_readme.write_readme(
            project_dir, project, state, saida["components"],
            bcs=[b for b in (bcs or "").split(",") if b],
            baseline=({"error": "componente reprovado com risco aceito; "
                                "baseline não é criado sobre scaffold que "
                                "não compila"} if houve_override else None),
            definitions=definicoes, force=force)
        saida["readme"] = readme.relative_to(project_dir).as_posix()
        if scaffold_readme.foi_gerado_por_nos(readme) or force:
            print(f"  {DIM}README: {saida['readme']}{RESET}")
        else:
            saida["readme_preserved"] = True
            print(f"  {YELLOW}⚠ {saida['readme']} tem outro autor — preservado. "
                  f"Use --force para substituí-lo pela versão gerada.{RESET}")
    except OSError as exc:
        saida.setdefault("warnings", []).append(f"README não escrito: {exc}")
        print(f"  {YELLOW}⚠ README não escrito: {exc}{RESET}")

    if houve_override:
        print(f"\n{YELLOW}  {len(saida['failure_overrides'])} componente(s) "
              f"reprovado(s) com risco aceito — agentes coder permanecem "
              f"bloqueados.{RESET}")
        blocked_by_gate(project_dir, state,
                        "componente reprovado com prosseguimento autorizado; "
                        "coders exigem baseline compilável")
        saida["success"] = True
        saida["coders_released"] = False
        return saida

    baseline = create_baseline(project_dir, state)
    saida["baseline"] = baseline
    if baseline.get("commit_sha"):
        for component_type in COMPONENT_TYPES:
            update_scaffold_task(project_dir, state, component_type=component_type,
                                 status=COMPLETED, commit_sha=baseline["commit_sha"])
    if baseline.get("error"):
        saida["errors"].append(f"baseline: {baseline['error']}")
        print(f"\n{RED}✖ baseline não criado: {baseline['error']}{RESET}")
        return saida

    resumo = build_summary(state, commit_sha=baseline.get("commit_sha"),
                           log_path=(tobe_root / "source-code" / "GENERATION_LOG.md").as_posix())
    if ja_aprovado and decision is None:
        aprovacao = state.get("approval")
        print(f"  {DIM}aprovação já registrada — gate não reapresentado.{RESET}")
    else:
        aprovacao = request_approval(project_dir, state, summary=resumo,
                                     run_id=run_id, decision=decision,
                                     interactive=interactive,
                                     timeout_s=approval_timeout_s)
    saida["approval"] = aprovacao
    estado_gate = (aprovacao or {}).get("status")

    if estado_gate == REJECTED:
        blocked_by_gate(project_dir, state,
                        "aprovação rejeitada pelo operador; scaffolds preservados")
        saida["success"] = True   # rejeição é resultado controlado, não falha técnica
        saida["coders_released"] = False
        return saida
    if estado_gate != APPROVED:
        saida["success"] = True   # espera também é resultado controlado
        saida["coders_released"] = False
        return saida

    saida["success"] = True
    saida["coders_released"] = True
    return saida


def coders_released(project: str, workspace: Path = REPO_ROOT) -> bool:
    """Porta única dos agentes coder. Chamada por quem for despachá-los."""
    project_dir = Path(workspace) / "projects" / project
    return is_approved(load_state(project_dir, project))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fase de scaffold: frontend → backend → baseline → aprovação.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--workspace", default=str(REPO_ROOT))
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--approve", action="store_true",
                       help="registra aprovação explícita sem terminal")
    grupo.add_argument("--reject", action="store_true",
                       help="registra rejeição explícita sem terminal")
    parser.add_argument("--bcs", default=None,
                        help="bounded contexts separados por vírgula (ambos generators)")
    parser.add_argument("--force", action="store_true",
                        help="sobrescreve arquivos existentes nos generators")
    parser.add_argument("--no-reuse", action="store_true",
                        help="ignora scaffold concluído e regenera")
    parser.add_argument("--skip-build", action="store_true",
                        help="pula a compilação real (diagnóstico; não libera baseline)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="prazo de generator/verifier, em segundos")
    parser.add_argument("--approval-timeout", type=int, default=None,
                        help=f"segundos de espera no gate antes da aprovação "
                             f"automática (default: "
                             f"{DEFAULT_APPROVAL_TIMEOUT_S}; 0 = modo estrito, "
                             f"sem aprovação automática)")
    parser.add_argument("--on-component-failure", default=None,
                        choices=["continue", "abort"],
                        help="decide sem terminal o que fazer quando um "
                             "componente reprova; sem a flag, pergunta ao "
                             "operador e aborta se ninguem responder")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    decisao = "approve" if args.approve else ("reject" if args.reject else None)
    try:
        resultado = run_scaffold_phase(
            args.project, Path(args.workspace), decision=decisao, bcs=args.bcs,
            force=args.force, skip_build=args.skip_build, timeout=args.timeout,
            approval_timeout_s=args.approval_timeout, reuse=not args.no_reuse,
            failure_decision=args.on_component_failure)
    except (ScaffoldRunnerError, FrontMatterError, ScaffoldPathError,
            StateError) as exc:
        # Falha esperada da fase vira mensagem objetiva, nunca traceback: quem
        # opera a esteira precisa do que fazer, não do stack do Python.
        payload = {"success": False, "project": args.project,
                   "errors": [str(exc)], "coders_released": False}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            regua = "=" * 72
            print()
            print(f"{RED}{regua}{RESET}")
            print(f"{RED}{BOLD}  FASE DE SCAFFOLD INTERROMPIDA{RESET}")
            print(f"{RED}{regua}{RESET}")
            print(f"  {type(exc).__name__}: {exc}")
            print()
            print(f"{CYAN}  PRÓXIMO PASSO{RESET}")
            print(f"{CYAN}    Corrija a causa acima e re-execute. O estado ficou "
                  f"em tasks-progress.json;{RESET}")
            print(f"{CYAN}    nenhum agente coder foi liberado.{RESET}")
            print()
        return 2

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
    else:
        estado = (resultado.get("approval") or {}).get("status") or "—"
        print(f"\nscaffold: {'OK' if not resultado['errors'] else 'FALHOU'} | "
              f"gate: {estado} | coders liberados: "
              f"{'sim' if resultado['coders_released'] else 'não'}")
    return 0 if resultado.get("success") and not resultado.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
