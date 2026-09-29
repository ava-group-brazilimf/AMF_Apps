#!/usr/bin/env python3
"""Extrai o protótipo navegável da F3 para um manifesto determinístico da F3S.

Por que existe
--------------
Até aqui a F3S enxergava o protótipo por uma fresta: `screen-list.md` servia
para associar tela → bounded context por *slug*, e `index.html` não entrava em
lugar nenhum do planejamento. O resultado medido em `nopcommerce-02-cli-ava`
(RC-04) foi **7 de 15 telas ausentes** e 2 fiéis — o agente de frontend nunca
recebeu o layout que precisava reproduzir, então reinterpretou.

O `prototype_coverage` já reprovava isso, mas *depois*: ele confere a
`spec-prototype.md`. O que faltava era o protótipo virar **entrada formal** do
planejamento, com âncoras fechadas por wave — e é isto.

O que este módulo NÃO faz
-------------------------
* **Não executa JavaScript.** A extração é estática: `html.parser` da stdlib +
  regex sobre CSS. `onclick="showScreen('x')"` é lido como *texto* para
  descobrir o alvo de navegação; nada é avaliado.
* **Não infere comportamento.** Se o HTML/CSS/`screen-list.md` não dizem, o
  manifesto emite um warning estruturado (`PM-0xx`) em vez de inventar. Esta é
  a regra que separa este arquivo de um agente: um agente preenche a lacuna,
  uma tool determinística a declara.
* **Não baixa asset externo.** `https://…` vira `scope: external` — dependência
  declarada, nunca resolvida aqui.
* **Não usa LLM.** Nenhuma etapa da estrutura básica depende de modelo.

Determinismo
------------
Toda coleção sai ordenada por id; os ids derivam do conteúdo (id do HTML, nome
da classe, nome do campo), nunca da ordem de iteração de um `set` ou de um
`dict` de entrada. `generated_at` é o único campo não normativo e está fora dos
dois checksums — `build_manifest()` chamado duas vezes sobre as mesmas entradas
produz o mesmo JSON exceto por esse campo. Travado por
`tests/tools/test_prototype_manifest.py::test_determinismo_entre_execucoes`.

Uso
---
    python src/shared/tools/prototype_manifest.py --project Meu-ERP --json
    python src/shared/tools/prototype_manifest.py -p Meu-ERP --verify   # checksum
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover — pyyaml está no venv do repo
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[3]

# Força UTF-8 no Windows — mesma guarda de src/shared/checks/cli.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.0.0"

#: Caminho canônico do manifesto, relativo ao diretório do projeto. A F3S grava
#: tudo em `outputs/tobe/speckit` (`output_base` do F3S.yaml); manter um segundo
#: diretório para este artefato criaria a segunda fonte de verdade que o
#: cabeçalho do F3S.yaml existe para evitar.
MANIFEST_REL = "outputs/tobe/speckit/prototype-implementation-manifest.json"
PROTOTYPE_REL = "outputs/tobe/prototype/index.html"
SCREEN_LIST_REL = "outputs/tobe/prototype/screen-list.md"
DESIGN_TOKENS_REL = "outputs/tobe/prototype/design-tokens.json"
BC_MAP_REL = "outputs/tobe/docs/bounded-context-map.md"
PROJECT_CONFIG_REL = "context/project-config.yaml"


class PrototypeManifestError(RuntimeError):
    """Falha TÉCNICA: fonte obrigatória ausente, ilegível ou insegura.

    Distinta de warning: warning é lacuna de informação do protótipo; esta
    exceção é o pipeline não conseguir ler o que precisa. A separação segue a
    política do F3S.yaml — erro técnico tem exit != 0, defeito semântico não.
    """


# ─── Helpers determinísticos ─────────────────────────────────────────────────

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})

_STATE_WORDS = {
    "loading": "loading", "spinner": "loading", "skeleton": "loading",
    "empty": "empty", "no-data": "empty", "no-results": "empty",
    "error": "error", "danger": "error", "invalid": "validation",
    "success": "success", "disabled": "disabled",
    "validation": "validation", "required": "validation",
}

#: Classes que caracterizam um componente e o seu tipo. Ordem importa: a
#: primeira que casar vence, então o mais específico vem antes.
_KIND_BY_CLASS = (
    ("modal", "modal"), ("dialog", "modal"),
    ("sidebar", "navigation"), ("navbar", "navigation"),
    ("breadcrumb", "navigation"), ("menu", "navigation"), ("tabs", "navigation"),
    ("toolbar", "toolbar"),
    # `form` ANTES de `grid`/`table`: medido em cadastro-funcionarios-04, a
    # classe `form-grid` (o layout de duas colunas do formulário) casava com
    # `grid` e virava `CMP-TABLE-FORM-GRID` — um componente de tabela que não
    # existe, herdado por 5 telas. A ordem é a regra de desempate; o mais
    # semântico vem antes do mais genérico.
    ("form", "form"),
    ("data-table", "table"), ("table", "table"), ("grid", "table"),
    ("actions", "toolbar"),
    ("card", "card"), ("panel", "card"), ("tile", "card"),
    ("alert", "feedback"), ("toast", "feedback"), ("badge", "feedback"),
    ("field", "field"), ("input", "field"),
    ("list", "list"),
    ("btn", "button"), ("button", "button"),
    ("layout", "layout"), ("container", "layout"), ("header", "layout"),
    ("footer", "layout"), ("main", "layout"),
)

#: Componentes ESTRUTURAIS: os que precisam existir como unidade de código na
#: stack alvo, e por isso são cobrados por PROTOTYPE-COMPONENT-COVERAGE. Botão e
#: campo ficam de fora de propósito — eles são implementados *dentro* do
#: formulário, da tabela ou da toolbar que os contém, e exigir uma task por
#: botão tornaria o gate permanentemente irreprovável sem melhorar nada.
_STRUCTURAL_KINDS = frozenset({
    "layout", "navigation", "form", "table", "modal", "card", "feedback",
    "list", "toolbar", "region",
})

#: Elementos cujo TEXTO é o nome natural do componente. Restrito a elementos
#: folha: usar `.text()` de uma `<section>` traria a tela inteira como nome.
_TEXT_NAMED_TAGS = frozenset({
    "button", "a", "label", "th", "legend", "h1", "h2", "h3", "h4", "h5", "h6",
})

_KIND_BY_TAG = {
    "form": "form", "table": "table", "nav": "navigation",
    "button": "button", "header": "layout", "footer": "layout",
    "main": "layout", "aside": "layout", "section": "region",
    "input": "field", "select": "field", "textarea": "field",
    "ul": "list", "ol": "list", "dialog": "modal",
}

_TOKEN_CATEGORY = (
    ("colors", ("color", "bg", "background", "surface", "border", "shadow-color",
                "primary", "secondary", "danger", "success", "warning", "error",
                "hover", "on-")),
    ("typography", ("font", "line-height", "letter", "text-size", "weight",
                    "heading")),
    ("spacing", ("space", "spacing", "gap", "padding", "margin", "width",
                 "height", "size", "inset")),
)

_MEDIA_QUERY = re.compile(r"@media\s*([^{]+)\{", re.IGNORECASE)
_CSS_VAR = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)\s*;")
_CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_CLASS_SELECTOR = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")
_SHOW_SCREEN = re.compile(r"""showScreen\s*\(\s*['"]([A-Za-z0-9_-]+)['"]""")
_HANDLER_NAME = re.compile(r"^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\(")
_HTTP_ENDPOINT = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[A-Za-z0-9_\-/{}.:]*)")
_BC_ID = re.compile(r"\bBC-\d+\b")
_MIN_WIDTH = re.compile(r"min-width\s*:\s*([^)\s]+)")
_MAX_WIDTH = re.compile(r"max-width\s*:\s*([^)\s]+)")


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip("-")


def _upper_slug(value: str) -> str:
    return _slug(value).upper()


