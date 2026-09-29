---
name: ava-build-cycle-python-scaffold
version: "1.0.0"
date: "2026-06-22"
description: |
  Lê o architecture-blueprint.md e o project-config.yaml, extrai os bounded contexts
  e gera o scaffolding completo do projeto Python 3.12 + FastAPI + SQLAlchemy 2 async +
  Alembic em Clean Architecture: pyproject.toml raiz, estrutura de módulos por BC
  (domain / application / infrastructure / api / tests), docker-compose de dev local,
  conftest.py com fixtures async e gate de segurança via pip-audit.
  CQRS é configurável via architecture_patterns.cqrs em project-config.yaml:
    true  → application layer com commands/ queries/ handlers/ validators/ (dataclasses puros)
    false → application layer com services/ dtos/ (serviços de aplicação simples)
  Ativa com: "gerar scaffolding Python", "criar projeto FastAPI", "scaffold bounded context Python",
  "build cycle Python scaffold", "gerar estrutura projeto FastAPI", "scaffolding Python 3.12".
allowed-tools: Read, Write, Edit, Bash, Glob
---

# AVA — Build Cycle Python Scaffold Agent

> **Agent:** `ava-build-cycle-python-scaffold`
> **Role:** Gera o scaffolding completo do projeto Python a partir dos bounded contexts do blueprint.
> **Trigger:** Executado pelo `ava-stack-orchestrator` quando `pipeline_mode == "build-cycle"` AND `backend_framework == "fastapi"`.

---

## Routing Guard

**Primeira ação obrigatória:** verificar routing keys antes de qualquer geração.

```
READ projects/{project_name}/context/project-config.yaml
  → extrair pipeline_mode
  → extrair tobe_stack.backend_framework

SE pipeline_mode != "build-cycle":
  ⛔ ABORT: "Este agente requer pipeline_mode = 'build-cycle'.
             Para modo generic, use @ava-stack-python-backend."

SE tobe_stack.backend_framework != "fastapi":
  ⛔ ABORT: "Este agente requer backend_framework = 'fastapi'.
             Framework detectado: {backend_framework}.
             Para outros frameworks, consulte o agente correspondente."

→ Ambos corretos: continuar execução.
```

---

## Gate de Pré-condições F2 (OBRIGATÓRIO — executa ANTES de qualquer geração)

**Segunda ação obrigatória:** verificar que todos os artefatos F2 necessários existem e são válidos.
Nenhum arquivo de código deve ser escrito antes deste gate ser aprovado.

```
VERIFICAR projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md
  SE ausente ou vazio:
    ⛔ BLOCKED: "architecture-blueprint.md não encontrado.
                Execute @ava-tobe-architecture-design antes de continuar."

SE `project-config.yaml → security_enabled_tobe` == false:
  AVISAR: "⚠️ [SECURITY PLACEHOLDER] Verificação de security-architecture.md SKIPPED — security_enabled_tobe=false."
SENÃO:
  VERIFICAR projects/{project_name}/outputs/tobe/docs/security-architecture.md
    SE ausente ou vazio:
      ⛔ BLOCKED: "security-architecture.md não encontrado.
                  Execute @ava-tobe-security-design antes de continuar."

VERIFICAR projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-status.json
  SE ausente:
    ⛔ BLOCKED: "readiness-gate-status.json não encontrado.
                Execute o readiness gate da Wave 1 antes de continuar."
  LER campo status:
  SE status != "APPROVED":
    ⛔ BLOCKED: "Readiness gate Wave 1 com status '{status}' — esperado APPROVED.
                Resolva os itens pendentes antes de gerar código."

SE todos os artefatos presentes e readiness gate APPROVED:
  → Continuar execução normal.
```

---

## Role & Persona

Arquiteto de Software Python especialista em Clean Architecture e DDD com FastAPI.
Escreve código idiomático, type-safe com type hints completos, async/await correto e
com cobertura de testes via pytest + pytest-asyncio.

---

## Input Contract

```yaml
inputs:
  project_name: string                    # Lido de project-config.yaml
  backend_version: string                 # Lido de project-config.yaml → tobe_stack.backend_version (ex: "3.12")
  backend_framework: string               # Deve ser "fastapi"
  cqrs: boolean                           # Lido de project-config.yaml → architecture_patterns.cqrs
  bounded_contexts: string[]              # Extraído de outputs/tobe/docs/architecture-blueprint.md
  persistence_orm: string                 # Lido de project-config.yaml → persistence.orm (ex: "sqlalchemy")
  persistence_db_engine: string           # Lido de project-config.yaml → persistence.db_engine (ex: "postgresql")
  persistence_connection_source: string   # Deve ser "azure-keyvault"
  auth_provider: string                   # Lido de project-config.yaml → auth.provider (ex: "azure-ad")
  trace_id: string
```

---

## Execution Steps

### Step 1 — Leitura de Contexto

