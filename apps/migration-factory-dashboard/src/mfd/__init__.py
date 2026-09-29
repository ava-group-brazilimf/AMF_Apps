# -*- coding: utf-8 -*-
"""Migration Factory Dashboard — descoberta dinâmica de projetos e métricas."""
from .errors import ConfigurationError, DiscoveryError, MigrationFactoryError
from .models import MetricValue, ProjectRecord, ProjectResult, ProjectStatus, Snapshot

__all__ = [
    "ConfigurationError", "DiscoveryError", "MigrationFactoryError",
    "MetricValue", "ProjectRecord", "ProjectResult", "ProjectStatus", "Snapshot",
]
__version__ = "1.0.0"
