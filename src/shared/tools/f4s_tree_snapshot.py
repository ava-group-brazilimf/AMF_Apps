#!/usr/bin/env python3
"""
f4s_tree_snapshot.py — Gera snapshot da árvore de arquivos do repo F4S.

Ignora artefatos de build/cache para manter o snapshot enxuto e útil como
contexto para o próximo spec.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_IGNORE_PATTERNS = {
    ".git",
    ".gitignore",
    ".f4s",
    "bin",
    "obj",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    ".vs",
    ".idea",
    ".vscode",
    "*.dll",
    "*.exe",
    "*.pdb",
    "*.so",
    "*.dylib",
    "*.class",
    "*.jar",
}


def _should_ignore(path: Path, repo_root: Path, extra: set[str]) -> bool:
    """Decide se um arquivo/diretório deve ser omitido do snapshot."""
    rel = path.relative_to(repo_root)
    parts = rel.parts
    for part in parts:
        if part.lower() in DEFAULT_IGNORE_PATTERNS or part in extra:
            return True
    if path.is_file() and any(path.match(p) for p in DEFAULT_IGNORE_PATTERNS if "*" in p):
        return True
    return False


def snapshot(repo_root: Path, extra_ignore: set[str] | None = None,
             output_md: Path | None = None,
             output_json: Path | None = None) -> dict[str, Any]:
    """
    Gera snapshot da árvore de arquivos de `repo_root`.

    Retorna dict com `files` (lista de dicts com path relativo e tamanho) e
    `markdown` (string legível). Se `output_md`/`output_json` forem passados,
    grava os artefatos correspondentes.
    """
    if not repo_root.is_dir():
        raise FileNotFoundError(f"repo_root não existe: {repo_root}")
    ignore = set(extra_ignore or [])

    files: list[dict[str, Any]] = []
    for p in sorted(repo_root.rglob("*")):
        if _should_ignore(p, repo_root, ignore):
            continue
        if p.is_file():
            rel = p.relative_to(repo_root).as_posix()
            files.append({"path": rel, "size": p.stat().st_size})

    lines = ["# F4S — Current File Tree", "", f"Root: `{repo_root.as_posix()}`", ""]
    lines.append("| Path | Size (bytes) |")
    lines.append("|------|-------------|")
    for f in files:
        lines.append(f"| `{f['path']}` | {f['size']} |")
    lines.append("")
    lines.append(f"**Total files:** {len(files)}")
    markdown = "\n".join(lines)

    result = {"repo_root": repo_root.as_posix(), "files": files, "markdown": markdown}

    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(markdown, encoding="utf-8")
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(files, indent=2, ensure_ascii=False),
                               encoding="utf-8")

    return result
