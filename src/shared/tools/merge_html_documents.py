#!/usr/bin/env python3
"""
merge_html_documents.py — Reagrupa fragmentos HTML de um artefato num arquivo unico.

Complementa `merge_html_parts.py`. Aquele resolve fragmentos que sao PEDACOS de um
documento (corte sequencial ou fora de ordem). Este resolve o caso em que cada
fragmento e um DOCUMENTO COMPLETO e independente — cada `*.partN.html` tem o seu
proprio <!DOCTYPE>, <head>, <style>, topbar, <nav> e <script>.

E o caso do summary do F8: a Parte 1 (AS-IS) ja tem no menu lateral os itens de
F2/F4/F5, mas as secoes correspondentes so existem na Parte 2 (TO-BE) — clicar
nesses itens nao faz nada. Concatenar os dois arquivos tambem nao resolve: gera
<html>/<head>/<main> duplicados e sete ids repetidos.

A remontagem em modo `documents` faz:

  head      <head> do primeiro fragmento + as regras CSS que so existem nos demais
            (regras identicas sao descartadas; use --no-css-dedupe para manter)
  topbar    do primeiro fragmento (os demais sao descartados)
  <nav>     menu do primeiro fragmento + os grupos/itens dos demais que apontam
            para secoes ainda nao referenciadas; itens que so linkavam para o
            arquivo da outra parte sao removidos
  <main>    todas as secoes de todos os fragmentos, deduplicadas por id,
            na ordem dos fragmentos; exatamente uma abre visivel
  <script>  um bloco so; blocos repetidos (mesmas funcoes) sao descartados

Se os fragmentos NAO forem documentos completos, o script delega automaticamente
para as estrategias `sequential` / `splice` do merge_html_parts.py.

Uso:
    # Reagrupa e grava na propria pasta
    python src/shared/tools/merge_html_documents.py --input-dir projects/X/outputs/summary

    # Grava numa pasta de destino
    python src/shared/tools/merge_html_documents.py \
        --input-dir projects/X/outputs/summary \
        --output-dir projects/X/outputs/summary/dist

    # So valida e loga, sem gravar; log em arquivo + relatorio JSON
    python src/shared/tools/merge_html_documents.py -i projects/X/outputs/summary \
        --dry-run --log-file merge.log --report merge-report.json

Exit codes:
    0 — OK: todos os grupos remontados e validados sem erro
    1 — FAIL: pelo menos um grupo falhou na remontagem ou na validacao
    2 — NOOP: nenhum grupo `*.partN.html` encontrado na pasta
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from merge_html_parts import (  # noqa: E402  (import depende do sys.path acima)
    PART_RE,
    VOID_TAGS,
    Logger,
    detect_newline,
    detect_strategy,
    discover_groups,
    merge_sequential,
    merge_splice,
    validate_html,
)

# ─────────────────────────────────────────────────────────────────────────────
# Convencoes do template (sobrescreviveis pela CLI)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SECTION_CLASS = "sec"   # <div id="s-xxx" class="sec">   — secao navegavel
DEFAULT_ITEM_CLASS = "ni"       # <div class="ni" onclick="nav('s-xxx',this)">
DEFAULT_GROUP_CLASS = "ng"      # <div class="ng">               — grupo do menu
ACTIVE_CLASS = "on"             # classe que marca secao/item ativo

STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.IGNORECASE | re.DOTALL)
SCRIPT_TAG_RE = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)
SCRIPT_SRC_RE = re.compile(r"\bsrc\s*=", re.IGNORECASE)
INLINE_HANDLER_RE = re.compile(r'\bon[a-z]+="([^"]*)"', re.IGNORECASE)
LITERAL_RE = re.compile(r"""['"]([^'"]+)['"]""")
HREF_RE = re.compile(r'\bhref\s*=\s*"([^"]*)"', re.IGNORECASE)
LOCATION_RE = re.compile(r"\b(?:window\.)?location(?:\.href)?\s*=", re.IGNORECASE)
CLASS_ATTR_RE = re.compile(r'(\bclass\s*=\s*")([^"]*)(")', re.IGNORECASE)
ID_ATTR_RE = re.compile(r'\bid="([^"]+)"')
HTML_TAG_RE = re.compile(r"<html\b", re.IGNORECASE)
BODY_OPEN_RE = re.compile(r"<body\b", re.IGNORECASE)
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Localizador de elementos: offsets reais de cada tag no texto
# ─────────────────────────────────────────────────────────────────────────────

class Element:
    """Um elemento fechado, com os offsets exatos que ele ocupa no texto."""

    __slots__ = ("tag", "attrs", "start", "inner_start", "inner_end", "end")

    def __init__(self, tag: str, attrs: dict, start: int, inner_start: int):
        self.tag = tag
        self.attrs = attrs
        self.start = start
        self.inner_start = inner_start
        self.inner_end = inner_start
        self.end = inner_start

    @property
    def id(self) -> str:
        return self.attrs.get("id") or ""

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def __repr__(self) -> str:  # pragma: no cover — debug
        return f"<{self.tag} id={self.id!r} {self.start}:{self.end}>"


class _Locator(HTMLParser):
    """Percorre o documento e registra o span (start/end) de cada elemento fechado."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.line_off = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                self.line_off.append(i + 1)
        self.stack: list[Element] = []
        self.elements: list[Element] = []
        self.unclosed: list[str] = []

    def _off(self) -> int:
        line, col = self.getpos()
        return self.line_off[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        raw = self.get_starttag_text() or ""
        start = self._off()
        self.stack.append(Element(tag, dict(attrs), start, start + len(raw)))

    def handle_startendtag(self, tag, attrs):
        return  # <br/> e afins: nao abrem escopo

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        start = self._off()
        gt = self.text.find(">", start)
        end = gt + 1 if gt != -1 else start
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                el = self.stack[i]
                el.inner_end = start
                el.end = end
                self.elements.append(el)
                del self.stack[i:]
                return
        # </tag> sem abertura: o merge_html_parts.validate_html reporta isso

    def finish(self) -> None:
        for el in self.stack:
            self.unclosed.append(f"<{el.tag} id={el.id or '-'}>")
        self.elements.sort(key=lambda e: (e.start, -e.end))


# ─────────────────────────────────────────────────────────────────────────────
# Documento parseado
# ─────────────────────────────────────────────────────────────────────────────

class HtmlDoc:
    """Fragmento HTML completo, com os pontos de interesse ja localizados."""

    def __init__(self, path: Path, text: str, cfg: "Config"):
        self.path = path
        self.text = text
        self.cfg = cfg
        loc = _Locator(text)
        loc.feed(text)
        loc.close()
        loc.finish()
        self.elements = loc.elements
        self.unclosed = loc.unclosed

        self.head = self.first(tag="head")
        self.body = self.first(tag="body")
        self.nav = self.first(tag="nav") or self.first(tag="div", el_id="sb")
        self.main = self.first(tag="main") or self.first(tag="div", el_id="mn")

    # -- consultas -----------------------------------------------------------

    def first(self, tag: str | None = None, el_id: str | None = None,
              cls: str | None = None) -> Element | None:
        for el in self.elements:
            if tag and el.tag != tag:
                continue
            if el_id and el.id != el_id:
                continue
            if cls and cls not in el.classes:
                continue
            return el
        return None

    def outermost(self, cls: str, within: Element | None) -> list[Element]:
        """Elementos com a classe `cls` dentro de `within`, sem os aninhados neles."""
        lo = within.inner_start if within else 0
        hi = within.inner_end if within else len(self.text)
        found: list[Element] = []
        for el in self.elements:
            if el.start < lo or el.end > hi:
                continue
            if cls not in el.classes:
                continue
            if found and el.start < found[-1].end:
                continue  # aninhado dentro do anterior
            found.append(el)
        return found

    def html_of(self, el: Element) -> str:
        return self.text[el.start:el.end]

    def inner_of(self, el: Element) -> str:
        return self.text[el.inner_start:el.inner_end]

    @property
    def sections(self) -> list[Element]:
        return self.outermost(self.cfg.section_class, self.main or self.body)

    @property
    def nav_groups(self) -> list[Element]:
        return self.outermost(self.cfg.group_class, self.nav)

    def nav_items(self, within: Element | None = None) -> list[Element]:
        return self.outermost(self.cfg.item_class, within or self.nav)

    @property
    def styles(self) -> list[str]:
        return STYLE_RE.findall(self.text)

    def body_scripts(self) -> list[tuple[int, int, str]]:
        """Blocos <script> inline dentro do <body>: (start, end, codigo)."""
        out = []
        if not self.body:
            return out
        for m in SCRIPT_TAG_RE.finditer(self.text):
            if m.start() < self.body.inner_start or m.end() > self.body.inner_end:
                continue
            if SCRIPT_SRC_RE.search(m.group(1) or ""):
                continue
            out.append((m.start(), m.end(), m.group(2)))
        return out

    @property
    def is_standalone(self) -> bool:
        return bool(HTML_TAG_RE.search(self.text)
                    and BODY_OPEN_RE.search(self.text)
                    and BODY_CLOSE_RE.search(self.text))


class Config:
    def __init__(self, section_class: str, item_class: str, group_class: str,
                 css_dedupe: bool):
        self.section_class = section_class
        self.item_class = item_class
        self.group_class = group_class
        self.css_dedupe = css_dedupe


# ─────────────────────────────────────────────────────────────────────────────
# Utilitarios de edicao
# ─────────────────────────────────────────────────────────────────────────────

def apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    """Aplica substituicoes por span, do fim para o inicio (offsets nao invalidam)."""
    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:start] + repl + text[end:]
    return text


