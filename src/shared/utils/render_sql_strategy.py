"""
render_sql_strategy.py
======================
Renderiza `outputs/tobe/db/sql-strategy.md` para um projeto a partir do
template corporativo `sql-strategy.md.j2` + `sql-strategy.version`.

Implementa o contrato do agente `ava-tobe-database-policy` (Fase 1.4):
  - Gate: ADR-002 obrigatório.
  - policy_version == template_version (ambos derivados de
    sql-strategy.version, já que o template não declara frontmatter
    de versão — está sincronizado por convenção corporativa).
  - Fontes ausentes → marcador `[FONTE AUSENTE]` + manifesto com
    architecture_open_items=true.
  - Backup append-only em `.history/`.
  - Manifesto JSON com policy_version, template_version, trace_id,
    generated_at, fontes_usadas[], fontes_ausentes[], architecture_open_items.

Uso:
    python src/shared/utils/render_sql_strategy.py <project_name>
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[3]

VERSION_FILE = REPO_ROOT / "src" / "shared" / "data" / "policies" / "sql-strategy.version"
TEMPLATE_DIR = REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "tobe-architecture" / "templates" / "reports"
TEMPLATE_NAME = "sql-strategy.md.j2"


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _resolve_persistence(cfg: dict) -> dict:
    """tobe_stack.persistence is not in this project's yaml → fall back to
    ADR-002 / corporate defaults (SQL Server + EF Core 8). Documented."""
    p = (cfg.get("tobe_stack") or {}).get("persistence") or {}
    return {
        "engine": p.get("engine", "sqlserver"),
        "orm": p.get("orm", "efcore"),
    }


_BC_HEADING_RE = re.compile(r"^###\s+BC-(\d+)\s+([^\n]+)", re.M)


def _parse_bounded_contexts(bc_map_path: Path) -> list[dict]:
    if not bc_map_path.exists():
        return []
    text = bc_map_path.read_text(encoding="utf-8", errors="replace")
    contexts: list[dict] = []
    matches = list(_BC_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        bc_num = m.group(1)
        bc_name = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        # Aggregate Roots: linha começando "Aggregate Root" ou "Aggregate Roots"
        agg = []
        agg_m = re.search(r"Aggregate Roots?\**:?\s*([^\n]+)", body)
        if agg_m:
            agg = [a.strip().strip("`*") for a in re.split(r"[,;]", agg_m.group(1)) if a.strip()]
        # Slug for schema name
        slug = re.sub(r"[^a-z0-9]+", "_", bc_name.lower()).strip("_")
        contexts.append({
            "name": f"BC-{bc_num} {bc_name}",
            "schema_write": f"{slug}_write",
            "schema_read": f"{slug}_read",
            "aggregates": agg or ["—"],
            "projections": ["—"],
        })
    return contexts


def render_for_project(project_name: str) -> int:
    project_root = REPO_ROOT / "projects" / project_name
    if not project_root.exists():
        print(f"ERROR: project not found: {project_root}", file=sys.stderr)
        return 2

    config_path = project_root / "context" / "project-config.yaml"
    adr_path = project_root / "outputs" / "tobe" / "docs" / "decisions" / "ADR-002-database.md"
    schema_inv_path = project_root / "outputs" / "asis" / "db" / "schema-inventory.md"
    sp_map_path = project_root / "outputs" / "asis" / "db" / "stored-procedures-map.md"
    tr_map_path = project_root / "outputs" / "asis" / "db" / "triggers-map.md"
    bc_map_path = project_root / "outputs" / "tobe" / "docs" / "bounded-context-map.md"

    cfg = _read_yaml(config_path)

    # Gate: ADR-002
    if not adr_path.exists():
        print(f"ABORT: gate failed — ADR-002 missing at {adr_path}", file=sys.stderr)
        return 3

    # Versions
    policy_version = VERSION_FILE.read_text(encoding="utf-8").strip()
    template_version = policy_version  # template carries no separate frontmatter version → sync by convention

    # Fontes
    fontes_obrigatorias = {
        "sql-strategy.version": VERSION_FILE,
        "sql-strategy.md.j2": TEMPLATE_DIR / TEMPLATE_NAME,
        "project-config.yaml": config_path,
        "ADR-002-database.md": adr_path,
    }
    fontes_recomendadas = {
        "schema-inventory.md": schema_inv_path,
        "stored-procedures-map.md": sp_map_path,
        "triggers-map.md": tr_map_path,
        "bounded-context-map.md (TO-BE)": bc_map_path,
    }
    fontes_usadas = [str(p.relative_to(REPO_ROOT)) for p in fontes_obrigatorias.values()]
    fontes_ausentes: list[str] = []
    for name, p in fontes_recomendadas.items():
        if p.exists():
            fontes_usadas.append(str(p.relative_to(REPO_ROOT)))
        else:
            fontes_ausentes.append(str(p.relative_to(REPO_ROOT)))
    architecture_open_items = bool(fontes_ausentes)

    # Bounded contexts
    bcs = _parse_bounded_contexts(bc_map_path)

    persistence = _resolve_persistence(cfg)
    trace_id = str(uuid.uuid4())
    generated_at = _now_iso_utc()
    tech_lead_name = cfg.get("tech_lead_name") or cfg.get("team", {}).get("tech_lead") or "<a definir>"

    ctx: dict[str, Any] = {
        "project_name": cfg.get("project_name", project_name),
        "policy_version": policy_version,
        "generated_at": generated_at,
        "trace_id": trace_id,
        "tech_lead_name": tech_lead_name,
        "persistence": persistence,
        "bounded_contexts": bcs,
        "stored_procedures": [],   # AS-IS map ausente → seção marca [FONTE AUSENTE] via {% else %}
        "triggers": [],
        "coverage": {
            "sp_total": "?",
            "sp_migrated": 0,
            "trigger_total": "?",
            "trigger_migrated": 0,
            "views_writeside": 0,
            "views_readside": 0,
        },
        "fontes_ausentes": fontes_ausentes,
    }

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        keep_trailing_newline=True,
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
        # NOTE: not StrictUndefined — template uses `| default(...)` filters
    )
    template = env.get_template(TEMPLATE_NAME)
    rendered = template.render(**ctx)

    out_dir = project_root / "outputs" / "tobe" / "db"
    history_dir = out_dir / ".history"
    history_dir.mkdir(parents=True, exist_ok=True)

    out_md = out_dir / "sql-strategy.md"
    out_md.write_text(rendered, encoding="utf-8")

    backup = history_dir / f"sql-strategy-{policy_version}-{trace_id}.md"
    shutil.copy2(out_md, backup)

    manifest = {
        "policy_version": policy_version,
        "template_version": template_version,
        "trace_id": trace_id,
        "generated_at": generated_at,
        "project_name": ctx["project_name"],
        "persistence": persistence,
        "bounded_contexts_count": len(bcs),
        "fontes_usadas": fontes_usadas,
        "fontes_ausentes": fontes_ausentes,
        "architecture_open_items": architecture_open_items,
        "renderer": "src/shared/utils/render_sql_strategy.py",
    }
    (out_dir / "sql-strategy.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("OK render_sql_strategy")
    print(f"  output       : {out_md.relative_to(REPO_ROOT)}")
    print(f"  history      : {backup.relative_to(REPO_ROOT)}")
    print(f"  manifest     : {(out_dir / 'sql-strategy.manifest.json').relative_to(REPO_ROOT)}")
    print(f"  policy_ver   : {policy_version}")
    print(f"  trace_id     : {trace_id}")
    print(f"  bcs          : {len(bcs)}")
    print(f"  fontes_aus   : {len(fontes_ausentes)} → architecture_open_items={architecture_open_items}")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python render_sql_strategy.py <project_name>", file=sys.stderr)
        return 1
    return render_for_project(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
