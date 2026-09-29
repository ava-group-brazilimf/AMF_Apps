#!/usr/bin/env python3
"""
AVA Fabric – Business Rules Catalog Generator (deterministic)
=============================================================
Enumera **100%** das regras de negócio detectadas pela extração AST em um único
artefato lossless — ``business-rules-catalog.json`` — que se torna a fonte de
verdade canônica das regras para todas as fases downstream (TO-BE, codegen,
test-plan).

Motivação (post-filter)
-----------------------
O agente LLM ``ava-asis-documentation`` (skill RN) não consegue transcrever de
forma confiável milhares de regras discretas para Markdown — ele amostra. A
enumeração exaustiva de dados AST estruturados é uma **transformação
determinística**, não uma tarefa generativa. Este utilitário segue exatamente o
mesmo padrão de ``module_partitioner.py`` / ``sql_ir_generator.py``: roda **após**
a extração AST e pós-processa os JSONs monolíticos em um artefato consumível.

Entradas
--------
* ``compressed/01_business_rules.json`` — ``payload.rules`` (string bucketizada
  por ``type``: calculation / state_classification / threshold_condition /
  validation)
* ``compressed/02_form_business_rules.json`` — ``payload.forms`` (string CSV com
  coluna ``fields`` em JSON, opcionalmente table-compacted)

Saída
-----
* ``docs/business-rules-catalog.json`` — catálogo lossless com **todas** as
  regras, cada uma marcada com ``category`` / ``unit`` / ``domain_relevant``.

Invariante de paridade (falha ruidosa)
--------------------------------------
* ``#regras(01) == payload.counts.total``
* ``#regras_validacao(02) == #campos com has_validation OU event_handlers``
Qualquer divergência → exit code 1 (nada é perdido silenciosamente).

Uso standalone
--------------
    python business_rules_catalog_generator.py --project processaERP-005

Uso integrado (run_delphi_ast_analysis.py)
------------------------------------------
    BusinessRulesCatalogGenerator(project_name).run()
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Heurística de ruído de UI (generic-UI components)
# ---------------------------------------------------------------------------
# Units cujo conteúdo é predominantemente lógica de componente de UI genérico
# (não regra de domínio ERP). As regras NUNCA são descartadas — apenas marcadas
# com ``domain_relevant: false`` para que o downstream possa filtrar o ruído sem
# perda de dados. Pode ser sobrescrito por ``business_rules_ui_units`` no
# project-config.yaml.
_DEFAULT_UI_UNITS: set[str] = {"multiedit"}


def _norm(name: str) -> str:
    """lower-case + strip de extensão ``.pas`` para matching de unit."""
    base = Path(str(name)).name
    if base.lower().endswith(".pas"):
        base = base[:-4]
    return base.strip().lower()


def _parse_factored_block(header_line: str, data_lines: list[str]) -> list[dict[str, Any]]:
    """
    Decodifica um bloco ``[N]{col:type,col:type,...}`` seguido de ``N`` linhas CSV
    (dialeto RFC-4180 — o mesmo que o módulo ``csv`` do Python usa por padrão).

    Colunas declaradas como ``:json`` são desserializadas de JSON. Retorna uma
    lista de dicts ``{coluna: valor}`` (chaves sem o sufixo ``:type``).
    """
    # Extrai o schema de dentro das chaves {...}
    open_brace = header_line.index("{")
    close_brace = header_line.rindex("}")
    schema_raw = header_line[open_brace + 1:close_brace]
    columns: list[str] = []
    json_cols: set[str] = set()
    int_cols: set[str] = set()
    for spec in schema_raw.split(","):
        col, _, typ = spec.partition(":")
        col = col.strip()
        columns.append(col)
        if typ.strip() == "json":
            json_cols.add(col)
        elif typ.strip() == "int":
            int_cols.add(col)

    rows: list[dict[str, Any]] = []
    reader = csv.reader(data_lines)
    for fields in reader:
        if not fields or (len(fields) == 1 and fields[0] == ""):
            continue  # linha em branco (ex: trailing newline)
        record: dict[str, Any] = {}
        for i, col in enumerate(columns):
            val: Any = fields[i] if i < len(fields) else ""
            if col in json_cols:
                try:
                    val = json.loads(val) if val != "" else None
                except (json.JSONDecodeError, TypeError):
                    pass  # mantém string bruta se não for JSON válido
            elif col in int_cols:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            record[col] = val
        rows.append(record)
    return rows


def _decode_buckets(payload_rules: "str | list") -> dict[str, list[dict[str, Any]]]:
    """
    Decodifica ``payload.rules`` de ``01_business_rules.json``.

    Formato legado (compressão CSV):
        __buckets:type
        __key:<type>
        [N]{schema}
        <N linhas CSV>
        __key:<type2>
        ...

    Ou formato nativo (lista de dicionários) produzido por analisadores recentes.

    Retorna ``{type: [record, ...]}``.
    """
    if isinstance(payload_rules, list):
        buckets: dict[str, list[dict[str, Any]]] = {}
        for r in payload_rules:
            if not isinstance(r, dict):
                continue
            typ = r.get("type", "unknown")
            buckets.setdefault(typ, []).append(r)
        return buckets

    if not isinstance(payload_rules, str):
        raise ValueError("payload.rules deve ser str ou list")
    lines = payload_rules.split("\n")
    if not lines or not lines[0].startswith("__buckets:"):
        raise ValueError("payload.rules não inicia com '__buckets:type' — formato inesperado")

    buckets: dict[str, list[dict[str, Any]]] = {}
    i = 1
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("__key:"):
            bucket_type = line[len("__key:"):].strip()
            header = lines[i + 1]  # linha [N]{schema}
            # Coleta as linhas de dados até o próximo __key: ou fim
            j = i + 2
            data: list[str] = []
            while j < n and not lines[j].startswith("__key:"):
                data.append(lines[j])
                j += 1
            buckets[bucket_type] = _parse_factored_block(header, data)
            i = j
        else:
            i += 1
    return buckets


def _decode_forms(payload_forms: Any) -> list[dict[str, Any]]:
    """Decodifica ``payload.forms`` de ``02_form_business_rules.json``.

    Aceita tanto a lista canônica de forms (Java/.NET normalizado) quanto a
    string compactada herdada do analisador Delphi.
    """
    if isinstance(payload_forms, list):
        return [f for f in payload_forms if isinstance(f, dict)]
    if not isinstance(payload_forms, str):
        return []
    lines = payload_forms.split("\n")
    if not lines or not lines[0]:
        return []
    header = lines[0]  # [238]{schema}
    return _parse_factored_block(header, lines[1:])


def _normalize_fields(fields_val: Any) -> list[dict[str, Any]]:
    """
    Normaliza a coluna ``fields`` de um form para uma lista de dicts de campo,
    lidando com o formato lista simples E com o formato table-compacted
    (``{_compaction: table, _schema: [...], _rows: [...]}``).
    """
    if isinstance(fields_val, list):
        return [f for f in fields_val if isinstance(f, dict)]
    if isinstance(fields_val, dict) and fields_val.get("_compaction") == "table":
        schema = [c["name"] for c in fields_val.get("_schema", [])]
        out: list[dict[str, Any]] = []
        for row in fields_val.get("_rows", []):
            record: dict[str, Any] = {}
            for i, col in enumerate(schema):
                record[col] = row[i] if i < len(row) else None
            out.append(record)
        return out
    return []


def _field_event_handlers(field: dict[str, Any]) -> list[str]:
    """
    Extrai os nomes de event handlers não-vazios de um campo, cobrindo tanto o
    formato ``event_handlers: {OnClick: "..."}`` quanto as colunas achatadas
    ``event_handlers.OnClick: "..."`` do formato table-compacted.
    """
    handlers: list[str] = []
    eh = field.get("event_handlers")
    if isinstance(eh, dict):
        for k, v in eh.items():
            if v not in (None, "", {}, []):
                handlers.append(str(k))
    for key, val in field.items():
        if key.startswith("event_handlers.") and val not in (None, "", {}, []):
            handlers.append(key.split(".", 1)[1])
    return handlers


def _flatten_source_ref(record: dict[str, Any]) -> dict[str, Any]:
    """
    Expande um ``source_ref`` aninhado (Java/.NET) para as chaves achatadas
    ``source_ref.*`` que o restante do gerador já espera. Se já estiver achatado,
    retorna o record inalterado.
    """
    record = dict(record)
    src = record.get("source_ref")
    if not isinstance(src, dict):
        return record
    for key, value in src.items():
        flat_key = f"source_ref.{key}"
        if flat_key not in record:
            record[flat_key] = value
    return record


class BusinessRulesCatalogGenerator:
    """
    Gera o catálogo lossless de regras de negócio a partir dos artefatos AST
    compactados.
    """

    def __init__(
        self,
        project_name: str,
        *,
        compressed_dir: Path | None = None,
        docs_dir: Path | None = None,
    ) -> None:
        self.project_name = project_name
        self.config = self._load_config()

        base = Path(f"projects/{project_name}/outputs/asis")
        self.compressed_dir = (
            compressed_dir.resolve() if compressed_dir
            else (base / "delphi-ast-raw" / "compressed").resolve()
        )
        self.docs_dir = docs_dir.resolve() if docs_dir else (base / "docs").resolve()

        ui_units = self.config.get("business_rules_ui_units")
        if isinstance(ui_units, list) and ui_units:
            self.ui_units = {_norm(u) for u in ui_units}
        else:
            self.ui_units = set(_DEFAULT_UI_UNITS)

    # ------------------------------------------------------------------
    def _load_config(self) -> dict[str, Any]:
        cfg_path = Path(f"projects/{self.project_name}/context/project-config.yaml")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Regras de 01_business_rules.json
    # ------------------------------------------------------------------
    def _build_expression(self, rule_type: str, rec: dict[str, Any]) -> str:
        """Redige a expressão da regra em texto, por tipo."""
        if rule_type == "calculation":
            return str(rec.get("expression", "")).strip()
        if rule_type == "threshold_condition":
            return f"{rec.get('variable', '')} {rec.get('operator', '')} {rec.get('threshold', '')}".strip()
        if rule_type == "state_classification":
            states = rec.get("states")
            states_txt = ", ".join(map(str, states)) if isinstance(states, list) else str(states or "")
            return f"{rec.get('variable', '')} ∈ {{{states_txt}}}".strip()
        if rule_type == "validation":
            return str(rec.get("condition", "")).strip()
        # Fallback genérico (analisadores Java/.NET populam o campo expression)
        return str(rec.get("expression", "")).strip()

    def _catalog_from_01(self, path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = data.get("payload", {})
        buckets = _decode_buckets(payload.get("rules", ""))

        rules: list[dict[str, Any]] = []
        by_category: dict[str, int] = {}
        for rule_type, records in buckets.items():
            by_category[rule_type] = len(records)
            for rec in records:
                rec = _flatten_source_ref(rec)
                unit = str(rec.get("unit", ""))
                source_file = rec.get("source_ref.file", "")
                source_line = rec.get("source_ref.line", "")
                ast_id = str(rec.get("id", "")).strip()
                rules.append({
                    "id": ast_id,
                    "ast_ref": ast_id,
                    "origin": "01_business_rules.json",
                    "category": rule_type,
                    "unit": unit,
                    "method": rec.get("method", ""),
                    "target": rec.get("target") or rec.get("variable") or rec.get("action") or "",
                    "expression": self._build_expression(rule_type, rec),
                    "source": f"{source_file}:{source_line}" if source_file else "",
                    "domain_relevant": _norm(unit) not in self.ui_units,
                    "raw": rec,
                })
        return rules, by_category

    # ------------------------------------------------------------------
    # Regras de validação de tela de 02_form_business_rules.json
    # ------------------------------------------------------------------
    def _catalog_from_02(self, path: Path) -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        forms = _decode_forms(data.get("payload", {}).get("forms", ""))

        rules: list[dict[str, Any]] = []
        seq = 0
        for form in forms:
            form_name = form.get("form_name", "")
            form_class = form.get("form_class", "")
            source_file = form.get("source_file", "")
            for field in _normalize_fields(form.get("fields")):
                has_validation = bool(field.get("has_validation"))
                handlers = _field_event_handlers(field)
                if not (has_validation or handlers):
                    continue
                seq += 1
                field_name = field.get("name", "")
                unit = form_class or form_name
                rules.append({
                    "id": f"FBR-{seq:04d}",
                    "ast_ref": None,
                    "origin": "02_form_business_rules.json",
                    "category": "form_validation",
                    "unit": unit,
                    "form": form_name,
                    "form_class": form_class,
                    "field": field_name,
                    "component_class": field.get("component_class", ""),
                    "has_validation": has_validation,
                    "event_handlers": handlers,
                    "expression": self._describe_field_rule(field_name, has_validation, handlers),
                    "source": source_file,
                    "domain_relevant": _norm(unit) not in self.ui_units,
                    "raw": field,
                })
        return rules

    def _describe_field_rule(self, field: str, has_validation: bool, handlers: list[str]) -> str:
        parts: list[str] = []
        if has_validation:
            parts.append(f"campo '{field}' possui validação")
        if handlers:
            parts.append(f"handlers: {', '.join(handlers)}")
        return " — ".join(parts)

    def _count_expected_02(self, path: Path) -> int:
        data = json.loads(path.read_text(encoding="utf-8"))
        forms = _decode_forms(data.get("payload", {}).get("forms", ""))
        expected = 0
        for form in forms:
            for field in _normalize_fields(form.get("fields")):
                if bool(field.get("has_validation")) or _field_event_handlers(field):
                    expected += 1
        return expected

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> int:
        print(f"\n🔧 BusinessRulesCatalogGenerator :: {self.project_name}")
        print(f"   compressed : {self.compressed_dir}")
        print(f"   docs       : {self.docs_dir}")

        path_01 = self.compressed_dir / "01_business_rules.json"
        path_02 = self.compressed_dir / "02_form_business_rules.json"

        rules: list[dict[str, Any]] = []
        by_category: dict[str, int] = {}
        expected_total_01 = 0
        expected_total_02 = 0

        # ── 01 — cálculos / thresholds / classificações / validações ────────
        if path_01.exists():
            data_01 = json.loads(path_01.read_text(encoding="utf-8"))
            payload_counts = data_01.get("payload", {}).get("counts", {}) or {}
            expected_total_01 = (
                int(payload_counts.get("total", 0)) if "total" in payload_counts else None
            )
            r1, by_category = self._catalog_from_01(path_01)
            rules.extend(r1)
            # Se o analisador não informar counts.total (formato legado/parcial),
            # aceita o tamanho real da lista canônica.
            if expected_total_01 is None:
                expected_total_01 = len(r1)
            # PARIDADE 01 — falha ruidosa
            if len(r1) != expected_total_01:
                print(
                    f"   ❌ PARIDADE 01 falhou: catalogadas {len(r1)} ≠ "
                    f"payload.counts.total {expected_total_01}",
                    file=sys.stderr,
                )
                return 1
            print(f"   [BR-CATALOG-01] {len(r1)} regras de {path_01.name} "
                  f"(paridade OK: {expected_total_01})")
        else:
            print(f"   ⚠️  {path_01.name} ausente — sem regras de código.")

        # ── 02 — validações de tela / event handlers ───────────────────────
        if path_02.exists():
            expected_total_02 = self._count_expected_02(path_02)
            r2 = self._catalog_from_02(path_02)
            rules.extend(r2)
            # PARIDADE 02 — falha ruidosa
            if len(r2) != expected_total_02:
                print(
                    f"   ❌ PARIDADE 02 falhou: catalogadas {len(r2)} ≠ "
                    f"esperadas {expected_total_02} (has_validation OU event_handlers)",
                    file=sys.stderr,
                )
                return 1
            by_category["form_validation"] = len(r2)
            print(f"   [BR-CATALOG-02] {len(r2)} regras de validação de tela de "
                  f"{path_02.name} (paridade OK: {expected_total_02})")
        else:
            print(f"   ⚠️  {path_02.name} ausente — sem regras de tela.")

        domain_relevant = sum(1 for r in rules if r.get("domain_relevant"))
        ui_component = len(rules) - domain_relevant

        catalog = {
            "generated_at": self._timestamp(),
            "project": self.project_name,
            "trace_id": str(uuid.uuid4()),
            "source_artifacts": [path_01.name, path_02.name],
            "counts": {
                "total": len(rules),
                "from_01": expected_total_01,
                "from_02_validations": expected_total_02,
                "by_category": by_category,
                "domain_relevant": domain_relevant,
                "ui_component": ui_component,
            },
            "rules": rules,
        }

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.docs_dir / "business-rules-catalog.json"
        out_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"   ✅ {out_path}")
        print(f"   [BR-CATALOG] {len(rules)} regras catalogadas "
              f"(dominio={domain_relevant}, ui={ui_component})")

        # ── Enumeração Markdown das regras de DOMÍNIO (particionada) ────────
        self._write_domain_markdown(rules)
        return 0

    # ------------------------------------------------------------------
    # Enumeração Markdown determinística (apenas regras de domínio)
    # ------------------------------------------------------------------
    # Orçamento de tamanho por part (< hard limit de 600 KB de
    # artifact-size-governance.md). Mantém margem de segurança.
    _MD_PART_SOFT_BYTES = 500_000

    @staticmethod
    def _md_cell(text: Any) -> str:
        """Sanitiza um valor para célula de tabela Markdown."""
        s = str(text if text is not None else "")
        s = s.replace("\r", " ").replace("\n", " ")
        s = s.replace("|", "\\|")
        return s.strip()

    def _rule_md_row(self, r: dict[str, Any]) -> str:
        """Uma linha `| ID | Category | Rule | Source | Confirmed? |`."""
        if r.get("category") == "form_validation":
            rule_txt = r.get("expression") or (
                f"campo '{r.get('field', '')}' — {', '.join(r.get('event_handlers', []))}"
            )
        else:
            target = r.get("target")
            expr = r.get("expression", "")
            rule_txt = f"{target} = {expr}" if target and expr and "=" not in str(expr)[:2] else expr
        return (
            f"| {self._md_cell(r.get('id'))} "
            f"| {self._md_cell(r.get('category'))} "
            f"| {self._md_cell(rule_txt)} "
            f"| {self._md_cell(r.get('source'))} "
            f"| ✅ Code |"
        )

    def _build_domain_blocks(self, domain_rules: list[dict[str, Any]]) -> list[tuple[str, str]]:
        """
        Agrupa as regras de domínio por `unit` e retorna
        ``[(unit, bloco_markdown), ...]`` na ordem alfabética da unit.
        Cada bloco é uma seção `## Domain: <unit>` + tabela Formato B.
        """
        by_unit: dict[str, list[dict[str, Any]]] = {}
        for r in domain_rules:
            by_unit.setdefault(str(r.get("unit") or "(sem unit)"), []).append(r)

        blocks: list[tuple[str, str]] = []
        for unit in sorted(by_unit, key=str.lower):
            unit_rules = sorted(by_unit[unit], key=lambda x: str(x.get("id")))
            lines = [
                f"## Domain: {unit}",
                "",
                "| ID | Category | Rule | Source | Confirmed? |",
                "|----|----------|------|--------|------------|",
            ]
            lines.extend(self._rule_md_row(r) for r in unit_rules)
            lines.append("")
            blocks.append((unit, "\n".join(lines)))
        return blocks

    def _write_domain_markdown(self, rules: list[dict[str, Any]]) -> None:
        """
        Grava a enumeração 100% das regras de DOMÍNIO (domain_relevant == true)
        como Markdown particionado (`business-rules-part{N}.md`), Formato B.
        Regras de componentes de UI genéricos (domain_relevant == false)
        permanecem apenas no catálogo JSON.
        """
        domain_rules = [r for r in rules if r.get("domain_relevant")]
        if not domain_rules:
            print("   ⚠️  Nenhuma regra de domínio — enumeração Markdown ignorada.")
            return

        blocks = self._build_domain_blocks(domain_rules)

        # Particiona os blocos respeitando o orçamento de bytes por part
        # (nunca quebra uma unit no meio).
        parts: list[list[str]] = [[]]
        sizes: list[int] = [0]
        for unit, block in blocks:
            b = len(block.encode("utf-8"))
            if sizes[-1] > 0 and sizes[-1] + b > self._MD_PART_SOFT_BYTES:
                parts.append([])
                sizes.append(0)
            parts[-1].append(block)
            sizes[-1] += b

        total_parts = len(parts)
        date = self._timestamp()[:10]
        written: list[Path] = []
        for i, part_blocks in enumerate(parts, start=1):
            header = (
                f"# Business Rules — Enumeração de Domínio (Full) — {self.project_name} AS-IS — "
                f"Part {i}/{total_parts}\n"
                f"> ⚠️ Artefato particionado — este é o {i}º de {total_parts} arquivos.\n"
                f"> Enumeração **determinística** de TODAS as {len(domain_rules)} regras de "
                f"negócio de domínio (`domain_relevant == true`) do catálogo "
                f"[`business-rules-catalog.json`](./business-rules-catalog.json).\n"
                f"> Regras de componentes de UI genéricos permanecem apenas no catálogo JSON.\n"
                f"> Resumo curado de alto impacto: [`business-rules.md`](./business-rules.md).\n"
                f"**Generated**: {date}\n\n---\n\n"
            )
            content = header + "\n".join(part_blocks)
            out = self.docs_dir / f"business-rules-part{i}.md"
            out.write_text(content, encoding="utf-8")
            written.append(out)
            print(f"   ✅ {out.name} ({sizes[i-1] // 1024} KB, "
                  f"{sum(b.count('| BR-') + b.count('| FBR-') for b in part_blocks)} regras)")

        print(f"   [BR-CATALOG-MD] {len(domain_rules)} regras de domínio enumeradas em "
              f"{total_parts} part(s) Markdown")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_cli() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Gera o catálogo lossless de regras de negócio a partir dos artefatos AST"
    )
    ap.add_argument("--project", required=True, help="Nome do projeto")
    ap.add_argument(
        "--compressed-dir",
        type=Path,
        default=None,
        help="Diretório dos JSONs compactados (default: projects/{proj}/outputs/asis/delphi-ast-raw/compressed)",
    )
    ap.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="Diretório de saída docs (default: projects/{proj}/outputs/asis/docs)",
    )
    return ap


def main() -> int:
    ap = _build_cli()
    a = ap.parse_args()
    gen = BusinessRulesCatalogGenerator(
        project_name=a.project,
        compressed_dir=a.compressed_dir,
        docs_dir=a.docs_dir,
    )
    return gen.run()


if __name__ == "__main__":
    sys.exit(main())
