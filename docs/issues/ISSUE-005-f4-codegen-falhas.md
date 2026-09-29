# ISSUE-005 — F4 codegen: prompt idêntico para 394 tasks, frontend inexistente, backend não compila

**Date**: 2026-08-19
**Project**: nopcommerce-04
**Branch**: `feat/deterministic-task-dependency-graph`
**Severity**: CRITICAL — a F4 é inoperante; 2 de 394 tasks executaram e ambas falharam
**Status**: ROOT CAUSE IDENTIFIED — correções não aplicadas
**Escopo**: `projects/nopcommerce-04/outputs/tobe/source-code/`
**Relacionada**: `ISSUE-004-speckit-plan-graph-perda-silenciosa.md`

---

## 1. Estado da execução

`outputs/tobe/speckit/tasks-progress.json`:

| Status | Tasks |
| --- | --- |
| `failed` | **2** — `T-SCAFFOLD-ANGULAR-001`, `T-SCAFFOLD-DOTNET-001` |
| `pending` | **392** |

A F4 parou na wave 0. Nenhuma task de domínio chegou a ser despachada — as duas de
scaffold são pré-requisito de todas as outras por `target_stack`.

Ambas registraram `attempts: 1` no razão, mas os `GENERATION_LOG.md` mostram 2 e 3
tentativas de build com remediação automática entre elas.

### Árvore gerada

```
source-code/
├── angular/     4 arquivos — .gitignore, f4s-state.json, GENERATION_LOG.md, 1 snapshot
│                ZERO arquivos .ts, .html, .scss, package.json ou angular.json
└── dotnet/      367 arquivos — 123 .cs, 65 .csproj, 1 .sln
```

---

## 2. Causa raiz — as 394 tasks recebem o mesmo prompt

Este é o defeito central. Tudo o mais decorre dele.

O prompt efetivamente enviado ao agente coder, reproduzido a partir do código:

```
@ava-f4s-codegen-agent | SG | project: nopcommerce-04
```

**Idêntico para as 394 tasks.** Verificado: `expand_foreach` produz 394 passos e
`build_prompt` gera **1 prompt distinto**. Sem `task_id`, sem `target_stack`, sem
`feature`. O agente não tem como saber qual das 394 tasks está executando, nem se deve
gerar backend ou frontend.

### A cadeia de perda

A informação existe na origem e é descartada em quatro pontos independentes — qualquer
um deles sozinho já bastaria para causar a falha:

| # | Onde | O que acontece |
| --- | --- | --- |
| 1 | `traceability.json` | entrada **tem** `feature` ✅ |
| 2 | `task_ledger` → `tasks-progress.json` | **não persiste** `feature`; a task pronta volta com `feature: None` ❌ |
| 3 | `pipeline_plan.expand_foreach:374` | `feature=task.get("feature", "")` → `''` ❌ |
| 4 | `ava-pipeline-runner-cli.py:343-348` | o dict de substituição copia `phase, label, agent, trigger, inputs, task_group, target_stack, task_id, kind` — **`feature` não está na lista** ❌ |
| 5 | `ava-pipeline-runner-cli.py:2420-2431` | `build_prompt(agent, trigger, project, feature)` — **ignora `task_id` e `target_stack`**, que existem no passo ❌ |

O `Step` carrega `target_stack='angular'` e `task_id='T-SCAFFOLD-ANGULAR-001'` corretamente
até o fim. O prompt simplesmente não os usa.

### Consequência direta

`T-SCAFFOLD-ANGULAR-001` gravou **100 arquivos, todos em `dotnet/`**. Nenhum em `angular/`.

Sem discriminador no prompt, o agente inferiu a stack do contexto injetado — que é
dominado pela `constitution.md`, um documento de Clean Architecture .NET de 57 KB. Ele
gerou .NET nas duas vezes, porque nas duas vezes recebeu exatamente a mesma instrução.