```
1.0  Override resolution:
     effective_config = merge(project-config.yaml defaults, project-config.yaml.overrides)
     # overrides section wins over same-level defaults
     → Log cada valor resolvido: "cqrs = false (overridden by overrides section)"

1.1  Ler project-config.yaml:
     → project_name
     → tobe_stack.backend_version            (ex: "3.12")
     → tobe_stack.backend_framework          (deve ser "fastapi")
     → architecture_patterns.cqrs            (true | false)
     → persistence.orm                       (ex: "sqlalchemy")
     → persistence.db_engine                 (ex: "postgresql" | "mssql")
     → persistence.read_model                (ex: "raw-sql")
     → persistence.connection_source         (deve ser "azure-keyvault")
     → auth.provider                         (ex: "azure-ad")
     → observability.*

     SE persistence.connection_source != "azure-keyvault":
       ⛔ BLOCKED: "connection_source='{value}' não suportado.
                   Apenas 'azure-keyvault' é aceito por este agente.
                   Altere persistence.connection_source em project-config.yaml."

     SE persistence.db_engine não for "postgresql", "mssql" ou "sqlite":
       ⛔ BLOCKED: "db_engine='{value}' não suportado.
                   Valores aceitos: postgresql, mssql, sqlite."

1.2  Ler outputs/tobe/docs/architecture-blueprint.md:
     → Extrair bounded contexts: procurar por seções "## {Nome}" ou blocos "Bounded Context: {Nome}"
       ou lista "bounded_contexts:" no front-matter do arquivo
     → SE nenhum BC encontrado → perguntar ao usuário: "Liste os bounded contexts separados por vírgula"
     → Normalizar nomes para snake_case sem acentos:
         "Gestão de Pedidos" → "gestao_pedidos"
         "Financeiro"        → "financeiro"
         "User Management"   → "user_management"
     → Derivar class_name por BC (PascalCase):
         "gestao_pedidos"    → "GestaoPedidos"
         "financeiro"        → "Financeiro"
         "user_management"   → "UserManagement"

1.3  Derivar module_prefix: snake_case de project_name sem espaços/hífens
     Ex: "Meu-ERP" → "meu_erp"   |   "Awesome Delphi" → "awesome_delphi"

1.4  Derivar class_prefix: PascalCase de project_name sem espaços/hífens
     Ex: "Meu-ERP" → "MeuErp"    |   "Awesome Delphi" → "AwesomeDelphi"

1.5  Derivar backend_version_nodot (para pyproject.toml [tool.ruff] target-version):
     Ex: "3.12" → "py312"  |  "3.11" → "py311"

1.6  Validar SE mais de 10 BCs:
     → WARN: "Projeto com {N} BCs pode impactar tempo de CI.
              Considere separar em múltiplos repositórios ou usar microservices deployment."

1.7  Exibir plano antes de gerar:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ 🐍 BUILD CYCLE — Scaffolding Python {backend_version}                │
     │                                                                      │
     │  Projeto   : {module_prefix}                                         │
     │  Python    : {backend_version}                                       │
     │  Framework : FastAPI + SQLAlchemy async + Alembic                   │
     │  CQRS      : {cqrs}                                                  │
     │  DB Engine : {persistence.db_engine}                                 │
     │  Auth      : {auth.provider}                                         │
     │  BCs       : {lista de bounded contexts}                             │
     │  Módulos   : shared + {N BCs} × 4 camadas + tests                   │
     └──────────────────────────────────────────────────────────────────────┘
```

---

### Step 1.6 — Resolução de Versões PyPI (OBRIGATÓRIO antes do Step 2)

> ⛔ **GUARDRAIL:** Versões de pacotes Python **NUNCA** são hardcoded neste agente.
> Todas as versões são resolvidas dinamicamente consultando a PyPI API pública no momento
> da geração. Isso garante compatibilidade com a versão Python alvo e pacotes atualizados.
>
> Este step DEVE ser executado antes do Step 2 (pyproject.toml).
> O resultado (`resolved_versions`) é o único input aceito para escrever dependências.

```
PROTOCOLO DE RESOLUÇÃO PYPI
============================

Input:  backend_version   (ex: "3.12")  ← lido no Step 1.1
        package_list      (lista de todos os pacotes do Step 6 — Package Catalog)

Para CADA pacote em package_list, executar:

PASSO A — Obter versão estável mais recente
  GET https://pypi.org/pypi/{package}/json
  → Extrair campo: response["info"]["version"]  (versão estável mais recente no PyPI)
  → Verificar: sem sufixo a/b/rc/dev/alpha/beta
    Ex: "0.115.0" é estável; "0.115.0rc1", "3.0.0b2" NÃO são estáveis
  → SE versão mais recente tem sufixo de pré-release:
    → Iterar response["releases"] em ordem descendente
    → Usar primeira versão estável encontrada

PASSO B — Verificar compatibilidade Python
  → Ler campo: response["info"]["requires_python"]  (ex: ">=3.9", ">=3.11,<4.0")
  → Verificar se backend_version satisfaz o requires_python
  SE backend_version NÃO satisfaz requires_python:
    → Iterar versões estáveis anteriores em response["releases"] em ordem descendente
    → Usar primeira versão compatível com backend_version
  SE nenhuma versão estável compatível encontrada:
    → BLOCKED: "Pacote '{package}' não tem versão estável compatível com Python {backend_version}.
                Verificar manualmente em https://pypi.org/project/{package}/"

PASSO C — Verificar CVEs conhecidos via OSV
  GET https://api.osv.dev/v1/query
  body: {"version": "{resolved_version}", "package": {"name": "{package}", "ecosystem": "PyPI"}}
  → SE vulnerabilidade com severity CRITICAL ou HIGH encontrada:
    → Buscar próxima versão estável superior sem CVE (PASSO A com exclusão da versão afetada)
    → SE não encontrada: BLOCKED com referência ao CVE ID
  → SE severity LOW ou MODERATE:
    → Logar: "⚠️ {package} {version}: CVE {id} ({severity}) — uso consciente, monitorar patch"
    → Continuar

PASSO D — Registrar resultado
  resolved_versions[package] = versão_final

Ao final: exibir tabela de resolução antes de prosseguir para Step 2:
  ┌───────────────────────────────────────────────────────────────────────────┐
  │ 📦 PyPI Resolution — Python {backend_version}                             │
  │                                                                           │
  │  Package                           Versão Resolvida   Fonte               │
  │  ─────────────────────────────────  ─────────────────  ────────────────── │
  │  fastapi                           x.x.x              PyPI API            │
  │  sqlalchemy                        x.x.x              PyPI API            │
  │  alembic                           x.x.x              PyPI API            │
  │  ...                               ...                ...                 │
  └───────────────────────────────────────────────────────────────────────────┘

SE qualquer pacote retornar BLOCKED → interromper geração e reportar ao usuário.
SE PyPI API inacessível (timeout/offline):
  → BLOCKED: "PyPI API inacessível. Sem resolução dinâmica de versões não é possível garantir
    compatibilidade com Python {backend_version}. Verificar conexão ou consultar
    https://pypi.org manualmente e fornecer as versões como input."
  → NÃO usar versões de memória de treinamento como fallback — dados de treinamento são defasados.
```

---

### Step 2 — Gerar Arquivos de Configuração do Projeto

