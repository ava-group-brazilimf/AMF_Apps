---
name: dotnet-research-instructions
description: |
  Instruções de pesquisa .NET: fontes confiáveis, protocolo de resolução de versões,
  guardrails por versão. Consumido por ava-stack-docs-researcher e ava-stack-build-fixer.
version: "1.0.0"
date: 2026-06-25
---

# .NET Research Instructions

> Recurso compartilhado consumido por `ava-stack-docs-researcher` e `ava-stack-build-fixer`.

---

## §1 — Fontes Confiáveis (URLs permitidas para `fetch_webpage`)

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| Microsoft Learn — .NET | What's new, breaking changes | `learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-{version}` |
| Microsoft Learn — EF Core | What's new EF Core | `learn.microsoft.com/en-us/ef/core/what-is-new/ef-core-{version}` |
| Microsoft Learn — ASP.NET Core | Release notes | `learn.microsoft.com/en-us/aspnet/core/release-notes/aspnetcore-{version}` |
| Microsoft Learn — Breaking Changes | Detalhes de breaking changes | `learn.microsoft.com/en-us/dotnet/core/compatibility/breaking-changes` |
| NuGet API | Versões e metadata | `api.nuget.org/v3-flatcontainer/{packageId}/index.json` |
| NuGet Gallery | Página do pacote | `nuget.org/packages/{packageId}` |
| GitHub — dotnet/runtime | Release notes do runtime | `github.com/dotnet/runtime/releases` |
| GitHub — dotnet/aspnetcore | Release notes ASP.NET | `github.com/dotnet/aspnetcore/releases` |
| GitHub — Carter | Release notes Carter | `github.com/CarterCommunity/Carter/releases` |
| GitHub — MediatR | Release notes MediatR | `github.com/jbogard/MediatR/releases` |
| GitHub — Mapster | Wiki Mapster | `github.com/MapsterMapper/Mapster/wiki` |
| GitHub — FluentValidation | Docs FluentValidation | `github.com/FluentValidation/FluentValidation` |

> ⛔ URLs fora desta lista NÃO são fontes confiáveis para resolução de versões e patterns.
> Blog posts, StackOverflow e tutoriais de terceiros NÃO devem ser usados como fonte de verdade.

---

## §2 — Protocolo de Resolução por Tipo de Dependência

| Tipo | Regra de Versão | Exemplo |
|------|----------------|---------|
| `Microsoft.Extensions.*` | Alinhar com `backend_version` | .NET 10 → `10.0.x` |
| `Microsoft.EntityFrameworkCore.*` | Mesma major version do runtime | .NET 10 → `10.0.x` |
| `Microsoft.AspNetCore.*` | Mesma major version do runtime | .NET 10 → `10.0.x` |
| `Microsoft.Identity.Web` | Latest stable ≥ 4.x (CVE floor) | `4.x` |
| Pacotes de terceiros | Latest stable compatível com TFM | Carter, MediatR, etc. |

### Resolução de Versão — Procedimento

```
PARA CADA pacote na lista:
  1. Executar: dotnet package search --exact-match {packageId} --format json
     → Extrair latest stable version
  2. SE comando falhar:
     → fetch_webpage: api.nuget.org/v3-flatcontainer/{packageId}/index.json
     → Extrair última versão estável (não-preview, não-rc)
  3. SE ambos falharem:
     → ⛔ BLOCKED: "Não foi possível resolver versão para {packageId}"
     → NÃO usar versão de training data como fallback
```

---

## §3 — Guardrails Específicos por Versão do .NET

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| .NET 10 | `Mapster.DependencyInjection` quebrado — usar `TypeAdapterConfig.GlobalSettings.Scan()` | coder-dotnet-backend.md G1 |
| .NET 10 | Swashbuckle incompatível — usar `AddOpenApi()` + Scalar UI | dotnet-program-cs.md §6 |
| .NET 10 | `AddApplicationInsightsTelemetry(string)` obsoleto — usar overload com `Action<options>` | dotnet-program-cs.md §7 |
| .NET 9+ | `System.Text.Json` source generators preferidos sobre reflection | learn.microsoft.com |
| .NET 8+ | `[FromBody]` e `[FromQuery]` obrigatórios em Minimal APIs | learn.microsoft.com |
| .NET 6+ | `#nullable enable` obrigatório em todos os `.cs` | backend-context-protocol.md |

