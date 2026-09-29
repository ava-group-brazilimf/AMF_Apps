#!/usr/bin/env python3
"""Gera deterministicamente a foundation .NET da F4S via .NET CLI."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

import proc_stream
import short_path_root as spr
from scaffold_paths import ScaffoldPathError


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
TEMPLATE_DIR = REPO_ROOT / "src" / "shared" / "templates" / "dotnet-scaffold"
BLUEPRINTS = (
    Path("outputs/tobe/docs/architecture-blueprint.md"),
    Path("outputs/tobe/architecture-blueprint.md"),
)
CommandExecutor = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


#: Limite clássico de caminho do Windows. `Path.is_file()` não levanta erro
#: quando o caminho passa disso — devolve False, como se o arquivo não
#: existisse. Foi assim que a F4S produziu o `dotnet new … (73)` incompreensível
#: em 2026-08-26: o .csproj de 267 chars existia, `is_file()` dizia que não, o
#: scaffold mandava criar de novo e o `dotnet new` — que usa API long-path —
#: recusava sobrescrever (exit 73 = DestructiveChangesDetected).
WINDOWS_MAX_PATH = 260

#: Folga para o que o MSBuild acrescenta por baixo do .csproj durante o build:
#: `obj/Debug/net10.0/ref/<assembly>.dll` e afins. Medido: ~35 chars. Um csproj
#: que cabe em 260 mas estoura com a folga gera solution que NÃO compila — e
#: reprovar no scaffold é melhor que reprovar no verifier, sem diagnóstico.
MSBUILD_PATH_HEADROOM = 35


class ScaffoldError(Exception):
    """Erro que impede o scaffold."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ScaffoldError("pyyaml nao esta instalado")
    if not path.is_file():
        raise ScaffoldError(f"arquivo ausente: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScaffoldError(f"falha ao ler {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def _words(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    parts: list[str] = []
    for chunk in re.split(r"[-_\s]+", normalized.strip()):
        parts.extend(re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", chunk))
    return [part for part in parts if part]


def to_pascal(value: str) -> str:
    return "".join(part[:1].upper() + part[1:].lower() for part in _words(value))


def load_versions(template_dir: Path = TEMPLATE_DIR) -> dict[str, Any]:
    return _read_yaml(template_dir / "versions.yaml")


def _config_value(config: dict[str, Any], key: str) -> str:
    overrides = config.get("overrides")
    if isinstance(overrides, dict):
        nested = overrides.get("tobe_stack")
        if isinstance(nested, dict) and nested.get(key) is not None:
            return str(nested[key]).strip()
        if overrides.get(key) is not None:
            return str(overrides[key]).strip()
    stack = config.get("tobe_stack")
    return str(stack.get(key) or "").strip() if isinstance(stack, dict) else ""


def _to_tfm(value: str) -> str:
    match = re.search(r"(?:net)?\s*(\d+)(?:\.(\d+))?", value, re.IGNORECASE)
    if not match:
        raise ScaffoldError(f"backend_version ilegivel: {value!r}")
    return f"net{match.group(1)}.{match.group(2) or '0'}"


def _matrix_for_tfm(versions: dict[str, Any], tfm: str) -> dict[str, Any] | None:
    tfms = versions.get("tfms")
    if isinstance(tfms, dict) and isinstance(tfms.get(tfm), dict):
        return tfms[tfm]
    majors = versions.get("majors")
    major = tfm.removeprefix("net")
    return majors.get(major) if isinstance(majors, dict) and isinstance(majors.get(major), dict) else None


def _supported_tfms(versions: dict[str, Any]) -> list[str]:
    if isinstance(versions.get("tfms"), dict):
        return sorted(str(key) for key in versions["tfms"])
    majors = versions.get("supported_majors") or (versions.get("majors") or {}).keys()
    return sorted(f"net{major}" for major in majors)


def resolve_target(config: dict[str, Any], versions: dict[str, Any],
                   tfm_override: str | None, sdk_override: str | None) -> tuple[str, str, dict[str, Any]]:
    raw_tfm = tfm_override or _config_value(config, "backend_version")
    if not raw_tfm:
        raw_tfm = str(versions.get("default_tfm") or versions.get("default_major") or "")
    tfm = _to_tfm(raw_tfm)
    matrix = _matrix_for_tfm(versions, tfm)
    if matrix is None:
        raise ScaffoldError(
            f"TFM {tfm} nao e suportado por este scaffold. "
            f"TFMs suportados: {', '.join(_supported_tfms(versions)) or '<nenhum>'}.")
    da_matriz = str(matrix.get("sdk") or matrix.get("sdk_version") or "")
    sdk = sdk_override or _config_value(config, "dotnet_sdk_version") or da_matriz
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", sdk):
        # A mensagem precisa nomear a correção. `global.json` exige versão
        # exata de tres partes em `sdk.version`; a flutuacao de SDK e expressa
        # por `rollForward`, que o scaffold ja escreve como `latestFeature`.
        # Logo `10.0.x` nao e "quase certo": e a gramatica errada, e um
        # global.json com esse valor faz o proprio `dotnet` falhar ao ler.
        raise ScaffoldError(
            f"dotnet_sdk_version invalida: {sdk!r}. global.json exige versao "
            f"exata MAJOR.MINOR.PATCH (ex.: {da_matriz or '10.0.100'}) — a "
            "forma 'MAJOR.MINOR.x' nao existe em global.json; quem faz o SDK "
            "flutuar e rollForward=latestFeature, que este scaffold ja escreve. "
            "Corrija tobe_stack.dotnet_sdk_version em "
            "projects/<projeto>/context/project-config.yaml, ou remova a chave "
            f"para herdar {da_matriz!r} de "
            "src/shared/templates/dotnet-scaffold/versions.yaml.")
    return tfm, sdk, matrix


def extract_bcs(blueprint: str) -> list[str]:
    found: list[str] = []
    for table in re.findall(r"(?:^\|.*\|\s*$\n?)+", blueprint, re.MULTILINE):
        rows = [line.strip().strip("|") for line in table.splitlines() if line.strip()]
        if len(rows) < 3:
            continue
        header = [cell.strip().lower() for cell in rows[0].split("|")]
        column = next((index for index, cell in enumerate(header)
                       if "to-be" in cell and "module" in cell), None)
        if column is None:
            column = next((index for index, cell in enumerate(header)
                           if cell in {"name", "nome"}), None)
        if column is None:
            continue
        for row in rows[2:]:
            cells = [cell.strip() for cell in row.split("|")]
            if len(cells) > column:
                found.append(cells[column].replace("*", "").strip())
        if found:
            break
    if not found:
        summary = re.search(r"\|\s*Bounded contexts\s*\|\s*\d*\s*\(([^)]+)\)", blueprint, re.I)
        found = [item.strip() for item in summary.group(1).split(",")] if summary else []
    result: list[str] = []
    for value in found:
        normalized = to_pascal(value.split(".")[-1])
        if normalized and normalized.lower() not in {"shared", "sharedkernel", "na"} and normalized not in result:
            result.append(normalized)
    return result


def resolve_bcs(project_dir: Path, override: str | None) -> list[str]:
    if override:
        bcs = [to_pascal(value) for value in override.split(",") if value.strip()]
        if bcs and all(bcs):
            return bcs
        raise ScaffoldError("--bcs nao contem nomes validos")
    for relative in BLUEPRINTS:
        path = project_dir / relative
        if path.is_file():
            bcs = extract_bcs(path.read_text(encoding="utf-8", errors="replace"))
            if bcs:
                return bcs
    raise ScaffoldError("nao foi possivel derivar bounded contexts; use --bcs vendas,estoque")


def build_layout(prefix: str, bcs: list[str]) -> list[dict[str, str]]:
    projects = [{
        "template": "classlib", "name": f"{prefix}.SharedKernel",
        "relative": f"src/SharedKernel/{prefix}.SharedKernel", "folder": "src/SharedKernel",
    }]
    for bc in bcs:
        for layer, template, base in (
            ("Domain", "classlib", "src"), ("Application", "classlib", "src"),
            ("Infrastructure", "classlib", "src"), ("Api", "webapi", "src"),
            ("Domain.Tests", "xunit", "tests"), ("Application.Tests", "xunit", "tests"),
        ):
            name = f"{prefix}.{bc}.{layer}"
            projects.append({"template": template, "name": name,
                             "relative": f"{base}/{bc}/{name}", "folder": f"{base}/{bc}"})
    for project in projects:
        project["csproj"] = f"{project['relative']}/{project['name']}.csproj"
    return projects


def _existe(path: Path) -> bool:
    """Alias local de `short_path_root.path_exists` — ver o porquê lá."""
    return spr.path_exists(path)


def _traduzir_registros(registros: list[dict[str, Any]], curta: Path, real: Path) -> None:
    """Reescreve o log de comandos da raiz curta para a raiz de verdade.

    O registro de `argv`/`cwd` é o rastro de auditoria do que a F4S executou.
    Deixá-lo apontando para `Z:\\...` documenta uma unidade que deixou de
    existir no instante em que a geração terminou — irreproduzível para quem
    ler depois. Sem contorno ativo `curta == real` e nada muda.
    """
    if curta == real:
        return
    de, para = str(curta), str(real).rstrip("\\/") + "\\"
    for registro in registros:
        registro["argv"] = [str(item).replace(de, para) for item in registro.get("argv", [])]
        registro["cwd"] = str(registro.get("cwd", "")).replace(de, para)


def _erro_caminho_longo(pior: Path, root: Path) -> str:
    """Reprovacao quando nem o contorno por raiz curta foi possivel.

    A mensagem nomeia as quatro saidas em ordem de preferencia. Sem isso o
    operador recebe um `dotnet new (73)` que nao menciona comprimento de
    caminho em momento algum.
    """
    excesso = len(str(pior)) - spr.WINDOWS_MAX_PATH
    partes = [
        f"caminho longo demais para este Windows: o .csproj mais fundo tem "
        f"{len(str(pior))} chars, contra o limite de {spr.WINDOWS_MAX_PATH}. "
        f"Excesso: {excesso} chars — e nao ha letra de unidade livre para o "
        f"contorno automatico por raiz curta (subst).",
        f"  pior caminho: {pior}",
        f"  raiz do backend: {len(str(root))} chars",
        "Correcoes, em ordem de preferencia:",
        "  1. Habilitar caminhos longos (resolve para toda a esteira, exige "
        "admin + reinicio):",
        r"     Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control"
        r"\FileSystem' LongPathsEnabled 1",
        "  2. Liberar uma letra de unidade (Z:, Y:, X:, W:, V:, U: ou T:) "
        "para o contorno automatico por raiz curta.",
        f"  3. Mover o repositorio para uma raiz mais curta — encurtar a raiz "
        f"em {excesso} chars ja resolve (ex.: C:" + "\\" + "ava).",
        "  4. Encurtar project_name ou os nomes de Bounded Context, que "
        "entram duas vezes em cada caminho (pasta + arquivo).",
    ]
    return "\n".join(partes)


#: Teto por invocação do `dotnet`. Rede de segurança contra travamento
#: individual (NuGet sem rede, MSBuild em deadlock de node reuse), não
#: estimativa: nenhum `dotnet new`/`add`/`sln` legítimo chega perto disso.
#: Antes não havia teto nenhum aqui — um comando pendurado pendurava a fase
#: inteira, e quem morria era o processo pai, sem dizer em qual comando parou.
DOTNET_COMMAND_TIMEOUT_S = 600


def _execute(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # stdout deste processo é o JSON do contrato — por isso o log do `dotnet`
    # sai pelo stderr, que o `scaffold_runner` transmite ao vivo. Capturar
    # continua valendo: os dois fluxos vão inteiros para `commands[]`.
    # As sondas `dotnet new <t> --help` existem só para descobrir quais flags
    # este SDK aceita: são 4 telas de ajuda que não dizem nada sobre progresso.
    # Capturadas sim (o código as consulta), ecoadas não.
    sonda = "--help" in command
    return proc_stream.run(command, cwd=cwd, timeout_s=DOTNET_COMMAND_TIMEOUT_S,
                           prefix="      ", stream=sys.stderr,
                           echo_stdout=not sonda, echo_stderr=not sonda)


class Runner:
    def __init__(self, executor: CommandExecutor, records: list[dict[str, Any]]) -> None:
        self.executor, self.records = executor, records

    def run(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        # Um scaffold de 13 bounded contexts dispara ~280 invocações do
        # `dotnet`. Sem esta linha o operador vê 14 minutos de nada e não tem
        # como saber se o processo avança ou travou.
        inicio = time.monotonic()
        print(f"    $ {' '.join(command)}", file=sys.stderr, flush=True)
        try:
            result = self.executor(command, cwd)
        except FileNotFoundError as exc:
            raise ScaffoldError(f"comando nao encontrado: {command[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ScaffoldError(
                f"comando excedeu {exc.timeout}s: {' '.join(command)}") from exc
        print(f"      -> exit {result.returncode} "
              f"({time.monotonic() - inicio:.1f}s)", file=sys.stderr, flush=True)
        self.records.append({"argv": command, "cwd": str(cwd), "exit_code": result.returncode,
                             "stdout": result.stdout or "", "stderr": result.stderr or ""})
        if result.returncode:
            output = "\n".join((result.stderr or result.stdout or "").splitlines()[-20:])
            raise ScaffoldError(f"comando falhou ({result.returncode}): {' '.join(command)}\n{output}")
        return result


def _write(path: Path, content: str, root: Path, force: bool,
           written: list[str], skipped: list[str]) -> None:
    relative = path.relative_to(root).as_posix()
    if path.exists() and not force:
        skipped.append(relative)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    written.append(relative)


def _global_json(sdk: str) -> str:
    return json.dumps({"sdk": {"version": sdk, "rollForward": "latestFeature",
                                "allowPrerelease": False}}, indent=2) + "\n"


def _build_props(tfm: str, matrix: dict[str, Any],
                 *, redirect_output: bool = False,
                 short_path_root: str = "C:\\avaout") -> str:
    lang_version = str(matrix.get("lang_version") or "latest")
    redirect_block = ""
    target_block = ""
    if redirect_output:
        # Normaliza para barras simples; MSBuild aceita '\' e evita o escape
        # duplo exigido por f-string + XML.
        root = short_path_root.rstrip("\\/").replace("/", "\\")
        redirect_block = (
            '\n    <!-- Redireciona bin/obj para fora do repo encurtando o '
            'caminho total. O target CreateBaseOutputDirs abaixo garante que '
            'o diretorio exista. -->\n'
            f'    <BaseOutputPath Condition="$([MSBuild]::IsOSPlatform(\'Windows\'))">{root}\\\\$(MSBuildProjectName)\\\\bin\\\\</BaseOutputPath>\n'
            f'    <BaseIntermediateOutputPath Condition="$([MSBuild]::IsOSPlatform(\'Windows\'))">{root}\\\\$(MSBuildProjectName)\\\\obj\\\\</BaseIntermediateOutputPath>'
        )
        target_block = (
            '\n\n  <Target Name="CreateBaseOutputDirs" '
            'BeforeTargets="BeforeBuild" '
            'Condition="$([MSBuild]::IsOSPlatform(\'Windows\'))">\n'
            '    <MakeDir Directories="$(BaseOutputPath);$(BaseIntermediateOutputPath)" />\n'
            '  </Target>'
        )
    return f"""<Project>
  <PropertyGroup>
    <TargetFramework>{tfm}</TargetFramework>
    <LangVersion>{lang_version}</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <WarningsAsErrors></WarningsAsErrors>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>{redirect_block}
  </PropertyGroup>{target_block}
</Project>
"""


def _central_versions(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ScaffoldError(f"Directory.Packages.props invalido: {exc}") from exc
    return {node.attrib["Include"]: node.attrib["Version"] for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == "PackageVersion"
            and node.attrib.get("Include") and node.attrib.get("Version")}


def _normalize_cpm(projects: list[Path], versions: dict[str, str], root: Path) -> list[str]:
    updated: list[str] = []
    for path in projects:
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise ScaffoldError(f"projeto gerado invalido: {path}: {exc}") from exc
        changed = False
        for node in tree.getroot().iter():
            if node.tag.rsplit("}", 1)[-1] != "PackageReference":
                continue
            package, version = node.attrib.get("Include"), node.attrib.get("Version")
            if not package:
                continue
            if version:
                if package in versions and versions[package] != version:
                    raise ScaffoldError(f"versoes conflitantes para {package}")
                versions[package] = version
                del node.attrib["Version"]
                changed = True
            elif package not in versions:
                raise ScaffoldError(f"PackageReference sem PackageVersion central: {package}")
        if changed:
            if hasattr(ET, "indent"):
                ET.indent(tree, space="  ")
            tree.write(path, encoding="utf-8", xml_declaration=False)
            updated.append(path.relative_to(root).as_posix())
    return updated


def _packages_props(versions: dict[str, str]) -> str:
    lines = ["<Project>", "  <PropertyGroup>",
             "    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>",
             "  </PropertyGroup>", "  <ItemGroup>"]
    lines.extend(f'    <PackageVersion Include="{package}" Version="{version}" />'
                 for package, version in sorted(versions.items(), key=lambda item: item[0].lower()))
    return "\n".join([*lines, "  </ItemGroup>", "</Project>", ""])


def _has_reference(consumer: Path, provider: Path) -> bool:
    try:
        project = ET.parse(consumer).getroot()
    except ET.ParseError as exc:
        raise ScaffoldError(f"projeto invalido: {consumer}: {exc}") from exc
    return any((consumer.parent / node.attrib["Include"]).resolve() == provider.resolve()
               for node in project.iter() if node.tag.rsplit("}", 1)[-1] == "ProjectReference"
               and node.attrib.get("Include"))


def _references(layout: list[dict[str, str]], root: Path, bcs: list[str]) -> list[tuple[Path, Path]]:
    paths = {item["name"]: root / item["csproj"] for item in layout}
    prefix = layout[0]["name"].removesuffix(".SharedKernel")
    pairs: list[tuple[Path, Path]] = []
    for bc in bcs:
        domain = paths[f"{prefix}.{bc}.Domain"]
        application = paths[f"{prefix}.{bc}.Application"]
        infrastructure = paths[f"{prefix}.{bc}.Infrastructure"]
        api = paths[f"{prefix}.{bc}.Api"]
        pairs.extend([
            (domain, paths[f"{prefix}.SharedKernel"]), (application, domain),
            (infrastructure, application), (infrastructure, domain), (api, application),
            (api, infrastructure), (paths[f"{prefix}.{bc}.Domain.Tests"], domain),
            (paths[f"{prefix}.{bc}.Application.Tests"], application),
            (paths[f"{prefix}.{bc}.Application.Tests"], domain),
        ])
    return pairs


def scaffold(project: str, workspace: Path, *, app_root: Path | None = None,
             output_path: Path | None = None,
             bcs_override: str | None = None, tfm_override: str | None = None,
             sdk_override: str | None = None, solution_prefix_override: str | None = None,
             force: bool = False, executor: CommandExecutor = _execute) -> dict[str, Any]:
    project_dir = workspace / "projects" / project
    if not project_dir.is_dir():
        raise ScaffoldError(f"projeto nao encontrado: {project_dir}")
    config = _read_yaml(project_dir / "context" / "project-config.yaml")
    tfm, sdk, matrix = resolve_target(config, load_versions(), tfm_override, sdk_override)
    bcs = resolve_bcs(project_dir, bcs_override)
    prefix = to_pascal(solution_prefix_override or str(config.get("project_name") or project))
    if not prefix:
        raise ScaffoldError("solution_prefix vazio apos normalizacao")
    canonical_root = project_dir / "outputs" / "tobe" / "source-code" / "backend"
    if app_root is not None and output_path is not None:
        raise ScaffoldPathError("use apenas app_root ou output_path")
    if output_path is not None and output_path.resolve() != canonical_root.resolve():
        raise ScaffoldPathError(
            "destino derivado da tecnologia nao corresponde ao backend canônico")
    root = app_root or output_path or canonical_root
    # A raiz REAL, guardada antes de qualquer remapeamento: e ela que vai no
    # relatorio. Um JSON dizendo `Z:	ests\...` descreve uma unidade que ja nao
    # existe quando alguem for ler.
    raiz_real = root
    layout = build_layout(prefix, bcs)
    warnings: list[str] = []

    # Orcamento de caminho ANTES de qualquer escrita. Estourado, tentamos o
    # contorno determinístico (raiz curta via subst); so reprovamos se nem
    # isso for possivel. Ver src/shared/tools/short_path_root.py.
    pior = spr.budget_exceeded([root / item['csproj'] for item in layout],
                               headroom=MSBUILD_PATH_HEADROOM)

    # Configuracao de redirecionamento de bin/obj (opt-in, condicional).
    build_output = config.get("build_output") or {}
    redirect_enabled = bool(build_output.get("redirect_to_short_path"))
    condition = str(build_output.get("condition") or "max_path_risk").lower()
    short_path_root = str(build_output.get("short_path_root") or r"C:\avaout")
    max_path_risk = pior is not None
    apply_redirect = redirect_enabled and condition != "never" and (
        condition == "always" or (condition == "max_path_risk" and max_path_risk)
    )
    if apply_redirect and max_path_risk:
        warnings.append(
            f"risco de MAX_PATH detectado ({len(str(pior))} chars); "
            f"redirecionando bin/obj para {short_path_root} conforme "
            f'build_output.condition="{condition}".'
        )
    elif apply_redirect and condition == "always":
        warnings.append(
            f"bin/obj redirecionados para {short_path_root} "
            f'(build_output.condition="always").'
        )

    with spr.short_root(root, needed=pior is not None) as (trabalho, letra):
        if pior is not None and letra is None:
            raise ScaffoldError(_erro_caminho_longo(pior, root))
        if letra is not None:
            warnings.append(
                f'caminho acima de MAX_PATH ({len(str(pior))} chars); gerado '
                f'atraves da raiz curta {letra}: (subst). Os arquivos nasceram no '
                f'caminho real, com os nomes de sempre — a unidade so existiu '
                f'durante a geracao. Correcao definitiva: LongPathsEnabled=1.')
        root = trabalho

        root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        skipped: list[str] = []
        commands: list[dict[str, Any]] = []
        runner = Runner(executor, commands)

        _write(root / "global.json", _global_json(sdk), root, force, written, skipped)
        _write(root / "Directory.Build.props",
               _build_props(tfm, matrix, redirect_output=apply_redirect,
                            short_path_root=short_path_root),
               root, force, written, skipped)
        _write(root / ".gitignore", "bin/\nobj/\n.vs/\n.artifacts/\n", root, force, written, skipped)
        help_output = {template: runner.run(["dotnet", "new", template, "--help"], root).stdout
                       for template in ("sln", "classlib", "webapi", "xunit")}

        solution = root / f"{prefix}.sln"
        if not solution.is_file():
            command = ["dotnet", "new", "sln", "--name", prefix, "--output", "."]
            if "--format" in help_output["sln"]:
                command.extend(["--format", "sln"])
            runner.run(command, root)
            if not solution.is_file():
                raise ScaffoldError(f"dotnet new sln nao produziu {solution.name}")
            written.append(solution.name)
        else:
            skipped.append(solution.name)

        generated: list[Path] = []
        for item in layout:
            csproj = root / item["csproj"]
            if _existe(csproj) and not force:
                skipped.append(csproj.relative_to(root).as_posix())
                continue
            command = ["dotnet", "new", item["template"], "--name", item["name"], "--output",
                       item["relative"], "--framework", tfm, "--no-restore"]
            if item["template"] == "webapi" and "--no-openapi" in help_output["webapi"]:
                command.append("--no-openapi")
            # `--force` do scaffold precisa chegar ao `dotnet new`: sem isso a
            # retentativa sobre um diretorio parcial reprova com exit 73
            # (DestructiveChangesDetected) as tres vezes, identicamente, e o
            # operador tem de apagar a arvore na mao para destravar.
            if force and _existe(csproj):
                command.append("--force")
            runner.run(command, root)
            if not _existe(csproj):
                raise ScaffoldError(f"template {item['template']} nao produziu {csproj}")
            written.append(csproj.relative_to(root).as_posix())
            generated.append(csproj)

        package_file = root / "Directory.Packages.props"
        package_versions = {str(package): str(version)
                            for package, version in (matrix.get("packages") or {}).items()}
        package_versions.update(_central_versions(package_file))
        updated = _normalize_cpm(generated, package_versions, root)
        _write(package_file, _packages_props(package_versions), root, force, written, skipped)

        for consumer, provider in _references(layout, root, bcs):
            if not _has_reference(consumer, provider):
                runner.run(["dotnet", "add", str(consumer), "reference", str(provider)], root)

        solution_text = solution.read_text(encoding="utf-8", errors="replace")
        for item in layout:
            csproj = root / item["csproj"]
            if item["name"] not in solution_text:
                runner.run(["dotnet", "sln", str(solution), "add", str(csproj),
                            "--solution-folder", item["folder"]], root)
                solution_text += item["name"]

    _traduzir_registros(commands, root, raiz_real)
    return {"success": True, "status": "PASS", "stack": "dotnet",
            "component_type": "backend", "phase": "generation",
            "app_root": raiz_real.as_posix(), "output_path": raiz_real.as_posix(),
            "solution": solution.name,
            "solution_prefix": prefix, "tfm": tfm, "sdk": sdk, "bcs": bcs,
            "files_written": written, "files_skipped": skipped, "files_updated": updated,
            "commands": commands, "warnings": warnings, "error": None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera deterministicamente o scaffold .NET da F4S")
    parser.add_argument("--project", required=True)
    parser.add_argument("--workspace", default=str(REPO_ROOT))
    parser.add_argument("--root", default=None)
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--bcs", default=None)
    parser.add_argument("--tfm", default=None)
    parser.add_argument("--sdk", default=None)
    parser.add_argument("--solution-prefix", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.root and args.output_path and Path(args.root).resolve() != Path(args.output_path).resolve():
        parser.error("--root e --output-path apontam para destinos diferentes")
    try:
        result = scaffold(args.project, Path(args.workspace).resolve(),
                          app_root=Path(args.root).resolve() if args.root else None,
                          output_path=Path(args.output_path).resolve() if args.output_path else None,
                          bcs_override=args.bcs, tfm_override=args.tfm, sdk_override=args.sdk,
                          solution_prefix_override=args.solution_prefix, force=args.force)
    except ScaffoldError as exc:
        result = {"success": False, "status": "ERROR", "error": str(exc),
                  "files_written": [], "files_skipped": []}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[f4s-dotnet-scaffold] ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[f4s-dotnet-scaffold] PASS - {result['solution']} ({result['tfm']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())