def set_class_flag(html: str, flag: str, enabled: bool) -> str:
    """Liga/desliga uma classe na PRIMEIRA tag do trecho."""
    gt = html.find(">")
    if gt == -1:
        return html
    head, rest = html[:gt + 1], html[gt + 1:]

    def _sub(m: re.Match) -> str:
        classes = m.group(2).split()
        if enabled and flag not in classes:
            classes.append(flag)
        elif not enabled and flag in classes:
            classes = [c for c in classes if c != flag]
        return f"{m.group(1)}{' '.join(classes)}{m.group(3)}"

    return CLASS_ATTR_RE.sub(_sub, head, count=1) + rest


def cut_spans(html: str, base: int, spans: list[tuple[int, int]]) -> str:
    """Remove trechos (offsets absolutos) de um bloco que comeca em `base`."""
    for start, end in sorted(spans, reverse=True):
        s, e = start - base, end - base
        # engole o whitespace/quebra de linha que sobraria
        while e < len(html) and html[e] in " \t":
            e += 1
        if e < len(html) and html[e] == "\n":
            e += 1
        html = html[:s] + html[e:]
    return html


def split_css_rules(css: str) -> list[str]:
    """Quebra CSS em regras de topo (@media conta como uma regra so)."""
    rules, buf, depth = [], [], 0
    for ch in css:
        buf.append(ch)
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth <= 0:
                depth = 0
                rule = "".join(buf).strip()
                if rule:
                    rules.append(rule)
                buf = []
    tail = "".join(buf).strip()
    if tail:
        rules.append(tail)
    return rules


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def item_targets(html: str) -> list[str]:
    """Literais passados aos handlers inline de um item de menu."""
    out: list[str] = []
    for handler in INLINE_HANDLER_RE.findall(html):
        out.extend(LITERAL_RE.findall(handler))
    return out


