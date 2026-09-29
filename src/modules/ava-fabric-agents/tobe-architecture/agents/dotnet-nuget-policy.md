---
name: ava-dotnet-nuget-policy
version: "1.0.0"
description: |
  Política NuGet Central Package Management para projetos .NET gerados pelo AVA.
  Define security floors (versões mínimas por CVE), regras de transitive override,
  gate de vulnerabilidades (zero tolerância — toda severidade) e gate de build.
  Referenciado por: coder-dotnet.md
  Origem: sincronizado com .github/agents/shared/backend/DotNetSpecificRoles.md
  Última atualização: mai/2026 (incidente MeuERP — correção de CVEs transitivos)
allowed-tools: Read
---

> Apply: [@governance-apps](../../shared/governance-apps.md)

# AVA — Política NuGet .NET

## @dotnet-nuget-version-policy

**NuGet Central Package Management — Security Floors, Naming Traps & Gates de Build**

---

### Protocolo de Resolução de Versão (Step 1.6) — OBRIGATÓRIO antes de pinar qualquer pacote

> ⛔ **NUNCA** escrever `<PackageVersion>` com um número de versão obtido de memória, de treinamento ou de documentação estática. Versões de treinamento são potencialmente vulneráveis. O único valor aceitável é o resultado do procedimento abaixo.

**Executar para CADA pacote antes de pinar no `Directory.Packages.props`:**

**Passo A — Descobrir última versão estável (com verificação de existência real):**
```bash
dotnet package search <NomeDoPacote> --exact-match --format json
```
Extrair o campo `latestVersion` do resultado. Usar apenas versões sem sufixo pre-release (`-alpha`, `-beta`, `-preview`, `-rc`).

> ⚠️ **`latestVersion` ≠ versão publicável garantida.** Alguns pacotes retornam versões que foram yanked (removidas) ou que nunca existiram como release estável no feed. Antes de pinar, confirmar que a versão consta na lista `packages[0].versions` do JSON retornado. Se a versão de `latestVersion` não aparecer na lista `versions` ou a lista estiver vazia, usar a versão stable mais recente que apareça em `versions`.
>
> **Caso especial — Carter:** Carter segue ciclo de versão próprio, independente do runtime .NET. Versões como `9.2.0` podem não existir no feed NuGet.org. Ao resolver Carter:
> 1. Executar Passo A e anotar o valor de `latestVersion`
> 2. Verificar se este valor aparece em `packages[0].versions` — se não aparecer, tomar a versão stable imediatamente anterior da lista
> 3. Se `dotnet build` retornar `NU1603` para Carter após pinar: a versão pinada não existe ou foi yanked → decrementar para a versão anterior estável e repetir Passo B→D→C

**Passo B — Pinar e restaurar:**
```xml
<!-- Directory.Packages.props -->
<PackageVersion Include="<NomeDoPacote>" Version="<versão do Passo A>" />
```
```bash
dotnet restore
```

**Passo D — Validar ausência de downgrade e versão inexistente (BLOQUEANTE):**
```bash
dotnet build 2>&1 | Select-String "NU1605|NU1603"
```
- Saída esperada: **0 linhas**
- `NU1605` significa que a versão pinada no CPM é **menor** do que a versão mínima exigida por uma dependência transitiva do pacote recém-adicionado. Isso causa conflito de versão resolvido "para baixo" pelo NuGet — com `TreatWarningsAsErrors=true` viraria erro de build; com o padrão atual (`TreatWarningsAsErrors=false`) é um warning, mas ainda deve ser corrigido.
- Se `NU1605` for detectado:
  1. Ler a mensagem: ela informa qual pacote transitivo exige versão maior (ex: `PackageA → PackageB (>= X.Y.Z)`)
  2. Atualizar `<PackageVersion Include="PackageB" Version="X.Y.Z" />` no CPM para a versão exigida (`>= max` de toda a cadeia)
  3. `dotnet restore` → repetir Passo D até 0 linhas
  > **Cadeia típica que causa NU1605:** `HealthChecks.SqlServer → Microsoft.Data.SqlClient → Azure.Identity (≥ X)` — se `Azure.Identity` no CPM for menor que o mínimo exigido por SqlClient, NU1605 quebra o build no host. Sempre verificar a cadeia completa, não apenas o pacote direto.
