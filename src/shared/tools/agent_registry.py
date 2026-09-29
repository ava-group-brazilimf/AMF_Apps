#!/usr/bin/env python3
"""
agent_registry.py — Fonte canônica única dos agentes da esteira AVA Fabric.

Varre `src/modules/ava-fabric-agents/**/agents/**/*.md`, lê o frontmatter de cada
agente e deriva a fase a partir do módulo. Substitui os dois `AGENT_CATALOG`
mantidos à mão em `pipeline_observer.py` e `generate_observability_report.py`,
que haviam divergido entre si e da realidade em disco (52 de 101 agentes
ausentes, 18 versões divergentes — ver specs/032).

Autoridade da fase
------------------
`.specify/memory/constitution.md` § Project Reference (emenda v1.4.0). O
`module.yaml` da raiz ficou com a numeração pré-1.4.0 nos comentários e **não**
é autoridade:

    F1 asis-diagnostic · F2 tobe-architecture · F3 prototype   · F4 tech-stack
    F5 qa-agents       · F6 devops-agents     · F7 deliverables · F8 summary

Três lugares guardam a versão de um agente — o frontmatter, o literal
`--version` do bloco de observabilidade, e o catálogo. Aqui o **frontmatter é a
fonte de verdade**; `verify_agent_observability.py` reprova as divergências.

Uso
---
    python src/shared/tools/agent_registry.py                 # tabela legível
    python src/shared/tools/agent_registry.py --json
    python src/shared/tools/agent_registry.py --catalog        # formato AGENT_CATALOG
    python src/shared/tools/agent_registry.py --agent ava-qa-exploratory

Como biblioteca
---------------
    from agent_registry import load, catalog, get, PHASE_BY_MODULE

    load()      # todos os registros, incluindo não-despacháveis e depreciados
    catalog()   # [{"agent","phase","version"}] — despacháveis, ordenado por fase
    get("ava-qa-exploratory")
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
AGENTS_ROOT = PROJECT_ROOT / "src" / "modules" / "ava-fabric-agents"

# ─── Constants ───────────────────────────────────────────────────────────────

#: Fase por módulo — Constituição v1.4.0. `""` = transversal (master-orchestrator).
PHASE_BY_MODULE: dict[str, str] = {
    "asis-diagnostic": "F1",
    "tobe-architecture": "F2",
    "prototype": "F3",
    # F3S — camada de planejamento SpecKit, entre o protótipo e a geração de
    # código (spec 039). Sufixo em vez de número novo para não renumerar F4..F8,
    # que aparecem em prosa de agente, relatórios e artefatos já entregues.
    "speckit": "F3S",
    "tech-stack": "F4",
    "qa-agents": "F5",
    "devops-agents": "F6",
    "deliverables": "F7",
    "summary": "F8",
    "master-orchestrator": "",
}

PHASE_ORDER = ["F1", "F2", "F3", "F3S", "F4", "F5", "F6", "F7", "F8"]

PHASE_NAMES = {
    "F1": "AS-IS Diagnostic",
    "F2": "TO-BE Architecture",
    "F3": "Prototype",
    "F3S": "SpecKit Planning",
    "F4": "Stack / Codegen",
    "F5": "QA",
    "F6": "DevOps",
    "F7": "Deliverables",
    "F8": "Summary",
}

#: Orquestradores de fase — os únicos agentes que reportam agregado de fase.
PHASE_ORCHESTRATORS = {
    "ava-master-orchestrator",
    "ava-asis-orchestrator",
    "ava-tobe-orchestrator",
    "ava-speckit-orchestrator",
    "ava-stack-orchestrator",
    "ava-qa-orchestrator",
    "ava-devops-orchestrator",
}

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
_NAME_RE = re.compile(r'^name:\s*"?([^"\r\n]+?)"?\s*$', re.MULTILINE)
_VERSION_RE = re.compile(r'^version:\s*"?([^"\r\n]+?)"?\s*$', re.MULTILINE)
_ALLOWED_TOOLS_RE = re.compile(r'^allowed-tools:\s*(.+?)\s*$', re.MULTILINE)

#: Marcador do Batch Write Protocol (shared/batch-write-protocol.md). Um agente que
#: o referencia é instruído a persistir via `Bash` + PowerShell batch e portanto
#: **precisa** de `Bash` em `allowed-tools` — foi a contradição que deixou
#: `outputs/asis/docs/` vazio em processaERP-11.
_BATCH_WRITE_MARKER = "BatchWriteProtocol"

#: Marcador de contrato de saída — agente que declara artefatos precisa poder gravá-los.
_OUTPUT_CONTRACT_MARKER = "## Output Contract"
_TRACK_MARKER = "pipeline_observer.py -p {project_name} track"
_TRACK_ARGS_RE = re.compile(
    r'--agent\s+(\S+)\s+--phase\s+("[^"]*"|\S+)\s+--version\s+(\S+)'
)

_CACHE: list[dict[str, Any]] | None = None


# ─── Parsing ─────────────────────────────────────────────────────────────────

def _read_frontmatter(text: str) -> tuple[str | None, str | None]:
    """Extrai ``name`` e ``version`` do frontmatter YAML (sem exigir pyyaml)."""
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return None, None
    block = match.group(1)
    name = _NAME_RE.search(block)
    version = _VERSION_RE.search(block)
    return (name.group(1).strip() if name else None,
            version.group(1).strip() if version else None)


def _read_allowed_tools(text: str) -> tuple[list[str], str | None]:
    """Extrai ``allowed-tools`` do frontmatter.

    Devolve ``(tools, raw)``. A lista é sempre separada por vírgula na convenção
    do repositório; ``Read Write Edit`` (separado por espaço) é aceito aqui para
    que ``validate()`` possa **reprovar** a forma errada em vez de silenciosamente
    ver um único token — era o estado de `documentation-asis.md`, cujo grant de
    ferramentas não era interpretado e resultava em zero artefatos gravados.
    """
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return [], None
    found = _ALLOWED_TOOLS_RE.search(match.group(1))
    if not found:
        return [], None
    raw = found.group(1).strip()
    parts = [t.strip() for t in (raw.split(",") if "," in raw else raw.split())]
    return [t for t in parts if t], raw


def _read_track(text: str) -> tuple[str | None, str | None, str | None]:
    """Extrai ``--agent``/``--phase``/``--version`` do bloco de observabilidade."""
    match = _TRACK_ARGS_RE.search(text)
    if not match:
        return None, None, None
    phase = match.group(2)
    if phase.startswith('"') and phase.endswith('"'):
        phase = phase[1:-1]
    return match.group(1), phase, match.group(3)


def _module_of(path: Path) -> str:
    """Nome do módulo a partir do caminho (``…/ava-fabric-agents/<módulo>/agents/…``)."""
    try:
        return path.relative_to(AGENTS_ROOT).parts[0]
    except ValueError:
        return ""


def _is_dispatchable(path: Path) -> bool:
    """Sub-skills (``agents/*/skills/*.md``) não são agentes despacháveis.

    São arquivos de apoio lidos por um agente pai (ex.: os dialetos de banco sob
    ``db-analyzer/skills/``); não têm bloco de observabilidade nem entram no
    catálogo.
    """
    return "skills" not in path.parts


# ─── Varredura ───────────────────────────────────────────────────────────────

def _scan() -> list[dict[str, Any]]:
    """Varre o disco e devolve um registro por arquivo de agente."""
    records: list[dict[str, Any]] = []
    if not AGENTS_ROOT.is_dir():
        return records

    for path in sorted(AGENTS_ROOT.glob("*/agents/**/*.md")):
        try:
            # utf-8-sig e nao utf-8: um BOM de 3 bytes faz `_FRONTMATTER_RE`
            # (ancorada em \A) nao casar, o agente sai do catalogo em silencio, e
            # com ele saem cinco controles — validate_plan, verificacao de
            # observabilidade, regras AT-00x de allowed-tools, geracao de wrapper e
            # resolucao de spec_path. Custou um exit 2 em `run --all`.
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        name, version = _read_frontmatter(text)
        if not name:
            continue  # sem frontmatter `name:` não é agente

        track_agent, track_phase, track_version = _read_track(text)
        tools, tools_raw = _read_allowed_tools(text)
        module = _module_of(path)
        records.append({
            "agent": name,
            "version": version or "",
            "phase": PHASE_BY_MODULE.get(module, "?"),
            "module": module,
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "dispatchable": _is_dispatchable(path),
            "deprecated": "deprecated" in (version or "").lower(),
            "stub": "stub" in (version or "").lower(),
            "orchestrator": name in PHASE_ORCHESTRATORS,
            "has_track": _TRACK_MARKER in text,
            "track_agent": track_agent,
            "track_phase": track_phase,
            "track_version": track_version,
            "tools": tools,
            "tools_raw": tools_raw,
            "batch_write": _BATCH_WRITE_MARKER in text,
            "output_contract": _OUTPUT_CONTRACT_MARKER in text,
        })
    return records


# ─── API pública ─────────────────────────────────────────────────────────────

def load(refresh: bool = False) -> list[dict[str, Any]]:
    """Todos os registros de agente, com cache em memória."""
    global _CACHE
    if _CACHE is None or refresh:
        _CACHE = _scan()
    return _CACHE


def get(agent_id: str) -> dict[str, Any] | None:
    """Registro de um agente pelo id, preferindo o não-depreciado em caso de duplicata."""
    matches = [r for r in load() if r["agent"] == agent_id]
    if not matches:
        return None
    for record in matches:
        if not record["deprecated"]:
            return record
    return matches[0]


def duplicates() -> dict[str, list[str]]:
    """``{agent_id: [paths]}`` para ids declarados por mais de um arquivo.

    Registros depreciados são ignorados: `ava-asis-security-review` existe em
    duas cópias, mas a de `agents/security-review-asis.md` está marcada
    `1.4.0-DEPRECATED` e não é despachada. Remover o arquivo é limpeza separada
    (specs/032 § Fora de escopo) — o que importa aqui é não haver duas cópias
    **vivas** disputando a mesma chave de estado.
    """
    seen: dict[str, list[str]] = {}
    for record in load():
        if record["dispatchable"] and not record["deprecated"]:
            seen.setdefault(record["agent"], []).append(record["path"])
    return {agent: paths for agent, paths in seen.items() if len(paths) > 1}


def catalog() -> list[dict[str, str]]:
    """Catálogo no formato de ``AGENT_CATALOG``: despacháveis, sem depreciados.

    Ordenado por fase (transversal por último) e depois por id, para que os
    relatórios saiam estáveis entre execuções.
    """
    entries: dict[str, dict[str, str]] = {}
    for record in load():
        if not record["dispatchable"] or record["deprecated"]:
            continue
        entries[record["agent"]] = {
            "agent": record["agent"],
            "phase": record["phase"],
            "version": record["version"],
        }

    def sort_key(entry: dict[str, str]) -> tuple[int, str]:
        phase = entry["phase"]
        index = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else len(PHASE_ORDER)
        return (index, entry["agent"])

    return sorted(entries.values(), key=sort_key)


def validate() -> list[dict[str, str]]:
    """Reprova frontmatters que impedem um agente de persistir artefatos.

    As três regras derivam de falhas reais observadas em `processaERP-10/11`, onde
    diretórios de saída foram criados e ficaram **vazios** (ISSUE-002 § RC-4):

    ``AT-001``  ``allowed-tools`` separado por espaço em vez de vírgula. Toda a
                lista vira um token só e o grant não é interpretado — causa raiz de
                `outputs/asis/docs/` vazio (`documentation-asis.md`).
    ``AT-002``  Agente que referencia o `BatchWriteProtocol` sem ``Bash``. O spec
                manda gravar por `Bash` + PowerShell batch, mas a ferramenta não
                está concedida — contradição que trava toda a persistência.
    ``AT-003``  Agente com ``## Output Contract`` sem ``Write`` nem ``Bash``. Não
                tem como gravar o que promete.

    Depreciados e stubs são ignorados: `agents/security-review-asis.md` é uma
    lápide intencional com ``allowed-tools: Read``, e reprová-la seria ruído.
    """
    issues: list[dict[str, str]] = []
    for record in load():
        if not record["dispatchable"] or record["deprecated"] or record["stub"]:
            continue
        tools, raw = record["tools"], record["tools_raw"]
        if raw is None:
            continue  # sem allowed-tools declarado — fora do escopo destas regras

        if "," not in raw and len(raw.split()) > 1:
            issues.append({
                "rule": "AT-001",
                "agent": record["agent"],
                "path": record["path"],
                "detail": f"allowed-tools separado por espaço: {raw!r} — usar vírgula",
            })

        if record["batch_write"] and "Bash" not in tools:
            issues.append({
                "rule": "AT-002",
                "agent": record["agent"],
                "path": record["path"],
                "detail": "referencia BatchWriteProtocol mas não concede Bash",
            })

        if record["output_contract"] and not ({"Write", "Bash"} & set(tools)):
            issues.append({
                "rule": "AT-003",
                "agent": record["agent"],
                "path": record["path"],
                "detail": "declara Output Contract mas não concede Write nem Bash",
            })
    return issues


def orchestrator_of(phase: str) -> str | None:
    """Id do orquestrador de uma fase (``"F1"`` → ``ava-asis-orchestrator``).

    Existe para que o ponto de entrada da esteira (`copilot-cli-headroom.bat`)
    resolva a fase pelo registro em vez de carregar um mapa próprio. Um sétimo
    espelho manual de fase→agente é exatamente o defeito que originou este módulo
    (specs/032). Fases sem orquestrador registrado (F3, F7, F8) devolvem ``None``.
    """
    wanted = phase.strip().upper()
    for record in load():
        if (record["agent"] in PHASE_ORCHESTRATORS
                and record["phase"] == wanted
                and record["dispatchable"]
                and not record["deprecated"]):
            return str(record["agent"])
    return None


def catalog_or(fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    """Catálogo derivado do disco; ``fallback`` se a varredura vier vazia.

    Usado por ``pipeline_observer`` e ``generate_observability_report`` para que
    a tool continue funcionando fora da árvore do repositório.
    """
    try:
        derived = catalog()
    except Exception:  # noqa: BLE001 - catálogo nunca pode derrubar o observer
        return fallback
    return derived or fallback


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent_registry.py",
        description="Fonte canônica dos agentes da esteira (id, fase, versão)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  agent_registry.py\n"
            "  agent_registry.py --json\n"
            "  agent_registry.py --catalog\n"
            "  agent_registry.py --agent ava-qa-exploratory\n"
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emite todos os registros em JSON")
    parser.add_argument("--catalog", action="store_true", help="Emite no formato AGENT_CATALOG")
    parser.add_argument("--agent", help="Mostra apenas este agent_id")
    parser.add_argument(
        "--orchestrator",
        metavar="FASE",
        help="Imprime o id do orquestrador da fase (ex.: F1); exit 1 se não houver",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Reprova frontmatters que impedem persistência de artefatos (exit 1)",
    )
    args = parser.parse_args()

    if args.validate:
        issues = validate()
        if not issues:
            print("✅ allowed-tools: nenhum problema de persistência encontrado")
            return
        print(f"❌ {len(issues)} problema(s) de allowed-tools:\n", file=sys.stderr)
        for issue in issues:
            print(f"   [{issue['rule']}] {issue['agent']}", file=sys.stderr)
            print(f"           {issue['detail']}", file=sys.stderr)
            print(f"           {issue['path']}", file=sys.stderr)
        sys.exit(1)

    if args.orchestrator:
        agent = orchestrator_of(args.orchestrator)
        if agent is None:
            print(f"sem orquestrador registrado para a fase {args.orchestrator}",
                  file=sys.stderr)
            sys.exit(1)
        print(agent)
        return

    if args.agent:
        record = get(args.agent)
        if record is None:
            print(f"❌ agente não encontrado: {args.agent}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return

    if args.catalog:
        print(json.dumps(catalog(), indent=2, ensure_ascii=False))
        return

    records = load()
    if args.json:
        print(json.dumps(records, indent=2, ensure_ascii=False))
        return

    dispatchable = [r for r in records if r["dispatchable"]]
    print(f"📋 Registro de agentes :: {len(records)} arquivos "
          f"({len(dispatchable)} despacháveis)")
    for phase in PHASE_ORDER + [""]:
        group = [r for r in dispatchable if r["phase"] == phase]
        if not group:
            continue
        label = PHASE_NAMES.get(phase, "Transversal")
        print(f"\n   ── {phase or '--'} · {label} ({len(group)}) ──")
        for record in sorted(group, key=lambda r: r["agent"]):
            flags = "".join((
                "T" if record["has_track"] else "-",
                "O" if record["orchestrator"] else "-",
                "D" if record["deprecated"] else "-",
                "S" if record["stub"] else "-",
            ))
            print(f"   {flags}  {record['agent']:<40} {record['version'] or '(sem versão)'}")

    dups = duplicates()
    if dups:
        print("\n   ⚠️  ids duplicados:")
        for agent, paths in dups.items():
            print(f"      {agent}: {', '.join(paths)}")
    print("\n   legenda: T=track  O=orquestrador  D=depreciado  S=stub")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
