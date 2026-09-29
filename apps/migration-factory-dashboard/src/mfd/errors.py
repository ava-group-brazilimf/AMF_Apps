# -*- coding: utf-8 -*-
"""Exceções da aplicação."""
from __future__ import annotations


class MigrationFactoryError(Exception):
    """Base de todos os erros previstos da aplicação."""


class ConfigurationError(MigrationFactoryError):
    """Configuração ausente ou inválida — falha controlada (§5.2)."""


class DiscoveryError(MigrationFactoryError):
    """Falha ao listar o diretório raiz de projetos (§7)."""
