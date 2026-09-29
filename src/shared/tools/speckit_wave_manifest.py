#!/usr/bin/env python3
"""Build the deterministic wave-to-source manifest consumed by SpecKit F3S."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import prototype_manifest  # noqa: E402

# Força UTF-8 no Windows - mesma guarda de src/shared/checks/cli.py.
# Sem ela qualquer mensagem acentuada estoura UnicodeEncodeError no console
# cp1252 e a tool morre por um detalhe de terminal, não por um defeito real.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.0.0"

_BC_HEADING = re.compile(r"^##\s+(BC-\d+)\s*[:—-]\s*(.+?)\s*$", re.MULTILINE)
_WAVE_HEADING = re.compile(r"^##\s+(W\d+)\s*[—-]\s*(.+?)\s*$", re.MULTILINE)
_ANY_HEADING = re.compile(r"^##\s+\S.*$", re.MULTILINE)
_BC_ID = re.compile(r"\bBC-\d+\b")
_HEADING_BC_PAREN = re.compile(r"\(([^)]*BC-\d+[^)]*)\)")
_BC_DECLARATION = re.compile(r"^(BC-\d+)\b\s*[:—–-]?\s*([A-Za-z][A-Za-z0-9 ]*)?")
_LIST_ITEM = re.compile(r"^[-*+]\s+(.*)$")
_BOLD_RUN = re.compile(r"\*\*(.+?)\*\*")
_TRACE_ID = re.compile(r"\b(?:BR|FR)-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
_BR_ID = re.compile(r"\bBR-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")


class ManifestError(RuntimeError):
    """The wave model or its deterministic source mapping is invalid."""


def _project_dir(project: str, root: Path) -> Path:
    directory = root / "projects" / project
    if not directory.is_dir():
        raise ManifestError(f"project não encontrado: projects/{project}")
    return directory


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip("-")


def _sections(
    text: str, heading: re.Pattern[str], *, stop_at_any_heading: bool = False
) -> dict[str, tuple[str, str]]:
    matches = list(heading.finditer(text))
    # stop_at_any_heading fecha a seção também em headings `##` que não casam com
    # o padrão. Sem isso a última wave absorve os blocos finais do wave-plan.md
    # (Mapa de Dependências, Cronograma) e herda os BCs citados no Mermaid.
    boundaries = [item.start() for item in (
        _ANY_HEADING.finditer(text) if stop_at_any_heading else matches
    )]
    result: dict[str, tuple[str, str]] = {}
    for match in matches:
        end = next((pos for pos in boundaries if pos > match.start()), len(text))
        result[match.group(1)] = (match.group(2).strip(), text[match.start():end])
    return result


def _plan_contexts(name: str, section: str) -> dict[str, str]:
    """BCs que uma wave do wave-plan.md declara compor, mapeados para seu nome.

    Só posições declarativas contam: parênteses do heading da wave, célula de
    tabela, item de lista e rótulo em negrito. Menções em prosa — “BC-02 e
    BC-03 dependem de…” — são referências cruzadas de dependência entre waves,
    não composição, e contando-as o gate aborta por divergência inexistente.
    """
    found: dict[str, str] = {}

    def _record(candidate: str) -> None:
        match = _BC_DECLARATION.match(candidate.strip().strip("`").strip("*").strip())
        if not match:
            return
        bc_name = (match.group(2) or "").strip()
        if bc_name:
            found.setdefault(match.group(1), "")
            found[match.group(1)] = found[match.group(1)] or bc_name
            return
        # Sem nome logo após o id a célula é uma lista de BCs ("BC-01, BC-04").
        for bc_id in _BC_ID.findall(candidate):
            found.setdefault(bc_id, "")

    for group in _HEADING_BC_PAREN.findall(name):
        for bc_id in _BC_ID.findall(group):
            found.setdefault(bc_id, "")

    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            for cell in stripped.strip("|").split("|"):
                _record(cell)
            continue
        item = _LIST_ITEM.match(stripped)
        if item:
            _record(item.group(1))
        for bold in _BOLD_RUN.findall(stripped):
            _record(bold)
    return found


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({value.strip() for value in values if value and value.strip()})


def _normalize_model_waves(waves: list[Any], *, strict: bool = True,
                           warnings: list[str] | None = None) -> list[dict[str, Any]]:
    """Accept legacy context IDs while preserving the canonical context shape.

    Com ``strict=False`` um contexto sem nome resolvível degrada para
    ``bc_name == bc_id`` e registra um aviso, em vez de abortar. É o modo do
    caminho de remediação da F3S: um nome de BC provisório produz um recorte
    vertical com rótulo feio, mas produz — enquanto abortar não gera artefato
    nenhum e trava as fases seguintes. O modo estrito continua sendo o padrão,
    porque é ele que faz o gate reprovar um artefato incoerente.
    """
    avisos = warnings if warnings is not None else []
    normalized: list[dict[str, Any]] = []
    for wave_index, raw_wave in enumerate(waves):
        if not isinstance(raw_wave, dict):
            raise ManifestError(
                f"wave-model.json waves[{wave_index}] precisa ser um objeto, "
                f"recebido {type(raw_wave).__name__}"
            )
        wave = dict(raw_wave)
        raw_contexts = wave.get("bounded_contexts") or []
        if not isinstance(raw_contexts, list):
            raise ManifestError(
                f"wave-model.json waves[{wave_index}].bounded_contexts precisa ser uma lista"
            )

        string_contexts = [item for item in raw_contexts if isinstance(item, str)]
        if string_contexts:
            raw_details = wave.get("bc_details") or []
            if not isinstance(raw_details, list) or not all(
                isinstance(item, dict) for item in raw_details
            ):
                if strict:
                    raise ManifestError(
                        f"wave-model.json waves[{wave_index}] usa IDs textuais em "
                        "bounded_contexts, mas não declara bc_details[] válido"
                    )
                avisos.append(
                    f"waves[{wave_index}] usa IDs textuais sem bc_details[] válido; "
                    "nomes de BC degradados para o próprio id")
                raw_details = []
            details_by_id = {
                str(item.get("bc_id") or "").strip(): item
                for item in raw_details
                if str(item.get("bc_id") or "").strip()
            }
        else:
            details_by_id = {}

        contexts: list[dict[str, Any]] = []
        for context_index, raw_context in enumerate(raw_contexts):
            if isinstance(raw_context, dict):
                contexts.append(dict(raw_context))
                continue
            if not isinstance(raw_context, str) or not raw_context.strip():
                raise ManifestError(
                    f"wave-model.json waves[{wave_index}].bounded_contexts["
                    f"{context_index}] precisa ser um objeto ou um BC ID textual"
                )
            bc_id = raw_context.strip()
            detail = details_by_id.get(bc_id)
            bc_name = str(detail.get("bc_name") or "").strip() if detail else ""
            if not bc_name:
                if strict:
                    raise ManifestError(
                        f"wave-model.json waves[{wave_index}] não declara bc_details "
                        f"para bounded_contexts={bc_id!r}"
                    )
                avisos.append(
                    f"waves[{wave_index}]: {bc_id} sem bc_details — nome degradado "
                    f"para o próprio id")
                bc_name = bc_id
            contexts.append({"bc_id": bc_id, "bc_name": bc_name})

        wave["bounded_contexts"] = contexts
        normalized.append(wave)
    return normalized


def _load_model(project: str, project_dir: Path, *, strict: bool = True
                ) -> tuple[list[dict[str, Any]], str, str, list[str]]:
    model_path = project_dir / "outputs" / "tobe" / "migration" / "wave-model.json"
    plan_path = project_dir / "outputs" / "tobe" / "docs" / "wave-plan.md"
    warnings: list[str] = []
    if model_path.is_file():
        try:
            data = json.loads(model_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"wave-model.json inválido: {exc}") from exc
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        declared_project = str(data.get("project") or metadata.get("project_name") or "")
        if declared_project and declared_project != project:
            raise ManifestError(
                f"wave-model.json project={declared_project!r}, esperado {project!r}"
            )
        waves = data.get("waves")
        if not isinstance(waves, list) or not waves:
            raise ManifestError("wave-model.json precisa declarar waves[] não vazio")
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        declared_total = data.get("total_waves")
        if declared_total is None:
            declared_total = summary.get("total_waves")
        if declared_total is not None and int(declared_total) != len(waves):
            raise ManifestError(
                f"wave-model.json declara total_waves={declared_total}, mas contém {len(waves)}"
            )
        return _normalize_model_waves(waves, strict=strict, warnings=warnings), str(
            data.get("trace_id") or metadata.get("trace_id") or ""), (
            "outputs/tobe/migration/wave-model.json"
        ), warnings

    text = _read(plan_path)
    wave_sections = _sections(text, _WAVE_HEADING, stop_at_any_heading=True)
    if not wave_sections:
        raise ManifestError("wave-model.json ausente e wave-plan.md não contém waves parseáveis")
    warnings.append(
        "wave-model.json ausente; composição derivada de wave-plan.md em modo fallback"
    )
    waves: list[dict[str, Any]] = []
    previous: str | None = None
    for wave_id, (name, section) in wave_sections.items():
        contexts = [
            {"bc_id": bc_id, "bc_name": bc_name or bc_id}
            for bc_id, bc_name in sorted(_plan_contexts(name, section).items())
        ]
        lowered = name.lower()
        wave_type = "foundation" if wave_id == "W0" else (
            "cutover" if "cutover" in lowered else "domain"
        )
        waves.append({
            "wave_id": wave_id,
            "wave_name": name,
            "wave_type": wave_type,
            "description": "",
            "bounded_contexts": contexts,
            "dependencies": [previous] if previous else [],
            "acceptance_criteria": [],
        })
        previous = wave_id
    return waves, "", "outputs/tobe/docs/wave-plan.md", warnings


def _source(source_id: str, artifact: str, anchors: Iterable[str]) -> dict[str, Any] | None:
    unique = _unique(anchors)
    if not unique:
        return None
    return {"source_id": source_id, "artifact": artifact, "anchors": unique}


def _wave_id(value: Any) -> str:
    text = str(value).strip()
    if re.fullmatch(r"\d+", text):
        return f"W{int(text)}"
    return text.upper()


def _wave_dependencies(wave: dict[str, Any]) -> list[str]:
    raw = wave.get("dependencies")
    if raw is None:
        raw = wave.get("depends_on_waves") or []
    return [_wave_id(item) for item in raw]


def _markdown_bc_index(path: Path, id_pattern: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    anchors: dict[str, list[str]] = {}
    refs: dict[str, list[str]] = {}
    for bc_id, (_name, section) in _sections(_read(path), _BC_HEADING).items():
        anchors[bc_id] = _unique(re.findall(id_pattern, section))
        refs[bc_id] = _unique(_TRACE_ID.findall(section))
    return anchors, refs


def _openapi_index(directory: Path) -> dict[str, list[tuple[str, list[str]]]]:
    result: dict[str, list[tuple[str, list[str]]]] = {}
    for path in sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")]):
        text = _read(path)
        match = re.search(r"^\s*x-source-bc:\s*[\"']?(BC-\d+)", text, re.MULTILINE)
        if not match:
            match = re.search(r"\bbc[-_ ]?(\d{1,3})\b", path.stem, re.IGNORECASE)
            bc_id = f"BC-{int(match.group(1)):02d}" if match else ""
        else:
            bc_id = match.group(1)
        if not bc_id:
            continue
        operations = _unique(re.findall(
            r"^\s*operationId:\s*[\"']?([A-Za-z0-9_.-]+)", text, re.MULTILINE
        ))
        if operations:
            artifact = path.relative_to(directory.parents[3]).as_posix()
            result.setdefault(bc_id, []).append((artifact, operations))
    return result


def _api_map_index(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for line in _read(path).splitlines():
        if not line.lstrip().startswith("|") or re.match(r"^\s*\|?\s*-+", line):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        bc = next((cell for cell in cells if re.fullmatch(r"BC-\d+", cell)), None)
        if bc and cells and cells[0].lower() not in {"flow", "fluxo"}:
            result.setdefault(bc, []).append(cells[0])
    return result


def _prototype_index(path: Path, bc_names: dict[str, str]) -> dict[str, list[str]]:
    by_name = {_slug(name): bc_id for bc_id, name in bc_names.items()}
    result: dict[str, list[str]] = {}
    for line in _read(path).splitlines():
        if not line.lstrip().startswith("|") or re.match(r"^\s*\|?\s*-+", line):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"screen", "tela"}:
            continue
        bc_id = by_name.get(_slug(cells[1]))
        if bc_id:
            result.setdefault(bc_id, []).append(cells[0])
    return result


def _openapi_endpoint_index(directory: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """`(MÉTODO, path)` → `(operationId, artefato)`.

    É a junção que faltava entre o protótipo e o contrato: `screen-list.md`
    declara `GET /api/v1/funcoes`, o OpenAPI declara `operationId:
    GetAllFuncoes`, e ninguém ligava os dois. Sem essa ligação, a tela nunca
    encontra a operação de API e FRONTEND-API-CLIENT-COVERAGE não teria como
    exigir o client — que é exatamente o buraco entre frontend e backend.

    Parsing textual do YAML, deliberadamente: os OpenAPI da esteira são
    gerados e regulares, e adicionar um parser YAML completo aqui traria uma
    dependência para resolver um caso que a regex resolve com evidência.
    """
    index: dict[tuple[str, str], tuple[str, str]] = {}
    if not directory.is_dir():
        return index
    verbs = ("get", "post", "put", "patch", "delete", "head", "options")
    for path in sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")]):
        text = _read(path)
        try:
            artifact = path.relative_to(directory.parents[3]).as_posix()
        except ValueError:
            artifact = path.name
        bases = _unique(
            match.rstrip("/") for match in
            re.findall(r"^\s*-?\s*url:\s*[\"']?[a-z]+://[^/\s\"']+(/[^\s\"']*)",
                       text, re.MULTILINE)
            if match.rstrip("/")
        )
        current_route = ""
        current_verb = ""
        for line in text.splitlines():
            route = re.match(r"^\s{0,4}(/[A-Za-z0-9_\-/{}.:]*)\s*:\s*$", line)
            if route:
                current_route = route.group(1)
                current_verb = ""
                continue
            verb = re.match(r"^\s{2,8}(" + "|".join(verbs) + r")\s*:\s*$", line)
            if verb and current_route:
                current_verb = verb.group(1).upper()
                continue
            operation = re.match(r"^\s*operationId\s*:\s*[\"']?([A-Za-z0-9_.-]+)", line)
            if operation and current_route and current_verb:
                # Indexa a rota crua E prefixada por cada base declarada em
                # `servers.url`. O protótipo escreve `GET /api/v1/funcionarios`
                # (a URL que o browser chamaria) e o OpenAPI escreve
                # `/funcionarios` sob `servers: .../api/v1`. Sem casar as duas
                # grafias, NENHUM endpoint de tela resolvia para operationId —
                # medido em cadastro-funcionarios-04: 10 endpoints, 0 resolvidos,
                # e com isso o elo protótipo→API ficava vazio justamente no
                # ponto que este trabalho existe para consertar.
                for base in bases:
                    index.setdefault((current_verb, base + current_route),
                                     (operation.group(1), artifact))
                index.setdefault((current_verb, current_route),
                                 (operation.group(1), artifact))
    return index


def _normalize_route(path: str) -> str:
    """Rota sem query e com placeholders neutralizados, para casar contra o OpenAPI."""
    base = str(path or "").split("?", 1)[0].rstrip("/") or "/"
    return re.sub(r"\{[^}]*\}", "{}", base)


def _resolve_endpoint_operations(
    endpoints: list[dict[str, Any]],
    index: dict[tuple[str, str], tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve endpoints da tela contra o OpenAPI. Não inventa operationId.

    Endpoint sem correspondência sai com `operation_id: None` e vira aviso — a
    proibição do §21 ("não inventar operationId") é implementada aqui, não só
    pedida no prompt.
    """
    normalized_index = {
        (verb, _normalize_route(route)): value for (verb, route), value in index.items()
    }
    resolved: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for endpoint in endpoints:
        method = str(endpoint.get("method") or "").upper()
        route = _normalize_route(endpoint.get("path"))
        hit = normalized_index.get((method, route))
        entry = dict(endpoint)
        if hit:
            entry["operation_id"], entry["artifact"] = hit
        else:
            entry["operation_id"] = None
            entry["artifact"] = None
            unresolved.append(f"{method} {endpoint.get('path')}")
        resolved.append(entry)
    return resolved, unresolved


