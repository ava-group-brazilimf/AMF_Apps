# -*- coding: utf-8 -*-
"""Ponto de entrada de desenvolvimento.

    python run.py
    MIGRATION_FACTORY_PROJECTS_ROOT=/outro/caminho python run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mfd.config import load_app_config, load_metrics_config   # noqa: E402
from mfd.errors import ConfigurationError                     # noqa: E402
from mfd.logging_setup import setup_logging                   # noqa: E402
from mfd.web import create_app                                # noqa: E402


def main() -> int:
    try:
        config = load_app_config()
    except ConfigurationError as exc:
        print("Falha de configuração: %s" % exc, file=sys.stderr)
        return 2
    setup_logging(config.logging_level, config.logging_format)
    app = create_app(config, load_metrics_config())
    server = config.server or {}
    app.run(host=str(server.get("host", "127.0.0.1")),
            port=int(server.get("port", 5000)),
            debug=bool(server.get("debug", False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
