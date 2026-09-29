#!/usr/bin/env python3
"""Resolução canônica do diretório de saída do scaffold.

Regra arquitetural: o diretório raiz do código é definido pela RESPONSABILIDADE
do componente, nunca pela tecnologia. `source-code/frontend` e
`source-code/backend` são os dois únicos destinos válidos — trocar Angular por
React, ou .NET por Java, muda generator, verifier, templates e comandos de
build, mas jamais o caminho.

Antes desta regra o repo tinha duas convenções vivas ao mesmo tempo:
`f4s_phase_runner.py` gravava em `source-code/{stack}/` e o
`ava-stack-orchestrator` em `source-code/backend|frontend/`. O mesmo projeto
podia terminar com código em dois lugares, e nenhum verificador olhava os dois.

Este módulo é a única fonte da resolução. Generators recebem o caminho já
resolvido; nenhum deles o calcula.
"""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

#: Raiz relativa, dentro de `outputs/tobe/`, de todo código gerado.
SOURCE_CODE_ROOT = "source-code"

#: Os únicos `component_type` aceitos. A ordem é a ordem de execução da esteira
#: (RF-002): frontend sempre antes de backend.
COMPONENT_TYPES: tuple[str, ...] = ("frontend", "backend")

#: Mapa stack → responsabilidade. Serve para CLASSIFICAR uma stack, nunca para
#: montar caminho. Stacks novas entram aqui; o caminho continua o mesmo.
STACK_COMPONENT_TYPES: dict[str, str] = {
    # frontend
    "angular": "frontend",
    "react": "frontend",
    "vue": "frontend",
    "svelte": "frontend",
    "blazor": "frontend",
    # backend
    "dotnet": "backend",
    "spring-boot": "backend",
    "java": "backend",
    "fastapi": "backend",
    "python": "backend",
    "gin": "backend",
    "go": "backend",
    "nestjs": "backend",
    "node": "backend",
}

#: Entradas sob `source-code/` que não são output de componente: o repositório
#: do baseline e os artefatos de log/estado que convivem com ele.
INFRASTRUCTURE_DIRS: frozenset[str] = frozenset({
    ".git", ".f4s", "node_modules", "__pycache__",
})

#: Nomes de diretório proibidos como raiz de componente — todos derivados de
#: linguagem/framework. Verificados por nome exato sob `source-code/`.
FORBIDDEN_ROOT_NAMES: frozenset[str] = frozenset(
    set(STACK_COMPONENT_TYPES) | {"stacks", "dotnet-core", "aspnet", "ng", "spa"}
)


class ScaffoldPathError(ValueError):
    """Configuração de caminho inválida — sempre antes de escrever arquivo."""


def normalize_component_type(component_type: Any) -> str:
    """Valida e normaliza o `component_type`; falha para qualquer outro valor."""
    value = str(component_type or "").strip().lower()
    if value not in COMPONENT_TYPES:
        raise ScaffoldPathError(
            f"component_type inválido: {component_type!r}. "
            f"Valores aceitos: {', '.join(COMPONENT_TYPES)}."
        )
    return value


def resolve_source_code_path(component_type: Any) -> str:
    """Caminho canônico relativo do componente — `source-code/{frontend|backend}`.

    Contrato: depende EXCLUSIVAMENTE de `component_type`. A stack não entra na
    conta, não é concatenada e não pode sobrescrever o resultado.
    """
    return f"{SOURCE_CODE_ROOT}/{normalize_component_type(component_type)}"


def component_type_for_stack(stack: Any) -> str:
    """Responsabilidade arquitetural de uma stack conhecida."""
    value = str(stack or "").strip().lower()
    if value not in STACK_COMPONENT_TYPES:
        raise ScaffoldPathError(
            f"stack sem component_type declarado: {stack!r}. "
            f"Registre-a em STACK_COMPONENT_TYPES antes de usá-la."
        )
    return STACK_COMPONENT_TYPES[value]


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def resolve_output_dir(tobe_root: Path, component_type: Any) -> Path:
    """Caminho absoluto e validado onde o generator do componente deve escrever.

    `tobe_root` é `projects/{project}/outputs/tobe`. O retorno é sempre
    `{tobe_root}/source-code/{component_type}` — resolvido, dentro do
    workspace, e livre de symlink que escape da árvore.
    """
    component = normalize_component_type(component_type)
    base = Path(tobe_root)
    if not base.is_absolute():
        base = base.resolve()
    canonical = base / SOURCE_CODE_ROOT / component
    validate_output_dir(canonical, component, base)
    return canonical