def _load_prototype(project: str, root: Path,
                    warnings: list[str]) -> dict[str, Any] | None:
    """Manifesto do protótipo — de disco quando existe, calculado quando não.

    Os dois caminhos são necessários e produzem o mesmo objeto: `pipeline_plan`
    chama `build_manifest()` em processo para descobrir o fan-out ANTES da
    wave2 gravar qualquer coisa em disco, então exigir o arquivo aqui tornaria
    a F3S impossível de planejar na primeira execução.
    """
    from_disk = prototype_manifest.load_manifest(project, root)
    if from_disk is not None:
        return from_disk
    try:
        return prototype_manifest.build_manifest(project, root, strict=False)
    except prototype_manifest.PrototypeManifestError as exc:
        warnings.append(f"protótipo indisponível para o recorte por wave: {exc}")
        return None


def _shared_component_owner(features: list[dict[str, Any]]) -> str | None:
    """Feature que cria os componentes compartilhados e o Design System.

    Regra determinística e única, para satisfazer SINGLE-CREATE-OWNER: a
    foundation, quando existe; senão a primeira wave de codegen. Sem isto cada
    wave reivindicava `create` do mesmo botão compartilhado — foi assim que
    `cadastro-funcionarios-04` acumulou 31 conflitos de ownership, 24 deles
    cross-wave. A informação existia; faltava alguém decidir uma vez só.
    """
    foundation = [item for item in features
                  if item.get("wave_type") == "foundation" and item.get("codegen")]
    if foundation:
        return foundation[0]["feature"]
    codegen = [item for item in features if item.get("codegen")]
    return codegen[0]["feature"] if codegen else None


