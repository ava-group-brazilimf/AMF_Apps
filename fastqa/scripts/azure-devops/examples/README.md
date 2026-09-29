# 📦 Upload de Múltiplas Execuções de Teste (Batch Test Execution)

## � **NOVIDADE:** Preview e Confirmação Obrigatória

**A partir desta versão, o comando `@fastqa:azdo_upload_batch_test_execution` inclui:**
- ✅ **Preview formatado** do conteúdo dos arquivos JSON/CSV
- ⚠️ **Confirmação obrigatória** antes da execução
- 🔍 **Comandos de preview** para visualizar sem executar
- ✏️ **Opção de edição** inline dos dados

---

## 🎯 Objetivo

Este comando permite executar upload de múltiplas execuções de teste no Azure DevOps de uma vez, processando lote de test cases com suas respectivas evidências de forma sequencial e automatizada.

## 🔄 Novo Fluxo com Confirmação

1. **Escolher formato** (JSON, CSV ou Inline)
2. **Carregar/criar arquivo** com os dados
3. **📋 PREVIEW AUTOMÁTICO:** Sistema exibe conteúdo formatado
4. **⚠️ CONFIRMAÇÃO:** "Confirma as informações acima para prosseguir?"
5. **Opções:** Sim (executar) | Não (cancelar) | Editar (modificar)
6. **🚀 Execução:** Somente após confirmação positiva

## ⚡ Como Usar

### Comando FastQA Agent

```
@fastqa:azdo_upload_batch_test_execution
```

### 🔍 Comandos de Preview (Novo - Apenas Visualizar)

```bash
# Preview JSON (sem executar)
npx tsx upload-batch-test-execution.command.ts --preview-json "batch-executions.json"

# Preview CSV (sem executar)
npx tsx upload-batch-test-execution.command.ts --preview-csv "batch.csv" --test-plan-id 29

# Preview Inline (sem executar)
npx tsx upload-batch-test-execution.command.ts --preview-inline \
  --test-plan-id 29 --executions "38:14:Passed:C:/evidence/TC-14:Teste 1"
```

### Comando Direto (Execução)

```bash
# Via arquivo JSON
npx tsx upload-batch-test-execution.command.ts --json-file "batch-executions.json"

# Via arquivo CSV  
npx tsx upload-batch-test-execution.command.ts --csv-file "batch.csv" --test-plan-id 29

# Via parâmetros inline
npx tsx upload-batch-test-execution.command.ts --test-plan-id 29 \
  --executions "38:14:Passed:C:/evidence/TC-14:Teste 1|38:15:Failed:C:/evidence/TC-15:Teste 2"
```

## 📁 Formatos Suportados

### 1. JSON (Recomendado - Mais Flexível)

**Arquivo:** `batch-executions.json`

```json
{
  "testPlanId": 29,
  "executions": [
    {
      "testSuiteId": 38,
      "testCaseId": 14,
      "result": "Passed",
      "evidencePath": "C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-14",
      "comment": "Execução automatizada - Teste de logo no cabeçalho",
      "attachToWorkItem": true,
      "autoBug": false,
      "bugSeverity": "3 - Medium"
    },
    {
      "testSuiteId": 38,
      "testCaseId": 15,
      "result": "Failed",
      "evidencePath": "C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-15",
      "comment": "Falha na validação do formulário de login",
      "attachToWorkItem": false,
      "autoBug": true,
      "bugSeverity": "2 - High"
    }
  ]
}
```

### 2. CSV (Ideal para Planilhas)

**Arquivo:** `batch-executions.csv`

```csv
testSuiteId,testCaseId,result,evidencePath,comment,attachToWorkItem,autoBug,bugSeverity
38,14,Passed,C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-14,Execução automatizada,true,false,3 - Medium
38,15,Failed,C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-15,Falha na validação,false,true,2 - High
39,16,Blocked,C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-16,Dependência externa,true,false,4 - Low
```

### 3. Inline (Comandos Rápidos)

**Formato:** `suiteId:caseId:result:evidencePath:comment` separado por `|`

```bash
--executions "38:14:Passed:C:/evidence/TC-14:Teste login válido|38:15:Failed:C:/evidence/TC-15:Teste login inválido"
```

## 🔧 Parâmetros

