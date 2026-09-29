---
name: frontend-test-checklist
description: "Checklist de validação obrigatório para o agente ava-qa-frontend-test-generator antes de finalizar outputs"
version: "1.0.0"
agent: "ava-qa-frontend-test-generator"
gate: "Step 5 — Generate NgRx Store Tests (antes do Step 6 — Generate Documentation)"
---

# Frontend Test — Validation Checklist

> **Quando aplicar**: O agente `ava-qa-frontend-test-generator` DEVE executar este checklist
> antes de escrever o relatório final (Step 6 — Generate Documentation).
> Todos os critérios de severidade `BLOCKING` devem passar para que o gate seja `✅ PASS`.
> Critérios `WARNING` podem passar com ressalva (`⚠️ PASS_WITH_WARNINGS`).

---

## Critérios de Validação

| #  | ID | Critério | Severidade | Regra | Ação se falhar |
|----|----|----------|:----------:|-------|----------------|
| 1  | `CHK-FT-JEST-CONFIG` | Arquivos de configuração Jest presentes | `BLOCKING` | `jest.config.ts` e `setup-jest.ts` existem em `frontend/` | Criar ou corrigir os arquivos de configuração conforme template |
| 2  | `CHK-FT-COVERAGE` | Cobertura de componentes | `BLOCKING` | ≥ 80% dos componentes identificados no Step 2 possuem arquivo `.spec.ts` correspondente | Gerar `.spec.ts` para componentes sem cobertura |
| 3  | `CHK-FT-SMART-STATES` | Smart components testam 3 estados | `BLOCKING` | Cada Page component (`*-page.component.ts`) tem testes para os estados: `loading=true`, `list` com dados, e `error` com mensagem | Adicionar os estados faltantes no `.spec.ts` da page component |
| 4  | `CHK-FT-NO-IMPL-DETAIL` | Sem queries de detalhe de implementação | `BLOCKING` | Nenhum `.spec.ts` gerado usa `fixture.debugElement.query(By.css(...))` — todas as queries usam `getByRole`, `getByText`, `getByLabel` | Substituir queries CSS por Testing Library queries |
| 5  | `CHK-FT-USER-EVENT` | Interações usam userEvent | `WARNING` | Interações de usuário usam `userEvent` (ex.: `userEvent.click`, `userEvent.type`) em vez de `fireEvent` | Substituir `fireEvent` por `userEvent` nos testes afetados |
| 6  | `CHK-FT-STORE` | Reducers NgRx com testes de actions | `WARNING` | Cada `*.reducer.ts` identificado no Step 2 possui `.spec.ts` com testes para todas as actions mapeadas | Adicionar casos de teste para actions sem cobertura no reducer |
| 7  | `CHK-FT-NPM-TEST` | Suite de testes compila e executa | `BLOCKING` | `npm test -- --ci --passWithNoTests` exit 0 (zero erros de compilação TypeScript) | Corrigir erros de compilação TypeScript nos `.spec.ts` gerados |
| 8  | `CHK-FT-KARMA-REMOVED` | Karma completamente removido | `WARNING` | `karma`, `karma-*`, `jasmine-core` ausentes de `devDependencies` em `package.json` | Remover dependências Karma/Jasmine remanescentes |

---

## Gate Logic

```
BLOCKING_PASS  = ALL critérios com severidade BLOCKING passaram
WARNING_COUNT  = COUNT de critérios WARNING que falharam

if NOT BLOCKING_PASS:
    gate = ❌ FAIL
    action = Corrigir todos os BLOCKING antes de prosseguir para Step 6
elif WARNING_COUNT > 0:
    gate = ⚠️ PASS_WITH_WARNINGS
    action = Registrar warnings no relatório, prosseguir para Step 6
else:
    gate = ✅ PASS
    action = Prosseguir para Step 6
```

---

## Template de Resultado (para inclusão no relatório)

```markdown
## Validation Checklist

| #  | ID | Critério | Status | Detalhes |
|----|----|----------|:------:|----------|
| 1  | CHK-FT-JEST-CONFIG | jest.config.ts + setup-jest.ts | ✅ / ❌ | Arquivos {presentes / ausentes} |
| 2  | CHK-FT-COVERAGE | Cobertura de componentes | ✅ / ❌ | {N}/{total} componentes com .spec.ts ({%}%) |
| 3  | CHK-FT-SMART-STATES | 3 estados em smart components | ✅ / ❌ | {N}/{total} page components com 3 estados testados |
| 4  | CHK-FT-NO-IMPL-DETAIL | Sem By.css queries | ✅ / ❌ | {N} ocorrências de debugElement.query(By.css) |
| 5  | CHK-FT-USER-EVENT | userEvent sobre fireEvent | ✅ / ⚠️ | {N} ocorrências de fireEvent a substituir |
| 6  | CHK-FT-STORE | Reducers com todas as actions | ✅ / ⚠️ | {N}/{total} reducers com cobertura completa |
| 7  | CHK-FT-NPM-TEST | npm test --ci exit 0 | ✅ / ❌ | {0 erros / N erros de compilação TypeScript} |
| 8  | CHK-FT-KARMA-REMOVED | Karma removido | ✅ / ⚠️ | Karma {ausente / ainda presente em devDependencies} |

**Gate Result:** ✅ PASS / ⚠️ PASS_WITH_WARNINGS / ❌ FAIL
```
