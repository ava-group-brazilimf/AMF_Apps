#!/usr/bin/env python3
"""F4S Scaffold Spec Injector — deterministic pre-compile step.

Entry: python src/shared/tools/f4s_scaffold_injector.py --project <name>

Responsibilities:
  1. Read project-config.yaml and resolve target stacks (backend + frontend).
  2. For each target stack, locate the per-language scaffold spec MD under
     src/modules/ava-fabric-agents/tech-stack/scaffolds/.
  3. Enrich the W0 Foundation feature with deterministic scaffold groups and
      tasks so plan.md, task-fragment.json and tasks.md remain in one wave.

The emitted scaffold task produces ``artifact:scaffold:{stack}``; the compiler
adds implicit edges so every later task with the same target_stack depends on it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover — pyyaml está disponível no venv do repo
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

# Força UTF-8 no Windows - mesma guarda de src/shared/checks/cli.py.
# Sem ela qualquer mensagem acentuada estoura UnicodeEncodeError no console
# cp1252 e a tool morre por um detalhe de terminal, não por um defeito real.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(SCRIPT_DIR))

SCAFFOLDS_DIR = REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "tech-stack" / "scaffolds"


class ScaffoldInjectorError(ValueError):
    """Erro fatal do injector; o CLI trata como exit 2."""


def _fail(message: str) -> None:
    print(f"[f4s-scaffold-injector] ERROR: {message}", file=sys.stderr)
    raise ScaffoldInjectorError(message)


def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ScaffoldInjectorError("pyyaml não está instalado")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScaffoldInjectorError(f"arquivo ausente: {path}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ScaffoldInjectorError(f"falha ao ler {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def _normalize_stack(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return raw.strip().lower()


def _pascal_case(name: str) -> str:
    """Convert kebab/snake/camel case to PascalCase."""
    return "".join(part.capitalize() for part in re.split(r"[-_\s]+", name) if part)


def _stack_to_scaffold_path(stack: str) -> Path:
    specific = SCAFFOLDS_DIR / f"{stack}-scaffold.md"
    return specific if specific.exists() else SCAFFOLDS_DIR / "default-scaffold.md"


def _scaffold_title(stack: str, scaffold_md: Path) -> str:
    """Extract title from front-matter or first heading."""
    text = scaffold_md.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        try:
            fm_end = text.index("---", 3)
            front = yaml.safe_load(text[3:fm_end])
            if isinstance(front, dict) and front.get("name"):
                return str(front["name"])
        except Exception:  # noqa: BLE001
            pass
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return f"Scaffold {_pascal_case(stack)}"


def _verify_command_for_stack(stack: str) -> str:
    """Default build command per stack; can be overridden by scaffold front-matter."""
    return {
        "dotnet": "dotnet build",
        "spring-boot": "mvn compile",
        "fastapi": "python -m compileall src",
        "gin": "go build ./...",
        "nestjs": "npm run build",
        "angular": "ng build",
        "react": "npm run build",
        "vue": "npm run build",
        "blazor": "dotnet build",
    }.get(stack, "echo 'no build command configured'")


#: Âncora real dentro do próprio spec.md do scaffold. Antes o injetor apontava
#: `source_refs` para `architecture-blueprint.md` com a âncora literal "SCAFFOLD",
#: que não existe naquele arquivo — o CHK-SK-006 reprovava, com razão.
SCAFFOLD_ANCHOR = "Estrutura a gerar"


def _secoes_readiness(stack: str, target: str, verify_command: str) -> str:
    """As 6 seções literais que o readiness-gate C2 e o CHK-SK-014 exigem.

    Os headings são conferidos por glob em inglês; traduzi-los reprova.
    """
    return "\n".join([
        "## Context",
        "",
        f"Scaffold determinístico da stack `{stack}`, injetado por "
        "`f4s_scaffold_injector.py` como tarefa transversal da wave W0. É a "
        "primeira task de cada `target_stack`; toda task de domínio depende dela.",
        "",
        "## Input",
        "",
        "- `context/project-config.yaml` — `tobe_stack`, versões e nomes",
        "- `outputs/tobe/docs/architecture-blueprint.md` — bounded contexts",
        "- `outputs/tobe/speckit/constitution.md` — camadas e pacotes permitidos",
        "",
        "## Processing",
        "",
        "Aplicar a estrutura descrita na seção *Estrutura a gerar* acima, "
        "derivando nomes de projeto e bounded contexts das entradas. Nenhuma "
        "regra de negócio nesta etapa — apenas esqueleto, pacotes e referências.",
        "",
        "## Output",
        "",
        f"- `{target}` — registro da execução do scaffold",
        "- Árvore de projetos compilável em `outputs/tobe/source-code/`",
        "",
        "## Examples",
        "",
        "```bash",
        f"# verificação de aceite desta task",
        f"{verify_command}",
        "```",
        "",
        "## Failure Modes",
        "",
        f"- `{verify_command}` retorna diferente de zero → scaffold inválido; "
        "nenhuma task de domínio da stack pode iniciar.",
        "- Bounded context ausente no blueprint → projeto não gerado; a task de "
        "domínio correspondente falhará por diretório inexistente.",
        "- Versão de framework divergente de `project-config.yaml` → build quebra "
        "na primeira task que usar recurso da versão.",
        "",
    ])


def _inherit_trace_id(speckit_specs: Path, project_config: dict[str, Any],
                      project_name: str) -> str:
    """Descobre o trace_id do projeto em vez de inventar um.

    O compilador exige um único `trace_id` em todos os plan-graphs e fragments
    (`speckit_task_compiler`: "trace_id divergente entre fragments e planos").
    Como os scaffolds entram no mesmo conjunto, precisam herdar o mesmo valor.

    Ordem de precedência — do mais autoritativo ao último recurso:
      1. `trace_id` dos plan-graph.json de domínio já em disco (o que os agentes
         de planning gravaram; é o valor com que o conjunto já é coerente);
      2. `trace_id` do wave-spec-manifest.json;
      3. `trace_id` do project-config.yaml;
      4. derivação estável do nome do projeto — determinística, para que
         reexecutar o injetor não mude o resultado.
    """
    candidatos: list[str] = []
    for plan in sorted(speckit_specs.glob("*/plan-graph.json")):
        if plan.parent.name.startswith("000-scaffold-"):
            continue  # não herdar de si mesmo em reexecuções
        try:
            valor = json.loads(plan.read_text(encoding="utf-8")).get("trace_id")
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(valor, str) and valor:
            candidatos.append(valor)
    if candidatos:
        # Divergência entre os próprios planos é problema do compilador reportar;
        # aqui basta acompanhar a maioria para não ser a causa da divergência.
        return Counter(candidatos).most_common(1)[0][0]

    manifesto = speckit_specs.parent / "wave-spec-manifest.json"
    if manifesto.is_file():
        try:
            valor = json.loads(manifesto.read_text(encoding="utf-8")).get("trace_id")
            if isinstance(valor, str) and valor:
                return valor
        except (OSError, json.JSONDecodeError):
            pass

    do_config = project_config.get("trace_id")
    if isinstance(do_config, str) and do_config:
        return do_config

    return f"trace-{hashlib.sha256(project_name.encode('utf-8')).hexdigest()[:12]}"


def _resolve_target_stacks(project_config: dict[str, Any]) -> list[str]:
    """Return distinct target stacks that require code generation."""
    stacks: set[str] = set()
    tobe = project_config.get("tobe_stack") or {}
    backend = _normalize_stack(tobe.get("backend_framework"))
    frontend = _normalize_stack(tobe.get("frontend_framework"))
    if backend:
        stacks.add(backend)
    if frontend:
        stacks.add(frontend)
    return sorted(stacks)


def _component_type(stack: str) -> str:
    """Responsabilidade arquitetural da stack — a chave de tudo abaixo."""
    from scaffold_paths import component_type_for_stack
    return component_type_for_stack(stack)


def _scaffold_group(stack: str) -> str:
    # Group/task/artifact nomeiam a RESPONSABILIDADE, não a tecnologia: trocar
    # Angular por React não pode renomear a task nem invalidar as arestas do
    # grafo que dependem dela. A stack segue como atributo em `target_stack`.
    # Schema exige maiúsculas e dígitos: ^G-[A-Z0-9]+(?:-[A-Z0-9]+)*$
    return f"G-SCAFFOLD-{_component_type(stack).upper()}"


def _scaffold_task_id(stack: str) -> str:
    return f"T-SCAFFOLD-{_component_type(stack).upper()}-001"


def _scaffold_artifact(stack: str) -> str:
    return f"artifact:scaffold:{_component_type(stack)}"


def _target_file(stack: str) -> str:
    return f".scaffold/000-scaffold-{_component_type(stack)}.md"


def inject_scaffold_specs(
    project_name: str,
    repo_root: Path | None = None,
    *,
    write: bool = True,
) -> list[dict[str, Any]]:
    """Generate synthetic scaffold specs for every target stack.

    Returns a list describing each generated scaffold spec without writing if
    ``write=False``.
    """
    root = repo_root or REPO_ROOT
    config_path = root / "projects" / project_name / "context" / "project-config.yaml"
    if not config_path.exists():
        _fail(f"project-config.yaml não encontrado: {config_path}")

    project_config = _read_yaml(config_path)
    actual_project_name = project_config.get("project_name") or project_name

    stacks = _resolve_target_stacks(project_config)
    if not stacks:
        _fail("nenhuma target_stack encontrada em project-config.yaml → tobe_stack")

    speckit_specs = root / "projects" / actual_project_name / "outputs" / "tobe" / "speckit" / "specs"

    # ── trace_id: herdar, nunca inventar ─────────────────────────────────────
    # Antes: `project_config.get("trace_id") or f"trace-{uuid4().hex[:12]}"`.
    # O project-config.yaml normalmente NÃO tem trace_id, então o injetor sorteava
    # um UUID novo a cada execução. Isso (a) divergia do trace_id dos planos de
    # domínio, e o compilador exige um único trace_id em todo o conjunto, e (b)
    # tornava a saída de um passo "determinístico" irreprodutível.
    # Agora a origem é, em ordem: os plan-graph.json de domínio já em disco →
    # o manifesto de waves → o project-config → derivação estável do projeto.
    trace_id = _inherit_trace_id(speckit_specs, project_config, actual_project_name)
    manifest_path = speckit_specs.parent / "wave-spec-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    foundation = next(
        (item for item in manifest.get("features") or []
         if item.get("wave_id") == "W0" or item.get("wave_type") == "foundation"),
        None,
    )
    if not foundation or not foundation.get("feature"):
        _fail("wave W0 Foundation ausente em wave-spec-manifest.json")
    feature = str(foundation["feature"])
    feature_dir = speckit_specs / feature
    plan_graph_path = feature_dir / "plan-graph.json"
    fragment_path = feature_dir / "task-fragment.json"
    spec_path = feature_dir / "spec.md"
    plan_path = feature_dir / "plan.md"
    for required in (plan_graph_path, fragment_path, spec_path, plan_path):
        if not required.is_file():
            _fail(f"artefato W0 ausente antes da injeção: {required}")

    plan_graph = json.loads(plan_graph_path.read_text(encoding="utf-8"))
    task_fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    plan_graph["trace_id"] = trace_id
    task_fragment["trace_id"] = trace_id
    generated: list[dict[str, Any]] = []
    spec_sections: list[str] = []
    plan_rows: list[str] = []

    for stack in stacks:
        scaffold_md = _stack_to_scaffold_path(stack)
        if not scaffold_md.exists():
            _fail(f"scaffold não encontrado para stack {stack}: {scaffold_md}")

        title = _scaffold_title(stack, scaffold_md)
        group = _scaffold_group(stack)
        task_id = _scaffold_task_id(stack)
        target = _target_file(stack)
        verify_command = _verify_command_for_stack(stack)

        # Scaffolds são tarefas transversais de W0 (foundation): rodam antes
        # das waves de domínio e produzem o artefato base de cada stack.
        migration_wave_id = "W0"
        migration_wave_order = 0
        task_type = "frontend" if stack in {"angular", "react", "vue", "blazor"} else "backend"
        anchor = f"Scaffold determinístico — {stack}"
        source_refs = [{
            "artifact": f"outputs/tobe/speckit/specs/{feature}/spec.md",
            "anchor": anchor,
        }]
        if not any(item.get("group") == group for item in plan_graph.get("groups") or []):
            plan_graph.setdefault("groups", []).insert(0, {
                "group": group,
                "target_stack": stack,
                "scope": f"scaffold CLI determinístico {stack}",
                "depends_on": [],
                "verify_command": verify_command,
            })
        if not any(item.get("path") == target for item in plan_graph.get("files") or []):
            plan_graph.setdefault("files", []).insert(0, {
                "path": target,
                "action": "create",
                "group": group,
                "task_type": task_type,
                "responsibility": f"Executar receita CLI oficial para {stack}",
                "source_refs": source_refs,
                "produces": [_scaffold_artifact(stack)],
                "consumes": [],
            })
        if not any(item.get("task_id") == task_id for item in task_fragment.get("entries") or []):
            task_fragment.setdefault("entries", []).insert(0, {
                    "task_id": task_id,
                    "title": title,
                    "group": group,
                    "task_type": task_type,
                    "target_stack": stack,
                    "source_refs": source_refs,
                    "target_file": target,
                    "action": "create",
                    "depends_on": [],
                    "depends_on_groups": [],
                    "produces": [_scaffold_artifact(stack)],
                    "consumes": [],
                    "acceptance": [f"{verify_command} sem erro", "estrutura respeita a constituição"],
                    "verify_command": verify_command,
                    "priority": "P1",
                    "story_points": 1,
                })

        # RF-013 — fonte única de verdade. Antes a receita inteira era COPIADA
        # para dentro do spec.md, criando duas cópias editáveis que divergiam em
        # silêncio: alguém corrigia o `.md` da stack e o spec seguia com a versão
        # velha, ou o contrário. Agora o spec REFERENCIA o arquivo, com hash do
        # conteúdo para tornar a divergência detectável, e quem executa lê o
        # original — que é também de onde saem generator e verifier.
        digest = hashlib.sha256(scaffold_md.read_bytes()).hexdigest()[:16]
        scaffold_rel = scaffold_md.relative_to(REPO_ROOT).as_posix()
        componente = _component_type(stack)
        spec_sections.append(
            f"## {anchor}\n\n"
            f"> **Conteúdo derivado — não editar aqui.** A receita determinística\n"
            f"> desta stack vive em `{scaffold_rel}` e é executada pelo generator\n"
            f"> declarado no front-matter daquele arquivo. Editar esta seção não\n"
            f"> muda o que a esteira gera.\n\n"
            f"| Campo | Valor |\n|---|---|\n"
            f"| component_type | `{componente}` |\n"
            f"| stack | `{stack}` |\n"
            f"| receita | `{scaffold_rel}` |\n"
            f"| sha256 (16) | `{digest}` |\n"
            f"| destino | `source-code/{componente}/` |\n"
            f"| verificação | `{verify_command}` |\n"
        )
        plan_rows.append(
            f"| {group} | {stack} | Executar receita CLI da seção `{anchor}` da spec | "
            f"— | `{verify_command}` |"
        )
        generated.append({
            "stack": stack,
            "feature": feature,
            "task_id": task_id,
            "group": group,
            "verify_command": verify_command,
            "scaffold_md": str(scaffold_md.relative_to(REPO_ROOT)),
            "feature_dir": str(feature_dir.relative_to(root)),
        })

    if write:
        plan_graph_path.write_text(
            json.dumps(plan_graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        fragment_path.write_text(
            json.dumps(task_fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        spec_text = spec_path.read_text(encoding="utf-8")
        for section in spec_sections:
            heading = section.splitlines()[0]
            if heading not in spec_text:
                spec_text += "\n\n" + section
        spec_path.write_text(spec_text.rstrip() + "\n", encoding="utf-8")
        plan_text = plan_path.read_text(encoding="utf-8")
        marker = "## Scaffold determinístico da Foundation"
        if marker not in plan_text:
            plan_text += (
                f"\n\n{marker}\n\n"
                "| Grupo | Stack alvo | Escopo | Depende de | Verificação |\n"
                "|---|---|---|---|---|\n" + "\n".join(plan_rows) + "\n"
            )
        plan_path.write_text(plan_text, encoding="utf-8")

    return generated


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inject deterministic scaffold tasks into the W0 Foundation feature."
    )
    parser.add_argument("--project", required=True, help="Nome do projeto")
    parser.add_argument("--json", action="store_true", help="Emitir resultado como JSON")
    args = parser.parse_args(argv)

    try:
        generated = inject_scaffold_specs(args.project)
    except ScaffoldInjectorError as exc:
        print(f"[f4s-scaffold-injector] ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"generated": generated}, ensure_ascii=False, indent=2))
    else:
        print(f"[f4s-scaffold-injector] {len(generated)} scaffold spec(s) gerados:")
        for item in generated:
            print(f"  - {item['feature']} ({item['stack']}) -> {item['task_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
