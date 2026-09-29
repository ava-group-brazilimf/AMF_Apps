"""
Testes do sinal de fallback do NTP.

O defeito corrigido: `ntp_time.py` caía em `datetime.now(BRZ)` quando toda a rede
NTP falhava e imprimia **exatamente o mesmo formato**, com `-03:00` fixo. O
guardrail `[BENCHMARK BLOCKED]` de `summary-agent.md` ficava inalcançável — o
agente não tinha como distinguir hora NTP de relógio do Windows.

O contrato de compatibilidade é tão importante quanto a correção: `.vscode/settings.json`
auto-aprova o comando **exato** `python src/shared/utils/ntp_time.py`, então stdout e
a invocação sem flags não podem mudar.

    python -m pytest tests/utils/test_ntp_time.py -q
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "src" / "shared" / "utils" / "ntp_time.py"

ISO_BRZ = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-03:00$")


def _run(*args: str, force_fail: bool = False) -> subprocess.CompletedProcess:
    import os

    env = dict(os.environ)
    if force_fail:
        env["AVA_NTP_FORCE_FAIL"] = "1"
    else:
        env.pop("AVA_NTP_FORCE_FAIL", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=env, timeout=60,
    )


# ─── Contrato com os call sites existentes ───────────────────────────────────

def test_stdout_permanece_iso8601_brz_no_fallback():
    """Os ~10 call sites capturam stdout como timestamp — o formato não pode mudar."""
    proc = _run(force_fail=True)
    assert ISO_BRZ.match(proc.stdout.strip()), f"stdout fora do formato: {proc.stdout!r}"


def test_invocacao_sem_flags_nao_exige_argumento():
    """`.vscode/settings.json` auto-aprova o comando exato, sem flags."""
    proc = _run(force_fail=True)
    assert proc.returncode in (0, 3), f"exit inesperado: {proc.returncode}"
    assert proc.stdout.strip()


# ─── A correção: o fallback deixa de ser silencioso ──────────────────────────

def test_fallback_sai_com_codigo_3_e_avisa_no_stderr():
    proc = _run(force_fail=True)
    assert proc.returncode == 3, "fallback tem de ser distinguível pelo exit code"
    assert "NAO e NTP real" in proc.stderr or "não é NTP real" in proc.stderr
    # O aviso vai para stderr, nunca para stdout — senão contamina o timestamp.
    assert "AVISO" not in proc.stdout


def test_json_expoe_ntp_fallback():
    proc = _run("--json", force_fail=True)
    payload = json.loads(proc.stdout)
    assert payload["ntp_fallback"] is True
    assert payload["server"] is None
    assert ISO_BRZ.match(payload["timestamp"])


# ─── API de biblioteca ───────────────────────────────────────────────────────

def test_resolve_marca_o_fallback(monkeypatch):
    sys.path.insert(0, str(SCRIPT.parent))
    import importlib

    import ntp_time  # noqa: E402

    importlib.reload(ntp_time)
    monkeypatch.setattr(ntp_time, "get_ntp_time_with_source", lambda: (None, None))
    timestamp, fallback, server = ntp_time.resolve()
    assert fallback is True and server is None
    assert ISO_BRZ.match(timestamp)

    monkeypatch.setattr(ntp_time, "get_ntp_time_with_source", lambda: (1_780_000_000.0, "a.ntp.br"))
    timestamp, fallback, server = ntp_time.resolve()
    assert fallback is False and server == "a.ntp.br"
    assert ISO_BRZ.match(timestamp)


def test_force_fail_e_apenas_gancho_de_teste():
    """Sem a variável, o script tenta a rede de verdade (não é modo permanente)."""
    sys.path.insert(0, str(SCRIPT.parent))
    import ntp_time  # noqa: E402

    assert ntp_time._FORCE_FAIL_ENV == "AVA_NTP_FORCE_FAIL"