- `NU1603` significa que a versão pinada no CPM **não existe no feed NuGet** (foi yanked ou nunca publicada). O NuGet resolve para a versão real disponível e emite o warning promovido a erro.
- Se `NU1603` for detectado:
  1. Ler a mensagem: ela tem o formato `"Package X.Y.Z was not found. Package A.B.C was resolved instead."`
  2. **A.B.C é a versão real disponível no feed** — atualizar CPM para `Version="A.B.C"` (não decrementar manualmente)
  3. `dotnet restore` → repetir Passo D até 0 linhas
  > ⛔ **NUNCA** decrementar a versão manualmente (X.Y.(Z-1) pode também não existir)
  > ⛔ **NUNCA** usar a versão que estava em algum `.csproj` como fonte — ela pode ser a origem exata do problema
  > ✅ A versão correta está **na mensagem de erro do NuGet** — extrair A.B.C diretamente dela

**Passo C — Validar ausência de CVE (BLOQUEANTE):**
```bash
dotnet list package --vulnerable --include-transitive
```
- Saída esperada: `No vulnerable packages were found`
- Se qualquer CVE for listado para o pacote recém-pinado: **NÃO AVANÇAR**
  - Buscar a próxima versão patch/minor que cubra o CVE: repetir Passos A→C com versão superior
  - Se o CVE só for coberto por major version: usar o major mais recente sem pre-release
  - Se nenhuma versão do pacote estiver livre de CVE: substituir o pacote por alternativa (consultar seção "Armadilhas de Naming" para alternativas conhecidas) ou escalar para revisão de arquitetura

> ⚠️ **INVARIANTE ABSOLUTA:** Um pacote com CVE ativo **NUNCA** pode ser declarado como pinado. O gate `--vulnerable` deve retornar limpo **para cada pacote individualmente** antes de avançar para o próximo. Pinar todos e validar ao final é proibido — um CVE num pacote precoce pode mascarar CVEs em pacotes posteriores.

---

> ⚠️ **INVARIANTES ABSOLUTAS:**
> 1. Todo `<PackageReference>` em **todo** `.csproj` (incluindo projetos de teste) **DEVE** ter um `<PackageVersion>` correspondente em `Directory.Packages.props`. Entradas ausentes causam `NU1010` → falha de build.
> 2. Antes de retornar `COMPLETED`, o agente **DEVE** executar `dotnet build --no-incremental` e atingir **ZERO erros**. Um scaffold com build quebrado nunca é saída aceitável.
> 3. Versões pinadas no CPM **DEVEM** ser `>=` à versão máxima requerida por qualquer dependência transitiva. Violações causam `NU1605` → falha de build.
> 4. Pacotes com CVEs conhecidos (severidade NuGet audit `moderate` ou maior) **NÃO DEVEM** ser pinados em range que inclua a versão vulnerável. Com `TreatWarningsAsErrors=true`, `NU1902`/`NU1903` seriam promovidos a erros; no padrão atual (`TreatWarningsAsErrors=false`) aparecem como warnings, mas ainda indicam risco de segurança.

---

### Security Floors & Naming Traps

> ⛔ **Versões NÃO são hardcoded nesta política.**
> As versões são resolvidas dinamicamente via NuGet API pelo protocolo do
> `@ava-build-cycle-dotnet-scaffold` Step 1.6.
> Esta seção define APENAS:
> - **Pacotes com histórico de CVE** (requerem atenção especial na resolução)
> - **Armadilhas de naming** (pacotes que não existem no NuGet)
> - **Armadilhas de uso** (APIs que não funcionam como esperado)

#### Pacotes com Histórico de CVE (resolução dinâmica obrigatória)

> ⚠️ **Não existe floor numérico seguro permanente.** A versão "segura de hoje" pode ter novo CVE amanhã.
> O único gate válido é: resolver via NuGet API (Step 1.6) + executar `dotnet list package --vulnerable --include-transitive` → resultado limpo antes de declarar COMPLETED.
>
> A tabela abaixo registra pacotes com CVEs **conhecidos confirmados** que causaram falhas reais.
> Use os GHSA IDs para consultar o advisory atual e verificar se a versão resolvida os cobre.

