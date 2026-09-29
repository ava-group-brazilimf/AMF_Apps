---
name: scenario-generator-checklist
description: "Checklist de validação obrigatório para o agente ava-qa-scenario-generator antes de finalizar outputs"
version: "1.0.0"
agent: "ava-qa-scenario-generator"
gate: "STEP 5 — VALIDATE"
---

# Scenario Generator — Validation Checklist

> **Quando aplicar**: O agente `ava-qa-scenario-generator` DEVE executar este checklist
> no STEP 5 (VALIDATE) antes de escrever os arquivos finais (STEP 6).
> Todos os critérios de severidade `BLOCKING` devem passar para que o gate seja `✅ PASS`.
> Critérios `WARNING` podem passar com ressalva (`⚠️ PASS_WITH_WARNINGS`).

---

## Critérios de Validação

| # | ID | Critério | Severidade | Regra | Ação se falhar |
|---|-----|----------|:----------:|-------|----------------|
| 1 | `CHK-COUNT` | Contagem mínima de cenários | `BLOCKING` | Total de cenários ≥ 15 | Gerar cenários adicionais para features com menor cobertura |
| 2 | `CHK-HAPPY` | Cobertura de happy path | `BLOCKING` | Cada Feature tem ≥ 1 cenário com tag `@happy` | Adicionar cenário happy path para feature descoberta |
| 3 | `CHK-SAD` | Cobertura de sad path | `BLOCKING` | Cada Feature tem ≥ 1 cenário com tag `@sad` | Adicionar cenário sad path para feature descoberta |
| 4 | `CHK-GHERKIN` | Formato Gherkin válido | `BLOCKING` | Todo cenário segue ordem `Given` → `When` → `Then` | Corrigir cenário malformado — reordenar steps |
| 5 | `CHK-AMBIGUITY` | Sem ambiguidade de steps | `BLOCKING` | Nenhum step text idêntico com significados diferentes entre Features | Reescrever step com contexto específico da feature |
| 6 | `CHK-TAGS` | Tags obrigatórias | `WARNING` | Todo cenário tem ≥ 2 tags: 1 classificação (`@happy`/`@sad`/`@edge`) + 1 módulo (`@{module}`) | Adicionar tag faltante |
| 7 | `CHK-OUTLINE` | Scenario Outline aplicado | `WARNING` | Cenários que diferem apenas em dados (≥ 2) usam `Scenario Outline` + `Examples` | Converter cenários duplicados para Outline |
| 8 | `CHK-BG` | Background extraído | `WARNING` | Precondições repetidas em ≥ 2 cenários da mesma Feature extraídas para `Background` | Extrair steps compartilhados para Background |
| 9 | `CHK-TRACE` | Rastreabilidade | `WARNING` | Cada cenário tem comentário `# Source: {artefato}` referenciando origem | Adicionar referência ao artefato de origem |
| 10 | `CHK-ATOMIC` | Atomicidade | `WARNING` | Cada cenário testa exatamente 1 comportamento | Dividir cenário composto em cenários independentes |
| 11 | `CHK-STEPS` | Limite de steps | `WARNING` | Máximo 10 steps por cenário (`Given` + `When` + `Then` + `And` + `But`) | Simplificar cenário — extrair precondições para Background ou dividir |
| 12 | `CHK-DECL` | Steps declarativos | `WARNING` | Steps descrevem O QUE (declarativo), não COMO (imperativo) | Reescrever step: "the user submits the form" em vez de "click button Submit" |
| 13 | `CHK-THEN` | Then obrigatório | `BLOCKING` | Todo cenário tem pelo menos 1 step `Then` (resultado observável) | Adicionar step Then com resultado esperado |
| 14 | `CHK-SPECFLOW` | Compatibilidade SpecFlow/Cucumber | `BLOCKING` | Sem caracteres especiais em steps, encoding UTF-8, keywords válidas | Corrigir sintaxe — remover caracteres inválidos |
| 15 | `CHK-I18N` | Idioma correto | `WARNING` | Keywords Gherkin no idioma de `project-config.yaml` (`Feature`/`Funcionalidade`, etc.) | Traduzir keywords para o idioma configurado |

---

## Gate Logic

```
BLOCKING_PASS  = ALL critérios com severidade BLOCKING passaram
WARNING_COUNT  = COUNT de critérios WARNING que falharam

if NOT BLOCKING_PASS:
    gate = ❌ FAIL
    action = Corrigir todos os BLOCKING antes de prosseguir
elif WARNING_COUNT > 0:
    gate = ⚠️ PASS_WITH_WARNINGS
    action = Registrar warnings no report, prosseguir com STEP 6
else:
    gate = ✅ PASS
    action = Prosseguir com STEP 6
```

---

## Template de Resultado (para inclusão no report)

```markdown
## Validation Checklist

| # | ID | Critério | Status | Detalhes |
|---|-----|----------|:------:|----------|
| 1 | CHK-COUNT | Contagem mínima (≥ 15) | ✅ / ❌ | {N} cenários gerados |
| 2 | CHK-HAPPY | Happy path por Feature | ✅ / ❌ | {N}/{total} features cobertas |
| 3 | CHK-SAD | Sad path por Feature | ✅ / ❌ | {N}/{total} features cobertas |
| 4 | CHK-GHERKIN | Formato Gherkin | ✅ / ❌ | {N} cenários válidos |
| 5 | CHK-AMBIGUITY | Sem ambiguidade | ✅ / ❌ | {N} steps ambíguos encontrados |
| 6 | CHK-TAGS | Tags obrigatórias | ✅ / ⚠️ | {N} cenários com tags incompletas |
| 7 | CHK-OUTLINE | Scenario Outline | ✅ / ⚠️ | {N} candidatos a Outline |
| 8 | CHK-BG | Background | ✅ / ⚠️ | {N} features com precondições duplicadas |
| 9 | CHK-TRACE | Rastreabilidade | ✅ / ⚠️ | {N} cenários sem source reference |
| 10 | CHK-ATOMIC | Atomicidade | ✅ / ⚠️ | {N} cenários compostos |
| 11 | CHK-STEPS | Limite de steps | ✅ / ⚠️ | {N} cenários com >10 steps |
| 12 | CHK-DECL | Steps declarativos | ✅ / ⚠️ | {N} steps imperativos |
| 13 | CHK-THEN | Then obrigatório | ✅ / ❌ | {N} cenários sem Then |
| 14 | CHK-SPECFLOW | SpecFlow compat | ✅ / ❌ | {N} erros de sintaxe |
| 15 | CHK-I18N | Idioma correto | ✅ / ⚠️ | language: {language} |

**Gate**: {✅ PASS / ⚠️ PASS_WITH_WARNINGS / ❌ FAIL}
**BLOCKING failed**: {list or "none"}
**WARNING failed**: {list or "none"}
```
