"""
delphi_ast_analyzer.py — Extrator de levantamento de legado Delphi (v0.1).

Percorre uma árvore de fontes Delphi (.pas / .dfm) e produz OS 8 ARTEFATOS JSON:

    01_business_rules        05_procedures
    02_form_business_rules   06_integrations
    03_database_rules        07_apis
    04_database_schemas      08_code_overview

Estratégia de parsing (dois níveis, como já usado no AVA Fabric):
    1) DelphiAST real (RomanYankovsky/DelphiAST compilado via FPC) — se disponível,
       via hook `load_ast()`. Substitua o corpo do hook pela sua integração.
    2) Fallback por heurística/regex — SEMPRE funciona standalone (é o que roda aqui).

Esta é uma VERSÃO INICIAL: as heurísticas cobrem os padrões Delphi mais comuns
(TFDQuery/TADOQuery/TTable, TIdHTTP/TRESTClient, CreateOleObject, external '.dll',
handlers OnExit/OnValidate/OnChange, SQL embutido, etc.). Cada extrator é isolado
para você refinar ponto a ponto sem quebrar os demais.
"""
from __future__ import annotations
import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Any

from schemas import envelope, new_run_id, ARTIFACTS


# ----------------------------------------------------------------------------
# Hook para o DelphiAST real. Retorne uma AST (ou None p/ cair no regex).
# ----------------------------------------------------------------------------
def load_ast(pas_path: Path):  # pragma: no cover - ponto de integração
    """
    Ponto de integração com o seu parser DelphiAST compilado.
    Ex.: subprocess para o binário que emite AST em JSON, ou libffi.
    Enquanto retornar None, o analisador usa o fallback por regex.
    """
    return None


# ----------------------------------------------------------------------------
# Utilitários de leitura
# ----------------------------------------------------------------------------
def read_text(p: Path) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return p.read_bytes().decode("latin-1", errors="replace")


