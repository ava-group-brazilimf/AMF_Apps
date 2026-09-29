"""
run_pipeline.py — Caminho 2 ponta a ponta:

    Delphi (.pas/.dfm/.sql)  ->  10 artefatos JSON  ->  10 JSON pré-comprimidos (Headroom)

Uso:
    python run_pipeline.py ./sample
    python run_pipeline.py /caminho/do/legado --extraction ./extraction --compressed ./compressed
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import delphi_ast_analyzer as analyzer
import headroom_precompress as hr
import validate_artifacts
from schemas import ARTIFACTS


def _append_metrics(compressed_dir: str, source_root: str, overview_path: str,
                    mf: dict, extraction_ms: float, precompress_ms: float) -> None:
    """Acrescenta uma linha de observabilidade em {compressed}/metrics.jsonl."""
    overview = json.loads(Path(overview_path).read_text(encoding="utf-8"))
    totals = overview["payload"]["totals"]
    line = {
        "run_id": overview["_volatile"]["run_id"],
        "exec_date": datetime.now(timezone.utc).isoformat(),
        "source_root": source_root,
        "ast_mode": totals.get("mode"),
        "engine": mf.get("engine"),
        "extraction_duration_ms": round(extraction_ms),
        "precompress_duration_ms": round(precompress_ms),
        "tokens_in": mf["totals"]["tokens_in"],
        "tokens_out": mf["totals"]["tokens_out"],
        "reduction_pct": mf["totals"]["reduction_pct"],
        "artifact_counts": {
            "units_total": totals.get("units_total"),
            "business_rules": totals.get("business_rules"),
            "db_tables": totals.get("db_tables"),
            "db_relationships": totals.get("db_relationships", 0),
            "integrations": totals.get("integrations"),
            "apis": totals.get("apis"),
            "sql_functions": 0,
        },
        "status": "ok",
    }
    metrics_fp = Path(compressed_dir) / "metrics.jsonl"
    with open(metrics_fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline de pré-compressão AVA Fabric")
    ap.add_argument("source_root", help="raiz do código Delphi")
    ap.add_argument("--extraction", default="./extraction", help="saída dos JSONs crus")
    ap.add_argument("--compressed", default="./compressed", help="saída pré-comprimida")
    ap.add_argument("--skip-validate", action="store_true",
                     help="pula a validação de schema dos artefatos (não recomendado)")
    a = ap.parse_args()

    run_start = datetime.now()
    t_run0 = time.perf_counter()
    print(f"Início: {run_start:%Y-%m-%d %H:%M:%S}")

    print("\n== 1/2  Extração Delphi AST ==")
    t0 = time.perf_counter()
    written = analyzer.analyze(a.source_root, a.extraction)
    extraction_ms = (time.perf_counter() - t0) * 1000
    for name in written:
        print(f"   ok  {name}.json  ({ARTIFACTS[name]})")

    if not a.skip_validate:
        violations = validate_artifacts.validate_dir(a.extraction)
        if violations:
            print(f"\nFALHA: {len(violations)} violação(ões) de schema:", file=sys.stderr)
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            sys.exit(1)
        print("   schema OK (src/schemas/artifacts.schema.json)")

    print("\n== 2/2  Pré-compressão Headroom ==")
    t1 = time.perf_counter()
    mf = hr.precompress(a.extraction, a.compressed)
    precompress_ms = (time.perf_counter() - t1) * 1000
    t = mf["totals"]
    print(f"\n   TOTAL: {t['tokens_in']} -> {t['tokens_out']} tokens  "
          f"(-{t['reduction_pct']}%)")

    _append_metrics(a.compressed, a.source_root, written["08_code_overview"],
                    mf, extraction_ms, precompress_ms)
    print(f"\nArtefatos prontos para o contexto do Copilot em: {a.compressed}/")

    run_end = datetime.now()
    total_s = time.perf_counter() - t_run0
    print(f"\nFim: {run_end:%Y-%m-%d %H:%M:%S}  |  Tempo total: {_fmt_duration(total_s)}  "
          f"(extração {_fmt_duration(extraction_ms / 1000)} + "
          f"compressão {_fmt_duration(precompress_ms / 1000)})")


if __name__ == "__main__":
    main()