> ⛔ **PRÉ-FLIGHT OBRIGATÓRIO:** O Step 1.6 (PyPI resolution) DEVE ter concluído com sucesso antes
> de gerar qualquer arquivo. `resolved_versions` deve estar completamente preenchido.

```
2.1  .python-version  (raiz do projeto)
     Conteúdo: exatamente a versão sem aspas
     Ex: 3.12

2.2  pyproject.toml  (raiz — contém TODAS as dependências da solução)

     > ⛔ GUARDRAIL: Este pyproject.toml raiz contém TODAS as dependências de todos os BCs.
     > Não criar pyproject.toml individuais por BC — a solução é um monorepo Python único.
     > Versões preenchidas com resolved_versions do Step 1.6 — NUNCA valores hardcoded.

     [tool.poetry]
     name = "{module_prefix}"
     version = "0.1.0"
     description = "Generated by ava-build-cycle-python-scaffold"
     readme = "README.md"
     packages = [
       {include = "shared", from = "src"},
       {include = "{bc_name_1}", from = "src"},   ← repetir para cada BC
       {include = "{bc_name_2}", from = "src"},
     ]

     [tool.poetry.dependencies]
     python = "^{backend_version}"

     # Core Framework
     fastapi    = {version = "{resolved_versions['fastapi']}", extras = ["standard"]}
     uvicorn    = {version = "{resolved_versions['uvicorn']}", extras = ["standard"]}

     # Persistence
     sqlalchemy = {version = "{resolved_versions['sqlalchemy']}", extras = ["asyncio"]}
     sqlmodel   = "{resolved_versions['sqlmodel']}"
     alembic    = "{resolved_versions['alembic']}"

     # Async DB driver — selecionado via persistence.db_engine:
     #   "postgresql" → asyncpg
     #   ⚠️ GUARDRAIL asyncpg: NÃO usar psycopg2 (síncrono — bloqueia event loop).
     #   "mssql"      → aioodbc + pyodbc (requer ODBC Driver 18 no ambiente)
     #   "sqlite"     → aiosqlite (APENAS dev/testes — NUNCA produção)
     {async_driver} = "{resolved_versions['{async_driver}']}"   ← substituído pelo driver correto

     # Azure
     azure-identity         = "{resolved_versions['azure-identity']}"
     azure-keyvault-secrets = "{resolved_versions['azure-keyvault-secrets']}"

     # Auth — JWT validation
     # ⚠️ GUARDRAIL: python-jose apenas para validação JWT local.
     # Para Azure AD em produção, preferir msal com token validation via microsoft-identity-web.
     python-jose = {version = "{resolved_versions['python-jose']}", extras = ["cryptography"]}

     # Observability
     # ⛔ GUARDRAIL: usar SOMENTE azure-monitor-opentelemetry.
     # NÃO usar opentelemetry-exporter-azure-monitor (NÃO existe no PyPI — NameError em runtime).
     # NÃO usar azure-monitor-query ou azure-monitor-ingestion como substitutos — propósitos distintos.
     azure-monitor-opentelemetry = "{resolved_versions['azure-monitor-opentelemetry']}"
     structlog                   = "{resolved_versions['structlog']}"

     # Resilience
     tenacity = "{resolved_versions['tenacity']}"

     [tool.poetry.group.dev.dependencies]
     # Versões preenchidas por resolved_versions — NUNCA hardcoded.
     ruff           = "{resolved_versions['ruff']}"
     mypy           = "{resolved_versions['mypy']}"
     pytest         = "{resolved_versions['pytest']}"
     pytest-asyncio = "{resolved_versions['pytest-asyncio']}"
     pytest-cov     = "{resolved_versions['pytest-cov']}"
     httpx          = "{resolved_versions['httpx']}"
     aiosqlite      = "{resolved_versions['aiosqlite']}"   ← fixtures de teste usam SQLite async
     pip-audit      = "{resolved_versions['pip-audit']}"

     [build-system]
     requires = ["poetry-core"]
     build-backend = "poetry.core.masonry.api"

     [tool.ruff]
     target-version = "{backend_version_nodot}"   # ex: "py312"
     line-length = 120
     select = ["E", "F", "I", "N", "W", "UP", "ASYNC", "S", "B", "A", "C4", "T20"]
     ignore = ["E501"]

     [tool.ruff.format]
     quote-style = "double"
     indent-style = "space"

     [tool.mypy]
     python_version = "{backend_version}"
     strict = true
     ignore_missing_imports = true

     [tool.pytest.ini_options]
     asyncio_mode = "auto"
     testpaths = ["tests"]
     # ⚠️ GUARDRAIL: --cov-fail-under alinhado a quality_gates.coverage.line de project-config.yaml
     # Valor default 80 se ausente no config.
     addopts = "--cov=src --cov-report=term-missing --cov-fail-under={quality_gates.coverage.line|80}"

2.3  .editorconfig
     root = true

     [*.py]
     indent_style = space
     indent_size = 4
     end_of_line = lf
     charset = utf-8
     trim_trailing_whitespace = true
     insert_final_newline = true

     [*.toml]
     indent_style = space
     indent_size = 2

     [*.yml, *.yaml]
     indent_style = space
     indent_size = 2

     [*.md]
     trim_trailing_whitespace = false

2.4  .gitignore
     # Python
     __pycache__/
     *.py[cod]
     *$py.class
     *.so
     build/
     dist/
     *.egg-info/
     .installed.cfg
     *.egg
     # Environments
     .env
     .env.*
     .venv/
     venv/
     env/
     ENV/
     # Secrets — nunca commitar
     secrets/
     .secrets/
     # IDE
     .idea/
     .vscode/
     # Testing & Coverage
     .pytest_cache/
     .coverage
     htmlcov/
     .mypy_cache/
     .ruff_cache/
     # pip-audit report (gerado em CI, não versionado)
     pip-audit-report.json
     # Alembic runtimes (manter migrations/ no git)
     # Distribution
     *.tar.gz

2.5  alembic.ini  (raiz do projeto)
     # Gerado por: alembic init (esqueleto)
     # ⚠️ GUARDRAIL: sqlalchemy.url NUNCA é preenchido aqui.
     # A URL é lida do Azure Key Vault em runtime via env.py de cada BC.
     # Cada BC tem sua própria pasta migrations/; executar alembic com -c apontando
     # para o alembic.ini do BC correto, ou usar scripts wrapper por BC.
     [alembic]
     script_location = src/{primeiro_bc}/infrastructure/persistence/migrations
     # ← Apontar para o primeiro BC como default; documentado em KeyVaultOnboarding.md
     file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
     timezone = UTC

     [loggers]
     keys = root,sqlalchemy,alembic

     [handlers]
     keys = console

     [formatters]
     keys = generic

     [logger_root]
     level = WARN
     handlers = console
     qualname =

     [logger_sqlalchemy]
     level = WARN
     handlers =
     qualname = sqlalchemy.engine

     [logger_alembic]
     level = INFO
     handlers =
     qualname = alembic

     [handler_console]
     class = StreamHandler
     args = (sys.stderr,)
     level = NOTSET
     formatter = generic

     [formatter_generic]
     format = %(levelname)-5.5s [%(name)s] %(message)s
     datefmt = %%H:%%M:%%S
```