def strip_comments(src: str) -> str:
    src = re.sub(r"\(\*.*?\*\)", " ", src, flags=re.S)
    src = re.sub(r"\{.*?\}", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    return src


def line_of(src: str, idx: int) -> int:
    return src.count("\n", 0, idx) + 1


def unit_name(src: str, fallback: str) -> str:
    m = re.search(r"\bunit\s+([A-Za-z_][\w.]*)", src, re.I)
    return m.group(1) if m else fallback


# ----------------------------------------------------------------------------
# 05 — PROCEDURES / FUNCTIONS do código
# ----------------------------------------------------------------------------
PROC_RE = re.compile(
    r"\b(procedure|function)\s+([A-Za-z_][\w.]*)\s*(\(([^)]*)\))?\s*(?::\s*([\w.]+))?\s*;",
    re.I)


CLASS_DECL_RE = re.compile(
    r"\b([A-Za-z_]\w*)\s*=\s*class\b(?!\s+of\b)(?:\s*\(\s*([A-Za-z_][\w.]*)\s*\))?", re.I)


def overview_fallback(files: list[tuple[Path, str]]) -> dict[str, Any]:
    """Contagem aproximada (regex) de classes/LOC para arquivos sem AST disponível."""
    classes = 0
    loc = 0
    class_list: list[dict[str, Any]] = []
    for path, src in files:
        clean = strip_comments(src)
        for m in CLASS_DECL_RE.finditer(clean):
            classes += 1
            class_list.append({"name": m.group(1), "parent": m.group(2),
                              "file": path.name, "line": line_of(clean, m.start())})
        loc += src.count("\n") + 1
    return {"classes": classes, "loc_total": loc, "class_list": class_list}


# ----------------------------------------------------------------------------
# 09 — COBERTURA DE TESTES (frameworks DUnit/DUnitX + artefatos auxiliares)
# ----------------------------------------------------------------------------
TEST_FILENAME_PATTERNS = ["*test*.pas", "*spec*.pas", "*tests.pas",
                          "dunit*.pas", "*testcase*.pas", "*_test.pas"]
TEST_FIXTURE_BASE_CLASSES = {"ttestcase", "tdunitxtestfixture"}

TEST_FRAMEWORK_UNIT_RE = re.compile(r"\b(TestFramework|DUnitX(?:\.TestFramework)?|DUnit)\b", re.I)
TEST_ATTRIBUTE_RE = re.compile(r"^\s*\[\s*(TestFixture|Test|TestCase)\b[^\]]*\]", re.I | re.M)
PUBLISHED_BLOCK_RE = re.compile(
    r"\bpublished\b(.*?)(?=\b(?:strict\s+private|strict\s+protected|private|protected|public|published)\b|end\s*;)",
    re.I | re.S)
PUBLISHED_TEST_METHOD_RE = re.compile(r"\bprocedure\s+(Test\w*)\s*;", re.I)


def is_test_filename(path: Path) -> bool:
    """Nome de arquivo bate em algum padrão convencional de teste Delphi."""
    name = path.name.lower()
    return any(fnmatch.fnmatch(name, pat) for pat in TEST_FILENAME_PATTERNS)


def extract_test_coverage(files: list[tuple[Path, str]]) -> dict[str, Any]:
    """Fallback regex (para .pas sem AST disponível) dos mesmos sinais que
    o caminho AST detecta: uses de framework, herança de fixture, atributos
    [TestFixture]/[Test] e métodos published Test*."""
    findings: list[dict[str, Any]] = []
    for path, src in files:
        clean = strip_comments(src)
        for m in TEST_FRAMEWORK_UNIT_RE.finditer(clean):
            findings.append({"kind": "framework_uses", "name": m.group(1), "detected_via": "regex",
                            "source_ref": {"file": path.name, "line": line_of(clean, m.start())}})
        for m in CLASS_DECL_RE.finditer(clean):
            if (m.group(2) or "").lower() in TEST_FIXTURE_BASE_CLASSES:
                findings.append({"kind": "fixture_class", "name": m.group(1), "detected_via": "regex",
                                "source_ref": {"file": path.name, "line": line_of(clean, m.start())}})
        for m in TEST_ATTRIBUTE_RE.finditer(clean):
            findings.append({"kind": "attribute", "name": m.group(1), "detected_via": "regex",
                            "source_ref": {"file": path.name, "line": line_of(clean, m.start())}})
        for block in PUBLISHED_BLOCK_RE.finditer(clean):
            for tm in PUBLISHED_TEST_METHOD_RE.finditer(block.group(1)):
                findings.append({"kind": "published_test_method", "name": tm.group(1), "detected_via": "regex",
                                "source_ref": {"file": path.name,
                                               "line": line_of(clean, block.start(1) + tm.start())}})
    by_kind: dict[str, int] = {}
    for f in findings:
        by_kind[f["kind"]] = by_kind.get(f["kind"], 0) + 1
    return {"counts": {"total": len(findings), "by_kind": by_kind}, "test_findings": findings}


# Artefatos auxiliares de teste (nunca são código Delphi — sempre regex/glob,
# independente de o AST estar disponível ou não).
CI_CONTENT_RE = re.compile(r"test|dunit", re.I)
AUX_TEST_PATTERNS = {
    "manual_doc":    ["*test*.txt", "*test*.docx", "*test*.xls", "*test*.xlsx", "*roteiro*.md"],
    "runner_config": ["*.dunitx", "*.testrunner", "TestInsight*.ini", "*.nunit", "*.runsettings"],
    "ci_test_stage": ["*.yml", "*.yaml", "Jenkinsfile", "*.ps1"],   # + gate de conteúdo abaixo
    "test_data":     ["*fixture*.*", "*mock*.*", "*testdata*.*", "*seed*.*"],
}
AUX_LABELS = {"manual_doc": "Manual — Documented", "runner_config": "Runner Config",
             "ci_test_stage": "CI Test Stage", "test_data": "Test Data"}


def scan_test_indicators(source_root: Path) -> dict[str, Any]:
    """Varre a árvore inteira (não só .pas/.dfm) por artefatos indicadores de
    teste que não são código Delphi: docs manuais, configs de runner, CI/CD
    com stage de teste, dados de teste/fixtures."""
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, Path]] = set()
    for category, patterns in AUX_TEST_PATTERNS.items():
        for pat in patterns:
            for fp in source_root.rglob(pat):
                if not fp.is_file() or (category, fp) in seen:
                    continue
                if category == "ci_test_stage" and not CI_CONTENT_RE.search(read_text(fp)):
                    continue
                seen.add((category, fp))
                items.append({"category": category, "label": AUX_LABELS[category],
                            "source_ref": {"file": fp.name,
                                           "path": str(fp.relative_to(source_root)), "line": None}})
    counts = {c: sum(1 for it in items if it["category"] == c) for c in AUX_TEST_PATTERNS}
    return {"counts": counts, "items": items}