### Campos Obrigatórios

| Campo | Tipo | Descrição | Valores Aceitos |
|-------|------|-----------|-----------------|
| `testSuiteId` | number | ID da Test Suite no Azure DevOps | Número inteiro |
| `testCaseId` | number | ID do Test Case no Azure DevOps | Número inteiro |
| `result` | string | Resultado da execução | `Passed`, `Failed`, `Blocked`, `NotApplicable` |
| `evidencePath` | string | Caminho para arquivo/pasta de evidências | Caminho absoluto ou relativo |

### Campos Opcionais

| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `comment` | string | — | Comentário da execução |
| `attachToWorkItem` | boolean | `false` | Anexar evidências ao Work Item também |
| `autoBug` | boolean | `false` | Criar bug automaticamente se Failed |
| `bugSeverity` | string | `3 - Medium` | Severidade do bug auto-criado |

### Valores de Severidade

- `1 - Critical` — Sistema indisponível, perda de dados
- `2 - High` — Funcionalidade crítica sem workaround
- `3 - Medium` — Funcionalidade com workaround disponível
- `4 - Low` — Problema cosmético ou documentação

## 🚀 Fluxo de Execução

Para cada execução na lista, o script executa sequencialmente:

1. ✅ **Validação** — Verifica se arquivos de evidência existem
2. 🔍 **Test Point** — Obtém Test Point do Azure DevOps (Plan → Suite → Case)
3. ▶️ **Test Run** — Cria Test Run individual no Azure DevOps  
4. 📎 **Upload** — Anexa todas as evidências como attachments
5. ✅ **Outcome** — Atualiza resultado (Passed/Failed/Blocked)
6. 🏁 **Finalização** — Completa Test Run com status "Completed"
7. 🐛 **Bug (opcional)** — Cria bug se `autoBug=true` e resultado=Failed
8. 📋 **Work Item (opcional)** — Anexa evidências ao Work Item se `attachToWorkItem=true`
9. ⏱️ **Pausa** — Aguarda 1s antes da próxima execução (evitar throttling)

## 📊 Relatório de Saída

```
📊 RESUMO DO BATCH EXECUTION
═══════════════════════════════════════

   Test Plan:       #29
   Total Execuções: 4
   ✅ Sucessos:     3 (75.0%)
   ❌ Falhas:       1
   Test Runs:       4 criados  
   Evidências:      15 anexadas
   Bugs:            1 criados
   Duração Total:   45.3s

📋 DETALHAMENTO POR EXECUÇÃO:
   ✅ TC-14: 8.2s | Evidências: 5
   ❌ TC-15: 12.1s | Evidências: 0
      Erro: Test Point não encontrado para TC-15 na Suite 38
   ✅ TC-16: 15.7s | Evidências: 3
   ✅ TC-17: 9.3s | Evidências: 7

   📝 Log detalhado salvo em: C:/projetos/.../logs/batch-execution-1771623456789.json
```

## 🎯 Casos de Uso

### 1. Execução de Smoke Tests

Após deploy, executar testes críticos:

```json
{
  "testPlanId": 29,
  "executions": [
    { "testSuiteId": 40, "testCaseId": 20, "result": "Passed", "evidencePath": "C:/smoke/login", "comment": "Smoke - Login" },
    { "testSuiteId": 40, "testCaseId": 21, "result": "Passed", "evidencePath": "C:/smoke/search", "comment": "Smoke - Busca" },
    { "testSuiteId": 40, "testCaseId": 22, "result": "Passed", "evidencePath": "C:/smoke/checkout", "comment": "Smoke - Checkout" }
  ]
}
```

### 2. Regression Testing

Executar suíte de regressão com detecção automática de bugs:

```json
{
  "testPlanId": 29,
  "executions": [
    { "testSuiteId": 38, "testCaseId": 14, "result": "Passed", "evidencePath": "C:/regression/TC-14", "autoBug": false },
    { "testSuiteId": 38, "testCaseId": 15, "result": "Failed", "evidencePath": "C:/regression/TC-15", "autoBug": true, "bugSeverity": "2 - High" },
    { "testSuiteId": 38, "testCaseId": 16, "result": "Failed", "evidencePath": "C:/regression/TC-16", "autoBug": true, "bugSeverity": "1 - Critical" }
  ]
}
```