def is_cross_part_link(html: str, part_names: set[str]) -> bool:
    """Item de menu que so serve para pular para o arquivo de outra parte."""
    if LOCATION_RE.search(html):
        for lit in item_targets(html) + HREF_RE.findall(html):
            if Path(lit).name in part_names or PART_RE.match(Path(lit).name):
                return True
    for href in HREF_RE.findall(html):
        if Path(href.split("#")[0]).name in part_names:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Remontagem modo `documents` (requisito 2)
# ─────────────────────────────────────────────────────────────────────────────

def merge_documents(docs: list[tuple[int, HtmlDoc]], cfg: Config, log: Logger) -> str:
    base_n, base = docs[0]
    part_names = {d.path.name for _, d in docs}
    log.info(f"documento base: parte {base_n} ({base.path.name})")
    for el, label in ((base.head, "<head>"), (base.body, "<body>"),
                      (base.nav, "<nav>"), (base.main, "<main>")):
        log.info(f"base {label}: {'localizado' if el else 'AUSENTE'}", indent=2)
    if not base.body:
        raise ValueError(f"parte {base_n} nao tem <body> — nao da para usar como base")

    # ── 1. SECOES ───────────────────────────────────────────────────────────
    log.info("etapa A — reagrupando secoes de conteudo")
    merged_sections: list[tuple[str, str]] = []   # (id, html)
    seen_sections: dict[str, int] = {}            # id -> parte de origem
    active_id: str | None = None
    for n, doc in docs:
        secs = doc.sections
        kept = 0
        for el in secs:
            sid = el.id
            if not sid:
                log.warn(f"parte {n}: secao sem id descartada (offset {el.start})", indent=2)
                continue
            if sid in seen_sections:
                log.warn(
                    f"parte {n}: secao '{sid}' ja veio da parte {seen_sections[sid]} — "
                    f"duplicata descartada",
                    indent=2,
                )
                continue
            html = doc.html_of(el)
            if ACTIVE_CLASS in el.classes and active_id is None:
                active_id = sid
            merged_sections.append((sid, set_class_flag(html, ACTIVE_CLASS, False)))
            seen_sections[sid] = n
            kept += 1
        log.info(f"parte {n} ({doc.path.name}): {len(secs)} secao(oes), {kept} aproveitada(s)", indent=2)

    if not merged_sections:
        raise ValueError(f"nenhuma secao .{cfg.section_class} encontrada nos fragmentos")

    if active_id is None:
        active_id = merged_sections[0][0]
        log.warn(f"nenhuma secao vinha marcada como '{ACTIVE_CLASS}' — abrindo em '{active_id}'", indent=2)
    merged_sections = [
        (sid, set_class_flag(html, ACTIVE_CLASS, sid == active_id))
        for sid, html in merged_sections
    ]
    section_ids = [sid for sid, _ in merged_sections]
    log.ok(f"{len(merged_sections)} secao(oes) no documento unico; abre em '{active_id}'", indent=2)
    log.info("ordem final: " + ", ".join(section_ids), indent=2)

    # ── 2. MENU ─────────────────────────────────────────────────────────────
    log.info("etapa B — reagrupando o menu de navegacao")
    id_set = set(section_ids)
    linked: set[str] = set()
    nav_inner = ""
    first_item_of: dict[str, bool] = {}

    def classify(doc: HtmlDoc, el: Element, n: int) -> tuple[str, list[str]]:
        html = doc.html_of(el)
        if is_cross_part_link(html, part_names):
            return "cross", []
        targets = [t for t in item_targets(html) if t in id_set]
        if not targets:
            unknown = item_targets(html)
            return ("dead", unknown) if unknown else ("inert", [])
        return "ok", targets

    if base.nav:
        drops: list[tuple[int, int]] = []
        for el in base.nav_items():
            kind, targets = classify(base, el, base_n)
            if kind == "cross":
                log.info(f"parte {base_n}: item que linkava para outro arquivo removido", indent=2)
                drops.append((el.start, el.end))
            elif kind == "dead":
                log.warn(
                    f"parte {base_n}: item aponta para {targets} — secao inexistente, removido",
                    indent=2,
                )
                drops.append((el.start, el.end))
            else:
                linked.update(targets)
        nav_inner = cut_spans(base.inner_of(base.nav), base.nav.inner_start, drops)
        log.info(
            f"parte {base_n}: menu base com {len(base.nav_items())} item(ns), "
            f"{len(drops)} removido(s)",
            indent=2,
        )
    else:
        log.warn(f"parte {base_n} nao tem <nav> — o menu sera montado so com os demais", indent=2)

    extra_groups: list[str] = []
    for n, doc in docs[1:]:
        if not doc.nav:
            log.info(f"parte {n}: sem <nav>, nada a agregar no menu", indent=2)
            continue
        for grp in doc.nav_groups:
            items = doc.nav_items(grp)
            drops, keeps = [], 0
            for el in items:
                kind, targets = classify(doc, el, n)
                if kind == "ok" and not set(targets) & linked:
                    linked.update(targets)
                    keeps += 1
                    continue
                reason = {
                    "cross": "linka para outro arquivo",
                    "dead": "secao inexistente",
                    "inert": "sem alvo de navegacao",
                    "ok": "ja existe no menu base",
                }[kind]
                drops.append((el.start, el.end))
                log.info(f"parte {n}: item removido ({reason})", indent=3)
            if not keeps:
                log.info(f"parte {n}: grupo de menu inteiro descartado ({len(items)} item(ns))", indent=2)
                continue
            html = cut_spans(doc.html_of(grp), grp.start, drops)
            html = set_class_flag(html, ACTIVE_CLASS, False)
            extra_groups.append(html)
            log.info(f"parte {n}: grupo de menu agregado com {keeps} item(ns) novo(s)", indent=2)

    if extra_groups:
        nav_inner = nav_inner.rstrip() + "\n\n" + "\n\n".join(extra_groups) + "\n"

    # exatamente um item ativo — o que aponta para a secao que abre
    nav_inner = re.sub(
        rf'(\bclass\s*=\s*"[^"]*\b{re.escape(cfg.item_class)}\b[^"]*)\s+{ACTIVE_CLASS}\b',
        r"\1",
        nav_inner,
    )
    marked = False
    out_items: list[str] = []
    cursor = 0
    tmp_doc = _wrap_fragment(nav_inner, cfg)
    for el in tmp_doc.nav_items(tmp_doc.body):
        targets = [t for t in item_targets(tmp_doc.html_of(el)) if t == active_id]
        if targets and not marked:
            out_items.append(nav_inner[cursor:el.start])
            out_items.append(set_class_flag(tmp_doc.html_of(el), ACTIVE_CLASS, True))
            cursor = el.end
            marked = True
    out_items.append(nav_inner[cursor:])
    nav_inner = "".join(out_items)
    total_items = len(tmp_doc.nav_items(tmp_doc.body))
    log.ok(
        f"menu unico com {total_items} item(ns) cobrindo {len(linked)}/{len(id_set)} secao(oes)"
        + ("" if marked else f"; nenhum item aponta para '{active_id}'"),
        indent=2,
    )
    orphan = [s for s in section_ids if s not in linked]
    if orphan:
        log.warn(f"{len(orphan)} secao(oes) sem item de menu: {orphan}", indent=2)

    # ── 3. CSS ──────────────────────────────────────────────────────────────
    log.info("etapa C — reagrupando o CSS")
    seen_rules = {norm(r) for css in base.styles for r in split_css_rules(css)}
    extra_rules: list[str] = []
    for n, doc in docs[1:]:
        new, dup = 0, 0
        for css in doc.styles:
            for rule in split_css_rules(css):
                key = norm(rule)
                if cfg.css_dedupe and key in seen_rules:
                    dup += 1
                    continue
                seen_rules.add(key)
                extra_rules.append(rule)
                new += 1
        log.info(f"parte {n}: {new} regra(s) CSS nova(s), {dup} identica(s) descartada(s)", indent=2)
    log.ok(f"CSS final: base + {len(extra_rules)} regra(s) agregada(s)", indent=2)

    # ── 4. SCRIPTS ──────────────────────────────────────────────────────────
    log.info("etapa D — reagrupando o JavaScript")
    merged_js_lines: set[str] = set()
    scripts: list[str] = []
    for n, doc in docs:
        for _, _, code in doc.body_scripts():
            lines = {norm(l) for l in code.splitlines() if norm(l)}
            if lines and lines <= merged_js_lines:
                log.info(f"parte {n}: bloco <script> identico ao ja incluido — descartado", indent=2)
                continue
            merged_js_lines |= lines
            scripts.append(code)
            log.info(f"parte {n}: bloco <script> de {len(lines)} linha(s) uteis mantido", indent=2)
    log.ok(f"{len(scripts)} bloco(s) <script> no documento unico", indent=2)

    # ── 5. MONTAGEM ─────────────────────────────────────────────────────────
    log.info("etapa E — montando o documento unico sobre a base")
    edits: list[tuple[int, int, str]] = []

    for start, end, _ in base.body_scripts():
        edits.append((start, end, ""))
    log.info(f"scripts inline da base removidos do lugar original: {len(base.body_scripts())}", indent=2)

    if base.main:
        body_main = "\n\n".join(html for _, html in merged_sections)
        edits.append((base.main.inner_start, base.main.inner_end, "\n\n" + body_main + "\n\n"))
        log.info("<main> substituido pelo conjunto completo de secoes", indent=2)
    else:
        raise ValueError("documento base nao tem <main> nem container equivalente")

    if base.nav:
        edits.append((base.nav.inner_start, base.nav.inner_end, nav_inner))
        log.info("<nav> substituido pelo menu reagrupado", indent=2)

    if extra_rules and base.head:
        block = (
            "\n<style>\n"
            "/* ── CSS agregado das demais partes por merge_html_documents.py ── */\n"
            + "\n".join(extra_rules)
            + "\n</style>\n"
        )
        edits.append((base.head.inner_end, base.head.inner_end, block))
        log.info(f"bloco <style> com {len(extra_rules)} regra(s) agregado ao <head>", indent=2)

    js_block = "\n" + "\n".join(f"<script>{code}</script>" for code in scripts) + "\n"
    edits.append((base.body.inner_end, base.body.inner_end, js_block))
    log.info(f"{len(scripts)} bloco(s) <script> reposicionado(s) no fim do <body>", indent=2)

    text = apply_edits(base.text, edits)

    # links residuais para os arquivos das partes
    leftovers = [name for name in part_names if name in text]
    for name in leftovers:
        text = text.replace(f'"{name}"', '"#"').replace(f"'{name}'", "'#'")
        log.warn(f"referencia residual ao arquivo '{name}' neutralizada", indent=2)

    text = re.sub(r"\n{4,}", "\n\n\n", text)
    log.ok(f"documento unico montado: {len(text)} caracteres", indent=2)
    return text


