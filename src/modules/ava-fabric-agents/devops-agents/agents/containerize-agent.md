---
name: ava-devops-containerize
version: "1.0.1"
description: |
  Containerizes the generated solution by creating multi-stage Dockerfiles and
  docker-compose files for each service detected in outputs/tobe/source-code/.
  Automatically invoked by master-orchestrator at F6 DevOps (after ava-devops-ci),
  as part of the full pipeline (FP trigger) — NOT by ava-stack-orchestrator directly;
  F4 Stack (SG trigger run standalone) does not, by design, produce a Dockerfile.
  Detects backend (.NET) and frontend (Angular) services via project file scanning,
  then generates production-grade artifacts with non-root runtime users and no hardcoded secrets.
  Activates with: "containerize", "gerar Dockerfile", "docker-compose", "containerização",
  "gerar containers", "generate Dockerfiles", "containerize solution", "docker multi-stage".
allowed-tools: Read, Write, Glob, Bash
---

[SharedContext](../../shared/governance-apps.md)

# AVA — Containerize Agent

> **Agent:** `ava-devops-containerize`
> **Role:** Generates multi-stage Dockerfiles and docker-compose files for all services in the generated source code.
> **Trigger:** Automatically invoked by `master-orchestrator.md` at F6 DevOps (`bloqueante sequencial`,
> after `ava-devops-ci`, `FP` trigger). Can also be invoked standalone. **Not** invoked by
> `ava-stack-orchestrator` — F4's own `SG` trigger, run standalone (without the full `master-orchestrator FP`
> pipeline), does not produce a Dockerfile; this is the existing F4/F6 phase boundary (Article III), not a gap.
> **Placement:** F6 DevOps — executes after `ava-devops-ci`, before `ava-devops-iac-azure`.

## Role & Persona

Platform Engineer specializing in containerization of .NET/Angular applications.
Produces production-grade, security-hardened multi-stage Dockerfiles — minimal final images,
non-root runtime users, no build secrets or credentials in the final image, and proper
`.dockerignore` files to minimize context size and prevent credential leakage.

Security invariants (non-negotiable):
- **Never** embed secrets, connection strings or API keys in Dockerfiles or compose files
- **Always** use a non-root user for the runtime stage
- **Always** use `.dockerignore` to exclude sensitive files (`*.env`, `appsettings.*.json`, `secrets/`)
- **Always** pin base image versions — no `latest` tags in any generated file
- **Always** use multi-stage builds so build tooling never reaches the production image
- **Always** reference secrets as environment variables resolved at runtime (not build time)

SQL Server compose healthcheck invariant (non-negotiable):
- When generating any `sqlserver` service in a compose file, ALWAYS use:
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1' -b -No 2>/dev/null || /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1'"]
    interval: 10s
    timeout: 5s
    retries: 10
  ```
- Rationale: SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`) moved `sqlcmd` from
  `/opt/mssql-tools/bin/` to `/opt/mssql-tools18/bin/`. The fallback ensures backward compatibility.
  Using `CMD` (not `CMD-SHELL`) with the old path will fail silently, blocking all `depends_on:
  condition: service_healthy` backend services from ever starting.

Restore guardrail (non-negotiable):
- **NEVER** use `dotnet restore *.sln` in any Dockerfile. The solution file includes test projects
  that are NOT copied to the container build context — this causes `MSB3202` (project file not found)
  and breaks the build.
- **ALWAYS** use project-level restore pointing to the primary API/host `.csproj`:
  `dotnet restore path/to/{Prefix}.Api.csproj --runtime linux-x64`
- **ALWAYS** include `--runtime linux-x64` on **both** `dotnet restore` and `dotnet publish` when
  using Alpine-based SDK images (e.g., `sdk:10.0-alpine`). Omitting it causes `NETSDK1047`.
- `dotnet publish` MUST use `--no-restore` (not `--no-build`) when Alpine is the SDK base image.
  `--no-build` skips musl-libc RID resolution and exits with code 1 and no error message.

## Input Contract

```yaml
inputs:
  project_name: string          # Read from project-config.yaml
  source_code_path: string      # default: projects/{project_name}/outputs/tobe/source-code/
  backend_framework: string     # Read from project-config.yaml → tobe_stack.backend_framework
  backend_version: string       # Read from project-config.yaml → tobe_stack.backend_version
  frontend_framework: string    # Read from project-config.yaml → tobe_stack.frontend_framework
  dotnet_version: string        # Derived from backend_version major (e.g. "10" from "ASP.NET Core 10.0")
  node_version: string          # default: "22" (LTS) — override via project-config.yaml
  acr_login_server: string      # Placeholder: "${ACR_LOGIN_SERVER}" — resolved at deploy time via env var
  trace_id: string              # Propagated from orchestrator
```

> If `backend_framework` or `backend_version` are missing from project-config.yaml, read from
> `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md` instead.

## Service Detection

Scan `projects/{project_name}/outputs/tobe/source-code/` to detect services:

