#!/usr/bin/env python3
"""
f4_gate.py — Gate estrutural entre a F4S (scaffold) e a F4 (geração de código).

Por que existe
--------------
A precondição "só despache coders se o scaffold foi aprovado" existia apenas
como prosa no Step 0.0 de `orchestrator-stack.md` — isto é, era conferida pelo
próprio agente que ela governa. Um agente que pule ou racionalize a checagem
não era bloqueado por ninguém.

Aqui a mesma pergunta é respondida por código, lendo o estado que a F4S grava,
antes de qualquer inferência. Este módulo **não escreve nada**: a F4S continua
sendo a única dona de `outputs/tobe/tasks-progress.json` (estado do scaffold,
schema 1.0.0 — arquivo distinto do razão da F4, que vive em
`outputs/tobe/speckit/tasks-progress.json`).

Fail-closed: ausência de evidência é reprovação. Nunca "aprovado por omissão".
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import scaffold_state  # noqa: E402
from scaffold_paths import COMPONENT_TYPES, resolve_source_code_path  # noqa: E402


@dataclass
class GateResult:
    """Veredito do gate. `ok=False` impede o despacho de qualquer coder."""

    ok: bool
    coders_released: bool = False
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "coders_released": self.coders_released,
            "reasons": list(self.reasons),
            "details": dict(self.details),
        }

    def message(self) -> str:
        cabecalho = ("gate F4S->F4 aprovado" if self.ok
                     else "gate F4S->F4 REPROVADO — nenhum agente coder sera despachado")
        linhas = [cabecalho]
        linhas += [f"  - {motivo}" for motivo in self.reasons]
        if not self.ok:
            linhas.append("  Rode: python src/shared/tools/scaffold_runner.py "
                          "--project {projeto} --json  e aprove o baseline.")
        return "\n".join(linhas)


def scaffold_state_path(project: str, repo_root: Path | None = None) -> Path:
    project_dir = (repo_root or REPO_ROOT) / "projects" / project
    return scaffold_state.state_path(project_dir)


def check(project: str, repo_root: Path | None = None) -> GateResult:
    """Confere, em disco, tudo que a F4 precisa da F4S antes de começar."""
    root = repo_root or REPO_ROOT
    project_dir = root / "projects" / project
    tobe_root = project_dir / "outputs" / "tobe"
    motivos: list[str] = []
    detalhes: dict[str, Any] = {"project": project}

    caminho_estado = scaffold_state.state_path(project_dir)
    detalhes["scaffold_state"] = caminho_estado.as_posix()
    if not caminho_estado.is_file():
        return GateResult(
            ok=False, coders_released=False,
            reasons=[f"estado da F4S ausente: {caminho_estado} — a F4S nao foi "
                     f"executada neste projeto"],
            details=detalhes)

    estado = scaffold_state.load_state(project_dir, project)

    # 1. Cada componente precisa ter concluído E compilado.
    componentes: dict[str, Any] = {}
    for component_type in COMPONENT_TYPES:
        registro = scaffold_state.scaffold_task(estado, component_type) or {}
        componentes[component_type] = {
            "status": registro.get("status"),
            "build_status": registro.get("build_status"),
            "verification_status": registro.get("verification_status"),
            "commit_sha": registro.get("commit_sha"),
            "stack": registro.get("stack"),
        }
        if registro.get("status") != scaffold_state.COMPLETED:
            motivos.append(
                f"scaffold de {component_type} nao esta `completed` "
                f"(status={registro.get('status') or 'ausente'})")
            continue
        if registro.get("build_status") not in {"succeeded", None}:
            motivos.append(
                f"build inicial de {component_type} nao passou "
                f"(build_status={registro.get('build_status')!r})")
        if registro.get("verification_status") not in {"succeeded", None}:
            motivos.append(
                f"verificacao inicial de {component_type} nao passou "
                f"(verification_status={registro.get('verification_status')!r})")
    detalhes["components"] = componentes

    # 2. Diretórios canônicos precisam existir e ter scaffold de verdade.
    #    A definição é a MESMA do baseline (`f4_baseline.scaffold_present`):
    #    diretório com um `.keep` dentro não é scaffold, e o gate concordar com
    #    o baseline evita a fase passar aqui e reprovar task por task depois.
    import f4_baseline  # noqa: PLC0415
    for component_type in COMPONENT_TYPES:
        destino = tobe_root / resolve_source_code_path(component_type)
        existe = f4_baseline.scaffold_present(destino)
        componentes[component_type]["canonical_dir"] = destino.as_posix()
        componentes[component_type]["canonical_dir_populated"] = existe
        if not existe:
            motivos.append(
                f"diretorio canonico ausente ou vazio: "
                f"{resolve_source_code_path(component_type)}/")

    # 3. Baseline git da F4S — o ponto de retorno sobre o qual a F4 commita.
    repo_git = tobe_root / "source-code" / ".git"
    commit = next((componentes[c].get("commit_sha") for c in COMPONENT_TYPES
                   if componentes[c].get("commit_sha")), None)
    detalhes["baseline_repo"] = repo_git.as_posix()
    detalhes["baseline_commit"] = commit
    if not repo_git.is_dir():
        motivos.append("baseline git ausente em source-code/.git — a F4 commita "
                       "cada task nesse repositorio")
    if not commit:
        motivos.append("nenhum commit de baseline registrado no estado da F4S")

    # 4. O gate humano. `is_approved` e a unica porta dos coders.
    liberado = scaffold_state.is_approved(estado)
    detalhes["approval"] = estado.get("approval")
    detalhes["coders_released"] = liberado
    if not liberado:
        motivos.append(
            f"coders_released=false (approval="
            f"{scaffold_state.approval_status(estado) or 'ausente'}) — "
            f"o baseline nao foi aprovado")

    downstream = estado.get("downstream") or {}
    if downstream.get("status") == scaffold_state.BLOCKED:
        motivos.append(f"F4S bloqueou o downstream: {downstream.get('reason')}")

    return GateResult(ok=not motivos, coders_released=liberado,
                      reasons=motivos, details=detalhes)


def _main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415
    import json  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/f4_gate.py",
        description="Gate estrutural F4S->F4. Exit 0 libera os coders.")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    resultado = check(args.project)
    if args.json:
        print(json.dumps(resultado.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(resultado.message())
    return 0 if resultado.ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
