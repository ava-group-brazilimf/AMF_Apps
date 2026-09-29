#!/usr/bin/env python3
"""
f4_baseline.py — Baseline de compilação do scaffold, antes da primeira task.

O que isto responde
-------------------
"O scaffold já compilava antes de eu mexer?" — sem essa resposta, um erro
preexistente vira culpa da task. Medido em `cadastro-funcionario-03`:
`T-W0-SCF-004` só criava um `.gitignore` e foi bloqueada por
`dotnet build ... -warnaserror` reprovar o **scaffold**, não a task.

O baseline roda **uma vez por componente**, é guardado em
`outputs/tobe/source-code/.f4s/baseline-{componente}.json` e reusado nas tasks
seguintes do mesmo componente.

O que ele nunca faz
-------------------
Recriar o scaffold. Se o diretório do componente não existir ou estiver vazio,
o baseline devolve `scaffold_missing` e quem chamou decide — a política é
registrar erro estrutural e seguir com as demais tasks, nunca gerar projeto
novo por cima.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import f4s_build_runner as build_runner  # noqa: E402

BASELINE_DIR = ".f4s"

#: Linhas de erro/aviso das toolchains suportadas. Contagem, não parsing fino:
#: o que importa é "quantos erros havia antes" versus "quantos há agora".
_ERROR_LINE = re.compile(
    r"(:\s*error\s|^\s*error\s|\bERROR\b|\bERR!\b|error TS\d+|error CS\d+)",
    re.IGNORECASE | re.MULTILINE)
_WARNING_LINE = re.compile(
    r"(:\s*warning\s|^\s*warning\s|\bWARN\b|warning TS\d+|warning CS\d+)",
    re.IGNORECASE | re.MULTILINE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def count_errors(saida: str) -> int:
    return len(_ERROR_LINE.findall(saida or ""))


def count_warnings(saida: str) -> int:
    return len(_WARNING_LINE.findall(saida or ""))


def baseline_path(repo: Path, component_type: str) -> Path:
    return Path(repo) / BASELINE_DIR / f"baseline-{component_type}.json"


def load(repo: Path, component_type: str) -> dict[str, Any] | None:
    caminho = baseline_path(repo, component_type)
    if not caminho.is_file():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save(repo: Path, component_type: str, dados: dict[str, Any]) -> Path:
    caminho = baseline_path(repo, component_type)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return caminho


def scaffold_present(work_dir: Path) -> bool:
    """O scaffold existe e tem conteúdo? Nada além disso é inferido."""
    caminho = Path(work_dir)
    if not caminho.is_dir():
        return False
    return any(item.name not in {".keep", ".gitkeep"} for item in caminho.iterdir())


def ensure(repo: Path, work_dir: Path, component_type: str, stack: str, *,
           timeout: int = 900, refresh: bool = False) -> dict[str, Any]:
    """Baseline do componente — do cache, ou medido agora.

    Devolve sempre um dicionário com `scaffoldPath`, `scaffoldPresent`,
    `baselineBuildCommand`, `baselineBuildExitCode`, `baselineErrors`,
    `baselineWarnings` e os timestamps. Nunca levanta por falha de build: um
    scaffold que não compila é um fato a registrar, não um motivo para parar.
    """
    if not refresh:
        cache = load(repo, component_type)
        if cache:
            return cache

    presente = scaffold_present(work_dir)
    registro: dict[str, Any] = {
        "component_type": component_type,
        "stack": stack,
        "scaffoldPath": Path(work_dir).as_posix(),
        "scaffoldPresent": presente,
        "scaffoldReused": presente,
        "scaffoldRecreated": False,
        "baselineBuildCommand": "",
        "baselineBuildExitCode": None,
        "baselineBuildStartedAt": None,
        "baselineBuildFinishedAt": None,
        "baselineBuildDuration": 0.0,
        "baselineErrors": 0,
        "baselineWarnings": 0,
        "status": "scaffold_missing",
        "measured_at": _now(),
    }
    if not presente:
        save(repo, component_type, registro)
        return registro

    inicio = time.time()
    registro["baselineBuildStartedAt"] = _now()
    try:
        resultado = build_runner.run_build(Path(work_dir), stack, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — baseline nunca derruba a fase
        registro.update({
            "status": "baseline_unavailable",
            "baselineBuildCommand": f"<erro: {type(exc).__name__}>",
            "baselineBuildExitCode": None,
            "baselineBuildFinishedAt": _now(),
            "baselineBuildDuration": round(time.time() - inicio, 2),
            "detail": str(exc)[:500],
        })
        save(repo, component_type, registro)
        return registro

    saida = (resultado.get("stdout") or "") + (resultado.get("stderr") or "")
    registro.update({
        "baselineFailureSignature": failure_signature(resultado),
        "baselineBuildCommand": resultado.get("command", ""),
        "baselineBuildExitCode": resultado.get("exit_code"),
        "baselineBuildFinishedAt": _now(),
        "baselineBuildDuration": round(time.time() - inicio, 2),
        "baselineErrors": count_errors(saida),
        "baselineWarnings": count_warnings(saida),
        "toolchain_missing": resultado.get("toolchain_missing", ""),
        "status": ("green" if resultado.get("exit_code") == 0
                   else "toolchain_missing" if resultado.get("toolchain_missing")
                   else "red"),
    })
    save(repo, component_type, registro)
    return registro


#: Ruído que muda entre execuções e não distingue uma falha de outra.
_RUIDO = re.compile(
    r"(\d+[.,]\d+\s*s(ec)?\b)|(\d{2}:\d{2}:\d{2})|([A-Za-z]:\\[^\s\"]+)|(/[^\s\"]+/)"
    r"|(\b\d{4}-\d{2}-\d{2}T[\d:.+-]+)|(\b0x[0-9a-f]+\b)",
    re.IGNORECASE)


def failure_signature(build_result: dict[str, Any]) -> str:
    """Impressão digital de uma falha de build: exit code + linhas de erro.

    Existe porque contar linhas com "error" **não** distingue falhas: um
    `verify_dotnet_solution.py` que reprova por prerequisito ou estrutura sai
    com exit 10/20 e **zero** linhas de erro. Comparar 0 com 0 fazia o pipeline
    concluir "não introduziu erro novo" para builds que nunca rodaram — e
    integrar 18 tasks como sucesso sem um único build verde
    (`cadastro-funcionario-03`).
    """
    if not build_result:
        return ""
    exit_code = build_result.get("exit_code")
    if exit_code == 0:
        return ""
    saida = ((build_result.get("stdout") or "")
             + (build_result.get("stderr") or ""))
    linhas = [_RUIDO.sub("", linha).strip()
              for linha in saida.splitlines()
              if _ERROR_LINE.search(linha) or "fail" in linha.lower()]
    corpo = "\n".join(sorted(set(linhas))[:20]) or _RUIDO.sub("", saida.strip())[:400]
    digest = hashlib.sha1(corpo.encode("utf-8", "replace")).hexdigest()[:12]
    return f"{exit_code}:{digest}"


def compare(baseline: dict[str, Any], build_result: dict[str, Any]) -> dict[str, Any]:
    """A task introduziu erro novo, ou herdou o que já estava quebrado?

    Regra, em ordem:

    1. build passou (exit 0) → nada introduzido, integrável;
    2. baseline verde e build falhou → **a task introduziu**, não integrável;
    3. baseline vermelho e a falha atual tem a MESMA assinatura da do baseline →
       é a mesma falha preexistente: não introduzida, integrável, e a task
       **não pode** ser declarada verificada (o componente não compila);
    4. baseline vermelho e assinatura diferente → falha diferente da conhecida.
       Isso é tratado como introduzida: presumir o contrário é o que deixava
       passar erro novo em cima de um scaffold já quebrado.
    """
    saida = (build_result.get("stdout") or "") + (build_result.get("stderr") or "")
    erros_agora = count_errors(saida)
    erros_antes = int((baseline or {}).get("baselineErrors", 0) or 0)
    status_baseline = (baseline or {}).get("status", "unknown")
    exit_code = build_result.get("exit_code")
    assinatura = failure_signature(build_result)
    assinatura_baseline = str((baseline or {}).get("baselineFailureSignature") or "")

    if exit_code == 0:
        introduziu, integravel, mesma = False, True, False
    elif status_baseline == "green":
        introduziu, integravel, mesma = True, False, False
    else:
        mesma = bool(assinatura) and assinatura == assinatura_baseline
        introduziu = not mesma
        integravel = mesma

    return {
        "errorsBefore": erros_antes,
        "errorsAfter": erros_agora,
        "warningsAfter": count_warnings(saida),
        "baselineStatus": status_baseline,
        "failureSignature": assinatura,
        "baselineFailureSignature": assinatura_baseline,
        "samePreexistingFailure": mesma,
        "introducedNewErrors": introduziu,
        # Integrável ≠ verificado. A task pode ser integrada quando não piorou o
        # quadro; `verified` continua exigindo exit code 0 de um build real.
        "integrable": integravel,
        "buildPassed": exit_code == 0,
    }
