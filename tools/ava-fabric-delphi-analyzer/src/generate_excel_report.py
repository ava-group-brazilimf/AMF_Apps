"""
generate_excel_report.py — Gera um dashboard Excel a partir dos JSONs de
EXTRAÇÃO (não os comprimidos — esses podem estar fatorados via `__headroom__`).

3 abas:
  - Estrutura       -> top unidades por complexidade ciclomática (08_code_overview)
  - Regras_Negocio  -> uma regra de negócio por linha (01_business_rules)
  - Dashboard       -> KPIs + gráficos (08_code_overview + by_type de 01/06/07)

Uso:
    python src/generate_excel_report.py <extraction_dir> -o <out.xlsx>
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

import xlsxwriter

# ---------------------------------------------------------------------------
# Paleta (dataviz skill - references/palette.md), fixa e validada.
# ---------------------------------------------------------------------------
CAT_BLUE = "#2a78d6"
CAT_AQUA = "#1baf7a"
CAT_YELLOW = "#eda100"
CAT_GREEN = "#008300"
CAT_VIOLET = "#4a3aa7"
CAT_RED = "#e34948"
CAT_MAGENTA = "#e87ba4"
CAT_ORANGE = "#eb6834"
CAT_ORDER = [CAT_BLUE, CAT_AQUA, CAT_YELLOW, CAT_GREEN, CAT_VIOLET, CAT_RED,
             CAT_MAGENTA, CAT_ORANGE]

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"

# tipos reais produzidos por src/ast_bridge.py::_method_rules() e
# src/regex_extractors.py::extract_business_rules() (ver A1 desta sessão)
TYPE_COLOR = {
    "validation": CAT_AQUA,
    "calculation": CAT_GREEN,
    "state_classification": CAT_VIOLET,
    "threshold_condition": CAT_YELLOW,
}
TYPE_LABEL = {
    "validation": "Validação",
    "calculation": "Cálculo",
    "state_classification": "Classificação de Estado",
    "threshold_condition": "Condição de Limite (Threshold)",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def truncate(text: Any, limit: int = 300) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "..."


def _type_color(t: str, seen: dict) -> str:
    if t in TYPE_COLOR:
        return TYPE_COLOR[t]
    if t not in seen:
        seen[t] = CAT_ORDER[len(seen) % len(CAT_ORDER)]
    return seen[t]


def _rule_detail(rule: dict) -> str:
    common = {"id", "unit", "type", "method", "source_ref", "fields"}
    extra = {k: v for k, v in rule.items() if k not in common and v not in (None, "", [])}
    return "; ".join(f"{k}={v}" for k, v in extra.items())


def build_workbook(extraction_dir: Path, out_path: Path) -> None:
    overview = load_json(extraction_dir / "08_code_overview.json")["payload"]
    business = load_json(extraction_dir / "01_business_rules.json")["payload"]
    integrations = load_json(extraction_dir / "06_integrations.json")["payload"]
    apis = load_json(extraction_dir / "07_apis.json")["payload"]

    totals = overview["totals"]
    complexity_by_unit = overview.get("complexity_by_unit", [])
    rules = business.get("rules", [])

    wb = xlsxwriter.Workbook(str(out_path))

    fmt_header = wb.add_format({"bold": True, "bg_color": CAT_BLUE, "font_color": "#ffffff",
                                 "border": 1, "border_color": GRID, "align": "left",
                                 "valign": "vcenter"})
    fmt_cell = wb.add_format({"border": 1, "border_color": GRID, "valign": "top",
                              "font_color": INK_PRIMARY})
    fmt_cell_wrap = wb.add_format({"border": 1, "border_color": GRID, "valign": "top",
                                   "text_wrap": True, "font_color": INK_PRIMARY})
    fmt_num = wb.add_format({"border": 1, "border_color": GRID, "num_format": "#,##0",
                             "font_color": INK_PRIMARY})

    # ------------------------------------------------------------------ #
    # Aba 1: Estrutura (top unidades por complexidade ciclomática)
    # ------------------------------------------------------------------ #
    ws1 = wb.add_worksheet("Estrutura")
    headers1 = ["Unit", "Complexidade Ciclomática", "Métodos Implementados"]
    for c, h in enumerate(headers1):
        ws1.write(0, c, h, fmt_header)
    for r, u in enumerate(complexity_by_unit, start=1):
        ws1.write(r, 0, u.get("unit", ""), fmt_cell)
        ws1.write_number(r, 1, u.get("cyclomatic", 0), fmt_num)
        ws1.write_number(r, 2, u.get("methods", 0), fmt_num)
    n1 = len(complexity_by_unit)
    ws1.autofilter(0, 0, max(n1, 1), len(headers1) - 1)
    ws1.freeze_panes(1, 1)
    for c, w in enumerate([32, 24, 20]):
        ws1.set_column(c, c, w)

    # ------------------------------------------------------------------ #
    # Aba 2: Regras_Negocio
    # ------------------------------------------------------------------ #
    ws2 = wb.add_worksheet("Regras_Negocio")
    headers2 = ["ID", "Tipo", "Unit", "Método", "Detalhe", "Arquivo", "Linha"]
    for c, h in enumerate(headers2):
        ws2.write(0, c, h, fmt_header)
    for r, rule in enumerate(rules, start=1):
        rtype = rule.get("type", "")
        src_ref = rule.get("source_ref", {})
        ws2.write(r, 0, rule.get("id", ""), fmt_cell)
        ws2.write(r, 1, TYPE_LABEL.get(rtype, rtype), fmt_cell)
        ws2.write(r, 2, rule.get("unit", ""), fmt_cell)
        ws2.write(r, 3, rule.get("method", ""), fmt_cell)
        ws2.write(r, 4, truncate(_rule_detail(rule), 300), fmt_cell_wrap)
        ws2.write(r, 5, src_ref.get("file", ""), fmt_cell)
        ws2.write_number(r, 6, src_ref.get("line", 0) or 0, fmt_num)
    n2 = len(rules)
    ws2.autofilter(0, 0, max(n2, 1), len(headers2) - 1)
    ws2.freeze_panes(1, 1)
    for c, w in enumerate([12, 26, 26, 30, 50, 40, 9]):
        ws2.set_column(c, c, w)
    for rtype, color in TYPE_COLOR.items():
        label = TYPE_LABEL[rtype]
        fmt_t = wb.add_format({"bg_color": color, "font_color": "#ffffff", "border": 1,
                               "border_color": GRID})
        ws2.conditional_format(1, 1, max(n2, 1), 1,
                              {"type": "text", "criteria": "containing",
                               "value": label, "format": fmt_t})

    # ------------------------------------------------------------------ #
    # Aba 3: Dashboard
    # ------------------------------------------------------------------ #
    ws3 = wb.add_worksheet("Dashboard")
    ws3.hide_gridlines(2)
    ws3.set_column(0, 0, 2)
    ws3.set_column(1, 1, 34)
    for c in range(2, 14):
        ws3.set_column(c, c, 13)

    fmt_title = wb.add_format({"bold": True, "font_size": 16, "font_color": INK_PRIMARY})
    fmt_subtitle = wb.add_format({"font_size": 10, "font_color": INK_SECONDARY})
    fmt_section = wb.add_format({"bold": True, "font_size": 12, "font_color": "#ffffff",
                                 "bg_color": CAT_BLUE, "indent": 1})
    fmt_kpi_label = wb.add_format({"font_size": 9, "font_color": INK_MUTED})
    fmt_kpi_value = wb.add_format({"bold": True, "font_size": 20, "font_color": INK_PRIMARY})
    fmt_tbl_head = wb.add_format({"bold": True, "border": 1, "border_color": GRID,
                                  "bg_color": "#f0efec", "font_color": INK_PRIMARY})
    fmt_tbl_cell = wb.add_format({"border": 1, "border_color": GRID, "font_color": INK_PRIMARY})
    fmt_tbl_num = wb.add_format({"border": 1, "border_color": GRID, "num_format": "#,##0",
                                 "font_color": INK_PRIMARY})

    row = 0
    ws3.merge_range(row, 1, row, 8, "Dashboard - AVA Fabric Delphi Analyzer", fmt_title)
    row += 1
    ws3.merge_range(row, 1, row, 8,
                    f"modo: {totals.get('mode', '-')}   |   "
                    f"unidades: {totals.get('units_total', 0)}", fmt_subtitle)
    row += 2

    kpis = [
        ("Unidades Analisadas", totals.get("units_total", 0)),
        ("Total LOC", totals.get("loc_total", 0)),
        ("Procedures", totals.get("procedures", 0)),
        ("Functions", totals.get("functions", 0)),
        ("Classes", totals.get("classes", 0)),
        ("Complexidade Média", totals.get("avg_cyclomatic", 0)),
        ("Forms/Telas", totals.get("forms_screens", 0)),
        ("Campos de Entrada", totals.get("input_fields", 0)),
        ("Regras de Negócio", totals.get("business_rules", 0)),
        ("Integrações", totals.get("integrations", 0)),
        ("APIs", totals.get("apis", 0)),
        ("Tabelas de BD", totals.get("db_tables", 0)),
    ]
    kpi_col = 1
    kpi_row0 = row
    for i, (label, value) in enumerate(kpis):
        c = kpi_col + (i % 4) * 2
        r = kpi_row0 + (i // 4) * 3
        ws3.merge_range(r, c, r, c + 1, label, fmt_kpi_label)
        ws3.merge_range(r + 1, c, r + 1, c + 1, value, fmt_kpi_value)
    row = kpi_row0 + ((len(kpis) - 1) // 4 + 1) * 3 + 1

    # --- Regras por Tipo --------------------------------------------
    ws3.merge_range(row, 1, row, 8, "Regras de Negócio por Tipo", fmt_section)
    row += 1
    by_type = business["counts"].get("by_type", {})
    type_tbl_row0 = row
    ws3.write_row(row, 1, ["Tipo", "Qtd"], fmt_tbl_head)
    row += 1
    type_items = sorted(by_type.items(), key=lambda kv: -kv[1])
    for rtype, qty in type_items:
        ws3.write(row, 1, TYPE_LABEL.get(rtype, rtype), fmt_tbl_cell)
        ws3.write_number(row, 2, qty, fmt_tbl_num)
        row += 1
    type_tbl_last = row - 1

    if type_items:
        chart_type = wb.add_chart({"type": "bar"})
        chart_type.add_series({
            "name": "Qtd de regras",
            "categories": ["Dashboard", type_tbl_row0 + 1, 1, type_tbl_last, 1],
            "values": ["Dashboard", type_tbl_row0 + 1, 2, type_tbl_last, 2],
            "points": [{"fill": {"color": _type_color(t, {})}} for t, _ in type_items],
            "data_labels": {"value": True},
        })
        chart_type.set_title({"name": "Regras de Negócio por Tipo"})
        chart_type.set_legend({"none": True})
        chart_type.set_x_axis({"line": {"color": GRID}})
        chart_type.set_y_axis({"line": {"color": GRID}})
        chart_type.set_size({"width": 480, "height": 300})
        ws3.insert_chart(type_tbl_row0, 5, chart_type)

    row += 1

    # --- Integrações por Tipo ------------------------------------------
    ws3.merge_range(row, 1, row, 8, "Integrações por Tipo", fmt_section)
    row += 1
    integ_by_type = integrations["counts"].get("by_type", {})
    integ_tbl_row0 = row
    ws3.write_row(row, 1, ["Tipo", "Qtd"], fmt_tbl_head)
    row += 1
    integ_items = sorted(integ_by_type.items(), key=lambda kv: -kv[1])
    for itype, qty in integ_items:
        ws3.write(row, 1, itype, fmt_tbl_cell)
        ws3.write_number(row, 2, qty, fmt_tbl_num)
        row += 1
    integ_tbl_last = row - 1

    if integ_items:
        chart_integ = wb.add_chart({"type": "column"})
        chart_integ.add_series({
            "name": "Qtd",
            "categories": ["Dashboard", integ_tbl_row0 + 1, 1, integ_tbl_last, 1],
            "values": ["Dashboard", integ_tbl_row0 + 1, 2, integ_tbl_last, 2],
            "points": [{"fill": {"color": _type_color(t, {})}} for t, _ in integ_items],
            "data_labels": {"value": True},
        })
        chart_integ.set_title({"name": "Integrações por Tipo"})
        chart_integ.set_legend({"none": True})
        chart_integ.set_x_axis({"line": {"color": GRID}})
        chart_integ.set_y_axis({"line": {"color": GRID}})
        chart_integ.set_size({"width": 420, "height": 300})
        ws3.insert_chart(integ_tbl_row0, 5, chart_integ)

    row += 1

    # --- Top units por complexidade -------------------------------------
    ws3.merge_range(row, 1, row, 8, "Top Unidades por Complexidade Ciclomática", fmt_section)
    row += 1
    top_tbl_row0 = row
    ws3.write_row(row, 1, ["Unit", "Complexidade"], fmt_tbl_head)
    row += 1
    for u in complexity_by_unit:
        ws3.write(row, 1, u.get("unit", ""), fmt_tbl_cell)
        ws3.write_number(row, 2, u.get("cyclomatic", 0), fmt_tbl_num)
        row += 1
    top_tbl_last = row - 1 if complexity_by_unit else row

    if complexity_by_unit:
        chart_top = wb.add_chart({"type": "bar"})
        chart_top.add_series({
            "name": "Complexidade",
            "categories": ["Dashboard", top_tbl_row0 + 1, 1, top_tbl_last, 1],
            "values": ["Dashboard", top_tbl_row0 + 1, 2, top_tbl_last, 2],
            "fill": {"color": CAT_BLUE},
            "data_labels": {"value": True},
        })
        chart_top.set_title({"name": "Top Unidades por Complexidade"})
        chart_top.set_legend({"none": True})
        chart_top.set_x_axis({"line": {"color": GRID}})
        chart_top.set_y_axis({"line": {"color": GRID}, "reverse": True})
        chart_top.set_size({"width": 520, "height": 380})
        ws3.insert_chart(top_tbl_row0, 5, chart_top)

    wb.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera dashboard Excel a partir dos artefatos de extração")
    ap.add_argument("extraction_dir", help="pasta com os 8 JSONs de extração (não comprimidos)")
    ap.add_argument("-o", "--out", default="./report.xlsx")
    a = ap.parse_args()

    extraction_dir = Path(a.extraction_dir)
    out_path = Path(a.out)
    build_workbook(extraction_dir, out_path)
    print(f"[ok] {out_path}")


if __name__ == "__main__":
    main()