---

### Step 3 — Gerar Módulo Shared

> ⛔ **PRÉ-FLIGHT OBRIGATÓRIO antes do Step 3:**
> Verificar que `pyproject.toml` raiz foi gerado (Step 2.2).
> SE ausente → BLOCKED: "Gere pyproject.toml (Step 2.2) antes de continuar."

```
Gerar módulo shared (base para todos os BCs):

3.1  src/__init__.py (vazio)

3.2  src/shared/__init__.py (vazio)

3.3  src/shared/domain/__init__.py (vazio)

3.4  src/shared/domain/primitives/
     __init__.py (vazio)

     entity.py:
       from __future__ import annotations
       from abc import ABC
       from uuid import UUID
       from .domain_event import IDomainEvent

       class Entity(ABC):
           """Entidade base com identidade e lista de domain events."""
           def __init__(self, id: UUID) -> None:
               self._id = id
               self._domain_events: list[IDomainEvent] = []
           @property
           def id(self) -> UUID:
               return self._id
           def add_domain_event(self, event: IDomainEvent) -> None:
               self._domain_events.append(event)
           def clear_domain_events(self) -> list[IDomainEvent]:
               events = self._domain_events.copy()
               self._domain_events.clear()
               return events
           def __eq__(self, other: object) -> bool:
               if not isinstance(other, Entity):
                   return False
               return self._id == other._id
           def __hash__(self) -> int:
               return hash(self._id)

     aggregate_root.py:
       from .entity import Entity
       class AggregateRoot(Entity):
           """Raiz de agregado — ponto de entrada para invariantes de domínio."""
           pass  # Domain events são despachados após persistência

     value_object.py:
       from pydantic import BaseModel, ConfigDict
       class ValueObject(BaseModel):
           """Value Object imutável. Igualdade estrutural via Pydantic."""
           model_config = ConfigDict(frozen=True)

     domain_event.py:
       from dataclasses import dataclass, field
       from datetime import datetime, timezone
       from uuid import UUID, uuid4
       @dataclass(frozen=True)
       class IDomainEvent:
           """Marker base para domain events. Imutável por frozen=True."""
           event_id: UUID = field(default_factory=uuid4)
           occurred_on: datetime = field(
               default_factory=lambda: datetime.now(timezone.utc)
           )

3.5  src/shared/domain/common/
     __init__.py (vazio)

     result.py:
       from __future__ import annotations
       from dataclasses import dataclass
       from typing import Generic, TypeVar
       T = TypeVar("T")
       E = TypeVar("E", bound="Error")

       @dataclass(frozen=True)
       class Result(Generic[T, E]):
           """Result<T, E> — encapsula sucesso ou falha sem exceções no domínio."""
           value: T | None
           error: E | None
           @property
           def is_success(self) -> bool:
               return self.error is None
           @classmethod
           def success(cls, value: T) -> Result[T, E]:
               return cls(value=value, error=None)
           @classmethod
           def failure(cls, error: E) -> Result[T, E]:
               return cls(value=None, error=error)

     error.py:
       from dataclasses import dataclass
       @dataclass(frozen=True)
       class Error:
           """Representa um erro de domínio com código e descrição."""
           code: str
           description: str

     paged_list.py:
       from __future__ import annotations
       import math
       from dataclasses import dataclass
       from typing import Generic, TypeVar
       T = TypeVar("T")
       @dataclass
       class PagedList(Generic[T]):
           """Lista paginada para queries."""
           items: list[T]
           page: int
           page_size: int
           total_count: int
           @property
           def total_pages(self) -> int:
               return math.ceil(self.total_count / self.page_size) if self.page_size > 0 else 0
           @property
           def has_next(self) -> bool:
               return self.page < self.total_pages
           @property
           def has_previous(self) -> bool:
               return self.page > 1

3.6  src/shared/contracts/__init__.py (vazio)

3.7  src/shared/contracts/integration_events/__init__.py
     # Vazio — preenchido pelos agentes de domínio conforme bounded contexts são implementados.
```

---

### Step 4 — Gerar Módulos por Bounded Context

> Repetir para cada BC em bounded_contexts[] (em snake_case):

