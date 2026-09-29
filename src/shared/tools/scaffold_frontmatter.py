#!/usr/bin/env python3
"""Front-matter dos scaffolds como configuração executável — e validada.

`angular-scaffold.md` já declarava `generator:` e `verifier:` desde a spec 042,
e nada os lia: o runner resolvia tudo por dicionário fixo
(`STACK_SCAFFOLD_GENERATORS`) e por `_verify_command_for_stack`. Declarar uma
configuração que o código ignora é pior que não declarar — o Markdown parece a
fonte da verdade sem ser.

Aqui o front-matter passa a ser a fonte. Como isso significa executar um
caminho vindo de arquivo de conteúdo, toda leitura passa por allowlist:
diretório permitido, sufixo permitido, arquivo existente, sem traversal, sem
symlink escapando do repo. Nada é executado a partir de um valor não validado.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover — pyyaml vive no venv do repo
    yaml = None

from scaffold_paths import (
    ScaffoldPathError,
    assert_declared_output_path,
    component_type_for_stack,
    normalize_component_type,
    resolve_source_code_path,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Diretórios de onde um generator/verifier pode ser executado. Um caminho fora
#: destes é rejeitado mesmo que exista e seja legítimo — ampliar a allowlist é
#: decisão consciente, não efeito de editar um Markdown.
ALLOWED_EXECUTABLE_DIRS: tuple[str, ...] = (
    "src/shared/tools",
    "src/shared/utils",
)

#: Só Python. Sem .sh/.ps1/.bat/.exe — o front-matter não vira vetor de comando.
ALLOWED_EXECUTABLE_SUFFIXES: frozenset[str] = frozenset({".py"})

#: Diretórios de onde um template pode ser lido.
ALLOWED_TEMPLATE_DIRS: tuple[str, ...] = ("src/shared/templates",)

#: Campos que todo scaffold precisa declarar.
REQUIRED_FIELDS: tuple[str, ...] = (
    "component_type", "stack", "generator", "verifier", "template_path",
)

#: Campos opcionais reconhecidos. Chave desconhecida é erro — typo em
#: configuração executável não pode passar silenciosamente.
OPTIONAL_FIELDS: tuple[str, ...] = (
    "id", "name", "version_source", "build_command", "manifest",
    "output_path", "description",
)


class FrontMatterError(ValueError):
    """Front-matter ausente, malformado, incompleto ou não autorizado."""


def _split_front_matter(text: str, origem: str) -> dict[str, Any]:
    if not text.startswith("---"):
        raise FrontMatterError(f"{origem}: front-matter YAML ausente (esperado '---' na linha 1)")
    fim = text.find("\n---", 3)
    if fim == -1:
        raise FrontMatterError(f"{origem}: front-matter não fechado com '---'")
    if yaml is None:
        raise FrontMatterError("pyyaml não está instalado")
    try:
        # safe_load: nunca `load`. O arquivo é conteúdo, não código.
        dados = yaml.safe_load(text[3:fim])
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"{origem}: front-matter YAML inválido: {exc}") from exc
    if not isinstance(dados, dict):
        raise FrontMatterError(f"{origem}: front-matter precisa ser um mapa YAML")
    return dados


def _resolve_allowed(valor: Any, campo: str, origem: str, *,
                     allowed_dirs: tuple[str, ...],
                     allowed_suffixes: frozenset[str] | None,
                     must_be_dir: bool,
                     repo_root: Path) -> Path:
    """Resolve um caminho declarado, aceitando-o só sob a allowlist."""
    bruto = str(valor or "").strip()
    if not bruto:
        raise FrontMatterError(f"{origem}: campo `{campo}` vazio")
    normalizado = bruto.replace("\\", "/")
    if normalizado.startswith("/") or (len(normalizado) > 1 and normalizado[1] == ":"):
        raise FrontMatterError(
            f"{origem}: `{campo}` precisa ser relativo à raiz do repo, "
            f"não absoluto: {bruto!r}")
    if ".." in Path(normalizado).parts:
        raise FrontMatterError(
            f"{origem}: `{campo}` contém traversal (`..`): {bruto!r}")

    raiz = repo_root.resolve()
    alvo = (raiz / normalizado).resolve(strict=False)
    try:
        relativo = alvo.relative_to(raiz).as_posix()
    except ValueError as exc:
        raise FrontMatterError(
            f"{origem}: `{campo}` resolve para fora do repositório: {bruto!r}") from exc

    if not any(relativo == base or relativo.startswith(base + "/")
               for base in allowed_dirs):
        raise FrontMatterError(
            f"{origem}: `{campo}` fora dos diretórios autorizados "
            f"({', '.join(allowed_dirs)}): {relativo}")

    if allowed_suffixes is not None and alvo.suffix.lower() not in allowed_suffixes:
        raise FrontMatterError(
            f"{origem}: `{campo}` tem extensão não autorizada "
            f"({alvo.suffix or 'sem extensão'}); permitido: "
            f"{', '.join(sorted(allowed_suffixes))}")

    if alvo.is_symlink() and not alvo.resolve(strict=False).is_relative_to(raiz):
        raise FrontMatterError(
            f"{origem}: `{campo}` é symlink para fora do repositório: {relativo}")

    if must_be_dir:
        if not alvo.is_dir():
            raise FrontMatterError(f"{origem}: `{campo}` não é um diretório: {relativo}")
    elif not alvo.is_file():
        raise FrontMatterError(f"{origem}: `{campo}` não existe: {relativo}")
    return alvo


def _rel(caminho: Any) -> str:
    """Relativo ao repo quando possível; absoluto quando não (bancada de teste)."""
    alvo = Path(caminho)
    try:
        return alvo.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return alvo.as_posix()


class ScaffoldDefinition:
    """Definição validada de um scaffold — a fonte única por componente."""

    __slots__ = ("component_type", "stack", "generator", "verifier",
                 "template_path", "version_source", "build_command",
                 "manifest", "source_path", "name", "raw")

    def __init__(self, **kwargs: Any) -> None:
        for campo in self.__slots__:
            setattr(self, campo, kwargs.get(campo))

    @property
    def output_path(self) -> str:
        """Sempre calculado do `component_type`. Nunca vem do front-matter."""
        return resolve_source_code_path(self.component_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type": self.component_type,
            "stack": self.stack,
            "name": self.name,
            "generator": _rel(self.generator),
            "verifier": _rel(self.verifier),
            "template_path": _rel(self.template_path),
            "version_source": self.version_source,
            "build_command": self.build_command,
            "manifest": self.manifest,
            "source_path": _rel(self.source_path),
            "output_path": self.output_path,
        }


def load_scaffold_definition(path: Path,
                             repo_root: Path | None = None) -> ScaffoldDefinition:
    """Lê e valida o front-matter de um `{stack}-scaffold.md`."""
    raiz = (repo_root or REPO_ROOT).resolve()
    arquivo = Path(path)
    if not arquivo.is_absolute():
        arquivo = raiz / arquivo
    origem = arquivo.name
    if not arquivo.is_file():
        raise FrontMatterError(f"scaffold não encontrado: {arquivo}")

    dados = _split_front_matter(arquivo.read_text(encoding="utf-8", errors="replace"), origem)

    desconhecidos = set(dados) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if desconhecidos:
        raise FrontMatterError(
            f"{origem}: campos não reconhecidos no front-matter: "
            f"{', '.join(sorted(desconhecidos))}")
    ausentes = [campo for campo in REQUIRED_FIELDS if not str(dados.get(campo) or "").strip()]
    if ausentes:
        raise FrontMatterError(
            f"{origem}: campos obrigatórios ausentes: {', '.join(ausentes)}")

    component_type = normalize_component_type(dados["component_type"])
    stack = str(dados["stack"]).strip().lower()

    # A stack precisa concordar com a responsabilidade declarada: `stack:
    # angular` com `component_type: backend` geraria frontend dentro de backend.
    esperado = component_type_for_stack(stack)
    if esperado != component_type:
        raise FrontMatterError(
            f"{origem}: stack `{stack}` é {esperado}, mas o front-matter declara "
            f"component_type: {component_type}")

    if "output_path" in dados:
        # Tolerado por compatibilidade, jamais usado para resolver o destino.
        assert_declared_output_path(dados["output_path"], component_type)

    generator = _resolve_allowed(
        dados["generator"], "generator", origem,
        allowed_dirs=ALLOWED_EXECUTABLE_DIRS,
        allowed_suffixes=ALLOWED_EXECUTABLE_SUFFIXES,
        must_be_dir=False, repo_root=raiz)
    verifier = _resolve_allowed(
        dados["verifier"], "verifier", origem,
        allowed_dirs=ALLOWED_EXECUTABLE_DIRS,
        allowed_suffixes=ALLOWED_EXECUTABLE_SUFFIXES,
        must_be_dir=False, repo_root=raiz)
    template_path = _resolve_allowed(
        dados["template_path"], "template_path", origem,
        allowed_dirs=ALLOWED_TEMPLATE_DIRS,
        allowed_suffixes=None, must_be_dir=True, repo_root=raiz)

    version_source = str(dados.get("version_source") or "versions.yaml").strip()
    if "/" in version_source or "\\" in version_source or ".." in version_source:
        raise FrontMatterError(
            f"{origem}: `version_source` deve ser um nome de arquivo dentro de "
            f"template_path, não um caminho: {version_source!r}")
    if not (template_path / version_source).is_file():
        raise FrontMatterError(
            f"{origem}: `version_source` não existe em template_path: "
            f"{version_source}")

    return ScaffoldDefinition(
        component_type=component_type,
        stack=stack,
        name=str(dados.get("name") or f"Scaffold {stack}").strip(),
        generator=generator,
        verifier=verifier,
        template_path=template_path,
        version_source=version_source,
        build_command=str(dados.get("build_command") or "").strip() or None,
        manifest=str(dados.get("manifest") or stack).strip(),
        source_path=arquivo,
        raw=dados,
    )


def scaffold_definition_for_stack(stack: str, scaffolds_dir: Path,
                                  repo_root: Path | None = None) -> ScaffoldDefinition:
    """Carrega a definição de `{scaffolds_dir}/{stack}-scaffold.md`.

    Sem fallback para `default-scaffold.md`: uma stack sem receita determinística
    precisa falhar alto, não gerar um esqueleto genérico que não compila.
    """
    caminho = Path(scaffolds_dir) / f"{str(stack).strip().lower()}-scaffold.md"
    if not caminho.is_file():
        raise FrontMatterError(
            f"stack sem scaffold determinístico: {stack} (esperado {caminho.name}). "
            f"Crie o arquivo com generator/verifier antes de usá-la na esteira.")
    return load_scaffold_definition(caminho, repo_root=repo_root)
