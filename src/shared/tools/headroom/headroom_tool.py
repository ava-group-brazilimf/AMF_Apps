#!/usr/bin/env python3
"""
headroom_tool.py — CLI determinística da tool Headroom do AVA Fabric.

Interface única entre a esteira de agentes e o motor Headroom (fork embedded em
``./vendor``).  Todo agente que consome artefatos AST chama esta CLI via a
diretiva ``Bash:``, do mesmo jeito que já chama ``pipeline_observer.py``.

Camadas
-------
- ``headroom_config.py``  resolve a configuração (env > project-config.yaml > headroom.yaml)
- ``headroom_context.py`` decodifica o formato Headroom e monta a fatia por agente
- este arquivo         expõe tudo como subcomandos e grava as métricas

Uso na esteira
--------------
    # Fatia de contexto do agente (barato, sem LLM) — o que ele deve ler
    python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP slice \\
        --agent ava-asis-db-analyzer --json

    # Registro de compressão (uma linha por chamada LLM)
    python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP metrics \\
        --agent ava-asis-inventory --phase F1 \\
        --original 12400 --compressed 1860 --latency-ms 320

    # Agregado do projeto
    python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP stats

Uso avulso
----------
    python src/shared/tools/headroom/headroom_tool.py decode --input arq.json
    python src/shared/tools/headroom/headroom_tool.py compress --input arq.json -o out.json
    python src/shared/tools/headroom/headroom_tool.py doctor
    python src/shared/tools/headroom/headroom_tool.py proxy status

Exit codes
----------
    0 — OK
    1 — degradado (motor ausente, proxy fora do ar, artefato faltando)
    2 — erro de uso ou de execução
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import headroom_config as hcfg  # noqa: E402
import headroom_context as hctx  # noqa: E402

# ─── Constants ───────────────────────────────────────────────────────────────

BRZ = timezone(timedelta(hours=-3))
REPO_ROOT = hcfg.REPO_ROOT
PID_FILE = REPO_ROOT / ".headroom" / "proxy.pid"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_brz() -> str:
    return datetime.now(BRZ).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def _fail(message: str, code: int = 2) -> None:
    print(f"❌ {message}", file=sys.stderr)
    sys.exit(code)


def _headroom_exe() -> str:
    """``headroom`` do venv isolado, ou o do PATH como fallback."""
    exe = hcfg.venv_headroom()
    return str(exe) if exe else "headroom"


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    probe_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    try:
        with socket.create_connection((probe_host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _append_metric(project_name: str, payload: dict[str, Any], cfg: dict[str, Any]) -> Path:
    """Append-only no JSONL do projeto — mesmo idioma de ``pipeline_observer``."""
    path = hcfg.metrics_path(project_name, cfg)
    with open(path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def _read_metrics(project_name: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = hcfg.metrics_path(project_name, cfg)
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _savings_pct(original: float, compressed: float) -> float:
    return round(100.0 * (1 - compressed / original), 1) if original else 0.0


# ─── Atribuição por janela de tempo (specs/032 · D3) ─────────────────────────
# O proxy sabe QUANTO comprimiu, mas não sabe QUAL agente originou a requisição
# — ele vê só o processo do Copilot CLI. O observer sabe QUANDO cada agente
# rodou. Cruzando os dois por tempo, a economia medida ganha dono.

#: Aliases tolerados no JSONL do proxy — o esquema não é contratual.
_TS_KEYS = ("timestamp", "ts", "time", "created_at")
_BEFORE_KEYS = ("tokens_before", "input_tokens_before", "tokens_in", "prompt_tokens_before")
_AFTER_KEYS = ("tokens_after", "input_tokens_after", "tokens_out", "prompt_tokens_after")
_LATENCY_KEYS = ("latency_ms", "duration_ms", "elapsed_ms")


def _first(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if record.get(key) is not None:
            return record[key]
    return None


def _parse_epoch(value: Any, assume_utc: bool = True) -> float | None:
    """ISO-8601 → epoch UTC. Aceita ``Z``, offset explícito e naive."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        # Proxy grava em UTC; o observer sempre carrega o offset -03:00.
        moment = moment.replace(tzinfo=timezone.utc if assume_utc else BRZ)
    return moment.timestamp()