| Pacote | CVEs conhecidos confirmados | Observação de resolução |
|---|---|---|
| `Microsoft.Identity.Web` | GHSA-rpq8-q44m-2rpg | ⛔ Versões `3.x` não têm fix disponível — garantir que NuGet API resolva `4.x` ou superior |
| `Microsoft.Data.SqlClient` | Dependência mínima de `AspNetCore.HealthChecks.SqlServer` | Resolver versão que satisfaça o peer requirement — versões antigas causam NU1605 |
| `Azure.Identity` | Dependência mínima de `Azure.Monitor.OpenTelemetry.AspNetCore` | Resolver versão que satisfaça o peer requirement — versões antigas causam NU1605 via EF Core SqlServer |
| `OpenTelemetry.Api` | GHSA-g94r-2vxg-569j | Trazido transitivamente por `Azure.Monitor.OpenTelemetry.AspNetCore` — aplicar transitive override (Passo 4 da Regra abaixo) no host quando `--vulnerable` detectar CVE |
| `OpenTelemetry.Extensions.Hosting` | GHSA-4625-4j76-fww9 | Idem — resolver via NuGet API e validar com `--vulnerable` |
| `OpenTelemetry.Instrumentation.Http` | Dependência mínima de `Azure.Monitor.OpenTelemetry.AspNetCore` | Resolver versão que satisfaça o peer requirement — versões antigas causam NU1605 |
| `Carter` | GHSA-37gx-xxp4-5rgx · GHSA-w3x6-4m5h-cxqf (via `System.Security.Cryptography.Xml` transitivo) | **Verificação TFM obrigatória antes de pinar:** confirmar que a versão resolvida inclui `netX.0` correspondente ao `tobe_stack.backend_version` do config. Procedimento: (1) `dotnet package search Carter --exact-match --format json` → extrair `latestVersion` e checar `targetFrameworks`; (2) se TFM incompatível, buscar versão anterior compatível via `https://api.nuget.org/v3/registration5/carter/index.json`; (3) após pinar, executar `--vulnerable` — se CVE em `System.Security.Cryptography.Xml`: aplicar transitive override nos projetos `Microsoft.NET.Sdk` afetados (ver Regras Especiais abaixo); (4) se nova versão de Carter já resolve o CVE internamente, nenhum override adicional necessário |
| `System.Security.Cryptography.Xml` | GHSA-37gx-xxp4-5rgx · GHSA-w3x6-4m5h-cxqf | Trazido transitivamente por Carter em projetos `Microsoft.NET.Sdk` — ver "Regras Especiais" abaixo |

#### Regras Especiais (não override simples)

| Pacote | SDK do projeto | Regra | Motivo |
|---|---|---|---|
| `System.Security.Cryptography.Xml` | `Microsoft.NET.Sdk.Web` | ⛔ **NÃO** adicionar como `<PackageReference>` | Framework ASP.NET Core já provê versão patched — referência direta causa **NU1510** |
| `System.Security.Cryptography.Xml` | `Microsoft.NET.Sdk` + Carter | ✅ **DEVE** aplicar transitive override (Passo 4 da Regra de Transitive Override abaixo) | Carter traz este pacote transitivamente; CPM pin sozinho é ignorado pelo NuGet sem `<PackageReference>` direto → **NU1903** persiste. Versão segura: resolver via NuGet API (Step 1.6) e validar com `dotnet list package --vulnerable` |
| `Azure.Core` | `Microsoft.NET.Sdk.Web` | Pin explícito obrigatório quando Azure.Monitor + Azure.Identity estiverem presentes | CS0433 (ambiguous type DefaultAzureCredential) — adicionar `<PackageReference Include="Azure.Core" />` ao host `.csproj` se CS0433 aparecer |

> **Cadeia transitiva confirmada (incidente MeuERP mai/2026):**
> - `Carter 8.x` → `System.Security.Cryptography.Xml` (via dependências internas ASP.NET Core) — afeta **todo** projeto `Microsoft.NET.Sdk` que usa Carter; projeto `.Web` não é afetado (framework provê)
> - `Azure.Monitor.OpenTelemetry.AspNetCore` → `OpenTelemetry.Api` — afeta host `Microsoft.NET.Sdk.Web` quando a versão transitiva resolvida contém CVE; resolver via NuGet API e validar com `--vulnerable`