A spec do scaffold Angular está **correta** (`stack: angular`, título "Scaffold Angular
Frontend", aponta para `build-cycle-angular-agent.md`) — ela só nunca foi citada no prompt.

Este é o mesmo padrão da ISSUE-004: dado declarado a montante, descartado antes do
consumidor. Aqui o `agent_map` do `ava-pipeline.yaml:240-249` reforça — as 9 stacks
mapeiam para o **mesmo** `ava-f4s-codegen-agent`, então a discriminação só poderia vir do
prompt ou do contexto, e não vem de nenhum dos dois.

---

## 3. Diagnóstico do frontend

### F-01 — Nenhum código Angular foi gerado

| Evidência | Valor |
| --- | --- |
| arquivos em `angular/` | 4 (nenhum de código) |
| `package.json` / `angular.json` | ausentes |
| arquivos `.ts` no projeto inteiro | **0** |
| arquivos gravados pela task Angular | 100, **todos em `dotnet/`** |

Causa: seção 2.

### F-02 — Angular CLI não instalado no host

```
verify_command : ng build
exit_code      : 127
build output   : [WinError 2] The system cannot find the file specified
```

Exit 127 é "comando não encontrado". Confirmado no host: `node v22.16.0` e `npm 10.9.2`
presentes, **`ng` ausente**.

Nenhum passo verifica o toolchain antes de despachar. A task foi executada, consumiu
inferência, gerou 100 arquivos errados, e só então tentou um comando inexistente.

### F-03 — Remediação automática rodou duas vezes sem poder funcionar

```
Attempt 1: exit 127 — "remediation triggered"
Attempt 2: exit 127 — "remediation did not change files"
```

A remediação supõe erro de compilação no código gerado. Aqui o código nem existe e o
compilador nem está instalado. Ela não tinha o que corrigir, e o relatório final atribui a
falha a "missing dependencies, unresolved symbols, or generated code that contradicts the
project structure" — três hipóteses, nenhuma correta.

---

## 4. Diagnóstico do backend

### B-01 — Violação de Central Package Management (2 erros, bloqueia o build)

```
error NU1008: The following PackageReference items cannot define a value for Version:
  Microsoft.EntityFrameworkCore.SqlServer, Microsoft.EntityFrameworkCore.Tools, Dapper,
  Konscious.Security.Cryptography.Argon2, Serilog.AspNetCore, OpenTelemetry.Extensions.Hosting
  → src/Modules/Security/Security.Infrastructure/Security.Infrastructure.csproj

error NU1008: ... (17 pacotes)
  → src/Host/NopCommerce.API/NopCommerce.API.csproj
```

`Directory.Packages.props` declara `<ManagePackageVersionsCentrally>true</...>` com 47
`PackageVersion`. Sob CPM, `.csproj` **não pode** trazer `Version=` inline.

Sete `.csproj` trazem:

| Projeto | Refs inline | Fora do catálogo central |
| --- | --- | --- |
| `src/Host/NopCommerce.API` | 17 | 4 |
| `src/Modules/Security/Security.Infrastructure` | 6 | 0 |
| `tests/Common.UnitTests` | 6 | 0 |
| `tests/Media.UnitTests` | 6 | 0 |
| `tests/Security.UnitTests` | 6 | 0 |
| `tests/Shipping.UnitTests` | 6 | 0 |
| `tests/Tax.UnitTests` | 6 | 0 |

Os outros **58 `.csproj` estão corretos** — sem `Version=`. Inconsistência dentro de uma
única geração: o mesmo agente, no mesmo despacho, aplicou a convenção em 58 projetos e
esqueceu em 7.

Pacotes a acrescentar em `Directory.Packages.props`: `AspNetCore.HealthChecks.SqlServer`,
`AspNetCore.HealthChecks.Redis`, `AspNetCore.HealthChecks.AzureBlobStorage`,
`Azure.Extensions.AspNetCore.Configuration.Secrets`.

### B-02 — Cobertura de build ilusória: 25 projetos nunca compilados

| Métrica | Valor |
| --- | --- |
| `.csproj` em disco | **65** |
| projetos na `NopCommerce.sln` | **24** |
| órfãos da solution | 41 |
| ├─ alcançados via `ProjectReference` | 16 |
| └─ **nunca compilados** | **25** |

`dotnet build` compila a solution. Os 25 projetos que não estão nem na `.sln` nem são
referenciados por quem está — incluindo `Catalog.API`, `Customers.API`, `Messages.API` e
todos os `*.IntegrationTests` — **jamais passaram pelo compilador**.

Ou seja: mesmo depois de corrigir os dois `NU1008`, um "build OK" cobriria 40 de 65
projetos. O `verify_command: dotnet build` do razão daria `verified` sobre 62% da árvore.

Isto é a mesma classe de defeito que a ISSUE-004 tratou no gate de saída: verificação que
passa sem cobrir o que diz cobrir.

### B-03 — 53 warnings de vulnerabilidade conhecida

`NU1903` (alta) e `NU1902` (moderada) em pacotes que o próprio scaffold escolheu:

| Pacote | Versão | Severidade |
| --- | --- | --- |
| `AutoMapper` | 13.0.1 | alta |
| `System.Security.Cryptography.Xml` | 9.0.0 | alta |
| `OpenTelemetry.Api` | 1.10.0 | moderada |

Não bloqueiam o build, mas contradizem a `constitution.md`, que traz requisitos de
segurança. Nenhum check da esteira examina o resultado do restore.

### B-04 — Remediação esgotou 3 tentativas sem tocar na causa

```
Attempt 1: exit 1 — remediation triggered
Attempt 2: exit 1 — remediation triggered
Attempt 3: exit 1 — final attempt failed; spec will be skipped
```

`NU1008` é determinístico e trivialmente corrigível: remover `Version=` de 7 arquivos e
acrescentar 4 `PackageVersion`. A remediação não reconhece a classe de erro — trata tudo
como erro de código C#.

---

## 5. Por que o código não compila — resumo causal

```
prompt sem task_id/target_stack/feature   (seção 2)
        │
        ├─→ agente gera .NET quando deveria gerar Angular
        │       └─→ angular/ vazio → ng build → 127 (agravado por ng não instalado)
        │
        └─→ agente gera o scaffold .NET sem discriminação de task
                └─→ 7 de 65 csproj com Version= inline sob CPM
                        └─→ NU1008 × 2 → dotnet build exit 1
                                └─→ 3 tentativas de remediação cega
                                        └─→ task skipped → 392 tasks nunca despachadas
```

O backend tem **2 erros de compilação**, ambos de configuração de projeto, nenhum de
código C#. Os 123 arquivos `.cs` gerados não chegaram a ser avaliados pelo compilador nos
25 projetos órfãos, e nos demais o build para no restore, antes da compilação.

---

## 6. Correções propostas

### Prioridade 1 — desbloqueia a F4 (código de esteira)

| # | Correção | Arquivo |
| --- | --- | --- |
| P1.1 | `build_prompt` passa a incluir `task_id` e `target_stack` quando presentes no passo | `ava-pipeline-runner-cli.py:2420` |
| P1.2 | `_expand_ledger_phase` copia `feature` para o dict do passo | `ava-pipeline-runner-cli.py:343` |
| P1.3 | `task_ledger` persiste `feature` no `tasks-progress.json` | `src/shared/tools/task_ledger.py` |
| P1.4 | Preflight de toolchain: verificar que o `verify_command` da task existe no PATH **antes** de despachar; exit 127 vira bloqueio prévio, não falha pós-inferência | `ava-pipeline-runner-cli.py` |
| P1.5 | Remediação passa a reconhecer classes de erro determinísticas (`NU1008`, `NU1101`, `CS0246`) e aplicar a correção específica, em vez de reexecutar o build às cegas | `src/shared/tools/f4s_build_runner.py` |

### Prioridade 2 — cobertura de verificação

| # | Correção |
| --- | --- |
| P2.1 | Check novo: todo `.csproj` em disco tem de estar na `.sln` ou ser alcançável por `ProjectReference`. Órfão reprova o scaffold. |
| P2.2 | `verify_command` do scaffold passa a incluir os projetos de teste, hoje fora da solution |
| P2.3 | Falha de restore com `NU1903` de severidade alta vira achado do gate, não warning silencioso |

### Prioridade 3 — dados já gerados

| # | Ação |
| --- | --- |
| P3.1 | Remover `Version=` dos 7 `.csproj` e acrescentar os 4 `PackageVersion` faltantes — determinístico |
| P3.2 | Acrescentar os 41 projetos órfãos à `NopCommerce.sln` |
| P3.3 | Instalar Angular CLI no host (`npm i -g @angular/cli`) ou trocar o `verify_command` para `npx ng build` |
| P3.4 | Descartar `angular/` e reexecutar `T-SCAFFOLD-ANGULAR-001` **depois** de P1.1/P1.2 |

⚠️ P3.4 depende de P1: reexecutar hoje produziria .NET de novo, porque o prompt continuaria
idêntico ao do scaffold .NET.

---

## 7. O que não foi possível avaliar

- **Qualidade do C# gerado.** O build para no restore; o compilador nunca processou os 123
  arquivos `.cs`. Erros de código — se existirem — continuam invisíveis.
- **As 392 tasks de domínio.** Nunca despachadas. Toda a avaliação acima cobre apenas as
  duas tasks de scaffold da wave 0.
