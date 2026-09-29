#!/usr/bin/env python3
"""
merge_html_parts.py — Remonta artefatos HTML que o gerador quebrou em varias partes.

Agentes que emitem HTML grande (ava-summary / F8, ava-prototype / F3) estouram o limite
de tokens de saida por resposta e gravam o artefato em fragmentos `*.partN.html`. Nenhum
fragmento abre corretamente no browser: um tem o <head>/CSS mas nao tem o JavaScript,
outro tem o JavaScript mas nao tem o CSS. Esta ferramenta recebe a pasta com os
fragmentos, remonta o documento unico, valida o resultado e loga cada decisao.

Duas modalidades de quebra sao detectadas automaticamente:

  sequential  Corte limpo: so o ultimo fragmento fecha o documento.
              Remontagem = concatenacao na ordem das partes.

  splice      Corte fora de ordem: dois ou mais fragmentos fecham o documento
              (</main>, </body>) e o conteudo esta trocado de lugar — o bloco
              <script> vem antes das secoes que ainda pertencem ao <main>.
              Remontagem = costura cirurgica (secoes reinseridas dentro do
              container, script realocado para o fim do <body>, tags
              duplicadas descartadas).

Uso:
    # Pasta com os fragmentos — saida na propria pasta
    python src/shared/tools/merge_html_parts.py --input-dir projects/X/outputs/summary

    # Saida em outra pasta
    python src/shared/tools/merge_html_parts.py --input-dir projects/X/outputs/summary \
        --output-dir projects/X/outputs/summary/dist

    # Varre subpastas, sem gravar nada (so valida e loga)
    python src/shared/tools/merge_html_parts.py --input-dir projects/X/outputs \
        --recursive --dry-run

    # Grava log em arquivo e relatorio JSON
    python src/shared/tools/merge_html_parts.py --input-dir projects/X/outputs/summary \
        --log-file merge.log --report merge-report.json

Exit codes:
    0 — OK: todos os grupos remontados e validados sem erro
    1 — FAIL: pelo menos um grupo falhou na remontagem ou na validacao
    2 — NOOP: nenhum grupo `*.partN.html` encontrado na pasta
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Padroes de nome de fragmento
# ─────────────────────────────────────────────────────────────────────────────

PART_RE = re.compile(r"^(?P<base>.+?)[._-]part[_-]?(?P<n>\d+)\.(?P<ext>html?)$", re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────────────
# Padroes de estrutura HTML
# ─────────────────────────────────────────────────────────────────────────────

DOC_OPEN_RE = re.compile(r"^\s*(<!DOCTYPE\b|<html\b|<head\b|<body\b)", re.IGNORECASE)
DOC_CLOSE_RE = re.compile(r"</\s*(main|body|html)\s*>", re.IGNORECASE)
MAIN_CLOSE_RE = re.compile(r"^\s*</\s*main\s*>\s*$", re.IGNORECASE)
BODY_CLOSE_RE = re.compile(r"^\s*</\s*body\s*>\s*$", re.IGNORECASE)
HTML_CLOSE_RE = re.compile(r"^\s*</\s*html\s*>\s*$", re.IGNORECASE)
# Linha que contem APENAS um fechamento de container (opcionalmente + comentario)
PURE_CLOSE_RE = re.compile(
    r"^\s*</\s*(main|div|section|aside|nav|header|footer)\s*>\s*(<!--.*?-->)?\s*$", re.IGNORECASE
)
SCRIPT_OPEN_RE = re.compile(r"^\s*<script\b(?![^>]*\bsrc=)", re.IGNORECASE)
SCRIPT_CLOSE_RE = re.compile(r"</\s*script\s*>", re.IGNORECASE)
# Secao de conteudo escondida na marra pelo gerador
HIDDEN_SECTION_RE = re.compile(
    r'(<(?:div|section)\b[^>]*\bclass="[^"]*\b(?:sec|view|section|panel|screen)\b[^"]*")'
    r'\s+style="\s*display:\s*none[^"]*"',
    re.IGNORECASE,
)
# Script "patch" que so desesconde secoes — vira lixo depois da remontagem correta
PATCH_SCRIPT_RE = re.compile(r"""\[style\*=["']display:\s*none""", re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────────────
# Padroes de validacao
# ─────────────────────────────────────────────────────────────────────────────

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
# Tags cujo fechamento e opcional em HTML5 — auto-fecham sem gerar erro
OPTIONAL_CLOSE_TAGS = {
    "li", "p", "tr", "td", "th", "tbody", "thead", "tfoot",
    "option", "optgroup", "dt", "dd", "rt", "rp", "colgroup",
}
SINGLETON_TAGS = {"html", "head", "body", "main", "title"}

ID_ATTR_RE = re.compile(r'\bid="([^"]+)"')
HREF_ANCHOR_RE = re.compile(r'\bhref="#([^"]+)"')
GET_BY_ID_RE = re.compile(r"""getElementById\(\s*['"]([^'"]+)['"]\s*\)""")
QUERY_ID_RE = re.compile(r"""querySelector(?:All)?\(\s*['"]#([A-Za-z_][\w-]*)['"]\s*\)""")
INLINE_HANDLER_RE = re.compile(r'\bon[a-z]+="([^"]*)"', re.IGNORECASE)
# Chamada de funcao que NAO e acesso a membro (nao vem depois de ponto)
CALL_RE = re.compile(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(")
CALL_WITH_STR_RE = re.compile(r"""(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(\s*['"]([^'"]+)['"]""")
FUNC_DEF_RE = re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(")
FUNC_ASSIGN_RE = re.compile(r"\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\()")
WINDOW_ASSIGN_RE = re.compile(r"\bwindow\.([A-Za-z_$][\w$]*)\s*=")
EXTERNAL_RES_RE = re.compile(r'\b(?:src|href)="(https?://[^"]+)"', re.IGNORECASE)
# URL montada em runtime pelo JS (ex.: s.src='https://cdn.jsdelivr.net/...') — nao aparece
# como atributo no HTML, mas quebra igual quando a maquina esta offline.
JS_URL_RE = re.compile(r"""['"](https?://[^'"\s]+\.(?:js|css)(?:\?[^'"\s]*)?)['"]""", re.IGNORECASE)
# Prefixos usados pelos templates AVA para id de secao navegavel. Deliberadamente
# estreito: `page-`/`screen-` sao prefixos de CLASSE nesses templates, nao de id.
ID_LIKE_LITERAL_RE = re.compile(r"""['"]((?:view|sec|tab|panel|s)-[\w-]{2,})['"]""")
SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)

# Identificadores que aparecem como chamada mas nao sao funcoes do documento
JS_NON_FUNCTIONS = {
    "if", "for", "while", "switch", "return", "typeof", "instanceof", "new",
    "delete", "void", "catch", "function", "do", "else", "in", "of", "await",
    "window", "document", "console", "alert", "confirm", "prompt", "event",
    "this", "Number", "String", "Boolean", "Array", "Object", "JSON", "Math",
    "Date", "RegExp", "Promise", "Set", "Map", "parseInt", "parseFloat",
    "isNaN", "encodeURIComponent", "decodeURIComponent", "setTimeout",
    "setInterval", "clearTimeout", "clearInterval", "requestAnimationFrame",
    "localStorage", "sessionStorage", "Error", "Symbol", "BigInt",
}


# ─────────────────────────────────────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────────────────────────────────────

class Logger:
    """Log linear e timestampado do processo de remontagem (requisito 5)."""

    LEVELS = {"STEP": 0, "INFO": 1, "OK": 1, "WARN": 2, "ERROR": 3, "DEBUG": 0}

    def __init__(self, log_file: Path | None = None, quiet: bool = False):
        self._lines: list[str] = []
        self._fh = None
        self._quiet = quiet
        self.counts: Counter = Counter()
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self._fh = log_file.open("w", encoding="utf-8")

    def _emit(self, level: str, msg: str, indent: int = 0) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level:<5}] {'  ' * indent}{msg}"
        self._lines.append(line)
        self.counts[level] += 1
        if not self._quiet:
            print(line, flush=True)
        if self._fh:
            self._fh.write(line + "\n")

    def step(self, msg: str) -> None:
        if self._lines:
            self._emit("STEP", "")
        self._emit("STEP", f"== {msg} ==")

    def info(self, msg: str, indent: int = 1) -> None:
        self._emit("INFO", msg, indent)

    def ok(self, msg: str, indent: int = 1) -> None:
        self._emit("OK", msg, indent)

    def warn(self, msg: str, indent: int = 1) -> None:
        self._emit("WARN", msg, indent)

    def error(self, msg: str, indent: int = 1) -> None:
        self._emit("ERROR", msg, indent)

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    @property
    def lines(self) -> list[str]:
        return list(self._lines)


# ─────────────────────────────────────────────────────────────────────────────
# Descoberta e agrupamento dos fragmentos (requisito 1)
# ─────────────────────────────────────────────────────────────────────────────

def discover_groups(input_dir: Path, recursive: bool, log: Logger) -> dict[Path, list[tuple[int, Path]]]:
    """Varre a pasta e agrupa os fragmentos `*.partN.html` por documento de destino."""
    log.step(f"1/5 Descobrindo fragmentos em {input_dir}")
    log.info(f"modo de varredura: {'recursivo' if recursive else 'somente esta pasta'}")

    files = sorted(input_dir.rglob("*") if recursive else input_dir.glob("*"))
    candidates = [f for f in files if f.is_file()]
    log.info(f"{len(candidates)} arquivo(s) inspecionado(s)")

    groups: dict[Path, list[tuple[int, Path]]] = defaultdict(list)
    for f in candidates:
        m = PART_RE.match(f.name)
        if not m:
            continue
        base, n = m.group("base"), int(m.group("n"))
        # `index.html.part1.html` -> `index.html` | `REL-2026.part1.html` -> `REL-2026.html`
        out_name = base if base.lower().endswith((".html", ".htm")) else f"{base}.html"
        groups[f.parent / out_name].append((n, f))
        log.info(f"fragmento: {f.name}  ->  parte {n} de '{out_name}'", indent=2)

    for out_path in groups:
        groups[out_path].sort(key=lambda t: t[0])

    if not groups:
        log.warn("nenhum arquivo no padrao *.partN.html encontrado")
        return {}

    log.ok(f"{len(groups)} grupo(s) identificado(s)")
    for out_path, parts in groups.items():
        nums = [n for n, _ in parts]
        log.info(f"'{out_path.name}': {len(parts)} parte(s) {nums}", indent=2)
        expected = list(range(min(nums), min(nums) + len(nums)))
        if nums != expected:
            log.warn(f"numeracao nao e contigua ({nums}) — pode haver fragmento faltando", indent=2)
    return dict(groups)


# ─────────────────────────────────────────────────────────────────────────────
# Deteccao da modalidade de quebra
# ─────────────────────────────────────────────────────────────────────────────

def detect_strategy(parts: list[tuple[int, Path, list[str]]], log: Logger) -> str:
    """sequential se so o ultimo fragmento fecha o documento; splice caso contrario."""
    log.info("analisando onde cada fragmento fecha o documento:")
    offenders = []
    for idx, (n, path, lines) in enumerate(parts):
        closers = [
            f"{tag} (linha {i + 1})"
            for i, line in enumerate(lines)
            for tag in DOC_CLOSE_RE.findall(line)
        ]
        is_last = idx == len(parts) - 1
        label = "ultimo" if is_last else f"parte {n}"
        if closers:
            log.info(f"{label}: fecha com {', '.join(closers[:4])}", indent=2)
            if not is_last:
                offenders.append(n)
        else:
            log.info(f"{label}: nao fecha o documento", indent=2)

    if offenders:
        log.info(f"parte(s) {offenders} fecham o documento antes do fim -> scaffolding duplicado")
        log.ok("estrategia: SPLICE (costura cirurgica)")
        return "splice"
    log.info("nenhum fragmento intermediario fecha o documento -> corte limpo")
    log.ok("estrategia: SEQUENTIAL (concatenacao)")
    return "sequential"


# ─────────────────────────────────────────────────────────────────────────────
# Remontagem (requisito 2)
# ─────────────────────────────────────────────────────────────────────────────

def _strip_trailing_doc_close(lines: list[str]) -> tuple[list[str], int]:
    """Remove o rabicho final </body></html> (e linhas vazias) de um bloco."""
    end = len(lines)
    removed = 0
    while end > 0:
        s = lines[end - 1]
        if not s.strip() or BODY_CLOSE_RE.match(s) or HTML_CLOSE_RE.match(s):
            if s.strip():
                removed += 1
            end -= 1
        else:
            break
    return lines[:end], removed


def _extract_scripts(lines: list[str], log: Logger, origin: str) -> tuple[list[str], list[list[str]]]:
    """Separa blocos <script> inline do conteudo, para realoca-los no fim do <body>."""
    content: list[str] = []
    scripts: list[list[str]] = []
    i = 0
    while i < len(lines):
        if SCRIPT_OPEN_RE.match(lines[i]):
            start = i
            block = [lines[i]]
            if not SCRIPT_CLOSE_RE.search(lines[i]):
                i += 1
                while i < len(lines):
                    block.append(lines[i])
                    if SCRIPT_CLOSE_RE.search(lines[i]):
                        break
                    i += 1
            body = "\n".join(block)
            if PATCH_SCRIPT_RE.search(body):
                log.info(
                    f"{origin}: script-patch de visibilidade nas linhas "
                    f"{start + 1}-{i + 1} DESCARTADO (gambiarra do gerador)",
                    indent=2,
                )
            else:
                scripts.append(block)
                log.info(
                    f"{origin}: bloco <script> das linhas {start + 1}-{i + 1} "
                    f"({len(block)} linhas) realocado para o fim do <body>",
                    indent=2,
                )
            i += 1
            continue
        content.append(lines[i])
        i += 1
    return content, scripts


def _unhide_sections(lines: list[str], log: Logger, origin: str) -> list[str]:
    out, n = [], 0
    for line in lines:
        new, hits = HIDDEN_SECTION_RE.subn(r"\1", line)
        n += hits
        out.append(new)
    if n:
        log.info(f"{origin}: {n} secao(oes) com style=\"display:none\" liberadas", indent=2)
    return out


def merge_sequential(parts: list[tuple[int, Path, list[str]]], log: Logger) -> list[str]:
    """Concatena os fragmentos na ordem. Valida que nenhum reabre o documento."""
    log.info("remontando por concatenacao direta")
    out: list[str] = []
    for idx, (n, path, lines) in enumerate(parts):
        if idx > 0:
            reopen = [i + 1 for i, s in enumerate(lines) if DOC_OPEN_RE.match(s)]
            if reopen:
                raise ValueError(
                    f"parte {n} reabre o documento nas linhas {reopen[:5]} — "
                    f"o corte nao e sequencial, esperava-se splice"
                )
        out.extend(lines)
        log.info(f"parte {n} ({path.name}): +{len(lines)} linhas (total {len(out)})", indent=2)
    return out


def merge_splice(parts: list[tuple[int, Path, list[str]]], log: Logger) -> list[str]:
    """Costura cirurgica: reinsere o conteudo das partes seguintes dentro do container
    da parte 1 e realoca os <script> para o fim do <body>."""
    log.info("remontando por costura cirurgica")
    n1, path1, l1 = parts[0]

    # --- parte 1: achar o fechamento do container principal ------------------
    cut = next((i for i, s in enumerate(l1) if MAIN_CLOSE_RE.match(s)), None)
    container = "</main>"
    if cut is None:
        cut = next((i for i, s in enumerate(l1) if BODY_CLOSE_RE.match(s)), None)
        container = "</body>"
    if cut is None:
        raise ValueError(f"parte {n1} nao tem </main> nem </body> — impossivel localizar o corte")
    log.info(f"parte {n1} ({path1.name}): container {container} na linha {cut + 1}", indent=2)

    head = l1[:cut]
    log.info(f"parte {n1}: head = linhas 1-{cut} (head/CSS/topbar/sidebar/secoes)", indent=2)

    # Fechamentos de container que vem logo apos (ex.: </main> + </div> do layout)
    closers: list[str] = []
    j = cut
    while j < len(l1) and PURE_CLOSE_RE.match(l1[j]):
        closers.append(l1[j])
        j += 1
    log.info(f"parte {n1}: fechamentos preservados = {[c.strip() for c in closers]}", indent=2)

    tail, dropped = _strip_trailing_doc_close(l1[j:])
    log.info(
        f"parte {n1}: tail = linhas {j + 1}-{j + len(tail)} "
        f"(watermark/drawer/modais){f', {dropped} tag(s) de fechamento descartada(s)' if dropped else ''}",
        indent=2,
    )
    tail, tail_scripts = _extract_scripts(tail, log, f"parte {n1} tail")

    # --- partes 2..N: conteudo + scripts -------------------------------------
    body_content: list[str] = []
    scripts: list[list[str]] = list(tail_scripts)
    for n, path, lines in parts[1:]:
        origin = f"parte {n} ({path.name})"
        # Descarta o scaffolding duplicado: do ULTIMO </main> ate o fim
        stop = next((i for i in range(len(lines) - 1, -1, -1) if MAIN_CLOSE_RE.match(lines[i])), None)
        if stop is not None:
            log.info(
                f"{origin}: scaffolding duplicado das linhas {stop + 1}-{len(lines)} descartado "
                f"({container}, layout, watermark, </body></html>)",
                indent=2,
            )
            lines = lines[:stop]
        else:
            lines, dropped = _strip_trailing_doc_close(lines)
            if dropped:
                log.info(f"{origin}: {dropped} tag(s) de fechamento final descartada(s)", indent=2)
        # Descarta reabertura de documento, se houver
        reopen = [i for i, s in enumerate(lines) if DOC_OPEN_RE.match(s)]
        if reopen:
            log.warn(f"{origin}: {len(reopen)} linha(s) reabrindo o documento descartada(s)", indent=2)
            lines = [s for i, s in enumerate(lines) if i not in set(reopen)]

        lines, part_scripts = _extract_scripts(lines, log, origin)
        lines = _unhide_sections(lines, log, origin)
        scripts.extend(part_scripts)
        body_content.extend(lines)
        log.info(f"{origin}: +{len(lines)} linhas de conteudo para dentro do {container}", indent=2)

    # --- montagem final ------------------------------------------------------
    out: list[str] = []
    out.extend(head)
    out.append("")
    out.extend(body_content)
    out.extend(closers)
    out.extend(tail)
    for block in scripts:
        out.extend(block)
    out.append("")
    out.append("</body>")
    out.append("</html>")
    log.info(
        f"montagem: head({len(head)}) + conteudo({len(body_content)}) + fechamentos({len(closers)}) "
        f"+ tail({len(tail)}) + {len(scripts)} script(s) + </body></html> = {len(out)} linhas",
        indent=2,
    )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Validacao (requisito 3)
# ─────────────────────────────────────────────────────────────────────────────

class _StructureParser(HTMLParser):
    """Checa aninhamento real das tags (nao contagem cega de abre/fecha)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.problems: list[str] = []
        self.tag_counts: Counter = Counter()

    def handle_starttag(self, tag, attrs):
        self.tag_counts[tag] += 1
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.tag_counts[tag] += 1

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        for depth in range(len(self.stack) - 1, -1, -1):
            if self.stack[depth][0] == tag:
                for orphan, line in self.stack[depth + 1:]:
                    if orphan not in OPTIONAL_CLOSE_TAGS:
                        self.problems.append(f"<{orphan}> aberta na linha {line} nunca foi fechada")
                del self.stack[depth:]
                return
        self.problems.append(f"</{tag}> na linha {self.getpos()[0]} nao tem abertura correspondente")

    def finish(self):
        for orphan, line in self.stack:
            if orphan not in OPTIONAL_CLOSE_TAGS:
                self.problems.append(f"<{orphan}> aberta na linha {line} nunca foi fechada")


def validate_html(text: str, log: Logger) -> tuple[list[str], list[str], dict]:
    """Valida o documento remontado. Retorna (erros, avisos, metricas)."""
    errors: list[str] = []
    warnings: list[str] = []

    # --- 1. aninhamento ------------------------------------------------------
    parser = _StructureParser()
    try:
        parser.feed(text)
        parser.finish()
    except Exception as exc:  # noqa: BLE001 — parser tolerante, so registra
        errors.append(f"parser falhou: {exc}")
    for p in parser.problems:
        errors.append(f"estrutura: {p}")
    log.info(
        f"aninhamento de tags: {len(parser.problems)} problema(s) "
        f"({sum(parser.tag_counts.values())} tags analisadas)",
        indent=2,
    )

    # --- 2. tags que so podem existir uma vez --------------------------------
    for tag in sorted(SINGLETON_TAGS):
        c = parser.tag_counts.get(tag, 0)
        if c > 1:
            errors.append(f"singleton: <{tag}> aparece {c}x (deveria aparecer no maximo 1x)")
    doctypes = len(re.findall(r"<!DOCTYPE\b", text, re.IGNORECASE))
    if doctypes > 1:
        errors.append(f"singleton: <!DOCTYPE> aparece {doctypes}x")
    if doctypes == 0:
        warnings.append("documento sem <!DOCTYPE>")
    log.info(
        "singletons: "
        + ", ".join(f"{t}={parser.tag_counts.get(t, 0)}" for t in ("html", "head", "body", "main"))
        + f", doctype={doctypes}",
        indent=2,
    )

    # --- 3. ids duplicados ---------------------------------------------------
    ids = ID_ATTR_RE.findall(text)
    id_set = set(ids)
    dups = [i for i, c in Counter(ids).items() if c > 1]
    for d in sorted(dups):
        errors.append(f"id duplicado: id=\"{d}\" aparece {ids.count(d)}x")
    log.info(f"ids: {len(id_set)} unicos, {len(dups)} duplicado(s)", indent=2)

    # --- 4. handlers inline apontam para funcoes que existem -----------------
    script_src = "\n".join(SCRIPT_BLOCK_RE.findall(text))
    defined = set(FUNC_DEF_RE.findall(script_src))
    defined |= set(FUNC_ASSIGN_RE.findall(script_src))
    defined |= set(WINDOW_ASSIGN_RE.findall(script_src))

    handlers = INLINE_HANDLER_RE.findall(text)
    called: set[str] = set()
    for h in handlers:
        called.update(CALL_RE.findall(h))
    called -= JS_NON_FUNCTIONS
    missing_fn = sorted(called - defined)
    for fn in missing_fn:
        errors.append(f"handler inline chama {fn}() mas a funcao nao esta definida em nenhum <script>")
    log.info(
        f"handlers inline: {len(handlers)} atributo(s), {len(called)} funcao(oes) usada(s), "
        f"{len(defined)} definida(s), {len(missing_fn)} ausente(s)",
        indent=2,
    )

    # --- 5. alvos de navegacao existem como elemento -------------------------
    anchors = {a for a in HREF_ANCHOR_RE.findall(text) if a and a != "#"}
    missing_anchor = sorted(a for a in anchors if a not in id_set)
    for a in missing_anchor:
        errors.append(f'navegacao: href="#{a}" nao tem elemento com id="{a}"')

    # Detecta funcoes de navegacao pelo padrao dos argumentos (auto-tuning):
    # se a maioria do 1o argumento string de F casa com ids existentes, F navega.
    by_func: dict[str, set[str]] = defaultdict(set)
    for fn, lit in CALL_WITH_STR_RE.findall(text):
        if fn not in JS_NON_FUNCTIONS:
            by_func[fn].add(lit)
    nav_funcs = []
    for fn, lits in by_func.items():
        if len(lits) < 2:
            continue
        hit = sum(1 for l in lits if l in id_set)
        # Metade ou mais dos literais casando com ids reais => F navega por id, e os
        # que nao casam sao referencias quebradas (o sintoma classico do merge errado).
        if hit / len(lits) >= 0.5:
            nav_funcs.append(fn)
            for l in sorted(lits - id_set):
                errors.append(f"navegacao: {fn}('{l}') nao tem elemento com id=\"{l}\"")
    log.info(
        f"navegacao: {len(anchors)} ancora(s), {len(missing_anchor)} quebrada(s); "
        f"funcao(oes) de navegacao detectada(s): {sorted(nav_funcs) or 'nenhuma'}",
        indent=2,
    )

    # Literais com cara de id que nao existem (WARN — pode ser classe CSS)
    id_like = {m for m in ID_LIKE_LITERAL_RE.findall(text)}
    orphan_like = sorted(l for l in id_like if l not in id_set)
    for l in orphan_like:
        warnings.append(f"literal '{l}' parece um id de secao mas nao existe no documento")

    # --- 6. getElementById / querySelector('#id') ----------------------------
    js_ids = set(GET_BY_ID_RE.findall(text)) | set(QUERY_ID_RE.findall(text))
    missing_js = sorted(i for i in js_ids if i not in id_set)
    for i in missing_js:
        warnings.append(f"JS acessa id=\"{i}\" que nao existe no documento (pode ser criado em runtime)")
    log.info(f"acessos por id no JS: {len(js_ids)}, {len(missing_js)} sem elemento correspondente", indent=2)

    # --- 7. recursos externos (tag + injetados pelo JS) ----------------------
    ext_tags = set(EXTERNAL_RES_RE.findall(text))
    ext_js = set(JS_URL_RE.findall(script_src))
    ext = sorted(ext_tags | ext_js)
    if ext:
        log.info(f"recursos externos (exigem internet): {len(ext)}", indent=2)
        for e in ext:
            log.info(f"{e}  [{'tag' if e in ext_tags else 'injetado via JS'}]", indent=3)
        warnings.append(
            f"documento depende de {len(ext)} recurso(s) externo(s) — offline eles nao carregam"
        )
    else:
        log.info("recursos externos: nenhum — documento self-contained", indent=2)

    # --- 8. quantas secoes abrem visiveis ------------------------------------
    visible = len(re.findall(r'class="[^"]*\b(?:sec|view)\b[^"]*\b(?:on|active)\b[^"]*"', text))
    sections = len(re.findall(r'<(?:div|section)\b[^>]*\bclass="[^"]*\b(?:sec|view)\b[^"]*"', text))
    if sections:
        log.info(f"secoes navegaveis: {sections}, visiveis por padrao: {visible}", indent=2)
        if visible == 0:
            warnings.append("nenhuma secao abre visivel por padrao — a pagina abre em branco")
        elif visible > 1:
            warnings.append(f"{visible} secoes abrem visiveis ao mesmo tempo (esperado: 1)")

    metrics = {
        "tags": sum(parser.tag_counts.values()),
        "ids_unicos": len(id_set),
        "ids_duplicados": len(dups),
        "handlers_inline": len(handlers),
        "funcoes_definidas": len(defined),
        "ancoras": len(anchors),
        "secoes": sections,
        "secoes_visiveis": visible,
        "recursos_externos": ext,
        "nav_funcs": sorted(nav_funcs),
    }
    return errors, warnings, metrics


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline por grupo
# ─────────────────────────────────────────────────────────────────────────────

def detect_newline(raw: str) -> str:
    return "\r\n" if raw.count("\r\n") > raw.count("\n") - raw.count("\r\n") else "\n"


def process_group(
    out_name: str,
    part_files: list[tuple[int, Path]],
    output_dir: Path,
    dry_run: bool,
    force: bool,
    log: Logger,
) -> dict:
    result = {
        "arquivo": out_name,
        "partes": [p.name for _, p in part_files],
        "estrategia": None,
        "saida": None,
        "linhas": 0,
        "bytes": 0,
        "erros": [],
        "avisos": [],
        "metricas": {},
        "status": "FAIL",
    }

    # ---- ler ---------------------------------------------------------------
    parts: list[tuple[int, Path, list[str]]] = []
    newline = "\n"
    total_in = 0
    for n, path in part_files:
        raw = path.read_text(encoding="utf-8")
        if n == part_files[0][0]:
            newline = detect_newline(raw)
        lines = raw.splitlines()
        total_in += len(lines)
        parts.append((n, path, lines))
        log.info(f"lido {path.name}: {len(lines)} linhas, {path.stat().st_size} bytes", indent=2)
    log.info(f"quebra de linha detectada: {'CRLF' if newline == chr(13) + chr(10) else 'LF'}", indent=2)

    # ---- estrategia + remontagem ------------------------------------------
    strategy = detect_strategy(parts, log)
    result["estrategia"] = strategy
    merged = merge_sequential(parts, log) if strategy == "sequential" else merge_splice(parts, log)
    result["linhas"] = len(merged)
    log.ok(f"remontado: {total_in} linhas de entrada -> {len(merged)} linhas de saida")

    text = newline.join(merged) + newline

    # ---- validacao ---------------------------------------------------------
    log.step(f"3/5 Validando '{out_name}'")
    errors, warnings, metrics = validate_html(text, log)
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
    result["bytes"] = len(text.encode("utf-8"))
    if dry_run:
        log.warn(f"--dry-run: NADA foi gravado (seriam {result['bytes']} bytes em {out_path})")
    elif errors and not force:
        log.error("arquivo NAO gravado porque a validacao falhou (use --force para gravar mesmo assim)")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        if errors:
            log.warn(f"--force: gravando apesar de {len(errors)} erro(s) de validacao")
        out_path.write_text(text, encoding="utf-8", newline="")
        log.ok(f"gravado: {out_path} ({result['bytes']} bytes, {len(merged)} linhas)")

    result["status"] = "OK" if not errors else "FAIL"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="merge_html_parts.py",
        description="Remonta artefatos HTML quebrados em *.partN.html num arquivo unico e valida o resultado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input-dir", "-i", required=True, type=Path,
                    help="Pasta que contem os fragmentos *.partN.html")
    ap.add_argument("--output-dir", "-o", type=Path, default=None,
                    help="Pasta de destino do arquivo unico (padrao: a propria pasta do fragmento)")
    ap.add_argument("--recursive", "-r", action="store_true",
                    help="Varre subpastas procurando grupos de fragmentos")
    ap.add_argument("--dry-run", action="store_true",
                    help="Executa e valida sem gravar nada em disco")
    ap.add_argument("--force", action="store_true",
                    help="Grava o arquivo mesmo se a validacao encontrar erros")
    ap.add_argument("--log-file", type=Path, default=None,
                    help="Alem do stdout, grava o log do processo neste arquivo")
    ap.add_argument("--report", type=Path, default=None,
                    help="Grava um relatorio JSON do processo neste arquivo")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="Nao imprime o log no stdout (util com --log-file)")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    log = Logger(args.log_file, args.quiet)
    started = datetime.now()
    log.info(f"merge_html_parts.py iniciado em {started.isoformat(timespec='seconds')}", indent=0)

    input_dir: Path = args.input_dir.expanduser().resolve()
    if not input_dir.is_dir():
        log.error(f"pasta de entrada nao existe: {input_dir}", indent=0)
        log.close()
        return 1

    groups = discover_groups(input_dir, args.recursive, log)
    if not groups:
        log.error("nada a fazer", indent=0)
        log.close()
        return 2

    results = []
    for out_path, part_files in groups.items():
        out_name = out_path.name
        out_dir = args.output_dir.expanduser().resolve() if args.output_dir else out_path.parent
        log.step(f"2/5 Remontando '{out_name}' ({len(part_files)} partes) -> {out_dir}")
        try:
            res = process_group(out_name, part_files, out_dir, args.dry_run, args.force, log)
        except Exception as exc:  # noqa: BLE001 — um grupo ruim nao derruba os demais
            log.error(f"falha ao remontar '{out_name}': {exc}", indent=1)
            res = {
                "arquivo": out_name, "partes": [p.name for _, p in part_files],
                "estrategia": None, "saida": None, "linhas": 0, "bytes": 0,
                "erros": [str(exc)], "avisos": [], "metricas": {}, "status": "FAIL",
            }
        results.append(res)

    # ---- resumo ------------------------------------------------------------
    log.step("5/5 Resumo")
    ok = sum(1 for r in results if r["status"] == "OK")
    for r in results:
        log.info(
            f"[{r['status']:<4}] {r['arquivo']}  <- {len(r['partes'])} parte(s)  "
            f"estrategia={r['estrategia']}  linhas={r['linhas']}  bytes={r['bytes']}  "
            f"erros={len(r['erros'])}  avisos={len(r['avisos'])}"
        )
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