> **Cadeias transitivas NU1605 confirmadas (incidente MeuERP mai/2026) — padrões de downgrade:**
>
> **Padrão 1 — HealthChecks.SqlServer + Azure.Identity:**
> `AspNetCore.HealthChecks.SqlServer → Microsoft.Data.SqlClient → Azure.Identity (≥ X.Y.Z)`
> Se `Azure.Identity` no CPM for pinado com versão menor que o mínimo exigido por `Microsoft.Data.SqlClient` (transitivo de HealthChecks), o NuGet detecta downgrade → `NU1605`.
> **Regra:** ao adicionar `AspNetCore.HealthChecks.SqlServer` ao CPM, executar Passo D imediatamente após restore — a versão de `Azure.Identity` no CPM deve satisfazer o requisito **da cadeia inteira**, não apenas o que o host declara diretamente.
>
> **Padrão 2 — EFCore.SqlServer + Dapper coexistindo na mesma Infrastructure:**
> `Microsoft.EntityFrameworkCore.SqlServer → Microsoft.Data.SqlClient (≥ X.Y.Z)` e
> `Dapper → Microsoft.Data.SqlClient (≥ A.B.C)` — se A.B.C < X.Y.Z, o CPM deve usar `max(X.Y.Z, A.B.C)`.
> Quando EF Core SqlServer e Dapper referenciam versões mínimas diferentes de `Microsoft.Data.SqlClient`, pinar a versão mais baixa causa `NU1605` a partir do projeto que exige a maior. **Regra:** sempre verificar `dotnet build | Select-String "NU1605"` após adicionar qualquer pacote de acesso a dados (EF, Dapper, HealthChecks.*Sql).
>
> **Padrão 3 — Microsoft.Identity.Web + Microsoft.Identity.Abstractions (NU1902/GHSA-rpq8-q44m-2rpg):**
> `Microsoft.Identity.Web (< versão limpa) → Microsoft.Identity.Abstractions 8.0.0 (GHSA-rpq8-q44m-2rpg, severidade moderada)`
> Se `Microsoft.Identity.Web` no CPM for pinado com versão que puxa `Microsoft.Identity.Abstractions 8.0.0` vulnerável, o NuGet detecta CVE → `NU1902` → warning no padrão atual (`TreatWarningsAsErrors=false`) ou erro se a flag for reativada.
> **Regra:** ao adicionar `Microsoft.Identity.Web` ao CPM, executar Passo A (Step 1.6) para resolver a versão mais recente; executar Passo C (`--vulnerable`) antes de finalizar. Se NU1902 persistir, adicionar transitive override explícito:
> ```xml
> <!-- Directory.Packages.props — transitive override para cobrir GHSA-rpq8-q44m-2rpg -->
> <!-- Microsoft.Identity.Web < versão limpa → Microsoft.Identity.Abstractions 8.0.0 vulnerável -->
> <PackageVersion Include="Microsoft.Identity.Abstractions" Version="{versão resolvida via Step 1.6}" />
> ```
> **Gate Passo D** (após restore): `dotnet build 2>&1 | Select-String "NU1605|NU1902|Microsoft.Identity"` → 0 linhas. Qualquer match relacionado a `Microsoft.Identity.*` = verificar cadeia completa e atualizar ambos os pacotes no CPM.

> ⚠️ **CS0433 — extern alias:** Quando `Azure.Core` e `Azure.Identity` exportam `DefaultAzureCredential` no mesmo namespace (type-forwarding), adicionar `<Aliases>AzureId</Aliases>` na `<PackageReference>` de `Azure.Identity` e usar `AzureId::Azure.Identity.DefaultAzureCredential()` no código.

#### Armadilhas de Naming (pacotes que NÃO existem no NuGet)

> ⛔ Os itens abaixo **NÃO existem** no NuGet. Referenciar qualquer um causa **NU1101** (falha de restore).

| Pacote (NÃO existe) | Pacote correto |
|---|---|
| `OpenTelemetry.Exporter.AzureMonitor` | `Azure.Monitor.OpenTelemetry.AspNetCore` |
| `OpenTelemetry.AzureMonitor.Exporter` | `Azure.Monitor.OpenTelemetry.AspNetCore` |
| `AzureMonitor.OpenTelemetry.Exporter` | `Azure.Monitor.OpenTelemetry.AspNetCore` |

#### Armadilhas de Versão (padrões de versionamento que causam NU1101 ou NU1605)