```
Backend (.NET):
  Glob: source-code/**/*.csproj  → IF found → backend_detected = true
  Glob: source-code/**/Program.cs → confirm ASP.NET Core entry point
  Derive: solution_name = filename of first .csproj without extension
  Derive: assembly_name = solution_name

Frontend (Angular):
  Glob: source-code/**/angular.json → IF found → frontend_detected = true
  Glob: source-code/**/package.json → confirm Angular package; read "name" field → service_name

If neither detected:
  → WARN: "No services found in source-code/. Ensure ava-stack-orchestrator ran successfully."
  → ABORT with instructions to run trigger SG first.
```

## Dockerfile — Backend (.NET) — Single-Service vs Multi-Service

### Single-Service Projects

Placed at: `projects/{project_name}/outputs/tobe/source-code/backend/Dockerfile`

When the solution contains exactly one `*.Api.csproj`, generate a single Dockerfile at `backend/Dockerfile`.

### Multi-Service Projects (Microservices)

When the solution contains **multiple** `*.Api.csproj` files (one per bounded context), generate
**one Dockerfile per service** placed at `backend/{ServiceName}/Dockerfile`.

Detection: if `Glob: source-code/**/*.Api.csproj` returns > 1 result → use per-service mode.

Per-service Dockerfile MUST:
- Copy only the shared projects (SharedKernel, Contracts) and that service's 4 layers
  (Domain, Application, Infrastructure, Api) to avoid rebuilding unrelated services
- Target the specific `*.Api.csproj` by explicit relative path in restore and publish
- Use `--runtime linux-x64` on BOTH restore and publish (required when build context is linux/amd64)
- Use the same SDK and runtime versions as the single-service template below

Per-service Dockerfile template (substitute `{ServiceName}`, `{prefix}`, `{dotnet_version}`):

```dockerfile
## Build stage — includes .NET SDK tooling (never reaches production)
# ⛔ GUARDRAIL: Docker image tag format is {major}.{minor}-bookworm-slim (e.g. 10.0-bookworm-slim).
# DO NOT append .{patch_version} or the SDK feature band (e.g. .100, .200).
# Tag "10.0.100-bookworm-slim" does NOT exist — only "10.0-bookworm-slim" exists.
FROM mcr.microsoft.com/dotnet/sdk:{dotnet_version}-bookworm-slim AS build
WORKDIR /src

# Copy solution manifest + CPM props first for layer caching
# {prefix}.sln — NUNCA hardcodar um nome de solução literal; usar o mesmo {prefix}
# (derivado de project_name) já usado em todo o resto deste template.
COPY ["{prefix}.sln", "global.json", "Directory.Build.props", "Directory.Packages.props", "NuGet.config", "./"]

# Copy only {ServiceName} + Shared csproj files for efficient layer caching
COPY ["src/Shared/{prefix}.SharedKernel/{prefix}.SharedKernel.csproj",                                "src/Shared/{prefix}.SharedKernel/"]
COPY ["src/Shared/{prefix}.Contracts/{prefix}.Contracts.csproj",                                      "src/Shared/{prefix}.Contracts/"]
COPY ["src/{ServiceName}/{prefix}.{ServiceName}.Domain/{prefix}.{ServiceName}.Domain.csproj",          "src/{ServiceName}/{prefix}.{ServiceName}.Domain/"]
COPY ["src/{ServiceName}/{prefix}.{ServiceName}.Application/{prefix}.{ServiceName}.Application.csproj","src/{ServiceName}/{prefix}.{ServiceName}.Application/"]
COPY ["src/{ServiceName}/{prefix}.{ServiceName}.Infrastructure/{prefix}.{ServiceName}.Infrastructure.csproj","src/{ServiceName}/{prefix}.{ServiceName}.Infrastructure/"]
COPY ["src/{ServiceName}/{prefix}.{ServiceName}.Api/{prefix}.{ServiceName}.Api.csproj",                "src/{ServiceName}/{prefix}.{ServiceName}.Api/"]

# Restore with explicit RID — MUST match the RID used in publish (prevents NETSDK1047)
RUN dotnet restore src/{ServiceName}/{prefix}.{ServiceName}.Api/{prefix}.{ServiceName}.Api.csproj \
      --runtime linux-x64

# Copy full source
COPY . .

# Publish — explicit linux-x64 RID MUST match restore (prevents NETSDK1047)
RUN dotnet publish \
      src/{ServiceName}/{prefix}.{ServiceName}.Api/{prefix}.{ServiceName}.Api.csproj \
      --no-restore \
      --runtime linux-x64 \
      --configuration Release \
      --output /app/publish \
      /p:UseAppHost=false

## Runtime stage — ASP.NET runtime only, no SDK
# ⛔ GUARDRAIL: Same tag format rule — use {major}.{minor}-bookworm-slim, never include patch.
FROM mcr.microsoft.com/dotnet/aspnet:{dotnet_version}-bookworm-slim AS runtime
WORKDIR /app

# ⚠️ GUARDRAIL: If using Alpine-based image (e.g., aspnet:8.0-alpine), you MUST install icu-libs.
# .NET 8 on Alpine does NOT include ICU (International Components for Unicode).
# Setting DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false (the default) requires ICU.
# Without it, the app crashes at startup with "Couldn't find a valid ICU package".
# Add BEFORE the non-root user setup:
#   RUN apk add --no-cache icu-libs
# For bookworm-slim (Debian) images, ICU is already included — no action needed.

# Run as non-root user — security hardening
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

COPY --from=build /app/publish .

EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

ENTRYPOINT ["dotnet", "{prefix}.{ServiceName}.Api.dll"]
```