def _prototype_slice(prototype: dict[str, Any], bc_ids: list[str],
                     *, owns_shared: bool,
                     endpoint_index: dict[tuple[str, str], tuple[str, str]],
                     ) -> dict[str, Any]:
    """Recorte FECHADO do protótipo para uma migration wave.

    O que a wave recebe: as telas dos seus bounded contexts, os componentes que
    essas telas usam, as rotas dessas telas e as operações de API dessas telas.
    Quem é dono do compartilhado recebe também o Design System inteiro e o
    catálogo de componentes compartilhados.

    O que a wave NÃO recebe: o `index.html`. O agente lê o manifesto, não o
    protótipo cru — é o que impede que "a fatia vertical" volte a ser "a base
    inteira" (§21 do briefing).
    """
    wanted = set(bc_ids)
    screens = [screen for screen in prototype.get("screens") or []
               if screen.get("bounded_context") in wanted]
    shared_ids = {component["component_id"]
                  for component in prototype.get("shared_components") or []}

    screen_entries: list[dict[str, Any]] = []
    api_ops: set[str] = set()
    unresolved: list[str] = []
    component_ids: set[str] = set()
    route_ids: set[str] = set()
    token_ids: set[str] = set()
    html_anchors: set[str] = set()

    for screen in sorted(screens, key=lambda item: item["screen_id"]):
        endpoints, missing = _resolve_endpoint_operations(
            screen.get("api_endpoints") or [], endpoint_index)
        unresolved.extend(f"{screen['screen_id']}: {item}" for item in missing)
        own = sorted({component["component_id"]
                      for component in screen.get("components") or []
                      if component["component_id"] not in shared_ids})
        used_shared = sorted({component["component_id"]
                              for component in screen.get("components") or []
                              if component["component_id"] in shared_ids})
        component_ids.update(own)
        route_ids.add(screen["route_id"]) if screen.get("route_id") else None
        token_ids.update(screen.get("design_tokens") or [])
        if screen.get("html_id"):
            html_anchors.add(screen["html_id"])
        operations = sorted({item["operation_id"] for item in endpoints
                             if item.get("operation_id")})
        api_ops.update(operations)
        screen_entries.append({
            "screen_id": screen["screen_id"],
            "name": screen["name"],
            "route": screen.get("route"),
            "route_id": screen.get("route_id"),
            "bounded_context": screen.get("bounded_context"),
            "dynamic": bool(screen.get("dynamic")),
            "static_justification": screen.get("static_justification"),
            "source_anchor": screen["source_anchor"],
            "component_ids": own,
            "shared_component_ids": used_shared,
            "form_ids": [form["form_id"] for form in screen.get("forms") or []],
            "table_ids": [table["table_id"] for table in screen.get("tables") or []],
            "action_ids": [action["action_id"] for action in screen.get("actions") or []],
            "states": sorted({state["state"] for state in screen.get("states") or []}),
            "navigation_targets": list(screen.get("navigation_targets") or []),
            "design_tokens": list(screen.get("design_tokens") or []),
            "api_endpoints": endpoints,
            "api_ops": operations,
            "accessibility_hints": list(screen.get("accessibility_hints") or []),
            "responsive_hints": list(screen.get("responsive_hints") or []),
        })

    design_system: dict[str, Any] = {}
    owned_components: list[dict[str, Any]] = []
    if owns_shared:
        catalogue = prototype.get("design_system") or {}
        design_system = {
            key: list(catalogue.get(key) or [])
            for key in ("colors", "typography", "spacing", "other_tokens",
                        "breakpoints", "icons", "global_styles", "component_patterns")
        }
        owned_components = list(prototype.get("shared_components") or [])
        token_ids.update(
            token["token_id"] for key in ("colors", "typography", "spacing",
                                          "other_tokens")
            for token in design_system.get(key) or [])

    screen_ids = [entry["screen_id"] for entry in screen_entries]
    flows = [flow for flow in prototype.get("flows") or []
             if all(item in screen_ids for item in flow.get("screens") or [])]
    crossing = [flow for flow in prototype.get("flows") or []
                if any(item in screen_ids for item in flow.get("screens") or [])
                and not all(item in screen_ids for item in flow.get("screens") or [])]

    return {
        "screens": screen_entries,
        "routes": sorted(route_ids),
        "component_ids": sorted(component_ids),
        "shared_component_ids": sorted(shared_ids) if owns_shared else sorted(
            {cid for entry in screen_entries for cid in entry["shared_component_ids"]}),
        "owns_shared_components": owns_shared,
        "owned_shared_components": owned_components,
        "design_system": design_system,
        "design_tokens": sorted(token_ids),
        "api_ops": sorted(api_ops),
        "unresolved_endpoints": sorted(set(unresolved)),
        "flows": [flow["flow_id"] for flow in flows],
        "crossing_flows": [flow["flow_id"] for flow in crossing],
        "html_anchors": sorted(html_anchors),
    }