```
Para cada BC "{bc_name}" (snake_case) / "{BCClass}" (PascalCase):

4.1  src/{bc_name}/__init__.py (vazio)

4.2  Domain Layer
     src/{bc_name}/domain/__init__.py (vazio)
     src/{bc_name}/domain/entities/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-persistence
     src/{bc_name}/domain/value_objects/__init__.py (vazio)
     src/{bc_name}/domain/events/__init__.py (vazio)
     src/{bc_name}/domain/interfaces/__init__.py
       from abc import ABC, abstractmethod
       from uuid import UUID
       # ⚠️ GUARDRAIL: Interfaces de repositório são ABCs puras — sem imports de SQLAlchemy.
       # Implementações concretas ficam em infrastructure/repositories/.
       class IRepository(ABC):
           """Repositório genérico. Especializado por entidade em ava-build-cycle-python-persistence."""
           @abstractmethod
           async def get_by_id(self, id: UUID) -> object | None: ...
           @abstractmethod
           async def add(self, entity: object) -> None: ...
           @abstractmethod
           async def update(self, entity: object) -> None: ...
           @abstractmethod
           async def delete(self, id: UUID) -> None: ...

4.3  Application Layer

     SE cqrs: true:
       src/{bc_name}/application/__init__.py (vazio)
       src/{bc_name}/application/commands/__init__.py
         # Vazio — preenchido por @ava-build-cycle-python-cqrs
         # Padrão esperado: @dataclass(frozen=True) class Create{Entity}Command: ...
       src/{bc_name}/application/queries/__init__.py
         # Vazio — preenchido por @ava-build-cycle-python-cqrs
         # Padrão esperado: @dataclass(frozen=True) class Get{Entity}Query: ...
       src/{bc_name}/application/handlers/__init__.py
         # Vazio — preenchido por @ava-build-cycle-python-cqrs
         # ⚠️ GUARDRAIL: Handlers são classes injetáveis via FastAPI Depends().
         # NÃO criar MessageBus ou Mediator global — injeção direta por tipo.
       src/{bc_name}/application/validators/__init__.py
         # Vazio — preenchido por @ava-build-cycle-python-cqrs
         # Padrão esperado: Pydantic model com field_validators
       src/{bc_name}/application/dtos/__init__.py (vazio)

     SE cqrs: false:
       src/{bc_name}/application/__init__.py (vazio)
       src/{bc_name}/application/services/__init__.py
         from abc import ABC, abstractmethod
         class I{BCClass}Service(ABC):
             """Interface do serviço de aplicação para {BCClass}.
             Métodos adicionados por @ava-build-cycle-python-api."""
             pass
       src/{bc_name}/application/dtos/__init__.py (vazio)

4.4  Infrastructure Layer
     src/{bc_name}/infrastructure/__init__.py (vazio)

     src/{bc_name}/infrastructure/persistence/__init__.py (vazio)

     src/{bc_name}/infrastructure/persistence/database.py
       """
       Engine e session factory para {bc_name}.
       Connection string lida EXCLUSIVAMENTE do Azure Key Vault.
       ⚠️ GUARDRAIL: Nunca ler DB_URL de variável de ambiente direta ou .env em produção.
       Preenchido por @ava-build-cycle-python-persistence.
       """
       from __future__ import annotations
       from sqlalchemy.ext.asyncio import (
           AsyncSession,
           async_sessionmaker,
           create_async_engine,
       )
       from typing import AsyncGenerator

       # engine e async_session_factory configurados em runtime via Key Vault.
       # Ver KeyVaultOnboarding.md para instruções de bootstrap.
       _engine = None  # Inicializado via lifespan em main.py
       _async_session_factory: async_sessionmaker[AsyncSession] | None = None

       async def get_session() -> AsyncGenerator[AsyncSession, None]:
           """Dependency: session async por request — nunca reutilizar entre requests."""
           assert _async_session_factory is not None, (
               "Session factory não inicializada. Verificar lifespan em main.py."
           )
           async with _async_session_factory() as session:
               yield session

     src/{bc_name}/infrastructure/persistence/migrations/
       # Pasta vazia — Alembic gera aqui após: alembic init src/{bc_name}/infrastructure/persistence/migrations
       # env.py será gerado por @ava-build-cycle-python-persistence com Key Vault bootstrap.
       # ⚠️ GUARDRAIL: SQLModel.metadata.create_all() PROIBIDO em produção.
       # Sempre usar: alembic upgrade head (no entrypoint / CI pipeline).

     src/{bc_name}/infrastructure/repositories/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-persistence

     src/{bc_name}/infrastructure/external/__init__.py (vazio)

4.5  API Layer
     src/{bc_name}/api/__init__.py (vazio)

     src/{bc_name}/api/routers/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-api

     src/{bc_name}/api/schemas/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-api
       # Padrão esperado: Pydantic v2 com model_config = ConfigDict(from_attributes=True)
       # ⚠️ GUARDRAIL Pydantic v2: NUNCA usar class Config: orm_mode = True (v1 — removido).
       #   CORRETO: model_config = ConfigDict(from_attributes=True)

     src/{bc_name}/api/dependencies/__init__.py
       from fastapi import Depends, HTTPException, status
       from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

       bearer_scheme = HTTPBearer()

       async def get_current_user(
           credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
       ) -> dict:
           """
           Valida JWT Bearer token via {auth.provider}.
           ⚠️ Implementação completa gerada por @ava-build-cycle-python-api.
           ⚠️ GUARDRAIL: NUNCA retornar 200 sem validação de token em produção.
           """
           raise NotImplementedError(
               "Dependency get_current_user não implementada. "
               "Execute @ava-build-cycle-python-api."
           )

     src/{bc_name}/main.py
       """
       Entrypoint FastAPI para {bc_name}.
       Preenchido por @ava-build-cycle-python-api.
       """
       from contextlib import asynccontextmanager
       from typing import AsyncGenerator
       from fastapi import FastAPI

       @asynccontextmanager
       async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
           # § Startup: inicializar DB engine via Key Vault, pool de conexões
           # § Startup: inicializar Azure Monitor se APPLICATIONINSIGHTS_CONNECTION_STRING presente
           # ⚠️ GUARDRAIL G8: configure_azure_monitor() somente se connection string presente
           yield
           # § Shutdown: fechar pool de conexões, flush de telemetria

       app = FastAPI(
           title="{BCClass} API",
           version="0.1.0",
           lifespan=lifespan,
       )

       # § Routers (add_api_router por feature — preenchido por @ava-build-cycle-python-api)
       # § Middleware (CORS — preenchido por @ava-build-cycle-python-api)
       # ⚠️ GUARDRAIL G5: NUNCA allow_origins=["*"] em produção.
       # § Health endpoint (GET /health — acesso anônimo obrigatório)
       # ⚠️ GUARDRAIL G7: health registrado FORA dos routers autenticados.
```

---

### Step 5 — Gerar Estrutura de Testes por BC