> ⛔ Nenhum número de versão é hardcoded abaixo — a tabela descreve **padrões de erro**, não versões específicas.
> Sempre usar Step 1.6 para resolver a versão concreta antes de pinar.

| Pacote | Padrão problemático | Situação |
|---|---|---|
| `Serilog.Enrichers.CorrelationId` | Versões com apenas dois segmentos (ex: major.minor sem patch) | Muitas versões publicadas neste padrão **não existem no NuGet** — sempre usar Step 1.6 Passo A (`dotnet package search --exact-match`) para confirmar que a versão existe antes de pinar |
| `Microsoft.Extensions.Http.Resilience` | Versão baseada no número do TFM (ex: `8.x`, `9.x`, `10.x`) | Este pacote **não segue o versionamento do runtime .NET** — segue o ciclo independente do `Microsoft.Extensions`. Usar Step 1.6 para resolver a versão real publicada |

#### Armadilhas de Uso (APIs que não funcionam como esperado)

> ⛔ Os padrões abaixo causam erro de compilação ou runtime silencioso.

| Pacote | Anti-padrão | Correto |
|---|---|---|
| `Mapster.DependencyInjection` | `services.AddScoped<IMapper, ServiceMapper>()` | Não funciona em .NET 10. Usar `TypeAdapterConfig.GlobalSettings.Scan(Assembly.GetExecutingAssembly())` |
| `Microsoft.ApplicationInsights.AspNetCore` | Usar junto com `Azure.Monitor.OpenTelemetry.AspNetCore` | Escolher UM dos dois — misturar duplica telemetria e pode causar conflitos |
| `Swashbuckle.AspNetCore` | Usar com `Microsoft.AspNetCore.OpenApi` (TFM-locked) | Incompatível com `Microsoft.OpenApi 2.0`. Usar `AddOpenApi()` / `MapOpenApi()` built-in |

#### Testes — Participam do CPM (nomes — versão via Step 1.6)

> ⚠️ Projetos de teste participam do Central Package Management. Todo `<PackageReference>` de teste
> **DEVE** ter um `<PackageVersion>` correspondente — omissão causa `NU1010`.
> Versões são resolvidas via NuGet API (Step 1.6). Pacotes obrigatórios:

- `Microsoft.NET.Test.Sdk` — obrigatório em TODOS os projetos de teste
- `xunit` + `xunit.runner.visualstudio`
- `Moq` ou `NSubstitute` (escolher um)
- `FluentAssertions`
- `Microsoft.AspNetCore.Mvc.Testing` — testes de integração (TFM-locked)
- `Testcontainers.MsSql` + `Testcontainers.Redis` — testes de integração
- `NetArchTest.Rules` — testes de arquitetura
- `coverlet.collector` — obrigatório em TODOS os projetos de teste

---

### Checklist de Completude CPM (executar antes de retornar COMPLETED)

Antes de marcar a tarefa como concluída, executar o seguinte procedimento para cada projeto na solução:

```
Para cada .csproj na solução:
  Para cada <PackageReference Include="X"> nesse .csproj:
    1. Verificar: <PackageVersion Include="X"> existe em Directory.Packages.props
       → Se ausente: executar Step 1.6 (Protocolo de Resolução de Versão) para X e adicionar
    2. Após pinar X: executar dotnet restore + dotnet list package --vulnerable --include-transitive
       → Resultado DEVE ser vazio para X antes de avançar para o próximo pacote
       → Se CVE encontrado: Step 1.6 com versão superior → repetir até limpar
```

> ⛔ **PROIBIDO:** verificar vulnerabilidades somente no final, após pinar todos os pacotes. O gate `--vulnerable` deve ser executado **incrementalmente** — cada pacote pinado é validado antes de avançar para o próximo. Um CVE num pacote precoce pode mascarar CVEs em pacotes posteriores na saída do scan final.

---

### Regra de Transitive Override

> ⚠️ **BUG COMUM:** `<PackageVersion>` no CPM **NÃO sobrescreve** pacotes puramente transitivos (sem `<PackageReference>` direto em nenhum `.csproj`). O NuGet ignora o pin do CPM nesses casos — `NU1902`/`NU1903` persistem mesmo com a versão correta no `Directory.Packages.props`.

Quando um pacote transitivo possui CVE, aplicar **TODOS** os passos obrigatoriamente na ordem abaixo:

1. Identificar o pacote transitivo `P` com CVE (via `dotnet list package --vulnerable --include-transitive`).
2. Executar o **Step 1.6** (seção "Protocolo de Resolução de Versão") para `P` — obter a versão segura via `dotnet package search`, restaurar e confirmar que `--vulnerable` retorna limpo para `P`.
3. Verificar se `P` já tem `<PackageVersion>` no `Directory.Packages.props`:
   - Se sim: substituir pela versão segura obtida no Passo 2.
   - Se não: adicionar `<PackageVersion Include="P" Version="<versão segura do Passo 2>" />`.
4. **OBRIGATÓRIO:** Adicionar `<PackageReference Include="P" />` (**sem** atributo `Version`) em **cada** `.csproj` afetado — este passo ativa o pin do CPM para o pacote transitivo. Sem ele, o NuGet ignora o `<PackageVersion>` e o CVE persiste.
   ```xml
   <!-- transitive override: CVE <GHSA-ID> via <Pacote-Consumidor> — sem este PackageReference o CPM pin é ignorado pelo NuGet -->
   <PackageReference Include="P" />
   ```
5. Executar `dotnet restore` + `dotnet list package --vulnerable --include-transitive` → confirmar resultado limpo antes de avançar.

> **Exceção `Microsoft.NET.Sdk.Web`:** Pacotes providos pelo framework ASP.NET Core (ex: `System.Security.Cryptography.Xml`) **já têm** a versão patched injetada automaticamente. Adicionar `<PackageReference>` direto nesses projetos causa **NU1510**. Verificar o SDK do projeto antes de aplicar o Passo 4 — ver tabela "Regras Especiais".

> ⛔ **PROIBIDO:** Pular o Passo 2 (Step 1.6) e escrever a versão diretamente. A versão escrita sem validação pode ser ela própria vulnerável a outro CVE.

**Referência do incidente (MeuERP, mai/2026):**
- `OpenTelemetry.Api` (GHSA-g94r-2vxg-569j): CPM pin existia, mas sem `<PackageReference>` direto em `MeuERP.Api.csproj` → NU1902 persistia.
- `System.Security.Cryptography.Xml` (GHSA-37gx-xxp4-5rgx + GHSA-w3x6-4m5h-cxqf): sem CPM pin e sem `<PackageReference>` direto em projetos `Microsoft.NET.Sdk` com Carter → NU1903 em todo `.Api` slice e em `CustomerSupplier.Infrastructure`.
- **Solução aplicada:** Step 1.6 para ambos → `<PackageVersion>` no CPM + `<PackageReference>` direto nos `.csproj` afetados (exceto host `.Web` onde o framework já provê).

---

### Gate Pré-Entrega (OBRIGATÓRIO — ZERO TOLERÂNCIA)

Após gerar ou modificar qualquer `.csproj` ou `Directory.Packages.props`, executar **nesta ordem** antes de retornar `COMPLETED`:

#### Passo 1 — Scan de Vulnerabilidades NuGet (EXECUTAR PRIMEIRO)

```bash
dotnet list package --vulnerable --include-transitive
```

- **Política: ZERO CVEs aceitas — qualquer severidade bloqueia a entrega.**
- Severidades bloqueantes: `Low` · `Moderate` · `High` · `Critical` — **sem exceção**.
- Saída esperada ao passar: `No vulnerable packages were found`.
- Se qualquer CVE for listado: corrigir usando a Regra de Transitive Override acima e re-executar o scan antes de avançar.

> ⚠️ **INVARIANTE:** Não existe CVE "aceitável por ser low" neste pipeline. Uma dependência com CVE Low é um bloqueio igual a Critical.

#### Passo 2 — Build bottom-up por camada (GUARDRAIL CASCADE)

> ⚠️ **INVARIANTE:** Buildar camada a camada na ordem abaixo. Falha em qualquer nível = PARAR e corrigir antes de avançar. Nunca declarar `COMPLETED` com build quebrado em qualquer projeto da SLN.

```
1. Domain         → dotnet build src/{BC}/{BC}.Domain/
2. Application    → dotnet build src/{BC}/{BC}.Application/
3. Infrastructure → dotnet build src/{BC}/{BC}.Infrastructure/
4. Api (slice)    → dotnet build src/{BC}/{BC}.Api/
5. Host           → dotnet build hosts/{Host}/
6. SLN inteira    → dotnet build --no-incremental {SLN}.sln
```