def _read_proxy_log(path: Path) -> list[dict[str, Any]]:
    """Normaliza o JSONL do proxy, descartando linhas sem tempo ou sem tokens."""
    if not path.is_file():
        return []
    requests: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, dict):
            continue
        epoch = _parse_epoch(_first(raw, _TS_KEYS))
        before = _first(raw, _BEFORE_KEYS)
        after = _first(raw, _AFTER_KEYS)
        if epoch is None or before is None or after is None:
            continue
        try:
            requests.append({
                "epoch": epoch,
                "model": raw.get("model"),
                "before": int(before),
                "after": int(after),
                "latency_ms": int(_first(raw, _LATENCY_KEYS) or 0),
                "request_id": raw.get("request_id"),
            })
        except (TypeError, ValueError):
            continue
    return requests


def _agent_windows(project_name: str) -> list[dict[str, Any]]:
    """Janela ``[fim − duração, fim]`` de cada agente, em epoch UTC.

    ⚠️ A janela **não** está pronta no estado: `cmd_track` grava
    ``start_time == end_time`` porque os agentes só informam ``--duration-ms``
    (ver pipeline_observer.py, resolução de `start_time`). Reconstruímos aqui.
    """
    state_path = (REPO_ROOT / "projects" / project_name / "outputs"
                  / "observability" / "pipeline-run-state.json")
    if not state_path.is_file():
        return []
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    windows: list[dict[str, Any]] = []
    for agent_id, data in (state.get("agents") or {}).items():
        end = _parse_epoch(data.get("end_time"), assume_utc=False)
        if end is None:
            continue
        start = _parse_epoch(data.get("start_time"), assume_utc=False)
        duration_s = float(data.get("duration_ms") or 0) / 1000.0
        # Se start == end (caso normal), a duração é a única fonte da janela.
        if start is None or (end - start) < 1.0:
            start = end - duration_s
        windows.append({
            "agent_id": agent_id,
            "phase": data.get("phase", ""),
            "version": data.get("version", ""),
            "model": data.get("model"),
            "start": start,
            "end": end,
            "run_id": state.get("run_id"),
        })
    return windows