def _attach_prototype(project: str, root: Path, features: list[dict[str, Any]],
                      warnings: list[str],
                      endpoint_index: dict[tuple[str, str], tuple[str, str]]) -> None:
    """Anexa a cada feature o recorte do protótipo e as âncoras correspondentes.

    Muta `features` no lugar porque o manifesto de waves continua sendo UM
    artefato: um segundo arquivo "manifesto de frontend" seria a segunda fonte
    de verdade que o F3S.yaml existe para impedir.
    """
    prototype = _load_prototype(project, root, warnings)
    if prototype is None:
        for feature in features:
            feature["prototype"] = None
        return

    owner = _shared_component_owner(features)
    assigned_screens: set[str] = set()

    for feature in features:
        if not feature.get("codegen"):
            feature["prototype"] = None
            continue
        bc_ids = [item["bc_id"] for item in feature["bounded_contexts"]]
        slice_ = _prototype_slice(
            prototype, bc_ids,
            owns_shared=(feature["feature"] == owner),
            endpoint_index=endpoint_index)
        feature["prototype"] = slice_
        assigned_screens.update(entry["screen_id"] for entry in slice_["screens"])

        # Âncoras FECHADAS. `prototype-manifest` carrega os ids estáveis (que
        # existem literalmente no JSON, então CHK-SK-006 os encontra ao reabrir
        # o arquivo); `prototype` carrega os ids de seção do index.html, para
        # que a rastreabilidade chegue ao HTML original sem despejá-lo inteiro
        # no contexto do agente.
        anchors = [
            *(entry["screen_id"] for entry in slice_["screens"]),
            *slice_["component_ids"],
            *slice_["shared_component_ids"],
            *slice_["routes"],
            *slice_["design_tokens"],
        ]
        item = _source("prototype-manifest", prototype_manifest.MANIFEST_REL, anchors)
        if item:
            feature["sources"].append(item)
        html = _source("prototype-html", prototype_manifest.PROTOTYPE_REL,
                       slice_["html_anchors"])
        if html:
            feature["sources"].append(html)
        if slice_["api_ops"]:
            existing = {source["source_id"] for source in feature["sources"]}
            if "api" not in existing:
                # A wave consome operações que o índice por BC do OpenAPI não
                # atribuiu a ela. Registrar a fonte é o que permite ao gate
                # cobrar a task de backend sem que o agente precise adivinhar.
                feature["sources"].append({
                    "source_id": "api-operations",
                    "artifact": "outputs/tobe/docs/openapi",
                    "anchors": list(slice_["api_ops"]),
                })
        for unresolved in slice_["unresolved_endpoints"]:
            warnings.append(
                f"{feature['feature']}: endpoint do protótipo sem operationId no "
                f"OpenAPI — {unresolved} (nenhuma operação foi inventada)")
        feature["sources"].sort(key=lambda source: (source["source_id"],
                                                    source["artifact"]))

    orphan_screens = sorted(
        screen["screen_id"] for screen in prototype.get("screens") or []
        if screen["screen_id"] not in assigned_screens)
    if orphan_screens:
        warnings.append(
            "telas do protótipo sem migration wave (bounded context ausente ou "
            f"não modelado): {', '.join(orphan_screens[:8])}"
            f"{'…' if len(orphan_screens) > 8 else ''}")
    if owner is None:
        warnings.append(
            "nenhuma feature de codegen para receber ownership do Design System "
            "e dos componentes compartilhados")