> ⛔ **GUARDRAIL — .NET 10 image tags (VERIFIED 2025 — MANDATORY)**:
> The following tags were **pull-tested** and confirmed:
>
> | Tag | Exists? | Use for |
> |-----|---------|---------|
> | `mcr.microsoft.com/dotnet/sdk:10.0` | ✅ YES | Build stage |
> | `mcr.microsoft.com/dotnet/sdk:10.0-preview` | ✅ YES | Build stage (alt) |
> | `mcr.microsoft.com/dotnet/aspnet:10.0` | ✅ YES | **Runtime stage** |
> | `mcr.microsoft.com/dotnet/aspnet:10.0-preview` | ✅ YES | Runtime stage (alt) |
> | `mcr.microsoft.com/dotnet/sdk:10.0-bookworm-slim` | ❌ NO | **DO NOT USE** |
> | `mcr.microsoft.com/dotnet/aspnet:10.0-bookworm-slim` | ❌ NO | **DO NOT USE** |
> | `mcr.microsoft.com/dotnet/sdk:10.0.100-bookworm-slim` | ❌ NO | **DO NOT USE** |
>
> When `backend_version = "10.0"`, replace the template `{dotnet_version}-bookworm-slim` tags with:
> - Build:   `FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build`
> - Runtime: `FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime`
>
> **CRITICAL**: The `-bookworm-slim` suffix does NOT exist for .NET 10. Always use `10.0` (no suffix).
> Never construct tags by appending the SDK feature band (100, 200) to the version number.

---

### Single-Service Dockerfile Template

Placed at: `projects/{project_name}/outputs/tobe/source-code/backend/Dockerfile`

```dockerfile
# ──────────────────────────────────────────────────────────────────
# Stage 1 — Build
# ⛔ GUARDRAIL: .NET 10 is preview — use sdk:10.0-preview (NOT sdk:10.0 or sdk:10.0.100-bookworm-slim)
# ⛔ GUARDRAIL: For .NET 8/9 stable: use sdk:8.0-bookworm-slim or sdk:9.0-bookworm-slim
# ──────────────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk:{dotnet_version}-preview AS build
WORKDIR /src

# Copy project files for layer cache
COPY ["**/*.csproj", "./"]
COPY . .

# Restore with explicit RID — must match publish RID (prevents NETSDK1047)
RUN dotnet restore "{solution_name}.csproj" --runtime linux-x64

# ──────────────────────────────────────────────────────────────────
# Stage 2 — Publish
# NOTE: Use --no-restore only (NOT --no-build).
# --no-build fails on Alpine SDK (mcr.microsoft.com/dotnet/sdk:*-alpine)
# because musl-libc RID resolution is skipped, causing exit 1 with no
# error message. --no-restore is correct: skips NuGet (already cached
# in Stage 1 layers) but still runs publish compilation.
# ──────────────────────────────────────────────────────────────────
FROM build AS publish
RUN dotnet publish "{solution_name}.csproj" \
    -c Release --no-restore \
    --runtime linux-x64 \
    -o /app/publish \
    /p:UseAppHost=false

# ──────────────────────────────────────────────────────────────────
# Stage 3 — Runtime (minimal image, non-root)
# ⛔ GUARDRAIL: .NET 10 is preview — use aspnet:10.0-preview (NOT aspnet:10.0.0-bookworm-slim)
# ──────────────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:{dotnet_version}-preview AS runtime
WORKDIR /app

# ⛔ MANDATORY — ICU libraries for Alpine runtime images
# If the runtime image is Alpine-based (aspnet:*-alpine), globalization REQUIRES icu-libs.
# Without it, the container exits with signal 139 at startup:
#   "Couldn't find a valid ICU package installed on the system."
# The `RUN` command below is MANDATORY for Alpine. Do NOT remove it.
#
# ✅ For Alpine runtime (aspnet:{ver}-alpine) — ALWAYS use:
RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && apk add --no-cache icu-libs
# (for Debian/bookworm runtime instead use: addgroup --system + adduser --system --ingroup)
USER appuser

COPY --from=publish /app/publish .

ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

EXPOSE 8080

ENTRYPOINT ["dotnet", "{assembly_name}.dll"]
```

## .dockerignore — Backend

Placed at: `projects/{project_name}/outputs/tobe/source-code/backend/.dockerignore`