def attribute_requests(
    windows: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Distribui as requisições do proxy entre os agentes por sobreposição.

    Dispatch paralelo produz janelas sobrepostas; nesse caso a requisição é
    dividida em ``1/N`` e marcada ``ambiguous`` — melhor um número honesto e
    rotulado do que atribuir tudo ao primeiro agente que casar.
    """
    buckets: dict[str, dict[str, Any]] = {}
    unattributed = {"requests": 0, "before": 0.0, "after": 0.0, "latency_ms": 0}

    def bucket_for(agent_id: str, window: dict[str, Any] | None) -> dict[str, Any]:
        if agent_id not in buckets:
            buckets[agent_id] = {
                "agent_id": agent_id,
                "phase": (window or {}).get("phase", ""),
                "version": (window or {}).get("version", ""),
                "model": (window or {}).get("model"),
                "run_id": (window or {}).get("run_id"),
                "requests": 0.0,
                "before": 0.0,
                "after": 0.0,
                "latency_ms": 0.0,
                "ambiguous_requests": 0,
                "max_overlap": 1,
                "window_start": (window or {}).get("start"),
                "window_end": (window or {}).get("end"),
            }
        return buckets[agent_id]

    for request in requests:
        matches = [w for w in windows if w["start"] <= request["epoch"] <= w["end"]]
        if not matches:
            unattributed["requests"] += 1
            unattributed["before"] += request["before"]
            unattributed["after"] += request["after"]
            unattributed["latency_ms"] += request["latency_ms"]
            continue
        share = 1.0 / len(matches)
        for window in matches:
            bucket = bucket_for(window["agent_id"], window)
            bucket["requests"] += share
            bucket["before"] += request["before"] * share
            bucket["after"] += request["after"] * share
            bucket["latency_ms"] += request["latency_ms"] * share
            if len(matches) > 1:
                bucket["ambiguous_requests"] += 1
                bucket["max_overlap"] = max(bucket["max_overlap"], len(matches))

    return buckets, unattributed


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_slice(args: argparse.Namespace) -> None:
    """Fatia de artefatos que o agente consome + tokens estimados."""
    cfg = hcfg.load_config(args.project)
    context = hctx.build_agent_context(
        args.project, args.agent, args.language,
        include_payloads=args.with_payloads)

    if args.json:
        print(json.dumps(context, indent=2, ensure_ascii=False))
    else:
        limit = int(cfg.get("context_limit", 200000))
        tokens = context["tokens_estimated"]
        pct = round(100.0 * tokens / limit, 1) if limit else 0.0
        print(f"🧮 Headroom slice :: {args.project} :: {args.agent}")
        if not context["known_agent"]:
            print("   ⚠️  agente fora de AGENT_ARTIFACT_SLICE — fatia vazia assumida")
        print(f"   artefatos : {', '.join(context['artifacts']) or '(nenhum — agente de consolidação)'}")
        print(f"   tokens    : {tokens:,} de {limit:,} ({pct}% do limite)")
        print(f"   compressed: {context['compressed_dir'] or '(ausente — Step 0/AST não rodou)'}")

    if not context["compressed_dir"]:
        sys.exit(1)


def cmd_decode(args: argparse.Namespace) -> None:
    """Decodifica um arquivo no formato Headroom para JSON legível."""
    src = Path(args.input)
    if not src.is_file():
        _fail(f"arquivo não encontrado: {src}")
    try:
        doc = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"JSON inválido em {src}: {exc}")
        return

    decoded = hctx.decode_headroom(doc)
    report = hctx.decode_report(doc)
    payload = json.dumps(decoded, indent=2, ensure_ascii=False)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
        print(f"✅ decodificado → {out}")
    else:
        print(payload)

    if report["rows_dropped"]:
        print(f"⚠️  {report['rows_dropped']} de {report['rows_total']} linhas foram "
              f"amostradas fora na pré-compressão (motor fallback, sampled=true)",
              file=sys.stderr)


def cmd_compress(args: argparse.Namespace) -> None:
    """Comprime um arquivo via motor Headroom; sem motor, copia sem comprimir."""
    cfg = hcfg.load_config(args.project)
    src = Path(args.input)
    if not src.is_file():
        _fail(f"arquivo não encontrado: {src}")

    raw = src.read_text(encoding="utf-8")
    model = args.model or str(cfg.get("model", "claude-sonnet-4-6"))
    limit = int(args.limit or cfg.get("context_limit", 200000))
    ccfg = cfg.get("compress", {})

    if not hctx.HEADROOM_AVAILABLE:
        if not cfg.get("fallback_on_error", True):
            _fail("headroom-ai não está instalado e fallback_on_error=false", 1)
        print("⚠️  headroom-ai indisponível — passthrough sem compressão "
              "(rode src/shared/tools/headroom/setup.ps1)", file=sys.stderr)
        out_text, tokens_in, tokens_out, transforms = raw, 0, 0, ["passthrough"]
    else:
        from headroom import CompressConfig, compress  # noqa: PLC0415

        # O detector do headroom só reconhece JSON_ARRAY na raiz. Os artefatos AST
        # são objetos, então embrulhamos num array de 1 elemento e desembrulhamos
        # depois — mesmo truque de headroom_precompress.py no analisador externo.
        try:
            doc = json.loads(raw)
            wrapped, is_json = json.dumps([doc], ensure_ascii=False), True
        except json.JSONDecodeError:
            wrapped, is_json = raw, False

        result = compress(
            [{"role": "user", "content": wrapped}],
            model=model,
            model_limit=limit,
            config=CompressConfig(
                compress_user_messages=bool(ccfg.get("compress_user_messages", True)),
                protect_recent=int(ccfg.get("protect_recent", 0)),
                min_tokens_to_compress=int(ccfg.get("min_tokens_to_compress", 250)),
                target_ratio=ccfg.get("target_ratio"),
            ),
        )
        content = result.messages[-1]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        if is_json:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list) and len(parsed) == 1:
                    content = json.dumps(parsed[0], ensure_ascii=False)
            except json.JSONDecodeError:
                pass  # forma inesperada — grava como veio
        out_text = content
        tokens_in, tokens_out = result.tokens_before, result.tokens_after
        transforms = list(result.transforms_applied)

    out_path = Path(args.out) if args.out else src.with_suffix(".compressed.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")

    pct = _savings_pct(tokens_in, tokens_out)
    print(f"✅ {src.name}: {tokens_in:,} → {tokens_out:,} tokens (-{pct}%) → {out_path}")
    print(f"   transforms: {', '.join(transforms) or '(nenhum)'}")

    if args.project:
        _append_metric(args.project, {
            "ts": _now_brz(),
            "agent_id": args.agent or "cli:compress",
            "phase": args.phase,
            "model": model,
            "original_tokens": tokens_in,
            "compressed_tokens": tokens_out,
            "tokens_saved": max(0, tokens_in - tokens_out),
            "savings_pct": pct,
            "compression_applied": hctx.HEADROOM_AVAILABLE,
            "detect_backend": cfg.get("detect_backend", "auto"),
            "proxy_used": False,
            "latency_ms": None,
            "context_limit": limit,
            "source": str(src),
            "transforms": transforms,
            "error": None,
        }, cfg)


def cmd_metrics(args: argparse.Namespace) -> None:
    """Registra uma linha de métrica de compressão (auto-report do agente)."""
    cfg = hcfg.load_config(args.project)
    original, compressed = args.original, args.compressed
    payload = {
        "ts": _now_brz(),
        "run_id": args.run_id,
        "agent_id": args.agent,
        "phase": args.phase,
        "model": args.model or str(cfg.get("model", "claude-sonnet-4-6")),
        # `manual` distingue de `self-report` (hook do track) e `proxy` (attribute).
        "source": "manual",
        "original_tokens": original,
        "compressed_tokens": compressed,
        "tokens_saved": max(0, original - compressed),
        "savings_pct": _savings_pct(original, compressed),
        "compression_applied": args.error is None and compressed < original,
        "detect_backend": cfg.get("detect_backend", "auto"),
        "proxy_used": args.proxy_used,
        "latency_ms": args.latency_ms,
        "context_limit": int(cfg.get("context_limit", 200000)),
        "error": args.error,
    }
    path = _append_metric(args.project, payload, cfg)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"📊 {args.agent} [{args.phase}]: {original:,} → {compressed:,} tokens "
              f"(-{payload['savings_pct']}%) → {path.relative_to(REPO_ROOT)}")


def cmd_attribute(args: argparse.Namespace) -> None:
    """Credita a economia medida pelo proxy a cada agente, por janela de tempo."""
    cfg = hcfg.load_config(args.project)
    log_path = hcfg.proxy_log_path(cfg)
    requests = _read_proxy_log(log_path)
    windows = _agent_windows(args.project)

    if args.phase:
        windows = [w for w in windows if w["phase"] == args.phase]

    if not requests:
        print(f"ℹ️  nenhuma requisição no log do proxy ({log_path}).", file=sys.stderr)
        print("   O proxy grava esse JSONL só quando HEADROOM_LOG_FILE está ativo "
              "e passa tráfego por ele.", file=sys.stderr)
        sys.exit(1)
    if not windows:
        print(f"ℹ️  nenhum agente com janela de execução em {args.project}"
              + (f" na fase {args.phase}" if args.phase else "")
              + " — rode a esteira com `pipeline_observer track` antes.", file=sys.stderr)
        sys.exit(1)

    buckets, unattributed = attribute_requests(windows, requests)

    written = 0
    for bucket in sorted(buckets.values(), key=lambda b: b["agent_id"]):
        before, after = round(bucket["before"]), round(bucket["after"])
        payload = {
            "ts": _now_brz(),
            "run_id": bucket["run_id"],
            "agent_id": bucket["agent_id"],
            "phase": bucket["phase"],
            "version": bucket["version"],
            "model": bucket["model"] or cfg.get("model"),
            "source": "proxy",
            "requests": round(bucket["requests"], 2),
            "original_tokens": before,
            "compressed_tokens": after,
            "tokens_saved": max(0, before - after),
            "savings_pct": _savings_pct(before, after),
            "compression_applied": after < before,
            "latency_ms": round(bucket["latency_ms"]),
            "attribution": "ambiguous" if bucket["ambiguous_requests"] else "exclusive",
            "ambiguous_requests": bucket["ambiguous_requests"],
            "max_overlap": bucket["max_overlap"],
            "context_limit": int(cfg.get("context_limit", 200000)),
            "proxy_used": True,
            "error": None,
        }
        if not args.dry_run:
            _append_metric(args.project, payload, cfg)
        written += 1

    total_before = sum(b["before"] for b in buckets.values()) + unattributed["before"]
    total_after = sum(b["after"] for b in buckets.values()) + unattributed["after"]

    summary = {
        "project": args.project,
        "phase": args.phase,
        "proxy_log": str(log_path),
        "requests_total": len(requests),
        "requests_unattributed": unattributed["requests"],
        "agents_attributed": written,
        "original_tokens": round(total_before),
        "compressed_tokens": round(total_after),
        "savings_pct": _savings_pct(total_before, total_after),
        "dry_run": bool(args.dry_run),
    }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    print(f"🧮 Headroom attribute :: {args.project}"
          + (f" :: {args.phase}" if args.phase else ""))
    print(f"   requisições : {len(requests)}  "
          f"({unattributed['requests']} fora de qualquer janela)")
    print(f"   tokens      : {round(total_before):,} → {round(total_after):,}  "
          f"(-{summary['savings_pct']}%)")
    print("   ── por agente ──")
    for bucket in sorted(buckets.values(), key=lambda b: -b["before"]):
        before, after = round(bucket["before"]), round(bucket["after"])
        flag = f"  ⚠️ {bucket['ambiguous_requests']} ambíguas (até {bucket['max_overlap']}x)" \
            if bucket["ambiguous_requests"] else ""
        print(f"   {bucket['agent_id']:<38} {before:>9,} → {after:>9,}  "
              f"(-{_savings_pct(before, after)}%){flag}")
    if unattributed["requests"]:
        print(f"   {'__unattributed__':<38} {round(unattributed['before']):>9,} → "
              f"{round(unattributed['after']):>9,}")
        print("   (requisições fora de qualquer janela de agente — orquestrador "
              "entre dispatches, ou agente que não chamou `track`)")
    if args.dry_run:
        print("\n   (dry-run — nada foi gravado)")
    else:
        print(f"\n   ✅ {written} linhas `source: proxy` gravadas em "
              f"{hcfg.metrics_path(args.project, cfg).relative_to(REPO_ROOT)}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Agrega o JSONL de métricas do projeto, separando estimado × medido."""
    cfg = hcfg.load_config(args.project)
    records = _read_metrics(args.project, cfg)
    if not records:
        print(f"ℹ️  nenhuma métrica registrada ainda para {args.project}")
        sys.exit(1)

    def blank() -> dict[str, Any]:
        return {"calls": 0, "tin": 0, "tout": 0, "volume": 0, "ambiguous": 0}

    per_source: dict[str, dict[str, Any]] = {}
    per_agent: dict[str, dict[str, dict[str, Any]]] = {}

    for record in records:
        source = str(record.get("source") or "manual")
        agent = str(record.get("agent_id") or "?")
        for bucket in (per_source.setdefault(source, blank()),
                       per_agent.setdefault(agent, {}).setdefault(source, blank())):
            bucket["calls"] += 1
            bucket["tin"] += int(record.get("original_tokens") or 0)
            bucket["tout"] += int(record.get("compressed_tokens") or 0)
            bucket["volume"] += int(record.get("tokens_total") or 0)
            if record.get("attribution") == "ambiguous":
                bucket["ambiguous"] += 1

    summary = {
        "project": args.project,
        "calls": len(records),
        "errors": sum(1 for r in records if r.get("error")),
        "by_source": {
            source: {**vals, "savings_pct": _savings_pct(vals["tin"], vals["tout"])}
            for source, vals in sorted(per_source.items())
        },
        "per_agent": {
            agent: {
                source: {**vals, "savings_pct": _savings_pct(vals["tin"], vals["tout"])}
                for source, vals in sorted(sources.items())
            }
            for agent, sources in sorted(per_agent.items())
        },
    }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    print(f"📊 Headroom stats :: {args.project}")
    print(f"   registros : {summary['calls']}  (erros: {summary['errors']})")
    for source, vals in summary["by_source"].items():
        if source == "self-report":
            print(f"   {source:<12} {vals['calls']:>3} registros · "
                  f"volume {vals['volume']:,} tokens (estimado pelo agente)")
        else:
            print(f"   {source:<12} {vals['calls']:>3} registros · "
                  f"{vals['tin']:,} → {vals['tout']:,} (-{vals['savings_pct']}%)"
                  + (f" · {vals['ambiguous']} ambíguas" if vals["ambiguous"] else ""))

    print("   ── por agente ──")
    for agent, sources in summary["per_agent"].items():
        proxy = sources.get("proxy")
        manual = sources.get("manual")
        measured = proxy or manual
        volume = sum(s["volume"] for s in sources.values())
        if measured and measured["tin"]:
            print(f"   {agent:<38} {measured['tin']:>9,} → {measured['tout']:>9,}  "
                  f"(-{measured['savings_pct']}%)")
        else:
            print(f"   {agent:<38} {volume:>9,} tokens  (sem medição do proxy)")


def _copilot_routing(expected_url: str) -> tuple[bool, str]:
    """O ``copilot`` deste shell passa pelo proxy?

    ``.vscode/settings.json`` injeta ``HEADROOM_*`` e ``ANTHROPIC_TARGET_API_URL`` em
    todo terminal integrado, mas **não** ``COPILOT_PROVIDER_BASE_URL`` — só
    ``copilot-cli-headroom.bat`` faz isso. O resultado é o pior tipo de falha
    silenciosa: a tool reporta o proxy configurado e no ar, e mesmo assim
    ``proxy-requests.jsonl`` fica sem uma linha sequer, porque o ``copilot`` daquele
    terminal foi direto ao Foundry.

    Não dá para corrigir em ``settings.json``: o bearer token vem de ``.copilot-key``
    e não pode viver em arquivo versionado — um terminal meio-configurado falharia na
    requisição em vez de degradar. Então o diagnóstico só torna o bypass **visível**.
    """
    actual = os.environ.get("COPILOT_PROVIDER_BASE_URL", "").strip()
    if not actual:
        return False, ("COPILOT_PROVIDER_BASE_URL não definida — o copilot deste shell "
                       "NÃO passa pelo proxy; use copilot-cli-headroom.bat")
    if actual.rstrip("/") != expected_url.rstrip("/"):
        return False, f"aponta para {actual} — esperado {expected_url} (bypass do proxy)"
    return True, f"{actual} (via proxy)"


def cmd_doctor(args: argparse.Namespace) -> None:
    """Diagnóstico: venv, fork, motor, fatias, proxy e upstream."""
    cfg = hcfg.load_config(args.project)
    proxy = cfg.get("proxy", {})
    host, port = str(proxy.get("host", "127.0.0.1")), int(proxy.get("port", 8787))
    venv_py, venv_hr = hcfg.venv_python(), hcfg.venv_headroom()
    proxy_up = _port_open(host, port)

    checks = [
        ("config", True, f"model={cfg.get('model')} limit={cfg.get('context_limit')} "
                         f"enabled={cfg.get('enabled')}"),
        ("fork (vendor/)", (hcfg.VENDOR_DIR / "pyproject.toml").is_file(),
         str(hcfg.VENDOR_DIR.relative_to(REPO_ROOT))),
        ("venv isolado", venv_py is not None,
         str(venv_py.relative_to(REPO_ROOT)) if venv_py else "ausente — rode setup.ps1"),
        ("cli headroom", venv_hr is not None,
         str(venv_hr.relative_to(REPO_ROOT)) if venv_hr else "ausente no venv (usando PATH)"),
        ("motor (import headroom)", hctx.HEADROOM_AVAILABLE,
         "disponível" if hctx.HEADROOM_AVAILABLE else "indisponível — compressão em passthrough"),
        ("fatias por agente", bool(hctx.AGENT_ARTIFACT_SLICE),
         f"{len(hctx.AGENT_ARTIFACT_SLICE)} agentes em context_budget.AGENT_ARTIFACT_SLICE"),
        ("proxy", proxy_up, f"{host}:{port} " + ("no ar" if proxy_up else "fora do ar")),
        ("upstream", bool(proxy.get("upstream")), str(proxy.get("upstream") or "não configurado")),
        ("copilot → proxy", *_copilot_routing(hcfg.proxy_url(cfg))),
    ]
    if args.project:
        compressed = hctx.resolve_compressed_dir(args.project, args.language)
        checks.append(("artefatos AST", compressed is not None,
                       str(compressed) if compressed else
                       f"nenhum compressed/ em projects/{args.project}/outputs/asis/"))

    if args.json:
        print(json.dumps({
            "ok": all(ok for _, ok, _ in checks),
            "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
        }, indent=2, ensure_ascii=False))
    else:
        print("🩺 Headroom doctor")
        for name, ok, detail in checks:
            print(f"   {'✅' if ok else '⚠️ '} {name:<26} {detail}")

    # Só o fork ausente é erro duro: sem ele a tool não tem o que rodar.
    if not (hcfg.VENDOR_DIR / "pyproject.toml").is_file():
        sys.exit(2)
    sys.exit(0 if all(ok for _, ok, _ in checks) else 1)


def cmd_proxy(args: argparse.Namespace) -> None:
    """Sobe/derruba/consulta o proxy interceptor."""
    cfg = hcfg.load_config(args.project)
    proxy = cfg.get("proxy", {})
    host, port = str(proxy.get("host", "127.0.0.1")), int(proxy.get("port", 8787))

    if args.action == "status":
        up = _port_open(host, port)
        detail = {"running": up, "host": host, "port": port,
                  "upstream": proxy.get("upstream"),
                  "pid": PID_FILE.read_text(encoding="utf-8").strip()
                         if PID_FILE.is_file() else None}
        if args.json:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        else:
            print(f"{'🟢' if up else '🔴'} proxy {host}:{port} "
                  f"{'no ar' if up else 'fora do ar'} → {proxy.get('upstream')}")
        sys.exit(0 if up else 1)

    if args.action == "start":
        if _port_open(host, port):
            print(f"ℹ️  proxy já está no ar em {host}:{port}")
            sys.exit(0)
        env = {**os.environ, **hcfg.proxy_env(cfg)}
        cmd = [_headroom_exe(), "proxy", "--host", host, "--port", str(port)]
        if not proxy.get("http2", False):
            cmd.append("--no-http2")
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Destacar o processo para que ele sobreviva ao fim deste comando.
        if os.name == "nt":
            detach = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
        else:
            detach = {"start_new_session": True}
        try:
            process = subprocess.Popen(  # noqa: S603
                cmd, env=env, cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detach)
        except FileNotFoundError:
            _fail("executável 'headroom' não encontrado — rode src/shared/tools/headroom/setup.ps1")
            return
        PID_FILE.write_text(str(process.pid), encoding="utf-8")
        print(f"🚀 proxy iniciado (pid {process.pid}) em {host}:{port} → {proxy.get('upstream')}")
        print(f"   log: {hcfg.proxy_log_path(cfg)}")
        return

    # stop
    if not PID_FILE.is_file():
        print("ℹ️  nenhum pid registrado em .headroom/proxy.pid")
        sys.exit(1)
    pid = PID_FILE.read_text(encoding="utf-8").strip()
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", pid, "/F", "/T"],  # noqa: S603,S607
                           check=False, capture_output=True)
        else:
            os.kill(int(pid), 15)
    except (OSError, ValueError) as exc:
        _fail(f"falha ao encerrar pid {pid}: {exc}", 1)
    PID_FILE.unlink(missing_ok=True)
    print(f"🛑 proxy encerrado (pid {pid})")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="headroom_tool.py",
        description="Tool Headroom do AVA Fabric — compressão de contexto e métricas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  headroom_tool.py -p Meu-ERP slice --agent ava-asis-db-analyzer --json\n"
            "  headroom_tool.py -p Meu-ERP metrics --agent ava-asis-inventory --phase F1 \\\n"
            "      --original 12400 --compressed 1860 --latency-ms 320\n"
            "  headroom_tool.py -p Meu-ERP stats\n"
            "  headroom_tool.py decode --input compressed/05_procedures.json\n"
            "  headroom_tool.py doctor\n"
            "  headroom_tool.py proxy start\n"
        ),
    )
    parser.add_argument("-p", "--project", help="Nome do projeto em projects/")
    parser.add_argument("--language", help="Tecnologia legada (delphi, vb, cobol…)")
    subs = parser.add_subparsers(dest="command", required=True)

    sp = subs.add_parser("slice", help="Fatia de artefatos + tokens de um agente")
    sp.add_argument("--agent", required=True)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--with-payloads", action="store_true",
                    help="Inclui o conteúdo decodificado dos artefatos na saída")

    sp = subs.add_parser("decode", help="Decodifica um artefato no formato Headroom")
    sp.add_argument("--input", required=True)
    sp.add_argument("-o", "--out")

    sp = subs.add_parser("compress", help="Comprime um arquivo via motor Headroom")
    sp.add_argument("--input", required=True)
    sp.add_argument("-o", "--out")
    sp.add_argument("--model")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--agent", help="agent_id para a linha de métrica")
    sp.add_argument("--phase", help="Fase da esteira (F1…F7)")

    sp = subs.add_parser("metrics", help="Registra uma linha de métrica de compressão")
    sp.add_argument("--agent", required=True)
    sp.add_argument("--phase", required=True)
    sp.add_argument("--original", type=int, required=True, help="tokens antes da compressão")
    sp.add_argument("--compressed", type=int, required=True, help="tokens depois")
    sp.add_argument("--latency-ms", type=int)
    sp.add_argument("--model")
    sp.add_argument("--run-id")
    sp.add_argument("--proxy-used", action="store_true")
    sp.add_argument("--error", help="Mensagem de erro, se a compressão falhou")
    sp.add_argument("--json", action="store_true")

    sp = subs.add_parser(
        "attribute",
        help="Credita a economia medida pelo proxy a cada agente (por janela de tempo)")
    sp.add_argument("--phase", help="Restringe a uma fase (F1…F8)")
    sp.add_argument("--dry-run", action="store_true", help="Calcula sem gravar")
    sp.add_argument("--json", action="store_true")

    sp = subs.add_parser("stats", help="Agregado das métricas do projeto")
    sp.add_argument("--json", action="store_true")

    sp = subs.add_parser("doctor", help="Diagnóstico da instalação e do proxy")
    sp.add_argument("--json", action="store_true")

    sp = subs.add_parser("proxy", help="Gerencia o proxy interceptor")
    sp.add_argument("action", choices=["start", "stop", "status"])
    sp.add_argument("--json", action="store_true")

    args = parser.parse_args()

    needs_project = {"slice", "metrics", "stats", "attribute"}
    if args.command in needs_project and not args.project:
        parser.error(f"o subcomando '{args.command}' exige -p/--project")

    dispatch = {
        "slice": cmd_slice,
        "decode": cmd_decode,
        "compress": cmd_compress,
        "metrics": cmd_metrics,
        "attribute": cmd_attribute,
        "stats": cmd_stats,
        "doctor": cmd_doctor,
        "proxy": cmd_proxy,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