def validate_output_dir(candidate: Path, component_type: Any,
                        tobe_root: Path) -> Path:
    """Rejeita qualquer destino que não seja o canônico do componente.

    Cobre, nesta ordem: component_type inválido, caminho relativo ambíguo,
    traversal, saída de `source-code/`, nome derivado de tecnologia, e symlink
    (do próprio diretório ou de qualquer ancestral até `source-code/`) que
    aponte para fora da árvore do projeto.
    """
    component = normalize_component_type(component_type)
    base = Path(tobe_root)
    base = base if base.is_absolute() else base.resolve()
    source_root = base / SOURCE_CODE_ROOT

    path = Path(candidate)
    if not path.is_absolute():
        path = (base / path).resolve(strict=False)
    else:
        path = path.resolve(strict=False)

    if not _within(path, source_root.resolve(strict=False)):
        raise ScaffoldPathError(
            f"destino fora de {SOURCE_CODE_ROOT}/: {candidate} "
            f"(esperado {source_root / component})"
        )

    relative = path.relative_to(source_root.resolve(strict=False))
    parts = relative.parts
    if len(parts) != 1:
        raise ScaffoldPathError(
            f"destino não é a raiz de um componente: {SOURCE_CODE_ROOT}/"
            f"{'/'.join(parts)} (esperado {resolve_source_code_path(component)})"
        )
    name = parts[0]
    if name in FORBIDDEN_ROOT_NAMES:
        raise ScaffoldPathError(
            f"diretório raiz derivado da tecnologia é proibido: "
            f"{SOURCE_CODE_ROOT}/{name}. Use "
            f"{resolve_source_code_path(component)} — a stack é metadado, "
            f"não caminho."
        )
    if name != component:
        raise ScaffoldPathError(
            f"destino {SOURCE_CODE_ROOT}/{name} não corresponde a "
            f"component_type={component} (esperado "
            f"{resolve_source_code_path(component)})"
        )

    # Symlink em qualquer nível entre source-code/ e o diretório do componente
    # permitiria escrever fora do repositório preservando o nome canônico.
    for level in (source_root, source_root / component):
        if level.is_symlink():
            destino = level.resolve(strict=False)
            if not _within(destino, base):
                raise ScaffoldPathError(
                    f"symlink aponta para fora do projeto: {level} -> {destino}"
                )
    return path


def assert_declared_output_path(declared: Any, component_type: Any) -> str:
    """Valida um `output_path` informativo declarado em front-matter/estado.

    Mantido apenas por compatibilidade: o valor é conferido contra o canônico e
    qualquer divergência é erro de configuração. A recomendação continua sendo
    não declarar `output_path` e deixá-lo ser calculado.
    """
    esperado = resolve_source_code_path(component_type)
    valor = str(declared or "").strip().replace("\\", "/").strip("/")
    if valor != esperado:
        raise ScaffoldPathError(
            f"output_path declarado ({declared!r}) diverge do canônico para "
            f"component_type={normalize_component_type(component_type)}: "
            f"{esperado!r}. Remova o campo ou corrija-o."
        )
    return esperado


def canonical_output_paths() -> dict[str, str]:
    """`{component_type: caminho canônico}` — para relatórios e mensagens."""
    return {item: resolve_source_code_path(item) for item in COMPONENT_TYPES}


def detect_legacy_output_dirs(tobe_root: Path) -> list[dict[str, Any]]:
    """Diretórios herdados sob `source-code/` cujo nome vem da tecnologia.

    Só REPORTA. Mover, apagar ou sobrescrever código existente exige rotina
    explícita de migração — nunca acontece como efeito colateral de um build.
    """
    base = Path(tobe_root)
    source_root = base / SOURCE_CODE_ROOT
    achados: list[dict[str, Any]] = []
    if not source_root.is_dir():
        return achados
    for entry in sorted(source_root.iterdir()):
        if not entry.is_dir() or entry.name in COMPONENT_TYPES:
            continue
        # `.git/` é o repo do próprio baseline — que vive em `source-code/`
        # justamente para que um commit contenha frontend E backend. Diretório
        # oculto nunca é output de stack.
        if entry.name.startswith(".") or entry.name in INFRASTRUCTURE_DIRS:
            continue
        stack = entry.name.lower()
        achados.append({
            "path": entry.as_posix(),
            "name": entry.name,
            "stack": stack if stack in STACK_COMPONENT_TYPES else None,
            "component_type": STACK_COMPONENT_TYPES.get(stack),
            "canonical": (
                resolve_source_code_path(STACK_COMPONENT_TYPES[stack])
                if stack in STACK_COMPONENT_TYPES else None
            ),
            "has_files": any(entry.rglob("*")),
        })
    return achados


def files_outside_canonical(tobe_root: Path,
                            component_types: Iterable[str] = COMPONENT_TYPES) -> list[str]:
    """Diretórios não canônicos com conteúdo — bloqueiam o commit de baseline."""
    permitidos = {normalize_component_type(item) for item in component_types}
    return [
        item["path"] for item in detect_legacy_output_dirs(tobe_root)
        if item["has_files"] and item["name"] not in permitidos
    ]


#: Construções que reintroduzem caminho por stack. Usado pelo teste de
#: regressão que varre o código-fonte.
STACK_PATH_ANTIPATTERNS: tuple[tuple[str, str], ...] = (
    (r'["\']source-code/\{\s*stack', 'f-string "source-code/{stack}"'),
    (r'["\']source-code/\{\s*target_stack', 'f-string "source-code/{target_stack}"'),
    (r'Path\(\s*["\']source-code["\']\s*\)\s*/\s*\w*stack', 'Path("source-code") / stack'),
    (r'["\']source-code["\']\s*,\s*\w*stack\b', 'os.path.join("source-code", stack)'),
    (r'["\']source-code["\']\s*/\s*\w*stack\b', '"source-code" / stack'),
)


def find_stack_path_antipatterns(text: str) -> list[str]:
    """Rótulos dos antipadrões de caminho-por-stack encontrados em `text`."""
    return [rotulo for padrao, rotulo in STACK_PATH_ANTIPATTERNS
            if re.search(padrao, text)]
