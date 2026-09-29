"""
delphi_ast_analyzer.py — Extrator de levantamento Delphi (v0.2, AST real).

Consome a IR normalizada do DelphiAST real (via ast_bridge) quando o binário
ava_ast_cli está disponível; FALLBACK REGEX por arquivo quando não. Gera os 8 artefatos.

Caminho por artefato:
  01 business_rules      regex statement-level (adequado) sobre todo .pas
  02 form_business_rules regex sobre .dfm         (DelphiAST não parseia .dfm)
  03 database_rules      IR (SQL literais + transações)          | fallback regex
  04 database_schemas    IR (CREATE TABLE + componentes DB)       | fallback regex
  05 procedures          IR (só implementações -> SEM duplicação) | fallback regex
  06 integrations        IR (uses + componentes + literais .dll)  | fallback regex
  07 apis                IR (componentes HTTP + URLs literais)     | fallback regex
  08 code_overview       IR (contagens + complexidade reais)      | fallback regex
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from schemas import envelope, new_run_id, ARTIFACTS
import ast_bridge
import regex_extractors as rgx


# ---------------------------------------------------------------------------
# Extratores IR (recebem lista de IRs; itens sem ID)
# ---------------------------------------------------------------------------
def procs_from_ir(irs):
    code_procs, stored = [], {}
    for ir in irs:
        for m in ir["methods"]:
            if not m["is_implementation"]:
                continue  # descarta declarações -> elimina duplicação decl/impl
            code_procs.append({
                "unit": ir["unit"], "class": m["class"], "name": m["name"],
                "kind": m["kind"],
                "params": [f'{p["name"]}: {p["type"]}' if p["type"] else p["name"]
                           for p in m["params"]],
                "returns": m["returns"], "loc": m["loc"], "calls": m["calls"][:20],
                "source_ref": {"file": ir["file"], "line": m["begin_line"]},
            })
        for lit in ir["string_literals"]:
            sm = re.match(r"(?:exec(?:ute)?\s+(?:procedure\s+)?)([A-Za-z_]\w+)",
                          lit["value"], re.I)
            if sm:
                stored.setdefault(sm.group(1).lower(),
                                  {"name": sm.group(1), "called_from": []})
                stored[sm.group(1).lower()]["called_from"].append(
                    {"file": ir["file"], "line": lit["line"]})
    return code_procs, list(stored.values())


def db_rules_from_ir(irs):
    rules = []
    for ir in irs:
        for s in ir["sql_statements"]:
            if s["op"] in ("insert", "update", "delete"):
                rules.append({"type": "write_operation", "operation": s["op"],
                              "tables": s["tables"],
                              "source_ref": {"file": ir["file"], "line": s["line"]}})
        for c in ir["calls"]:
            if re.search(r"\b(StartTransaction|Commit|Rollback)\b", c, re.I):
                rules.append({"type": "transaction", "operation": c.split(".")[-1],
                              "source_ref": {"file": ir["file"]}})
    return rules


def _sql_columns(sql: str) -> list[str]:
    """Infere colunas de um SQL: SELECT list, WHERE, INSERT (col list) e UPDATE SET."""
    cols = set()
    sel = re.search(r"select\s+(.+?)\s+from\b", sql, re.I | re.S)
    if sel and "*" not in sel.group(1):
        for c in sel.group(1).split(","):
            name = re.sub(r"\s+as\s+\w+", "", c.strip(), flags=re.I).split(".")[-1]
            if re.fullmatch(r"[A-Za-z_]\w*", name):
                cols.add(name)
    # INSERT INTO t (c1, c2, ...) VALUES (...)
    ins = re.search(r"insert\s+into\s+\w+\s*\(([^)]+)\)", sql, re.I | re.S)
    if ins:
        for c in ins.group(1).split(","):
            name = c.strip().strip('"[]`')
            if re.fullmatch(r"[A-Za-z_]\w*", name):
                cols.add(name)
    # UPDATE t SET c1 = .., c2 = ..
    upd = re.search(r"update\s+\w+\s+set\s+(.+?)(?:\bwhere\b|$)", sql, re.I | re.S)
    if upd:
        for c in re.findall(r"([A-Za-z_]\w*)\s*=", upd.group(1)):
            cols.add(c)
    for c in re.findall(r"\b([A-Za-z_]\w*)\s*(?:<=|>=|<>|=|<|>|\blike\b|\bin\b)",
                        sql, re.I):
        if c.lower() not in ("and", "or", "where", "select", "from", "order", "by", "set"):
            cols.add(c)
    return sorted(cols)


def db_schemas_from_ir(irs):
    tables, datasets, inferred = {}, [], {}
    for ir in irs:
        for lit in ir["string_literals"]:
            m = re.search(r"create\s+table\s+([A-Za-z_]\w*)\s*\((.*)\)",
                          lit["value"], re.I | re.S)
            if m:
                tables[m.group(1).lower()] = {
                    "name": m.group(1), "origin": "ddl",
                    "columns": rgx._parse_ddl_columns(m.group(2)),
                    "source": {"file": ir["file"], "line": lit["line"]}}
        # tabelas/colunas inferidas de TODO SQL (inclui SELECT) — intel de acesso real
        for s in ir["sql_statements"]:
            for t in s["tables"]:
                entry = inferred.setdefault(t, {"name": t, "origin": "inferred_from_sql",
                                                "accessed_columns": set(),
                                                "operations": set(), "used_in": set()})
                entry["operations"].add(s["op"])
                entry["used_in"].add(ir["file"])
                entry["accessed_columns"].update(_sql_columns(s["sql"]))
        if ir["db_components"]:
            datasets.append({"unit": ir["unit"], "components": ir["db_components"]})
    # serializa sets; não duplica tabela que já tem DDL
    inferred_list = []
    for t, e in inferred.items():
        if t in tables:
            continue
        inferred_list.append({**e, "accessed_columns": sorted(e["accessed_columns"]),
                              "operations": sorted(e["operations"]),
                              "used_in": sorted(e["used_in"])})
    return list(tables.values()), datasets, inferred_list


def integrations_from_ir(irs):
    out = []
    for ir in irs:
        for u in ir["uses"]:
            if re.search(r"IdSMTP|IdMessage|ACBrMail", u, re.I):
                out.append({"type": "email", "target": u, "via": "ACBr" if "ACBr" in u else "Indy",
                            "source_ref": {"file": ir["file"]}})
            elif re.search(r"ACBrBoleto|ACBrBanco|ACBrTitulo|ACBrBol", u, re.I):
                out.append({"type": "banking_boleto", "target": u, "via": "ACBr",
                            "source_ref": {"file": ir["file"]}})
            elif re.search(r"ACBrNFe|ACBrNFCe|ACBrSAT|ACBreSocial|ACBrReinf", u, re.I):
                out.append({"type": "fiscal", "target": u, "via": "ACBr",
                            "source_ref": {"file": ir["file"]}})
            elif re.search(r"IdTCP|ScktComp|IdUDP", u, re.I):
                out.append({"type": "socket", "target": u, "source_ref": {"file": ir["file"]}})
            elif re.search(r"ComObj", u, re.I):
                out.append({"type": "com", "target": u, "source_ref": {"file": ir["file"]}})
        for c in ir["calls"]:
            if re.search(r"CreateOleObject", c, re.I):
                out.append({"type": "com", "target": c, "source_ref": {"file": ir["file"]}})
        for lit in ir["string_literals"]:
            if lit["value"].lower().endswith(".dll"):
                out.append({"type": "dll", "target": lit["value"],
                            "source_ref": {"file": ir["file"], "line": lit["line"]}})
    # dedup por (type, target) mantendo primeira ocorrência
    seen, uniq = set(), []
    for it in out:
        key = (it["type"], it["target"])
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq


def apis_from_ir(irs):
    out = []
    for ir in irs:
        urls = sorted({l["value"] for l in ir["string_literals"]
                       if l["value"].lower().startswith(("http://", "https://"))})
        if not ir["http_components"] and not urls:
            continue
        for cli in (ir["http_components"] or ["unknown"]):
            protocol = ("SOAP" if "RIO" in cli.upper()
                        else "REST" if "REST" in cli.upper() else "HTTP")
            out.append({"client_class": cli, "protocol": protocol,
                        "endpoints": urls[:20], "used_in": ir["file"],
                        "source_ref": {"file": ir["file"]}})
    return out


def overview_from_ir(irs, dfm_forms):
    impl = [m for ir in irs for m in ir["methods"] if m["is_implementation"]]
    procs = [m for m in impl if m["kind"] in ("procedure", "constructor", "destructor")]
    funcs = [m for m in impl if m["kind"] == "function"]
    classes = [{**c, "file": ir["file"]} for ir in irs for c in ir["classes"]]
    return {
        "totals": {
            "units_parsed_ast": len(irs),
            "loc_total": sum(ir["control_flow"].get("_loc", 0) for ir in irs),
            "classes": len(classes),
            "procedures": len(procs),
            "functions": len(funcs),
            "forms_screens": dfm_forms.get("forms", 0),
            "input_fields": dfm_forms.get("fields", 0),
            "avg_cyclomatic": round(sum(ir["cyclomatic"] for ir in irs) / len(irs), 1)
            if irs else 0,
        },
        "classes": classes,
        "complexity_by_unit": sorted(
            [{"unit": ir["unit"], "cyclomatic": ir["cyclomatic"],
              "methods": len([m for m in ir["methods"] if m["is_implementation"]])}
             for ir in irs], key=lambda x: -x["cyclomatic"])[:15],
    }


def business_rules_from_ir(irs):
    rules = []
    for ir in irs:
        rules.extend(ir.get("business_rules", []))
    return rules


def _assign_ids(items, prefix):
    for i, it in enumerate(items, 1):
        it["id"] = f"{prefix}-{i:04d}"
    return items


# ---------------------------------------------------------------------------
# Orquestração com dispatch IR | regex por arquivo
# ---------------------------------------------------------------------------
def analyze(source_root, out_dir):
    root = Path(source_root)
    pas_paths = sorted(root.rglob("*.pas"))
    dfm_files = [(p, rgx.read_text(p)) for p in sorted(root.rglob("*.dfm"))]

    total = len(pas_paths)
    print(f"   lendo {total} arquivo(s) .pas...")
    t_scan0 = time.perf_counter()
    last_print = 0.0
    live = sys.stdout.isatty()  # terminal interativo -> sobrescreve a linha;
                                # saída capturada/redirecionada -> uma linha por update

    irs, regex_pas, ir_pas = [], [], []
    sql_files = [(p, rgx.read_text(p)) for p in sorted(root.rglob("*.sql"))]
    for i, p in enumerate(pas_paths, 1):
        ir = ast_bridge.build_ir(p)
        if ir is not None:
            src = rgx.read_text(p)
            ir["control_flow"]["_loc"] = src.count("\n") + 1
            irs.append(ir)
            ir_pas.append((p, src))
        else:
            regex_pas.append((p, rgx.read_text(p)))

        now = time.perf_counter()
        if total and (now - last_print >= 0.5 or i == total):
            elapsed = now - t_scan0
            pct = i / total * 100
            eta = (elapsed / i) * (total - i)
            name = p.name if len(p.name) <= 38 else p.name[:35] + "..."
            line = (f"[{i}/{total}] {pct:5.1f}%  {name:<38}  "
                    f"decorrido {elapsed:6.1f}s  ETA {eta:6.1f}s")
            if live:
                sys.stdout.write(f"\r   {line}   ")
            else:
                sys.stdout.write(f"   {line}\n")
            sys.stdout.flush()
            last_print = now
    if total and live:
        sys.stdout.write("\n")
        sys.stdout.flush()
    print(f"   leitura concluída em {time.perf_counter() - t_scan0:.1f}s "
          f"({len(irs)} via AST, {len(regex_pas)} via regex)")

    ast_mode = "ast+regex-fallback" if irs else "regex-only"
    R = {}

    # 01 business rules — IR (IF/ASSIGN/CASE por método) + fallback regex
    br = business_rules_from_ir(irs)
    if regex_pas:
        br += rgx.extract_business_rules(regex_pas)["rules"]
    br = _assign_ids(br, "BR")
    by_type = {}
    for r in br:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    R["01_business_rules"] = {"counts": {"total": len(br), "by_type": by_type,
                                         "mode": ast_mode}, "rules": br}

    # 02 form rules — .dfm
    form_res = rgx.extract_form_rules(dfm_files)
    R["02_form_business_rules"] = form_res

    # 03 database rules — IR + fallback
    db_rules = db_rules_from_ir(irs) + (rgx.extract_db_rules(regex_pas)["rules"]
                                        if regex_pas else [])
    db_rules = _assign_ids(db_rules, "DBR")
    R["03_database_rules"] = {"counts": {"total": len(db_rules), "mode": ast_mode},
                              "rules": db_rules}

    # 04 database schemas — IR + fallback
    tables, datasets, inferred = db_schemas_from_ir(irs)
    fb_schema = rgx.extract_db_schemas(regex_pas + dfm_files + sql_files)
    tables += fb_schema["tables"]
    R["04_database_schemas"] = {
        "counts": {"tables_ddl": len(tables), "tables_inferred": len(inferred),
                   "datasets": len(datasets),
                   "relationships": len(fb_schema.get("relationships", [])),
                   "mode": ast_mode},
        "tables": tables, "inferred_tables": inferred,
        "relationships": fb_schema.get("relationships", []),
        "db_component_datasets": datasets,
        "dataset_fields": fb_schema["dataset_fields"]}

    # 05 procedures — IR (só implementações) + fallback
    code_procs, stored = procs_from_ir(irs)
    if regex_pas:
        fb = rgx.extract_procedures(regex_pas)
        code_procs += fb["code_procedures"]
        stored += fb["stored_procedures"]
    R["05_procedures"] = {
        "counts": {"code_procedures": len(code_procs),
                   "stored_procedures": len(stored), "mode": ast_mode},
        "code_procedures": code_procs, "stored_procedures": stored}

    # 06 integrations — IR + fallback
    integ = integrations_from_ir(irs)
    if regex_pas:
        integ += rgx.extract_integrations(regex_pas)["integrations"]
    integ = _assign_ids(integ, "INT")
    by_type = {}
    for it in integ:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
    R["06_integrations"] = {"counts": {"total": len(integ), "by_type": by_type,
                                       "mode": ast_mode}, "integrations": integ}

    # 07 apis — IR + fallback
    apis = apis_from_ir(irs)
    if regex_pas:
        apis += rgx.extract_apis(regex_pas)["apis"]
    apis = _assign_ids(apis, "API")
    api_counts = {"total": len(apis), "mode": ast_mode}
    if not apis:
        api_counts["note"] = ("nenhum cliente HTTP detectado (esperado em app "
                               "desktop ADO/local sem integração REST/SOAP)")
    R["07_apis"] = {"counts": api_counts, "apis": apis}

    # 08 overview — IR counts (exatos) + fallback regex (aproximado) p/ unidades sem AST
    ov = overview_from_ir(irs, form_res["counts"])
    if regex_pas:
        fb_ov = rgx.overview_fallback(regex_pas)
        ov["totals"]["classes"] += fb_ov["classes"]
        ov["totals"]["loc_total"] += fb_ov["loc_total"]
        ov["classes"] += fb_ov["class_list"]
        ov["totals"]["procedures"] += sum(1 for p in fb["code_procedures"]
                                          if p["kind"] != "function")
        ov["totals"]["functions"] += sum(1 for p in fb["code_procedures"]
                                         if p["kind"] == "function")
    ov["totals"]["units_total"] = len(irs) + len(regex_pas)
    ov["totals"].update({
        "business_rules": R["01_business_rules"]["counts"]["total"],
        "integrations": len(integ), "apis": len(apis),
        "db_tables": len(tables) + len(inferred),
        "mode": ast_mode,
    })
    R["08_code_overview"] = ov

    # 09 cobertura de testes — nome de arquivo (todos) + IR (uses/fixture/published/
    # atributo) + fallback regex + artefatos auxiliares (nunca são código Delphi)
    filename_hits = {p.name for p in pas_paths if rgx.is_test_filename(p)}

    ast_findings = []
    for ir in irs:
        for c in ir.get("classes", []):
            if (c.get("parent") or "").lower() in ast_bridge.TEST_FIXTURE_BASE_CLASSES \
               or any(a.lower() == "testfixture" for a in c.get("attributes", [])):
                ast_findings.append({"kind": "fixture_class", "name": c["name"], "detected_via": "ast",
                                     "source_ref": {"file": ir["file"], "line": c["line"]}})
        for m in ir.get("methods", []):
            if m.get("visibility") == "published" and m["name"].lower().startswith("test"):
                ast_findings.append({"kind": "published_test_method", "name": m["name"],
                                     "detected_via": "ast",
                                     "source_ref": {"file": ir["file"], "line": m["begin_line"]}})
            for attr in m.get("attributes", []):
                if attr.lower() in {"test", "testcase"}:
                    ast_findings.append({"kind": "attribute", "name": f"[{attr}] {m['name']}",
                                         "detected_via": "ast",
                                         "source_ref": {"file": ir["file"], "line": m["begin_line"]}})
        for tu in ir.get("test_uses", []):
            ast_findings.append({"kind": "framework_uses", "name": tu["name"], "detected_via": "ast",
                                 "source_ref": {"file": ir["file"], "line": tu["line"]}})

    regex_findings = rgx.extract_test_coverage(regex_pas)["test_findings"] if regex_pas else []
    test_findings = ast_findings + regex_findings
    test_findings += [{"kind": "filename_pattern", "name": f, "detected_via": "filename",
                       "source_ref": {"file": f, "line": None}} for f in sorted(filename_hits)]

    aux = rgx.scan_test_indicators(root)

    test_unit_files = {f["source_ref"]["file"] for f in test_findings}
    # "TestFixture" é sempre atributo de CLASSE (nunca de método) — excluir do
    # dedup de test_methods; no fallback regex ele entra como "attribute" genérico
    # por não haver associação posicional ao alvo (só o AST resolve isso).
    test_method_keys = {(f["source_ref"]["file"], f["name"]) for f in test_findings
                        if f["kind"] == "published_test_method"
                        or (f["kind"] == "attribute" and "testfixture" not in f["name"].lower())}
    R["09_test_coverage"] = {
        "counts": {
            "test_units": len(test_unit_files),
            "test_methods": len(test_method_keys),
            "test_fixtures": sum(1 for f in test_findings if f["kind"] == "fixture_class"),
            "manual_test_docs": aux["counts"]["manual_doc"],
            "runner_configs": aux["counts"]["runner_config"],
            "ci_test_stages": aux["counts"]["ci_test_stage"],
            "test_data_files": aux["counts"]["test_data"],
            "mode": ast_mode,
        },
        "test_findings": _assign_ids(test_findings, "TST"),
        "auxiliary_indicators": _assign_ids(aux["items"], "TSTX"),
    }

    run_id = new_run_id()
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    for artifact, payload in R.items():
        doc = envelope(artifact, payload, source_root, run_id)
        fp = os.path.join(out_dir, f"{artifact}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        written[artifact] = fp
    return written


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Extrator Delphi AST -> 8 artefatos JSON")
    ap.add_argument("source_root")
    ap.add_argument("-o", "--out", default="./extraction")
    a = ap.parse_args()
    files = analyze(a.source_root, a.out)
    print(f"Gerados {len(files)} artefatos "
          f"(AST real: {'sim' if ast_bridge.is_available() else 'nao (regex)'})")
    for name, fp in files.items():
        print(f"  - {ARTIFACTS[name]:<55} {os.path.basename(fp)}")