def extract_procedures(files: list[tuple[Path, str]]) -> dict[str, Any]:
    code_procs: list[dict[str, Any]] = []
    stored_procs: dict[str, dict[str, Any]] = {}

    for path, src in files:
        clean = strip_comments(src)
        unit = unit_name(clean, path.stem)
        seen: set[tuple[str, str]] = set()
        for m in PROC_RE.finditer(clean):
            kind, name = m.group(1).lower(), m.group(2)
            key = (name.lower(), kind)
            if key in seen:      # ignora a 2ª ocorrência (declaração vs implementação)
                continue
            seen.add(key)
            params = [p.strip() for p in (m.group(4) or "").split(";") if p.strip()]
            code_procs.append({
                "unit": unit,
                "name": name,
                "kind": kind,
                "params": params,
                "returns": (m.group(5) or None) if kind == "function" else None,
                "source_ref": {"file": path.name, "line": line_of(clean, m.start())},
            })

        # stored procedures chamadas (TFDStoredProc / TStoredProc / EXEC / ExecProc)
        for sm in re.finditer(r"StoredProcName\s*=\s*'([^']+)'", src, re.I):
            _add_sp(stored_procs, sm.group(1), path, src, sm.start())
        for sm in re.finditer(r"(?:exec(?:ute)?\s+procedure\s+|EXEC\s+)([A-Za-z_]\w+)",
                              src, re.I):
            _add_sp(stored_procs, sm.group(1), path, src, sm.start())

    return {
        "counts": {"code_procedures": len(code_procs),
                   "stored_procedures": len(stored_procs)},
        "code_procedures": code_procs,
        "stored_procedures": list(stored_procs.values()),
    }


def _add_sp(bucket, name, path, src, idx):
    key = name.lower()
    if key not in bucket:
        bucket[key] = {"name": name, "called_from": [], "params": []}
    bucket[key]["called_from"].append(
        {"file": path.name, "line": line_of(src, idx)})


# ----------------------------------------------------------------------------
# 01 — REGRAS DE NEGÓCIO (validações, cálculos, workflow no código)
# ----------------------------------------------------------------------------
RULE_PATTERNS = [
    ("validation", re.compile(
        r"\bif\b[^;]{0,200}?\bthen\b\s*(?:raise|Abort|ShowMessage|MessageDlg)"
        r"[^;]{0,200};", re.I | re.S)),
    ("validation", re.compile(r"\braise\s+E\w+\.Create[^;]{0,200};", re.I)),
    ("calculation", re.compile(
        r"\b([A-Za-z_]\w*)\s*:=\s*[^;\n]*?[\*/+\-][^;\n]*?;", re.I)),
]

# limiares de negócio: IF com comparação numérica binária, mesmo sem ação de
# validação explícita no THEN (ex.: "if Saldo > 1000 then ApplyDiscount")
THRESHOLD_RE = re.compile(
    r"\bif\b[^;]{0,150}?\b([A-Za-z_]\w*)\s*(>=|<=|<>|=|>|<)\s*(\d+(?:\.\d+)?)\b"
    r"[^;]{0,150}?\bthen\b", re.I)


def extract_business_rules(files: list[tuple[Path, str]]) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    rid = 0
    for path, src in files:
        clean = strip_comments(src)
        unit = unit_name(clean, path.stem)
        validated_lines: set[int] = set()
        for rtype, pat in RULE_PATTERNS:
            for m in pat.finditer(clean):
                snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:240]
                if rtype == "calculation" and not re.search(r"[\*/]", snippet):
                    continue  # reduz ruído: só cálculo com mult/div
                line = line_of(clean, m.start())
                if rtype == "validation":
                    validated_lines.add(line)
                rid += 1
                rules.append({
                    "id": f"BR-{rid:04d}",
                    "unit": unit,
                    "type": rtype,
                    "statement": snippet,
                    "fields": sorted(set(re.findall(r"\b[A-Za-z_]\w*\.[A-Za-z_]\w*",
                                                    snippet)))[:12],
                    "source_ref": {"file": path.name, "line": line},
                })
        for m in THRESHOLD_RE.finditer(clean):
            line = line_of(clean, m.start())
            if line in validated_lines:
                continue  # já classificado como validation nesta linha
            rid += 1
            rules.append({
                "id": f"BR-{rid:04d}",
                "unit": unit,
                "type": "threshold_condition",
                "statement": re.sub(r"\s+", " ", m.group(0)).strip()[:240],
                "fields": [m.group(1)],
                "source_ref": {"file": path.name, "line": line},
            })
    return {"counts": {"total": len(rules)}, "rules": rules}