### 3. Execução via Planilha (Excel → CSV)

1. Preencher planilha Excel com dados dos testes
2. Exportar como CSV
3. Executar batch:

```bash
npx tsx upload-batch-test-execution.command.ts --csv-file "relatorio-testes.csv" --test-plan-id 29
```

## ⚠️ Validações Automáticas

O script executa as seguintes validações:

- ✅ **Arquivos de evidência** — Verifica se existem nos caminhos especificados
- ✅ **Associação Test Case → Suite** — Valida se TC está na Suite informada
- ✅ **Formatos** — JSON/CSV estruturalmente corretos
- ✅ **Campos obrigatórios** — testSuiteId, testCaseId, result, evidencePath
- ✅ **Valores de resultado** — Passed | Failed | Blocked | NotApplicable
- ✅ **Valores de severidade** — 1-Critical, 2-High, 3-Medium, 4-Low
- ✅ **Credenciais Azure DevOps** — PAT token válido no .env

## 📂 Estrutura de Evidências

O script suporta evidências em:

### Arquivo Individual
```
evidencePath: "C:/projetos/evidence/login-error.mp4"
```

### Pasta com Múltiplos Arquivos
```
evidencePath: "C:/projetos/evidence/TC-14/"
├── step-01-navegacao.png
├── step-02-preenchimento.png  
├── step-03-validacao.png
└── video-completo.webm
```

### Extensões Suportadas
`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.mp4`, `.webm`, `.avi`, `.pdf`, `.html`, `.txt`, `.md`, `.json`, `.xlsx`, `.docx`

## 🔗 Integração com Outros Comandos

### Antes do Batch
1. `@fastqa:azdo_list_test_plans` — Identificar IDs de Plans/Suites
2. `@fastqa:azdo_create_test_case` — Criar test cases se necessário
3. `@fastqa:azdo_add_testcase_to_suite` — Associar TCs às suites

### Depois do Batch  
1. `@fastqa:azdo_generate_report` — Gerar relatório consolidado
2. `@fastqa:azdo_get_work_item_by_id_or_title` — Verificar bugs criados

## 🚨 Tratamento de Erros

### Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| `Test Point não encontrado` | Test Case não está na Suite | Usar `@fastqa:azdo_add_testcase_to_suite` |
| `Arquivo não encontrado` | Caminho de evidência inválido | Verificar paths no JSON/CSV |
| `401 Unauthorized` | PAT inválido | Renovar token no `.env` |
| `Formato JSON inválido` | Estrutura incorreta | Validar com exemplo fornecido |
| `CSV mal formado` | Cabeçalho ou dados incorretos | Verificar vírgulas e aspas |

### Comportamento em Falhas

- ✅ **Falha individual** — Continua processando demais execuções
- ✅ **Log detalhado** — Registra erro específico para cada falha  
- ✅ **Relatório final** — Exibe sucessos e falhas com detalhamento
- ✅ **Rollback** — Não desfaz execuções já concluídas (por design)

## 📁 Arquivos de Log

### Log Detalhado JSON
`fastqa/scripts/azure-devops/logs/batch-execution-{timestamp}.json`

```json
{
  "totalExecutions": 4,
  "successful": 3,
  "failed": 1,
  "testRunsCreated": 4,
  "evidencesUploaded": 15,
  "bugsCreated": 1,  
  "duration": 45320,
  "results": [
    {
      "testCaseId": 14,
      "success": true,
      "testRunId": 123,
      "testResultId": 456,
      "evidencesUploaded": 5,
      "duration": 8234
    }
  ]
}
```

## 🎓 Exemplos Práticos

Os arquivos de exemplo estão disponíveis em:

- 📄 **JSON:** `fastqa/scripts/azure-devops/examples/batch-executions-example.json`
- 📄 **CSV:** `fastqa/scripts/azure-devops/examples/batch-executions-example.csv`

Copie e adapte conforme sua necessidade!

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte o log detalhado em `logs/batch-execution-*.json`
2. Verifique as credenciais no arquivo `.env`
3. Execute um teste individual primeiro com `@fastqa:azdo_upload_test_execution`
4. Consulte a documentação completa em `.github/instructions/fastQAAzureDevOps.instructions.md`