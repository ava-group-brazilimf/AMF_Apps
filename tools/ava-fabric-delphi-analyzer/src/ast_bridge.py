"""
ast_bridge.py — Ponte entre o DelphiAST real (XML) e a IR normalizada.

Fluxo:  load_ast(path) -> ElementTree root  ->  normalize_ast(root) -> IR

A IR normalizada é o contrato que os 8 extratores consomem, para que eles NÃO
dependam do formato bruto do DelphiAST. Se o parser real não estiver disponível,
`load_ast` retorna None e o analyzer cai no fallback regex por arquivo.

Formato do XML do DelphiAST (confirmado no ava_ast_cli):
  METHOD[name,kind,begin_line,end_line]  (impl = nome qualificado 'TClasse.Metodo' + corpo)
    PARAMETERS > PARAMETER > NAME[value] + TYPE[name]
    RETURNTYPE > TYPE[name]
    STATEMENTS ...            <- presença = implementação (não declaração)
  USES > UNIT[name]
  TYPEDECL[name] > TYPE[type='class', name=<pai>]
  FIELD > TYPE[name]
  LITERAL[type='string', value=...]      <- SQL, URLs, nomes de DLL
  CALL > IDENTIFIER[name] | DOT(IDENTIFIER.IDENTIFIER)
  IF / CASE / FOR / WHILE / REPEAT       <- complexidade ciclomática
"""
from __future__ import annotations
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

# No Windows, o binário compilado é o .exe (bin/build-windows/); no Linux/macOS
# é o binário sem extensão. AVA_AST_CLI sempre tem prioridade se setado.
_DEFAULT_BIN_NAME = "ava_ast_cli.exe" if sys.platform == "win32" else "ava_ast_cli"
_DEFAULT_BIN = Path(__file__).parent.parent / "bin" / _DEFAULT_BIN_NAME
BIN_PATH = Path(os.environ.get("AVA_AST_CLI", _DEFAULT_BIN))

DB_COMPONENT_TYPES = {
    "TQuery", "TTable", "TADOQuery", "TADOCommand", "TADOTable", "TFDQuery",
    "TFDTable", "TFDStoredProc", "TStoredProc", "TZQuery", "TIBQuery",
    "TSQLQuery", "TClientDataSet",
}
HTTP_COMPONENT_TYPES = {
    "TIdHTTP", "TNetHTTPClient", "THTTPClient", "TRESTClient", "TRESTRequest",
    "THTTPRIO",
}


# ---------------------------------------------------------------------------
# load_ast — invoca o binário e devolve a raiz XML (ou None)
# ---------------------------------------------------------------------------
def is_available() -> bool:
    return BIN_PATH.exists() and os.access(BIN_PATH, os.X_OK)