Gate final: **`0 Error(s)`** na SLN inteira.

**Erros comuns por nível e ação de correção:**
- `NU1010` → pacote ausente no CPM → adicionar em `Directory.Packages.props`.
- `NU1605` → downgrade de versão → bumpar a versão no CPM.
- `NU1901` → CVE low → corrigir versão + adicionar PackageReference direto se transitivo.
- `NU1902` → CVE moderate → idem.
- `NU1903` → CVE high/critical → idem.
- `NU1510` → PackageReference redundante em projeto `.Web` (framework já provê) → remover a referência direta.
- `CS0433` → tipo ambíguo entre dois assemblies → usar `extern alias` para desambiguar.
- `CS*` → erro de compilação → corrigir código-fonte.

---


### Step 1 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-dotnet-nuget-policy --phase F2 --version 1.0.0 \
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

### Template Obrigatório para Directory.Packages.props

Todo scaffold gerado DEVE incluir este `<PropertyGroup>` no `Directory.Packages.props`:

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <!-- NuGet Audit: zero tolerance — all CVE severities (Low/Moderate/High/Critical) block the build -->
    <NuGetAudit>true</NuGetAudit>
    <NuGetAuditLevel>low</NuGetAuditLevel>
    <WarningsAsErrors></WarningsAsErrors>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
  </PropertyGroup>

  <ItemGroup>
    <!-- versões pinadas aqui -->
  </ItemGroup>
</Project>
```

> `NuGetAuditLevel=low` sem `TreatWarningsAsErrors=true` mantém `NU1901/NU1902/NU1903` como warnings — o build não quebra por CVE audit, mas os avisos permanecem visíveis no log.

---

### Template para Directory.Build.props

Todo scaffold gerado DEVE incluir (ou atualizar) o `Directory.Build.props` na raiz da solution com a tag `<Copyright>` resolvida pela **Copyright Header Rule** do `coder-dotnet.md`.

```xml
<Project>
  <PropertyGroup>
    <!-- Copyright resolvido pelo agente coder-dotnet via campos copyright +
         copyright_suffix de project-config.yaml.
         Embutido automaticamente pelo compilador .NET em todos os metadados
         de assembly: DLLs, EXEs e pacotes NuGet — sem configuração adicional
         por projeto. -->
    <Copyright>{copyright_final}</Copyright>
    <Company>Avanade</Company>
    <!-- Redireciona bin/obj para fora do repo encurtando o caminho total.
         O target CreateBaseOutputDirs abaixo garante que o diretorio exista. -->
    <BaseOutputPath Condition="$([MSBuild]::IsOSPlatform('Windows'))">C:\avaout\$(MSBuildProjectName)\bin\</BaseOutputPath>
    <BaseIntermediateOutputPath Condition="$([MSBuild]::IsOSPlatform('Windows'))">C:\avaout\$(MSBuildProjectName)\obj\</BaseIntermediateOutputPath>
  </PropertyGroup>

  <Target Name="CreateBaseOutputDirs" BeforeTargets="BeforeBuild" Condition="$([MSBuild]::IsOSPlatform('Windows'))">
    <MakeDir Directories="$(BaseOutputPath);$(BaseIntermediateOutputPath)" />
  </Target>
</Project>
```

> **Delegação:** A responsabilidade de calcular `copyright_final` e escrever este arquivo pertence ao agente `coder-dotnet`. Não duplicar a lógica aqui — este template é apenas referência de estrutura.

---

### SDK Correto por Tipo de Projeto

| Tipo de projeto | SDK correto | Observação |
|---|---|---|
| API / Web app | `Microsoft.NET.Sdk.Web` | **OBRIGATÓRIO** — sem `.Web` faltam `WebApplication`, `StatusCodes`, `IApplicationBuilder` etc. |
| Domain / Application / Infrastructure | `Microsoft.NET.Sdk` | Sem `.Web` — projetos de lógica pura |
| Testes | `Microsoft.NET.Sdk` | Sem `.Web` |

> ⚠️ Usar `Microsoft.NET.Sdk` em um projeto API causa erros `CS0103: WebApplication does not exist` e outros em cascata.