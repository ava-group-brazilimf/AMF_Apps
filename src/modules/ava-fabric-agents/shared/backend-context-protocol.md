---
name: ava-backend-context-protocol
description: |
  Protocolo compartilhado de leitura de contexto, invariantes e failure modes comuns
  para todos os agentes backend .NET, em ambos os pipeline_mode ("generic" e "build-cycle").
  Referenciado por: build-cycle-dotnet-scaffold, build-cycle-efcore,
                    build-cycle-cqrs, build-cycle-minimal-apis,
                    coder-dotnet-backend, coder-java-backend,
                    coder-go-backend, coder-python-backend.
allowed-tools: Read
---

# AVA — Backend Context Protocol

> Apply: [@governance-apps](governance-apps.md)

## @backend-override-resolution

**Override resolution (MUST run before any other read in every build-cycle agent):**

```
READ project-config.yaml → todos os campos (ponto único de configuração)
effective_config = merge(project-config.yaml fields, project-config.yaml.overrides)
Log: "cqrs = {value} ({source: overrides|project-config})"
USE effective_config for ALL subsequent reads
```

**Campos mínimos lidos por todos os agentes:**

```
project_name              ← project-config.yaml
solution_prefix           ← PascalCase de project_name sem espaços/hífens
                             Ex: "Meu-ERP" → "MeuERP"
backend_version           ← project-config.yaml → tobe_stack.backend_version
cqrs                      ← project-config.yaml → architecture_patterns.cqrs
```

---

## @backend-dotnet-invariants

**Invariantes invioláveis — comuns a todos os agentes backend .NET:**

1. `#nullable enable` em todos os arquivos `.cs` gerados
2. `async/await` — nunca `.Result` ou `.Wait()`
3. Injeção via construtor — nunca `new` em classes de negócio
4. `FluentValidation` — nunca validação inline (`if (x == null) throw`)
5. `record` para Commands, Queries, DTOs imutáveis e Value Objects
6. `Guid` obrigatório para PKs e FKs — nunca `int`, `long` ou `uint`
7. Connection string EXCLUSIVAMENTE via Azure Key Vault — nunca `appsettings.json` ou variável de ambiente direta
8. ZERO vulnerabilidades NuGet (toda severidade) — executar gate antes de COMPLETED
9. Build ZERO erros obrigatório antes de retornar COMPLETED

**Versões canônicas e pacotes proibidos:**
> Ver [@dotnet-nuget-policy](../tobe-architecture/agents/dotnet-nuget-policy.md)

---

## @backend-common-failure-modes

**Failure modes comuns — aplicam-se a todos os agentes build-cycle:**

| Cenário | Ação |
|---------|------|
| `project-config.yaml` não encontrado | BLOCKED: "project-config.yaml não encontrado em projects/{project_name}/context/. Execute a wave de contexto antes de continuar." |
| `tobe_stack` ausente no project-config.yaml | BLOCKED: "Seção tobe_stack não encontrada em project-config.yaml. Certifique-se de usar o template atualizado." |
| Agente predecessor não executado (pastas src/ ausentes) | BLOCKED: "Execute @ava-build-cycle-dotnet-scaffold primeiro — estrutura de pastas não encontrada." |
| `cqrs` ausente no project-config.yaml | Perguntar: "CQRS habilitado? (s/n)" — sem assumir default |
| BC com nome contendo caracteres especiais/acentos | Normalizar para PascalCase sem espaços/acentos; avisar: "'{original}' normalizado para '{normalizado}'" |
| BC com mais de 15 entidades | WARN: "BC '{nome}' com {N} entidades — considere subdivisão em BCs menores" |
| Mais de 10 bounded contexts na solução | WARN: "Solução com {N} BCs pode impactar tempo de build. Considere separar em múltiplos repositórios." |
| Versão obsoleta de pacote usada pelo LLM | LER `docs-research-bundle.md` §1 (versões resolvidas) e §6 (guardrails de versão) ANTES de gerar código. Se bundle ausente → usar @dotnet-nuget-policy como fallback. |