def _wrap_fragment(fragment: str, cfg: Config) -> HtmlDoc:
    """Reparseia um trecho solto para poder consultar os elementos dele."""
    wrapped = f"<body>{fragment}</body>"
    doc = HtmlDoc(Path("<fragmento>"), wrapped, cfg)
    # os offsets ficam deslocados de len('<body>'); corrige para o texto original
    shift = len("<body>")
    for el in doc.elements:
        el.start -= shift
        el.inner_start -= shift
        el.inner_end -= shift
        el.end -= shift
    doc.text = fragment
    if doc.body:
        doc.body.inner_start = 0
        doc.body.inner_end = len(fragment)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# Validacao complementar (requisito 3)
# ─────────────────────────────────────────────────────────────────────────────

def validate_coverage(text: str, docs: list[tuple[int, HtmlDoc]], cfg: Config,
                      log: Logger) -> tuple[list[str], list[str], dict]:
    """Confere que o arquivo unico cobre tudo o que estava nos fragmentos."""
    errors: list[str] = []
    warnings: list[str] = []
    out_ids = set(ID_ATTR_RE.findall(text))

    missing: dict[str, list[str]] = {}
    total_in = 0
    for n, doc in docs:
        ids = [el.id for el in doc.sections if el.id]
        total_in += len(ids)
        lost = [i for i in ids if i not in out_ids]
        if lost:
            missing[str(n)] = lost
            errors.append(f"cobertura: secoes da parte {n} ausentes no arquivo unico: {lost}")
    log.info(
        f"cobertura de secoes: {total_in} nos fragmentos, "
        f"{len(missing)} parte(s) com secao faltando",
        indent=2,
    )

    part_names = {d.path.name for _, d in docs}
    residual = sorted(name for name in part_names if name in text)
    for name in residual:
        errors.append(f"o arquivo unico ainda referencia o fragmento '{name}'")
    log.info(f"referencias residuais aos fragmentos: {len(residual)}", indent=2)

    for tag in ("html", "head", "body", "main", "nav", "title"):
        c = len(re.findall(rf"<{tag}\b", text, re.IGNORECASE))
        if c > 1:
            errors.append(f"scaffolding duplicado: <{tag}> aparece {c}x")

    body_scripts = len([m for m in SCRIPT_TAG_RE.finditer(text)])
    log.info(f"blocos <script> no arquivo unico: {body_scripts}", indent=2)

    metrics = {
        "secoes_nos_fragmentos": total_in,
        "secoes_no_arquivo": len(re.findall(
            rf'\bclass="[^"]*\b{re.escape(cfg.section_class)}\b[^"]*"', text)),
        "secoes_faltando": missing,
        "referencias_residuais": residual,
        "blocos_script": body_scripts,
    }
    return errors, warnings, metrics


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline por grupo
# ─────────────────────────────────────────────────────────────────────────────