def load_ast(pas_path: Path, timeout_sec: int = 30) -> Optional[ET.Element]:
    """Roda o ava_ast_cli e devolve a raiz do XML da AST. None => usar fallback."""
    if not is_available() or pas_path.suffix.lower() != ".pas":
        return None
    fd, tmp_name = tempfile.mkstemp(suffix=".xml")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        r = subprocess.run([str(BIN_PATH), str(pas_path), str(tmp)],
                           capture_output=True, text=True, timeout=timeout_sec)
        if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
            return None
        return ET.fromstring(tmp.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# helpers XML
# ---------------------------------------------------------------------------
def _a(node: ET.Element, key: str, default: str = "") -> str:
    return node.attrib.get(key, default)


def _int(node: ET.Element, key: str, default: int = 0) -> int:
    try:
        return int(node.attrib.get(key, default))
    except (ValueError, TypeError):
        return default


def _callee(call: ET.Element) -> Optional[str]:
    """Extrai o nome do alvo de um CALL (IDENTIFIER simples ou cadeia DOT)."""
    for child in call:
        if child.tag == "IDENTIFIER":
            return _a(child, "name")
        if child.tag == "DOT":
            ids = [_a(i, "name") for i in child.iter("IDENTIFIER") if _a(i, "name")]
            if ids:
                return ".".join(ids[:3])
        if child.tag == "CALL":
            return _callee(child)
    return None


SQL_RE = re.compile(r"\b(select|insert\s+into|update|delete\s+from)\b", re.I)
TABLE_RE = re.compile(r"\b(?:from|into|update|join)\s+([A-Za-z_]\w*)", re.I)


def _sql_meta(value: str) -> Optional[dict[str, Any]]:
    m = SQL_RE.search(value)
    if not m:
        return None
    op = m.group(1).split()[0].lower()
    tables = sorted(set(t.lower() for t in TABLE_RE.findall(value)))
    return {"op": op, "tables": tables,
            "sql": value if len(value) <= 300 else value[:297] + "..."}


# ---- serializador de expressão da AST -> texto legível --------------------
_BINOP = {
    "EQUAL": "=", "NOTEQUAL": "<>", "LOWER": "<", "GREATER": ">",
    "LOWEROREQUAL": "<=", "GREATEROREQUAL": ">=", "ADD": "+", "SUB": "-",
    "MUL": "*", "FDIV": "/", "DIVIDE": "/", "DIV": " div ", "MOD": " mod ",
    "AND": " and ", "OR": " or ", "XOR": " xor ", "IN": " in ",
}
_ARITH = {"ADD", "SUB", "MUL", "FDIV", "DIVIDE", "DIV", "MOD"}
_COMPARISON = {"EQUAL", "NOTEQUAL", "LOWER", "GREATER", "LOWEROREQUAL", "GREATEROREQUAL"}
_VALIDATION_CALLS = re.compile(
    r"ShowMessage|MessageDlg|MessageBox|Application\.MessageBox|Abort|Raise", re.I)


def _unwrap_expr(node: ET.Element) -> ET.Element:
    """Desce por wrappers de um filho só (EXPRESSION/EXPRESSIONS/...) até o nó real."""
    while len(node) == 1 and node.tag not in _BINOP and node.tag != "NOT":
        node = node[0]
    return node


def _expr_to_str(node: ET.Element, depth: int = 0) -> str:
    """Serializa um nó de expressão da AST em texto Pascal aproximado."""
    if depth > 12:
        return "..."
    tag = node.tag
    if tag == "IDENTIFIER":
        return _a(node, "name")
    if tag == "LITERAL":
        v = _a(node, "value")
        return f"'{v}'" if _a(node, "type") == "string" else v
    if tag == "DOT":
        return ".".join(_expr_to_str(c, depth + 1) for c in node)
    if tag == "CALL":
        parts = list(node)
        if not parts:
            return ""
        callee = _expr_to_str(parts[0], depth + 1)
        args = [_expr_to_str(e, depth + 1)
                for exprs in node.findall("EXPRESSIONS")
                for e in exprs.findall("EXPRESSION")]
        return f"{callee}({', '.join(a for a in args if a)})"
    if tag in _BINOP:
        kids = [c for c in node]
        if len(kids) == 2:
            return f"{_expr_to_str(kids[0], depth+1)} {_BINOP[tag]} {_expr_to_str(kids[1], depth+1)}"
    if tag == "NOT":
        return f"not {_expr_to_str(node[0], depth+1)}" if len(node) else "not"
    # EXPRESSION/EXPRESSIONS/RHS/LHS/THEN e afins: desembrulha
    kids = [c for c in node]
    if len(kids) == 1:
        return _expr_to_str(kids[0], depth + 1)
    return " ".join(_expr_to_str(c, depth + 1) for c in kids)


def _method_rules(method: ET.Element, unit: str, file: str, qname: str) -> list[dict]:
    """Extrai candidatos a regra de negócio de UM método (associados ao método)."""
    rules = []

    # validações: IF cujo THEN dispara ShowMessage/MessageDlg/Abort/Raise
    validated_ifs = set()
    for if_node in method.iter("IF"):
        then = if_node.find("THEN")
        actions = []
        if then is not None:
            for call in then.iter("CALL"):
                ident = call.find("IDENTIFIER")
                nm = _a(ident, "name") if ident is not None else ""
                if nm and _VALIDATION_CALLS.search(nm):
                    msg = call.find(".//LITERAL[@type='string']")
                    actions.append(nm + (f"('{_a(msg,'value')}')" if msg is not None else ""))
        # RAISE dentro do THEN
        if then is not None and then.find(".//RAISE") is not None:
            actions.append("raise")
        if not actions:
            continue
        validated_ifs.add(id(if_node))
        expr = if_node.find("EXPRESSION")
        rules.append({
            "type": "validation", "unit": unit, "method": qname,
            "condition": _expr_to_str(expr) if expr is not None else "",
            "action": "; ".join(dict.fromkeys(actions)),
            "fields": sorted({i for i in re.findall(r"[A-Za-z_]\w*\.[A-Za-z_]\w*",
                                                    _expr_to_str(expr) if expr is not None else "")}),
            "source_ref": {"file": file, "line": _int(if_node, "line")},
        })

    # limiares de negócio: IF com comparação numérica binária, mesmo sem ação de
    # validação explícita no THEN (ex.: "if Saldo > 1000 then ApplyDiscount")
    for if_node in method.iter("IF"):
        if id(if_node) in validated_ifs:
            continue
        expr = if_node.find("EXPRESSION")
        if expr is None:
            continue
        cmp_node = _unwrap_expr(expr)
        if cmp_node.tag not in _COMPARISON or len(cmp_node) != 2:
            continue
        lhs, rhs = cmp_node[0], cmp_node[1]
        if lhs.tag == "IDENTIFIER" and rhs.tag == "LITERAL" and _a(rhs, "type") != "string":
            ident, lit = lhs, rhs
        elif rhs.tag == "IDENTIFIER" and lhs.tag == "LITERAL" and _a(lhs, "type") != "string":
            ident, lit = rhs, lhs
        else:
            continue
        rules.append({
            "type": "threshold_condition", "unit": unit, "method": qname,
            "variable": _a(ident, "name"), "operator": _BINOP[cmp_node.tag],
            "threshold": _a(lit, "value"),
            "source_ref": {"file": file, "line": _int(if_node, "line")},
        })

    # cálculos: ASSIGN cujo RHS contém operador aritmético NUMÉRICO (não concat de string)
    for asg in method.iter("ASSIGN"):
        rhs = asg.find("RHS")
        if rhs is None:
            continue
        ops = {c.tag for c in rhs.iter() if c.tag in _ARITH}
        if not ops:
            continue
        # '+' sobre strings usa a mesma tag ADD: se há literal string no RHS,
        # é construção de texto/SQL (pertence a db_rules), não cálculo de negócio
        if any(_a(l, "type") == "string" for l in rhs.iter("LITERAL")):
            continue
        idents = [i for i in rhs.iter("IDENTIFIER")]
        # descarta incrementos triviais tipo i := i + 1
        if ops <= {"ADD", "SUB"} and len(idents) < 2:
            continue
        lhs = asg.find("LHS")
        rules.append({
            "type": "calculation", "unit": unit, "method": qname,
            "target": _expr_to_str(lhs) if lhs is not None else "",
            "expression": _expr_to_str(rhs),
            "source_ref": {"file": file, "line": _int(asg, "line")},
        })

    # classificação de estado: CASE
    for case in method.iter("CASE"):
        expr = case.find("EXPRESSION")
        var = ""
        if expr is not None:
            ident = expr.find(".//IDENTIFIER")
            var = _a(ident, "name") if ident is not None else ""
        states = [_a(l, "value") for l in case.findall(".//CASELABEL//LITERAL")
                  if _a(l, "value")]
        rules.append({
            "type": "state_classification", "unit": unit, "method": qname,
            "variable": var, "states": states,
            "source_ref": {"file": file, "line": _int(case, "line")},
        })
    return rules


# ---------------------------------------------------------------------------
# Utilitários de árvore para cobertura de testes (09_test_coverage)
# ---------------------------------------------------------------------------
_VIS_TAGS = {"PRIVATE": "private", "PROTECTED": "protected",
             "STRICTPRIVATE": "strict_private", "STRICTPROTECTED": "strict_protected",
             "PUBLIC": "public", "PUBLISHED": "published"}
TEST_FRAMEWORK_UNITS = {"testframework", "dunitx", "dunitx.testframework", "dunit"}
TEST_FIXTURE_BASE_CLASSES = {"ttestcase", "tdunitxtestfixture"}


def _index_attributes(root: ET.Element) -> dict[int, list[str]]:
    """id(TYPEDECL|METHOD) -> [nomes de atributo]. ATTRIBUTES é emitido como
    irmão anterior do alvo no mesmo pai (sem id/ref) — precisa de varredura
    posicional (list(node), não .iter(), que perde a ordem entre irmãos).

    Iterativo (pilha explícita, não recursão Python) — árvores AST reais
    (métodos com muitos IF/CASE aninhados) podem passar de 1000 níveis de
    profundidade e estourar o limite de recursão do interpretador."""
    by_target: dict[int, list[str]] = {}
    stack = [root]
    while stack:
        node = stack.pop()
        pending: list[str] = []
        for child in list(node):
            if child.tag == "ATTRIBUTES":
                pending = [_a(n, "value") for n in child.iter("NAME") if _a(n, "value")]
            elif child.tag in ("TYPEDECL", "METHOD"):
                if pending:
                    by_target[id(child)] = pending
                pending = []
            else:
                pending = []
            stack.append(child)
    return by_target


def _index_visibility(root: ET.Element) -> dict[int, dict]:
    """id(METHOD) -> {"visibility": 'private'|'public'|'published'|...,
    "class": nome da classe declarante} — ElementTree não tem .getparent(),
    então visibilidade e classe atuais são propagadas descendo a árvore.

    Iterativo (pilha explícita) pelo mesmo motivo de `_index_attributes`."""
    by_method: dict[int, dict] = {}
    stack: list[tuple[ET.Element, Optional[str], Optional[str]]] = [(root, None, None)]
    while stack:
        node, current_vis, current_class = stack.pop()
        for child in list(node):
            nxt_vis = _VIS_TAGS.get(child.tag, current_vis)
            nxt_class = _a(child, "name") if child.tag == "TYPEDECL" else current_class
            if child.tag == "METHOD" and current_vis:
                by_method[id(child)] = {"visibility": current_vis, "class": current_class}
            stack.append((child, nxt_vis, nxt_class))
    return by_method


def _test_framework_uses(root: ET.Element) -> list[dict]:
    """Re-scan dedicado de USES/UNIT só p/ frameworks de teste — não mexe no
    campo `uses` existente (consumido em outros lugares como set de strings)."""
    hits = []
    for us in root.iter("USES"):
        for u in us.iter("UNIT"):
            name = _a(u, "name")
            if name and name.lower() in TEST_FRAMEWORK_UNITS:
                hits.append({"name": name, "line": _int(u, "line")})
    return hits


# ---------------------------------------------------------------------------
# normalize_ast — XML -> IR
# ---------------------------------------------------------------------------
def normalize_ast(root: ET.Element, file_path: str) -> dict[str, Any]:
    unit = _a(root, "name") or Path(file_path).stem

    # tipo do arquivo (TForm/TDataModule/...) via herança de classe
    file_type = "unit"
    for td in root.iter("TYPEDECL"):
        for t in td.iter("TYPE"):
            parent = _a(t, "name")
            if parent in ("TForm", "TDataModule", "TFrame", "TThread"):
                file_type = parent

    uses = sorted({_a(u, "name") for us in root.iter("USES")
                   for u in us.iter("UNIT") if _a(u, "name")})
    attrs_idx = _index_attributes(root)
    vis_idx = _index_visibility(root)
    test_uses = _test_framework_uses(root)

    classes = []
    for td in root.iter("TYPEDECL"):
        t = td.find("TYPE")
        if t is not None and _a(t, "type") == "class":
            parent_node = t.find("TYPE")   # <TYPE name="TPai"/> aninhado, não o próprio t
            parent = _a(parent_node, "name") if parent_node is not None else ""
            classes.append({"name": _a(td, "name"), "parent": parent or None,
                            "line": _int(td, "begin_line"),
                            "attributes": attrs_idx.get(id(td), [])})

    # métodos: separa implementação (tem corpo) de declaração
    methods = []
    business_rules = []
    for m in root.iter("METHOD"):
        name = _a(m, "name")
        if not name:
            continue
        has_body = m.find(".//STATEMENTS") is not None
        vis_info = vis_idx.get(id(m)) or {}
        cls, short = (name.split(".", 1) if "." in name else (vis_info.get("class"), name))
        rt = m.find("RETURNTYPE/TYPE")
        params = []
        for p in m.findall(".//PARAMETER"):
            nm = p.find("NAME")
            ty = p.find("TYPE")
            params.append({"name": _a(nm, "value") if nm is not None else "",
                           "type": _a(ty, "name") if ty is not None else None})
        begin, end = _int(m, "begin_line"), _int(m, "end_line")
        calls = sorted({c for c in (_callee(x) for x in m.iter("CALL")) if c})
        methods.append({
            "class": cls, "name": short, "qualified_name": name,
            "kind": _a(m, "kind") or "procedure",
            "params": params,
            "returns": _a(rt, "name") if rt is not None else None,
            "begin_line": begin, "end_line": end,
            "loc": max(0, end - begin + 1) if has_body else 0,
            "is_implementation": has_body,
            "calls": calls,
            "visibility": vis_info.get("visibility"),
            "attributes": attrs_idx.get(id(m), []),
        })
        if has_body:
            business_rules.extend(
                _method_rules(m, unit, Path(file_path).name, name))

    fields = [{"name": _field_name(f), "type": _a(f.find("TYPE"), "name")}
              for f in root.iter("FIELD") if f.find("TYPE") is not None]

    string_literals, sql_statements = [], []
    for lit in root.iter("LITERAL"):
        if _a(lit, "type") != "string":
            continue
        val = _a(lit, "value")
        if not val:
            continue
        entry = {"value": val, "line": _int(lit, "line")}
        string_literals.append(entry)
        meta = _sql_meta(val)
        if meta:
            sql_statements.append({**meta, "line": _int(lit, "line")})

    calls = sorted({c for c in (_callee(x) for x in root.iter("CALL")) if c})

    cf = {k.lower(): sum(1 for _ in root.iter(k))
          for k in ("IF", "CASE", "FOR", "WHILE", "REPEAT")}
    cyclomatic = 1 + cf["if"] + cf["case"] + cf["for"] + cf["while"] + cf["repeat"]

    return {
        "unit": unit, "file": Path(file_path).name, "file_type": file_type,
        "uses": uses, "test_uses": test_uses, "classes": classes,
        "methods": methods, "fields": fields,
        "business_rules": business_rules,
        "string_literals": string_literals, "sql_statements": sql_statements,
        "calls": calls, "control_flow": cf, "cyclomatic": cyclomatic,
        "db_components": sorted({f["type"] for f in fields
                                 if f["type"] in DB_COMPONENT_TYPES}),
        "http_components": sorted({f["type"] for f in fields
                                   if f["type"] in HTTP_COMPONENT_TYPES}),
    }


def _field_name(field: ET.Element) -> str:
    nm = field.find("NAME")
    if nm is not None:
        return _a(nm, "value") or _a(nm, "name")
    return _a(field, "name")


def build_ir(pas_path: Path) -> Optional[dict[str, Any]]:
    """Conveniência: load_ast + normalize_ast num passo. None => fallback."""
    root = load_ast(pas_path)
    return normalize_ast(root, str(pas_path)) if root is not None else None
