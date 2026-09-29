#!/usr/bin/env python3
"""
check_session_health.py — Detecta subagente que nasceu morto numa sessão do Copilot CLI.

Por que isto existe
-------------------
Um levantamento de 70 sessões (`~/.copilot/session-state/*/events.jsonl`) encontrou
**78 dispatches que não produziram absolutamente nada**, e a esteira seguiu como se
tivessem retornado resultado:

    agentName          modelo          dispatches   com totalToolCalls == 0
    task               claude-sonnet-4        950   10 de 946  (1%)
    general-purpose    gpt-5.4                 54   53 de 53   (100%)
    explore            gpt-5.4-mini            24   19 de 19   (100%)

A sequência é sempre a mesma:

    subagent.started    agentName=general-purpose  model=gpt-5.4
    session.error  404  "Model 'claude-sonnet-4-6' not found on provider at …"
    subagent.completed  agentName=general-purpose  totalToolCalls=0

Com BYOK, **todo** tráfego vai para o provider configurado. Quando o CLI troca o
modelo do subagente para um modelo hospedado do GitHub (`gpt-5.4`), a troca dispara
uma validação do wire model contra o provider — que responde 404. O subagente morre
antes da primeira tool call.

`agent_runner.py` é imune (pina `--model`, roda com `--excluded-tools=skill,task`).
Esta ferramenta cobre o caminho **interativo**, onde não há runner e ninguém está
olhando — é a mesma consulta que produziu a tabela acima, agora executável.

Uso
---
    python src/shared/tools/check_session_health.py                   # última sessão
    python src/shared/tools/check_session_health.py --all
    python src/shared/tools/check_session_health.py --session <uuid-ou-prefixo>
    python src/shared/tools/check_session_health.py --all --since 2026-08-03
    python src/shared/tools/check_session_health.py --all --json

Exit codes: 0 saudável · 1 problema encontrado · 2 erro de uso.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

#: Modelo BYOK esperado. É o `COPILOT_PROVIDER_MODEL_ID` do `copilot-cli-headroom.bat`
#: (o wire model `claude-sonnet-4-6` é o nome no Foundry, não o que aparece aqui).
DEFAULT_EXPECTED_MODEL = "claude-sonnet-4"

#: Tipos de subagente embutidos do CLI que trazem modelo próprio e, sob BYOK,
#: falham 100% das vezes. `task` herda o modelo do pai e funciona.
BUILTIN_FOREIGN_AGENTS = ("general-purpose", "explore")


def session_root() -> Path:
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".copilot" / "session-state"


def _iter_events(path: Path):
    """Eventos de um `events.jsonl`, ignorando linhas corrompidas.

    O arquivo é append-only e pode estar sendo escrito enquanto lemos; uma linha
    parcial no fim não pode derrubar a análise.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue


def _endpoint_of(message: str) -> str:
    """Rota provável a partir da mensagem de erro — proxy ou direto."""
    if "127.0.0.1" in message or "localhost" in message:
        return "proxy Headroom"
    if "services.ai.azure.com" in message:
        return "direto Foundry"
    if "openai.azure.com" in message:
        return "variante openai.azure"
    return "desconhecida"


def analyze(path: Path, expected_model: str) -> dict[str, Any]:
    """Fatos de saúde de uma sessão. Só leitura, nunca modifica o JSONL."""
    events = list(_iter_events(path))
    started: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    errors: list[dict[str, Any]] = []
    first_ts = events[0].get("timestamp", "") if events else ""
    overflow = False

    for event in events:
        kind = event.get("type", "")
        data = event.get("data") or {}

        if kind == "subagent.started":
            key = str(data.get("toolCallId") or f"{len(order)}")
            started[key] = {
                "agent": data.get("agentName"),
                "model": data.get("model"),
                "tool_calls": None,
                "failed": False,
                "error": None,
                "ts": event.get("timestamp", ""),
            }
            order.append(key)
        elif kind in ("subagent.completed", "subagent.failed"):
            key = str(data.get("toolCallId") or "")
            entry = started.get(key)
            if entry is None:
                # Sem toolCallId casável: atribui ao último aberto do mesmo agente.
                for candidate in reversed(order):
                    if (started[candidate]["agent"] == data.get("agentName")
                            and started[candidate]["tool_calls"] is None):
                        entry = started[candidate]
                        break
            if entry is not None:
                # SEM default: `totalToolCalls` ausente é DESCONHECIDO, não zero.
                # Com `data.get(..., 0)` o evento sem o campo virava "vazio" e o
                # relatório acusava 770 `task` mortos onde havia 10.
                entry["tool_calls"] = data.get("totalToolCalls")
                entry["failed"] = kind == "subagent.failed"
                entry["error"] = data.get("error")
        elif kind == "session.error":
            message = str(data.get("message") or "")
            errors.append({
                "status": data.get("statusCode"),
                "type": data.get("errorType"),
                "message": message,
                "endpoint": _endpoint_of(message),
            })
        elif kind in ("session.compaction_start", "session.truncation"):
            overflow = True

    subagents = [started[k] for k in order]
    foreign = [s for s in subagents if s["model"] and s["model"] != expected_model]
    empty = [s for s in subagents if s["tool_calls"] == 0]
    model_404 = [e for e in errors if e["status"] == 404 and "not found" in e["message"].lower()]

    return {
        "session": path.parent.name,
        "started_at": first_ts,
        "subagents": subagents,
        "total": len(subagents),
        "foreign_model": foreign,
        "empty": empty,
        "model_404": model_404,
        "context_overflow": overflow,
        "healthy": not foreign and not empty and not model_404,
    }