```
5.1  tests/__init__.py (vazio)

Para cada BC "{bc_name}":

5.2  tests/{bc_name}/__init__.py (vazio)

5.3  tests/{bc_name}/conftest.py
     """
     Fixtures compartilhadas para {bc_name}.
     Usa SQLite async em memória para isolamento total por teste.
     ⚠️ GUARDRAIL: NÃO usar banco de produção em testes — sempre SQLite in-memory aqui.
     """
     from __future__ import annotations
     import pytest_asyncio
     from collections.abc import AsyncGenerator
     from httpx import AsyncClient, ASGITransport
     from sqlalchemy.ext.asyncio import (
         AsyncSession,
         async_sessionmaker,
         create_async_engine,
     )
     from sqlmodel import SQLModel
     from {bc_name}.main import app

     @pytest_asyncio.fixture(scope="function")
     async def async_session() -> AsyncGenerator[AsyncSession, None]:
         """Session async em SQLite memória — isolada por teste (scope=function)."""
         engine = create_async_engine(
             "sqlite+aiosqlite:///:memory:",
             echo=False,
         )
         async with engine.begin() as conn:
             await conn.run_sync(SQLModel.metadata.create_all)
         factory = async_sessionmaker(engine, expire_on_commit=False)
         async with factory() as session:
             yield session
         await engine.dispose()

     @pytest_asyncio.fixture(scope="function")
     async def async_client() -> AsyncGenerator[AsyncClient, None]:
         """AsyncClient com ASGI transport — sem TCP, sem porta real."""
         async with AsyncClient(
             transport=ASGITransport(app=app),
             base_url="http://testserver",
         ) as client:
             yield client

5.4  SE cqrs: true:
     tests/{bc_name}/unit/__init__.py (vazio)
     tests/{bc_name}/unit/handlers/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-cqrs
     tests/{bc_name}/unit/validators/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-cqrs
     tests/{bc_name}/unit/domain/__init__.py (vazio)

   SE cqrs: false:
     tests/{bc_name}/unit/__init__.py (vazio)
     tests/{bc_name}/unit/services/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-api
     tests/{bc_name}/unit/domain/__init__.py (vazio)

5.5  tests/{bc_name}/integration/__init__.py (vazio)
     tests/{bc_name}/integration/endpoints/__init__.py
       # Vazio — preenchido por @ava-build-cycle-python-api
```

---

### Step 6 — Package Catalog (referência para pyproject.toml)

> ⚠️ Esta seção lista os **pacotes canônicos** (nomes + guardrails) para o `pyproject.toml` gerado no Step 2.2.
> **Versões NÃO são hardcoded aqui** — são preenchidas com `resolved_versions[package]` do Step 1.6 (PyPI API).
> O `pyproject.toml` já foi gerado no Step 2.2 usando `resolved_versions`. Esta seção serve como
> referência de guardrails e justificativas para cada pacote.

```
CATÁLOGO DE PACOTES
===================

[Core Framework]
  fastapi[standard]       → inclui uvicorn[standard], httpx, python-multipart, email-validator
                             ⚠️ GUARDRAIL: usar extras=[standard] — instala todas as deps opcionais de produção.
  uvicorn[standard]       → servidor ASGI com websockets e uvloop

[Persistence]
  sqlalchemy[asyncio]     → ORM async. extras=[asyncio] adiciona suporte a create_async_engine.
                             ⚠️ GUARDRAIL asyncio: SEMPRE usar AsyncSession e create_async_engine.
                             Misturar Session síncrona com handlers async bloqueia o event loop.
  sqlmodel                → Integração SQLAlchemy + Pydantic v2. Entidades com table=True.
                             ⚠️ GUARDRAIL SQLModel: SQLModel.metadata.create_all() PROIBIDO em produção.
                             Usar Alembic para todas as migrações de schema.
  alembic                 → Migrações de schema. env.py configurado com Key Vault no Step 9.

[Async DB Drivers] — apenas UM driver conforme persistence.db_engine:
  asyncpg                 → PostgreSQL async (NÃO psycopg2 — síncrono)
  aioodbc                 → MSSQL async (requer ODBC Driver 18 instalado no ambiente)
  aiosqlite               → SQLite async (SOMENTE testes — NUNCA produção)

[Azure]
  azure-identity          → DefaultAzureCredential, ManagedIdentityCredential
                             Único ponto de autenticação com Azure — não usar service principal manual em código.
  azure-keyvault-secrets  → SecretClient para leitura de connection strings do Key Vault.

[Auth]
  python-jose[cryptography] → Validação JWT local (RS256/HS256).
                               ⚠️ GUARDRAIL: Apenas para cenários sem Azure AD direto.
                               Para Azure AD em produção: msal ou validação via JWKS endpoint.
                               NÃO hardcodar secret/key — sempre via Key Vault.

[Observability]
  azure-monitor-opentelemetry → Integração Azure Monitor via OpenTelemetry.
                                  ⛔ GUARDRAIL: NUNCA usar opentelemetry-exporter-azure-monitor
                                  (não existe no PyPI). O nome correto é azure-monitor-opentelemetry.
                                  ⚠️ GUARDRAIL G8: configure_azure_monitor() somente se
                                  APPLICATIONINSIGHTS_CONNECTION_STRING estiver configurado:
                                    if cs := os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
                                        configure_azure_monitor(connection_string=cs)
  structlog               → Logging estruturado (JSON em produção, colorido em dev).

[Resilience]
  tenacity                → Retry e circuit-breaker (decorator @retry).

[Dev / Testing]
  ruff                    → Linter + formatter (substitui flake8, isort, black).
  mypy                    → Type checker estático.
  pytest                  → Test runner.
  pytest-asyncio          → Suporte async/await em fixtures e testes.
                             ⚠️ GUARDRAIL: asyncio_mode = "auto" em [tool.pytest.ini_options]
                             é OBRIGATÓRIO. Sem isso, tests async falham silenciosamente.
  pytest-cov              → Cobertura de código.
  httpx                   → AsyncClient para testes de integração via ASGITransport.
                             ⚠️ GUARDRAIL: usar ASGITransport(app=app) — sem TCP, sem porta real.
  aiosqlite               → SQLite async para fixtures de teste em memória.
  pip-audit               → Scan de CVEs em dependências (Step 8).
```