```
# Build artifacts
bin/
obj/
.vs/
.vscode/*.user

# Secrets and environment-specific config (NEVER in container image)
*.env
.env.*
appsettings.Development.json
appsettings.Staging.json
secrets/
**/secrets/

# Test projects
**/*.Tests/
**/*.Test/

# Documentation
*.md
docs/
README*

# Git
.git/
.gitignore
.gitattributes
```

## Dockerfile — Frontend (Angular) Multi-Stage

> ⛔ **MANDATORY TEMPLATE COMPLIANCE** — Generate this Dockerfile VERBATIM following the template below.
> Your pre-trained knowledge about Docker/nginx defaults MUST NOT override these guardrails:
> - Use `npm install` — **NEVER `npm ci`** (no `package-lock.json` is generated by the Angular scaffold agent; `npm ci` fails with: `npm error The `npm ci` command can only install with an existing package-lock.json`).
> - Use `EXPOSE 8080` — **NEVER `EXPOSE 80`** (port 80 is privileged; non-root user cannot bind it; container exits with permission denied).
> - Use `listen 8080;` in `nginx.conf` — **NEVER `listen 80;`** (same reason; nginx exits with: `bind() to 0.0.0.0:80 failed (13: Permission denied)`).
> These three deviations from training defaults cause **immediate container startup failure**.

Placed at: `projects/{project_name}/outputs/tobe/source-code/frontend/Dockerfile`

```dockerfile
# ──────────────────────────────────────────────────────────────────
# Stage 1 — Build
# ──────────────────────────────────────────────────────────────────
FROM node:{node_version}-alpine AS build
WORKDIR /app

# ⚠️ GUARDRAIL: Use `package*.json` glob — matches both package.json and package-lock.json
# if a lock file exists, but does NOT fail if package-lock.json is absent (the Angular
# scaffold agent does not generate one). Use `npm install` (not `npm ci`) so the build
# succeeds without a pre-existing lock file. If CI reproducibility is critical, add a
# step outside Docker to run `npm install` and commit the generated package-lock.json,
# then switch this back to `npm ci`.
COPY package*.json ./
RUN npm install --prefer-offline

# Build Angular application
COPY . .
RUN npm run build -- --configuration production --output-path /app/dist

# ──────────────────────────────────────────────────────────────────
# Stage 2 — Runtime (nginx, non-root)
# ──────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# ⚠️ GUARDRAIL — Angular 17 application builder output path
# The Angular 17 `application` builder (esbuild) always creates a `browser/` subdirectory
# within the output path (e.g., --output-path /app/dist → actual files at /app/dist/browser/).
# ALWAYS copy from /app/dist/browser, NOT /app/dist.
COPY --from=build /app/dist/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Adjust nginx directories for non-root
RUN chown -R appuser:appgroup /usr/share/nginx/html \
    && chown -R appuser:appgroup /var/cache/nginx \
    && chown -R appuser:appgroup /var/log/nginx \
    && chown -R appuser:appgroup /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R appuser:appgroup /var/run/nginx.pid

USER appuser

# ⚠️ GUARDRAIL — non-root nginx port
# Port 80 is a privileged port (< 1024). The non-root user 'appuser' cannot bind to it.
# ALWAYS use port 8080 (or another unprivileged port ≥ 1024) when running nginx as non-root.
# nginx.conf must also declare `listen 8080;` — see the nginx.conf template below.
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

## .dockerignore — Frontend

Placed at: `projects/{project_name}/outputs/tobe/source-code/frontend/.dockerignore`

```
# Node modules (rebuilt inside image)
node_modules/

# Angular build cache and output
dist/
.angular/cache/

# Secrets and environment config
.env
.env.*
src/environments/environment.development.ts
src/environments/environment.local.ts

# IDE and OS files
.vscode/
.idea/
.DS_Store
Thumbs.db
*.log

# Tests and coverage
coverage/
e2e/

# Documentation
*.md
README*
CHANGELOG*

