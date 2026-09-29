#!/usr/bin/env python3
"""
f4s_angular_scaffold.py — gerador determinístico do scaffold Angular (spec 042).

Renderiza a árvore versionada em `src/shared/templates/angular-scaffold/` sobre
`projects/{project}/outputs/tobe/source-code/frontend/`, produzindo um workspace
que compila na primeira tentativa.

O destino vem de `scaffold_paths.resolve_source_code_path("frontend")`: o
diretório é definido pela responsabilidade do componente, nunca pela stack.

Substitui a geração interpretativa por um agente LLM a partir de prosa. O agente
continua responsável pelas features de cada bounded context — mas só depois que este
scaffold passou no gate de compilação.

Uso:
    python src/shared/tools/f4s_angular_scaffold.py --project Meu-ERP --json
    python src/shared/tools/f4s_angular_scaffold.py --project Meu-ERP --bcs vendas,estoque
    python src/shared/tools/f4s_angular_scaffold.py --project Meu-ERP --force

Saída (JSON em stdout):
    {
      "status": "PASS" | "ERROR",
      "app_root": "/abs/path",
      "app_name": "meu-erp",
      "angular_major": "17",
      "bcs": ["vendas", "estoque"],
      "files_written": [...],
      "files_skipped": [...],
      "error": null
    }

Exit codes:
    0 — PASS
    2 — ERROR (config inválida, major não suportado, BC indeterminável, template ausente)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover — pyyaml está disponível no venv do repo
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
TEMPLATE_DIR = REPO_ROOT / "src" / "shared" / "templates" / "angular-scaffold"

sys.path.insert(0, str(SCRIPT_DIR))
from scaffold_paths import resolve_output_dir, validate_output_dir  # noqa: E402

#: Diretório-molde renderizado uma vez por bounded context.
BC_TEMPLATE_DIRNAME = "_bc"

#: Delimitador de token. Deliberadamente NÃO é chave dupla: os templates contêm
#: interpolação de template do Angular, e os dois delimitadores colidiriam.
TOKEN_RE = re.compile(r"%%([a-z][a-z0-9_]*)%%")


class ScaffoldError(Exception):
    """Erro fatal do gerador; o CLI trata como exit 2."""


# ─── helpers de nomenclatura ────────────────────────────────────────────────────


def _words(name: str) -> list[str]:
    """Quebra um identificador em palavras, aceitando kebab, snake, espaço e camel."""
    parts: list[str] = []
    for chunk in re.split(r"[-_\s]+", name.strip()):
        if not chunk:
            continue
        # Quebra camelCase/PascalCase preservando siglas (APIGateway -> API, Gateway).
        parts.extend(re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", chunk))
    return [p for p in parts if p]


def to_kebab(name: str) -> str:
    return "-".join(w.lower() for w in _words(name))


def to_pascal(name: str) -> str:
    return "".join(w[:1].upper() + w[1:].lower() for w in _words(name))


def to_camel(name: str) -> str:
    pascal = to_pascal(name)
    return pascal[:1].lower() + pascal[1:] if pascal else ""


def to_title(name: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in _words(name))


# ─── leitura de configuração ────────────────────────────────────────────────────


def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ScaffoldError("pyyaml não está instalado — necessário para ler YAML")
    if not path.is_file():
        raise ScaffoldError(f"arquivo ausente: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ScaffoldError(f"falha ao ler {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def load_versions(template_dir: Path = TEMPLATE_DIR) -> dict[str, Any]:
    return _read_yaml(template_dir / "versions.yaml")


def resolve_major(project_config: dict[str, Any], versions: dict[str, Any]) -> str:
    """Resolve o major do Angular. Major não mapeado reprova — nunca adivinha.

    Article I: a versão vem de `project-config.yaml`; a matriz vive em `versions.yaml`.
    """
    raw = ""
    tobe = project_config.get("tobe_stack")
    if isinstance(tobe, dict):
        raw = str(tobe.get("frontend_version") or "").strip()

    if not raw:
        raw = str(versions.get("default_major") or "").strip()
    if not raw:
        raise ScaffoldError(
            "não foi possível resolver o major do Angular: "
            "`tobe_stack.frontend_version` ausente em project-config.yaml e "
            "`default_major` ausente em versions.yaml"
        )

    # Aceita "17", "17.3", "^17.3.0", "v17".
    match = re.search(r"\d+", raw)
    if not match:
        raise ScaffoldError(f"versão de frontend ilegível: {raw!r}")
    major = match.group(0)

    majors = versions.get("majors") or {}
    if major not in majors:
        supported = ", ".join(sorted(majors, key=int))
        raise ScaffoldError(
            f"Angular major {major} não é suportado por este scaffold. "
            f"Majors suportados: {supported}. "
            "Para adicionar um novo, estenda "
            "src/shared/templates/angular-scaffold/versions.yaml — "
            "o gerador nunca adivinha versões de dependência."
        )
    return major


# ─── bounded contexts ───────────────────────────────────────────────────────────

#: Nomes que aparecem na coluna TO-BE mas não são bounded contexts de aplicação.
_BC_STOPWORDS = {"shared kernel", "sharedkernel", "shared", "n/a", "-", ""}


def _blueprint_candidates(project_dir: Path) -> list[Path]:
    """Retorna as fontes TO-BE que podem declarar os bounded contexts.

    Algumas versões publicam o mapa de BCs em um artefato separado do
    blueprint arquitetural. O blueprint permanece a fonte primária.
    """
    tobe = project_dir / "outputs" / "tobe"
    return [
        tobe / "docs" / "architecture-blueprint.md",
        tobe / "architecture-blueprint.md",
        tobe / "docs" / "bounded-context-map.md",
        tobe / "bounded-context-map.md",
    ]


def extract_bcs(blueprint_text: str) -> list[str]:
    """Extrai bounded contexts do architecture-blueprint.md.

    Quatro estratégias, na ordem de confiabilidade observada nos artefatos reais:

    1. A tabela sob o heading "Bounded Context Map": a coluna "TO-BE Module" traz
       os nomes em negrito.
     2. A tabela sob o heading "Bounded Contexts TO-BE" com a coluna "Name"
         ou "Nome", emitida por versões anteriores do architecture blueprint.
     3. A linha de resumo `| Bounded contexts | 2 (Identity, DataManagement) |`.
     4. Headings `## BC-01: Nome`, usados pelo bounded-context-map.md detalhado.

    Devolve [] quando nada é reconhecido — o chamador decide se isso reprova.
    """
    found: list[str] = []

    # Estratégia 1 — tabela do Bounded Context Map.
    section = re.search(
        r"^#{1,4}\s*[\d.\s]*Bounded Context Map.*?$(.*?)(?=^#{1,4}\s|\Z)",
        blueprint_text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if section:
        rows = [ln for ln in section.group(1).splitlines() if ln.strip().startswith("|")]
        header_idx: int | None = None
        col_idx: int | None = None
        for i, row in enumerate(rows):
            cells = [c.strip().lower() for c in row.strip().strip("|").split("|")]
            for j, cell in enumerate(cells):
                if "to-be" in cell and "module" in cell:
                    header_idx, col_idx = i, j
                    break
            if header_idx is not None:
                break
        if header_idx is not None and col_idx is not None:
            for row in rows[header_idx + 1:]:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if len(cells) <= col_idx:
                    continue
                value = cells[col_idx].replace("*", "").strip()
                if value.lower() in _BC_STOPWORDS or set(value) <= {"-", ":", " "}:
                    continue
                found.append(value)

    # Estratégia 2 — tabela legada de Bounded Contexts TO-BE.
    if not found:
        section = re.search(
            r"^#{1,4}\s*[\d.\s]*Bounded Contexts(?:\s+TO-BE)?.*?$(.*?)(?=^#{1,4}\s|\Z)",
            blueprint_text,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        if section:
            rows = [ln for ln in section.group(1).splitlines() if ln.strip().startswith("|")]
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
                if len(cells) < 2:
                    continue
                value = cells[1].replace("*", "").strip()
                if value.lower() not in _BC_STOPWORDS:
                    found.append(value)

    # Estratégia 3 — linha de resumo.
    if not found:
        summary = re.search(
            r"\|\s*Bounded contexts\s*\|\s*\d*\s*\(([^)]+)\)",
            blueprint_text,
            re.IGNORECASE,
        )
        if summary:
            for part in summary.group(1).split(","):
                value = part.replace("*", "").strip()
                if value and value.lower() not in _BC_STOPWORDS:
                    found.append(value)

    # Estratégia 4 — mapa detalhado com um heading por BC.
    if not found:
        for match in re.finditer(
            r"^#{1,4}\s*BC[- ]\d+\s*:\s*(.+?)\s*$",
            blueprint_text,
            re.MULTILINE | re.IGNORECASE,
        ):
            value = match.group(1).replace("*", "").strip()
            if value.lower() not in _BC_STOPWORDS:
                found.append(value)

    # Dedup preservando ordem.
    seen: set[str] = set()
    unique: list[str] = []
    for name in found:
        key = to_kebab(name)
        if key and key not in seen:
            seen.add(key)
            unique.append(name)
    return unique


def resolve_bcs(project_dir: Path, override: str | None) -> list[str]:
    if override:
        names = [n.strip() for n in override.split(",") if n.strip()]
        if not names:
            raise ScaffoldError("--bcs foi informado mas não contém nenhum nome")
        return names

    candidates = _blueprint_candidates(project_dir)
    for path in candidates:
        if path.is_file():
            bcs = extract_bcs(path.read_text(encoding="utf-8", errors="replace"))
            if bcs:
                return bcs

    looked = "\n".join(f"  - {p}" for p in candidates)
    raise ScaffoldError(
        "não foi possível derivar nenhum bounded context do architecture-blueprint.md.\n"
        f"Procurado em:\n{looked}\n"
        "Esperado: uma tabela sob o heading 'Bounded Context Map' com a coluna "
        "'TO-BE Module', um bounded-context-map.md com headings 'BC-N', ou a "
        "linha de resumo '| Bounded contexts | N (A, B) |'.\n"
        "Use --bcs a,b para informar os contextos explicitamente."
    )


# ─── renderização ───────────────────────────────────────────────────────────────


def render(text: str, tokens: dict[str, str], source: str) -> str:
    """Substitui os tokens e reprova se sobrar algum não resolvido.

    Um token remanescente significa template e gerador fora de sincronia — deixar
    passar produziria um arquivo com lixo literal, exatamente a classe de defeito
    que esta spec elimina.
    """
    for key, value in tokens.items():
        text = text.replace(f"%%{key}%%", value)
    leftover = TOKEN_RE.search(text)
    if leftover:
        raise ScaffoldError(
            f"token não resolvido {leftover.group(0)} em {source}; "
            f"tokens disponíveis: {', '.join(sorted(tokens))}"
        )
    return text


def _json_block(mapping: dict[str, str], indent: int) -> str:
    """Serializa um bloco de dependências já indentado para embutir no package.json."""
    raw = json.dumps(mapping, indent=2, ensure_ascii=False)
    pad = " " * indent
    lines = raw.splitlines()
    return "\n".join([lines[0]] + [pad + ln for ln in lines[1:]])


def build_tokens(app_name: str, major: str, versions: dict[str, Any],
                 bcs: list[str]) -> dict[str, str]:
    matrix = versions["majors"][major]

    routes_lines: list[str] = []
    nav_lines: list[str] = []
    for bc in bcs:
        kebab, camel = to_kebab(bc), to_camel(bc)
        routes_lines.append(
            "  {\n"
            f"    path: '{kebab}',\n"
            "    loadChildren: () =>\n"
            f"      import('./features/{kebab}/{kebab}.routes')"
            f".then((m) => m.{camel}Routes),\n"
            "  },"
        )
        nav_lines.append(
            f'        <a routerLink="/{kebab}" routerLinkActive="active">'
            f"{to_title(bc)}</a>"
        )

    return {
        "app_name": app_name,
        "app_title": to_title(app_name),
        "default_route": to_kebab(bcs[0]),
        "dependencies_block": _json_block(matrix["dependencies"], 2),
        "dev_dependencies_block": _json_block(matrix["devDependencies"], 2),
        "bc_routes_block": "\n".join(routes_lines),
        "bc_nav_block": "\n".join(nav_lines),
    }


def bc_tokens(base: dict[str, str], bc: str) -> dict[str, str]:
    return {
        **base,
        "bc_kebab": to_kebab(bc),
        "bc_pascal": to_pascal(bc),
        "bc_camel": to_camel(bc),
        "bc_title": to_title(bc),
    }


def _emit(dest: Path, content: str | bytes, force: bool,
          written: list[str], skipped: list[str], app_root: Path) -> None:
    rel = dest.relative_to(app_root).as_posix()
    if dest.exists() and not force:
        skipped.append(rel)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        dest.write_bytes(content)
    else:
        dest.write_text(content, encoding="utf-8", newline="\n")
    written.append(rel)


def generate(app_root: Path, tokens: dict[str, str], bcs: list[str], force: bool,
             template_dir: Path = TEMPLATE_DIR) -> tuple[list[str], list[str]]:
    """Renderiza a árvore de templates. Idempotente salvo `force`."""
    if not template_dir.is_dir():
        raise ScaffoldError(f"diretório de templates ausente: {template_dir}")

    written: list[str] = []
    skipped: list[str] = []
    bc_dir = template_dir / "src" / "app" / "features" / BC_TEMPLATE_DIRNAME

    for src in sorted(template_dir.rglob("*")):
        if src.is_dir() or src.name == "versions.yaml":
            continue
        if bc_dir in src.parents:
            continue  # renderizado por BC, logo abaixo

        rel = src.relative_to(template_dir)
        if src.suffix == ".tmpl":
            dest = app_root / rel.with_suffix("")
            _emit(dest, render(src.read_text(encoding="utf-8"), tokens, rel.as_posix()),
                  force, written, skipped, app_root)
        else:
            _emit(app_root / rel, src.read_bytes(), force, written, skipped, app_root)

    # Um diretório de feature por bounded context.
    for bc in bcs:
        tok = bc_tokens(tokens, bc)
        target_dir = app_root / "src" / "app" / "features" / tok["bc_kebab"]
        for src in sorted(bc_dir.rglob("*")):
            if src.is_dir():
                continue
            rel = src.relative_to(bc_dir)
            name = render(rel.name, tok, rel.as_posix())
            dest = target_dir / rel.parent / name
            if src.suffix == ".tmpl":
                dest = dest.with_suffix("")
                _emit(dest, render(src.read_text(encoding="utf-8"), tok, rel.as_posix()),
                      force, written, skipped, app_root)
            else:
                _emit(dest, src.read_bytes(), force, written, skipped, app_root)

    return written, skipped


# ─── CLI ────────────────────────────────────────────────────────────────────────


def scaffold(project: str, workspace: Path, app_root: Path | None = None,
             bcs_override: str | None = None, force: bool = False,
             template_dir: Path = TEMPLATE_DIR) -> dict[str, Any]:
    project_dir = workspace / "projects" / project
    if not project_dir.is_dir():
        raise ScaffoldError(f"projeto não encontrado: {project_dir}")

    config = _read_yaml(project_dir / "context" / "project-config.yaml")
    versions = load_versions(template_dir)
    major = resolve_major(config, versions)
    bcs = resolve_bcs(project_dir, bcs_override)

    # O destino é `source-code/frontend/` — definido pela RESPONSABILIDADE do
    # componente, nunca pela stack. Antes era `source-code/angular/`, o que
    # obrigava toda troca de framework a mexer em caminho, e deixava o mesmo
    # projeto com código em dois lugares (o ava-stack-orchestrator já gravava em
    # `frontend/`). Um `--root` explícito continua aceito, mas é validado contra
    # o canônico: não existe rota para escrever fora dele.
    tobe_root = project_dir / "outputs" / "tobe"
    root = (validate_output_dir(Path(app_root), "frontend", tobe_root)
            if app_root else resolve_output_dir(tobe_root, "frontend"))
    root.mkdir(parents=True, exist_ok=True)

    app_name = to_kebab(str(config.get("project_name") or project))
    tokens = build_tokens(app_name, major, versions, bcs)
    written, skipped = generate(root, tokens, bcs, force, template_dir)

    return {
        "success": True,
        "status": "PASS",
        "stack": "angular",
        "component_type": "frontend",
        "phase": "generation",
        "output_path": root.as_posix(),
        "app_root": str(root),
        "app_name": app_name,
        "angular_major": major,
        "bcs": [to_kebab(b) for b in bcs],
        "files_written": written,
        "files_skipped": skipped,
        "error": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera deterministicamente o scaffold Angular de um projeto."
    )
    parser.add_argument("--project", required=True, help="nome do projeto")
    parser.add_argument("--workspace", default=str(REPO_ROOT),
                        help="raiz do workspace que contém projects/ (default: repo)")
    parser.add_argument("--root", default=None,
                        help="app_root explícito; precisa ser o canônico "
                             "source-code/frontend (default: resolvido)")
    parser.add_argument("--bcs", default=None,
                        help="lista de bounded contexts separada por vírgula, "
                             "sobrepondo a derivação do blueprint")
    parser.add_argument("--force", action="store_true",
                        help="sobrescreve arquivos existentes (default: preserva)")
    parser.add_argument("--json", action="store_true", help="saída JSON em stdout")
    args = parser.parse_args(argv)

    try:
        result = scaffold(
            project=args.project,
            workspace=Path(args.workspace).resolve(),
            app_root=Path(args.root).resolve() if args.root else None,
            bcs_override=args.bcs,
            force=args.force,
        )
    except ScaffoldError as exc:
        payload = {"status": "ERROR", "error": str(exc), "files_written": [],
                   "files_skipped": []}
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"[f4s-angular-scaffold] ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"[f4s-angular-scaffold] PASS — Angular {result['angular_major']} em "
              f"{result['app_root']}")
        print(f"  bounded contexts : {', '.join(result['bcs'])}")
        print(f"  arquivos escritos: {len(result['files_written'])}")
        print(f"  preservados      : {len(result['files_skipped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