def build_manifest(project: str, repo_root: Path | None = None, *,
                   strict: bool = True) -> dict[str, Any]:
    """Return the complete manifest without writing to disk."""
    root = repo_root or REPO_ROOT
    project_dir = _project_dir(project, root)
    outputs = project_dir / "outputs"
    waves, trace_id, wave_source, warnings = _load_model(project, project_dir,
                                                        strict=strict)

    backlog_path = outputs / "tobe" / "docs" / "backlog-tobe.md"
    tests_path = outputs / "tobe" / "qa" / "test-cases.md"
    rules_path = outputs / "asis" / "docs" / "business-rules.md"
    api_map_path = outputs / "tobe" / "docs" / "api-map.md"
    prototype_path = outputs / "tobe" / "prototype" / "screen-list.md"
    plan_path = outputs / "tobe" / "docs" / "wave-plan.md"

    backlog, backlog_refs = _markdown_bc_index(backlog_path, r"\bUS-[A-Z0-9-]+\b")
    tests, test_refs = _markdown_bc_index(tests_path, r"\bTC-[A-Z0-9-]+\b")
    rule_source_catalog = set(_TRACE_ID.findall(_read(rules_path)))
    business_rule_catalog = set(_BR_ID.findall(_read(rules_path)))
    openapi = _openapi_index(outputs / "tobe" / "docs" / "openapi")
    openapi_endpoints = _openapi_endpoint_index(outputs / "tobe" / "docs" / "openapi")
    api_map = _api_map_index(api_map_path)

    all_bc_names = {
        str(context.get("bc_id")): str(context.get("bc_name"))
        for wave in waves for context in (wave.get("bounded_contexts") or [])
        if context.get("bc_id") and context.get("bc_name")
    }
    prototype = _prototype_index(prototype_path, all_bc_names)

    plan_sections = _sections(
        _read(plan_path), _WAVE_HEADING, stop_at_any_heading=True
    ) if plan_path.is_file() else {}
    plan_wave_ids = set(plan_sections)
    model_wave_ids = {
        _wave_id(wave.get("wave_id") if wave.get("wave_id") is not None
                 else wave.get("wave_number"))
        for wave in waves
    }
    if plan_wave_ids and plan_wave_ids != model_wave_ids:
        raise ManifestError(
            "wave-plan.md diverge do wave-model.json: "
            f"model={sorted(model_wave_ids)}, plan={sorted(plan_wave_ids)}"
        )
    model_contexts = {
        _wave_id(wave.get("wave_id") if wave.get("wave_id") is not None
                 else wave.get("wave_number")): {
            str(context.get("bc_id")) for context in (wave.get("bounded_contexts") or [])
            if context.get("bc_id")
        }
        for wave in waves
    }
    for wave_id, (plan_name, section) in plan_sections.items():
        explicit = set(_plan_contexts(plan_name, section))
        declared = model_contexts.get(wave_id, set())
        if explicit and explicit != declared:
            delta = []
            if explicit - declared:
                delta.append(f"só no plan={sorted(explicit - declared)}")
            if declared - explicit:
                delta.append(f"só no modelo={sorted(declared - explicit)}")
            raise ManifestError(
                f"{wave_id}: BCs do wave-plan.md divergem do modelo: "
                f"model={sorted(declared)}, plan={sorted(explicit)} ({'; '.join(delta)})"
            )

    features: list[dict[str, Any]] = []
    wave_ids: set[str] = set()
    for order, wave in enumerate(waves, start=1):
        raw_wave_id = wave.get("wave_id") if wave.get("wave_id") is not None \
            else wave.get("wave_number")
        wave_id = _wave_id(raw_wave_id)
        if not re.fullmatch(r"W\d+", wave_id) or wave_id in wave_ids:
            raise ManifestError(f"wave_id inválido ou duplicado: {wave_id!r}")
        wave_ids.add(wave_id)
        name = str(wave.get("wave_name") or wave_id).strip()
        slug_name = re.sub(
            rf"^{re.escape(wave_id)}\s*[—-]\s*", "", name, flags=re.IGNORECASE
        )
        contexts = [
            {"bc_id": str(item.get("bc_id")), "bc_name": str(item.get("bc_name"))}
            for item in (wave.get("bounded_contexts") or [])
            if item.get("bc_id") and item.get("bc_name")
        ]
        bc_ids = [item["bc_id"] for item in contexts]
        refs = set()
        for bc_id in bc_ids:
            refs.update(backlog_refs.get(bc_id, []))
            refs.update(test_refs.get(bc_id, []))

        sources: list[dict[str, Any]] = []
        candidates = [
            _source("wave-model", wave_source, [wave_id]),
            _source("wave-plan", "outputs/tobe/docs/wave-plan.md", [wave_id])
            if plan_path.is_file() else None,
                _source("business-rules", "outputs/asis/docs/business-rules.md",
                    refs & rule_source_catalog),
            _source("api-map", "outputs/tobe/docs/api-map.md",
                    (anchor for bc_id in bc_ids for anchor in api_map.get(bc_id, []))),
            _source("backlog", "outputs/tobe/docs/backlog-tobe.md",
                    (anchor for bc_id in bc_ids for anchor in backlog.get(bc_id, []))),
            _source("test-cases", "outputs/tobe/qa/test-cases.md",
                    (anchor for bc_id in bc_ids for anchor in tests.get(bc_id, []))),
            _source("prototype", "outputs/tobe/prototype/screen-list.md",
                    (anchor for bc_id in bc_ids for anchor in prototype.get(bc_id, []))),
        ]
        sources.extend(item for item in candidates if item is not None)
        for bc_id in bc_ids:
            for artifact, anchors in openapi.get(bc_id, []):
                item = _source("api", artifact, anchors)
                if item:
                    sources.append(item)

        wave_type = str(wave.get("wave_type") or "domain")
        features.append({
            "wave_id": wave_id,
            "migration_wave_order": order - 1,
            "feature": f"{order:03d}-{_slug(wave_id)}-{_slug(slug_name)}",
            "title": name,
            "wave_type": wave_type,
            "description": str(wave.get("description") or wave.get("scope_description") or ""),
            "bounded_contexts": contexts,
            "depends_on": _wave_dependencies(wave),
            "acceptance_criteria": [
                str(item) for item in (wave.get("acceptance_criteria") or [])
            ],
            # Foundation é executável: contém o scaffold determinístico das
            # stacks e precisa participar de plan/tasks antes das waves de domínio.
            "codegen": wave_type != "cutover",
            "sources": sources,
        })

    _attach_prototype(project, root, features, warnings, openapi_endpoints)

    dangling = sorted({dependency for feature in features for dependency in feature["depends_on"]}
                      - wave_ids)
    if dangling:
        raise ManifestError(f"waves dependem de ids inexistentes: {', '.join(dangling)}")

    assigned: dict[str, set[str]] = defaultdict(set)
    for feature in features:
        for item in feature["sources"]:
            assigned[item["source_id"]].update(item["anchors"])
    all_openapi_operations = set()
    for path in sorted([*(outputs / "tobe" / "docs" / "openapi").glob("*.yaml"),
                        *(outputs / "tobe" / "docs" / "openapi").glob("*.yml")]):
        all_openapi_operations.update(re.findall(
            r"^\s*operationId:\s*[\"']?([A-Za-z0-9_.-]+)", _read(path), re.MULTILINE
        ))
    catalogs = {
        "business-rules": business_rule_catalog,
        "api": all_openapi_operations,
        "backlog": {anchor for values in backlog.values() for anchor in values},
        "test-cases": {anchor for values in tests.values() for anchor in values},
    }
    unassigned = {
        source_id: sorted(values - assigned.get(source_id, set()))
        for source_id, values in catalogs.items()
        if values - assigned.get(source_id, set())
    }
    if unassigned:
        rendered = "; ".join(
            f"{source_id}={','.join(values[:8])}" for source_id, values in unassigned.items()
        )
        warnings.append(
            f"âncoras formais sem migration wave (transversais/não mapeadas): {rendered}"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "trace_id": trace_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wave_source": wave_source,
        "wave_plan": "outputs/tobe/docs/wave-plan.md" if plan_path.is_file() else None,
        "total_waves": len(features),
        "warnings": warnings,
        "features": features,
    }


def write_manifest(project: str, repo_root: Path | None = None, *,
                   strict: bool = True) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    output = build_manifest(project, root, strict=strict)
    target = _project_dir(project, root) / "outputs" / "tobe" / "speckit" / "wave-spec-manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speckit_wave_manifest.py")
    parser.add_argument("--project", "-p", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn", action="store_true",
                        help="converte erros de validação em avisos e retorna exit 0")
    args = parser.parse_args(argv)
    try:
        result = write_manifest(args.project)
    except ManifestError as exc:
        if args.warn:
            warning = {
                "status": "warning",
                "message": str(exc),
                "command": "speckit_wave_manifest",
                "project": args.project,
            }
            print(json.dumps(warning, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        if args.warn:
            warning = {
                "status": "warning",
                "message": f"{type(exc).__name__}: {exc}",
                "command": "speckit_wave_manifest",
                "project": args.project,
            }
            print(json.dumps(warning, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {type(exc).__name__}: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        raise
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"wave-spec-manifest.json: {result['total_waves']} wave(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())