def _short_hash(value: str) -> str:
    """Sufixo estável para desambiguar ids quando o slug colide."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:6].upper()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _unique_ordered(values: Iterable[str]) -> list[str]:
    return sorted({str(v) for v in values if v})


# ─── Árvore HTML mínima ──────────────────────────────────────────────────────

class _Node:
    """Nó de uma árvore HTML tolerante. Sem DOM real e sem dependência externa."""

    __slots__ = ("tag", "attrs", "children", "parent", "texts", "line")

    def __init__(self, tag: str, attrs: dict[str, str], parent: "_Node | None",
                 line: int) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[_Node] = []
        self.parent = parent
        self.texts: list[str] = []
        self.line = line

    # -- consultas ---------------------------------------------------------
    def attr(self, name: str) -> str:
        return str(self.attrs.get(name) or "")

    def classes(self) -> list[str]:
        return [c for c in self.attr("class").split() if c]

    def text(self) -> str:
        parts = list(self.texts)
        for child in self.children:
            parts.append(child.text())
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def walk(self) -> "Iterable[_Node]":
        yield self
        for child in self.children:
            yield from child.walk()

    def find_all(self, *tags: str) -> "list[_Node]":
        wanted = set(tags)
        return [node for node in self.walk() if node is not self and node.tag in wanted]


class _TreeBuilder(HTMLParser):
    """Constrói a árvore. `convert_charrefs` ligado: o texto já vem decodificado."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", {}, None, 0)
        self._stack: list[_Node] = [self.root]
        self.styles: list[str] = []
        self.inline_scripts: list[str] = []
        self._in_style = False
        self._in_script = False

    # HTMLParser API ------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {k.lower(): (v if v is not None else "") for k, v in attrs}
        node = _Node(tag, mapping, self._stack[-1], self.getpos()[0])
        self._stack[-1].children.append(node)
        if tag == "style":
            self._in_style = True
        elif tag == "script":
            self._in_script = True
        if tag not in _VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {k.lower(): (v if v is not None else "") for k, v in attrs}
        node = _Node(tag, mapping, self._stack[-1], self.getpos()[0])
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False
        elif tag == "script":
            self._in_script = False
        # Fecha até o `tag` correspondente; tolera markup mal aninhado sem
        # descartar a árvore inteira (protótipo é HTML gerado, não validado).
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.styles.append(data)
            return
        if self._in_script:
            self.inline_scripts.append(data)
            return
        if data.strip():
            self._stack[-1].texts.append(data.strip())


# ─── Segurança de caminho ────────────────────────────────────────────────────

def _is_external(reference: str) -> bool:
    ref = reference.strip().lower()
    return (
        ref.startswith(("http://", "https://", "//", "data:", "mailto:", "tel:"))
        or bool(re.match(r"^[a-z][a-z0-9+.-]*:", ref)) and not ref.startswith("file:")
    )


def _safe_local_path(reference: str, base_dir: Path, workspace: Path,
                     warnings: list[dict[str, Any]]) -> Path | None:
    """Resolve uma referência local, recusando qualquer escape do workspace.

    Um protótipo é HTML gerado por agente; tratar suas referências como
    confiáveis é convidar `../../../etc/passwd` para dentro do manifesto.
    """
    ref = reference.split("#", 1)[0].split("?", 1)[0].strip()
    if not ref or ref.startswith("#"):
        return None
    candidate = Path(ref)
    if candidate.is_absolute() or ref.startswith("\\\\") or ref.startswith("/"):
        _warn(warnings, "PM-010", "warning",
              "referência de asset com caminho absoluto foi ignorada",
              evidence=reference,
              action="use caminho relativo ao index.html no protótipo")
        return None
    try:
        resolved = (base_dir / candidate).resolve()
        resolved.relative_to(workspace.resolve())
    except (OSError, ValueError):
        _warn(warnings, "PM-011", "warning",
              "referência de asset aponta para fora do workspace e foi ignorada",
              evidence=reference,
              action="mova o asset para dentro de outputs/tobe/prototype/")
        return None
    return resolved


def _warn(bucket: list[dict[str, Any]], code: str, severity: str, message: str,
          *, evidence: str = "", action: str = "",
          affected: Iterable[str] | None = None) -> None:
    entry = {
        "code": code,
        "severity": severity,
        "message": message,
        "evidence": evidence[:400],
        "affected_items": sorted(set(affected or [])),
        "recommended_action": action or "revise o protótipo da F3 e regere a F3S",
    }
    if entry not in bucket:
        bucket.append(entry)


# ─── project-config ──────────────────────────────────────────────────────────