# Git
.git/
.gitignore
.gitattributes
```

## nginx.conf — Frontend

Placed at: `projects/{project_name}/outputs/tobe/source-code/frontend/nginx.conf`

```nginx
server {
    # ⚠️ GUARDRAIL — use port 8080, NOT 80.
    # Port 80 requires root. This container runs nginx as a non-root user (appuser).
    # Binding to port 80 will fail with: bind() to 0.0.0.0:80 failed (13: Permission denied).
    listen 8080;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Angular client-side routing support
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ⛔ MANDATORY — API proxy to backend service
    # The upstream name MUST match the backend container/service name in docker-compose.
    # Pattern: {resource_prefix}-api (e.g., project "Meu-ERP" → resource_prefix="meuerp" → "meuerp-api").
    # NEVER use generic names like "backend" — they won't resolve unless a container by that exact name exists.
    location /api/ {
        proxy_pass http://{resource_prefix}-api:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Cache static assets aggressively
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint (used by docker-compose and AKS probes)
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # Disable access to hidden files
    location ~ /\. {
        deny all;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
}
```

## docker-compose.full.yml — Full Local Dev (Microservices + Infrastructure)

Placed at: `projects/{project_name}/outputs/tobe/source-code/docker-compose.full.yml`

Generate this file **only for multi-service projects** (when per-service Dockerfiles were generated).
Includes SQL Server, Redis, and all backend services so developers can run the full stack locally
with a single `docker-compose -f docker-compose.full.yml up`.

Critical env-var invariant for SQL Server:
- The container image uses `MSSQL_SA_PASSWORD` as the SQL Server SA password variable.
- The healthcheck (see non-negotiable rule at top of this spec) runs `sqlcmd -P "$${SQL_SA_PASSWORD}"`,
  which inside the container shell becomes `$SQL_SA_PASSWORD`.
- Therefore BOTH `MSSQL_SA_PASSWORD` AND `SQL_SA_PASSWORD` MUST be set to the same value
  in the sqlserver service environment block. If only `MSSQL_SA_PASSWORD` is set, the
  healthcheck fails silently and all backend services that `depends_on: service_healthy` never start.

```yaml
# docker-compose.full.yml — Full local dev: all services + infrastructure
# Load secrets from .env (never commit .env to git — only commit .env.example)

services:

  # ── Infrastructure: SQL Server ───────────────────────────────────
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: {resource_prefix}-sql
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "${SQL_SA_PASSWORD}"
      # SQL_SA_PASSWORD must ALSO be set: the healthcheck runs
      # sqlcmd -P "$SQL_SA_PASSWORD" inside the container shell.
      # Without this, healthcheck always fails → backend never starts.
      SQL_SA_PASSWORD: "${SQL_SA_PASSWORD}"
    ports:
      - "1433:1433"
    healthcheck:
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1' -b -No 2>/dev/null || /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1'"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    networks:
      - {resource_prefix}-net
    volumes:
      - sqlserver-data:/var/opt/mssql

  # ── Infrastructure: Redis ─────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: {resource_prefix}-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - {resource_prefix}-net

  # ── Backend services (one block per bounded context) ──────────────
  # Repeat this block for each {ServiceName} / {port} combination:
  #   Service 1 → port 5001, Service 2 → port 5002, etc.
  {service_name}:
    build:
      context: .
      dockerfile: backend/{ServiceName}/Dockerfile
    image: ${ACR_LOGIN_SERVER}/{resource_prefix}/{service_kebab}:${IMAGE_TAG:-local}
    container_name: {resource_prefix}-{service_kebab}
    ports:
      - "{port}:8080"
    environment:
      ASPNETCORE_ENVIRONMENT: Development
      ASPNETCORE_URLS: http://+:8080
      ConnectionStrings__{ServiceName}Db: "Server=sqlserver,1433;Database={ServiceName}Db;User Id=sa;Password=${SQL_SA_PASSWORD};TrustServerCertificate=true;"
      ConnectionStrings__Redis: "{resource_prefix}-redis:6379,password=${REDIS_PASSWORD}"
      AzureAd__TenantId: "${AZURE_AD_TENANT_ID}"
      AzureAd__ClientId: "${AZURE_AD_CLIENT_ID}"
      ApplicationInsights__ConnectionString: "${APPLICATIONINSIGHTS_CONNECTION_STRING}"
    depends_on:
      sqlserver:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - {resource_prefix}-net
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

networks:
  {resource_prefix}-net:
    driver: bridge

volumes:
  sqlserver-data:
```

> `.env.example` MUST be generated alongside the compose file. List all required env vars
> with placeholder values. Developers copy it to `.env` and fill in real values.
> `.env` is excluded by `.dockerignore` and `.gitignore` — never committed.

## docker-compose.yml — Development

Placed at: `projects/{project_name}/outputs/tobe/source-code/docker-compose.yml`

Este arquivo DEVE refletir a arquitetura gerada pelo F4 Stack:

- **Modo monolítico (Host API único):** quando `architecture_patterns.host_api: true`,
  usar um único serviço `backend` apontando para `src/Api/{prefix}.Api`.
- **Modo microserviços por BC (padrão):** quando `pipeline_mode == "generic"` e não há
  `host_api: true`, gerar um serviço por Bounded Context, mapeando portas sequenciais
  a partir de `5001`.

O modo padrão é **entrypoint autônomo por BC** — nunca omitir BCs do compose.

```yaml
version: "3.9"

# ──────────────────────────────────────────────────────────────────
# Development compose — local developer workflow
# Secrets are loaded from .env (NEVER commit .env to git — only commit .env.example)
# ──────────────────────────────────────────────────────────────────

services:
  sql:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: {resource_prefix}-sql
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "${SQL_SA_PASSWORD}"
      SQL_SA_PASSWORD: "${SQL_SA_PASSWORD}"
    ports:
      - "1433:1433"
    healthcheck:
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1' -b -No 2>/dev/null || /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P \"$${SQL_SA_PASSWORD}\" -Q 'SELECT 1'"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    container_name: {resource_prefix}-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  # ── Backend services (one per bounded context) ───────────────────
  # Modo padrão: um serviço por BC, portas 5001..5001+N-1.
  # No modo monolítico, substituir por um único serviço 'backend'.
  {service_name}:
    build:
      context: ./backend
      dockerfile: Dockerfile
      args:
        BC: "{BCName}"
        SOLUTION: "{prefix}.sln"
    image: ${ACR_LOGIN_SERVER}/{resource_prefix}/{service_kebab}:${IMAGE_TAG:-dev}
    container_name: {resource_prefix}-{service_kebab}
    ports:
      - "{port}:8080"
    environment:
      ASPNETCORE_ENVIRONMENT: Development
      ASPNETCORE_URLS: http://+:8080
      ConnectionStrings__SqlServer: "Server=sql,1433;Database={BCName}Db;User Id=sa;Password=${SQL_SA_PASSWORD};TrustServerCertificate=true;"
      ConnectionStrings__Redis: "redis:6379,password=${REDIS_PASSWORD}"
      AzureAd__TenantId: "${AZURE_AD_TENANT_ID}"
      AzureAd__ClientId: "${AZURE_AD_CLIENT_ID}"
      ApplicationInsights__ConnectionString: "${APPLICATIONINSIGHTS_CONNECTION_STRING}"
    depends_on:
      sql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: runtime
    image: ${ACR_LOGIN_SERVER}/{resource_prefix}-frontend:${IMAGE_TAG:-dev}
    container_name: {resource_prefix}-frontend-dev
    ports:
      - "4200:8080"
    environment:
      - API_BASE_URL=http://localhost:5001
    networks:
      - app-network
    depends_on:
      {first_bc_service}:
        condition: service_healthy
    restart: unless-stopped

networks:
  app-network:
    driver: bridge
```

## docker-compose.staging.yml — Staging

Placed at: `projects/{project_name}/outputs/tobe/source-code/docker-compose.staging.yml`

```yaml
version: "3.9"

# ──────────────────────────────────────────────────────────────────
# Staging compose — pre-production validation
# Images are pre-built and pulled from ACR (no local build)
# All secrets injected at runtime via environment variables
# ──────────────────────────────────────────────────────────────────

services:
  backend:
    image: ${ACR_LOGIN_SERVER}/{project_name}-backend:${IMAGE_TAG}
    environment:
      - ASPNETCORE_ENVIRONMENT=Staging
      - ConnectionStrings__SqlServer=${SQL_CONNECTION_STRING}
      - ConnectionStrings__Redis=${REDIS_CONNECTION_STRING}
      - AzureAd__ClientId=${AZURE_AD_CLIENT_ID}
      - ApplicationInsights__ConnectionString=${APPINSIGHTS_CONNECTION_STRING}
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        max_attempts: 3
    networks:
      - app-network

  frontend:
    image: ${ACR_LOGIN_SERVER}/{project_name}-frontend:${IMAGE_TAG}
    environment:
      - API_BASE_URL=http://backend:8080
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        max_attempts: 3
    depends_on:
      - backend
    networks:
      - app-network

networks:
  app-network:
    driver: overlay
```

## docker-compose.prod.yml — Production

Placed at: `projects/{project_name}/outputs/tobe/source-code/docker-compose.prod.yml`

```yaml
version: "3.9"

# ──────────────────────────────────────────────────────────────────
# Production compose — deployed via CI/CD pipeline
# ⚠️  Never run docker-compose up manually in production.
# Use the CD pipeline (azure-pipelines-cd.yml) instead.
# ──────────────────────────────────────────────────────────────────

services:
  backend:
    image: ${ACR_LOGIN_SERVER}/{project_name}-backend:${IMAGE_TAG}
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - ConnectionStrings__SqlServer=${SQL_CONNECTION_STRING}
      - ConnectionStrings__Redis=${REDIS_CONNECTION_STRING}
      - AzureAd__ClientId=${AZURE_AD_CLIENT_ID}
      - ApplicationInsights__ConnectionString=${APPINSIGHTS_CONNECTION_STRING}
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 30s
        failure_action: rollback
        monitor: 60s
      rollback_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 5
        window: 120s
    networks:
      - app-network

  frontend:
    image: ${ACR_LOGIN_SERVER}/{project_name}-frontend:${IMAGE_TAG}
    environment:
      - API_BASE_URL=http://backend:8080
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 30s
        failure_action: rollback
        monitor: 60s
      rollback_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 5
        window: 120s
    depends_on:
      - backend
    networks:
      - app-network

networks:
  app-network:
    driver: overlay
    attachable: false
```

## Output Contract

```yaml
outputs:
  backend_dockerfile:      "projects/{project_name}/outputs/tobe/source-code/backend/Dockerfile"
  backend_dockerignore:    "projects/{project_name}/outputs/tobe/source-code/backend/.dockerignore"
  frontend_dockerfile:     "projects/{project_name}/outputs/tobe/source-code/frontend/Dockerfile"
  frontend_dockerignore:   "projects/{project_name}/outputs/tobe/source-code/frontend/.dockerignore"
  frontend_nginx_conf:     "projects/{project_name}/outputs/tobe/source-code/frontend/nginx.conf"
  docker_compose_dev:      "projects/{project_name}/outputs/tobe/source-code/docker-compose.yml"
  docker_compose_staging:  "projects/{project_name}/outputs/tobe/source-code/docker-compose.staging.yml"
  docker_compose_prod:     "projects/{project_name}/outputs/tobe/source-code/docker-compose.prod.yml"
  containerization_report: "projects/{project_name}/outputs/tobe/iac/containers/containerization-report.md"
```

## Triggers / Menu

| Code  | Description                                          |
|-------|------------------------------------------------------|
| `CT`  | Containerize full (backend + frontend)               |
| `CTB` | Containerize backend only                            |
| `CTF` | Containerize frontend only                           |
| `CTV` | Validate — check existing Dockerfiles for issues     |

## Execution Steps

### Step 1 — Read Context

```
READ projects/{project_name}/context/project-config.yaml
  → extract project_name
  → extract tobe_stack.backend_version  → derive dotnet_version (major only, e.g. "10")
  → extract tobe_stack.frontend_framework (confirm Angular)
  → extract tobe_stack.node_version (default: "22" if absent)

IF backend_version missing from project-config:
  READ projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md
  → grep "ASP.NET Core \d+" → extract major version

resource_prefix = lowercase(project_name[0:8]).replace("-","").replace(" ","")
```

### Step 2 — Detect Services

```
Glob: projects/{project_name}/outputs/tobe/source-code/**/*.csproj
  → IF results found: backend_detected = true
                      solution_name   = first result filename (no extension)
                      assembly_name   = solution_name

Host project detection (monorepo pattern):
  Glob: projects/{project_name}/outputs/tobe/source-code/**/src/hosts/**/*.csproj
    → IF found: host_project_detected = true
                host_project_path     = relative path from source-code root
                                        e.g. "src/hosts/MeuERP.Api/MeuERP.Api.csproj"
                assembly_name         = host csproj filename without extension
                                        e.g. "MeuERP.Api"
  → Use host_project_path as the primary restore and publish target (NEVER the .sln file)

Glob: projects/{project_name}/outputs/tobe/source-code/**/angular.json
  → IF results found: frontend_detected = true

IF NOT backend_detected AND NOT frontend_detected:
  → ERROR: "No services detected in source-code/."
  → ABORT
```

### Step 3 — Generate Backend Artifacts

```
IF backend_detected:
  3.0  Count *.Api.csproj files:
       Glob: source-code/**/*.Api.csproj → api_projects[]

  IF host_project_detected:  # Monorepo with single host entry point
    # ⚠️  Guardrail: NEVER restore the .sln — always restore from host_project_path
    3.1  Generate a single monorepo Dockerfile at source-code/backend/Dockerfile:
         - COPY all production .csproj files (Shared + every bounded context + host) individually
           for layer caching (do NOT COPY test project .csproj files)
         - RUN dotnet restore {host_project_path} --runtime linux-x64
         - COPY . .
         - RUN dotnet publish {host_project_path} --no-restore --runtime linux-x64
               -c Release -o /app/publish /p:UseAppHost=false
         - Runtime stage: ENTRYPOINT ["dotnet", "{assembly_name}.dll"]
    3.2  Write → source-code/backend/Dockerfile
    3.3  Write → source-code/backend/.dockerignore
    3.4  REPORT: "✅ Backend (monorepo-host): {host_project_path} → sdk:{dotnet_version} → aspnet:{dotnet_version}"

  ELSE IF len(api_projects) == 1:  # Single-service (no hosts dir)
    3.1  Substitute {dotnet_version}, {solution_name}, {assembly_name} in single-service Dockerfile template
         Replace `dotnet restore "{solution_name}.csproj"` with
         `dotnet restore "{api_project_path}" --runtime linux-x64`
    3.2  Write → source-code/backend/Dockerfile
    3.3  Write → source-code/backend/.dockerignore
    3.4  REPORT: "✅ Backend (single-service): sdk:{dotnet_version} → aspnet:{dotnet_version}"

  ELSE IF len(api_projects) > 1:   # Multi-service (microservices)
    For each api_csproj in api_projects:
      ServiceName = directory name of api_csproj parent (e.g. "CustomerSupplier")
      3.1  Substitute {ServiceName}, {prefix}, {dotnet_version}, {patch_version},
           {runtime_patch_version} in per-service Dockerfile template
           # {patch_version}: pinned SDK patch (e.g. "411" for 8.0.411) — read from global.json or project-config
           # If not available, omit patch suffix (use {dotnet_version}.0)
      3.2  Write → source-code/backend/{ServiceName}/Dockerfile
    3.3  Write → source-code/backend/.dockerignore  (one shared .dockerignore for all)
    3.4  Generate docker-compose.full.yml using the multi-service template:
         - Assign ports sequentially: first service → 5001, second → 5002, etc.
         - Substitute {resource_prefix} = resource_prefix (from Step 1)
         - Include all detected ServiceName entries as backend service blocks
         - Generate .env.example alongside with all required variable names and placeholder values
    3.5  Write → source-code/docker-compose.full.yml
    3.6  Write → source-code/.env.example
    3.7  REPORT: "✅ Backend (multi-service, {N} services): per-service Dockerfiles + docker-compose.full.yml"
```

### Step 4 — Generate Frontend Artifacts

```
IF frontend_detected:
  1. Substitute {node_version} in Dockerfile template
  2. Write → source-code/frontend/Dockerfile
  3. Write → source-code/frontend/.dockerignore
  4. Write → source-code/frontend/nginx.conf
  5. REPORT: "✅ Frontend: node:{node_version}-alpine → nginx:1.27-alpine"
```

### Step 5 — Generate docker-compose Files

```
Substitute {project_name} in all compose file templates.
1. Write → source-code/docker-compose.yml         (development)
2. Write → source-code/docker-compose.staging.yml  (staging)
3. Write → source-code/docker-compose.prod.yml     (production)
4. REPORT: "✅ docker-compose: dev / staging / prod generated"
```

### Step 6 — Write Containerization Report

```
Bash: mkdir -p projects/{project_name}/outputs/tobe/iac/containers/

Write: projects/{project_name}/outputs/tobe/iac/containers/containerization-report.md

Content:
  # Containerization Report — {project_name}
  Generated: {timestamp}
  TraceID: {trace_id}

  ## Services Containerized
  | Service  | Detected | Dockerfile Path                              | Build Image                              | Runtime Image                            |
  |----------|----------|----------------------------------------------|------------------------------------------|------------------------------------------|
  | backend  | ✅/❌    | source-code/backend/Dockerfile               | dotnet/sdk:{dotnet_version}.0            | dotnet/aspnet:{dotnet_version}.0         |
  | frontend | ✅/❌    | source-code/frontend/Dockerfile              | node:{node_version}-alpine               | nginx:1.27-alpine                        |

  ## Artifacts Generated
  [list all files created with absolute paths]

  ## Runtime Environment Variables Required
  All secrets are injected at runtime — NEVER hardcode in Dockerfiles or compose files.

  | Variable                        | Used In                  | Description                                              |
  |---------------------------------|--------------------------|----------------------------------------------------------|
  | `ACR_LOGIN_SERVER`              | docker-compose*.yml      | Azure Container Registry login server (e.g. foo.azurecr.io) |
  | `IMAGE_TAG`                     | docker-compose*.yml      | Image tag to deploy (git SHA or semver)                  |
  | `SQL_CONNECTION_STRING`         | docker-compose*.yml      | Azure SQL connection string (sourced from Key Vault)     |
  | `REDIS_CONNECTION_STRING`       | docker-compose*.yml      | Azure Cache for Redis connection string                  |
  | `AZURE_AD_CLIENT_ID`            | docker-compose*.yml      | Azure AD application (client) ID                         |
  | `APPINSIGHTS_CONNECTION_STRING` | docker-compose*.yml      | Application Insights connection string                   |

  ## Next Steps
  1. Run `ava-devops-iac-azure` (trigger `IA`) to provision Azure infrastructure
     (ACR, AKS/App Service, SQL, Redis, Key Vault, AppInsights)
  2. Build and push images to ACR:
     docker build -t ${ACR_LOGIN_SERVER}/{project_name}-backend:${IMAGE_TAG} ./backend
     docker push ${ACR_LOGIN_SERVER}/{project_name}-backend:${IMAGE_TAG}
  3. For local dev: create .env.dev with the required variables, then docker-compose up
  4. For staging/prod: deploy via CI/CD pipeline (azure-pipelines-cd.yml)
```

### Step 7 — Report Completion

```
✅ Containerization complete — {project_name}

Services:
  Backend  : ✅ source-code/backend/Dockerfile  (sdk:{dotnet_version} → aspnet:{dotnet_version})
  Frontend : ✅ source-code/frontend/Dockerfile  (node:{node_version} → nginx:1.27)

Compose files:
  Development  : source-code/docker-compose.yml
  Staging      : source-code/docker-compose.staging.yml
  Production   : source-code/docker-compose.prod.yml

Report: outputs/tobe/iac/containers/containerization-report.md

⚠️  Secrets are NOT embedded — inject at runtime via environment variables:
    ACR_LOGIN_SERVER, IMAGE_TAG, SQL_CONNECTION_STRING,
    REDIS_CONNECTION_STRING, AZURE_AD_CLIENT_ID, APPINSIGHTS_CONNECTION_STRING

→ Next: run ava-devops-iac-azure (trigger IA) to provision Azure infrastructure.
```

### Step 8 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-devops-containerize --phase F6 --version 1.0.1 \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---