# ----------------------------------------------------------------------------
# 02 — REGRAS EM TELAS / FORMS (tratamento de campos)
# ----------------------------------------------------------------------------
DFM_OBJECT_RE = re.compile(r"^\s*object\s+(\w+):\s*(\w+)", re.I | re.M)
FIELD_PROPS = ["EditMask", "MaxLength", "Required", "ReadOnly", "Enabled",
               "Visible", "CharCase", "PasswordChar", "DataField", "DataSource"]
FIELD_EVENTS = ["OnExit", "OnChange", "OnValidate", "OnKeyPress", "OnClick",
                "OnEnter", "OnDblClick"]
INPUT_CLASSES = ("Edit", "ComboBox", "DBEdit", "DBComboBox", "MaskEdit",
                 "DateTimePicker", "CheckBox", "RadioGroup", "Memo", "DBGrid",
                 "SpinEdit", "DBLookupComboBox")


def extract_form_rules(dfm_files: list[tuple[Path, str]]) -> dict[str, Any]:
    forms: list[dict[str, Any]] = []
    for path, src in dfm_files:
        objects = list(DFM_OBJECT_RE.finditer(src))
        if not objects:
            continue
        form_name, form_class = objects[0].group(1), objects[0].group(2)
        fields: list[dict[str, Any]] = []
        for i, obj in enumerate(objects[1:], start=1):
            name, cls = obj.group(1), obj.group(2)
            if not any(k in cls for k in INPUT_CLASSES):
                continue
            end = objects[i + 1].start() if i + 1 < len(objects) else len(src)
            block = src[obj.start():end]
            props = {p: _dfm_val(block, p) for p in FIELD_PROPS
                     if _dfm_val(block, p) is not None}
            events = {e: _dfm_val(block, e) for e in FIELD_EVENTS
                      if _dfm_val(block, e) is not None}
            fields.append({
                "name": name, "component_class": cls,
                "properties": props,
                "event_handlers": events,
                "has_validation": bool(events.get("OnValidate") or events.get("OnExit")),
            })
        forms.append({
            "form_name": form_name, "form_class": form_class,
            "source_file": path.name,
            "field_count": len(fields),
            "fields": fields,
        })
    total_fields = sum(f["field_count"] for f in forms)
    return {"counts": {"forms": len(forms), "fields": total_fields}, "forms": forms}


def _dfm_val(block: str, prop: str):
    m = re.search(rf"^\s*{prop}\s*=\s*(.+)$", block, re.I | re.M)
    return m.group(1).strip() if m else None


# ----------------------------------------------------------------------------
# 04 — SCHEMAS DE BANCO (DDL embutido + field defs em .dfm)
# ----------------------------------------------------------------------------
CREATE_TABLE_RE = re.compile(
    r"create\s+table\s+([A-Za-z_][\w.]*)\s*\((.*?)\)\s*;", re.I | re.S)
DFM_FIELD_RE = re.compile(
    r"object\s+\w+:\s*T(\w+)Field\s+FieldName\s*=\s*'([^']+)'", re.I)
ALTER_FK_RE = re.compile(
    r"alter\s+table\s+([A-Za-z_][\w.]*)\s+add\s+(?:constraint\s+([A-Za-z_][\w.]*)\s+)?"
    r"foreign\s+key\s*\(([^)]+)\)\s*references\s+([A-Za-z_][\w.]*)"
    r"(?:\s*\(([^)]+)\))?\s*(?:on\s+delete\s+\w+)?\s*(?:on\s+update\s+\w+)?\s*;",
    re.I | re.S)


def _drop_table_constraints(body: str) -> str:
    """Remove inline CONSTRAINT ... clauses from CREATE TABLE body."""
    out = []
    for raw in re.split(r",(?![^(]*\))", body):
        stripped = raw.strip()
        if re.match(r"constraint\b", stripped, re.I):
            continue
        out.append(raw)
    return ",".join(out)