def load_target_stack(project_dir: Path,
                      warnings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Stack alvo a partir de `context/project-config.yaml` — única autoridade.

    A ausência do arquivo é ERRO de fonte obrigatória (§16 do briefing): sem ele
    não há como saber em que tecnologia planejar, e adivinhar é exatamente o que
    produz o plano Angular num projeto React.
    """
    path = project_dir / PROJECT_CONFIG_REL
    if not path.is_file():
        raise PrototypeManifestError(
            f"fonte obrigatória ausente: {PROJECT_CONFIG_REL} — sem ela a stack "
            f"frontend/backend não é identificável e o planejamento seria inventado"
        )
    if yaml is None:
        raise PrototypeManifestError("pyyaml não está instalado")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — YAML inválido é erro técnico
        raise PrototypeManifestError(f"{PROJECT_CONFIG_REL} ilegível: {exc}") from exc
    stack = data.get("tobe_stack") if isinstance(data.get("tobe_stack"), dict) else {}
    resolved = {
        "frontend_framework": _str_or_none(stack.get("frontend_framework")),
        "frontend_language": _str_or_none(stack.get("frontend_language")),
        "frontend_version": _str_or_none(stack.get("frontend_version")),
        "backend_framework": _str_or_none(stack.get("backend_framework")),
        "backend_language": _str_or_none(stack.get("backend_language")),
        "backend_version": _str_or_none(stack.get("backend_version")),
        "package_manager": _str_or_none(stack.get("package_manager")),
    }
    if warnings is not None and not resolved["frontend_framework"]:
        _warn(warnings, "PM-012", "error",
              "tobe_stack.frontend_framework ausente em project-config.yaml",
              evidence=PROJECT_CONFIG_REL,
              action="declare tobe_stack.frontend_framework antes de rodar a F3S")
    return resolved


def _str_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


# ─── screen-list.md ──────────────────────────────────────────────────────────

def _parse_screen_list(path: Path) -> list[dict[str, Any]]:
    """Linhas do inventário de telas da F3, na ordem do arquivo."""
    rows: list[dict[str, Any]] = []
    for line in _read_text(path).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or re.match(r"^\|[\s:\-|]+\|?$", stripped):
            continue
        cells = [c.strip().strip("`") for c in stripped.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"screen", "tela"}:
            continue
        bc_cell = cells[1]
        bc_match = _BC_ID.search(bc_cell)
        endpoints = []
        if len(cells) > 2:
            for method, route in _HTTP_ENDPOINT.findall(cells[2].replace("\\|", "|")):
                endpoints.append({
                    "method": method.upper(),
                    "path": route,
                    "operation_id": None,
                    "source_anchor": cells[0],
                })
        rows.append({
            "name": cells[0],
            "bounded_context": bc_match.group(0) if bc_match else None,
            "bounded_context_name": _BC_ID.sub("", bc_cell).strip() or None,
            "endpoints": endpoints,
            "status": cells[-1].lower() if len(cells) > 3 else "included",
            "as_is_reference": cells[3] if len(cells) > 4 else "",
        })
    return rows


# ─── CSS ─────────────────────────────────────────────────────────────────────

def _categorize_token(name: str) -> str:
    lowered = name.lower().lstrip("-")
    for category, needles in _TOKEN_CATEGORY:
        if any(needle in lowered for needle in needles):
            return category
    return "other_tokens"


def _parse_css(css_sources: list[tuple[str, str]],
               warnings: list[dict[str, Any]]) -> dict[str, Any]:
    """Tokens, breakpoints, estilos globais e padrões de componente.

    `css_sources` é uma lista de `(anchor, conteúdo)` já ordenada — o anchor é a
    âncora de rastreabilidade que vai parar em `source_refs`.
    """
    tokens: dict[str, dict[str, Any]] = {}
    breakpoints: dict[str, dict[str, Any]] = {}
    global_styles: dict[str, dict[str, Any]] = {}
    class_usage: dict[str, int] = {}

    for anchor, css in css_sources:
        for name, value in _CSS_VAR.findall(css):
            token_id = f"TOK-{_upper_slug(name.lstrip('-'))}"
            if token_id in tokens:
                continue
            tokens[token_id] = {
                "token_id": token_id,
                "name": name,
                "value": re.sub(r"\s+", " ", value).strip(),
                "category": _categorize_token(name),
                "source_anchor": anchor,
                "origin": "css-custom-property",
            }
        for raw_query in _MEDIA_QUERY.findall(css):
            query = re.sub(r"\s+", " ", raw_query).strip()
            bp_id = f"BPT-{_upper_slug(query) or _short_hash(query)}"
            if len(bp_id) > 48:
                bp_id = f"BPT-{_short_hash(query)}"
            breakpoints.setdefault(bp_id, {
                "breakpoint_id": bp_id,
                "query": query,
                "min_width": (_MIN_WIDTH.search(query).group(1)
                              if _MIN_WIDTH.search(query) else None),
                "max_width": (_MAX_WIDTH.search(query).group(1)
                              if _MAX_WIDTH.search(query) else None),
                "source_anchor": anchor,
            })
        for raw_selector, body in _CSS_RULE.findall(css):
            selector = re.sub(r"\s+", " ", raw_selector).strip()
            if not selector or selector.startswith("@"):
                continue
            declarations = len([d for d in body.split(";") if d.strip()])
            for part in selector.split(","):
                single = part.strip()
                if not single:
                    continue
                if _CLASS_SELECTOR.search(single):
                    for klass in _CLASS_SELECTOR.findall(single):
                        class_usage[klass] = class_usage.get(klass, 0) + 1
                elif re.fullmatch(r"[*a-zA-Z][a-zA-Z0-9\-]*(::?[a-z-]+)?|:root|html|body",
                                  single):
                    entry = global_styles.setdefault(single, {
                        "selector": single, "declarations": 0,
                        "source_anchor": anchor,
                    })
                    entry["declarations"] += declarations

    # Atribuição token → classe. Sem isto, cada tela recebia a lista GLOBAL de
    # tokens e `design_tokens` deixava de discriminar: o gate de cobertura do
    # Design System não conseguia dizer QUE token uma feature precisa, e a fatia
    # de contexto por wave voltava a ser "o protótipo inteiro".
    tokens_by_class: dict[str, set[str]] = {}
    global_tokens: set[str] = set()
    name_to_id = {token["name"]: token_id for token_id, token in tokens.items()}
    for _anchor, css in css_sources:
        for raw_selector, body in _CSS_RULE.findall(css):
            referenced = {
                name_to_id[name] for name in re.findall(r"var\(\s*(--[A-Za-z0-9_-]+)", body)
                if name in name_to_id
            }
            if not referenced:
                continue
            selector = re.sub(r"\s+", " ", raw_selector).strip()
            classes = set(_CLASS_SELECTOR.findall(selector))
            if classes:
                for klass in classes:
                    tokens_by_class.setdefault(klass, set()).update(referenced)
            else:
                # `:root`, `body`, `*`, seletores de elemento: herdados por toda
                # tela, então pertencem ao Design System global.
                global_tokens.update(referenced)

    patterns: dict[str, dict[str, Any]] = {}
    for klass in sorted(class_usage):
        base = klass.split("-")[0]
        if len(base) < 2:
            continue
        pattern_id = f"PAT-{_upper_slug(base)}"
        entry = patterns.setdefault(pattern_id, {
            "pattern_id": pattern_id,
            "base_class": base,
            "variants": [],
            "usage_count": 0,
            "used_by_screens": [],
            "source_anchor": f".{base}",
        })
        if klass != base and klass not in entry["variants"]:
            entry["variants"].append(klass)
        entry["usage_count"] += class_usage[klass]

    if not tokens:
        _warn(warnings, "PM-020", "warning",
              "nenhuma custom property CSS encontrada no protótipo",
              evidence="; ".join(anchor for anchor, _ in css_sources) or "(sem CSS)",
              action="declare os tokens como :root{--token: valor} no protótipo, "
                     "ou aceite que o Design System venha só de design-tokens.json")
    return {
        "tokens": tokens,
        "breakpoints": breakpoints,
        "global_styles": global_styles,
        "component_patterns": patterns,
        "tokens_by_class": {k: sorted(v) for k, v in sorted(tokens_by_class.items())},
        "global_tokens": sorted(global_tokens),
    }


def _merge_design_tokens_json(path: Path, tokens: dict[str, dict[str, Any]],
                              anchor: str) -> None:
    """Funde `design-tokens.json` (artefato oficial da F3) sem sobrescrever CSS.

    O CSS vence porque é o que o browser realmente aplicou no protótipo — o JSON
    é a declaração de intenção. Divergência não é reconciliada em silêncio: o
    token do JSON entra só quando não existe equivalente no CSS.
    """
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    for group, values in sorted(data.items()):
        if not isinstance(values, dict):
            continue
        for name, value in sorted(values.items()):
            if not isinstance(value, (str, int, float)):
                continue
            token_id = f"TOK-{_upper_slug(group + '-' + name)}"
            css_equivalent = f"TOK-{_upper_slug(group + '-' + name)}"
            if token_id in tokens or css_equivalent in tokens:
                continue
            tokens[token_id] = {
                "token_id": token_id,
                "name": f"{group}.{name}",
                "value": str(value),
                "category": _categorize_token(f"{group}-{name}"),
                "source_anchor": anchor,
                "origin": "design-tokens-json",
            }


# ─── Componentes, formulários, tabelas, ações ────────────────────────────────

def _component_kind(node: _Node) -> str:
    classes = [c.lower() for c in node.classes()]
    for needle, kind in _KIND_BY_CLASS:
        if any(needle in klass for klass in classes):
            return kind
    return _KIND_BY_TAG.get(node.tag, "other")


def _component_name(node: _Node, kind: str) -> str:
    for attribute in ("aria-label", "id", "name", "title"):
        value = node.attr(attribute)
        if value:
            return value
    if node.tag in _TEXT_NAMED_TAGS:
        text = node.text()
        if 0 < len(text) <= 40:
            return text
    classes = node.classes()
    if classes:
        return classes[0]
    return f"{node.tag}-{kind}"


def _selector_for(node: _Node) -> str:
    if node.attr("id"):
        return f"#{node.attr('id')}"
    classes = node.classes()
    if classes:
        return node.tag + "".join(f".{c}" for c in classes[:3])
    return node.tag


def _accessibility_hints(node: _Node) -> list[str]:
    hints: list[str] = []
    for key, value in sorted(node.attrs.items()):
        if key.startswith("aria-") or key in {"role", "alt", "title", "for", "lang"}:
            hints.append(f"{key}={value}" if value else key)
    if node.tag in {"input", "select", "textarea"} and not node.attr("aria-label"):
        if node.attr("id"):
            hints.append(f"label-for={node.attr('id')}")
    return hints


def _make_component(node: _Node, screen_id: str,
                    seen: dict[str, dict[str, Any]]) -> dict[str, Any]:
    kind = _component_kind(node)
    name = _component_name(node, kind)
    base = f"{kind}-{name}"
    component_id = f"CMP-{_upper_slug(base)}" if _slug(base) else \
        f"CMP-{_upper_slug(kind)}-{_short_hash(_selector_for(node))}"
    if len(component_id) > 64:
        component_id = f"CMP-{_upper_slug(kind)}-{_short_hash(base)}"
    existing = seen.get(component_id)
    if existing is not None:
        if screen_id and screen_id not in existing["used_by_screens"]:
            existing["used_by_screens"].append(screen_id)
            existing["used_by_screens"].sort()
        return existing
    component = {
        "component_id": component_id,
        "kind": kind,
        "name": name,
        "required": kind in _STRUCTURAL_KINDS,
        "selector": _selector_for(node),
        "classes": sorted(set(node.classes())),
        "shared": False,
        "used_by_screens": [screen_id] if screen_id else [],
        "design_tokens": [],
        "accessibility_hints": _accessibility_hints(node),
        "source_anchor": _selector_for(node),
    }
    seen[component_id] = component
    return component


def _field_validations(node: _Node) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    message = node.attr("data-error-msg") or node.attr("data-error") or None
    for attribute in ("required", "pattern", "min", "max", "minlength",
                      "maxlength", "step", "readonly", "disabled"):
        if attribute in node.attrs:
            raw = node.attr(attribute)
            value: Any = True if raw == "" else raw
            rules.append({"rule": attribute, "value": value, "message": message})
    if node.attr("type") in {"email", "url", "number", "date", "tel"}:
        rules.append({"rule": "format", "value": node.attr("type"), "message": message})
    return rules


def _extract_form(node: _Node, screen_slug: str) -> dict[str, Any]:
    html_id = node.attr("id") or node.attr("name")
    base = html_id or f"{screen_slug}-form"
    form_id = f"FRM-{_upper_slug(base)}"
    labels = {
        label.attr("for"): label.text()
        for label in node.find_all("label") if label.attr("for")
    }
    fields: list[dict[str, Any]] = []
    for control in node.find_all("input", "select", "textarea"):
        name = control.attr("name") or control.attr("id")
        if not name:
            continue
        input_type = (control.attr("type") or
                      ("select" if control.tag == "select" else
                       "textarea" if control.tag == "textarea" else "text"))
        options = [option.text() for option in control.find_all("option")
                   if option.text()] if control.tag == "select" else []
        fields.append({
            "field_id": f"FLD-{_upper_slug(base + '-' + name)}",
            "name": name,
            "label": labels.get(control.attr("id")) or control.attr("aria-label") or None,
            "input_type": input_type,
            "required": "required" in control.attrs,
            "validations": _field_validations(control),
            "options": options,
            "source_anchor": f"#{control.attr('id')}" if control.attr("id") else name,
        })
    handler = node.attr("onsubmit")
    submit = _HANDLER_NAME.match(handler).group(1) if _HANDLER_NAME.match(handler) else None
    return {
        "form_id": form_id,
        "component_id": f"CMP-{_upper_slug('form-' + (html_id or base))}",
        "name": node.attr("aria-label") or html_id or base,
        "html_id": html_id,
        "submit_action": submit,
        "fields": sorted(fields, key=lambda item: item["field_id"]),
        "source_anchor": f"#{html_id}" if html_id else f"form[{screen_slug}]",
    }


def _extract_table(node: _Node, screen_slug: str, index: int) -> dict[str, Any]:
    html_id = node.attr("id")
    label = node.attr("aria-label")
    base = html_id or _slug(label) or f"{screen_slug}-table-{index + 1}"
    columns = [header.text() for header in node.find_all("th") if header.text()]
    row_actions = _unique_ordered(
        button.text() or button.attr("aria-label") or button.attr("title")
        for button in node.find_all("button", "a")
    )
    return {
        "table_id": f"TBL-{_upper_slug(base)}",
        "component_id": f"CMP-{_upper_slug('table-' + base)}",
        "name": label or html_id or base,
        "html_id": html_id,
        "columns": columns,
        "row_actions": row_actions,
        "source_anchor": f"#{html_id}" if html_id else f"table[{screen_slug}][{index}]",
    }


def _extract_action(node: _Node, screen_slug: str,
                    screen_id_by_html: dict[str, str]) -> dict[str, Any] | None:
    label = node.text() or node.attr("aria-label") or node.attr("title") or node.attr("id")
    onclick = node.attr("onclick")
    href = node.attr("href")
    kind = "unknown"
    handler: str | None = None
    target_screen: str | None = None

    if node.tag == "button" and node.attr("type") == "submit":
        kind = "submit"
    elif node.tag == "button" and node.attr("type") == "reset":
        kind = "reset"

    nav = _SHOW_SCREEN.search(onclick) or _SHOW_SCREEN.search(href)
    if nav:
        kind = "navigate"
        target_screen = screen_id_by_html.get(f"screen-{nav.group(1)}") \
            or screen_id_by_html.get(nav.group(1))
    elif href.startswith("#") and len(href) > 1:
        kind = "navigate"
        target_screen = screen_id_by_html.get(href[1:])
    if onclick:
        match = _HANDLER_NAME.match(onclick)
        if match:
            handler = match.group(1)
            if kind == "unknown":
                lowered = handler.lower()
                if "close" in lowered or "hide" in lowered:
                    kind = "close-modal"
                elif "open" in lowered or "show" in lowered or "confirm" in lowered:
                    kind = "open-modal"
                else:
                    kind = "invoke"
        elif "style.display='none'" in onclick.replace(" ", ""):
            kind = "close-modal"
        elif kind == "unknown":
            kind = "invoke"
    if kind == "unknown" and not label:
        return None
    base = label or handler or node.attr("id") or screen_slug
    action_id = f"ACT-{_upper_slug(screen_slug + '-' + base)}"
    if len(action_id) > 72:
        action_id = f"ACT-{_upper_slug(screen_slug)}-{_short_hash(base)}"
    return {
        "action_id": action_id,
        "label": label or base,
        "kind": kind,
        "handler": handler,
        "target_screen_id": target_screen,
        "source_anchor": _selector_for(node),
    }


def _inside_table_row(node: _Node, boundary: _Node) -> bool:
    """True quando o nó está dentro de um `<tr>`/`<tbody>` da tela."""
    current = node.parent
    while current is not None and current is not boundary:
        if current.tag in {"tr", "tbody", "td"}:
            return True
        current = current.parent
    return False


def _screen_states(node: _Node) -> list[dict[str, Any]]:
    states: dict[tuple[str, str], dict[str, Any]] = {}
    for element in node.walk():
        haystack = " ".join([*element.classes(), element.attr("id")]).lower()
        for needle, state in _STATE_WORDS.items():
            if needle in haystack:
                selector = _selector_for(element)
                states.setdefault((state, selector), {
                    "state": state, "selector": selector,
                    "source_anchor": selector,
                })
    return sorted(states.values(), key=lambda item: (item["state"], item["selector"]))


def _responsive_hints(node: _Node, breakpoints: dict[str, dict[str, Any]]) -> list[str]:
    hints: list[str] = []
    classes = {c.lower() for element in node.walk() for c in element.classes()}
    for klass in sorted(classes):
        if re.search(r"\b(sm|md|lg|xl|mobile|tablet|desktop|responsive|col-|grid|flex)\b",
                     klass):
            hints.append(f"class:{klass}")
    hints.extend(f"breakpoint:{bp['breakpoint_id']}" for bp in
                 sorted(breakpoints.values(), key=lambda item: item["breakpoint_id"]))
    return hints[:64]


# ─── Construção do manifesto ─────────────────────────────────────────────────

def _collect_assets(tree: _TreeBuilder, prototype_dir: Path, workspace: Path,
                    warnings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                             list[tuple[str, str]]]:
    """Assets referenciados + fontes CSS locais para o extrator de Design System."""
    assets: dict[str, dict[str, Any]] = {}
    css_sources: list[tuple[str, str]] = []
    for index, style in enumerate(tree.styles):
        css_sources.append((f"{PROTOTYPE_REL}#style[{index}]", style))

    references: list[tuple[str, str, str]] = []  # (ref, kind, referenced_by)
    for node in tree.root.walk():
        if node.tag == "link" and "stylesheet" in node.attr("rel").lower():
            references.append((node.attr("href"), "stylesheet", _selector_for(node)))
        elif node.tag == "script" and node.attr("src"):
            references.append((node.attr("src"), "script", _selector_for(node)))
        elif node.tag == "img" and node.attr("src"):
            references.append((node.attr("src"), "image", _selector_for(node)))
        elif node.tag in {"video", "audio", "source"} and node.attr("src"):
            references.append((node.attr("src"), "media", _selector_for(node)))

    for reference, kind, referenced_by in references:
        if not reference.strip():
            continue
        if _is_external(reference):
            entry = assets.setdefault(reference, {
                "path": reference, "kind": kind, "scope": "external",
                "checksum": None, "referenced_by": [],
            })
            if referenced_by not in entry["referenced_by"]:
                entry["referenced_by"].append(referenced_by)
            _warn(warnings, "PM-030", "info",
                  "asset externo registrado como dependência, não baixado",
                  evidence=reference, affected=[reference],
                  action="confirme a política de CDN/offline do projeto antes da F4")
            continue
        resolved = _safe_local_path(reference, prototype_dir, workspace, warnings)
        if resolved is None:
            continue
        try:
            relative = resolved.relative_to(workspace).as_posix()
        except ValueError:
            continue
        if not resolved.is_file():
            _warn(warnings, "PM-031", "warning",
                  "asset local referenciado pelo protótipo não existe em disco",
                  evidence=reference, affected=[relative],
                  action="regere o protótipo da F3 ou remova a referência quebrada")
            continue
        payload = resolved.read_bytes()
        entry = assets.setdefault(relative, {
            "path": relative, "kind": kind, "scope": "local",
            "checksum": _sha256_bytes(payload), "referenced_by": [],
        })
        if referenced_by not in entry["referenced_by"]:
            entry["referenced_by"].append(referenced_by)
        if kind == "stylesheet":
            css_sources.append((relative, payload.decode("utf-8", errors="replace")))

    for entry in assets.values():
        entry["referenced_by"].sort()
    return sorted(assets.values(), key=lambda item: item["path"]), css_sources


def _screen_nodes(tree: _TreeBuilder) -> list[_Node]:
    """Telas do protótipo, em ordem de aparição no documento.

    Reconhecimento em cascata, do mais explícito ao mais frouxo. Nada aqui
    adivinha: se nenhuma das formas aparece, `build_manifest` emite PM-001 e o
    manifesto sai com `screens: []` — visível, em vez de silenciosamente vazio.
    """
    explicit = [node for node in tree.root.walk()
                if node.attr("id").startswith("screen-")
                and node.tag in {"section", "div", "main", "article", "template"}]
    if explicit:
        return explicit
    by_class = [node for node in tree.root.walk()
                if "screen" in [c.lower() for c in node.classes()]]
    if by_class:
        return by_class
    return [node for node in tree.root.walk() if node.attr("data-screen")]


def build_manifest(project: str, repo_root: Path | None = None, *,
                   strict: bool = True) -> dict[str, Any]:
    """Manifesto completo, sem escrever em disco.

    `strict=True` levanta `PrototypeManifestError` quando o protótipo não existe.
    `strict=False` devolve um manifesto vazio com warning `PM-001` de severidade
    `error` — modo do caminho de remediação, em que a F3S precisa registrar a
    ausência sem impedir que as demais tools da wave rodem.
    """
    root = repo_root or REPO_ROOT
    project_dir = root / "projects" / project
    if not project_dir.is_dir():
        raise PrototypeManifestError(f"project não encontrado: projects/{project}")

    warnings: list[dict[str, Any]] = []
    target_stack = load_target_stack(project_dir, warnings)

    prototype_path = project_dir / PROTOTYPE_REL
    screen_list_path = project_dir / SCREEN_LIST_REL
    design_tokens_path = project_dir / DESIGN_TOKENS_REL

    if not prototype_path.is_file():
        message = (
            f"fonte obrigatória ausente: {PROTOTYPE_REL} — a F3S não pode planejar "
            f"frontend sem o protótipo navegável produzido pela F3"
        )
        if strict:
            raise PrototypeManifestError(message)
        _warn(warnings, "PM-001", "error", message, evidence=PROTOTYPE_REL,
              action="execute a F3 (ava-prototype) antes da F3S")
        return _empty_manifest(project, target_stack, warnings)

    raw = prototype_path.read_bytes()
    tree = _TreeBuilder()
    try:
        tree.feed(raw.decode("utf-8", errors="replace"))
        tree.close()
    except Exception as exc:  # noqa: BLE001 — HTML ilegível é erro técnico
        raise PrototypeManifestError(f"{PROTOTYPE_REL} não pôde ser parseado: {exc}") from exc

    assets, css_sources = _collect_assets(tree, prototype_path.parent, root, warnings)
    css = _parse_css(css_sources, warnings)
    _merge_design_tokens_json(design_tokens_path, css["tokens"], DESIGN_TOKENS_REL)

    screen_rows = _parse_screen_list(screen_list_path)
    if not screen_rows and screen_list_path.is_file():
        _warn(warnings, "PM-002", "warning",
              "screen-list.md existe mas nenhuma linha de inventário foi reconhecida",
              evidence=SCREEN_LIST_REL,
              action="mantenha a tabela | Screen | Bounded Context | API Endpoint | ... |")
    elif not screen_list_path.is_file():
        _warn(warnings, "PM-003", "error",
              "screen-list.md ausente — telas ficam sem bounded context e sem endpoint",
              evidence=SCREEN_LIST_REL,
              action="execute a F3 (ava-prototype) para produzir o inventário de telas")

    nodes = _screen_nodes(tree)
    if not nodes:
        _warn(warnings, "PM-004", "error",
              "nenhuma tela reconhecida no protótipo",
              evidence=PROTOTYPE_REL,
              action="marque cada tela como <section id=\"screen-...\"> ou class=\"screen\"")

    # Índice html-id → screen_id, necessário para resolver alvos de navegação
    # antes de montar as ações. Dois passos, porque a ação da tela 1 pode
    # apontar para a tela 9.
    screen_id_by_html: dict[str, str] = {}
    for node in nodes:
        html_id = node.attr("id") or node.attr("data-screen")
        base = re.sub(r"^screen-", "", html_id) if html_id else _slug(node.attr("aria-label"))
        if not base:
            continue
        screen_id_by_html[html_id or base] = f"SCR-{_upper_slug(base)}"

    # ── Passo 1: identidade das telas ────────────────────────────────────────
    # Separado do passo 2 porque a atribuição de linha do inventário é global:
    # decidir tela-a-tela permitia que duas telas reivindicassem a mesma linha.
    candidates: list[dict[str, Any]] = []
    for node in nodes:
        html_id = node.attr("id") or node.attr("data-screen")
        base = re.sub(r"^screen-", "", html_id) if html_id else _slug(node.attr("aria-label"))
        if not base:
            _warn(warnings, "PM-005", "warning",
                  "elemento de tela sem id estável foi ignorado",
                  evidence=_selector_for(node),
                  action="dê um id 'screen-<nome>' à seção no protótipo")
            continue
        candidates.append({
            "node": node,
            "html_id": html_id,
            "base": base,
            "screen_id": f"SCR-{_upper_slug(base)}",
            "name": (node.attr("aria-label") or node.attr("data-screen-name")
                     or _first_heading(node) or base),
        })

    rows_by_slug = {_slug(row["name"]): row for row in screen_rows}
    fuzzy = _assign_screen_rows(
        [{"screen_id": c["screen_id"], "name": c["name"], "base": c["base"]}
         for c in candidates], screen_rows)

    shared_seen: dict[str, dict[str, Any]] = {}
    screens: list[dict[str, Any]] = []
    routes: dict[str, dict[str, Any]] = {}
    matched_rows: set[str] = set()
    assets_by_path = {asset["path"]: asset for asset in assets}

    # ── Passo 2: conteúdo de cada tela ───────────────────────────────────────
    for candidate in candidates:
        node = candidate["node"]
        html_id = candidate["html_id"]
        base = candidate["base"]
        screen_id = candidate["screen_id"]
        name = candidate["name"]
        row = (rows_by_slug.get(_slug(name)) or rows_by_slug.get(_slug(base))
               or fuzzy.get(screen_id))
        if row is not None:
            matched_rows.add(_slug(row["name"]))
        else:
            _warn(warnings, "PM-006", "warning",
                  f"tela {screen_id} não tem linha correspondente no screen-list.md",
                  evidence=f"{PROTOTYPE_REL}#{html_id}", affected=[screen_id],
                  action="alinhe o nome da tela entre index.html e screen-list.md; "
                         "sem isso a tela fica sem bounded context e sem endpoint")

        components_local: dict[str, dict[str, Any]] = {}
        for element in node.walk():
            if element is node:
                continue
            if _inside_table_row(element, node):
                # Linhas de tabela do protótipo são DADOS DE EXEMPLO. Cada botão
                # "Editar" delas virava um componente próprio — medido aqui:
                # `CMP-BUTTON-EDITAR-ANA-PAULA-SOUZA`, um por funcionário fake.
                # A ação da linha já está em `table.row_actions`, que é a forma
                # correta: uma ação de linha, não N componentes.
                continue
            if element.tag in _KIND_BY_TAG or element.classes():
                kind = _component_kind(element)
                if kind == "other" and element.tag not in _KIND_BY_TAG:
                    continue
                component = _make_component(element, screen_id, shared_seen)
                components_local[component["component_id"]] = component

        forms = [_extract_form(form, base) for form in node.find_all("form")]
        tables = [_extract_table(table, base, index)
                  for index, table in enumerate(node.find_all("table"))]
        actions: list[dict[str, Any]] = []
        for element in node.find_all("button", "a"):
            action = _extract_action(element, base, screen_id_by_html)
            if action is not None:
                actions.append(action)
        actions = _dedupe_by_key(actions, "action_id")

        endpoints = list(row["endpoints"]) if row else []
        dynamic = bool(endpoints or forms or tables)
        static_justification = None
        if not dynamic:
            static_justification = (
                "nenhum endpoint no screen-list.md, nenhum formulário e nenhuma "
                "tabela de dados no protótipo — tela tratada como estática"
            )
            _warn(warnings, "PM-007", "info",
                  f"tela {screen_id} classificada como estática",
                  evidence=static_justification, affected=[screen_id],
                  action="se a tela consome API, declare o endpoint no screen-list.md")
        elif not endpoints:
            _warn(warnings, "PM-008", "warning",
                  f"tela {screen_id} tem formulário/tabela mas nenhum endpoint mapeado",
                  evidence=f"{SCREEN_LIST_REL}:{row['name'] if row else screen_id}",
                  affected=[screen_id],
                  action="declare o endpoint da tela no screen-list.md ou justifique "
                         "como estática; a F3S não inventa operationId")

        route_path = _route_for(node, base)
        route_id = f"RTE-{_upper_slug(base)}"
        routes.setdefault(route_id, {
            "route_id": route_id,
            "path": route_path,
            "screen_id": screen_id,
            "default": "active" in [c.lower() for c in node.classes()],
            "source_anchor": f"{PROTOTYPE_REL}#{html_id}",
        })

        screens.append({
            "screen_id": screen_id,
            "name": name,
            "route": route_path,
            "route_id": route_id,
            "bounded_context": row["bounded_context"] if row else None,
            "bounded_context_name": row["bounded_context_name"] if row else None,
            "source_anchor": f"{PROTOTYPE_REL}#{html_id}",
            "html_id": html_id,
            "layout": _layout_of(node),
            "dynamic": dynamic,
            "static_justification": static_justification,
            "components": sorted(components_local.values(),
                                 key=lambda item: item["component_id"]),
            "forms": sorted(forms, key=lambda item: item["form_id"]),
            "tables": sorted(tables, key=lambda item: item["table_id"]),
            "actions": sorted(actions, key=lambda item: item["action_id"]),
            "navigation_targets": _unique_ordered(
                action["target_screen_id"] for action in actions
                if action.get("target_screen_id")),
            "states": _screen_states(node),
            "assets": _screen_assets(node, prototype_path.parent, root, assets_by_path),
            "design_tokens": _screen_tokens(node, css),
            "api_endpoints": endpoints,
            "accessibility_hints": _accessibility_hints(node),
            "responsive_hints": _responsive_hints(node, css["breakpoints"]),
        })

    for row in screen_rows:
        if row["status"].startswith("exclu") or row["status"].startswith("out"):
            continue
        if _slug(row["name"]) not in matched_rows:
            _warn(warnings, "PM-009", "warning",
                  f"tela '{row['name']}' está no screen-list.md mas não no index.html",
                  evidence=f"{SCREEN_LIST_REL}:{row['name']}",
                  affected=[row["name"]],
                  action="regere o protótipo incluindo a tela, ou marque-a como excluída")

    # Compartilhado = usado por mais de uma tela. Ownership de create fica com a
    # foundation; ver `speckit_wave_manifest._shared_component_owner`.
    for component in shared_seen.values():
        component["shared"] = len(component["used_by_screens"]) > 1
    shared_components = sorted(
        (component for component in shared_seen.values() if component["shared"]),
        key=lambda item: item["component_id"])

    flows = _build_flows(screens)
    design_system = _group_tokens(css)
    design_system["icons"] = _collect_icons(tree)

    entry_checksum = _sha256_bytes(raw)
    content_checksum = _sha256_bytes(
        raw + b"".join(
            (asset["checksum"] or "").encode("utf-8")
            for asset in assets if asset["scope"] == "local"))

    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "trace_id": "",
        "generated_at": _now_iso(),
        "target_stack": target_stack,
        "prototype": {
            "entrypoint": PROTOTYPE_REL,
            "checksum": entry_checksum,
            "content_checksum": content_checksum,
            "screen_list": SCREEN_LIST_REL if screen_list_path.is_file() else None,
            "design_tokens_file": (DESIGN_TOKENS_REL if design_tokens_path.is_file()
                                   else None),
            "assets": assets,
        },
        "design_system": design_system,
        "shared_components": shared_components,
        "routes": sorted(routes.values(), key=lambda item: item["route_id"]),
        "screens": sorted(screens, key=lambda item: item["screen_id"]),
        "flows": flows,
        "warnings": sorted(warnings, key=lambda item: (item["code"], item["message"])),
    }


def _empty_manifest(project: str, target_stack: dict[str, Any],
                    warnings: list[dict[str, Any]]) -> dict[str, Any]:
    """Manifesto válido e vazio. Não é placeholder: o motivo está em warnings."""
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "trace_id": "",
        "generated_at": _now_iso(),
        "target_stack": target_stack,
        "prototype": {
            "entrypoint": PROTOTYPE_REL,
            "checksum": _sha256_bytes(b""),
            "content_checksum": _sha256_bytes(b""),
            "screen_list": None,
            "design_tokens_file": None,
            "assets": [],
        },
        "design_system": {
            "colors": [], "typography": [], "spacing": [], "other_tokens": [],
            "breakpoints": [], "icons": [], "global_styles": [],
            "component_patterns": [],
        },
        "shared_components": [],
        "routes": [],
        "screens": [],
        "flows": [],
        "warnings": sorted(warnings, key=lambda item: (item["code"], item["message"])),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _first_heading(node: _Node) -> str:
    for heading in node.find_all("h1", "h2", "h3"):
        text = heading.text()
        if text:
            return text
    return ""


def _layout_of(node: _Node) -> str | None:
    classes = [c for c in node.classes() if c.lower() != "screen"]
    if classes:
        return " ".join(sorted(classes))
    for child in node.children:
        child_classes = [c for c in child.classes()
                         if re.search(r"layout|container|wrapper|grid|flex", c, re.I)]
        if child_classes:
            return " ".join(sorted(child_classes))
    return None


def _route_for(node: _Node, base: str) -> str:
    declared = node.attr("data-route")
    if declared:
        return declared if declared.startswith("/") else f"/{declared}"
    return f"/{_slug(base)}"


#: Palavras sem valor discriminante no nome de uma tela, nos dois idiomas em que
#: os protótipos da esteira são gerados.
_NAME_STOPWORDS = frozenset({
    "de", "da", "do", "das", "dos", "e", "a", "o", "as", "os", "em", "por",
    "para", "the", "of", "and", "to", "for", "screen", "tela", "page", "pagina",
})

#: Comprimento mínimo do prefixo comum para dois tokens serem "o mesmo termo".
#: 5 separa `cadastro`/`cadastrar` (prefixo `cadastr`, 7) de `funcao`/
#: `funcionario` (prefixo `func`, 4) — que é exatamente a confusão que
#: atribuiria a tela de funcionários ao bounded context de funções.
_TOKEN_PREFIX_MIN = 5

#: Score mínimo e margem sobre o segundo colocado. Sem a margem, `Lista de
#: Funções` casaria com `Listar Funcionários` (0.5, pelo `listar` em comum).
_MATCH_MIN_SCORE = 0.5
_MATCH_MIN_MARGIN = 0.15


def _name_tokens(value: str) -> list[str]:
    return [token for token in _slug(value).split("-")
            if token and token not in _NAME_STOPWORDS]


def _tokens_equivalent(left: str, right: str) -> bool:
    if left == right:
        return True
    common = 0
    for a, b in zip(left, right):
        if a != b:
            break
        common += 1
    return common >= _TOKEN_PREFIX_MIN


def _name_similarity(left: str, right: str) -> float:
    """Fração de termos em comum entre dois nomes de tela. Determinística."""
    left_tokens = _name_tokens(left)
    right_tokens = _name_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    remaining = list(right_tokens)
    matched = 0
    for token in left_tokens:
        for index, candidate in enumerate(remaining):
            if _tokens_equivalent(token, candidate):
                matched += 1
                del remaining[index]
                break
    return matched / max(len(left_tokens), len(right_tokens))


def _assign_screen_rows(candidates: list[dict[str, str]],
                        rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Casa cada tela do HTML com no máximo uma linha do `screen-list.md`.

    O casamento por prefixo puro que existia aqui rejeitava os pares reais do
    protótipo de `cadastro-funcionarios-04` — `Lista de Funcionários` (aria-label)
    contra `Listar Funcionários` (inventário), e `Cadastro de Funcionário` contra
    `Cadastrar / Editar Funcionário`. Resultado: 4 das 9 telas ficavam sem
    bounded context, e sem BC a tela não é atribuível a nenhuma migration wave —
    ou seja, as quatro telas de CRUD, o coração do sistema, saíam do
    planejamento por uma diferença de conjugação verbal.

    A correção continua conservadora e auditável: comparação por termos com
    prefixo comum mínimo, score mínimo, margem obrigatória sobre o segundo
    colocado e atribuição gulosa 1:1 em ordem determinística. Ambíguo continua
    virando PM-006 — o que não pode acontecer é casar errado em silêncio.
    """
    scored: list[tuple[float, str, str, dict[str, Any]]] = []
    for candidate in candidates:
        for row in rows:
            score = max(_name_similarity(candidate["name"], row["name"]),
                        _name_similarity(candidate["base"], row["name"]))
            if score >= _MATCH_MIN_SCORE:
                scored.append((score, candidate["screen_id"], row["name"], row))

    by_screen: dict[str, list[tuple[float, str, dict[str, Any]]]] = {}
    for score, screen_id, row_name, row in scored:
        by_screen.setdefault(screen_id, []).append((score, row_name, row))

    # Ordem determinística: melhor score primeiro; empates por screen_id e nome
    # da linha, nunca pela ordem de iteração de um dict.
    ranked = sorted(scored, key=lambda item: (-item[0], item[1], item[2]))
    assigned: dict[str, dict[str, Any]] = {}
    taken_rows: set[str] = set()
    for score, screen_id, row_name, row in ranked:
        if screen_id in assigned or row_name in taken_rows:
            continue
        # A margem é medida contra as linhas AINDA DISPONÍVEIS. Medi-la contra
        # todas fazia `Relatório por Função (Master-Detail)` ser recusado por
        # ambiguidade com `Relatório de Funções` — uma linha que, naquele ponto,
        # já pertencia a `SCR-REL-FUNCOES` com score 1.0. Ambiguidade com um
        # candidato indisponível não é ambiguidade.
        competitors = sorted((s for s, name, _ in by_screen[screen_id]
                              if name != row_name and name not in taken_rows),
                             reverse=True)
        if competitors and score - competitors[0] < _MATCH_MIN_MARGIN:
            continue  # ambíguo — PM-006 diz a verdade melhor que um palpite
        assigned[screen_id] = row
        taken_rows.add(row_name)
    return assigned


def _screen_tokens(node: _Node, css: dict[str, Any]) -> list[str]:
    """Tokens que ESTA tela realmente usa: globais + os das classes do subtree.

    A alternativa que existia — devolver o catálogo inteiro para toda tela —
    tornava `design_tokens` inútil como recorte: a fatia de contexto por wave
    voltava a ser "o Design System todo", que é justamente o que o §21 do
    briefing proíbe ("não enviar todo o index.html para todas as features").
    """
    by_class = css.get("tokens_by_class") or {}
    used = set(css.get("global_tokens") or [])
    for element in node.walk():
        for klass in element.classes():
            used.update(by_class.get(klass, ()))
    return sorted(used)


def _screen_assets(node: _Node, prototype_dir: Path, workspace: Path,
                   assets_by_path: dict[str, dict[str, Any]]) -> list[str]:
    """Assets referenciados DENTRO da tela. Stylesheet e script são do documento."""
    found: set[str] = set()
    for element in node.walk():
        reference = element.attr("src") or element.attr("poster")
        if not reference or _is_external(reference):
            continue
        try:
            resolved = (prototype_dir / Path(reference.split("#")[0].split("?")[0])).resolve()
            relative = resolved.relative_to(workspace.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        if relative in assets_by_path:
            found.add(relative)
    return sorted(found)


def _dedupe_by_key(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for item in items:
        seen.setdefault(item[key], item)
    return list(seen.values())


def _group_tokens(css: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "colors": [], "typography": [], "spacing": [], "other_tokens": [],
    }
    for token in sorted(css["tokens"].values(), key=lambda item: item["token_id"]):
        grouped[token["category"]].append(token)
    return {
        **grouped,
        "breakpoints": sorted(css["breakpoints"].values(),
                              key=lambda item: item["breakpoint_id"]),
        "icons": [],
        "global_styles": sorted(css["global_styles"].values(),
                                key=lambda item: item["selector"]),
        "component_patterns": sorted(css["component_patterns"].values(),
                                     key=lambda item: item["pattern_id"]),
    }


def _collect_icons(tree: _TreeBuilder) -> list[dict[str, Any]]:
    icons: dict[str, dict[str, Any]] = {}
    for node in tree.root.walk():
        name = ""
        kind = ""
        if node.tag == "svg":
            name = node.attr("aria-label") or node.attr("id") or "svg"
            kind = "inline-svg"
        elif node.tag in {"i", "span"} and any(
                re.match(r"^(icon|fa|mdi|material)", c, re.I) for c in node.classes()):
            name = next(c for c in node.classes()
                        if re.match(r"^(icon|fa|mdi|material)", c, re.I))
            kind = "icon-font"
        elif node.tag == "img" and re.search(r"icon", node.attr("src"), re.I):
            name = node.attr("alt") or Path(node.attr("src")).stem
            kind = "image"
        if not name:
            continue
        icon_id = f"ICO-{_upper_slug(name)}"
        icons.setdefault(icon_id, {
            "icon_id": icon_id, "name": name, "kind": kind,
            "source_anchor": _selector_for(node),
        })
    return sorted(icons.values(), key=lambda item: item["icon_id"])


def _build_flows(screens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fluxos de navegação de 2 telas — a aresta é o que o protótipo prova.

    Um fluxo mais longo exigiria inferir intenção; aqui só se registra o que
    está escrito: a tela A tem uma ação que leva à tela B. `critical=True` para
    fluxos que tocam uma tela dinâmica, que é o recorte de E2E-COVERAGE.
    """
    dynamic = {screen["screen_id"] for screen in screens if screen["dynamic"]}
    flows: dict[str, dict[str, Any]] = {}
    for screen in sorted(screens, key=lambda item: item["screen_id"]):
        for target in screen["navigation_targets"]:
            if target == screen["screen_id"]:
                continue
            flow_id = f"FLW-{_upper_slug(screen['screen_id'][4:] + '-TO-' + target[4:])}"
            if len(flow_id) > 72:
                flow_id = f"FLW-{_short_hash(screen['screen_id'] + target)}"
            flows.setdefault(flow_id, {
                "flow_id": flow_id,
                "name": f"{screen['name']} → {target}",
                "screens": [screen["screen_id"], target],
                "critical": screen["screen_id"] in dynamic or target in dynamic,
                "source_anchor": screen["source_anchor"],
            })
    return sorted(flows.values(), key=lambda item: item["flow_id"])


# ─── Validação de schema (sem dependência externa) ───────────────────────────

def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validação estrutural determinística contra o schema publicado.

    Não usa `jsonschema` porque o repo não o tem como dependência (ver
    `headroom/vendor/tests/test_codex_openai_contract_parity.py`, que evita
    exatamente essa adição). Confere o que o contrato exige de fato: chaves
    obrigatórias, formato dos ids e unicidade — que é o que quebra consumidor.
    """
    problems: list[str] = []
    for field in ("schema_version", "project", "generated_at", "prototype",
                  "design_system", "screens", "warnings"):
        if field not in manifest:
            problems.append(f"campo obrigatório ausente: {field}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        problems.append(
            f"schema_version={manifest.get('schema_version')!r}, esperado {SCHEMA_VERSION!r}")
    prototype = manifest.get("prototype") or {}
    checksum = str(prototype.get("checksum") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", checksum):
        problems.append(f"prototype.checksum inválido: {checksum!r}")

    patterns = {
        "screen_id": r"^SCR-[A-Z0-9-]+$",
        "component_id": r"^CMP-[A-Z0-9-]+$",
        "route_id": r"^RTE-[A-Z0-9-]+$",
        "token_id": r"^TOK-[A-Z0-9-]+$",
        "form_id": r"^FRM-[A-Z0-9-]+$",
        "table_id": r"^TBL-[A-Z0-9-]+$",
        "field_id": r"^FLD-[A-Z0-9-]+$",
        "action_id": r"^ACT-[A-Z0-9-]+$",
        "flow_id": r"^FLW-[A-Z0-9-]+$",
    }

    def _check_ids(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in patterns and isinstance(value, str):
                    if not re.fullmatch(patterns[key], value):
                        problems.append(f"{path}.{key} fora do padrão: {value!r}")
                _check_ids(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _check_ids(item, f"{path}[{index}]")

    _check_ids(manifest, "$")

    seen_screens: set[str] = set()
    for screen in manifest.get("screens") or []:
        screen_id = str(screen.get("screen_id") or "")
        if screen_id in seen_screens:
            problems.append(f"screen_id duplicado: {screen_id}")
        seen_screens.add(screen_id)
    for route in manifest.get("routes") or []:
        if route.get("screen_id") not in seen_screens:
            problems.append(
                f"route {route.get('route_id')} referencia screen_id inexistente: "
                f"{route.get('screen_id')}")
    for flow in manifest.get("flows") or []:
        for screen_id in flow.get("screens") or []:
            if screen_id not in seen_screens:
                problems.append(
                    f"flow {flow.get('flow_id')} referencia screen_id inexistente: {screen_id}")
    return problems


# ─── Persistência ────────────────────────────────────────────────────────────

def manifest_path(project: str, repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / "projects" / project / MANIFEST_REL


def write_manifest(project: str, repo_root: Path | None = None, *,
                   strict: bool = True) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    manifest = build_manifest(project, root, strict=strict)
    problems = validate_manifest(manifest)
    if problems:
        raise PrototypeManifestError(
            "manifesto do protótipo não conforma ao schema: " + "; ".join(problems[:5]))
    target = manifest_path(project, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(target)
    return manifest


def load_manifest(project: str, repo_root: Path | None = None) -> dict[str, Any] | None:
    """Manifesto já gravado, ou None. Consumidores degradam, nunca estouram."""
    path = manifest_path(project, repo_root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def verify_checksum(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """PROTOTYPE-CHECKSUM-CONSISTENCY em forma de função.

    Protótipo regerado depois do manifesto significa que todo `source_anchor`
    das tasks aponta para um arquivo que mudou. É o único jeito de detectar isso
    sem reparsear tudo.
    """
    root = repo_root or REPO_ROOT
    manifest = load_manifest(project, root)
    prototype = root / "projects" / project / PROTOTYPE_REL
    if manifest is None:
        return {"status": "missing", "reason": "manifesto do protótipo não existe",
                "expected": None, "actual": None}
    expected = str((manifest.get("prototype") or {}).get("checksum") or "")
    if not prototype.is_file():
        return {"status": "missing", "reason": f"{PROTOTYPE_REL} não existe",
                "expected": expected, "actual": None}
    actual = _sha256_bytes(prototype.read_bytes())
    return {
        "status": "ok" if actual == expected else "stale",
        "reason": ("" if actual == expected else
                   "o protótipo mudou depois da geração do manifesto; as âncoras "
                   "das tasks podem apontar para conteúdo inexistente"),
        "expected": expected,
        "actual": actual,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prototype_manifest.py")
    parser.add_argument("--project", "-p", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn", action="store_true",
                        help="converte erro de fonte em aviso e retorna exit 0")
    parser.add_argument("--verify", action="store_true",
                        help="apenas confere o checksum do protótipo contra o manifesto")
    args = parser.parse_args(argv)

    if args.verify:
        result = verify_checksum(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json
              else f"checksum do protótipo: {result['status']} {result['reason']}")
        return 0 if result["status"] == "ok" or args.warn else 1

    try:
        manifest = write_manifest(args.project, strict=not args.warn)
    except PrototypeManifestError as exc:
        payload = {"status": "error", "command": "prototype_manifest",
                   "project": args.project, "message": str(exc)}
        if args.warn:
            payload["status"] = "warning"
            print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json
              else f"ERRO: {exc}", file=sys.stderr)
        return 2

    errors = [w for w in manifest["warnings"] if w["severity"] == "error"]
    if args.json:
        print(json.dumps({
            "status": "warning" if errors else "ok",
            "command": "prototype_manifest",
            "project": args.project,
            "path": MANIFEST_REL,
            "screens": len(manifest["screens"]),
            "shared_components": len(manifest["shared_components"]),
            "routes": len(manifest["routes"]),
            "design_tokens": sum(len(manifest["design_system"][key]) for key in
                                 ("colors", "typography", "spacing", "other_tokens")),
            "flows": len(manifest["flows"]),
            "warnings": manifest["warnings"],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"prototype-implementation-manifest.json: "
              f"{len(manifest['screens'])} tela(s), "
              f"{len(manifest['shared_components'])} componente(s) compartilhado(s), "
              f"{len(manifest['warnings'])} aviso(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