def _pick_sessions(args: argparse.Namespace) -> list[Path]:
    root = session_root()
    if not root.is_dir():
        print(f"❌ diretório de sessões não encontrado: {root}", file=sys.stderr)
        raise SystemExit(2)

    files = sorted(root.glob("*/events.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if args.session:
        files = [f for f in files if f.parent.name.startswith(args.session)]
        if not files:
            print(f"❌ nenhuma sessão casa com {args.session!r}", file=sys.stderr)
            raise SystemExit(2)
        return files
    if args.all:
        return files
    return files[:1]


def _render(reports: list[dict[str, Any]], expected_model: str) -> None:
    by_pair: Counter = Counter()
    empty_by_pair: Counter = Counter()
    unknown_by_pair: Counter = Counter()
    endpoints: Counter = Counter()
    doentes = [r for r in reports if not r["healthy"]]

    for report in reports:
        for sub in report["subagents"]:
            par = (sub["agent"], sub["model"])
            by_pair[par] += 1
            if sub["tool_calls"] == 0:
                empty_by_pair[par] += 1
            elif sub["tool_calls"] is None:
                unknown_by_pair[par] += 1
        for err in report["model_404"]:
            endpoints[err["endpoint"]] += 1

    print(f"🩺 {len(reports)} sessão(ões) · modelo BYOK esperado: {expected_model}\n")

    if by_pair:
        print("   agentName / modelo                        dispatches   sem tool call   sem retorno")
        print("   " + "─" * 82)
        for par, count in by_pair.most_common():
            agent, model = par
            vazio = empty_by_pair[par]
            desconhecido = unknown_by_pair[par]
            alerta = "  ⚠️" if model and model != expected_model else ""
            pct = f"{vazio} ({vazio * 100 // count}%)" if vazio else "—"
            rotulo = f"{agent} / {model}"
            print(f"   {rotulo:<40} {count:>10}   {pct:>13}   {desconhecido or '—':>11}{alerta}")
        print()

    if endpoints:
        print("\n   404 de modelo por rota:")
        for endpoint, count in endpoints.most_common():
            print(f"      {count:>4}  {endpoint}")

    if doentes:
        print(f"\n   Sessões com problema ({len(doentes)} de {len(reports)}):")
        for report in doentes[:12]:
            marcas = []
            if report["foreign_model"]:
                marcas.append(f"{len(report['foreign_model'])} fora do BYOK")
            if report["empty"]:
                marcas.append(f"{len(report['empty'])} vazio(s)")
            if report["model_404"]:
                marcas.append(f"{len(report['model_404'])} 404")
            if report["context_overflow"]:
                marcas.append("context_overflow")
            print(f"      {report['started_at'][:19]}  {report['session'][:8]}  " + " · ".join(marcas))

    print()
    if doentes:
        print(f"❌ {len(doentes)} sessão(ões) com subagente que não produziu nada.")
        print("   Causa conhecida: tipos embutidos ("
              + ", ".join(BUILTIN_FOREIGN_AGENTS)
              + ") trazem modelo próprio;")
        print("   sob BYOK a troca de modelo dispara validação do wire model e retorna 404.")
        print("   Correção: subagents.agents.<nome>.model = \"inherit\" nas settings do CLI.")
    else:
        print("✅ nenhum subagente fora do modelo BYOK e nenhum sem tool call.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="check_session_health.py",
        description="Detecta subagente sem tool call / fora do modelo BYOK numa sessão do Copilot CLI",
    )
    escopo = parser.add_mutually_exclusive_group()
    escopo.add_argument("--all", action="store_true", help="Todas as sessões (default: só a última)")
    escopo.add_argument("--session", help="UUID ou prefixo de uma sessão")
    parser.add_argument("--since", metavar="YYYY-MM-DD",
                        help="Ignora sessões iniciadas antes desta data")
    parser.add_argument("--expect-model", default=DEFAULT_EXPECTED_MODEL,
                        help=f"Modelo BYOK esperado (default: {DEFAULT_EXPECTED_MODEL})")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    reports = [analyze(path, args.expect_model) for path in _pick_sessions(args)]
    if args.since:
        reports = [r for r in reports if (r["started_at"] or "")[:10] >= args.since]
    if not reports:
        print("nenhuma sessão no filtro informado", file=sys.stderr)
        raise SystemExit(2)

    if args.json:
        print(json.dumps({
            "expected_model": args.expect_model,
            "sessions": len(reports),
            "unhealthy": sum(1 for r in reports if not r["healthy"]),
            "reports": reports,
        }, indent=2, ensure_ascii=False))
    else:
        _render(reports, args.expect_model)

    raise SystemExit(1 if any(not r["healthy"] for r in reports) else 0)


if __name__ == "__main__":
    main()