def _extract_inline_constraints(body: str) -> dict[str, Any]:
    """Extrai PK, FKs, UNIQUE e índices inline de CREATE TABLE."""
    pk, fks, uqs, idxs = [], [], [], []
    for raw in re.split(r",(?![^(]*\))", body):
        stripped = raw.strip()
        if not stripped or not re.match(r"constraint\b", stripped, re.I):
            continue
        name = ""
        nm = re.match(r"constraint\s+([A-Za-z_][\w.]*)\s+(.*)", stripped, re.I | re.S)
        if nm:
            name, stripped = nm.group(1), nm.group(2).strip()
        if re.match(r"primary\s+key\s*\(", stripped, re.I):
            m = re.match(r"primary\s+key\s*\(([^)]+)\)", stripped, re.I)
            if m:
                pk = [c.strip().strip('"[]`') for c in m.group(1).split(",")]
        elif re.match(r"foreign\s+key\s*\(", stripped, re.I):
            m = re.match(r"foreign\s+key\s*\(([^)]+)\)\s*references\s+([A-Za-z_][\w.]*)",
                         stripped, re.I)
            if m:
                fks.append({
                    "name": name,
                    "columns": [c.strip().strip('"[]`') for c in m.group(1).split(",")],
                    "references_table": m.group(2).split(".")[-1].strip('"[]`'),
                    "references_columns": [],
                })
        elif re.match(r"unique\s*\(", stripped, re.I):
            m = re.match(r"unique\s*\(([^)]+)\)", stripped, re.I)
            if m:
                uqs.append({"name": name,
                            "columns": [c.strip().strip('"[]`') for c in m.group(1).split(",")]})
        else:
            idxs.append({"name": name, "definition": stripped[:200]})
    return {"primary_key": pk, "foreign_keys": fks,
            "unique_keys": uqs, "indexes": idxs}


def extract_db_schemas(files: list[tuple[Path, str]]) -> dict[str, Any]:
    tables: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []

    def _table_name(n: str) -> str:
        return n.split(".")[-1].strip('"[]`').lower()

    for path, src in files:
        clean = strip_comments(src)
        for m in CREATE_TABLE_RE.finditer(clean):
            tname = m.group(1)
            body = _drop_table_constraints(m.group(2))
            cols = _parse_ddl_columns(body)
            constraints = _extract_inline_constraints(m.group(2))
            tables[tname.lower()] = {
                "name": tname, "source": {"file": path.name,
                                          "line": line_of(clean, m.start())},
                "origin": "ddl", "columns": cols,
                "primary_key": constraints.get("primary_key")
                               or [c["name"] for c in cols if c.get("pk")],
                "foreign_keys": constraints.get("foreign_keys", []),
                "unique_keys": constraints.get("unique_keys", []),
                "indexes": constraints.get("indexes", []),
            }
        # ALTER TABLE ... ADD FOREIGN KEY ...
        for m in ALTER_FK_RE.finditer(clean):
            child = _table_name(m.group(1))
            child_cols = [c.strip().strip('"[]`').lower() for c in m.group(3).split(",")]
            parent = _table_name(m.group(4))
            parent_cols_raw = m.group(5)
            parent_cols = [c.strip().strip('"[]`').lower() for c in parent_cols_raw.split(",")] if parent_cols_raw else []
            relationships.append({
                "kind": "fk", "source_table": child, "source_columns": child_cols,
                "target_table": parent, "target_columns": parent_cols,
                "constraint_name": (m.group(2) or "").strip(),
                "source_ref": {"file": path.name, "line": line_of(clean, m.start())},
            })

    # field defs de datasets em .dfm (quando não há DDL)
    dataset_fields: dict[str, list[dict[str, str]]] = {}
    for path, src in files:
        if path.suffix.lower() != ".dfm":
            continue
        for m in DFM_FIELD_RE.finditer(src):
            dataset_fields.setdefault(path.stem, []).append(
                {"name": m.group(2), "delphi_type": m.group(1)})
    return {
        "counts": {"tables_ddl": len(tables),
                   "datasets_dfm": len(dataset_fields),
                   "relationships": len(relationships)},
        "tables": list(tables.values()),
        "relationships": relationships,
        "dataset_fields": [{"dataset": k, "fields": v}
                           for k, v in dataset_fields.items()],
    }


