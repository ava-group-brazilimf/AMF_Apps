#!/usr/bin/env python3
"""
mcp_server.py — MCP server interno da tool Headroom (transporte stdio).

Expõe as operações de contexto do AVA Fabric como ferramentas MCP, para que o
host (VSCode / Copilot Chat / Claude Code) as chame direto, sem `Bash:`.
Registrado em ``.vscode/mcp.json`` como servidor ``ava-headroom``.

Ferramentas expostas
--------------------
``headroom_slice``     fatia de artefatos + tokens de um agente (barato, sem LLM)
``headroom_compress``  comprime um texto/JSON via motor Headroom
``headroom_decode``    decodifica um artefato do formato Headroom
``headroom_stats``     agregado das métricas de compressão de um projeto
``headroom_retrieve``  lê um artefato AST já decodificado

Complementaridade com o proxy
-----------------------------
Este servidor é **sob demanda**: comprime o que for pedido explicitamente.
Para comprimir *todas* as requisições, o proxy 8787 continua sendo obrigatório
(invariante I3) — ver ``run_standalone.ps1`` e ``copilot-cli-headroom.bat``.

Execução
--------
    src/shared/tools/headroom/.venv/Scripts/python.exe \\
        src/shared/tools/headroom/mcp_server.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import headroom_config as hcfg  # noqa: E402
import headroom_context as hctx  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - mcp vem em requirements.txt[mcp]
    print("mcp não instalado — rode src/shared/tools/headroom/setup.ps1 "
          "(headroom-ai[mcp])", file=sys.stderr)
    sys.exit(2)

mcp = FastMCP("ava-headroom")


@mcp.tool()
def headroom_slice(project: str, agent_id: str, language: str | None = None) -> str:
    """Devolve a fatia de artefatos AST que um agente consome e o custo em tokens.

    Fonte canônica: ``AGENT_ARTIFACT_SLICE`` em ``context_budget.py``. Use antes
    de despachar um agente — nenhum agente deve receber o payload completo.
    """
    context = hctx.build_agent_context(project, agent_id, language, include_payloads=False)
    return json.dumps(context, ensure_ascii=False, indent=2)


@mcp.tool()
def headroom_retrieve(project: str, artifact: str, language: str | None = None) -> str:
    """Lê um artefato AST de ``compressed/`` já decodificado.

    ``artifact`` é o nome sem extensão, ex.: ``04_database_schemas``.
    """
    doc = hctx.read_artifact(project, artifact, language)
    if not doc:
        return json.dumps(
            {"error": f"artefato '{artifact}' não encontrado para o projeto '{project}'"},
            ensure_ascii=False)
    return json.dumps(doc, ensure_ascii=False, indent=2)


@mcp.tool()
def headroom_decode(content: str) -> str:
    """Decodifica um JSON no formato Headroom (tabular do SmartCrusher ou factored_array)."""
    try:
        doc = json.loads(content)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"JSON inválido: {exc}"}, ensure_ascii=False)
    return json.dumps(hctx.decode_headroom(doc), ensure_ascii=False, indent=2)


@mcp.tool()
def headroom_compress(content: str, project: str | None = None,
                      model: str | None = None) -> str:
    """Comprime um texto ou JSON via motor Headroom.

    Devolve ``{content, tokens_before, tokens_after, savings_pct, transforms}``.
    Sem o motor instalado, devolve o conteúdo intacto com ``applied: false``
    (degradar, nunca bloquear — invariante IV3).
    """
    cfg = hcfg.load_config(project)
    if not hctx.HEADROOM_AVAILABLE:
        return json.dumps({"content": content, "applied": False,
                           "reason": "headroom-ai indisponível — rode setup.ps1"},
                          ensure_ascii=False)

    from headroom import CompressConfig, compress  # noqa: PLC0415

    ccfg: dict[str, Any] = cfg.get("compress", {})
    try:
        doc = json.loads(content)
        wrapped, is_json = json.dumps([doc], ensure_ascii=False), True
    except json.JSONDecodeError:
        wrapped, is_json = content, False

    result = compress(
        [{"role": "user", "content": wrapped}],
        model=model or str(cfg.get("model", "claude-sonnet-4-6")),
        model_limit=int(cfg.get("context_limit", 200000)),
        config=CompressConfig(
            compress_user_messages=bool(ccfg.get("compress_user_messages", True)),
            protect_recent=int(ccfg.get("protect_recent", 0)),
            min_tokens_to_compress=int(ccfg.get("min_tokens_to_compress", 250)),
            target_ratio=ccfg.get("target_ratio"),
        ),
    )
    out = result.messages[-1]["content"]
    if not isinstance(out, str):
        out = json.dumps(out, ensure_ascii=False)
    if is_json:
        try:
            parsed = json.loads(out)
            if isinstance(parsed, list) and len(parsed) == 1:
                out = json.dumps(parsed[0], ensure_ascii=False)
        except json.JSONDecodeError:
            pass

    before, after = result.tokens_before, result.tokens_after
    return json.dumps({
        "content": out,
        "applied": True,
        "tokens_before": before,
        "tokens_after": after,
        "savings_pct": round(100.0 * (1 - after / before), 1) if before else 0.0,
        "transforms": list(result.transforms_applied),
    }, ensure_ascii=False)


@mcp.tool()
def headroom_stats(project: str) -> str:
    """Agregado das métricas de compressão gravadas para o projeto."""
    cfg = hcfg.load_config(project)
    path = hcfg.metrics_path(project, cfg)
    if not path.is_file():
        return json.dumps({"project": project, "calls": 0,
                           "detail": "nenhuma métrica registrada ainda"}, ensure_ascii=False)

    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total_in = sum(int(r.get("original_tokens") or 0) for r in records)
    total_out = sum(int(r.get("compressed_tokens") or 0) for r in records)
    return json.dumps({
        "project": project,
        "calls": len(records),
        "original_tokens": total_in,
        "compressed_tokens": total_out,
        "tokens_saved": max(0, total_in - total_out),
        "savings_pct": round(100.0 * (1 - total_out / total_in), 1) if total_in else 0.0,
        "errors": sum(1 for r in records if r.get("error")),
        "metrics_file": str(path),
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