def process_group(out_name: str, part_files: list[tuple[int, Path]], output_dir: Path,
                  cfg: Config, mode: str, dry_run: bool, force: bool, log: Logger) -> dict:
    result = {
        "arquivo": out_name,
        "partes": [p.name for _, p in part_files],
        "modo": None,
        "saida": None,
        "bytes_entrada": 0,
        "bytes": 0,
        "erros": [],
        "avisos": [],
        "metricas": {},
        "status": "FAIL",
    }

    # ---- leitura -----------------------------------------------------------
    docs: list[tuple[int, HtmlDoc]] = []
    newline = "\n"
    for idx, (n, path) in enumerate(part_files):
        raw = path.read_text(encoding="utf-8")
        if idx == 0:
            newline = detect_newline(raw)
        doc = HtmlDoc(path, raw.replace("\r\n", "\n"), cfg)
        docs.append((n, doc))
        result["bytes_entrada"] += path.stat().st_size
        log.info(
            f"lido {path.name}: {path.stat().st_size} bytes, "
            f"{len(doc.sections)} secao(oes), {len(doc.nav_items()) if doc.nav else 0} item(ns) de menu, "
            f"{'documento completo' if doc.is_standalone else 'fragmento parcial'}",
            indent=2,
        )
        if doc.unclosed:
            log.warn(f"{path.name}: tags sem fechamento: {doc.unclosed[:5]}", indent=2)
    log.info(f"quebra de linha: {'CRLF' if newline == chr(13) + chr(10) else 'LF'}", indent=2)

    # ---- escolha do modo ---------------------------------------------------
    standalone = all(d.is_standalone for _, d in docs) and len(docs) >= 2
    chosen = mode
    if mode == "auto":
        chosen = "documents" if standalone else "legacy"
        log.info(
            f"modo automatico: todos os fragmentos sao documentos completos? "
            f"{'sim' if standalone else 'nao'} -> {chosen}",
            indent=2,
        )
    result["modo"] = chosen

    # ---- remontagem --------------------------------------------------------
    if chosen == "documents":
        log.ok("estrategia: DOCUMENTS (fusao de documentos completos)", indent=2)
        text = merge_documents(docs, cfg, log)
    else:
        log.ok("estrategia: LEGACY (delegando para merge_html_parts)", indent=2)
        parts_lines = [(n, d.path, d.text.splitlines()) for n, d in docs]
        strategy = detect_strategy(parts_lines, log)
        result["modo"] = f"legacy:{strategy}"
        merged = merge_sequential(parts_lines, log) if strategy == "sequential" \
            else merge_splice(parts_lines, log)
        text = "\n".join(merged) + "\n"

    if newline != "\n":
        text = text.replace("\n", newline)
    result["bytes"] = len(text.encode("utf-8"))
    log.ok(
        f"reagrupado: {result['bytes_entrada']} bytes de entrada -> {result['bytes']} bytes de saida"
    )

    # ---- validacao ---------------------------------------------------------
    log.step(f"3/5 Validando '{out_name}'")
    errors, warnings, metrics = validate_html(text, log)
    if chosen == "documents":
        log.info("checagens de cobertura do reagrupamento:", indent=1)
        c_err, c_warn, c_metrics = validate_coverage(text, docs, cfg, log)
        errors += c_err
        warnings += c_warn
        metrics.update(c_metrics)
    result["erros"], result["avisos"], result["metricas"] = errors, warnings, metrics

    for w in warnings:
        log.warn(w, indent=2)
    for e in errors:
        log.error(e, indent=2)
    if errors:
        log.error(f"validacao FALHOU: {len(errors)} erro(s), {len(warnings)} aviso(s)")
    else:
        log.ok(f"validacao PASSOU: 0 erro(s), {len(warnings)} aviso(s)")

    # ---- gravacao ----------------------------------------------------------
    log.step(f"4/5 Gravando '{out_name}'")
    out_path = output_dir / out_name
    result["saida"] = str(out_path)
    if dry_run:
        log.warn(f"--dry-run: nada gravado (seriam {result['bytes']} bytes em {out_path})")
    elif errors and not force:
        log.error("arquivo NAO gravado porque a validacao falhou (use --force para gravar assim mesmo)")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        if errors:
            log.warn(f"--force: gravando apesar de {len(errors)} erro(s)")
        out_path.write_text(text, encoding="utf-8", newline="")
        log.ok(f"gravado: {out_path} ({result['bytes']} bytes)")

    result["status"] = "OK" if not errors else "FAIL"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="merge_html_documents.py",
        description="Reagrupa fragmentos *.partN.html num arquivo unico, valida e loga o processo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input-dir", "-i", required=True, type=Path,
                    help="Pasta que contem os fragmentos *.partN.html (requisito 1)")
    ap.add_argument("--output-dir", "-o", type=Path, default=None,
                    help="Pasta onde o arquivo unico sera gerado (padrao: a propria pasta de entrada)")
    ap.add_argument("--mode", choices=("auto", "documents", "legacy"), default="auto",
                    help="auto (padrao) escolhe entre fusao de documentos e as estrategias legadas")
    ap.add_argument("--recursive", "-r", action="store_true",
                    help="Procura grupos de fragmentos tambem nas subpastas")
    ap.add_argument("--dry-run", action="store_true",
                    help="Executa e valida sem gravar nada em disco")
    ap.add_argument("--force", action="store_true",
                    help="Grava mesmo se a validacao encontrar erros")
    ap.add_argument("--no-css-dedupe", action="store_true",
                    help="Mantem as regras CSS repetidas das demais partes")
    ap.add_argument("--section-class", default=DEFAULT_SECTION_CLASS,
                    help=f"Classe das secoes navegaveis (padrao: {DEFAULT_SECTION_CLASS})")
    ap.add_argument("--item-class", default=DEFAULT_ITEM_CLASS,
                    help=f"Classe dos itens do menu (padrao: {DEFAULT_ITEM_CLASS})")
    ap.add_argument("--group-class", default=DEFAULT_GROUP_CLASS,
                    help=f"Classe dos grupos do menu (padrao: {DEFAULT_GROUP_CLASS})")
    ap.add_argument("--log-file", type=Path, default=None,
                    help="Alem do stdout, grava o log do processo neste arquivo (requisito 5)")
    ap.add_argument("--report", type=Path, default=None,
                    help="Grava um relatorio JSON do processo neste arquivo")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="Nao imprime o log no stdout (util com --log-file)")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    log = Logger(args.log_file, args.quiet)
    started = datetime.now()
    log.info(f"merge_html_documents.py iniciado em {started.isoformat(timespec='seconds')}", indent=0)

    input_dir: Path = args.input_dir.expanduser().resolve()
    if not input_dir.is_dir():
        log.error(f"pasta de entrada nao existe: {input_dir}", indent=0)
        log.close()
        return 1

    cfg = Config(args.section_class, args.item_class, args.group_class,
                 css_dedupe=not args.no_css_dedupe)

    groups = discover_groups(input_dir, args.recursive, log)
    if not groups:
        log.error("nada a fazer", indent=0)
        log.close()
        return 2

    results = []
    for out_path, part_files in groups.items():
        out_name = out_path.name
        out_dir = args.output_dir.expanduser().resolve() if args.output_dir else out_path.parent
        log.step(f"2/5 Reagrupando '{out_name}' ({len(part_files)} partes) -> {out_dir}")
        try:
            res = process_group(out_name, part_files, out_dir, cfg, args.mode,
                                args.dry_run, args.force, log)
        except Exception as exc:  # noqa: BLE001 — um grupo ruim nao derruba os demais
            log.error(f"falha ao reagrupar '{out_name}': {exc}", indent=1)
            res = {
                "arquivo": out_name, "partes": [p.name for _, p in part_files],
                "modo": args.mode, "saida": None, "bytes_entrada": 0, "bytes": 0,
                "erros": [str(exc)], "avisos": [], "metricas": {}, "status": "FAIL",
            }
        results.append(res)

    log.step("5/5 Resumo")
    ok = sum(1 for r in results if r["status"] == "OK")
    for r in results:
        log.info(
            f"[{r['status']:<4}] {r['arquivo']}  <- {len(r['partes'])} parte(s)  "
            f"modo={r['modo']}  bytes={r['bytes']}  "
            f"erros={len(r['erros'])}  avisos={len(r['avisos'])}"
        )
        if r["saida"] and r["status"] == "OK":
            log.info(f"arquivo unico: {r['saida']}", indent=2)
    elapsed = (datetime.now() - started).total_seconds()
    log.info(f"{ok}/{len(results)} grupo(s) OK em {elapsed:.2f}s", indent=0)
    log.info(
        "contagem do log: "
        + ", ".join(f"{k}={v}" for k, v in sorted(log.counts.items()) if k != "STEP"),
        indent=0,
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {
                    "gerado_em": started.isoformat(timespec="seconds"),
                    "input_dir": str(input_dir),
                    "output_dir": str(args.output_dir) if args.output_dir else None,
                    "dry_run": args.dry_run,
                    "duracao_s": round(elapsed, 3),
                    "grupos": results,
                    "log": log.lines,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        log.ok(f"relatorio JSON: {args.report}", indent=0)

    log.close()
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