def _parse_ddl_columns(body: str) -> list[dict[str, Any]]:
    cols = []
    for raw in re.split(r",(?![^(]*\))", body):
        raw = raw.strip()
        if not raw or re.match(r"(primary|foreign|constraint|key|unique|check)\b",
                               raw, re.I):
            _mark_pk(cols, raw)
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        cols.append({
            "name": parts[0].strip('"[]`'),
            "data_type": parts[1],
            "nullable": "not null" not in raw.lower(),
            "pk": "primary key" in raw.lower(),
        })
    return cols


def _mark_pk(cols, raw):
    m = re.search(r"primary\s+key\s*\(([^)]+)\)", raw, re.I)
    if not m:
        return
    pk_cols = {c.strip().strip('"[]`').lower() for c in m.group(1).split(",")}
    for c in cols:
        if c["name"].lower() in pk_cols:
            c["pk"] = True


# ----------------------------------------------------------------------------
# 03 — REGRAS DE BANCO (transações, integridade, SQL de escrita)
# ----------------------------------------------------------------------------
def extract_db_rules(files: list[tuple[Path, str]]) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    rid = 0
    for path, src in files:
        for m in re.finditer(r"\b(StartTransaction|Commit|Rollback)\b", src, re.I):
            rid += 1
            rules.append({"id": f"DBR-{rid:04d}", "type": "transaction",
                          "operation": m.group(1),
                          "source_ref": {"file": path.name,
                                         "line": line_of(src, m.start())}})
        for m in re.finditer(r"\b(insert\s+into|update\s+|delete\s+from)\s+([A-Za-z_]\w*)",
                             src, re.I):
            rid += 1
            rules.append({"id": f"DBR-{rid:04d}", "type": "write_operation",
                          "operation": m.group(1).strip().lower().split()[0],
                          "table": m.group(2),
                          "source_ref": {"file": path.name,
                                         "line": line_of(src, m.start())}})
    return {"counts": {"total": len(rules)}, "rules": rules}


# ----------------------------------------------------------------------------
# 06 — INTEGRAÇÕES (DLL, COM, sockets, e-mail, arquivos, filas)
# ----------------------------------------------------------------------------
INTEGRATION_PATTERNS = {
    "dll":    re.compile(r"external\s+'([^']+\.dll)'", re.I),
    "com":    re.compile(r"CreateOleObject\s*\(\s*'([^']+)'", re.I),
    "email":  re.compile(r"\bT?IdSMTP\b|\bTIdMessage\b", re.I),
    "socket": re.compile(r"\bT(?:Id)?(?:TCP|UDP)(?:Client|Server)\b|"
                         r"\bTClientSocket\b|\bTServerSocket\b", re.I),
    "file":   re.compile(r"\b(AssignFile|TFileStream\.Create|TStringList\.LoadFromFile)"
                         r"\b", re.I),
    "queue":  re.compile(r"\b(RabbitMQ|MSMQ|TibcoRV|Kafka)\b", re.I),
}


def extract_integrations(files: list[tuple[Path, str]]) -> dict[str, Any]:
    integrations: list[dict[str, Any]] = []
    iid = 0
    for path, src in files:
        for itype, pat in INTEGRATION_PATTERNS.items():
            for m in pat.finditer(src):
                iid += 1
                integrations.append({
                    "id": f"INT-{iid:04d}", "type": itype,
                    "target": (m.group(1) if m.groups() else m.group(0)),
                    "source_ref": {"file": path.name, "line": line_of(src, m.start())},
                })
    by_type: dict[str, int] = {}
    for it in integrations:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
    return {"counts": {"total": len(integrations), "by_type": by_type},
            "integrations": integrations}


# ----------------------------------------------------------------------------
# 07 — APIs USADAS (REST / SOAP / HTTP)
# ----------------------------------------------------------------------------
API_CLIENT_RE = re.compile(
    r"\b(TIdHTTP|TNetHTTPClient|THTTPClient|TRESTClient|TRESTRequest|THTTPRIO|TsgcWebSocket)\b",
    re.I)
URL_RE = re.compile(r"'(https?://[^']+)'", re.I)
HTTP_VERB_RE = re.compile(
    r"\.(Get|Post|Put|Delete|Patch)\s*\(", re.I)