### APIs Deprecadas Conhecidas

| API Deprecada | Versão Afetada | Substituto | Referência |
|---------------|---------------|------------|-----------|
| `services.AddMapster()` | .NET 10 | `TypeAdapterConfig.GlobalSettings.Scan(asm)` | G1 |
| `AddSwaggerGen()` | .NET 10 | `AddOpenApi()` + Scalar | dotnet-program-cs §6 |
| `AddApplicationInsightsTelemetry(connStr)` | .NET 10 | `AddApplicationInsightsTelemetry(o => o.ConnectionString = ...)` | dotnet-program-cs §7 |
| `IMapper` (Mapster DI) | .NET 10 | `source.Adapt<T>()` (static extension) | G1 |
| `UseSwagger()` + `UseSwaggerUI()` | .NET 10 | `MapOpenApi()` + `MapScalarApiReference()` | dotnet-program-cs §6 |

---

## §4 — Referência Cruzada com Políticas Existentes

| Política | Referência | Propósito |
|----------|-----------|-----------|
| Versões NuGet | `@dotnet-nuget-policy` (`src/modules/ava-fabric-agents/tobe-architecture/agents/dotnet-nuget-policy.md`) | Security floors, transitive override pattern, naming traps |
| Invariantes de código | `@backend-context-protocol` → `@backend-dotnet-invariants` | #nullable, async/await, DI, FluentValidation, record, Guid PKs |
| Template Program.cs | `@dotnet-program-cs.md` (`src/modules/ava-fabric-agents/shared/templates/dotnet-program-cs.md`) | 11 seções canônicas do Program.cs |
| Frontend Governance | `@frontend-governance` (`src/modules/ava-fabric-agents/shared/frontend-governance.md`) | Angular standards, MSAL, NgRx |

---

## §5 — Protocolo de Pesquisa por Pacote (5 Passos)

Para cada pacote identificado em `Directory.Packages.props` ou `project-config.yaml`:

| Passo | Ação | Ferramenta | Output |
|-------|------|-----------|--------|
| P1 — Discover latest | `dotnet package search --exact-match {packageId} --format json` | Bash | Versão latest stable |
| P2 — Check CVE | `dotnet list package --vulnerable` ou NuGet advisory API | Bash | Status CVE (clean/vulnerable) |
| P3 — Fetch docs oficiais | URLs de §1 conforme tipo do pacote | fetch_webpage | Docs, breaking changes, migration guide |
| P4 — Fetch changelog | GitHub releases do pacote | fetch_webpage / github_text_search | Release notes, breaking changes entre versões |
| P5 — Consolidar | Agregar no bundle (versão, breaking changes, patterns, guardrails) | Write | Entrada no bundle §1-§6 |

### Regras de Fallback

```
SE P1 falhar → tentar P1b (NuGet API via fetch_webpage)
SE P1b falhar → ⛔ BLOCKED para este pacote (NÃO usar versão de training data)
SE P3 falhar → registrar WARNING no bundle, continuar com P4
SE P4 falhar → registrar WARNING no bundle, continuar com P5
```

---

## §6 — Breaking Changes Conhecidos por Stack Version

### .NET 10 (net10.0)

1. **Mapster DI removido** — `Mapster.DependencyInjection` não registra tipos. Usar padrão estático.
2. **Swashbuckle incompatível** — não suporta .NET 10 minimal APIs nativamente. Usar `Microsoft.AspNetCore.OpenApi`.
3. **Rate Limiting namespace split** — `System.Threading.RateLimiting` separado de `Microsoft.AspNetCore.RateLimiting`.
4. **Azure Monitor telemetry** — `UseAzureMonitor()` requer connection string não-nula (crash em startup).
5. **EF Core 10** — `HasConversion` para value objects requer `ValueConverter<T,T>` explícito (não mais infere).

### .NET 9 (net9.0)

1. **System.Text.Json source generators** — reflection-based serialization emite warning de trim.
2. **Minimal APIs parameter binding** — `[FromBody]`/`[FromQuery]` obrigatórios (breaking vs .NET 7).

### .NET 8 (net8.0)

1. **Identity API endpoints** — `MapIdentityApi<T>()` novo padrão; `AddDefaultIdentity` deprecated.
2. **Keyed services** — `[FromKeyedServices]` novo; impacta DI registration patterns.
