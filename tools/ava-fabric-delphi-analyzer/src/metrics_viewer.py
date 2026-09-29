"""
metrics_viewer.py — Lê o metrics.jsonl (gerado por run_pipeline.py) e exibe um
relatório consolidado de execuções: modo AST, tokens, redução, duração.

Uso:
    python src/metrics_viewer.py
    python src/metrics_viewer.py --metrics-file ./compressed/metrics.jsonl
    python src/metrics_viewer.py --run-id 6f95624db473
    python src/metrics_viewer.py --last 5
    python src/metrics_viewer.py --export metrics-report.csv
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

METRICS_FILE = Path("./compressed/metrics.jsonl")

FIELDS = [
    "run_id", "exec_date", "source_root", "ast_mode", "engine",
    "extraction_duration_ms", "precompress_duration_ms",
    "tokens_in", "tokens_out", "reduction_pct", "status",
]


def load_records(metrics_file: Path, run_id: str | None = None,
                 last_n: int | None = None) -> list[dict]:
    if not metrics_file.exists():
        return []
    records = []
    with open(metrics_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if run_id and r.get("run_id") != run_id:
                continue
            records.append(r)
    if last_n:
        records = records[-last_n:]
    return records


def print_report(records: list[dict]) -> None:
    print(f"\n{'='*88}")
    print("  AVA Fabric Delphi Analyzer — Pipeline Metrics Report")
    print(f"{'='*88}")

    grand_tokens_in = grand_tokens_out = 0
    grand_dur_ms = 0

    for r in records:
        counts = r.get("artifact_counts", {})
        print(f"\n  [run_id: {r.get('run_id')}]  ({r.get('exec_date', '')[:19]})")
        print(f"    source: {r.get('source_root')}")
        print(f"    ast_mode: {r.get('ast_mode')}   engine: {r.get('engine')}   "
              f"status: {r.get('status')}")
        print(f"    units_total: {counts.get('units_total', 0):,}   "
              f"business_rules: {counts.get('business_rules', 0):,}   "
              f"db_tables: {counts.get('db_tables', 0):,}   "
              f"integrations: {counts.get('integrations', 0):,}   "
              f"apis: {counts.get('apis', 0):,}")
        dur = r.get("extraction_duration_ms", 0) + r.get("precompress_duration_ms", 0)
        print(f"    tokens: {r.get('tokens_in', 0):,} -> {r.get('tokens_out', 0):,}  "
              f"(-{r.get('reduction_pct', 0)}%)   duration: {dur:,.0f}ms "
              f"(extração {r.get('extraction_duration_ms', 0):,.0f}ms + "
              f"precompressão {r.get('precompress_duration_ms', 0):,.0f}ms)")

        grand_tokens_in += r.get("tokens_in", 0)
        grand_tokens_out += r.get("tokens_out", 0)
        grand_dur_ms += dur

    print(f"\n{'-'*88}")
    print(f"  TOTAL across {len(records)} run(s): "
          f"tokens {grand_tokens_in:,} -> {grand_tokens_out:,}  |  "
          f"duração {grand_dur_ms:,.0f}ms")
    print(f"{'='*88}\n")


def export_csv(records: list[dict], output_file: str) -> None:
    if not records:
        print("Nenhum registro para exportar.")
        return
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"Exportado {len(records)} registro(s) para {output_file}")


def main() -> None:
    ap = argparse.ArgumentParser(description="AVA Fabric Delphi Analyzer — Metrics Viewer")
    ap.add_argument("--metrics-file", default=str(METRICS_FILE))
    ap.add_argument("--run-id", default=None, help="Filtra por run_id específico")
    ap.add_argument("--last", type=int, default=None, help="Mostra as últimas N execuções")
    ap.add_argument("--export", default=None, help="Exporta para arquivo CSV")
    a = ap.parse_args()

    mf = Path(a.metrics_file)
    if not mf.exists():
        print(f"[INFO] Arquivo de métricas não encontrado: {mf}")
        print("Rode o pipeline (run_pipeline.py) primeiro para gerar métricas.")
        sys.exit(0)

    records = load_records(mf, run_id=a.run_id, last_n=a.last)
    if not records:
        print("Nenhum registro encontrado com esse filtro.")
        sys.exit(0)

    if a.export:
        export_csv(records, a.export)
    else:
        print_report(records)


if __name__ == "__main__":
    main()