def extract_apis(files: list[tuple[Path, str]]) -> dict[str, Any]:
    apis: list[dict[str, Any]] = []
    aid = 0
    for path, src in files:
        clients = {m.group(1) for m in API_CLIENT_RE.finditer(src)}
        urls = sorted({m.group(1) for m in URL_RE.finditer(src)})
        verbs = sorted({m.group(1).upper() for m in HTTP_VERB_RE.finditer(src)})
        if not clients and not urls:
            continue
        for cli in (clients or {"unknown"}):
            protocol = ("SOAP" if "RIO" in cli.upper()
                        else "REST" if "REST" in cli.upper() else "HTTP")
            aid += 1
            apis.append({
                "id": f"API-{aid:04d}", "client_class": cli, "protocol": protocol,
                "endpoints": urls[:20], "methods": verbs,
                "used_in": path.name,
                "source_ref": {"file": path.name},
            })
    return {"counts": {"total": len(apis)}, "apis": apis}


# ----------------------------------------------------------------------------
# 08 — LEVANTAMENTO GERAL
# ----------------------------------------------------------------------------
def extract_overview(pas_files, dfm_files, results: dict[str, Any]) -> dict[str, Any]:
    loc = {"pas": 0, "dfm": 0}
    for _, src in pas_files:
        loc["pas"] += src.count("\n") + 1
    for _, src in dfm_files:
        loc["dfm"] += src.count("\n") + 1

    classes = 0
    for _, src in pas_files:
        classes += len(re.findall(r"=\s*class\b", strip_comments(src), re.I))

    procs = results["05_procedures"]["counts"]
    return {
        "totals": {
            "files": len(pas_files) + len(dfm_files),
            "units_pas": len(pas_files),
            "forms_dfm": len(dfm_files),
            "loc_total": loc["pas"] + loc["dfm"],
            "loc_by_type": loc,
            "classes": classes,
            "procedures": procs["code_procedures"],
            "stored_procedures": procs["stored_procedures"],
            "forms_screens": results["02_form_business_rules"]["counts"]["forms"],
            "input_fields": results["02_form_business_rules"]["counts"]["fields"],
            "db_tables": results["04_database_schemas"]["counts"]["tables_ddl"],
            "business_rules": results["01_business_rules"]["counts"]["total"],
            "integrations": results["06_integrations"]["counts"]["total"],
            "apis": results["07_apis"]["counts"]["total"],
            "sql_functions": 0,
        },
        "largest_units": sorted(
            [{"file": p.name, "loc": s.count("\n") + 1} for p, s in pas_files],
            key=lambda x: -x["loc"])[:10],
        "migration_hints": {
            "high_coupling_forms": [f["form_name"]
                                    for f in results["02_form_business_rules"]["forms"]
                                    if f["field_count"] >= 10],
            "external_surface": results["06_integrations"]["counts"]["by_type"],
        },
    }


# ----------------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------------
def analyze(source_root: str, out_dir: str) -> dict[str, str]:
    root = Path(source_root)
    pas = [(p, read_text(p)) for p in sorted(root.rglob("*.pas"))]
    dfm = [(p, read_text(p)) for p in sorted(root.rglob("*.dfm"))]
    sql = [(p, read_text(p)) for p in sorted(root.rglob("*.sql"))]
    all_files = pas + dfm + sql

    results: dict[str, Any] = {}
    results["01_business_rules"] = extract_business_rules(pas)
    results["02_form_business_rules"] = extract_form_rules(dfm)
    results["03_database_rules"] = extract_db_rules(all_files)
    results["04_database_schemas"] = extract_db_schemas(all_files)
    results["05_procedures"] = extract_procedures(pas)
    results["06_integrations"] = extract_integrations(all_files)
    results["07_apis"] = extract_apis(all_files)
    results["08_code_overview"] = extract_overview(pas, dfm, results)

    run_id = new_run_id()
    os.makedirs(out_dir, exist_ok=True)
    written: dict[str, str] = {}
    for artifact, payload in results.items():
        doc = envelope(artifact, payload, source_root, run_id)
        fp = os.path.join(out_dir, f"{artifact}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        written[artifact] = fp
    return written


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Extrator Delphi AST -> 8 artefatos JSON")
    ap.add_argument("source_root", help="raiz do código Delphi (.pas/.dfm)")
    ap.add_argument("-o", "--out", default="./extraction", help="pasta de saída")
    a = ap.parse_args()
    files = analyze(a.source_root, a.out)
    print(f"Gerados {len(files)} artefatos em {a.out}:")
    for name, fp in files.items():
        print(f"  - {ARTIFACTS[name]:<55} {os.path.basename(fp)}")
