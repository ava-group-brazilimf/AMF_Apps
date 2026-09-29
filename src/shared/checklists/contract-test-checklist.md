---
name: contract-test-checklist
description: "Checklist de validação obrigatório para o agente ava-qa-contract-test-generator antes de finalizar outputs"
version: "1.0.0"
agent: "ava-qa-contract-test-generator"
gate: "Step 6 — Update .sln (antes do Step 7 — Generate Documentation)"
---

# Contract Test — Validation Checklist

> **Quando aplicar**: O agente `ava-qa-contract-test-generator` DEVE executar este checklist
> antes de escrever o relatório final (Step 7 — Generate Documentation).
> Todos os critérios de severidade `BLOCKING` devem passar para que o gate seja `✅ PASS`.
> Critérios `WARNING` podem passar com ressalva (`⚠️ PASS_WITH_WARNINGS`).

---

## Critérios de Validação

| #  | ID | Critério | Severidade | Regra | Ação se falhar |
|----|----|----------|:----------:|-------|----------------|
| 1  | `CHK-CT-CONSUMER` | Cobertura de operations no consumer | `BLOCKING` | Cada operação HTTP identificada nos OpenAPI specs tem ≥ 1 consumer test em `Consumer/*.cs` | Adicionar interaction faltante para a operação sem cobertura |
| 2  | `CHK-CT-PROVIDER` | Verificação de provider presente | `BLOCKING` | Cada BC que possui consumer tests tem um provider verification test em `Provider/*.cs` | Criar `{BC}ProviderTests.cs` para o BC sem verificação |
| 3  | `CHK-CT-PACT-FILES` | Consumer tests geram pact files | `BLOCKING` | Cada consumer test referencia `PactConfig.CreatePact(...)` e define ao menos 1 interaction com `.UponReceiving(...)` | Corrigir testes que não definem interactions PactNet válidas |
| 4  | `CHK-CT-BUILD` | Compilação do projeto | `BLOCKING` | `dotnet build {ProjectName}.ContractTests.csproj` exit 0 (zero erros de compilação) | Corrigir erros de compilação antes de finalizar |
| 5  | `CHK-CT-SLN` | Projeto registrado na solution | `WARNING` | `{ProjectName}.ContractTests.csproj` está referenciado no arquivo `.sln` | Adicionar bloco `Project(...)EndProject` na `.sln` |
| 6  | `CHK-CT-NAMING` | Nomenclatura dos métodos de teste | `WARNING` | Métodos de consumer test seguem padrão `{Entity}_{Interaction}_{ExpectedBehavior}` (ex.: `GetContasPagarList_WithValidToken_ReturnsPagedResult`) | Renomear métodos que não seguem a convenção |
| 7  | `CHK-CT-TRACEABILITY` | Rastreabilidade TC-ID | `WARNING` | Cada `[Fact]` tem comentário `// CT-{NNN}` acima da declaração | Adicionar comentário de rastreabilidade ao `[Fact]` |
| 8  | `CHK-CT-SCHEMA` | Validação de schema contra OpenAPI | `BLOCKING` | O response body em cada interaction `.WillRespond().WithJsonBody(...)` contém os campos obrigatórios definidos no schema OpenAPI correspondente | Alinhar `WithJsonBody` com os campos `required` do schema OpenAPI |

---

## Gate Logic

```
BLOCKING_PASS  = ALL critérios com severidade BLOCKING passaram
WARNING_COUNT  = COUNT de critérios WARNING que falharam

if NOT BLOCKING_PASS:
    gate = ❌ FAIL
    action = Corrigir todos os BLOCKING antes de prosseguir para Step 7
elif WARNING_COUNT > 0:
    gate = ⚠️ PASS_WITH_WARNINGS
    action = Registrar warnings no relatório, prosseguir para Step 7
else:
    gate = ✅ PASS
    action = Prosseguir para Step 7
```

---

## Template de Resultado (para inclusão no relatório)

```markdown
## Validation Checklist

| #  | ID | Critério | Status | Detalhes |
|----|----|----------|:------:|----------|
| 1  | CHK-CT-CONSUMER | Cobertura de operations | ✅ / ❌ | {N}/{total} operations com consumer test |
| 2  | CHK-CT-PROVIDER | Provider verification | ✅ / ❌ | {N}/{total} BCs com provider test |
| 3  | CHK-CT-PACT-FILES | Pact interactions definidas | ✅ / ❌ | {N}/{total} consumer tests com interaction válida |
| 4  | CHK-CT-BUILD | dotnet build exit 0 | ✅ / ❌ | {0 erros / N erros de compilação} |
| 5  | CHK-CT-SLN | Projeto na solution | ✅ / ⚠️ | Projeto {referenciado / não referenciado} na .sln |
| 6  | CHK-CT-NAMING | Nomenclatura de métodos | ✅ / ⚠️ | {N} métodos fora do padrão |
| 7  | CHK-CT-TRACEABILITY | Rastreabilidade TC-ID | ✅ / ⚠️ | {N}/{total} [Fact]s sem comentário CT-NNN |
| 8  | CHK-CT-SCHEMA | Schema OpenAPI validado | ✅ / ❌ | {N}/{total} interactions com schema alinhado |

**Gate Result:** ✅ PASS / ⚠️ PASS_WITH_WARNINGS / ❌ FAIL
```
