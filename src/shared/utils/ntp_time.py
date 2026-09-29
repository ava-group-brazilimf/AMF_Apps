"""
ntp_time.py — Returns current timestamp as ISO8601 UTC-3 queried from Brazilian NTP servers.

Usage: python src/shared/utils/ntp_time.py
Output example: 2026-05-07T14:32:11-03:00

Por que o fallback agora é AUDÍVEL
----------------------------------
Até então, quando os 8 servidores NTP falhavam, o script caía em
``datetime.now(BRZ)`` e imprimia **exatamente o mesmo formato**, com o ``-03:00``
fixo na string. Não havia flag, aviso nem código de saída diferente.

Consequência: o guardrail de ``summary-agent.md`` — *"SE a chamada NTP falhar →
ABORT + [BENCHMARK BLOCKED]"* — era **inalcançável**, porque o agente não tinha
como distinguir hora NTP de relógio do Windows. Um relatório podia afirmar
"timestamps NTP reais" contendo hora local.

Contrato de compatibilidade (não quebrar)
-----------------------------------------
``.vscode/settings.json`` auto-aprova o comando **exato**
``^python src/shared/utils/ntp_time\\.py$``. Portanto:

* **stdout permanece idêntico** na invocação sem flags — os ~10 call sites em
  ``.md`` de agente continuam funcionando sem alteração;
* o fallback sinaliza por **stderr** e por **exit code 3** — quem ignora o código
  de saída não muda de comportamento;
* ``--json`` é opcional e expõe ``ntp_fallback`` explicitamente, no formato que
  ``specs/002-qa-local-pipeline/research.md`` já especificava.

Exit codes: 0 hora NTP real · 3 fallback para relógio local.
"""
import json
import os
import socket
import struct
import sys
from datetime import datetime, timezone, timedelta

NTP_SERVERS = [
    "a.st1.ntp.br",
    "b.st1.ntp.br",
    "c.st1.ntp.br",
    "a.ntp.br",
    "b.ntp.br",
    "c.ntp.br",
    "br.pool.ntp.org",
    "ntp.cais.rnp.br",
]

NTP_EPOCH_DELTA = 2208988800  # seconds between 1900-01-01 and 1970-01-01
NTP_PORT = 123
TIMEOUT_SECONDS = 3

BRZ = timezone(timedelta(hours=-3))

#: Código de saída do fallback. Não é 1: 1 já significa "erro de execução" para
#: quem chama, e degradar para o relógio local não é erro — é um resultado pior,
#: que precisa ser distinguível.
EXIT_FALLBACK = 3

#: Gancho de teste — força a falha de todos os servidores sem derrubar a rede.
_FORCE_FAIL_ENV = "AVA_NTP_FORCE_FAIL"


def query_ntp(host: str) -> float:
    """Query a single NTP server. Returns Unix timestamp (float)."""
    packet = b'\x1b' + b'\x00' * 47  # LI=0, VN=3, Mode=3 (client)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT_SECONDS)
        sock.sendto(packet, (host, NTP_PORT))
        data, _ = sock.recvfrom(1024)
    if len(data) < 48:
        raise ValueError(f"Response too short: {len(data)} bytes")
    # Transmit Timestamp field starts at byte 40 (two 32-bit big-endian integers)
    seconds, fraction = struct.unpack("!II", data[40:48])
    return (seconds - NTP_EPOCH_DELTA) + fraction / 2**32


def get_ntp_time() -> float | None:
    """Try each NTP server in order. Returns None if all fail."""
    if os.environ.get(_FORCE_FAIL_ENV):
        return None
    for server in NTP_SERVERS:
        try:
            return query_ntp(server)
        except Exception:
            continue
    return None


def get_ntp_time_with_source() -> tuple[float | None, str | None]:
    """``(unix_time, servidor)``. ``(None, None)`` quando todos falham."""
    if os.environ.get(_FORCE_FAIL_ENV):
        return None, None
    for server in NTP_SERVERS:
        try:
            return query_ntp(server), server
        except Exception:
            continue
    return None, None


def resolve() -> tuple[str, bool, str | None]:
    """``(timestamp ISO8601 BRZ, houve_fallback, servidor)``."""
    unix_time, server = get_ntp_time_with_source()
    fallback = unix_time is None
    moment = (datetime.now(BRZ) if fallback
              else datetime.fromtimestamp(unix_time, tz=BRZ))
    return moment.strftime("%Y-%m-%dT%H:%M:%S-03:00"), fallback, server


def main() -> int:
    as_json = "--json" in sys.argv[1:]
    timestamp, fallback, server = resolve()

    if as_json:
        print(json.dumps({
            "timestamp": timestamp,
            "ntp_fallback": fallback,
            "server": server,
        }, ensure_ascii=False))
    else:
        # stdout INALTERADO — é o contrato com os ~10 call sites e com a
        # auto-aprovação do .vscode/settings.json.
        print(timestamp)

    if fallback:
        print(
            "AVISO: nenhum dos servidores NTP respondeu; usando o relogio local. "
            "O timestamp NAO e NTP real.",
            file=sys.stderr,
        )
        return EXIT_FALLBACK
    return 0


if __name__ == "__main__":
    sys.exit(main())
