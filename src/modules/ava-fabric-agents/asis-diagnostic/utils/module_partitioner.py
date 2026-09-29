#!/usr/bin/env python3
"""
AVA Fabric – Module Partitioner (Leiden-based)
===============================================
Particiona um repositório Delphi em módulos / bounded contexts via detecção de
comunidades no grafo de dependências ``uses``.  O algoritmo utilizado é o
**Leiden** (Traag et al., 2019), que corrige bugs de resolução e comunidades
desconexas do Louvain clássico.

Arquitetura (post-filter)
-------------------------
A ferramenta AST externa NÃO é modificada.  Ela extrai todo o repositório em
9 JSONs monolíticos.  Este script é invocado **após** a extração, lê
``08_code_overview.json`` para construir o grafo de dependências, executa o
Leiden e produz os artefatos de partição.  Agentes downstream filtram suas
análises a partir do ``scope-filter-manifest.json`` gerado aqui.

Artefatos gerados
-----------------
* ``module-partition.json``        — mapeamento completo módulo → [units]
* ``scope-filter-manifest.json``   — manifesto ativo quando scope_modules != "all"
* ``sql-ir.json`` (via ``sql_ir_generator.py``) — representação normalizada do schema + entidades + relacionamentos para consumo por agentes de MER/DB Design

Uso standalone
--------------
    python module_partitioner.py --project Meu-ERP \
        --scope-modules Financeiro Vendas \
        --resolution 1.0 \
        --output-dir projects/Meu-ERP/outputs/asis/ast-raw/delphi/compressed

Uso integrado (run_ast_analysis.py)
-----------------------------------
    partitioner = ModulePartitioner(project_name, language="delphi")
    partitioner.run()

Dependências
------------
    pip install python-igraph leidenalg pyyaml
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# RegEx para extração de ``uses`` (Delphi / Object Pascal)
# ---------------------------------------------------------------------------
_RE_USES = re.compile(r"(?im)^\s*uses\s+([^;]+);")


def _extract_uses_from_sources(source_dir: Path) -> dict[str, list[str]]:
    """
    Varre recursivamente ``source_dir`` em busca de arquivos ``.pas`` e extrai
    as cláusulas ``uses`` via regex.  Retorna ``{unit_name: [imported, ...]}``.
    """
    deps: dict[str, list[str]] = {}
    for pas_file in source_dir.rglob("*.pas"):
        try:
            text = pas_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        matches = _RE_USES.findall(text)
        # Normaliza o nome da unit a partir do nome do arquivo
        unit_name = pas_file.name
        imports: list[str] = []
        for match in matches:
            # Pode haver múltiplas linhas separadas por vírgula
            for part in match.split(","):
                cleaned = part.strip()
                if cleaned:
                    imports.append(cleaned)
        if imports:
            deps[unit_name] = imports
    return deps


def _normalize_unit(name: str) -> str:
    """Remove qualquer caminho e força lower-case para matching."""
    return Path(name).name.lower()


# ---------------------------------------------------------------------------
# Leiden wrapper
# ---------------------------------------------------------------------------

def _run_leiden(
    edges: list[tuple[str, str, float]],
    *,
    resolution: float | None = None,
    seed: int = 42,
) -> dict[str, list[str]]:
    """
    Executa o algoritmo Leiden sobre a lista de arestas e retorna um dict
    ``{community_name: [unit, ...]}``.

    Args:
        edges: lista de (source, target, weight)
        resolution: se None, auto-tune com base no número de vértices.
        seed: seed para reprodutibilidade.
    """
    try:
        import igraph as ig
        import leidenalg
    except ImportError as exc:
        raise RuntimeError(
            "Dependências python-igraph e leidenalg não instaladas. "
            "Execute: pip install python-igraph leidenalg"
        ) from exc

    # Normaliza nomes dos nós
    node_set: set[str] = set()
    for s, t, _ in edges:
        node_set.add(_normalize_unit(s))
        node_set.add(_normalize_unit(t))

    vertices = sorted(node_set)
    idx = {v: i for i, v in enumerate(vertices)}

    ig_edges = []
    ig_weights = []
    for s, t, w in edges:
        s_n = _normalize_unit(s)
        t_n = _normalize_unit(t)
        if s_n == t_n:
            continue
        ig_edges.append((idx[s_n], idx[t_n]))
        ig_weights.append(w)

    G = ig.Graph(directed=True)
    G.add_vertices(len(vertices))
    if ig_edges:
        G.add_edges(ig_edges)
        G.es["weight"] = ig_weights

    # Resolução auto-tunada
    if resolution is None:
        n = G.vcount()
        if n < 50:
            resolution = 0.5
        elif n < 200:
            resolution = 1.0
        else:
            resolution = 1.5

    partition = leidenalg.find_partition(
        G,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=resolution,
        weights="weight",
        seed=seed,
    )

    # Agrupa units por comunidade
    communities: dict[int, list[str]] = {}
    for vid, comm_id in enumerate(partition.membership):
        communities.setdefault(comm_id, []).append(vertices[vid])

    return communities


def _name_community(
    units: list[str],
    graph_edges: list[tuple[str, str, float]],
) -> str:
    """
    Nomeia uma comunidade heuricamente:
    1. Prefixo de diretório mais comum (se houver paths).
    2. Caso contrário, unit com maior weighted in-degree (hub).
    """
    # Tenta prefixo de diretório
    prefixes: dict[str, int] = {}
    for u in units:
        p = Path(u)
        if str(p.parent) != ".":
            pref = str(p.parent).replace("\\", "/").split("/")[0]
            prefixes[pref] = prefixes.get(pref, 0) + 1
    if prefixes:
        best_prefix = max(prefixes, key=prefixes.get)  # type: ignore[arg-type]
        if prefixes[best_prefix] > len(units) * 0.3:
            return best_prefix.capitalize()

    # Fallback: hub de maior grau
    in_degrees: dict[str, float] = {}
    for s, t, w in graph_edges:
        s_n = _normalize_unit(s)
        t_n = _normalize_unit(t)
        if t_n in (_normalize_unit(u) for u in units):
            in_degrees[t_n] = in_degrees.get(t_n, 0.0) + w

    if in_degrees:
        hub = max(in_degrees, key=in_degrees.get)  # type: ignore[arg-type]
        # Remove extensão e prefixos genéricos
        base = Path(hub).stem
        for prefix in ("u", "unit", "frm", "cls"):
            if base.lower().startswith(prefix):
                base = base[len(prefix) :]
                break
        return base.capitalize() if base else "Modulo"

    return "Modulo"


# ---------------------------------------------------------------------------
# Override manual
# ---------------------------------------------------------------------------

def _load_manual_override(override_path: Path) -> dict[str, Any] | None:
    if not override_path.exists():
        return None
    data = json.loads(override_path.read_text(encoding="utf-8"))
    if "modules" not in data:
        raise ValueError(f"override file {override_path} deve conter chave 'modules'")
    return data


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class ModulePartitioner:
    """
    Motor de particionamento de módulos para repositórios Delphi / .NET / Java.
    """

    def __init__(
        self,
        project_name: str,
        *,
        language: str = "delphi",
        scope_modules: list[str] | str | None = None,
        resolution: float | None = None,
        output_dir: Path | None = None,
        source_dir: Path | None = None,
    ) -> None:
        self.project_name = project_name
        self.language = language
        self.config = self._load_config()

        # Resolve scope_modules
        if scope_modules is None:
            raw = self.config.get("scope_modules", "all")
            if isinstance(raw, list):
                self.scope_modules = raw
            else:
                self.scope_modules = str(raw).strip().lower()
        else:
            self.scope_modules = (
                [m.strip().lower() for m in scope_modules]
                if isinstance(scope_modules, list)
                else str(scope_modules).strip().lower()
            )

        # Resolve resolution
        if resolution is None:
            self.resolution = self.config.get("module_partitioner_resolution")
        else:
            self.resolution = resolution

        # Resolve output_dir
        if output_dir is None:
            self.output_dir = (
                Path(f"projects/{project_name}/outputs/asis/ast-raw/{self.language}/compressed")
                .resolve()
            )
        else:
            self.output_dir = output_dir.resolve()

        # Resolve source_dir (para extrair uses adicionais se necessário)
        if source_dir is None:
            repo = self.config.get("repository_path", "")
            self.source_dir = Path(repo).resolve() if repo else None
        else:
            self.source_dir = source_dir.resolve()

        self._override: dict[str, Any] | None = None
        self._partition: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _load_config(self) -> dict[str, Any]:
        cfg_path = Path(f"projects/{self.project_name}/context/project-config.yaml")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_code_overview(self) -> dict[str, Any]:
        overview_path = self.output_dir.parent / "extraction" / "08_code_overview.json"
        if not overview_path.exists():
            raise FileNotFoundError(
                f"08_code_overview.json não encontrado em {overview_path.parent}"
            )
        return json.loads(overview_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Build dependency graph
    # ------------------------------------------------------------------
    def _build_graph(self) -> list[tuple[str, str, float]]:
        """
        Constrói o grafo de dependências a partir de:
        1. ``08_code_overview.json`` → payload.classes[].{name, file, parent}
        2. Regex de ``uses`` nos fontes .pas (fallback / enriquecimento)
        """
        overview = self._load_code_overview()
        classes = overview.get("payload", {}).get("classes", [])

        edges: list[tuple[str, str, float]] = []
        seen: set[tuple[str, str]] = set()

        # Primary: classes do overview
        for cls in classes:
            unit_file = cls.get("file", "")
            if not unit_file:
                continue
            unit_name = Path(unit_file).name
            parent = cls.get("parent", "")
            if parent:
                parent_unit = Path(parent).name if "/" in parent or "\\" in parent else parent
                key = (_normalize_unit(unit_name), _normalize_unit(parent_unit))
                if key not in seen:
                    seen.add(key)
                    edges.append((unit_name, parent_unit, 1.0))

        # Secondary / enrichment: regex de uses nos fontes
        if self.source_dir and self.source_dir.exists():
            uses_map = _extract_uses_from_sources(self.source_dir)
            for unit_name, imports in uses_map.items():
                for imp in imports:
                    key = (_normalize_unit(unit_name), _normalize_unit(imp))
                    if key not in seen:
                        seen.add(key)
                        edges.append((unit_name, imp, 1.0))

        return edges

    # ------------------------------------------------------------------
    # Partitioning
    # ------------------------------------------------------------------
    def _partition_modules(self) -> dict[str, list[str]]:
        override_filename = self.config.get("module_override_file") or "module-override.json"
        override_path = Path(
            f"projects/{self.project_name}/context/{override_filename}"
        )
        manual = _load_manual_override(override_path)
        if manual:
            print("   ⚡ Module override detectado — pulando inferência Leiden.")
            self._override = manual
            return {name: sorted(units) for name, units in manual["modules"].items()}

        edges = self._build_graph()
        if not edges:
            print("   ⚠️  Nenhuma aresta de dependência encontrada — retornando partição trivial.")
            # Partição trivial: cada unit é um módulo
            overview = self._load_code_overview()
            units = {
                Path(c.get("file", "") or c.get("name", "")).name
                for c in overview.get("payload", {}).get("classes", [])
                if (c.get("file") or c.get("name"))
            }
            return {f"Modulo_{i}": [u] for i, u in enumerate(sorted(units), 1)}

        # Executa Leiden
        communities = _run_leiden(edges, resolution=self.resolution)
        # Nomeia cada comunidade
        partition: dict[str, list[str]] = {}
        for comm_id, units in communities.items():
            name = _name_community(units, edges)
            # Evita colisão de nomes
            final_name = name
            suffix = 1
            while final_name in partition:
                final_name = f"{name}_{suffix}"
                suffix += 1
            partition[final_name] = sorted(units)

        return partition

    # ------------------------------------------------------------------
    # Scope filtering
    # ------------------------------------------------------------------
    def _apply_scope(self) -> dict[str, Any]:
        all_units = set()
        for units in self._partition.values():
            all_units.update(units)

        if self.scope_modules == "all":
            return {
                "scope_modules": "all",
                "included_units": sorted(all_units),
                "excluded_units": [],
                "module_partition": self._partition,
                "source": self._override.get("source", "manual") if self._override else "leiden",
                "resolution": self.resolution,
            }

        # scope_modules é uma lista
        requested = set(self.scope_modules)  # type: ignore[arg-type]
        included_modules: dict[str, list[str]] = {}
        included_units: set[str] = set()

        for mod_name, units in self._partition.items():
            if mod_name.lower() in requested:
                included_modules[mod_name] = units
                included_units.update(units)

        missing = requested - {m.lower() for m in included_modules}
        if missing:
            print(
                f"   ⚠️  Módulos solicitados não encontrados na partição: {sorted(missing)}",
                file=sys.stderr,
            )

        excluded = sorted(all_units - included_units)
        return {
            "scope_modules": sorted(requested),
            "included_units": sorted(included_units),
            "excluded_units": excluded,
            "module_partition": included_modules,
            "source": self._override.get("source", "manual") if self._override else "leiden",
            "resolution": self.resolution,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> int:
        """
        Executa o pipeline completo de particionamento e grava os artefatos.
        Retorna 0 em sucesso, 1 em erro.
        """
        print(f"\n🔧 ModulePartitioner :: {self.project_name}")
        print(f"   output_dir : {self.output_dir}")
        print(f"   scope      : {self.scope_modules}")
        print(f"   resolution : {self.resolution}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._partition = self._partition_modules()
        except Exception as exc:
            print(f"   ❌ Falha na partição: {exc}", file=sys.stderr)
            return 1

        print(f"   📦 Módulos inferidos: {len(self._partition)}")
        for name, units in sorted(self._partition.items()):
            print(f"      • {name}: {len(units)} units")

        # Grava module-partition.json (sempre)
        partition_path = self.output_dir / "module-partition.json"
        partition_path.write_text(
            json.dumps(self._partition, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"   ✅ {partition_path}")

        # Grava scope-filter-manifest.json (sempre; utilidade total quando scope="all")
        manifest = self._apply_scope()
        manifest_path = self.output_dir / "scope-filter-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"   ✅ {manifest_path}")

        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_cli() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Particiona repositório Delphi em módulos via Leiden algorithm"
    )
    ap.add_argument("--project", required=True, help="Nome do projeto")
    ap.add_argument(
        "--scope-modules",
        nargs="+",
        default=None,
        help='Lista de módulos (ex: Financeiro Vendas). Use "all" para todo o repo.',
    )
    ap.add_argument(
        "--resolution",
        type=float,
        default=None,
        help="Resolução do Leiden (auto-tunado se omitido)",
    )
    ap.add_argument(
        "--language",
        default="delphi",
        help="Linguagem legada detectada (default: delphi)",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Diretório de saída (default: projects/{proj}/outputs/asis/ast-raw/{language}/compressed)",
    )
    ap.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Diretório fonte .pas (default: repository_path do project-config)",
    )
    return ap


def main() -> int:
    ap = _build_cli()
    a = ap.parse_args()

    scope_modules: list[str] | str | None = a.scope_modules
    if isinstance(scope_modules, list) and len(scope_modules) == 1:
        if scope_modules[0].lower() == "all":
            scope_modules = "all"

    partitioner = ModulePartitioner(
        project_name=a.project,
        language=a.language,
        scope_modules=scope_modules,
        resolution=a.resolution,
        output_dir=a.output_dir,
        source_dir=a.source_dir,
    )
    return partitioner.run()


if __name__ == "__main__":
    sys.exit(main())
