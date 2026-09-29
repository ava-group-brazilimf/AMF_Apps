# -*- coding: utf-8 -*-
"""Configuração de log da aplicação (§7.15)."""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: str = "INFO", fmt: str | None = None) -> logging.Logger:
    """Configura o logger raiz do pacote uma única vez."""
    global _CONFIGURED
    logger = logging.getLogger("mfd")
    if not _CONFIGURED:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt or "%(asctime)s %(levelname)-7s %(name)s | %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
        _CONFIGURED = True
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    return logger