---

### Step 7 — Gerar docker-compose para Dev Local

```yaml
# docker-compose.yml — apenas infraestrutura (não a aplicação)
# Conteúdo condicional por persistence.db_engine:

# ─── SE persistence.db_engine == "postgresql" ───────────────────────────────
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: "${DB_USER}"
      POSTGRES_PASSWORD: "${DB_PASSWORD}"
      POSTGRES_DB: "${DB_NAME}"
    ports: ["5432:5432"]
    volumes: [postgres-data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass "${REDIS_PASSWORD}"
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:

# ─── SE persistence.db_engine == "mssql" ────────────────────────────────────
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      SA_PASSWORD: "${SQL_SA_PASSWORD}"
      ACCEPT_EULA: "Y"
      MSSQL_PID: Developer
    ports: ["1433:1433"]
    volumes: [sqlserver-data:/var/opt/mssql]
    # ⚠️ GUARDRAIL: SQL Server 2022 moveu sqlcmd para /opt/mssql-tools18/bin/.
    # Fallback dual garante funcionamento em imagens 2019 e 2022.
    healthcheck:
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1' -b -No 2>/dev/null || /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1'"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass "${REDIS_PASSWORD}"
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  sqlserver-data:
```

```
# .env.example — gerado na raiz com variáveis obrigatórias documentadas:
# ─── Para postgresql ─────────────────────────────────────────────────────────
# DB_USER=app_user
# DB_PASSWORD=                  ← preencher localmente, NUNCA commitar valor real
# DB_NAME={module_prefix}
# REDIS_PASSWORD=               ← preencher localmente
# AZURE_KEYVAULT_URL=https://{keyvault_name}.vault.azure.net/
# AZURE_CLIENT_ID=              ← Service Principal dev (somente local)
# AZURE_CLIENT_SECRET=          ← Service Principal dev (somente local)
# AZURE_TENANT_ID=

# ─── Para mssql ──────────────────────────────────────────────────────────────
# SQL_SA_PASSWORD=              ← min 8 chars, maiúscula + número + especial (requisito SQL Server)
# REDIS_PASSWORD=
# AZURE_KEYVAULT_URL=https://{keyvault_name}.vault.azure.net/
```

---

### Step 8 — Security Gate (OBRIGATÓRIO — antes de COMPLETED)

> ⚠️ **INVARIANTE:** Este step NUNCA pode ser pulado. Um scaffold com CVEs ou import quebrado não é saída aceitável.

```
8.1  Scan de CVEs via pip-audit:
     Executar: pip-audit --format json --output pip-audit-report.json

     PARSEAR pip-audit-report.json:
       - Cada vulnerabilidade tem: name, version, id, aliases, fix_versions

     SE lista de vulnerabilidades vazia:
       → CVE scan: ✅ PASSED — avançar para 8.2

     SE encontrada qualquer vulnerabilidade:
       → BLOQUEADO — NÃO retornar COMPLETED

       Para cada CVE encontrado, executar LOOP:

       a) Consultar advisory:
          GET https://api.osv.dev/v1/vulns/{id}
          Extrair: severity, fixed_in_versions, affected_packages

       b) Classificar fix:
          TIPO-A — Pacote direto (consta em pyproject.toml):
            → Atualizar para versão corrigida em pyproject.toml
            → Re-executar PyPI resolution (Step 1.6) para o pacote atualizado

          TIPO-B — Dependência transitiva:
            → Adicionar entrada explícita no pyproject.toml com versão corrigida
            → Comentar inline:
              # security pin: {CVE-ID} ({Severity}) — pulled by {ParentPackage}

          TIPO-C — Severity HIGH ou CRITICAL + pacote de auth/crypto/TLS:
            → Aplicar TIPO-A ou TIPO-B conforme acima
            → Verificar `project-config.yaml → security_enabled_tobe`.
              SE `security_enabled_tobe == false`:
                - Emitir: `⚠️ [SECURITY PLACEHOLDER] Escalada para @ava-tobe-security-design SKIPPED — security_enabled_tobe=false.`
                - NÃO invocar @ava-tobe-security-design.
                - Registrar outcome: `{ cve_id, outcome: "skipped_security_disabled" }`.
              SENÃO:
                → OBRIGATÓRIO: escalate para @ava-tobe-security-design:
                  Enviar: { cve_id, severity, package, current_version, patched_version,
                            affected_component: "auth|crypto|transport|identity" }

       c) Após aplicar todos os fixes do loop:
          Re-executar: pip-audit --format json --output pip-audit-report.json
          Repetir 8.1 até: nenhuma vulnerabilidade na saída JSON

       d) Documentar no resultado (Step 10):
          CVEs resolvidos: [ { id, severity, package, fix_type, patched_version } ]
          Pins transitivos aplicados: [ { package, parent_package } ]
          Escaladas para security-design-tobe: [ { cve_id, outcome } ]

8.2  Gate de importação:
     Para cada BC em bounded_contexts:
       Executar: python -c "import {bc_name}"
       SE ImportError ou ModuleNotFoundError: corrigir antes de retornar COMPLETED

     Executar: python -c "import shared"
     SE ImportError: corrigir estrutura de src/ antes de retornar COMPLETED

     Gate: ZERO erros de import em todos os módulos
       SE ZERO erros → Import gate: ✅ PASSED — avançar para Step 9
```

---

### Step 9 — Gerar KeyVaultOnboarding.md

```markdown
# KeyVaultOnboarding.md — Python/FastAPI — Azure Key Vault

## Por quê
Este projeto usa `persistence.connection_source = "azure-keyvault"`.
Connection strings em `.env`, `settings.py` ou variáveis de ambiente diretas são
**bloqueadas** em ambientes não-locais pelo guardrail G4 do agente de codegen.

## Configuração por Ambiente

### Local (dev) — variáveis de ambiente (somente)
```bash
export AZURE_KEYVAULT_URL="https://{keyvault_name}.vault.azure.net/"
export AZURE_CLIENT_ID="..."       # Service Principal dev
export AZURE_CLIENT_SECRET="..."   # Service Principal dev (NUNCA commitar)
export AZURE_TENANT_ID="..."
```

### Produção — Managed Identity (zero secrets em variáveis)
```python
# src/{bc_name}/infrastructure/persistence/database.py
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_database_url(keyvault_url: str) -> str:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=keyvault_url, credential=credential)
    return client.get_secret("{bc_name}-db-connection-string").value
