#!/usr/bin/env python3
"""
f4_routing.py — Roteamento determinístico da F4 (Tech Stack Code Generation).

Este módulo é a implementação executável do `ava-stack-orchestrator`: ele não
gera código, ele **decide**. Para cada task do razão responde, de forma
auditável e fail-closed:

  * qual agente especializado implementa a task (`ava-stack-{tech}-{camada}`);
  * qual é o `component_type` (frontend | backend);
  * qual é o diretório canônico de saída;
  * qual comando de build/verificação vale para a stack;
  * por que essa decisão foi tomada (`reason`, para o log de observabilidade).

Por que existe
--------------
O passo F4 declarava `ava-stack-orchestrator` como agente e um `agent_map` que
apontava **todas** as stacks para o mesmo `ava-f4s-codegen-agent`. Os coders
reais declarados em `tech-stack/module.yaml` — `ava-stack-dotnet-backend`,
`ava-stack-angular-frontend`, ... — nunca eram carregados. O roteamento existia
só na prosa da spec do orquestrador, que é interpretada pelo próprio agente que
ela governa.

Aqui o roteamento é código: uma tabela explícita, conferida contra o
`agent_registry` e contra o disco. Stack desconhecida, agente inexistente ou
spec ausente **falham** — não caem em agente genérico. Fallback silencioso para
um coder genérico é o defeito, não a rede de proteção.

Diretório canônico
------------------
A resolução do caminho é delegada a `scaffold_paths`, o mesmo módulo que a F4S
usa. `target_stack` escolhe agente e comandos; **nunca** entra no caminho. É o
que garante que o esqueleto (F4S) e as features (F4) terminem no mesmo lugar.
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

import f4_scope  # noqa: E402
import scaffold_paths  # noqa: E402
from scaffold_paths import (  # noqa: E402
    COMPONENT_TYPES,
    ScaffoldPathError,
    component_type_for_stack,
    normalize_component_type,
    resolve_source_code_path,
)


class RoutingError(Exception):
    """Roteamento impossível. Sempre antes de despachar qualquer agente."""

    def __init__(self, message: str, *, code: str = "ROUTE000",
                 task_id: str = "", detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.task_id = task_id
        self.detail = dict(detail or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "task_id": self.task_id,
            "message": str(self),
            "detail": self.detail,
        }


#: Agentes coder reais, por `component_type` e stack. Os ids são os declarados
#: em `src/modules/ava-fabric-agents/tech-stack/module.yaml` — não invente nomes
#: aqui: `validate_routing_table()` confere cada um contra o `agent_registry`.
#:
#: Aliases existem porque o `target_stack` do SpecKit ora nomeia o framework
#: (`spring-boot`, `fastapi`, `gin`, `nestjs`), ora a linguagem (`java`,
#: `python`, `go`, `node`). As duas grafias roteiam para o mesmo agente.
STACK_AGENTS: dict[str, dict[str, str]] = {
    "backend": {
        "dotnet": "ava-stack-dotnet-backend",
        "spring-boot": "ava-stack-java-backend",
        "java": "ava-stack-java-backend",
        "fastapi": "ava-stack-python-backend",
        "python": "ava-stack-python-backend",
        "gin": "ava-stack-go-backend",
        "go": "ava-stack-go-backend",
        "nestjs": "ava-stack-node-backend",
        "node": "ava-stack-node-backend",
    },
    "frontend": {
        "angular": "ava-stack-angular-frontend",
        "react": "ava-stack-react-frontend",
        "vue": "ava-stack-vue-frontend",
        "blazor": "ava-stack-blazor-frontend",
    },
}

#: Agente das tasks de infraestrutura. A F4 não tinha para onde mandar uma task
#: que pede `infra/terraform/main.tf`: ela chegava rotulada como `backend` e o
#: arquivo terminava em `backend/infra/terraform/`, fora do escopo do commit.
#: `ava-devops-iac` já existe no repositório e é o dono de IaC.
INFRA_AGENT = "ava-devops-iac"

#: Comando de verificação padrão de infraestrutura. Falha aqui **não** bloqueia
#: a esteira (ver `f4_scope.is_blocking`): credencial ausente ou provider
#: indisponível não diz nada sobre o `.tf` gerado.
INFRA_BUILD_COMMAND: tuple[str, ...] = ("terraform", "validate")

#: Agentes que NUNCA podem ser resultado de roteamento por stack. O genérico
#: continua existindo no repositório (e pode ser despachado à mão), mas ele ser
#: escolhido *por omissão* é exatamente o defeito que este módulo fecha.
FORBIDDEN_ROUTE_TARGETS: frozenset[str] = frozenset({
    "ava-f4s-codegen-agent",
    "ava-stack-orchestrator",
})


@dataclass(frozen=True)
class Route:
    """Decisão de roteamento de uma task. Tudo que o despacho precisa saber."""

    task_id: str
    task_type: str
    component_type: str
    target_stack: str
    agent: str
    spec_path: str
    canonical_source_rel: str
    canonical_source_dir: Path
    repo_dir: Path
    build_command: list[str] = field(default_factory=list)
    verify_command: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "component_type": self.component_type,
            "target_stack": self.target_stack,
            "agent": self.agent,
            "spec_path": self.spec_path,
            "canonical_source_rel": self.canonical_source_rel,
            "canonical_source_dir": self.canonical_source_dir.as_posix(),
            "repo_dir": self.repo_dir.as_posix(),
            "build_command": list(self.build_command),
            "verify_command": self.verify_command,
            "routing_reason": self.reason,
        }


# ─── Caminhos canônicos ──────────────────────────────────────────────────────

def tobe_root(project: str, repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / "projects" / project / "outputs" / "tobe"


def source_code_root(project: str, repo_root: Path | None = None) -> Path:
    """Raiz do repositório git de código — a mesma que a F4S usa no baseline."""
    return tobe_root(project, repo_root) / scaffold_paths.SOURCE_CODE_ROOT


def canonical_source_dir(project: str, component_type: str,
                         repo_root: Path | None = None) -> Path:
    """`outputs/tobe/source-code/{frontend|backend|infra}` — validado, sempre.

    A stack não entra aqui. Nem como sufixo, nem como prefixo, nem como
    fallback: quem quiser `source-code/dotnet` precisa mudar `scaffold_paths`,
    e lá a construção é proibida por teste de regressão.

    `infra` não passa por `scaffold_paths.resolve_output_dir` porque aquele
    módulo é a autoridade dos DOIS componentes que a F4S gera, e mexer nele
    mudaria o comportamento da F4S. Infraestrutura é escopo da F4.
    """
    if str(component_type).strip().lower() == f4_scope.KIND_INFRA:
        return source_code_root(project, repo_root) / f4_scope.KIND_INFRA
    return scaffold_paths.resolve_output_dir(
        tobe_root(project, repo_root), component_type)


# ─── Classificação ───────────────────────────────────────────────────────────

def component_type_for_task(task: dict[str, Any]) -> str:
    """`component_type` da task — evidência manda, `task_type` é ponto de partida.

    Ordem: infraestrutura reconhecida por `f4_scope.classify` (alvo declarado,
    comando de verificação ou id) vence tudo — foi obedecer ao rótulo
    `task_type: backend` de uma task cujo alvo era `infra/terraform/main.tf` que
    fez o arquivo terminar em `backend/infra/terraform/`. Depois disso,
    `task_type` manda e a stack confirma; divergência entre os dois é defeito de
    planejamento e falha aqui, antes de escrever no lugar errado.
    """
    task_id = str(task.get("task_id") or "")
    classificacao = f4_scope.classify(task)
    if classificacao.kind == f4_scope.KIND_INFRA:
        return f4_scope.KIND_INFRA

    declarado = str(task.get("task_type") or "").strip().lower()
    stack = str(task.get("target_stack") or "").strip().lower()

    derivado = ""
    if stack:
        try:
            derivado = component_type_for_stack(stack)
        except ScaffoldPathError as exc:
            if not declarado:
                raise RoutingError(
                    f"target_stack {stack!r} nao tem `component_type` declarado "
                    f"e a task nao traz `task_type`: {exc}",
                    code="ROUTE001", task_id=task_id,
                    detail={"target_stack": stack}) from exc

    if declarado:
        if declarado not in COMPONENT_TYPES:
            raise RoutingError(
                f"task_type invalido: {declarado!r} "
                f"(aceitos: {', '.join(COMPONENT_TYPES)})",
                code="ROUTE002", task_id=task_id,
                detail={"task_type": declarado})
        if derivado and derivado != declarado:
            raise RoutingError(
                f"task_type={declarado!r} conflita com target_stack={stack!r}, "
                f"que e {derivado!r}. Corrija o fragmento da task na F3S — "
                f"escrever no diretorio errado e pior que parar aqui.",
                code="ROUTE003", task_id=task_id,
                detail={"task_type": declarado, "target_stack": stack,
                        "component_type_da_stack": derivado})
        return declarado

    if derivado:
        return derivado

    raise RoutingError(
        "task sem `task_type` e sem `target_stack` — impossivel decidir "
        "frontend ou backend",
        code="ROUTE004", task_id=task_id)


def agent_for(component_type: str, target_stack: str,
              task_id: str = "") -> tuple[str, str]:
    """`(agent_id, motivo)` para a combinação. Sem fallback genérico."""
    if str(component_type).strip().lower() == f4_scope.KIND_INFRA:
        return INFRA_AGENT, f"infra → {INFRA_AGENT} (IaC é escopo próprio)"
    component = normalize_component_type(component_type)
    stack = str(target_stack or "").strip().lower()
    if not stack:
        raise RoutingError(
            "task sem `target_stack` — o agente coder e escolhido pela stack",
            code="ROUTE005", task_id=task_id)

    tabela = STACK_AGENTS.get(component, {})
    agente = tabela.get(stack)
    if not agente:
        raise RoutingError(
            f"nenhum agente especializado para {component}/{stack}. "
            f"Stacks roteaveis em {component}: "
            f"{', '.join(sorted(tabela)) or '(nenhuma)'}. "
            f"Declare o agente em tech-stack/module.yaml e registre-o em "
            f"f4_routing.STACK_AGENTS — o generico nao e rede de protecao.",
            code="ROUTE006", task_id=task_id,
            detail={"component_type": component, "target_stack": stack})
    if agente in FORBIDDEN_ROUTE_TARGETS:
        raise RoutingError(
            f"tabela de roteamento aponta {component}/{stack} para o agente "
            f"generico {agente!r} — proibido por construcao",
            code="ROUTE007", task_id=task_id)
    return agente, f"{component}/{stack} -> {agente} (tech-stack/module.yaml)"


def spec_path_for(agent_id: str, repo_root: Path | None = None,
                  task_id: str = "") -> str:
    """Caminho da spec do agente, conferido no registry E em disco.

    `repo_root` aqui é a raiz do REPOSITÓRIO (onde vive `src/modules/...`), que
    não é necessariamente a raiz do workspace de projetos usada nos testes —
    por isso o default é o `REPO_ROOT` deste módulo, e não o workspace.
    """
    root = repo_root or REPO_ROOT
    try:
        import agent_registry  # noqa: PLC0415
        entrada = agent_registry.get(agent_id)
    except Exception as exc:  # noqa: BLE001 — registry quebrado é erro de rota
        raise RoutingError(
            f"agent_registry indisponivel ao resolver {agent_id!r}: {exc}",
            code="ROUTE008", task_id=task_id) from exc

    caminho = str((entrada or {}).get("path") or "")
    if not caminho:
        raise RoutingError(
            f"agente {agent_id!r} nao esta no agent_registry — o roteamento "
            f"nao inventa spec e nao cai no generico",
            code="ROUTE009", task_id=task_id)
    if not (root / caminho).is_file():
        raise RoutingError(
            f"spec do agente {agent_id!r} ausente em disco: {caminho}",
            code="ROUTE010", task_id=task_id, detail={"spec_path": caminho})
    return caminho


def build_command_for(target_stack: str, verify_command: str = "",
                      task_id: str = "", component_type: str = "") -> list[str]:
    """Comando de verificação da stack, com o `verify_command` da task no topo.

    Infraestrutura tem comando próprio e **não** passa pelo build runner das
    stacks de aplicação: `terraform validate` num diretório sem `.terraform/`
    inicializado não é sinal de qualidade do `.tf`.
    """
    if str(component_type).strip().lower() == f4_scope.KIND_INFRA:
        if verify_command:
            import shlex  # noqa: PLC0415
            return shlex.split(verify_command)
        return list(INFRA_BUILD_COMMAND)
    try:
        import f4s_build_runner  # noqa: PLC0415
        return f4s_build_runner.resolve_command(target_stack,
                                                verify_command or None)
    except Exception as exc:  # noqa: BLE001
        raise RoutingError(
            f"stack {target_stack!r} sem comando de build resolvivel: {exc}",
            code="ROUTE011", task_id=task_id) from exc


# ─── Decisão ─────────────────────────────────────────────────────────────────

def resolve_route(task: dict[str, Any], project: str,
                  repo_root: Path | None = None) -> Route:
    """Rota completa da task. Levanta `RoutingError` em vez de improvisar."""
    root = repo_root or REPO_ROOT
    task_id = str(task.get("task_id") or "")
    if not task_id:
        raise RoutingError("task sem `task_id`", code="ROUTE012")

    component = component_type_for_task(task)
    stack = str(task.get("target_stack") or "").strip().lower()
    agente, motivo = agent_for(component, stack, task_id)
    # A spec do agente vem do repositório, não do workspace do projeto.
    spec = spec_path_for(agente, None, task_id)
    verify = str(task.get("verify_command") or "").strip()
    destino = canonical_source_dir(project, component, root)

    return Route(
        task_id=task_id,
        task_type=component,
        component_type=component,
        target_stack=stack,
        agent=agente,
        spec_path=spec,
        canonical_source_rel=(f"{scaffold_paths.SOURCE_CODE_ROOT}/{component}"
                              if component == f4_scope.KIND_INFRA
                              else resolve_source_code_path(component)),
        canonical_source_dir=destino,
        repo_dir=source_code_root(project, root),
        build_command=build_command_for(stack, verify, task_id,
                                        component_type=component),
        verify_command=verify,
        reason=motivo,
    )


def routing_table() -> list[dict[str, str]]:
    """A tabela inteira, achatada — para documentação, relatório e teste."""
    return [
        {"component_type": componente, "target_stack": stack, "agent": agente}
        for componente in sorted(STACK_AGENTS)
        for stack, agente in sorted(STACK_AGENTS[componente].items())
    ]


def validate_routing_table(repo_root: Path | None = None) -> list[str]:
    """Problemas entre a tabela e o repositório real. Lista vazia = coerente."""
    problemas: list[str] = []
    for item in routing_table():
        try:
            spec_path_for(item["agent"], None)
        except RoutingError as exc:
            problemas.append(
                f"{item['component_type']}/{item['target_stack']}: {exc}")
    return problemas


def _main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415
    import json  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/f4_routing.py",
        description="Tabela de roteamento da F4 — stack para agente especializado.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--validate", action="store_true",
                        help="confere cada agente contra o registry e o disco")
    args = parser.parse_args(argv)

    if args.validate:
        problemas = validate_routing_table()
        if args.json:
            print(json.dumps({"status": "ok" if not problemas else "broken",
                              "issues": problemas}, ensure_ascii=False, indent=2))
        else:
            for item in problemas:
                print(f"  [ERRO] {item}")
            if not problemas:
                print("  [OK] tabela de roteamento coerente com o agent_registry")
        return 0 if not problemas else 1

    tabela = routing_table()
    if args.json:
        print(json.dumps(tabela, ensure_ascii=False, indent=2))
    else:
        for item in tabela:
            print(f"  {item['component_type']:<9} {item['target_stack']:<12} "
                  f"-> {item['agent']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
