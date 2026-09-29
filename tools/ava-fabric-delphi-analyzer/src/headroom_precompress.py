"""
headroom_precompress.py — Estágio 2 do Caminho 2 (pré-compressão offline).

Comprime CADA um dos 9 artefatos JSON antes de entrarem no contexto do agente
`.md` no Copilot. Dois modos:

    [A] Headroom REAL — se `headroom-ai` estiver instalado
        (pip install "headroom-ai[all]"). Usa headroom.compress() com o pipeline
        completo (CacheAligner -> ContentRouter -> SmartCrusher). Reversível (CCR),
        métricas de token reais.
    [B] Fallback local — SmartCrusher-lite (schema-factoring + preserva anomalias),
        para rodar sem dependências.

Gera manifest.json com tokens_in/out, ratio e transforms por artefato — pronto
para o metrics.jsonl do AVA Fabric.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

# ----------------------------------------------------------------------------
# [A] Headroom REAL
# ----------------------------------------------------------------------------
def _headroom_available() -> bool:
    try:
        import headroom  # noqa
        return True
    except Exception:
        return False


def _compress_with_headroom(raw: str, model: str) -> dict[str, Any] | None:
    """Comprime via headroom.compress(). Retorna dict de resultado ou None."""
    try:
        from headroom import compress, CompressConfig
    except Exception:
        return None
    try:
        doc = json.loads(raw)
    except Exception:
        return None
    try:
        # Headroom só detecta JSON_ARRAY no nível raiz (content.startswith("[")) —
        # todo artefato aqui é um objeto ({"artifact":..., "payload":...}), então
        # embrulhamos num array de 1 elemento pra acionar o SmartCrusher real, e
        # desembrulhamos depois. Verificado empiricamente: sem isso, 100% dos
        # artefatos caem em PLAIN_TEXT e o router sempre reporta "noop".
        wrapped = json.dumps([doc], ensure_ascii=False)
        cfg = CompressConfig(compress_user_messages=True, protect_recent=0,
                             min_tokens_to_compress=100)
        res = compress([{"role": "user", "content": wrapped}], model=model, config=cfg)
        content = res.messages[-1]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        try:
            parsed = json.loads(content)
            if not (isinstance(parsed, list) and len(parsed) == 1):
                return None  # forma inesperada -> cai pro fallback local
            unwrapped = json.dumps(parsed[0], ensure_ascii=False)
        except Exception:
            return None
        return {"content": unwrapped, "tokens_in": res.tokens_before,
                "tokens_out": res.tokens_after,
                "transforms": list(res.transforms_applied), "mode": "headroom"}
    except Exception:
        return None


# ----------------------------------------------------------------------------
# [B] Fallback local — SmartCrusher-lite
# ----------------------------------------------------------------------------
HEAD, TAIL, MAX_ROWS = 30, 15, 200


def est_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def _looks_anomalous(row: dict) -> bool:
    blob = json.dumps(row, ensure_ascii=False).lower()
    return any(k in blob for k in ("error", "erro", "fail", "exception", "warn"))


def _factor_array(arr: list) -> dict | None:
    if len(arr) < 4 or not all(isinstance(x, dict) for x in arr):
        return None
    keys = list(arr[0].keys())
    if not all(list(x.keys()) == keys for x in arr):
        return None
    rows = [[x[k] for k in keys] for x in arr]
    kept, sampled = rows, False
    if len(rows) > MAX_ROWS:
        h, t = MAX_ROWS * HEAD // 100, MAX_ROWS * TAIL // 100
        anomalies = [r for r, o in zip(rows, arr) if _looks_anomalous(o)]
        kept, sampled = rows[:h] + anomalies + rows[-t:], True
    return {"__headroom__": "factored_array", "schema": keys, "count": len(arr),
            "kept": len(kept), "sampled": sampled, "rows": kept}


def _crush(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _crush(v) for k, v in node.items()}
    if isinstance(node, list):
        f = _factor_array(node) if node and isinstance(node[0], dict) else None
        return f if f else [_crush(x) for x in node]
    return node


def _compress_fallback(raw: str) -> dict[str, Any]:
    doc = json.loads(raw)
    if "payload" in doc:
        doc["payload"] = _crush(doc["payload"])
    doc["_headroom"] = {"mode": "fallback-smartcrusher-lite"}
    out = json.dumps(doc, ensure_ascii=False)
    return {"content": out, "tokens_in": est_tokens(raw), "tokens_out": est_tokens(out),
            "transforms": ["fallback:factor_array"], "mode": "fallback-smartcrusher-lite"}


# ----------------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------------
def precompress(in_dir: str, out_dir: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    manifest: dict[str, Any] = {"engine": "headroom" if _headroom_available()
                                else "fallback", "model": model, "artifacts": []}
    tin = tout = 0
    files = sorted(Path(in_dir).glob("*.json"))
    for i, fp in enumerate(files, 1):
        t_art0 = time.perf_counter()
        raw = fp.read_text(encoding="utf-8")
        res = _compress_with_headroom(raw, model) or _compress_fallback(raw)
        (Path(out_dir) / fp.name).write_text(res["content"], encoding="utf-8")
        duration_ms = (time.perf_counter() - t_art0) * 1000
        tin += res["tokens_in"]
        tout += res["tokens_out"]
        reduction_pct = (round(100 * (1 - res["tokens_out"] / res["tokens_in"]), 1)
                        if res["tokens_in"] else 0.0)
        print(f"   [{i}/{len(files)}] {fp.stem:<24} {res['tokens_in']:>6} -> "
              f"{res['tokens_out']:>6} tok  (-{reduction_pct}%)  {duration_ms/1000:5.2f}s")
        manifest["artifacts"].append({
            "artifact": fp.stem, "mode": res["mode"],
            "tokens_in": res["tokens_in"], "tokens_out": res["tokens_out"],
            "reduction_pct": reduction_pct, "duration_ms": round(duration_ms),
            "transforms": res["transforms"]})
    manifest["totals"] = {"tokens_in": tin, "tokens_out": tout,
                          "reduction_pct": round(100 * (1 - tout / tin), 1) if tin else 0.0}
    (Path(out_dir) / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Pré-compressão Headroom dos 9 artefatos")
    ap.add_argument("in_dir")
    ap.add_argument("-o", "--out", default="./compressed")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    mf = precompress(a.in_dir, a.out, a.model)
    print(f"Engine: {mf['engine']}")
    for art in mf["artifacts"]:
        print(f"  {art['artifact']:<24} {art['tokens_in']:>6} -> {art['tokens_out']:>6} "
              f"tok  (-{art['reduction_pct']}%)  {art['transforms']}")
    t = mf["totals"]
    print(f"  TOTAL: {t['tokens_in']} -> {t['tokens_out']} tok  (-{t['reduction_pct']}%)")