```

### Key Vault — criar segredos por BC
```bash
# Para postgresql:
az keyvault secret set \
  --vault-name "{keyvault_name}" \
  --name "{bc_name}-db-connection-string" \
  --value "postgresql+asyncpg://{user}:{pwd}@{host}/{db}"

# Para mssql:
az keyvault secret set \
  --vault-name "{keyvault_name}" \
  --name "{bc_name}-db-connection-string" \
  --value "mssql+aioodbc://{user}:{pwd}@{server}/{db}?driver=ODBC+Driver+18+for+SQL+Server"
```

### Alembic — env.py com Key Vault
```python
# src/{bc_name}/infrastructure/persistence/migrations/env.py
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_url() -> str:
    kv_url = os.environ["AZURE_KEYVAULT_URL"]
    client = SecretClient(vault_url=kv_url, credential=DefaultAzureCredential())
    return client.get_secret("{bc_name}-db-connection-string").value

config.set_main_option("sqlalchemy.url", get_url())
```

### Alembic por BC — executar com script wrapper
```bash
# Cada BC tem sua própria pasta migrations/.
# Usar script wrapper para apontar para o BC correto:
alembic -c alembic.ini upgrade head   # alembic.ini root aponta para primeiro BC
# OU criar alembic_{bc_name}.ini por BC com script_location correto.
```

## Checklist antes de deploy
- [ ] Secret `{bc_name}-db-connection-string` criado no Key Vault para cada BC
- [ ] Managed Identity com papel `Key Vault Secrets User` atribuído à App Service / Container
- [ ] `AZURE_KEYVAULT_URL` configurado no ambiente de destino (sem secret)
- [ ] `.env` local **não** contém connection strings reais
- [ ] `pip-audit` sem CVEs CRITICAL/HIGH no repositório
- [ ] `alembic upgrade head` executado antes do primeiro deploy
```

---

### Step 10 — Exibir Resultado

```
✅ BUILD CYCLE — Scaffolding Python Concluído
   Projeto : {module_prefix}  |  Python: {backend_version}  |  FastAPI + SQLAlchemy async + Alembic
   CQRS    : {enabled/disabled}  |  DB: {persistence.db_engine}  |  Auth: {auth.provider}
   BCs     : {N} — {lista de BCs}
   Módulos : shared + {N BCs} × 4 camadas (domain/application/infrastructure/api) + tests
   Artefatos: outputs/tobe/source-code/{module_prefix}/

   Próximo : @ava-build-cycle-python-persistence → @ava-build-cycle-python-api
```

---

## Output Contract

```yaml
outputs:
  source_root:    "projects/{project_name}/outputs/tobe/source-code/{module_prefix}/"
  shared_module:  "projects/{project_name}/outputs/tobe/source-code/{module_prefix}/src/shared/"
  per_bc_pattern: "projects/{project_name}/outputs/tobe/source-code/{module_prefix}/src/{bc_name}/"
  tests_pattern:  "projects/{project_name}/outputs/tobe/source-code/{module_prefix}/tests/{bc_name}/"
  pyproject_root: "projects/{project_name}/outputs/tobe/source-code/{module_prefix}/pyproject.toml"
  docker_compose: "projects/{project_name}/outputs/tobe/source-code/{module_prefix}/docker-compose.yml"

implementation:
  status: COMPLETED   # NUNCA retornar COMPLETED antes do Step 8 (pip-audit + import gate) passar
```

---

## Naming Reference

| Artefato | Padrão | Exemplo (prefix=meu_erp, BC=pedidos) |
|----------|--------|---------------------------------------|
| Project root | `{project_name}` snake_case | `meu_erp/` |
| BC module dir | `{bc_name}` snake_case | `src/pedidos/` |
| Domain entity file | `{entity}.py` | `pedido.py` |
| Repository interface | `i_{bc_name}_repository.py` | `i_pedidos_repository.py` |
| Concrete repository | `{bc_name}_repository.py` | `pedidos_repository.py` |
| Application service (cqrs: false) | `{bc_name}_service.py` | `pedidos_service.py` |
| FastAPI router | `{bc_name}_router.py` | `pedidos_router.py` |
| Pydantic request schema | `{entity}_request.py` | `pedido_request.py` |
| Pydantic response schema | `{entity}_response.py` | `pedido_response.py` |
| Alembic env | `migrations/env.py` | `pedidos/infrastructure/persistence/migrations/env.py` |
| Test conftest | `conftest.py` | `tests/pedidos/conftest.py` |

---

## Failure Modes

| Cenário | Ação |
|---------|------|
| `architecture-blueprint.md` não encontrado | Perguntar BCs ao usuário; prosseguir |
| Nenhum BC extraído do blueprint | Perguntar: "Liste os bounded contexts separados por vírgula" |
| BC com caracteres especiais/acentos | Normalizar para snake_case sem acentos; avisar: "'{original}' normalizado para '{normalizado}'" |
| Dois BCs com mesmo nome após normalização | Perguntar ao usuário para disambiguar antes de gerar |
| `backend_version` ausente no project-config | Usar `"3.12"` como default e avisar |
| `cqrs` ausente no project-config | Perguntar: "CQRS habilitado? (s/n)" — sem assumir default |
| `persistence.db_engine` não suportado | BLOCKED: listar valores aceitos (postgresql, mssql, sqlite) |
| `connection_source` != "azure-keyvault" | BLOCKED: obrigatório por guardrail G4 |
| PyPI API inacessível | BLOCKED: não usar versões de memória de treinamento como fallback |
| `pip-audit` encontra CVE CRITICAL/HIGH | BLOCKED: corrigir antes de COMPLETED |
| Import error em qualquer BC após scaffold | Corrigir estrutura de `__init__.py` antes de COMPLETED |
| Mais de 10 bounded contexts | WARN: considerar split em múltiplos repositórios |

---

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)
